#!/usr/bin/env python3
"""Fixture tests for current_evidence_refresh soak report selection."""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path
from typing import Any

import current_evidence_refresh as refresh
import hd_soak_report


def write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="ascii")
    return path


def pending_report() -> dict[str, Any]:
    return {
        "executed": False,
        "passed": False,
        "runtime_policy": "opt-in visible runtime soak; use -Execute only after approval",
        "stage": hd_soak_report.PROTECTED_STABLE_STAGE,
        "stable_stage_should_change": False,
        "tier": "short2",
        "route": "menu-idle",
        "duration_sec": 120,
        "candidate": r"C:\ClashTests\hd-soak\pending.exe",
        "output_directory": r"C:\ClashCaptures\hd-soak\pending",
        "final_route_marker": "pending_approval",
        "failures": ["short2 menu-idle soak was not executed because visible-runtime escalation was not approved"],
        "execution_blocked_reason": "visible-runtime run requires explicit user approval",
    }


def visual_anomaly_report() -> dict[str, Any]:
    report = pending_report()
    report.update(
        {
            "executed": True,
            "passed": False,
            "failures": ["black/blank patch risk"],
            "frame_sample_count": 1,
            "frame_hash_unique_count": 1,
            "nonblack_percent_min": 0.0,
            "nonblack_percent_max": 0.0,
            "mean_luma_min": 2.0,
            "mean_luma_max": 2.0,
            "unique_sample_colors_min": 249,
            "unique_sample_colors_max": 249,
            "frame_samples": [
                {
                    "Name": "frame-0000",
                    "Timestamp": "2026-06-16T12:00:00.0000000+00:00",
                    "Width": 800,
                    "Height": 600,
                    "Hash": "a" * 64,
                    "NonblackPercent": 0.0,
                    "MeanLuma": 2.0,
                    "UniqueSampleColors": 249,
                    "NonblackBounds": {"X": 20, "Y": 20, "Right": 30, "Bottom": 30, "Width": 11, "Height": 11},
                }
            ],
        }
    )
    return report


def args_for(tmp: Path, legacy: Path, canonical: Path) -> argparse.Namespace:
    return argparse.Namespace(
        hd_soak_report=legacy,
        hd_soak_first_step_report=canonical,
        hd_soak_report_guard_json=tmp / "guard.json",
        hd_soak_report_guard_md=tmp / "guard.md",
        hd_soak_failure_triage_json=tmp / "triage.json",
        hd_soak_failure_triage_md=tmp / "triage.md",
    )


def test_legacy_report_selected_when_canonical_missing() -> None:
    with tempfile.TemporaryDirectory() as directory:
        tmp = Path(directory)
        legacy = write_json(tmp / "legacy.json", pending_report())
        canonical = tmp / "canonical.json"
        args = args_for(tmp, legacy, canonical)
        selected, source = refresh.selected_hd_soak_report_path(args)
        metadata = refresh.hd_soak_report_selection_metadata(args, selected, source)
    assert selected == legacy
    assert source == "legacy_compatibility"
    assert metadata["canonical_first_step_report"] == str(canonical)
    assert metadata["canonical_first_step_present"] is False
    assert metadata["legacy_report"] == str(legacy)
    assert metadata["legacy_report_present"] is True
    assert metadata["canonical_runtime_report_missing"] is True


def test_canonical_first_step_report_selected_when_present() -> None:
    with tempfile.TemporaryDirectory() as directory:
        tmp = Path(directory)
        legacy = write_json(tmp / "legacy.json", pending_report())
        canonical = write_json(tmp / "canonical.json", pending_report())
        args = args_for(tmp, legacy, canonical)
        selected, source = refresh.selected_hd_soak_report_path(args)
        metadata = refresh.hd_soak_report_selection_metadata(args, selected, source)
    assert selected == canonical
    assert source == "canonical_first_short_step"
    assert metadata["canonical_first_step_report"] == str(canonical)
    assert metadata["canonical_first_step_present"] is True
    assert metadata["legacy_report"] == str(legacy)
    assert metadata["legacy_report_present"] is True
    assert metadata["canonical_runtime_report_missing"] is False


