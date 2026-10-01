#!/usr/bin/env python3
"""Run public source-only checks without retail game inputs."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(label: str, command: list[str]) -> int:
    print(f"== {label}")
    result = subprocess.run(command, cwd=ROOT, text=True)
    print(f"{label}: {'PASS' if result.returncode == 0 else 'FAIL'}")
    return result.returncode


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["cloud"], default="cloud")
    parser.parse_args()

    py = sys.executable
    checks = [
        ("public boundary", [py, "tools/check-public-boundary.py"]),
        ("launcher core", [py, "tools/test_launcher_core.py"]),
        ("launcher policy", [py, "tools/test_launcher_policy_guard.py"]),
        ("patch resolution", [py, "tools/test_patch_resolution.py"]),
        ("patch definition guard", [py, "tools/test_patch_definition_guard.py"]),
        ("resolution manifest guard", [py, "tools/test_resolution_manifest_guard.py"]),
        ("stable stage guard", [py, "tools/test_stable_stage_guard.py"]),
        ("git diff check", ["git", "diff", "--check"]),
    ]

    failures = sum(1 for label, command in checks if run(label, command))
    return 2 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
