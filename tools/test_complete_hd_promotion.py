#!/usr/bin/env python3
"""Fixture tests for the HD promotion orchestrator.

Subprocesses are replaced with fixture report writers. These tests never run
promotion sub-tools, alter the release checklist, or launch runtime.
"""

from __future__ import annotations

import contextlib
import io
import json
import shutil
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import complete_hd_promotion as promo  # noqa: E402


def _args(**overrides):
    argv = ["--run-manifest", "captures/archive/run/run-manifest.json"]
    for key, value in overrides.items():
        flag = "--" + key.replace("_", "-")
        if value is True:
            argv.append(flag)
        elif value is not None:
            argv.extend([flag, str(value)])
    return promo.parse_args(argv)


def test_step_plan_order_without_battle() -> None:
    steps = promo.plan_steps(_args())
    names = [name for name, _ in steps]
    assert names == [
        "assemble_proof",
        "manual_checklist",
        "right_bottom_promotion",
        "castle_overview_promotion",
    ], names


def test_step_plan_includes_battle_when_dir_given() -> None:
    steps = promo.plan_steps(_args(battle_run_dir="captures/archive/battle"))
    names = [name for name, _ in steps]
    assert "battle_click_consumed" in names
    assert names.index("battle_click_consumed") == 2, names


def test_every_planned_step_has_an_isolated_artifact() -> None:
    artifact_dir = Path("fixture-promotion-artifacts")
    for args in (_args(), _args(battle_run_dir="captures/archive/battle")):
        steps = promo.plan_steps(args, artifact_dir)
        outputs = promo.artifact_paths(artifact_dir)
        names = [name for name, _ in steps]
        assert set(names) <= outputs.keys(), names
        assert len(names) == len(set(names)), names
        for name, argv in steps:
            flag = "--write-report-json" if name == "assemble_proof" else "--write-json"
            assert argv.count(flag) == 1, (name, argv)
            assert Path(argv[argv.index(flag) + 1]) == outputs[name], (name, argv)
            if name != "assemble_proof":
                assert argv.count("--write-markdown") == 1, (name, argv)
                assert Path(argv[argv.index("--write-markdown") + 1]) == outputs[name].with_suffix(".md")
        # The component plan remains isolated from release mode. Full release
        # evidence goes through the separate candidate-bound evaluator.
        assert "hd_layout_promotion" not in names, names
        assert all(Path(argv[0]).name != "current_evidence_refresh.py" for _, argv in steps), steps


def test_step_flags_reference_proof_and_manifest() -> None:
    args = _args(observations="obs.json", proof_json="p.json")
    steps = dict(promo.plan_steps(args))
    assemble = " ".join(steps["assemble_proof"])
    assert "assemble_manual_directinput_proof.py" in assemble
    assert "--run-manifest" in assemble and "--observations obs.json" in assemble
    assert "--output p.json" in assemble and "--require-valid" in assemble
    for key in ("right_bottom_promotion", "castle_overview_promotion"):
        joined = " ".join(steps[key])
        assert "--manual-input-proof p.json" in joined, joined
        assert "--require-pass" in joined
    checklist = " ".join(steps["manual_checklist"])
    assert "--require-promotion-ready" in checklist


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def fixture_proof() -> dict:
    return {
        "evidence_class": "manual_directinput",
        "approved_visible_runtime": True,
        "approval_record": "fixture-only approved session; not runtime evidence",
        "candidate_path": r"C:\ClashTests\fixture\candidate.exe",
        "executable_sha256": "a" * 64,
        "no_stale_processes": True,
        "checked_items": [
            {"id": item["id"], "stage": item["stage"], "status": "pass",
             "candidate_path": r"C:\ClashTests\fixture\component.exe", "executable_sha256": "b" * 64,
             "observed_result": "fixture observation", "evidence": "fixture evidence",
             "pass_fail_notes": "fixture pass", "no_crash": True}
            for item in promo.manual_directinput_checklist.CHECKLIST_ITEMS
        ],
    }


