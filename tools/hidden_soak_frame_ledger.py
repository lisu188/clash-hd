"""Source preparation for complete hidden map-idle frame retention.

No native, filesystem, capture, launch or approval adapter is supplied. The
caller owns the independently authenticated run and issues each read lease;
fixed host adapters must eventually supply actual observations. This component
records packed indexed8 bytes, including failed/short reads. It cannot prove
native pitch, coherent rendering, loaded modules, process health or job cleanup.
All broad acceptance claims remain false. Legacy producers are not admitted.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path, PureWindowsPath
import re
import struct

import hidden_soak_process_lease as process

SOURCE = Path(__file__).resolve()
SCHEMA = "hidden_soak_frame_ledger_v1"
MAGIC = b"CLASH-HIDDEN-FRAME\x01"
SECOND = 1_000_000_000
DURATION_NS, PERIOD_NS, MAX_LATENESS_NS = 7200 * SECOND, 30 * SECOND, 2 * SECOND
PERIODIC_COUNT, FRAME_COUNT = 241, 242
PRESETS = ((800, 600), (1024, 768), (1280, 720), (1280, 960), (1366, 768),
           (1920, 1080), (2560, 1440), (3440, 1440), (3840, 2160))
PROFILES = ("classic", "framed", "completehd", "modalwidgets")
HEADER_BYTES, MAX_RAW_BYTES = 188, 3840 * 2160
MAX_CONTAINER_JSON, MAX_LEDGER_JSON = 64 * 1024, 2 * 1024 * 1024
SCRATCH_BYTES, METADATA_BYTES = 128 * 1024 * 1024, 32 * 1024 * 1024
FALSE_CLAIMS = {key: False for key in (
    "passed", "producer_capability_verified", "no_breakaway_job_verified",
    "loaded_candidate_verified", "loaded_probe_verified", "runtime_acceptance",
    "release_acceptance", "manual_input_verified", "promotion_ready",
    "geometry_verified", "stable_resolution")}


def _require(value, message):
    if not value:
        raise ValueError(message)


def _int(value, maximum, label, minimum=0):
    _require(type(value) is int and minimum <= value <= maximum, label)


def _sha(data):
    _require(type(data) is bytes, "original bytes required")
    return hashlib.sha256(data).hexdigest()


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                      allow_nan=False).encode("ascii")


def _object(pairs):
    result = {}
    for key, value in pairs:
        _require(key not in result, "duplicate JSON field")
        result[key] = value
    return result


def _decode_json(data):
    _require(type(data) is bytes, "canonical JSON bytes required")
    value = json.loads(data, object_pairs_hook=_object,
                       parse_constant=lambda value: (_ for _ in ()).throw(ValueError("nonfinite JSON")))
    _require(_canonical(value) == data, "noncanonical JSON")
    return value


def _path(path):
    return process._path(path)


def _text(value, label):
    _require(type(value) is str and 0 < len(value) <= 4096
             and not any(c in value for c in "\0\r\n"), label)


def _generation(value):
    _require(type(value) is process.Generation, "typed generation required")


@dataclass(frozen=True)
class SurfaceAuthority:
    width: int
    height: int
    header_address: int
    pixels_address: int
    header: bytes

    def __post_init__(self):
        _int(self.width, 3840, "invalid width", 1)
        _int(self.height, 2160, "invalid height", 1)
        _require((self.width, self.height) in PRESETS, "custom dimensions remain experimental; ledger admits fixed presets only")
        _int(self.header_address, 0x7fff0000 - HEADER_BYTES, "invalid bounded x86 user surface header address", 0x10000)
        _int(self.pixels_address, 0x7fff0000 - self.width * self.height, "invalid bounded x86 packed pixel address", 0x10000)
        _require(type(self.header) is bytes and len(self.header) == HEADER_BYTES, "complete surface header required")
        _require(struct.unpack_from("<HHI", self.header) == (self.width, self.height, self.pixels_address),
                 "surface header differs from packed authority")
        _require(self.header_address + HEADER_BYTES <= self.pixels_address
                 or self.pixels_address + self.width * self.height <= self.header_address, "header/pixels overlap")


@dataclass(frozen=True)
class FrameAuthority:
    run: process.RunAuthority
    target: process.Generation
    debugger: process.Generation
    surface: SurfaceAuthority
    start_ns: int
    checkout_root: str
    output_root: str
    output_identity: str
    runtime_asset_bytes: int
    available_peak_bytes: int

    def __post_init__(self):
        _require(type(self.run) is process.RunAuthority and type(self.surface) is SurfaceAuthority,
                 "independently supplied typed run/surface required")
        _generation(self.target); _generation(self.debugger)
        _int(self.start_ns, (1 << 63) - DURATION_NS - MAX_LATENESS_NS, "invalid monotonic origin", 1)
        _int(self.runtime_asset_bytes, 1 << 50, "invalid external runtime asset budget")
        _int(self.available_peak_bytes, 1 << 50, "invalid external peak allowance", 1)
        _require(self.run.profile in PROFILES and self.run.resolution == f"{self.surface.width}x{self.surface.height}",
                 "run profile/resolution differs")
        for role, generation in (("candidate", self.target), ("debugger", self.debugger)):
            image = next(row for row in self.run.images if row.role == role)
            _require((image.path, image.sha256) == (generation.image_path, generation.image_sha256), "run image/generation differs")
        _require(len({self.target.pid, self.debugger.pid, self.run.controller.pid}) == 3, "aliased process generations")
        _require(self.run.controller.creation_filetime <= self.debugger.creation_filetime <= self.target.creation_filetime,
                 "child predates its independently bound parent generation")
        object.__setattr__(self, "checkout_root", _path(self.checkout_root))
        object.__setattr__(self, "output_root", _path(self.output_root))
        checkout, output = PureWindowsPath(self.checkout_root), PureWindowsPath(self.output_root)
        _require(len(output.parts) > 1 and checkout != output and checkout not in output.parents
                 and output not in checkout.parents, "retention must be outside checkout and its ancestors")
        _text(self.output_identity, "external directory identity required")
        _require(_path(str(SOURCE)) in {row.path for row in self.run.source_pins}, "fixed ledger source pin required")
        _require(self.available_peak_bytes >= budget(self.surface, self.runtime_asset_bytes)["total_peak_bytes"],
                 "insufficient externally approved peak allowance")


@dataclass(frozen=True)
class ReadLease:
    run_id: str
    ordinal: int
    token: str
    issued_ns: int
    target: process.Generation
    debugger: process.Generation
    surface: SurfaceAuthority

    def __post_init__(self):
        _require(type(self.run_id) is str and re.fullmatch(r"[0-9a-f]{32}", self.run_id), "invalid run ID")
        _int(self.ordinal, FRAME_COUNT - 1, "invalid scheduled ordinal")
        _require(type(self.token) is str and re.fullmatch(r"[0-9a-f]{32}", self.token), "independent read lease token required")
        _int(self.issued_ns, (1 << 63) - 1, "invalid lease issue time", 1)
        _generation(self.target); _generation(self.debugger)
        _require(type(self.surface) is SurfaceAuthority, "typed surface lease required")


@dataclass(frozen=True)
class ReadResult:
    target_before: process.Observation
    target_after: process.Observation
    debugger_before: process.Generation
    debugger_after: process.Generation
    header_before: bytes
    header_after: bytes
    pitch_before: int
    pitch_after: int
    requested_bytes: int
    returned_bytes: int
    native_return: int
    native_error: int
    raw: bytes

    def __post_init__(self):
        _require(type(self.target_before) is process.Observation and type(self.target_after) is process.Observation,
                 "actual typed process observations required")
        _generation(self.debugger_before); _generation(self.debugger_after)
        for header in (self.header_before, self.header_after):
            _require(type(header) is bytes and len(header) <= HEADER_BYTES, "bounded original header bytes required")
        for value in (self.pitch_before, self.pitch_after, self.requested_bytes, self.returned_bytes):
            _int(value, MAX_RAW_BYTES, "invalid native read dimensions/count")
        _int(self.native_return, 1, "invalid native BOOL")
        _int(self.native_error, 0xffffffff, "invalid native error")
        _require(type(self.raw) is bytes and len(self.raw) <= MAX_RAW_BYTES, "bounded original raw bytes required")
        _require(self.returned_bytes == len(self.raw) and self.returned_bytes <= self.requested_bytes,
                 "native byte receipt differs from original bytes")


class ReadFailure(Exception):
    """Readers must preserve actual partial bytes when raising a read error."""
    def __init__(self, result, message):
        _require(type(result) is ReadResult, "typed partial read result required")
        _text(message, "bounded read failure diagnostic required")
        self.result = result
        super().__init__(message)


@dataclass(frozen=True)
class DirectoryObservation:
    resolved_path: str
    identity: str
    ancestor_reparse: tuple[bool, ...]

    def __post_init__(self):
        object.__setattr__(self, "resolved_path", _path(self.resolved_path))
        _text(self.identity, "directory identity required")
        _require(type(self.ancestor_reparse) is tuple and all(type(row) is bool for row in self.ancestor_reparse)
                 and len(self.ancestor_reparse) == len(PureWindowsPath(self.resolved_path).parts),
                 "complete root/ancestor reparse observations required")


@dataclass(frozen=True)
class DiskSpace:
    total_bytes: int
    free_bytes: int

    def __post_init__(self):
        _int(self.total_bytes, 1 << 63, "invalid volume size", 1)
        _int(self.free_bytes, self.total_bytes, "invalid free space")


@dataclass(frozen=True)
class FileObservation:
    identity: str
    size: int
    regular: bool
    reparse: bool
    links: int

    def __post_init__(self):
        _text(self.identity, "file identity required")
        _int(self.size, MAX_RAW_BYTES + MAX_CONTAINER_JSON + MAX_LEDGER_JSON, "invalid retained file size")
        _require(type(self.regular) is bool and type(self.reparse) is bool, "typed file attributes required")
        _int(self.links, 0xffffffff, "invalid link count", 1)


@dataclass(frozen=True)
class ArtifactBinding:
    name: str
    sha256: str
    size: int
    identity: str

    def __post_init__(self):
        _require(type(self.name) is str and re.fullmatch(r"(?:frame-[0-9]{4}\.frame(?:\.partial)?|ledger\.json(?:\.partial)?)", self.name),
                 "fixed artifact filename required")
        process._digest(self.sha256)
        _int(self.size, MAX_RAW_BYTES + MAX_CONTAINER_JSON + MAX_LEDGER_JSON, "invalid bound artifact size")
        _text(self.identity, "external artifact identity required")


@dataclass(frozen=True)
class CollectorBinding:
    """Retain separately through the caller, never recover from the report.

    This binds the original collector output. It is not a native provenance,
    signature, job, loaded-module or approval authority.
    """
    authority_sha256: str
    ledger: ArtifactBinding
    artifacts: tuple[ArtifactBinding, ...]

    def __post_init__(self):
        process._digest(self.authority_sha256)
        _require(type(self.ledger) is ArtifactBinding and self.ledger.name == "ledger.json", "typed ledger binding required")
        _require(type(self.artifacts) is tuple and len(self.artifacts) <= FRAME_COUNT
                 and all(type(row) is ArtifactBinding and row.name != "ledger.json" for row in self.artifacts)
                 and len({row.name for row in self.artifacts}) == len(self.artifacts), "unique external raw bindings required")


@dataclass(frozen=True)
class PendingCapture:
    """Original bytes still owned in memory after a persistence failure.

    The outer host must retain this debt through an independently safe writer.
    Partial files are preserved; this object never claims durable retention.
    """
    ordinal: int
    canonical_metadata: bytes
    raw: bytes


def budget(surface, runtime_asset_bytes):
    _require(type(surface) is SurfaceAuthority, "typed geometry required")
    _int(runtime_asset_bytes, 1 << 50, "invalid external runtime asset budget")
    frame = surface.width * surface.height
    temporary = max(frame, MAX_RAW_BYTES) + len(MAGIC) + 4 + MAX_CONTAINER_JSON
    return {"raw_frame_bytes": frame, "frame_count": FRAME_COUNT,
            "all_raw_bytes": FRAME_COUNT * frame, "atomic_temporary_bytes": temporary,
            "scratch_bytes": SCRATCH_BYTES, "metadata_bytes": METADATA_BYTES,
            "runtime_asset_bytes": runtime_asset_bytes,
            "total_peak_bytes": runtime_asset_bytes + FRAME_COUNT * frame + temporary + SCRATCH_BYTES + METADATA_BYTES}


def schedule():
    return {"route": "map_idle", "duration_ns": DURATION_NS, "period_ns": PERIOD_NS,
            "periodic_count": PERIODIC_COUNT, "frame_count": FRAME_COUNT,
            "max_lateness_ns": MAX_LATENESS_NS, "terminal_capture": "separate_after_final_periodic",
            "format": "packed_indexed8", "custom_dimensions": "experimental_not_admitted"}


def _wire_authority(authority):
    value = asdict(authority)
    value["surface"]["header"] = authority.surface.header.hex()
    return value


def _wire_lease(lease):
    value = asdict(lease)
    value["surface"]["header"] = lease.surface.header.hex()
    return value


def _wire_result(result):
    value = asdict(result)
    value.pop("raw")
    value["header_before"], value["header_after"] = result.header_before.hex(), result.header_after.hex()
    return value


def _source_check(authority, adapter):
    for pin in authority.run.source_pins:
        _require(adapter.source_sha256(pin.path) == pin.sha256, "fixed source snapshot changed")


def _root_check(authority, adapter):
    observed = adapter.inspect_root(authority.output_root)
    _require(type(observed) is DirectoryObservation
             and observed.resolved_path == authority.output_root
             and observed.identity == authority.output_identity
             and not any(observed.ancestor_reparse), "output escaped, changed or crossed a reparse point")


def _file_check(observed):
    _require(type(observed) is FileObservation and observed.regular and not observed.reparse and observed.links == 1,
             "retained artifact is nonregular, aliased or reparsed")


def _scope_errors(authority, lease, result, begin, end, previous_end):
    errors = []
    expected = authority.surface.width * authority.surface.height
    due = authority.start_ns + min(lease.ordinal, PERIODIC_COUNT - 1) * PERIOD_NS
    if not (due <= begin <= end <= due + MAX_LATENESS_NS):
        errors.append("absolute scheduled read window missed")
    if previous_end is not None and begin <= previous_end:
        errors.append("read order/terminal separation lost")
    if not due <= lease.issued_ns <= begin:
        errors.append("read lease was not freshly issued for the scheduled slot")
    if (lease.run_id, lease.target, lease.debugger, lease.surface) != (
            authority.run.run_id, authority.target, authority.debugger, authority.surface):
        errors.append("read lease differs from independent run authority")
    for observed in (result.target_before, result.target_after):
        if observed.generation != authority.target or observed.parent_pid != authority.debugger.pid or observed.wait_result != 258:
            errors.append("retained target generation/parent/liveness differs")
    if result.debugger_before != authority.debugger or result.debugger_after != authority.debugger:
        errors.append("retained parent generation differs")
    if result.header_before != authority.surface.header or result.header_after != authority.surface.header:
        errors.append("complete surface header changed or partial")
    if result.pitch_before != authority.surface.width or result.pitch_after != authority.surface.width:
        errors.append("native pitch differs from supported packed indexed8 scope")
    if (result.requested_bytes, result.returned_bytes, result.native_return, result.native_error) != (expected, expected, 1, 0):
        errors.append("native frame read failed, shortened or incompatible")
    return errors


def _container(metadata, raw):
    header = _canonical(metadata)
    _require(len(header) <= MAX_CONTAINER_JSON and len(raw) <= MAX_RAW_BYTES, "frame container limit exceeded")
    return (MAGIC + struct.pack("<I", len(header)) + header, raw)


def _decode_container(data):
    _require(type(data) is bytes and data.startswith(MAGIC) and len(data) >= len(MAGIC) + 4, "invalid frame container")
    count = struct.unpack_from("<I", data, len(MAGIC))[0]
    _require(count <= MAX_CONTAINER_JSON and len(data) >= len(MAGIC) + 4 + count, "partial/oversize frame container header")
    start = len(MAGIC) + 4
    return _decode_json(data[start:start + count]), data[start + count:]


class FrameLedger:
    """Adapter-only collector; no count/duration/retry/reserve overrides.

    Adapter methods are inspect_root, source_sha256, disk_space, monotonic_ns,
    create_exclusive, write, flush, close, publish_exclusive, stat, read. All
    paths handed to file methods are fixed basenames in the attested output
    root; adapters must use that retained root, exclusive handles and atomic
    no-replacement rename. Failed partial files are never deleted or retried.
    A reader's read(lease, requested_bytes) returns original typed ReadResult,
    including failed reads, or raises ReadFailure with that original receipt.
    Untyped exceptions cannot recover unknown partial bytes and fail scope.
    """
    def __init__(self, authority, adapter):
        _require(type(authority) is FrameAuthority, "typed external frame authority required")
        self.authority, self.adapter = authority, adapter
        self.rows, self.artifacts, self.tokens, self.retained_bytes = [], [], set(), 0
        self.pending_captures = []
        self.finished = False
        self._prewrite()

    def _prewrite(self, additional_bytes=0):
        _source_check(self.authority, self.adapter); _root_check(self.authority, self.adapter)
        _int(additional_bytes, MAX_RAW_BYTES + MAX_CONTAINER_JSON + MAX_LEDGER_JSON, "invalid next retention payload")
        plan = budget(self.authority.surface, self.authority.runtime_asset_bytes)
        retention_allowance = plan["all_raw_bytes"] + plan["atomic_temporary_bytes"] + plan["metadata_bytes"]
        _require(self.retained_bytes + additional_bytes <= retention_allowance,
                 "remaining approved retention allowance cannot cover complete next payload")
        remaining = plan["total_peak_bytes"] - self.retained_bytes
        for root in (self.authority.checkout_root, self.authority.output_root):
            space = self.adapter.disk_space(root)
            _require(type(space) is DiskSpace and space.free_bytes * 10 > space.total_bytes
                     and (space.free_bytes - remaining) * 10 > space.total_bytes,
                     "strict ten-percent reserve plus remaining peak allowance unavailable")

    def _bound_read(self, name):
        _root_check(self.authority, self.adapter)
        before = self.adapter.stat(name); _file_check(before)
        data = self.adapter.read(name)
        after = self.adapter.stat(name); _file_check(after)
        _require(before == after and type(data) is bytes and len(data) == before.size, "retained file changed during readback")
        return ArtifactBinding(name, _sha(data), len(data), before.identity)

    def _atomic(self, name, segments):
        _require(type(name) is str and re.fullmatch(r"(?:frame-[0-9]{4}\.frame|ledger\.json)", name),
                 "atomic target must be a fixed retention basename")
        _require(type(segments) is tuple and 1 <= len(segments) <= 2 and all(type(data) is bytes for data in segments),
                 "bounded original write segments required")
        expected = hashlib.sha256()
        for data in segments:
            expected.update(data)
        expected_size = sum(map(len, segments))
        _require(expected_size <= MAX_RAW_BYTES + MAX_CONTAINER_JSON + len(MAGIC) + 4,
                 "atomic retention payload exceeds fixed bound")
        temporary = name + ".partial" if name != "ledger.json" else "ledger.json.partial"
        self._prewrite(expected_size)
        handle, error, count, published = None, None, 0, False
        try:
            handle = self.adapter.create_exclusive(temporary)
            _require(handle is not None, "exclusive writer did not return an owned handle")
            for data in segments:
                self._prewrite(len(data))
                returned = self.adapter.write(handle, data)
                _int(returned, len(data), "invalid atomic write count")
                count += returned; self.retained_bytes += returned
                _require(returned == len(data), "short atomic write; partial retained")
            self._prewrite()
            _require(self.adapter.flush(handle) is None, "adapter flush must return checked success or raise")
        except Exception as exc:
            error = type(exc).__name__ + ": " + str(exc)
        finally:
            if handle is not None:
                try:
                    _require(self.adapter.close(handle) is None, "adapter close must return checked success or raise")
                except Exception as exc:
                    error = (error + "; " if error else "") + "close failed: " + str(exc)
        if error is None:
            try:
                self._prewrite()
                _require(self.adapter.publish_exclusive(temporary, name) is None,
                         "adapter publish must return checked success or raise")
                published = True
                bound = self._bound_read(name)
                _require(bound.size == expected_size and bound.sha256 == expected.hexdigest(),
                         "atomic readback differs from complete original write bytes")
                return bound, None
            except Exception as exc:
                error = type(exc).__name__ + ": " + str(exc)
        partial = None
        failed_path = name if published else temporary
        error += "; retained path requires diagnostic review: " + failed_path
        if handle is not None:
            try:
                partial = self._bound_read(failed_path)
            except Exception as exc:
                error += "; partial binding failed: " + str(exc)
        return partial, error[:4096]

    def capture(self, lease, reader):
        _require(not self.finished and type(lease) is ReadLease and lease.ordinal == len(self.rows),
                 "only the next scheduled attempt may be recorded once")
        _require(lease.token not in self.tokens, "read lease replayed")
        self.tokens.add(lease.token)
        begin, end, result, errors, artifact, retention_error = None, None, None, [], None, None
        try:
            self._prewrite()
            begin = self.adapter.monotonic_ns(); _int(begin, (1 << 63) - 1, "invalid capture clock", 1)
            _require((lease.run_id, lease.target, lease.debugger, lease.surface) == (
                self.authority.run.run_id, self.authority.target, self.authority.debugger, self.authority.surface),
                "read lease differs from independent run authority before reading")
            due = self.authority.start_ns + min(lease.ordinal, PERIODIC_COUNT - 1) * PERIOD_NS
            _require(due <= lease.issued_ns <= begin <= due + MAX_LATENESS_NS
                     and (not self.rows or self.rows[-1]["end_ns"] is None or begin > self.rows[-1]["end_ns"]),
                     "scheduled lease/order/window denied before reading")
            try:
                result = reader.read(lease, self.authority.surface.width * self.authority.surface.height)
            except ReadFailure as exc:
                result = exc.result
                errors.append("ReadFailure: " + str(exc))
            _require(type(result) is ReadResult, "typed original read result required")
            end = self.adapter.monotonic_ns(); _int(end, (1 << 63) - 1, "invalid capture clock", 1)
            _source_check(self.authority, self.adapter)
            errors.extend(_scope_errors(self.authority, lease, result, begin, end,
                                        self.rows[-1]["end_ns"] if self.rows else None))
        except Exception as exc:
            errors.append((type(exc).__name__ + ": " + str(exc))[:4096])
        metadata = {"ordinal": lease.ordinal, "lease": _wire_lease(lease), "begin_ns": begin, "end_ns": end,
                    "read": _wire_result(result) if type(result) is ReadResult else None,
                    "errors": errors, "raw_sha256": _sha(result.raw if type(result) is ReadResult else b"")}
        try:
            artifact, retention_error = self._atomic(f"frame-{lease.ordinal:04d}.frame",
                                           _container(metadata, result.raw if type(result) is ReadResult else b""))
            if retention_error:
                errors.append(retention_error)
        except Exception as exc:
            retention_error = (type(exc).__name__ + ": " + str(exc))[:4096]
            errors.append(retention_error)
        if artifact is not None:
            self.artifacts.append(artifact)
        if artifact is None or retention_error is not None:
            self.pending_captures.append(PendingCapture(lease.ordinal, _canonical(metadata),
                                                       result.raw if type(result) is ReadResult else b""))
        self.rows.append({**metadata, "errors": list(errors), "artifact": asdict(artifact) if artifact else None})
        return not errors

    def finish(self):
        _require(not self.finished, "ledger already finished")
        self.finished = True
        finish_ns = self.adapter.monotonic_ns(); _int(finish_ns, (1 << 63) - 1, "invalid finish clock", 1)
        report = {"schema": SCHEMA, "authority": _wire_authority(self.authority), "schedule": schedule(),
                  "budget": budget(self.authority.surface, self.authority.runtime_asset_bytes),
                  "attempts": self.rows, "finish_ns": finish_ns, "claims": dict(FALSE_CLAIMS)}
        data = _canonical(report)
        _require(len(data) <= MAX_LEDGER_JSON, "ledger diagnostic limit exceeded")
        artifact, error = self._atomic("ledger.json", (data,))
        if error is not None:
            return report, None, error
        binding = CollectorBinding(_sha(_canonical(_wire_authority(self.authority))), artifact, tuple(self.artifacts))
        return report, binding, None


def replay(authority, binding, adapter):
    """Recompute scope from original containers and separately retained binding.

    The caller must supply its original typed authority and collector binding,
    never deserialize either from an alleged passing report. Missing/failed
    attempts remain failures; no broad runtime claim can become true.
    """
    errors = []
    try:
        _require(type(authority) is FrameAuthority and type(binding) is CollectorBinding, "independent typed authority/binding required")
        _source_check(authority, adapter); _root_check(authority, adapter)
        _require(binding.authority_sha256 == _sha(_canonical(_wire_authority(authority))), "external authority binding differs")
        def original(bound):
            before = adapter.stat(bound.name); _file_check(before)
            _require((before.identity, before.size) == (bound.identity, bound.size), "external artifact identity differs")
            data = adapter.read(bound.name)
            _require(adapter.stat(bound.name) == before and _sha(data) == bound.sha256 and len(data) == bound.size,
                     "original retained bytes changed")
            return data
        report = _decode_json(original(binding.ledger))
        _require(type(report) is dict and set(report) == {"schema", "authority", "schedule", "budget", "attempts", "finish_ns", "claims"},
                 "unknown/missing ledger fields")
        _require(report["schema"] == SCHEMA and _canonical(report["authority"]) == _canonical(_wire_authority(authority)), "report run authority differs")
        _require(_canonical(report["schedule"]) == _canonical(schedule()) and _canonical(report["budget"]) == _canonical(budget(authority.surface, authority.runtime_asset_bytes)),
                 "fixed schedule/peak allowance differs")
        _require(_canonical(report["claims"]) == _canonical(FALSE_CLAIMS), "invented acceptance claims")
        _require(type(report["attempts"]) is list and len(report["attempts"]) == FRAME_COUNT, "every scheduled attempt is required")
        _int(report["finish_ns"], (1 << 63) - 1, "invalid final clock", 1)
        by_name = {row.name: row for row in binding.artifacts}
        _require(len(by_name) == FRAME_COUNT, "all original raw containers required")
        tokens, previous_end = set(), None
        for ordinal, row in enumerate(report["attempts"]):
            _require(type(row) is dict and set(row) == {"ordinal", "lease", "begin_ns", "end_ns", "read", "errors", "raw_sha256", "artifact"}, "invalid attempt fields")
            _require(type(row["ordinal"]) is int and row["ordinal"] == ordinal, "scheduled read omitted, duplicated or reordered")
            _require(type(row["artifact"]) is dict, "failed attempt has no retained raw diagnostic")
            bound = by_name.pop(f"frame-{ordinal:04d}.frame", None)
            _require(bound is not None and _canonical(row["artifact"]) == _canonical(asdict(bound)), "raw container reference differs")
            metadata, raw = _decode_container(original(bound))
            _require(_canonical(metadata) == _canonical({key: value for key, value in row.items() if key != "artifact"}), "raw receipt/ledger differs")
            _require(type(row["errors"]) is list and not row["errors"], "failed read/retention remains a failure")
            lease_wire = row["lease"]
            _require(type(lease_wire) is dict and set(lease_wire) == {"run_id", "ordinal", "token", "issued_ns", "target", "debugger", "surface"}, "invalid read lease fields")
            lease = ReadLease(lease_wire["run_id"], lease_wire["ordinal"], lease_wire["token"], lease_wire["issued_ns"],
                              authority.target, authority.debugger, authority.surface)
            _require(_canonical(_wire_lease(lease)) == _canonical(lease_wire) and lease.ordinal == ordinal, "lease process/surface authority differs")
            _require(lease.token not in tokens, "duplicate independently issued read lease")
            tokens.add(lease.token)
            read = row["read"]
            _require(type(read) is dict and set(read) == set(ReadResult.__dataclass_fields__) - {"raw"}, "complete typed raw read receipt required")
            def observation(value):
                _require(type(value) is dict and set(value) == set(process.Observation.__dataclass_fields__), "invalid process observation")
                generation = value["generation"]
                _require(type(generation) is dict and set(generation) == set(process.Generation.__dataclass_fields__), "invalid process generation")
                return process.Observation(process.Generation(**generation), value["parent_pid"], value["wait_result"], value["exit_code"], value["exit_filetime"])
            result = ReadResult(observation(read["target_before"]), observation(read["target_after"]),
                                process.Generation(**read["debugger_before"]), process.Generation(**read["debugger_after"]),
                                bytes.fromhex(read["header_before"]), bytes.fromhex(read["header_after"]),
                                read["pitch_before"], read["pitch_after"], read["requested_bytes"], read["returned_bytes"],
                                read["native_return"], read["native_error"], raw)
            _require(_canonical(_wire_result(result)) == _canonical(read), "noncanonical/coerced native receipt")
            _int(row["begin_ns"], (1 << 63) - 1, "invalid begin clock", 1)
            _int(row["end_ns"], (1 << 63) - 1, "invalid end clock", 1)
            _require(not _scope_errors(authority, lease, result, row["begin_ns"], row["end_ns"], previous_end), "raw scope/lease/schedule verification failed")
            _require(_sha(raw) == row["raw_sha256"], "full raw byte digest differs")
            previous_end = row["end_ns"]
        _require(not by_name and previous_end <= report["finish_ns"]
                 and report["finish_ns"] >= authority.start_ns + DURATION_NS, "final ordered two-hour envelope missing")
        _source_check(authority, adapter); _root_check(authority, adapter)
    except Exception as exc:
        errors.append((type(exc).__name__ + ": " + str(exc))[:4096])
    return {**FALSE_CLAIMS, "raw_ledger_replay_passed": not errors, "failures": errors}
