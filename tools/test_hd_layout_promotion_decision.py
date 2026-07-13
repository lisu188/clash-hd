#!/usr/bin/env python3
"""Fixture tests for the fail-closed HD-layout promotion decision."""

from __future__ import annotations

import argparse
import copy
import json
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "hd_layout_promotion_decision.py"
sys.path.insert(0, str(ROOT / "tools"))

import hd_layout_promotion_decision as decision_tool  # noqa: E402


SHA = decision_tool.EXPECTED_CANDIDATE_SHA256
STABLE = decision_tool.PROTECTED_STABLE_STAGE
STAGE = decision_tool.HD_LAYOUT_STAGE


def valid_payloads() -> dict[str, dict]:
    hidden_checks = {
        name: {"passed": True}
        for name in (
            "no_access_violation",
            "tooltip_init_anchor",
            "panel_setup",
            "panel_draws",
            "panel_hitscan_anchor",
            "panel_redraw_clip",
        )
    }
    visible_checks = {
        "candidate_identity": {"passed": True},
        "map_capture_authenticity": {
            "passed": True,
            "hash_matches": True,
            "handles_match": True,
            "capture_mode": "screen",
        },
        "hover_capture_authenticity": {
            "passed": True,
            "hash_matches": True,
            "handles_match": True,
            "capture_mode": "screen",
        },
        "gameplay_route": {"passed": True},
        "tooltip_bottom_center_visible": {"passed": True},
        "panel_right_bottom_visible": {"passed": True},
    }
    items = [
        {"id": f"manual-{index}", "status": "pending_manual"}
        for index in range(5)
    ]
    return {
        "patch": {
            "stage": STAGE,
            "exe_sha256": SHA,
            "groups": copy.deepcopy(decision_tool.EXPECTED_PATCH_GROUPS),
            "current_hd_map_gate": {
                "passed": True,
                "checks": {
                    "visible_tiles_12x9": {"passed": True},
                    "present_bounds_800": {"passed": True},
                },
            },
        },
        "hidden": {
            "passed": True,
            "redraw_clip_proved": True,
            "target_size": [800, 600],
            "checks": hidden_checks,
        },
        "hidden_run": {
            "Passed": True,
            "HiddenDesktop": True,
            "AllowVisibleDesktop": False,
            "Stage": STAGE,
            "CandidateSha256": SHA,
        },
        "visible": {
            "passed": True,
            "evidence_class": "approved_visible_automated_layout_composition",
            "candidate_sha256": SHA,
            "checks": visible_checks,
            "automated_hover_alignment": {
                "passed": True,
                "requested_client": [640, 544],
                "actual_client": [640, 544],
                "click_event_count": 0,
                "proof_class": "automated_win32_setcursor_alignment",
                "manual_directinput_proof": False,
                "command_click_alignment": False,
            },
            "failed_panel_click_attempt": {
                "attempt_observed": True,
                "requested_client": [760, 560],
                "actual_client": [716, 493],
                "client_error": [-44, -67],
                "path_verified": False,
                "click_path_verified": False,
                "alignment_passed": False,
                "classified_failed_attempt": True,
            },
            "command_click_alignment": False,
            "panel_click_callback_proof": False,
            "manual_directinput_proof": False,
            "stable_stage_promotion_ready": False,
            "promotion_ready": False,
        },
        "manual": {
            "passed": True,
            "status": "pending_manual_validation",
            "manual_proof": None,
            "manual_proof_supplied": False,
            "manual_proof_valid": False,
            "manual_proof_summary": {"checked_item_count": 0},
            "promotion_ready": False,
            "stable_stage_should_change": False,
            "items": items,
            "summary": {
                "pending_count": 5,
                "promotion_ready": False,
                "stable_stage_should_change": False,
            },
        },
        "process_hygiene": {
            "passed": True,
            "matching_process_count": 0,
            "matching_processes": [],
        },
    }


def args_for(
    *,
    current_stable_stage: str = STABLE,
    allow_cdb_only_promotion: bool = False,
    promotion_override_manifest: Path | None = None,
) -> argparse.Namespace:
    return argparse.Namespace(
        current_stable_stage=current_stable_stage,
        allow_cdb_only_promotion=allow_cdb_only_promotion,
        promotion_override_manifest=promotion_override_manifest,
    )