def fixture_runner(args, calls: list[str], *, edits=None, exit_codes=None,
                   omitted=None, proof_edit=None):
    """Emit only synthetic JSON; no child process or production output path."""
    edits = edits or {}
    exit_codes = exit_codes or {}
    omitted = omitted or set()

    def run(name: str, argv: list[str]) -> dict:
        calls.append(name)
        proof = fixture_proof()
        common = {"generated_at": datetime.now(timezone.utc).isoformat(),
                  "passed": True, "failures": []}
        proof_summary = {"executable_sha256": proof["executable_sha256"], "checked_item_count": 5}
        if name == "assemble_proof":
            if proof_edit:
                proof_edit(proof)
            write_json(args.proof_json, proof)
            report = {**common, **proof_summary, "manual_proof_valid": True,
                      "run_manifest": str(args.run_manifest), "output_path": str(args.proof_json),
                      "observations": str(args.observations) if args.observations else None,
                      "passing_ids": promo.manual_directinput_checklist.REQUIRED_IDS}
            output = Path(argv[argv.index("--write-report-json") + 1])
        elif name == "battle_click_consumed":
            report = {**common, "real_visible_click_consumed": True, "invalid_run_count": 0,
                      "runs": [{"path": str(args.battle_run_dir)}]}
            output = Path(argv[argv.index("--write-json") + 1])
        else:
            manual = name == "manual_checklist"
            prefix = "manual_proof" if manual else "manual_input_proof"
            report = {**common, prefix: str(args.proof_json), prefix + "_supplied": True,
                      prefix + "_valid": True, prefix + "_summary": dict(proof_summary),
                      "allow_cdb_only_promotion": False}
            if manual:
                report["promotion_ready"] = True
            else:
                stable = promo.manual_directinput_checklist.CURRENT_STABLE_STAGE
                report.update({"decision": "eligible_for_stable_promotion",
                               "stable_stage_should_change": True, "current_stable_stage": stable,
                               "candidate_sha256": "b" * 64,
                               "promotion_override_manifest_supplied": False})
                if name == "right_bottom_promotion":
                    report["validation_stage"] = stable + "-rightbottomcompose"
                else:
                    report["validation_stage"] = "castlecenter-all"
                    report["resolved_validation_stage"] = stable + "-castlecenter-all"
            output = Path(argv[argv.index("--write-json") + 1])
        if name in edits:
            edits[name](report)
        if name not in omitted:
            write_json(output, report)
        return {"name": name, "exit_code": exit_codes.get(name, 0), "passed": True,
                "stdout_tail": "fixture output", "stderr_tail": ""}

    return run


def evaluate_fixture(fixture: Path, **runner_options):
    args = _args(proof_json=fixture / "proof.json", write_json=fixture / "summary.json")
    calls: list[str] = []
    report = promo.run_component_sequence(
        args, fixture / "artifacts", runner=fixture_runner(args, calls, **runner_options)
    )
    return report, calls


def test_affirmative_components_are_not_whole_hd_readiness(fixture: Path) -> None:
    report, calls = evaluate_fixture(fixture)
    assert len(calls) == 4, (calls, report)
    assert report["passed"] and report["component_promotion_ready"], report
    assert report["component_candidate_identity_bound"] is True, report
    assert report["promotion_ready"] is False and report["stable_stage_should_change"] is False, report
    assert report["whole_hd_acceptance_evaluated"] is False, report
    assert report["checklist_updated"] is None, report
    assert set(report["unimplemented_acceptance_requirements"]) == {
        "hd_layout", "endurance", "continuity", "combined_candidate", "resolution_coverage", "promotion_decision"
    }, report
    assert all(Path(step["artifact_json"]).is_file() for step in report["steps"]), report


