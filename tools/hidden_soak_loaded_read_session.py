"""Adapter-only initial-loader receipts; no native producer or storage adapter.

Source-issued canonical preparation may precede launch. A previously held
checkpoint never moves: any reconstruction under that hold is charged by the
first original counter receipt. Raw partial reads and incomplete phases remain
original RAM attempts; they cannot become fabricated complete observations.
"""
from __future__ import annotations

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
SOURCE = "tools/hidden_soak_loaded_read_session.py"
ORACLE = "tools/hidden_soak_loaded_image.py"
ORACLE_SHA256 = "5c59a3498f0f5a03967e2375ca92defd05883cb918bffa353b387acce129251e"
SCHEMA = "hidden_soak_loaded_read_session_v1"
SECOND, HOLD_SECONDS = 1_000_000_000, 20
U63, U32 = (1 << 63) - 1, (1 << 32) - 1
RAW_SCOPE_BYTES = 16 * 1024 * 1024
RAW_TEMPORARY_BYTES = 64 * 1024 + 3
METADATA_BYTES = 8 * 1024 * 1024
REPORT_RESERVE_BYTES = 64 * 1024
MAX_RECEIPTS = 32768
FALSE_CLAIMS = {name: False for name in (
    "passed", "native_producer_provenance_verified", "native_read_lease_verified", "native_coherence_verified",
    "native_clock_verified", "native_precision_verified", "running_duration_verified", "loaded_candidate_verified",
    "loaded_probe_verified", "probe_executed", "no_breakaway_job_verified", "runtime_acceptance",
    "release_acceptance", "manual_input_verified", "promotion_ready", "stable")}


def _require(value, message):
    if not value: raise ValueError(message)


def _integer(value, minimum, maximum, label):
    _require(type(value) is int and minimum <= value <= maximum, label)


def _token(value):
    _require(type(value) is str and uuid.UUID(value).hex == value, "original canonical epoch/token required")


def _hash(raw):
    _require(type(raw) is bytes, "original byte string required")
    return hashlib.sha256(raw).hexdigest()


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")


def budget():
    return dict(raw_scope_bytes=RAW_SCOPE_BYTES, raw_temporary_bytes=RAW_TEMPORARY_BYTES,
                metadata_bytes=METADATA_BYTES, metadata_atomic_temporary_bytes=METADATA_BYTES,
                additional_disk_peak_bytes=RAW_SCOPE_BYTES + RAW_TEMPORARY_BYTES + 2 * METADATA_BYTES,
                excluded=["canonical candidate/original/source RAM", "native host and assets", "job/generation receipts",
                          "frame ledger and running transcript", "over-capacity complete original Pending RAM"],
                scope="known raw/metadata retention allowance only; no disk writes or reserve bypass installed")


@dataclass(frozen=True)
class QpcAnchor:
    epoch_id: str
    frequency_hz: int
    origin_tick: int
    origin_ns: int
    held_start_tick: int

    def __post_init__(self):
        _token(self.epoch_id)
        _integer(self.frequency_hz, 1, SECOND, "bounded independently frozen QPC frequency required")
        _integer(self.origin_tick, 1, U63, "independent original QPC origin required")
        _integer(self.origin_ns, 1, U63 - HOLD_SECONDS * SECOND, "independent ns epoch origin required")
        _integer(self.held_start_tick, self.origin_tick, U63 - HOLD_SECONDS * self.frequency_hz,
                 "unchanged independent held checkpoint tick required")


@dataclass(frozen=True)
class QpcSample:
    epoch_id: str
    frequency_hz: int
    tick: int
    frequency_native_return: int
    frequency_native_error: int
    counter_native_return: int
    counter_native_error: int

    def __post_init__(self):
        _token(self.epoch_id)
        for name in ("frequency_hz", "tick"):
            _integer(getattr(self, name), -(1 << 63), U63, "original LARGE_INTEGER required")
        for name in ("frequency_native_return", "counter_native_return"):
            _integer(getattr(self, name), -(1 << 31), U32, "original native BOOL scalar required")
        for name in ("frequency_native_error", "counter_native_error"):
            _integer(getattr(self, name), 0, U32, "original native DWORD error required")