def evaluate(
    payloads: dict[str, dict] | None = None,
    args: argparse.Namespace | None = None,
) -> dict:
    return decision_tool.evaluate_decision(
        args or args_for(),
        **(payloads or valid_payloads()),
    )


def assert_failed(decision: dict, fragment: str) -> None:
    assert decision["passed"] is False, decision
    assert decision["decision"] == "defer_stable_promotion", decision
    assert decision["stable_stage_should_change"] is False, decision
    assert decision["promotion_ready"] is False, decision
    assert decision["override_accepted"] is False, decision
    assert any(fragment in failure for failure in decision["failures"]), decision


def test_current_evidence_defers_and_passes() -> None:
    decision = evaluate()
    assert decision["passed"] is True, decision
    assert decision["decision"] == "defer_stable_promotion", decision
    assert decision["stable_stage_should_change"] is False, decision
    assert decision["current_stable_stage"] == STABLE, decision
    assert decision["validation_stage"] == STAGE, decision
    assert decision["candidate_sha256"] == SHA, decision
    assert decision["manual_directinput_proof"] is False, decision
    assert decision["manual_checked_item_count"] == 0, decision
    assert decision["manual_checklist_item_count"] == 5, decision
    assert decision["command_click_alignment"] is False, decision
    assert decision["panel_click_callback_proof"] is False, decision
    assert decision["promotion_ready"] is False, decision
    assert decision["override_accepted"] is False, decision
    assert all(check["passed"] for check in decision["checks"].values()), decision


def test_sha_drift_fails_closed() -> None:
    cases = (
        ("patch", "exe_sha256"),
        ("hidden_run", "CandidateSha256"),
        ("visible", "candidate_sha256"),
    )
    for source, key in cases:
        payloads = valid_payloads()
        payloads[source][key] = "A" * 64
        source_label = {
            "patch": "patch_manifest",
            "hidden_run": "hidden_archived_run",
            "visible": "visible_composition",
        }[source]
        assert_failed(evaluate(payloads), f"{source_label} candidate SHA-256")


def test_hidden_or_visible_failure_fails_closed() -> None:
    payloads = valid_payloads()
    payloads["hidden"]["passed"] = False
    assert_failed(evaluate(payloads), "hidden HD-layout geometry summary is not passing")

    payloads = valid_payloads()
    payloads["hidden_run"]["Passed"] = False
    assert_failed(evaluate(payloads), "archived hidden-desktop run summary is not passing")

    payloads = valid_payloads()
    payloads["visible"]["passed"] = False
    assert_failed(evaluate(payloads), "visible HD-layout composition summary is not passing")

    payloads = valid_payloads()
    payloads["visible"]["checks"]["hover_capture_authenticity"]["hash_matches"] = False
    assert_failed(evaluate(payloads), "authentic hash/handle-matched screen capture")


def test_click_cannot_be_reclassified_as_success() -> None:
    mutations = (
        ("failed", "alignment_passed", True, "alignment_passed=true"),
        ("failed", "path_verified", True, "path_verified=true"),
        ("visible", "command_click_alignment", True, "command-click alignment"),
        ("visible", "panel_click_callback_proof", True, "command-panel callback"),
    )
    for scope, key, value, fragment in mutations:
        payloads = valid_payloads()
        target = (
            payloads["visible"]["failed_panel_click_attempt"]
            if scope == "failed"
            else payloads["visible"]
        )
        target[key] = value
        assert_failed(evaluate(payloads), fragment)

    payloads = valid_payloads()
    payloads["visible"]["failed_panel_click_attempt"]["actual_client"] = [760, 560]
    assert_failed(evaluate(payloads), "failed command click actual_client")


def test_manual_or_promotion_claim_fails_closed() -> None:
    payloads = valid_payloads()
    payloads["visible"]["manual_directinput_proof"] = True
    assert_failed(evaluate(payloads), "manual_directinput_proof=true")

    payloads = valid_payloads()
    payloads["visible"]["promotion_ready"] = True
    assert_failed(evaluate(payloads), "promotion_ready=true")

    payloads = valid_payloads()
    payloads["manual"]["manual_proof_supplied"] = True
    payloads["manual"]["manual_proof_valid"] = True
    payloads["manual"]["manual_proof_summary"]["checked_item_count"] = 1
    payloads["manual"]["items"][0]["status"] = "passed"
    assert_failed(evaluate(payloads), "manual DirectInput proof was supplied or claimed valid")

    payloads = valid_payloads()
    payloads["manual"]["promotion_ready"] = True
    payloads["manual"]["summary"]["promotion_ready"] = True
    assert_failed(evaluate(payloads), "manual checklist incorrectly claims promotion readiness")


