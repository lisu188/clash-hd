"""Versioned source preparation for an initial-hold immutable-byte comparator.

No compiler, native adapter, storage adapter or process launch is provided here.
The frozen V1 batch and expected-byte issuer are read unchanged. Production
requests are live opaque capabilities; a manifest or cloned dataclass cannot
choose executable ranges, exemptions, expected bytes or generated C++.
"""
from __future__ import annotations

import ast
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
SOURCE = "tools/hidden_soak_loader_compare_native.py"
ADAPTER = "tools/hidden_soak_loader_compare_native_adapter.py"
EXPECTED = "tools/hidden_soak_loader_expected.py"
EXPECTED_SHA256 = "976495cb684cbd744672af20de60694a77392cde53ed0327321357657441f146"
V1 = "tools/hidden_soak_loader_native.py"
V1_SHA256 = "6504fb7aeeb7f5c86c3024c124cc715936e49e01944378e74170909cf780d287"
REQUEST_MAGIC, ARCHIVE_MAGIC = b"CLHDCP2\0", b"CLHDCR2\0"
REQUEST_PREFIX = struct.Struct("<8s4I3Q")
REQUEST_SIZE = REQUEST_PREFIX.size + 3 * 16 + 6 * 32 + 32
IO_FOOTER = struct.Struct("<iIIIiI")
COMPARISON_RECORD = struct.Struct("<10I3q")
MAX_FRAMES, MAX_READS = 32768, 512
MAX_FRAME_JSON, MAX_FRAME_RAW = 512 * 1024, 65539
COMPARISON_JSON = 4096
EXTRA_METADATA = MAX_FRAME_JSON + 8 + (2 + 2 * MAX_READS) * (COMPARISON_JSON + 8)
FOOTER_ALLOWANCE = MAX_FRAMES * IO_FOOTER.size
MAX_METADATA = 8 * 1024**2 + EXTRA_METADATA + FOOTER_ALLOWANCE
MAX_FAILURE_METADATA = MAX_METADATA + 1024**2
MAX_RAW = 16 * 1024**2 + MAX_READS * COMPARISON_RECORD.size
MAX_FAILURE_RAW = MAX_RAW + MAX_FRAME_RAW
FALSE_CLAIMS = {name: False for name in (
    "passed", "native_producer_provenance_verified", "native_read_coherence_verified",
    "native_generation_ownership_verified", "native_job_cleanup_verified", "host_cleanup_complete",
    "storage_durability_verified", "receipt_tail_durability_verified", "loaded_candidate_verified",
    "whole_image_verified", "loaded_probe_verified", "probe_executed", "running_duration_verified",
    "runtime_acceptance", "release_acceptance", "manual_input_verified", "promotion_ready", "stable")}


def _require(value, message):
    if not value:
        raise ValueError(message)


def _sha(raw):
    _require(type(raw) is bytes, "exact byte string required")
    return hashlib.sha256(raw).hexdigest()


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                      allow_nan=False).encode("ascii")


def retention_budget():
    payload = 17121324
    journal = MAX_FAILURE_RAW + 2 * MAX_FAILURE_METADATA
    archive = MAX_FAILURE_RAW + MAX_FAILURE_METADATA
    return dict(request_bytes=REQUEST_SIZE, request_atomic_temporary_bytes=REQUEST_SIZE,
        expected_payload_bytes=payload, expected_payload_atomic_temporary_bytes=payload,
        main_packet_prefix_bytes=8, io_footer_bytes=IO_FOOTER.size,
        maximum_frames=MAX_FRAMES, comparison_record_bytes=COMPARISON_RECORD.size,
        comparison_json_bytes=COMPARISON_JSON, extra_comparison_metadata_bytes=EXTRA_METADATA,
        maximum_footer_bytes=FOOTER_ALLOWANCE, normal_metadata_bytes=MAX_METADATA,
        failure_metadata_bytes=MAX_FAILURE_METADATA, normal_raw_bytes=MAX_RAW,
        failure_raw_bytes=MAX_FAILURE_RAW, native_journal_peak_bytes=journal,
        separate_complete_archive_copy_bytes=archive,
        known_peak_bytes=2 * payload + 2 * REQUEST_SIZE + journal + archive,
        exclusions=["compiler/source/object/binary outputs and candidate/assets",
                    "independent build/launch/generation/job/storage receipts",
                    "original/source/expected-model/native packet RAM", "unknown native output debt"],
        receipt_tail="Footer append/flush cannot recursively attest its own durability; independent storage remains required.")


