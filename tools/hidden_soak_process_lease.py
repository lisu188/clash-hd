"""Bounded retained-handle ownership for a future hidden-soak producer.

The caller supplies an independently authenticated, in-memory RunAuthority.
Reports cannot create that authority. No launch, approval, job-completeness or
release proof is provided. Unseen children of an exited parent fail closed.
Windows APIs are loaded only when WindowsAdapter is explicitly constructed.
The existing owned_hidden_process host supplies a no-breakaway job boundary;
its original assignment/membership/drain receipts remain separately required.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass
import hashlib
import json
import os
from pathlib import Path, PureWindowsPath
import re
import stat
import time
import uuid

SCHEMA = "hidden_soak_process_lease_v1"
SOURCE = Path(__file__).resolve()
WAIT_OBJECT_0, WAIT_TIMEOUT = 0, 258
SHA = re.compile(r"[0-9a-f]{64}\Z")
MAX_EVENTS, MAX_JSON_BYTES = 4096, 2 * 1024 * 1024


def _require(value, message):
    if not value:
        raise ValueError(message)


def _integer(value, maximum, label, minimum=0):
    _require(type(value) is int and minimum <= value <= maximum, label)


def _path(value):
    _require(type(value) is str and len(value) <= 4096 and bool(re.match(r"^[A-Za-z]:[\\/]", value))
             and not any(c in value for c in "\0\r\n") and ":" not in value[2:]
             and ".." not in PureWindowsPath(value).parts, "absolute unambiguous local Windows path required")
    return str(PureWindowsPath(value)).casefold()


def _digest(value):
    _require(type(value) is str and SHA.fullmatch(value), "canonical SHA-256 required")
    return value


@dataclass(frozen=True)
class Generation:
    pid: int
    creation_filetime: int
    image_path: str
    image_sha256: str

    def __post_init__(self):
        _integer(self.pid, 0xffffffff, "invalid process PID", 1)
        _integer(self.creation_filetime, 0xffffffffffffffff, "invalid creation FILETIME", 1)
        object.__setattr__(self, "image_path", _path(self.image_path))
        _require(self.image_path.endswith(".exe"), "explicit executable identity required")
        _digest(self.image_sha256)


@dataclass(frozen=True)
class Observation:
    generation: Generation
    parent_pid: int
    wait_result: int
    exit_code: int | None
    exit_filetime: int

    def __post_init__(self):
        _require(type(self.generation) is Generation, "typed process generation required")
        _integer(self.parent_pid, 0xffffffff, "invalid native parent PID")
        _require(type(self.wait_result) is int and self.wait_result in (0, 258), "invalid native wait observation")
        _integer(self.exit_filetime, 0xffffffffffffffff, "invalid exit FILETIME")
        if self.wait_result == WAIT_TIMEOUT:
            _require(self.exit_code is None and self.exit_filetime == 0, "live process has an exit receipt")
        else:
            _integer(self.exit_code, 0xffffffff, "invalid signalled exit code")
            _require(self.exit_filetime >= self.generation.creation_filetime, "exit precedes process creation")


@dataclass(frozen=True)
class ImageAuthority:
    role: str
    path: str
    sha256: str

    def __post_init__(self):
        _require(self.role in ("debugger", "candidate", "descendant") and type(self.role) is str, "invalid process role")
        object.__setattr__(self, "path", _path(self.path))
        _require(self.path.endswith(".exe"), "explicit executable authority required")
        _digest(self.sha256)


@dataclass(frozen=True)
class SourcePin:
    path: str
    sha256: str

    def __post_init__(self):
        object.__setattr__(self, "path", _path(self.path))
        _digest(self.sha256)


@dataclass(frozen=True)
class RunAuthority:
    run_id: str
    candidate_sha256: str
    probe_sha256: str
    profile: str
    resolution: str
    stage: str
    controller: Generation
    images: tuple[ImageAuthority, ...]
    source_pins: tuple[SourcePin, ...]

    def __post_init__(self):
        _require(type(self.run_id) is str and uuid.UUID(self.run_id).hex == self.run_id, "canonical caller run UUID required")
        _digest(self.candidate_sha256); _digest(self.probe_sha256)
        for name in ("profile", "resolution", "stage"):
            value = getattr(self, name)
            _require(type(value) is str and 0 < len(value) <= 512 and not any(c in value for c in "\0\r\n"), "invalid caller context")
        _require(type(self.controller) is Generation and type(self.images) is tuple and 2 <= len(self.images) <= 32
                 and all(type(row) is ImageAuthority for row in self.images), "typed caller image authorities required")
        _require(sum(row.role == "debugger" for row in self.images) == 1
                 and sum(row.role == "candidate" for row in self.images) == 1
                 and len({(row.role, row.path) for row in self.images}) == len(self.images), "duplicate/missing image authority")
        _require(next(row.sha256 for row in self.images if row.role == "candidate") == self.candidate_sha256,
                 "candidate image authority differs from caller context")
        _require(type(self.source_pins) is tuple and 1 <= len(self.source_pins) <= 64
                 and all(type(row) is SourcePin for row in self.source_pins)
                 and len({row.path for row in self.source_pins}) == len(self.source_pins)
                 and _path(str(SOURCE)) in {row.path for row in self.source_pins}, "fixed component source pin required")


@dataclass(frozen=True)
class Snapshot:
    pid: int
    parent_pid: int
    observation: Observation | None
    error: str | None = None

    def __post_init__(self):
        _integer(self.pid, 0xffffffff, "invalid snapshot PID", 1)
        _integer(self.parent_pid, 0xffffffff, "invalid snapshot parent PID")
        _require(self.observation is None or type(self.observation) is Observation, "typed snapshot observation required")
        _require(self.error is None or type(self.error) is str and 0 < len(self.error) <= 4096, "invalid snapshot error")
        _require(self.observation is not None or self.error is not None, "snapshot lacks an observation/error")
        if self.observation is not None:
            _require(self.observation.generation.pid == self.pid and self.observation.parent_pid == self.parent_pid,
                     "snapshot identity differs")


def _error(exc):
    return (type(exc).__name__ + ": " + str(exc))[:4096]


def _wire(value):
    return asdict(value) if hasattr(value, "__dataclass_fields__") else value


@dataclass
class _Lease:
    slot: str
    handle: object
    generation: Generation
    role: str
    parent_slot: str | None
    stopped: bool = False
    attempted: bool = False


class ProcessLeases:
    """Own handles, never reusable PIDs; cleanup is bounded and idempotent.

    adapter is a fixed host implementation or a fixture object, never imported
    from an artifact. Callers retain reports externally, including failures.
    """
    def __init__(self, authority, adapter, *, max_adoptions=32, reconciliation_rounds=4, wait_ms=5000):
        _require(type(authority) is RunAuthority, "caller-owned typed authority required; reports are not authority")
        _integer(max_adoptions, 128, "invalid adoption budget", 1)
        _integer(reconciliation_rounds, 16, "invalid reconciliation budget", 2)
        _integer(wait_ms, 30000, "invalid wait budget", 1)
        self.authority, self.adapter = authority, adapter
        self.max_adoptions, self.rounds, self.wait_ms = max_adoptions, reconciliation_rounds, wait_ms
        self.events, self.leases, self.handles = [], {}, {}
        self.closed, self.finished, self.anchor_ok = set(), False, False
        self.counter, self.adoption_exhausted, self.empty_snapshots = 0, False, 0
        # Leave enough bounded space for finish plus every actual handle close,
        # including 4096-character diagnostics. Receipt exhaustion must never
        # interrupt the finally block's closure attempts.
        self.close_reserve = (max_adoptions + 2) * 8192
        self.receipt_bytes = len(json.dumps(_wire(authority)).encode("utf-8")) + 1024
        try:
            _require(self._sources(), "initial producer source authority differs")
            _require(adapter.current_pid() == authority.controller.pid, "controller differs from actual caller PID")
            handle = self._open("controller", authority.controller.pid)
            observation = adapter.observe(handle)
            _require(observation.generation == authority.controller and observation.wait_result == 258, "controller generation differs")
            self.leases["controller"] = _Lease("controller", handle, authority.controller, "controller", None)
            self.anchor_ok = True
            self._event("anchor", observation=_wire(observation), error=None)
        except Exception as exc:
            self._event("anchor", observation=None, error=_error(exc))

    def _event(self, op, **fields):
        event = dict(sequence=len(self.events), monotonic_ns=time.monotonic_ns(), op=op, **fields)
        size = len(json.dumps(event, ensure_ascii=True).encode("utf-8")) + 2
        if op in ("close", "finish"):
            _require(len(self.events) < MAX_EVENTS and self.receipt_bytes + size <= MAX_JSON_BYTES,
                     "reserved closure receipt budget exhausted")
        else:
            self._capacity(size=size)
        self.events.append(event); self.receipt_bytes += size

    def _capacity(self, *, events=1, size=0):
        _require(len(self.events) + events <= MAX_EVENTS - self.max_adoptions - 2
                 and self.receipt_bytes + size <= MAX_JSON_BYTES - self.close_reserve,
                 "process receipt budget exhausted")

    def _sources(self):
        self._capacity()
        rows, error = [], None
        try:
            for pin in self.authority.source_pins:
                actual = self.adapter.source_sha256(pin.path)
                rows.append(dict(path=pin.path, sha256=actual))
                _require(actual == pin.sha256, "producer source changed: " + pin.path)
        except Exception as exc:
            error = _error(exc)
        self._event("sources", rows=rows, error=error)
        return error is None

    def _open(self, slot, pid):
        self._capacity()
        try:
            handle = self.adapter.open_process(pid)
            _require(handle is not None, "native open returned no handle")
            self.handles[slot] = handle
            self._event("open", slot=slot, pid=pid, error=None)
            return handle
        except Exception as exc:
            self._event("open", slot=slot, pid=pid, error=_error(exc))
            raise

    def _close(self, slot):
        if slot in self.closed or slot not in self.handles:
            return
        self.closed.add(slot)  # exactly one attempt, including denied closes
        try:
            results = self.adapter.close(self.handles[slot])
            self._event("close", slot=slot, results=results, error=None)
        except Exception as exc:
            self._event("close", slot=slot, results=[], error=_error(exc))

    def adopt(self, expected, role, parent_slot="controller"):
        _require(not self.finished, "lease collection is closed")
        _require(type(expected) is Generation and type(role) is str, "typed expected generation/role required")
        if self.counter >= self.max_adoptions:
            if not self.adoption_exhausted:
                self.adoption_exhausted = True
                self._event("denied", pid=expected.pid, error="adoption attempt budget exhausted")
            return None
        self._capacity(events=3)
        self.counter += 1; slot = f"process-{self.counter:04d}"
        fields = dict(slot=slot, role=role, parent_slot=parent_slot, expected=_wire(expected),
                      observation=None, child_after=None, parent_before=None, parent_current=None, parent_after=None)
        try:
            _require(self.anchor_ok and self._sources(), "unverified controller/source authority")
            _require(not any(row.generation.pid == expected.pid for key,row in self.leases.items() if key != "controller"),
                     "duplicate or reused owned PID")
            _require(any(row.role == role and row.path == expected.image_path and row.sha256 == expected.image_sha256
                         for row in self.authority.images), "image/role outside caller authority")
            parent = self.leases[parent_slot]
            before = self.adapter.observe(parent.handle); fields["parent_before"] = _wire(before)
            _require(before.generation == parent.generation and before.wait_result == 258, "parent generation vanished or changed")
            handle = self._open(slot, expected.pid)
            observed = self.adapter.observe(handle); fields["observation"] = _wire(observed)
            current = self.adapter.parent_generation(handle); fields["parent_current"] = _wire(current)
            after = self.adapter.observe(parent.handle); fields["parent_after"] = _wire(after)
            child_after = self.adapter.observe(handle); fields["child_after"] = _wire(child_after)
            _require(observed.generation == expected and observed.wait_result == 258, "opened process differs from enumerated/launch generation")
            _require(child_after.generation == expected and child_after.wait_result == 258
                     and child_after.parent_pid == observed.parent_pid, "child changed during parent attestation")
            _require(observed.parent_pid == parent.generation.pid and current == parent.generation
                     and after.generation == parent.generation and after.wait_result == 258
                     and expected.creation_filetime >= parent.generation.creation_filetime,
                     "native parent generation or birth window differs")
            self.leases[slot] = _Lease(slot, handle, expected, role, parent_slot)
            self._event("adopt", **fields, error=None)
            return slot
        except Exception as exc:
            self._event("adopt", **fields, error=_error(exc)); self._close(slot)
            return None

    def discover(self):
        _require(not self.finished, "lease collection is closed")
        rows, error = [], None
        try:
            _require(self.anchor_ok and self._sources(), "unverified enumeration authority")
            rows = self.adapter.enumerate(tuple(row.generation.pid for row in self.leases.values()),
                                          tuple(row.generation.pid for key,row in self.leases.items() if key != "controller"))
            _require(type(rows) is tuple and len(rows) <= 512 and all(type(row) is Snapshot for row in rows)
                     and len({row.pid for row in rows}) == len(rows), "missing/duplicate/unbounded native snapshot")
        except Exception as exc:
            error = _error(exc); rows = ()
        self._event("enumerate", rows=[_wire(row) for row in rows], error=error)
        self.empty_snapshots = self.empty_snapshots+1 if not rows and error is None else 0
        for row in rows:
            if row.error is not None:
                continue  # the original enumeration row itself retains failure
            known = next((lease for lease in self.leases.values() if lease.generation.pid == row.pid), None)
            if known is not None:
                continue
            parent = next((lease for lease in self.leases.values() if lease.generation.pid == row.parent_pid), None)
            if parent is None:
                continue  # replay rejects absence of a retained parent directly
            generation = row.observation.generation
            matches = [image for image in self.authority.images if image.path == generation.image_path and image.sha256 == generation.image_sha256]
            role = next((image.role for image in matches if image.role == "candidate"), "descendant")
            self.adopt(generation, role, parent.slot)
        return rows

    def attested_handle(self, slot):
        """Borrow the already owned handle after fresh generation/source checks."""
        _require(not self.finished and slot in self.leases and slot != "controller", "no live owned lease")
        lease = self.leases[slot]
        observation, error = None, None
        try:
            _require(self._sources(), "producer source changed")
            observation = self.adapter.observe(lease.handle)
            _require(observation.generation == lease.generation and observation.wait_result == 258, "owned process changed or exited")
        except Exception as exc:
            error = _error(exc)
        self._event("attest", slot=slot, observation=_wire(observation), error=error)
        if error is not None:
            raise ValueError(error)
        return lease.handle

    def _stop(self, lease):
        if lease.attempted:
            return
        self._capacity(events=3)
        lease.attempted = True
        observed, result, error = None, None, None
        try:
            _require(self._sources(), "producer source changed before termination")
            observed = self.adapter.observe(lease.handle)
            _require(observed.generation == lease.generation, "retained process identity changed before termination")
            if observed.wait_result == 258:
                result = self.adapter.terminate(lease.handle)
        except Exception as exc:
            error = _error(exc)
        self._event("terminate", slot=lease.slot, observation=_wire(observed), result=result, error=error)
        # A raw denied TerminateProcess result still permits a retained-handle
        # wait, but remains a failure. An identity/source attestation exception
        # prevents further process operations; cleanup still attempts closure.
        waited, after, wait_error = None, None, None
        try:
            if error is None:
                waited = self.adapter.wait(lease.handle, self.wait_ms)
                after = self.adapter.observe(lease.handle)
                lease.stopped = (waited["wait_result"] == 0 and after.generation == lease.generation
                                 and after.wait_result == 0 and after.exit_code == waited["exit_code"])
        except Exception as exc:
            wait_error = _error(exc)
        self._event("wait", slot=lease.slot, milliseconds=self.wait_ms, result=waited,
                    observation=_wire(after), error=wait_error)

    def cleanup(self):
        if self.finished:
            return self.report()
        try:
            # Discover while ancestors are live, before debugger-first cleanup.
            for _ in range(self.rounds):
                count = len(self.leases); self.discover()
                if len(self.leases) == count:
                    break
            empty = 0
            for _ in range(self.rounds):
                self._sources()
                ordered = sorted((row for key,row in self.leases.items() if key != "controller"),
                                 key=lambda row: (row.role != "debugger", -row.generation.creation_filetime))
                for lease in ordered:
                    self._stop(lease)
                rows = self.discover()
                empty = empty+1 if not rows else 0
                if empty == 2:
                    break
            self._event("finish", empty_snapshots=self.empty_snapshots, error=None)
        except Exception as exc:
            self._event("finish", empty_snapshots=0, error=_error(exc))
        finally:
            for slot in tuple(self.handles):
                self._close(slot)
            self.finished = True
        return self.report()

    def report(self):
        raw = dict(schema=SCHEMA, authority=_wire(self.authority), events=deepcopy(self.events),
                   host_cleanup_complete=False, release_acceptance=False, runtime_acceptance=False,
                   manual_input_proof=False, promotion_ready=False,
                   required_future_capability="raw authenticated no-breakaway job assignment, membership and drain receipts")
        measured = replay_receipts(raw, self.authority)
        raw["owned_handles_cleanup_verified"] = measured["owned_handles_cleanup_verified"]
        raw["failures"] = measured["failures"]
        return raw


def _generation(raw):
    _require(type(raw) is dict and set(raw) == {"pid","creation_filetime","image_path","image_sha256"}, "missing/extra generation fields")
    return Generation(**raw)


def _observation(raw):
    _require(type(raw) is dict and set(raw) == {"generation","parent_pid","wait_result","exit_code","exit_filetime"}, "missing/extra observation fields")
    return Observation(_generation(raw["generation"]), raw["parent_pid"], raw["wait_result"], raw["exit_code"], raw["exit_filetime"])


def _native_result(raw):
    _require(type(raw) is dict and set(raw) == {"return_value","error_code"}, "missing/extra native result fields")
    _require(type(raw["return_value"]) is int and raw["return_value"] in (0,1), "invalid native BOOL")
    _integer(raw["error_code"], 0xffffffff, "invalid native error code")
    _require(raw == {"return_value":1,"error_code":0}, "native operation failed")


def replay_receipts(report, authority):
    """Recompute scoped ownership cleanup from raw receipts and external authority.

    This does not attest that a file is genuine native output; the fixed producer
    and immutable artifact provenance remain the host verifier's responsibility.
    """
    failures, opened, adopted, closed, stopped, terminated = [], {}, {}, set(), set(), set()
    adoption_outcomes, last_wait = set(), -1
    anchor, finish, last_time, latest_source = False, False, -1, -1
    pending, last_empty_count = {}, 0
    fields = {
        "sources":{"rows"}, "open":{"slot","pid"}, "anchor":{"observation"},
        "adopt":{"slot","role","parent_slot","expected","observation","child_after","parent_before","parent_current","parent_after"},
        "attest":{"slot","observation"}, "enumerate":{"rows"}, "denied":{"pid"},
        "terminate":{"slot","observation","result"}, "wait":{"slot","milliseconds","result","observation"},
        "close":{"slot","results"}, "finish":{"empty_snapshots"},
    }
    def reject(message): failures.append(message)
    try:
        _require(type(authority) is RunAuthority and type(report) is dict and report.get("schema") == SCHEMA,
                 "typed external authority/versioned process receipts required")
        core={"schema","authority","events","required_future_capability","host_cleanup_complete",
              "release_acceptance","runtime_acceptance","manual_input_proof","promotion_ready"}
        _require(core<=set(report)<=core|{"owned_handles_cleanup_verified","failures"},
                 "missing/extra top-level process receipt fields")
        _require(report["required_future_capability"]=="raw authenticated no-breakaway job assignment, membership and drain receipts",
                 "required original host job receipts differ")
        _require(json.dumps(report.get("authority"),sort_keys=True) == json.dumps(_wire(authority),sort_keys=True), "run authority rebound")
        for field in ("host_cleanup_complete","release_acceptance","runtime_acceptance","manual_input_proof","promotion_ready"):
            _require(report.get(field) is False, "unsupported acceptance claim: "+field)
        events = report.get("events")
        _require(type(events) is list and len(events) <= MAX_EVENTS
                 and len(json.dumps(report).encode("utf-8")) <= MAX_JSON_BYTES,
                 "bounded ordered receipt inventory required")
        for sequence,event in enumerate(events):
            _require(type(event) is dict and type(event.get("sequence")) is int and event["sequence"] == sequence, "missing/duplicate/reordered receipt")
            _integer(event.get("monotonic_ns"),0x7fffffffffffffff,"invalid receipt clock")
            _require(event["monotonic_ns"] >= last_time, "receipt clock went backwards"); last_time=event["monotonic_ns"]
            op, error = event.get("op"), event.get("error")
            _require(type(op) is str and op in fields and set(event)==fields[op]|{"sequence","monotonic_ns","op","error"}, "missing/extra receipt fields")
            _require(not finish or op=="close", "process operations after finish")
            _require(error is None or type(error) is str and 0 < len(error) <= 4096, "invalid failure diagnostic")
            if error is not None:
                reject(op+": "+error)
            if op == "sources":
                _require(event.get("rows") == [_wire(pin) for pin in authority.source_pins], "producer source inventory differs")
                latest_source=sequence
            elif op == "open":
                slot=event.get("slot"); _require(type(slot) is str and slot not in opened, "duplicate/missing open slot")
                _integer(event.get("pid"),0xffffffff,"invalid opened PID",1)
                _require(latest_source==sequence-1, "open lacks fresh source checkpoint")
                if error is None: opened[slot]=event["pid"]
            elif op == "anchor":
                _require(not anchor and "controller" in opened, "missing/duplicate controller anchor")
                if error is None:
                    _require(sequence==2 and latest_source==0 and opened["controller"]==authority.controller.pid, "startup source/open ordering differs")
                    observed=_observation(event["observation"])
                    _require(observed.generation == authority.controller and observed.wait_result == 258, "controller anchor differs")
                    adopted["controller"]=(authority.controller,"controller",None); anchor=True
            elif op == "adopt":
                slot=event.get("slot")
                _require(type(slot) is str and slot!="controller" and slot not in closed
                         and slot not in adoption_outcomes,"duplicate/closed/nonprocess adoption outcome")
                if slot in opened:
                    adoption_outcomes.add(slot)
                else:
                    _require(error is not None,"adoption lacks a successful retained open")
                if error is not None: continue
                slot,parent,role=event.get("slot"),event.get("parent_slot"),event.get("role")
                _require(anchor and slot in opened and slot not in adopted and parent in adopted
                         and slot not in closed and parent not in closed
                         and latest_source==sequence-2 and events[sequence-1].get("slot")==slot
                         and events[sequence-1].get("op")=="open", "adoption lacks fresh sources/owned open/live parent")
                expected=_generation(event["expected"]); observed=_observation(event["observation"])
                _require(opened[slot] == expected.pid and observed.generation == expected and observed.wait_result == 258,
                         "adopted generation differs")
                child_after=_observation(event["child_after"])
                _require(child_after.generation==expected and child_after.wait_result==258
                         and child_after.parent_pid==observed.parent_pid,"child changed during parent attestation")
                parent_generation=adopted[parent][0]
                _require(observed.parent_pid == parent_generation.pid and expected.creation_filetime >= parent_generation.creation_filetime,
                         "parent PID/birth differs")
                for key in ("parent_before","parent_after"):
                    row=_observation(event[key]); _require(row.generation == parent_generation and row.wait_result == 258,"parent vanished or changed")
                _require(_generation(event["parent_current"]) == parent_generation, "native parent generation differs")
                _require(any(row.role == role and row.path == expected.image_path and row.sha256 == expected.image_sha256 for row in authority.images), "image authority differs")
                _require(not any(value[0].pid == expected.pid for value in adopted.values()), "duplicate/reused adopted PID")
                if expected.pid in pending:
                    snapshot=pending.pop(expected.pid)
                    _require(snapshot.generation==expected and snapshot.parent_pid==parent_generation.pid,
                             "adoption differs from its preceding native snapshot")
                adopted[slot]=(expected,role,parent)
            elif op == "attest":
                _require(event["slot"] in adopted and event["slot"] not in closed
                         and latest_source==sequence-1, "attestation uses unowned/closed handle/stale sources")
                if error is None:
                    row=_observation(event["observation"]); _require(row.generation == adopted[event["slot"]][0] and row.wait_result == 258,"attestation differs")
            elif op == "enumerate":
                _require(anchor and "controller" not in closed and not pending,
                         "enumeration lacks live owned anchor or omits adoption of a previously discovered child")
                _require(latest_source==sequence-1, "enumeration lacks fresh source checkpoint")
                rows=event.get("rows"); _require(type(rows) is list and len(rows)<=512 and len({row["pid"] for row in rows})==len(rows), "missing/duplicate enumeration")
                last_empty_count=last_empty_count+1 if not rows and error is None else 0
                for row in rows:
                    _require(type(row) is dict and set(row)=={"pid","parent_pid","observation","error"}, "invalid snapshot fields")
                    snapshot=Snapshot(row["pid"],row["parent_pid"],None if row["observation"] is None else _observation(row["observation"]),row["error"])
                    if row["error"]:
                        reject("enumeration: "+row["error"]); continue
                    known=next((slot for slot,value in adopted.items() if value[0].pid==snapshot.pid),None)
                    if known is not None:
                        _require(known not in closed and snapshot.observation.generation==adopted[known][0],
                                 "enumeration detected owned PID reuse or closed handle")
                        parent=adopted[known][2]
                        if parent is not None:
                            _require(snapshot.parent_pid==adopted[parent][0].pid,"enumeration changed native parent PID")
                    else:
                        parent=next((slot for slot,value in adopted.items() if value[0].pid==snapshot.parent_pid),None)
                        _require(parent is not None and parent not in closed and parent not in stopped
                                 and snapshot.observation.wait_result==258,
                                 "unseen child's parent vanished or lacks a retained live parent generation")
                        pending[snapshot.pid]=snapshot.observation
            elif op == "denied":
                _require(error is not None,"denial lacks diagnostic")
            elif op == "terminate":
                slot=event.get("slot"); _require(slot in adopted and slot != "controller" and slot not in closed
                    and slot not in terminated and latest_source==sequence-1, "duplicate/unowned/closed termination or stale sources")
                _require(not pending,"termination precedes adoption of discovered children")
                if adopted[slot][1] != "debugger":
                    _require(all(key in stopped for key,value in adopted.items() if value[1]=="debugger"),
                             "cleanup does not stop/wait for debugger first")
                terminated.add(slot)
                if error is None:
                    row=_observation(event["observation"]); _require(row.generation == adopted[slot][0],"termination identity differs")
                    if row.wait_result==258: _native_result(event["result"])
                    else: _require(event["result"] is None,"already-exited process was terminated")
            elif op == "wait":
                slot=event.get("slot"); _require(slot in adopted and slot != "controller" and slot not in stopped
                    and slot not in closed and slot in terminated and events[sequence-1].get("op")=="terminate"
                    and events[sequence-1].get("slot")==slot, "duplicate/unowned/closed wait or missing matching terminate receipt")
                _integer(event.get("milliseconds"),30000,"invalid bounded wait",1)
                last_wait=sequence
                if error is None:
                    raw=event.get("result"); _require(type(raw) is dict and set(raw)=={"wait_result","error_code","exit_code"},"invalid wait result fields")
                    _require(type(raw["wait_result"]) is int and raw["wait_result"]==0 and type(raw["error_code"]) is int and raw["error_code"]==0,"native wait failed/timed out")
                    _integer(raw["exit_code"],0xffffffff,"invalid waited exit code")
                    row=_observation(event["observation"])
                    _require(row.generation == adopted[slot][0] and row.wait_result==0 and row.exit_code==raw["exit_code"],"post-wait identity differs")
                    stopped.add(slot)
            elif op == "close":
                slot=event.get("slot"); _require(slot in opened and slot not in closed,"missing/duplicate close receipt")
                _require(slot=="controller" or slot in adoption_outcomes,"opened process lacks its adoption outcome before close")
                _require(slot not in adopted or finish, "adopted handle closed before finish")
                results=event.get("results"); _require(type(results) is list and len(results)==1
                    and type(results[0]) is dict and results[0].get("kind")=="process","invalid native close inventory")
                for row in results:
                    _require(type(row) is dict and set(row)=={"kind","return_value","error_code"},"invalid close fields")
                    _native_result({key:row[key] for key in ("return_value","error_code")})
                closed.add(slot)
            elif op == "finish":
                _require(not finish,"duplicate finish receipt"); finish=True
                _require(not pending,"finish omits adoption of discovered children")
                _require(set(adopted)-{"controller"}==stopped, "finish precedes owned child waits")
                _require(type(event.get("empty_snapshots")) is int and event["empty_snapshots"]==last_empty_count
                         and last_empty_count>=2,"final descendants not cleared")
                snapshots=[row for row in events[:sequence] if row.get("op")=="enumerate"]
                _require(len(snapshots)>=2 and all(row["rows"]==[] and row["error"] is None for row in snapshots[-2:]),"missing two final empty native snapshots")
                _require(last_wait>=0 and all(row["sequence"]>last_wait for row in snapshots[-2:])
                         and snapshots[-1]["sequence"]==sequence-1
                         and all(row["op"] in ("sources","enumerate") for row in events[last_wait+1:sequence]),
                         "final empty snapshots must follow the final owned wait without later process operations")
            else:
                raise ValueError("unknown receipt operation")
        _require(anchor and finish and latest_source>=0 and set(opened)==closed
                 and set(adopted)-{"controller"}==stopped==terminated,"missing source/anchor/terminate/wait/close/finish receipts")
        _require(set(opened)-{"controller"}==adoption_outcomes,"missing/duplicate retained-open adoption outcomes")
        _require(sum(value[1]=="debugger" for value in adopted.values())==1
                 and sum(value[1]=="candidate" for value in adopted.values())==1,
                 "missing/duplicate debugger or candidate generation receipts")
    except (ValueError,TypeError,KeyError,AttributeError,RecursionError,OverflowError) as exc:
        reject(_error(exc))
    if type(report) is dict and "owned_handles_cleanup_verified" in report and report["owned_handles_cleanup_verified"] is not (not failures):
        reject("claimed cleanup differs from raw receipt replay")
    if type(report) is dict and "failures" in report:
        expected=list(dict.fromkeys(failures))
        if type(report["failures"]) is not list or report["failures"]!=expected:
            reject("claimed failure diagnostics differ from raw receipt replay")
    return dict(owned_handles_cleanup_verified=not failures, failures=list(dict.fromkeys(failures)),
                host_cleanup_complete=False,release_acceptance=False)


def load_receipts(data):
    _require(type(data) is bytes and len(data)<=MAX_JSON_BYTES,"bounded raw receipt JSON required")
    def unique(pairs):
        result={}
        for key,value in pairs:
            _require(key not in result,"duplicate JSON field"); result[key]=value
        return result
    return json.loads(data.decode("utf-8"),object_pairs_hook=unique,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError("nonfinite JSON value")))


class WindowsAdapter:
    """Lazy native adapter. No enumeration/open/termination occurs at import.

    Toolhelp ancestry alone cannot authenticate vanished unseen ancestors. The
    adapter provides parent PID plus a freshly opened parent generation; the
    collection additionally requires its retained parent to remain live.
    """
    def __init__(self):
        if os.name != "nt": raise OSError("Windows process leases require Windows")
        import ctypes as c
        from ctypes import wintypes as w
        self.c,self.w=c,w; self.k=c.WinDLL("kernel32",use_last_error=True)
        self._handles={}; self._parents={}
        signatures={
            "OpenProcess":([w.DWORD,w.BOOL,w.DWORD],w.HANDLE),"CloseHandle":([w.HANDLE],w.BOOL),
            "GetProcessId":([w.HANDLE],w.DWORD),"GetProcessTimes":([w.HANDLE,c.c_void_p,c.c_void_p,c.c_void_p,c.c_void_p],w.BOOL),
            "QueryFullProcessImageNameW":([w.HANDLE,w.DWORD,w.LPWSTR,c.POINTER(w.DWORD)],w.BOOL),
            "WaitForSingleObject":([w.HANDLE,w.DWORD],w.DWORD),"GetExitCodeProcess":([w.HANDLE,c.POINTER(w.DWORD)],w.BOOL),
            "TerminateProcess":([w.HANDLE,w.UINT],w.BOOL),
            "CreateToolhelp32Snapshot":([w.DWORD,w.DWORD],w.HANDLE),
        }
        for name,(args,result) in signatures.items():
            fn=getattr(self.k,name); fn.argtypes=args; fn.restype=result

    def current_pid(self): return os.getpid()

    @staticmethod
    def source_sha256(path):
        target=Path(path)
        def identity(info):
            return info.st_dev,info.st_ino,info.st_size,info.st_mtime_ns
        def plain_path():
            for item in (target,*target.parents):
                info=item.lstat()
                _require(not stat.S_ISLNK(info.st_mode) and not getattr(info,"st_file_attributes",0)&0x400,"reparse source/image path")
            _require(_path(str(target.resolve(strict=True)))==_path(str(target)),"source/image path resolved outside authority")
        plain_path()
        before=target.stat()
        _require(stat.S_ISREG(before.st_mode) and 0<=before.st_size<=256*1024*1024,"source/image hash budget exceeded")
        digest=hashlib.sha256()
        with target.open("rb") as stream:
            _require(identity(os.fstat(stream.fileno()))==identity(before),"source/image changed before opening")
            count=0
            while block:=stream.read(1024*1024):
                count+=len(block)
                _require(count<=before.st_size,"source/image grew while hashing")
                digest.update(block)
            _require(count==before.st_size and identity(os.fstat(stream.fileno()))==identity(before),
                     "source/image changed while hashing")
        after=target.stat()
        plain_path()
        _require(identity(before)==identity(after),"source/image changed while hashing")
        return digest.hexdigest()

    def open_process(self,pid):
        _integer(pid,0xffffffff,"invalid native PID",1)
        handle=self.k.OpenProcess(0x1000|0x100000|1,False,pid)
        if not handle: raise OSError(self.c.get_last_error(),"OpenProcess")
        self._handles[handle]=False
        self._parents.pop(handle,None)
        return handle

    def _check_handle(self,handle):
        _require(handle in self._handles and self._handles[handle] is False,"unknown/closed retained handle")

    def _parent_pid(self,handle,*,exited=False):
        if exited:
            # Never look up a signalled retained handle's reusable PID. A new
            # process can already occupy that Toolhelp row. Only a previously
            # observed live parent is available, and no ownership is granted.
            return self._parents.get(handle,0)
        pid=int(self.k.GetProcessId(handle))
        found=next((parent for current,parent in self._entries() if current==pid),None)
        if found is not None:
            self._parents[handle]=found
            return found
        raise ValueError("live process missing from native snapshot")

    def observe(self,handle):
        self._check_handle(handle); c,w=self.c,self.w
        path=c.create_unicode_buffer(32768); length=w.DWORD(32768)
        if not self.k.QueryFullProcessImageNameW(handle,0,path,c.byref(length)): raise OSError(c.get_last_error(),"QueryFullProcessImageNameW")
        result=self.k.WaitForSingleObject(handle,0); code=None
        if result not in (0,258): raise OSError(c.get_last_error(),"WaitForSingleObject")
        times=[c.c_uint64() for _ in range(4)]
        if not self.k.GetProcessTimes(handle,*(c.byref(row) for row in times)): raise OSError(c.get_last_error(),"GetProcessTimes")
        if result==258 and times[1].value:
            result=self.k.WaitForSingleObject(handle,0)
            if result!=0: raise OSError(c.get_last_error(),"process exit changed during observation")
        if result==0:
            raw=w.DWORD()
            if not self.k.GetExitCodeProcess(handle,c.byref(raw)): raise OSError(c.get_last_error(),"GetExitCodeProcess")
            code=raw.value  # 259 is a legitimate exit code after a signalled wait
        generation=Generation(int(self.k.GetProcessId(handle)),times[0].value,path.value,self.source_sha256(path.value))
        return Observation(generation,self._parent_pid(handle,exited=result==0),result,code,times[1].value)

    def parent_generation(self,handle):
        self._check_handle(handle); parent=self.open_process(self._parent_pid(handle))
        try: return self.observe(parent).generation
        finally:
            results=self.close(parent)
            _require(all(row["return_value"]==1 for row in results),"parent query handle close failed")

    def terminate(self,handle):
        self._check_handle(handle); result=int(self.k.TerminateProcess(handle,1))
        return dict(return_value=result,error_code=0 if result else self.c.get_last_error())

    def wait(self,handle,milliseconds):
        self._check_handle(handle); result=int(self.k.WaitForSingleObject(handle,milliseconds)); code=None
        error=0
        if result==0:
            raw=self.w.DWORD()
            if self.k.GetExitCodeProcess(handle,self.c.byref(raw)): code=raw.value
            else: error=self.c.get_last_error()
        elif result!=258: error=self.c.get_last_error()
        return dict(wait_result=result,error_code=error,exit_code=code)

    def close(self,handle):
        self._check_handle(handle); self._handles[handle]=True
        self._parents.pop(handle,None)
        result=int(self.k.CloseHandle(handle))
        return [dict(kind="process",return_value=result,error_code=0 if result else self.c.get_last_error())]

    def _entries(self):
        c,w=self.c,self.w
        class Entry(c.Structure):
            _fields_=[("size",w.DWORD),("usage",w.DWORD),("pid",w.DWORD),("heap",c.c_size_t),
                      ("module",w.DWORD),("threads",w.DWORD),("parent",w.DWORD),("priority",w.LONG),
                      ("flags",w.DWORD),("exe",w.WCHAR*260)]
        for name in ("Process32FirstW","Process32NextW"):
            fn=getattr(self.k,name); fn.argtypes=[w.HANDLE,c.POINTER(Entry)]; fn.restype=w.BOOL
        snapshot=self.k.CreateToolhelp32Snapshot(2,0)
        if snapshot in (None,0,c.c_void_p(-1).value): raise OSError(c.get_last_error(),"CreateToolhelp32Snapshot")
        rows=[]; entry=Entry(); entry.size=c.sizeof(entry)
        try:
            ok=self.k.Process32FirstW(snapshot,c.byref(entry))
            while ok:
                rows.append((int(entry.pid),int(entry.parent)))
                _require(len(rows)<=65536,"native process snapshot budget exceeded")
                ok=self.k.Process32NextW(snapshot,c.byref(entry))
            _require(c.get_last_error()==18,"native enumeration ended without ERROR_NO_MORE_FILES")
        finally:
            if not self.k.CloseHandle(snapshot): raise OSError(c.get_last_error(),"Close native snapshot")
        return tuple(rows)

    def enumerate(self,parent_pids,known_pids):
        rows=[]
        for pid,parent in self._entries():
            if parent not in parent_pids and pid not in known_pids: continue
            handle=None
            try:
                handle=self.open_process(pid); observed=self.observe(handle)
                row=Snapshot(pid,parent,observed)
            except Exception as exc:
                row=Snapshot(pid,parent,None,_error(exc))
            finally:
                if handle is not None:
                    results=self.close(handle)
                    if not all(value["return_value"]==1 for value in results):
                        row=Snapshot(pid,parent,row.observation,"snapshot handle close failed")
            rows.append(row); _require(len(rows)<=512,"native descendant snapshot budget exceeded")
        return tuple(rows)
