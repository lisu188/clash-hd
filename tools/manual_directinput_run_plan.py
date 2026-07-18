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
DEFAULT_PULSE_TOOL = Path("tools/menu_pulse_click.py")
DEFAULT_PROOF_JSON = Path("captures/current/manual-directinput-proof-current.json")

RUNTIME_POLICY = (
    "repo-only command planner; reads generated JSON and writes JSON/Markdown reports; "
    "does not run PowerShell, launch Clash95, CDB, wrappers, move the mouse, or open visible windows"
)
GUARD_POLICY = (
    "manual DirectInput commands remain templates until explicit user approval; every visible "
    "runtime command must carry -AllowVisibleRuntime and the proof manifest must be validated "
    "before promotion; the visible harness window must use the safe desktop offset so "
    "lower/right 800x600 client targets are not cursor-clamped"
)
ENGINE_INPUT_POLICY = (
    "the game reads mouse position from the DirectInput accumulator, not the OS cursor, so "
    "SetCursorPos/absolute-SendInput moves are invisible to its hit test; every menu, map, and "
    "follow-up click in this plan is driven by pulse-mode relative injection through "
    "tools/menu_pulse_click.py with frame-diff engine-cursor feedback and per-point aim error"
)
CANDIDATE_PATH_POLICY = (
    "candidate placeholders must resolve to freshly built, hashed executables under "
    f"{manual_directinput_checklist.EXPECTED_CANDIDATE_ROOT}; never use "
    f"{manual_directinput_checklist.FORBIDDEN_LIVE_ORIGINAL} or a repository-local executable"
)
# The approved 2026-07-13 wrapper run measured a (3,26) non-client offset on
# the 800x600 logical desktop.  Moving the outer window to (0,-30) keeps the
# full logical client, including x=780/y=580 proof points, inside 0..799/0..599.
SAFE_MOVE_WINDOW_ORIGIN = (0, -30)

# 2026-07-17 diagnosis (commit 589f5700): the menu and map read the mouse from
# the DirectInput ACCUMULATOR, not the OS cursor.  Every -MoveMode the visual
# smoke harness historically offered (setcursor / sendinput-absolute) is
# invisible to the engine hit test, so the previously prescribed
# "-MoveMode auto -ClickMode sendinput" commands verified OS-cursor placement
# while the engine cursor never moved and no click was ever registered.  The
# route and the per-target follow-up points therefore run through
# tools/menu_pulse_click.py: one relative MOUSEEVENTF_MOVE per ~28ms input
# poll, frame-diff engine-cursor feedback, button held while pulsing.
INPUT_MODE = "pulse"
# What the plan is allowed to emit, checked independently of INPUT_MODE so a
# regression back to an OS-cursor lane fails the plan instead of relabelling it.
REQUIRED_INPUT_MODE_FLAG = "-InputMode pulse"
ENGINE_INPUT_MECHANISM = "pulse-relative-engine-aim"
DI_INVISIBLE_MOVE_MODES = ("setcursor", "sendinput-absolute", "auto")
# Engine-space load route.  The centered main-menu Load ellipse centre was
# measured at 302,211 on 2026-07-17; the historic 300,218 was an OS-cursor-era
# approximation.  Slot/confirm targets come from the menu load route notes.
PULSE_ROUTE_STEPS = "load-button:302,211;load-slot0:320,166;confirm-load:400,226"
INTRO_VERIFY_ROUNDS = 12
PULSE_AIM_TOLERANCE_PX = 10
# Castle-entry click point.  UNVERIFIED PROVENANCE - do not describe this as
# proven real-runtime evidence.  It was originally taken from captures/archive/
# manual-barracks-entry/click-castle.json plus the 2026-07-12 manual session
# (now captures/archive/manual-visible-session-2026-07-12.md, banner-marked
# SUPERSEDED), which claimed a real click at client (470,397) entered the
# slot-0 "Stormus" castle overview.  a07ea061 refuted that reading: those
# clicks used move_method=setcursor with logical_delta [0,0], so the engine's
# DirectInput accumulator never moved (root cause fixed in 589f5700), that
# session never loaded the save, and "Stormus" is an exe-resident scenario
# default name rather than the slot-0 owner record.  (470,397) is therefore a
# plausible starting aim point awaiting a pulse-mode re-verification, not a
# documented result.  The castle targets still need some entry click before any
# overview descriptor point is reachable; the load route only reaches the map.
CASTLE_ENTRY_POINT = "castle-entry:470,397"


