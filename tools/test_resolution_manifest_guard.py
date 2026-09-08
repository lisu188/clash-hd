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


def good_profile_manifest(*, completehd: bool = False) -> dict:
    manifest = good_manifest()
    classic = {
        "default": manifest["default"], "stage": manifest["stable_stage"],
        "recipe_revision": "classic-frozen-800-v1", "features": {"minimap_viewport": False},
        "resolutions": copy.deepcopy(manifest["resolutions"]),
    }
    classic["resolutions"]["800x600"]["evidence_scope"] = {
        key: copy.deepcopy(classic[key]) for key in ("stage", "recipe_revision", "features")
    }
    framed = {
        "default": manifest["default"],
        "stage": manifest["stable_stage"] + "-combinedui-partialtiles-initialpaint-framed-validation",
        "recipe_revision": "four-border-partial-initial-v1", "features": {"minimap_viewport": True},
        "resolutions": {key: {"status": "experimental", "tiles": None, "evidence": None}
                        for key in manifest["resolutions"]},
    }
    manifest.update(schema=2, default_renderer="classic", profiles={"classic": classic, "framed": framed},
                    resolutions=copy.deepcopy(classic["resolutions"]))
    if completehd:
        manifest["profiles"]["completehd"] = {
            "default": "800x600", "stage": manifest["stable_stage"] + "-completehd-validation",
            "recipe_revision": "complete_hd_v1", "features": {"minimap_viewport": True},
            "resolutions": {key: {"status": "experimental", "tiles": None, "evidence": None}
                            for key in ("800x600", "1024x768", "1280x720", "1280x960", "1920x1080", "802x602")},
        }
    return manifest


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
    for schema, factory in ((1, good_manifest), (2, good_profile_manifest),
                            ("2-completehd", lambda: good_profile_manifest(completehd=True))):
        for name, path, update in cases:
            case_root = fixture / str(schema) / name
            args = make_good_fixture(case_root, factory())
            rewrite_json(case_root / path, update)
            guard = resolution_manifest_guard.build_guard(args)
            assert not guard["checks"]["evidence_backed"]["passed"], (schema, name, guard)


def test_profile_manifest_preserves_classic_checks(fixture: Path) -> None:
    args = make_good_fixture(fixture, good_profile_manifest())
    guard = resolution_manifest_guard.build_guard(args)
    assert guard["passed"], guard["failures"]
    assert guard["status_counts"] == {"stable": 1, "validated": 0, "experimental": 1}
    for check in ("resolution_keys_valid", "single_stable_default", "stable_stage_matches",
                  "tiles_formula", "evidence_backed", "custom_bounds_sane", "profile_contracts"):
        assert guard["checks"][check]["passed"], check
    assert guard["checks"]["evidence_backed"]["summary"]["checked"] == ["800x600"]
    assert guard["checks"]["profile_contracts"]["summary"]["framed_runtime_evidence_verified"] is False


def test_profile_manifest_rejects_malformed_or_stale_contracts(fixture: Path) -> None:
    cases = [
        ("missing-profiles", lambda m: m.pop("profiles")),
        ("malformed-profile", lambda m: m["profiles"].update(framed=[])),
        ("unknown-profile", lambda m: m["profiles"].update(other={})),
        ("wrong-default-renderer", lambda m: m.update(default_renderer="framed")),
        ("projection-drift", lambda m: m["resolutions"]["800x600"].update(status="experimental")),
        ("recipe-drift", lambda m: m["profiles"]["framed"].update(recipe_revision="stale")),
        ("feature-drift", lambda m: m["profiles"]["framed"].update(features={"minimap_viewport": False})),
        ("feature-type", lambda m: m["profiles"]["framed"].update(features={"minimap_viewport": 1})),
        ("stage-drift", lambda m: m["profiles"]["framed"].update(stage=m["stable_stage"])),
        ("scope-drift", lambda m: m["profiles"]["classic"]["resolutions"]["800x600"]["evidence_scope"].update(recipe_revision="stale")),
        ("missing-scope", lambda m: m["profiles"]["classic"]["resolutions"]["800x600"].pop("evidence_scope")),
        ("bad-entry", lambda m: m["profiles"]["framed"]["resolutions"].update({"800x600": None})),
    ]
    for name, update in cases:
        manifest = good_profile_manifest()
        update(manifest)
        if name in ("scope-drift", "missing-scope"):
            manifest["resolutions"] = copy.deepcopy(manifest["profiles"]["classic"]["resolutions"])
        args = make_good_fixture(fixture / name, manifest)
        guard = resolution_manifest_guard.build_guard(args)
        assert not guard["passed"], (name, guard)


