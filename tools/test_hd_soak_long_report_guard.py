#!/usr/bin/env python3
"""Fixture tests for hd_soak_long_report_guard.py."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "hd_soak_long_report_guard.py"
sys.path.insert(0, str(ROOT / "tools"))

import hd_soak_long_report_guard as guard  # noqa: E402


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
    route: str, *, duration_sec: int = guard.MIN_DURATION_SEC, sha: str = SHA
) -> dict[str, Any]:
    """A hidden-host guard with its additional provenance and input disclosure."""
    report = long_report(route, duration_sec=duration_sec)
    report["environment"] = "hidden_cdb_host"
    report["evidence_class"] = "approved_hidden_cdb_host_soak"
    report["candidate_sha256"] = sha
    report["checks"]["patch_evidence"]["summary"]["candidate_sha256"] = sha
    report["input_responsiveness"] = "not_applicable_hidden"
    report["entry_mechanism"] = "CDB breakpoint-forced saved-map entry"
    report["pan_mechanism"] = "CDB forced scroll writes" if route == "map-pan" else None
    for name in (
        "schema", "environment", "wrapper_provenance", "marker_provenance",
        "cleanup_provenance", "forced_entry_disclosure", "elapsed_coverage",
    ):
        report["checks"][name] = {"passed": True, "summary": {}, "failures": []}
    return report


def test_incomplete_or_forged_short_ladder_cannot_unlock_long_runs() -> None:
    for steps in ([], short_status(complete=True)["steps"][:1],
                  list(reversed(short_status(complete=True)["steps"])),
                  [short_status(complete=True)["steps"][0]] * 5):
        status = short_status(complete=True)
        status["steps"] = steps
        assert not guard.short_ladder_complete(status), status


def test_hidden_long_provenance_cannot_be_dropped_or_failed() -> None:
    for name in (
        "schema", "environment", "wrapper_provenance", "marker_provenance",
        "cleanup_provenance", "forced_entry_disclosure", "elapsed_coverage",
    ):
        for missing in (True, False):
            report = hidden_long_report("map-pan")
            if missing:
                del report["checks"][name]
            else:
                report["checks"][name]["passed"] = False
            valid, failures, _ = guard.validate_long_report(report)
            assert not valid
            assert any(name in failure for failure in failures), failures


def test_hidden_long_disclosures_cannot_be_faked_or_omitted() -> None:
    for field, value in (
        ("input_responsiveness", True), ("input_responsiveness", None),
        ("entry_mechanism", ""), ("pan_mechanism", None),
        ("evidence_class", "host_visible_runtime_soak"),
    ):
        report = hidden_long_report("map-pan")
        report[field] = value
        valid, failures, _ = guard.validate_long_report(report)
        assert not valid
        assert any(field in failure for failure in failures), failures
    valid, failures, summary = guard.validate_long_report(hidden_long_report("map-pan"))
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
    for duration in ("7200", True, None, float("nan"), float("inf")):
        report = long_report("map-idle")
        report["duration_sec"] = duration
        valid, failures, _ = guard.validate_long_report(report)
        assert not valid, failures


def test_incomplete_ladder_missing_proof_is_locked(fixture: Path) -> None:
    short = write_json(fixture / "short.json", short_status(complete=False))
    report = guard.build_report(short_step_status_json=short, proof_json=fixture / "missing-proof.json")
    assert report["overall"] is False
    assert report["short_ladder"]["ladder_complete"] is False
    assert report["status"] == "locked_short_ladder_incomplete"
    assert any("short ladder is not complete" in failure for failure in report["failures"])


def test_complete_ladder_missing_proof_stays_blocked(fixture: Path) -> None:
    short = write_json(fixture / "short.json", short_status(complete=True))
    report = guard.build_report(short_step_status_json=short, proof_json=fixture / "missing-proof.json")
    assert report["overall"] is False
    assert report["short_ladder"]["ladder_complete"] is True
    assert report["status"] == "blocked_missing_long_proof"
    assert report["counts"]["passing_routes"] == 0
    assert all(route not in report["route_records"] for route in ("map-idle", "map-pan"))


def test_valid_future_two_route_proof_passes(fixture: Path) -> None:
    short = write_json(fixture / "short.json", short_status(complete=True))
    map_idle = write_json(fixture / "map-idle.json", long_report("map-idle"))
    map_pan = write_json(fixture / "map-pan.json", long_report("map-pan"))
    proof = write_proof(fixture, [map_idle, map_pan])
    report = guard.build_report(short_step_status_json=short, proof_json=proof)
    assert report["overall"] is True, report["failures"]
    assert report["duration_sec"] == guard.MIN_DURATION_SEC
    assert report["counts"]["passing_routes"] == 2
    assert set(report["route_records"]) == {"map-idle", "map-pan"}


def test_nested_patch_evidence_candidate_sha_is_accepted(fixture: Path) -> None:
    short = write_json(fixture / "short.json", short_status(complete=True))
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
    short = write_json(fixture / "short.json", short_status(complete=True))
    map_idle = write_json(fixture / "map-idle.json", hidden_long_report("map-idle"))
    map_pan = write_json(fixture / "map-pan.json", hidden_long_report("map-pan"))
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
    assert "CDB breakpoint-forced saved-map entry" in markdown
    assert "CDB forced scroll writes" in markdown


def test_host_route_records_label_host_environment(fixture: Path) -> None:
    short = write_json(fixture / "short.json", short_status(complete=True))
    map_idle = write_json(fixture / "map-idle.json", long_report("map-idle"))
    map_pan = write_json(fixture / "map-pan.json", long_report("map-pan"))
    proof = write_proof(fixture, [map_idle, map_pan])
    report = guard.build_report(short_step_status_json=short, proof_json=proof)
    assert report["overall"] is True, report["failures"]
    assert report["route_records"]["map-idle"]["environment"] == "host_visible"
    markdown = guard.to_markdown(report)
    assert "environment=`host_visible`" in markdown


def test_hidden_mixed_candidate_sha_fails(fixture: Path) -> None:
    short = write_json(fixture / "short.json", short_status(complete=True))
    map_idle = write_json(fixture / "map-idle.json", hidden_long_report("map-idle"))
    map_pan = write_json(fixture / "map-pan.json", hidden_long_report("map-pan", sha="d" * 64))
    proof = write_proof(fixture, [map_idle, map_pan])
    report = guard.build_report(short_step_status_json=short, proof_json=proof)
    assert report["overall"] is False
    assert any("different candidate SHA-256s" in failure for failure in report["failures"])


def test_hidden_sub_duration_fails(fixture: Path) -> None:
    short = write_json(fixture / "short.json", short_status(complete=True))
    map_idle = write_json(fixture / "map-idle.json", hidden_long_report("map-idle"))
    map_pan = write_json(fixture / "map-pan.json", hidden_long_report("map-pan", duration_sec=3600))
    proof = write_proof(fixture, [map_idle, map_pan])
    report = guard.build_report(short_step_status_json=short, proof_json=proof)
    assert report["overall"] is False
    assert any("duration_sec 3600" in failure for failure in report["failures"])


def test_hidden_failed_required_check_fails(fixture: Path) -> None:
    short = write_json(fixture / "short.json", short_status(complete=True))
    map_idle = write_json(fixture / "map-idle.json", hidden_long_report("map-idle"))
    bad = hidden_long_report("map-pan")
    bad["checks"]["input_responsiveness"]["passed"] = False
    map_pan = write_json(fixture / "map-pan.json", bad)
    proof = write_proof(fixture, [map_idle, map_pan])
    report = guard.build_report(short_step_status_json=short, proof_json=proof)
    assert report["overall"] is False
    assert any("input_responsiveness" in failure for failure in report["failures"])


def test_mixed_candidate_sha_fails(fixture: Path) -> None:
    short = write_json(fixture / "short.json", short_status(complete=True))
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
    short = write_json(fixture / "short.json", short_status(complete=True))
    map_idle = write_json(fixture / "map-idle.json", long_report("map-idle"))
    proof = write_proof(fixture, [map_idle])
    report = guard.build_report(short_step_status_json=short, proof_json=proof)
    assert report["overall"] is False
    assert any("missing passing 2h+ representative route: map-pan" in failure for failure in report["failures"])


def test_short_duration_and_failed_check_fail(fixture: Path) -> None:
    short = write_json(fixture / "short.json", short_status(complete=True))
    bad = long_report("map-pan", duration_sec=3600)
    bad["checks"]["process_growth"]["passed"] = False
    map_pan = write_json(fixture / "map-pan.json", bad)
    proof = write_proof(fixture, [map_pan])
    report = guard.build_report(short_step_status_json=short, proof_json=proof)
    assert report["overall"] is False
    assert any("duration_sec 3600" in failure for failure in report["failures"])
    assert any("process_growth" in failure for failure in report["failures"])


def test_unprotected_stage_fails(fixture: Path) -> None:
    short = write_json(fixture / "short.json", short_status(complete=True))
    bad = long_report("map-idle")
    bad["stage"] = "validation-only-stage"
    map_idle = write_json(fixture / "map-idle.json", bad)
    proof = write_proof(fixture, [map_idle])
    report = guard.build_report(short_step_status_json=short, proof_json=proof)
    assert report["overall"] is False
    assert any("protected stable stage" in failure for failure in report["failures"])


def test_cli_writes_outputs_and_require_pass_fails_closed(fixture: Path) -> None:
    short = write_json(fixture / "short.json", short_status(complete=False))
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
        test_hidden_long_provenance_cannot_be_dropped_or_failed()
        test_hidden_long_disclosures_cannot_be_faked_or_omitted()
        test_unsupported_or_mislabeled_long_environment_fails()
        test_inconsistent_status_or_invalid_duration_fails_closed()
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
