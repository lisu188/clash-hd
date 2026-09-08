#!/usr/bin/env python3
"""Fixture tests for the resolution manifest guard."""

from __future__ import annotations

import argparse
import copy
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


def profile_fixture(root: Path, *, complete: bool = True) -> argparse.Namespace:
    manifest = json.loads((ROOT / "src/launcher/resolutions.json").read_text(encoding="utf-8"))
    original_stage = manifest["stable_stage"]
    manifest["stable_stage"] = STABLE_STAGE
    if not complete:
        manifest["profiles"].pop("completehd", None)
    for config in manifest["profiles"].values():
        config["stage"] = config["stage"].replace(original_stage, STABLE_STAGE)
    classic = manifest["profiles"]["classic"]
    classic["resolutions"] = good_manifest()["resolutions"]
    classic["resolutions"]["800x600"]["evidence_scope"] = {
        key: copy.deepcopy(classic[key]) for key in ("stage", "recipe_revision", "features")}
    manifest["resolutions"] = copy.deepcopy(classic["resolutions"])
    args = make_good_fixture(root, manifest)
    from patch_clash95_hd import EXPECTED_SHA256
    digest = "a" * 64
    for name in ("normal", "forced"):
        write_json(root / f"captures/archive/run-{name}/summary.json", {
            "Passed": True, "LaunchMode": "hidden-desktop", "HiddenDesktop": True,
            "Stage": STABLE_STAGE, "InputSha256": EXPECTED_SHA256, "CandidateSha256": digest,
            "Surface": {"Width": 800, "Height": 600, "Bytes": 480000}})
    write_json(root / "captures/current/smoke.json", {
        "passed": True, "resolution": "800x600",
        "patch_stage": {"passed": True, "stage": STABLE_STAGE, "sha256": digest},
        "post_owner_evidence": {name: {"passed": True, "run": f"captures/archive/run-{run}", "candidate_sha256": digest}
                                for name, run in (("normal", "normal"), ("forced_visible", "forced"))}})
    for name in resolution_manifest_guard.source_pins(set(manifest["profiles"])):
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, target)
    return args


def test_profiles_and_bound_evidence(fixture: Path) -> None:
    for complete in (False, True):
        args = profile_fixture(fixture / str(complete), complete=complete)
        guard = resolution_manifest_guard.build_guard(args)
        assert guard["passed"], guard["failures"]
        assert guard["status_counts"]["stable"] == 1 and guard["promotion_ready"] is False
        assert len(guard["checks"]["source_context"]["summary"]["sources"]) > 10


def test_profile_metadata_failures(fixture: Path) -> None:
    args = profile_fixture(fixture)
    path = fixture / args.manifest
    original = json.loads(path.read_text(encoding="utf-8"))
    mutations = [
        lambda m: m.update(default_renderer="framed"),
        lambda m: m["profiles"]["framed"].update(stage=STABLE_STAGE),
        lambda m: m["profiles"]["framed"].update(recipe_revision="wrong"),
        lambda m: m["profiles"]["completehd"]["features"].update(minimap_viewport=False),
        lambda m: m["profiles"]["framed"].update(default="1920x1080"),
        lambda m: m["profiles"]["completehd"]["resolutions"].pop("802x602"),
        lambda m: m["profiles"]["completehd"]["resolutions"]["1920x1080"].update(status="validated"),
        lambda m: m["profiles"]["framed"]["resolutions"]["1920x1080"].update(status="stable"),
        lambda m: m["profiles"]["classic"]["resolutions"]["800x600"]["evidence_scope"].update(recipe_revision="wrong"),
        lambda m: m["profiles"]["classic"]["resolutions"]["800x600"]["evidence_scope"]["features"].update(minimap_viewport=0),
        lambda m: m["profiles"]["framed"]["resolutions"]["802x602"].update(tiles=[12, 9]),
    ]
    # Framed terrain excludes its right and bottom borders; 802x602 has 11x8 full cells.
    original["profiles"]["framed"]["resolutions"]["802x602"] = {"status": "experimental", "tiles": [11, 8], "evidence": None}
    write_json(path, original)
    assert resolution_manifest_guard.build_guard(args)["passed"]
    for mutate in mutations:
        manifest = copy.deepcopy(original)
        mutate(manifest)
        write_json(path, manifest)
        result = resolution_manifest_guard.build_guard(args)
        assert not result["passed"], manifest


