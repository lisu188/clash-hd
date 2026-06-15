#!/usr/bin/env python3
"""Fixture tests for the no-visible runtime guard."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path
from typing import Iterator


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "no_visible_runtime_guard.py"
sys.path.insert(0, str(ROOT / "tools"))

import no_visible_runtime_guard  # noqa: E402


RUNTIME_POLICY = "repo-only; does not launch Clash95, CDB, wrappers, or visible windows"


@contextmanager
def pushd(path: Path) -> Iterator[None]:
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


def run_script(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def good_summary() -> dict:
    return {
        "Passed": True,
        "LaunchMode": "hidden-desktop",
        "HiddenDesktop": True,
        "AllowVisibleDesktop": False,
        "DesktopName": "clash-fixture-hidden",
        "Stage": "fixture-stage",
        "CandidateSha256": "fixture-sha",
        "ExtraProbeTemplate": "fixture-probe.cdb",
    }


def write_run(root: Path, name: str, summary: dict | None = None) -> Path:
    run = root / "captures" / name
    run.mkdir(parents=True, exist_ok=True)
    if summary is not None:
        (run / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return Path("captures") / name


def payload_for(*runs: Path, runtime_policy: str = RUNTIME_POLICY) -> dict:
    return {
        "runtime_policy": runtime_policy,
        "checks": {
            f"run_{index}": {
                "json": str(run / "summary.json"),
                "run": str(run),
            }
            for index, run in enumerate(runs)
        },
    }


def test_guard_passes_hidden_desktop_runs(fixture: Path) -> None:
    run_a = write_run(fixture, "cdb-surface-dump-20260101-010101", good_summary())
    run_b = write_run(fixture, "cdb-surface-dump-20260101-010102", good_summary())
    with pushd(fixture):
        guard = no_visible_runtime_guard.build_guard_from_payloads(
            [payload_for(run_a, run_b)],
            runtime_policy=RUNTIME_POLICY,
        )
    assert guard["passed"] is True, guard
    assert guard["run_count"] == 2, guard
    assert guard["hidden_run_count"] == 2, guard
    assert not guard["failures"], guard


def test_guard_rejects_weak_runtime_policy(fixture: Path) -> None:
    run = write_run(fixture, "cdb-surface-dump-20260101-010101", good_summary())
    with pushd(fixture):
        guard = no_visible_runtime_guard.build_guard_from_payloads(
            [payload_for(run, runtime_policy="repo-only")],
            runtime_policy="repo-only",
        )
    assert guard["passed"] is False, guard
    assert any("runtime policy" in failure for failure in guard["failures"]), guard


def test_guard_rejects_visible_runtime_regressions(fixture: Path) -> None:
    cases = [
        ("visible-hidden-flag", {"HiddenDesktop": False}, "HiddenDesktop is False"),
        ("visible-launch-mode", {"LaunchMode": "visible-desktop-explicit"}, "LaunchMode is visible-desktop-explicit"),
        ("allow-visible", {"AllowVisibleDesktop": True}, "AllowVisibleDesktop is true"),
    ]
    for label, updates, expected_failure in cases:
        case_root = fixture / label
        summary = deepcopy(good_summary())
        summary.update(updates)
        run = write_run(case_root, "cdb-surface-dump-20260101-010101", summary)
        with pushd(case_root):
            guard = no_visible_runtime_guard.build_guard_from_payloads(
                [payload_for(run)],
                runtime_policy=RUNTIME_POLICY,
            )
        assert guard["passed"] is False, guard
        assert any(expected_failure in failure for failure in guard["failures"]), guard


def test_guard_rejects_missing_run_summary(fixture: Path) -> None:
    run = write_run(fixture, "cdb-surface-dump-20260101-010101", None)
    with pushd(fixture):
        guard = no_visible_runtime_guard.build_guard_from_payloads(
            [payload_for(run)],
            runtime_policy=RUNTIME_POLICY,
        )
    assert guard["passed"] is False, guard
    assert any("missing run summary" in failure for failure in guard["failures"]), guard


def test_cli_writes_outputs_and_fails_closed(fixture: Path) -> None:
    good_run = write_run(fixture, "cdb-surface-dump-20260101-010101", good_summary())
    refresh_json = fixture / "refresh.json"
    refresh_json.write_text(json.dumps(payload_for(good_run), indent=2) + "\n", encoding="utf-8")
    out_json = fixture / "good-output" / "guard.json"
    out_md = fixture / "good-output" / "guard.md"
    good_cli = run_script(
        fixture,
        "--refresh-json",
        "refresh.json",
        "--write-json",
        str(out_json),
        "--write-markdown",
        str(out_md),
        "--require-pass",
    )
    assert good_cli.returncode == 0, good_cli.stdout + good_cli.stderr
    assert json.loads(out_json.read_text(encoding="utf-8"))["passed"] is True
    assert "- Overall: PASS" in out_md.read_text(encoding="utf-8")

    bad_summary = good_summary()
    bad_summary["LaunchMode"] = "visible-desktop-explicit"
    bad_run = write_run(fixture, "cdb-surface-dump-20260101-010102", bad_summary)
    bad_refresh_json = fixture / "bad-refresh.json"
    bad_refresh_json.write_text(json.dumps(payload_for(bad_run), indent=2) + "\n", encoding="utf-8")
    bad_json = fixture / "bad-output" / "guard.json"
    bad_md = fixture / "bad-output" / "guard.md"
    bad_cli = run_script(
        fixture,
        "--refresh-json",
        "bad-refresh.json",
        "--write-json",
        str(bad_json),
        "--write-markdown",
        str(bad_md),
        "--require-pass",
    )
    assert bad_cli.returncode == 2, bad_cli.stdout + bad_cli.stderr
    assert json.loads(bad_json.read_text(encoding="utf-8"))["passed"] is False
    assert "- Overall: FAIL" in bad_md.read_text(encoding="utf-8")


def run_tests() -> None:
    fixture = ROOT / ".codex-loop" / "tmp-tests" / "no-visible-runtime-fixture"
    shutil.rmtree(fixture, ignore_errors=True)
    fixture.mkdir(parents=True)
    try:
        test_guard_passes_hidden_desktop_runs(fixture / "passes")
        test_guard_rejects_weak_runtime_policy(fixture / "runtime-policy")
        test_guard_rejects_visible_runtime_regressions(fixture / "visible-regressions")
        test_guard_rejects_missing_run_summary(fixture / "missing-summary")
        test_cli_writes_outputs_and_fails_closed(fixture / "cli")
    finally:
        shutil.rmtree(fixture, ignore_errors=True)


def main() -> int:
    run_tests()
    print("no-visible runtime guard tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
