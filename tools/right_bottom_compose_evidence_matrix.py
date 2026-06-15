#!/usr/bin/env python3
"""Run the repo-only right-bottom composition evidence matrix.

This is the compact no-runtime gate for the current rightbottomcompose
validation stage. It checks existing refresh artifacts only; it does not launch
Clash95, CDB, wrappers, or any visible GUI process.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import right_bottom_compose_promotion_decision


DEFAULT_REFRESH_JSON = Path("captures/current/current-evidence-refresh-current.json")
DEFAULT_MATRIX_JSON = Path("captures/current/right-bottom-compose-evidence-current.json")
DEFAULT_MATRIX_MD = Path("captures/current/right-bottom-compose-evidence-current.md")
DEFAULT_STABLE_STAGE = right_bottom_compose_promotion_decision.DEFAULT_STABLE_STAGE
DEFAULT_VALIDATION_STAGE = right_bottom_compose_promotion_decision.DEFAULT_VALIDATION_STAGE

REQUIRED_CHECKS = (
    "right_bottom_compose_patch",
    "right_bottom_compose_fullstart_route",
    "right_bottom_compose_normal_gate",
    "right_bottom_compose_ui_probe",
    "right_bottom_grid_hit",
    "right_bottom_natural_route_guard",
    "right_bottom_route_timing_guard",
    "right_bottom_compose_promotion_decision",
)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _check_failures(name: str, check: dict[str, Any] | None) -> list[str]:
    if check is None:
        return [f"{name} is missing"]
    if check.get("passed"):
        return []
    failures = check.get("failures") or ["failed without a detailed reason"]
    return [f"{name}: {failure}" for failure in failures]


def _summary(checks: dict[str, Any], name: str) -> dict[str, Any]:
    return (checks.get(name) or {}).get("summary") or {}


def build_matrix_from_checks(args: argparse.Namespace, checks: dict[str, Any]) -> dict[str, Any]:
    failures: list[str] = []
    for name in REQUIRED_CHECKS:
        failures.extend(_check_failures(name, checks.get(name)))

    patch = _summary(checks, "right_bottom_compose_patch")
    fullstart = _summary(checks, "right_bottom_compose_fullstart_route")
    normal = _summary(checks, "right_bottom_compose_normal_gate")
    ui = _summary(checks, "right_bottom_compose_ui_probe")
    grid = _summary(checks, "right_bottom_grid_hit")
    natural_route = _summary(checks, "right_bottom_natural_route_guard")
    timing = _summary(checks, "right_bottom_route_timing_guard")
    decision = _summary(checks, "right_bottom_compose_promotion_decision")

    candidate_values = {
        value
        for value in (
            patch.get("candidate_sha256"),
            fullstart.get("candidate_sha256"),
            normal.get("candidate_sha256"),
            ui.get("candidate_sha256"),
            grid.get("candidate_sha256"),
            timing.get("candidate_sha256"),
            decision.get("candidate_sha256"),
        )
        if value
    }
    if len(candidate_values) > 1:
        failures.append(f"right-bottom candidate SHA values disagree: {sorted(candidate_values)}")

    expected_patch_stage = args.validation_stage
    for label, summary in (
        ("patch", patch),
        ("fullstart_route", fullstart),
        ("normal_gate", normal),
        ("natural_ui_probe", ui),
        ("controlled_grid_hit", grid),
    ):
        if summary.get("stage") != expected_patch_stage:
            failures.append(f"{label} stage is {summary.get('stage')}, expected {expected_patch_stage}")

    patch_group = patch.get("right_bottom_patch_group") or {}
    if patch_group.get("patched") != 4 or patch_group.get("total") != 4:
        failures.append(f"right-bottom patch group was {patch_group}, expected 4/4")
    if patch.get("current_hd_map_gate") is not True:
        failures.append("right-bottom patch did not preserve the current HD map byte gate")

    if fullstart.get("hidden_desktop") is not True:
        failures.append("full-start route did not run on hidden desktop")
    if fullstart.get("no_skip_start_anims") is not True:
        failures.append("full-start route did not use the full startup/resource path")
    if fullstart.get("fast_forward_start_anims"):
        failures.append("full-start route unexpectedly fast-forwarded startup animations")
    if fullstart.get("map_validation_skipped") is not True:
        failures.append("full-start route was expected to skip map validation for controlled owner/action proof")
    if fullstart.get("ready") is not True:
        failures.append("full-start route was not ready")
    if int(fullstart.get("av_count") or 0):
        failures.append(f"full-start route has AV rows: {fullstart.get('av_count')}")

    if normal.get("hidden_desktop") is not True:
        failures.append("normal gate did not run on hidden desktop")
    if normal.get("map_validation_skipped"):
        failures.append("normal map gate skipped map validation")
    if normal.get("surface") != [800, 600]:
        failures.append(f"normal map gate surface was {normal.get('surface')}")
    if normal.get("visibility_explained_gate") is not True:
        failures.append("normal map gate visibility explanation did not pass")
    if int(normal.get("visibility_unexplained_blank_cells") or 0):
        failures.append(
            f"normal map gate has unexplained blank cells: {normal.get('visibility_unexplained_blank_cells')}"
        )

    if ui.get("hidden_desktop") is not True:
        failures.append("natural UI probe did not run on hidden desktop")
    if int(ui.get("rbui_desc_switch") or 0) <= 0:
        failures.append("natural UI probe did not reach descriptor switch rows")
    if int(ui.get("rbui_viewport_switch") or 0) <= 0:
        failures.append("natural UI probe did not reach viewport switch rows")
    natural_owner_rows = int(ui.get("rbui_panel_draw") or 0) + int(ui.get("rbui_action_box") or 0)
    if natural_owner_rows <= 0:
        failures.append("natural UI probe did not enter owner/action draw rows")
    if int(ui.get("av_count") or 0):
        failures.append(f"natural UI probe has AV rows: {ui.get('av_count')}")

    if grid.get("hidden_desktop") is not True:
        failures.append("controlled grid-hit proof did not run on hidden desktop")
    if grid.get("map_validation_skipped") is not True:
        failures.append("controlled grid-hit proof did not skip map validation")
    if grid.get("fast_forward_start_anims") is not True:
        failures.append("controlled grid-hit proof did not fast-forward startup animations")
    if grid.get("surface") != [800, 600]:
        failures.append(f"controlled grid-hit surface was {grid.get('surface')}")
    if grid.get("grid_hit_ok") is not True:
        failures.append("controlled grid-hit proof did not prove the target grid cell")
    if grid.get("last_grid_entry") != [450, 73]:
        failures.append(f"controlled grid-hit entry was {grid.get('last_grid_entry')}, expected [450, 73]")
    if grid.get("last_grid_result") != 0:
        failures.append(f"controlled grid-hit result was {grid.get('last_grid_result')}, expected 0")
    if int(grid.get("forced_gate_count") or 0) <= 0:
        failures.append("controlled grid-hit proof did not reach/force the hidden flip gate")
    if int(grid.get("failure_exit_count") or 0) != 0:
        failures.append("controlled grid-hit proof used a failure exit")
    if int(grid.get("draw_row_count") or 0) <= 0:
        failures.append("controlled grid-hit proof did not observe draw rows")
    if int(grid.get("av_count") or 0):
        failures.append(f"controlled grid-hit proof has AV rows: {grid.get('av_count')}")

    natural_owner_flag = natural_route.get("owner_flag_test") or {}
    natural_action_descriptor = natural_route.get("action_descriptor") or {}
    natural_descriptor_result = natural_route.get("descriptor_result") or {}
    if natural_route.get("hidden_desktop") is not True:
        failures.append("natural route guard did not run on hidden desktop")
    if natural_route.get("state_gated_by_owner_flag") is not True:
        failures.append("natural route guard did not classify the owner-flag save-state gate")
    if natural_route.get("owner_entry_flag") != "0x00":
        failures.append(f"natural route owner entry flag was {natural_route.get('owner_entry_flag')}, expected 0x00")
    if natural_owner_flag.get("owner_flag") != "0x00":
        failures.append(f"natural route owner flag was {natural_owner_flag.get('owner_flag')}, expected 0x00")
    if any(int(natural_owner_flag.get(bit) or 0) for bit in ("bit2", "bit1", "bit8")):
        failures.append(f"natural route owner flag bits were {natural_owner_flag}, expected all zero")
    if str(natural_action_descriptor.get("callback") or "").lower() != "004338e0":
        failures.append("natural route action descriptor callback was not 004338E0")
    if int(natural_action_descriptor.get("x") or -1) < 800:
        failures.append("natural route action descriptor was not off-screen")
    if natural_descriptor_result.get("result") != 0:
        failures.append(f"natural route descriptor result was {natural_descriptor_result.get('result')}, expected 0")
    if int(natural_route.get("action_route_count") or 0) != 0:
        failures.append("natural route unexpectedly entered the owner/action renderer")
    if int(natural_route.get("av_count") or 0):
        failures.append(f"natural route guard has AV rows: {natural_route.get('av_count')}")

    if int(timing.get("patch_route_ordered_markers") or 0) < 20:
        failures.append("route timing guard did not preserve patch route marker ordering")
    if int(timing.get("fullstart_route_ordered_markers") or 0) < 20:
        failures.append("route timing guard did not preserve full-start route marker ordering")
    if int(timing.get("grid_route_ordered_markers") or 0) < 20:
        failures.append("route timing guard did not preserve grid route marker ordering")
    if timing.get("grid_hit_ok") is not True:
        failures.append("route timing guard did not preserve grid-hit proof")
    if timing.get("last_grid_entry") != [450, 73]:
        failures.append(f"route timing guard grid entry was {timing.get('last_grid_entry')}, expected [450, 73]")
    if timing.get("last_grid_result") != 0:
        failures.append(f"route timing guard grid result was {timing.get('last_grid_result')}, expected 0")
    if int(timing.get("failure_exit_count") or 0) != 0:
        failures.append("route timing guard observed failure exits")
    if int(timing.get("av_count") or 0):
        failures.append(f"route timing guard observed AV rows: {timing.get('av_count')}")

    if decision.get("decision") != "defer_stable_promotion":
        failures.append(f"promotion decision is {decision.get('decision')}, expected defer_stable_promotion")
    if decision.get("stable_stage_should_change") is not False:
        failures.append("promotion decision would change the stable HD map stage")
    if decision.get("current_stable_stage") != args.current_stable_stage:
        failures.append(
            f"stable stage is {decision.get('current_stable_stage')}, expected {args.current_stable_stage}"
        )

    candidate_sha = next(iter(candidate_values), None)
    return {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "passed": not failures,
        "runtime_policy": "repo-only; does not launch Clash95, CDB, wrappers, or visible windows",
        "promotion_status": "validation_stage_only",
        "stable_stage_should_change": False,
        "current_stable_stage": args.current_stable_stage,
        "validation_stage": args.validation_stage,
        "candidate_sha256": candidate_sha,
        "checks": {
            name: {
                "passed": bool((checks.get(name) or {}).get("passed")),
                "summary": (checks.get(name) or {}).get("summary", {}),
            }
            for name in REQUIRED_CHECKS
        },
        "key_evidence": {
            "patch_group": patch_group,
            "fullstart_route_ready": fullstart.get("ready"),
            "fullstart_route_av_count": fullstart.get("av_count"),
            "bottom_right_ui_corner_nonblack": fullstart.get("bottom_right_ui_corner_nonblack"),
            "bottom_right_tile_r8c10_nonblack": fullstart.get("bottom_right_tile_r8c10_nonblack"),
            "bottom_right_tile_r8c11_nonblack": fullstart.get("bottom_right_tile_r8c11_nonblack"),
            "normal_surface": normal.get("surface"),
            "normal_unexplained_blank_cells": normal.get("visibility_unexplained_blank_cells"),
            "natural_desc_switch": ui.get("rbui_desc_switch"),
            "natural_panel_draw": ui.get("rbui_panel_draw"),
            "natural_action_box": ui.get("rbui_action_box"),
            "controlled_grid_hit_ok": grid.get("grid_hit_ok"),
            "controlled_grid_entry": grid.get("last_grid_entry"),
            "controlled_grid_result": grid.get("last_grid_result"),
            "controlled_grid_forced_gate_count": grid.get("forced_gate_count"),
            "controlled_grid_failure_exit_count": grid.get("failure_exit_count"),
            "natural_route_state_gated": natural_route.get("state_gated_by_owner_flag"),
            "natural_route_owner_entry_flag": natural_route.get("owner_entry_flag"),
            "natural_route_owner_flag_test": natural_owner_flag,
            "natural_route_action_descriptor": natural_action_descriptor,
            "natural_route_descriptor_result": natural_descriptor_result,
            "natural_route_action_route_count": natural_route.get("action_route_count"),
            "natural_route_av_count": natural_route.get("av_count"),
            "route_timing_patch_markers": timing.get("patch_route_ordered_markers"),
            "route_timing_fullstart_markers": timing.get("fullstart_route_ordered_markers"),
            "route_timing_grid_markers": timing.get("grid_route_ordered_markers"),
            "route_timing_failure_exit_count": timing.get("failure_exit_count"),
            "route_timing_av_count": timing.get("av_count"),
            "promotion_decision": decision.get("decision"),
        },
        "failures": failures,
    }


def build_matrix(args: argparse.Namespace) -> dict[str, Any]:
    refresh = load_json(args.refresh_json)
    return build_matrix_from_checks(args, refresh.get("checks", {}))


def print_matrix(matrix: dict[str, Any]) -> None:
    print(f"overall: {'PASS' if matrix['passed'] else 'FAIL'}")
    print(f"runtime-policy: {matrix['runtime_policy']}")
    print(f"promotion-status: {matrix['promotion_status']}")
    print(f"stable-stage-should-change: {matrix['stable_stage_should_change']}")
    print(f"validation-stage: {matrix['validation_stage']}")
    print(f"candidate-sha256: {matrix.get('candidate_sha256')}")
    print("required-checks:")
    for name, check in matrix["checks"].items():
        print(f"  - {name}: {'PASS' if check.get('passed') else 'FAIL'}")
    if matrix["failures"]:
        print("failures:")
        for failure in matrix["failures"]:
            print(f"  - {failure}")


def write_markdown(path: Path, matrix: dict[str, Any]) -> None:
    evidence = matrix["key_evidence"]
    lines = [
        "# Right-Bottom Compose Evidence Matrix",
        "",
        f"- Overall: {'PASS' if matrix['passed'] else 'FAIL'}",
        f"- Generated: `{matrix['generated_at']}`",
        f"- Runtime policy: {matrix['runtime_policy']}",
        f"- Promotion status: `{matrix['promotion_status']}`",
        f"- Stable stage should change: `{matrix['stable_stage_should_change']}`",
        f"- Current stable stage: `{matrix['current_stable_stage']}`",
        f"- Validation stage: `{matrix['validation_stage']}`",
        f"- Candidate SHA-256: `{matrix['candidate_sha256']}`",
        "",
        "## Required Checks",
        "",
    ]
    lines.extend(
        f"- `{name}`: `{'PASS' if check.get('passed') else 'FAIL'}`"
        for name, check in matrix["checks"].items()
    )
    lines.extend(
        [
            "",
            "## Key Evidence",
            "",
            f"- Patch group: `{evidence['patch_group']}`",
            f"- Full-start route ready: `{evidence['fullstart_route_ready']}`",
            f"- Full-start route AV count: `{evidence['fullstart_route_av_count']}`",
            f"- Bottom-right corner nonblack: `{evidence['bottom_right_ui_corner_nonblack']}`",
            f"- r8c10 nonblack: `{evidence['bottom_right_tile_r8c10_nonblack']}`",
            f"- r8c11 nonblack: `{evidence['bottom_right_tile_r8c11_nonblack']}`",
            f"- Normal map gate surface: `{evidence['normal_surface']}`",
            f"- Normal gate unexplained blanks: `{evidence['normal_unexplained_blank_cells']}`",
            f"- Natural UI descriptor switch rows: `{evidence['natural_desc_switch']}`",
            f"- Natural UI owner/action rows: `RBUI_PANEL_DRAW={evidence['natural_panel_draw']}`, `RBUI_ACTION_BOX={evidence['natural_action_box']}`",
            f"- Controlled grid hit: `ok={evidence['controlled_grid_hit_ok']}`, `entry={evidence['controlled_grid_entry']}`, `result={evidence['controlled_grid_result']}`",
            f"- Controlled grid forced gates/failure exits: `{evidence['controlled_grid_forced_gate_count']}` / `{evidence['controlled_grid_failure_exit_count']}`",
            f"- Natural route state-gated: `{evidence['natural_route_state_gated']}`",
            f"- Natural route owner entry flag: `{evidence['natural_route_owner_entry_flag']}`",
            f"- Natural route owner flag test: `{evidence['natural_route_owner_flag_test']}`",
            f"- Natural route action descriptor: `{evidence['natural_route_action_descriptor']}`",
            f"- Natural route descriptor result: `{evidence['natural_route_descriptor_result']}`",
            f"- Natural route owner/action rows / AV rows: `{evidence['natural_route_action_route_count']}` / `{evidence['natural_route_av_count']}`",
            f"- Route timing ordered markers: `patch={evidence['route_timing_patch_markers']}`, `fullstart={evidence['route_timing_fullstart_markers']}`, `grid={evidence['route_timing_grid_markers']}`",
            f"- Route timing failure exits / AV rows: `{evidence['route_timing_failure_exit_count']}` / `{evidence['route_timing_av_count']}`",
            f"- Promotion decision: `{evidence['promotion_decision']}`",
        ]
    )
    if matrix["failures"]:
        lines.extend(["", "## Failures", ""])
        lines.extend(f"- {failure}" for failure in matrix["failures"])
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh-json", type=Path, default=DEFAULT_REFRESH_JSON)
    parser.add_argument("--current-stable-stage", default=DEFAULT_STABLE_STAGE)
    parser.add_argument("--validation-stage", default=DEFAULT_VALIDATION_STAGE)
    parser.add_argument("--write-json", type=Path, default=DEFAULT_MATRIX_JSON)
    parser.add_argument("--write-markdown", type=Path, default=DEFAULT_MATRIX_MD)
    parser.add_argument("--require-pass", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    matrix = build_matrix(args)
    print_matrix(matrix)
    if args.write_json:
        args.write_json.parent.mkdir(parents=True, exist_ok=True)
        args.write_json.write_text(json.dumps(matrix, indent=2) + "\n", encoding="utf-8")
    if args.write_markdown:
        write_markdown(args.write_markdown, matrix)
    if args.require_pass and not matrix["passed"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
