#!/usr/bin/env python3
"""Run the repo-only Clash95 HD map smoke matrix.

This is the compact no-runtime gate for the current HD map baseline. It checks:

- selected candidate executable has the current HD map patch stage applied;
- post-owner visibility evidence matrix passes for normal and forced-visible
  CDB surface dumps.

It does not launch Clash95, CDB, wrappers, or any GUI process.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import patch_stage_report
import post_owner_evidence_matrix


DEFAULT_STAGE = "gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch"
DEFAULT_CAPTURES_ROOT = Path("captures/archive")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def repo_relative(path: Path) -> str:
    try:
        return str(path.relative_to(Path.cwd()))
    except ValueError:
        return str(path)


def select_patch_exe(args: argparse.Namespace, post_owner_matrix: dict[str, Any]) -> Path | None:
    if args.patch_exe:
        return args.patch_exe
    forced_run = post_owner_matrix.get("forced_visible", {}).get("run")
    normal_run = post_owner_matrix.get("normal", {}).get("run")
    for run in (forced_run, normal_run):
        if not run:
            continue
        summary_path = Path(run) / "summary.json"
        if not summary_path.exists():
            continue
        candidate = load_json(summary_path).get("CandidatePath")
        if candidate:
            return Path(candidate)
    return None


def patch_counts(report: dict[str, Any]) -> dict[str, int]:
    if isinstance(report.get("patches"), dict):
        patches = report["patches"]
        patched = int(patches.get("patched", 0))
        original = int(patches.get("original", 0))
        unexpected = int(patches.get("unexpected", 0))
        total = int(patches.get("total") or patched + original + unexpected)
        return {
            "patched": patched,
            "original": original,
            "unexpected": unexpected,
            "total": total,
        }
    status_counts = report.get("status_counts") or {}
    patched = int(status_counts.get("patched", 0))
    original = int(status_counts.get("original", 0))
    unexpected = int(status_counts.get("unexpected", 0))
    total = int(report.get("patch_count") or patched + original + unexpected)
    return {
        "patched": patched,
        "original": original,
        "unexpected": unexpected,
        "total": total,
    }


def patch_stage_gate_from_report(report: dict[str, Any], stage: str, source: Path) -> dict[str, Any]:
    if isinstance(report.get("patch_stage"), dict):
        report = report["patch_stage"]
    gate = report.get("current_hd_map_gate") or {"passed": False, "failures": ["missing current_hd_map_gate"]}
    counts = patch_counts(report)
    failures = list(gate.get("failures") or [])
    report_stage = str(report.get("stage") or "")
    if report_stage != stage:
        failures.append(f"archived patch report stage mismatch: expected {stage}, got {report_stage}")
    if counts["unexpected"]:
        failures.append(f"archived patch report has {counts['unexpected']} unexpected records")
    return {
        "passed": bool(gate.get("passed")) and not failures,
        "exe": report.get("exe"),
        "source": str(source),
        "archived": True,
        "stage": report_stage or stage,
        "sha256": report.get("exe_sha256") or report.get("sha256"),
        "patches": counts,
        "map": report.get("map"),
        "current_hd_map_gate": gate,
        "failures": failures,
    }


def patch_stage_gate(exe: Path | None, stage: str) -> dict[str, Any]:
    if exe is None:
        return {
            "passed": False,
            "exe": None,
            "stage": stage,
            "failures": ["no candidate executable path was found"],
        }
    if not exe.exists():
        return {
            "passed": False,
            "exe": str(exe),
            "stage": stage,
            "failures": [f"candidate executable does not exist: {exe}"],
        }
    report = patch_stage_report.build_report(exe, stage)
    gate = report["current_hd_map_gate"]
    counts = patch_counts(report)
    return {
        "passed": bool(gate.get("passed")) and int(report["status_counts"].get("unexpected", 0)) == 0,
        "exe": str(exe),
        "source": str(exe),
        "archived": False,
        "stage": stage,
        "sha256": report.get("exe_sha256"),
        "patches": counts,
        "map": report.get("map"),
        "current_hd_map_gate": gate,
        "failures": list(gate.get("failures") or []),
    }


def build_matrix(args: argparse.Namespace) -> dict[str, Any]:
    post_args = argparse.Namespace(
        captures_root=args.captures_root,
        normal_run=args.normal_run,
        forced_run=args.forced_run,
    )
    post_owner = post_owner_evidence_matrix.build_matrix(post_args)
    if args.patch_report_json:
        patch_stage = patch_stage_gate_from_report(load_json(args.patch_report_json), args.stage, args.patch_report_json)
    else:
        exe = select_patch_exe(args, post_owner)
        patch_stage = patch_stage_gate(exe, args.stage)
    failures: list[str] = []
    if not patch_stage["passed"]:
        failures.extend(f"patch-stage: {failure}" for failure in patch_stage.get("failures", []))
    if not post_owner["passed"]:
        failures.append("post-owner evidence matrix failed")
    return {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "captures_root": str(args.captures_root),
        "patch_report_json": str(args.patch_report_json) if args.patch_report_json else None,
        "passed": not failures,
        "patch_stage": patch_stage,
        "post_owner_evidence": post_owner,
        "failures": failures,
    }


def print_matrix(matrix: dict[str, Any]) -> None:
    patch_stage = matrix["patch_stage"]
    post_owner = matrix["post_owner_evidence"]
    print(f"overall: {'PASS' if matrix['passed'] else 'FAIL'}")
    print(f"patch-stage: {'PASS' if patch_stage['passed'] else 'FAIL'}")
    print(f"  exe: {patch_stage.get('exe')}")
    if patch_stage.get("archived"):
        print(f"  archived_report: {patch_stage.get('source')}")
    print(f"  stage: {patch_stage.get('stage')}")
    print(f"  sha256: {patch_stage.get('sha256')}")
    patches = patch_stage.get("patches") or {}
    if patches:
        print(
            "  patches: patched={patched} original={original} unexpected={unexpected} total={total}".format(
                **patches
            )
        )
    print(f"post-owner-evidence: {'PASS' if post_owner['passed'] else 'FAIL'}")
    normal = post_owner.get("normal", {})
    forced = post_owner.get("forced_visible", {})
    print(f"  normal: {normal.get('run')} screenshot={normal.get('screenshot')}")
    print(f"  forced: {forced.get('run')} screenshot={forced.get('screenshot')}")
    if matrix.get("failures"):
        print("failures:")
        for failure in matrix["failures"]:
            print(f"  - {failure}")


def markdown_image(path: str | None, label: str) -> str:
    return f"![{label}]({path})" if path else "_No screenshot path recorded._"


def write_markdown(path: Path, matrix: dict[str, Any]) -> None:
    patch_stage = matrix["patch_stage"]
    post_owner = matrix["post_owner_evidence"]
    normal = post_owner.get("normal", {})
    forced = post_owner.get("forced_visible", {})
    patches = patch_stage.get("patches") or {}
    lines = [
        "# HD Map Smoke Matrix",
        "",
        f"- Overall: {'PASS' if matrix['passed'] else 'FAIL'}",
        f"- Generated: `{matrix['generated_at']}`",
        "",
        "## Patch Stage",
        "",
        f"- Status: {'PASS' if patch_stage['passed'] else 'FAIL'}",
        f"- Executable: `{patch_stage.get('exe')}`",
        f"- Source: `{patch_stage.get('source')}`",
        f"- Archived report: `{bool(patch_stage.get('archived'))}`",
        f"- Stage: `{patch_stage.get('stage')}`",
        f"- SHA-256: `{patch_stage.get('sha256')}`",
        "- Patches: patched={patched} original={original} unexpected={unexpected} total={total}".format(
            patched=patches.get("patched", "?"),
            original=patches.get("original", "?"),
            unexpected=patches.get("unexpected", "?"),
            total=patches.get("total", "?"),
        ),
        "",
        "## Post-Owner Evidence",
        "",
        f"- Status: {'PASS' if post_owner['passed'] else 'FAIL'}",
        f"- Normal run: `{normal.get('run', 'not found')}`",
        f"- Forced-visible run: `{forced.get('run', 'not found')}`",
        "",
        markdown_image(normal.get("screenshot"), "normal post-owner surface"),
        "",
        markdown_image(forced.get("screenshot"), "forced-visible post-owner surface"),
        "",
    ]
    if matrix.get("failures"):
        lines.extend(["## Failures", ""])
        lines.extend(f"- {failure}" for failure in matrix["failures"])
        lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--captures-root", type=Path, default=DEFAULT_CAPTURES_ROOT)
    parser.add_argument("--normal-run", type=Path)
    parser.add_argument("--forced-run", type=Path)
    parser.add_argument("--patch-exe", type=Path)
    parser.add_argument(
        "--patch-report-json",
        type=Path,
        help="use an archived tools/patch_stage_report.py JSON report instead of reading a local executable",
    )
    parser.add_argument("--stage", default=DEFAULT_STAGE)
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
