#!/usr/bin/env python3
"""Fixture tests for the load-slot timeout phase classifier."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "load_slot_timeout_phase.py"
sys.path.insert(0, str(ROOT / "tools"))

import load_slot_timeout_phase as phase  # noqa: E402


SUCCESS_LOG = """\
SURFDUMP_LOAD_COORD seq=0 choice=5 entry=0x000efa5d ex=232 ey=228 mouse=(320,210) selected=0 accept=0
SURFDUMP_LOAD_MENU_ENTRY choice=5 exit=1 selected=0 accept=0 mouse=(320,210)
SURFDUMP_LOAD_MENU_LOOP seq=0 exit=0 selected=-1 accept=0 mouse=(320,210) lbtn=0x80
SURFDUMP_FORCE_LOAD_SELECT seq=0 mouse=(320,210) selected=-1 accept=0
SURFDUMP_FORCE_LOAD_ACCEPT seq=0 selected=2 accept=0 mouse=(320,210)
SURFDUMP_LOAD_ACCEPT_CALL arg=0 selected=2 accept_before=0 mouse=(320,210)
SURFDUMP_LOADSAVE selected_arg=2 selected_global=2 accept=1 choice=5 gd=03fe0030
SURFDUMP_PLAYGAME gd=03fe0030 map=(50,50) scroll=(39,42) surface=03fac880 size=(640,480)
SURFDUMP_READY redraw_seq=1 surface=0a07ed50 size=(800,600) base=0a360030 bytes=480000
"""


def blocked_log(slot: int, *, entry: str = "0x000efa5d", load_menu_entry: bool = False) -> str:
    y = 166 + 22 * slot
    text = (
        f"SURFDUMP_LOAD_COORD seq=0 choice=5 entry={entry} ex=232 ey=228 "
        f"mouse=(320,{y}) selected=0 accept=0\n"
    )
    if load_menu_entry:
        text += f"SURFDUMP_LOAD_MENU_ENTRY choice=5 exit=1 selected=0 accept=0 mouse=(320,{y})\n"
    return text


def write_run(root: Path, name: str, *, slot: int, log_text: str, passed: bool, timed_out: bool) -> Path:
    run = root / name
    run.mkdir(parents=True)
    stack = run / "timeout-stack.log"
    summary = {
        "Passed": passed,
        "TimedOut": timed_out,
        "HiddenDesktop": True,
        "AllowVisibleDesktop": False,
        "LoadSlot": slot,
        "Av": False,
        "TimeoutStackLog": str(stack),
        "PngPath": str(run / "surface.png") if passed else None,
    }
    (run / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
    (run / "cdb-surface-dump.log").write_text(log_text, encoding="utf-8")
    stack.write_text(
        "0:000> ~* kb\n"
        "000edc64 004605e4 0000004c 0051d4c0 00000001 clash95+0x207cd\n",
        encoding="utf-8",
    )
    if passed:
        (run / "surface.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    return run


def write_fixture(root: Path, *, slot2_log: str = SUCCESS_LOG, slot3_log: str | None = None) -> dict[str, Path]:
    return {
        "slot2": write_run(root, "slot2", slot=2, log_text=slot2_log, passed=True, timed_out=False),
        "slot3": write_run(root, "slot3", slot=3, log_text=slot3_log or blocked_log(3), passed=False, timed_out=True),
        "slot4": write_run(root, "slot4", slot=4, log_text=blocked_log(4), passed=False, timed_out=True),
        "slot5": write_run(root, "slot5", slot=5, log_text=blocked_log(5, entry="0x000efa92"), passed=False, timed_out=True),
        "recent_slot5": write_run(
            root,
            "recent_slot5",
            slot=5,
            log_text=blocked_log(5, entry="0x000efa92"),
            passed=False,
            timed_out=True,
        ),
    }


def build(paths: dict[str, Path]) -> dict:
    return phase.build_report(
        slot2_run=paths["slot2"],
        slot3_run=paths["slot3"],
        slot4_run=paths["slot4"],
        slot5_run=paths["slot5"],
        recent_slot5_run=paths["recent_slot5"],
    )


def test_guard_passes_current_shape() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        report = build(write_fixture(Path(tmp)))
    assert report["passed"] is True, report
    assert report["summary"]["slot2_phase"] == "load_menu_accept_success"
    assert report["summary"]["blocked_slots"] == [3, 4, 5]


def test_guard_fails_when_slot2_no_longer_reaches_loadsave() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        report = build(write_fixture(Path(tmp), slot2_log=SUCCESS_LOG.replace("SURFDUMP_LOADSAVE", "NOPE")))
    assert report["passed"] is False, report
    assert any("slot2_success" in failure and "SURFDUMP_LOADSAVE" in failure for failure in report["failures"])


def test_guard_fails_when_blocked_slot_reaches_load_menu_entry() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        report = build(write_fixture(Path(tmp), slot3_log=blocked_log(3, load_menu_entry=True)))
    assert report["passed"] is False, report
    assert any("slot3_timeout" in failure and "LOAD_MENU_ENTRY" in failure for failure in report["failures"])


def test_cli_writes_outputs_and_honors_require_pass() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        paths = write_fixture(root)
        out_json = root / "phase.json"
        out_md = root / "phase.md"
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
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
                str(out_json),
                "--write-markdown",
                str(out_md),
                "--require-pass",
            ],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        assert out_json.exists()
        assert out_md.exists()


def run_tests() -> None:
    fixture = ROOT / ".codex-loop" / "tmp-tests" / "load-slot-timeout-phase-fixture"
    shutil.rmtree(fixture, ignore_errors=True)
    fixture.mkdir(parents=True)
    try:
        test_guard_passes_current_shape()
        test_guard_fails_when_slot2_no_longer_reaches_loadsave()
        test_guard_fails_when_blocked_slot_reaches_load_menu_entry()
        test_cli_writes_outputs_and_honors_require_pass()
    finally:
        shutil.rmtree(fixture, ignore_errors=True)


def main() -> int:
    run_tests()
    print("load slot timeout phase tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
