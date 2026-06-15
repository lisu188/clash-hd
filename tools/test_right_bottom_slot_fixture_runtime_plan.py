#!/usr/bin/env python3
"""Tests for right_bottom_slot_fixture_runtime_plan.py."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import right_bottom_slot_fixture_runtime_plan as plan


def write_json(path: Path, payload: dict[str, object]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def fixture_report(
    *,
    passed: bool = True,
    proof_class: str = "non_natural_isolated_fixture",
    promotion_ready: bool = False,
    stable_stage_should_change: bool = False,
    target_load_slot: int = 0,
) -> dict[str, object]:
    return {
        "passed": passed,
        "plan": {
            "proof_class": proof_class,
            "promotion_ready": promotion_ready,
            "stable_stage_should_change": stable_stage_should_change,
            "fixture_root": r"C:\ClashTests\right-bottom-slot5-as-slot0-fixture",
            "fixture_save": r"C:\ClashTests\right-bottom-slot5-as-slot0-fixture\save\0.dat",
            "target_load_slot": target_load_slot,
        },
    }


def script_guard(*, passed: bool = True) -> dict[str, object]:
    return {
        "passed": passed,
        "script": "scripts/smoke/prepare_right_bottom_slot_fixture.ps1",
        "markers": {
            "seed_workdir_switch": True,
            "seed_excludes_save_dir": True,
            "seed_workdir_copy": True,
        },
        "dry_run_exit_line": 102,
        "seed_copy_line": 113,
        "copy_line": 114,
        "risky_visible_lines": [],
    }


def write_inputs(root: Path, *, fixture: dict[str, object] | None = None, guard: dict[str, object] | None = None) -> dict[str, Path]:
    fixture_json = write_json(root / "fixture.json", fixture or fixture_report())
    guard_json = write_json(root / "guard.json", guard or script_guard())
    surface = root / "scripts/cdb/run_cdb_surface_dump.ps1"
    surface.parent.mkdir(parents=True, exist_ok=True)
    surface.write_text("# surface dump\n", encoding="utf-8")
    extra = root / "extra.cdb"
    extra.write_text(".echo probe\n", encoding="utf-8")
    parser = root / "result_summary.py"
    parser.write_text("# result parser\n", encoding="utf-8")
    return {"fixture": fixture_json, "guard": guard_json, "surface": surface, "extra": extra, "parser": parser}


def build(paths: dict[str, Path], repo_root: Path) -> dict[str, object]:
    return plan.build_plan(
        fixture_plan_json=paths["fixture"],
        script_guard_json=paths["guard"],
        surface_dump_script=paths["surface"],
        extra_probe=paths["extra"],
        result_parser=paths["parser"],
        repo_root=repo_root,
    )


def test_passes_and_builds_hidden_fixture_command() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        report = build(write_inputs(root), root)
    assert report["passed"], report
    assert "-SeedWorkDir" in report["commands"]["prepare_dry_run"]
    assert "-SeedWorkDir" in report["commands"]["prepare_execute"]
    command = report["commands"]["hidden_fixture_probe"]
    assert "-WorkDir 'C:\\ClashTests\\right-bottom-slot5-as-slot0-fixture'" in command
    assert "-CandidateDir 'C:\\ClashTests\\right-bottom-slot5-as-slot0-fixture\\candidate'" in command
    assert "-LoadSlot 0" in command
    assert "-UseDdrawProxy" in command
    assert "-FastForwardStartAnims" in command
    assert "-SkipMapValidation" in command
    assert "-ExtraProbeTemplate" in command
    summary_command = report["commands"]["summarize_fixture_result"]
    assert "right-bottom-slot-fixture-result-summary" in summary_command
    assert "--expected-slot 0" in summary_command
    assert "--require-load-success" in summary_command
    assert "--require-slot-match" in summary_command
    assert "--require-owner-bit2" in summary_command
    assert "--require-owner-action" in summary_command
    assert report["summary"]["promotion_ready"] is False
    assert report["summary"]["stable_stage_should_change"] is False
    assert report["summary"]["prepare_seed_workdir"] is True
    assert report["summary"]["result_log_template"].endswith("cdb-surface-dump.log")


def test_requires_strict_fixture_slot_acceptance() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        report = build(write_inputs(root), root)
    assert report["passed"], report
    prerequisites = "\n".join(report["runtime_prerequisites"])
    markers = "\n".join(report["expected_success_markers"])
    assert "selected_arg and selected_global consistent with expected slot 0" in prerequisites
    assert "SURFDUMP_LOADSAVE selected_arg=0 selected_global=0" in markers
    assert "SURFDUMP_LOADSAVE selected_arg=0\n" not in markers


def test_fails_when_fixture_plan_promotes() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        paths = write_inputs(root, fixture=fixture_report(promotion_ready=True))
        report = build(paths, root)
    assert not report["passed"]
    assert any("promotion-ready" in failure for failure in report["failures"]), report


def test_fails_when_script_guard_fails() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        paths = write_inputs(root, guard=script_guard(passed=False))
        report = build(paths, root)
    assert not report["passed"]
    assert any("script guard is not passing" in failure for failure in report["failures"]), report


def test_fails_when_script_guard_lacks_seed_marker() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        guard = script_guard()
        guard["markers"]["seed_workdir_copy"] = False
        paths = write_inputs(root, guard=guard)
        report = build(paths, root)
    assert not report["passed"]
    assert any("seed_workdir_copy" in failure for failure in report["failures"]), report


def test_fails_when_result_parser_missing() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        paths = write_inputs(root)
        paths["parser"].unlink()
        report = build(paths, root)
    assert not report["passed"]
    assert any("result summary parser" in failure for failure in report["failures"]), report


def test_fails_when_fixture_root_inside_repo() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        fixture = fixture_report()
        fixture["plan"]["fixture_root"] = str(root / "fixture")
        fixture["plan"]["fixture_save"] = str(root / "fixture" / "save" / "0.dat")
        paths = write_inputs(root, fixture=fixture)
        report = build(paths, root)
    assert not report["passed"]
    assert any("inside the repository" in failure for failure in report["failures"]), report


def test_cli_writes_outputs_and_requires_pass() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        paths = write_inputs(root)
        out_json = root / "out.json"
        out_md = root / "out.md"
        result = subprocess.run(
            [
                sys.executable,
                str(Path(plan.__file__)),
                "--fixture-plan-json",
                str(paths["fixture"]),
                "--script-guard-json",
                str(paths["guard"]),
                "--surface-dump-script",
                str(paths["surface"]),
                "--extra-probe",
                str(paths["extra"]),
                "--result-parser",
                str(paths["parser"]),
                "--repo-root",
                str(root),
                "--write-json",
                str(out_json),
                "--write-markdown",
                str(out_md),
                "--require-pass",
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        assert out_json.exists()
        assert out_md.exists()


def run_tests() -> None:
    test_passes_and_builds_hidden_fixture_command()
    test_requires_strict_fixture_slot_acceptance()
    test_fails_when_fixture_plan_promotes()
    test_fails_when_script_guard_fails()
    test_fails_when_script_guard_lacks_seed_marker()
    test_fails_when_result_parser_missing()
    test_fails_when_fixture_root_inside_repo()
    test_cli_writes_outputs_and_requires_pass()


if __name__ == "__main__":
    run_tests()
    print("right_bottom_slot_fixture_runtime_plan tests passed")
