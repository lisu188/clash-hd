#!/usr/bin/env python3
"""Summarize future right-bottom isolated slot fixture CDB logs.

This is a repo-only parser for logs produced by the hidden-desktop slot fixture
route in ``right_bottom_slot_fixture_runtime_plan.py``. It does not launch
Clash95, CDB, wrappers, PowerShell, or visible windows.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


MARKERS = (
    "SURFDUMP_LOADSAVE",
    "SURFDUMP_PLAYGAME",
    "SURFDUMP_READY",
    "SURFDUMP_HOST_READY",
    "NOWNER_HEADER",
    "NOWNER_FORCE_MAP_CASTLE_CLICK",
    "NOWNER_MAP_TILE",
    "NOWNER_BUILDING_TILE",
    "NOWNER_CASTLE_OVERVIEW_ENTRY",
    "NOWNER_CASTLE_HIT_GIVEUP",
    "NOWNER_CASTLE_HITMAP_SAMPLE",
    "NOWNER_CASTLE_CMD99_TARGET",
    "NOWNER_CASTLE_HIT",
    "NOWNER_CASTLE_CMD99_GATE",
    "NOWNER_CASTLE_CALLBACK",
    "NOWNER_433C20_ENTRY",
    "NOWNER_OWNER_FLAG_TEST",
    "NOWNER_OWNER_SCREEN_DESC_DRAW",
    "NOWNER_OWNER_DESC_RESULT_SURFDUMP_READY",
    "NOWNER_HITTEST_ENTRY",
    "NOWNER_HITTEST_COMPARE",
    "NOWNER_HITTEST_SCAN_TAIL",
    "NOWNER_DESCRIPTOR_CALLBACK",
    "NOWNER_4338E0_ENTRY",
    "NOWNER_419ED0_ENTRY",
    "NOWNER_419ED0_SOUND_PREP",
    "NOWNER_419ED0_SOUND_RETURN",
    "NOWNER_419ED0_STATE6_READY",
    "NOWNER_419ED0_RENDER_BEGIN_RETURN",
    "NOWNER_419ED0_RENDER_BEGIN",
    "NOWNER_419ED0_STATE5_DONE",
    "NOWNER_RENDER_BEGIN_LATE_ARMED",
    "NOWNER_RELEASE_OWNER_DESC_CLICK",
    "NOWNER_RENDER_BEGIN_ENTRY",
    "NOWNER_RENDER_BEGIN_LOOP",
    "NOWNER_RENDER_BEGIN_FLIP_RESULT",
    "NOWNER_RENDER_BEGIN_DD_PUMP_CALL",
    "NOWNER_RENDER_BEGIN_DD_PUMP_RETURN",
    "NOWNER_RENDER_BEGIN_LOST_RESULT",
    "NOWNER_RENDER_BEGIN_ITERATION_LIMIT",
    "NOWNER_RENDER_BEGIN_EXIT",
    "NOWNER_DD_PUMP_ENTRY",
    "NOWNER_DD_PUMP_MSG_PUMP_CALL",
    "NOWNER_DD_PUMP_MSG_PUMP_RETURN",
    "NOWNER_4338E0_AFTER_SELECT",
    "NOWNER_4338E0_AFTER_GATE",
    "NOWNER_4338E0_RESOURCE_SETUP",
    "NOWNER_4338E0_PRE_PUMP",
    "NOWNER_4338E0_PUMP_ENTRY",
    "NOWNER_4338E0_PUMP_FILL",
    "NOWNER_4338E0_PUMP_RETURN",
    "NOWNER_4338E0_POST_PUMP",
    "NOWNER_4338E0_SURFDUMP_READY",
    "NOWNER_4338E0_OWNER_FLAG_BLOCKED",
    "NOWNER_ACTION_CALL_WRAPPER",
    "NOWNER_WRAPPER_ENTRY",
    "NOWNER_WRAPPER_ALLOC_RESULT",
    "NOWNER_WRAPPER_TEMP_SURFACE",
    "NOWNER_WRAPPER_CALL_STOCK_435BC0",
    "NOWNER_OWNER_435BC0_ENTRY",
    "NOWNER_435BC0_ALLOC_RESULT",
    "NOWNER_435BC0_MODEL_CHECK",
    "NOWNER_435BC0_POLL_LIMIT",
    "NOWNER_435BC0_POLL",
    "NOWNER_435BC0_WRITE_532218",
    "NOWNER_435BC0_WRITE_5322C8",
    "NOWNER_435BC0_PANEL_DRAW",
    "NOWNER_435BC0_GRID_DRAW",
    "NOWNER_435BC0_STATUS_DRAW",
    "NOWNER_435BC0_ACTION_BOX",
    "NOWNER_435BC0_GRID_ROUTE_ENTRY",
    "NOWNER_435BC0_GRID_GATE",
    "NOWNER_435BC0_GRID_CALL",
    "NOWNER_435BC0_GRID_ENTRY",
    "NOWNER_435BC0_GRID_RESULT",
    "NOWNER_435BC0_GRID_FAIL",
    "NOWNER_435BC0_SELECTION_UPDATE",
    "NOWNER_435BC0_SELECTION_AFTER",
    "NOWNER_435BC0_LOOP_HEAD",
    "NOWNER_435BC0_LOOP_PUMP_CALL",
    "NOWNER_435BC0_PUMP_ENTRY",
    "NOWNER_435BC0_PUMP_MSG_CALL",
    "NOWNER_435BC0_PUMP_MSG_RETURN",
    "NOWNER_435BC0_PUMP_TICK_RETURN",
    "NOWNER_435BC0_PUMP_CB14_CALL",
    "NOWNER_435BC0_PUMP_CB14_RETURN",
    "NOWNER_435BC0_PUMP_608F0A_CALL",
    "NOWNER_435BC0_PUMP_608F0A_RETURN",
    "NOWNER_435BC0_PUMP_608F0B_CALL",
    "NOWNER_435BC0_PUMP_608F0B_RETURN",
    "NOWNER_435BC0_PUMP_CB04_CALL",
    "NOWNER_435BC0_PUMP_CB04_RETURN",
    "NOWNER_SOURCEHOLD_LOOP_PUMP",
    "NOWNER_SOURCEHOLD_CB14_PRE",
    "NOWNER_SOURCEHOLD_608F0A_PRE",
    "NOWNER_SOURCEHOLD_608F0B_PRE",
    "NOWNER_SOURCEHOLD_608F0A_COORDS_PRE",
    "NOWNER_SOURCEHOLD_608F0B_COORDS_PRE",
    "NOWNER_SOURCEHOLD_4612E0_ENTRY",
    "NOWNER_SOURCEHOLD_4612E0_RETURN",
    "NOWNER_SOURCEHOLD_4612E0_DIRECT",
    "NOWNER_SOURCEHOLD_4612E0_DIRECT_POST",
    "NOWNER_SOURCEHOLD_4612E0_AFTER_X",
    "NOWNER_SOURCEHOLD_4612E0_AFTER_Y",
    "NOWNER_SOURCEHOLD_4612E0_AFTER_BUTTON",
    "NOWNER_SOURCEHOLD_4612E0_AFTER_REFRESH",
    "NOWNER_SOURCEHOLD_4612E0_INTERPOLATE",
    "NOWNER_SOURCEHOLD_4612E0_INTERPOLATE_POST",
    "NOWNER_ACTION_FORCE_NATIVE",
    "NOWNER_ACTION_FORCE_DISPLAY",
    "NOWNER_ACTION_DESCRIPTOR_ENTRY",
    "NOWNER_ACTION_WIDGET_PRE_GATES",
    "NOWNER_ACTION_WIDGET_CLICK_GATE_RET",
    "NOWNER_ACTION_WIDGET_CLICK_GATE",
    "NOWNER_ACTION_DESCRIPTOR_CALLBACK",
    "NOWNER_ACTION_DESCRIPTOR_RESULT",
    "NOWNER_ACTION_CLICK_435620_BEFORE_SET",
    "NOWNER_ACTION_CLICK_435620_ENTRY",
    "NOWNER_ACTION_CLICK_EXIT_SET",
    "NOWNER_435BC0_LOOP_DRAW_CALL",
    "NOWNER_435BC0_LOOP_DRAW_RETURN",
    "NOWNER_435BC0_LOOP_HIT_RESULT",
    "NOWNER_435BC0_LOOP_COMPARE",
    "NOWNER_435BC0_LOOP_LIMIT",
    "NOWNER_435BC0_LOOP_EXIT",
    "NOWNER_435BC0_NO_HIT_UPDATE",
    "NOWNER_435BC0_RETURN",
    "NOWNER_WRAPPER_STOCK_RETURN",
    "NOWNER_WRAPPER_RESTORE_SURFACE",
    "NOWNER_WRAPPER_COPYBACK_CALL",
    "NOWNER_WRAPPER_COPYBACK_RETURN",
    "NOWNER_WRAPPER_PRESENT_CALL",
    "NOWNER_WRAPPER_ALLOC_FAILED_FALLBACK",
    "NOWNER_WRAPPER_COPYBACK_DONE",
    "AV_SURFDUMP",
)

PROOF_CLASS = "non_natural_isolated_fixture"

ACTION_ROUTE_MARKERS = (
    "NOWNER_4338E0_ENTRY",
    "NOWNER_ACTION_CALL_WRAPPER",
    "NOWNER_OWNER_435BC0_ENTRY",
    "NOWNER_WRAPPER_COPYBACK_DONE",
)

OWNER_ACTION_DRAW_MARKERS = (
    "NOWNER_ACTION_CALL_WRAPPER",
    "NOWNER_OWNER_435BC0_ENTRY",
    "NOWNER_WRAPPER_COPYBACK_DONE",
)

OWNER_ACTION_PRELUDE_MARKERS = (
    "NOWNER_419ED0_ENTRY",
    "NOWNER_419ED0_SOUND_PREP",
    "NOWNER_419ED0_SOUND_RETURN",
    "NOWNER_419ED0_STATE6_READY",
    "NOWNER_419ED0_RENDER_BEGIN",
    "NOWNER_419ED0_RENDER_BEGIN_RETURN",
    "NOWNER_419ED0_STATE5_DONE",
    "NOWNER_RELEASE_OWNER_DESC_CLICK",
    "NOWNER_RENDER_BEGIN_ENTRY",
    "NOWNER_RENDER_BEGIN_LOOP",
    "NOWNER_RENDER_BEGIN_FLIP_RESULT",
    "NOWNER_RENDER_BEGIN_DD_PUMP_CALL",
    "NOWNER_RENDER_BEGIN_DD_PUMP_RETURN",
    "NOWNER_RENDER_BEGIN_LOST_RESULT",
    "NOWNER_RENDER_BEGIN_ITERATION_LIMIT",
    "NOWNER_RENDER_BEGIN_EXIT",
    "NOWNER_DD_PUMP_ENTRY",
    "NOWNER_DD_PUMP_MSG_PUMP_CALL",
    "NOWNER_DD_PUMP_MSG_PUMP_RETURN",
    "NOWNER_4338E0_AFTER_SELECT",
    "NOWNER_4338E0_AFTER_GATE",
    "NOWNER_4338E0_RESOURCE_SETUP",
    "NOWNER_4338E0_PRE_PUMP",
    "NOWNER_4338E0_PUMP_ENTRY",
    "NOWNER_4338E0_PUMP_FILL",
    "NOWNER_4338E0_PUMP_RETURN",
    "NOWNER_4338E0_POST_PUMP",
)

REQUIRED_CASTLE_ROUTE_MARKERS = (
    "NOWNER_CASTLE_CMD99_GATE",
    "NOWNER_CASTLE_CALLBACK",
    "NOWNER_433C20_ENTRY",
    "NOWNER_OWNER_FLAG_TEST",
)

RENDER_BEGIN_MARKERS = (
    "NOWNER_RENDER_BEGIN_ENTRY",
    "NOWNER_RENDER_BEGIN_LOOP",
    "NOWNER_RENDER_BEGIN_FLIP_RESULT",
    "NOWNER_RENDER_BEGIN_DD_PUMP_CALL",
    "NOWNER_RENDER_BEGIN_DD_PUMP_RETURN",
    "NOWNER_RENDER_BEGIN_LOST_RESULT",
    "NOWNER_RENDER_BEGIN_ITERATION_LIMIT",
    "NOWNER_RENDER_BEGIN_EXIT",
)

DD_PUMP_MARKERS = (
    "NOWNER_DD_PUMP_ENTRY",
    "NOWNER_DD_PUMP_MSG_PUMP_CALL",
    "NOWNER_DD_PUMP_MSG_PUMP_RETURN",
)

DESCRIPTOR_HITTEST_MARKERS = (
    "NOWNER_HITTEST_ENTRY",
    "NOWNER_HITTEST_COMPARE",
    "NOWNER_HITTEST_SCAN_TAIL",
    "NOWNER_DESCRIPTOR_CALLBACK",
)

STOCK_LOOPSTATE_MARKERS = (
    "NOWNER_435BC0_POLL_LIMIT",
    "NOWNER_435BC0_POLL",
    "NOWNER_435BC0_WRITE_532218",
    "NOWNER_435BC0_WRITE_5322C8",
    "NOWNER_435BC0_PANEL_DRAW",
    "NOWNER_435BC0_GRID_DRAW",
    "NOWNER_435BC0_STATUS_DRAW",
    "NOWNER_435BC0_ACTION_BOX",
)

STOCK_GRID_MARKERS = (
    "NOWNER_435BC0_GRID_ROUTE_ENTRY",
    "NOWNER_435BC0_GRID_GATE",
    "NOWNER_435BC0_GRID_CALL",
    "NOWNER_435BC0_GRID_ENTRY",
    "NOWNER_435BC0_GRID_RESULT",
    "NOWNER_435BC0_GRID_FAIL",
    "NOWNER_435BC0_SELECTION_UPDATE",
    "NOWNER_435BC0_SELECTION_AFTER",
)

SOURCEHOLD_MARKERS = (
    "NOWNER_SOURCEHOLD_LOOP_PUMP",
    "NOWNER_SOURCEHOLD_CB14_PRE",
    "NOWNER_SOURCEHOLD_608F0A_PRE",
    "NOWNER_SOURCEHOLD_608F0B_PRE",
    "NOWNER_SOURCEHOLD_608F0A_COORDS_PRE",
    "NOWNER_SOURCEHOLD_608F0B_COORDS_PRE",
    "NOWNER_SOURCEHOLD_4612E0_ENTRY",
    "NOWNER_SOURCEHOLD_4612E0_RETURN",
    "NOWNER_SOURCEHOLD_4612E0_DIRECT",
    "NOWNER_SOURCEHOLD_4612E0_DIRECT_POST",
    "NOWNER_SOURCEHOLD_4612E0_AFTER_X",
    "NOWNER_SOURCEHOLD_4612E0_AFTER_Y",
    "NOWNER_SOURCEHOLD_4612E0_AFTER_BUTTON",
    "NOWNER_SOURCEHOLD_4612E0_AFTER_REFRESH",
    "NOWNER_SOURCEHOLD_4612E0_INTERPOLATE",
    "NOWNER_SOURCEHOLD_4612E0_INTERPOLATE_POST",
)

SOURCEHOLD_4612E0_MARKERS = (
    "NOWNER_SOURCEHOLD_4612E0_ENTRY",
    "NOWNER_SOURCEHOLD_4612E0_RETURN",
    "NOWNER_SOURCEHOLD_4612E0_DIRECT",
    "NOWNER_SOURCEHOLD_4612E0_DIRECT_POST",
    "NOWNER_SOURCEHOLD_4612E0_AFTER_X",
    "NOWNER_SOURCEHOLD_4612E0_AFTER_Y",
    "NOWNER_SOURCEHOLD_4612E0_AFTER_BUTTON",
    "NOWNER_SOURCEHOLD_4612E0_AFTER_REFRESH",
    "NOWNER_SOURCEHOLD_4612E0_INTERPOLATE",
    "NOWNER_SOURCEHOLD_4612E0_INTERPOLATE_POST",
)

ACTION_CLICK_MARKERS = (
    "NOWNER_ACTION_FORCE_NATIVE",
    "NOWNER_ACTION_FORCE_DISPLAY",
    "NOWNER_ACTION_DESCRIPTOR_ENTRY",
    "NOWNER_ACTION_WIDGET_PRE_GATES",
    "NOWNER_ACTION_WIDGET_CLICK_GATE_RET",
    "NOWNER_ACTION_WIDGET_CLICK_GATE",
    "NOWNER_ACTION_DESCRIPTOR_CALLBACK",
    "NOWNER_ACTION_DESCRIPTOR_RESULT",
    "NOWNER_ACTION_CLICK_435620_BEFORE_SET",
    "NOWNER_ACTION_CLICK_435620_ENTRY",
    "NOWNER_ACTION_CLICK_EXIT_SET",
)

ACTION_FORCE_MARKERS = (
    "NOWNER_ACTION_FORCE_NATIVE",
    "NOWNER_ACTION_FORCE_DISPLAY",
)

COPYBACK_PATH_MARKERS = (
    "NOWNER_WRAPPER_ENTRY",
    "NOWNER_WRAPPER_ALLOC_RESULT",
    "NOWNER_WRAPPER_TEMP_SURFACE",
    "NOWNER_WRAPPER_CALL_STOCK_435BC0",
    "NOWNER_435BC0_ALLOC_RESULT",
    "NOWNER_435BC0_MODEL_CHECK",
    *STOCK_LOOPSTATE_MARKERS,
    *STOCK_GRID_MARKERS,
    "NOWNER_435BC0_LOOP_HEAD",
    "NOWNER_435BC0_LOOP_PUMP_CALL",
    "NOWNER_435BC0_PUMP_ENTRY",
    "NOWNER_435BC0_PUMP_MSG_CALL",
    "NOWNER_435BC0_PUMP_MSG_RETURN",
    "NOWNER_435BC0_PUMP_TICK_RETURN",
    "NOWNER_435BC0_PUMP_CB14_CALL",
    "NOWNER_435BC0_PUMP_CB14_RETURN",
    "NOWNER_435BC0_PUMP_608F0A_CALL",
    "NOWNER_435BC0_PUMP_608F0A_RETURN",
    "NOWNER_435BC0_PUMP_608F0B_CALL",
    "NOWNER_435BC0_PUMP_608F0B_RETURN",
    "NOWNER_435BC0_PUMP_CB04_CALL",
    "NOWNER_435BC0_PUMP_CB04_RETURN",
    *SOURCEHOLD_MARKERS,
    *ACTION_CLICK_MARKERS,
    "NOWNER_435BC0_LOOP_DRAW_CALL",
    "NOWNER_435BC0_LOOP_DRAW_RETURN",
    "NOWNER_435BC0_LOOP_HIT_RESULT",
    "NOWNER_435BC0_LOOP_COMPARE",
    "NOWNER_435BC0_LOOP_LIMIT",
    "NOWNER_435BC0_LOOP_EXIT",
    "NOWNER_435BC0_NO_HIT_UPDATE",
    "NOWNER_435BC0_RETURN",
    "NOWNER_WRAPPER_STOCK_RETURN",
    "NOWNER_WRAPPER_RESTORE_SURFACE",
    "NOWNER_WRAPPER_COPYBACK_CALL",
    "NOWNER_WRAPPER_COPYBACK_RETURN",
    "NOWNER_WRAPPER_PRESENT_CALL",
    "NOWNER_WRAPPER_ALLOC_FAILED_FALLBACK",
)

KV_RE = re.compile(r"(?P<key>[A-Za-z_][A-Za-z0-9_]*)=(?P<value>\([^)]*\)|[^\s]+)")
MARKER_RE = re.compile("|".join(re.escape(marker) for marker in MARKERS))


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


def parse_key_values(fragment: str) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for item in KV_RE.finditer(fragment):
        key = item.group("key")
        if key not in values:
            values[key] = parse_value(item.group("value"))
    return values


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
            end = matches[index + 1].start() if index + 1 < len(matches) else len(line)
            fragment = line[match.start() : end].strip()
            rows.append(
                {
                    "line": line_no,
                    "marker": marker,
                    "values": parse_key_values(fragment),
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


def first_row(rows: list[dict[str, Any]], marker: str) -> dict[str, Any] | None:
    matches = rows_for(rows, marker)
    return matches[0] if matches else None


def last_row(rows: list[dict[str, Any]], marker: str) -> dict[str, Any] | None:
    matches = rows_for(rows, marker)
    return matches[-1] if matches else None


def first_marker_index(rows: list[dict[str, Any]], markers: tuple[str, ...]) -> int | None:
    for index, row in enumerate(rows):
        if row["marker"] in markers:
            return index
    return None


def last_marker_row(rows: list[dict[str, Any]], marker: str) -> dict[str, Any] | None:
    for row in reversed(rows):
        if row["marker"] == marker:
            return row
    return None


def first_marker_row(rows: list[dict[str, Any]], marker: str) -> dict[str, Any] | None:
    for row in rows:
        if row["marker"] == marker:
            return row
    return None


def unique_preserving_order(values: list[Any]) -> list[Any]:
    unique: list[Any] = []
    for value in values:
        if value not in unique:
            unique.append(value)
    return unique


def count_positive(counts: dict[str, int], *markers: str) -> bool:
    return all(int(counts.get(marker) or 0) > 0 for marker in markers)


def classify_timeout_stack(log_path: Path) -> dict[str, Any]:
    stack_path = log_path.with_name("timeout-stack.log")
    if not stack_path.exists():
        return {
            "path": str(stack_path),
            "present": False,
            "classification": "not_found",
        }
    text = stack_path.read_text(encoding="utf-8-sig", errors="replace")
    lowered = text.lower()
    if "access violation" in lowered or "code c0000005" in lowered:
        classification = "access_violation"
    elif (
        "user32!peekmessagea" in lowered
        and ("00461b58" in lowered or "004605df" in lowered or "+0x605df" in lowered)
    ):
        classification = "peekmessage_dd_pump"
    elif "004609" in lowered or "+0x609" in lowered:
        classification = "render_begin"
    elif (
        "00419b8d" in lowered
        or "00419dd9" in lowered
        or "+0x19b8d" in lowered
        or "+0x19dd9" in lowered
    ):
        classification = "descriptor_hit_scan"
    elif "wake debugger" in lowered:
        classification = "timeout_other"
    else:
        classification = "unclassified"
    return {
        "path": str(stack_path),
        "present": True,
        "classification": classification,
    }


def read_run_summary(log_path: Path) -> dict[str, Any]:
    summary_path = log_path.with_name("summary.json")
    if not summary_path.exists():
        return {"path": str(summary_path), "present": False}
    try:
        data = json.loads(summary_path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        return {
            "path": str(summary_path),
            "present": True,
            "error": str(exc),
        }
    data["path"] = str(summary_path)
    data["present"] = True
    return data


def classify(summary: dict[str, Any]) -> str:
    counts = summary["marker_counts"]
    if summary["av_count"]:
        return "access_violation"
    if summary["loadsave_rows"] and not summary["expected_slot_match"]:
        return "slot_mismatch"
    if not summary["load_success"]:
        return "load_not_reached"
    if not count_positive(counts, *REQUIRED_CASTLE_ROUTE_MARKERS):
        return "castle_route_not_reached"
    if not summary["owner_bit2_set"]:
        return "owner_flag_still_blocked"
    if summary["owner_action_route_count"] and summary["owner_action_draw_count"] <= 0:
        if summary["owner_action_render_begin_returned"]:
            return "owner_action_render_begin_returned"
        if summary["owner_action_render_begin_stalled"]:
            if summary["owner_desc_release_count"] and summary["render_flag_bit01_count"]:
                return "owner_action_clickrelease_still_stalled"
            if summary["render_flag_held_during_spin"]:
                return "owner_action_render_flag_held"
            return "owner_action_ddraw_wait_stalled"
        if summary["owner_action_prelude_count"]:
            return "owner_action_prelude_stalled"
        return "owner_action_entry_only"
    if summary["owner_action_route_count"] and summary["copyback_path_marker_count"]:
        if summary["wrapper_copyback_count"] > 0:
            return "owner_action_copyback_reached"
        if summary["wrapper_alloc_failed_fallback_count"] > 0:
            return "owner_action_wrapper_alloc_failed_fallback"
        if summary["owner_435bc0_loop_limit_count"] > 0:
            return "owner_action_435bc0_loop_stalled"
        return "owner_action_copyback_not_reached"
    if summary["owner_action_route_count"]:
        return "owner_action_draw_reached"
    return "owner_loop_no_action"


def build_classification(summary: dict[str, Any]) -> list[str]:
    counts = summary["marker_counts"]
    lines: list[str] = []
    if summary["load_success"]:
        lines.append("LOADSAVE and PlayGame were reached")
    else:
        lines.append("LOADSAVE and PlayGame were not both reached")
    if summary["candidate_sha256"]:
        lines.append(f"candidate SHA-256: {summary['candidate_sha256']}")
    if summary["stage"]:
        lines.append(f"probe stage: {summary['stage']}")
    if summary["expected_slot_match"]:
        lines.append("observed load slot matches the expected fixture slot")
    else:
        lines.append("observed load slot does not match the expected fixture slot")
    if not summary["loadsave_slot_consistent"]:
        lines.append(f"conflicting LOADSAVE slot values were observed: {summary['loadsave_slot_unique_values']}")
    if summary["loadsave_slot_expected_match"] is False:
        lines.append("one or more LOADSAVE slot values did not match the expected fixture slot")
    if count_positive(counts, *REQUIRED_CASTLE_ROUTE_MARKERS):
        lines.append("castle command-99 owner loop was reached")
    else:
        lines.append("castle command-99 owner loop was not fully reached")
    if counts["NOWNER_CASTLE_HIT_GIVEUP"]:
        lines.append("castle overview command hit target was not reached before bounded giveup")
    if counts["NOWNER_CASTLE_HITMAP_SAMPLE"]:
        lines.append("castle overview hitmap samples were captured around command 0x63")
    if summary["owner_bit2_set"]:
        lines.append("owner flag bit 0x02 was set")
    else:
        lines.append("owner flag bit 0x02 was not set")
    if counts["NOWNER_4338E0_OWNER_FLAG_BLOCKED"]:
        lines.append("owner/action route still emitted the owner-flag blocked marker")
    if summary["owner_action_prelude_count"]:
        lines.append(
            f"owner/action prelude markers were observed: {summary['owner_action_prelude_count']}"
        )
    if summary["owner_action_render_begin_reached"]:
        if summary["owner_action_render_begin_returned"]:
            lines.append("owner/action prelude returned from Render_Begin")
        else:
            lines.append("owner/action prelude reached Render_Begin but no return row was observed")
    if summary["render_begin_marker_count"]:
        lines.append(
            "Render_Begin markers late_armed={armed} entry={entry} loop={loop} flip={flip} "
            "dd_pump_call={call} dd_pump_return={ret} lost={lost} limit={limit} exit={exit}".format(
                armed=summary["render_begin_late_armed_count"],
                entry=summary["render_begin_entry_count"],
                loop=summary["render_begin_loop_count"],
                flip=summary["render_begin_flip_result_count"],
                call=summary["render_begin_dd_pump_call_count"],
                ret=summary["render_begin_dd_pump_return_count"],
                lost=summary["render_begin_lost_result_count"],
                limit=summary["render_begin_iteration_limit_count"],
                exit=summary["render_begin_exit_count"],
            )
        )
    if summary["render_flag_values"]:
        lines.append(
            "Render_Begin flag values d544d04 unique={unique} bit01_rows={bit_rows} last={last}".format(
                unique=summary["render_flag_unique_values"],
                bit_rows=summary["render_flag_bit01_count"],
                last=summary["render_flag_last_value"],
            )
        )
    if summary["render_flag_held_during_spin"]:
        lines.append("Render_Begin spin is correlated with d544d04 bit 0x01/0x02 staying set")
    if summary["owner_desc_release_count"]:
        lines.append(
            f"owner descriptor click-release rows were observed: {summary['owner_desc_release_count']}"
        )
        if summary["last_owner_desc_release"] is not None:
            lines.append(f"last owner descriptor click-release row: {summary['last_owner_desc_release']}")
    if summary["last_render_begin_flip_result"] is not None:
        lines.append(f"last Render_Begin flip result: {summary['last_render_begin_flip_result']}")
    if summary["last_render_begin_lost_result"] is not None:
        lines.append(f"last Render_Begin lost result: {summary['last_render_begin_lost_result']}")
    if summary["last_render_begin_dd_pump_return"] is not None:
        lines.append(f"last Render_Begin DD_Pump return: {summary['last_render_begin_dd_pump_return']}")
    if summary["dd_pump_marker_count"]:
        lines.append(
            "DD_Pump markers entry={entry} message_call={call} message_return={ret}".format(
                entry=summary["dd_pump_entry_count"],
                call=summary["dd_pump_msg_pump_call_count"],
                ret=summary["dd_pump_msg_pump_return_count"],
            )
        )
    if summary["timeout_stack"]["present"]:
        lines.append(f"timeout stack classification: {summary['timeout_stack_classification']}")
    if summary["owner_action_ddraw_wait_stalled"]:
        lines.append("owner/action Render_Begin is classified as a DD_Pump wait stall")
    if summary["owner_action_route_count"]:
        lines.append("owner/action route markers were observed")
    else:
        lines.append("owner/action route markers were not observed")
    if summary["owner_action_draw_count"]:
        lines.append("owner/action draw rows were observed")
    elif summary["owner_action_route_count"]:
        lines.append("owner/action draw rows were not observed after route entry")
    if summary["copyback_path_marker_count"]:
        lines.append(
            "copyback path markers wrapper_entry={entry} call_stock={call_stock} "
            "stock_return={stock_return} copyback_call={copy_call} copyback_return={copy_return} "
            "done={done} alloc_fallback={fallback}".format(
                entry=summary["wrapper_entry_count"],
                call_stock=summary["wrapper_call_stock_count"],
                stock_return=summary["wrapper_stock_return_count"],
                copy_call=summary["wrapper_copyback_call_count"],
                copy_return=summary["wrapper_copyback_return_count"],
                done=summary["wrapper_copyback_count"],
                fallback=summary["wrapper_alloc_failed_fallback_count"],
            )
        )
    if summary["descriptor_hittest_marker_count"]:
        lines.append(f"descriptor hit-test markers were observed: {summary['descriptor_hittest_marker_count']}")
    if summary["stock_loopstate_marker_count"]:
        lines.append(
            "stock 00435BC0 loop-state markers poll={poll} poll_limit={poll_limit} "
            "write_owner={write_owner} write_hover={write_hover}".format(
                poll=summary["owner_435bc0_poll_count"],
                poll_limit=summary["owner_435bc0_poll_limit_count"],
                write_owner=summary["owner_435bc0_write_532218_count"],
                write_hover=summary["owner_435bc0_write_5322c8_count"],
            )
        )
    if summary["stock_grid_marker_count"]:
        lines.append(
            "stock 00435BC0 grid markers route={route} gate={gate} result={result} "
            "fail={fail} selection_update={selection_update}".format(
                route=summary["owner_435bc0_grid_route_count"],
                gate=summary["owner_435bc0_grid_gate_count"],
                result=summary["owner_435bc0_grid_result_count"],
                fail=summary["owner_435bc0_grid_fail_count"],
                selection_update=summary["owner_435bc0_selection_update_count"],
            )
        )
    if summary["sourcehold_marker_count"]:
        lines.append(
            "source-hold markers were observed: {total} callsite={callsite} inner_4612e0={inner}".format(
                total=summary["sourcehold_marker_count"],
                callsite=summary["sourcehold_callsite_marker_count"],
                inner=summary["sourcehold_4612e0_marker_count"],
            )
        )
    if summary["input_source_cb14_4612e0_seen"]:
        lines.append(
            "stock pump cb14 was 004612e0; inner 004612E0 source-copy offsets "
            f"seen={summary['sourcehold_4612e0_marker_count']}"
        )
    if summary["debugger_forced_click_only"]:
        lines.append("action-button callback/copyback proof is debugger-forced, not real input-source proof")
    elif summary["real_input_click_proven"]:
        lines.append("action-button callback reached without debugger force markers")
    lines.append(f"real input-source status: {summary['input_source_status']}")
    if summary["action_click_marker_count"]:
        lines.append(
            "native action-click markers force={force} native_force={native_force} display_force={display_force} desc_entry={entry} desc_callback={callback} "
            "result={result} cb435620={cb435620} exit_set={exit_set}".format(
                force=summary["action_click_force_count"],
                native_force=summary["action_click_native_force_count"],
                display_force=summary["action_click_display_force_count"],
                entry=summary["action_descriptor_entry_count"],
                callback=summary["action_descriptor_callback_count"],
                result=summary["action_descriptor_result_count"],
                cb435620=summary["action_click_435620_entry_count"],
                exit_set=summary["action_click_exit_set_count"],
            )
        )
    if summary["last_action_force"] is not None:
        lines.append(f"last native action force row: {summary['last_action_force']}")
    if summary["last_action_descriptor_callback"] is not None:
        lines.append(f"last native action descriptor callback row: {summary['last_action_descriptor_callback']}")
    if summary["last_action_click_exit_set"] is not None:
        lines.append(f"last native action click exit-set row: {summary['last_action_click_exit_set']}")
    if summary["last_owner_435bc0_poll"] is not None:
        lines.append(f"last stock 00435BC0 poll row: {summary['last_owner_435bc0_poll']}")
    if summary["last_owner_435bc0_poll_before_action_force"] is not None:
        lines.append(
            "last stock 00435BC0 poll before action force: "
            f"{summary['last_owner_435bc0_poll_before_action_force']}"
        )
    if summary["first_owner_435bc0_poll_after_action_force"] is not None:
        lines.append(
            "first stock 00435BC0 poll after action force: "
            f"{summary['first_owner_435bc0_poll_after_action_force']}"
        )
    if summary["last_owner_435bc0_poll_after_action_force"] is not None:
        lines.append(
            "last stock 00435BC0 poll after action force: "
            f"{summary['last_owner_435bc0_poll_after_action_force']}"
        )
    if summary["last_owner_435bc0_grid_result"] is not None:
        lines.append(f"last stock 00435BC0 grid result: {summary['last_owner_435bc0_grid_result']}")
    if summary["owner_435bc0_loop_count"]:
        lines.append(
            "stock 00435BC0 loop markers head={head} pump_call={pump} draw_call={draw_call} "
            "draw_return={draw_return} hit={hit} compare={compare} limit={limit} "
            "loop_exit={loop_exit} return={ret}".format(
                head=summary["owner_435bc0_loop_count"],
                pump=summary["owner_435bc0_pump_call_count"],
                draw_call=summary["owner_435bc0_draw_call_count"],
                draw_return=summary["owner_435bc0_draw_return_count"],
                hit=summary["owner_435bc0_hit_result_count"],
                compare=summary["owner_435bc0_compare_count"],
                limit=summary["owner_435bc0_loop_limit_count"],
                loop_exit=summary["owner_435bc0_loop_exit_count"],
                ret=summary["owner_435bc0_return_count"],
            )
        )
    if summary["owner_435bc0_pump_cb14_call_count"] or summary["owner_435bc0_pump_608f0b_call_count"]:
        lines.append(
            "stock 00435BC0 pump callback markers entry={entry} tick_return={tick} "
            "cb14_call={cb14_call} cb14_return={cb14_return} 608f0b_call={call_608f0b} "
            "cb04_call={cb04_call}".format(
                entry=summary["owner_435bc0_pump_entry_count"],
                tick=summary["owner_435bc0_pump_tick_return_count"],
                cb14_call=summary["owner_435bc0_pump_cb14_call_count"],
                cb14_return=summary["owner_435bc0_pump_cb14_return_count"],
                call_608f0b=summary["owner_435bc0_pump_608f0b_call_count"],
                cb04_call=summary["owner_435bc0_pump_cb04_call_count"],
            )
        )
    if summary["last_owner_435bc0_pump_cb14_call"] is not None:
        lines.append(f"last stock 00435BC0 pump cb14 call: {summary['last_owner_435bc0_pump_cb14_call']}")
    if summary["last_owner_435bc0_pump_608f0b_call"] is not None:
        lines.append(f"last stock 00435BC0 pump 608f0b call: {summary['last_owner_435bc0_pump_608f0b_call']}")
    if summary["first_owner_435bc0_pump_cb14_call"] is not None:
        lines.append(f"first stock 00435BC0 pump cb14 call: {summary['first_owner_435bc0_pump_cb14_call']}")
    if summary["first_owner_435bc0_pump_608f0b_call"] is not None:
        lines.append(f"first stock 00435BC0 pump 608f0b call: {summary['first_owner_435bc0_pump_608f0b_call']}")
    if summary["wrapper_entry_count"] and summary["wrapper_copyback_count"] <= 0:
        lines.append("wrapper copyback completion was not observed after wrapper entry")
    if counts["NOWNER_4338E0_SURFDUMP_READY"]:
        lines.append("fixture surface dump was bounded at the 004338E0 owner/action entry")
    if summary["av_count"]:
        lines.append("AV evidence was observed")
    return lines


def parse_log(
    path: Path,
    expected_slot: int | None = 0,
    proof_class: str = PROOF_CLASS,
) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    rows, av_rows = parse_rows(text)
    counts = marker_counts(rows)
    loadsave = last_row(rows, "SURFDUMP_LOADSAVE")
    playgame = last_row(rows, "SURFDUMP_PLAYGAME")
    owner_flag = last_row(rows, "NOWNER_OWNER_FLAG_TEST")
    owner_entry = last_row(rows, "NOWNER_433C20_ENTRY")
    hitmap_sample = last_row(rows, "NOWNER_CASTLE_HITMAP_SAMPLE")
    cmd99_target = last_row(rows, "NOWNER_CASTLE_CMD99_TARGET")
    hit_rows = rows_for(rows, "NOWNER_CASTLE_HIT")
    loadsave_rows = rows_for(rows, "SURFDUMP_LOADSAVE")
    selected_arg = (loadsave or {}).get("values", {}).get("selected_arg") if loadsave else None
    selected_global = (loadsave or {}).get("values", {}).get("selected_global") if loadsave else None
    loadsave_slot_values: list[int] = []
    for row in loadsave_rows:
        for key in ("selected_arg", "selected_global"):
            value = row["values"].get(key)
            if value is not None:
                loadsave_slot_values.append(value)
    loadsave_slot_unique_values = unique_preserving_order(loadsave_slot_values)
    loadsave_slot_consistent = len(loadsave_slot_unique_values) <= 1
    loadsave_slot_expected_match = (
        expected_slot is None
        or (
            bool(loadsave_slot_values)
            and loadsave_slot_consistent
            and loadsave_slot_unique_values[0] == expected_slot
        )
    )
    expected_slot_match = (
        expected_slot is None
        or loadsave_slot_expected_match
    )
    owner_flag_values = (owner_flag or {}).get("values") if owner_flag else {}
    owner_bit2 = int((owner_flag_values or {}).get("bit2") or 0)
    action_count = sum(int(counts.get(marker) or 0) for marker in ACTION_ROUTE_MARKERS)
    action_draw_count = sum(int(counts.get(marker) or 0) for marker in OWNER_ACTION_DRAW_MARKERS)
    action_prelude_count = sum(int(counts.get(marker) or 0) for marker in OWNER_ACTION_PRELUDE_MARKERS)
    render_begin_count = sum(int(counts.get(marker) or 0) for marker in RENDER_BEGIN_MARKERS)
    dd_pump_count = sum(int(counts.get(marker) or 0) for marker in DD_PUMP_MARKERS)
    descriptor_hittest_count = sum(int(counts.get(marker) or 0) for marker in DESCRIPTOR_HITTEST_MARKERS)
    stock_loopstate_count = sum(int(counts.get(marker) or 0) for marker in STOCK_LOOPSTATE_MARKERS)
    stock_grid_count = sum(int(counts.get(marker) or 0) for marker in STOCK_GRID_MARKERS)
    sourcehold_count = sum(int(counts.get(marker) or 0) for marker in SOURCEHOLD_MARKERS)
    sourcehold_4612e0_count = sum(int(counts.get(marker) or 0) for marker in SOURCEHOLD_4612E0_MARKERS)
    sourcehold_callsite_count = sourcehold_count - sourcehold_4612e0_count
    action_click_count = sum(int(counts.get(marker) or 0) for marker in ACTION_CLICK_MARKERS)
    copyback_path_count = sum(int(counts.get(marker) or 0) for marker in COPYBACK_PATH_MARKERS)
    render_begin_late_armed_count = int(counts.get("NOWNER_RENDER_BEGIN_LATE_ARMED") or 0)
    render_begin_entry_count = int(counts.get("NOWNER_RENDER_BEGIN_ENTRY") or 0)
    render_begin_loop_count = int(counts.get("NOWNER_RENDER_BEGIN_LOOP") or 0)
    render_begin_flip_result_count = int(counts.get("NOWNER_RENDER_BEGIN_FLIP_RESULT") or 0)
    render_begin_dd_pump_call_count = int(counts.get("NOWNER_RENDER_BEGIN_DD_PUMP_CALL") or 0)
    render_begin_dd_pump_return_count = int(counts.get("NOWNER_RENDER_BEGIN_DD_PUMP_RETURN") or 0)
    render_begin_lost_result_count = int(counts.get("NOWNER_RENDER_BEGIN_LOST_RESULT") or 0)
    render_begin_iteration_limit_count = int(counts.get("NOWNER_RENDER_BEGIN_ITERATION_LIMIT") or 0)
    render_begin_exit_count = int(counts.get("NOWNER_RENDER_BEGIN_EXIT") or 0)
    owner_desc_release_count = int(counts.get("NOWNER_RELEASE_OWNER_DESC_CLICK") or 0)
    wrapper_copyback_count = int(counts.get("NOWNER_WRAPPER_COPYBACK_DONE") or 0)
    wrapper_entry_count = int(counts.get("NOWNER_WRAPPER_ENTRY") or 0)
    wrapper_alloc_result_count = int(counts.get("NOWNER_WRAPPER_ALLOC_RESULT") or 0)
    wrapper_temp_surface_count = int(counts.get("NOWNER_WRAPPER_TEMP_SURFACE") or 0)
    wrapper_call_stock_count = int(counts.get("NOWNER_WRAPPER_CALL_STOCK_435BC0") or 0)
    wrapper_stock_return_count = int(counts.get("NOWNER_WRAPPER_STOCK_RETURN") or 0)
    wrapper_restore_surface_count = int(counts.get("NOWNER_WRAPPER_RESTORE_SURFACE") or 0)
    wrapper_copyback_call_count = int(counts.get("NOWNER_WRAPPER_COPYBACK_CALL") or 0)
    wrapper_copyback_return_count = int(counts.get("NOWNER_WRAPPER_COPYBACK_RETURN") or 0)
    wrapper_present_call_count = int(counts.get("NOWNER_WRAPPER_PRESENT_CALL") or 0)
    wrapper_alloc_failed_fallback_count = int(counts.get("NOWNER_WRAPPER_ALLOC_FAILED_FALLBACK") or 0)
    owner_435bc0_alloc_result_count = int(counts.get("NOWNER_435BC0_ALLOC_RESULT") or 0)
    owner_435bc0_model_check_count = int(counts.get("NOWNER_435BC0_MODEL_CHECK") or 0)
    owner_435bc0_poll_count = int(counts.get("NOWNER_435BC0_POLL") or 0)
    owner_435bc0_poll_limit_count = int(counts.get("NOWNER_435BC0_POLL_LIMIT") or 0)
    owner_435bc0_write_532218_count = int(counts.get("NOWNER_435BC0_WRITE_532218") or 0)
    owner_435bc0_write_5322c8_count = int(counts.get("NOWNER_435BC0_WRITE_5322C8") or 0)
    owner_435bc0_grid_route_count = int(counts.get("NOWNER_435BC0_GRID_ROUTE_ENTRY") or 0)
    owner_435bc0_grid_gate_count = int(counts.get("NOWNER_435BC0_GRID_GATE") or 0)
    owner_435bc0_grid_result_count = int(counts.get("NOWNER_435BC0_GRID_RESULT") or 0)
    owner_435bc0_grid_fail_count = int(counts.get("NOWNER_435BC0_GRID_FAIL") or 0)
    owner_435bc0_selection_update_count = int(counts.get("NOWNER_435BC0_SELECTION_UPDATE") or 0)
    owner_435bc0_loop_count = int(counts.get("NOWNER_435BC0_LOOP_HEAD") or 0)
    owner_435bc0_pump_call_count = int(counts.get("NOWNER_435BC0_LOOP_PUMP_CALL") or 0)
    owner_435bc0_draw_call_count = int(counts.get("NOWNER_435BC0_LOOP_DRAW_CALL") or 0)
    owner_435bc0_draw_return_count = int(counts.get("NOWNER_435BC0_LOOP_DRAW_RETURN") or 0)
    owner_435bc0_hit_result_count = int(counts.get("NOWNER_435BC0_LOOP_HIT_RESULT") or 0)
    owner_435bc0_compare_count = int(counts.get("NOWNER_435BC0_LOOP_COMPARE") or 0)
    owner_435bc0_loop_limit_count = int(counts.get("NOWNER_435BC0_LOOP_LIMIT") or 0)
    owner_435bc0_loop_exit_count = int(counts.get("NOWNER_435BC0_LOOP_EXIT") or 0)
    owner_435bc0_no_hit_update_count = int(counts.get("NOWNER_435BC0_NO_HIT_UPDATE") or 0)
    owner_435bc0_return_count = int(counts.get("NOWNER_435BC0_RETURN") or 0)
    owner_435bc0_pump_entry_count = int(counts.get("NOWNER_435BC0_PUMP_ENTRY") or 0)
    owner_435bc0_pump_msg_call_count = int(counts.get("NOWNER_435BC0_PUMP_MSG_CALL") or 0)
    owner_435bc0_pump_msg_return_count = int(counts.get("NOWNER_435BC0_PUMP_MSG_RETURN") or 0)
    owner_435bc0_pump_tick_return_count = int(counts.get("NOWNER_435BC0_PUMP_TICK_RETURN") or 0)
    owner_435bc0_pump_cb14_call_count = int(counts.get("NOWNER_435BC0_PUMP_CB14_CALL") or 0)
    owner_435bc0_pump_cb14_return_count = int(counts.get("NOWNER_435BC0_PUMP_CB14_RETURN") or 0)
    owner_435bc0_pump_608f0a_call_count = int(counts.get("NOWNER_435BC0_PUMP_608F0A_CALL") or 0)
    owner_435bc0_pump_608f0a_return_count = int(counts.get("NOWNER_435BC0_PUMP_608F0A_RETURN") or 0)
    owner_435bc0_pump_608f0b_call_count = int(counts.get("NOWNER_435BC0_PUMP_608F0B_CALL") or 0)
    owner_435bc0_pump_608f0b_return_count = int(counts.get("NOWNER_435BC0_PUMP_608F0B_RETURN") or 0)
    owner_435bc0_pump_cb04_call_count = int(counts.get("NOWNER_435BC0_PUMP_CB04_CALL") or 0)
    owner_435bc0_pump_cb04_return_count = int(counts.get("NOWNER_435BC0_PUMP_CB04_RETURN") or 0)
    action_click_force_count = sum(int(counts.get(marker) or 0) for marker in ACTION_FORCE_MARKERS)
    action_click_native_force_count = int(counts.get("NOWNER_ACTION_FORCE_NATIVE") or 0)
    action_click_display_force_count = int(counts.get("NOWNER_ACTION_FORCE_DISPLAY") or 0)
    action_descriptor_entry_count = int(counts.get("NOWNER_ACTION_DESCRIPTOR_ENTRY") or 0)
    action_widget_click_gate_ret_count = int(counts.get("NOWNER_ACTION_WIDGET_CLICK_GATE_RET") or 0)
    action_descriptor_callback_count = int(counts.get("NOWNER_ACTION_DESCRIPTOR_CALLBACK") or 0)
    action_descriptor_result_count = int(counts.get("NOWNER_ACTION_DESCRIPTOR_RESULT") or 0)
    action_click_435620_entry_count = int(counts.get("NOWNER_ACTION_CLICK_435620_ENTRY") or 0)
    action_click_exit_set_count = int(counts.get("NOWNER_ACTION_CLICK_EXIT_SET") or 0)
    dd_pump_entry_count = int(counts.get("NOWNER_DD_PUMP_ENTRY") or 0)
    dd_pump_msg_pump_call_count = int(counts.get("NOWNER_DD_PUMP_MSG_PUMP_CALL") or 0)
    dd_pump_msg_pump_return_count = int(counts.get("NOWNER_DD_PUMP_MSG_PUMP_RETURN") or 0)
    last_flip_result = last_row(rows, "NOWNER_RENDER_BEGIN_FLIP_RESULT")
    last_lost_result = last_row(rows, "NOWNER_RENDER_BEGIN_LOST_RESULT")
    last_dd_pump_return = last_row(rows, "NOWNER_RENDER_BEGIN_DD_PUMP_RETURN")
    last_release = last_row(rows, "NOWNER_RELEASE_OWNER_DESC_CLICK")
    last_wrapper_entry = last_row(rows, "NOWNER_WRAPPER_ENTRY")
    last_wrapper_stock_return = last_row(rows, "NOWNER_WRAPPER_STOCK_RETURN")
    last_owner_435bc0_loop = last_row(rows, "NOWNER_435BC0_LOOP_HEAD")
    last_owner_435bc0_hit_result = last_row(rows, "NOWNER_435BC0_LOOP_HIT_RESULT")
    last_owner_435bc0_compare = last_row(rows, "NOWNER_435BC0_LOOP_COMPARE")
    last_owner_435bc0_poll = last_row(rows, "NOWNER_435BC0_POLL")
    last_owner_435bc0_grid_gate = last_row(rows, "NOWNER_435BC0_GRID_GATE")
    last_owner_435bc0_grid_result = last_row(rows, "NOWNER_435BC0_GRID_RESULT")
    last_owner_435bc0_pump_call = last_row(rows, "NOWNER_435BC0_LOOP_PUMP_CALL")
    last_owner_435bc0_pump_tick_return = last_row(rows, "NOWNER_435BC0_PUMP_TICK_RETURN")
    last_owner_435bc0_pump_cb14_call = last_row(rows, "NOWNER_435BC0_PUMP_CB14_CALL")
    last_owner_435bc0_pump_608f0b_call = last_row(rows, "NOWNER_435BC0_PUMP_608F0B_CALL")
    last_owner_435bc0_pump_cb04_call = last_row(rows, "NOWNER_435BC0_PUMP_CB04_CALL")
    first_owner_435bc0_pump_tick_return = first_row(rows, "NOWNER_435BC0_PUMP_TICK_RETURN")
    first_owner_435bc0_pump_cb14_call = first_row(rows, "NOWNER_435BC0_PUMP_CB14_CALL")
    first_owner_435bc0_pump_608f0b_call = first_row(rows, "NOWNER_435BC0_PUMP_608F0B_CALL")
    sourcehold_rows = [row for row in rows if row["marker"] in SOURCEHOLD_MARKERS]
    action_click_rows = [row for row in rows if row["marker"] in ACTION_CLICK_MARKERS]
    action_force_rows = [row for row in rows if row["marker"] in ACTION_FORCE_MARKERS]
    first_action_force_index = first_marker_index(rows, ACTION_FORCE_MARKERS)
    rows_before_action_force = rows[:first_action_force_index] if first_action_force_index is not None else rows
    rows_after_action_force = rows[first_action_force_index + 1 :] if first_action_force_index is not None else []
    last_owner_435bc0_poll_before_action_force = last_marker_row(
        rows_before_action_force,
        "NOWNER_435BC0_POLL",
    )
    first_owner_435bc0_poll_after_action_force = first_marker_row(
        rows_after_action_force,
        "NOWNER_435BC0_POLL",
    )
    last_owner_435bc0_poll_after_action_force = last_marker_row(
        rows_after_action_force,
        "NOWNER_435BC0_POLL",
    )
    last_action_descriptor_callback = last_row(rows, "NOWNER_ACTION_DESCRIPTOR_CALLBACK")
    last_action_descriptor_result = last_row(rows, "NOWNER_ACTION_DESCRIPTOR_RESULT")
    last_action_click_exit_set = last_row(rows, "NOWNER_ACTION_CLICK_EXIT_SET")
    flag_markers = set(RENDER_BEGIN_MARKERS + DD_PUMP_MARKERS + ("NOWNER_419ED0_RENDER_BEGIN", "NOWNER_4338E0_ENTRY"))
    render_flag_values = [
        row["values"]["d544d04"]
        for row in rows
        if row["marker"] in flag_markers and "d544d04" in row["values"]
    ]
    render_flag_unique_values = unique_preserving_order(render_flag_values)
    render_flag_bit01_count = sum(1 for value in render_flag_values if int(value) & 0x03)
    render_flag_nonzero_count = sum(1 for value in render_flag_values if int(value) != 0)
    render_flag_last_value = render_flag_values[-1] if render_flag_values else None
    timeout_stack = classify_timeout_stack(path)
    run_summary = read_run_summary(path)
    last_cb14_values = (last_owner_435bc0_pump_cb14_call or {}).get("values") if last_owner_435bc0_pump_cb14_call else {}
    input_source_cb14_4612e0_seen = int((last_cb14_values or {}).get("cb14") or 0) == 0x004612E0
    real_input_click_proven = bool(
        action_click_force_count == 0
        and action_descriptor_callback_count > 0
        and action_click_435620_entry_count > 0
        and action_click_exit_set_count > 0
    )
    debugger_forced_click_only = bool(
        action_click_force_count > 0
        and action_click_435620_entry_count > 0
        and not real_input_click_proven
    )
    if real_input_click_proven:
        input_source_status = "real_input_action_click_reached"
    elif debugger_forced_click_only:
        input_source_status = "debugger_forced_action_click_only"
    elif input_source_cb14_4612e0_seen and sourcehold_4612e0_count == 0:
        input_source_status = "cb14_4612e0_callsite_seen_inner_offsets_unverified"
    elif input_source_cb14_4612e0_seen:
        input_source_status = "cb14_4612e0_inner_offsets_seen"
    else:
        input_source_status = "real_input_source_not_observed"
    render_begin_reached = (
        int(counts.get("NOWNER_419ED0_RENDER_BEGIN") or 0) > 0
        or render_begin_entry_count > 0
    )
    render_begin_returned = (
        int(counts.get("NOWNER_419ED0_RENDER_BEGIN_RETURN") or 0) > 0
        or render_begin_exit_count > 0
    )
    render_begin_stalled = render_begin_reached and not render_begin_returned
    ddraw_wait_stalled = (
        render_begin_stalled
        and (
            render_begin_dd_pump_call_count > render_begin_dd_pump_return_count
            or dd_pump_entry_count > 0
            or dd_pump_msg_pump_call_count > dd_pump_msg_pump_return_count
            or timeout_stack["classification"] == "peekmessage_dd_pump"
        )
    )
    render_flag_held_during_spin = bool(
        render_begin_stalled
        and not owner_desc_release_count
        and render_flag_bit01_count > 0
        and (
            render_begin_iteration_limit_count > 0
            or render_begin_loop_count > 1
            or (last_flip_result and int(last_flip_result["values"].get("eax") or 0) != 0)
            or (last_lost_result and int(last_lost_result["values"].get("eax") or 0) != 0)
        )
    )
    summary: dict[str, Any] = {
        "log": str(path),
        "proof_class": proof_class,
        "expected_slot": expected_slot,
        "selected_arg": selected_arg,
        "selected_global": selected_global,
        "loadsave_rows": loadsave_rows,
        "loadsave_slot_values": loadsave_slot_values,
        "loadsave_slot_unique_values": loadsave_slot_unique_values,
        "loadsave_slot_consistent": loadsave_slot_consistent,
        "loadsave_slot_expected_match": loadsave_slot_expected_match,
        "expected_slot_match": expected_slot_match,
        "row_count": len(rows),
        "marker_counts": counts,
        "av_count": len(av_rows),
        "av_rows": av_rows,
        "load_success": count_positive(counts, "SURFDUMP_LOADSAVE", "SURFDUMP_PLAYGAME"),
        "owner_loop_reached": count_positive(counts, *REQUIRED_CASTLE_ROUTE_MARKERS),
        "owner_entry": (owner_entry or {}).get("values") if owner_entry else None,
        "owner_flag_test": owner_flag_values,
        "owner_bit2_set": owner_bit2 != 0,
        "owner_action_route_count": action_count,
        "owner_action_draw_count": action_draw_count,
        "owner_action_prelude_count": action_prelude_count,
        "copyback_path_marker_count": copyback_path_count,
        "render_begin_marker_count": render_begin_count,
        "dd_pump_marker_count": dd_pump_count,
        "descriptor_hittest_marker_count": descriptor_hittest_count,
        "stock_loopstate_marker_count": stock_loopstate_count,
        "stock_grid_marker_count": stock_grid_count,
        "sourcehold_marker_count": sourcehold_count,
        "sourcehold_callsite_marker_count": sourcehold_callsite_count,
        "sourcehold_4612e0_marker_count": sourcehold_4612e0_count,
        "input_source_cb14_4612e0_seen": input_source_cb14_4612e0_seen,
        "input_source_status": input_source_status,
        "real_input_click_proven": real_input_click_proven,
        "debugger_forced_click_only": debugger_forced_click_only,
        "action_click_marker_count": action_click_count,
        "render_begin_late_armed_count": render_begin_late_armed_count,
        "render_begin_entry_count": render_begin_entry_count,
        "render_begin_loop_count": render_begin_loop_count,
        "render_begin_flip_result_count": render_begin_flip_result_count,
        "render_begin_dd_pump_call_count": render_begin_dd_pump_call_count,
        "render_begin_dd_pump_return_count": render_begin_dd_pump_return_count,
        "render_begin_lost_result_count": render_begin_lost_result_count,
        "render_begin_iteration_limit_count": render_begin_iteration_limit_count,
        "render_begin_exit_count": render_begin_exit_count,
        "owner_desc_release_count": owner_desc_release_count,
        "last_owner_desc_release": (last_release or {}).get("values") if last_release else None,
        "wrapper_copyback_count": wrapper_copyback_count,
        "wrapper_entry_count": wrapper_entry_count,
        "wrapper_alloc_result_count": wrapper_alloc_result_count,
        "wrapper_temp_surface_count": wrapper_temp_surface_count,
        "wrapper_call_stock_count": wrapper_call_stock_count,
        "wrapper_stock_return_count": wrapper_stock_return_count,
        "wrapper_restore_surface_count": wrapper_restore_surface_count,
        "wrapper_copyback_call_count": wrapper_copyback_call_count,
        "wrapper_copyback_return_count": wrapper_copyback_return_count,
        "wrapper_present_call_count": wrapper_present_call_count,
        "wrapper_alloc_failed_fallback_count": wrapper_alloc_failed_fallback_count,
        "owner_435bc0_alloc_result_count": owner_435bc0_alloc_result_count,
        "owner_435bc0_model_check_count": owner_435bc0_model_check_count,
        "owner_435bc0_poll_count": owner_435bc0_poll_count,
        "owner_435bc0_poll_limit_count": owner_435bc0_poll_limit_count,
        "owner_435bc0_write_532218_count": owner_435bc0_write_532218_count,
        "owner_435bc0_write_5322c8_count": owner_435bc0_write_5322c8_count,
        "owner_435bc0_grid_route_count": owner_435bc0_grid_route_count,
        "owner_435bc0_grid_gate_count": owner_435bc0_grid_gate_count,
        "owner_435bc0_grid_result_count": owner_435bc0_grid_result_count,
        "owner_435bc0_grid_fail_count": owner_435bc0_grid_fail_count,
        "owner_435bc0_selection_update_count": owner_435bc0_selection_update_count,
        "owner_435bc0_loop_count": owner_435bc0_loop_count,
        "owner_435bc0_pump_call_count": owner_435bc0_pump_call_count,
        "owner_435bc0_draw_call_count": owner_435bc0_draw_call_count,
        "owner_435bc0_draw_return_count": owner_435bc0_draw_return_count,
        "owner_435bc0_hit_result_count": owner_435bc0_hit_result_count,
        "owner_435bc0_compare_count": owner_435bc0_compare_count,
        "owner_435bc0_loop_limit_count": owner_435bc0_loop_limit_count,
        "owner_435bc0_loop_exit_count": owner_435bc0_loop_exit_count,
        "owner_435bc0_no_hit_update_count": owner_435bc0_no_hit_update_count,
        "owner_435bc0_return_count": owner_435bc0_return_count,
        "owner_435bc0_pump_entry_count": owner_435bc0_pump_entry_count,
        "owner_435bc0_pump_msg_call_count": owner_435bc0_pump_msg_call_count,
        "owner_435bc0_pump_msg_return_count": owner_435bc0_pump_msg_return_count,
        "owner_435bc0_pump_tick_return_count": owner_435bc0_pump_tick_return_count,
        "owner_435bc0_pump_cb14_call_count": owner_435bc0_pump_cb14_call_count,
        "owner_435bc0_pump_cb14_return_count": owner_435bc0_pump_cb14_return_count,
        "owner_435bc0_pump_608f0a_call_count": owner_435bc0_pump_608f0a_call_count,
        "owner_435bc0_pump_608f0a_return_count": owner_435bc0_pump_608f0a_return_count,
        "owner_435bc0_pump_608f0b_call_count": owner_435bc0_pump_608f0b_call_count,
        "owner_435bc0_pump_608f0b_return_count": owner_435bc0_pump_608f0b_return_count,
        "owner_435bc0_pump_cb04_call_count": owner_435bc0_pump_cb04_call_count,
        "owner_435bc0_pump_cb04_return_count": owner_435bc0_pump_cb04_return_count,
        "action_click_force_count": action_click_force_count,
        "action_click_native_force_count": action_click_native_force_count,
        "action_click_display_force_count": action_click_display_force_count,
        "action_descriptor_entry_count": action_descriptor_entry_count,
        "action_widget_click_gate_ret_count": action_widget_click_gate_ret_count,
        "action_descriptor_callback_count": action_descriptor_callback_count,
        "action_descriptor_result_count": action_descriptor_result_count,
        "action_click_435620_entry_count": action_click_435620_entry_count,
        "action_click_exit_set_count": action_click_exit_set_count,
        "last_wrapper_entry": (last_wrapper_entry or {}).get("values") if last_wrapper_entry else None,
        "last_wrapper_stock_return": (last_wrapper_stock_return or {}).get("values") if last_wrapper_stock_return else None,
        "last_owner_435bc0_loop": (last_owner_435bc0_loop or {}).get("values") if last_owner_435bc0_loop else None,
        "last_owner_435bc0_hit_result": (
            last_owner_435bc0_hit_result or {}
        ).get("values") if last_owner_435bc0_hit_result else None,
        "last_owner_435bc0_compare": (
            last_owner_435bc0_compare or {}
        ).get("values") if last_owner_435bc0_compare else None,
        "last_owner_435bc0_poll": (last_owner_435bc0_poll or {}).get("values") if last_owner_435bc0_poll else None,
        "last_owner_435bc0_poll_before_action_force": (
            last_owner_435bc0_poll_before_action_force or {}
        ).get("values") if last_owner_435bc0_poll_before_action_force else None,
        "first_owner_435bc0_poll_after_action_force": (
            first_owner_435bc0_poll_after_action_force or {}
        ).get("values") if first_owner_435bc0_poll_after_action_force else None,
        "last_owner_435bc0_poll_after_action_force": (
            last_owner_435bc0_poll_after_action_force or {}
        ).get("values") if last_owner_435bc0_poll_after_action_force else None,
        "last_owner_435bc0_grid_gate": (
            last_owner_435bc0_grid_gate or {}
        ).get("values") if last_owner_435bc0_grid_gate else None,
        "last_owner_435bc0_grid_result": (
            last_owner_435bc0_grid_result or {}
        ).get("values") if last_owner_435bc0_grid_result else None,
        "last_owner_435bc0_pump_call": (
            last_owner_435bc0_pump_call or {}
        ).get("values") if last_owner_435bc0_pump_call else None,
        "last_owner_435bc0_pump_tick_return": (
            last_owner_435bc0_pump_tick_return or {}
        ).get("values") if last_owner_435bc0_pump_tick_return else None,
        "last_owner_435bc0_pump_cb14_call": (
            last_owner_435bc0_pump_cb14_call or {}
        ).get("values") if last_owner_435bc0_pump_cb14_call else None,
        "last_owner_435bc0_pump_608f0b_call": (
            last_owner_435bc0_pump_608f0b_call or {}
        ).get("values") if last_owner_435bc0_pump_608f0b_call else None,
        "last_owner_435bc0_pump_cb04_call": (
            last_owner_435bc0_pump_cb04_call or {}
        ).get("values") if last_owner_435bc0_pump_cb04_call else None,
        "first_owner_435bc0_pump_tick_return": (
            first_owner_435bc0_pump_tick_return or {}
        ).get("values") if first_owner_435bc0_pump_tick_return else None,
        "first_owner_435bc0_pump_cb14_call": (
            first_owner_435bc0_pump_cb14_call or {}
        ).get("values") if first_owner_435bc0_pump_cb14_call else None,
        "first_owner_435bc0_pump_608f0b_call": (
            first_owner_435bc0_pump_608f0b_call or {}
        ).get("values") if first_owner_435bc0_pump_608f0b_call else None,
        "last_sourcehold_marker": sourcehold_rows[-1]["marker"] if sourcehold_rows else None,
        "last_sourcehold": (sourcehold_rows[-1] if sourcehold_rows else {}).get("values") if sourcehold_rows else None,
        "last_action_click_marker": action_click_rows[-1]["marker"] if action_click_rows else None,
        "last_action_force_marker": action_force_rows[-1]["marker"] if action_force_rows else None,
        "last_action_force": (
            action_force_rows[-1] if action_force_rows else {}
        ).get("values") if action_force_rows else None,
        "last_action_descriptor_callback": (
            last_action_descriptor_callback or {}
        ).get("values") if last_action_descriptor_callback else None,
        "last_action_descriptor_result": (
            last_action_descriptor_result or {}
        ).get("values") if last_action_descriptor_result else None,
        "last_action_click_exit_set": (
            last_action_click_exit_set or {}
        ).get("values") if last_action_click_exit_set else None,
        "render_flag_values": render_flag_values,
        "render_flag_unique_values": render_flag_unique_values,
        "render_flag_bit01_count": render_flag_bit01_count,
        "render_flag_nonzero_count": render_flag_nonzero_count,
        "render_flag_last_value": render_flag_last_value,
        "render_flag_held_during_spin": render_flag_held_during_spin,
        "dd_pump_entry_count": dd_pump_entry_count,
        "dd_pump_msg_pump_call_count": dd_pump_msg_pump_call_count,
        "dd_pump_msg_pump_return_count": dd_pump_msg_pump_return_count,
        "last_render_begin_flip_result": (last_flip_result or {}).get("values") if last_flip_result else None,
        "last_render_begin_lost_result": (last_lost_result or {}).get("values") if last_lost_result else None,
        "last_render_begin_dd_pump_return": (last_dd_pump_return or {}).get("values") if last_dd_pump_return else None,
        "timeout_stack": timeout_stack,
        "timeout_stack_classification": timeout_stack["classification"],
        "run_summary": run_summary,
        "candidate_sha256": run_summary.get("CandidateSha256"),
        "candidate_path": run_summary.get("CandidatePath"),
        "candidate_dir": run_summary.get("CandidateDir"),
        "stage": run_summary.get("Stage"),
        "owner_action_render_begin_reached": render_begin_reached,
        "owner_action_render_begin_returned": render_begin_returned,
        "owner_action_render_begin_stalled": render_begin_stalled,
        "owner_action_ddraw_wait_stalled": ddraw_wait_stalled,
        "castle_hitmap_sample": (hitmap_sample or {}).get("values") if hitmap_sample else None,
        "castle_cmd99_target": (cmd99_target or {}).get("values") if cmd99_target else None,
        "castle_hit_count": len(hit_rows),
        "last_castle_hit": (hit_rows[-1] if hit_rows else {}).get("values") if hit_rows else None,
        "loadsave": (loadsave or {}).get("values") if loadsave else None,
        "playgame": (playgame or {}).get("values") if playgame else None,
        "rows": rows,
    }
    summary["status"] = classify(summary)
    summary["classification"] = build_classification(summary)
    return summary


def write_markdown(summary: dict[str, Any], path: Path) -> None:
    lines = [
        "# Right-Bottom Slot Fixture Result Summary",
        "",
        f"- Log: `{summary['log']}`",
        f"- Proof class: `{summary['proof_class']}`",
        f"- Status: `{summary['status']}`",
        f"- Stage: `{summary['stage']}`",
        f"- Candidate path: `{summary['candidate_path']}`",
        f"- Candidate SHA-256: `{summary['candidate_sha256']}`",
        f"- Candidate dir: `{summary['candidate_dir']}`",
        f"- Expected slot: `{summary['expected_slot']}`",
        f"- Selected arg: `{summary['selected_arg']}`",
        f"- Selected global: `{summary['selected_global']}`",
        f"- LOADSAVE slot values: `{summary['loadsave_slot_values']}`",
        f"- LOADSAVE slot consistent: `{summary['loadsave_slot_consistent']}`",
        f"- LOADSAVE slot expected match: `{summary['loadsave_slot_expected_match']}`",
        f"- Expected slot match: `{summary['expected_slot_match']}`",
        f"- Rows parsed: `{summary['row_count']}`",
        f"- Access violations: `{summary['av_count']}`",
        f"- Load success: `{summary['load_success']}`",
        f"- Owner loop reached: `{summary['owner_loop_reached']}`",
        f"- Owner flag test: `{summary['owner_flag_test']}`",
        f"- Owner/action route count: `{summary['owner_action_route_count']}`",
        f"- Owner/action draw count: `{summary['owner_action_draw_count']}`",
        f"- Owner/action prelude count: `{summary['owner_action_prelude_count']}`",
        f"- Copyback path marker count: `{summary['copyback_path_marker_count']}`",
        f"- Owner/action Render_Begin reached: `{summary['owner_action_render_begin_reached']}`",
        f"- Owner/action Render_Begin returned: `{summary['owner_action_render_begin_returned']}`",
        f"- Owner/action Render_Begin stalled: `{summary['owner_action_render_begin_stalled']}`",
        f"- Owner/action DD_Pump wait stalled: `{summary['owner_action_ddraw_wait_stalled']}`",
        f"- Render_Begin marker count: `{summary['render_begin_marker_count']}`",
        f"- Descriptor hit-test marker count: `{summary['descriptor_hittest_marker_count']}`",
        f"- Stock loop-state marker count: `{summary['stock_loopstate_marker_count']}`",
        f"- Stock grid marker count: `{summary['stock_grid_marker_count']}`",
        f"- Source-hold marker count: `{summary['sourcehold_marker_count']}`",
        f"- Native action-click marker count: `{summary['action_click_marker_count']}`",
        f"- Render_Begin late-armed count: `{summary['render_begin_late_armed_count']}`",
        f"- Render_Begin entry count: `{summary['render_begin_entry_count']}`",
        f"- Render_Begin loop count: `{summary['render_begin_loop_count']}`",
        f"- Render_Begin flip result count: `{summary['render_begin_flip_result_count']}`",
        f"- Render_Begin DD_Pump call count: `{summary['render_begin_dd_pump_call_count']}`",
        f"- Render_Begin DD_Pump return count: `{summary['render_begin_dd_pump_return_count']}`",
        f"- Render_Begin lost result count: `{summary['render_begin_lost_result_count']}`",
        f"- Render_Begin iteration limit count: `{summary['render_begin_iteration_limit_count']}`",
        f"- Render_Begin exit count: `{summary['render_begin_exit_count']}`",
        f"- Owner descriptor click-release count: `{summary['owner_desc_release_count']}`",
        f"- Last owner descriptor click-release: `{summary['last_owner_desc_release']}`",
        f"- Wrapper copyback count: `{summary['wrapper_copyback_count']}`",
        f"- Wrapper entry count: `{summary['wrapper_entry_count']}`",
        f"- Wrapper call-stock count: `{summary['wrapper_call_stock_count']}`",
        f"- Wrapper stock-return count: `{summary['wrapper_stock_return_count']}`",
        f"- Wrapper copyback-call count: `{summary['wrapper_copyback_call_count']}`",
        f"- Wrapper copyback-return count: `{summary['wrapper_copyback_return_count']}`",
        f"- Wrapper alloc-failed fallback count: `{summary['wrapper_alloc_failed_fallback_count']}`",
        f"- 00435BC0 poll count: `{summary['owner_435bc0_poll_count']}`",
        f"- 00435BC0 poll limit count: `{summary['owner_435bc0_poll_limit_count']}`",
        f"- 00435BC0 write d532218 count: `{summary['owner_435bc0_write_532218_count']}`",
        f"- 00435BC0 write d5322c8 count: `{summary['owner_435bc0_write_5322c8_count']}`",
        f"- 00435BC0 grid route count: `{summary['owner_435bc0_grid_route_count']}`",
        f"- 00435BC0 grid gate count: `{summary['owner_435bc0_grid_gate_count']}`",
        f"- 00435BC0 grid result count: `{summary['owner_435bc0_grid_result_count']}`",
        f"- 00435BC0 grid fail count: `{summary['owner_435bc0_grid_fail_count']}`",
        f"- 00435BC0 selection update count: `{summary['owner_435bc0_selection_update_count']}`",
        f"- 00435BC0 loop head count: `{summary['owner_435bc0_loop_count']}`",
        f"- 00435BC0 loop limit count: `{summary['owner_435bc0_loop_limit_count']}`",
        f"- 00435BC0 return count: `{summary['owner_435bc0_return_count']}`",
        f"- 00435BC0 pump tick-return count: `{summary['owner_435bc0_pump_tick_return_count']}`",
        f"- 00435BC0 pump cb14 call/return count: `{summary['owner_435bc0_pump_cb14_call_count']}` / `{summary['owner_435bc0_pump_cb14_return_count']}`",
        f"- 00435BC0 pump 608f0b call/return count: `{summary['owner_435bc0_pump_608f0b_call_count']}` / `{summary['owner_435bc0_pump_608f0b_return_count']}`",
        f"- 00435BC0 pump cb04 call/return count: `{summary['owner_435bc0_pump_cb04_call_count']}` / `{summary['owner_435bc0_pump_cb04_return_count']}`",
        f"- Source-hold callsite/inner-004612E0 marker counts: `{summary['sourcehold_callsite_marker_count']}` / `{summary['sourcehold_4612e0_marker_count']}`",
        f"- Input-source cb14=004612E0 seen: `{summary['input_source_cb14_4612e0_seen']}`",
        f"- Real input-source status: `{summary['input_source_status']}`",
        f"- Real input click proven: `{summary['real_input_click_proven']}`",
        f"- Debugger-forced click only: `{summary['debugger_forced_click_only']}`",
        f"- Native action force count: `{summary['action_click_force_count']}`",
        f"- Native action native-force count: `{summary['action_click_native_force_count']}`",
        f"- Native action display-force count: `{summary['action_click_display_force_count']}`",
        f"- Native action descriptor entry count: `{summary['action_descriptor_entry_count']}`",
        f"- Native action widget click-gate return count: `{summary['action_widget_click_gate_ret_count']}`",
        f"- Native action descriptor callback count: `{summary['action_descriptor_callback_count']}`",
        f"- Native action descriptor result count: `{summary['action_descriptor_result_count']}`",
        f"- Native action 00435620 entry count: `{summary['action_click_435620_entry_count']}`",
        f"- Native action exit-set count: `{summary['action_click_exit_set_count']}`",
        f"- Last wrapper entry: `{summary['last_wrapper_entry']}`",
        f"- Last wrapper stock return: `{summary['last_wrapper_stock_return']}`",
        f"- Last 00435BC0 loop row: `{summary['last_owner_435bc0_loop']}`",
        f"- Last 00435BC0 hit result: `{summary['last_owner_435bc0_hit_result']}`",
        f"- Last 00435BC0 compare: `{summary['last_owner_435bc0_compare']}`",
        f"- Last 00435BC0 poll: `{summary['last_owner_435bc0_poll']}`",
        f"- Last 00435BC0 grid gate: `{summary['last_owner_435bc0_grid_gate']}`",
        f"- Last 00435BC0 grid result: `{summary['last_owner_435bc0_grid_result']}`",
        f"- Last 00435BC0 pump call: `{summary['last_owner_435bc0_pump_call']}`",
        f"- Last 00435BC0 pump tick-return: `{summary['last_owner_435bc0_pump_tick_return']}`",
        f"- Last 00435BC0 pump cb14 call: `{summary['last_owner_435bc0_pump_cb14_call']}`",
        f"- Last 00435BC0 pump 608f0b call: `{summary['last_owner_435bc0_pump_608f0b_call']}`",
        f"- Last 00435BC0 pump cb04 call: `{summary['last_owner_435bc0_pump_cb04_call']}`",
        f"- First 00435BC0 pump tick-return: `{summary['first_owner_435bc0_pump_tick_return']}`",
        f"- First 00435BC0 pump cb14 call: `{summary['first_owner_435bc0_pump_cb14_call']}`",
        f"- First 00435BC0 pump 608f0b call: `{summary['first_owner_435bc0_pump_608f0b_call']}`",
        f"- Last 00435BC0 poll before action force: `{summary['last_owner_435bc0_poll_before_action_force']}`",
        f"- First 00435BC0 poll after action force: `{summary['first_owner_435bc0_poll_after_action_force']}`",
        f"- Last 00435BC0 poll after action force: `{summary['last_owner_435bc0_poll_after_action_force']}`",
        f"- Last source-hold marker: `{summary['last_sourcehold_marker']}`",
        f"- Last source-hold row: `{summary['last_sourcehold']}`",
        f"- Last native action-click marker: `{summary['last_action_click_marker']}`",
        f"- Last native action force marker: `{summary['last_action_force_marker']}`",
        f"- Last native action force: `{summary['last_action_force']}`",
        f"- Last native action descriptor callback: `{summary['last_action_descriptor_callback']}`",
        f"- Last native action descriptor result: `{summary['last_action_descriptor_result']}`",
        f"- Last native action click exit-set: `{summary['last_action_click_exit_set']}`",
        f"- Render flag values: `{summary['render_flag_values']}`",
        f"- Render flag unique values: `{summary['render_flag_unique_values']}`",
        f"- Render flag bit01 count: `{summary['render_flag_bit01_count']}`",
        f"- Render flag last value: `{summary['render_flag_last_value']}`",
        f"- Render flag held during spin: `{summary['render_flag_held_during_spin']}`",
        f"- DD_Pump marker count: `{summary['dd_pump_marker_count']}`",
        f"- DD_Pump entry count: `{summary['dd_pump_entry_count']}`",
        f"- DD_Pump message pump call count: `{summary['dd_pump_msg_pump_call_count']}`",
        f"- DD_Pump message pump return count: `{summary['dd_pump_msg_pump_return_count']}`",
        f"- Last Render_Begin flip result: `{summary['last_render_begin_flip_result']}`",
        f"- Last Render_Begin lost result: `{summary['last_render_begin_lost_result']}`",
        f"- Last Render_Begin DD_Pump return: `{summary['last_render_begin_dd_pump_return']}`",
        f"- Timeout stack classification: `{summary['timeout_stack_classification']}`",
        f"- Timeout stack: `{summary['timeout_stack']['path']}`",
        f"- Castle hitmap sample: `{summary['castle_hitmap_sample']}`",
        f"- Castle command-99 target: `{summary['castle_cmd99_target']}`",
        f"- Castle hit count: `{summary['castle_hit_count']}`",
        f"- Last castle hit: `{summary['last_castle_hit']}`",
        "",
        "## Marker Counts",
        "",
    ]
    for marker, count in summary["marker_counts"].items():
        lines.append(f"- `{marker}`: `{count}`")
    lines.extend(["", "## Classification", ""])
    lines.extend(f"- {item}" for item in summary["classification"])
    lines.extend(["", "## Key Rows", ""])
    for row in summary["rows"][-20:]:
        lines.append(f"- line {row['line']}: `{row['text']}`")
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log", type=Path)
    parser.add_argument("--expected-slot", type=int, default=0)
    parser.add_argument("--proof-class", default=PROOF_CLASS)
    parser.add_argument("--write-json", type=Path)
    parser.add_argument("--write-md", type=Path)
    parser.add_argument("--require-load-success", action="store_true")
    parser.add_argument("--require-slot-match", action="store_true")
    parser.add_argument("--require-owner-bit2", action="store_true")
    parser.add_argument("--require-owner-action", action="store_true")
    parser.add_argument("--require-owner-action-draw", action="store_true")
    parser.add_argument("--require-click-release", action="store_true")
    parser.add_argument("--require-render-begin-exit", action="store_true")
    parser.add_argument("--require-copyback-path", action="store_true")
    parser.add_argument("--require-wrapper-copyback", action="store_true")
    args = parser.parse_args(argv)

    summary = parse_log(args.log, args.expected_slot, args.proof_class)
    if args.write_json:
        args.write_json.parent.mkdir(parents=True, exist_ok=True)
        args.write_json.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    if args.write_md:
        write_markdown(summary, args.write_md)

    print(
        "status={status} load_success={load_success} owner_bit2={owner_bit2_set} "
        "owner_action_rows={owner_action_route_count} render_begin_exit={render_begin_exit_count} "
        "release_rows={owner_desc_release_count} render_flag_last={render_flag_last_value} "
        "render_flag_held={render_flag_held_during_spin} dd_pump_entries={dd_pump_entry_count} "
        "stock_poll={owner_435bc0_poll_count} stock_grid={stock_grid_marker_count} "
        "copyback_path={copyback_path_marker_count} wrapper_copyback={wrapper_copyback_count} "
        "timeout_stack={timeout_stack_classification} "
        "candidate_sha={candidate_sha256} av={av_count}".format(**summary)
    )
    for item in summary["classification"]:
        print(f"- {item}")

    if args.require_load_success and not summary["load_success"]:
        print("required fixture load success was not observed", file=sys.stderr)
        return 2
    if args.require_slot_match and not summary["expected_slot_match"]:
        print("expected fixture slot did not match observed LOADSAVE slot", file=sys.stderr)
        return 2
    if args.require_owner_bit2 and not summary["owner_bit2_set"]:
        print("required owner flag bit 0x02 was not observed", file=sys.stderr)
        return 2
    if args.require_owner_action and summary["owner_action_route_count"] <= 0:
        print("required owner/action route was not observed", file=sys.stderr)
        return 2
    if args.require_owner_action_draw and summary["owner_action_draw_count"] <= 0:
        print("required owner/action draw rows were not observed", file=sys.stderr)
        return 2
    if args.require_click_release and summary["owner_desc_release_count"] <= 0:
        print("required owner descriptor click release was not observed", file=sys.stderr)
        return 2
    if args.require_render_begin_exit and summary["render_begin_exit_count"] <= 0:
        print("required Render_Begin exit was not observed", file=sys.stderr)
        return 2
    if args.require_copyback_path and summary["copyback_path_marker_count"] <= 0:
        print("required wrapper/00435BC0 copyback path markers were not observed", file=sys.stderr)
        return 2
    if args.require_wrapper_copyback and summary["wrapper_copyback_count"] <= 0:
        print("required wrapper copyback was not observed", file=sys.stderr)
        return 2
    if summary["av_count"]:
        print("access violation rows were observed", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
