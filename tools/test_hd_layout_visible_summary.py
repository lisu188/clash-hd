#!/usr/bin/env python3
"""Focused tests for the approved visible HD-layout evidence summary."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import hd_layout_visible_summary as visible  # noqa: E402
from capture_geometry import Image  # noqa: E402


def fixture_images() -> tuple[Image, Image]:
    width, height = visible.EXPECTED_CAPTURE_SIZE
    background = (40, 80, 120)
    before_pixels = [background] * (width * height)

    # A sparse 128x16 neutral-bright string-shaped footprint at the expected
    # bottom-centred location.  There is no neutral-bright content in the
    # legacy middle-lower strip.
    for y in range(880, 896):
        for x in range(529, 657):
            if (x + y) % 4 == 0:
                before_pixels[y * width + x] = (220, 215, 210)
    before_pixels[880 * width + 529] = (220, 215, 210)
    before_pixels[895 * width + 656] = (220, 215, 210)

    after_pixels = list(before_pixels)
    left, top, right, bottom = visible.PANEL_ACTIVE_RECT
    for y in range(top, bottom + 1):
        for x in range(left, right + 1):
            after_pixels[y * width + x] = (180, 115, 35) if (x + y) % 2 else (95, 55, 20)
    return (
        Image(width=width, height=height, pixels=before_pixels),
        Image(width=width, height=height, pixels=after_pixels),
    )


def candidate_payload() -> dict:
    return {
        "Exe": r"C:\ClashTests\right-bottom-slot5-as-slot0-fixture\clash95_hd_hdlayout_visible_20260713.exe",
        "ExeSha256": visible.EXPECTED_CANDIDATE_SHA256,
    }


def hover_payload() -> dict:
    return {
        "client_size": [800, 600],
        "points": [
            {
                "client": [640, 544],
                "actual_client": [640, 544],
                "client_error": [0, 0],
                "move_mode": "auto",
                "move_method": "setcursor",
                "samples": [
                    {
                        "requested_client": [640, 544],
                        "actual_client": [640, 544],
                        "client_error": [0, 0],
                    }
                ],
                "clicks": [],
            }
        ],
        "max_abs_error": 0,
        "max_sample_abs_error": 0,
        "click_event_count": 0,
        "path_verified": True,
        "click_path_verified": True,
    }


def failed_click_payload() -> dict:
    return {
        "points": [
            {
                "client": [760, 560],
                "actual_client": [716, 493],
                "client_error": [-44, -67],
            }
        ],
        "max_abs_error": 67,
        "max_sample_abs_error": 67,
        "click_event_count": 2,
        "path_verified": False,
        "click_path_verified": False,
    }


def test_candidate_identity_is_exact_and_isolated() -> None:
    check = visible._candidate_check(candidate_payload())
    assert check["passed"], check

    wrong = candidate_payload()
    wrong["ExeSha256"] = "00" * 32
    assert not visible._candidate_check(wrong)["passed"]

    original = candidate_payload()
    original["Exe"] = r"C:\Clash\clash95.exe"
    assert not visible._candidate_check(original)["passed"]


def test_tooltip_and_panel_geometry_detectors() -> None:
    before, after = fixture_images()
    tooltip, legacy_tooltip = visible._tooltip_check(before)
    assert tooltip["passed"], tooltip
    assert tooltip["neutral_bright_pixels"] >= 500, tooltip
    assert legacy_tooltip["passed"], legacy_tooltip
    assert legacy_tooltip["neutral_bright_pixels"] == 0, legacy_tooltip

    panel, legacy_panel = visible._panel_check(before, after)
    assert panel["passed"], panel
    assert panel["active_region"]["changed_percent"] == 100.0, panel
    assert panel["active_region"]["changed_bounds"] == {
        "x": 912,
        "y": 792,
        "right": 1008,
        "bottom": 888,
        "width": 97,
        "height": 97,
    }
    assert legacy_panel["passed"], legacy_panel
    assert legacy_panel["changed_percent"] == 0.0, legacy_panel


def test_hover_is_automated_alignment_only() -> None:
    check = visible._hover_alignment_check(hover_payload())
    assert check["passed"], check
    assert check["proof_class"] == "automated_win32_setcursor_alignment", check
    assert check["manual_directinput_proof"] is False, check
    assert check["command_click_alignment"] is False, check

    bad = hover_payload()
    bad["points"][0]["actual_client"] = [639, 544]
    bad["points"][0]["client_error"] = [-1, 0]
    bad["max_abs_error"] = 1
    assert not visible._hover_alignment_check(bad)["passed"]


def test_failed_descriptor5_click_is_never_hidden() -> None:
    attempt = visible._failed_click_attempt(failed_click_payload())
    assert attempt["attempt_observed"] is True, attempt
    assert attempt["classified_failed_attempt"] is True, attempt
    assert attempt["alignment_passed"] is False, attempt
    assert attempt["client_error"] == [-44, -67], attempt
    assert attempt["excluded_from_pass_gate"] is True, attempt


def test_real_archive_and_claim_boundaries() -> None:
    summary = visible.summarize(
        ROOT / visible.DEFAULT_RUN_DIR,
        ROOT / visible.DEFAULT_BASELINE_FRAME,
    )
    assert summary["passed"], summary
    assert summary["candidate_sha256"] == visible.EXPECTED_CANDIDATE_SHA256, summary
    assert summary["failed_panel_click_attempt"]["classified_failed_attempt"] is True, summary
    assert summary["command_click_alignment"] is False, summary
    assert summary["panel_click_callback_proof"] is False, summary
    assert summary["manual_directinput_proof"] is False, summary
    assert summary["stable_stage_promotion_ready"] is False, summary
    assert summary["promotion_ready"] is False, summary


def test_cli_writes_strict_outputs() -> None:
    with tempfile.TemporaryDirectory(prefix="hd-layout-visible-") as temp_dir:
        output_json = Path(temp_dir) / "summary.json"
        output_md = Path(temp_dir) / "summary.md"
        command = [
            sys.executable,
            str(ROOT / "tools" / "hd_layout_visible_summary.py"),
            str(ROOT / visible.DEFAULT_RUN_DIR),
            "--baseline-frame",
            str(ROOT / visible.DEFAULT_BASELINE_FRAME),
            "--write-json",
            str(output_json),
            "--write-markdown",
            str(output_md),
            "--require-pass",
        ]
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        assert result.returncode == 0, result.stdout + result.stderr
        payload = json.loads(output_json.read_text(encoding="utf-8"))
        assert payload["passed"] is True, payload
        assert payload["command_click_alignment"] is False, payload
        assert payload["failed_panel_click_attempt"]["alignment_passed"] is False, payload
        markdown = output_md.read_text(encoding="utf-8")
        assert "Result: `PASS`" in markdown, markdown
        assert "Command-click alignment: `false`" in markdown, markdown
        assert "Client error: `[-44, -67]`" in markdown, markdown


def run_tests() -> None:
    test_candidate_identity_is_exact_and_isolated()
    test_tooltip_and_panel_geometry_detectors()
    test_hover_is_automated_alignment_only()
    test_failed_descriptor5_click_is_never_hidden()
    test_real_archive_and_claim_boundaries()
    test_cli_writes_strict_outputs()


def main() -> int:
    run_tests()
    print("HD layout visible summary tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
