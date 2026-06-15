#!/usr/bin/env python3
"""Build the canonical artifact manifest for short-tier HD soak steps.

This is a repo-only command manifest. It does not run the soak harness. The
purpose is to give each short ladder step a durable report path so evidence can
accumulate instead of overwriting the generic short-soak report.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import hd_soak_short_tier_ladder


RUNTIME_POLICY = (
    "repo-only short-soak artifact manifest; does not launch Clash95, CDB, "
    "wrappers, PowerShell harnesses, or visible windows"
)
DEFAULT_JSON = Path("captures/current/hd-soak-short-artifact-manifest-current.json")
DEFAULT_MD = Path("captures/current/hd-soak-short-artifact-manifest-current.md")
DEFAULT_LEGACY_REPORT_JSON = Path("captures/current/hd-soak-short-current.json")
DEFAULT_LEGACY_REPORT_MD = Path("captures/current/hd-soak-short-current.md")


def status_text(passed: bool) -> str:
    return "PASS" if passed else "FAIL"


def path_text(path: Path) -> str:
    return str(path).replace("/", "\\")


def step_slug(step: dict[str, Any]) -> str:
    tier = str(step["tier"]).replace("_", "-")
    route = str(step["route"]).replace("_", "-")
    return f"{tier}-{route}"


def canonical_paths(step: dict[str, Any]) -> dict[str, str]:
    slug = step_slug(step)
    return {
        "report_json": path_text(Path("captures/current") / f"hd-soak-{slug}-current.json"),
        "report_markdown": path_text(Path("captures/current") / f"hd-soak-{slug}-current.md"),
        "guard_json": path_text(Path("captures/current") / f"hd-soak-{slug}-guard-current.json"),
        "guard_markdown": path_text(Path("captures/current") / f"hd-soak-{slug}-guard-current.md"),
        "triage_json": path_text(Path("captures/current") / f"hd-soak-{slug}-triage-current.json"),
        "triage_markdown": path_text(Path("captures/current") / f"hd-soak-{slug}-triage-current.md"),
    }


def harness_command(step: dict[str, Any], paths: dict[str, str], *, execute: bool) -> str:
    parts = [
        "powershell.exe",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        r".\scripts\smoke\run_hd_soak.ps1",
        "-Tier",
        str(step["tier"]),
        "-Route",
        str(step["route"]),
        "-ReportJson",
        paths["report_json"],
        "-ReportMarkdown",
        paths["report_markdown"],
    ]
    if execute:
        parts.extend(["-Execute", "-AllowVisibleRuntime", "-RequirePass"])
    parts.append("-Json")
    return " ".join(parts)


def guard_command(paths: dict[str, str], *, require_pass: bool = True) -> str:
    parts = [
        "python",
        r"tools\hd_soak_report.py",
        paths["report_json"],
        "--write-json",
        paths["guard_json"],
        "--write-markdown",
        paths["guard_markdown"],
    ]
    if require_pass:
        parts.append("--require-pass")
    return " ".join(parts)


def triage_command(paths: dict[str, str]) -> str:
    return (
        "python "
        r"tools\hd_soak_failure_triage.py "
        f"{paths['report_json']} "
        f"--write-json {paths['triage_json']} "
        f"--write-markdown {paths['triage_markdown']}"
    )


def is_current_artifact_path(value: str) -> bool:
    normalized = value.replace("/", "\\")
    return normalized.startswith("captures\\current\\")


def build_step_records(steps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for index, step in enumerate(steps, start=1):
        paths = canonical_paths(step)
        report_path = Path(paths["report_json"])
        record = {
            "index": index,
            "id": step["id"],
            "tier": step["tier"],
            "route": step["route"],
            "duration_sec": step["duration_sec"],
            "prerequisites": step["prerequisites"],
            "paths": paths,
            "report_exists": report_path.exists(),
            "safe_dry_run_command": harness_command(step, paths, execute=False),
            "approval_gated_runtime_command": harness_command(step, paths, execute=True),
            "guard_command": guard_command(paths),
            "triage_command": triage_command(paths),
            "requires_visible_runtime": True,
            "requires_explicit_user_approval": True,
            "writes_outside_repo": [r"C:\ClashTests\hd-soak", r"C:\ClashCaptures\hd-soak"],
            "must_not_modify": [r"C:\Clash\clash95.exe"],
            "stable_stage_should_change": False,
            "right_bottom_promotion_blocked": True,
        }
        records.append(record)
    return records


def validate_records(records: list[dict[str, Any]]) -> list[str]:
    failures: list[str] = []
    path_values: list[str] = []
    for record in records:
        paths = record["paths"]
        for key, value in paths.items():
            if not is_current_artifact_path(value):
                failures.append(f"{record['id']} {key} is outside captures/current: {value}")
            path_values.append(value.lower())
        command = record["approval_gated_runtime_command"]
        if "-Execute -AllowVisibleRuntime -RequirePass" not in command:
            failures.append(f"{record['id']} runtime command is not visibly approval-gated")
        if "-ReportJson" not in command or "-ReportMarkdown" not in command:
            failures.append(f"{record['id']} runtime command does not pin report outputs")
        if "-Execute" in record["safe_dry_run_command"]:
            failures.append(f"{record['id']} safe dry-run command includes -Execute")
        if record["stable_stage_should_change"] is not False:
            failures.append(f"{record['id']} would change stable stage")
        if record["right_bottom_promotion_blocked"] is not True:
            failures.append(f"{record['id']} does not keep right-bottom promotion blocked")
    duplicates = sorted({value for value in path_values if path_values.count(value) > 1})
    for duplicate in duplicates:
        failures.append(f"duplicate canonical artifact path: {duplicate}")
    return failures


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    records = build_step_records(hd_soak_short_tier_ladder.SHORT_LADDER_STEPS)
    failures = validate_records(records)
    legacy_json = args.legacy_report_json
    legacy_md = args.legacy_report_md
    existing_step_reports = [record for record in records if record["report_exists"]]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "passed": not failures,
        "runtime_policy": RUNTIME_POLICY,
        "protected_stable_stage": hd_soak_short_tier_ladder.PROTECTED_STABLE_STAGE,
        "legacy_default_report": {
            "json": path_text(legacy_json),
            "markdown": path_text(legacy_md),
            "json_exists": legacy_json.exists(),
            "markdown_exists": legacy_md.exists(),
            "purpose": "compatibility report used by the existing short-soak guard",
        },
        "step_count": len(records),
        "existing_step_report_count": len(existing_step_reports),
        "step_reports": records,
        "locks": {
            "stable_stage_should_change": False,
            "right_bottom_promotion_blocked": True,
            "long_tiers_locked_until_step_reports_pass": True,
            "future_lanes_locked_until_step_reports_pass": True,
        },
        "failures": failures,
    }


def to_markdown(report: dict[str, Any]) -> str:
    legacy = report["legacy_default_report"]
    lines = [
        "# HD Soak Short Artifact Manifest",
        "",
        f"- Overall: {status_text(bool(report['passed']))}",
        f"- Generated: `{report['generated_at']}`",
        f"- Runtime policy: {report['runtime_policy']}",
        f"- Protected stable stage: `{report['protected_stable_stage']}`",
        f"- Step reports present: `{report['existing_step_report_count']}/{report['step_count']}`",
        f"- Legacy default report: `{legacy['json']}` exists=`{legacy['json_exists']}`",
        f"- Stable stage should change: `{report['locks']['stable_stage_should_change']}`",
        f"- Right-bottom promotion blocked: `{report['locks']['right_bottom_promotion_blocked']}`",
        "",
        "## Step Reports",
        "",
    ]
    for record in report["step_reports"]:
        lines.append(
            f"- `{record['id']}`: report=`{record['paths']['report_json']}` "
            f"exists=`{record['report_exists']}`"
        )
    lines.extend(["", "## Current First-Step Command", ""])
    first = report["step_reports"][0]
    lines.extend(
        [
            "Safe dry-run command:",
            "",
            "```powershell",
            first["safe_dry_run_command"],
            "```",
            "",
            "Approval-gated runtime command:",
            "",
            "```powershell",
            first["approval_gated_runtime_command"],
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
    parser.add_argument("--legacy-report-json", type=Path, default=DEFAULT_LEGACY_REPORT_JSON)
    parser.add_argument("--legacy-report-md", type=Path, default=DEFAULT_LEGACY_REPORT_MD)
    parser.add_argument("--write-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--write-markdown", "--write-md", dest="write_markdown", type=Path, default=DEFAULT_MD)
    parser.add_argument("--require-pass", action="store_true")
    args = parser.parse_args()

    report = build_report(args)
    write_outputs(report, args.write_json, args.write_markdown)
    print(f"overall: {status_text(bool(report['passed']))}")
    print(f"runtime-policy: {report['runtime_policy']}")
    print(f"step-reports-present: {report['existing_step_report_count']}/{report['step_count']}")
    if report["failures"]:
        print("failures:")
        for failure in report["failures"]:
            print(f"  - {failure}")
    if args.require_pass and not report["passed"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