def test_exit_zero_deferred_decision_fails(fixture: Path) -> None:
    def defer(report):
        report.update(decision="defer_stable_promotion", stable_stage_should_change=False,
                      reasons=["manual approval or evidence remains missing"])
    report, calls = evaluate_fixture(fixture, edits={"right_bottom_promotion": defer})
    assert report["passed"] is False and report["component_promotion_ready"] is False, report
    assert calls[-1] == "right_bottom_promotion" and "castle_overview_promotion" in report["skipped_steps"], report
    assert report["steps"][-1]["process_passed"] is True, report
    assert "manual approval or evidence remains missing" in report["steps"][-1]["report"]["reasons"], report


def test_stale_missing_and_wrongproof_artifacts_fail(fixture: Path) -> None:
    cases = {
        "stale": lambda report: report.update(generated_at=(datetime.now(timezone.utc) - timedelta(days=1)).isoformat()),
        "future": lambda report: report.update(generated_at=(datetime.now(timezone.utc) + timedelta(days=1)).isoformat()),
        "wrong_path": lambda report: report.update(manual_input_proof="unrelated-proof.json"),
        "wrong_sha": lambda report: report["manual_input_proof_summary"].update(executable_sha256="c" * 64),
        "wrong_count": lambda report: report["manual_input_proof_summary"].update(checked_item_count=4),
        "wrong_stage": lambda report: report.update(validation_stage="different-stage"),
        "invalid_proof": lambda report: report.update(manual_input_proof_valid=False),
        "override": lambda report: report.update(decision="eligible_for_override_manifest_promotion"),
    }
    for name, edit in cases.items():
        report, _ = evaluate_fixture(fixture / name, edits={"right_bottom_promotion": edit})
        assert not report["passed"] and not report["component_promotion_ready"], (name, report)
        assert report["promotion_ready"] is False and report["checklist_updated"] is None, (name, report)
    for step in ("assemble_proof", "manual_checklist", "right_bottom_promotion", "castle_overview_promotion"):
        report, calls = evaluate_fixture(fixture / ("missing-" + step), omitted={step})
        assert report["passed"] is False and calls[-1] == step, (step, report)


def test_prerequisite_failure_stops_and_preserves_blockers(fixture: Path) -> None:
    for step in ("assemble_proof", "manual_checklist"):
        report, calls = evaluate_fixture(
            fixture / step, exit_codes={step: 2},
            edits={step: lambda payload: payload.update(passed=False, failures=["required approval missing", "target evidence missing"])},
        )
        assert calls[-1] == step and "right_bottom_promotion" not in calls, report
        assert any("required approval missing" in failure for failure in report["failures"]), report
        assert any("target evidence missing" in failure for failure in report["failures"]), report
    report, calls = evaluate_fixture(fixture / "unapproved", proof_edit=lambda proof: proof.update(approved_visible_runtime=False))
    assert calls == ["assemble_proof"] and not report["passed"], report


def test_optional_battle_report_is_bound_to_supplied_run(fixture: Path) -> None:
    args = _args(proof_json=fixture / "proof.json", battle_run_dir=fixture / "recorded-battle")
    calls: list[str] = []
    report = promo.run_component_sequence(args, fixture / "passing", runner=fixture_runner(args, calls))
    assert report["passed"] and report["battle_evaluated"], report
    assert report["battle_candidate_identity_bound"] is False, report
    assert "no candidate SHA/stage" in report["battle_evidence_scope"], report
    calls.clear()
    report = promo.run_component_sequence(
        args, fixture / "unrelated",
        runner=fixture_runner(args, calls, edits={"battle_click_consumed": lambda payload: payload.update(runs=[{"path": "unrelated-battle"}])}),
    )
    assert calls[-1] == "battle_click_consumed" and not report["passed"], report


