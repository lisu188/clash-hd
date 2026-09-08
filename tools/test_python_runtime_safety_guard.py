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
        fixture / "tools" / "hd_soak_execution_boundary.py",
        "import subprocess\nsubprocess.run(['powershell.exe', '-Execute', '-AllowVisibleRuntime'])\n",
    )
    write(
        fixture / "tools" / "hd_soak_intro_skip_rerun_readiness.py",
        "APPROVAL = 'visible runtime PostMessage intro skip only in command text'\n",
    )
    write(fixture / "tools" / "right_bottom_slot_fixture_script_guard.py", "PATTERN = 'Start-Process SendInput'\n")
    write(fixture / "tools" / "test_probe.py", "import subprocess\nsubprocess.run(['x'])\n")
    write(
        fixture / "src" / "launcher" / "core.py",
        "import subprocess\nsubprocess.Popen(['clash95_hd_800x600.exe'])\n",
    )
    write(fixture / "src" / "launcher" / "gui.py", "def on_play(self):\n    pass\n")
    args = type("Args", (), {"root": fixture, "tools_dir": Path("tools")})()
    guard = python_runtime_safety_guard.build_guard(args)
    assert guard["passed"] is True, guard
    classes = {record["path"]: record["classification"] for record in guard["records"]}
    assert classes["src/launcher/core.py"] == "user_gated_launcher", classes
    assert classes["src/launcher/gui.py"] == "safe", classes
    assert classes["tools/mouse_path_probe.py"] == "manual_visible_runtime_gated", classes
    assert classes["tools/raw_sendinput_click.py"] == "manual_visible_runtime_gated", classes
    assert classes["tools/battle_visible_input_summary.py"] == "exempt", classes
    assert classes["tools/process_hygiene_guard.py"] == "exempt", classes
    assert classes["tools/repo_test_sweep.py"] == "exempt", classes
    assert classes["tools/hd_soak_dry_run_plan.py"] == "exempt", classes
    assert classes["tools/hd_soak_execution_boundary.py"] == "exempt", classes
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


def test_offline_report_source_passes(fixture: Path) -> None:
    path = fixture / "tools" / "hidden_soak_report_assembler.py"
    source = (ROOT / "tools" / path.name).read_text(encoding="utf-8-sig")
    write(path, source)
    record = python_runtime_safety_guard.classify_python(path, fixture)
    assert record["classification"] == "offline_report", record
    assert not record["failures"], record
    # The original false positive is report prose, not an executable API.
    assert "process_launch" in record["risk_categories"], record


def test_offline_report_name_does_not_hide_runtime_apis(fixture: Path) -> None:
    cases = {
        "subprocess_alias": "import subprocess as reports\nreports.Popen(['clash95.exe'])\n",
        "imported_alias": "from subprocess import Popen as build_report\nbuild_report(['clash95.exe'])\n",
        "input": "import ctypes\nctypes.windll.user32.SendInput(1, None, 0)\n",
        "deferred_api": "launch_later = api.CreateProcess\n",
        "fstring_expression": "report = f'{api.PostMessageW(0, 0, 0, 0)}'\n",
        "dynamic_import": "loader = __import__\nloader('subprocess')\n",
        "dynamic_lookup": "launch = getattr(api, 'Popen')\n",
        "unreviewed_import": "import multiprocessing as reports\n",
        "invalid_source": "def broken(:\n",
    }
    for case, source in cases.items():
        case_root = fixture / case
        path = case_root / "tools" / "hidden_soak_report_assembler.py"
        write(path, source)
        args = type("Args", (), {"root": case_root, "tools_dir": Path("tools")})()
        guard = python_runtime_safety_guard.build_guard(args)
        assert guard["passed"] is False, (case, guard)
        record = guard["records"][0]
        assert record["classification"] == "unclassified_risky", (case, record)
        assert record["failures"], (case, record)


def test_offline_report_review_is_path_specific(fixture: Path) -> None:
    path = fixture / "src" / "launcher" / "hidden_soak_report_assembler.py"
    write(path, "MESSAGE = 'recorded execution run (offline evidence)'\n")
    record = python_runtime_safety_guard.classify_python(path, fixture)
    assert record["classification"] == "unclassified_risky", record
    assert record["failures"], record


def run_tests() -> None:
    fixture = ROOT / ".codex-loop" / "tmp-tests" / "python-runtime-safety-fixture"
    shutil.rmtree(fixture, ignore_errors=True)
    fixture.mkdir(parents=True)
    try:
        test_unclassified_risky_helper_fails(fixture / "unsafe")
        test_gated_and_exempt_helpers_pass(fixture / "gated")
        test_cli_writes_outputs_and_fails_closed(fixture / "cli")
        test_offline_report_source_passes(fixture / "offline")
        test_offline_report_name_does_not_hide_runtime_apis(fixture / "offline-unsafe")
        test_offline_report_review_is_path_specific(fixture / "offline-path")
    finally:
        shutil.rmtree(fixture, ignore_errors=True)


def main() -> int:
    run_tests()
    print("python runtime safety guard tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
