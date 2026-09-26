"""Explicit native human-loop phase control, composed after the pause host.

This source transform launches nothing. The optional seventh process argument
``native-phase-v1`` enables a separate mailbox. The controller observes native
40B0A0 -> 40B0D4 -> 40B233 before holding the original caller frame. A click
changes only cursor X/Y and the resolved left-button DWORD, executes the
original CALL, and observes its predicate and return. It never injects a call
or changes EIP, ESP, selection, movement state, or a predicate result.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

MODE = 'native-phase-v1'
ACK_SCHEMA = 'clash95_native_phase_ack_v1'
REQUEST_PREFIX = 'CLASH_PHASE_V1'
LEASE_MS = 20_000

# These spans exclude the patched minimap CALL at 4084A9. Relative CALL/JMP
# encodings survive rebasing. All are checked before any phase breakpoint.
NATIVE_ANCHORS = {
    0x40B0A0: '53515256575583ec04e832a8030031d2e8eba80300',
    0x40B0CF: 'e8fc540500',
    0x40B0D4: '89e8e845caffffe810fdffffe82b2b0000e8c637000085c0',
    0x40B233: 'e868d2ffff',
    0x40B238: 'e9dcfeffff',
    0x4084A0: '53515256575583ec58',
    0x4087DC: 'e80f810500',
    0x4087E1: '85c00f851a070000',
    0x4608F0: 'f6402c010f95c025ff000000c3',
}

CONTROLLER_SOURCE = r'''
static void snapshot(Session &s,const std::string &out,int sample,bool proxy);
struct PhaseRequest {
    ULONGLONG sequence=0;
    std::string operation,lease,successor,binding,wire;
    ULONG x=0,y=0;
};
struct NativePhaseController {
    enum State { Idle, AwaitPostpoll, AwaitCaller, Held, AwaitDispatch, AwaitPredicateOrReturn };
    PauseLeaseController &owner;
    Session &s;
    bool enabled=false,ready_published=false,proxy=false,human_entry_seen=false,postpoll_seen=false;
    bool after_action=false,dispatch_seen=false,predicate_observed=false,return_seen=false;
    bool first_human_acquire_waited=false;
    State state=Idle;
    ULONGLONG last_sequence=0,transition_deadline=0,held_deadline=0;
    ULONG root_esp=0,held_esp=0,held_eip=0,action_index=0,target_x=0,target_y=0;
    ULONG dispatch_eip=0,dispatch_esp=0,dispatch_return=0,predicate_value=0,return_eip=0,return_esp=0;
    ULONG raw_x=0,raw_y=0;
    int capture_index=-1;
    std::string out,last_wire,current_lease,pending_lease,binding_sha256;
    std::vector<std::string> used_leases;
    IDebugBreakpoint *human_bp=nullptr,*phase_bp=nullptr,*return_bp=nullptr;
    ULONG human_id=DEBUG_ANY_ID,phase_id=DEBUG_ANY_ID,return_id=DEBUG_ANY_ID;
    static const char *source_sha256() { return "@PHASE_SOURCE_SHA256@"; }

    static bool hex(const std::string &v,size_t count) {
        if (v.size()!=count) return false;
        for (char c:v) if (!((c>='0' && c<='9') || (c>='a' && c<='f'))) return false;
        return true;
    }
    static ULONGLONG number(const std::string &v,bool nonzero) {
        if (v.empty() || (v.size()>1 && v[0]=='0') || (nonzero && v=="0"))
            throw std::runtime_error("phase noncanonical integer");
        ULONGLONG value=0,maximum=~static_cast<ULONGLONG>(0);
        for (char c:v) {
            if (c<'0' || c>'9' || value>(maximum-static_cast<unsigned>(c-'0'))/10)
                throw std::runtime_error("phase integer rejected");
            value=value*10+static_cast<unsigned>(c-'0');
        }
        return value;
    }
    ULONG address(ULONG original) const { return owner.image_base+(original-0x400000); }
    ULONG word(ULONG original) { return s.word(address(original)); }
    ULONG stack() const {
        ULONG64 value=0; check(s.registers->GetStackOffset(&value),"phase read ESP");
        if (value<0x10000 || value>=0x7ffe0000 || (value&3)) throw std::runtime_error("phase ESP out of bounds or unaligned");
        return static_cast<ULONG>(value);
    }
    ULONG eax() const {
        ULONG index=0; DEBUG_VALUE value={};
        check(s.registers->GetIndexByName("eax",&index),"phase EAX index");
        check(s.registers->GetValue(index,&value),"phase read EAX");
        if (value.Type!=DEBUG_VALUE_INT32) throw std::runtime_error("phase non-x86 EAX");
        return value.I32;
    }
    static void deadline(ULONGLONG until) {
        if (!until || GetTickCount64()>=until)
            throw std::runtime_error("native phase expired; owned target must terminate");
    }
    void require_frame() {
        owner.verify_owner(); select_owned_primary(s);
        if (!human_entry_seen || root_esp<0x10020 || stack()!=root_esp-28)
            throw std::runtime_error("phase did not retain the native human caller frame");
    }
    void trace_view(const char *phase) {
        owner.verify_owner();
        ULONG gd=word(0x5202E4);
        if (gd<0x10000 || gd>0x7ffe0000-140016) throw std::runtime_error("phase camera GD bounds rejected");
        LONG x=static_cast<LONG>(s.word(gd+140008)),y=static_cast<LONG>(s.word(gd+140012));
        auto shift=s.read(address(0x54512C),1)[0];
        ULONG resolved=word(0x544D04),primary=s.read(address(0x5451C0),1)[0],secondary=s.read(address(0x5451C8),1)[0];
        ULONG extent=word(0x51D4C0);
        printf("REAL_PHASE_VIEW phase=%s gd=%08lx scroll_x=%ld scroll_y=%ld raw_x=%lu raw_y=%lu shift=%u extent=%08lx width=%lu height=%lu resolved=%08lx primary=%02lx secondary=%02lx\n",
            phase,gd,x,y,word(0x544CFC),word(0x544D00),static_cast<unsigned>(shift),extent,extent&0xffff,extent>>16,
            resolved,primary,secondary); fflush(stdout);
    }
    void clear_bp(IDebugBreakpoint *&bp,ULONG &id) {
        // RemoveBreakpoint invalidates the object even though it exposes IUnknown.
        auto *removed=bp; bp=nullptr; id=DEBUG_ANY_ID;
        if (removed) check(s.control->RemoveBreakpoint(removed),"remove owned phase breakpoint");
    }
    void arm(IDebugBreakpoint *&bp,ULONG &id,ULONG original) {
        clear_bp(bp,id);
        ULONG primary=0;
        check(s.system->GetThreadIdBySystemId(s.primary_tid,&primary),"phase retained thread id");
        check(s.control->AddBreakpoint(DEBUG_BREAKPOINT_DATA,DEBUG_ANY_ID,&bp),"add owned phase hardware breakpoint");
        check(bp->SetDataParameters(1,DEBUG_BREAK_EXECUTE),"phase hardware execute only");
        check(bp->SetOffset(address(original)),"phase native breakpoint address");
        check(bp->SetMatchThreadId(primary),"phase breakpoint retained primary thread");
        check(bp->GetId(&id),"phase breakpoint identity");
        check(bp->AddFlags(DEBUG_BREAKPOINT_ENABLED),"enable owned phase breakpoint");
    }
    void go() { owner.verify_owner(); check(s.control->SetExecutionStatus(DEBUG_STATUS_GO),"continue natural phase"); }
    void anchor(ULONG original,const unsigned char *expected,size_t size) {
        auto actual=s.read(address(original),static_cast<ULONG>(size));
        if (memcmp(actual.data(),expected,size)) throw std::runtime_error("native phase byte anchor differs");
    }
    void verify_anchors() {
@PHASE_ANCHORS@
    }
    NativePhaseController(PauseLeaseController &parent,const char *mode,const std::string &output,bool use_proxy):owner(parent),s(parent.s),proxy(use_proxy),out(output) {
        if (!mode) return;
        if (strcmp(mode,"native-phase-v1") || !owner.enabled) throw std::runtime_error("explicit native phase mode rejected");
        enabled=true;
        owner.verify_token(); owner.verify_owner(); verify_anchors();
        owner.absent_or_regular(owner.path("phase-ack.json"),true);
        owner.absent_or_regular(owner.path("phase-ack.json.tmp"),true);
        // Armed before startup can enter the human loop. Software startup
        // breakpoints remain separately owned; only one DR slot is used here.
        arm(human_bp,human_id,0x40B0A0);
    }
    ~NativePhaseController() {
        for (auto bp:{human_bp,phase_bp,return_bp}) if (bp) s.control->RemoveBreakpoint(bp);
    }
    void remember(const std::string &lease) {
        if (!hex(lease,32) || used_leases.size()>=1024) throw std::runtime_error("phase lease token or count rejected");
        for (const auto &old:used_leases) if (old==lease) throw std::runtime_error("phase lease token reused");
        used_leases.push_back(lease);
    }
    bool request(PhaseRequest &result) const {
        owner.verify_token();
        std::string wire; if (!owner.read_file("phase-request.txt",wire,last_sequence==0)) return false;
        std::vector<std::string> fields; size_t start=0;
        if (wire.empty() || wire.back()!='\n') throw std::runtime_error("phase request line rejected");
        for (size_t i=0;i<wire.size();++i) {
            char c=wire[i];
            if (c==' ' || (c=='\n' && i==wire.size()-1)) {
                if (i==start) throw std::runtime_error("phase request empty token");
                fields.push_back(wire.substr(start,i-start)); start=i+1;
            } else if (c<33 || c>126) throw std::runtime_error("phase request non-ASCII token");
        }
        if (fields.size()<5 || fields[0]!="CLASH_PHASE_V1" || fields[1]!=owner.session || !hex(fields[4],32))
            throw std::runtime_error("phase request grammar or session rejected");
        ULONGLONG seq=number(fields[2],true);
        if (seq==last_sequence) {
            if (wire!=last_wire) throw std::runtime_error("phase request changed without new sequence");
            return false;
        }
        if (last_sequence==~static_cast<ULONGLONG>(0) || seq!=last_sequence+1)
            throw std::runtime_error("phase stale or skipped sequence");
        if (fields[3]=="click") {
            if (fields.size()!=9 || !hex(fields[5],32) || !hex(fields[8],64))
                throw std::runtime_error("phase click grammar rejected");
            ULONGLONG x=number(fields[6],false),y=number(fields[7],false);
            if (x>=3840 || y>=2160) throw std::runtime_error("phase click point out of bounds");
            result.successor=fields[5]; result.x=static_cast<ULONG>(x); result.y=static_cast<ULONG>(y); result.binding=fields[8];
        } else if (fields.size()!=5 || (fields[3]!="acquire" && fields[3]!="release"))
            throw std::runtime_error("phase operation rejected");
        result.sequence=seq; result.operation=fields[3]; result.lease=fields[4]; result.wire=wire; return true;
    }
    void accept(const PhaseRequest &r) { last_sequence=r.sequence; last_wire=r.wire; }
    void reject_mixed_mailbox() const {
        std::string ignored;
        if (owner.read_file("request.txt",ignored,true)) throw std::runtime_error("generic pause requests forbidden in native phase mode");
    }
    void ack(const char *status,const char *phase,const std::string &lease,ULONGLONG until,bool paused) const {
        owner.verify_token(); owner.verify_owner();
        owner.absent_or_regular(owner.path("phase-ack.json"),false);
        char json[4096];
        int count=sprintf_s(json,
            "{\"schema\":\"clash95_native_phase_ack_v1\",\"session_id\":\"%s\",\"request_seq\":%llu,"
            "\"status\":\"%s\",\"lease_id\":\"%s\",\"pid\":%lu,\"primary_tid\":%lu,"
            "\"creation_filetime\":%llu,\"image_base\":%lu,\"deadline_tick_ms\":%llu,\"paused\":%s,"
            "\"phase\":\"%s\",\"controller_sha256\":\"%s\",\"root_esp\":%lu,\"held_esp\":%lu,\"held_eip\":%lu,"
            "\"human_entry_seen\":%s,\"postpoll_seen\":%s,\"action_index\":%lu,\"capture_index\":%d,"
            "\"binding_sha256\":\"%s\",\"target_x\":%lu,\"target_y\":%lu,"
            "\"dispatch_seen\":%s,\"dispatch_eip\":%lu,\"dispatch_esp\":%lu,\"dispatch_return\":%lu,"
            "\"predicate_observed\":%s,\"predicate_value\":%lu,\"return_seen\":%s,\"return_eip\":%lu,\"return_esp\":%lu}\n",
            owner.session.c_str(),last_sequence,status,lease.c_str(),s.owned_pid,s.primary_tid,
            owner.creation_filetime,owner.image_base,until,paused?"true":"false",phase,source_sha256(),root_esp,held_esp,held_eip,
            human_entry_seen?"true":"false",postpoll_seen?"true":"false",action_index,capture_index,binding_sha256.c_str(),target_x,target_y,
            dispatch_seen?"true":"false",dispatch_eip,dispatch_esp,dispatch_return,predicate_observed?"true":"false",predicate_value,
            return_seen?"true":"false",return_eip,return_esp);
        if (count<0) throw std::runtime_error("phase acknowledgment encoding failed");
        LeaseHandle temporary(CreateFileA(owner.path("phase-ack.json.tmp").c_str(),GENERIC_WRITE,0,nullptr,
            CREATE_NEW,FILE_ATTRIBUTE_NORMAL|FILE_FLAG_WRITE_THROUGH,nullptr));
        DWORD written=0;
        if (temporary.value==INVALID_HANDLE_VALUE || !WriteFile(temporary.value,json,static_cast<DWORD>(count),&written,nullptr) ||
            written!=static_cast<DWORD>(count) || !FlushFileBuffers(temporary.value))
            throw std::runtime_error("phase acknowledgment write failed");
        temporary.close();
        if (!MoveFileExA(owner.path("phase-ack.json.tmp").c_str(),owner.path("phase-ack.json").c_str(),
            MOVEFILE_REPLACE_EXISTING|MOVEFILE_WRITE_THROUGH)) throw std::runtime_error("phase acknowledgment atomic replace failed");
    }
    void publish_ready(bool entered) {
        if (!enabled || ready_published || !entered) return;
        if (!owner.ready_published) throw std::runtime_error("phase readiness precedes owned entry readiness");
        reject_mixed_mailbox(); fflush(stdout); ack("ready","ready","",0,false); ready_published=true;
    }
    void reset_trace() {
        dispatch_seen=predicate_observed=return_seen=false;
        dispatch_eip=dispatch_esp=dispatch_return=predicate_value=return_eip=return_esp=0;
    }
    void accept_acquire(const PhaseRequest &next) {
        if (state!=Idle || next.operation!="acquire") throw std::runtime_error("phase request outside idle acquisition");
        remember(next.lease); accept(next); current_lease=next.lease; pending_lease.clear();
        reset_trace(); binding_sha256.clear(); target_x=target_y=0; after_action=false; postpoll_seen=false;
        transition_deadline=GetTickCount64()+20000;
    }
    void await_first_acquire() {
        if (!ready_published || first_human_acquire_waited || state!=Idle || !human_entry_seen)
            throw std::runtime_error("phase first human acquisition boundary differs");
        first_human_acquire_waited=true;
        ULONGLONG until=GetTickCount64()+20000;
        // Keep the first natural human-entry event stopped. This is not a read
        // lease; only the subsequent observed postpoll/caller grants one.
        for (;;) {
            deadline(until); owner.verify_owner(); reject_mixed_mailbox();
            PhaseRequest next;
            if (request(next)) {
                deadline(until); accept_acquire(next);
                arm(phase_bp,phase_id,0x40B0D4); state=AwaitPostpoll; go(); return;
            }
            Sleep(10);
        }
    }
    void service() {
        if (!enabled || !ready_published) return;
        owner.verify_owner(); reject_mixed_mailbox();
        if (state!=Idle) deadline(transition_deadline);
        // Startup first-chance exceptions must stay on the ordinary event path.
        // Even a queued acquire is consumed only at the first human entry.
        if (!human_entry_seen) return;
        PhaseRequest next; if (!request(next)) return;
        accept_acquire(next);
        // The generic native-break identity contract is reused unchanged only
        // to arm a breakpoint. It cannot authorize a phase read or click.
        pause_owned(s); owner.verify_native_break(); deadline(transition_deadline);
        arm(phase_bp,phase_id,0x40B0D4); state=AwaitPostpoll; go();
    }
    void write_input(ULONG original,ULONG expected,ULONG value) {
        if (original!=0x544CFC && original!=0x544D00 && original!=0x544D04)
            throw std::runtime_error("phase write outside three controlled input fields");
        if (word(original)!=expected) throw std::runtime_error("phase input old bytes changed");
        ULONG written=0; check(s.memory->WriteVirtual(address(original),&value,4,&written),"phase controlled input DWORD");
        if (written!=4 || word(original)!=value) throw std::runtime_error("phase input write/readback failed");
    }
    void ordinary_owner() {
        if (word(0x5199D8)!=address(0x40AD40) || !word(0x527C24) || word(0x52698C) ||
            word(0x526990) || word(0x5202E8) || word(0x526994)>1)
            throw std::runtime_error("phase ordinary map owner differs");
    }
    void click(const PhaseRequest &next) {
        require_frame(); ordinary_owner(); deadline(held_deadline);
        ULONG extent=word(0x51D4C0),width=extent&0xffff,height=extent>>16;
        auto shift=s.read(address(0x54512C),1)[0];
        ULONG resolved=word(0x544D04),primary=s.read(address(0x5451C0),1)[0],secondary=s.read(address(0x5451C8),1)[0];
        // Compute diagnostics only for a defined shift; invalid shifts still reject below.
        ULONGLONG x=shift<=31?static_cast<ULONGLONG>(next.x)<<shift:0;
        ULONGLONG y=shift<=31?static_cast<ULONGLONG>(next.y)<<shift:0;
        printf("REAL_PHASE_PRECLICK action=%lu target_x=%lu target_y=%lu shift=%u extent=%08lx width=%lu height=%lu raw_target_valid=%d raw_target_x=%llu raw_target_y=%llu resolved=%08lx primary=%02lx secondary=%02lx\n",
            action_index+1,next.x,next.y,static_cast<unsigned>(shift),extent,width,height,shift<=31,x,y,resolved,primary,secondary); fflush(stdout);
        if (width<640 || width>3840 || height<480 || height>2160 || next.x>=width || next.y>=height || shift>21)
            throw std::runtime_error("phase measured input extent or shift rejected");
        if (x>0x7fffffff || y>0x7fffffff || resolved!=0 || (primary&0x80) || (secondary&0x80))
            throw std::runtime_error("phase cursor overflow or existing native button input");
        ULONG previous_x=word(0x544CFC),previous_y=word(0x544D00);
        remember(next.successor); pending_lease=next.successor; accept(next);
        current_lease.clear(); binding_sha256=next.binding; target_x=next.x; target_y=next.y;
        raw_x=static_cast<ULONG>(x); raw_y=static_cast<ULONG>(y); reset_trace(); ++action_index;
        ack("executing","executing","",0,false); deadline(held_deadline);
        write_input(0x544CFC,previous_x,raw_x); write_input(0x544D00,previous_y,raw_y); write_input(0x544D04,0,1);
        deadline(held_deadline); arm(phase_bp,phase_id,0x4084A0);
        transition_deadline=GetTickCount64()+20000; held_deadline=0; state=AwaitDispatch; go();
    }
    void hold() {
        require_frame(); ordinary_owner(); deadline(transition_deadline);
        trace_view("caller-hold");
        held_eip=address(0x40B233); held_esp=stack();
        if (!postpoll_seen) throw std::runtime_error("phase caller reached without observed postpoll");
        if (after_action) { current_lease=pending_lease; pending_lease.clear(); }
        if (current_lease.empty()) throw std::runtime_error("phase hold has no one-use lease");
        state=Held; capture_index=100+static_cast<int>(action_index)*2;
        snapshot(s,out,capture_index,proxy);
        require_frame(); ordinary_owner(); deadline(transition_deadline);
        held_deadline=GetTickCount64()+20000;
        ack("held",after_action?"predispatch-after":"predispatch-before",current_lease,held_deadline,true);
        for (;;) {
            deadline(held_deadline); owner.verify_owner(); reject_mixed_mailbox();
            PhaseRequest next;
            if (request(next)) {
                if (next.lease!=current_lease) throw std::runtime_error("phase request has a different held lease");
                if (next.operation=="click") { click(next); return; }
                if (next.operation!="release") throw std::runtime_error("phase held operation rejected");
                require_frame(); deadline(held_deadline); accept(next); current_lease.clear(); held_deadline=0;
                state=Idle; go(); ack("released","released","",0,false); return;
            }
            Sleep(10);
        }
    }
    bool on_event(ULONG type,ULONG process,ULONG thread,ULONG64 ip) {
        if (!enabled) return false;
        if (type!=DEBUG_EVENT_BREAKPOINT) {
            if (state!=Idle) throw std::runtime_error("unexpected event during native phase transition");
            return false;
        }
        DEBUG_LAST_EVENT_INFO_BREAKPOINT event={}; ULONG actual_type=0,actual_process=0,actual_thread=0,used=0,description_used=0;
        char description[1024]={};
        check(s.control->GetLastEventInformation(&actual_type,&actual_process,&actual_thread,&event,sizeof(event),&used,
            description,sizeof(description),&description_used),"phase breakpoint event identity");
        bool human=event.Id==human_id,phase=phase_bp && event.Id==phase_id,returned=return_bp && event.Id==return_id;
        if (!human && !phase && !returned) {
            if (state!=Idle) throw std::runtime_error("unowned breakpoint during native phase transition");
            return false;
        }
        ULONG owned_process=0,primary=0;
        check(s.system->GetProcessIdBySystemId(s.owned_pid,&owned_process),"phase event process");
        check(s.system->GetThreadIdBySystemId(s.primary_tid,&primary),"phase event primary thread");
        if (used!=sizeof(event) || actual_type!=type || actual_process!=process || actual_thread!=thread ||
            process!=owned_process || thread!=primary) throw std::runtime_error("phase event owner mismatch");
        owner.verify_owner(); select_owned_primary(s);
        if (human) {
            if (ip!=address(0x40B0A0) || state!=Idle)
                throw std::runtime_error("unexpected human-loop reentry during phase");
            bool first=!human_entry_seen;
            root_esp=stack(); human_entry_seen=true;
            trace_view("human-entry");
            printf("REAL_PHASE_HUMAN pid=%lu tid=%lu eip=%08llx root_esp=%08lx\n",s.owned_pid,s.primary_tid,ip,root_esp); fflush(stdout);
            if (first) { await_first_acquire(); return true; }
            go(); return true;
        }
        deadline(transition_deadline);
        if (phase && state==AwaitPostpoll && ip==address(0x40B0D4)) {
            require_frame(); postpoll_seen=true;
            clear_bp(phase_bp,phase_id); arm(phase_bp,phase_id,0x40B233); state=AwaitCaller; go(); return true;
        }
        if (phase && state==AwaitCaller && ip==address(0x40B233)) {
            clear_bp(phase_bp,phase_id); hold(); return true;
        }
        if (phase && state==AwaitDispatch && ip==address(0x4084A0)) {
            if (stack()!=root_esp-32 || s.word(stack())!=address(0x40B238) ||
                word(0x544CFC)!=raw_x || word(0x544D00)!=raw_y || word(0x544D04)!=1)
                throw std::runtime_error("phase natural dispatch caller or controlled input differs");
            dispatch_seen=true; dispatch_eip=static_cast<ULONG>(ip); dispatch_esp=stack(); dispatch_return=s.word(dispatch_esp);
            clear_bp(phase_bp,phase_id); arm(phase_bp,phase_id,0x4087E1); arm(return_bp,return_id,0x40B238);
            state=AwaitPredicateOrReturn; go(); return true;
        }
        if (phase && state==AwaitPredicateOrReturn && ip==address(0x4087E1)) {
            if (!dispatch_seen || predicate_observed || stack()!=dispatch_esp-112 || s.word(dispatch_esp)!=dispatch_return)
                throw std::runtime_error("phase native predicate frame differs");
            predicate_value=eax();
            if (predicate_value>1 || (predicate_value==1 &&
                (word(0x544CFC)!=raw_x || word(0x544D00)!=raw_y || word(0x544D04)!=1)))
                throw std::runtime_error("phase native predicate input/result differs");
            predicate_observed=true; clear_bp(phase_bp,phase_id); go(); return true;
        }
        if (returned && state==AwaitPredicateOrReturn && ip==address(0x40B238)) {
            require_frame();
            if (!dispatch_seen || dispatch_return!=ip) throw std::runtime_error("phase native return has no matching dispatch");
            return_seen=true; return_eip=static_cast<ULONG>(ip); return_esp=stack();
            clear_bp(phase_bp,phase_id); clear_bp(return_bp,return_id);
            ULONG button=word(0x544D04);
            if (button>1) throw std::runtime_error("phase return has unrelated native button state");
            if (button==1) write_input(0x544D04,1,0);
            printf("REAL_PHASE_RETURN action=%lu caller=%08lx dispatch=%08lx dispatch_esp=%08lx predicate_seen=%d predicate=%lu return=%08lx return_esp=%08lx binding=%s\n",
                action_index,address(0x40B233),dispatch_eip,dispatch_esp,predicate_observed,predicate_value,return_eip,return_esp,binding_sha256.c_str()); fflush(stdout);
            after_action=true; postpoll_seen=false; arm(phase_bp,phase_id,0x40B0D4); state=AwaitPostpoll; go(); return true;
        }
        throw std::runtime_error("owned phase breakpoint violated expected native transition");
    }
    void finish() {
        if (enabled && state!=Idle) throw std::runtime_error("host interval ended during a native phase transaction");
    }
};
'''

_SNAPSHOT = 'static void snapshot(Session &s,const std::string &out,int sample,bool proxy) {\n'
_ARGUMENTS = '    if (argc!=5 && argc!=6) return 2;\n'
_CONSTRUCTOR = '        PauseLeaseController leases(s,argc==6?argv[5]:nullptr,base);\n'
_READY = '                leases.publish_ready(entered);\n'
_SERVICE = '            leases.service();\n'
_EVENT = '                if (ip==entry && !entered) { entered=true; printf("REAL_EXE_ENTRY observed=1\\n"); }\n'
_PERIODIC = '            if (GetTickCount64()>=next) {\n'
_FINISH = '        ULONG status=0; s.control->GetExecutionStatus(&status);\n'


def source_sha256() -> str:
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def source_replacements() -> tuple[tuple[str, str], ...]:
    checks = []
    for index, (address, hex_bytes) in enumerate(NATIVE_ANCHORS.items()):
        values = ','.join('0x'+hex_bytes[pos:pos+2] for pos in range(0, len(hex_bytes), 2))
        checks.append(f'        const unsigned char anchor_{index}[]={{'+values+'};')
        checks.append(f'        anchor(0x{address:06X},anchor_{index},sizeof(anchor_{index}));')
    controller = CONTROLLER_SOURCE.replace('@PHASE_ANCHORS@', '\n'.join(checks))
    controller = controller.replace('@PHASE_SOURCE_SHA256@', source_sha256())
    return (
        (_SNAPSHOT, controller+_SNAPSHOT),
        (_ARGUMENTS, '    if (argc!=5 && argc!=6 && argc!=7) return 2;\n'),
        (_CONSTRUCTOR, '        PauseLeaseController leases(s,argc>=6?argv[5]:nullptr,base);\n'
         '        NativePhaseController phases(leases,argc==7?argv[6]:nullptr,argv[2],strcmp(argv[4],"proxy")==0);\n'),
        (_READY, _READY+'                phases.publish_ready(entered);\n'),
        (_SERVICE, '            if (phases.enabled) phases.service(); else leases.service();\n'),
        (_EVENT, '                if (phases.on_event(type,proc,thread,ip)) continue;\n'+_EVENT),
        (_PERIODIC, '            if (!phases.enabled && GetTickCount64()>=next) {\n'),
        (_FINISH, '        phases.finish();\n'+_FINISH),
    )


def render_source(base_source: str) -> str:
    """Extend only an already transformed pause harness at exact source anchors."""
    if not isinstance(base_source, str):
        raise TypeError('Harness source must be text')
    if 'NativePhaseController' in base_source:
        raise ValueError('Harness already contains native phase control')
    if base_source.count('struct PauseLeaseController {') != 1:
        raise ValueError('Existing generic pause controller required')
    replacements = source_replacements()
    for old, _new in replacements:
        if base_source.count(old) != 1:
            raise ValueError('Native phase anchor missing or duplicated: '+old.splitlines()[0])
    for old, new in replacements:
        base_source = base_source.replace(old, new, 1)
    return base_source
