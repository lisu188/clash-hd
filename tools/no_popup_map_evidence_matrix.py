#!/usr/bin/env python3
"""Summarize no-popup Clash95 HD map evidence.

This pairs the two proof shapes used for the hidden-desktop CDB surface dump:

- normal run: dark active cells are accepted only when the visibility
  explanation gate proves they are fog/unexplored state;
- forced-visible run: debugger-visible edge cells must render as nonblank.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


RUN_RE = re.compile(r"^cdb-surface-dump-(\d{8})-(\d{6})$")


@dataclass
class Run:
    path: Path
    summary: dict[str, Any]
    mtime: float


def load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"_error": f"{type(exc).__name__}: {exc}"}


def run_dir_from_arg(path: Path) -> Path:
    if path.name.lower() == "summary.json":
        return path.parent
    return path


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


def scan_runs(captures_root: Path) -> list[Run]:
    runs: list[Run] = []
    for path in captures_root.glob("cdb-surface-dump-*/summary.json"):
        runs.append(load_run(path))
    return sorted(runs, key=lambda run: run_sort_key(run.path), reverse=True)


def as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def nested_list(row: dict[str, Any], *keys: str) -> list[Any]:
    current: Any = row
    for key in keys:
        if not isinstance(current, dict):
            return []
        current = current.get(key)
    return as_list(current)


def nested_bool(row: dict[str, Any], *keys: str) -> bool:
    current: Any = row
    for key in keys:
        if not isinstance(current, dict):
            return False
        current = current.get(key)
    return bool(current)


def normal_passed(summary: dict[str, Any]) -> bool:
    unexplained = nested_list(summary, "VisibilityExplainedGate", "UnexplainedBlankCells")
    return (
        bool(summary.get("Passed"))
        and not bool(summary.get("ForceVisibleEdges"))
        and bool(summary.get("VisibilityRequireExplained"))
        and nested_bool(summary, "VisibilityExplainedGate", "Required")
        and nested_bool(summary, "VisibilityExplainedGate", "Passed")
        and not unexplained
    )


def forced_passed(summary: dict[str, Any]) -> bool:
    gate = summary.get("ForcedVisibleGate") or {}
    return (
        bool(summary.get("Passed"))
        and bool(summary.get("ForceVisibleEdges"))
        and bool(gate.get("passed"))
        and int(summary.get("ForcedVisibleExitCode") or 0) == 0
        and not as_list(summary.get("CoverageBlankActiveCells"))
        and not as_list(gate.get("blank_active_cells"))
    )


def find_latest(runs: list[Run], predicate: Any) -> Run | None:
    for run in runs:
        if not run.summary.get("_error") and predicate(run.summary):
            return run
    return None


def summarize_normal(run: Run | None) -> dict[str, Any]:
    if run is None:
        return {"kind": "normal", "present": False, "passed": False, "failures": ["no passing normal run found"]}
    summary = run.summary
    blank = as_list(summary.get("CoverageBlankActiveCells"))
    unexplained = as_list(summary.get("VisibilityUnexplainedBlankCells")) or nested_list(
        summary, "VisibilityExplainedGate", "UnexplainedBlankCells"
    )
    gate = summary.get("VisibilityExplainedGate") or {}
    failures: list[str] = []
    if not summary.get("Passed"):
        failures.append("summary Passed is false")
    if summary.get("ForceVisibleEdges"):
        failures.append("run is forced-visible")
    if not summary.get("VisibilityRequireExplained"):
        failures.append("VisibilityRequireExplained is false")
    if not gate.get("Passed"):
        failures.append("VisibilityExplainedGate did not pass")
    if unexplained:
        failures.append("unexplained blank cells: " + ", ".join(str(item) for item in unexplained))
    return {
        "kind": "normal",
        "present": True,
        "passed": not failures,
        "run": str(run.path),
        "mtime": iso_mtime(run.mtime),
        "screenshot": summary.get("PngPath"),
        "candidate_sha256": summary.get("CandidateSha256"),
        "surface": summary.get("Surface"),
        "blank_active_count": len(blank),
        "unexplained_blank_count": len(unexplained),
        "visibility_status_counts": summary.get("VisibilityStatusCounts") or {},
        "visibility_gate": gate,
        "failures": failures,
    }


def summarize_forced(run: Run | None) -> dict[str, Any]:
    if run is None:
        return {
            "kind": "forced-visible",
            "present": False,
            "passed": False,
            "failures": ["no passing forced-visible run found"],
        }
    summary = run.summary
    gate = summary.get("ForcedVisibleGate") or {}
    blank = as_list(summary.get("CoverageBlankActiveCells"))
    failures: list[str] = []
    if not summary.get("Passed"):
        failures.append("summary Passed is false")
    if not summary.get("ForceVisibleEdges"):
        failures.append("run is not forced-visible")
    if not gate.get("passed"):
        failures.append("ForcedVisibleGate did not pass")
    if int(summary.get("ForcedVisibleExitCode") or 0) != 0:
        failures.append(f"ForcedVisibleExitCode={summary.get('ForcedVisibleExitCode')}")
    if blank:
        failures.append("coverage blank active cells: " + ", ".join(str(item) for item in blank))
    return {
        "kind": "forced-visible",
        "present": True,
        "passed": not failures,
        "run": str(run.path),
        "mtime": iso_mtime(run.mtime),
        "screenshot": summary.get("PngPath"),
        "candidate_sha256": summary.get("CandidateSha256"),
        "surface": summary.get("Surface"),
        "blank_active_count": len(blank),
        "forced_visible_exit_code": summary.get("ForcedVisibleExitCode"),
        "vedge_visret_count": gate.get("vedge_visret_count"),
        "vedge_post_count": gate.get("vedge_post_count"),
        "vedge_visret_nonzero_count": gate.get("vedge_visret_nonzero_count"),
        "vedge_post_nonblack_count": gate.get("vedge_post_nonblack_count"),
        "latest_visdump": gate.get("latest_visdump"),
        "forced_visible_gate": gate,
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
    if row["kind"] == "normal":
        counts = row.get("visibility_status_counts") or {}
        print(
            f"  blanks: active={row.get('blank_active_count')} "
            f"unexplained={row.get('unexplained_blank_count')} "
            f"visibility_status_counts={counts}"
        )
    else:
        latest = row.get("latest_visdump") or {}
        print(
            f"  forced: blanks={row.get('blank_active_count')} "
            f"visret={row.get('vedge_visret_count')} "
            f"post={row.get('vedge_post_count')} "
            f"visret_nonzero={row.get('vedge_visret_nonzero_count')} "
            f"post_nonblack={row.get('vedge_post_nonblack_count')} "
            f"map0={latest.get('map0')}"
        )
    if row.get("failures"):
        print("  failures:")
        for failure in row["failures"]:
            print(f"    - {failure}")


def print_matrix(matrix: dict[str, Any]) -> None:
    print(f"no-popup map evidence: {'PASS' if matrix['passed'] else 'FAIL'}")
    print(f"captures_root: {matrix['captures_root']}")
    print_section(matrix["normal"])
    print_section(matrix["forced_visible"])


def markdown_path(value: Any) -> str:
    if value is None:
        return ""
    return str(value).replace("\\", "/")


def markdown_status(row: dict[str, Any]) -> str:
    return "PASS" if row.get("passed") else "FAIL"


def render_markdown(matrix: dict[str, Any]) -> str:
    normal = matrix["normal"]
    forced = matrix["forced_visible"]
    normal_counts = normal.get("visibility_status_counts") or {}
    forced_visdump = forced.get("latest_visdump") or {}
    lines = [
        "# No-Popup Map Evidence",
        "",
        f"- Overall: {'PASS' if matrix['passed'] else 'FAIL'}",
        f"- Captures root: `{matrix['captures_root']}`",
        "",
        "## Normal Visibility-Explained Run",
        "",
        f"- Status: {markdown_status(normal)}",
        f"- Run: `{normal.get('run', '')}`",
        f"- Candidate SHA-256: `{normal.get('candidate_sha256', '')}`",
        f"- Blank active cells: {normal.get('blank_active_count')}",
        f"- Unexplained blank cells: {normal.get('unexplained_blank_count')}",
        f"- Visibility status counts: `{normal_counts}`",
        f"- Screenshot: `{normal.get('screenshot', '')}`",
        "",
        f"![normal no-popup surface]({markdown_path(normal.get('screenshot'))})",
        "",
        "## Forced-Visible Edge Run",
        "",
        f"- Status: {markdown_status(forced)}",
        f"- Run: `{forced.get('run', '')}`",
        f"- Candidate SHA-256: `{forced.get('candidate_sha256', '')}`",
        f"- Blank active cells: {forced.get('blank_active_count')}",
        f"- VEDGE visibility returns: {forced.get('vedge_visret_count')}",
        f"- VEDGE post samples: {forced.get('vedge_post_count')}",
        f"- Nonzero visibility returns: {forced.get('vedge_visret_nonzero_count')}",
        f"- Nonblack post samples: {forced.get('vedge_post_nonblack_count')}",
        f"- Latest visibility dump map0: `{forced_visdump.get('map0')}`",
        f"- Screenshot: `{forced.get('screenshot', '')}`",
        "",
        f"![forced-visible no-popup surface]({markdown_path(forced.get('screenshot'))})",
        "",
        "## Interpretation",
        "",
        (
            "Normal no-popup dark cells are accepted only because the same run "
            "explains them as visibility/fog state. The forced-visible proof "
            "shows the HD right/bottom cells draw when visibility permits them."
        ),
        "",
    ]
    for row in (normal, forced):
        if row.get("failures"):
            lines.extend([f"## {row['kind']} Failures", ""])
            lines.extend(f"- {failure}" for failure in row["failures"])
            lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--captures-root", type=Path, default=Path("captures"))
    parser.add_argument("--normal-run", type=Path, help="Normal run folder or summary.json")
    parser.add_argument("--forced-run", type=Path, help="Forced-visible run folder or summary.json")
    parser.add_argument("--write-json", type=Path)
    parser.add_argument("--write-markdown", type=Path)
    parser.add_argument("--require-pass", action="store_true", help="exit 2 unless both evidence rows pass")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    matrix = build_matrix(args)
    if args.write_json:
        args.write_json.parent.mkdir(parents=True, exist_ok=True)
        args.write_json.write_text(json.dumps(matrix, indent=2), encoding="ascii")
    if args.write_markdown:
        args.write_markdown.parent.mkdir(parents=True, exist_ok=True)
        args.write_markdown.write_text(render_markdown(matrix), encoding="ascii")
    print_matrix(matrix)
    if args.require_pass and not matrix["passed"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
