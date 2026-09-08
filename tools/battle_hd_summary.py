#!/usr/bin/env python3
"""Fail-closed, repo-only evidence summary for the 1280x720 battle HD lane.

The catalog probe proves owner visits only. Geometry, actions, modal completion,
return health, and final composition need dedicated observations; visiting an
owner or printing the intended layout never proves those claims. Existing
centered-native BATTLE_* evidence cannot satisfy this separate BATTLE_HD_* lane.

Run manifest schema 1 binds candidate, candidate_sha256, stage, resolution,
wrapper, launch_mode, input_method, input_evidence_class, route_method,
log_sha256, and explicit forced_actions (an array). Optional visible proof binds
the same identity, approval_record, frames [{path, sha256}], tear_check
{path, sha256}, and composition_checks. Paths resolve against their manifest.
This tool grades records; it cannot grant approval or authenticate human input.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path, PureWindowsPath
from typing import Any


EXPECTED_STAGE = (
    "gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-"
    "presentbounds-minimapright-dynvswitch-castlecenter-all-battlehd"
)
EXPECTED_BASE_SHA256 = "500055D77D03D514E8D3168506BD10F67CD8569BCC450604FF8192F46CDAF3AE"
RESOLUTION = [1280, 720]
BATTLEFIELD_RECT = [32, 136, 1120, 584]  # Half-open bounds, 17 by 7 native tiles.
HUD_RECT = [1120, 120, 1280, 600]
OWNER_ADDRESSES = {
    "ENTRY": 0x42E9E0, "FULL_REDRAW": 0x430C20, "DIRTY_REDRAW": 0x430B20,
    "PROJECTION": 0x42FFB0, "CAMERA": 0x426E20, "PAN": 0x42C840,
    "GRID": 0x42CB50, "HUD": 0x430F80, "FRAME": 0x42E8B0,
    "BANNER": 0x42D730, "DIALOG": 0x42DAE0, "RESULTS": 0x42E5A0,
    "RETURN": 0x41B14A, "MAP_POLL": 0x40B0C3,
}
STREAM_MARKER_RE = re.compile(r"(?<!\S)((?:BATTLE|SURFDUMP)_[A-Z][A-Z0-9_]*)\b")
KV_RE = re.compile(r"([a-z][a-z0-9_]*)=(\([^)]*\)|\S+)")
SHA_RE = re.compile(r"[0-9a-fA-F]{64}")
PLACEHOLDER_RE = re.compile(r"placeholder|replace_|pending|not.recorded", re.I)
FORCE_RE = re.compile(r"^(?:BATTLE|BATTLE_HD)_[A-Z_]*(?:FORCE|SYNTHETIC|SKIP|SPIN_GUARD|LOST_GUARD)[A-Z_]*\b")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def load_json(path: Path | None) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig")) if path else {}
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def parse_value(value: str) -> Any:
    if value.startswith("(") and value.endswith(")"):
        return [parse_value(item) for item in value[1:-1].split(",")]
    if re.fullmatch(r"0x[0-9a-fA-F]+|[0-9a-fA-F]{8}", value):
        return int(value, 16)
    if re.fullmatch(r"-?\d+", value):
        return int(value)
    return value


def parse_rows(log: str) -> tuple[list[dict[str, Any]], list[str], list[str]]:
    """Read output records, including adjacent records on one physical line.

    CDB nested breakpoint commands can consume the escaped printf newline.
    Splitting at *all* battle/surfdump marker boundaries prevents unrelated
    marker fields from being attributed to an HD record. Command echoes,
    quoted payloads, format strings, and malformed field text are not records.
    ``order`` retains chronology when several records share ``line``.
    """
    rows, errors, interventions = [], [], []
    lines = log.splitlines()
    initial_break_seen = False
    for number, raw in enumerate(lines, 1):
        line = raw.strip()
        # Echoed .printf commands (including ones with fully literal payloads)
        # must never count as observed debugger output.
        if re.match(r"^(?:\d+:\d+>|bp\b|\.printf\b|\.echo\b)", line):
            continue
        # CDB's initial loader stop precedes execution of our command file.
        # Recognize its actual ntdll owner; an arbitrary INT3 stays a failure.
        initial_break = (not initial_break_seen and not rows and not interventions
                         and re.search(r"Break instruction exception - code 80000003 \(first chance\)", line)
                         and any(re.match(r"ntdll!LdrpDoDebuggerBreak\b", context.strip())
                                 for context in lines[number:number + 6]))
        if initial_break:
            initial_break_seen = True
        if not initial_break and re.search(r"access violation|code c0000005|unable to (?:insert|remove) breakpoint|breakpoint .*failed|code 80000003|syntax error|extra character error|couldn't resolve error", line, re.I):
            errors.append(f"line {number}: {line}")
        markers = list(STREAM_MARKER_RE.finditer(line))
        # Do not salvage strings embedded in commands, diagnostics, or quotes.
        if not markers or markers[0].start() != 0:
            continue
        for index, marker in enumerate(markers):
            name = marker[1]
            end = markers[index + 1].start() if index + 1 < len(markers) else len(line)
            payload = line[marker.end():end].strip()
            if FORCE_RE.match(name):
                interventions.append(name)
            if not name.startswith("BATTLE_HD_"):
                continue
            if re.search(r"^BATTLE_HD_(?:[A-Z0-9]+_)*(?:AV|FAIL|ERROR)(?:_|$)", name):
                errors.append(f"line {number}: {name} {payload}")
            if any(character in payload for character in '%";'):
                continue
            fields = list(KV_RE.finditer(payload))
            if KV_RE.sub("", payload).strip():
                continue
            names = [field[1] for field in fields]
            if len(names) != len(set(names)):
                errors.append(f"line {number}: duplicate marker fields")
                continue
            rows.append({"line": number, "order": len(rows), "marker": name,
                         "values": {field[1]: parse_value(field[2]) for field in fields}})
    return rows, errors, sorted(set(interventions))


def candidate_is_isolated(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    path = PureWindowsPath(value)
    return (path.is_absolute() and ".." not in path.parts
            and len(path.parts) > 2 and path.parts[0].lower() == "c:\\"
            and path.parts[1].lower() == "clashtests")


def artifact(ref: Any, base: Path) -> Path | None:
    if not isinstance(ref, dict) or not isinstance(ref.get("path"), str):
        return None
    path = Path(ref["path"])
    path = path if path.is_absolute() else base / path
    try:
        return path if digest(path) == str(ref.get("sha256", "")).upper() else None
    except OSError:
        return None


def visible_failures(proof_path: Path | None, manifest: dict[str, Any]) -> list[str]:
    proof = load_json(proof_path)
    failures = []
    if not proof or not proof_path:
        return ["matching visible composition proof is missing"]
    for key in ("candidate_sha256", "stage", "resolution", "wrapper", "input_method", "log_sha256"):
        if proof.get(key) != manifest.get(key):
            failures.append(f"visible proof {key} does not match the run")
    if proof.get("schema") != 1 or proof.get("approved") is not True:
        failures.append("visible proof schema or actual approval is missing")
    approval = proof.get("approval_record")
    if not isinstance(approval, str) or not approval.strip() or PLACEHOLDER_RE.search(approval):
        failures.append("visible proof has no substantive approval record")
    if manifest.get("launch_mode") != "visible-window":
        failures.append("hidden software-surface evidence is not visible composition")
    frames = proof.get("frames")
    verified = [artifact(ref, proof_path.parent) for ref in frames] if isinstance(frames, list) else []
    if not verified or any(path is None for path in verified):
        failures.append("visible frame files or their hashes are missing/mismatched")
    tear_path = artifact(proof.get("tear_check"), proof_path.parent)
    tear = load_json(tear_path)
    tear_frames = tear.get("frames") or []
    tear_names = {str(Path(row.get("frame", "")).resolve()) for row in tear_frames if isinstance(row, dict)}
    if tear.get("clean") is not True or not verified or any(str(path.resolve()) not in tear_names for path in verified if path):
        failures.append("clean tear assessment does not cover the supplied visible frames")
    checks = proof.get("composition_checks") or {}
    for key in ("battlefield", "hud", "frame", "banner", "modal", "post_return_map"):
        if checks.get(key) is not True:
            failures.append(f"visible {key} composition has no accepted observation")
    return failures


def helper_measurements(rows: list[dict[str, Any]], identity_valid: bool,
                        runtime_errors: list[str]) -> dict[str, Any]:
    """Grade direct debugger calls separately from end-to-end input/rendering.

    A successful mouse helper call proves its returned coordinates and carry,
    not movement/attack callbacks. Projection calls prove coordinates visited,
    not copied pixels, composition, animation correctness, or map restoration.
    """
    def values(name: str, **fields: Any) -> list[dict[str, Any]]:
        return [row["values"] for row in rows if row["marker"] == "BATTLE_HD_" + name
                and all(row["values"].get(key) == value for key, value in fields.items())]

    def arena_camera(value: dict[str, Any]) -> bool:
        arena, camera = value.get("arena"), value.get("camera")
        return (isinstance(arena, list) and len(arena) == 2
                and all(type(item) is int for item in arena) and 1 <= arena[0] <= 20 and arena[1] == 7
                and isinstance(camera, list) and len(camera) == 2
                and all(type(item) is int for item in camera)
                and 0 <= camera[0] <= max(0, arena[0] - 17) and camera[1] == 0)

    checks: dict[str, Any] = {}
    completed = bool(values("MEASUREMENTS_DONE", evidence="forced_hidden_helper_measurements"))

    def check(name: str, measured: bool, note: str) -> None:
        checks[name] = {"passed": measured and completed and identity_valid and not runtime_errors,
                        "measurement_matches": measured, "note": note}

    lower, upper = values("CLAMP_MEASURE", case="lower"), values("CLAMP_MEASURE", case="upper")
    clamp = any(arena_camera(low) and arena_camera(high)
                and low["arena"] == high["arena"] and low["camera"] == [0, 0]
                and high["camera"] == [max(0, high["arena"][0] - 17), 0]
                for low in lower for high in upper)
    check("camera_endpoints", clamp, "Forced out-of-range camera values followed by direct clamp calls; keyboard, drag, repeat, and selection recentering are separate claims.")

    points = {"top_left": [32, 136], "top_right": [1119, 136],
              "bottom_left": [32, 583], "bottom_right": [1119, 583],
              "hud": [1120, 136], "outside": [31, 136],
              "top_padding": [32, 135], "bottom_padding": [32, 584]}
    matched_cases = []
    for case, point in points.items():
        for value in values("MOUSE_CELL_MEASURE", case=case, point=point, mouse_after=point):
            if not arena_camera(value):
                continue
            local = [(point[0] - 32) // 64, (point[1] - 136) // 64]
            inside = (32 <= point[0] < 1120 and 136 <= point[1] < 584
                      and local[0] + value["camera"][0] < value["arena"][0])
            if value.get("carry") == int(not inside) and value.get("local") == (local if inside else [-1, -1]):
                matched_cases.append(case)
                break
    check("mouse_cell_boundaries", len(matched_cases) == len(points),
          "Forced raw mouse values and direct mouse-cell helper returns; no physical or injected input and no grid action callback are inferred.")

    full_tiles = values("TILE_MEASURE", eip=0x42FFB5, phase=11)
    full_pixels = values("PIXEL_MEASURE", eip=0x42FFE6, phase=11)
    coverage = False
    for value in values("DRAW_COVERAGE"):
        if not arena_camera(value) or value["camera"] != [0, 0]:
            continue
        width = min(17, value["arena"][0])
        expected = [[column, row] for column in range(width) for row in range(7)]
        expected_pixels = [(32 + column * 64, 136 + row * 64) for column, row in expected]
        coverage |= (value.get("columns_mask") == (1 << width) - 1
                     and value.get("tile_calls") == len(expected)
                     and [tile.get("world") for tile in full_tiles] == expected
                     and all(tile.get("camera") == [0, 0] for tile in full_tiles)
                     and [(pixel.get("x"), pixel.get("y")) for pixel in full_pixels] == expected_pixels)
    check("full_tile_projection", coverage,
          "Direct full-redraw call visited each existing visible tile and produced the expected tile origins; copy bounds and final composition remain separate.")

    dirty = bool(values("DIRTY_MEASURE", returned=1, tile=[8, 0])
                 and values("TILE_MEASURE", eip=0x42FFB5, phase=12, world=[8, 0], camera=[0, 0])
                 and values("PIXEL_MEASURE", eip=0x42FFE6, phase=12, x=544, y=136))
    check("dirty_tile_projection", dirty,
          "Direct dirty redraw reached and returned from tile (8,0), including its expected pixel origin; natural animation and dirty copy bounds remain separate.")

    descriptor_xy = ([1138, 490], [1201, 490], [1138, 521], [1138, 552], [1201, 521], [1145, 120])
    callbacks = (0x42D4E0, 0x42D3A0, 0x42D5B0, 0x42D670, 0x42D560, 0x42D6F0)
    descriptors = all(values("HUD_DESCRIPTOR", index=index, desc=0x514B78 + index * 53,
                             xy=xy, callback=callbacks[index]) for index, xy in enumerate(descriptor_xy))
    check("hud_descriptor_coordinates", descriptors,
          "Six descriptor positions and unchanged callback pointers were read from memory; command enabled/disabled behavior remains unproven.")
    frame_rectangles = (([0, 0, 31, 479], [0, 120]), ([480, 0, 639, 479], [1120, 120]),
                        ([32, 0, 479, 15], [32, 120]), ([32, 464, 479, 479], [32, 584]),
                        ([32, 0, 479, 15], [480, 120]), ([32, 464, 479, 479], [480, 584]),
                        ([32, 0, 223, 15], [928, 120]), ([32, 464, 223, 479], [928, 584]))
    frame = all(any(type(value.get("src")) is int and value["src"] != 0
                        and value.get("dst") == 0x51D4C0 and type(value.get("ret")) is int
                        and 0x566110 <= value["ret"] < 0x566320
                        for value in values("HUD_BLIT", source=source, destination=destination))
                for source, destination in frame_rectangles)
    check("frame_copy_rectangles", frame,
          "Eight native border/sidebar source rectangles reached the expected destination copy calls; completion and final pixels require separate evidence.")
    check("present_surface", bool(values("PRESENT_MEASURE", eip=0x460EA0, phase=14, surface=RESOLUTION)),
          "A direct present call saw the 1280x720 software surface; this is not final wrapper composition or a bounds check.")
    return {"evidence_class": "forced_hidden_helper_measurements", "sequence_completed": completed,
            "identity_valid": identity_valid, "runtime_errors": runtime_errors,
            "checks": checks, "mouse_cases_measured": matched_cases,
            "observed_arenas": sorted({tuple(value["arena"]) for value in lower + upper if arena_camera(value)}),
            "acceptance_claims_satisfied_by_helpers": False}


def camera_measurements(rows: list[dict[str, Any]], identity_valid: bool,
                        runtime_errors: list[str]) -> dict[str, Any]:
    """Actual clamp/recenter returns under explicitly installed arena fixtures."""
    def select(name: str) -> list[dict[str, Any]]:
        return [row for row in rows if row["marker"] == "BATTLE_HD_CAMERA_FIXTURE_" + name]
    measured = select("MEASURE")
    expected = {"width17_lower": ([17, 7], [0, 0], None), "width17_upper": ([17, 7], [0, 0], None),
                "width20_lower": ([20, 7], [0, 0], None), "width20_upper": ([20, 7], [3, 0], None),
                "recenter_left": ([20, 7], [0, 0], [0, 3]), "recenter_right": ([20, 7], [3, 0], [19, 3]),
                "retain_visible": ([20, 7], [3, 0], [10, 3])}
    matching = {}
    for case, (arena, camera, unit) in expected.items():
        matching[case] = [row for row in measured if row["values"].get("case") == case
                          and row["values"].get("arena") == arena and row["values"].get("camera") == camera
                          and (unit is None or row["values"].get("unit0") == unit)]
    restored = any(saved["values"] == returned["values"] and saved["order"] < returned["order"] < done["order"]
                   and all(any(saved["order"] < row["order"] < returned["order"] for row in matching[case]) for case in expected)
                   and done["values"].get("proof") == "forced_hidden_clamp_recenter_not_natural_arena"
                   for saved in select("SAVED") for returned in select("RESTORED") for done in select("COMPLETE"))
    return {"evidence_class": "forced_hidden_camera_fixture", "sequence_completed": restored,
            "identity_valid": identity_valid, "runtime_errors": runtime_errors,
            "checks": {case: {"passed": bool(found) and restored and identity_valid and not runtime_errors,
                               "measurement_matches": bool(found)} for case, found in matching.items()},
            "original_state_restored": restored,
            "observed_cases": [row["values"] for row in measured],
            "saved_state": [row["values"] for row in select("SAVED")],
            "restored_state": [row["values"] for row in select("RESTORED")],
            "note": "Arena widths17/20 and unit0 coordinates were forced only around direct clamp/recenter calls. No rendering was allowed with fixture state; natural 17/20-column arenas, camera input, and frame correctness remain separate.",
            "acceptance_claims_satisfied_by_camera_fixture": False}


def lifecycle_measurements(rows: list[dict[str, Any]], identity_valid: bool,
                           runtime_errors: list[str]) -> dict[str, Any]:
    """Keep forced callback, copy-call, and restoration observations distinct."""
    def select(name: str, **fields: Any) -> list[dict[str, Any]]:
        return [row for row in rows if row["marker"] == "BATTLE_HD_LIFECYCLE_" + name
                and all(row["values"].get(key) == value for key, value in fields.items())]

    def centered(rect: Any) -> bool:
        return (isinstance(rect, list) and len(rect) == 4 and all(type(v) is int for v in rect)
                and 32 <= rect[0] <= rect[2] < 1120 and 136 <= rect[1] <= rect[3] < 584
                and abs(rect[0] + rect[2] + 1 - 1152) <= 1
                and abs(rect[1] + rect[3] + 1 - 720) <= 1)

    checks: dict[str, Any] = {}
    def check(name: str, observed: bool, note: str) -> None:
        checks[name] = {"passed": observed and identity_valid and not runtime_errors,
                        "measurement_matches": observed, "note": note}

    banners = select("BANNER_DRAW")
    restored_banners = select("BANNER_RESTORED")
    check("banner_geometry", any(centered(row["values"].get("rect")) for row in banners),
          "An inclusive banner rectangle was measured within one pixel of the battlefield center; final colors and pixels are separate.")
    check("banner_render_hook_restore", any(restored["order"] > draw["order"]
          and restored["values"].get("render") == draw["values"].get("saved_render")
          and restored["values"].get("render") == restored["values"].get("expected")
          and restored["values"].get("hook") == restored["values"].get("expected_hook")
          and bool(restored["values"].get("render")) and bool(restored["values"].get("hook"))
          for draw in banners for restored in restored_banners),
          "Measured render and hook pointers matched their saved values after forced banner dismissal.")
    check("banner_cursor_return", any(row["values"].get("mouse") == [576, 360] for row in restored_banners),
          "The logical cursor must actually read (576,360) at the banner-return observation; intended patch coordinates alone do not pass.")
    for case, attack, state in (("disabled", 0, 1), ("enabled", 1, 2)):
        observed = any(row["values"].get("attack") == attack and row["values"].get("descriptor_state") == state
                       and type(row["values"].get("enabled")) is int
                       and bool(row["values"]["enabled"]) == (case == "enabled")
                       for row in select("COMMAND_RETURN", case=case))
        check(f"{case}_callback_state", observed,
              "Unit type and descriptor state were forced before a direct callback; returned state is observed, without physical click or grid-action proof.")
    modals = select("MODAL_DRAW")
    restored_modals = select("MODAL_RESTORED")
    modal = any(centered(draw["values"].get("rect"))
                and draw["order"] < result["order"] < restored["order"]
                and restored["values"].get("result") == 1
                and restored["values"].get("render") == draw["values"].get("saved_render")
                and restored["values"].get("render") == restored["values"].get("expected")
                and bool(restored["values"].get("render"))
                for draw in modals for result in select("MODAL_CALLBACK_RETURN", yes=1) for restored in restored_modals)
    check("modal_yes_and_render_restore", modal,
          "Centered modal geometry, directly forced Yes callback result, and render-pointer restoration were observed in order; No and real input remain unproven.")
    check("modal_cursor_return", any(row["values"].get("mouse") == [576, 360] for row in restored_modals),
          "The logical cursor must actually read (576,360) after modal restoration.")
    geometries = select("RESULTS_GEOMETRY", scope=1)
    results_geometry = False
    results_copies = False
    for row in geometries:
        origin, size = row["values"].get("origin"), row["values"].get("size")
        if (not isinstance(origin, list) or len(origin) != 2 or not isinstance(size, list) or len(size) != 2
                or not all(type(v) is int for v in origin + size) or min(size) <= 0):
            continue
        x, y = origin
        width, height = size
        rect = [x, y, x + width - 1, y + height - 1]
        if not centered(rect):
            continue
        results_geometry = True
        results_copies |= any(row["order"] < saved["order"] < restored["order"]
                             and saved["values"].get("src") == 0 and bool(saved["values"].get("dst"))
                             and restored["values"].get("src") == saved["values"].get("dst")
                             and restored["values"].get("dst") == 0
                             for saved in select("RESULTS_COPY", ret=0x4454F5, source=rect, destination=[0, 0])
                             for restored in select("RESULTS_COPY", ret=0x44589F, source=[0, 0, width - 1, height - 1], destination=origin))
    check("results_geometry", results_geometry,
          "The shared results message measured native size at the battlefield center while battle-specific scope was1.")
    check("results_copy_rectangles", results_copies,
          "Results background save/restore copy calls used matching rectangles and the same temporary buffer; final pixels remain separate.")
    check("results_scope_restore", any(restored["order"] > geometry["order"]
          and restored["values"].get("renderer") == restored["values"].get("expected") == geometry["values"].get("renderer")
          and bool(restored["values"].get("renderer"))
          for geometry in geometries for restored in select("RESULTS_SCOPE_RESTORED", scope=0)),
          "After results dismissal, battle-specific scope returned0 and the renderer matched its saved pointer.")
    cursor_queued = select("CURSOR_QUEUED")
    cursor_polled = select("CURSOR_POST_POLL")
    check("cursor_targets_queued", all(select("CURSOR_QUEUED", ret=caller, logical=[576, 360]) for caller in (0x42DA46, 0x42DE6E, 0x566533)),
          "Banner, modal, and results queued(576,360) before the immediate input poll; this does not prove the poll retained that target.")
    check("results_cursor_return", bool(select("CURSOR_POST_POLL", ret=0x566533, logical=[576, 360])),
          "The results cursor must still read(576,360) after its immediate input poll.")
    entries = select("ENTRY", surface=RESOLUTION)
    restored_owners = select("OWNER_RESTORED", surface=RESOLUTION)
    polls = select("MAP_POLL", surface=RESOLUTION)
    healthy_returns = []
    for entry in entries:
        initial = entry["values"]
        bounds = initial.get("input_bounds")
        if (not initial.get("render") or not initial.get("hook") or not isinstance(bounds, list) or len(bounds) != 4
                or not all(type(value) is int for value in bounds)
                or not (0 <= bounds[0] < bounds[2] <= 1280 and 0 <= bounds[1] < bounds[3] <= 720)):
            continue
        for owner in restored_owners:
            restored = owner["values"]
            if not (owner["order"] > entry["order"]
                    and restored.get("hook") == initial.get("hook") == restored.get("expected_hook")
                    and restored.get("input_bounds") == initial.get("input_bounds")):
                continue
            for continuation in select("UNIT_ATTACK_CONTINUATION"):
                for poll in polls:
                    if (owner["order"] < continuation["order"] < poll["order"]
                            and all(poll["values"].get(key) == initial.get(key) for key in ("render", "hook", "input_bounds"))):
                        healthy_returns.append((entry, poll))
    check("owner_hook_and_map_state_restore", bool(healthy_returns),
          "Battle owner hook/input bounds matched entry; after Unit_Attack continuation the map poll also matched entry render pointer. This does not prove correct restored pixels or map input.")
    completed = any(entry["order"] < results["order"] < returned["order"] < freed["order"] < continuation["order"] < poll["order"] < draw["order"]
                    for entry in entries for results in select("RESULTS_ENTRY") for returned in select("RESULTS_RETURN")
                    for freed in select("BATTLE_FREED", battle=0) for continuation in select("UNIT_ATTACK_CONTINUATION")
                    for poll in polls for draw in select("MAP_REDRAW_RETURNED", proof="forced_hidden_owner_call"))
    check("results_and_forced_map_redraw", completed,
          "Results and their return preceded the restored map poll and a direct map-redraw return; this is a forced lifecycle diagnostic.")
    return {"evidence_class": "forced_hidden_lifecycle", "sequence_completed": completed,
            "identity_valid": identity_valid, "runtime_errors": runtime_errors, "checks": checks,
            "observed_banner_rects": [row["values"].get("rect") for row in banners],
            "observed_banner_return_mouse": [row["values"].get("mouse") for row in restored_banners],
            "observed_modal_rects": [row["values"].get("rect") for row in modals],
            "observed_modal_return_mouse": [row["values"].get("mouse") for row in restored_modals],
            "observed_owner_state": [row["values"] for row in restored_owners],
            "observed_map_poll_state": [row["values"] for row in polls],
            "observed_results_geometry": [row["values"] for row in geometries],
            "observed_cursor_queued": [row["values"] for row in cursor_queued],
            "observed_cursor_post_poll": [row["values"] for row in cursor_polled],
            "post_return_composition_proven": False,
            "acceptance_claims_satisfied_by_forced_lifecycle": False}


def build_summary(capture_or_log: Path, run_manifest: Path | None = None,
                  patch_stage_json: Path | None = None,
                  visible_proof: Path | None = None) -> dict[str, Any]:
    log_path = capture_or_log / "cdb-surface-dump.log" if capture_or_log.is_dir() else capture_or_log
    manifest_path = run_manifest or (capture_or_log / "battle-hd-run.json" if capture_or_log.is_dir() else None)
    manifest, patch = load_json(manifest_path), load_json(patch_stage_json)
    try:
        log = log_path.read_text(encoding="utf-8", errors="replace")
        log_sha = digest(log_path)
    except OSError:
        log, log_sha = "", None
    rows, runtime_errors, interventions = parse_rows(log)
    identity_errors = []
    if not log_sha:
        identity_errors.append("runtime log is missing")
    if manifest.get("schema") != 1:
        identity_errors.append("schema 1 run manifest is missing")
    for key, expected in (("stage", EXPECTED_STAGE), ("resolution", RESOLUTION), ("log_sha256", log_sha)):
        if expected is None or manifest.get(key) != expected:
            identity_errors.append(f"run {key} is missing or mismatched")
    sha = manifest.get("candidate_sha256")
    if not isinstance(sha, str) or not SHA_RE.fullmatch(sha):
        identity_errors.append("candidate SHA-256 is missing or malformed")
    if not candidate_is_isolated(manifest.get("candidate")):
        identity_errors.append("candidate must be an isolated C:\\ClashTests path")
    for key in ("wrapper", "input_method", "input_evidence_class", "route_method", "launch_mode"):
        value = manifest.get(key)
        if not isinstance(value, str) or not value.strip() or PLACEHOLDER_RE.search(value):
            identity_errors.append(f"run {key} is not classified")
    if not isinstance(manifest.get("forced_actions"), list):
        identity_errors.append("forced_actions must be explicitly recorded, including an empty list")
    if (patch.get("stage") != EXPECTED_STAGE or patch.get("exe_sha256") != sha
            or not candidate_is_isolated(patch.get("exe"))
            or patch.get("resolution") != "1280x720"
            or patch.get("expected_base_sha256") != EXPECTED_BASE_SHA256):
        identity_errors.append("patch-stage identity does not match the run and known original")
    counts = patch.get("status_counts")
    counts = counts if isinstance(counts, dict) else {}
    # patch_stage_report serializes a Counter; zero-count statuses are absent.
    if (type(counts.get("patched")) is not int or counts["patched"] <= 0
            or any(type(counts.get(key, 0)) is not int or counts.get(key, 0) != 0 for key in ("original", "unexpected"))
            or set(counts) - {"patched", "original", "unexpected"}
            or type(patch.get("patch_count")) is not int
            or patch.get("patch_count") != counts.get("patched")):
        identity_errors.append("complete patched byte verification is missing")

    def found(name: str, **fields: Any) -> list[dict[str, Any]]:
        eip = OWNER_ADDRESSES.get(name)
        return [row for row in rows if row["marker"] == "BATTLE_HD_" + name
                and (eip is None or row["values"].get("eip") == eip)
                and all(row["values"].get(key) == value for key, value in fields.items())]

    claims: dict[str, dict[str, Any]] = {}

    def claim(name: str, failures: list[str]) -> None:
        claims[name] = {"passed": not failures and not identity_errors and not runtime_errors,
                        "failures": failures, "identity_valid": not identity_errors}

    claim("identity", identity_errors)
    interval_completed = bool(found("MEASUREMENTS_DONE", evidence="forced_hidden_helper_measurements")
                              or lifecycle_measurements(rows, not identity_errors, runtime_errors)["sequence_completed"]
                              or camera_measurements(rows, not identity_errors, runtime_errors)["sequence_completed"]
                              or found("MAP_HEALTH", surface=RESOLUTION, input_restored=1,
                                       render_restored=1, source="observed"))
    claim("runtime_health", runtime_errors + ([] if interval_completed else ["no completed helper sequence or post-return health observation"]))
    claims["runtime_health"]["scope"] = "Completed observed interval without logged runtime/debugger errors; not liveness, soak, or final composition."
    visits = {name: bool(found(name)) for name in OWNER_ADDRESSES}
    required_owners = set(OWNER_ADDRESSES) - {"RESULTS", "RETURN", "MAP_POLL"}
    claim("route_catalog", [f"owner {name} was not observed" for name in sorted(required_owners) if not visits[name]])
    # Dedicated measurement rows, absent from the observational catalog, are
    # required. Intended configuration and owner visits cannot satisfy these.
    geometry = found("GEOMETRY", observed_rect=BATTLEFIELD_RECT, observed_hud=HUD_RECT,
                     observed_tiles=[17, 7], surface=RESOLUTION, source="measured")
    claim("geometry", [] if geometry else ["measured expanded battlefield/HUD geometry is missing"])
    render_errors = []
    for name in ("FULL_REDRAW", "DIRTY_REDRAW"):
        if not found(name, clip=BATTLEFIELD_RECT, surface=RESOLUTION, bounds_ok=1):
            render_errors.append(f"{name} has no measured clipping/bounds observation")
    if not found("PRESENT", surface=RESOLUTION, bounds_ok=1):
        render_errors.append("battle HD presentation bounds are unproven")
    claim("render", render_errors)
    input_errors = []
    required_cases = {"top_left": [32, 136], "top_right": [1119, 136],
                      "bottom_left": [32, 583], "bottom_right": [1119, 583],
                      "hud": [1120, 136], "outside": [31, 136],
                      "top_padding": [32, 135], "bottom_padding": [32, 584]}
    for case, point in required_cases.items():
        matching = []
        for row in found("GRID_RESULT", case=case, point=point, source="observed"):
            values = row["values"]
            camera, arena = values.get("camera"), values.get("arena")
            if not isinstance(camera, list) or len(camera) != 2 or not all(type(v) is int for v in camera):
                continue
            if (not isinstance(arena, list) or len(arena) != 2 or not all(type(v) is int for v in arena)
                    or not (1 <= arena[0] <= 20 and arena[1] == 7)):
                continue
            if not (0 <= camera[0] <= max(0, arena[0] - 17) and camera[1] == 0):
                continue
            cell = [camera[0] + (point[0] - 32) // 64, camera[1] + (point[1] - 136) // 64]
            inside = (32 <= point[0] < 1120 and 136 <= point[1] < 584 and cell[0] < arena[0])
            if values.get("accepted") == int(inside) and values.get("cell") == (cell if inside else [-1, -1]):
                matching.append(row)
        if not matching:
            input_errors.append(f"grid {case} result is unproven")
    for case in ("enabled", "disabled"):
        if not found("COMMAND_RESULT", case=case, matched=1, source="observed"):
            input_errors.append(f"{case} command outcome is unproven")
    for direction in ("left", "right", "up", "down"):
        pan_rows = found("PAN_RESULT", direction=direction, source="observed")
        matched = False
        for row in pan_rows:
            camera, arena = row["values"].get("camera"), row["values"].get("arena")
            if (not isinstance(arena, list) or len(arena) != 2 or not all(type(v) is int for v in arena)
                    or not (1 <= arena[0] <= 20 and arena[1] == 7)
                    or not isinstance(camera, list) or len(camera) != 2 or not all(type(v) is int for v in camera)):
                continue
            maximum = max(0, arena[0] - 17)
            matched |= (0 <= camera[0] <= maximum and camera[1] == 0
                        and (direction != "left" or camera[0] == 0)
                        and (direction != "right" or camera[0] == maximum)
                        and row["values"].get("camera_after_repeat") == camera)
        if not matched:
            input_errors.append(f"{direction} camera pan/clamp is unproven")
    claim("input", input_errors)
    modal_rows = found("MODAL_RESULT", opened=1, closed=1, input_restored=1, source="observed")
    claim("modal", [] if visits["DIALOG"] and modal_rows else ["modal open/use/close and restored input are unproven"])
    entries, results, returns, polls = (found(name) for name in ("ENTRY", "RESULTS", "RETURN", "MAP_POLL"))
    ordered_return = any(entry["order"] < result["order"] < returned["order"] < poll["order"]
                         for entry in entries for result in results for returned in returns for poll in polls)
    restored = found("MAP_HEALTH", surface=RESOLUTION, input_restored=1, render_restored=1, source="observed")
    return_errors = []
    if not ordered_return:
        return_errors.append("ordered battle entry/results/Unit_Attack return/map poll was not observed")
    if not any(health["order"] > poll["order"] for health in restored for poll in polls):
        return_errors.append("post-return HD map rendering and input are unproven")
    claim("return", return_errors)
    claim("visible", visible_failures(visible_proof, manifest))
    forced_actions = manifest.get("forced_actions") or []
    is_forced = bool(interventions or forced_actions or manifest.get("route_method") != "natural")
    manual = manifest.get("input_evidence_class") == "manual_directinput" and manifest.get("input_method") == "human"
    evidence_class = "forced_validation" if is_forced else "manual_runtime" if manual else "automated_runtime"
    claim("unforced_runtime", ["forced route/actions or debugger intervention remain present"] if is_forced else [])
    failures = [f"{name}: {reason}" for name, check in claims.items() for reason in check["failures"]]
    return {
        "schema": 1, "generated_at": datetime.now(timezone.utc).isoformat(),
        "runtime_policy": "repo-only evidence parsing; launches no game, debugger, wrapper, or visible window",
        "passed": all(check["passed"] for check in claims.values()),
        "stage": EXPECTED_STAGE, "candidate": manifest.get("candidate"),
        "candidate_sha256": sha, "resolution": RESOLUTION,
        "patch_verification": {"report": str(patch_stage_json) if patch_stage_json else None,
                               "candidate": patch.get("exe"), "candidate_sha256": patch.get("exe_sha256"),
                               "patch_count": patch.get("patch_count"), "status_counts": counts,
                               "binding": "identical executable SHA-256; runtime and verification paths are recorded independently"},
        "runtime_context": {key: manifest.get(key) for key in ("wrapper", "launch_mode", "input_method",
                                                               "input_evidence_class", "route_method", "harness_result")},
        "source_artifacts": manifest.get("artifacts", {}),
        "recorded_observations": manifest.get("observations", []),
        "limitations": manifest.get("limitations", []),
        "visual_mode": "expanded-battle-hd" if claims["geometry"]["passed"] else "unproven",
        "promotion_status": "validation_stage_only", "stable_stage_should_change": False,
        "evidence_class": evidence_class, "manual_input_claim_accepted": False,
        "manual_input_note": "No manual release approval is inferred from input mechanism or parser success.",
        "run_manifest": str(manifest_path) if manifest_path else None, "log": str(log_path),
        "log_sha256": log_sha, "claims": claims, "owner_visits": visits,
        "forced_markers": interventions, "forced_actions": forced_actions,
        "helper_measurements": helper_measurements(rows, not identity_errors, runtime_errors),
        "lifecycle_measurements": lifecycle_measurements(rows, not identity_errors, runtime_errors),
        "camera_measurements": camera_measurements(rows, not identity_errors, runtime_errors),
        "marker_counts": {name: sum(row["marker"] == name for row in rows) for name in sorted({row["marker"] for row in rows})},
        "failures": failures,
    }


def markdown(summary: dict[str, Any]) -> str:
    lines = ["# Battle HD Evidence", "", f"- Overall: {'PASS' if summary['passed'] else 'FAIL'}",
             f"- Stage: `{summary['stage']}`", f"- Candidate SHA: `{summary['candidate_sha256']}`",
             f"- Runtime candidate: `{summary['candidate']}`",
             f"- Byte-verification candidate: `{summary['patch_verification']['candidate']}` (same SHA-256)",
             f"- Resolution: `{summary['resolution']}`", f"- Evidence class: `{summary['evidence_class']}`",
             f"- Launch/input: `{summary['runtime_context']['launch_mode']}` / `{summary['runtime_context']['input_method']}`",
             f"- Wrapper: `{summary['runtime_context']['wrapper']}`",
             "- Promotion: `validation_stage_only`", "- Stable stage should change: `False`", "",
             "| Claim | Result |", "|---|---|"]
    lines.extend(f"| {name} | {'PASS' if check['passed'] else 'FAIL'} |" for name, check in summary["claims"].items())
    helper = summary["helper_measurements"]
    lines.extend(["", "## Direct helper diagnostics", "",
                  "These forced debugger calls cannot satisfy end-to-end input, rendering, modal, lifecycle, or visible acceptance.", "",
                  f"- Sequence completed: `{helper['sequence_completed']}`",
                  f"- Observed arena dimensions: `{helper['observed_arenas']}`", "",
                  "| Measurement | Result | Meaning |", "|---|---|---|"])
    lines.extend(f"| {name} | {'PASS' if check['passed'] else 'UNPROVEN'} | {check['note']} |"
                 for name, check in helper["checks"].items())
    camera = summary["camera_measurements"]
    if camera["observed_cases"]:
        lines.extend(["", "## Forced camera fixture", "", camera["note"], "",
                      f"- Original state restored: `{camera['original_state_restored']}`", "",
                      "| Case | Arena | Camera | Unit0 | Result |", "|---|---|---|---|---|"])
        lines.extend(f"| {row.get('case')} | {row.get('arena')} | {row.get('camera')} | {row.get('unit0')} | "
                     f"{'PASS' if camera['checks'].get(row.get('case'), {}).get('passed') else 'UNPROVEN'} |"
                     for row in camera["observed_cases"])
    lifecycle = summary["lifecycle_measurements"]
    if any(name.startswith("BATTLE_HD_LIFECYCLE_") for name in summary["marker_counts"]):
        lines.extend(["", "## Forced lifecycle diagnostics", "",
                      f"- Sequence completed: `{lifecycle['sequence_completed']}`",
                      f"- Observed banner-return mouse: `{lifecycle['observed_banner_return_mouse']}`",
                      f"- Observed modal-return mouse: `{lifecycle['observed_modal_return_mouse']}`", "",
                      "| Measurement | Result | Meaning |", "|---|---|---|"])
        lines.extend(f"| {name} | {'PASS' if check['passed'] else 'UNPROVEN'} | {check['note']} |"
                     for name, check in lifecycle["checks"].items())
    lines.extend(["", "## Missing or failing evidence", ""])
    lines.extend(f"- {item.get('observation')}" for item in summary["recorded_observations"] if isinstance(item, dict))
    lines.extend(f"- {item}" for item in summary["limitations"])
    lines.extend(f"- {item}" for item in summary["failures"] or ["None. Promotion remains a separate explicit decision."])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture_or_log", type=Path)
    parser.add_argument("--run-manifest", type=Path)
    parser.add_argument("--patch-stage-json", type=Path)
    parser.add_argument("--visible-proof", type=Path)
    parser.add_argument("--write-json", type=Path)
    parser.add_argument("--write-markdown", "--write-md", type=Path)
    parser.add_argument("--require-pass", action="store_true")
    args = parser.parse_args()
    summary = build_summary(args.capture_or_log, args.run_manifest, args.patch_stage_json, args.visible_proof)
    print(f"battle HD: {'PASS' if summary['passed'] else 'FAIL'}; {len(summary['failures'])} missing/failing claims; validation only")
    for path, content in ((args.write_json, json.dumps(summary, indent=2) + "\n"),
                          (args.write_markdown, markdown(summary))):
        if path:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
    return 2 if args.require_pass and not summary["passed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