def test_profile_manifest_cannot_relabel_classic_evidence(fixture: Path) -> None:
    for status in ("stable", "validated"):
        manifest = good_profile_manifest()
        framed = manifest["profiles"]["framed"]
        entry = copy.deepcopy(manifest["resolutions"]["800x600"])
        entry.update(status=status, tiles=None)
        # Even a rewritten scope is metadata, not proof that these Classic
        # candidate/run artifacts exercised the Framed feature configuration.
        entry["evidence_scope"] = {key: copy.deepcopy(framed[key])
                                   for key in ("stage", "recipe_revision", "features")}
        framed["resolutions"]["800x600"] = entry
        args = make_good_fixture(fixture / status, manifest)
        guard = resolution_manifest_guard.build_guard(args)
        assert not guard["checks"]["profile_contracts"]["passed"], guard
        assert any("Classic evidence cannot certify" in failure for failure in guard["failures"])


def test_profile_manifest_uses_framed_tile_geometry(fixture: Path) -> None:
    for tiles, expected_pass in (([11, 8], True), ([12, 9], False)):
        manifest = good_profile_manifest()
        manifest["profiles"]["framed"]["resolutions"]["800x600"]["tiles"] = tiles
        args = make_good_fixture(fixture / str(expected_pass), manifest)
        guard = resolution_manifest_guard.build_guard(args)
        assert guard["passed"] is expected_pass, guard


def test_profile_manifest_rejects_duplicate_keys_and_schema_aliases(fixture: Path) -> None:
    args = make_good_fixture(fixture, good_profile_manifest())
    path = fixture / args.manifest
    serialized = path.read_text(encoding="utf-8")
    path.write_text(serialized.replace('"schema": 2,', '"schema": 2, "schema": 2,', 1), encoding="utf-8")
    guard = resolution_manifest_guard.build_guard(args)
    assert not guard["passed"] and any("Duplicate" in failure for failure in guard["failures"]), guard
    for schema in (True, 2.0, "2", 3):
        manifest = good_profile_manifest()
        manifest["schema"] = schema
        write_json(path, manifest)
        guard = resolution_manifest_guard.build_guard(args)
        assert not guard["passed"], (schema, guard)


def test_completehd_profile_remains_experimental_and_geometry_checked(fixture: Path) -> None:
    manifest = good_profile_manifest(completehd=True)
    manifest["profiles"]["completehd"]["resolutions"]["800x600"]["tiles"] = [11, 8]
    args = make_good_fixture(fixture, manifest)
    guard = resolution_manifest_guard.build_guard(args)
    assert guard["passed"], guard["failures"]
    summary = guard["checks"]["profile_contracts"]["summary"]
    assert summary["completehd_resolution_count"] == 6
    assert summary["completehd_runtime_evidence_verified"] is False
    assert guard["checks"]["evidence_backed"]["summary"]["checked"] == ["800x600"]
    manifest["profiles"]["completehd"]["resolutions"]["800x600"]["tiles"] = [12, 9]
    write_json(fixture / args.manifest, manifest)
    guard = resolution_manifest_guard.build_guard(args)
    assert not guard["checks"]["profile_contracts"]["passed"], guard


def test_completehd_profile_rejects_contract_drift_and_promotion(fixture: Path) -> None:
    for mutation in ("unknown-profile", "stage", "recipe", "features", "default", "missing-resolution",
                     "extra-resolution", "malformed-resolutions", "malformed-entry", "stable", "validated"):
        manifest = good_profile_manifest(completehd=True)
        profile = manifest["profiles"]["completehd"]
        if mutation == "unknown-profile": manifest["profiles"]["unknown"] = copy.deepcopy(profile)
        elif mutation == "stage": profile["stage"] = manifest["stable_stage"]
        elif mutation == "recipe": profile["recipe_revision"] = "unreviewed-recipe"
        elif mutation == "features": profile["features"]["minimap_viewport"] = 1
        elif mutation == "default": profile["default"] = "1920x1080"
        elif mutation == "missing-resolution": profile["resolutions"].pop("802x602")
        elif mutation == "extra-resolution": profile["resolutions"]["1366x768"] = {"status": "experimental"}
        elif mutation == "malformed-resolutions": profile["resolutions"] = None
        elif mutation == "malformed-entry": profile["resolutions"]["800x600"] = None
        else: profile["resolutions"]["800x600"]["status"] = mutation
        args = make_good_fixture(fixture / mutation, manifest)
        guard = resolution_manifest_guard.build_guard(args)
        assert not guard["passed"], (mutation, guard)


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
        test_profile_manifest_preserves_classic_checks(fixture / "profiles")
        test_profile_manifest_rejects_malformed_or_stale_contracts(fixture / "profile-contracts")
        test_profile_manifest_cannot_relabel_classic_evidence(fixture / "profile-evidence")
        test_profile_manifest_uses_framed_tile_geometry(fixture / "profile-tiles")
        test_profile_manifest_rejects_duplicate_keys_and_schema_aliases(fixture / "profile-schema")
        test_completehd_profile_remains_experimental_and_geometry_checked(fixture / "completehd-profile")
        test_completehd_profile_rejects_contract_drift_and_promotion(fixture / "completehd-contract")
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
