#!/usr/bin/env python3
"""Fixture tests for the Linux/wine HD validation driver (dry-run plan only)."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "run_hd_linux_validation.py"
WINE_SH = ROOT / "scripts" / "smoke" / "run_clash_hd_linux_wine.sh"
sys.path.insert(0, str(ROOT / "tools"))

import manual_directinput_checklist as checklist  # noqa: E402
import run_hd_linux_validation as driver  # noqa: E402


def run_script(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=str(ROOT),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def _plan(*args: str) -> dict:
    return driver.build_plan(driver.parse_args(list(args)))


def test_dry_run_plans_all_targets() -> None:
    plan = _plan("--dry-run")
    assert plan["runner"] == "linux-wine"
    assert plan["dry_run"] is True
    assert plan["passed"] is True, plan["failures"]
    ids = [t["id"] for t in plan["targets"]]
    assert ids == list(checklist.REQUIRED_IDS), ids
    # Stage per target matches the checklist's authoritative stage.
    stage_by_id = {i["id"]: i["stage"] for i in checklist.CHECKLIST_ITEMS}
    for target in plan["targets"]:
        assert target["stage"] == stage_by_id[target["id"]], target


def test_three_distinct_candidate_stages() -> None:
    plan = _plan("--dry-run")
    assert len(plan["candidate_stages"]) == 3, plan["candidate_stages"].keys()


def test_right_bottom_gets_fixture_command() -> None:
    plan = _plan("--dry-run")
    rb = next(t for t in plan["targets"] if t["id"] == "right_bottom_validation_input")
    assert "fixture_command" in rb
    assert "prepare_addon_flags_fixture.py" in rb["fixture_command"]
    assert rb["stage"].endswith("rightbottomcompose")


def test_observations_start_empty_and_pending() -> None:
    plan = _plan("--dry-run")
    for target in plan["targets"]:
        assert target["status"] == "pending", target
        assert target["observed_result"] == "", target
        assert target["no_crash"] is False, target


def test_execute_without_binary_or_approval_fails() -> None:
    plan = _plan("--execute")
    assert plan["passed"] is False
    joined = " ".join(plan["failures"])
    assert "--allow-visible-runtime" in joined, plan["failures"]
    assert "source-exe" in joined or "clash95.exe" in joined, plan["failures"]


def test_wrong_sha_source_rejected(fixture: Path) -> None:
    fake = fixture / "clash95.exe"
    fake.write_bytes(b"not the real game binary")
    plan = _plan("--execute", "--source-exe", str(fake), "--allow-visible-runtime",
                 "--approval-record", "approved")
    assert plan["source_present"] is True
    assert any("does not match the expected base" in f for f in plan["failures"]), plan["failures"]


def test_launch_command_references_worker() -> None:
    plan = _plan("--dry-run")
    for target in plan["targets"]:
        assert "run_clash_hd_linux_wine.sh" in target["launch_command"], target
        assert "--allow-visible-runtime" in target["launch_command"], target


def test_worker_script_has_approval_guard() -> None:
    text = WINE_SH.read_text(encoding="utf-8")
    assert "--allow-visible-runtime" in text
    assert "allow_visible_runtime" in text


class _FakeProc:
    def __init__(self, returncode: int) -> None:
        self.returncode = returncode


def test_execute_runs_patch_fixture_and_launch(fixture: Path) -> None:
    plan = _plan("--execute", "--run-dir", str(fixture / "run"))
    # execute_plan is unit-tested in isolation; main() only calls it once the
    # preflight (approval + SHA-verified binary) has passed, so clear that here.
    plan["failures"] = []
    plan["passed"] = True
    calls: list[list[str]] = []

    # Seed a captured target-summary for one target to test folding.
    rb = next(t for t in plan["targets"] if t["id"] == "right_bottom_validation_input")
    Path(rb["out_dir"]).mkdir(parents=True, exist_ok=True)
    (Path(rb["out_dir"]) / "target-summary.json").write_text(
        json.dumps({"no_crash": True, "artifacts": ["after-followup.png"]}), encoding="utf-8"
    )

    def fake_runner(argv):
        calls.append(argv)
        return _FakeProc(0)

    result = driver.execute_plan(plan, runner=fake_runner)
    kinds = [s["step"].split(":")[0] for s in result["execution_steps"]]
    assert kinds.count("patch") == 3, kinds
    assert any(s["step"] == "fixture:right_bottom_validation_input" for s in result["execution_steps"])
    assert kinds.count("launch") == 5, kinds
    assert result["executed"] is True
    assert result["passed"] is True, result["failures"]
    # Folded captured evidence.
    rb2 = next(t for t in result["targets"] if t["id"] == "right_bottom_validation_input")
    assert rb2["no_crash"] is True and rb2["artifacts"] == ["after-followup.png"]


def test_execute_failure_flips_passed(fixture: Path) -> None:
    plan = _plan("--execute", "--run-dir", str(fixture / "run2"))
    plan["failures"] = []
    plan["passed"] = True

    def failing_launch(argv):
        # Fail only the launch steps.
        return _FakeProc(1 if "run_clash_hd_linux_wine.sh" in " ".join(argv) else 0)

    result = driver.execute_plan(plan, runner=failing_launch)
    assert result["passed"] is False
    assert any("launch:" in f for f in result["failures"]), result["failures"]


def test_cli_dry_run_writes_manifest(fixture: Path) -> None:
    out = fixture / "run-manifest.json"
    run = run_script("--dry-run", "--write-json", str(out))
    assert run.returncode == 0, run.stdout + run.stderr
    manifest = json.loads(out.read_text(encoding="utf-8"))
    assert manifest["runner"] == "linux-wine"
    assert len(manifest["targets"]) == 5


def run_tests() -> None:
    fixture = ROOT / ".codex-loop" / "tmp-tests" / "run-hd-linux-validation"
    shutil.rmtree(fixture, ignore_errors=True)
    fixture.mkdir(parents=True)
    try:
        test_dry_run_plans_all_targets()
        test_three_distinct_candidate_stages()
        test_right_bottom_gets_fixture_command()
        test_observations_start_empty_and_pending()
        test_execute_without_binary_or_approval_fails()
        test_wrong_sha_source_rejected(fixture)
        test_launch_command_references_worker()
        test_worker_script_has_approval_guard()
        test_execute_runs_patch_fixture_and_launch(fixture)
        test_execute_failure_flips_passed(fixture)
        test_cli_dry_run_writes_manifest(fixture)
    finally:
        shutil.rmtree(fixture, ignore_errors=True)


def main() -> int:
    run_tests()
    print("run HD linux validation tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
