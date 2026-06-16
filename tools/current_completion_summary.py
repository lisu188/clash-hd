#!/usr/bin/env python3
"""Build the current percentage completion summary.

This is repo-only bookkeeping for progress reporting. It reads generated
evidence artifacts and computes percentages for the measurable gates without
launching Clash95, CDB, wrappers, PowerShell, or visible windows.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_REFRESH_JSON = Path("captures/current/current-evidence-refresh-current.json")
DEFAULT_BATTLE_JSON = Path("captures/current/battle-ui-evidence-current.json")
DEFAULT_MANUAL_CHECKLIST_JSON = Path("captures/current/manual-directinput-validation-checklist-current.json")
DEFAULT_RIGHT_BOTTOM_DECISION_JSON = Path("captures/current/right-bottom-compose-promotion-decision-current.json")
DEFAULT_REPO_TEST_SWEEP_JSON = Path("captures/current/repo-test-sweep-current.json")
DEFAULT_JSON = Path("captures/current/current-completion-summary-current.json")
DEFAULT_MD = Path("captures/current/current-completion-summary-current.md")
RUNTIME_POLICY = "repo-only; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def load_repo_test_sweep(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "passed": False,
            "test_count": 0,
            "passed_count": 0,
            "failed_count": 0,
            "failures": [f"repo test sweep artifact is missing: {path}"],
        }
    try:
        return load_json(path)
    except json.JSONDecodeError as exc:
        return {
            "passed": False,
            "test_count": 0,
            "passed_count": 0,
            "failed_count": 0,
            "failures": [
                f"repo test sweep artifact is invalid JSON: {path}: {exc.msg} at line {exc.lineno} column {exc.colno}"
            ],
        }


def percent(numerator: int | float, denominator: int | float) -> float:
    if not denominator:
        return 0.0
    return round((float(numerator) / float(denominator)) * 100.0, 2)


def check_pass_percent(checks: dict[str, Any]) -> tuple[int, int, float]:
    excluded = {"current_completion_summary", "current_completion_summary_tests"}
    counted_checks = {
        name: check
        for name, check in checks.items()
        if name not in excluded
    }
    total = len(counted_checks)
    passed = sum(1 for check in counted_checks.values() if bool(check.get("passed")))
    return passed, total, percent(passed, total)


def focused_battle_basis(battle: dict[str, Any]) -> str:
    completion = battle.get("completion_summary") or {}
    visible_input = (battle.get("checks") or {}).get("visible_input") or {}
    blocker = completion.get("remaining_blocker")
    if not blocker:
        open_items = visible_input.get("open_items") or battle.get("open_items") or []
        blocker = open_items[0] if open_items else "battle evidence focused completion percent"

    details: list[str] = []
    if visible_input.get("command_ready_run_count") is not None:
        details.append(f"command-ready runs: {visible_input.get('command_ready_run_count')}")
    if visible_input.get("click_consumed_run_count") is not None:
        details.append(f"click-consumed runs: {visible_input.get('click_consumed_run_count')}")
    if int(visible_input.get("invalid_run_count") or 0):
        details.append(f"invalid runs retained: {visible_input.get('invalid_run_count')}")

    if details:
        return f"remaining blocker: {blocker} ({'; '.join(details)})"
    return f"remaining blocker: {blocker}"


def build_summary_from_data(
    *,
    refresh: dict[str, Any],
    battle: dict[str, Any],
    checklist: dict[str, Any],
    right_bottom: dict[str, Any],
    repo_test_sweep: dict[str, Any],
    source_artifacts: dict[str, str],
) -> dict[str, Any]:
    failures: list[str] = []

    refresh_checks = refresh.get("checks") or {}
    if not isinstance(refresh_checks, dict) or not refresh_checks:
        failures.append("current evidence refresh has no checks")
        refresh_checks = {}
    refresh_passed, refresh_total, refresh_percent = check_pass_percent(refresh_checks)

    focused_completion = (
        battle.get("completion_summary") or {}
    ).get("focused_completion_percent")
    if focused_completion is None:
        focused_completion = (battle.get("checks", {}).get("visible_input", {}) or {}).get(
            "focused_completion_percent"
        )
    if focused_completion is None:
        failures.append("battle evidence is missing focused completion percent")
        focused_completion = 0.0

    manual_summary = checklist.get("summary") or {}
    manual_total = int(manual_summary.get("item_count") or 0)
    manual_pending = int(manual_summary.get("pending_count") or 0)
    manual_done = max(0, manual_total - manual_pending)
    manual_percent = percent(manual_done, manual_total)

    right_bottom_required = right_bottom.get("required_checks") or {}
    rb_total = len(right_bottom_required)
    rb_passed = sum(1 for passed in right_bottom_required.values() if bool(passed))
    rb_percent = percent(rb_passed, rb_total)
    rb_blockers = list(right_bottom.get("failures") or [])

    sweep_total = int(repo_test_sweep.get("test_count") or 0)
    sweep_passed = int(repo_test_sweep.get("passed_count") or 0)
    sweep_failed = int(repo_test_sweep.get("failed_count") or 0)
    sweep_percent = percent(sweep_passed, sweep_total)
    if not sweep_total:
        failures.append("repo test sweep has no tests")
    if repo_test_sweep.get("passed") is not True or sweep_failed:
        failures.append("repo test sweep is not passing")
    failures.extend(str(failure) for failure in repo_test_sweep.get("failures") or [])

    manual_proof_valid = bool(checklist.get("manual_proof_valid"))
    promotion_ready = bool(checklist.get("promotion_ready"))
    stable_stage_should_change = bool(right_bottom.get("stable_stage_should_change"))
    full_game_complete = bool(
        refresh.get("passed")
        and battle.get("passed")
        and manual_proof_valid
        and promotion_ready
        and stable_stage_should_change
    )
    full_game_percent_statement = (
        "100.00%"
        if full_game_complete
        else "not 100%; manual DirectInput proof and stable promotion remain blocked"
    )

    rows = [
        {
            "id": "current_repo_evidence_gates",
            "label": "Current repo evidence gates",
            "completion_percent": refresh_percent,
            "passed": bool(refresh.get("passed")),
            "basis": f"{refresh_passed}/{refresh_total} refresh checks pass",
        },
        {
            "id": "repo_test_sweep",
            "label": "Repo-only Python test sweep",
            "completion_percent": sweep_percent,
            "passed": bool(repo_test_sweep.get("passed")) and sweep_failed == 0,
            "basis": f"{sweep_passed}/{sweep_total} tools/test_*.py files pass",
        },
        {
            "id": "focused_battle_right_bottom_lane",
            "label": "Focused battle/right-bottom command lane",
            "completion_percent": round(float(focused_completion), 2),
            "passed": bool(battle.get("passed")),
            "basis": focused_battle_basis(battle),
        },
        {
            "id": "right_bottom_promotion_gate",
            "label": "Right-bottom promotion gate",
            "completion_percent": rb_percent,
            "passed": bool(right_bottom.get("passed")),
            "basis": f"{rb_passed}/{rb_total} required promotion checks pass",
        },
        {
            "id": "manual_directinput_validation",
            "label": "Manual DirectInput validation",
            "completion_percent": manual_percent,
            "passed": manual_proof_valid,
            "basis": f"{manual_done}/{manual_total} manual checklist items have accepted proof",
        },
    ]

    return {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "passed": not failures,
        "runtime_policy": RUNTIME_POLICY,
        "percent_policy": (
            "Percentages are computed from generated evidence gates and checklist counts. "
            "They are progress indicators, not a claim that full-game reverse engineering is complete."
        ),
        "source_artifacts": source_artifacts,
        "percentages": rows,
        "full_game_complete": full_game_complete,
        "full_game_percent_statement": full_game_percent_statement,
        "remaining_blockers": {
            "manual_directinput_pending_ids": manual_summary.get("pending_ids") or [],
            "right_bottom_failures": rb_blockers,
            "battle_open_items": battle.get("open_items") or [],
        },
        "failures": failures,
    }


def build_summary(args: argparse.Namespace) -> dict[str, Any]:
    return build_summary_from_data(
        refresh=load_json(args.refresh_json),
        battle=load_json(args.battle_json),
        checklist=load_json(args.manual_checklist_json),
        right_bottom=load_json(args.right_bottom_decision_json),
        repo_test_sweep=load_repo_test_sweep(args.repo_test_sweep_json),
        source_artifacts={
            "refresh_json": str(args.refresh_json),
            "battle_json": str(args.battle_json),
            "manual_checklist_json": str(args.manual_checklist_json),
            "right_bottom_decision_json": str(args.right_bottom_decision_json),
            "repo_test_sweep_json": str(args.repo_test_sweep_json),
        },
    )


def print_summary(summary: dict[str, Any]) -> None:
    print(f"overall: {'PASS' if summary['passed'] else 'FAIL'}")
    print(f"runtime-policy: {summary['runtime_policy']}")
    print("percentages:")
    for row in summary["percentages"]:
        print(f"  - {row['label']}: {row['completion_percent']:.2f}%")
    print(f"full-game: {summary['full_game_percent_statement']}")
    if summary["failures"]:
        print("failures:")
        for failure in summary["failures"]:
            print(f"  - {failure}")


def write_markdown(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# Current Completion Summary",
        "",
        f"- Overall: {'PASS' if summary['passed'] else 'FAIL'}",
        f"- Generated: `{summary['generated_at']}`",
        f"- Runtime policy: {summary['runtime_policy']}",
        f"- Percent policy: {summary['percent_policy']}",
        f"- Full game complete: `{summary['full_game_complete']}`",
        f"- Full game percent statement: {summary['full_game_percent_statement']}",
        "",
        "## Percentages",
        "",
    ]
    for row in summary["percentages"]:
        lines.extend(
            [
                f"- {row['label']}: `{row['completion_percent']:.2f}%`",
                f"  Basis: {row['basis']}",
            ]
        )
    blockers = summary["remaining_blockers"]
    lines.extend(
        [
            "",
            "## Remaining Blockers",
            "",
            f"- Manual DirectInput pending IDs: `{blockers['manual_directinput_pending_ids']}`",
            f"- Right-bottom failures: `{blockers['right_bottom_failures']}`",
            f"- Battle open items: `{blockers['battle_open_items']}`",
        ]
    )
    if summary["failures"]:
        lines.extend(["", "## Failures", ""])
        lines.extend(f"- {failure}" for failure in summary["failures"])
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh-json", type=Path, default=DEFAULT_REFRESH_JSON)
    parser.add_argument("--battle-json", type=Path, default=DEFAULT_BATTLE_JSON)
    parser.add_argument("--manual-checklist-json", type=Path, default=DEFAULT_MANUAL_CHECKLIST_JSON)
    parser.add_argument("--right-bottom-decision-json", type=Path, default=DEFAULT_RIGHT_BOTTOM_DECISION_JSON)
    parser.add_argument("--repo-test-sweep-json", type=Path, default=DEFAULT_REPO_TEST_SWEEP_JSON)
    parser.add_argument("--write-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--write-markdown", type=Path, default=DEFAULT_MD)
    parser.add_argument("--require-pass", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary = build_summary(args)
    print_summary(summary)
    if args.write_json:
        args.write_json.parent.mkdir(parents=True, exist_ok=True)
        args.write_json.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    if args.write_markdown:
        write_markdown(args.write_markdown, summary)
    if args.require_pass and not summary["passed"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
