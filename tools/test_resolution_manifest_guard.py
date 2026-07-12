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


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def make_run_dir(root: Path, rel: str, hidden: bool = True) -> None:
    write_json(
        root / rel / "summary.json",
        {
            "Passed": True,
            "LaunchMode": "hidden-desktop" if hidden else "visible",
            "HiddenDesktop": hidden,
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
    make_run_dir(root, "captures/archive/run-normal")
    make_run_dir(root, "captures/archive/run-forced")
    write_json(root / "captures/current/smoke.json", {"passed": True})
    return argparse.Namespace(
        root=root,
        manifest=Path("src/launcher/resolutions.json"),
        expected_default="800x600",
        expected_stable_stage=STABLE_STAGE,
    )


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
