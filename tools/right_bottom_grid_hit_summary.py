#!/usr/bin/env python3
"""Summarize Clash95 right-bottom controlled grid-hit CDB probes."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


MARKERS = (
    "RBGRID_OWNER_SETUP_CALL",
    "RBGRID_OWNER_FLAG_FORCED",
    "RBGRID_WRITE_532154",
    "RBGRID_ACTION_CALL",
    "RBGRID_433914_CALL_435BC0",
    "RBGRID_OWNER_435BC0_ENTRY",
    "RBGRID_WRITE_532218",
    "RBGRID_WRITE_5322C8",
    "RBGRID_PANEL_DRAW_4347A0",
    "RBGRID_GRID_DRAW_434E20",
    "RBGRID_STATUS_DRAW_435280",
    "RBGRID_ACTION_BOX_435500",
    "RBGRID_FORCE_NATIVE",
    "RBGRID_GRID_ROUTE_ENTRY",
    "RBGRID_GRID_GATE",
    "RBGRID_GRID_CALL",
    "RBGRID_GRID_ENTRY",
    "RBGRID_GRID_RESULT",
    "RBGRID_GRID_ACCEPT",
    "RBGRID_GRID_FAIL",
    "RBGRID_FAIL_EXIT_ARM",
    "RBGRID_SELECTION_UPDATE",
    "RBGRID_SELECTION_AFTER",
    "RBGRID_4338E0_AFTER_435BC0",
    "RBGRID_SURFDUMP_READY",
    "SURFDUMP_READY",
)

KV_RE = re.compile(r"(?P<key>[A-Za-z_][A-Za-z0-9_]*)=(?P<value>\([^)]*\)|[^\s]+)")


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


def parse_log(path: Path, expected_entry: list[int], expected_result: int) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="replace")
    marker_counts = {marker: 0 for marker in MARKERS}
    marker_re = re.compile("|".join(re.escape(marker) for marker in MARKERS))
    rows: list[dict[str, Any]] = []
    av_rows: list[dict[str, Any]] = []

    for index, line in enumerate(text.splitlines(), start=1):
        lowered = line.lower()
        if "access violation" in lowered or "code c0000005" in lowered or line.lstrip().startswith("AV_"):
            av_rows.append({"line": index, "text": line.strip()})
        matches = list(marker_re.finditer(line))
        for match_index, match in enumerate(matches):
            marker = match.group(0)
            end = matches[match_index + 1].start() if match_index + 1 < len(matches) else len(line)
            fragment = line[match.start() : end].strip()
            marker_counts[marker] += 1
            rows.append(
                {
                    "line": index,
                    "marker": marker,
                    "values": {
                        key_match.group("key"): parse_value(key_match.group("value"))
                        for key_match in KV_RE.finditer(fragment)
                    },
                    "text": fragment,
                }
            )

    grid_entries = [row for row in rows if row["marker"] == "RBGRID_GRID_ENTRY"]
    grid_results = [row for row in rows if row["marker"] == "RBGRID_GRID_RESULT"]
    grid_accepts = [row for row in rows if row["marker"] == "RBGRID_GRID_ACCEPT"]
    gate_rows = [row for row in rows if row["marker"] == "RBGRID_GRID_GATE"]
    forced_gate_rows = [
        row
        for row in gate_rows
        if str(row["values"].get("forced_result", "0")).lower() not in {"0", "false", "none"}
    ]
    failed_exit_rows = [row for row in rows if row["marker"] == "RBGRID_FAIL_EXIT_ARM"]
    selection_updates = [row for row in rows if row["marker"] == "RBGRID_SELECTION_UPDATE"]
    draw_rows = [
        row
        for row in rows
        if row["marker"]
        in {
            "RBGRID_PANEL_DRAW_4347A0",
            "RBGRID_GRID_DRAW_434E20",
            "RBGRID_STATUS_DRAW_435280",
            "RBGRID_ACTION_BOX_435500",
        }
    ]

    grid_hit_proofs: list[dict[str, Any]] = []
    last_entry: list[int] | None = None
    for row in rows:
        if row["marker"] == "RBGRID_GRID_ENTRY":
            last_entry = row["values"].get("mouse")
        elif row["marker"] == "RBGRID_GRID_RESULT":
            result = row["values"].get("result")
            if last_entry == expected_entry and result == expected_result:
                grid_hit_proofs.append(
                    {
                        "entry": last_entry,
                        "result": result,
                        "line": row["line"],
                    }
                )

    ready = bool(marker_counts["RBGRID_SURFDUMP_READY"] or marker_counts["SURFDUMP_READY"])
    grid_hit_ok = bool(grid_hit_proofs)
    classification: list[str] = []
    if marker_counts["RBGRID_FORCE_NATIVE"]:
        classification.append("native grid coordinate was installed by the probe")
    else:
        classification.append("native grid coordinate was not observed")
    if marker_counts["RBGRID_OWNER_435BC0_ENTRY"]:
        classification.append("right-bottom owner/action route entered 00435BC0")
    else:
        classification.append("right-bottom owner/action route did not enter 00435BC0")
    if draw_rows:
        classification.append("right-bottom panel/grid/status/action drawing rows fired")
    else:
        classification.append("right-bottom panel/grid/status/action drawing rows did not fire")
    if gate_rows:
        classification.append("hidden-desktop DD flip gate was reached")
    if forced_gate_rows:
        classification.append("hidden-desktop DD flip gate was debugger-forced")
    if marker_counts["RBGRID_GRID_ENTRY"]:
        classification.append("right-bottom grid hit-test was reached")
    else:
        classification.append("right-bottom grid hit-test was not reached")
    if grid_hit_ok:
        classification.append(
            f"grid hit-test returned expected cell {expected_result} at native coordinate {tuple(expected_entry)}"
        )
    else:
        classification.append(
            f"grid hit-test did not prove expected cell {expected_result} at native coordinate {tuple(expected_entry)}"
        )
    if grid_accepts:
        classification.append("grid result was accepted and the probe armed loop exit")
    if failed_exit_rows:
        classification.append("probe used failure exit because grid result was not accepted")
    if selection_updates:
        classification.append("grid selection update was observed")
    else:
        classification.append("grid selection update was not observed")
    if ready:
        classification.append("surface dump reached ready state")
    else:
        classification.append("surface dump did not reach ready state")
    if av_rows:
        classification.append("AV observed")

    return {
        "log": str(path),
        "expected_entry": expected_entry,
        "expected_result": expected_result,
        "marker_counts": marker_counts,
        "row_count": len(rows),
        "av_count": len(av_rows),
        "av_rows": av_rows,
        "ready": ready,
        "last_grid_entry": grid_entries[-1]["values"].get("mouse") if grid_entries else None,
        "last_grid_result": grid_results[-1]["values"].get("result") if grid_results else None,
        "grid_hit_ok": grid_hit_ok,
        "grid_hit_proofs": grid_hit_proofs,
        "forced_gate_count": len(forced_gate_rows),
        "failure_exit_count": len(failed_exit_rows),
        "selection_update_count": len(selection_updates),
        "draw_row_count": len(draw_rows),
        "classification": classification,
        "rows": rows,
    }


def write_markdown(summary: dict[str, Any], path: Path, screenshot: str | None) -> None:
    lines = [
        "# Right-Bottom Controlled Grid Hit Probe",
        "",
        f"- Log: `{summary['log']}`",
        f"- Rows parsed: {summary['row_count']}",
        f"- Access violations: {summary['av_count']}",
        f"- Ready: {summary['ready']}",
        f"- Expected grid entry: `{summary['expected_entry']}`",
        f"- Last grid entry: `{summary['last_grid_entry']}`",
        f"- Last grid result: `{summary['last_grid_result']}`",
        f"- Grid hit ok: {summary['grid_hit_ok']}",
        f"- Forced hidden flip gates: {summary['forced_gate_count']}",
        f"- Failure exits: {summary['failure_exit_count']}",
        f"- Draw rows: {summary['draw_row_count']}",
        f"- Selection updates: {summary['selection_update_count']}",
        "",
        "## Classification",
        "",
    ]
    lines.extend(f"- {item}" for item in summary["classification"])
    if screenshot:
        lines.extend(
            [
                "",
                "## Diagnostic Screenshot",
                "",
                "This CDB/proxy frame is hit-test/control-flow evidence only. Do not use it as visual acceptance proof for the final right-bottom action menu layout.",
                "",
                f"![right-bottom controlled grid hit]({screenshot})",
            ]
        )
    lines.extend(["", "## Key Rows", ""])
    for row in summary["rows"][-18:]:
        lines.append(f"- line {row['line']}: `{row['text']}`")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log", type=Path)
    parser.add_argument("--expected-entry", default="450,73")
    parser.add_argument("--expected-result", type=int, default=0)
    parser.add_argument("--write-json", type=Path)
    parser.add_argument("--write-md", type=Path)
    parser.add_argument("--screenshot")
    parser.add_argument("--require-ready", action="store_true")
    parser.add_argument("--require-grid-hit", action="store_true")
    parser.add_argument("--require-draw-rows", action="store_true")
    parser.add_argument("--forbid-failure-exit", action="store_true")
    args = parser.parse_args()

    expected_entry = [int(part.strip(), 0) for part in args.expected_entry.split(",")]
    summary = parse_log(args.log, expected_entry, args.expected_result)
    if args.screenshot:
        summary["screenshot"] = args.screenshot
    if args.write_json:
        args.write_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    if args.write_md:
        write_markdown(summary, args.write_md, args.screenshot)

    print(
        "ready={ready} grid_hit_ok={grid_hit_ok} last_grid_entry={entry} "
        "last_grid_result={result} forced_gate_count={forced_gate_count} "
        "failure_exits={failure_exits} draw_rows={draw_rows} av_count={av}".format(
            ready=summary["ready"],
            grid_hit_ok=summary["grid_hit_ok"],
            entry=summary["last_grid_entry"],
            result=summary["last_grid_result"],
            forced_gate_count=summary["forced_gate_count"],
            failure_exits=summary["failure_exit_count"],
            draw_rows=summary["draw_row_count"],
            av=summary["av_count"],
        )
    )
    for item in summary["classification"]:
        print(f"- {item}")

    if args.require_ready and not summary["ready"]:
        print("required surface-ready marker was not observed", file=sys.stderr)
        return 2
    if args.require_grid_hit and not summary["grid_hit_ok"]:
        print("required grid hit proof was not observed", file=sys.stderr)
        return 2
    if args.require_draw_rows and summary["draw_row_count"] <= 0:
        print("required draw rows were not observed", file=sys.stderr)
        return 2
    if args.forbid_failure_exit and summary["failure_exit_count"]:
        print("failure exit rows were observed", file=sys.stderr)
        return 2
    if summary["av_count"]:
        print("access violation rows were observed", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
