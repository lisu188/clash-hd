#!/usr/bin/env python3
"""Combine first-mission unit-selection action-bar and native tooltip evidence."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import border_tooltip_summary
import hover_selection_ui_summary
import unit_selection_action_bar_summary
from capture_geometry import read_png


TOOLTIP_STRIP = (32, 528, 585, 599)
ACTION_BAR_REGION = (150, 455, 520, 500)
REQUIRED_HOVER_MODES = {
    "selected_unit_hover",
    "bottom_tooltip_hover",
    "action_grid_hover",
    "action_box_hover",
    "safe_center_hold",
}


def logical_rect_to_pixels(
    image_width: int,
    image_height: int,
    rect: tuple[int, int, int, int],
    logical_width: int,
    logical_height: int,
) -> tuple[int, int, int, int]:
    left, top, right, bottom = rect
    scale_x = image_width / logical_width
    scale_y = image_height / logical_height
    return (
        max(0, min(image_width - 1, int(left * scale_x))),
        max(0, min(image_height - 1, int(top * scale_y))),
        max(0, min(image_width - 1, int((right + 1) * scale_x) - 1)),
        max(0, min(image_height - 1, int((bottom + 1) * scale_y) - 1)),
    )


def analyze_region(
    png: Path,
    rect: tuple[int, int, int, int],
    args: argparse.Namespace,
) -> dict[str, Any]:
    image = read_png(png)
    x0, y0, x1, y1 = logical_rect_to_pixels(
        image.width,
        image.height,
        rect,
        args.logical_width,
        args.logical_height,
    )
    total = 0
    nonblack = 0
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            total += 1
            if max(image.rgb_at(x, y)) > args.threshold:
                nonblack += 1
    black = total - nonblack
    return {
        "logical_rect": list(rect),
        "image_rect": [x0, y0, x1, y1],
        "nonblack_percent": round(nonblack * 100.0 / total, 3) if total else 0.0,
        "black_percent": round(black * 100.0 / total, 3) if total else 0.0,
    }


def summarize(log: Path, png: Path | None, args: argparse.Namespace) -> dict[str, Any]:
    unit = unit_selection_action_bar_summary.parse_log(log, expected_slot=args.expected_slot)
    hover = hover_selection_ui_summary.parse_log(log)
    border_args = argparse.Namespace(
        logical_width=args.logical_width,
        logical_height=args.logical_height,
        threshold=args.threshold,
    )
    border = border_tooltip_summary.summarize(log, png, border_args)

    hover_modes = [row.get("mode", "") for row in hover["force_states"]]
    hover_mode_set = set(hover_modes)
    missing_hover_modes = sorted(REQUIRED_HOVER_MODES - hover_mode_set)
    hover_sequence_observed = not missing_hover_modes

    tooltip_present_regions = border["present_by_region"]
    tooltip_null_regions = border["null_present_by_region"]
    tooltip_owner_row_count = (
        len(hover["entries"])
        + border["row_counts"].get("entries", 0)
        + border["row_counts"].get("text", 0)
        + tooltip_present_regions.get("bottom_tooltip", 0)
    )
    tooltip_owner_evidence = tooltip_owner_row_count > 0

    png_regions = None
    action_bar_visible = None
    tooltip_strip_nonblack_visible = None
    tooltip_strip_visible = None
    if png:
        png_regions = {
            "selected_unit_action_bar": analyze_region(png, ACTION_BAR_REGION, args),
            "bottom_tooltip_strip": analyze_region(png, TOOLTIP_STRIP, args),
        }
        action_bar_visible = (
            png_regions["selected_unit_action_bar"]["nonblack_percent"]
            >= args.action_bar_min_nonblack
        )
        tooltip_strip_nonblack_visible = (
            png_regions["bottom_tooltip_strip"]["nonblack_percent"]
            >= args.tooltip_min_nonblack
        )
        tooltip_strip_visible = tooltip_owner_evidence and tooltip_strip_nonblack_visible

    unit_basic_pass = (
        unit["load_slot_match"]
        and unit["ready"]
        and unit["selection_success"]
        and unit["unit_info_route"]
        and unit["post_redraw_route"]
        and unit["present_helper"]
        and unit["action_update"]
    )
    av_count = unit["av_count"] + hover["av_count"] + len(border["av_rows"])
    no_av = av_count == 0
    action_bar_regression_pass = unit["post_redraw_route"] and (
        True if action_bar_visible is None else action_bar_visible
    )
    evidence_pass = unit_basic_pass and hover_sequence_observed and no_av and action_bar_regression_pass
    tooltip_recovered = tooltip_owner_evidence and tooltip_strip_visible is True
    overall_pass = evidence_pass and tooltip_recovered

    if not evidence_pass:
        decision = "BASIC_EVIDENCE_FAILED"
    elif not tooltip_owner_evidence:
        decision = "NO_PATCH_OWNER_NOT_REACHED"
    elif not tooltip_recovered:
        decision = "OWNER_REACHED_PATCH_ALLOWED"
    else:
        decision = "TOOLTIP_RECOVERED"

    classification: list[str] = []
    if unit_basic_pass:
        classification.append("first-mission selection and post-redraw 00406980 action-bar route passed")
    else:
        classification.append("first-mission selection/post-redraw action-bar route failed one or more gates")
    if hover_sequence_observed:
        classification.append("all five tooltip/action hover states were forced")
    else:
        classification.append("tooltip/action hover sequence was incomplete")
    if tooltip_owner_evidence:
        classification.append("native tooltip/status owner evidence was observed")
    else:
        classification.append("native tooltip/status owner evidence was not observed")
    if action_bar_visible is True:
        classification.append("selected-unit action-bar visual regression gate passed")
    elif action_bar_visible is False:
        classification.append("selected-unit action-bar visual regression gate failed")
    if tooltip_strip_nonblack_visible is True and tooltip_owner_evidence:
        classification.append("native bottom tooltip strip has owner-backed nonblack coverage")
    elif tooltip_strip_nonblack_visible is True:
        classification.append("native bottom tooltip strip has nonblack pixels without owner evidence")
    elif tooltip_strip_nonblack_visible is False:
        classification.append("native bottom tooltip strip remains visually blank")
    if no_av:
        classification.append("no AV rows were observed")
    else:
        classification.append("AV rows were observed")

    return {
        "log": str(log),
        "png": str(png) if png else None,
        "expected_slot": args.expected_slot,
        "unit": unit,
        "hover": hover,
        "border": border,
        "hover_modes": hover_modes,
        "missing_hover_modes": missing_hover_modes,
        "hover_sequence_observed": hover_sequence_observed,
        "tooltip_owner_row_count": tooltip_owner_row_count,
        "tooltip_owner_evidence": tooltip_owner_evidence,
        "tooltip_present_by_region": tooltip_present_regions,
        "tooltip_null_present_by_region": tooltip_null_regions,
        "png_regions": png_regions,
        "action_bar_visible": action_bar_visible,
        "tooltip_strip_nonblack_visible": tooltip_strip_nonblack_visible,
        "tooltip_strip_visible": tooltip_strip_visible,
        "unit_basic_pass": unit_basic_pass,
        "no_av": no_av,
        "av_count": av_count,
        "evidence_pass": evidence_pass,
        "tooltip_recovered": tooltip_recovered,
        "overall_pass": overall_pass,
        "decision": decision,
        "classification": classification,
    }


def write_markdown(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# Unit Selection Tooltip And Action Bar Summary",
        "",
        f"- Log: `{summary['log']}`",
        f"- PNG: `{summary['png']}`",
        f"- Expected slot: `{summary['expected_slot']}`",
        f"- Evidence pass: `{summary['evidence_pass']}`",
        f"- Overall tooltip recovered: `{summary['overall_pass']}`",
        f"- Decision: `{summary['decision']}`",
        f"- Unit route pass: `{summary['unit_basic_pass']}`",
        f"- Post-redraw action-bar route: `{summary['unit']['post_redraw_route']}`",
        f"- Hover sequence observed: `{summary['hover_sequence_observed']}`",
        f"- Missing hover modes: `{summary['missing_hover_modes']}`",
        f"- Tooltip owner evidence: `{summary['tooltip_owner_evidence']}`",
        f"- Tooltip owner row count: `{summary['tooltip_owner_row_count']}`",
        f"- Tooltip present rows by region: `{summary['tooltip_present_by_region']}`",
        f"- Tooltip null-present rows by region: `{summary['tooltip_null_present_by_region']}`",
        f"- Action-bar visible: `{summary['action_bar_visible']}`",
        f"- Tooltip strip nonblack: `{summary['tooltip_strip_nonblack_visible']}`",
        f"- Tooltip strip visible: `{summary['tooltip_strip_visible']}`",
        f"- AV rows: `{summary['av_count']}`",
        "",
        "## Classification",
    ]
    lines.extend(f"- {item}" for item in summary["classification"])
    lines.extend(["", "## Hover Modes"])
    lines.extend(f"- {mode}" for mode in summary["hover_modes"])
    if not summary["hover_modes"]:
        lines.append("- none")
    if summary["png_regions"]:
        lines.extend(["", "## PNG Regions"])
        for name, region in summary["png_regions"].items():
            lines.append(
                f"- `{name}`: nonblack `{region['nonblack_percent']}%`, "
                f"black `{region['black_percent']}%`, rect `{region['logical_rect']}`"
            )
    lines.extend(["", "## First Tooltip Entries"])
    for row in summary["hover"]["entries"][:20]:
        lines.append(f"- line {row['line_no']}: {row['kind']}")
    if not summary["hover"]["entries"]:
        lines.append("- none")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def print_summary(summary: dict[str, Any]) -> None:
    print(
        "evidence_pass={evidence} overall_pass={overall} decision={decision} "
        "unit={unit} post_redraw={post} hover={hover} owner={owner} action_bar={action} tooltip={tooltip} av_count={av}".format(
            evidence=summary["evidence_pass"],
            overall=summary["overall_pass"],
            decision=summary["decision"],
            unit=summary["unit_basic_pass"],
            post=summary["unit"]["post_redraw_route"],
            hover=summary["hover_sequence_observed"],
            owner=summary["tooltip_owner_evidence"],
            action=summary["action_bar_visible"],
            tooltip=summary["tooltip_strip_visible"],
            av=summary["av_count"],
        )
    )
    for item in summary["classification"]:
        print(f"- {item}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log", type=Path)
    parser.add_argument("--png", type=Path)
    parser.add_argument("--expected-slot", type=int, default=0)
    parser.add_argument("--write-json", type=Path)
    parser.add_argument("--write-md", type=Path)
    parser.add_argument("--logical-width", type=int, default=800)
    parser.add_argument("--logical-height", type=int, default=600)
    parser.add_argument("--threshold", type=int, default=12)
    parser.add_argument("--action-bar-min-nonblack", type=float, default=40.0)
    parser.add_argument("--tooltip-min-nonblack", type=float, default=1.0)
    parser.add_argument("--require-evidence-pass", action="store_true")
    parser.add_argument("--require-tooltip-owner", action="store_true")
    parser.add_argument("--require-tooltip-visible", action="store_true")
    parser.add_argument("--require-action-bar-visible", action="store_true")
    args = parser.parse_args(argv)

    summary = summarize(args.log, args.png, args)
    if args.write_json:
        args.write_json.parent.mkdir(parents=True, exist_ok=True)
        args.write_json.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    if args.write_md:
        write_markdown(args.write_md, summary)
    print_summary(summary)

    failures: list[str] = []
    if args.require_evidence_pass and not summary["evidence_pass"]:
        failures.append("basic first-mission unit-selection tooltip evidence did not pass")
    if args.require_tooltip_owner and not summary["tooltip_owner_evidence"]:
        failures.append("native tooltip/status owner evidence was not observed")
    if args.require_tooltip_visible and not summary["tooltip_strip_visible"]:
        failures.append("native bottom tooltip strip was not visible")
    if args.require_action_bar_visible and not summary["action_bar_visible"]:
        failures.append("selected-unit action bar was not visible")
    if failures:
        for failure in failures:
            print(f"ERROR: {failure}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
