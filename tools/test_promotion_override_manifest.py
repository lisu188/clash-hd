#!/usr/bin/env python3
"""Fixture tests for promotion_override_manifest.py."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "promotion_override_manifest.py"
sys.path.insert(0, str(ROOT / "tools"))

import promotion_override_manifest  # noqa: E402


STAGE = "gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-rightbottomcompose"
SHA = "c" * 64


def run_script(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def write_manifest(path: Path, **updates) -> Path:
    payload = {
        "evidence_class": "cdb_only_promotion_override",
        "approved_cdb_only_promotion": True,
        "approval_record": "User explicitly approved a CDB-only promotion override.",
        "target_scope": "right_bottom_compose",
        "candidate_stage": STAGE,
        "candidate_sha256": SHA,
        "accepted_risk": "Manual DirectInput proof is bypassed for this scoped promotion.",
        "evidence_refs": ["captures/current/right-bottom-compose-evidence-current.md"],
        "no_stale_processes": True,
        "manual_bypass_reason": "Manual DirectInput testing was unavailable and the user accepted CDB-only evidence.",
    }
    payload.update(updates)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def test_absent_manifest_is_safe_inactive() -> None:
    report = promotion_override_manifest.build_report(
        type("Args", (), {"manifest": None, "target_scope": None, "candidate_stage": None, "candidate_sha256": None})()
    )
    assert report["passed"] is True, report
    assert report["override_active"] is False, report


def test_valid_manifest_passes(fixture: Path) -> None:
    manifest = write_manifest(fixture / "override.json")
    validation = promotion_override_manifest.validate_manifest(
        manifest,
        target_scope="right_bottom_compose",
        candidate_stage=STAGE,
        candidate_sha256=SHA,
    )
    assert validation["valid"] is True, validation


def test_missing_approval_bad_sha_and_process_failures(fixture: Path) -> None:
    cases = [
        ("approval", {"approved_cdb_only_promotion": False}, "approved_cdb_only_promotion=true"),
        ("sha", {"candidate_sha256": "bad"}, "64-hex"),
        ("process", {"no_stale_processes": False}, "no_stale_processes=true"),
    ]
    for name, updates, expected in cases:
        manifest = write_manifest(fixture / f"{name}.json", **updates)
        validation = promotion_override_manifest.validate_manifest(manifest, target_scope="right_bottom_compose")
        assert validation["valid"] is False, validation
        assert any(expected in failure for failure in validation["failures"]), validation


def test_missing_approval_and_no_stale_processes_fail(fixture: Path) -> None:
    missing_approval = write_manifest(fixture / "missing-approval.json")
    payload = json.loads(missing_approval.read_text(encoding="utf-8"))
    payload.pop("approved_cdb_only_promotion")
    missing_approval.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    approval_validation = promotion_override_manifest.validate_manifest(
        missing_approval,
        target_scope="right_bottom_compose",
    )
    assert approval_validation["valid"] is False, approval_validation
    assert any("approved_cdb_only_promotion" in failure for failure in approval_validation["failures"]), approval_validation

    missing_processes = write_manifest(fixture / "missing-processes.json")
    payload = json.loads(missing_processes.read_text(encoding="utf-8"))
    payload.pop("no_stale_processes")
    missing_processes.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    process_validation = promotion_override_manifest.validate_manifest(
        missing_processes,
        target_scope="right_bottom_compose",
    )
    assert process_validation["valid"] is False, process_validation
    assert any("no_stale_processes" in failure for failure in process_validation["failures"]), process_validation


def test_scope_stage_and_sha_mismatch_fail(fixture: Path) -> None:
    manifest = write_manifest(fixture / "override.json")
    validation = promotion_override_manifest.validate_manifest(
        manifest,
        target_scope="castle_overview",
        candidate_stage="other-stage",
        candidate_sha256="d" * 64,
    )
    assert validation["valid"] is False, validation
    assert any("target_scope" in failure for failure in validation["failures"]), validation
    assert any("candidate_stage" in failure for failure in validation["failures"]), validation
    assert any("candidate_sha256" in failure for failure in validation["failures"]), validation


def test_cli_writes_outputs_and_fails_closed(fixture: Path) -> None:
    bad_manifest = write_manifest(fixture / "bad.json", candidate_sha256="bad")
    out_json = fixture / "out" / "override.json"
    out_md = fixture / "out" / "override.md"
    result = run_script(
        "--manifest",
        str(bad_manifest),
        "--target-scope",
        "right_bottom_compose",
        "--write-json",
        str(out_json),
        "--write-markdown",
        str(out_md),
        "--require-pass",
    )
    assert result.returncode == 2, result.stdout + result.stderr
    assert json.loads(out_json.read_text(encoding="utf-8"))["passed"] is False
    assert "Promotion Override Manifest" in out_md.read_text(encoding="utf-8")


def run_tests() -> None:
    fixture = ROOT / ".codex-loop" / "tmp-tests" / "promotion-override-manifest-fixture"
    shutil.rmtree(fixture, ignore_errors=True)
    fixture.mkdir(parents=True)
    try:
        test_absent_manifest_is_safe_inactive()
        test_valid_manifest_passes(fixture / "valid")
        test_missing_approval_bad_sha_and_process_failures(fixture / "bad-fields")
        test_missing_approval_and_no_stale_processes_fail(fixture / "missing-fields")
        test_scope_stage_and_sha_mismatch_fail(fixture / "mismatch")
        test_cli_writes_outputs_and_fails_closed(fixture / "cli")
    finally:
        shutil.rmtree(fixture, ignore_errors=True)


def main() -> int:
    run_tests()
    print("promotion override manifest tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
