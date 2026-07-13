#!/usr/bin/env python3
"""Verify validation-only Clash95 patch groups stay out of the stable stage.

This is a repo-only guard. It imports the patch table and reads existing
promotion/evidence artifacts; it does not launch Clash95, CDB, wrappers, or
any visible GUI process.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import patch_clash95_hd  # noqa: E402


DEFAULT_JSON = Path("captures/current/stable-stage-guard-current.json")
DEFAULT_MD = Path("captures/current/stable-stage-guard-current.md")
DEFAULT_RIGHT_BOTTOM_DECISION = Path(
    "captures/current/right-bottom-compose-promotion-decision-current.json"
)
DEFAULT_RIGHT_BOTTOM_MATRIX = Path("captures/current/right-bottom-compose-evidence-current.json")
DEFAULT_CASTLE_DECISION = Path("captures/current/castle-overview-promotion-decision-current.json")
DEFAULT_CASTLE_MATRIX = Path("captures/current/castle-overview-evidence-current.json")

RIGHT_BOTTOM_VALIDATION_STAGE = (
    "gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-"
    "presentbounds-minimapright-dynvswitch-rightbottomcompose"
)
TOOLTIP_BOTTOM_CENTER_STAGE = patch_clash95_hd.DEFAULT_STAGE + "-tooltipbottomcenter"
UNIT_COMMAND_PANEL_STAGE = patch_clash95_hd.DEFAULT_STAGE + "-unitcommandpanel-rightbottom"
HD_LAYOUT_STAGE = patch_clash95_hd.DEFAULT_STAGE + "-hdlayout"
FRAME_RESTORE_STAGE = patch_clash95_hd.DEFAULT_STAGE + "-framerestore"
CASTLECENTER_STAGE = (
    "gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-"
    "presentbounds-minimapright-dynvswitch-castlecenter"
)
CASTLECENTER_HITBOX_STAGE = (
    "gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-"
    "presentbounds-minimapright-dynvswitch-castlecenter-hitbox"
)
CASTLECENTER_ALL_STAGE = (
    "gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-"
    "presentbounds-minimapright-dynvswitch-castlecenter-all"
)
BATTLECENTER_STAGE = CASTLECENTER_ALL_STAGE + "-battlecenter"
BATTLECENTER_INPUTPROBE_STAGE = BATTLECENTER_STAGE + "-inputprobe"

VALIDATION_ONLY_GROUPS = (
    "right-bottom-compose-proof",
    "terrain-tooltip-bottom-center",
    "selected-unit-command-panel-right-bottom",
    "castle-ui-center-present",
    "castle-ui-center-present-wrapper",
    "castle-ui-centered-input",
    "castle-overview-center-present-wrapper",
    "castle-overview-centered-input",
    "battle-ui-center-present-wrapper",
    "battle-grid-centered-input",
    "battle-ui-centered-input",
    "frame-restore-bands",
)

MENU_SURFACE_GROUP = "menu-surface"
MAP_SURFACE_UPGRADE_GROUP = "map-surface-upgrade-scrollclamp"

VALIDATION_STAGE_EXPECTATIONS = {
    RIGHT_BOTTOM_VALIDATION_STAGE: ("right-bottom-compose-proof",),
    TOOLTIP_BOTTOM_CENTER_STAGE: ("terrain-tooltip-bottom-center",),
    UNIT_COMMAND_PANEL_STAGE: ("selected-unit-command-panel-right-bottom",),
    HD_LAYOUT_STAGE: (
        "terrain-tooltip-bottom-center",
        "selected-unit-command-panel-right-bottom",
    ),
    FRAME_RESTORE_STAGE: ("frame-restore-bands",),
    CASTLECENTER_STAGE: ("castle-ui-center-present",),
    CASTLECENTER_HITBOX_STAGE: (
        "castle-ui-center-present",
        "castle-ui-centered-input",
    ),
    CASTLECENTER_ALL_STAGE: (
        "castle-ui-center-present-wrapper",
        "castle-ui-centered-input",
        "castle-overview-center-present-wrapper",
        "castle-overview-centered-input",
    ),
    BATTLECENTER_STAGE: (
        "castle-ui-center-present-wrapper",
        "castle-ui-centered-input",
        "castle-overview-center-present-wrapper",
        "castle-overview-centered-input",
        "battle-ui-center-present-wrapper",
    ),
    BATTLECENTER_INPUTPROBE_STAGE: (
        "castle-ui-center-present-wrapper",
        "castle-ui-centered-input",
        "castle-overview-center-present-wrapper",
        "castle-overview-centered-input",
        "battle-ui-center-present-wrapper",
        "battle-grid-centered-input",
        "battle-ui-centered-input",
    ),
}

CASTLE_DECISION_REQUIRED_PROOF = (
    "focused_displayed_wrapper_ok",
    "visible_multihit_completion_ok",
    "dormant_multihit_completion_ok",
)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def status_text(passed: bool) -> str:
    return "PASS" if passed else "FAIL"


def check_record(passed: bool, summary: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "passed": passed,
        "summary": summary or {},
        "failures": [],
    }


def failed_record(failure: str, summary: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "passed": False,
        "summary": summary or {},
        "failures": [failure],
    }


def stage_groups(stage: str) -> set[str] | None:
    groups = patch_clash95_hd.STAGE_GROUPS.get(stage)
    if groups is None:
        return None
    return set(groups)


def targets_completed(check: dict[str, Any]) -> bool:
    targets = check.get("targets") or []
    return bool(targets) and all(target.get("completion_ok") is True for target in targets)


def castle_matrix_proof(matrix: dict[str, Any]) -> dict[str, Any]:
    checks = matrix.get("checks") or {}
    focused = checks.get("focused_hitbox") or {}
    visible = checks.get("visible_multihit") or {}
    dormant = checks.get("dormant_multihit") or {}
    return {
        "focused_displayed_wrapper_ok": focused.get("displayed_wrapper_ok") is True,
        "visible_multihit_completion_ok": targets_completed(visible),
        "dormant_multihit_completion_ok": targets_completed(dormant),
    }


def build_stage_scope_checks(current_stable_stage: str) -> dict[str, Any]:
    checks: dict[str, Any] = {}
    stable_groups = stage_groups(current_stable_stage)

    patcher_default = getattr(patch_clash95_hd, "DEFAULT_STAGE", None)
    checks["patcher_default_stage"] = check_record(
        patcher_default == current_stable_stage,
        {
            "patcher_default_stage": patcher_default,
            "expected_stable_stage": current_stable_stage,
        },
    )
    if patcher_default != current_stable_stage:
        checks["patcher_default_stage"]["failures"].append(
            f"patcher default stage is {patcher_default}, expected {current_stable_stage}"
        )

    if stable_groups is None:
        checks["stable_stage_defined"] = failed_record(
            f"stable stage is not defined in patch_clash95_hd.STAGE_GROUPS: {current_stable_stage}",
            {"stable_stage": current_stable_stage},
        )
        checks["stable_stage_validation_groups_absent"] = failed_record(
            "stable stage groups could not be inspected",
            {"stable_stage": current_stable_stage},
        )
        return checks

    stable_validation_groups = sorted(set(VALIDATION_ONLY_GROUPS) & stable_groups)
    checks["stable_stage_defined"] = check_record(
        True,
        {
            "stable_stage": current_stable_stage,
            "group_count": len(stable_groups),
        },
    )
    checks["stable_stage_validation_groups_absent"] = check_record(
        not stable_validation_groups,
        {
            "stable_stage": current_stable_stage,
            "validation_only_groups_in_stable": stable_validation_groups,
        },
    )
    if stable_validation_groups:
        checks["stable_stage_validation_groups_absent"]["failures"].append(
            f"validation-only groups found in stable stage: {stable_validation_groups}"
        )

    for stage, extra_groups in VALIDATION_STAGE_EXPECTATIONS.items():
        groups = stage_groups(stage)
        check_name = f"validation_stage_scope_{stage.split('-')[-1]}"
        if groups is None:
            checks[check_name] = failed_record(
                f"validation stage is not defined: {stage}",
                {"validation_stage": stage},
            )
            continue
        expected_groups = stable_groups | set(extra_groups)
        unexpected_groups = sorted(groups - expected_groups)
        missing_groups = sorted(expected_groups - groups)
        passed = not unexpected_groups and not missing_groups
        checks[check_name] = check_record(
            passed,
            {
                "validation_stage": stage,
                "expected_extra_groups": list(extra_groups),
                "unexpected_groups": unexpected_groups,
                "missing_groups": missing_groups,
            },
        )
        if unexpected_groups:
            checks[check_name]["failures"].append(
                f"{stage} has unexpected groups beyond stable plus validation extras: {unexpected_groups}"
            )
        if missing_groups:
            checks[check_name]["failures"].append(
                f"{stage} is missing expected stable/validation groups: {missing_groups}"
            )

    mapsurface_stages = sorted(
        stage for stage in patch_clash95_hd.STAGE_GROUPS if "mapsurface" in stage
    )
    menusurface_diagnostic_stages = sorted(
        stage for stage in patch_clash95_hd.STAGE_GROUPS if "menusurface" in stage
    )
    mapsurface_with_menu_surface = sorted(
        stage
        for stage in mapsurface_stages
        if MENU_SURFACE_GROUP in (stage_groups(stage) or set())
    )
    mapsurface_missing_upgrade = sorted(
        stage
        for stage in mapsurface_stages
        if MAP_SURFACE_UPGRADE_GROUP not in (stage_groups(stage) or set())
    )
    diagnostic_missing_menu_surface = sorted(
        stage
        for stage in menusurface_diagnostic_stages
        if MENU_SURFACE_GROUP not in (stage_groups(stage) or set())
    )
    menu_scope_passed = (
        bool(mapsurface_stages)
        and not mapsurface_with_menu_surface
        and not mapsurface_missing_upgrade
        and not diagnostic_missing_menu_surface
    )
    checks["menu_surface_replaced_by_map_surface_upgrade"] = check_record(
        menu_scope_passed,
        {
            "mapsurface_stages": mapsurface_stages,
            "menusurface_diagnostic_stages": menusurface_diagnostic_stages,
            "forbidden_group": MENU_SURFACE_GROUP,
            "required_mapsurface_group": MAP_SURFACE_UPGRADE_GROUP,
            "mapsurface_with_menu_surface": mapsurface_with_menu_surface,
            "mapsurface_missing_upgrade": mapsurface_missing_upgrade,
            "diagnostic_missing_menu_surface": diagnostic_missing_menu_surface,
        },
    )
    if not mapsurface_stages:
        checks["menu_surface_replaced_by_map_surface_upgrade"]["failures"].append(
            "no mapsurface stages were found to guard"
        )
    if mapsurface_with_menu_surface:
        checks["menu_surface_replaced_by_map_surface_upgrade"]["failures"].append(
            f"mapsurface stages still include global menu-surface group: {mapsurface_with_menu_surface}"
        )
    if mapsurface_missing_upgrade:
        checks["menu_surface_replaced_by_map_surface_upgrade"]["failures"].append(
            f"mapsurface stages are missing gameplay-only map surface upgrade: {mapsurface_missing_upgrade}"
        )
    if diagnostic_missing_menu_surface:
        checks["menu_surface_replaced_by_map_surface_upgrade"]["failures"].append(
            f"menusurface diagnostic stages no longer carry menu-surface group: {diagnostic_missing_menu_surface}"
        )

    return checks


def promotion_decision_check(
    label: str,
    path: Path,
    current_stable_stage: str,
    required_proof: tuple[str, ...] = (),
    allow_nonpassing_defer: bool = False,
) -> dict[str, Any]:
    if not path.exists():
        return failed_record(f"missing {label} promotion decision: {path}", {"path": str(path)})
    decision = load_json(path)
    failures: list[str] = []
    decision_passed = decision.get("passed") is True
    if not decision_passed and not allow_nonpassing_defer:
        failures.append(f"{label} promotion decision is not passing")
    if decision.get("decision") != "defer_stable_promotion":
        failures.append(
            f"{label} decision is {decision.get('decision')}, expected defer_stable_promotion"
        )
    if decision.get("stable_stage_should_change") is not False:
        failures.append(f"{label} decision would change the stable stage")
    if decision.get("current_stable_stage") != current_stable_stage:
        failures.append(
            f"{label} current stable stage is {decision.get('current_stable_stage')}, "
            f"expected {current_stable_stage}"
        )
    proof = decision.get("proof") or {}
    for key in required_proof:
        if proof.get(key) is not True:
            failures.append(f"{label} promotion decision missing required proof: {key}")
    return {
        "passed": not failures,
        "summary": {
            "path": str(path),
            "decision": decision.get("decision"),
            "stable_stage_should_change": decision.get("stable_stage_should_change"),
            "current_stable_stage": decision.get("current_stable_stage"),
            "validation_stage": decision.get("validation_stage"),
            "candidate_sha256": decision.get("candidate_sha256"),
            "evidence_passed": decision_passed,
            "proof": {key: proof.get(key) for key in required_proof},
        },
        "failures": failures,
    }


def evidence_matrix_check(
    label: str,
    path: Path,
    current_stable_stage: str | None,
    require_castle_proof: bool = False,
    allow_nonpassing_validation: bool = False,
) -> dict[str, Any]:
    if not path.exists():
        return failed_record(f"missing {label} evidence matrix: {path}", {"path": str(path)})
    matrix = load_json(path)
    failures: list[str] = []
    matrix_passed = matrix.get("passed") is True
    if not matrix_passed and not allow_nonpassing_validation:
        failures.append(f"{label} evidence matrix is not passing")
    if matrix.get("promotion_status") != "validation_stage_only":
        failures.append(
            f"{label} promotion status is {matrix.get('promotion_status')}, "
            "expected validation_stage_only"
        )
    if matrix.get("stable_stage_should_change") is not None:
        if matrix.get("stable_stage_should_change") is not False:
            failures.append(f"{label} matrix would change the stable stage")
    if current_stable_stage and matrix.get("current_stable_stage") not in (None, current_stable_stage):
        failures.append(
            f"{label} current stable stage is {matrix.get('current_stable_stage')}, "
            f"expected {current_stable_stage}"
        )
    proof: dict[str, Any] = {}
    if require_castle_proof:
        proof = castle_matrix_proof(matrix)
        for key, value in proof.items():
            if value is not True:
                failures.append(f"{label} evidence matrix missing required proof: {key}")
    return {
        "passed": not failures,
        "summary": {
            "path": str(path),
            "promotion_status": matrix.get("promotion_status"),
            "stable_stage_should_change": matrix.get("stable_stage_should_change"),
            "current_stable_stage": matrix.get("current_stable_stage"),
            "validation_stage": matrix.get("validation_stage") or matrix.get("stage"),
            "candidate_sha256": matrix.get("candidate_sha256")
            or (matrix.get("checks", {}).get("patch_stage", {}) or {}).get("sha256"),
            "evidence_passed": matrix_passed,
            "proof": proof,
        },
        "failures": failures,
    }


def build_guard(args: argparse.Namespace) -> dict[str, Any]:
    checks = build_stage_scope_checks(args.current_stable_stage)
    checks["right_bottom_promotion_decision"] = promotion_decision_check(
        "right-bottom",
        args.right_bottom_decision,
        args.current_stable_stage,
        allow_nonpassing_defer=True,
    )
    checks["right_bottom_evidence_matrix"] = evidence_matrix_check(
        "right-bottom",
        args.right_bottom_matrix,
        args.current_stable_stage,
        allow_nonpassing_validation=True,
    )
    checks["castle_overview_promotion_decision"] = promotion_decision_check(
        "castle overview",
        args.castle_decision,
        args.current_stable_stage,
        CASTLE_DECISION_REQUIRED_PROOF,
    )
    checks["castle_overview_evidence_matrix"] = evidence_matrix_check(
        "castle overview",
        args.castle_matrix,
        None,
        require_castle_proof=True,
    )

    failures: list[str] = []
    for name, check in checks.items():
        if not check.get("passed"):
            failures.extend(f"{name}: {failure}" for failure in check.get("failures", []))

    stable_groups = stage_groups(args.current_stable_stage) or set()
    validation_groups_in_stable = sorted(set(VALIDATION_ONLY_GROUPS) & stable_groups)
    menu_scope = checks.get("menu_surface_replaced_by_map_surface_upgrade", {}).get("summary", {})
    return {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "passed": not failures,
        "runtime_policy": "repo-only; does not launch Clash95, CDB, wrappers, or visible windows",
        "current_stable_stage": args.current_stable_stage,
        "patcher_default_stage": getattr(patch_clash95_hd, "DEFAULT_STAGE", None),
        "validation_only_groups": list(VALIDATION_ONLY_GROUPS),
        "validation_only_groups_in_stable": validation_groups_in_stable,
        "validation_stage_expectations": {
            stage: list(groups) for stage, groups in VALIDATION_STAGE_EXPECTATIONS.items()
        },
        "mapsurface_stages_checked": menu_scope.get("mapsurface_stages", []),
        "mapsurface_with_menu_surface": menu_scope.get("mapsurface_with_menu_surface", []),
        "mapsurface_missing_upgrade": menu_scope.get("mapsurface_missing_upgrade", []),
        "checks": checks,
        "failures": failures,
    }


def print_guard(guard: dict[str, Any]) -> None:
    print(f"overall: {status_text(guard['passed'])}")
    print(f"runtime-policy: {guard['runtime_policy']}")
    print(f"current-stable-stage: {guard['current_stable_stage']}")
    print(f"patcher-default-stage: {guard['patcher_default_stage']}")
    print(f"validation-groups-in-stable: {guard['validation_only_groups_in_stable']}")
    print(f"mapsurface-stages-checked: {guard['mapsurface_stages_checked']}")
    print(f"mapsurface-with-menu-surface: {guard['mapsurface_with_menu_surface']}")
    print(f"mapsurface-missing-upgrade: {guard['mapsurface_missing_upgrade']}")
    for name, check in guard["checks"].items():
        print(f"{name}: {status_text(bool(check.get('passed')))}")
    if guard["failures"]:
        print("failures:")
        for failure in guard["failures"]:
            print(f"  - {failure}")


def write_markdown(path: Path, guard: dict[str, Any]) -> None:
    lines = [
        "# Stable Stage Guard",
        "",
        f"- Overall: {status_text(guard['passed'])}",
        f"- Generated: `{guard['generated_at']}`",
        f"- Runtime policy: {guard['runtime_policy']}",
        f"- Current stable stage: `{guard['current_stable_stage']}`",
        f"- Patcher default stage: `{guard['patcher_default_stage']}`",
        f"- Validation-only groups in stable stage: `{guard['validation_only_groups_in_stable']}`",
        f"- Mapsurface stages checked: `{guard['mapsurface_stages_checked']}`",
        f"- Mapsurface stages with menu-surface: `{guard['mapsurface_with_menu_surface']}`",
        f"- Mapsurface stages missing upgrade: `{guard['mapsurface_missing_upgrade']}`",
        "",
        "## Checks",
        "",
    ]
    for name, check in guard["checks"].items():
        lines.append(f"- `{name}`: `{status_text(bool(check.get('passed')))}`")
        proof = (check.get("summary") or {}).get("proof") or {}
        for key, value in proof.items():
            lines.append(f"  - `{key}`: `{value}`")
        for failure in check.get("failures", []):
            lines.append(f"  - {failure}")
    lines.extend(["", "## Validation-Only Groups", ""])
    lines.extend(f"- `{group}`" for group in guard["validation_only_groups"])
    lines.extend(["", "## Validation Stages", ""])
    for stage, groups in guard["validation_stage_expectations"].items():
        lines.append(f"- `{stage}`: `{groups}`")
    if guard["failures"]:
        lines.extend(["", "## Failures", ""])
        lines.extend(f"- {failure}" for failure in guard["failures"])
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--current-stable-stage", default=patch_clash95_hd.DEFAULT_STAGE)
    parser.add_argument("--right-bottom-decision", type=Path, default=DEFAULT_RIGHT_BOTTOM_DECISION)
    parser.add_argument("--right-bottom-matrix", type=Path, default=DEFAULT_RIGHT_BOTTOM_MATRIX)
    parser.add_argument("--castle-decision", type=Path, default=DEFAULT_CASTLE_DECISION)
    parser.add_argument("--castle-matrix", type=Path, default=DEFAULT_CASTLE_MATRIX)
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
