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
    "BATTLE_COMMAND_ATTEMPT",
    "BATTLE_COMMAND_RESULT",
    "BATTLE_COMMAND_FORCE_ENABLED_UNIT",
    "BATTLE_COMMAND_CLICK_GATE_FORCE",
    "BATTLE_COMMAND_CLICK_GATE_OBSERVED",
    "BATTLE_COMMAND_REARM_PRE_GATES",
    "BATTLE_COMMAND_PRE_GATES",
    "BATTLE_COMMAND_DESCRIPTOR_CALLBACK",
    "BATTLE_COMMAND_RENDER_BEGIN_ENTER",
    "BATTLE_COMMAND_RENDER_BEGIN_SKIP",
    "BATTLE_COMMAND_SYNTHETIC_RELEASE",
    "BATTLE_RENDER_BEGIN_ENTER",
    "BATTLE_RENDER_BEGIN_LOOP",
    "BATTLE_RENDER_BEGIN_SPIN_GUARD",
    "BATTLE_RENDER_BEGIN_LOST_CHECK",
    "BATTLE_RENDER_BEGIN_LOST_GUARD",
    "BATTLE_RENDER_BEGIN_EXIT",
    "BATTLE_COMMAND_CALLBACK_RESULT",
    "BATTLE_COMMAND_CALLBACK",
    "BATTLE_COMMAND_SKIP_TURN_BANNER",
    "BATTLE_COMMAND_SKIP_TURN_FRAME",
    "BATTLE_COMMAND_HIT",
    "BATTLE_COMMAND_NATIVE_HIT",
    "BATTLE_GRID_ATTEMPT",
    "BATTLE_GRID_RESULT",
    "BATTLE_GRID_HIT",
    "BATTLE_POSTREADY_PRESENT",
    "BATTLE_POSTREADY_COPYBACK",
    "BATTLE_POSTREADY_GRID_ATTEMPT",
    "BATTLE_POSTREADY_SUMMARY",
    "BATTLE_INPUTPROBE_GRID_PRE",
    "BATTLE_INPUTPROBE_GRID_CAVE_ENTRY",
    "BATTLE_INPUTPROBE_GRID_INNER",
    "BATTLE_INPUTPROBE_GRID_POST",
    "BATTLE_INPUTPROBE_DESCRIPTOR_PRE",
    "BATTLE_INPUTPROBE_DESCRIPTOR_CAVE_ENTRY",
    "BATTLE_INPUTPROBE_DESCRIPTOR_INNER",
    "BATTLE_INPUTPROBE_DESCRIPTOR_POST",
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
PRINTF_TOKEN_RE = re.compile(r"%[0-9A-Za-z]")


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
            if PRINTF_TOKEN_RE.search(fragment):
                continue
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


def markdown_image_ref(screenshot: str, markdown_path: Path) -> str:
    screenshot_path = Path(screenshot)
    try:
        return screenshot_path.resolve().relative_to(markdown_path.parent.resolve()).as_posix()
    except (OSError, ValueError):
        return screenshot


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


def battle_center_wrapper_seen(rows: list[dict[str, Any]]) -> bool:
    for row in rows:
        if row["marker"] != "BATTLE_PRESENT_CALL":
            continue
        ret = row.get("values", {}).get("ret")
        if isinstance(ret, int) and 0x0051BA00 <= ret < 0x0051BB00:
            return True
    return False


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


