#!/usr/bin/env python3
"""Fixture tests for hd_endurance_next_actions.py."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import hd_endurance_next_actions as next_actions


def write_json(path: Path, data: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="ascii")
    return path


def checklist_fixture(*, complete: bool = False) -> dict[str, Any]:
    if complete:
        return {
            "full_game_complete": True,
            "counts": {"total": 14, "passed": 14, "blocked": 0, "missing": 0},
            "next_milestone": None,
            "requirements": [],
        }
    return {
        "full_game_complete": False,
        "counts": {"total": 14, "passed": 4, "blocked": 6, "missing": 4},
        "next_milestone": {
            "id": "short2_menu_idle_soak",
            "title": "First short2 menu-idle soak passes",
            "next_probe": "run the approval-gated short2 menu-idle soak on the protected stage",
        },
        "requirements": [
            {
                "id": "short2_menu_idle_soak",
                "passed": False,
                "status": "blocked",
                "category": "endurance",
                "summary": "short2 visible-runtime soak has not produced passing frame/process evidence",
                "next_probe": "run the approval-gated short2 menu-idle soak on the protected stage",
            },
            {
                "id": "stable_menu_real_input",
                "passed": False,
                "status": "blocked",
                "category": "manual input",
                "summary": "menu-load proof remains pending manual DirectInput validation",
                "next_probe": "collect approved manual menu-load proof or keep promotion blocked",
            },
        ],
    }


def args_for(path: Path) -> argparse.Namespace:
    return argparse.Namespace(checklist_json=path)


def test_short2_next_action_is_visible_approval_gated() -> None:
    with tempfile.TemporaryDirectory() as directory:
        checklist_path = write_json(Path(directory) / "checklist.json", checklist_fixture())
        report = next_actions.build_report(args_for(checklist_path))
        action = report["next_action"]
        assert report["passed"] is True
        assert report["status"] == "waiting_for_explicit_visible_runtime_approval"
        assert action["id"] == "run_short2_menu_idle_soak"
        assert action["requires_visible_runtime"] is True
        assert action["requires_explicit_user_approval"] is True
        assert "-Execute -AllowVisibleRuntime" in action["exact_runtime_command"]
        assert "-ReportJson captures\\current\\hd-soak-short2-menu-idle-current.json" in action["exact_runtime_command"]
        assert "-ReportMarkdown captures\\current\\hd-soak-short2-menu-idle-current.md" in action["exact_runtime_command"]
        assert "-Execute" not in action["safe_dry_run_command"]
        assert "hd-soak-short2-menu-idle-current.json" in action["safe_dry_run_command"]
        assert "hd-soak-short2-menu-idle-guard-current.json" in " ".join(action["post_run_validation"])
        assert "hd-soak-short2-menu-idle-triage-current.json" in " ".join(action["post_run_validation"])
        assert r"C:\Clash\clash95.exe" in action["must_not_modify"]


def test_missing_checklist_fails_closed() -> None:
    report = next_actions.build_report(args_for(Path("does-not-exist.json")))
    assert report["passed"] is False
    assert report["next_action"] is None
    assert report["failures"]


def test_complete_checklist_switches_to_release_audit() -> None:
    with tempfile.TemporaryDirectory() as directory:
        checklist_path = write_json(Path(directory) / "checklist.json", checklist_fixture(complete=True))
        report = next_actions.build_report(args_for(checklist_path))
        assert report["passed"] is True
        assert report["status"] == "release_complete_pending_audit"
        assert report["next_action"]["id"] == "release_audit"
        assert report["next_action"]["requires_visible_runtime"] is False


def test_cli_writes_outputs() -> None:
    with tempfile.TemporaryDirectory() as directory:
        tmp = Path(directory)
        checklist_path = write_json(tmp / "checklist.json", checklist_fixture())
        json_out = tmp / "next.json"
        md_out = tmp / "next.md"
        script = Path(__file__).resolve().parent / "hd_endurance_next_actions.py"
        result = subprocess.run(
            [
                sys.executable,
                str(script),
                "--checklist-json",
                str(checklist_path),
                "--write-json",
                str(json_out),
                "--write-markdown",
                str(md_out),
                "--require-pass",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        assert json_out.exists()
        assert md_out.exists()
        report = json.loads(json_out.read_text(encoding="ascii"))
        assert report["next_action"]["id"] == "run_short2_menu_idle_soak"


def run_tests() -> None:
    test_short2_next_action_is_visible_approval_gated()
    test_missing_checklist_fails_closed()
    test_complete_checklist_switches_to_release_audit()
    test_cli_writes_outputs()


if __name__ == "__main__":
    run_tests()
    print("hd_endurance_next_actions tests passed")
