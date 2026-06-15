#!/usr/bin/env python3
"""Fixture tests for the battle UI evidence matrix helper."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from copy import deepcopy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "battle_ui_evidence_matrix.py"
sys.path.insert(0, str(ROOT / "tools"))

import battle_ui_evidence_matrix  # noqa: E402


SHA = battle_ui_evidence_matrix.EXPECTED_BATTLE_SHA256
INPUT_SHA = battle_ui_evidence_matrix.EXPECTED_INPUT_SHA256


def run_script(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def summary(**overrides) -> dict:
    payload = {
        "battle_ready": True,
        "surface_size": [800, 600],
        "visual_mode": "centered-native-640x480",
        "centered_offset": [80, 60],
        "centered_wrapper_seen": True,
        "av_count": 0,
        "hidden_desktop": True,
        "candidate": r"C:\ClashTests\battle\clash95_hd_battle.exe",
        "candidate_sha256": SHA,
        "screenshot": r"captures\fixture\surface.png",
    }
    payload.update(overrides)
    return payload


def good_payloads() -> dict[str, dict]:
    return {
        "force_entry": summary(),
        "command_hit": summary(command_hit_ok=True, command_native_hit_ok=True),
        "command_callback": summary(
            command_callback_ok=True,
            command_callback_result_ok=True,
            last_command_callback_result={"values": {"branch": "precondition-disabled"}},
        ),
        "enabled_callback": summary(
            command_callback_ok=True,
            command_callback_result_ok=True,
            command_render_begin_skip_seen=True,
            last_command_callback_result={"values": {"branch": "state2"}},
        ),
        "grid_hit": summary(
            grid_hit_ok=True,
            last_grid_result={"values": {"cell": [1, 1]}},
            last_grid_hit={"values": {"cell": [0, 0]}},
        ),
        "centered_input": summary(
            candidate=r"C:\ClashTests\battle-inputprobe\clash95_hd_battle_input.exe",
            candidate_sha256=INPUT_SHA,
            grid_input_wrapper_ok=True,
            descriptor_input_wrapper_ok=True,
            centered_input_wrapper_ok=True,
            last_grid_inputprobe_inner={"values": {"mouse": [64, 48]}},
            last_descriptor_inputprobe_inner={"values": {"mouse": [508, 380]}},
        ),
        "post_ready_redraw": summary(
            post_ready_redraw_sample_ok=True,
            post_ready_presents=9,
            post_ready_copybacks=6,
            post_ready_grid_attempts=1,
            last_post_ready_grid_attempt={"values": {"native": [64, 48]}},
            last_post_ready_summary={"values": {"last_ret": 0x0042CB46}},
        ),
        "modal_classified": summary(
            modal_classified=True,
            last_modal_classified={"values": {"status": "input_update_seen_no_modal"}},
        ),
    }


def write_json(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def write_fixture(fixture: Path, payloads: dict[str, dict] | None = None) -> argparse.Namespace:
    payloads = payloads or good_payloads()
    paths = {name: write_json(fixture / f"{name}.json", payload) for name, payload in payloads.items()}
    patch_stage = write_json(
        fixture / "patch-stage.json",
        {
            "exe": r"C:\ClashTests\battle\clash95_hd_battle.exe",
            "stage": battle_ui_evidence_matrix.EXPECTED_STAGE,
            "exe_sha256": SHA,
            "expected_base_sha256": battle_ui_evidence_matrix.EXPECTED_BASE_SHA256,
            "status_counts": {"patched": 136, "original": 0, "unexpected": 0},
            "groups": {"battle-ui-center-present-wrapper": {"patched": 2, "total": 2}},
        },
    )
    input_patch_stage = write_json(
        fixture / "input-patch-stage.json",
        {
            "exe": r"C:\ClashTests\battle-inputprobe\clash95_hd_battle_input.exe",
            "stage": battle_ui_evidence_matrix.EXPECTED_INPUT_STAGE,
            "exe_sha256": INPUT_SHA,
            "expected_base_sha256": battle_ui_evidence_matrix.EXPECTED_BASE_SHA256,
            "status_counts": {"patched": 140, "original": 0, "unexpected": 0},
            "groups": {
                "battle-ui-center-present-wrapper": {"patched": 2, "total": 2},
                "battle-grid-centered-input": {"patched": 2, "total": 2},
                "battle-ui-centered-input": {"patched": 2, "total": 2},
            },
        },
    )
    availability = write_json(
        fixture / "availability.json",
        {
            "unit_count": 18,
            "selected_unit_naturally_disabled": True,
            "naturally_enabled_unit_count": 0,
            "enabled_table_type_count": 11,
            "enabled_table_types": [
                {"unit_type": 8, "name_en": "Dragon cavalry"},
                {"unit_type": 9, "name_en": "Archer"},
            ],
        },
    )
    slot_scan = write_json(
        fixture / "slot-scan.json",
        {
            "run_count": 6,
            "routed_slot_count": 3,
            "timeout_before_unit_scan_count": 3,
            "natural_enabled_unit_count": 0,
        },
    )
    save_inventory = write_json(
        fixture / "save-inventory.json",
        {
            "slot_count": 6,
            "total_unit_count": 63,
            "natural_enabled_unit_count": 0,
            "save_memory_delta": 16,
        },
    )
    constructed_fixture = write_json(
        fixture / "constructed-fixture.json",
        {
            "dry_run": True,
            "wrote_output": False,
            "output_save": None,
            "unit_index": 0,
            "unit_type_offset": "0x00023EFC",
            "old_unit_type": 5,
            "old_name": "Light cavalry",
            "old_enabled": 0,
            "target_unit_type": 8,
            "target_name": "Dragon cavalry",
            "target_enabled": 3,
            "target_is_enabled": True,
        },
    )
    constructed_fixture_unit_scan = write_json(
        fixture / "constructed-fixture-unit-scan.json",
        {
            "unit_count": 18,
            "naturally_enabled_unit_count": 1,
            "naturally_enabled_units": [
                {"unit_type": 8, "name_en": "Dragon cavalry", "enabled": 3},
            ],
        },
    )
    constructed_fixture_command = write_json(
        fixture / "constructed-fixture-command.json",
        summary(
            command_callback_ok=True,
            command_callback_result_ok=True,
            command_render_begin_skip_seen=False,
            command_render_begin_enter_seen=True,
            command_rearm_pre_gates_seen=False,
            command_pre_gates_seen=True,
            command_synthetic_release_seen=True,
            render_begin_guard_seen=False,
            render_begin_exit_seen=True,
            marker_counts={
                "BATTLE_COMMAND_FORCE_ENABLED_UNIT": 0,
                "BATTLE_COMMAND_CLICK_GATE_FORCE": 0,
                "BATTLE_COMMAND_CLICK_GATE_OBSERVED": 1,
                "BATTLE_COMMAND_REARM_PRE_GATES": 0,
                "BATTLE_COMMAND_PRE_GATES": 1,
                "BATTLE_COMMAND_RENDER_BEGIN_SKIP": 0,
                "BATTLE_COMMAND_RENDER_BEGIN_ENTER": 1,
                "BATTLE_COMMAND_SYNTHETIC_RELEASE": 1,
                "BATTLE_RENDER_BEGIN_EXIT": 1,
            },
            last_command_attempt={
                "values": {
                    "coord_mode": "visual-click",
                    "displayed": [588, 440],
                    "expected_native": [508, 380],
                },
            },
            last_command_callback={"values": {"unit_type": 8, "avail": 10, "enabled": 3}},
            last_command_callback_result={"values": {"branch": "state1"}},
        ),
    )
    stable = write_json(fixture / "stable-smoke.json", {"passed": True})
    visible_input = write_json(
        fixture / "visible-input.json",
        {
            "focused_completion_percent": 99.91,
            "command_ready_run_count": 2,
            "click_consumed_run_count": 0,
            "invalid_run_count": 1,
            "passed": False,
            "real_visible_click_consumed": False,
        },
    )
    return argparse.Namespace(
        force_entry_json=paths["force_entry"],
        command_hit_json=paths["command_hit"],
        command_callback_json=paths["command_callback"],
        enabled_callback_json=paths["enabled_callback"],
        grid_hit_json=paths["grid_hit"],
        centered_input_json=paths["centered_input"],
        post_ready_redraw_json=paths["post_ready_redraw"],
        modal_classified_json=paths["modal_classified"],
        patch_stage_json=patch_stage,
        input_patch_stage_json=input_patch_stage,
        availability_json=availability,
        slot_scan_json=slot_scan,
        save_inventory_json=save_inventory,
        constructed_fixture_json=constructed_fixture,
        constructed_fixture_unit_scan_json=constructed_fixture_unit_scan,
        constructed_fixture_command_json=constructed_fixture_command,
        stable_smoke_json=stable,
        visible_input_json=visible_input,
    )


def test_matrix_passes_with_current_evidence_shape(fixture: Path) -> None:
    matrix = battle_ui_evidence_matrix.build_matrix(write_fixture(fixture))
    assert matrix["passed"] is True, matrix
    assert matrix["promotion_status"] == "validation_stage_only", matrix
    assert matrix["stable_stage_should_change"] is False, matrix
    assert matrix["key_evidence"]["grid_visual_cell"] == [1, 1], matrix
    assert matrix["key_evidence"]["grid_native_cell"] == [0, 0], matrix
    assert matrix["key_evidence"]["centered_input_wrapper_ok"] is True, matrix
    assert matrix["key_evidence"]["post_ready_redraw_sample_ok"] is True, matrix
    assert matrix["key_evidence"]["post_ready_last_present_ret"] == "0x0042CB46", matrix
    assert matrix["key_evidence"]["natural_enabled_unit_count"] == 0, matrix
    assert matrix["key_evidence"]["enabled_table_type_count"] == 11, matrix
    assert matrix["key_evidence"]["enabled_table_type_names"] == ["Dragon cavalry", "Archer"], matrix
    assert matrix["key_evidence"]["slot_scan_routed_slots"] == 3, matrix
    assert matrix["key_evidence"]["slot_scan_natural_enabled_units"] == 0, matrix
    assert matrix["key_evidence"]["save_inventory_slots"] == 6, matrix
    assert matrix["key_evidence"]["save_inventory_units"] == 63, matrix
    assert matrix["key_evidence"]["constructed_fixture_status"] == "dry_run_plan", matrix
    assert matrix["key_evidence"]["constructed_fixture_change"] == "Light cavalry -> Dragon cavalry", matrix
    assert matrix["key_evidence"]["constructed_fixture_natural_enabled_units"] == 1, matrix
    assert matrix["key_evidence"]["constructed_fixture_enabled_unit"] == "Dragon cavalry", matrix
    assert matrix["key_evidence"]["constructed_fixture_attempt_coord_mode"] == "visual-click", matrix
    assert matrix["key_evidence"]["constructed_fixture_attempt_displayed"] == [588, 440], matrix
    assert matrix["key_evidence"]["constructed_fixture_attempt_expected_native"] == [508, 380], matrix
    assert matrix["key_evidence"]["constructed_fixture_callback_unit_type"] == 8, matrix
    assert matrix["key_evidence"]["constructed_fixture_callback_enabled"] == 3, matrix
    assert matrix["key_evidence"]["constructed_fixture_callback_branch"] == "state1", matrix
    assert matrix["key_evidence"]["constructed_fixture_forced_unit_rows"] == 0, matrix
    assert matrix["key_evidence"]["constructed_fixture_forced_click_gate_rows"] == 0, matrix
    assert matrix["key_evidence"]["constructed_fixture_observed_click_gate_rows"] == 1, matrix
    assert matrix["key_evidence"]["constructed_fixture_render_begin_skip_seen"] is False, matrix
    assert matrix["key_evidence"]["constructed_fixture_render_begin_enter_seen"] is True, matrix
    assert matrix["key_evidence"]["constructed_fixture_rearm_pre_gates_seen"] is False, matrix
    assert matrix["key_evidence"]["constructed_fixture_pre_gates_seen"] is True, matrix
    assert matrix["key_evidence"]["constructed_fixture_synthetic_release_seen"] is True, matrix
    assert matrix["key_evidence"]["constructed_fixture_render_begin_guard_seen"] is False, matrix
    assert matrix["key_evidence"]["constructed_fixture_render_begin_exit_seen"] is True, matrix
    assert matrix["key_evidence"]["visible_input_focused_completion_percent"] == 99.91, matrix
    assert matrix["key_evidence"]["visible_input_summary_passed"] is False, matrix
    assert matrix["key_evidence"]["visible_input_command_ready_runs"] == 2, matrix
    assert matrix["key_evidence"]["visible_input_click_consumed_runs"] == 0, matrix
    assert matrix["key_evidence"]["visible_input_invalid_runs"] == 1, matrix
    assert matrix["key_evidence"]["visible_input_real_click_consumed"] is False, matrix
    assert matrix["checks"]["visible_input"]["passed"] is True, matrix
    assert matrix["completion_summary"]["focused_area"] == "battle/right-bottom command lane", matrix
    assert matrix["completion_summary"]["focused_completion_percent"] == 99.91, matrix
    assert matrix["completion_summary"]["real_visible_click_consumed"] is False, matrix
    assert matrix["completion_summary"]["full_game_complete"] is False, matrix
    assert matrix["completion_summary"]["full_game_statement"] == "Full-game reverse engineering is not 100%.", matrix
    assert matrix["completion_summary"]["remaining_blocker"] == "real visible click-to-callback proof", matrix
    assert "real visible click-to-callback proof remains open" in matrix["open_items"], matrix
    assert matrix["input_candidate_sha256"] == INPUT_SHA, matrix


def test_matrix_fails_closed_for_each_summary(fixture: Path) -> None:
    for name in battle_ui_evidence_matrix.SUMMARY_NAMES:
        payloads = good_payloads()
        payloads[name] = deepcopy(payloads[name])
        payloads[name]["av_count"] = 1
        matrix = battle_ui_evidence_matrix.build_matrix(write_fixture(fixture / name, payloads))
        assert matrix["passed"] is False, matrix
        assert any(name in failure and "AV rows" in failure for failure in matrix["failures"]), matrix


def test_matrix_rejects_feature_regressions(fixture: Path) -> None:
    cases = [
        ("command_hit", "command_hit_ok", False, "visual command hit"),
        ("command_hit", "command_native_hit_ok", False, "native command hit"),
        ("enabled_callback", "command_render_begin_skip_seen", False, "render-begin skip"),
        ("grid_hit", "grid_hit_ok", False, "grid hit"),
        ("centered_input", "centered_input_wrapper_ok", False, "centered input wrapper"),
        ("post_ready_redraw", "post_ready_redraw_sample_ok", False, "post-ready redraw sample"),
        ("modal_classified", "modal_classified", False, "modal path"),
    ]
    for name, key, value, expected in cases:
        payloads = good_payloads()
        payloads[name] = deepcopy(payloads[name])
        payloads[name][key] = value
        matrix = battle_ui_evidence_matrix.build_matrix(write_fixture(fixture / key, payloads))
        assert matrix["passed"] is False, matrix
        assert any(expected in failure for failure in matrix["failures"]), matrix


def test_matrix_rejects_constructed_fixture_render_guard(fixture: Path) -> None:
    args = write_fixture(fixture / "constructed-guard")
    path = Path(args.constructed_fixture_command_json)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["render_begin_guard_seen"] = True
    path.write_text(json.dumps(payload), encoding="utf-8")

    matrix = battle_ui_evidence_matrix.build_matrix(args)

    assert matrix["passed"] is False, matrix
    assert any("render-begin still uses" in failure for failure in matrix["failures"]), matrix


def test_matrix_rejects_missing_constructed_fixture_release(fixture: Path) -> None:
    args = write_fixture(fixture / "constructed-release")
    path = Path(args.constructed_fixture_command_json)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["command_synthetic_release_seen"] = False
    path.write_text(json.dumps(payload), encoding="utf-8")

    matrix = battle_ui_evidence_matrix.build_matrix(args)

    assert matrix["passed"] is False, matrix
    assert any("synthetic click release" in failure for failure in matrix["failures"]), matrix


def test_matrix_rejects_constructed_fixture_click_rearm(fixture: Path) -> None:
    args = write_fixture(fixture / "constructed-rearm")
    path = Path(args.constructed_fixture_command_json)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["command_rearm_pre_gates_seen"] = True
    path.write_text(json.dumps(payload), encoding="utf-8")

    matrix = battle_ui_evidence_matrix.build_matrix(args)

    assert matrix["passed"] is False, matrix
    assert any("rearms before click gate" in failure for failure in matrix["failures"]), matrix


def test_matrix_rejects_constructed_fixture_native_click_attempt(fixture: Path) -> None:
    args = write_fixture(fixture / "constructed-native-click")
    path = Path(args.constructed_fixture_command_json)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["last_command_attempt"]["values"]["coord_mode"] = "native-click"
    payload["last_command_attempt"]["values"]["displayed"] = [508, 380]
    payload["last_command_attempt"]["values"]["expected_native"] = None
    path.write_text(json.dumps(payload), encoding="utf-8")

    matrix = battle_ui_evidence_matrix.build_matrix(args)

    assert matrix["passed"] is False, matrix
    assert any("coord_mode" in failure for failure in matrix["failures"]), matrix


def test_matrix_rejects_missing_visible_command_readiness(fixture: Path) -> None:
    args = write_fixture(fixture / "visible-input")
    path = Path(args.visible_input_json)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["command_ready_run_count"] = 0
    path.write_text(json.dumps(payload), encoding="utf-8")

    matrix = battle_ui_evidence_matrix.build_matrix(args)

    assert matrix["passed"] is False, matrix
    assert any("visible input command readiness" in failure for failure in matrix["failures"]), matrix


def test_matrix_rejects_visible_input_overclaim_without_real_click(fixture: Path) -> None:
    args = write_fixture(fixture / "visible-overclaim")
    path = Path(args.visible_input_json)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["passed"] = True
    path.write_text(json.dumps(payload), encoding="utf-8")

    matrix = battle_ui_evidence_matrix.build_matrix(args)

    assert matrix["passed"] is False, matrix
    assert any("claims pass without real visible click" in failure for failure in matrix["failures"]), matrix


def test_matrix_rejects_visible_input_real_click_count_mismatch(fixture: Path) -> None:
    args = write_fixture(fixture / "visible-click-mismatch")
    path = Path(args.visible_input_json)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["real_visible_click_consumed"] = True
    payload["click_consumed_run_count"] = 0
    path.write_text(json.dumps(payload), encoding="utf-8")

    matrix = battle_ui_evidence_matrix.build_matrix(args)

    assert matrix["passed"] is False, matrix
    assert any("has no click-consumed run" in failure for failure in matrix["failures"]), matrix


def test_cli_writes_outputs_and_requires_pass(fixture: Path) -> None:
    args = write_fixture(fixture / "cli")
    out_json = fixture / "matrix.json"
    out_md = fixture / "matrix.md"
    run = run_script(
        "--force-entry-json",
        str(args.force_entry_json),
        "--command-hit-json",
        str(args.command_hit_json),
        "--command-callback-json",
        str(args.command_callback_json),
        "--enabled-callback-json",
        str(args.enabled_callback_json),
        "--grid-hit-json",
        str(args.grid_hit_json),
        "--centered-input-json",
        str(args.centered_input_json),
        "--post-ready-redraw-json",
        str(args.post_ready_redraw_json),
        "--modal-classified-json",
        str(args.modal_classified_json),
        "--patch-stage-json",
        str(args.patch_stage_json),
        "--input-patch-stage-json",
        str(args.input_patch_stage_json),
        "--availability-json",
        str(args.availability_json),
        "--slot-scan-json",
        str(args.slot_scan_json),
        "--save-inventory-json",
        str(args.save_inventory_json),
        "--constructed-fixture-json",
        str(args.constructed_fixture_json),
        "--constructed-fixture-unit-scan-json",
        str(args.constructed_fixture_unit_scan_json),
        "--constructed-fixture-command-json",
        str(args.constructed_fixture_command_json),
        "--stable-smoke-json",
        str(args.stable_smoke_json),
        "--visible-input-json",
        str(args.visible_input_json),
        "--write-json",
        str(out_json),
        "--write-md",
        str(out_md),
        "--require-pass",
    )
    assert run.returncode == 0, run.stdout + run.stderr
    assert json.loads(out_json.read_text(encoding="utf-8"))["passed"] is True
    written_markdown = out_md.read_text(encoding="utf-8")
    assert "- Overall: PASS" in written_markdown
    assert "## Completion Summary" in written_markdown
    assert "- Focused completion: `99.91%`" in written_markdown

    failing = run_script(
        "--force-entry-json",
        str(fixture / "missing.json"),
        "--write-json",
        str(fixture / "failing-matrix.json"),
        "--write-md",
        str(fixture / "failing-matrix.md"),
        "--require-pass",
    )
    assert failing.returncode == 2, failing.stdout + failing.stderr


def run_tests() -> None:
    fixture = ROOT / ".codex-loop" / "tmp-tests" / "battle-ui-evidence-matrix-fixture"
    shutil.rmtree(fixture, ignore_errors=True)
    fixture.mkdir(parents=True)
    try:
        test_matrix_passes_with_current_evidence_shape(fixture / "pass")
        test_matrix_fails_closed_for_each_summary(fixture / "summaries")
        test_matrix_rejects_feature_regressions(fixture / "features")
        test_matrix_rejects_constructed_fixture_render_guard(fixture / "constructed-render-guard")
        test_matrix_rejects_missing_constructed_fixture_release(fixture / "constructed-release")
        test_matrix_rejects_constructed_fixture_click_rearm(fixture / "constructed-rearm")
        test_matrix_rejects_constructed_fixture_native_click_attempt(fixture / "constructed-native-click")
        test_matrix_rejects_missing_visible_command_readiness(fixture / "visible-input")
        test_matrix_rejects_visible_input_overclaim_without_real_click(fixture / "visible-overclaim")
        test_matrix_rejects_visible_input_real_click_count_mismatch(fixture / "visible-click-mismatch")
        test_cli_writes_outputs_and_requires_pass(fixture / "cli")
    finally:
        shutil.rmtree(fixture, ignore_errors=True)


def main() -> int:
    run_tests()
    print("battle UI evidence matrix tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
