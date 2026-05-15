#!/usr/bin/env python3
"""Fail-closed gate for Clash95 battle UI HD evidence."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import battle_ui_summary


EXPECTED_STAGE = (
    "gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-"
    "presentbounds-minimapright-dynvswitch-castlecenter-all-battlecenter"
)
EXPECTED_BASE_SHA256 = "500055D77D03D514E8D3168506BD10F67CD8569BCC450604FF8192F46CDAF3AE"


def load_json(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}


def under_clash_tests(path_text: str | None) -> bool:
    if not path_text:
        return False
    return path_text.replace("/", "\\").lower().startswith("c:\\clashtests\\")


def status_text(passed: bool) -> str:
    return "PASS" if passed else "FAIL"


def build_gate(args: argparse.Namespace) -> dict[str, Any]:
    summary = battle_ui_summary.build_summary(args.capture_or_log)
    patch_stage = load_json(args.patch_stage_json)
    stable_smoke = load_json(args.stable_smoke_json)
    failures: list[str] = []

    candidate = summary.get("candidate") or patch_stage.get("exe")
    if not under_clash_tests(candidate):
        failures.append(f"candidate is not under C:\\ClashTests: {candidate}")

    expected_base = str(patch_stage.get("expected_base_sha256") or "").upper()
    if patch_stage and expected_base != EXPECTED_BASE_SHA256:
        failures.append(
            f"patch-stage expected base SHA mismatch: {expected_base or 'missing'}"
        )
    elif not patch_stage:
        failures.append("patch-stage report was not supplied")

    if patch_stage and patch_stage.get("stage") != args.stage:
        failures.append(
            f"patch-stage report stage {patch_stage.get('stage')!r} did not match {args.stage!r}"
        )
    status_counts = patch_stage.get("status_counts") or {}
    original_count = int(status_counts.get("original", 0) or 0)
    unexpected_count = int(status_counts.get("unexpected", 0) or 0)
    if original_count:
        failures.append(f"patch-stage report has original bytes: {original_count}")
    if unexpected_count:
        failures.append(f"patch-stage report has unexpected bytes: {unexpected_count}")

    if not summary["battle_reached"]:
        failures.append("battle mode was not reached")
    if summary["av_count"]:
        failures.append(f"battle AV/crash rows were observed: {summary['av_count']}")
    if summary["surface_size"] is None:
        failures.append("battle surface size was not classified")
    if summary["visual_mode"] == "unknown":
        failures.append("battle visual mode was not classified")
    if args.require_centered:
        if summary["visual_mode"] != "centered-native-640x480":
            failures.append(
                f"centered-native visual mode required, got {summary['visual_mode']}"
            )
        if summary["centered_offset"] != [80, 60]:
            failures.append(f"center offset [80, 60] was not proven: {summary['centered_offset']}")
    if not summary["command_descriptor_found"]:
        failures.append("battle command descriptor was not found")
    if not summary["command_hit_ok"]:
        failures.append("battle command click did not prove displayed-to-native descriptor/callback route")
    if not summary["grid_hit_ok"]:
        failures.append("battle tactical-grid click did not prove displayed-to-native cell/result route")
    if not (summary["modal_hit"] or summary["modal_classified"]):
        failures.append("battle modal/dialog path was not tested or classified")

    stable_passed = bool(
        stable_smoke.get("passed")
        or stable_smoke.get("overall") == "PASS"
        or stable_smoke.get("patch_stage_passed")
    )
    if args.stable_smoke_json and not stable_passed:
        failures.append(f"stable HD-map regression evidence did not pass: {args.stable_smoke_json}")

    return {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "passed": not failures,
        "runtime_policy": "repo-only gate over existing battle probe and patch-stage artifacts; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows",
        "stage": args.stage,
        "candidate": candidate,
        "candidate_sha256": summary.get("candidate_sha256") or patch_stage.get("exe_sha256"),
        "patch_stage_json": str(args.patch_stage_json) if args.patch_stage_json else None,
        "stable_smoke_json": str(args.stable_smoke_json) if args.stable_smoke_json else None,
        "original_count": original_count,
        "unexpected_count": unexpected_count,
        "battle_summary": summary,
        "stable_smoke_passed": stable_passed if args.stable_smoke_json else None,
        "failures": failures,
    }


def write_markdown(path: Path, gate: dict[str, Any]) -> None:
    summary = gate["battle_summary"]
    lines = [
        "# Battle UI Gate",
        "",
        f"- Overall: {status_text(bool(gate['passed']))}",
        f"- Generated: `{gate['generated_at']}`",
        f"- Runtime policy: {gate['runtime_policy']}",
        f"- Stage: `{gate['stage']}`",
        f"- Candidate: `{gate.get('candidate')}`",
        f"- Candidate SHA-256: `{gate.get('candidate_sha256')}`",
        f"- Patch-stage JSON: `{gate.get('patch_stage_json')}`",
        f"- Stable smoke JSON: `{gate.get('stable_smoke_json')}`",
        f"- Original bytes: `{gate['original_count']}`",
        f"- Unexpected bytes: `{gate['unexpected_count']}`",
        f"- Battle reached: `{summary['battle_reached']}`",
        f"- Surface size: `{summary['surface_size']}`",
        f"- Visual mode: `{summary['visual_mode']}`",
        f"- Centered offset: `{summary['centered_offset']}`",
        f"- Command descriptor found: `{summary['command_descriptor_found']}`",
        f"- Command hit ok: `{summary['command_hit_ok']}`",
        f"- Grid hit ok: `{summary['grid_hit_ok']}`",
        f"- Modal classified: `{summary['modal_hit'] or summary['modal_classified']}`",
        f"- Access violations: `{summary['av_count']}`",
        "",
        "## Failures",
        "",
    ]
    if gate["failures"]:
        lines.extend(f"- {failure}" for failure in gate["failures"])
    else:
        lines.append("- None")
    lines.extend(["", "## Battle Classification", ""])
    lines.extend(f"- {item}" for item in summary["classification"])
    if summary.get("screenshot"):
        lines.extend(["", "## Screenshot", "", f"![battle UI surface]({summary['screenshot']})"])
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture_or_log", type=Path)
    parser.add_argument("--stage", default=EXPECTED_STAGE)
    parser.add_argument("--patch-stage-json", type=Path)
    parser.add_argument("--stable-smoke-json", type=Path)
    parser.add_argument("--require-centered", action="store_true")
    parser.add_argument("--write-json", type=Path)
    parser.add_argument("--write-markdown", "--write-md", dest="write_markdown", type=Path)
    parser.add_argument("--require-pass", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    gate = build_gate(args)
    print(f"overall: {status_text(bool(gate['passed']))}")
    print(f"battle-reached: {gate['battle_summary']['battle_reached']}")
    print(f"visual-mode: {gate['battle_summary']['visual_mode']}")
    print(f"command-hit-ok: {gate['battle_summary']['command_hit_ok']}")
    print(f"grid-hit-ok: {gate['battle_summary']['grid_hit_ok']}")
    print(f"failures: {len(gate['failures'])}")
    for failure in gate["failures"]:
        print(f"  - {failure}")
    if args.write_json:
        args.write_json.parent.mkdir(parents=True, exist_ok=True)
        args.write_json.write_text(json.dumps(gate, indent=2) + "\n", encoding="utf-8")
    if args.write_markdown:
        write_markdown(args.write_markdown, gate)
    if args.require_pass and not gate["passed"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
