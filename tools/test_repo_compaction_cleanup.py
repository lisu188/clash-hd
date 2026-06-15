#!/usr/bin/env python3
"""Fixture tests for repo_compaction_cleanup.py."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "repo_compaction_cleanup.py"
sys.path.insert(0, str(ROOT / "tools"))

import repo_compaction_cleanup  # noqa: E402


def run_script(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(cwd), *args],
        cwd=str(cwd),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def git(root: Path, *args: str) -> None:
    result = subprocess.run(
        ["git", *args],
        cwd=str(root),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def init_repo(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    git(root, "init")
    write(root / ".gitignore", "__pycache__/\n.pytest_cache/\n")
    git(root, "add", ".gitignore")


def build(root: Path, archive_root: Path | None = None, execute: bool = False) -> dict:
    return repo_compaction_cleanup.build_plan(
        root=root,
        archive_root=archive_root or (root.parent / "archive"),
        execute=execute,
    )


def test_stale_generated_capture_dir_is_archived(fixture: Path) -> None:
    init_repo(fixture)
    write(fixture / "captures" / "cdb-surface-dump-20250101-000000" / "RUN-SUMMARY.md", "old\n")
    write(fixture / "captures" / "cdb-surface-dump-20250101-000000" / "surface.png", "png\n")
    plan = build(fixture)
    paths = {candidate["path"] for candidate in plan["archive_candidates"]}
    assert plan["passed"] is True, plan
    assert "captures/cdb-surface-dump-20250101-000000" in paths, plan


def test_current_and_preserved_capture_entries_are_kept(fixture: Path) -> None:
    init_repo(fixture)
    write(
        fixture / "captures" / "current" / "hd-map-evidence-current.md",
        "`captures/archive/cdb-surface-dump-20250101-010101/surface.png`\n",
    )
    write(fixture / "captures" / "archive" / "cdb-surface-dump-20250101-010101" / "surface.png", "png\n")
    write(fixture / "captures" / "archive" / "cdb-surface-dump-20260615-100407" / "surface.png", "proof\n")
    plan = build(fixture)
    paths = {candidate["path"] for candidate in plan["archive_candidates"]}
    assert "captures/archive/cdb-surface-dump-20250101-010101" not in paths, plan
    assert "captures/archive/cdb-surface-dump-20260615-100407" not in paths, plan


def test_unreferenced_compact_archive_capture_dir_is_archived(fixture: Path) -> None:
    init_repo(fixture)
    write(fixture / "captures" / "archive" / "visual-smoke-20250101-000000" / "results.json", "{}\n")
    plan = build(fixture)
    paths = {candidate["path"] for candidate in plan["archive_candidates"]}
    assert "captures/archive/visual-smoke-20250101-000000" in paths, plan


def test_tracked_file_inside_archive_target_fails_closed(fixture: Path) -> None:
    init_repo(fixture)
    write(fixture / "captures" / "cdb-surface-dump-20250101-020202" / "tracked.txt", "tracked\n")
    git(fixture, "add", "captures/cdb-surface-dump-20250101-020202/tracked.txt")
    write(fixture / "captures" / "cdb-surface-dump-20250101-020202" / "new.log", "new\n")
    plan = build(fixture)
    assert plan["passed"] is False, plan
    assert any("tracked or modified" in failure for failure in plan["failures"]), plan


def test_current_root_capture_report_is_kept(fixture: Path) -> None:
    init_repo(fixture)
    write(fixture / "captures" / "README.md", "# captures\n")
    write(fixture / "captures" / "current" / "current-completion-summary-current.md", "current\n")
    write(fixture / "captures" / "patch-stage-old.json", "{}\n")
    plan = build(fixture)
    paths = {candidate["path"] for candidate in plan["archive_candidates"]}
    assert "captures/README.md" not in paths, plan
    assert "captures/current/current-completion-summary-current.md" not in paths, plan
    assert "captures/patch-stage-old.json" in paths, plan


def test_cache_dirs_are_delete_candidates_only_when_untracked(fixture: Path) -> None:
    init_repo(fixture)
    write(fixture / "tools" / "__pycache__" / "x.pyc", "cache\n")
    plan = build(fixture)
    paths = {candidate["path"] for candidate in plan["delete_candidates"]}
    assert "tools/__pycache__" in paths, plan
    assert plan["passed"] is True, plan


def test_forbidden_artifact_outside_archive_candidate_fails(fixture: Path) -> None:
    init_repo(fixture)
    write(fixture / "candidate.dll", "nope\n")
    plan = build(fixture)
    assert plan["passed"] is False, plan
    assert any("forbidden binary" in failure for failure in plan["failures"]), plan


def test_temp_dir_with_nested_git_repo_is_not_deleted(fixture: Path) -> None:
    init_repo(fixture)
    nested = fixture / ".codex-loop" / "tmp-tests" / "nested"
    init_repo(nested)
    plan = build(fixture)
    paths = {candidate["path"] for candidate in plan["delete_candidates"]}
    assert ".codex-loop/tmp-tests" not in paths, plan
    assert plan["passed"] is True, plan


def test_cli_writes_report_and_requires_pass(fixture: Path) -> None:
    init_repo(fixture)
    write(fixture / "captures" / "visual-smoke-20250101-000000" / "results.json", "{}\n")
    out_json = fixture / "reports" / "repo-compaction-current.json"
    out_md = fixture / "reports" / "repo-compaction-current.md"
    result = run_script(
        fixture,
        "--archive-root",
        str(fixture.parent / "archive"),
        "--write-json",
        str(out_json),
        "--write-markdown",
        str(out_md),
        "--require-pass",
    )
    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(out_json.read_text(encoding="utf-8"))
    assert payload["passed"] is True, payload
    assert "Repo Compaction Cleanup" in out_md.read_text(encoding="utf-8")


def run_tests() -> None:
    fixture = Path(tempfile.mkdtemp(prefix="repo-compaction-cleanup-fixture-"))
    try:
        test_stale_generated_capture_dir_is_archived(fixture / "stale-dir")
        test_current_and_preserved_capture_entries_are_kept(fixture / "current-keep")
        test_unreferenced_compact_archive_capture_dir_is_archived(fixture / "compact-archive")
        test_tracked_file_inside_archive_target_fails_closed(fixture / "tracked-fails")
        test_current_root_capture_report_is_kept(fixture / "current-root-file")
        test_cache_dirs_are_delete_candidates_only_when_untracked(fixture / "cache-delete")
        test_forbidden_artifact_outside_archive_candidate_fails(fixture / "forbidden-artifact")
        test_temp_dir_with_nested_git_repo_is_not_deleted(fixture / "nested-git-temp")
        test_cli_writes_report_and_requires_pass(fixture / "cli")
    finally:
        shutil.rmtree(fixture, ignore_errors=True)


def main() -> int:
    run_tests()
    print("repo compaction cleanup tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