def test_report_guard_and_triage_use_canonical_first_step_when_present() -> None:
    with tempfile.TemporaryDirectory() as directory:
        tmp = Path(directory)
        legacy = write_json(tmp / "legacy.json", pending_report())
        canonical = write_json(tmp / "canonical.json", pending_report())
        args = args_for(tmp, legacy, canonical)
        guard = refresh.build_hd_soak_report_guard(args)
        triage = refresh.build_hd_soak_failure_triage(args)
    assert guard["summary"]["source_report"] == str(canonical)
    assert guard["summary"]["source_report_selection"] == "canonical_first_short_step"
    assert guard["summary"]["canonical_first_step_report"] == str(canonical)
    assert guard["summary"]["canonical_first_step_present"] is True
    assert guard["summary"]["canonical_runtime_report_missing"] is False
    assert triage["summary"]["source_report"] == str(canonical)
    assert triage["summary"]["source_report_selection"] == "canonical_first_short_step"
    assert triage["summary"]["canonical_first_step_report"] == str(canonical)
    assert triage["summary"]["canonical_first_step_present"] is True
    assert triage["summary"]["canonical_runtime_report_missing"] is False
    assert triage["summary"]["classification"] == "not_executed_pending_approval"


def test_triage_summary_includes_visual_anomaly_counts() -> None:
    with tempfile.TemporaryDirectory() as directory:
        tmp = Path(directory)
        legacy = write_json(tmp / "legacy.json", pending_report())
        canonical = write_json(tmp / "canonical.json", visual_anomaly_report())
        args = args_for(tmp, legacy, canonical)
        triage = refresh.build_hd_soak_failure_triage(args)
    assert triage["summary"]["classification"] == "render_or_palette_regression"
    assert triage["summary"]["visual_anomaly_passed"] is False
    assert triage["summary"]["black_patch_risk_count"] == 1
    assert triage["summary"]["palette_or_stripe_risk_count"] == 0
    assert triage["summary"]["missing_nonblack_bounds_count"] == 0


COMPOSE_UI_SHA = "F" * 64


def write_compose_ui_run(
    run: Path,
    *,
    rows_present: bool,
) -> None:
    """Write a minimal synthetic right-bottom compose UI probe run directory."""
    marker_counts = {
        "SURFDUMP_PLAYGAME": 1,
        "SURFDUMP_READY": 1,
        "RBUI_DESC_SWITCH": 2 if rows_present else 0,
        "RBUI_VIEWPORT_SWITCH": 1,
        "RBUI_PANEL_DRAW": 1 if rows_present else 0,
        "RBUI_ACTION_BOX": 1 if rows_present else 0,
    }
    write_json(
        run / "right-bottom-ui-summary.json",
        {
            "Passed": True if rows_present else False,
            "Error": None,
            "SurfaceDumpPassed": True,
            "RbuiMarkersSeen": True,
            "RequiresOwnerActionRows": True,
            "OwnerActionRowsSeen": rows_present,
            "Stage": refresh.RIGHT_BOTTOM_COMPOSE_PATCH_STAGE,
            "ExtraProbeTemplate": "probes/cdb/ui/clash95_right_bottom_ui_extra.cdb",
            "CandidateSha256": COMPOSE_UI_SHA,
            "PngPath": None,
            "MarkerCounts": marker_counts,
        },
    )
    write_json(
        run / "summary.json",
        {
            "HiddenDesktop": True,
            "SkipMapValidation": False,
            "NoSkipStartAnims": True,
            "Stage": refresh.RIGHT_BOTTOM_COMPOSE_PATCH_STAGE,
        },
    )
    write_json(run / "right-bottom-ui-bounds.json", {"images": [{"regions": []}]})
    (run / "cdb-surface-dump.log").write_text("SURFDUMP_READY\n", encoding="ascii")


