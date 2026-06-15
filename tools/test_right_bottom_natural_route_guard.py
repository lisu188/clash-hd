#!/usr/bin/env python3
"""Tests for right_bottom_natural_route_guard.py."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import right_bottom_natural_route_guard as guard


GOOD_LOG = (
    "NOWNER_CASTLE_CMD99_GATE gate_before=1 forced_gate=1 "
    "NOWNER_CASTLE_CALLBACK callback=00433c20 eax_arg=041bc71a command=99 "
    "NOWNER_433C20_ENTRY ret=0042262e owner_arg=041bc71a owner_flag=0x00 d532150_before=00000000 surface=0a2fed90 size=(800,600) "
    "NOWNER_OWNER_FLAG_TEST owner=041bc71a owner_flag=0x00 bit2=0 bit1=0 bit8=0 "
    "NOWNER_OWNER_SCREEN_DESC_DRAW list=00514fc0 d0=(39,426 cb=004338c0) d1=(1000,426 cb=004338e0) d2=(1000,426 cb=00433a40) surface=0a2fed90 size=(800,600) "
    "NOWNER_FORCE_OWNER_DESC_CLICK native=(180,440) raw=(00002d00,00006e00) d1=(1000,426 cb=004338e0) owner=041bc71a owner_flag=0x00 "
    "NOWNER_HITTEST_ENTRY count=1 desc=00514fc0 xy=(39,426) flags=0x01 hit=004338c0 mouse=(180,440) click=00000001 button0=0x80 "
    "NOWNER_OWNER_DESC_RESULT_SURFDUMP_READY result=0 mouse=(180,440) owner=041bc71a owner_flag=0x00 surface=0a2fed90 size=(800,600) base=0a5a0030 bytes=480000 "
    "SURFDUMP_READY redraw_seq=997 surface=0a2fed90 size=(800,600) base=0a5a0030 bytes=480000 SURFDUMP_HOST_READY"
)


def write_run(root: Path, log_text: str = GOOD_LOG) -> Path:
    run = root / "run"
    run.mkdir()
    (run / "summary.json").write_text(
        json.dumps(
            {
                "Passed": True,
                "HiddenDesktop": True,
                "UseDdrawProxy": True,
                "Stage": guard.EXPECTED_STAGE,
                "ExtraProbeTemplate": f"C:/repo/{guard.EXPECTED_PROBE}",
                "CandidateSha256": "D3FF",
                "PngPath": str(run / "surface.png"),
            }
        ),
        encoding="utf-8",
    )
    (run / "cdb-surface-dump.log").write_text(log_text + "\n", encoding="utf-8")
    return run


def test_passes_for_offscreen_owner_flag_zero() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        report = guard.build_report(write_run(Path(tmp)))
    assert report["passed"], report
    assert report["state_gated_by_owner_flag"] is True
    assert report["summary"]["action_descriptor"]["x"] == 1000
    assert report["summary"]["action_route_count"] == 0


def test_fails_when_action_descriptor_is_in_bounds() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        run = write_run(Path(tmp), GOOD_LOG.replace("d1=(1000,426 cb=004338e0)", "d1=(180,426 cb=004338e0)"))
        report = guard.build_report(run)
    assert not report["passed"]
    assert any("owner-loop descriptor d1" in failure or "expected 1000" in failure for failure in report["failures"])


def test_fails_when_static_owner_loop_descriptor_model_drifts() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        run = write_run(Path(tmp), GOOD_LOG.replace("d2=(1000,426 cb=00433a40)", "d2=(1000,426 cb=00433ac0)"))
        report = guard.build_report(run)
    assert not report["passed"]
    assert any("owner-loop descriptor d2" in failure for failure in report["failures"])


def test_fails_when_owner_flag_allows_action_route() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        log = GOOD_LOG.replace("owner_flag=0x00 bit2=0 bit1=0 bit8=0", "owner_flag=0x02 bit2=2 bit1=0 bit8=0")
        run = write_run(Path(tmp), log)
        report = guard.build_report(run)
    assert not report["passed"]
    assert any("owner flag-test value" in failure or "owner flag bits" in failure for failure in report["failures"])


def test_fails_when_owner_action_renderer_rows_fire() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        run = write_run(Path(tmp), GOOD_LOG + " NOWNER_ACTION_CALL_WRAPPER ret=0040ae16 owner_arg=041bc71a")
        report = guard.build_report(run)
    assert not report["passed"]
    assert any("unexpectedly entered" in failure for failure in report["failures"])


def run_tests() -> None:
    test_passes_for_offscreen_owner_flag_zero()
    test_fails_when_action_descriptor_is_in_bounds()
    test_fails_when_static_owner_loop_descriptor_model_drifts()
    test_fails_when_owner_flag_allows_action_route()
    test_fails_when_owner_action_renderer_rows_fire()


if __name__ == "__main__":
    run_tests()
    print("right_bottom_natural_route_guard tests passed")