@dataclass(frozen=True, eq=False, slots=True, weakref_slot=True)
class ComparisonPlan:
    binding_json: str


@dataclass(frozen=True, eq=False, slots=True, weakref_slot=True)
class ComparisonRequest:
    binding_json: str


@dataclass(frozen=True)
class ComparisonFacts:
    metadata_json: str
    request_bytes: bytes
    expected_payload: bytes
    host_source: bytes
    descriptors: tuple
    fixups: tuple
    expected_raw: bytes
    model_chunks: object
    check_sources: object


def _replace(source, old, new):
    _require(source.count(old) == 1, "frozen V1 source replacement is not uniquely authenticated")
    return source.replace(old, new)


def _render(base, metadata, request, payload):
    """Exact bounded transformations of the fixed immutable V1 C++ source."""
    constants = ("\nstatic const char *fixed_request_sha=\"" + _sha(request) + "\";\n" +
                 "static const char *fixed_payload_sha=\"" + _sha(payload) + "\";\n")
    source = _replace(base, "struct Request {", constants + "struct Request {")
    start, end = source.index("struct Request {"), source.index("static std::string qpc(")
    source = source[:start] + REQUEST_CPP + source[end:]
    start, end = source.index("struct Journal {"), source.index("static Journal *active_journal")
    source = source[:start] + JOURNAL_CPP + source[end:]
    source = _replace(source, "static Journal *active_journal=nullptr;",
                      "static Journal *active_journal=nullptr;" + BINDING_CPP)
    source = _replace(source,
        "static std::string qpc(const Request &r,unsigned long long &tick,bool &valid) {",
        "static std::string qpc(const Request &r,unsigned long long &tick,bool &valid,LONGLONG *original_tick=nullptr) {")
    source = _replace(source,
        "tick=static_cast<unsigned long long>(counter.QuadPart);",
        "tick=static_cast<unsigned long long>(counter.QuadPart); if(original_tick)*original_tick=counter.QuadPart;")
    start, end = source.index("    void read(ULONG ordinal"), source.index("\n};\nstatic void callback_error")
    source = source[:start] + READ_CPP + source[end:]
    source = _replace(source, 'demand(argc==3,"exact original invocation requires candidate and prepared request path");',
        'demand(argc==4,"exact V2 invocation requires candidate, request and expected payload paths");')
    source = _replace(source, 'Request r=parse_request(argv[2]);', 'Request r=parse_request(argv[2],argv[3]);')
    source = source.replace('quote("asynchronous_only")', 'quote("immutable_scope_initial_hold")')
    source = _replace(source, 's.counter(); completed=true;',
        's.phase(); s.j.frame("comparison_complete",object({{"read_count",number(ordinal)},'
        '{"result_count",number(s.comparison_results)},{"compared_bytes",number(s.compared_bytes)},'
        '{"expected_payload_sha256",quote(s.r.payload_sha)}})); s.counter(); completed=true;')
    source = _replace(source, 'EXCEPTION_RECORD64 initial_record={}; ULONG initial_first=0;',
        'EXCEPTION_RECORD64 initial_record={}; ULONG initial_first=0;\n'
        '    ULONG comparison_results=0; unsigned long long compared_bytes=0;\n'
        '    const DWORD native_owner_tid=GetCurrentThreadId();')
    source = _replace(source, '        bool cv=false,dv=false,tv=false;',
        '        DWORD current_native_tid=GetCurrentThreadId();\n        bool cv=false,dv=false,tv=false;')
    source = _replace(source, '        j.frame(operation,object({{"run_id",quote(r.run)},',
        '        j.frame(operation,object({{"native_owner_tid",number(native_owner_tid)},'
        '{"current_native_tid",number(current_native_tid)},{"run_id",quote(r.run)},')
    source = _replace(source,
        '        demand(cv&&dv&&tv&&cp==r.controller&&dp==GetCurrentProcessId()&&tp==pid&&th==r.candidate&&dh==expected_host_hash,',
        '        demand(native_owner_tid&&current_native_tid==native_owner_tid&&cv&&dv&&tv&&cp==r.controller&&dp==GetCurrentProcessId()&&tp==pid&&th==r.candidate&&dh==expected_host_hash,')
    source = _replace(source, 's.expected_host_hash=host;',
        's.expected_host_hash=host; s.j.frame("comparison_begin",object({'
        '{"expected_payload_sha256",quote(r.payload_sha)},{"read_count",number(r.rows.size()+1)},'
        '{"scope",quote("canonical_headers_executable_raw_and_zero_extents_only")}}));')
    # Packet limits include JSON, framing and the original main-I/O footer.
    source = source.replace("@NORMAL_META@", str(MAX_METADATA)).replace("@FAIL_META@", str(MAX_FAILURE_METADATA))
    source = source.replace("@NORMAL_RAW@", str(MAX_RAW)).replace("@FAIL_RAW@", str(MAX_FAILURE_RAW))
    source = source.replace("@MAX_FRAMES@", str(MAX_FRAMES))
    _require("@" not in source, "unresolved source placeholder")
    return source.encode("ascii")