@dataclass(frozen=True)
class Projection:
    original_tick: int
    elapsed_ticks: int
    numerator_ns: int
    denominator_hz: int
    remainder: int
    lower_ns: int
    upper_ns: int


def project(anchor, tick):
    """Exact rational interval; the fractional remainder is never discarded."""
    _require(type(anchor) is QpcAnchor, "typed independent anchor required")
    _integer(tick, anchor.origin_tick, U63, "original counter precedes fixed epoch")
    elapsed = tick - anchor.origin_tick
    numerator = elapsed * SECOND
    quotient, remainder = divmod(numerator, anchor.frequency_hz)
    lower = anchor.origin_ns + quotient
    upper = lower + bool(remainder)
    _require(upper <= U63, "QPC projection exceeds bounded ns extent")
    return Projection(tick, elapsed, numerator, anchor.frequency_hz, remainder, lower, upper)


@dataclass(frozen=True)
class OwnerObservation:
    run_id: str
    checkpoint_id: str
    clock_epoch: str
    controller: object
    debugger: object
    target: object
    wait_results: tuple
    native_errors: tuple
    probe_sequence: int
    breakpoint_sequence: int
    command_sequence: int

    def __post_init__(self):
        for value in (self.run_id, self.checkpoint_id, self.clock_epoch): _token(value)
        for rows in (self.wait_results, self.native_errors):
            _require(type(rows) is tuple and len(rows) == 3, "three original retained-owner native receipts required")
            for value in rows: _integer(value, 0, U32, "original native owner DWORD required")
        for name in ("probe_sequence", "breakpoint_sequence", "command_sequence"):
            _integer(getattr(self, name), 0, U63, "original independently supplied owner sequence required")


@dataclass(frozen=True)
class BreakpointCountResult:
    hresult: int
    count: int

    def __post_init__(self):
        _integer(self.hresult, -(1 << 31), U32, "original signed/unsigned GetNumberBreakpoints HRESULT required")
        _integer(self.count, 0, U32, "original native breakpoint ULONG count required")


@dataclass(frozen=True)
class Pointer64Result:
    hresult: int

    def __post_init__(self):
        _integer(self.hresult, -(1 << 31), U32, "original signed/unsigned HRESULT required")


@dataclass(frozen=True)
class ReadResult:
    hresult: int
    returned_bytes: int
    raw: bytes

    def __post_init__(self):
        _integer(self.hresult, -(1 << 31), U32, "original signed/unsigned HRESULT required")
        _integer(self.returned_bytes, 0, U32, "original native count required")
        # Do not discard an impossible oversized native/adapter result to fit
        # the journal. Capacity rejection retains the complete Pending object.
        _require(type(self.raw) is bytes, "complete original bytes required")


@dataclass(frozen=True)
class OriginalReceipt:
    sequence: int
    operation: str
    argument: object
    original: object


@dataclass(frozen=True)
class RawAttempt:
    ordinal: int
    address: int
    requested_bytes: int
    phase_before: object
    begin_counter: object
    original_return: object
    end_counter: object
    phase_after: object


@dataclass(frozen=True)
class OriginalFailure:
    type_name: str
    message: str
    original_result: object


@dataclass(frozen=True)
class SessionResult:
    report_json: str
    receipts: tuple
    raw_attempts: tuple
    oracle_reads: tuple
    pending: object = None
    original_failures: tuple = ()

    def report(self): return json.loads(self.report_json)


@dataclass(frozen=True, eq=False, slots=True, weakref_slot=True)
class PreparedReadPlan:
    """Readable source binding only; identity must have a live source issuer."""
    binding_json: str


def _clone(cls, value):
    _require(is_dataclass(value) and not isinstance(value, type) and type(value).__name__ == cls.__name__
             and {row.name for row in fields(value)} == {row.name for row in fields(cls)}, "original typed " + cls.__name__ + " required")
    return cls(**{row.name: getattr(value, row.name) for row in fields(cls)})


def _summary(value):
    if type(value) is bytes: return dict(original_raw_bytes=len(value), original_raw_sha256=_hash(value))
    if is_dataclass(value) and not isinstance(value, type):
        return {row.name: _summary(getattr(value, row.name)) for row in fields(value)}
    if type(value) in (tuple, list): return [_summary(row) for row in value]
    if type(value) is dict:
        _require(all(type(key) is str for key in value), "metadata key must retain string type")
        return {key: _summary(row) for key, row in value.items()}
    _require(type(value) in (str, int, bool, type(None)), "original receipt has unsupported metadata type")
    return value


