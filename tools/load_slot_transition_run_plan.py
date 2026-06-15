#!/usr/bin/env python3
"""Build a no-popup command plan for the blocked load-slot transition.

Rows 3-5 currently reach early load-coordinate rows but stop before the real
0044895A load-menu entry. This planner emits hidden-desktop command templates
for a future CDB pass that late-arms the transition probe after the main Load
callback. It does not run PowerShell, CDB, Clash95, wrappers, or visible
windows.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_ENTRY_GAP_JSON = Path("captures/current/load-slot-entry-gap-current.json")
DEFAULT_PROBE_GUARD_JSON = Path("captures/current/load-slot-transition-probe-guard-current.json")
DEFAULT_JSON = Path("captures/current/load-slot-transition-run-plan-current.json")
DEFAULT_MD = Path("captures/current/load-slot-transition-run-plan-current.md")
DEFAULT_SURFACE_DUMP_SCRIPT = Path("scripts/cdb/run_cdb_surface_dump.ps1")
DEFAULT_EXTRA_PROBE = Path("probes/cdb/menu/clash95_load_slot_entry_transition_extra.cdb")
DEFAULT_RESULT_PARSER = Path("tools/load_slot_transition_summary.py")
DEFAULT_STAGE = (
    "gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-"
    "minimapright-dynvswitch-castlecenter-all-battlecenter"
)
DEFAULT_CANDIDATE_ROOT = Path(r"C:\ClashTests\load-slot-transition")
DEFAULT_RESULT_ROOT = Path("captures/cdb-surface-dump-TRANSITION-RUN")

RUNTIME_POLICY = (
    "repo-only command planner; reads generated JSON and writes JSON/Markdown reports; "
    "does not run PowerShell, launch Clash95, CDB, wrappers, or visible windows"
)
GUARD_POLICY = (
    "passes only when rows 3-5 remain blocked before 0044895A, the transition "
    "probe guard is passing, and every future command stays hidden-desktop and "
    "non-promoting"
)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def status_text(passed: bool) -> str:
    return "PASS" if passed else "FAIL"


def quote_ps(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def command_text(parts: list[str]) -> str:
    return " ".join(parts)


def path_is_under(child: Path, parent: Path) -> bool:
    try:
        child.resolve(strict=False).relative_to(parent.resolve(strict=False))
        return True
    except ValueError:
        return False


def _load_report(path: Path, label: str, failures: list[str]) -> dict[str, Any]:
    if not path.exists():
        failures.append(f"missing {label}: {path}")
        return {}
    return load_json(path)


def _blocked_rows(entry_gap: dict[str, Any]) -> list[int]:
    summary = entry_gap.get("summary") or {}
    return sorted(int(row) for row in (summary.get("blocked_rows") or []))


def _make_probe_command(
    *,
    slot: int,
    stage: str,
    surface_dump_script: Path,
    extra_probe: Path,
    candidate_root: Path,
    run_seconds: int,
) -> str:
    return command_text(
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
            "-LateLoadSlotForcingOnly",
            "-Stage",
            quote_ps(stage),
            "-CandidateDir",
            quote_ps(str(candidate_root / f"slot{slot}")),
            "-LoadSlot",
            str(slot),
            "-ExtraProbeTemplate",
            quote_ps(str(extra_probe)),
            "-RunSeconds",
            str(run_seconds),
        ]
    )


def _make_summary_command(
    *,
    slot: int,
    result_parser: Path,
    result_root: Path,
) -> str:
    run_root = result_root / f"slot{slot}"
    return command_text(
        [
            "python",
            quote_ps(str(result_parser)),
            quote_ps(str(run_root / "cdb-surface-dump.log")),
            "--expected-slot",
            str(slot),
            "--write-json",
            quote_ps(str(run_root / "load-slot-transition-summary.json")),
            "--write-md",
            quote_ps(str(run_root / "load-slot-transition-summary.md")),
            "--require-entry",
            "--require-slot-match",
        ]
    )


def build_plan(
    *,
    entry_gap_json: Path = DEFAULT_ENTRY_GAP_JSON,
    probe_guard_json: Path = DEFAULT_PROBE_GUARD_JSON,
    surface_dump_script: Path = DEFAULT_SURFACE_DUMP_SCRIPT,
    extra_probe: Path = DEFAULT_EXTRA_PROBE,
    result_parser: Path = DEFAULT_RESULT_PARSER,
    stage: str = DEFAULT_STAGE,
    candidate_root: Path = DEFAULT_CANDIDATE_ROOT,
    result_root: Path = DEFAULT_RESULT_ROOT,
    repo_root: Path | None = None,
    run_seconds: int = 120,
) -> dict[str, Any]:
    repo_root = repo_root or Path.cwd()
    failures: list[str] = []
    entry_gap = _load_report(entry_gap_json, "load-slot entry gap", failures)
    probe_guard = _load_report(probe_guard_json, "load-slot transition probe guard", failures)

    if not surface_dump_script.exists():
        failures.append(f"missing surface-dump script: {surface_dump_script}")
    if not extra_probe.exists():
        failures.append(f"missing transition extra probe: {extra_probe}")
    if not result_parser.exists():
        failures.append(f"missing transition result parser: {result_parser}")

    rows = _blocked_rows(entry_gap)
    if entry_gap and entry_gap.get("passed") is not True:
        failures.append("load-slot entry gap report is not passing")
    if entry_gap and entry_gap.get("promotion_ready") is not False:
        failures.append("load-slot entry gap is unexpectedly promotion-ready")
    if entry_gap and entry_gap.get("gap_classification") != "after_main_load_callback_before_load_menu_case_entry":
        failures.append(f"unexpected gap classification: {entry_gap.get('gap_classification')}")
    if rows != [3, 4, 5]:
        failures.append(f"blocked rows are {rows}, expected [3, 4, 5]")

    probe_summary = probe_guard.get("summary") or {}
    if probe_guard and probe_guard.get("passed") is not True:
        failures.append("load-slot transition probe guard is not passing")
    if probe_summary.get("late_entry_breakpoint") != "0044895A":
        failures.append("transition probe guard does not target 0044895A as the late entry breakpoint")
    if probe_summary.get("early_descriptor_breakpoint_avoided") is not True:
        failures.append("transition probe guard no longer avoids early descriptor forcing")
    if probe_summary.get("slot_conditions_parameterized") is not True:
        failures.append("transition probe guard no longer proves late select/accept are parameterized by target slot")
    if probe_summary.get("extra_probe_placeholders_replaced") is not True:
        failures.append("surface-dump runner no longer replaces transition extra-probe placeholders")
    if probe_summary.get("late_load_slot_forcing_only_supported") is not True:
        failures.append("surface-dump runner no longer supports disabling pre-0044895A load-slot forcing")
    if path_is_under(candidate_root, repo_root):
        failures.append(f"candidate root is inside the repository: {candidate_root}")

    probe_commands = {
        f"slot{slot}_hidden_transition_probe": _make_probe_command(
            slot=slot,
            stage=stage,
            surface_dump_script=surface_dump_script,
            extra_probe=extra_probe,
            candidate_root=candidate_root,
            run_seconds=run_seconds,
        )
        for slot in rows
    }
    summary_commands = {
        f"slot{slot}_summarize_transition": _make_summary_command(
            slot=slot,
            result_parser=result_parser,
            result_root=result_root,
        )
        for slot in rows
    }
    all_command_text = "\n".join([*probe_commands.values(), *summary_commands.values()])
    if "-AllowVisibleDesktop" in all_command_text or "-AllowVisibleRuntime" in all_command_text:
        failures.append("future transition command unexpectedly allows visible runtime")
    if "-Execute" in all_command_text:
        failures.append("transition run plan unexpectedly contains an execute/copy switch")

    expected_markers = [
        "LSTRANS_LOAD_CALLBACK_ENTRY",
        "LSTRANS_AFTER_MAIN_CALLBACK",
        "LSTRANS_MAIN_WAIT_GATE",
        "LSTRANS_WAIT_LOOP_PUMP",
        "LSTRANS_WAIT_LOOP_COMPARE",
        "LSTRANS_WAIT_LOOP_EXIT",
        "LSTRANS_MAIN_SWITCH_DISPATCH",
        "LSTRANS_MAIN_DISPATCH_POLL",
        "LSTRANS_LOAD_MENU_ENTRY",
        "LSTRANS_LATE_MOUSE_SET",
        "LSTRANS_LOAD_SLOT_DRAW",
        "LSTRANS_LOAD_MENU_LOOP",
    ]
    result_acceptance = [
        "entry proof: load_slot_transition_summary.py --require-entry --require-slot-match passes for each row with consistent target_slot values",
        "success proof: if LOADSAVE/PlayGame appear, rerun the same summary with --require-success and require those slot rows to match before treating it as load success",
        "slot forcing proof: pre-0044895A load-slot coordinate forcing stays disabled; slot selection is armed only at or after the load-menu entry",
        "promotion remains blocked until natural owner/action proof or approved manual DirectInput proof exists",
    ]

    return {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "passed": not failures,
        "runtime_policy": RUNTIME_POLICY,
        "guard_policy": GUARD_POLICY,
        "promotion_ready": False,
        "stable_stage_should_change": False,
        "source_artifacts": {
            "entry_gap_json": str(entry_gap_json),
            "probe_guard_json": str(probe_guard_json),
            "surface_dump_script": str(surface_dump_script),
            "extra_probe": str(extra_probe),
            "result_parser": str(result_parser),
        },
        "summary": {
            "target_rows": rows,
            "stage": stage,
            "candidate_root": str(candidate_root),
            "result_root_template": str(result_root),
            "run_seconds": run_seconds,
            "late_entry_breakpoint": probe_summary.get("late_entry_breakpoint"),
            "gap_classification": entry_gap.get("gap_classification"),
            "command_count": len(probe_commands),
            "summary_command_count": len(summary_commands),
            "visible_runtime_allowed": False,
        },
        "commands": {
            "hidden_transition_probes": probe_commands,
            "summaries": summary_commands,
        },
        "expected_markers": expected_markers,
        "result_acceptance": result_acceptance,
        "failures": failures,
    }


def write_markdown(path: Path, report: dict[str, Any]) -> None:
    summary = report.get("summary") or {}
    lines = [
        "# Load Slot Transition Run Plan",
        "",
        f"- Status: {status_text(bool(report.get('passed')))}",
        f"- Generated: `{report['generated_at']}`",
        f"- Runtime policy: {report['runtime_policy']}",
        f"- Guard policy: {report['guard_policy']}",
        f"- Promotion ready: `{report['promotion_ready']}`",
        f"- stable_stage_should_change: `{report['stable_stage_should_change']}`",
        f"- Target rows: `{summary.get('target_rows')}`",
        f"- Stage: `{summary.get('stage')}`",
        f"- Candidate root: `{summary.get('candidate_root')}`",
        f"- Result root template: `{summary.get('result_root_template')}`",
        f"- Late entry breakpoint: `{summary.get('late_entry_breakpoint')}`",
        "",
        "## Commands",
        "",
    ]
    for label, command in (report.get("commands") or {}).get("hidden_transition_probes", {}).items():
        lines.extend([f"### {label}", "", "```powershell", command, "```", ""])
    lines.extend(["## Summary Commands", ""])
    for label, command in (report.get("commands") or {}).get("summaries", {}).items():
        lines.extend([f"### {label}", "", "```powershell", command, "```", ""])
    lines.extend(["## Expected Markers", ""])
    lines.extend(f"- `{marker}`" for marker in report.get("expected_markers") or [])
    lines.extend(["", "## Result Acceptance", ""])
    lines.extend(f"- {item}" for item in report.get("result_acceptance") or [])
    if report.get("failures"):
        lines.extend(["", "## Failures", ""])
        lines.extend(f"- {failure}" for failure in report["failures"])
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def write_json(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--entry-gap-json", type=Path, default=DEFAULT_ENTRY_GAP_JSON)
    parser.add_argument("--probe-guard-json", type=Path, default=DEFAULT_PROBE_GUARD_JSON)
    parser.add_argument("--surface-dump-script", type=Path, default=DEFAULT_SURFACE_DUMP_SCRIPT)
    parser.add_argument("--extra-probe", type=Path, default=DEFAULT_EXTRA_PROBE)
    parser.add_argument("--result-parser", type=Path, default=DEFAULT_RESULT_PARSER)
    parser.add_argument("--stage", default=DEFAULT_STAGE)
    parser.add_argument("--candidate-root", type=Path, default=DEFAULT_CANDIDATE_ROOT)
    parser.add_argument("--result-root", type=Path, default=DEFAULT_RESULT_ROOT)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--run-seconds", type=int, default=120)
    parser.add_argument("--write-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--write-markdown", type=Path, default=DEFAULT_MD)
    parser.add_argument("--require-pass", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = build_plan(
        entry_gap_json=args.entry_gap_json,
        probe_guard_json=args.probe_guard_json,
        surface_dump_script=args.surface_dump_script,
        extra_probe=args.extra_probe,
        result_parser=args.result_parser,
        stage=args.stage,
        candidate_root=args.candidate_root,
        result_root=args.result_root,
        repo_root=args.repo_root,
        run_seconds=args.run_seconds,
    )
    write_json(args.write_json, report)
    write_markdown(args.write_markdown, report)
    summary = report["summary"]
    print(f"overall: {status_text(bool(report['passed']))}")
    print(f"target-rows: {summary.get('target_rows')}")
    print(f"command-count: {summary.get('command_count')}")
    print(f"promotion-ready: {report['promotion_ready']}")
    if report["failures"]:
        print("failures:")
        for failure in report["failures"]:
            print(f"  - {failure}")
    if args.require_pass and not report["passed"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
