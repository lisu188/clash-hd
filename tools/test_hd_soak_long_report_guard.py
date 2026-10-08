#!/usr/bin/env python3
"""Fixture tests for hd_soak_long_report_guard.py."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "hd_soak_long_report_guard.py"
sys.path.insert(0, str(ROOT / "tools"))

import hd_soak_long_report_guard as guard  # noqa: E402
import hd_soak_report as soak
import test_hd_soak_report as soak_fixtures
from test_hidden_soak_integration import hidden_report as assembled_hidden_report


SHA = "c" * 64
REQUIRED_CHECKS = [
    "executed",
    "source_status",
    "protected_stage",
    "tier_route",
    "patch_evidence",
    "promotion_boundary",
    "artifact_locations",
    "capture_integrity",
    "frame_inventory",
    "render_metrics",
    "frame_progression",
    "process_liveness",
    "process_growth",
    "input_responsiveness",
    "summary_consistency",
    "artifact_budget",
]


def write_json(path: Path, data: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="ascii")
    return path


def short_status(*, complete: bool) -> dict[str, Any]:
    return {
        "passed": True,
        "ladder_complete": complete,
        "current_step": None if complete else {"id": "short2_menu_idle"},
        "steps": [
            {"id": step_id, "passed": complete}
            for step_id in (
                "short2_menu_idle", "short2_map_idle", "short10_map_idle",
                "short10_map_pan", "short30_map_pan",
            )
        ],
    }


def write_short_status(path: Path, *, complete: bool) -> Path:
    payload = short_status(complete=complete)
    if complete:
        for row, canonical in zip(payload["steps"], guard.SHORT_LADDER_STEPS):
            fixture = path.parent / canonical["id"]
            fixture.mkdir(parents=True, exist_ok=True)
            source = soak_fixtures.passing_report(fixture)
            source.update(tier=canonical["tier"], route=canonical["route"],
                          duration_sec=canonical["duration_sec"],
                          map_route_reached=canonical["route"] in ("map-idle", "map-pan"),
                          frame_progress_expected=canonical["route"] == "map-pan")
            end = datetime(2026, 6, 16, 12, tzinfo=timezone.utc) + timedelta(seconds=canonical["duration_sec"])
            for samples in (source["frame_samples"], source["process_samples"]):
                samples[-1]["Timestamp"] = end.isoformat()
            source_path = fixture / "report.json"
            source["report_json"] = str(source_path)
            write_json(source_path, source)
            evaluation = soak.evaluate_report_for_environment(source)
            assert evaluation["overall"], evaluation["failures"]
            guard_path = write_json(fixture / "guard.json", evaluation)
            row.update(canonical, paths={"report_json": str(source_path), "guard_json": str(guard_path)})
    return write_json(path, payload)


def long_report(route: str, *, duration_sec: int = guard.MIN_DURATION_SEC, overall: bool = True) -> dict[str, Any]:
    checks = {name: {"passed": True, "summary": {}, "failures": []} for name in REQUIRED_CHECKS}
    checks["patch_evidence"]["summary"] = {"candidate_sha256": SHA}
    return {
        "overall": overall,
        "stage": guard.PROTECTED_STABLE_STAGE,
        "tier": "custom",
        "route": route,
        "duration_sec": duration_sec,
        "candidate_sha256": SHA,
        "checks": checks,
        "failures": [] if overall else ["fixture failure"],
    }


def write_proof(tmp: Path, report_paths: list[Path]) -> Path:
    return write_json(tmp / "long-proof.json", {"report_guards": [str(path) for path in report_paths]})


def hidden_long_report(
    fixture: Path, route: str, *, duration_sec: int = guard.MIN_DURATION_SEC, sha: str = SHA
) -> dict[str, Any]:
    """Create real tiny source/patch JSON and its actual environment guard."""
    source = assembled_hidden_report(fixture, route, duration_sec, 30)
    source["candidate_sha256"] = sha
    patch_path = Path(source["patch_stage_report"])
    patch = json.loads(patch_path.read_text(encoding="utf-8"))
    patch["exe_sha256"] = sha
    write_json(patch_path, patch)
    source_path = fixture / "source-report.json"
    source["report_json"] = str(source_path)
    write_json(source_path, source)
    evaluated = soak.evaluate_report_for_environment(source)
    assert evaluated["overall"], evaluated["failures"]
    assert evaluated["source_report_sha256"]
    return evaluated


def test_incomplete_or_forged_short_ladder_cannot_unlock_long_runs() -> None:
    for steps in ([], short_status(complete=True)["steps"][:1],
                  list(reversed(short_status(complete=True)["steps"])),
                  [short_status(complete=True)["steps"][0]] * 5):
        status = short_status(complete=True)
        status["steps"] = steps
        assert not guard.short_ladder_complete(status), status


def test_hidden_long_provenance_cannot_be_dropped_or_failed(fixture: Path) -> None:
    for name in (
        "schema", "environment", "wrapper_provenance", "marker_provenance",
        "cleanup_provenance", "forced_entry_disclosure", "elapsed_coverage",
    ):
        for missing in (True, False):
            report = hidden_long_report(fixture, "map-pan")
            if missing:
                del report["checks"][name]
            else:
                report["checks"][name]["passed"] = False
            valid, failures, _ = guard.validate_long_report(report)
            assert not valid
            assert any(name in failure for failure in failures), failures


def test_hidden_long_disclosures_cannot_be_faked_or_omitted(fixture: Path) -> None:
    for field, value in (
        ("input_responsiveness", True), ("input_responsiveness", None),
        ("entry_mechanism", ""), ("pan_mechanism", None),
        ("evidence_class", "host_visible_runtime_soak"),
    ):
        report = hidden_long_report(fixture, "map-pan")
        report[field] = value
        valid, failures, _ = guard.validate_long_report(report)
        assert not valid
        assert any(field in failure for failure in failures), failures
    valid, failures, summary = guard.validate_long_report(hidden_long_report(fixture, "map-pan"))
    assert valid, failures
    assert summary["input_responsiveness"] == "not_applicable_hidden"
    assert summary["entry_mechanism"] and summary["pan_mechanism"]


def test_unsupported_or_mislabeled_long_environment_fails() -> None:
    for environment, evidence_class in (
        ("unknown", None), ("guest_win98_qemu", "approved_guest_win98_soak"),
        (None, "approved_hidden_cdb_host_soak"),
    ):
        report = long_report("map-idle")
        report.update(environment=environment, evidence_class=evidence_class)
        valid, failures, _ = guard.validate_long_report(report)
        assert not valid, failures


def test_inconsistent_status_or_invalid_duration_fails_closed() -> None:
    report = long_report("map-idle", overall=False)
    report["passed"] = True
    valid, failures, _ = guard.validate_long_report(report)
    assert not valid
    assert any("conflicting" in failure for failure in failures)
    for duration in ("7200", True, None, float("nan"), float("inf"), 1 << 4096):
        report = long_report("map-idle")
        report["duration_sec"] = duration
        valid, failures, _ = guard.validate_long_report(report)
        assert not valid, failures
    assert not guard.finite_number(1 << 4096)


def test_embedded_nul_source_references_fail_closed(fixture: Path) -> None:
    for report in (long_report("map-idle"), hidden_long_report(fixture, "map-idle")):
        report["source_report"] = "\x00"
        valid, failures, _ = guard.validate_long_report(report)
        assert not valid
        assert any("ValueError" in failure for failure in failures), failures
    payload, failures = guard.load_json(Path("\x00"))
    assert payload is None and any("ValueError" in failure for failure in failures)


def test_hidden_check_summaries_cannot_contradict_passing_flags(fixture: Path) -> None:
    mutations = (
        ("environment", "environment", "guest_win98_qemu"),
        ("forced_entry_disclosure", "route", "map-idle"),
        ("input_responsiveness", "input_responsiveness", True),
        ("elapsed_coverage", "duration_sec", 120),
        ("elapsed_coverage", "frame_elapsed_sec", 120),
        ("elapsed_coverage", "required_elapsed_sec", 118),
        ("wrapper_provenance", "present_enabled", 1),
        ("wrapper_provenance", "sha256", "not-a-digest"),
        ("cleanup_provenance", "game_stopped", False),
        ("schema", "schema", "host_visible_report"),
    )
    for check, field, value in mutations:
        report = hidden_long_report(fixture, "map-pan")
        report["checks"][check]["summary"][field] = value
        valid, failures, _ = guard.validate_long_report(report)
        assert not valid, (check, field, value)
        assert any(check in failure for failure in failures), failures
    report = hidden_long_report(fixture, "map-pan")
    report["checks"]["marker_provenance"]["summary"]["route_end_marker"]["route_ticks"] = 7680
    assert not guard.validate_long_report(report)[0]


def test_exact_mechanisms_candidate_binding_and_explicit_environment(fixture: Path) -> None:
    for field in ("entry_mechanism", "pan_mechanism"):
        report = hidden_long_report(fixture, "map-pan")
        report[field] = "invented"
        assert not guard.validate_long_report(report)[0]
    for value in (None, "", [], {}, 0):
        report = long_report("map-idle")
        report["environment"] = value
        assert not guard.validate_long_report(report)[0], value
    report = hidden_long_report(fixture, "map-pan")
    report["candidate_sha256"] = "e" * 64
    assert not guard.validate_long_report(report)[0]
    report = hidden_long_report(fixture, "map-pan")
    report["checks"]["wrapper_provenance"]["failures"] = ["retained error"]
    assert not guard.validate_long_report(report)[0]


def test_saved_complete_ladder_requires_fresh_exact_sources(fixture: Path) -> None:
    assert not guard.short_ladder_complete(short_status(complete=True))
    path = write_short_status(fixture / "short.json", complete=True)
    status = json.loads(path.read_text(encoding="ascii"))
    assert guard.short_ladder_complete(status)
    source = json.loads(Path(status["steps"][0]["paths"]["report_json"]).read_text(encoding="ascii"))
    Path(source["patch_stage_report"]).unlink()
    assert not guard.short_ladder_complete(status)


def test_saved_ladder_malformed_sources_and_paths_fail_closed(fixture: Path) -> None:
    for mutation in ("invalid_json", "invalid_encoding", "nul_path", "directory_path", "list_source"):
        path = write_short_status(fixture / mutation / "short.json", complete=True)
        status = json.loads(path.read_text(encoding="utf-8"))
        source_path = Path(status["steps"][0]["paths"]["report_json"])
        if mutation in ("invalid_json", "invalid_encoding", "list_source"):
            raw = {"invalid_json": b"{", "invalid_encoding": b"\xff", "list_source": b"[]"}[mutation]
            source_path.write_bytes(raw)
            assert not guard.short_ladder_complete(status), mutation
            assert source_path.read_bytes() == raw
        else:
            status["steps"][0]["paths"]["report_json"] = "\x00" if mutation == "nul_path" else str(source_path.parent)
            assert not guard.short_ladder_complete(status), mutation


def test_hidden_long_regrades_exact_source_and_preserves_saved_receipts(fixture: Path) -> None:
    for mutation in ("missing_hash", "wrong_hash", "missing_source", "raw_byte_drift", "source_drift",
                     "invalid_json", "invalid_encoding", "missing_patch", "patch_byte_drift", "patch_drift"):
        report = hidden_long_report(fixture / mutation, "map-idle")
        source_path = Path(report["source_report"])
        source = json.loads(source_path.read_text(encoding="utf-8"))
        patch_path = Path(source["patch_stage_report"])
        if mutation == "missing_hash":
            report.pop("source_report_sha256")
        elif mutation == "wrong_hash":
            report["source_report_sha256"] = "0" * 64
        elif mutation == "missing_source":
            source_path.unlink()
        elif mutation == "raw_byte_drift":
            source_path.write_bytes(source_path.read_bytes() + b"\n")
        elif mutation == "source_drift":
            source["process_samples"][1]["HasExited"] = True
            write_json(source_path, source)
        elif mutation == "invalid_json":
            source_path.write_bytes(b"{")
        elif mutation == "invalid_encoding":
            source_path.write_bytes(b"\xff")
        elif mutation == "missing_patch":
            patch_path.unlink()
        elif mutation == "patch_byte_drift":
            patch_path.write_bytes(patch_path.read_bytes() + b"\n")
        else:
            payload = json.loads(patch_path.read_text(encoding="utf-8"))
            payload["exe_sha256"] = "0" * 64
            write_json(patch_path, payload)
        original_guard = json.dumps(report, sort_keys=True)
        valid, failures, _ = guard.validate_long_report(report)
        assert not valid, mutation
        assert any("source_report" in failure or "patch_stage_report" in failure for failure in failures), failures
        assert json.dumps(report, sort_keys=True) == original_guard


def test_hidden_long_source_identity_and_checks_cannot_be_substituted(fixture: Path) -> None:
    for mutation in ("identity", "check", "foreign_source"):
        report = hidden_long_report(fixture / mutation, "map-idle")
        if mutation == "identity":
            report["candidate_sha256"] = "e" * 64
        elif mutation == "check":
            report["checks"]["frame_inventory"]["summary"]["frame_sample_count"] += 1
        else:
            foreign = hidden_long_report(fixture / "foreign", "map-pan")
            report["source_report"] = foreign["source_report"]
            report["source_report_sha256"] = foreign["source_report_sha256"]
        assert not guard.validate_long_report(report)[0], mutation


def test_hidden_long_requires_thirty_second_samples_and_complete_end_ticks(fixture: Path) -> None:
    for field, value in (("tick_delta", 10), ("hits", 0), ("player", 1)):
        report = hidden_long_report(fixture / field, "map-idle")
        report["checks"]["marker_provenance"]["summary"]["route_end_marker"][field] = value
        valid, failures, _ = guard.validate_long_report(report)
        assert not valid
        assert any("terminal" in failure or "checks" in failure for failure in failures), failures
    source = assembled_hidden_report(fixture / "noncanonical-sampling", "map-idle", 7200, 30)
    source.update(sample_interval_sec=7200, required_elapsed_sec=0)
    source["elapsed_coverage"]["required_sec"] = 0
    source["report_json"] = str(fixture / "noncanonical-sampling" / "source-report.json")
    write_json(Path(source["report_json"]), source)
    report = soak.evaluate_report_for_environment(source)
    assert report["overall"], report["failures"]
    valid, failures, _ = guard.validate_long_report(report)
    assert not valid
    assert any("canonical sample_interval_sec=30" in failure for failure in failures), failures


def test_hidden_long_requires_ten_second_pan_intervals(fixture: Path) -> None:
    source = assembled_hidden_report(fixture, "map-pan", 7200, 30)
    source["pan_interval_sec"] = source["pan_mechanism_detail"]["pan_interval_sec"] = 12
    source["pan_events"] = [
        {"phase": index % 4, "x": 4 + int(index % 4 in (1, 2)),
         "y": 6 + int(index % 4 in (2, 3)), "hits": (index + 1) * 768,
         "tick_delta": (index + 1) * 768}
        for index in range((7200 * 64 - 1) // 768)
    ]
    source["pan_event_count"] = source["pan_mechanism_detail"]["pan_event_count"] = len(source["pan_events"])
    source["route_end_marker"].update(scroll_x=source["pan_events"][-1]["x"], scroll_y=source["pan_events"][-1]["y"])
    source["report_json"] = str(fixture / "source-report.json")
    write_json(Path(source["report_json"]), source)
    report = soak.evaluate_report_for_environment(source)
    assert report["overall"], report["failures"]
    valid, failures, _ = guard.validate_long_report(report)
    assert not valid
    assert any("canonical pan_interval_sec=10" in failure for failure in failures), failures


def test_visible_labels_cannot_erase_explicit_foreign_evidence(fixture: Path) -> None:
    for strip_summaries in (False, True):
        report = hidden_long_report(fixture / str(strip_summaries), "map-idle")
        report.update(environment="host_visible", evidence_class=soak.HOST_EVIDENCE_CLASS)
        if strip_summaries:
            for field in ("expected_environment", "expected_evidence_class", "input_responsiveness"):
                report.pop(field, None)
            report["checks"].pop("environment")
            report["checks"].pop("schema")
            report["checks"]["input_responsiveness"]["summary"] = {}
        valid, failures, _ = guard.validate_long_report(report)
        assert not valid
        assert any("foreign proof-class" in failure for failure in failures), failures
    for field in ("expected_evidence_class", "environment_summary_class", "environment_summary_expected_class"):
        for malformed in ([], {}, ["hidden_cdb_host"]):
            report = long_report("map-idle")
            if field == "expected_evidence_class":
                report[field] = malformed
            else:
                key = "evidence_class" if field == "environment_summary_class" else "expected_evidence_class"
                report["checks"]["environment"] = {"passed": True, "summary": {key: malformed}, "failures": []}
            assert not guard.validate_long_report(report)[0], (field, malformed)
    legacy = long_report("map-idle")
    assert guard.validate_long_report(legacy)[0]
    legacy.update(environment="host_visible", evidence_class=soak.HOST_EVIDENCE_CLASS,
                  expected_environment="host_visible", expected_evidence_class=soak.HOST_EVIDENCE_CLASS)
    assert guard.validate_long_report(legacy)[0]


def test_incomplete_ladder_missing_proof_is_locked(fixture: Path) -> None:
    short = write_short_status(fixture / "short.json", complete=False)
    report = guard.build_report(short_step_status_json=short, proof_json=fixture / "missing-proof.json")
    assert report["overall"] is False
    assert report["short_ladder"]["ladder_complete"] is False
    assert report["status"] == "locked_short_ladder_incomplete"
    assert any("short ladder is not complete" in failure for failure in report["failures"])


def test_complete_ladder_missing_proof_stays_blocked(fixture: Path) -> None:
    short = write_short_status(fixture / "short.json", complete=True)
    report = guard.build_report(short_step_status_json=short, proof_json=fixture / "missing-proof.json")
    assert report["overall"] is False
    assert report["short_ladder"]["ladder_complete"] is True
    assert report["status"] == "blocked_missing_long_proof"
    assert report["counts"]["passing_routes"] == 0
    assert all(route not in report["route_records"] for route in ("map-idle", "map-pan"))


def test_valid_future_two_route_proof_passes(fixture: Path) -> None:
    short = write_short_status(fixture / "short.json", complete=True)
    map_idle = write_json(fixture / "map-idle.json", long_report("map-idle"))
    map_pan = write_json(fixture / "map-pan.json", long_report("map-pan"))
    proof = write_proof(fixture, [map_idle, map_pan])
    report = guard.build_report(short_step_status_json=short, proof_json=proof)
    assert report["overall"] is True, report["failures"]
    assert report["duration_sec"] == guard.MIN_DURATION_SEC
    assert report["counts"]["passing_routes"] == 2
    assert set(report["route_records"]) == {"map-idle", "map-pan"}


def test_nested_patch_evidence_candidate_sha_is_accepted(fixture: Path) -> None:
    short = write_short_status(fixture / "short.json", complete=True)
    map_idle_payload = long_report("map-idle")
    map_pan_payload = long_report("map-pan")
    map_idle_payload.pop("candidate_sha256")
    map_pan_payload.pop("candidate_sha256")
    map_idle = write_json(fixture / "map-idle.json", map_idle_payload)
    map_pan = write_json(fixture / "map-pan.json", map_pan_payload)
    proof = write_proof(fixture, [map_idle, map_pan])
    report = guard.build_report(short_step_status_json=short, proof_json=proof)
    assert report["overall"] is True, report["failures"]
    assert report["route_records"]["map-idle"]["candidate_sha256"] == SHA


def test_hidden_two_route_proof_passes_and_labels_environment(fixture: Path) -> None:
    short = write_short_status(fixture / "short.json", complete=True)
    map_idle = write_json(fixture / "map-idle.json", hidden_long_report(fixture / "idle-source", "map-idle"))
    map_pan = write_json(fixture / "map-pan.json", hidden_long_report(fixture / "pan-source", "map-pan"))
    proof = write_proof(fixture, [map_idle, map_pan])
    report = guard.build_report(short_step_status_json=short, proof_json=proof)
    assert report["overall"] is True, report["failures"]
    assert report["duration_sec"] == guard.MIN_DURATION_SEC
    assert report["counts"]["passing_routes"] == 2
    assert report["route_records"]["map-idle"]["environment"] == "hidden_cdb_host"
    assert report["route_records"]["map-pan"]["environment"] == "hidden_cdb_host"
    markdown = guard.to_markdown(report)
    assert "environment=`hidden_cdb_host`" in markdown
    assert "not_applicable_hidden" in markdown
    assert soak.HIDDEN_ENTRY_MECHANISM in markdown
    assert soak.HIDDEN_PAN_MECHANISM in markdown


def test_host_route_records_label_host_environment(fixture: Path) -> None:
    short = write_short_status(fixture / "short.json", complete=True)
    map_idle = write_json(fixture / "map-idle.json", long_report("map-idle"))
    map_pan = write_json(fixture / "map-pan.json", long_report("map-pan"))
    proof = write_proof(fixture, [map_idle, map_pan])
    report = guard.build_report(short_step_status_json=short, proof_json=proof)
    assert report["overall"] is True, report["failures"]
    assert report["route_records"]["map-idle"]["environment"] == "host_visible"
    markdown = guard.to_markdown(report)
    assert "environment=`host_visible`" in markdown


def test_hidden_mixed_candidate_sha_fails(fixture: Path) -> None:
    short = write_short_status(fixture / "short.json", complete=True)
    map_idle = write_json(fixture / "map-idle.json", hidden_long_report(fixture / "idle-source", "map-idle"))
    map_pan = write_json(fixture / "map-pan.json", hidden_long_report(fixture / "pan-source", "map-pan", sha="d" * 64))
    proof = write_proof(fixture, [map_idle, map_pan])
    report = guard.build_report(short_step_status_json=short, proof_json=proof)
    assert report["overall"] is False
    assert any("different candidate SHA-256s" in failure for failure in report["failures"])


def test_hidden_sub_duration_fails(fixture: Path) -> None:
    short = write_short_status(fixture / "short.json", complete=True)
    map_idle = write_json(fixture / "map-idle.json", hidden_long_report(fixture / "idle-source", "map-idle"))
    map_pan = write_json(fixture / "map-pan.json", hidden_long_report(fixture / "pan-source", "map-pan", duration_sec=3600))
    proof = write_proof(fixture, [map_idle, map_pan])
    report = guard.build_report(short_step_status_json=short, proof_json=proof)
    assert report["overall"] is False
    assert any("duration_sec 3600" in failure for failure in report["failures"])


def test_hidden_failed_required_check_fails(fixture: Path) -> None:
    short = write_short_status(fixture / "short.json", complete=True)
    map_idle = write_json(fixture / "map-idle.json", hidden_long_report(fixture / "idle-source", "map-idle"))
    bad = hidden_long_report(fixture / "pan-source", "map-pan")
    bad["checks"]["input_responsiveness"]["passed"] = False
    map_pan = write_json(fixture / "map-pan.json", bad)
    proof = write_proof(fixture, [map_idle, map_pan])
    report = guard.build_report(short_step_status_json=short, proof_json=proof)
    assert report["overall"] is False
    assert any("input_responsiveness" in failure for failure in report["failures"])


def test_mixed_candidate_sha_fails(fixture: Path) -> None:
    short = write_short_status(fixture / "short.json", complete=True)
    map_idle = write_json(fixture / "map-idle.json", long_report("map-idle"))
    map_pan_payload = long_report("map-pan")
    map_pan_payload["candidate_sha256"] = "d" * 64
    map_pan_payload["checks"]["patch_evidence"]["summary"]["candidate_sha256"] = "d" * 64
    map_pan = write_json(fixture / "map-pan.json", map_pan_payload)
    proof = write_proof(fixture, [map_idle, map_pan])
    report = guard.build_report(short_step_status_json=short, proof_json=proof)
    assert report["overall"] is False
    assert any("different candidate SHA-256s" in failure for failure in report["failures"])


def test_missing_representative_route_fails(fixture: Path) -> None:
    short = write_short_status(fixture / "short.json", complete=True)
    map_idle = write_json(fixture / "map-idle.json", long_report("map-idle"))
    proof = write_proof(fixture, [map_idle])
    report = guard.build_report(short_step_status_json=short, proof_json=proof)
    assert report["overall"] is False
    assert any("missing passing 2h+ representative route: map-pan" in failure for failure in report["failures"])


def test_short_duration_and_failed_check_fail(fixture: Path) -> None:
    short = write_short_status(fixture / "short.json", complete=True)
    bad = long_report("map-pan", duration_sec=3600)
    bad["checks"]["process_growth"]["passed"] = False
    map_pan = write_json(fixture / "map-pan.json", bad)
    proof = write_proof(fixture, [map_pan])
    report = guard.build_report(short_step_status_json=short, proof_json=proof)
    assert report["overall"] is False
    assert any("duration_sec 3600" in failure for failure in report["failures"])
    assert any("process_growth" in failure for failure in report["failures"])


def test_unprotected_stage_fails(fixture: Path) -> None:
    short = write_short_status(fixture / "short.json", complete=True)
    bad = long_report("map-idle")
    bad["stage"] = "validation-only-stage"
    map_idle = write_json(fixture / "map-idle.json", bad)
    proof = write_proof(fixture, [map_idle])
    report = guard.build_report(short_step_status_json=short, proof_json=proof)
    assert report["overall"] is False
    assert any("protected stable stage" in failure for failure in report["failures"])


def test_cli_writes_outputs_and_require_pass_fails_closed(fixture: Path) -> None:
    short = write_short_status(fixture / "short.json", complete=False)
    missing = fixture / "missing-proof.json"
    out_json = fixture / "out" / "long.json"
    out_md = fixture / "out" / "long.md"
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--short-step-status-json",
            str(short),
            "--proof-json",
            str(missing),
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
    assert json.loads(out_json.read_text(encoding="ascii"))["overall"] is False
    assert "HD Long Soak Report Guard" in out_md.read_text(encoding="ascii")


def run_tests() -> None:
    with tempfile.TemporaryDirectory(prefix="clash-long-soak-guard-") as directory:
        fixture = Path(directory)
        test_incomplete_or_forged_short_ladder_cannot_unlock_long_runs()
        test_hidden_long_provenance_cannot_be_dropped_or_failed(fixture / "provenance")
        test_hidden_long_disclosures_cannot_be_faked_or_omitted(fixture / "disclosures")
        test_unsupported_or_mislabeled_long_environment_fails()
        test_inconsistent_status_or_invalid_duration_fails_closed()
        test_embedded_nul_source_references_fail_closed(fixture / "nul-source")
        test_hidden_check_summaries_cannot_contradict_passing_flags(fixture / "summaries")
        test_exact_mechanisms_candidate_binding_and_explicit_environment(fixture / "identity")
        test_saved_complete_ladder_requires_fresh_exact_sources(fixture / "stale-short")
        test_saved_ladder_malformed_sources_and_paths_fail_closed(fixture / "malformed-short")
        test_hidden_long_regrades_exact_source_and_preserves_saved_receipts(fixture / "source-regrade")
        test_hidden_long_source_identity_and_checks_cannot_be_substituted(fixture / "source-identity")
        test_hidden_long_requires_thirty_second_samples_and_complete_end_ticks(fixture / "canonical-coverage")
        test_hidden_long_requires_ten_second_pan_intervals(fixture / "canonical-pan")
        test_visible_labels_cannot_erase_explicit_foreign_evidence(fixture / "foreign-class")
        test_incomplete_ladder_missing_proof_is_locked(fixture / "incomplete-missing")
        test_complete_ladder_missing_proof_stays_blocked(fixture / "complete-missing")
        test_valid_future_two_route_proof_passes(fixture / "valid")
        test_nested_patch_evidence_candidate_sha_is_accepted(fixture / "nested-sha")
        test_hidden_two_route_proof_passes_and_labels_environment(fixture / "hidden-valid")
        test_host_route_records_label_host_environment(fixture / "host-labeled")
        test_hidden_mixed_candidate_sha_fails(fixture / "hidden-mixed-sha")
        test_hidden_sub_duration_fails(fixture / "hidden-short-duration")
        test_hidden_failed_required_check_fails(fixture / "hidden-bad-check")
        test_mixed_candidate_sha_fails(fixture / "mixed-sha")
        test_missing_representative_route_fails(fixture / "missing-route")
        test_short_duration_and_failed_check_fail(fixture / "bad-check")
        test_unprotected_stage_fails(fixture / "bad-stage")
        test_cli_writes_outputs_and_require_pass_fails_closed(fixture / "cli")


def main() -> int:
    run_tests()
    print("hd soak long report guard tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
