#!/usr/bin/env python3
"""Preview generated row-specific load-slot transition CDB probes.

This is a repo-only guard. It simulates the placeholder replacements that
scripts/cdb/run_cdb_surface_dump.ps1 applies to probes/cdb/menu/clash95_load_slot_entry_transition_extra.cdb
for rows 3-5, then verifies the generated CDB text is row-specific before any
hidden-desktop runtime pass is attempted.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import load_slot_transition_geometry_guard


DEFAULT_RUN_PLAN_JSON = Path("captures/current/load-slot-transition-run-plan-current.json")
DEFAULT_GEOMETRY_GUARD_JSON = Path("captures/current/load-slot-transition-geometry-guard-current.json")
DEFAULT_EXTRA_PROBE = Path("probes/cdb/menu/clash95_load_slot_entry_transition_extra.cdb")
DEFAULT_JSON = Path("captures/current/load-slot-transition-probe-preview-current.json")
DEFAULT_MD = Path("captures/current/load-slot-transition-probe-preview-current.md")

RUNTIME_POLICY = (
    "repo-only generated-probe preview; does not launch Clash95, CDB, wrappers, "
    "PowerShell, or visible windows"
)
GUARD_POLICY = (
    "passes only when generated row 3-5 transition probes have no placeholders, "
    "carry row-specific raw mouse values, and keep late select/accept conditions "
    "targeted at the requested slot"
)

PLACEHOLDERS = ("__LOAD_SLOT__", "__LOAD_MOUSE_RAW_X__", "__LOAD_MOUSE_RAW_Y__")
SLOT_CONDITION_RE = r"poi\(00543d7c\)\s*==\s*{slot}"
UNRESOLVED_PLACEHOLDER_RE = re.compile(r"__[A-Z0-9_]+__")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def status_text(passed: bool) -> str:
    return "PASS" if passed else "FAIL"


def generated_probe_text(template: str, geometry: dict[str, Any]) -> str:
    return (
        template.replace("__LOAD_SLOT__", str(geometry["slot"]))
        .replace("__LOAD_MOUSE_RAW_X__", geometry["raw_x_hex"])
        .replace("__LOAD_MOUSE_RAW_Y__", geometry["raw_y_hex"])
    )


def preview_for_slot(template: str, slot: int) -> dict[str, Any]:
    geometry = load_slot_transition_geometry_guard.row_geometry(slot)
    text = generated_probe_text(template, geometry)
    unresolved = sorted(set(UNRESOLVED_PLACEHOLDER_RE.findall(text)))
    slot_condition_count = len(re.findall(SLOT_CONDITION_RE.format(slot=slot), text))
    target_slot_count = text.count(f"target_slot={slot}")
    raw_x_count = text.lower().count(str(geometry["raw_x_hex"]).lower())
    raw_y_count = text.lower().count(str(geometry["raw_y_hex"]).lower())
    late_markers = {
        marker: marker in text
        for marker in (
            "LSTRANS_LOAD_MENU_ENTRY",
            "LSTRANS_LATE_MOUSE_SET",
            "LSTRANS_LATE_FORCE_SELECT",
            "LSTRANS_LATE_FORCE_ACCEPT",
            "LSTRANS_LOADSAVE",
            "LSTRANS_PLAYGAME",
        )
    }
    failures: list[str] = []
    if unresolved:
        failures.append(f"slot {slot} preview still has placeholders: {unresolved}")
    if slot_condition_count < 2:
        failures.append(f"slot {slot} preview does not parameterize both select/accept conditions")
    if target_slot_count < 5:
        failures.append(f"slot {slot} preview has too few target_slot={slot} markers")
    if raw_x_count < 2:
        failures.append(f"slot {slot} preview has too few raw-x replacements: {geometry['raw_x_hex']}")
    if raw_y_count < 2:
        failures.append(f"slot {slot} preview has too few raw-y replacements: {geometry['raw_y_hex']}")
    missing_markers = [marker for marker, present in late_markers.items() if not present]
    if missing_markers:
        failures.append(f"slot {slot} preview is missing markers: {missing_markers}")

    hardcoded_other_slots: list[int] = []
    for other in (3, 4, 5):
        if other != slot and re.search(SLOT_CONDITION_RE.format(slot=other), text):
            hardcoded_other_slots.append(other)
    if hardcoded_other_slots:
        failures.append(f"slot {slot} preview contains other slot conditions: {hardcoded_other_slots}")

    return {
        "slot": slot,
        "passed": not failures,
        "geometry": geometry,
        "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest().upper(),
        "line_count": len(text.splitlines()),
        "unresolved_placeholders": unresolved,
        "slot_condition_count": slot_condition_count,
        "target_slot_count": target_slot_count,
        "raw_x_count": raw_x_count,
        "raw_y_count": raw_y_count,
        "late_markers": late_markers,
        "failures": failures,
    }


def build_report(
    *,
    run_plan_json: Path = DEFAULT_RUN_PLAN_JSON,
    geometry_guard_json: Path = DEFAULT_GEOMETRY_GUARD_JSON,
    extra_probe: Path = DEFAULT_EXTRA_PROBE,
) -> dict[str, Any]:
    failures: list[str] = []
    if not run_plan_json.exists():
        failures.append(f"missing transition run plan: {run_plan_json}")
        run_plan: dict[str, Any] = {}
    else:
        run_plan = load_json(run_plan_json)
    if not geometry_guard_json.exists():
        failures.append(f"missing transition geometry guard: {geometry_guard_json}")
        geometry_guard: dict[str, Any] = {}
    else:
        geometry_guard = load_json(geometry_guard_json)
    if not extra_probe.exists():
        failures.append(f"missing transition extra probe: {extra_probe}")
        template = ""
    else:
        template = extra_probe.read_text(encoding="utf-8-sig", errors="replace")

    target_rows = [int(row) for row in ((run_plan.get("summary") or {}).get("target_rows") or [])]
    geometry_rows = [int(row.get("slot")) for row in ((geometry_guard.get("summary") or {}).get("row_geometry") or [])]
    previews = [preview_for_slot(template, slot) for slot in target_rows] if template else []

    checks = {
        "run_plan_passed": run_plan.get("passed") is True,
        "geometry_guard_passed": geometry_guard.get("passed") is True,
        "target_rows_3_4_5": target_rows == [3, 4, 5],
        "geometry_rows_match_target_rows": geometry_rows == target_rows,
        "non_promoting": run_plan.get("promotion_ready") is False
        and run_plan.get("stable_stage_should_change") is False,
        "all_previews_passed": all(preview["passed"] for preview in previews) and len(previews) == 3,
    }
    for name, passed in checks.items():
        if not passed:
            failures.append(f"transition probe preview failed: {name}")
    for preview in previews:
        failures.extend(preview["failures"])

    return {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "passed": not failures,
        "runtime_policy": RUNTIME_POLICY,
        "guard_policy": GUARD_POLICY,
        "promotion_ready": False,
        "stable_stage_should_change": False,
        "source_artifacts": {
            "run_plan_json": str(run_plan_json),
            "geometry_guard_json": str(geometry_guard_json),
            "extra_probe": str(extra_probe),
        },
        "checks": checks,
        "summary": {
            "target_rows": target_rows,
            "preview_count": len(previews),
            "preview_sha256": {str(preview["slot"]): preview["sha256"] for preview in previews},
            "row_geometry": [preview["geometry"] for preview in previews],
        },
        "previews": previews,
        "failures": failures,
    }


def write_markdown(path: Path, report: dict[str, Any]) -> None:
    summary = report.get("summary") or {}
    lines = [
        "# Load Slot Transition Probe Preview",
        "",
        f"- Status: {status_text(bool(report.get('passed')))}",
        f"- Generated: `{report['generated_at']}`",
        f"- Runtime policy: {report['runtime_policy']}",
        f"- Guard policy: {report['guard_policy']}",
        f"- Promotion ready: `{report['promotion_ready']}`",
        f"- stable_stage_should_change: `{report['stable_stage_should_change']}`",
        f"- Target rows: `{summary.get('target_rows')}`",
        f"- Preview count: `{summary.get('preview_count')}`",
        "",
        "## Checks",
        "",
    ]
    lines.extend(f"- `{name}`: `{status_text(bool(passed))}`" for name, passed in report["checks"].items())
    lines.extend(["", "## Previews", ""])
    for preview in report.get("previews") or []:
        geometry = preview["geometry"]
        lines.extend(
            [
                f"### Slot {preview['slot']}",
                "",
                f"- Status: `{status_text(bool(preview['passed']))}`",
                f"- SHA-256: `{preview['sha256']}`",
                f"- Mouse: `({geometry['mouse_x']},{geometry['mouse_y']})`",
                f"- Raw: `({geometry['raw_x_hex']},{geometry['raw_y_hex']})`",
                f"- Slot condition count: `{preview['slot_condition_count']}`",
                f"- Target-slot marker count: `{preview['target_slot_count']}`",
                f"- Raw-x replacement count: `{preview['raw_x_count']}`",
                f"- Raw-y replacement count: `{preview['raw_y_count']}`",
                "",
            ]
        )
    if report.get("failures"):
        lines.extend(["## Failures", ""])
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
    parser.add_argument("--geometry-guard-json", type=Path, default=DEFAULT_GEOMETRY_GUARD_JSON)
    parser.add_argument("--extra-probe", type=Path, default=DEFAULT_EXTRA_PROBE)
    parser.add_argument("--write-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--write-markdown", type=Path, default=DEFAULT_MD)
    parser.add_argument("--require-pass", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = build_report(
        run_plan_json=args.run_plan_json,
        geometry_guard_json=args.geometry_guard_json,
        extra_probe=args.extra_probe,
    )
    write_json(args.write_json, report)
    write_markdown(args.write_markdown, report)
    print(f"overall: {status_text(bool(report['passed']))}")
    print(f"target-rows: {report['summary'].get('target_rows')}")
    for preview in report.get("previews") or []:
        geometry = preview["geometry"]
        print(
            "slot {slot}: {status} raw=({raw_x_hex},{raw_y_hex}) sha256={sha}".format(
                slot=preview["slot"],
                status=status_text(bool(preview["passed"])),
                raw_x_hex=geometry["raw_x_hex"],
                raw_y_hex=geometry["raw_y_hex"],
                sha=preview["sha256"],
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
