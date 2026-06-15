#!/usr/bin/env python3
"""Run the repo-only Clash95 battle UI evidence matrix.

This matrix combines the current focused battle UI summaries. It checks
existing hidden-desktop CDB/proxy artifacts only; it does not launch Clash95,
CDB, wrappers, PowerShell, or any visible GUI process.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


EXPECTED_STAGE = (
    "gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-"
    "presentbounds-minimapright-dynvswitch-castlecenter-all-battlecenter"
)
EXPECTED_INPUT_STAGE = EXPECTED_STAGE + "-inputprobe"
EXPECTED_BASE_SHA256 = "500055D77D03D514E8D3168506BD10F67CD8569BCC450604FF8192F46CDAF3AE"
EXPECTED_BATTLE_SHA256 = "F3BC31F22EC15765D525ED3EADD00183C78BB1B8F76B3B1C3978AF3480A546EF"
EXPECTED_INPUT_SHA256 = "F84933776944E2B616F6BBCCF7708ABBF06498D5438FA8DF7B7AF1BB56CD180A"

DEFAULT_FORCE_ENTRY_JSON = Path("captures/current/battle-ui-force-entry-current.json")
DEFAULT_COMMAND_HIT_JSON = Path("captures/current/battle-ui-command-hit-current.json")
DEFAULT_COMMAND_CALLBACK_JSON = Path("captures/current/battle-ui-command-callback-current.json")
DEFAULT_ENABLED_CALLBACK_JSON = Path("captures/current/battle-ui-command-enabled-callback-current.json")
DEFAULT_GRID_HIT_JSON = Path("captures/current/battle-ui-grid-hit-current.json")
DEFAULT_CENTERED_INPUT_JSON = Path("captures/current/battle-ui-centered-input-current.json")
DEFAULT_POST_READY_REDRAW_JSON = Path("captures/current/battle-ui-post-ready-redraw-current.json")
DEFAULT_MODAL_CLASSIFIED_JSON = Path("captures/current/battle-ui-modal-classified-current.json")
DEFAULT_PATCH_STAGE_JSON = Path("captures/current/patch-stage-battlecenter-current.json")
DEFAULT_INPUT_PATCH_STAGE_JSON = Path("captures/current/patch-stage-battlecenter-inputprobe-patched-current.json")
DEFAULT_AVAILABILITY_JSON = Path("captures/current/battle-command-availability-current.json")
DEFAULT_SLOT_SCAN_JSON = Path("captures/current/battle-slot-scan-current.json")
DEFAULT_SAVE_INVENTORY_JSON = Path("captures/current/battle-save-unit-inventory-current.json")
DEFAULT_CONSTRUCTED_FIXTURE_JSON = Path("captures/current/battle-constructed-save-fixture-current.json")
DEFAULT_CONSTRUCTED_FIXTURE_UNIT_SCAN_JSON = Path("captures/current/battle-constructed-fixture-unit-scan-current.json")
DEFAULT_CONSTRUCTED_FIXTURE_COMMAND_JSON = Path("captures/current/battle-constructed-fixture-command-callback-current.json")
DEFAULT_STABLE_SMOKE_JSON = Path("captures/current/hd-map-smoke-current.json")
DEFAULT_VISIBLE_INPUT_JSON = Path("captures/current/battle-visible-input-current.json")
DEFAULT_MATRIX_JSON = Path("captures/current/battle-ui-evidence-current.json")
DEFAULT_MATRIX_MD = Path("captures/current/battle-ui-evidence-current.md")

SUMMARY_NAMES = (
    "force_entry",
    "command_hit",
    "command_callback",
    "enabled_callback",
    "grid_hit",
    "centered_input",
    "post_ready_redraw",
    "modal_classified",
)
SCREENSHOT_CHECK_NAMES = SUMMARY_NAMES + ("constructed_fixture_command",)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def maybe_load_json(path: Path) -> tuple[dict[str, Any] | None, list[str]]:
    if not path.exists():
        return None, [f"missing JSON: {path}"]
    try:
        return load_json(path), []
    except json.JSONDecodeError as exc:
        return None, [f"invalid JSON {path}: {exc}"]


def under_clash_tests(path_text: str | None) -> bool:
    if not path_text:
        return False
    return path_text.replace("/", "\\").lower().startswith("c:\\clashtests\\")


def status_text(passed: bool) -> str:
    return "PASS" if passed else "FAIL"


def markdown_image_ref(screenshot: str, markdown_path: Path) -> str:
    screenshot_path = Path(screenshot)
    try:
        return screenshot_path.resolve().relative_to(markdown_path.parent.resolve()).as_posix()
    except (OSError, ValueError):
        return screenshot


def row_values(summary: dict[str, Any], key: str) -> dict[str, Any]:
    row = summary.get(key) or {}
    return row.get("values") or {}


def hex_or_none(value: Any) -> str | None:
    if isinstance(value, int):
        return f"0x{value:08X}"
    return None


def common_summary_failures(name: str, summary: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    if summary.get("battle_ready") is not True:
        failures.append(f"{name}: battle_ready is not true")
    if summary.get("surface_size") != [800, 600]:
        failures.append(f"{name}: surface_size is {summary.get('surface_size')}")
    if summary.get("visual_mode") != "centered-native-640x480":
        failures.append(f"{name}: visual_mode is {summary.get('visual_mode')}")
    if summary.get("centered_wrapper_seen") is not True:
        failures.append(f"{name}: centered wrapper was not observed")
    if int(summary.get("av_count") or 0):
        failures.append(f"{name}: AV rows were observed: {summary.get('av_count')}")
    if summary.get("hidden_desktop") is not True:
        failures.append(f"{name}: hidden_desktop is not true")
    if not under_clash_tests(summary.get("candidate")):
        failures.append(f"{name}: candidate is not under C:\\ClashTests: {summary.get('candidate')}")
    return failures


def feature_failures(name: str, summary: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    if name == "force_entry":
        if summary.get("centered_offset") != [80, 60]:
            failures.append(f"{name}: centered offset is {summary.get('centered_offset')}")
    elif name == "command_hit":
        if summary.get("command_hit_ok") is not True:
            failures.append("command_hit: visual command hit is not proven")
        if summary.get("command_native_hit_ok") is not True:
            failures.append("command_hit: native command hit is not proven")
    elif name == "command_callback":
        if summary.get("command_callback_ok") is not True:
            failures.append("command_callback: callback entry is not proven")
        if summary.get("command_callback_result_ok") is not True:
            failures.append("command_callback: callback result is not proven")
        branch = row_values(summary, "last_command_callback_result").get("branch")
        if branch != "precondition-disabled":
            failures.append(f"command_callback: branch is {branch}, expected precondition-disabled")
    elif name == "enabled_callback":
        if summary.get("command_callback_ok") is not True:
            failures.append("enabled_callback: callback entry is not proven")
        if summary.get("command_callback_result_ok") is not True:
            failures.append("enabled_callback: callback result is not proven")
        if summary.get("command_render_begin_skip_seen") is not True:
            failures.append("enabled_callback: render-begin skip row is not proven")
        branch = row_values(summary, "last_command_callback_result").get("branch")
        if branch != "state2":
            failures.append(f"enabled_callback: branch is {branch}, expected state2")
    elif name == "grid_hit":
        if summary.get("grid_hit_ok") is not True:
            failures.append("grid_hit: grid hit is not proven")
        visual_cell = row_values(summary, "last_grid_result").get("cell")
        native_cell = row_values(summary, "last_grid_hit").get("cell")
        if visual_cell != [1, 1]:
            failures.append(f"grid_hit: visual result cell is {visual_cell}, expected [1, 1]")
        if native_cell != [0, 0]:
            failures.append(f"grid_hit: native hit cell is {native_cell}, expected [0, 0]")
    elif name == "centered_input":
        if summary.get("grid_input_wrapper_ok") is not True:
            failures.append("centered_input: grid input wrapper is not proven")
        if summary.get("descriptor_input_wrapper_ok") is not True:
            failures.append("centered_input: descriptor input wrapper is not proven")
        if summary.get("centered_input_wrapper_ok") is not True:
            failures.append("centered_input: combined centered input wrapper is not proven")
        grid_inner = row_values(summary, "last_grid_inputprobe_inner").get("mouse")
        descriptor_inner = row_values(summary, "last_descriptor_inputprobe_inner").get("mouse")
        if grid_inner != [64, 48]:
            failures.append(f"centered_input: grid inner mouse is {grid_inner}, expected [64, 48]")
        if descriptor_inner != [508, 380]:
            failures.append(f"centered_input: descriptor inner mouse is {descriptor_inner}, expected [508, 380]")
    elif name == "post_ready_redraw":
        if summary.get("post_ready_redraw_sample_ok") is not True:
            failures.append("post_ready_redraw: post-ready redraw sample is not proven")
        if int(summary.get("post_ready_presents") or 0) < 9:
            failures.append(f"post_ready_redraw: presents is {summary.get('post_ready_presents')}, expected at least 9")
        if int(summary.get("post_ready_copybacks") or 0) < 1:
            failures.append(f"post_ready_redraw: copybacks is {summary.get('post_ready_copybacks')}, expected at least 1")
        if int(summary.get("post_ready_grid_attempts") or 0) < 1:
            failures.append(
                f"post_ready_redraw: grid attempts is {summary.get('post_ready_grid_attempts')}, expected at least 1"
            )
        grid_native = row_values(summary, "last_post_ready_grid_attempt").get("native")
        last_ret = row_values(summary, "last_post_ready_summary").get("last_ret")
        if grid_native != [64, 48]:
            failures.append(f"post_ready_redraw: forced grid native point is {grid_native}, expected [64, 48]")
        if last_ret != 0x0042CB46:
            failures.append(f"post_ready_redraw: final present return is {last_ret}, expected 0x0042CB46")
    elif name == "modal_classified":
        if summary.get("modal_classified") is not True:
            failures.append("modal_classified: modal path was not classified")
        status = row_values(summary, "last_modal_classified").get("status")
        if status not in (None, "input_update_seen_no_modal"):
            failures.append(f"modal_classified: status is {status}")
    return failures


def patch_stage_gate(
    path: Path,
    *,
    expected_stage: str = EXPECTED_STAGE,
    expected_sha256: str = EXPECTED_BATTLE_SHA256,
    expected_groups: dict[str, int] | None = None,
) -> dict[str, Any]:
    expected_groups = expected_groups or {"battle-ui-center-present-wrapper": 2}
    payload, failures = maybe_load_json(path)
    if payload is None:
        return {"passed": False, "path": str(path), "failures": failures}
    if payload.get("stage") != expected_stage:
        failures.append(f"patch stage is {payload.get('stage')}, expected {expected_stage}")
    if str(payload.get("expected_base_sha256") or "").upper() != EXPECTED_BASE_SHA256:
        failures.append("patch-stage base SHA mismatch")
    status_counts = payload.get("status_counts") or {}
    if int(status_counts.get("original", 0) or 0):
        failures.append(f"patch-stage has original bytes: {status_counts.get('original')}")
    if int(status_counts.get("unexpected", 0) or 0):
        failures.append(f"patch-stage has unexpected bytes: {status_counts.get('unexpected')}")
    groups = payload.get("groups") or {}
    checked_groups: dict[str, Any] = {}
    for group_name, expected_total in expected_groups.items():
        group = groups.get(group_name) or {}
        checked_groups[group_name] = group
        if group.get("patched") != expected_total or group.get("total") != expected_total:
            failures.append(f"{group_name} group is {group}, expected {expected_total}/{expected_total}")
    if str(payload.get("exe_sha256") or "").upper() != expected_sha256:
        failures.append("candidate SHA mismatch in patch-stage report")
    return {
        "passed": not failures,
        "path": str(path),
        "stage": payload.get("stage"),
        "candidate": payload.get("exe"),
        "candidate_sha256": payload.get("exe_sha256"),
        "status_counts": status_counts,
        "groups": checked_groups,
        "failures": failures,
    }


def stable_smoke_gate(path: Path) -> dict[str, Any]:
    payload, failures = maybe_load_json(path)
    if payload is None:
        return {"passed": False, "path": str(path), "failures": failures}
    passed = bool(payload.get("passed") or payload.get("overall") == "PASS")
    if not passed:
        failures.append("stable HD-map smoke did not pass")
    return {
        "passed": not failures,
        "path": str(path),
        "candidate_sha256": payload.get("candidate_sha256")
        or (payload.get("patch_stage") or {}).get("sha256"),
        "failures": failures,
    }


def visible_input_gate(path: Path) -> dict[str, Any]:
    payload, failures = maybe_load_json(path)
    if payload is None:
        return {
            "passed": False,
            "path": str(path),
            "focused_completion_percent": None,
            "command_ready_run_count": 0,
            "click_consumed_run_count": 0,
            "invalid_run_count": 0,
            "real_visible_click_consumed": False,
            "open_items": [],
            "failures": failures,
        }
    command_ready_run_count = int(payload.get("command_ready_run_count") or 0)
    click_consumed_run_count = int(payload.get("click_consumed_run_count") or 0)
    invalid_run_count = int(payload.get("invalid_run_count") or 0)
    real_visible_click_consumed = bool(payload.get("real_visible_click_consumed"))
    summary_passed = bool(payload.get("passed"))
    if command_ready_run_count < 1:
        failures.append("visible input command readiness is not proven")
    if summary_passed and not real_visible_click_consumed:
        failures.append("visible input summary claims pass without real visible click consumption")
    if real_visible_click_consumed and click_consumed_run_count < 1:
        failures.append("visible input summary claims real click consumption but has no click-consumed run")
    focused_completion = payload.get("focused_completion_percent")
    if focused_completion is not None and float(focused_completion) >= 100.0 and not real_visible_click_consumed:
        failures.append("visible input focused completion claims 100% before real click consumption")
    open_items: list[str] = []
    if click_consumed_run_count < 1 or not real_visible_click_consumed:
        open_items.append("real visible click-to-callback proof remains open")
    if invalid_run_count:
        open_items.append(f"{invalid_run_count} invalid visible-input run(s) are retained as negative evidence")
    return {
        "passed": not failures,
        "path": str(path),
        "summary_passed": summary_passed,
        "focused_completion_percent": payload.get("focused_completion_percent"),
        "command_ready_run_count": command_ready_run_count,
        "click_consumed_run_count": click_consumed_run_count,
        "invalid_run_count": invalid_run_count,
        "real_visible_click_consumed": real_visible_click_consumed,
        "open_items": open_items,
        "failures": failures,
    }


def availability_gate(path: Path) -> dict[str, Any]:
    payload, failures = maybe_load_json(path)
    if payload is None:
        return {"passed": False, "path": str(path), "failures": failures}
    if payload.get("selected_unit_naturally_disabled") is not True:
        failures.append("selected unit is not classified as naturally disabled")
    if int(payload.get("naturally_enabled_unit_count") or 0) != 0:
        failures.append(f"natural enabled unit count is {payload.get('naturally_enabled_unit_count')}, expected 0")
    if int(payload.get("unit_count") or 0) <= 0:
        failures.append("no battle force-unit rows were parsed")
    return {
        "passed": not failures,
        "path": str(path),
        "unit_count": payload.get("unit_count"),
        "selected_unit_naturally_disabled": payload.get("selected_unit_naturally_disabled"),
        "naturally_enabled_unit_count": payload.get("naturally_enabled_unit_count"),
        "enabled_table_type_count": payload.get("enabled_table_type_count"),
        "enabled_table_type_names": [
            row.get("name_en") or f"type {row.get('unit_type')}"
            for row in payload.get("enabled_table_types", [])
        ],
        "failures": failures,
    }


def slot_scan_gate(path: Path) -> dict[str, Any]:
    payload, failures = maybe_load_json(path)
    if payload is None:
        return {"passed": False, "path": str(path), "failures": failures}
    if int(payload.get("natural_enabled_unit_count") or 0) != 0:
        failures.append(f"slot scan found natural enabled units: {payload.get('natural_enabled_unit_count')}")
    if int(payload.get("routed_slot_count") or 0) < 3:
        failures.append(f"slot scan routed only {payload.get('routed_slot_count')} slots, expected at least 3")
    if int(payload.get("run_count") or 0) < 6:
        failures.append(f"slot scan covered only {payload.get('run_count')} runs, expected at least 6")
    return {
        "passed": not failures,
        "path": str(path),
        "run_count": payload.get("run_count"),
        "routed_slot_count": payload.get("routed_slot_count"),
        "timeout_before_unit_scan_count": payload.get("timeout_before_unit_scan_count"),
        "natural_enabled_unit_count": payload.get("natural_enabled_unit_count"),
        "failures": failures,
    }


def save_inventory_gate(path: Path) -> dict[str, Any]:
    payload, failures = maybe_load_json(path)
    if payload is None:
        return {"passed": False, "path": str(path), "failures": failures}
    if int(payload.get("natural_enabled_unit_count") or 0) != 0:
        failures.append(f"save inventory found natural enabled units: {payload.get('natural_enabled_unit_count')}")
    if int(payload.get("slot_count") or 0) < 6:
        failures.append(f"save inventory covered only {payload.get('slot_count')} slots, expected at least 6")
    if int(payload.get("total_unit_count") or 0) <= 0:
        failures.append("save inventory parsed no unit records")
    if int(payload.get("save_memory_delta") or 0) != 16:
        failures.append(f"save inventory memory delta is {payload.get('save_memory_delta')}, expected 16")
    return {
        "passed": not failures,
        "path": str(path),
        "slot_count": payload.get("slot_count"),
        "total_unit_count": payload.get("total_unit_count"),
        "natural_enabled_unit_count": payload.get("natural_enabled_unit_count"),
        "save_memory_delta": payload.get("save_memory_delta"),
        "failures": failures,
    }


def constructed_fixture_gate(path: Path) -> dict[str, Any]:
    payload, failures = maybe_load_json(path)
    if payload is None:
        return {"passed": False, "path": str(path), "failures": failures}
    if payload.get("target_is_enabled") is not True:
        failures.append("constructed fixture target unit type is not enabled")
    if int(payload.get("old_enabled") or 0) != 0:
        failures.append(f"constructed fixture source unit already enabled: {payload.get('old_enabled')}")
    if int(payload.get("target_enabled") or 0) <= 0:
        failures.append(f"constructed fixture target enabled value is {payload.get('target_enabled')}")
    output_save = str(payload.get("output_save") or "")
    if output_save.replace("/", "\\").lower().startswith("c:\\clash\\save\\"):
        failures.append(f"constructed fixture output points at live save dir: {output_save}")
    status = "copied_save_written" if payload.get("wrote_output") else "dry_run_plan"
    return {
        "passed": not failures,
        "path": str(path),
        "status": status,
        "dry_run": payload.get("dry_run"),
        "wrote_output": payload.get("wrote_output"),
        "unit_index": payload.get("unit_index"),
        "unit_type_offset": payload.get("unit_type_offset"),
        "old_unit_type": payload.get("old_unit_type"),
        "old_name": payload.get("old_name"),
        "target_unit_type": payload.get("target_unit_type"),
        "target_name": payload.get("target_name"),
        "target_enabled": payload.get("target_enabled"),
        "failures": failures,
    }


def constructed_fixture_unit_scan_gate(path: Path) -> dict[str, Any]:
    payload, failures = maybe_load_json(path)
    if payload is None:
        return {"passed": False, "path": str(path), "failures": failures}
    if int(payload.get("unit_count") or 0) <= 0:
        failures.append("constructed fixture unit scan parsed no unit records")
    if int(payload.get("naturally_enabled_unit_count") or 0) < 1:
        failures.append(
            f"constructed fixture natural enabled count is {payload.get('naturally_enabled_unit_count')}, expected at least 1"
        )
    enabled_units = payload.get("naturally_enabled_units") or []
    first_enabled = enabled_units[0] if enabled_units else {}
    return {
        "passed": not failures,
        "path": str(path),
        "unit_count": payload.get("unit_count"),
        "naturally_enabled_unit_count": payload.get("naturally_enabled_unit_count"),
        "first_enabled_unit_type": first_enabled.get("unit_type"),
        "first_enabled_name": first_enabled.get("name_en"),
        "first_enabled_value": first_enabled.get("enabled"),
        "failures": failures,
    }


def constructed_fixture_command_gate(path: Path) -> dict[str, Any]:
    payload, failures = maybe_load_json(path)
    if payload is None:
        return {"passed": False, "path": str(path), "failures": failures}
    failures.extend(common_summary_failures("constructed_fixture_command", payload))
    if payload.get("command_callback_ok") is not True:
        failures.append("constructed fixture command callback entry is not proven")
    if payload.get("command_callback_result_ok") is not True:
        failures.append("constructed fixture command callback result is not proven")
    if payload.get("command_render_begin_skip_seen") is True:
        failures.append("constructed fixture command probe still skips render-begin")
    if payload.get("command_render_begin_enter_seen") is not True:
        failures.append("constructed fixture render-begin call entry is not proven")
    if payload.get("command_rearm_pre_gates_seen") is True:
        failures.append("constructed fixture command probe still rearms before click gate")
    if payload.get("command_pre_gates_seen") is not True:
        failures.append("constructed fixture command pre-gate state is not proven")
    if payload.get("command_synthetic_release_seen") is not True:
        failures.append("constructed fixture synthetic click release is not proven")
    if payload.get("render_begin_guard_seen") is True:
        failures.append("constructed fixture render-begin still uses a hidden-harness guard")
    if payload.get("render_begin_exit_seen") is not True:
        failures.append("constructed fixture render-begin call exit is not proven")
    marker_counts = payload.get("marker_counts") or {}
    if int(marker_counts.get("BATTLE_COMMAND_FORCE_ENABLED_UNIT") or 0) != 0:
        failures.append("constructed fixture command probe still forced the unit type")
    if int(marker_counts.get("BATTLE_COMMAND_CLICK_GATE_FORCE") or 0) != 0:
        failures.append("constructed fixture command probe still forced the click gate")
    if int(marker_counts.get("BATTLE_COMMAND_CLICK_GATE_OBSERVED") or 0) < 1:
        failures.append("constructed fixture natural click gate was not observed")
    attempt_values = row_values(payload, "last_command_attempt")
    callback_values = row_values(payload, "last_command_callback")
    result_values = row_values(payload, "last_command_callback_result")
    if attempt_values.get("coord_mode") != "visual-click":
        failures.append(
            f"constructed fixture command attempt coord_mode is {attempt_values.get('coord_mode')}, expected visual-click"
        )
    if attempt_values.get("displayed") != [588, 440]:
        failures.append(
            f"constructed fixture command attempt displayed point is {attempt_values.get('displayed')}, expected [588, 440]"
        )
    if attempt_values.get("expected_native") != [508, 380]:
        failures.append(
            "constructed fixture command attempt expected native point is "
            f"{attempt_values.get('expected_native')}, expected [508, 380]"
        )
    if callback_values.get("unit_type") != 8:
        failures.append(f"constructed fixture callback unit type is {callback_values.get('unit_type')}, expected 8")
    if callback_values.get("enabled") != 3:
        failures.append(f"constructed fixture callback enabled is {callback_values.get('enabled')}, expected 3")
    if result_values.get("branch") not in ("state1", "state2"):
        failures.append(f"constructed fixture callback branch is {result_values.get('branch')}")
    return {
        "passed": not failures,
        "path": str(path),
        "candidate_sha256": payload.get("candidate_sha256"),
        "screenshot": payload.get("screenshot"),
        "attempt_coord_mode": attempt_values.get("coord_mode"),
        "attempt_displayed": attempt_values.get("displayed"),
        "attempt_expected_native": attempt_values.get("expected_native"),
        "unit_type": callback_values.get("unit_type"),
        "availability": callback_values.get("avail"),
        "enabled": callback_values.get("enabled"),
        "branch": result_values.get("branch"),
        "forced_unit_rows": marker_counts.get("BATTLE_COMMAND_FORCE_ENABLED_UNIT"),
        "forced_click_gate_rows": marker_counts.get("BATTLE_COMMAND_CLICK_GATE_FORCE"),
        "observed_click_gate_rows": marker_counts.get("BATTLE_COMMAND_CLICK_GATE_OBSERVED"),
        "render_begin_skip_seen": payload.get("command_render_begin_skip_seen"),
        "render_begin_enter_seen": payload.get("command_render_begin_enter_seen"),
        "rearm_pre_gates_seen": payload.get("command_rearm_pre_gates_seen"),
        "pre_gates_seen": payload.get("command_pre_gates_seen"),
        "synthetic_release_seen": payload.get("command_synthetic_release_seen"),
        "render_begin_guard_seen": payload.get("render_begin_guard_seen"),
        "render_begin_exit_seen": payload.get("render_begin_exit_seen"),
        "failures": failures,
    }


def build_matrix(args: argparse.Namespace) -> dict[str, Any]:
    paths = {
        "force_entry": args.force_entry_json,
        "command_hit": args.command_hit_json,
        "command_callback": args.command_callback_json,
        "enabled_callback": args.enabled_callback_json,
        "grid_hit": args.grid_hit_json,
        "centered_input": args.centered_input_json,
        "post_ready_redraw": args.post_ready_redraw_json,
        "modal_classified": args.modal_classified_json,
    }
    summaries: dict[str, Any] = {}
    checks: dict[str, Any] = {}
    failures: list[str] = []

    for name in SUMMARY_NAMES:
        payload, load_failures = maybe_load_json(paths[name])
        if payload is None:
            checks[name] = {"passed": False, "path": str(paths[name]), "failures": load_failures}
            failures.extend(load_failures)
            continue
        check_failures = common_summary_failures(name, payload)
        check_failures.extend(feature_failures(name, payload))
        summaries[name] = payload
        checks[name] = {
            "passed": not check_failures,
            "path": str(paths[name]),
            "candidate_sha256": payload.get("candidate_sha256"),
            "screenshot": payload.get("screenshot"),
            "failures": check_failures,
        }
        failures.extend(check_failures)

    patch_stage = patch_stage_gate(args.patch_stage_json)
    input_patch_stage = patch_stage_gate(
        args.input_patch_stage_json,
        expected_stage=EXPECTED_INPUT_STAGE,
        expected_sha256=EXPECTED_INPUT_SHA256,
        expected_groups={
            "battle-ui-center-present-wrapper": 2,
            "battle-grid-centered-input": 2,
            "battle-ui-centered-input": 2,
        },
    )
    stable_smoke = stable_smoke_gate(args.stable_smoke_json)
    availability = availability_gate(args.availability_json)
    slot_scan = slot_scan_gate(args.slot_scan_json)
    save_inventory = save_inventory_gate(args.save_inventory_json)
    constructed_fixture = constructed_fixture_gate(args.constructed_fixture_json)
    constructed_fixture_unit_scan = constructed_fixture_unit_scan_gate(args.constructed_fixture_unit_scan_json)
    constructed_fixture_command = constructed_fixture_command_gate(args.constructed_fixture_command_json)
    visible_input = visible_input_gate(args.visible_input_json)
    checks["patch_stage"] = patch_stage
    checks["input_patch_stage"] = input_patch_stage
    checks["availability_scan"] = availability
    checks["slot_scan"] = slot_scan
    checks["save_inventory"] = save_inventory
    checks["constructed_fixture_plan"] = constructed_fixture
    checks["constructed_fixture_unit_scan"] = constructed_fixture_unit_scan
    checks["constructed_fixture_command"] = constructed_fixture_command
    checks["stable_smoke"] = stable_smoke
    checks["visible_input"] = visible_input
    failures.extend(f"patch_stage: {failure}" for failure in patch_stage["failures"])
    failures.extend(f"input_patch_stage: {failure}" for failure in input_patch_stage["failures"])
    failures.extend(f"availability_scan: {failure}" for failure in availability["failures"])
    failures.extend(f"slot_scan: {failure}" for failure in slot_scan["failures"])
    failures.extend(f"save_inventory: {failure}" for failure in save_inventory["failures"])
    failures.extend(f"constructed_fixture_plan: {failure}" for failure in constructed_fixture["failures"])
    failures.extend(
        f"constructed_fixture_unit_scan: {failure}" for failure in constructed_fixture_unit_scan["failures"]
    )
    failures.extend(
        f"constructed_fixture_command: {failure}" for failure in constructed_fixture_command["failures"]
    )
    failures.extend(f"stable_smoke: {failure}" for failure in stable_smoke["failures"])
    failures.extend(f"visible_input: {failure}" for failure in visible_input["failures"])

    candidate_values = {
        str(value).upper()
        for value in [patch_stage.get("candidate_sha256"), input_patch_stage.get("candidate_sha256")]
        + [summary.get("candidate_sha256") for summary in summaries.values()]
        if value
    }
    expected_candidate_values = {EXPECTED_BATTLE_SHA256, EXPECTED_INPUT_SHA256}
    if not candidate_values or not candidate_values.issubset(expected_candidate_values):
        failures.append(f"battle candidate SHA values are {sorted(candidate_values)}")
    if EXPECTED_BATTLE_SHA256 not in candidate_values:
        failures.append("battlecenter candidate SHA was not observed")
    if EXPECTED_INPUT_SHA256 not in candidate_values:
        failures.append("battle inputprobe candidate SHA was not observed")

    return {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "passed": not failures,
        "runtime_policy": "repo-only; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows",
        "stage": EXPECTED_STAGE,
        "input_stage": EXPECTED_INPUT_STAGE,
        "candidate_sha256": EXPECTED_BATTLE_SHA256 if EXPECTED_BATTLE_SHA256 in candidate_values else None,
        "input_candidate_sha256": EXPECTED_INPUT_SHA256 if EXPECTED_INPUT_SHA256 in candidate_values else None,
        "promotion_status": "validation_stage_only",
        "stable_stage_should_change": False,
        "checks": checks,
        "key_evidence": {
            "centered_visual": summaries.get("force_entry", {}).get("visual_mode"),
            "command_hit_ok": summaries.get("command_hit", {}).get("command_hit_ok"),
            "command_native_hit_ok": summaries.get("command_hit", {}).get("command_native_hit_ok"),
            "command_callback_branch": row_values(summaries.get("command_callback", {}), "last_command_callback_result").get("branch"),
            "enabled_callback_branch": row_values(summaries.get("enabled_callback", {}), "last_command_callback_result").get("branch"),
            "grid_visual_cell": row_values(summaries.get("grid_hit", {}), "last_grid_result").get("cell"),
            "grid_native_cell": row_values(summaries.get("grid_hit", {}), "last_grid_hit").get("cell"),
            "centered_input_wrapper_ok": summaries.get("centered_input", {}).get("centered_input_wrapper_ok"),
            "grid_input_inner_mouse": row_values(summaries.get("centered_input", {}), "last_grid_inputprobe_inner").get("mouse"),
            "descriptor_input_inner_mouse": row_values(summaries.get("centered_input", {}), "last_descriptor_inputprobe_inner").get("mouse"),
            "post_ready_redraw_sample_ok": summaries.get("post_ready_redraw", {}).get("post_ready_redraw_sample_ok"),
            "post_ready_presents": summaries.get("post_ready_redraw", {}).get("post_ready_presents"),
            "post_ready_copybacks": summaries.get("post_ready_redraw", {}).get("post_ready_copybacks"),
            "post_ready_grid_native": row_values(summaries.get("post_ready_redraw", {}), "last_post_ready_grid_attempt").get("native"),
            "post_ready_last_present_ret": hex_or_none(
                row_values(summaries.get("post_ready_redraw", {}), "last_post_ready_summary").get("last_ret")
            ),
            "natural_enabled_unit_count": availability.get("naturally_enabled_unit_count"),
            "selected_unit_naturally_disabled": availability.get("selected_unit_naturally_disabled"),
            "enabled_table_type_count": availability.get("enabled_table_type_count"),
            "enabled_table_type_names": availability.get("enabled_table_type_names"),
            "slot_scan_routed_slots": slot_scan.get("routed_slot_count"),
            "slot_scan_timeouts": slot_scan.get("timeout_before_unit_scan_count"),
            "slot_scan_natural_enabled_units": slot_scan.get("natural_enabled_unit_count"),
            "save_inventory_slots": save_inventory.get("slot_count"),
            "save_inventory_units": save_inventory.get("total_unit_count"),
            "save_inventory_natural_enabled_units": save_inventory.get("natural_enabled_unit_count"),
            "constructed_fixture_status": constructed_fixture.get("status"),
            "constructed_fixture_change": (
                f"{constructed_fixture.get('old_name')} -> {constructed_fixture.get('target_name')}"
                if constructed_fixture.get("old_name") or constructed_fixture.get("target_name")
                else None
            ),
            "constructed_fixture_type_offset": constructed_fixture.get("unit_type_offset"),
            "constructed_fixture_natural_enabled_units": constructed_fixture_unit_scan.get(
                "naturally_enabled_unit_count"
            ),
            "constructed_fixture_enabled_unit": constructed_fixture_unit_scan.get("first_enabled_name"),
            "constructed_fixture_attempt_coord_mode": constructed_fixture_command.get("attempt_coord_mode"),
            "constructed_fixture_attempt_displayed": constructed_fixture_command.get("attempt_displayed"),
            "constructed_fixture_attempt_expected_native": constructed_fixture_command.get(
                "attempt_expected_native"
            ),
            "constructed_fixture_callback_unit_type": constructed_fixture_command.get("unit_type"),
            "constructed_fixture_callback_enabled": constructed_fixture_command.get("enabled"),
            "constructed_fixture_callback_branch": constructed_fixture_command.get("branch"),
            "constructed_fixture_forced_unit_rows": constructed_fixture_command.get("forced_unit_rows"),
            "constructed_fixture_forced_click_gate_rows": constructed_fixture_command.get("forced_click_gate_rows"),
            "constructed_fixture_observed_click_gate_rows": constructed_fixture_command.get(
                "observed_click_gate_rows"
            ),
            "constructed_fixture_render_begin_skip_seen": constructed_fixture_command.get(
                "render_begin_skip_seen"
            ),
            "constructed_fixture_render_begin_enter_seen": constructed_fixture_command.get(
                "render_begin_enter_seen"
            ),
            "constructed_fixture_rearm_pre_gates_seen": constructed_fixture_command.get(
                "rearm_pre_gates_seen"
            ),
            "constructed_fixture_pre_gates_seen": constructed_fixture_command.get("pre_gates_seen"),
            "constructed_fixture_synthetic_release_seen": constructed_fixture_command.get(
                "synthetic_release_seen"
            ),
            "constructed_fixture_render_begin_guard_seen": constructed_fixture_command.get(
                "render_begin_guard_seen"
            ),
            "constructed_fixture_render_begin_exit_seen": constructed_fixture_command.get(
                "render_begin_exit_seen"
            ),
            "modal_classified": summaries.get("modal_classified", {}).get("modal_classified"),
            "visible_input_focused_completion_percent": visible_input.get("focused_completion_percent"),
            "visible_input_summary_passed": visible_input.get("summary_passed"),
            "visible_input_command_ready_runs": visible_input.get("command_ready_run_count"),
            "visible_input_click_consumed_runs": visible_input.get("click_consumed_run_count"),
            "visible_input_invalid_runs": visible_input.get("invalid_run_count"),
            "visible_input_real_click_consumed": visible_input.get("real_visible_click_consumed"),
        },
        "completion_summary": {
            "focused_area": "battle/right-bottom command lane",
            "focused_completion_percent": visible_input.get("focused_completion_percent"),
            "real_visible_click_consumed": visible_input.get("real_visible_click_consumed"),
            "full_game_complete": False,
            "full_game_completion_percent": None,
            "full_game_statement": "Full-game reverse engineering is not 100%.",
            "remaining_blocker": (
                "real visible click-to-callback proof"
                if not visible_input.get("real_visible_click_consumed")
                else None
            ),
        },
        "open_items": visible_input.get("open_items", []),
        "failures": failures,
    }


def write_markdown(path: Path, matrix: dict[str, Any]) -> None:
    lines = [
        "# Battle UI Evidence Matrix",
        "",
        f"- Overall: {status_text(bool(matrix['passed']))}",
        f"- Generated: `{matrix['generated_at']}`",
        f"- Runtime policy: {matrix['runtime_policy']}",
        f"- Stage: `{matrix['stage']}`",
        f"- Inputprobe stage: `{matrix['input_stage']}`",
        f"- Candidate SHA-256: `{matrix.get('candidate_sha256')}`",
        f"- Input candidate SHA-256: `{matrix.get('input_candidate_sha256')}`",
        f"- Promotion status: `{matrix['promotion_status']}`",
        f"- Stable stage should change: `{matrix['stable_stage_should_change']}`",
        "",
        "## Completion Summary",
        "",
        f"- Focused area: `{matrix['completion_summary']['focused_area']}`",
        f"- Focused completion: `{matrix['completion_summary']['focused_completion_percent']}%`",
        (
            "- Real visible click-to-callback proof: `"
            + ("proven" if matrix["completion_summary"]["real_visible_click_consumed"] else "open")
            + "`"
        ),
        f"- Full-game status: `{matrix['completion_summary']['full_game_statement']}`",
        f"- Remaining blocker: `{matrix['completion_summary']['remaining_blocker']}`",
        "",
        "## Checks",
        "",
    ]
    for name, check in matrix["checks"].items():
        lines.append(f"- {name}: {status_text(bool(check.get('passed')))}")
    lines.extend(["", "## Key Evidence", ""])
    for key, value in matrix["key_evidence"].items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(["", "## Failures", ""])
    if matrix["failures"]:
        lines.extend(f"- {failure}" for failure in matrix["failures"])
    else:
        lines.append("- None")
    lines.extend(["", "## Open Items", ""])
    if matrix.get("open_items"):
        lines.extend(f"- {item}" for item in matrix["open_items"])
    else:
        lines.append("- None")
    screenshots = [
        check.get("screenshot")
        for name, check in matrix["checks"].items()
        if name in SCREENSHOT_CHECK_NAMES and check.get("screenshot")
    ]
    if screenshots:
        lines.extend(["", "## Screenshots", ""])
        for screenshot in screenshots:
            lines.append(f"![battle UI evidence]({markdown_image_ref(screenshot, path)})")
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force-entry-json", type=Path, default=DEFAULT_FORCE_ENTRY_JSON)
    parser.add_argument("--command-hit-json", type=Path, default=DEFAULT_COMMAND_HIT_JSON)
    parser.add_argument("--command-callback-json", type=Path, default=DEFAULT_COMMAND_CALLBACK_JSON)
    parser.add_argument("--enabled-callback-json", type=Path, default=DEFAULT_ENABLED_CALLBACK_JSON)
    parser.add_argument("--grid-hit-json", type=Path, default=DEFAULT_GRID_HIT_JSON)
    parser.add_argument("--centered-input-json", type=Path, default=DEFAULT_CENTERED_INPUT_JSON)
    parser.add_argument("--post-ready-redraw-json", type=Path, default=DEFAULT_POST_READY_REDRAW_JSON)
    parser.add_argument("--modal-classified-json", type=Path, default=DEFAULT_MODAL_CLASSIFIED_JSON)
    parser.add_argument("--patch-stage-json", type=Path, default=DEFAULT_PATCH_STAGE_JSON)
    parser.add_argument("--input-patch-stage-json", type=Path, default=DEFAULT_INPUT_PATCH_STAGE_JSON)
    parser.add_argument("--availability-json", type=Path, default=DEFAULT_AVAILABILITY_JSON)
    parser.add_argument("--slot-scan-json", type=Path, default=DEFAULT_SLOT_SCAN_JSON)
    parser.add_argument("--save-inventory-json", type=Path, default=DEFAULT_SAVE_INVENTORY_JSON)
    parser.add_argument("--constructed-fixture-json", type=Path, default=DEFAULT_CONSTRUCTED_FIXTURE_JSON)
    parser.add_argument(
        "--constructed-fixture-unit-scan-json",
        type=Path,
        default=DEFAULT_CONSTRUCTED_FIXTURE_UNIT_SCAN_JSON,
    )
    parser.add_argument(
        "--constructed-fixture-command-json",
        type=Path,
        default=DEFAULT_CONSTRUCTED_FIXTURE_COMMAND_JSON,
    )
    parser.add_argument("--stable-smoke-json", type=Path, default=DEFAULT_STABLE_SMOKE_JSON)
    parser.add_argument("--visible-input-json", type=Path, default=DEFAULT_VISIBLE_INPUT_JSON)
    parser.add_argument("--write-json", type=Path, default=DEFAULT_MATRIX_JSON)
    parser.add_argument("--write-markdown", "--write-md", dest="write_markdown", type=Path, default=DEFAULT_MATRIX_MD)
    parser.add_argument("--require-pass", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    matrix = build_matrix(args)
    print(f"overall: {status_text(bool(matrix['passed']))}")
    print(f"runtime-policy: {matrix['runtime_policy']}")
    print(f"promotion-status: {matrix['promotion_status']}")
    print(f"candidate-sha256: {matrix.get('candidate_sha256')}")
    print(f"input-candidate-sha256: {matrix.get('input_candidate_sha256')}")
    completion = matrix["completion_summary"]
    print(f"focused-completion: {completion['focused_completion_percent']}%")
    print(f"full-game-status: {completion['full_game_statement']}")
    print(f"failures: {len(matrix['failures'])}")
    for failure in matrix["failures"]:
        print(f"  - {failure}")
    if args.write_json:
        args.write_json.parent.mkdir(parents=True, exist_ok=True)
        args.write_json.write_text(json.dumps(matrix, indent=2) + "\n", encoding="utf-8")
    if args.write_markdown:
        write_markdown(args.write_markdown, matrix)
    if args.require_pass and not matrix["passed"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
