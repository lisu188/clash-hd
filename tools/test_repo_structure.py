#!/usr/bin/env python3
"""Regression tests for repo_structure.py."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "repo_structure.py"
sys.path.insert(0, str(ROOT / "tools"))

import repo_structure  # noqa: E402


def main() -> int:
    output = repo_structure.build_output(ROOT)
    assert output.startswith("# Compact Repository Structure\n"), output
    assert "clash-hd/" in output, output
    assert "├── tools/" in output, output
    assert "├── raw/" in output, output
    assert "└── meta/" in output, output
    assert "User-owned source material" in output, output
    assert "Agent-maintained Obsidian-compatible" in output, output

    counted = repo_structure.build_output(ROOT, include_counts=True)
    assert "tools/" in counted and " files)" in counted, counted

    run = subprocess.run(
        [sys.executable, str(SCRIPT), "--counts"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    assert run.returncode == 0, run.stdout + run.stderr
    assert "# Compact Repository Structure" in run.stdout, run.stdout
    assert "captures/" in run.stdout, run.stdout

    print("repo_structure tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
