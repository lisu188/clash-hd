#!/usr/bin/env python3
"""Fixture tests for load_slot_transition_readiness_matrix.py."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "load_slot_transition_readiness_matrix.py"
sys.path.insert(0, str(ROOT / "tools"))

import load_slot_transition_readiness_matrix as matrix  # noqa: E402


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


def good_payloads() -> dict[str, dict]:
    command_prefix = (
        "powershell.exe -NoProfile -ExecutionPolicy Bypass -File "
        "'scripts/cdb/run_cdb_surface_dump.ps1' -UseDdrawProxy -FastForwardStartAnims "
        "-SkipMapValidation -Stage 'battlecenter' "
    )
    hidden_commands = {
        f"slot{slot}_hidden_transition_probe": (
            command_prefix
            + f"-CandidateDir 'C:\\ClashTests\\load-slot-transition\\slot{slot}' "
            + f"-LoadSlot {slot} -ExtraProbeTemplate "
            + "'probes/cdb/menu/clash95_load_slot_entry_transition_extra.cdb' -RunSeconds 120"
        )
        for slot in (3, 4, 5)
    }
    summaries = {
        f"slot{slot}_summarize_transition": (
            "python 'tools\\load_slot_transition_summary.py' "
            + f"'captures\\run\\slot{slot}\\cdb-surface-dump.log' "
            + f"--expected-slot {slot} --write-json 'out.json' --write-md 'out.md' "
            + "--require-entry --require-slot-match"
        )
        for slot in (3, 4, 5)
    }
    geometry_rows = [
        {
            "slot": 3,
            "mouse_x": 320,
            "mouse_y": 232,
            "raw_x_hex": "00005000",
            "raw_y_hex": "00003a00",
        },
        {
            "slot": 4,
            "mouse_x": 320,
            "mouse_y": 254,
            "raw_x_hex": "00005000",
            "raw_y_hex": "00003f80",
        },
        {
            "slot": 5,
            "mouse_x": 320,
            "mouse_y": 276,
            "raw_x_hex": "00005000",
            "raw_y_hex": "00004500",
        },
    ]
    entry_gap = {
        "passed": True,
        "promotion_ready": False,
        "gap_classification": "after_main_load_callback_before_load_menu_case_entry",
        "summary": {
            "slot2_post_entry_success": True,
            "blocked_rows": [3, 4, 5],
        },
    }
    probe_guard = {
        "passed": True,
        "summary": {
            "slot_conditions_parameterized": True,
            "extra_probe_placeholders_replaced": True,
        },
    }
    run_plan = {
        "passed": True,
        "promotion_ready": False,
        "stable_stage_should_change": False,
        "summary": {
            "target_rows": [3, 4, 5],
            "stage": "battlecenter",
            "candidate_root": "C:\\ClashTests\\load-slot-transition",
            "command_count": 3,
            "summary_command_count": 3,
        },
        "commands": {
            "hidden_transition_probes": hidden_commands,
            "summaries": summaries,
        },
        "result_acceptance": [
            "entry proof: load_slot_transition_summary.py --require-entry --require-slot-match passes for each row with consistent target_slot values",
            "success proof: if LOADSAVE/PlayGame appear, rerun the same summary with --require-success and require those slot rows to match before treating it as load success",
            "promotion remains blocked until natural owner/action proof or approved manual DirectInput proof exists",
        ],
    }
    geometry = {
        "passed": True,
        "promotion_ready": False,
        "stable_stage_should_change": False,
        "summary": {
            "target_rows": [3, 4, 5],
            "row_geometry": geometry_rows,
        },
    }
    preview = {
        "passed": True,
        "promotion_ready": False,
        "stable_stage_should_change": False,
        "summary": {
            "target_rows": [3, 4, 5],
            "preview_sha256": {"3": "a" * 64, "4": "b" * 64, "5": "c" * 64},
        },
        "previews": [{"slot": 3}, {"slot": 4}, {"slot": 5}],
    }
    summary_tests = {"passed": True}
    return {
        "entry_gap": entry_gap,
        "probe_guard": probe_guard,
        "run_plan": run_plan,
        "geometry": geometry,
        "preview": preview,
        "summary_tests": summary_tests,
    }


def write_payloads(fixture: Path, payloads: dict[str, dict] | None = None) -> dict[str, Path]:
    payloads = payloads or good_payloads()
    return {
        "entry_gap": write_json(fixture / "entry-gap.json", payloads["entry_gap"]),
        "probe_guard": write_json(fixture / "probe-guard.json", payloads["probe_guard"]),
        "run_plan": write_json(fixture / "run-plan.json", payloads["run_plan"]),
        "geometry": write_json(fixture / "geometry.json", payloads["geometry"]),
        "preview": write_json(fixture / "preview.json", payloads["preview"]),
        "summary_tests": write_json(fixture / "summary-tests.json", payloads["summary_tests"]),
    }


def build_from_paths(paths: dict[str, Path]) -> dict:
    return matrix.build_matrix(
        entry_gap_json=paths["entry_gap"],
        probe_guard_json=paths["probe_guard"],
        run_plan_json=paths["run_plan"],
        geometry_guard_json=paths["geometry"],
        probe_preview_json=paths["preview"],
        summary_tests_json=paths["summary_tests"],
    )


def test_good_readiness_shape_passes(fixture: Path) -> None:
    report = build_from_paths(write_payloads(fixture))
    assert report["passed"] is True, report
    assert report["classification"] == "ready_for_hidden_transition_probe", report
    assert report["promotion_ready"] is False, report
    assert report["checks"]["run_plan_hidden_commands"] is True, report


def test_visible_command_fails(fixture: Path) -> None:
    payloads = good_payloads()
    payloads["run_plan"]["commands"]["hidden_transition_probes"]["slot5_hidden_transition_probe"] += (
        " -AllowVisibleDesktop"
    )
    report = build_from_paths(write_payloads(fixture, payloads))
    assert report["passed"] is False, report
    assert any("run_plan_hidden_commands" in failure for failure in report["failures"]), report


def test_summary_command_without_entry_requirement_fails(fixture: Path) -> None:
    payloads = good_payloads()
    payloads["run_plan"]["commands"]["summaries"]["slot4_summarize_transition"] = (
        payloads["run_plan"]["commands"]["summaries"]["slot4_summarize_transition"].replace(
            " --require-entry",
            "",
        )
    )
    report = build_from_paths(write_payloads(fixture, payloads))
    assert report["passed"] is False, report
    assert any("summary_commands_strict" in failure for failure in report["failures"]), report


def test_result_acceptance_without_slot_consistency_fails(fixture: Path) -> None:
    payloads = good_payloads()
    payloads["run_plan"]["result_acceptance"] = [
        "entry proof: load_slot_transition_summary.py --require-entry --require-slot-match passes for each row",
        "success proof: rerun with --require-success",
        "promotion remains blocked until natural owner/action proof or approved manual DirectInput proof exists",
    ]
    report = build_from_paths(write_payloads(fixture, payloads))
    assert report["passed"] is False, report
    assert any("result_acceptance_non_promoting" in failure for failure in report["failures"]), report


def test_preview_target_drift_fails(fixture: Path) -> None:
    payloads = good_payloads()
    payloads["preview"]["previews"] = [{"slot": 3}, {"slot": 4}, {"slot": 6}]
    report = build_from_paths(write_payloads(fixture, payloads))
    assert report["passed"] is False, report
    assert any("probe_preview_rows_match_targets" in failure for failure in report["failures"]), report


def test_promoting_readiness_fails(fixture: Path) -> None:
    payloads = good_payloads()
    payloads["run_plan"]["promotion_ready"] = True
    report = build_from_paths(write_payloads(fixture, payloads))
    assert report["passed"] is False, report
    assert any("non_promoting" in failure for failure in report["failures"]), report


def test_cli_writes_outputs(fixture: Path) -> None:
    paths = write_payloads(fixture)
    out_json = fixture / "out" / "readiness.json"
    out_md = fixture / "out" / "readiness.md"
    run = run_script(
        "--entry-gap-json",
        str(paths["entry_gap"]),
        "--probe-guard-json",
        str(paths["probe_guard"]),
        "--run-plan-json",
        str(paths["run_plan"]),
        "--geometry-guard-json",
        str(paths["geometry"]),
        "--probe-preview-json",
        str(paths["preview"]),
        "--summary-tests-json",
        str(paths["summary_tests"]),
        "--write-json",
        str(out_json),
        "--write-markdown",
        str(out_md),
        "--require-pass",
    )
    assert run.returncode == 0, run.stdout + run.stderr
    assert json.loads(out_json.read_text(encoding="utf-8"))["passed"] is True
    assert "Load Slot Transition Readiness Matrix" in out_md.read_text(encoding="utf-8")


def run_tests() -> None:
    fixture = ROOT / ".codex-loop" / "tmp-tests" / "load-slot-transition-readiness-fixture"
    shutil.rmtree(fixture, ignore_errors=True)
    fixture.mkdir(parents=True)
    try:
        test_good_readiness_shape_passes(fixture / "good")
        test_visible_command_fails(fixture / "visible-command")
        test_summary_command_without_entry_requirement_fails(fixture / "loose-summary")
        test_result_acceptance_without_slot_consistency_fails(fixture / "loose-acceptance")
        test_preview_target_drift_fails(fixture / "preview-drift")
        test_promoting_readiness_fails(fixture / "promoting")
        test_cli_writes_outputs(fixture / "cli")
    finally:
        shutil.rmtree(fixture, ignore_errors=True)


def main() -> int:
    run_tests()
    print("load-slot transition readiness matrix tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
