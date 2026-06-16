#!/usr/bin/env python3
"""Fixture tests for hd_soak_long_report_guard.py."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
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
        "steps": [{"id": "short2_menu_idle", "passed": True if complete else False}],
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


def test_current_missing_proof_is_locked() -> None:
    report = guard.build_report()
    assert report["overall"] is False
    assert report["short_ladder"]["ladder_complete"] is False
    assert report["status"] == "locked_short_ladder_incomplete"
    assert any("short ladder is not complete" in failure for failure in report["failures"])


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
    fixture = ROOT / ".codex-loop" / "tmp-tests" / "hd-soak-long-report-guard-fixture"
    shutil.rmtree(fixture, ignore_errors=True)
    fixture.mkdir(parents=True)
    try:
        test_current_missing_proof_is_locked()
        test_valid_future_two_route_proof_passes(fixture / "valid")
        test_nested_patch_evidence_candidate_sha_is_accepted(fixture / "nested-sha")
        test_mixed_candidate_sha_fails(fixture / "mixed-sha")
        test_missing_representative_route_fails(fixture / "missing-route")
        test_short_duration_and_failed_check_fail(fixture / "bad-check")
        test_unprotected_stage_fails(fixture / "bad-stage")
        test_cli_writes_outputs_and_require_pass_fails_closed(fixture / "cli")
    finally:
        shutil.rmtree(fixture, ignore_errors=True)


def main() -> int:
    run_tests()
    print("hd soak long report guard tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
