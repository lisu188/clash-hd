#!/usr/bin/env python3
"""Fixture tests for hidden_soak_report_assembler.py plus static guards for the
hidden soak probe and runner. Only source-extracted parser functions are run in
isolated PowerShell; no full harness, game, debugger or native build executes."""

from __future__ import annotations

import copy
import json
import re
import subprocess
from contextlib import redirect_stdout
from io import StringIO
from unittest.mock import patch
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "hidden_soak_report_assembler.py"
PROBE = ROOT / "probes" / "cdb" / "soak" / "clash95_hidden_soak_route_extra.cdb"
RUNNER = ROOT / "scripts" / "cdb" / "run_hidden_soak.ps1"
sys.path.insert(0, str(ROOT / "tools"))

import hidden_soak_report_assembler as assembler  # noqa: E402
from test_hidden_soak_artifact_fixtures import fixture_artifact_reads, publish_fixture_report, seal_fixture


SHA = "a" * 64
BASE_SHA = "500055d77d03d514e8d3168506bd10f67cd8569bcc450604ff8192f46cdaf3ae"
START = datetime(2026, 7, 28, 10, 0, 0, tzinfo=timezone.utc)


def iso(offset_sec: int) -> str:
    return (START + timedelta(seconds=offset_sec)).isoformat()


def frame_rows(count: int, interval: int, *, unique_hashes: int = 1) -> list[dict[str, Any]]:
    rows = []
    for index in range(count):
        hash_index = index % max(1, unique_hashes)
        rows.append(
            {
                "Name": f"frame-{index + 1:04d}",
                "Timestamp": iso(index * interval),
                "Width": 800,
                "Height": 600,
                "Hash": f"{hash_index:02x}" * 32,
                "NonblackPercent": 87.5,
                "UniqueSampleColors": 42,
                "CaptureMode": "hidden-cdb-host-readprocessmemory",
                "RenderEvidence": True,
            }
        )
    return rows


def process_rows(count: int, interval: int) -> list[dict[str, Any]]:
    rows = []
    for index in range(count):
        rows.append(
            {
                "Timestamp": iso(index * interval),
                "HasExited": False,
                "ExitCode": None,
                "WorkingSet64": 50_000_000 + index * 1000,
                "PrivateMemorySize64": 40_000_000 + index * 1000,
                "HandleCount": 200 + (index % 3),
            }
        )
    return rows


