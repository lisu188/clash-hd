#!/usr/bin/env python3
"""Cross-checks that the HD validation drivers stay in sync with the checklist.

The Windows Sandbox driver is PowerShell (not runnable on Linux), so these are
text-level invariants: both drivers must cover all five required target IDs and
the three candidate stages, and must keep their visible-runtime approval guards.
"""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import manual_directinput_checklist as checklist  # noqa: E402

SANDBOX = ROOT / "scripts" / "smoke" / "run_clash_hd_full_validation.ps1"
LINUX_SH = ROOT / "scripts" / "smoke" / "run_clash_hd_linux_wine.sh"
LINUX_PY = ROOT / "tools" / "run_hd_linux_validation.py"
VISUAL_SMOKE = ROOT / "scripts" / "smoke" / "run_clash_visual_smoke.ps1"

STAGE_SUFFIXES = ("dynvswitch", "rightbottomcompose", "castlecenter-all")


def test_visual_smoke_single_followup_param() -> None:
    # A branch merge once duplicated the FollowupPoints parameter (parse error)
    # and left a legacy Invoke-MousePath followup block that clobbered the
    # pulse lane's rows. Keep both regressions locked out.
    text = VISUAL_SMOKE.read_text(encoding="utf-8")
    assert text.count("[string]$FollowupPoints") == 1, "duplicate FollowupPoints parameter"
    assert text.count("$followupRows = @()") == 1, "duplicate followupRows init clobbers pulse rows"


def test_sandbox_driver_uses_pulse_lane_and_authoritative_specs() -> None:
    text = SANDBOX.read_text(encoding="utf-8")
    assert "'-InputMode', 'pulse'" in text, "sandbox driver must drive the pulse lane"
    assert "'-PulseRouteSteps'" in text
    assert "manual_directinput_run_plan" in text, "followup specs must come from the run plan, not hardcoded copies"
    for legacy_args in ("'-MoveMode', 'auto'", "'-ClickMode', 'sendinput'"):
        assert legacy_args not in text, f"legacy engine-invisible input args resurfaced: {legacy_args}"


def test_linux_worker_strips_named_points() -> None:
    text = LINUX_SH.read_text(encoding="utf-8")
    assert 'p="${p##*:}"' in text, "worker must accept name:x,y aim points from the run plan"


def test_sandbox_driver_covers_all_targets() -> None:
    text = SANDBOX.read_text(encoding="utf-8")
    for item_id in checklist.REQUIRED_IDS:
        assert item_id in text, f"sandbox driver is missing target id {item_id}"
    for suffix in STAGE_SUFFIXES:
        assert suffix in text, f"sandbox driver is missing stage suffix {suffix}"


def test_sandbox_driver_has_guards() -> None:
    text = SANDBOX.read_text(encoding="utf-8")
    assert "AllowVisibleRuntime" in text
    assert "ApprovalRecord" in text
    assert "prepare_addon_flags_fixture.py" in text
    assert "run-manifest.json" in text
    # Never fabricates observations: statuses start pending, fields blank.
    assert "status = 'pending'" in text
    assert "run_clash_visual_smoke.ps1" in text


def test_linux_driver_covers_all_targets() -> None:
    text = LINUX_PY.read_text(encoding="utf-8")
    # The Python driver derives target ids from the checklist module, so assert
    # the wiring points exist rather than hardcoded ids.
    assert "REQUIRED_IDS" in text
    assert "run_clash_hd_linux_wine.sh" in text
    assert "prepare_addon_flags_fixture.py" in text


def test_linux_worker_has_guard() -> None:
    text = LINUX_SH.read_text(encoding="utf-8")
    assert "--allow-visible-runtime" in text
    assert "xdotool" in text
    assert "wine" in text


def run_tests() -> None:
    test_sandbox_driver_covers_all_targets()
    test_sandbox_driver_has_guards()
    test_linux_driver_covers_all_targets()
    test_linux_worker_has_guard()
    test_visual_smoke_single_followup_param()
    test_sandbox_driver_uses_pulse_lane_and_authoritative_specs()
    test_linux_worker_strips_named_points()


def main() -> int:
    run_tests()
    print("HD validation driver cross-checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
