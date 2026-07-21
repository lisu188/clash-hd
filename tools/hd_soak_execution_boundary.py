#!/usr/bin/env python3
"""Probe that bad visible-runtime approval packets fail before side effects.

This is a negative harness check. It invokes scripts/smoke/run_hd_soak.ps1 with
invalid approval packets, a nonexistent input executable, and repository-local
temporary paths. Passing means the harness returned failure before creating the
candidate/output/report paths that would precede a visible runtime launch.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCRIPT = Path("scripts/smoke/run_hd_soak.ps1")
DEFAULT_JSON = Path("captures/current/hd-soak-execution-boundary-current.json")
DEFAULT_MD = Path("captures/current/hd-soak-execution-boundary-current.md")
DEFAULT_FIXTURE_ROOT = Path(".codex-loop/tmp-tests/hd-soak-execution-boundary")
RUNTIME_POLICY = (
    "repo-local negative harness probe; invokes PowerShell only with invalid "
    "visible-runtime approval and a nonexistent input executable, and must not "
    "launch Clash95, CDB, wrappers, or visible windows"
)
PROTECTED_STABLE_STAGE = (
    "gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-"
    "minimapright-dynvswitch"
)


@dataclass(frozen=True)
class BoundaryCase:
    name: str
    expected_phrase: str
    token: str | None = None
    expires_utc: str | None = None


Runner = Callable[..., subprocess.CompletedProcess[str]]


CASES = [
    BoundaryCase(
        name="missing_token",
        expected_phrase="requires -VisibleRuntimeApprovalToken",
        expires_utc="2999-01-01T00:00:00+00:00",
    ),
    BoundaryCase(
        name="missing_expiry",
        expected_phrase="requires -VisibleRuntimeApprovalExpiresUtc",
        token="0000000000000000",
    ),
    BoundaryCase(
        name="expired_packet",
        expected_phrase="Visible runtime approval expired",
        token="0000000000000000",
        expires_utc="2000-01-01T00:00:00+00:00",
    ),
    BoundaryCase(
        name="token_mismatch",
        expected_phrase="Visible runtime approval token does not match",
        token="0000000000000000",
        expires_utc="2999-01-01T00:00:00+00:00",
    ),
]


def status_text(passed: bool) -> str:
    return "PASS" if passed else "FAIL"


def repo_path(path: Path) -> Path:
    return path if path.is_absolute() else REPO_ROOT / path


def relative_or_absolute(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def build_command(script: Path, root: Path, case: BoundaryCase) -> list[str]:
    case_root = root / case.name
    workdir = case_root / "workdir"
    candidate_dir = case_root / "candidate"
    output_root = case_root / "output"
    report_json = case_root / "report.json"
    report_md = case_root / "report.md"
    input_exe = case_root / "missing-clash95.exe"
    workdir.mkdir(parents=True, exist_ok=True)
    command = [
        "powershell.exe",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(script),
        "-InputExe",
        str(input_exe),
        "-WorkDir",
        str(workdir),
        "-Stage",
        PROTECTED_STABLE_STAGE,
        "-Tier",
        "short2",
        "-Route",
        "menu-idle",
        "-CandidateDir",
        str(candidate_dir),
        "-CandidateName",
        "boundary.exe",
        "-OutputRoot",
        str(output_root),
        "-ReportJson",
        str(report_json),
        "-ReportMarkdown",
        str(report_md),
        "-IntroSkipClickMode",
        "postmessage",
        "-IntroSkipClicks",
        "8",
        "-SkipPulses",
        "4",
        "-SampleIntervalSec",
        "15",
        "-MaxInputDriftPx",
        "1",
        "-MinNonblackPercent",
        "10",
        "-MinUniqueSampleColors",
        "8",
        "-MaxArtifactMB",
        "250",
        "-MaxWorkingSetGrowthMB",
        "64",
        "-MaxPrivateMemoryGrowthMB",
        "64",
        "-MaxHandleGrowth",
        "128",
        "-AllowRepoCandidateDir",
        "-Execute",
        "-AllowVisibleRuntime",
        "-RequirePass",
        "-Json",
    ]
    if case.expires_utc is not None:
        command.extend(["-VisibleRuntimeApprovalExpiresUtc", case.expires_utc])
    if case.token is not None:
        command.extend(["-VisibleRuntimeApprovalToken", case.token])
    return command


def side_effect_paths(root: Path, case: BoundaryCase) -> dict[str, Path]:
    case_root = root / case.name
    return {
        "candidate_dir": case_root / "candidate",
        "candidate_exe": case_root / "candidate" / "boundary.exe",
        "output_root": case_root / "output",
        "report_json": case_root / "report.json",
        "report_markdown": case_root / "report.md",
    }


def run_case(script: Path, root: Path, case: BoundaryCase, runner: Runner = subprocess.run) -> dict[str, Any]:
    command = build_command(script, root, case)
    paths = side_effect_paths(root, case)
    try:
        result = runner(
            command,
            cwd=REPO_ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    except FileNotFoundError as exc:
        # No PowerShell on this platform: the refusal contract cannot be
        # exercised, so the case fails closed with an explicit reason instead
        # of crashing the whole evidence refresh. Only the Windows rig can turn
        # this check green.
        return {
            "name": case.name,
            "passed": False,
            "exit_code": None,
            "expected_phrase": case.expected_phrase,
            "expected_phrase_seen": False,
            "side_effects": {name: path.exists() for name, path in paths.items()},
            "side_effect_paths": {name: relative_or_absolute(path) for name, path in paths.items()},
            "stdout_tail": "",
            "stderr_tail": f"boundary probe runner unavailable on this platform: {exc}",
            "command": " ".join(command),
        }
    combined = f"{result.stdout}\n{result.stderr}"
    side_effects = {name: path.exists() for name, path in paths.items()}
    passed = (
        result.returncode != 0
        and case.expected_phrase in combined
        and not any(side_effects.values())
    )
    return {
        "name": case.name,
        "passed": passed,
        "exit_code": result.returncode,
        "expected_phrase": case.expected_phrase,
        "expected_phrase_seen": case.expected_phrase in combined,
        "side_effects": side_effects,
        "side_effect_paths": {name: relative_or_absolute(path) for name, path in paths.items()},
        "stdout_tail": result.stdout[-1200:],
        "stderr_tail": result.stderr[-1200:],
        "command": " ".join(command),
    }


def build_report(args: argparse.Namespace, runner: Runner = subprocess.run) -> dict[str, Any]:
    script = repo_path(args.script)
    fixture_root = repo_path(args.fixture_root)
    if args.clean_fixture and fixture_root.exists():
        shutil.rmtree(fixture_root)
    fixture_root.mkdir(parents=True, exist_ok=True)
    failures: list[str] = []
    if not script.exists():
        failures.append(f"harness script missing: {script}")
        case_results: list[dict[str, Any]] = []
    else:
        case_results = [run_case(script, fixture_root, case, runner=runner) for case in CASES]
        for result in case_results:
            if not result["passed"]:
                failures.append(
                    f"{result['name']} did not fail closed before side effects"
                )
    if args.clean_fixture and fixture_root.exists():
        shutil.rmtree(fixture_root)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "passed": not failures,
        "runtime_policy": RUNTIME_POLICY,
        "guard_policy": (
            "invalid visible-runtime approval packets must fail before output, "
            "candidate, report, patch, or launch side effects"
        ),
        "script": relative_or_absolute(script),
        "fixture_root": relative_or_absolute(fixture_root),
        "case_count": len(case_results),
        "cases": case_results,
        "failures": failures,
    }


def to_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# HD Soak Execution Boundary",
        "",
        f"- Overall: {status_text(bool(report.get('passed')))}",
        f"- Generated: `{report.get('generated_at')}`",
        f"- Runtime policy: {report.get('runtime_policy')}",
        f"- Guard policy: {report.get('guard_policy')}",
        f"- Script: `{report.get('script')}`",
        f"- Cases: `{report.get('case_count')}`",
        "",
        "## Cases",
        "",
    ]
    for case in report.get("cases") or []:
        side_effects = case.get("side_effects") or {}
        active = [name for name, exists in side_effects.items() if exists]
        lines.extend(
            [
                f"- `{case.get('name')}`: {status_text(bool(case.get('passed')))} "
                f"exit=`{case.get('exit_code')}` phrase=`{case.get('expected_phrase_seen')}` "
                f"side_effects=`{','.join(active) if active else 'none'}`",
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
    parser.add_argument("--script", type=Path, default=DEFAULT_SCRIPT)
    parser.add_argument("--fixture-root", type=Path, default=DEFAULT_FIXTURE_ROOT)
    parser.add_argument("--write-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--write-markdown", "--write-md", dest="write_markdown", type=Path, default=DEFAULT_MD)
    parser.add_argument("--no-clean-fixture", dest="clean_fixture", action="store_false")
    parser.set_defaults(clean_fixture=True)
    parser.add_argument("--require-pass", action="store_true")
    args = parser.parse_args()

    report = build_report(args)
    write_outputs(report, args.write_json, args.write_markdown)
    print(f"overall: {status_text(bool(report['passed']))}")
    print(f"runtime-policy: {report['runtime_policy']}")
    for case in report.get("cases") or []:
        print(f"{case['name']}: {status_text(bool(case['passed']))}")
    if report["failures"]:
        print("failures:")
        for failure in report["failures"]:
            print(f"  - {failure}")
    return 1 if args.require_pass and not report["passed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
