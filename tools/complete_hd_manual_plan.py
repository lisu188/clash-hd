"""Plan human-operated complete-HD observations from an authenticated candidate.

This module reads files only. It never launches, attaches, captures, injects
input, or creates approval/proof records. Historical pulse plans are untouched.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any, Callable

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.patcher.framed_viewport import FramedViewport
import complete_hd_evidence as evidence
import hd_layout_command_input_summary as command

ROOT = Path(__file__).resolve().parents[1]
CAPTURE_ROOT = Path("C:/ClashCaptures")
SCHEMA = "complete_hd_human_observation_plan_v1"
SOURCES = (
    "tools/complete_hd_manual_plan.py", "src/patcher/framed_viewport.py",
    "scripts/smoke/run_clash_visual_smoke.ps1", "tools/menu_pulse_click.py",
    "tools/hd_layout_observation_manifest.py", "tools/hd_layout_command_input_summary.py",
    "probes/cdb/ui/clash95_hd_layout_command_input_extra.cdb",
    "tools/complete_hd_evidence.py", "tools/complete_hd_runtime_context.py",
)


def file_ref(path: Path) -> dict[str, str]:
    return {"path": str(path.resolve()), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def capture_template(context: dict, output: Path, target: str) -> dict:
    """Unresolved structured argv: never a runnable command or launch request."""
    return {
        "status": "capture_only_requires_fresh_approval_and_runtime_binding",
        "program": "powershell.exe",
        "arguments": ["-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
            str(ROOT / "scripts/smoke/run_clash_visual_smoke.ps1"),
            "-Exe", context["candidate_path"], "-Resolution", context["identity"]["resolution"],
            "-Stage", context["identity"]["stage"], "-InputMode", "manual",
            "-ObserveProcessId", {"runtime_value": "owned_candidate_pid", "minimum": 1},
            "-RunSeconds", "60", "-ObserveIntervalMs", "250", "-Route", "menu-only",
            "-OutRoot", str(output / target), "-AllowVisibleRuntime"],
        "unresolved": ["fresh explicit approval bound to the saved plan hash",
                       "positive PID and start time of the separately approved candidate owner",
                       "actual loaded executable path/SHA, wrapper/configuration, HWND and measured client placement"],
        "launches_candidate": False, "injects_input": False,
        "manual_input_accepted": False,
        "limitations": [
            "The existing attach-only harness collects frames; it does not verify this complete manifest or accept manual proof.",
            "Never omit ObserveProcessId or substitute zero: that selects the historical launch/global-cleanup path.",
            "The owning approved launcher/observer must verify cleanup of its exact process; the attachment does not own it.",
        ],
    }


def targets(context: dict, geometry: FramedViewport) -> list[dict]:
    ox, oy = (geometry.width - 640) // 2, (geometry.height - 480) // 2
    canvas = [ox, oy, ox + 639, oy + 479]
    terrain = list(geometry.terrain.as_tuple())
    cells = [list(cell.as_tuple()) for cell in geometry.action_cells]
    left, top = cells[0][:2]
    native_sequence = list(command.SEQUENCE)
    common = {
        "stage": context["identity"]["stage"], "candidate_identity": context["identity"],
        "input_method": "manual_directinput", "input_operator": "human",
        "status": "pending_human_observation_and_target_binding", "evidence_accepted": False,
        "required_evidence": ["exact approved candidate/run identity and measured client placement",
            "human-operated cursor and pressed-input observation aligned to the displayed target",
            "same-thread native hit/dispatch/callback sequence where implemented",
            "2-3 consecutive raw captures before and after each transition, tear analysis and operator notes",
            "observed expected behavior, no crash, and exact owned-process cleanup"],
    }
    specs = [
        {
            "id": "stable_menu_load", "title": "Centered menu and save-load controls",
            "geometry": {"native_canvas_inclusive": [0, 0, 639, 479], "display_canvas_inclusive": canvas,
                         "clickable_rectangles": None},
            "human_steps": ["Use the physical mouse and keyboard to reach the displayed main menu.",
                "Select the displayed Load control, a prepared isolated test save and its confirmation by hand.",
                "Record each menu transition and the healthy map after loading; retain misses and failed transitions."],
            "native_observer": {"implemented": False, "descriptor": None, "hit_test": None, "callback": None},
            "blocking_gaps": ["Candidate-bound menu/load-list descriptor geometry and passive native callback observer are unimplemented.",
                "Centered canvas bounds are not control hitboxes; the historical load-list coordinates must not be translated by assumption.",
                "The exact isolated save, starting state and loader route must be bound before execution."],
        },
        {
            "id": "stable_hd_map_input", "title": "Expanded map selection, scrolling and minimap",
            "geometry": {"terrain_inclusive": terrain,
                "frame_bands_inclusive": [list(rect.as_tuple()) for rect in geometry.frame_bands],
                "rightmost_middle_cell_inclusive": list(geometry.cell_rect(geometry.ceil_tiles[0] - 1, geometry.ceil_tiles[1] // 2).as_tuple()),
                "bottom_middle_cell_inclusive": list(geometry.cell_rect(geometry.ceil_tiles[0] // 2, geometry.ceil_tiles[1] - 1).as_tuple()),
                "minimap": {"exclusive_right_anchor": geometry.minimap_right_anchor, "top": 16,
                            "backing_size": None, "clickable_rectangle": None}},
            "human_steps": ["Select a visible unit and visible terrain using the physical mouse.",
                "Move by hand toward each displayed map edge; observe horizontal and vertical scrolling and world-end clamps.",
                "After the minimap backing bounds are measured for this world, operate visible minimap targets by hand and verify viewport movement and erasure.",
                "Repeat selection, movement and deselection after scrolling; inspect all four borders and action controls."],
            "native_observer": {"implemented": False, "descriptor": None, "hit_test": None, "callback": None},
            "blocking_gaps": ["Native edge-scroll trigger bounds, selected world targets and candidate-bound grid/minimap input observers are unimplemented.",
                "Listed terrain cells are geometry regions only; visible terrain, world ownership and overlay exclusion must be observed.",
                "Minimap backing dimensions depend on the world and must be measured; no fixed 214-pixel assumption is accepted."],
        },
        {
            "id": "right_bottom_validation_input", "title": "Relocated command panel and lower/right controls",
            "geometry": {"action_cells_inclusive": cells,
                "first_command_native_hit_bounds_exclusive": [left, top, left + 63, top + 31],
                "first_command_point": [left + 32, top + 16]},
            "human_steps": ["Select an ordinary map unit by hand, then hold the cursor over central traversable terrain for captures.",
                "Hover the first displayed command icon without changing selection, then click it once by hand.",
                "Observe the native callback and resulting behavior; inspect all six cells and the right/bottom borders before and after the transition."],
            "native_observer": {"implemented": True, "scope": "first ordinary selected-unit command only; separate panel callback proof",
                "producer": "tools/hd_layout_observation_manifest.py", "input_method": "manual_directinput",
                "required_candidate_argument": "--candidate-manifest",
                "descriptor": f"0x{command.EXPECTED_DESCRIPTOR:08x}",
                "dispatch": f"0x{command.EXPECTED_DISPATCH:08x}",
                "callback": f"0x{command.EXPECTED_CALLBACK:08x}",
                "callback_return_address": f"0x{command.EXPECTED_RETURN:08x}",
                "sequence": native_sequence,
                "contract": "Complete loaded-byte guards must precede the exact run identity and ordered same-thread descriptor, hit, pressed-input gate, dispatch and callback records.",
                "manual_release_proof": False},
            "blocking_gaps": ["The first-command observer does not cover every action cell, lower/right grid target or castle owner control.",
                "The complete manual-target release verifier is unimplemented; panel callback evidence cannot substitute for the five human targets."],
        },
        {
            "id": "castle_barracks_centered_input", "title": "Centered barracks controls and map return",
            "geometry": {"native_canvas_inclusive": [0, 0, 639, 479], "display_canvas_inclusive": canvas,
                         "clickable_rectangles": None},
            "human_steps": ["After the castle route and actual hit-map targets are bound, enter that castle and its barracks by hand.",
                "Operate the displayed barracks controls by hand, recording portraits/slots and callback behavior.",
                "Exit by hand and inspect restored map painting, selection, all borders and action cells."],
            "native_observer": {"implemented": False, "descriptor": None, "hit_test": None, "callback": None},
            "blocking_gaps": ["A candidate- and save-bound castle-entry route, barracks hit-map targets and passive native input observer are unimplemented.",
                "Slot drawing rectangles and historical pulse coordinates are not clickable-control proof.",
                "Allocation/ownership restoration and healthy post-exit redraw still need matching runtime evidence."],
        },
        {
            "id": "castle_overview_centered_input", "title": "Centered castle overview controls and return",
            "geometry": {"native_canvas_inclusive": [0, 0, 639, 479], "display_canvas_inclusive": canvas,
                         "clickable_rectangles": None},
            "human_steps": ["After each actual castle hit-map target is bound, operate the displayed overview routes by hand.",
                "Record entry, visible controls, native callback behavior and exit for each required route, including court, recruitment and peasants.",
                "Return to the map by hand and verify painting, selection and controls remain healthy."],
            "native_observer": {"implemented": False, "descriptor": None, "hit_test": None, "callback": None},
            "blocking_gaps": ["Overview targets depend on the actual castle hit-map asset and owner state; no fixed control rectangles are admitted.",
                "Candidate-bound passive observers and complete route/return evidence are unimplemented."],
        },
    ]
    return [{**copy.deepcopy(common), **spec} for spec in specs]


def build_plan(candidate_manifest: Path, *, run_id: str, output_root: Path,
               context_loader: Callable = evidence.candidate_manifest_context) -> dict[str, Any]:
    if not re.fullmatch(r"[A-Za-z0-9_.-]{1,100}", run_id) or run_id in (".", ".."):
        raise ValueError("run ID must be a bounded path-safe identifier")
    output = (output_root.resolve() / run_id).resolve()
    if (not output.is_relative_to(CAPTURE_ROOT.resolve()) or output == CAPTURE_ROOT.resolve()
            or output.is_relative_to(ROOT.resolve()) or output.exists()):
        raise ValueError("planned raw output must be a new external directory under C:/ClashCaptures")
    context = context_loader(candidate_manifest.resolve())
    identity = context["identity"]
    if (identity.get("stage") != evidence.STAGE or identity.get("recipe_revision") != evidence.RECIPE_REVISION
            or context.get("byte_rebuild_passed") is not True):
        raise ValueError("human plan requires the reconstructed complete candidate recipe")
    width, height = map(int, identity["resolution"].split("x"))
    geometry = FramedViewport(width, height)
    bundle = {name: file_ref(Path(context[key])) for name, key in
              (("candidate", "candidate_path"), ("metadata", "metadata_path"), ("canonical_probe", "probe_path"))}
    for artifact, key in (("candidate", "candidate_sha256"), ("metadata", "metadata_sha256"), ("canonical_probe", "probe_sha256")):
        if bundle[artifact]["sha256"] != identity[key]:
            raise ValueError("complete candidate bundle changed during human planning")
    rows = targets(context, geometry)
    for row in rows:
        row["capture_template"] = capture_template(context, output, row["id"])
    return {
        "schema": SCHEMA, "run_id": run_id, "planning_valid": True,
        "executed": False, "runtime_ready": False, "manual_input_accepted": False, "promotion_ready": False,
        "candidate_identity": identity, "artifacts": bundle,
        "source_artifacts": {name: file_ref(ROOT / name) for name in SOURCES},
        "candidate_source_hashes": context["source_hashes"], "output_directory": str(output),
        "input_policy": {"method": "manual_directinput", "operator": "human", "injected_input_allowed": False,
                         "forced_routes_or_callbacks_allowed": False,
                         "watching_injected_input_is_manual_proof": False},
        "approval_requirement": {"fresh_explicit_user_approval_required": True,
            "creates_approval_record": False,
            "must_bind": ["saved plan SHA-256", "candidate_identity", "run_id", "wrapper and configuration SHA-256",
                          "isolated save and assets", "output_directory", "human-only input method", "permitted runtime interval"]},
        "measured_placement_requirement": {"expected_client_size": [width, height],
            "fixed_desktop_offset": None, "inspect": "all four client corners, center, and each actual control target",
            "policy": "Measure client-to-screen geometry and accessibility after approval; stop if any required target is inaccessible. Do not move or focus a window through this planner."},
        "capture_contract": {"count_per_checkpoint": [2, 3], "prefer": "consecutive pixel-identical pair",
            "tear_check_source": file_ref(ROOT / "tools/capture_tear_check.py"),
            "labels": ["stage", "resolution", "capture method", "target/transition", "result"],
            "raw_material_outside_repository": True},
        "targets": rows,
        "blocking_gaps": ["A separate approved owner must launch the exact candidate and bind its runtime identity and cleanup.",
            "Visible wrapper/configuration and isolated save/assets are not yet bound to this planning-only artifact.",
            "The five complete-candidate manual release verifiers are unimplemented; every target remains incomplete.",
            "Capture completion and generated plans are not evidence of native input, behavior, or release eligibility."],
    }


def validate_plan(plan: dict, candidate_manifest: Path, *, context_loader: Callable = evidence.candidate_manifest_context) -> None:
    output = Path(plan["output_directory"])
    expected = build_plan(candidate_manifest, run_id=plan["run_id"], output_root=output.parent, context_loader=context_loader)
    if plan != expected:
        raise ValueError("human plan differs from exact candidate, sources, geometry, or human-only contract")


def write_plan(path: Path, plan: dict) -> None:
    path = path.resolve()
    if not path.is_relative_to(CAPTURE_ROOT.resolve()) or path.is_relative_to(ROOT.resolve()):
        raise ValueError("human plan output must remain outside the repository under C:/ClashCaptures")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(plan, stream, indent=2)
        stream.write("\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-manifest", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--write-json", type=Path)
    parser.add_argument("--require-runtime-ready", action="store_true")
    args = parser.parse_args()
    try:
        plan = build_plan(args.candidate_manifest, run_id=args.run_id, output_root=args.output_root)
        if args.write_json:
            write_plan(args.write_json, plan)
        else:
            print(json.dumps(plan, indent=2))
        return 2 if args.require_runtime_ready and not plan["runtime_ready"] else 0
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(2, f"cannot prepare human observation plan: {error}\n")


if __name__ == "__main__":
    raise SystemExit(main())
