#!/usr/bin/env python3
"""Guard the focused right-bottom controlled grid-hit probe.

This is a repo-only inspection guard. It verifies that the focused CDB probe
still covers the proven right-bottom owner/action/grid hit-test callsites, that
the summary parser still recognizes the probe rows, and that the current
archived hidden-desktop log proves native coordinate (450,73) returns grid cell
0 with no failure-exit or AV rows.
It does not launch Clash95, CDB, wrappers, PowerShell, or visible windows.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import right_bottom_grid_hit_summary


DEFAULT_PROBE = Path("probes/cdb/ui/clash95_right_bottom_grid_hit_extra.cdb")
DEFAULT_SUMMARY_PARSER = Path("tools/right_bottom_grid_hit_summary.py")
DEFAULT_FOCUSED_RUN = Path("captures/archive/cdb-surface-dump-20260712-150240")
DEFAULT_JSON = Path("captures/current/right-bottom-grid-hit-probe-guard-current.json")
DEFAULT_MD = Path("captures/current/right-bottom-grid-hit-probe-guard-current.md")
RUNTIME_POLICY = "repo-only; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows"
GUARD_POLICY = (
    "focused right-bottom grid-hit proof must keep the owner/action/grid breakpoints, "
    "continue to prove native coordinate (450,73) returns grid cell 0, and stay "
    "hidden-desktop with no failure-exit or AV rows"
)
EXPECTED_STAGE = (
    "gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-"
    "minimapright-dynvswitch-rightbottomcompose"
)
EXPECTED_ENTRY = [450, 73]
EXPECTED_RESULT = 0

REQUIRED_BREAKPOINTS = {
    "00433D5F": "right-bottom owner surface pointer write short-return",
    "0040AE16": "debugger-routed owner/action sequence and surface-ready row",
    "00433914": "action descriptor call into owner route",
    "00433919": "post-owner return and fallback ready row",
    "00435BC0": "right-bottom owner route entry",
    "00435BCA": "right-bottom owner pointer write",
    "00435C3E": "right-bottom hover-slot write",
    "004347A0": "right-bottom panel draw",
    "00434E20": "right-bottom grid draw",
    "00435280": "right-bottom status draw",
    "00435500": "right-bottom action-box draw",
    "00435B90": "native grid coordinate injection",
    "00435A00": "grid route entry",
    "00435A0E": "grid gate result",
    "00435A17": "grid hit-test call",
    "00435580": "grid hit-test entry",
    "0043560E": "grid hit-test result and accept",
    "004355FF": "grid failure sentinel",
    "00435A9A": "selection-update sentinel",
    "00435AA0": "selection-after sentinel",
}

REQUIRED_PROBE_MARKERS = {
    marker: "recognized right-bottom controlled grid-hit probe row"
    for marker in right_bottom_grid_hit_summary.MARKERS
}

REQUIRED_LOG_MARKERS = {
    "RBGRID_OWNER_SETUP_CALL": "owner setup was reached",
    "RBGRID_OWNER_FLAG_FORCED": "owner action flag was forced",
    "RBGRID_WRITE_532154": "owner surface pointer write was observed",
    "RBGRID_ACTION_CALL": "action descriptor route was invoked",
    "RBGRID_433914_CALL_435BC0": "owner route callsite was reached",
    "RBGRID_OWNER_435BC0_ENTRY": "owner route entered",
    "RBGRID_WRITE_532218": "owner global write was observed",
    "RBGRID_WRITE_5322C8": "hover-slot write was observed",
    "RBGRID_PANEL_DRAW_4347A0": "panel draw row was observed",
    "RBGRID_GRID_DRAW_434E20": "grid draw row was observed",
    "RBGRID_STATUS_DRAW_435280": "status draw row was observed",
    "RBGRID_ACTION_BOX_435500": "action-box draw row was observed",
    "RBGRID_FORCE_NATIVE": "native coordinate was installed",
    "RBGRID_GRID_ROUTE_ENTRY": "grid route entry was reached",
    "RBGRID_GRID_GATE": "grid gate was reached",
    "RBGRID_GRID_CALL": "grid hit-test callsite was reached",
    "RBGRID_GRID_ENTRY": "grid hit-test entry was reached",
    "RBGRID_GRID_RESULT": "grid hit-test result was logged",
    "RBGRID_GRID_ACCEPT": "expected grid result was accepted",
    "RBGRID_4338E0_AFTER_435BC0": "owner route returned cleanly",
    "RBGRID_SURFDUMP_READY": "probe surface-ready row was emitted",
    "SURFDUMP_READY": "surface-dump host row was emitted",
}


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig", errors="replace")


def status_text(passed: bool) -> str:
    return "PASS" if passed else "FAIL"


def probe_template_matches(value: object, expected_rel: str) -> bool:
    normalized = str(value or "").replace("\\", "/").lower()
    expected = expected_rel.replace("\\", "/").lower()
    basename = expected.rsplit("/", 1)[-1]
    return expected in normalized or normalized.endswith("/" + basename) or normalized.endswith(basename)


def breakpoint_present(text: str, address: str) -> bool:
    return bool(re.search(rf"\bbp(?:\s+/1)?\s+{re.escape(address)}\b", text, re.IGNORECASE))


def check_probe_script(path: Path) -> dict[str, Any]:
    failures: list[str] = []
    if not path.exists():
        return {
            "passed": False,
            "path": str(path),
            "failures": [f"missing probe script: {path}"],
        }

    text = read_text(path)
    breakpoints = {
        address: {
            "present": breakpoint_present(text, address),
            "purpose": purpose,
        }
        for address, purpose in REQUIRED_BREAKPOINTS.items()
    }
    for address, record in breakpoints.items():
        if not record["present"]:
            failures.append(f"missing breakpoint {address}: {record['purpose']}")

    markers = {
        marker: {
            "present": marker in text,
            "purpose": purpose,
        }
        for marker, purpose in REQUIRED_PROBE_MARKERS.items()
    }
    for marker, record in markers.items():
        if not record["present"]:
            failures.append(f"missing probe marker {marker}: {record['purpose']}")

    return {
        "passed": not failures,
        "path": str(path),
        "breakpoints": breakpoints,
        "markers": markers,
        "failures": failures,
    }


def check_summary_parser(path: Path) -> dict[str, Any]:
    failures: list[str] = []
    if not path.exists():
        return {
            "passed": False,
            "path": str(path),
            "failures": [f"missing summary parser: {path}"],
        }

    text = read_text(path)
    markers = {marker: marker in text for marker in REQUIRED_PROBE_MARKERS}
    for marker, present in markers.items():
        if not present:
            failures.append(f"summary parser does not recognize marker: {marker}")

    return {
        "passed": not failures,
        "path": str(path),
        "markers": markers,
        "failures": failures,
    }


def ready_sizes(grid: dict[str, Any]) -> list[list[int]]:
    sizes: list[list[int]] = []
    for row in grid.get("rows") or []:
        if row.get("marker") not in {"RBGRID_SURFDUMP_READY", "SURFDUMP_READY"}:
            continue
        values = row.get("values") or {}
        size = values.get("size")
        if isinstance(size, list):
            sizes.append(size)
    return sizes


def check_focused_log(run: Path) -> dict[str, Any]:
    summary_path = run / "summary.json"
    log = run / "cdb-surface-dump.log"
    failures: list[str] = []
    if not summary_path.exists():
        return {
            "passed": False,
            "run": str(run),
            "summary_json": str(summary_path),
            "log": str(log),
            "failures": [f"missing focused grid-hit summary: {summary_path}"],
        }
    if not log.exists():
        return {
            "passed": False,
            "run": str(run),
            "summary_json": str(summary_path),
            "log": str(log),
            "failures": [f"missing focused grid-hit log: {log}"],
        }

    summary = json.loads(summary_path.read_text(encoding="utf-8-sig"))
    grid = right_bottom_grid_hit_summary.parse_log(log, EXPECTED_ENTRY, EXPECTED_RESULT)
    surface = summary.get("Surface") or {}

    if summary.get("Passed") is not True:
        failures.append("focused grid-hit surface dump did not pass")
    if summary.get("HiddenDesktop") is not True:
        failures.append("focused grid-hit run was not hidden-desktop")
    if summary.get("AllowVisibleDesktop") is True:
        failures.append("focused grid-hit run allowed visible desktop fallback")
    if summary.get("UseDdrawProxy") is not True:
        failures.append("focused grid-hit run did not use the DirectDraw proxy")
    if summary.get("FastForwardStartAnims") is not True:
        failures.append("focused grid-hit run did not fast-forward startup animations")
    if summary.get("SkipMapValidation") is not True:
        failures.append("focused grid-hit run did not skip map validation for the controlled probe")
    if summary.get("Stage") != EXPECTED_STAGE:
        failures.append(f"focused grid-hit stage was {summary.get('Stage')!r}")
    if not probe_template_matches(
        summary.get("ExtraProbeTemplate"),
        "probes/cdb/ui/clash95_right_bottom_grid_hit_extra.cdb",
    ):
        failures.append("focused grid-hit extra probe template was not recorded")
    if [surface.get("Width"), surface.get("Height")] != [800, 600]:
        failures.append(f"focused grid-hit surface was {[surface.get('Width'), surface.get('Height')]}")

    marker_counts = grid.get("marker_counts") or {}
    for marker, purpose in REQUIRED_LOG_MARKERS.items():
        if int(marker_counts.get(marker) or 0) <= 0:
            failures.append(f"focused grid-hit log missing {marker}: {purpose}")

    sizes = ready_sizes(grid)
    if [800, 600] not in sizes:
        failures.append(f"focused grid-hit ready sizes did not include [800, 600]: {sizes}")
    if not grid.get("ready"):
        failures.append("focused grid-hit log did not reach ready state")
    if not grid.get("grid_hit_ok"):
        failures.append("focused grid-hit log did not prove cell 0 at native coordinate (450,73)")
    if grid.get("last_grid_entry") != EXPECTED_ENTRY:
        failures.append(f"focused grid-hit entry was {grid.get('last_grid_entry')}")
    if grid.get("last_grid_result") != EXPECTED_RESULT:
        failures.append(f"focused grid-hit result was {grid.get('last_grid_result')}")
    if int(grid.get("forced_gate_count") or 0) <= 0:
        failures.append("focused grid-hit hidden flip gate was not reached/forced")
    if int(grid.get("failure_exit_count") or 0) != 0:
        failures.append("focused grid-hit probe used failure exit")
    if int(marker_counts.get("RBGRID_GRID_FAIL") or 0) != 0:
        failures.append("focused grid-hit failure rows were observed")
    if int(grid.get("draw_row_count") or 0) <= 0:
        failures.append("focused grid-hit draw rows were not observed")
    if int(grid.get("av_count") or 0) != 0:
        failures.append("focused grid-hit AV rows were observed")

    return {
        "passed": not failures,
        "run": str(run),
        "summary_json": str(summary_path),
        "log": str(log),
        "hidden_desktop": summary.get("HiddenDesktop"),
        "allow_visible_desktop": summary.get("AllowVisibleDesktop"),
        "use_ddraw_proxy": summary.get("UseDdrawProxy"),
        "fast_forward_start_anims": summary.get("FastForwardStartAnims"),
        "skip_map_validation": summary.get("SkipMapValidation"),
        "stage": summary.get("Stage"),
        "extra_probe_template": summary.get("ExtraProbeTemplate"),
        "surface": [surface.get("Width"), surface.get("Height")],
        "ready_sizes": sizes,
        "ready": grid.get("ready"),
        "grid_hit_ok": grid.get("grid_hit_ok"),
        "last_grid_entry": grid.get("last_grid_entry"),
        "last_grid_result": grid.get("last_grid_result"),
        "forced_gate_count": grid.get("forced_gate_count"),
        "failure_exit_count": grid.get("failure_exit_count"),
        "draw_row_count": grid.get("draw_row_count"),
        "av_count": grid.get("av_count"),
        "marker_counts": marker_counts,
        "failures": failures,
    }


def build_guard(args: argparse.Namespace) -> dict[str, Any]:
    probe = check_probe_script(args.probe_script)
    parser = check_summary_parser(args.summary_parser)
    focused = check_focused_log(args.focused_run)
    checks = {
        "probe_script": probe,
        "summary_parser": parser,
        "focused_grid_hit_log": focused,
    }
    failures: list[str] = []
    for name, check in checks.items():
        if not check.get("passed"):
            failures.extend(f"{name}: {failure}" for failure in check.get("failures", []))

    return {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "passed": not failures,
        "runtime_policy": RUNTIME_POLICY,
        "guard_policy": GUARD_POLICY,
        "expected_stage": EXPECTED_STAGE,
        "expected_entry": EXPECTED_ENTRY,
        "expected_result": EXPECTED_RESULT,
        "required_breakpoints": REQUIRED_BREAKPOINTS,
        "required_probe_markers": REQUIRED_PROBE_MARKERS,
        "required_log_markers": REQUIRED_LOG_MARKERS,
        "checks": checks,
        "failures": failures,
    }


def write_json(path: Path, guard: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(guard, indent=2) + "\n", encoding="utf-8")


def write_markdown(path: Path, guard: dict[str, Any]) -> None:
    checks = guard["checks"]
    probe = checks["probe_script"]
    focused = checks["focused_grid_hit_log"]
    lines = [
        "# Right-Bottom Grid Hit Probe Guard",
        "",
        f"- Overall: {status_text(bool(guard.get('passed')))}",
        f"- Generated: `{guard['generated_at']}`",
        f"- Runtime policy: {guard['runtime_policy']}",
        f"- Guard policy: {guard['guard_policy']}",
        f"- Expected stage: `{guard['expected_stage']}`",
        f"- Expected entry/result: `{guard['expected_entry']}` -> `{guard['expected_result']}`",
        "",
        "## Probe Script",
        "",
        f"- Status: {status_text(bool(probe.get('passed')))}",
        f"- Script: `{probe.get('path')}`",
        "",
        "### Required Breakpoints",
        "",
    ]
    for address, record in (probe.get("breakpoints") or {}).items():
        lines.append(
            f"- `{address}`: {status_text(bool(record.get('present')))} - {record.get('purpose')}"
        )

    lines.extend(["", "### Required Markers", ""])
    for marker, record in (probe.get("markers") or {}).items():
        lines.append(
            f"- `{marker}`: {status_text(bool(record.get('present')))} - {record.get('purpose')}"
        )

    lines.extend(
        [
            "",
            "## Focused Grid-Hit Log",
            "",
            f"- Status: {status_text(bool(focused.get('passed')))}",
            f"- Run: `{focused.get('run')}`",
            f"- Log: `{focused.get('log')}`",
            f"- Hidden desktop: `{focused.get('hidden_desktop')}`",
            f"- Allow visible desktop: `{focused.get('allow_visible_desktop')}`",
            f"- DirectDraw proxy: `{focused.get('use_ddraw_proxy')}`",
            f"- Fast-forward startup: `{focused.get('fast_forward_start_anims')}`",
            f"- Skip map validation: `{focused.get('skip_map_validation')}`",
            f"- Stage: `{focused.get('stage')}`",
            f"- Surface: `{focused.get('surface')}`",
            f"- Ready sizes: `{focused.get('ready_sizes')}`",
            f"- Grid hit ok: `{focused.get('grid_hit_ok')}`",
            f"- Last grid entry: `{focused.get('last_grid_entry')}`",
            f"- Last grid result: `{focused.get('last_grid_result')}`",
            f"- Forced hidden flip gates: `{focused.get('forced_gate_count')}`",
            f"- Failure exits: `{focused.get('failure_exit_count')}`",
            f"- Draw rows: `{focused.get('draw_row_count')}`",
            f"- Access violations: `{focused.get('av_count')}`",
        ]
    )

    if guard.get("failures"):
        lines.extend(["", "## Failures", ""])
        lines.extend(f"- {failure}" for failure in guard["failures"])
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def print_guard(guard: dict[str, Any]) -> None:
    print(f"overall: {status_text(bool(guard.get('passed')))}")
    print(f"runtime-policy: {guard['runtime_policy']}")
    print(f"guard-policy: {guard['guard_policy']}")
    for name, check in guard["checks"].items():
        print(f"{name}: {status_text(bool(check.get('passed')))}")
        if name == "probe_script":
            present = [
                address
                for address, record in (check.get("breakpoints") or {}).items()
                if record.get("present")
            ]
            print(f"  breakpoints_present: {present}")
        if name == "focused_grid_hit_log":
            print(f"  surface: {check.get('surface')}")
            print(f"  grid_hit_ok: {check.get('grid_hit_ok')}")
            print(f"  last_grid_entry: {check.get('last_grid_entry')}")
            print(f"  last_grid_result: {check.get('last_grid_result')}")
            print(f"  failure_exit_count: {check.get('failure_exit_count')}")
            print(f"  av_count: {check.get('av_count')}")
        if check.get("failures"):
            for failure in check["failures"]:
                print(f"  - {failure}")
    if guard.get("failures"):
        print("failures:")
        for failure in guard["failures"]:
            print(f"  - {failure}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--probe-script", type=Path, default=DEFAULT_PROBE)
    parser.add_argument("--summary-parser", type=Path, default=DEFAULT_SUMMARY_PARSER)
    parser.add_argument("--focused-run", type=Path, default=DEFAULT_FOCUSED_RUN)
    parser.add_argument("--write-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--write-markdown", type=Path, default=DEFAULT_MD)
    parser.add_argument("--require-pass", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    guard = build_guard(args)
    if args.write_json:
        write_json(args.write_json, guard)
    if args.write_markdown:
        write_markdown(args.write_markdown, guard)
    print_guard(guard)
    if args.require_pass and not guard["passed"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
