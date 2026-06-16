#!/usr/bin/env python3
"""Run the repo-only Clash95 castle overview evidence matrix.

This is the compact no-runtime gate for the current castle overview validation
stage. It checks existing hidden-desktop CDB/proxy artifacts only; it does not
launch Clash95, CDB, wrappers, or any visible GUI process.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import castle_owner_records_summary
import castle_overview_gate
import castle_overview_hitbox_summary
import castle_overview_hitmap_summary
import castle_overview_multihit_summary
import patch_stage_report


DEFAULT_STAGE = "castlecenter-all"
STAGE_ALIASES = {
    "castlecenter-all": (
        "gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-"
        "presentbounds-minimapright-dynvswitch-castlecenter-all"
    ),
}
DEFAULT_OVERVIEW_RUN = Path("captures/archive/cdb-surface-dump-20260515-105041")
DEFAULT_BARRACKS_RUN = Path("captures/archive/cdb-surface-dump-20260512-082418")
DEFAULT_FOCUSED_HITBOX_RUN = Path("captures/archive/cdb-surface-dump-20260515-105411")
DEFAULT_VISIBLE_MULTI_RUN = Path("captures/archive/cdb-surface-dump-20260515-105458")
DEFAULT_OWNER_RECORDS_RAW = Path("captures/current/castle-owner-records-current.raw")
DEFAULT_FORCED_HITMAP_RAW = Path("captures/archive/castle-overview-hitmap-flags1f.raw")
DEFAULT_DORMANT_MULTI_RUN = Path("captures/archive/cdb-surface-dump-20260515-105557")

VISIBLE_COMMAND_RAWS = (0xF8, 0xFE, 0xFF)
DORMANT_COMMAND_RAWS = (0xFA, 0xFB, 0xFC, 0xFD)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def repo_relative(path: Path | str | None) -> str | None:
    if path is None:
        return None
    candidate = Path(path)
    try:
        return str(candidate.relative_to(Path.cwd()))
    except ValueError:
        return str(candidate)


def first_existing_candidate(runs: list[Path]) -> Path | None:
    for run in runs:
        summary_path = run / "summary.json"
        if not summary_path.exists():
            continue
        candidate = load_json(summary_path).get("CandidatePath")
        if candidate:
            return Path(candidate)
    return None


def resolve_stage(stage: str) -> str:
    return STAGE_ALIASES.get(stage, stage)


def patch_counts(report: dict[str, Any]) -> dict[str, int]:
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
    resolved_stage = resolve_stage(stage)
    failures: list[str] = []
    report_stage = str(report.get("stage") or "")
    if report_stage != resolved_stage:
        failures.append(f"archived patch report stage mismatch: expected {resolved_stage}, got {report_stage}")
    counts = patch_counts(report)
    if counts["original"]:
        failures.append(f"{counts['original']} selected patch bytes are still original")
    if counts["unexpected"]:
        failures.append(f"{counts['unexpected']} selected patch bytes are unexpected")
    current_gate = report.get("current_hd_map_gate") or {}
    if current_gate and not current_gate.get("passed"):
        for failure in current_gate.get("failures") or ["current HD map gate did not pass"]:
            failures.append(f"current_hd_map_gate: {failure}")
    return {
        "passed": not failures,
        "exe": report.get("exe"),
        "source": str(source),
        "archived": True,
        "stage": stage,
        "resolved_stage": report_stage or resolved_stage,
        "sha256": report.get("exe_sha256") or report.get("sha256"),
        "patches": counts,
        "groups": report.get("groups", {}),
        "failures": failures,
    }


def patch_stage_gate(exe: Path | None, stage: str) -> dict[str, Any]:
    resolved_stage = resolve_stage(stage)
    if exe is None:
        return {
            "passed": False,
            "exe": None,
            "stage": stage,
            "resolved_stage": resolved_stage,
            "failures": ["no candidate executable path was found"],
        }
    if not exe.exists():
        return {
            "passed": False,
            "exe": str(exe),
            "stage": stage,
            "resolved_stage": resolved_stage,
            "failures": [f"candidate executable does not exist: {exe}"],
        }

    report = patch_stage_report.build_report(exe, resolved_stage)
    status_counts = report["status_counts"]
    failures = []
    if int(status_counts.get("original", 0)):
        failures.append(f"{status_counts['original']} selected patch bytes are still original")
    if int(status_counts.get("unexpected", 0)):
        failures.append(f"{status_counts['unexpected']} selected patch bytes are unexpected")

    return {
        "passed": not failures,
        "exe": str(exe),
        "stage": stage,
        "resolved_stage": resolved_stage,
        "sha256": report.get("exe_sha256"),
        "patches": {
            "patched": int(status_counts.get("patched", 0)),
            "original": int(status_counts.get("original", 0)),
            "unexpected": int(status_counts.get("unexpected", 0)),
            "total": int(report.get("patch_count", 0)),
        },
        "groups": report.get("groups", {}),
        "failures": failures,
    }


def focused_hitbox_gate(run: Path) -> dict[str, Any]:
    log = run / "cdb-surface-dump.log"
    failures: list[str] = []
    if not log.exists():
        return {
            "passed": False,
            "run": str(run),
            "log": str(log),
            "failures": [f"missing focused hitbox log: {log}"],
        }
    summary = castle_overview_hitbox_summary.parse_log(log)
    ready = bool(
        summary["marker_counts"]["CASTLEOV_HITBOX_SURFDUMP_READY"]
        or summary["marker_counts"]["SURFDUMP_READY"]
    )
    if not ready:
        failures.append("focused hitbox surface-ready marker was not observed")
    if summary["last_ready"].get("size") != [800, 600]:
        failures.append(f"focused hitbox ready surface was {summary['last_ready'].get('size')}")
    for key, label in (
        ("displayed_hit_ok", "displayed-coordinate target hit"),
        ("descriptor_ok", "descriptor install"),
        ("click_gate_ok", "stock click gate"),
        ("callback_suppressed", "callback suppression after gate proof"),
    ):
        if not summary.get(key):
            failures.append(f"focused hitbox did not prove {label}")
    displayed_wrapper_ok = bool(summary["marker_counts"]["CASTLEOV_HITBOX_DISPLAYED_WRAPPER_OK"])
    if not displayed_wrapper_ok:
        failures.append("focused hitbox did not prove displayed-coordinate binary wrapper success")
    if summary.get("callback_called"):
        failures.append("focused hitbox callback was entered")
    if summary.get("av_count"):
        failures.append("focused hitbox AV rows were observed")
    return {
        "passed": not failures,
        "run": str(run),
        "log": str(log),
        "screenshot": str((run / "surface.png").resolve()) if (run / "surface.png").exists() else None,
        "ready": ready,
        "ready_size": summary["last_ready"].get("size"),
        "displayed_result": summary.get("displayed_result"),
        "displayed_wrapper_ok": displayed_wrapper_ok,
        "last_descriptor": summary.get("last_descriptor"),
        "last_click_gate": summary.get("last_click_gate"),
        "av_count": summary.get("av_count"),
        "classification": summary.get("classification", []),
        "failures": failures,
    }


def multihit_gate(run: Path, label: str) -> dict[str, Any]:
    log = run / "cdb-surface-dump.log"
    failures: list[str] = []
    if not log.exists():
        return {
            "passed": False,
            "label": label,
            "run": str(run),
            "log": str(log),
            "failures": [f"missing {label} log: {log}"],
        }
    summary = castle_overview_multihit_summary.parse_log(log)
    ready = bool(
        summary["marker_counts"]["CASTLEOV_MULTI_SURFDUMP_READY"]
        or summary["marker_counts"]["SURFDUMP_READY"]
    )
    if not ready:
        failures.append(f"{label} surface-ready marker was not observed")
    if summary["last_ready"].get("size") != [800, 600]:
        failures.append(f"{label} ready surface was {summary['last_ready'].get('size')}")
    if not summary.get("all_targets_ok"):
        failures.append(f"{label} did not prove all targets")
    if summary.get("callback_called"):
        failures.append(f"{label} descriptor callback was entered")
    if summary.get("av_count"):
        failures.append(f"{label} AV rows were observed")
    targets = []
    for index, target in sorted(summary.get("targets", {}).items()):
        expected = target.get("expected", {})
        targets.append(
            {
                "index": index,
                "raw": expected.get("raw"),
                "command": expected.get("command"),
                "callback": expected.get("callback"),
                "raw_ok": target.get("raw_ok"),
                "descriptor_ok": target.get("descriptor_ok"),
                "gate_ok": target.get("gate_ok"),
                "completion_ok": target.get("completion_ok"),
                "ok": target.get("ok"),
            }
        )
    return {
        "passed": not failures,
        "label": label,
        "run": str(run),
        "log": str(log),
        "screenshot": str((run / "surface.png").resolve()) if (run / "surface.png").exists() else None,
        "ready": ready,
        "ready_size": summary["last_ready"].get("size"),
        "all_targets_ok": summary.get("all_targets_ok"),
        "callback_called": summary.get("callback_called"),
        "av_count": summary.get("av_count"),
        "targets": targets,
        "classification": summary.get("classification", []),
        "failures": failures,
    }


def owner_records_gate(raw: Path) -> dict[str, Any]:
    failures: list[str] = []
    if not raw.exists():
        return {
            "passed": False,
            "raw": str(raw),
            "failures": [f"missing owner records raw dump: {raw}"],
        }
    summary = castle_owner_records_summary.summarize(raw, castle_owner_records_summary.DEFAULT_RECORDS)
    if summary["interesting_records"]:
        failures.append("current owner-record dump contains feature-flag records")
    if not summary["active_records"]:
        failures.append("current owner-record dump has no active records")
    return {
        "passed": not failures,
        "raw": str(raw),
        "record_count": summary["record_count"],
        "active_records": len(summary["active_records"]),
        "nonempty_records": len(summary["nonempty_records"]),
        "interesting_records": len(summary["interesting_records"]),
        "flag_1a0_values": summary["flag_1a0_values"],
        "flag_1a4_values": summary["flag_1a4_values"],
        "failures": failures,
    }


def hitmap_gate(raw: Path) -> dict[str, Any]:
    failures: list[str] = []
    if not raw.exists():
        return {
            "passed": False,
            "raw": str(raw),
            "failures": [f"missing forced hitmap raw dump: {raw}"],
        }
    summary = castle_overview_hitmap_summary.summarize(raw, width=640, height=480)
    for raw_id in VISIBLE_COMMAND_RAWS + DORMANT_COMMAND_RAWS:
        key = f"0x{raw_id:02X}"
        if not summary["values"][key]["present"]:
            failures.append(f"forced hitmap raw id {key} is absent")
    return {
        "passed": not failures,
        "raw": str(raw),
        "present_raw_ids": summary["present_raw_ids"],
        "visible_command_raws": [f"0x{raw_id:02X}" for raw_id in VISIBLE_COMMAND_RAWS],
        "dormant_command_raws": [f"0x{raw_id:02X}" for raw_id in DORMANT_COMMAND_RAWS],
        "values": summary["values"],
        "failures": failures,
    }


def build_matrix(args: argparse.Namespace) -> dict[str, Any]:
    runs = [
        args.dormant_multihit_run,
        args.visible_multihit_run,
        args.focused_hitbox_run,
        args.overview_run,
        args.barracks_run,
    ]
    if getattr(args, "patch_report_json", None):
        patch_stage = patch_stage_gate_from_report(load_json(args.patch_report_json), args.stage, args.patch_report_json)
    else:
        patch_exe = args.patch_exe or first_existing_candidate(runs)
        patch_stage = patch_stage_gate(patch_exe, args.stage)
    overview_visual = castle_overview_gate.build_gate(
        run_dir=args.overview_run,
        expected_commands=castle_overview_gate.DEFAULT_COMMANDS,
        threshold=args.threshold,
        max_echo_percent=args.max_echo_percent,
        barracks_run=args.barracks_run,
    )
    focused_hitbox = focused_hitbox_gate(args.focused_hitbox_run)
    visible_multihit = multihit_gate(args.visible_multihit_run, "visible-command multi-hit")
    owner_records = owner_records_gate(args.owner_records_raw)
    forced_hitmap = hitmap_gate(args.forced_hitmap_raw)
    dormant_multihit = multihit_gate(args.dormant_multihit_run, "dormant-command multi-hit")

    checks = {
        "patch_stage": patch_stage,
        "overview_visual": overview_visual,
        "focused_hitbox": focused_hitbox,
        "visible_multihit": visible_multihit,
        "owner_records": owner_records,
        "forced_hitmap": forced_hitmap,
        "dormant_multihit": dormant_multihit,
    }
    failures: list[str] = []
    for name, check in checks.items():
        if not check.get("passed"):
            check_failures = check.get("failures") or ["failed without a detailed reason"]
            failures.extend(f"{name}: {failure}" for failure in check_failures)

    return {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "passed": not failures,
        "stage": args.stage,
        "promotion_status": "validation_stage_only",
        "runtime_policy": "repo-only; does not launch Clash95, CDB, wrappers, or visible windows",
        "checks": checks,
        "failures": failures,
    }


def print_matrix(matrix: dict[str, Any]) -> None:
    print(f"overall: {'PASS' if matrix['passed'] else 'FAIL'}")
    print(f"stage: {matrix['stage']}")
    print(f"promotion-status: {matrix['promotion_status']}")
    print(f"runtime-policy: {matrix['runtime_policy']}")
    for name, check in matrix["checks"].items():
        print(f"{name}: {'PASS' if check.get('passed') else 'FAIL'}")
        if name == "patch_stage":
            print(f"  exe: {check.get('exe')}")
            if check.get("archived"):
                print(f"  archived_report: {check.get('source')}")
            print(f"  resolved-stage: {check.get('resolved_stage')}")
            print(f"  sha256: {check.get('sha256')}")
            patches = check.get("patches") or {}
            if patches:
                print(
                    "  patches: patched={patched} original={original} unexpected={unexpected} total={total}".format(
                        **patches
                    )
                )
        if name in {"visible_multihit", "dormant_multihit"}:
            target_text = ", ".join(
                "0x{command:02X}/0x{raw:02X}:{status} done:{done}".format(
                    command=target["command"],
                    raw=target["raw"],
                    status="ok" if target.get("ok") else "fail",
                    done="ok" if target.get("completion_ok") else "fail",
                )
                for target in check.get("targets", [])
            )
            print(f"  targets: {target_text}")
        if check.get("failures"):
            for failure in check["failures"]:
                print(f"  - {failure}")
    if matrix.get("failures"):
        print("failures:")
        for failure in matrix["failures"]:
            print(f"  - {failure}")


def markdown_image(path: str | None, label: str) -> str:
    if not path:
        return "_No screenshot path recorded._"
    image_path = Path(path)
    if not image_path.is_absolute():
        image_path = image_path.resolve()
    return f"![{label}]({image_path})"


def target_completion_text(check: dict[str, Any]) -> str:
    targets = check.get("targets") or []
    if not targets:
        return "none"
    return ", ".join(
        "index {index} 0x{command:02X}/0x{raw:02X} completion={completion}".format(
            index=target.get("index"),
            command=target.get("command"),
            raw=target.get("raw"),
            completion=bool(target.get("completion_ok")),
        )
        for target in targets
    )


def write_markdown(path: Path, matrix: dict[str, Any]) -> None:
    checks = matrix["checks"]
    patch_stage = checks["patch_stage"]
    overview_visual = checks["overview_visual"]
    focused_hitbox = checks["focused_hitbox"]
    visible_multihit = checks["visible_multihit"]
    owner_records = checks["owner_records"]
    forced_hitmap = checks["forced_hitmap"]
    dormant_multihit = checks["dormant_multihit"]
    patches = patch_stage.get("patches") or {}
    overview_catalog = overview_visual.get("catalog", {})
    overview_geometry_gate = (overview_visual.get("geometry") or {}).get("gate", {})

    lines = [
        "# Castle Overview Evidence Matrix",
        "",
        f"- Overall: {'PASS' if matrix['passed'] else 'FAIL'}",
        f"- Generated: `{matrix['generated_at']}`",
        f"- Stage: `{matrix['stage']}`",
        f"- Promotion status: `{matrix['promotion_status']}`",
        f"- Runtime policy: {matrix['runtime_policy']}",
        "",
        "## Patch Stage",
        "",
        f"- Status: {'PASS' if patch_stage['passed'] else 'FAIL'}",
        f"- Executable: `{patch_stage.get('exe')}`",
        f"- Source: `{patch_stage.get('source')}`",
        f"- Archived report: `{bool(patch_stage.get('archived'))}`",
        f"- Resolved stage: `{patch_stage.get('resolved_stage')}`",
        f"- SHA-256: `{patch_stage.get('sha256')}`",
        "- Patches: patched={patched} original={original} unexpected={unexpected} total={total}".format(
            patched=patches.get("patched", "?"),
            original=patches.get("original", "?"),
            unexpected=patches.get("unexpected", "?"),
            total=patches.get("total", "?"),
        ),
        "",
        "## Overview Visual",
        "",
        f"- Status: {'PASS' if overview_visual['passed'] else 'FAIL'}",
        f"- Run: `{repo_relative(overview_visual.get('run_dir'))}`",
        f"- Commands: {', '.join(overview_catalog.get('commands') or [])}",
        f"- Surface size: `{overview_catalog.get('last_surface', {}).get('size')}`",
        f"- Centered geometry: {'PASS' if overview_geometry_gate.get('passed') else 'FAIL'}",
        "",
        markdown_image(overview_visual.get("screenshot"), "castle overview surface"),
        "",
        "## Input Hitboxes",
        "",
        f"- Focused command `0x86`: {'PASS' if focused_hitbox['passed'] else 'FAIL'}",
        f"- Focused displayed wrapper proof: `{focused_hitbox.get('displayed_wrapper_ok')}`",
        f"- Visible commands `0x86`, `0x63`, `0x87`: {'PASS' if visible_multihit['passed'] else 'FAIL'}",
        f"- Visible target completion: `{target_completion_text(visible_multihit)}`",
        f"- Dormant commands `0x99`, `0x9C`, `0x9F`, `0xA6`: {'PASS' if dormant_multihit['passed'] else 'FAIL'}",
        f"- Dormant target completion: `{target_completion_text(dormant_multihit)}`",
        "",
        "## Owner/Hitmap State",
        "",
        f"- Current owner records: {'PASS' if owner_records['passed'] else 'FAIL'}",
        f"- Active records: `{owner_records.get('active_records')}`",
        f"- Interesting feature-flag records: `{owner_records.get('interesting_records')}`",
        f"- Forced owner-feature hitmap: {'PASS' if forced_hitmap['passed'] else 'FAIL'}",
        f"- Present forced raw IDs: {', '.join(forced_hitmap.get('present_raw_ids') or [])}",
        "",
        "## Additional Screenshots",
        "",
        markdown_image(focused_hitbox.get("screenshot"), "focused overview hitbox surface"),
        "",
        markdown_image(visible_multihit.get("screenshot"), "visible-command overview multi-hit surface"),
        "",
        markdown_image(dormant_multihit.get("screenshot"), "dormant-command overview multi-hit surface"),
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
    parser.add_argument("--stage", default=DEFAULT_STAGE)
    parser.add_argument("--patch-exe", type=Path)
    parser.add_argument(
        "--patch-report-json",
        type=Path,
        help="use an archived tools/patch_stage_report.py JSON report instead of reading a local executable",
    )
    parser.add_argument("--overview-run", type=Path, default=DEFAULT_OVERVIEW_RUN)
    parser.add_argument("--barracks-run", type=Path, default=DEFAULT_BARRACKS_RUN)
    parser.add_argument("--focused-hitbox-run", type=Path, default=DEFAULT_FOCUSED_HITBOX_RUN)
    parser.add_argument("--visible-multihit-run", type=Path, default=DEFAULT_VISIBLE_MULTI_RUN)
    parser.add_argument("--owner-records-raw", type=Path, default=DEFAULT_OWNER_RECORDS_RAW)
    parser.add_argument("--forced-hitmap-raw", type=Path, default=DEFAULT_FORCED_HITMAP_RAW)
    parser.add_argument("--dormant-multihit-run", type=Path, default=DEFAULT_DORMANT_MULTI_RUN)
    parser.add_argument("--threshold", type=int, default=12)
    parser.add_argument("--max-echo-percent", type=float, default=25.0)
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
