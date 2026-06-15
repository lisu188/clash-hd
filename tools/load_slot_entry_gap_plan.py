#!/usr/bin/env python3
"""Classify the current load-slot entry gap from static and archived evidence.

This is repo-only evidence. It reads the decompiled source export, the current
CDB surface-dump probe script, and the generated load-slot timeout phase report.
It does not launch Clash95, CDB, wrappers, PowerShell, or visible windows.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_DECOMP_C = Path(r"C:\Clash\clash95.c")
DEFAULT_CDB_PROBE = Path("probes/cdb/render/clash95_surface_dump_probe.cdb")
DEFAULT_TIMEOUT_PHASE_JSON = Path("captures/current/load-slot-timeout-phase-current.json")
DEFAULT_JSON = Path("captures/current/load-slot-entry-gap-current.json")
DEFAULT_MD = Path("captures/current/load-slot-entry-gap-current.md")

RUNTIME_POLICY = (
    "repo-only; reads decompilation text, CDB probe text, and generated timeout "
    "phase JSON; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows"
)
GUARD_POLICY = (
    "passes only when static code still places the real load-row loop after the "
    "main Load callback, the current probe spans both sides of that transition, "
    "slot 2 reaches the post-entry accept path, and slots 3-5 still stop before "
    "0044895A load-menu entry"
)

DECOMP_MARKERS = {
    "case5_load_menu_entry": "case 5:",
    "selected_reset_before_load_menu": "dword_5441E0 = -1;",
    "draws_ten_rows_after_entry": "for ( k = 0; k < 10; sub_44A140(k, (DWORD)a3) )",
    "copies_load_descriptors": "qmemcpy(v123, &unk_518808, 0x9Fu);",
    "initializes_load_descriptors": "sub_419D80(v123);",
    "resets_exit_flag_after_descriptor_init": "dword_543D78 = 0;",
    "load_loop_after_present": "while ( !dword_543D78 )",
    "load_row_x_bounds": "dword_544CFC >> byte_54512C >= 244 && dword_544CFC >> byte_54512C <= 410",
    "load_row_formula": "v108 = ((dword_544D00 >> byte_54512C) - 155) / 22;",
    "load_row_limit": "if ( v108 <= 9 )",
    "selected_row_write": "dword_5441E0 = ((dword_544D00 >> byte_54512C) - 155) / 22;",
    "click_accept_helper": "if ( sub_460950((int)dword_544CD8) )",
    "accept_helper_call": "sub_44A110(0, (DWORD)a3);",
    "accept_file_check": "result = sub_444750(dword_5441E0, a2);",
    "accept_sets_success_flag": "dword_544190 = 1;",
    "accept_exits_load_loop": "dword_543D78 = 1;",
    "loadsave_after_accept": "sub_444490(a2, (DWORD)a3, a4);",
    "playgame_after_accept": "PlayGame(v109, a2, (DWORD)a3, 1, a4);",
}

CDB_MARKERS = {
    "early_descriptor_breakpoint": "bp 00419B80",
    "pre_entry_load_coord_log": "SURFDUMP_LOAD_COORD",
    "main_load_callback_skip": "bp 00447780",
    "main_load_callback_log": "SURFDUMP_SKIP_MAIN_LOAD_CALLBACK",
    "main_dispatch_poll": "bp 00447D61",
    "load_menu_entry_breakpoint": "bp 0044895A",
    "load_menu_entry_log": "SURFDUMP_LOAD_MENU_ENTRY",
    "load_menu_loop_breakpoint": "bp 00448A45",
    "force_load_select_breakpoint": "bp 00448A68",
    "force_load_accept_breakpoint": "bp 00448AE3",
    "load_accept_helper_breakpoint": "bp 0044A110",
    "loadsave_breakpoint": "bp 00444490",
    "playgame_breakpoint": "bp 0040B660",
}

BLOCKED_STATUS = "stalled_after_load_button_before_load_menu_loop"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig", errors="replace")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def status_text(passed: bool) -> str:
    return "PASS" if passed else "FAIL"


def check_text_markers(path: Path, markers: dict[str, str]) -> dict[str, Any]:
    failures: list[str] = []
    text = ""
    if not path.exists():
        failures.append(f"missing text file: {path}")
    else:
        text = read_text(path)
    marker_results = {name: marker in text for name, marker in markers.items()}
    for name, present in marker_results.items():
        if not present:
            failures.append(f"missing marker {name}: {markers[name]}")
    return {
        "path": str(path),
        "exists": path.exists(),
        "passed": not failures,
        "markers": marker_results,
        "failures": failures,
    }


def phase_value(phase: dict[str, Any], key: str) -> int:
    value = phase.get(key)
    if value is None:
        return 0
    return int(value)


def check_phase_report(path: Path) -> dict[str, Any]:
    failures: list[str] = []
    report: dict[str, Any] = {}
    if not path.exists():
        failures.append(f"missing timeout phase JSON: {path}")
    else:
        report = load_json(path)

    phases = report.get("phases") or {}
    if report and report.get("passed") is not True:
        failures.append("timeout phase report is not passing")

    slot2 = phases.get("slot2_success") or {}
    if slot2.get("status") != "load_menu_accept_success":
        failures.append(f"slot2 status is {slot2.get('status')}, expected load_menu_accept_success")
    for marker_key in (
        "load_menu_entry_count",
        "load_menu_loop_count",
        "force_select_count",
        "loadsave_count",
        "playgame_count",
    ):
        if phase_value(slot2, marker_key) <= 0:
            failures.append(f"slot2 missing post-entry marker count: {marker_key}")

    blocked_rows: dict[str, Any] = {}
    for label, slot in (
        ("slot3_timeout", 3),
        ("slot4_timeout", 4),
        ("slot5_timeout", 5),
        ("recent_slot5_timeout", 5),
    ):
        phase = phases.get(label) or {}
        row_failures: list[str] = []
        if phase.get("status") != BLOCKED_STATUS:
            row_failures.append(f"status is {phase.get('status')}, expected {BLOCKED_STATUS}")
        if phase.get("load_slot") != slot:
            row_failures.append(f"load slot is {phase.get('load_slot')}, expected {slot}")
        if phase_value(phase, "load_coord_count") <= 0:
            row_failures.append("missing early load-coordinate rows")
        for count_key in (
            "load_menu_entry_count",
            "load_menu_loop_count",
            "force_select_count",
            "loadsave_count",
            "playgame_count",
        ):
            if phase_value(phase, count_key) != 0:
                row_failures.append(f"{count_key} is {phase.get(count_key)}, expected 0")
        blocked_rows[label] = {
            "slot": slot,
            "status": phase.get("status"),
            "load_coord_count": phase.get("load_coord_count"),
            "last_load_coord": phase.get("last_load_coord"),
            "last_marker": phase.get("last_marker"),
            "timeout_stack_category": phase.get("timeout_stack_category"),
            "passed": not row_failures,
            "failures": row_failures,
        }
        failures.extend(f"{label}: {failure}" for failure in row_failures)

    return {
        "path": str(path),
        "exists": path.exists(),
        "passed": not failures,
        "slot2": {
            "status": slot2.get("status"),
            "run": slot2.get("run"),
            "load_coord_count": slot2.get("load_coord_count"),
            "load_menu_entry_count": slot2.get("load_menu_entry_count"),
            "load_menu_loop_count": slot2.get("load_menu_loop_count"),
            "force_select_count": slot2.get("force_select_count"),
            "loadsave_count": slot2.get("loadsave_count"),
            "playgame_count": slot2.get("playgame_count"),
        },
        "blocked_rows": blocked_rows,
        "screenshot": report.get("screenshot"),
        "summary": report.get("summary") or {},
        "failures": failures,
    }


def build_report(
    decomp_c: Path = DEFAULT_DECOMP_C,
    cdb_probe: Path = DEFAULT_CDB_PROBE,
    timeout_phase_json: Path = DEFAULT_TIMEOUT_PHASE_JSON,
) -> dict[str, Any]:
    failures: list[str] = []
    static_decomp = check_text_markers(decomp_c, DECOMP_MARKERS)
    cdb_probe_check = check_text_markers(cdb_probe, CDB_MARKERS)
    timeout_phase = check_phase_report(timeout_phase_json)

    failures.extend(f"decomp: {failure}" for failure in static_decomp["failures"])
    failures.extend(f"cdb_probe: {failure}" for failure in cdb_probe_check["failures"])
    failures.extend(f"timeout_phase: {failure}" for failure in timeout_phase["failures"])

    next_probe_targets = [
        "add a CDB transition row between 00447780 and 0044895A to prove when case 5 is dispatched",
        "late-arm row forcing only after 0044895A instead of relying on early 00419B80 descriptor hits",
        "log dword_543D7C and dword_543D78 immediately before and after the main dispatch consumes the load callback",
    ]
    current_gap = (
        "Rows 3-5 are stopped in the transition after the forced main Load callback "
        "and before 0044895A load-menu entry. They are not yet evidence of invalid "
        "save rows because 0044A110/sub_444750, LOADSAVE, and PlayGame are never reached."
    )

    return {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "passed": not failures,
        "runtime_policy": RUNTIME_POLICY,
        "guard_policy": GUARD_POLICY,
        "promotion_ready": False,
        "gap_classification": "after_main_load_callback_before_load_menu_case_entry",
        "static_decomp": static_decomp,
        "cdb_probe": cdb_probe_check,
        "timeout_phase": timeout_phase,
        "summary": {
            "current_gap": current_gap,
            "slot2_post_entry_success": timeout_phase.get("slot2", {}).get("status")
            == "load_menu_accept_success",
            "blocked_rows": [3, 4, 5],
            "recent_slot5_same_gap": (
                (timeout_phase.get("blocked_rows") or {})
                .get("recent_slot5_timeout", {})
                .get("passed")
                is True
            ),
            "next_probe_targets": next_probe_targets,
            "next_non_promoting_route_option": (
                "use an isolated slot fixture or direct-loader probe only if it is labeled "
                "non-natural route evidence until the menu transition is proven"
            ),
        },
        "screenshot": timeout_phase.get("screenshot"),
        "failures": failures,
    }


def write_markdown(path: Path, report: dict[str, Any]) -> None:
    summary = report["summary"]
    lines = [
        "# Load Slot Entry Gap",
        "",
        f"- Status: {status_text(bool(report.get('passed')))}",
        f"- Generated: `{report['generated_at']}`",
        f"- Runtime policy: {report['runtime_policy']}",
        f"- Guard policy: {report['guard_policy']}",
        f"- Promotion ready: `{report['promotion_ready']}`",
        f"- Gap classification: `{report['gap_classification']}`",
        f"- Slot 2 post-entry success: `{summary.get('slot2_post_entry_success')}`",
        f"- Blocked rows: `{summary.get('blocked_rows')}`",
        f"- Recent slot-5 same gap: `{summary.get('recent_slot5_same_gap')}`",
        "",
        "## Current Gap",
        "",
        summary.get("current_gap") or "",
        "",
        "## Static And Probe Coverage",
        "",
        f"- Static decomp markers: `{status_text(bool(report['static_decomp'].get('passed')))}`",
        f"- CDB probe markers: `{status_text(bool(report['cdb_probe'].get('passed')))}`",
        f"- Timeout phase report: `{status_text(bool(report['timeout_phase'].get('passed')))}`",
        "",
        "## Blocked Rows",
        "",
        "| Label | Slot | Status | Load coords | Last marker | Stack category |",
        "| --- | ---: | --- | ---: | --- | --- |",
    ]
    for label, row in (report["timeout_phase"].get("blocked_rows") or {}).items():
        lines.append(
            "| {label} | {slot} | `{status}` | {coords} | `{marker}` | `{stack}` |".format(
                label=label,
                slot=row.get("slot"),
                status=row.get("status"),
                coords=row.get("load_coord_count"),
                marker=row.get("last_marker"),
                stack=row.get("timeout_stack_category"),
            )
        )
    lines.extend(["", "## Next Probe Targets", ""])
    lines.extend(f"- {target}" for target in summary.get("next_probe_targets") or [])
    lines.extend(["", "## Non-Promoting Route Option", ""])
    lines.append(summary.get("next_non_promoting_route_option") or "")
    if report.get("screenshot"):
        lines.extend(["", f"![slot2 load route surface]({report['screenshot']})"])
    if report.get("failures"):
        lines.extend(["", "## Failures", ""])
        lines.extend(f"- {failure}" for failure in report["failures"])
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--decomp-c", type=Path, default=DEFAULT_DECOMP_C)
    parser.add_argument("--cdb-probe", type=Path, default=DEFAULT_CDB_PROBE)
    parser.add_argument("--timeout-phase-json", type=Path, default=DEFAULT_TIMEOUT_PHASE_JSON)
    parser.add_argument("--write-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--write-markdown", type=Path, default=DEFAULT_MD)
    parser.add_argument("--require-pass", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = build_report(
        decomp_c=args.decomp_c,
        cdb_probe=args.cdb_probe,
        timeout_phase_json=args.timeout_phase_json,
    )
    print(f"overall: {status_text(bool(report['passed']))}")
    print(f"runtime-policy: {report['runtime_policy']}")
    print(f"gap-classification: {report['gap_classification']}")
    print(f"promotion-ready: {report['promotion_ready']}")
    for label, row in (report["timeout_phase"].get("blocked_rows") or {}).items():
        print(f"{label}: {status_text(bool(row.get('passed')))} {row.get('status')}")
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