def make_samples(route: str = "map-idle", *, _seal: bool = True, **overrides: Any) -> dict[str, Any]:
    duration = 120
    interval = 30
    count = (duration // interval) + 1
    samples: dict[str, Any] = {
        "schema": "hidden_cdb_host_soak_samples_v1",
        "generated_at": iso(0),
        "executed": True,
        "environment": "hidden_cdb_host",
        "route": route,
        "duration_sec": duration,
        "frame_interval_sec": interval,
        "duration_ticks": duration * 64,
        "pan_interval_sec": 10 if route == "map-pan" else None,
        "stage": assembler.PROTECTED_STABLE_STAGE,
        "input_exe": r"C:\Clash\clash95.exe",
        "input_sha256": BASE_SHA,
        "candidate": r"C:\ClashTests\hd-soak\hidden\run\clash95_hd_hidden_soak.exe",
        "candidate_sha256": SHA,
        "patch_stage_report": r"C:\ClashCaptures\hd-soak\hidden\run\patch-stage.json",
        "workdir": r"C:\Clash",
        "output_directory": r"C:\ClashCaptures\hd-soak\hidden\run",
        "load_slot": 2,
        "cdb_log": r"C:\ClashCaptures\hd-soak\hidden\run\hidden-soak-cdb.log",
        "generated_probe": r"C:\ClashCaptures\hd-soak\hidden\run\probe.generated.cdb",
        "launch_mode": "hidden-desktop",
        "frame_read_method": "host_readprocessmemory",
        "surface_base": "0x00b40000",
        "ready_marker": {
            "source": "SOAK_SURFDUMP_READY", "redraw_seq": 4, "surface": "00a00000",
            "base": "00b40000", "width": 800, "height": 600, "bytes": 480000,
            "line_number": 11,
        },
        "route_start_marker": {
            "route_ticks": duration * 64, "pan": int(route == "map-pan"), "player": 0,
            "tick": 1000, "game_data": "00c00000", "scroll_x": 4, "scroll_y": 6,
            "line_number": 10,
        },
        "route_end_marker": {
            "route_ticks": duration * 64, "pan": int(route == "map-pan"),
            "hits": 8192, "tick_delta": duration * 64, "player": 0,
            "scroll_x": 5 if route == "map-pan" else 4,
            "scroll_y": 7 if route == "map-pan" else 6,
            "line_number": 24,
        },
        "pan_plans": [{
            "source": "SOAK_PAN_PLAN", "safe": 1, "line_number": 12,
            "base_x": 4, "base_y": 6, "delta_x": 1, "delta_y": 1, "max_x": 20, "max_y": 20,
        }] if route == "map-pan" else [],
        "pan_events": [
            {"phase": index % 4, "x": 4 + int(index % 4 in (1, 2)),
             "y": 6 + int(index % 4 in (2, 3)), "hits": (index + 1) * 500,
             "tick_delta": (index + 1) * 640, "delta_x": 1, "delta_y": 1, "line_number": 13 + index}
            for index in range(11)
        ] if route == "map-pan" else [],
        "proxy": {
            "used": True, "path": r"C:\ClashTests\hd-soak\hidden\run\ddraw.dll",
            "sha256": "b" * 64,
            "build_manifest": r"C:\ClashTests\hd-soak\hidden\run\ddraw_surfdump_proxy.build.json",
            "log": r"C:\ClashTests\hd-soak\hidden\run\ddraw_surfdump_proxy.log",
            "build_log": r"C:\ClashCaptures\hd-soak\hidden\run\ddraw-proxy-build\build.log",
            "present_enabled": False,
        },
        "cleanup": {"game_stopped": True, "cdb_stopped": True, "errors": []},
        "elapsed_coverage": {
            "formula": "duration_sec - sample_interval_sec - 2", "required_sec": duration - interval - 2,
            "frame_elapsed_sec": duration, "process_elapsed_sec": duration, "passed": True,
        },
        "surface": {
            "Base": "00b40000",
            "Width": 800,
            "Height": 600,
            "Bytes": 480000,
            "Source": "SOAK_SURFDUMP_READY",
        },
        "ready_observed": True,
        "soak_route_start_observed": True,
        "soak_route_end_observed": True,
        "heartbeat_count": 4,
        "pan_event_count": 11 if route == "map-pan" else 0,
        "av_observed": False,
        "surface_invalid_observed": False,
        "app_request_quit_observed": False,
        "cdb_exit_before_duration": False,
        "game_exit_before_duration": False,
        "clean_stop": True,
        "clean_stop_mechanism": "harness_stop_after_route_end",
        "exit_code": None,
        "process_exited_unexpectedly": False,
        "input_responsiveness": "not_applicable_hidden",
        "runner_failures": [],
        "capture_errors": [],
        "frame_samples": frame_rows(count, interval, unique_hashes=3 if route == "map-pan" else 1),
        "process_samples": process_rows(count, interval),
        "artifact_bytes": 5_000_000,
        "max_artifact_mb": 250,
        "max_working_set_growth_mb": 64,
        "max_private_memory_growth_mb": 64,
        "max_handle_growth": 128,
        "report_json": r"C:\ClashCaptures\hd-soak\hidden\run\report.json",
        "report_markdown": r"C:\ClashCaptures\hd-soak\hidden\run\RUN-SUMMARY.md",
    }
    if _seal:
        samples = seal_fixture(samples)
    samples.update(overrides)
    return samples


def test_passing_map_idle() -> None:
    report = assembler.assemble_report(make_samples("map-idle"))
    assert report["passed"] is True, report["failures"]
    assert report["environment"] == "hidden_cdb_host"
    assert report["evidence_class"] == "approved_hidden_cdb_host_soak"
    assert report["input_responsiveness"] == "not_applicable_hidden"
    assert report["entry_mechanism_detail"]["forced"] is True
    assert report["entry_mechanism"] == "cdb_breakpoint_forced_loader_entry"
    assert report["pan_mechanism"] == "none"
    assert report["frame_stability_class"] == "stable_idle"
    assert report["tier"] == "short2"
    assert report["working_set_growth_bytes"] == 4000
    assert report["clean_stop"] is True


def test_artifact_layout_rejects_missing_cross_run_and_ambiguous_paths() -> None:
    original = make_samples()
    path_fields = (
        "input_exe", "workdir", "candidate", "output_directory", "cdb_log", "generated_probe",
        "proxy.path", "proxy.build_manifest", "proxy.log", "proxy.build_log",
    )
    cases = [(field, value) for field in path_fields for value in (None, "", 1, False, [], {})]
    cases.extend((field, (original["proxy"][field.split(".", 1)[1]] if field.startswith("proxy.") else original[field]) + separator)
                 for field in path_fields if field not in {"workdir", "output_directory"}
                 for separator in ("\\", "/"))
    cases.extend(("candidate", value) for value in (
        r"C:\ClashTests\hd-soak\hidden\run\..\candidate.exe",
        r"C:\ClashTests\hd-soak\hidden\run\.\candidate.exe",
        r"C:\ClashTests\hd-soak\hidden\run\candidate.exe:stream",
        r"C:\ClashTests\hd-soak\hidden\NUL.txt\candidate.exe",
        r"C:\ClashTests\hd-soak\hidden\run\candidate.exe.",
        r"C:\ClashTests\hd-soak\hidden\run \candidate.exe",
        r"\ClashTests\hd-soak\hidden\run\candidate.exe",
        r"C:ClashTests\hd-soak\hidden\run\candidate.exe",
        r"\\host\ClashTests\hd-soak\hidden\run\candidate.exe",
        r"\\?\C:\ClashTests\hd-soak\hidden\run\candidate.exe",
        r"\\.\C:\ClashTests\hd-soak\hidden\run\candidate.exe",
        r"C:\ClashTests\hd-soak\hidden\candidate.exe",
        r"C:\ClashTests\hd-soak\hidden\run\nested\candidate.exe",
        r"C:\ClashTests\hd-soak\different-run\candidate.exe",
    ))
    cases.extend((
        ("output_directory", r"C:\ClashCaptures\hd-soak\hidden\other-run"),
        ("output_directory", r"C:\ClashCaptures\hd-soak\hidden\run\nested"),
        ("proxy.path", r"C:\unrelated\ddraw.dll"),
        ("proxy.build_manifest", r"C:\ClashTests\hd-soak\hidden\other-run\ddraw_surfdump_proxy.build.json"),
        ("proxy.log", r"C:\ClashTests\hd-soak\hidden\run\nested\ddraw_surfdump_proxy.log"),
        ("proxy.build_log", r"C:\ClashCaptures\hd-soak\hidden\other-run\build.log"),
        ("proxy.build_log", original["output_directory"]),
        ("cdb_log", r"C:\ClashCaptures\hd-soak\hidden\other-run\hidden-soak-cdb.log"),
        ("generated_probe", r"C:\ClashCaptures\hd-soak-hidden\run\probe.generated.cdb"),
    ))
    for field, value in cases:
        samples = copy.deepcopy(original)
        container, key = (samples["proxy"], field.split(".", 1)[1]) if field.startswith("proxy.") else (samples, field)
        container[key] = value
        report = assembler.assemble_report(samples)
        assert not report["passed"], (field, value, report)
        assert any(field in failure for failure in report["failures"]), (field, value, report["failures"])


def test_artifact_layout_case_and_slashes_are_lexical_only() -> None:
    samples = make_samples()
    for field in ("input_exe", "workdir", "candidate", "output_directory", "cdb_log", "generated_probe"):
        samples[field] = samples[field].upper().replace("\\", "/")
    for field in ("path", "build_manifest", "log", "build_log"):
        samples["proxy"][field] = samples["proxy"][field].upper().replace("\\", "/")
    _, layout_failures = assembler.validate_hidden_artifact_layout(samples)
    assert not layout_failures, layout_failures
    report = assembler.assemble_report(samples)
    assert report["passed"], report["failures"]


def test_passing_map_pan_discloses_forced_pan() -> None:
    report = assembler.assemble_report(make_samples("map-pan"))
    assert report["passed"] is True, report["failures"]
    assert report["pan_mechanism"] == "cdb_forced_native_arrow_key"
    assert report["pan_mechanism_detail"]["forced"] is True
    assert report["pan_mechanism_detail"]["pan_event_count"] == 11
    assert report["frame_progress_expected"] is True
    assert report["frame_stability_class"] == "progressing"


def test_map_pan_without_pan_events_fails() -> None:
    report = assembler.assemble_report(make_samples("map-pan", pan_events=[], pan_event_count=0))
    assert report["passed"] is False
    assert any("no SOAK_PAN_SET" in failure for failure in report["failures"])


def test_map_pan_single_hash_fails() -> None:
    samples = make_samples("map-pan")
    samples["frame_samples"] = frame_rows(5, 30, unique_hashes=1)
    report = assembler.assemble_report(samples)
    assert report["passed"] is False
    assert any("frame progression required" in failure for failure in report["failures"])


def test_map_idle_with_pan_events_fails() -> None:
    report = assembler.assemble_report(make_samples("map-idle", pan_events=make_samples("map-pan")["pan_events"], pan_event_count=11))
    assert report["passed"] is False
    assert any("idle route must not pan" in failure for failure in report["failures"])


def test_av_and_missing_markers_fail() -> None:
    report = assembler.assemble_report(make_samples("map-idle", av_observed=True))
    assert report["passed"] is False
    assert any("access violation" in failure for failure in report["failures"])

    report = assembler.assemble_report(make_samples("map-idle", ready_marker=None))
    assert report["passed"] is False
    assert any("ready_marker is missing" in failure for failure in report["failures"])

    report = assembler.assemble_report(make_samples("map-idle", route_end_marker=None))
    assert report["passed"] is False
    assert any("route_end_marker is missing" in failure for failure in report["failures"])


def test_exit_before_duration_fails() -> None:
    report = assembler.assemble_report(
        make_samples(
            "map-idle",
            game_exit_before_duration=True,
            process_exited_unexpectedly=True,
            exit_code=-1,
            clean_stop=False,
            cleanup={"game_stopped": False, "cdb_stopped": True, "errors": []},
        )
    )
    assert report["passed"] is False
    assert any("exited before the soak duration" in failure for failure in report["failures"])
    assert any("did not stop the run cleanly" in failure for failure in report["failures"])


def test_fabricated_input_metric_fails() -> None:
    report = assembler.assemble_report(make_samples("map-idle", input_max_abs_error=0))
    assert report["passed"] is False
    assert any("refusing fields: input_max_abs_error" in failure for failure in report["failures"])

    report = assembler.assemble_report(
        make_samples("map-idle", route_results=[{"Name": "fake", "MaxAbsError": 0}])
    )
    assert report["passed"] is False
    assert any("refusing fields: route_results" in failure for failure in report["failures"])

    report = assembler.assemble_report(make_samples("map-idle", input_responsiveness=0))
    assert report["passed"] is False
    assert any("must record the 'not_applicable_hidden' sentinel" in failure for failure in report["failures"])


def test_sentinel_is_stamped_even_on_failure() -> None:
    report = assembler.assemble_report(make_samples("map-idle", av_observed=True))
    assert report["environment"] == "hidden_cdb_host"
    assert report["input_responsiveness"] == "not_applicable_hidden"
    assert report["entry_mechanism_detail"]["forced"] is True


def test_missing_host_process_metrics_fail() -> None:
    samples = make_samples("map-idle")
    samples["process_samples"] = process_rows(1, 30)
    report = assembler.assemble_report(samples)
    assert report["passed"] is False
    assert any("process sample count 1 is below 2" in failure for failure in report["failures"])
    assert any("REQUIRED" in failure and "working_set_growth_bytes" in failure for failure in report["failures"])


def test_render_thresholds_and_size_fail_closed() -> None:
    samples = make_samples("map-idle")
    for frame in samples["frame_samples"]:
        frame["NonblackPercent"] = 0.5
    report = assembler.assemble_report(samples)
    assert report["passed"] is False
    assert any("minimum nonblack percent" in failure for failure in report["failures"])

    samples = make_samples("map-idle")
    samples["frame_samples"][0]["Width"] = 640
    samples["frame_samples"][0]["Height"] = 480
    report = assembler.assemble_report(samples)
    assert report["passed"] is False
    assert any("were not 800x600" in failure for failure in report["failures"])


def test_wrong_capture_mode_fails() -> None:
    samples = make_samples("map-idle")
    samples["frame_samples"][0]["CaptureMode"] = "screen"
    report = assembler.assemble_report(samples)
    assert report["passed"] is False
    assert any("hidden-cdb-host-readprocessmemory" in failure for failure in report["failures"])


def test_elapsed_coverage_gap_fails() -> None:
    samples = make_samples("map-idle")
    samples["frame_samples"] = frame_rows(2, 5)
    report = assembler.assemble_report(samples)
    assert report["passed"] is False
    assert any("frame sample elapsed coverage" in failure for failure in report["failures"])


def test_periodic_coverage_rejects_sparse_unordered_and_missing_samples() -> None:
    samples = make_samples()
    samples.update(duration_sec=7200, duration_ticks=460800,
                   frame_samples=frame_rows(2, 7200), process_samples=process_rows(2, 7200))
    samples["route_start_marker"]["route_ticks"] = 460800
    samples["route_end_marker"].update(route_ticks=460800, tick_delta=460800)
    samples["elapsed_coverage"].update(required_sec=7168, frame_elapsed_sec=7200, process_elapsed_sec=7200)
    report = assembler.assemble_report(samples)
    assert not report["passed"]
    assert any("periodic sample count" in failure for failure in report["failures"])
    assert not report["elapsed_coverage"]["passed"]
    for inventory in ("frame_samples", "process_samples"):
        for mutation in ("interior_gap", "reversed", "duplicate", "malformed"):
            samples = make_samples()
            rows = samples[inventory]
            if mutation == "interior_gap":
                rows.pop(2)  # Endpoint coverage remains 120s and count remains sufficient.
            elif mutation == "reversed":
                rows[1], rows[2] = rows[2], rows[1]
            elif mutation == "duplicate":
                rows[2]["Timestamp"] = rows[1]["Timestamp"]
            else:
                rows[2] = "retained malformed original"
            report = assembler.assemble_report(samples)
            assert not report["passed"], (inventory, mutation)
            assert report[inventory] == rows  # No dropped or synthesized original rows.
            assert any("sample" in failure for failure in report["failures"])
    samples = make_samples()
    for inventory in ("frame_samples", "process_samples"):
        for row, seconds in zip(samples[inventory], (0, 31, 61, 92, 120)):
            row["Timestamp"] = iso(seconds)
    assert assembler.assemble_report(samples)["passed"]


def test_periodic_count_uses_the_same_bounded_jitter_as_each_gap() -> None:
    samples = make_samples(_seal=False)
    samples.update(duration_sec=1800, duration_ticks=115200, frame_interval_sec=15,
                   frame_samples=frame_rows(119, 15), process_samples=process_rows(119, 15))
    samples["route_start_marker"]["route_ticks"] = 115200
    samples["route_end_marker"].update(route_ticks=115200, tick_delta=115200)
    samples["elapsed_coverage"].update(required_sec=1783, frame_elapsed_sec=1798, process_elapsed_sec=1798)
    for inventory in ("frame_samples", "process_samples"):
        for index, row in enumerate(samples[inventory]):
            row["Timestamp"] = iso(index * 1798 / 118)
    report = assembler.assemble_report(seal_fixture(samples))
    assert report["passed"], report["failures"]
    assert report["frame_sample_count"] == report["process_sample_count"] == 119
    assert report["required_elapsed_sec"] == 1783


def test_terminal_marker_identity_and_scroll_are_bound_to_the_route() -> None:
    for route in ("map-idle", "map-pan"):
        for field in ("route_ticks", "pan", "player", "scroll_x", "scroll_y"):
            for missing in (True, False):
                samples = make_samples(route)
                end = samples["route_end_marker"]
                if missing:
                    end.pop(field)
                else:
                    end[field] += 1
                report = assembler.assemble_report(samples)
                assert not report["passed"], (route, field, missing)
                assert any(f"route_end_marker.{field}" in failure for failure in report["failures"]), report["failures"]


def test_every_process_sample_requires_live_numeric_telemetry() -> None:
    for field in ("WorkingSet64", "PrivateMemorySize64", "HandleCount", "HasExited"):
        for value in (None, -1, True, "unavailable"):
            samples = make_samples()
            samples["process_samples"][2][field] = value
            report = assembler.assemble_report(samples)
            assert not report["passed"], (field, value)
            assert any(field in failure for failure in report["failures"]), report["failures"]


def test_pan_events_require_positive_periodic_full_route_coverage() -> None:
    for mutation in ("negative_tick", "zero_hits", "missing_middle", "missing_tail", "late_start", "past_end"):
        samples = make_samples("map-pan")
        events = samples["pan_events"]
        if mutation == "negative_tick":
            events[0]["tick_delta"] = -1
        elif mutation == "zero_hits":
            events[0]["hits"] = 0
        elif mutation == "missing_middle":
            events.pop(3)
        elif mutation == "missing_tail":
            del events[4:]
        elif mutation == "late_start":
            for event in events:
                event["tick_delta"] += 129
        else:
            events[-1]["tick_delta"] = samples["duration_ticks"]
        samples["pan_event_count"] = len(events)
        report = assembler.assemble_report(samples)
        assert not report["passed"], mutation
        assert any("pan" in failure for failure in report["failures"]), report["failures"]
    samples = make_samples("map-pan", _seal=False)
    for event in samples["pan_events"]:
        event["tick_delta"] += 128  # Bounded first-redraw jitter, exact adjacent interval.
    assert assembler.assemble_report(seal_fixture(samples))["passed"]


def test_missing_or_forged_provenance_fails() -> None:
    for field in ("ready_marker", "route_start_marker", "route_end_marker", "proxy", "cleanup", "elapsed_coverage"):
        samples = make_samples()
        samples.pop(field)
        report = assembler.assemble_report(samples)
        assert not report["passed"], field
        assert any(field in failure for failure in report["failures"]), report["failures"]
    for field, value in (("present_enabled", True), ("sha256", "invalid"), ("used", False)):
        samples = make_samples()
        samples["proxy"][field] = value
        assert not assembler.assemble_report(samples)["passed"], (field, value)
    samples = make_samples()
    samples["route_end_marker"]["tick_delta"] = 10
    assert not assembler.assemble_report(samples)["passed"]
    samples = make_samples()
    samples["elapsed_coverage"]["frame_elapsed_sec"] = 999
    assert not assembler.assemble_report(samples)["passed"]


def test_reports_pass_shared_hidden_grader(fixture: Path) -> None:
    from hd_soak_report import evaluate_report_for_environment

    fixture.mkdir(parents=True, exist_ok=True)
    for route in ("map-idle", "map-pan"):
        report = publish_fixture_report(assembler.assemble_report(make_samples(route)), fixture)
        guard = evaluate_report_for_environment(report)
        assert guard["overall"], guard["failures"]


def test_every_hidden_frame_requires_strict_metrics_and_surface_provenance(fixture: Path) -> None:
    from hd_soak_report import evaluate_report_for_environment

    fixture.mkdir(parents=True, exist_ok=True)
    samples = make_samples()
    baseline = publish_fixture_report(assembler.assemble_report(samples), fixture)
    assert baseline["passed"]
    assert evaluate_report_for_environment(baseline)["overall"]
    cases = [
        ("NonblackPercent", value)
        for value in (None, True, False, "87.5", float("nan"), float("inf"), -float("inf"), -1, 101, 9.9)
    ] + [
        ("UniqueSampleColors", value)
        for value in (None, True, False, "42", 42.5, float("nan"), float("inf"), -1, 257, 7)
    ] + [
        ("CaptureMode", "screen"), ("CaptureMode", "qmp_screendump"), ("CaptureMode", None),
        ("RenderEvidence", False), ("Width", 800.5), ("Height", "600"),
        ("Hash", int("1" * 64)),
    ]
    for field, value in cases:
        invalid = copy.deepcopy(samples)
        invalid["frame_samples"][1][field] = value
        assembled = assembler.assemble_report(invalid)
        assert not assembled["passed"], (field, value, assembled["failures"])
        # Independently exercise the public grader on a formerly passing
        # report. Do not let assembler source_status=False supply the failure.
        supplied = copy.deepcopy(baseline)
        supplied["frame_samples"] = invalid["frame_samples"]
        guard = evaluate_report_for_environment(supplied)
        assert not guard["overall"], (field, value)
        assert not guard["checks"]["render_metrics"]["passed"], (field, value, guard["failures"])
        assert supplied["frame_samples"] == invalid["frame_samples"]
    for field in ("NonblackPercent", "UniqueSampleColors"):
        invalid = copy.deepcopy(samples)
        del invalid["frame_samples"][1][field]
        assert not assembler.assemble_report(invalid)["passed"], field
        supplied = copy.deepcopy(baseline)
        supplied["frame_samples"] = invalid["frame_samples"]
        assert not evaluate_report_for_environment(supplied)["overall"], field

    # Legacy hidden grader rows omit the optional stamp and name the same
    # surface-read mechanism differently. The raw assembler stays canonical.
    legacy = copy.deepcopy(baseline)
    for row in legacy["frame_samples"]:
        row.pop("RenderEvidence")
        row["CaptureMode"] = "host_readprocessmemory_surface"
    # A distinct valid compatibility baseline gets its own source publication;
    # never overwrite the canonical baseline used by the negative mutations.
    legacy = publish_fixture_report(legacy, fixture / "legacy-positive")
    assert evaluate_report_for_environment(legacy)["overall"]
    raw_legacy = copy.deepcopy(samples)
    raw_legacy["frame_samples"] = legacy["frame_samples"]
    assert not assembler.assemble_report(raw_legacy)["passed"]
    unstamped = copy.deepcopy(samples)
    for row in unstamped["frame_samples"]:
        row.pop("RenderEvidence")
    assert assembler.assemble_report(unstamped)["passed"]


def test_pan_count_uses_the_same_bounded_jitter_as_each_gap(fixture: Path) -> None:
    from hd_soak_report import evaluate_report_for_environment

    fixture.mkdir(parents=True, exist_ok=True)
    samples = make_samples("map-pan", _seal=False)
    samples["pan_events"] = [
        {"phase": index % 4, "x": 4 + int(index % 4 in (1, 2)),
         "y": 6 + int(index % 4 in (2, 3)), "hits": (index + 1) * 500,
         "tick_delta": (index + 1) * 768, "delta_x": 1, "delta_y": 1, "line_number": 13 + index}
        for index in range(9)
    ]
    samples["pan_event_count"] = len(samples["pan_events"])
    samples["route_end_marker"].update(scroll_x=4, scroll_y=6)
    samples = seal_fixture(samples)
    report = publish_fixture_report(assembler.assemble_report(samples), fixture)
    assert report["passed"], report["failures"]
    assert evaluate_report_for_environment(report)["overall"]
    samples["pan_events"][0]["tick_delta"] += 1
    assert not assembler.assemble_report(samples)["passed"]
    supplied = copy.deepcopy(report)
    supplied["pan_events"] = samples["pan_events"]
    guard = evaluate_report_for_environment(supplied)
    assert not guard["overall"]
    assert not guard["checks"]["marker_provenance"]["passed"]


def test_terminal_redraw_hits_must_advance_after_the_final_pan(fixture: Path) -> None:
    from hd_soak_report import evaluate_report_for_environment

    fixture.mkdir(parents=True, exist_ok=True)
    samples = make_samples("map-pan", _seal=False)
    final_pan_hits = samples["pan_events"][-1]["hits"]
    assert samples["route_end_marker"]["tick_delta"] > samples["pan_events"][-1]["tick_delta"]
    samples["route_end_marker"]["hits"] = final_pan_hits + 1
    samples = seal_fixture(samples)
    baseline = publish_fixture_report(assembler.assemble_report(samples), fixture)
    assert baseline["passed"], baseline["failures"]
    assert evaluate_report_for_environment(baseline)["overall"]
    for hits in (0, 1, final_pan_hits - 1, final_pan_hits):
        invalid = copy.deepcopy(samples)
        invalid["route_end_marker"]["hits"] = hits
        assembled = assembler.assemble_report(invalid)
        assert not assembled["passed"], hits
        assert any("route_end_marker.hits" in failure for failure in assembled["failures"])
        supplied = copy.deepcopy(baseline)
        supplied["route_end_marker"] = invalid["route_end_marker"]
        guard = evaluate_report_for_environment(supplied)
        assert not guard["overall"], hits
        assert not guard["checks"]["marker_provenance"]["passed"]
        assert any("route_end_marker.hits" in failure for failure in guard["failures"])


def test_pan_coordinates_require_one_genuine_exact_four_phase_cycle(fixture: Path) -> None:
    from hd_soak_report import evaluate_report_for_environment

    fixture.mkdir(parents=True, exist_ok=True)

    def cycle(dx: int, dy: int, *, declared: bool = False) -> dict[str, Any]:
        samples = make_samples("map-pan", _seal=False)
        base_x, base_y = (4 if dx else 0), (6 if dy else 0)
        samples["route_start_marker"].update(scroll_x=base_x, scroll_y=base_y)
        samples["pan_plans"][0].update(
            base_x=base_x, base_y=base_y, delta_x=dx, delta_y=dy,
            max_x=20 if dx == 1 else base_x, max_y=20 if dy == 1 else base_y,
        )
        for index, event in enumerate(samples["pan_events"]):
            event["x"] = base_x + (dx if index % 4 in (1, 2) else 0)
            event["y"] = base_y + (dy if index % 4 in (2, 3) else 0)
            event.update(delta_x=dx, delta_y=dy)
        if not declared:
            # Pattern inference stays independently tested, but a full new
            # receipt must retain the deltas actually emitted by the probe.
            inferred = copy.deepcopy(samples["pan_events"])
            for event in inferred:
                event.pop("delta_x")
                event.pop("delta_y")
            from hd_soak_report import hidden_pan_pattern_failures
            if (dx, dy) != (0, 0):
                assert not hidden_pan_pattern_failures(samples["route_start_marker"], inferred)
        samples["route_end_marker"].update(
            scroll_x=samples["pan_events"][-1]["x"], scroll_y=samples["pan_events"][-1]["y"],
        )
        return seal_fixture(samples)

    for dx, dy in ((1, 1), (-1, -1), (1, -1), (-1, 1), (1, 0), (-1, 0), (0, 1), (0, -1)):
        for declared in (False, True):
            samples = cycle(dx, dy, declared=declared)
            report = publish_fixture_report(assembler.assemble_report(samples), fixture)
            assert report["passed"], (dx, dy, declared, report["failures"])
            assert evaluate_report_for_environment(report)["overall"], (dx, dy, declared)
    baseline = publish_fixture_report(assembler.assemble_report(cycle(1, 1)), fixture)
    for mutation in ("zero_pan", "wrong_phase_zero", "wrong_phase_y", "inconsistent_x", "inconsistent_y",
                     "declared_zero", "declared_inconsistent", "declared_partial", "fractional_coordinate"):
        invalid = cycle(1, 1)
        events = invalid["pan_events"]
        if mutation == "zero_pan":
            invalid = cycle(0, 0)
        elif mutation == "wrong_phase_zero":
            events[0]["x"] = 5
        elif mutation == "wrong_phase_y":
            events[1]["y"] = 7
        elif mutation == "inconsistent_x":
            events[5]["x"] = 3
        elif mutation == "inconsistent_y":
            events[6]["y"] = 5
        elif mutation == "declared_zero":
            for event in events:
                event.update(delta_x=0, delta_y=0)
        elif mutation == "declared_inconsistent":
            invalid = cycle(1, 1, declared=True)
            invalid["pan_events"][2]["delta_x"] = -1
        elif mutation == "declared_partial":
            events[0]["delta_x"] = 1
            events[0].pop("delta_y")
        else:
            events[1]["x"] = 4.5
        assembled = assembler.assemble_report(invalid)
        assert not assembled["passed"], mutation
        supplied = copy.deepcopy(baseline)
        supplied["pan_events"] = invalid["pan_events"]
        supplied["route_end_marker"] = invalid["route_end_marker"]
        guard = evaluate_report_for_environment(supplied)
        assert not guard["overall"], mutation
        assert not guard["checks"]["marker_provenance"]["passed"], mutation
        assert any("pan" in failure for failure in guard["failures"]), (mutation, guard["failures"])


def test_live_pan_plan_receipts_are_retained_and_independently_regraded(fixture: Path) -> None:
    from hd_soak_report import evaluate_report_for_environment

    fixture.mkdir(parents=True, exist_ok=True)
    samples = make_samples("map-pan")
    baseline = publish_fixture_report(assembler.assemble_report(samples), fixture)
    assert baseline["passed"], baseline["failures"]
    assert baseline["pan_plans"] == samples["pan_plans"]
    assert evaluate_report_for_environment(baseline)["overall"]

    mutations = [
        "missing", "empty", "duplicate", "nonobject", "nonarray", "source_prose",
        "unsafe", "safe_bool", "safe_text", "negative_max", "negative_base", "base_beyond_max",
        "outward_at_upper_bound", "wrong_interior_direction", "voluntary_zero_axis", "voluntary_zero_x", "base_mismatch",
        "before_start", "before_ready", "at_end", "start_after_plan", "ready_after_plan",
        "end_before_events", "event_before_plan", "event_at_end", "event_duplicate_line",
        "event_missing_line", "event_missing_delta", "event_changed_delta", "event_bool_delta", "event_bool_line",
        "missing_start_line", "missing_ready_line", "missing_end_line",
    ]
    for field in ("base_x", "base_y", "max_x", "max_y", "delta_x", "delta_y", "line_number"):
        mutations.extend((f"missing_{field}", f"bool_{field}", f"float_{field}", f"text_{field}"))
    for mutation in mutations:
        invalid = copy.deepcopy(samples)
        plan = invalid["pan_plans"][0]
        events = invalid["pan_events"]
        if mutation == "missing":
            invalid.pop("pan_plans")
        elif mutation == "empty":
            invalid["pan_plans"] = []
        elif mutation == "duplicate":
            invalid["pan_plans"].append(copy.deepcopy(plan))
        elif mutation == "nonobject":
            invalid["pan_plans"] = ["SOAK_PAN_PLAN"]
        elif mutation == "nonarray":
            invalid["pan_plans"] = plan
        elif mutation == "source_prose":
            plan["source"] = ".echo SOAK_PAN_PLAN base=(4,6) delta=(1,1) max=(20,20) safe=1"
        elif mutation in ("unsafe", "safe_bool", "safe_text"):
            plan["safe"] = {"unsafe": 0, "safe_bool": True, "safe_text": "1"}[mutation]
        elif mutation == "negative_max":
            plan["max_x"] = -1
        elif mutation == "negative_base":
            plan["base_x"] = -1
        elif mutation == "base_beyond_max":
            plan["base_y"] = 21
        elif mutation == "outward_at_upper_bound":
            plan["max_x"] = plan["base_x"]
        elif mutation in ("wrong_interior_direction", "voluntary_zero_axis", "voluntary_zero_x"):
            axis = "x" if mutation != "voluntary_zero_axis" else "y"
            delta = -1 if mutation == "wrong_interior_direction" else 0
            plan[f"delta_{axis}"] = delta
            for index, event in enumerate(events):
                active = index % 4 in ((1, 2) if axis == "x" else (2, 3))
                event[axis] = plan[f"base_{axis}"] + (delta if active else 0)
                event[f"delta_{axis}"] = delta
            invalid["route_end_marker"][f"scroll_{axis}"] = events[-1][axis]
        elif mutation == "base_mismatch":
            invalid["route_start_marker"]["scroll_x"] = 3
        elif mutation in ("before_start", "before_ready", "at_end"):
            plan["line_number"] = {
                "before_start": invalid["route_start_marker"]["line_number"] - 1,
                "before_ready": invalid["ready_marker"]["line_number"],
                "at_end": invalid["route_end_marker"]["line_number"],
            }[mutation]
        elif mutation in ("start_after_plan", "ready_after_plan", "end_before_events"):
            marker = {"start_after_plan": "route_start_marker", "ready_after_plan": "ready_marker",
                      "end_before_events": "route_end_marker"}[mutation]
            invalid[marker]["line_number"] = (plan["line_number"] + 1 if marker != "route_end_marker"
                                               else events[-1]["line_number"])
        elif mutation == "event_before_plan":
            events[0]["line_number"] = plan["line_number"]
        elif mutation == "event_at_end":
            events[-1]["line_number"] = invalid["route_end_marker"]["line_number"]
        elif mutation == "event_duplicate_line":
            events[1]["line_number"] = events[0]["line_number"]
        elif mutation == "event_missing_line":
            events[0].pop("line_number")
        elif mutation == "event_missing_delta":
            events[0].pop("delta_y")
        elif mutation == "event_changed_delta":
            events[0]["delta_y"] = -1
        elif mutation == "event_bool_delta":
            events[0]["delta_y"] = True
        elif mutation == "event_bool_line":
            events[0]["line_number"] = True
        elif mutation in ("missing_start_line", "missing_ready_line", "missing_end_line"):
            marker = {"missing_start_line": "route_start_marker", "missing_ready_line": "ready_marker",
                      "missing_end_line": "route_end_marker"}[mutation]
            invalid[marker].pop("line_number")
        else:
            kind, field = mutation.split("_", 1)
            if kind == "missing":
                plan.pop(field)
            else:
                plan[field] = {"bool": True, "float": 1.0, "text": "1"}[kind]
        before = copy.deepcopy(invalid)
        assembled = assembler.assemble_report(invalid)
        assert not assembled["passed"], mutation
        assert assembled["pan_plans"] == invalid.get("pan_plans"), mutation
        assert invalid == before, mutation
        # Regrade a formerly passing report independently of the assembler's
        # saved source_status/failures. Missing original receipts stay missing.
        supplied = copy.deepcopy(baseline)
        for field in ("pan_plans", "pan_events", "route_start_marker", "ready_marker", "route_end_marker"):
            if field in invalid:
                supplied[field] = invalid[field]
            else:
                supplied.pop(field, None)
        guard = evaluate_report_for_environment(supplied)
        assert not guard["overall"], mutation
        assert not guard["checks"]["marker_provenance"]["passed"], mutation
        assert any("pan_plan" in failure or "retained pan plan" in failure
                   or ".line_number" in failure for failure in guard["failures"]), (mutation, guard["failures"])

    idle = make_samples("map-idle", pan_plans=samples["pan_plans"])
    assert not assembler.assemble_report(idle)["passed"]
    # A missing retained inventory is not equivalent to an observed empty one.
    idle.pop("pan_plans")
    missing_inventory = assembler.assemble_report(idle)
    assert not missing_inventory["passed"]
    assert any("pan_plans inventory" in failure for failure in missing_inventory["failures"])


def test_runner_structured_marker_parser(fixture: Path) -> None:
    """Run only two source-extracted pure functions, never the runtime script."""
    powershell = Path(r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe")
    if not powershell.exists():
        return  # Windows-only parser coverage; portable assembler checks still run.
    fixture.mkdir(parents=True, exist_ok=True)
    helper = fixture / "parse-only.ps1"
    helper.write_text(r'''
param([string]$Runner, [string]$Log, [string]$Route)
$ErrorActionPreference = 'Stop'
$tokens = $null
$parseErrors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile($Runner, [ref]$tokens, [ref]$parseErrors)
if ($parseErrors.Count) { throw ($parseErrors | Out-String) }
foreach ($functionName in @('Parse-SoakLog', 'Get-RouteValidationFailures')) {
    $definition = $ast.Find({ param($node) $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -eq $functionName }, $true)
    if (-not $definition) { throw "Function not found: $functionName" }
    Invoke-Expression $definition.Extent.Text
}
$observed = Parse-SoakLog -LogText ([System.IO.File]::ReadAllText($Log))
$failures = @(Get-RouteValidationFailures -Observations $observed -ExpectedRoute $Route -ExpectedDurationTicks 7680 -ExpectedPanIntervalTicks 640)
$observations = $observed
$ready = @($observed.ReadyRows | Where-Object { $_.Source -eq 'SOAK_SURFDUMP_READY' }) | Select-Object -First 1
$startMarker = @($observed.RouteStarts) | Select-Object -First 1
$endMarker = @($observed.RouteEnds) | Select-Object -First 1
# Execute only the five exact serialization expressions from the samples
# hashtable. No surrounding harness, preflight, build or launch is invoked.
$samplesAssignment = $ast.Find({ param($node)
    $node -is [System.Management.Automation.Language.AssignmentStatementAst] -and
    $node.Left.Extent.Text -eq '$samples'
}, $true)
$samplesHashtable = $samplesAssignment.Right.Find({ param($node)
    $node -is [System.Management.Automation.Language.HashtableAst]
}, $true)
$serialized = [ordered]@{}
foreach ($field in @('ready_marker', 'route_start_marker', 'route_end_marker', 'pan_plans', 'pan_events')) {
    $entry = @($samplesHashtable.KeyValuePairs | Where-Object { $_.Item1.Extent.Text -eq $field })[0]
    if (-not $entry) { throw "Missing serialization field: $field" }
    if ($field -in @('pan_plans', 'pan_events')) {
        $serialized[$field] = @(Invoke-Expression $entry.Item2.Extent.Text)
    } else {
        $serialized[$field] = Invoke-Expression $entry.Item2.Extent.Text
    }
}
[ordered]@{
    ready = @($observed.ReadyRows).Count; starts = @($observed.RouteStarts).Count; ends = @($observed.RouteEnds).Count
    heartbeat = @($observed.Heartbeats).Count; pan = @($observed.PanEvents).Count
    plans = @($observed.PanPlans)
    serialized = $serialized
    av = $observed.AvObserved; invalid = $observed.SurfaceInvalidObserved; quit = $observed.AppRequestQuitObserved
    failures = $failures
} | ConvertTo-Json -Depth 8
''', encoding="ascii")
    prose = ".echo SOAK_ROUTE_END and AV_SURFDUMP SURFDUMP_INVALID SURFDUMP_APP_REQUEST_QUIT\n"

    def parse(log: str, route: str = "map-idle") -> dict[str, Any]:
        log_path = fixture / "input.log"
        log_path.write_text(log, encoding="ascii")
        result = subprocess.run(
            [str(powershell), "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(helper), "-Runner", str(RUNNER),
             "-Log", str(log_path), "-Route", route], capture_output=True, text=True, check=False,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        return json.loads(result.stdout)

    observed = parse(prose)
    assert observed["ready"] == observed["starts"] == observed["ends"] == 0, observed
    assert not any(observed[field] for field in ("av", "invalid", "quit")), observed
    assert observed["failures"], observed

    ready = "SOAK_SURFDUMP_READY redraw_seq=4 surface=00a00000 size=(800,600) base=00b40000 bytes=480000\n"
    start = "SOAK_ROUTE_START route_ticks=7680 pan=0 player=0 tick=1000 gd=00c00000 scroll=(4,6)\n"
    heartbeat = "SOAK_HEARTBEAT hits=2048 tickdelta=2000 player=0 scroll=(4,6)\n"
    end = "SOAK_ROUTE_END route_ticks=7680 pan=0 hits=8192 tickdelta=7680 player=0 scroll=(4,6)\n"
    idle = prose + start + ready + heartbeat + end
    observed = parse(idle)
    assert not observed["failures"], observed
    assert observed["ready"] == observed["starts"] == observed["ends"] == observed["heartbeat"] == 1, observed
    assert parse(idle.replace("tickdelta=7680", "tickdelta=10"))["failures"]

    pan_plan = "SOAK_PAN_PLAN base=(4,6) delta=(1,1) max=(20,20) safe=1\n"
    pan_event_rows = [
        f"SOAK_PAN_SET phase={event['phase']} x={event['x']} y={event['y']} hits={event['hits']} "
        f"tickdelta={event['tick_delta']} delta=(1,1)\n"
        for event in make_samples("map-pan")["pan_events"]
    ]
    pan_heartbeat = heartbeat.replace("hits=2048", "hits=1600")
    pan = (prose + start.replace("pan=0", "pan=1") + ready + pan_plan
           + "".join(pan_event_rows[:3]) + pan_heartbeat.replace("scroll=(4,6)", "scroll=(5,7)")
           + "".join(pan_event_rows[3:])
           + end.replace("pan=0", "pan=1").replace("scroll=(4,6)", "scroll=(5,7)"))
    parsed = parse(pan, "map-pan")
    assert not parsed["failures"]
    assert len(parsed["plans"]) == 1
    assert parsed["plans"][0] == {
        "Source": "SOAK_PAN_PLAN", "Safe": 1, "BaseX": 4, "BaseY": 6,
        "DeltaX": 1, "DeltaY": 1, "MaxX": 20, "MaxY": 20, "LineNumber": 4,
    }, parsed["plans"]
    assert not parse(prose + ".echo " + pan_plan)["plans"]
    assert not parse(pan_plan.replace("safe=1", "safe=0"))["plans"]
    # Real source parser and source serialization feed the assembler and
    # independent dispatcher. All inputs remain tiny synthetic fixture rows.
    from hd_soak_report import evaluate_report_for_environment
    parsed_samples = make_samples("map-pan", _seal=False)
    parsed_samples.update(parsed["serialized"])
    parsed_samples = seal_fixture(parsed_samples)
    report = publish_fixture_report(assembler.assemble_report(parsed_samples), fixture)
    assert report["passed"], report["failures"]
    assert evaluate_report_for_environment(report)["overall"]
    missing = copy.deepcopy(report)
    missing.pop("pan_plans")
    assert not evaluate_report_for_environment(missing)["overall"]
    assert parse(pan.replace("phase=1 x=5", "phase=1 x=99"), "map-pan")["failures"]
    # A real short30 run logged event 7 at 5121 after scheduling it at 5120,
    # then event 8 at 5760. Keep rejecting that 639-tick observation: fixing
    # the producer's clock sampling must not relax the evidence interval.
    split_clock_pan = pan.replace("tickdelta=5120", "tickdelta=5121")
    observed = parse(split_clock_pan, "map-pan")
    assert any("SOAK_PAN_SET event 8 is not ordered" in failure for failure in observed["failures"]), observed


def test_cli_writes_outputs_and_require_pass_fails_closed(fixture: Path) -> None:
    samples_path = fixture / "samples.json"
    samples_path.parent.mkdir(parents=True, exist_ok=True)
    samples_path.write_text(
        json.dumps(make_samples("map-idle", av_observed=True), indent=2), encoding="ascii"
    )
    out_json = fixture / "report.json"
    out_md = fixture / "RUN-SUMMARY.md"
    result = subprocess.run(
        [
            sys.executable,
            "-B",
            str(SCRIPT),
            str(samples_path),
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
    assert result.returncode == 1, result.stdout + result.stderr
    report = json.loads(out_json.read_text(encoding="ascii"))
    assert report["passed"] is False
    assert report["environment"] == "hidden_cdb_host"
    md = out_md.read_text(encoding="ascii")
    assert "environment" in md and "hidden_cdb_host" in md
    assert "FORCED entry (disclosed)" in md
    assert "not_applicable_hidden" in md


def test_cli_rejects_unbacked_samples_without_test_reader(fixture: Path) -> None:
    samples_path = fixture / "samples.json"
    samples_path.parent.mkdir(parents=True, exist_ok=True)
    samples_path.write_text(json.dumps(make_samples("map-pan"), indent=2), encoding="ascii")
    out_json = fixture / "report.json"
    result = subprocess.run(
        [sys.executable, "-B", str(SCRIPT), str(samples_path), "--write-json", str(out_json), "--require-pass"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    assert result.returncode == 1, result.stdout + result.stderr
    report = json.loads(out_json.read_text(encoding="ascii"))
    assert report["passed"] is False
    assert any("retained" in failure for failure in report["failures"])


def test_cli_main_with_fixed_artifacts_writes_passing_outputs(fixture: Path) -> None:
    # Only the fixed reader boundary is mocked by the enclosing fixture scope.
    # Execute the actual CLI parser, assembler and serializers in this process.
    fixture.mkdir(parents=True, exist_ok=True)
    samples_path, report_path, markdown_path = fixture / "samples.json", fixture / "report.json", fixture / "report.md"
    samples_path.write_text(json.dumps(make_samples("map-pan")), encoding="ascii")
    with patch.object(sys, "argv", [str(SCRIPT), str(samples_path), "--write-json", str(report_path),
                                   "--write-markdown", str(markdown_path), "--require-pass"]), redirect_stdout(StringIO()):
        assert assembler.main() == 0
    report = json.loads(report_path.read_text(encoding="ascii"))
    assert report["passed"], report["failures"]
    assert all(check["passed"] for check in report["retained_artifact_checks"].values())
    assert "not_applicable_hidden" in markdown_path.read_text(encoding="ascii")


# --- static guards: probe -----------------------------------------------------

def test_artifact_inventory_cannot_be_missing_or_coerced() -> None:
    for value in (None, True, False, -1, 1.5, "5000000", "", [], {}, float("nan")):
        samples = make_samples("map-idle")
        samples["artifact_bytes"] = value
        report = assembler.assemble_report(samples)
        assert not report["passed"], value
        assert any("artifact_bytes must be" in error for error in report["failures"]), report["failures"]
    samples = make_samples("map-idle")
    del samples["artifact_bytes"]
    assert not assembler.assemble_report(samples)["passed"]


def test_probe_placeholder_contract_and_safety() -> None:
    text = PROBE.read_text(encoding="ascii")
    # Placeholder contract: the runner substitutes complete CDB literals.
    for placeholder in ("__SOAK_DURATION_TICKS__", "__SOAK_PAN__", "__PAN_INTERVAL_TICKS__"):
        assert placeholder in text, f"probe is missing placeholder {placeholder}"
    # No standalone g command (the composition guard would reject it).
    assert not re.search(r"(?m)^\s*g\s*$", text), "probe must not contain a standalone g command"
    # Echo text must be semicolon-free.
    for line in text.splitlines():
        if line.startswith(".echo"):
            assert ";" not in line, f"echo line contains a semicolon: {line}"
    # Scratch stays inside the proven DOS-stub window 00400040-0040006c
    # (e_lfanew is 0x70; the PE header starts at 00400070).
    for match in re.finditer(r"\bed (00[0-9a-fA-F]{6})\b", text):
        address = int(match.group(1), 16)
        if 0x00400000 <= address < 0x00500000:
            assert 0x00400040 <= address <= 0x0040006C, f"scratch write outside proven stub window: {match.group(1)}"
    # Only the base-dump latch registers t7/t13 are touched; all 20 $t registers
    # are base-template-owned and $t20 does not exist.
    for match in re.finditer(r"r @\$t(\d+)\s*=", text):
        assert match.group(1) in {"7", "13"}, f"probe writes base-owned register $t{match.group(1)}"
    # No next-player advances anywhere (day-wrap hang avoidance).
    assert "0040AA60" not in text, "probe must not call the next-player routine"
    # The forced-pan writes target the documented scroll fields.
    assert "0n140008" in text and "0n140012" in text
    # Soak marker rows the runner and assembler depend on.
    for marker in ("SOAK_ROUTE_START", "SOAK_SURFDUMP_READY", "SOAK_HEARTBEAT", "SOAK_PAN_PLAN", "SOAK_PAN_SET", "SOAK_ROUTE_END"):
        assert marker in text, f"probe is missing marker {marker}"


def test_runner_static_contract() -> None:
    text = RUNNER.read_text(encoding="ascii")
    # Placeholder substitution for the soak contract happens only in the
    # canonical composer, which the runner calls instead of composing inline.
    composer = (ROOT / "tools" / "hidden_soak_probe_composition.py").read_text(encoding="ascii")
    assert "$compositionRaw = & $pythonExe -B $composer --probe-template" in text
    for placeholder in ("__SOAK_DURATION_TICKS__", "__SOAK_PAN__", "__PAN_INTERVAL_TICKS__"):
        assert placeholder in composer, f"composer never substitutes {placeholder}"
        assert placeholder not in text, f"runner still composes {placeholder} inline"
    # Honesty sentinel is hardcoded, never computed.
    assert "input_responsiveness = 'not_applicable_hidden'" in text
    # Hidden desktop only; no visible fallback switch exists.
    assert "CreateDesktop" in text
    assert "AllowVisibleDesktop" not in text
    # Fail-closed markers.
    for marker in ("AV_SURFDUMP", "SOAK_ROUTE_END", "SURFDUMP_INVALID", "SURFDUMP_APP_REQUEST_QUIT"):
        assert marker in text, f"runner does not watch for {marker}"
    # Environment stamp flows into the samples payload.
    assert "hidden_cdb_host" in text
    # Real reads, not fabrication: the ReadProcessMemory path is present.
    assert "ReadProcessMemory" in text
    # Preserve every actual parsed plan row, including source/safe and bounds;
    # a summary count or saved validation boolean is not a receipt.
    assert "$samples = [ordered]@{" in text
    payload = text.split("$samples = [ordered]@{", 1)[1]
    assert "pan_plans = @($observations.PanPlans | ForEach-Object" in payload
    for field in ("source = $_.Source", "safe = $_.Safe", "line_number = $_.LineNumber",
                  "base_x = $_.BaseX", "base_y = $_.BaseY", "delta_x = $_.DeltaX",
                  "delta_y = $_.DeltaY", "max_x = $_.MaxX", "max_y = $_.MaxY"):
        assert field in payload, field


def test_probe_deadlines_and_observations_share_one_clock_sample() -> None:
    """The target clock keeps moving while a breakpoint command is evaluated."""
    lines = PROBE.read_text(encoding="ascii").splitlines()
    start = next(line for line in lines if line.startswith("bp 0040B0C3 "))
    redraw = next(line for line in lines if line.startswith("bp 00406FA1 "))
    assert start.count("poi(7ffe0320)") == 1
    assert "ed 00400054 poi(00400044)" in start
    assert "__SOAK_PAN__, poi(005202ec), poi(00400044)," in start
    assert redraw.count("poi(7ffe0320)") == 1
    assert ".if (poi(0040004c) == 2) { ed 0040004c poi(7ffe0320);" in redraw
    assert "ed 00400054 poi(0040004c)" in redraw
    assert "poi(0040004c)-poi(00400054)" in redraw
    # Heartbeat and the route deadline/end use that latch; a due pan stores it
    # as the step's scheduled tick and the handler reports that same sample.
    assert redraw.count("poi(0040004c)-poi(00400044)") == 3
    handler = next(line for line in lines if line.startswith("bp 00407D20 "))
    assert "poi(7ffe0320)" not in handler
    assert handler.count("poi(00400054)-poi(00400044)") == 2
    assert "0n140008 poi" not in redraw + handler and "ed poi(005202e4)" not in redraw + handler


def _run_tests() -> None:
    with tempfile.TemporaryDirectory(prefix="clash-hidden-soak-tests-") as temporary:
        fixture = Path(temporary)
        test_passing_map_idle()
        test_artifact_layout_rejects_missing_cross_run_and_ambiguous_paths()
        test_artifact_layout_case_and_slashes_are_lexical_only()
        test_passing_map_pan_discloses_forced_pan()
        test_map_pan_without_pan_events_fails()
        test_map_pan_single_hash_fails()
        test_map_idle_with_pan_events_fails()
        test_av_and_missing_markers_fail()
        test_exit_before_duration_fails()
        test_fabricated_input_metric_fails()
        test_sentinel_is_stamped_even_on_failure()
        test_missing_host_process_metrics_fail()
        test_render_thresholds_and_size_fail_closed()
        test_wrong_capture_mode_fails()
        test_elapsed_coverage_gap_fails()
        test_periodic_coverage_rejects_sparse_unordered_and_missing_samples()
        test_periodic_count_uses_the_same_bounded_jitter_as_each_gap()
        test_terminal_marker_identity_and_scroll_are_bound_to_the_route()
        test_every_process_sample_requires_live_numeric_telemetry()
        test_pan_events_require_positive_periodic_full_route_coverage()
        test_missing_or_forged_provenance_fails()
        test_reports_pass_shared_hidden_grader(fixture / "shared-grader")
        test_every_hidden_frame_requires_strict_metrics_and_surface_provenance(fixture / "strict-frames")
        test_pan_count_uses_the_same_bounded_jitter_as_each_gap(fixture / "pan-jitter")
        test_terminal_redraw_hits_must_advance_after_the_final_pan(fixture / "terminal-pan-hits")
        test_pan_coordinates_require_one_genuine_exact_four_phase_cycle(fixture / "pan-coordinate-cycle")
        test_live_pan_plan_receipts_are_retained_and_independently_regraded(fixture / "live-pan-plan")
        test_runner_structured_marker_parser(fixture / "parser")
        test_cli_writes_outputs_and_require_pass_fails_closed(fixture / "cli-fail")
        test_cli_rejects_unbacked_samples_without_test_reader(fixture / "cli-unbacked")
        test_cli_main_with_fixed_artifacts_writes_passing_outputs(fixture / "cli-main")
        test_probe_placeholder_contract_and_safety()
        test_artifact_inventory_cannot_be_missing_or_coerced()
        test_probe_deadlines_and_observations_share_one_clock_sample()
        test_runner_static_contract()


def run_tests() -> None:
    with fixture_artifact_reads():
        for field, value in (("frame_samples", True), ("process_samples", 3),
                             ("capture_errors", True), ("runner_failures", True),
                             ("duration_sec", float("inf")), ("duration_sec", "120")):
            report = assembler.assemble_report(make_samples(**{field: value}))
            assert not report["passed"], (field, value)
        samples = make_samples()
        samples["ready_marker"]["source"] = []
        assert not assembler.assemble_report(samples)["passed"]
        samples = make_samples()
        samples["process_samples"][0]["WorkingSet64"] = float("inf")
        assert not assembler.assemble_report(samples)["passed"]
        for inventory in ("frame_samples", "process_samples"):
            for timestamp in ("9999-12-31T23:59:59-23:59", "0001-01-01T00:00:00+23:59"):
                samples = make_samples()
                samples[inventory][0]["Timestamp"] = timestamp
                report = assembler.assemble_report(samples)
                assert not report["passed"], (inventory, timestamp)
                assert any("timestamp" in failure for failure in report["failures"])
        baseline = make_samples()
        for field in ("av_observed", "surface_invalid_observed", "app_request_quit_observed"):
            for value in ("true", 0, [], None):
                samples = copy.deepcopy(baseline)
                samples[field] = value
                report = assembler.assemble_report(samples)
                assert not report["passed"], (field, value)
                assert report[field] == value and type(report[field]) is type(value)
                assert any(field in failure for failure in report["failures"])
            samples = copy.deepcopy(baseline)
            del samples[field]
            report = assembler.assemble_report(samples)
            assert not report["passed"], field
            assert any(field in failure for failure in report["failures"])
        for field, value in (("WorkingSet64", 1 << 63), ("PrivateMemorySize64", 1 << 63),
                             ("HandleCount", 1 << 31), ("WorkingSet64", 10 ** 1000),
                             ("PrivateMemorySize64", 10 ** 1000), ("HandleCount", 10 ** 1000)):
            samples = copy.deepcopy(baseline)
            samples["process_samples"][2][field] = value
            report = assembler.assemble_report(samples)
            assert not report["passed"], field
            assert any(field in failure and "range" in failure for failure in report["failures"])
        for value in (True, None, [None], ["oops"], {}):
            samples = copy.deepcopy(baseline)
            samples["frame_samples"] = value
            report = assembler.assemble_report(samples)
            assert not report["passed"]
            assert "## Failures" in assembler.to_markdown(report)
            assert report["frame_samples"] == value
        _run_tests()


def main() -> int:
    run_tests()
    print("hidden soak report assembler tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