def write_compose_ui_manifest(path: Path) -> Path:
    return write_json(
        path,
        {
            "exe_sha256": COMPOSE_UI_SHA,
            "groups": {"right-bottom-compose-proof": {"patched": 4, "total": 4}},
            "current_hd_map_gate": {"passed": True},
        },
    )


def write_fixture_run(
    run: Path,
    *,
    log_text: str = (
        "NOWNER_435BC0_PANEL_DRAW selected=0\n"
        "NOWNER_435BC0_GRID_DRAW slot=0\n"
        "NOWNER_WRAPPER_COPYBACK_DONE\n"
        "NOWNER_WRAPPER_PRESENT_CALL\n"
    ),
    write_log: bool = True,
    write_result_summary: bool = True,
) -> None:
    run.mkdir(parents=True, exist_ok=True)
    if write_log:
        (run / "cdb-surface-dump.log").write_text(log_text, encoding="ascii")
    if write_result_summary:
        write_json(
            run / "right-bottom-slot-fixture-result-summary.json",
            {
                "proof_class": "non_natural_isolated_fixture",
                "expected_slot_match": True,
                "row_count": 272,
                "stage": "fixture-stage",
                "candidate_sha256": "D3FF",
            },
        )


def compose_ui_args(tmp: Path) -> argparse.Namespace:
    return argparse.Namespace(
        right_bottom_compose_ui_run=tmp / "compose-ui-run",
        right_bottom_compose_patch_manifest=write_compose_ui_manifest(tmp / "manifest.json"),
        right_bottom_compose_ui_fixture_run=tmp / "fixture-run",
    )


def test_compose_ui_probe_accepts_fixture_natural_draw() -> None:
    with tempfile.TemporaryDirectory() as directory:
        tmp = Path(directory)
        args = compose_ui_args(tmp)
        write_compose_ui_run(args.right_bottom_compose_ui_run, rows_present=False)
        write_fixture_run(args.right_bottom_compose_ui_fixture_run)
        result = refresh.build_right_bottom_compose_ui_probe(args)
    assert result["passed"] is True, result
    summary = result["summary"]
    assert summary["natural_draw_source"] == "slot5_as_slot0_fixture", result
    fixture = summary["fixture"]
    assert "user ruling 2026-07-14" in fixture["ruling"], result
    assert fixture["marker_counts"]["NOWNER_435BC0_PANEL_DRAW"] == 1, result
    assert fixture["marker_counts"]["NOWNER_435BC0_GRID_DRAW"] == 1, result
    assert fixture["marker_counts"]["NOWNER_WRAPPER_COPYBACK_DONE"] == 1, result
    assert fixture["av_count"] == 0, result
    assert fixture["proof_class"] == "non_natural_isolated_fixture", result


def test_compose_ui_probe_natural_rows_path_unchanged() -> None:
    with tempfile.TemporaryDirectory() as directory:
        tmp = Path(directory)
        args = compose_ui_args(tmp)
        write_compose_ui_run(args.right_bottom_compose_ui_run, rows_present=True)
        # No fixture run is written: the original natural-rows path must pass alone.
        result = refresh.build_right_bottom_compose_ui_probe(args)
    assert result["passed"] is True, result
    assert result["summary"]["natural_draw_source"] == "bare_map_natural_rows", result
    assert result["summary"]["fixture"] is None, result


def test_compose_ui_probe_fixture_missing_log_fails_closed() -> None:
    with tempfile.TemporaryDirectory() as directory:
        tmp = Path(directory)
        args = compose_ui_args(tmp)
        write_compose_ui_run(args.right_bottom_compose_ui_run, rows_present=False)
        write_fixture_run(args.right_bottom_compose_ui_fixture_run, write_log=False)
        result = refresh.build_right_bottom_compose_ui_probe(args)
    assert result["passed"] is False, result
    assert any(
        "missing right-bottom fixture natural-draw log" in failure for failure in result["failures"]
    ), result


