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


def assignment_literal_array_block(text: str, name: str) -> str:
    pattern = re.compile(
        rf"\${re.escape(name)}\s*=\s*@\((?P<body>.*?)\)\s*\r?\n",
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
        "IntroSkipClickMode": "postmessage",
        "VisibleRuntimeApprovalExpiresUtc": "",
        "VisibleRuntimeApprovalToken": "",
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
    token_guard_line = line_number(text, r"if\s*\(\s*-not\s+\$VisibleRuntimeApprovalToken\s*\)")
    expiry_guard_line = line_number(text, r"if\s*\(\s*-not\s+\$VisibleRuntimeApprovalExpiresUtc\s*\)")
    expiry_parse_line = line_number(text, r"\[System\.DateTimeOffset\]::Parse")
    expiry_stale_line = line_number(text, r"Visible runtime approval expired")
    min_ttl_line = line_number(text, r"\$minApprovalTtlMinutes\s*=\s*30\b")
    ttl_guard_line = line_number(text, r"Visible runtime approval expires too soon")
    token_match_line = line_number(text, r"\$VisibleRuntimeApprovalToken\s+-ne\s+\$expectedVisibleRuntimeApprovalToken")
    dry_run_line = line_number(text, r"if\s*\(\s*-not\s+\$Execute\s*\)")
    output_dir_line = line_number(text, r"New-Item\s+-ItemType\s+Directory\s+-Force\s+-Path\s+\$outDir\b")
    candidate_dir_line = line_number(text, r"New-Item\s+-ItemType\s+Directory\s+-Force\s+-Path\s+\$CandidateDirFull\b")
    patch_report_line = line_number(text, r"&\s+\$PythonFull\s+@patchArgs\b")
    start_process_line = line_number(text, r"Start-Process\s+-FilePath\s+\$CandidateFull\b")
    if execute_line is None:
        approval_failures.append("missing -Execute switch")
    if allow_line is None:
        approval_failures.append("missing -AllowVisibleRuntime switch")
    if guard_line is None:
        approval_failures.append("missing execution-time AllowVisibleRuntime guard")
    if token_guard_line is None:
        approval_failures.append("missing visible runtime approval token presence guard")
    if expiry_guard_line is None:
        approval_failures.append("missing visible runtime approval expiry presence guard")
    if expiry_parse_line is None:
        approval_failures.append("missing visible runtime approval expiry parser")
    if expiry_stale_line is None:
        approval_failures.append("missing stale visible runtime approval expiry guard")
    if min_ttl_line is None:
        approval_failures.append("missing 30-minute visible runtime approval TTL constant")
    if ttl_guard_line is None or "[System.TimeSpan]::FromMinutes($minApprovalTtlMinutes)" not in text:
        approval_failures.append("missing visible runtime approval minimum TTL guard")
    if token_match_line is None:
        approval_failures.append("missing visible runtime approval token match guard")
    if dry_run_line is None:
        approval_failures.append("missing dry-run branch")
    if "explicit user approval" not in text.lower():
        approval_failures.append("missing explicit user approval phrase")
    if "-Execute" not in text or "-AllowVisibleRuntime" not in text:
        approval_failures.append("dry-run plan does not show explicit execute/visible flags")
    approval_boundary_lines = {
        "AllowVisibleRuntime guard": guard_line,
        "approval token presence guard": token_guard_line,
        "approval expiry presence guard": expiry_guard_line,
        "approval expiry stale guard": expiry_stale_line,
        "approval minimum TTL guard": ttl_guard_line,
        "approval token match guard": token_match_line,
    }
    side_effect_lines = {
        "output directory creation": output_dir_line,
        "candidate directory creation": candidate_dir_line,
        "patch report execution": patch_report_line,
        "visible process launch": start_process_line,
    }
    for boundary_name, boundary_line in approval_boundary_lines.items():
        if boundary_line is None:
            continue
        for side_effect_name, side_effect_line in side_effect_lines.items():
            if side_effect_line is not None and boundary_line > side_effect_line:
                approval_failures.append(
                    f"{boundary_name} must appear before {side_effect_name}"
                )
    execute_command_block = assignment_array_block(text, "executeCommand")
    execute_command_fragments = [
        "-Execute",
        "-AllowVisibleRuntime",
        "-IntroSkipClickMode",
        "-IntroSkipClicks",
        "-SkipPulses",
        "-SampleIntervalSec",
        "-MaxInputDriftPx",
        "-MinNonblackPercent",
        "-MinUniqueSampleColors",
        "-MaxArtifactMB",
        "-MaxWorkingSetGrowthMB",
        "-MaxPrivateMemoryGrowthMB",
        "-MaxHandleGrowth",
        "-VisibleRuntimeApprovalExpiresUtc",
        "-VisibleRuntimeApprovalToken",
        "-RequirePass",
        "-Json",
    ]
    approval_token_block = assignment_literal_array_block(text, "approvalTokenFields")
    approval_token_markers = [
        "$InputExeFull",
        "$WorkDirFull",
        "$windowedMode.Sha256",
        "$Stage",
        "$Tier",
        "$Route",
        "$DurationResolvedSec",
        "$CandidateDirFull",
        "$CandidateName",
        "$OutputRootFull",
        "$ReportJsonFull",
        "$ReportMarkdownFull",
        "$IntroSkipClickMode",
        "$IntroSkipClicks",
        "$IntroSkipStopClickRepeatOnDrift",
        "$SkipPulses",
        "$MaxInputDriftPx",
        "$SampleIntervalSec",
        "$MinNonblackPercent",
        "$MinUniqueSampleColors",
        "$MaxArtifactMB",
        "$MaxWorkingSetGrowthMB",
        "$MaxPrivateMemoryGrowthMB",
        "$MaxHandleGrowth",
        "$approvalExpiresUtc",
    ]
    if not execute_command_block:
        approval_failures.append("dry-run execute command block is missing")
    for fragment in execute_command_fragments:
        if fragment not in execute_command_block:
            approval_failures.append(f"dry-run execute command does not include {fragment}")
    if not approval_token_block:
        approval_failures.append("visible runtime approval token source block is missing")
    for marker in approval_token_markers:
        if marker not in approval_token_block:
            approval_failures.append(f"visible runtime approval token source does not include {marker}")
    if "min_ttl_minutes = $minApprovalTtlMinutes" not in text:
        approval_failures.append("dry-run visible runtime approval report does not include min_ttl_minutes")
    checks["visible_runtime_opt_in"] = check_record(
        not approval_failures,
        {
            "execute_switch_line": execute_line,
            "allow_visible_runtime_switch_line": allow_line,
            "dry_run_branch_line": dry_run_line,
            "runtime_guard_line": guard_line,
            "token_guard_line": token_guard_line,
            "expiry_guard_line": expiry_guard_line,
            "expiry_parse_line": expiry_parse_line,
            "expiry_stale_line": expiry_stale_line,
            "min_ttl_line": min_ttl_line,
            "ttl_guard_line": ttl_guard_line,
            "token_match_line": token_match_line,
            "output_dir_line": output_dir_line,
            "candidate_dir_line": candidate_dir_line,
            "patch_report_line": patch_report_line,
            "start_process_line": start_process_line,
            "execute_command_fragments": execute_command_fragments,
            "approval_token_markers": approval_token_markers,
        },
        approval_failures,
    )

    intro_failures = []
    intro_values = ["IntroSkipClickMode", "postmessage", "none", "IntroSkipClicks", "SkipPulses"]
    if not contains_all(text, intro_values):
        intro_failures.append("intro skip controls are missing required mode/count/pulse tokens")
    for marker in [
        "ClickModeOverride",
        "ClickRepeatOverride",
        "StopClickRepeatOnDrift",
        "--stop-click-repeat-on-drift",
        "EffectiveClickMode",
        "EffectiveClickRepeat",
        "TransitionStopObserved",
        "sample_drift_after_click",
        "intro_skip_harness_prep_not_manual_directinput_release_proof",
    ]:
        if marker not in text:
            intro_failures.append(f"intro skip override/report marker is missing: {marker}")
    if observed_defaults.get("IntroSkipClickMode") != "postmessage":
        intro_failures.append("IntroSkipClickMode default must remain postmessage")
    checks["intro_skip_policy"] = check_record(
        not intro_failures,
        {
            "intro_skip_click_mode_default": observed_defaults.get("IntroSkipClickMode"),
            "proof_class": "intro_skip_harness_prep_not_manual_directinput_release_proof",
        },
        intro_failures,
    )

    windowed_failures = []
    windowed_markers = [
        "Get-DxcfgWindowedStatus",
        "dxcfg.ini",
        "$display -ne 'application'",
        "$presentation -ne 'windowed'",
        "Windowed DirectDraw config check failed",
        "window_mode = $windowedMode",
        "$windowedMode.Sha256",
    ]
    for marker in windowed_markers:
        if marker not in text:
            windowed_failures.append(f"windowed-mode contract marker is missing: {marker}")
    checks["windowed_mode"] = check_record(
        not windowed_failures,
        {
            "required_display": "application",
            "required_presentation": "windowed",
            "config_name": "dxcfg.ini",
            "approval_token_pins_config_sha256": "$windowedMode.Sha256" in approval_token_block,
        },
        windowed_failures,
    )

    health_failures = []
    health_markers = [
        "Get-WindowHealthSample",
        "IsHungAppWindow",
        "window_health_policy",
        "window_health_samples",
        "window_hang_observed",
        "window_missing_while_alive_observed",
        "capture skipped because window health was",
        "before-{0}",
        "after-{0}-wait",
        "before-frame-{0:D4}",
    ]
    for marker in health_markers:
        if marker not in text:
            health_failures.append(f"window-health marker is missing: {marker}")
    checks["window_health_stop"] = check_record(
        not health_failures,
        {
            "probe": "EnumWindows plus IsHungAppWindow",
            "stops_input_and_capture_on_failure": True,
            "required_markers": health_markers,
        },
        health_failures,
    )

    # The window-health grace retries above only cover HEALTH SAMPLING. The
    # input helpers cache a handle across the intro->menu mode switch, and the
    # wrapper recreates its window there (2026-07-18: WinError 1400 killed a
    # short2 run with zero frames), so the harness must pin the settle gate and
    # the bounded re-acquire it hands to tools/mouse_path_probe.py.
    freshness_failures = []
    freshness_markers = [
        "$WindowStableSamples",
        "$WindowStablePollMs",
        "$WindowStableTimeoutSec",
        "$WindowReacquireAttempts",
        "$WindowReacquireDelayMs",
        "--window-stable-samples",
        "--window-stable-poll-ms",
        "--window-stable-timeout-sec",
        "--window-reacquire-attempts",
        "--window-reacquire-delay-ms",
        "WindowStable",
        "WindowLostObserved",
        "WindowReacquireCount",
    ]
    for marker in freshness_markers:
        if marker not in text:
            freshness_failures.append(f"window-handle freshness marker is missing: {marker}")
    checks["window_handle_freshness"] = check_record(
        not freshness_failures,
        {
            "policy": (
                "input helpers re-resolve the target window per phase and wait for a "
                "stable hwnd/client size before sending input"
            ),
            "required_markers": freshness_markers,
        },
        freshness_failures,
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
        "max_artifact_mb",
        "artifact_limit_bytes",
        "artifact_bytes",
        "process_exited_unexpectedly",
        "exit_code",
        "clean_stop",
        "final_route_marker",
        "route_results",
        "process_samples",
        "frame_samples",
        "capture_errors",
        "window_health_sample_count",
        "window_hang_observed",
        "window_missing_while_alive_observed",
        "window_health_first_failure",
        "window_health_samples",
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
