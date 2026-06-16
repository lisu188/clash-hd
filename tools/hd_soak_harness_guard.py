#!/usr/bin/env python3
"""Validate the opt-in HD soak harness source policy.

This is a repo-only source guard. It reads scripts/smoke/run_hd_soak.ps1 and
does not launch Clash95, CDB, wrappers, PowerShell, or visible windows.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_SCRIPT = Path("scripts/smoke/run_hd_soak.ps1")
DEFAULT_JSON = Path("captures/current/hd-soak-harness-guard-current.json")
DEFAULT_MD = Path("captures/current/hd-soak-harness-guard-current.md")
RUNTIME_POLICY = (
    "repo-only source inspection; does not launch Clash95, CDB, wrappers, "
    "PowerShell harnesses, or visible windows"
)
PROTECTED_STABLE_STAGE = (
    "gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-"
    "minimapright-dynvswitch"
)


def status_text(passed: bool) -> str:
    return "PASS" if passed else "FAIL"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig", errors="replace")


def param_default(text: str, name: str) -> str | None:
    pattern = re.compile(
        rf"\[string\]\${re.escape(name)}\s*=\s*(['\"])(?P<value>.*?)\1",
        re.IGNORECASE | re.DOTALL,
    )
    match = pattern.search(text)
    return match.group("value") if match else None


def contains_all(text: str, values: list[str]) -> bool:
    lower = text.lower()
    return all(value.lower() in lower for value in values)


def line_number(text: str, pattern: str) -> int | None:
    regex = re.compile(pattern, re.IGNORECASE)
    for index, line in enumerate(text.splitlines(), start=1):
        if regex.search(line):
            return index
    return None


def assignment_array_block(text: str, name: str) -> str:
    pattern = re.compile(
        rf"\${re.escape(name)}\s*=\s*@\((?P<body>.*?)\)\s*-join\s+['\"]\s+['\"]",
        re.IGNORECASE | re.DOTALL,
    )
    match = pattern.search(text)
    return match.group("body") if match else ""


def check_record(passed: bool, summary: dict[str, Any], failures: list[str] | None = None) -> dict[str, Any]:
    return {"passed": passed, "summary": summary, "failures": failures or []}


def build_guard(script: Path = DEFAULT_SCRIPT) -> dict[str, Any]:
    failures: list[str] = []
    checks: dict[str, Any] = {}
    script_path = Path(script)
    if not script_path.exists():
        failures.append(f"script does not exist: {script_path}")
        return {
            "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
            "passed": False,
            "runtime_policy": RUNTIME_POLICY,
            "guard_policy": "HD soak harness must stay opt-in, protected-stage, non-promoting, and artifact-safe",
            "script": str(script_path),
            "checks": {},
            "failures": failures,
        }

    text = read_text(script_path)

    default_expectations = {
        "CandidateDir": r"C:\ClashTests\hd-soak",
        "OutputRoot": r"C:\ClashCaptures\hd-soak",
        "ReportJson": r"captures\current\hd-soak-short-current.json",
        "ReportMarkdown": r"captures\current\hd-soak-short-current.md",
        "Stage": PROTECTED_STABLE_STAGE,
    }
    default_failures = []
    observed_defaults = {name: param_default(text, name) for name in default_expectations}
    for name, expected in default_expectations.items():
        if observed_defaults[name] != expected:
            default_failures.append(f"{name} default is {observed_defaults[name]!r}, expected {expected!r}")
    checks["safe_defaults"] = check_record(not default_failures, observed_defaults, default_failures)

    stable_literal = re.search(r"\$StableStage\s*=\s*['\"](?P<stage>[^'\"]+)['\"]", text, re.IGNORECASE)
    stable_stage = stable_literal.group("stage") if stable_literal else None
    stable_failures = []
    if stable_stage != PROTECTED_STABLE_STAGE:
        stable_failures.append(f"StableStage is {stable_stage!r}, expected protected stage")
    if "stable_stage_should_change = $false" not in text.lower():
        stable_failures.append("report/plan does not keep stable_stage_should_change false")
    checks["protected_stage_boundary"] = check_record(
        not stable_failures,
        {"stable_stage": stable_stage, "protected_stage": PROTECTED_STABLE_STAGE},
        stable_failures,
    )

    tier_failures = []
    tier_values = ["short2", "short10", "short30", "custom"]
    if not contains_all(text, tier_values):
        tier_failures.append("tier ValidateSet is missing one or more short/custom tiers")
    for tier, duration in {"short2": "120", "short10": "600", "short30": "1800"}.items():
        if not re.search(rf"['\"]?{tier}['\"]?\s*\{{\s*return\s+{duration}\s*\}}", text, re.IGNORECASE):
            tier_failures.append(f"{tier} duration is not {duration} seconds")
    if "Use -DurationSec with -Tier custom" not in text:
        tier_failures.append("custom tier does not require -DurationSec")
    checks["short_tiers"] = check_record(
        not tier_failures,
        {"required_tiers": tier_values, "durations_sec": {"short2": 120, "short10": 600, "short30": 1800}},
        tier_failures,
    )

    route_failures = []
    route_values = ["menu-idle", "map-idle", "map-pan", "custom"]
    if not contains_all(text, route_values):
        route_failures.append("route ValidateSet is missing one or more required routes")
    for marker in ["load-button", "load-slot0", "confirm-load", "pan-path"]:
        if marker not in text:
            route_failures.append(f"route marker is missing: {marker}")
    checks["short_routes"] = check_record(
        not route_failures,
        {"required_routes": route_values, "required_markers": ["load-button", "load-slot0", "confirm-load", "pan-path"]},
        route_failures,
    )

    approval_failures = []
    execute_line = line_number(text, r"\[switch\]\$Execute\b")
    allow_line = line_number(text, r"\[switch\]\$AllowVisibleRuntime\b")
    guard_line = line_number(text, r"if\s*\(\s*-not\s+\$AllowVisibleRuntime\s*\)")
    dry_run_line = line_number(text, r"if\s*\(\s*-not\s+\$Execute\s*\)")
    if execute_line is None:
        approval_failures.append("missing -Execute switch")
    if allow_line is None:
        approval_failures.append("missing -AllowVisibleRuntime switch")
    if guard_line is None:
        approval_failures.append("missing execution-time AllowVisibleRuntime guard")
    if dry_run_line is None:
        approval_failures.append("missing dry-run branch")
    if "explicit user approval" not in text.lower():
        approval_failures.append("missing explicit user approval phrase")
    if "-Execute" not in text or "-AllowVisibleRuntime" not in text:
        approval_failures.append("dry-run plan does not show explicit execute/visible flags")
    execute_command_block = assignment_array_block(text, "executeCommand")
    execute_command_fragments = ["-Execute", "-AllowVisibleRuntime", "-RequirePass", "-Json"]
    if not execute_command_block:
        approval_failures.append("dry-run execute command block is missing")
    for fragment in execute_command_fragments:
        if fragment not in execute_command_block:
            approval_failures.append(f"dry-run execute command does not include {fragment}")
    checks["visible_runtime_opt_in"] = check_record(
        not approval_failures,
        {
            "execute_switch_line": execute_line,
            "allow_visible_runtime_switch_line": allow_line,
            "dry_run_branch_line": dry_run_line,
            "runtime_guard_line": guard_line,
            "execute_command_fragments": execute_command_fragments,
        },
        approval_failures,
    )

    artifact_failures = []
    if "Refusing candidate output inside repository by default" not in text:
        artifact_failures.append("candidate-dir repo refusal is missing")
    if "Test-IsUnderPath $CandidateDirFull $RepoRoot" not in text:
        artifact_failures.append("candidate-dir repo containment check is missing")
    if "raw PNG frames and per-step logs stay outside the repository by default" not in text:
        artifact_failures.append("raw artifact outside-repo policy text is missing")
    if "MaxArtifactMB" not in text or "artifact size exceeded" not in text:
        artifact_failures.append("artifact budget check is missing")
    checks["artifact_policy"] = check_record(
        not artifact_failures,
        {"candidate_dir_default": observed_defaults.get("CandidateDir"), "output_root_default": observed_defaults.get("OutputRoot")},
        artifact_failures,
    )

    patch_failures = []
    for marker in ["patch_clash95_hd.py", "patch_stage_report.py", "--require-current-hd-map"]:
        if marker not in text:
            patch_failures.append(f"patch verification marker is missing: {marker}")
    if "$Stage -eq $StableStage" not in text:
        patch_failures.append("current-HD-map patch report is not gated on the stable stage")
    checks["patch_manifest_verification"] = check_record(not patch_failures, {}, patch_failures)

    metric_failures = []
    required_metrics = [
        "frame_sample_count",
        "frame_hash_unique_count",
        "frame_progress_expected",
        "frame_stability_class",
        "sample_interval_sec",
        "nonblack_percent_min",
        "nonblack_percent_max",
        "mean_luma_min",
        "mean_luma_max",
        "unique_sample_colors_min",
        "unique_sample_colors_max",
        "input_max_abs_error",
        "input_max_sample_abs_error",
        "max_input_drift_px",
        "process_sample_count",
        "working_set_growth_bytes",
        "private_memory_growth_bytes",
        "handle_growth",
        "max_working_set_growth_mb",
        "max_private_memory_growth_mb",
        "max_handle_growth",
        "working_set_growth_limit_bytes",
        "private_memory_growth_limit_bytes",
        "artifact_bytes",
        "process_exited_unexpectedly",
        "exit_code",
        "clean_stop",
        "final_route_marker",
        "route_results",
        "process_samples",
        "frame_samples",
        "capture_errors",
    ]
    for metric in required_metrics:
        if metric not in text:
            metric_failures.append(f"report metric is missing: {metric}")
    checks["required_metrics"] = check_record(
        not metric_failures,
        {"required_metric_count": len(required_metrics), "required_metrics": required_metrics},
        metric_failures,
    )

    promotion_failures = []
    if "right_bottom_promotion_blocked = $true" not in text.lower():
        promotion_failures.append("right-bottom promotion is not kept blocked")
    if "automated_visible_runtime_diagnostic_not_manual_directinput_release_proof" not in text:
        promotion_failures.append("executed report input proof class is not diagnostic/not-manual")
    checks["promotion_boundary"] = check_record(not promotion_failures, {}, promotion_failures)

    failures = [failure for check in checks.values() for failure in check["failures"]]
    return {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "passed": not failures,
        "runtime_policy": RUNTIME_POLICY,
        "guard_policy": "HD soak harness must stay opt-in, protected-stage, non-promoting, and artifact-safe",
        "script": str(script_path),
        "checks": checks,
        "failures": failures,
    }


def write_markdown(path: Path, guard: dict[str, Any]) -> None:
    lines = [
        "# HD Soak Harness Guard",
        "",
        f"- Overall: {status_text(bool(guard.get('passed')))}",
        f"- Generated: `{guard['generated_at']}`",
        f"- Runtime policy: {guard['runtime_policy']}",
        f"- Guard policy: {guard['guard_policy']}",
        f"- Script: `{guard['script']}`",
        "",
        "## Checks",
        "",
    ]
    for name, check in guard.get("checks", {}).items():
        lines.append(f"- `{name}`: `{status_text(bool(check.get('passed')))}`")
    if guard.get("failures"):
        lines.extend(["", "## Failures", ""])
        lines.extend(f"- {failure}" for failure in guard["failures"])
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="ascii")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--script", type=Path, default=DEFAULT_SCRIPT)
    parser.add_argument("--write-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--write-markdown", "--write-md", dest="write_markdown", type=Path, default=DEFAULT_MD)
    parser.add_argument("--require-pass", action="store_true")
    args = parser.parse_args()

    guard = build_guard(args.script)
    print(f"overall: {status_text(bool(guard['passed']))}")
    print(f"runtime-policy: {guard['runtime_policy']}")
    print(f"script: {guard['script']}")
    if guard["failures"]:
        print("failures:")
        for failure in guard["failures"]:
            print(f"  - {failure}")
    if args.write_json:
        args.write_json.parent.mkdir(parents=True, exist_ok=True)
        args.write_json.write_text(json.dumps(guard, indent=2) + "\n", encoding="ascii")
    if args.write_markdown:
        write_markdown(args.write_markdown, guard)
    if args.require_pass and not guard["passed"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
