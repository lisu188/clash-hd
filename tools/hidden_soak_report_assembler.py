#!/usr/bin/env python3
"""Assemble the hidden-CDB host soak report (environment=hidden_cdb_host).

APPROVED PROOF CLASS (user ruling 2026-07-27, memory no-popup-windows.md): the
hidden-CDB soak is a THIRD additive evidence variant next to the host
visible-runtime soak and the QEMU-Win98 guest soak. This assembler turns the
raw samples payload written by scripts/cdb/run_hidden_soak.ps1 into the
canonical hidden-class report JSON plus a RUN-SUMMARY.md, enforcing the honesty
contract:

- ``input_responsiveness`` is ALWAYS the ``not_applicable_hidden`` sentinel.
  A samples payload that carries any input measurement (a numeric
  responsiveness value, input drift fields, route_results rows) FAILS - a
  hidden desktop delivers no input, so any such number would be fabricated.
- ALL host process metrics (working set, private memory, handle growth,
  exit/clean-stop) STAY REQUIRED - unlike the guest class, the game is a real
  host process here. Missing process telemetry FAILS; it is never defaulted.
- Frame/render metrics must come from real periodic surface reads
  (capture mode ``hidden-cdb-host-readprocessmemory``); hashes are recomputed
  summary-side from the actual frame rows, never trusted from a summary field.
- Forced-entry mechanics are DISCLOSED: ``entry_mechanism`` names the
  breakpoint-forced loader map entry, and ``pan_mechanism`` names the forced
  scroll writes for map-pan. These fields are always present, never hidden.
- Every report is stamped ``environment=hidden_cdb_host`` so it can never be
  mistaken for a visible-runtime or guest soak.

Fail-closed everywhere: a metric that cannot be measured is recorded as the
sentinel with a reason, never a made-up number, and every missing proof marker
(ready row, route start, route end) is a failure.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from hd_soak_report import (  # noqa: E402
    EXPECTED_BASE_SHA256,
    PROTECTED_STABLE_STAGE,
    integer_or_none,
    float_or_none,
    is_sha256,
    normalize_sha,
    status_text,
    timestamp_span_seconds,
)

HIDDEN_ENVIRONMENT = "hidden_cdb_host"
HIDDEN_EVIDENCE_CLASS = "approved_hidden_cdb_host_soak"
NOT_APPLICABLE_HIDDEN = "not_applicable_hidden"
HIDDEN_CAPTURE_MODE = "hidden-cdb-host-readprocessmemory"
HIDDEN_FRAME_READ_METHOD = "host_readprocessmemory"
ENTRY_MECHANISM = "cdb_breakpoint_forced_loader_entry"
PAN_MECHANISM = "cdb_forced_scroll_write"
NO_PAN_MECHANISM = "none"
ELAPSED_COVERAGE_FORMULA = "duration_sec - sample_interval_sec - 2"
HIDDEN_RUNTIME_POLICY = (
    "opt-in approved hidden-CDB host soak (environment=hidden_cdb_host); the game runs "
    "as a real host process on a hidden desktop with no input delivery; "
    "input_responsiveness is the not_applicable_hidden sentinel and is never "
    "fabricated; all host process metrics stay required; frame metrics come "
    "from real periodic ReadProcessMemory surface reads; map entry and any pan "
    "are breakpoint-forced and disclosed; never a visible-runtime or guest proof"
)
INPUT_RESPONSIVENESS_REASON = (
    "hidden-desktop run delivers no user input; responsiveness cannot be "
    "measured and is recorded as the sentinel, never fabricated"
)
NONBLACK_DEFINITION = (
    "percent of surface bytes with a nonzero 8-bit palette index, computed from "
    "real ReadProcessMemory surface bytes (palette index 0 is the engine clear "
    "color)"
)
UNIQUE_COLORS_DEFINITION = (
    "count of distinct 8-bit palette indices present in the full surface read"
)
# Fields whose presence in a samples payload means someone tried to smuggle an
# input measurement into a hidden run. Any of them present and non-empty fails.
FORBIDDEN_INPUT_FIELDS = (
    "input_max_abs_error",
    "input_max_sample_abs_error",
    "route_results",
)
FIXED_TIER_DURATIONS = {120: "short2", 600: "short10", 1800: "short30"}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def derive_tier(duration_sec: int | None) -> str:
    if duration_sec in FIXED_TIER_DURATIONS:
        return FIXED_TIER_DURATIONS[duration_sec]
    return "custom"


def nonempty_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def cdb_hex_pointer(value: Any) -> int | None:
    """Parse a pointer printed by CDB, whose unprefixed form is hexadecimal."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value > 0 else None
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    if text.lower().startswith("0x"):
        text = text[2:]
    if not text or not all(character in "0123456789abcdefABCDEF" for character in text):
        return None
    parsed = int(text, 16)
    return parsed if parsed > 0 else None


