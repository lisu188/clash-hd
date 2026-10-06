"""Pure source-owned comparison of initial loader-held PE32 observations.

Public APIs privately reconstruct the four frozen all-preset parent recipes.
Reports, public constructor aliases, span lists and pass flags grant no byte
authority. Raw reads remain owned in the returned result, including failures.
No native/read/filesystem adapter, launch, probe execution or acceptance exists.
The strict mapped-header ImageBase policy is unverified against a native loader.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import asdict, dataclass, fields, is_dataclass
import hashlib
import json
from pathlib import Path, PureWindowsPath
import re
import struct
import sys
import types
import uuid

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "tools/hidden_soak_loaded_image.py"
CONTEXT = "src/patcher/battle_profile_context.py"
PE = "src/patcher/pe_extension.py"
PINNED = {
    CONTEXT: "be3bbca018c415895ba7e79e64862512f330297fb56b4d8321f8f6d378c38500",
    PE: "4d66e7fa3bf17c6260fffaefc8d4e4e8da0ba76ceea7746858c52299f74d7c27",
}
SCHEMA = "hidden_soak_loaded_image_v1"
CHUNK_BYTES, MAX_IMAGE_BYTES, MAX_READ_TOTAL = 64 * 1024, 64 * 1024 * 1024, 16 * 1024 * 1024
MAX_READS, MAX_HOLD_NS, USER_LIMIT = 512, 20_000_000_000, 0x7ffe0000
HEADER_POLICY = "canonical_preferred_ImageBase_DWORD_unchanged_native_behavior_unverified"
PHASE_QUERY_NAMES = ("IDebugControl.GetExecutionStatus", "IDebugSystemObjects.GetCurrentProcessSystemId",
                     "IDebugSystemObjects.GetCurrentThreadSystemId", "IDebugSystemObjects.GetCurrentProcessId",
                     "IDebugSystemObjects.GetCurrentThreadId")
FALSE_CLAIMS = {name: False for name in (
    "passed", "loaded_candidate_verified", "native_loaded_bytes_verified", "native_probe_verified", "canonical_probe_executed",
    "producer_capability_verified", "no_breakaway_job_verified", "runtime_acceptance",
    "release_acceptance", "manual_input_verified", "promotion_ready", "whole_image_verified")}


def _require(value, message):
    if not value:
        raise ValueError(message)


def _int(value, maximum, label, minimum=0):
    _require(type(value) is int and minimum <= value <= maximum, label)


def _hresult(value):
    _int(value, 0xffffffff, "original signed32 or unsigned32 HRESULT integer required", -(1 << 31))


def _sha(data):
    _require(type(data) is bytes, "original byte string required")
    return hashlib.sha256(data).hexdigest()


def _digest(value):
    _require(type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value), "canonical SHA-256 required")


def _token(value):
    _require(type(value) is str and re.fullmatch(r"[0-9a-f]{32}", value), "canonical independently owned token required")


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def _object(pairs):
    result = {}
    for key, value in pairs:
        _require(key not in result, "duplicate JSON field")
        result[key] = value
    return result


def _json(text):
    _require(type(text) is str and len(text) <= MAX_IMAGE_BYTES, "bounded canonical JSON required")
    result = json.loads(text, object_pairs_hook=_object,
                        parse_constant=lambda value: (_ for _ in ()).throw(ValueError("nonfinite JSON")))
    _require(_canonical(result) == text, "noncanonical JSON")
    return result


def _path(value):
    _require(type(value) is str and 0 < len(value) <= 4096 and re.match(r"^[A-Za-z]:[\\/]", value)
             and not any(c in value for c in "\0\r\n") and ":" not in value[2:]
             and ".." not in PureWindowsPath(value).parts, "unambiguous local Windows image path required")
    return str(PureWindowsPath(value)).casefold()


@dataclass(frozen=True)
class Generation:
    pid: int
    creation_filetime: int
    image_path: str
    image_sha256: str

    def __post_init__(self):
        _int(self.pid, 0xffffffff, "invalid native PID", 1)
        _int(self.creation_filetime, 0xffffffffffffffff, "invalid native creation FILETIME", 1)
        object.__setattr__(self, "image_path", _path(self.image_path))
        _require(self.image_path.endswith(".exe"), "explicit image identity required")
        _digest(self.image_sha256)


@dataclass(frozen=True)
class LoaderAuthority:
    """Caller-owned epoch/generations, never recovered from a report.

    Genuine native issuance is a future producer capability. These fields only
    constrain supplied raw observations; they do not establish that capability.
    """
    run_id: str
    profile: str
    resolution: str
    stage: str
    recipe_revision: str
    candidate_sha256: str
    probe_sha256: str
    source_closure_sha256: str
    controller: Generation
    debugger: Generation
    target: Generation
    clock_epoch: str
    clock_origin_ns: int
    checkpoint_id: str
    checkpoint_start_ns: int
    image_base: int
    peb_address: int
    primary_tid: int
    engine_pid: int
    engine_tid: int

    def __post_init__(self):
        for value in (self.run_id, self.clock_epoch, self.checkpoint_id): _token(value)
        for value in (self.candidate_sha256, self.probe_sha256, self.source_closure_sha256): _digest(value)
        for value in (self.profile, self.resolution, self.stage, self.recipe_revision):
            _require(type(value) is str and 0 < len(value) <= 512 and not any(c in value for c in "\0\r\n"), "invalid exact recipe identity")
        _require(all(type(value) is Generation for value in (self.controller, self.debugger, self.target)), "typed retained generations required")
        _require(len({self.controller.pid, self.debugger.pid, self.target.pid}) == 3
                 and self.controller.creation_filetime <= self.debugger.creation_filetime <= self.target.creation_filetime,
                 "aliased/reused parent generations")
        _require(self.target.image_sha256 == self.candidate_sha256, "target file authority differs")
        _int(self.clock_origin_ns, (1 << 63) - MAX_HOLD_NS, "invalid independent clock origin", 1)
        _int(self.checkpoint_start_ns, (1 << 63) - MAX_HOLD_NS, "invalid held checkpoint origin", self.clock_origin_ns)
        _int(self.image_base, USER_LIMIT, "invalid actual x86 image base", 0x10000)
        _require(self.image_base % 0x10000 == 0, "unaligned actual loader base")
        _int(self.peb_address, USER_LIMIT - 12, "invalid native PEB pointer", 0x10000)
        _require(self.peb_address % 4 == 0, "unaligned native PEB pointer")
        _int(self.primary_tid, 0xffffffff, "invalid retained primary TID", 1)
        _int(self.engine_pid, 0xffffffff, "invalid selected engine process")
        _int(self.engine_tid, 0xffffffff, "invalid selected engine thread")


@dataclass(frozen=True)
class NativeQuery:
    name: str
    hresult: int
    value: int

    def __post_init__(self):
        _require(type(self.name) is str and self.name in PHASE_QUERY_NAMES, "source-owned native phase query required")
        _hresult(self.hresult)
        _int(self.value, 0xffffffff, "original native query DWORD required")


@dataclass(frozen=True)
class HeldPhase:
    run_id: str
    clock_epoch: str
    checkpoint_id: str
    controller: Generation
    debugger: Generation
    target: Generation
    system_pid: int
    system_tid: int
    engine_pid: int
    engine_tid: int
    image_base: int
    execution_status: int
    pointer64_hresult: int
    probe_sequence: int
    breakpoint_sequence: int
    monotonic_ns: int
    native_queries: tuple[NativeQuery, ...]

    def __post_init__(self):
        for value in (self.run_id, self.clock_epoch, self.checkpoint_id): _token(value)
        _require(all(type(value) is Generation for value in (self.controller, self.debugger, self.target)), "typed held generations required")
        for name in ("system_pid", "system_tid", "engine_pid", "engine_tid", "image_base", "execution_status",
                     "probe_sequence", "breakpoint_sequence"):
            _int(getattr(self, name), 0xffffffff, "invalid native phase field: " + name)
        _hresult(self.pointer64_hresult)
        _int(self.monotonic_ns, (1 << 63) - 1, "invalid held-phase clock", 1)
        _require(type(self.native_queries) is tuple and len(self.native_queries) <= len(PHASE_QUERY_NAMES)
                 and all(type(row) is NativeQuery for row in self.native_queries), "bounded original typed query tuple required")


@dataclass(frozen=True)
class RawRead:
    ordinal: int
    address: int
    requested_bytes: int
    returned_bytes: int
    hresult: int
    raw: bytes
    begin_ns: int
    end_ns: int
    phase_before: HeldPhase
    phase_after: HeldPhase

    def __post_init__(self):
        _int(self.ordinal, MAX_READS - 1, "invalid raw read ordinal")
        _int(self.address, 0xffffffff, "invalid native read pointer")
        _int(self.requested_bytes, CHUNK_BYTES + 3, "invalid bounded native request")
        _int(self.returned_bytes, 0xffffffff, "invalid original native count")
        _hresult(self.hresult)
        _require(type(self.raw) is bytes and len(self.raw) <= CHUNK_BYTES + 3, "bounded original raw bytes required")
        _int(self.begin_ns, (1 << 63) - 1, "invalid original begin timestamp", 1)
        _int(self.end_ns, (1 << 63) - 1, "invalid original end timestamp", 1)
        _require(type(self.phase_before) is type(self.phase_after) is HeldPhase, "typed native phase receipts required")


@dataclass(frozen=True)
class LoadedImageContract:
    candidate: bytes
    typed_metadata_json: str
    canonical_probe: bytes
    plan_json: str

    def __post_init__(self):
        _require(type(self.candidate) is bytes and 0 < len(self.candidate) <= MAX_IMAGE_BYTES, "bounded candidate bytes required")
        _require(type(self.canonical_probe) is bytes and 0 < len(self.canonical_probe) <= MAX_IMAGE_BYTES, "canonical probe bytes required")
        _json(self.typed_metadata_json); _json(self.plan_json)

    def plan(self):
        return _json(self.plan_json)


@dataclass(frozen=True)
class LoadedImageResult:
    report_json: str
    original_reads: tuple

    def report(self):
        return _json(self.report_json)


def _clone(cls, value):
    # Private recompilation creates fresh class identities. Accept only exact
    # typed record shapes; JSON mappings and report objects are never authority.
    _require(is_dataclass(value) and not isinstance(value, type) and type(value).__name__ == cls.__name__
             and {row.name for row in fields(value)} == {row.name for row in fields(cls)}, "typed original record required: " + cls.__name__)
    data = {row.name: getattr(value, row.name) for row in fields(cls)}
    if cls in (LoaderAuthority, HeldPhase):
        for name in ("controller", "debugger", "target"): data[name] = _clone(Generation, data[name])
    if cls is HeldPhase:
        _require(type(data["native_queries"]) is tuple, "original typed native query tuple required")
        data["native_queries"] = tuple(_clone(NativeQuery, row) for row in data["native_queries"])
    if cls is RawRead:
        for name in ("phase_before", "phase_after"): data[name] = _clone(HeldPhase, data[name])
    return cls(**data)


def _read_source(name, digest=None):
    path = ROOT / name
    _require(path.resolve(strict=True) == path and path.is_relative_to(ROOT), "noncanonical source location")
    for entry in (path, *path.parents):
        _require(not entry.is_symlink() and not getattr(entry, "is_junction", lambda: False)()
                 and not getattr(entry.stat(), "st_file_attributes", 0) & 0x400, "reparsed source path")
    before = path.stat(); data = path.read_bytes(); after = path.stat()
    stamp = lambda row: (row.st_dev, row.st_ino, row.st_size, row.st_mtime_ns)
    _require(stamp(before) == stamp(after) and (digest is None or _sha(data) == digest), "source pin/identity changed: " + name)
    return data, stamp(after)


def _snapshot():
    _require(Path(__file__).resolve() == ROOT / SOURCE, "oracle loaded from another checkout")
    return {name: _read_source(name, digest) for name, digest in dict(PINNED, **{SOURCE: None}).items()}


def _unchanged(snapshot):
    _require(_snapshot() == snapshot, "oracle/context/PE source changed during operation")


@contextmanager
def _modules(snapshot):
    prefix = "_clash95_loaded_image_" + uuid.uuid4().hex
    saved_path = list(sys.path)
    try:
        for suffix in ("", ".tools", ".src", ".src.patcher"):
            module = types.ModuleType(prefix + suffix); module.__path__ = []
            sys.modules[module.__name__] = module
            if suffix:
                parent, _, leaf = module.__name__.rpartition(".")
                setattr(sys.modules[parent], leaf, module)
        result = {}
        for name in (PE, CONTEXT, SOURCE):
            full = prefix + "." + name.removesuffix(".py").replace("/", ".")
            module = types.ModuleType(full)
            module.__file__, module.__package__ = str(ROOT / name), full.rpartition(".")[0]
            module.__loaded_source_sha256__ = _sha(snapshot[name][0])
            sys.modules[full] = module
            setattr(sys.modules[module.__package__], full.rpartition(".")[2], module)
            exec(compile(snapshot[name][0], module.__file__, "exec"), module.__dict__)
            result[name] = module
        yield result
    finally:
        for name in list(sys.modules):
            if name == prefix or name.startswith(prefix + "."): del sys.modules[name]
        sys.path[:] = saved_path


def _derive_plan(candidate, pe):
    """Pure synthetic seam; public production calls independently authenticate."""
    _require(type(candidate) is bytes and 0 < len(candidate) <= MAX_IMAGE_BYTES, "bounded PE32 candidate required")
    image = pe.inspect_pe(candidate)
    _require(image.image_size <= MAX_IMAGE_BYTES, "mapped image extent exceeds source-owned bound")
    relocation_raw, relocation_fields = pe._old_relocations(candidate, image)
    fields_sorted = sorted(relocation_fields)
    image_base_field = image.optional_offset + 28
    _require(not any(at < image_base_field + 4 and image_base_field < at + 4 for at in fields_sorted),
             "HIGHLOW overlaps strict canonical header ImageBase policy")
    ranges = [dict(kind="headers", rva=0, size=image.headers_size, file_offset=0, section=None)]
    nonexecutables = []
    for index, section in enumerate(image.sections):
        if section.characteristics & 0x20000000:
            _require(not section.characteristics & 0x80000000, "writable executable section unsupported")
            _require(section.raw_offset and section.raw_size, "unbacked executable section unsupported")
            ranges.append(dict(kind="executable_raw", rva=section.rva, size=section.raw_size,
                               file_offset=section.raw_offset, section=index))
            if section.memory_size > section.raw_size:
                ranges.append(dict(kind="executable_zero_tail", rva=section.rva + section.raw_size,
                                   size=section.memory_size - section.raw_size, file_offset=None, section=index))
        else:
            nonexecutables.append(dict(rva=section.rva, size=section.memory_size, section=index))
    _require(len(ranges) > 1 and sum(row["size"] for row in ranges) + 4 <= MAX_READ_TOTAL, "executable/header scope is empty or exceeds read allowance")
    selected = []
    for at in fields_sorted:
        matches = [row for row in ranges if row["rva"] <= at < row["rva"] + row["size"]]
        if matches:
            _require(len(matches) == 1 and at + 4 <= matches[0]["rva"] + matches[0]["size"]
                     and matches[0]["file_offset"] is not None, "HIGHLOW crosses or lacks a complete checked backing")
            selected.append(at)
    chunks = []
    for range_index, row in enumerate(ranges):
        at, end = row["rva"], row["rva"] + row["size"]
        while at < end:
            stop = min(at + CHUNK_BYTES, end)
            for relocation in selected:
                if relocation < stop < relocation + 4: stop = relocation + 4
            _require(stop <= end and stop - at <= CHUNK_BYTES + 3, "relocation-safe chunk exceeds fixed bound")
            chunks.append(dict(range_index=range_index, rva=at, size=stop - at,
                               file_offset=None if row["file_offset"] is None else row["file_offset"] + at - row["rva"]))
            at = stop
    _require(len(chunks) + 1 <= MAX_READS, "fixed raw read inventory exceeds bound")
    gaps, cursor = [], 0
    for row in sorted(ranges, key=lambda value: value["rva"]):
        if row["rva"] > cursor: gaps.append(dict(rva=cursor, size=row["rva"] - cursor))
        cursor = max(cursor, row["rva"] + row["size"])
    if cursor < image.image_size: gaps.append(dict(rva=cursor, size=image.image_size - cursor))
    return dict(preferred_base=image.image_base, image_size=image.image_size, headers_size=image.headers_size,
                header_imagebase_offset=image_base_field, header_imagebase_policy=HEADER_POLICY,
                ranges=ranges, chunks=chunks, selected_highlow_rvas=selected,
                all_highlow_rvas=fields_sorted, relocation_directory_sha256=_sha(relocation_raw),
                excluded_nonexecutable_sections=nonexecutables, excluded_unchecked_image_intervals=gaps,
                checked_bytes=sum(row["size"] for row in ranges), required_read_count=len(chunks) + 1,
                native_read_method="IDebugDataSpaces.ReadVirtual",
                hresult_wire_policy="original_signed32_or_unsigned32_integer_unchanged; read/query_S_OK_0; pointer64_S_FALSE_1_only",
                phase_queries=list(PHASE_QUERY_NAMES), phase_query_hresult_policy="each_original_S_OK_required_in_fixed_order",
                boundary="initial_loader_held_before_probe_and_code_breakpoints",
                canonical_probe_rebase_policy="preferred_only_probe_not_executed_or_rewritten",
                zero_tail_policy="strict_zero_at_initial_loader_checkpoint_native_behavior_unverified")


def _make_contract(candidate, metadata_tree, probe, profile, resolution, stage, revision, source_hashes, pe):
    plan = dict(schema=SCHEMA, profile=profile, resolution=resolution, stage=stage, recipe_revision=revision,
                candidate_sha256=_sha(candidate), canonical_probe_sha256=_sha(probe), source_hashes=source_hashes,
                source_closure_sha256=_sha(_canonical(source_hashes).encode("ascii")),
                immutable_scope=_derive_plan(candidate, pe), claims=dict(FALSE_CLAIMS))
    return LoadedImageContract(candidate, metadata_tree, probe, _canonical(plan))


def _prepare_authenticated(original, profile, resolution, candidate, metadata, canonical_probe, *, modules, snapshot):
    _require(globals().get("__loaded_source_sha256__") == _sha(snapshot[SOURCE][0]), "private canonical oracle producer required")
    _require(type(canonical_probe) is bytes, "original canonical probe bytes required")
    context = modules[CONTEXT]
    parent = context.authenticate_parent(original, candidate, metadata, canonical_probe.decode("utf-8"),
                                         profile=profile, resolution=resolution)
    sources, stamps = context._source_snapshot(profile)
    context._unchanged(sources, stamps)
    allocation = parent.allocation_plan()
    closure = {name: _sha(data) for name, data in sources.items()} | {name: _sha(data) for name, (data, _) in snapshot.items()}
    contract = _make_contract(parent.candidate, parent.parent_metadata_json, parent.canonical_probe.encode("utf-8"),
                              profile, resolution, allocation["parent_stage"], allocation["parent_revision"], closure, modules[PE])
    context._unchanged(sources, stamps); _unchanged(snapshot)
    return contract, sources, stamps


def _phase(authority, monotonic_ns):
    return HeldPhase(authority.run_id, authority.clock_epoch, authority.checkpoint_id,
                     authority.controller, authority.debugger, authority.target, authority.target.pid,
                     authority.primary_tid, authority.engine_pid, authority.engine_tid, authority.image_base,
                     6, 1, 0, 0, monotonic_ns,
                     tuple(NativeQuery(name, 0, value) for name, value in zip(PHASE_QUERY_NAMES,
                         (6, authority.target.pid, authority.primary_tid, authority.engine_pid, authority.engine_tid))))


def _checked_plan(contract):
    plan = _json(contract.plan_json)
    _require(type(plan) is dict and set(plan) == {"schema", "profile", "resolution", "stage", "recipe_revision",
             "candidate_sha256", "canonical_probe_sha256", "source_hashes", "source_closure_sha256", "immutable_scope", "claims"},
             "exact source-owned contract fields required")
    _require(plan["schema"] == SCHEMA and _canonical(plan["claims"]) == _canonical(FALSE_CLAIMS),
             "source-owned schema/false evidence claims changed")
    _require(plan["candidate_sha256"] == _sha(contract.candidate)
             and plan["canonical_probe_sha256"] == _sha(contract.canonical_probe), "original candidate/probe contract bytes changed")
    _require(type(plan["source_hashes"]) is dict and all(type(name) is str for name in plan["source_hashes"]),
             "source closure must retain exact canonical paths")
    for digest in plan["source_hashes"].values(): _digest(digest)
    _require(plan["source_closure_sha256"] == _sha(_canonical(plan["source_hashes"]).encode("ascii")),
             "source closure digest differs from its full typed inventory")
    return plan


def _expected_chunks(contract, authority, pe):
    plan = _checked_plan(contract)
    scope = _derive_plan(contract.candidate, pe)
    _require(_canonical(scope) == _canonical(plan["immutable_scope"]), "caller range/exemption/relocation plan differs")
    _require(authority.image_base + scope["image_size"] <= USER_LIMIT, "loaded image overflows bounded x86 user extent")
    _require(authority.peb_address + 12 <= authority.image_base
             or authority.peb_address >= authority.image_base + scope["image_size"], "PEB aliases candidate image")
    expected = [(authority.peb_address + 8, struct.pack("<I", authority.image_base))]
    for row in scope["chunks"]:
        data = bytearray(row["size"] if row["file_offset"] is None else contract.candidate[row["file_offset"]:row["file_offset"] + row["size"]])
        for relocation in scope["selected_highlow_rvas"]:
            if row["rva"] <= relocation < row["rva"] + row["size"]:
                offset = relocation - row["rva"]
                _require(offset + 4 <= len(data), "HIGHLOW split across raw read chunks")
                old = struct.unpack_from("<I", data, offset)[0]
                struct.pack_into("<I", data, offset, (old + authority.image_base - scope["preferred_base"]) & 0xffffffff)
        expected.append((authority.image_base + row["rva"], bytes(data)))
    return expected


def _compare(contract, authority, reads, pe):
    """Private pure fixture seam; no public caller-provided authority bypass."""
    errors, observations = [], []
    try:
        contract = _clone(LoadedImageContract, contract); authority = _clone(LoaderAuthority, authority)
        _require(type(reads) is tuple and len(reads) <= MAX_READS, "bounded original read tuple required")
        cloned = tuple(_clone(RawRead, row) for row in reads)
        plan = _checked_plan(contract)
        _require((authority.profile, authority.resolution, authority.stage, authority.recipe_revision,
                  authority.candidate_sha256, authority.probe_sha256, authority.source_closure_sha256) ==
                 (plan["profile"], plan["resolution"], plan["stage"], plan["recipe_revision"],
                  _sha(contract.candidate), _sha(contract.canonical_probe), plan["source_closure_sha256"]),
                 "independent run/source/candidate/probe/recipe authority differs")
        expected = _expected_chunks(contract, authority, pe)
        _require(len(cloned) == len(expected), "every complete source-owned raw chunk is required")
        previous = authority.checkpoint_start_ns
        for ordinal, (row, (address, data)) in enumerate(zip(cloned, expected)):
            failures = []
            if row.ordinal != ordinal or row.address != address or row.requested_bytes != len(data):
                failures.append("raw chunk omitted, duplicated, reordered or substituted")
            if row.hresult != 0 or row.returned_bytes != len(data) or len(row.raw) != len(data):
                failures.append("native read failed, shortened or returned an incompatible original count")
            if row.raw != data:
                failures.append("complete original bytes differ from source-owned loader expectation")
            for observed in (row.phase_before, row.phase_after):
                if asdict(observed) != asdict(_phase(authority, observed.monotonic_ns)):
                    failures.append("held loader phase/generation/selection/architecture changed or probe/breakpoint already armed")
            if not (previous <= row.phase_before.monotonic_ns <= row.begin_ns <= row.end_ns <= row.phase_after.monotonic_ns
                    <= authority.checkpoint_start_ns + MAX_HOLD_NS):
                failures.append("raw read leaves the independently bound held epoch or clock order")
            previous = row.phase_after.monotonic_ns
            observations.append(dict(ordinal=row.ordinal, address=row.address, requested_bytes=row.requested_bytes,
                                     returned_bytes=row.returned_bytes, hresult=row.hresult, raw_bytes=len(row.raw),
                                     raw_sha256=_sha(row.raw), failures=failures,
                                     phase_before_queries=[asdict(query) for query in row.phase_before.native_queries],
                                     phase_after_queries=[asdict(query) for query in row.phase_after.native_queries],
                                     phase_before_pointer64_hresult=row.phase_before.pointer64_hresult,
                                     phase_after_pointer64_hresult=row.phase_after.pointer64_hresult))
            errors.extend(f"read {ordinal}: {failure}" for failure in failures)
    except Exception as exc:
        errors.append((type(exc).__name__ + ": " + str(exc))[:4096])
    return LoadedImageResult(_canonical(dict(schema=SCHEMA, **FALSE_CLAIMS, source_comparison_passed=not errors,
        failures=errors, observations=observations,
        scope="Canonical headers plus all executable raw/zero extents only; nonexecutable sections/alignment excluded; native issuance and loader behavior unverified.",
        unverified_gaps=["readonly constants", "runtime RW/IAT/provider state", "native collector/read-lease issuance",
                         "independent native PEB pointer query issuance",
                         "actual loader header/zero-tail behavior", "preferred/nonpreferred probe execution"])), reads)


def prepare_contract(original: bytes, profile: str, resolution: str, *, candidate: bytes, metadata: dict,
                     canonical_probe: bytes) -> LoadedImageContract:
    """No manifest-selected recipe/ranges; privately authenticate actual parent."""
    snapshot = _snapshot()
    with _modules(snapshot) as modules:
        result, _, _ = modules[SOURCE]._prepare_authenticated(original, profile, resolution, candidate, metadata,
                                                              canonical_probe, modules=modules, snapshot=snapshot)
    _unchanged(snapshot)
    return result


def replay_loaded_image(original: bytes, contract, authority, reads: tuple) -> LoadedImageResult:
    """Reauthenticate source and exact bundle before and after original replay."""
    try:
        snapshot = _snapshot()
        with _modules(snapshot) as modules:
            producer, context = modules[SOURCE], modules[CONTEXT]
            copied = producer._clone(producer.LoadedImageContract, contract)
            metadata = context._restore_metadata(producer._json(copied.typed_metadata_json))
            plan = producer._checked_plan(copied)
            rebuilt, sources, stamps = producer._prepare_authenticated(original, plan["profile"], plan["resolution"],
                copied.candidate, metadata, copied.canonical_probe, modules=modules, snapshot=snapshot)
            producer._require(rebuilt.plan_json == copied.plan_json, "supplied contract source/ranges/exemptions differ")
            context._unchanged(sources, stamps)
            result = producer._compare(rebuilt, authority, reads, modules[PE])
            context._unchanged(sources, stamps)
        _unchanged(snapshot)
        return result
    except Exception as exc:
        return LoadedImageResult(_canonical(dict(schema=SCHEMA, **FALSE_CLAIMS, source_comparison_passed=False,
            failures=[(type(exc).__name__ + ": " + str(exc))[:4096]], observations=[])), reads)
