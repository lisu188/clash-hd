#!/usr/bin/env python3
"""Audit first-mission HD frames for stripe glitches and black patches.

This is repo-only image analysis. It reads archived PNG evidence and reports
whether the current first-mission validation frames look playable, without
launching Clash95, CDB, wrappers, PowerShell, or visible windows.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from capture_geometry import Image, luminance, read_png


DEFAULT_JSON = Path("captures/current/first-mission-visual-audit-current.json")
DEFAULT_MD = Path("captures/current/first-mission-visual-audit-current.md")
RUNTIME_POLICY = (
    "repo-only PNG audit; does not launch Clash95, CDB, wrappers, PowerShell, "
    "or visible windows"
)
GUARD_POLICY = (
    "first-mission frames must keep the play area rendered, avoid horizontal or "
    "vertical stripe signatures, and expose remaining large black UI patches as "
    "non-playable blockers instead of hiding them behind route success"
)

DEFAULT_FRAMES = [
    {
        "id": "baseline_selection",
        "role": "baseline first-mission selected-unit route",
        "path": "captures/archive/cdb-surface-dump-20260527-092117/surface.png",
        "primary": False,
    },
    {
        "id": "pre_redraw_action_bar",
        "role": "pre-redraw selected-unit action-bar recovery",
        "path": "captures/archive/cdb-surface-dump-20260527-100641/surface.png",
        "primary": False,
    },
    {
        "id": "tooltip_owner_probe",
        "role": "bottom-tooltip owner diagnostic",
        "path": "captures/archive/cdb-surface-dump-20260527-101402/surface.png",
        "primary": False,
    },
    {
        "id": "hover_selection_probe",
        "role": "hover/selection diagnostic",
        "path": "captures/archive/cdb-surface-dump-20260527-101727/surface.png",
        "primary": False,
    },
    {
        "id": "combined_tooltip_action_bar",
        "role": "combined tooltip/action-bar diagnostic before post-redraw fix",
        "path": "captures/archive/cdb-surface-dump-20260527-111658/surface.png",
        "primary": False,
    },
    {
        "id": "post_redraw_action_bar",
        "role": "legacy lower-map post-redraw action-bar frame",
        "path": "captures/archive/cdb-surface-dump-20260527-114559/surface.png",
        "primary": False,
    },
    {
        "id": "post_redraw_action_bar_bottom_gauge",
        "role": "current first-mission bottom action-bar and gauge frame",
        "path": "captures/archive/cdb-surface-dump-20260616-133855/surface.png",
        "primary": False,
    },
    {
        "id": "combined_natural_unit",
        "role": "current combined-stage natural selected-unit frame",
        "path": "captures/archive/cdb-surface-dump-20260616-135148/surface.png",
        "primary": False,
    },
    {
        "id": "combined_minimap_surface_probe",
        "role": "current combined-stage selected-unit frame with minimap backing samples",
        "path": "captures/archive/cdb-surface-dump-20260616-141733/surface.png",
        "primary": False,
    },
    {
        "id": "bottom_edge_panel_only",
        "role": "current bottom-edge selected-unit panel frame",
        "path": "captures/archive/cdb-surface-dump-20260616-153155/surface.png",
        "primary": False,
    },
    {
        "id": "centered_bottom_edge_panel",
        "role": "current centered bottom-edge selected-unit panel frame",
        "path": "captures/archive/cdb-surface-dump-20260616-153751/surface.png",
        "primary": True,
    },
]

REGIONS: dict[str, tuple[int, int, int, int]] = {
    "play_area": (32, 16, 585, 527),
    "selected_action_bar": (215, 580, 585, 599),
    "legacy_middle_action_bar": (150, 455, 520, 500),
    "bottom_tooltip_strip": (32, 528, 585, 599),
    "right_below_minimap": (586, 230, 799, 599),
    "bottom_right_panel": (586, 528, 799, 599),
    "minimap_interior": (594, 24, 793, 220),
}


def status_text(passed: bool) -> str:
    return "PASS" if passed else "FAIL"


def average_diff(a: tuple[int, int, int], b: tuple[int, int, int]) -> float:
    return sum(abs(int(a[index]) - int(b[index])) for index in range(3)) / 3.0


def clamp_rect(image: Image, rect: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    left, top, right, bottom = rect
    return (
        max(0, min(image.width - 1, left)),
        max(0, min(image.height - 1, top)),
        max(0, min(image.width - 1, right)),
        max(0, min(image.height - 1, bottom)),
    )


def region_stats(
    image: Image,
    rect: tuple[int, int, int, int],
    *,
    threshold: int,
    bright_threshold: float,
) -> dict[str, Any]:
    left, top, right, bottom = clamp_rect(image, rect)
    total = 0
    nonblack = 0
    bright = 0
    luma_sum = 0.0
    min_luma = 255.0
    max_luma = 0.0
    quantized_colors: set[tuple[int, int, int]] = set()
    for y in range(top, bottom + 1):
        for x in range(left, right + 1):
            rgb = image.rgb_at(x, y)
            luma = luminance(rgb)
            total += 1
            luma_sum += luma
            min_luma = min(min_luma, luma)
            max_luma = max(max_luma, luma)
            if max(rgb) > threshold:
                nonblack += 1
            if luma >= bright_threshold:
                bright += 1
            quantized_colors.add((rgb[0] >> 4, rgb[1] >> 4, rgb[2] >> 4))

    nonblack_percent = round(nonblack * 100.0 / total, 3) if total else 0.0
    black_percent = round(100.0 - nonblack_percent, 3)
    return {
        "rect": [left, top, right, bottom],
        "pixels": total,
        "nonblack_percent": nonblack_percent,
        "black_percent": black_percent,
        "bright_percent": round(bright * 100.0 / total, 3) if total else 0.0,
        "mean_luma": round(luma_sum / total, 3) if total else 0.0,
        "min_luma": round(min_luma, 3) if total else 0.0,
        "max_luma": round(max_luma, 3) if total else 0.0,
        "quantized_color_bins": len(quantized_colors),
    }


def stripe_metrics(
    image: Image,
    rect: tuple[int, int, int, int],
    *,
    diff_threshold: float,
    max_high_percent: float,
    max_excess_percent: float,
) -> dict[str, Any]:
    left, top, right, bottom = clamp_rect(image, rect)
    x_diffs: list[float] = []
    for x in range(left, right):
        total = 0.0
        samples = 0
        for y in range(top, bottom + 1):
            total += average_diff(image.rgb_at(x, y), image.rgb_at(x + 1, y))
            samples += 1
        x_diffs.append(total / max(1, samples))

    y_diffs: list[float] = []
    for y in range(top, bottom):
        total = 0.0
        samples = 0
        for x in range(left, right + 1):
            total += average_diff(image.rgb_at(x, y), image.rgb_at(x, y + 1))
            samples += 1
        y_diffs.append(total / max(1, samples))

    vertical_high_percent = round(
        sum(1 for value in x_diffs if value >= diff_threshold) * 100.0 / max(1, len(x_diffs)),
        3,
    )
    horizontal_high_percent = round(
        sum(1 for value in y_diffs if value >= diff_threshold) * 100.0 / max(1, len(y_diffs)),
        3,
    )
    vertical_mean = sum(x_diffs) / max(1, len(x_diffs))
    horizontal_mean = sum(y_diffs) / max(1, len(y_diffs))
    vertical_excess = round(max(0.0, vertical_high_percent - horizontal_high_percent), 3)
    horizontal_excess = round(max(0.0, horizontal_high_percent - vertical_high_percent), 3)
    vertical_stripe = (
        vertical_high_percent > max_high_percent
        and vertical_excess > max_excess_percent
    )
    horizontal_stripe = (
        horizontal_high_percent > max_high_percent
        and horizontal_excess > max_excess_percent
    )
    return {
        "rect": [left, top, right, bottom],
        "diff_threshold": diff_threshold,
        "max_high_percent": max_high_percent,
        "max_excess_percent": max_excess_percent,
        "vertical_high_percent": vertical_high_percent,
        "horizontal_high_percent": horizontal_high_percent,
        "vertical_excess_percent": vertical_excess,
        "horizontal_excess_percent": horizontal_excess,
        "vertical_mean_diff": round(vertical_mean, 3),
        "horizontal_mean_diff": round(horizontal_mean, 3),
        "mean_diff_ratio_x_over_y": round(vertical_mean / max(0.001, horizontal_mean), 3),
        "vertical_stripe_detected": vertical_stripe,
        "horizontal_stripe_detected": horizontal_stripe,
        "passed": not (vertical_stripe or horizontal_stripe),
    }


def analyze_frame(
    frame: dict[str, Any],
    *,
    threshold: int,
    bright_threshold: float,
    diff_threshold: float,
    max_stripe_high_percent: float,
    max_stripe_excess_percent: float,
) -> dict[str, Any]:
    path = Path(frame["path"])
    failures: list[str] = []
    if not path.exists():
        return {
            **frame,
            "path": str(path),
            "present": False,
            "passed": False,
            "failures": [f"missing frame PNG: {path}"],
        }

    image = read_png(path)
    regions = {
        name: region_stats(
            image,
            rect,
            threshold=threshold,
            bright_threshold=bright_threshold,
        )
        for name, rect in REGIONS.items()
    }
    stripes = stripe_metrics(
        image,
        REGIONS["play_area"],
        diff_threshold=diff_threshold,
        max_high_percent=max_stripe_high_percent,
        max_excess_percent=max_stripe_excess_percent,
    )

    play_area_rendered = regions["play_area"]["nonblack_percent"] >= 90.0
    action_bar_visible = (
        regions["selected_action_bar"]["nonblack_percent"] >= 80.0
        and regions["selected_action_bar"]["mean_luma"] <= 98.0
    )
    legacy_middle_action_bar_visible = (
        regions["legacy_middle_action_bar"]["nonblack_percent"] >= 80.0
        and regions["legacy_middle_action_bar"]["mean_luma"] <= 98.0
    )
    black_patch_regions = [
        name
        for name in ("right_below_minimap", "bottom_right_panel", "minimap_interior")
        if regions[name]["black_percent"] >= 70.0
    ]

    if not play_area_rendered:
        failures.append("play area is mostly black or missing")
    if frame.get("primary") and not action_bar_visible:
        failures.append("primary frame selected-unit action bar is not visible")
    if not stripes["passed"]:
        failures.append("stripe signature detected in play area")
    if frame.get("primary") and legacy_middle_action_bar_visible and not action_bar_visible:
        failures.append("selected-unit action bar is still in the legacy middle placement")

    frame_clean_for_playability = bool(
        play_area_rendered
        and action_bar_visible
        and stripes["passed"]
        and not black_patch_regions
    )
    status = (
        "visual_clean_candidate"
        if frame_clean_for_playability
        else "black_patch_or_diagnostic_frame"
    )

    return {
        **frame,
        "path": str(path),
        "present": True,
        "image": {"width": image.width, "height": image.height},
        "status": status,
        "passed": not failures,
        "frame_clean_for_playability": frame_clean_for_playability,
        "play_area_rendered": play_area_rendered,
        "selected_action_bar_visible": action_bar_visible,
        "legacy_middle_action_bar_visible": legacy_middle_action_bar_visible,
        "black_patch_regions": black_patch_regions,
        "regions": regions,
        "stripe_metrics": stripes,
        "failures": failures,
    }


def primary_black_patch_details(primary: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not primary:
        return []
    regions = primary.get("regions") or {}
    details: list[dict[str, Any]] = []
    for name in primary.get("black_patch_regions") or []:
        stats = regions.get(name) or {}
        details.append(
            {
                "region": name,
                "rect": stats.get("rect"),
                "black_percent": stats.get("black_percent"),
                "nonblack_percent": stats.get("nonblack_percent"),
                "mean_luma": stats.get("mean_luma"),
                "quantized_color_bins": stats.get("quantized_color_bins"),
            }
        )
    return details


def next_probe_for_primary(primary: dict[str, Any] | None) -> str:
    if not primary:
        return "restore a primary first-mission frame definition and rerun the visual audit"
    black_regions = primary.get("black_patch_regions") or []
    if black_regions:
        return (
            "inspect the primary frame's right-side/minimap/bottom-panel compose or present path "
            "for black patch regions, then rerun first_mission_visual_audit.py"
        )
    if not primary.get("selected_action_bar_visible"):
        return "restore the bottom selected-unit action bar and rerun first_mission_visual_audit.py"
    if primary.get("legacy_middle_action_bar_visible"):
        return "remove the legacy middle selected-unit action bar placement and rerun first_mission_visual_audit.py"
    if not (primary.get("stripe_metrics") or {}).get("passed", True):
        return "inspect palette/stripe frame output and rerun first_mission_visual_audit.py"
    return "rerun first_mission_visual_audit.py after the next first-mission visual evidence refresh"


def build_report(frames: list[dict[str, Any]], args: argparse.Namespace) -> dict[str, Any]:
    analyzed = [
        analyze_frame(
            frame,
            threshold=args.threshold,
            bright_threshold=args.bright_threshold,
            diff_threshold=args.diff_threshold,
            max_stripe_high_percent=args.max_stripe_high_percent,
            max_stripe_excess_percent=args.max_stripe_excess_percent,
        )
        for frame in frames
    ]
    primary_frames = [frame for frame in analyzed if frame.get("primary")]
    primary = primary_frames[0] if primary_frames else None
    failures: list[str] = []
    if primary is None:
        failures.append("missing primary first-mission frame definition")
    elif not primary.get("frame_clean_for_playability"):
        primary_reasons = list(primary.get("failures") or [])
        primary_reasons.extend(
            f"black patch: {name}" for name in primary.get("black_patch_regions") or []
        )
        failures.append(
            "primary first-mission frame is not visually clean for playability: "
            + ", ".join(primary_reasons or ["unknown"])
        )
    stripe_failures = [
        frame["id"]
        for frame in analyzed
        if not (frame.get("stripe_metrics") or {}).get("passed", True)
    ]
    if stripe_failures:
        failures.append(f"stripe signatures detected: {stripe_failures}")

    diagnostic_black_frames = [
        frame["id"]
        for frame in analyzed
        if frame.get("present") and not frame.get("play_area_rendered")
    ]
    if primary and primary.get("legacy_middle_action_bar_visible") and not primary.get(
        "selected_action_bar_visible"
    ):
        current_status = "legacy_middle_action_bar_detected"
    elif primary and primary.get("selected_action_bar_visible") and primary.get("play_area_rendered"):
        current_status = "selected_unit_action_bar_on_bottom_but_black_ui_patches_remain"
    else:
        current_status = "first_mission_visual_playability_not_proven"
    black_patch_details = primary_black_patch_details(primary)
    return {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "passed": not failures,
        "runtime_policy": RUNTIME_POLICY,
        "guard_policy": GUARD_POLICY,
        "current_status": current_status,
        "first_mission_visual_clean": bool(primary and primary.get("frame_clean_for_playability")),
        "primary_frame": primary.get("id") if primary else None,
        "primary_frame_path": primary.get("path") if primary else None,
        "next_probe": next_probe_for_primary(primary),
        "summary": {
            "frame_count": len(analyzed),
            "stripe_failure_frames": stripe_failures,
            "diagnostic_black_frames": diagnostic_black_frames,
            "primary_black_patch_regions": primary.get("black_patch_regions") if primary else [],
            "primary_black_patch_details": black_patch_details,
            "primary_frame_path": primary.get("path") if primary else None,
            "next_probe": next_probe_for_primary(primary),
            "primary_play_area_nonblack": (
                ((primary.get("regions") or {}).get("play_area") or {}).get("nonblack_percent")
                if primary
                else None
            ),
            "primary_selected_action_bar_nonblack": (
                ((primary.get("regions") or {}).get("selected_action_bar") or {}).get("nonblack_percent")
                if primary
                else None
            ),
            "primary_selected_action_bar_mean_luma": (
                ((primary.get("regions") or {}).get("selected_action_bar") or {}).get("mean_luma")
                if primary
                else None
            ),
            "primary_selected_action_bar_visible": (
                primary.get("selected_action_bar_visible") if primary else None
            ),
            "primary_legacy_middle_action_bar_nonblack": (
                ((primary.get("regions") or {}).get("legacy_middle_action_bar") or {}).get(
                    "nonblack_percent"
                )
                if primary
                else None
            ),
            "primary_legacy_middle_action_bar_mean_luma": (
                ((primary.get("regions") or {}).get("legacy_middle_action_bar") or {}).get(
                    "mean_luma"
                )
                if primary
                else None
            ),
            "primary_legacy_middle_action_bar_visible": (
                primary.get("legacy_middle_action_bar_visible") if primary else None
            ),
        },
        "frames": analyzed,
        "failures": failures,
    }


def write_json(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


def write_markdown(path: Path, report: dict[str, Any]) -> None:
    summary = report["summary"]
    lines = [
        "# First Mission Visual Audit",
        "",
        f"- Overall: {status_text(bool(report['passed']))}",
        f"- Generated: `{report['generated_at']}`",
        f"- Runtime policy: {report['runtime_policy']}",
        f"- Guard policy: {report['guard_policy']}",
        f"- Current status: `{report['current_status']}`",
        f"- First mission visual clean: `{report['first_mission_visual_clean']}`",
        f"- Primary frame: `{report['primary_frame']}`",
        f"- Primary frame path: `{report.get('primary_frame_path')}`",
        f"- Next probe: {report.get('next_probe')}",
        f"- Primary play area nonblack: `{summary.get('primary_play_area_nonblack')}`%",
        f"- Primary selected action bar nonblack: `{summary.get('primary_selected_action_bar_nonblack')}`%",
        f"- Primary selected action bar mean luma: `{summary.get('primary_selected_action_bar_mean_luma')}`",
        f"- Primary selected action bar visible: `{summary.get('primary_selected_action_bar_visible')}`",
        f"- Primary legacy middle action bar nonblack: `{summary.get('primary_legacy_middle_action_bar_nonblack')}`%",
        f"- Primary legacy middle action bar mean luma: `{summary.get('primary_legacy_middle_action_bar_mean_luma')}`",
        f"- Primary legacy middle action bar visible: `{summary.get('primary_legacy_middle_action_bar_visible')}`",
        f"- Primary black patch regions: `{summary.get('primary_black_patch_regions')}`",
        f"- Stripe failure frames: `{summary.get('stripe_failure_frames')}`",
        f"- Diagnostic black frames: `{summary.get('diagnostic_black_frames')}`",
        "",
    ]
    black_details = summary.get("primary_black_patch_details") or []
    if black_details:
        lines.extend(["## Primary Black Patch Details", ""])
        for detail in black_details:
            lines.append(
                f"- `{detail.get('region')}` rect=`{detail.get('rect')}` "
                f"black=`{detail.get('black_percent')}`% "
                f"nonblack=`{detail.get('nonblack_percent')}`% "
                f"mean_luma=`{detail.get('mean_luma')}` "
                f"color_bins=`{detail.get('quantized_color_bins')}`"
            )
        lines.append("")
    lines.extend(
        [
        "## Frames",
        "",
        ]
    )
    for frame in report["frames"]:
        regions = frame.get("regions") or {}
        stripes = frame.get("stripe_metrics") or {}
        lines.extend(
            [
                f"### {frame['id']}",
                "",
                f"- Role: {frame.get('role')}",
                f"- Path: `{frame.get('path')}`",
                f"- Status: `{frame.get('status')}`",
                f"- Frame clean for playability: `{frame.get('frame_clean_for_playability')}`",
                f"- Play area nonblack: `{(regions.get('play_area') or {}).get('nonblack_percent')}`%",
                f"- Expected bottom action bar nonblack: `{(regions.get('selected_action_bar') or {}).get('nonblack_percent')}`%",
                f"- Expected bottom action bar mean luma: `{(regions.get('selected_action_bar') or {}).get('mean_luma')}`",
                f"- Expected bottom action bar visible: `{frame.get('selected_action_bar_visible')}`",
                f"- Legacy middle action bar nonblack: `{(regions.get('legacy_middle_action_bar') or {}).get('nonblack_percent')}`%",
                f"- Legacy middle action bar mean luma: `{(regions.get('legacy_middle_action_bar') or {}).get('mean_luma')}`",
                f"- Legacy middle action bar visible: `{frame.get('legacy_middle_action_bar_visible')}`",
                f"- Bottom tooltip black: `{(regions.get('bottom_tooltip_strip') or {}).get('black_percent')}`%",
                f"- Right below minimap black: `{(regions.get('right_below_minimap') or {}).get('black_percent')}`%",
                f"- Minimap interior black: `{(regions.get('minimap_interior') or {}).get('black_percent')}`%",
                f"- Stripe pass: `{stripes.get('passed')}` horizontal_high=`{stripes.get('horizontal_high_percent')}`% vertical_high=`{stripes.get('vertical_high_percent')}`%",
                f"- Black patch regions: `{frame.get('black_patch_regions')}`",
                "",
            ]
        )
    if report["failures"]:
        lines.extend(["## Failures", ""])
        lines.extend(f"- {failure}" for failure in report["failures"])
        lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_frame(value: str) -> dict[str, Any]:
    parts = value.split(":", 3)
    if len(parts) != 4:
        raise argparse.ArgumentTypeError("frame must be id:primary(true|false):role:path")
    item_id, primary_text, role, path = parts
    return {
        "id": item_id,
        "primary": primary_text.strip().lower() in {"1", "true", "yes"},
        "role": role,
        "path": path,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frame", action="append", type=parse_frame)
    parser.add_argument("--threshold", type=int, default=12)
    parser.add_argument("--bright-threshold", type=float, default=96.0)
    parser.add_argument("--diff-threshold", type=float, default=40.0)
    parser.add_argument("--max-stripe-high-percent", type=float, default=12.0)
    parser.add_argument("--max-stripe-excess-percent", type=float, default=8.0)
    parser.add_argument("--write-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--write-markdown", type=Path, default=DEFAULT_MD)
    parser.add_argument("--require-pass", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = build_report(args.frame or DEFAULT_FRAMES, args)
    if args.write_json:
        write_json(args.write_json, report)
    if args.write_markdown:
        write_markdown(args.write_markdown, report)
    print(f"overall: {status_text(bool(report['passed']))}")
    print(f"current-status: {report['current_status']}")
    print(f"first-mission-visual-clean: {report['first_mission_visual_clean']}")
    print(f"primary-black-patch-regions: {report['summary']['primary_black_patch_regions']}")
    print(f"next-probe: {report.get('next_probe')}")
    print(f"stripe-failure-frames: {report['summary']['stripe_failure_frames']}")
    print(f"diagnostic-black-frames: {report['summary']['diagnostic_black_frames']}")
    if report["failures"]:
        print("failures:")
        for failure in report["failures"]:
            print(f"  - {failure}")
    if args.require_pass and not report["passed"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
