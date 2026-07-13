#!/usr/bin/env python3
"""Fixture tests for patch_definition_guard.py."""

from __future__ import annotations

from dataclasses import dataclass
import json
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "patch_definition_guard.py"
sys.path.insert(0, str(ROOT / "tools"))

import patch_definition_guard  # noqa: E402


@dataclass(frozen=True)
class Patch:
    group: str
    offset: int
    old_hex: str
    new_hex: str
    note: str = "fixture"


class FakeModule:
    DEFAULT_STAGE = patch_definition_guard.EXPECTED_STABLE_STAGE
    PATCHES = (
        Patch("display", 0x10, "aaaa", "bbbb"),
        Patch("input", 0x20, "cccc", "dddd"),
        Patch("right-bottom-compose-proof", 0x30, "eeee", "ffff"),
        Patch("castle-ui-center-present", 0x40, "1111", "2222"),
        Patch("castle-ui-center-present-wrapper", 0x50, "3333", "4444"),
        Patch("castle-ui-centered-input", 0x60, "5555", "6666"),
        Patch("castle-overview-center-present-wrapper", 0x70, "7777", "8888"),
        Patch("castle-overview-centered-input", 0x80, "9999", "aaaa"),
        Patch("battle-ui-center-present-wrapper", 0x90, "abab", "bcbc"),
        Patch("battle-grid-centered-input", 0xA0, "cdcd", "dede"),
        Patch("battle-ui-centered-input", 0xB0, "efef", "fafa"),
        Patch("terrain-tooltip-bottom-center", 0xC0, "0101", "0202"),
        Patch("selected-unit-command-panel-right-bottom", 0xD0, "0303", "0404"),
    )
    STAGE_GROUPS = {
        patch_definition_guard.EXPECTED_STABLE_STAGE: ("display", "input"),
        patch_definition_guard.RIGHT_BOTTOM_VALIDATION_STAGE: (
            "display",
            "input",
            "right-bottom-compose-proof",
        ),
        patch_definition_guard.TOOLTIP_BOTTOM_CENTER_STAGE: (
            "display",
            "input",
            "terrain-tooltip-bottom-center",
        ),
        patch_definition_guard.UNIT_COMMAND_PANEL_STAGE: (
            "display",
            "input",
            "selected-unit-command-panel-right-bottom",
        ),
        patch_definition_guard.HD_LAYOUT_STAGE: (
            "display",
            "input",
            "terrain-tooltip-bottom-center",
            "selected-unit-command-panel-right-bottom",
        ),
        patch_definition_guard.CASTLECENTER_STAGE: (
            "display",
            "input",
            "castle-ui-center-present",
        ),
        patch_definition_guard.CASTLECENTER_HITBOX_STAGE: (
            "display",
            "input",
            "castle-ui-center-present",
            "castle-ui-centered-input",
        ),
        patch_definition_guard.CASTLECENTER_ALL_STAGE: (
            "display",
            "input",
            "castle-ui-center-present-wrapper",
            "castle-ui-centered-input",
            "castle-overview-center-present-wrapper",
            "castle-overview-centered-input",
        ),
        patch_definition_guard.BATTLECENTER_STAGE: (
            "display",
            "input",
            "castle-ui-center-present-wrapper",
            "castle-ui-centered-input",
            "castle-overview-center-present-wrapper",
            "castle-overview-centered-input",
            "battle-ui-center-present-wrapper",
        ),
        patch_definition_guard.BATTLECENTER_INPUTPROBE_STAGE: (
            "display",
            "input",
            "castle-ui-center-present-wrapper",
            "castle-ui-centered-input",
            "castle-overview-center-present-wrapper",
            "castle-overview-centered-input",
            "battle-ui-center-present-wrapper",
            "battle-grid-centered-input",
            "battle-ui-centered-input",
        ),
    }


