#!/usr/bin/env python3
"""Fixture tests for the manual DirectInput run-plan helper."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "manual_directinput_run_plan.py"
sys.path.insert(0, str(ROOT / "tools"))

import manual_directinput_checklist  # noqa: E402
import manual_directinput_proof_template  # noqa: E402
import manual_directinput_run_plan  # noqa: E402


def write_json(path: Path, data: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return path


def run_script(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def write_guarded_script(path: Path, *, pulse_lane: bool = False) -> Path:
    lines = [
        "param(",
        "    [switch]$AllowVisibleRuntime",
    ]
    if pulse_lane:
        lines += [
            "    ,[ValidateSet('legacy', 'pulse')]",
            "    [string]$InputMode = 'legacy'",
            "    ,[string]$PulseRouteSteps = ''",
            "    ,[string]$FollowupPoints = ''",
        ]
    lines += [
        ")",
        "if (-not $AllowVisibleRuntime) {",
        "    throw 'Re-run with -AllowVisibleRuntime only after explicit user approval.'",
        "}",
    ]
    if pulse_lane:
        lines.append("$pulseTool = Join-Path $RepoRoot 'tools\\menu_pulse_click.py'")
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def write_pulse_tool(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "# stub engine-aim pulse tool",
                "# supports --steps, --probe-only and --aim-points",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return path


def write_current_reports(fixture: Path) -> argparse.Namespace:
    checklist = manual_directinput_checklist.build_checklist(
        argparse.Namespace(manual_proof=None, allow_cdb_only_promotion=False)
    )
    template = manual_directinput_proof_template.build_template()
    template_report = manual_directinput_proof_template.build_report(
        fixture / "manual-directinput-proof-template.json",
        template,
    )
    return argparse.Namespace(
        checklist_json=write_json(fixture / "checklist.json", checklist),
        template_report_json=write_json(fixture / "template-report.json", template_report),
        visual_smoke_script=write_guarded_script(fixture / "run_clash_visual_smoke.ps1", pulse_lane=True),
        battle_visible_script=write_guarded_script(fixture / "scripts/cdb/run_cdb_battle_visible_input_probe.ps1"),
        checklist_script=write_guarded_script(fixture / "manual_directinput_checklist.py"),
        pulse_tool=write_pulse_tool(fixture / "tools/menu_pulse_click.py"),
        proof_json=fixture / "manual-directinput-proof-current.json",
    )


def plan_from_args(args: argparse.Namespace) -> dict:
    return manual_directinput_run_plan.build_plan(
        checklist_json=args.checklist_json,
        template_report_json=args.template_report_json,
        visual_smoke_script=args.visual_smoke_script,
        battle_visible_script=args.battle_visible_script,
        checklist_script=args.checklist_script,
        pulse_tool=args.pulse_tool,
        proof_json=args.proof_json,
    )


def build_fixture_plan(fixture: Path) -> dict:
    return plan_from_args(write_current_reports(fixture))


def test_plan_passes_but_does_not_claim_proof(fixture: Path) -> None:
    plan = build_fixture_plan(fixture)
    assert plan["passed"] is True, plan
    assert plan["proof_ready"] is False, plan
    assert plan["visible_runtime_requires_approval"] is True, plan
    assert "does not run PowerShell" in plan["runtime_policy"], plan
    assert plan["candidate_root"] == "C:\\ClashTests", plan
    assert "repository-local" in plan["candidate_path_policy"], plan
    assert plan["summary"]["promotion_ready"] is False, plan
    assert plan["summary"]["all_commands_have_safe_window_origin"] is True, plan
    assert plan["summary"]["all_commands_use_pulse_input_mode"] is True, plan
    assert plan["input_mode"] == "pulse", plan
    assert plan["engine_input_mechanism"] == "pulse-relative-engine-aim", plan
    assert "DirectInput accumulator" in plan["engine_input_policy"], plan
    assert "setcursor" in plan["di_invisible_move_modes"], plan


def test_one_approval_gated_command_per_required_id(fixture: Path) -> None:
    plan = build_fixture_plan(fixture)
    commands = plan["commands"]
    assert sorted(commands) == sorted(manual_directinput_checklist.REQUIRED_IDS), plan
    for item_id, command in commands.items():
        assert "-AllowVisibleRuntime" in command["command"], (item_id, command)
        assert "powershell.exe" in command["command"], (item_id, command)
        assert command["candidate_placeholder"].startswith("C:\\ClashTests\\"), (item_id, command)
        assert "-Exe 'C:\\ClashTests\\" in command["command"], (item_id, command)
        assert "-MoveWindowX 0 -MoveWindowY -30" in command["command"], (item_id, command)
        assert command["move_window_origin"] == [0, -30], (item_id, command)
        assert "repository-local" in command["candidate_path_policy"], (item_id, command)
        assert command["requires_explicit_user_approval"] is True, (item_id, command)
        assert command["stage"], (item_id, command)


def test_every_command_drives_the_engine_cursor(fixture: Path) -> None:
    plan = build_fixture_plan(fixture)
    for item_id, command in plan["commands"].items():
        text = command["command"]
        assert "-InputMode pulse" in text, (item_id, text)
        assert "-PulseRouteSteps 'load-button:302,211;" in text, (item_id, text)
        assert command["input_mode"] == "pulse", (item_id, command)
        assert command["engine_input_mechanism"] == "pulse-relative-engine-aim", (item_id, command)
        assert command["aim_tolerance_px"] > 0, (item_id, command)
        # The DI-invisible lane must never be the only thing a command asks for.
        if command["followup_points"]:
            assert f"-FollowupPoints '{command['followup_points']}'" in text, (item_id, text)
        else:
            assert "-FollowupPoints" not in text, (item_id, text)


def test_castle_targets_carry_the_entry_click_and_the_barracks_gap(fixture: Path) -> None:
    plan = build_fixture_plan(fixture)
    for item_id in ("castle_barracks_centered_input", "castle_overview_centered_input"):
        command = plan["commands"][item_id]
        assert command["followup_points"].startswith("castle-entry:470,397"), command
    barracks = plan["commands"]["castle_barracks_centered_input"]
    assert "OPEN COORDINATE GAP" in barracks["notes"], barracks
    assert "371,107" in barracks["notes"], barracks
    assert any("barracks-entry coordinate is known" in item for item in plan["runtime_prerequisites"]), plan


def test_harness_without_pulse_lane_fails_closed(fixture: Path) -> None:
    args = write_current_reports(fixture)
    # A harness that only offers the DirectInput-invisible OS-cursor modes must
    # not be handed a plan that claims engine-visible clicks.
    write_guarded_script(args.visual_smoke_script, pulse_lane=False)
    plan = plan_from_args(args)
    assert plan["passed"] is False, plan
    assert any("pulse input lane" in failure for failure in plan["failures"]), plan


def test_missing_pulse_tool_fails_closed(fixture: Path) -> None:
    args = write_current_reports(fixture)
    args.pulse_tool.unlink()
    plan = plan_from_args(args)
    assert plan["passed"] is False, plan
    assert any("engine-aim pulse tool" in failure for failure in plan["failures"]), plan


def test_pulse_tool_without_aim_points_fails_closed(fixture: Path) -> None:
    args = write_current_reports(fixture)
    args.pulse_tool.write_text("# only --probe-only here\n", encoding="utf-8")
    plan = plan_from_args(args)
    assert plan["passed"] is False, plan
    assert any("--aim-points" in failure for failure in plan["failures"]), plan


def test_legacy_input_mode_fails_closed(fixture: Path) -> None:
    args = write_current_reports(fixture)
    original = manual_directinput_run_plan.INPUT_MODE
    try:
        manual_directinput_run_plan.INPUT_MODE = "legacy"
        plan = plan_from_args(args)
    finally:
        manual_directinput_run_plan.INPUT_MODE = original
    assert plan["passed"] is False, plan
    assert any("engine-visible pulse input mode" in failure for failure in plan["failures"]), plan


def test_missing_checklist_item_fails_closed(fixture: Path) -> None:
    args = write_current_reports(fixture)
    checklist = json.loads(args.checklist_json.read_text(encoding="utf-8"))
    checklist["summary"]["pending_ids"].remove("right_bottom_validation_input")
    args.checklist_json.write_text(json.dumps(checklist, indent=2) + "\n", encoding="utf-8")
    plan = plan_from_args(args)
    assert plan["passed"] is False, plan
    assert any("right_bottom_validation_input" in failure for failure in plan["failures"]), plan


def test_missing_allow_visible_runtime_fails_closed(fixture: Path) -> None:
    args = write_current_reports(fixture)
    args.visual_smoke_script.parent.mkdir(parents=True, exist_ok=True)
    args.visual_smoke_script.write_text("param()\n", encoding="utf-8")
    plan = plan_from_args(args)
    assert plan["passed"] is False, plan
    assert any("AllowVisibleRuntime" in failure for failure in plan["failures"]), plan


def test_non_isolated_candidate_placeholder_fails_closed(fixture: Path) -> None:
    args = write_current_reports(fixture)
    original = manual_directinput_run_plan.COMMAND_SPECS["stable_menu_load"]["candidate"]
    try:
        manual_directinput_run_plan.COMMAND_SPECS["stable_menu_load"]["candidate"] = (
            "clash95_hd_manual.exe"
        )
        plan = plan_from_args(args)
    finally:
        manual_directinput_run_plan.COMMAND_SPECS["stable_menu_load"]["candidate"] = original
    assert plan["passed"] is False, plan
    assert any("not under C:\\ClashTests" in failure for failure in plan["failures"]), plan


def test_nonzero_window_origin_fails_closed(fixture: Path) -> None:
    args = write_current_reports(fixture)
    original = manual_directinput_run_plan.SAFE_MOVE_WINDOW_ORIGIN
    try:
        manual_directinput_run_plan.SAFE_MOVE_WINDOW_ORIGIN = (80, 80)
        plan = plan_from_args(args)
    finally:
        manual_directinput_run_plan.SAFE_MOVE_WINDOW_ORIGIN = original
    assert plan["passed"] is False, plan
    assert any("safe (0,-30) window offset" in failure for failure in plan["failures"]), plan


def test_cli_writes_outputs(fixture: Path) -> None:
    args = write_current_reports(fixture)
    out_json = fixture / "out" / "run-plan.json"
    out_md = fixture / "out" / "run-plan.md"
    run = run_script(
        "--checklist-json",
        str(args.checklist_json),
        "--template-report-json",
        str(args.template_report_json),
        "--visual-smoke-script",
        str(args.visual_smoke_script),
        "--battle-visible-script",
        str(args.battle_visible_script),
        "--checklist-script",
        str(args.checklist_script),
        "--pulse-tool",
        str(args.pulse_tool),
        "--proof-json",
        str(args.proof_json),
        "--write-json",
        str(out_json),
        "--write-markdown",
        str(out_md),
        "--require-pass",
    )
    assert run.returncode == 0, run.stdout + run.stderr
    payload = json.loads(out_json.read_text(encoding="utf-8"))
    assert payload["passed"] is True, payload
    assert payload["summary"]["all_commands_have_allow_visible_runtime"] is True, payload
    assert payload["summary"]["all_commands_have_safe_window_origin"] is True, payload
    assert payload["summary"]["all_commands_use_pulse_input_mode"] is True, payload
    assert payload["summary"]["followup_point_targets"] == [
        "stable_hd_map_input",
        "right_bottom_validation_input",
        "castle_barracks_centered_input",
        "castle_overview_centered_input",
    ], payload
    markdown = out_md.read_text(encoding="utf-8")
    assert "-AllowVisibleRuntime" in markdown
    assert "-MoveWindowX 0 -MoveWindowY -30" in markdown
    assert "-InputMode pulse" in markdown
    assert "Pulse engine-aim route steps" in markdown
    assert "C:\\ClashTests" in markdown


def run_tests() -> None:
    fixture = ROOT / ".codex-loop" / "tmp-tests" / "manual-directinput-run-plan-fixture"
    shutil.rmtree(fixture, ignore_errors=True)
    fixture.mkdir(parents=True)
    try:
        test_plan_passes_but_does_not_claim_proof(fixture / "default")
        test_one_approval_gated_command_per_required_id(fixture / "commands")
        test_every_command_drives_the_engine_cursor(fixture / "engine-cursor")
        test_castle_targets_carry_the_entry_click_and_the_barracks_gap(fixture / "castle-gap")
        test_harness_without_pulse_lane_fails_closed(fixture / "no-pulse-lane")
        test_missing_pulse_tool_fails_closed(fixture / "no-pulse-tool")
        test_pulse_tool_without_aim_points_fails_closed(fixture / "no-aim-points")
        test_legacy_input_mode_fails_closed(fixture / "legacy-input-mode")
        test_missing_checklist_item_fails_closed(fixture / "missing-item")
        test_missing_allow_visible_runtime_fails_closed(fixture / "missing-guard")
        test_non_isolated_candidate_placeholder_fails_closed(fixture / "candidate-root")
        test_nonzero_window_origin_fails_closed(fixture / "unsafe-window-origin")
        test_cli_writes_outputs(fixture / "cli")
    finally:
        shutil.rmtree(fixture, ignore_errors=True)


def main() -> int:
    run_tests()
    print("manual DirectInput run plan tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
