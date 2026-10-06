"""Source-only canonical expected-byte payloads for a future loader batch.

Private admission reconstructs the exact frozen four-profile parent. A payload
hash or decoder result is never authority. Models cover canonical headers and
executable raw/zero extents only; PEB4 remains a separate mandatory native read.
No native comparison, storage adapter, launch or acceptance is installed.
"""
from __future__ import annotations

import ast
from dataclasses import asdict, dataclass, fields, is_dataclass
import hashlib
import json
from pathlib import Path
import struct
import sys
import types
import uuid
import weakref

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "tools/hidden_soak_loader_expected.py"
ORACLE = "tools/hidden_soak_loaded_image.py"
ORACLE_SHA256 = "5c59a3498f0f5a03967e2375ca92defd05883cb918bffa353b387acce129251e"
SCHEMA = "hidden_soak_loader_expected_v1"
MAGIC = b"CLHDLE1\0"
PREFIX = struct.Struct("<8s10I")
DESCRIPTOR = struct.Struct("<8I")
MAX_METADATA, MAX_CHUNKS, MAX_FIXUPS = 65536, 511, 65536
MAX_RAW, MAX_CHUNK, MAX_IMAGE = 16 * 1024**2 - 4, 65539, 64 * 1024**2
MAX_PAYLOAD = PREFIX.size + MAX_METADATA + MAX_CHUNKS * DESCRIPTOR.size + MAX_FIXUPS * 4 + MAX_RAW + 32
USER_LIMIT = 0x7ffe0000
FALSE_CLAIMS = {name: False for name in (
    "passed", "native_producer_provenance_verified", "native_read_coherence_verified",
    "native_generation_ownership_verified", "native_job_cleanup_verified", "host_cleanup_complete",
    "canonical_comparison_during_native_hold", "loaded_candidate_verified", "whole_image_verified",
    "loaded_probe_verified", "probe_executed", "running_duration_verified", "runtime_acceptance",
    "release_acceptance", "manual_input_verified", "promotion_ready", "stable")}
FACT_FIELDS = frozenset(("schema", "profile", "resolution", "stage", "recipe_revision", "candidate_sha256",
    "probe_sha256", "typed_metadata_sha256", "source_hashes", "source_closure_sha256", "issuer_source_sha256",
    "oracle_source_sha256", "contract_sha256", "immutable_scope_sha256", "preferred_base", "image_size",
    "headers_size", "header_imagebase_offset", "header_imagebase_policy", "all_highlow_count", "all_highlow_rvas_sha256",
    "selected_highlow_rvas_sha256", "relocation_directory_sha256", "excluded_nonexecutable_sections",
    "excluded_unchecked_image_intervals", "checked_bytes", "required_read_count", "expected_raw_sha256",
    "mandatory_extra_read", "scope", "unverified_gaps", "claims", "authority"))


def _require(value, label):
    if not value: raise ValueError(label)


def _int(value, maximum, label, minimum=0):
    _require(type(value) is int and minimum <= value <= maximum, label)


def _sha(raw):
    _require(type(raw) is bytes, "unchanged byte string required")
    return hashlib.sha256(raw).hexdigest()


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")


def _object(pairs):
    result = {}
    for key, value in pairs:
        _require(key not in result, "duplicate metadata field")
        result[key] = value
    return result


def _json(raw):
    value = json.loads(raw, object_pairs_hook=_object,
        parse_constant=lambda token: (_ for _ in ()).throw(ValueError("nonfinite metadata")))
    _require(_canonical(value) == raw, "exact canonical ASCII metadata required")
    return value


def retention_budget():
    """Exact wire maxima; no storage, reserve bypass or complete-host budget."""
    journal = 16 * 1024**2 + 65539 + 2 * 9 * 1024**2
    archive = 16 * 1024**2 + 65539 + 9 * 1024**2
    return dict(prefix_bytes=PREFIX.size, metadata_bytes=MAX_METADATA,
        chunk_descriptor_bytes=MAX_CHUNKS * DESCRIPTOR.size, highlow_bytes=MAX_FIXUPS * 4,
        expected_raw_bytes=MAX_RAW, trailer_bytes=32, alignment_bytes=0,
        maximum_payload_bytes=MAX_PAYLOAD, payload_atomic_temporary_bytes=MAX_PAYLOAD,
        additional_payload_peak_bytes=2 * MAX_PAYLOAD, existing_native_journal_peak_bytes=journal,
        separate_complete_native_archive_copy_bytes=archive,
        combined_known_peak_bytes=2 * MAX_PAYLOAD + journal + archive,
        exclusions=["candidate/assets/compiler output", "original/candidate/source/expected-model RAM",
                    "generation/job/clock receipts and additional exports", "unavailable native output debt"],
        scope="known payload and original archive allowances only; no filesystem/native adapter or reserve bypass")


