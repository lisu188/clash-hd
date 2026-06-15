#!/usr/bin/env python3
"""Fixture tests for the stable-stage validation-boundary guard."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "stable_stage_guard.py"
sys.path.insert(0, str(ROOT / "tools"))

import stable_stage_guard  # noqa: E402


STABLE_STAGE = stable_stage_guard.patch_clash95_hd.DEFAULT_STAGE
CASTLE_PROOF = {
    "focused_displayed_wrapper_ok": True,
    "visible_multihit_completion_ok": True,
    "dormant_multihit_completion_ok": True,
}
CASTLE_MATRIX_CHECKS = {
    "focused_hitbox": {
        "displayed_wrapper_ok": True,
    },
    "visible_multihit": {
        "targets": [
            {"completion_ok": True},
            {"completion_ok": True},
        ],
    },
    "dormant_multihit": {
        "targets": [
            {"completion_ok": True},
            {"completion_ok": True},
        ],
    },
}


def run_script(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def decision_payload(
    *,
    validation_stage: str,
    passed: bool = True,
    decision: str = "defer_stable_promotion",
    stable_stage_should_change: bool = False,
    current_stable_stage: str = STABLE_STAGE,
    proof: dict | None = None,
) -> dict:
    payload = {
        "passed": passed,
        "decision": decision,
        "stable_stage_should_change": stable_stage_should_change,
        "current_stable_stage": current_stable_stage,
        "validation_stage": validation_stage,
        "candidate_sha256": "fixture",
        "failures": [] if passed else ["intentional fixture failure"],
    }
    if proof is not None:
        payload["proof"] = proof
    return payload


def matrix_payload(
    *,
    validation_stage: str,
    passed: bool = True,
    promotion_status: str = "validation_stage_only",
    stable_stage_should_change: bool = False,
    current_stable_stage: str | None = STABLE_STAGE,
    checks: dict | None = None,
) -> dict:
    payload = {
        "passed": passed,
        "promotion_status": promotion_status,
        "stable_stage_should_change": stable_stage_should_change,
        "current_stable_stage": current_stable_stage,
        "validation_stage": validation_stage,
        "candidate_sha256": "fixture",
        "failures": [] if passed else ["intentional fixture failure"],
    }
    if checks is not None:
        payload["checks"] = checks
    return payload


def write_fixture(
    fixture: Path,
    *,
    bad_castle_decision: bool = False,
    missing_castle_proof: bool = False,
    missing_castle_matrix_proof: bool = False,
) -> argparse.Namespace:
    fixture.mkdir(parents=True, exist_ok=True)
    right_bottom_decision = fixture / "right-bottom-decision.json"
    right_bottom_matrix = fixture / "right-bottom-matrix.json"
    castle_decision = fixture / "castle-decision.json"
    castle_matrix = fixture / "castle-matrix.json"

    write_json(
        right_bottom_decision,
        decision_payload(validation_stage=stable_stage_guard.RIGHT_BOTTOM_VALIDATION_STAGE),
    )
    write_json(
        right_bottom_matrix,
        matrix_payload(validation_stage=stable_stage_guard.RIGHT_BOTTOM_VALIDATION_STAGE),
    )
    write_json(
        castle_decision,
        decision_payload(
            validation_stage=stable_stage_guard.CASTLECENTER_ALL_STAGE,
            decision="promote_to_stable" if bad_castle_decision else "defer_stable_promotion",
            stable_stage_should_change=bad_castle_decision,
            proof=None if missing_castle_proof else CASTLE_PROOF,
        ),
    )
    write_json(
        castle_matrix,
        matrix_payload(
            validation_stage=stable_stage_guard.CASTLECENTER_ALL_STAGE,
            current_stable_stage=None,
            checks=None if missing_castle_matrix_proof else CASTLE_MATRIX_CHECKS,
        ),
    )
    return argparse.Namespace(
        current_stable_stage=STABLE_STAGE,
        right_bottom_decision=right_bottom_decision,
        right_bottom_matrix=right_bottom_matrix,
        castle_decision=castle_decision,
        castle_matrix=castle_matrix,
    )


def with_stage_groups(groups: dict[str, tuple[str, ...]], callback) -> None:
    original = stable_stage_guard.patch_clash95_hd.STAGE_GROUPS
    stable_stage_guard.patch_clash95_hd.STAGE_GROUPS = groups
    try:
        callback()
    finally:
        stable_stage_guard.patch_clash95_hd.STAGE_GROUPS = original


def test_good_fixture(fixture: Path) -> None:
    args = write_fixture(fixture)
    guard = stable_stage_guard.build_guard(args)
    assert guard["passed"] is True, guard


def test_patcher_default_drift_fails(fixture: Path) -> None:
    args = write_fixture(fixture)
    original_default = stable_stage_guard.patch_clash95_hd.DEFAULT_STAGE
    stable_stage_guard.patch_clash95_hd.DEFAULT_STAGE = stable_stage_guard.CASTLECENTER_ALL_STAGE
    try:
        guard = stable_stage_guard.build_guard(args)
    finally:
        stable_stage_guard.patch_clash95_hd.DEFAULT_STAGE = original_default
    assert guard["passed"] is False, guard
    assert any("patcher default stage" in failure for failure in guard["failures"]), guard


def test_validation_group_leak_fails(fixture: Path) -> None:
    args = write_fixture(fixture)
    groups = {
        stage: tuple(stage_groups)
        for stage, stage_groups in stable_stage_guard.patch_clash95_hd.STAGE_GROUPS.items()
    }
    groups[STABLE_STAGE] = groups[STABLE_STAGE] + ("castle-overview-centered-input",)

    def check() -> None:
        guard = stable_stage_guard.build_guard(args)
        assert guard["passed"] is False, guard
        assert "castle-overview-centered-input" in guard["validation_only_groups_in_stable"], guard
        assert any("validation-only groups found in stable stage" in failure for failure in guard["failures"]), guard

    with_stage_groups(groups, check)


def test_validation_stage_scope_fails(fixture: Path) -> None:
    args = write_fixture(fixture)
    groups = {
        stage: tuple(stage_groups)
        for stage, stage_groups in stable_stage_guard.patch_clash95_hd.STAGE_GROUPS.items()
    }
    groups[stable_stage_guard.CASTLECENTER_ALL_STAGE] = tuple(
        group
        for group in groups[stable_stage_guard.CASTLECENTER_ALL_STAGE]
        if group != "castle-overview-centered-input"
    )

    def check() -> None:
        guard = stable_stage_guard.build_guard(args)
        assert guard["passed"] is False, guard
        assert any("is missing expected stable/validation groups" in failure for failure in guard["failures"]), guard

    with_stage_groups(groups, check)


def test_mapsurface_stages_cannot_use_global_menu_surface(fixture: Path) -> None:
    args = write_fixture(fixture)
    groups = {
        stage: tuple(stage_groups)
        for stage, stage_groups in stable_stage_guard.patch_clash95_hd.STAGE_GROUPS.items()
    }
    groups[STABLE_STAGE] = groups[STABLE_STAGE] + (stable_stage_guard.MENU_SURFACE_GROUP,)

    def check() -> None:
        guard = stable_stage_guard.build_guard(args)
        assert guard["passed"] is False, guard
        assert STABLE_STAGE in guard["mapsurface_with_menu_surface"], guard
        assert any("mapsurface stages still include global menu-surface group" in failure for failure in guard["failures"]), guard

    with_stage_groups(groups, check)


def test_mapsurface_stages_require_gameplay_upgrade(fixture: Path) -> None:
    args = write_fixture(fixture)
    groups = {
        stage: tuple(stage_groups)
        for stage, stage_groups in stable_stage_guard.patch_clash95_hd.STAGE_GROUPS.items()
    }
    groups[STABLE_STAGE] = tuple(
        group
        for group in groups[STABLE_STAGE]
        if group != stable_stage_guard.MAP_SURFACE_UPGRADE_GROUP
    )

    def check() -> None:
        guard = stable_stage_guard.build_guard(args)
        assert guard["passed"] is False, guard
        assert STABLE_STAGE in guard["mapsurface_missing_upgrade"], guard
        assert any("missing gameplay-only map surface upgrade" in failure for failure in guard["failures"]), guard

    with_stage_groups(groups, check)


def test_promotion_decision_fails(fixture: Path) -> None:
    args = write_fixture(fixture, bad_castle_decision=True)
    guard = stable_stage_guard.build_guard(args)
    assert guard["passed"] is False, guard
    assert any("decision is promote_to_stable" in failure for failure in guard["failures"]), guard
    assert any("would change the stable stage" in failure for failure in guard["failures"]), guard


def test_right_bottom_nonpassing_defer_remains_stable_safe(fixture: Path) -> None:
    args = write_fixture(fixture)
    write_json(
        args.right_bottom_decision,
        decision_payload(
            validation_stage=stable_stage_guard.RIGHT_BOTTOM_VALIDATION_STAGE,
            passed=False,
        ),
    )
    write_json(
        args.right_bottom_matrix,
        matrix_payload(
            validation_stage=stable_stage_guard.RIGHT_BOTTOM_VALIDATION_STAGE,
            passed=False,
        ),
    )
    guard = stable_stage_guard.build_guard(args)
    assert guard["passed"] is True, guard
    assert guard["checks"]["right_bottom_promotion_decision"]["summary"]["evidence_passed"] is False, guard
    assert guard["checks"]["right_bottom_evidence_matrix"]["summary"]["evidence_passed"] is False, guard


def test_castle_promotion_decision_missing_proof_fails(fixture: Path) -> None:
    args = write_fixture(fixture, missing_castle_proof=True)
    guard = stable_stage_guard.build_guard(args)
    assert guard["passed"] is False, guard
    assert any("missing required proof" in failure for failure in guard["failures"]), guard
    assert any("focused_displayed_wrapper_ok" in failure for failure in guard["failures"]), guard


def test_castle_evidence_matrix_missing_proof_fails(fixture: Path) -> None:
    args = write_fixture(fixture, missing_castle_matrix_proof=True)
    guard = stable_stage_guard.build_guard(args)
    assert guard["passed"] is False, guard
    assert any("evidence matrix missing required proof" in failure for failure in guard["failures"]), guard
    assert any("visible_multihit_completion_ok" in failure for failure in guard["failures"]), guard


def test_cli_writes_outputs_and_fails_closed(fixture: Path) -> None:
    good_args = write_fixture(fixture / "good")
    out_json = fixture / "good-output" / "stable.json"
    out_md = fixture / "good-output" / "stable.md"
    good_run = run_script(
        "--current-stable-stage",
        str(good_args.current_stable_stage),
        "--right-bottom-decision",
        str(good_args.right_bottom_decision),
        "--right-bottom-matrix",
        str(good_args.right_bottom_matrix),
        "--castle-decision",
        str(good_args.castle_decision),
        "--castle-matrix",
        str(good_args.castle_matrix),
        "--write-json",
        str(out_json),
        "--write-markdown",
        str(out_md),
        "--require-pass",
    )
    assert good_run.returncode == 0, good_run.stdout + good_run.stderr
    assert json.loads(out_json.read_text(encoding="utf-8"))["passed"] is True
    assert "- Overall: PASS" in out_md.read_text(encoding="utf-8")

    bad_args = write_fixture(fixture / "bad", bad_castle_decision=True)
    bad_json = fixture / "bad-output" / "stable.json"
    bad_md = fixture / "bad-output" / "stable.md"
    bad_run = run_script(
        "--current-stable-stage",
        str(bad_args.current_stable_stage),
        "--right-bottom-decision",
        str(bad_args.right_bottom_decision),
        "--right-bottom-matrix",
        str(bad_args.right_bottom_matrix),
        "--castle-decision",
        str(bad_args.castle_decision),
        "--castle-matrix",
        str(bad_args.castle_matrix),
        "--write-json",
        str(bad_json),
        "--write-markdown",
        str(bad_md),
        "--require-pass",
    )
    assert bad_run.returncode == 2, bad_run.stdout + bad_run.stderr
    assert json.loads(bad_json.read_text(encoding="utf-8"))["passed"] is False
    assert "- Overall: FAIL" in bad_md.read_text(encoding="utf-8")


def run_tests() -> None:
    fixture = ROOT / ".codex-loop" / "tmp-tests" / "stable-stage-guard-fixture"
    shutil.rmtree(fixture, ignore_errors=True)
    fixture.mkdir(parents=True)
    try:
        test_good_fixture(fixture / "good")
        test_patcher_default_drift_fails(fixture / "default-drift")
        test_validation_group_leak_fails(fixture / "validation-leak")
        test_validation_stage_scope_fails(fixture / "validation-scope")
        test_mapsurface_stages_cannot_use_global_menu_surface(fixture / "menu-surface-leak")
        test_mapsurface_stages_require_gameplay_upgrade(fixture / "map-surface-upgrade")
        test_promotion_decision_fails(fixture / "promotion-decision")
        test_right_bottom_nonpassing_defer_remains_stable_safe(fixture / "right-bottom-nonpassing-defer")
        test_castle_promotion_decision_missing_proof_fails(fixture / "missing-castle-proof")
        test_castle_evidence_matrix_missing_proof_fails(fixture / "missing-castle-matrix-proof")
        test_cli_writes_outputs_and_fails_closed(fixture / "cli")
    finally:
        shutil.rmtree(fixture, ignore_errors=True)


def main() -> int:
    run_tests()
    print("stable stage guard tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
