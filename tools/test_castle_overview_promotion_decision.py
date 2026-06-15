#!/usr/bin/env python3
"""Fixture tests for the castle overview promotion decision helper."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "castle_overview_promotion_decision.py"
sys.path.insert(0, str(ROOT / "tools"))

import castle_overview_promotion_decision  # noqa: E402
import manual_directinput_checklist  # noqa: E402


STABLE_STAGE = castle_overview_promotion_decision.DEFAULT_STABLE_STAGE
VALIDATION_STAGE = STABLE_STAGE + "-castlecenter-all"
CANDIDATE_SHA = "d" * 64


def write_valid_manual_proof(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "evidence_class": "manual_directinput",
                "approved_visible_runtime": True,
                "approval_record": "User explicitly approved visible manual DirectInput validation.",
                "candidate_path": "C:\\ClashTests\\manual-proof\\clash95_hd_manual.exe",
                "executable_sha256": "b" * 64,
                "no_stale_processes": True,
                "checked_items": [
                    {
                        "id": item["id"],
                        "stage": item["stage"],
                        "status": "passed",
                        "observed_result": f"{item['id']} manual route passed.",
                        "evidence": f"manual screenshot or notes for {item['id']}",
                        "pass_fail_notes": f"{item['id']} passed with no crash.",
                        "no_crash": True,
                    }
                    for item in manual_directinput_checklist.CHECKLIST_ITEMS
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def write_valid_override_manifest(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "manifest_type": "promotion_override",
                "explicit_user_approval": True,
                "approval_record": "User explicitly approved this castle overview CDB-only promotion override.",
                "target_scope": "castle_overview",
                "candidate_stage": VALIDATION_STAGE,
                "candidate_sha256": CANDIDATE_SHA,
                "accepted_risk": "CDB/proxy-only evidence bypasses live manual DirectInput proof.",
                "evidence_refs": [
                    "captures/current/castle-overview-promotion-decision-current.json",
                    "captures/current/process-hygiene-guard-current.json",
                ],
                "no_stale_process_result": {
                    "passed": True,
                    "matching_process_count": 0,
                    "source": "captures/current/process-hygiene-guard-current.json",
                },
                "manual_directinput_bypass_reason": (
                    "Manual DirectInput proof is bypassed for this castle overview scope because "
                    "the user explicitly approved CDB/proxy-only promotion."
                ),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def run_script(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def target(index: int, raw: int, command: int, *, completion_ok: bool = True) -> dict:
    return {
        "index": index,
        "raw": raw,
        "command": command,
        "callback": 0x00400000 + index,
        "raw_ok": True,
        "descriptor_ok": True,
        "gate_ok": True,
        "completion_ok": completion_ok,
        "ok": completion_ok,
    }


def matrix_payload(
    *,
    passed: bool = True,
    displayed_wrapper_ok: bool = True,
    visible_completion_ok: bool = True,
    dormant_completion_ok: bool = True,
) -> dict:
    return {
        "passed": passed,
        "stage": "castlecenter-all",
        "promotion_status": "validation_stage_only" if passed else "regressed",
        "runtime_policy": "repo-only fixture",
        "checks": {
            "patch_stage": {
                "resolved_stage": VALIDATION_STAGE,
                "sha256": CANDIDATE_SHA,
            },
            "focused_hitbox": {
                "passed": displayed_wrapper_ok,
                "displayed_wrapper_ok": displayed_wrapper_ok,
                "av_count": 0,
            },
            "visible_multihit": {
                "passed": visible_completion_ok,
                "av_count": 0,
                "targets": [
                    target(0, 0xF8, 0x86, completion_ok=visible_completion_ok),
                    target(1, 0xFE, 0x63, completion_ok=visible_completion_ok),
                ],
            },
            "dormant_multihit": {
                "passed": dormant_completion_ok,
                "av_count": 0,
                "targets": [
                    target(0, 0xFA, 0x99, completion_ok=dormant_completion_ok),
                    target(1, 0xFB, 0x9C, completion_ok=dormant_completion_ok),
                ],
            },
        },
        "failures": [] if passed else ["intentional matrix fixture failure"],
    }


def write_matrix(
    path: Path,
    *,
    passed: bool = True,
    displayed_wrapper_ok: bool = True,
    visible_completion_ok: bool = True,
    dormant_completion_ok: bool = True,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            matrix_payload(
                passed=passed,
                displayed_wrapper_ok=displayed_wrapper_ok,
                visible_completion_ok=visible_completion_ok,
                dormant_completion_ok=dormant_completion_ok,
            ),
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def args_for(
    matrix: Path,
    *,
    manual_input_proof: Path | None = None,
    allow_cdb_only_promotion: bool = False,
    promotion_override_manifest: Path | None = None,
) -> argparse.Namespace:
    return argparse.Namespace(
        matrix=matrix,
        current_stable_stage=STABLE_STAGE,
        manual_input_proof=manual_input_proof,
        allow_cdb_only_promotion=allow_cdb_only_promotion,
        promotion_override_manifest=promotion_override_manifest,
    )


def test_deferred_by_default(fixture: Path) -> None:
    matrix = write_matrix(fixture / "matrix.json")
    decision = castle_overview_promotion_decision.build_decision(args_for(matrix))
    assert decision["passed"] is True, decision
    assert decision["decision"] == "defer_stable_promotion", decision
    assert decision["stable_stage_should_change"] is False, decision
    assert decision["manual_input_proof"] is None, decision
    assert decision["allow_cdb_only_promotion"] is False, decision
    assert decision["proof"]["focused_displayed_wrapper_ok"] is True, decision
    assert decision["proof"]["visible_multihit_completion_ok"] is True, decision
    assert decision["proof"]["dormant_multihit_completion_ok"] is True, decision


def test_failing_matrix_fails(fixture: Path) -> None:
    matrix = write_matrix(fixture / "matrix.json", passed=False)
    decision = castle_overview_promotion_decision.build_decision(args_for(matrix))
    assert decision["passed"] is False, decision
    assert decision["decision"] == "defer_stable_promotion", decision
    assert decision["stable_stage_should_change"] is False, decision
    assert any("matrix is not passing" in failure for failure in decision["failures"]), decision


def test_missing_matrix_proof_fails(fixture: Path) -> None:
    matrix = write_matrix(
        fixture / "matrix.json",
        displayed_wrapper_ok=False,
        visible_completion_ok=False,
        dormant_completion_ok=False,
    )
    proof = write_valid_manual_proof(fixture / "manual-proof.json")
    decision = castle_overview_promotion_decision.build_decision(
        args_for(matrix, manual_input_proof=proof, allow_cdb_only_promotion=True)
    )
    assert decision["passed"] is False, decision
    assert decision["decision"] == "defer_stable_promotion", decision
    assert decision["stable_stage_should_change"] is False, decision
    assert any("displayed-wrapper proof is missing" in failure for failure in decision["failures"]), decision
    assert any("visible-command multi-hit target-done" in failure for failure in decision["failures"]), decision
    assert any("dormant-command multi-hit target-done" in failure for failure in decision["failures"]), decision


def test_valid_manual_input_proof_allows_stable_promotion(fixture: Path) -> None:
    matrix = write_matrix(fixture / "matrix.json")
    proof = write_valid_manual_proof(fixture / "manual-proof.json")
    decision = castle_overview_promotion_decision.build_decision(
        args_for(matrix, manual_input_proof=proof)
    )
    assert decision["passed"] is True, decision
    assert decision["decision"] == "eligible_for_stable_promotion", decision
    assert decision["stable_stage_should_change"] is True, decision
    assert decision["manual_input_proof"] == str(proof), decision
    assert decision["manual_input_proof_valid"] is True, decision


def test_placeholder_manual_input_proof_fails_closed(fixture: Path) -> None:
    matrix = write_matrix(fixture / "matrix.json")
    proof = fixture / "manual-proof.md"
    proof.parent.mkdir(parents=True, exist_ok=True)
    proof.write_text("# proof placeholder\n", encoding="utf-8")
    decision = castle_overview_promotion_decision.build_decision(
        args_for(matrix, manual_input_proof=proof)
    )
    assert decision["passed"] is False, decision
    assert decision["decision"] == "defer_stable_promotion", decision
    assert decision["stable_stage_should_change"] is False, decision
    assert decision["manual_input_proof_supplied"] is True, decision
    assert decision["manual_input_proof_valid"] is False, decision
    assert any("not valid JSON" in failure for failure in decision["failures"]), decision


def test_bare_cdb_only_override_is_blocked(fixture: Path) -> None:
    matrix = write_matrix(fixture / "matrix.json")
    decision = castle_overview_promotion_decision.build_decision(
        args_for(matrix, allow_cdb_only_promotion=True)
    )
    assert decision["passed"] is False, decision
    assert decision["decision"] == "defer_stable_promotion", decision
    assert decision["stable_stage_should_change"] is False, decision
    assert decision["allow_cdb_only_promotion"] is True, decision
    assert decision["bare_cdb_only_promotion_blocked"] is True, decision
    assert any("bare --allow-cdb-only-promotion" in failure for failure in decision["failures"]), decision


def test_manifest_backed_override_allows_promotion(fixture: Path) -> None:
    matrix = write_matrix(fixture / "matrix.json")
    manifest = write_valid_override_manifest(fixture / "override.json")
    decision = castle_overview_promotion_decision.build_decision(
        args_for(matrix, promotion_override_manifest=manifest)
    )
    assert decision["passed"] is True, decision
    assert decision["decision"] == "eligible_for_override_manifest_promotion", decision
    assert decision["stable_stage_should_change"] is True, decision
    assert decision["promotion_override_manifest"] == str(manifest), decision
    assert decision["promotion_override_manifest_valid"] is True, decision


def test_cli_writes_outputs_and_fails_closed(fixture: Path) -> None:
    good_matrix = write_matrix(fixture / "good" / "matrix.json")
    out_json = fixture / "good-output" / "decision.json"
    out_md = fixture / "good-output" / "decision.md"
    good_run = run_script(
        "--matrix",
        str(good_matrix),
        "--current-stable-stage",
        STABLE_STAGE,
        "--write-json",
        str(out_json),
        "--write-markdown",
        str(out_md),
        "--require-pass",
    )
    assert good_run.returncode == 0, good_run.stdout + good_run.stderr
    assert json.loads(out_json.read_text(encoding="utf-8"))["passed"] is True
    assert "- Decision record: PASS" in out_md.read_text(encoding="utf-8")

    bad_matrix = write_matrix(fixture / "bad" / "matrix.json", passed=False)
    bad_json = fixture / "bad-output" / "decision.json"
    bad_md = fixture / "bad-output" / "decision.md"
    bad_run = run_script(
        "--matrix",
        str(bad_matrix),
        "--current-stable-stage",
        STABLE_STAGE,
        "--write-json",
        str(bad_json),
        "--write-markdown",
        str(bad_md),
        "--require-pass",
    )
    assert bad_run.returncode == 2, bad_run.stdout + bad_run.stderr
    assert json.loads(bad_json.read_text(encoding="utf-8"))["passed"] is False
    assert "- Decision record: FAIL" in bad_md.read_text(encoding="utf-8")

    placeholder_proof = fixture / "placeholder-proof.md"
    placeholder_proof.write_text("# not a manifest\n", encoding="utf-8")
    invalid_proof_run = run_script(
        "--matrix",
        str(good_matrix),
        "--current-stable-stage",
        STABLE_STAGE,
        "--manual-input-proof",
        str(placeholder_proof),
        "--write-json",
        str(fixture / "invalid-proof-output" / "decision.json"),
        "--write-markdown",
        str(fixture / "invalid-proof-output" / "decision.md"),
        "--require-pass",
    )
    assert invalid_proof_run.returncode == 2, invalid_proof_run.stdout + invalid_proof_run.stderr

    bare_override_run = run_script(
        "--matrix",
        str(good_matrix),
        "--current-stable-stage",
        STABLE_STAGE,
        "--allow-cdb-only-promotion",
        "--write-json",
        str(fixture / "bare-override-output" / "decision.json"),
        "--write-markdown",
        str(fixture / "bare-override-output" / "decision.md"),
        "--require-pass",
    )
    assert bare_override_run.returncode == 2, bare_override_run.stdout + bare_override_run.stderr
    assert json.loads((fixture / "bare-override-output" / "decision.json").read_text(encoding="utf-8"))[
        "bare_cdb_only_promotion_blocked"
    ] is True

    manifest = write_valid_override_manifest(fixture / "override.json")
    manifest_run = run_script(
        "--matrix",
        str(good_matrix),
        "--current-stable-stage",
        STABLE_STAGE,
        "--promotion-override-manifest",
        str(manifest),
        "--write-json",
        str(fixture / "manifest-output" / "decision.json"),
        "--write-markdown",
        str(fixture / "manifest-output" / "decision.md"),
        "--require-pass",
    )
    assert manifest_run.returncode == 0, manifest_run.stdout + manifest_run.stderr
    assert json.loads((fixture / "manifest-output" / "decision.json").read_text(encoding="utf-8"))[
        "promotion_override_manifest_valid"
    ] is True


def run_tests() -> None:
    fixture = ROOT / ".codex-loop" / "tmp-tests" / "castle-overview-promotion-decision-fixture"
    shutil.rmtree(fixture, ignore_errors=True)
    fixture.mkdir(parents=True)
    try:
        test_deferred_by_default(fixture / "defer")
        test_failing_matrix_fails(fixture / "failing-matrix")
        test_missing_matrix_proof_fails(fixture / "missing-proof")
        test_valid_manual_input_proof_allows_stable_promotion(fixture / "manual")
        test_placeholder_manual_input_proof_fails_closed(fixture / "placeholder-manual")
        test_bare_cdb_only_override_is_blocked(fixture / "override")
        test_manifest_backed_override_allows_promotion(fixture / "manifest")
        test_cli_writes_outputs_and_fails_closed(fixture / "cli")
    finally:
        shutil.rmtree(fixture, ignore_errors=True)


def main() -> int:
    run_tests()
    print("castle overview promotion decision tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
