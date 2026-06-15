#!/usr/bin/env python3
"""Fixture tests for the handoff freshness guard."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "handoff_freshness_guard.py"
sys.path.insert(0, str(ROOT / "tools"))

import handoff_freshness_guard  # noqa: E402


@contextmanager
def pushd(path: Path) -> Iterator[None]:
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


def run_script(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def write_good_handoff(
    root: Path,
    *,
    stale_phrase: str | None = None,
    omit_route_link: bool = False,
    omit_owner_flag_inventory: bool = False,
    omit_load_slot_route_limit: bool = False,
    omit_load_slot_transition_readiness: bool = False,
    omit_loop_load_slot_transition_readiness: bool = False,
    omit_visible_launcher_guard: bool = False,
    omit_completion_summary: bool = False,
) -> argparse.Namespace:
    next_md = root / ".codex-loop" / "NEXT.md"
    state_md = root / ".codex-loop" / "STATE.md"
    tasks_md = root / ".codex-loop" / "TASKS.md"
    evidence = root / "captures" / "hd-map-evidence-current.md"
    progress = root / "docs/hd/HD_MOD_PROGRESS.md"
    question = root / "wiki" / "questions" / "how-should-the-bottom-tooltip-be-recovered.md"
    for path in [next_md, state_md, tasks_md, evidence, progress, question]:
        path.parent.mkdir(parents=True, exist_ok=True)

    route_links = ""
    if not omit_route_link:
        route_links = (
            "captures/current/right-bottom-route-timing-guard-current.md\n"
            "captures/current/right-bottom-route-timing-guard-tests-current.md\n"
        )
    owner_flag_inventory = ""
    if not omit_owner_flag_inventory:
        owner_flag_inventory = (
            "The right-bottom owner flag inventory is "
            "captures/current/right-bottom-owner-flag-inventory-current.md with tests at "
            "captures/current/right-bottom-owner-flag-inventory-tests-current.md, and it records "
            "zero natural owner/action routes in the archived CDB corpus.\n"
        )
    load_slot_route_limit = ""
    if not omit_load_slot_route_limit:
        load_slot_route_limit = (
            "The load-slot route limit boundary is "
            "captures/current/load-slot-route-limit-current.md with tests at "
            "captures/current/load-slot-route-limit-tests-current.md, and it records slots 3-5 "
            "as route-harness blocked before force-select and LOADSAVE.\n"
        )
    load_slot_transition_readiness = ""
    if not omit_load_slot_transition_readiness:
        load_slot_transition_readiness = (
            "The load-slot transition readiness matrix is "
            "captures/current/load-slot-transition-readiness-current.md with tests at "
            "captures/current/load-slot-transition-readiness-tests-current.md, and it records "
            "ready_for_hidden_transition_probe while remaining non-promoting.\n"
        )
    visible_launcher = ""
    if not omit_visible_launcher_guard:
        visible_launcher = (
            "The visible runtime launcher guard is "
            "captures/current/visible-runtime-launcher-guard-current.md with tests at "
            "captures/current/visible-runtime-launcher-guard-tests-current.md, and "
            "legacy launchers require -AllowVisibleRuntime before visible runtime work.\n"
        )
    completion_summary = ""
    if not omit_completion_summary:
        completion_summary = (
            "The generated percentage summary is "
            "captures/current/current-completion-summary-current.md and keeps "
            "full-game completion below 100% until manual proof exists.\n"
        )
    common = (
        "The right-bottom route timing guard closes the current no-popup CDB/proxy "
        "route timing layer while stable-stage promotion still needs "
        "manual/visible DirectInput proof or an explicit CDB-only promotion override. "
        "Do not run visible/manual validation without explicit user approval. "
        "Do not launch Clash95, CDB, wrappers, PowerShell harnesses, or visible windows "
        "unless the user explicitly approves. "
        "The manual DirectInput checklist is captures/current/manual-directinput-validation-checklist-current.md "
        "and records pending_manual_validation. "
        "The manual DirectInput proof template is "
        "captures/current/manual-directinput-proof-template-current.md and records "
        "template_valid_as_proof=False.\n"
        f"{completion_summary}"
        f"{visible_launcher}"
        f"{owner_flag_inventory}"
        f"{load_slot_route_limit}"
        f"{load_slot_transition_readiness}"
        f"{route_links}"
    )
    extra = f"\n{stale_phrase}\n" if stale_phrase else ""
    loop_common = common
    if omit_loop_load_slot_transition_readiness and load_slot_transition_readiness:
        loop_common = loop_common.replace(load_slot_transition_readiness, "")
    next_md.write_text(loop_common + extra, encoding="utf-8")
    state_md.write_text(loop_common, encoding="utf-8")
    tasks_md.write_text("[x] Gather broader route/input safety.\n" + loop_common, encoding="utf-8")
    evidence.write_text(common, encoding="utf-8")
    progress.write_text(common, encoding="utf-8")
    question.write_text(common, encoding="utf-8")
    return argparse.Namespace(
        next_md=next_md,
        state_md=state_md,
        tasks_md=tasks_md,
        evidence_index=evidence,
        progress_md=progress,
        bottom_question_md=question,
    )


def test_guard_passes_current_handoff(fixture: Path) -> None:
    args = write_good_handoff(fixture)
    with pushd(fixture):
        guard = handoff_freshness_guard.build_guard(args)
    assert guard["passed"] is True, guard
    assert not guard["failures"], guard


def test_guard_rejects_stale_route_safety_phrase(fixture: Path) -> None:
    args = write_good_handoff(
        fixture,
        stale_phrase="The next right-bottom target is broader route/input safety for this validation stage.",
    )
    with pushd(fixture):
        guard = handoff_freshness_guard.build_guard(args)
    assert guard["passed"] is False, guard
    assert any("stale blocker phrase" in failure for failure in guard["failures"]), guard


def test_guard_rejects_stale_legacy_visible_capture_tasks(fixture: Path) -> None:
    args = write_good_handoff(
        fixture,
        stale_phrase=(
            "- [ ] Validate the bounds-guarded dynamic-origin candidate outside the debugger.\n"
            "- [ ] Fix frame capture/window selection for CDB map probes; the current PNG can include the debugger console.\n"
        ),
    )
    with pushd(fixture):
        guard = handoff_freshness_guard.build_guard(args)
    assert guard["passed"] is False, guard
    assert any("outside the debugger" in failure.lower() for failure in guard["failures"]), guard
    assert any("cdb map probes" in failure.lower() for failure in guard["failures"]), guard


def test_guard_rejects_stale_vm_visual_smoke_tasks(fixture: Path) -> None:
    args = write_good_handoff(
        fixture,
        stale_phrase=(
            "- [ ] Run a true clean visual/gameplay smoke pass on the v2 conditional-switch candidate.\n"
            "- [ ] Enable Windows Sandbox (`Containers-DisposableClientVM`) and run the VM capture.\n"
            "- [ ] Finish the log-sentinel early-stop mode for VM CDB route probes.\n"
        ),
    )
    with pushd(fixture):
        guard = handoff_freshness_guard.build_guard(args)
    assert guard["passed"] is False, guard
    assert any("conditional-switch" in failure.lower() for failure in guard["failures"]), guard
    assert any("windows sandbox" in failure.lower() for failure in guard["failures"]), guard
    assert any("log-sentinel" in failure.lower() for failure in guard["failures"]), guard


def test_guard_rejects_missing_route_timing_links(fixture: Path) -> None:
    args = write_good_handoff(fixture, omit_route_link=True)
    with pushd(fixture):
        guard = handoff_freshness_guard.build_guard(args)
    assert guard["passed"] is False, guard
    assert any("right-bottom-route-timing-guard-current.md" in failure for failure in guard["failures"]), guard


def test_guard_rejects_missing_owner_flag_inventory_artifacts(fixture: Path) -> None:
    args = write_good_handoff(fixture, omit_owner_flag_inventory=True)
    with pushd(fixture):
        guard = handoff_freshness_guard.build_guard(args)
    assert guard["passed"] is False, guard
    assert any("owner_flag_inventory_artifacts" in failure for failure in guard["failures"]), guard


def test_guard_rejects_missing_load_slot_route_limit_artifacts(fixture: Path) -> None:
    args = write_good_handoff(fixture, omit_load_slot_route_limit=True)
    with pushd(fixture):
        guard = handoff_freshness_guard.build_guard(args)
    assert guard["passed"] is False, guard
    assert any("load_slot_route_limit_artifacts" in failure for failure in guard["failures"]), guard


def test_guard_rejects_missing_load_slot_transition_readiness_artifacts(fixture: Path) -> None:
    args = write_good_handoff(fixture, omit_load_slot_transition_readiness=True)
    with pushd(fixture):
        guard = handoff_freshness_guard.build_guard(args)
    assert guard["passed"] is False, guard
    assert any("load_slot_transition_readiness_artifacts" in failure for failure in guard["failures"]), guard


def test_guard_rejects_missing_loop_load_slot_transition_readiness_artifacts(fixture: Path) -> None:
    args = write_good_handoff(fixture, omit_loop_load_slot_transition_readiness=True)
    with pushd(fixture):
        guard = handoff_freshness_guard.build_guard(args)
    assert guard["passed"] is False, guard
    assert any("loop_load_slot_transition_readiness_artifacts" in failure for failure in guard["failures"]), guard


def test_guard_rejects_missing_manual_or_override_blocker(fixture: Path) -> None:
    args = write_good_handoff(fixture)
    args.next_md.write_text(
        args.next_md.read_text(encoding="utf-8").replace("explicit CDB-only promotion", "approval"),
        encoding="utf-8",
    )
    for path in [args.state_md, args.tasks_md, args.evidence_index, args.progress_md, args.bottom_question_md]:
        path.write_text(
            path.read_text(encoding="utf-8").replace("explicit CDB-only promotion", "approval"),
            encoding="utf-8",
        )
    with pushd(fixture):
        guard = handoff_freshness_guard.build_guard(args)
    assert guard["passed"] is False, guard
    assert any("manual_or_override_blocker" in failure for failure in guard["failures"]), guard


def test_guard_rejects_missing_manual_checklist_artifact(fixture: Path) -> None:
    args = write_good_handoff(fixture)
    for path in [args.next_md, args.state_md, args.tasks_md, args.evidence_index, args.progress_md, args.bottom_question_md]:
        path.write_text(
            path.read_text(encoding="utf-8").replace(
                "captures/current/manual-directinput-validation-checklist-current.md",
                "manual checklist",
            ),
            encoding="utf-8",
        )
    with pushd(fixture):
        guard = handoff_freshness_guard.build_guard(args)
    assert guard["passed"] is False, guard
    assert any("manual_checklist_artifact" in failure for failure in guard["failures"]), guard


def test_guard_rejects_missing_manual_proof_template_artifact(fixture: Path) -> None:
    args = write_good_handoff(fixture)
    for path in [args.next_md, args.state_md, args.tasks_md, args.evidence_index, args.progress_md, args.bottom_question_md]:
        text = path.read_text(encoding="utf-8")
        text = text.replace(
            "captures/current/manual-directinput-proof-template-current.md",
            "manual proof template",
        ).replace("template_valid_as_proof=False", "template pending")
        path.write_text(text, encoding="utf-8")
    with pushd(fixture):
        guard = handoff_freshness_guard.build_guard(args)
    assert guard["passed"] is False, guard
    assert any("manual_proof_template_artifact" in failure for failure in guard["failures"]), guard


def test_guard_rejects_missing_completion_summary_artifact(fixture: Path) -> None:
    args = write_good_handoff(fixture, omit_completion_summary=True)
    with pushd(fixture):
        guard = handoff_freshness_guard.build_guard(args)
    assert guard["passed"] is False, guard
    assert any("completion_summary_artifact" in failure for failure in guard["failures"]), guard


def test_guard_rejects_missing_no_popup_operator_preference(fixture: Path) -> None:
    args = write_good_handoff(fixture)
    for path in [args.next_md, args.state_md, args.tasks_md, args.evidence_index, args.progress_md, args.bottom_question_md]:
        text = path.read_text(encoding="utf-8")
        text = text.replace(
            "Do not launch Clash95, CDB, wrappers, PowerShell harnesses, or visible windows "
            "unless the user explicitly approves. ",
            "",
        ).replace(
            "Do not launch Clash95, CDB, wrappers, PowerShell harnesses, or visible\n"
            "windows unless the user explicitly approves. ",
            "",
        )
        path.write_text(text, encoding="utf-8")
    with pushd(fixture):
        guard = handoff_freshness_guard.build_guard(args)
    assert guard["passed"] is False, guard
    assert any("no_popup_operator_preference" in failure for failure in guard["failures"]), guard


def test_guard_rejects_missing_visible_runtime_launcher_guard(fixture: Path) -> None:
    args = write_good_handoff(fixture, omit_visible_launcher_guard=True)
    with pushd(fixture):
        guard = handoff_freshness_guard.build_guard(args)
    assert guard["passed"] is False, guard
    assert any("visible_runtime_launcher_guard" in failure for failure in guard["failures"]), guard


def test_cli_writes_outputs_and_fails_closed(fixture: Path) -> None:
    args = write_good_handoff(fixture)
    out_json = fixture / "guard.json"
    out_md = fixture / "guard.md"
    good = run_script(
        fixture,
        "--next-md",
        str(args.next_md),
        "--state-md",
        str(args.state_md),
        "--tasks-md",
        str(args.tasks_md),
        "--evidence-index",
        str(args.evidence_index),
        "--progress-md",
        str(args.progress_md),
        "--bottom-question-md",
        str(args.bottom_question_md),
        "--write-json",
        str(out_json),
        "--write-markdown",
        str(out_md),
        "--require-pass",
    )
    assert good.returncode == 0, good.stdout + good.stderr
    assert json.loads(out_json.read_text(encoding="utf-8"))["passed"] is True
    assert "- Overall: PASS" in out_md.read_text(encoding="utf-8")

    args.next_md.write_text(
        args.next_md.read_text(encoding="utf-8")
        + "\nnext no-popup target is broader route/input safety\n",
        encoding="utf-8",
    )
    bad_json = fixture / "bad-guard.json"
    bad_md = fixture / "bad-guard.md"
    bad = run_script(
        fixture,
        "--next-md",
        str(args.next_md),
        "--state-md",
        str(args.state_md),
        "--tasks-md",
        str(args.tasks_md),
        "--evidence-index",
        str(args.evidence_index),
        "--progress-md",
        str(args.progress_md),
        "--bottom-question-md",
        str(args.bottom_question_md),
        "--write-json",
        str(bad_json),
        "--write-markdown",
        str(bad_md),
        "--require-pass",
    )
    assert bad.returncode == 2, bad.stdout + bad.stderr
    assert json.loads(bad_json.read_text(encoding="utf-8"))["passed"] is False
    assert "- Overall: FAIL" in bad_md.read_text(encoding="utf-8")


def run_tests() -> None:
    fixture = ROOT / ".codex-loop" / "tmp-tests" / "handoff-freshness-fixture"
    shutil.rmtree(fixture, ignore_errors=True)
    fixture.mkdir(parents=True)
    try:
        test_guard_passes_current_handoff(fixture / "passes")
        test_guard_rejects_stale_route_safety_phrase(fixture / "stale")
        test_guard_rejects_stale_legacy_visible_capture_tasks(fixture / "stale-legacy-visible-capture")
        test_guard_rejects_stale_vm_visual_smoke_tasks(fixture / "stale-vm-visual-smoke")
        test_guard_rejects_missing_route_timing_links(fixture / "missing-route")
        test_guard_rejects_missing_owner_flag_inventory_artifacts(fixture / "missing-owner-flag-inventory")
        test_guard_rejects_missing_load_slot_route_limit_artifacts(fixture / "missing-load-slot-route-limit")
        test_guard_rejects_missing_load_slot_transition_readiness_artifacts(
            fixture / "missing-load-slot-transition-readiness"
        )
        test_guard_rejects_missing_loop_load_slot_transition_readiness_artifacts(
            fixture / "missing-loop-load-slot-transition-readiness"
        )
        test_guard_rejects_missing_manual_or_override_blocker(fixture / "missing-blocker")
        test_guard_rejects_missing_manual_checklist_artifact(fixture / "missing-checklist")
        test_guard_rejects_missing_manual_proof_template_artifact(fixture / "missing-template")
        test_guard_rejects_missing_completion_summary_artifact(fixture / "missing-completion-summary")
        test_guard_rejects_missing_no_popup_operator_preference(fixture / "missing-no-popup-preference")
        test_guard_rejects_missing_visible_runtime_launcher_guard(fixture / "missing-visible-launcher")
        test_cli_writes_outputs_and_fails_closed(fixture / "cli")
    finally:
        shutil.rmtree(fixture, ignore_errors=True)


def main() -> int:
    run_tests()
    print("handoff freshness guard tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
