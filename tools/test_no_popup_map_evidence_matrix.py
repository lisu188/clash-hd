#!/usr/bin/env python3
"""Fixture tests for the no-popup map evidence matrix helper."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from copy import deepcopy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "no_popup_map_evidence_matrix.py"
sys.path.insert(0, str(ROOT / "tools"))

import no_popup_map_evidence_matrix  # noqa: E402


SHA = "fixture-sha"


def run_script(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def good_normal_summary() -> dict:
    return {
        "Passed": True,
        "ForceVisibleEdges": False,
        "VisibilityRequireExplained": True,
        "VisibilityExplainedGate": {
            "Required": True,
            "Passed": True,
            "UnexplainedBlankCells": [],
        },
        "CoverageBlankActiveCells": ["r6c10", "r6c11"],
        "VisibilityStatusCounts": {"visibility_zero": 2},
        "VisibilityUnexplainedBlankCells": [],
        "PngPath": str(ROOT / "captures" / "fixture-normal.png"),
        "CandidateSha256": SHA,
        "Surface": {"Width": 800, "Height": 600, "Bytes": 480000},
    }


def good_forced_summary() -> dict:
    return {
        "Passed": True,
        "ForceVisibleEdges": True,
        "ForcedVisibleExitCode": 0,
        "CoverageBlankActiveCells": [],
        "ForcedVisibleGate": {
            "passed": True,
            "blank_active_cells": [],
            "vedge_visret_count": 54,
            "vedge_post_count": 54,
            "vedge_visret_nonzero_count": 54,
            "vedge_post_nonblack_count": 54,
            "latest_visdump": {"map0": [10, 17]},
        },
        "PngPath": str(ROOT / "captures" / "fixture-forced.png"),
        "CandidateSha256": SHA,
        "Surface": {"Width": 800, "Height": 600, "Bytes": 480000},
    }


def write_run(root: Path, name: str, summary: dict) -> Path:
    run = root / name
    run.mkdir(parents=True, exist_ok=True)
    (run / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return run


def args_for(captures: Path, normal: Path | None = None, forced: Path | None = None) -> argparse.Namespace:
    return argparse.Namespace(captures_root=captures, normal_run=normal, forced_run=forced)


def test_matrix_passes_with_explicit_runs(fixture: Path) -> None:
    captures = fixture / "captures"
    normal = write_run(captures, "cdb-surface-dump-20260101-010101", good_normal_summary())
    forced = write_run(captures, "cdb-surface-dump-20260101-010102", good_forced_summary())
    matrix = no_popup_map_evidence_matrix.build_matrix(args_for(captures, normal, forced))
    assert matrix["passed"] is True, matrix
    assert matrix["normal"]["blank_active_count"] == 2, matrix
    assert matrix["normal"]["unexplained_blank_count"] == 0, matrix
    assert matrix["forced_visible"]["blank_active_count"] == 0, matrix
    assert matrix["forced_visible"]["vedge_post_nonblack_count"] == 54, matrix
    markdown = no_popup_map_evidence_matrix.render_markdown(matrix)
    assert "- Overall: PASS" in markdown, markdown
    assert "Normal Visibility-Explained Run" in markdown, markdown
    assert "Forced-Visible Edge Run" in markdown, markdown


def test_matrix_scans_latest_passing_runs(fixture: Path) -> None:
    captures = fixture / "captures"
    bad_normal = good_normal_summary()
    bad_normal["VisibilityExplainedGate"]["Passed"] = False
    write_run(captures, "cdb-surface-dump-20260101-010101", bad_normal)
    selected_normal = write_run(captures, "cdb-surface-dump-20260101-010102", good_normal_summary())

    bad_forced = good_forced_summary()
    bad_forced["ForcedVisibleGate"]["passed"] = False
    write_run(captures, "cdb-surface-dump-20260101-010103", bad_forced)
    selected_forced = write_run(captures, "cdb-surface-dump-20260101-010104", good_forced_summary())

    matrix = no_popup_map_evidence_matrix.build_matrix(args_for(captures))
    assert matrix["passed"] is True, matrix
    assert matrix["normal"]["run"] == str(selected_normal), matrix
    assert matrix["forced_visible"]["run"] == str(selected_forced), matrix


def test_matrix_rejects_normal_regressions(fixture: Path) -> None:
    cases = [
        ("failed summary", ("Passed",), False, "summary Passed is false"),
        ("forced normal", ("ForceVisibleEdges",), True, "run is forced-visible"),
        ("explanation off", ("VisibilityRequireExplained",), False, "VisibilityRequireExplained is false"),
        ("failed gate", ("VisibilityExplainedGate", "Passed"), False, "VisibilityExplainedGate did not pass"),
        (
            "unexplained blanks",
            ("VisibilityExplainedGate", "UnexplainedBlankCells"),
            ["r8c11"],
            "unexplained blank cells",
        ),
    ]
    for label, keys, value, expected_failure in cases:
        captures = fixture / label.replace(" ", "-")
        normal_summary = deepcopy(good_normal_summary())
        current = normal_summary
        for key in keys[:-1]:
            current = current[key]
        current[keys[-1]] = value
        normal = write_run(captures, "cdb-surface-dump-20260101-010101", normal_summary)
        forced = write_run(captures, "cdb-surface-dump-20260101-010102", good_forced_summary())
        matrix = no_popup_map_evidence_matrix.build_matrix(args_for(captures, normal, forced))
        assert matrix["passed"] is False, matrix
        assert any(expected_failure in failure for failure in matrix["normal"]["failures"]), matrix


def test_matrix_rejects_forced_visible_regressions(fixture: Path) -> None:
    cases = [
        ("failed summary", ("Passed",), False, "summary Passed is false"),
        ("not forced", ("ForceVisibleEdges",), False, "run is not forced-visible"),
        ("failed gate", ("ForcedVisibleGate", "passed"), False, "ForcedVisibleGate did not pass"),
        ("bad exit", ("ForcedVisibleExitCode",), 2, "ForcedVisibleExitCode=2"),
        ("blank cells", ("CoverageBlankActiveCells",), ["r8c11"], "coverage blank active cells"),
    ]
    for label, keys, value, expected_failure in cases:
        captures = fixture / label.replace(" ", "-")
        forced_summary = deepcopy(good_forced_summary())
        current = forced_summary
        for key in keys[:-1]:
            current = current[key]
        current[keys[-1]] = value
        normal = write_run(captures, "cdb-surface-dump-20260101-010101", good_normal_summary())
        forced = write_run(captures, "cdb-surface-dump-20260101-010102", forced_summary)
        matrix = no_popup_map_evidence_matrix.build_matrix(args_for(captures, normal, forced))
        assert matrix["passed"] is False, matrix
        assert any(expected_failure in failure for failure in matrix["forced_visible"]["failures"]), matrix


def test_cli_writes_outputs_and_fails_closed(fixture: Path) -> None:
    captures = fixture / "captures"
    normal = write_run(captures, "cdb-surface-dump-20260101-010101", good_normal_summary())
    forced = write_run(captures, "cdb-surface-dump-20260101-010102", good_forced_summary())
    out_json = fixture / "good-output" / "matrix.json"
    out_md = fixture / "good-output" / "matrix.md"
    good_run = run_script(
        "--captures-root",
        str(captures),
        "--normal-run",
        str(normal),
        "--forced-run",
        str(forced),
        "--write-json",
        str(out_json),
        "--write-markdown",
        str(out_md),
        "--require-pass",
    )
    assert good_run.returncode == 0, good_run.stdout + good_run.stderr
    assert json.loads(out_json.read_text(encoding="ascii"))["passed"] is True
    assert "- Overall: PASS" in out_md.read_text(encoding="ascii")

    bad_normal_summary = good_normal_summary()
    bad_normal_summary["VisibilityExplainedGate"]["UnexplainedBlankCells"] = ["r8c11"]
    bad_normal = write_run(captures, "cdb-surface-dump-20260101-010103", bad_normal_summary)
    bad_json = fixture / "bad-output" / "matrix.json"
    bad_md = fixture / "bad-output" / "matrix.md"
    bad_run = run_script(
        "--captures-root",
        str(captures),
        "--normal-run",
        str(bad_normal),
        "--forced-run",
        str(forced),
        "--write-json",
        str(bad_json),
        "--write-markdown",
        str(bad_md),
        "--require-pass",
    )
    assert bad_run.returncode == 2, bad_run.stdout + bad_run.stderr
    assert json.loads(bad_json.read_text(encoding="ascii"))["passed"] is False
    assert "- Overall: FAIL" in bad_md.read_text(encoding="ascii")


def run_tests() -> None:
    fixture = ROOT / ".codex-loop" / "tmp-tests" / "no-popup-map-evidence-fixture"
    shutil.rmtree(fixture, ignore_errors=True)
    fixture.mkdir(parents=True)
    try:
        test_matrix_passes_with_explicit_runs(fixture / "explicit")
        test_matrix_scans_latest_passing_runs(fixture / "scan")
        test_matrix_rejects_normal_regressions(fixture / "normal-regressions")
        test_matrix_rejects_forced_visible_regressions(fixture / "forced-regressions")
        test_cli_writes_outputs_and_fails_closed(fixture / "cli")
    finally:
        shutil.rmtree(fixture, ignore_errors=True)


def main() -> int:
    run_tests()
    print("no-popup map evidence matrix tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
