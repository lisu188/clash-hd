#!/usr/bin/env python3
"""Fixture tests for the first-mission unit-selection action-bar parser."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "unit_selection_action_bar_summary.py"
sys.path.insert(0, str(ROOT / "tools"))

import unit_selection_action_bar_summary  # noqa: E402


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
SURFDUMP_LOADSAVE selected_arg=0 selected_global=0 accept=1 choice=5 gd=04220030
SURFDUMP_PLAYGAME gd=04220030 map=(100,100) scroll=(10,17) surface=03e9c880 size=(640,480)
UNITSEL_ROUTE_START gd=04220030 player=0 scroll=(10,17) map=(100,100) selected=-1 prior=-1 shift=6 surface=03ace540 size=(800,600)
UNITSEL_INVOKE_408030_THEN_406980 screen=(448,176) raw=(0x00007000,0x00002c00) select_return=00406980 update_return=0040b0c3
UNITSEL_SELECT_TILE map=(16,19) tile=3 selected_before=-1 current=0
UNITSEL_SELECT_SUCCESS eax=1 selected_after=3
UNITSEL_406980_ENTRY ret=0040b0c3 selected=3 prior=-1 d526994=0 render=03ace540 map_surface=03ace540 sz=(800,600)
UNITSEL_40A490_ENTRY ret=0040698c selected=3 prior=-1 current=0 d526994=0
UNITSEL_40A500_ENTRY ret=0040a4f2 eax=00000010 edx=000001b3 ecx=04220030 ebp=00000000 selected=3 prior=-1 d526994=0
UNITSEL_40A500_CALL_423B00 ret=00000003 selected=3 prior=-1 d526994=0
UNITSEL_423B00_ENTRY ret=0040a5f3 eax=00000008 edx=0000087f ecx=04220030 ebp=00000000 selected=3 prior=-1 d526994=0
UNITSEL_WRITE_514194 eip=00423b1c ret=0000087f selected=3 new_prior=3 d526994=1
UNITSEL_406980_PRESENT_HELPER ret=00406bad src=03b00000 dst=00000000 src_ltrb=(0,0,99,370) dxy=(363,468) selected=3 prior=3 render=0051d4c0 map_surface=03ace540
UNITSEL_406980_RENDER_PRESENT ret=00406bb2 eax=00544cd8 selected=3 prior=3 render=0051d4c0 map_surface=03ace540 sz=(800,600)
UNITSEL_406980_RETURN_DUMP selected=3 prior=3 d526994=1 surface=03ace540 size=(800,600) base=03ad0030 bytes=480000
UNITSEL_POST_REDRAW_CAVE_ENTRY caller_ret=0040ae3f selected=3 prior=3 d526994=1 d5202e0=03ace540 sz=(800,600) render=0051d4c0 mouse=(448,176)
UNITSEL_406980_POST_REDRAW_ENTRY ret=0051bc00 selected=3 prior=3 d526994=1 render=0051d4c0 map_surface=03ace540 sz=(800,600)
UNITSEL_406980_POST_REDRAW_RETURN selected=3 prior=3 d526994=1 d5202e0=03ace540 sz=(800,600) render=0051d4c0 mouse=(448,176)
SURFDUMP_READY redraw_seq=900 surface=03ace540 size=(800,600) base=03ad0030 bytes=480000
SURFDUMP_HOST_READY
"""


def archived_loop_update_log_text() -> str:
    return """
SURFDUMP_LOADSAVE selected_arg=0 selected_global=0 accept=1 choice=5 gd=04220030
SURFDUMP_PLAYGAME gd=04220030 map=(100,100) scroll=(10,17) surface=03e9c880 size=(640,480)
RLOOPU_HEADER gd=04220030 player=0 scroll=(10,17) map=(100,100) selected=-1 prior=-1 shift=6 surface=03ace540 size=(800,600)
RLOOPU_INVOKE_408030_THEN_406980 screen=(448,176) raw=(0x00007000,0x00002c00) select_return=00406980 update_return=0040b0c3
RLOOPU_SELECT_TILE map=(16,19) tile=3 selected_before=-1 current=0
RLOOPU_SELECT_SUCCESS eax=1 selected_after=3
RLOOPU_406980_ENTRY ret=0040b0c3 selected=3 prior=-1 d526994=0 render=03ace540 map_surface=03ace540 sz=(800,600)
RLOOPU_40A500_ENTRY ret=0040a4f2 eax=00000010 edx=000001b3 ecx=04220030 ebp=00000000 selected=3 prior=-1 d526994=0
RLOOPU_40A500_CALL_423B00 ret=00000003 selected=3 prior=-1 d526994=0
RLOOPU_423B00_ENTRY ret=0040a5f3 eax=00000008 edx=0000087f ecx=04220030 ebp=00000000 selected=3 prior=-1 d526994=0
RLOOPU_WRITE_514194 eip=00423b1c ret=0000087f selected=3 new_prior=3 d526994=1
SURFDUMP_REDRAW seq=0 scroll=(10,17) end12=(22,26) map=(100,100) surface=03ace540 size=(800,600)
SURFDUMP_READY redraw_seq=4 surface=03ace540 size=(800,600) base=03ad0030 bytes=480000
"""