def canonical_pointer(value: Any) -> str | None:
    parsed = cdb_hex_pointer(value)
    return f"0x{parsed:08x}" if parsed is not None else None


def disabled_presentation(value: Any) -> bool:
    return value is False or (type(value) is int and value == 0)


def assemble_report(
    samples: dict[str, Any],
    *,
    min_frames: int = 2,
    min_nonblack_percent: float = 10.0,
    min_unique_sample_colors: int = 8,
    expected_width: int = 800,
    expected_height: int = 600,
) -> dict[str, Any]:
    failures: list[str] = []

    route = str(samples.get("route") or "")
    duration_sec = integer_or_none(samples.get("duration_sec"))
    frame_interval_sec = integer_or_none(samples.get("frame_interval_sec"))
    frame_samples = list(samples.get("frame_samples") or [])
    process_samples = list(samples.get("process_samples") or [])
    capture_errors = list(samples.get("capture_errors") or [])
    runner_failures = [str(row) for row in (samples.get("runner_failures") or [])]
    ready_marker = samples.get("ready_marker")
    route_start_marker = samples.get("route_start_marker")
    route_end_marker = samples.get("route_end_marker")
    pan_events = samples.get("pan_events")
    proxy = samples.get("proxy")
    cleanup = samples.get("cleanup")

    executed = samples.get("executed") is True
    if not executed:
        failures.append("samples payload was not produced by an execution run (executed is not true)")

    if samples.get("environment") != HIDDEN_ENVIRONMENT:
        failures.append(
            f"samples environment is {samples.get('environment')!r}; this assembler only builds "
            f"{HIDDEN_ENVIRONMENT!r} reports"
        )

    if route not in {"map-idle", "map-pan"}:
        failures.append(f"unknown hidden soak route: {route!r}")
    if duration_sec is None or duration_sec <= 0:
        failures.append("duration_sec is missing or not positive")
    if frame_interval_sec is None or frame_interval_sec <= 0:
        failures.append("frame_interval_sec is missing or not positive")

    # --- honesty: refuse imported/fabricated input measurements --------------
    reported_input = samples.get("input_responsiveness")
    if reported_input != NOT_APPLICABLE_HIDDEN:
        failures.append(
            f"input_responsiveness is {reported_input!r}; a hidden run cannot measure input and "
            f"must record the {NOT_APPLICABLE_HIDDEN!r} sentinel, never a value"
        )
    smuggled = [
        field
        for field in FORBIDDEN_INPUT_FIELDS
        if field in samples and samples.get(field) not in (None, [], {})
    ]
    if smuggled:
        failures.append(
            "hidden run cannot carry input-responsiveness measurements; refusing fields: "
            + ", ".join(smuggled)
        )

    # --- failures carried from the runner ------------------------------------
    failures.extend(runner_failures)
    if capture_errors:
        failures.append(f"capture_errors contains {len(capture_errors)} row(s)")

    # --- structured proof markers (fail closed) ------------------------------
    # Legacy booleans are retained in the output for compatibility, but they
    # are derived from these parsed rows and can never substitute for them.
    ready_valid = isinstance(ready_marker, dict)
    ready_width = integer_or_none(ready_marker.get("width")) if ready_valid else None
    ready_height = integer_or_none(ready_marker.get("height")) if ready_valid else None
    ready_bytes = integer_or_none(ready_marker.get("bytes")) if ready_valid else None
    ready_base = canonical_pointer(ready_marker.get("base")) if ready_valid else None
    ready_surface = cdb_hex_pointer(ready_marker.get("surface")) if ready_valid else None
    ready_redraw_seq = integer_or_none(ready_marker.get("redraw_seq")) if ready_valid else None
    if not ready_valid:
        failures.append("ready_marker is missing or malformed; the anchored SOAK_SURFDUMP_READY row is required")
    else:
        if ready_marker.get("source") not in {"SOAK_SURFDUMP_READY", "SURFDUMP_READY"}:
            failures.append("ready_marker.source is not an anchored surface-ready marker")
        if ready_redraw_seq is None or ready_redraw_seq < 0:
            failures.append("ready_marker.redraw_seq is missing or invalid")
        if ready_surface is None:
            failures.append("ready_marker.surface is missing or invalid")
        if ready_base is None:
            failures.append("ready_marker.base is missing or invalid; the surface base is unproven")
        if ready_width != expected_width or ready_height != expected_height:
            failures.append(
                f"ready_marker size is {ready_width}x{ready_height}, expected {expected_width}x{expected_height}"
            )
        if ready_bytes != expected_width * expected_height:
            failures.append(
                f"ready_marker.bytes is {ready_bytes}, expected {expected_width * expected_height}"
            )
    legacy_surface = samples.get("surface") if isinstance(samples.get("surface"), dict) else {}
    legacy_surface_base = canonical_pointer(legacy_surface.get("Base"))
    surface_base = ready_base or legacy_surface_base
    reported_surface_base = canonical_pointer(samples.get("surface_base"))
    if ready_base is not None and reported_surface_base != ready_base:
        failures.append(
            f"surface_base is {samples.get('surface_base')!r}, expected ready_marker.base {ready_base!r}"
        )
    if samples.get("frame_read_method") != HIDDEN_FRAME_READ_METHOD:
        failures.append(
            f"frame_read_method is {samples.get('frame_read_method')!r}, expected "
            f"{HIDDEN_FRAME_READ_METHOD!r}"
        )

    duration_ticks = integer_or_none(samples.get("duration_ticks"))
    expected_duration_ticks = duration_sec * 64 if duration_sec is not None else None
    start_valid = isinstance(route_start_marker, dict)
    start_route_ticks = integer_or_none(route_start_marker.get("route_ticks")) if start_valid else None
    start_pan = integer_or_none(route_start_marker.get("pan")) if start_valid else None
    start_scroll_x = integer_or_none(route_start_marker.get("scroll_x")) if start_valid else None
    start_scroll_y = integer_or_none(route_start_marker.get("scroll_y")) if start_valid else None
    if not start_valid:
        failures.append("route_start_marker is missing or malformed; anchored SOAK_ROUTE_START evidence is required")
    else:
        if duration_ticks is None or duration_ticks <= 0 or duration_ticks != expected_duration_ticks:
            failures.append(
                f"duration_ticks is {duration_ticks!r}, expected {expected_duration_ticks!r} from duration_sec"
            )
        if start_route_ticks != duration_ticks:
            failures.append(
                f"route_start_marker.route_ticks is {start_route_ticks!r}, expected requested {duration_ticks!r}"
            )
        expected_pan = 1 if route == "map-pan" else 0
        if start_pan != expected_pan:
            failures.append(
                f"route_start_marker.pan is {start_pan!r}, expected {expected_pan} for route {route!r}"
            )
        for field in ("player", "tick", "scroll_x", "scroll_y"):
            if integer_or_none(route_start_marker.get(field)) is None:
                failures.append(f"route_start_marker.{field} is missing or invalid")
        if cdb_hex_pointer(route_start_marker.get("game_data")) is None:
            failures.append("route_start_marker.game_data is missing or invalid")

    end_valid = isinstance(route_end_marker, dict)
    end_tick_delta = integer_or_none(route_end_marker.get("tick_delta")) if end_valid else None
    if not end_valid:
        failures.append("route_end_marker is missing or malformed; anchored SOAK_ROUTE_END evidence is required")
    else:
        for field in ("hits", "tick_delta", "player", "scroll_x", "scroll_y"):
            if integer_or_none(route_end_marker.get(field)) is None:
                failures.append(f"route_end_marker.{field} is missing or invalid")
        if integer_or_none(route_end_marker.get("hits")) is not None and integer_or_none(
            route_end_marker.get("hits")
        ) <= 0:
            failures.append("route_end_marker.hits must be positive")
        if duration_ticks is None or end_tick_delta is None or end_tick_delta < duration_ticks:
            failures.append(
                f"route_end_marker.tick_delta is {end_tick_delta!r}, below requested {duration_ticks!r}"
            )

    heartbeat_count = integer_or_none(samples.get("heartbeat_count"))
    if heartbeat_count is None or heartbeat_count <= 0:
        failures.append("heartbeat_count is missing or zero; anchored SOAK_HEARTBEAT evidence is required")

    if not isinstance(pan_events, list):
        failures.append("pan_events is missing or malformed; anchored SOAK_PAN_SET inventory is required")
        pan_events = []
    previous_tick_delta: int | None = None
    previous_hits: int | None = None
    bounded_pan_coordinates = True
    for index, event in enumerate(pan_events):
        if not isinstance(event, dict):
            failures.append(f"pan_events[{index}] is not an object")
            continue
        phase = integer_or_none(event.get("phase"))
        x = integer_or_none(event.get("x"))
        y = integer_or_none(event.get("y"))
        hits = integer_or_none(event.get("hits"))
        tick_delta = integer_or_none(event.get("tick_delta"))
        if None in (phase, x, y, hits, tick_delta):
            failures.append(f"pan_events[{index}] is missing a required numeric field")
            continue
        if phase != index % 4:
            failures.append(f"pan_events[{index}].phase is {phase}, expected ordered phase {index % 4}")
        if previous_tick_delta is not None and tick_delta <= previous_tick_delta:
            failures.append("pan_events tick_delta values are not strictly increasing")
        if previous_hits is not None and hits < previous_hits:
            failures.append("pan_events hits values are not ordered")
        previous_tick_delta = tick_delta
        previous_hits = hits
        if start_scroll_x is not None and start_scroll_y is not None:
            if abs(x - start_scroll_x) > 1 or abs(y - start_scroll_y) > 1:
                bounded_pan_coordinates = False
    if not bounded_pan_coordinates:
        failures.append("pan_events contain scroll coordinates outside the bounded inward +/-1 cycle")

    pan_event_count = len(pan_events)
    reported_pan_event_count = integer_or_none(samples.get("pan_event_count"))
    if reported_pan_event_count is not None and reported_pan_event_count != pan_event_count:
        failures.append(
            f"pan_event_count summary {reported_pan_event_count} does not match {pan_event_count} parsed rows"
        )
    if route == "map-pan" and pan_event_count < 1:
        failures.append("map-pan route recorded no SOAK_PAN_SET forced-scroll events")
    if route == "map-idle" and pan_event_count > 0:
        failures.append(
            f"map-idle route recorded {pan_event_count} forced-scroll events; an idle route must not pan"
        )

    # The memory-only proxy is part of the hidden capture chain. It must have a
    # SHA-tied build/log trail and presentation must remain disabled.
    proxy_valid = isinstance(proxy, dict)
    if not proxy_valid:
        failures.append("proxy provenance is missing or malformed")
        proxy = {}
    else:
        if proxy.get("used") is not True:
            failures.append("memory-only DirectDraw proxy was not used")
        if not nonempty_text(proxy.get("path")) or not str(proxy.get("path")).lower().endswith("ddraw.dll"):
            failures.append("proxy.path is missing or is not the per-candidate ddraw.dll")
        if not is_sha256(proxy.get("sha256")):
            failures.append("proxy.sha256 is missing or invalid")
        if not nonempty_text(proxy.get("build_manifest")):
            failures.append("proxy.build_manifest is missing")
        if not nonempty_text(proxy.get("log")):
            failures.append("proxy.log is missing")
        if not disabled_presentation(proxy.get("present_enabled")):
            failures.append("proxy presentation is not disabled (present_enabled must be false/0)")

    cleanup_valid = isinstance(cleanup, dict)
    raw_cleanup_errors = cleanup.get("errors") if cleanup_valid else None
    cleanup_errors = list(raw_cleanup_errors or []) if isinstance(raw_cleanup_errors, list) else []
    game_stopped = cleanup.get("game_stopped") is True if cleanup_valid else False
    cdb_stopped = cleanup.get("cdb_stopped") is True if cleanup_valid else False
    clean_stop = cleanup_valid and game_stopped and cdb_stopped and not cleanup_errors
    if not cleanup_valid:
        failures.append("cleanup provenance is missing or malformed")
        cleanup = {}
    else:
        if not isinstance(raw_cleanup_errors, list):
            failures.append("cleanup.errors is missing or is not an array")
        if not game_stopped:
            failures.append("cleanup did not verify game process termination")
        if not cdb_stopped:
            failures.append("cleanup did not verify CDB process termination")
        if cleanup_errors:
            failures.append(f"cleanup contains {len(cleanup_errors)} error(s)")
    if samples.get("av_observed") is True:
        failures.append("an access violation row was observed during the soak")
    if samples.get("surface_invalid_observed") is True:
        failures.append("the base template reported SURFDUMP_INVALID")
    if samples.get("app_request_quit_observed") is True:
        failures.append("the game requested App_RequestQuit during the soak")
    if samples.get("cdb_exit_before_duration") is True:
        failures.append("CDB exited before the soak duration completed")
    if samples.get("game_exit_before_duration") is True:
        failures.append("the game process exited before the soak duration completed")

    # --- provenance -----------------------------------------------------------
    stage = samples.get("stage")
    if stage != PROTECTED_STABLE_STAGE:
        failures.append(f"stage is {stage!r}, expected the protected stable stage")
    if normalize_sha(samples.get("input_sha256")) != EXPECTED_BASE_SHA256:
        failures.append("input_sha256 does not match the expected original Clash95 base SHA-256")
    if not is_sha256(samples.get("candidate_sha256")):
        failures.append("candidate_sha256 is missing or is not a SHA-256 hex digest")

    # --- frame inventory + render metrics (real reads only) ------------------
    frame_count = len(frame_samples)
    if frame_count < min_frames:
        failures.append(f"frame sample count {frame_count} is below {min_frames}")
    size_bad = [
        frame
        for frame in frame_samples
        if integer_or_none(frame.get("Width")) != expected_width
        or integer_or_none(frame.get("Height")) != expected_height
    ]
    if size_bad:
        failures.append(f"{len(size_bad)} frame samples were not {expected_width}x{expected_height}")
    bad_hashes = [frame for frame in frame_samples if not is_sha256(frame.get("Hash"))]
    if bad_hashes:
        failures.append(f"{len(bad_hashes)} frame samples have missing or invalid SHA-256 hashes")
    wrong_mode = [
        frame for frame in frame_samples if frame.get("CaptureMode") != HIDDEN_CAPTURE_MODE
    ]
    if wrong_mode:
        failures.append(
            f"{len(wrong_mode)} frame samples did not come through the {HIDDEN_CAPTURE_MODE!r} capture path"
        )

    nonblack_values = [
        value
        for value in (float_or_none(frame.get("NonblackPercent")) for frame in frame_samples)
        if value is not None
    ]
    unique_values = [
        value
        for value in (integer_or_none(frame.get("UniqueSampleColors")) for frame in frame_samples)
        if value is not None
    ]
    if len(nonblack_values) != frame_count:
        failures.append("one or more frame samples are missing NonblackPercent")
    if len(unique_values) != frame_count:
        failures.append("one or more frame samples are missing UniqueSampleColors")
    min_nonblack = min(nonblack_values) if nonblack_values else 0.0
    max_nonblack = max(nonblack_values) if nonblack_values else 0.0
    min_unique = min(unique_values) if unique_values else 0
    max_unique = max(unique_values) if unique_values else 0
    if frame_count and min_nonblack < min_nonblack_percent:
        failures.append(f"minimum nonblack percent {min_nonblack} is below {min_nonblack_percent}")
    if frame_count and min_unique < min_unique_sample_colors:
        failures.append(f"minimum unique sampled colors {min_unique} is below {min_unique_sample_colors}")

    # --- frame progression (hashes recomputed from the actual rows) ----------
    computed_hash_unique_count = len(
        {str(frame.get("Hash")) for frame in frame_samples if frame.get("Hash")}
    )
    frame_progress_expected = route == "map-pan"
    if frame_count <= 0:
        frame_stability_class = "no_frames"
    elif computed_hash_unique_count <= 1:
        frame_stability_class = "stable_idle"
    else:
        frame_stability_class = "progressing"
    if frame_progress_expected and computed_hash_unique_count < 2:
        failures.append(
            "frame progression required for map-pan but fewer than 2 unique frame hashes were recorded"
        )

    # --- forced-pan disclosure consistency ------------------------------------
    pan_interval_sec = integer_or_none(samples.get("pan_interval_sec"))
    if route == "map-pan" and (pan_interval_sec is None or pan_interval_sec <= 0):
        failures.append("map-pan route has no positive pan_interval_sec")

    # --- host process metrics: REQUIRED for the hidden class ------------------
    process_sample_count = len(process_samples)
    if process_sample_count < 2:
        failures.append(f"process sample count {process_sample_count} is below 2")
    exited_rows = [row for row in process_samples if row.get("HasExited") is True]
    if exited_rows:
        failures.append(f"{len(exited_rows)} process samples reported HasExited=True")

    def growth(field: str) -> int | None:
        values = [
            value
            for value in (integer_or_none(row.get(field)) for row in process_samples)
            if value is not None
        ]
        if len(values) < 2:
            return None
        return values[-1] - values[0]

    working_set_growth = growth("WorkingSet64")
    private_memory_growth = growth("PrivateMemorySize64")
    handle_growth = growth("HandleCount")
    max_working_set_growth_mb = integer_or_none(samples.get("max_working_set_growth_mb")) or 64
    max_private_memory_growth_mb = integer_or_none(samples.get("max_private_memory_growth_mb")) or 64
    max_handle_growth = integer_or_none(samples.get("max_handle_growth")) or 128
    working_set_limit = max_working_set_growth_mb * 1024 * 1024
    private_memory_limit = max_private_memory_growth_mb * 1024 * 1024
    if working_set_growth is None:
        failures.append(
            "working_set_growth_bytes could not be computed; host process metrics are REQUIRED "
            "for the hidden class and are never defaulted"
        )
    elif working_set_growth > working_set_limit:
        failures.append(f"working_set_growth_bytes {working_set_growth} exceeds limit {working_set_limit}")
    if private_memory_growth is None:
        failures.append(
            "private_memory_growth_bytes could not be computed; host process metrics are REQUIRED "
            "for the hidden class and are never defaulted"
        )
    elif private_memory_growth > private_memory_limit:
        failures.append(
            f"private_memory_growth_bytes {private_memory_growth} exceeds limit {private_memory_limit}"
        )
    if handle_growth is None:
        failures.append(
            "handle_growth could not be computed; host process metrics are REQUIRED for the "
            "hidden class and are never defaulted"
        )
    elif handle_growth > max_handle_growth:
        failures.append(f"handle_growth {handle_growth} exceeds limit {max_handle_growth}")

    if samples.get("process_exited_unexpectedly") is True:
        failures.append(f"process exited unexpectedly with code {samples.get('exit_code')}")
    if not clean_stop:
        failures.append("the harness did not stop the run cleanly after SOAK_ROUTE_END")

    # --- elapsed coverage ------------------------------------------------------
    frame_elapsed_sec, invalid_frame_ts = timestamp_span_seconds(frame_samples)
    process_elapsed_sec, invalid_process_ts = timestamp_span_seconds(process_samples)
    if invalid_frame_ts:
        failures.append(f"{invalid_frame_ts} frame samples have missing or invalid timestamps")
    if invalid_process_ts:
        failures.append(f"{invalid_process_ts} process samples have missing or invalid timestamps")
    required_elapsed_sec = None
    if duration_sec is not None and frame_interval_sec is not None and frame_interval_sec > 0:
        required_elapsed_sec = max(0, duration_sec - frame_interval_sec - 2)
    if required_elapsed_sec is not None:
        if frame_elapsed_sec is None:
            failures.append("frame sample elapsed coverage could not be computed")
        elif frame_elapsed_sec < required_elapsed_sec:
            failures.append(
                f"frame sample elapsed coverage {frame_elapsed_sec:.3f}s is below required "
                f"{required_elapsed_sec:.3f}s"
            )
        if process_elapsed_sec is None:
            failures.append("process sample elapsed coverage could not be computed")
        elif process_elapsed_sec < required_elapsed_sec:
            failures.append(
                f"process sample elapsed coverage {process_elapsed_sec:.3f}s is below required "
                f"{required_elapsed_sec:.3f}s"
            )

    reported_elapsed = samples.get("elapsed_coverage")
    if not isinstance(reported_elapsed, dict):
        failures.append("elapsed_coverage provenance is missing or malformed")
        reported_elapsed = {}
    else:
        if reported_elapsed.get("formula") != ELAPSED_COVERAGE_FORMULA:
            failures.append(
                f"elapsed_coverage.formula is {reported_elapsed.get('formula')!r}, expected "
                f"{ELAPSED_COVERAGE_FORMULA!r}"
            )
        reported_required = float_or_none(reported_elapsed.get("required_sec"))
        if (
            required_elapsed_sec is None
            or reported_required is None
            or abs(reported_required - required_elapsed_sec) > 0.001
        ):
            failures.append(
                f"elapsed_coverage.required_sec is {reported_required!r}, expected {required_elapsed_sec!r}"
            )
        for field, computed in (
            ("frame_elapsed_sec", frame_elapsed_sec),
            ("process_elapsed_sec", process_elapsed_sec),
        ):
            reported_value = float_or_none(reported_elapsed.get(field))
            if reported_value is None or computed is None or abs(reported_value - computed) > 0.001:
                failures.append(
                    f"elapsed_coverage.{field} is {reported_value!r}, expected detailed-row value {computed!r}"
                )
        if reported_elapsed.get("passed") is not True:
            failures.append("elapsed_coverage.passed is not true")

    # --- artifact budget -------------------------------------------------------
    artifact_bytes = integer_or_none(samples.get("artifact_bytes"))
    max_artifact_mb = integer_or_none(samples.get("max_artifact_mb"))
    artifact_limit_bytes = None
    if max_artifact_mb is None or max_artifact_mb <= 0:
        failures.append("max_artifact_mb is missing or not positive")
    else:
        artifact_limit_bytes = max_artifact_mb * 1024 * 1024
    if artifact_bytes is None:
        failures.append("artifact_bytes is missing")
    elif artifact_limit_bytes is not None and artifact_bytes > artifact_limit_bytes:
        failures.append(f"artifact bytes {artifact_bytes} exceeds limit {artifact_limit_bytes}")

    # --- disclosures (always present, never hidden) ---------------------------
    entry_mechanism_detail = {
        "mechanism": ENTRY_MECHANISM,
        "forced": True,
        "disclosure": (
            "map entry was FORCED by CDB breakpoints riding the surface-dump base "
            "template loader route (forced main-menu click, forced load-slot select "
            "and accept); it was not reached by user input"
        ),
        "load_slot": integer_or_none(samples.get("load_slot")),
    }
    if route == "map-pan":
        pan_mechanism = PAN_MECHANISM
        pan_mechanism_detail = {
            "mechanism": PAN_MECHANISM,
            "forced": True,
            "disclosure": (
                "map pan was FORCED by periodic CDB writes of a bounded four-phase "
                "cycle into the gameData scroll fields gd+140008/gd+140012 "
                "(SOAK_PAN_SET rows); it was not user input"
            ),
            "pan_interval_sec": pan_interval_sec,
            "pan_event_count": pan_event_count,
            "scroll_fields": ["gd+140008", "gd+140012"],
        }
    else:
        pan_mechanism = NO_PAN_MECHANISM
        pan_mechanism_detail = {
            "mechanism": NO_PAN_MECHANISM,
            "forced": False,
            "pan_event_count": pan_event_count,
        }

    report: dict[str, Any] = {
        "schema": "hidden_cdb_host_soak_report_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "runtime_policy": HIDDEN_RUNTIME_POLICY,
        "environment": HIDDEN_ENVIRONMENT,
        "evidence_class": HIDDEN_EVIDENCE_CLASS,
        "executed": executed,
        "passed": not failures,
        "failures": failures,
        "tier": derive_tier(duration_sec),
        "route": route,
        "duration_sec": duration_sec,
        "sample_interval_sec": frame_interval_sec,
        "stage": stage,
        "protected_stable_stage": PROTECTED_STABLE_STAGE,
        "stable_stage_should_change": False,
        "input_exe": samples.get("input_exe"),
        "input_sha256": samples.get("input_sha256"),
        "candidate": samples.get("candidate"),
        "candidate_sha256": samples.get("candidate_sha256"),
        "patch_stage_report": samples.get("patch_stage_report"),
        "workdir": samples.get("workdir"),
        "output_directory": samples.get("output_directory"),
        "report_json": samples.get("report_json"),
        "report_markdown": samples.get("report_markdown"),
        "cdb_log": samples.get("cdb_log"),
        "generated_probe": samples.get("generated_probe"),
        "launch_mode": samples.get("launch_mode"),
        "entry_mechanism": ENTRY_MECHANISM,
        "entry_mechanism_detail": entry_mechanism_detail,
        "pan_mechanism": pan_mechanism,
        "pan_mechanism_detail": pan_mechanism_detail,
        "input_responsiveness": NOT_APPLICABLE_HIDDEN,
        "input_responsiveness_reason": INPUT_RESPONSIVENESS_REASON,
        "input_proof_class": "hidden_cdb_host_no_input_diagnostic_not_manual",
        "right_bottom_promotion_blocked": True,
        "capture_mode": HIDDEN_CAPTURE_MODE,
        "surface": samples.get("surface"),
        "surface_base": surface_base,
        "frame_read_method": HIDDEN_FRAME_READ_METHOD,
        "ready_marker": ready_marker if isinstance(ready_marker, dict) else None,
        "route_start_marker": route_start_marker if isinstance(route_start_marker, dict) else None,
        "route_end_marker": route_end_marker if isinstance(route_end_marker, dict) else None,
        "pan_events": pan_events,
        "proxy": proxy,
        "cleanup": cleanup,
        "ready_observed": ready_valid,
        "soak_route_start_observed": start_valid,
        "soak_route_end_observed": end_valid,
        "heartbeat_count": heartbeat_count or 0,
        "pan_event_count": pan_event_count,
        "av_observed": samples.get("av_observed") is True,
        "frame_sample_count": frame_count,
        "frame_hash_unique_count": computed_hash_unique_count,
        "frame_progress_expected": frame_progress_expected,
        "frame_stability_class": frame_stability_class,
        "nonblack_percent_min": min_nonblack,
        "nonblack_percent_max": max_nonblack,
        "unique_sample_colors_min": min_unique,
        "unique_sample_colors_max": max_unique,
        "nonblack_definition": NONBLACK_DEFINITION,
        "unique_colors_definition": UNIQUE_COLORS_DEFINITION,
        "frame_elapsed_sec": frame_elapsed_sec,
        "process_elapsed_sec": process_elapsed_sec,
        "required_elapsed_sec": required_elapsed_sec,
        "elapsed_coverage": {
            "formula": ELAPSED_COVERAGE_FORMULA,
            "required_sec": required_elapsed_sec,
            "frame_elapsed_sec": frame_elapsed_sec,
            "process_elapsed_sec": process_elapsed_sec,
            "passed": (
                required_elapsed_sec is not None
                and frame_elapsed_sec is not None
                and process_elapsed_sec is not None
                and frame_elapsed_sec >= required_elapsed_sec
                and process_elapsed_sec >= required_elapsed_sec
            ),
        },
        "process_sample_count": process_sample_count,
        "working_set_growth_bytes": working_set_growth,
        "private_memory_growth_bytes": private_memory_growth,
        "handle_growth": handle_growth,
        "max_working_set_growth_mb": max_working_set_growth_mb,
        "max_private_memory_growth_mb": max_private_memory_growth_mb,
        "max_handle_growth": max_handle_growth,
        "working_set_growth_limit_bytes": working_set_limit,
        "private_memory_growth_limit_bytes": private_memory_limit,
        "process_exited_unexpectedly": samples.get("process_exited_unexpectedly") is True,
        "exit_code": samples.get("exit_code"),
        "clean_stop": clean_stop,
        "clean_stop_mechanism": "verified_game_and_cdb_termination",
        "max_artifact_mb": max_artifact_mb,
        "artifact_limit_bytes": artifact_limit_bytes,
        "artifact_bytes": artifact_bytes,
        "frame_samples": frame_samples,
        "process_samples": process_samples,
        "capture_errors": capture_errors,
    }
    return report