class _Stopped(Exception): pass


class _Journal:
    def __init__(self):
        self.rows, self.bytes, self.raw_bytes, self.pending = [], 2, 0, None

    def add(self, operation, argument, original):
        receipt = OriginalReceipt(len(self.rows) + 1, operation, argument, original)
        try:
            cost = len(_canonical(_summary(receipt))) + bool(self.rows)
            raw = _raw_size(original)
            _require(len(self.rows) < MAX_RECEIPTS and self.bytes + cost <= METADATA_BYTES - REPORT_RESERVE_BYTES,
                     "complete receipt metadata capacity exceeded")
            _require(self.raw_bytes + raw <= RAW_SCOPE_BYTES + RAW_TEMPORARY_BYTES,
                     "complete original raw capacity exceeded")
        except Exception:
            self.pending = receipt
            raise _Stopped("complete original receipt retained Pending; capacity/type debt prevents completion")
        self.rows.append(receipt); self.bytes += cost; self.raw_bytes += raw
        return receipt


def _raw_size(value):
    return len(value.raw) if is_dataclass(value) and type(value).__name__ == "ReadResult" and type(getattr(value, "raw", None)) is bytes else 0


def _inventory(bound, authority, oracle, pe):
    plan = oracle._checked_plan(bound)
    scope = oracle._derive_plan(bound.candidate, pe)
    _require(oracle._canonical(scope) == oracle._canonical(plan["immutable_scope"]), "canonical inventory differs")
    _require(authority.image_base + scope["image_size"] <= oracle.USER_LIMIT,
             "bounded original loaded image extent required")
    _require(authority.peb_address + 12 <= authority.image_base or
             authority.peb_address >= authority.image_base + scope["image_size"], "PEB aliases loaded image")
    return ((authority.peb_address + 8, 4),) + tuple((authority.image_base + row["rva"], row["size"]) for row in scope["chunks"])