@dataclass(frozen=True)
class PayloadAuthority:
    """Caller-owned source binding only; these scalars prove no native epoch."""
    run_id: str
    checkpoint_id: str
    epoch_id: str
    controller_pid: int
    frequency_hz: int
    origin_tick: int
    origin_ns: int

    def __post_init__(self):
        for token in (self.run_id, self.checkpoint_id, self.epoch_id):
            _require(type(token) is str and uuid.UUID(token).hex == token, "canonical caller-owned token required")
        for value, maximum, label in ((self.controller_pid, 0xffffffff, "controller PID"),
                (self.frequency_hz, 10**9, "QPC frequency"), (self.origin_tick, (1 << 63) - 1, "QPC origin"),
                (self.origin_ns, (1 << 63) - 20 * 10**9, "time origin")):
            _int(value, maximum, "bounded original " + label + " required", 1)


@dataclass(frozen=True, eq=False, slots=True, weakref_slot=True)
class ExpectedReadPlan:
    binding_json: str


@dataclass(frozen=True, eq=False, slots=True, weakref_slot=True)
class ExpectedPayload:
    binding_json: str


@dataclass(frozen=True)
class PayloadFacts:
    metadata_json: str
    payload_bytes: bytes
    descriptors: tuple
    selected_highlow_rvas: tuple
    check_sources: object


@dataclass(frozen=True)
class PayloadResult:
    report_json: str
    original_payload: object
    modeled_chunks: tuple = ()

    def report(self):
        return json.loads(self.report_json)


def _authority(original):
    _require(is_dataclass(original) and not isinstance(original, type)
             and type(original).__name__ == "PayloadAuthority"
             and {row.name for row in fields(original)} == {row.name for row in fields(PayloadAuthority)},
             "typed caller-owned PayloadAuthority required")
    return PayloadAuthority(**{row.name: getattr(original, row.name) for row in fields(PayloadAuthority)})


