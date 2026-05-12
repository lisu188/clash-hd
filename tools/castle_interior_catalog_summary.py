#!/usr/bin/env python3
"""Summarize Clash95 castle interior descriptor catalog CDB probes."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


MARKERS = (
    "CASTLECAT_INVOKE_PLAYGAME",
    "CASTLECAT_SCREEN_FULL_ENTRY",
    "CASTLECAT_OWNER_SET",
    "CASTLECAT_OVERVIEW_ALLOC_INITIAL",
    "CASTLECAT_OVERVIEW_ALLOC_ACTION",
    "CASTLECAT_OVERVIEW_WRAPPER_ENTRY",
    "CASTLECAT_OVERVIEW_CENTERED_MOUSE_SET",
    "CASTLECAT_OVERVIEW_DESC_INPUT_WRAPPER_ENTRY",
    "CASTLECAT_OVERVIEW_SURFACE_HIT_WRAPPER_ENTRY",
    "CASTLECAT_RENDERHOOK_DRAW",
    "CASTLECAT_OVERVIEW_POST_DRAW",
    "CASTLECAT_OVERVIEW_ACTION_POST_DRAW",
    "CASTLECAT_FORCE_HITTEST",
    "CASTLECAT_BRANCH",
    "CASTLECAT_DESCRIPTOR_INSTALL",
    "CASTLECAT_CLICK_GATE",
    "CASTLECAT_CALLBACK_CALL",
    "CASTLECAT_SURFDUMP_READY",
    "SURFDUMP_READY",
    "SURFDUMP_HOST_READY",
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
        if re.fullmatch(r"[0-9A-Fa-f]{6,8}", value):
            return int(value, 16)
        return value


def parse_log(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="replace")
    marker_counts = {marker: 0 for marker in MARKERS}
    marker_re = re.compile("|".join(re.escape(marker) for marker in MARKERS))
    rows: list[dict[str, Any]] = []
    av_rows: list[dict[str, Any]] = []

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

    descriptor_rows = [row for row in rows if row["marker"] == "CASTLECAT_DESCRIPTOR_INSTALL"]
    branch_rows = [row for row in rows if row["marker"] == "CASTLECAT_BRANCH"]
    forced_rows = [row for row in rows if row["marker"] == "CASTLECAT_FORCE_HITTEST"]
    overview_post_rows = [
        row
        for row in rows
        if row["marker"] in {
            "CASTLECAT_OVERVIEW_POST_DRAW",
            "CASTLECAT_OVERVIEW_ACTION_POST_DRAW",
        }
    ]
    surface_rows = [row for row in rows if row["marker"] in {"CASTLECAT_SURFDUMP_READY", "SURFDUMP_READY"}]

    descriptors = []
    seen: set[tuple[int, int]] = set()
    for row in descriptor_rows:
        command = row["values"].get("command")
        callback = row["values"].get("callback")
        if not isinstance(command, int) or not isinstance(callback, int):
            continue
        key = (command, callback)
        if key in seen:
            continue
        seen.add(key)
        descriptors.append(
            {
                "command": command,
                "command_hex": f"0x{command:02X}",
                "callback": callback,
                "callback_hex": f"0x{callback:08X}",
                "text": row["values"].get("text"),
                "owner_flag": row["values"].get("owner_flag"),
                "first_line": row["line"],
            }
        )

    commands = sorted({item["command"] for item in descriptors})
    callbacks = sorted({item["callback"] for item in descriptors})
    last_surface = surface_rows[-1]["values"] if surface_rows else {}

    classification: list[str] = []
    if marker_counts["CASTLECAT_INVOKE_PLAYGAME"]:
        classification.append("controlled castle-screen invocation was attempted")
    else:
        classification.append("controlled castle-screen invocation was not observed")
    if descriptor_rows:
        classification.append(f"cataloged {len(descriptors)} unique castle descriptor callbacks")
    else:
        classification.append("no castle descriptor callbacks were cataloged")
    if surface_rows:
        classification.append("surface dump reached ready state")
    else:
        classification.append("surface dump did not reach ready state")
    if overview_post_rows:
        last_overview_size = overview_post_rows[-1]["values"].get("main_size")
        classification.append(f"overview redraw finished on main surface size {last_overview_size}")
    else:
        classification.append("overview redraw post-draw marker was not observed")
    if last_surface.get("size") == [800, 600]:
        classification.append("catalog finished on an 800x600 surface")
    elif last_surface.get("surface"):
        classification.append(f"catalog finished on surface size {last_surface.get('size')}")
    if av_rows:
        classification.append("AV observed")

    return {
        "log": str(path),
        "marker_counts": marker_counts,
        "row_count": len(rows),
        "av_count": len(av_rows),
        "av_rows": av_rows,
        "forced_hit_count": len(forced_rows),
        "overview_post_draw_count": len(overview_post_rows),
        "last_overview_post_draw": overview_post_rows[-1]["values"] if overview_post_rows else {},
        "branch_count": len(branch_rows),
        "descriptor_row_count": len(descriptor_rows),
        "descriptors": descriptors,
        "commands": commands,
        "commands_hex": [f"0x{command:02X}" for command in commands],
        "callbacks": callbacks,
        "callbacks_hex": [f"0x{callback:08X}" for callback in callbacks],
        "last_surface": last_surface,
        "classification": classification,
        "rows": rows,
    }


def write_markdown(summary: dict[str, Any], path: Path, screenshot: str | None) -> None:
    lines = [
        "# Castle Interior Descriptor Catalog",
        "",
        f"- Log: `{summary['log']}`",
        f"- Rows parsed: {summary['row_count']}",
        f"- Forced hit-test rows: {summary['forced_hit_count']}",
        f"- Unique descriptors: {len(summary['descriptors'])}",
        f"- Commands: {', '.join(summary['commands_hex']) or 'none'}",
        f"- Access violations: {summary['av_count']}",
        "",
        "## Classification",
        "",
    ]
    lines.extend(f"- {item}" for item in summary["classification"])
    lines.extend(["", "## Descriptors", ""])
    if summary["descriptors"]:
        lines.append("| Command | Callback | First Line | Notes |")
        lines.append("| --- | --- | ---: | --- |")
        for item in summary["descriptors"]:
            lines.append(
                "| `{command}` | `{callback}` | {line} | owner_flag `{flag}` text `{text}` |".format(
                    command=item["command_hex"],
                    callback=item["callback_hex"],
                    line=item["first_line"],
                    flag=item.get("owner_flag"),
                    text=item.get("text"),
                )
            )
    else:
        lines.append("- none")
    if screenshot:
        lines.extend(["", "## Screenshot", "", f"![castle interior catalog]({screenshot})"])
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_command(value: str) -> int:
    return int(value, 0)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log", type=Path)
    parser.add_argument("--write-json", type=Path)
    parser.add_argument("--write-md", type=Path)
    parser.add_argument("--screenshot")
    parser.add_argument("--require-ready", action="store_true")
    parser.add_argument("--require-800x600", action="store_true")
    parser.add_argument("--require-command", type=parse_command, action="append", default=[])
    args = parser.parse_args()

    summary = parse_log(args.log)
    if args.screenshot:
        summary["screenshot"] = args.screenshot
    if args.write_json:
        args.write_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    if args.write_md:
        write_markdown(summary, args.write_md, args.screenshot)

    print(
        "ready={ready} surface_size={surface_size} descriptors={descriptors} "
        "commands={commands} av_count={av}".format(
            ready=bool(
                summary["marker_counts"]["CASTLECAT_SURFDUMP_READY"]
                or summary["marker_counts"]["SURFDUMP_READY"]
            ),
            surface_size=summary["last_surface"].get("size"),
            descriptors=len(summary["descriptors"]),
            commands=",".join(summary["commands_hex"]) or "none",
            av=summary["av_count"],
        )
    )
    for item in summary["classification"]:
        print(f"- {item}")

    if args.require_ready and not (
        summary["marker_counts"]["CASTLECAT_SURFDUMP_READY"]
        or summary["marker_counts"]["SURFDUMP_READY"]
    ):
        print("required surface-ready marker was not observed", file=sys.stderr)
        return 2
    if args.require_800x600 and summary["last_surface"].get("size") != [800, 600]:
        print("required 800x600 surface was not observed", file=sys.stderr)
        return 2
    missing_commands = [
        command for command in args.require_command if command not in summary["commands"]
    ]
    if missing_commands:
        print(
            "required command(s) were not cataloged: "
            + ", ".join(f"0x{command:02X}" for command in missing_commands),
            file=sys.stderr,
        )
        return 2
    if summary["av_count"]:
        print("access violation rows were observed", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