COMMAND_SPECS: dict[str, dict[str, Any]] = {
    "stable_menu_load": {
        "candidate": r"C:\ClashTests\manual-directinput\<stable-hd-map-candidate-exe>",
        "script": DEFAULT_VISUAL_SMOKE_SCRIPT,
        "route": "load-slot0",
        "route_points": "300,218;320,166;400,226",
        "pulse_route_steps": PULSE_ROUTE_STEPS,
        "followup_points": "",
        "notes": (
            "proves the centered menu load route and held-click cadence against the engine's "
            "DirectInput accumulator; the harness gates on a verified menu fingerprint, an "
            "engine-cursor liveness probe, and per-step aim error plus frame transition"
        ),
    },
    "stable_hd_map_input": {
        "candidate": r"C:\ClashTests\manual-directinput\<stable-hd-map-candidate-exe>",
        "script": DEFAULT_VISUAL_SMOKE_SCRIPT,
        "route": "load-slot0",
        "route_points": "300,218;320,166;400,226",
        "pulse_route_steps": PULSE_ROUTE_STEPS,
        "followup_points": (
            "map-center:400,300;map-right-edge:780,300;map-bottom:400,580;minimap-right-bottom:760,560"
        ),
        "notes": (
            "the command reaches gameplay through the pulse load route, then aims and clicks each "
            "map edge/minimap/selection point with engine-cursor feedback; per-point aim error and "
            "frame delta are recorded, and edge-scroll behaviour still needs a human read of the frames"
        ),
    },
    "right_bottom_validation_input": {
        "candidate": r"C:\ClashTests\manual-directinput\<rightbottomcompose-candidate-exe>",
        "script": DEFAULT_VISUAL_SMOKE_SCRIPT,
        "route": "load-slot0",
        "route_points": "300,218;320,166;400,226",
        "pulse_route_steps": PULSE_ROUTE_STEPS,
        "followup_points": "action-ui:588,440;grid-hit:450,73;minimap-right-bottom:760,560",
        "notes": (
            "the command reaches gameplay through the pulse load route, then aims the recovered "
            "lower/right action UI and the controlled native (450,73) grid-hit position; needs the "
            "slot5-as-slot0 right-bottom fixture staged so the owner/action descriptors exist"
        ),
    },
    "castle_barracks_centered_input": {
        "candidate": r"C:\ClashTests\manual-directinput\<castlecenter-all-candidate-exe>",
        "script": DEFAULT_VISUAL_SMOKE_SCRIPT,
        "route": "load-slot0",
        "route_points": "300,218;320,166;400,226",
        "pulse_route_steps": PULSE_ROUTE_STEPS,
        "followup_points": f"{CASTLE_ENTRY_POINT};castle-0x63:231,366;barracks-0x86:398,228",
        "notes": (
            "BARRACKS COORDINATE RESOLVED (2026-07-18): the live slot-0 castle DOES present "
            "command 0x86 (21906 hitmap pixels, native bbox [175,47,455,223]). The earlier "
            "'no known coordinate / different castle layout' claim was a misdiagnosis: the "
            "committed hitmap is the live save's own castle (owner record 0, 'Drakefly', map "
            "pos 14,20 - 'Stormus' is an exe-resident scenario default name, not this record), "
            "and the 2026-07-12 miss happened because that session never loaded the save at all "
            "(SetCursorPos moved only the OS cursor, never the DirectInput accumulator - the bug "
            "fixed in 589f5700), so a default scenario with a different castle was on screen. "
            "Displayed (371,107) is evidence-backed twice on hidden slot-0 runs "
            "(cdb-surface-dump-20260712-144245 multihit and -144151 hitbox: raw 0xF8 -> command "
            "0x86 -> callback 0044FE70, gate 1) but sits on the bbox top edge with ~1px "
            "clearance (75/289 of a +/-8px box). This command therefore aims (398,228) = native "
            "(318,168), the same region's interior with ~37px clearance (289/289 of a +/-8px "
            "box), derived statically from the committed hitmap raw and NOT yet live "
            "hit-tested - if it misses, fall back to the proven (371,107). The remaining work "
            "for this target is executing the 0044FE70 callback (hidden probes deliberately "
            "suppress it), not discovering a coordinate"
        ),
    },
    "castle_overview_centered_input": {
        "candidate": r"C:\ClashTests\manual-directinput\<castlecenter-all-candidate-exe>",
        "script": DEFAULT_VISUAL_SMOKE_SCRIPT,
        "route": "load-slot0",
        "route_points": "300,218;320,166;400,226",
        "pulse_route_steps": PULSE_ROUTE_STEPS,
        "followup_points": (
            f"{CASTLE_ENTRY_POINT};castle-0x63:231,366;owner-action:180,440;overview-0x87:503,426"
        ),
        "notes": (
            "the command reaches gameplay through the pulse load route, enters the castle overview "
            "at the documented real-runtime (470,397) click, then aims the centered overview "
            "descriptors; 231,366 is the 0x63 displayed coordinate that a fixture run already "
            "recorded as sampling 0x0c rather than the descriptor, and 503,426 has no hitmap "
            "evidence behind it, so both need frame confirmation before being reported as hits"
        ),
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
    parts = [
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
        # The engine-visible lane. -MoveMode/-ClickMode below still drive the
        # intro-skip stimuli (mouse_path_probe space pulses and clicks, which
        # the intro does consume); the menu/map route and every follow-up
        # point go through the pulse engine-aim path instead.
        "-InputMode",
        INPUT_MODE,
        "-PulseRouteSteps",
        quote_ps(str(spec["pulse_route_steps"])),
    ]
    if spec.get("followup_points"):
        parts += ["-FollowupPoints", quote_ps(str(spec["followup_points"]))]
    parts += [
        "-PulseAimTolerancePx",
        str(PULSE_AIM_TOLERANCE_PX),
        "-IntroMaxRounds",
        str(INTRO_VERIFY_ROUNDS),
        "-MoveMode",
        "auto",
        "-ClickMode",
        "sendinput",
        "-ClickHoldMs",
        "300",
        "-ClickRepeat",
        "2",
        "-MoveWindowX",
        str(SAFE_MOVE_WINDOW_ORIGIN[0]),
        "-MoveWindowY",
        str(SAFE_MOVE_WINDOW_ORIGIN[1]),
        "-AllowVisibleRuntime",
    ]
    return command_text(parts)


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


def script_supports_pulse_input(path: Path) -> bool:
    """The harness must actually expose the engine-visible pulse lane.

    Without this the emitted commands would silently fall back to the
    DI-invisible OS-cursor path that never registered a click.
    """
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    return all(
        token in text
        for token in ("$InputMode", "'pulse'", "$PulseRouteSteps", "$FollowupPoints", "menu_pulse_click.py")
    )


def pulse_tool_supports_aim_points(path: Path) -> bool:
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    return "--aim-points" in text and "--probe-only" in text


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
            "pulse_route_steps": spec["pulse_route_steps"],
            "followup_points": spec["followup_points"],
            "input_mode": INPUT_MODE,
            "engine_input_mechanism": ENGINE_INPUT_MECHANISM,
            "aim_tolerance_px": PULSE_AIM_TOLERANCE_PX,
            "intro_verify_rounds": INTRO_VERIFY_ROUNDS,
            "move_window_origin": list(SAFE_MOVE_WINDOW_ORIGIN),
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
    pulse_tool: Path = DEFAULT_PULSE_TOOL,
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
    if not script_supports_pulse_input(visual_smoke_script):
        failures.append(
            f"visible runtime script does not expose the engine-visible pulse input lane "
            f"(-InputMode pulse / -PulseRouteSteps / -FollowupPoints): {visual_smoke_script}"
        )
    if not pulse_tool.exists():
        failures.append(f"missing engine-aim pulse tool: {pulse_tool}")
    elif not pulse_tool_supports_aim_points(pulse_tool):
        failures.append(
            f"engine-aim pulse tool lacks the --aim-points/--probe-only modes the plan relies on: {pulse_tool}"
        )

    commands = build_commands()
    for item_id in manual_directinput_checklist.REQUIRED_IDS:
        command = commands.get(item_id, {}).get("command", "")
        if not command:
            failures.append(f"missing command template for manual target: {item_id}")
        elif "-AllowVisibleRuntime" not in command:
            failures.append(f"manual target command lacks -AllowVisibleRuntime: {item_id}")
        if "-MoveWindowX 0 -MoveWindowY -30" not in command:
            failures.append(
                f"manual target command lacks the safe (0,-30) window offset: {item_id}"
            )
        if REQUIRED_INPUT_MODE_FLAG not in command:
            failures.append(
                f"manual target command does not select the engine-visible pulse input mode: {item_id}"
            )
        if "-PulseRouteSteps" not in command:
            failures.append(f"manual target command lacks pulse route steps: {item_id}")
        expected_followup = COMMAND_SPECS[item_id].get("followup_points") or ""
        if expected_followup and "-FollowupPoints" not in command:
            failures.append(
                f"manual target command lacks the pulse follow-up validation points: {item_id}"
            )
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
        "the harness uses -MoveWindowX 0 -MoveWindowY -30 so the measured (3,26) non-client offset still leaves 800x600 lower/right client points inside the active desktop instead of cursor-clamping them",
        "each manual target captures observed result, screenshot or notes, pass/fail notes, and no-crash status",
        "captures/current/manual-directinput-proof-current.json is filled from the approved run and validated before promotion",
        "-InputMode pulse is used for every target: the engine reads the DirectInput accumulator, so setcursor/absolute moves never reach its hit test and any run without the pulse lane proves nothing about clicks",
        "each run reports IntroMenuVerified and CursorProbeAlive before trusting a route; a run that never verified the menu fingerprint or never woke the engine cursor is a failed run, not a failed build",
        "the pulse lane is automated-but-real OS SendInput; evidence_class stays manual_directinput only if the operator genuinely witnessed the run, and the harness-side proof class stays automated_visible_runtime_engine_aim_evidence",
        "castle targets need the documented real-runtime castle-entry click (470,397) before any overview descriptor point is reachable; the load route only reaches the map",
        "castle_barracks_centered_input aims the resolved barracks descriptor 0x86 at displayed (398,228); the 2026-07-12 miss at (371,107) is explained (that session never loaded the save - SetCursorPos never moved the DirectInput accumulator, fixed in 589f5700), and (371,107) itself is the evidence-backed fallback. Record this target as passing only if the run's own frames show the barracks build sub-screen actually entered (the 0044FE70 callback executing), not merely a click at the coordinate",
        "right_bottom_validation_input needs the slot5-as-slot0 right-bottom fixture staged (scripts/smoke/prepare_right_bottom_slot_fixture.ps1) so owner/action descriptors exist to hit",
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
        "input_mode": INPUT_MODE,
        "engine_input_mechanism": ENGINE_INPUT_MECHANISM,
        "engine_input_policy": ENGINE_INPUT_POLICY,
        "di_invisible_move_modes": list(DI_INVISIBLE_MOVE_MODES),
        "pulse_tool": str(pulse_tool),
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
            "all_commands_have_safe_window_origin": all(
                "-MoveWindowX 0 -MoveWindowY -30" in command.get("command", "")
                and command.get("move_window_origin") == [0, -30]
                for command in commands.values()
            ),
            "all_commands_use_pulse_input_mode": all(
                REQUIRED_INPUT_MODE_FLAG in command.get("command", "")
                and "-PulseRouteSteps" in command.get("command", "")
                for command in commands.values()
            ),
            "followup_point_targets": [
                item_id
                for item_id, command in commands.items()
                if command.get("followup_points")
            ],
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
        f"- Engine input policy: {report['engine_input_policy']}",
        f"- Input mode: `{report['input_mode']}` (mechanism `{report['engine_input_mechanism']}`, tool `{report['pulse_tool']}`)",
        f"- DirectInput-invisible move modes (never sufficient alone): `{', '.join(report['di_invisible_move_modes'])}`",
        f"- Candidate path policy: {report['candidate_path_policy']}",
        f"- Candidate root: `{report['candidate_root']}`",
        f"- Visible runtime requires approval: `{report['visible_runtime_requires_approval']}`",
        f"- Proof ready: `{report['proof_ready']}`",
        f"- Manual target count: `{report['manual_target_count']}`",
        f"- All commands have -AllowVisibleRuntime: `{summary.get('all_commands_have_allow_visible_runtime')}`",
        f"- All commands use safe window offset (0,-30): `{summary.get('all_commands_have_safe_window_origin')}`",
        f"- All commands use the engine-visible pulse input mode: `{summary.get('all_commands_use_pulse_input_mode')}`",
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
                f"- Load-route points (legacy record): `{item['route_points']}`",
                f"- Pulse engine-aim route steps: `{item['pulse_route_steps']}`",
                f"- Follow-up pulse aim points: `{item['followup_points'] or 'n/a'}`",
                f"- Input mode: `{item['input_mode']}` / `{item['engine_input_mechanism']}`",
                f"- Aim tolerance px: `{item['aim_tolerance_px']}`",
                f"- Intro verify rounds: `{item['intro_verify_rounds']}`",
                f"- Safe window origin: `{item['move_window_origin']}`",
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
    parser.add_argument("--pulse-tool", type=Path, default=DEFAULT_PULSE_TOOL)
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
        pulse_tool=args.pulse_tool,
        proof_json=args.proof_json,
    )
    print(f"overall: {status_text(bool(report.get('passed')))}")
    print(f"runtime-policy: {report['runtime_policy']}")
    print(f"input-mode: {report['input_mode']} ({report['engine_input_mechanism']})")
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