def _build_state(contract, *, oracle, pe, issuer_sha256, check_sources):
    """Pure synthetic fixture seam; production reaches this after fresh admission."""
    check_sources()
    plan = oracle._checked_plan(contract)
    scope = oracle._derive_plan(contract.candidate, pe)
    _require(oracle._canonical(scope) == oracle._canonical(plan["immutable_scope"]), "caller immutable scope differs")
    selected = tuple(scope["selected_highlow_rvas"])
    _require(len(selected) <= MAX_FIXUPS, "complete selected HIGHLOW inventory exceeds source cap")
    chunks, raw, owned_fixups = [], bytearray(), set()
    kinds = {"headers": 0, "executable_raw": 1, "executable_zero_tail": 2}
    for ordinal, chunk in enumerate(scope["chunks"]):
        indices = [index for index, rva in enumerate(selected) if chunk["rva"] <= rva < chunk["rva"] + chunk["size"]]
        _require(not indices or indices == list(range(indices[0], indices[0] + len(indices))), "noncontiguous selected fixup slice")
        for index in indices:
            _require(index not in owned_fixups and selected[index] + 4 <= chunk["rva"] + chunk["size"], "split or aliased HIGHLOW")
            owned_fixups.add(index)
        kind = kinds[scope["ranges"][chunk["range_index"]]["kind"]]
        data = bytes(chunk["size"]) if chunk["file_offset"] is None else contract.candidate[chunk["file_offset"]:chunk["file_offset"] + chunk["size"]]
        _require(len(data) == chunk["size"], "complete canonical chunk backing required")
        chunks.append((ordinal, chunk["rva"], chunk["size"], len(raw), indices[0] if indices else 0,
                       len(indices), chunk["range_index"], kind))
        raw.extend(data)
    _require(len(chunks) <= MAX_CHUNKS and len(raw) <= MAX_RAW and owned_fixups == set(range(len(selected))),
             "complete source-owned payload inventory exceeds cap or omits fixups")
    _require(len(raw) == scope["checked_bytes"], "canonical raw byte count differs")
    facts = dict(schema=SCHEMA, profile=plan["profile"], resolution=plan["resolution"], stage=plan["stage"],
        recipe_revision=plan["recipe_revision"], candidate_sha256=plan["candidate_sha256"],
        probe_sha256=plan["canonical_probe_sha256"], typed_metadata_sha256=_sha(contract.typed_metadata_json.encode("ascii")),
        source_hashes=plan["source_hashes"], source_closure_sha256=plan["source_closure_sha256"],
        issuer_source_sha256=issuer_sha256, oracle_source_sha256=ORACLE_SHA256,
        contract_sha256=_sha(contract.plan_json.encode("ascii")), immutable_scope_sha256=_sha(oracle._canonical(scope).encode("ascii")),
        preferred_base=scope["preferred_base"], image_size=scope["image_size"], headers_size=scope["headers_size"],
        header_imagebase_offset=scope["header_imagebase_offset"], header_imagebase_policy=scope["header_imagebase_policy"],
        all_highlow_count=len(scope["all_highlow_rvas"]), all_highlow_rvas_sha256=_sha(_canonical(scope["all_highlow_rvas"])),
        selected_highlow_rvas_sha256=_sha(_canonical(list(selected))), relocation_directory_sha256=scope["relocation_directory_sha256"],
        excluded_nonexecutable_sections=scope["excluded_nonexecutable_sections"],
        excluded_unchecked_image_intervals=scope["excluded_unchecked_image_intervals"],
        checked_bytes=len(raw), required_read_count=len(chunks) + 1, expected_raw_sha256=_sha(bytes(raw)),
        mandatory_extra_read="original PEB.ImageBaseAddress4 bytes; runtime pointer and actual base remain external",
        scope="canonical headers and executable raw/zero extents only; nonexecutable data and alignment excluded",
        unverified_gaps=["native loader/header behavior", "readonly/RW/IAT/provider contents", "loaded host/source provenance",
                         "live target/host generations", "no-breakaway job and complete cleanup", "durable storage and actual reserve"],
        claims=dict(FALSE_CLAIMS))
    check_sources()
    return _canonical(facts), tuple(chunks), selected, bytes(raw), check_sources


def _encode(state, authority):
    facts_raw, chunks, fixups, raw, check = state
    check(); owned = _authority(authority)
    metadata = _canonical(dict(_json(facts_raw), authority=asdict(owned)))
    _require(len(metadata) <= MAX_METADATA, "complete metadata exceeds source cap")
    facts = _json(facts_raw)
    prefix = PREFIX.pack(MAGIC, 1, len(metadata), len(chunks), len(fixups), len(raw), facts["preferred_base"],
                         facts["image_size"], facts["headers_size"], facts["header_imagebase_offset"], 0)
    body = prefix + metadata + b"".join(DESCRIPTOR.pack(*row) for row in chunks)
    body += b"".join(struct.pack("<I", rva) for rva in fixups) + raw
    payload = body + hashlib.sha256(body).digest()
    _require(len(payload) <= MAX_PAYLOAD, "complete payload exceeds source cap")
    check(); return metadata, payload