def _collect(bound, authority, anchor, adapter, *, oracle, pe, check_sources):
    """Private synthetic seam; public caller always supplies canonical admission."""
    journal, raw_attempts, complete_reads, failures, projections, originals = _Journal(), [], [], [], [], []
    previous_tick = None
    active_attempt = None
    try:
        authority = oracle._clone(oracle.LoaderAuthority, authority); anchor = _clone(QpcAnchor, anchor)
        _require((authority.clock_epoch, authority.clock_origin_ns, authority.checkpoint_start_ns)
                 == (anchor.epoch_id, anchor.origin_ns, project(anchor, anchor.held_start_tick).lower_ns),
                 "independently fixed clock/checkpoint mapping differs")
        plan = oracle._checked_plan(bound)
        _require((authority.profile, authority.resolution, authority.stage, authority.recipe_revision,
                  authority.candidate_sha256, authority.probe_sha256, authority.source_closure_sha256)
                 == (plan["profile"], plan["resolution"], plan["stage"], plan["recipe_revision"],
                     plan["candidate_sha256"], plan["canonical_probe_sha256"], plan["source_closure_sha256"]),
                 "independent run/candidate/probe/source recipe binding differs before adapter access")
        inventory = _inventory(bound, authority, oracle, pe)
        check_sources()
        previous_tick = anchor.held_start_tick

        def counter():
            nonlocal previous_tick
            original = adapter.counter()
            journal.add("counter", None, original)
            sample = _clone(QpcSample, original)
            _require((sample.epoch_id, sample.frequency_hz, sample.frequency_native_return, sample.frequency_native_error,
                      sample.counter_native_return, sample.counter_native_error)
                     == (anchor.epoch_id, anchor.frequency_hz, 1, 0, 1, 0), "original QPC/frequency receipt failed or changed")
            _require(previous_tick <= sample.tick and sample.tick - anchor.held_start_tick <= HOLD_SECONDS * anchor.frequency_hz,
                     "original QPC order/unchanged20s checkpoint expired")
            previous_tick = sample.tick
            mapped = project(anchor, sample.tick); projections.append(mapped)
            journal.add("projection", sample.tick, mapped)
            return sample, mapped

        def owner():
            original = adapter.observe_owner(); journal.add("owner", None, original)
            observed = _clone(OwnerObservation, original)
            for field in ("controller", "debugger", "target"):
                _require(asdict(oracle._clone(oracle.Generation, getattr(observed, field))) == asdict(getattr(authority, field)),
                         "retained owner generation/path/hash changed")
            _require((observed.run_id, observed.checkpoint_id, observed.clock_epoch, observed.wait_results, observed.native_errors)
                     == (authority.run_id, authority.checkpoint_id, authority.clock_epoch, (258, 258, 258), (0, 0, 0)),
                     "original owner/lease/liveness receipt failed or differs")
            _require((observed.probe_sequence, observed.breakpoint_sequence, observed.command_sequence) == (0, 0, 0),
                     "original external owner probe/breakpoint/command sequence is not initial-loader zero")
            return observed

        def phase():
            before_owner = owner(); counter()
            queries = []
            for name, expected in zip(oracle.PHASE_QUERY_NAMES,
                                      (6, authority.target.pid, authority.primary_tid, authority.engine_pid, authority.engine_tid)):
                counter()
                original = adapter.query(name); journal.add("query", name, original)
                query = oracle._clone(oracle.NativeQuery, original)
                _require((query.name, query.hresult, query.value) == (name, 0, expected), "original phase query failed or returned stale/foreign value")
                queries.append(query); counter()
            counter()
            original = adapter.get_number_breakpoints(); journal.add("GetNumberBreakpoints", None, original)
            breakpoints = _clone(BreakpointCountResult, original)
            _require((breakpoints.hresult, breakpoints.count) == (0, 0),
                     "original GetNumberBreakpoints failed or nonzero; stale zero cannot hide failed HRESULT")
            counter()
            counter()
            original = adapter.pointer64(); journal.add("pointer64", None, original)
            pointer = _clone(Pointer64Result, original)
            _require(pointer.hresult == 1, "original IsPointer64Bit receipt differs or failed")
            _, mapped = counter(); after_owner = owner()
            _require((after_owner.probe_sequence, after_owner.breakpoint_sequence, after_owner.command_sequence)
                     == (before_owner.probe_sequence, before_owner.breakpoint_sequence, before_owner.command_sequence),
                     "original owner sequence changed across held boundary")
            return oracle.HeldPhase(authority.run_id, authority.clock_epoch, authority.checkpoint_id,
                authority.controller, authority.debugger, authority.target, authority.target.pid, authority.primary_tid,
                authority.engine_pid, authority.engine_tid, authority.image_base, 6, pointer.hresult,
                after_owner.probe_sequence, after_owner.breakpoint_sequence,
                mapped.lower_ns, tuple(queries))

        counter()
        for ordinal, (address, size) in enumerate(inventory):
            check_sources()
            before = phase(); begin, begin_ns = counter()
            active_attempt = RawAttempt(ordinal, address, size, before, begin, None, None, None)
            raw_attempts.append(active_attempt)
            original = adapter.read_virtual(address, size)
            active_attempt = RawAttempt(ordinal, address, size, before, begin, original, None, None)
            raw_attempts[-1] = active_attempt
            journal.add("read_virtual", dict(ordinal=ordinal, address=address, requested_bytes=size), original)
            returned = _clone(ReadResult, original)
            _require(returned.hresult == 0 and returned.returned_bytes == size and len(returned.raw) == size,
                     "original ReadVirtual partial/failure/count mismatch retained; no further calls")
            end, end_ns = counter()
            active_attempt = RawAttempt(ordinal, address, size, before, begin, original, end, None)
            raw_attempts[-1] = active_attempt
            after = phase()
            active_attempt = RawAttempt(ordinal, address, size, before, begin, original, end, after)
            raw_attempts[-1] = active_attempt
            complete_reads.append(oracle.RawRead(ordinal, address, size, returned.returned_bytes, returned.hresult,
                returned.raw, begin_ns.lower_ns, end_ns.lower_ns, before, after))
            active_attempt = None
        check_sources()
        compared = oracle._compare(bound, authority, tuple(complete_reads), pe).report()
        _require(compared["source_comparison_passed"], "complete canonical byte replay rejected: " + str(compared["failures"]))
        check_sources(); counter(); check_sources()
    except Exception as error:
        original_error = str(error)
        originals.append(OriginalFailure(type(error).__name__, original_error, getattr(error, "original_result", None)))
        failures.append(type(error).__name__ + (": " + original_error if len(original_error.encode("utf-8")) <= 4096
                                                else ": full original error retained in receipt/Pending RAM"))
        partial = getattr(error, "original_result", None)
        if partial is not None:
            if active_attempt is not None:
                raw_attempts[-1] = RawAttempt(active_attempt.ordinal, active_attempt.address, active_attempt.requested_bytes,
                    active_attempt.phase_before, active_attempt.begin_counter, partial, None, None)
            if journal.pending is None:
                try: journal.add("adapter_exception_original", None, partial)
                except Exception: pass
        # Exception itself is retained, even when its full string cannot fit
        # the bounded metadata. No truncation or retry/replacement is allowed.
        if journal.pending is None:
            try: journal.add("exception", type(error).__name__, original_error)
            except Exception: pass
    report = dict(schema=SCHEMA, **FALSE_CLAIMS, supplied_receipt_collection_passed=not failures,
                  failures=failures, required_hold_seconds=HOLD_SECONDS,
                  complete_oracle_read_count=len(complete_reads), raw_attempt_count=len(raw_attempts),
                  receipt_count=len(journal.rows), metadata_bytes=journal.bytes, retained_raw_bytes=journal.raw_bytes,
                  pending_ram_present=journal.pending is not None,
                  pending_ram_raw_bytes=(_raw_size(journal.pending.original) if journal.pending is not None else 0),
                  pending_ram_error_bytes=(sum(len(row.message.encode("utf-8")) for row in originals) if journal.pending is not None else 0),
                  budget=budget(), projection_count=len(projections),
                  conversion_policy="exact rational tick arithmetic/order/20s guard; floor/ceil interval only; fractional remainder retained",
                  mandatory_gaps=["native collector and lease issuance", "external owner sequence/native initial-loader event provenance",
                    "QPC calibration/awake/asynchronous-event provenance",
                    "actual loader/header/zero-tail behavior", "readonly/RW/IAT/provider state", "canonical probe execution",
                    "native no-breakaway job cleanup", "atomic external raw/metadata retention and real disk reserve"])
    encoded_report = _canonical(report)
    _require(len(encoded_report) <= REPORT_RESERVE_BYTES, "source-owned report envelope exceeded")
    return SessionResult(encoded_report.decode("ascii"), tuple(journal.rows), tuple(raw_attempts), tuple(complete_reads), journal.pending, tuple(originals))


