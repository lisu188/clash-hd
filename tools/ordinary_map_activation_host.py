"""Read-only native WM_ACTIVATEAPP/Acquire/Unacquire source observer.

Compose after the startup, pause and phase generators. One primary-thread
hardware execute breakpoint observes bounded native pairs, including events
before startup retirement. It never requests activation or changes input,
memory, registers, native control flow or existing phase acceptance.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

SCHEMA = 'clash95_native_activation_trace_v1'
MAX_TRANSACTIONS = 16
PENDING_MS = 20_000
ORIGINAL_SHA256 = '500055d77d03d514e8d3168506bd10f67cd8569bcc450604ff8192f46cdaf3ae'
# Original ASM/file bytes audited 2026-09-30. Both backend bodies execute
# mouse first, then keyboard, then the unsupported joystick branch.
NATIVE_ANCHORS = {
    0x4617C0: '535657558b7c24148b5c24188b74241c',
    0x461823: '31db6689f35368f40f5000e8ed78fbff83c40883fb01746e',
    0x461864: 'b898515400e812a70100833d9051540000',
    0x46189A: '891dd499510031c05d5f5e5bc21000',
    0x4618B6: 'b898515400e870a60100a17cd5510085c0',
    0x47BF30: '53515289c383b83401000000751f83bb380100000074098b4304508b10ff521c'
              '83bb3c01000000750f5a595bc38b4008508b10ff521cebd68b430c508b18ff531c5a595bc3',
    0x47BF80: '53515289c383b83401000000751f83bb380100000074098b4304508b10ff5220'
              '83bb3c01000000750f5a595bc38b4008508b10ff5220ebd68b430c508b18ff53205a595bc3',
}


def verify_original_anchors(data: bytes) -> dict[int, str]:
    """Authenticate the original read-only; runtime also checks candidate/loaded spans."""
    if type(data) is not bytes or hashlib.sha256(data).hexdigest() != ORIGINAL_SHA256:
        raise ValueError('Unknown original executable')
    from src.patcher.partial_tile_clip import file_offset
    for va, expected in NATIVE_ANCHORS.items():
        raw = bytes.fromhex(expected)
        offset = file_offset(data, va, len(raw))
        if data[offset:offset + len(raw)] != raw:
            raise ValueError(f'Original activation anchor differs at {va:08x}')
    return dict(NATIVE_ANCHORS)


CONTROLLER_SOURCE = r'''
// Diagnostic observer: only this single owned DR execute breakpoint is added.
struct NativeActivationController {
    enum Step { Activation, OuterCall, DeviceCall, DeviceReturn, OuterReturn, WndProcRet };
    PauseLeaseController &owner;
    Session &s;
    const bool *startup_retired;
    const std::vector<unsigned char> &disk;
    bool enabled=false,armed=false,finished=false,pending=false,seen_retired=false,outer_seen=false;
    IDebugBreakpoint *bp=nullptr;
    ULONG bp_id=DEBUG_ANY_ID,engine_process=0,engine_thread=0,target=0;
    Step step=Activation;
    ULONGLONG host_deadline=0,pending_deadline=0;
    ULONG tx=0,transactions=0,branch_esp=0,entry_esp=0,wndproc_return=0;
    ULONG hwnd=0,message=0,wparam=0,low=0,lparam=0,mouse_ready=0,keyboard_ready=0;
    ULONG device_index=0,device=0,vtable=0,method=0,last_hresult=0;
    std::vector<bool> devices; // true=mouse, false=keyboard; native execution order.
    static const char *source_sha256() { return "@ACTIVATION_SOURCE_SHA256@"; }
    ULONG address(ULONG native) const { return owner.image_base+(native-0x400000); }
    ULONG reg(const char *name) const {
        ULONG index=0; DEBUG_VALUE value={};
        check(s.registers->GetIndexByName(name,&index),"activation register index");
        check(s.registers->GetValue(index,&value),"activation register read");
        if(value.Type!=DEBUG_VALUE_INT32)throw std::runtime_error("activation requires x86 registers");
        return value.I32;
    }
    static bool pointer(ULONG value,ULONG span=4) {
        return value>=0x10000 && value<=0x7ffe0000-span && !(value&3);
    }
    void retained_context() const {
        owner.verify_token(); owner.verify_owner();
        ULONG status=0,pid=0,tid=0,process=0,thread=0;
        check(s.control->GetExecutionStatus(&status),"activation stopped status");
        check(s.system->GetCurrentProcessSystemId(&pid),"activation selected process");
        check(s.system->GetCurrentThreadSystemId(&tid),"activation selected thread");
        check(s.system->GetCurrentProcessId(&process),"activation engine process");
        check(s.system->GetCurrentThreadId(&thread),"activation engine thread");
        if(status!=DEBUG_STATUS_BREAK || pid!=s.owned_pid || tid!=s.primary_tid ||
           process!=engine_process || thread!=engine_thread)
            throw std::runtime_error("activation stopped retained context differs");
    }
    void verify_anchors() {
@ACTIVATION_ANCHORS@
    }
    void anchor(ULONG va,const char *hex) {
        auto expected=StartupController::decode(hex);
        if(StartupController::disk_read(disk,va,expected.size())!=expected ||
           s.read(address(va),static_cast<ULONG>(expected.size()))!=expected)
            throw std::runtime_error("activation candidate disk or loaded bytes differ");
    }
    NativeActivationController(PauseLeaseController &parent,const bool *retired,
        const std::vector<unsigned char> &candidate,bool use):owner(parent),s(parent.s),startup_retired(retired),disk(candidate),enabled(use) {
        if(!enabled)return;
        if(!owner.enabled || owner.image_base!=0x400000 || !startup_retired || *startup_retired)
            throw std::runtime_error("activation requires owned initial stop and genuine startup flag");
        owner.verify_token(); owner.verify_owner();
        check(s.system->GetProcessIdBySystemId(s.owned_pid,&engine_process),"activation owned engine process");
        check(s.system->GetThreadIdBySystemId(s.primary_tid,&engine_thread),"activation owned engine thread");
        retained_context(); verify_anchors();
    }
    ~NativeActivationController() {
        if(bp){auto *removed=bp;bp=nullptr;bp_id=DEBUG_ANY_ID;s.control->RemoveBreakpoint(removed);}
    }
    void clear() {
        if(bp){auto *removed=bp;bp=nullptr;bp_id=DEBUG_ANY_ID;
            check(s.control->RemoveBreakpoint(removed),"activation retire owned breakpoint");}
        armed=false;
    }
    void rotate(ULONG native,Step next) {
        if(!bp || !armed)throw std::runtime_error("activation lost rotating breakpoint");
        target=address(native); step=next;
        check(bp->SetOffset(target),"activation rotate owned execute address");
    }
    void emit(const char *kind,ULONG transaction,const char *fields,ULONGLONG tick) {
        if(!startup_retired || (seen_retired && !*startup_retired))
            throw std::runtime_error("activation startup retirement regressed");
        seen_retired=*startup_retired;
        if(strcmp(kind,"finish") && (tick>=host_deadline || (pending && tick>=pending_deadline)))
            throw std::runtime_error("activation observation deadline expired");
        char json[2048];
        int count=sprintf_s(json,"{\"schema\":\"clash95_native_activation_trace_v1\",\"kind\":\"%s\",\"tx\":%lu,"
            "\"pid\":%lu,\"tid\":%lu,\"creation_filetime\":%llu,\"image_base\":%lu,"
            "\"controller_sha256\":\"%s\",\"session_id\":\"%s\",\"tick_ms\":%llu,\"startup_retired\":%s,%s}",
            kind,transaction,s.owned_pid,s.primary_tid,owner.creation_filetime,owner.image_base,
            source_sha256(),owner.session.c_str(),tick,*startup_retired?"true":"false",fields);
        if(count<0)throw std::runtime_error("activation trace encoding failed");
        printf("REAL_ACTIVATION_V1 %s\n",json);fflush(stdout);
    }
    void arm_initial(ULONGLONG host_start,ULONGLONG bound) {
        if(!enabled)return;
        retained_context(); verify_anchors(); ULONGLONG now=GetTickCount64();
        if(armed || bp || finished || *startup_retired || host_start>now || bound<=now ||
           bound<host_start || bound-host_start<10000 || bound-host_start>180000)
            throw std::runtime_error("activation initial-stop interval rejected");
        host_deadline=bound; target=address(0x461823);
        try {
            check(s.control->AddBreakpoint(DEBUG_BREAKPOINT_DATA,DEBUG_ANY_ID,&bp),"activation add one hardware breakpoint");
            check(bp->SetDataParameters(1,DEBUG_BREAK_EXECUTE),"activation execute only");
            check(bp->SetOffset(target),"activation initial WM_ACTIVATEAPP address");
            check(bp->SetMatchThreadId(engine_thread),"activation retained primary thread");
            check(bp->GetId(&bp_id),"activation breakpoint identity");
            check(bp->AddFlags(DEBUG_BREAKPOINT_ENABLED),"activation enable owned breakpoint");
            armed=true;
        } catch(...){clear();throw;}
        char fields[192];sprintf_s(fields,"\"initial_stop_armed\":true,\"host_start_tick_ms\":%llu,\"deadline_tick_ms\":%llu,\"max_transactions\":16",host_start,host_deadline);
        emit("start",0,fields,GetTickCount64());
    }
    void require_pending_deadline() const {
        ULONGLONG now=GetTickCount64();
        if(!pending || now>=host_deadline || now>=pending_deadline)
            throw std::runtime_error("activation pending transaction expired or missing");
    }
    void require_pending() const {
        require_pending_deadline();
        if(s.word(entry_esp)!=wndproc_return || s.word(branch_esp+20)!=hwnd ||
           s.word(branch_esp+24)!=message || s.word(branch_esp+28)!=wparam || s.word(branch_esp+32)!=lparam)
            throw std::runtime_error("activation retained WndProc caller or arguments changed");
        if(outer_seen && (s.word(address(0x5452CC))!=mouse_ready ||
           s.word(address(0x5452D0))!=keyboard_ready || s.word(address(0x5452D4))))
            throw std::runtime_error("activation ready flags changed or joystick unsupported");
    }
    ULONG outer_call() const { return low==1?0x4618BB:0x461869; }
    ULONG outer_return() const { return low==1?0x4618C0:0x46186E; }
    ULONG device_call() const {
        bool mouse=devices.at(device_index);
        return low==1?(mouse?0x47BF63:0x47BF4D):(mouse?0x47BFB3:0x47BF9D);
    }
    ULONG device_return() const { return device_call()+3; }
    const char *device_kind() const { return devices.at(device_index)?"mouse":"keyboard"; }
    ULONG device_field() const { return address(0x545198)+(devices.at(device_index)?8:4); }
    ULONG method_slot() const { return low==1?0x1c:0x20; }
    void require_device() const {
        if(reg("ebx")!=address(0x545198) || s.word(branch_esp-4)!=address(outer_return()) ||
           s.word(device_field())!=device || s.word(device)!=vtable || s.word(vtable+method_slot())!=method)
            throw std::runtime_error("activation native backend, caller or COM identity changed");
    }
    void resume() { owner.verify_owner();check(s.control->SetExecutionStatus(DEBUG_STATUS_GO),"continue observed activation only"); }
    void retire(const char *reason) {
        if(pending)throw std::runtime_error("activation retired with a pending transaction");
        clear();ULONGLONG tick=GetTickCount64();
        if(!strcmp(reason,"host_interval") && tick>=host_deadline)reason="host_deadline";
        char fields[160];sprintf_s(fields,"\"transactions\":%lu,\"pending\":false,\"reason\":\"%s\"",transactions,reason);
        emit("finish",0,fields,tick);finished=true;
    }
    void service() {
        if(!enabled || finished)return;
        owner.verify_token();owner.verify_owner();
        if(!armed)throw std::runtime_error("activation observer was not initially armed");
        if(pending){require_pending_deadline();return;}
        if(GetTickCount64()>=host_deadline)retire("host_deadline");
    }
    bool on_event(ULONG type,ULONG process,ULONG thread,ULONG64 ip) {
        if(!enabled || finished || type!=DEBUG_EVENT_BREAKPOINT)return false;
        DEBUG_LAST_EVENT_INFO_BREAKPOINT info={};ULONG actual=0,pid=0,tid=0,used=0,description_used=0;char description[256]={};
        check(s.control->GetLastEventInformation(&actual,&pid,&tid,&info,sizeof(info),&used,description,sizeof(description),&description_used),"activation actual breakpoint");
        if(!bp || info.Id!=bp_id)return false;
        retained_context();ULONG64 offset=0;check(bp->GetOffset(&offset),"activation owned breakpoint offset");
        ULONG current_id=DEBUG_ANY_ID;check(bp->GetId(&current_id),"activation retained breakpoint id");
        ULONG breakpoint_type=0,processor_type=0;check(bp->GetType(&breakpoint_type,&processor_type),"activation hardware breakpoint type");
        ULONG data_size=0,access=0;check(bp->GetDataParameters(&data_size,&access),"activation execute breakpoint parameters");
        if(actual!=type || pid!=process || tid!=thread || used!=sizeof(info) || process!=engine_process || thread!=engine_thread ||
           current_id!=bp_id || ip!=target || offset!=target || reg("eip")!=target || breakpoint_type!=DEBUG_BREAKPOINT_DATA ||
           processor_type!=IMAGE_FILE_MACHINE_I386 || data_size!=1 || access!=DEBUG_BREAK_EXECUTE ||
           GetTickCount64()>=host_deadline)
            throw std::runtime_error("activation breakpoint ownership, instruction or deadline differs");
        char fields[768];
        if(step==Activation){
            if(pending || tx!=transactions || transactions>=16)throw std::runtime_error("activation reentry or transaction cap rejected");
            branch_esp=reg("esp");
            if(!pointer(branch_esp,36) || branch_esp<0x10020)throw std::runtime_error("activation WndProc stack rejected");
            entry_esp=branch_esp+16;wndproc_return=s.word(entry_esp);
            hwnd=s.word(branch_esp+20);message=s.word(branch_esp+24);wparam=s.word(branch_esp+28);lparam=s.word(branch_esp+32);low=wparam&0xffff;
            if(!hwnd || message!=0x1c || reg("ebx")!=message || reg("esi")!=wparam || reg("edi")!=hwnd ||
               wndproc_return<0x10000 || wndproc_return>=0x7ffe0000)
                throw std::runtime_error("activation native WM_ACTIVATEAPP arguments rejected");
            ULONGLONG tick=GetTickCount64();
            if(tick>~static_cast<ULONGLONG>(0)-20000)throw std::runtime_error("activation tick overflow rejected");
            pending_deadline=tick+20000;
            if(pending_deadline>host_deadline)pending_deadline=host_deadline;
            ++tx;pending=true;outer_seen=false;devices.clear();device_index=0;
            sprintf_s(fields,"\"branch_esp\":%lu,\"entry_esp\":%lu,\"hwnd\":%lu,\"message\":%lu,\"wparam\":%lu,"
                "\"wparam_low16\":%lu,\"lparam\":%lu,\"wndproc_return\":%lu,\"deadline_tick_ms\":%llu",
                branch_esp,entry_esp,hwnd,message,wparam,low,lparam,wndproc_return,pending_deadline);
            emit("activation",tx,fields,tick);
            rotate(low<=1?outer_call():0x4618A6,low<=1?OuterCall:WndProcRet);resume();return true;
        }
        require_pending();
        if(step==OuterCall){
            if(reg("esp")!=branch_esp || reg("eax")!=address(0x545198) || reg("ebx")!=low)
                throw std::runtime_error("activation native outer CALL frame differs");
            mouse_ready=s.word(address(0x5452CC));keyboard_ready=s.word(address(0x5452D0));
            if(s.word(address(0x5452D4)))throw std::runtime_error("activation joystick path is outside observer scope");
            outer_seen=true;if(mouse_ready)devices.push_back(true);if(keyboard_ready)devices.push_back(false);
            sprintf_s(fields,"\"operation\":\"%s\",\"call_va\":%lu,\"return_va\":%lu,\"call_esp\":%lu,\"backend\":%lu,"
                "\"mouse_ready\":%lu,\"keyboard_ready\":%lu,\"joystick_ready\":0",
                low==1?"acquire":"unacquire",address(outer_call()),address(outer_return()),branch_esp,address(0x545198),mouse_ready,keyboard_ready);
            emit("outer_call",tx,fields,GetTickCount64());
            rotate(devices.empty()?outer_return():device_call(),devices.empty()?OuterReturn:DeviceCall);resume();return true;
        }
        if(step==DeviceCall){
            if(reg("esp")!=branch_esp-20 || reg("ebx")!=address(0x545198))throw std::runtime_error("activation COM call frame differs");
            device=s.word(device_field());if(!pointer(device))throw std::runtime_error("activation enabled device pointer rejected");
            vtable=s.word(device);if(!pointer(vtable,method_slot()+4))throw std::runtime_error("activation vtable pointer rejected");
            method=s.word(vtable+method_slot());
            if(method<0x10000 || method>=0x7ffe0000 || reg("eax")!=device || reg("edx")!=vtable || s.word(branch_esp-20)!=device)
                throw std::runtime_error("activation COM method or this argument differs");
            require_device();
            sprintf_s(fields,"\"device_kind\":\"%s\",\"call_va\":%lu,\"return_va\":%lu,\"call_esp\":%lu,\"device\":%lu,\"vtable\":%lu,\"method\":%lu",
                device_kind(),address(device_call()),address(device_return()),branch_esp-20,device,vtable,method);
            emit("device_call",tx,fields,GetTickCount64());rotate(device_return(),DeviceReturn);resume();return true;
        }
        if(step==DeviceReturn){
            if(reg("esp")!=branch_esp-16)throw std::runtime_error("activation stdcall return frame differs");
            last_hresult=reg("eax");require_device();
            sprintf_s(fields,"\"device_kind\":\"%s\",\"return_va\":%lu,\"return_esp\":%lu,\"hresult\":%lu",
                device_kind(),address(device_return()),branch_esp-16,last_hresult);
            emit("device_return",tx,fields,GetTickCount64());++device_index;
            rotate(device_index<devices.size()?device_call():outer_return(),device_index<devices.size()?DeviceCall:OuterReturn);resume();return true;
        }
        if(step==OuterReturn){
            ULONG result=reg("eax");
            if(reg("esp")!=branch_esp || reg("ebx")!=low || result!=(devices.empty()?address(0x545198):last_hresult))
                throw std::runtime_error("activation outer return or final native result differs");
            sprintf_s(fields,"\"return_va\":%lu,\"return_esp\":%lu,\"eax\":%lu",address(outer_return()),branch_esp,result);
            emit("outer_return",tx,fields,GetTickCount64());rotate(0x4618A6,WndProcRet);resume();return true;
        }
        if(step==WndProcRet){
            if(reg("esp")!=entry_esp || reg("eax")!=0)throw std::runtime_error("activation WndProc RET frame differs");
            sprintf_s(fields,"\"epilogue_va\":%lu,\"epilogue_esp\":%lu,\"entry_esp\":%lu,\"wndproc_return\":%lu,"
                "\"hwnd\":%lu,\"message\":%lu,\"wparam\":%lu,\"wparam_low16\":%lu,\"lparam\":%lu",
                address(0x4618A6),entry_esp,entry_esp,wndproc_return,hwnd,message,wparam,low,lparam);
            emit("end",tx,fields,GetTickCount64());pending=false;++transactions;
            if(transactions==16)retire("transaction_cap");else rotate(0x461823,Activation);
            resume();return true;
        }
        throw std::runtime_error("activation owned breakpoint violated native pair order");
    }
    void finish() {
        if(!enabled || finished)return;
        owner.verify_token();owner.verify_owner();
        if(pending)throw std::runtime_error("host interval ended with activation transaction pending");
        retire("host_interval");
    }
};
'''

_SNAPSHOT = 'static void snapshot(Session &s,const std::string &out,int sample,bool proxy) {\n'
_CONSTRUCTORS = ('        PauseLeaseController leases(s,argc>=6?argv[5]:nullptr,base);\n'
                 '        StartupController startup(s,disk,base);\n'
                 '        NativePhaseController phases(leases,argc==7?argv[6]:nullptr,argv[2],strcmp(argv[4],"proxy")==0,&startup.retired);\n')
_EVENT = ('                if (startup.on_event(type,proc,thread,ip)) continue;\n'
          '                if (phases.on_event(type,proc,thread,ip)) continue;\n')
_SERVICE = '            if (phases.enabled) phases.service(); else leases.service();\n'
_GO = '        check(s.control->SetExecutionStatus(DEBUG_STATUS_GO),"run actual code");\n'
_FINISH = '        phases.finish();\n'


def source_sha256() -> str:
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def source_replacements() -> tuple[tuple[str, str], ...]:
    anchors = '\n'.join(f'        anchor(0x{va:06X},"{raw}");' for va, raw in NATIVE_ANCHORS.items())
    controller = CONTROLLER_SOURCE.replace('@ACTIVATION_ANCHORS@', anchors)
    controller = controller.replace('@ACTIVATION_SOURCE_SHA256@', source_sha256())
    return (
        (_SNAPSHOT, controller + _SNAPSHOT),
        (_CONSTRUCTORS, _CONSTRUCTORS + '        NativeActivationController activation(leases,&startup.retired,disk,phases.enabled);\n'),
        (_GO, '        activation.arm_initial(start,start+static_cast<ULONGLONG>(seconds)*1000);\n' + _GO),
        (_EVENT, _EVENT.splitlines(keepends=True)[0] + '                if (activation.on_event(type,proc,thread,ip)) continue;\n' + _EVENT.splitlines(keepends=True)[1]),
        (_SERVICE, '            activation.service();\n' + _SERVICE),
        (_FINISH, '        activation.finish();\n' + _FINISH),
    )


def render_source(base_source: str) -> str:
    """Require exact owned startup→pause→phase composition; transform source only."""
    if type(base_source) is not str:
        raise TypeError('Harness source must be text')
    if 'NativeActivationController' in base_source:
        raise ValueError('Harness already contains activation observer')
    for declaration in ('struct StartupController {', 'struct PauseLeaseController {', 'struct NativePhaseController {'):
        if base_source.count(declaration) != 1:
            raise ValueError('Composed startup, pause and phase controllers required')
    replacements = source_replacements()
    for old, _new in replacements:
        if base_source.count(old) != 1:
            raise ValueError('Activation source anchor missing, reordered or duplicated: ' + old.splitlines()[0])
    for old, new in replacements:
        base_source = base_source.replace(old, new, 1)
    return base_source
