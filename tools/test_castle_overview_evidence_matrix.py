#!/usr/bin/env python3
"""Fixture tests for the castle overview evidence matrix helper."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "castle_overview_evidence_matrix.py"
sys.path.insert(0, str(ROOT / "tools"))

import castle_overview_evidence_matrix  # noqa: E402


CHECK_NAMES = (
    "patch_stage",
    "overview_visual",
    "focused_hitbox",
    "visible_multihit",
    "owner_records",
    "forced_hitmap",
    "dormant_multihit",
)

GOOD_FOCUSED_LOG = """
CASTLEOV_HITBOX_OVERVIEW_POST_DRAW main_surface=0a06fd90 main_size=(800,600) overview_surface=0a06fcd0 overview_size=(640,480) owner_screen=0946c71a mouse=(371,107) click_flag=00000001 button0=0x80
CASTLEOV_HITBOX_DISPLAYED_HITTEST_BEGIN displayed=(371,107) expected_native=(291,47) raw=(00005cc0,00001ac0) click_flag=00000001 button0=0x80
CASTLEOV_HITBOX_DISPLAYED_RESULT raw_hit=248 adjusted_hit=0 mouse=(371,107) raw=(00005cc0,00001ac0) target_raw=248
CASTLEOV_HITBOX_DISPLAYED_WRAPPER_OK raw_hit=248 mouse=(371,107) raw=(00005cc0,00001ac0) target_raw=248
CASTLEOV_HITBOX_DESCRIPTOR_INSTALL command=134 callback=0044fe70 text=00000003 arg_count=5171110 owner_screen=0946c71a surface=0a06fd90 sz=(800,600) mouse=(371,107)
CASTLEOV_HITBOX_CLICK_GATE command=134 callback=0044fe70 gate=1 mouse=(371,107) click_flag=00000001 button0=0x80
CASTLEOV_HITBOX_CLICK_GATE_OK command=134 callback=0044fe70 gate=1 displayed=(371,107) native=(291,47) surface=0a06fd90 size=(800,600) base=0a130030 bytes=480000
CASTLEOV_HITBOX_SURFDUMP_READY reason=click_gate_ok surface=0a06fd90 size=(800,600) base=0a130030 bytes=480000 owner_screen=0946c71a exit_flag=0
SURFDUMP_READY redraw_seq=995 surface=0a06fd90 size=(800,600) base=0a130030 bytes=480000
SURFDUMP_HOST_READY
CASTLEOV_HITBOX_CALLBACK_SUPPRESSED command=134 callback=0044fe70 reason=probe_gate_complete
"""

GOOD_MULTI_LOG = """
CASTLEOV_MULTI_TARGET_SET index=0 raw=0xf8 command=0x86 callback=0x0044fe70 expected_gate=1
CASTLEOV_MULTI_HITTEST_RESULT index=0 raw_hit=0xf8
CASTLEOV_MULTI_DESCRIPTOR_INSTALL index=0 command=0x86 callback=0x0044fe70
CASTLEOV_MULTI_CLICK_GATE index=0 command=0x86 callback=0x0044fe70 gate=1
CASTLEOV_MULTI_TARGET_DONE index=0 command=0x86 callback=0x0044fe70 gate=1 raw=0xf8
CASTLEOV_MULTI_SURFDUMP_READY size=(800,600)
"""


def run_script(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def fake_check(name: str, *, passed: bool = True) -> dict[str, Any]:
    failures = [] if passed else [f"intentional {name} fixture failure"]
    result: dict[str, Any] = {"passed": passed, "failures": failures}
    if name == "patch_stage":
        result.update(
            {
                "exe": "fixture.exe",
                "stage": "castlecenter-all",
                "resolved_stage": castle_overview_evidence_matrix.resolve_stage("castlecenter-all"),
                "sha256": "fixture",
                "patches": {"patched": 134, "original": 0, "unexpected": 0, "total": 134},
            }
        )
    return result


def args_for(fixture: Path) -> argparse.Namespace:
    return argparse.Namespace(
        stage="castlecenter-all",
        patch_exe=fixture / "fixture.exe",
        overview_run=fixture / "overview",
        barracks_run=fixture / "barracks",
        focused_hitbox_run=fixture / "focused",
        visible_multihit_run=fixture / "visible",
        owner_records_raw=fixture / "owner.raw",
        forced_hitmap_raw=fixture / "hitmap.raw",
        dormant_multihit_run=fixture / "dormant",
        threshold=12,
        max_echo_percent=25.0,
    )


def with_fake_gates(
    failing_check: str | None,
    callback: Callable[[], None],
) -> None:
    original_patch_stage_gate = castle_overview_evidence_matrix.patch_stage_gate
    original_overview_gate = castle_overview_evidence_matrix.castle_overview_gate.build_gate
    original_focused_hitbox_gate = castle_overview_evidence_matrix.focused_hitbox_gate
    original_multihit_gate = castle_overview_evidence_matrix.multihit_gate
    original_owner_records_gate = castle_overview_evidence_matrix.owner_records_gate
    original_hitmap_gate = castle_overview_evidence_matrix.hitmap_gate

    def check(name: str) -> dict[str, Any]:
        return fake_check(name, passed=name != failing_check)

    try:
        castle_overview_evidence_matrix.patch_stage_gate = lambda *_args, **_kwargs: check("patch_stage")
        castle_overview_evidence_matrix.castle_overview_gate.build_gate = lambda **_kwargs: check("overview_visual")
        castle_overview_evidence_matrix.focused_hitbox_gate = lambda *_args, **_kwargs: check("focused_hitbox")

        def multihit(_run: Path, label: str) -> dict[str, Any]:
            name = "dormant_multihit" if "dormant" in label else "visible_multihit"
            return check(name)

        castle_overview_evidence_matrix.multihit_gate = multihit
        castle_overview_evidence_matrix.owner_records_gate = lambda *_args, **_kwargs: check("owner_records")
        castle_overview_evidence_matrix.hitmap_gate = lambda *_args, **_kwargs: check("forced_hitmap")
        callback()
    finally:
        castle_overview_evidence_matrix.patch_stage_gate = original_patch_stage_gate
        castle_overview_evidence_matrix.castle_overview_gate.build_gate = original_overview_gate
        castle_overview_evidence_matrix.focused_hitbox_gate = original_focused_hitbox_gate
        castle_overview_evidence_matrix.multihit_gate = original_multihit_gate
        castle_overview_evidence_matrix.owner_records_gate = original_owner_records_gate
        castle_overview_evidence_matrix.hitmap_gate = original_hitmap_gate


def test_matrix_passes_with_all_checks(fixture: Path) -> None:
    def assertions() -> None:
        matrix = castle_overview_evidence_matrix.build_matrix(args_for(fixture))
        assert matrix["passed"] is True, matrix
        assert matrix["promotion_status"] == "validation_stage_only", matrix
        assert "does not launch Clash95" in matrix["runtime_policy"], matrix
        assert set(matrix["checks"]) == set(CHECK_NAMES), matrix

    with_fake_gates(None, assertions)


def test_matrix_fails_when_each_required_check_fails(fixture: Path) -> None:
    for name in CHECK_NAMES:
        def assertions(name: str = name) -> None:
            matrix = castle_overview_evidence_matrix.build_matrix(args_for(fixture / name))
            assert matrix["passed"] is False, matrix
            assert any(f"{name}: intentional {name} fixture failure" in failure for failure in matrix["failures"]), matrix

        with_fake_gates(name, assertions)


def test_cli_writes_outputs_and_fails_closed(fixture: Path) -> None:
    out_json = fixture / "matrix.json"
    out_md = fixture / "matrix.md"
    missing = fixture / "missing"
    run = run_script(
        "--patch-exe",
        str(missing / "candidate.exe"),
        "--overview-run",
        str(missing / "overview"),
        "--barracks-run",
        str(missing / "barracks"),
        "--focused-hitbox-run",
        str(missing / "focused"),
        "--visible-multihit-run",
        str(missing / "visible"),
        "--owner-records-raw",
        str(missing / "owner.raw"),
        "--forced-hitmap-raw",
        str(missing / "hitmap.raw"),
        "--dormant-multihit-run",
        str(missing / "dormant"),
        "--write-json",
        str(out_json),
        "--write-markdown",
        str(out_md),
        "--require-pass",
    )
    assert run.returncode == 2, run.stdout + run.stderr
    written = json.loads(out_json.read_text(encoding="utf-8"))
    assert written["passed"] is False, written
    assert "- Overall: FAIL" in out_md.read_text(encoding="utf-8")


def test_focused_hitbox_gate_requires_displayed_wrapper_proof(fixture: Path) -> None:
    run = fixture / "focused"
    run.mkdir(parents=True)
    log = run / "cdb-surface-dump.log"
    log.write_text(GOOD_FOCUSED_LOG, encoding="utf-8")

    good = castle_overview_evidence_matrix.focused_hitbox_gate(run)
    assert good["passed"] is True, good
    assert good["displayed_wrapper_ok"] is True, good

    log.write_text(
        GOOD_FOCUSED_LOG.replace(
            "CASTLEOV_HITBOX_DISPLAYED_WRAPPER_OK",
            "REMOVED_DISPLAYED_WRAPPER_OK",
        ),
        encoding="utf-8",
    )
    missing_wrapper = castle_overview_evidence_matrix.focused_hitbox_gate(run)
    assert missing_wrapper["passed"] is False, missing_wrapper
    assert missing_wrapper["displayed_wrapper_ok"] is False, missing_wrapper
    assert any("binary wrapper success" in failure for failure in missing_wrapper["failures"]), missing_wrapper


def test_multihit_gate_reports_completion_proof(fixture: Path) -> None:
    run = fixture / "visible"
    run.mkdir(parents=True)
    log = run / "cdb-surface-dump.log"
    log.write_text(GOOD_MULTI_LOG, encoding="utf-8")

    good = castle_overview_evidence_matrix.multihit_gate(run, "visible-command multi-hit")
    assert good["passed"] is True, good
    assert good["targets"][0]["completion_ok"] is True, good
    assert good["targets"][0]["raw_ok"] is True, good
    assert good["targets"][0]["descriptor_ok"] is True, good
    assert good["targets"][0]["gate_ok"] is True, good

    log.write_text(
        GOOD_MULTI_LOG.replace("CASTLEOV_MULTI_TARGET_DONE", "REMOVED_TARGET_DONE"),
        encoding="utf-8",
    )
    missing_completion = castle_overview_evidence_matrix.multihit_gate(run, "visible-command multi-hit")
    assert missing_completion["passed"] is False, missing_completion
    assert missing_completion["targets"][0]["completion_ok"] is False, missing_completion
    assert any("did not prove all targets" in failure for failure in missing_completion["failures"]), missing_completion


def run_tests() -> None:
    fixture = ROOT / ".codex-loop" / "tmp-tests" / "castle-overview-evidence-matrix-fixture"
    shutil.rmtree(fixture, ignore_errors=True)
    fixture.mkdir(parents=True)
    try:
        test_matrix_passes_with_all_checks(fixture / "pass")
        test_matrix_fails_when_each_required_check_fails(fixture / "failures")
        test_cli_writes_outputs_and_fails_closed(fixture / "cli")
        test_focused_hitbox_gate_requires_displayed_wrapper_proof(fixture / "focused-wrapper")
        test_multihit_gate_reports_completion_proof(fixture / "multi-completion")
    finally:
        shutil.rmtree(fixture, ignore_errors=True)


def main() -> int:
    run_tests()
    print("castle overview evidence matrix tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