def _source_bytes(path):
    _require(path.resolve(strict=True) == path and path.is_relative_to(ROOT), "canonical source path required")
    for entry in (path, *path.parents):
        _require(not entry.is_symlink() and not getattr(entry, "is_junction", lambda: False)()
                 and not getattr(entry.stat(), "st_file_attributes", 0) & 0x400, "reparsed source path")
    before = path.stat(); raw = path.read_bytes(); after = path.stat()
    stamp = lambda row: (row.st_dev, row.st_ino, row.st_size, row.st_mtime_ns)
    _require(stamp(before) == stamp(after), "source identity changed during read")
    return raw, stamp(after)


def _prepare_execution(original, contract):
    """All expensive reconstruction occurs here, before a native held epoch."""
    own_path, oracle_path = ROOT / SOURCE, ROOT / ORACLE
    _require(Path(__file__).resolve() == own_path, "noncanonical collector module")
    snapshot = (_source_bytes(own_path), _source_bytes(oracle_path))
    _require(_hash(snapshot[1][0]) == ORACLE_SHA256, "fixed canonical oracle source differs")
    prefix = "_clash95_loader_read_" + uuid.uuid4().hex
    modules = {}
    try:
        package = types.ModuleType(prefix); package.__path__ = []; sys.modules[prefix] = package
        for name, (raw, _) in (("hidden_soak_loaded_image", snapshot[1]), ("hidden_soak_loaded_read_session", snapshot[0])):
            module = types.ModuleType(prefix + "." + name)
            module.__file__, module.__package__ = str(ROOT / "tools" / (name + ".py")), prefix
            sys.modules[module.__name__] = module
            exec(compile(raw, module.__file__, "exec"), module.__dict__); modules[name] = module
        oracle = modules["hidden_soak_loaded_image"]
        source_snapshot = oracle._snapshot()
        with oracle._modules(source_snapshot) as canonical:
            producer, context = canonical[oracle.SOURCE], canonical[oracle.CONTEXT]
            copied = producer._clone(producer.LoadedImageContract, contract)
            plan = producer._checked_plan(copied)
            metadata = context._restore_metadata(producer._json(copied.typed_metadata_json))
            rebuilt, sources, stamps = producer._prepare_authenticated(original, plan["profile"], plan["resolution"],
                copied.candidate, metadata, copied.canonical_probe, modules=canonical, snapshot=source_snapshot)
            _require(rebuilt.plan_json == copied.plan_json, "supplied contract differs from fresh fixed admission")
            def check_sources():
                context._unchanged(sources, stamps); oracle._unchanged(source_snapshot)
                _require((_source_bytes(own_path), _source_bytes(oracle_path)) == snapshot, "collector/oracle source changed")
            check_sources()
            # Immutable source-issued binding grants no native authority. The
            # object registry, never this text/hash, supplies issuer identity.
            binding = _canonical(dict(schema=SCHEMA, oracle_source_sha256=ORACLE_SHA256,
                collector_source_sha256=_hash(snapshot[0][0]), contract_sha256=_hash(rebuilt.plan_json.encode("ascii")),
                source_closure_sha256=plan["source_closure_sha256"], candidate_sha256=plan["candidate_sha256"],
                relative_requests=[dict(rva=row["rva"], size=row["size"]) for row in plan["immutable_scope"]["chunks"]],
                extra_request="PEB.ImageBaseAddress4bytes; native PEB binding remains external", claims=FALSE_CLAIMS)).decode("ascii")
            canonical_collector = modules["hidden_soak_loaded_read_session"]
            def execute(authority, anchor, adapter):
                return canonical_collector._collect(rebuilt, authority, anchor, adapter,
                    oracle=producer, pe=canonical[oracle.PE], check_sources=check_sources)
            return binding, execute
    finally:
        for name in list(sys.modules):
            if name == prefix or name.startswith(prefix + "."): del sys.modules[name]