def _private_preparation(original, contract, imported_source):
    own, adapter, expected_path, v1_path = (ROOT / name for name in (SOURCE, ADAPTER, EXPECTED, V1))
    expected_raw, v1_raw, adapter_raw = expected_path.read_bytes(), v1_path.read_bytes(), adapter.read_bytes()
    _require(own.read_bytes() == imported_source and _sha(expected_raw) == EXPECTED_SHA256 and
             _sha(v1_raw) == V1_SHA256, "fixed canonical producer sources differ")
    prefix = "_clash_compare_" + uuid.uuid4().hex
    created = {}
    try:
        modules = {}
        for suffix, raw, path in (("expected", expected_raw, expected_path), ("v1", v1_raw, v1_path)):
            name = prefix + "_" + suffix
            _require(name not in sys.modules, "private source namespace collision")
            module = types.ModuleType(name); module.__file__ = str(path)
            sys.modules[name] = module; created[name] = module
            exec(compile(raw, str(path), "exec"), module.__dict__); modules[suffix] = module
        expected = modules["expected"]
        plan = expected.prepare_expected_plan(original, contract)
        snapshots = ((own, imported_source), (adapter, adapter_raw), (expected_path, expected_raw), (v1_path, v1_raw))
        def check():
            _require(tuple((path, path.read_bytes()) for path, _ in snapshots) == snapshots,
                     "source graph changed after compilation/admission")
        check()
        def issue(authority):
            check(); payload = expected.issue_expected_payload(plan, authority)
            facts = expected.inspect_expected_payload(payload)
            data = json.loads(facts.metadata_json)
            parsed, descriptors, fixups, raw = expected._decode(facts.payload_bytes)
            _require(data == parsed, "opaque expected metadata differs")
            def model(base):
                check(); result = expected.model_loaded_chunks(payload, base)
                _require(result.report().get("modeled_source_bytes_derived") is True, "fixed model failed")
                check(); return result.modeled_chunks
            check()
            closure = _sha(_canonical({str(path.relative_to(ROOT)).replace("\\", "/"): _sha(raw)
                                      for path, raw in snapshots}))
            return data, facts.payload_bytes, descriptors, fixups, raw, model, closure
        return issue, modules["v1"].HARNESS, check, _sha(imported_source), _sha(adapter_raw)
    finally:
        for name, module in created.items():
            if sys.modules.get(name) is module:
                del sys.modules[name]


def _closed_preparation(raw, path):
    """Remove only the exact terminal factory call; freeze all dependencies privately."""
    tree = ast.parse(raw, filename=str(path))
    names = ("prepare_comparison_plan", "prepare_comparison_request", "inspect_comparison_request")
    matches = [node for node in tree.body if isinstance(node, ast.Assign) and
               any(isinstance(target, ast.Tuple) and tuple(getattr(item, "id", None) for item in target.elts) == names
                   for target in node.targets)]
    _require(len(matches) == 1 and matches[0] is tree.body[-1], "unique terminal factory assignment required")
    node = matches[0]
    _require(len(node.targets) == 1 and isinstance(node.value, ast.Call) and
             isinstance(node.value.func, ast.Name) and node.value.func.id == "_factory" and
             not node.value.args and not node.value.keywords, "exact terminal factory AST required")
    _require(sum(type(item) is ast.Call and type(item.func) is ast.Name and item.func.id == "_factory"
                 for item in ast.walk(tree)) == 1, "only the authenticated terminal factory may issue APIs")
    tree.body.pop()
    name = "_clash_compare_admission_" + uuid.uuid4().hex
    _require(name not in sys.modules, "private admission namespace collision")
    module = types.ModuleType(name); module.__file__ = str(path)
    sys.modules[name] = module
    try:
        exec(compile(tree, str(path), "exec"), module.__dict__)
        return module._private_preparation, module._render
    finally:
        if sys.modules.get(name) is module:
            del sys.modules[name]


