#!/usr/bin/env python3
"""Summarize focused LSTRANS load-slot transition CDB logs.

This is a repo-only parser for logs produced by
probes/cdb/menu/clash95_load_slot_entry_transition_extra.cdb. It does not launch Clash95, CDB,
wrappers, PowerShell, or visible windows.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


MARKERS = (
    "LSTRANS_LOAD_CALLBACK_ENTRY",
    "LSTRANS_AFTER_MAIN_CALLBACK",
    "LSTRANS_MAIN_WAIT_GATE",
    "LSTRANS_WAIT_LOOP_PUMP",
    "LSTRANS_WAIT_LOOP_COMPARE",
    "LSTRANS_WAIT_LOOP_EXIT",
    "LSTRANS_MAIN_SWITCH_DISPATCH",
    "LSTRANS_MAIN_DISPATCH_POLL",
    "LSTRANS_LOAD_MENU_ENTRY",
    "LSTRANS_LATE_MOUSE_SET",
    "LSTRANS_LOAD_SLOT_DRAW",
    "LSTRANS_LOAD_MENU_LOOP",
    "LSTRANS_LATE_FORCE_SELECT",
    "LSTRANS_LATE_FORCE_ACCEPT",
    "LSTRANS_LOAD_ACCEPT_CALL",
    "LSTRANS_LOADSAVE",
    "LSTRANS_PLAYGAME",
)

MARKER_ALIASES = {
    "SURFDUMP_PLAYGAME": "LSTRANS_PLAYGAME",
}

KV_RE = re.compile(r"(?P<key>[A-Za-z_][A-Za-z0-9_]*)=(?P<value>\([^)]*\)|[^\s]+)")
MARKER_RE = re.compile("|".join(re.escape(marker) for marker in (*MARKERS, *MARKER_ALIASES)))


def parse_value(value: str) -> Any:
    value = value.strip().rstrip(",")
    if value.startswith("(") and value.endswith(")"):
        parts = [part.strip() for part in value[1:-1].split(",") if part.strip()]
        return [parse_value(part) for part in parts]
    try:
        return int(value, 0)
    except ValueError:
        if re.fullmatch(r"[0-9A-Fa-f]{6,8}", value):
            return int(value, 16)
        return value


def parse_rows(text: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    av_rows: list[dict[str, Any]] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        lowered = line.lower()
        if "access violation" in lowered or "code c0000005" in lowered or line.lstrip().startswith("AV_"):
            av_rows.append({"line": line_no, "text": line.strip()})
        matches = list(MARKER_RE.finditer(line))
        for index, match in enumerate(matches):
            marker = match.group(0)
            marker = MARKER_ALIASES.get(marker, marker)
            end = matches[index + 1].start() if index + 1 < len(matches) else len(line)
            fragment = line[match.start() : end].strip()
            rows.append(
                {
                    "line": line_no,
                    "marker": marker,
                    "values": {
                        item.group("key"): parse_value(item.group("value"))
                        for item in KV_RE.finditer(fragment)
                    },
                    "text": fragment,
                }
            )
    return rows, av_rows


def marker_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = {marker: 0 for marker in MARKERS}
    for row in rows:
        counts[row["marker"]] += 1
    return counts


def rows_for(rows: list[dict[str, Any]], marker: str) -> list[dict[str, Any]]:
    return [row for row in rows if row["marker"] == marker]


def last_row(rows: list[dict[str, Any]], marker: str) -> dict[str, Any] | None:
    matches = rows_for(rows, marker)
    return matches[-1] if matches else None


def unique_preserving_order(values: list[Any]) -> list[Any]:
    unique: list[Any] = []
    for value in values:
        if value not in unique:
            unique.append(value)
    return unique


def count_positive(counts: dict[str, int], *markers: str) -> bool:
    return all(int(counts.get(marker) or 0) > 0 for marker in markers)


def nonzero_gd(row: dict[str, Any] | None) -> bool:
    if not row:
        return False
    gd = (row.get("values") or {}).get("gd")
    return gd not in (None, 0, "00000000")


def classify(summary: dict[str, Any]) -> str:
    counts = summary["marker_counts"]
    if summary["av_count"]:
        return "access_violation"
    if not summary["expected_slot_match"] and (
        summary["target_slot_values"] or summary["loadsave"] or summary["playgame"]
    ):
        return "slot_mismatch"
    if counts["LSTRANS_LOADSAVE"] and nonzero_gd(summary.get("last_playgame_row")):
        return "late_entry_load_success"
    if count_positive(counts, "LSTRANS_LOAD_MENU_ENTRY", "LSTRANS_LATE_MOUSE_SET") and not counts["LSTRANS_LOADSAVE"]:
        return "entered_load_menu_without_loadsave"
    if (
        counts["LSTRANS_LOAD_CALLBACK_ENTRY"]
        or counts["LSTRANS_AFTER_MAIN_CALLBACK"]
        or counts["LSTRANS_MAIN_WAIT_GATE"]
        or counts["LSTRANS_WAIT_LOOP_PUMP"]
        or counts["LSTRANS_WAIT_LOOP_COMPARE"]
        or counts["LSTRANS_WAIT_LOOP_EXIT"]
        or counts["LSTRANS_MAIN_SWITCH_DISPATCH"]
        or counts["LSTRANS_MAIN_DISPATCH_POLL"]
    ):
        return "stalled_before_load_menu_entry"
    return "no_main_load_handoff"


def build_classification(summary: dict[str, Any]) -> list[str]:
    counts = summary["marker_counts"]
    lines: list[str] = []
    if summary["expected_slot"] is not None:
        lines.append(
            "all observed target_slot values "
            + ("match" if summary["target_slot_expected_match"] else "do not match")
            + f" expected slot {summary['expected_slot']}"
        )
    if not summary["target_slot_consistent"]:
        lines.append(f"conflicting target_slot values were observed: {summary['target_slot_unique_values']}")
    if summary["loadsave_slot_match"] is False:
        lines.append("LOADSAVE selected slot did not match the expected slot")
    if summary["playgame_slot_match"] is False:
        lines.append("PlayGame target slot did not match the expected slot")
    if counts["LSTRANS_LOAD_CALLBACK_ENTRY"]:
        lines.append("main Load callback entry was observed")
    if counts["LSTRANS_AFTER_MAIN_CALLBACK"]:
        lines.append("main Load callback handoff was observed")
    else:
        lines.append("main Load callback handoff was not observed")
    if counts["LSTRANS_MAIN_WAIT_GATE"]:
        lines.append("main dispatch wait-gate rows were observed before the case switch")
    if counts["LSTRANS_WAIT_LOOP_PUMP"]:
        lines.append("main dispatch wait-loop pump rows were observed before the case switch")
    if counts["LSTRANS_WAIT_LOOP_COMPARE"]:
        last_compare = summary.get("last_wait_loop_compare") or {}
        will_loop = last_compare.get("will_loop")
        if will_loop == 1:
            lines.append("main dispatch wait-loop compare still branched back before the case switch")
        elif will_loop == 0:
            lines.append("main dispatch wait-loop compare was ready to fall through toward the case switch")
        else:
            lines.append("main dispatch wait-loop compare rows were observed before the case switch")
    if counts["LSTRANS_WAIT_LOOP_EXIT"]:
        lines.append("main dispatch wait-loop exit rows were observed before the case switch")
    if counts["LSTRANS_MAIN_SWITCH_DISPATCH"]:
        lines.append("main switch-dispatch rows were observed before the load-menu entry")
    if counts["LSTRANS_MAIN_DISPATCH_POLL"]:
        lines.append("main dispatch polling rows were observed")
    if counts["LSTRANS_LOAD_MENU_ENTRY"]:
        lines.append("real 0044895A load-menu entry was reached")
    else:
        lines.append("real 0044895A load-menu entry was not reached")
    if counts["LSTRANS_LATE_MOUSE_SET"]:
        lines.append("late mouse placement after load-menu entry was observed")
    if counts["LSTRANS_LOAD_SLOT_DRAW"]:
        lines.append("load-slot row drawing was observed")
    if counts["LSTRANS_LATE_FORCE_SELECT"]:
        lines.append("late force-select row was observed")
    if counts["LSTRANS_LATE_FORCE_ACCEPT"]:
        lines.append("late force-accept row was observed")
    if counts["LSTRANS_LOAD_ACCEPT_CALL"]:
        lines.append("load accept helper was reached")
    if counts["LSTRANS_LOADSAVE"]:
        lines.append("LOADSAVE was reached")
    if counts["LSTRANS_PLAYGAME"]:
        lines.append("PlayGame was reached")
    if summary["av_count"]:
        lines.append("AV evidence was observed")
    return lines


def parse_log(path: Path, expected_slot: int | None = None) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    rows, av_rows = parse_rows(text)
    counts = marker_counts(rows)
    loadsave = last_row(rows, "LSTRANS_LOADSAVE")
    playgame = last_row(rows, "LSTRANS_PLAYGAME")
    mouse_set = last_row(rows, "LSTRANS_LATE_MOUSE_SET")
    callback_entry = last_row(rows, "LSTRANS_LOAD_CALLBACK_ENTRY")
    wait_gate = last_row(rows, "LSTRANS_MAIN_WAIT_GATE")
    wait_loop_pump = last_row(rows, "LSTRANS_WAIT_LOOP_PUMP")
    wait_loop_compare = last_row(rows, "LSTRANS_WAIT_LOOP_COMPARE")
    wait_loop_exit = last_row(rows, "LSTRANS_WAIT_LOOP_EXIT")
    switch_dispatch = last_row(rows, "LSTRANS_MAIN_SWITCH_DISPATCH")
    loadsave_values = (loadsave or {}).get("values", {}) if loadsave else {}
    playgame_values = (playgame or {}).get("values", {}) if playgame else {}
    selected_arg = loadsave_values.get("selected_arg") if loadsave else None
    selected_global = loadsave_values.get("selected_global") if loadsave else None
    target_slot_values = [
        row["values"].get("target_slot")
        for row in rows
        if row["values"].get("target_slot") is not None
    ]
    target_slot_unique_values = unique_preserving_order(target_slot_values)
    target_slot_consistent = len(target_slot_unique_values) <= 1
    target_slot = target_slot_values[-1] if target_slot_values else expected_slot
    target_slot_expected_match = (
        expected_slot is None
        or (
            bool(target_slot_values)
            and target_slot_consistent
            and target_slot_unique_values[0] == expected_slot
        )
    )
    loadsave_slot_match = None
    if expected_slot is not None and loadsave:
        loadsave_slot_match = (
            selected_arg == expected_slot
            and selected_global in (None, expected_slot)
            and loadsave_values.get("target_slot") in (None, expected_slot)
        )
    playgame_slot_match = None
    if expected_slot is not None and playgame:
        playgame_slot_match = playgame_values.get("target_slot") in (None, expected_slot)
    expected_slot_match = (
        expected_slot is None
        or (
            target_slot_expected_match
            and loadsave_slot_match is not False
            and playgame_slot_match is not False
        )
    )
    summary: dict[str, Any] = {
        "log": str(path),
        "expected_slot": expected_slot,
        "target_slot": target_slot,
        "target_slot_values": target_slot_values,
        "target_slot_unique_values": target_slot_unique_values,
        "target_slot_consistent": target_slot_consistent,
        "target_slot_expected_match": target_slot_expected_match,
        "loadsave_slot_match": loadsave_slot_match,
        "playgame_slot_match": playgame_slot_match,
        "expected_slot_match": expected_slot_match,
        "row_count": len(rows),
        "marker_counts": counts,
        "av_count": len(av_rows),
        "av_rows": av_rows,
        "last_late_mouse": (mouse_set or {}).get("values") if mouse_set else None,
        "last_callback_entry": (callback_entry or {}).get("values") if callback_entry else None,
        "last_wait_gate": (wait_gate or {}).get("values") if wait_gate else None,
        "last_wait_loop_pump": (wait_loop_pump or {}).get("values") if wait_loop_pump else None,
        "last_wait_loop_compare": (wait_loop_compare or {}).get("values") if wait_loop_compare else None,
        "last_wait_loop_exit": (wait_loop_exit or {}).get("values") if wait_loop_exit else None,
        "last_switch_dispatch": (switch_dispatch or {}).get("values") if switch_dispatch else None,
        "loadsave": (loadsave or {}).get("values") if loadsave else None,
        "playgame": (playgame or {}).get("values") if playgame else None,
        "last_playgame_row": playgame,
        "selected_arg": selected_arg,
        "rows": rows,
    }
    summary["status"] = classify(summary)
    summary["classification"] = build_classification(summary)
    return summary


def write_markdown(summary: dict[str, Any], path: Path) -> None:
    lines = [
        "# Load Slot Transition Summary",
        "",
        f"- Log: `{summary['log']}`",
        f"- Status: `{summary['status']}`",
        f"- Expected slot: `{summary['expected_slot']}`",
        f"- Target slot: `{summary['target_slot']}`",
        f"- Target slot values: `{summary['target_slot_values']}`",
        f"- Target slot consistent: `{summary['target_slot_consistent']}`",
        f"- Target slot expected match: `{summary['target_slot_expected_match']}`",
        f"- LOADSAVE slot match: `{summary['loadsave_slot_match']}`",
        f"- PlayGame slot match: `{summary['playgame_slot_match']}`",
        f"- Expected slot match: `{summary['expected_slot_match']}`",
        f"- Rows parsed: `{summary['row_count']}`",
        f"- Access violations: `{summary['av_count']}`",
        f"- Last callback entry: `{summary['last_callback_entry']}`",
        f"- Last wait gate: `{summary['last_wait_gate']}`",
        f"- Last wait-loop pump: `{summary['last_wait_loop_pump']}`",
        f"- Last wait-loop compare: `{summary['last_wait_loop_compare']}`",
        f"- Last wait-loop exit: `{summary['last_wait_loop_exit']}`",
        f"- Last switch dispatch: `{summary['last_switch_dispatch']}`",
        f"- Last late mouse: `{summary['last_late_mouse']}`",
        f"- LOADSAVE: `{summary['loadsave']}`",
        f"- PlayGame: `{summary['playgame']}`",
        "",
        "## Marker Counts",
        "",
    ]
    for marker, count in summary["marker_counts"].items():
        lines.append(f"- `{marker}`: `{count}`")
    lines.extend(["", "## Classification", ""])
    lines.extend(f"- {item}" for item in summary["classification"])
    lines.extend(["", "## Key Rows", ""])
    for row in summary["rows"][-18:]:
        lines.append(f"- line {row['line']}: `{row['text']}`")
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log", type=Path)
    parser.add_argument("--expected-slot", type=int)
    parser.add_argument("--write-json", type=Path)
    parser.add_argument("--write-md", type=Path)
    parser.add_argument("--require-success", action="store_true")
    parser.add_argument("--require-entry", action="store_true")
    parser.add_argument("--require-slot-match", action="store_true")
    args = parser.parse_args()

    summary = parse_log(args.log, args.expected_slot)
    if args.write_json:
        args.write_json.parent.mkdir(parents=True, exist_ok=True)
        args.write_json.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    if args.write_md:
        write_markdown(summary, args.write_md)

    print(f"status={summary['status']} rows={summary['row_count']} av={summary['av_count']}")
    for item in summary["classification"]:
        print(f"- {item}")

    if args.require_entry and not summary["marker_counts"]["LSTRANS_LOAD_MENU_ENTRY"]:
        print("required load-menu entry was not observed", file=sys.stderr)
        return 2
    if args.require_success and summary["status"] != "late_entry_load_success":
        print("required late-entry load success was not observed", file=sys.stderr)
        return 2
    if args.require_slot_match and not summary["expected_slot_match"]:
        print("expected slot did not match observed target/LOADSAVE slot", file=sys.stderr)
        return 2
    if summary["av_count"]:
        print("access violation rows were observed", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
