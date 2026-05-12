#!/usr/bin/env python3
"""Regression tests for evidence_index_check.py."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "evidence_index_check.py"
sys.path.insert(0, str(ROOT / "tools"))

import evidence_index_check  # noqa: E402


def run_check(index: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(index), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def main() -> int:
    fixture = ROOT / ".codex-loop" / "tmp-tests" / "evidence-index-check-fixture"
    shutil.rmtree(fixture, ignore_errors=True)
    fixture.mkdir(parents=True)
    try:
        (fixture / "report.md").write_text("# Report\n", encoding="utf-8")
        (fixture / "surface.png").write_bytes(b"\x89PNG\r\n\x1a\n")
        good = fixture / "good.md"
        bad = fixture / "bad.md"
        good.write_text(
            "\n".join(
                [
                    "# Good",
                    "",
                    "- [Report](report.md)",
                    "",
                    "![Surface](surface.png)",
                    "",
                    "```powershell",
                    "# [Ignored](missing.md)",
                    "```",
                ]
            ),
            encoding="utf-8",
        )
        bad.write_text(
            "\n".join(
                [
                    "# Bad",
                    "",
                    "- [Missing](missing.md)",
                    "",
                    "![Missing image](missing.png)",
                ]
            ),
            encoding="utf-8",
        )

        good_report = evidence_index_check.build_report(good)
        assert good_report["passed"] is True, good_report
        assert good_report["counts"]["links"] == 1, good_report
        assert good_report["counts"]["images"] == 1, good_report

        bad_report = evidence_index_check.build_report(bad)
        assert bad_report["passed"] is False, bad_report
        assert bad_report["counts"]["missing"] == 2, bad_report
        assert bad_report["counts"]["image_missing"] == 1, bad_report

        good_run = run_check(good, "--require-pass")
        assert good_run.returncode == 0, good_run.stdout + good_run.stderr

        bad_run = run_check(bad, "--require-pass")
        assert bad_run.returncode == 2, bad_run.stdout + bad_run.stderr
    finally:
        shutil.rmtree(fixture, ignore_errors=True)
    print("evidence_index_check tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