def _factory(*, _preparation=None):
    """Fixture registries remain separate from the public production registry."""
    own = Path(__file__).resolve(); raw = own.read_bytes()
    prepare, render = _closed_preparation(raw, own) if _preparation is None else (_preparation, _render)
    require, hasher, dumps, reference = _require, hashlib.sha256, json.dumps, weakref.ref
    def sha(value):
        require(type(value) is bytes, "exact byte string required")
        return hasher(value).hexdigest()
    def canonical(value):
        return dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                     allow_nan=False).encode("ascii")
    plan_class, request_class, facts_class = ComparisonPlan, ComparisonRequest, ComparisonFacts
    prefix, request_magic = REQUEST_PREFIX, REQUEST_MAGIC
    request_size, expected_pin, v1_pin = REQUEST_SIZE, EXPECTED_SHA256, V1_SHA256
    claims = dict(FALSE_CLAIMS)
    plans, requests = {}, {}
    def guard():
        require(own.read_bytes() == raw, "imported comparator source changed")
    def retain(registry, obj, state):
        key = id(obj)
        def retired(reference):
            if key in registry and registry[key][0] is reference:
                del registry[key]
        registry[key] = (reference(obj, retired), obj.binding_json, state)
        return obj
    def admit(registry, cls, obj):
        guard(); entry = registry.get(id(obj))
        require(type(obj) is cls and entry is not None and entry[0]() is obj and entry[1] == obj.binding_json,
                 "genuine live source-issued opaque capability required")
        entry[2][2]() if registry is plans else entry[2][-1]()
        return entry[2]
    def prepare_comparison_plan(original, contract):
        guard(); state = prepare(original, contract, raw); guard()
        return retain(plans, plan_class(canonical(dict(schema="loader_compare_plan_v2", claims=claims)).decode()), state)
    def prepare_comparison_request(plan, authority):
        issue, base, check, source_sha, adapter_sha = admit(plans, plan_class, plan)
        data, payload, descriptors, fixups, expected_raw, model, closure = issue(authority)
        a = data["authority"]
        hashes = (data["candidate_sha256"], sha(payload), data["probe_sha256"], data["contract_sha256"],
                  data["source_closure_sha256"], closure)
        request = prefix.pack(request_magic, len(descriptors), data["preferred_base"], data["image_size"],
            a["controller_pid"], a["frequency_hz"], a["origin_tick"], a["origin_ns"])
        request += b"".join(bytes.fromhex(a[name]) for name in ("run_id", "checkpoint_id", "epoch_id"))
        request += b"".join(bytes.fromhex(value) for value in hashes)
        request += hasher(request).digest()
        require(len(request) == request_size, "fixed request extent differs")
        metadata = dict(schema="loader_compare_request_v2", **{key: data[key] for key in (
            "profile", "resolution", "stage", "recipe_revision", "candidate_sha256", "probe_sha256",
            "contract_sha256", "source_closure_sha256", "preferred_base", "image_size", "headers_size")},
            **a, producer_source_closure_sha256=closure, expected_payload_sha256=sha(payload),
            expected_metadata_sha256=sha(canonical(data)), expected_issuer_source_sha256=expected_pin,
            native_v1_source_sha256=v1_pin, native_source_sha256=source_sha, adapter_source_sha256=adapter_sha,
            request_sha256=sha(request), chunk_count=len(descriptors), highlow_count=len(fixups), claims=claims)
        host = render(base, metadata, request, payload)
        metadata["host_source_sha256"] = sha(host)
        binding = canonical(metadata).decode("ascii")
        check(); guard()
        state = (binding, request, payload, host, descriptors, fixups, expected_raw, model, check)
        return retain(requests, request_class(binding), state)
    def inspect_comparison_request(request):
        state = admit(requests, request_class, request)
        return facts_class(*state)
    return prepare_comparison_plan, prepare_comparison_request, inspect_comparison_request


