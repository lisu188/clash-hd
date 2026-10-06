"""Offline binary native-loader archive adapter; no native calls or launch.

Original frames and the entire archive remain available after malformed input,
failed native observations or incomplete collection. Supplied source/launch
bindings cannot establish native issuance, synchronous coherence or acceptance.
This offline model does not authenticate a running controller, its loaded Python
implementation, public alias environment, compilation, or unknown engine events.
Oversized original packets remain the caller's independently retained debt;
rejecting an unavailable payload cannot establish complete native retention.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
import struct
import weakref

import hidden_soak_loaded_image as image
import hidden_soak_loaded_read_session as session

SOURCE = Path(__file__).resolve()
_IMPORTED_SOURCE_BYTES = SOURCE.read_bytes()
MAGIC = b"CLHDLR1\0"
MAX_FRAME_METADATA = 512 * 1024
MAX_FRAME_RAW = 65539
MAX_TOTAL_RAW = 16 * 1024 * 1024 + MAX_FRAME_RAW
MAX_TOTAL_METADATA = 8 * 1024 * 1024
MAX_FAILURE_METADATA = MAX_TOTAL_METADATA + 1024 * 1024
MAX_FRAMES = 32768
FALSE_CLAIMS = {name: False for name in (
    "passed", "native_producer_provenance_verified", "native_loaded_bytes_verified",
    "whole_candidate_verified", "native_coherence_verified", "native_clock_verified",
    "running_duration_verified", "host_clock_coverage_verified", "no_breakaway_job_verified",
    "runtime_acceptance", "manual_input_verified", "release_acceptance", "promotion_ready", "stable")}


def _require(value, message):
    if not value: raise ValueError(message)


def _integer(value, minimum, maximum, label):
    _require(type(value) is int and minimum <= value <= maximum, label)


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")


def _object(pairs):
    result = {}
    for key, value in pairs:
        _require(key not in result, "duplicate original metadata key")
        result[key] = value
    return result


def _exact(value, names, label):
    _require(type(value) is dict and set(value) == set(names), "exact original " + label + " fields required")
    return value


@dataclass(frozen=True)
class OriginalFrame:
    sequence: int
    operation: str
    metadata: bytes
    raw: bytes
    offset: int

    def data(self):
        return json.loads(self.metadata)["data"]


class ArchiveError(ValueError):
    """Full original bytes and prior complete frames survive every rejection."""
    def __init__(self, message, original_archive, parsed_frames=(), original_result=None):
        super().__init__(message)
        self.original_archive = original_archive
        self.parsed_frames = tuple(parsed_frames)
        self.original_result = original_result


def _frames(raw):
    frames, metadata_total, raw_total, offset = [], len(MAGIC), 0, len(MAGIC)
    try:
        _require(type(raw) is bytes, "entire original archive bytes required")
        _require(len(raw) <= MAX_FAILURE_METADATA + MAX_TOTAL_RAW, "original archive exceeds source-owned capacity; retained intact")
        _require(raw.startswith(MAGIC), "original archive magic missing or incompatible")
        while offset < len(raw):
            _require(len(frames) < MAX_FRAMES, "original frame count exceeds source-owned bound")
            _require(len(raw) - offset >= 8, "truncated original frame header")
            start = offset
            metadata_bytes, raw_bytes = struct.unpack_from("<II", raw, offset)
            offset += 8
            _require(0 < metadata_bytes <= MAX_FRAME_METADATA and raw_bytes <= MAX_FRAME_RAW,
                     "original per-frame length exceeds source-owned bound")
            metadata_total += 8 + metadata_bytes; raw_total += raw_bytes
            _require(metadata_total <= MAX_FAILURE_METADATA and raw_total <= MAX_TOTAL_RAW,
                     "original aggregate length exceeds source-owned bound")
            _require(metadata_bytes + raw_bytes <= len(raw) - offset, "truncated original metadata or raw prefix")
            metadata = raw[offset:offset + metadata_bytes]; offset += metadata_bytes
            original = raw[offset:offset + raw_bytes]; offset += raw_bytes
            value = json.loads(metadata.decode("ascii"), object_pairs_hook=_object,
                               parse_constant=lambda value: (_ for _ in ()).throw(ValueError("nonfinite original metadata")))
            _require(_canonical(value) == metadata, "original metadata is not canonical ASCII JSON")
            _exact(value, ("sequence", "operation", "data"), "frame")
            _integer(value["sequence"], 1, MAX_FRAMES, "original frame sequence is not an integer")
            _require(value["sequence"] == len(frames) + 1, "original frame sequence omitted, repeated or reordered")
            _require(type(value["operation"]) is str and 0 < len(value["operation"]) <= 128 and
                     value["operation"].isascii() and type(value["data"]) is dict, "original frame operation/data shape differs")
            _require(value["operation"] in ("read_virtual", "native_failure") or not original,
                     "raw bytes attached to an incompatible operation")
            frames.append(OriginalFrame(value["sequence"], value["operation"], metadata, original, start))
        _require(frames, "empty original archive")
        return tuple(frames)
    except Exception as error:
        raise ArchiveError(type(error).__name__ + ": " + str(error), raw, frames) from error


GENERATION_FIELDS = ("pid", "pid_error", "path_return", "path_error", "path_chars", "image_path_utf16le",
    "times_return", "times_error", "creation_filetime", "exit_filetime", "kernel_filetime", "user_filetime",
    "image_sha256", "hash_status", "wait_result", "wait_error", "parent_pid", "parent_query_return",
    "parent_query_error", "parent_creation_filetime", "parent_times_return", "parent_times_error")


def _generation(raw, expected, parent):
    _exact(raw, GENERATION_FIELDS, "retained generation")
    for name in ("pid", "pid_error", "path_error", "path_chars", "times_error", "wait_result", "wait_error",
                 "parent_pid", "parent_query_error", "parent_times_error"):
        _integer(raw[name], 0, 0xffffffff, "original native generation DWORD differs")
    for name in ("path_return", "times_return", "parent_query_return", "parent_times_return", "hash_status"):
        _integer(raw[name], -(1 << 31), 0xffffffff, "original native signed32/DWORD scalar differs")
    for name in ("creation_filetime", "exit_filetime", "kernel_filetime", "user_filetime", "parent_creation_filetime"):
        _integer(raw[name], 0, (1 << 64) - 1, "original native FILETIME differs")
    text = raw["image_path_utf16le"]
    _require(type(text) is str and len(text) <= 2 * 65536 and len(text) % 4 == 0 and
             all(c in "0123456789abcdef" for c in text), "bounded canonical original UTF16LE bytes required")
    original_path = bytes.fromhex(text)
    _require(0 < raw["path_chars"] <= 32768 and raw["path_chars"] * 2 == len(original_path),
             "original returned path count differs from exact retained UTF16LE prefix")
    path = original_path[:raw["path_chars"] * 2].decode("utf-16-le", "strict")
    _require(raw["path_return"] != 0 and raw["times_return"] != 0 and raw["hash_status"] == 0,
             "original generation path/time/hash query failed")
    _require(raw["wait_result"] == 258 and raw["exit_filetime"] == 0 and
             all(raw[name] == 0 for name in ("pid_error", "path_error", "times_error", "wait_error")),
             "original retained generation wait or cleared-error receipt failed")
    observed = image.Generation(raw["pid"], raw["creation_filetime"], path, raw["image_sha256"])
    _require(observed == expected, "original observed generation differs from independent authority")
    _require(raw["parent_query_return"] != 0 and raw["parent_times_return"] != 0 and
             raw["parent_query_error"] == raw["parent_times_error"] == 0 and
             raw["parent_pid"] > 0 and raw["parent_creation_filetime"] > 0,
             "original parent query/time failed; ancestry above controller remains unbound")
    if parent is not None:
        _require(raw["parent_query_return"] != 0 and raw["parent_times_return"] != 0 and
                 (raw["parent_pid"], raw["parent_creation_filetime"]) == (parent.pid, parent.creation_filetime) and
                 raw["parent_query_error"] == raw["parent_times_error"] == 0,
                 "original observed parent generation differs or failed")
    return observed, raw["wait_result"], raw["wait_error"]


@dataclass(frozen=True)
class ArchiveAuthority:
    """Independent launch/source/artifact binding; never derived from archive."""
    request_sha256: str
    candidate_file_sha256: str
    host_file_sha256: str
    host_source_sha256: str
    native_source_sha256: str
    adapter_source_sha256: str
    archive_sha256: str
    archive_size: int
    run_id: str
    checkpoint_id: str
    epoch_id: str
    controller_pid: int
    observed_host_exit_code: int

    def __post_init__(self):
        for name in ("request_sha256", "candidate_file_sha256", "host_file_sha256", "host_source_sha256",
                     "native_source_sha256", "adapter_source_sha256", "archive_sha256"):
            image._digest(getattr(self, name))
        for name in ("run_id", "checkpoint_id", "epoch_id"): image._token(getattr(self, name))
        _integer(self.archive_size, 0, (1 << 63) - 1, "entire original archive size required")
        _integer(self.controller_pid, 1, 0xffffffff, "independent controller PID required")
        _integer(self.observed_host_exit_code, 0, 0xffffffff, "original launch-observed host exit DWORD required")


COLLECTOR_SCHEMAS = dict(counter=tuple(session.QpcSample.__dataclass_fields__),
    query=("name", "hresult", "value"), GetNumberBreakpoints=("hresult", "count"),
    pointer64=("hresult",), read_virtual=("ordinal", "address", "requested_bytes", "hresult", "returned_bytes"),
    owner=("run_id", "checkpoint_id", "clock_epoch", "controller", "debugger", "target",
           "probe_sequence", "breakpoint_sequence", "command_sequence"))


class OfflineAdapter:
    """One ordered immutable transcript cursor, not a Windows API adapter."""
    def __init__(self, archive, authority, anchor):
        _require(type(authority) is image.LoaderAuthority and type(anchor) is session.QpcAnchor,
                 "independent typed loader authority and QPC anchor required")
        self.archive, self.authority, self.anchor = archive, authority, anchor
        self.rows = tuple(row for row in archive.frames if row.operation in COLLECTOR_SCHEMAS)
        self.position, self.read_ordinal = 0, 0

    def _take(self, operation):
        try:
            self.archive.check_sources()
            _require(type(self.rows) is tuple and self.rows == tuple(row for row in self.archive.frames if row.operation in COLLECTOR_SCHEMAS),
                     "source-issued original collector stream was replaced")
            _require(self.position < len(self.rows), "required original collector operation is absent")
            row = self.rows[self.position]
            _require(row.operation == operation, "original collector operation missing/reordered/duplicated")
            self.position += 1
            _exact(row.data(), COLLECTOR_SCHEMAS[operation], operation)
            return row, row.data()
        except Exception as error:
            original = self.rows[self.position - 1] if self.position else None
            raise ArchiveError(str(error), self.archive.original_archive, self.archive.frames, original) from error

    def counter(self):
        row, value = self._take("counter")
        try: return session.QpcSample(**value)
        except Exception as error: raise ArchiveError(str(error), self.archive.original_archive, self.archive.frames, row) from error

    def query(self, name):
        row, value = self._take("query")
        try:
            _require(value["name"] == name, "original native query name differs from requested operation")
            return image.NativeQuery(**value)
        except Exception as error: raise ArchiveError(str(error), self.archive.original_archive, self.archive.frames, row) from error

    def get_number_breakpoints(self):
        row, value = self._take("GetNumberBreakpoints")
        try: return session.BreakpointCountResult(**value)
        except Exception as error: raise ArchiveError(str(error), self.archive.original_archive, self.archive.frames, row) from error

    def pointer64(self):
        row, value = self._take("pointer64")
        try: return session.Pointer64Result(**value)
        except Exception as error: raise ArchiveError(str(error), self.archive.original_archive, self.archive.frames, row) from error

    def read_virtual(self, address, size):
        row, value = self._take("read_virtual")
        try:
            for field in ("ordinal", "address", "requested_bytes", "returned_bytes"):
                _integer(value[field], 0, 0xffffffff, "original ReadVirtual DWORD differs")
            _require((value["ordinal"], value["address"], value["requested_bytes"]) ==
                     (self.read_ordinal, address, size), "original ReadVirtual request/ordinal differs")
            self.read_ordinal += 1
            return session.ReadResult(value["hresult"], value["returned_bytes"], row.raw)
        except Exception as error: raise ArchiveError(str(error), self.archive.original_archive, self.archive.frames, row) from error

    def observe_owner(self):
        row, value = self._take("owner")
        try:
            expected = self.authority
            observed = [_generation(value[role], getattr(expected, role), parent)
                        for role, parent in (("controller", None), ("debugger", expected.controller), ("target", expected.debugger))]
            return session.OwnerObservation(value["run_id"], value["checkpoint_id"], value["clock_epoch"],
                *(item[0] for item in observed), tuple(item[1] for item in observed), tuple(item[2] for item in observed),
                value["probe_sequence"], value["breakpoint_sequence"], value["command_sequence"])
        except Exception as error: raise ArchiveError(str(error), self.archive.original_archive, self.archive.frames, row) from error

    def require_consumed(self):
        self.archive.check_sources()
        _require(self.position == len(self.rows), "original collector operations remain unconsumed")


INVOCATION_FIELDS = ("request_sha256", "candidate_file_sha256", "host_file_sha256", "controller_pid",
                     "run_id", "checkpoint_id", "epoch_id", "comparison_scope")
FACT_FIELDS = ("request_sha256", "host_source_sha256", "native_source_sha256", "adapter_source_sha256",
               "candidate_sha256", "profile", "resolution", "stage", "recipe_revision", "probe_sha256",
               "source_closure_sha256", "run_id", "checkpoint_id", "epoch_id", "controller_pid",
               "frequency_hz", "origin_tick", "origin_ns", "preferred_base", "image_size")
CREATE_FIELDS = ("image_handle", "process_handle", "initial_thread_handle", "base_offset", "module_size",
    "thread_data_offset", "start_offset", "module_name_hex", "image_name_hex", "pid", "tid",
    "checksum", "timestamp", "pid_error", "tid_error",
    "duplicate_process_return", "duplicate_process_error", "duplicate_thread_return", "duplicate_thread_error",
    "owned_process_handle", "owned_thread_handle")
LOAD_FIELDS = ("image_handle", "base_offset", "module_size", "module_name_hex", "image_name_hex", "checksum", "timestamp")
CLEANUP_FIELDS = ("target_pid", "target_pid_error", "target_wait", "target_wait_error", "target_creation_filetime", "target_exit_filetime",
    "target_kernel_filetime", "target_user_filetime", "target_times_return", "target_times_error",
    "target_exit_return", "target_exit_error", "target_exit_code", "target_close", "target_close_error",
    "thread_close", "thread_close_error", "controller_close", "controller_close_error", "debugger_close", "debugger_close_error",
    "event_callbacks_hresult", "output_callbacks_hresult")
STARTUP_SCHEMAS = dict(setup=("api_name", "hresult", "value"), callback_create=CREATE_FIELDS,
    callback_load=LOAD_FIELDS, callback_exception=("record_hex", "first_chance", "qpc"),
    wait_event=("hresult", "flags", "timeout_ms"),
    event=("hresult", "type", "engine_pid", "engine_tid", "extra_hex", "description_hex", "extra_used", "description_used"),
    peb=("hresult", "address"), held=("qpc", "initial_exception_sequence"),
    startup_owner=COLLECTOR_SCHEMAS["owner"], origin=("anchor", "sample"), invocation=INVOCATION_FIELDS,
    stop=("end_session_hresult", "qpc", "execution_status"), cleanup=CLEANUP_FIELDS,
    finish=("status", "frame_count", "raw_bytes", "metadata_bytes", "comparison_scope"),
    error=("type_name", "message_hex", "retention_debt"))
STARTUP_SCHEMAS.update(output=("mask", "text_hex"), launch=("target_path_utf16le", "command_hex", "create_flags"),
    native_failure=("api_name", "native_return", "native_error", "requested_bytes", "returned_bytes", "detail_hex"))
SETUP_NAMES = ("DebugCreate", "QueryInterface.control", "QueryInterface.memory", "QueryInterface.system",
               "SetEventCallbacks", "SetOutputCallbacks", "AddEngineOptions", "GetEngineOptions", "CreateProcess")


def _hex(value, maximum, label, exact=None):
    _require(type(value) is str and len(value) % 2 == 0 and len(value) <= 2 * maximum and
             all(c in "0123456789abcdef" for c in value), "canonical bounded original " + label + " hex required")
    raw = bytes.fromhex(value)
    _require(exact is None or len(raw) == exact, "entire original " + label + " capacity differs")
    return raw


def _callback_name(value):
    # A null PCSTR is the empty byte string. A non-null original string is
    # complete, <=32768 bytes, with exactly one terminating NUL.
    original = _hex(value, 32768, "callback name")
    _require(not original or original[-1] == 0 and b"\0" not in original[:-1],
             "source-impossible unterminated or embedded-NUL callback name")
    return original


def _qpc(value, metadata):
    _exact(value, session.QpcSample.__dataclass_fields__, "native QPC")
    sample = session.QpcSample(**value)
    _require((sample.epoch_id, sample.frequency_hz, sample.frequency_native_return, sample.frequency_native_error,
              sample.counter_native_return, sample.counter_native_error) ==
             (metadata["epoch_id"], metadata["frequency_hz"], 1, 0, 1, 0), "original native QPC query failed or differs")
    _require(sample.tick >= metadata["origin_tick"], "original QPC precedes independently frozen origin")
    return sample


def _protocol(frames, external, metadata):
    original_frames = frames
    _require(tuple(row.operation for row in frames[:2]) == ("invocation", "origin") and frames[-1].operation == "finish",
             "original invocation/origin and terminal finish must bound the complete archive")
    for row in frames:
        names = COLLECTOR_SCHEMAS.get(row.operation, STARTUP_SCHEMAS.get(row.operation))
        _require(names is not None, "unknown native archive operation")
        _exact(row.data(), names, row.operation)
        _require(row.operation not in ("error", "native_failure"), "original native failure packet retained; complete archive cannot pass")
        if row.operation == "output":
            _integer(row.data()["mask"], 0, 0xffffffff, "original output mask DWORD required")
            text = _hex(row.data()["text_hex"], 32768, "output callback")
            _require(text and text[-1] == 0 and b"\0" not in text[:-1], "entire original output C-string prefix required")
    _require(sum(len(row.raw) for row in frames) <= 16 * 1024 * 1024 and
             len(MAGIC) + sum(8 + len(row.metadata) for row in frames) <= MAX_TOTAL_METADATA,
             "original archive consumed failure-only allowance; cannot complete")
    # Asynchronous output callbacks remain retained, but are not substitutes
    # for a required synchronous operation or a native coherence observation.
    frames = tuple(row for row in frames if row.operation != "output")
    _require(tuple(row.operation for row in frames[:2]) == ("invocation", "origin"), "invocation/origin missing or reordered")
    expected = {name: getattr(external, name) for name in INVOCATION_FIELDS if name != "comparison_scope"}
    expected["comparison_scope"] = "asynchronous_only"
    _require(_canonical(frames[0].data()) == _canonical(expected), "native invocation differs from independent launch/source authority")
    origin = frames[1].data()
    _require(_canonical(origin["anchor"]) == _canonical({name: metadata[name] for name in ("epoch_id", "frequency_hz", "origin_tick", "origin_ns")}),
             "native original anchor differs from source-issued prelaunch request")
    origin_sample = _qpc(origin["sample"], metadata)
    _require(external.observed_host_exit_code == 0, "original external host exit failed")
    index = 2
    while index < len(frames) and frames[index].operation in ("setup", "launch", "callback_create", "callback_load", "callback_exception"):
        index += 1
    startup = frames[2:index]
    _require(startup, "original startup observations missing")
    setup = [row for row in startup if row.operation == "setup"]
    _require(tuple(row.data()["api_name"] for row in setup) == SETUP_NAMES,
             "source-owned startup API order is missing, repeated or incompatible")
    launches = [row for row in startup if row.operation == "launch"]
    _require(len(launches) == 1 and tuple(startup[:len(SETUP_NAMES) - 1]) == tuple(setup[:-1]) and
             startup.index(launches[0]) == len(SETUP_NAMES) - 1 and startup.index(launches[0]) < startup.index(setup[-1]) and
             all(row.operation.startswith("callback_") for row in startup[startup.index(launches[0]) + 1:startup.index(setup[-1])]),
             "original fixed setup must precede launch and CreateProcess receipt; only its callbacks may intervene")
    launch = launches[0].data()
    original_launch_path = _hex(launch["target_path_utf16le"], 65536, "target launch UTF16LE")
    _require(len(original_launch_path) % 2 == 0 and original_launch_path.endswith(b"\0\0"),
             "entire original launch UTF16LE string with terminator required")
    target_path = original_launch_path[:-2].decode("utf-16-le", "strict")
    image._path(target_path)
    _require(target_path.isascii() and type(launch["create_flags"]) is int and launch["create_flags"] == 0x08000002 and
             _hex(launch["command_hex"], 32768, "original target command") == ("\"" + target_path + "\"").encode("ascii") + b"\0",
             "source-owned original launch command/flags differ")
    _require(tuple(row.operation for row in frames[index:index + 5]) ==
             ("wait_event", "event", "peb", "held", "startup_owner"), "original startup wait/event/PEB/held/owner sequence incomplete")
    creates = [row for row in startup if row.operation == "callback_create"]
    exceptions = [row for row in startup if row.operation == "callback_exception"]
    _require(len(creates) == len(exceptions) == 1, "unique original create/initial exception callbacks required")
    _require(startup.index(launches[0]) < startup.index(creates[0]) < startup.index(exceptions[0]),
             "original create/initial exception callback precedes launch or is reordered")
    create = creates[0].data()
    for name in CREATE_FIELDS:
        if name.endswith("_hex"): _callback_name(create[name])
        else: _integer(create[name], -(1 << 31) if name.endswith("_return") else 0,
                       0xffffffff if name in ("module_size", "pid", "tid", "checksum", "timestamp") or name.endswith(("_return", "_error")) else (1 << 64) - 1,
                       "original create callback scalar differs")
    _require(create["duplicate_process_return"] != 0 and create["duplicate_thread_return"] != 0 and
             create["duplicate_process_error"] == create["duplicate_thread_error"] == create["pid_error"] == create["tid_error"] == 0 and
             0 < create["owned_process_handle"] < (1 << 64) - 1 and
             0 < create["owned_thread_handle"] < (1 << 64) - 1 and
             create["owned_process_handle"] != create["owned_thread_handle"], "original callback handle retention failed")
    exception = exceptions[0].data()
    original_record = _hex(exception["record_hex"], 152, "EXCEPTION_RECORD64", exact=152)
    _require(struct.unpack_from("<I", original_record)[0] == 0x80000003 and type(exception["first_chance"]) is int and
             exception["first_chance"] == 1, "original callback is not the natural initial breakpoint observation")
    initial_qpc = _qpc(exception["qpc"], metadata)
    _require(origin_sample.tick <= initial_qpc.tick, "original callback QPC precedes the earlier native origin observation")
    held = frames[index + 3].data()
    held_sample = _qpc(held["qpc"], metadata)
    _require(type(held["initial_exception_sequence"]) is int and held["initial_exception_sequence"] == exceptions[0].sequence and
             initial_qpc.tick <= held_sample.tick <= initial_qpc.tick + 20 * metadata["frequency_hz"],
             "original later held sample precedes/exceeds its unchanged callback QPC")
    for row in startup:
        value = row.data()
        if row.operation == "setup":
            _integer(value["hresult"], -(1 << 31), 0xffffffff, "original setup HRESULT required")
            _require(type(value["api_name"]) is str and value["hresult"] == 0 and
                     (value["value"] is None or type(value["value"]) is int and 0 <= value["value"] <= (1 << 64) - 1),
                     "original setup API/scalar failed")
            if value["api_name"] in SETUP_NAMES[:4]:
                _require(type(value["value"]) is int and 0 < value["value"] < (1 << 64) - 1,
                         "original retained COM interface pointer missing")
            elif value["api_name"] == "GetEngineOptions":
                _require(type(value["value"]) is int and value["value"] <= 0xffffffff and
                         value["value"] & 0x20 and value["value"] & 0x1000,
                         "original engine options lack initial-break/shell restriction")
            else: _require(value["value"] is None, "original setup has an unexpected output scalar")
        if row.operation == "callback_load":
            for name in LOAD_FIELDS:
                if name.endswith("_hex"): _callback_name(value[name])
                else: _integer(value[name], 0, (1 << 64) - 1 if name in ("image_handle", "base_offset") else 0xffffffff,
                               "original callback load scalar differs")
    wait, event, peb = (row.data() for row in frames[index:index + 3])
    _require(type(wait["hresult"]) is int and wait["hresult"] == 0 and type(wait["flags"]) is int and wait["flags"] == 0 and
             type(wait["timeout_ms"]) is int and wait["timeout_ms"] == 15000, "original fixed WaitForEvent failed or is incompatible")
    _require(type(event["hresult"]) is int and event["hresult"] == 0 and type(event["type"]) is int and event["type"] == 2,
             "original last event is not the initial exception")
    extra = _hex(event["extra_hex"], 256, "last-event extra", exact=256)
    _hex(event["description_hex"], 1024, "last-event description", exact=1024)
    for name in ("engine_pid", "engine_tid", "extra_used", "description_used"):
        _integer(event[name], 0, 0xffffffff, "original last-event DWORD differs")
    _require(event["extra_used"] == 160 and event["description_used"] <= 1024,
             "original last-event returned lengths overflow retained capacities")
    def exception_fields(raw):
        code, flags, pointer, address, count = struct.unpack_from("<IIQQI", raw)
        _require(count <= 15, "original exception parameter count exceeds native array")
        return code, flags, pointer, address, count, struct.unpack_from("<" + "Q" * count, raw, 32)
    _require(exception_fields(extra[:152]) == exception_fields(original_record) and
             struct.unpack_from("<I", extra, 152)[0] == exception["first_chance"],
             "original last-event exception does not match callback semantics")
    _require(type(peb["hresult"]) is int and peb["hresult"] == 0, "original PEB query failed")
    _integer(peb["address"], 0x10000, image.USER_LIMIT - 12, "original bounded x86 PEB required")
    _require(tuple(row.operation for row in frames[-3:]) == ("stop", "cleanup", "finish"), "native stop/cleanup/finish missing or reordered")
    calls = frames[index + 5:-3]
    _require(calls and calls[0].operation == calls[-1].operation == "counter" and
             all(row.operation in COLLECTOR_SCHEMAS for row in calls), "complete original collector stream required")
    previous = held_sample.tick
    for row in calls:
        if row.operation == "counter":
            sample = _qpc(row.data(), metadata)
            _require(previous <= sample.tick <= initial_qpc.tick + 20 * metadata["frequency_hz"], "original held QPC order/duration failed")
            previous = sample.tick
    stop = frames[-3].data()
    _require(type(stop["end_session_hresult"]) is int and stop["end_session_hresult"] == 0,
             "original EndSession failed")
    status = image.NativeQuery(**_exact(stop["execution_status"], ("name", "hresult", "value"), "post-stop status"))
    _require((status.name, status.hresult, status.value) == (image.PHASE_QUERY_NAMES[0], 0, 7), "original post-stop status differs or failed")
    stopped = _qpc(stop["qpc"], metadata)
    _require(previous <= stopped.tick <= initial_qpc.tick + 20 * metadata["frequency_hz"], "physical held work exceeded original checkpoint or QPC order")
    cleanup = frames[-2].data()
    for name, value in cleanup.items():
        _integer(value, -(1 << 31) if name.endswith(("_return", "_close", "_hresult")) else 0,
                 (1 << 64) - 1 if name.endswith("filetime") else 0xffffffff, "original cleanup scalar differs")
    _require(cleanup["event_callbacks_hresult"] == cleanup["output_callbacks_hresult"] == 0,
             "original callbacks were not successfully unregistered before finish")
    _require(cleanup["target_pid_error"] == 0 and cleanup["target_wait"] == 0 and cleanup["target_wait_error"] == 0 and
             cleanup["target_times_return"] != 0 and cleanup["target_times_error"] == 0 and
             cleanup["target_exit_return"] != 0 and cleanup["target_exit_error"] == 0 and
             cleanup["target_exit_filetime"] >= cleanup["target_creation_filetime"] > 0,
             "original retained target wait/exit/time cleanup failed")
    for role in ("target", "thread", "controller", "debugger"):
        _require(cleanup[role + "_close"] != 0 and cleanup[role + "_close_error"] == 0, "original retained native handle close failed")
    finish = frames[-1].data()
    metadata_bytes = len(MAGIC) + sum(8 + len(row.metadata) for row in original_frames[:-1])
    raw_bytes = sum(len(row.raw) for row in original_frames[:-1])
    _require(_canonical(finish) == _canonical(dict(status="complete", frame_count=len(original_frames) - 1, raw_bytes=raw_bytes,
                            metadata_bytes=metadata_bytes, comparison_scope="asynchronous_only")), "original finish counters/status/scope differ")
    return create, event, peb, initial_qpc, frames[index + 4], cleanup, target_path


@dataclass(frozen=True, eq=False, slots=True, weakref_slot=True)
class ParsedArchive:
    """Readable original archive; source issuer identity grants only replay."""
    original_archive: bytes
    frames: tuple[OriginalFrame, ...]


@dataclass(frozen=True)
class _ArchiveContext:
    original_archive: bytes
    frames: tuple[OriginalFrame, ...]
    check_sources: object


def _api_factory():
    import hidden_soak_loader_native as native
    inspect_request = native.inspect_request
    frames_reader, protocol_checker, adapter_class = _frames, _protocol, OfflineAdapter
    imported_source = _IMPORTED_SOURCE_BYTES
    issued = {}
    def source_identity(expected_hash):
        _require(_sha(imported_source) == expected_hash and SOURCE.read_bytes() == imported_source,
                 "imported adapter bytes differ from source-issued binding or current source")
    def seal(frames):
        return tuple((row.sequence, row.operation, row.metadata, row.raw, row.offset) for row in frames)
    def parse_archive(raw, authority, request):
        frames = ()
        try:
            _require(type(raw) is bytes and type(authority) is ArchiveAuthority, "independent typed archive authority required")
            authority = ArchiveAuthority(**asdict(authority))
            _require((_sha(raw), len(raw)) == (authority.archive_sha256, authority.archive_size), "independent original archive binding differs")
            facts = inspect_request(request)
            facts.check_sources()
            metadata = json.loads(facts.metadata_json, object_pairs_hook=_object)
            _require(_canonical(metadata).decode("ascii") == facts.metadata_json, "source-issued facts metadata is noncanonical")
            _exact(metadata, FACT_FIELDS, "source-issued request facts")
            source_identity(metadata["adapter_source_sha256"])
            _require(type(facts.request_bytes) is type(facts.host_source) is bytes and
                     _sha(facts.request_bytes) == metadata["request_sha256"] and _sha(facts.host_source) == metadata["host_source_sha256"],
                     "source-issued request/native host bytes differ")
            expected = dict(request_sha256=authority.request_sha256, candidate_sha256=authority.candidate_file_sha256,
                host_source_sha256=authority.host_source_sha256, native_source_sha256=authority.native_source_sha256,
                adapter_source_sha256=authority.adapter_source_sha256, run_id=authority.run_id,
                checkpoint_id=authority.checkpoint_id, epoch_id=authority.epoch_id, controller_pid=authority.controller_pid)
            _require(all(metadata[name] == value for name, value in expected.items()) and
                     _sha(SOURCE.read_bytes()) == authority.adapter_source_sha256, "independent source/launch/candidate/request binding differs")
            frames = frames_reader(raw)
            observed = protocol_checker(frames, authority, metadata)
            facts.check_sources()
            source_identity(authority.adapter_source_sha256)
            parsed = ParsedArchive(raw, frames)
            identity = id(parsed)
            def retire(reference):
                if identity in issued and issued[identity][0] is reference: del issued[identity]
            issued[identity] = (weakref.ref(parsed, retire), raw, frames, facts, metadata, observed, authority, seal(frames))
            return parsed
        except ArchiveError: raise
        except Exception as error: raise ArchiveError(type(error).__name__ + ": " + str(error), raw, frames) from error
    def create_adapter(parsed, authority, anchor):
        entry = issued.get(id(parsed))
        _require(type(parsed) is ParsedArchive and entry is not None and entry[0]() is parsed,
                 "live source-issued parsed archive identity required")
        _, raw, frames, facts, metadata, observed, external, sealed = entry
        source_identity(metadata["adapter_source_sha256"])
        _require(parsed.original_archive is raw and parsed.frames is frames, "source-issued original archive was altered")
        _require(type(authority) is image.LoaderAuthority and type(anchor) is session.QpcAnchor,
                 "independent typed loader/QPC authority required")
        create, event, peb, held, startup_owner, cleanup, target_path = observed
        for name in ("profile", "resolution", "stage", "recipe_revision", "probe_sha256", "source_closure_sha256"):
            _require(getattr(authority, name) == metadata[name], "independent loader/source recipe differs")
        _require((authority.run_id, authority.checkpoint_id, authority.clock_epoch, authority.controller.pid, authority.candidate_sha256) ==
                 (external.run_id, external.checkpoint_id, external.epoch_id, external.controller_pid, external.candidate_file_sha256),
                 "independent loader launch binding differs")
        _require((authority.debugger.image_sha256, authority.target.pid, authority.primary_tid, authority.image_base,
                  authority.peb_address, authority.engine_pid, authority.engine_tid) ==
                 (external.host_file_sha256, create["pid"], create["tid"], create["base_offset"], peb["address"], event["engine_pid"], event["engine_tid"]),
                 "independent loader generation/PEB/base/selected IDs differ from native observations")
        _require(create["module_size"] == metadata["image_size"],
                 "original create callback module extent differs from source-issued canonical image size")
        _require(image._path(target_path) == authority.target.image_path, "original launched target pathname differs from independent generation")
        _require((anchor.epoch_id, anchor.frequency_hz, anchor.origin_tick, anchor.origin_ns, anchor.held_start_tick) ==
                 (metadata["epoch_id"], metadata["frequency_hz"], metadata["origin_tick"], metadata["origin_ns"], held.tick),
                 "independent prelaunch/held QPC anchor differs")
        _require((authority.clock_origin_ns, authority.checkpoint_start_ns) ==
                 (anchor.origin_ns, session.project(anchor, anchor.held_start_tick).lower_ns), "independent unchanged held ns mapping differs")
        _require((cleanup["target_pid"], cleanup["target_creation_filetime"]) ==
                 (authority.target.pid, authority.target.creation_filetime), "original cleanup targets another/reused generation")
        def check():
            facts.check_sources()
            source_identity(external.adapter_source_sha256)
            _require(
                     parsed.original_archive is raw and parsed.frames is frames and seal(frames) == sealed,
                     "source-issued archive/source changed")
        context = _ArchiveContext(raw, frames, check)
        adapter = adapter_class(context, authority, anchor)
        # Startup owner remains an original separate observation, not copied
        # authority. Validate all three native generations before any read.
        packet = startup_owner.data()
        for name in ("probe_sequence", "breakpoint_sequence", "command_sequence"):
            _integer(packet[name], 0, (1 << 63) - 1, "original startup owner sequence must be an integer")
        for role, parent in (("controller", None), ("debugger", authority.controller), ("target", authority.debugger)):
            _generation(packet[role], getattr(authority, role), parent)
        _require((packet["run_id"], packet["checkpoint_id"], packet["clock_epoch"], packet["probe_sequence"],
                  packet["breakpoint_sequence"], packet["command_sequence"]) ==
                 (authority.run_id, authority.checkpoint_id, authority.clock_epoch, 0, 0, 0), "original startup owner sequences differ")
        check()
        return adapter
    def collect_archive(parsed, authority, anchor):
        adapter = create_adapter(parsed, authority, anchor)
        entry = issued[id(parsed)]
        result = entry[3].collect(authority, anchor, adapter)
        if result.report().get("supplied_receipt_collection_passed"):
            try: adapter.require_consumed()
            except Exception as error:
                raise ArchiveError(str(error), parsed.original_archive, parsed.frames, result) from error
        return result
    return parse_archive, create_adapter, collect_archive


# The request issuer is captured once. A later public alias cannot issue an
# arbitrary request or supply a private preparation closure to this parser.
parse_archive, create_adapter, collect_archive = _api_factory()
