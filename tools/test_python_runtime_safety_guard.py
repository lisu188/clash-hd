#!/usr/bin/env python3
"""Fixture tests for python_runtime_safety_guard.py."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "python_runtime_safety_guard.py"
sys.path.insert(0, str(ROOT / "tools"))

import python_runtime_safety_guard  # noqa: E402


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


def test_unclassified_risky_helper_fails(fixture: Path) -> None:
    write(fixture / "tools" / "unsafe_helper.py", "import subprocess\nsubprocess.Popen(['x'])\n")
    args = type("Args", (), {"root": fixture, "tools_dir": Path("tools")})()
    guard = python_runtime_safety_guard.build_guard(args)
    assert guard["passed"] is False, guard
    assert any("unsafe_helper.py" in failure for failure in guard["failures"]), guard


def test_gated_and_exempt_helpers_pass(fixture: Path) -> None:
    write(fixture / "tools" / "mouse_path_probe.py", "import ctypes\nuser32.SendInput(1, None, 0)\n")
    write(fixture / "tools" / "raw_sendinput_click.py", "import ctypes\nuser32.SendInput(1, None, 0)\n")
    write(fixture / "tools" / "battle_visible_input_summary.py", "SENDINPUT_NAME = 'raw-sendinput-click.json'\n")
    write(fixture / "tools" / "process_hygiene_guard.py", "import ctypes\nctypes.WinDLL('kernel32')\n")
    write(fixture / "tools" / "repo_test_sweep.py", "import subprocess\nsubprocess.run(['python', 'test_probe.py'])\n")
    write(fixture / "tools" / "hd_soak_dry_run_plan.py", "import subprocess\nsubprocess.run(['powershell.exe', '-File', 'run_hd_soak.ps1'])\n")
    write(
        fixture / "tools" / "hd_soak_intro_skip_rerun_readiness.py",
        "APPROVAL = 'visible runtime PostMessage intro skip only in command text'\n",
    )
    write(fixture / "tools" / "right_bottom_slot_fixture_script_guard.py", "PATTERN = 'Start-Process SendInput'\n")
    write(fixture / "tools" / "test_probe.py", "import subprocess\nsubprocess.run(['x'])\n")
    args = type("Args", (), {"root": fixture, "tools_dir": Path("tools")})()
    guard = python_runtime_safety_guard.build_guard(args)
    assert guard["passed"] is True, guard
    classes = {record["path"]: record["classification"] for record in guard["records"]}
    assert classes["tools/mouse_path_probe.py"] == "manual_visible_runtime_gated", classes
    assert classes["tools/raw_sendinput_click.py"] == "manual_visible_runtime_gated", classes
    assert classes["tools/battle_visible_input_summary.py"] == "exempt", classes
    assert classes["tools/process_hygiene_guard.py"] == "exempt", classes
    assert classes["tools/repo_test_sweep.py"] == "exempt", classes
    assert classes["tools/hd_soak_dry_run_plan.py"] == "exempt", classes
    assert classes["tools/hd_soak_intro_skip_rerun_readiness.py"] == "exempt", classes
    assert classes["tools/right_bottom_slot_fixture_script_guard.py"] == "exempt", classes
    assert classes["tools/test_probe.py"] == "test_fixture", classes


def test_cli_writes_outputs_and_fails_closed(fixture: Path) -> None:
    write(fixture / "tools" / "unsafe_helper.py", "import ctypes\nuser32.PostMessageW(0, 0, 0, 0)\n")
    out_json = fixture / "out" / "guard.json"
    out_md = fixture / "out" / "guard.md"
    result = run_script(
        fixture,
        "--root",
        str(fixture),
        "--write-json",
        str(out_json),
        "--write-markdown",
        str(out_md),
        "--require-pass",
    )
    assert result.returncode == 2, result.stdout + result.stderr
    assert json.loads(out_json.read_text(encoding="utf-8"))["passed"] is False
    assert "Python Runtime Safety Guard" in out_md.read_text(encoding="utf-8")


def run_tests() -> None:
    fixture = ROOT / ".codex-loop" / "tmp-tests" / "python-runtime-safety-fixture"
    shutil.rmtree(fixture, ignore_errors=True)
    fixture.mkdir(parents=True)
    try:
        test_unclassified_risky_helper_fails(fixture / "unsafe")
        test_gated_and_exempt_helpers_pass(fixture / "gated")
        test_cli_writes_outputs_and_fails_closed(fixture / "cli")
    finally:
        shutil.rmtree(fixture, ignore_errors=True)


def main() -> int:
    run_tests()
    print("python runtime safety guard tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
