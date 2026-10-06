"""V3 terminate-only initial-loader observer and request-independent outer source.

This source preparation issues no native, cleanup, storage or game acceptance.
The adapter owns its own private registry and actual compiler/retained-generation
admission. The public generator registry cannot confer that native authority.
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
SOURCE = "tools/hidden_soak_loader_v3.py"
ADAPTER = "tools/hidden_soak_loader_v3_adapter.py"
V2 = "tools/hidden_soak_loader_compare_native.py"
V2_SHA = "fee6780971d5e305b770a01aff5d6f195394f20b283f252efe81f00c419e20fe"
GATE_MAGIC = b"CLHDGA3\0"
CORE_MAGIC = b"CLHDBV3\0"
GATE_SIZE, CORE_SIZE, BOOT_SIZE = 576, 32768, 32864
OBSERVER_METADATA, OBSERVER_RAW, OBSERVER_PACKET_RAW = 64*1024**2, 512*1024**2, 4*1024**2
GATE_HEADER = struct.Struct("<8sIIQII")
GENERATION = struct.Struct("<IQ")
PATH_NAMES = ("candidate", "request", "payload", "observer", "caller", "outer", "root",
              "outer_archive", "bootstrap", "observer_archive", "observer_stderr", "challenge", "adoption")
HASH_NAMES = ("request", "payload", "candidate", "probe", "caller", "outer", "producer")
ACTORS = ("observer", "observer", "observer", "outer", "outer", "outer", "outer")
FALSE_CLAIMS = {key: False for key in (
    "passed", "native_producer_provenance_verified", "native_read_coherence_verified",
    "compiled_producer_verified", "loaded_producer_verified", "no_breakaway_job_verified",
    "native_generation_ownership_verified", "native_job_cleanup_verified", "host_cleanup_complete",
    "storage_durability_verified", "receipt_tail_durability_verified", "loaded_candidate_verified",
    "whole_image_verified", "loaded_probe_verified", "probe_executed", "running_duration_verified",
    "map_ready", "natural_map_readiness_verified", "runtime_acceptance", "release_acceptance", "manual_input_verified", "promotion_ready", "stable")}


def _require(value, reason):
    if not value:
        raise ValueError(reason)


def _sha(raw):
    _require(type(raw) is bytes, "original exact bytes required")
    return hashlib.sha256(raw).hexdigest()


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")


def _closed(raw, path, names, factory):
    _require(path.read_bytes() == raw, "canonical source differs before private compilation")
    tree = ast.parse(raw, filename=str(path))
    terminal = tree.body[-1]
    calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)
             and isinstance(node.func, ast.Name) and node.func.id == factory]
    _require(len(calls) == 1 and isinstance(terminal, ast.Assign) and len(terminal.targets) == 1
             and isinstance(terminal.targets[0], ast.Tuple)
             and tuple(getattr(node, "id", None) for node in terminal.targets[0].elts) == names
             and isinstance(terminal.value, ast.Call) and isinstance(terminal.value.func, ast.Name)
             and terminal.value.func.id == factory and not terminal.value.args and not terminal.value.keywords,
             "sole structurally authenticated terminal factory required")
    tree.body.pop()
    name = "_clash_loader_v3_" + uuid.uuid4().hex
    module = types.ModuleType(name); module.__file__ = str(path)
    _require(name not in sys.modules, "private namespace collision")
    sys.modules[name] = module
    try:
        _require(path.read_bytes() == raw, "canonical source changed before private execution")
        exec(compile(tree, str(path), "exec"), module.__dict__)
        _require(sys.modules.get(name) is module, "owned private namespace identity lost during execution")
        _require(path.read_bytes() == raw, "canonical source changed during private execution")
        return module
    finally:
        if sys.modules.get(name) is module:
            del sys.modules[name]


def parse_core(raw):
    """Strict syntax, never independent source/native authority."""
    _require(type(raw) is bytes and len(raw) == CORE_SIZE and raw[:8] == CORE_MAGIC,
             "exact complete core required")
    _require(struct.unpack_from("<II", raw, 8) == (3, CORE_SIZE), "fixed core header differs")
    caller_pid, caller_creation, outer_pid, outer_creation, frequency, origin, origin_ns = struct.unpack_from("<IQIQQQQ", raw, 16)
    _require(caller_pid and outer_pid and caller_pid != outer_pid and caller_creation and outer_creation
             and 0 < frequency <= 10**9 and 0 < origin < 2**63 and 0 < origin_ns < 2**63 - 20 * 10**9,
             "distinct original generations and epoch required")
    ids = tuple(raw[64+i*16:80+i*16].hex() for i in range(3))
    _require(all(int(token, 16) for token in ids) and len(set(ids)) == 3, "distinct source-issued identifiers required")
    hashes = {key: raw[112+i*32:144+i*32].hex() for i, key in enumerate(HASH_NAMES)}
    _require(all(int(value, 16) for value in hashes.values()), "complete source bindings required")
    archives = tuple(raw[336+i*16:352+i*16].hex() for i in range(3))
    _require(all(int(token, 16) for token in archives) and len(set(archives)) == 3, "actor archives must be distinct")
    paths = {}
    for i, name in enumerate(PATH_NAMES):
        slot = raw[384+i*2048:384+(i+1)*2048]
        text = slot.decode("utf-16le")
        at = text.find("\0")
        _require(at > 2 and not text[at:].strip("\0"), "fixed terminated path with zero tail required")
        value = text[:at]
        _require(len(value) < 1024 and value.isascii() and value[1:3] == ":\\" and
                 not any(part in ("", ".", "..") for part in value[3:].split("\\")) and
                 not any(char in value[3:] for char in '\"<>|?*:/') and
                 all(ord(char)>=32 for char in value), "absolute literal Windows path required")
        paths[name] = value
    _require(len({value.lower() for value in paths.values()}) == len(paths), "artifact paths must be distinct")
    root = paths["root"].lower() + "\\"
    _require(all(paths[name].lower().startswith(root) for name in PATH_NAMES if name not in ("caller", "root")),
             "all native artifacts must stay under dedicated root")
    volume, file_id, peak, assets = struct.unpack_from("<IQQQ", raw, 27008)
    _require(volume and file_id and peak >= retention_budget()["fixed_required_peak_bytes"] + assets and raw[27036:] == bytes(CORE_SIZE-27036),
             "source peak/root identity/zero policy differs")
    return dict(caller_pid=caller_pid, caller_creation=caller_creation, outer_pid=outer_pid,
        outer_creation=outer_creation, frequency=frequency, origin=origin, origin_ns=origin_ns,
        run_id=ids[0], checkpoint_id=ids[1], epoch_id=ids[2], hashes=hashes, archives=archives,
        paths=paths, volume=volume, file_id=file_id, peak=peak, assets=assets)


def parse_gate(raw, *, kind):
    _require(type(raw) is bytes and len(raw) == GATE_SIZE and kind in (1, 2), "complete original gate required")
    _require(GATE_HEADER.unpack_from(raw) == (GATE_MAGIC, 3, kind, 1, GATE_SIZE, 0), "exact gate header differs")
    _require(hashlib.sha256(raw[:544]).digest() == raw[544:], "original gate prefix checksum differs")
    ids = tuple(raw[32+i*16:48+i*16].hex() for i in range(3))
    nonce = raw[80:96]
    generations = tuple(GENERATION.unpack_from(raw, 96+i*12) for i in range(4))
    frequency, origin, initial = struct.unpack_from("<3Q", raw, 144)
    sequences = struct.unpack_from("<7Q", raw, 168)
    hashes = tuple(raw[224+i*32:256+i*32].hex() for i in range(10))
    _require(len(set(ids)) == 3 and all(int(item, 16) for item in ids) and any(nonce)
             and all(pid and creation for pid, creation in generations) and len({pid for pid, _ in generations}) == 4
             and 0 < frequency <= 10**9 and 0 < origin <= initial < 2**63
             and all(sequences[:3]) and sequences[6] > 0, "original complete gate fields required")
    _require((kind == 1 and sequences[3:6] == (0, 0, 0) and hashes[9] == "0"*64)
             or (kind == 2 and all(sequences) and hashes[9] != "0"*64), "kind-dependent acyclic binding differs")
    _require(all(value != "0"*64 for value in hashes[:9]), "gate source/archive bindings omitted")
    return dict(ids=ids, nonce=nonce, generations=generations, frequency=frequency, origin=origin,
        initial_tick=initial, sequences=sequences, hashes=hashes, actors=ACTORS)


def retention_budget():
    # Original outer API capacities include whole 4096-row Toolhelp cohorts.
    metadata, raw, frames, pending = 32*1024**2, 64*1024**2, 32768, 16*1024**2
    outer_archive = 8 + metadata + raw + frames*32
    payload_max = 17121324
    observer_meta = OBSERVER_METADATA + 1024**2
    observer_raw = OBSERVER_RAW + OBSERVER_PACKET_RAW
    observer_archive = observer_meta + observer_raw
    observer_peak = 2*payload_max + 640 + observer_raw + 2*observer_meta + observer_archive
    diagnostics = 4*16*1024**2
    caller_archive = 64*1024**2 + 128*1024**2
    caller_pending = 64*1024**2
    caller_close = 16*1024**2
    caller_peak = 2*caller_archive + caller_pending + 2*caller_close
    bootstrap_and_gates = 2*BOOT_SIZE + 4*GATE_SIZE
    known_peak = 2*outer_archive + pending + observer_peak + bootstrap_and_gates + caller_peak + diagnostics
    build_peak = 512*1024**2
    return dict(outer_metadata_bytes=metadata, outer_raw_bytes=raw, outer_frames=frames,
        outer_pending_original_bytes=pending, outer_archive_bytes=outer_archive,
        outer_archive_complete_copy_bytes=outer_archive, observer_metadata_bytes=observer_meta,
        observer_raw_bytes=observer_raw, observer_archive_bytes=observer_archive,
        observer_peak_bytes=observer_peak,
        bootstrap_bytes=BOOT_SIZE, bootstrap_atomic_bytes=BOOT_SIZE, gate_bytes=GATE_SIZE,
        caller_archive_bytes=caller_archive, caller_complete_copy_bytes=caller_archive,
        caller_pending_bytes=caller_pending,
        caller_close_original_bytes=caller_close,caller_close_complete_copy_bytes=caller_close,
        observer_and_outer_stderr_with_complete_copies_bytes=diagnostics,
        known_peak_bytes=known_peak, source_owned_build_bytes=build_peak,
        fixed_required_peak_bytes=known_peak+build_peak,
        exclusions=["additional candidate/assets and over-capacity compiler timeout originals",
                    "original/source/native model RAM", "unavailable or over-capacity original output debt"],
        storage_scope="main packet IO is observed; footer own IO and external storage provenance remain unverified")


@dataclass(frozen=True, eq=False, slots=True, weakref_slot=True)
class ReadPlan:
    binding_json: str


@dataclass(frozen=True, eq=False, slots=True, weakref_slot=True)
class ReadRequest:
    binding_json: str


@dataclass(frozen=True)
class Facts:
    metadata_json: str
    request_bytes: bytes
    expected_payload: bytes
    observer_source: bytes
    core_bytes: bytes
    predecessor_facts: object
    check_sources: object


def _replace(source, before, after):
    _require(source.count(before) == 1, "frozen source transform must be unique")
    return source.replace(before, after)


def _render_observer(facts, core, *, fixture_mode=0):
    values = parse_core(core)
    data = json.loads(facts.metadata_json)
    producer = _sha(_canonical(dict(v3_source_sha256=_sha((ROOT/SOURCE).read_bytes()),
        v3_adapter_sha256=_sha((ROOT/ADAPTER).read_bytes()),
        predecessor_producer_closure_sha256=data["producer_source_closure_sha256"])))
    _require(values["hashes"]["producer"] == producer, "core canonical producer closure differs")
    for field, value in (("request", _sha(facts.request_bytes)), ("payload", _sha(facts.expected_payload)),
                         ("candidate", data["candidate_sha256"]), ("probe", data["probe_sha256"])):
        _require(values["hashes"][field] == value, "core source/candidate/probe mismatch")
    _require((data["controller_pid"], data["frequency_hz"], data["origin_tick"], data["origin_ns"],
              data["run_id"], data["checkpoint_id"], data["epoch_id"]) ==
             (values["outer_pid"], values["frequency"], values["origin"], values["origin_ns"],
              values["run_id"], values["checkpoint_id"], values["epoch_id"]), "request/core native owner differs")
    _require(type(fixture_mode) is int and fixture_mode in range(11), "fixed synthetic cases only")
    source = facts.host_source.decode("ascii")
    source = _replace(source, "#include <windows.h>", "#include <windows.h>\n#include <array>")
    source = _replace(source, "struct Journal {", "static bool v3_reserve();\nstruct Journal {")
    source = _replace(source, "void begin() { demand(GetFileType(output)", "void begin() { demand(v3_reserve(),\"strict reserve blocks observer magic\"); demand(GetFileType(output)")
    source = _replace(source, "        OriginalIo io={};", "        demand(v3_reserve(),\"strict reserve blocks original observer packet; pending originals/debt\");\n        OriginalIo io={};")
    source = _replace(source, "        DWORD footer_count=0;", "        demand(v3_reserve(),\"strict reserve blocks observer receipt tail; debt\");\n        DWORD footer_count=0;")
    source = _replace(source, "raw.size()>65539||", "raw.size()>4194304||")
    source = _replace(source, "metadata_bytes+json.size()+32>14958616||raw_bytes+raw.size()>16875523",
        "metadata_bytes+json.size()+32>"+str(OBSERVER_METADATA+1024**2)+"||raw_bytes+raw.size()>"+str(OBSERVER_RAW+OBSERVER_PACKET_RAW))
    source = _replace(source, "if(metadata_bytes>13910040||raw_bytes>16809984)",
        "if(metadata_bytes>"+str(OBSERVER_METADATA)+"||raw_bytes>"+str(OBSERVER_RAW)+")")
    source = _replace(source, "    long hs=0; bool hs_observed=false;", r'''    active_journal->frame("generation_capacity",object({{"handle",number(bits(h))},{"pid",number(pid)},{"pid_error",number(pid_error)},
        {"path_return",signed_number(pr)},{"path_error",number(pe)},{"path_chars",number(chars)},
        {"times_return",signed_number(tr)},{"times_error",number(te)},{"times_hex",quote(hex(&created,8)+hex(&ended,8)+hex(&kernel,8)+hex(&user,8))}}),
        Bytes(reinterpret_cast<unsigned char*>(path),reinterpret_cast<unsigned char*>(path)+sizeof(path)));
    long hs=0; bool hs_observed=false;''')
    source = _replace(source, "    unsigned int rows=0;\n    while(more&&rows++<65536)", r'''    unsigned int rows=0;Bytes original_rows;original_rows.reserve(4096*(sizeof(row)+8));
    auto retain_row=[&](){auto bp=reinterpret_cast<unsigned char*>(&more),ep=reinterpret_cast<unsigned char*>(&parent_error),rp=reinterpret_cast<unsigned char*>(&row);
        original_rows.insert(original_rows.end(),bp,bp+4);original_rows.insert(original_rows.end(),ep,ep+4);original_rows.insert(original_rows.end(),rp,rp+sizeof(row));};
    retain_row();
    while(more&&rows++<4095)''')
    source = _replace(source, "more=Process32NextW(snapshot.value,&row); parent_error=GetLastError(); }",
        "more=Process32NextW(snapshot.value,&row); parent_error=GetLastError(); retain_row(); }")
    source = _replace(source, "    valid=pid&&pid_error==0", r'''    active_journal->frame("generation_parent_capacity",object({{"handle",number(bits(h))},{"snapshot_handle",number(bits(snapshot.value))},
        {"snapshot_error",number(snapshot_error)},{"parent_pid",number(parent_pid)},{"parent_return",signed_number(parent_return)},
        {"parent_error",number(parent_error)},{"parent_times_return",signed_number(ptr)},{"parent_times_error",number(pte)},
        {"parent_times_hex",quote(hex(&pc,8)+hex(&px,8)+hex(&pk,8)+hex(&pu,8))},{"row_bytes",number(sizeof(row))},{"cohort_rows",number(original_rows.size()/(sizeof(row)+8))}}),original_rows);
    valid=pid&&pid_error==0''')
    source = _replace(source, '"CLHDCR2\\0"', '"CLHDOV3\\0"')
    source = source.replace("Bytes{'C','L','H','D','C','R','2',0}", "Bytes{'C','L','H','D','O','V','3',0}")
    source = _replace(source, "struct Session;", OBSERVER_GATE_CPP + "\nstruct Session;")
    source = _replace(source, "ULONG comparison_results=0;", "unsigned long long create_sequence=0;\n    ULONG comparison_results=0;")
    source = _replace(source, '        demand(dp==TRUE&&dt==TRUE', '        s.create_sequence=s.j.sequence;\n        demand(dp==TRUE&&dt==TRUE')
    source = _replace(source, "s.owner(\"startup_owner\"); s.counter(); s.read(0,s.peb+8,4);",
        's.owner("startup_owner"); s.counter(); gate(s,argv); s.phase(); s.read(0,s.peb+8,4);')
    source = _replace(source, 'demand(argc==4,"exact V2 invocation requires candidate, request and expected payload paths");',
        'demand(argc==9,"exact V3 seven-handle invocation required"); clear_inheritance(startup,argv);')
    source = _replace(source, "static void callback_error", OBSERVER_GATE_METHOD + "\nstatic void callback_error")
    source = _replace(source, '        try { startup.frame("finish"', '        close_v3_inherited(startup);\n        try { startup.frame("finish"')
    source = _replace(source, '        s.j.frame("finish",object({{"status",quote(completed?',
        '        completed=close_v3_inherited(s.j)&&completed;\n        s.j.frame("finish",object({{"status",quote(completed?')
    source = _replace(source, "struct Session;", "struct Session;\nstatic void gate(Session&,wchar_t**);")
    source = source.replace("@CORE_SHA@", _sha(core)).replace("@FIXTURE_MODE@", str(fixture_mode))
    source = source.replace("@STORAGE_ROOT@", "L"+json.dumps(values["paths"]["root"]))
    source = source.replace("@APPROVED_PEAK@", str(values["peak"]))
    _require("@" not in source, "unresolved observer source")
    return source.encode("ascii")


def _factory(*, _fixture=None, _fixture_mode=0):
    """Opaque registries; an isolated fixture registry is never production."""
    own = Path(__file__).resolve(); own_raw = own.read_bytes(); root = own.parents[1]
    path = root/V2; raw = path.read_bytes()
    require, digest, dumps, ref, read = _require, hashlib.sha256, json.dumps, weakref.ref, Path.read_bytes
    require(digest(raw).hexdigest() == V2_SHA, "fixed V2 source changed")
    private = _closed(raw, path, ("prepare_comparison_plan", "prepare_comparison_request", "inspect_comparison_request"), "_factory")
    prepare, issue, inspect = private._factory() if _fixture is None else _fixture
    _require(type(_fixture_mode) is int and _fixture_mode in range(11) and
             (_fixture is not None or _fixture_mode == 0), "synthetic cases cannot enter production registry")
    renderer, core_parser, fixture_mode = _render_observer, parse_core, _fixture_mode
    plans, requests = {}, {}
    classes = ReadPlan, ReadRequest, Facts
    snapshots = ((own, own_raw), (path, raw))
    def guard():
        require(all(read(p) == b for p,b in snapshots), "V3 or frozen predecessor source changed")
    def retain(registry, obj, state):
        key = id(obj)
        def gone(reference):
            if key in registry and registry[key][0] is reference: del registry[key]
        registry[key] = (ref(obj, gone), obj.binding_json, state)
        return obj
    def admit(registry, obj, cls):
        guard(); state = registry.get(id(obj))
        require(type(obj) is cls and state is not None and state[0]() is obj and state[1] == obj.binding_json,
                "genuine same-registry live capability required")
        return state[2]
    def prepare_plan(original, contract):
        guard(); value = prepare(original, contract); guard()
        return retain(plans, classes[0](dumps(dict(schema="loader_v3_plan", claims=FALSE_CLAIMS), sort_keys=True)), value)
    def prepare_request(plan, authority):
        predecessor = issue(admit(plans, plan, classes[0]), authority); facts = inspect(predecessor); guard()
        binding = dumps(dict(schema="loader_v3_request", predecessor_sha256=digest(facts.request_bytes).hexdigest(),
            claims=FALSE_CLAIMS), sort_keys=True)
        return retain(requests, classes[1](binding), [predecessor, facts, b"", b""])
    def render_observer(request, core):
        state = admit(requests, request, classes[1]); core_parser(core)
        require(not state[2], "immutable request core already issued")
        rendered = renderer(state[1], core, fixture_mode=fixture_mode); guard()
        state[2], state[3] = core, rendered
        return rendered
    def inspect_request(request):
        state = admit(requests, request, classes[1]); facts = inspect(state[0]); guard()
        return classes[2](facts.metadata_json, facts.request_bytes, facts.expected_payload, state[3], state[2], facts, guard)
    return prepare_plan, prepare_request, render_observer, inspect_request


OBSERVER_GATE_CPP = r'''
#pragma pack(push,1)
struct GateGeneration {DWORD pid; unsigned long long creation;};
struct GatePacket {char magic[8];DWORD version,kind;unsigned long long sequence;DWORD size,reserved;
    unsigned char ids[48],nonce[16];GateGeneration generations[4];unsigned long long frequency,origin,initial;
    unsigned long long refs[7];unsigned char hashes[320],trailer[32];};
#pragma pack(pop)
static_assert(sizeof(GatePacket)==576,"exact acyclic actor-qualified gate");
static Bytes v3_boot;
static HANDLE v3_handles[7]={};
static unsigned long long v3_channel_sequence=0;
static std::string close_original(HANDLE&,DWORD&);
static const int fixture_mode=@FIXTURE_MODE@;
static bool v3_reserve(){ULARGE_INTEGER available={},total={},free={};SetLastError(0);BOOL result=GetDiskFreeSpaceExW(@STORAGE_ROOT@,&available,&total,&free);DWORD error=GetLastError();
    fprintf(stderr,"ORIGINAL_OBSERVER_RESERVE return=%ld error=%lu available=%llu total=%llu free=%llu approved_peak=%llu\n",result,error,available.QuadPart,total.QuadPart,free.QuadPart,static_cast<unsigned long long>(@APPROVED_PEAK@));
    return result&&available.QuadPart>@APPROVED_PEAK@&&available.QuadPart-@APPROVED_PEAK@>total.QuadPart/10;}
static unsigned long long u64(const Bytes &b,size_t at){demand(at+8<=b.size(),"whole gate integer");unsigned long long v;memcpy(&v,b.data()+at,8);return v;}
static DWORD u32(const Bytes &b,size_t at){demand(at+4<=b.size(),"whole gate DWORD");DWORD v;memcpy(&v,b.data()+at,4);return v;}
static void unhex(const std::string &s,unsigned char *out,size_t count){demand(s.size()==count*2,"exact SHA/identifier width");
    auto nib=[](char c)->unsigned char{demand((c>='0'&&c<='9')||(c>='a'&&c<='f'),"canonical lowercase hash");return static_cast<unsigned char>(c<='9'?c-'0':c-'a'+10);};
    for(size_t i=0;i<count;++i)out[i]=static_cast<unsigned char>((nib(s[2*i])<<4)|nib(s[2*i+1]));}
static Bytes asbytes(const void *v,size_t size){const auto*p=static_cast<const unsigned char*>(v);return Bytes(p,p+size);}
static std::string v3_hash(Journal &j,const Bytes &raw){size_t before=original_buffer_hashes.size();auto digest=bytes_hash(raw);
    demand(original_buffer_hashes.size()==before+1,"original hash receipt omitted");j.frame("gate_hash",original_buffer_hashes.back());return digest;}
static HANDLE arg_handle(const wchar_t *arg,bool sequence=false){wchar_t *end=nullptr;unsigned long long value=_wcstoui64(arg,&end,10);
    demand(value&&value<=MAXDWORD&&end!=arg,"x86 representable inherited original handle required");
    if(sequence){demand(*end==L':',"qualified channel sequence required");wchar_t *last=nullptr;v3_channel_sequence=_wcstoui64(end+1,&last,10);demand(last!=end+1&&!*last&&v3_channel_sequence,"original outer channel reference required");}
    else demand(!*end,"unmodified original handle argument required");return reinterpret_cast<HANDLE>(static_cast<ULONG_PTR>(value));}
static void clear_inheritance(Journal &j,wchar_t **argv){
    v3_handles[0]=GetStdHandle(STD_INPUT_HANDLE);v3_handles[1]=GetStdHandle(STD_OUTPUT_HANDLE);v3_handles[2]=GetStdHandle(STD_ERROR_HANDLE);
    for(unsigned i=0;i<4;++i)v3_handles[i+3]=arg_handle(argv[i+5],i==3);
    for(unsigned i=0;i<7;++i){demand(v3_handles[i]&&v3_handles[i]!=INVALID_HANDLE_VALUE,"seven original handles missing");for(unsigned k=0;k<i;++k)demand(v3_handles[i]!=v3_handles[k],"duplicate inherited role");
        DWORD flags=0;SetLastError(0);BOOL got=GetHandleInformation(v3_handles[i],&flags);DWORD ge=GetLastError();
        j.frame("inherited_flags",object({{"role",number(i)},{"handle",number(bits(v3_handles[i]))},{"return",signed_number(got)},{"error",number(ge)},{"flags",number(flags)}}),asbytes(&flags,4));
        demand(got&&ge==0&&(flags&HANDLE_FLAG_INHERIT),"original inherit flag unavailable");
        SetLastError(0);BOOL set=SetHandleInformation(v3_handles[i],HANDLE_FLAG_INHERIT,0);DWORD se=GetLastError();
        j.frame("clear_inherit",object({{"role",number(i)},{"handle",number(bits(v3_handles[i]))},{"return",signed_number(set)},{"error",number(se)}}));demand(set&&se==0,"clear inherit denied");
        flags=0;SetLastError(0);got=GetHandleInformation(v3_handles[i],&flags);ge=GetLastError();
        j.frame("cleared_flags",object({{"role",number(i)},{"handle",number(bits(v3_handles[i]))},{"return",signed_number(got)},{"error",number(ge)},{"flags",number(flags)}}),asbytes(&flags,4));demand(got&&ge==0&&!(flags&HANDLE_FLAG_INHERIT),"target inherited role leak");}
    v3_boot=read_file(argv[4]);j.frame("bootstrap",object({{"bytes",number(v3_boot.size())}}),v3_boot);
    demand(v3_boot.size()==32864&&!memcmp(v3_boot.data(),"CLHDBV3\0",8)&&u32(v3_boot,8)==3&&u32(v3_boot,12)==32768,"source bootstrap differs");
    demand(v3_hash(j,Bytes(v3_boot.begin(),v3_boot.begin()+32768))=="@CORE_SHA@","source-issued core changed");
    demand(v3_hash(j,Bytes(v3_boot.begin(),v3_boot.end()-32))==hex(v3_boot.data()+32832,32),"bootstrap prefix hash differs");
}
static GateGeneration gate_generation(Journal &j,HANDLE h,const char *role){SetLastError(0);DWORD pid=GetProcessId(h),pe=GetLastError();
    FILETIME times[4]={};SetLastError(0);BOOL tr=GetProcessTimes(h,&times[0],&times[1],&times[2],&times[3]);DWORD te=GetLastError();
    SetLastError(0);DWORD wr=WaitForSingleObject(h,0),we=GetLastError();DWORD exit=0;SetLastError(0);BOOL er=GetExitCodeProcess(h,&exit);DWORD ee=GetLastError();
    j.frame("gate_generation",object({{"role",quote(role)},{"handle",number(bits(h))},{"pid",number(pid)},{"pid_error",number(pe)},
        {"times_return",signed_number(tr)},{"times_error",number(te)},{"wait",number(wr)},{"wait_error",number(we)},
        {"exit_return",signed_number(er)},{"exit_error",number(ee)},{"exit_code",number(exit)}}),asbytes(times,sizeof(times)));
    demand(pid&&pe==0&&tr&&te==0&&ft(times[0])&&ft(times[1])==0&&wr==WAIT_TIMEOUT&&we==0&&er&&ee==0&&exit==STILL_ACTIVE,"live original gate generation failed");
    return GateGeneration{pid,ft(times[0])};}
static void gate_file(Journal &j,HANDLE h,const char *role){BY_HANDLE_FILE_INFORMATION info={};SetLastError(0);BOOL r=GetFileInformationByHandle(h,&info);DWORD e=GetLastError();
    std::array<wchar_t,32768> path={};SetLastError(0);DWORD count=GetFinalPathNameByHandleW(h,path.data(),static_cast<DWORD>(path.size()),FILE_NAME_NORMALIZED|VOLUME_NAME_DOS),error=GetLastError();
    j.frame("gate_file_info",object({{"role",quote(role)},{"handle",number(bits(h))},{"return",signed_number(r)},{"error",number(e)}}),asbytes(&info,sizeof(info)));
    j.frame("gate_file_path",object({{"role",quote(role)},{"handle",number(bits(h))},{"chars",number(count)},{"error",number(error)}}),asbytes(path.data(),sizeof(path)));
    demand(r&&e==0&&!(info.dwFileAttributes&(FILE_ATTRIBUTE_REPARSE_POINT|FILE_ATTRIBUTE_DIRECTORY))&&count&&count<path.size()&&error==0,"original gate channel identity failed");
    std::wstring observed(path.data(),count);if(observed.substr(0,4)==L"\\\\?\\")observed=observed.substr(4);
    const auto *expected=reinterpret_cast<const wchar_t*>(v3_boot.data()+384+2048*(!strcmp(role,"challenge_writer")?11:12));
    demand(_wcsicmp(observed.c_str(),expected)==0,"original gate channel path differs from source core");}
static bool close_v3_inherited(Journal &j) noexcept{bool complete=true;for(unsigned i=0;i<7;++i){if(i==1||i==2||!v3_handles[i]||v3_handles[i]==INVALID_HANDLE_VALUE)continue;
    HANDLE original=v3_handles[i];SetLastError(0);BOOL result=CloseHandle(original);DWORD error=GetLastError();if(result)v3_handles[i]=nullptr;
    try{j.frame("inherited_close",object({{"role",number(i)},{"handle",number(bits(original))},{"return",signed_number(result)},{"error",number(error)}}));}
    catch(...){j.debt=true;complete=false;fprintf(stderr,"ORIGINAL_INHERITED_CLOSE_DEBT role=%u handle=%llu return=%ld error=%lu\n",i,bits(original),result,error);}
    if(!result){complete=false;j.failed=true;}}return complete;}
struct GateCallerGuard{Handle &owned;Journal &journal;bool closed=false;
    bool close() noexcept{if(closed)return !journal.failed&&!journal.debt;closed=true;HANDLE original=owned.value;owned.value=nullptr;
        if(!original||original==INVALID_HANDLE_VALUE)return true;
        SetLastError(0);BOOL result=CloseHandle(original);DWORD error=GetLastError();bool retained=true;
        try{journal.frame("gate_close_caller",object({{"handle",number(bits(original))},{"return",signed_number(result)},{"error",number(error)}}));}
        catch(...){journal.debt=true;retained=false;fprintf(stderr,"ORIGINAL_GATE_CALLER_CLOSE_DEBT handle=%llu return=%ld error=%lu\n",bits(original),result,error);}
        if(!result)journal.failed=true;return result&&retained&&!journal.failed&&!journal.debt;}
    ~GateCallerGuard() noexcept{close();}};
'''

OBSERVER_GATE_METHOD = r'''
static void gate(Session &s,wchar_t **){
    GatePacket challenge={};memcpy(challenge.magic,"CLHDGA3\0",8);challenge.version=3;challenge.kind=1;challenge.sequence=1;challenge.size=576;
    memcpy(challenge.ids,v3_boot.data()+64,48);challenge.frequency=s.r.frequency;challenge.origin=s.r.origin;challenge.initial=s.held;
    unsigned char random[16]={};NTSTATUS random_status=BCryptGenRandom(nullptr,random,sizeof(random),BCRYPT_USE_SYSTEM_PREFERRED_RNG);
    s.j.frame("gate_nonce",object({{"status",signed_number(random_status)}}),asbytes(random,sizeof(random)));demand(random_status==0,"original challenge RNG failed");memcpy(challenge.nonce,random,16);
    SetLastError(0);Handle caller(OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION|SYNCHRONIZE,FALSE,u32(v3_boot,16)));DWORD ce=GetLastError();GateCallerGuard caller_guard{caller,s.j};
    s.j.frame("gate_open_caller",object({{"return",number(bits(caller.value))},{"error",number(ce)},{"pid",number(u32(v3_boot,16))}}));demand(caller.value&&ce==0,"original caller unavailable");
    challenge.generations[0]=gate_generation(s.j,caller.value,"caller");challenge.generations[1]=gate_generation(s.j,s.controller.value,"outer");
    challenge.generations[2]=gate_generation(s.j,s.debugger.value,"observer");challenge.generations[3]=gate_generation(s.j,s.target.value,"target");
    demand(challenge.generations[0].pid==u32(v3_boot,16)&&challenge.generations[0].creation==u64(v3_boot,20)&&
        challenge.generations[1].pid==u32(v3_boot,28)&&challenge.generations[1].creation==u64(v3_boot,32),"caller/outer generation differs from source core");
    for(unsigned i=0;i<6;++i)memcpy(challenge.hashes+32*i,v3_boot.data()+112+32*i,32);
    unhex(s.expected_host_hash,challenge.hashes+192,32);memcpy(challenge.hashes+224,v3_boot.data()+304,32);
    unhex(v3_hash(s.j,v3_boot),challenge.hashes+256,32);
    demand(hex(v3_boot.data()+32768,32)==s.expected_host_hash,"actual observer file differs from compiler/bootstrap binding");
    gate_file(s.j,v3_handles[3],"challenge_writer");gate_file(s.j,v3_handles[4],"adoption_reader");s.phase();
    challenge.refs[0]=s.initial_sequence;challenge.refs[1]=s.create_sequence;challenge.refs[2]=s.j.sequence;challenge.refs[6]=v3_channel_sequence;
    unhex(v3_hash(s.j,asbytes(&challenge,544)),challenge.trailer,32);
    if(fixture_mode==1){DWORD e=0;auto r=close_original(v3_handles[3],e);s.j.frame("fixture_close_challenge",object({{"return",r},{"error",number(e)}}));}
    demand(v3_reserve(),"strict reserve blocks original challenge write");DWORD got=0;SetLastError(0);BOOL wr=WriteFile(v3_handles[3],&challenge,sizeof(challenge),&got,nullptr);DWORD we=GetLastError();
    SetLastError(0);BOOL fl=FlushFileBuffers(v3_handles[3]);DWORD fe=GetLastError();
    s.j.frame("challenge_write",object({{"write_return",signed_number(wr)},{"write_error",number(we)},{"requested",number(sizeof(challenge))},{"returned",number(got)},
        {"flush_return",signed_number(fl)},{"flush_error",number(fe)}}),asbytes(&challenge,sizeof(challenge)));
    demand(wr&&got==sizeof(challenge)&&fl,"original challenge write/flush failed");s.counter();
    if(fixture_mode==2){DWORD e=0;auto r=close_original(v3_handles[5],e);s.j.frame("fixture_close_challenge_event",object({{"return",r},{"error",number(e)}}));}
    SetLastError(0);BOOL signaled=SetEvent(v3_handles[5]);DWORD signal_error=GetLastError();
    s.j.frame("challenge_signal",object({{"return",signed_number(signaled)},{"error",number(signal_error)}}));demand(signaled,"original challenge signal failed");
    unsigned long long now=0;bool valid=false;auto sample=qpc(s.r,now,valid);s.j.frame("gate_wait_before",sample);
    demand(valid&&now>=s.held&&now-s.held<20*s.r.frequency,"unchanged hold exhausted before adoption");
    DWORD ms=static_cast<DWORD>(((20*s.r.frequency-(now-s.held))*1000)/s.r.frequency);
    SetLastError(0);DWORD waited=WaitForSingleObject(v3_handles[6],ms),wait_error=GetLastError();
    s.j.frame("adoption_wait",object({{"return",number(waited)},{"error",number(wait_error)},{"timeout_ms",number(ms)}}));s.counter();
    demand(waited==WAIT_OBJECT_0,"independent adoption event missing/late");
    GatePacket adoption={};got=0;SetLastError(0);BOOL rr=ReadFile(v3_handles[4],&adoption,sizeof(adoption),&got,nullptr);DWORD re=GetLastError();
    s.j.frame("adoption_read",object({{"return",signed_number(rr)},{"error",number(re)},{"requested",number(sizeof(adoption))},{"returned",number(got)}}),asbytes(&adoption,sizeof(adoption)));
    demand(rr&&got==576&&adoption.kind==2&&adoption.refs[3]&&adoption.refs[4]&&adoption.refs[5],"original adoption partial/type/sequence failed");
    demand(v3_hash(s.j,asbytes(&adoption,544))==hex(adoption.trailer,32)&&hex(adoption.hashes+288,32)==v3_hash(s.j,asbytes(&challenge,576)),"original adoption prefix/challenge binding failed");
    GatePacket expected=challenge;expected.kind=2;memcpy(expected.refs+3,adoption.refs+3,24);memcpy(expected.hashes+288,adoption.hashes+288,32);memcpy(expected.trailer,adoption.trailer,32);
    demand(!memcmp(&expected,&adoption,576),"original actor/generation/epoch/hash/nonce changed across adoption");
    for(unsigned i=0;i<4;++i){HANDLE h=i==0?caller.value:i==1?s.controller.value:i==2?s.debugger.value:s.target.value;
        auto current=gate_generation(s.j,h,i==0?"caller":i==1?"outer":i==2?"observer":"target");demand(!memcmp(&current,&adoption.generations[i],12),"fresh generation differs after adoption");}
    s.phase();s.counter();demand(caller_guard.close(),"original gate caller close/retention failed");s.j.frame("gate_complete",object({{"challenge_sha256",quote(hex(adoption.hashes+288,32))},{"outer_archive_id",quote(hex(v3_boot.data()+352,16))}}));
    if(fixture_mode==4)s.peb=0x7ffe0000; // Actual out-of-scope ReadVirtual or exact-buffer comparison rejects; no injected HRESULT.
}
'''



OUTER_MAIN = r'''
#pragma pack(push,1)
struct GateGeneration{DWORD pid;unsigned long long creation;};
struct GatePacket{char magic[8];DWORD version,kind;unsigned long long sequence;DWORD size,reserved;
    unsigned char ids[48],nonce[16];GateGeneration generations[4];unsigned long long frequency,origin,initial;
    unsigned long long refs[7];unsigned char hashes[320],trailer[32];};
#pragma pack(pop)
static_assert(sizeof(GatePacket)==576,"fixed V3 gate");
static const int fixture_mode=@MODE@;
static DWORD get32(const Bytes&v,size_t at){demand(at+4<=v.size(),"whole DWORD");DWORD x;memcpy(&x,v.data()+at,4);return x;}
static unsigned long long get64(const Bytes&v,size_t at){demand(at+8<=v.size(),"whole QWORD");unsigned long long x;memcpy(&x,v.data()+at,8);return x;}
static std::wstring path_slot(const Bytes &v,size_t i){demand(i<13,"fixed path role");const auto *p=reinterpret_cast<const wchar_t*>(v.data()+384+i*2048);size_t count=0;
    while(count<1024&&p[count]){demand(p[count]>=32&&p[count]<128,"ASCII literal paths only");++count;}demand(count>3&&count<1024&&p[1]==L':'&&p[2]==L'\\',"absolute bounded path");
    for(size_t j=3;j<count;++j)demand(!wcschr(L"\"<>|?*:/",p[j]),"source literal filename scope");
    for(size_t j=count;j<1024;++j)demand(p[j]==0,"nonzero path tail");return std::wstring(p,count);}
static Bytes read_exact(Owned &file,DWORD size,const char *phase){Bytes v(size);DWORD got=0;Tick b=tick();SetLastError(0);
    BOOL r=ReadFile(file.h,v.data(),size,&got,nullptr);DWORD e=GetLastError();api("ReadFile",file.role,phase,file.h,r,e,size,got,v,"{}",b);
    demand(r&&got==size,"full original input read failed; partial capacity retained");return v;}
static void write_exact(Owned &file,const Bytes &v,const char *phase){demand(reserve_original(),"strict reserve blocks channel write");Tick b=tick();DWORD got=0;SetLastError(0);BOOL r=WriteFile(file.h,v.data(),static_cast<DWORD>(v.size()),&got,nullptr);DWORD e=GetLastError();
    api("WriteFile",file.role,phase,file.h,r,e,static_cast<DWORD>(v.size()),got,v,"{}",b);b=tick();SetLastError(0);BOOL f=FlushFileBuffers(file.h);DWORD fe=GetLastError();
    api("FlushFileBuffers",file.role,phase,file.h,f,fe,0,0,Bytes(),"{}",b);demand(r&&got==v.size()&&f,"original channel write/flush failed");}
static void unhex(const std::string &s,unsigned char*p,size_t count){demand(s.size()==2*count,"hash width");auto nib=[](char c){demand((c>='0'&&c<='9')||(c>='a'&&c<='f'),"hash token");return c<='9'?c-'0':c-'a'+10;};
    for(size_t i=0;i<count;++i)p[i]=static_cast<unsigned char>((nib(s[2*i])<<4)|nib(s[2*i+1]));}
static void file_open(Owned &file,const std::wstring &path,const char *role,DWORD access,DWORD disposition){if(disposition==CREATE_NEW)demand(reserve_original(),"strict reserve blocks channel creation");Tick b=tick();SetLastError(0);
    HANDLE h=CreateFileW(path.c_str(),access,FILE_SHARE_READ|FILE_SHARE_WRITE,nullptr,disposition,FILE_FLAG_OPEN_REPARSE_POINT,nullptr);DWORD e=GetLastError();
    if(h&&h!=INVALID_HANDLE_VALUE)own(file,h,role);
    api("CreateFileW",role,"channel",h,bits(h),e,0,0,Bytes(),obj({{"path",quote(ascii(path))},{"access",n(access)},{"disposition",n(disposition)}}),b);
    demand(h&&h!=INVALID_HANDLE_VALUE,"unique original channel collision/denial");
    if(!strcmp(role,"stdin_original")){b=tick();SetLastError(0);DWORD type=GetFileType(h);e=GetLastError();api("GetFileType",role,"channel",h,type,e,0,0,Bytes(),"{}",b);demand(type==FILE_TYPE_CHAR,"original NUL character input required");}
    else{info(h,role);demand(final_path(h,role)==lower(path),"channel path escaped source root");}}
static void independent_reader(Owned &reader,Owned &writer,const std::wstring &path,const char *role){file_open(reader,path,role,FILE_GENERIC_READ,OPEN_EXISTING);
    auto wi=info(writer.h,writer.role),ri=info(reader.h,role);demand(wi.dwVolumeSerialNumber==ri.dwVolumeSerialNumber&&fileid(wi)==fileid(ri),"independent reader file identity differs");}
static void event_create(Owned &x,const char *role){Tick b=tick();SetLastError(0);HANDLE h=CreateEventW(nullptr,TRUE,FALSE,nullptr);DWORD e=GetLastError();if(h)own(x,h,role);
    api("CreateEventW",role,"channel",h,bits(h),e,0,0,Bytes(),obj({{"manual_reset",n(1)},{"initial_state",n(0)},{"unnamed",n(1)}}),b);demand(h,"private original event denied");}
static void restrict_duplicate(Owned &dup,Owned &original,const char *role,DWORD access){HANDLE h=nullptr;Tick b=tick();SetLastError(0);
    BOOL r=DuplicateHandle(GetCurrentProcess(),original.h,GetCurrentProcess(),&h,access,TRUE,0);DWORD e=GetLastError();if(h)own(dup,h,role);
    api("DuplicateHandle",role,"inherit",h,r,e,0,0,Bytes(),obj({{"original",n(bits(original.h))},{"desired_access",n(access)},{"inherit",n(1)},{"options",n(0)}}),b);demand(r&&h&&bits(h)<=MAXDWORD,"restricted x86 handle duplicate denied/overflow");
    DWORD flags=0;b=tick();SetLastError(0);BOOL gr=GetHandleInformation(h,&flags);e=GetLastError();api("GetHandleInformation",role,"inherit",h,gr,e,4,4,bytes(&flags,4),"{}",b);
    demand(gr&&(flags&HANDLE_FLAG_INHERIT),"original inheritable duplicate flags missing");}
int wmain(int argc,wchar_t **argv){Owned desktop,job,host,thread,target,caller,self,boot_file,stdin_original,archive,stderr_file,challenge_writer,challenge_reader,adoption_writer,adoption_reader,challenge_event,adoption_event;
    std::array<Owned,7> inherited;std::array<Owned,32> directories;size_t directory_count=0;File observer,candidate,request,payload,caller_image,self_image;
    Bytes attributes_memory,boot;LPPROC_THREAD_ATTRIBUTE_LIST attributes=nullptr;bool attributes_ready=false,host_assigned=false;
    DWORD host_pid=0,target_pid=0;unsigned long long host_creation=0,target_creation=0,outer_creation=0,frequency=0;Tick launch_started;
    try{
        demand(argc==2,"sole literal issued bootstrap path required");
        file_open(boot_file,argv[1],"bootstrap",FILE_GENERIC_READ,OPEN_EXISTING);boot=read_exact(boot_file,32864,"bootstrap");
        demand(!memcmp(boot.data(),"CLHDBV3\0",8)&&get32(boot,8)==3&&get32(boot,12)==32768,"source-issued bootstrap wire differs");
        demand(hash_bytes(Bytes(boot.begin(),boot.end()-32),"bootstrap_prefix")==hex(boot.data()+32832,32),"bootstrap prefix checksum differs");
        std::array<std::wstring,13> paths;for(size_t i=0;i<paths.size();++i)paths[i]=path_slot(boot,i);
        root_value=paths[6];archive_value=paths[7];c_root=root_value.c_str();c_job_archive=archive_value.c_str();c_approved_peak=get64(boot,27020);frequency=get64(boot,40);
        demand(lower(paths[8])==lower(argv[1]),"supplied bootstrap path differs from source envelope");
        const std::wstring prefix=lower(root_value)+L"\\";for(size_t i=0;i<13;++i)if(i!=4&&i!=6)demand(lower(paths[i]).substr(0,prefix.size())==prefix,"artifact path escaped dedicated root");
        for(size_t i=0;i<13;++i)for(size_t j=0;j<i;++j)demand(lower(paths[i])!=lower(paths[j]),"duplicate artifact path");
        for(size_t i=27036;i<32768;++i)demand(!boot[i],"unknown core policy bytes");
        LARGE_INTEGER f={};Tick b=tick();SetLastError(0);BOOL fr=QueryPerformanceFrequency(&f);DWORD e=GetLastError();api("QueryPerformanceFrequency","clock","startup",nullptr,fr,e,8,8,bytes(&f,8),"{}",b);
        demand(fr&&frequency&&frequency<=1000000000&&f.QuadPart==static_cast<LONGLONG>(frequency),"original epoch frequency differs");
        demand(c_approved_peak>=@PEAK@+get64(boot,27028),"source full peak lowered");
        size_t pos=3;while(true){size_t next=root_value.find(L'\\',pos);auto path=next==std::wstring::npos?root_value:root_value.substr(0,next);
            demand(directory_count<directories.size(),"bounded original root ancestry");b=tick();SetLastError(0);HANDLE h=CreateFileW(path.c_str(),FILE_READ_ATTRIBUTES,FILE_SHARE_READ|FILE_SHARE_WRITE,nullptr,OPEN_EXISTING,FILE_FLAG_OPEN_REPARSE_POINT|FILE_FLAG_BACKUP_SEMANTICS,nullptr);e=GetLastError();
            if(h&&h!=INVALID_HANDLE_VALUE)own(directories[directory_count++],h,"directory");api("CreateFileW","directory","root",h,bits(h),e,0,0,Bytes(),obj({{"path",quote(ascii(path))}}),b);demand(h&&h!=INVALID_HANDLE_VALUE,"root ancestor denied");
            auto fi=info(h,"directory");demand((fi.dwFileAttributes&FILE_ATTRIBUTE_DIRECTORY)&&final_path(h,"directory")==lower(path),"root ancestor/reparse differs");
            if(next==std::wstring::npos){demand(fi.dwVolumeSerialNumber==get32(boot,27008)&&fileid(fi)==get64(boot,27012),"independent root file ID differs");break;}pos=next+1;}
        demand(reserve_original(),"whole peak and strict reserve unavailable");journal.begin();journal.frame("bootstrap",obj({{"sha256",quote(hash_bytes(boot,"bootstrap_whole"))}}),boot);
        open_file(observer,paths[3].c_str(),"observer_file",8*1024*1024,hex(boot.data()+32768,32).c_str());
        open_file(candidate,paths[0].c_str(),"candidate_file",32*1024*1024,hex(boot.data()+176,32).c_str());
        open_file(request,paths[1].c_str(),"request_file",320,hex(boot.data()+112,32).c_str());
        open_file(payload,paths[2].c_str(),"payload_file",17121324,hex(boot.data()+144,32).c_str());
        open_file(caller_image,paths[4].c_str(),"caller_file",32*1024*1024,hex(boot.data()+240,32).c_str());
        open_file(self_image,paths[5].c_str(),"outer_file",8*1024*1024,hex(boot.data()+272,32).c_str());
        std::array<wchar_t,32768> ownpath={};b=tick();SetLastError(0);DWORD count=GetModuleFileNameW(nullptr,ownpath.data(),static_cast<DWORD>(ownpath.size()));e=GetLastError();api("GetModuleFileNameW","outer","startup",nullptr,count,e,sizeof(ownpath),count,bytes(ownpath.data(),sizeof(ownpath)),"{}",b);demand(count&&count<ownpath.size()&&lower(std::wstring(ownpath.data(),count))==lower(paths[5]),"actual outer path differs");
        b=tick();SetLastError(0);HANDLE ch=OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION|SYNCHRONIZE,FALSE,get32(boot,16));e=GetLastError();if(ch)own(caller,ch,"caller");api("OpenProcess","caller","startup",ch,bits(ch),e,0,0,Bytes(),"{}",b);demand(ch,"caller vanished");
        HANDLE sh=nullptr;b=tick();SetLastError(0);BOOL dr=DuplicateHandle(GetCurrentProcess(),GetCurrentProcess(),GetCurrentProcess(),&sh,PROCESS_QUERY_LIMITED_INFORMATION|SYNCHRONIZE,FALSE,0);e=GetLastError();if(sh)own(self,sh,"outer");api("DuplicateHandle","outer","startup",sh,dr,e,0,0,Bytes(),obj({{"desired_access",n(PROCESS_QUERY_LIMITED_INFORMATION|SYNCHRONIZE)},{"inherit",n(0)},{"options",n(0)}}),b);demand(dr&&sh,"outer retained generation denied");
        auto ci=process_identity(caller,caller_image,"startup",0,0,true);auto oi=process_identity(self,self_image,"startup",ci.pid,ci.creation,true);
        outer_creation=oi.creation;demand(ci.pid==get32(boot,16)&&ci.creation==get64(boot,20)&&oi.pid==get32(boot,28)&&oi.creation==get64(boot,32)&&oi.pid==GetCurrentProcessId()&&parent_of(oi.pid)==ci.pid,"source-issued distinct caller/outer generation differs");
        std::wstring desktop_name=L"ClashLoaderV3_";std::string run=hex(boot.data()+64,16);desktop_name.append(run.begin(),run.end());
        b=tick();SetLastError(0);HDESK dh=CreateDesktopW(desktop_name.c_str(),nullptr,nullptr,0,DESKTOP_ALL_ACCESS,nullptr);e=GetLastError();if(dh)own(desktop,reinterpret_cast<HANDLE>(dh),"desktop");api("CreateDesktopW","desktop","setup",reinterpret_cast<HANDLE>(dh),bits(reinterpret_cast<HANDLE>(dh)),e,0,0,Bytes(),obj({{"name",quote(ascii(desktop_name))}}),b);demand(dh,"original private desktop denied");
        b=tick();SetLastError(0);HANDLE jh=CreateJobObjectW(nullptr,nullptr);e=GetLastError();if(jh)own(job,jh,"job");api("CreateJobObjectW","job","setup",jh,bits(jh),e,0,0,Bytes(),"{}",b);demand(jh,"original job denied");
        JOBOBJECT_EXTENDED_LIMIT_INFORMATION li={};li.BasicLimitInformation.LimitFlags=JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE;b=tick();SetLastError(0);BOOL jr=SetInformationJobObject(jh,JobObjectExtendedLimitInformation,&li,sizeof(li));e=GetLastError();api("SetInformationJobObject","job","setup",jh,jr,e,sizeof(li),sizeof(li),bytes(&li,sizeof(li)),"{}",b);demand(jr,"no-breakaway setup denied");limits(job,"setup");
        file_open(stdin_original,L"NUL","stdin_original",FILE_GENERIC_READ,OPEN_EXISTING);
        file_open(archive,paths[9],"observer_archive",FILE_GENERIC_WRITE|FILE_READ_ATTRIBUTES,CREATE_NEW);
        file_open(stderr_file,paths[10],"observer_stderr",FILE_GENERIC_WRITE|FILE_READ_ATTRIBUTES,CREATE_NEW);
        file_open(challenge_writer,paths[11],"challenge_writer",FILE_GENERIC_WRITE|FILE_READ_ATTRIBUTES,CREATE_NEW);
        independent_reader(challenge_reader,challenge_writer,paths[11],"challenge_reader");
        file_open(adoption_writer,paths[12],"adoption_writer",FILE_GENERIC_WRITE|FILE_READ_ATTRIBUTES,CREATE_NEW);
        independent_reader(adoption_reader,adoption_writer,paths[12],"adoption_reader");event_create(challenge_event,"challenge_event");event_create(adoption_event,"adoption_event");
        restrict_duplicate(inherited[0],stdin_original,"stdin",FILE_GENERIC_READ);
        restrict_duplicate(inherited[1],archive,"stdout",FILE_GENERIC_WRITE|FILE_READ_ATTRIBUTES);
        restrict_duplicate(inherited[2],stderr_file,"stderr",FILE_GENERIC_WRITE|FILE_READ_ATTRIBUTES);
        restrict_duplicate(inherited[3],challenge_writer,"challenge_writer_inherited",FILE_GENERIC_WRITE|FILE_READ_ATTRIBUTES);
        restrict_duplicate(inherited[4],adoption_reader,"adoption_reader_inherited",FILE_GENERIC_READ);
        restrict_duplicate(inherited[5],challenge_event,"challenge_event_inherited",EVENT_MODIFY_STATE);
        restrict_duplicate(inherited[6],adoption_event,"adoption_event_inherited",SYNCHRONIZE);
        journal.frame("channel_identity",obj({{"outer_archive_id",quote(hex(boot.data()+352,16))},{"observer_archive_id",quote(hex(boot.data()+336,16))},
            {"challenge_writer",n(bits(challenge_writer.h))},{"challenge_reader",n(bits(challenge_reader.h))},{"adoption_writer",n(bits(adoption_writer.h))},{"adoption_reader",n(bits(adoption_reader.h))}}));auto channel_sequence=journal.sequence;
        SIZE_T size=0;b=tick();SetLastError(0);BOOL ar=InitializeProcThreadAttributeList(nullptr,1,0,&size);e=GetLastError();api("InitializeProcThreadAttributeList.size","attributes","setup",nullptr,ar,e,sizeof(size),sizeof(size),bytes(&size,sizeof(size)),"{}",b);demand(!ar&&e==ERROR_INSUFFICIENT_BUFFER&&size&&size<=65536,"original attribute capacity query failed");
        attributes_memory.resize(size);attributes=reinterpret_cast<LPPROC_THREAD_ATTRIBUTE_LIST>(attributes_memory.data());b=tick();SetLastError(0);ar=InitializeProcThreadAttributeList(attributes,1,0,&size);e=GetLastError();attributes_ready=ar!=0;api("InitializeProcThreadAttributeList","attributes","setup",reinterpret_cast<HANDLE>(attributes),ar,e,static_cast<DWORD>(attributes_memory.size()),static_cast<DWORD>(size),attributes_memory,"{}",b);demand(ar,"attributes failed");
        HANDLE list[7];for(unsigned i=0;i<7;++i)list[i]=inherited[i].h;b=tick();SetLastError(0);ar=UpdateProcThreadAttribute(attributes,0,PROC_THREAD_ATTRIBUTE_HANDLE_LIST,list,sizeof(list),nullptr,nullptr);e=GetLastError();api("UpdateProcThreadAttribute","attributes","setup",reinterpret_cast<HANDLE>(attributes),ar,e,sizeof(list),sizeof(list),bytes(list,sizeof(list)),"{}",b);demand(ar,"exact seven inherited roles denied");
        STARTUPINFOEXW si={};si.StartupInfo.cb=sizeof(si);si.StartupInfo.lpDesktop=const_cast<wchar_t*>(desktop_name.c_str());si.StartupInfo.dwFlags=STARTF_USESTDHANDLES;si.StartupInfo.hStdInput=list[0];si.StartupInfo.hStdOutput=list[1];si.StartupInfo.hStdError=list[2];si.lpAttributeList=attributes;
        std::wstring command=L"\""+paths[3]+L"\" \""+paths[0]+L"\" \""+paths[1]+L"\" \""+paths[2]+L"\" \""+paths[8]+L"\"";
        for(unsigned i=3;i<7;++i){command+=L" "+std::to_wstring(bits(list[i]));if(i==6)command+=L":"+std::to_wstring(channel_sequence);}
        if(fixture_mode==9){b=tick();SetLastError(0);BOOL sc=SetHandleInformation(list[6],HANDLE_FLAG_INHERIT,0);e=GetLastError();api("SetHandleInformation","adoption_event_inherited","fixture",list[6],sc,e,0,0,Bytes(),"{}",b);demand(sc,"original fixture inheritance change denied");}
        journal.frame("startup_info",obj({{"bytes",n(sizeof(si))}}),bytes(&si,sizeof(si)));
        PROCESS_INFORMATION pi={};launch_started=tick();demand(launch_started.result&&launch_started.tick>0,"original launch anchor failed");b=tick();SetLastError(0);demand(!failed&&!debt,"retention failure blocks suspended child launch");
        BOOL cp=CreateProcessW(paths[3].c_str(),command.data(),nullptr,nullptr,TRUE,0x08080404,nullptr,root_value.c_str(),&si.StartupInfo,&pi);e=GetLastError();
        if(pi.hProcess&&pi.hProcess!=INVALID_HANDLE_VALUE)own(host,pi.hProcess,"observer");if(pi.hThread&&pi.hThread!=INVALID_HANDLE_VALUE)own(thread,pi.hThread,"observer_thread");host_pid=pi.dwProcessId;
        api("CreateProcessW","observer","launch",host.h,cp,e,sizeof(pi),sizeof(pi),bytes(&pi,sizeof(pi)),obj({{"flags",n(0x08080404)},{"inherit_handles",n(1)},{"command",quote(ascii(command))},{"desktop",quote(ascii(desktop_name))},{"launch_anchor",q(launch_started)}}),b);delete_attributes(attributes,attributes_ready);demand(cp&&host.h&&thread.h&&host_pid&&pi.dwThreadId,"suspended observer denied");
        for(auto &role:inherited)close_owned(role);
        auto hi=process_identity(host,observer,"startup",oi.pid,oi.creation,true);host_creation=hi.creation;demand(hi.pid==host_pid&&parent_of(host_pid)==oi.pid,"observer actual parent changed");
        b=tick();SetLastError(0);jr=AssignProcessToJobObject(job.h,host.h);e=GetLastError();api("AssignProcessToJobObject","observer","startup",host.h,jr,e,0,0,Bytes(),obj({{"job",n(bits(job.h))}}),b);demand(jr,"observer job admission failed");host_assigned=true;membership(host,job,"startup");limits(job,"startup");
        b=tick();SetLastError(0);DWORD resume=ResumeThread(thread.h);e=GetLastError();api("ResumeThread","observer_thread","startup",thread.h,resume,e,0,0,Bytes(),"{}",b);demand(resume==1,"exactly once suspended observer resume required");close_owned(thread);
        auto remaining=[&](Tick *original=nullptr){Tick now=tick();if(original)*original=now;demand(now.result&&now.tick>=launch_started.tick&&now.tick-launch_started.tick<35*static_cast<LONGLONG>(frequency),"unchanged outer35s exhausted");return static_cast<DWORD>(((35*frequency-(now.tick-launch_started.tick))*1000)/frequency);};
        Tick gate_timeout_counter;DWORD gate_timeout=remaining(&gate_timeout_counter);HANDLE gate_waiters[2]={challenge_event.h,host.h};b=tick();SetLastError(0);DWORD wait=WaitForMultipleObjects(2,gate_waiters,FALSE,gate_timeout);e=GetLastError();
        api("WaitForMultipleObjects","challenge_event","gate",challenge_event.h,wait,e,sizeof(gate_waiters),sizeof(gate_waiters),bytes(gate_waiters,sizeof(gate_waiters)),obj({{"count",n(2)},{"wait_all",n(0)},{"timeout_ms",n(gate_timeout)},{"timeout_counter",q(gate_timeout_counter)}}),b);
        demand(wait==WAIT_OBJECT_0,"genuine challenge event missing/late or observer already exited");
        Bytes original_challenge=read_exact(challenge_reader,576,"challenge");GatePacket challenge;memcpy(&challenge,original_challenge.data(),576);
        demand(!memcmp(challenge.magic,"CLHDGA3\0",8)&&challenge.version==3&&challenge.kind==1&&challenge.sequence==1&&challenge.size==576&&!challenge.reserved,"original challenge header differs");
        demand(hash_bytes(Bytes(original_challenge.begin(),original_challenge.begin()+544),"challenge_prefix")==hex(challenge.trailer,32),"original challenge prefix hash differs");
        demand(!memcmp(challenge.ids,boot.data()+64,48)&&challenge.frequency==frequency&&challenge.origin==get64(boot,48)&&challenge.initial>=challenge.origin&&
            challenge.refs[0]&&challenge.refs[1]&&challenge.refs[2]&&!challenge.refs[3]&&!challenge.refs[4]&&!challenge.refs[5]&&challenge.refs[6]==channel_sequence,"original challenge epoch/actor slots differ");
        for(unsigned i=0;i<6;++i)demand(!memcmp(challenge.hashes+32*i,boot.data()+112+32*i,32),"original source/request/candidate bindings differ");
        demand(!memcmp(challenge.hashes+192,boot.data()+32768,32)&&!memcmp(challenge.hashes+224,boot.data()+304,32)&&hex(challenge.hashes+256,32)==hash_bytes(boot,"bootstrap_join"),"observer/source/bootstrap binding differs");
        for(unsigned i=0;i<32;++i)demand(challenge.hashes[288+i]==0,"challenge self-hash must be zero");
        demand(challenge.generations[0].pid==ci.pid&&challenge.generations[0].creation==ci.creation&&challenge.generations[1].pid==oi.pid&&challenge.generations[1].creation==oi.creation&&challenge.generations[2].pid==host_pid&&challenge.generations[2].creation==host_creation,"original actor generations differ");
        Tick held_now=tick();demand(held_now.result&&held_now.tick>=static_cast<LONGLONG>(challenge.initial)&&held_now.tick-challenge.initial<20*frequency,"original earliest hold already exhausted");
        auto before=process_identity(host,observer,"adopt_before",oi.pid,oi.creation,true);demand(before.pid==host_pid&&before.creation==host_creation,"observer changed before live adoption");auto adoption_begin=journal.sequence;
        target_pid=challenge.generations[3].pid;DWORD requested_target_pid=fixture_mode==3?0:target_pid;b=tick();SetLastError(0);HANDLE th=OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION|SYNCHRONIZE|PROCESS_TERMINATE,FALSE,requested_target_pid);e=GetLastError();if(th)own(target,th,"target");api("OpenProcess","target","adoption",th,bits(th),e,0,0,Bytes(),obj({{"pid",n(requested_target_pid)},{"challenged_pid",n(target_pid)}}),b);demand(th,"live target adoption denied");
        demand(parent_of(target_pid)==host_pid,"original target parent differs from observer");auto ti=process_identity(target,candidate,"adopt_before",host_pid,host_creation,true);membership(target,job,"adoption");auto membership_sequence=journal.sequence;
        auto after=process_identity(host,observer,"adopt_after",oi.pid,oi.creation,true);auto ta=process_identity(target,candidate,"adopt_after",host_pid,host_creation,true);auto adoption_end=journal.sequence;
        target_creation=ti.creation;demand(ti.pid==target_pid&&ti.creation==challenge.generations[3].creation&&after.pid==host_pid&&after.creation==host_creation&&ta.pid==target_pid&&ta.creation==target_creation,"original live adoption generation reused/mutated");
        GatePacket adoption=challenge;adoption.kind=2;adoption.refs[3]=adoption_begin;adoption.refs[4]=adoption_end;adoption.refs[5]=membership_sequence;unhex(hash_bytes(original_challenge,"challenge_whole"),adoption.hashes+288,32);
        if(fixture_mode==6)adoption.generations[3].creation^=1;
        if(fixture_mode==7)adoption.nonce[0]^=1;
        Bytes prefix_bytes=bytes(&adoption,544);unhex(hash_bytes(prefix_bytes,"adoption_prefix"),adoption.trailer,32);Bytes original_adoption=bytes(&adoption,576);
        journal.frame("adoption_packet",obj({{"challenge_sha256",quote(hex(adoption.hashes+288,32))},{"target_creation",n(target_creation)}}),original_adoption);
        write_exact(adoption_writer,original_adoption,"adoption");
        if(fixture_mode==5)close_owned(adoption_event);
        if(fixture_mode==8)journal.frame("fixture_withhold_adoption_signal",obj({{"initial_tick",n(challenge.initial)}}));
        else{b=tick();SetLastError(0);BOOL signal=SetEvent(adoption_event.h);e=GetLastError();api("SetEvent","adoption_event","adoption",adoption_event.h,signal,e,0,0,Bytes(),"{}",b);demand(signal,"adoption signal denied");}
        Tick finish_timeout_counter;DWORD finish_timeout=remaining(&finish_timeout_counter);b=tick();SetLastError(0);DWORD finished=WaitForSingleObject(host.h,finish_timeout);e=GetLastError();api("WaitForSingleObject","observer","natural_finish",host.h,finished,e,0,0,Bytes(),obj({{"timeout_ms",n(finish_timeout)},{"timeout_counter",q(finish_timeout_counter)}}),b);Tick finish_counter;remaining(&finish_counter);journal.frame("outer_finish_bound",q(finish_counter));demand(finished==WAIT_OBJECT_0,"observer did not terminate within outer35s");
        DWORD exit=0;b=tick();SetLastError(0);BOOL er=GetExitCodeProcess(host.h,&exit);e=GetLastError();api("GetExitCodeProcess","observer","natural_finish",host.h,er,e,4,4,bytes(&exit,4),"{}",b);demand(er&&exit==0,"observer retained failure is not a passing composition");
        membership(host,job,"precleanup");membership(target,job,"precleanup");limits(job,"precleanup");auto before_cleanup=pids(job,"precleanup");
        for(DWORD pid:before_cleanup)demand(pid==host_pid||pid==target_pid,"late unknown job descendant rejected");accounting(job,"precleanup");
    }catch(const std::exception&e){failure_reason="original setup/gate/adoption failure";rejected(e.what());}catch(...){failed=true;debt=true;failure_reason="unknown original failure";}
    delete_attributes(attributes,attributes_ready);
    if(fixture_mode==10){Tick b=tick();SetLastError(0);BOOL original=TerminateJobObject(nullptr,0);DWORD error=GetLastError();api("TerminateJobObject","fixture_invalid_job","cleanup",nullptr,original,error,0,0,Bytes(),"{}",b);if(!original)failed=true;}
    stop_owned(job,true);if(host.h&&!host_assigned)stop_owned(host,false);
    for(auto *process:{&host,&target})if(process->h){wait_owned(*process);try{process_identity(*process,process==&host?observer:candidate,"exit",process==&host?GetCurrentProcessId():host_pid,process==&host?outer_creation:host_creation,false);}catch(const std::exception&e){rejected(e.what());}catch(...){failed=true;debt=true;}}
    if(job.h){unsigned empties=0;Tick start=tick();for(unsigned i=0;i<512&&empties<2;++i){try{auto rows=pids(job,"drain");DWORD active=accounting(job,"drain");for(DWORD pid:rows)if(pid!=host_pid&&pid!=target_pid)failed=true;
        empties=rows.empty()&&active==0?empties+1:0;Tick now=tick();if(!now.result||now.tick-start.tick>5*static_cast<LONGLONG>(frequency)){failed=true;break;}if(empties<2)Sleep(1);}catch(const std::exception&e){rejected(e.what());break;}catch(...){failed=true;debt=true;break;}}if(empties!=2)failed=true;}
    for(auto &x:inherited)close_owned(x);close_owned(thread);close_owned(target);close_owned(host);close_owned(job);close_owned(desktop,true);
    for(auto*x:{&stdin_original,&archive,&stderr_file,&challenge_writer,&challenge_reader,&adoption_writer,&adoption_reader,&challenge_event,&adoption_event,&boot_file,&caller,&self})close_owned(*x);
    for(auto*f:{&observer,&candidate,&request,&payload,&caller_image,&self_image})close_owned(f->handle);while(directory_count)close_owned(directories[--directory_count]);
    journal.frame("finish",obj({{"failed",failed?"1":"0"},{"debt",debt?"1":"0"},{"scope",quote("V3_initial_loader_terminate_only")}}));
    if(!journal.begun){for(const auto&row:journal.prelude)journal.emergency("unpublished original prelude "+row.operation+" "+row.data,row.original);failed=true;debt=true;}
    return failed||debt?1:0;
}
'''


def render_outer_source(*, fixture_mode=0):
    _require(type(fixture_mode) is int and fixture_mode in range(11), "source-owned synthetic cases only")
    rendered = OUTER_HELPERS + OUTER_MAIN.replace("@MODE@", str(fixture_mode)).replace("@PEAK@", str(retention_budget()["fixed_required_peak_bytes"]))
    _require("@" not in rendered, "unresolved outer source")
    return rendered.encode("ascii")


def _api_factory(_path=Path(__file__).resolve(), _read=Path.read_bytes, _sha256=hashlib.sha256,
                 _closed_compile=_closed):
    raw = _read(_path)
    names = ("prepare_plan", "prepare_request", "render_observer", "inspect_request")
    module = _closed_compile(raw, _path, names, "_api_factory")
    apis = module._factory(); require = module._require
    def captured(operation):
        def invoke(*args, **kwargs):
            require(_read(_path) == raw, "imported canonical V3 changed before dispatch")
            result = operation(*args, **kwargs)
            require(_read(_path) == raw, "imported canonical V3 changed after dispatch")
            return result
        return invoke
    return tuple(captured(operation) for operation in apis)


# Owned V3 source; no dependency on the unpublished controller module.
OUTER_HELPERS = r'''
// Fixed WIN64 outer controller; no game commands, GO, probe or input APIs.
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <tlhelp32.h>
#include <bcrypt.h>
#include <algorithm>
#include <array>
#include <cctype>
#include <cstdio>
#include <cstring>
#include <cwctype>
#include <iostream>
#include <map>
#include <stdexcept>
#include <string>
#include <vector>
#pragma comment(lib,"bcrypt.lib")
static_assert(sizeof(void*)==8,"WIN64 outer controller required");
static_assert(sizeof(JOBOBJECT_EXTENDED_LIMIT_INFORMATION)==144,"fixed WIN64 limits");
static_assert(sizeof(JOBOBJECT_BASIC_ACCOUNTING_INFORMATION)==48,"fixed accounting");
static_assert(sizeof(PROCESSENTRY32W)==568,"full original WIN64 Toolhelp row");
using Bytes=std::vector<unsigned char>;
static std::wstring root_value,archive_value;
static const wchar_t *c_root=L".",*c_job_archive=L"";
static unsigned long long c_approved_peak=0;
static const unsigned long long metadata_cap=33554432, failure_metadata_cap=33554432;
static const unsigned long long raw_cap=67108864, failure_raw_cap=67108864;
static const unsigned long long event_cap=32768, pending_cap=16777216;
static bool failed=false, debt=false;
static const char *failure_reason="";
static unsigned long long bits(HANDLE h){return static_cast<unsigned long long>(reinterpret_cast<ULONG_PTR>(h));}
static unsigned long long ft(FILETIME f){return (static_cast<unsigned long long>(f.dwHighDateTime)<<32)|f.dwLowDateTime;}
static std::string n(unsigned long long x){return std::to_string(x);}
static std::string sn(long long x){return std::to_string(x);}
static std::string hex(const void *p,size_t size){static const char t[]="0123456789abcdef";std::string out;out.reserve(2*size);
    const auto *b=static_cast<const unsigned char*>(p);for(size_t i=0;i<size;++i){out+=t[b[i]>>4];out+=t[b[i]&15];}return out;}
static std::string quote(const std::string &s){std::string out="\"";for(unsigned char c:s){if(c=='\"'||c=='\\'){out+='\\';out+=c;}
    else if(c<32||c>126){char v[7];sprintf_s(v,"\\u%04x",c);out+=v;}else out+=c;}return out+'\"';}
static std::string obj(std::initializer_list<std::pair<std::string,std::string>> rows){std::map<std::string,std::string> sorted;
    for(const auto &row:rows)if(!sorted.emplace(row.first,row.second).second)throw std::runtime_error("duplicate canonical key");
    std::string out="{";bool first=true;for(const auto &row:sorted){if(!first)out+=',';first=false;out+=quote(row.first)+":"+row.second;}return out+'}';}
static std::string ascii(const std::wstring &s){std::string out;for(wchar_t c:s){if(c>127)throw std::runtime_error("ASCII scope mismatch");out+=static_cast<char>(c);}return out;}
static std::wstring lower(std::wstring s){for(auto &c:s)c=static_cast<wchar_t>(towlower(c));return s;}
static void demand(bool yes,const char *why){if(!yes)throw std::runtime_error(why);}
struct Tick{BOOL result=0;DWORD error=0;LONGLONG tick=0;};
static Tick tick(){Tick t;LARGE_INTEGER v={};SetLastError(0);t.result=QueryPerformanceCounter(&v);t.error=GetLastError();t.tick=v.QuadPart;return t;}
static std::string q(const Tick &t){return obj({{"result",sn(t.result)},{"error",n(t.error)},{"tick",sn(t.tick)}});}
static Tick last_tick;
static bool reserve_original(){ULARGE_INTEGER free={},total={},unused={};SetLastError(0);
    BOOL r=GetDiskFreeSpaceExW(c_root,&free,&total,&unused);DWORD e=GetLastError();
    std::cerr<<"ORIGINAL_PREWRITE_RESERVE "<<obj({{"return",sn(r)},{"error",n(e)},{"free",n(free.QuadPart)},
        {"total",n(total.QuadPart)},{"unused",n(unused.QuadPart)},{"required_peak",n(c_approved_peak)}})<<"\n";
    return r&&free.QuadPart>c_approved_peak&&free.QuadPart-c_approved_peak>total.QuadPart/10;}
struct Journal {
    HANDLE out=GetStdHandle(STD_OUTPUT_HANDLE);unsigned long long sequence=0,meta=8,raw=0,pending=0;
    bool begun=false;struct Pending{std::string operation,data;Bytes original;};std::vector<Pending> prelude;
    void emergency(const std::string &message,const Bytes &original=Bytes()) noexcept {
        debt=true;failed=true;
        try {if(pending+message.size()+2*original.size()>pending_cap){std::cerr<<"UNKNOWN_ORIGINAL_OUTPUT_DEBT size="<<original.size()<<"\n";return;}
            pending+=message.size()+2*original.size();std::cerr<<"ORIGINAL_PENDING "<<message<<" raw="<<hex(original.data(),original.size())<<"\n";}
        catch(...){debt=true;}
    }
    void begin(){SetLastError(0);DWORD type=GetFileType(out),type_error=GetLastError();
        demand(type==FILE_TYPE_DISK,"regular external job archive required");
        std::array<wchar_t,32768> path={};SetLastError(0);DWORD chars=GetFinalPathNameByHandleW(out,path.data(),static_cast<DWORD>(path.size()),FILE_NAME_NORMALIZED|VOLUME_NAME_DOS);DWORD path_error=GetLastError();
        std::cerr<<"ORIGINAL_ARCHIVE_PATH "<<obj({{"return",n(chars)},{"error",n(path_error)},{"capacity",n(sizeof(path))}})<<" raw="<<hex(path.data(),sizeof(path))<<"\n";
        demand(chars&&chars<path.size(),"original external archive path unavailable");std::wstring final(path.data(),chars);if(final.substr(0,4)==L"\\\\?\\")final=final.substr(4);
        demand(lower(final)==lower(c_job_archive),"borrowed archive escaped independent dedicated root");
        demand(reserve_original(),"reserve blocks magic; original available receipts remain external stderr debt");
        DWORD got=0;SetLastError(0);BOOL wr=WriteFile(out,"CLHDOUT3",8,&got,nullptr);DWORD we=GetLastError();
        SetLastError(0);BOOL fl=FlushFileBuffers(out);DWORD fe=GetLastError();
        std::cerr<<"ORIGINAL_MAGIC_IO "<<obj({{"type",n(type)},{"type_error",n(type_error)},{"write_return",sn(wr)},
            {"write_error",n(we)},{"requested",n(8)},{"returned",n(got)},{"flush_return",sn(fl)},{"flush_error",n(fe)}})<<" raw=434c48444f555433\n";
        demand(wr&&got==8&&fl,"original magic write/flush failed; stderr originals retained");
        begun=true;auto original=std::move(prelude);prelude.clear();for(const auto &row:original)frame(row.operation,row.data,row.original);
    }
    bool frame(const std::string &operation,const std::string &data,const Bytes &original=Bytes()) noexcept {
        try {
            if(!begun){demand(pending+operation.size()+data.size()+original.size()<=pending_cap,"original prelude RAM exceeds bound; debt");
                pending+=operation.size()+data.size()+original.size();prelude.push_back(Pending{operation,data,original});return true;}
            std::string json=obj({{"sequence",n(sequence+1)},{"operation",quote(operation)},{"data",data}});
            demand(json.size()<=512*1024&&original.size()<=4096*(568+8),"original packet exceeds fixed capacity");
            demand(sequence<event_cap&&meta+json.size()+32<=failure_metadata_cap&&raw+original.size()<=failure_raw_cap,"original journal exhausted; debt");
            Bytes block(8+json.size()+original.size());ULONG sizes[2]={static_cast<ULONG>(json.size()),static_cast<ULONG>(original.size())};
            memcpy(block.data(),sizes,8);memcpy(block.data()+8,json.data(),json.size());if(!original.empty())memcpy(block.data()+8+json.size(),original.data(),original.size());
            demand(reserve_original(),"reserve blocks packet; complete pending original bytes remain debt");
            DWORD got=0;SetLastError(0);BOOL wr=WriteFile(out,block.data(),static_cast<DWORD>(block.size()),&got,nullptr);DWORD we=GetLastError();
            SetLastError(0);BOOL fl=FlushFileBuffers(out);DWORD fe=GetLastError();
            struct Tail{LONG wr;DWORD we,requested,got;LONG fl;DWORD fe;};static_assert(sizeof(Tail)==24,"fixed original main IO");
            Tail tail={wr,we,static_cast<DWORD>(block.size()),got,fl,fe};
            if(!reserve_original()){emergency("reserve blocked footer; original main IO="+hex(&tail,sizeof(tail)),block);return false;}
            DWORD tg=0;SetLastError(0);BOOL tw=WriteFile(out,&tail,24,&tg,nullptr);DWORD te=GetLastError();
            SetLastError(0);BOOL tf=FlushFileBuffers(out);DWORD tfe=GetLastError();
            std::cerr<<"ORIGINAL_RECEIPT_TAIL "<<obj({{"sequence",n(sequence+1)},{"write_return",sn(tw)},{"write_error",n(te)},
                {"requested",n(24)},{"returned",n(tg)},{"flush_return",sn(tf)},{"flush_error",n(tfe)}})<<"\n";
            ++sequence;meta+=json.size()+32;raw+=original.size();
            if(!wr||got!=block.size()||!fl||!tw||tg!=24||!tf){emergency("original packet/receipt-tail IO failed",block);return false;}
            if(meta>metadata_cap||raw>raw_cap){emergency("complete original over normal capacity retained");return false;}return true;
        }catch(const std::exception &e){try{emergency(e.what()+std::string(" data=")+data,original);}
            catch(...){failed=true;debt=true;fprintf(stderr,"UNKNOWN_ORIGINAL_SERIALIZATION_DEBT raw_size=%zu\n",original.size());
                if(!original.empty())fwrite(original.data(),1,original.size(),stderr);}return false;}
        catch(...){failed=true;debt=true;fprintf(stderr,"UNKNOWN_ORIGINAL_SERIALIZATION_DEBT raw_size=%zu\n",original.size());
            if(!original.empty())fwrite(original.data(),1,original.size(),stderr);return false;}
    }
} journal;
static void original_debt(const char *name,HANDLE handle,long long result,DWORD error,DWORD requested,DWORD returned,
                          const void *raw,size_t size,const Tick &begin,const Tick &end) noexcept {
    failed=true;debt=true;failure_reason="original diagnostic serialization/storage failure";
    fprintf(stderr,"ORIGINAL_UNSERIALIZED_API %s handle=%llu result=%lld error=%lu requested=%lu returned=%lu begin=%ld/%lu/%lld end=%ld/%lu/%lld raw_size=%zu\n",
        name,bits(handle),result,error,requested,returned,begin.result,begin.error,begin.tick,end.result,end.error,end.tick,size);
    if(size&&fwrite(raw,1,size,stderr)!=size)fprintf(stderr,"UNKNOWN_ORIGINAL_OUTPUT_DEBT raw_size=%zu\n",size);
}
static void api(const char *name,const char *role,const char *phase,HANDLE handle,long long result,DWORD error,
                DWORD requested=0,DWORD returned=0,const Bytes &raw=Bytes(),const std::string &detail="{}",Tick begin=Tick()) noexcept {
    Tick end=tick();try {bool retained=journal.frame("api",obj({{"name",quote(name)},{"role",quote(role)},{"phase",quote(phase)},
        {"handle",n(bits(handle))},{"result",!strcmp(name,"DeleteProcThreadAttributeList")?"null":sn(result)},
        {"error",n(error)},{"requested",n(requested)},{"returned",n(returned)},
        {"length_kind",quote(!strcmp(name,"ReadFile")||!strcmp(name,"QueryFullProcessImageNameW")||!strcmp(name,"GetFinalPathNameByHandleW")||!strcmp(name,"GetModuleFileNameW")||strstr(name,"QueryInformationJobObject.")==name||!strcmp(name,"BCryptGetProperty")?"original_native_count":"source_capacity_no_native_count")},
        {"begin",q(begin)},{"end",q(end)},{"detail",detail}}),raw);
    if(!begin.result||!end.result||begin.tick<=0||end.tick<begin.tick||begin.tick<last_tick.tick){failed=true;failure_reason="native QPC query/order failed";}
    last_tick=end;if(!retained){failed=true;debt=true;}
    }catch(...){original_debt(name,handle,result,error,requested,returned,raw.data(),raw.size(),begin,end);}
}
struct Owned{const char *role="";HANDLE h=nullptr;bool closed=false;};
// Immediate pointer/handle stores only: no allocation or diagnostic can precede adoption.
static void own(Owned &x,HANDLE h,const char *role) noexcept {x.h=h;x.role=role;}
static void close_owned(Owned &x,bool desktop=false) noexcept {if(x.closed||!x.h||x.h==INVALID_HANDLE_VALUE)return;
    Tick b=tick();SetLastError(0);BOOL v=desktop?CloseDesktop(reinterpret_cast<HDESK>(x.h)):CloseHandle(x.h);DWORD e=GetLastError();
    x.closed=true;try{api(desktop?"CloseDesktop":"CloseHandle",x.role,"close",x.h,v,e,0,0,Bytes(),"{}",b);}
    catch(...){original_debt(desktop?"CloseDesktop":"CloseHandle",x.h,v,e,0,0,nullptr,0,b,tick());}
    if(!v){failed=true;failure_reason="owned close denied";}}
static void rejected(const char *message) noexcept {
    failed=true;try{journal.frame("rejected",obj({{"message",quote(message)}}));}
    catch(...){debt=true;fprintf(stderr,"ORIGINAL_REJECTION_UNSERIALIZED %s\n",message);}}
static void delete_attributes(LPPROC_THREAD_ATTRIBUTE_LIST attributes,bool &initialized) noexcept {
    if(!initialized)return;Tick b=tick();DeleteProcThreadAttributeList(attributes);initialized=false;
    try{api("DeleteProcThreadAttributeList","attributes","close",reinterpret_cast<HANDLE>(attributes),0,0,0,0,Bytes(),"{\"return_kind\":\"void\"}",b);}
    catch(...){original_debt("DeleteProcThreadAttributeList",reinterpret_cast<HANDLE>(attributes),0,0,0,0,nullptr,0,b,tick());}}
static void stop_owned(Owned &x,bool job) noexcept {
    if(!x.h||x.h==INVALID_HANDLE_VALUE)return;Tick b=tick();SetLastError(0);
    BOOL r=job?TerminateJobObject(x.h,0):TerminateProcess(x.h,1);DWORD e=GetLastError();
    try{api(job?"TerminateJobObject":"TerminateProcess",x.role,"cleanup",x.h,r,e,0,0,Bytes(),"{}",b);}
    catch(...){original_debt(job?"TerminateJobObject":"TerminateProcess",x.h,r,e,0,0,nullptr,0,b,tick());}if(!r)failed=true;}
static void wait_owned(Owned &x) noexcept {
    if(!x.h||x.h==INVALID_HANDLE_VALUE)return;Tick b=tick();SetLastError(0);DWORD r=WaitForSingleObject(x.h,5000),e=GetLastError();
    try{api("WaitForSingleObject",x.role,"cleanup",x.h,r,e,0,0,Bytes(),"{\"timeout\":5000}",b);}
    catch(...){original_debt("WaitForSingleObject",x.h,r,e,0,0,nullptr,0,b,tick());}if(r!=WAIT_OBJECT_0)failed=true;}
struct File{Owned handle;BY_HANDLE_FILE_INFORMATION info={};std::wstring path;std::string digest;};
static Bytes bytes(const void *p,size_t size){const auto *a=static_cast<const unsigned char*>(p);return Bytes(a,a+size);}
static std::wstring final_path(HANDLE h,const char *role){std::array<wchar_t,32768> v={};Tick b=tick();SetLastError(0);
    DWORD count=GetFinalPathNameByHandleW(h,v.data(),static_cast<DWORD>(v.size()),FILE_NAME_NORMALIZED|VOLUME_NAME_DOS);DWORD error=GetLastError();
    api("GetFinalPathNameByHandleW",role,"path",h,count,error,sizeof(v),count,bytes(v.data(),sizeof(v)),"{}",b);
    demand(count&&count<v.size(),"complete original final path unavailable");std::wstring s(v.data(),count);
    if(s.substr(0,4)==L"\\\\?\\")s=s.substr(4);return lower(s);}
static BY_HANDLE_FILE_INFORMATION info(HANDLE h,const char *role){BY_HANDLE_FILE_INFORMATION v={};Tick b=tick();SetLastError(0);
    BOOL r=GetFileInformationByHandle(h,&v);DWORD e=GetLastError();api("GetFileInformationByHandle",role,"identity",h,r,e,sizeof(v),sizeof(v),bytes(&v,sizeof(v)),"{}",b);
    demand(r&&!(v.dwFileAttributes&FILE_ATTRIBUTE_REPARSE_POINT),"reparse/unknown file identity rejected");return v;}
static unsigned long long fileid(const BY_HANDLE_FILE_INFORMATION &v){return (static_cast<unsigned long long>(v.nFileIndexHigh)<<32)|v.nFileIndexLow;}
static std::string hash_bytes(const Bytes &data,const char *role){BCRYPT_ALG_HANDLE a=nullptr;BCRYPT_HASH_HANDLE h=nullptr;DWORD size=0,returned=0;
    auto retire=[&]() noexcept {if(h){HANDLE original=reinterpret_cast<HANDLE>(h);Tick b=tick();NTSTATUS r=BCryptDestroyHash(h);h=nullptr;
            try{api("BCryptDestroyHash",role,"close",original,r,0,0,0,Bytes(),"{}",b);}catch(...){original_debt("BCryptDestroyHash",original,r,0,0,0,nullptr,0,b,tick());}if(r)failed=true;}
        if(a){HANDLE original=reinterpret_cast<HANDLE>(a);Tick b=tick();NTSTATUS r=BCryptCloseAlgorithmProvider(a,0);a=nullptr;
            try{api("BCryptCloseAlgorithmProvider",role,"close",original,r,0,0,0,Bytes(),"{}",b);}catch(...){original_debt("BCryptCloseAlgorithmProvider",original,r,0,0,0,nullptr,0,b,tick());}if(r)failed=true;}};
    try{Tick b=tick();NTSTATUS r=BCryptOpenAlgorithmProvider(&a,BCRYPT_SHA256_ALGORITHM,nullptr,0);api("BCryptOpenAlgorithmProvider",role,"hash",reinterpret_cast<HANDLE>(a),r,0,0,0,Bytes(),"{}",b);demand(r==0&&a,"hash provider failed");
        b=tick();r=BCryptGetProperty(a,BCRYPT_OBJECT_LENGTH,reinterpret_cast<PUCHAR>(&size),4,&returned,0);api("BCryptGetProperty",role,"hash",reinterpret_cast<HANDLE>(a),r,0,4,returned,bytes(&size,4),"{}",b);
        demand(r==0&&returned==4&&size&&size<=65536,"bounded original hash object capacity required");
        Bytes object(size),digest(32);b=tick();r=BCryptCreateHash(a,&h,object.data(),size,nullptr,0,0);api("BCryptCreateHash",role,"hash",reinterpret_cast<HANDLE>(h),r,0,size,size,object,"{}",b);demand(r==0&&h,"original hash creation failed");
        b=tick();r=BCryptHashData(h,const_cast<PUCHAR>(data.data()),static_cast<ULONG>(data.size()),0);api("BCryptHashData",role,"hash",reinterpret_cast<HANDLE>(h),r,0,static_cast<DWORD>(data.size()),0,Bytes(),"{}",b);demand(r==0,"original hash data failed");
        b=tick();r=BCryptFinishHash(h,digest.data(),32,0);api("BCryptFinishHash",role,"hash",reinterpret_cast<HANDLE>(h),r,0,32,32,digest,"{}",b);demand(r==0,"original hash finish failed");
        retire();demand(!failed&&!debt,"hash cleanup/retention failed");return hex(digest.data(),32);
    }catch(...){retire();throw;}}
static void open_file(File &f,const wchar_t *path,const char *role,unsigned long long cap,const char *expected){f.path=lower(path);Tick b=tick();SetLastError(0);
    HANDLE h=CreateFileW(path,GENERIC_READ,FILE_SHARE_READ,nullptr,OPEN_EXISTING,FILE_FLAG_OPEN_REPARSE_POINT,nullptr);DWORD e=GetLastError();
    if(h&&h!=INVALID_HANDLE_VALUE)own(f.handle,h,role);
    api("CreateFileW",role,"input",h,bits(h),e,0,0,Bytes(),obj({{"path",quote(ascii(f.path))}}),b);demand(h&&h!=INVALID_HANDLE_VALUE,"input file denied");
    f.info=info(h,role);demand(final_path(h,role)==f.path,"input path escaped frozen root");
    LARGE_INTEGER size={};b=tick();SetLastError(0);BOOL sr=GetFileSizeEx(h,&size);e=GetLastError();api("GetFileSizeEx",role,"input",h,sr,e,8,8,bytes(&size,8),"{}",b);
    demand(sr&&size.QuadPart>0&&static_cast<unsigned long long>(size.QuadPart)<=cap,"input size exceeds source bound");Bytes data;data.reserve(static_cast<size_t>(size.QuadPart));
    while(data.size()<static_cast<size_t>(size.QuadPart)){Bytes block(65536);DWORD got=0,request=static_cast<DWORD>(std::min<size_t>(block.size(),static_cast<size_t>(size.QuadPart)-data.size()));
        b=tick();SetLastError(0);BOOL rr=ReadFile(h,block.data(),request,&got,nullptr);e=GetLastError();api("ReadFile",role,"input",h,rr,e,request,got,block,"{}",b);
        demand(rr&&got==request,"original partial input retained; no retry/replacement");data.insert(data.end(),block.begin(),block.begin()+got);}
    f.digest=hash_bytes(data,role);demand(!expected||f.digest==expected,"physical frozen input hash differs");
    journal.frame("artifact",obj({{"role",quote(role)},{"path",quote(ascii(f.path))},{"sha256",quote(f.digest)},
        {"volume",n(f.info.dwVolumeSerialNumber)},{"file_id",n(fileid(f.info))},{"size",n(data.size())}}));}
struct Identity{DWORD pid;unsigned long long creation;};
static Identity process_identity(Owned &x,File &image,const char *phase,DWORD parent_pid,unsigned long long parent_creation,bool require_live){
    Tick b=tick();SetLastError(0);DWORD pid=GetProcessId(x.h),pe=GetLastError();api("GetProcessId",x.role,phase,x.h,pid,pe,0,0,Bytes(),"{}",b);
    std::array<wchar_t,32768> path={};DWORD chars=static_cast<DWORD>(path.size());b=tick();SetLastError(0);BOOL pr=QueryFullProcessImageNameW(x.h,0,path.data(),&chars);DWORD e=GetLastError();
    api("QueryFullProcessImageNameW",x.role,phase,x.h,pr,e,sizeof(path),chars,bytes(path.data(),sizeof(path)),"{}",b);
    FILETIME t[4]={};b=tick();SetLastError(0);BOOL tr=GetProcessTimes(x.h,&t[0],&t[1],&t[2],&t[3]);e=GetLastError();api("GetProcessTimes",x.role,phase,x.h,tr,e,32,32,bytes(t,32),"{}",b);
    b=tick();SetLastError(0);DWORD waited=WaitForSingleObject(x.h,0),we=GetLastError();api("WaitForSingleObject",x.role,phase,x.h,waited,we,0,0,Bytes(),obj({{"timeout",n(0)}}),b);
    DWORD exit=0;b=tick();SetLastError(0);BOOL er=GetExitCodeProcess(x.h,&exit);e=GetLastError();api("GetExitCodeProcess",x.role,phase,x.h,er,e,4,4,bytes(&exit,4),"{}",b);
    journal.frame("identity",obj({{"role",quote(x.role)},{"phase",quote(phase)},{"pid",n(pid)},
        {"creation",n(ft(t[0]))},{"exit_time",n(ft(t[1]))},{"wait",n(waited)},{"exit_code",n(exit)},
        {"path",quote(pr&&chars<path.size()?ascii(lower(std::wstring(path.data(),chars))):"")},{"sha256",quote(image.digest)},
        {"parent_pid",n(parent_pid)},{"parent_creation",n(parent_creation)},
        {"parent_scope",quote(!strcmp(phase,"startup")?"fresh_snapshot":"previously_proved_retained_generation")}}));
    demand(!failed&&!debt&&pid&&pr&&chars&&chars<path.size()&&tr&&er&&ft(t[0])&&lower(std::wstring(path.data(),chars))==image.path,
        "original process identity unavailable/mismatched");
    demand(require_live?(waited==WAIT_TIMEOUT&&exit==STILL_ACTIVE&&ft(t[1])==0):
        ((waited==WAIT_TIMEOUT&&exit==STILL_ACTIVE&&ft(t[1])==0)||(waited==WAIT_OBJECT_0&&exit!=STILL_ACTIVE&&ft(t[1])>=ft(t[0]))),"native liveness observation failed");
    return Identity{pid,ft(t[0])};
}
static DWORD parent_of(DWORD pid){Owned snapshot;Tick b=tick();SetLastError(0);HANDLE h=CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS,0);DWORD e=GetLastError();
    if(h&&h!=INVALID_HANDLE_VALUE)own(snapshot,h,"snapshot");
    struct Guard{Owned &handle;~Guard() noexcept {close_owned(handle);}} guard{snapshot};
    api("CreateToolhelp32Snapshot","snapshot","parent",h,bits(h),e,0,0,Bytes(),"{}",b);demand(h!=INVALID_HANDLE_VALUE,"original parent snapshot failed");
    PROCESSENTRY32W row={};row.dwSize=sizeof(row);Bytes original;DWORD parent=0,matches=0;unsigned int count=0;
    b=tick();SetLastError(0);BOOL more=Process32FirstW(h,&row);e=GetLastError();
    while(true){LONG result=more;original.insert(original.end(),reinterpret_cast<unsigned char*>(&result),reinterpret_cast<unsigned char*>(&result)+4);
        original.insert(original.end(),reinterpret_cast<unsigned char*>(&e),reinterpret_cast<unsigned char*>(&e)+4);auto copy=bytes(&row,sizeof(row));original.insert(original.end(),copy.begin(),copy.end());
        if(more&&row.th32ProcessID==pid){parent=row.th32ParentProcessID;++matches;}
        if(!more)break;if(++count>=4095){failed=true;debt=true;break;}row={};row.dwSize=sizeof(row);SetLastError(0);more=Process32NextW(h,&row);e=GetLastError();}
    DWORD terminal_error=e;api("Process32FirstW/Process32NextW","snapshot","parent",h,more,e,sizeof(row),static_cast<DWORD>(original.size()),original,obj({{"pid",n(pid)}}),b);
    close_owned(snapshot);
    demand(!failed&&!more&&terminal_error==ERROR_NO_MORE_FILES&&matches==1&&parent,"parent snapshot incomplete/ambiguous");return parent;}
static void membership(Owned &process,Owned &job,const char *phase){BOOL member=FALSE;Tick b=tick();SetLastError(0);
    BOOL r=IsProcessInJob(process.h,job.h,&member);DWORD e=GetLastError();api("IsProcessInJob",process.role,phase,process.h,r,e,4,4,bytes(&member,4),obj({{"job",n(bits(job.h))}}),b);
    demand(r&&member,"actual owned-job membership unavailable");}
static void limits(Owned &job,const char *phase){JOBOBJECT_EXTENDED_LIMIT_INFORMATION v={};DWORD got=0;Tick b=tick();SetLastError(0);
    BOOL r=QueryInformationJobObject(job.h,JobObjectExtendedLimitInformation,&v,sizeof(v),&got);DWORD e=GetLastError();
    api("QueryInformationJobObject.limits",job.role,phase,job.h,r,e,sizeof(v),got,bytes(&v,sizeof(v)),"{}",b);
    demand(r&&got==sizeof(v)&&(v.BasicLimitInformation.LimitFlags&0x2000)&&!(v.BasicLimitInformation.LimitFlags&0x1800),"no-breakaway limit readback rejected");}
static std::vector<DWORD> pids(Owned &job,const char *phase){std::array<unsigned char,520> v={};DWORD got=0;Tick b=tick();SetLastError(0);
    BOOL r=QueryInformationJobObject(job.h,JobObjectBasicProcessIdList,v.data(),static_cast<DWORD>(v.size()),&got);DWORD e=GetLastError();
    api("QueryInformationJobObject.pids",job.role,phase,job.h,r,e,520,got,bytes(v.data(),520),"{}",b);
    auto *rows=reinterpret_cast<JOBOBJECT_BASIC_PROCESS_ID_LIST*>(v.data());demand(r&&rows->NumberOfAssignedProcesses<=64&&rows->NumberOfProcessIdsInList==rows->NumberOfAssignedProcesses&&got==8+8*rows->NumberOfProcessIdsInList,"original job PID list incomplete");
    std::vector<DWORD> out;for(DWORD i=0;i<rows->NumberOfProcessIdsInList;++i){demand(rows->ProcessIdList[i]&&rows->ProcessIdList[i]<=MAXDWORD,"invalid/unknown PID width");out.push_back(static_cast<DWORD>(rows->ProcessIdList[i]));}return out;}
static DWORD accounting(Owned &job,const char *phase){JOBOBJECT_BASIC_ACCOUNTING_INFORMATION v={};DWORD got=0;Tick b=tick();SetLastError(0);
    BOOL r=QueryInformationJobObject(job.h,JobObjectBasicAccountingInformation,&v,sizeof(v),&got);DWORD e=GetLastError();
    api("QueryInformationJobObject.accounting",job.role,phase,job.h,r,e,sizeof(v),got,bytes(&v,sizeof(v)),"{}",b);
    demand(r&&got==sizeof(v),"original accounting unavailable");return v.ActiveProcesses;}
// Minimal source-owned JSON decoder for discovery; original whole packets are retained first.
'''


prepare_plan, prepare_request, render_observer, inspect_request = _api_factory()
