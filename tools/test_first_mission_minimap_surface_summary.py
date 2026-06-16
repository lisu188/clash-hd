#!/usr/bin/env python3
"""Fixture tests for first_mission_minimap_surface_summary.py."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "first_mission_minimap_surface_summary.py"
sys.path.insert(0, str(ROOT / "tools"))

import first_mission_minimap_surface_summary as summary_tool  # noqa: E402


SAMPLE_LOG = """\
FMMS_MINIMAP_INIT left=586 top=16 width=214 height=214 right=799 bottom=229 backing=00000000 backing_sz=(0,0) backing_base=00000000 scale=2
FMMS_UNITSEL_SELECT_SUCCESS eax=1 selected_after=3
FMMS_MINIMAP_DIRTY_ENTRY seq=0 ret=004169a1 bounds=(586,16,799,229) backing=07ecd268 backing_sz=(214,214) backing_base=086b0030 map_surface=09fe5ab8 map_sz=(800,600) regs=(20,5f,4f,10) backing_samples=(01,01,01,01,01,21) map_samples=(00,00,00,00,00,00)
FMMS_MINIMAP_DIRTY_ENTRY seq=1 ret=004169a1 bounds=(586,16,799,229) backing=07ecd268 backing_sz=(214,214) backing_base=086b0030 map_surface=09fe5ab8 map_sz=(800,600) regs=(60,9f,4f,10) backing_samples=(01,01,01,01,01,21) map_samples=(01,01,01,01,c1,01)
FMMS_FULLREDRAW_AFTER_LOWER redraw=0 surface=09fe5ab8 size=(800,600) minimap_samples=(01,01,01,01) right_panel_samples=(01,01,01) bottom_samples=(c1,01,01)
FMMS_UNITSEL_DONE selected=3 prior=3 d526994=1 surface=09fe5ab8 size=(800,600)
SURFDUMP_READY redraw_seq=4 surface=09fe5ab8 size=(800,600) base=0a320030 bytes=480000
"""


def test_summary_passes_with_anchor_backing_and_unit_selection(fixture: Path) -> None:
    fixture.mkdir(parents=True, exist_ok=True)
    log = fixture / "cdb.log"
    log.write_text(SAMPLE_LOG, encoding="utf-8")
    report = summary_tool.summarize(log)
    assert report["passed"] is True, report
    assert report["unit_selected"] is True, report
    assert report["minimap_anchor_ok"] is True, report
    assert report["backing_size_ok"] is True, report
    assert report["map_surface_ok"] is True, report
    assert report["backing_black_like_percent"] > 80.0, report
    assert "mostly black-like" in report["interpretation"], report


def test_visibility_explains_right_bottom_blank_cells(fixture: Path) -> None:
    fixture.mkdir(parents=True, exist_ok=True)
    log = fixture / "cdb.log"
    log.write_text(SAMPLE_LOG, encoding="utf-8")
    coverage = fixture / "coverage.json"
    coverage.write_text(
        json.dumps(
            {
                "images": [
                    {
                        "frame_check": {
                            "gameplay_frame_likely": True,
                            "edge_coverage": {"right_edge_below_minimap_nonblack_percent": 0.0},
                        },
                        "summary": {
                            "blank_active_cells": ["r3c10", "r8c11"],
                            "flagged_active_cells": 2,
                            "measurable_active_cells": 99,
                        },
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    visibility = fixture / "visibility.json"
    visibility.write_text(
        json.dumps(
            {
                "blank_cells": ["r3c10", "r8c11"],
                "explained_blank_cells": ["r3c10", "r8c11"],
                "unexplained_blank_cells": [],
                "status_counts": {"visibility_zero": 2},
            }
        ),
        encoding="utf-8",
    )
    report = summary_tool.summarize(log, coverage, visibility)
    assert report["all_blank_cells_visibility_explained"] is True, report
    assert report["blank_active_cells"] == ["r3c10", "r8c11"], report
    assert report["visibility_unexplained_blank_cells"] == [], report
    assert "visibility-zero explained" in report["blocker"], report


def test_missing_ready_fails(fixture: Path) -> None:
    fixture.mkdir(parents=True, exist_ok=True)
    log = fixture / "missing-ready.log"
    log.write_text(SAMPLE_LOG.replace("SURFDUMP_READY", "SURFDUMP_NOT_READY"), encoding="utf-8")
    report = summary_tool.summarize(log)
    assert report["passed"] is False, report
    assert report["ready_seen"] is False, report


def test_cli_writes_outputs(fixture: Path) -> None:
    fixture.mkdir(parents=True, exist_ok=True)
    log = fixture / "cdb.log"
    log.write_text(SAMPLE_LOG, encoding="utf-8")
    out_json = fixture / "out" / "summary.json"
    out_md = fixture / "out" / "summary.md"
    coverage = fixture / "coverage.json"
    visibility = fixture / "visibility.json"
    coverage.write_text(
        json.dumps(
            {
                "images": [
                    {
                        "frame_check": {"gameplay_frame_likely": True},
                        "summary": {"blank_active_cells": ["r3c10"]},
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    visibility.write_text(
        json.dumps(
            {
                "blank_cells": ["r3c10"],
                "explained_blank_cells": ["r3c10"],
                "unexplained_blank_cells": [],
                "status_counts": {"visibility_zero": 1},
            }
        ),
        encoding="utf-8",
    )
    run = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            str(log),
            "--coverage-json",
            str(coverage),
            "--visibility-json",
            str(visibility),
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
    assert run.returncode == 0, run.stdout + run.stderr
    payload = json.loads(out_json.read_text(encoding="ascii"))
    assert payload["passed"] is True, payload
    assert "First Mission Minimap Surface Summary" in out_md.read_text(encoding="utf-8")


def run_tests() -> None:
    fixture = ROOT / ".codex-loop" / "tmp-tests" / "first-mission-minimap-surface-fixture"
    shutil.rmtree(fixture, ignore_errors=True)
    fixture.mkdir(parents=True)
    try:
        test_summary_passes_with_anchor_backing_and_unit_selection(fixture / "pass")
        test_visibility_explains_right_bottom_blank_cells(fixture / "visibility")
        test_missing_ready_fails(fixture / "missing-ready")
        test_cli_writes_outputs(fixture / "cli")
    finally:
        shutil.rmtree(fixture, ignore_errors=True)


def main() -> int:
    run_tests()
    print("first mission minimap surface summary tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