def test_stable_stage_mismatch_fails_closed() -> None:
    assert_failed(
        evaluate(args=args_for(current_stable_stage=f"{STABLE}-changed")),
        "current stable stage is",
    )

    payloads = valid_payloads()
    payloads["patch"]["stage"] = STABLE
    assert_failed(evaluate(payloads), "expected exact HD-layout stage")

    payloads = valid_payloads()
    payloads["hidden_run"]["Stage"] = STABLE
    assert_failed(evaluate(payloads), "archived hidden run stage")


def test_all_override_routes_are_rejected(fixture: Path) -> None:
    assert_failed(
        evaluate(args=args_for(allow_cdb_only_promotion=True)),
        "CDB-only promotion overrides are prohibited",
    )
    assert_failed(
        evaluate(args=args_for(promotion_override_manifest=fixture / "override.json")),
        "promotion override manifests are not accepted",
    )


def write_payloads(fixture: Path, payloads: dict[str, dict]) -> dict[str, Path]:
    fixture.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    for name, payload in payloads.items():
        path = fixture / f"{name}.json"
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        paths[name] = path
    return paths


def run_cli(paths: dict[str, Path], out_dir: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--patch-json",
            str(paths["patch"]),
            "--hidden-json",
            str(paths["hidden"]),
            "--hidden-run-json",
            str(paths["hidden_run"]),
            "--visible-json",
            str(paths["visible"]),
            "--manual-json",
            str(paths["manual"]),
            "--process-hygiene-json",
            str(paths["process_hygiene"]),
            "--write-json",
            str(out_dir / "decision.json"),
            "--write-markdown",
            str(out_dir / "decision.md"),
            "--require-pass",
            *extra,
        ],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def test_cli_writes_pass_and_fails_closed(fixture: Path) -> None:
    good_paths = write_payloads(fixture / "good-inputs", valid_payloads())
    good_out = fixture / "good-output"
    good = run_cli(good_paths, good_out)
    assert good.returncode == 0, good.stdout + good.stderr
    good_json = json.loads((good_out / "decision.json").read_text(encoding="utf-8"))
    assert good_json["passed"] is True, good_json
    assert good_json["decision"] == "defer_stable_promotion", good_json
    assert good_json["stable_stage_should_change"] is False, good_json
    good_md = (good_out / "decision.md").read_text(encoding="utf-8")
    assert "- Decision record: `PASS`" in good_md, good_md
    assert "Visible composition PASS is not command-input" in good_md, good_md

    bad_payloads = valid_payloads()
    bad_payloads["visible"]["command_click_alignment"] = True
    bad_paths = write_payloads(fixture / "bad-inputs", bad_payloads)
    bad_out = fixture / "bad-output"
    bad = run_cli(bad_paths, bad_out)
    assert bad.returncode == 2, bad.stdout + bad.stderr
    bad_json = json.loads((bad_out / "decision.json").read_text(encoding="utf-8"))
    assert bad_json["passed"] is False, bad_json
    assert bad_json["stable_stage_should_change"] is False, bad_json

    override_out = fixture / "override-output"
    override = run_cli(good_paths, override_out, "--allow-cdb-only-promotion")
    assert override.returncode == 2, override.stdout + override.stderr
    override_json = json.loads(
        (override_out / "decision.json").read_text(encoding="utf-8")
    )
    assert override_json["override_accepted"] is False, override_json


def run_tests() -> None:
    fixture = ROOT / ".codex-loop" / "tmp-tests" / "hd-layout-promotion-decision"
    shutil.rmtree(fixture, ignore_errors=True)
    fixture.mkdir(parents=True)
    try:
        test_current_evidence_defers_and_passes()
        test_sha_drift_fails_closed()
        test_hidden_or_visible_failure_fails_closed()
        test_click_cannot_be_reclassified_as_success()
        test_manual_or_promotion_claim_fails_closed()
        test_stable_stage_mismatch_fails_closed()
        test_all_override_routes_are_rejected(fixture / "override")
        test_cli_writes_pass_and_fails_closed(fixture / "cli")
    finally:
        shutil.rmtree(fixture, ignore_errors=True)


def main() -> int:
    run_tests()
    print("HD layout promotion decision tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
