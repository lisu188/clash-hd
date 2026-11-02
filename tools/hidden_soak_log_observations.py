"""Anchored hidden-CDB log parsing and retained-byte observation consistency.

The reader is fixed in production. A digest, parsed row or successful replay
does not authenticate the native producer, process, loaded image, coherent
capture, running time, manual input or promotion readiness.
"""
from __future__ import annotations

import hashlib
import re
from typing import Any

from hidden_soak_artifact_layout import HIDDEN_OUTPUT_ROOT, _windows_path
from hidden_soak_retained_files import read_retained_file as _reader


MAX_LOG_BYTES = 64 * 1024 * 1024
_SHA256 = re.compile(r"[0-9a-fA-F]{64}\Z")
_POINTER = r"[0-9a-fA-F`]+"
_ROW_SPECS = (
    (rf"(SOAK_SURFDUMP_READY|SURFDUMP_READY) redraw_seq=(\d+) surface=({_POINTER}) size=\((\d+),(\d+)\) base=({_POINTER}) bytes=(\d+)",
     "ReadyRows", ("Source", "RedrawSeq", "Surface", "Width", "Height", "Base", "Bytes")),
    (rf"SOAK_ROUTE_START route_ticks=(\d+) pan=(0|1) player=(-?\d+) tick=(-?\d+) gd=({_POINTER}) scroll=\((-?\d+),(-?\d+)\)",
     "RouteStarts", ("RouteTicks", "Pan", "Player", "Tick", "GameData", "ScrollX", "ScrollY")),
    (r"SOAK_ROUTE_END route_ticks=(\d+) pan=(0|1) hits=(\d+) tickdelta=(\d+) player=(-?\d+) scroll=\((-?\d+),(-?\d+)\)",
     "RouteEnds", ("RouteTicks", "Pan", "Hits", "TickDelta", "Player", "ScrollX", "ScrollY")),
    (r"SOAK_HEARTBEAT hits=(\d+) tickdelta=(\d+) player=(-?\d+) scroll=\((-?\d+),(-?\d+)\)",
     "Heartbeats", ("Hits", "TickDelta", "Player", "ScrollX", "ScrollY")),
    (r"SOAK_PAN_PLAN base=\((-?\d+),(-?\d+)\) delta=\((-?\d+),(-?\d+)\) max=\((-?\d+),(-?\d+)\) safe=1",
     "PanPlans", ("BaseX", "BaseY", "DeltaX", "DeltaY", "MaxX", "MaxY")),
    (r"SOAK_PAN_UNSAFE base=\((-?\d+),(-?\d+)\) max=\((-?\d+),(-?\d+)\) reason=([a-z0-9_-]+)",
     "PanUnsafeRows", ("BaseX", "BaseY", "MaxX", "MaxY", "Reason")),
    (r"SOAK_PAN_SET phase=(\d+) x=(-?\d+) y=(-?\d+) hits=(\d+) tickdelta=(\d+) delta=\((-?\d+),(-?\d+)\)",
     "PanEvents", ("Phase", "X", "Y", "Hits", "TickDelta", "DeltaX", "DeltaY")),
)
_ROWS = tuple((re.compile(pattern, re.ASCII), bucket, fields) for pattern, bucket, fields in _ROW_SPECS)
_TEXT_FIELDS = {"Source", "Surface", "Base", "GameData", "Reason"}
_INT64_FIELDS = {"RedrawSeq", "RouteTicks", "Tick", "Hits", "TickDelta"}
_FAILURE_FLAGS = {
    "av_observed": "AvObserved", "surface_invalid_observed": "SurfaceInvalidObserved",
    "app_request_quit_observed": "AppRequestQuitObserved",
}
_MARKER = re.compile(
    r"^(SOAK_SURFDUMP_READY|SURFDUMP_READY|SOAK_ROUTE_START|SOAK_ROUTE_END|SOAK_HEARTBEAT|"
    r"SOAK_PAN_PLAN|SOAK_PAN_UNSAFE|SOAK_PAN_SET|AV_SURFDUMP|SURFDUMP_INVALID|SURFDUMP_APP_REQUEST_QUIT)(?:\s+(.*))?$",
    re.ASCII,
)
_FIELD_ATTEMPT = re.compile(
    r"^(?:redraw_seq|route_ticks|hits|base|phase|text_ptr|caption_ptr|surface|scroll|pan|tickdelta|delta|max|safe)\b"
    r"|\b[A-Za-z_][A-Za-z0-9_]*\s*=", re.ASCII,
)
_QUIT = re.compile(rf"SURFDUMP_APP_REQUEST_QUIT text_ptr={_POINTER} caption_ptr={_POINTER}", re.ASCII | re.IGNORECASE)