def to_markdown(report: dict[str, Any]) -> str:
    overall = "PASS" if report.get("passed") else "FAIL"
    entry_detail = report.get("entry_mechanism_detail") or {}
    pan_detail = report.get("pan_mechanism_detail") or {}
    lines = [
        "# HD Hidden-CDB Host Soak Report",
        "",
        f"- **environment={report.get('environment')}** (never a visible-runtime or guest soak)",
        f"- Evidence class: `{report.get('evidence_class')}`",
        f"- Overall: {overall}",
        f"- Generated: `{report.get('generated_at')}`",
        f"- Tier / route: `{report.get('tier')}` / `{report.get('route')}`",
        f"- Duration seconds: `{report.get('duration_sec')}`",
        f"- Sample interval seconds: `{report.get('sample_interval_sec')}`",
        f"- Stage: `{report.get('stage')}`",
        f"- Candidate SHA-256: `{report.get('candidate_sha256')}`",
        f"- Output directory: `{report.get('output_directory')}`",
        "",
        "## Honesty contract",
        "",
        f"- Input responsiveness: `{report.get('input_responsiveness')}` "
        f"({report.get('input_responsiveness_reason')})",
        f"- FORCED entry (disclosed): `{report.get('entry_mechanism')}` "
        f"load_slot={entry_detail.get('load_slot')}",
        f"- Pan mechanism (disclosed): `{report.get('pan_mechanism')}` "
        f"forced={pan_detail.get('forced')} events={pan_detail.get('pan_event_count')}",
        f"- Surface base / read method: `{report.get('surface_base')}` / "
        f"`{report.get('frame_read_method')}`",
        f"- Memory-only proxy SHA / present_enabled: `{(report.get('proxy') or {}).get('sha256')}` / "
        f"`{(report.get('proxy') or {}).get('present_enabled')}`",
        f"- Nonblack definition: {report.get('nonblack_definition')}",
        "",
        "## Render evidence (real ReadProcessMemory surface reads)",
        "",
        f"- Frame samples: `{report.get('frame_sample_count')}`",
        f"- Unique frame hashes (computed from rows): `{report.get('frame_hash_unique_count')}`",
        f"- Frame stability class: `{report.get('frame_stability_class')}`",
        f"- Nonblack min/max: `{report.get('nonblack_percent_min')}` / `{report.get('nonblack_percent_max')}`",
        f"- Unique sampled colors min/max: `{report.get('unique_sample_colors_min')}` / "
        f"`{report.get('unique_sample_colors_max')}`",
        f"- Heartbeats: `{report.get('heartbeat_count')}`",
        "",
        "## Host process metrics (required)",
        "",
        f"- Process samples: `{report.get('process_sample_count')}`",
        f"- Working set growth bytes: `{report.get('working_set_growth_bytes')}`",
        f"- Private memory growth bytes: `{report.get('private_memory_growth_bytes')}`",
        f"- Handle growth: `{report.get('handle_growth')}`",
        f"- Process exited unexpectedly: `{report.get('process_exited_unexpectedly')}`",
        f"- Clean stop: `{report.get('clean_stop')}` (`{report.get('clean_stop_mechanism')}`)",
        f"- Artifact bytes: `{report.get('artifact_bytes')}` (limit `{report.get('artifact_limit_bytes')}`)",
    ]
    png_frames = [
        frame for frame in (report.get("frame_samples") or []) if frame.get("PngPath")
    ]
    if png_frames:
        lines.extend(["", "## Edge frames", ""])
        for frame in png_frames:
            lines.append(
                f"- {frame.get('Name')}: nonblack={frame.get('NonblackPercent')} "
                f"colors={frame.get('UniqueSampleColors')} hash={frame.get('Hash')}"
            )
            lines.append(f"  ![{frame.get('Name')}]({frame.get('PngPath')})")
    if report.get("failures"):
        lines.extend(["", "## Failures", ""])
        for failure in report["failures"]:
            lines.append(f"- {failure}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("samples", type=Path, help="samples JSON written by run_hidden_soak.ps1")
    parser.add_argument("--write-json", type=Path)
    parser.add_argument("--write-markdown", "--write-md", dest="write_markdown", type=Path)
    parser.add_argument("--min-nonblack-percent", type=float, default=10.0)
    parser.add_argument("--min-unique-sample-colors", type=int, default=8)
    parser.add_argument("--require-pass", action="store_true")
    args = parser.parse_args()

    samples = load_json(args.samples)
    report = assemble_report(
        samples,
        min_nonblack_percent=args.min_nonblack_percent,
        min_unique_sample_colors=args.min_unique_sample_colors,
    )
    if args.write_json:
        args.write_json.parent.mkdir(parents=True, exist_ok=True)
        args.write_json.write_text(json.dumps(report, indent=2), encoding="ascii")
    if args.write_markdown:
        args.write_markdown.parent.mkdir(parents=True, exist_ok=True)
        args.write_markdown.write_text(to_markdown(report), encoding="ascii")

    print(f"environment: {report['environment']}")
    print(f"overall: {status_text(bool(report['passed']))}")
    print(f"route: {report.get('route')} tier: {report.get('tier')} duration: {report.get('duration_sec')}s")
    print(f"input_responsiveness: {report['input_responsiveness']}")
    if report["failures"]:
        print("failures:")
        for failure in report["failures"]:
            print(f"  - {failure}")
    if args.require_pass and not report["passed"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