def _decode(payload):
    """Bounded structural diagnostics only; this cannot authenticate a payload."""
    _require(type(payload) is bytes and PREFIX.size + 32 <= len(payload) <= MAX_PAYLOAD, "original payload size/type exceeds fixed cap")
    magic, version, meta_size, count, fixup_count, raw_size, preferred, image_size, headers_size, base_field, flags = PREFIX.unpack_from(payload)
    _require(magic == MAGIC and version == 1 and flags == 0, "unsupported payload prefix")
    _require(0 < meta_size <= MAX_METADATA and 0 < count <= MAX_CHUNKS and fixup_count <= MAX_FIXUPS
             and 0 < raw_size <= MAX_RAW and 0 < image_size <= MAX_IMAGE, "payload inventory exceeds fixed cap")
    expected_size = PREFIX.size + meta_size + count * DESCRIPTOR.size + fixup_count * 4 + raw_size + 32
    _require(len(payload) == expected_size and hashlib.sha256(payload[:-32]).digest() == payload[-32:], "complete EOF/trailer differs")
    offset = PREFIX.size; metadata = _json(payload[offset:offset + meta_size]); offset += meta_size
    _require(type(metadata) is dict and set(metadata) == FACT_FIELDS and metadata["schema"] == SCHEMA
             and _canonical(metadata["claims"]) == _canonical(FALSE_CLAIMS),
             "source scope or false claims differ")
    _require(_canonical(asdict(PayloadAuthority(**metadata["authority"]))) == _canonical(metadata["authority"]), "authority type/value differs")
    for name, value in (("preferred_base", preferred), ("image_size", image_size), ("headers_size", headers_size),
                        ("header_imagebase_offset", base_field), ("checked_bytes", raw_size), ("required_read_count", count + 1)):
        _require(type(metadata[name]) is int and metadata[name] == value, "wire/metadata scalar differs: " + name)
    _require(metadata["header_imagebase_policy"] == "canonical_preferred_ImageBase_DWORD_unchanged_native_behavior_unverified",
             "strict unchanged header ImageBase policy required")
    _require(preferred >= 0x10000 and preferred % 0x10000 == 0 and preferred + image_size <= USER_LIMIT
             and 0 < headers_size <= raw_size and base_field + 4 <= headers_size, "bounded canonical PE extent required")
    chunks = tuple(DESCRIPTOR.unpack_from(payload, offset + index * DESCRIPTOR.size) for index in range(count)); offset += count * DESCRIPTOR.size
    fixups = tuple(struct.unpack_from("<I", payload, offset + index * 4)[0] for index in range(fixup_count)); offset += fixup_count * 4
    raw = payload[offset:offset + raw_size]
    _require(_sha(raw) == metadata["expected_raw_sha256"] and _sha(_canonical(list(fixups))) == metadata["selected_highlow_rvas_sha256"],
             "complete raw/fixup metadata digests differ")
    _require(all(a + 4 <= b for a, b in zip(fixups, fixups[1:])), "duplicate/overlapping/reordered fixups")
    cursor, owned, intervals, header_total = 0, set(), [], 0
    previous_range, previous_kind, previous_end = 0, 0, 0
    for index, row in enumerate(chunks):
        ordinal, rva, size, raw_offset, first, number, range_index, kind = row
        _require(ordinal == index and 0 < size <= MAX_CHUNK and raw_offset == cursor and rva + size <= image_size,
                 "ordered complete chunk descriptor required")
        _require(kind in (0, 1, 2) and range_index in (previous_range, previous_range + 1), "source range order/type differs")
        if index == 0:
            _require(rva == 0 and range_index == 0 and kind == 0, "complete header chunk must be first")
        elif range_index == previous_range:
            _require(rva == previous_end and kind == previous_kind, "chunk gap or kind change within range")
        else:
            _require(kind != 0 and (kind != 2 or previous_kind == 1 and rva == previous_end), "unsupported raw/zero range transition")
        _require(all(rva + size <= start or rva >= end for start, end in intervals), "overlapping scope chunks")
        intervals.append((rva, rva + size))
        if kind == 0:
            _require(range_index == 0, "header range alias")
            header_total += size
        if kind == 2: _require(not any(raw[raw_offset:raw_offset + size]) and number == 0, "zero tail bytes/fixups differ")
        _require(first + number <= len(fixups) and (number != 0 or first == 0), "invalid exact fixup slice")
        for slot in range(first, first + number):
            at = fixups[slot]
            _require(slot not in owned and rva <= at and at + 4 <= rva + size
                     and (at + 4 <= base_field or at >= base_field + 4), "split/aliased/header ImageBase fixup")
            owned.add(slot)
        cursor += size; previous_range, previous_kind, previous_end = range_index, kind, rva + size
    _require(cursor == len(raw) and header_total == headers_size and owned == set(range(len(fixups))), "scope/raw/fixup omission")
    _require(struct.unpack_from("<I", raw, base_field)[0] == preferred, "canonical header ImageBase changed")
    return metadata, chunks, fixups, raw


def _model(payload, image_base):
    metadata, chunks, fixups, raw = _decode(payload)
    _int(image_base, USER_LIMIT, "bounded modeled x86 base required", 0x10000)
    _require(image_base % 0x10000 == 0 and image_base + metadata["image_size"] <= USER_LIMIT, "modeled load extent overflows")
    result = []
    for _, rva, size, raw_offset, first, number, _, _ in chunks:
        data = bytearray(raw[raw_offset:raw_offset + size])
        for at in fixups[first:first + number]:
            offset = at - rva
            old = struct.unpack_from("<I", data, offset)[0]
            struct.pack_into("<I", data, offset, (old + image_base - metadata["preferred_base"]) & 0xffffffff)
        result.append((image_base + rva, bytes(data)))
    return tuple(result)


