#!/usr/bin/env python3
"""Summarize Clash95 castle barracks/action-panel CDB probe logs."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


MARKERS = (
    "APBARRACKS_OWNER_SETUP_CALL",
    "APBARRACKS_OWNER_FLAG_FORCED",
    "APBARRACKS_433C20_ENTRY",
    "APBARRACKS_WRITE_532150",
    "APBARRACKS_WRITE_53214C",
    "APBARRACKS_WRITE_532154",
    "APBARRACKS_ACTION_CALL",
    "APBARRACKS_433914_CALL_435BC0",
    "APBARRACKS_OWNER_435BC0_ENTRY",
    "APBARRACKS_WRITE_532218",
    "APBARRACKS_WRITE_5322C8",
    "APBARRACKS_SELECT_FORCED",
    "APBARRACKS_PANEL_DRAW_4347A0",
    "APBARRACKS_GRID_DRAW_434E20",
    "APBARRACKS_STATUS_DRAW_435280",
    "APBARRACKS_ACTION_BOX_435500",
    "APBARRACKS_ACTION_BOX_SET_TARGET",
    "APBARRACKS_ACTION_BOX_AFTER_BACKUP",
    "APBARRACKS_ACTION_BOX_BEFORE_RESTORE",
    "APBARRACKS_AFTER_ACTION_BOX",
    "APBARRACKS_COPYBACK_SET_TARGET",
    "APBARRACKS_COPYBACK_AFTER_CALL",
    "APBARRACKS_OWNER_POLL_EXIT_ARM",
    "APBARRACKS_SURFDUMP_READY",
    "SURFDUMP_READY",
)

KV_RE = re.compile(
    r"(?P<key>[A-Za-z_][A-Za-z0-9_]*)="
    r"(?P<value>\([^)]*\)|[^\s]+)"
)


def parse_value(value: str) -> Any:
    value = value.strip()
    if value.startswith("(") and value.endswith(")"):
        parts = [part.strip() for part in value[1:-1].split(",") if part.strip()]
        return [parse_value(part) for part in parts]
    if value.lower() in {"true", "false"}:
        return value.lower() == "true"
    try:
        return int(value, 0)
    except ValueError:
        return value


def parse_log(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    marker_counts = {marker: 0 for marker in MARKERS}
    rows: list[dict[str, Any]] = []
    av_rows: list[dict[str, Any]] = []

    marker_re = re.compile("|".join(re.escape(marker) for marker in MARKERS))

    for index, line in enumerate(lines, start=1):
        if "Access violation" in line or "code c0000005" in line.lower():
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

    panel_rows = [row for row in rows if row["marker"] == "APBARRACKS_PANEL_DRAW_4347A0"]
    selected_addons = [
        row["values"].get("selected_addon")
        for row in rows
        if "selected_addon" in row["values"]
    ]
    selected_addons = [value for value in selected_addons if isinstance(value, int)]

    classification: list[str] = []
    if marker_counts["APBARRACKS_OWNER_SETUP_CALL"] and marker_counts["APBARRACKS_WRITE_532154"]:
        classification.append("owner setup globals were installed for the castle action path")
    else:
        classification.append("owner setup globals were not fully observed")
    if marker_counts["APBARRACKS_433914_CALL_435BC0"] and marker_counts["APBARRACKS_OWNER_435BC0_ENTRY"]:
        classification.append("castle action-panel routine 00435BC0 was reached")
    else:
        classification.append("castle action-panel routine 00435BC0 was not reached")
    if marker_counts["APBARRACKS_PANEL_DRAW_4347A0"] and marker_counts["APBARRACKS_GRID_DRAW_434E20"]:
        classification.append("detail panel and 12-slot grid draw functions executed")
    else:
        classification.append("detail panel or grid draw evidence is missing")
    if marker_counts["APBARRACKS_ACTION_BOX_435500"]:
        classification.append("bottom action box draw function executed")
    else:
        classification.append("bottom action box draw function was not observed")
    if marker_counts["APBARRACKS_SURFDUMP_READY"] or marker_counts["SURFDUMP_READY"]:
        classification.append("surface dump reached ready state")
    else:
        classification.append("surface dump did not reach ready state")

    return {
        "log": str(path),
        "marker_counts": marker_counts,
        "row_count": len(rows),
        "panel_row_count": len(panel_rows),
        "selected_addons": selected_addons,
        "last_selected_addon": selected_addons[-1] if selected_addons else None,
        "av_count": len(av_rows),
        "av_rows": av_rows,
        "classification": classification,
        "rows": rows,
    }


def write_markdown(summary: dict[str, Any], path: Path, screenshot: str | None) -> None:
    counts = summary["marker_counts"]
    lines = [
        "# Castle Barracks UI Probe",
        "",
        f"- Log: `{summary['log']}`",
        f"- Rows parsed: {summary['row_count']}",
        f"- Access violations: {summary['av_count']}",
        f"- Last selected addon id: {summary['last_selected_addon']}",
        "",
        "## Classification",
        "",
    ]
    lines += [f"- {item}" for item in summary["classification"]]
    lines += ["", "## Marker Counts", ""]
    lines += [f"- {marker}: {count}" for marker, count in counts.items()]
    if screenshot:
        lines += ["", "## Screenshot", "", f"![castle barracks UI]({screenshot})"]
    lines += ["", "## Key Rows", ""]
    for row in summary["rows"][-12:]:
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
    parser.add_argument("--require-panel", action="store_true")
    args = parser.parse_args()

    summary = parse_log(args.log)
    if args.screenshot:
        summary["screenshot"] = args.screenshot
    if args.write_json:
        args.write_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    if args.write_md:
        write_markdown(summary, args.write_md, args.screenshot)

    print(
        "ready={ready} panel={panel} action_box={action_box} av_count={av} "
        "last_selected_addon={addon}".format(
            ready=bool(
                summary["marker_counts"]["APBARRACKS_SURFDUMP_READY"]
                or summary["marker_counts"]["SURFDUMP_READY"]
            ),
            panel=bool(summary["marker_counts"]["APBARRACKS_PANEL_DRAW_4347A0"]),
            action_box=bool(summary["marker_counts"]["APBARRACKS_ACTION_BOX_435500"]),
            av=summary["av_count"],
            addon=summary["last_selected_addon"],
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
    if args.require_panel and not (
        summary["marker_counts"]["APBARRACKS_PANEL_DRAW_4347A0"]
        and summary["marker_counts"]["APBARRACKS_GRID_DRAW_434E20"]
        and summary["marker_counts"]["APBARRACKS_ACTION_BOX_435500"]
    ):
        print("required panel/grid/action-box markers were not observed", file=sys.stderr)
        return 2
    if summary["av_count"]:
        print("access violation rows were observed", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
