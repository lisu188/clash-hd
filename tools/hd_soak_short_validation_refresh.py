#!/usr/bin/env python3
"""Refresh guard and triage artifacts for canonical short HD soak reports.

This is repo-only post-processing. It does not run the soak harness. If a
canonical short-step report exists, it writes that step's guard and triage
outputs from the short artifact manifest so the step-status report can consume
them automatically.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import hd_soak_failure_triage
import hd_soak_report
import hd_soak_short_artifact_manifest


RUNTIME_POLICY = (
    "repo-only short-soak validation refresh; does not launch Clash95, CDB, "
    "wrappers, PowerShell harnesses, or visible windows"
)
DEFAULT_MANIFEST_JSON = hd_soak_short_artifact_manifest.DEFAULT_JSON
DEFAULT_JSON = Path("captures/current/hd-soak-short-validation-refresh-current.json")
DEFAULT_MD = Path("captures/current/hd-soak-short-validation-refresh-current.md")


def status_text(passed: bool) -> str:
    return "PASS" if passed else "FAIL"


def load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="ascii")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="ascii")


def path_from_text(value: str | None) -> Path | None:
    if not value:
        return None
    return Path(value.replace("\\", "/"))


def report_matches_step(report: dict[str, Any], step: dict[str, Any]) -> bool:
    return (
        report.get("stage") == hd_soak_report.PROTECTED_STABLE_STAGE
        and report.get("tier") == step.get("tier")
        and report.get("route") == step.get("route")
    )


def refresh_step(step: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    paths = step.get("paths") or {}
    report_path = path_from_text(paths.get("report_json"))
    guard_json = path_from_text(paths.get("guard_json"))
    guard_md = path_from_text(paths.get("guard_markdown"))
    triage_json = path_from_text(paths.get("triage_json"))
    triage_md = path_from_text(paths.get("triage_markdown"))
    failures: list[str] = []

    record: dict[str, Any] = {
        "id": step.get("id"),
        "tier": step.get("tier"),
        "route": step.get("route"),
        "report": str(report_path) if report_path else None,
        "guard_json": str(guard_json) if guard_json else None,
        "triage_json": str(triage_json) if triage_json else None,
        "report_exists": bool(report_path and report_path.exists()),
        "guard_written": False,
        "triage_written": False,
        "status": "no_report",
    }
    if report_path is None:
        failures.append(f"{step.get('id')} has no report_json path")
        record["status"] = "invalid_manifest_paths"
        return record, failures
    if not report_path.exists():
        return record, failures
    if not all([guard_json, guard_md, triage_json, triage_md]):
        failures.append(f"{step.get('id')} is missing guard or triage output paths")
        record["status"] = "invalid_manifest_paths"
        return record, failures

    try:
        report = hd_soak_report.load_json(report_path)
    except (OSError, json.JSONDecodeError) as exc:
        failures.append(f"{step.get('id')} could not read canonical report {report_path}: {exc}")
        record["status"] = "unreadable_report"
        return record, failures

    if not report_matches_step(report, step):
        failures.append(f"{step.get('id')} canonical report does not match expected tier/route/stage")
        record["status"] = "report_mismatch"
        return record, failures

    evaluation = hd_soak_report.evaluate_report(report)
    evaluation["source_report"] = str(report_path)
    write_json(guard_json, evaluation)
    write_text(guard_md, hd_soak_report.to_markdown(evaluation))

    triage = hd_soak_failure_triage.build_triage(report, report_path)
    hd_soak_failure_triage.write_outputs(triage, triage_json, triage_md)

    record.update(
        {
            "guard_written": True,
            "triage_written": True,
            "status": "validated_pass" if evaluation.get("overall") else "validated_failed",
            "guard_overall": evaluation.get("overall"),
            "triage_classification": triage.get("classification"),
            "triage_passed": triage.get("passed"),
            "executed": report.get("executed"),
            "report_passed": report.get("passed"),
            "frame_sample_count": report.get("frame_sample_count"),
            "final_route_marker": report.get("final_route_marker"),
            "candidate_sha256": report.get("candidate_sha256"),
        }
    )
    return record, failures


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    manifest = load_json(args.manifest_json)
    failures: list[str] = []
    if manifest is None:
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "passed": False,
            "runtime_policy": RUNTIME_POLICY,
            "manifest": str(args.manifest_json),
            "status": "missing_manifest",
            "steps": [],
            "failures": [f"missing artifact manifest: {args.manifest_json}"],
        }
    if not manifest.get("passed"):
        failures.append("artifact manifest is not passing")

    steps: list[dict[str, Any]] = []
    for step in manifest.get("step_reports") or []:
        record, step_failures = refresh_step(step)
        steps.append(record)
        failures.extend(step_failures)

    report_count = sum(1 for step in steps if step.get("report_exists"))
    guard_written_count = sum(1 for step in steps if step.get("guard_written"))
    triage_written_count = sum(1 for step in steps if step.get("triage_written"))
    failed_runtime_count = sum(1 for step in steps if step.get("status") == "validated_failed")
    status = "pending_no_reports" if report_count == 0 else "validated_reports"
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "passed": not failures,
        "runtime_policy": RUNTIME_POLICY,
        "manifest": str(args.manifest_json),
        "status": status if not failures else "refresh_failed",
        "counts": {
            "steps": len(steps),
            "reports_found": report_count,
            "guards_written": guard_written_count,
            "triage_written": triage_written_count,
            "validated_failed": failed_runtime_count,
        },
        "steps": steps,
        "failures": failures,
    }


def to_markdown(report: dict[str, Any]) -> str:
    counts = report.get("counts") or {}
    lines = [
        "# HD Soak Short Validation Refresh",
        "",
        f"- Overall: {status_text(bool(report['passed']))}",
        f"- Generated: `{report['generated_at']}`",
        f"- Runtime policy: {report['runtime_policy']}",
        f"- Manifest: `{report.get('manifest')}`",
        f"- Status: `{report.get('status')}`",
        f"- Reports found: `{counts.get('reports_found')}/{counts.get('steps')}`",
        f"- Guards written: `{counts.get('guards_written')}`",
        f"- Triage written: `{counts.get('triage_written')}`",
        f"- Failed runtime reports classified: `{counts.get('validated_failed')}`",
        "",
        "## Steps",
        "",
    ]
    for step in report.get("steps") or []:
        lines.append(
            f"- `{step.get('id')}`: status=`{step.get('status')}` "
            f"report_exists=`{step.get('report_exists')}` "
            f"guard=`{step.get('guard_written')}` triage=`{step.get('triage_written')}`"
        )
    if report.get("failures"):
        lines.extend(["", "## Failures", ""])
        lines.extend(f"- {failure}" for failure in report["failures"])
    lines.append("")
    return "\n".join(lines)


def write_outputs(report: dict[str, Any], json_path: Path | None, md_path: Path | None) -> None:
    if json_path:
        write_json(json_path, report)
    if md_path:
        write_text(md_path, to_markdown(report))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest-json", type=Path, default=DEFAULT_MANIFEST_JSON)
    parser.add_argument("--write-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--write-markdown", "--write-md", dest="write_markdown", type=Path, default=DEFAULT_MD)
    parser.add_argument("--require-pass", action="store_true")
    args = parser.parse_args()

    report = build_report(args)
    write_outputs(report, args.write_json, args.write_markdown)
    print(f"overall: {status_text(bool(report['passed']))}")
    print(f"runtime-policy: {report['runtime_policy']}")
    print(f"status: {report.get('status')}")
    print(f"reports-found: {(report.get('counts') or {}).get('reports_found')}")
    if report["failures"]:
        print("failures:")
        for failure in report["failures"]:
            print(f"  - {failure}")
    if args.require_pass and not report["passed"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
