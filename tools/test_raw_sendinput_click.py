#!/usr/bin/env python3
"""Repo-only tests for raw SendInput click helper."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "raw_sendinput_click.py"
sys.path.insert(0, str(ROOT / "tools"))

import raw_sendinput_click  # noqa: E402


def run_script(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def test_parse_points() -> None:
    assert raw_sendinput_click.parse_points("668,520; 588,440") == [(668, 520), (588, 440)]


def test_build_dry_run_shape() -> None:
    result = raw_sendinput_click.build_dry_run([(668, 520)], hold_ms=300, repeat=3)
    assert result == {
        "dry_run": True,
        "points": [
            {
                "requested_screen": [668, 520],
                "clicks": [
                    {"repeat_index": 0, "hold_ms": 300},
                    {"repeat_index": 1, "hold_ms": 300},
                    {"repeat_index": 2, "hold_ms": 300},
                ],
            }
        ],
    }


def test_cli_dry_run_writes_json(fixture: Path) -> None:
    fixture.mkdir(parents=True, exist_ok=True)
    out_json = fixture / "raw-click.json"
    run = run_script(
        "--screen-points",
        "668,520;588,440",
        "--click-hold-ms",
        "250",
        "--click-repeat",
        "2",
        "--dry-run",
        "--json",
        str(out_json),
    )
    assert run.returncode == 0, run.stdout + run.stderr
    result = json.loads(out_json.read_text(encoding="ascii"))
    assert result["dry_run"] is True
    assert [point["requested_screen"] for point in result["points"]] == [[668, 520], [588, 440]]
    assert result["points"][0]["clicks"][1]["hold_ms"] == 250


def run_tests() -> None:
    fixture = ROOT / ".codex-loop" / "tmp-tests" / "raw-sendinput-click-fixture"
    shutil.rmtree(fixture, ignore_errors=True)
    fixture.mkdir(parents=True, exist_ok=True)
    try:
        test_parse_points()
        test_build_dry_run_shape()
        test_cli_dry_run_writes_json(fixture)
    finally:
        shutil.rmtree(fixture, ignore_errors=True)


def main() -> int:
    run_tests()
    print("raw SendInput click helper tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