def _api_factory():
    # Weak identity keys prevent both caller-created copies and an unbounded
    # retained cache of original/candidate/source RAM across prepared plans.
    issued = {}
    capability_class, prepare_execution = PreparedReadPlan, _prepare_execution
    def failed(error):
        return SessionResult(_canonical(dict(schema=SCHEMA, **FALSE_CLAIMS, supplied_receipt_collection_passed=False,
            failures=[type(error).__name__ + ": " + str(error)], budget=budget(),
            mandatory_gaps=["source-issued canonical preparation required before adapter operation"])).decode("ascii"), (), (), ())
    def prepare_read_plan(original, contract):
        """Source-only expensive admission before launch; returns opaque identity."""
        binding, execute = prepare_execution(original, contract)
        capability = capability_class(binding)
        identity = id(capability)
        def retire(reference):
            if identity in issued and issued[identity][0] is reference: del issued[identity]
        issued[identity] = (weakref.ref(capability, retire), binding, execute)
        return capability
    def collect_prepared_reads(prepared, authority, anchor, adapter):
        """Only a live source-issued identity can supply cached byte authority."""
        try:
            entry = issued.get(id(prepared))
            _require(type(prepared) is capability_class and entry is not None and entry[0]() is prepared,
                     "source-issued prepared object identity required")
            _, binding, execute = entry
            _require(prepared.binding_json == binding, "issued readable source binding was altered")
            return execute(authority, anchor, adapter)
        except Exception as error: return failed(error)
    def collect_loader_reads(original, contract, authority, anchor, adapter):
        """Convenience path; existing hold charges all reconstruction time."""
        try: return collect_prepared_reads(prepare_read_plan(original, contract), authority, anchor, adapter)
        except Exception as error: return failed(error)
    return prepare_read_plan, collect_prepared_reads, collect_loader_reads


prepare_read_plan, collect_prepared_reads, collect_loader_reads = _api_factory()
