"""Fixed x86 initial-loader batch source; preparation never runs native code.

The stdout archive contains original native observations. Canonical comparison
is asynchronous, after termination; no comparison or whole-candidate proof is
claimed during the native hold. Public plans/requests are opaque live issuer
identities, not self-authenticated manifests or arbitrary expected ranges.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import struct
import sys
import types
import uuid
import weakref

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "tools/hidden_soak_loader_native.py"
ADAPTER = "tools/hidden_soak_loader_native_adapter.py"
COLLECTOR = "tools/hidden_soak_loaded_read_session.py"
COLLECTOR_SHA256 = "8840cb175a6d2f4a965d249d8a739a608155e3df49afb17bf12e08f445c837b7"
REQUEST_MAGIC = b"CLHDLP1\0"
ARCHIVE_MAGIC = b"CLHDLR1\0"
MAX_METADATA = 8 * 1024 * 1024
MAX_FAILURE_METADATA = 1024 * 1024
MAX_RAW = 16 * 1024 * 1024
MAX_FRAME_JSON = 512 * 1024
MAX_FRAME_RAW = 64 * 1024 + 3
FALSE_CLAIMS = {name: False for name in (
    "passed", "native_producer_provenance_verified", "native_read_coherence_verified",
    "native_generation_ownership_verified", "native_job_cleanup_verified", "host_cleanup_complete",
    "canonical_comparison_during_native_hold", "loaded_candidate_verified", "loaded_probe_verified",
    "probe_executed", "running_duration_verified", "runtime_acceptance", "release_acceptance",
    "manual_input_verified", "promotion_ready", "stable")}


def _require(value, label):
    if not value: raise ValueError(label)


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")


def _sha(raw): return hashlib.sha256(raw).hexdigest()


def retention_budget():
    """One native journal, atomic copy, and complete known failure allowance."""
    return dict(raw_bytes=MAX_RAW, raw_temporary_bytes=MAX_FRAME_RAW,
        metadata_bytes=MAX_METADATA, failure_metadata_bytes=MAX_FAILURE_METADATA,
        atomic_metadata_temporary_bytes=MAX_METADATA + MAX_FAILURE_METADATA,
        additional_peak_bytes=MAX_RAW + MAX_FRAME_RAW + 2 * (MAX_METADATA + MAX_FAILURE_METADATA),
        collector_allowance_is_not_additionally_counted=True,
        exclusions=["candidate/assets/native compiler output", "original/source/collector RAM",
                    "independent generation/job/clock receipts", "additional durable comparison exports",
                    "unknown or unavailable original native output debt"],
        scope="one shared native raw/metadata journal only; no retention/disk reserve bypass installed")


@dataclass(frozen=True, eq=False, slots=True, weakref_slot=True)
class NativeReadPlan:
    binding_json: str


@dataclass(frozen=True, eq=False, slots=True, weakref_slot=True)
class NativeRequest:
    binding_json: str


@dataclass(frozen=True)
class RequestFacts:
    metadata_json: str
    request_bytes: bytes
    host_source: bytes
    requests: tuple
    collect: object
    check_sources: object


def _private_preparation(original, contract):
    # Privately compile both producer sources. Mutating public HARNESS or
    # collector constructors must not supply source-issued byte authority.
    own_path, collector_path, adapter_path = ROOT / SOURCE, ROOT / COLLECTOR, ROOT / ADAPTER
    _require(Path(__file__).resolve() == own_path, "canonical producer path required")
    own_raw, collector_raw = own_path.read_bytes(), collector_path.read_bytes()
    _require(_sha(collector_raw) == COLLECTOR_SHA256, "frozen collector differs")
    prefix = "_clash95_native_batch_" + uuid.uuid4().hex
    try:
        package = types.ModuleType(prefix); package.__path__ = []; sys.modules[prefix] = package
        modules = {}
        oracle_path = ROOT / "tools/hidden_soak_loaded_image.py"
        oracle_raw = oracle_path.read_bytes()
        for name, raw, path in (("collector", collector_raw, collector_path), ("producer", own_raw, own_path),
                               ("oracle", oracle_raw, oracle_path)):
            module = types.ModuleType(prefix + "." + name); module.__file__, module.__package__ = str(path), prefix
            sys.modules[module.__name__] = module
            exec(compile(raw, str(path), "exec"), module.__dict__); modules[name] = module
        collector, producer = modules["collector"], modules["producer"]
        snapshot = tuple((path, collector._source_bytes(path)) for path in (own_path, collector_path, adapter_path))
        _require(snapshot[0][1][0] == own_raw and snapshot[1][1][0] == collector_raw,
                 "producer bytes changed between compilation and source snapshot")
        _require(_sha(oracle_raw) == collector.ORACLE_SHA256, "frozen oracle differs")
        # Freeze the exact typed caller fields once, before authentication.
        # Later caller mutation cannot choose the request inventory.
        copied = modules["oracle"]._clone(modules["oracle"].LoadedImageContract, contract)
        prepared = collector.prepare_read_plan(original, copied)
        # The opaque collector admission already independently reconstructs
        # actual narrow/wide recipes, typed metadata, probe and full sources.
        binding = json.loads(prepared.binding_json)
        # Its readable text is used only after genuine live issuer admission.
        # Obtain exact canonical PE requests independently from the contract,
        # authenticated again by this frozen private collector preparation.
        plan = json.loads(copied.plan_json)
        _require(binding["candidate_sha256"] == plan["candidate_sha256"] and
                 binding["contract_sha256"] == _sha(copied.plan_json.encode("ascii")), "prepared binding differs")
        requests = tuple((row["rva"], row["size"]) for row in plan["immutable_scope"]["chunks"])
        def check_sources():
            _require(tuple((path, collector._source_bytes(path)) for path, _ in snapshot) == snapshot, "producer sources changed")
        check_sources()
        facts = dict(profile=plan["profile"], resolution=plan["resolution"], stage=plan["stage"],
            recipe_revision=plan["recipe_revision"], candidate_sha256=plan["candidate_sha256"],
            probe_sha256=plan["canonical_probe_sha256"], source_closure_sha256=plan["source_closure_sha256"],
            preferred_base=plan["immutable_scope"]["preferred_base"], image_size=plan["immutable_scope"]["image_size"],
            native_source_sha256=_sha(own_raw), adapter_source_sha256=_sha(snapshot[2][1][0]),
            host_source_sha256=_sha(producer.HARNESS.encode("ascii")))
        def collect(authority, anchor, adapter):
            check_sources()
            result = collector.collect_prepared_reads(prepared, authority, anchor, adapter)
            check_sources(); return result
        return facts, requests, producer.HARNESS.encode("ascii"), collect, check_sources
    finally:
        for name in list(sys.modules):
            if name == prefix or name.startswith(prefix + "."): del sys.modules[name]


def _factory():
    plans, requests = {}, {}
    plan_class, request_class, facts_class, prepare = NativeReadPlan, NativeRequest, RequestFacts, _private_preparation
    fixed_claims = dict(FALSE_CLAIMS)
    def retain(registry, obj, binding, state):
        identity = id(obj)
        def retire(ref):
            if identity in registry and registry[identity][0] is ref: del registry[identity]
        registry[identity] = (weakref.ref(obj, retire), binding, state)
        return obj
    def admitted(registry, cls, obj):
        row = registry.get(id(obj))
        _require(type(obj) is cls and row is not None and row[0]() is obj and obj.binding_json == row[1],
                 "live source-issued opaque identity required")
        row[2][-1](); return row[2]
    def prepare_native_plan(original, contract):
        state = prepare(original, contract)
        binding = _canonical(dict(state[0], requests=[list(row) for row in state[1]], claims=fixed_claims)).decode("ascii")
        return retain(plans, plan_class(binding), binding, state)
    def prepare_request(plan, *, run_id, checkpoint_id, epoch_id, controller_pid, frequency_hz, origin_tick, origin_ns):
        facts, rows, host, collect, check = admitted(plans, plan_class, plan)
        for token in (run_id, checkpoint_id, epoch_id):
            _require(type(token) is str and uuid.UUID(token).hex == token, "canonical independently issued token required")
        for value, minimum, maximum in ((controller_pid, 1, 0xffffffff), (frequency_hz, 1, 10**9),
                (origin_tick, 1, (1 << 63) - 1), (origin_ns, 1, (1 << 63) - 20 * 10**9)):
            _require(type(value) is int and minimum <= value <= maximum, "bounded original independent clock/owner scalar required")
        raw = (REQUEST_MAGIC + struct.pack("<IIIIQQQ", len(rows), facts["preferred_base"], facts["image_size"],
            controller_pid, frequency_hz, origin_tick, origin_ns) + facts["candidate_sha256"].encode("ascii") +
            (run_id + checkpoint_id + epoch_id).encode("ascii") + b"".join(struct.pack("<II", *row) for row in rows))
        metadata = dict(facts, request_sha256=_sha(raw), run_id=run_id, checkpoint_id=checkpoint_id,
            epoch_id=epoch_id, controller_pid=controller_pid, frequency_hz=frequency_hz, origin_tick=origin_tick, origin_ns=origin_ns)
        binding = _canonical(metadata).decode("ascii")
        state = (binding, raw, host, rows, collect, check)
        return retain(requests, request_class(binding), binding, state)
    def inspect_request(request):
        binding, raw, host, rows, collect, check = admitted(requests, request_class, request)
        return facts_class(binding, raw, host, rows, collect, check)
    return prepare_native_plan, prepare_request, inspect_request


# HARNESS is privately recompiled from this canonical file before issuance.
# There is no public generic constructor accepting expected ranges or bytes.
HARNESS = r'''
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <tlhelp32.h>
#include <bcrypt.h>
#include <dbgeng.h>
#include <algorithm>
#include <cstdio>
#include <cstring>
#include <cwchar>
#include <memory>
#include <stdexcept>
#include <string>
#include <vector>
#include <utility>

using Bytes=std::vector<unsigned char>;
static_assert(sizeof(EXCEPTION_RECORD64)==152,"exact original exception record required");
static_assert(sizeof(DEBUG_LAST_EVENT_INFO_EXCEPTION)==160,"exact original last exception event required");
using Object=std::vector<std::pair<std::string,std::string>>;
static std::string number(unsigned long long n) { return std::to_string(n); }
static std::string signed_number(long n) { return std::to_string(n); }
static std::string quote(const std::string &s) {
    std::string out="\"";
    for(unsigned char c:s) {
        if(c=='"'||c=='\\') { out+='\\'; out+=static_cast<char>(c); }
        else if(c<32||c>126) { char b[7]; sprintf_s(b,"\\u%04x",c); out+=b; }
        else out+=static_cast<char>(c);
    }
    return out+'"';
}
static std::string object(Object fields) {
    std::sort(fields.begin(),fields.end()); std::string out="{";
    for(const auto &row:fields) { if(out.size()>1) out+=','; out+=quote(row.first)+':'+row.second; }
    return out+'}';
}
static std::string hex(const void *p,size_t n) {
    const auto *v=static_cast<const unsigned char *>(p); std::string out; out.reserve(n*2);
    const char *chars="0123456789abcdef";
    for(size_t i=0;i<n;++i) { out+=chars[v[i]>>4]; out+=chars[v[i]&15]; } return out;
}
static unsigned long long bits(HANDLE h) { return reinterpret_cast<ULONG_PTR>(h); }
static void demand(bool ok,const char *reason) { if(!ok) throw std::runtime_error(reason); }
static unsigned long long ft(FILETIME v) { return (static_cast<unsigned long long>(v.dwHighDateTime)<<32)|v.dwLowDateTime; }
struct NativeFailure : std::runtime_error {
    std::string original; Bytes prefix;
    NativeFailure(const char *api,long long result,DWORD error,ULONG requested=0,ULONG returned=0,Bytes raw=Bytes()):
        std::runtime_error(api),original(object({{"api_name",quote(api)},{"native_return",std::to_string(result)},
        {"native_error",number(error)},{"requested_bytes",number(requested)},{"returned_bytes",number(returned)},
        {"detail_hex",quote("")}})),prefix(std::move(raw)) {}
};
static void (*failure_sink)(const NativeFailure &)=nullptr;
struct Handle {
    HANDLE value=nullptr;
    Handle()=default; explicit Handle(HANDLE h):value(h) {}
    Handle(const Handle&)=delete; Handle &operator=(const Handle&)=delete;
    ~Handle() { if(value&&value!=INVALID_HANDLE_VALUE) CloseHandle(value); }
    HANDLE release() { HANDLE old=value; value=nullptr; return old; }
};
static Bytes read_file(const wchar_t *path) {
    SetLastError(0); Handle f(CreateFileW(path,GENERIC_READ,FILE_SHARE_READ,nullptr,OPEN_EXISTING,FILE_FLAG_OPEN_REPARSE_POINT,nullptr));
    DWORD error=GetLastError();
    if(f.value==INVALID_HANDLE_VALUE)throw NativeFailure("CreateFileW",static_cast<long long>(bits(f.value)),error);
    BY_HANDLE_FILE_INFORMATION info={}; LARGE_INTEGER size={};
    SetLastError(0); DWORD type=GetFileType(f.value); error=GetLastError();
    if(type!=FILE_TYPE_DISK)throw NativeFailure("GetFileType",type,error);
    SetLastError(0); BOOL observed=GetFileInformationByHandle(f.value,&info); error=GetLastError();
    if(!observed)throw NativeFailure("GetFileInformationByHandle",observed,error);
    demand(!(info.dwFileAttributes&(FILE_ATTRIBUTE_DIRECTORY|FILE_ATTRIBUTE_REPARSE_POINT)),"regular nonreparsed input required");
    SetLastError(0); observed=GetFileSizeEx(f.value,&size); error=GetLastError();
    if(!observed)throw NativeFailure("GetFileSizeEx",observed,error);
    demand(size.QuadPart>0&&size.QuadPart<=64*1024*1024,"bounded regular input required");
    Bytes out; out.reserve(static_cast<size_t>(size.QuadPart));
    while(out.size()<static_cast<size_t>(size.QuadPart)) {
        ULONG requested=static_cast<ULONG>(std::min<size_t>(65536,static_cast<size_t>(size.QuadPart)-out.size()));
        Bytes block(requested); DWORD got=0; SetLastError(0);
        BOOL read=ReadFile(f.value,block.data(),requested,&got,nullptr); error=GetLastError();
        // Preserve the complete requested-capacity original on a failing or
        // short read, including its initialized/unwritten tail. The native
        // returned count remains separate and cannot authorize that tail.
        if(!read||got!=requested)throw NativeFailure("ReadFile",read,error,requested,got,std::move(block));
        out.insert(out.end(),block.begin(),block.end());
    }
    return out;
}
static std::string file_hash(const wchar_t *path,long &status,bool *status_observed=nullptr) {
    if(status_observed)*status_observed=false;
    try {
        Bytes bytes=read_file(path); BCRYPT_ALG_HANDLE algorithm=nullptr;
        status=BCryptOpenAlgorithmProvider(&algorithm,BCRYPT_SHA256_ALGORITHM,nullptr,0);
        if(status_observed)*status_observed=true;
        if(status!=0)throw NativeFailure("BCryptOpenAlgorithmProvider",status,0);
        unsigned char digest[32]={}; status=BCryptHash(algorithm,nullptr,0,bytes.data(),static_cast<ULONG>(bytes.size()),digest,32);
        NTSTATUS closed=BCryptCloseAlgorithmProvider(algorithm,0);
        if(status!=0||closed!=0) {
            NativeFailure failed(status!=0?"BCryptHash":"BCryptCloseAlgorithmProvider",status!=0?status:closed,0);
            auto original=object({{"hash_status",signed_number(status)},{"close_status",signed_number(closed)}});
            failed.original=object({{"api_name",quote(status!=0?"BCryptHash":"BCryptCloseAlgorithmProvider")},
                {"native_return",signed_number(status!=0?status:closed)},{"native_error","0"},{"requested_bytes","0"},
                {"returned_bytes","0"},{"detail_hex",quote(hex(original.data(),original.size()))}});
            throw failed;
        }
        return hex(digest,32);
    } catch(const NativeFailure &failed) { if(failure_sink)failure_sink(failed); else throw; return ""; }
}
struct Request {
    ULONG preferred=0,image_size=0,controller=0; unsigned long long frequency=0,origin=0,origin_ns=0;
    std::string candidate,run,checkpoint,epoch,sha; std::vector<std::pair<ULONG,ULONG>> rows;
};
static Request parse_request(const wchar_t *path) {
    Bytes b=read_file(path); demand(b.size()>=208&&!memcmp(b.data(),"CLHDLP1\0",8),"fixed request magic required");
    Request r; ULONG count=0; memcpy(&count,b.data()+8,4); memcpy(&r.preferred,b.data()+12,4);
    memcpy(&r.image_size,b.data()+16,4); memcpy(&r.controller,b.data()+20,4);
    memcpy(&r.frequency,b.data()+24,8); memcpy(&r.origin,b.data()+32,8); memcpy(&r.origin_ns,b.data()+40,8);
    demand(count>0&&count<=511&&b.size()==208+count*8&&r.controller&&r.frequency&&r.frequency<=1000000000&&r.origin&&r.origin_ns,
        "source-owned request extent differs");
    r.candidate.assign(reinterpret_cast<const char *>(b.data()+48),64);
    r.run.assign(reinterpret_cast<const char *>(b.data()+112),32); r.checkpoint.assign(reinterpret_cast<const char *>(b.data()+144),32);
    r.epoch.assign(reinterpret_cast<const char *>(b.data()+176),32);
    for(const auto &token:{r.candidate,r.run,r.checkpoint,r.epoch})
        for(char c:token) demand(c>='0'&&c<='9'||c>='a'&&c<='f',"source-owned token bytes differ");
    unsigned long long total=4;
    for(ULONG i=0;i<count;++i) {
        ULONG at=0,size=0; memcpy(&at,b.data()+208+i*8,4); memcpy(&size,b.data()+212+i*8,4);
        demand(size&&size<=65539&&at<=r.image_size&&size<=r.image_size-at,"fixed request range invalid");
        r.rows.emplace_back(at,size); total+=size;
    }
    demand(total<=16*1024*1024,"fixed complete read allowance exceeded");
    long hash_status=0; r.sha=file_hash(path,hash_status); demand(hash_status==0&&!r.sha.empty(),"request hash unavailable"); return r;
}
static std::string qpc(const Request &r,unsigned long long &tick,bool &valid) {
    LARGE_INTEGER frequency={},counter={}; SetLastError(0); BOOL fr=QueryPerformanceFrequency(&frequency); DWORD fe=GetLastError();
    SetLastError(0); BOOL cr=QueryPerformanceCounter(&counter); DWORD ce=GetLastError(); tick=static_cast<unsigned long long>(counter.QuadPart);
    valid=fr==TRUE&&cr==TRUE&&fe==0&&ce==0&&frequency.QuadPart==static_cast<LONGLONG>(r.frequency)&&
        counter.QuadPart>0&&tick>=r.origin;
    return object({{"epoch_id",quote(r.epoch)},{"frequency_hz",std::to_string(frequency.QuadPart)},{"tick",std::to_string(counter.QuadPart)},
        {"frequency_native_return",signed_number(fr)},{"frequency_native_error",number(fe)},
        {"counter_native_return",signed_number(cr)},{"counter_native_error",number(ce)}});
}
struct Journal {
    HANDLE output=GetStdHandle(STD_OUTPUT_HANDLE); unsigned long long sequence=0,raw_bytes=0,metadata_bytes=8;
    bool debt=false,failed=false;
    void write(const void *p,DWORD n) { DWORD got=0; if(!WriteFile(output,p,n,&got,nullptr)||got!=n) { debt=true; throw std::runtime_error("original archive write debt"); } }
    void begin() { demand(GetFileType(output)==FILE_TYPE_DISK,"FILE_TYPE_DISK original archive required; pipes unsupported"); write("CLHDLR1\0",8); }
    void frame(const std::string &op,const std::string &data,const Bytes &raw=Bytes()) {
        std::string json=object({{"sequence",number(sequence+1)},{"operation",quote(op)},{"data",data}});
        if(json.size()>512*1024||raw.size()>65539) { debt=true; throw std::runtime_error("complete original packet exceeds fixed capacity; unknown output debt"); }
        // A whole final failing packet may use the reserved 1MiB diagnostics.
        if(metadata_bytes+json.size()+8>9*1024*1024||raw_bytes+raw.size()>16*1024*1024+65539) { debt=true; throw std::runtime_error("original archive retention debt"); }
        ULONG sizes[2]={static_cast<ULONG>(json.size()),static_cast<ULONG>(raw.size())};
        write(sizes,8); write(json.data(),sizes[0]); if(sizes[1]) write(raw.data(),sizes[1]);
        if(!FlushFileBuffers(output)) { debt=true; throw std::runtime_error("original archive flush debt"); }
        ++sequence; metadata_bytes+=json.size()+8; raw_bytes+=raw.size();
        if(metadata_bytes>8*1024*1024||raw_bytes>16*1024*1024) throw std::runtime_error("complete over-capacity original packet retained");
    }
};
static Journal *active_journal=nullptr;
static void retain_native_failure(const NativeFailure &failed) {
    demand(active_journal!=nullptr,"original native failure has no archive; debt");
    active_journal->failed=true; active_journal->frame("native_failure",failed.original,failed.prefix);
}
static std::string generation(HANDLE h,HANDLE parent,bool &valid,std::string &identity,std::string &image_hash,DWORD &observed_pid) {
    SetLastError(0); DWORD pid=GetProcessId(h),pid_error=GetLastError();
    wchar_t path[32768]={}; DWORD chars=32768; SetLastError(0); BOOL pr=QueryFullProcessImageNameW(h,0,path,&chars); DWORD pe=GetLastError();
    FILETIME created={},ended={},kernel={},user={}; SetLastError(0); BOOL tr=GetProcessTimes(h,&created,&ended,&kernel,&user); DWORD te=GetLastError();
    long hs=0; bool hs_observed=false; std::string digest=pr ? file_hash(path,hs,&hs_observed):"";
    SetLastError(0); DWORD waited=WaitForSingleObject(h,0),we=GetLastError();
    DWORD parent_pid=0,parent_error=0; BOOL parent_return=0;
    SetLastError(0); Handle snapshot(CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS,0)); DWORD snapshot_error=GetLastError();
    if(snapshot.value==INVALID_HANDLE_VALUE)retain_native_failure(NativeFailure("CreateToolhelp32Snapshot",static_cast<long long>(bits(snapshot.value)),snapshot_error));
    PROCESSENTRY32W row={}; row.dwSize=sizeof(row);
    SetLastError(0); BOOL more=Process32FirstW(snapshot.value,&row); parent_error=GetLastError();
    unsigned int rows=0;
    while(more&&rows++<65536) { if(row.th32ProcessID==pid) { parent_pid=row.th32ParentProcessID; parent_return=more; break; }
        SetLastError(0); more=Process32NextW(snapshot.value,&row); parent_error=GetLastError(); }
    Handle actual_parent;
    if(!parent&&parent_return) {
        SetLastError(0); actual_parent.value=OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION|SYNCHRONIZE,FALSE,parent_pid);
        DWORD opened_error=GetLastError();
        if(!actual_parent.value)retain_native_failure(NativeFailure("OpenProcess.parent",0,opened_error));
    }
    HANDLE ph=parent?parent:actual_parent.value; FILETIME pc={},px={},pk={},pu={}; SetLastError(0);
    BOOL ptr=GetProcessTimes(ph,&pc,&px,&pk,&pu); DWORD pte=GetLastError();
    valid=pid&&pid_error==0&&pr==TRUE&&pe==0&&chars>0&&chars<32768&&tr==TRUE&&te==0&&ft(created)>0&&
        ft(ended)==0&&hs_observed&&hs==0&&!digest.empty()&&waited==WAIT_TIMEOUT&&we==0&&parent_return==TRUE&&
        parent_error==0&&parent_pid&&ptr==TRUE&&pte==0&&ft(pc)>0&&(!parent||GetProcessId(parent)==parent_pid)&&
        active_journal&&!active_journal->failed;
    observed_pid=pid; image_hash=digest;
    identity=object({{"pid",number(pid)},{"creation_filetime",number(ft(created))},
        {"image_path_utf16le",quote(hex(path,pr&&chars<=32768?chars*2:sizeof(path)))},
        {"image_sha256",quote(digest)},{"parent_pid",number(parent_pid)},{"parent_creation_filetime",number(ft(pc))}});
    return object({{"pid",number(pid)},{"pid_error",number(pid_error)},{"path_return",signed_number(pr)},{"path_error",number(pe)},
        {"path_chars",number(chars)},{"image_path_utf16le",quote(hex(path,pr&&chars<=32768?chars*2:sizeof(path)))},
        {"times_return",signed_number(tr)},{"times_error",number(te)},{"creation_filetime",number(ft(created))},
        {"exit_filetime",number(ft(ended))},{"kernel_filetime",number(ft(kernel))},{"user_filetime",number(ft(user))},
        {"image_sha256",quote(digest)},{"hash_status",hs_observed?signed_number(hs):"null"},{"wait_result",number(waited)},{"wait_error",number(we)},
        {"parent_pid",number(parent_pid)},{"parent_query_return",signed_number(parent_return)},{"parent_query_error",number(parent_error)},
        {"parent_creation_filetime",number(ft(pc))},{"parent_times_return",signed_number(ptr)},{"parent_times_error",number(pte)}});
}
struct Session;
struct CaptureOutput : IDebugOutputCallbacks {
    LONG refs=1; Session &s; explicit CaptureOutput(Session &owner):s(owner) {}
    STDMETHOD(QueryInterface)(REFIID id,PVOID *p) { if(!p)return E_POINTER; *p=nullptr;
        if(id!=__uuidof(IUnknown)&&id!=__uuidof(IDebugOutputCallbacks))return E_NOINTERFACE;
        *p=static_cast<IDebugOutputCallbacks *>(this); AddRef(); return S_OK; }
    STDMETHOD_(ULONG,AddRef)() { return InterlockedIncrement(&refs); }
    STDMETHOD_(ULONG,Release)() { return InterlockedDecrement(&refs); }
    STDMETHOD(Output)(ULONG,PCSTR);
};
struct Events : IDebugEventCallbacks {
    LONG refs=1; Session &s; explicit Events(Session &owner):s(owner) {}
    STDMETHOD(QueryInterface)(REFIID id,PVOID *p) { if(!p)return E_POINTER; *p=nullptr;
        if(id!=__uuidof(IUnknown)&&id!=__uuidof(IDebugEventCallbacks))return E_NOINTERFACE;
        *p=static_cast<IDebugEventCallbacks *>(this); AddRef(); return S_OK; }
    STDMETHOD_(ULONG,AddRef)() { return InterlockedIncrement(&refs); }
    STDMETHOD_(ULONG,Release)() { return InterlockedDecrement(&refs); }
    STDMETHOD(GetInterestMask)(PULONG mask) { *mask=DEBUG_EVENT_CREATE_PROCESS|DEBUG_EVENT_LOAD_MODULE|DEBUG_EVENT_EXCEPTION; return S_OK; }
    STDMETHOD(Breakpoint)(PDEBUG_BREAKPOINT) { return DEBUG_STATUS_NO_CHANGE; }
    STDMETHOD(Exception)(PEXCEPTION_RECORD64,ULONG);
    STDMETHOD(CreateThread)(ULONG64,ULONG64,ULONG64) { return DEBUG_STATUS_NO_CHANGE; }
    STDMETHOD(ExitThread)(ULONG) { return DEBUG_STATUS_NO_CHANGE; }
    STDMETHOD(CreateProcess)(ULONG64,ULONG64,ULONG64,ULONG,PCSTR,PCSTR,ULONG,ULONG,ULONG64,ULONG64,ULONG64);
    STDMETHOD(ExitProcess)(ULONG) { return DEBUG_STATUS_NO_CHANGE; }
    STDMETHOD(LoadModule)(ULONG64,ULONG64,ULONG,PCSTR,PCSTR,ULONG,ULONG);
    STDMETHOD(UnloadModule)(PCSTR,ULONG64) { return DEBUG_STATUS_NO_CHANGE; }
    STDMETHOD(SystemError)(ULONG,ULONG) { return DEBUG_STATUS_NO_CHANGE; }
    STDMETHOD(SessionStatus)(ULONG) { return DEBUG_STATUS_NO_CHANGE; }
    STDMETHOD(ChangeDebuggeeState)(ULONG,ULONG64) { return DEBUG_STATUS_NO_CHANGE; }
    STDMETHOD(ChangeEngineState)(ULONG,ULONG64) { return DEBUG_STATUS_NO_CHANGE; }
    STDMETHOD(ChangeSymbolState)(ULONG,ULONG64) { return DEBUG_STATUS_NO_CHANGE; }
};
static std::string original_string(PCSTR p) {
    if(!p) return ""; size_t n=strnlen_s(p,32768); demand(n<32768,"original callback string has unknown remainder debt"); return hex(p,n+1);
}
struct Session {
    Request r; Journal j; HMODULE engine=nullptr; IDebugClient *client=nullptr; IDebugControl *control=nullptr;
    IDebugDataSpaces *memory=nullptr; IDebugSystemObjects *system=nullptr; Events events; CaptureOutput output;
    Handle controller,debugger,target,thread; unsigned long long held=0,initial_sequence=0,base=0,peb=0;
    DWORD pid=0,tid=0; ULONG engine_pid=0,engine_tid=0; bool callback_failed=false;
    EXCEPTION_RECORD64 initial_record={}; ULONG initial_first=0;
    std::string expected_host_hash,controller_identity,debugger_identity,target_identity;
    // These counters describe this fixed command-free owner's interface only.
    // They do not attest unknown external engine activity or collector provenance.
    const ULONG64 probe_sequence=0,breakpoint_sequence=0,command_sequence=0;
    explicit Session(Request request,Journal journal):r(std::move(request)),j(std::move(journal)),events(*this),output(*this) {}
    ~Session() {
        if(system)system->Release(); if(memory)memory->Release(); if(control)control->Release(); if(client)client->Release();
        if(engine)FreeLibrary(engine);
    }
    void setup(const char *name,HRESULT hr,const std::string &value="null") {
        j.frame("setup",object({{"api_name",quote(name)},{"hresult",signed_number(hr)},{"value",value}})); demand(hr==S_OK,"original setup HRESULT failed");
    }
    void counter() {
        unsigned long long tick=0; bool valid=false; auto data=qpc(r,tick,valid); j.frame("counter",data);
        demand(valid&&held&&tick>=held&&tick-held<=20*r.frequency,"original QPC failed or whole20s held checkpoint exceeded");
    }
    void owner(const char *operation="owner") {
        bool cv=false,dv=false,tv=false;
        std::string ci,di,ti,ch,dh,th; DWORD cp=0,dp=0,tp=0;
        auto co=generation(controller.value,nullptr,cv,ci,ch,cp),de=generation(debugger.value,controller.value,dv,di,dh,dp),
            ta=generation(target.value,debugger.value,tv,ti,th,tp);
        j.frame(operation,object({{"run_id",quote(r.run)},{"checkpoint_id",quote(r.checkpoint)},{"clock_epoch",quote(r.epoch)},
            {"controller",co},{"debugger",de},{"target",ta},{"probe_sequence",number(probe_sequence)},
            {"breakpoint_sequence",number(breakpoint_sequence)},{"command_sequence",number(command_sequence)}}));
        demand(cv&&dv&&tv&&cp==r.controller&&dp==GetCurrentProcessId()&&tp==pid&&th==r.candidate&&dh==expected_host_hash,
            "original retained owner generation/liveness/file binding failed");
        if(controller_identity.empty()) { controller_identity=ci; debugger_identity=di; target_identity=ti; }
        demand(ci==controller_identity&&di==debugger_identity&&ti==target_identity,"original retained generation/path/hash/parent changed");
    }
    void query(const char *name) {
        ULONG value=0; HRESULT hr=E_INVALIDARG;
        if(!strcmp(name,"IDebugControl.GetExecutionStatus"))hr=control->GetExecutionStatus(&value);
        else if(!strcmp(name,"IDebugSystemObjects.GetCurrentProcessSystemId"))hr=system->GetCurrentProcessSystemId(&value);
        else if(!strcmp(name,"IDebugSystemObjects.GetCurrentThreadSystemId"))hr=system->GetCurrentThreadSystemId(&value);
        else if(!strcmp(name,"IDebugSystemObjects.GetCurrentProcessId"))hr=system->GetCurrentProcessId(&value);
        else if(!strcmp(name,"IDebugSystemObjects.GetCurrentThreadId"))hr=system->GetCurrentThreadId(&value);
        j.frame("query",object({{"name",quote(name)},{"hresult",signed_number(hr)},{"value",number(value)}}));
        ULONG expected=!strcmp(name,"IDebugControl.GetExecutionStatus")?DEBUG_STATUS_BREAK:
            !strcmp(name,"IDebugSystemObjects.GetCurrentProcessSystemId")?pid:
            !strcmp(name,"IDebugSystemObjects.GetCurrentThreadSystemId")?tid:
            !strcmp(name,"IDebugSystemObjects.GetCurrentProcessId")?engine_pid:engine_tid;
        demand(hr==S_OK&&value==expected,"original phase query failed or successful foreign value");
    }
    void phase() {
        owner(); counter(); const char *names[]={"IDebugControl.GetExecutionStatus","IDebugSystemObjects.GetCurrentProcessSystemId",
            "IDebugSystemObjects.GetCurrentThreadSystemId","IDebugSystemObjects.GetCurrentProcessId","IDebugSystemObjects.GetCurrentThreadId"};
        for(const char *name:names) { counter(); query(name); counter(); }
        counter(); ULONG count=0; HRESULT hr=control->GetNumberBreakpoints(&count);
        j.frame("GetNumberBreakpoints",object({{"hresult",signed_number(hr)},{"count",number(count)}}));
        demand(hr==S_OK&&count==0,"original installed breakpoint query failed/nonzero"); counter();
        counter(); hr=control->IsPointer64Bit(); j.frame("pointer64",object({{"hresult",signed_number(hr)}}));
        demand(hr==S_FALSE,"original pointer-width query failed/differs"); counter(); owner();
    }
    void read(ULONG ordinal,ULONG64 address,ULONG size) {
        phase(); counter(); Bytes raw(size); ULONG actual=0; HRESULT hr=memory->ReadVirtual(address,raw.data(),size,&actual);
        if(actual<=size)raw.resize(actual);
        j.frame("read_virtual",object({{"ordinal",number(ordinal)},{"address",number(address)},{"requested_bytes",number(size)},
            {"hresult",signed_number(hr)},{"returned_bytes",number(actual)}}),raw);
        demand(hr==S_OK&&actual==size,"original partial/failed ReadVirtual retained"); counter(); phase();
    }
};
static void callback_error(Session &s,const std::exception &error) {
    s.callback_failed=true; s.j.failed=true; s.j.debt=true;
    try { s.j.frame("error",object({{"type_name",quote("callback_error")},{"message_hex",quote(hex(error.what(),strlen(error.what())))},
        {"retention_debt","true"}})); } catch(...) { s.j.debt=true; }
}
HRESULT CaptureOutput::Output(ULONG mask,PCSTR text) {
    try { s.j.frame("output",object({{"mask",number(mask)},{"text_hex",quote(original_string(text))}})); }
    catch(const std::exception &error) { callback_error(s,error); } return S_OK;
}
HRESULT Events::CreateProcess(ULONG64 image,ULONG64 process,ULONG64 base,ULONG size,PCSTR module,PCSTR name,
    ULONG checksum,ULONG timestamp,ULONG64 thread,ULONG64 thread_data,ULONG64 start) {
    try {
        HANDLE owned_process=nullptr,owned_thread=nullptr; SetLastError(0);
        BOOL dp=DuplicateHandle(GetCurrentProcess(),reinterpret_cast<HANDLE>(static_cast<ULONG_PTR>(process)),GetCurrentProcess(),&owned_process,0,FALSE,DUPLICATE_SAME_ACCESS);
        DWORD dpe=GetLastError(); SetLastError(0);
        BOOL dt=DuplicateHandle(GetCurrentProcess(),reinterpret_cast<HANDLE>(static_cast<ULONG_PTR>(thread)),GetCurrentProcess(),&owned_thread,0,FALSE,DUPLICATE_SAME_ACCESS);
        DWORD dte=GetLastError(); Handle observed_process(owned_process),observed_thread(owned_thread);
        SetLastError(0); DWORD observed_pid=GetProcessId(owned_process),pid_error=GetLastError();
        SetLastError(0); DWORD observed_tid=GetThreadId(owned_thread),tid_error=GetLastError();
        s.j.frame("callback_create",object({{"image_handle",number(image)},{"process_handle",number(process)},{"initial_thread_handle",number(thread)},
            {"base_offset",number(base)},{"module_size",number(size)},{"thread_data_offset",number(thread_data)},{"start_offset",number(start)},
            {"module_name_hex",quote(original_string(module))},{"image_name_hex",quote(original_string(name))},
            {"checksum",number(checksum)},{"timestamp",number(timestamp)},{"pid",number(observed_pid)},{"pid_error",number(pid_error)},
            {"tid",number(observed_tid)},{"tid_error",number(tid_error)},
            {"duplicate_process_return",signed_number(dp)},{"duplicate_process_error",number(dpe)},{"duplicate_thread_return",signed_number(dt)},
            {"duplicate_thread_error",number(dte)},{"owned_process_handle",number(bits(owned_process))},{"owned_thread_handle",number(bits(owned_thread))}}));
        demand(dp==TRUE&&dt==TRUE&&dpe==0&&dte==0&&observed_pid&&observed_tid&&pid_error==0&&tid_error==0,
            "retained native target generation unavailable");
        demand(!s.target.value&&!s.thread.value,"duplicate CREATE_PROCESS rejected; newly duplicated handles retired by local ownership");
        s.target.value=observed_process.release(); s.thread.value=observed_thread.release(); s.base=base;
        s.pid=observed_pid; s.tid=observed_tid;
    } catch(const std::exception &error) { callback_error(s,error); } return DEBUG_STATUS_NO_CHANGE;
}
HRESULT Events::LoadModule(ULONG64 image,ULONG64 base,ULONG size,PCSTR module,PCSTR name,ULONG checksum,ULONG timestamp) {
    try { s.j.frame("callback_load",object({{"image_handle",number(image)},{"base_offset",number(base)},{"module_size",number(size)},
        {"module_name_hex",quote(original_string(module))},{"image_name_hex",quote(original_string(name))},{"checksum",number(checksum)},{"timestamp",number(timestamp)}})); }
    catch(const std::exception &error) { callback_error(s,error); } return DEBUG_STATUS_NO_CHANGE;
}
HRESULT Events::Exception(PEXCEPTION_RECORD64 record,ULONG first) {
    try {
        unsigned long long tick=0; bool valid=false; std::string sample=qpc(s.r,tick,valid);
        s.j.frame("callback_exception",object({{"record_hex",quote(hex(record,sizeof(*record)))},{"first_chance",number(first)},{"qpc",sample}}));
        demand(valid,"original initial-event QPC query failed/changed");
        if(first&&record->ExceptionCode==EXCEPTION_BREAKPOINT&&!s.held) {
            s.held=tick; s.initial_sequence=s.j.sequence; s.initial_record=*record; s.initial_first=first;
        }
    } catch(const std::exception &error) { callback_error(s,error); } return DEBUG_STATUS_NO_CHANGE;
}
static std::string close_original(HANDLE &h,DWORD &error) { SetLastError(0); BOOL r=CloseHandle(h); error=GetLastError(); if(r)h=nullptr; return signed_number(r); }
int wmain(int argc,wchar_t **argv) {
    Journal startup;
    std::unique_ptr<Session> owner;
    bool completed=false;
    try {
        startup.begin(); active_journal=&startup; failure_sink=retain_native_failure;
        demand(argc==3,"exact original invocation requires candidate and prepared request path");
        Request r=parse_request(argv[2]); owner.reset(new Session(r,std::move(startup))); Session &s=*owner; active_journal=&s.j;
        wchar_t own[MAX_PATH]={}; SetLastError(0); DWORD own_chars=GetModuleFileNameW(nullptr,own,MAX_PATH),own_error=GetLastError();
        if(!own_chars||own_chars>=MAX_PATH)throw NativeFailure("GetModuleFileNameW",own_chars,own_error,sizeof(own),
            static_cast<ULONG>(std::min<DWORD>(own_chars,MAX_PATH)*sizeof(wchar_t)),Bytes(reinterpret_cast<unsigned char *>(own),reinterpret_cast<unsigned char *>(own)+sizeof(own)));
        long ch=0,hh=0; std::string candidate=file_hash(argv[1],ch),host=file_hash(own,hh);
        s.j.frame("invocation",object({{"request_sha256",quote(r.sha)},{"candidate_file_sha256",quote(candidate)},{"host_file_sha256",quote(host)},
            {"controller_pid",number(r.controller)},{"run_id",quote(r.run)},{"checkpoint_id",quote(r.checkpoint)},{"epoch_id",quote(r.epoch)},
            {"comparison_scope",quote("asynchronous_only")}})); demand(ch==0&&hh==0&&candidate==r.candidate,"observed file/request hash mismatch");
        s.expected_host_hash=host;
        unsigned long long origin_sample=0; bool origin_valid=false;
        s.j.frame("origin",object({{"anchor",object({{"epoch_id",quote(r.epoch)},{"frequency_hz",number(r.frequency)},
            {"origin_tick",number(r.origin)},{"origin_ns",number(r.origin_ns)}})},{"sample",qpc(r,origin_sample,origin_valid)}}));
        demand(origin_valid,"original independent QPC frequency/origin failed or changed");
        SetLastError(0); s.controller.value=OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION|SYNCHRONIZE,FALSE,r.controller);
        DWORD controller_error=GetLastError();
        if(!s.controller.value)throw NativeFailure("OpenProcess.controller",0,controller_error);
        SetLastError(0); s.debugger.value=OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION|SYNCHRONIZE,FALSE,GetCurrentProcessId());
        DWORD debugger_error=GetLastError();
        if(!s.debugger.value)throw NativeFailure("OpenProcess.debugger",0,debugger_error);
        wchar_t system_dir[MAX_PATH]={},engine_path[MAX_PATH]={}; SetLastError(0);
        DWORD directory_chars=GetSystemDirectoryW(system_dir,MAX_PATH),directory_error=GetLastError();
        if(!directory_chars||directory_chars>=MAX_PATH)throw NativeFailure("GetSystemDirectoryW",directory_chars,directory_error);
        demand(swprintf_s(engine_path,L"%s\\dbgeng.dll",system_dir)>0,"bounded x86 system engine path formatting failed");
        SetLastError(0); s.engine=LoadLibraryExW(engine_path,nullptr,LOAD_LIBRARY_SEARCH_SYSTEM32); DWORD load_error=GetLastError();
        if(!s.engine)throw NativeFailure("LoadLibraryExW",0,load_error);
        SetLastError(0); auto create=reinterpret_cast<HRESULT(WINAPI *)(REFIID,PVOID *)>(GetProcAddress(s.engine,"DebugCreate")); DWORD symbol_error=GetLastError();
        if(!create)throw NativeFailure("GetProcAddress.DebugCreate",0,symbol_error);
        HRESULT hr=create(__uuidof(IDebugClient),reinterpret_cast<PVOID *>(&s.client)); s.setup("DebugCreate",hr,number(bits(reinterpret_cast<HANDLE>(s.client))));
        hr=s.client->QueryInterface(__uuidof(IDebugControl),reinterpret_cast<PVOID *>(&s.control)); s.setup("QueryInterface.control",hr,number(bits(reinterpret_cast<HANDLE>(s.control))));
        hr=s.client->QueryInterface(__uuidof(IDebugDataSpaces),reinterpret_cast<PVOID *>(&s.memory)); s.setup("QueryInterface.memory",hr,number(bits(reinterpret_cast<HANDLE>(s.memory))));
        hr=s.client->QueryInterface(__uuidof(IDebugSystemObjects),reinterpret_cast<PVOID *>(&s.system)); s.setup("QueryInterface.system",hr,number(bits(reinterpret_cast<HANDLE>(s.system))));
        s.setup("SetEventCallbacks",s.client->SetEventCallbacks(&s.events));
        s.setup("SetOutputCallbacks",s.client->SetOutputCallbacks(&s.output));
        s.setup("AddEngineOptions",s.control->AddEngineOptions(DEBUG_ENGOPT_INITIAL_BREAK|DEBUG_ENGOPT_DISALLOW_SHELL_COMMANDS));
        ULONG options=0; hr=s.control->GetEngineOptions(&options); s.setup("GetEngineOptions",hr,number(options));
        demand((options&(DEBUG_ENGOPT_INITIAL_BREAK|DEBUG_ENGOPT_DISALLOW_SHELL_COMMANDS))==
            (DEBUG_ENGOPT_INITIAL_BREAK|DEBUG_ENGOPT_DISALLOW_SHELL_COMMANDS),"original fixed engine options not retained");
        char target[MAX_PATH]={}; SetLastError(0);
        int converted=WideCharToMultiByte(CP_UTF8,WC_ERR_INVALID_CHARS,argv[1],-1,target,MAX_PATH,nullptr,nullptr); DWORD convert_error=GetLastError();
        if(converted<=0)throw NativeFailure("WideCharToMultiByte",converted,convert_error,sizeof(target),0,
            Bytes(reinterpret_cast<unsigned char *>(target),reinterpret_cast<unsigned char *>(target)+sizeof(target)));
        for(unsigned char c:std::string(target))demand(c<128,"initial native source scope requires ASCII target path");
        std::string command="\""+std::string(target)+"\""; std::vector<char> mutable_command(command.begin(),command.end()); mutable_command.push_back(0);
        s.j.frame("launch",object({{"target_path_utf16le",quote(hex(argv[1],(wcslen(argv[1])+1)*sizeof(wchar_t)))},
            {"command_hex",quote(hex(mutable_command.data(),mutable_command.size()))},
            {"create_flags",number(DEBUG_ONLY_THIS_PROCESS|CREATE_NO_WINDOW)}}));
        s.setup("CreateProcess",s.client->CreateProcess(0,mutable_command.data(),DEBUG_ONLY_THIS_PROCESS|CREATE_NO_WINDOW));
        hr=s.control->WaitForEvent(0,15000); s.j.frame("wait_event",object({{"hresult",signed_number(hr)},{"flags","0"},{"timeout_ms","15000"}}));
        demand(hr==S_OK&&!s.callback_failed&&s.held&&s.target.value&&s.thread.value,"original initial loader event/ownership unavailable");
        ULONG type=0,process=0,thread=0,extra_used=0,description_used=0; unsigned char extra[256]={},description[1024]={};
        hr=s.control->GetLastEventInformation(&type,&process,&thread,extra,sizeof(extra),&extra_used,reinterpret_cast<PSTR>(description),sizeof(description),&description_used);
        s.j.frame("event",object({{"hresult",signed_number(hr)},{"type",number(type)},{"engine_pid",number(process)},{"engine_tid",number(thread)},
            {"extra_hex",quote(hex(extra,sizeof(extra)))},{"description_hex",quote(hex(description,sizeof(description)))},
            {"extra_used",number(extra_used)},{"description_used",number(description_used)}}));
        demand(hr==S_OK&&type==DEBUG_EVENT_EXCEPTION&&extra_used==sizeof(DEBUG_LAST_EVENT_INFO_EXCEPTION),"original first event truncated/incompatible");
        auto event=reinterpret_cast<DEBUG_LAST_EVENT_INFO_EXCEPTION *>(extra);
        const auto &observed=event->ExceptionRecord; const auto &initial=s.initial_record;
        bool same=event->FirstChance==s.initial_first&&initial.NumberParameters<=15&&observed.NumberParameters==initial.NumberParameters&&
            observed.ExceptionCode==initial.ExceptionCode&&observed.ExceptionFlags==initial.ExceptionFlags&&
            observed.ExceptionRecord==initial.ExceptionRecord&&observed.ExceptionAddress==initial.ExceptionAddress;
        for(ULONG i=0;same&&i<initial.NumberParameters;++i)same=observed.ExceptionInformation[i]==initial.ExceptionInformation[i];
        demand(same&&event->FirstChance==1&&observed.ExceptionCode==EXCEPTION_BREAKPOINT,"original initial callback/event semantic payload differs");
        s.engine_pid=process; s.engine_tid=thread;
        hr=s.system->GetCurrentProcessPeb(&s.peb); s.j.frame("peb",object({{"hresult",signed_number(hr)},{"address",number(s.peb)}}));
        demand(hr==S_OK&&s.peb>=0x10000&&s.peb<=0x7ffe0000-12&&s.base>=0x10000&&s.base<=0x7ffe0000-r.image_size,"original PEB/module extent invalid");
        unsigned long long held_tick=0; bool held_valid=false; auto held_sample=qpc(r,held_tick,held_valid);
        // Retain the original callback sample separately; held_start_tick is
        // derived by the offline adapter from that exact referenced packet.
        s.j.frame("held",object({{"qpc",held_sample},{"initial_exception_sequence",number(s.initial_sequence)}}));
        demand(held_valid&&held_tick>=s.held&&held_tick-s.held<=20*r.frequency,"original held QPC failed or exceeded unchanged checkpoint");
        s.owner("startup_owner"); s.counter(); s.read(0,s.peb+8,4);
        ULONG ordinal=1; for(const auto &row:r.rows)s.read(ordinal++,s.base+row.first,row.second);
        s.counter(); completed=true;
    } catch(const std::exception &error) {
        Journal &j=owner?owner->j:startup; j.failed=true;
        try {
            if(auto native=dynamic_cast<const NativeFailure *>(&error))j.frame("native_failure",native->original,native->prefix);
            j.frame("error",object({{"type_name",quote("native_error")},{"message_hex",quote(hex(error.what(),strlen(error.what())))},
                {"retention_debt",j.debt?"true":"false"}}));
        } catch(...) { j.debt=true; }
    }
    if(!owner) {
        try { startup.frame("finish",object({{"status",quote("failed")},{"frame_count",number(startup.sequence)},
            {"raw_bytes",number(startup.raw_bytes)},{"metadata_bytes",number(startup.metadata_bytes)},
            {"comparison_scope",quote("asynchronous_only")}})); } catch(...) {}
        active_journal=nullptr; failure_sink=nullptr; return 2;
    }
    Session &s=*owner;
    try {
        HRESULT ended=s.client?s.client->EndSession(DEBUG_END_ACTIVE_TERMINATE):E_UNEXPECTED;
        unsigned long long stopped=0; bool stop_valid=false; auto stopped_sample=qpc(s.r,stopped,stop_valid); ULONG status=0;
        HRESULT status_hr=s.control?s.control->GetExecutionStatus(&status):E_UNEXPECTED;
        s.j.frame("stop",object({{"end_session_hresult",s.client?signed_number(ended):"null"},{"qpc",stopped_sample},
            {"execution_status",object({{"name",quote("IDebugControl.GetExecutionStatus")},{"hresult",s.control?signed_number(status_hr):"null"},{"value",number(status)}})}}));
        completed=completed&&stop_valid&&ended==S_OK&&status_hr==S_OK&&status==DEBUG_STATUS_NO_DEBUGGEE&&s.held&&stopped>=s.held&&stopped-s.held<=20*s.r.frequency;
        SetLastError(0); DWORD waited=WaitForSingleObject(s.target.value,5000); DWORD wait_error=GetLastError();
        // Query fresh final times/exit after the retained wait. Do not reuse a
        // pre-wait zero exit FILETIME or STILL_ACTIVE observation as cleanup.
        FILETIME c={},x={},k={},u={}; SetLastError(0); BOOL times=GetProcessTimes(s.target.value,&c,&x,&k,&u); DWORD times_error=GetLastError();
        SetLastError(0); DWORD pid=GetProcessId(s.target.value),pid_error=GetLastError();
        DWORD exit_code=0; SetLastError(0); BOOL exited=GetExitCodeProcess(s.target.value,&exit_code); DWORD exit_error=GetLastError();
        DWORD target_error=0,thread_error=0,controller_error=0,debugger_error=0;
        auto tc=close_original(s.target.value,target_error),thc=close_original(s.thread.value,thread_error),cc=close_original(s.controller.value,controller_error),dc=close_original(s.debugger.value,debugger_error);
        HRESULT event_callbacks=s.client?s.client->SetEventCallbacks(nullptr):E_UNEXPECTED;
        HRESULT output_callbacks=s.client?s.client->SetOutputCallbacks(nullptr):E_UNEXPECTED;
        s.j.frame("cleanup",object({{"target_pid",number(pid)},{"target_pid_error",number(pid_error)},{"target_wait",number(waited)},{"target_wait_error",number(wait_error)},
            {"target_creation_filetime",number(ft(c))},{"target_exit_filetime",number(ft(x))},{"target_kernel_filetime",number(ft(k))},{"target_user_filetime",number(ft(u))},
            {"target_times_return",signed_number(times)},{"target_times_error",number(times_error)},{"target_exit_return",signed_number(exited)},
            {"target_exit_error",number(exit_error)},{"target_exit_code",number(exit_code)},{"target_close",tc},{"target_close_error",number(target_error)},
            {"thread_close",thc},{"thread_close_error",number(thread_error)},{"controller_close",cc},{"controller_close_error",number(controller_error)},
            {"debugger_close",dc},{"debugger_close_error",number(debugger_error)},
            {"event_callbacks_hresult",s.client?signed_number(event_callbacks):"null"},
            {"output_callbacks_hresult",s.client?signed_number(output_callbacks):"null"}}));
        completed=completed&&times&&exited&&pid==s.pid&&pid_error==0&&waited==WAIT_OBJECT_0&&tc!="0"&&thc!="0"&&cc!="0"&&dc!="0"&&
            event_callbacks==S_OK&&output_callbacks==S_OK&&!s.j.debt&&!s.j.failed;
        s.j.frame("finish",object({{"status",quote(completed?"complete":"failed")},{"frame_count",number(s.j.sequence)},
            {"raw_bytes",number(s.j.raw_bytes)},{"metadata_bytes",number(s.j.metadata_bytes)},{"comparison_scope",quote("asynchronous_only")}}));
    } catch(...) { active_journal=nullptr; failure_sink=nullptr; return 3; }
    active_journal=nullptr; failure_sink=nullptr;
    return completed?0:3;
}
'''

prepare_native_plan, prepare_request, inspect_request = _factory()
