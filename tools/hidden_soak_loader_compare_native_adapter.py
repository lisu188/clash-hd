"""Versioned supplied-receipt replay for an initial-hold byte comparator.

No native calls, storage adapter, launch, evidence lane or promotion is provided.
Original packet/footer bytes remain distinct from their semantic interpretation.
A main-write receipt cannot attest the append/flush of its own trailing footer.
Request issuance and parsing share one privately compiled generator registry.
"""
from __future__ import annotations

import ast
from copy import deepcopy
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
import struct
import sys
import types
import uuid
import weakref

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path(__file__).resolve()
GENERATOR = ROOT / "tools/hidden_soak_loader_compare_native.py"
V1_ADAPTER = ROOT / "tools/hidden_soak_loader_native_adapter.py"
V1_ADAPTER_SHA256 = "3cb68b6bc6b28fcbda2861adc1141c308aefe8c3aa121da0de0f0c23723b18b2"
VALIDATOR_DEPENDENCIES = (
    ("tools/hidden_soak_loaded_image.py", "5c59a3498f0f5a03967e2375ca92defd05883cb918bffa353b387acce129251e"),
    ("tools/hidden_soak_loaded_read_session.py", "8840cb175a6d2f4a965d249d8a739a608155e3df49afb17bf12e08f445c837b7"))
MAGIC = b"CLHDCR2\0"
FRAME = struct.Struct("<II")
IO_FOOTER = struct.Struct("<iIIIiI")
COMPARISON_RECORD = struct.Struct("<10I3q")
MAX_FRAMES = 32768
MAX_FRAME_METADATA, MAX_FRAME_RAW = 512 * 1024, 65539
MAX_TOTAL_METADATA, MAX_FAILURE_METADATA = 13910040, 14958616
MAX_TOTAL_RAW, MAX_FAILURE_RAW = 16809984, 16875523
MAX_ARCHIVE = MAX_FAILURE_METADATA + MAX_FAILURE_RAW
COMPARISON_JSON = 4096
SCOPE = "immutable_scope_initial_hold"
IMMUTABLE_SCOPE = "canonical_headers_executable_raw_and_zero_extents_only"
FALSE_CLAIMS = {name: False for name in (
    "passed", "native_producer_provenance_verified", "native_read_coherence_verified",
    "native_generation_ownership_verified", "native_job_cleanup_verified", "host_cleanup_complete",
    "storage_durability_verified", "receipt_tail_durability_verified", "loaded_candidate_verified",
    "whole_image_verified", "loaded_probe_verified", "probe_executed", "running_duration_verified",
    "runtime_acceptance", "release_acceptance", "manual_input_verified", "promotion_ready", "stable")}
RESULT_FIELDS = ("version", "ordinal", "descriptor_index", "read_frame_sequence", "requested_bytes",
    "returned_bytes", "comparison_status", "mismatch_count", "first_mismatch", "applied_highlow_count",
    "address", "before_tick", "after_tick")
IO_FIELDS = ("write_return", "write_error", "requested", "returned", "flush_return", "flush_error")


def _require(value, message):
    if not value:
        raise ValueError(message)


def _integer(value, minimum, maximum, label):
    _require(type(value) is int and minimum <= value <= maximum, label)


def _sha(raw):
    _require(type(raw) is bytes, "exact original bytes required")
    return hashlib.sha256(raw).hexdigest()


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                      allow_nan=False).encode("ascii")


def _object(pairs):
    result = {}
    for key, value in pairs:
        _require(key not in result, "duplicate JSON field")
        result[key] = value
    return result


def _json(raw):
    value = json.loads(raw.decode("ascii", "strict"), object_pairs_hook=_object,
        parse_constant=lambda token: (_ for _ in ()).throw(ValueError("nonfinite JSON")))
    _require(_canonical(value) == raw, "canonical original ASCII JSON required")
    return value


def _exact(value, fields, label):
    _require(type(value) is dict and set(value) == set(fields), "exact " + label + " fields required")
    return value


@dataclass(frozen=True)
class OriginalFrame:
    sequence: int
    operation: str
    metadata: bytes
    raw: bytes
    footer: bytes
    offset: int

    def data(self):
        return _json(self.metadata)["data"]

    def io(self):
        return dict(zip(IO_FIELDS, IO_FOOTER.unpack(self.footer)))


class ArchiveError(ValueError):
    """Retain the entire original, even when framing or replay fails."""
    def __init__(self, message, original_archive, frames=(), original_observation=None):
        super().__init__(message)
        self.original_archive = original_archive
        self.frames = tuple(frames)
        self.original_observation = original_observation