def parse_soak_log(log_bytes: bytes) -> dict[str, Any]:
    """Mirror PowerShell Parse-SoakLog rows, with explicit malformed diagnostics.

    ASCII marker bytes are scanned reversibly in non-BOM logs; localized CDB
    startup prose is not interpreted. BOM-marked Unicode uses its declared
    encoding. CRLF/LF line positions and trimmed marker rows match PowerShell.
    Printed startup prose beginning ``SOAK_PAN_PLAN and ...`` is not a row.
    A bare incomplete marker or structured field attempt that misses the exact
    grammar is a failure, never an observation manufactured from substrings.
    """
    result: dict[str, Any] = {bucket: [] for _, bucket, _ in _ROWS}
    result.update(AvObserved=False, SurfaceInvalidObserved=False, AppRequestQuitObserved=False, failures=[])
    if type(log_bytes) is not bytes or len(log_bytes) > MAX_LOG_BYTES:
        result["failures"].append("CDB log must be original bytes within the fixed log allowance")
        return result
    try:
        if log_bytes.startswith((b"\xff\xfe", b"\xfe\xff")):
            text = log_bytes.decode("utf-16")
        elif log_bytes.startswith(b"\xef\xbb\xbf"):
            text = log_bytes.decode("utf-8-sig")
        else:
            text = log_bytes.decode("latin-1")
    except UnicodeError as exc:
        result["failures"].append(f"CDB log Unicode decoding failed: {exc}")
        return result
    if "\0" in text:
        result["failures"].append("CDB log contains unexpected NUL characters")
    for line_number, raw_line in enumerate(text.split("\n"), 1):
        line = raw_line.strip()
        if not line:
            continue
        matched = False
        for pattern, bucket, fields in _ROWS:
            match = pattern.fullmatch(line)
            if not match:
                continue
            matched = True
            row: dict[str, Any] = {}
            for field, value in zip(fields, match.groups()):
                if field in _TEXT_FIELDS:
                    row[field] = value
                    continue
                bits = 64 if field in _INT64_FIELDS else 32
                significant = value.lstrip("-").lstrip("0") or "0"
                number = int(significant) * (-1 if value.startswith("-") else 1) if len(significant) <= 19 else None
                if number is None or not -(1 << (bits - 1)) <= number < (1 << (bits - 1)):
                    result["failures"].append(f"CDB log line {line_number}: {field} exceeds the PowerShell int{bits} range")
                    row = {}
                    break
                row[field] = number
            if row:
                if bucket == "PanPlans":
                    row.update(Source="SOAK_PAN_PLAN", Safe=1)
                row["LineNumber"] = line_number
                result[bucket].append(row)
            break
        if matched:
            continue
        # PowerShell -eq and -match used for these failure rows are case
        # insensitive, unlike the explicit [regex]::Match structured rows.
        if line.upper() == "AV_SURFDUMP":
            result["AvObserved"] = True
        elif line.upper() == "SURFDUMP_INVALID":
            result["SurfaceInvalidObserved"] = True
        elif _QUIT.fullmatch(line):
            result["AppRequestQuitObserved"] = True
        else:
            marker = _MARKER.fullmatch(line)
            if marker and (not marker.group(2) or _FIELD_ATTEMPT.search(marker.group(2))):
                result["failures"].append(f"CDB log line {line_number}: malformed structured {marker.group(1)} row")
    return result


_READY_FIELDS = {"source": "Source", "redraw_seq": "RedrawSeq", "surface": "Surface", "base": "Base",
                 "width": "Width", "height": "Height", "bytes": "Bytes", "line_number": "LineNumber"}
