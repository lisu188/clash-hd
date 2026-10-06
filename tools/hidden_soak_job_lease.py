"""WIN64-only ordered job-receipt preparation; no native adapter or job proof.

This pure collector/replay retains supplied Win32 buffers and original scalars.
It never launches, queries, closes, writes artifacts, or upgrades legacy cleanup
booleans. The frozen host must acquire a future instrumented native adapter.
The required order is a future protocol, not an attestation that the unchanged
owned_hidden_process host already emits or follows every recorded operation.
Snapshots here cover startup and cleanup only, not the per-frame/whole-run
schedule. A replay pass cannot establish genuine job issuance or no breakaways.
The adapter must retain original oversized buffers/errors before constructing
these bounded records; constructor rejection itself cannot prove retention.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
import struct

import hidden_soak_process_lease as process
import hidden_soak_running_time as clock

MODULE_PATH = Path(__file__).resolve()
SOURCE = str(MODULE_PATH)
SCHEMA = "hidden_soak_job_receipts_win64_v1"
FROZEN_HOST_SHA256 = "c3861e3495c2ad4e11cb92213ab6f20623096683b79cbef79ae767aec4f4e00c"
FROZEN_PROCESS_SHA256 = "abe72430a334cc05814b3cd2eb792716b5ee6bf7f11d31a0a766870abf1d163b"
FROZEN_CLOCK_SHA256 = "ce9d3869f7114a9663fe46f0a0297b47eb16a1f2931a3018b6f559610b25d66d"
U32, U64 = (1 << 32) - 1, (1 << 64) - 1
MAX_EVENTS, MAX_JSON_BYTES, MAX_SOURCE_BYTES = 4096, 4 * 1024 * 1024, 8 * 1024 * 1024
MAX_RAW_BUFFER, MAX_ERROR_BYTES, MAX_PIDS, MAX_DRAIN_PAIRS = 4096, 4096, 64, 512
LIMIT_BYTES, ACCOUNTING_BYTES, PID_BUFFER_BYTES = 144, 48, 8 + 8 * MAX_PIDS
DRAIN_SECONDS, CREATE_FLAGS, OPEN_ACCESS = 5, 0x08080404, 0x00101001
ROLES = ("desktop", "job", "stdin", "stdout_duplicate", "debugger_process", "debugger_thread", "candidate_process")
KINDS = ("desktop", "job", "limit_set", "limit_query", "stdin", "stdout", "launch", "close",
         "identity", "assign", "membership", "resume", "target_open", "pids", "accounting",
         "terminate", "wait", "finish", "unknown")
APIS = dict(desktop="CreateDesktopW", job="CreateJobObjectW", limit_set="SetInformationJobObject",
    limit_query="QueryInformationJobObject", stdin="CreateFileW", stdout="DuplicateHandle", launch="CreateProcessW",
    identity="GetProcessId/QueryFullProcessImageNameW/GetProcessTimes/WaitForSingleObject/GetExitCodeProcess",
    assign="AssignProcessToJobObject", membership="IsProcessInJob", resume="ResumeThread", target_open="OpenProcess",
    pids="QueryInformationJobObject", accounting="QueryInformationJobObject", terminate="TerminateJobObject",
    wait="WaitForSingleObject/GetProcessId/QueryFullProcessImageNameW/GetProcessTimes/GetExitCodeProcess", finish="")
FALSE_CLAIMS = {name: False for name in (
    "passed", "native_producer_provenance_verified", "no_breakaway_job_verified", "host_cleanup_complete",
    "native_job_cleanup_verified", "per_frame_membership_verified", "whole_run_membership_verified",
    "loaded_candidate_verified", "running_duration_verified", "host_clock_coverage_verified",
    "runtime_acceptance", "release_acceptance", "manual_input_verified", "promotion_ready", "stable")}


def _require(value, message):
    if not value:
        raise ValueError(message)


def _int(value, maximum, label, minimum=0):
    _require(type(value) is int and minimum <= value <= maximum, label)


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")


def policy():
    return dict(controller_abi="WIN64_only", pointer_bytes=8, limit_information_class=9,
        limit_bytes=LIMIT_BYTES, flags_offset=16, required_flags=0x2000, forbidden_breakaway_flags=0x1800,
        accounting_information_class=1, accounting_bytes=ACCOUNTING_BYTES,
        pid_information_class=3, pid_buffer_bytes=PID_BUFFER_BYTES, max_pids=MAX_PIDS,
        pid_returned_length="8+8*NumberOfProcessIdsInList; full_original_capacity_buffer_retained",
        win32_result_policy="original_signed32_or_unsigned32_BOOL; nonzero_success; observed_GetLastError_retained_not_success_predicate",
        create_flags=CREATE_FLAGS, open_target_access=OPEN_ACCESS, resume_previous_count=1,
        drain_seconds=DRAIN_SECONDS, max_drain_pairs=MAX_DRAIN_PAIRS, max_events=MAX_EVENTS,
        max_json_bytes=MAX_JSON_BYTES, max_raw_buffer_bytes=MAX_RAW_BUFFER, max_error_bytes=MAX_ERROR_BYTES,
        scope="startup_and_precleanup_supplied_receipts_only; no_per_frame_whole_run_or_native_proof")


def retention_allowance():
    return dict(transcript_bytes=MAX_JSON_BYTES, atomic_temporary_bytes=MAX_JSON_BYTES,
        additional_peak_bytes=2 * MAX_JSON_BYTES, included_in_frozen_frame_budget=False,
        scope="known_serialized_owned_bytes_only; source_native_RAM_and_other_producer_costs_additional")


@dataclass(frozen=True)
class HandleToken:
    role: str
    token: str

    def __post_init__(self):
        _require(type(self.role) is str and self.role in ROLES, "source-owned handle role required")
        clock._token(self.token)


@dataclass(frozen=True)
class JobAuthority:
    run: process.RunAuthority
    debugger: process.Generation
    target: process.Generation
    debugger_primary_tid: int
    clock: clock.ClockAuthority
    host_source: process.SourcePin
    handles: tuple[HandleToken, ...]
    caller_stdout_handle: int
    desktop_name: str

    def __post_init__(self):
        _require(type(self.run) is process.RunAuthority and type(self.debugger) is type(self.target) is process.Generation,
                 "typed independently frozen run/generations required")
        _require(type(self.clock) is clock.ClockAuthority and type(self.host_source) is process.SourcePin,
                 "typed independently frozen clock/host source required")
        _require(self.run.profile in clock.PROFILES and self.run.resolution in clock.PRESETS, "only canonical profile/presets admitted")
        _require(len({self.run.controller.pid, self.debugger.pid, self.target.pid}) == 3 and
                 self.run.controller.creation_filetime <= self.debugger.creation_filetime <= self.target.creation_filetime,
                 "aliased/reused parent generations")
        for role, generation in (("debugger", self.debugger), ("candidate", self.target)):
            image = next(row for row in self.run.images if row.role == role)
            _require((image.path, image.sha256) == (generation.image_path, generation.image_sha256), "frozen image authority differs")
        _int(self.debugger_primary_tid, U32, "invalid debugger CreateProcess primary TID", 1)
        _int(self.caller_stdout_handle, U64 - 1, "invalid protected caller stdout handle", 1)
        _require(type(self.desktop_name) is str and self.desktop_name.startswith("ClashOwnedHost_") and
                 len(self.desktop_name) <= 256 and self.desktop_name.isascii() and
                 all(c.isalnum() or c == "_" for c in self.desktop_name), "independent private desktop name required")
        _require(type(self.handles) is tuple and tuple(row.role for row in self.handles) == ROLES and
                 all(type(row) is HandleToken for row in self.handles) and
                 len({row.token for row in self.handles}) == len(ROLES), "complete distinct retained handle tokens required")
        pins = {row.path: row.sha256 for row in self.run.source_pins}
        _require(process._path(SOURCE) in pins and pins.get(self.host_source.path) == self.host_source.sha256,
                 "fixed component/native host source pins required")
        excluded = ("hidden_soak_job_lease.py", "hidden_soak_running_time.py", "hidden_soak_process_lease.py", "owned_hidden_process.py")
        _require(not self.host_source.path.endswith(tuple("\\" + name for name in excluded)), "instrumented native host cannot substitute a preparatory component")
        for suffix, expected in (("owned_hidden_process.py", FROZEN_HOST_SHA256),
                                 ("hidden_soak_process_lease.py", FROZEN_PROCESS_SHA256),
                                 ("hidden_soak_running_time.py", FROZEN_CLOCK_SHA256)):
            found = [row for row in self.run.source_pins if row.path.endswith("\\tools\\" + suffix)]
            _require(len(found) == 1 and found[0].sha256 == expected, "frozen predecessor source differs")


@dataclass(frozen=True)
class RawIdentity:
    """Original scalar outputs; failed/empty/invalid identities remain representable."""
    pid: int
    pid_error: int
    image_path: str
    image_sha256: str
    path_return: int
    path_error: int
    creation_filetime: int
    exit_filetime: int
    times_return: int
    times_error: int
    parent_pid: int
    wait_result: int
    exit_return: int
    exit_error: int
    exit_code: int

    def __post_init__(self):
        for name in ("pid", "pid_error", "path_error", "times_error", "parent_pid", "wait_result", "exit_error", "exit_code"):
            _int(getattr(self, name), U32, "invalid original native identity DWORD")
        for name in ("path_return", "times_return", "exit_return"):
            _int(getattr(self, name), U32, "invalid original native identity BOOL", -(1 << 31))
        for name in ("creation_filetime", "exit_filetime"):
            _int(getattr(self, name), U64, "invalid original native FILETIME")
        _require(type(self.image_path) is str and len(self.image_path) <= 32768, "bounded original image path required")
        _require(type(self.image_sha256) is str and (not self.image_sha256 or process._digest(self.image_sha256)), "original file digest required")


@dataclass(frozen=True)
class RawJobEvent:
    sequence: int
    kind: str
    run_id: str
    source_snapshot_sha256: str
    begin: clock.ClockSample
    end: clock.ClockSample
    api_name: str = ""
    token: str = ""
    handle_value: int | None = None
    related_token: str = ""
    related_handle_value: int | None = None
    borrowed_handle_value: int | None = None
    native_return: int | None = None
    native_error: int = 0
    value: int | None = None
    flags: int | None = None
    inherit_handles: int | None = None
    process_pid: int | None = None
    timeout_milliseconds: int | None = None
    membership_result: int | None = None
    object_name: str | None = None
    inherited_tokens: tuple[str, ...] = ()
    information_class: int | None = None
    requested_bytes: int | None = None
    returned_bytes: int | None = None
    input_buffer: bytes = b""
    output_buffer: bytes = b""
    phase: str = ""
    identity_before: RawIdentity | None = None
    identity_after: RawIdentity | None = None
    error: str = ""

    def __post_init__(self):
        _int(self.sequence, MAX_EVENTS, "invalid original event sequence", 1)
        _require(type(self.kind) is str and self.kind in KINDS, "typed source-owned native operation required")
        _require(type(self.api_name) is str and len(self.api_name) <= 256, "bounded original API name required")
        clock._token(self.run_id); process._digest(self.source_snapshot_sha256)
        _require(type(self.begin) is type(self.end) is clock.ClockSample, "typed original QPC samples required")
        for token in (self.token, self.related_token):
            if token: clock._token(token)
        for name in ("handle_value", "related_handle_value", "borrowed_handle_value"):
            if getattr(self, name) is not None: _int(getattr(self, name), U64, "original native HANDLE bits required", -(1 << 63))
        if self.native_return is not None: _int(self.native_return, U32, "original native BOOL required", -(1 << 31))
        for name in ("inherit_handles", "membership_result"):
            if getattr(self, name) is not None: _int(getattr(self, name), U32, "original native BOOL input/output required", -(1 << 31))
        for name in ("native_error", "value", "flags", "process_pid", "timeout_milliseconds", "information_class", "requested_bytes", "returned_bytes"):
            if getattr(self, name) is not None: _int(getattr(self, name), U32, "original native DWORD required")
        _require(self.object_name is None or type(self.object_name) is str and len(self.object_name) <= 32768, "bounded original object name required")
        _require(type(self.inherited_tokens) is tuple and len(self.inherited_tokens) <= len(ROLES), "original bounded inherited token list required")
        for token in self.inherited_tokens: clock._token(token)
        for name in ("input_buffer", "output_buffer"):
            _require(type(getattr(self, name)) is bytes and len(getattr(self, name)) <= MAX_RAW_BUFFER, "bounded entire original native buffer required")
        _require(type(self.phase) is str and self.phase in ("", "setup", "startup", "precleanup", "drain"), "source-owned query phase required")
        _require(all(value is None or type(value) is RawIdentity for value in (self.identity_before, self.identity_after)), "typed original native identity receipts required")
        _require(type(self.error) is str and len(self.error.encode("utf-8")) <= MAX_ERROR_BYTES, "bounded complete original error required")


@dataclass(frozen=True)
class TranscriptBinding:
    authority_sha256: str
    source_snapshot_sha256: str
    artifact_sha256: str
    artifact_size: int

    def __post_init__(self):
        for value in (self.authority_sha256, self.source_snapshot_sha256, self.artifact_sha256): process._digest(value)
        _int(self.artifact_size, MAX_JSON_BYTES, "bounded independently retained original transcript required", 1)


@dataclass(frozen=True)
class ReplayResult:
    report_json: bytes
    original_transcript: bytes

    def report(self):
        return json.loads(self.report_json)


def authority_sha256(authority):
    _require(type(authority) is JobAuthority, "typed independent job authority required")
    return _sha(_canonical(asdict(authority)))


def source_snapshot_sha256(authority):
    return _sha(_canonical([asdict(row) for row in authority.run.source_pins]))


def _sources(authority, source_bytes):
    _require(type(source_bytes) is dict and set(source_bytes) == {row.path for row in authority.run.source_pins}, "exact independently supplied source bytes required")
    _require(all(type(data) is bytes for data in source_bytes.values()) and sum(map(len, source_bytes.values())) <= MAX_SOURCE_BYTES, "bounded original source inventory required")
    for row in authority.run.source_pins: _require(_sha(source_bytes[row.path]) == row.sha256, "original source identity changed")
    own = next(row.sha256 for row in authority.run.source_pins if row.path == process._path(SOURCE))
    _require(_sha(MODULE_PATH.read_bytes()) == own, "loaded job component changed")
    for name, expected in (("owned_hidden_process.py", FROZEN_HOST_SHA256),
                           ("hidden_soak_process_lease.py", FROZEN_PROCESS_SHA256),
                           ("hidden_soak_running_time.py", FROZEN_CLOCK_SHA256)):
        path = MODULE_PATH.parent / name
        _require(path.resolve(strict=True) == path and not path.is_symlink() and
                 not getattr(path, "is_junction", lambda: False)() and
                 not getattr(path.stat(), "st_file_attributes", 0) & 0x400 and _sha(path.read_bytes()) == expected,
                 "canonical frozen host/clock/process source changed")


def _wire(event):
    value = asdict(event)
    for name in ("input_buffer", "output_buffer"): value[name] = getattr(event, name).hex()
    return value


class TranscriptLimitError(ValueError):
    def __init__(self, message, report, event):
        super().__init__(message)
        self.report, self.event = report, event


class TranscriptCollector:
    """Provided-receipt serialization only; no native calls or artifact I/O."""
    def __init__(self, authority, source_bytes):
        _require(type(authority) is JobAuthority, "typed independent job authority required")
        _sources(authority, source_bytes)
        self.authority, self.source_bytes, self.events = authority, dict(source_bytes), []
        self.receipt_bytes = len(_canonical(self.report()))

    def report(self):
        return dict(schema=SCHEMA, authority_sha256=authority_sha256(self.authority), source_snapshot_sha256=source_snapshot_sha256(self.authority),
                    policy=policy(), events=[_wire(row) for row in self.events], claims=dict(FALSE_CLAIMS))

    def record(self, event):
        _require(type(event) is RawJobEvent, "typed entire original native receipt required")
        try:
            _sources(self.authority, self.source_bytes)
        except Exception as error:
            raise TranscriptLimitError("original attempted receipt source guard failed: " + str(error), self.report(), event) from error
        additional = len(_canonical(_wire(event))) + bool(self.events)
        if len(self.events) >= MAX_EVENTS or self.receipt_bytes + additional > MAX_JSON_BYTES:
            raise TranscriptLimitError("bounded original transcript capacity exceeded", self.report(), event)
        self.events.append(event); self.receipt_bytes += additional

    def encode(self):
        _sources(self.authority, self.source_bytes)
        data = _canonical(self.report())
        _require(len(data) == self.receipt_bytes <= MAX_JSON_BYTES, "serialized retention count differs")
        return data


def _exact(value, fields, label):
    _require(type(value) is dict and set(value) == set(fields), "exact " + label + " fields required")
    return value


def _event(value):
    value = dict(_exact(value, RawJobEvent.__dataclass_fields__, "original job receipt"))
    for name in ("begin", "end"):
        value[name] = clock.ClockSample(**_exact(value[name], clock.ClockSample.__dataclass_fields__, "original clock sample"))
    for name in ("identity_before", "identity_after"):
        if value[name] is not None: value[name] = RawIdentity(**_exact(value[name], RawIdentity.__dataclass_fields__, "original identity"))
    for name in ("input_buffer", "output_buffer"):
        data = value[name]
        _require(type(data) is str and len(data) <= 2 * MAX_RAW_BUFFER and len(data) % 2 == 0 and
                 all(c in "0123456789abcdef" for c in data), "canonical entire original raw buffer required")
        value[name] = bytes.fromhex(data)
    _require(type(value["inherited_tokens"]) is list, "original inherited token list required")
    value["inherited_tokens"] = tuple(value["inherited_tokens"])
    return RawJobEvent(**value)


def _identity(raw, generation, parent_pid, *, live=None):
    _require(type(raw) is RawIdentity, "original retained-handle identity query missing")
    _require(raw.pid == generation.pid and raw.path_return != 0 and raw.times_return != 0 and raw.exit_return != 0,
             "native identity query failed or returned another PID")
    _require((process._path(raw.image_path), raw.image_sha256, raw.creation_filetime, raw.parent_pid) ==
             (generation.image_path, generation.image_sha256, generation.creation_filetime, parent_pid), "retained native generation/source parent differs")
    _require(raw.wait_result in (0, 258), "retained native wait failed")
    if raw.wait_result == 258:
        _require(raw.exit_filetime == 0 and raw.exit_code == 259, "live native identity contains an exit")
    else:
        _require(raw.exit_filetime >= generation.creation_filetime, "signalled native identity lacks exit time")
    if live is not None: _require((raw.wait_result == 258) is live, "retained native process liveness differs")
    return raw.wait_result == 258


def _query(row, kind):
    size, info = {"limit_query": (LIMIT_BYTES, 9), "pids": (PID_BUFFER_BYTES, 3), "accounting": (ACCOUNTING_BYTES, 1)}[kind]
    _require(row.native_return is not None and row.native_return != 0, "original job query failed")
    _require(row.information_class == info and row.requested_bytes == size and len(row.output_buffer) == size,
             "job query class/capacity or entire original buffer differs")
    if kind == "limit_query":
        _require(row.returned_bytes == size and struct.unpack_from("<I", row.output_buffer, 16)[0] == 0x2000,
                 "job query limits/readback allow breakaway or are incomplete")
        return None
    if kind == "accounting":
        _require(row.returned_bytes == size, "original job accounting length is incomplete")
        times = struct.unpack_from("<4q", row.output_buffer)
        faults, total, active, terminated = struct.unpack_from("<4I", row.output_buffer, 32)
        _require(all(value >= 0 for value in times) and active <= total and terminated <= total,
                 "invalid original job accounting counters")
        return dict(times=times, page_faults=faults, total=total, active=active, terminated_by_limit=terminated)
    assigned, count = struct.unpack_from("<II", row.output_buffer)
    _require(assigned == count <= MAX_PIDS and row.returned_bytes == 8 + 8 * count,
             "original PID list is shortened, overflowing or not complete")
    pids = struct.unpack_from("<" + "Q" * count, row.output_buffer, 8)
    _require(all(0 < pid <= U32 for pid in pids) and len(set(pids)) == len(pids), "invalid/duplicate native PID slots")
    return pids


def replay(data, authority, binding, source_bytes):
    """Recompute only the supplied ordered protocol; native cleanup stays false."""
    failures, handles, closed, parsed = [], {}, set(), []
    def failure(message): failures.append(message)
    try:
        _require(type(authority) is JobAuthority and type(binding) is TranscriptBinding, "independent typed replay authority required")
        _sources(authority, source_bytes)
        _require(type(data) is bytes and 0 < len(data) <= MAX_JSON_BYTES, "bounded original transcript bytes required")
        _require((binding.authority_sha256, binding.source_snapshot_sha256, binding.artifact_sha256, binding.artifact_size) ==
                 (authority_sha256(authority), source_snapshot_sha256(authority), _sha(data), len(data)), "independently retained original transcript binding differs")
        def unique(pairs):
            result = {}
            for key, value in pairs:
                _require(key not in result, "duplicate original JSON field"); result[key] = value
            return result
        report = json.loads(data, object_pairs_hook=unique, parse_constant=lambda value: (_ for _ in ()).throw(ValueError("nonfinite JSON")))
        _require(_canonical(report) == data, "noncanonical original transcript")
        _exact(report, ("schema", "authority_sha256", "source_snapshot_sha256", "policy", "events", "claims"), "source-owned transcript")
        _require(report["schema"] == SCHEMA and report["authority_sha256"] == authority_sha256(authority) and
                 report["source_snapshot_sha256"] == source_snapshot_sha256(authority) and
                 _canonical(report["policy"]) == _canonical(policy()) and _canonical(report["claims"]) == _canonical(FALSE_CLAIMS), "source-owned schema/policy/binding/false claims changed")
        _require(type(report["events"]) is list and 0 < len(report["events"]) <= MAX_EVENTS, "bounded original event list required")
        events = tuple(_event(value) for value in report["events"])
        tokens = {row.role: row.token for row in authority.handles}
        parents = dict(debugger_process=authority.run.controller.pid, candidate_process=authority.debugger.pid)
        generations = dict(debugger_process=authority.debugger, candidate_process=authority.target)
        latest = {role: True for role in generations}
        setup = [("desktop", "desktop", ""), ("job", "job", ""), ("limit_set", "job", ""), ("limit_query", "job", "setup"),
                 ("stdin", "stdin", ""), ("stdout", "stdout_duplicate", ""), ("launch", "debugger_process", ""),
                 ("close", "stdout_duplicate", ""), ("close", "stdin", ""), ("identity", "debugger_process", "startup"),
                 ("assign", "debugger_process", ""), ("membership", "debugger_process", "startup"),
                 ("resume", "debugger_thread", ""), ("close", "debugger_thread", ""), ("target_open", "candidate_process", ""),
                 ("identity", "candidate_process", "startup"), ("membership", "candidate_process", "startup"),
                 ("limit_query", "job", "startup"), ("pids", "job", "startup"), ("accounting", "job", "startup"),
                 ("identity", "debugger_process", "precleanup"), ("identity", "candidate_process", "precleanup"),
                 ("membership", "debugger_process", "precleanup"), ("membership", "candidate_process", "precleanup"),
                 ("limit_query", "job", "precleanup"), ("pids", "job", "precleanup"), ("accounting", "job", "precleanup"),
                 ("terminate", "job", ""), ("wait", "debugger_process", ""), ("wait", "candidate_process", "")]
        ending = [("close", role, "") for role in ("candidate_process", "debugger_process", "job", "desktop")] + [("finish", "", "")]
        index, ending_index, drain_pairs, drain_started, previous = 0, 0, 0, None, authority.clock.origin_tick
        draining, drained, final_account, pid_sets = False, False, None, {}
        semantic = ("borrowed_handle_value", "native_return", "value", "flags", "inherit_handles", "process_pid", "timeout_milliseconds", "membership_result", "object_name", "inherited_tokens", "information_class", "requested_bytes", "returned_bytes", "input_buffer", "output_buffer", "identity_before", "identity_after")
        defaults = dict(borrowed_handle_value=None, native_return=None, value=None, flags=None, inherit_handles=None, process_pid=None, timeout_milliseconds=None,
                        membership_result=None, object_name=None, inherited_tokens=(), information_class=None,
                        requested_bytes=None, returned_bytes=None, input_buffer=b"", output_buffer=b"", identity_before=None, identity_after=None)
        for ordinal, row in enumerate(events, 1):
            try:
                _require(row.sequence == ordinal and row.run_id == authority.run.run_id and row.source_snapshot_sha256 == source_snapshot_sha256(authority), "event sequence/run/source authority differs")
                for sample in (row.begin, row.end):
                    _require((sample.epoch_id, sample.frequency_hz) == (authority.clock.epoch_id, authority.clock.frequency_hz) and sample.native_return != 0,
                             "original controller QPC query failed or changed epoch")
                _require(previous <= row.begin.tick <= row.end.tick, "original job clock order differs")
                previous = row.end.tick
                _require(not row.error, "original native error retained")
                if index < len(setup): kind, role, phase = setup[index]
                elif not drained:
                    draining = True
                    kind, role, phase = ("accounting" if final_account is None else "pids", "job", "drain")
                else:
                    _require(ending_index < len(ending), "native operations follow final finish")
                    kind, role, phase = ending[ending_index]
                _require((row.kind, row.token, row.phase) == (kind, tokens.get(role, ""), phase), "missing, reordered, duplicated or incompatible native operation")
                expected_api = ("CloseDesktop" if role == "desktop" else "CloseHandle") if kind == "close" else APIS[kind]
                _require(row.api_name == expected_api, "original native API/handle-close kind differs")
                expected = dict(defaults)
                acquire = kind in ("desktop", "job", "stdin", "stdout", "target_open", "launch")
                if acquire:
                    _require(row.handle_value is not None and 0 < row.handle_value < U64 and role not in handles,
                             "native handle acquisition failed/reused token")
                    _require(row.handle_value != authority.caller_stdout_handle and all(value != row.handle_value for key, value in handles.items() if key not in closed), "new retained handle aliases a live/protected handle")
                    handles[role] = row.handle_value
                elif role:
                    _require(role in handles and role not in closed and row.handle_value == handles[role], "retained handle/token authority lost or already closed")
                else: _require(row.handle_value is None, "finish carries an invented native handle")
                related_role = "job" if kind in ("assign", "membership") else "debugger_thread" if kind == "launch" else None
                if kind == "launch":
                    _require(row.related_token == tokens["debugger_thread"] and row.related_handle_value is not None and
                             0 < row.related_handle_value < U64 and row.related_handle_value not in handles.values() and
                             row.related_handle_value != authority.caller_stdout_handle, "created primary thread handle aliases or is absent")
                    handles["debugger_thread"] = row.related_handle_value
                elif related_role:
                    _require(row.related_token == tokens[related_role] and row.related_handle_value == handles.get(related_role) and related_role not in closed, "native operation queries another/unowned job")
                else: _require(not row.related_token and row.related_handle_value is None, "invented related handle field")
                if kind == "desktop": expected["object_name"] = authority.desktop_name
                elif kind in ("stdout", "launch", "limit_set", "limit_query", "pids", "accounting", "assign", "membership", "close", "terminate"):
                    _require(row.native_return is not None and row.native_return != 0, "original native BOOL indicates failure")
                    expected["native_return"] = row.native_return
                if kind == "target_open": expected.update(flags=OPEN_ACCESS, process_pid=authority.target.pid, inherit_handles=0)
                if kind == "stdout": expected.update(borrowed_handle_value=authority.caller_stdout_handle, flags=2, inherit_handles=1)
                if kind == "stdin": expected.update(object_name="NUL", flags=0x80000000, inherit_handles=1)
                if kind == "launch":
                    expected.update(flags=CREATE_FLAGS, value=authority.debugger_primary_tid, process_pid=authority.debugger.pid,
                                    object_name=authority.desktop_name,
                                    inherit_handles=1, inherited_tokens=(tokens["stdin"], tokens["stdout_duplicate"]))
                    _require(not {"stdin", "stdout_duplicate"} & closed, "launch references closed inherited handles")
                if kind == "limit_set":
                    expected_input = bytearray(LIMIT_BYTES); struct.pack_into("<I", expected_input, 16, 0x2000)
                    expected.update(information_class=9, requested_bytes=LIMIT_BYTES, input_buffer=bytes(expected_input))
                if kind in ("limit_query", "pids", "accounting"):
                    expected.update(information_class=row.information_class, requested_bytes=row.requested_bytes,
                                    returned_bytes=row.returned_bytes, output_buffer=row.output_buffer)
                    value = _query(row, kind)
                    parsed.append(dict(sequence=ordinal, kind=kind, phase=phase, raw_sha256=_sha(row.output_buffer), returned_bytes=row.returned_bytes, parsed=value))
                    if phase in ("startup", "precleanup") and kind == "pids":
                        wanted = {generation.pid for name, generation in generations.items() if latest[name]}
                        _require(set(value) == wanted, "unknown/late/vanished native job membership differs from retained generations")
                        pid_sets[phase] = value
                    if phase in ("startup", "precleanup") and kind == "accounting":
                        _require(value["total"] == 2 and value["active"] == len(pid_sets[phase]), "job accounting and complete native membership differ")
                    if phase == "drain":
                        if drain_started is None: drain_started = row.begin.tick
                        _require(row.end.tick - drain_started <= DRAIN_SECONDS * authority.clock.frequency_hz, "owned job drain deadline exceeded")
                        if kind == "accounting": final_account = value
                        else:
                            drain_pairs += 1
                            _require(drain_pairs <= MAX_DRAIN_PAIRS and final_account["total"] == 2 and final_account["active"] == len(value), "drain count/counters/coherence differ")
                            _require(set(value) <= {generation.pid for generation in generations.values()}, "unknown late descendant has no independent generation authority")
                            drained = final_account["active"] == 0 and not value
                            final_account = None
                if kind in ("identity", "membership", "wait"):
                    required_live = True if phase == "startup" else False if kind == "wait" else None
                    before_live = _identity(row.identity_before, generations[role], parents[role], live=required_live)
                    expected["identity_before"] = row.identity_before
                    latest[role] = before_live
                    if kind == "membership":
                        after_live = _identity(row.identity_after, generations[role], parents[role], live=required_live)
                        _require(before_live == after_live and row.membership_result is not None and
                                 (not before_live or row.membership_result != 0), "native membership result/liveness differs")
                        expected.update(membership_result=row.membership_result, identity_after=row.identity_after)
                    if kind == "wait": expected.update(value=0, timeout_milliseconds=5000)
                if kind == "resume": expected["value"] = 1
                if kind == "terminate": expected["value"] = 1
                if kind == "finish": _require(row.native_error == 0, "finish contains an invented native error scalar")
                for name in semantic: _require(getattr(row, name) == expected[name], "original native result/input shape differs: " + name)
                if kind == "close": closed.add(role)
                if index < len(setup): index += 1
                elif drained and not draining: ending_index += 1
                elif row.kind in ("close", "finish"): ending_index += 1
                draining = not drained
            except Exception as error:
                failure(f"event {ordinal}: {type(error).__name__}: {error}")
        _require(index == len(setup) and drained and ending_index == len(ending), "complete assignment/membership/drain/close sequence missing")
        _require(set(handles) == set(ROLES) and closed == set(ROLES), "retained handle acquisition/close debt remains")
        _sources(authority, source_bytes)
    except Exception as error:
        failure(type(error).__name__ + ": " + str(error))
    result = dict(schema=SCHEMA, **FALSE_CLAIMS, raw_job_receipt_replay_passed=not failures,
        failures=failures, acquired_roles=list(handles), closed_roles=sorted(closed), remaining_handle_debt=sorted(set(handles) - closed),
        parsed_original_queries=parsed, controller_abi="WIN64_only",
        mandatory_future_gaps=["genuine instrumented native source/handle issuance", "actual no-breakaway host cleanup",
            "per-frame/whole-run membership schedule", "native parent/target module bytes and process progress",
            "native snapshot coherence and other controller ABI", "unchanged host lacks this future receipt protocol",
            "oversized original native buffers/errors retained before bounded record construction",
            "public Python aliases are not privately reconstructed native producer authority",
            "durable original receipts and total producer budget"])
    return ReplayResult(_canonical(result), data)