def parse_frames(original):
    """Bounded structural diagnostics only; no native/source authority issued."""
    frames = []
    offset, metadata_bytes, raw_bytes = len(MAGIC), len(MAGIC), 0
    try:
        _require(type(original) is bytes and len(MAGIC) <= len(original) <= MAX_ARCHIVE,
                 "entire original archive bytes/type exceed fixed cap")
        _require(original[:len(MAGIC)] == MAGIC, "exact V2 archive magic required")
        while offset < len(original):
            start = offset
            _require(len(frames) < MAX_FRAMES and offset + FRAME.size <= len(original),
                     "frame count exceeds cap or original prefix is truncated")
            meta_size, raw_size = FRAME.unpack_from(original, offset)
            _require(0 < meta_size <= MAX_FRAME_METADATA and raw_size <= MAX_FRAME_RAW,
                     "complete original packet exceeds fixed capacity")
            offset += FRAME.size
            end = offset + meta_size + raw_size
            _require(end + IO_FOOTER.size <= len(original), "original metadata/raw/footer is truncated")
            metadata = original[offset:offset + meta_size]
            value = _exact(_json(metadata), ("sequence", "operation", "data"), "frame")
            _integer(value["sequence"], 1, MAX_FRAMES, "bounded original frame sequence required")
            _require(value["sequence"] == len(frames) + 1 and type(value["operation"]) is str
                     and value["operation"] and type(value["data"]) is dict,
                     "ordered original frame sequence/operation/data required")
            raw = original[offset + meta_size:end]
            footer = original[end:end + IO_FOOTER.size]
            row = OriginalFrame(value["sequence"], value["operation"], metadata, raw, footer, start)
            frames.append(row)
            _require(row.operation in ("read_virtual_capacity", "comparison_result", "native_failure") or not raw,
                     "unexpected raw payload operation")
            if row.operation == "comparison_result":
                _require(meta_size <= COMPARISON_JSON and raw_size == COMPARISON_RECORD.size,
                         "exact bounded comparison result packet required")
            if row.operation in ("comparison_begin", "comparison_complete", "comparison_counter"):
                _require(meta_size <= COMPARISON_JSON, "comparison metadata exceeds fixed operation cap")
            offset = end + IO_FOOTER.size
            metadata_bytes += FRAME.size + meta_size + IO_FOOTER.size
            raw_bytes += raw_size
            _require(metadata_bytes <= MAX_FAILURE_METADATA and raw_bytes <= MAX_FAILURE_RAW,
                     "complete retained archive exceeds original failure allowance")
        _require(frames, "required original frames are absent")
        return tuple(frames)
    except Exception as error:
        if isinstance(error, ArchiveError):
            raise
        raise ArchiveError(type(error).__name__ + ": " + str(error), original, frames) from error


def _io(value, requested):
    _exact(value, IO_FIELDS, "original main I/O")
    for name in ("write_return", "flush_return"):
        _integer(value[name], -(1 << 31), (1 << 31) - 1, "original signed native BOOL required")
    for name in ("write_error", "requested", "returned", "flush_error"):
        _integer(value[name], 0, 0xffffffff, "original native I/O DWORD required")
    _require(value["requested"] == requested and value["returned"] == requested
             and value["write_return"] != 0 and value["flush_return"] != 0,
             "original main packet write/flush failed or short")
    # A success-call error is retained as observed, not a fabricated BOOL rule.
    # Footer append/flush remains outside this main-operation observation.


def decode_comparison_record(original):
    _require(type(original) is bytes and len(original) == COMPARISON_RECORD.size,
             "exact original 64-byte comparison record required")
    return dict(zip(RESULT_FIELDS, COMPARISON_RECORD.unpack(original)))


