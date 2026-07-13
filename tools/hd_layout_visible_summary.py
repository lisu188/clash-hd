#!/usr/bin/env python3
"""Strict repo-only summary for the approved visible HD-layout evidence run.

This tool reads archived PNG/JSON evidence only.  A PASS means that the
validation-only ``hdlayout`` candidate has authentic visible composition for
the bottom-centred terrain tooltip and the active right-bottom command-panel
icons, plus exact automated Win32 cursor placement over the first panel icon.

It deliberately does *not* claim a command click/callback, manual DirectInput
mouse proof, stable-stage promotion, or release readiness.  The archived
descriptor-5 click attempt is parsed and exposed as a failed, screen-edge-
clamped attempt instead of being silently ignored.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path, PureWindowsPath
from typing import Any

import capture_tear_check
from capture_geometry import Image, luminance, read_png


EXPECTED_CANDIDATE_SHA256 = (
    "911A4F1CFB3CFEE7974F50742CC98FDD16DCC82EAA95C88F748E0976140E6FBD"
)
DEFAULT_RUN_DIR = Path("captures/archive/visual-smoke-20260713-075818")
DEFAULT_BASELINE_FRAME = Path("captures/archive/manual-rightbottom-entry/after-load-map.png")
DEFAULT_JSON = Path("captures/current/hd-layout-visible-current.json")
DEFAULT_MD = Path("captures/current/hd-layout-visible-current.md")

# The archived screen grabs are a 1200x900 capture of an 800x600 client (1.5x).
EXPECTED_CAPTURE_SIZE = (1200, 900)
EXPECTED_CLIENT_SIZE = (800, 600)
CAPTURE_SCALE = 1.5

# Broad tooltip search strips.  The predicate isolates the neutral, pale
# terrain string from the orange/green map beneath it.
TOOLTIP_BOTTOM_RECT = (360, 870, 830, 899)
TOOLTIP_LEGACY_RECT = (240, 690, 710, 730)
TOOLTIP_MIN_NEUTRAL_BRIGHT_PIXELS = 300
TOOLTIP_MAX_LEGACY_NEUTRAL_BRIGHT_PIXELS = 20
NEUTRAL_BRIGHT_MIN_LUMA = 160.0
NEUTRAL_BRIGHT_MAX_SPREAD = 80

# Only descriptors 0 and 3 have visible sprites in this save state (globe and
# unit figures).  Their combined 64x64 logical block becomes 96x96 captured
# pixels.  The hidden-CDB layout gate separately proves all six descriptors.
PANEL_ACTIVE_RECT = (912, 792, 1008, 888)
PANEL_FULL_RECT = (912, 792, 1199, 899)
PANEL_LEGACY_ACTIVE_RECT = (624, 600, 720, 696)
PANEL_DIFF_THRESHOLD = 10
PANEL_MIN_ACTIVE_CHANGED_PERCENT = 90.0
PANEL_MIN_FULL_CHANGED_PERCENT = 20.0
PANEL_MAX_LEGACY_CHANGED_PERCENT = 0.1

EXPECTED_HOVER_POINT = (640, 544)
EXPECTED_FAILED_CLICK_POINT = (760, 560)


def _now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def _same_handle(*values: Any) -> bool:
    normalized = [str(value).strip().lower() for value in values]
    return bool(normalized and normalized[0] not in {"", "0", "0x0"} and len(set(normalized)) == 1)


def _capture_authenticity(
    frame: Path,
    sidecar: dict[str, Any],
    *,
    expected_target_hwnd: str | None = None,
) -> dict[str, Any]:
    actual_sha = _sha256(frame)
    recorded_sha = str(sidecar.get("Hash", "")).upper()
    handles_match = _same_handle(
        sidecar.get("TargetHwnd"),
        sidecar.get("CenterWindowHwnd"),
        sidecar.get("CenterRootHwnd"),
    )
    target_hwnd = str(sidecar.get("TargetHwnd", ""))
    cross_capture_hwnd_matches = (
        expected_target_hwnd is None
        or target_hwnd.strip().lower() == expected_target_hwnd.strip().lower()
    )
    passed = (
        frame.is_file()
        and actual_sha == recorded_sha
        and (int(sidecar.get("Width", -1)), int(sidecar.get("Height", -1)))
        == EXPECTED_CAPTURE_SIZE
        and sidecar.get("CaptureMode") == "screen"
        and sidecar.get("CenterWindowMatchesTarget") is True
        and handles_match
        and cross_capture_hwnd_matches
    )
    return {
        "passed": passed,
        "frame": str(frame),
        "actual_sha256": actual_sha,
        "recorded_sha256": recorded_sha,
        "hash_matches": actual_sha == recorded_sha,
        "capture_size": [int(sidecar.get("Width", -1)), int(sidecar.get("Height", -1))],
        "expected_capture_size": list(EXPECTED_CAPTURE_SIZE),
        "capture_mode": sidecar.get("CaptureMode"),
        "center_window_matches_target": sidecar.get("CenterWindowMatchesTarget"),
        "target_hwnd": target_hwnd,
        "center_window_hwnd": sidecar.get("CenterWindowHwnd"),
        "center_root_hwnd": sidecar.get("CenterRootHwnd"),
        "handles_match": handles_match,
        "cross_capture_hwnd_matches": cross_capture_hwnd_matches,
        "origin": [sidecar.get("OriginX"), sidecar.get("OriginY")],
        "nonblack_percent": sidecar.get("NonblackPercent"),
        "mean_luma": sidecar.get("MeanLuma"),
        "unique_sample_colors": sidecar.get("UniqueSampleColors"),
    }


def _candidate_check(results: dict[str, Any]) -> dict[str, Any]:
    recorded_sha = str(results.get("ExeSha256", "")).upper()
    exe = str(results.get("Exe", ""))
    lowered = exe.lower().replace("/", "\\")
    isolated = lowered.startswith("c:\\clashtests\\")
    original = lowered == r"c:\clash\clash95.exe"
    basename = PureWindowsPath(exe).name.lower() if exe else ""
    passed = (
        recorded_sha == EXPECTED_CANDIDATE_SHA256
        and isolated
        and not original
        and basename.startswith("clash95_hd_hdlayout_visible_")
        and basename.endswith(".exe")
    )
    return {
        "passed": passed,
        "recorded_sha256": recorded_sha,
        "expected_sha256": EXPECTED_CANDIDATE_SHA256,
        "sha_matches": recorded_sha == EXPECTED_CANDIDATE_SHA256,
        "exe": exe,
        "isolated_under_clashtests": isolated,
        "is_original_executable": original,
        "expected_candidate_name": basename.startswith("clash95_hd_hdlayout_visible_")
        and basename.endswith(".exe"),
    }


def _gameplay_route_check(results: dict[str, Any], map_frame_sha: str) -> dict[str, Any]:
    map_frame = results.get("MapFrame") if isinstance(results.get("MapFrame"), dict) else {}
    route_steps = results.get("RouteSteps") if isinstance(results.get("RouteSteps"), list) else []
    route_steps_valid = bool(route_steps) and all(
        isinstance(step, dict)
        and step.get("PathVerified") is True
        and step.get("ClickPathVerified") is True
        and step.get("ProbeExitCode") == 0
        and step.get("GameplayFrameLikely") is True
        and not step.get("GameplayWarnings")
        for step in route_steps
    )
    result_map_sha = str(map_frame.get("Hash", "")).upper()
    passed = (
        results.get("MainMenuReady") is True
        and results.get("FinalFrameState") == "gameplay-likely"
        and results.get("GameplayFrameLikely") is True
        and not results.get("GameplayWarnings")
        and results.get("MapPathVerified") is True
        and results.get("MapClickPathVerified") is True
        and results.get("MapProbeExitCode") == 0
        and results.get("Route") == "custom"
        and route_steps_valid
        and result_map_sha == map_frame_sha
    )
    return {
        "passed": passed,
        "main_menu_ready": results.get("MainMenuReady"),
        "final_frame_state": results.get("FinalFrameState"),
        "gameplay_frame_likely": results.get("GameplayFrameLikely"),
        "gameplay_warnings": results.get("GameplayWarnings"),
        "map_path_verified": results.get("MapPathVerified"),
        "map_click_path_verified": results.get("MapClickPathVerified"),
        "map_probe_exit_code": results.get("MapProbeExitCode"),
        "route": results.get("Route"),
        "route_step_count": len(route_steps),
        "route_steps_valid": route_steps_valid,
        "result_map_sha256": result_map_sha,
        "result_map_hash_matches": result_map_sha == map_frame_sha,
        "scope_note": (
            "These are automated route/menu clicks used to reach gameplay; they are not "
            "manual DirectInput or relocated command-panel click proof."
        ),
    }


def _rect(rect: tuple[int, int, int, int]) -> list[int]:
    return list(rect)


def _neutral_bright_stats(image: Image, rect: tuple[int, int, int, int]) -> dict[str, Any]:
    left, top, right, bottom = rect
    if left < 0 or top < 0 or right >= image.width or bottom >= image.height:
        raise ValueError(f"analysis rect {rect} outside {image.width}x{image.height} frame")
    points: list[tuple[int, int]] = []
    for y in range(top, bottom + 1):
        for x in range(left, right + 1):
            rgb = image.rgb_at(x, y)
            if (
                luminance(rgb) >= NEUTRAL_BRIGHT_MIN_LUMA
                and max(rgb) - min(rgb) <= NEUTRAL_BRIGHT_MAX_SPREAD
            ):
                points.append((x, y))
    bounds = None
    if points:
        min_x = min(point[0] for point in points)
        min_y = min(point[1] for point in points)
        max_x = max(point[0] for point in points)
        max_y = max(point[1] for point in points)
        bounds = {
            "x": min_x,
            "y": min_y,
            "right": max_x,
            "bottom": max_y,
            "width": max_x - min_x + 1,
            "height": max_y - min_y + 1,
            "center_x": round((min_x + max_x) / 2.0, 2),
            "center_y": round((min_y + max_y) / 2.0, 2),
        }
    return {
        "rect": _rect(rect),
        "neutral_bright_pixels": len(points),
        "neutral_bright_bounds": bounds,
        "minimum_luma": NEUTRAL_BRIGHT_MIN_LUMA,
        "maximum_channel_spread": NEUTRAL_BRIGHT_MAX_SPREAD,
    }


def _tooltip_check(image: Image) -> tuple[dict[str, Any], dict[str, Any]]:
    expected = _neutral_bright_stats(image, TOOLTIP_BOTTOM_RECT)
    legacy = _neutral_bright_stats(image, TOOLTIP_LEGACY_RECT)
    bounds = expected["neutral_bright_bounds"]
    expected_pass = bool(
        expected["neutral_bright_pixels"] >= TOOLTIP_MIN_NEUTRAL_BRIGHT_PIXELS
        and bounds
        and 500 <= bounds["x"] <= 550
        and 640 <= bounds["right"] <= 680
        and 878 <= bounds["y"] <= 885
        and 892 <= bounds["bottom"] <= 899
        and abs(float(bounds["center_x"]) - 594.75) <= 15.0
    )
    legacy_pass = (
        legacy["neutral_bright_pixels"] <= TOOLTIP_MAX_LEGACY_NEUTRAL_BRIGHT_PIXELS
    )
    expected.update(
        {
            "passed": expected_pass,
            "minimum_neutral_bright_pixels": TOOLTIP_MIN_NEUTRAL_BRIGHT_PIXELS,
            "expected_capture_center_x": 594.75,
            "capture_scale": CAPTURE_SCALE,
            "logical_anchor": [240, 586, 553, 599],
        }
    )
    legacy.update(
        {
            "passed": legacy_pass,
            "maximum_neutral_bright_pixels": TOOLTIP_MAX_LEGACY_NEUTRAL_BRIGHT_PIXELS,
            "legacy_logical_anchor": [160, 467, 473, 480],
        }
    )
    return expected, legacy


def _diff_stats(
    before: Image,
    after: Image,
    rect: tuple[int, int, int, int],
    *,
    threshold: int = PANEL_DIFF_THRESHOLD,
) -> dict[str, Any]:
    if (before.width, before.height) != (after.width, after.height):
        raise ValueError("before/after dimensions differ")
    left, top, right, bottom = rect
    points: list[tuple[int, int]] = []
    total = (right - left + 1) * (bottom - top + 1)
    for y in range(top, bottom + 1):
        for x in range(left, right + 1):
            old = before.rgb_at(x, y)
            new = after.rgb_at(x, y)
            if max(abs(old[index] - new[index]) for index in range(3)) > threshold:
                points.append((x, y))
    bounds = None
    if points:
        min_x = min(point[0] for point in points)
        min_y = min(point[1] for point in points)
        max_x = max(point[0] for point in points)
        max_y = max(point[1] for point in points)
        bounds = {
            "x": min_x,
            "y": min_y,
            "right": max_x,
            "bottom": max_y,
            "width": max_x - min_x + 1,
            "height": max_y - min_y + 1,
        }
    return {
        "rect": _rect(rect),
        "threshold": threshold,
        "pixels": total,
        "changed_pixels": len(points),
        "changed_percent": round(len(points) * 100.0 / total, 3),
        "changed_bounds": bounds,
    }


def _panel_check(before: Image, after: Image) -> tuple[dict[str, Any], dict[str, Any]]:
    active = _diff_stats(before, after, PANEL_ACTIVE_RECT)
    full = _diff_stats(before, after, PANEL_FULL_RECT)
    legacy = _diff_stats(before, after, PANEL_LEGACY_ACTIVE_RECT)
    expected_bounds = active["changed_bounds"]
    panel_pass = bool(
        active["changed_percent"] >= PANEL_MIN_ACTIVE_CHANGED_PERCENT
        and full["changed_percent"] >= PANEL_MIN_FULL_CHANGED_PERCENT
        and expected_bounds
        and 908 <= expected_bounds["x"] <= 916
        and 1004 <= expected_bounds["right"] <= 1012
        and 788 <= expected_bounds["y"] <= 796
        and 884 <= expected_bounds["bottom"] <= 892
    )
    legacy_pass = legacy["changed_percent"] <= PANEL_MAX_LEGACY_CHANGED_PERCENT
    expected = {
        "passed": panel_pass,
        "active_region": active,
        "full_six_slot_region": full,
        "minimum_active_changed_percent": PANEL_MIN_ACTIVE_CHANGED_PERCENT,
        "minimum_full_changed_percent": PANEL_MIN_FULL_CHANGED_PERCENT,
        "active_visible_descriptors": [0, 3],
        "active_visible_content": ["globe", "unit_figures"],
        "logical_active_rect": [608, 528, 672, 592],
        "capture_scale": CAPTURE_SCALE,
        "scope_note": (
            "This save state visibly exercises descriptors 0 and 3. The hidden CDB "
            "summary is the separate proof for all six descriptor coordinates."
        ),
    }
    legacy.update(
        {
            "passed": legacy_pass,
            "maximum_changed_percent": PANEL_MAX_LEGACY_CHANGED_PERCENT,
            "legacy_logical_active_rect": [416, 400, 480, 464],
        }
    )
    return expected, legacy


def _hover_alignment_check(payload: dict[str, Any]) -> dict[str, Any]:
    points = payload.get("points") if isinstance(payload.get("points"), list) else []
    point = points[0] if len(points) == 1 and isinstance(points[0], dict) else {}
    requested = point.get("client")
    actual = point.get("actual_client")
    samples = point.get("samples") if isinstance(point.get("samples"), list) else []
    all_samples_exact = bool(samples) and all(
        isinstance(sample, dict)
        and sample.get("requested_client") == list(EXPECTED_HOVER_POINT)
        and sample.get("actual_client") == list(EXPECTED_HOVER_POINT)
        and sample.get("client_error") == [0, 0]
        for sample in samples
    )
    passed = (
        payload.get("client_size") == list(EXPECTED_CLIENT_SIZE)
        and requested == list(EXPECTED_HOVER_POINT)
        and actual == list(EXPECTED_HOVER_POINT)
        and point.get("client_error") == [0, 0]
        and point.get("move_method") == "setcursor"
        and payload.get("max_abs_error") == 0
        and payload.get("max_sample_abs_error") == 0
        and payload.get("path_verified") is True
        and payload.get("click_event_count") == 0
        and not point.get("clicks")
        and all_samples_exact
    )
    return {
        "passed": passed,
        "client_size": payload.get("client_size"),
        "expected_client_size": list(EXPECTED_CLIENT_SIZE),
        "requested_client": requested,
        "actual_client": actual,
        "client_error": point.get("client_error"),
        "max_abs_error": payload.get("max_abs_error"),
        "max_sample_abs_error": payload.get("max_sample_abs_error"),
        "path_verified": payload.get("path_verified"),
        "move_mode": point.get("move_mode"),
        "move_method": point.get("move_method"),
        "sample_count": len(samples),
        "all_samples_exact": all_samples_exact,
        "click_event_count": payload.get("click_event_count"),
        "proof_class": "automated_win32_setcursor_alignment",
        "manual_directinput_proof": False,
        "command_click_alignment": False,
    }


def _failed_click_attempt(payload: dict[str, Any]) -> dict[str, Any]:
    points = payload.get("points") if isinstance(payload.get("points"), list) else []
    point = points[0] if points and isinstance(points[0], dict) else {}
    requested = point.get("client")
    actual = point.get("actual_client")
    error = point.get("client_error")
    attempt_observed = bool(points and payload.get("click_event_count", 0) > 0)
    alignment_passed = bool(
        attempt_observed
        and requested == list(EXPECTED_FAILED_CLICK_POINT)
        and actual == list(EXPECTED_FAILED_CLICK_POINT)
        and error == [0, 0]
        and payload.get("path_verified") is True
        and payload.get("click_path_verified") is True
    )
    classified_failed = bool(
        attempt_observed
        and requested == list(EXPECTED_FAILED_CLICK_POINT)
        and not alignment_passed
        and payload.get("path_verified") is False
        and payload.get("click_path_verified") is False
    )
    return {
        "attempt_observed": attempt_observed,
        "requested_client": requested,
        "actual_client": actual,
        "client_error": error,
        "max_abs_error": payload.get("max_abs_error"),
        "max_sample_abs_error": payload.get("max_sample_abs_error"),
        "click_event_count": payload.get("click_event_count"),
        "path_verified": payload.get("path_verified"),
        "click_path_verified": payload.get("click_path_verified"),
        "alignment_passed": alignment_passed,
        "classified_failed_attempt": classified_failed,
        "excluded_from_pass_gate": True,
        "failure_reason": (
            "The requested screen point extended beyond the active desktop; Win32 clamped "
            "the cursor, so this attempt proves neither descriptor-5 click alignment nor a callback."
            if classified_failed
            else "The archived attempt was not the expected exact descriptor-5 failure shape."
        ),
    }


def _baseline_context(frame: Path, image: Image, sidecar: dict[str, Any]) -> dict[str, Any]:
    authenticity = _capture_authenticity(frame, sidecar)
    old_stats = _neutral_bright_stats(image, TOOLTIP_LEGACY_RECT)
    new_stats = _neutral_bright_stats(image, TOOLTIP_BOTTOM_RECT)
    passed = (
        authenticity["passed"]
        and old_stats["neutral_bright_pixels"] >= TOOLTIP_MIN_NEUTRAL_BRIGHT_PIXELS
        and new_stats["neutral_bright_pixels"] <= TOOLTIP_MAX_LEGACY_NEUTRAL_BRIGHT_PIXELS
    )
    return {
        "passed": passed,
        "frame": str(frame),
        "authenticity": authenticity,
        "legacy_tooltip_region": old_stats,
        "new_tooltip_region": new_stats,
        "scope_note": (
            "Contextual pre-fix capture showing the old tooltip placement; it is not "
            "evidence about the patched candidate by itself."
        ),
    }


def summarize(run_dir: Path, baseline_frame: Path = DEFAULT_BASELINE_FRAME) -> dict[str, Any]:
    results_path = run_dir / "results.json"
    map_frame = run_dir / "after-map-path.png"
    map_sidecar_path = run_dir / "after-map-path.png.json"
    hover_frame = run_dir / "after-hdlayout-panel-hover.png"
    hover_sidecar_path = run_dir / "after-hdlayout-panel-hover.json"
    hover_path_path = run_dir / "panel-hover-640-544.json"
    failed_click_path = run_dir / "panel-desc5-click.json"
    baseline_sidecar_path = baseline_frame.with_suffix(".json")

    required = [
        results_path,
        map_frame,
        map_sidecar_path,
        hover_frame,
        hover_sidecar_path,
        hover_path_path,
        failed_click_path,
        baseline_frame,
        baseline_sidecar_path,
    ]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise ValueError("missing required evidence: " + ", ".join(missing))

    results = _read_json(results_path)
    map_sidecar = _read_json(map_sidecar_path)
    hover_sidecar = _read_json(hover_sidecar_path)
    hover_path = _read_json(hover_path_path)
    click_attempt_payload = _read_json(failed_click_path)
    baseline_sidecar = _read_json(baseline_sidecar_path)

    map_image = read_png(map_frame)
    hover_image = read_png(hover_frame)
    baseline_image = read_png(baseline_frame)

    candidate = _candidate_check(results)
    map_authenticity = _capture_authenticity(map_frame, map_sidecar)
    hover_authenticity = _capture_authenticity(
        hover_frame,
        hover_sidecar,
        expected_target_hwnd=str(map_sidecar.get("TargetHwnd", "")),
    )
    gameplay = _gameplay_route_check(results, map_authenticity["actual_sha256"])
    tooltip_bottom, tooltip_legacy = _tooltip_check(map_image)
    panel_expected, panel_legacy = _panel_check(map_image, hover_image)
    hover_alignment = _hover_alignment_check(hover_path)
    failed_click = _failed_click_attempt(click_attempt_payload)
    baseline = _baseline_context(baseline_frame, baseline_image, baseline_sidecar)

    tear_report = capture_tear_check.build_report([map_frame, hover_frame], None)
    tear_check = {
        "passed": tear_report["clean"],
        "advisory": True,
        "verdict": tear_report["verdict"],
        "clean": tear_report["clean"],
        "frame_count": tear_report["frame_count"],
        "frames": tear_report["frames"],
        "note": tear_report["note"],
    }
    process_liveness = {
        "passed": results.get("ProcessExitedBeforeCleanup") is False
        and results.get("ExitCode") is None,
        "process_exited_before_cleanup": results.get("ProcessExitedBeforeCleanup"),
        "exit_code": results.get("ExitCode"),
        "scope_note": "The candidate remained alive until harness cleanup; this is not a soak test.",
    }

    checks = {
        "candidate_identity": candidate,
        "map_capture_authenticity": map_authenticity,
        "hover_capture_authenticity": hover_authenticity,
        "gameplay_route": gameplay,
        "tooltip_bottom_center_visible": tooltip_bottom,
        "tooltip_legacy_location_absent": tooltip_legacy,
        "pre_fix_baseline_context": baseline,
        "panel_right_bottom_visible": panel_expected,
        "panel_legacy_location_unchanged": panel_legacy,
        "automated_hover_alignment": hover_alignment,
        "capture_tear_advisory_clean": tear_check,
        "process_liveness_until_cleanup": process_liveness,
    }
    passed = all(bool(check.get("passed")) for check in checks.values())

    return {
        "generated_at": _now(),
        "runtime_policy": (
            "repo-only PNG/JSON parser; does not launch Clash95, CDB, wrappers, "
            "PowerShell, input automation, or visible windows"
        ),
        "run_dir": str(run_dir),
        "passed": passed,
        "evidence_class": "approved_visible_automated_layout_composition",
        "pass_scope": (
            "Authentic visible 800x600 composition of the relocated terrain tooltip and "
            "active command-panel sprites, with exact automated Win32 hover placement."
        ),
        "candidate_sha256": candidate["recorded_sha256"],
        "checks": checks,
        "frames": {
            "map": map_authenticity,
            "panel_hover": hover_authenticity,
            "pre_fix_baseline": baseline["authenticity"],
        },
        "tooltip": {
            "bottom_center": tooltip_bottom,
            "legacy_location": tooltip_legacy,
            "pre_fix_baseline": baseline,
        },
        "panel": {
            "right_bottom": panel_expected,
            "legacy_location": panel_legacy,
        },
        "automated_hover_alignment": hover_alignment,
        "failed_panel_click_attempt": failed_click,
        "command_click_alignment": False,
        "panel_click_callback_proof": False,
        "manual_directinput_proof": False,
        "stable_stage_promotion_ready": False,
        "promotion_ready": False,
        "limitations": [
            "The descriptor-5 click attempt was clamped by the desktop edge and failed alignment.",
            "SetCursor/GetCursorPos agreement is automated Win32 evidence, not manual DirectInput proof.",
            "Only active descriptors 0 and 3 are visibly populated in this save state; hidden CDB evidence covers all six coordinates.",
            "The tear result is an advisory content/ROI heuristic, not proof that a desktop grab is tear-free.",
            "This validation-only candidate is not the protected stable/default stage and this report does not promote it.",
            "A short/long soak, castle/battle continuity, and release validation remain separate gates.",
        ],
    }


def _status(value: bool) -> str:
    return "PASS" if value else "FAIL"


def write_markdown(path: Path, summary: dict[str, Any]) -> None:
    click = summary["failed_panel_click_attempt"]
    tooltip = summary["tooltip"]["bottom_center"]
    panel = summary["panel"]["right_bottom"]
    lines = [
        "# HD Layout Visible Evidence Summary",
        "",
        f"- Generated: `{summary['generated_at']}`",
        f"- Run: `{summary['run_dir']}`",
        f"- Candidate SHA-256: `{summary['candidate_sha256']}`",
        f"- Result: `{_status(summary['passed'])}`",
        f"- Evidence class: `{summary['evidence_class']}`",
        f"- Pass scope: {summary['pass_scope']}",
        "- Manual DirectInput proof: `false`",
        "- Command-click alignment: `false`",
        "- Panel callback proof: `false`",
        "- Stable-stage promotion ready: `false`",
        "- Promotion ready: `false`",
        "",
        "## Checks",
        "",
        "| Check | Result |",
        "| --- | --- |",
    ]
    for name, check in summary["checks"].items():
        lines.append(f"| `{name}` | `{_status(bool(check['passed']))}` |")
    lines.extend(
        [
            "",
            "## Measured Layout",
            "",
            f"- Tooltip neutral-bright pixels: `{tooltip['neutral_bright_pixels']}`; bounds: `{tooltip['neutral_bright_bounds']}`.",
            f"- Active panel diff: `{panel['active_region']['changed_percent']}%`; bounds: `{panel['active_region']['changed_bounds']}`.",
            f"- Full six-slot panel-region diff: `{panel['full_six_slot_region']['changed_percent']}%`.",
            f"- Automated hover point: requested `{summary['automated_hover_alignment']['requested_client']}`, actual `{summary['automated_hover_alignment']['actual_client']}`, error `{summary['automated_hover_alignment']['client_error']}`.",
            "",
            "## Failed Panel Click Attempt",
            "",
            f"- Attempt observed: `{str(click['attempt_observed']).lower()}`",
            f"- Requested client point: `{click['requested_client']}`",
            f"- Actual client point: `{click['actual_client']}`",
            f"- Client error: `{click['client_error']}`",
            f"- Path verified: `{str(click['path_verified']).lower()}`",
            f"- Click path verified: `{str(click['click_path_verified']).lower()}`",
            f"- Alignment passed: `{str(click['alignment_passed']).lower()}`",
            f"- Classification: {click['failure_reason']}",
            "",
            "## Limitations",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in summary["limitations"])
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def print_summary(summary: dict[str, Any]) -> None:
    print(f"run: {summary['run_dir']}")
    print(f"candidate: {summary['candidate_sha256']}")
    print(f"result: {_status(summary['passed'])}")
    for name, check in summary["checks"].items():
        print(f"{name}: {_status(bool(check['passed']))}")
    click = summary["failed_panel_click_attempt"]
    print(
        "failed panel click: requested={requested} actual={actual} error={error} "
        "alignment_passed={passed}".format(
            requested=click["requested_client"],
            actual=click["actual_client"],
            error=click["client_error"],
            passed=click["alignment_passed"],
        )
    )
    print("manual_directinput_proof: false")
    print("promotion_ready: false")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", nargs="?", type=Path, default=DEFAULT_RUN_DIR)
    parser.add_argument("--baseline-frame", type=Path, default=DEFAULT_BASELINE_FRAME)
    parser.add_argument("--write-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--write-markdown", "--write-md", dest="write_markdown", type=Path, default=DEFAULT_MD)
    parser.add_argument("--require-pass", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        summary = summarize(args.run_dir, args.baseline_frame)
        print_summary(summary)
        if args.write_json:
            args.write_json.parent.mkdir(parents=True, exist_ok=True)
            args.write_json.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        if args.write_markdown:
            write_markdown(args.write_markdown, summary)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"input/output error: {exc}", file=sys.stderr)
        return 2
    return 2 if args.require_pass and not summary["passed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
