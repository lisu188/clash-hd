#!/usr/bin/env python3
"""Build the ordered short-tier HD soak ladder.

This is a repo-only planning and guard artifact. It reads compact current
evidence reports, records the exact short-tier order, and keeps longer/future
lanes locked until the short ladder has real soak evidence.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROTECTED_STABLE_STAGE = (
    "gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-"
    "minimapright-dynvswitch"
)
RUNTIME_POLICY = (
    "repo-only short-tier soak ladder; does not launch Clash95, CDB, wrappers, "
    "PowerShell harnesses, or visible windows"
)

DEFAULT_ROUTE_COVERAGE_JSON = Path("captures/current/hd-soak-route-coverage-current.json")
DEFAULT_NEXT_ACTIONS_JSON = Path("captures/current/hd-endurance-next-actions-current.json")
DEFAULT_SOAK_REPORT_JSON = Path("captures/current/hd-soak-report-guard-current.json")
DEFAULT_JSON = Path("captures/current/hd-soak-short-tier-ladder-current.json")
DEFAULT_MD = Path("captures/current/hd-soak-short-tier-ladder-current.md")

SHORT_LADDER_STEPS: list[dict[str, Any]] = [
    {
        "id": "short2_menu_idle",
        "title": "Short2 menu idle",
        "tier": "short2",
        "route": "menu-idle",
        "duration_sec": 120,
        "prerequisites": [],
        "purpose": "first protected-stage liveness, clean stop, and stable 800x600 menu rendering",
    },
    {
        "id": "short2_map_idle",
        "title": "Short2 map idle",
        "tier": "short2",
        "route": "map-idle",
        "duration_sec": 120,
        "prerequisites": ["short2_menu_idle"],
        "purpose": "representative save-load route with stable HD map rendering",
    },
    {
        "id": "short10_map_idle",
        "title": "Short10 map idle",
        "tier": "short10",
        "route": "map-idle",
        "duration_sec": 600,
        "prerequisites": ["short2_map_idle"],
        "purpose": "medium idle trend for frame, palette, process, and artifact stability",
    },
    {
        "id": "short10_map_pan",
        "title": "Short10 map pan",
        "tier": "short10",
        "route": "map-pan",
        "duration_sec": 600,
        "prerequisites": ["short10_map_idle"],
        "purpose": "deterministic map movement trend and input responsiveness smoke",
    },
    {
        "id": "short30_map_pan",
        "title": "Short30 map pan",
        "tier": "short30",
        "route": "map-pan",
        "duration_sec": 1800,
        "prerequisites": ["short10_map_pan"],
        "purpose": "pre-endurance pan/input trend before any 2h+ or future screen-route lane",
    },
]

FUTURE_LANE_IDS = [
    "castle_overview_enter_exit",
    "barracks_castle_centered_input",
    "right_bottom_action_menu",
    "tactical_battle_entry_return",
    "save_load_roundtrip",
    "turn_advancement",
    "campaign_route",
]


def status_text(passed: bool) -> str:
    return "PASS" if passed else "FAIL"


def load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8-sig"))


def path_text(path: Path) -> str:
    return str(path).replace("/", "\\")


def step_slug(step: dict[str, Any]) -> str:
    return f"{str(step['tier']).replace('_', '-')}-{str(step['route']).replace('_', '-')}"


def canonical_report_paths(step: dict[str, Any]) -> dict[str, str]:
    slug = step_slug(step)
    return {
        "report_json": path_text(Path("captures/current") / f"hd-soak-{slug}-current.json"),
        "report_markdown": path_text(Path("captures/current") / f"hd-soak-{slug}-current.md"),
    }


def command_for_step(step: dict[str, Any], *, execute: bool) -> str:
    paths = canonical_report_paths(step)
    parts = [
        "powershell.exe",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        r".\scripts\smoke\run_hd_soak.ps1",
        "-Tier",
        str(step["tier"]),
        "-Route",
        str(step["route"]),
        "-ReportJson",
        paths["report_json"],
        "-ReportMarkdown",
        paths["report_markdown"],
    ]
    if execute:
        parts.extend(["-Execute", "-AllowVisibleRuntime", "-RequirePass"])
    parts.append("-Json")
    return " ".join(parts)


def nested(data: dict[str, Any] | None, *keys: str, default: Any = None) -> Any:
    value: Any = data or {}
    for key in keys:
        if not isinstance(value, dict) or key not in value:
            return default
        value = value[key]
    return value


def soak_report_matches_step(report: dict[str, Any] | None, step: dict[str, Any]) -> bool:
    if not report:
        return False
    return (
        report.get("stage") == PROTECTED_STABLE_STAGE
        and report.get("tier") == step["tier"]
        and report.get("route") == step["route"]
    )


def route_step_names(route_coverage: dict[str, Any] | None, route: str) -> list[str]:
    for lane in (route_coverage or {}).get("release_lanes") or []:
        if lane.get("route") == route:
            return [str(name) for name in lane.get("route_steps") or []]
    return []


def route_coverage_failures(route_coverage: dict[str, Any] | None) -> list[str]:
    if route_coverage is None:
        return [f"missing route coverage report: {DEFAULT_ROUTE_COVERAGE_JSON}"]
    failures: list[str] = []
    if not route_coverage.get("passed"):
        failures.append("route coverage report is not passing")
    routes = set(route_coverage.get("implemented_routes") or [])
    tiers = set(route_coverage.get("implemented_tiers") or [])
    tier_seconds = route_coverage.get("tier_seconds") or {}
    for step in SHORT_LADDER_STEPS:
        if step["route"] not in routes:
            failures.append(f"ladder route missing from harness coverage: {step['route']}")
        if step["tier"] not in tiers:
            failures.append(f"ladder tier missing from harness coverage: {step['tier']}")
        if int(tier_seconds.get(step["tier"]) or 0) != int(step["duration_sec"]):
            failures.append(
                f"{step['tier']} duration is {tier_seconds.get(step['tier'])}, "
                f"expected {step['duration_sec']}"
            )
    return failures


def build_steps(
    route_coverage: dict[str, Any] | None,
    soak_report: dict[str, Any] | None,
    route_coverage_json: Path,
    soak_report_json: Path,
) -> list[dict[str, Any]]:
    routes = set((route_coverage or {}).get("implemented_routes") or [])
    tiers = set((route_coverage or {}).get("implemented_tiers") or [])
    tier_seconds = (route_coverage or {}).get("tier_seconds") or {}
    passed_by_id: dict[str, bool] = {}
    steps: list[dict[str, Any]] = []

    for step in SHORT_LADDER_STEPS:
        prerequisites = [str(value) for value in step["prerequisites"]]
        prerequisites_passed = all(passed_by_id.get(prereq) for prereq in prerequisites)
        harness_ready = (
            step["route"] in routes
            and step["tier"] in tiers
            and int(tier_seconds.get(step["tier"]) or 0) == int(step["duration_sec"])
        )
        matched_report = soak_report_matches_step(soak_report, step)
        matched_report_passed = bool(matched_report and soak_report and soak_report.get("overall"))
        matched_report_executed = bool(matched_report and nested(soak_report, "checks", "executed", "summary", "executed"))

        if not harness_ready:
            status = "missing_harness_contract"
        elif matched_report_passed:
            status = "pass"
        elif not prerequisites_passed:
            status = "locked_by_prerequisite"
        else:
            status = "approval_required"

        record = {
            **step,
            "status": status,
            "passed": status == "pass",
            "harness_ready": harness_ready,
            "route_steps": route_step_names(route_coverage, str(step["route"])),
            "evidence": [str(soak_report_json)] if matched_report else [],
            "matched_current_soak_report": matched_report,
            "matched_current_soak_report_executed": matched_report_executed,
            "matched_current_soak_report_overall": bool(matched_report and soak_report and soak_report.get("overall")),
            "safe_dry_run_command": command_for_step(step, execute=False),
            "approval_gated_runtime_command": command_for_step(step, execute=True),
            "canonical_report_paths": canonical_report_paths(step),
            "requires_visible_runtime": status == "approval_required",
            "requires_explicit_user_approval": status == "approval_required",
            "writes_outside_repo": [r"C:\ClashTests\hd-soak", r"C:\ClashCaptures\hd-soak"],
            "must_not_modify": [r"C:\Clash\clash95.exe"],
            "route_coverage": str(route_coverage_json),
        }
        if matched_report and soak_report and not matched_report_passed:
            record["soak_report_failures"] = soak_report.get("failures") or []
        passed_by_id[str(step["id"])] = bool(record["passed"])
        steps.append(record)
    return steps


def current_step(steps: list[dict[str, Any]]) -> dict[str, Any] | None:
    for step in steps:
        if not step.get("passed"):
            return step
    return None


def future_lane_locks(route_coverage: dict[str, Any] | None) -> list[dict[str, Any]]:
    lanes = []
    by_id = {str(lane.get("id")): lane for lane in (route_coverage or {}).get("release_lanes") or []}
    for lane_id in FUTURE_LANE_IDS:
        lane = by_id.get(lane_id, {})
        lanes.append(
            {
                "id": lane_id,
                "route": lane.get("route"),
                "implemented_in_harness": bool(lane.get("implemented_in_harness")),
                "status": lane.get("status") or "planned_not_implemented",
                "promotion_scope": lane.get("promotion_scope") or "locked_until_short_ladder_and_route_proof",
                "next_probe": lane.get("next_probe") or "define after short ladder passes",
                "stable_stage_should_change": False,
            }
        )
    return lanes


def next_action_alignment(next_actions: dict[str, Any] | None, step: dict[str, Any] | None) -> dict[str, Any]:
    action = (next_actions or {}).get("next_action") or {}
    expected = step.get("approval_gated_runtime_command") if step else None
    reported = action.get("exact_runtime_command")
    return {
        "next_actions_report_present": next_actions is not None,
        "next_actions_passed": bool(next_actions and next_actions.get("passed")),
        "reported_next_action": action.get("id"),
        "reported_runtime_command": reported,
        "expected_runtime_command": expected,
        "matches_expected_current_step": bool(reported and expected and reported == expected),
    }


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    route_coverage = load_json(args.route_coverage_json)
    next_actions = load_json(args.next_actions_json)
    soak_report = load_json(args.soak_report_json)

    failures = route_coverage_failures(route_coverage)
    if next_actions is None:
        failures.append(f"missing next-action report: {args.next_actions_json}")
    elif not next_actions.get("passed"):
        failures.append("next-action report is not passing")

    steps = build_steps(route_coverage, soak_report, args.route_coverage_json, args.soak_report_json)
    next_step = current_step(steps)
    alignment = next_action_alignment(next_actions, next_step)
    if next_step and next_step["id"] == "short2_menu_idle" and not alignment["matches_expected_current_step"]:
        failures.append("next-action command does not match the first short2 menu-idle ladder step")

    ladder_complete = all(step.get("passed") for step in steps)
    counts = {
        "total": len(steps),
        "passed": sum(1 for step in steps if step.get("passed")),
        "approval_required": sum(1 for step in steps if step.get("status") == "approval_required"),
        "locked_by_prerequisite": sum(1 for step in steps if step.get("status") == "locked_by_prerequisite"),
        "missing_harness_contract": sum(1 for step in steps if step.get("status") == "missing_harness_contract"),
    }

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "passed": not failures,
        "runtime_policy": RUNTIME_POLICY,
        "protected_stable_stage": PROTECTED_STABLE_STAGE,
        "source_artifacts": {
            "route_coverage": str(args.route_coverage_json),
            "next_actions": str(args.next_actions_json),
            "soak_report_guard": str(args.soak_report_json),
        },
        "ladder_complete": ladder_complete,
        "counts": counts,
        "current_step": None
        if next_step is None
        else {
            "id": next_step["id"],
            "tier": next_step["tier"],
            "route": next_step["route"],
            "status": next_step["status"],
            "requires_explicit_user_approval": next_step["requires_explicit_user_approval"],
            "safe_dry_run_command": next_step["safe_dry_run_command"],
            "approval_gated_runtime_command": next_step["approval_gated_runtime_command"],
        },
        "steps": steps,
        "locks": {
            "stable_stage_should_change": False,
            "right_bottom_promotion_blocked": True,
            "long_tiers_locked": not ladder_complete,
            "long_tiers_unlock_condition": "all short-tier ladder steps pass with real soak evidence",
            "future_lanes_locked": True,
            "future_lanes_unlock_condition": (
                "short ladder passes first; each future lane still needs its own natural/manual input, "
                "continuity, and promotion-boundary proof"
            ),
        },
        "future_lane_locks": future_lane_locks(route_coverage),
        "next_action_alignment": alignment,
        "failures": failures,
    }


def to_markdown(report: dict[str, Any]) -> str:
    current = report.get("current_step") or {}
    lines = [
        "# HD Soak Short-Tier Ladder",
        "",
        f"- Overall: {status_text(bool(report['passed']))}",
        f"- Generated: `{report['generated_at']}`",
        f"- Runtime policy: {report['runtime_policy']}",
        f"- Protected stable stage: `{report['protected_stable_stage']}`",
        f"- Ladder complete: `{report['ladder_complete']}`",
        f"- Current step: `{current.get('id') or 'none'}`",
        f"- Stable stage should change: `{report['locks']['stable_stage_should_change']}`",
        f"- Right-bottom promotion blocked: `{report['locks']['right_bottom_promotion_blocked']}`",
        f"- Long tiers locked: `{report['locks']['long_tiers_locked']}`",
        f"- Future lanes locked: `{report['locks']['future_lanes_locked']}`",
        "",
        "## Steps",
        "",
    ]
    for step in report.get("steps") or []:
        lines.append(
            f"- `{step['id']}`: tier=`{step['tier']}` route=`{step['route']}` "
            f"status=`{step['status']}` passed=`{step['passed']}`"
        )

    if current:
        lines.extend(
            [
                "",
                "## Current Step Commands",
                "",
                "Safe dry-run command:",
                "",
                "```powershell",
                current["safe_dry_run_command"],
                "```",
                "",
                "Approval-gated runtime command:",
                "",
                "```powershell",
                current["approval_gated_runtime_command"],
                "```",
            ]
        )

    lines.extend(["", "## Locked Future Lanes", ""])
    for lane in report.get("future_lane_locks") or []:
        lines.append(
            f"- `{lane['id']}`: status=`{lane['status']}` "
            f"implemented=`{lane['implemented_in_harness']}`"
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
    parser.add_argument("--route-coverage-json", type=Path, default=DEFAULT_ROUTE_COVERAGE_JSON)
    parser.add_argument("--next-actions-json", type=Path, default=DEFAULT_NEXT_ACTIONS_JSON)
    parser.add_argument("--soak-report-json", type=Path, default=DEFAULT_SOAK_REPORT_JSON)
    parser.add_argument("--write-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--write-markdown", "--write-md", dest="write_markdown", type=Path, default=DEFAULT_MD)
    parser.add_argument("--require-pass", action="store_true")
    args = parser.parse_args()

    report = build_report(args)
    write_outputs(report, args.write_json, args.write_markdown)
    print(f"overall: {status_text(bool(report['passed']))}")
    print(f"runtime-policy: {report['runtime_policy']}")
    print(f"ladder-complete: {report.get('ladder_complete')}")
    current = report.get("current_step") or {}
    if current:
        print(f"current-step: {current.get('id')} ({current.get('status')})")
    if report["failures"]:
        print("failures:")
        for failure in report["failures"]:
            print(f"  - {failure}")
    if args.require_pass and not report["passed"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
