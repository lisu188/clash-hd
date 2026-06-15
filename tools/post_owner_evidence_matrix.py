#!/usr/bin/env python3
"""Summarize post-owner HD map visibility evidence.

This pairs two CDB-only surface-dump proof shapes:

- normal post-owner run: the target right/bottom cells are blank only when the
  same-run visibility gate explains them as fog/unexplored state;
- seven-cell forced-visible run: the same cells render when CDB temporarily
  sets exactly their save-visibility bits.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


RUN_RE = re.compile(r"^cdb-surface-dump-(\d{8})-(\d{6})$")
DEFAULT_CAPTURES_ROOT = Path("captures/archive")
EXTRA_PROBE_NAME = "probes/cdb/map/clash95_post_owner_tile_visibility_extra.cdb"
LEGACY_EXTRA_PROBE_NAME = "clash95_post_owner_tile_visibility_extra.cdb"
TARGET_CELLS = ("r6c10", "r6c11", "r7c10", "r7c11", "r8c0", "r8c10", "r8c11")


@dataclass
class Run:
    path: Path
    summary: dict[str, Any]
    mtime: float


def as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def nested(row: dict[str, Any], *keys: str) -> Any:
    current: Any = row
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def nested_bool(row: dict[str, Any], *keys: str) -> bool:
    return bool(nested(row, *keys))


def int_value(value: Any, default: int = 0) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"_error": f"{type(exc).__name__}: {exc}"}


def run_dir_from_arg(path: Path) -> Path:
    return path.parent if path.name.lower() == "summary.json" else path


def run_sort_key(path: Path) -> tuple[str, float]:
    match = RUN_RE.match(path.name)
    stamp = f"{match.group(1)}{match.group(2)}" if match else ""
    try:
        mtime = path.stat().st_mtime
    except OSError:
        mtime = 0.0
    return stamp, mtime


def iso_mtime(stamp: float) -> str:
    if not stamp:
        return ""
    return datetime.fromtimestamp(stamp, tz=timezone.utc).astimezone().isoformat(timespec="seconds")


def load_run(path: Path) -> Run:
    run_dir = run_dir_from_arg(path)
    summary_path = run_dir / "summary.json"
    try:
        mtime = summary_path.stat().st_mtime
    except OSError:
        mtime = 0.0
    return Run(path=run_dir, summary=load_json(summary_path), mtime=mtime)


def screenshot_path(run: Run, summary: dict[str, Any]) -> str | None:
    png = summary.get("PngPath")
    if png and Path(png).exists():
        return str(Path(png).resolve())
    archived_png = run.path / "surface.png"
    if archived_png.exists():
        return str(archived_png.resolve())
    return png


def scan_runs(captures_root: Path) -> list[Run]:
    runs = [load_run(path) for path in captures_root.glob("cdb-surface-dump-*/summary.json")]
    return sorted(runs, key=lambda run: run_sort_key(run.path), reverse=True)


def uses_post_owner_probe(summary: dict[str, Any]) -> bool:
    probe = str(summary.get("ExtraProbeTemplate") or "").replace("\\", "/").lower()
    return probe.endswith(EXTRA_PROBE_NAME.lower()) or probe.endswith(LEGACY_EXTRA_PROBE_NAME.lower())


def normal_passed(summary: dict[str, Any]) -> bool:
    blank = [str(cell) for cell in as_list(summary.get("CoverageBlankActiveCells"))]
    unexplained = as_list(summary.get("VisibilityUnexplainedBlankCells")) or as_list(
        nested(summary, "VisibilityExplainedGate", "UnexplainedBlankCells")
    )
    status_counts = summary.get("VisibilityStatusCounts") or {}
    return (
        bool(summary.get("Passed"))
        and uses_post_owner_probe(summary)
        and not bool(summary.get("ForceVisibleEdges"))
        and not bool(summary.get("PostOwnerForceVisibleSeven"))
        and bool(summary.get("VisibilityRequireExplained"))
        and nested_bool(summary, "VisibilityExplainedGate", "Required")
        and nested_bool(summary, "VisibilityExplainedGate", "Passed")
        and not unexplained
        and set(TARGET_CELLS).issubset(set(blank))
        and int(status_counts.get("visibility_zero") or 0) >= len(TARGET_CELLS)
    )


def forced_passed(summary: dict[str, Any]) -> bool:
    gate = summary.get("PostOwnerForcedVisibleGate") or {}
    return (
        bool(summary.get("Passed"))
        and uses_post_owner_probe(summary)
        and bool(summary.get("PostOwnerForceVisibleSeven"))
        and int_value(summary.get("PostOwnerForcedVisibleExitCode"), -1) == 0
        and bool(gate.get("passed"))
        and not as_list(summary.get("CoverageBlankActiveCells"))
        and not as_list(gate.get("missing_cells"))
        and not as_list(gate.get("zero_hit_cells"))
        and not as_list(gate.get("still_blank_cells"))
    )


def find_latest(runs: list[Run], predicate: Callable[[dict[str, Any]], bool]) -> Run | None:
    for run in runs:
        if not run.summary.get("_error") and predicate(run.summary):
            return run
    return None


def summarize_normal(run: Run | None) -> dict[str, Any]:
    if run is None:
        return {"kind": "normal-post-owner", "present": False, "passed": False, "failures": ["no passing normal post-owner run found"]}
    summary = run.summary
    blank = [str(cell) for cell in as_list(summary.get("CoverageBlankActiveCells"))]
    unexplained = as_list(summary.get("VisibilityUnexplainedBlankCells")) or as_list(
        nested(summary, "VisibilityExplainedGate", "UnexplainedBlankCells")
    )
    gate = summary.get("VisibilityExplainedGate") or {}
    status_counts = summary.get("VisibilityStatusCounts") or {}
    failures: list[str] = []
    if not normal_passed(summary):
        if not summary.get("Passed"):
            failures.append("summary Passed is false")
        if not uses_post_owner_probe(summary):
            failures.append("run does not use the post-owner tile visibility probe")
        if summary.get("PostOwnerForceVisibleSeven") or summary.get("ForceVisibleEdges"):
            failures.append("run is a forced-visible run")
        if not gate.get("Passed"):
            failures.append("VisibilityExplainedGate did not pass")
        if unexplained:
            failures.append("unexplained blank cells: " + ", ".join(str(item) for item in unexplained))
        missing_targets = sorted(set(TARGET_CELLS) - set(blank))
        if missing_targets:
            failures.append("missing expected blank target cells: " + ", ".join(missing_targets))
        if int(status_counts.get("visibility_zero") or 0) < len(TARGET_CELLS):
            failures.append(f"visibility_zero count too low: {status_counts.get('visibility_zero')}")
    return {
        "kind": "normal-post-owner",
        "present": True,
        "passed": not failures,
        "run": str(run.path),
        "mtime": iso_mtime(run.mtime),
        "screenshot": screenshot_path(run, summary),
        "candidate_sha256": summary.get("CandidateSha256"),
        "surface": summary.get("Surface"),
        "blank_active_cells": blank,
        "target_blank_cells": [cell for cell in TARGET_CELLS if cell in blank],
        "visibility_status_counts": status_counts,
        "visibility_gate": gate,
        "failures": failures,
    }


def summarize_forced(run: Run | None) -> dict[str, Any]:
    if run is None:
        return {"kind": "post-owner-forced-visible", "present": False, "passed": False, "failures": ["no passing post-owner forced-visible run found"]}
    summary = run.summary
    gate = summary.get("PostOwnerForcedVisibleGate") or {}
    blank = as_list(summary.get("CoverageBlankActiveCells"))
    failures: list[str] = []
    if not forced_passed(summary):
        if not summary.get("Passed"):
            failures.append("summary Passed is false")
        if not uses_post_owner_probe(summary):
            failures.append("run does not use the post-owner tile visibility probe")
        if not summary.get("PostOwnerForceVisibleSeven"):
            failures.append("PostOwnerForceVisibleSeven is false")
        if int_value(summary.get("PostOwnerForcedVisibleExitCode"), -1) != 0:
            failures.append(f"PostOwnerForcedVisibleExitCode={summary.get('PostOwnerForcedVisibleExitCode')}")
        if not gate.get("passed"):
            failures.append("PostOwnerForcedVisibleGate did not pass")
        if blank:
            failures.append("coverage blank active cells remain: " + ", ".join(str(item) for item in blank))
        for key in ("missing_cells", "zero_hit_cells", "still_blank_cells"):
            values = as_list(gate.get(key))
            if values:
                failures.append(f"{key}: " + ", ".join(str(item) for item in values))
    return {
        "kind": "post-owner-forced-visible",
        "present": True,
        "passed": not failures,
        "run": str(run.path),
        "mtime": iso_mtime(run.mtime),
        "screenshot": screenshot_path(run, summary),
        "candidate_sha256": summary.get("CandidateSha256"),
        "surface": summary.get("Surface"),
        "blank_active_cells": blank,
        "post_owner_forced_visible_exit_code": summary.get("PostOwnerForcedVisibleExitCode"),
        "force_rows": gate.get("force_rows"),
        "force_done_rows": gate.get("force_done_rows"),
        "action_rows": gate.get("action_rows"),
        "ready_rows": gate.get("ready_rows"),
        "missing_cells": as_list(gate.get("missing_cells")),
        "zero_hit_cells": as_list(gate.get("zero_hit_cells")),
        "still_blank_cells": as_list(gate.get("still_blank_cells")),
        "post_owner_forced_visible_gate": gate,
        "failures": failures,
    }


def build_matrix(args: argparse.Namespace) -> dict[str, Any]:
    runs = scan_runs(args.captures_root)
    normal_run = load_run(args.normal_run) if args.normal_run else find_latest(runs, normal_passed)
    forced_run = load_run(args.forced_run) if args.forced_run else find_latest(runs, forced_passed)
    normal = summarize_normal(normal_run)
    forced = summarize_forced(forced_run)
    return {
        "captures_root": str(args.captures_root),
        "normal": normal,
        "forced_visible": forced,
        "passed": bool(normal["passed"] and forced["passed"]),
    }


def print_section(row: dict[str, Any]) -> None:
    status = "PASS" if row["passed"] else "FAIL"
    print(f"{row['kind']}: {status}")
    if row.get("run"):
        print(f"  run: {row['run']}")
    if row.get("screenshot"):
        print(f"  screenshot: {row['screenshot']}")
    if row.get("candidate_sha256"):
        print(f"  candidate_sha256: {row['candidate_sha256']}")
    surface = row.get("surface") or {}
    if surface:
        print(f"  surface: {surface.get('Width')}x{surface.get('Height')} bytes={surface.get('Bytes')}")
    if row["kind"] == "normal-post-owner":
        print(
            "  normal: blanks={blank_count} target_blanks={target_count} visibility_status_counts={counts}".format(
                blank_count=len(row.get("blank_active_cells") or []),
                target_count=len(row.get("target_blank_cells") or []),
                counts=row.get("visibility_status_counts") or {},
            )
        )
    else:
        print(
            "  forced: blanks={blank_count} force={force_rows} done={force_done_rows} action={action_rows} ready={ready_rows}".format(
                blank_count=len(row.get("blank_active_cells") or []),
                force_rows=row.get("force_rows"),
                force_done_rows=row.get("force_done_rows"),
                action_rows=row.get("action_rows"),
                ready_rows=row.get("ready_rows"),
            )
        )
    if row.get("failures"):
        print("  failures:")
        for failure in row["failures"]:
            print(f"    - {failure}")


def print_matrix(matrix: dict[str, Any]) -> None:
    print(f"captures_root: {matrix['captures_root']}")
    print_section(matrix["normal"])
    print_section(matrix["forced_visible"])
    print(f"overall: {'PASS' if matrix['passed'] else 'FAIL'}")


def markdown_image(path: str | None, label: str) -> str:
    return f"![{label}]({path})" if path else "_No screenshot path recorded._"


def write_markdown(path: Path, matrix: dict[str, Any]) -> None:
    normal = matrix["normal"]
    forced = matrix["forced_visible"]
    lines = [
        "# Post-Owner Visibility Evidence Matrix",
        "",
        f"- Overall: {'PASS' if matrix['passed'] else 'FAIL'}",
        f"- Captures root: `{matrix['captures_root']}`",
        "",
        "## Normal Visibility-Zero Proof",
        "",
        f"- Status: {'PASS' if normal['passed'] else 'FAIL'}",
        f"- Run: `{normal.get('run', 'not found')}`",
        f"- Blank active cells: {', '.join(normal.get('blank_active_cells') or []) if normal.get('blank_active_cells') else 'none'}",
        f"- Visibility status counts: `{normal.get('visibility_status_counts') or {}}`",
        "",
        markdown_image(normal.get("screenshot"), "normal post-owner surface"),
        "",
        "## Seven-Cell Forced-Visible Proof",
        "",
        f"- Status: {'PASS' if forced['passed'] else 'FAIL'}",
        f"- Run: `{forced.get('run', 'not found')}`",
        f"- Blank active cells: {', '.join(str(item) for item in forced.get('blank_active_cells') or []) if forced.get('blank_active_cells') else 'none'}",
        f"- Gate counts: force={forced.get('force_rows')} done={forced.get('force_done_rows')} action={forced.get('action_rows')} ready={forced.get('ready_rows')}",
        "",
        markdown_image(forced.get("screenshot"), "forced-visible post-owner surface"),
        "",
    ]
    if normal.get("failures") or forced.get("failures"):
        lines.extend(["## Failures", ""])
        for row in (normal, forced):
            for failure in row.get("failures") or []:
                lines.append(f"- {row['kind']}: {failure}")
        lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--captures-root", type=Path, default=DEFAULT_CAPTURES_ROOT)
    parser.add_argument("--normal-run", type=Path)
    parser.add_argument("--forced-run", type=Path)
    parser.add_argument("--write-json", type=Path)
    parser.add_argument("--write-markdown", type=Path)
    parser.add_argument("--require-pass", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    matrix = build_matrix(args)
    print_matrix(matrix)
    if args.write_json:
        args.write_json.parent.mkdir(parents=True, exist_ok=True)
        args.write_json.write_text(json.dumps(matrix, indent=2) + "\n", encoding="utf-8")
    if args.write_markdown:
        write_markdown(args.write_markdown, matrix)
    if args.require_pass and not matrix["passed"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
