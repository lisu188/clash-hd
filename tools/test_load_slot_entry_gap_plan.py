#!/usr/bin/env python3
"""Fixture tests for load_slot_entry_gap_plan.py."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import load_slot_entry_gap_plan as gap


DECOMP_TEXT = """
case 5:
  dword_5441E0 = -1;
  for ( k = 0; k < 10; sub_44A140(k, (DWORD)a3) )
    ;
  qmemcpy(v123, &unk_518808, 0x9Fu);
  sub_419D80(v123);
  dword_543D78 = 0;
  while ( !dword_543D78 )
  {
    if ( dword_544CFC >> byte_54512C >= 244 && dword_544CFC >> byte_54512C <= 410 )
    {
      v108 = ((dword_544D00 >> byte_54512C) - 155) / 22;
      if ( v108 <= 9 )
      {
        dword_5441E0 = ((dword_544D00 >> byte_54512C) - 155) / 22;
        if ( sub_460950((int)dword_544CD8) )
          sub_44A110(0, (DWORD)a3);
      }
    }
  }
  sub_444490(a2, (DWORD)a3, a4);
  PlayGame(v109, a2, (DWORD)a3, 1, a4);
result = sub_444750(dword_5441E0, a2);
dword_544190 = 1;
dword_543D78 = 1;
"""

CDB_TEXT = """
bp 00419B80 "__PRE_ENTRY_LOAD_COORD_ACTION__; gc"
bp 00447780 ".printf \\"SURFDUMP_SKIP_MAIN_LOAD_CALLBACK\\"; gc"
bp 00447D61 ".printf \\"SURFDUMP_MAIN_DISPATCH_POLL\\"; gc"
bp 0044895A ".printf \\"SURFDUMP_LOAD_MENU_ENTRY\\"; gc"
bp 00448A45 ".printf \\"SURFDUMP_LOAD_MENU_LOOP\\"; gc"
bp 00448A68 ".printf \\"SURFDUMP_FORCE_LOAD_SELECT\\"; gc"
bp 00448AE3 ".printf \\"SURFDUMP_FORCE_LOAD_ACCEPT\\"; gc"
bp 0044A110 ".printf \\"SURFDUMP_LOAD_ACCEPT_CALL\\"; gc"
bp 00444490 ".printf \\"SURFDUMP_LOADSAVE\\"; gc"
bp 0040B660 ".printf \\"SURFDUMP_PLAYGAME\\"; gc"
"""


def phase(slot3_entry_count: int = 0, slot2_loadsave_count: int = 1) -> dict[str, object]:
    return {
        "passed": True,
        "summary": {"current_divergence": "fixture"},
        "screenshot": "captures/fixture/surface.png",
        "phases": {
            "slot2_success": {
                "status": "load_menu_accept_success",
                "run": "slot2",
                "load_slot": 2,
                "load_coord_count": 10,
                "load_menu_entry_count": 1,
                "load_menu_loop_count": 4,
                "force_select_count": 1,
                "loadsave_count": slot2_loadsave_count,
                "playgame_count": 1,
                "last_marker": "SURFDUMP_READY",
            },
            "slot3_timeout": blocked_phase(3, entry_count=slot3_entry_count),
            "slot4_timeout": blocked_phase(4),
            "slot5_timeout": blocked_phase(5),
            "recent_slot5_timeout": blocked_phase(5),
        },
    }


def blocked_phase(slot: int, *, entry_count: int = 0) -> dict[str, object]:
    return {
        "status": gap.BLOCKED_STATUS,
        "run": f"slot{slot}",
        "load_slot": slot,
        "load_coord_count": 1,
        "load_menu_entry_count": entry_count,
        "load_menu_loop_count": 0,
        "force_select_count": 0,
        "loadsave_count": 0,
        "playgame_count": 0,
        "last_marker": "SURFDUMP_LOAD_COORD",
        "timeout_stack_category": "qpc_timing_poll_before_load_menu_loop",
    }


def write_fixture(
    root: Path,
    *,
    decomp_text: str = DECOMP_TEXT,
    cdb_text: str = CDB_TEXT,
    phase_report: dict[str, object] | None = None,
) -> dict[str, Path]:
    decomp = root / "clash95.c"
    cdb = root / "probe.cdb"
    phase_json = root / "phase.json"
    decomp.write_text(decomp_text, encoding="utf-8")
    cdb.write_text(cdb_text, encoding="utf-8")
    phase_json.write_text(json.dumps(phase_report or phase()), encoding="utf-8")
    return {"decomp": decomp, "cdb": cdb, "phase": phase_json}


def build(paths: dict[str, Path]) -> dict[str, object]:
    return gap.build_report(
        decomp_c=paths["decomp"],
        cdb_probe=paths["cdb"],
        timeout_phase_json=paths["phase"],
    )


def test_passes_current_gap_shape() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        report = build(write_fixture(Path(tmp)))
    assert report["passed"], report
    assert report["gap_classification"] == "after_main_load_callback_before_load_menu_case_entry"
    assert report["promotion_ready"] is False


def test_fails_without_static_case5_row_loop() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        report = build(write_fixture(Path(tmp), decomp_text=DECOMP_TEXT.replace("k < 10", "k < 5")))
    assert not report["passed"]
    assert any("draws_ten_rows_after_entry" in failure for failure in report["failures"])


def test_fails_without_probe_load_menu_entry_breakpoint() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        report = build(write_fixture(Path(tmp), cdb_text=CDB_TEXT.replace("bp 0044895A", "bp 0044895B")))
    assert not report["passed"]
    assert any("load_menu_entry_breakpoint" in failure for failure in report["failures"])


def test_fails_when_blocked_row_reaches_entry() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        report = build(write_fixture(Path(tmp), phase_report=phase(slot3_entry_count=1)))
    assert not report["passed"]
    assert any("slot3_timeout" in failure and "load_menu_entry_count" in failure for failure in report["failures"])


def test_fails_when_slot2_no_longer_reaches_loadsave() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        report = build(write_fixture(Path(tmp), phase_report=phase(slot2_loadsave_count=0)))
    assert not report["passed"]
    assert any("slot2" in failure and "loadsave_count" in failure for failure in report["failures"])


def test_cli_writes_outputs_and_requires_pass() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        paths = write_fixture(root)
        out_json = root / "gap.json"
        out_md = root / "gap.md"
        result = subprocess.run(
            [
                sys.executable,
                str(Path(gap.__file__)),
                "--decomp-c",
                str(paths["decomp"]),
                "--cdb-probe",
                str(paths["cdb"]),
                "--timeout-phase-json",
                str(paths["phase"]),
                "--write-json",
                str(out_json),
                "--write-markdown",
                str(out_md),
                "--require-pass",
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        assert out_json.exists()
        assert out_md.exists()


def run_tests() -> None:
    test_passes_current_gap_shape()
    test_fails_without_static_case5_row_loop()
    test_fails_without_probe_load_menu_entry_breakpoint()
    test_fails_when_blocked_row_reaches_entry()
    test_fails_when_slot2_no_longer_reaches_loadsave()
    test_cli_writes_outputs_and_requires_pass()


if __name__ == "__main__":
    run_tests()
    print("load_slot_entry_gap_plan tests passed")
