#!/usr/bin/env python3
"""Fixture tests for the launcher policy guard."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "launcher_policy_guard.py"
sys.path.insert(0, str(ROOT / "tools"))

import launcher_policy_guard  # noqa: E402


GOOD_CORE = """
LAUNCH_POLICY = "user-initiated; never part of the evidence refresh"

def assert_plan_paths(plan):
    raise LauncherError("Refusing write outside candidates root")
    raise LauncherError("Refusing write inside the game directory")

def launch_game(plan, *, confirmed: bool, popen=None):
    if confirmed is not True:
        raise PermissionError("launch_game requires confirmed=True")
"""
GOOD_GUI = "def on_play(self):\n    core.launch_game(plan, confirmed=True)\n"
GOOD_RUN = "def main():\n    core.launch_game(plan, confirmed=True)\n"
GOOD_PS1 = "& $PythonFull $RunScript @LauncherArgs\nexit $LASTEXITCODE\n"
GOOD_REFRESH = "def build_refresh(args):\n    return {}\n"
GOOD_DOC = (
    "# Launcher\n\nuser-initiated launches only; the launcher is never part "
    "of the evidence refresh and never ships or downloads DLLs.\n"
)


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def make_good_fixture(root: Path) -> argparse.Namespace:
    write(root / "src/launcher/core.py", GOOD_CORE)
    write(root / "src/launcher/gui.py", GOOD_GUI)
    write(root / "src/launcher/run.py", GOOD_RUN)
    write(root / "src/launcher/presets.py", "OPTIONS = []\n")
    write(root / "scripts/launcher/run_launcher.ps1", GOOD_PS1)
    write(root / "tools/current_evidence_refresh.py", GOOD_REFRESH)
    write(root / "docs/hd/LAUNCHER.md", GOOD_DOC)
    return argparse.Namespace(
        launcher_dir=root / "src/launcher",
        scripts_dir=root / "scripts/launcher",
        refresh_script=root / "tools/current_evidence_refresh.py",
        doc=root / "docs/hd/LAUNCHER.md",
    )


def run_script(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def test_good_fixture(fixture: Path) -> None:
    args = make_good_fixture(fixture)
    guard = launcher_policy_guard.build_guard(args)
    assert guard["passed"], guard["failures"]
    assert all(check["passed"] for check in guard["checks"].values()), guard


def test_missing_confirmed_gate_fails(fixture: Path) -> None:
    args = make_good_fixture(fixture)
    write(
        fixture / "src/launcher/core.py",
        GOOD_CORE.replace("*, confirmed: bool", "confirmed=False"),
    )
    guard = launcher_policy_guard.build_guard(args)
    assert not guard["passed"], guard
    assert not guard["checks"]["core_confirmed_gate"]["passed"], guard


def test_missing_write_refusal_fails(fixture: Path) -> None:
    args = make_good_fixture(fixture)
    write(
        fixture / "src/launcher/core.py",
        GOOD_CORE.replace("Refusing write outside candidates root", "whatever"),
    )
    guard = launcher_policy_guard.build_guard(args)
    assert not guard["checks"]["core_write_refusal"]["passed"], guard


def test_unexpected_call_site_fails(fixture: Path) -> None:
    args = make_good_fixture(fixture)
    write(fixture / "src/launcher/settings.py", "core.launch_game(plan, confirmed=True)\n")
    guard = launcher_policy_guard.build_guard(args)
    assert not guard["checks"]["launch_call_sites"]["passed"], guard
    assert "settings.py" in guard["checks"]["launch_call_sites"]["summary"]["unexpected"]


def test_refresh_reference_fails(fixture: Path) -> None:
    args = make_good_fixture(fixture)
    write(
        fixture / "tools/current_evidence_refresh.py",
        GOOD_REFRESH + "# also invoke run_launcher for fun\n",
    )
    guard = launcher_policy_guard.build_guard(args)
    assert not guard["checks"]["refresh_isolation"]["passed"], guard


def test_risky_ps1_fails(fixture: Path) -> None:
    args = make_good_fixture(fixture)
    write(
        fixture / "scripts/launcher/run_launcher.ps1",
        "Start-Process -FilePath $Exe\n",
    )
    guard = launcher_policy_guard.build_guard(args)
    assert not guard["checks"]["launcher_scripts_no_risky_calls"]["passed"], guard


def test_missing_doc_phrase_fails(fixture: Path) -> None:
    args = make_good_fixture(fixture)
    write(fixture / "docs/hd/LAUNCHER.md", "# Launcher\n\nnothing to see\n")
    guard = launcher_policy_guard.build_guard(args)
    assert not guard["checks"]["doc_policy"]["passed"], guard


def test_cli_writes_outputs_and_fails_closed(fixture: Path) -> None:
    args = make_good_fixture(fixture / "good")
    out_json = fixture / "guard.json"
    out_md = fixture / "guard.md"
    completed = run_script(
        "--launcher-dir", str(args.launcher_dir),
        "--scripts-dir", str(args.scripts_dir),
        "--refresh-script", str(args.refresh_script),
        "--doc", str(args.doc),
        "--write-json", str(out_json),
        "--write-markdown", str(out_md),
        "--require-pass",
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    payload = json.loads(out_json.read_text(encoding="utf-8"))
    assert payload["passed"] is True, payload
    assert "- Overall: PASS" in out_md.read_text(encoding="utf-8")

    bad_args = make_good_fixture(fixture / "bad")
    write(fixture / "bad" / "docs/hd/LAUNCHER.md", "# nope\n")
    completed = run_script(
        "--launcher-dir", str(bad_args.launcher_dir),
        "--scripts-dir", str(bad_args.scripts_dir),
        "--refresh-script", str(bad_args.refresh_script),
        "--doc", str(bad_args.doc),
        "--write-json", str(fixture / "bad.json"),
        "--write-markdown", str(fixture / "bad.md"),
        "--require-pass",
    )
    assert completed.returncode == 2, completed.stdout + completed.stderr
    assert "- Overall: FAIL" in (fixture / "bad.md").read_text(encoding="utf-8")


def run_tests() -> None:
    fixture = ROOT / ".codex-loop" / "tmp-tests" / "launcher-policy-guard-fixture"
    shutil.rmtree(fixture, ignore_errors=True)
    fixture.mkdir(parents=True)
    try:
        test_good_fixture(fixture / "good")
        test_missing_confirmed_gate_fails(fixture / "gate")
        test_missing_write_refusal_fails(fixture / "refusal")
        test_unexpected_call_site_fails(fixture / "call-site")
        test_refresh_reference_fails(fixture / "refresh")
        test_risky_ps1_fails(fixture / "ps1")
        test_missing_doc_phrase_fails(fixture / "doc")
        test_cli_writes_outputs_and_fails_closed(fixture / "cli")
    finally:
        shutil.rmtree(fixture, ignore_errors=True)


def main() -> int:
    run_tests()
    print("launcher policy guard tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
