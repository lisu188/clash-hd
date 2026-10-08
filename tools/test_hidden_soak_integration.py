#!/usr/bin/env python3
"""Synthetic assembler -> dispatcher -> refresh -> short/long guard integration.

Only tiny JSON/Markdown fixtures are written to a temporary directory. No game,
debugger, native compiler, proxy build or runtime harness is launched.
"""

from __future__ import annotations

import argparse
import copy
import json
import tempfile
from pathlib import Path

import hd_soak_long_report_guard as long_guard
import hd_soak_report as grader
import hd_soak_short_step_status as short_status
import hd_soak_short_validation_refresh as refresh
import hidden_soak_report_assembler as assembler
import test_hd_soak_short_validation_refresh as short_fixtures
import test_hidden_soak_report_assembler as samples_fixtures


def hidden_report(tmp: Path, route: str, duration: int, interval: int) -> dict:
    tmp.mkdir(parents=True, exist_ok=True)
    patch_path = short_fixtures.write_patch_stage_fixture(tmp / "patch-stage.json", samples_fixtures.SHA)
    count = duration // interval + 1
    samples = samples_fixtures.make_samples(route)
    samples.update(
        duration_sec=duration, duration_ticks=duration * 64, frame_interval_sec=interval,
        patch_stage_report=str(patch_path),
        frame_samples=samples_fixtures.frame_rows(count, interval, unique_hashes=2 if route == "map-pan" else 1),
        process_samples=samples_fixtures.process_rows(count, interval),
        elapsed_coverage={
            "formula": "duration_sec - sample_interval_sec - 2", "required_sec": duration - interval - 2,
            "frame_elapsed_sec": duration, "process_elapsed_sec": duration, "passed": True,
        },
    )
    samples["route_start_marker"]["route_ticks"] = duration * 64
    samples["route_end_marker"].update(route_ticks=duration * 64, tick_delta=duration * 64, hits=duration * 64 + 100)
    if route == "map-pan":
        samples["pan_events"] = [
            {"phase": index % 4, "x": 4 + int(index % 4 in (1, 2)),
             "y": 6 + int(index % 4 in (2, 3)), "hits": (index + 1) * 640,
             "tick_delta": (index + 1) * 640}
            for index in range((duration * 64 - 1) // 640)
        ]
        samples["route_end_marker"].update(
            scroll_x=samples["pan_events"][-1]["x"], scroll_y=samples["pan_events"][-1]["y"],
        )
        samples["pan_event_count"] = len(samples["pan_events"])
    report = assembler.assemble_report(samples)
    assert report["passed"], report["failures"]
    return report


def write_json(path: Path, payload: dict) -> Path:
    return short_fixtures.write_json(path, payload)


def completed_short_pipeline(tmp: Path) -> tuple[dict, Path]:
    manifest = short_fixtures.manifest_fixture(tmp)
    for step in manifest["step_reports"]:
        if step["id"] == "short2_menu_idle":
            report = short_fixtures.soak_report(step, passed=True)
        else:
            report = hidden_report(tmp / step["id"], step["route"], step["duration_sec"], 15)
        report["report_json"] = step["paths"]["report_json"]
        write_json(Path(report["report_json"]), report)
    manifest_path = write_json(tmp / "manifest.json", manifest)
    refreshed = refresh.build_report(argparse.Namespace(manifest_json=manifest_path))
    assert refreshed["passed"], refreshed["failures"]
    assert all(record["guard_overall"] for record in refreshed["steps"]), refreshed
    status = short_status.build_report(argparse.Namespace(manifest_json=manifest_path, legacy_report_json=tmp / "absent.json"))
    assert status["passed"] and status["ladder_complete"], status["failures"]
    assert status["counts"]["passed"] == 5
    return status, write_json(tmp / "short-status.json", status)


def test_full_hidden_pipeline_and_long_route_join(tmp: Path) -> None:
    status, status_path = completed_short_pipeline(tmp)
    refs = []
    for route in ("map-idle", "map-pan"):
        report = hidden_report(tmp / route, route, 7200, 30)
        report["report_json"] = str(tmp / route / "full-report.json")
        write_json(Path(report["report_json"]), report)
        evaluated = grader.evaluate_report_for_environment(report)
        assert evaluated["overall"], evaluated["failures"]
        valid, failures, _ = long_guard.validate_long_report(evaluated)
        assert valid, failures
        refs.append(str(write_json(tmp / route / "guard.json", evaluated)))
    proof = write_json(tmp / "proof.json", {"report_guards": refs})
    joined = long_guard.build_report(short_step_status_json=status_path, proof_json=proof)
    assert joined["overall"], joined["failures"]
    assert joined["counts"]["passing_routes"] == 2
    assert status["steps"][0]["summary"]["environment"] == "host_visible"
    assert all(row["summary"]["environment"] == "hidden_cdb_host" for row in status["steps"][1:])
    for row in joined["route_records"].values():
        assert row["input_responsiveness"] == "not_applicable_hidden"


def test_long_guard_rejects_relabeling_short_coverage_and_missing_provenance(tmp: Path) -> None:
    report = hidden_report(tmp, "map-pan", 7200, 30)
    report["report_json"] = str(tmp / "full-report.json")
    write_json(Path(report["report_json"]), report)
    evaluation = grader.evaluate_report_for_environment(report)
    assert evaluation["overall"], evaluation["failures"]
    assert long_guard.validate_long_report(evaluation)[0]
    for mutate in (
        lambda value: value.update(environment="host_visible"),
        lambda value: value.update(input_responsiveness=True),
        lambda value: value["checks"]["elapsed_coverage"]["summary"].update(duration_sec=120),
        lambda value: value["checks"].pop("wrapper_provenance"),
    ):
        altered = copy.deepcopy(evaluation)
        mutate(altered)
        assert not long_guard.validate_long_report(altered)[0]


def test_refresh_classifies_failed_hidden_sentinel_and_locks_short_step(tmp: Path) -> None:
    manifest = short_fixtures.manifest_fixture(tmp)
    step = manifest["step_reports"][1]
    report = hidden_report(tmp, "map-idle", 120, 15)
    report.update(report_json=step["paths"]["report_json"], input_responsiveness=True)
    path = write_json(Path(report["report_json"]), report)
    original = path.read_bytes()
    record, failures = refresh.refresh_step(step)
    assert not failures
    assert record["status"] == "validated_failed" and record["guard_overall"] is False
    triage = json.loads(Path(step["paths"]["triage_json"]).read_text(encoding="ascii"))
    assert triage["passed"] is False and triage["classification"] == "guard_validation_failure"
    assert path.read_bytes() == original
    _, passed, _, _ = short_status.step_status(step, prerequisites_passed=True, legacy_report=None)
    assert not passed


def test_lost_patch_provenance_revokes_saved_ladder_without_mutating_it(tmp: Path) -> None:
    status, path = completed_short_pipeline(tmp)
    original = path.read_bytes()
    source = json.loads(Path(status["steps"][1]["paths"]["report_json"]).read_text(encoding="ascii"))
    Path(source["patch_stage_report"]).unlink()
    assert not long_guard.short_ladder_complete(status)
    assert path.read_bytes() == original


def test_hidden_long_guard_revalidates_exact_source_and_patch_bytes(tmp: Path) -> None:
    source = hidden_report(tmp, "map-idle", 7200, 30)
    source["report_json"] = str(tmp / "full-report.json")
    path = write_json(Path(source["report_json"]), source)
    evaluation = grader.evaluate_report_for_environment(source)
    assert evaluation["overall"], evaluation["failures"]
    assert long_guard.validate_long_report(evaluation)[0]
    original = path.read_bytes()
    path.write_bytes(original + b"\n")
    assert not long_guard.validate_long_report(evaluation)[0]
    path.write_bytes(original)
    assert long_guard.validate_long_report(evaluation)[0]
    patch_path = Path(source["patch_stage_report"])
    patch_original = patch_path.read_bytes()
    patch_path.write_bytes(patch_original + b"\n")
    assert not long_guard.validate_long_report(evaluation)[0]
    patch_path.write_bytes(patch_original)
    assert long_guard.validate_long_report(evaluation)[0]
    patch_path.unlink()
    assert not long_guard.validate_long_report(evaluation)[0]
    path.unlink()
    assert not long_guard.validate_long_report(evaluation)[0]


def run_tests() -> None:
    with tempfile.TemporaryDirectory(prefix="clash-hidden-soak-integration-") as directory:
        tmp = Path(directory)
        test_full_hidden_pipeline_and_long_route_join(tmp / "pipeline")
        test_long_guard_rejects_relabeling_short_coverage_and_missing_provenance(tmp / "contradictions")
        test_refresh_classifies_failed_hidden_sentinel_and_locks_short_step(tmp / "failed-refresh")
        test_lost_patch_provenance_revokes_saved_ladder_without_mutating_it(tmp / "lost-provenance")
        test_hidden_long_guard_revalidates_exact_source_and_patch_bytes(tmp / "long-source-binding")


if __name__ == "__main__":
    run_tests()
    print("hidden soak integration tests passed (5 groups; synthetic only)")
