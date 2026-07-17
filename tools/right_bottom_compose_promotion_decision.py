#!/usr/bin/env python3
"""Record a repo-only right-bottom composition promotion decision.

The right-bottom composition patch is intentionally a validation-stage patch.
This helper turns the current repo-only evidence checks into an explicit
promotion decision so the stable HD map stage is not changed silently.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import manual_directinput_checklist
import promotion_override_manifest


DEFAULT_REFRESH_JSON = Path("captures/current/current-evidence-refresh-current.json")
DEFAULT_DECISION_JSON = Path("captures/current/right-bottom-compose-promotion-decision-current.json")
DEFAULT_DECISION_MD = Path("captures/current/right-bottom-compose-promotion-decision-current.md")
DEFAULT_STABLE_STAGE = (
    "gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-"
    "presentbounds-minimapright-dynvswitch"
)
DEFAULT_VALIDATION_STAGE = (
    "gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-"
    "presentbounds-minimapright-dynvswitch-rightbottomcompose"
)

REQUIRED_CHECKS = (
    "right_bottom_compose_patch",
    "right_bottom_compose_fullstart_route",
    "right_bottom_compose_normal_gate",
    "right_bottom_compose_ui_probe",
    "right_bottom_grid_hit",
    "right_bottom_natural_route_guard",
    "right_bottom_route_timing_guard",
)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _check_failed(name: str, check: dict[str, Any] | None) -> list[str]:
    if check is None:
        return [f"{name} is missing"]
    if check.get("passed"):
        return []
    failures = check.get("failures") or ["failed without a detailed reason"]
    return [f"{name}: {failure}" for failure in failures]


def validate_manual_input_proof(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {
            "path": None,
            "supplied": False,
            "valid": False,
            "summary": {
                "executable_sha256": None,
                "checked_item_count": 0,
            },
            "failures": [],
        }

    proof, failures = manual_directinput_checklist.validate_manual_proof(path)
    return {
        "path": str(path),
        "supplied": True,
        "valid": proof is not None and not failures,
        "summary": {
            "executable_sha256": proof.get("executable_sha256") if proof else None,
            "checked_item_count": len(proof.get("checked_items", [])) if proof else 0,
        },
        "failures": failures,
    }


def build_decision_from_checks(args: argparse.Namespace, checks: dict[str, Any]) -> dict[str, Any]:
    failures: list[str] = []
    for name in REQUIRED_CHECKS:
        failures.extend(_check_failed(name, checks.get(name)))

    patch_summary = (checks.get("right_bottom_compose_patch") or {}).get("summary") or {}
    fullstart_summary = (checks.get("right_bottom_compose_fullstart_route") or {}).get("summary") or {}
    normal_summary = (checks.get("right_bottom_compose_normal_gate") or {}).get("summary") or {}
    ui_summary = (checks.get("right_bottom_compose_ui_probe") or {}).get("summary") or {}
    grid_summary = (checks.get("right_bottom_grid_hit") or {}).get("summary") or {}
    natural_route_summary = (checks.get("right_bottom_natural_route_guard") or {}).get("summary") or {}
    timing_summary = (checks.get("right_bottom_route_timing_guard") or {}).get("summary") or {}

    natural_owner_rows = int(ui_summary.get("rbui_panel_draw") or 0) + int(ui_summary.get("rbui_action_box") or 0)
    ui_fixture = ui_summary.get("fixture") or {}
    ui_fixture_markers = ui_fixture.get("marker_counts") or {}
    # user ruling 2026-07-14: slot5-as-slot0 fixture accepted as natural-draw evidence.
    # Bare-map rows-absent is the physically-correct engine result; the accepted fixture
    # run supplies the natural-draw proof under the same marker requirements.
    fixture_natural_draw_accepted = bool(
        ui_summary.get("natural_draw_source") == "slot5_as_slot0_fixture"
        and int(ui_fixture_markers.get("NOWNER_435BC0_PANEL_DRAW") or 0) >= 1
        and int(ui_fixture_markers.get("NOWNER_435BC0_GRID_DRAW") or 0) >= 1
        and int(ui_fixture_markers.get("NOWNER_WRAPPER_COPYBACK_DONE") or 0) >= 1
        and ui_fixture.get("av_count") == 0
    )
    if natural_owner_rows <= 0 and not fixture_natural_draw_accepted:
        failures.append(
            "right-bottom natural UI probe did not enter owner/action draw rows and no accepted "
            "slot5-as-slot0 fixture natural-draw evidence was recorded"
        )
    natural_owner_flag = natural_route_summary.get("owner_flag_test") or {}
    natural_action_descriptor = natural_route_summary.get("action_descriptor") or {}
    if natural_route_summary.get("state_gated_by_owner_flag") is not True:
        failures.append("right-bottom natural route guard did not prove the owner-flag save-state gate")
    if int(natural_route_summary.get("action_route_count") or 0) != 0:
        failures.append("right-bottom natural route unexpectedly entered owner/action renderer rows")
    if int(natural_route_summary.get("av_count") or 0):
        failures.append(f"right-bottom natural route guard has AV rows: {natural_route_summary.get('av_count')}")
    if natural_owner_flag.get("owner_flag") != "0x00":
        failures.append(f"right-bottom natural route owner flag was {natural_owner_flag.get('owner_flag')}, expected 0x00")
    if any(int(natural_owner_flag.get(bit) or 0) for bit in ("bit2", "bit1", "bit8")):
        failures.append(f"right-bottom natural route owner flag bits were {natural_owner_flag}, expected all zero")
    if str(natural_action_descriptor.get("callback") or "").lower() != "004338e0":
        failures.append("right-bottom natural route action descriptor callback was not 004338E0")
    if int(natural_action_descriptor.get("x") or -1) < 800:
        failures.append("right-bottom natural route action descriptor was not off-screen")

    evidence_passed = not failures
    manual_input_proof = validate_manual_input_proof(getattr(args, "manual_input_proof", None))
    failures.extend(manual_input_proof["failures"])
    manual_input_proof_valid = bool(manual_input_proof["valid"])
    cdb_only_override = bool(getattr(args, "allow_cdb_only_promotion", False))
    override_manifest = promotion_override_manifest.validate_manifest(
        getattr(args, "promotion_override_manifest", None),
        expected_target_scope="right_bottom_compose",
        expected_candidate_stage=args.validation_stage,
        expected_candidate_sha256=patch_summary.get("candidate_sha256"),
    )
    failures.extend(override_manifest["failures"])
    override_manifest_valid = bool(override_manifest["valid"])
    bare_override_blocked = bool(cdb_only_override and not override_manifest["supplied"])
    if bare_override_blocked:
        failures.append(
            "bare --allow-cdb-only-promotion is blocked; supply --promotion-override-manifest"
        )
    evidence_ready = (
        evidence_passed
        and not manual_input_proof["failures"]
        and not override_manifest["failures"]
        and not bare_override_blocked
    )

    if evidence_ready and manual_input_proof_valid:
        decision = "eligible_for_stable_promotion"
        stable_stage_should_change = True
        reasons = [
            "right-bottom validation evidence gates are passing",
            f"manual/real input proof was supplied: {args.manual_input_proof}",
        ]
    elif evidence_ready and override_manifest_valid:
        decision = "eligible_for_override_manifest_promotion"
        stable_stage_should_change = True
        reasons = [
            "right-bottom validation evidence gates are passing",
            f"CDB/proxy-only promotion override manifest is valid: {override_manifest['path']}",
        ]
    else:
        decision = "defer_stable_promotion"
        stable_stage_should_change = False
        reasons = [
            "right-bottom validation evidence gates are passing"
            if evidence_passed
            else "one or more right-bottom validation evidence gates are not passing",
            "current proof is repo-only CDB/proxy evidence",
            "controlled native grid-hit proof is present"
            if grid_summary.get("grid_hit_ok")
            else "controlled native grid-hit proof is missing",
            "route timing/order guard is present"
            if timing_summary.get("candidate_sha256")
            else "route timing/order guard is missing",
            "natural route owner-flag save-state proof is present"
            if natural_route_summary.get("state_gated_by_owner_flag")
            else "natural route owner-flag save-state proof is missing",
            "natural route action descriptor is parked off-screen"
            if int(natural_action_descriptor.get("x") or -1) >= 800
            else "natural route action descriptor is not parked off-screen",
            "manual/visible DirectInput validation has not been supplied"
            if not manual_input_proof["supplied"]
            else "manual/visible DirectInput proof was supplied but failed manifest validation",
            "promotion override manifest is valid"
            if override_manifest_valid
            else (
                "bare CDB-only promotion flag is blocked without a manifest"
                if bare_override_blocked
                else "promotion override manifest has not been supplied"
            ),
            (
                "natural right-bottom UI probe has owner/action draw evidence"
                if natural_owner_rows > 0
                else (
                    "natural draw evidence accepted from the slot5-as-slot0 fixture "
                    "(user ruling 2026-07-14: slot5-as-slot0 fixture accepted as natural-draw evidence)"
                    if fixture_natural_draw_accepted
                    else "natural right-bottom UI probe does not enter owner/action draw rows"
                )
            ),
            "visible/manual runs require explicit user approval",
        ]

    next_actions = []
    if decision == "defer_stable_promotion":
        next_actions.extend(
            [
                "keep the patcher default stable HD map stage unchanged",
                "keep right-bottom composition hooks scoped to rightbottomcompose",
                "continue with repo-only or hidden-desktop/CDB route and input safety evidence",
                "request explicit approval before any visible/manual input validation",
            ]
        )
    else:
        next_actions.extend(
            [
                "update the patcher default or stable stage intentionally",
                "rerun patch byte, evidence refresh, map, and input gates after any stage change",
                "document the promotion scope and evidence class",
            ]
        )

    return {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "passed": not failures,
        "decision": decision,
        "stable_stage_should_change": stable_stage_should_change,
        "current_stable_stage": args.current_stable_stage,
        "validation_stage": args.validation_stage,
        "candidate_sha256": patch_summary.get("candidate_sha256"),
        "manual_input_proof": str(args.manual_input_proof) if args.manual_input_proof else None,
        "manual_input_proof_supplied": bool(manual_input_proof["supplied"]),
        "manual_input_proof_valid": manual_input_proof_valid,
        "manual_input_proof_summary": manual_input_proof["summary"],
        "allow_cdb_only_promotion": cdb_only_override,
        "bare_cdb_only_promotion_blocked": bare_override_blocked,
        "promotion_override_manifest": override_manifest["path"],
        "promotion_override_manifest_supplied": bool(override_manifest["supplied"]),
        "promotion_override_manifest_valid": override_manifest_valid,
        "promotion_override_manifest_summary": override_manifest["summary"],
        "natural_draw_source": ui_summary.get("natural_draw_source"),
        "fixture_natural_draw_accepted": fixture_natural_draw_accepted,
        "fixture_natural_draw": ui_fixture or None,
        "required_checks": {name: bool((checks.get(name) or {}).get("passed")) for name in REQUIRED_CHECKS},
        "evidence": {
            "patch": patch_summary,
            "fullstart_route": fullstart_summary,
            "normal_gate": normal_summary,
            "natural_ui_probe": ui_summary,
            "controlled_grid_hit": grid_summary,
            "natural_route_guard": natural_route_summary,
            "route_timing_guard": timing_summary,
        },
        "reasons": reasons,
        "next_actions": next_actions,
        "failures": failures,
    }


def build_decision(args: argparse.Namespace) -> dict[str, Any]:
    refresh = load_json(args.refresh_json)
    return build_decision_from_checks(args, refresh.get("checks", {}))


def print_decision(decision: dict[str, Any]) -> None:
    print(f"decision-record: {'PASS' if decision['passed'] else 'FAIL'}")
    print(f"decision: {decision['decision']}")
    print(f"stable-stage-should-change: {decision['stable_stage_should_change']}")
    print(f"current-stable-stage: {decision['current_stable_stage']}")
    print(f"validation-stage: {decision['validation_stage']}")
    print(f"candidate-sha256: {decision.get('candidate_sha256')}")
    print(f"manual-input-proof-valid: {decision['manual_input_proof_valid']}")
    print(f"natural-draw-source: {decision.get('natural_draw_source')}")
    print(f"fixture-natural-draw-accepted: {decision.get('fixture_natural_draw_accepted')}")
    print(f"promotion-override-manifest-valid: {decision['promotion_override_manifest_valid']}")
    print(f"bare-cdb-only-promotion-blocked: {decision['bare_cdb_only_promotion_blocked']}")
    print("required-checks:")
    for name, passed in decision["required_checks"].items():
        print(f"  - {name}: {'PASS' if passed else 'FAIL'}")
    print("reasons:")
    for reason in decision["reasons"]:
        print(f"  - {reason}")
    if decision["failures"]:
        print("failures:")
        for failure in decision["failures"]:
            print(f"  - {failure}")


def write_markdown(path: Path, decision: dict[str, Any]) -> None:
    evidence = decision["evidence"]
    lines = [
        "# Right-Bottom Compose Promotion Decision",
        "",
        f"- Decision record: {'PASS' if decision['passed'] else 'FAIL'}",
        f"- Decision: `{decision['decision']}`",
        f"- Stable stage should change: `{decision['stable_stage_should_change']}`",
        f"- Generated: `{decision['generated_at']}`",
        f"- Current stable stage: `{decision['current_stable_stage']}`",
        f"- Validation stage: `{decision['validation_stage']}`",
        f"- Candidate SHA-256: `{decision['candidate_sha256']}`",
        f"- Manual input proof: `{decision['manual_input_proof']}`",
        f"- Manual input proof supplied: `{decision['manual_input_proof_supplied']}`",
        f"- Manual input proof valid: `{decision['manual_input_proof_valid']}`",
        f"- Manual input proof SHA-256: `{decision['manual_input_proof_summary'].get('executable_sha256')}`",
        f"- Manual input proof checked items: `{decision['manual_input_proof_summary'].get('checked_item_count')}`",
        f"- CDB-only promotion override: `{decision['allow_cdb_only_promotion']}`",
        f"- Bare CDB-only promotion blocked: `{decision['bare_cdb_only_promotion_blocked']}`",
        f"- Promotion override manifest: `{decision['promotion_override_manifest']}`",
        f"- Promotion override manifest supplied: `{decision['promotion_override_manifest_supplied']}`",
        f"- Promotion override manifest valid: `{decision['promotion_override_manifest_valid']}`",
        f"- Promotion override scope: `{decision['promotion_override_manifest_summary'].get('target_scope')}`",
        f"- Promotion override SHA-256: `{decision['promotion_override_manifest_summary'].get('candidate_sha256')}`",
        "",
        "## Required Checks",
        "",
    ]
    lines.extend(
        f"- `{name}`: `{'PASS' if passed else 'FAIL'}`"
        for name, passed in decision["required_checks"].items()
    )
    lines.extend(
        [
            "",
            "## Evidence Summary",
            "",
            f"- Patch group: `{evidence['patch'].get('right_bottom_patch_group')}`",
            f"- Current HD map gate: `{evidence['patch'].get('current_hd_map_gate')}`",
            f"- Full-start route ready: `{evidence['fullstart_route'].get('ready')}`",
            f"- Full-start route AV count: `{evidence['fullstart_route'].get('av_count')}`",
            f"- Normal map gate surface: `{evidence['normal_gate'].get('surface')}`",
            f"- Normal gate unexplained blanks: `{evidence['normal_gate'].get('visibility_unexplained_blank_cells')}`",
            f"- Natural UI descriptor switch rows: `{evidence['natural_ui_probe'].get('rbui_desc_switch')}`",
            f"- Natural UI owner/action rows: `RBUI_PANEL_DRAW={evidence['natural_ui_probe'].get('rbui_panel_draw')}`, `RBUI_ACTION_BOX={evidence['natural_ui_probe'].get('rbui_action_box')}`",
            f"- Natural draw source: `{decision.get('natural_draw_source')}`",
            f"- Fixture natural-draw accepted: `{decision.get('fixture_natural_draw_accepted')}`",
            f"- Fixture natural-draw evidence: `{decision.get('fixture_natural_draw')}`",
            f"- Controlled grid hit: `grid_hit_ok={evidence['controlled_grid_hit'].get('grid_hit_ok')}`, `entry={evidence['controlled_grid_hit'].get('last_grid_entry')}`, `result={evidence['controlled_grid_hit'].get('last_grid_result')}`",
            f"- Controlled grid hit AV count: `{evidence['controlled_grid_hit'].get('av_count')}`",
            f"- Natural route state-gated: `{evidence['natural_route_guard'].get('state_gated_by_owner_flag')}`",
            f"- Natural route owner flag test: `{evidence['natural_route_guard'].get('owner_flag_test')}`",
            f"- Natural route action descriptor: `{evidence['natural_route_guard'].get('action_descriptor')}`",
            f"- Natural route owner/action rows / AV rows: `{evidence['natural_route_guard'].get('action_route_count')}` / `{evidence['natural_route_guard'].get('av_count')}`",
            f"- Route timing guard ordered markers: `patch={evidence['route_timing_guard'].get('patch_route_ordered_markers')}`, `fullstart={evidence['route_timing_guard'].get('fullstart_route_ordered_markers')}`, `grid={evidence['route_timing_guard'].get('grid_route_ordered_markers')}`",
            f"- Route timing guard failure exits / AV rows: `{evidence['route_timing_guard'].get('failure_exit_count')}` / `{evidence['route_timing_guard'].get('av_count')}`",
            f"- Bottom-right corner nonblack: `{evidence['fullstart_route'].get('bottom_right_ui_corner_nonblack')}`",
            f"- r8c10 nonblack: `{evidence['fullstart_route'].get('bottom_right_tile_r8c10_nonblack')}`",
            f"- r8c11 nonblack: `{evidence['fullstart_route'].get('bottom_right_tile_r8c11_nonblack')}`",
            "",
            "## Reasons",
            "",
        ]
    )
    lines.extend(f"- {reason}" for reason in decision["reasons"])
    lines.extend(["", "## Next Actions", ""])
    lines.extend(f"- {action}" for action in decision["next_actions"])
    if decision["failures"]:
        lines.extend(["", "## Failures", ""])
        lines.extend(f"- {failure}" for failure in decision["failures"])
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh-json", type=Path, default=DEFAULT_REFRESH_JSON)
    parser.add_argument("--current-stable-stage", default=DEFAULT_STABLE_STAGE)
    parser.add_argument("--validation-stage", default=DEFAULT_VALIDATION_STAGE)
    parser.add_argument("--manual-input-proof", type=Path)
    parser.add_argument("--allow-cdb-only-promotion", action="store_true")
    parser.add_argument("--promotion-override-manifest", type=Path)
    parser.add_argument("--write-json", type=Path, default=DEFAULT_DECISION_JSON)
    parser.add_argument("--write-markdown", type=Path, default=DEFAULT_DECISION_MD)
    parser.add_argument("--require-pass", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    decision = build_decision(args)
    print_decision(decision)
    if args.write_json:
        args.write_json.parent.mkdir(parents=True, exist_ok=True)
        args.write_json.write_text(json.dumps(decision, indent=2) + "\n", encoding="utf-8")
    if args.write_markdown:
        write_markdown(args.write_markdown, decision)
    if args.require_pass and not decision["passed"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