REQUEST_CPP = r'''
static std::vector<std::string> original_buffer_hashes;
static std::string bytes_hash(const Bytes &bytes) {
    BCRYPT_ALG_HANDLE algorithm=nullptr;
    NTSTATUS opened=BCryptOpenAlgorithmProvider(&algorithm,BCRYPT_SHA256_ALGORITHM,nullptr,0);
    if(opened!=0) {
        auto observation=object({{"input_bytes",number(bytes.size())},{"open_status",signed_number(opened)},
            {"hash_status","null"},{"close_status","null"},{"digest_hex","null"}});
        NativeFailure failure("BCryptOpenAlgorithmProvider.buffer",opened,0);
        failure.original=object({{"api_name",quote("BCryptOpenAlgorithmProvider.buffer")},{"native_return",signed_number(opened)},
            {"native_error","0"},{"requested_bytes","0"},{"returned_bytes","0"},{"detail_hex",quote(hex(observation.data(),observation.size()))}});
        throw failure;
    }
    unsigned char digest[32]={}; NTSTATUS hashed=BCryptHash(algorithm,nullptr,0,const_cast<PUCHAR>(bytes.data()),static_cast<ULONG>(bytes.size()),digest,32);
    NTSTATUS closed=BCryptCloseAlgorithmProvider(algorithm,0);
    auto observation=object({{"input_bytes",number(bytes.size())},{"open_status",signed_number(opened)},
        {"hash_status",signed_number(hashed)},{"close_status",signed_number(closed)},{"digest_hex",quote(hex(digest,32))}});
    original_buffer_hashes.push_back(observation);
    if(hashed!=0||closed!=0) {
        NativeFailure failure(hashed!=0?"BCryptHash.buffer":"BCryptCloseAlgorithmProvider.buffer",hashed!=0?hashed:closed,0);
        failure.original=object({{"api_name",quote(hashed!=0?"BCryptHash.buffer":"BCryptCloseAlgorithmProvider.buffer")},
            {"native_return",signed_number(hashed!=0?hashed:closed)},{"native_error","0"},{"requested_bytes","0"},
            {"returned_bytes","0"},{"detail_hex",quote(hex(observation.data(),observation.size()))}});
        throw failure;
    }
    return hex(digest,32);
}
static ULONG word(const Bytes &b,size_t at) { demand(at<=b.size()&&4<=b.size()-at,"whole bounded DWORD required"); ULONG v=0; memcpy(&v,b.data()+at,4); return v; }
struct Descriptor { ULONG ordinal,rva,size,raw_offset,first,count,range,kind; };
static_assert(sizeof(Descriptor)==32,"fixed descriptor width");
struct Request {
    ULONG preferred=0,image_size=0,controller=0,headers=0,base_field=0;
    unsigned long long frequency=0,origin=0,origin_ns=0;
    std::string candidate,run,checkpoint,epoch,sha,payload_sha;
    Bytes payload,expected; std::vector<Descriptor> descriptors; std::vector<ULONG> fixups;
    std::vector<std::pair<ULONG,ULONG>> rows;
};
static void retain_expected_binding(const Request &,const wchar_t *,const wchar_t *);
static Request parse_request(const wchar_t *path,const wchar_t *payload_path) {
    Bytes b=read_file(path); demand(b.size()==320&&!memcmp(b.data(),"CLHDCP2\0",8),"exact fixed V2 request required");
    Request r; ULONG count=word(b,8); r.preferred=word(b,12); r.image_size=word(b,16); r.controller=word(b,20);
    memcpy(&r.frequency,b.data()+24,8); memcpy(&r.origin,b.data()+32,8); memcpy(&r.origin_ns,b.data()+40,8);
    r.run=hex(b.data()+48,16); r.checkpoint=hex(b.data()+64,16); r.epoch=hex(b.data()+80,16);
    r.candidate=hex(b.data()+96,32); r.payload_sha=hex(b.data()+128,32); r.sha=bytes_hash(b);
    demand(r.sha==fixed_request_sha&&r.payload_sha==fixed_payload_sha,"compiled fixed request/payload binding differs");
    Bytes body(b.begin(),b.end()-32); demand(bytes_hash(body)==hex(b.data()+288,32),"original request trailer differs");
    demand(count&&count<=511&&r.controller&&r.frequency&&r.frequency<=1000000000&&r.origin&&r.origin_ns,
        "bounded original request authority required");
    r.payload=read_file(payload_path); demand(r.payload.size()<=17121324&&r.payload.size()>=80,"bounded complete expected payload required");
    demand(bytes_hash(r.payload)==r.payload_sha&&!memcmp(r.payload.data(),"CLHDLE1\0",8)&&word(r.payload,8)==1,"fixed source-issued payload differs");
    ULONG meta=word(r.payload,12),chunks=word(r.payload,16),fixes=word(r.payload,20),raw=word(r.payload,24);
    r.headers=word(r.payload,36); r.base_field=word(r.payload,40);
    unsigned long long extent=48ULL+meta+32ULL*chunks+4ULL*fixes+raw+32;
    demand(meta&&meta<=65536&&chunks==count&&fixes<=65536&&raw&&raw<=16*1024*1024-4&&extent==r.payload.size()&&
        word(r.payload,28)==r.preferred&&word(r.payload,32)==r.image_size&&word(r.payload,44)==0&&
        r.preferred>=0x10000&&r.preferred%0x10000==0&&r.image_size&&r.image_size<=64*1024*1024&&r.headers&&
        r.headers<=r.image_size&&r.base_field<=r.headers&&4<=r.headers-r.base_field,"exact complete payload extents differ");
    Bytes pbody(r.payload.begin(),r.payload.end()-32);
    demand(bytes_hash(pbody)==hex(r.payload.data()+r.payload.size()-32,32),"original payload trailer differs");
    size_t at=48+meta; r.descriptors.resize(chunks); memcpy(r.descriptors.data(),r.payload.data()+at,chunks*32); at+=chunks*32;
    r.fixups.resize(fixes); if(fixes)memcpy(r.fixups.data(),r.payload.data()+at,fixes*4); at+=fixes*4;
    r.expected.assign(r.payload.begin()+at,r.payload.begin()+at+raw);
    std::vector<bool> owned(fixes,false); ULONG cursor=0,header_total=0,prev_range=0,prev_kind=0,prev_end=0;
    for(ULONG i=0;i<fixes;++i)demand(r.fixups[i]<=r.image_size&&4<=r.image_size-r.fixups[i]&&
        (!i||r.fixups[i-1]+4<=r.fixups[i]),"duplicate/reordered/out-of-image HIGHLOW");
    for(ULONG i=0;i<chunks;++i) {
        auto d=r.descriptors[i]; demand(d.ordinal==i&&d.size&&d.size<=65539&&d.raw_offset==cursor&&
            d.rva<=r.image_size&&d.size<=r.image_size-d.rva&&d.kind<=2&&d.first<=fixes&&d.count<=fixes-d.first&&
            (d.count||d.first==0)&&d.range>=prev_range&&d.range<=prev_range+1,"invalid exact descriptor");
        if(!i)demand(d.rva==0&&d.range==0&&d.kind==0,"complete headers first");
        else if(d.range==prev_range)demand(d.rva==prev_end&&d.kind==prev_kind,"source chunk gap/kind differs");
        else demand(d.rva>=prev_end&&d.kind!=0&&(d.kind!=2||(prev_kind==1&&d.rva==prev_end)),"source raw/zero range differs");
        demand(d.raw_offset<=raw&&d.size<=raw-d.raw_offset,"complete expected raw extent differs");
        if(d.kind==0) { demand(d.range==0,"header alias"); header_total+=d.size; }
        if(d.kind==2) { demand(d.count==0,"zero tail fixup forbidden"); for(ULONG x=0;x<d.size;++x)demand(r.expected[d.raw_offset+x]==0,"zero tail differs"); }
        for(ULONG x=d.first;x<d.first+d.count;++x) {
            ULONG f=r.fixups[x]; demand(!owned[x]&&f>=d.rva&&f-d.rva<=d.size&&4<=d.size-(f-d.rva)&&
                (f+4<=r.base_field||f>=r.base_field+4),"split/aliased/header-ImageBase HIGHLOW"); owned[x]=true;
        }
        cursor+=d.size; prev_range=d.range; prev_kind=d.kind; prev_end=d.rva+d.size; r.rows.emplace_back(d.rva,d.size);
    }
    demand(cursor==raw&&header_total==r.headers&&word(r.expected,r.base_field)==r.preferred,"strict canonical headers/whole raw scope differs");
    for(bool value:owned)demand(value,"missing selected HIGHLOW");
    retain_expected_binding(r,path,payload_path);
    return r;
}
'''


