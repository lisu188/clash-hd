#!/usr/bin/env python3
"""Fixture tests for the battle UI probe parser."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "battle_ui_summary.py"
sys.path.insert(0, str(ROOT / "tools"))

import battle_ui_summary  # noqa: E402


def run_script(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def write_capture(path: Path, log_text: str, *, summary: dict | None = None) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    (path / "cdb-surface-dump.log").write_text(log_text.strip() + "\n", encoding="utf-8")
    (path / "summary.json").write_text(
        json.dumps(
            summary
            or {
                "Candidate": r"C:\ClashTests\battlecenter\clash95_hd_battle.exe",
                "CandidateSha256": "A" * 64,
                "LaunchMode": "hidden-desktop-cdb",
                "HiddenDesktop": True,
                "AllowVisibleDesktop": False,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (path / "surface.png").write_bytes(b"fixture-png")
    return path


def good_log_text() -> str:
    return """
BATTLE_READY source=HandleBattleResults eip=0042e5a0 ret=0042e600 surface=0a2fedd0 width=800 height=600 mouse=(160,120)
BATTLE_SURFACE ptr=0a2fedd0 width=800 height=600 pitch=800 base=0a5a0030 mode=centered-native offset=(80,60)
BATTLE_DRAW_ENTRY eip=00441670 name=BattleDraw ret=0042e610 target=0a2fedd0 width=800 height=600
BATTLE_DESCRIPTOR desc=0051a000 x=24 y=420 w=96 h=24 callback=0042f000 source=draw_list render=0a2fedd0 surface=0a2fedd0 width=800 height=600
BATTLE_INPUT_SCAN eip=00419dc0 list=0051a000 displayed=(160,120) native=(80,60) scale=6 render=0a2fedd0 surface=0a2fedd0 width=800 height=600
BATTLE_COMMAND_HIT desc=0051a000 displayed=(160,120) native=(80,60) callback=0042f000 result=1
BATTLE_GRID_HIT displayed=(320,240) native=(240,180) cell=(3,2) result=0
BATTLE_MODAL_CLASSIFIED status=not_open eip=00460950 displayed=(160,120) native=(80,60) scale=6
BATTLE_PRESENT_CALL eip=00460ea0 ret=0042e620 src=0a2fedd0 dst=0a2fedd0 rect=(0,0,800,600) surface=0a2fedd0 width=800 height=600
BATTLE_DONE reason=after_HandleBattleResults eip=0042e6f0 surface=0a2fedd0 width=800 height=600
SURFDUMP_READY redraw_seq=991 surface=0a2fedd0 size=(800,600) base=0a5a0030 bytes=480000 SURFDUMP_HOST_READY
"""


def test_good_capture_summary(fixture: Path) -> None:
    capture = write_capture(fixture / "good", good_log_text())
    summary = battle_ui_summary.build_summary(capture)
    assert summary["battle_reached"] is True, summary
    assert summary["battle_ready"] is True, summary
    assert summary["surface_size"] == [800, 600], summary
    assert summary["visual_mode"] == "centered-native-640x480", summary
    assert summary["centered_offset"] == [80, 60], summary
    assert summary["command_descriptor_found"] is True, summary
    assert summary["command_hit_ok"] is True, summary
    assert summary["grid_hit_ok"] is True, summary
    assert summary["modal_classified"] is True, summary
    assert summary["av_count"] == 0, summary
    assert summary["candidate"].endswith("clash95_hd_battle.exe"), summary
    assert summary["hidden_desktop"] is True, summary
    assert summary["allow_visible_desktop"] is False, summary


def test_missing_or_crashing_capture_classifies_fail_closed(fixture: Path) -> None:
    missing = battle_ui_summary.build_summary(fixture / "missing")
    assert missing["battle_reached"] is False, missing
    assert missing["surface_size"] is None, missing
    assert any("missing log" in item for item in missing["classification"]), missing

    candidate_only = write_capture(
        fixture / "candidate-only",
        "BATTLE_ROUTE_CANDIDATE name=Unit_Attack eip=0041ad20 surface=0a2fedd0 width=800 height=600",
    )
    routed = battle_ui_summary.build_summary(candidate_only)
    assert routed["battle_reached"] is False, routed
    assert routed["marker_counts"]["BATTLE_ROUTE_CANDIDATE"] == 1, routed

    crashing = write_capture(
        fixture / "crashing",
        good_log_text() + "\nAccess violation - code c0000005 first chance\n",
    )
    summary = battle_ui_summary.build_summary(crashing)
    assert summary["av_count"] == 1, summary
    assert summary["no_av"] is False, summary


def test_cli_writes_outputs(fixture: Path) -> None:
    capture = write_capture(fixture / "good", good_log_text())
    out_json = fixture / "battle-summary.json"
    out_md = fixture / "battle-summary.md"
    run = run_script(str(capture), "--write-json", str(out_json), "--write-md", str(out_md))
    assert run.returncode == 0, run.stdout + run.stderr
    written = json.loads(out_json.read_text(encoding="utf-8"))
    assert written["battle_ready"] is True, written
    assert "- Visual mode: `centered-native-640x480`" in out_md.read_text(encoding="utf-8")


def run_tests() -> None:
    fixture = ROOT / ".codex-loop" / "tmp-tests" / "battle-ui-summary-fixture"
    shutil.rmtree(fixture, ignore_errors=True)
    fixture.mkdir(parents=True)
    try:
        test_good_capture_summary(fixture / "parse")
        test_missing_or_crashing_capture_classifies_fail_closed(fixture / "fail-closed")
        test_cli_writes_outputs(fixture / "cli")
    finally:
        shutil.rmtree(fixture, ignore_errors=True)


def main() -> int:
    run_tests()
    print("battle UI summary tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
