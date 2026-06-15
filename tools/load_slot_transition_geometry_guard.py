#!/usr/bin/env python3
"""Guard row geometry for the load-slot transition run plan.

The transition probe is useful only if the generated row-specific commands
route to the intended load rows. This repo-only guard checks the PowerShell
formula that replaces the CDB placeholders and records the expected logical and
raw mouse coordinates for rows 3-5.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_RUN_PLAN_JSON = Path("captures/current/load-slot-transition-run-plan-current.json")
DEFAULT_SURFACE_DUMP_SCRIPT = Path("scripts/cdb/run_cdb_surface_dump.ps1")
DEFAULT_EXTRA_PROBE = Path("probes/cdb/menu/clash95_load_slot_entry_transition_extra.cdb")
DEFAULT_JSON = Path("captures/current/load-slot-transition-geometry-guard-current.json")
DEFAULT_MD = Path("captures/current/load-slot-transition-geometry-guard-current.md")

RUNTIME_POLICY = (
    "repo-only source/plan inspection; does not launch Clash95, CDB, wrappers, "
    "PowerShell, or visible windows"
)
GUARD_POLICY = (
    "passes only when the transition run plan targets rows 3-5 and the "
    "surface-dump launcher still replaces extra-probe load-slot mouse "
    "placeholders using x=320 and y=166+22*slot shifted into raw mouse globals"
)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def status_text(passed: bool) -> str:
    return "PASS" if passed else "FAIL"


def row_geometry(slot: int) -> dict[str, Any]:
    mouse_x = 320
    mouse_y = 166 + (22 * slot)
    raw_x = mouse_x << 6
    raw_y = mouse_y << 6
    return {
        "slot": slot,
        "mouse_x": mouse_x,
        "mouse_y": mouse_y,
        "raw_x": raw_x,
        "raw_y": raw_y,
        "raw_x_hex": f"{raw_x:08x}",
        "raw_y_hex": f"{raw_y:08x}",
    }


def _contains_all(text: str, needles: list[str]) -> list[str]:
    return [needle for needle in needles if needle not in text]


def build_guard(
    *,
    run_plan_json: Path = DEFAULT_RUN_PLAN_JSON,
    surface_dump_script: Path = DEFAULT_SURFACE_DUMP_SCRIPT,
    extra_probe: Path = DEFAULT_EXTRA_PROBE,
) -> dict[str, Any]:
    failures: list[str] = []
    if not run_plan_json.exists():
        failures.append(f"missing transition run plan: {run_plan_json}")
        run_plan: dict[str, Any] = {}
    else:
        run_plan = load_json(run_plan_json)

    if not surface_dump_script.exists():
        failures.append(f"missing surface-dump script: {surface_dump_script}")
        script_text = ""
    else:
        script_text = surface_dump_script.read_text(encoding="utf-8-sig", errors="replace")

    if not extra_probe.exists():
        failures.append(f"missing transition extra probe: {extra_probe}")
        probe_text = ""
    else:
        probe_text = extra_probe.read_text(encoding="utf-8-sig", errors="replace")

    summary = run_plan.get("summary") or {}
    target_rows = [int(row) for row in (summary.get("target_rows") or [])]
    geometry = [row_geometry(slot) for slot in target_rows]
    commands = (run_plan.get("commands") or {}).get("hidden_transition_probes") or {}
    summary_commands = (run_plan.get("commands") or {}).get("summaries") or {}

    expected_script_needles = [
        "$loadMouseX = 320",
        "$loadMouseY = 166 + (22 * $LoadSlot)",
        "$loadMouseRawX = $loadMouseX -shl 6",
        "$loadMouseRawY = $loadMouseY -shl 6",
        "$extraProbeText = $extraProbeText.Replace('__LOAD_SLOT__'",
        "$extraProbeText = $extraProbeText.Replace('__LOAD_MOUSE_RAW_X__'",
        "$extraProbeText = $extraProbeText.Replace('__LOAD_MOUSE_RAW_Y__'",
    ]
    expected_probe_needles = [
        "__LOAD_SLOT__",
        "__LOAD_MOUSE_RAW_X__",
        "__LOAD_MOUSE_RAW_Y__",
        "LSTRANS_LATE_MOUSE_SET",
        "LSTRANS_LATE_FORCE_SELECT",
    ]
    missing_script = _contains_all(script_text, expected_script_needles)
    missing_probe = _contains_all(probe_text, expected_probe_needles)

    checks = {
        "run_plan_passed": run_plan.get("passed") is True,
        "target_rows_3_4_5": target_rows == [3, 4, 5],
        "surface_formula_present": not missing_script,
        "probe_placeholders_present": not missing_probe,
        "commands_row_specific": all(
            f"-LoadSlot {slot}" in commands.get(f"slot{slot}_hidden_transition_probe", "")
            and f"slot{slot}" in commands.get(f"slot{slot}_hidden_transition_probe", "")
            for slot in target_rows
        ),
        "summary_commands_require_entry": all(
            f"--expected-slot {slot}" in summary_commands.get(f"slot{slot}_summarize_transition", "")
            and "--require-entry" in summary_commands.get(f"slot{slot}_summarize_transition", "")
            and "--require-slot-match" in summary_commands.get(f"slot{slot}_summarize_transition", "")
            for slot in target_rows
        ),
        "non_promoting": run_plan.get("promotion_ready") is False
        and run_plan.get("stable_stage_should_change") is False,
    }
    for name, passed in checks.items():
        if not passed:
            failures.append(f"transition geometry guard failed: {name}")
    for needle in missing_script:
        failures.append(f"surface-dump script missing geometry token: {needle}")
    for needle in missing_probe:
        failures.append(f"transition probe missing placeholder/token: {needle}")

    return {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "passed": not failures,
        "runtime_policy": RUNTIME_POLICY,
        "guard_policy": GUARD_POLICY,
        "promotion_ready": False,
        "stable_stage_should_change": False,
        "source_artifacts": {
            "run_plan_json": str(run_plan_json),
            "surface_dump_script": str(surface_dump_script),
            "extra_probe": str(extra_probe),
        },
        "checks": checks,
        "summary": {
            "target_rows": target_rows,
            "row_geometry": geometry,
            "formula": "mouse_x=320; mouse_y=166+22*slot; raw=logical<<6",
            "run_plan_command_count": summary.get("command_count"),
            "run_plan_summary_command_count": summary.get("summary_command_count"),
        },
        "failures": failures,
    }


def write_markdown(path: Path, report: dict[str, Any]) -> None:
    summary = report.get("summary") or {}
    lines = [
        "# Load Slot Transition Geometry Guard",
        "",
        f"- Status: {status_text(bool(report.get('passed')))}",
        f"- Generated: `{report['generated_at']}`",
        f"- Runtime policy: {report['runtime_policy']}",
        f"- Guard policy: {report['guard_policy']}",
        f"- Promotion ready: `{report['promotion_ready']}`",
        f"- stable_stage_should_change: `{report['stable_stage_should_change']}`",
        f"- Formula: `{summary.get('formula')}`",
        "",
        "## Checks",
        "",
    ]
    lines.extend(f"- `{name}`: `{status_text(bool(passed))}`" for name, passed in report["checks"].items())
    lines.extend(["", "## Row Geometry", ""])
    for row in summary.get("row_geometry") or []:
        lines.append(
            "- slot `{slot}`: mouse=({mouse_x},{mouse_y}) raw=({raw_x_hex},{raw_y_hex})".format(
                **row
            )
        )
    if report.get("failures"):
        lines.extend(["", "## Failures", ""])
        lines.extend(f"- {failure}" for failure in report["failures"])
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def write_json(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-plan-json", type=Path, default=DEFAULT_RUN_PLAN_JSON)
    parser.add_argument("--surface-dump-script", type=Path, default=DEFAULT_SURFACE_DUMP_SCRIPT)
    parser.add_argument("--extra-probe", type=Path, default=DEFAULT_EXTRA_PROBE)
    parser.add_argument("--write-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--write-markdown", type=Path, default=DEFAULT_MD)
    parser.add_argument("--require-pass", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = build_guard(
        run_plan_json=args.run_plan_json,
        surface_dump_script=args.surface_dump_script,
        extra_probe=args.extra_probe,
    )
    write_json(args.write_json, report)
    write_markdown(args.write_markdown, report)
    print(f"overall: {status_text(bool(report['passed']))}")
    print(f"target-rows: {report['summary'].get('target_rows')}")
    for row in report["summary"].get("row_geometry") or []:
        print(
            "slot {slot}: mouse=({mouse_x},{mouse_y}) raw=({raw_x_hex},{raw_y_hex})".format(
                **row
            )
        )
    if report["failures"]:
        print("failures:")
        for failure in report["failures"]:
            print(f"  - {failure}")
    if args.require_pass and not report["passed"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