def _private_preparation(original, contract, imported_source):
    own_path, oracle_path = ROOT / SOURCE, ROOT / ORACLE
    _require(Path(__file__).resolve() == own_path and own_path.read_bytes() == imported_source, "imported issuer source differs")
    oracle_raw = oracle_path.read_bytes()
    _require(_sha(oracle_raw) == ORACLE_SHA256, "frozen oracle differs")
    prefix = "_clash95_expected_" + uuid.uuid4().hex
    created = {}
    try:
        _require(prefix not in sys.modules, "private issuer namespace collision")
        package = types.ModuleType(prefix); package.__path__ = []; sys.modules[prefix] = package; created[prefix] = package
        modules = {}
        for name, raw, path in (("oracle", oracle_raw, oracle_path), ("issuer", imported_source, own_path)):
            module = types.ModuleType(prefix + "." + name); module.__file__, module.__package__ = str(path), prefix
            _require(module.__name__ not in sys.modules, "private producer namespace collision")
            sys.modules[module.__name__] = module; created[module.__name__] = module
            exec(compile(raw, str(path), "exec"), module.__dict__); modules[name] = module
        oracle, producer = modules["oracle"], modules["issuer"]
        snapshot = oracle._snapshot()
        own_snapshot = oracle._read_source(SOURCE)
        _require(own_snapshot[0] == imported_source and snapshot[ORACLE][0] == oracle_raw, "compiled/source snapshot differs")
        with oracle._modules(snapshot) as canonical:
            fixed, context, pe = canonical[oracle.SOURCE], canonical[oracle.CONTEXT], canonical[oracle.PE]
            copied = fixed._clone(fixed.LoadedImageContract, contract)
            plan = fixed._checked_plan(copied)
            metadata = context._restore_metadata(fixed._json(copied.typed_metadata_json))
            rebuilt, sources, stamps = fixed._prepare_authenticated(original, plan["profile"], plan["resolution"], copied.candidate,
                metadata, copied.canonical_probe, modules=canonical, snapshot=snapshot)
            _require(rebuilt == copied, "fresh canonical candidate/probe/typed contract differs")
            def check():
                context._unchanged(sources, stamps); oracle._unchanged(snapshot)
                _require(oracle._read_source(SOURCE) == own_snapshot, "issuer source changed")
            check()
            state = producer._build_state(rebuilt, oracle=fixed, pe=pe, issuer_sha256=_sha(imported_source), check_sources=check)
            def encode(authority): return producer._encode(state, authority)
            return state[0], state[1], state[2], encode, producer._decode, producer._model, check
    finally:
        for name, module in created.items():
            if sys.modules.get(name) is module: del sys.modules[name]


def _closed_preparation(raw, path):
    """Compile canonical admission definitions without recursive API issuance."""
    tree = ast.parse(raw, filename=str(path))
    names = ("prepare_expected_plan", "issue_expected_payload", "inspect_expected_payload",
             "model_loaded_chunks", "replay_expected_payload")
    terminal = tree.body[-1]
    _require(type(terminal) is ast.Assign and len(terminal.targets) == 1
             and type(terminal.targets[0]) is ast.Tuple
             and tuple(node.id if type(node) is ast.Name else None for node in terminal.targets[0].elts) == names
             and type(terminal.value) is ast.Call and type(terminal.value.func) is ast.Name
             and terminal.value.func.id == "_api_factory" and not terminal.value.args and not terminal.value.keywords,
             "exact terminal API factory assignment required")
    _require(sum(type(node) is ast.Call and type(node.func) is ast.Name and node.func.id == "_api_factory"
                 for node in ast.walk(tree)) == 1, "only the authenticated terminal factory may issue APIs")
    tree.body.pop()  # The sole permitted source transformation.
    name = "_clash95_expected_admission_" + uuid.uuid4().hex
    module = types.ModuleType(name); module.__file__, module.__package__ = str(path), ""
    _require(name not in sys.modules, "private admission namespace collision")
    sys.modules[name] = module
    try:
        exec(compile(tree, str(path), "exec"), module.__dict__)
        return module._private_preparation
    finally:
        if sys.modules.get(name) is module: del sys.modules[name]


