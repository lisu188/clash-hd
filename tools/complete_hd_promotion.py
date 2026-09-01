#!/usr/bin/env python3
"""Run the HD completion promotion sequence end to end.

Given the run manifest from an approved VM validation session, this orchestrator
runs, in order:

1. ``assemble_manual_directinput_proof.py`` -> writes the proof manifest.
2. ``manual_directinput_checklist.py --require-promotion-ready`` -> the proof is
   structurally valid and promotion-ready.
3. ``battle_visible_input_summary.py --require-click-consumed`` (only when a
   ``--battle-run-dir`` is supplied) -> a real battle click was consumed.
4. The three promotion decisions in FINISH_LINE_RUNBOOK step-4 order --
   ``hd_layout_promotion_decision.py``,
   ``right_bottom_compose_promotion_decision.py``,
   ``castle_overview_promotion_decision.py`` -> all flip to
   ``eligible_for_stable_promotion``.
5. ``current_evidence_refresh.py`` twice (the runbook's double refresh); the
   second run carries ``--require-pass`` and is the 165/165 gate.

Every step is a repo-only tool; this launches no game, VM, or visible window --
it only grades the artifacts an approved run already produced. When all steps
pass and ``--update-checklist`` is given, it checks the two remaining boxes in
``reports/final_hd_release_checklist.md``.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
PROOF_JSON = Path("captures/current/manual-directinput-proof-current.json")
DEFAULT_SUMMARY_JSON = Path("captures/current/complete-hd-promotion-current.json")
CHECKLIST_MD = ROOT / "reports" / "final_hd_release_checklist.md"

RUNTIME_POLICY = (
    "repo-only promotion orchestrator; runs assembler + checklist + promotion "
    "decision tools over already-captured artifacts; launches no game, VM, CDB, "
    "wrapper, PowerShell, or visible window"
)


def plan_steps(args: argparse.Namespace) -> list[tuple[str, list[str]]]:
    """Build the ordered (name, argv) step plan without running anything."""
    assemble_argv = [
        str(TOOLS / "assemble_manual_directinput_proof.py"),
        "--run-manifest", str(args.run_manifest),
        "--output", str(args.proof_json),
        "--require-valid",
    ]
    if args.observations:
        assemble_argv += ["--observations", str(args.observations)]

    steps: list[tuple[str, list[str]]] = [
        ("assemble_proof", assemble_argv),
        (
            "manual_checklist",
            [
                str(TOOLS / "manual_directinput_checklist.py"),
                "--manual-proof", str(args.proof_json),
                "--require-pass",
                "--require-promotion-ready",
            ],
        ),
    ]
    if args.battle_run_dir:
        steps.append(
            (
                "battle_click_consumed",
                [
                    str(TOOLS / "battle_visible_input_summary.py"),
                    str(args.battle_run_dir),
                    "--require-click-consumed",
                ],
            )
        )
    # The three promotion decisions in FINISH_LINE_RUNBOOK step-4 order. The
    # hd-layout decision reads the manual checklist JSON that the
    # manual_checklist step above regenerates with the validated proof.
    steps.append(
        (
            "hd_layout_promotion",
            [
                str(TOOLS / "hd_layout_promotion_decision.py"),
                "--require-pass",
            ],
        )
    )
    steps.append(
        (
            "right_bottom_promotion",
            [
                str(TOOLS / "right_bottom_compose_promotion_decision.py"),
                "--manual-input-proof", str(args.proof_json),
                "--require-pass",
            ],
        )
    )
    steps.append(
        (
            "castle_overview_promotion",
            [
                str(TOOLS / "castle_overview_promotion_decision.py"),
                "--manual-input-proof", str(args.proof_json),
                "--require-pass",
            ],
        )
    )
    # Runbook step 4 ends with the double evidence refresh; --require-pass makes
    # the second run the 165/165 gate that --update-checklist depends on.
    steps.append(("evidence_refresh_1", [str(TOOLS / "current_evidence_refresh.py")]))
    steps.append(("evidence_refresh_2", [str(TOOLS / "current_evidence_refresh.py"), "--require-pass"]))
    return steps


def run_step(name: str, argv: list[str]) -> dict[str, Any]:
    proc = subprocess.run(
        [sys.executable, *argv],
        cwd=str(ROOT),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    return {
        "name": name,
        "command": " ".join(argv),
        "exit_code": proc.returncode,
        "passed": proc.returncode == 0,
        "stdout_tail": proc.stdout[-2000:],
        "stderr_tail": proc.stderr[-2000:],
    }


def check_release_boxes(md_path: Path) -> Path | None:
    """Check the two open manual/promotion boxes; return the path if it changed."""
    if not md_path.exists():
        return None
    text = md_path.read_text(encoding="utf-8")
    updated = text.replace(
        "- [ ] Manual DirectInput proof manifest passes for all five required targets.",
        "- [x] Manual DirectInput proof manifest passes for all five required targets.",
    ).replace(
        "- [ ] Promotion decision tools allow stable promotion.",
        "- [x] Promotion decision tools allow stable promotion.",
    )
    if updated != text:
        md_path.write_text(updated, encoding="utf-8")
        return md_path
    return None


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-manifest", type=Path, required=True, help="Run manifest from an approved VM run")
    parser.add_argument("--observations", type=Path, help="Optional operator observations JSON")
    parser.add_argument("--proof-json", type=Path, default=PROOF_JSON, help="Where to write/read the proof manifest")
    parser.add_argument("--battle-run-dir", type=Path, help="Battle visible-input run dir for the click-consumed gate")
    parser.add_argument("--update-checklist", action="store_true", help="Check the two release boxes on full pass")
    parser.add_argument("--write-json", type=Path, default=DEFAULT_SUMMARY_JSON)
    parser.add_argument("--require-pass", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    steps = [run_step(name, step_argv) for name, step_argv in plan_steps(args)]
    passed = all(step["passed"] for step in steps)
    checklist_updated = None
    if passed and args.update_checklist:
        changed = check_release_boxes(CHECKLIST_MD)
        checklist_updated = str(changed) if changed else None

    summary = {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "runtime_policy": RUNTIME_POLICY,
        "run_manifest": str(args.run_manifest),
        "proof_json": str(args.proof_json),
        "battle_run_dir": str(args.battle_run_dir) if args.battle_run_dir else None,
        "passed": passed,
        "promotion_ready": passed,
        "checklist_updated": checklist_updated,
        "steps": steps,
        "failures": [step["name"] for step in steps if not step["passed"]],
    }

    if args.write_json:
        args.write_json.parent.mkdir(parents=True, exist_ok=True)
        args.write_json.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    print(f"runtime-policy: {RUNTIME_POLICY}")
    for step in steps:
        print(f"  {'PASS' if step['passed'] else 'FAIL'} {step['name']} (exit {step['exit_code']})")
    print(f"promotion-ready: {passed}")
    if checklist_updated:
        print(f"checklist-updated: {checklist_updated}")
    if summary["failures"]:
        print(f"failures: {summary['failures']}")

    if args.require_pass and not passed:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
