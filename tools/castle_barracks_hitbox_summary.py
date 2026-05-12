#!/usr/bin/env python3
"""Summarize Clash95 centered castle/barracks hitbox CDB probe logs."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


MARKERS = (
    "APBARRACKS_HITBOX_FORCE_CENTERED",
    "APBARRACKS_HITBOX_OWNER_NATIVE",
    "APBARRACKS_HITBOX_OWNER_RESTORED",
    "APBARRACKS_HITBOX_DESCRIPTOR_RESULT",
    "APBARRACKS_HITBOX_CLICK_STATE",
    "APBARRACKS_HITBOX_GRID_GATE",
    "APBARRACKS_HITBOX_GRID_ENTRY",
    "APBARRACKS_HITBOX_GRID_RESULT",
    "APBARRACKS_HITBOX_GRID_ACCEPT",
    "APBARRACKS_HITBOX_GRID_FAIL",
    "APBARRACKS_HITBOX_SELECTION_UPDATE",
    "APBARRACKS_HITBOX_SELECTION_AFTER",
    "APBARRACKS_HITBOX_EXIT_ARM",
    "APBARRACKS_SURFDUMP_READY",
    "SURFDUMP_READY",
)

KV_RE = re.compile(
    r"(?P<key>[A-Za-z_][A-Za-z0-9_]*)="
    r"(?P<value>\([^)]*\)|[^\s]+)"
)


def parse_value(value: str) -> Any:
    value = value.strip().rstrip(",")
    if value.startswith("(") and value.endswith(")"):
        parts = [part.strip() for part in value[1:-1].split(",") if part.strip()]
        return [parse_value(part) for part in parts]
    try:
        return int(value, 0)
    except ValueError:
        return value


def parse_log(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="replace")
    marker_counts = {marker: 0 for marker in MARKERS}
    rows: list[dict[str, Any]] = []
    av_rows: list[dict[str, Any]] = []
    marker_re = re.compile("|".join(re.escape(marker) for marker in MARKERS))

    for index, line in enumerate(text.splitlines(), start=1):
        lowered = line.lower()
        if "access violation" in lowered or "code c0000005" in lowered:
            av_rows.append({"line": index, "text": line.strip()})

        matches = list(marker_re.finditer(line))
        for match_index, match in enumerate(matches):
            marker = match.group(0)
            end = matches[match_index + 1].start() if match_index + 1 < len(matches) else len(line)
            fragment = line[match.start() : end].strip()
            marker_counts[marker] += 1
            values = {m.group("key"): parse_value(m.group("value")) for m in KV_RE.finditer(fragment)}
            rows.append(
                {
                    "line": index,
                    "marker": marker,
                    "values": values,
                    "text": fragment,
                }
            )

    grid_results: list[Any] = []
    grid_entries: list[Any] = []
    grid_hit_proofs: list[dict[str, Any]] = []
    current_grid_entry: Any = None
    for row in rows:
        if row["marker"] == "APBARRACKS_HITBOX_GRID_ENTRY":
            current_grid_entry = row["values"].get("mouse")
            grid_entries.append(current_grid_entry)
        elif row["marker"] == "APBARRACKS_HITBOX_GRID_RESULT":
            result = row["values"].get("result")
            grid_results.append(result)
            if current_grid_entry == [450, 73] and result == 0:
                grid_hit_proofs.append(
                    {
                        "entry": current_grid_entry,
                        "result": result,
                        "line": row["line"],
                    }
                )
    selection_updates = [
        row for row in rows if row["marker"] == "APBARRACKS_HITBOX_SELECTION_UPDATE"
    ]
    gate_rows = [
        row for row in rows if row["marker"] == "APBARRACKS_HITBOX_GRID_GATE"
    ]
    raw_gate_ok = any(row["values"].get("raw_result") == 1 for row in gate_rows)
    forced_gate_rows = [
        row
        for row in gate_rows
        if str(row["values"].get("forced_result", "none")).lower()
        not in {"none", "0", "false"}
    ]

    last_grid_result = grid_results[-1] if grid_results else None
    last_grid_entry = grid_entries[-1] if grid_entries else None

    grid_hit_ok = bool(grid_hit_proofs)
    classification: list[str] = []
    if marker_counts["APBARRACKS_HITBOX_FORCE_CENTERED"]:
        classification.append("forced centered coordinate was installed")
    else:
        classification.append("forced centered coordinate was not observed")
    if marker_counts["APBARRACKS_HITBOX_OWNER_NATIVE"]:
        classification.append("owner-poll wrapper transformed the coordinate to native space")
    else:
        classification.append("owner-poll native transform was not observed")
    if marker_counts["APBARRACKS_HITBOX_GRID_ENTRY"]:
        classification.append("barracks grid hit-test was reached")
    else:
        classification.append("barracks grid hit-test was not reached")
    if gate_rows and raw_gate_ok:
        classification.append("grid route gate passed from raw input/click state")
    elif gate_rows:
        classification.append("grid route gate did not pass from raw input/click state")
    if forced_gate_rows:
        classification.append("grid route gate was debugger-forced")
    elif gate_rows:
        classification.append("grid route gate was not debugger-forced")
    if grid_hit_ok:
        classification.append("grid hit-test returned expected cell 0 at native coordinate 450,73")
    else:
        classification.append("grid hit-test did not prove expected cell 0 at native coordinate 450,73")
    if marker_counts["APBARRACKS_HITBOX_GRID_ACCEPT"]:
        classification.append("grid result was accepted and the probe armed loop exit")
    if selection_updates:
        classification.append("grid selection update was observed")
    else:
        classification.append("grid selection update was not observed")
    if marker_counts["APBARRACKS_SURFDUMP_READY"] or marker_counts["SURFDUMP_READY"]:
        classification.append("surface dump reached ready state")
    else:
        classification.append("surface dump did not reach ready state")

    return {
        "log": str(path),
        "marker_counts": marker_counts,
        "row_count": len(rows),
        "av_count": len(av_rows),
        "av_rows": av_rows,
        "last_grid_result": last_grid_result,
        "last_grid_entry": last_grid_entry,
        "gate_rows": gate_rows,
        "raw_gate_ok": raw_gate_ok,
        "forced_gate_count": len(forced_gate_rows),
        "grid_hit_proofs": grid_hit_proofs,
        "grid_hit_ok": grid_hit_ok,
        "selection_update_count": len(selection_updates),
        "classification": classification,
        "rows": rows,
    }


def write_markdown(summary: dict[str, Any], path: Path, screenshot: str | None) -> None:
    lines = [
        "# Castle Barracks Centered Hitbox Probe",
        "",
        f"- Log: `{summary['log']}`",
        f"- Rows parsed: {summary['row_count']}",
        f"- Access violations: {summary['av_count']}",
        f"- Last grid entry: `{summary['last_grid_entry']}`",
        f"- Last grid result: `{summary['last_grid_result']}`",
        f"- Raw grid gate ok: {summary['raw_gate_ok']}",
        f"- Forced grid gates: {summary['forced_gate_count']}",
        f"- Grid hit ok: {summary['grid_hit_ok']}",
        f"- Selection updates: {summary['selection_update_count']}",
        "",
        "## Classification",
        "",
    ]
    lines += [f"- {item}" for item in summary["classification"]]
    if screenshot:
        lines += ["", "## Screenshot", "", f"![castle barracks centered hitbox]({screenshot})"]
    lines += ["", "## Key Rows", ""]
    for row in summary["rows"][-16:]:
        lines.append(f"- line {row['line']}: `{row['text']}`")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log", type=Path)
    parser.add_argument("--write-json", type=Path)
    parser.add_argument("--write-md", type=Path)
    parser.add_argument("--screenshot")
    parser.add_argument("--require-ready", action="store_true")
    parser.add_argument("--require-raw-gate", action="store_true")
    parser.add_argument("--forbid-forced-gate", action="store_true")
    parser.add_argument("--require-grid-hit", action="store_true")
    parser.add_argument("--require-selection-update", action="store_true")
    args = parser.parse_args()

    summary = parse_log(args.log)
    if args.screenshot:
        summary["screenshot"] = args.screenshot
    if args.write_json:
        args.write_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    if args.write_md:
        write_markdown(summary, args.write_md, args.screenshot)

    print(
        "ready={ready} grid_hit_ok={grid_hit_ok} last_grid_entry={entry} "
        "last_grid_result={result} raw_gate_ok={raw_gate_ok} "
        "forced_gate_count={forced_gate_count} selection_updates={updates} "
        "av_count={av}".format(
            ready=bool(
                summary["marker_counts"]["APBARRACKS_SURFDUMP_READY"]
                or summary["marker_counts"]["SURFDUMP_READY"]
            ),
            grid_hit_ok=summary["grid_hit_ok"],
            entry=summary["last_grid_entry"],
            result=summary["last_grid_result"],
            raw_gate_ok=summary["raw_gate_ok"],
            forced_gate_count=summary["forced_gate_count"],
            updates=summary["selection_update_count"],
            av=summary["av_count"],
        )
    )
    for item in summary["classification"]:
        print(f"- {item}")

    if args.require_ready and not (
        summary["marker_counts"]["APBARRACKS_SURFDUMP_READY"]
        or summary["marker_counts"]["SURFDUMP_READY"]
    ):
        print("required surface-ready marker was not observed", file=sys.stderr)
        return 2
    if args.require_grid_hit and not summary["grid_hit_ok"]:
        print("required grid hit proof was not observed", file=sys.stderr)
        return 2
    if args.require_raw_gate and not summary["raw_gate_ok"]:
        print("required raw grid route gate pass was not observed", file=sys.stderr)
        return 2
    if args.forbid_forced_gate and summary["forced_gate_count"]:
        print("debugger-forced grid route gate rows were observed", file=sys.stderr)
        return 2
    if args.require_selection_update and summary["selection_update_count"] <= 0:
        print("required selection update was not observed", file=sys.stderr)
        return 2
    if summary["av_count"]:
        print("access violation rows were observed", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