def run_script(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def clone_module(**updates):
    attrs = {
        "DEFAULT_STAGE": FakeModule.DEFAULT_STAGE,
        "PATCHES": FakeModule.PATCHES,
        "STAGE_GROUPS": dict(FakeModule.STAGE_GROUPS),
    }
    attrs.update(updates)
    return type("FixtureModule", (), attrs)


def test_good_fixture_passes() -> None:
    guard = patch_definition_guard.build_guard(type("Args", (), {})(), FakeModule)
    assert guard["passed"] is True, guard
    assert guard["validation_groups_in_stable"] == [], guard


def test_default_drift_fails() -> None:
    module = clone_module(DEFAULT_STAGE="display")
    guard = patch_definition_guard.build_guard(type("Args", (), {})(), module)
    assert guard["passed"] is False, guard
    assert any("DEFAULT_STAGE" in failure for failure in guard["failures"]), guard


def test_validation_leakage_fails() -> None:
    stages = dict(FakeModule.STAGE_GROUPS)
    stages[patch_definition_guard.EXPECTED_STABLE_STAGE] = (
        "display",
        "input",
        "right-bottom-compose-proof",
    )
    module = clone_module(STAGE_GROUPS=stages)
    guard = patch_definition_guard.build_guard(type("Args", (), {})(), module)
    assert guard["passed"] is False, guard
    assert any("validation-only groups leaked" in failure for failure in guard["failures"]), guard


def test_unknown_group_fails() -> None:
    stages = dict(FakeModule.STAGE_GROUPS)
    stages[patch_definition_guard.RIGHT_BOTTOM_VALIDATION_STAGE] = (
        "display",
        "input",
        "missing-group",
    )
    module = clone_module(STAGE_GROUPS=stages)
    guard = patch_definition_guard.build_guard(type("Args", (), {})(), module)
    assert guard["passed"] is False, guard
    assert any("unknown patch groups" in failure for failure in guard["failures"]), guard


def test_battlecenter_fixture_has_no_extra_groups() -> None:
    guard = patch_definition_guard.build_guard(type("Args", (), {})(), FakeModule)
    summary = guard["validation_stage_summaries"][patch_definition_guard.BATTLECENTER_STAGE]
    assert summary["missing"] == [], guard
    assert summary["unexpected"] == [], guard
    assert summary["expected_extras"] == [
        "battle-ui-center-present-wrapper",
        "castle-overview-center-present-wrapper",
        "castle-overview-centered-input",
        "castle-ui-center-present-wrapper",
        "castle-ui-centered-input",
    ], guard


def test_hd_layout_fixture_has_only_layout_groups() -> None:
    guard = patch_definition_guard.build_guard(type("Args", (), {})(), FakeModule)
    summary = guard["validation_stage_summaries"][patch_definition_guard.HD_LAYOUT_STAGE]
    assert summary["missing"] == [], guard
    assert summary["unexpected"] == [], guard
    assert summary["expected_extras"] == [
        "selected-unit-command-panel-right-bottom",
        "terrain-tooltip-bottom-center",
    ], guard


def test_overlapping_selected_patch_fails() -> None:
    patches = FakeModule.PATCHES + (Patch("input", 0x11, "bb", "cc"),)
    module = clone_module(PATCHES=patches)
    guard = patch_definition_guard.build_guard(type("Args", (), {})(), module)
    assert guard["passed"] is False, guard
    assert any("overlapping selected patches" in failure for failure in guard["failures"]), guard


def test_cli_writes_current_outputs(fixture: Path) -> None:
    out_json = fixture / "guard.json"
    out_md = fixture / "guard.md"
    result = run_script("--write-json", str(out_json), "--write-markdown", str(out_md), "--require-pass")
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(out_json.read_text(encoding="utf-8"))["passed"] is True
    assert "Patch Definition Guard" in out_md.read_text(encoding="utf-8")


def run_tests() -> None:
    fixture = ROOT / ".codex-loop" / "tmp-tests" / "patch-definition-fixture"
    shutil.rmtree(fixture, ignore_errors=True)
    fixture.mkdir(parents=True)
    try:
        test_good_fixture_passes()
        test_default_drift_fails()
        test_validation_leakage_fails()
        test_unknown_group_fails()
        test_battlecenter_fixture_has_no_extra_groups()
        test_hd_layout_fixture_has_only_layout_groups()
        test_overlapping_selected_patch_fails()
        test_cli_writes_current_outputs(fixture / "cli")
    finally:
        shutil.rmtree(fixture, ignore_errors=True)


def main() -> int:
    run_tests()
    print("patch definition guard tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
