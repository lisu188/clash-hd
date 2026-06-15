#!/usr/bin/env python3
"""Classify natural right-bottom action-route save candidates.

This is a repo-only planner/guard for the current right-bottom action-menu
blocker. It combines local save metadata with archived hidden-desktop CDB logs
to prove which installed saves can plausibly drive the natural owner/action
lane, and which harness step is still blocking that proof.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_SAVE_SCAN_JSON = Path("captures/current/castle-save-owner-flag-scan-current.json")
DEFAULT_BASELINE_RUN = Path("captures/archive/cdb-surface-dump-20260518-213418")
DEFAULT_SLOT2_RUN = Path("captures/archive/cdb-surface-dump-20260523-001159")
DEFAULT_SLOT5_RUN = Path("captures/archive/cdb-surface-dump-20260523-000931")
DEFAULT_JSON = Path("captures/current/right-bottom-natural-route-candidate-matrix-current.json")
DEFAULT_MD = Path("captures/current/right-bottom-natural-route-candidate-matrix-current.md")
EXPECTED_STAGE = (
    "gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-"
    "minimapright-dynvswitch-rightbottomaction-nativecenter"
)
EXPECTED_PROBE = "probes/cdb/castle/clash95_castle_cmd99_owner_action_descriptor_extra.cdb"
RUNTIME_POLICY = (
    "repo/local metadata only; reads generated save-scan JSON and existing hidden-desktop "
    "CDB artifacts, and does not launch Clash95, CDB, wrappers, PowerShell, or visible windows"
)
GUARD_POLICY = (
    "passes only when current evidence shows an action-eligible installed save record exists, "
    "the archived slot-0 natural route clicks owner record index 0 but is blocked by owner flag "
    "0x00, slot 2 loads yet misses the bit-2 record with the current click, and slot 5 has a "
    "route-compatible bit-2 record but the current load harness times out before LOADSAVE"
)


MARKERS = (
    "SURFDUMP_LOADSAVE",
    "SURFDUMP_PLAYGAME",
    "NOWNER_MAP_TILE",
    "NOWNER_BUILDING_TILE",
    "NOWNER_CASTLE_OVERVIEW_ENTRY",
    "NOWNER_OWNER_FLAG_TEST",
    "NOWNER_4338E0_ENTRY",
    "NOWNER_ACTION_CALL_WRAPPER",
    "NOWNER_OWNER_435BC0_ENTRY",
    "NOWNER_WRAPPER_COPYBACK_DONE",
    "SURFDUMP_READY",
    "SURFDUMP_HOST_READY",
    "AV_SURFDUMP",
)
ACTION_ROUTE_MARKERS = (
    "NOWNER_4338E0_ENTRY",
    "NOWNER_ACTION_CALL_WRAPPER",
    "NOWNER_OWNER_435BC0_ENTRY",
    "NOWNER_WRAPPER_COPYBACK_DONE",
)

ROUTE_INJECT_RE = re.compile(r"route-injects load slot (?P<slot>\d+)")
LOADSAVE_RE = re.compile(
    r"SURFDUMP_LOADSAVE\b.*?\bselected_arg=(?P<selected_arg>-?\d+)\b.*?"
    r"\bselected_global=(?P<selected_global>-?\d+)\b.*?\baccept=(?P<accept>\d+)"
)
PLAYGAME_RE = re.compile(
    r"SURFDUMP_PLAYGAME\b.*?\bmap=\((?P<map_w>\d+),(?P<map_h>\d+)\)\s+"
    r"scroll=\((?P<scroll_x>-?\d+),(?P<scroll_y>-?\d+)\).*?"
    r"\bsize=\((?P<surface_w>\d+),(?P<surface_h>\d+)\)"
)
MAP_TILE_RE = re.compile(
    r"NOWNER_MAP_TILE\b.*?\bmap=\((?P<x>-?\d+),(?P<y>-?\d+)\).*?"
    r"\bmouse=\((?P<mouse_x>-?\d+),(?P<mouse_y>-?\d+)\).*?"
    r"\bselected=(?P<selected>-?\d+)\b.*?\bcurrent=(?P<current>-?\d+)"
)
BUILDING_TILE_RE = re.compile(
    r"NOWNER_BUILDING_TILE\b.*?\bmap=\((?P<x>-?\d+),(?P<y>-?\d+)\).*?"
    r"\btile=(?P<tile>\d+)\b.*?\bindex=(?P<index>-?\d+)\b.*?"
    r"\bowner=(?P<owner>-?\d+)\b.*?\bmode=(?P<mode>-?\d+)\b.*?"
    r"\bactive=(?P<active>-?\d+)\b.*?\bflags=(?P<flags>0x[0-9a-fA-F]+)"
)
FLAG_TEST_RE = re.compile(
    r"NOWNER_OWNER_FLAG_TEST\b.*?\bowner_flag=(?P<owner_flag>0x[0-9a-fA-F]+)\b.*?"
    r"\bbit2=(?P<bit2>\d+)\b.*?\bbit1=(?P<bit1>\d+)\b.*?\bbit8=(?P<bit8>\d+)"
)
SAVE_SLOT_RE = re.compile(r"(?P<slot>\d+)\.dat$", re.IGNORECASE)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def marker_counts(text: str) -> dict[str, int]:
    return {marker: text.count(marker) for marker in MARKERS}


def probe_template_matches(value: object, expected_rel: str) -> bool:
    normalized = str(value or "").replace("\\", "/").lower()
    expected = expected_rel.replace("\\", "/").lower()
    basename = expected.rsplit("/", 1)[-1]
    return expected in normalized or normalized.endswith("/" + basename) or normalized.endswith(basename)


def int_group(match: re.Match[str], name: str) -> int:
    return int(match.group(name))


def maybe_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def save_slot(save: str | None) -> int | None:
    if not save:
        return None
    match = SAVE_SLOT_RE.search(save.replace("\\", "/"))
    if not match:
        return None
    return int(match.group("slot"))


def record_summary(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if not row:
        return None
    return {
        "save": row.get("save"),
        "save_slot": save_slot(row.get("save")),
        "record_index": row.get("record_index"),
        "position": [row.get("x"), row.get("y")],
        "owner": row.get("owner"),
        "flags_1a0": row.get("flags_1a0"),
        "flags_1a0_hex": row.get("flags_1a0_hex"),
        "flags_1a4_hex": row.get("flags_1a4_hex"),
        "bit2": row.get("bit2"),
        "bit1": row.get("bit1"),
        "bit8": row.get("bit8"),
        "action_eligible": bool(row.get("action_eligible")),
    }


def save_records_by_slot(save_scan: dict[str, Any]) -> dict[int, list[dict[str, Any]]]:
    records: dict[int, list[dict[str, Any]]] = {}
    for block in save_scan.get("plausible_blocks") or []:
        slot = save_slot(block.get("save"))
        if slot is None:
            continue
        records.setdefault(slot, [])
        for row in block.get("active_records") or []:
            records[slot].append(row)
    return records


def all_action_records(save_scan: dict[str, Any]) -> list[dict[str, Any]]:
    rows = list(save_scan.get("records_with_bit2") or [])
    if rows:
        return rows
    for block in save_scan.get("plausible_blocks") or []:
        for row in block.get("records_with_bit2") or []:
            rows.append(row)
    return rows


def first_match(pattern: re.Pattern[str], text: str) -> dict[str, Any] | None:
    match = pattern.search(text)
    if not match:
        return None
    result: dict[str, Any] = {}
    for key, value in match.groupdict().items():
        if value is None:
            result[key] = None
        elif value.startswith("0x"):
            result[key] = value.lower()
        else:
            result[key] = int(value)
    return result


def all_matches(pattern: re.Pattern[str], text: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for match in pattern.finditer(text):
        row: dict[str, Any] = {}
        for key, value in match.groupdict().items():
            if value is None:
                row[key] = None
            elif value.startswith("0x"):
                row[key] = value.lower()
            else:
                row[key] = int(value)
        rows.append(row)
    return rows


def parse_run(run: Path) -> dict[str, Any]:
    summary_path = run / "summary.json"
    log_path = run / "cdb-surface-dump.log"
    failures: list[str] = []
    summary: dict[str, Any] = {}
    text = ""

    if not summary_path.exists():
        failures.append(f"missing summary: {summary_path}")
    else:
        summary = load_json(summary_path)
    if not log_path.exists():
        failures.append(f"missing log: {log_path}")
    else:
        text = log_path.read_text(encoding="utf-8", errors="replace")

    counts = marker_counts(text)
    route_inject = first_match(ROUTE_INJECT_RE, text)
    loadsave = first_match(LOADSAVE_RE, text)
    playgame = first_match(PLAYGAME_RE, text)
    map_tiles = all_matches(MAP_TILE_RE, text)
    building_tiles = all_matches(BUILDING_TILE_RE, text)
    flag_test = first_match(FLAG_TEST_RE, text)
    slot = maybe_int(summary.get("LoadSlot"))
    if slot is None and route_inject:
        slot = maybe_int(route_inject.get("slot"))

    action_route_count = sum(int(counts.get(marker) or 0) for marker in ACTION_ROUTE_MARKERS)
    hidden = summary.get("HiddenDesktop") is True
    stage_ok = summary.get("Stage") == EXPECTED_STAGE
    probe_ok = probe_template_matches(summary.get("ExtraProbeTemplate"), EXPECTED_PROBE)
    no_av = summary.get("Av") is not True and int(counts.get("AV_SURFDUMP") or 0) == 0

    return {
        "run": str(run),
        "summary_json": str(summary_path),
        "log": str(log_path),
        "summary_exists": summary_path.exists(),
        "log_exists": log_path.exists(),
        "passed": summary.get("Passed") is True,
        "timed_out": summary.get("TimedOut") is True,
        "hidden_desktop": hidden,
        "use_ddraw_proxy": summary.get("UseDdrawProxy") is True,
        "stage": summary.get("Stage"),
        "stage_ok": stage_ok,
        "probe_ok": probe_ok,
        "candidate_sha256": summary.get("CandidateSha256"),
        "load_slot": slot,
        "route_injected_load_slot": route_inject.get("slot") if route_inject else None,
        "loadsave": loadsave,
        "load_succeeded": bool(loadsave and playgame),
        "playgame": playgame,
        "map_tiles": map_tiles[:8],
        "map_tile_count": len(map_tiles),
        "building_tiles": building_tiles,
        "building_tile": building_tiles[0] if building_tiles else None,
        "map_click_hits_building": bool(building_tiles),
        "castle_overview_reached": int(counts.get("NOWNER_CASTLE_OVERVIEW_ENTRY") or 0) > 0,
        "flag_test": flag_test,
        "owner_flag_zero_blocker": bool(
            flag_test
            and flag_test.get("owner_flag") == "0x00"
            and int(flag_test.get("bit2") or 0) == 0
            and int(flag_test.get("bit1") or 0) == 0
            and int(flag_test.get("bit8") or 0) == 0
        ),
        "action_route_count": action_route_count,
        "marker_counts": counts,
        "no_av": no_av,
        "screenshot": summary.get("PngPath"),
        "failures": failures,
    }


def records_for_slot(records_by_slot: dict[int, list[dict[str, Any]]], slot: int) -> list[dict[str, Any]]:
    return list(records_by_slot.get(slot) or [])


def first_action_record_for_slot(
    records_by_slot: dict[int, list[dict[str, Any]]],
    slot: int,
) -> dict[str, Any] | None:
    for row in records_for_slot(records_by_slot, slot):
        if row.get("action_eligible"):
            return row
    return None


def route_compatible_records(
    action_records: list[dict[str, Any]],
    route_index: int | None,
) -> list[dict[str, Any]]:
    if route_index is None:
        return []
    return [
        row
        for row in action_records
        if maybe_int(row.get("record_index")) == route_index
    ]


def classify_slot2(slot2: dict[str, Any], records_by_slot: dict[int, list[dict[str, Any]]]) -> dict[str, Any]:
    action_record = first_action_record_for_slot(records_by_slot, 2)
    status = "unknown"
    if slot2.get("load_succeeded") and not slot2.get("map_click_hits_building"):
        status = "loads_but_click_misses_castle"
    elif slot2.get("map_click_hits_building"):
        status = "click_hits_castle"
    elif slot2.get("timed_out"):
        status = "timeout"
    return {
        "status": status,
        "load_succeeded": slot2.get("load_succeeded"),
        "map_click_hits_building": slot2.get("map_click_hits_building"),
        "castle_overview_reached": slot2.get("castle_overview_reached"),
        "first_map_tile": (slot2.get("map_tiles") or [None])[0],
        "action_record": record_summary(action_record),
    }


def classify_slot5(slot5: dict[str, Any], route_candidate: dict[str, Any] | None) -> dict[str, Any]:
    status = "unknown"
    if slot5.get("timed_out") and not slot5.get("loadsave"):
        status = "timeout_before_loadsave"
    elif slot5.get("load_succeeded"):
        status = "loaded_needs_new_action_probe"
    return {
        "status": status,
        "timed_out": slot5.get("timed_out"),
        "load_succeeded": slot5.get("load_succeeded"),
        "loadsave": slot5.get("loadsave"),
        "route_compatible_candidate": record_summary(route_candidate),
    }


def build_report(
    save_scan_json: Path = DEFAULT_SAVE_SCAN_JSON,
    baseline_run: Path = DEFAULT_BASELINE_RUN,
    slot2_run: Path = DEFAULT_SLOT2_RUN,
    slot5_run: Path = DEFAULT_SLOT5_RUN,
) -> dict[str, Any]:
    failures: list[str] = []
    save_scan: dict[str, Any] = {}
    if not save_scan_json.exists():
        failures.append(f"missing save scan JSON: {save_scan_json}")
    else:
        save_scan = load_json(save_scan_json)

    baseline = parse_run(baseline_run)
    slot2 = parse_run(slot2_run)
    slot5 = parse_run(slot5_run)
    for label, run in (("baseline", baseline), ("slot2", slot2), ("slot5", slot5)):
        failures.extend(f"{label}: {failure}" for failure in run.get("failures") or [])

    records_by_slot = save_records_by_slot(save_scan)
    action_records = all_action_records(save_scan)
    baseline_tile = baseline.get("building_tile") or {}
    route_index = maybe_int(baseline_tile.get("index"))
    compatible = route_compatible_records(action_records, route_index)
    route_candidate = next(
        (row for row in compatible if save_slot(row.get("save")) == 5),
        compatible[0] if compatible else None,
    )
    slot2_status = classify_slot2(slot2, records_by_slot)
    slot5_status = classify_slot5(slot5, route_candidate)

    if save_scan and save_scan.get("passed") is not True:
        failures.append("save scan did not pass")
    if not action_records:
        failures.append("save scan has no action-eligible bit-2 owner records")
    if not baseline.get("passed"):
        failures.append("baseline natural route run did not pass")
    if baseline.get("hidden_desktop") is not True:
        failures.append("baseline natural route run was not hidden-desktop")
    if baseline.get("use_ddraw_proxy") is not True:
        failures.append("baseline natural route run did not use DirectDraw proxy")
    if baseline.get("stage_ok") is not True:
        failures.append(f"baseline stage mismatch: {baseline.get('stage')}")
    if baseline.get("probe_ok") is not True:
        failures.append("baseline natural route run used an unexpected probe")
    if baseline.get("no_av") is not True:
        failures.append("baseline natural route run has AV evidence")
    if baseline.get("load_slot") != 0:
        failures.append(f"baseline load slot was {baseline.get('load_slot')}, expected 0")
    if baseline.get("load_succeeded") is not True:
        failures.append("baseline did not reach LOADSAVE and PLAYGAME")
    if baseline.get("map_click_hits_building") is not True:
        failures.append("baseline map click did not hit a building tile")
    if baseline.get("castle_overview_reached") is not True:
        failures.append("baseline did not reach castle overview")
    if baseline.get("owner_flag_zero_blocker") is not True:
        failures.append("baseline did not prove owner_flag 0x00 bit blocker")
    if route_index is None:
        failures.append("baseline did not expose a route building record index")
    if not route_candidate:
        failures.append(f"no action-eligible save record matches route record index {route_index}")
    elif save_slot(route_candidate.get("save")) != 5:
        failures.append(f"route-compatible action record is not in save slot 5: {route_candidate.get('save')}")

    if slot2.get("hidden_desktop") is not True:
        failures.append("slot2 exploratory run was not hidden-desktop")
    if slot2.get("stage_ok") is not True:
        failures.append(f"slot2 stage mismatch: {slot2.get('stage')}")
    if slot2.get("no_av") is not True:
        failures.append("slot2 exploratory run has AV evidence")
    if slot2.get("load_slot") != 2:
        failures.append(f"slot2 exploratory run load slot was {slot2.get('load_slot')}, expected 2")
    if slot2.get("load_succeeded") is not True:
        failures.append("slot2 exploratory run did not prove alternate-slot LOADSAVE and PLAYGAME")
    if slot2_status["status"] != "loads_but_click_misses_castle":
        failures.append(f"slot2 exploratory status was {slot2_status['status']}, expected loads_but_click_misses_castle")
    slot2_record = slot2_status.get("action_record") or {}
    if slot2_record.get("record_index") == route_index:
        failures.append("slot2 action record unexpectedly matches the baseline route index")

    if slot5.get("hidden_desktop") is not True:
        failures.append("slot5 exploratory run was not hidden-desktop")
    if slot5.get("stage_ok") is not True:
        failures.append(f"slot5 stage mismatch: {slot5.get('stage')}")
    if slot5.get("no_av") is not True:
        failures.append("slot5 exploratory run has AV evidence")
    if slot5.get("load_slot") != 5:
        failures.append(f"slot5 exploratory run load slot was {slot5.get('load_slot')}, expected 5")
    if slot5_status["status"] != "timeout_before_loadsave":
        failures.append(f"slot5 exploratory status was {slot5_status['status']}, expected timeout_before_loadsave")

    passed = not failures
    blocker = (
        "route-compatible save slot 5 has owner flag bit 0x02 at record index 0, "
        "but the hidden CDB load-slot route currently times out before LOADSAVE; "
        "slot 2 confirms alternate-slot loading works but the current map click misses its bit-2 castle"
    )
    next_steps = [
        "fix the hidden CDB load-slot selection path for slot 5 and rerun the natural owner/action probe",
        "or build an isolated working-directory fixture that maps the slot-5 save state to a route-compatible slot without mutating C:\\Clash\\save",
        "or retarget the CDB map click/scroll path to the slot-2 bit-2 castle at record index 1",
    ]

    return {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "passed": passed,
        "runtime_policy": RUNTIME_POLICY,
        "guard_policy": GUARD_POLICY,
        "promotion_ready": False,
        "save_scan_json": str(save_scan_json),
        "baseline_run": str(baseline_run),
        "slot2_run": str(slot2_run),
        "slot5_run": str(slot5_run),
        "screenshot": slot2.get("screenshot") or baseline.get("screenshot"),
        "summary": {
            "save_scan_passed": save_scan.get("passed"),
            "action_eligible_record_count": len(action_records),
            "baseline_route_index": route_index,
            "baseline_owner_flag_zero_blocker": baseline.get("owner_flag_zero_blocker"),
            "route_compatible_candidate": record_summary(route_candidate),
            "slot2_status": slot2_status,
            "slot5_status": slot5_status,
            "current_blocker": blocker,
            "next_proof_options": next_steps,
        },
        "baseline": baseline,
        "slot2": slot2,
        "slot5": slot5,
        "route_compatible_records": [record_summary(row) for row in compatible],
        "failures": failures,
    }


def status_text(passed: bool) -> str:
    return "PASS" if passed else "FAIL"


def write_markdown(path: Path, report: dict[str, Any]) -> None:
    summary = report["summary"]
    route_candidate = summary.get("route_compatible_candidate") or {}
    slot2 = summary.get("slot2_status") or {}
    slot5 = summary.get("slot5_status") or {}
    lines = [
        "# Right-Bottom Natural Route Candidate Matrix",
        "",
        f"- Status: {status_text(bool(report.get('passed')))}",
        f"- Generated: `{report['generated_at']}`",
        f"- Runtime policy: {report['runtime_policy']}",
        f"- Guard policy: {report['guard_policy']}",
        f"- Promotion ready: `{report['promotion_ready']}`",
        f"- Save scan: `{report['save_scan_json']}`",
        f"- Baseline run: `{report['baseline_run']}`",
        f"- Slot 2 run: `{report['slot2_run']}`",
        f"- Slot 5 run: `{report['slot5_run']}`",
        "",
        "## Classification",
        "",
        f"- Action-eligible owner records: `{summary.get('action_eligible_record_count')}`",
        f"- Baseline route record index: `{summary.get('baseline_route_index')}`",
        f"- Baseline owner-flag blocker: `{summary.get('baseline_owner_flag_zero_blocker')}`",
        f"- Route-compatible candidate: save slot `{route_candidate.get('save_slot')}`, record `{route_candidate.get('record_index')}`, position `{route_candidate.get('position')}`, flags `{route_candidate.get('flags_1a0_hex')}`",
        f"- Slot 2 exploratory status: `{slot2.get('status')}`",
        f"- Slot 2 first map tile: `{slot2.get('first_map_tile')}`",
        f"- Slot 2 action record: `{slot2.get('action_record')}`",
        f"- Slot 5 exploratory status: `{slot5.get('status')}`",
        f"- Current blocker: {summary.get('current_blocker')}",
        "",
        "## Next Proof Options",
        "",
    ]
    lines.extend(f"- {step}" for step in summary.get("next_proof_options") or [])
    if report.get("screenshot"):
        lines.extend(["", f"![slot2 hidden route surface]({report['screenshot']})"])
    if report.get("failures"):
        lines.extend(["", "## Failures", ""])
        lines.extend(f"- {failure}" for failure in report["failures"])
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--save-scan-json", type=Path, default=DEFAULT_SAVE_SCAN_JSON)
    parser.add_argument("--baseline-run", type=Path, default=DEFAULT_BASELINE_RUN)
    parser.add_argument("--slot2-run", type=Path, default=DEFAULT_SLOT2_RUN)
    parser.add_argument("--slot5-run", type=Path, default=DEFAULT_SLOT5_RUN)
    parser.add_argument("--write-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--write-markdown", type=Path, default=DEFAULT_MD)
    parser.add_argument("--require-pass", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        save_scan_json=args.save_scan_json,
        baseline_run=args.baseline_run,
        slot2_run=args.slot2_run,
        slot5_run=args.slot5_run,
    )
    print(f"overall: {status_text(bool(report['passed']))}")
    print(f"runtime-policy: {report['runtime_policy']}")
    print(f"promotion-ready: {report['promotion_ready']}")
    print(f"route-compatible-candidate: {report['summary'].get('route_compatible_candidate')}")
    print(f"slot2-status: {report['summary'].get('slot2_status', {}).get('status')}")
    print(f"slot5-status: {report['summary'].get('slot5_status', {}).get('status')}")
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
