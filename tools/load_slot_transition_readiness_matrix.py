#!/usr/bin/env python3
"""Aggregate the current load-slot transition readiness evidence.

This repo-only matrix checks that the next rows 3-5 transition probe is ready
to run under the hidden-desktop CDB harness. It does not treat the blocked rows
as solved and it does not promote any patch stage.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_ENTRY_GAP_JSON = Path("captures/current/load-slot-entry-gap-current.json")
DEFAULT_PROBE_GUARD_JSON = Path("captures/current/load-slot-transition-probe-guard-current.json")
DEFAULT_RUN_PLAN_JSON = Path("captures/current/load-slot-transition-run-plan-current.json")
DEFAULT_GEOMETRY_GUARD_JSON = Path("captures/current/load-slot-transition-geometry-guard-current.json")
DEFAULT_PROBE_PREVIEW_JSON = Path("captures/current/load-slot-transition-probe-preview-current.json")
DEFAULT_SUMMARY_TESTS_JSON = Path("captures/current/load-slot-transition-summary-tests-current.json")
DEFAULT_JSON = Path("captures/current/load-slot-transition-readiness-current.json")
DEFAULT_MD = Path("captures/current/load-slot-transition-readiness-current.md")

TARGET_ROWS = [3, 4, 5]
RUNTIME_POLICY = (
    "repo-only transition readiness matrix; reads generated JSON reports and "
    "does not launch Clash95, CDB, wrappers, PowerShell, or visible windows"
)
GUARD_POLICY = (
    "passes only when rows 3-5 are still classified as pre-0044895A blockers, "
    "the late-entry probe, row geometry, generated previews, and summary parser "
    "are all passing, every future command is hidden-desktop, target-slot "
    "acceptance is strict, and the result acceptance remains non-promoting"
)


def load_json(path: Path, label: str, failures: list[str]) -> dict[str, Any]:
    if not path.exists():
        failures.append(f"missing {label}: {path}")
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def status_text(passed: bool) -> str:
    return "PASS" if passed else "FAIL"


def as_int_list(values: Any) -> list[int]:
    return [int(value) for value in (values or [])]


def command_is_hidden(command: str) -> bool:
    lowered = command.lower()
    return (
        "-useddrawproxy" in lowered
        and "-fastforwardstartanims" in lowered
        and "-skipmapvalidation" in lowered
        and "-allowvisibledesktop" not in lowered
        and "-allowvisibleruntime" not in lowered
        and "c:\\clashtests\\load-slot-transition" in lowered
    )


def summary_command_is_strict(command: str) -> bool:
    lowered = command.lower()
    return (
        "tools\\load_slot_transition_summary.py" in lowered
        and "--require-entry" in lowered
        and "--require-slot-match" in lowered
    )


def build_matrix(
    *,
    entry_gap_json: Path = DEFAULT_ENTRY_GAP_JSON,
    probe_guard_json: Path = DEFAULT_PROBE_GUARD_JSON,
    run_plan_json: Path = DEFAULT_RUN_PLAN_JSON,
    geometry_guard_json: Path = DEFAULT_GEOMETRY_GUARD_JSON,
    probe_preview_json: Path = DEFAULT_PROBE_PREVIEW_JSON,
    summary_tests_json: Path = DEFAULT_SUMMARY_TESTS_JSON,
) -> dict[str, Any]:
    failures: list[str] = []
    entry_gap = load_json(entry_gap_json, "load-slot entry gap", failures)
    probe_guard = load_json(probe_guard_json, "load-slot transition probe guard", failures)
    run_plan = load_json(run_plan_json, "load-slot transition run plan", failures)
    geometry_guard = load_json(geometry_guard_json, "load-slot transition geometry guard", failures)
    probe_preview = load_json(probe_preview_json, "load-slot transition probe preview", failures)
    summary_tests = load_json(summary_tests_json, "load-slot transition summary tests", failures)

    entry_summary = entry_gap.get("summary") or {}
    run_summary = run_plan.get("summary") or {}
    geometry_summary = geometry_guard.get("summary") or {}
    preview_summary = probe_preview.get("summary") or {}
    hidden_commands = (run_plan.get("commands") or {}).get("hidden_transition_probes") or {}
    summary_commands = (run_plan.get("commands") or {}).get("summaries") or {}
    preview_rows = probe_preview.get("previews") or []
    result_acceptance = run_plan.get("result_acceptance") or []

    target_rows = as_int_list(run_summary.get("target_rows"))
    geometry_rows = as_int_list(row.get("slot") for row in (geometry_summary.get("row_geometry") or []))
    preview_target_rows = as_int_list(preview_summary.get("target_rows"))
    blocked_rows = as_int_list(entry_summary.get("blocked_rows"))
    preview_hashes = preview_summary.get("preview_sha256") or {}
    acceptance_text = " ".join(str(item) for item in result_acceptance).lower()

    hidden_command_values = list(hidden_commands.values())
    summary_command_values = list(summary_commands.values())
    expected_slots_have_commands = all(
        any(f"-loadslot {slot}" in command.lower() for command in hidden_command_values)
        for slot in TARGET_ROWS
    )
    expected_slots_have_summaries = all(
        any(f"--expected-slot {slot}" in command.lower() for command in summary_command_values)
        for slot in TARGET_ROWS
    )
    acceptance_mentions_success_gate = any("--require-success" in item for item in result_acceptance)
    acceptance_mentions_slot_consistency = (
        "target_slot" in acceptance_text and "loadsave/playgame" in acceptance_text
    )

    checks = {
        "entry_gap_passed": bool(entry_gap.get("passed")),
        "slot2_post_entry_success": bool(entry_summary.get("slot2_post_entry_success")),
        "rows_3_4_5_blocked_before_entry": blocked_rows == TARGET_ROWS
        and entry_gap.get("gap_classification") == "after_main_load_callback_before_load_menu_case_entry",
        "probe_guard_passed": bool(probe_guard.get("passed")),
        "probe_guard_is_parameterized": bool(
            (probe_guard.get("summary") or {}).get("slot_conditions_parameterized")
            and (probe_guard.get("summary") or {}).get("extra_probe_placeholders_replaced")
        ),
        "run_plan_passed": bool(run_plan.get("passed")),
        "run_plan_targets_rows_3_4_5": target_rows == TARGET_ROWS,
        "run_plan_hidden_commands": bool(hidden_command_values)
        and all(command_is_hidden(command) for command in hidden_command_values)
        and expected_slots_have_commands,
        "summary_commands_strict": bool(summary_command_values)
        and all(summary_command_is_strict(command) for command in summary_command_values)
        and expected_slots_have_summaries,
        "geometry_guard_passed": bool(geometry_guard.get("passed")),
        "geometry_rows_match_targets": geometry_rows == TARGET_ROWS,
        "probe_preview_passed": bool(probe_preview.get("passed")),
        "probe_preview_rows_match_targets": preview_target_rows == TARGET_ROWS
        and [int(row.get("slot")) for row in preview_rows] == TARGET_ROWS,
        "probe_preview_hashes_present": all(str(slot) in preview_hashes for slot in TARGET_ROWS),
        "summary_parser_tests_passed": bool(summary_tests.get("passed")),
        "non_promoting": all(
            report.get("promotion_ready") is False
            and report.get("stable_stage_should_change", False) is False
            for report in (run_plan, geometry_guard, probe_preview)
        ),
        "result_acceptance_non_promoting": acceptance_mentions_success_gate
        and acceptance_mentions_slot_consistency
        and any("promotion remains blocked" in item.lower() for item in result_acceptance),
    }

    for name, passed in checks.items():
        if not passed:
            failures.append(f"transition readiness check failed: {name}")

    classification = (
        "ready_for_hidden_transition_probe"
        if not failures
        else "transition_readiness_incomplete_or_stale"
    )
    next_steps = [
        "run the hidden slot 3, 4, and 5 transition probes only when runtime approval is available",
        "summarize each resulting LSTRANS log with --require-entry --require-slot-match so target_slot values must stay row-consistent",
        "treat LOADSAVE/PlayGame rows as success only after rerunning the summary with --require-success and matching slot rows",
        "keep the evidence non-promoting until natural owner/action proof or approved manual DirectInput proof exists",
    ]

    return {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "passed": not failures,
        "runtime_policy": RUNTIME_POLICY,
        "guard_policy": GUARD_POLICY,
        "classification": classification,
        "promotion_ready": False,
        "stable_stage_should_change": False,
        "source_artifacts": {
            "entry_gap_json": str(entry_gap_json),
            "probe_guard_json": str(probe_guard_json),
            "run_plan_json": str(run_plan_json),
            "geometry_guard_json": str(geometry_guard_json),
            "probe_preview_json": str(probe_preview_json),
            "summary_tests_json": str(summary_tests_json),
        },
        "checks": checks,
        "summary": {
            "target_rows": TARGET_ROWS,
            "blocked_rows": blocked_rows,
            "stage": run_summary.get("stage"),
            "candidate_root": run_summary.get("candidate_root"),
            "command_count": len(hidden_command_values),
            "summary_command_count": len(summary_command_values),
            "preview_sha256": preview_hashes,
            "result_acceptance": result_acceptance,
        },
        "next_steps": next_steps,
        "failures": failures,
    }


def write_markdown(path: Path, report: dict[str, Any]) -> None:
    summary = report["summary"]
    lines = [
        "# Load Slot Transition Readiness Matrix",
        "",
        f"- Overall: {status_text(bool(report['passed']))}",
        f"- Generated: `{report['generated_at']}`",
        f"- Runtime policy: {report['runtime_policy']}",
        f"- Guard policy: {report['guard_policy']}",
        f"- Classification: `{report['classification']}`",
        f"- Promotion ready: `{report['promotion_ready']}`",
        f"- stable_stage_should_change: `{report['stable_stage_should_change']}`",
        f"- Target rows: `{summary['target_rows']}`",
        f"- Blocked rows: `{summary['blocked_rows']}`",
        f"- Command count: `{summary['command_count']}`",
        f"- Summary command count: `{summary['summary_command_count']}`",
        f"- Stage: `{summary['stage']}`",
        f"- Candidate root: `{summary['candidate_root']}`",
        "",
        "## Checks",
        "",
    ]
    lines.extend(
        f"- `{name}`: `{status_text(bool(passed))}`"
        for name, passed in report["checks"].items()
    )
    lines.extend(["", "## Preview Hashes", ""])
    for slot in TARGET_ROWS:
        lines.append(f"- Slot `{slot}`: `{summary['preview_sha256'].get(str(slot))}`")
    lines.extend(["", "## Result Acceptance", ""])
    lines.extend(f"- {item}" for item in summary["result_acceptance"])
    lines.extend(["", "## Next Steps", ""])
    lines.extend(f"- {item}" for item in report["next_steps"])
    if report["failures"]:
        lines.extend(["", "## Failures", ""])
        lines.extend(f"- {failure}" for failure in report["failures"])
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--entry-gap-json", type=Path, default=DEFAULT_ENTRY_GAP_JSON)
    parser.add_argument("--probe-guard-json", type=Path, default=DEFAULT_PROBE_GUARD_JSON)
    parser.add_argument("--run-plan-json", type=Path, default=DEFAULT_RUN_PLAN_JSON)
    parser.add_argument("--geometry-guard-json", type=Path, default=DEFAULT_GEOMETRY_GUARD_JSON)
    parser.add_argument("--probe-preview-json", type=Path, default=DEFAULT_PROBE_PREVIEW_JSON)
    parser.add_argument("--summary-tests-json", type=Path, default=DEFAULT_SUMMARY_TESTS_JSON)
    parser.add_argument("--write-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--write-markdown", "--write-md", dest="write_markdown", type=Path, default=DEFAULT_MD)
    parser.add_argument("--require-pass", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_matrix(
        entry_gap_json=args.entry_gap_json,
        probe_guard_json=args.probe_guard_json,
        run_plan_json=args.run_plan_json,
        geometry_guard_json=args.geometry_guard_json,
        probe_preview_json=args.probe_preview_json,
        summary_tests_json=args.summary_tests_json,
    )
    print(f"overall: {status_text(bool(report['passed']))}")
    print(f"runtime-policy: {report['runtime_policy']}")
    print(f"classification: {report['classification']}")
    print(f"promotion-ready: {report['promotion_ready']}")
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
