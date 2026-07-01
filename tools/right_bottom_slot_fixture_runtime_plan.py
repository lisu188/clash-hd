#!/usr/bin/env python3
"""Build the hidden-desktop command plan for the right-bottom slot fixture.

This is repo-only planning. It reads the fixture plan and script guard reports,
then emits the exact preparation and CDB surface-dump commands a future runtime
pass should use. It does not run PowerShell, copy saves, launch CDB, or open
visible windows.
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path, PureWindowsPath
from typing import Any


DEFAULT_FIXTURE_PLAN_JSON = Path("captures/current/right-bottom-slot-fixture-plan-current.json")
DEFAULT_SCRIPT_GUARD_JSON = Path("captures/current/right-bottom-slot-fixture-script-guard-current.json")
DEFAULT_JSON = Path("captures/current/right-bottom-slot-fixture-runtime-plan-current.json")
DEFAULT_MD = Path("captures/current/right-bottom-slot-fixture-runtime-plan-current.md")
DEFAULT_SURFACE_DUMP_SCRIPT = Path("scripts/cdb/run_cdb_surface_dump.ps1")
DEFAULT_EXTRA_PROBE = Path("probes/cdb/castle/clash95_castle_cmd99_owner_action_descriptor_extra.cdb")
DEFAULT_RESULT_PARSER = Path("tools/right_bottom_slot_fixture_result_summary.py")
DEFAULT_STAGE = (
    "gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-"
    "minimapright-dynvswitch-rightbottomaction-nativecenter"
)
DEFAULT_RESULT_LOG = Path("captures/cdb-surface-dump-FIXTURE-RUN/cdb-surface-dump.log")
DEFAULT_RESULT_JSON = Path("captures/cdb-surface-dump-FIXTURE-RUN/right-bottom-slot-fixture-result-summary.json")
DEFAULT_RESULT_MD = Path("captures/cdb-surface-dump-FIXTURE-RUN/right-bottom-slot-fixture-result-summary.md")

RUNTIME_POLICY = (
    "repo-only command planner; reads generated JSON and writes JSON/Markdown reports; "
    "does not run PowerShell, copy saves, launch Clash95, CDB, wrappers, or visible windows"
)
GUARD_POLICY = (
    "passes only when the right-bottom slot fixture remains non-promoting, the dry-run "
    "preparation helper is source-guarded, and the future CDB command stays hidden-desktop "
    "with an isolated workdir/candidate dir"
)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def status_text(passed: bool) -> str:
    return "PASS" if passed else "FAIL"


def quote_ps(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def target_path(value: Any) -> Path | PureWindowsPath:
    # A drive-letter/UNC/backslash value is a Windows game-host path and must keep
    # backslash separators on any host; anything else is a normal local path.
    text = str(value)
    if PureWindowsPath(text).drive or "\\" in text:
        return PureWindowsPath(text)
    return Path(text)


def path_is_under(child: Path, parent: Path) -> bool:
    # Windows-target paths (drive-letter or UNC) describe the game host, not this
    # checkout; on a POSIX host they can never be under the repo root.
    child_win = PureWindowsPath(str(child))
    if child_win.drive or str(child).startswith("\\\\"):
        if os.name != "nt":
            return False
        try:
            child_win.relative_to(PureWindowsPath(str(Path(parent).resolve(strict=False))))
            return True
        except ValueError:
            return False
    try:
        Path(str(child)).resolve(strict=False).relative_to(Path(parent).resolve(strict=False))
        return True
    except ValueError:
        return False


def command_text(parts: list[str]) -> str:
    return " ".join(parts)


def build_plan(
    fixture_plan_json: Path = DEFAULT_FIXTURE_PLAN_JSON,
    script_guard_json: Path = DEFAULT_SCRIPT_GUARD_JSON,
    *,
    surface_dump_script: Path = DEFAULT_SURFACE_DUMP_SCRIPT,
    extra_probe: Path = DEFAULT_EXTRA_PROBE,
    result_parser: Path = DEFAULT_RESULT_PARSER,
    stage: str = DEFAULT_STAGE,
    repo_root: Path | None = None,
    run_seconds: int = 120,
) -> dict[str, Any]:
    repo_root = repo_root or Path.cwd()
    failures: list[str] = []
    fixture_report: dict[str, Any] = {}
    script_guard: dict[str, Any] = {}

    if not fixture_plan_json.exists():
        failures.append(f"missing fixture plan JSON: {fixture_plan_json}")
    else:
        fixture_report = load_json(fixture_plan_json)
    if not script_guard_json.exists():
        failures.append(f"missing script guard JSON: {script_guard_json}")
    else:
        script_guard = load_json(script_guard_json)
    if not surface_dump_script.exists():
        failures.append(f"missing surface-dump script: {surface_dump_script}")
    if not extra_probe.exists():
        failures.append(f"missing extra CDB probe: {extra_probe}")
    if not result_parser.exists():
        failures.append(f"missing result summary parser: {result_parser}")

    fixture_plan = fixture_report.get("plan") or {}
    # Windows-target paths: keep backslash separators regardless of host OS so the
    # emitted PowerShell commands are valid on the game host.
    fixture_root = target_path(fixture_plan.get("fixture_root") or r"C:\ClashTests\right-bottom-slot5-as-slot0-fixture")
    fixture_save = target_path(fixture_plan.get("fixture_save") or (fixture_root / "save" / "0.dat"))
    candidate_dir = fixture_root / "candidate"
    target_load_slot = int(fixture_plan.get("target_load_slot") or 0)

    if fixture_report and fixture_report.get("passed") is not True:
        failures.append("right-bottom slot fixture plan is not passing")
    if script_guard and script_guard.get("passed") is not True:
        failures.append("right-bottom slot fixture script guard is not passing")
    script_markers = script_guard.get("markers") or {}
    for marker in ("seed_workdir_switch", "seed_excludes_save_dir", "seed_workdir_copy"):
        if script_guard and script_markers.get(marker) is not True:
            failures.append(f"right-bottom slot fixture script guard is missing marker: {marker}")
    if fixture_plan.get("proof_class") != "non_natural_isolated_fixture":
        failures.append(f"unexpected fixture proof class: {fixture_plan.get('proof_class')}")
    if fixture_plan.get("promotion_ready") is not False:
        failures.append("fixture plan is unexpectedly promotion-ready")
    if fixture_plan.get("stable_stage_should_change") is not False:
        failures.append("fixture plan unexpectedly changes the stable stage")
    if target_load_slot != 0:
        failures.append(f"fixture target load slot is {target_load_slot}, expected 0")
    if path_is_under(fixture_root, repo_root):
        failures.append(f"fixture root is inside the repository: {fixture_root}")
    if str(candidate_dir).casefold() == str(fixture_root).casefold():
        failures.append("candidate dir must be a child of the fixture workdir, not the workdir itself")

    prepare_dry_run = command_text(
        [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            quote_ps(str(Path("scripts/smoke/prepare_right_bottom_slot_fixture.ps1"))),
            "-SeedWorkDir",
            "-Json",
        ]
    )
    prepare_execute = command_text(
        [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            quote_ps(str(Path("scripts/smoke/prepare_right_bottom_slot_fixture.ps1"))),
            "-SeedWorkDir",
            "-Execute",
        ]
    )
    hidden_probe = command_text(
        [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            quote_ps(str(surface_dump_script)),
            "-UseDdrawProxy",
            "-FastForwardStartAnims",
            "-SkipMapValidation",
            "-Stage",
            quote_ps(stage),
            "-WorkDir",
            quote_ps(str(fixture_root)),
            "-CandidateDir",
            quote_ps(str(candidate_dir)),
            "-LoadSlot",
            str(target_load_slot),
            "-ExtraProbeTemplate",
            quote_ps(str(extra_probe)),
            "-RunSeconds",
            str(run_seconds),
        ]
    )
    summarize_fixture_result = command_text(
        [
            "python",
            quote_ps(str(result_parser)),
            quote_ps(str(DEFAULT_RESULT_LOG)),
            "--expected-slot",
            str(target_load_slot),
            "--write-json",
            quote_ps(str(DEFAULT_RESULT_JSON)),
            "--write-md",
            quote_ps(str(DEFAULT_RESULT_MD)),
            "--require-load-success",
            "--require-slot-match",
            "--require-owner-bit2",
            "--require-owner-action",
        ]
    )

    commands = {
        "prepare_dry_run": prepare_dry_run,
        "prepare_execute": prepare_execute,
        "hidden_fixture_probe": hidden_probe,
        "summarize_fixture_result": summarize_fixture_result,
    }
    prerequisites = [
        "fixture root must be a complete isolated Clash95 working directory seeded outside the repository",
        "scripts/smoke/prepare_right_bottom_slot_fixture.ps1 seeds non-save children from C:\\Clash, then overlays only the route-compatible save as save\\0.dat",
        "scripts/cdb/run_cdb_surface_dump.ps1 must use the fixture root as -WorkDir so save\\0.dat is local to the fixture",
        "scripts/cdb/run_cdb_surface_dump.ps1 must use a child -CandidateDir so the DirectDraw proxy is not placed directly in the workdir",
        "right_bottom_slot_fixture_result_summary.py must keep selected_arg and selected_global consistent with expected slot 0",
        "the result remains non-natural fixture evidence until rows 3-5 naturally enter the load menu and LOADSAVE",
    ]
    expected_success_markers = [
        "SURFDUMP_LOADSAVE selected_arg=0 selected_global=0",
        "SURFDUMP_PLAYGAME",
        "NOWNER_OWNER_FLAG_TEST owner_flag has bit2 set",
        "NOWNER_4338E0_ENTRY or owner/action renderer rows",
        "fixture result summary status=owner_action_reached",
        "no AV_SURFDUMP rows",
    ]

    return {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "passed": not failures,
        "runtime_policy": RUNTIME_POLICY,
        "guard_policy": GUARD_POLICY,
        "fixture_plan_json": str(fixture_plan_json),
        "script_guard_json": str(script_guard_json),
        "surface_dump_script": str(surface_dump_script),
        "extra_probe": str(extra_probe),
        "result_parser": str(result_parser),
        "summary": {
            "proof_class": fixture_plan.get("proof_class"),
            "promotion_ready": fixture_plan.get("promotion_ready"),
            "stable_stage_should_change": fixture_plan.get("stable_stage_should_change"),
            "fixture_root": str(fixture_root),
            "fixture_save": str(fixture_save),
            "candidate_dir": str(candidate_dir),
            "target_load_slot": target_load_slot,
            "prepare_seed_workdir": True,
            "stage": stage,
            "run_seconds": run_seconds,
            "result_log_template": str(DEFAULT_RESULT_LOG),
            "result_json_template": str(DEFAULT_RESULT_JSON),
            "result_md_template": str(DEFAULT_RESULT_MD),
        },
        "commands": commands,
        "runtime_prerequisites": prerequisites,
        "expected_success_markers": expected_success_markers,
        "failures": failures,
    }


def write_markdown(path: Path, report: dict[str, Any]) -> None:
    summary = report.get("summary") or {}
    lines = [
        "# Right-Bottom Slot Fixture Runtime Plan",
        "",
        f"- Status: {status_text(bool(report.get('passed')))}",
        f"- Generated: `{report['generated_at']}`",
        f"- Runtime policy: {report['runtime_policy']}",
        f"- Guard policy: {report['guard_policy']}",
        f"- Fixture plan: `{report['fixture_plan_json']}`",
        f"- Script guard: `{report['script_guard_json']}`",
        f"- Surface-dump script: `{report['surface_dump_script']}`",
        f"- Extra probe: `{report['extra_probe']}`",
        f"- Result parser: `{report['result_parser']}`",
        "",
        "## Summary",
        "",
        f"- Proof class: `{summary.get('proof_class')}`",
        f"- Promotion ready: `{summary.get('promotion_ready')}`",
        f"- stable_stage_should_change: `{summary.get('stable_stage_should_change')}`",
        f"- Fixture root: `{summary.get('fixture_root')}`",
        f"- Fixture save: `{summary.get('fixture_save')}`",
        f"- Candidate dir: `{summary.get('candidate_dir')}`",
        f"- Target load slot: `{summary.get('target_load_slot')}`",
        f"- Prepare seed workdir: `{summary.get('prepare_seed_workdir')}`",
        f"- Stage: `{summary.get('stage')}`",
        f"- Result log template: `{summary.get('result_log_template')}`",
        f"- Result JSON template: `{summary.get('result_json_template')}`",
        f"- Result Markdown template: `{summary.get('result_md_template')}`",
        "",
        "## Commands",
        "",
    ]
    for name, command in report.get("commands", {}).items():
        lines.extend([f"### {name}", "", "```powershell", command, "```", ""])
    lines.extend(["## Runtime Prerequisites", ""])
    lines.extend(f"- {item}" for item in report.get("runtime_prerequisites") or [])
    lines.extend(["", "## Expected Success Markers", ""])
    lines.extend(f"- `{item}`" for item in report.get("expected_success_markers") or [])
    if report.get("failures"):
        lines.extend(["", "## Failures", ""])
        lines.extend(f"- {failure}" for failure in report["failures"])
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture-plan-json", type=Path, default=DEFAULT_FIXTURE_PLAN_JSON)
    parser.add_argument("--script-guard-json", type=Path, default=DEFAULT_SCRIPT_GUARD_JSON)
    parser.add_argument("--surface-dump-script", type=Path, default=DEFAULT_SURFACE_DUMP_SCRIPT)
    parser.add_argument("--extra-probe", type=Path, default=DEFAULT_EXTRA_PROBE)
    parser.add_argument("--result-parser", type=Path, default=DEFAULT_RESULT_PARSER)
    parser.add_argument("--stage", default=DEFAULT_STAGE)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--run-seconds", type=int, default=120)
    parser.add_argument("--write-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--write-markdown", "--write-md", dest="write_markdown", type=Path, default=DEFAULT_MD)
    parser.add_argument("--require-pass", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_plan(
        fixture_plan_json=args.fixture_plan_json,
        script_guard_json=args.script_guard_json,
        surface_dump_script=args.surface_dump_script,
        extra_probe=args.extra_probe,
        result_parser=args.result_parser,
        stage=args.stage,
        repo_root=args.repo_root,
        run_seconds=args.run_seconds,
    )
    print(f"overall: {status_text(bool(report.get('passed')))}")
    print(f"runtime-policy: {report['runtime_policy']}")
    print(f"proof-class: {report['summary'].get('proof_class')}")
    print(f"fixture-root: {report['summary'].get('fixture_root')}")
    print(f"candidate-dir: {report['summary'].get('candidate_dir')}")
    if report["failures"]:
        print("failures:")
        for failure in report["failures"]:
            print(f"  - {failure}")
    if args.write_json:
        args.write_json.parent.mkdir(parents=True, exist_ok=True)
        args.write_json.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if args.write_markdown:
        write_markdown(args.write_markdown, report)
    if args.require_pass and not report["passed"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