def test_component_candidate_matches_each_manual_target(fixture: Path) -> None:
    target_ids = [target for targets in promo.COMPONENT_MANUAL_TARGETS.values() for target in targets]
    for target_id in target_ids:
        for field, replacement in (("executable_sha256", None), ("executable_sha256", "c" * 64),
                                   ("candidate_path", r"C:\Clash\clash95.exe")):
            def edit(proof, target_id=target_id, field=field, replacement=replacement):
                target = next(item for item in proof["checked_items"] if item["id"] == target_id)
                target[field] = replacement
            report, _ = evaluate_fixture(fixture / f"{target_id}-{field}-{replacement is None}", proof_edit=edit)
            assert not report["passed"] and not report["component_candidate_identity_bound"], report
            assert any(target_id in failure for failure in report["failures"]), report


def test_proof_mutation_and_existing_output_fail(fixture: Path) -> None:
    args = _args(proof_json=fixture / "proof.json")
    calls: list[str] = []
    fake = fixture_runner(args, calls)
    def mutate(name, argv):
        result = fake(name, argv)
        if name == "manual_checklist":
            payload = json.loads(args.proof_json.read_text())
            payload["approval_record"] = "different fixture approval"
            write_json(args.proof_json, payload)
        return result
    report = promo.run_component_sequence(args, fixture / "mutated", runner=mutate)
    assert calls == ["assemble_proof", "manual_checklist"] and not report["passed"], report
    assert any("manual proof changed" in failure for failure in report["failures"]), report
    calls.clear()
    output = promo.artifact_paths(fixture / "existing")["assemble_proof"]
    write_json(output, {"passed": True})
    report = promo.run_component_sequence(args, fixture / "existing", runner=fake)
    assert calls == [] and not report["passed"], report


def test_checklist_request_is_blocked_and_main_uses_unique_outputs(fixture: Path) -> None:
    args = _args(proof_json=fixture / "proof.json", write_json=fixture / "summary.json", update_checklist=True)
    calls: list[str] = []
    fake = fixture_runner(args, calls)
    checklist = ROOT / "reports" / "final_hd_release_checklist.md"
    before = checklist.read_bytes()
    paths = []
    for index in range(2):
        with patch.object(promo, "run_step", fake), contextlib.redirect_stdout(io.StringIO()):
            argv = [
                "--run-manifest", str(args.run_manifest), "--proof-json", str(args.proof_json),
                "--write-json", str(args.write_json), "--update-checklist",
            ]
            result = promo.main(argv + (["--require-pass"] if index == 0 else []))
        assert result == 2, result
        report = json.loads(args.write_json.read_text())
        assert report["component_promotion_ready"] is True and report["passed"] is False, report
        assert report["checklist_updated"] is None and report["promotion_ready"] is False, report
        paths.append(report["steps"][0]["artifact_json"])
    assert paths[0] != paths[1], paths
    assert checklist.read_bytes() == before


def run_tests() -> None:
    fixture = ROOT / ".codex-loop" / "tmp-tests" / "complete-hd-promotion"
    shutil.rmtree(fixture, ignore_errors=True)
    fixture.mkdir(parents=True)
    try:
        test_step_plan_order_without_battle()
        test_step_plan_includes_battle_when_dir_given()
        test_every_planned_step_has_an_isolated_artifact()
        test_step_flags_reference_proof_and_manifest()
        test_affirmative_components_are_not_whole_hd_readiness(fixture / "affirmative")
        test_exit_zero_deferred_decision_fails(fixture / "deferred")
        test_stale_missing_and_wrongproof_artifacts_fail(fixture / "bad-artifacts")
        test_prerequisite_failure_stops_and_preserves_blockers(fixture / "prerequisites")
        test_optional_battle_report_is_bound_to_supplied_run(fixture / "battle")
        test_component_candidate_matches_each_manual_target(fixture / "component-identity")
        test_proof_mutation_and_existing_output_fail(fixture / "identity")
        test_checklist_request_is_blocked_and_main_uses_unique_outputs(fixture / "checklist")
    finally:
        shutil.rmtree(fixture, ignore_errors=True)


def main() -> int:
    run_tests()
    print("complete HD promotion tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
