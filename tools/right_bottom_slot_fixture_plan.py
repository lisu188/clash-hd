#!/usr/bin/env python3
r"""Plan the non-promoting right-bottom slot fixture route.

The current natural route evidence has a useful split: load slot 0 reaches the
right-bottom castle path but its owner flag is zero, while installed save slot 5
has the route-compatible owner/action record but the hidden load-row harness
stalls before LOADSAVE. This helper turns that split into a machine-checked
fixture plan: copy ``C:\Clash\save\5.dat`` into an isolated workdir as
``save\0.dat`` and rerun the already-proven row-0 path.

This script is intentionally repo-only by default. It writes JSON/Markdown
evidence, never copies saves, and marks the fixture as non-natural and
non-promoting until a natural menu route or explicit manual/override proof
exists.
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path, PureWindowsPath
from typing import Any


DEFAULT_CANDIDATE_MATRIX_JSON = Path("captures/current/right-bottom-natural-route-candidate-matrix-current.json")
DEFAULT_LOAD_SLOT_ROUTE_LIMIT_JSON = Path("captures/current/load-slot-route-limit-current.json")
DEFAULT_FIXTURE_ROOT = Path(r"C:\ClashTests\right-bottom-slot5-as-slot0-fixture")
DEFAULT_JSON = Path("captures/current/right-bottom-slot-fixture-plan-current.json")
DEFAULT_MD = Path("captures/current/right-bottom-slot-fixture-plan-current.md")

RUNTIME_POLICY = (
    "repo-only fixture planner; reads generated evidence JSON and writes only "
    "JSON/Markdown reports; does not copy saves, launch Clash95, CDB, wrappers, "
    "PowerShell, or visible windows"
)
GUARD_POLICY = (
    "passes only while the slot-5 route-compatible save remains blocked before "
    "LOADSAVE, the row-0 natural route remains proven, and the proposed copied "
    "save stays isolated and non-promoting"
)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def status_text(passed: bool) -> str:
    return "PASS" if passed else "FAIL"


def nested_get(value: dict[str, Any], path: list[str], default: Any = None) -> Any:
    current: Any = value
    for key in path:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return current


def path_is_under(child: Path, parent: Path) -> bool:
    # Windows-target paths (drive-letter or UNC) describe the game host, not this
    # checkout; on a POSIX host they can never be under the repo root.
    child_win = PureWindowsPath(str(child))
    if child_win.drive or str(child).startswith("\\\\"):
        if os.name != "nt":
            return False
        try:
            child_win.relative_to(PureWindowsPath(str(Path(parent).resolve(strict=False))))
            return True
        except ValueError:
            return False
    try:
        Path(str(child)).resolve(strict=False).relative_to(Path(parent).resolve(strict=False))
        return True
    except ValueError:
        return False


def same_path(left: Path, right: Path) -> bool:
    # Compare as Windows-target paths so the check is stable on any host.
    return (
        PureWindowsPath(str(left)).as_posix().casefold()
        == PureWindowsPath(str(right)).as_posix().casefold()
    )


def build_plan(
    candidate_matrix_json: Path = DEFAULT_CANDIDATE_MATRIX_JSON,
    load_slot_route_limit_json: Path = DEFAULT_LOAD_SLOT_ROUTE_LIMIT_JSON,
    *,
    fixture_root: Path = DEFAULT_FIXTURE_ROOT,
    repo_root: Path | None = None,
    target_load_slot: int = 0,
) -> dict[str, Any]:
    failures: list[str] = []
    repo_root = repo_root or Path.cwd()

    candidate_matrix: dict[str, Any] = {}
    load_slot_route_limit: dict[str, Any] = {}
    if not candidate_matrix_json.exists():
        failures.append(f"missing candidate matrix JSON: {candidate_matrix_json}")
    else:
        candidate_matrix = load_json(candidate_matrix_json)
    if not load_slot_route_limit_json.exists():
        failures.append(f"missing load-slot route-limit JSON: {load_slot_route_limit_json}")
    else:
        load_slot_route_limit = load_json(load_slot_route_limit_json)

    summary = candidate_matrix.get("summary") or {}
    route_candidate = summary.get("route_compatible_candidate") or {}
    slot5_status = summary.get("slot5_status") or {}
    slot2_status = summary.get("slot2_status") or {}
    baseline = candidate_matrix.get("baseline") or {}
    route_limit_summary = load_slot_route_limit.get("summary") or {}

    source_save_text = route_candidate.get("save") or r"C:\Clash\save\5.dat"
    source_save = Path(source_save_text)
    # Windows-target path: keep backslash separators regardless of host OS.
    fixture_save = PureWindowsPath(str(fixture_root)) / "save" / f"{target_load_slot}.dat"

    if candidate_matrix and candidate_matrix.get("passed") is not True:
        failures.append("right-bottom natural route candidate matrix is not passing")
    if candidate_matrix and candidate_matrix.get("promotion_ready") is not False:
        failures.append("candidate matrix is unexpectedly promotion-ready")
    if load_slot_route_limit and load_slot_route_limit.get("passed") is not True:
        failures.append("load-slot route-limit guard is not passing")

    if baseline:
        if baseline.get("load_slot") != target_load_slot:
            failures.append(f"baseline load slot is {baseline.get('load_slot')}, expected {target_load_slot}")
        if baseline.get("load_succeeded") is not True:
            failures.append("baseline row-0 route no longer reaches LOADSAVE/PlayGame")
        if baseline.get("map_click_hits_building") is not True:
            failures.append("baseline row-0 click no longer hits the route building")
        if baseline.get("castle_overview_reached") is not True:
            failures.append("baseline row-0 route no longer reaches castle overview")
        if baseline.get("owner_flag_zero_blocker") is not True:
            failures.append("baseline no longer proves the owner-flag-zero blocker")

    if route_candidate.get("save_slot") != 5:
        failures.append(f"route-compatible candidate save slot is {route_candidate.get('save_slot')}, expected 5")
    if route_candidate.get("record_index") != summary.get("baseline_route_index"):
        failures.append(
            "route-compatible candidate record index does not match the proven baseline route index"
        )
    if route_candidate.get("action_eligible") is not True or not route_candidate.get("bit2"):
        failures.append("route-compatible candidate is not action eligible")
    if slot5_status.get("status") != "timeout_before_loadsave":
        failures.append(f"slot5 status is {slot5_status.get('status')}, expected timeout_before_loadsave")
    if slot2_status.get("status") != "loads_but_click_misses_castle":
        failures.append(
            f"slot2 status is {slot2_status.get('status')}, expected loads_but_click_misses_castle"
        )
    if route_limit_summary.get("recent_slot5_blocked") is not True:
        failures.append("load-slot route-limit guard no longer shows recent slot5 blocked")

    if path_is_under(fixture_root, repo_root):
        failures.append(f"fixture root is inside the repository: {fixture_root}")
    if same_path(fixture_save, source_save):
        failures.append("fixture destination would overwrite the source save")
    if source_save_text.replace("/", "\\").lower() == r"c:\clash\save\0.dat":
        failures.append("source save is already slot 0; fixture would not test the slot-5 save state")

    plan = {
        "proof_class": "non_natural_isolated_fixture",
        "promotion_ready": False,
        "stable_stage_should_change": False,
        "preferred_next_step": "copy_slot5_save_as_isolated_slot0_then_run_row0_hidden_probe",
        "source_save": str(source_save),
        "source_save_slot": route_candidate.get("save_slot"),
        "source_record_index": route_candidate.get("record_index"),
        "source_record_position": route_candidate.get("position"),
        "source_flags_1a0": route_candidate.get("flags_1a0_hex"),
        "fixture_root": str(fixture_root),
        "fixture_save": str(fixture_save),
        "target_load_slot": target_load_slot,
        "target_row_already_proven": bool(
            baseline.get("load_slot") == target_load_slot
            and baseline.get("load_succeeded") is True
            and baseline.get("map_click_hits_building") is True
            and baseline.get("castle_overview_reached") is True
        ),
        "must_not_mutate": [r"C:\Clash\save", str(repo_root)],
        "runtime_followup_needed": [
            "create the isolated workdir outside the repository",
            "copy only the selected save as save\\0.dat inside that workdir",
            "run the hidden-desktop row-0 right-bottom natural-route probe from the isolated workdir",
            "require LOADSAVE/PlayGame, nonzero owner-flag bit 0x02, owner/action draw rows, and no AV rows",
            "keep the result labeled non-natural fixture evidence until rows 3-5 naturally enter the load menu",
        ],
        "promotion_blockers_preserved": [
            "manual DirectInput proof is still absent",
            "natural slot-5 menu loading is still blocked before LOADSAVE",
            "fixture evidence must not change the stable stage by itself",
        ],
    }

    return {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "passed": not failures,
        "runtime_policy": RUNTIME_POLICY,
        "guard_policy": GUARD_POLICY,
        "candidate_matrix_json": str(candidate_matrix_json),
        "load_slot_route_limit_json": str(load_slot_route_limit_json),
        "summary": {
            "candidate_matrix_passed": candidate_matrix.get("passed"),
            "load_slot_route_limit_passed": load_slot_route_limit.get("passed"),
            "baseline_route_index": summary.get("baseline_route_index"),
            "route_candidate": route_candidate,
            "slot2_status": slot2_status.get("status"),
            "slot5_status": slot5_status.get("status"),
            "recent_slot5_blocked": route_limit_summary.get("recent_slot5_blocked"),
            "fixture_save": str(fixture_save),
            "proof_class": plan["proof_class"],
            "promotion_ready": plan["promotion_ready"],
            "stable_stage_should_change": plan["stable_stage_should_change"],
        },
        "plan": plan,
        "failures": failures,
    }


def write_markdown(path: Path, report: dict[str, Any]) -> None:
    summary = report.get("summary") or {}
    plan = report.get("plan") or {}
    route_candidate = summary.get("route_candidate") or {}
    lines = [
        "# Right-Bottom Slot Fixture Plan",
        "",
        f"- Status: {status_text(bool(report.get('passed')))}",
        f"- Generated: `{report['generated_at']}`",
        f"- Runtime policy: {report['runtime_policy']}",
        f"- Guard policy: {report['guard_policy']}",
        f"- Candidate matrix: `{report['candidate_matrix_json']}`",
        f"- Load-slot route limit: `{report['load_slot_route_limit_json']}`",
        "",
        "## Decision",
        "",
        f"- Preferred next step: `{plan.get('preferred_next_step')}`",
        f"- Proof class: `{plan.get('proof_class')}`",
        f"- Promotion ready: `{plan.get('promotion_ready')}`",
        f"- stable_stage_should_change: `{plan.get('stable_stage_should_change')}`",
        f"- Source save: `{plan.get('source_save')}`",
        f"- Fixture save: `{plan.get('fixture_save')}`",
        f"- Target load slot: `{plan.get('target_load_slot')}`",
        f"- Target row already proven: `{plan.get('target_row_already_proven')}`",
        "",
        "## Evidence Inputs",
        "",
        f"- Baseline route index: `{summary.get('baseline_route_index')}`",
        f"- Route candidate: save slot `{route_candidate.get('save_slot')}`, record `{route_candidate.get('record_index')}`, position `{route_candidate.get('position')}`, flags `{route_candidate.get('flags_1a0_hex')}`",
        f"- Slot 2 status: `{summary.get('slot2_status')}`",
        f"- Slot 5 status: `{summary.get('slot5_status')}`",
        f"- Recent slot-5 blocked: `{summary.get('recent_slot5_blocked')}`",
        "",
        "## Follow-Up Requirements",
        "",
    ]
    lines.extend(f"- {item}" for item in plan.get("runtime_followup_needed") or [])
    lines.extend(["", "## Promotion Blockers Preserved", ""])
    lines.extend(f"- {item}" for item in plan.get("promotion_blockers_preserved") or [])
    if report.get("failures"):
        lines.extend(["", "## Failures", ""])
        lines.extend(f"- {failure}" for failure in report["failures"])
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-matrix-json", type=Path, default=DEFAULT_CANDIDATE_MATRIX_JSON)
    parser.add_argument("--load-slot-route-limit-json", type=Path, default=DEFAULT_LOAD_SLOT_ROUTE_LIMIT_JSON)
    parser.add_argument("--fixture-root", type=Path, default=DEFAULT_FIXTURE_ROOT)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--target-load-slot", type=int, default=0)
    parser.add_argument("--write-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--write-markdown", "--write-md", dest="write_markdown", type=Path, default=DEFAULT_MD)
    parser.add_argument("--require-pass", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_plan(
        candidate_matrix_json=args.candidate_matrix_json,
        load_slot_route_limit_json=args.load_slot_route_limit_json,
        fixture_root=args.fixture_root,
        repo_root=args.repo_root,
        target_load_slot=args.target_load_slot,
    )
    print(f"overall: {status_text(bool(report.get('passed')))}")
    print(f"runtime-policy: {report['runtime_policy']}")
    print(f"proof-class: {report['plan'].get('proof_class')}")
    print(f"promotion-ready: {report['plan'].get('promotion_ready')}")
    print(f"fixture-save: {report['plan'].get('fixture_save')}")
    if report["failures"]:
        print("failures:")
        for failure in report["failures"]:
            print(f"  - {failure}")
    if args.write_json:
        args.write_json.parent.mkdir(parents=True, exist_ok=True)
        args.write_json.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if args.write_markdown:
        write_markdown(args.write_markdown, report)
    if args.require_pass and not report["passed"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
