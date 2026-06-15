#!/usr/bin/env python3
"""Fixture tests for the castle overview focused hitbox summary parser."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "castle_overview_hitbox_summary.py"
sys.path.insert(0, str(ROOT / "tools"))

import castle_overview_hitbox_summary  # noqa: E402


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
CASTLEOV_HITBOX_DISPLAYED_SET x=371 y=107
CASTLEOV_HITBOX_DISPLAYED_RESULT x=371 y=107 raw_hit=0xf8
CASTLEOV_HITBOX_NATIVE_TRANSFORM_SET displayed=(371,107) native=(291,47)
CASTLEOV_HITBOX_NATIVE_RESULT x=291 y=47 raw_hit=0xf8
CASTLEOV_HITBOX_DESCRIPTOR_INSTALL command=0x86 callback=0x0044fe70
CASTLEOV_HITBOX_CLICK_GATE command=0x86 callback=0x0044fe70 gate=1
CASTLEOV_HITBOX_CALLBACK_SUPPRESSED
CASTLEOV_HITBOX_SURFDUMP_READY size=(800,600)
"""


def test_good_log_summary(fixture: Path) -> None:
    log = write_log(fixture / "good.log", good_log_text())
    summary = castle_overview_hitbox_summary.parse_log(log)
    assert summary["displayed_hit_ok"] is True, summary
    assert summary["native_hit_ok"] is True, summary
    assert summary["descriptor_ok"] is True, summary
    assert summary["click_gate_ok"] is True, summary
    assert summary["callback_suppressed"] is True, summary
    assert summary["callback_called"] is False, summary
    assert summary["av_count"] == 0, summary
    assert summary["last_ready"]["size"] == [800, 600], summary


def test_cli_required_flags_pass_and_write_outputs(fixture: Path) -> None:
    log = write_log(fixture / "good.log", good_log_text())
    out_json = fixture / "summary.json"
    out_md = fixture / "summary.md"
    run = run_script(
        str(log),
        "--require-ready",
        "--require-800x600",
        "--require-displayed-hit",
        "--require-native-hit",
        "--require-descriptor",
        "--require-click-gate",
        "--require-callback-suppressed",
        "--forbid-callback",
        "--write-json",
        str(out_json),
        "--write-md",
        str(out_md),
    )
    assert run.returncode == 0, run.stdout + run.stderr
    written = json.loads(out_json.read_text(encoding="utf-8"))
    assert written["displayed_hit_ok"] is True, written
    assert "Displayed hit ok: True" in out_md.read_text(encoding="utf-8")


def test_cli_required_flags_fail_closed(fixture: Path) -> None:
    cases = [
        ("missing-ready", "CASTLEOV_HITBOX_DISPLAYED_RESULT raw_hit=0xf8", "--require-ready"),
        ("wrong-size", good_log_text().replace("size=(800,600)", "size=(640,480)"), "--require-800x600"),
        ("missing-displayed", good_log_text().replace("raw_hit=0xf8", "raw_hit=0xfa", 1), "--require-displayed-hit"),
        ("missing-native", good_log_text().replace("CASTLEOV_HITBOX_NATIVE_RESULT x=291 y=47 raw_hit=0xf8", ""), "--require-native-hit"),
        ("missing-descriptor", good_log_text().replace("callback=0x0044fe70", "callback=0x00420000", 1), "--require-descriptor"),
        ("missing-gate", good_log_text().replace("gate=1", "gate=0"), "--require-click-gate"),
        ("missing-suppressed", good_log_text().replace("CASTLEOV_HITBOX_CALLBACK_SUPPRESSED", ""), "--require-callback-suppressed"),
        ("callback-called", good_log_text() + "\nCASTLEOV_HITBOX_CALLBACK_CALL command=0x86", "--forbid-callback"),
    ]
    for name, text, flag in cases:
        log = write_log(fixture / f"{name}.log", text)
        run = run_script(str(log), flag)
        assert run.returncode == 2, f"{name}: {run.stdout}{run.stderr}"

    av_log = write_log(fixture / "av.log", good_log_text() + "\nAccess violation - code c0000005")
    av_run = run_script(str(av_log))
    assert av_run.returncode == 2, av_run.stdout + av_run.stderr


def run_tests() -> None:
    fixture = ROOT / ".codex-loop" / "tmp-tests" / "castle-overview-hitbox-summary-fixture"
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
    print("castle overview hitbox summary tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
