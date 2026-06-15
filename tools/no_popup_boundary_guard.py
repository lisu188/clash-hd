#!/usr/bin/env python3
"""Verify the current no-popup boundary guards are complete and linked.

This is a repo-only aggregate guard. It reads existing refresh/evidence data
and does not launch Clash95, CDB, wrappers, PowerShell, or any visible GUI
process.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_REFRESH_JSON = Path("captures/current/current-evidence-refresh-current.json")
DEFAULT_EVIDENCE_INDEX = Path("captures/current/hd-map-evidence-current.md")
DEFAULT_JSON = Path("captures/current/no-popup-boundary-guard-current.json")
DEFAULT_MD = Path("captures/current/no-popup-boundary-guard-current.md")
RUNTIME_POLICY = "repo-only aggregate inspection; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows"

REQUIRED_GUARDS = {
    "stable_stage_guard": {
        "markdown": "stable-stage-guard-current.md",
        "purpose": "validation-only groups stay out of the stable HD map stage",
    },
    "exe_artifact_guard": {
        "markdown": "exe-artifact-guard-current.md",
        "purpose": "repository contains no tracked or filesystem .exe artifacts",
    },
    "surface_dump_policy_guard": {
        "markdown": "surface-dump-policy-guard-current.md",
        "purpose": "surface-dump launcher defaults to hidden desktop",
    },
    "visible_runtime_launcher_guard": {
        "markdown": "visible-runtime-launcher-guard-current.md",
        "purpose": "legacy visible-runtime launchers require explicit approval switch",
    },
    "no_visible_runtime_guard": {
        "markdown": "no-visible-runtime-guard-current.md",
        "purpose": "referenced CDB surface-dump evidence is hidden-desktop",
    },
    "process_hygiene_guard": {
        "markdown": "process-hygiene-guard-current.md",
        "purpose": "no cdb.exe or clash95* process is left running",
    },
}

REQUIRED_SUPPORTING_REPORTS = {
    "no_popup_map_evidence": {
        "markdown": "no-popup-map-evidence-current.md",
        "purpose": "compact no-popup map visibility and forced-visible baseline",
    },
    "no_popup_map_evidence_tests": {
        "markdown": "no-popup-map-evidence-tests-current.md",
        "purpose": "fixture regression coverage for the no-popup map evidence matrix",
    },
    "no_visible_runtime_guard_tests": {
        "markdown": "no-visible-runtime-guard-tests-current.md",
        "purpose": "fixture regression coverage for the no-visible runtime guard",
    },
    "no_popup_guard_tests": {
        "markdown": "no-popup-guard-tests-current.md",
        "purpose": "fixture regression coverage for the no-popup guard set",
    },
    "visible_runtime_launcher_guard_tests": {
        "markdown": "visible-runtime-launcher-guard-tests-current.md",
        "purpose": "fixture regression coverage for legacy visible-runtime launcher gates",
    },
    "python_runtime_safety_guard": {
        "markdown": "python-runtime-safety-current.md",
        "purpose": "Python helpers with runtime/window/input APIs are gated, exempt, or fail closed",
    },
    "python_runtime_safety_guard_tests": {
        "markdown": "python-runtime-safety-tests-current.md",
        "purpose": "fixture regression coverage for risky Python helper classification",
    },
    "patch_definition_guard": {
        "markdown": "patch-definition-current.md",
        "purpose": "patch stage definitions keep stable and validation-only groups separated",
    },
    "patch_definition_guard_tests": {
        "markdown": "patch-definition-tests-current.md",
        "purpose": "fixture regression coverage for patch definition drift and overlap failures",
    },
    "capture_corpus_index": {
        "markdown": "capture-corpus-index-current.md",
        "purpose": "read-only capture corpus index prevents stale visible-era artifacts becoming current blockers",
    },
    "capture_corpus_index_tests": {
        "markdown": "capture-corpus-index-tests-current.md",
        "purpose": "fixture regression coverage for capture reference and stale artifact classification",
    },
    "current_completion_summary": {
        "markdown": "current-completion-summary-current.md",
        "purpose": "percentage progress report stays generated from current evidence gates",
    },
    "current_completion_summary_tests": {
        "markdown": "current-completion-summary-tests-current.md",
        "purpose": "fixture regression coverage for the generated percentage progress report",
    },
    "process_hygiene_guard_tests": {
        "markdown": "process-hygiene-guard-tests-current.md",
        "purpose": "fixture regression coverage for the process hygiene guard",
    },
    "manual_directinput_checklist": {
        "markdown": "manual-directinput-validation-checklist-current.md",
        "purpose": "remaining manual DirectInput targets stay enumerated and promotion remains blocked",
    },
    "manual_directinput_checklist_tests": {
        "markdown": "manual-directinput-validation-checklist-tests-current.md",
        "purpose": "fixture regression coverage for the manual DirectInput checklist",
    },
    "manual_directinput_proof_template": {
        "markdown": "manual-directinput-proof-template-current.md",
        "purpose": "manual DirectInput proof manifest template stays visible and non-promoting",
    },
    "manual_directinput_proof_template_tests": {
        "markdown": "manual-directinput-proof-template-tests-current.md",
        "purpose": "fixture regression coverage for the manual DirectInput proof template",
    },
    "manual_directinput_run_plan": {
        "markdown": "manual-directinput-run-plan-current.md",
        "purpose": "approval-gated visible/manual DirectInput command plan remains non-executing and non-promoting",
    },
    "manual_directinput_run_plan_tests": {
        "markdown": "manual-directinput-run-plan-tests-current.md",
        "purpose": "fixture regression coverage for the manual DirectInput run plan",
    },
    "promotion_override_guard": {
        "markdown": "promotion-override-guard-current.md",
        "purpose": "CDB-only promotion override remains inactive in current evidence",
    },
    "promotion_override_guard_tests": {
        "markdown": "promotion-override-guard-tests-current.md",
        "purpose": "fixture regression coverage for the promotion override guard",
    },
    "promotion_override_manifest": {
        "markdown": "promotion-override-manifest-current.md",
        "purpose": "CDB-only promotion override manifest remains absent or strictly validated",
    },
    "promotion_override_manifest_tests": {
        "markdown": "promotion-override-manifest-tests-current.md",
        "purpose": "fixture regression coverage for strict CDB-only promotion override manifests",
    },
    "handoff_freshness_guard": {
        "markdown": "handoff-freshness-guard-current.md",
        "purpose": "current handoff docs point at the latest no-popup blockers",
    },
    "handoff_freshness_guard_tests": {
        "markdown": "handoff-freshness-guard-tests-current.md",
        "purpose": "fixture regression coverage for the handoff freshness guard",
    },
    "right_bottom_compose_promotion_decision_tests": {
        "markdown": "right-bottom-compose-promotion-decision-tests-current.md",
        "purpose": "fixture regression coverage for the right-bottom compose promotion decision",
    },
    "right_bottom_compose_evidence_matrix_tests": {
        "markdown": "right-bottom-compose-evidence-matrix-tests-current.md",
        "purpose": "fixture regression coverage for the right-bottom compose evidence matrix",
    },
    "right_bottom_blocker_triage": {
        "markdown": "right-bottom-blocker-triage-current.md",
        "purpose": "compact non-promoting triage of the current right-bottom action-menu blocker",
    },
    "right_bottom_blocker_triage_tests": {
        "markdown": "right-bottom-blocker-triage-tests-current.md",
        "purpose": "fixture regression coverage for the right-bottom action-menu blocker triage",
    },
    "right_bottom_visual_artifact_guard": {
        "markdown": "right-bottom-visual-artifact-guard-current.md",
        "purpose": "right-bottom natural UI stripe/layout artifact remains explicitly non-promoting",
    },
    "right_bottom_visual_artifact_guard_tests": {
        "markdown": "right-bottom-visual-artifact-guard-tests-current.md",
        "purpose": "fixture regression coverage for the right-bottom visual artifact guard",
    },
    "right_bottom_grid_hit": {
        "markdown": "right-bottom-grid-hit-current.md",
        "purpose": "controlled no-popup native grid-hit proof for the right-bottom compose validation stage",
    },
    "right_bottom_grid_hit_summary_tests": {
        "markdown": "right-bottom-grid-hit-summary-tests-current.md",
        "purpose": "fixture regression coverage for the right-bottom grid-hit parser",
    },
    "right_bottom_grid_hit_probe_guard": {
        "markdown": "right-bottom-grid-hit-probe-guard-current.md",
        "purpose": "focused right-bottom grid-hit probe keeps proven no-popup callsites",
    },
    "right_bottom_grid_hit_probe_guard_tests": {
        "markdown": "right-bottom-grid-hit-probe-guard-tests-current.md",
        "purpose": "fixture regression coverage for the right-bottom grid-hit probe guard",
    },
    "right_bottom_natural_route_guard": {
        "markdown": "right-bottom-natural-route-guard-current.md",
        "purpose": "natural right-bottom castle/action route is classified as owner-flag save-state gated",
    },
    "right_bottom_natural_route_guard_tests": {
        "markdown": "right-bottom-natural-route-guard-tests-current.md",
        "purpose": "fixture regression coverage for the right-bottom natural-route guard",
    },
    "right_bottom_slot_fixture_plan": {
        "markdown": "right-bottom-slot-fixture-plan-current.md",
        "purpose": "non-promoting isolated slot5-as-slot0 fixture plan for the right-bottom owner/action route",
    },
    "right_bottom_slot_fixture_plan_tests": {
        "markdown": "right-bottom-slot-fixture-plan-tests-current.md",
        "purpose": "fixture regression coverage for the right-bottom isolated slot fixture plan",
    },
    "right_bottom_slot_fixture_script_guard": {
        "markdown": "right-bottom-slot-fixture-script-guard-current.md",
        "purpose": "source guard for the dry-run right-bottom slot fixture preparation helper",
    },
    "right_bottom_slot_fixture_script_guard_tests": {
        "markdown": "right-bottom-slot-fixture-script-guard-tests-current.md",
        "purpose": "fixture regression coverage for the right-bottom slot fixture preparation helper guard",
    },
    "right_bottom_slot_fixture_runtime_plan": {
        "markdown": "right-bottom-slot-fixture-runtime-plan-current.md",
        "purpose": "hidden-desktop command plan for the non-promoting right-bottom isolated slot fixture",
    },
    "right_bottom_slot_fixture_runtime_plan_tests": {
        "markdown": "right-bottom-slot-fixture-runtime-plan-tests-current.md",
        "purpose": "fixture regression coverage for the right-bottom slot fixture runtime command plan",
    },
    "right_bottom_slot_fixture_result_summary_tests": {
        "markdown": "right-bottom-slot-fixture-result-summary-tests-current.md",
        "purpose": "fixture regression coverage for future right-bottom slot fixture CDB result classification",
    },
    "load_slot_route_limit_guard": {
        "markdown": "load-slot-route-limit-current.md",
        "purpose": "load-slot route boundary keeps slot5/right-bottom save-state candidate classified as route-harness blocked",
    },
    "load_slot_route_limit_guard_tests": {
        "markdown": "load-slot-route-limit-tests-current.md",
        "purpose": "fixture regression coverage for the load-slot route limit guard",
    },
    "load_slot_timeout_phase": {
        "markdown": "load-slot-timeout-phase-current.md",
        "purpose": "load-slot timeout phase keeps rows 3-5 classified as pre-load-menu-loop stalls",
    },
    "load_slot_timeout_phase_tests": {
        "markdown": "load-slot-timeout-phase-tests-current.md",
        "purpose": "fixture regression coverage for the load-slot timeout phase classifier",
    },
    "load_slot_entry_gap": {
        "markdown": "load-slot-entry-gap-current.md",
        "purpose": "load-slot entry gap keeps rows 3-5 classified as stopping before case-5 entry",
    },
    "load_slot_entry_gap_tests": {
        "markdown": "load-slot-entry-gap-tests-current.md",
        "purpose": "fixture regression coverage for the load-slot entry gap classifier",
    },
    "load_slot_transition_probe_guard": {
        "markdown": "load-slot-transition-probe-guard-current.md",
        "purpose": "focused late-entry load-slot transition probe avoids early descriptor forcing",
    },
    "load_slot_transition_probe_guard_tests": {
        "markdown": "load-slot-transition-probe-guard-tests-current.md",
        "purpose": "fixture regression coverage for the load-slot transition probe guard",
    },
    "load_slot_transition_run_plan": {
        "markdown": "load-slot-transition-run-plan-current.md",
        "purpose": "hidden-desktop command plan for the rows 3-5 load-slot transition blocker",
    },
    "load_slot_transition_run_plan_tests": {
        "markdown": "load-slot-transition-run-plan-tests-current.md",
        "purpose": "fixture regression coverage for the load-slot transition run plan",
    },
    "load_slot_transition_geometry_guard": {
        "markdown": "load-slot-transition-geometry-guard-current.md",
        "purpose": "row geometry guard for the rows 3-5 load-slot transition plan",
    },
    "load_slot_transition_geometry_guard_tests": {
        "markdown": "load-slot-transition-geometry-guard-tests-current.md",
        "purpose": "fixture regression coverage for the load-slot transition row geometry guard",
    },
    "load_slot_transition_probe_preview": {
        "markdown": "load-slot-transition-probe-preview-current.md",
        "purpose": "row-specific generated CDB preview for the rows 3-5 load-slot transition probes",
    },
    "load_slot_transition_probe_preview_tests": {
        "markdown": "load-slot-transition-probe-preview-tests-current.md",
        "purpose": "fixture regression coverage for row-specific generated transition probe previews",
    },
    "load_slot_transition_readiness": {
        "markdown": "load-slot-transition-readiness-current.md",
        "purpose": "aggregate hidden transition readiness matrix for rows 3-5",
    },
    "load_slot_transition_readiness_tests": {
        "markdown": "load-slot-transition-readiness-tests-current.md",
        "purpose": "fixture regression coverage for the load-slot transition readiness matrix",
    },
    "load_slot_transition_summary_tests": {
        "markdown": "load-slot-transition-summary-tests-current.md",
        "purpose": "fixture regression coverage for future LSTRANS log classification",
    },
    "right_bottom_owner_flag_static_guard": {
        "markdown": "right-bottom-owner-flag-static-guard-current.md",
        "purpose": "static original-exe byte guard for command-99 owner-loop and action owner-flag gates",
    },
    "right_bottom_owner_flag_static_guard_tests": {
        "markdown": "right-bottom-owner-flag-static-guard-tests-current.md",
        "purpose": "fixture regression coverage for the right-bottom owner-flag static guard",
    },
    "right_bottom_owner_flag_inventory": {
        "markdown": "right-bottom-owner-flag-inventory-current.md",
        "purpose": "right-bottom owner-flag inventory keeps natural and forced action-route evidence classified",
    },
    "right_bottom_owner_flag_inventory_tests": {
        "markdown": "right-bottom-owner-flag-inventory-tests-current.md",
        "purpose": "fixture regression coverage for the right-bottom owner-flag inventory",
    },
    "right_bottom_route_timing_guard": {
        "markdown": "right-bottom-route-timing-guard-current.md",
        "purpose": "right-bottom patch/full-start/grid marker ordering remains stable",
    },
    "right_bottom_route_timing_guard_tests": {
        "markdown": "right-bottom-route-timing-guard-tests-current.md",
        "purpose": "fixture regression coverage for the right-bottom route timing guard",
    },
    "castle_overview_baseline_recheck": {
        "markdown": "castle-overview-baseline-recheck-current.md",
        "purpose": "current fixed castle overview and barracks no-popup baselines remain attached",
    },
    "castle_overview_baseline_recheck_tests": {
        "markdown": "castle-overview-baseline-recheck-tests-current.md",
        "purpose": "fixture regression coverage for the castle overview baseline recheck",
    },
    "castle_owner_records_summary_tests": {
        "markdown": "castle-owner-records-summary-tests-current.md",
        "purpose": "fixture regression coverage for the castle owner-record parser",
    },
    "castle_overview_evidence_matrix_tests": {
        "markdown": "castle-overview-evidence-matrix-tests-current.md",
        "purpose": "fixture regression coverage for the castle overview evidence matrix",
    },
    "castle_overview_gate_tests": {
        "markdown": "castle-overview-gate-tests-current.md",
        "purpose": "fixture regression coverage for the castle overview visual/catalog gate",
    },
    "castle_overview_hitbox_summary_tests": {
        "markdown": "castle-overview-hitbox-summary-tests-current.md",
        "purpose": "fixture regression coverage for the focused castle overview hitbox parser",
    },
    "castle_overview_hitmap_summary_tests": {
        "markdown": "castle-overview-hitmap-summary-tests-current.md",
        "purpose": "fixture regression coverage for the castle overview raw hitmap parser",
    },
    "castle_overview_multihit_summary_tests": {
        "markdown": "castle-overview-multihit-summary-tests-current.md",
        "purpose": "fixture regression coverage for the castle overview multi-hit parser",
    },
    "castle_overview_promotion_decision_tests": {
        "markdown": "castle-overview-promotion-decision-tests-current.md",
        "purpose": "fixture regression coverage for the castle overview promotion decision",
    },
    "castle_overview_probe_guard": {
        "markdown": "castle-overview-probe-guard-current.md",
        "purpose": "focused castle overview probe keeps proven no-popup hitbox callsites",
    },
    "castle_overview_probe_guard_tests": {
        "markdown": "castle-overview-probe-guard-tests-current.md",
        "purpose": "fixture regression coverage for the focused castle overview probe guard",
    },
    "stable_stage_guard_tests": {
        "markdown": "stable-stage-guard-tests-current.md",
        "purpose": "fixture regression coverage for stable-stage validation-scope boundaries",
    },
    "docs_consistency_guard": {
        "markdown": "docs-consistency-current.md",
        "purpose": "current docs and handoff files match generated stable-stage/no-popup/manual-proof facts",
    },
    "docs_consistency_guard_tests": {
        "markdown": "docs-consistency-tests-current.md",
        "purpose": "fixture regression coverage for stale docs and generated-count drift",
    },
}

REQUIRED_REPORTS = {**REQUIRED_GUARDS, **REQUIRED_SUPPORTING_REPORTS}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def status_text(passed: bool) -> str:
    return "PASS" if passed else "FAIL"


def check_record(passed: bool, summary: dict[str, Any], failures: list[str] | None = None) -> dict[str, Any]:
    return {
        "passed": passed,
        "summary": summary,
        "failures": failures or [],
    }


def evidence_contains(evidence_index: Path, needle: str) -> bool:
    if not evidence_index.exists():
        return False
    text = evidence_index.read_text(encoding="utf-8-sig", errors="replace")
    return needle.replace("\\", "/") in text.replace("\\", "/")


def build_guard_from_checks(
    checks: dict[str, Any],
    evidence_index: Path,
) -> dict[str, Any]:
    failures: list[str] = []
    guard_checks: dict[str, Any] = {}
    required_names = list(REQUIRED_REPORTS)

    for name, requirement in REQUIRED_REPORTS.items():
        check = checks.get(name)
        check_failures: list[str] = []
        if check is None:
            check_failures.append(f"missing refresh check: {name}")
        elif not check.get("passed"):
            check_failures.append(f"refresh check is not passing: {name}")

        markdown = requirement["markdown"]
        linked = evidence_contains(evidence_index, markdown)
        if not linked:
            check_failures.append(f"evidence index does not link {markdown}")

        path_exists = True
        if check and check.get("markdown"):
            path_exists = Path(check["markdown"]).exists()
            if not path_exists:
                check_failures.append(f"guard markdown output is missing: {check['markdown']}")

        guard_checks[name] = check_record(
            not check_failures,
            {
                "purpose": requirement["purpose"],
                "expected_markdown": markdown,
                "refresh_markdown": check.get("markdown") if check else None,
                "refresh_json": check.get("json") if check else None,
                "linked_from_evidence_index": linked,
                "markdown_exists": path_exists,
            },
            check_failures,
        )
        failures.extend(f"{name}: {failure}" for failure in check_failures)

    return {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "passed": not failures,
        "runtime_policy": RUNTIME_POLICY,
        "guard_policy": "current refresh must include all no-popup boundary reports and the evidence index must link each report",
        "evidence_index": str(evidence_index),
        "required_guard_count": len(REQUIRED_GUARDS),
        "required_supporting_report_count": len(REQUIRED_SUPPORTING_REPORTS),
        "required_report_count": len(required_names),
        "required_guards": list(REQUIRED_GUARDS),
        "required_supporting_reports": list(REQUIRED_SUPPORTING_REPORTS),
        "required_reports": required_names,
        "checks": guard_checks,
        "failures": failures,
    }


def build_guard(args: argparse.Namespace) -> dict[str, Any]:
    if not args.refresh_json.exists():
        return {
            "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
            "passed": False,
            "runtime_policy": RUNTIME_POLICY,
            "guard_policy": "current refresh must include all no-popup boundary reports and the evidence index must link each report",
            "evidence_index": str(args.evidence_index),
            "required_guard_count": len(REQUIRED_GUARDS),
            "required_supporting_report_count": len(REQUIRED_SUPPORTING_REPORTS),
            "required_report_count": len(REQUIRED_REPORTS),
            "required_guards": list(REQUIRED_GUARDS),
            "required_supporting_reports": list(REQUIRED_SUPPORTING_REPORTS),
            "required_reports": list(REQUIRED_REPORTS),
            "checks": {},
            "failures": [f"missing refresh JSON: {args.refresh_json}"],
        }
    refresh = load_json(args.refresh_json)
    return build_guard_from_checks(refresh.get("checks", {}), args.evidence_index)


def print_guard(guard: dict[str, Any]) -> None:
    print(f"overall: {status_text(guard['passed'])}")
    print(f"runtime-policy: {guard['runtime_policy']}")
    print(f"guard-policy: {guard['guard_policy']}")
    for name, check in guard["checks"].items():
        print(f"{name}: {status_text(bool(check.get('passed')))}")
    if guard["failures"]:
        print("failures:")
        for failure in guard["failures"]:
            print(f"  - {failure}")


def write_markdown(path: Path, guard: dict[str, Any]) -> None:
    lines = [
        "# No-Popup Boundary Guard",
        "",
        f"- Overall: {status_text(guard['passed'])}",
        f"- Generated: `{guard['generated_at']}`",
        f"- Runtime policy: {guard['runtime_policy']}",
        f"- Guard policy: {guard['guard_policy']}",
        f"- Evidence index: `{guard['evidence_index']}`",
        f"- Core boundary guards: `{guard.get('required_guard_count')}`",
        f"- Supporting reports: `{guard.get('required_supporting_report_count')}`",
        f"- Required reports total: `{guard.get('required_report_count')}`",
        "",
        "## Required Reports",
        "",
    ]
    for name, check in guard["checks"].items():
        summary = check.get("summary") or {}
        lines.append(
            "- `{name}`: `{status}` report=`{report}` linked=`{linked}`".format(
                name=name,
                status=status_text(bool(check.get("passed"))),
                report=summary.get("refresh_markdown") or summary.get("expected_markdown"),
                linked=summary.get("linked_from_evidence_index"),
            )
        )
        for failure in check.get("failures", []):
            lines.append(f"  - {failure}")
    if guard["failures"]:
        lines.extend(["", "## Failures", ""])
        lines.extend(f"- {failure}" for failure in guard["failures"])
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh-json", type=Path, default=DEFAULT_REFRESH_JSON)
    parser.add_argument("--evidence-index", type=Path, default=DEFAULT_EVIDENCE_INDEX)
    parser.add_argument("--write-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--write-markdown", type=Path, default=DEFAULT_MD)
    parser.add_argument("--require-pass", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    guard = build_guard(args)
    print_guard(guard)
    if args.write_json:
        args.write_json.parent.mkdir(parents=True, exist_ok=True)
        args.write_json.write_text(json.dumps(guard, indent=2) + "\n", encoding="utf-8")
    if args.write_markdown:
        write_markdown(args.write_markdown, guard)
    if args.require_pass and not guard["passed"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