def test_profile_evidence_and_source_failures(fixture: Path) -> None:
    args = profile_fixture(fixture)
    path = fixture / "captures/archive/run-normal/summary.json"
    original = json.loads(path.read_text(encoding="utf-8"))
    for mutation in ({"Passed": False}, {"HiddenDesktop": "true"}, {"Stage": "wrong"},
                     {"CandidateSha256": "b" * 64}, {"InputSha256": "b" * 64},
                     {"Resolution": "1024x768"}, {"Surface": {"Width": 1024, "Height": 768, "Bytes": 786432}}):
        write_json(path, {**original, **mutation})
        report = resolution_manifest_guard.build_guard(args)
        assert not report["checks"]["evidence_backed"]["passed"], mutation
    write_json(path, original)
    smoke_path = fixture / "captures/current/smoke.json"
    smoke = json.loads(smoke_path.read_text(encoding="utf-8"))
    smoke["post_owner_evidence"]["normal"]["run"] = "captures/archive/unrelated"
    write_json(smoke_path, smoke)
    assert not resolution_manifest_guard.build_guard(args)["checks"]["evidence_backed"]["passed"]
    minimap = fixture / "src/patcher/framed_minimap.py"
    minimap.write_bytes(minimap.read_bytes() + b"\n# altered fixture source\n")
    report = resolution_manifest_guard.build_guard(args)
    assert not report["checks"]["source_context"]["passed"], report


def test_duplicate_keys_fail(fixture: Path) -> None:
    args = make_good_fixture(fixture)
    path = fixture / args.manifest
    path.write_text(path.read_text(encoding="utf-8").replace('"schema": 1', '"schema": 2, "schema": 1'), encoding="utf-8")
    assert not resolution_manifest_guard.build_guard(args)["passed"]


def test_malformed_profiles_fail_without_exception(fixture: Path) -> None:
    args = profile_fixture(fixture)
    path = fixture / args.manifest
    original = json.loads(path.read_text(encoding="utf-8"))
    for mutate in (
        lambda m: m.update(profiles=[]),
        lambda m: m["profiles"].update(framed=None),
        lambda m: m["profiles"]["framed"].update(resolutions=[]),
        lambda m: m["profiles"]["completehd"].update(resolutions=None),
        lambda m: m["profiles"]["framed"]["resolutions"].update({"640x480": {"status": "experimental", "tiles": [10, 7]}}),
        lambda m: m.update(custom_bounds="bad"),
    ):
        bad = copy.deepcopy(original)
        mutate(bad)
        write_json(path, bad)
        assert not resolution_manifest_guard.build_guard(args)["passed"], bad
    for mutation in ({"schema": True}, {"resolutions": {"800x600": None}}, {"custom_bounds": "bad"}):
        write_json(path, {**good_manifest(), **mutation})
        assert not resolution_manifest_guard.build_guard(args)["passed"], mutation


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
        test_profiles_and_bound_evidence(fixture / "profiles")
        test_profile_metadata_failures(fixture / "profile-metadata")
        test_profile_evidence_and_source_failures(fixture / "profile-evidence")
        test_duplicate_keys_fail(fixture / "duplicates")
        test_malformed_profiles_fail_without_exception(fixture / "malformed")
    finally:
        shutil.rmtree(fixture, ignore_errors=True)


def main() -> int:
    run_tests()
    print("resolution manifest guard tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
