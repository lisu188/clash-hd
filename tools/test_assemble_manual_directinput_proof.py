#!/usr/bin/env python3
"""Fixture tests for the manual DirectInput proof assembler.

These build synthetic run manifests (never real proof) to verify the assembler
produces a schema-valid proof from a complete run and fails closed on partial or
placeholder runs.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "assemble_manual_directinput_proof.py"
sys.path.insert(0, str(ROOT / "tools"))

import assemble_manual_directinput_proof as assembler  # noqa: E402
import manual_directinput_checklist  # noqa: E402


def run_script(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=str(ROOT),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def complete_run_manifest() -> dict:
    """A synthetic run manifest standing in for a real approved run."""
    targets = []
    for item in manual_directinput_checklist.CHECKLIST_ITEMS:
        targets.append(
            {
                "id": item["id"],
                "candidate_path": "C:\\ClashTests\\manual-directinput\\clash95_hd_candidate.exe",
                "executable_sha256": "a" * 64,
                "artifacts": [f"{item['id']}-after.png"],
                "observed_result": f"{item['id']}: real click reached the descriptor callback.",
                "evidence": f"screenshot {item['id']}-after.png plus route log",
                "pass_fail_notes": f"{item['id']} passed; centered coordinates matched.",
                "no_crash": True,
                "status": "pass",
            }
        )
    return {
        "runner": "linux-wine",
        "approved_visible_runtime": True,
        "approval_record": "User approved visible manual DirectInput validation on 2026-07-19.",
        "no_stale_processes": True,
        "candidate_path": "C:\\ClashTests\\manual-directinput\\clash95_hd_candidate.exe",
        "executable_sha256": "a" * 64,
        "targets": targets,
    }


def test_complete_run_assembles_valid_proof() -> None:
    proof = assembler.build_proof(complete_run_manifest(), None)
    failures = manual_directinput_checklist.validate_manual_proof_data(proof)
    assert failures == [], failures
    # Stages come from the checklist, not the input.
    stage_by_id = {i["id"]: i["stage"] for i in manual_directinput_checklist.CHECKLIST_ITEMS}
    for item in proof["checked_items"]:
        assert item["stage"] == stage_by_id[item["id"]], item


def test_stage_is_authoritative_even_if_input_lies() -> None:
    manifest = complete_run_manifest()
    for target in manifest["targets"]:
        target["stage"] = "totally-wrong-stage"
    proof = assembler.build_proof(manifest, None)
    failures = manual_directinput_checklist.validate_manual_proof_data(proof)
    assert failures == [], failures  # assembler overrides the bogus stage


def test_partial_run_fails_closed() -> None:
    manifest = complete_run_manifest()
    # Drop one target's observation to a placeholder.
    manifest["targets"][2]["observed_result"] = "REPLACE_WITH_MANUAL_OBSERVATION"
    manifest["targets"][2]["status"] = "pending"
    proof = assembler.build_proof(manifest, None)
    failures = manual_directinput_checklist.validate_manual_proof_data(proof)
    assert failures, "partial run must not validate"


def test_observations_merge_over_run_manifest() -> None:
    manifest = complete_run_manifest()
    # Strip observations from the run manifest; supply them separately.
    for target in manifest["targets"]:
        target.pop("observed_result", None)
        target.pop("evidence", None)
        target.pop("pass_fail_notes", None)
        target.pop("status", None)
        target.pop("no_crash", None)
    observations = {
        "targets": [
            {
                "id": item["id"],
                "observed_result": f"{item['id']} observed real click.",
                "evidence": f"notes for {item['id']}",
                "pass_fail_notes": f"{item['id']} pass",
                "no_crash": True,
                "status": "pass",
            }
            for item in manual_directinput_checklist.CHECKLIST_ITEMS
        ]
    }
    proof = assembler.build_proof(manifest, observations)
    assert manual_directinput_checklist.validate_manual_proof_data(proof) == []


def test_cli_writes_and_gates(fixture: Path) -> None:
    manifest_path = fixture / "run-manifest.json"
    manifest_path.write_text(json.dumps(complete_run_manifest()), encoding="utf-8")
    out = fixture / "proof.json"
    report = fixture / "report.json"
    run = run_script(
        "--run-manifest", str(manifest_path),
        "--output", str(out),
        "--write-report-json", str(report),
        "--require-valid",
    )
    assert run.returncode == 0, run.stdout + run.stderr
    proof = json.loads(out.read_text(encoding="utf-8"))
    assert proof["evidence_class"] == "manual_directinput"
    assert manual_directinput_checklist.validate_manual_proof_data(proof) == []
    report_data = json.loads(report.read_text(encoding="utf-8"))
    assert report_data["manual_proof_valid"] is True, report_data


def test_cli_fails_closed_on_placeholder(fixture: Path) -> None:
    manifest = complete_run_manifest()
    manifest["approval_record"] = ""  # missing approval
    manifest_path = fixture / "bad-manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    out = fixture / "bad-proof.json"
    run = run_script(
        "--run-manifest", str(manifest_path),
        "--output", str(out),
        "--require-valid",
    )
    assert run.returncode == 2, run.stdout + run.stderr
    # Working manifest is still written for inspection.
    assert out.exists()


def run_tests() -> None:
    fixture = ROOT / ".codex-loop" / "tmp-tests" / "assemble-manual-proof"
    shutil.rmtree(fixture, ignore_errors=True)
    fixture.mkdir(parents=True)
    try:
        test_complete_run_assembles_valid_proof()
        test_stage_is_authoritative_even_if_input_lies()
        test_partial_run_fails_closed()
        test_observations_merge_over_run_manifest()
        cli = fixture / "cli"
        cli.mkdir(parents=True, exist_ok=True)
        test_cli_writes_and_gates(cli)
        cli2 = fixture / "cli2"
        cli2.mkdir(parents=True, exist_ok=True)
        test_cli_fails_closed_on_placeholder(cli2)
    finally:
        shutil.rmtree(fixture, ignore_errors=True)


def main() -> int:
    run_tests()
    print("assemble manual DirectInput proof tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
