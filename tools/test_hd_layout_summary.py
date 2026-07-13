#!/usr/bin/env python3
"""Synthetic fixture tests for the hidden-CDB HD layout summary."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import hd_layout_summary as layout  # noqa: E402


PASS_LOG = """\
HDLAYOUT_TOOLTIP_INIT ret=00000000 left=240 top=586 right=553 bottom=599 surface=0a636a80 map_surface=0a30eeb0 size=(800,600)
HDLAYOUT_PANEL_SETUP ret=0040b7b3 clip_single=800 clip_list=800 e0=(608,528) e1=(672,528) e2=(736,528) e3=(608,560) e4=(672,560) e5=(736,560) render=0a30eeb0 map_surface=0a30eeb0 size=(800,600)
HDLAYOUT_PANEL_DRAW desc=00511d40 x=608 y=528 flags=0x01 draw=004191f0 hit=00409d80 render=0a30eeb0 map_surface=0a30eeb0
HDLAYOUT_PANEL_DRAW desc=00511d75 x=672 y=528 flags=0x01 draw=004191f0 hit=00409df0 render=0a30eeb0 map_surface=0a30eeb0
HDLAYOUT_PANEL_DRAW desc=00511daa x=736 y=528 flags=0x01 draw=004191f0 hit=00409f00 render=0a30eeb0 map_surface=0a30eeb0
HDLAYOUT_PANEL_DRAW desc=00511ddf x=608 y=560 flags=0x01 draw=004191f0 hit=0040a040 render=0a30eeb0 map_surface=0a30eeb0
HDLAYOUT_PANEL_DRAW desc=00511e14 x=672 y=560 flags=0x01 draw=004191f0 hit=0040a0e0 render=0a30eeb0 map_surface=0a30eeb0
HDLAYOUT_PANEL_DRAW desc=00511e49 x=736 y=560 flags=0x01 draw=004191f0 hit=0040a000 render=0a30eeb0 map_surface=0a30eeb0
HDLAYOUT_PANEL_HITSCAN list=00511d40 mouse=(320,166) e0=(608,528) e5=(736,560)
"""


def summary_for(text: str) -> dict:
    return layout.build_summary(Path("synthetic.log"), layout.parse_text(text))


def test_synthetic_pass_without_tooltip_draw() -> None:
    summary = summary_for(PASS_LOG)
    assert summary["passed"], summary
    assert summary["marker_counts"]["tooltip_draw"] == 0, summary
    assert summary["tooltip_draw_required"] is False, summary
    assert summary["checks"]["panel_draws"]["valid_descriptor_count"] == 6, summary


def test_wrong_tooltip_fails() -> None:
    summary = summary_for(PASS_LOG.replace("left=240 top=586", "left=241 top=586", 1))
    assert not summary["passed"], summary
    assert not summary["checks"]["tooltip_init_anchor"]["passed"], summary


def test_missing_panel_entry_fails() -> None:
    missing = "HDLAYOUT_PANEL_DRAW desc=00511e49 x=736 y=560"
    text = "\n".join(line for line in PASS_LOG.splitlines() if missing not in line)
    summary = summary_for(text)
    assert not summary["passed"], summary
    draw_check = summary["checks"]["panel_draws"]
    assert draw_check["valid_descriptor_count"] == 5, draw_check
    assert draw_check["missing_descriptors"] == ["0x00511e49"], draw_check


def test_wrong_clip_fails() -> None:
    summary = summary_for(PASS_LOG.replace("clip_list=800", "clip_list=799", 1))
    assert not summary["passed"], summary
    assert not summary["checks"]["panel_setup"]["passed"], summary


def test_access_violation_marker_fails() -> None:
    summary = summary_for(PASS_LOG + "AV_SURFDUMP\n")
    assert not summary["passed"], summary
    av_check = summary["checks"]["no_access_violation"]
    assert not av_check["passed"], av_check
    assert av_check["marker_count"] == 1, av_check


def test_redraw_invoke_requires_exact_clip_allow() -> None:
    invoke = (
        "HDLAYOUT_PANEL_REDRAW_INVOKE desc=00511e49 x=736 y=560 "
        "helper=00419d60 return=0040a460\n"
    )
    redraw = (
        "HDLAYOUT_PANEL_REDRAW desc=00511e49 x=736 y=560 flags=0x01 "
        "draw=004191f0 hit=0040a000 render=0a30eeb0 map_surface=0a30eeb0\n"
    )
    allowed = (
        "HDLAYOUT_PANEL_REDRAW_ALLOWED desc=00511e49 x=736 y=560 clip=800 "
        "draw=004191f0 render=0a30eeb0 map_surface=0a30eeb0\n"
    )
    summary = summary_for(PASS_LOG + invoke + allowed)
    assert summary["passed"], summary
    assert summary["redraw_clip_proved"] is True, summary
    redraw_check = summary["checks"]["panel_redraw_clip"]
    assert redraw_check["required"] is True, summary
    assert redraw_check["redraw_row_required"] is False, summary
    assert redraw_check["matching_redraw_row_count"] == 0, summary

    with_telemetry = summary_for(PASS_LOG + invoke + redraw + allowed)
    assert with_telemetry["passed"], with_telemetry
    assert with_telemetry["checks"]["panel_redraw_clip"]["matching_redraw_row_count"] == 1

    missing = summary_for(PASS_LOG + invoke)
    assert not missing["passed"], missing
    assert missing["redraw_clip_proved"] is False, missing
    assert not missing["checks"]["panel_redraw_clip"]["passed"], missing

    wrong_clip = summary_for(PASS_LOG + invoke + allowed.replace("clip=800", "clip=799"))
    assert not wrong_clip["passed"], wrong_clip
    assert wrong_clip["checks"]["panel_redraw_clip"]["matching_redraw_allowed_row_count"] == 0, wrong_clip

    malformed_invoke = summary_for(PASS_LOG + "HDLAYOUT_PANEL_REDRAW_INVOKE malformed\n" + allowed)
    assert not malformed_invoke["passed"], malformed_invoke
    redraw_check = malformed_invoke["checks"]["panel_redraw_clip"]
    assert redraw_check["required"] is True, redraw_check
    assert redraw_check["parsed_redraw_invoke_row_count"] == 0, redraw_check


def test_cli_writes_outputs_and_enforces_gate() -> None:
    with tempfile.TemporaryDirectory(prefix="hd-layout-summary-") as temp_dir:
        temp = Path(temp_dir)
        log = temp / "layout.log"
        output_json = temp / "layout.json"
        output_md = temp / "layout.md"
        log.write_text(PASS_LOG, encoding="utf-8")
        command = [
            sys.executable,
            str(ROOT / "tools" / "hd_layout_summary.py"),
            str(log),
            "--write-json",
            str(output_json),
            "--write-markdown",
            str(output_md),
            "--require-pass",
        ]
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        assert result.returncode == 0, result.stdout + result.stderr
        assert json.loads(output_json.read_text(encoding="utf-8"))["passed"] is True
        assert "Result: `PASS`" in output_md.read_text(encoding="utf-8")

        log.write_text(PASS_LOG.replace("clip_single=800", "clip_single=799", 1), encoding="utf-8")
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        assert result.returncode == 2, result.stdout + result.stderr


def run_tests() -> None:
    test_synthetic_pass_without_tooltip_draw()
    test_wrong_tooltip_fails()
    test_missing_panel_entry_fails()
    test_wrong_clip_fails()
    test_access_violation_marker_fails()
    test_redraw_invoke_requires_exact_clip_allow()
    test_cli_writes_outputs_and_enforces_gate()


def main() -> int:
    run_tests()
    print("hd layout summary tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
