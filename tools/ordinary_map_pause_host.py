"""Opt-in bounded read leases for the existing owned DbgEng smoke harness.

``render_source(real_exe_smoke.HARNESS)`` only transforms source; it launches
nothing. Five-argument use retains the ordinary harness behavior. The sixth
argument enables a caller-created local ASCII control directory. A ready ack
means verified image/entry readiness, not ordinary-map readiness. Only a paused
ack grants a read lease, and failure or expiry reaches Session's owned cleanup.
"""
from __future__ import annotations


CONTROLLER_SOURCE = r'''
// Opt-in read lease. No input delivery or target-memory writes belong here.
struct LeaseHandle {
    HANDLE value=INVALID_HANDLE_VALUE;
    LeaseHandle() = default;
    explicit LeaseHandle(HANDLE v):value(v) {}
    LeaseHandle(const LeaseHandle &)=delete;
    LeaseHandle &operator=(const LeaseHandle &)=delete;
    ~LeaseHandle() { close(); }
    void close() { if (value!=INVALID_HANDLE_VALUE) { CloseHandle(value); value=INVALID_HANDLE_VALUE; } }
};
struct LeaseRequest {
    ULONGLONG sequence=0;
    std::string operation,lease,wire;
};
struct PauseLeaseController {
    Session &s;
    bool enabled=false,ready_published=false;
    ULONG image_base=0;
    ULONGLONG creation_filetime=0,last_sequence=0;
    std::string directory,session,last_wire;
    std::vector<std::string> used_leases;
    LeaseHandle directory_handle;

    static bool hex_token(const std::string &v) {
        if (v.size()!=32) return false;
        for (char c:v) if (!((c>='0' && c<='9') || (c>='a' && c<='f'))) return false;
        return true;
    }
    std::string path(const char *name) const { return directory+"\\"+name; }
    static ULONGLONG process_creation(Session &owner) {
        FILETIME created={},exited={},kernel={},user={};
        if (!GetProcessTimes(owner.process,&created,&exited,&kernel,&user))
            throw std::runtime_error("lease retained process times unavailable");
        return (static_cast<ULONGLONG>(created.dwHighDateTime)<<32)|created.dwLowDateTime;
    }
    void verify_owner() const {
        if (!s.process || !s.primary_thread || WaitForSingleObject(s.process,0)!=WAIT_TIMEOUT ||
            WaitForSingleObject(s.primary_thread,0)!=WAIT_TIMEOUT ||
            GetProcessId(s.process)!=s.owned_pid || GetThreadId(s.primary_thread)!=s.primary_tid ||
            GetProcessIdOfThread(s.primary_thread)!=s.owned_pid || process_creation(s)!=creation_filetime)
            throw std::runtime_error("lease retained process or primary thread identity changed");
    }
    bool read_file(const char *name,std::string &result,bool allow_missing=false) const {
        LeaseHandle file(CreateFileA(path(name).c_str(),GENERIC_READ,
            FILE_SHARE_READ|FILE_SHARE_WRITE|FILE_SHARE_DELETE,nullptr,OPEN_EXISTING,
            FILE_ATTRIBUTE_NORMAL|FILE_FLAG_OPEN_REPARSE_POINT,nullptr));
        if (file.value==INVALID_HANDLE_VALUE) {
            if (allow_missing && GetLastError()==ERROR_FILE_NOT_FOUND) return false;
            throw std::runtime_error("lease control file unavailable");
        }
        BY_HANDLE_FILE_INFORMATION info={};
        if (GetFileType(file.value)!=FILE_TYPE_DISK || !GetFileInformationByHandle(file.value,&info) ||
            (info.dwFileAttributes&(FILE_ATTRIBUTE_DIRECTORY|FILE_ATTRIBUTE_REPARSE_POINT)) ||
            info.nFileSizeHigh || info.nFileSizeLow>256)
            throw std::runtime_error("lease control file type or bound rejected");
        char bytes[256]={}; DWORD got=0;
        if (!ReadFile(file.value,bytes,sizeof(bytes),&got,nullptr) || got!=info.nFileSizeLow)
            throw std::runtime_error("lease control file changed or read failed");
        result.assign(bytes,got); return true;
    }
    void verify_token() const {
        std::string token; read_file("session.token",token);
        if (token!=session+"\n") throw std::runtime_error("lease session token changed");
    }
    static void absent_or_regular(const std::string &name,bool must_be_absent) {
        DWORD attrs=GetFileAttributesA(name.c_str());
        if (attrs==INVALID_FILE_ATTRIBUTES) {
            if (GetLastError()==ERROR_FILE_NOT_FOUND) return;
            throw std::runtime_error("lease acknowledgment path unavailable");
        }
        if (must_be_absent || (attrs&(FILE_ATTRIBUTE_DIRECTORY|FILE_ATTRIBUTE_REPARSE_POINT)))
            throw std::runtime_error("lease acknowledgment path already used or redirected");
    }
    PauseLeaseController(Session &owner,const char *control_directory,ULONG base):s(owner),image_base(base) {
        if (!control_directory) return;
        enabled=true; directory=control_directory;
        if (directory.size()<3 || directory.size()>MAX_PATH-32 ||
            !((directory[0]>='A' && directory[0]<='Z') || (directory[0]>='a' && directory[0]<='z')) ||
            directory[1]!=':' || (directory[2]!='\\' && directory[2]!='/'))
            throw std::runtime_error("lease directory requires a bounded absolute local path");
        for (unsigned char c:directory) if (c<32 || c>126)
            throw std::runtime_error("lease directory must be ASCII");
        directory_handle.value=CreateFileA(directory.c_str(),GENERIC_READ,FILE_SHARE_READ|FILE_SHARE_WRITE,
            nullptr,OPEN_EXISTING,FILE_FLAG_BACKUP_SEMANTICS|FILE_FLAG_OPEN_REPARSE_POINT,nullptr);
        BY_HANDLE_FILE_INFORMATION info={};
        if (directory_handle.value==INVALID_HANDLE_VALUE ||
            !GetFileInformationByHandle(directory_handle.value,&info) ||
            !(info.dwFileAttributes&FILE_ATTRIBUTE_DIRECTORY) || (info.dwFileAttributes&FILE_ATTRIBUTE_REPARSE_POINT))
            throw std::runtime_error("lease control directory unavailable or redirected");
        std::string token; read_file("session.token",token);
        if (token.size()!=33 || token.back()!='\n' || !hex_token(token.substr(0,32)))
            throw std::runtime_error("lease session token grammar rejected");
        session=token.substr(0,32);
        absent_or_regular(path("ack.json"),true); absent_or_regular(path("ack.json.tmp"),true);
        creation_filetime=process_creation(s); verify_owner();
    }
    void ack(const char *status,const std::string &lease,ULONGLONG deadline,bool paused) const {
        verify_token(); verify_owner(); absent_or_regular(path("ack.json"),false);
        char json[1024];
        int count=sprintf_s(json,
            "{\"schema\":\"clash95_debug_pause_ack_v1\",\"session_id\":\"%s\",\"request_seq\":%llu,"
            "\"status\":\"%s\",\"lease_id\":\"%s\",\"pid\":%lu,\"primary_tid\":%lu,"
            "\"creation_filetime\":%llu,\"image_base\":%lu,\"deadline_tick_ms\":%llu,\"paused\":%s}\n",
            session.c_str(),last_sequence,status,lease.c_str(),s.owned_pid,s.primary_tid,
            creation_filetime,image_base,deadline,paused?"true":"false");
        if (count<0) throw std::runtime_error("lease acknowledgment encoding failed");
        LeaseHandle temporary(CreateFileA(path("ack.json.tmp").c_str(),GENERIC_WRITE,0,nullptr,
            CREATE_NEW,FILE_ATTRIBUTE_NORMAL|FILE_FLAG_WRITE_THROUGH,nullptr));
        DWORD written=0;
        if (temporary.value==INVALID_HANDLE_VALUE ||
            !WriteFile(temporary.value,json,static_cast<DWORD>(count),&written,nullptr) ||
            written!=static_cast<DWORD>(count) || !FlushFileBuffers(temporary.value))
            throw std::runtime_error("lease acknowledgment write failed");
        temporary.close();
        if (!MoveFileExA(path("ack.json.tmp").c_str(),path("ack.json").c_str(),
            MOVEFILE_REPLACE_EXISTING|MOVEFILE_WRITE_THROUGH))
            throw std::runtime_error("lease acknowledgment atomic replace failed");
    }
    void publish_ready(bool entered) {
        if (!enabled || ready_published || !entered) return;
        ULONG status=0; check(s.control->GetExecutionStatus(&status),"lease ready execution status");
        if (status!=DEBUG_STATUS_GO) throw std::runtime_error("lease ready requires resumed entry");
        fflush(stdout);
        ack("ready","",0,false); ready_published=true;
    }
    bool request(LeaseRequest &result) const {
        verify_token();
        std::string wire; if (!read_file("request.txt",wire,last_sequence==0)) return false;
        std::vector<std::string> fields; size_t start=0;
        if (wire.empty() || wire.back()!='\n') throw std::runtime_error("lease request line rejected");
        for (size_t i=0;i<wire.size();++i) {
            char c=wire[i];
            if (c==' ' || (c=='\n' && i==wire.size()-1)) {
                if (i==start) throw std::runtime_error("lease request empty token rejected");
                fields.push_back(wire.substr(start,i-start)); start=i+1;
            } else if (c<33 || c>126) throw std::runtime_error("lease request non-ASCII token rejected");
        }
        if (fields.size()!=5 || fields[0]!="CLASH_LEASE_V1" || fields[1]!=session ||
            (fields[3]!="pause" && fields[3]!="resume") || !hex_token(fields[4]) ||
            fields[2].empty() || fields[2][0]=='0')
            throw std::runtime_error("lease request grammar or session rejected");
        ULONGLONG sequence=0,maximum=~static_cast<ULONGLONG>(0);
        for (char c:fields[2]) {
            if (c<'0' || c>'9' || sequence>(maximum-static_cast<unsigned>(c-'0'))/10)
                throw std::runtime_error("lease request sequence rejected");
            sequence=sequence*10+static_cast<unsigned>(c-'0');
        }
        if (sequence==last_sequence) {
            if (wire!=last_wire) throw std::runtime_error("lease request changed without a new sequence");
            return false;
        }
        if (last_sequence==maximum || sequence!=last_sequence+1)
            throw std::runtime_error("lease request stale or skipped sequence");
        result.sequence=sequence; result.operation=fields[3]; result.lease=fields[4]; result.wire=wire;
        return true;
    }
    void accept(const LeaseRequest &r) { last_sequence=r.sequence; last_wire=r.wire; }
    void verify_native_break() const {
        ULONG type=0,process=0,thread=0,used=0,description_used=0,owned_process=0,primary=0;
        DEBUG_LAST_EVENT_INFO_EXCEPTION event={}; char description[1024]={};
        check(s.control->GetLastEventInformation(&type,&process,&thread,&event,sizeof(event),&used,
            description,sizeof(description),&description_used),"lease native break event identity");
        check(s.system->GetProcessIdBySystemId(s.owned_pid,&owned_process),"lease event owned process");
        check(s.system->GetThreadIdBySystemId(s.primary_tid,&primary),"lease event retained primary");
        ULONG64 native_break=0;
        check(s.symbols->GetOffsetByName("ntdll!DbgBreakPoint",&native_break),"lease native break export");
        if (type!=DEBUG_EVENT_EXCEPTION || used!=sizeof(event) || process!=owned_process ||
            thread==primary || !event.FirstChance || event.ExceptionRecord.ExceptionCode!=EXCEPTION_BREAKPOINT ||
            event.ExceptionRecord.ExceptionAddress!=native_break)
            throw std::runtime_error("lease pause received an unexpected queued debugger event");
        select_owned_primary(s);
    }
    static void check_deadline(ULONGLONG deadline) {
        if (GetTickCount64()>=deadline) throw std::runtime_error("lease expired; owned target must terminate");
    }
    void service() {
        if (!enabled || !ready_published) return;
        LeaseRequest initial; if (!request(initial)) return;
        if (initial.operation!="pause") throw std::runtime_error("lease resume without a held pause");
        for (const auto &old:used_leases) if (old==initial.lease)
            throw std::runtime_error("lease token reused");
        if (used_leases.size()>=1024) throw std::runtime_error("lease session request bound exceeded");
        verify_owner(); pause_owned(s); verify_native_break();
        ULONGLONG deadline=GetTickCount64()+20000;
        used_leases.push_back(initial.lease); accept(initial); ack("paused",initial.lease,deadline,true);
        // This owns the event loop until explicit, matching resume or failure.
        // No periodic snapshot, WaitForEvent, native command, or input runs here.
        for (;;) {
            check_deadline(deadline); verify_owner();
            LeaseRequest next;
            if (request(next)) {
                if (next.operation!="resume" || next.lease!=initial.lease)
                    throw std::runtime_error("lease requires its matching next resume request");
                select_owned_primary(s); verify_owner(); check_deadline(deadline);
                check(s.control->SetExecutionStatus(DEBUG_STATUS_GO),"lease explicit resume");
                accept(next); ack("resumed",initial.lease,0,false); return;
            }
            Sleep(10);
        }
    }
};
'''

