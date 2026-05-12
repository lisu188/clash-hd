#!/usr/bin/env python3
"""Summarize Clash95 mouse-edge scroll CDB probe logs."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


PLAYGAME_RE = re.compile(
    r"MOUSEEDGE_PLAYGAME gd=(?P<gd>\S+) map=\((?P<mapw>-?\d+),(?P<maph>-?\d+)\) "
    r"scroll=\((?P<scrollx>-?\d+),(?P<scrolly>-?\d+)\)"
)
INVOKE_RE = re.compile(
    r"MOUSEEDGE_INVOKE scroll=\((?P<scrollx>-?\d+),(?P<scrolly>-?\d+)\) "
    r"mouse=\((?P<mousex>-?\d+),(?P<mousey>-?\d+)\)"
)
ENTRY_RE = re.compile(
    r"MOUSEEDGE_ENTRY scroll=\((?P<scrollx>-?\d+),(?P<scrolly>-?\d+)\) "
    r"mouse=\((?P<mousex>-?\d+),(?P<mousey>-?\d+)\)"
)
DELTA_RE = re.compile(
    r"MOUSEEDGE_DELTA seq=(?P<seq>\d+) start=\((?P<startx>-?\d+),(?P<starty>-?\d+)\) "
    r"forced=\((?P<forcedx>-?\d+),(?P<forcedy>-?\d+)\) "
    r"scroll_before=\((?P<scrollx>-?\d+),(?P<scrolly>-?\d+)\)"
)
STEP_RE = re.compile(
    r"MOUSEEDGE_STEP seq=(?P<seq>\d+) scroll=\((?P<scrollx>-?\d+),(?P<scrolly>-?\d+)\) "
    r"end12=\((?P<endx>-?\d+),(?P<endy>-?\d+)\) map=\((?P<mapw>-?\d+),(?P<maph>-?\d+)\) "
    r"max_hd=\((?P<hdx>-?\d+),(?P<hdy>-?\d+)\) max_old=\((?P<oldx>-?\d+),(?P<oldy>-?\d+)\) "
    r"mouse=\((?P<mousex>-?\d+),(?P<mousey>-?\d+)\)"
)
REDRAW_RE = re.compile(
    r"MOUSEEDGE_REDRAW seq=(?P<seq>\d+) scroll=\((?P<scrollx>-?\d+),(?P<scrolly>-?\d+)\) "
    r"end12=\((?P<endx>-?\d+),(?P<endy>-?\d+)\) map=\((?P<mapw>-?\d+),(?P<maph>-?\d+)\) "
    r"max_hd=\((?P<hdx>-?\d+),(?P<hdy>-?\d+)\) max_old=\((?P<oldx>-?\d+),(?P<oldy>-?\d+)\)"
)
BOUNDARY_RE = re.compile(
    r"MOUSEEDGE_BOUNDARY_READY steps=(?P<steps>\d+) scroll=\((?P<scrollx>-?\d+),(?P<scrolly>-?\d+)\) "
    r"max_hd=\((?P<hdx>-?\d+),(?P<hdy>-?\d+)\)"
)
EXCEPTION_ADDRESS_RE = re.compile(r"ExceptionAddress:\s+(?P<address>[0-9a-fA-F]+)(?:\s+\((?P<symbol>[^)]+)\))?")
EXCEPTION_CODE_RE = re.compile(r"ExceptionCode:\s+(?P<code>[0-9a-fA-F]+)")
ACCESS_RE = re.compile(r"Attempt to (?P<access>\w+) from address (?P<address>[0-9a-fA-F]+)")
REGISTERS_RE = re.compile(
    r"eax=(?P<eax>[0-9a-fA-F]+) ebx=(?P<ebx>[0-9a-fA-F]+) ecx=(?P<ecx>[0-9a-fA-F]+) "
    r"edx=(?P<edx>[0-9a-fA-F]+) esi=(?P<esi>[0-9a-fA-F]+) edi=(?P<edi>[0-9a-fA-F]+)"
)

INT_FIELDS = {
    "seq",
    "steps",
    "scrollx",
    "scrolly",
    "endx",
    "endy",
    "mapw",
    "maph",
    "hdx",
    "hdy",
    "oldx",
    "oldy",
    "mousex",
    "mousey",
    "startx",
    "starty",
    "forcedx",
    "forcedy",
}


def convert(match: re.Match[str], line_no: int, kind: str) -> dict:
    row: dict[str, int | str] = {"kind": kind, "line_no": line_no}
    for key, value in match.groupdict().items():
        if key in INT_FIELDS:
            row[key] = int(value)
        else:
            row[key] = value
    return row


def parse_log(path: Path) -> dict[str, list[dict]]:
    rows: dict[str, list[dict]] = {
        "playgame": [],
        "invoke": [],
        "entry": [],
        "delta": [],
        "step": [],
        "redraw": [],
        "boundary_ready": [],
        "av": [],
    }
    for line_no, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
        if match := PLAYGAME_RE.search(line):
            rows["playgame"].append(convert(match, line_no, "MOUSEEDGE_PLAYGAME"))
        elif match := INVOKE_RE.search(line):
            rows["invoke"].append(convert(match, line_no, "MOUSEEDGE_INVOKE"))
        elif match := ENTRY_RE.search(line):
            rows["entry"].append(convert(match, line_no, "MOUSEEDGE_ENTRY"))
        elif match := DELTA_RE.search(line):
            rows["delta"].append(convert(match, line_no, "MOUSEEDGE_DELTA"))
        elif match := STEP_RE.search(line):
            rows["step"].append(convert(match, line_no, "MOUSEEDGE_STEP"))
        elif match := REDRAW_RE.search(line):
            rows["redraw"].append(convert(match, line_no, "MOUSEEDGE_REDRAW"))
        elif match := BOUNDARY_RE.search(line):
            rows["boundary_ready"].append(convert(match, line_no, "MOUSEEDGE_BOUNDARY_READY"))
        elif line.strip() == "AV_MOUSEEDGE":
            rows["av"].append({"kind": "AV_MOUSEEDGE", "line_no": line_no})
        elif rows["av"] and (match := EXCEPTION_ADDRESS_RE.search(line)):
            rows["av"][-1]["exception_address"] = match.group("address").lower()
            if match.group("symbol"):
                rows["av"][-1]["exception_symbol"] = match.group("symbol")
        elif rows["av"] and (match := EXCEPTION_CODE_RE.search(line)):
            rows["av"][-1]["exception_code"] = match.group("code").lower()
        elif rows["av"] and (match := ACCESS_RE.search(line)):
            rows["av"][-1]["access"] = match.group("access").lower()
            rows["av"][-1]["access_address"] = match.group("address").lower()
        elif rows["av"] and (match := REGISTERS_RE.search(line)):
            rows["av"][-1]["registers"] = {key: value.lower() for key, value in match.groupdict().items()}
    return rows


def boundary_rows(rows: list[dict]) -> list[dict]:
    return [
        row
        for row in rows
        if int(row["scrollx"]) == int(row["hdx"]) and int(row["scrolly"]) == int(row["hdy"])
    ]


def overrun_rows(rows: list[dict]) -> list[dict]:
    return [
        row
        for row in rows
        if int(row["endx"]) > int(row["mapw"]) or int(row["endy"]) > int(row["maph"])
    ]


def old_overflow_rows(rows: list[dict]) -> list[dict]:
    return [
        row
        for row in rows
        if int(row["oldx"]) + 12 > int(row["mapw"]) or int(row["oldy"]) + 9 > int(row["maph"])
    ]


def summarize(path: Path) -> dict:
    rows = parse_log(path)
    step_boundary = boundary_rows(rows["step"])
    redraw_boundary = boundary_rows(rows["redraw"])
    step_overruns = overrun_rows(rows["step"])
    redraw_overruns = overrun_rows(rows["redraw"])
    observations = sorted(rows["step"] + rows["redraw"], key=lambda row: int(row["line_no"]))
    return {
        "log": str(path),
        "playgame_rows": len(rows["playgame"]),
        "invoke_rows": len(rows["invoke"]),
        "entry_rows": len(rows["entry"]),
        "delta_rows": len(rows["delta"]),
        "step_rows": len(rows["step"]),
        "redraw_rows": len(rows["redraw"]),
        "boundary_ready_rows": len(rows["boundary_ready"]),
        "av_rows": len(rows["av"]),
        "boundary_reached": bool(step_boundary or redraw_boundary or rows["boundary_ready"]),
        "overrun_count": len(step_overruns) + len(redraw_overruns),
        "old_overflow_risk_count": len(old_overflow_rows(rows["step"])) + len(old_overflow_rows(rows["redraw"])),
        "first_playgame": rows["playgame"][:1],
        "first_entry": rows["entry"][:1],
        "first_delta": rows["delta"][:1],
        "first_step": rows["step"][:1],
        "final_step": rows["step"][-1:] if rows["step"] else [],
        "final_redraw": rows["redraw"][-1:] if rows["redraw"] else [],
        "final_observation": observations[-1:] if observations else [],
        "first_av": rows["av"][:1],
        "boundary_rows": (step_boundary + redraw_boundary)[:5],
        "boundary_ready": rows["boundary_ready"][:5],
        "overrun_rows": (step_overruns + redraw_overruns)[:5],
    }


def print_summary(summary: dict) -> None:
    print(f"log: {summary['log']}")
    print(
        "rows: playgame={playgame_rows} invoke={invoke_rows} entry={entry_rows} "
        "delta={delta_rows} step={step_rows} redraw={redraw_rows} "
        "boundary_ready={boundary_ready_rows} av={av_rows}".format(**summary)
    )
    print(f"boundary_reached: {summary['boundary_reached']}")
    print(f"overrun_count: {summary['overrun_count']}")
    print(f"old_overflow_risk_count: {summary['old_overflow_risk_count']}")
    for key in (
        "first_playgame",
        "first_entry",
        "first_delta",
        "first_step",
        "final_step",
        "final_redraw",
        "final_observation",
        "first_av",
    ):
        if summary[key]:
            print(f"{key}: {summary[key][0]}")
    print(f"boundary_rows: {summary['boundary_rows']}")
    print(f"boundary_ready: {summary['boundary_ready']}")


def parse_pair(value: str) -> tuple[int, int]:
    try:
        left, right = value.split(",", 1)
        return int(left), int(right)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("expected a pair like 88,91") from exc


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log", type=Path)
    parser.add_argument("--write-json", type=Path)
    parser.add_argument("--require-hd-boundary", action="store_true")
    parser.add_argument("--require-boundary-ready", action="store_true")
    parser.add_argument("--expect-final-scroll", type=parse_pair, metavar="X,Y")
    parser.add_argument("--expect-final-end", type=parse_pair, metavar="X,Y")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary = summarize(args.log)
    if args.write_json:
        args.write_json.parent.mkdir(parents=True, exist_ok=True)
        args.write_json.write_text(json.dumps(summary, indent=2), encoding="ascii")
    print_summary(summary)
    failures = []
    if args.require_hd_boundary and (
        not summary["boundary_reached"] or summary["overrun_count"] or summary["av_rows"]
    ):
        failures.append("HD boundary was not proven cleanly")
    if args.require_boundary_ready and not summary["boundary_ready_rows"]:
        failures.append("MOUSEEDGE_BOUNDARY_READY was not logged")
    final_rows = summary["final_observation"]
    final = final_rows[0] if final_rows else None
    if args.expect_final_scroll:
        expected_x, expected_y = args.expect_final_scroll
        if not final or (int(final["scrollx"]), int(final["scrolly"])) != (expected_x, expected_y):
            failures.append(f"final scroll did not match ({expected_x},{expected_y})")
    if args.expect_final_end:
        expected_x, expected_y = args.expect_final_end
        if not final or (int(final["endx"]), int(final["endy"])) != (expected_x, expected_y):
            failures.append(f"final end12 did not match ({expected_x},{expected_y})")
    if failures:
        for failure in failures:
            print(f"ERROR: {failure}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
