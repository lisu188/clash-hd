#!/usr/bin/env python3
"""Inventory HD soak route coverage without launching the game.

This report distinguishes routes implemented by scripts/smoke/run_hd_soak.ps1
from future release-horizon lanes that must remain planned/non-promoting until
their own approval, input, and continuity evidence exists.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_SCRIPT = Path("scripts/smoke/run_hd_soak.ps1")
DEFAULT_JSON = Path("captures/current/hd-soak-route-coverage-current.json")
DEFAULT_MD = Path("captures/current/hd-soak-route-coverage-current.md")
RUNTIME_POLICY = (
    "repo-only soak route coverage inventory; does not launch Clash95, CDB, "
    "wrappers, PowerShell harnesses, or visible windows"
)


REQUIRED_SHORT_ROUTES = {
    "menu-idle": {"tier": "short2", "purpose": "main menu liveness and stable 800x600 capture"},
    "map-idle": {"tier": "short2", "purpose": "representative save load and stable HD map idle"},
    "map-pan": {"tier": "short10", "purpose": "deterministic map movement and frame/input trend"},
}

RELEASE_LANES = [
    {
        "id": "menu_idle",
        "route": "menu-idle",
        "status": "implemented_pending_first_soak",
        "proof_class": "approval_gated_visible_runtime",
        "promotion_scope": "non_promoting_short_soak",
        "next_probe": "run short2 menu-idle after explicit visible-runtime approval",
    },
    {
        "id": "map_idle",
        "route": "map-idle",
        "status": "implemented_waiting_on_short2_menu",
        "proof_class": "approval_gated_visible_runtime",
        "promotion_scope": "non_promoting_short_soak",
        "next_probe": "run short2 map-idle after menu-idle passes",
    },
    {
        "id": "map_pan",
        "route": "map-pan",
        "status": "implemented_waiting_on_map_idle",
        "proof_class": "approval_gated_visible_runtime",
        "promotion_scope": "non_promoting_short_soak",
        "next_probe": "run short10/short30 map-pan after map-idle passes",
    },
    {
        "id": "castle_overview_enter_exit",
        "route": None,
        "status": "planned_not_implemented",
        "proof_class": "future_visible_or_manual_input",
        "promotion_scope": "blocked_until_manual_or_strict_natural_proof",
        "next_probe": "add a non-promoting castle overview route only after short map routes stabilize",
    },
    {
        "id": "barracks_castle_centered_input",
        "route": None,
        "status": "planned_not_implemented",
        "proof_class": "future_visible_or_manual_input",
        "promotion_scope": "blocked_until_manual_or_strict_natural_proof",
        "next_probe": "add centered castle/barracks enter-exit route after castle baseline is approval-ready",
    },
    {
        "id": "right_bottom_action_menu",
        "route": None,
        "status": "planned_blocked_by_manual_or_natural_proof",
        "proof_class": "future_visible_or_manual_input",
        "promotion_scope": "blocked; forced coordinates remain diagnostic only",
        "next_probe": "replace debugger-forced action-click proof with natural or approved manual input proof",
    },
    {
        "id": "tactical_battle_entry_return",
        "route": None,
        "status": "planned_not_implemented",
        "proof_class": "future_visible_or_manual_input",
        "promotion_scope": "blocked_until_battle_entry_return_and_click_to_callback_proof",
        "next_probe": "add battle entry/use/return route after representative map/castle routes are stable",
    },
    {
        "id": "save_load_roundtrip",
        "route": None,
        "status": "planned_not_implemented",
        "proof_class": "future_safe_test_save_continuity",
        "promotion_scope": "blocked_until_safe_save_roundtrip_evidence",
        "next_probe": "define safe isolated save/load continuity evidence after short tiers pass",
    },
    {
        "id": "turn_advancement",
        "route": None,
        "status": "planned_not_implemented",
        "proof_class": "future_state_continuity",
        "promotion_scope": "blocked_until_turn_state_evidence",
        "next_probe": "add deterministic turn-advance route after save/load continuity is safe",
    },
    {
        "id": "campaign_route",
        "route": None,
        "status": "planned_not_implemented",
        "proof_class": "future_long_visible_runtime",
        "promotion_scope": "blocked_until_long_soak_and_campaign_continuity",
        "next_probe": "add representative campaign route only after short and medium tiers are stable",
    },
]


def status_text(passed: bool) -> str:
    return "PASS" if passed else "FAIL"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig", errors="replace")


def parse_validate_set(text: str, parameter_name: str) -> list[str]:
    pattern = re.compile(
        rf"\[ValidateSet\((?P<values>[^)]*)\)\]\s*\r?\n\s*\[string\]\${re.escape(parameter_name)}\b",
        re.IGNORECASE,
    )
    match = pattern.search(text)
    if not match:
        return []
    return re.findall(r"'([^']+)'|\"([^\"]+)\"", match.group("values"))


def normalize_validate_values(values: list[tuple[str, str]] | list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        if isinstance(value, tuple):
            result.append(next(part for part in value if part))
        else:
            result.append(value)
    return result


def parse_tier_seconds(text: str) -> dict[str, int]:
    seconds: dict[str, int] = {}
    for tier in ("short2", "short10", "short30"):
        match = re.search(rf"['\"]{tier}['\"]\s*\{{\s*return\s+(\d+)\s*\}}", text, re.IGNORECASE)
        if match:
            seconds[tier] = int(match.group(1))
    return seconds


def implemented_route_steps(text: str, route: str) -> list[str]:
    route_match = re.search(
        rf"['\"]{re.escape(route)}['\"]\s*\{{(?P<body>.*?)(?=\n\s*['\"](?:menu-idle|map-idle|map-pan|custom)['\"]\s*\{{|\n\s*default\s*\{{)",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    if not route_match:
        return []
    return re.findall(r"Name\s*=\s*['\"]([^'\"]+)['\"]", route_match.group("body"))


def build_report(script: Path = DEFAULT_SCRIPT) -> dict[str, Any]:
    failures: list[str] = []
    if not script.exists():
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "passed": False,
            "runtime_policy": RUNTIME_POLICY,
            "script": str(script),
            "failures": [f"missing soak harness script: {script}"],
        }

    text = read_text(script)
    route_values = normalize_validate_values(parse_validate_set(text, "Route"))
    tier_values = normalize_validate_values(parse_validate_set(text, "Tier"))
    tier_seconds = parse_tier_seconds(text)
    route_steps = {route: implemented_route_steps(text, route) for route in route_values}

    for route in REQUIRED_SHORT_ROUTES:
        if route not in route_values:
            failures.append(f"required short route is missing from harness ValidateSet: {route}")
    for tier, seconds in {"short2": 120, "short10": 600, "short30": 1800}.items():
        if tier not in tier_values:
            failures.append(f"required short tier is missing from harness ValidateSet: {tier}")
        if tier_seconds.get(tier) != seconds:
            failures.append(f"{tier} duration is {tier_seconds.get(tier)}, expected {seconds}")
    if "custom" not in route_values or "custom" not in tier_values:
        failures.append("custom route/tier escape hatch is missing")
    if "-AllowVisibleRuntime" not in text or "-Execute" not in text:
        failures.append("harness no longer exposes explicit visible-runtime execution flags")

    lanes: list[dict[str, Any]] = []
    for lane in RELEASE_LANES:
        lane_record = dict(lane)
        route = lane.get("route")
        lane_record["implemented_in_harness"] = bool(route and route in route_values)
        lane_record["route_steps"] = route_steps.get(str(route), []) if route else []
        lane_record["stable_stage_should_change"] = False
        lanes.append(lane_record)

    implemented_lane_count = sum(1 for lane in lanes if lane["implemented_in_harness"])
    planned_lane_count = len(lanes) - implemented_lane_count
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "passed": not failures,
        "runtime_policy": RUNTIME_POLICY,
        "script": str(script),
        "implemented_routes": route_values,
        "implemented_tiers": tier_values,
        "tier_seconds": tier_seconds,
        "required_short_routes": REQUIRED_SHORT_ROUTES,
        "release_lanes": lanes,
        "counts": {
            "release_lane_count": len(lanes),
            "implemented_lane_count": implemented_lane_count,
            "planned_lane_count": planned_lane_count,
            "required_short_route_count": len(REQUIRED_SHORT_ROUTES),
        },
        "coverage_complete": planned_lane_count == 0,
        "next_runtime_route": "menu-idle",
        "next_after_short2_menu_idle": "map-idle",
        "failures": failures,
    }


def to_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# HD Soak Route Coverage",
        "",
        f"- Overall: {status_text(bool(report['passed']))}",
        f"- Generated: `{report['generated_at']}`",
        f"- Runtime policy: {report['runtime_policy']}",
        f"- Harness script: `{report['script']}`",
        f"- Implemented routes: `{', '.join(report.get('implemented_routes') or [])}`",
        f"- Implemented tiers: `{', '.join(report.get('implemented_tiers') or [])}`",
        f"- Release lanes implemented: `{report['counts']['implemented_lane_count']}/{report['counts']['release_lane_count']}`",
        f"- Coverage complete: `{report['coverage_complete']}`",
        f"- Next runtime route: `{report['next_runtime_route']}`",
        "",
        "## Release Lanes",
        "",
    ]
    for lane in report["release_lanes"]:
        route = lane.get("route") or "not-yet-scripted"
        lines.append(
            f"- `{lane['id']}`: status=`{lane['status']}` route=`{route}` "
            f"implemented=`{lane['implemented_in_harness']}` proof=`{lane['proof_class']}`"
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
    parser.add_argument("--script", type=Path, default=DEFAULT_SCRIPT)
    parser.add_argument("--write-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--write-markdown", "--write-md", dest="write_markdown", type=Path, default=DEFAULT_MD)
    parser.add_argument("--require-pass", action="store_true")
    args = parser.parse_args()

    report = build_report(args.script)
    write_outputs(report, args.write_json, args.write_markdown)
    print(f"overall: {status_text(bool(report['passed']))}")
    print(f"runtime-policy: {report['runtime_policy']}")
    print(f"implemented-lanes: {report.get('counts', {}).get('implemented_lane_count')}/{report.get('counts', {}).get('release_lane_count')}")
    print(f"coverage-complete: {report.get('coverage_complete')}")
    if report["failures"]:
        print("failures:")
        for failure in report["failures"]:
            print(f"  - {failure}")
    if args.require_pass and not report["passed"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