def _source_helpers():
    """Privately compile fixed validators; never project a V2 read into V1."""
    raw = V1_ADAPTER.read_bytes()
    _require(_sha(raw) == V1_ADAPTER_SHA256, "frozen V1 validator source changed")
    tree = ast.parse(raw, filename=str(V1_ADAPTER))
    names = ("parse_archive", "create_adapter", "collect_archive")
    terminal = tree.body[-1]
    _require(isinstance(terminal, ast.Assign) and len(terminal.targets) == 1
             and isinstance(terminal.targets[0], ast.Tuple)
             and tuple(getattr(item, "id", None) for item in terminal.targets[0].elts) == names
             and isinstance(terminal.value, ast.Call) and isinstance(terminal.value.func, ast.Name)
             and terminal.value.func.id == "_api_factory" and not terminal.value.args and not terminal.value.keywords,
             "exact fixed V1 terminal factory required")
    tree.body.pop()
    imports = [node for node in tree.body if isinstance(node, ast.Import)
               and len(node.names) == 1 and (node.names[0].name, node.names[0].asname) in
               (("hidden_soak_loaded_image", "image"), ("hidden_soak_loaded_read_session", "session"))]
    _require(len(imports) == 2, "exact fixed validator dependency imports required")
    tree.body = [node for node in tree.body if node not in imports]
    name = "_clash_compare_validators_" + uuid.uuid4().hex
    _require(name not in sys.modules, "private validator namespace collision")
    module = types.ModuleType(name)
    module.__file__ = str(V1_ADAPTER)
    sys.modules[name] = module
    created = [(name, module)]
    snapshots = [(V1_ADAPTER, raw)]
    try:
        for suffix, (relative, digest) in zip(("image", "session"), VALIDATOR_DEPENDENCIES):
            path = ROOT / relative
            original = path.read_bytes()
            _require(_sha(original) == digest, "frozen validator dependency source changed")
            dependency_tree = ast.parse(original, filename=str(path))
            if suffix == "session":
                terminal = dependency_tree.body[-1]
                _require(isinstance(terminal, ast.Assign) and isinstance(terminal.value, ast.Call)
                         and isinstance(terminal.value.func, ast.Name) and terminal.value.func.id == "_api_factory",
                         "fixed session terminal factory required")
                dependency_tree.body.pop()
            child_name = name + "_" + suffix
            _require(child_name not in sys.modules, "private validator dependency namespace collision")
            child = types.ModuleType(child_name); child.__file__ = str(path)
            sys.modules[child_name] = child; created.append((child_name, child))
            exec(compile(dependency_tree, str(path), "exec"), child.__dict__)
            setattr(module, suffix, child)
            snapshots.append((path, original))
        exec(compile(tree, str(V1_ADAPTER), "exec"), module.__dict__)
        module.session.image = module.image
        protocol = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "_protocol")
        def assignment(name):
            rows = [index for index, node in enumerate(protocol.body) if isinstance(node, ast.Assign)
                    and any(isinstance(target, ast.Name) and target.id == name for target in node.targets)]
            _require(len(rows) == 1, "unique fixed validator boundary required: " + name)
            return rows[0]
        startup = deepcopy(protocol.body[assignment("expected"):assignment("calls")])
        scopes = [node for statement in startup for node in ast.walk(statement)
                  if isinstance(node, ast.Constant) and node.value == "asynchronous_only"]
        _require(len(scopes) == 1, "exact fixed startup scope boundary required")
        scopes[0].value = SCOPE
        startup += ast.parse("return create, event, peb, initial_qpc, held_sample, frames[index + 4], index + 5, target_path").body
        cleanup = deepcopy(protocol.body[assignment("stop"):assignment("finish")])
        cleanup += ast.parse("return cleanup").body
        for name, args, body in (("_v2_startup", "frames, external, metadata", startup),
                                 ("_v2_cleanup", "frames, metadata, previous, initial_qpc", cleanup)):
            function = ast.parse("def " + name + "(" + args + "):\n    pass\n").body[0]
            function.body = body
            helper = ast.fix_missing_locations(ast.Module(body=[function], type_ignores=[]))
            exec(compile(helper, str(V1_ADAPTER), "exec"), module.__dict__)
        _require(all(path.read_bytes() == original for path, original in snapshots), "fixed validator source changed during compilation")
        return module, tuple(snapshots)
    finally:
        for created_name, created_module in reversed(created):
            if sys.modules.get(created_name) is created_module:
                del sys.modules[created_name]


FACT_FIELDS = ("schema", "profile", "resolution", "stage", "recipe_revision", "candidate_sha256",
    "probe_sha256", "contract_sha256", "source_closure_sha256", "preferred_base", "image_size", "headers_size",
    "run_id", "checkpoint_id", "epoch_id", "controller_pid", "frequency_hz", "origin_tick", "origin_ns",
    "producer_source_closure_sha256", "expected_payload_sha256", "expected_metadata_sha256",
    "expected_issuer_source_sha256", "native_v1_source_sha256", "native_source_sha256", "adapter_source_sha256",
    "request_sha256", "chunk_count", "highlow_count", "claims", "host_source_sha256")
EXTRA_SCHEMAS = dict(archive_magic_io=IO_FIELDS,
    expected_binding=("request_sha256", "expected_payload_sha256", "metadata_hex", "request_path_utf16le",
                      "payload_path_utf16le", "payload_bytes", "chunk_count", "highlow_count", "hash_receipts"),
    comparison_begin=("expected_payload_sha256", "read_count", "scope"),
    comparison_counter=("ordinal", "qpc"),
    comparison_result=("read_sequence", "before_sequence", "comparison_called", "post_qpc_called", "post_qpc"),
    comparison_complete=("read_count", "result_count", "compared_bytes", "expected_payload_sha256"),
    read_virtual_capacity=("ordinal", "address", "requested_bytes", "hresult", "returned_bytes"),
    owner=("run_id", "checkpoint_id", "clock_epoch", "controller", "debugger", "target", "probe_sequence",
           "breakpoint_sequence", "command_sequence", "native_owner_tid", "current_native_tid"),
    startup_owner=("run_id", "checkpoint_id", "clock_epoch", "controller", "debugger", "target", "probe_sequence",
                   "breakpoint_sequence", "command_sequence", "native_owner_tid", "current_native_tid"))


@dataclass(frozen=True)
class ArchiveAuthority:
    """Independent artifact/launch/source bindings, not archive-derived claims."""
    request_sha256: str
    expected_payload_sha256: str
    candidate_file_sha256: str
    host_file_sha256: str
    host_source_sha256: str
    native_source_sha256: str
    adapter_source_sha256: str
    probe_sha256: str
    contract_sha256: str
    source_closure_sha256: str
    producer_source_closure_sha256: str
    archive_sha256: str
    archive_size: int
    run_id: str
    checkpoint_id: str
    epoch_id: str
    controller_pid: int
    native_exit_code: int

    def __post_init__(self):
        for name in self.__dataclass_fields__:
            value = getattr(self, name)
            if name.endswith("sha256"):
                _require(type(value) is str and len(value) == 64 and all(c in "0123456789abcdef" for c in value),
                         "canonical independent digest required")
        for name in ("run_id", "checkpoint_id", "epoch_id"):
            value = getattr(self, name)
            _require(type(value) is str and uuid.UUID(value).hex == value, "canonical independent token required")
        _integer(self.archive_size, 0, (1 << 63) - 1, "entire original archive size required")
        _integer(self.controller_pid, 1, 0xffffffff, "independent controller PID required")
        _integer(self.native_exit_code, 0, 0xffffffff, "original external exit DWORD required")

    @property
    def observed_host_exit_code(self):
        return self.native_exit_code


