"""Source-only synthetic recorder for the frozen paused-surface protocol.

No game/native/owner factory is implemented. The fixed dispatcher calls an
explicit synthetic adapter; it never interprets a report as live ownership.
Every supplied output, including failures and partial buffers, is retained
before semantic checks. Consistency is diagnostic only; all authority is false.
Historical producers, the replay helper and production registry are unchanged.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import struct
import tempfile
from types import MappingProxyType, ModuleType
import uuid

ROOT = Path(__file__).resolve().parents[1]
HELPER_SHA256 = "60fbb1b8392b302b4366e0acaec7bd659705daf8c856df6a2818a5e5b0690dcb"
HELPER_PATH = ROOT / "tools/paused_surface_triple_replay.py"
AUTHORITY_FLAGS = ("passed", "candidate_authenticated", "canonical_probe_verified", "source_authenticated",
    "native_provenance_verified", "release_evidence_verified", "geometry_evidence_verified", "runtime_proof",
    "manual_input_proof", "ordinary_input_proof", "visible_composition_proof", "live_cleanup_verified",
    "endurance_proof", "promotion_ready")
STATE = (("selected_stack", 0x511B58, 3), ("panel_stack", 0x514194, 3),
         ("lower", 0x526994, 1), ("owner", 0x5199D8, 0x40AD40))
READ_ROLES = tuple("state_before_" + row[0] for row in STATE) + (
    "e0_before", "header_before", "pixels", "e0_after", "header_after") + tuple("state_after_" + row[0] for row in STATE)
OPERATIONS = {"QueryPerformanceFrequency": (8,), "QueryPerformanceCounter": (8,),
    "GetProcessId": (), "GetProcessTimes": (32,), "WaitForSingleObject": (),
    "ReadProcessMemory": (8, None)}
MAX_COMMAND = 256 * 1024
MAX_LOG = 16 * 1024 * 1024
MAX_JOURNAL = 2 * 1024 * 1024
MAX_RETENTION = 2 * 1024 * 1024
MAX_MANIFEST = 64 * 1024
MAX_RAM = 96 * 1024 * 1024
MAX_FILE = 64 * 1024 * 1024
MAX_CALLS = 432
MAX_ORIGINALS = 1183  # 1179 native outputs + commands, two paused logs, journal
MAX_ARCHIVE_FILES = MAX_ORIGINALS + 2  # manifest + retention sidecar
MAX_TINY_PUBLICATION = 64 * 1024
MAX_TINY_FILES = 16


class SourceOnlyError(ValueError):
    pass


def require(condition, text):
    if not condition:
        raise ValueError(text)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _stamp(info):
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_mode,
            getattr(info, "st_file_attributes", 0))


def _helper():
    """Read a fixed local source once, never a report-selected/public alias."""
    for part in (HELPER_PATH, *HELPER_PATH.parents):
        info = part.lstat()
        require(not stat.S_ISLNK(info.st_mode) and not (getattr(info, "st_file_attributes", 0) & 0x400),
                "helper source reparse path")
    before = HELPER_PATH.stat()
    with HELPER_PATH.open("rb") as stream:
        require(_stamp(os.fstat(stream.fileno())) == _stamp(before), "opened helper source changed")
        source = stream.read(1024 * 1024 + 1)
        require(_stamp(os.fstat(stream.fileno())) == _stamp(before), "helper changed during source read")
    require(_stamp(HELPER_PATH.stat()) == _stamp(before) and len(source) <= 1024 * 1024
            and sha(source) == HELPER_SHA256, "frozen replay helper source differs")
    private = ModuleType("_paused_surface_recorder_private_helper")
    private.__file__ = str(HELPER_PATH)
    exec(compile(source, str(HELPER_PATH), "exec"), private.__dict__)
    require(private.READ_ROLES == READ_ROLES and tuple((key, *value) for key, value in private.STATE.items()) == STATE,
            "fixed protocol roles differ")
    return private, source, _stamp(before)


@dataclass(frozen=True)
class ModelPlan:
    """Immutable synthetic inputs; not candidate/source/owner authentication."""
    wire: bytes
    commands: bytes
    prefix: bytes
    final: bytes


def prepare_synthetic_plan(binding, identity, state, commands, prefix, final, *, epoch="synthetic_pause"):
    helper, _, _ = _helper()
    helper.keys(binding, ("profile", "stage", "recipe", "representation", "phase", "resolution",
                         "candidate_sha256", "original_sha256", "probe_sha256", "producer_sha256"), "binding")
    require((binding["profile"], binding["stage"], binding["recipe"], binding["representation"], binding["phase"]) ==
            ("Complete HD", helper.STAGE, "complete_hd_v1", helper.REPRESENTATION, helper.PHASE), "narrow stack3 binding required")
    require(binding["resolution"] in helper.RESOLUTIONS, "unsupported synthetic byte geometry")
    width, height = map(int, binding["resolution"].split("x"))
    for field in ("candidate_sha256", "original_sha256", "probe_sha256", "producer_sha256"):
        helper.digest(binding[field], field)
    helper.keys(identity, ("process_id", "creation_filetime", "handle"), "synthetic identity")
    for field, high in (("process_id", 0xFFFFFFFF), ("creation_filetime", 0x7FFFFFFFFFFFFFFF), ("handle", 0xFFFFFFFFFFFFFFFF)):
        helper.integer(identity[field], 1, high, field)
    helper.keys(state, ("tid", "eip", "esp", "selected_stack", "panel_stack", "lower", "owner",
                       "surface", "base", "width", "height", "vtable"), "synthetic stop state")
    require(all(type(value) is int for value in state.values()), "integer stopped state required")
    require((state["eip"], state["width"], state["height"], state["vtable"]) == (0x406FA1, width, height, 0x50EE24),
            "fixed stopped PC/geometry/vtable differs")
    helper.integer(state["tid"], 1, 0xFFFFFFFF, "TID")
    helper.integer(state["esp"], 0x10000, 0xFFFFFFFC, "ESP")
    require(state["esp"] % 4 == 0, "unaligned ESP")
    helper.integer(state["surface"], 0x10000, 0xFFFFFF44, "surface")
    require(state["surface"] != 0x51D4C0, "fixed primary surface incompatible")
    helper.integer(state["base"], 0x10000, 0x100000000 - width * height, "base")
    require(all(state[name] == expected for name, _, expected in STATE), "only selected/panel stack3 is supported")
    require(type(epoch) is str and re.fullmatch(r"[A-Za-z0-9_-]{1,64}", epoch), "bounded synthetic epoch")
    require(type(commands) is bytes and len(commands) <= MAX_COMMAND and sha(commands) == binding["probe_sha256"]
            and commands.count(b".echo SHSEL_HOST_READY") == 1, "bounded exact supplied probe bytes required")
    require(type(prefix) is bytes and type(final) is bytes and len(prefix) <= MAX_LOG and len(final) <= MAX_LOG,
            "bounded paused original logs required")
    # These checks do not authenticate the canonical probe or any native stop.
    lines = [line.rstrip(b"\r") for line in prefix.splitlines() if line.strip()]
    require(lines[-2:] == [helper.ready_line(state), b"SHSEL_HOST_READY"] and prefix == final,
            "exact equal stopped prefix/end logs required; cleanup tail is separate")
    wire = canonical(dict(binding=binding, identity=identity, state=state, epoch=epoch))
    return ModelPlan(wire, commands, prefix, final)


def native_owner_factory(*args, **kwargs):
    raise SourceOnlyError("Real retained-owner factory is unavailable; no native process or capture is authorized here")


def execute(*args, **kwargs):
    raise SourceOnlyError("Native execution is unavailable in this source-only synthetic recorder")


@dataclass(frozen=True)
class Output:
    """Supplied synthetic native bits. None means unavailable, never zero-fill."""
    result: bytes | None
    error: bytes | None
    buffers: tuple[bytes | None, ...] = ()


class SyntheticCallFailure(RuntimeError):
    def __init__(self, message, output=None):
        super().__init__(message)
        self.output = output


class SyntheticAdapter:
    """Explicit model boundary only. There is deliberately no native subclass."""
    def invoke(self, operation, arguments):
        raise NotImplementedError


@dataclass(frozen=True)
class Original:
    role: str
    path: str
    data: bytes

    def reference(self):
        return dict(path=self.path, bytes=len(self.data), sha256=sha(self.data))


class RAMOriginals:
    def __init__(self):
        self.directory = Path(tempfile.gettempdir()) / ("synthetic-paused-recorder-never-written-" + uuid.uuid4().hex)
        self.rows = []
        self.total = 0
        self.roles = set()

    def put(self, role, data):
        require(type(role) is str and role not in self.roles, "original role reused")
        require(type(data) is bytes, "unavailable output cannot be manufactured")
        require(len(self.rows) < MAX_ORIGINALS and len(data) <= MAX_FILE and self.total + len(data) <= MAX_RAM,
                "hard original count/byte capacity exhausted")
        row = Original(role, str(self.directory / f"{len(self.rows) + 1:04d}.bin"), data)
        self.rows.append(row)
        self.roles.add(role)
        self.total += len(data)
        return row.reference()

    def freeze(self):
        return FrozenOriginals(tuple(self.rows))


class FrozenOriginals:
    def __init__(self, rows):
        self.rows = tuple(rows)
        self.values = MappingProxyType({row.path: row for row in self.rows})
        require(len(self.values) == len(self.rows) and len({row.role for row in self.rows}) == len(self.rows),
                "immutable original namespace alias")
        self.loaded = {}

    def reference(self, value, role):
        require(type(value) is dict and set(value) == {"path", "bytes", "sha256"}, "exact original reference required")
        require(value["path"] not in self.loaded, "original physical model identity reused")
        row = self.values[value["path"]]
        require(value == row.reference(), "original identity/bytes rebound")
        self.loaded[row.path] = role
        return row.data

    def unchanged(self):
        require(all(self.values[row.path] is row and row.reference()["sha256"] == sha(row.data) for row in self.rows),
                "immutable originals changed")

    def receipts(self):
        return [dict(row.reference(), role=self.loaded[row.path]) for row in self.rows if row.path in self.loaded]


@dataclass(frozen=True)
class PendingCall:
    ordinal: int
    operation: str
    arguments: tuple
    output: object
    exception: str | None
    original_exception: object | None = None


@dataclass(frozen=True)
class Recording:
    manifest_bytes: bytes
    journal_bytes: bytes
    retention_bytes: bytes
    originals: tuple[Original, ...]
    calls: tuple[PendingCall, ...]
    diagnostic: dict
    exceptions: tuple[object, ...]
    failures: tuple[str, ...]
    missing: tuple[str, ...]

    def reader(self):
        return FrozenOriginals(self.originals)


class RecordingFailure(RuntimeError):
    """Final serialization/replay failed; exact pending outputs survive."""
    def __init__(self, error, recorder):
        super().__init__("Source-only recording finalization failed; original exception retained without rendering")
        self.original_cause = error
        self.originals = tuple(recorder.originals.rows)
        self.calls = tuple(recorder.calls)
        self.packet_references = tuple(recorder.packet_references)
        self.failures = tuple(recorder.failures)
        self.missing = tuple(recorder.missing)
        self.exceptions = tuple(recorder.original_exceptions)


def retention_budget(resolution, *, allocation_unit=4096, external_bytes=0):
    helper, _, _ = _helper()
    require(resolution in helper.RESOLUTIONS, "unsupported byte-format budget")
    helper.integer(allocation_unit, 1, 1024 * 1024, "allocation unit")
    helper.integer(external_bytes, 0, 1024 ** 4, "external output allowance")
    width, height = map(int, resolution.split("x"))
    native_bytes = 3 * width * height + 8784
    content = native_bytes + MAX_COMMAND + 2 * MAX_LOG + MAX_JOURNAL + MAX_RETENTION + MAX_MANIFEST
    require(content <= MAX_RAM, "format exceeds immutable archive cap")
    return dict(schema="clash95_paused_recorder_budget_v2", resolution=resolution,
        native_originals=1179, total_originals=MAX_ORIGINALS, native_bytes=native_bytes,
        total_archive_files=MAX_ARCHIVE_FILES, manifest_cap=MAX_MANIFEST,
        content_cap=content, atomic_temporary=max(MAX_LOG, width * height),
        allocation_slack=MAX_ARCHIVE_FILES * (allocation_unit - 1), external_bytes=external_bytes,
        required_peak=content + max(MAX_LOG, width * height) + MAX_ARCHIVE_FILES * (allocation_unit - 1) + external_bytes,
        runtime_budget_complete=False, runtime_assets_counted=False, native_provenance_verified=False)


def require_reserve(free, total, required):
    require(all(type(value) is int for value in (free, total, required)) and total > 0 and 0 <= free <= total and required >= 0,
            "bounded actual-shaped disk values required")
    require(free * 10 > total and (free - required) * 10 > total,
            "strict greater-than-ten-percent reserve plus entire output allowance required")


class Recorder:
    def __init__(self, plan, adapter):
        require(type(plan) is ModelPlan and isinstance(adapter, SyntheticAdapter), "explicit synthetic plan/adapter required")
        self.helper, self.helper_source, self.helper_stamp = _helper()
        self.plan, self.adapter = plan, adapter
        self.parameters = self.helper.parse_json(plan.wire)
        self.helper.keys(self.parameters, ("binding", "identity", "state", "epoch"), "immutable synthetic plan")
        checked = prepare_synthetic_plan(self.parameters["binding"], self.parameters["identity"], self.parameters["state"],
                                        plan.commands, plan.prefix, plan.final, epoch=self.parameters["epoch"])
        require(checked == plan, "forged/noncanonical synthetic plan")
        self.originals = RAMOriginals()
        self.calls, self.failures, self.missing = [], [], []
        self.original_exceptions = []
        self.packet_references = []
        self.frozen = False

    def _call(self, operation, arguments, role, widths):
        require(operation in OPERATIONS and len(self.calls) < MAX_CALLS, "source-selected operation/call capacity required")
        expected = OPERATIONS[operation]
        if operation == "ReadProcessMemory":
            require(len(arguments) == 3 and all(type(value) is int for value in arguments)
                    and 0 < arguments[0] <= 0xFFFFFFFFFFFFFFFF and 0x10000 <= arguments[1]
                    and 0 < arguments[2] <= 3840 * 2160 and arguments[1] + arguments[2] <= 0x100000000,
                    "bounded fixed RPM arguments required")
            expected = (8, arguments[2])
        require(widths == expected, "source-owned output ABI/capacity differs")
        failure, output, original_exception = None, None, None
        try:
            output = self.adapter.invoke(operation, tuple(arguments))
        except Exception as error:
            original_exception = error
        # Adopt the entire packet before any output/schema/semantic/persistence check.
        self.calls.append(PendingCall(len(self.calls) + 1, operation, tuple(arguments), output, failure, original_exception))
        if original_exception is not None:
            self.original_exceptions.append(original_exception)
            # Only our exact source-owned failure class has a known output slot.
            # Unknown subclasses/objects remain retained, with no attribute or
            # string/repr/iterator interpretation of their contents.
            if type(original_exception) is SyntheticCallFailure:
                output = original_exception.output
                failure = "SyntheticCallFailure: exception text unavailable; original exception object retained"
            else:
                failure = "Synthetic adapter exception: text unavailable; original exception object retained"
            self.calls[-1] = PendingCall(len(self.calls), operation, tuple(arguments), output, failure, original_exception)
            self.missing.append(role + ": exception text unavailable; exact original exception retained")
        references = {}
        self.packet_references.append(dict(ordinal=len(self.calls), operation=operation, arguments=list(arguments),
                                          originals=references, exception=failure, original_exception_retained=original_exception is not None))
        if type(output) is Output:
            pieces = [("return", output.result), ("error", output.error)]
            # The fixed API has at most two buffers. Never iterate a supplied
            # iterable or allocate metadata for an unbounded malformed tuple.
            if type(output.buffers) is tuple:
                for index in range(min(len(output.buffers), 2)):
                    pieces.append(("buffer" + str(index), output.buffers[index]))
                if len(output.buffers) != len(widths):
                    self.missing.append(role + ": unexpected buffer arity; complete original packet retained in pending")
            else:
                self.missing.append(role + ": non-tuple buffers not traversed; complete original packet retained in pending")
            for field, value in pieces:
                label = role + "." + field
                if value is None:
                    self.missing.append(label)
                elif type(value) is bytes:
                    try:
                        references[field] = self.originals.put(label, value)
                    except ValueError as error:
                        self.original_exceptions.append(error)
                        self.missing.append(label + ": unpersisted original retained in pending packet")
                        self.failures.append(label + ": originals retention failed; original exception object retained without text")
                else:
                    self.missing.append(label + ": wrong original type retained in pending packet")
        else:
            self.missing.append(role + ": original packet unavailable")
        if failure:
            raise ValueError(role + ": " + failure)
        require(type(output) is Output and type(output.buffers) is tuple and len(output.buffers) == len(widths),
                role + ": exact original output fields required")
        require(set(references) == {"return", "error", *("buffer" + str(index) for index in range(len(widths)))},
                role + ": missing/unpersisted original output")
        require(len(output.result) == len(output.error) == 4 and all(type(value) is bytes and len(value) == width
                for value, width in zip(output.buffers, widths)), role + ": original capacity/ABI differs")
        return references, output

    def _qpc(self, role):
        references, output = self._call("QueryPerformanceCounter", (), role, (8,))
        value = {"return": references["return"], "error": references["error"], "counter": references["buffer0"]}
        require(int.from_bytes(output.result, "little") != 0, role + ": original QPC failed")
        require(0 < int.from_bytes(output.buffers[0], "little") <= 0x7FFFFFFFFFFFFFFF, role + ": invalid QPC counter")
        return value

    def _identity(self, role):
        identity = self.parameters["identity"]
        handle = identity["handle"]
        pid, pid_output = self._call("GetProcessId", (handle,), role + ".pid", ())
        times, times_output = self._call("GetProcessTimes", (handle,), role + ".times", (32,))
        wait, wait_output = self._call("WaitForSingleObject", (handle, 0), role + ".wait", ())
        clock = self._qpc(role + ".qpc")
        row = dict(handle=handle, pid_return=pid["return"], pid_error=pid["error"], times_return=times["return"],
            times_error=times["error"], filetimes=times["buffer0"], wait_return=wait["return"], wait_error=wait["error"], qpc=clock)
        require(int.from_bytes(pid_output.result, "little") == identity["process_id"], role + ": actual-shaped PID differs")
        require(int.from_bytes(times_output.result, "little") != 0, role + ": original GetProcessTimes failed")
        # Exit FILETIME is undefined while live: retain all32B without consuming it.
        require(struct.unpack("<QQQQ", times_output.buffers[0])[0] == identity["creation_filetime"], role + ": creation differs")
        require(int.from_bytes(wait_output.result, "little") == 258, role + ": retained process not alive")
        return row

    def _read(self, cohort, role):
        state, identity = self.parameters["state"], self.parameters["identity"]
        if role.startswith("state_"):
            field = role.split("_", 2)[2]
            address, count = next((address, 4) for name, address, _ in STATE if name == field)
        elif role.startswith("e0_"):
            address, count = 0x5202E0, 4
        elif role.startswith("header_"):
            address, count = state["surface"], 188
        else:
            require(role == "pixels", "unknown source-owned role")
            address, count = state["base"], state["width"] * state["height"]
        label = f"cohort{cohort}.{role}"
        row = dict(ordinal=(cohort - 1) * len(READ_ROLES) + READ_ROLES.index(role) + 1, role=role,
            api="ReadProcessMemory", handle=identity["handle"], address=address, requested=count,
            identity_before=self._identity(label + ".before"), qpc_begin=self._qpc(label + ".begin"))
        raw, output = self._call("ReadProcessMemory", (identity["handle"], address, count), label + ".rpm", (8, count))
        row.update(native_return=raw["return"], native_error=raw["error"], returned_count=raw["buffer0"], buffer=raw["buffer1"])
        row.update(qpc_end=self._qpc(label + ".end"), identity_after=self._identity(label + ".after"))
        # Genuine-shaped post-read observations are retained even if RPM failed.
        require(int.from_bytes(output.result, "little") != 0, label + ": original RPM failed")
        require(int.from_bytes(output.buffers[0], "little") == count, label + ": original RPM short/extra count")
        return row

    def collect(self):
        require(not self.frozen, "recorder is single-use")
        self.frozen = True
        p = self.parameters
        refs = {}
        journal = dict(schema=self.helper.JOURNAL_SCHEMA, evidence_class="synthetic_fixture", host_architecture="x64",
            binding=p["binding"], identity=p["identity"], frequency=None,
            pause=dict(epoch=p["epoch"], state=p["state"], prefix_sha256=sha(self.plan.prefix), begin=None, end=None),
            cohorts=[], completion=None)
        next_role = "frequency"
        try:
            for role, data in (("commands", self.plan.commands), ("debugger_prefix", self.plan.prefix), ("debugger_final", self.plan.final)):
                refs[role] = self.originals.put(role, data)
            frequency, output = self._call("QueryPerformanceFrequency", (), "frequency", (8,))
            journal["frequency"] = {"return": frequency["return"], "error": frequency["error"], "frequency": frequency["buffer0"]}
            require(int.from_bytes(output.result, "little") != 0 and 0 < int.from_bytes(output.buffers[0], "little") <= 0x7FFFFFFFFFFFFFFF,
                    "original QPF failure/frequency")
            next_role = "pause.begin"
            journal["pause"]["begin"] = self._qpc(next_role)
            for index in range(1, 4):
                cohort = dict(index=index, pause_epoch=p["epoch"], reads=[])
                journal["cohorts"].append(cohort)
                for role in READ_ROLES:
                    next_role = f"cohort{index}.{role}"
                    cohort["reads"].append(self._read(index, role))
            next_role = "pause.end"
            journal["pause"]["end"] = self._qpc(next_role)
        except Exception as error:
            self.original_exceptions.append(error)
            self.failures.append("Source-owned dispatch interrupted at " + next_role + "; exception text unavailable")
            self.missing.append("dispatch interrupted at " + next_role + "; subsequent outputs were not observed")
        try:
            _, fresh_source, fresh_stamp = _helper()
            require(fresh_stamp == self.helper_stamp and fresh_source == self.helper_source,
                    "frozen helper source changed before final replay")
        except Exception as error:
            self.original_exceptions.append(error)
            self.failures.append("helper final rehash failed; original exception object retained without text")
            self.missing.append("helper final rehash exception text unavailable")
        journal["completion"] = dict(status="failed" if self.failures or self.missing else "complete",
            failures=list(self.failures), missing_originals=list(self.missing))
        try:
            journal_bytes = canonical(journal)
            require(len(journal_bytes) <= MAX_JOURNAL, "journal hard capacity exceeded")
            refs["journal"] = self.originals.put("journal", journal_bytes)
            manifest = dict(schema=self.helper.MANIFEST_SCHEMA, evidence_class="synthetic_fixture", binding=p["binding"], artifacts=refs)
            manifest_bytes = canonical(manifest)
            require(len(manifest_bytes) <= MAX_MANIFEST, "manifest hard capacity exceeded")
            # The unchanged helper cannot put failed pre-return calls in a read
            # row. This separate diagnostic sidecar retains EVERY packet's refs.
            retention = dict(schema="clash95_paused_recorder_retention_v2", evidence_class="synthetic_fixture",
                authority={name: False for name in AUTHORITY_FLAGS}, calls=self.packet_references,
                originals=[dict(row.reference(), role=row.role) for row in self.originals.rows],
                failures=self.failures, missing_originals=self.missing,
                original_exception_objects_retained=len(self.original_exceptions),
                scope="Source-issued synthetic packet retention; not native/storage/job provenance")
            retention_bytes = canonical(retention)
            require(len(retention_bytes) <= MAX_RETENTION, "retention sidecar hard capacity exceeded")
            diagnostic = self.helper.replay(manifest, self.originals.freeze())
            diagnostic["recorder_scope"] = "Synthetic fixed-dispatch preparation only; real owner/execute factory unavailable"
            diagnostic["recorder_retained_originals"] = retention["originals"]
            diagnostic["recorder_retained_calls"] = len(self.calls)
            diagnostic["recorder_failures"] = list(self.failures)
            diagnostic["recorder_missing_originals"] = list(self.missing)
            diagnostic["remaining_debts"].append("This recorder has no native adapter, retained job binding, canonical candidate/probe reconstruction or storage-durability proof.")
            require(all(diagnostic[flag] is False for flag in AUTHORITY_FLAGS), "diagnostic cannot issue authority")
            return Recording(manifest_bytes, journal_bytes, retention_bytes, tuple(self.originals.rows), tuple(self.calls), diagnostic,
                             tuple(self.original_exceptions), tuple(self.failures), tuple(self.missing))
        except Exception as error:
            raise RecordingFailure(error, self) from error


class TinySyntheticPublisher:
    """Explicit tiny-file fixture seam; cannot publish a full capture/archive.

    Space is an externally supplied SYNTHETIC observation. This class proves no
    actual reserve/native storage. Existing targets are never overwritten; all
    originals are also retained by the caller on any publication failure.
    """
    def __init__(self, directory, *, free, total, allowance=MAX_TINY_PUBLICATION):
        require(type(allowance) is int and 0 < allowance <= MAX_TINY_PUBLICATION, "tiny fixture allowance required")
        require_reserve(free, total, allowance * 2 + 2 * MAX_TINY_FILES * 4096)
        directory = Path(directory)
        require(directory.is_absolute() and ".." not in directory.parts and not directory.exists(), "new literal tiny-fixture directory required")
        for part in directory.parents:
            info = part.lstat()
            require(not stat.S_ISLNK(info.st_mode) and not (getattr(info, "st_file_attributes", 0) & 0x400), "fixture reparse ancestor")
        self.directory, self.allowance = directory, allowance
        self.rows, self.used, self.failures = [], 0, []
        self.original_exceptions = []
        self.free, self.total = free, total
        directory.mkdir()
        info = directory.lstat()
        self.directory_identity = (info.st_dev, info.st_ino)
        helper, _, _ = _helper()
        canonical_directory = helper.checked_path(str(directory))
        canonical_info = canonical_directory.lstat()
        require(stat.S_ISDIR(info.st_mode) and stat.S_ISDIR(canonical_info.st_mode)
                and not (getattr(canonical_info, "st_file_attributes", 0) & 0x400)
                and (canonical_info.st_dev, canonical_info.st_ino) == self.directory_identity,
                "fixture canonical directory identity changed")
        self.directory = canonical_directory
        self.pending = []

    def put(self, data):
        # Keep the original before budget/path/write checks; no durability claim.
        self.pending.append(data)
        try:
            require(not self.failures, "publication failure remains sticky")
            require(type(data) is bytes and self.used + len(data) <= self.allowance, "tiny fixture hard byte budget")
            require(len(self.rows) < MAX_TINY_FILES, "tiny fixture hard file-count budget")
            require_reserve(self.free, self.total, 2 * self.allowance + 2 * MAX_TINY_FILES * 4096)
            for part in (self.directory, *self.directory.parents):
                info = part.lstat()
                require(not stat.S_ISLNK(info.st_mode) and not (getattr(info, "st_file_attributes", 0) & 0x400), "fixture reparse path")
            info = self.directory.lstat()
            require((info.st_dev, info.st_ino) == self.directory_identity, "fixture output directory identity changed")
            target = self.directory / f"{len(self.rows) + 1:04d}.bin"
            temporary = self.directory / (target.name + ".pending")
            descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
            with os.fdopen(descriptor, "wb") as stream:
                require(stream.write(data) == len(data), "partial fixture write")
                stream.flush()
                os.fsync(stream.fileno())
                info = os.fstat(stream.fileno())
                require(stat.S_ISREG(info.st_mode) and info.st_size == len(data), "fixture opened output differs")
            # Hard-link admission is atomic and non-overwriting on both hosts.
            os.link(temporary, target)
            temporary.unlink()
            info = target.lstat()
            helper, _, _ = _helper()
            require(not getattr(info, "st_file_attributes", 0) & 0x400 and info.st_nlink == 1
                    and helper.bounded_file_read(target, info, len(data)) == data, "fixture identity/bytes differ after publication")
            require((info.st_dev, info.st_ino) not in {(row[1][0], row[1][1]) for row in self.rows}, "fixture physical file identity reused")
            self.rows.append((target, _stamp(info), data))
            self.used += len(data)
            return dict(path=str(target), bytes=len(data), sha256=sha(data))
        except Exception as error:
            self.original_exceptions.append(error)
            self.failures.append("Tiny synthetic publication failed; original exception object retained without text")
            raise

    def unchanged(self):
        require(not self.failures, "publication failure remains sticky")
        helper, _, _ = _helper()
        info = self.directory.lstat()
        require((info.st_dev, info.st_ino) == self.directory_identity
                and helper.checked_path(str(self.directory)) == self.directory, "fixture final directory identity changed")
        for path, stamp, data in self.rows:
            require(helper.checked_path(str(path)) == path and _stamp(path.lstat()) == stamp
                    and path.lstat().st_nlink == 1, "fixture final physical identity changed")
            require(helper.bounded_file_read(path, path.lstat(), len(data)) == data, "fixture final bytes changed")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    arguments = parser.parse_args(argv)
    if arguments.execute:
        parser.error("Native execution/retained-owner factory is unavailable in this source-only slice")
    value = {name: False for name in AUTHORITY_FLAGS}
    value.update(schema="clash95_paused_surface_recorder_preparation_v2", synthetic_only=True,
                 native_owner_factory_available=False, native_execution_available=False, fixed_reads=39,
                 production_verifier_registered=False)
    print(canonical(value).decode())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
