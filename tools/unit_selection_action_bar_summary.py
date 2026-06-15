#!/usr/bin/env python3
"""Summarize first-mission unit-selection action-bar CDB evidence."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


MARKERS = (
    "UNITSEL_ROUTE_START",
    "UNITSEL_INVOKE_408030_THEN_406980",
    "UNITSEL_SELECT_ENTRY",
    "UNITSEL_SELECT_TILE",
    "UNITSEL_SELECT_SUCCESS",
    "UNITSEL_SELECT_FAIL",
    "UNITSEL_WRITE_511B58",
    "UNITSEL_WRITE_514194",
    "UNITSEL_406980_ENTRY",
    "UNITSEL_406980_POST_REDRAW_ENTRY",
    "UNITSEL_406980_PRESENT_HELPER",
    "UNITSEL_406980_RENDER_PRESENT",
    "UNITSEL_POST_REDRAW_CAVE_ENTRY",
    "UNITSEL_406980_POST_REDRAW_RETURN",
    "UNITSEL_406980_RETURN_DUMP",
    "UNITSEL_40A490_ENTRY",
    "UNITSEL_40A500_ENTRY",
    "UNITSEL_40A500_CALL_423B00",
    "UNITSEL_423B00_ENTRY",
    "SURFDUMP_LOADSAVE",
    "SURFDUMP_PLAYGAME",
    "SURFDUMP_REDRAW",
    "SURFDUMP_READY",
    "SURFDUMP_HOST_READY",
    "AV_SURFDUMP",
)

ALIASES = {
    "RLOOPU_HEADER": "UNITSEL_ROUTE_START",
    "RLOOPU_INVOKE_408030_THEN_406980": "UNITSEL_INVOKE_408030_THEN_406980",
    "RLOOPU_SELECT_ENTRY": "UNITSEL_SELECT_ENTRY",
    "RLOOPU_SELECT_TILE": "UNITSEL_SELECT_TILE",
    "RLOOPU_SELECT_SUCCESS": "UNITSEL_SELECT_SUCCESS",
    "RLOOPU_SELECT_FAIL": "UNITSEL_SELECT_FAIL",
    "RLOOPU_WRITE_511B58": "UNITSEL_WRITE_511B58",
    "RLOOPU_WRITE_514194": "UNITSEL_WRITE_514194",
    "RLOOPU_406980_ENTRY": "UNITSEL_406980_ENTRY",
    "RLOOPU_40A490_ENTRY": "UNITSEL_40A490_ENTRY",
    "RLOOPU_40A500_ENTRY": "UNITSEL_40A500_ENTRY",
    "RLOOPU_40A500_CALL_423B00": "UNITSEL_40A500_CALL_423B00",
    "RLOOPU_423B00_ENTRY": "UNITSEL_423B00_ENTRY",
    "RLOOP_HEADER": "UNITSEL_ROUTE_START",
    "RLOOP_INVOKE_408030": "UNITSEL_INVOKE_408030_THEN_406980",
    "RLOOP_SELECT_ENTRY": "UNITSEL_SELECT_ENTRY",
    "RLOOP_SELECT_TILE": "UNITSEL_SELECT_TILE",
    "RLOOP_SELECT_SUCCESS": "UNITSEL_SELECT_SUCCESS",
    "RLOOP_SELECT_FAIL": "UNITSEL_SELECT_FAIL",
    "RLOOP_WRITE_511B58": "UNITSEL_WRITE_511B58",
    "RLOOP_WRITE_514194": "UNITSEL_WRITE_514194",
    "RSEL_INVOKE_408030": "UNITSEL_INVOKE_408030_THEN_406980",
    "RSEL_INVOKE_408030_POST_RESET": "UNITSEL_INVOKE_408030_THEN_406980",
    "RSEL_SELECT_ENTRY": "UNITSEL_SELECT_ENTRY",
    "RSEL_SELECT_TILE": "UNITSEL_SELECT_TILE",
    "RSEL_SELECT_SUCCESS": "UNITSEL_SELECT_SUCCESS",
    "RSEL_SELECT_FAIL": "UNITSEL_SELECT_FAIL",
    "RSEL_WRITE_511B58": "UNITSEL_WRITE_511B58",
    "APROUTE_40A500_ENTRY": "UNITSEL_40A500_ENTRY",
    "APROUTE_40A500_CALL_423B00": "UNITSEL_40A500_CALL_423B00",
}

VALUE_RE = re.compile(r"(?P<key>[A-Za-z0-9_]+)=(?P<value>[-+0-9A-Fa-fx`]+)")
SLOT_RE = re.compile(
    r"SURFDUMP_LOADSAVE\b.*?\bselected_arg=(?P<arg>-?\d+)\b.*?\bselected_global=(?P<global>-?\d+)"
)
MARKER_RE = re.compile(r"\b(?P<marker>[A-Z][A-Z0-9_]+)\b")


def normalize_marker(marker: str) -> str | None:
    if marker in MARKERS:
        return marker
    return ALIASES.get(marker)


def parse_int(value: str) -> int | None:
    clean = value.replace("`", "")
    try:
        return int(clean, 0)
    except ValueError:
        return None


def parse_values(line: str) -> dict[str, int | str]:
    values: dict[str, int | str] = {}
    for match in VALUE_RE.finditer(line):
        value = match.group("value")
        parsed = parse_int(value)
        values[match.group("key")] = parsed if parsed is not None else value.replace("`", "")
    return values


def parse_log(path: Path, expected_slot: int = 0) -> dict[str, Any]:
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    counts = {marker: 0 for marker in MARKERS}
    rows: list[dict[str, Any]] = []
    loadsave_rows: list[dict[str, Any]] = []
    redraw_lines: list[int] = []
    ready_lines: list[int] = []
    av_rows: list[dict[str, Any]] = []

    for line_no, line in enumerate(lines, start=1):
        stripped = line.lstrip()
        if "Access violation - code" in stripped or stripped.startswith("AV_"):
            av_rows.append({"line_no": line_no, "line": stripped})
        for slot_match in SLOT_RE.finditer(line):
            loadsave_rows.append(
                {
                    "line_no": line_no,
                    "selected_arg": int(slot_match.group("arg")),
                    "selected_global": int(slot_match.group("global")),
                }
            )
        seen_on_line: set[str] = set()
        for marker_match in MARKER_RE.finditer(line):
            marker = normalize_marker(marker_match.group("marker"))
            if not marker or marker in seen_on_line:
                continue
            seen_on_line.add(marker)
            counts[marker] += 1
            row = {
                "line_no": line_no,
                "marker": marker,
                "raw_marker": marker_match.group("marker"),
                "line": stripped,
                "values": parse_values(line),
            }
            rows.append(row)
            if marker == "SURFDUMP_REDRAW":
                redraw_lines.append(line_no)
            elif marker == "SURFDUMP_READY":
                ready_lines.append(line_no)
            elif marker == "AV_SURFDUMP":
                av_rows.append({"line_no": line_no, "line": stripped})

    first_ready_line = min(ready_lines) if ready_lines else 0
    first_redraw_line = min(redraw_lines) if redraw_lines else 0
    return_dump_rows = [row for row in rows if row["marker"] == "UNITSEL_406980_RETURN_DUMP"]
    selection_success_rows = [row for row in rows if row["marker"] == "UNITSEL_SELECT_SUCCESS"]
    selection_write_success_rows = [
        row
        for row in rows
        if row["marker"] == "UNITSEL_WRITE_511B58"
        and isinstance(row["values"].get("new"), int)
        and row["values"]["new"] >= 0
    ]
    write_prior_rows = [row for row in rows if row["marker"] == "UNITSEL_WRITE_514194"]

    slot_matches = [
        row["selected_arg"] == expected_slot and row["selected_global"] == expected_slot
        for row in loadsave_rows
    ]
    load_slot_match = bool(loadsave_rows) and all(slot_matches)
    pre_redraw_dump = bool(return_dump_rows) or (
        bool(first_ready_line) and (not first_redraw_line or first_ready_line < first_redraw_line)
    )
    selection_success = bool(selection_success_rows or selection_write_success_rows)
    unit_info_route = counts["UNITSEL_406980_ENTRY"] > 0
    post_redraw_route = (
        counts["UNITSEL_POST_REDRAW_CAVE_ENTRY"] > 0
        and counts["UNITSEL_406980_POST_REDRAW_ENTRY"] > 0
        and counts["UNITSEL_406980_POST_REDRAW_RETURN"] > 0
    )
    present_helper = counts["UNITSEL_406980_PRESENT_HELPER"] > 0
    action_update = (
        counts["UNITSEL_40A500_ENTRY"] > 0
        and counts["UNITSEL_40A500_CALL_423B00"] > 0
        and (counts["UNITSEL_423B00_ENTRY"] > 0 or bool(write_prior_rows))
    )

    classification: list[str] = []
    if load_slot_match:
        classification.append(f"load route used expected slot {expected_slot}")
    elif loadsave_rows:
        classification.append("load route reached LOADSAVE, but slot fields did not match expectation")
    else:
        classification.append("LOADSAVE was not observed")
    if selection_success:
        classification.append("first-mission unit selection succeeded")
    else:
        classification.append("unit selection success was not observed")
    if unit_info_route:
        classification.append("selected-unit info/action updater 00406980 ran")
    else:
        classification.append("selected-unit info/action updater 00406980 did not run")
    if present_helper:
        classification.append("00406980 reached its low-level present/copy helper")
    if post_redraw_route:
        classification.append("selected-unit action bar was rerun after the full redraw exit")
    if action_update:
        classification.append("selected-unit action update route reached 0040A500 -> 00423B00")
    if pre_redraw_dump:
        classification.append("surface dump was armed before the later map redraw")
    elif counts["SURFDUMP_READY"]:
        classification.append("surface dump happened after the normal redraw cadence")
    if av_rows:
        classification.append("AV observed")

    return {
        "log": str(path),
        "expected_slot": expected_slot,
        "marker_counts": counts,
        "rows": rows,
        "loadsave_rows": loadsave_rows,
        "load_slot_match": load_slot_match,
        "ready": counts["SURFDUMP_READY"] > 0,
        "first_ready_line": first_ready_line,
        "first_redraw_line": first_redraw_line,
        "pre_redraw_dump": pre_redraw_dump,
        "selection_success": selection_success,
        "unit_info_route": unit_info_route,
        "post_redraw_route": post_redraw_route,
        "present_helper": present_helper,
        "render_present": counts["UNITSEL_406980_RENDER_PRESENT"] > 0,
        "action_update": action_update,
        "av_count": len(av_rows),
        "av_rows": av_rows,
        "classification": classification,
    }


def write_markdown(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# Unit Selection Action Bar Summary",
        "",
        f"- Log: `{summary['log']}`",
        f"- Expected load slot: `{summary['expected_slot']}`",
        f"- Load slot match: `{summary['load_slot_match']}`",
        f"- Ready: `{summary['ready']}`",
        f"- Pre-redraw dump: `{summary['pre_redraw_dump']}`",
        f"- Selection success: `{summary['selection_success']}`",
        f"- 00406980 route: `{summary['unit_info_route']}`",
        f"- Post-redraw 00406980 route: `{summary['post_redraw_route']}`",
        f"- Present helper: `{summary['present_helper']}`",
        f"- Render present: `{summary['render_present']}`",
        f"- 0040A500 -> 00423B00 update: `{summary['action_update']}`",
        f"- AV rows: `{summary['av_count']}`",
        "",
        "## Classification",
    ]
    lines.extend(f"- {item}" for item in summary["classification"])
    lines.extend(["", "## Marker Counts"])
    for marker in MARKERS:
        lines.append(f"- {marker}: {summary['marker_counts'][marker]}")
    lines.extend(["", "## First Rows"])
    for row in summary["rows"][:40]:
        lines.append(f"- line {row['line_no']}: {row['line']}")
    if not summary["rows"]:
        lines.append("- none")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log", type=Path)
    parser.add_argument("--expected-slot", type=int, default=0)
    parser.add_argument("--write-json", type=Path)
    parser.add_argument("--write-md", type=Path)
    parser.add_argument("--require-load-slot", action="store_true")
    parser.add_argument("--require-ready", action="store_true")
    parser.add_argument("--require-pre-redraw-dump", action="store_true")
    parser.add_argument("--require-selection-success", action="store_true")
    parser.add_argument("--require-unit-info-route", action="store_true")
    parser.add_argument("--require-post-redraw-route", action="store_true")
    parser.add_argument("--require-present-helper", action="store_true")
    parser.add_argument("--require-action-update", action="store_true")
    parser.add_argument("--require-no-av", action="store_true")
    args = parser.parse_args(argv)

    summary = parse_log(args.log, expected_slot=args.expected_slot)
    if args.write_json:
        args.write_json.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    if args.write_md:
        write_markdown(args.write_md, summary)

    print(
        "slot_match={slot} ready={ready} pre_redraw_dump={dump} selection_success={sel} "
        "unit_info_route={route} post_redraw_route={post} present_helper={helper} action_update={update} av_count={av}".format(
            slot=summary["load_slot_match"],
            ready=summary["ready"],
            dump=summary["pre_redraw_dump"],
            sel=summary["selection_success"],
            route=summary["unit_info_route"],
            post=summary["post_redraw_route"],
            helper=summary["present_helper"],
            update=summary["action_update"],
            av=summary["av_count"],
        )
    )
    for item in summary["classification"]:
        print(f"- {item}")

    failures: list[str] = []
    if args.require_load_slot and not summary["load_slot_match"]:
        failures.append("expected LOADSAVE slot fields were not observed")
    if args.require_ready and not summary["ready"]:
        failures.append("SURFDUMP_READY was not observed")
    if args.require_pre_redraw_dump and not summary["pre_redraw_dump"]:
        failures.append("pre-redraw action-bar dump was not observed")
    if args.require_selection_success and not summary["selection_success"]:
        failures.append("unit selection success was not observed")
    if args.require_unit_info_route and not summary["unit_info_route"]:
        failures.append("selected-unit info/action route was not observed")
    if args.require_post_redraw_route and not summary["post_redraw_route"]:
        failures.append("post-redraw selected-unit info/action route was not observed")
    if args.require_present_helper and not summary["present_helper"]:
        failures.append("selected-unit present helper was not observed")
    if args.require_action_update and not summary["action_update"]:
        failures.append("selected-unit action update route was not observed")
    if args.require_no_av and summary["av_count"]:
        failures.append("AV rows were observed")
    if failures:
        for failure in failures:
            print(f"ERROR: {failure}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
