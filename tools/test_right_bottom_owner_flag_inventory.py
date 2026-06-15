#!/usr/bin/env python3
"""Tests for right_bottom_owner_flag_inventory.py."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "right_bottom_owner_flag_inventory.py"
sys.path.insert(0, str(ROOT / "tools"))

import right_bottom_owner_flag_inventory as inventory  # noqa: E402


NATURAL_BLOCKED_LOG = (
    "NOWNER_OWNER_FLAG_TEST owner=041bc71a owner_flag=0x00 bit2=0 bit1=0 bit8=0 "
    "NOWNER_OWNER_SCREEN_DESC_DRAW list=00514fc0 "
    "d0=(39,426 cb=004338c0) d1=(1000,426 cb=004338e0) d2=(1000,426 cb=00433a40) "
    "NOWNER_OWNER_DESC_RESULT_SURFDUMP_READY result=0 mouse=(180,440) owner=041bc71a "
    "owner_flag=0x00 surface=0a2fed90 size=(800,600) SURFDUMP_READY SURFDUMP_HOST_READY"
)

FORCED_ROUTE_LOG = (
    "APPOST_OWNER_FLAG_FORCED owner=07e4c71a owner_flag_new=0x02 "
    "APPOST_ACTION_CALL desc=00511d40 owner=07e4c71a owner_flag=0x02 "
    "APPOST_OWNER_435BC0_ENTRY ret=00433919 owner_arg=07e4c71a "
    "APPOST_PANEL_DRAW_4347A0 ret=00435d84 "
    "APPOST_ACTION_BOX_435500 ret=00435d93"
)

DESCRIPTOR_ONLY_LOG = "RBUI_DESC_SWITCH ret=0040a474 eax=00511d40 d5202e0=0a07ed90 sz=(800,600)"

FIXTURE_ACTION_LOG = (
    "=== Clash95 slot5-as-slot0 fixture owner/action descriptor probe === "
    "NOWNER_CASTLE_HITMAP_SAMPLE displayed=(231,366) displayed_sample=0x0c "
    "native=(151,306) native_sample=0xfe expected_raw=254 "
    "NOWNER_CASTLE_CMD99_TARGET native=(151,306) displayed_hint=(231,366) "
    "raw=(000025c0,00004c80) "
    "NOWNER_CASTLE_HIT raw_hit=254 adjusted=6 expected_raw=254 "
    "NOWNER_OWNER_FLAG_TEST owner=043dc71a owner_flag=0x0b bit2=2 bit1=1 bit8=8 "
    "NOWNER_OWNER_SCREEN_DESC_DRAW list=00514fc0 "
    "d0=(39,426 cb=004338c0) d1=(155,426 cb=004338e0) d2=(272,426 cb=00433a40) "
    "NOWNER_4338E0_ENTRY ret=00419c60 eax_desc=00514ff5 owner=043dc71a owner_flag=0x0b "
    "NOWNER_4338E0_SURFDUMP_READY surface=0a06f030 size=(800,600)"
)


def write_run(root: Path, name: str, log_text: str) -> Path:
    run = root / name
    run.mkdir(parents=True)
    (run / "summary.json").write_text(
        json.dumps(
            {
                "HiddenDesktop": True,
                "Stage": f"stage-{name}",
                "CandidateSha256": f"SHA-{name}",
                "Surface": {"Width": 800, "Height": 600},
            }
        ),
        encoding="utf-8",
    )
    (run / "cdb-surface-dump.log").write_text(log_text + "\n", encoding="utf-8")
    return run


def run_script(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def test_inventory_classifies_current_blocker_and_forced_route(fixture: Path) -> None:
    write_run(fixture, "natural", NATURAL_BLOCKED_LOG)
    write_run(fixture, "forced", FORCED_ROUTE_LOG)
    write_run(fixture, "descriptor", DESCRIPTOR_ONLY_LOG)
    report = inventory.build_report(fixture)
    assert report["passed"], report
    assert report["natural_state_gated_count"] == 1, report
    assert report["forced_owner_action_route_count"] == 1, report
    assert report["natural_ui_descriptor_only_count"] == 1, report
    assert report["natural_action_route_count"] == 0, report
    assert report["non_natural_isolated_fixture_count"] == 0, report


def test_inventory_classifies_fixture_action_rows_as_non_natural(fixture: Path) -> None:
    fixture_run = write_run(fixture, "fixture", FIXTURE_ACTION_LOG)
    (fixture_run / "right-bottom-slot-fixture-result-summary.json").write_text(
        json.dumps(
            {
                "proof_class": "non_natural_isolated_fixture",
                "status": "owner_action_reached",
            }
        ),
        encoding="utf-8",
    )
    write_run(fixture, "natural", NATURAL_BLOCKED_LOG)
    write_run(fixture, "forced", FORCED_ROUTE_LOG)
    report = inventory.build_report(fixture)
    assert report["passed"], report
    assert report["natural_action_route_count"] == 0, report
    assert report["non_natural_isolated_fixture_count"] == 1, report
    assert report["non_natural_isolated_fixture_action_route_count"] == 1, report


def test_inventory_fails_when_natural_route_already_enters_action_rows(fixture: Path) -> None:
    write_run(fixture, "natural", NATURAL_BLOCKED_LOG + " NOWNER_ACTION_CALL_WRAPPER owner=041bc71a")
    write_run(fixture, "forced", FORCED_ROUTE_LOG)
    report = inventory.build_report(fixture)
    assert not report["passed"], report
    assert report["natural_action_route_count"] == 1, report
    assert any("non-fixture archived natural route" in failure for failure in report["failures"]), report


def test_cli_writes_outputs(fixture: Path) -> None:
    write_run(fixture, "natural", NATURAL_BLOCKED_LOG)
    write_run(fixture, "forced", FORCED_ROUTE_LOG)
    out_json = fixture / "out" / "inventory.json"
    out_md = fixture / "out" / "inventory.md"
    run = run_script(
        "--captures-root",
        str(fixture),
        "--write-json",
        str(out_json),
        "--write-markdown",
        str(out_md),
        "--require-pass",
    )
    assert run.returncode == 0, run.stdout + run.stderr
    assert json.loads(out_json.read_text(encoding="utf-8"))["passed"] is True
    assert "Right-Bottom Owner-Flag Inventory" in out_md.read_text(encoding="utf-8")


def run_tests() -> None:
    fixture = ROOT / ".codex-loop" / "tmp-tests" / "right-bottom-owner-flag-inventory"
    shutil.rmtree(fixture, ignore_errors=True)
    fixture.mkdir(parents=True)
    try:
        test_inventory_classifies_current_blocker_and_forced_route(fixture / "classifies")
        test_inventory_classifies_fixture_action_rows_as_non_natural(fixture / "fixture-action")
        test_inventory_fails_when_natural_route_already_enters_action_rows(fixture / "natural-action")
        test_cli_writes_outputs(fixture / "cli")
    finally:
        shutil.rmtree(fixture, ignore_errors=True)


def main() -> int:
    run_tests()
    print("right_bottom_owner_flag_inventory tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
