#!/usr/bin/env python3
"""Recheck the read-only castle overview baseline artifacts.

This is a repo-only aggregator for the current full-overview visual baseline, the
barracks controlled-stop baseline, and the latest castle overview matrix. It
does not launch Clash95, CDB, wrappers, PowerShell, or any visible window.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import castle_barracks_action_click_summary
import castle_overview_evidence_matrix
import castle_overview_gate


DEFAULT_OVERVIEW_BASELINE_RUN = Path("captures/archive/cdb-surface-dump-20260515-105041")
DEFAULT_BARRACKS_BASELINE_RUN = Path("captures/archive/cdb-surface-dump-20260512-082418")
DEFAULT_JSON = Path("captures/current/castle-overview-baseline-recheck-current.json")
DEFAULT_MD = Path("captures/current/castle-overview-baseline-recheck-current.md")
RUNTIME_POLICY = "repo-only; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows"


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def status_text(passed: bool) -> str:
    return "PASS" if passed else "FAIL"


def hex_byte(value: Any) -> str:
    if value is None:
        return "none"
    return f"0x{int(value):02X}"


def targets_completion_ok(targets: list[dict[str, Any]]) -> bool:
    return bool(targets) and all(target.get("completion_ok") is True for target in targets)


def target_completion_text(targets: list[dict[str, Any]]) -> str:
    if not targets:
        return "none"
    return ", ".join(
        "index {index} {command}/{raw} completion={completion}".format(
            index=target.get("index"),
            command=hex_byte(target.get("command")),
            raw=hex_byte(target.get("raw")),
            completion=bool(target.get("completion_ok")),
        )
        for target in targets
    )


def apply_latest_matrix_completion_gate(matrix: dict[str, Any]) -> dict[str, Any]:
    updated = dict(matrix)
    visible_targets = updated.get("visible_multihit_targets") or []
    dormant_targets = updated.get("dormant_multihit_targets") or []
    visible_completion_ok = targets_completion_ok(visible_targets)
    dormant_completion_ok = targets_completion_ok(dormant_targets)
    failures = list(updated.get("failures", []))
    for passed, message in (
        (
            visible_completion_ok,
            "latest matrix visible-command multi-hit target-done completion proof is missing",
        ),
        (
            dormant_completion_ok,
            "latest matrix dormant-command multi-hit target-done completion proof is missing",
        ),
    ):
        if not passed and message not in failures:
            failures.append(message)
    updated["visible_multihit_completion_ok"] = visible_completion_ok
    updated["dormant_multihit_completion_ok"] = dormant_completion_ok
    updated["failures"] = failures
    updated["passed"] = bool(updated.get("passed")) and not failures
    return updated


def repo_relative(path: Path | str | None) -> str | None:
    if path is None:
        return None
    candidate = Path(path)
    try:
        return str(candidate.relative_to(Path.cwd()))
    except ValueError:
        return str(candidate)


def build_barracks_controlled_stop(run: Path) -> dict[str, Any]:
    log = run / "cdb-surface-dump.log"
    failures: list[str] = []
    if not log.exists():
        return {
            "passed": False,
            "run": str(run),
            "log": str(log),
            "failures": [f"missing barracks baseline log: {log}"],
        }

    summary = castle_barracks_action_click_summary.parse_log(
        log,
        expected_desc=0x005151CF,
        expected_callback=0x004356C0,
    )
    ready = bool(
        summary["marker_counts"].get("APBARRACKS_SURFDUMP_READY")
        or summary["marker_counts"].get("SURFDUMP_READY")
    )
    if not ready:
        failures.append("barracks baseline surface-ready marker was not observed")
    if not summary.get("descriptor_click_ok"):
        failures.append("barracks baseline descriptor click was not observed")
    if not summary.get("controlled_4356c0_ok"):
        failures.append("barracks baseline controlled 004356c0 stop was not observed")
    if summary.get("failure_exit_count"):
        failures.append("barracks baseline used a failure exit")
    if summary.get("av_count"):
        failures.append("barracks baseline AV rows were observed")

    return {
        "passed": not failures,
        "run": str(run),
        "log": str(log),
        "ready": ready,
        "descriptor_click_ok": summary.get("descriptor_click_ok"),
        "controlled_4356c0_ok": summary.get("controlled_4356c0_ok"),
        "failure_exit_count": summary.get("failure_exit_count"),
        "av_count": summary.get("av_count"),
        "classification": summary.get("classification", []),
        "failures": failures,
    }


def build_latest_matrix(args: argparse.Namespace) -> dict[str, Any]:
    matrix_args = argparse.Namespace(
        stage=args.stage,
        patch_exe=args.patch_exe,
        patch_report_json=getattr(args, "patch_report_json", None),
        overview_run=args.latest_overview_run,
        barracks_run=args.barracks_run,
        focused_hitbox_run=args.focused_hitbox_run,
        visible_multihit_run=args.visible_multihit_run,
        owner_records_raw=args.owner_records_raw,
        forced_hitmap_raw=args.forced_hitmap_raw,
        dormant_multihit_run=args.dormant_multihit_run,
        threshold=args.threshold,
        max_echo_percent=args.max_echo_percent,
    )
    matrix = castle_overview_evidence_matrix.build_matrix(matrix_args)
    checks = matrix.get("checks", {})
    patch_stage = checks.get("patch_stage", {})
    visible_targets = (checks.get("visible_multihit") or {}).get("targets", [])
    dormant_targets = (checks.get("dormant_multihit") or {}).get("targets", [])
    return apply_latest_matrix_completion_gate({
        "passed": bool(matrix.get("passed")),
        "stage": matrix.get("stage"),
        "promotion_status": matrix.get("promotion_status"),
        "candidate_sha256": patch_stage.get("sha256"),
        "patches": patch_stage.get("patches"),
        "visible_multihit_targets": visible_targets,
        "dormant_multihit_targets": dormant_targets,
        "failures": matrix.get("failures", []),
    })


def build_recheck(args: argparse.Namespace) -> dict[str, Any]:
    overview_gate = castle_overview_gate.build_gate(
        run_dir=args.overview_run,
        expected_commands=castle_overview_gate.DEFAULT_COMMANDS,
        threshold=args.threshold,
        max_echo_percent=args.max_echo_percent,
        barracks_run=args.barracks_run,
    )
    barracks_controlled_stop = build_barracks_controlled_stop(args.barracks_run)
    latest_matrix = apply_latest_matrix_completion_gate(build_latest_matrix(args))

    checks = {
        "overview_visual_baseline": {
            "passed": bool(overview_gate.get("passed")),
            "run": overview_gate.get("run_dir"),
            "screenshot": overview_gate.get("screenshot"),
            "commands": (overview_gate.get("catalog") or {}).get("commands", []),
            "surface_size": ((overview_gate.get("catalog") or {}).get("last_surface") or {}).get("size"),
            "overview_post_draw_size": (
                (overview_gate.get("catalog") or {}).get("last_overview_post_draw") or {}
            ).get("main_size"),
            "centered_geometry_passed": (
                ((overview_gate.get("geometry") or {}).get("gate") or {}).get("passed")
            ),
            "barracks_baseline_passed": (
                (overview_gate.get("barracks_baseline") or {}).get("passed")
            ),
            "failures": overview_gate.get("failures", []),
        },
        "barracks_controlled_stop": barracks_controlled_stop,
        "latest_castle_overview_matrix": latest_matrix,
    }
    failures: list[str] = []
    for name, check in checks.items():
        if not check.get("passed"):
            check_failures = check.get("failures") or ["failed without a detailed reason"]
            failures.extend(f"{name}: {failure}" for failure in check_failures)

    return {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "passed": not failures,
        "runtime_policy": RUNTIME_POLICY,
        "checks": checks,
        "failures": failures,
    }


def write_markdown(path: Path, recheck: dict[str, Any]) -> None:
    checks = recheck["checks"]
    overview = checks["overview_visual_baseline"]
    barracks = checks["barracks_controlled_stop"]
    matrix = checks["latest_castle_overview_matrix"]
    patches = matrix.get("patches") or {}
    lines = [
        "# Castle Overview Baseline Recheck",
        "",
        f"- Overall: {status_text(bool(recheck.get('passed')))}",
        f"- Generated: `{recheck['generated_at']}`",
        f"- Runtime policy: {recheck['runtime_policy']}",
        "",
        "## Overview Visual Baseline",
        "",
        f"- Status: {status_text(bool(overview.get('passed')))}",
        f"- Run: `{repo_relative(overview.get('run'))}`",
        f"- Surface size: `{overview.get('surface_size')}`",
        f"- Overview post-draw size: `{overview.get('overview_post_draw_size')}`",
        f"- Commands: {', '.join(overview.get('commands') or [])}",
        f"- Centered geometry: {status_text(bool(overview.get('centered_geometry_passed')))}",
        f"- Barracks baseline through overview gate: {status_text(bool(overview.get('barracks_baseline_passed')))}",
        "",
        "## Barracks Controlled Stop Baseline",
        "",
        f"- Status: {status_text(bool(barracks.get('passed')))}",
        f"- Run: `{repo_relative(barracks.get('run'))}`",
        f"- Ready: `{barracks.get('ready')}`",
        f"- Descriptor click: `{barracks.get('descriptor_click_ok')}`",
        f"- Controlled 004356c0 stop: `{barracks.get('controlled_4356c0_ok')}`",
        f"- Failure exits: `{barracks.get('failure_exit_count')}`",
        f"- Access violations: `{barracks.get('av_count')}`",
        "",
        "## Latest Castle Overview Matrix",
        "",
        f"- Status: {status_text(bool(matrix.get('passed')))}",
        f"- Stage: `{matrix.get('stage')}`",
        f"- Promotion status: `{matrix.get('promotion_status')}`",
        f"- Candidate SHA-256: `{matrix.get('candidate_sha256')}`",
        "- Patches: patched={patched} original={original} unexpected={unexpected} total={total}".format(
            patched=patches.get("patched", "?"),
            original=patches.get("original", "?"),
            unexpected=patches.get("unexpected", "?"),
            total=patches.get("total", "?"),
        ),
        f"- Visible target completion: {target_completion_text(matrix.get('visible_multihit_targets') or [])}",
        f"- Dormant target completion: {target_completion_text(matrix.get('dormant_multihit_targets') or [])}",
        "",
    ]
    if recheck.get("failures"):
        lines.extend(["## Failures", ""])
        lines.extend(f"- {failure}" for failure in recheck["failures"])
        lines.append("")
    screenshot = overview.get("screenshot")
    if screenshot:
        lines.extend(
            [
                "## Screenshot",
                "",
                f"![castle overview baseline]({Path(screenshot).resolve()})",
                "",
            ]
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def print_recheck(recheck: dict[str, Any]) -> None:
    print(f"overall: {status_text(bool(recheck.get('passed')))}")
    print(f"runtime-policy: {recheck['runtime_policy']}")
    for name, check in recheck["checks"].items():
        print(f"{name}: {status_text(bool(check.get('passed')))}")
        if name == "overview_visual_baseline":
            print(f"  run: {check.get('run')}")
            print(f"  surface_size: {check.get('surface_size')}")
            print(f"  commands: {', '.join(check.get('commands') or [])}")
        if name == "barracks_controlled_stop":
            print(f"  descriptor_click_ok: {check.get('descriptor_click_ok')}")
            print(f"  controlled_4356c0_ok: {check.get('controlled_4356c0_ok')}")
            print(f"  av_count: {check.get('av_count')}")
        if name == "latest_castle_overview_matrix":
            print(f"  promotion_status: {check.get('promotion_status')}")
            print(f"  candidate_sha256: {check.get('candidate_sha256')}")
            print(
                "  visible_target_completion: "
                f"{target_completion_text(check.get('visible_multihit_targets') or [])}"
            )
            print(
                "  dormant_target_completion: "
                f"{target_completion_text(check.get('dormant_multihit_targets') or [])}"
            )
        if check.get("failures"):
            for failure in check["failures"]:
                print(f"  - {failure}")
    if recheck.get("failures"):
        print("failures:")
        for failure in recheck["failures"]:
            print(f"  - {failure}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--overview-run", type=Path, default=DEFAULT_OVERVIEW_BASELINE_RUN)
    parser.add_argument("--barracks-run", type=Path, default=DEFAULT_BARRACKS_BASELINE_RUN)
    parser.add_argument("--stage", default=castle_overview_evidence_matrix.DEFAULT_STAGE)
    parser.add_argument("--patch-exe", type=Path)
    parser.add_argument("--patch-report-json", type=Path)
    parser.add_argument("--latest-overview-run", type=Path, default=castle_overview_evidence_matrix.DEFAULT_OVERVIEW_RUN)
    parser.add_argument("--focused-hitbox-run", type=Path, default=castle_overview_evidence_matrix.DEFAULT_FOCUSED_HITBOX_RUN)
    parser.add_argument("--visible-multihit-run", type=Path, default=castle_overview_evidence_matrix.DEFAULT_VISIBLE_MULTI_RUN)
    parser.add_argument("--owner-records-raw", type=Path, default=castle_overview_evidence_matrix.DEFAULT_OWNER_RECORDS_RAW)
    parser.add_argument("--forced-hitmap-raw", type=Path, default=castle_overview_evidence_matrix.DEFAULT_FORCED_HITMAP_RAW)
    parser.add_argument("--dormant-multihit-run", type=Path, default=castle_overview_evidence_matrix.DEFAULT_DORMANT_MULTI_RUN)
    parser.add_argument("--threshold", type=int, default=12)
    parser.add_argument("--max-echo-percent", type=float, default=25.0)
    parser.add_argument("--write-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--write-markdown", type=Path, default=DEFAULT_MD)
    parser.add_argument("--require-pass", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    recheck = build_recheck(args)
    if args.write_json:
        write_json(args.write_json, recheck)
    if args.write_markdown:
        write_markdown(args.write_markdown, recheck)
    print_recheck(recheck)
    if args.require_pass and not recheck["passed"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
