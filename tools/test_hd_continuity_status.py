#!/usr/bin/env python3
"""Fixture tests for hd_continuity_status.py."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "hd_continuity_status.py"
sys.path.insert(0, str(ROOT / "tools"))

import hd_continuity_status as continuity  # noqa: E402


SHA = "a" * 64


def run_script(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def proof(**updates: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "proof_class": "approved_visible_runtime",
        "approved": True,
        "approval_record": "User explicitly approved continuity runtime evidence.",
        "stage": continuity.PROTECTED_STABLE_STAGE,
        "candidate_sha256": SHA,
        "safe_test_save": True,
        "isolated_workdir": True,
        "live_save_mutated": False,
        "state_desync_detected": False,
        "before_state_sha256": SHA,
        "after_state_sha256": "b" * 64,
        "duration_sec": 900,
        "route": "fixture-continuity-route",
        "start_marker": "fixture-start",
        "end_marker": "fixture-end",
        "route_markers": ["fixture-start", "fixture-middle", "fixture-end"],
        "before_observation": "Fixture records stable state before the continuity action.",
        "after_observation": "Fixture records stable state after the continuity action.",
        "summary": "Fixture continuity evidence is complete.",
        "evidence_refs": ["captures/current/fixture-continuity-summary.md"],
    }
    payload.update(updates)
    return payload


def write_manifest(path: Path, **proof_updates: object) -> Path:
    payload = {
        "proofs": {
            "save_load_roundtrip": proof(roundtrip_completed=True, duration_sec=120, **proof_updates),
            "turn_advancement": proof(turn_advanced=True, duration_sec=120, **proof_updates),
            "campaign_routes": proof(route_completed=True, palette_corruption_detected=False, **proof_updates),
        }
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="ascii")
    return path


def test_missing_proof_manifest_fails_closed() -> None:
    report = continuity.build_report(ROOT / ".codex-loop" / "tmp-tests" / "missing-continuity-proof.json")
    assert report["passed"] is False
    assert report["counts"] == {"total": 3, "passed": 0, "blocked": 3}
    assert all(check["status"] == "blocked_missing_proof" for check in report["checks"].values())


def test_valid_manifest_passes_all_checks(fixture: Path) -> None:
    manifest = write_manifest(fixture / "continuity-proof.json")
    report = continuity.build_report(manifest)
    assert report["passed"] is True, report["failures"]
    assert report["counts"]["passed"] == 3
    assert all(check["status"] == "pass" for check in report["checks"].values())


def test_mixed_candidate_sha_fails_all_lanes(fixture: Path) -> None:
    payload = {
        "proofs": {
            "save_load_roundtrip": proof(roundtrip_completed=True, duration_sec=120),
            "turn_advancement": proof(turn_advanced=True, duration_sec=120),
            "campaign_routes": proof(
                route_completed=True,
                palette_corruption_detected=False,
                candidate_sha256="c" * 64,
            ),
        }
    }
    fixture.mkdir(parents=True, exist_ok=True)
    manifest = fixture / "mixed-candidate.json"
    manifest.write_text(json.dumps(payload, indent=2) + "\n", encoding="ascii")
    report = continuity.build_report(manifest)
    assert report["passed"] is False
    assert report["counts"]["passed"] == 0
    assert all(check["status"] == "blocked_candidate_mismatch" for check in report["checks"].values())
    assert any("different candidate SHA-256s" in failure for failure in report["failures"])


def test_live_save_and_repo_binary_artifacts_fail(fixture: Path) -> None:
    manifest = write_manifest(
        fixture / "bad-artifacts.json",
        evidence_refs=["C:\\Clash\\save\\0.dat", "captures/current/bad.exe"],
    )
    report = continuity.build_report(manifest)
    assert report["passed"] is False
    assert any("live C:\\Clash\\save" in failure for failure in report["failures"])
    assert any("forbidden artifact" in failure for failure in report["failures"])


def test_campaign_duration_and_palette_gate_fail(fixture: Path) -> None:
    payload = {
        "proofs": {
            "save_load_roundtrip": proof(roundtrip_completed=True, duration_sec=120),
            "turn_advancement": proof(turn_advanced=True, duration_sec=120),
            "campaign_routes": proof(route_completed=True, palette_corruption_detected=True, duration_sec=120),
        }
    }
    fixture.mkdir(parents=True, exist_ok=True)
    manifest = fixture / "bad-campaign.json"
    manifest.write_text(json.dumps(payload, indent=2) + "\n", encoding="ascii")
    report = continuity.build_report(manifest)
    assert report["passed"] is False
    campaign = report["checks"]["campaign_routes"]
    assert campaign["status"] == "blocked_invalid_proof"
    assert any("palette_corruption_detected must be false" in failure for failure in campaign["failures"])
    assert any("duration_sec 120 is below 600" in failure for failure in campaign["failures"])


def test_stage_sha_and_approval_fail(fixture: Path) -> None:
    manifest = write_manifest(
        fixture / "bad-common.json",
        approved=False,
        stage="other-stage",
        candidate_sha256="bad",
    )
    report = continuity.build_report(manifest)
    assert report["passed"] is False
    assert any("approved must be true" in failure for failure in report["failures"])
    assert any("protected stable stage" in failure for failure in report["failures"])
    assert any("candidate_sha256" in failure for failure in report["failures"])


def test_route_markers_and_observations_are_required(fixture: Path) -> None:
    manifest = write_manifest(
        fixture / "bad-route-proof.json",
        route="TODO route",
        start_marker="same-marker",
        end_marker="same-marker",
        route_markers=[],
        before_observation="placeholder before",
        after_observation="",
    )
    report = continuity.build_report(manifest)
    assert report["passed"] is False
    assert any("route must be present" in failure for failure in report["failures"])
    assert any("start_marker and end_marker must differ" in failure for failure in report["failures"])
    assert any("route_markers must be a nonempty list" in failure for failure in report["failures"])
    assert any("before_observation must be present" in failure for failure in report["failures"])
    assert any("after_observation must be present" in failure for failure in report["failures"])


def test_cli_writes_outputs_and_require_pass_fails_closed(fixture: Path) -> None:
    missing = fixture / "missing.json"
    out_json = fixture / "out" / "continuity.json"
    out_md = fixture / "out" / "continuity.md"
    result = run_script(
        "--proof-json",
        str(missing),
        "--write-json",
        str(out_json),
        "--write-markdown",
        str(out_md),
        "--require-pass",
    )
    assert result.returncode == 1, result.stdout + result.stderr
    assert json.loads(out_json.read_text(encoding="ascii"))["passed"] is False
    assert "HD Continuity Status" in out_md.read_text(encoding="ascii")


def run_tests() -> None:
    fixture = ROOT / ".codex-loop" / "tmp-tests" / "hd-continuity-status-fixture"
    shutil.rmtree(fixture, ignore_errors=True)
    fixture.mkdir(parents=True)
    try:
        test_missing_proof_manifest_fails_closed()
        test_valid_manifest_passes_all_checks(fixture / "valid")
        test_mixed_candidate_sha_fails_all_lanes(fixture / "mixed-candidate")
        test_live_save_and_repo_binary_artifacts_fail(fixture / "bad-artifacts")
        test_campaign_duration_and_palette_gate_fail(fixture / "bad-campaign")
        test_stage_sha_and_approval_fail(fixture / "bad-common")
        test_route_markers_and_observations_are_required(fixture / "bad-route-proof")
        test_cli_writes_outputs_and_require_pass_fails_closed(fixture / "cli")
    finally:
        shutil.rmtree(fixture, ignore_errors=True)


def main() -> int:
    run_tests()
    print("hd continuity status tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
