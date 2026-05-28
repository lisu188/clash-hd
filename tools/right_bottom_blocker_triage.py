#!/usr/bin/env python3
"""Classify the current right-bottom action-menu blocker.

This is repo-only triage. It reads generated evidence reports and records why
the right-bottom action UI is still not promotable: controlled composition
renders the lower/right UI, but the natural route does not enter owner/action
draw rows and remains save-state/load-route gated.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_COMPOSE_EVIDENCE_JSON = Path("captures/right-bottom-compose-evidence-current.json")
DEFAULT_PROMOTION_DECISION_JSON = Path("captures/right-bottom-compose-promotion-decision-current.json")
DEFAULT_NATURAL_ROUTE_JSON = Path("captures/right-bottom-natural-route-guard-current.json")
DEFAULT_NATURAL_SLOT5_SUMMARY_JSON = Path(
    "captures/cdb-surface-dump-20260527-193512/right-bottom-natural-slot5-summary.json"
)
DEFAULT_SLOT_FIXTURE_RUNTIME_PLAN_JSON = Path("captures/right-bottom-slot-fixture-runtime-plan-current.json")
DEFAULT_LOAD_SLOT_ENTRY_GAP_JSON = Path("captures/load-slot-entry-gap-current.json")
DEFAULT_MANUAL_RUN_PLAN_JSON = Path("captures/manual-directinput-run-plan-current.json")
DEFAULT_JSON = Path("captures/right-bottom-blocker-triage-current.json")
DEFAULT_MD = Path("captures/right-bottom-blocker-triage-current.md")

RUNTIME_POLICY = (
    "repo-only evidence triage; reads generated JSON reports and does not launch "
    "Clash95, CDB, wrappers, PowerShell, or visible windows"
)
GUARD_POLICY = (
    "passes only while the current blocker is explicitly classified as non-promoting: "
    "controlled composition is recovered, natural owner/action rows are absent, the "
    "natural route is either owner-flag gated or blocked inside the slot5 "
    "Render_Begin/DD_Pump/copyback lane, and the next proof path remains hidden diagnosis "
    "or approved manual input"
)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def status_text(passed: bool) -> str:
    return "PASS" if passed else "FAIL"


def _check(compose: dict[str, Any], name: str) -> dict[str, Any]:
    return (compose.get("checks") or {}).get(name) or {}


def _summary(compose: dict[str, Any], name: str) -> dict[str, Any]:
    return _check(compose, name).get("summary") or {}


def _load_report(path: Path, label: str, failures: list[str]) -> dict[str, Any]:
    if not path.exists():
        failures.append(f"missing {label}: {path}")
        return {}
    return load_json(path)


def _int_value(value: Any, default: int = -1) -> int:
    if value is None:
        return default
    return int(value)


def build_triage(
    *,
    compose_evidence_json: Path = DEFAULT_COMPOSE_EVIDENCE_JSON,
    promotion_decision_json: Path = DEFAULT_PROMOTION_DECISION_JSON,
    natural_route_json: Path = DEFAULT_NATURAL_ROUTE_JSON,
    natural_slot5_summary_json: Path = DEFAULT_NATURAL_SLOT5_SUMMARY_JSON,
    slot_fixture_runtime_plan_json: Path = DEFAULT_SLOT_FIXTURE_RUNTIME_PLAN_JSON,
    load_slot_entry_gap_json: Path = DEFAULT_LOAD_SLOT_ENTRY_GAP_JSON,
    manual_run_plan_json: Path = DEFAULT_MANUAL_RUN_PLAN_JSON,
) -> dict[str, Any]:
    failures: list[str] = []
    compose = _load_report(compose_evidence_json, "right-bottom compose evidence", failures)
    decision = _load_report(promotion_decision_json, "right-bottom promotion decision", failures)
    natural_route = _load_report(natural_route_json, "right-bottom natural route guard", failures)
    natural_slot5 = load_json(natural_slot5_summary_json) if natural_slot5_summary_json.exists() else {}
    fixture_plan = _load_report(slot_fixture_runtime_plan_json, "right-bottom slot fixture runtime plan", failures)
    entry_gap = _load_report(load_slot_entry_gap_json, "load-slot entry gap", failures)
    manual_plan = _load_report(manual_run_plan_json, "manual DirectInput run plan", failures)

    patch = _summary(compose, "right_bottom_compose_patch")
    fullstart = _summary(compose, "right_bottom_compose_fullstart_route")
    normal_gate = _summary(compose, "right_bottom_compose_normal_gate")
    natural_ui = _summary(compose, "right_bottom_compose_ui_probe")
    grid_hit = _summary(compose, "right_bottom_grid_hit")
    natural_summary = natural_route.get("summary") or {}
    fixture_summary = fixture_plan.get("summary") or {}
    entry_summary = entry_gap.get("summary") or {}
    manual_summary = manual_plan.get("summary") or {}

    controlled_composition_recovered = bool(
        _check(compose, "right_bottom_compose_patch").get("passed")
        and _check(compose, "right_bottom_compose_fullstart_route").get("passed")
        and float(fullstart.get("bottom_right_ui_corner_nonblack") or 0.0) >= 40.0
        and float(fullstart.get("bottom_right_tile_r8c10_nonblack") or 0.0) >= 40.0
        and float(fullstart.get("bottom_right_tile_r8c11_nonblack") or 0.0) >= 40.0
        and int(fullstart.get("av_count") or 0) == 0
    )
    natural_ui_owner_action_rows = int(natural_ui.get("rbui_panel_draw") or 0) + int(
        natural_ui.get("rbui_action_box") or 0
    )
    natural_ui_absent = bool(
        natural_ui.get("rbui_markers_seen")
        and natural_ui_owner_action_rows == 0
        and int(natural_ui.get("av_count") or 0) == 0
    )
    owner_flag = natural_summary.get("owner_flag_test") or {}
    action_descriptor = natural_summary.get("action_descriptor") or {}
    natural_route_state_gated = bool(
        natural_route.get("passed")
        and natural_summary.get("state_gated_by_owner_flag") is True
        and owner_flag.get("owner_flag") == "0x00"
        and not any(int(owner_flag.get(bit) or 0) for bit in ("bit2", "bit1", "bit8"))
        and int(action_descriptor.get("x") or -1) >= 800
        and str(action_descriptor.get("callback") or "").lower() == "004338e0"
        and int(natural_summary.get("action_route_count") or 0) == 0
        and int(natural_summary.get("av_count") or 0) == 0
    )
    natural_slot5_render_begin_blocked = bool(
        natural_slot5
        and natural_slot5.get("proof_class") == "natural_slot5_right_bottom_route"
        and natural_slot5.get("status") in {
            "owner_action_render_begin_stalled",
            "owner_action_ddraw_wait_stalled",
            "owner_action_render_flag_held",
            "owner_action_clickrelease_still_stalled",
        }
        and natural_slot5.get("expected_slot_match") is True
        and natural_slot5.get("load_success") is True
        and natural_slot5.get("owner_bit2_set") is True
        and int(natural_slot5.get("owner_action_route_count") or 0) > 0
        and int(natural_slot5.get("owner_action_draw_count") or 0) == 0
        and natural_slot5.get("owner_action_render_begin_stalled") is True
        and (
            natural_slot5.get("owner_action_ddraw_wait_stalled") is True
            or natural_slot5.get("status") == "owner_action_render_begin_stalled"
        )
        and int(natural_slot5.get("av_count") or 0) == 0
    )
    natural_slot5_copyback_blocked = bool(
        natural_slot5
        and natural_slot5.get("proof_class") == "natural_slot5_right_bottom_route"
        and natural_slot5.get("status") in {
            "owner_action_draw_reached",
            "owner_action_copyback_not_reached",
            "owner_action_435bc0_loop_stalled",
        }
        and natural_slot5.get("expected_slot_match") is True
        and natural_slot5.get("load_success") is True
        and natural_slot5.get("owner_bit2_set") is True
        and int(natural_slot5.get("owner_action_route_count") or 0) > 0
        and int(natural_slot5.get("owner_action_draw_count") or 0) > 0
        and int(natural_slot5.get("render_begin_exit_count") or 0) > 0
        and int(natural_slot5.get("wrapper_copyback_count") or 0) == 0
        and int(natural_slot5.get("av_count") or 0) == 0
    )
    natural_route_blocker_documented = bool(
        natural_route_state_gated or natural_slot5_render_begin_blocked or natural_slot5_copyback_blocked
    )
    hidden_fixture_plan_ready = bool(
        fixture_plan.get("passed")
        and fixture_summary.get("proof_class") == "non_natural_isolated_fixture"
        and fixture_summary.get("promotion_ready") is False
        and fixture_summary.get("stable_stage_should_change") is False
        and _int_value(fixture_summary.get("target_load_slot")) == 0
    )
    natural_load_slot_blocked = bool(
        entry_gap.get("passed")
        and entry_gap.get("promotion_ready") is False
        and entry_gap.get("gap_classification") == "after_main_load_callback_before_load_menu_case_entry"
        and 5 in (entry_summary.get("blocked_rows") or [])
    )
    manual_plan_waiting = bool(
        manual_plan.get("passed")
        and manual_plan.get("proof_ready") is False
        and manual_summary.get("all_commands_have_allow_visible_runtime") is True
    )
    promotion_deferred = bool(
        decision.get("decision") == "defer_stable_promotion"
        and decision.get("stable_stage_should_change") is False
    )

    checks = {
        "controlled_composition_recovered": controlled_composition_recovered,
        "natural_ui_owner_action_rows_absent": natural_ui_absent,
        "natural_route_blocker_documented": natural_route_blocker_documented,
        "hidden_fixture_plan_ready": hidden_fixture_plan_ready,
        "manual_plan_waiting_for_approval": manual_plan_waiting,
        "promotion_deferred": promotion_deferred,
    }
    for name, passed in checks.items():
        if not passed:
            failures.append(f"triage check failed: {name}")

    classification = (
        "controlled_recovered_but_natural_route_blocked"
        if not failures
        else "triage_incomplete_or_stale"
    )
    conclusion = (
        "The right-bottom action/menu surface is not stable-promotable yet. "
        "Controlled composition recovers the lower/right UI, but natural owner/action "
        "copyback remains absent. The current slot 5 natural route reaches owner bit "
        "0x02, 004338E0, Render_Begin exit, and owner/action draw entry, then stops "
        "before wrapper copyback."
    )
    next_proof_options = [
        "run the hidden v8 copyback trace to classify wrapper entry, stock 00435BC0 return, copyback call/return, or loop stall before 0051B86D",
        "collect approved visible/manual DirectInput proof and validate the manual proof manifest",
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
            "compose_evidence_json": str(compose_evidence_json),
            "promotion_decision_json": str(promotion_decision_json),
            "natural_route_json": str(natural_route_json),
            "natural_slot5_summary_json": str(natural_slot5_summary_json),
            "slot_fixture_runtime_plan_json": str(slot_fixture_runtime_plan_json),
            "load_slot_entry_gap_json": str(load_slot_entry_gap_json),
            "manual_run_plan_json": str(manual_run_plan_json),
        },
        "checks": checks,
        "observations": {
            "controlled_bottom_right_ui_corner_nonblack": fullstart.get("bottom_right_ui_corner_nonblack"),
            "controlled_r8c10_nonblack": fullstart.get("bottom_right_tile_r8c10_nonblack"),
            "controlled_r8c11_nonblack": fullstart.get("bottom_right_tile_r8c11_nonblack"),
            "normal_gate_unexplained_blanks": normal_gate.get("visibility_unexplained_blank_cells"),
            "natural_ui_owner_action_rows": natural_ui_owner_action_rows,
            "natural_ui_rbui_panel_draw": natural_ui.get("rbui_panel_draw"),
            "natural_ui_rbui_action_box": natural_ui.get("rbui_action_box"),
            "natural_route_owner_flag_test": owner_flag,
            "natural_route_action_descriptor": action_descriptor,
            "natural_slot5_status": natural_slot5.get("status"),
            "natural_slot5_render_begin_stalled": natural_slot5.get("owner_action_render_begin_stalled"),
            "natural_slot5_ddraw_wait_stalled": natural_slot5.get("owner_action_ddraw_wait_stalled"),
            "natural_slot5_render_begin_late_armed_count": natural_slot5.get("render_begin_late_armed_count"),
            "natural_slot5_last_flip_result": natural_slot5.get("last_render_begin_flip_result"),
            "natural_slot5_last_lost_result": natural_slot5.get("last_render_begin_lost_result"),
            "natural_slot5_render_flag_unique_values": natural_slot5.get("render_flag_unique_values"),
            "natural_slot5_render_flag_held": natural_slot5.get("render_flag_held_during_spin"),
            "natural_slot5_release_count": natural_slot5.get("owner_desc_release_count"),
            "natural_slot5_owner_action_draw_count": natural_slot5.get("owner_action_draw_count"),
            "natural_slot5_wrapper_copyback_count": natural_slot5.get("wrapper_copyback_count"),
            "natural_slot5_copyback_path_marker_count": natural_slot5.get("copyback_path_marker_count"),
            "natural_slot5_435bc0_loop_count": natural_slot5.get("owner_435bc0_loop_count"),
            "natural_slot5_435bc0_return_count": natural_slot5.get("owner_435bc0_return_count"),
            "grid_hit_ok": grid_hit.get("grid_hit_ok"),
            "grid_hit_entry": grid_hit.get("last_grid_entry"),
            "grid_hit_result": grid_hit.get("last_grid_result"),
            "fixture_target_load_slot": fixture_summary.get("target_load_slot"),
            "fixture_proof_class": fixture_summary.get("proof_class"),
            "load_slot_gap_classification": entry_gap.get("gap_classification"),
            "load_slot_blocked_rows": entry_summary.get("blocked_rows"),
            "manual_run_plan_command_count": manual_summary.get("command_count"),
        },
        "conclusion": conclusion,
        "next_proof_options": next_proof_options,
        "failures": failures,
    }


def write_markdown(path: Path, report: dict[str, Any]) -> None:
    observations = report["observations"]
    lines = [
        "# Right-Bottom Blocker Triage",
        "",
        f"- Overall: {status_text(bool(report['passed']))}",
        f"- Generated: `{report['generated_at']}`",
        f"- Runtime policy: {report['runtime_policy']}",
        f"- Guard policy: {report['guard_policy']}",
        f"- Classification: `{report['classification']}`",
        f"- Promotion ready: `{report['promotion_ready']}`",
        f"- stable_stage_should_change: `{report['stable_stage_should_change']}`",
        f"- Conclusion: {report['conclusion']}",
        "",
        "## Checks",
        "",
    ]
    lines.extend(
        f"- `{name}`: `{status_text(bool(passed))}`"
        for name, passed in report["checks"].items()
    )
    lines.extend(
        [
            "",
            "## Observations",
            "",
            f"- Controlled bottom-right corner nonblack: `{observations.get('controlled_bottom_right_ui_corner_nonblack')}`",
            f"- Controlled r8c10/r8c11 nonblack: `{observations.get('controlled_r8c10_nonblack')}` / `{observations.get('controlled_r8c11_nonblack')}`",
            f"- Natural UI owner/action rows: `{observations.get('natural_ui_owner_action_rows')}`",
            f"- Natural route owner flag test: `{observations.get('natural_route_owner_flag_test')}`",
            f"- Natural route action descriptor: `{observations.get('natural_route_action_descriptor')}`",
            f"- Natural slot5 status: `{observations.get('natural_slot5_status')}`",
            f"- Natural slot5 Render_Begin stalled: `{observations.get('natural_slot5_render_begin_stalled')}`",
            f"- Natural slot5 DD_Pump wait stalled: `{observations.get('natural_slot5_ddraw_wait_stalled')}`",
            f"- Natural slot5 Render_Begin late-armed count: `{observations.get('natural_slot5_render_begin_late_armed_count')}`",
            f"- Natural slot5 last flip result: `{observations.get('natural_slot5_last_flip_result')}`",
            f"- Natural slot5 last lost result: `{observations.get('natural_slot5_last_lost_result')}`",
            f"- Natural slot5 render flag unique values: `{observations.get('natural_slot5_render_flag_unique_values')}`",
            f"- Natural slot5 render flag held: `{observations.get('natural_slot5_render_flag_held')}`",
            f"- Natural slot5 click-release rows: `{observations.get('natural_slot5_release_count')}`",
            f"- Natural slot5 owner/action draw count: `{observations.get('natural_slot5_owner_action_draw_count')}`",
            f"- Natural slot5 wrapper copyback count: `{observations.get('natural_slot5_wrapper_copyback_count')}`",
            f"- Natural slot5 copyback path marker count: `{observations.get('natural_slot5_copyback_path_marker_count')}`",
            f"- Natural slot5 00435BC0 loop/return count: `{observations.get('natural_slot5_435bc0_loop_count')}` / `{observations.get('natural_slot5_435bc0_return_count')}`",
            f"- Grid hit: `ok={observations.get('grid_hit_ok')}`, `entry={observations.get('grid_hit_entry')}`, `result={observations.get('grid_hit_result')}`",
            f"- Fixture proof class / load slot: `{observations.get('fixture_proof_class')}` / `{observations.get('fixture_target_load_slot')}`",
            f"- Legacy load-slot gap / blocked rows: `{observations.get('load_slot_gap_classification')}` / `{observations.get('load_slot_blocked_rows')}`",
            f"- Manual run-plan command count: `{observations.get('manual_run_plan_command_count')}`",
            "",
            "## Next Proof Options",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in report["next_proof_options"])
    if report["failures"]:
        lines.extend(["", "## Failures", ""])
        lines.extend(f"- {failure}" for failure in report["failures"])
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compose-evidence-json", type=Path, default=DEFAULT_COMPOSE_EVIDENCE_JSON)
    parser.add_argument("--promotion-decision-json", type=Path, default=DEFAULT_PROMOTION_DECISION_JSON)
    parser.add_argument("--natural-route-json", type=Path, default=DEFAULT_NATURAL_ROUTE_JSON)
    parser.add_argument("--natural-slot5-summary-json", type=Path, default=DEFAULT_NATURAL_SLOT5_SUMMARY_JSON)
    parser.add_argument(
        "--slot-fixture-runtime-plan-json",
        type=Path,
        default=DEFAULT_SLOT_FIXTURE_RUNTIME_PLAN_JSON,
    )
    parser.add_argument("--load-slot-entry-gap-json", type=Path, default=DEFAULT_LOAD_SLOT_ENTRY_GAP_JSON)
    parser.add_argument("--manual-run-plan-json", type=Path, default=DEFAULT_MANUAL_RUN_PLAN_JSON)
    parser.add_argument("--write-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--write-markdown", "--write-md", dest="write_markdown", type=Path, default=DEFAULT_MD)
    parser.add_argument("--require-pass", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_triage(
        compose_evidence_json=args.compose_evidence_json,
        promotion_decision_json=args.promotion_decision_json,
        natural_route_json=args.natural_route_json,
        natural_slot5_summary_json=args.natural_slot5_summary_json,
        slot_fixture_runtime_plan_json=args.slot_fixture_runtime_plan_json,
        load_slot_entry_gap_json=args.load_slot_entry_gap_json,
        manual_run_plan_json=args.manual_run_plan_json,
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
