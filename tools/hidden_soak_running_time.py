"""Adapter-only QPC/DbgEng receipt arithmetic; no native duration proof.

The v2 clock policy is separate from the frozen wall-clock frame ledger. Only
post-GO/status-ack to pre-break-request ticks contribute, with a fixed one-tick
debit at each endpoint. These receipts do not prove host-awake coverage, actual
CPU/render progress or native producer provenance. No evidence lane is added.
Original QPC samples remain unchanged; credited ticks are a separate derived
value. No GetTickCount64/Python-monotonic epoch conversion is installed.
HRESULT receipts retain the original signed32 or unsigned32 integer form;
neither representation is normalized, and replay accepts success only as zero.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
import re
import uuid

import hidden_soak_process_lease as process

MODULE_PATH = Path(__file__).resolve()
SOURCE = str(MODULE_PATH)
SCHEMA = "hidden_soak_running_transcript_v2"
SECOND = 1_000_000_000
REQUIRED_SECONDS, PERIOD_SECONDS = 7200, 30
PERIODIC_COUNT, CAPTURE_COUNT = 241, 242
ENDPOINT_DEBIT_TICKS = 1  # Per endpoint, source-owned; never a caller option.
MAX_SLOT_LATENESS_NS = 2 * SECOND
MAX_HELD_SECONDS = 20
MAX_EVENTS, MAX_JSON_BYTES, MAX_ERROR_BYTES = 4096, 4 * 1024 * 1024, 4096
MAX_SOURCE_BYTES = 8 * 1024 * 1024
U63, U32 = (1 << 63) - 1, (1 << 32) - 1
GO, BREAK = 1, 6
FROZEN_WALL_LEDGER_SHA256 = "f9340af2f7c2fce723c420939f32a91f980b13b62f6096b2f3794abf2856ee0b"
FROZEN_PROCESS_LEASE_SHA256 = "abe72430a334cc05814b3cd2eb792716b5ee6bf7f11d31a0a766870abf1d163b"
PROFILES = ("classic", "framed", "completehd", "modalwidgets")
PRESETS = ("800x600", "1024x768", "1280x720", "1280x960", "1366x768",
           "1920x1080", "2560x1440", "3440x1440", "3840x2160")
FALSE_CLAIMS = {name: False for name in (
    "passed", "native_producer_provenance_verified", "natural_startup_verified",
    "running_duration_verified", "host_clock_coverage_verified", "render_progress_verified",
    "frame_pixels_verified", "loaded_candidate_verified", "loaded_probe_verified",
    "no_breakaway_job_verified", "ordered_ladder_verified", "runtime_acceptance",
    "release_acceptance", "manual_input_verified", "promotion_ready", "stable")}


def _require(value, message):
    if not value:
        raise ValueError(message)


def _int(value, maximum, label, minimum=0):
    _require(type(value) is int and minimum <= value <= maximum, label)


def _digest(value):
    _require(type(value) is str and re.fullmatch("[0-9a-f]{64}", value), "canonical SHA-256 required")
    return value


def _token(value):
    _require(type(value) is str and uuid.UUID(value).hex == value, "canonical UUID token required")
    return value


def _sha(value):
    return hashlib.sha256(value).hexdigest()


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                      allow_nan=False).encode("ascii")


def policy():
    return dict(clock="windows_qpc_v1", credit="GO_status_ack_end_to_BREAK_REQUEST_begin",
                endpoint_debit_ticks=ENDPOINT_DEBIT_TICKS,
                required_seconds=REQUIRED_SECONDS, periodic_seconds=PERIOD_SECONDS,
                periodic_count=PERIODIC_COUNT, capture_count=CAPTURE_COUNT,
                max_slot_lateness_ns=MAX_SLOT_LATENESS_NS,
                maximum_held_seconds=MAX_HELD_SECONDS,
                max_events=MAX_EVENTS, max_json_bytes=MAX_JSON_BYTES,
                max_error_bytes=MAX_ERROR_BYTES, max_source_bytes=MAX_SOURCE_BYTES,
                hresult_wire_policy="original_signed32_or_unsigned32_integer_unchanged; success_exactly_zero",
                terminal="distinct_pause_after_periodic_240",
                wall_ledger_predecessor_sha256=FROZEN_WALL_LEDGER_SHA256,
                uncertainty="unknown_transition_fails; held_time_and_call_windows_excluded",
                scope="provided_debugger_GO_receipt_arithmetic_only; no native duration proof")


def retention_allowance():
    """Known serialized bytes only; caller adds native-host/source/RAM costs."""
    return dict(transcript_bytes=MAX_JSON_BYTES, atomic_temporary_bytes=MAX_JSON_BYTES,
                additional_peak_bytes=2 * MAX_JSON_BYTES,
                included_in_frozen_wall_ledger_budget=False,
                scope="one retained transcript plus one same-size atomic temporary; other producer costs additional")


@dataclass(frozen=True)
class ArtifactBinding:
    path: str
    sha256: str
    size: int

    def __post_init__(self):
        object.__setattr__(self, "path", process._path(self.path))
        _digest(self.sha256)
        _int(self.size, 1 << 40, "invalid external artifact size", 1)


@dataclass(frozen=True)
class CaptureBinding:
    ordinal: int
    pause_token: str
    artifact: ArtifactBinding

    def __post_init__(self):
        _int(self.ordinal, CAPTURE_COUNT - 1, "invalid capture ordinal")
        _token(self.pause_token)
        _require(type(self.artifact) is ArtifactBinding, "typed external capture binding required")


@dataclass(frozen=True)
class ClockAuthority:
    epoch_id: str
    frequency_hz: int
    origin_tick: int

    def __post_init__(self):
        _token(self.epoch_id)
        _int(self.frequency_hz, 1_000_000_000, "unsupported QPC frequency", 1)
        _int(self.origin_tick, U63 - REQUIRED_SECONDS * self.frequency_hz,
             "invalid independent native clock origin", 1)


@dataclass(frozen=True)
class TimeAuthority:
    run: process.RunAuthority
    target: process.Generation
    debugger: process.Generation
    primary_tid: int
    native_break_address: int
    readiness: ArtifactBinding
    clock: ClockAuthority
    host_source: process.SourcePin
    captures: tuple[CaptureBinding, ...]

    def __post_init__(self):
        _require(type(self.run) is process.RunAuthority and type(self.target) is process.Generation
                 and type(self.debugger) is process.Generation, "typed independent run/generations required")
        _require(self.run.profile in PROFILES and self.run.resolution in PRESETS, "preset/profile not admitted")
        _require(type(self.readiness) is ArtifactBinding and type(self.clock) is ClockAuthority
                 and type(self.host_source) is process.SourcePin, "typed readiness/clock/source authority required")
        _int(self.primary_tid, U32, "invalid retained primary TID", 1)
        _int(self.native_break_address, 0x7fff0000, "invalid expected native break address", 0x10000)
        _require(len({self.run.controller.pid, self.target.pid, self.debugger.pid}) == 3,
                 "aliased process generations")
        _require(self.run.controller.creation_filetime <= self.debugger.creation_filetime
                 <= self.target.creation_filetime, "parent generation chronology differs")
        for role, generation in (("candidate", self.target), ("debugger", self.debugger)):
            image = next(row for row in self.run.images if row.role == role)
            _require((image.path, image.sha256) == (generation.image_path, generation.image_sha256),
                     "generation differs from independently frozen image")
        pins = {row.path: row.sha256 for row in self.run.source_pins}
        _require(process._path(SOURCE) in pins and self.host_source.path in pins
                 and pins[self.host_source.path] == self.host_source.sha256,
                 "fixed time/native-host source pins required")
        _require(self.host_source.path != process._path(SOURCE)
                 and not self.host_source.path.endswith(("\\hidden_soak_process_lease.py", "\\hidden_soak_frame_ledger.py")),
                 "native host source cannot substitute this component or its frozen predecessors")
        for suffix, expected in (("hidden_soak_frame_ledger.py", FROZEN_WALL_LEDGER_SHA256),
                                 ("hidden_soak_process_lease.py", FROZEN_PROCESS_LEASE_SHA256)):
            matching = [pin for pin in self.run.source_pins if pin.path.endswith("\\tools\\" + suffix)]
            _require(len(matching) == 1 and matching[0].sha256 == expected, "frozen predecessor source differs")
        _require(type(self.captures) is tuple and len(self.captures) == CAPTURE_COUNT
                 and all(type(row) is CaptureBinding for row in self.captures), "all 242 typed capture bindings required")
        _require(tuple(row.ordinal for row in self.captures) == tuple(range(CAPTURE_COUNT)),
                 "capture ordinal inventory differs")
        _require(len({row.pause_token for row in self.captures}) == CAPTURE_COUNT
                 and len({row.artifact.path for row in self.captures}) == CAPTURE_COUNT,
                 "duplicate capture pause/artifact references")
        _require(self.readiness.path not in {row.artifact.path for row in self.captures},
                 "readiness aliases a frame artifact")


@dataclass(frozen=True)
class ClockSample:
    epoch_id: str
    frequency_hz: int
    tick: int
    native_return: int
    native_error: int

    def __post_init__(self):
        _token(self.epoch_id)
        # Failed native calls may leave zero/negative LARGE_INTEGER values or
        # nonstandard BOOL values. Preserve them; replay rejects success claims.
        _int(self.frequency_hz, U63, "invalid raw QPC frequency", -(1 << 63))
        _int(self.tick, U63, "invalid raw QPC tick", -(1 << 63))
        _int(self.native_return, U32, "raw QPC BOOL required", -(1 << 31))
        _int(self.native_error, U32, "raw QPC error required")


@dataclass(frozen=True)
class NativeBreak:
    event_type: int
    exception_code: int
    first_chance: int
    process_pid: int
    thread_tid: int
    address: int

    def __post_init__(self):
        for name in self.__dataclass_fields__:
            _int(getattr(self, name), U32, "invalid raw native break field")


@dataclass(frozen=True)
class NativeEvent:
    sequence: int
    kind: str
    run_id: str
    source_snapshot_sha256: str
    begin: ClockSample
    end: ClockSample
    target_before: process.Observation
    target_after: process.Observation
    debugger_before: process.Observation
    debugger_after: process.Observation
    pause_token: str = ""
    ordinal: int | None = None
    artifact: ArtifactBinding | None = None
    set_hresult: int | None = None
    get_hresult: int | None = None
    requested_status: int | None = None
    execution_status: int | None = None
    native_return: int | None = None
    native_error: int | None = None
    event_hresult: int | None = None
    native_break: NativeBreak | None = None
    error: str = ""

    def __post_init__(self):
        _int(self.sequence, MAX_EVENTS, "invalid event sequence", 1)
        _require(self.kind in ("ready", "go", "break_request", "break_ack", "read_begin", "read_end", "finish", "unknown"),
                 "unknown typed event kind")
        _token(self.run_id); _digest(self.source_snapshot_sha256)
        _require(type(self.begin) is ClockSample and type(self.end) is ClockSample, "typed original QPC samples required")
        for name in ("target_before", "target_after", "debugger_before", "debugger_after"):
            _require(type(getattr(self, name)) is process.Observation, "typed retained process observation required")
        if self.pause_token:
            _token(self.pause_token)
        if self.ordinal is not None:
            _int(self.ordinal, CAPTURE_COUNT - 1, "invalid native capture ordinal")
        _require(self.artifact is None or type(self.artifact) is ArtifactBinding, "typed raw artifact reference required")
        for name in ("set_hresult", "get_hresult", "event_hresult"):
            if getattr(self, name) is not None:
                _int(getattr(self, name), U32, "invalid original HRESULT representation", -(1 << 31))
        for name in ("requested_status", "execution_status", "native_return", "native_error"):
            if getattr(self, name) is not None:
                _int(getattr(self, name), U32, "invalid original native result")
        _require(self.native_break is None or type(self.native_break) is NativeBreak, "typed native breakpoint receipt required")
        _require(type(self.error) is str and len(self.error.encode("utf-8")) <= MAX_ERROR_BYTES,
                 "bounded full original error receipt required")


@dataclass(frozen=True)
class TranscriptBinding:
    authority_sha256: str
    source_snapshot_sha256: str
    artifact_sha256: str
    artifact_size: int

    def __post_init__(self):
        for name in ("authority_sha256", "source_snapshot_sha256", "artifact_sha256"):
            _digest(getattr(self, name))
        _int(self.artifact_size, MAX_JSON_BYTES, "bounded independently retained transcript required", 1)


def authority_sha256(authority):
    _require(type(authority) is TimeAuthority, "typed independent time authority required")
    return _sha(_canonical(asdict(authority)))


def source_snapshot_sha256(authority):
    return _sha(_canonical([asdict(pin) for pin in authority.run.source_pins]))


def _sources(authority, source_bytes):
    _require(type(source_bytes) is dict and set(source_bytes) == {row.path for row in authority.run.source_pins},
             "exact independently supplied source byte inventory required")
    _require(all(type(data) is bytes for data in source_bytes.values())
             and sum(map(len, source_bytes.values())) <= MAX_SOURCE_BYTES, "bounded original source bytes required")
    for pin in authority.run.source_pins:
        _require(_sha(source_bytes[pin.path]) == pin.sha256, "source byte identity changed")
    _require(_sha(MODULE_PATH.read_bytes()) == next(row.sha256 for row in authority.run.source_pins
                                                 if row.path == process._path(SOURCE)), "loaded time source file changed")


class TranscriptLimitError(ValueError):
    """Retains the entire prior transcript and attempted event in RAM."""
    def __init__(self, message, report, event):
        super().__init__(message)
        self.report, self.event = report, event


class TranscriptCollector:
    """Serializes typed provided receipts only; no native adapter or file I/O."""
    def __init__(self, authority, source_bytes):
        _require(type(authority) is TimeAuthority, "typed independent time authority required")
        _sources(authority, source_bytes)
        self.authority, self.source_bytes = authority, dict(source_bytes)
        self.events = []
        self.receipt_bytes = len(_canonical(self.report()))

    def report(self):
        return dict(schema=SCHEMA, authority_sha256=authority_sha256(self.authority),
                    source_snapshot_sha256=source_snapshot_sha256(self.authority), policy=policy(),
                    events=[asdict(row) for row in self.events], claims=dict(FALSE_CLAIMS))

    def record(self, event):
        _require(type(event) is NativeEvent, "typed original native receipt required")
        _sources(self.authority, self.source_bytes)
        additional = len(_canonical(asdict(event))) + bool(self.events)
        if len(self.events) >= MAX_EVENTS or self.receipt_bytes + additional > MAX_JSON_BYTES:
            raise TranscriptLimitError("bounded transcript capacity exceeded", self.report(), event)
        self.events.append(event)
        self.receipt_bytes += additional

    def encode(self):
        _sources(self.authority, self.source_bytes)
        data = _canonical(self.report())
        _require(len(data) == self.receipt_bytes and len(data) <= MAX_JSON_BYTES,
                 "serialized transcript capacity differs")
        return data


def _exact(value, names, label):
    _require(type(value) is dict and set(value) == set(names), "exact " + label + " fields required")
    return value


def _generation(value):
    return process.Generation(**_exact(value, process.Generation.__dataclass_fields__, "generation"))


def _observation(value):
    value = dict(_exact(value, process.Observation.__dataclass_fields__, "observation"))
    value["generation"] = _generation(value["generation"])
    return process.Observation(**value)


def _event(value):
    value = dict(_exact(value, NativeEvent.__dataclass_fields__, "native event"))
    for name in ("begin", "end"):
        value[name] = ClockSample(**_exact(value[name], ClockSample.__dataclass_fields__, "clock sample"))
    for name in ("target_before", "target_after", "debugger_before", "debugger_after"):
        value[name] = _observation(value[name])
    if value["artifact"] is not None:
        value["artifact"] = ArtifactBinding(**_exact(value["artifact"], ArtifactBinding.__dataclass_fields__, "artifact"))
    if value["native_break"] is not None:
        value["native_break"] = NativeBreak(**_exact(value["native_break"], NativeBreak.__dataclass_fields__, "native break"))
    return NativeEvent(**value)


def replay(data, authority, binding, source_bytes):
    """Recompute supplied GO receipt arithmetic; every broader claim stays false."""
    failures, ticks, captures = [], 0, 0
    try:
        _require(type(authority) is TimeAuthority and type(binding) is TranscriptBinding, "independent typed replay bindings required")
        _sources(authority, source_bytes)
        _require(type(data) is bytes and 0 < len(data) <= MAX_JSON_BYTES, "bounded original transcript bytes required")
        _require((binding.authority_sha256, binding.source_snapshot_sha256, binding.artifact_sha256, binding.artifact_size)
                 == (authority_sha256(authority), source_snapshot_sha256(authority), _sha(data), len(data)),
                 "independently retained transcript binding differs")
        def unique(rows):
            result = {}
            for key, value in rows:
                _require(key not in result, "duplicate JSON field")
                result[key] = value
            return result
        def invalid(value):
            raise ValueError("nonfinite JSON token: " + value)
        report = json.loads(data, object_pairs_hook=unique, parse_constant=invalid)
        _exact(report, ("schema", "authority_sha256", "source_snapshot_sha256", "policy", "events", "claims"), "transcript")
        _require(_canonical(report) == data, "original transcript is noncanonical")
        _require((report["schema"], report["authority_sha256"], report["source_snapshot_sha256"])
                 == (SCHEMA, authority_sha256(authority), source_snapshot_sha256(authority)), "transcript external authority differs")
        _require(_canonical(report["policy"]) == _canonical(policy())
                 and _canonical(report["claims"]) == _canonical(FALSE_CLAIMS),
                 "source-owned version policy or evidence limits changed")
        _require(type(report["events"]) is list and 0 < len(report["events"]) <= MAX_EVENTS, "bounded full raw event timeline required")
        rows = [_event(row) for row in report["events"]]
        state, token, run_start, read_start, previous_end = "initial", "", None, None, authority.clock.origin_tick
        previous_read_end, last_ordinal, finished, held_deadline = None, None, False, None
        result_fields = ("set_hresult", "get_hresult", "requested_status", "execution_status", "native_return", "native_error", "event_hresult", "native_break")
        for index, row in enumerate(rows, 1):
            credit, capture_increment = 0, 0
            _require(row.sequence == index and not finished, "event missing, reordered or appended after finish")
            _require(row.run_id == authority.run.run_id and row.source_snapshot_sha256 == source_snapshot_sha256(authority), "event run/source scope differs")
            for clock in (row.begin, row.end):
                _require((clock.epoch_id, clock.frequency_hz, clock.native_return, clock.native_error)
                         == (authority.clock.epoch_id, authority.clock.frequency_hz, 1, 0), "original QPC epoch/frequency/read failed")
            _require(previous_end <= row.begin.tick <= row.end.tick, "original native clock order regressed")
            previous_end = row.end.tick
            for name, generation, parent in (("target_before", authority.target, authority.debugger.pid),
                    ("target_after", authority.target, authority.debugger.pid),
                    ("debugger_before", authority.debugger, authority.run.controller.pid),
                    ("debugger_after", authority.debugger, authority.run.controller.pid)):
                observed = getattr(row, name)
                _require(observed.generation == generation and observed.parent_pid == parent and observed.wait_result == 258,
                         "retained source-bound generation/parent/liveness differs")
            _require(not row.error and row.kind != "unknown", "full original native failure or unknown transition retained")
            if state in ("held", "reading", "read_complete"):
                _require(row.end.tick <= held_deadline, "source-owned held pause epoch expired")
            expected = dict.fromkeys(result_fields)
            if row.kind == "ready":
                _require(state == "initial" and row.pause_token == "" and row.ordinal is None
                         and row.artifact == authority.readiness, "initial readiness binding differs")
                expected.update(get_hresult=0, execution_status=BREAK); state = "held_ready"
            elif row.kind == "go":
                _require(state in ("held_ready", "read_complete") and row.pause_token == token
                         and row.ordinal is None and row.artifact is None, "orphan or foreign pause-token GO")
                expected.update(set_hresult=0, get_hresult=0, requested_status=GO, execution_status=GO)
                run_start, state = row.end.tick, "go"
            elif row.kind == "break_request":
                _require(state == "go" and captures < CAPTURE_COUNT and row.ordinal is None
                         and row.artifact is None and row.pause_token == authority.captures[captures].pause_token,
                         "orphan or substituted native break request")
                expected.update(native_return=1, native_error=0)
                credit = max(0, row.begin.tick - run_start - 2 * ENDPOINT_DEBIT_TICKS)
                token, state = row.pause_token, "break_requested"
            elif row.kind == "break_ack":
                _require(state == "break_requested" and row.pause_token == token and row.ordinal is None
                         and row.artifact is None, "native break acknowledgment has a different original pause token")
                native = row.native_break
                _require(native is not None and (native.event_type, native.exception_code, native.first_chance,
                         native.process_pid, native.address) == (2, 0x80000003, 1, authority.target.pid, authority.native_break_address)
                         and native.thread_tid not in (0, authority.primary_tid), "raw native breakpoint identity differs")
                expected.update(get_hresult=0, execution_status=BREAK, event_hresult=0, native_break=native)
                held_deadline, state = row.begin.tick + MAX_HELD_SECONDS * authority.clock.frequency_hz, "held"
            elif row.kind in ("read_begin", "read_end"):
                _require(captures < CAPTURE_COUNT and row.pause_token == token
                         and row.ordinal == captures and row.artifact == authority.captures[captures].artifact,
                         "read differs from original independently bound capture/pause epoch")
                expected.update(get_hresult=0, execution_status=BREAK)
                if row.kind == "read_begin":
                    _require(state == "held" and (previous_read_end is None or row.begin.tick > previous_read_end),
                             "orphan, duplicate or unseparated terminal read")
                    elapsed_ns = ticks * SECOND // authority.clock.frequency_hz
                    due_ns = min(captures, PERIODIC_COUNT - 1) * PERIOD_SECONDS * SECOND
                    _require(due_ns <= elapsed_ns <= due_ns + MAX_SLOT_LATENESS_NS,
                             "fixed source-owned running-time capture slot missed")
                    read_start, state = row.begin.tick, "reading"
                else:
                    _require(state == "reading" and (row.end.tick - read_start) * SECOND
                             <= MAX_SLOT_LATENESS_NS * authority.clock.frequency_hz, "paused read envelope failed or exceeded its source bound")
                    previous_read_end, last_ordinal = row.end.tick, captures
                    capture_increment, state = 1, "read_complete"
            elif row.kind == "finish":
                _require(state == "read_complete" and captures == CAPTURE_COUNT and last_ordinal == CAPTURE_COUNT - 1
                         and row.pause_token == token and row.ordinal is None and row.artifact is None,
                         "ordered distinct terminal capture/held finish missing")
                expected.update(get_hresult=0, execution_status=BREAK)
                finished = True
            _require({name: getattr(row, name) for name in result_fields} == expected,
                     "original native command/status result failed, ambiguous or substituted")
            ticks += credit
            captures += capture_increment
        _require(finished and ticks >= REQUIRED_SECONDS * authority.clock.frequency_hz,
                 "fixed 7200-second GO receipt lower bound or held finish missing")
        _sources(authority, source_bytes)
    except Exception as error:
        failures.append(type(error).__name__ + ": " + str(error))
    return {**FALSE_CLAIMS, "raw_running_transcript_replay_passed": not failures,
            "observed_GO_lower_bound_ticks": ticks,
            "observed_GO_lower_bound_ns": ticks * SECOND // authority.clock.frequency_hz if type(authority) is TimeAuthority else 0,
            "bound_capture_count": captures, "failures": failures,
            "mandatory_producer_gaps": ["native receipt provenance and loaded source/target identity",
                "host awake/suspend coverage and unknown asynchronous engine-event coverage",
                "actual CPU/render/process health and natural ordinary-map readiness",
                "raw frame contents/coherence and complete no-breakaway job cleanup",
                "same-candidate ordered endurance ladder and independent runtime/release evaluation"]}