def _protocol(original_frames, external, facts, helpers):
    metadata = _exact(_json(facts.metadata_json.encode("ascii")), FACT_FIELDS, "source-issued comparison facts")
    _require(metadata["schema"] == "loader_compare_request_v2" and _canonical(metadata["claims"]) == _canonical(FALSE_CLAIMS),
             "exact V2 scope and false broad claims required")
    schemas = {**helpers.STARTUP_SCHEMAS, **helpers.COLLECTOR_SCHEMAS, **EXTRA_SCHEMAS}
    schemas.pop("read_virtual")
    for row in original_frames:
        _require(row.operation in schemas, "unknown V2 operation")
        _exact(row.data(), schemas[row.operation], row.operation)
        _io(row.io(), 8 + len(row.metadata) + len(row.raw))
        _require(row.operation not in ("error", "native_failure"), "original sticky native failure retained")
        if row.operation == "output":
            value = row.data()
            _integer(value["mask"], 0, 0xffffffff, "original output mask required")
            text = helpers._hex(value["text_hex"], 32768, "output callback")
            _require(text and text[-1] == 0 and b"\0" not in text[:-1], "complete original output callback required")
    _require(sum(len(row.raw) for row in original_frames) <= MAX_TOTAL_RAW and
             len(MAGIC) + sum(32 + len(row.metadata) for row in original_frames) <= MAX_TOTAL_METADATA,
             "original failure allowance cannot yield completion")
    frames = tuple(row for row in original_frames if row.operation != "output")
    _require(tuple(row.operation for row in frames[:5]) ==
             ("archive_magic_io", "expected_binding", "invocation", "comparison_begin", "origin"),
             "fixed V2 magic/binding/invocation/comparison/origin order required")
    _io(frames[0].data(), len(MAGIC))
    binding = frames[1].data()
    meta_size = struct.unpack_from("<I", facts.expected_payload, 12)[0]
    expected_binding = dict(request_sha256=metadata["request_sha256"], expected_payload_sha256=metadata["expected_payload_sha256"],
        metadata_hex=facts.expected_payload[48:48 + meta_size].hex(), payload_bytes=len(facts.expected_payload),
        chunk_count=len(facts.descriptors), highlow_count=len(facts.fixups))
    _require(all(type(binding[name]) is type(value) and binding[name] == value for name, value in expected_binding.items()),
             "original expected payload metadata/inventory/source binding differs")
    hashes = ((facts.request_bytes, _sha(facts.request_bytes)), (facts.request_bytes[:-32], facts.request_bytes[-32:].hex()),
              (facts.expected_payload, _sha(facts.expected_payload)), (facts.expected_payload[:-32], facts.expected_payload[-32:].hex()))
    _require(type(binding["hash_receipts"]) is list and len(binding["hash_receipts"]) == len(hashes), "four original buffer hash receipts required")
    for receipt, (original, digest) in zip(binding["hash_receipts"], hashes):
        _exact(receipt, ("input_bytes", "open_status", "hash_status", "close_status", "digest_hex"), "original buffer hash")
        for name in ("open_status", "hash_status", "close_status"):
            _integer(receipt[name], -(1 << 31), 0xffffffff, "original signed/unsigned NTSTATUS required")
        _require(type(receipt["input_bytes"]) is int and receipt["input_bytes"] == len(original)
                 and all(receipt[name] == 0 for name in ("open_status", "hash_status", "close_status"))
                 and receipt["digest_hex"] == digest, "original complete buffer hash operation failed/reordered/differs")
    for name in ("request_path_utf16le", "payload_path_utf16le"):
        raw = helpers._hex(binding[name], 65536, "original input path")
        _require(len(raw) % 2 == 0 and raw.endswith(b"\0\0"), "whole original UTF16LE input path required")
        helpers.image._path(raw[:-2].decode("utf-16-le", "strict"))
    count = len(facts.descriptors) + 1
    _require(1 < count <= 512 and metadata["chunk_count"] == count - 1 and metadata["highlow_count"] == len(facts.fixups),
             "complete source-issued read/fixup inventory differs")
    _require(frames[3].data() == dict(expected_payload_sha256=metadata["expected_payload_sha256"], read_count=count, scope=IMMUTABLE_SCOPE),
             "original comparison-begin scope/count differs")
    control = frames[2:3] + frames[4:]
    create, event, peb, initial, held, startup_owner, index, target_path = helpers._v2_startup(control, external, metadata)
    _require(create["module_size"] == metadata["image_size"], "original module extent differs")
    base = create["base_offset"]
    _integer(base, 0x10000, helpers.image.USER_LIMIT - metadata["image_size"], "bounded original callback base required")
    _require(base % 0x10000 == 0, "original callback base alignment differs")
    expected_chunks = facts.model_chunks(base)
    _require(type(expected_chunks) is tuple and len(expected_chunks) == len(facts.descriptors), "complete fixed expected model required")
    calls = control[index:-3]
    position, previous = 0, held.tick
    owners = []
    identities = {}
    native_owner_tid = startup_owner.data()["native_owner_tid"]
    _integer(native_owner_tid, 1, 0xffffffff, "original retained native owner TID required")
    for role in ("controller", "debugger", "target"):
        raw = startup_owner.data()[role]
        path = helpers._hex(raw["image_path_utf16le"], 65536, "generation path").decode("utf-16-le", "strict")
        identities[role] = helpers.image.Generation(raw["pid"], raw["creation_filetime"], path, raw["image_sha256"])
    _require((identities["controller"].pid, identities["debugger"].image_sha256, identities["target"].pid,
              identities["target"].image_sha256, identities["target"].image_path) ==
             (external.controller_pid, external.host_file_sha256, create["pid"], external.candidate_file_sha256,
              helpers.image._path(target_path)), "original retained source/file/PID identities differ")
    def owner(row):
        value = row.data()
        for name in ("native_owner_tid", "current_native_tid"):
            _integer(value[name], 1, 0xffffffff, "original owner thread DWORD required")
            _require(value[name] == native_owner_tid, "original owner thread changed")
        for name in ("probe_sequence", "breakpoint_sequence", "command_sequence"):
            _integer(value[name], 0, (1 << 63) - 1, "original owner sequence integer required")
        _require((value["run_id"], value["checkpoint_id"], value["clock_epoch"], value["probe_sequence"],
                  value["breakpoint_sequence"], value["command_sequence"]) ==
                 (metadata["run_id"], metadata["checkpoint_id"], metadata["epoch_id"], 0, 0, 0),
                 "original owner scope/command sequence differs")
        for role, parent in (("controller", None), ("debugger", identities["controller"]), ("target", identities["debugger"])):
            helpers._generation(value[role], identities[role], parent)
        owners.append(row)
    owner(startup_owner)
    def take(operation):
        nonlocal position
        _require(position < len(calls) and calls[position].operation == operation,
                 "required V2 operation absent/reordered/duplicated: " + operation)
        row = calls[position]
        position += 1
        return row
    def clock(value):
        nonlocal previous
        sample = helpers._qpc(value, metadata)
        _require(previous <= sample.tick <= initial.tick + 20 * metadata["frequency_hz"],
                 "original QPC order/unchanged twenty-second hold failed")
        previous = sample.tick
        return sample
    def counter():
        return clock(take("counter").data())
    def phase():
        owner(take("owner")); counter()
        expected_values = (6, create["pid"], create["tid"], event["engine_pid"], event["engine_tid"])
        for name, value in zip(helpers.image.PHASE_QUERY_NAMES, expected_values):
            counter(); packet = take("query").data()
            observed = helpers.image.NativeQuery(**packet)
            _require((observed.name, observed.hresult, observed.value) == (name, 0, value), "original phase query failed/differs")
            counter()
        counter(); packet = take("GetNumberBreakpoints").data()
        _require(type(packet["hresult"]) is type(packet["count"]) is int and packet == dict(hresult=0, count=0),
                 "original breakpoint query failed/nonzero")
        counter(); counter(); packet = take("pointer64").data()
        _require(type(packet["hresult"]) is int and packet["hresult"] == 1, "original x86 pointer-width query failed")
        counter(); owner(take("owner"))
    counter()
    compared = 0
    result_rows = []
    for ordinal in range(count):
        phase(); counter(); row = take("read_virtual_capacity"); value = row.data()
        if ordinal == 0:
            address, expected = peb["address"] + 8, struct.pack("<I", base)
            descriptor, fixups = 0xffffffff, 0
        else:
            address, expected = expected_chunks[ordinal - 1]
            descriptor, fixups = ordinal - 1, facts.descriptors[ordinal - 1][5]
        _require(type(expected) is bytes and type(address) is int and address == (peb["address"] + 8 if ordinal == 0 else base + facts.descriptors[ordinal - 1][1]),
                 "exact PEB-derived expected address/source bytes required")
        for name in ("ordinal", "address", "requested_bytes", "returned_bytes"):
            _integer(value[name], 0, 0xffffffff, "original capacity-read DWORD required")
        _integer(value["hresult"], -(1 << 31), 0xffffffff, "original signed/unsigned HRESULT required")
        _require((value["ordinal"], value["address"], value["requested_bytes"], value["hresult"], value["returned_bytes"], len(row.raw)) ==
                 (ordinal, address, len(expected), 0, len(expected), len(expected)), "original full capacity read failed/partial/differs")
        counter(); phase(); before_row = take("comparison_counter"); before = before_row.data()
        _require(type(before["ordinal"]) is int and before["ordinal"] == ordinal, "comparison-start ordinal differs")
        start = clock(before["qpc"])
        result_row = take("comparison_result"); result = result_row.data()
        _require(result["comparison_called"] is True and result["post_qpc_called"] is True
                 and type(result["read_sequence"]) is type(result["before_sequence"]) is int
                 and (result["read_sequence"], result["before_sequence"]) == (row.sequence, before_row.sequence),
                 "original comparison operation/read/clock binding differs")
        end = clock(result["post_qpc"])
        mismatches = [index for index, (actual, wanted) in enumerate(zip(row.raw, expected)) if actual != wanted]
        wanted = dict(version=1, ordinal=ordinal, descriptor_index=descriptor, read_frame_sequence=row.sequence,
            requested_bytes=len(expected), returned_bytes=len(expected), comparison_status=bool(mismatches),
            mismatch_count=len(mismatches), first_mismatch=mismatches[0] if mismatches else 0xffffffff,
            applied_highlow_count=fixups, address=address, before_tick=start.tick, after_tick=end.tick)
        wanted["comparison_status"] = int(wanted["comparison_status"])
        _require(decode_comparison_record(result_row.raw) == wanted, "original comparison scalar result differs from recomputed bytes")
        _require(not mismatches, "original immutable byte mismatch retained")
        compared += len(expected); result_rows.append(result_row)
    phase()
    complete = take("comparison_complete")
    _require(complete.data() == dict(read_count=count, result_count=count, compared_bytes=compared,
              expected_payload_sha256=metadata["expected_payload_sha256"]), "complete original comparison counts/source differ")
    counter(); _require(position == len(calls), "extra unconsumed V2 operation")
    cleanup = helpers._v2_cleanup(control, metadata, previous, initial)
    _require((cleanup["target_pid"], cleanup["target_creation_filetime"]) ==
             (identities["target"].pid, identities["target"].creation_filetime), "original cleanup generation differs")
    finish = frames[-1].data()
    _require(finish == dict(status="complete", frame_count=len(original_frames) - 1,
        raw_bytes=sum(len(row.raw) for row in original_frames[:-1]),
        metadata_bytes=len(MAGIC) + sum(32 + len(row.metadata) for row in original_frames[:-1]), comparison_scope=SCOPE),
        "original finish counters/status/scope differ")
    return dict(metadata=metadata, create=create, event=event, peb=peb, held=initial,
                owners=tuple(owners), identities=identities, cleanup=cleanup, compared_bytes=compared,
                read_count=count, results=tuple(result_rows))


