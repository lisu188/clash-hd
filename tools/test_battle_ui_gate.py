#!/usr/bin/env python3
"""Fixture tests for the battle UI evidence gate."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "battle_ui_gate.py"
sys.path.insert(0, str(ROOT / "tools"))

import battle_ui_gate  # noqa: E402
import test_battle_ui_summary  # noqa: E402


def run_script(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def write_patch_stage(path: Path, **overrides) -> Path:
    payload = {
        "exe": r"C:\ClashTests\battlecenter\clash95_hd_battle.exe",
        "stage": battle_ui_gate.EXPECTED_STAGE,
        "exe_sha256": "B" * 64,
        "expected_base_sha256": battle_ui_gate.EXPECTED_BASE_SHA256,
        "status_counts": {"patched": 134, "original": 0, "unexpected": 0},
    }
    payload.update(overrides)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def write_stable_smoke(path: Path, **overrides) -> Path:
    payload = {"passed": True, "candidate_sha256": "A" * 64}
    payload.update(overrides)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def good_gate(fixture: Path) -> dict:
    capture = test_battle_ui_summary.write_capture(fixture / "capture", test_battle_ui_summary.good_log_text())
    patch_stage = write_patch_stage(fixture / "patch-stage.json")
    stable = write_stable_smoke(fixture / "stable-smoke.json")
    args = type(
        "Args",
        (),
        {
            "capture_or_log": capture,
            "patch_stage_json": patch_stage,
            "stable_smoke_json": stable,
            "stage": battle_ui_gate.EXPECTED_STAGE,
            "require_centered": True,
        },
    )()
    return battle_ui_gate.build_gate(args)


def test_good_gate_passes(fixture: Path) -> None:
    gate = good_gate(fixture)
    assert gate["passed"] is True, gate
    assert gate["original_count"] == 0, gate
    assert gate["unexpected_count"] == 0, gate
    assert gate["battle_summary"]["visual_mode"] == "centered-native-640x480", gate
    assert gate["stable_smoke_passed"] is True, gate


def test_gate_fails_closed_for_missing_evidence(fixture: Path) -> None:
    capture = test_battle_ui_summary.write_capture(
        fixture / "capture",
        "BATTLE_READY source=fixture surface=0a2fedd0 width=800 height=600",
        summary={
            "Candidate": r"C:\Temp\bad.exe",
            "CandidateSha256": "A" * 64,
            "LaunchMode": "hidden-desktop-cdb",
            "HiddenDesktop": True,
            "AllowVisibleDesktop": False,
        },
    )
    patch_stage = write_patch_stage(
        fixture / "patch-stage.json",
        exe=r"C:\Temp\bad.exe",
        status_counts={"patched": 132, "original": 1, "unexpected": 1},
    )
    stable = write_stable_smoke(fixture / "stable-smoke.json", passed=False)
    args = type(
        "Args",
        (),
        {
            "capture_or_log": capture,
            "patch_stage_json": patch_stage,
            "stable_smoke_json": stable,
            "stage": battle_ui_gate.EXPECTED_STAGE,
            "require_centered": True,
        },
    )()
    gate = battle_ui_gate.build_gate(args)
    assert gate["passed"] is False, gate
    joined = "\n".join(gate["failures"])
    assert "candidate is not under C:\\ClashTests" in joined, gate
    assert "original bytes" in joined, gate
    assert "unexpected bytes" in joined, gate
    assert "centered-native visual mode required" in joined, gate
    assert "battle command descriptor was not found" in joined, gate
    assert "stable HD-map regression evidence did not pass" in joined, gate


def test_cli_writes_outputs_and_requires_pass(fixture: Path) -> None:
    capture = test_battle_ui_summary.write_capture(fixture / "capture", test_battle_ui_summary.good_log_text())
    patch_stage = write_patch_stage(fixture / "patch-stage.json")
    stable = write_stable_smoke(fixture / "stable-smoke.json")
    out_json = fixture / "battle-gate.json"
    out_md = fixture / "battle-gate.md"
    passing = run_script(
        str(capture),
        "--patch-stage-json",
        str(patch_stage),
        "--stable-smoke-json",
        str(stable),
        "--require-centered",
        "--write-json",
        str(out_json),
        "--write-md",
        str(out_md),
        "--require-pass",
    )
    assert passing.returncode == 0, passing.stdout + passing.stderr
    assert json.loads(out_json.read_text(encoding="utf-8"))["passed"] is True
    assert "- Overall: PASS" in out_md.read_text(encoding="utf-8")

    failing = run_script(str(fixture / "missing"), "--require-pass")
    assert failing.returncode == 2, failing.stdout + failing.stderr


def run_tests() -> None:
    fixture = ROOT / ".codex-loop" / "tmp-tests" / "battle-ui-gate-fixture"
    shutil.rmtree(fixture, ignore_errors=True)
    fixture.mkdir(parents=True)
    try:
        test_good_gate_passes(fixture / "pass")
        test_gate_fails_closed_for_missing_evidence(fixture / "fail")
        test_cli_writes_outputs_and_requires_pass(fixture / "cli")
    finally:
        shutil.rmtree(fixture, ignore_errors=True)


def main() -> int:
    run_tests()
    print("battle UI gate tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
