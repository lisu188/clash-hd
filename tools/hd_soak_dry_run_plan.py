#!/usr/bin/env python3
"""Persist and validate the current short HD soak dry-run plan.

This guard invokes the selected visible or hidden soak harness without -Execute unless a
fixture plan is supplied. It does not launch Clash95, CDB, wrappers, or visible
windows. The output is the machine-checked handoff packet for the next
short soak, preserving the separate visible approval boundary.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shlex
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import hd_soak_intro_skip_rerun_readiness as intro_readiness

REPO_ROOT = Path(__file__).resolve().parents[1]
PROTECTED_STABLE_STAGE = (
    "gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-"
    "minimapright-dynvswitch"
)
EXPECTED_BASE_SHA256 = "500055d77d03d514e8d3168506bd10f67cd8569bcc450604ff8192f46cdaf3ae"
RUNTIME_POLICY = (
    "repo-only soak dry-run plan guard; invokes the PowerShell harness only "
    "without -Execute unless --read-plan-json is supplied; does not launch "
    "Clash95, CDB, wrappers, or visible windows"
)
DEFAULT_STEP_STATUS_JSON = Path("captures/current/hd-soak-short-step-status-current.json")
DEFAULT_SCRIPT = Path("scripts/smoke/run_hd_soak.ps1")
HIDDEN_SCRIPT = Path("scripts/cdb/run_hidden_soak.ps1")
HIDDEN_ENVIRONMENT = "hidden_cdb_host"
HOST_ENVIRONMENT = "host_visible"
HIDDEN_EVIDENCE_CLASS = "approved_hidden_cdb_host_soak"
HIDDEN_INPUT_RESPONSIVENESS = "not_applicable_hidden"
HIDDEN_CANDIDATE_ROOT = r"C:\ClashTests\hd-soak\hidden"
HIDDEN_OUTPUT_ROOT = r"C:\ClashCaptures\hd-soak\hidden"
DEFAULT_JSON = Path("captures/current/hd-soak-dry-run-plan-current.json")
DEFAULT_MD = Path("captures/current/hd-soak-dry-run-plan-current.md")
MAX_INPUT_DRIFT_PX = 1
EXPECTED_SAMPLE_INTERVAL_SEC = 15
EXPECTED_MIN_NONBLACK_PERCENT = 10.0
EXPECTED_MIN_NONBLACK_PERCENT_TEXT = "10"
EXPECTED_MIN_UNIQUE_SAMPLE_COLORS = 8
EXPECTED_MAX_ARTIFACT_MB = 250
EXPECTED_MAX_WORKING_SET_GROWTH_MB = 64
EXPECTED_MAX_PRIVATE_MEMORY_GROWTH_MB = 64
EXPECTED_MAX_HANDLE_GROWTH = 128
EXPECTED_INTRO_SKIP_CLICK_MODE = "postmessage"
EXPECTED_INTRO_SKIP_CLICKS = 8
EXPECTED_SKIP_PULSES = 4
EXPECTED_CANDIDATE_DIR = r"C:\ClashTests\hd-soak"
EXPECTED_OUTPUT_ROOT = r"C:\ClashCaptures\hd-soak"
EXPECTED_INPUT_EXE = r"C:\Clash\clash95.exe"
EXPECTED_WORKDIR = r"C:\Clash"
APPROVAL_TOKEN_LENGTH = 16
APPROVAL_MAX_AGE_HOURS = 12
MIN_APPROVAL_TTL_MINUTES = 30
APPROVAL_EXPIRY_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T.*(?:Z|[+-]\d{2}:\d{2})$")


def status_text(passed: bool) -> str:
    return "PASS" if passed else "FAIL"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def normalized_path(value: Any) -> str:
    return str(value or "").replace("/", "\\").rstrip("\\").casefold()


def resolve_repo_path(path_text: str) -> Path:
    path = Path(path_text.replace("\\", "/"))
    if path.is_absolute():
        return path
    return REPO_ROOT / path


def command_text(args: list[str]) -> str:
    return " ".join(args)


def current_step_record(step_status: dict[str, Any]) -> dict[str, Any] | None:
    current = step_status.get("current_step") or {}
    current_id = current.get("id")
    for step in step_status.get("steps") or []:
        if step.get("id") == current_id:
            return step
    return None


def dry_run_command(script: Path, step: dict[str, Any]) -> list[str]:
    paths = step.get("paths") or {}
    if step.get("preferred_environment", HOST_ENVIRONMENT) == HIDDEN_ENVIRONMENT:
        command = ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script)]
        options = {
            "Route": step.get("route"), "DurationSec": step.get("duration_sec"),
            "FrameIntervalSec": EXPECTED_SAMPLE_INTERVAL_SEC, "PanIntervalSec": 10,
            "ReportJson": paths.get("report_json"), "ReportMarkdown": paths.get("report_markdown"),
            "GuardJson": paths.get("guard_json"), "GuardMarkdown": paths.get("guard_markdown"),
            "MaxArtifactMB": EXPECTED_MAX_ARTIFACT_MB,
            "MaxWorkingSetGrowthMB": EXPECTED_MAX_WORKING_SET_GROWTH_MB,
            "MaxPrivateMemoryGrowthMB": EXPECTED_MAX_PRIVATE_MEMORY_GROWTH_MB,
            "MaxHandleGrowth": EXPECTED_MAX_HANDLE_GROWTH,
        }
        for name, value in options.items():
            command.extend([f"-{name}", str(value or "")])
        return command + ["-RequirePass", "-Json"]
    return [
        "powershell.exe",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(script),
        "-Tier",
        str(step.get("tier") or ""),
        "-Route",
        str(step.get("route") or ""),
        "-ReportJson",
        str(paths.get("report_json") or ""),
        "-ReportMarkdown",
        str(paths.get("report_markdown") or ""),
        "-IntroSkipClickMode",
        EXPECTED_INTRO_SKIP_CLICK_MODE,
        "-IntroSkipClicks",
        str(EXPECTED_INTRO_SKIP_CLICKS),
        "-SkipPulses",
        str(EXPECTED_SKIP_PULSES),
        "-SampleIntervalSec",
        str(EXPECTED_SAMPLE_INTERVAL_SEC),
        "-MaxInputDriftPx",
        str(MAX_INPUT_DRIFT_PX),
        "-MinNonblackPercent",
        str(EXPECTED_MIN_NONBLACK_PERCENT),
        "-MinUniqueSampleColors",
        str(EXPECTED_MIN_UNIQUE_SAMPLE_COLORS),
        "-MaxArtifactMB",
        str(EXPECTED_MAX_ARTIFACT_MB),
        "-MaxWorkingSetGrowthMB",
        str(EXPECTED_MAX_WORKING_SET_GROWTH_MB),
        "-MaxPrivateMemoryGrowthMB",
        str(EXPECTED_MAX_PRIVATE_MEMORY_GROWTH_MB),
        "-MaxHandleGrowth",
        str(EXPECTED_MAX_HANDLE_GROWTH),
        "-Json",
    ]


def extract_json(stdout: str) -> dict[str, Any]:
    start = stdout.find("{")
    end = stdout.rfind("}")
    if start < 0 or end < start:
        raise ValueError("dry-run output did not contain a JSON object")
    return json.loads(stdout[start : end + 1])


def parse_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def approval_ttl_status(approval_expires_utc: Any) -> dict[str, Any]:
    expires_at = parse_datetime(approval_expires_utc)
    now = datetime.now(timezone.utc)
    failures: list[str] = []
    remaining_seconds: float | None = None
    if expires_at is None:
        failures.append("plan visible runtime approval expires_utc is missing or invalid")
    else:
        remaining = expires_at - now
        remaining_seconds = remaining.total_seconds()
        if remaining < timedelta(minutes=MIN_APPROVAL_TTL_MINUTES):
            failures.append(
                "plan visible runtime approval expires too soon; "
                f"regenerate before approval so at least {MIN_APPROVAL_TTL_MINUTES} minutes remain"
            )
    return {
        "expires_utc": approval_expires_utc,
        "remaining_seconds": remaining_seconds,
        "min_remaining_minutes": MIN_APPROVAL_TTL_MINUTES,
        "passed": not failures,
        "failures": failures,
    }


def run_harness_plan(script: Path, step: dict[str, Any]) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    command = dry_run_command(script, step)
    try:
        run = subprocess.run(
            command,
            cwd=REPO_ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    except FileNotFoundError as exc:
        # No PowerShell on this platform: the dry-run harness plan cannot be
        # extracted, so fail closed with a recorded reason instead of crashing
        # the evidence refresh. Only the Windows rig can turn this check green.
        return None, {
            "command": command_text(command),
            "exit_code": None,
            "stderr": f"dry-run harness runner unavailable on this platform: {exc}",
        }
    detail = {
        "command": command_text(command),
        "exit_code": run.returncode,
        "stderr": run.stderr.strip(),
    }
    if run.returncode != 0:
        return None, detail
    try:
        return extract_json(run.stdout), detail
    except (json.JSONDecodeError, ValueError) as exc:
        detail["parse_error"] = str(exc)
        return None, detail


def hidden_runner_source_binding() -> dict[str, Any]:
    """Record the reviewed runner source enforcing fields absent from its JSON plan."""
    path = REPO_ROOT / HIDDEN_SCRIPT
    source = path.read_bytes()
    text = source.decode("utf-8-sig")
    declarations = {
        "ProtectedStableStage": PROTECTED_STABLE_STAGE, "ExpectedBaseSha256": EXPECTED_BASE_SHA256.upper(),
        "ExpectedInputExe": EXPECTED_INPUT_EXE, "ExpectedWorkDir": EXPECTED_WORKDIR,
        "ExpectedCandidateRoot": HIDDEN_CANDIDATE_ROOT, "ExpectedOutputRoot": HIDDEN_OUTPUT_ROOT,
    }
    failures = []
    gate = text.find("if (-not $Execute) {")
    preflight = text[:gate] if gate >= 0 else ""
    for name, value in declarations.items():
        if f"${name} = '{value}'" not in preflight:
            failures.append(f"hidden runner source does not pin {name} before its Execute gate")
    for fragment in (
        "$inputSha -ne $ExpectedBaseSha256", "$Stage -ne $ProtectedStableStage",
        "-Left $InputExe -Right $ExpectedInputExe", "-Left $WorkDir -Right $ExpectedWorkDir",
        "-Left $CandidateDir -Right $ExpectedCandidateRoot", "-Left $OutDir -Right $ExpectedOutputRoot",
    ):
        if fragment not in preflight:
            failures.append(f"hidden runner source is missing preflight enforcement: {fragment}")
    return {"path": str(path), "sha256": hashlib.sha256(source).hexdigest(),
            "protected_stage": PROTECTED_STABLE_STAGE, "input_exe": EXPECTED_INPUT_EXE,
            "workdir": EXPECTED_WORKDIR, "candidate_root": HIDDEN_CANDIDATE_ROOT,
            "output_root": HIDDEN_OUTPUT_ROOT, "passed": not failures, "failures": failures}


def hidden_command_options(command: Any) -> tuple[dict[str, str | bool], list[str]]:
    if not isinstance(command, str) or any(character in command for character in ";|&`$\n\r"):
        return {}, ["hidden runtime command is missing or contains shell operators"]
    try:
        tokens = [token[1:-1] if len(token) >= 2 and token[0] == token[-1] and token[0] in "\"'" else token
                  for token in shlex.split(command, posix=False)]
    except ValueError:
        return {}, ["hidden runtime command quoting is malformed"]
    if [token.casefold() for token in tokens[:5]] != ["powershell.exe", "-noprofile", "-executionpolicy", "bypass", "-file"]:
        return {}, ["hidden runtime command does not use the expected PowerShell File invocation"]
    if len(tokens) < 6 or normalized_path(resolve_repo_path(tokens[5])) != normalized_path(REPO_ROOT / HIDDEN_SCRIPT):
        return {}, ["hidden runtime command does not use the repository hidden runner"]
    options: dict[str, str | bool] = {}
    index = 6
    while index < len(tokens):
        name = tokens[index]
        if not name.startswith("-") or name in options:
            return {}, ["hidden runtime command contains duplicate or malformed options"]
        if name in {"-Execute", "-RequirePass", "-Json"}:
            options[name] = True
            index += 1
        elif index + 1 < len(tokens) and not tokens[index + 1].startswith("-"):
            options[name] = tokens[index + 1]
            index += 2
        else:
            return {}, [f"hidden runtime command option is malformed: {name}"]
    return options, []


def validate_hidden_plan(plan: dict[str, Any], step: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    if step.get("preferred_environment") != HIDDEN_ENVIRONMENT or step.get("route") not in {"map-idle", "map-pan"}:
        failures.append("hidden plan does not correspond to a supported hidden map step")
    for field, expected in (("executed", False), ("preflight_passed", True), ("environment", HIDDEN_ENVIRONMENT),
                            ("route", step.get("route")), ("duration_sec", step.get("duration_sec"))):
        if plan.get(field) != expected or (isinstance(expected, bool) and plan.get(field) is not expected):
            failures.append(f"hidden plan {field} is {plan.get(field)!r}, expected {expected!r}")
    if str(plan.get("input_sha256") or "").lower() != EXPECTED_BASE_SHA256:
        failures.append("hidden plan input_sha256 does not match the protected base SHA")
    for field, root in (("candidate_run_directory", HIDDEN_CANDIDATE_ROOT), ("output_directory", HIDDEN_OUTPUT_ROOT)):
        value = normalized_path(plan.get(field))
        if not value.startswith(normalized_path(root) + "\\") or ".." in value.split("\\"):
            failures.append(f"hidden plan {field} is not a per-run directory under {root}")
    failures.extend(hidden_runner_source_binding()["failures"])
    options, command_failures = hidden_command_options(plan.get("hidden_runtime_command"))
    failures.extend(command_failures)
    expected_options = {
        "-Route": str(step.get("route")), "-DurationSec": str(step.get("duration_sec")),
        "-FrameIntervalSec": str(EXPECTED_SAMPLE_INTERVAL_SEC), "-PanIntervalSec": "10", "-LoadSlot": "2",
        "-ReadyTimeoutSec": "240", "-EndGraceSec": "180", "-PngEdgeCount": "3",
        "-MaxArtifactMB": str(EXPECTED_MAX_ARTIFACT_MB),
        "-MaxWorkingSetGrowthMB": str(EXPECTED_MAX_WORKING_SET_GROWTH_MB),
        "-MaxPrivateMemoryGrowthMB": str(EXPECTED_MAX_PRIVATE_MEMORY_GROWTH_MB),
        "-MaxHandleGrowth": str(EXPECTED_MAX_HANDLE_GROWTH),
        "-Execute": True, "-RequirePass": True, "-Json": True,
    }
    for name, expected in expected_options.items():
        if options.get(name) != expected:
            failures.append(f"hidden runtime command {name} is {options.get(name)!r}, expected {expected!r}")
    path_options = {
        "-ProbeTemplate": str(REPO_ROOT / "probes/cdb/render/clash95_surface_dump_probe.cdb"),
        "-SoakProbeTemplate": str(REPO_ROOT / "probes/cdb/soak/clash95_hidden_soak_route_extra.cdb"),
        "-DdrawProxyBuildScript": str(REPO_ROOT / "scripts/build/build_ddraw_surfdump_proxy.ps1"),
        **{option: (step.get("paths") or {}).get(key) for option, key in (
            ("-ReportJson", "report_json"), ("-ReportMarkdown", "report_markdown"),
            ("-GuardJson", "guard_json"), ("-GuardMarkdown", "guard_markdown"))},
    }
    for name, expected in path_options.items():
        value = options.get(name)
        if not isinstance(value, str) or not expected or normalized_path(resolve_repo_path(value)) != normalized_path(resolve_repo_path(str(expected))):
            failures.append(f"hidden runtime command {name} does not match its canonical path")
    python = options.get("-Python")
    if (not isinstance(python, str) or not Path(python).is_file()
            or normalized_path(Path(python).resolve()) != normalized_path(Path(sys.executable).resolve())):
        failures.append("hidden runtime command Python does not match the verified guard interpreter")
    unexpected = set(options) - set(expected_options) - set(path_options) - {"-Python"}
    if unexpected:
        failures.append(f"hidden runtime command has unexpected options: {sorted(unexpected)}")
    return failures


def validate_plan(plan: dict[str, Any], step: dict[str, Any]) -> list[str]:
    if step.get("preferred_environment", HOST_ENVIRONMENT) == HIDDEN_ENVIRONMENT:
        return validate_hidden_plan(plan, step)
    failures: list[str] = []
    paths = step.get("paths") or {}
    expected_report_json = resolve_repo_path(str(paths.get("report_json") or ""))
    expected_report_md = resolve_repo_path(str(paths.get("report_markdown") or ""))
    execute_command = str((plan.get("commands") or {}).get("execute") or "")
    patch_command = str((plan.get("commands") or {}).get("patch") or "")

    if plan.get("dry_run") is not True:
        failures.append("plan is not marked as a dry run")
    policy = str(plan.get("runtime_policy") or "").lower()
    if "opt-in" not in policy or "explicit user approval" not in policy:
        failures.append("runtime policy does not record opt-in explicit approval")
    if plan.get("stage") != PROTECTED_STABLE_STAGE:
        failures.append(f"stage is {plan.get('stage')!r}, expected protected stable stage")
    if plan.get("protected_stable_stage") != PROTECTED_STABLE_STAGE:
        failures.append("protected_stable_stage does not match the protected stage")
    if plan.get("stable_stage_should_change") is not False:
        failures.append("plan would change the stable stage")
    if plan.get("right_bottom_promotion_blocked") is not True:
        failures.append("plan does not keep right-bottom promotion blocked")
    if plan.get("tier") != step.get("tier") or plan.get("route") != step.get("route"):
        failures.append("plan tier/route do not match the current short step")
    if int(plan.get("duration_sec") or 0) != int(step.get("duration_sec") or 0):
        failures.append("plan duration does not match the current short step")
    if normalized_path(plan.get("input_exe")) != normalized_path(EXPECTED_INPUT_EXE):
        failures.append("plan input_exe is not the original C:\\Clash executable")
    if normalized_path(plan.get("workdir")) != normalized_path(EXPECTED_WORKDIR):
        failures.append("plan workdir is not C:\\Clash")
    if normalized_path(plan.get("candidate_dir")) != normalized_path(EXPECTED_CANDIDATE_DIR):
        failures.append("plan candidate_dir is not the isolated C:\\ClashTests soak directory")
    if normalized_path(plan.get("output_root")) != normalized_path(EXPECTED_OUTPUT_ROOT):
        failures.append("plan output_root is not the external C:\\ClashCaptures soak directory")
    if normalized_path(plan.get("candidate_path")).startswith(normalized_path(str(REPO_ROOT))):
        failures.append("plan candidate_path is inside the repository")
    if normalized_path(plan.get("report_json")) != normalized_path(expected_report_json):
        failures.append("plan report_json does not match the canonical current-step report")
    if normalized_path(plan.get("report_markdown")) != normalized_path(expected_report_md):
        failures.append("plan report_markdown does not match the canonical current-step report")
    if (plan.get("input_limits") or {}).get("max_input_drift_px") != MAX_INPUT_DRIFT_PX:
        failures.append("plan does not pin max input drift to 1 px")
    if int(plan.get("sample_interval_sec") or 0) != EXPECTED_SAMPLE_INTERVAL_SEC:
        failures.append(f"plan sample_interval_sec is not {EXPECTED_SAMPLE_INTERVAL_SEC}")
    frame_limits = plan.get("frame_limits") or {}
    if float(frame_limits.get("min_nonblack_percent") or 0.0) != EXPECTED_MIN_NONBLACK_PERCENT:
        failures.append(
            f"plan frame limit min_nonblack_percent is {frame_limits.get('min_nonblack_percent')!r}, "
            f"expected {EXPECTED_MIN_NONBLACK_PERCENT}"
        )
    if int(frame_limits.get("min_unique_sample_colors") or 0) != EXPECTED_MIN_UNIQUE_SAMPLE_COLORS:
        failures.append(
            f"plan frame limit min_unique_sample_colors is {frame_limits.get('min_unique_sample_colors')!r}, "
            f"expected {EXPECTED_MIN_UNIQUE_SAMPLE_COLORS}"
        )
    intro_skip = plan.get("intro_skip") or {}
    if intro_skip.get("click_mode") != EXPECTED_INTRO_SKIP_CLICK_MODE:
        failures.append("plan intro_skip click_mode is not postmessage")
    if int(intro_skip.get("click_repeat") or 0) != EXPECTED_INTRO_SKIP_CLICKS:
        failures.append(f"plan intro_skip click_repeat is not {EXPECTED_INTRO_SKIP_CLICKS}")
    if int(intro_skip.get("space_pulses") or 0) != EXPECTED_SKIP_PULSES:
        failures.append(f"plan intro_skip space_pulses is not {EXPECTED_SKIP_PULSES}")
    if intro_skip.get("proof_class") != "intro_skip_harness_prep_not_manual_directinput_release_proof":
        failures.append("plan intro_skip proof_class is missing the non-manual proof boundary")

    approval = plan.get("visible_runtime_approval") or {}
    approval_token = str(approval.get("token") or "")
    if len(approval_token) != APPROVAL_TOKEN_LENGTH or not all(ch in "0123456789abcdef" for ch in approval_token):
        failures.append("plan visible runtime approval token is missing or malformed")
    if approval.get("token_kind") != "sha256-16":
        failures.append("plan visible runtime approval token_kind is not sha256-16")
    approval_expires_utc = str(approval.get("expires_utc") or "")
    if not APPROVAL_EXPIRY_PATTERN.match(approval_expires_utc):
        failures.append("plan visible runtime approval expires_utc is missing or malformed")
    failures.extend(approval_ttl_status(approval_expires_utc)["failures"])
    if int(approval.get("max_age_hours") or 0) != APPROVAL_MAX_AGE_HOURS:
        failures.append(f"plan visible runtime approval max_age_hours is not {APPROVAL_MAX_AGE_HOURS}")
    if int(approval.get("min_ttl_minutes") or 0) != MIN_APPROVAL_TTL_MINUTES:
        failures.append(f"plan visible runtime approval min_ttl_minutes is not {MIN_APPROVAL_TTL_MINUTES}")
    token_fields = approval.get("token_fields") or []
    if not isinstance(token_fields, list) or len(token_fields) < 10:
        failures.append("plan visible runtime approval token_fields are missing")
    elif approval_expires_utc not in token_fields:
        failures.append("plan visible runtime approval expiry is not covered by token_fields")
    if "copy-exact dry-run approval packet" not in str(approval.get("purpose") or ""):
        failures.append("plan visible runtime approval purpose does not explain the copy-exact boundary")

    growth = plan.get("growth_limits") or {}
    expected_growth = {
        "max_working_set_growth_mb": EXPECTED_MAX_WORKING_SET_GROWTH_MB,
        "max_private_memory_growth_mb": EXPECTED_MAX_PRIVATE_MEMORY_GROWTH_MB,
        "max_handle_growth": EXPECTED_MAX_HANDLE_GROWTH,
        "max_artifact_mb": EXPECTED_MAX_ARTIFACT_MB,
    }
    for name, expected in expected_growth.items():
        if int(growth.get(name) or 0) != expected:
            failures.append(f"plan growth limit {name} is {growth.get(name)!r}, expected {expected}")

    raw_policy = str(plan.get("raw_artifacts_policy") or "").lower()
    if "outside the repository" not in raw_policy:
        failures.append("plan does not state that raw artifacts stay outside the repository")
    if plan.get("input_exists") is not True:
        failures.append("plan input_exe does not exist or was not confirmed readable")
    base_status = str(plan.get("base_sha_status") or "")
    if base_status != "ok":
        failures.append(f"plan base_sha_status is {base_status!r}, expected 'ok'")
    elif str(plan.get("input_sha256") or "").lower() != EXPECTED_BASE_SHA256:
        failures.append("plan input_sha256 does not match the expected base SHA")

    for fragment in ("patch_clash95_hd.py", "--input", "--output", "--stage", PROTECTED_STABLE_STAGE):
        if fragment not in patch_command:
            failures.append(f"patch command missing fragment: {fragment}")
    for fragment in (
        "-InputExe",
        EXPECTED_INPUT_EXE,
        "-WorkDir",
        EXPECTED_WORKDIR,
        "-Stage",
        PROTECTED_STABLE_STAGE,
        "-Execute",
        "-AllowVisibleRuntime",
        "-RequirePass",
        "-Json",
        "-OutputRoot",
        EXPECTED_OUTPUT_ROOT,
        "-ReportJson",
        "-ReportMarkdown",
        "-IntroSkipClickMode",
        EXPECTED_INTRO_SKIP_CLICK_MODE,
        "-IntroSkipClicks",
        str(EXPECTED_INTRO_SKIP_CLICKS),
        "-SkipPulses",
        str(EXPECTED_SKIP_PULSES),
        "-SampleIntervalSec",
        str(EXPECTED_SAMPLE_INTERVAL_SEC),
        "-MaxInputDriftPx",
        "1",
        "-MinNonblackPercent",
        EXPECTED_MIN_NONBLACK_PERCENT_TEXT,
        "-MinUniqueSampleColors",
        str(EXPECTED_MIN_UNIQUE_SAMPLE_COLORS),
        "-MaxArtifactMB",
        str(EXPECTED_MAX_ARTIFACT_MB),
        "-MaxWorkingSetGrowthMB",
        str(EXPECTED_MAX_WORKING_SET_GROWTH_MB),
        "-MaxPrivateMemoryGrowthMB",
        str(EXPECTED_MAX_PRIVATE_MEMORY_GROWTH_MB),
        "-MaxHandleGrowth",
        str(EXPECTED_MAX_HANDLE_GROWTH),
        "-VisibleRuntimeApprovalExpiresUtc",
        approval_expires_utc,
        "-VisibleRuntimeApprovalToken",
        approval_token,
    ):
        if fragment not in execute_command:
            failures.append(f"execute command missing fragment: {fragment}")
    if normalized_path(EXPECTED_CANDIDATE_DIR) not in normalized_path(execute_command):
        failures.append("execute command does not use the isolated candidate directory")
    if normalized_path(expected_report_json) not in normalized_path(execute_command):
        failures.append("execute command does not pin canonical report JSON")
    if normalized_path(expected_report_md) not in normalized_path(execute_command):
        failures.append("execute command does not pin canonical report Markdown")
    return failures


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    step_status = load_json(args.step_status_json)
    if intro_readiness.short_ladder_terminal_claim(step_status):
        return intro_readiness.completed_short_ladder_report(step_status, args.step_status_json, RUNTIME_POLICY)
    failures: list[str] = []
    if not step_status.get("passed"):
        failures.append("short-step status report is not passing")
    current = step_status.get("current_step") or {}
    step = current_step_record(step_status)
    if step is None:
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "passed": False,
            "runtime_policy": RUNTIME_POLICY,
            "status": "missing_current_step",
            "source_artifacts": {"step_status_json": str(args.step_status_json)},
            "failures": ["current short-step record is missing"],
        }

    environment = step.get("preferred_environment", HOST_ENVIRONMENT)
    required_script = HIDDEN_SCRIPT if environment == HIDDEN_ENVIRONMENT else DEFAULT_SCRIPT
    requested_script = getattr(args, "script", None)
    # Existing programmatic callers pass DEFAULT_SCRIPT as the old default.
    # Hidden steps always route to the hidden runner; no visible fallback exists.
    script = required_script if requested_script in (None, DEFAULT_SCRIPT) else Path(requested_script)
    script_valid = normalized_path(resolve_repo_path(str(script))) == normalized_path(REPO_ROOT / required_script)
    if environment not in (HOST_ENVIRONMENT, HIDDEN_ENVIRONMENT):
        failures.append(f"unsupported short-soak preferred environment: {environment!r}")
    if not script_valid:
        failures.append("selected harness script does not match the current environment")

    if args.read_plan_json:
        plan = load_json(args.read_plan_json)
        invocation = {
            "command": None,
            "exit_code": None,
            "source": str(args.read_plan_json),
            "used_fixture_plan": True,
        }
    elif script_valid and environment in (HOST_ENVIRONMENT, HIDDEN_ENVIRONMENT):
        plan, invocation = run_harness_plan(script, step)
        invocation["used_fixture_plan"] = False
    else:
        plan = None
        invocation = {"command": None, "exit_code": None, "used_fixture_plan": False}
    if plan is None:
        failures.append("dry-run harness did not produce a readable JSON plan")
        plan = {}
    else:
        failures.extend(validate_plan(plan, step))
    hidden = environment == HIDDEN_ENVIRONMENT
    approval_ttl = ({"status": "not_applicable_hidden", "applicable": False}
                    if hidden else approval_ttl_status((plan.get("visible_runtime_approval") or {}).get("expires_utc")))

    status = ("ready_for_hidden_runtime" if hidden else "ready_for_explicit_approval") if not failures else "dry_run_plan_invalid"
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "passed": not failures,
        "runtime_policy": RUNTIME_POLICY,
        "status": status,
        "environment": environment,
        "evidence_class": HIDDEN_EVIDENCE_CLASS if hidden else "host_visible_runtime_soak",
        "input_responsiveness": HIDDEN_INPUT_RESPONSIVENESS if hidden else None,
        "runner_source": hidden_runner_source_binding() if hidden else None,
        "source_artifacts": {
            "step_status_json": str(args.step_status_json),
            "script": str(script),
            "read_plan_json": str(args.read_plan_json) if args.read_plan_json else None,
        },
        "current_step": {
            "id": current.get("id"),
            "status": current.get("status"),
            "tier": step.get("tier"),
            "route": step.get("route"),
            "duration_sec": step.get("duration_sec"),
            "paths": step.get("paths"),
            "preferred_environment": environment,
        },
        "invocation": invocation,
        "plan": plan,
        "approval_ttl": approval_ttl,
        "approval_gated_execute_command": None if hidden else (plan.get("commands") or {}).get("execute"),
        "hidden_runtime_command": plan.get("hidden_runtime_command") if hidden else None,
        "recommended_runtime_command": plan.get("hidden_runtime_command") if hidden else (plan.get("commands") or {}).get("execute"),
        "locks": {
            "stable_stage_should_change": False,
            "right_bottom_promotion_blocked": True,
            "long_tiers_locked": True,
            "future_lanes_locked": True,
        },
        "failures": failures,
    }


def to_markdown(report: dict[str, Any]) -> str:
    if report.get("terminal_short_ladder"):
        return intro_readiness.completed_short_ladder_markdown(report, "HD Soak Dry-Run Plan")
    step = report.get("current_step") or {}
    plan = report.get("plan") or {}
    approval_ttl = report.get("approval_ttl") or {}
    hidden = report.get("environment") == HIDDEN_ENVIRONMENT
    lines = [
        "# HD Soak Dry-Run Plan",
        "",
        f"- Overall: {status_text(bool(report.get('passed')))}",
        f"- Generated: `{report.get('generated_at')}`",
        f"- Runtime policy: {report.get('runtime_policy')}",
        f"- Status: `{report.get('status')}`",
        f"- Current step: `{step.get('id')}` status=`{step.get('status')}`",
        f"- Tier/route: `{step.get('tier')}` / `{step.get('route')}`",
        f"- Environment: `{report.get('environment')}`",
        f"- Dry run: `{plan.get('executed') is False if hidden else plan.get('dry_run')}`",
        f"- Candidate dir: `{plan.get('candidate_run_directory') if hidden else plan.get('candidate_dir')}`",
        f"- Output root: `{plan.get('output_directory') if hidden else plan.get('output_root')}`",
        f"- Report JSON: `{plan.get('report_json')}`",
        f"- Max input drift px: `{(plan.get('input_limits') or {}).get('max_input_drift_px')}`",
        f"- Intro skip: mode=`{(plan.get('intro_skip') or {}).get('click_mode')}` repeat=`{(plan.get('intro_skip') or {}).get('click_repeat')}` pulses=`{(plan.get('intro_skip') or {}).get('space_pulses')}`",
        f"- Approval TTL: `{status_text(bool(approval_ttl.get('passed')))}; expires={approval_ttl.get('expires_utc')}; remaining_seconds={approval_ttl.get('remaining_seconds')}; min_minutes={approval_ttl.get('min_remaining_minutes')}`",
        f"- Stable stage should change: `{report.get('locks', {}).get('stable_stage_should_change')}`",
        f"- Right-bottom promotion blocked: `{report.get('locks', {}).get('right_bottom_promotion_blocked')}`",
        "",
        "## Hidden Runtime Command" if hidden else "## Approval-Gated Execute Command",
        "",
        "```powershell",
        str(report.get("recommended_runtime_command") or ""),
        "```",
    ]
    invocation = report.get("invocation") or {}
    lines.extend(
        [
            "",
            "## Invocation",
            "",
            f"- Used fixture plan: `{invocation.get('used_fixture_plan')}`",
            f"- Exit code: `{invocation.get('exit_code')}`",
            f"- Command: `{invocation.get('command')}`",
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
    parser.add_argument("--step-status-json", type=Path, default=DEFAULT_STEP_STATUS_JSON)
    parser.add_argument("--script", type=Path, help="harness override; must match the current environment")
    parser.add_argument("--read-plan-json", type=Path)
    parser.add_argument("--write-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--write-markdown", "--write-md", dest="write_markdown", type=Path, default=DEFAULT_MD)
    parser.add_argument("--require-pass", action="store_true")
    args = parser.parse_args()

    report = build_report(args)
    write_outputs(report, args.write_json, args.write_markdown)
    print(f"overall: {status_text(bool(report['passed']))}")
    print(f"runtime-policy: {report['runtime_policy']}")
    print(f"status: {report.get('status')}")
    print(f"current-step: {(report.get('current_step') or {}).get('id')}")
    if report["failures"]:
        print("failures:")
        for failure in report["failures"]:
            print(f"  - {failure}")
    if args.require_pass and not report["passed"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
