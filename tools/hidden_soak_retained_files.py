"""Read-only retained-file checks and hidden indexed8 frame consistency.

These checks detect observed path/file drift and compare retained bytes. They
do not make files immutable or authenticate their producer, live process,
loaded image, coherent capture, running time, input, or promotion readiness.
There is no report-controlled alternate reader, fixture root, or skip policy.
"""

from __future__ import annotations

import hashlib
import math
import os
import re
import stat
from pathlib import Path
from typing import Any

from hidden_soak_artifact_layout import HIDDEN_OUTPUT_ROOT, _windows_path


_REPARSE_POINT = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
_FRAME_BYTES = 800 * 600
_FRAME_NAME = re.compile(r"frame-([0-9]{4,10})\Z")
_SHA256 = re.compile(r"[0-9a-fA-F]{64}\Z")


class RetainedFileError(ValueError):
    """A rejected read, retaining every original operation/close exception."""

    def __init__(self, message: str, errors: tuple[Exception, ...] = ()) -> None:
        self.errors = errors
        details = "; ".join(f"{type(error).__name__}: {error}" for error in errors)
        super().__init__(f"{message}: {details}" if details else message)


def _stamp(info: os.stat_result) -> tuple[int, ...]:
    # atime is deliberately excluded: the read itself may update it. Full
    # identity and observed metadata are compared; this is not an atomic lock.
    return (
        info.st_dev, info.st_ino, info.st_mode, info.st_size,
        info.st_mtime_ns, info.st_ctime_ns, getattr(info, "st_file_attributes", 0),
    )


def _path_snapshot(path: Path) -> tuple[tuple[int, ...], ...]:
    """Inspect the root before descendants, without resolve/following links."""
    chain = [*reversed(path.parents), path]
    snapshots = []
    for index, component in enumerate(chain):
        info = os.lstat(component)
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & _REPARSE_POINT:
            raise ValueError(f"symbolic/reparse retained-file path is forbidden: {component}")
        expected_kind = stat.S_ISREG if index == len(chain) - 1 else stat.S_ISDIR
        if not expected_kind(info.st_mode):
            raise ValueError(f"retained-file path has a nonregular file or nondirectory ancestor: {component}")
        if info.st_ino <= 0 or info.st_size < 0:
            raise ValueError(f"retained-file path has unavailable identity or invalid size: {component}")
        snapshots.append(_stamp(info))
    return tuple(snapshots)


def read_retained_file(path: str, max_bytes: int) -> bytes:
    """Read a bounded regular file, failing on observed identity/path drift.

    Native absolute paths only. Ancestors are checked root-first before opening
    and after reading; the held descriptor's identity/metadata must match both
    endpoint observations. Actual reads are bounded even if the file grows.
    Read and close failures are both preserved in ``RetainedFileError.errors``.
    A successful read supplies observed-byte consistency, not immutability or
    native producer provenance, and cannot prevent a later path replacement.
    """
    errors: list[Exception] = []
    descriptor: int | None = None
    data = b""
    try:
        if type(path) is not str or not path or path != path.strip() or "\x00" in path:
            raise ValueError("retained-file path must be a nonempty unambiguous string")
        if type(max_bytes) is not int or max_bytes <= 0:
            raise ValueError("retained-file maximum byte count must be a positive integer")
        target = Path(path)
        if not target.is_absolute() or target == Path(target.anchor):
            raise ValueError("retained-file path must name an absolute file")
        if ".." in target.parts:
            raise ValueError("retained-file traversal components are forbidden")
        before = _path_snapshot(target)
        size = before[-1][3]
        if size > max_bytes:
            raise ValueError(f"retained file size {size} exceeds maximum {max_bytes}")
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(target, flags)
        if _stamp(os.fstat(descriptor)) != before[-1]:
            raise ValueError("held retained-file identity differs from its admitted path")
        chunks: list[bytes] = []
        read_count = 0
        while read_count <= size:
            chunk = os.read(descriptor, min(65536, size + 1 - read_count))
            if not chunk:
                break
            chunks.append(chunk)
            read_count += len(chunk)
            if read_count > size:
                raise ValueError("retained file grew during its bounded read")
        if read_count != size:
            raise ValueError("retained file ended before its admitted byte count")
        if _stamp(os.fstat(descriptor)) != before[-1]:
            raise ValueError("held retained-file identity/metadata changed during read")
        if _path_snapshot(target) != before:
            raise ValueError("retained-file path or ancestor identity/metadata changed during read")
        data = b"".join(chunks)
    except Exception as error:
        errors.append(error)
    finally:
        if descriptor is not None:
            try:
                os.close(descriptor)
            except Exception as error:
                errors.append(error)
    if errors:
        raise RetainedFileError(f"retained file read rejected for {path!r}", tuple(errors)) from errors[0]
    return data


# This is the sole frame-check IO seam. Tests can scope a patch to this module
# and a fixed synthetic inventory; payload fields cannot replace the reader.
_read_retained_file = read_retained_file