def test_compose_ui_probe_fixture_marker_regression_fails_closed() -> None:
    with tempfile.TemporaryDirectory() as directory:
        tmp = Path(directory)
        args = compose_ui_args(tmp)
        write_compose_ui_run(args.right_bottom_compose_ui_run, rows_present=False)
        write_fixture_run(
            args.right_bottom_compose_ui_fixture_run,
            log_text="NOWNER_435BC0_GRID_DRAW\nNOWNER_WRAPPER_COPYBACK_DONE\n",
        )
        result = refresh.build_right_bottom_compose_ui_probe(args)
    assert result["passed"] is False, result
    assert any("NOWNER_435BC0_PANEL_DRAW" in failure for failure in result["failures"]), result


def test_compose_ui_probe_fixture_av_rows_fail_closed() -> None:
    with tempfile.TemporaryDirectory() as directory:
        tmp = Path(directory)
        args = compose_ui_args(tmp)
        write_compose_ui_run(args.right_bottom_compose_ui_run, rows_present=False)
        write_fixture_run(
            args.right_bottom_compose_ui_fixture_run,
            log_text=(
                "NOWNER_435BC0_PANEL_DRAW\n"
                "NOWNER_435BC0_GRID_DRAW\n"
                "NOWNER_WRAPPER_COPYBACK_DONE\n"
                "Access violation - code c0000005\n"
            ),
        )
        result = refresh.build_right_bottom_compose_ui_probe(args)
    assert result["passed"] is False, result
    assert any("AV rows" in failure for failure in result["failures"]), result


def test_compose_ui_probe_missing_result_summary_fails_closed() -> None:
    with tempfile.TemporaryDirectory() as directory:
        tmp = Path(directory)
        args = compose_ui_args(tmp)
        write_compose_ui_run(args.right_bottom_compose_ui_run, rows_present=False)
        write_fixture_run(args.right_bottom_compose_ui_fixture_run, write_result_summary=False)
        result = refresh.build_right_bottom_compose_ui_probe(args)
    assert result["passed"] is False, result
    assert any(
        "missing right-bottom fixture natural-draw result summary" in failure
        for failure in result["failures"]
    ), result


def test_compose_ui_probe_wrapper_failure_beyond_rows_absent_fails() -> None:
    with tempfile.TemporaryDirectory() as directory:
        tmp = Path(directory)
        args = compose_ui_args(tmp)
        write_compose_ui_run(args.right_bottom_compose_ui_run, rows_present=False)
        summary_path = args.right_bottom_compose_ui_run / "right-bottom-ui-summary.json"
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        summary["Error"] = "wrapper crashed"
        write_json(summary_path, summary)
        write_fixture_run(args.right_bottom_compose_ui_fixture_run)
        result = refresh.build_right_bottom_compose_ui_probe(args)
    assert result["passed"] is False, result
    assert any(
        "beyond the retired rows-absent expectation" in failure for failure in result["failures"]
    ), result


def run_tests() -> None:
    test_legacy_report_selected_when_canonical_missing()
    test_canonical_first_step_report_selected_when_present()
    test_report_guard_and_triage_use_canonical_first_step_when_present()
    test_triage_summary_includes_visual_anomaly_counts()
    test_compose_ui_probe_accepts_fixture_natural_draw()
    test_compose_ui_probe_natural_rows_path_unchanged()
    test_compose_ui_probe_fixture_missing_log_fails_closed()
    test_compose_ui_probe_fixture_marker_regression_fails_closed()
    test_compose_ui_probe_fixture_av_rows_fail_closed()
    test_compose_ui_probe_missing_result_summary_fails_closed()
    test_compose_ui_probe_wrapper_failure_beyond_rows_absent_fails()


if __name__ == "__main__":
    run_tests()
    print("current_evidence_refresh tests passed")