def _api_factory(*, _preparation=None):
    # The optional private fixture seam has a distinct registry and can never
    # issue a capability accepted by the production functions below.
    plans, payloads = {}, {}
    own_path, oracle_path, oracle_pin = ROOT / SOURCE, ROOT / ORACLE, ORACLE_SHA256
    imported_source = own_path.read_bytes()
    fixed_hash = hashlib.sha256
    prepare = _closed_preparation(imported_source, own_path) if _preparation is None else _preparation
    canonical, sha, require = _canonical, _sha, _require
    plan_class, payload_class, facts_class, result_class = ExpectedReadPlan, ExpectedPayload, PayloadFacts, PayloadResult
    false_claims, schema = dict(FALSE_CLAIMS), SCHEMA
    def guard_import():
        require(own_path.read_bytes() == imported_source and fixed_hash(oracle_path.read_bytes()).hexdigest() == oracle_pin,
                "imported issuer/frozen oracle source differs")
    def retain(registry, obj, binding, state):
        identity = id(obj)
        def retired(reference):
            if identity in registry and registry[identity][0] is reference: del registry[identity]
        registry[identity] = (weakref.ref(obj, retired), binding, state)
        return obj
    def admitted(registry, cls, obj):
        guard_import()
        entry = registry.get(id(obj))
        require(type(obj) is cls and entry is not None and entry[0]() is obj and obj.binding_json == entry[1],
                "genuine live source-issued opaque identity required")
        entry[2][-1](); return entry[2]
    def prepare_expected_plan(original, contract):
        guard_import()
        state = prepare(original, contract, imported_source)
        binding = canonical(dict(metadata_sha256=sha(state[0]), claims=false_claims)).decode("ascii")
        return retain(plans, plan_class(binding), binding, state)
    def issue_expected_payload(plan, authority):
        state = admitted(plans, plan_class, plan)
        metadata, raw = state[3](authority)
        binding = canonical(dict(metadata_sha256=sha(metadata), payload_sha256=sha(raw), claims=false_claims)).decode("ascii")
        held = (metadata, raw, state[1], state[2], state[4], state[5], state[-1])
        return retain(payloads, payload_class(binding), binding, held)
    def inspect_expected_payload(payload):
        metadata, raw, chunks, fixups, _, _, check = admitted(payloads, payload_class, payload)
        return facts_class(metadata.decode("ascii"), raw, chunks, fixups, check)
    def model_loaded_chunks(payload, image_base):
        metadata, raw, _, _, _, model, check = admitted(payloads, payload_class, payload)
        check(); result = model(raw, image_base); check()
        report = dict(schema=schema, **false_claims, modeled_source_bytes_derived=True,
                      modeled_base=image_base, payload_sha256=sha(raw), metadata_sha256=sha(metadata),
                      mandatory_extra_read="PEB.ImageBaseAddress4 bytes remain independently required", native_base_observed=False)
        return result_class(canonical(report).decode("ascii"), raw, result)
    def replay_expected_payload(original, contract, authority, original_payload, image_base):
        result, failures = (), []
        try:
            # Fresh canonical reconstruction; even a complete resealed payload
            # with matching report hashes cannot replace this byte authority.
            guard_import(); state = prepare(original, contract, imported_source)
            metadata, expected = state[3](authority)
            state[-1](); state[4](original_payload)
            require(original_payload == expected, "fresh canonical expected payload differs")
            result = state[5](original_payload, image_base); state[-1]()
        except Exception as error:
            result = ()  # Nothing derived under a lost source receipt is published.
            failures.append(type(error).__name__ + ": " + str(error))
        report = dict(schema=schema, **false_claims, source_payload_replay_passed=not failures, failures=failures,
            original_payload_bytes=len(original_payload) if type(original_payload) is bytes else None,
            original_payload_sha256=sha(original_payload) if type(original_payload) is bytes else None,
            native_base_observed=False, original_retention="unchanged RAM only; no durable storage adapter")
        return result_class(canonical(report).decode("ascii"), original_payload, result)
    return prepare_expected_plan, issue_expected_payload, inspect_expected_payload, model_loaded_chunks, replay_expected_payload


prepare_expected_plan, issue_expected_payload, inspect_expected_payload, model_loaded_chunks, replay_expected_payload = _api_factory()
