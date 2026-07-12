#!/usr/bin/env python3
"""Guard the current load-slot route boundary from static and CDB evidence.

This is a repo-only classifier for the menu load route. It reads the decompiled
source export, the current surface-dump harness script, and archived
hidden-desktop CDB artifacts. It does not launch Clash95, CDB, wrappers,
PowerShell, or visible windows.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_DECOMP_C = Path(r"C:\Clash\clash95.c")
DEFAULT_SURFACE_PROBE_SCRIPT = Path("scripts/cdb/run_cdb_surface_dump.ps1")
DEFAULT_SLOT2_RUN = Path("captures/archive/cdb-surface-dump-20260712-153805")
DEFAULT_SLOT3_RUN = Path("captures/archive/cdb-surface-dump-20260712-153827")
DEFAULT_SLOT4_RUN = Path("captures/archive/cdb-surface-dump-20260712-154103")
DEFAULT_SLOT5_RUN = Path("captures/archive/cdb-surface-dump-20260712-154340")
DEFAULT_RECENT_SLOT5_RUN = Path("captures/archive/cdb-surface-dump-20260712-153529")
DEFAULT_JSON = Path("captures/current/load-slot-route-limit-current.json")
DEFAULT_MD = Path("captures/current/load-slot-route-limit-current.md")

RUNTIME_POLICY = (
    "repo-only; reads decompilation text, harness text, and existing hidden-desktop "
    "CDB artifacts; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows"
)
GUARD_POLICY = (
    "passes only when static evidence still shows a ten-row local load menu and "
    "integer save-file checks, the current harness still computes row clicks from "
    "166 + 22 * LoadSlot, archived slot 2 reaches LOADSAVE/PlayGame, and archived "
    "slots 3-5 plus the current slot-5 right-bottom attempt all time out before "
    "force-select, force-accept, LOADSAVE, and PlayGame"
)

DECOMP_MARKERS = {
    "save_formatter": 'return sprintf_(a2, "save\\\\%d.dat", a1);',
    "load_accept_file_check": "result = sub_444750(dword_5441E0, a2);",
    "load_accept_sets_flag": "dword_544190 = 1;",
    "draws_ten_rows": "for ( k = 0; k < 10; sub_44A140(k, (DWORD)a3) )",
    "hit_tests_ten_rows": "if ( v108 <= 9 )",
    "selected_row_formula": "dword_5441E0 = ((dword_544D00 >> byte_54512C) - 155) / 22;",
    "accept_helper_call": "sub_44A110(0, (DWORD)a3);",
    "loadsave_after_accept": "sub_444490(a2, (DWORD)a3, a4);",
    "row_draw_formula": "v4 = (unsigned __int16)(22 * a1 + 155);",
    "row_text_bounds": "UI_DrawTextFmt(v4, 244, 410, 22 * a1 + 155",
}
HARNESS_MARKERS = {
    "validate_range_0_9": "[ValidateRange(0,9)]",
    "load_mouse_x": "$loadMouseX = 320",
    "load_mouse_y_formula": "$loadMouseY = 166 + (22 * $LoadSlot)",
    "load_mouse_raw_x": "$loadMouseRawX = $loadMouseX -shl 6",
    "load_mouse_raw_y": "$loadMouseRawY = $loadMouseY -shl 6",
    "load_slot_replacement": "$probeText = $probeText.Replace('__LOAD_SLOT__'",
}

ROUTE_INJECT_RE = re.compile(r"route-injects load slot (?P<slot>\d+)")
LOAD_COORD_RE = re.compile(
    r"SURFDUMP_LOAD_COORD\b.*?\bseq=(?P<seq>\d+)\b.*?\bmouse=\((?P<mouse_x>-?\d+),(?P<mouse_y>-?\d+)\)"
    r".*?\bselected=(?P<selected>-?\d+)\b.*?\baccept=(?P<accept>-?\d+)"
)
FORCE_SELECT_RE = re.compile(
    r"SURFDUMP_FORCE_LOAD_SELECT\b.*?\bseq=(?P<seq>\d+)\b.*?\bmouse=\((?P<mouse_x>-?\d+),(?P<mouse_y>-?\d+)\)"
    r".*?\bselected=(?P<selected>-?\d+)\b.*?\baccept=(?P<accept>-?\d+)"
)
FORCE_ACCEPT_RE = re.compile(
    r"SURFDUMP_FORCE_LOAD_ACCEPT\b.*?\bseq=(?P<seq>\d+)\b.*?\bselected=(?P<selected>-?\d+)"
    r".*?\baccept=(?P<accept>-?\d+)\b.*?\bmouse=\((?P<mouse_x>-?\d+),(?P<mouse_y>-?\d+)\)"
)
LOAD_ACCEPT_RE = re.compile(
    r"SURFDUMP_LOAD_ACCEPT_CALL\b.*?\barg=(?P<arg>-?\d+)\b.*?\bselected=(?P<selected>-?\d+)"
    r".*?\baccept_before=(?P<accept_before>-?\d+)\b.*?\bmouse=\((?P<mouse_x>-?\d+),(?P<mouse_y>-?\d+)\)"
)
LOADSAVE_RE = re.compile(
    r"SURFDUMP_LOADSAVE\b.*?\bselected_arg=(?P<selected_arg>-?\d+)\b.*?"
    r"\bselected_global=(?P<selected_global>-?\d+)\b.*?\baccept=(?P<accept>-?\d+)"
)
PLAYGAME_RE = re.compile(
    r"SURFDUMP_PLAYGAME\b.*?\bmap=\((?P<map_w>\d+),(?P<map_h>\d+)\)\s+"
    r"scroll=\((?P<scroll_x>-?\d+),(?P<scroll_y>-?\d+)\).*?"
    r"\bsize=\((?P<surface_w>\d+),(?P<surface_h>\d+)\)"
)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig", errors="replace")


def status_text(passed: bool) -> str:
    return "PASS" if passed else "FAIL"


def expected_mouse(slot: int | None) -> list[int] | None:
    if slot is None:
        return None
    return [320, 166 + (22 * slot)]


def maybe_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def all_matches(pattern: re.Pattern[str], text: str) -> list[dict[str, int]]:
    rows: list[dict[str, int]] = []
    for match in pattern.finditer(text):
        rows.append({key: int(value) for key, value in match.groupdict().items()})
    return rows


def first_match(pattern: re.Pattern[str], text: str) -> dict[str, int] | None:
    rows = all_matches(pattern, text)
    return rows[0] if rows else None


def check_markers(path: Path, markers: dict[str, str]) -> dict[str, Any]:
    failures: list[str] = []
    text = ""
    exists = path.exists()
    if not exists:
        failures.append(f"missing text file: {path}")
    else:
        text = read_text(path)

    results = {name: marker in text for name, marker in markers.items()}
    for name, present in results.items():
        if not present:
            failures.append(f"missing marker {name}: {markers[name]}")
    return {
        "path": str(path),
        "exists": exists,
        "passed": not failures,
        "markers": results,
        "failures": failures,
    }


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
        text = read_text(log_path)

    route = first_match(ROUTE_INJECT_RE, text)
    slot = maybe_int(summary.get("LoadSlot"))
    if slot is None and route:
        slot = route.get("slot")
    load_coords = all_matches(LOAD_COORD_RE, text)
    force_selects = all_matches(FORCE_SELECT_RE, text)
    force_accepts = all_matches(FORCE_ACCEPT_RE, text)
    load_accepts = all_matches(LOAD_ACCEPT_RE, text)
    loadsave = first_match(LOADSAVE_RE, text)
    playgame = first_match(PLAYGAME_RE, text)
    first_coord = load_coords[0] if load_coords else None
    actual_mouse = [first_coord["mouse_x"], first_coord["mouse_y"]] if first_coord else None
    expected = expected_mouse(slot)
    no_av = (
        summary.get("Av") is not True
        and "AV_SURFDUMP" not in text
        and "c0000005" not in text.lower()
        and "access violation" not in text.lower()
    )

    return {
        "run": str(run),
        "summary_json": str(summary_path),
        "log": str(log_path),
        "summary_exists": summary_path.exists(),
        "log_exists": log_path.exists(),
        "passed": summary.get("Passed") is True,
        "timed_out": summary.get("TimedOut") is True,
        "hidden_desktop": summary.get("HiddenDesktop") is True,
        "allow_visible_desktop": summary.get("AllowVisibleDesktop") is True,
        "use_ddraw_proxy": summary.get("UseDdrawProxy") is True,
        "skip_map_validation": summary.get("SkipMapValidation"),
        "fast_forward_start_anims": summary.get("FastForwardStartAnims"),
        "stage": summary.get("Stage"),
        "candidate_sha256": summary.get("CandidateSha256"),
        "load_slot": slot,
        "route_injected_load_slot": route.get("slot") if route else None,
        "expected_mouse": expected,
        "first_load_coord": first_coord,
        "actual_mouse": actual_mouse,
        "mouse_formula_ok": actual_mouse == expected if actual_mouse and expected else False,
        "load_coord_count": len(load_coords),
        "force_select_count": len(force_selects),
        "force_accept_count": len(force_accepts),
        "load_accept_count": len(load_accepts),
        "loadsave": loadsave,
        "playgame": playgame,
        "load_succeeded": bool(loadsave and playgame),
        "no_av": no_av,
        "screenshot": summary.get("PngPath"),
        "timeout_stack_log": summary.get("TimeoutStackLog"),
        "failures": failures,
    }


def classify_success(run: dict[str, Any], expected_slot: int) -> tuple[str, list[str]]:
    failures: list[str] = []
    if run.get("load_slot") != expected_slot:
        failures.append(f"load slot was {run.get('load_slot')}, expected {expected_slot}")
    if run.get("hidden_desktop") is not True:
        failures.append("run was not hidden-desktop")
    if run.get("allow_visible_desktop"):
        failures.append("run allowed visible desktop fallback")
    if run.get("use_ddraw_proxy") is not True:
        failures.append("run did not use the DirectDraw proxy")
    if run.get("mouse_formula_ok") is not True:
        failures.append(f"first load mouse was {run.get('actual_mouse')}, expected {run.get('expected_mouse')}")
    if run.get("load_succeeded") is not True:
        failures.append("run did not reach both SURFDUMP_LOADSAVE and SURFDUMP_PLAYGAME")
    loadsave = run.get("loadsave") or {}
    if loadsave.get("selected_arg") != expected_slot or loadsave.get("selected_global") != expected_slot:
        failures.append(f"LOADSAVE selected {loadsave}, expected slot {expected_slot}")
    if int(run.get("force_select_count") or 0) <= 0:
        failures.append("run did not reach forced load-select breakpoint")
    if int(run.get("force_accept_count") or 0) <= 0:
        failures.append("run did not reach forced load-accept breakpoint")
    if int(run.get("load_accept_count") or 0) <= 0:
        failures.append("run did not reach load accept helper")
    if run.get("timed_out"):
        failures.append("run timed out")
    if run.get("no_av") is not True:
        failures.append("run has AV evidence")
    return ("loads" if not failures else "unexpected"), failures


def classify_blocked(run: dict[str, Any], expected_slot: int) -> tuple[str, list[str]]:
    failures: list[str] = []
    if run.get("load_slot") != expected_slot:
        failures.append(f"load slot was {run.get('load_slot')}, expected {expected_slot}")
    if run.get("hidden_desktop") is not True:
        failures.append("run was not hidden-desktop")
    if run.get("allow_visible_desktop"):
        failures.append("run allowed visible desktop fallback")
    if run.get("use_ddraw_proxy") is not True:
        failures.append("run did not use the DirectDraw proxy")
    if run.get("mouse_formula_ok") is not True:
        failures.append(f"first load mouse was {run.get('actual_mouse')}, expected {run.get('expected_mouse')}")
    if run.get("timed_out") is not True:
        failures.append("run did not time out as current blocker evidence")
    if run.get("loadsave"):
        failures.append(f"run unexpectedly reached LOADSAVE: {run.get('loadsave')}")
    if run.get("playgame"):
        failures.append(f"run unexpectedly reached PlayGame: {run.get('playgame')}")
    if int(run.get("force_select_count") or 0) > 0:
        failures.append("run reached forced load-select breakpoint; blocker shape changed")
    if int(run.get("force_accept_count") or 0) > 0:
        failures.append("run reached forced load-accept breakpoint; blocker shape changed")
    if int(run.get("load_accept_count") or 0) > 0:
        failures.append("run reached load accept helper; blocker shape changed")
    if run.get("no_av") is not True:
        failures.append("run has AV evidence")
    return ("timeout_before_force_select_and_loadsave" if not failures else "unexpected"), failures


def build_report(
    decomp_c: Path = DEFAULT_DECOMP_C,
    surface_probe_script: Path = DEFAULT_SURFACE_PROBE_SCRIPT,
    slot2_run: Path = DEFAULT_SLOT2_RUN,
    slot3_run: Path = DEFAULT_SLOT3_RUN,
    slot4_run: Path = DEFAULT_SLOT4_RUN,
    slot5_run: Path = DEFAULT_SLOT5_RUN,
    recent_slot5_run: Path = DEFAULT_RECENT_SLOT5_RUN,
) -> dict[str, Any]:
    failures: list[str] = []
    static_decomp = check_markers(decomp_c, DECOMP_MARKERS)
    harness = check_markers(surface_probe_script, HARNESS_MARKERS)
    failures.extend(f"decomp: {failure}" for failure in static_decomp["failures"])
    failures.extend(f"harness: {failure}" for failure in harness["failures"])

    runs = {
        "slot2_success": parse_run(slot2_run),
        "slot3_blocked": parse_run(slot3_run),
        "slot4_blocked": parse_run(slot4_run),
        "slot5_blocked": parse_run(slot5_run),
        "recent_slot5_blocked": parse_run(recent_slot5_run),
    }
    for label, run in runs.items():
        failures.extend(f"{label}: {failure}" for failure in run.get("failures") or [])

    slot_status: dict[str, Any] = {}
    slot2_status, status_failures = classify_success(runs["slot2_success"], 2)
    slot_status["slot2_success"] = {
        "status": slot2_status,
        "run": runs["slot2_success"]["run"],
        "selected": runs["slot2_success"].get("loadsave"),
        "mouse": runs["slot2_success"].get("actual_mouse"),
        "failures": status_failures,
    }
    failures.extend(f"slot2_success: {failure}" for failure in status_failures)

    for label, expected_slot in (
        ("slot3_blocked", 3),
        ("slot4_blocked", 4),
        ("slot5_blocked", 5),
        ("recent_slot5_blocked", 5),
    ):
        blocked_status, status_failures = classify_blocked(runs[label], expected_slot)
        slot_status[label] = {
            "status": blocked_status,
            "run": runs[label]["run"],
            "mouse": runs[label].get("actual_mouse"),
            "force_select_count": runs[label].get("force_select_count"),
            "force_accept_count": runs[label].get("force_accept_count"),
            "load_accept_count": runs[label].get("load_accept_count"),
            "timeout_stack_log": runs[label].get("timeout_stack_log"),
            "failures": status_failures,
        }
        failures.extend(f"{label}: {failure}" for failure in status_failures)

    cohort_sha = {
        runs[label].get("candidate_sha256")
        for label in ("slot2_success", "slot3_blocked", "slot4_blocked", "slot5_blocked")
        if runs[label].get("candidate_sha256")
    }
    if len(cohort_sha) > 1:
        failures.append(f"archived slot cohort candidate SHA values disagree: {sorted(cohort_sha)}")
    cohort_stage = {
        runs[label].get("stage")
        for label in ("slot2_success", "slot3_blocked", "slot4_blocked", "slot5_blocked")
        if runs[label].get("stage")
    }
    if len(cohort_stage) > 1:
        failures.append(f"archived slot cohort stages disagree: {sorted(cohort_stage)}")

    passed = not failures
    current_boundary = (
        "static code and harness parameters allow rows 0-9, but current archived hidden "
        "evidence only proves the slot-2 row path. Slots 3, 4, and 5, plus the current "
        "slot-5 right-bottom attempt, stall before force-select/accept and LOADSAVE."
    )
    next_steps = [
        "debug why rows 3-5 stop before the forced load-select breakpoint under the current CDB route",
        "or create an isolated test working directory that maps the slot-5 save state to a proven row without editing C:\\Clash\\save",
        "or use a direct-loader probe, but label it non-natural route evidence until menu selection is proven",
    ]

    return {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "passed": passed,
        "runtime_policy": RUNTIME_POLICY,
        "guard_policy": GUARD_POLICY,
        "promotion_ready": False,
        "static_decomp": static_decomp,
        "harness": harness,
        "slot_status": slot_status,
        "runs": runs,
        "summary": {
            "static_load_rows": "0..9" if static_decomp.get("passed") else None,
            "harness_mouse_formula": "x=320, y=166 + 22 * LoadSlot" if harness.get("passed") else None,
            "archived_success_slots": [2] if slot2_status == "loads" else [],
            "archived_blocked_slots": [
                slot
                for label, slot in (("slot3_blocked", 3), ("slot4_blocked", 4), ("slot5_blocked", 5))
                if slot_status.get(label, {}).get("status") == "timeout_before_force_select_and_loadsave"
            ],
            "recent_slot5_blocked": (
                slot_status.get("recent_slot5_blocked", {}).get("status")
                == "timeout_before_force_select_and_loadsave"
            ),
            "current_boundary": current_boundary,
            "next_proof_options": next_steps,
            "cohort_candidate_sha256": next(iter(cohort_sha), None) if len(cohort_sha) == 1 else None,
            "cohort_stage": next(iter(cohort_stage), None) if len(cohort_stage) == 1 else None,
        },
        "screenshot": runs["slot2_success"].get("screenshot"),
        "failures": failures,
    }


def write_markdown(path: Path, report: dict[str, Any]) -> None:
    summary = report["summary"]
    lines = [
        "# Load Slot Route Limit Guard",
        "",
        f"- Status: {status_text(bool(report.get('passed')))}",
        f"- Generated: `{report['generated_at']}`",
        f"- Runtime policy: {report['runtime_policy']}",
        f"- Guard policy: {report['guard_policy']}",
        f"- Promotion ready: `{report['promotion_ready']}`",
        f"- Static load rows: `{summary.get('static_load_rows')}`",
        f"- Harness mouse formula: `{summary.get('harness_mouse_formula')}`",
        f"- Archived success slots: `{summary.get('archived_success_slots')}`",
        f"- Archived blocked slots: `{summary.get('archived_blocked_slots')}`",
        f"- Recent slot-5 blocked: `{summary.get('recent_slot5_blocked')}`",
        f"- Cohort stage: `{summary.get('cohort_stage')}`",
        f"- Cohort candidate SHA-256: `{summary.get('cohort_candidate_sha256')}`",
        "",
        "## Boundary",
        "",
        summary.get("current_boundary") or "",
        "",
        "## Slot Status",
        "",
    ]
    for label, status in report["slot_status"].items():
        lines.append(
            "- `{label}`: `{status}` run=`{run}` mouse=`{mouse}`".format(
                label=label,
                status=status.get("status"),
                run=status.get("run"),
                mouse=status.get("mouse"),
            )
        )
        if status.get("timeout_stack_log"):
            lines.append(f"  Timeout stack: `{status['timeout_stack_log']}`")
        for failure in status.get("failures") or []:
            lines.append(f"  - {failure}")
    lines.extend(["", "## Next Proof Options", ""])
    lines.extend(f"- {step}" for step in summary.get("next_proof_options") or [])
    if report.get("screenshot"):
        lines.extend(["", f"![slot2 load route surface]({report['screenshot']})"])
    if report.get("failures"):
        lines.extend(["", "## Failures", ""])
        lines.extend(f"- {failure}" for failure in report["failures"])
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--decomp-c", type=Path, default=DEFAULT_DECOMP_C)
    parser.add_argument("--surface-probe-script", type=Path, default=DEFAULT_SURFACE_PROBE_SCRIPT)
    parser.add_argument("--slot2-run", type=Path, default=DEFAULT_SLOT2_RUN)
    parser.add_argument("--slot3-run", type=Path, default=DEFAULT_SLOT3_RUN)
    parser.add_argument("--slot4-run", type=Path, default=DEFAULT_SLOT4_RUN)
    parser.add_argument("--slot5-run", type=Path, default=DEFAULT_SLOT5_RUN)
    parser.add_argument("--recent-slot5-run", type=Path, default=DEFAULT_RECENT_SLOT5_RUN)
    parser.add_argument("--write-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--write-markdown", type=Path, default=DEFAULT_MD)
    parser.add_argument("--require-pass", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(
        decomp_c=args.decomp_c,
        surface_probe_script=args.surface_probe_script,
        slot2_run=args.slot2_run,
        slot3_run=args.slot3_run,
        slot4_run=args.slot4_run,
        slot5_run=args.slot5_run,
        recent_slot5_run=args.recent_slot5_run,
    )
    print(f"overall: {status_text(bool(report['passed']))}")
    print(f"runtime-policy: {report['runtime_policy']}")
    print(f"promotion-ready: {report['promotion_ready']}")
    for label, status in report["slot_status"].items():
        print(f"{label}: {status_text(status.get('status') != 'unexpected')} {status.get('status')}")
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
