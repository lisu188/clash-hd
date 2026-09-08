#!/usr/bin/env python3
"""Evaluate right-bottom and castle promotion eligibility from recorded proof.

Fresh affirmative JSON decisions, bound to the assembled manual proof, are
required; a successful tool exit can also describe a valid deferred decision.
This component sequence does not implement whole-HD release acceptance or
change the stable stage. --update-checklist remains accepted but fails closed
until the missing whole-HD acceptance path exists. The runbook also requires
HD-layout and final aggregate acceptance; its historical HD-layout parser has
no affirmative promotion path, and refreshing reports cannot replace those
requirements. This scoped sequence launches neither runtime nor an aggregate
refresh.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

import manual_directinput_checklist


ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
PROOF_JSON = Path("captures/current/manual-directinput-proof-current.json")
DEFAULT_SUMMARY_JSON = Path("captures/current/complete-hd-promotion-current.json")

RUNTIME_POLICY = (
    "repo-only promotion orchestrator; runs assembler + checklist + promotion "
    "decision tools over already-captured artifacts; launches no game, VM, CDB, "
    "wrapper, PowerShell, or visible window"
)

WHOLE_HD_REQUIREMENTS = {
    "hd_layout": (
        "Affirmative HD-layout eligibility bound to candidate and manual/input evidence; "
        "tools/hd_layout_promotion_decision.py currently records the deferred historical frontier."
    ),
    "endurance": (
        "Complete the ordered short soak ladder and both 2h map-idle/map-pan routes with "
        "matching report/guard identities and real process/render telemetry; evaluate "
        "tools/hd_endurance_release_checklist.py without treating hidden endurance as manual input."
    ),
    "continuity": (
        "Evaluate tools/hd_continuity_status.py and evidence for repeated gameplay transitions, "
        "save/load and turn/day-wrap continuity; retain separate approved visible/manual requirements."
    ),
    "combined_candidate": (
        "An explicit combined validation stage/candidate needs byte gates and compatible render, "
        "input and runtime evidence for the actual group union; separate component SHAs do not prove it."
    ),
    "resolution_coverage": (
        "Validate every advertised release preset in src/launcher/resolutions.json with its own "
        "byte gate and evidence lane; unvalidated/custom resolutions remain experimental."
    ),
    "promotion_decision": (
        "An explicit promotion decision with the complete acceptance set is required before any "
        "protected stable-stage or release-checklist change. This orchestrator does not implement it."
    ),
}
COMPONENT_MANUAL_TARGETS = {
    "right_bottom_promotion": ("right_bottom_validation_input",),
    "castle_overview_promotion": ("castle_barracks_centered_input", "castle_overview_centered_input"),
}


def repo_path(path: Path | str) -> Path:
    path = Path(path)
    return (path if path.is_absolute() else ROOT / path).resolve()


def artifact_paths(directory: Path) -> dict[str, Path]:
    return {
        name: directory / f"{name}.json"
        for name in (
            "assemble_proof", "manual_checklist", "battle_click_consumed",
            "right_bottom_promotion", "castle_overview_promotion",
        )
    }


def plan_steps(args: argparse.Namespace, artifact_dir: Path | None = None) -> list[tuple[str, list[str]]]:
    """Build the scoped component plan; whole-HD acceptance remains separate."""
    outputs = artifact_paths(artifact_dir or DEFAULT_SUMMARY_JSON.parent / "complete-hd-promotion-artifacts")
    assemble_argv = [
        str(TOOLS / "assemble_manual_directinput_proof.py"),
        "--run-manifest", str(args.run_manifest),
        "--output", str(args.proof_json),
        "--write-report-json", str(outputs["assemble_proof"]),
        "--require-valid",
    ]
    if args.observations:
        assemble_argv += ["--observations", str(args.observations)]

    steps: list[tuple[str, list[str]]] = [
        ("assemble_proof", assemble_argv),
        (
            "manual_checklist",
            [
                str(TOOLS / "manual_directinput_checklist.py"),
                "--manual-proof", str(args.proof_json),
                "--require-pass",
                "--require-promotion-ready",
            ],
        ),
    ]
    if args.battle_run_dir:
        steps.append(
            (
                "battle_click_consumed",
                [
                    str(TOOLS / "battle_visible_input_summary.py"),
                    str(args.battle_run_dir),
                    "--require-click-consumed",
                    "--require-command-ready",
                    "--require-no-invalid",
                ],
            )
        )
    steps.append(
        (
            "right_bottom_promotion",
            [
                str(TOOLS / "right_bottom_compose_promotion_decision.py"),
                "--manual-input-proof", str(args.proof_json),
                "--require-pass",
            ],
        )
    )
    steps.append(
        (
            "castle_overview_promotion",
            [
                str(TOOLS / "castle_overview_promotion_decision.py"),
                "--manual-input-proof", str(args.proof_json),
                "--require-pass",
            ],
        )
    )
    for name, argv in steps:
        if name != "assemble_proof":
            argv.extend([
                "--write-json", str(outputs[name]),
                "--write-markdown", str(outputs[name].with_suffix(".md")),
            ])
    return steps


def run_step(name: str, argv: list[str]) -> dict[str, Any]:
    proc = subprocess.run(
        [sys.executable, *argv],
        cwd=str(ROOT),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    return {
        "name": name,
        "command": " ".join(argv),
        "exit_code": proc.returncode,
        "passed": proc.returncode == 0,
        "stdout_tail": proc.stdout[-2000:],
        "stderr_tail": proc.stderr[-2000:],
    }


def read_fresh_report(path: Path, started: datetime, finished: datetime) -> dict[str, Any]:
    report = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(report, dict):
        raise ValueError("generated report is not a JSON object")
    generated = datetime.fromisoformat(str(report.get("generated_at", "")).replace("Z", "+00:00"))
    # Existing producers stamp whole seconds; permit that rounding only.
    if generated.tzinfo is None or not (
        started.replace(microsecond=0) <= generated <= finished
    ):
        raise ValueError("generated report timestamp is stale, future, or lacks timezone")
    return report


def validate_report(name: str, report: dict[str, Any], args: argparse.Namespace,
                    proof: dict[str, Any]) -> list[str]:
    failures = [str(item) for item in report.get("failures", [])]
    if report.get("passed") is not True:
        failures.append("generated report did not pass")

    def require(condition: bool, message: str) -> None:
        if not condition:
            failures.append(message)

    def same_path(value: Any, expected: Path) -> bool:
        return isinstance(value, str) and bool(value) and repo_path(value) == repo_path(expected)

    if name == "assemble_proof":
        require(report.get("manual_proof_valid") is True, "assembler did not validate the manual proof")
        require(same_path(report.get("run_manifest"), args.run_manifest), "assembler run manifest does not match")
        require(same_path(report.get("output_path"), args.proof_json), "assembler proof output does not match")
        require(
            same_path(report.get("observations"), args.observations) if args.observations
            else report.get("observations") is None,
            "assembler observations do not match",
        )
        require(set(report.get("passing_ids") or []) == set(manual_directinput_checklist.REQUIRED_IDS),
                "assembler did not report all five required passing targets")
        summary = report
    elif name == "battle_click_consumed":
        require(report.get("real_visible_click_consumed") is True, "battle click consumption is not proven")
        require(report.get("invalid_run_count") == 0, "battle report contains invalid runs")
        require(any(same_path(run.get("path"), args.battle_run_dir)
                    for run in report.get("runs", []) if isinstance(run, dict)),
                "battle report is not bound to the supplied run")
        return failures
    else:
        prefix = "manual_proof" if name == "manual_checklist" else "manual_input_proof"
        require(same_path(report.get(prefix), args.proof_json), "report manual proof path does not match")
        require(report.get(prefix + "_supplied") is True, "report did not receive manual proof")
        require(report.get(prefix + "_valid") is True, "report manual proof is invalid")
        require(report.get("allow_cdb_only_promotion") is False, "CDB-only promotion cannot replace manual proof")
        summary = report.get(prefix + "_summary") or {}
        if name == "manual_checklist":
            require(report.get("promotion_ready") is True, "manual checklist is not promotion-ready")
        else:
            require(report.get("decision") == "eligible_for_stable_promotion",
                    f"decision is {report.get('decision')!r}, not affirmative stable eligibility")
            require(report.get("stable_stage_should_change") is True, "decision does not authorize component promotion")
            require(report.get("promotion_override_manifest_supplied") is False,
                    "override promotion is outside this manual-proof sequence")
            stable = manual_directinput_checklist.CURRENT_STABLE_STAGE
            require(report.get("current_stable_stage") == stable, "decision protected stable stage does not match")
            expected_stage = stable + (
                "-rightbottomcompose" if name == "right_bottom_promotion" else "-castlecenter-all"
            )
            require((report.get("resolved_validation_stage") or report.get("validation_stage")) == expected_stage,
                    "decision component validation stage does not match")
            require(bool(manual_directinput_checklist.SHA256_RE.fullmatch(str(report.get("candidate_sha256", "")))),
                    "decision component candidate SHA-256 is missing or invalid")
            for target_id in COMPONENT_MANUAL_TARGETS[name]:
                targets = [item for item in proof.get("checked_items", [])
                           if isinstance(item, dict) and item.get("id") == target_id]
                require(len(targets) == 1, f"component proof requires exactly one target {target_id}")
                if len(targets) != 1:
                    continue
                target = targets[0]
                require(target.get("stage") == expected_stage, f"manual target {target_id} stage does not match component")
                target_sha = target.get("executable_sha256")
                require(
                    isinstance(target_sha, str)
                    and bool(manual_directinput_checklist.SHA256_RE.fullmatch(target_sha))
                    and target_sha.casefold() == str(report.get("candidate_sha256", "")).casefold(),
                    f"manual target {target_id} executable SHA-256 is missing or does not match decision candidate",
                )
                target_path = target.get("candidate_path")
                require(
                    isinstance(target_path, str)
                    and target_path.casefold().endswith(".exe")
                    and manual_directinput_checklist._is_same_or_under(
                        target_path, manual_directinput_checklist.EXPECTED_CANDIDATE_ROOT
                    ),
                    f"manual target {target_id} candidate_path must identify an isolated executable under C:\\ClashTests",
                )
    require(str(summary.get("executable_sha256", "")).casefold() == str(proof.get("executable_sha256", "")).casefold(),
            "report executable SHA-256 does not match the supplied manual proof")
    require(summary.get("checked_item_count") == len(manual_directinput_checklist.REQUIRED_IDS),
            "report does not contain all five checked targets")
    return failures


def run_component_sequence(args: argparse.Namespace, artifact_dir: Path, *, runner=None) -> dict[str, Any]:
    """Grade fresh component artifacts; stop before dependent steps on failure."""
    runner = runner or run_step
    artifact_dir.mkdir(parents=True, exist_ok=True)
    outputs = artifact_paths(artifact_dir)
    plan = plan_steps(args, artifact_dir)
    steps: list[dict[str, Any]] = []
    proof: dict[str, Any] = {}
    proof_digest = None
    for name, argv in plan:
        started = datetime.now(timezone.utc)
        report: dict[str, Any] = {}
        result: dict[str, Any] = {"name": name, "exit_code": None, "process_passed": False}
        failures: list[str] = []
        try:
            if outputs[name].exists():
                raise ValueError("output already exists; a fresh invocation artifact is required")
            if proof_digest and hashlib.sha256(repo_path(args.proof_json).read_bytes()).hexdigest() != proof_digest:
                raise ValueError("manual proof changed after assembly")
            result = runner(name, argv)
            result["process_passed"] = result.get("exit_code") == 0
            if not result["process_passed"]:
                failures.append(f"subprocess exited {result.get('exit_code')}")
            # Read even a failing tool's fresh report so its evidence/approval
            # failures are retained. Never continue to a dependent tool.
            report = read_fresh_report(outputs[name], started, datetime.now(timezone.utc))
            if name == "assemble_proof":
                proof = json.loads(repo_path(args.proof_json).read_text(encoding="utf-8-sig"))
                failures.extend(manual_directinput_checklist.validate_manual_proof_data(proof))
                proof_digest = hashlib.sha256(repo_path(args.proof_json).read_bytes()).hexdigest()
            elif hashlib.sha256(repo_path(args.proof_json).read_bytes()).hexdigest() != proof_digest:
                failures.append("manual proof changed during component evaluation")
            failures.extend(validate_report(name, report, args, proof))
        except (OSError, ValueError, TypeError, AttributeError) as exc:
            failures.append(str(exc))
        result.update({"passed": not failures, "artifact_json": str(outputs[name]),
                       "report": report, "failures": failures})
        steps.append(result)
        if failures:
            break
    component_ready = len(steps) == len(plan) and all(step["passed"] for step in steps)
    failures = [f"{step['name']}: {failure}" for step in steps for failure in step["failures"]]
    if args.update_checklist:
        failures.append("--update-checklist is blocked: whole-HD acceptance is not implemented; component eligibility cannot check release boxes")
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "runtime_policy": RUNTIME_POLICY,
        "evaluation_scope": "right_bottom_and_castle_component_eligibility",
        "run_manifest": str(args.run_manifest), "proof_json": str(args.proof_json),
        "manual_proof_sha256": proof_digest,
        "battle_run_dir": str(args.battle_run_dir) if args.battle_run_dir else None,
        "battle_evaluated": any(step["name"] == "battle_click_consumed" and step["passed"] for step in steps),
        "battle_candidate_identity_bound": False,
        "battle_evidence_scope": (
            "recorded command-click consumption only; the battle summary producer has no candidate SHA/stage "
            "and the five-target manual proof has no battle target, so this step cannot prove candidate eligibility"
        ),
        "passed": component_ready and not failures,
        "component_promotion_ready": component_ready,
        "component_candidate_identity_bound": component_ready,
        "promotion_ready": False,
        "whole_hd_acceptance_evaluated": False,
        "unimplemented_acceptance_requirements": WHOLE_HD_REQUIREMENTS,
        "stable_stage_should_change": False,
        "checklist_updated": None,
        "steps": steps,
        "skipped_steps": [name for name, _ in plan[len(steps):]],
        "failures": failures,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-manifest", type=Path, required=True, help="Run manifest from an approved VM run")
    parser.add_argument("--observations", type=Path, help="Optional operator observations JSON")
    parser.add_argument("--proof-json", type=Path, default=PROOF_JSON, help="Where to write/read the proof manifest")
    parser.add_argument("--battle-run-dir", type=Path, help="Battle visible-input run dir for the click-consumed gate")
    parser.add_argument("--update-checklist", action="store_true", help="Compatibility option; fails closed until whole-HD acceptance is implemented")
    parser.add_argument("--write-json", type=Path, default=DEFAULT_SUMMARY_JSON)
    parser.add_argument("--require-pass", action="store_true", help="Require the scoped component evaluation to pass; does not assert whole-HD readiness")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    artifact_dir = repo_path(args.write_json or DEFAULT_SUMMARY_JSON).parent / "complete-hd-promotion-artifacts" / uuid4().hex
    summary = run_component_sequence(args, artifact_dir)

    if args.write_json:
        summary_path = repo_path(args.write_json)
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    print(f"runtime-policy: {RUNTIME_POLICY}")
    for step in summary["steps"]:
        print(f"  {'PASS' if step['passed'] else 'FAIL'} {step['name']} (exit {step['exit_code']})")
    print(f"component-promotion-ready: {summary['component_promotion_ready']}")
    print("promotion-ready: False (whole-HD acceptance is not implemented)")
    if summary["failures"]:
        print(f"failures: {summary['failures']}")

    if not summary["passed"] and (args.require_pass or args.update_checklist):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