def write_based_selection_log_text() -> str:
    return good_log_text().replace(
        "UNITSEL_SELECT_SUCCESS eax=1 selected_after=3",
        "UNITSEL_WRITE_511B58 eip=00408131 ret=00544cd8 new=3 prior=-1 mouse=(448,176)",
    )


def test_good_log_summary(fixture: Path) -> None:
    log = write_log(fixture / "good.log", good_log_text())
    summary = unit_selection_action_bar_summary.parse_log(log, expected_slot=0)
    assert summary["load_slot_match"] is True, summary
    assert summary["ready"] is True, summary
    assert summary["pre_redraw_dump"] is True, summary
    assert summary["selection_success"] is True, summary
    assert summary["unit_info_route"] is True, summary
    assert summary["post_redraw_route"] is True, summary
    assert summary["present_helper"] is True, summary
    assert summary["action_update"] is True, summary
    assert summary["av_count"] == 0, summary


def test_write_to_selected_unit_counts_as_selection_success(fixture: Path) -> None:
    log = write_log(fixture / "write-selection.log", write_based_selection_log_text())
    summary = unit_selection_action_bar_summary.parse_log(log, expected_slot=0)
    assert summary["selection_success"] is True, summary


def test_archived_loop_update_is_route_proof_not_pre_redraw_visual_proof(fixture: Path) -> None:
    log = write_log(fixture / "archived.log", archived_loop_update_log_text())
    summary = unit_selection_action_bar_summary.parse_log(log, expected_slot=0)
    assert summary["selection_success"] is True, summary
    assert summary["unit_info_route"] is True, summary
    assert summary["post_redraw_route"] is False, summary
    assert summary["action_update"] is True, summary
    assert summary["pre_redraw_dump"] is False, summary


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
        "--require-load-slot",
        "--require-ready",
        "--require-pre-redraw-dump",
        "--require-selection-success",
        "--require-unit-info-route",
        "--require-post-redraw-route",
        "--require-present-helper",
        "--require-action-update",
        "--require-no-av",
    )
    assert run.returncode == 0, run.stdout + run.stderr
    written = json.loads(out_json.read_text(encoding="utf-8"))
    assert written["pre_redraw_dump"] is True, written
    assert "- Pre-redraw dump: `True`" in out_md.read_text(encoding="utf-8")


def test_cli_required_flags_fail_closed(fixture: Path) -> None:
    cases = [
        ("slot-mismatch", good_log_text().replace("selected_global=0", "selected_global=1"), "--require-load-slot"),
        ("missing-ready", good_log_text().replace("SURFDUMP_READY", "REMOVED_READY"), "--require-ready"),
        ("post-redraw-only", archived_loop_update_log_text(), "--require-pre-redraw-dump"),
        ("missing-selection", good_log_text().replace("UNITSEL_SELECT_SUCCESS", "UNITSEL_SELECT_FAIL"), "--require-selection-success"),
        ("missing-present", good_log_text().replace("UNITSEL_406980_PRESENT_HELPER", "UNITSEL_PRESENT_REMOVED"), "--require-present-helper"),
        ("missing-post-redraw", good_log_text().replace("UNITSEL_406980_POST_REDRAW_ENTRY", "UNITSEL_POST_REDRAW_REMOVED"), "--require-post-redraw-route"),
        ("missing-update", good_log_text().replace("UNITSEL_40A500_CALL_423B00", "UNITSEL_UPDATE_REMOVED"), "--require-action-update"),
        ("av", good_log_text() + "\nAV_SURFDUMP", "--require-no-av"),
    ]
    for name, text, flag in cases:
        log = write_log(fixture / f"{name}.log", text)
        run = run_script(str(log), flag)
        assert run.returncode == 2, f"{name}: {run.stdout}{run.stderr}"


def run_tests() -> None:
    fixture = ROOT / ".codex-loop" / "tmp-tests" / "unit-selection-action-bar-fixture"
    shutil.rmtree(fixture, ignore_errors=True)
    fixture.mkdir(parents=True)
    try:
        test_good_log_summary(fixture / "parse")
        test_write_to_selected_unit_counts_as_selection_success(fixture / "write-selection")
        test_archived_loop_update_is_route_proof_not_pre_redraw_visual_proof(fixture / "archived")
        test_cli_required_flags_pass_and_write_outputs(fixture / "cli-pass")
        test_cli_required_flags_fail_closed(fixture / "cli-fail")
    finally:
        shutil.rmtree(fixture, ignore_errors=True)


def main() -> int:
    run_tests()
    print("unit selection action bar summary tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
