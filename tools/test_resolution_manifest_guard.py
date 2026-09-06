#!/usr/bin/env python3
"""Fixture tests for the resolution manifest guard."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "resolution_manifest_guard.py"
sys.path.insert(0, str(ROOT / "tools"))

import resolution_manifest_guard  # noqa: E402


STABLE_STAGE = "fixture-stable-stage"
CANDIDATE_SHA = "a" * 64


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def surface(width: int = 800, height: int = 600) -> dict:
    return {"Width": width, "Height": height, "Bytes": width * height}


def make_run_dir(root: Path, rel: str, hidden: bool = True, width: int = 800, height: int = 600) -> None:
    write_json(
        root / rel / "summary.json",
        {
            "Passed": True,
            "LaunchMode": "hidden-desktop" if hidden else "visible",
            "HiddenDesktop": hidden,
            "Stage": STABLE_STAGE,
            "CandidateSha256": CANDIDATE_SHA,
            "Surface": surface(width, height),
        },
    )


def good_manifest() -> dict:
    return {
        "schema": 1,
        "default": "800x600",
        "stable_stage": STABLE_STAGE,
        "resolutions": {
            "800x600": {
                "status": "stable",
                "tiles": [12, 9],
                "evidence": {
                    "normal_run": "captures/archive/run-normal",
                    "forced_run": "captures/archive/run-forced",
                    "smoke_json": "captures/current/smoke.json",
                },
            },
            "1920x1080": {"status": "experimental", "tiles": None, "evidence": None},
        },
        "custom_allowed": True,
        "custom_bounds": {"min": [800, 600], "max": [3840, 2160]},
    }


def make_good_fixture(root: Path, manifest: dict | None = None) -> argparse.Namespace:
    write_json(root / "src/launcher/resolutions.json", manifest or good_manifest())
    write_evidence_bundle(root)
    return argparse.Namespace(
        root=root,
        manifest=Path("src/launcher/resolutions.json"),
        expected_default="800x600",
        expected_stable_stage=STABLE_STAGE,
    )


def write_evidence_bundle(root: Path, resolution: str = "800x600", prefix: str = "") -> dict:
    """Use existing patch report, smoke matrix, and CDB summary schemas."""
    width, height = (int(part) for part in resolution.split("x"))
    evidence = {
        "normal_run": f"captures/archive/{prefix}run-normal",
        "forced_run": f"captures/archive/{prefix}run-forced",
        "smoke_json": f"captures/current/{prefix}smoke.json",
    }
    patch_ref = f"captures/current/{prefix}patch-report.json"
    write_json(root / patch_ref, {
        "resolution": resolution, "stage": STABLE_STAGE, "exe_sha256": CANDIDATE_SHA,
        "patch_count": 118, "status_counts": {"patched": 118},
        "current_hd_map_gate": {"passed": True, "failures": []},
    })
    rows = {"passed": True}
    for run_key, smoke_key in (("normal_run", "normal"), ("forced_run", "forced_visible")):
        run_ref = evidence[run_key]
        make_run_dir(root, run_ref, width=width, height=height)
        rows[smoke_key] = {
            "run": run_ref, "passed": True, "present": True, "failures": [],
            "candidate_sha256": CANDIDATE_SHA, "surface": surface(width, height),
        }
    write_json(root / evidence["smoke_json"], {
        "passed": True, "failures": [], "resolution": resolution, "patch_report_json": patch_ref,
        "patch_stage": {
            "passed": True, "failures": [], "stage": STABLE_STAGE, "sha256": CANDIDATE_SHA,
            "archived": True, "source": patch_ref,
            "patches": {"total": 118, "patched": 118, "original": 0, "unexpected": 0},
            "current_hd_map_gate": {"passed": True, "failures": []},
        },
        "post_owner_evidence": rows,
    })
    return evidence


def rewrite_json(path: Path, update) -> None:
    payload = json.loads(path.read_text(encoding="utf-8"))
    update(payload)
    write_json(path, payload)


def run_script(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def test_good_fixture(fixture: Path) -> None:
    args = make_good_fixture(fixture)
    guard = resolution_manifest_guard.build_guard(args)
    assert guard["passed"], guard["failures"]
    assert guard["status_counts"]["stable"] == 1, guard


def test_missing_manifest_fails(fixture: Path) -> None:
    args = argparse.Namespace(
        root=fixture,
        manifest=Path("src/launcher/resolutions.json"),
        expected_default="800x600",
        expected_stable_stage=STABLE_STAGE,
    )
    guard = resolution_manifest_guard.build_guard(args)
    assert not guard["passed"], guard


def test_two_stable_entries_fail(fixture: Path) -> None:
    manifest = good_manifest()
    manifest["resolutions"]["1920x1080"] = {
        "status": "stable",
        "tiles": [29, 16],
        "evidence": manifest["resolutions"]["800x600"]["evidence"],
    }
    args = make_good_fixture(fixture, manifest)
    guard = resolution_manifest_guard.build_guard(args)
    assert not guard["checks"]["single_stable_default"]["passed"], guard


def test_stable_stage_mismatch_fails(fixture: Path) -> None:
    manifest = good_manifest()
    manifest["stable_stage"] = "some-other-stage"
    args = make_good_fixture(fixture, manifest)
    guard = resolution_manifest_guard.build_guard(args)
    assert not guard["checks"]["stable_stage_matches"]["passed"], guard


def test_wrong_tiles_fail(fixture: Path) -> None:
    manifest = good_manifest()
    manifest["resolutions"]["800x600"]["tiles"] = [11, 9]
    args = make_good_fixture(fixture, manifest)
    guard = resolution_manifest_guard.build_guard(args)
    assert not guard["checks"]["tiles_formula"]["passed"], guard


def test_visible_run_fails(fixture: Path) -> None:
    args = make_good_fixture(fixture)
    make_run_dir(fixture, "captures/archive/run-normal", hidden=False)
    guard = resolution_manifest_guard.build_guard(args)
    assert not guard["checks"]["evidence_backed"]["passed"], guard


def test_missing_run_dir_fails(fixture: Path) -> None:
    args = make_good_fixture(fixture)
    shutil.rmtree(fixture / "captures/archive/run-forced")
    guard = resolution_manifest_guard.build_guard(args)
    assert not guard["checks"]["evidence_backed"]["passed"], guard


def test_failing_smoke_fails(fixture: Path) -> None:
    args = make_good_fixture(fixture)
    write_json(fixture / "captures/current/smoke.json", {"passed": False})
    guard = resolution_manifest_guard.build_guard(args)
    assert not guard["checks"]["evidence_backed"]["passed"], guard


def test_validated_without_evidence_fails(fixture: Path) -> None:
    manifest = good_manifest()
    manifest["resolutions"]["1920x1080"] = {
        "status": "validated",
        "tiles": [29, 16],
        "evidence": None,
    }
    args = make_good_fixture(fixture, manifest)
    guard = resolution_manifest_guard.build_guard(args)
    assert not guard["checks"]["evidence_backed"]["passed"], guard


def test_validated_with_matching_larger_evidence_passes(fixture: Path) -> None:
    args = make_good_fixture(fixture)
    manifest = good_manifest()
    manifest["resolutions"]["1920x1080"] = {
        "status": "validated", "tiles": [29, 16],
        "evidence": write_evidence_bundle(fixture, "1920x1080", "hd-"),
    }
    write_json(fixture / args.manifest, manifest)
    guard = resolution_manifest_guard.build_guard(args)
    assert guard["passed"], guard["failures"]


def test_archived_800_evidence_cannot_validate_larger_preset(fixture: Path) -> None:
    manifest = good_manifest()
    manifest["resolutions"]["1920x1080"] = {
        "status": "validated", "tiles": [29, 16],
        "evidence": manifest["resolutions"]["800x600"]["evidence"],
    }
    args = make_good_fixture(fixture, manifest)
    guard = resolution_manifest_guard.build_guard(args)
    assert not guard["checks"]["evidence_backed"]["passed"]
    assert any("does not match 1920x1080" in failure for failure in guard["failures"]), guard


def test_binding_mismatches_fail(fixture: Path) -> None:
    cases = [
        ("smoke-dimension", "captures/current/smoke.json", lambda d: d.update(resolution="1024x768")),
        ("patch-dimension", "captures/current/patch-report.json", lambda d: d.update(resolution="1024x768")),
        ("run-dimension", "captures/archive/run-normal/summary.json", lambda d: d.update(Surface=surface(1024, 768))),
        ("row-dimension", "captures/current/smoke.json", lambda d: d["post_owner_evidence"]["forced_visible"].update(surface=surface(1024, 768))),
        ("patch-stage", "captures/current/patch-report.json", lambda d: d.update(stage="different-stage")),
        ("gate-stage", "captures/current/smoke.json", lambda d: d["patch_stage"].update(stage="different-stage")),
        ("run-stage", "captures/archive/run-forced/summary.json", lambda d: d.update(Stage="different-stage")),
        ("patch-sha", "captures/current/patch-report.json", lambda d: d.update(exe_sha256="b" * 64)),
        ("gate-sha", "captures/current/smoke.json", lambda d: d["patch_stage"].update(sha256="b" * 64)),
        ("run-sha", "captures/archive/run-normal/summary.json", lambda d: d.update(CandidateSha256="b" * 64)),
        ("row-sha", "captures/current/smoke.json", lambda d: d["post_owner_evidence"]["normal"].update(candidate_sha256="b" * 64)),
        ("row-reference", "captures/current/smoke.json", lambda d: d["post_owner_evidence"]["normal"].update(run="captures/archive/run-forced")),
        ("gate-source", "captures/current/smoke.json", lambda d: d["patch_stage"].update(source="captures/current/unrelated.json")),
        ("raw-fail", "captures/current/patch-report.json", lambda d: d["current_hd_map_gate"].update(passed=False)),
        ("raw-count", "captures/current/patch-report.json", lambda d: d["status_counts"].update(patched=117, original=1)),
        ("raw-unexpected", "captures/current/patch-report.json", lambda d: d["status_counts"].update(patched=117, unexpected=1)),
        ("gate-count", "captures/current/smoke.json", lambda d: d["patch_stage"]["patches"].update(total=119)),
        ("run-fail", "captures/archive/run-normal/summary.json", lambda d: d.update(Passed=False)),
        ("null-resolution", "captures/current/patch-report.json", lambda d: d.update(resolution=None)),
    ]
    for name, path, update in cases:
        case_root = fixture / name
        args = make_good_fixture(case_root)
        rewrite_json(case_root / path, update)
        guard = resolution_manifest_guard.build_guard(args)
        assert not guard["checks"]["evidence_backed"]["passed"], (name, guard)


def test_legacy_missing_patch_resolution_is_800_only(fixture: Path) -> None:
    args = make_good_fixture(fixture)
    rewrite_json(fixture / "captures/current/patch-report.json", lambda d: d.pop("resolution"))
    assert resolution_manifest_guard.build_guard(args)["passed"]
    evidence = write_evidence_bundle(fixture, "1920x1080", "larger-")
    rewrite_json(fixture / "captures/current/larger-patch-report.json", lambda d: d.pop("resolution"))
    manifest = good_manifest()
    manifest["resolutions"]["1920x1080"] = {"status": "validated", "tiles": [29, 16], "evidence": evidence}
    write_json(fixture / args.manifest, manifest)
    guard = resolution_manifest_guard.build_guard(args)
    assert not guard["checks"]["evidence_backed"]["passed"], guard


def test_bad_bounds_fail(fixture: Path) -> None:
    manifest = good_manifest()
    manifest["custom_bounds"] = {"min": [640, 480], "max": [3840, 2160]}
    args = make_good_fixture(fixture, manifest)
    guard = resolution_manifest_guard.build_guard(args)
    assert not guard["checks"]["custom_bounds_sane"]["passed"], guard


def test_bad_key_fails(fixture: Path) -> None:
    manifest = good_manifest()
    manifest["resolutions"]["800by600"] = {"status": "experimental"}
    args = make_good_fixture(fixture, manifest)
    guard = resolution_manifest_guard.build_guard(args)
    assert not guard["checks"]["resolution_keys_valid"]["passed"], guard


def test_cli_writes_outputs_and_fails_closed(fixture: Path) -> None:
    make_good_fixture(fixture / "good")
    out_json = fixture / "guard.json"
    out_md = fixture / "guard.md"
    completed = run_script(
        "--root", str(fixture / "good"),
        "--expected-stable-stage", STABLE_STAGE,
        "--write-json", str(out_json),
        "--write-markdown", str(out_md),
        "--require-pass",
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    payload = json.loads(out_json.read_text(encoding="utf-8"))
    assert payload["passed"] is True, payload
    assert "- Overall: PASS" in out_md.read_text(encoding="utf-8")

    bad = good_manifest()
    bad["default"] = "1920x1080"
    make_good_fixture(fixture / "bad", bad)
    completed = run_script(
        "--root", str(fixture / "bad"),
        "--expected-stable-stage", STABLE_STAGE,
        "--write-json", str(fixture / "bad.json"),
        "--write-markdown", str(fixture / "bad.md"),
        "--require-pass",
    )
    assert completed.returncode == 2, completed.stdout + completed.stderr
    assert "- Overall: FAIL" in (fixture / "bad.md").read_text(encoding="utf-8")


def run_tests() -> None:
    fixture = ROOT / ".codex-loop" / "tmp-tests" / "resolution-manifest-guard-fixture"
    shutil.rmtree(fixture, ignore_errors=True)
    fixture.mkdir(parents=True)
    try:
        test_good_fixture(fixture / "good")
        test_missing_manifest_fails(fixture / "missing")
        test_two_stable_entries_fail(fixture / "two-stable")
        test_stable_stage_mismatch_fails(fixture / "stage")
        test_wrong_tiles_fail(fixture / "tiles")
        test_visible_run_fails(fixture / "visible")
        test_missing_run_dir_fails(fixture / "run-dir")
        test_failing_smoke_fails(fixture / "smoke")
        test_validated_without_evidence_fails(fixture / "validated")
        test_validated_with_matching_larger_evidence_passes(fixture / "validated-matching")
        test_archived_800_evidence_cannot_validate_larger_preset(fixture / "reused-800")
        test_binding_mismatches_fail(fixture / "binding-mismatches")
        test_legacy_missing_patch_resolution_is_800_only(fixture / "legacy-resolution")
        test_bad_bounds_fail(fixture / "bounds")
        test_bad_key_fails(fixture / "key")
        test_cli_writes_outputs_and_fails_closed(fixture / "cli")
    finally:
        shutil.rmtree(fixture, ignore_errors=True)


def main() -> int:
    run_tests()
    print("resolution manifest guard tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