@dataclass(frozen=True, eq=False, slots=True, weakref_slot=True)
class ParsedArchive:
    original_archive: bytes
    frames: tuple


@dataclass(frozen=True)
class ReplayResult:
    report_json: str
    original_archive: bytes
    frames: tuple

    def report(self):
        return _json(self.report_json.encode("ascii"))


def _build_api(imported_source, public_authority, *, _inspector=None, _helpers=None):
    """Called only in isolated compiled globals; fixture inspectors stay local."""
    _require(_helpers is None or _inspector[1] is _fixture_inspector_guard,
             "supplied validators are restricted to explicit fixture registries")
    helpers, helper_sources = _source_helpers() if _helpers is None else _helpers
    inspector, inspector_guard = _inspector
    inspect = inspector
    reader, protocol, authority_class, parsed_class = parse_frames, _protocol, ArchiveAuthority, ParsedArchive
    issued = {}
    source_path, source_raw = SOURCE, imported_source
    def check_source():
        _require(source_path.read_bytes() == source_raw and all(path.read_bytes() == original for path, original in helper_sources),
                 "imported comparator/validator source changed")
    def seal(frames):
        return tuple((row.sequence, row.operation, row.metadata, row.raw, row.footer, row.offset) for row in frames)
    def admission(raw, external, facts):
        check_source()
        _require(type(raw) is bytes and type(external) is public_authority, "independent typed archive authority required")
        external = authority_class(**asdict(external))
        _require((_sha(raw), len(raw)) == (external.archive_sha256, external.archive_size), "independent entire archive binding differs")
        facts.check_sources()
        metadata = _exact(_json(facts.metadata_json.encode("ascii")), FACT_FIELDS, "source-issued facts")
        _require(type(facts.request_bytes) is type(facts.expected_payload) is type(facts.host_source) is bytes
                 and len(facts.request_bytes) == 320 and _sha(facts.request_bytes[:-32]) == facts.request_bytes[-32:].hex()
                 and _sha(facts.request_bytes) == metadata["request_sha256"]
                 and _sha(facts.expected_payload) == metadata["expected_payload_sha256"]
                 and _sha(facts.host_source) == metadata["host_source_sha256"], "complete fixed request/payload/host bytes differ")
        expected = dict(request_sha256=external.request_sha256, expected_payload_sha256=external.expected_payload_sha256,
            candidate_sha256=external.candidate_file_sha256, host_source_sha256=external.host_source_sha256,
            native_source_sha256=external.native_source_sha256, adapter_source_sha256=external.adapter_source_sha256,
            probe_sha256=external.probe_sha256, contract_sha256=external.contract_sha256,
            source_closure_sha256=external.source_closure_sha256, producer_source_closure_sha256=external.producer_source_closure_sha256,
            run_id=external.run_id, checkpoint_id=external.checkpoint_id, epoch_id=external.epoch_id, controller_pid=external.controller_pid)
        _require(all(type(metadata[name]) is type(value) and metadata[name] == value for name, value in expected.items())
                 and _sha(source_raw) == external.adapter_source_sha256,
                 "independent source/request/payload/candidate/probe/launch binding differs")
        return external
    def parse(raw, external, request):
        frames = ()
        try:
            check_source(); inspector_guard(); facts = inspect(request)
            fixed = admission(raw, external, facts)
            frames = reader(raw); observed = protocol(frames, fixed, facts, helpers)
            facts.check_sources(); inspector_guard(); check_source()
            parsed = parsed_class(raw, frames)
            key = id(parsed)
            def retired(reference):
                if key in issued and issued[key][0] is reference:
                    del issued[key]
            issued[key] = (weakref.ref(parsed, retired), raw, frames, seal(frames), facts, fixed, observed)
            return parsed
        except ArchiveError:
            raise
        except Exception as error:
            raise ArchiveError(type(error).__name__ + ": " + str(error), raw, frames) from error
    def result(raw, frames, observed, *, fixture):
        metadata = observed["metadata"]
        report = dict(schema="loader_compare_replay_v2", fixture_only=fixture,
            immutable_comparison_replay_passed=True, supplied_receipt_math_only=True,
            archive_sha256=_sha(raw), archive_bytes=len(raw), read_count=observed["read_count"],
            compared_bytes=observed["compared_bytes"], expected_payload_sha256=metadata["expected_payload_sha256"],
            profile=metadata["profile"], resolution=metadata["resolution"], stage=metadata["stage"],
            recipe_revision=metadata["recipe_revision"], candidate_sha256=metadata["candidate_sha256"],
            probe_sha256=metadata["probe_sha256"], scope=IMMUTABLE_SCOPE,
            receipt_tail="The footer cannot attest its own append/flush; independent storage remains required.",
            issuer_registry_boundary="Request issuance and parsing use the same private source-checked registry.",
            **FALSE_CLAIMS)
        return ReplayResult(_canonical(report).decode("ascii"), raw, frames)
    def replay(parsed, authority, anchor):
        entry = issued.get(id(parsed))
        supplied_raw = parsed.original_archive if isinstance(parsed, parsed_class) else None
        genuine = type(parsed) is parsed_class and entry is not None and entry[0]() is parsed
        raw = entry[1] if genuine else supplied_raw
        frames = parsed.frames if isinstance(parsed, parsed_class) else ()
        try:
            check_source(); inspector_guard()
            _require(type(parsed) is parsed_class and entry is not None and entry[0]() is parsed,
                     "live source-issued parsed archive identity required")
            _, original, expected_frames, sealed, facts, external, observed = entry
            _require(supplied_raw is original and frames is expected_frames and seal(frames) == sealed,
                     "source-issued archive was changed")
            facts.check_sources()
            authority = helpers.image._clone(helpers.image.LoaderAuthority, authority)
            anchor = helpers.session._clone(helpers.session.QpcAnchor, anchor)
            metadata = observed["metadata"]
            for name in ("profile", "resolution", "stage", "recipe_revision", "probe_sha256", "source_closure_sha256"):
                _require(getattr(authority, name) == metadata[name], "independent loader recipe/source differs")
            _require((authority.run_id, authority.checkpoint_id, authority.clock_epoch, authority.controller.pid,
                      authority.candidate_sha256, authority.debugger.image_sha256) ==
                     (external.run_id, external.checkpoint_id, external.epoch_id, external.controller_pid,
                      external.candidate_file_sha256, external.host_file_sha256), "independent loader launch binding differs")
            create, event, peb = observed["create"], observed["event"], observed["peb"]
            _require((authority.target.pid, authority.primary_tid, authority.image_base, authority.peb_address,
                      authority.engine_pid, authority.engine_tid) ==
                     (create["pid"], create["tid"], create["base_offset"], peb["address"], event["engine_pid"], event["engine_tid"]),
                     "independent retained target/selected context differs")
            for row in observed["owners"]:
                for role, parent in (("controller", None), ("debugger", authority.controller), ("target", authority.debugger)):
                    helpers._generation(row.data()[role], getattr(authority, role), parent)
            _require((anchor.epoch_id, anchor.frequency_hz, anchor.origin_tick, anchor.origin_ns, anchor.held_start_tick) ==
                     (metadata["epoch_id"], metadata["frequency_hz"], metadata["origin_tick"], metadata["origin_ns"], observed["held"].tick),
                     "independent clock origin/first callback anchor differs")
            _require((authority.clock_origin_ns, authority.checkpoint_start_ns) ==
                     (anchor.origin_ns, helpers.session.project(anchor, anchor.held_start_tick).lower_ns),
                     "independent held-clock mapping differs")
            facts.check_sources(); inspector_guard(); check_source()
            return result(raw, frames, observed, fixture=inspector_guard is _fixture_inspector_guard)
        except Exception as error:
            if isinstance(error, ArchiveError):
                raise
            raise ArchiveError(type(error).__name__ + ": " + str(error), raw, frames,
                               original_observation=supplied_raw) from error
    def fixture_replay(raw, facts, external):
        frames = ()
        try:
            fixed = admission(raw, external, facts)
            frames = reader(raw); observed = protocol(frames, fixed, facts, helpers)
            facts.check_sources(); check_source()
            return result(raw, frames, observed, fixture=True)
        except Exception as error:
            if isinstance(error, ArchiveError):
                raise
            raise ArchiveError(type(error).__name__ + ": " + str(error), raw, frames) from error
    return parse, replay, fixture_replay


