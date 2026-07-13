#!/usr/bin/env python3
"""Strict repo-only summary for the natural slot-2 record-1 owner/action proof.

The CDB probe injects coordinates and button state, but it must not mutate the
saved owner record, map scroll, command gate, modal exit, or control flow.  This
tool checks both the local probe source and one hidden-desktop surface-dump run.
It does not launch Clash95 or CDB.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
PROBE_NAME = "clash95_castle_cmd99_owner_action_slot2_record1_natural_extra.cdb"
DEFAULT_PROBE = REPO_ROOT / "probes" / "cdb" / "castle" / PROBE_NAME
EXPECTED_STAGE = (
    "gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-"
    "presentbounds-minimapright-dynvswitch-rightbottomcompose"
)
EXPECTED_INPUT_SHA256 = "500055D77D03D514E8D3168506BD10F67CD8569BCC450604FF8192F46CDAF3AE"
EXPECTED_CANDIDATE_SHA256 = "EFE643F0511A85946AD752CD7AB516207722FDC8409E4529C3CE40660EA84756"
PROOF_CLASS = "natural_saved_state_slot2_record1_right_bottom_compose"
INPUT_CLASS = (
    "debugger_forced_coordinates_and_selection_reset_natural_saved_state_engine_route"
)

ALLOWED_WRITES = {
    "005451c0": "eb",  # sampled left-button byte
    "00544d04": "ed",  # sampled click state
    "00544cfc": "ed",  # logical/raw mouse x
    "00544d00": "ed",  # logical/raw mouse y
    "00511b58": "ed",  # selected map object reset
    "00514194": "ed",  # prior selected map object reset
}

REQUIRED_SOURCE_MARKERS = (
    "RBNAT_SLOT2_TARGET",
    "RBNAT_MINIMAP_INPUT",
    "RBNAT_MINIMAP_RESULT",
    "NOWNER_FORCE_MAP_CASTLE_CLICK",
    "NOWNER_CASTLE_CMD99_GATE gate_before=%d forced_gate=0",
    "NOWNER_433C20_ENTRY",
    "NOWNER_RELEASE_OWNER_DESC_CLICK",
    "NOWNER_ACTION_CALL_STOCK",
    "NOWNER_OWNER_435BC0_ENTRY",
    "RBUI_PANEL_DRAW",
    "RBUI_GRID_DRAW",
    "RBUI_STATUS_DRAW",
    "RBUI_ACTION_BOX",
    "RBUI_DESC_SWITCH",
    "RBUI_VIEWPORT_SWITCH",
    "RBNAT_STATUS_COMPOSE_ENTER",
    "RBNAT_STATUS_COMPOSE_DONE",
    "RBNAT_ACTION_COMPOSE_ENTER",
    "RBNAT_ACTION_COMPOSE_DONE",
    "SURFDUMP_HOST_READY",
)

ORDERED_MARKERS = (
    "SURFDUMP_LOADSAVE",
    "SURFDUMP_PLAYGAME",
    "RBNAT_SLOT2_TARGET",
    "RBNAT_MINIMAP_INPUT",
    "RBNAT_MINIMAP_RESULT",
    "NOWNER_FORCE_MAP_CASTLE_CLICK",
    "NOWNER_MAP_TILE",
    "NOWNER_BUILDING_TILE",
    "NOWNER_CASTLE_OVERVIEW_ENTRY",
    "NOWNER_CASTLE_OVERVIEW_POST_DRAW",
    "NOWNER_CASTLE_HITMAP_SAMPLE",
    "NOWNER_CASTLE_CMD99_TARGET",
    "NOWNER_CASTLE_HIT",
    "NOWNER_CASTLE_DESCRIPTOR",
    "NOWNER_CASTLE_CMD99_GATE",
    "NOWNER_CASTLE_CALLBACK",
    "NOWNER_433C20_ENTRY",
    "NOWNER_OWNER_FLAG_TEST",
    "NOWNER_OWNER_SCREEN_DESC_DRAW",
    "NOWNER_FORCE_OWNER_DESC_CLICK",
    "NOWNER_DESCRIPTOR_CALLBACK",
    "NOWNER_4338E0_ENTRY",
    "NOWNER_RELEASE_OWNER_DESC_CLICK",
    "NOWNER_ACTION_CALL_STOCK",
    "NOWNER_OWNER_435BC0_ENTRY",
    "RBUI_PANEL_DRAW",
    "RBUI_GRID_DRAW",
    "RBUI_STATUS_DRAW",
    "RBNAT_STATUS_COMPOSE_ENTER",
    "RBNAT_STATUS_COMPOSE_DONE",
    "RBUI_ACTION_BOX",
    "RBNAT_ACTION_COMPOSE_ENTER",
    "RBNAT_ACTION_COMPOSE_DONE",
    "SURFDUMP_READY",
    "SURFDUMP_HOST_READY",
)

FORBIDDEN_RUNTIME = (
    "AV_SURFDUMP",
    "RBNAT_FAIL_",
    "NOWNER_4338E0_OWNER_FLAG_BLOCKED",
    "NOWNER_CASTLE_HIT_GIVEUP",
    "APPOST_OWNER_FLAG_FORCED",
    "OWNER_FLAG_FORCED",
    "forced_gate=1",
    "c0000005",
    "access violation",
)


def _norm_hex(value: str) -> str:
    return value.lower().removeprefix("0x").lstrip("0") or "0"


def _bool(value: Any) -> bool:
    return value is True


def _match(text: str, pattern: str) -> re.Match[str] | None:
    return re.search(pattern, text, re.IGNORECASE | re.MULTILINE)


def _matches(text: str, pattern: str) -> list[re.Match[str]]:
    return list(re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE))


def _ordered_positions(text: str) -> tuple[dict[str, int], list[str]]:
    positions: dict[str, int] = {}
    failures: list[str] = []
    cursor = 0
    for marker in ORDERED_MARKERS:
        pos = text.find(marker, cursor)
        positions[marker] = pos
        if pos < 0:
            failures.append(f"missing_ordered_marker:{marker}")
        else:
            cursor = pos + len(marker)
    return positions, failures


def guard_probe(path: Path) -> dict[str, Any]:
    failures: list[str] = []
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return {
            "passed": False,
            "path": str(path),
            "failures": [f"probe_read_error:{exc}"],
            "writes": [],
            "register_assignments": [],
        }

    missing = [marker for marker in REQUIRED_SOURCE_MARKERS if marker not in text]
    failures.extend(f"missing_source_marker:{marker}" for marker in missing)

    writes: list[dict[str, str]] = []
    for match in re.finditer(r"(?<![A-Za-z0-9_])(e[bwdq])\s+([^\s;]+)", text, re.IGNORECASE):
        opcode = match.group(1).lower()
        destination = match.group(2).lower()
        writes.append({"opcode": opcode, "destination": destination})
        expected_opcode = ALLOWED_WRITES.get(destination)
        if expected_opcode is None:
            failures.append(f"forbidden_memory_write:{opcode}:{destination}")
        elif opcode != expected_opcode:
            failures.append(
                f"wrong_memory_write_width:{destination}:expected={expected_opcode}:actual={opcode}"
            )

    register_assignments: list[str] = []
    for match in re.finditer(r"(?<![A-Za-z0-9_])r\s+([^=\s]+)\s*=", text, re.IGNORECASE):
        register = match.group(1).lower()
        register_assignments.append(register)
        if not re.fullmatch(r"@\$t(?:[0-9]|1[0-9])", register):
            failures.append(f"forbidden_register_assignment:{register}")

    lower = text.lower()
    banned_source_tokens = {
        "forced_gate=1": "command gate forcing marker",
        "owner_flag_forced": "owner flag forcing marker",
        "appost_owner_flag_forced": "post-owner flag forcing marker",
    }
    for token, reason in banned_source_tokens.items():
        if token in lower:
            failures.append(f"forbidden_source_token:{token}:{reason}")

    # The allowlist above is the authoritative mutation check.  These booleans
    # are explicit metadata so downstream gates cannot mistake coordinate
    # injection for a fully natural/manual input proof.
    return {
        "passed": not failures,
        "path": str(path.resolve()),
        "failures": failures,
        "writes": writes,
        "register_assignments": register_assignments,
        "owner_flag_forced": False,
        "scroll_forced": False,
        "command_gate_forced": False,
        "modal_exit_forced": False,
        "direct_route_forced": False,
        "debugger_forced_coordinates": True,
        "selection_reset_forced": True,
        "real_input_proven": False,
    }


def _check_exact_facts(text: str) -> tuple[dict[str, Any], list[str]]:
    facts: dict[str, Any] = {}
    failures: list[str] = []

    load_rows = _matches(
        text,
        r"SURFDUMP_LOADSAVE\s+selected_arg=(\d+)\s+selected_global=(\d+)\s+"
        r"accept=(\d+)\s+choice=(\d+)",
    )
    facts["loadsave_rows"] = len(load_rows)
    facts["loadsave_slot2"] = bool(load_rows) and all(
        tuple(int(value) for value in row.groups()) == (2, 2, 1, 5) for row in load_rows
    )
    if not facts["loadsave_slot2"]:
        failures.append("loadsave_not_consistently_slot2")

    play_rows = _matches(
        text,
        r"SURFDUMP_PLAYGAME\s+gd=([0-9a-f]+)\s+map=\((\d+),(\d+)\)\s+"
        r"scroll=\((-?\d+),(-?\d+)\)",
    )
    facts["playgame_rows"] = len(play_rows)
    facts["playgame_map_50x50"] = any(
        int(row.group(2)) == 50 and int(row.group(3)) == 50 for row in play_rows
    )
    if not facts["playgame_map_50x50"]:
        failures.append("playgame_map_not_50x50")

    target = _match(
        text,
        r"RBNAT_SLOT2_TARGET\s+gd=([0-9a-f]+)\s+record=1\s+record_ptr=([0-9a-f]+)\s+"
        r"pos=\((\d+),(\d+)\)\s+owner=(\d+)\s+mode=(\d+)\s+flags=0x([0-9a-f]+)\s+"
        r"flag_1a4=0x([0-9a-f]+)\s+tile=(\d+)\s+map=\((\d+),(\d+)\)\s+"
        r"player=(\d+)\s+minimap_active=(\d+)\s+surface=([0-9a-f]+)\s+size=\((\d+),(\d+)\)",
    )
    if target:
        facts["record_pointer"] = _norm_hex(target.group(2))
        facts["target"] = {
            "record": 1,
            "position": [int(target.group(3)), int(target.group(4))],
            "owner": int(target.group(5)),
            "mode": int(target.group(6)),
            "flags": int(target.group(7), 16),
            "flag_1a4": int(target.group(8), 16),
            "tile": int(target.group(9)),
            "map": [int(target.group(10)), int(target.group(11))],
            "player": int(target.group(12)),
            "minimap_active": int(target.group(13)),
            "surface_size": [int(target.group(15)), int(target.group(16))],
        }
        expected_target = {
            "position": [1, 23],
            "owner": 1,
            "mode": 2,
            "flags": 0x16,
            "flag_1a4": 0,
            "tile": 32769,
            "map": [50, 50],
            "surface_size": [800, 600],
        }
        if any(facts["target"][key] != value for key, value in expected_target.items()):
            failures.append("slot2_record1_target_fact_mismatch")
        if facts["target"]["minimap_active"] == 0:
            failures.append("slot2_minimap_inactive")
    else:
        failures.append("missing_or_malformed_slot2_target")

    minimap = _match(
        text,
        r"RBNAT_MINIMAP_INPUT\s+origin=\((-?\d+),(-?\d+)\)\s+scale=(\d+)\s+"
        r"target=\((-?\d+),(-?\d+)\)\s+expected_scroll=\(0,20\)",
    )
    if minimap:
        ox, oy, scale, tx, ty = (int(value) for value in minimap.groups())
        facts["minimap"] = {"origin": [ox, oy], "scale": scale, "target": [tx, ty]}
        if scale <= 0 or tx != ox + 7 or ty != oy + 7 + 20 * scale:
            failures.append("minimap_target_formula_mismatch")
    else:
        failures.append("missing_or_malformed_minimap_input")
    if not _match(text, r"RBNAT_MINIMAP_RESULT\s+scroll=\(0,20\)\s+target=\(0,20\)"):
        failures.append("minimap_result_not_scroll_0_20")

    exact_patterns = {
        "map_click_1_23": r"NOWNER_FORCE_MAP_CASTLE_CLICK\s+screen=\(96,224\)\s+expected_map=\(1,23\)",
        "map_tile_1_23": r"NOWNER_MAP_TILE\s+map=\(1,23\)",
        "building_record1": (
            r"NOWNER_BUILDING_TILE\s+map=\(1,23\)\s+tile=32769\s+index=1\s+"
            r"record_ptr=([0-9a-f]+)\s+owner=1\s+mode=2\s+active=\d+\s+flags=0x16"
        ),
        "castle_index1": r"NOWNER_CASTLE_OVERVIEW_ENTRY\b.*?castle_index=1\s+expected_index=1",
        "native_hitmap_fe": (
            r"NOWNER_CASTLE_HITMAP_SAMPLE\b.*?size=\(640,480\).*?native=\(151,306\)\s+"
            r"native_sample=0xfe\s+expected_raw=254"
        ),
        "cmd99_target": r"NOWNER_CASTLE_CMD99_TARGET\s+native=\(151,306\)",
        "raw_hit254": r"NOWNER_CASTLE_HIT\s+raw_hit=254\s+adjusted=6\s+expected_raw=254",
        "command99_callback": r"NOWNER_CASTLE_DESCRIPTOR\s+command=99\s+callback=0*433c20\b",
        "natural_gate": r"NOWNER_CASTLE_CMD99_GATE\s+gate_before=1\s+forced_gate=0",
        "owner_flag_bits": (
            r"NOWNER_OWNER_FLAG_TEST\s+owner=([0-9a-f]+)\s+owner_flag=0x16\s+"
            r"bit2=2\s+bit1=0\s+bit8=0"
        ),
        "owner_descriptor_d1": (
            r"NOWNER_OWNER_SCREEN_DESC_DRAW\b.*?d1=\(155,426\s+cb=0*4338e0\)"
        ),
        "owner_click": r"NOWNER_FORCE_OWNER_DESC_CLICK\s+native=\(180,440\)",
        "descriptor_callback": (
            r"NOWNER_DESCRIPTOR_CALLBACK\s+desc=0*514ff5\s+xy=\(155,426\).*?callback=0*4338e0"
        ),
        "click_release": (
            r"NOWNER_RELEASE_OWNER_DESC_CLICK\b.*?after_d544d04=0+\s+after_button0=0x00"
        ),
        "direct_stock_call": (
            r"NOWNER_ACTION_CALL_STOCK\s+target=0*435bc0\b.*?surface=([0-9a-f]+)\s+"
            r"size=\(800,600\)\s+nativecenter_wrapper=0"
        ),
        "stock_entry_800": (
            r"NOWNER_OWNER_435BC0_ENTRY\b.*?owner_arg=([0-9a-f]+).*?size=\(800,600\)\s+direct_stock=1"
        ),
        "status_compose_enter": (
            r"RBNAT_STATUS_COMPOSE_ENTER\s+hook=0*4352b3\s+cave=0*5132e0\s+"
            r"return=0*4352b8\b.*?size=\(800,600\)"
        ),
        "status_compose_done": r"RBNAT_STATUS_COMPOSE_DONE\b.*?size=\(800,600\)",
        "action_compose_enter": (
            r"RBNAT_ACTION_COMPOSE_ENTER\s+hook=0*435da5\s+cave=0*513e80\s+"
            r"return=0*435daa\b.*?size=\(800,600\)"
        ),
        "ready_800": (
            r"SURFDUMP_READY\s+redraw_seq=992\s+surface=([0-9a-f]+)\s+"
            r"size=\(800,600\)\s+base=([0-9a-f]+)\s+bytes=480000"
        ),
    }
    exact_matches: dict[str, re.Match[str] | None] = {
        name: _match(text, pattern) for name, pattern in exact_patterns.items()
    }
    facts["exact_checks"] = {name: match is not None for name, match in exact_matches.items()}
    failures.extend(f"exact_fact_failed:{name}" for name, match in exact_matches.items() if not match)

    record_pointer = facts.get("record_pointer")
    callback = _match(
        text,
        r"NOWNER_CASTLE_CALLBACK\s+callback=0*433c20\s+eax_arg=([0-9a-f]+)\s+command=99",
    )
    owner_entry = _match(
        text,
        r"NOWNER_433C20_ENTRY\b.*?owner_arg=([0-9a-f]+)\s+expected_owner=([0-9a-f]+)\s+"
        r"owner_flag=0x16\b.*?size=\(800,600\)",
    )
    if not callback:
        failures.append("missing_or_malformed_castle_callback")
    elif record_pointer and _norm_hex(callback.group(1)) != record_pointer:
        failures.append("castle_callback_owner_pointer_mismatch")
    if not owner_entry:
        failures.append("missing_or_malformed_owner_entry")
    elif record_pointer and any(_norm_hex(value) != record_pointer for value in owner_entry.groups()):
        failures.append("owner_entry_pointer_mismatch")

    compose_done = _match(
        text,
        r"RBNAT_ACTION_COMPOSE_DONE\b.*?size=\((\d+),(\d+)\)\s+base=([0-9a-f]+)\s+"
        r"bytes=(\d+)\s+status_state=(\d+)\s+action_state=(\d+)\s+panel_draws=(\d+)\s+"
        r"grid_draws=(\d+)\s+status_draws=(\d+)\s+action_draws=(\d+)\s+"
        r"desc_switches=(\d+)\s+viewport_switches=(\d+)",
    )
    if compose_done:
        values = [int(value) if index != 2 else value for index, value in enumerate(compose_done.groups())]
        facts["compose_done"] = {
            "size": values[0:2],
            "base": _norm_hex(str(values[2])),
            "bytes": values[3],
            "status_state": values[4],
            "action_state": values[5],
            "panel_draws": values[6],
            "grid_draws": values[7],
            "status_draws": values[8],
            "action_draws": values[9],
            "desc_switches": values[10],
            "viewport_switches": values[11],
        }
        final = facts["compose_done"]
        if (
            final["size"] != [800, 600]
            or final["bytes"] != 480000
            or final["status_state"] != 2
            or final["action_state"] != 2
            or any(final[name] <= 0 for name in (
                "panel_draws", "grid_draws", "status_draws", "action_draws",
                "desc_switches", "viewport_switches",
            ))
        ):
            failures.append("compose_done_counts_or_surface_mismatch")
    else:
        failures.append("missing_or_malformed_action_compose_done")

    marker_counts = {
        marker: len(re.findall(rf"\b{re.escape(marker)}\b", text))
        for marker in ("RBUI_DESC_SWITCH", "RBUI_VIEWPORT_SWITCH", "RBUI_PANEL_DRAW", "RBUI_ACTION_BOX")
    }
    facts["marker_counts"] = marker_counts
    if marker_counts["RBUI_DESC_SWITCH"] <= 0:
        failures.append("missing_rbui_desc_switch")
    if marker_counts["RBUI_VIEWPORT_SWITCH"] <= 0:
        failures.append("missing_rbui_viewport_switch")

    return facts, failures


def analyze_run(run_dir: Path, probe_path: Path = DEFAULT_PROBE) -> dict[str, Any]:
    run_dir = run_dir.resolve()
    summary_path = run_dir / "summary.json"
    log_path = run_dir / "cdb-surface-dump.log"
    failures: list[str] = []

    try:
        run_summary = json.loads(summary_path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        run_summary = {}
        failures.append(f"summary_read_error:{exc}")
    try:
        log_text = log_path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        log_text = ""
        failures.append(f"log_read_error:{exc}")

    source_guard = guard_probe(probe_path)
    failures.extend(f"source_guard:{failure}" for failure in source_guard["failures"])

    surface = run_summary.get("Surface") or {}
    extra_probe = Path(str(run_summary.get("ExtraProbeTemplate") or "")).name.lower()
    png_exists = (run_dir / "surface.png").is_file()
    profile_checks = {
        "summary_passed": _bool(run_summary.get("Passed")),
        "no_summary_error": run_summary.get("Error") in (None, ""),
        "not_timed_out": run_summary.get("TimedOut") is False,
        "hidden_launch_mode": str(run_summary.get("LaunchMode", "")).lower() == "hidden-desktop",
        "hidden_desktop": _bool(run_summary.get("HiddenDesktop")),
        "visible_fallback_disabled": run_summary.get("AllowVisibleDesktop") is False,
        "use_ddraw_proxy": _bool(run_summary.get("UseDdrawProxy")),
        "load_slot_2": run_summary.get("LoadSlot") == 2,
        "late_load_slot_forcing_only": _bool(run_summary.get("LateLoadSlotForcingOnly")),
        "fast_forward_start_anims": _bool(run_summary.get("FastForwardStartAnims")),
        "no_skip_start_anims_disabled": run_summary.get("NoSkipStartAnims") is False,
        "skip_map_validation": _bool(run_summary.get("SkipMapValidation")),
        "force_visible_edges_disabled": run_summary.get("ForceVisibleEdges") is False,
        "post_owner_force_visible_disabled": run_summary.get("PostOwnerForceVisibleSeven") is False,
        "exact_stage": run_summary.get("Stage") == EXPECTED_STAGE,
        "exact_input_sha": str(run_summary.get("InputSha256", "")).upper() == EXPECTED_INPUT_SHA256,
        "exact_candidate_sha": (
            str(run_summary.get("CandidateSha256", "")).upper() == EXPECTED_CANDIDATE_SHA256
        ),
        "exact_extra_probe": extra_probe == PROBE_NAME.lower(),
        "stopped_after_dump": _bool(run_summary.get("StoppedAfterDump")),
        "host_dumped_memory": _bool(run_summary.get("HostDumpedMemory")),
        "surface_800x600": surface.get("Width") == 800 and surface.get("Height") == 600,
        "surface_480000_bytes": surface.get("Bytes") == 480000 and run_summary.get("RawBytes") == 480000,
        "surface_png_exists": png_exists,
        "source_guard": source_guard["passed"],
    }
    failures.extend(f"profile_check_failed:{name}" for name, passed in profile_checks.items() if not passed)

    ordered_positions, order_failures = _ordered_positions(log_text)
    failures.extend(order_failures)
    runtime_forbidden_hits = [token for token in FORBIDDEN_RUNTIME if token.lower() in log_text.lower()]
    failures.extend(f"forbidden_runtime_marker:{token}" for token in runtime_forbidden_hits)

    facts, fact_failures = _check_exact_facts(log_text)
    failures.extend(fact_failures)
    failures = list(dict.fromkeys(failures))

    passed = not failures
    return {
        "schema_version": 1,
        "proof_class": PROOF_CLASS,
        "input_classification": INPUT_CLASS,
        "status": "pass" if passed else "fail",
        "passed": passed,
        "run_dir": str(run_dir),
        "summary_path": str(summary_path),
        "log_path": str(log_path),
        "probe_path": str(probe_path.resolve()),
        "expected": {
            "stage": EXPECTED_STAGE,
            "input_sha256": EXPECTED_INPUT_SHA256,
            "candidate_sha256": EXPECTED_CANDIDATE_SHA256,
            "load_slot": 2,
            "record": 1,
            "position": [1, 23],
            "owner": 1,
            "flags": "0x16",
        },
        "profile_checks": profile_checks,
        "source_guard": source_guard,
        "runtime_forbidden_hits": runtime_forbidden_hits,
        "ordered_marker_positions": ordered_positions,
        "facts": facts,
        "evidence_limits": {
            "natural_saved_state": True,
            "engine_minimap_scroll": True,
            "engine_command_gate": True,
            "owner_flag_forced": False,
            "scroll_forced": False,
            "command_gate_forced": False,
            "modal_exit_forced": False,
            "direct_route_forced": False,
            "debugger_forced_coordinates": True,
            "selection_reset_forced": True,
            "real_input_proven": False,
            "visible_runtime_proven": False,
            "stable_stage_promotion_proven": False,
        },
        "failures": failures,
    }


def render_markdown(report: dict[str, Any]) -> str:
    status = "PASS" if report["passed"] else "FAIL"
    lines = [
        "# Right-bottom natural slot-2 record-1 summary",
        "",
        f"- Overall: **{status}**",
        f"- Proof class: `{report['proof_class']}`",
        f"- Input classification: `{report['input_classification']}`",
        f"- Run: `{report['run_dir']}`",
        f"- Stage: `{report['expected']['stage']}`",
        "- Saved target: slot `2`, record `1`, position `(1,23)`, owner `1`, flags `0x16`",
        "- Runtime scope: hidden-desktop CDB/ddraw proxy; debugger-forced coordinates and selection reset",
        "- Not proven: real/manual input, visible runtime, or stable-stage promotion",
        "",
        "## Profile checks",
        "",
    ]
    lines.extend(
        f"- `{name}`: `{'PASS' if passed else 'FAIL'}`"
        for name, passed in report["profile_checks"].items()
    )
    lines.extend(["", "## Mutation guard", ""])
    for name in (
        "owner_flag_forced", "scroll_forced", "command_gate_forced",
        "modal_exit_forced", "direct_route_forced", "selection_reset_forced",
        "real_input_proven",
    ):
        lines.append(f"- `{name}`: `{report['evidence_limits'][name]}`")
    lines.extend(["", "## Failures", ""])
    if report["failures"]:
        lines.extend(f"- `{failure}`" for failure in report["failures"])
    else:
        lines.append("- None")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", type=Path, help="cdb-surface-dump run directory")
    parser.add_argument("--probe", type=Path, default=DEFAULT_PROBE)
    parser.add_argument("--write-json", type=Path)
    parser.add_argument("--write-markdown", "--write-md", dest="write_markdown", type=Path)
    parser.add_argument("--require-pass", action="store_true")
    args = parser.parse_args()

    report = analyze_run(args.run_dir, args.probe)
    if args.write_json:
        args.write_json.parent.mkdir(parents=True, exist_ok=True)
        args.write_json.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if args.write_markdown:
        args.write_markdown.parent.mkdir(parents=True, exist_ok=True)
        args.write_markdown.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 2 if args.require_pass and not report["passed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
