#!/usr/bin/env python3
"""Fixture tests for the right-bottom compose promotion decision helper."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "right_bottom_compose_promotion_decision.py"
sys.path.insert(0, str(ROOT / "tools"))

import right_bottom_compose_promotion_decision  # noqa: E402
import manual_directinput_checklist  # noqa: E402


STABLE_STAGE = right_bottom_compose_promotion_decision.DEFAULT_STABLE_STAGE
VALIDATION_STAGE = right_bottom_compose_promotion_decision.DEFAULT_VALIDATION_STAGE
REQUIRED_CHECKS = right_bottom_compose_promotion_decision.REQUIRED_CHECKS
CANDIDATE_SHA = "c" * 64


def write_valid_manual_proof(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "evidence_class": "manual_directinput",
                "approved_visible_runtime": True,
                "approval_record": "User explicitly approved visible manual DirectInput validation.",
                "candidate_path": "C:\\ClashTests\\manual-proof\\clash95_hd_manual.exe",
                "executable_sha256": "a" * 64,
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
                "approval_record": "User explicitly approved this right-bottom CDB-only promotion override.",
                "target_scope": "right_bottom_compose",
                "candidate_stage": VALIDATION_STAGE,
                "candidate_sha256": CANDIDATE_SHA,
                "accepted_risk": "CDB/proxy-only evidence bypasses live manual DirectInput proof.",
                "evidence_refs": [
                    "captures/current/right-bottom-compose-promotion-decision-current.json",
                    "captures/current/process-hygiene-guard-current.json",
                ],
                "no_stale_process_result": {
                    "passed": True,
                    "matching_process_count": 0,
                    "source": "captures/current/process-hygiene-guard-current.json",
                },
                "manual_directinput_bypass_reason": (
                    "Manual DirectInput proof is bypassed for this right-bottom scope because "
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


def check_payload(name: str, *, passed: bool = True) -> dict:
    summary = {"candidate_sha256": CANDIDATE_SHA}
    if name == "right_bottom_compose_fullstart_route":
        summary.update({"ready": True, "av_count": 0})
    elif name == "right_bottom_compose_normal_gate":
        summary.update({"surface": [800, 600], "visibility_unexplained_blank_cells": 0})
    elif name == "right_bottom_compose_ui_probe":
        summary.update({"rbui_desc_switch": 35, "rbui_panel_draw": 1, "rbui_action_box": 1})
    elif name == "right_bottom_compose_patch":
        summary.update({"right_bottom_patch_group": {"patched": 4, "total": 4}, "current_hd_map_gate": True})
    elif name == "right_bottom_grid_hit":
        summary.update(
            {
                "grid_hit_ok": True,
                "last_grid_entry": [450, 73],
                "last_grid_result": 0,
                "av_count": 0,
            }
        )
    elif name == "right_bottom_natural_route_guard":
        summary.update(
            {
                "state_gated_by_owner_flag": True,
                "owner_entry_flag": "0x00",
                "owner_flag_test": {"owner_flag": "0x00", "bit2": 0, "bit1": 0, "bit8": 0},
                "action_descriptor": {"slot": "d1", "x": 1000, "y": 426, "callback": "004338e0"},
                "descriptor_result": {"result": 0, "owner": "041bc71a", "owner_flag": "0x00", "surface": [800, 600]},
                "action_route_count": 0,
                "av_count": 0,
            }
        )
    elif name == "right_bottom_route_timing_guard":
        summary.update(
            {
                "patch_route_ordered_markers": 29,
                "fullstart_route_ordered_markers": 29,
                "grid_route_ordered_markers": 25,
                "grid_hit_ok": True,
                "last_grid_entry": [450, 73],
                "last_grid_result": 0,
                "failure_exit_count": 0,
                "av_count": 0,
            }
        )
    return {
        "passed": passed,
        "summary": summary,
        "failures": [] if passed else [f"intentional {name} fixture failure"],
    }


def checks_payload(*, failing: str | None = None, missing: str | None = None) -> dict:
    checks = {}
    for name in REQUIRED_CHECKS:
        if name == missing:
            continue
        checks[name] = check_payload(name, passed=name != failing)
    return checks


def args_for(
    *,
    manual_input_proof: Path | None = None,
    allow_cdb_only_promotion: bool = False,
    promotion_override_manifest: Path | None = None,
) -> argparse.Namespace:
    return argparse.Namespace(
        current_stable_stage=STABLE_STAGE,
        validation_stage=VALIDATION_STAGE,
        manual_input_proof=manual_input_proof,
        allow_cdb_only_promotion=allow_cdb_only_promotion,
        promotion_override_manifest=promotion_override_manifest,
    )


def write_refresh(path: Path, checks: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"checks": checks}, indent=2) + "\n", encoding="utf-8")
    return path


def test_deferred_by_default(fixture: Path) -> None:
    decision = right_bottom_compose_promotion_decision.build_decision_from_checks(
        args_for(),
        checks_payload(),
    )
    assert decision["passed"] is True, decision
    assert decision["decision"] == "defer_stable_promotion", decision
    assert decision["stable_stage_should_change"] is False, decision
    assert decision["manual_input_proof"] is None, decision
    assert decision["allow_cdb_only_promotion"] is False, decision
    assert "controlled native grid-hit proof is present" in decision["reasons"], decision
    assert "route timing/order guard is present" in decision["reasons"], decision
    assert "natural route owner-flag save-state proof is present" in decision["reasons"], decision
    assert "natural route action descriptor is parked off-screen" in decision["reasons"], decision
    assert "natural right-bottom UI probe has owner/action draw evidence" in decision["reasons"], decision


def test_natural_owner_action_rows_are_required(fixture: Path) -> None:
    checks = checks_payload()
    checks["right_bottom_compose_ui_probe"]["summary"]["rbui_panel_draw"] = 0
    checks["right_bottom_compose_ui_probe"]["summary"]["rbui_action_box"] = 0
    decision = right_bottom_compose_promotion_decision.build_decision_from_checks(args_for(), checks)
    assert decision["passed"] is False, decision
    assert decision["decision"] == "defer_stable_promotion", decision
    assert decision["stable_stage_should_change"] is False, decision
    assert any("natural UI probe did not enter owner/action draw rows" in failure for failure in decision["failures"]), decision
    assert "natural right-bottom UI probe does not enter owner/action draw rows" in decision["reasons"], decision


def test_natural_route_guard_summary_is_required(fixture: Path) -> None:
    cases = [
        ("state gate", "state_gated_by_owner_flag", False, "save-state gate"),
        ("action rows", "action_route_count", 1, "unexpectedly entered"),
        ("av rows", "av_count", 1, "natural route guard has AV"),
    ]
    for _label, key, value, expected_failure in cases:
        checks = checks_payload()
        checks["right_bottom_natural_route_guard"]["summary"][key] = value
        decision = right_bottom_compose_promotion_decision.build_decision_from_checks(args_for(), checks)
        assert decision["passed"] is False, decision
        assert decision["decision"] == "defer_stable_promotion", decision
        assert any(expected_failure in failure for failure in decision["failures"]), decision

    checks = checks_payload()
    checks["right_bottom_natural_route_guard"]["summary"]["owner_flag_test"]["bit2"] = 2
    decision = right_bottom_compose_promotion_decision.build_decision_from_checks(args_for(), checks)
    assert decision["passed"] is False, decision
    assert any("owner flag bits" in failure for failure in decision["failures"]), decision

    checks = checks_payload()
    checks["right_bottom_natural_route_guard"]["summary"]["action_descriptor"]["x"] = 799
    decision = right_bottom_compose_promotion_decision.build_decision_from_checks(args_for(), checks)
    assert decision["passed"] is False, decision
    assert any("action descriptor was not off-screen" in failure for failure in decision["failures"]), decision


def test_missing_or_failed_required_checks_fail(fixture: Path) -> None:
    for name in REQUIRED_CHECKS:
        failed = right_bottom_compose_promotion_decision.build_decision_from_checks(
            args_for(),
            checks_payload(failing=name),
        )
        assert failed["passed"] is False, failed
        assert failed["decision"] == "defer_stable_promotion", failed
        assert any(f"{name}: intentional {name} fixture failure" in failure for failure in failed["failures"]), failed

        missing = right_bottom_compose_promotion_decision.build_decision_from_checks(
            args_for(),
            checks_payload(missing=name),
        )
        assert missing["passed"] is False, missing
        assert any(f"{name} is missing" in failure for failure in missing["failures"]), missing


def test_valid_manual_input_proof_allows_stable_promotion(fixture: Path) -> None:
    proof = write_valid_manual_proof(fixture / "manual-proof.json")
    decision = right_bottom_compose_promotion_decision.build_decision_from_checks(
        args_for(manual_input_proof=proof),
        checks_payload(),
    )
    assert decision["passed"] is True, decision
    assert decision["decision"] == "eligible_for_stable_promotion", decision
    assert decision["stable_stage_should_change"] is True, decision
    assert decision["manual_input_proof"] == str(proof), decision
    assert decision["manual_input_proof_valid"] is True, decision


def test_placeholder_manual_input_proof_fails_closed(fixture: Path) -> None:
    proof = fixture / "manual-proof.md"
    proof.parent.mkdir(parents=True, exist_ok=True)
    proof.write_text("# proof placeholder\n", encoding="utf-8")
    decision = right_bottom_compose_promotion_decision.build_decision_from_checks(
        args_for(manual_input_proof=proof),
        checks_payload(),
    )
    assert decision["passed"] is False, decision
    assert decision["decision"] == "defer_stable_promotion", decision
    assert decision["stable_stage_should_change"] is False, decision
    assert decision["manual_input_proof_supplied"] is True, decision
    assert decision["manual_input_proof_valid"] is False, decision
    assert any("not valid JSON" in failure for failure in decision["failures"]), decision


def test_bare_cdb_only_override_is_blocked(fixture: Path) -> None:
    decision = right_bottom_compose_promotion_decision.build_decision_from_checks(
        args_for(allow_cdb_only_promotion=True),
        checks_payload(),
    )
    assert decision["passed"] is False, decision
    assert decision["decision"] == "defer_stable_promotion", decision
    assert decision["stable_stage_should_change"] is False, decision
    assert decision["allow_cdb_only_promotion"] is True, decision
    assert decision["bare_cdb_only_promotion_blocked"] is True, decision
    assert any("bare --allow-cdb-only-promotion" in failure for failure in decision["failures"]), decision


def test_manifest_backed_override_allows_promotion(fixture: Path) -> None:
    manifest = write_valid_override_manifest(fixture / "override.json")
    decision = right_bottom_compose_promotion_decision.build_decision_from_checks(
        args_for(promotion_override_manifest=manifest),
        checks_payload(),
    )
    assert decision["passed"] is True, decision
    assert decision["decision"] == "eligible_for_override_manifest_promotion", decision
    assert decision["stable_stage_should_change"] is True, decision
    assert decision["promotion_override_manifest"] == str(manifest), decision
    assert decision["promotion_override_manifest_valid"] is True, decision


def test_cli_writes_outputs_and_fails_closed(fixture: Path) -> None:
    good_refresh = write_refresh(fixture / "good" / "refresh.json", checks_payload())
    out_json = fixture / "good-output" / "decision.json"
    out_md = fixture / "good-output" / "decision.md"
    good_run = run_script(
        "--refresh-json",
        str(good_refresh),
        "--write-json",
        str(out_json),
        "--write-markdown",
        str(out_md),
        "--require-pass",
    )
    assert good_run.returncode == 0, good_run.stdout + good_run.stderr
    assert json.loads(out_json.read_text(encoding="utf-8"))["passed"] is True
    assert "- Decision record: PASS" in out_md.read_text(encoding="utf-8")

    bad_refresh = write_refresh(
        fixture / "bad" / "refresh.json",
        checks_payload(failing="right_bottom_compose_ui_probe"),
    )
    bad_json = fixture / "bad-output" / "decision.json"
    bad_md = fixture / "bad-output" / "decision.md"
    bad_run = run_script(
        "--refresh-json",
        str(bad_refresh),
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
        "--refresh-json",
        str(good_refresh),
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
        "--refresh-json",
        str(good_refresh),
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
        "--refresh-json",
        str(good_refresh),
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
    fixture = ROOT / ".codex-loop" / "tmp-tests" / "right-bottom-compose-promotion-fixture"
    shutil.rmtree(fixture, ignore_errors=True)
    fixture.mkdir(parents=True)
    try:
        test_deferred_by_default(fixture / "defer")
        test_natural_owner_action_rows_are_required(fixture / "natural-owner")
        test_natural_route_guard_summary_is_required(fixture / "natural-route")
        test_missing_or_failed_required_checks_fail(fixture / "required")
        test_valid_manual_input_proof_allows_stable_promotion(fixture / "manual")
        test_placeholder_manual_input_proof_fails_closed(fixture / "placeholder-manual")
        test_bare_cdb_only_override_is_blocked(fixture / "override")
        test_manifest_backed_override_allows_promotion(fixture / "manifest")
        test_cli_writes_outputs_and_fails_closed(fixture / "cli")
    finally:
        shutil.rmtree(fixture, ignore_errors=True)


def main() -> int:
    run_tests()
    print("right-bottom compose promotion decision tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