_IMPORTED_SOURCE_BYTES = SOURCE.read_bytes()
_IMPORTED_GENERATOR_BYTES = GENERATOR.read_bytes()


def _fixture_inspector_guard():
    """An explicit fixture registry never grants production issuance."""


def _api_factory(*, _inspector=None, _helpers=None, _path=SOURCE, _raw=_IMPORTED_SOURCE_BYTES,
                 _parse=ast.parse, _module=types.ModuleType, _modules=sys.modules,
                 _fresh=uuid.uuid4, _compile=compile, _exec=exec, _walk=ast.walk,
                 _assign=ast.Assign, _tuple=ast.Tuple, _call=ast.Call, _name=ast.Name,
                 _authority=ArchiveAuthority, _error=ArchiveError,
                 _generator=GENERATOR, _generator_raw=_IMPORTED_GENERATOR_BYTES):
    """Recompile canonical admission before any public helper can execute."""
    if _path.read_bytes() != _raw:
        raise ValueError("imported adapter source differs before private compilation")
    def inspector_guard():
        if _generator.read_bytes() != _generator_raw:
            raise ValueError("privately compiled generator source changed")
    inspector_guard()
    tree = _parse(_raw, filename=str(_path))
    names = ("prepare_comparison_plan", "prepare_comparison_request", "inspect_comparison_request",
             "parse_archive", "replay_archive", "replay_fixture_archive")
    terminal = tree.body[-1]
    calls = [node for node in _walk(tree) if isinstance(node, _call)
             and isinstance(node.func, _name) and node.func.id == "_api_factory"]
    if (len(calls) != 1 or not isinstance(terminal, _assign) or len(terminal.targets) != 1
            or not isinstance(terminal.targets[0], _tuple)
            or tuple(getattr(item, "id", None) for item in terminal.targets[0].elts) != names
            or not isinstance(terminal.value, _call) or not isinstance(terminal.value.func, _name)
            or terminal.value.func.id != "_api_factory" or terminal.value.args or terminal.value.keywords):
        raise ValueError("sole exact terminal public factory required")
    tree.body.pop()
    name = "_clash_compare_adapter_" + _fresh().hex
    if name in _modules:
        raise ValueError("private adapter namespace collision")
    module = _module(name); module.__file__ = str(_path); _modules[name] = module
    generator_name = name + "_generator"
    generator = _module(generator_name); generator.__file__ = str(_generator)
    if generator_name in _modules:
        if _modules.get(name) is module:
            del _modules[name]
        raise ValueError("private generator namespace collision")
    _modules[generator_name] = generator
    try:
        generator_tree = _parse(_generator_raw, filename=str(_generator))
        terminal = generator_tree.body[-1]
        generator_names = ("prepare_comparison_plan", "prepare_comparison_request", "inspect_comparison_request")
        calls = [node for node in _walk(generator_tree) if isinstance(node, _call)
                 and isinstance(node.func, _name) and node.func.id == "_factory"]
        if (len(calls) != 1 or not isinstance(terminal, _assign) or len(terminal.targets) != 1
                or not isinstance(terminal.targets[0], _tuple)
                or tuple(getattr(item, "id", None) for item in terminal.targets[0].elts) != generator_names
                or not isinstance(terminal.value, _call) or not isinstance(terminal.value.func, _name)
                or terminal.value.func.id != "_factory" or terminal.value.args or terminal.value.keywords):
            raise ValueError("sole exact terminal generator factory required")
        generator_tree.body.pop()
        _exec(_compile(generator_tree, str(_generator), "exec"), generator.__dict__)
        inspector_guard()
        issuer_apis = generator._factory()
        inspector_guard()
        _exec(_compile(tree, str(_path), "exec"), module.__dict__)
        if _path.read_bytes() != _raw:
            raise ValueError("adapter source changed during private compilation")
        module.ArchiveError = _error
        if _inspector is None:
            selected = (issuer_apis[2], inspector_guard)
        else:
            selected = (_inspector, module._fixture_inspector_guard)
        def guarded(operation):
            def issue(*args, **kwargs):
                if _path.read_bytes() != _raw:
                    raise ValueError("adapter source changed before private issuance")
                inspector_guard()
                result = operation(*args, **kwargs)
                inspector_guard()
                if _path.read_bytes() != _raw:
                    raise ValueError("adapter source changed after private issuance")
                return result
            return issue
        return tuple(guarded(operation) for operation in issuer_apis) + module._build_api(
            _raw, _authority, _inspector=selected, _helpers=_helpers)
    finally:
        if _modules.get(generator_name) is generator:
            del _modules[generator_name]
        if _modules.get(name) is module:
            del _modules[name]


prepare_comparison_plan, prepare_comparison_request, inspect_comparison_request, parse_archive, replay_archive, replay_fixture_archive = _api_factory()
