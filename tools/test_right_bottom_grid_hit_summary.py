#!/usr/bin/env python3
"""Fixture tests for the right-bottom controlled grid-hit parser."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "right_bottom_grid_hit_summary.py"
sys.path.insert(0, str(ROOT / "tools"))

import right_bottom_grid_hit_summary  # noqa: E402


def run_script(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def write_log(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")
    return path


def good_log_text() -> str:
    return """
RBGRID_OWNER_SETUP_CALL owner=041bc71a owner_flag_old=0x00 scroll=(10,17) surface=0a2fedd0 sz=(800,600)
RBGRID_OWNER_FLAG_FORCED owner=041bc71a owner_flag_new=0x02 RBGRID_WRITE_532154 ret=0040ae16 new=0a62b610 d532150=041bc71a d53214c=00000001 surface=0a2fedd0 sz=(800,600) short_return=1
RBGRID_ACTION_CALL desc=00511d40 owner=041bc71a owner_flag=0x02 d532150=041bc71a d53214c=00000001 d532154=0a62b610 surface=0a2fedd0 sz=(800,600) skip_prelude=1
RBGRID_433914_CALL_435BC0 ret=0040ae16 owner_arg=041bc71a owner_global=041bc71a owner_flag=0x02 d532218=00000000 d5322c8=0 surface=0a2fedd0 sz=(800,600)
RBGRID_OWNER_435BC0_ENTRY ret=00433919 owner_arg=041bc71a d532218_before=00000000 d5322c8_before=0 d532210_before=0 surface=0a2fedd0 sz=(800,600) mouse=(420,166)
RBGRID_WRITE_532218 ret=00000003 new=041bc71a selected_index=0 hover_slot=0 surface=0a2fedd0 sz=(800,600)
RBGRID_WRITE_5322C8 ret=00000003 new=-1 d532218=041bc71a selected_index=0 surface=0a2fedd0 sz=(800,600)
RBGRID_PANEL_DRAW_4347A0 ret=00435d84 owner=041bc71a selected_index=0 hover_slot=-1 render=0a2fedd0 map_surface=0a2fedd0 sz=(800,600)
RBGRID_GRID_DRAW_434E20 ret=00435172 owner=041bc71a selected_index=0 hover_slot=-1 render=0a2fedd0 map_surface=0a2fedd0 sz=(800,600)
RBGRID_STATUS_DRAW_435280 ret=00435d8e owner=041bc71a selected_index=0 hover_slot=-1 mouse=(420,166) render=0a2fedd0 map_surface=0a2fedd0
RBGRID_ACTION_BOX_435500 ret=00435d93 owner=041bc71a selected_index=0 hover_slot=-1 mouse=(420,166) render=0051d4c0 map_surface=0a2fedd0
RBGRID_FORCE_NATIVE target=grid0 native=(450,73) shift=6 raw=(00007080,00001240) selected_index=0 hover_slot=-1
RBGRID_GRID_ROUTE_ENTRY selected_index=0 hover_slot=-1 mouse=(450,73)
RBGRID_GRID_GATE raw_result=0 forced_result=1 mouse=(450,73)
RBGRID_GRID_CALL mouse=(450,73) raw=(00007080,00001240) expected_native=(450,73)
RBGRID_GRID_ENTRY mouse=(450,73) raw=(00007080,00001240) expected_native=(450,73) shift=6 selected_index=0 hover_slot=-1
RBGRID_GRID_RESULT result=0 expected=0 mouse=(450,73) selected_index=0 hover_slot=-1
RBGRID_GRID_ACCEPT result=0 exit_armed=1 hover_slot=-1
RBGRID_4338E0_AFTER_435BC0 ret=0040ae16 d532218=041bc71a selected_index=0 hover_slot=0 surface=0a2fedd0 sz=(800,600)
RBGRID_SURFDUMP_READY after_action=1 surface=0a2fedd0 size=(800,600) base=0a5a0030 bytes=480000 d532150=041bc71a d532218=041bc71a selected_index=0 hover_slot=0 scroll=(10,17)
SURFDUMP_READY redraw_seq=991 surface=0a2fedd0 size=(800,600) base=0a5a0030 bytes=480000 SURFDUMP_HOST_READY
"""


def test_good_log_summary(fixture: Path) -> None:
    log = write_log(fixture / "good.log", good_log_text())
    summary = right_bottom_grid_hit_summary.parse_log(log, [450, 73], 0)
    assert summary["ready"] is True, summary
    assert summary["grid_hit_ok"] is True, summary
    assert summary["last_grid_entry"] == [450, 73], summary
    assert summary["last_grid_result"] == 0, summary
    assert summary["forced_gate_count"] == 1, summary
    assert summary["failure_exit_count"] == 0, summary
    assert summary["draw_row_count"] == 4, summary
    assert summary["av_count"] == 0, summary


def test_cli_required_flags_pass_and_write_outputs(fixture: Path) -> None:
    log = write_log(fixture / "good.log", good_log_text())
    out_json = fixture / "summary.json"
    out_md = fixture / "summary.md"
    run = run_script(
        str(log),
        "--write-json",
        str(out_json),
        "--write-md",
        str(out_md),
        "--require-ready",
        "--require-grid-hit",
        "--require-draw-rows",
        "--forbid-failure-exit",
    )
    assert run.returncode == 0, run.stdout + run.stderr
    written = json.loads(out_json.read_text(encoding="utf-8"))
    assert written["grid_hit_ok"] is True, written
    assert "- Grid hit ok: True" in out_md.read_text(encoding="utf-8")


def test_cli_required_flags_fail_closed(fixture: Path) -> None:
    cases = [
        ("missing-ready", good_log_text().replace("RBGRID_SURFDUMP_READY", "REMOVED_READY").replace("SURFDUMP_READY", "REMOVED_SURF"), "--require-ready"),
        ("wrong-entry", good_log_text().replace("mouse=(450,73)", "mouse=(451,73)"), "--require-grid-hit"),
        ("wrong-result", good_log_text().replace("RBGRID_GRID_RESULT result=0", "RBGRID_GRID_RESULT result=1"), "--require-grid-hit"),
        ("missing-draw", "\n".join(line for line in good_log_text().splitlines() if "_DRAW_" not in line and "ACTION_BOX" not in line), "--require-draw-rows"),
        ("failure-exit", good_log_text() + "\nRBGRID_FAIL_EXIT_ARM selected_index=0 hover_slot=-1 mouse=(450,73)", "--forbid-failure-exit"),
    ]
    for name, text, flag in cases:
        log = write_log(fixture / f"{name}.log", text)
        run = run_script(str(log), flag)
        assert run.returncode == 2, f"{name}: {run.stdout}{run.stderr}"

    av_log = write_log(fixture / "av.log", good_log_text() + "\nAccess violation - code c0000005")
    av_run = run_script(str(av_log))
    assert av_run.returncode == 2, av_run.stdout + av_run.stderr


def run_tests() -> None:
    fixture = ROOT / ".codex-loop" / "tmp-tests" / "right-bottom-grid-hit-summary-fixture"
    shutil.rmtree(fixture, ignore_errors=True)
    fixture.mkdir(parents=True)
    try:
        test_good_log_summary(fixture / "parse")
        test_cli_required_flags_pass_and_write_outputs(fixture / "cli-pass")
        test_cli_required_flags_fail_closed(fixture / "cli-fail")
    finally:
        shutil.rmtree(fixture, ignore_errors=True)


def main() -> int:
    run_tests()
    print("right-bottom grid hit summary tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
