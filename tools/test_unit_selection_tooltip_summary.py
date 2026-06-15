#!/usr/bin/env python3
"""Fixture tests for unit_selection_tooltip_summary.py."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import unit_selection_tooltip_summary  # noqa: E402


def base_log_text(*, include_owner: bool = False) -> str:
    lines = [
        "SURFDUMP_LOADSAVE selected_arg=0 selected_global=0 accept=1 choice=5 gd=04340030",
        "UNITSEL_ROUTE_START gd=04340030 player=0 scroll=(10,17) map=(100,100) selected=-1 prior=-1 shift=6 surface=0491fbd8 size=(800,600)",
        "UNITSEL_INVOKE_408030_THEN_406980 screen=(448,176) raw=(0x00007000,0x00002c00) select_return=00406980 update_return=0040b0c3",
        "UNITSEL_SELECT_TILE map=(16,19) tile=3 selected_before=-1 current=0",
        "UNITSEL_WRITE_511B58 eip=00408131 ret=00544cd8 new=3 prior=-1 mouse=(448,176)",
        "UNITSEL_406980_ENTRY ret=0040b0c3 selected=3 prior=-1 d526994=0 render=0491fbd8 map_surface=0491fbd8 sz=(800,600)",
        "UNITSEL_40A500_ENTRY ret=0040a4f2 eax=00000010 edx=000001b3 ecx=04340030 ebp=00000000 selected=3 prior=-1 d526994=0",
        "UNITSEL_40A500_CALL_423B00 ret=00000003 selected=3 prior=-1 d526994=0",
        "UNITSEL_423B00_ENTRY ret=0040a5f3 eax=00000008 edx=0000087f ecx=04340030 ebp=00000000 selected=3 prior=-1 d526994=0",
        "UNITSEL_WRITE_514194 eip=00423b1c ret=0000087f selected=3 new_prior=3 d526994=1",
        "UNITSEL_406980_PRESENT_HELPER ret=00000063 src=04c4c208 dst=00000000 src_ltrb=(0,0,8,363) dxy=(468,1) selected=3 prior=3 render=04c4c208 map_surface=0491fbd8",
        "UNITSEL_406980_RENDER_PRESENT ret=00000001 eax=006cfe00 selected=3 prior=3 render=04c4c208 map_surface=0491fbd8 sz=(800,600)",
        "UNITSEL_406980_RETURN_DUMP selected=3 prior=3 d526994=1 surface=0491fbd8 size=(800,600) base=04bc0030 bytes=480000",
        "UNITSEL_POST_REDRAW_CAVE_ENTRY caller_ret=0040ae3f selected=3 prior=3 d526994=1 d5202e0=0491fbd8 sz=(800,600) render=0051d4c0 mouse=(448,176)",
        "UNITSEL_406980_POST_REDRAW_ENTRY ret=0051bc00 selected=3 prior=3 d526994=1 render=0051d4c0 map_surface=0491fbd8 sz=(800,600)",
        "UNITSEL_406980_POST_REDRAW_RETURN selected=3 prior=3 d526994=1 d5202e0=0491fbd8 sz=(800,600) render=0051d4c0 mouse=(448,176)",
        "HOVSEL_FORCE_STATE seq=0 mode=selected_unit_hover mouse=(448,176) raw=(0x00007000,0x00002c00) selected=3 action=0 d532218=00000000 d532220=0",
        "HOVSEL_FORCE_STATE seq=1 mode=bottom_tooltip_hover mouse=(400,560) raw=(0x00006400,0x00008c00) selected=3 action=0 d532218=00000000 d532220=0",
        "HOVSEL_FORCE_STATE seq=2 mode=action_grid_hover mouse=(474,114) raw=(0x00007680,0x00001c80) selected=3 action=0 d532218=00000000 d532220=0",
        "HOVSEL_FORCE_STATE seq=3 mode=action_box_hover mouse=(320,388) raw=(0x00005000,0x00006100) selected=3 action=0 d532218=00000000 d532220=0",
        "HOVSEL_FORCE_STATE seq=4 mode=safe_center_hold mouse=(320,300) raw=(0x00005000,0x00004b00) selected=3 action=0 d532218=00000000 d532220=0",
    ]
    if include_owner:
        lines.extend(
            [
                "HOVSEL_UNITINFO_ENTRY ret=0041a7b7 args=(00000020,00000210,00000249,00000000) render=0051d4c0 map_surface=0491fbd8 sz=(800,600) mouse=(400,560) selected=3 action=0",
                "TOOLTIP_TEXTFMT ret=0041a158 x=32 y=536 right=585 style=0 fmt=00520520 d5202e0=0491fbd8 sz=(800,600) mouse=(400,560)",
                "BORDER_TOOLTIP_PRESENT ret=0041a112 call=0041a10d src=0051d4c0 srcsz=(800,600) dst=0491fbd8 dstsz=(800,600) ltrb=(0,0,553,71) dxy=(32,528) d5202e0=0491fbd8 mouse=(400,560)",
            ]
        )
    lines.append("SURFDUMP_READY redraw_seq=4 surface=0491fbd8 size=(800,600) base=04bc0030 bytes=480000")
    return "\n".join(lines) + "\n"


def args() -> argparse.Namespace:
    return argparse.Namespace(
        expected_slot=0,
        logical_width=800,
        logical_height=600,
        threshold=12,
        action_bar_min_nonblack=40.0,
        tooltip_min_nonblack=1.0,
    )


def write_log(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_no_owner_stops_before_patch(fixture: Path) -> None:
    log = write_log(fixture / "no-owner.log", base_log_text())
    summary = unit_selection_tooltip_summary.summarize(log, None, args())
    assert summary["evidence_pass"], summary
    assert not summary["tooltip_owner_evidence"], summary
    assert summary["decision"] == "NO_PATCH_OWNER_NOT_REACHED", summary


def test_owner_rows_allow_patch_candidate(fixture: Path) -> None:
    log = write_log(fixture / "owner.log", base_log_text(include_owner=True))
    summary = unit_selection_tooltip_summary.summarize(log, None, args())
    assert summary["evidence_pass"], summary
    assert summary["tooltip_owner_evidence"], summary
    assert summary["tooltip_present_by_region"]["bottom_tooltip"] == 1, summary
    assert summary["decision"] == "OWNER_REACHED_PATCH_ALLOWED", summary


def test_missing_post_redraw_action_bar_fails_evidence(fixture: Path) -> None:
    text = base_log_text().replace("UNITSEL_406980_POST_REDRAW_ENTRY", "UNITSEL_POST_REDRAW_REMOVED")
    log = write_log(fixture / "missing-post-redraw.log", text)
    summary = unit_selection_tooltip_summary.summarize(log, None, args())
    assert not summary["evidence_pass"], summary
    assert not summary["unit"]["post_redraw_route"], summary
    assert summary["decision"] == "BASIC_EVIDENCE_FAILED", summary


def run_tests() -> None:
    fixture = ROOT / ".codex-loop" / "tmp-tests" / "unit-selection-tooltip-summary-fixture"
    shutil.rmtree(fixture, ignore_errors=True)
    fixture.mkdir(parents=True, exist_ok=True)
    try:
        test_no_owner_stops_before_patch(fixture / "no-owner")
        test_owner_rows_allow_patch_candidate(fixture / "owner")
        test_missing_post_redraw_action_bar_fails_evidence(fixture / "missing-post-redraw")
    finally:
        shutil.rmtree(fixture, ignore_errors=True)


def main() -> int:
    run_tests()
    print("unit selection tooltip summary tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
