#!/usr/bin/env python3
"""Guard right-bottom route/input marker ordering from archived no-popup runs.

This is a repo-only inspection helper. It reads existing CDB surface-dump logs
and summaries; it does not launch Clash95, CDB, wrappers, PowerShell, or any
visible window.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import right_bottom_grid_hit_summary


DEFAULT_PATCH_RUN = Path("captures/archive/cdb-surface-dump-20260712-160204")
DEFAULT_FULLSTART_RUN = Path("captures/archive/cdb-surface-dump-20260712-160351")
DEFAULT_GRID_RUN = Path("captures/archive/cdb-surface-dump-20260712-150240")
DEFAULT_JSON = Path("captures/current/right-bottom-route-timing-guard-current.json")
DEFAULT_MD = Path("captures/current/right-bottom-route-timing-guard-current.md")
EXPECTED_STAGE = (
    "gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-"
    "minimapright-dynvswitch-rightbottomcompose"
)
EXPECTED_GRID_ENTRY = [450, 73]
EXPECTED_GRID_RESULT = 0
RUNTIME_POLICY = "repo-only; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows"
GUARD_POLICY = (
    "right-bottom validation evidence must keep hidden route/copyback/grid marker ordering, "
    "candidate SHA agreement, 800x600 surfaces, and no AV/failure-exit rows"
)

ROUTE_SEQUENCE = (
    "SURFDUMP_PLAYGAME",
    "SURFDUMP_REDRAW",
    "APPOST_OWNER_SETUP_CALL",
    "APPOST_OWNER_FLAG_FORCED",
    "APPOST_WRITE_532150",
    "APPOST_WRITE_53214C",
    "APPOST_WRITE_532154",
    "APPOST_ACTION_CALL",
    "APPOST_433914_CALL_435BC0",
    "APPOST_OWNER_435BC0_ENTRY",
    "APPOST_WRITE_532218",
    "APPOST_WRITE_5322C8",
    "APPOST_PANEL_DRAW_4347A0",
    "APPOST_GRID_DRAW_434E20",
    "APPOST_STATUS_DRAW_435280",
    "APPOST_ACTION_BOX_435500",
    "TOOLTIP_ACTION_BOX",
    "APCOMP_ACTION_BOX_ENTRY",
    "APREDIR_SET_MAP_TARGET",
    "APREDIR_AFTER_BACKUP_COPY",
    "APREDIR_BEFORE_RESTORE",
    "APREDIR_AFTER_ACTION_BOX",
    "APREDIR_COPYBACK_SET_MAP_TARGET",
    "APREDIR_COPYBACK_AFTER_CALL",
    "APCOMP_COPYBACK_SAMPLES",
    "APPOST_OWNER_POLL_EXIT_ARM",
    "APPOST_SURFDUMP_READY",
    "SURFDUMP_READY",
    "SURFDUMP_HOST_READY",
)

ROUTE_REQUIRED_COUNTS = {
    "TOOLTIP_TEXT": 1,
    "TOOLTIP_TEXTFMT": 1,
    "BORDER_TOOLTIP_PRESENT_NULLPTR": 1,
    "APREDIR_COPYBACK_AFTER_CALL": 1,
    "APCOMP_COPYBACK_SAMPLES": 1,
}

GRID_SEQUENCE = (
    "SURFDUMP_PLAYGAME",
    "SURFDUMP_REDRAW",
    "RBGRID_OWNER_SETUP_CALL",
    "RBGRID_OWNER_FLAG_FORCED",
    "RBGRID_WRITE_532154",
    "RBGRID_ACTION_CALL",
    "RBGRID_433914_CALL_435BC0",
    "RBGRID_OWNER_435BC0_ENTRY",
    "RBGRID_WRITE_532218",
    "RBGRID_WRITE_5322C8",
    "RBGRID_PANEL_DRAW_4347A0",
    "RBGRID_GRID_DRAW_434E20",
    "RBGRID_STATUS_DRAW_435280",
    "RBGRID_ACTION_BOX_435500",
    "RBGRID_FORCE_NATIVE",
    "RBGRID_GRID_ROUTE_ENTRY",
    "RBGRID_GRID_GATE",
    "RBGRID_GRID_CALL",
    "RBGRID_GRID_ENTRY",
    "RBGRID_GRID_RESULT",
    "RBGRID_GRID_ACCEPT",
    "RBGRID_4338E0_AFTER_435BC0",
    "RBGRID_SURFDUMP_READY",
    "SURFDUMP_READY",
    "SURFDUMP_HOST_READY",
)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig", errors="replace")


def status_text(passed: bool) -> str:
    return "PASS" if passed else "FAIL"


def probe_template_matches(value: object, expected_rel: str) -> bool:
    normalized = str(value or "").replace("\\", "/").lower()
    expected = expected_rel.replace("\\", "/").lower()
    basename = expected.rsplit("/", 1)[-1]
    return expected in normalized or normalized.endswith("/" + basename) or normalized.endswith(basename)


def marker_occurrences(text: str, marker: str) -> list[int]:
    pattern = re.compile(rf"(?<![A-Za-z0-9_]){re.escape(marker)}(?![A-Za-z0-9_])")
    return [match.start() for match in pattern.finditer(text)]


def marker_positions(text: str, markers: tuple[str, ...]) -> dict[str, dict[str, Any]]:
    positions: dict[str, dict[str, Any]] = {}
    for marker in markers:
        occurrences = marker_occurrences(text, marker)
        positions[marker] = {
            "count": len(occurrences),
            "first": occurrences[0] if occurrences else None,
        }
    return positions


def check_order(label: str, text: str, sequence: tuple[str, ...]) -> tuple[dict[str, dict[str, Any]], list[str]]:
    positions = marker_positions(text, sequence)
    failures: list[str] = []
    for marker, record in positions.items():
        if record["count"] <= 0:
            failures.append(f"{label} missing marker: {marker}")

    for previous, current in zip(sequence, sequence[1:]):
        previous_pos = positions[previous]["first"]
        current_pos = positions[current]["first"]
        if previous_pos is None or current_pos is None:
            continue
        if previous_pos >= current_pos:
            failures.append(f"{label} marker order regression: {previous} must precede {current}")
    return positions, failures


def check_common_summary(label: str, summary: dict[str, Any], failures: list[str]) -> dict[str, Any]:
    surface = summary.get("Surface") or {}
    if summary.get("Passed") is not True:
        failures.append(f"{label} summary is not passing")
    if summary.get("HiddenDesktop") is not True:
        failures.append(f"{label} did not run on a hidden desktop")
    if summary.get("AllowVisibleDesktop") is True:
        failures.append(f"{label} allowed visible desktop fallback")
    if summary.get("UseDdrawProxy") is not True:
        failures.append(f"{label} did not use the DirectDraw proxy")
    if summary.get("Stage") != EXPECTED_STAGE:
        failures.append(f"{label} stage is {summary.get('Stage')!r}, expected {EXPECTED_STAGE}")
    if [surface.get("Width"), surface.get("Height")] != [800, 600]:
        failures.append(f"{label} surface was {[surface.get('Width'), surface.get('Height')]}, expected [800, 600]")
    return {
        "candidate_sha256": summary.get("CandidateSha256"),
        "stage": summary.get("Stage"),
        "hidden_desktop": summary.get("HiddenDesktop"),
        "surface": [surface.get("Width"), surface.get("Height")],
        "no_skip_start_anims": summary.get("NoSkipStartAnims"),
        "fast_forward_start_anims": summary.get("FastForwardStartAnims"),
        "skip_map_validation": summary.get("SkipMapValidation"),
        "extra_probe_template": summary.get("ExtraProbeTemplate"),
    }


def check_no_crash(label: str, text: str, failures: list[str]) -> None:
    lower = text.lower()
    if "c0000005" in lower or "access violation" in lower:
        failures.append(f"{label} log contains an access violation")
    if marker_occurrences(text, "AV_SURFDUMP"):
        failures.append(f"{label} log contains AV_SURFDUMP rows")


def check_route_run(run: Path, label: str, *, full_start: bool) -> dict[str, Any]:
    summary_path = run / "summary.json"
    log_path = run / "cdb-surface-dump.log"
    failures: list[str] = []
    if not summary_path.exists():
        return {"passed": False, "run": str(run), "failures": [f"{label} missing summary: {summary_path}"]}
    if not log_path.exists():
        return {"passed": False, "run": str(run), "failures": [f"{label} missing log: {log_path}"]}

    summary = load_json(summary_path)
    text = read_text(log_path)
    summary_record = check_common_summary(label, summary, failures)
    check_no_crash(label, text, failures)
    positions, order_failures = check_order(label, text, ROUTE_SEQUENCE)
    failures.extend(order_failures)

    for marker, minimum in ROUTE_REQUIRED_COUNTS.items():
        count = len(marker_occurrences(text, marker))
        if count < minimum:
            failures.append(f"{label} marker {marker} count {count} is below {minimum}")

    if full_start:
        if summary.get("NoSkipStartAnims") is not True:
            failures.append(f"{label} did not keep the full startup/resource path")
        if summary.get("FastForwardStartAnims"):
            failures.append(f"{label} unexpectedly fast-forwarded startup animations")
    else:
        if summary.get("FastForwardStartAnims") is not True:
            failures.append(f"{label} did not fast-forward startup animations")
    if summary.get("SkipMapValidation") is not True:
        failures.append(f"{label} was expected to skip map validation for controlled owner/action proof")
    if not probe_template_matches(
        summary.get("ExtraProbeTemplate"),
        "probes/cdb/map/clash95_post_owner_action_extra.cdb",
    ):
        failures.append(f"{label} did not record the post-owner action extra probe")

    return {
        "passed": not failures,
        "run": str(run),
        "summary": summary_record,
        "ordered_markers": list(ROUTE_SEQUENCE),
        "marker_counts": {marker: positions[marker]["count"] for marker in ROUTE_SEQUENCE},
        "failures": failures,
    }


def check_grid_run(run: Path) -> dict[str, Any]:
    summary_path = run / "summary.json"
    log_path = run / "cdb-surface-dump.log"
    failures: list[str] = []
    if not summary_path.exists():
        return {"passed": False, "run": str(run), "failures": [f"grid missing summary: {summary_path}"]}
    if not log_path.exists():
        return {"passed": False, "run": str(run), "failures": [f"grid missing log: {log_path}"]}

    summary = load_json(summary_path)
    text = read_text(log_path)
    summary_record = check_common_summary("grid", summary, failures)
    check_no_crash("grid", text, failures)
    positions, order_failures = check_order("grid", text, GRID_SEQUENCE)
    failures.extend(order_failures)

    if summary.get("FastForwardStartAnims") is not True:
        failures.append("grid did not fast-forward startup animations")
    if summary.get("SkipMapValidation") is not True:
        failures.append("grid was expected to skip map validation")
    if not probe_template_matches(
        summary.get("ExtraProbeTemplate"),
        "probes/cdb/ui/clash95_right_bottom_grid_hit_extra.cdb",
    ):
        failures.append("grid did not record the focused grid-hit extra probe")

    grid = right_bottom_grid_hit_summary.parse_log(log_path, EXPECTED_GRID_ENTRY, EXPECTED_GRID_RESULT)
    if grid.get("grid_hit_ok") is not True:
        failures.append("grid hit proof did not pass")
    if grid.get("last_grid_entry") != EXPECTED_GRID_ENTRY:
        failures.append(f"grid entry was {grid.get('last_grid_entry')}, expected {EXPECTED_GRID_ENTRY}")
    if grid.get("last_grid_result") != EXPECTED_GRID_RESULT:
        failures.append(f"grid result was {grid.get('last_grid_result')}, expected {EXPECTED_GRID_RESULT}")
    if int(grid.get("failure_exit_count") or 0):
        failures.append("grid proof used a failure exit")
    if int(grid.get("av_count") or 0):
        failures.append("grid proof has AV rows")

    return {
        "passed": not failures,
        "run": str(run),
        "summary": summary_record,
        "ordered_markers": list(GRID_SEQUENCE),
        "marker_counts": {marker: positions[marker]["count"] for marker in GRID_SEQUENCE},
        "grid_hit_ok": grid.get("grid_hit_ok"),
        "last_grid_entry": grid.get("last_grid_entry"),
        "last_grid_result": grid.get("last_grid_result"),
        "failure_exit_count": grid.get("failure_exit_count"),
        "av_count": grid.get("av_count"),
        "failures": failures,
    }


def build_guard(args: argparse.Namespace) -> dict[str, Any]:
    checks = {
        "patch_route": check_route_run(args.patch_run, "patch route", full_start=False),
        "fullstart_route": check_route_run(args.fullstart_run, "full-start route", full_start=True),
        "grid_route": check_grid_run(args.grid_run),
    }
    failures = [
        f"{name}: {failure}"
        for name, check in checks.items()
        for failure in check.get("failures", [])
    ]

    candidate_values = {
        (check.get("summary") or {}).get("candidate_sha256")
        for check in checks.values()
        if (check.get("summary") or {}).get("candidate_sha256")
    }
    if len(candidate_values) > 1:
        failures.append(f"right-bottom route candidate SHA values disagree: {sorted(candidate_values)}")

    return {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "passed": not failures,
        "runtime_policy": RUNTIME_POLICY,
        "guard_policy": GUARD_POLICY,
        "expected_stage": EXPECTED_STAGE,
        "candidate_sha256": next(iter(candidate_values), None),
        "checks": checks,
        "failures": failures,
    }


def print_guard(guard: dict[str, Any]) -> None:
    print(f"overall: {status_text(bool(guard.get('passed')))}")
    print(f"runtime-policy: {guard['runtime_policy']}")
    print(f"guard-policy: {guard['guard_policy']}")
    print(f"candidate-sha256: {guard.get('candidate_sha256')}")
    for name, check in guard["checks"].items():
        print(f"{name}: {status_text(bool(check.get('passed')))}")
    if guard.get("failures"):
        print("failures:")
        for failure in guard["failures"]:
            print(f"  - {failure}")


def write_markdown(path: Path, guard: dict[str, Any]) -> None:
    lines = [
        "# Right-Bottom Route Timing Guard",
        "",
        f"- Overall: {status_text(bool(guard.get('passed')))}",
        f"- Generated: `{guard['generated_at']}`",
        f"- Runtime policy: {guard['runtime_policy']}",
        f"- Guard policy: {guard['guard_policy']}",
        f"- Expected stage: `{guard['expected_stage']}`",
        f"- Candidate SHA-256: `{guard.get('candidate_sha256')}`",
        "",
        "## Checks",
        "",
    ]
    for name, check in guard["checks"].items():
        summary = check.get("summary") or {}
        lines.extend(
            [
                f"### {name.replace('_', ' ').title()}",
                "",
                f"- Status: {status_text(bool(check.get('passed')))}",
                f"- Run: `{check.get('run')}`",
                f"- Hidden desktop: `{summary.get('hidden_desktop')}`",
                f"- Surface: `{summary.get('surface')}`",
                f"- Fast-forward startup: `{summary.get('fast_forward_start_anims')}`",
                f"- Full startup path: `{summary.get('no_skip_start_anims')}`",
            ]
        )
        if name == "grid_route":
            lines.extend(
                [
                    f"- Grid hit ok: `{check.get('grid_hit_ok')}`",
                    f"- Grid entry/result: `{check.get('last_grid_entry')}` / `{check.get('last_grid_result')}`",
                    f"- Failure exits / AV rows: `{check.get('failure_exit_count')}` / `{check.get('av_count')}`",
                ]
            )
        lines.append(f"- Ordered markers: `{len(check.get('ordered_markers') or [])}`")
        if check.get("failures"):
            lines.append("- Failures:")
            lines.extend(f"  - {failure}" for failure in check["failures"])
        lines.append("")
    if guard.get("failures"):
        lines.extend(["## Failures", ""])
        lines.extend(f"- {failure}" for failure in guard["failures"])
        lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--patch-run", type=Path, default=DEFAULT_PATCH_RUN)
    parser.add_argument("--fullstart-run", type=Path, default=DEFAULT_FULLSTART_RUN)
    parser.add_argument("--grid-run", type=Path, default=DEFAULT_GRID_RUN)
    parser.add_argument("--write-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--write-markdown", type=Path, default=DEFAULT_MD)
    parser.add_argument("--require-pass", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    guard = build_guard(args)
    print_guard(guard)
    if args.write_json:
        args.write_json.parent.mkdir(parents=True, exist_ok=True)
        args.write_json.write_text(json.dumps(guard, indent=2) + "\n", encoding="utf-8")
    if args.write_markdown:
        write_markdown(args.write_markdown, guard)
    if args.require_pass and not guard["passed"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
