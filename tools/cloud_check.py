#!/usr/bin/env python3
"""Run the Codex Cloud-safe validation set.

This intentionally avoids Windows-only runtime work: no CDB, no DirectDraw
wrapper launch, no Ghidra execution, and no original or patched executable
access. Fresh runtime proof remains a local Windows task.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run_command(label: str, command: list[str]) -> int:
    print(f"== {label}")
    result = subprocess.run(command, cwd=ROOT, text=True)
    if result.returncode:
        print(f"{label}: FAIL ({result.returncode})")
    else:
        print(f"{label}: PASS")
    return result.returncode


def git_ls_root_exes() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "*.exe"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode:
        return [result.stderr.strip() or "git ls-files failed"]
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def check_no_tracked_exes() -> int:
    print("== tracked executable policy")
    exes = git_ls_root_exes()
    if exes:
        print("tracked executable policy: FAIL")
        for path in exes:
            print(f"- {path}")
        return 2
    print("tracked executable policy: PASS")
    return 0


def run_cloud_mode() -> int:
    py = sys.executable
    checks = [
        ("test evidence_index_check", [py, "tools/test_evidence_index_check.py"]),
        ("test patch_manifest_compare", [py, "tools/test_patch_manifest_compare.py"]),
        ("test mouse_edge_summary", [py, "tools/test_mouse_edge_summary.py"]),
        (
            "validate cloud fixtures",
            [py, "tools/build_cloud_fixtures.py", "--manifest", "cloud/fixtures/manifest.json", "--validate-only"],
        ),
        (
            "archived HD map smoke matrix",
            [
                py,
                "tools/hd_map_smoke_matrix.py",
                "--captures-root",
                "cloud/fixtures/evidence/hd-map/runs",
                "--patch-report-json",
                "cloud/fixtures/evidence/hd-map/patch-stage-report.json",
                "--require-pass",
            ],
        ),
        ("git diff check", ["git", "diff", "--check"]),
    ]

    failures = check_no_tracked_exes()
    for label, command in checks:
        failures += 1 if run_command(label, command) else 0
    print("== wiki lint")
    print("wiki_lint.py is intentionally not part of cloud_check yet; current wiki-link repair is a separate task.")
    return 2 if failures else 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["cloud"], default="cloud")
    return parser.parse_args()


def main() -> int:
    parse_args()
    return run_cloud_mode()


if __name__ == "__main__":
    raise SystemExit(main())
