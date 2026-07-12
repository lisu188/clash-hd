#!/usr/bin/env python3
"""Fixture tests for the Clash95 HD launcher core logic."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src" / "launcher"))

import patch_clash95_hd  # noqa: E402

import core  # noqa: E402
import ini as ini_mod  # noqa: E402
import presets  # noqa: E402
import settings as settings_mod  # noqa: E402


def make_base_bytes() -> bytes:
    patches = patch_clash95_hd.select_patches(patch_clash95_hd.DEFAULT_STAGE)
    size = max(patch.offset + len(patch.old) for patch in patches) + 16
    buffer = bytearray(size)
    for patch in patches:
        buffer[patch.offset : patch.offset + len(patch.old)] = patch.old
    return bytes(buffer)


BASE_BYTES = make_base_bytes()
BASE_SHA = core.sha256_bytes(BASE_BYTES)


def make_environment(fixture: Path) -> tuple[Path, Path]:
    clash_dir = fixture / "clash"
    candidates_root = fixture / "candidates"
    clash_dir.mkdir(parents=True, exist_ok=True)
    candidates_root.mkdir(parents=True, exist_ok=True)
    (clash_dir / core.BASE_EXE_NAME).write_bytes(BASE_BYTES)
    (clash_dir / core.WRAPPER_DLL_NAME).write_bytes(b"fixture wrapper dll")
    return clash_dir, candidates_root


def make_plan(clash_dir: Path, candidates_root: Path) -> core.CandidatePlan:
    return core.plan_candidate(
        clash_dir=clash_dir,
        candidates_root=candidates_root,
        expected_base_sha=BASE_SHA,
        allow_repo_candidates=True,
    )


def expect_launcher_error(callback, needle: str) -> None:
    try:
        callback()
    except core.LauncherError as exc:
        assert needle.lower() in str(exc).lower(), (needle, str(exc))
        return
    raise AssertionError(f"expected LauncherError containing {needle!r}")


def test_plan_refusals(fixture: Path) -> None:
    clash_dir, candidates_root = make_environment(fixture)

    expect_launcher_error(
        lambda: core.plan_candidate(
            clash_dir=clash_dir, candidates_root=candidates_root
        ),
        "inside the repository",
    )
    expect_launcher_error(
        lambda: core.plan_candidate(
            clash_dir=clash_dir,
            candidates_root=clash_dir / "candidates",
            allow_repo_candidates=True,
        ),
        "game directory",
    )
    expect_launcher_error(
        lambda: core.plan_candidate(
            stage="not-a-real-stage",
            clash_dir=clash_dir,
            candidates_root=candidates_root,
            allow_repo_candidates=True,
        ),
        "unknown patch stage",
    )
    if not presets.patcher_supports_resolutions(patch_clash95_hd):
        expect_launcher_error(
            lambda: core.plan_candidate(
                resolution="1920x1080",
                clash_dir=clash_dir,
                candidates_root=candidates_root,
                allow_repo_candidates=True,
            ),
            "not supported yet",
        )


def test_ensure_candidate_builds_and_reuses(fixture: Path) -> None:
    clash_dir, candidates_root = make_environment(fixture)
    plan = make_plan(clash_dir, candidates_root)

    result = core.ensure_candidate(plan)
    assert result["reused"] is False, result
    patches = patch_clash95_hd.select_patches(plan.stage)
    assert result["patch_count"] == len(patches), result
    gate = result["byte_gate"]
    assert gate["patched"] == len(patches), gate
    assert gate["original"] == 0 and gate["unexpected"] == 0, gate

    deploy = core.deploy_runtime_files(plan, result)
    assert deploy["wrapper"] == "copied", deploy
    assert deploy["dxcfg"] == "written", deploy
    assert plan.manifest_path.is_file()
    manifest = json.loads(plan.manifest_path.read_text(encoding="utf-8"))
    assert manifest["output_sha256"] == result["output_sha256"], manifest

    again = core.ensure_candidate(plan)
    assert again["reused"] is True, again

    plan.candidate_exe.write_bytes(b"corrupted")
    rebuilt = core.ensure_candidate(plan)
    assert rebuilt["reused"] is False, rebuilt
    assert rebuilt["output_sha256"] == result["output_sha256"], rebuilt


def test_sha_mismatch_refused(fixture: Path) -> None:
    clash_dir, candidates_root = make_environment(fixture)
    tampered = bytearray(BASE_BYTES)
    tampered[0] ^= 0xFF
    (clash_dir / core.BASE_EXE_NAME).write_bytes(bytes(tampered))
    plan = make_plan(clash_dir, candidates_root)
    expect_launcher_error(lambda: core.ensure_candidate(plan), "SHA-256 mismatch")


def test_launch_gate(fixture: Path) -> None:
    clash_dir, candidates_root = make_environment(fixture)
    plan = make_plan(clash_dir, candidates_root)
    result = core.ensure_candidate(plan)

    try:
        core.launch_game(plan, confirmed=False)
    except PermissionError as exc:
        assert "confirmed=True" in str(exc), str(exc)
    else:
        raise AssertionError("launch_game must refuse confirmed=False")

    expect_launcher_error(
        lambda: core.launch_game(plan, confirmed=True), core.WRAPPER_DLL_NAME
    )

    core.deploy_runtime_files(plan, result)
    recorded: dict[str, object] = {}

    class FakeProcess:
        pid = 4242

    def fake_starter(argv, cwd=None):
        recorded["argv"] = argv
        recorded["cwd"] = cwd
        return FakeProcess()

    process = core.launch_game(plan, confirmed=True, popen=fake_starter)
    assert process.pid == 4242
    assert recorded["argv"] == [str(plan.candidate_exe)], recorded
    assert recorded["cwd"] == str(plan.clash_dir), recorded


def test_deploy_missing_wrapper(fixture: Path) -> None:
    clash_dir, candidates_root = make_environment(fixture)
    (clash_dir / core.WRAPPER_DLL_NAME).unlink()
    plan = make_plan(clash_dir, candidates_root)
    result = core.ensure_candidate(plan)
    deploy = core.deploy_runtime_files(plan, result)
    assert deploy["wrapper"] == "missing", deploy
    assert deploy["dxcfg"] == "written", deploy


def test_environment_report(fixture: Path) -> None:
    clash_dir, candidates_root = make_environment(fixture)
    report = core.check_environment(
        clash_dir=clash_dir,
        candidates_root=candidates_root,
        expected_sha=BASE_SHA,
        snapshot_rows=[],
    )
    assert report.base_exe.passed, report.to_dict()
    assert report.wrapper_dll.passed, report.to_dict()
    assert report.running_processes.passed, report.to_dict()

    busy = core.check_environment(
        clash_dir=clash_dir,
        candidates_root=candidates_root,
        expected_sha=BASE_SHA,
        snapshot_rows=[
            {"image_name": "clash95_hd_800x600.exe", "pid": "1"},
            {"image_name": "notepad.exe", "pid": "2"},
        ],
    )
    assert not busy.running_processes.passed
    assert len(busy.running_processes.detail["matches"]) == 1


def test_settings_roundtrip_and_corruption(fixture: Path) -> None:
    path = fixture / "settings.json"
    data = settings_mod.load_settings(path)
    assert data == settings_mod.DEFAULT_SETTINGS, data
    data["last_resolution"] = "1024x768"
    settings_mod.save_settings(data, path)
    loaded = settings_mod.load_settings(path)
    assert loaded["last_resolution"] == "1024x768", loaded

    path.write_text("{not json", encoding="utf-8")
    recovered = settings_mod.load_settings(path)
    assert recovered == settings_mod.DEFAULT_SETTINGS, recovered


def test_lock_behaviour(fixture: Path) -> None:
    lock = fixture / "launcher.lock"
    assert settings_mod.acquire_lock(lock, pid=111) is True
    assert settings_mod.acquire_lock(lock, pid=222, pid_alive=lambda pid: True) is False
    assert settings_mod.acquire_lock(lock, pid=222, pid_alive=lambda pid: False) is True
    settings_mod.release_lock(lock, pid=333)
    assert lock.exists(), "release with wrong pid must keep the lock"
    settings_mod.release_lock(lock, pid=222)
    assert not lock.exists()


def test_ini_render(fixture: Path) -> None:
    rendered = ini_mod.render_dxcfg("integer")
    assert "scaling=integer" in rendered, rendered
    assert "display=application" in rendered, rendered
    try:
        ini_mod.render_dxcfg("nearest-magic")
    except ini_mod.ScalingModeError:
        pass
    else:
        raise AssertionError("unverified scaling mode must be rejected")


def test_clean_candidate_dir(fixture: Path) -> None:
    clash_dir, candidates_root = make_environment(fixture)
    plan = make_plan(clash_dir, candidates_root)
    result = core.ensure_candidate(plan)
    core.deploy_runtime_files(plan, result)
    removed = core.clean_candidate_dir(plan)
    assert removed, removed
    assert not plan.candidate_dir.exists()


def run_tests() -> None:
    fixture = ROOT / ".codex-loop" / "tmp-tests" / "launcher-core-fixture"
    shutil.rmtree(fixture, ignore_errors=True)
    fixture.mkdir(parents=True)
    try:
        test_plan_refusals(fixture / "refusals")
        test_ensure_candidate_builds_and_reuses(fixture / "build")
        test_sha_mismatch_refused(fixture / "sha")
        test_launch_gate(fixture / "launch")
        test_deploy_missing_wrapper(fixture / "wrapper")
        test_environment_report(fixture / "environment")
        test_settings_roundtrip_and_corruption(fixture / "settings")
        test_lock_behaviour(fixture / "lock")
        test_ini_render(fixture / "ini")
        test_clean_candidate_dir(fixture / "clean")
    finally:
        shutil.rmtree(fixture, ignore_errors=True)


def main() -> int:
    run_tests()
    print("launcher core tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