JOURNAL_CPP = r'''
#pragma pack(push,1)
struct OriginalIo { LONG write_return; DWORD write_error,requested,returned; LONG flush_return; DWORD flush_error; };
struct Compared { ULONG version,ordinal,descriptor,read_sequence,requested,returned,status,mismatches,first,fixups;
    LONGLONG address,before_tick,after_tick; };
#pragma pack(pop)
static_assert(sizeof(void*)==4&&sizeof(OriginalIo)==24&&sizeof(Compared)==64,"fixed x86 comparison wire");
struct Journal {
    HANDLE output=GetStdHandle(STD_OUTPUT_HANDLE); unsigned long long sequence=0,raw_bytes=0,metadata_bytes=8;
    bool debt=false,failed=false;
    void begin() { demand(GetFileType(output)==FILE_TYPE_DISK,"FILE_TYPE_DISK original archive required; pipes unsupported");
        DWORD got=0; SetLastError(0); BOOL written=WriteFile(output,"CLHDCR2\0",8,&got,nullptr); DWORD error=GetLastError();
        SetLastError(0); BOOL flushed=FlushFileBuffers(output); DWORD flush_error=GetLastError();
        auto original=object({{"write_return",signed_number(written)},{"write_error",number(error)},
            {"requested","8"},{"returned",number(got)},{"flush_return",signed_number(flushed)},{"flush_error",number(flush_error)}});
        if(!written||got!=8||!flushed) {
            debt=true; failed=true;
            // A failed begin may have no usable journal. Preserve the complete
            // original magic-I/O observation through the host's retained error
            // path; neither this diagnostic nor any later frame is durable proof.
            fprintf(stderr,"MAGIC_IO_DEBT %s\n",original.c_str());
            bool write_failed=!written||got!=8;
            const char *api=write_failed?"WriteFile.archive_magic":"FlushFileBuffers.archive_magic";
            LONG returned=write_failed?written:flushed; DWORD native_error=write_failed?error:flush_error;
            NativeFailure failure(api,returned,native_error,8,got,Bytes{'C','L','H','D','C','R','2',0});
            failure.original=object({{"api_name",quote(api)},{"native_return",signed_number(returned)},
                {"native_error",number(native_error)},{"requested_bytes","8"},{"returned_bytes",number(got)},
                {"detail_hex",quote(hex(original.data(),original.size()))}});
            throw failure;
        }
        frame("archive_magic_io",original); }
    void frame(const std::string &op,const std::string &data,const Bytes &raw=Bytes()) {
        std::string json=object({{"sequence",number(sequence+1)},{"operation",quote(op)},{"data",data}});
        bool compare=op=="comparison_counter"||op=="comparison_result"||op=="comparison_begin"||op=="comparison_complete";
        if(sequence>=@MAX_FRAMES@||json.size()>(compare?4096:512*1024)||raw.size()>65539||
            metadata_bytes+json.size()+32>@FAIL_META@||raw_bytes+raw.size()>@FAIL_RAW@) {
            debt=true; failed=true; throw std::runtime_error("whole original packet exceeds source cap; retained RAM debt"); }
        ULONG sizes[2]={static_cast<ULONG>(json.size()),static_cast<ULONG>(raw.size())}; Bytes packet(8+json.size()+raw.size());
        memcpy(packet.data(),sizes,8); memcpy(packet.data()+8,json.data(),json.size());
        if(!raw.empty())memcpy(packet.data()+8+json.size(),raw.data(),raw.size());
        OriginalIo io={}; io.requested=static_cast<DWORD>(packet.size()); SetLastError(0);
        io.write_return=WriteFile(output,packet.data(),io.requested,&io.returned,nullptr); io.write_error=GetLastError();
        SetLastError(0); io.flush_return=FlushFileBuffers(output); io.flush_error=GetLastError();
        // This footer retains original main-data I/O only. Its own append and
        // flush are an explicitly unattested tail, requiring external storage.
        DWORD footer_count=0; SetLastError(0); BOOL footer=WriteFile(output,&io,sizeof(io),&footer_count,nullptr); DWORD footer_error=GetLastError();
        SetLastError(0); BOOL footer_flushed=FlushFileBuffers(output); DWORD footer_flush_error=GetLastError();
        if(!io.write_return||io.returned!=io.requested||!io.flush_return||!footer||footer_count!=sizeof(io)||!footer_flushed) {
            debt=true; failed=true;
            fprintf(stderr,"IO_DEBT main=%ld,%lu,%lu,%lu,%ld,%lu tail=%ld,%lu,%lu,%ld,%lu\n",io.write_return,
                io.write_error,io.requested,io.returned,io.flush_return,io.flush_error,footer,footer_error,footer_count,
                footer_flushed,footer_flush_error); throw std::runtime_error("original main/footer I/O failure; external retained bytes/debt required"); }
        ++sequence; metadata_bytes+=json.size()+32; raw_bytes+=raw.size();
        if(metadata_bytes>@NORMAL_META@||raw_bytes>@NORMAL_RAW@) { failed=true; throw std::runtime_error("complete over-capacity original packet retained"); }
    }
};
'''


