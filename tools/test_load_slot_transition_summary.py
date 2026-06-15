#!/usr/bin/env python3
"""Fixture tests for load_slot_transition_summary.py."""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

import load_slot_transition_summary as summary


SUCCESS_LOG = """
LSTRANS_LOAD_CALLBACK_ENTRY choice_before=0 exit_before=0 target_slot=5 mouse=(300,218) lbtn=0x80
LSTRANS_AFTER_MAIN_CALLBACK desc=0x00518808 choice=5 exit=1 target_slot=5 mouse=(300,218) lbtn=0x80 flags=0x01
LSTRANS_MAIN_WAIT_GATE seq=0 choice=5 exit=1 target_slot=5 selected=-1 accept=0 mouse=(300,218) lbtn=0x80
LSTRANS_WAIT_LOOP_PUMP seq=0 choice=5 exit=1 target_slot=5 ecx_before=1 mouse=(300,218) lbtn=0x80
LSTRANS_WAIT_LOOP_COMPARE seq=1 choice=5 exit=1 target_slot=5 ecx_after=0 will_loop=0 mouse=(300,218) lbtn=0x80
LSTRANS_WAIT_LOOP_EXIT seq=2 choice=5 exit=1 target_slot=5 ecx=0 selected=-1 accept=0
LSTRANS_MAIN_SWITCH_DISPATCH seq=0 choice=5 exit=1 case_index=4 target_slot=5 selected=-1 accept=0
LSTRANS_MAIN_DISPATCH_POLL seq=0 choice=5 exit=1 aux=0 selected=-1 accept=0 target_slot=5
LSTRANS_LOAD_MENU_ENTRY choice=5 exit=0 selected=-1 accept=0 target_slot=5 mouse_before=(300,218)
LSTRANS_LATE_MOUSE_SET target_slot=5 mouse=(320,276) raw=(0x00005000,0x00004500) lbtn=0x80
LSTRANS_LOAD_SLOT_DRAW seq=0 slot=5 selected=5 accept=0 target_slot=5 mouse=(320,276) lbtn=0x80
LSTRANS_LOAD_MENU_LOOP exit=0 selected=5 accept=0 target_slot=5 mouse=(320,276) lbtn=0x80
LSTRANS_LATE_FORCE_SELECT target_slot=5 mouse=(320,276) selected=5 accept=0
LSTRANS_LATE_FORCE_ACCEPT target_slot=5 selected=5 accept=0 mouse=(320,276)
LSTRANS_LOAD_ACCEPT_CALL arg=0 selected=5 accept_before=0 target_slot=5 mouse=(320,276)
LSTRANS_LOADSAVE selected_arg=5 selected_global=5 accept=1 choice=5 gd=03fe0030 target_slot=5
LSTRANS_PLAYGAME gd=03fe0030 map=(50,50) scroll=(39,42) target_slot=5 surface=03fac880 size=(800,600)
"""

PRE_ENTRY_STALL_LOG = """
LSTRANS_LOAD_CALLBACK_ENTRY choice_before=0 exit_before=0 target_slot=5 mouse=(300,218) lbtn=0x80
LSTRANS_AFTER_MAIN_CALLBACK desc=0x00518808 choice=5 exit=1 target_slot=5 mouse=(300,218) lbtn=0x80 flags=0x01
LSTRANS_MAIN_WAIT_GATE seq=0 choice=5 exit=1 target_slot=5 selected=-1 accept=0 mouse=(300,218) lbtn=0x80
LSTRANS_WAIT_LOOP_PUMP seq=0 choice=5 exit=1 target_slot=5 ecx_before=1 mouse=(300,218) lbtn=0x80
LSTRANS_WAIT_LOOP_COMPARE seq=1 choice=5 exit=1 target_slot=5 ecx_after=1 will_loop=1 mouse=(300,218) lbtn=0x80
LSTRANS_MAIN_DISPATCH_POLL seq=0 choice=5 exit=1 aux=0 selected=-1 accept=0 target_slot=5
"""

