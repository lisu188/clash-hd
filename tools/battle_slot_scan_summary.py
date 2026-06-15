#!/usr/bin/env python3
"""Summarize hidden-desktop battle unit scans across load slots.

This is a repo-only evidence aggregator. It reads existing CDB logs and run
summaries, then reports whether any routed slot naturally exposes a unit type
whose command table bytes are enabled. It does not launch Clash95, CDB,
wrappers, PowerShell, or any visible process.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import battle_command_availability as availability


DEFAULT_RUNS = [
    Path("captures/archive/cdb-surface-dump-20260520-195244"),
    Path("captures/archive/cdb-surface-dump-20260520-202027"),
    Path("captures/archive/cdb-surface-dump-20260520-202424"),
    Path("captures/archive/cdb-surface-dump-20260520-202504"),
    Path("captures/archive/cdb-surface-dump-20260520-202640"),
    Path("captures/archive/cdb-surface-dump-20260520-202810"),
]
DEFAULT_JSON = Path("captures/current/battle-slot-scan-current.json")
DEFAULT_MD = Path("captures/current/battle-slot-scan-current.md")
DEFAULT_EXE = Path(r"C:\Clash\clash95.exe")

LOADSAVE_RE = re.compile(r"SURFDUMP_LOADSAVE\s+selected_arg=(?P<arg>-?\d+)\s+selected_global=(?P<global>-?\d+)")
LOAD_COORD_RE = re.compile(r"SURFDUMP_LOAD_COORD\s+seq=(?P<seq>\d+).*?mouse=\((?P<x>-?\d+),(?P<y>-?\d+)\)")
SLOT_SCAN_RE = re.compile(
    r"BATTLE_SLOT_SCAN_SUMMARY\s+unit_count=(?P<count>\d+)\s+current=(?P<current>-?\d+)\s+"
    r"load_selected=(?P<load_selected>-?\d+)"
)


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def latest_match(pattern: re.Pattern[str], text: str) -> re.Match[str] | None:
    matches = list(pattern.finditer(text))
    return matches[-1] if matches else None


def infer_slot(summary: dict[str, Any], text: str) -> int | None:
    if isinstance(summary.get("LoadSlot"), int):
        return int(summary["LoadSlot"])
    match = latest_match(LOADSAVE_RE, text)
    if match:
        return int(match.group("arg"))
    match = latest_match(SLOT_SCAN_RE, text)
    if match:
        return int(match.group("load_selected"))
    return None


def classify_run(summary: dict[str, Any], text: str, unit_count: int, natural_enabled_count: int) -> str:
    if unit_count > 0 and natural_enabled_count > 0:
        return "routed-natural-enabled"
    if unit_count > 0:
        return "routed-no-natural-enabled"
    if summary.get("TimedOut") is True:
        return "timeout-before-unit-scan"
    if "AV_SURFDUMP" in text:
        return "av-before-unit-scan"
    return "no-unit-scan"


def summarize_run(run: Path, exe: Path) -> dict[str, Any]:
    log_path = availability.capture_log_path(run)
    text = log_path.read_text(encoding="utf-8", errors="replace") if log_path.exists() else ""
    summary = read_json(run / "summary.json") if run.is_dir() else {}
    units = availability.parse_units(text)
    unit_types = sorted({unit["unit_type"] for unit in units})
    natural_enabled_count = 0
    natural_enabled_units: list[dict[str, Any]] = []
    availability_summary: dict[str, Any] | None = None
    if units:
        availability_summary = availability.build_summary(run, exe, max_unit_type=31)
        natural_enabled_count = int(availability_summary["naturally_enabled_unit_count"])
        natural_enabled_units = availability_summary["naturally_enabled_units"]

    loadsave_match = latest_match(LOADSAVE_RE, text)
    coord_match = latest_match(LOAD_COORD_RE, text)
    slot_scan_match = latest_match(SLOT_SCAN_RE, text)
    slot = infer_slot(summary, text)
    return {
        "run": str(run),
        "log": str(log_path),
        "slot": slot,
        "passed": bool(summary.get("Passed")),
        "timed_out": bool(summary.get("TimedOut")),
        "error": summary.get("Error"),
        "loadsave_seen": loadsave_match is not None,
        "loadsave_selected_arg": int(loadsave_match.group("arg")) if loadsave_match else None,
        "loadsave_selected_global": int(loadsave_match.group("global")) if loadsave_match else None,
        "last_load_mouse": [int(coord_match.group("x")), int(coord_match.group("y"))] if coord_match else None,
        "slot_scan_seen": slot_scan_match is not None,
        "slot_scan_unit_count": int(slot_scan_match.group("count")) if slot_scan_match else None,
        "unit_count": len(units),
        "unit_types": unit_types,
        "natural_enabled_unit_count": natural_enabled_count,
        "natural_enabled_units": natural_enabled_units,
        "classification": classify_run(summary, text, len(units), natural_enabled_count),
        "candidate": summary.get("CandidatePath"),
        "png": summary.get("PngPath"),
    }


def build_summary(runs: list[Path], exe: Path) -> dict[str, Any]:
    rows = [summarize_run(run, exe) for run in runs]
    routed = [row for row in rows if row["unit_count"] > 0]
    natural_enabled = [unit for row in rows for unit in row["natural_enabled_units"]]
    timed_out = [row for row in rows if row["timed_out"] and row["unit_count"] == 0]
    return {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "runtime_policy": "repo-only parser; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows",
        "exe": str(exe),
        "run_count": len(rows),
        "routed_slot_count": len(routed),
        "timeout_before_unit_scan_count": len(timed_out),
        "natural_enabled_unit_count": len(natural_enabled),
        "natural_enabled_units": natural_enabled,
        "rows": rows,
    }


def write_markdown(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# Battle Slot Scan",
        "",
        f"- Generated: `{summary['generated_at']}`",
        f"- Runtime policy: {summary['runtime_policy']}",
        f"- Executable: `{summary['exe']}`",
        f"- Runs: `{summary['run_count']}`",
        f"- Routed slots with unit rows: `{summary['routed_slot_count']}`",
        f"- Timeouts before unit scan: `{summary['timeout_before_unit_scan_count']}`",
        f"- Natural enabled unit count: `{summary['natural_enabled_unit_count']}`",
        "",
        "## Slots",
        "",
        "| Slot | Classification | LoadSave | Units | Types | Natural Enabled | Run |",
        "| ---: | --- | --- | ---: | --- | ---: | --- |",
    ]
    for row in summary["rows"]:
        types = ", ".join(str(unit_type) for unit_type in row["unit_types"]) or "none"
        loadsave = row["loadsave_selected_arg"] if row["loadsave_seen"] else "not reached"
        lines.append(
            f"| {row['slot'] if row['slot'] is not None else 'unknown'} | {row['classification']} | "
            f"{loadsave} | {row['unit_count']} | {types} | {row['natural_enabled_unit_count']} | `{row['run']}` |"
        )
    screenshots = [row["png"] for row in summary["rows"] if row.get("png")]
    if screenshots:
        lines.extend(["", "## Screenshots", ""])
        for screenshot in screenshots:
            try:
                ref = Path(screenshot).resolve().relative_to(path.parent.resolve()).as_posix()
            except (OSError, ValueError):
                ref = screenshot
            lines.append(f"![battle slot scan]({ref})")
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("runs", type=Path, nargs="*", default=DEFAULT_RUNS)
    parser.add_argument("--exe", type=Path, default=DEFAULT_EXE)
    parser.add_argument("--write-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--write-markdown", "--write-md", dest="write_markdown", type=Path, default=DEFAULT_MD)
    parser.add_argument("--require-no-natural-enabled", action="store_true")
    parser.add_argument("--require-routed-slots", type=int, default=0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary = build_summary(args.runs, args.exe)
    print(f"runs: {summary['run_count']}")
    print(f"routed-slot-count: {summary['routed_slot_count']}")
    print(f"timeout-before-unit-scan-count: {summary['timeout_before_unit_scan_count']}")
    print(f"natural-enabled-unit-count: {summary['natural_enabled_unit_count']}")
    if args.write_json:
        args.write_json.parent.mkdir(parents=True, exist_ok=True)
        args.write_json.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    if args.write_markdown:
        write_markdown(args.write_markdown, summary)
    if args.require_no_natural_enabled and summary["natural_enabled_unit_count"]:
        return 2
    if args.require_routed_slots and summary["routed_slot_count"] < args.require_routed_slots:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