_SNAPSHOT = 'static void snapshot(Session &s,const std::string &out,int sample,bool proxy) {\n'
_ARGUMENTS = '    if (argc!=5) return 2;\n'
_LOADED = ('        printf("REAL_LOADED pid=%lu base=%08lx entry=%08lx executable_sections_match=1\\n",'
           'pid,base,entry); fflush(stdout);\n')
_CONTINUE = '                check(s.control->SetExecutionStatus(DEBUG_STATUS_GO),"continue actual code");\n'
_WAIT = '            HRESULT hr=s.control->WaitForEvent(0,1000);\n'

SOURCE_REPLACEMENTS = (
    (_SNAPSHOT, CONTROLLER_SOURCE + _SNAPSHOT),
    (_ARGUMENTS, '    if (argc!=5 && argc!=6) return 2;\n'),
    (_LOADED, _LOADED + '        PauseLeaseController leases(s,argc==6?argv[5]:nullptr,base);\n'),
    (_CONTINUE, _CONTINUE + '                leases.publish_ready(entered);\n'),
    (_WAIT, '            leases.service();\n' + _WAIT),
)


def render_source(base_source: str) -> str:
    """Apply only the known source anchors, exactly once, or reject the input."""
    if not isinstance(base_source, str):
        raise TypeError('Harness source must be text')
    if 'PauseLeaseController' in base_source:
        raise ValueError('Harness already contains a pause lease controller')
    for old, _new in SOURCE_REPLACEMENTS:
        if base_source.count(old) != 1:
            raise ValueError('Harness source anchor missing or duplicated: ' + old.splitlines()[0])
    for old, new in SOURCE_REPLACEMENTS:
        base_source = base_source.replace(old, new, 1)
    return base_source