ENTRY_NO_LOADSAVE_LOG = """
LSTRANS_LOAD_CALLBACK_ENTRY choice_before=0 exit_before=0 target_slot=5 mouse=(300,218) lbtn=0x80
LSTRANS_AFTER_MAIN_CALLBACK desc=0x00518808 choice=5 exit=1 target_slot=5 mouse=(300,218) lbtn=0x80 flags=0x01
LSTRANS_MAIN_WAIT_GATE seq=0 choice=5 exit=1 target_slot=5 selected=-1 accept=0 mouse=(300,218) lbtn=0x80
LSTRANS_WAIT_LOOP_PUMP seq=0 choice=5 exit=1 target_slot=5 ecx_before=1 mouse=(300,218) lbtn=0x80
LSTRANS_WAIT_LOOP_COMPARE seq=1 choice=5 exit=1 target_slot=5 ecx_after=0 will_loop=0 mouse=(300,218) lbtn=0x80
LSTRANS_WAIT_LOOP_EXIT seq=2 choice=5 exit=1 target_slot=5 ecx=0 selected=-1 accept=0
LSTRANS_MAIN_SWITCH_DISPATCH seq=0 choice=5 exit=1 case_index=4 target_slot=5 selected=-1 accept=0
LSTRANS_MAIN_DISPATCH_POLL seq=0 choice=5 exit=1 aux=0 selected=-1 accept=0 target_slot=5
LSTRANS_LOAD_MENU_ENTRY choice=5 exit=0 selected=-1 accept=0 target_slot=5 mouse_before=(300,218)
LSTRANS_LATE_MOUSE_SET target_slot=5 mouse=(320,276) raw=(0x00005000,0x00004500) lbtn=0x80
LSTRANS_LOAD_MENU_LOOP exit=0 selected=-1 accept=0 target_slot=5 mouse=(320,276) lbtn=0x80
"""

TARGET_SLOT_CONFLICT_LOG = SUCCESS_LOG.replace("target_slot=5", "target_slot=4", 1)

LOADSAVE_SLOT_MISMATCH_LOG = SUCCESS_LOG.replace(
    "LSTRANS_LOADSAVE selected_arg=5 selected_global=5",
    "LSTRANS_LOADSAVE selected_arg=4 selected_global=4",
)

SURFDUMP_PLAYGAME_LOG = SUCCESS_LOG.replace("LSTRANS_PLAYGAME", "SURFDUMP_PLAYGAME")

NULL_GD_PLAYGAME_LOG = SUCCESS_LOG.replace("gd=03fe0030", "gd=00000000")


def write_log(root: Path, text: str) -> Path:
    path = root / "lstrans.log"
    path.write_text(text, encoding="utf-8")
    return path


def test_success_classification() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        report = summary.parse_log(write_log(Path(tmp), SUCCESS_LOG), expected_slot=5)
    assert report["status"] == "late_entry_load_success", report
    assert report["selected_arg"] == 5
    assert report["expected_slot_match"] is True
    assert report["target_slot_expected_match"] is True
    assert report["loadsave_slot_match"] is True
    assert report["playgame_slot_match"] is True
    assert report["marker_counts"]["LSTRANS_LOAD_CALLBACK_ENTRY"] == 1
    assert report["marker_counts"]["LSTRANS_WAIT_LOOP_COMPARE"] == 1
    assert report["marker_counts"]["LSTRANS_MAIN_SWITCH_DISPATCH"] == 1
    assert report["last_wait_loop_compare"]["will_loop"] == 0
    assert report["last_switch_dispatch"]["case_index"] == 4


def test_pre_entry_stall_classification() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        report = summary.parse_log(write_log(Path(tmp), PRE_ENTRY_STALL_LOG), expected_slot=5)
    assert report["status"] == "stalled_before_load_menu_entry", report
    assert report["marker_counts"]["LSTRANS_LOAD_MENU_ENTRY"] == 0
    assert report["last_wait_loop_compare"]["will_loop"] == 1


