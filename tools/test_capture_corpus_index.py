#!/usr/bin/env python3
"""Fixture tests for capture_corpus_index.py."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "capture_corpus_index.py"
sys.path.insert(0, str(ROOT / "tools"))

import capture_corpus_index  # noqa: E402


def run_script(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=str(cwd),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def args_for(root: Path, current_source: Path = Path("current.md")):
    return type(
        "Args",
        (),
        {
            "root": root,
            "captures_root": Path("captures"),
            "current_source": [current_source],
            "archived_source": [Path("archive.md")],
        },
    )()


def make_hidden_run(root: Path, name: str, base: Path = Path("captures")) -> None:
    run = root / base / name
    write(run / "RUN-SUMMARY.md", "Hidden desktop: true\nNo visible desktop window.\n")
    write(run / "surface.png", "png")


def test_current_hidden_reference_passes(fixture: Path) -> None:
    run_name = "cdb-surface-dump-20260514-140601"
    make_hidden_run(fixture, run_name, Path("captures/archive"))
    write(
        fixture / "captures" / "current" / "hd-map-evidence-current.md",
        "\n".join(
            [
                f"- [Run summary](../archive/{run_name}/RUN-SUMMARY.md)",
                f"![surface](../archive/{run_name}/surface.png)",
                "",
            ]
        ),
    )
    write(fixture / "archive.md", "")
    index = capture_corpus_index.build_index(args_for(fixture, Path("captures/current/hd-map-evidence-current.md")))
    assert index["passed"] is True, index
    assert index["reference_status_counts"]["current_referenced"] == 1, index


def test_missing_current_reference_fails(fixture: Path) -> None:
    run = fixture / "captures" / "cdb-surface-dump-20260514-150000"
    write(run / "RUN-SUMMARY.md", "Hidden desktop: true\nNo visible desktop window.\n")
    write(fixture / "current.md", "`captures/cdb-surface-dump-20260514-150000/surface.png`\n")
    write(fixture / "archive.md", "")
    index = capture_corpus_index.build_index(args_for(fixture))
    assert index["passed"] is False, index
    assert any("missing" in failure for failure in index["failures"]), index


def test_fixture_run_placeholder_is_not_current_reference(fixture: Path) -> None:
    write(
        fixture / "current.md",
        "\n".join(
            [
                "`captures/cdb-surface-dump-FIXTURE-RUN/cdb-surface-dump.log`",
                "`captures/cdb-surface-dump-FIXTURE-RUN/right-bottom-slot-fixture-result-summary.md`",
                "",
            ]
        ),
    )
    write(fixture / "archive.md", "")
    (fixture / "captures").mkdir(parents=True)
    index = capture_corpus_index.build_index(args_for(fixture))
    assert index["passed"] is True, index
    assert index["current_reference_count"] == 0, index


def test_transition_run_placeholder_is_not_current_reference(fixture: Path) -> None:
    write(
        fixture / "current.md",
        "\n".join(
            [
                "`captures/cdb-surface-dump-TRANSITION-RUN/cdb-surface-dump.log`",
                "`captures/cdb-surface-dump-TRANSITION-RUN/load-slot-transition-summary.md`",
                "",
            ]
        ),
    )
    write(fixture / "archive.md", "")
    (fixture / "captures").mkdir(parents=True)
    index = capture_corpus_index.build_index(args_for(fixture))
    assert index["passed"] is True, index
    assert index["current_reference_count"] == 0, index


def test_stale_visible_artifacts_do_not_fail(fixture: Path) -> None:
    (fixture / "captures" / "clicktest-20260422-155046").mkdir(parents=True)
    (fixture / "captures" / "visual-smoke-20260423-112320").mkdir(parents=True)
    write(fixture / "current.md", "")
    write(fixture / "archive.md", "`captures/clicktest-20260422-155046/results.json`\n")
    index = capture_corpus_index.build_index(args_for(fixture))
    assert index["passed"] is True, index
    assert index["stale_visible_or_sandbox_count"] == 2, index


def test_current_visible_or_sandbox_reference_fails(fixture: Path) -> None:
    (fixture / "captures" / "visual-smoke-20260423-112320").mkdir(parents=True)
    write(fixture / "current.md", "`captures/visual-smoke-20260423-112320/results.json`\n")
    write(fixture / "archive.md", "")
    index = capture_corpus_index.build_index(args_for(fixture))
    assert index["passed"] is False, index
    assert any("visible_era" in failure for failure in index["failures"]), index


def test_visible_fallback_cdb_reference_fails(fixture: Path) -> None:
    run = fixture / "captures" / "cdb-surface-dump-20260501-000000"
    write(run / "RUN-SUMMARY.md", "Visible desktop fallback: true\n")
    write(fixture / "current.md", "`captures/cdb-surface-dump-20260501-000000/RUN-SUMMARY.md`\n")
    write(fixture / "archive.md", "")
    index = capture_corpus_index.build_index(args_for(fixture))
    assert index["passed"] is False, index
    assert any("visible-desktop CDB" in failure for failure in index["failures"]), index


def test_cli_writes_outputs_and_fails_closed(fixture: Path) -> None:
    (fixture / "captures").mkdir(parents=True)
    write(fixture / "current.md", "`captures/missing-run/surface.png`\n")
    out_json = fixture / "out" / "index.json"
    out_md = fixture / "out" / "index.md"
    result = run_script(
        fixture,
        "--root",
        str(fixture),
        "--current-source",
        "current.md",
        "--archived-source",
        "archive.md",
        "--write-json",
        str(out_json),
        "--write-markdown",
        str(out_md),
        "--require-pass",
    )
    assert result.returncode == 2, result.stdout + result.stderr
    assert json.loads(out_json.read_text(encoding="utf-8"))["passed"] is False
    assert "Capture Corpus Index" in out_md.read_text(encoding="utf-8")


def run_tests() -> None:
    fixture = ROOT / ".codex-loop" / "tmp-tests" / "capture-corpus-index-fixture"
    shutil.rmtree(fixture, ignore_errors=True)
    fixture.mkdir(parents=True)
    try:
        test_current_hidden_reference_passes(fixture / "hidden")
        test_missing_current_reference_fails(fixture / "missing")
        test_fixture_run_placeholder_is_not_current_reference(fixture / "fixture-run-placeholder")
        test_transition_run_placeholder_is_not_current_reference(fixture / "transition-run-placeholder")
        test_stale_visible_artifacts_do_not_fail(fixture / "stale-visible")
        test_current_visible_or_sandbox_reference_fails(fixture / "current-visible")
        test_visible_fallback_cdb_reference_fails(fixture / "visible-fallback")
        test_cli_writes_outputs_and_fails_closed(fixture / "cli")
    finally:
        shutil.rmtree(fixture, ignore_errors=True)


def main() -> int:
    run_tests()
    print("capture corpus index tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
