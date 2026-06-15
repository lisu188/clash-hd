#!/usr/bin/env python3
"""Fixture tests for border_tooltip_summary.py."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import border_tooltip_summary  # noqa: E402


def test_compose_markers_and_sample_rows(fixture: Path) -> None:
    fixture.mkdir(parents=True, exist_ok=True)
    log = fixture / "compose.log"
    log.write_text(
        "\n".join(
            [
                "TOOLTIP_ACTION_BOX ret=00435505 edi=00000001 d532218=00000002 d5202e0=01000000 sz=(800,600) mouse=(320,240) render=00511230",
                "APCOMP_ACTION_BOX_ENTRY map_surface=01000000 map_samples_native=(01,02,03) map_samples_lower=(04,05,06)",
                "APCOMP_COPYBACK_SAMPLES map_surface=01000000 scratch=0051d4c0 map_native=(01,02,03) scratch_native=(04) map_lower=(05,06,07)",
                "APCOMPOSE_STATUS_SHIFT_CALL src=map ltrb=(401,288,593,357) dxy=(586,528) map_surface=01000000 before=(00,00,00)",
                "APCOMPOSE_STATUS_SHIFT_DONE map_surface=01000000 after=(01,02,03)",
                "APCOMPOSE_ACTION_SHIFT_CALL src=scratch ltrb=(285,350,450,425) dxy=(285,524) map_surface=01000000 before=(00,00,00)",
                "APCOMPOSE_ACTION_SHIFT_DONE map_surface=01000000 after=(01,02,03)",
                "BORDER_TOOLTIP_PRESENT_NULLPTR ret=00418a78 call=00418a73 src=01000000 dst=00000000 ltrb=(32,193,799,591) dxy=(32,193) d5202e0=01000000 mouse=(320,166)",
                "SURFDUMP_READY redraw_seq=951 surface=01000000 size=(800,600) base=02000000 bytes=480000",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    summary = border_tooltip_summary.summarize(
        log,
        None,
        type("Args", (), {"logical_width": 800, "logical_height": 600, "threshold": 12})(),
    )
    counts = summary["marker_counts"]
    assert counts["APCOMP_ACTION_BOX_ENTRY"] == 1, summary
    assert counts["APCOMP_COPYBACK_SAMPLES"] == 1, summary
    assert counts["APCOMPOSE_STATUS_SHIFT_CALL"] == 1, summary
    assert counts["APCOMPOSE_STATUS_SHIFT_DONE"] == 1, summary
    assert counts["APCOMPOSE_ACTION_SHIFT_CALL"] == 1, summary
    assert counts["APCOMPOSE_ACTION_SHIFT_DONE"] == 1, summary
    assert counts["BORDER_TOOLTIP_PRESENT_NULLPTR"] == 1, summary
    assert summary["row_counts"]["samples"] == 6, summary
    assert summary["row_counts"]["present_null"] == 1, summary
    assert summary["null_present_by_region"]["bottom_tooltip"] == 1, summary
    assert summary["null_present_by_region"]["bottom_frame"] == 1, summary


def run_tests() -> None:
    fixture = ROOT / ".codex-loop" / "tmp-tests" / "border-tooltip-summary-fixture"
    shutil.rmtree(fixture, ignore_errors=True)
    fixture.mkdir(parents=True, exist_ok=True)
    try:
        test_compose_markers_and_sample_rows(fixture / "compose")
    finally:
        shutil.rmtree(fixture, ignore_errors=True)


def main() -> int:
    run_tests()
    print("border tooltip summary tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