def test_surface_dump_playgame_alias_counts_as_playgame() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        report = summary.parse_log(write_log(Path(tmp), SURFDUMP_PLAYGAME_LOG), expected_slot=5)
    assert report["status"] == "late_entry_load_success", report
    assert report["marker_counts"]["LSTRANS_PLAYGAME"] == 1
    assert report["playgame"]["gd"] == 0x03FE0030


def test_null_game_data_playgame_does_not_count_as_success() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        report = summary.parse_log(write_log(Path(tmp), NULL_GD_PLAYGAME_LOG), expected_slot=5)
    assert report["status"] != "late_entry_load_success", report


def test_entry_without_loadsave_classification() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        report = summary.parse_log(write_log(Path(tmp), ENTRY_NO_LOADSAVE_LOG), expected_slot=5)
    assert report["status"] == "entered_load_menu_without_loadsave", report
    assert report["marker_counts"]["LSTRANS_LATE_MOUSE_SET"] == 1


def test_av_fails_closed() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        report = summary.parse_log(write_log(Path(tmp), SUCCESS_LOG + "\nAV_SURFDUMP code c0000005\n"), expected_slot=5)
    assert report["status"] == "access_violation", report
    assert report["av_count"] == 1


def test_target_slot_conflict_fails_closed() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        report = summary.parse_log(write_log(Path(tmp), TARGET_SLOT_CONFLICT_LOG), expected_slot=5)
    assert report["status"] == "slot_mismatch", report
    assert report["target_slot_consistent"] is False
    assert report["expected_slot_match"] is False


def test_loadsave_slot_mismatch_fails_closed() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        report = summary.parse_log(write_log(Path(tmp), LOADSAVE_SLOT_MISMATCH_LOG), expected_slot=5)
    assert report["status"] == "slot_mismatch", report
    assert report["target_slot_expected_match"] is True
    assert report["loadsave_slot_match"] is False
    assert report["expected_slot_match"] is False


def test_cli_writes_outputs_and_requires_success() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        log = write_log(root, SUCCESS_LOG)
        out_json = root / "summary.json"
        out_md = root / "summary.md"
        result = subprocess.run(
            [
                sys.executable,
                str(Path(summary.__file__)),
                str(log),
                "--expected-slot",
                "5",
                "--write-json",
                str(out_json),
                "--write-md",
                str(out_md),
                "--require-entry",
                "--require-success",
                "--require-slot-match",
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        assert out_json.exists()
        assert out_md.exists()


def test_cli_fails_when_entry_required_but_missing() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        log = write_log(Path(tmp), PRE_ENTRY_STALL_LOG)
        result = subprocess.run(
            [
                sys.executable,
                str(Path(summary.__file__)),
                str(log),
                "--expected-slot",
                "5",
                "--require-entry",
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        assert result.returncode == 2, result.stdout + result.stderr


def test_cli_fails_when_slot_match_required_but_target_conflicts() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        log = write_log(Path(tmp), TARGET_SLOT_CONFLICT_LOG)
        result = subprocess.run(
            [
                sys.executable,
                str(Path(summary.__file__)),
                str(log),
                "--expected-slot",
                "5",
                "--require-entry",
                "--require-slot-match",
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        assert result.returncode == 2, result.stdout + result.stderr


def run_tests() -> None:
    test_success_classification()
    test_pre_entry_stall_classification()
    test_surface_dump_playgame_alias_counts_as_playgame()
    test_null_game_data_playgame_does_not_count_as_success()
    test_entry_without_loadsave_classification()
    test_av_fails_closed()
    test_target_slot_conflict_fails_closed()
    test_loadsave_slot_mismatch_fails_closed()
    test_cli_writes_outputs_and_requires_success()
    test_cli_fails_when_entry_required_but_missing()
    test_cli_fails_when_slot_match_required_but_target_conflicts()


if __name__ == "__main__":
    run_tests()
    print("load_slot_transition_summary tests passed")
