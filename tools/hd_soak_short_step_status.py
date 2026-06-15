#!/usr/bin/env python3
"""Report per-step status for the short HD soak ladder.

This repo-only status report reads the canonical short-soak artifact manifest
and optional per-step report/guard/triage files. It does not run the game. It
keeps the ladder honest after a runtime run by requiring guard output for any
canonical report, and triage output for any failed canonical report.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROTECTED_STABLE_STAGE = (
    "gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-"
    "minimapright-dynvswitch"
)
RUNTIME_POLICY = (
    "repo-only short-soak step status; does not launch Clash95, CDB, wrappers, "
    "PowerShell harnesses, or visible windows"
)
DEFAULT_MANIFEST_JSON = Path("captures/current/hd-soak-short-artifact-manifest-current.json")
DEFAULT_LEGACY_REPORT_JSON = Path("captures/current/hd-soak-short-current.json")
DEFAULT_JSON = Path("captures/current/hd-soak-short-step-status-current.json")
DEFAULT_MD = Path("captures/current/hd-soak-short-step-status-current.md")


def status_text(passed: bool) -> str:
    return "PASS" if passed else "FAIL"


def load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8-sig"))


def matches_step(report: dict[str, Any] | None, step: dict[str, Any]) -> bool:
    if not report:
        return False
    return (
        report.get("stage") == PROTECTED_STABLE_STAGE
        and report.get("tier") == step.get("tier")
        and report.get("route") == step.get("route")
    )


def is_pending_approval(report: dict[str, Any] | None) -> bool:
    if not report:
        return False
    failures = "\n".join(str(row).lower() for row in report.get("failures") or [])
    return report.get("executed") is not True and (
        "approval" in failures or bool(report.get("execution_blocked_reason"))
    )


def step_status(
    step: dict[str, Any],
    *,
    prerequisites_passed: bool,
    legacy_report: dict[str, Any] | None,
) -> tuple[str, bool, list[str], dict[str, Any]]:
    paths = step.get("paths") or {}
    report_path = Path(paths.get("report_json") or "")
    guard_path = Path(paths.get("guard_json") or "")
    triage_path = Path(paths.get("triage_json") or "")
    report = load_json(report_path) if paths.get("report_json") else None
    guard = load_json(guard_path) if paths.get("guard_json") else None
    triage = load_json(triage_path) if paths.get("triage_json") else None
    failures: list[str] = []

    if report is None:
        legacy_matches = matches_step(legacy_report, step)
        if legacy_matches and is_pending_approval(legacy_report):
            return (
                "pending_approval_legacy_compat",
                False,
                failures,
                {
                    "canonical_report_present": False,
                    "legacy_report_matches": True,
                    "legacy_report_pending_approval": True,
                    "next_command": step.get("approval_gated_runtime_command"),
                },
            )
        if not prerequisites_passed:
            return (
                "locked_by_prerequisite",
                False,
                failures,
                {
                    "canonical_report_present": False,
                    "legacy_report_matches": legacy_matches,
                    "next_command": None,
                },
            )
        return (
            "missing_pending_approval",
            False,
            failures,
            {
                "canonical_report_present": False,
                "legacy_report_matches": legacy_matches,
                "next_command": step.get("approval_gated_runtime_command"),
            },
        )

    if not matches_step(report, step):
        failures.append(f"{step['id']} canonical report does not match expected tier/route/stage")
        return (
            "invalid_report_mismatch",
            False,
            failures,
            {
                "canonical_report_present": True,
                "guard_present": guard is not None,
                "triage_present": triage is not None,
            },
        )

    if guard is None:
        failures.append(f"{step['id']} has a canonical report but no guard output: {guard_path}")
        return (
            "needs_guard",
            False,
            failures,
            {
                "canonical_report_present": True,
                "guard_present": False,
                "triage_present": triage is not None,
                "next_command": step.get("guard_command"),
            },
        )

    guard_passed = bool(guard.get("overall"))
    if report.get("passed") is True and guard_passed:
        return (
            "pass",
            True,
            failures,
            {
                "canonical_report_present": True,
                "guard_present": True,
                "triage_present": triage is not None,
                "guard_overall": guard.get("overall"),
                "executed": report.get("executed"),
                "frame_sample_count": report.get("frame_sample_count"),
                "final_route_marker": report.get("final_route_marker"),
                "candidate_sha256": report.get("candidate_sha256"),
            },
        )

    if triage is None:
        failures.append(f"{step['id']} failed or unproven report has no triage output: {triage_path}")
        return (
            "failed_needs_triage",
            False,
            failures,
            {
                "canonical_report_present": True,
                "guard_present": True,
                "guard_overall": guard.get("overall"),
                "triage_present": False,
                "next_command": step.get("triage_command"),
            },
        )

    return (
        f"failed_classified_{triage.get('classification')}",
        False,
        failures,
        {
            "canonical_report_present": True,
            "guard_present": True,
            "guard_overall": guard.get("overall"),
            "triage_present": True,
            "triage_passed": triage.get("passed"),
            "classification": triage.get("classification"),
            "next_probe": triage.get("next_probe"),
            "frame_sample_count": report.get("frame_sample_count"),
            "final_route_marker": report.get("final_route_marker"),
            "candidate_sha256": report.get("candidate_sha256"),
        },
    )


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    manifest = load_json(args.manifest_json)
    legacy_report = load_json(args.legacy_report_json)
    failures: list[str] = []
    if manifest is None:
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "passed": False,
            "runtime_policy": RUNTIME_POLICY,
            "manifest": str(args.manifest_json),
            "failures": [f"missing artifact manifest: {args.manifest_json}"],
        }
    if not manifest.get("passed"):
        failures.append("artifact manifest is not passing")

    passed_by_id: dict[str, bool] = {}
    steps: list[dict[str, Any]] = []
    for step in manifest.get("step_reports") or []:
        prereqs = [str(value) for value in step.get("prerequisites") or []]
        prereqs_passed = all(passed_by_id.get(prereq) for prereq in prereqs)
        status, passed, step_failures, summary = step_status(
            step,
            prerequisites_passed=prereqs_passed,
            legacy_report=legacy_report,
        )
        failures.extend(step_failures)
        record = {
            "id": step.get("id"),
            "index": step.get("index"),
            "tier": step.get("tier"),
            "route": step.get("route"),
            "duration_sec": step.get("duration_sec"),
            "prerequisites": prereqs,
            "prerequisites_passed": prereqs_passed,
            "status": status,
            "passed": passed,
            "paths": step.get("paths"),
            "summary": summary,
            "safe_dry_run_command": step.get("safe_dry_run_command"),
            "approval_gated_runtime_command": step.get("approval_gated_runtime_command"),
        }
        passed_by_id[str(step.get("id"))] = bool(passed)
        steps.append(record)

    current_step = next((step for step in steps if not step.get("passed")), None)
    counts = {
        "total": len(steps),
        "passed": sum(1 for step in steps if step.get("passed")),
        "pending_or_missing": sum(
            1
            for step in steps
            if str(step.get("status") or "").startswith(("pending", "missing"))
        ),
        "locked": sum(1 for step in steps if step.get("status") == "locked_by_prerequisite"),
        "failed_or_invalid": sum(
            1
            for step in steps
            if str(step.get("status") or "").startswith(("failed", "invalid", "needs"))
        ),
    }
    ladder_complete = bool(steps) and counts["passed"] == counts["total"]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "passed": not failures,
        "runtime_policy": RUNTIME_POLICY,
        "manifest": str(args.manifest_json),
        "legacy_report": str(args.legacy_report_json),
        "protected_stable_stage": PROTECTED_STABLE_STAGE,
        "ladder_complete": ladder_complete,
        "counts": counts,
        "current_step": None
        if current_step is None
        else {
            "id": current_step.get("id"),
            "tier": current_step.get("tier"),
            "route": current_step.get("route"),
            "status": current_step.get("status"),
            "next_command": (current_step.get("summary") or {}).get("next_command"),
        },
        "steps": steps,
        "locks": {
            "stable_stage_should_change": False,
            "right_bottom_promotion_blocked": True,
            "long_tiers_locked": not ladder_complete,
            "future_lanes_locked": True,
        },
        "failures": failures,
    }


def to_markdown(report: dict[str, Any]) -> str:
    current = report.get("current_step") or {}
    lines = [
        "# HD Soak Short-Step Status",
        "",
        f"- Overall: {status_text(bool(report['passed']))}",
        f"- Generated: `{report['generated_at']}`",
        f"- Runtime policy: {report['runtime_policy']}",
        f"- Manifest: `{report.get('manifest')}`",
        f"- Ladder complete: `{report.get('ladder_complete')}`",
        f"- Current step: `{current.get('id') or 'none'}` status=`{current.get('status')}`",
        f"- Passed steps: `{report.get('counts', {}).get('passed')}/{report.get('counts', {}).get('total')}`",
        f"- Long tiers locked: `{report.get('locks', {}).get('long_tiers_locked')}`",
        f"- Future lanes locked: `{report.get('locks', {}).get('future_lanes_locked')}`",
        "",
        "## Steps",
        "",
    ]
    for step in report.get("steps") or []:
        lines.append(
            f"- `{step['id']}`: tier=`{step['tier']}` route=`{step['route']}` "
            f"status=`{step['status']}` passed=`{step['passed']}`"
        )
    if current.get("next_command"):
        lines.extend(
            [
                "",
                "## Current Next Command",
                "",
                "```powershell",
                current["next_command"],
                "```",
            ]
        )
    if report.get("failures"):
        lines.extend(["", "## Failures", ""])
        lines.extend(f"- {failure}" for failure in report["failures"])
    lines.append("")
    return "\n".join(lines)


def write_outputs(report: dict[str, Any], json_path: Path | None, md_path: Path | None) -> None:
    if json_path:
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(report, indent=2) + "\n", encoding="ascii")
    if md_path:
        md_path.parent.mkdir(parents=True, exist_ok=True)
        md_path.write_text(to_markdown(report), encoding="ascii")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest-json", type=Path, default=DEFAULT_MANIFEST_JSON)
    parser.add_argument("--legacy-report-json", type=Path, default=DEFAULT_LEGACY_REPORT_JSON)
    parser.add_argument("--write-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--write-markdown", "--write-md", dest="write_markdown", type=Path, default=DEFAULT_MD)
    parser.add_argument("--require-pass", action="store_true")
    args = parser.parse_args()

    report = build_report(args)
    write_outputs(report, args.write_json, args.write_markdown)
    print(f"overall: {status_text(bool(report['passed']))}")
    print(f"runtime-policy: {report['runtime_policy']}")
    print(f"ladder-complete: {report.get('ladder_complete')}")
    current = report.get("current_step") or {}
    if current:
        print(f"current-step: {current.get('id')} ({current.get('status')})")
    if report["failures"]:
        print("failures:")
        for failure in report["failures"]:
            print(f"  - {failure}")
    if args.require_pass and not report["passed"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