def row_value(row: dict[str, Any] | None, key: str) -> Any:
    if row is None:
        return None
    return row.get("values", {}).get(key)


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
    command_native_hit_ok = marker_counts["BATTLE_COMMAND_NATIVE_HIT"] > 0
    command_callback_ok = marker_counts["BATTLE_COMMAND_CALLBACK"] > 0
    command_callback_result_ok = marker_counts["BATTLE_COMMAND_CALLBACK_RESULT"] > 0
    command_render_begin_skip_seen = marker_counts["BATTLE_COMMAND_RENDER_BEGIN_SKIP"] > 0
    command_render_begin_enter_seen = marker_counts["BATTLE_COMMAND_RENDER_BEGIN_ENTER"] > 0
    command_rearm_pre_gates_seen = marker_counts["BATTLE_COMMAND_REARM_PRE_GATES"] > 0
    command_pre_gates_seen = marker_counts["BATTLE_COMMAND_PRE_GATES"] > 0
    command_synthetic_release_seen = marker_counts["BATTLE_COMMAND_SYNTHETIC_RELEASE"] > 0
    render_begin_enter_seen = marker_counts["BATTLE_RENDER_BEGIN_ENTER"] > 0
    render_begin_guard_seen = (
        marker_counts["BATTLE_RENDER_BEGIN_SPIN_GUARD"] > 0
        or marker_counts["BATTLE_RENDER_BEGIN_LOST_GUARD"] > 0
    )
    render_begin_exit_seen = marker_counts["BATTLE_RENDER_BEGIN_EXIT"] > 0
    grid_hit_ok = marker_counts["BATTLE_GRID_HIT"] > 0
    modal_hit = marker_counts["BATTLE_MODAL_HIT"] > 0
    modal_classified = marker_counts["BATTLE_MODAL_CLASSIFIED"] > 0
    post_ready_summary = last_row(rows, "BATTLE_POSTREADY_SUMMARY")
    post_ready_presents = marker_counts["BATTLE_POSTREADY_PRESENT"]
    post_ready_copybacks = marker_counts["BATTLE_POSTREADY_COPYBACK"]
    post_ready_grid_attempts = marker_counts["BATTLE_POSTREADY_GRID_ATTEMPT"]
    post_ready_redraw_sample_ok = (
        post_ready_summary is not None
        and post_ready_presents >= 1
        and post_ready_grid_attempts >= 1
        and row_value(post_ready_summary, "presents") == post_ready_presents
        and row_value(post_ready_summary, "size") == [800, 600]
    )
    no_av = not av_rows

    last_grid_pre = last_row(rows, "BATTLE_INPUTPROBE_GRID_PRE")
    last_grid_inner = last_row(rows, "BATTLE_INPUTPROBE_GRID_INNER")
    last_grid_post = last_row(rows, "BATTLE_INPUTPROBE_GRID_POST")
    last_descriptor_pre = last_row(rows, "BATTLE_INPUTPROBE_DESCRIPTOR_PRE")
    last_descriptor_inner = last_row(rows, "BATTLE_INPUTPROBE_DESCRIPTOR_INNER")
    last_descriptor_post = last_row(rows, "BATTLE_INPUTPROBE_DESCRIPTOR_POST")
    grid_input_wrapper_ok = (
        row_value(last_grid_pre, "displayed") == [144, 108]
        and row_value(last_grid_inner, "mouse") == [64, 48]
        and row_value(last_grid_post, "mouse") == [144, 108]
    )
    descriptor_input_wrapper_ok = (
        row_value(last_descriptor_pre, "displayed") == [588, 440]
        and row_value(last_descriptor_inner, "mouse") == [508, 380]
        and row_value(last_descriptor_post, "mouse") == [588, 440]
    )
    centered_input_wrapper_ok = grid_input_wrapper_ok and descriptor_input_wrapper_ok

    battle_surface = last_row(rows, "BATTLE_SURFACE")
    surfdump_ready = last_row(rows, "SURFDUMP_READY")
    surface_size = surface_size_from_ready(battle_surface) or surface_size_from_ready(surfdump_ready)
    centered_wrapper_seen = battle_center_wrapper_seen(rows)
    visual_mode = "unknown"
    centered_offset = None
    if battle_surface is not None:
        values = battle_surface["values"]
        if values.get("mode") == "centered-native" or values.get("offset") == [80, 60]:
            visual_mode = "centered-native-640x480"
            centered_offset = values.get("offset", [80, 60])
        elif centered_wrapper_seen and surface_size == [800, 600]:
            visual_mode = "centered-native-640x480"
            centered_offset = [80, 60]
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
        classification.append("battle visual command hit row observed")
    elif command_native_hit_ok:
        classification.append("battle native-coordinate command hit row observed, but visual hit remains unproven")
    else:
        classification.append("battle visual command hit proof was not observed")
    if command_callback_result_ok:
        classification.append("battle command callback result row observed")
    elif command_callback_ok:
        classification.append("battle command callback entry row observed, but no result row was captured")
    else:
        classification.append("battle command callback proof was not observed")
    if command_render_begin_skip_seen:
        classification.append("battle command callback render-begin skip row observed")
    elif command_render_begin_enter_seen and render_begin_exit_seen:
        if render_begin_guard_seen:
            classification.append("battle command callback render-begin call exited through hidden-harness loop guard")
        else:
            classification.append("battle command callback render-begin call entered and exited naturally")
        if command_synthetic_release_seen:
            classification.append("synthetic click state was released before render-begin")
    elif command_render_begin_enter_seen or render_begin_enter_seen:
        classification.append("battle command callback render-begin call entered but exit was not captured")
    if command_pre_gates_seen and not command_rearm_pre_gates_seen:
        classification.append("battle command click survived to pre-gate without rearm")
    elif command_rearm_pre_gates_seen:
        classification.append("battle command pre-gate click rearm row observed")
    if grid_hit_ok:
        classification.append("battle tactical-grid hit row observed")
    elif grid_input_wrapper_ok:
        classification.append("battle tactical-grid centered input wrapper restored coordinates")
    else:
        classification.append("battle tactical-grid hit proof was not observed")
    if post_ready_redraw_sample_ok:
        classification.append("battle post-ready redraw/present sample observed")
    elif post_ready_presents:
        classification.append("battle post-ready present rows observed without summary")
    if centered_input_wrapper_ok:
        classification.append("battle grid and descriptor centered input wrappers both passed pre/inner/post checks")
    elif grid_input_wrapper_ok:
        classification.append("battle grid centered input wrapper passed, descriptor wrapper did not")
    elif descriptor_input_wrapper_ok:
        classification.append("battle descriptor centered input wrapper passed, grid wrapper did not")
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
        "candidate": first_present(run_summary, "CandidatePath", "Candidate", "candidate_path", "candidate"),
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
        "centered_wrapper_seen": centered_wrapper_seen,
        "command_descriptor_found": command_descriptor_found,
        "command_hit_ok": command_hit_ok,
        "command_native_hit_ok": command_native_hit_ok,
        "command_callback_ok": command_callback_ok,
        "command_callback_result_ok": command_callback_result_ok,
        "command_render_begin_skip_seen": command_render_begin_skip_seen,
        "command_render_begin_enter_seen": command_render_begin_enter_seen,
        "command_rearm_pre_gates_seen": command_rearm_pre_gates_seen,
        "command_pre_gates_seen": command_pre_gates_seen,
        "command_synthetic_release_seen": command_synthetic_release_seen,
        "render_begin_enter_seen": render_begin_enter_seen,
        "render_begin_guard_seen": render_begin_guard_seen,
        "render_begin_exit_seen": render_begin_exit_seen,
        "grid_hit_ok": grid_hit_ok,
        "grid_input_wrapper_ok": grid_input_wrapper_ok,
        "descriptor_input_wrapper_ok": descriptor_input_wrapper_ok,
        "centered_input_wrapper_ok": centered_input_wrapper_ok,
        "post_ready_presents": post_ready_presents,
        "post_ready_copybacks": post_ready_copybacks,
        "post_ready_grid_attempts": post_ready_grid_attempts,
        "post_ready_redraw_sample_ok": post_ready_redraw_sample_ok,
        "modal_hit": modal_hit,
        "modal_classified": modal_classified,
        "no_av": no_av,
        "last_battle_surface": battle_surface,
        "last_command_attempt": last_row(rows, "BATTLE_COMMAND_ATTEMPT"),
        "last_command_hit": last_row(rows, "BATTLE_COMMAND_HIT"),
        "last_command_native_hit": last_row(rows, "BATTLE_COMMAND_NATIVE_HIT"),
        "last_command_callback": last_row(rows, "BATTLE_COMMAND_CALLBACK"),
        "last_command_rearm_pre_gates": last_row(rows, "BATTLE_COMMAND_REARM_PRE_GATES"),
        "last_command_pre_gates": last_row(rows, "BATTLE_COMMAND_PRE_GATES"),
        "last_command_render_begin_enter": last_row(rows, "BATTLE_COMMAND_RENDER_BEGIN_ENTER"),
        "last_command_render_begin_skip": last_row(rows, "BATTLE_COMMAND_RENDER_BEGIN_SKIP"),
        "last_command_synthetic_release": last_row(rows, "BATTLE_COMMAND_SYNTHETIC_RELEASE"),
        "last_render_begin_enter": last_row(rows, "BATTLE_RENDER_BEGIN_ENTER"),
        "last_render_begin_loop": last_row(rows, "BATTLE_RENDER_BEGIN_LOOP"),
        "last_render_begin_spin_guard": last_row(rows, "BATTLE_RENDER_BEGIN_SPIN_GUARD"),
        "last_render_begin_lost_check": last_row(rows, "BATTLE_RENDER_BEGIN_LOST_CHECK"),
        "last_render_begin_lost_guard": last_row(rows, "BATTLE_RENDER_BEGIN_LOST_GUARD"),
        "last_render_begin_exit": last_row(rows, "BATTLE_RENDER_BEGIN_EXIT"),
        "last_command_callback_result": last_row(rows, "BATTLE_COMMAND_CALLBACK_RESULT"),
        "last_grid_attempt": last_row(rows, "BATTLE_GRID_ATTEMPT"),
        "last_grid_result": last_row(rows, "BATTLE_GRID_RESULT"),
        "last_grid_hit": last_row(rows, "BATTLE_GRID_HIT"),
        "last_grid_inputprobe_pre": last_grid_pre,
        "last_grid_inputprobe_inner": last_grid_inner,
        "last_grid_inputprobe_post": last_grid_post,
        "last_descriptor_inputprobe_pre": last_descriptor_pre,
        "last_descriptor_inputprobe_inner": last_descriptor_inner,
        "last_descriptor_inputprobe_post": last_descriptor_post,
        "last_post_ready_grid_attempt": last_row(rows, "BATTLE_POSTREADY_GRID_ATTEMPT"),
        "last_post_ready_summary": post_ready_summary,
        "last_modal_hit": last_row(rows, "BATTLE_MODAL_HIT"),
        "last_modal_classified": last_row(rows, "BATTLE_MODAL_CLASSIFIED"),
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
        f"- Centered wrapper seen: `{summary['centered_wrapper_seen']}`",
        f"- Command descriptor found: `{summary['command_descriptor_found']}`",
        f"- Command visual hit ok: `{summary['command_hit_ok']}`",
        f"- Command native hit ok: `{summary['command_native_hit_ok']}`",
        f"- Command callback ok: `{summary['command_callback_ok']}`",
        f"- Command callback result ok: `{summary['command_callback_result_ok']}`",
        f"- Command render-begin skip seen: `{summary['command_render_begin_skip_seen']}`",
        f"- Command render-begin enter seen: `{summary['command_render_begin_enter_seen']}`",
        f"- Command rearm pre-gates seen: `{summary['command_rearm_pre_gates_seen']}`",
        f"- Command pre-gates seen: `{summary['command_pre_gates_seen']}`",
        f"- Command synthetic release seen: `{summary['command_synthetic_release_seen']}`",
        f"- Render-begin guard seen: `{summary['render_begin_guard_seen']}`",
        f"- Render-begin exit seen: `{summary['render_begin_exit_seen']}`",
        f"- Grid hit ok: `{summary['grid_hit_ok']}`",
        f"- Grid input wrapper ok: `{summary['grid_input_wrapper_ok']}`",
        f"- Descriptor input wrapper ok: `{summary['descriptor_input_wrapper_ok']}`",
        f"- Centered input wrapper ok: `{summary['centered_input_wrapper_ok']}`",
        f"- Post-ready presents: `{summary['post_ready_presents']}`",
        f"- Post-ready copybacks: `{summary['post_ready_copybacks']}`",
        f"- Post-ready grid attempts: `{summary['post_ready_grid_attempts']}`",
        f"- Post-ready redraw sample ok: `{summary['post_ready_redraw_sample_ok']}`",
        f"- Modal classified: `{summary['modal_hit'] or summary['modal_classified']}`",
        "",
        "## Classification",
        "",
    ]
    lines.extend(f"- {item}" for item in summary["classification"])
    if summary.get("screenshot"):
        screenshot = markdown_image_ref(summary["screenshot"], path)
        lines.extend(["", "## Screenshot", "", f"![battle UI surface]({screenshot})"])
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
    print(f"command-native-hit-ok: {summary['command_native_hit_ok']}")
    print(f"command-callback-ok: {summary['command_callback_ok']}")
    print(f"command-callback-result-ok: {summary['command_callback_result_ok']}")
    print(f"command-render-begin-skip-seen: {summary['command_render_begin_skip_seen']}")
    print(f"grid-hit-ok: {summary['grid_hit_ok']}")
    print(f"grid-input-wrapper-ok: {summary['grid_input_wrapper_ok']}")
    print(f"descriptor-input-wrapper-ok: {summary['descriptor_input_wrapper_ok']}")
    print(f"centered-input-wrapper-ok: {summary['centered_input_wrapper_ok']}")
    print(f"post-ready-presents: {summary['post_ready_presents']}")
    print(f"post-ready-copybacks: {summary['post_ready_copybacks']}")
    print(f"post-ready-grid-attempts: {summary['post_ready_grid_attempts']}")
    print(f"post-ready-redraw-sample-ok: {summary['post_ready_redraw_sample_ok']}")
    print(f"av-count: {summary['av_count']}")
    if args.write_json:
        args.write_json.parent.mkdir(parents=True, exist_ok=True)
        args.write_json.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    if args.write_markdown:
        write_markdown(args.write_markdown, summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
