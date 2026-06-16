#!/usr/bin/env python3
"""Build the approval-gated manual DirectInput run plan.

This is repo-only planning. It reads the current manual checklist and proof
template reports, then emits command templates for a future approved visible
runtime pass. It does not run PowerShell, launch Clash95, launch CDB, move the
mouse, or open visible windows.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import manual_directinput_checklist
import manual_directinput_proof_template


DEFAULT_CHECKLIST_JSON = manual_directinput_checklist.DEFAULT_JSON
DEFAULT_TEMPLATE_REPORT_JSON = manual_directinput_proof_template.DEFAULT_JSON
DEFAULT_JSON = Path("captures/current/manual-directinput-run-plan-current.json")
DEFAULT_MD = Path("captures/current/manual-directinput-run-plan-current.md")
DEFAULT_VISUAL_SMOKE_SCRIPT = Path("scripts/smoke/run_clash_visual_smoke.ps1")
DEFAULT_BATTLE_VISIBLE_SCRIPT = Path("scripts/cdb/run_cdb_battle_visible_input_probe.ps1")
DEFAULT_CHECKLIST_SCRIPT = Path("tools/manual_directinput_checklist.py")
DEFAULT_PROOF_JSON = Path("captures/current/manual-directinput-proof-current.json")

RUNTIME_POLICY = (
    "repo-only command planner; reads generated JSON and writes JSON/Markdown reports; "
    "does not run PowerShell, launch Clash95, CDB, wrappers, move the mouse, or open visible windows"
)
GUARD_POLICY = (
    "manual DirectInput commands remain templates until explicit user approval; every visible "
    "runtime command must carry -AllowVisibleRuntime and the proof manifest must be validated "
    "before promotion"
)
CANDIDATE_PATH_POLICY = (
    "candidate placeholders must resolve to freshly built, hashed executables under "
    f"{manual_directinput_checklist.EXPECTED_CANDIDATE_ROOT}; never use "
    f"{manual_directinput_checklist.FORBIDDEN_LIVE_ORIGINAL} or a repository-local executable"
)


COMMAND_SPECS: dict[str, dict[str, Any]] = {
    "stable_menu_load": {
        "candidate": r"C:\ClashTests\manual-directinput\<stable-hd-map-candidate-exe>",
        "script": DEFAULT_VISUAL_SMOKE_SCRIPT,
        "route": "load-slot0",
        "route_points": "300,218;320,166;400,226",
        "followup_points": "",
        "notes": "proves the centered menu load route and held-click cadence with real DirectInput",
    },
    "stable_hd_map_input": {
        "candidate": r"C:\ClashTests\manual-directinput\<stable-hd-map-candidate-exe>",
        "script": DEFAULT_VISUAL_SMOKE_SCRIPT,
        "route": "load-slot0",
        "route_points": "300,218;320,166;400,226",
        "followup_points": "400,300;780,300;400,580;760,560",
        "notes": "the command reaches gameplay through the load route; then manually exercise the listed map edge/minimap/selection points",
    },
    "right_bottom_validation_input": {
        "candidate": r"C:\ClashTests\manual-directinput\<rightbottomcompose-candidate-exe>",
        "script": DEFAULT_VISUAL_SMOKE_SCRIPT,
        "route": "load-slot0",
        "route_points": "300,218;320,166;400,226",
        "followup_points": "588,440;450,73;760,560",
        "notes": "the command reaches gameplay through the load route; then manually check the recovered lower/right action UI and displayed grid/action positions",
    },
    "castle_barracks_centered_input": {
        "candidate": r"C:\ClashTests\manual-directinput\<castlecenter-all-candidate-exe>",
        "script": DEFAULT_VISUAL_SMOKE_SCRIPT,
        "route": "load-slot0",
        "route_points": "300,218;320,166;400,226",
        "followup_points": "400,300;231,366;180,440",
        "notes": "the command reaches gameplay through the load route; then manually check centered barracks descriptor/action positions",
    },
    "castle_overview_centered_input": {
        "candidate": r"C:\ClashTests\manual-directinput\<castlecenter-all-candidate-exe>",
        "script": DEFAULT_VISUAL_SMOKE_SCRIPT,
        "route": "load-slot0",
        "route_points": "300,218;320,166;400,226",
        "followup_points": "231,366;180,440;503,426",
        "notes": "the command reaches gameplay through the load route; then manually check centered castle overview descriptors and callbacks",
    },
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def status_text(passed: bool) -> str:
    return "PASS" if passed else "FAIL"


def quote_ps(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def command_text(parts: list[str]) -> str:
    return " ".join(parts)


def visible_command(spec: dict[str, Any]) -> str:
    return command_text(
        [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            quote_ps(str(spec["script"])),
            "-Exe",
            quote_ps(str(spec["candidate"])),
            "-WorkDir",
            quote_ps(r"C:\Clash"),
            "-Route",
            quote_ps(str(spec["route"])),
            "-Points",
            quote_ps(str(spec["route_points"])),
            "-MoveMode",
            "auto",
            "-ClickMode",
            "sendinput",
            "-ClickHoldMs",
            "300",
            "-ClickRepeat",
            "2",
            "-AllowVisibleRuntime",
        ]
    )


def validate_proof_command(checklist_script: Path, proof_json: Path) -> str:
    return command_text(
        [
            "python",
            quote_ps(str(checklist_script)),
            "--manual-proof",
            quote_ps(str(proof_json)),
            "--require-pass",
            "--require-promotion-ready",
        ]
    )


def script_has_visible_guard(path: Path) -> bool:
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    return "[switch]$AllowVisibleRuntime" in text and "if (-not $AllowVisibleRuntime)" in text


def build_commands() -> dict[str, dict[str, Any]]:
    checklist_by_id = {
        item["id"]: item
        for item in manual_directinput_checklist.CHECKLIST_ITEMS
    }
    commands: dict[str, dict[str, Any]] = {}
    for item_id in manual_directinput_checklist.REQUIRED_IDS:
        spec = COMMAND_SPECS[item_id]
        commands[item_id] = {
            "title": checklist_by_id[item_id]["title"],
            "stage": checklist_by_id[item_id]["stage"],
            "script": str(spec["script"]),
            "candidate_placeholder": spec["candidate"],
            "candidate_path_policy": CANDIDATE_PATH_POLICY,
            "route": spec["route"],
            "route_points": spec["route_points"],
            "followup_points": spec["followup_points"],
            "requires_explicit_user_approval": True,
            "contains_allow_visible_runtime": True,
            "command": visible_command(spec),
            "notes": spec["notes"],
        }
    return commands


def build_plan(
    checklist_json: Path = DEFAULT_CHECKLIST_JSON,
    template_report_json: Path = DEFAULT_TEMPLATE_REPORT_JSON,
    *,
    visual_smoke_script: Path = DEFAULT_VISUAL_SMOKE_SCRIPT,
    battle_visible_script: Path = DEFAULT_BATTLE_VISIBLE_SCRIPT,
    checklist_script: Path = DEFAULT_CHECKLIST_SCRIPT,
    proof_json: Path = DEFAULT_PROOF_JSON,
) -> dict[str, Any]:
    failures: list[str] = []
    checklist: dict[str, Any] = {}
    template_report: dict[str, Any] = {}

    if not checklist_json.exists():
        failures.append(f"missing manual DirectInput checklist JSON: {checklist_json}")
    else:
        checklist = load_json(checklist_json)
    if not template_report_json.exists():
        failures.append(f"missing manual DirectInput proof template report JSON: {template_report_json}")
    else:
        template_report = load_json(template_report_json)

    if checklist and checklist.get("passed") is not True:
        failures.append("manual DirectInput checklist is not passing structurally")
    if checklist and checklist.get("visible_runtime_requires_approval") is not True:
        failures.append("manual DirectInput checklist does not require visible runtime approval")
    if checklist and checklist.get("manual_proof_valid") is True:
        failures.append("manual DirectInput proof is already valid; this planner should be superseded by proof validation")
    if checklist and checklist.get("promotion_ready") is True:
        failures.append("manual DirectInput checklist is unexpectedly promotion-ready")

    summary = checklist.get("summary") or {}
    pending_ids = list(summary.get("pending_ids") or [])
    missing_pending = [
        item_id
        for item_id in manual_directinput_checklist.REQUIRED_IDS
        if item_id not in pending_ids
    ]
    if checklist and missing_pending:
        failures.append(f"manual DirectInput checklist is missing pending IDs: {missing_pending}")

    if template_report and template_report.get("passed") is not True:
        failures.append("manual DirectInput proof template report is not passing")
    if template_report and template_report.get("template_valid_as_proof") is not False:
        failures.append("manual DirectInput proof template unexpectedly validates as proof")

    for script in (visual_smoke_script, battle_visible_script):
        if not script.exists():
            failures.append(f"missing guarded visible runtime script: {script}")
        elif not script_has_visible_guard(script):
            failures.append(f"visible runtime script is missing an AllowVisibleRuntime guard: {script}")
    if not checklist_script.exists():
        failures.append(f"missing manual proof validator script: {checklist_script}")

    commands = build_commands()
    for item_id in manual_directinput_checklist.REQUIRED_IDS:
        command = commands.get(item_id, {}).get("command", "")
        if not command:
            failures.append(f"missing command template for manual target: {item_id}")
        elif "-AllowVisibleRuntime" not in command:
            failures.append(f"manual target command lacks -AllowVisibleRuntime: {item_id}")
        candidate_placeholder = commands.get(item_id, {}).get("candidate_placeholder", "")
        if not manual_directinput_checklist._is_same_or_under(
            candidate_placeholder,
            manual_directinput_checklist.EXPECTED_CANDIDATE_ROOT,
        ):
            failures.append(
                f"manual target candidate placeholder is not under "
                f"{manual_directinput_checklist.EXPECTED_CANDIDATE_ROOT}: {item_id}"
            )
        if (
            manual_directinput_checklist._normalized_path_text(candidate_placeholder)
            == manual_directinput_checklist._normalized_path_text(
                manual_directinput_checklist.FORBIDDEN_LIVE_ORIGINAL
            )
        ):
            failures.append(
                f"manual target candidate placeholder points at the live original: {item_id}"
            )

    proof_validation = validate_proof_command(checklist_script, proof_json)
    prerequisites = [
        "user explicitly approves a visible/manual DirectInput validation pass",
        "candidate executable path placeholders are replaced with freshly built, hashed candidates",
        CANDIDATE_PATH_POLICY,
        "stale clash95*/cdb processes are killed and recorded before launching a visible runtime",
        "each manual target captures observed result, screenshot or notes, pass/fail notes, and no-crash status",
        "captures/current/manual-directinput-proof-current.json is filled from the approved run and validated before promotion",
    ]

    return {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "passed": not failures,
        "runtime_policy": RUNTIME_POLICY,
        "guard_policy": GUARD_POLICY,
        "candidate_path_policy": CANDIDATE_PATH_POLICY,
        "candidate_root": manual_directinput_checklist.EXPECTED_CANDIDATE_ROOT,
        "checklist_json": str(checklist_json),
        "template_report_json": str(template_report_json),
        "visible_runtime_guarded_scripts": [str(visual_smoke_script), str(battle_visible_script)],
        "proof_json_template": str(proof_json),
        "proof_ready": False,
        "visible_runtime_requires_approval": True,
        "manual_target_count": len(manual_directinput_checklist.REQUIRED_IDS),
        "commands": commands,
        "proof_validation_command": proof_validation,
        "runtime_prerequisites": prerequisites,
        "summary": {
            "pending_ids": pending_ids,
            "command_count": len(commands),
            "all_commands_have_allow_visible_runtime": all(
                "-AllowVisibleRuntime" in command.get("command", "")
                for command in commands.values()
            ),
            "template_valid_as_proof": template_report.get("template_valid_as_proof"),
            "manual_proof_valid": checklist.get("manual_proof_valid"),
            "promotion_ready": checklist.get("promotion_ready"),
        },
        "failures": failures,
    }


def write_markdown(path: Path, report: dict[str, Any]) -> None:
    summary = report.get("summary") or {}
    lines = [
        "# Manual DirectInput Run Plan",
        "",
        f"- Overall: {status_text(bool(report.get('passed')))}",
        f"- Generated: `{report['generated_at']}`",
        f"- Runtime policy: {report['runtime_policy']}",
        f"- Guard policy: {report['guard_policy']}",
        f"- Candidate path policy: {report['candidate_path_policy']}",
        f"- Candidate root: `{report['candidate_root']}`",
        f"- Visible runtime requires approval: `{report['visible_runtime_requires_approval']}`",
        f"- Proof ready: `{report['proof_ready']}`",
        f"- Manual target count: `{report['manual_target_count']}`",
        f"- All commands have -AllowVisibleRuntime: `{summary.get('all_commands_have_allow_visible_runtime')}`",
        f"- Manual proof valid: `{summary.get('manual_proof_valid')}`",
        f"- Promotion ready: `{summary.get('promotion_ready')}`",
        "",
        "## Commands",
        "",
    ]
    for item_id, item in report.get("commands", {}).items():
        lines.extend(
            [
                f"### {item['title']}",
                "",
                f"- ID: `{item_id}`",
                f"- Stage: `{item['stage']}`",
                f"- Candidate placeholder: `{item['candidate_placeholder']}`",
                f"- Candidate path policy: {item['candidate_path_policy']}",
                f"- Route: `{item['route']}`",
                f"- Load-route points: `{item['route_points']}`",
                f"- Follow-up manual points: `{item['followup_points'] or 'n/a'}`",
                f"- Notes: {item['notes']}",
                "",
                "```powershell",
                item["command"],
                "```",
                "",
            ]
        )
    lines.extend(
        [
            "## Proof Validation",
            "",
            "```powershell",
            report["proof_validation_command"],
            "```",
            "",
            "## Runtime Prerequisites",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in report.get("runtime_prerequisites") or [])
    if report.get("failures"):
        lines.extend(["", "## Failures", ""])
        lines.extend(f"- {failure}" for failure in report["failures"])
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checklist-json", type=Path, default=DEFAULT_CHECKLIST_JSON)
    parser.add_argument("--template-report-json", type=Path, default=DEFAULT_TEMPLATE_REPORT_JSON)
    parser.add_argument("--visual-smoke-script", type=Path, default=DEFAULT_VISUAL_SMOKE_SCRIPT)
    parser.add_argument("--battle-visible-script", type=Path, default=DEFAULT_BATTLE_VISIBLE_SCRIPT)
    parser.add_argument("--checklist-script", type=Path, default=DEFAULT_CHECKLIST_SCRIPT)
    parser.add_argument("--proof-json", type=Path, default=DEFAULT_PROOF_JSON)
    parser.add_argument("--write-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--write-markdown", "--write-md", dest="write_markdown", type=Path, default=DEFAULT_MD)
    parser.add_argument("--require-pass", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_plan(
        checklist_json=args.checklist_json,
        template_report_json=args.template_report_json,
        visual_smoke_script=args.visual_smoke_script,
        battle_visible_script=args.battle_visible_script,
        checklist_script=args.checklist_script,
        proof_json=args.proof_json,
    )
    print(f"overall: {status_text(bool(report.get('passed')))}")
    print(f"runtime-policy: {report['runtime_policy']}")
    print(f"manual-target-count: {report['manual_target_count']}")
    print(f"proof-ready: {report['proof_ready']}")
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