_START_FIELDS = {"route_ticks": "RouteTicks", "pan": "Pan", "player": "Player", "tick": "Tick",
                 "game_data": "GameData", "scroll_x": "ScrollX", "scroll_y": "ScrollY", "line_number": "LineNumber"}
_END_FIELDS = {"route_ticks": "RouteTicks", "pan": "Pan", "hits": "Hits", "tick_delta": "TickDelta",
               "player": "Player", "scroll_x": "ScrollX", "scroll_y": "ScrollY", "line_number": "LineNumber"}
_PLAN_FIELDS = {"source": "Source", "safe": "Safe", "base_x": "BaseX", "base_y": "BaseY", "delta_x": "DeltaX",
                "delta_y": "DeltaY", "max_x": "MaxX", "max_y": "MaxY", "line_number": "LineNumber"}
_PAN_FIELDS = {"phase": "Phase", "x": "X", "y": "Y", "hits": "Hits", "tick_delta": "TickDelta",
               "delta_x": "DeltaX", "delta_y": "DeltaY", "line_number": "LineNumber"}


def _compare_row(value: Any, actual: dict[str, Any], fields: dict[str, str], label: str) -> list[str]:
    if not isinstance(value, dict):
        return [f"{label} is missing or is not an object matching the retained log"]
    return [f"{label}.{name} differs from the retained CDB log"
            for name, source in fields.items()
            if name not in value or type(value[name]) is not type(actual[source]) or value[name] != actual[source]]


def _global_order_failures(observed: dict[str, Any]) -> list[str]:
    starts, ends = observed["RouteStarts"], observed["RouteEnds"]
    ready = [row for row in observed["ReadyRows"] if row["Source"] == "SOAK_SURFDUMP_READY"]
    failures = []
    for label, rows in (("SOAK_ROUTE_START", starts), ("SOAK_ROUTE_END", ends), ("SOAK_SURFDUMP_READY", ready)):
        if len(rows) != 1:
            failures.append(f"retained CDB log requires exactly one {label} row, observed {len(rows)}")
    if len(starts) != 1 or len(ends) != 1:
        return failures
    start, end = starts[0], ends[0]
    if end["LineNumber"] <= start["LineNumber"]:
        failures.append("retained route end does not follow route start")
    if len(ready) == 1 and not start["LineNumber"] < ready[0]["LineNumber"] < end["LineNumber"]:
        failures.append("retained SOAK_SURFDUMP_READY is outside route start/end")
    tick, hits, x, y = 0, 0, start["ScrollX"], start["ScrollY"]
    events = sorted(observed["Heartbeats"] + observed["PanEvents"] + ends, key=lambda row: row["LineNumber"])
    for row in events:
        if row["TickDelta"] < tick or row["Hits"] < hits or row["Hits"] <= 0 or (row["Hits"] == hits and row["TickDelta"] != tick):
            failures.append("retained route rows are not globally ordered by redraw tickdelta and hits")
        if "Player" in row and row["Player"] != start["Player"]:
            failures.append("retained route row player differs from route start")
        if "ScrollX" in row and (row["ScrollX"], row["ScrollY"]) != (x, y):
            failures.append("retained route scroll changes outside ordered forced-pan writes")
        if "DeltaX" in row:
            x, y = row["X"], row["Y"]
        if row["TickDelta"] > end["TickDelta"]:
            failures.append("retained route row tickdelta exceeds route end")
        if row not in ends and not start["LineNumber"] < row["LineNumber"] < end["LineNumber"]:
            failures.append("retained heartbeat/pan row is outside route start/end")
        tick, hits = row["TickDelta"], row["Hits"]
    tick, hits = -1, -1
    if not observed["Heartbeats"]:
        failures.append("retained CDB log contains no structured SOAK_HEARTBEAT rows")
    for row in observed["Heartbeats"]:
        if row["TickDelta"] <= tick or row["Hits"] <= hits:
            failures.append("retained heartbeats are not strictly ordered by tickdelta and hits")
        tick, hits = row["TickDelta"], row["Hits"]
    return failures


