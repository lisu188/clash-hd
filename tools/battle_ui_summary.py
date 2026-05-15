#!/usr/bin/env python3
"""Summarize Clash95 battle UI CDB probe logs.

The parser is deliberately evidence-driven. It accepts either a capture
directory containing ``cdb-surface-dump.log`` or a direct log path, and it only
classifies battle UI readiness from machine-readable ``BATTLE_*`` rows. It does
not launch Clash95, CDB, wrappers, PowerShell, or visible windows.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


MARKERS = (
    "BATTLE_READY",
    "BATTLE_OWNER_ENTRY",
    "BATTLE_DRAW_ENTRY",
    "BATTLE_SURFACE",
    "BATTLE_PRESENT_CALL",
    "BATTLE_COPYBACK_CALL",
    "BATTLE_DESCRIPTOR",
    "BATTLE_COMMAND_HIT",
    "BATTLE_GRID_HIT",
    "BATTLE_MODAL_HIT",
    "BATTLE_MODAL_CLASSIFIED",
    "BATTLE_ROUTE_CANDIDATE",
    "BATTLE_INPUT_SCAN",
    "BATTLE_AV",
    "BATTLE_DONE",
    "SURFDUMP_READY",
)

KV_RE = re.compile(r"(?P<key>[A-Za-z_][A-Za-z0-9_]*)=(?P<value>\([^)]*\)|[^\s]+)")
MARKER_RE = re.compile("|".join(re.escape(marker) for marker in MARKERS))


def capture_paths(path: Path) -> tuple[Path, Path | None, Path | None]:
    if path.is_dir():
        summary = path / "summary.json"
        screenshot = path / "surface.png"
        return path / "cdb-surface-dump.log", summary if summary.exists() else None, screenshot if screenshot.exists() else None
    return path, None, None


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
        if "access violation" in lowered or "code c0000005" in lowered or "BATTLE_AV" in line:
            av_rows.append({"line": line_no, "text": line.strip()})
        matches = list(MARKER_RE.finditer(line))
        for index, match in enumerate(matches):
            marker = match.group(0)
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


def load_summary_json(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}


def first_present(values: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in values:
            return values[key]
    return None


def last_row(rows: list[dict[str, Any]], marker: str) -> dict[str, Any] | None:
    for row in reversed(rows):
        if row["marker"] == marker:
            return row
    return None


def surface_size_from_ready(row: dict[str, Any] | None) -> list[int] | None:
    if row is None:
        return None
    values = row.get("values", {})
    if "size" in values:
        return values["size"]
    width = values.get("width")
    height = values.get("height")
    if isinstance(width, int) and isinstance(height, int):
        return [width, height]
    return None


def build_summary(path: Path) -> dict[str, Any]:
    log_path, summary_path, screenshot = capture_paths(path)
    text = ""
    missing_log = False
    if log_path.exists():
        text = log_path.read_text(encoding="utf-8", errors="replace")
    else:
        missing_log = True
    rows, av_rows = parse_rows(text)
    marker_counts = {marker: 0 for marker in MARKERS}
    for row in rows:
        marker_counts[row["marker"]] += 1

    run_summary = load_summary_json(summary_path)
    battle_markers = [
        marker
        for marker in MARKERS
        if marker.startswith("BATTLE_") and marker not in {"BATTLE_ROUTE_CANDIDATE", "BATTLE_AV"}
    ]
    battle_reached = any(marker_counts[marker] for marker in battle_markers)
    battle_ready = marker_counts["BATTLE_READY"] > 0
    command_descriptor_found = marker_counts["BATTLE_DESCRIPTOR"] > 0
    command_hit_ok = marker_counts["BATTLE_COMMAND_HIT"] > 0
    grid_hit_ok = marker_counts["BATTLE_GRID_HIT"] > 0
    modal_hit = marker_counts["BATTLE_MODAL_HIT"] > 0
    modal_classified = marker_counts["BATTLE_MODAL_CLASSIFIED"] > 0
    no_av = not av_rows

    battle_surface = last_row(rows, "BATTLE_SURFACE")
    surfdump_ready = last_row(rows, "SURFDUMP_READY")
    surface_size = surface_size_from_ready(battle_surface) or surface_size_from_ready(surfdump_ready)
    visual_mode = "unknown"
    centered_offset = None
    if battle_surface is not None:
        values = battle_surface["values"]
        if values.get("mode") == "centered-native" or values.get("offset") == [80, 60]:
            visual_mode = "centered-native-640x480"
            centered_offset = values.get("offset", [80, 60])
        elif surface_size == [800, 600]:
            visual_mode = "hd-surface-unclassified"
        elif surface_size == [640, 480]:
            visual_mode = "native-640x480-unclassified"

    classification: list[str] = []
    if missing_log:
        classification.append(f"missing log: {log_path}")
    if battle_ready:
        classification.append("battle ready marker observed")
    elif battle_reached:
        classification.append("battle route rows observed but no BATTLE_READY marker")
    else:
        classification.append("battle route was not reached")
    if surface_size:
        classification.append(f"surface size classified as {surface_size}")
    else:
        classification.append("battle surface size was not classified")
    if visual_mode == "centered-native-640x480":
        classification.append("centered native battle visual offset is present")
    elif visual_mode == "unknown":
        classification.append("battle visual mode is unknown")
    if command_descriptor_found:
        classification.append("battle command descriptor row observed")
    else:
        classification.append("battle command descriptor was not observed")
    if command_hit_ok:
        classification.append("battle command hit row observed")
    else:
        classification.append("battle command hit proof was not observed")
    if grid_hit_ok:
        classification.append("battle tactical-grid hit row observed")
    else:
        classification.append("battle tactical-grid hit proof was not observed")
    if modal_hit:
        classification.append("battle modal hit row observed")
    elif modal_classified:
        classification.append("battle modal path was classified without a hit")
    else:
        classification.append("battle modal path was not classified")
    if no_av:
        classification.append("no access violation rows observed")
    else:
        classification.append("access violation rows observed")

    return {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "input": str(path),
        "log": str(log_path),
        "summary_json": str(summary_path) if summary_path else None,
        "screenshot": str(screenshot) if screenshot else None,
        "runtime_policy": "repo-only parser; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows",
        "candidate": first_present(run_summary, "Candidate", "candidate"),
        "candidate_sha256": first_present(run_summary, "CandidateSha256", "CandidateSHA256", "candidate_sha256"),
        "launch_mode": first_present(run_summary, "LaunchMode", "launch_mode"),
        "hidden_desktop": first_present(run_summary, "HiddenDesktop", "hidden_desktop"),
        "allow_visible_desktop": first_present(run_summary, "AllowVisibleDesktop", "allow_visible_desktop"),
        "marker_counts": marker_counts,
        "row_count": len(rows),
        "rows": rows,
        "av_count": len(av_rows),
        "av_rows": av_rows,
        "battle_reached": battle_reached,
        "battle_ready": battle_ready,
        "surface_size": surface_size,
        "visual_mode": visual_mode,
        "centered_offset": centered_offset,
        "command_descriptor_found": command_descriptor_found,
        "command_hit_ok": command_hit_ok,
        "grid_hit_ok": grid_hit_ok,
        "modal_hit": modal_hit,
        "modal_classified": modal_classified,
        "no_av": no_av,
        "last_battle_surface": battle_surface,
        "last_command_hit": last_row(rows, "BATTLE_COMMAND_HIT"),
        "last_grid_hit": last_row(rows, "BATTLE_GRID_HIT"),
        "last_modal_hit": last_row(rows, "BATTLE_MODAL_HIT"),
        "classification": classification,
    }


def write_markdown(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# Battle UI Probe Summary",
        "",
        f"- Generated: `{summary['generated_at']}`",
        f"- Runtime policy: {summary['runtime_policy']}",
        f"- Log: `{summary['log']}`",
        f"- Candidate: `{summary.get('candidate')}`",
        f"- Candidate SHA-256: `{summary.get('candidate_sha256')}`",
        f"- Launch mode: `{summary.get('launch_mode')}`",
        f"- Hidden desktop: `{summary.get('hidden_desktop')}`",
        f"- Rows parsed: `{summary['row_count']}`",
        f"- Access violations: `{summary['av_count']}`",
        f"- Battle reached: `{summary['battle_reached']}`",
        f"- Battle ready: `{summary['battle_ready']}`",
        f"- Surface size: `{summary['surface_size']}`",
        f"- Visual mode: `{summary['visual_mode']}`",
        f"- Centered offset: `{summary['centered_offset']}`",
        f"- Command descriptor found: `{summary['command_descriptor_found']}`",
        f"- Command hit ok: `{summary['command_hit_ok']}`",
        f"- Grid hit ok: `{summary['grid_hit_ok']}`",
        f"- Modal classified: `{summary['modal_hit'] or summary['modal_classified']}`",
        "",
        "## Classification",
        "",
    ]
    lines.extend(f"- {item}" for item in summary["classification"])
    if summary.get("screenshot"):
        lines.extend(["", "## Screenshot", "", f"![battle UI surface]({summary['screenshot']})"])
    lines.extend(["", "## Recent Rows", ""])
    for row in summary["rows"][-25:]:
        lines.append(f"- line {row['line']}: `{row['text']}`")
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture_or_log", type=Path)
    parser.add_argument("--write-json", type=Path)
    parser.add_argument("--write-markdown", "--write-md", dest="write_markdown", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary = build_summary(args.capture_or_log)
    print(f"battle-reached: {summary['battle_reached']}")
    print(f"battle-ready: {summary['battle_ready']}")
    print(f"surface-size: {summary['surface_size']}")
    print(f"visual-mode: {summary['visual_mode']}")
    print(f"command-hit-ok: {summary['command_hit_ok']}")
    print(f"grid-hit-ok: {summary['grid_hit_ok']}")
    print(f"av-count: {summary['av_count']}")
    if args.write_json:
        args.write_json.parent.mkdir(parents=True, exist_ok=True)
        args.write_json.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    if args.write_markdown:
        write_markdown(args.write_markdown, summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