BINDING_CPP = r'''
static void retain_expected_binding(const Request &r,const wchar_t *path,const wchar_t *payload_path) {
    demand(active_journal!=nullptr,"original expected binding has no archive");
    size_t request_chars=wcsnlen_s(path,32768),payload_chars=wcsnlen_s(payload_path,32768);
    demand(request_chars<32768&&payload_chars<32768,"original input path remainder debt");
    std::string hashes="["; for(const auto &row:original_buffer_hashes) { if(hashes.size()>1)hashes+=','; hashes+=row; } hashes+=']';
    active_journal->frame("expected_binding",object({{"request_sha256",quote(r.sha)},
        {"expected_payload_sha256",quote(r.payload_sha)},{"metadata_hex",quote(hex(r.payload.data()+48,word(r.payload,12)))},
        {"request_path_utf16le",quote(hex(path,(request_chars+1)*2))},
        {"payload_path_utf16le",quote(hex(payload_path,(payload_chars+1)*2))},
        {"payload_bytes",number(r.payload.size())},{"chunk_count",number(r.descriptors.size())},
        {"highlow_count",number(r.fixups.size())},{"hash_receipts",hashes}}));
}
'''


READ_CPP = r'''
    void read(ULONG ordinal,ULONG64 address,ULONG size) {
        phase(); counter(); Bytes raw(size); ULONG actual=0; HRESULT hr=memory->ReadVirtual(address,raw.data(),size,&actual);
        // Preserve all requested-capacity original bytes, with HRESULT/count
        // separate. An unwritten initialized tail is not observed memory.
        j.frame("read_virtual_capacity",object({{"ordinal",number(ordinal)},{"address",number(address)},{"requested_bytes",number(size)},
            {"hresult",signed_number(hr)},{"returned_bytes",number(actual)}}),raw);
        ULONG read_sequence=static_cast<ULONG>(j.sequence);
        demand(hr==S_OK&&actual==size,"original partial/failed capacity read retained; comparison not called"); counter(); phase();
        unsigned long long before=0; LONGLONG original_before=0; bool before_valid=false; auto before_qpc=qpc(r,before,before_valid,&original_before);
        j.frame("comparison_counter",object({{"ordinal",number(ordinal)},{"qpc",before_qpc}})); ULONG before_sequence=static_cast<ULONG>(j.sequence);
        demand(before_valid&&held&&before>=held&&before-held<=20*r.frequency,"original comparison-start QPC failed/exceeded unchanged hold");
        Bytes expected(size); ULONG applied=0,descriptor=0xffffffff;
        if(!ordinal) {
            demand(size==4&&address==peb+8,"PEB read inventory differs"); ULONG observed=word(raw,0);
            demand(observed==base&&observed>=0x10000&&observed%0x10000==0&&observed<=0x7ffe0000-r.image_size,
                "actual full PEB base differs from original callback base"); base=observed; memcpy(expected.data(),&observed,4);
        } else {
            descriptor=ordinal-1; demand(descriptor<r.descriptors.size(),"unexpected descriptor ordinal"); auto d=r.descriptors[descriptor];
            demand(address==base+d.rva&&size==d.size,"actual PEB-derived address/request differs");
            memcpy(expected.data(),r.expected.data()+d.raw_offset,d.size);
            ULONG delta=static_cast<ULONG>(base)-r.preferred;
            for(ULONG at=d.first;at<d.first+d.count;++at) { ULONG offset=r.fixups[at]-d.rva,old=word(expected,offset),next=old+delta;
                memcpy(expected.data()+offset,&next,4); ++applied; }
        }
        ULONG mismatches=0,first=0xffffffff;
        for(ULONG i=0;i<size;++i)if(raw[i]!=expected[i]) { ++mismatches; if(first==0xffffffff)first=i; }
        unsigned long long after=0; LONGLONG original_after=0; bool after_valid=false; auto after_qpc=qpc(r,after,after_valid,&original_after);
        Compared result={1,ordinal,descriptor,read_sequence,size,actual,mismatches?1UL:0UL,mismatches,first,applied,
            static_cast<LONGLONG>(address),original_before,original_after};
        Bytes original(sizeof(result)); memcpy(original.data(),&result,sizeof(result));
        j.frame("comparison_result",object({{"read_sequence",number(read_sequence)},{"before_sequence",number(before_sequence)},
            {"comparison_called","true"},{"post_qpc_called","true"},{"post_qpc",after_qpc}}),original);
        ++comparison_results; compared_bytes+=size;
        demand(after_valid&&after>=before&&after-held<=20*r.frequency,"original post-comparison QPC failed/exceeded unchanged hold");
        demand(mismatches==0,"actual immutable-byte mismatch retained");
    }
'''


prepare_comparison_plan, prepare_comparison_request, inspect_comparison_request = _factory()