def validate_retained_frames(payload: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Check every declared full raw frame against its retained indexed8 bytes."""
    failures: list[str] = []
    results: list[dict[str, Any]] = []
    summary: dict[str, Any] = {
        "scope": "retained_hidden_indexed8_frame_byte_consistency_only",
        "expected_frame_bytes": _FRAME_BYTES,
        "frame_count": 0,
        "read_frame_count": 0,
        "consistent_frame_count": 0,
        "frames": results,
        "retained_frame_bytes_consistent": False,
        "immutable_files_authenticated": False,
        "native_producer_authenticated": False,
        "coherent_capture_authenticated": False,
        "original_file_authenticated": False,
    }
    if type(payload) is not dict:
        return summary, ["retained-frame payload must be an object"]
    output = _windows_path(payload.get("output_directory"), "output_directory", failures)
    if output is not None and output.parent != HIDDEN_OUTPUT_ROOT:
        failures.append("retained-frame output_directory must be one immediate canonical hidden run")
        output = None
    rows = payload.get("frame_samples")
    if type(rows) is not list or not rows:
        failures.append("retained-frame frame_samples must be a nonempty array")
        return summary, failures
    if "evidence_frames" in payload:
        failures.append("retained-frame evidence_frames cannot substitute or filter frame_samples")
    summary["frame_count"] = len(rows)
    names: set[str] = set()
    paths: set[str] = set()
    for index, row in enumerate(rows):
        label = f"retained frame {index}"
        prior_failures = len(failures)
        if type(row) is not dict:
            failures.append(f"{label} must be an object")
            results.append({"index": index, "passed": False})
            continue
        name = row.get("Name")
        name_match = _FRAME_NAME.fullmatch(name) if type(name) is str else None
        if name_match is None or int(name_match[1]) <= 0 or name != f"frame-{int(name_match[1]):04d}":
            failures.append(f"{label}.Name must use its canonical positive frame-NNNN spelling")
            name = None
        elif name in names:
            failures.append(f"{label}.Name duplicates another retained frame")
        else:
            names.add(name)
        raw_path = _windows_path(row.get("RawPath"), f"{label}.RawPath", failures)
        binding_valid = output is not None and name is not None and raw_path == output / "frames" / f"{name}.raw"
        if not binding_valid:
            failures.append(f"{label}.RawPath must match output_directory/frames/Name.raw exactly")
        if raw_path is not None:
            key = str(raw_path).casefold()
            if key in paths:
                failures.append(f"{label}.RawPath duplicates another retained frame")
            paths.add(key)
        if type(row.get("Width")) is not int or row["Width"] != 800 or type(row.get("Height")) is not int or row["Height"] != 600:
            failures.append(f"{label} must declare the fixed 800x600 indexed8 byte layout")
        declared_hash = row.get("Hash")
        if type(declared_hash) is not str or not _SHA256.fullmatch(declared_hash):
            failures.append(f"{label}.Hash must be a SHA-256 digest")
        nonblack = row.get("NonblackPercent")
        if type(nonblack) not in (int, float) or not 0 <= nonblack <= 100 or not math.isfinite(nonblack):
            failures.append(f"{label}.NonblackPercent must be a finite number in 0..100")
        colors = row.get("UniqueSampleColors")
        if type(colors) is not int or not 0 <= colors <= 256:
            failures.append(f"{label}.UniqueSampleColors must be an integer in 0..256")
        result = {"index": index, "name": name, "raw_path": str(raw_path) if raw_path is not None else None, "passed": False}
        results.append(result)
        if not binding_valid:
            continue
        try:
            data = _read_retained_file(str(raw_path), _FRAME_BYTES)
            if type(data) is not bytes or len(data) != _FRAME_BYTES:
                raise ValueError(f"full indexed8 frame must contain exactly {_FRAME_BYTES} bytes")
            summary["read_frame_count"] += 1
            digest = hashlib.sha256(data).hexdigest()
            # Match the producer's .NET Math.Round(value, 3): midpoint-to-even
            # after decimal scaling, rather than Python's decimal repr rounding.
            actual_nonblack = round(((len(data) - data.count(0)) * 100.0 / len(data)) * 1000.0) / 1000.0
            actual_colors = len(set(data))
            result.update(byte_count=len(data), sha256=digest, nonblack_percent=actual_nonblack, unique_sample_colors=actual_colors)
            if type(declared_hash) is str and digest != declared_hash.lower():
                failures.append(f"{label}.Hash does not match retained raw bytes")
            if actual_nonblack != nonblack:
                failures.append(f"{label}.NonblackPercent does not match retained raw bytes")
            if actual_colors != colors:
                failures.append(f"{label}.UniqueSampleColors does not match retained raw bytes")
        except Exception as error:
            failures.append(f"{label} retained raw read failed: {type(error).__name__}: {error}")
        result["passed"] = len(failures) == prior_failures
        if result["passed"]:
            summary["consistent_frame_count"] += 1
    summary["retained_frame_bytes_consistent"] = not failures
    return summary, failures
