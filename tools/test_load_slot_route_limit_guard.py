#!/usr/bin/env python3
"""Tests for load_slot_route_limit_guard.py."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import load_slot_route_limit_guard as guard


DECOMP_TEXT = """
int __usercall sub_4443C0@<eax>(int a1@<eax>, int a2@<edx>)
{
  return sprintf_(a2, "save\\\\%d.dat", a1);
}
int __usercall sub_44A110@<eax>(int a1@<eax>, DWORD a2@<ebp>)
{
  result = sub_444750(dword_5441E0, a2);
  if ( result )
  {
    dword_544190 = 1;
    dword_543D78 = 1;
  }
  return result;
}
case 5:
  for ( k = 0; k < 10; sub_44A140(k, (DWORD)a3) )
    ;
  if ( v108 <= 9 )
  {
    dword_5441E0 = ((dword_544D00 >> byte_54512C) - 155) / 22;
    sub_44A110(0, (DWORD)a3);
  }
  sub_444490(a2, (DWORD)a3, a4);
void *__usercall sub_44A140@<eax>(int a1@<eax>, DWORD a2@<ebp>)
{
  v4 = (unsigned __int16)(22 * a1 + 155);
  UI_DrawTextFmt(v4, 244, 410, 22 * a1 + 155, 3, (int)v7);
}
"""
HARNESS_TEXT = """
[ValidateRange(0,9)]
[int]$LoadSlot = 0
$loadMouseX = 320
$loadMouseY = 166 + (22 * $LoadSlot)
$loadMouseRawX = $loadMouseX -shl 6
$loadMouseRawY = $loadMouseY -shl 6
$probeText = $probeText.Replace('__LOAD_SLOT__', [string]$LoadSlot)
"""
STAGE = "gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch"


def success_log(slot: int) -> str:
    y = 166 + (22 * slot)
    return (
        f"route-injects load slot {slot}, waits for gameplay redraw, then dumps dword_5202E0\n"
        f"SURFDUMP_LOAD_COORD seq=0 choice=5 entry=0x000efa5d ex=232 ey=228 mouse=(320,{y}) selected=0 accept=0\n"
        f"SURFDUMP_FORCE_LOAD_SELECT seq=0 mouse=(320,{y}) selected=-1 accept=0\n"
        f"SURFDUMP_FORCE_LOAD_ACCEPT seq=0 selected={slot} accept=0 mouse=(320,{y})\n"
        f"SURFDUMP_LOAD_ACCEPT_CALL arg=0 selected={slot} accept_before=0 mouse=(320,{y})\n"
        f"SURFDUMP_LOADSAVE selected_arg={slot} selected_global={slot} accept=1 choice=5 gd=03fe0030\n"
        "SURFDUMP_PLAYGAME gd=03fe0030 map=(50,50) scroll=(39,42) surface=03fac880 size=(640,480)\n"
    )


def blocked_log(slot: int, *, force: bool = False, loadsave: bool = False) -> str:
    y = 166 + (22 * slot)
    text = (
        f"route-injects load slot {slot}, waits for gameplay redraw, then dumps dword_5202E0\n"
        f"SURFDUMP_LOAD_COORD seq=0 choice=5 entry=0x000efa5d ex=232 ey=228 mouse=(320,{y}) selected=0 accept=0\n"
    )
    if force:
        text += f"SURFDUMP_FORCE_LOAD_SELECT seq=0 mouse=(320,{y}) selected=-1 accept=0\n"
    if loadsave:
        text += (
            f"SURFDUMP_LOADSAVE selected_arg={slot} selected_global={slot} accept=1 choice=5 gd=03fe0030\n"
            "SURFDUMP_PLAYGAME gd=03fe0030 map=(50,50) scroll=(39,42) surface=03fac880 size=(640,480)\n"
        )
    return text


def write_run(
    root: Path,
    name: str,
    *,
    slot: int,
    log_text: str,
    passed: bool,
    timed_out: bool,
) -> Path:
    run = root / name
    run.mkdir()
    (run / "summary.json").write_text(
        json.dumps(
            {
                "Passed": passed,
                "TimedOut": timed_out,
                "HiddenDesktop": True,
                "AllowVisibleDesktop": False,
                "UseDdrawProxy": True,
                "SkipMapValidation": True,
                "FastForwardStartAnims": True,
                "Stage": STAGE,
                "CandidateSha256": "F3BC",
                "LoadSlot": slot,
                "Av": False,
                "PngPath": str(run / "surface.png"),
                "TimeoutStackLog": str(run / "timeout-stack.log") if timed_out else None,
            }
        ),
        encoding="utf-8",
    )
    (run / "cdb-surface-dump.log").write_text(log_text, encoding="utf-8")
    return run


def write_fixture(
    root: Path,
    *,
    decomp_text: str = DECOMP_TEXT,
    slot2_log: str | None = None,
    slot3_log: str | None = None,
    recent_slot5_log: str | None = None,
) -> dict[str, Path]:
    decomp = root / "clash95.c"
    harness = root / "scripts/cdb/run_cdb_surface_dump.ps1"
    decomp.write_text(decomp_text, encoding="utf-8")
    harness.parent.mkdir(parents=True, exist_ok=True)
    harness.write_text(HARNESS_TEXT, encoding="utf-8")
    return {
        "decomp": decomp,
        "harness": harness,
        "slot2": write_run(root, "slot2", slot=2, log_text=slot2_log or success_log(2), passed=True, timed_out=False),
        "slot3": write_run(root, "slot3", slot=3, log_text=slot3_log or blocked_log(3), passed=False, timed_out=True),
        "slot4": write_run(root, "slot4", slot=4, log_text=blocked_log(4), passed=False, timed_out=True),
        "slot5": write_run(root, "slot5", slot=5, log_text=blocked_log(5), passed=False, timed_out=True),
        "recent_slot5": write_run(
            root,
            "recent_slot5",
            slot=5,
            log_text=recent_slot5_log or blocked_log(5),
            passed=False,
            timed_out=True,
        ),
    }


def build(paths: dict[str, Path]) -> dict[str, object]:
    return guard.build_report(
        decomp_c=paths["decomp"],
        surface_probe_script=paths["harness"],
        slot2_run=paths["slot2"],
        slot3_run=paths["slot3"],
        slot4_run=paths["slot4"],
        slot5_run=paths["slot5"],
        recent_slot5_run=paths["recent_slot5"],
    )


def test_passes_current_route_limit_shape() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        report = build(write_fixture(Path(tmp)))
    assert report["passed"], report
    assert report["summary"]["static_load_rows"] == "0..9"
    assert report["summary"]["archived_success_slots"] == [2]
    assert report["summary"]["archived_blocked_slots"] == [3, 4, 5]
    assert report["promotion_ready"] is False


def test_fails_without_static_ten_row_evidence() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        report = build(write_fixture(Path(tmp), decomp_text=DECOMP_TEXT.replace("k < 10", "k < 5")))
    assert not report["passed"]
    assert any("draws_ten_rows" in failure for failure in report["failures"])


def test_fails_when_slot2_no_longer_loads() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        report = build(write_fixture(Path(tmp), slot2_log=blocked_log(2)))
    assert not report["passed"]
    assert any("slot2_success" in failure and "LOADSAVE" in failure for failure in report["failures"])


def test_fails_when_blocked_slot_loads() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        report = build(write_fixture(Path(tmp), slot3_log=blocked_log(3, loadsave=True)))
    assert not report["passed"]
    assert any("slot3_blocked" in failure and "LOADSAVE" in failure for failure in report["failures"])


def test_fails_when_blocked_slot_reaches_force_select() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        report = build(write_fixture(Path(tmp), recent_slot5_log=blocked_log(5, force=True)))
    assert not report["passed"]
    assert any("recent_slot5_blocked" in failure and "forced load-select" in failure for failure in report["failures"])


def test_cli_writes_outputs_and_requires_pass() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        paths = write_fixture(root)
        output_json = root / "out.json"
        output_md = root / "out.md"
        result = subprocess.run(
            [
                sys.executable,
                str(Path(guard.__file__)),
                "--decomp-c",
                str(paths["decomp"]),
                "--surface-probe-script",
                str(paths["harness"]),
                "--slot2-run",
                str(paths["slot2"]),
                "--slot3-run",
                str(paths["slot3"]),
                "--slot4-run",
                str(paths["slot4"]),
                "--slot5-run",
                str(paths["slot5"]),
                "--recent-slot5-run",
                str(paths["recent_slot5"]),
                "--write-json",
                str(output_json),
                "--write-markdown",
                str(output_md),
                "--require-pass",
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        assert output_json.exists()
        assert output_md.exists()


def run_tests() -> None:
    test_passes_current_route_limit_shape()
    test_fails_without_static_ten_row_evidence()
    test_fails_when_slot2_no_longer_loads()
    test_fails_when_blocked_slot_loads()
    test_fails_when_blocked_slot_reaches_force_select()
    test_cli_writes_outputs_and_requires_pass()


if __name__ == "__main__":
    run_tests()
    print("load_slot_route_limit_guard tests passed")