def validate_retained_log(payload: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Read actual pinned log bytes and compare complete structured inventories."""
    summary: dict[str, Any] = {
        "scope": "retained_cdb_log_bytes_and_observations_only", "checked": True,
        "native_producer_verified": False, "running_time_verified": False,
        "cdb_log": payload.get("cdb_log"), "sha256": None, "size": None,
    }
    layout_failures: list[str] = []
    path = _windows_path(payload.get("cdb_log"), "cdb_log", layout_failures)
    output = _windows_path(payload.get("output_directory"), "output_directory", layout_failures)
    if output is not None and output.parent != HIDDEN_OUTPUT_ROOT:
        layout_failures.append("output_directory is not one canonical hidden run directory")
    if path is not None and output is not None and (path == output or output not in path.parents):
        layout_failures.append("cdb_log must be strictly under the same hidden output_directory")
    failures = list(layout_failures)
    expected_sha, expected_size = payload.get("cdb_log_sha256"), payload.get("cdb_log_size")
    if type(expected_sha) is not str or not _SHA256.fullmatch(expected_sha):
        failures.append("cdb_log_sha256 must retain the collection-time SHA-256")
    if type(expected_size) is not int or not 0 < expected_size <= MAX_LOG_BYTES:
        failures.append("cdb_log_size must retain a positive bounded collection-time byte count")
    if layout_failures or path is None or output is None:
        return summary, failures
    try:
        raw = _reader(str(path), MAX_LOG_BYTES)
        if type(raw) is not bytes:
            raise ValueError("retained-file reader did not return original bytes")
    except (OSError, ValueError, TypeError) as exc:
        failures.append(f"retained CDB log read failed: {type(exc).__name__}: {exc}")
        return summary, failures
    summary.update(sha256=hashlib.sha256(raw).hexdigest(), size=len(raw))
    if type(expected_sha) is str and summary["sha256"] != expected_sha.lower():
        failures.append("retained CDB log SHA-256 differs from its collection-time binding")
    if type(expected_size) is int and len(raw) != expected_size:
        failures.append("retained CDB log size differs from its collection-time binding")
    observed = parse_soak_log(raw)
    failures.extend(observed["failures"])
    failures.extend(_global_order_failures(observed))
    ready = [row for row in observed["ReadyRows"] if row["Source"] == "SOAK_SURFDUMP_READY"]
    for field, rows, fields in (("ready_marker", ready, _READY_FIELDS), ("route_start_marker", observed["RouteStarts"], _START_FIELDS),
                                ("route_end_marker", observed["RouteEnds"], _END_FIELDS)):
        if len(rows) == 1:
            failures.extend(_compare_row(payload.get(field), rows[0], fields, field))
    for field, rows, fields in (("pan_plans", observed["PanPlans"], _PLAN_FIELDS), ("pan_events", observed["PanEvents"], _PAN_FIELDS)):
        supplied = payload.get(field)
        if type(supplied) is not list or len(supplied) != len(rows):
            failures.append(f"{field} inventory differs from the retained CDB log")
        else:
            for index, row in enumerate(rows):
                failures.extend(_compare_row(supplied[index], row, fields, f"{field}[{index}]"))
    for field, actual in (("heartbeat_count", len(observed["Heartbeats"])), ("pan_event_count", len(observed["PanEvents"]))):
        if type(payload.get(field)) is not int or payload[field] != actual:
            failures.append(f"{field} differs from the retained CDB log inventory")
    for field, bucket in _FAILURE_FLAGS.items():
        if type(payload.get(field)) is not bool or payload[field] != observed[bucket]:
            failures.append(f"{field} differs from the retained CDB log failure markers")
        if observed[bucket]:
            failures.append(f"retained CDB log contains {bucket} failure evidence")
    if observed["PanUnsafeRows"]:
        failures.append("retained CDB log contains SOAK_PAN_UNSAFE failure evidence")
    for field, actual in (("ready_observed", len(ready) == 1), ("soak_route_start_observed", len(observed["RouteStarts"]) == 1),
                          ("soak_route_end_observed", len(observed["RouteEnds"]) == 1)):
        if type(payload.get(field)) is not bool or payload[field] != actual:
            failures.append(f"{field} differs from the retained CDB log inventory")
    summary["observation_counts"] = {bucket: len(observed[bucket]) for bucket in ("ReadyRows", "RouteStarts", "RouteEnds", "Heartbeats", "PanPlans", "PanUnsafeRows", "PanEvents")}
    return summary, failures
