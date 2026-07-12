#!/usr/bin/env python3
"""Classify the current load-slot timeout phase from archived CDB logs.

This is repo-only evidence. It reads existing hidden-desktop CDB run folders and
does not launch Clash95, CDB, wrappers, PowerShell, or visible windows.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_SLOT2_RUN = Path("captures/archive/cdb-surface-dump-20260712-153805")
DEFAULT_SLOT3_RUN = Path("captures/archive/cdb-surface-dump-20260712-153827")
DEFAULT_SLOT4_RUN = Path("captures/archive/cdb-surface-dump-20260712-154103")
DEFAULT_SLOT5_RUN = Path("captures/archive/cdb-surface-dump-20260712-154340")
DEFAULT_RECENT_SLOT5_RUN = Path("captures/archive/cdb-surface-dump-20260712-153529")
DEFAULT_JSON = Path("captures/current/load-slot-timeout-phase-current.json")
DEFAULT_MD = Path("captures/current/load-slot-timeout-phase-current.md")

RUNTIME_POLICY = (
    "repo-only; reads archived hidden-desktop CDB logs, summaries, and timeout stacks; "
    "does not launch Clash95, CDB, wrappers, PowerShell, or visible windows"
)
GUARD_POLICY = (
    "passes only when slot 2 still proves the full load-menu accept path while "
    "slots 3-5 and the current slot-5 right-bottom attempt all stall after early "
    "load-menu descriptor rows but before 0044895A load-menu entry, forced select, "
    "LOADSAVE, and PlayGame"
)

MARKERS = [
    "SURFDUMP_START_ANIMS_SLEEP_FAST_FORWARD_ENABLED",
    "SURFDUMP_SKIP_START_SLEEP",
    "SURFDUMP_MAIN_HIT",
    "SURFDUMP_FORCE_MAIN_CLICK",
    "SURFDUMP_SKIP_MAIN_LOAD_CALLBACK",
    "SURFDUMP_LOAD_COORD",
    "SURFDUMP_LOAD_MENU_ENTRY",
    "SURFDUMP_LOAD_MENU_LOOP",
    "SURFDUMP_FORCE_LOAD_SELECT",
    "SURFDUMP_FORCE_LOAD_ACCEPT",
    "SURFDUMP_LOAD_ACCEPT_CALL",
    "SURFDUMP_LOADSAVE",
    "SURFDUMP_PLAYGAME",
    "BATTLE_SLOT_SCAN_START",
    "SURFDUMP_READY",
]

LOAD_COORD_RE = re.compile(
    r"SURFDUMP_LOAD_COORD\b.*?\bseq=(?P<seq>\d+)\b.*?\bchoice=(?P<choice>-?\d+)\b"
    r".*?\bentry=0x(?P<entry>[0-9a-fA-F]+)\b.*?\bex=(?P<ex>-?\d+)\b.*?\bey=(?P<ey>-?\d+)\b"
    r".*?\bmouse=\((?P<mouse_x>-?\d+),(?P<mouse_y>-?\d+)\)\s+"
    r"selected=(?P<selected>-?\d+)\s+accept=(?P<accept>-?\d+)"
)
LOADSAVE_RE = re.compile(r"SURFDUMP_LOADSAVE\b.*?\bselected_arg=(?P<selected_arg>-?\d+)")
PLAYGAME_RE = re.compile(r"SURFDUMP_PLAYGAME\b")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig", errors="replace")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def canonical_capture_path(path: Path) -> Path:
    if path.exists():
        return path
    normalized = str(path).replace("\\", "/")
    lower = normalized.lower()
    marker = "/captures/"
    suffix: str | None = None
    if marker in lower:
        suffix = normalized[lower.index(marker) + len(marker) :]
    elif lower.startswith("captures/"):
        suffix = normalized[len("captures/") :]
    if not suffix:
        return path
    candidates = [REPO_ROOT / "captures" / suffix]
    if suffix.lower().startswith("cdb-surface-dump-"):
        candidates.insert(0, REPO_ROOT / "captures" / "archive" / suffix)
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return path


def status_text(passed: bool) -> str:
    return "PASS" if passed else "FAIL"


def marker_counts(text: str) -> dict[str, int]:
    return {marker: text.count(marker) for marker in MARKERS}


def last_marker(counts: dict[str, int]) -> str | None:
    present = [marker for marker in MARKERS if counts.get(marker)]
    return present[-1] if present else None


def load_coord_rows(text: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for match in LOAD_COORD_RE.finditer(text):
        row: dict[str, Any] = {"entry": f"0x{match.group('entry').lower()}"}
        for key, value in match.groupdict().items():
            if key == "entry":
                continue
            row[key] = int(value)
        rows.append(row)
    return rows


def stack_category(text: str) -> str | None:
    lowered = text.lower()
    if not lowered:
        return None
    if "user32!peekmessagea" in lowered and "+0x61b58" in lowered:
        return "win32_message_poll_before_load_menu_loop"
    if "rtlqueryperformancecounter" in lowered and "+0x207c0" in lowered:
        return "qpc_timing_poll_before_load_menu_loop"
    if "+0x207cd" in lowered and "+0x605e4" in lowered:
        return "engine_timing_poll_before_load_menu_loop"
    if "css_" in lowered or "playavistretch" in lowered:
        return "avi_or_audio_worker_present"
    return "unknown_timeout_stack"


def parse_run(run: Path) -> dict[str, Any]:
    summary_path = run / "summary.json"
    log_path = run / "cdb-surface-dump.log"
    failures: list[str] = []
    summary: dict[str, Any] = {}
    log_text = ""
    stack_text = ""

    if not summary_path.exists():
        failures.append(f"missing summary: {summary_path}")
    else:
        summary = load_json(summary_path)
    if not log_path.exists():
        failures.append(f"missing log: {log_path}")
    else:
        log_text = read_text(log_path)

    timeout_stack = summary.get("TimeoutStackLog")
    stack_path = canonical_capture_path(Path(timeout_stack)) if timeout_stack else run / "timeout-stack.log"
    if stack_path.exists():
        stack_text = read_text(stack_path)
    elif summary.get("TimedOut"):
        failures.append(f"missing timeout stack: {stack_path}")

    counts = marker_counts(log_text)
    coords = load_coord_rows(log_text)
    loadsave = LOADSAVE_RE.search(log_text)
    playgame = PLAYGAME_RE.search(log_text)
    timed_out = summary.get("TimedOut") is True
    no_av = summary.get("Av") is not True and "access violation" not in log_text.lower()
    last_coord = coords[-1] if coords else None

    return {
        "run": str(run),
        "summary_json": str(summary_path),
        "log": str(log_path),
        "timeout_stack_log": str(stack_path) if stack_path else None,
        "summary_exists": summary_path.exists(),
        "log_exists": log_path.exists(),
        "passed": summary.get("Passed") is True,
        "timed_out": timed_out,
        "hidden_desktop": summary.get("HiddenDesktop") is True,
        "allow_visible_desktop": summary.get("AllowVisibleDesktop") is True,
        "load_slot": summary.get("LoadSlot"),
        "stage": summary.get("Stage"),
        "candidate_sha256": summary.get("CandidateSha256"),
        "marker_counts": counts,
        "last_marker": last_marker(counts),
        "load_coord_rows": coords,
        "load_coord_count": len(coords),
        "first_load_coord": coords[0] if coords else None,
        "last_load_coord": last_coord,
        "loadsave_selected_arg": int(loadsave.group("selected_arg")) if loadsave else None,
        "playgame_count": counts["SURFDUMP_PLAYGAME"],
        "timeout_stack_category": stack_category(stack_text),
        "no_av": no_av,
        "screenshot": summary.get("PngPath"),
        "failures": failures,
    }


def classify_success(run: dict[str, Any], expected_slot: int) -> tuple[str, list[str]]:
    failures: list[str] = []
    counts = run["marker_counts"]
    if run.get("hidden_desktop") is not True:
        failures.append("run is not hidden-desktop")
    if run.get("allow_visible_desktop"):
        failures.append("run allowed visible desktop fallback")
    if run.get("load_slot") != expected_slot:
        failures.append(f"load slot is {run.get('load_slot')}, expected {expected_slot}")
    for marker in (
        "SURFDUMP_LOAD_MENU_ENTRY",
        "SURFDUMP_LOAD_MENU_LOOP",
        "SURFDUMP_FORCE_LOAD_SELECT",
        "SURFDUMP_FORCE_LOAD_ACCEPT",
        "SURFDUMP_LOAD_ACCEPT_CALL",
        "SURFDUMP_LOADSAVE",
        "SURFDUMP_PLAYGAME",
    ):
        if counts.get(marker, 0) <= 0:
            failures.append(f"missing success marker {marker}")
    if run.get("loadsave_selected_arg") != expected_slot:
        failures.append(f"LOADSAVE selected {run.get('loadsave_selected_arg')}, expected {expected_slot}")
    if run.get("timed_out"):
        failures.append("success run timed out")
    if run.get("no_av") is not True:
        failures.append("success run has AV evidence")
    return ("load_menu_accept_success" if not failures else "unexpected"), failures


def classify_timeout(run: dict[str, Any], expected_slot: int) -> tuple[str, list[str]]:
    failures: list[str] = []
    counts = run["marker_counts"]
    if run.get("hidden_desktop") is not True:
        failures.append("run is not hidden-desktop")
    if run.get("allow_visible_desktop"):
        failures.append("run allowed visible desktop fallback")
    if run.get("load_slot") != expected_slot:
        failures.append(f"load slot is {run.get('load_slot')}, expected {expected_slot}")
    if run.get("timed_out") is not True:
        failures.append("blocked run did not time out")
    if counts.get("SURFDUMP_LOAD_COORD", 0) <= 0:
        failures.append("blocked run never reached load-coordinate descriptor rows")
    for marker in (
        "SURFDUMP_LOAD_MENU_ENTRY",
        "SURFDUMP_LOAD_MENU_LOOP",
        "SURFDUMP_FORCE_LOAD_SELECT",
        "SURFDUMP_FORCE_LOAD_ACCEPT",
        "SURFDUMP_LOAD_ACCEPT_CALL",
        "SURFDUMP_LOADSAVE",
        "SURFDUMP_PLAYGAME",
    ):
        if counts.get(marker, 0) > 0:
            failures.append(f"blocked run unexpectedly reached {marker}")
    if run.get("timeout_stack_category") is None:
        failures.append("blocked run has no timeout stack category")
    if run.get("no_av") is not True:
        failures.append("blocked run has AV evidence")
    return ("stalled_after_load_button_before_load_menu_loop" if not failures else "unexpected"), failures


def build_report(
    slot2_run: Path = DEFAULT_SLOT2_RUN,
    slot3_run: Path = DEFAULT_SLOT3_RUN,
    slot4_run: Path = DEFAULT_SLOT4_RUN,
    slot5_run: Path = DEFAULT_SLOT5_RUN,
    recent_slot5_run: Path = DEFAULT_RECENT_SLOT5_RUN,
) -> dict[str, Any]:
    failures: list[str] = []
    runs = {
        "slot2_success": parse_run(slot2_run),
        "slot3_timeout": parse_run(slot3_run),
        "slot4_timeout": parse_run(slot4_run),
        "slot5_timeout": parse_run(slot5_run),
        "recent_slot5_timeout": parse_run(recent_slot5_run),
    }
    for label, run in runs.items():
        failures.extend(f"{label}: {failure}" for failure in run.get("failures", []))

    phases: dict[str, Any] = {}
    status, status_failures = classify_success(runs["slot2_success"], 2)
    phases["slot2_success"] = phase_record(runs["slot2_success"], status, status_failures)
    failures.extend(f"slot2_success: {failure}" for failure in status_failures)

    for label, expected_slot in (
        ("slot3_timeout", 3),
        ("slot4_timeout", 4),
        ("slot5_timeout", 5),
        ("recent_slot5_timeout", 5),
    ):
        status, status_failures = classify_timeout(runs[label], expected_slot)
        phases[label] = phase_record(runs[label], status, status_failures)
        failures.extend(f"{label}: {failure}" for failure in status_failures)

    blocked = [
        label
        for label in ("slot3_timeout", "slot4_timeout", "slot5_timeout")
        if phases[label]["status"] == "stalled_after_load_button_before_load_menu_loop"
    ]
    stack_categories = {
        label: phases[label]["timeout_stack_category"]
        for label in ("slot3_timeout", "slot4_timeout", "slot5_timeout", "recent_slot5_timeout")
    }

    return {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "passed": not failures,
        "runtime_policy": RUNTIME_POLICY,
        "guard_policy": GUARD_POLICY,
        "promotion_ready": False,
        "runs": runs,
        "phases": phases,
        "summary": {
            "slot2_phase": phases["slot2_success"]["status"],
            "blocked_slots": [3, 4, 5] if len(blocked) == 3 else [],
            "recent_slot5_blocked": (
                phases["recent_slot5_timeout"]["status"]
                == "stalled_after_load_button_before_load_menu_loop"
            ),
            "current_divergence": (
                "slot 2 reaches the 0044895A load-menu entry and accept path; "
                "slots 3-5 reach early 00419B80 load-coordinate descriptor rows, "
                "then time out before 0044895A load-menu entry, forced select, "
                "LOADSAVE, or PlayGame"
            ),
            "timeout_stack_categories": stack_categories,
            "next_probe_target": "instrument the transition between the early 00419B80 load descriptors and 0044895A load-menu entry for rows 3-5",
        },
        "screenshot": runs["slot2_success"].get("screenshot"),
        "failures": failures,
    }


def phase_record(run: dict[str, Any], status: str, failures: list[str]) -> dict[str, Any]:
    counts = run.get("marker_counts") or {}
    return {
        "status": status,
        "run": run.get("run"),
        "load_slot": run.get("load_slot"),
        "load_coord_count": run.get("load_coord_count"),
        "last_load_coord": run.get("last_load_coord"),
        "last_marker": run.get("last_marker"),
        "load_menu_entry_count": counts.get("SURFDUMP_LOAD_MENU_ENTRY"),
        "load_menu_loop_count": counts.get("SURFDUMP_LOAD_MENU_LOOP"),
        "force_select_count": counts.get("SURFDUMP_FORCE_LOAD_SELECT"),
        "loadsave_count": counts.get("SURFDUMP_LOADSAVE"),
        "playgame_count": counts.get("SURFDUMP_PLAYGAME"),
        "timeout_stack_category": run.get("timeout_stack_category"),
        "failures": failures,
    }


def write_markdown(path: Path, report: dict[str, Any]) -> None:
    summary = report["summary"]
    lines = [
        "# Load Slot Timeout Phase",
        "",
        f"- Status: {status_text(bool(report.get('passed')))}",
        f"- Generated: `{report['generated_at']}`",
        f"- Runtime policy: {report['runtime_policy']}",
        f"- Guard policy: {report['guard_policy']}",
        f"- Promotion ready: `{report['promotion_ready']}`",
        f"- Slot 2 phase: `{summary.get('slot2_phase')}`",
        f"- Blocked slots: `{summary.get('blocked_slots')}`",
        f"- Recent slot-5 blocked: `{summary.get('recent_slot5_blocked')}`",
        f"- Next probe target: {summary.get('next_probe_target')}",
        "",
        "## Divergence",
        "",
        summary.get("current_divergence") or "",
        "",
        "## Phase Matrix",
        "",
        "| Label | Slot | Status | Load coords | Last coord | Last marker | Stack category |",
        "| --- | ---: | --- | ---: | --- | --- | --- |",
    ]
    for label, phase in report["phases"].items():
        lines.append(
            "| {label} | {slot} | `{status}` | {coords} | `{last_coord}` | `{last_marker}` | `{stack}` |".format(
                label=label,
                slot=phase.get("load_slot"),
                status=phase.get("status"),
                coords=phase.get("load_coord_count"),
                last_coord=phase.get("last_load_coord"),
                last_marker=phase.get("last_marker"),
                stack=phase.get("timeout_stack_category"),
            )
        )
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
    parser.add_argument("--slot2-run", type=Path, default=DEFAULT_SLOT2_RUN)
    parser.add_argument("--slot3-run", type=Path, default=DEFAULT_SLOT3_RUN)
    parser.add_argument("--slot4-run", type=Path, default=DEFAULT_SLOT4_RUN)
    parser.add_argument("--slot5-run", type=Path, default=DEFAULT_SLOT5_RUN)
    parser.add_argument("--recent-slot5-run", type=Path, default=DEFAULT_RECENT_SLOT5_RUN)
    parser.add_argument("--write-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--write-markdown", type=Path, default=DEFAULT_MD)
    parser.add_argument("--require-pass", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = build_report(
        slot2_run=args.slot2_run,
        slot3_run=args.slot3_run,
        slot4_run=args.slot4_run,
        slot5_run=args.slot5_run,
        recent_slot5_run=args.recent_slot5_run,
    )
    print(f"overall: {status_text(bool(report['passed']))}")
    print(f"runtime-policy: {report['runtime_policy']}")
    for label, phase in report["phases"].items():
        print(f"{label}: {phase['status']}")
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
