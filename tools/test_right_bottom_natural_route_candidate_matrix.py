#!/usr/bin/env python3
"""Tests for right_bottom_natural_route_candidate_matrix.py."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import right_bottom_natural_route_candidate_matrix as matrix


BASELINE_LOG = (
    "route-injects load slot 0, waits for gameplay redraw, then dumps dword_5202E0\n"
    "SURFDUMP_LOADSAVE selected_arg=0 selected_global=0 accept=1 choice=5 gd=04140030\n"
    "SURFDUMP_PLAYGAME gd=04140030 map=(100,100) scroll=(10,17) surface=0413c8c0 size=(640,480)\n"
    "NOWNER_MAP_TILE map=(15,21) mouse=(352,272) selected=-1 current=0 "
    "NOWNER_BUILDING_TILE map=(15,21) tile=32768 index=0 owner=0 mode=2 active=0 flags=0x00 "
    "NOWNER_CASTLE_OVERVIEW_ENTRY ret=0041ed6f castle_index=0 "
    "NOWNER_OWNER_FLAG_TEST owner=041bc71a owner_flag=0x00 bit2=0 bit1=0 bit8=0 "
    "NOWNER_OWNER_DESC_RESULT_SURFDUMP_READY result=0 surface=0a2fed90 size=(800,600) "
    "SURFDUMP_READY SURFDUMP_HOST_READY\n"
)
SLOT2_LOG = (
    "route-injects load slot 2, waits for gameplay redraw, then dumps dword_5202E0\n"
    "SURFDUMP_LOADSAVE selected_arg=2 selected_global=2 accept=1 choice=5 gd=038c0030\n"
    "SURFDUMP_PLAYGAME gd=038c0030 map=(50,50) scroll=(39,42) surface=038bc8b0 size=(640,480)\n"
    "NOWNER_MAP_TILE map=(43,45) mouse=(352,272) selected=-1 current=0 "
    "SURFDUMP_READY SURFDUMP_HOST_READY\n"
)
SLOT5_LOG = (
    "route-injects load slot 5, waits for gameplay redraw, then dumps dword_5202E0\n"
    "SURFDUMP_LOAD_COORD seq=0 choice=5 entry=0x000efa5d ex=232 ey=228 mouse=(320,276) selected=0 accept=0\n"
)


def record(save: str, index: int, x: int, y: int, flags: int) -> dict[str, object]:
    return {
        "save": save,
        "block_offset": 509690,
        "record_index": index,
        "x": x,
        "y": y,
        "owner": index,
        "byte_4": 2,
        "flags_1a0": flags,
        "flags_1a0_hex": f"0x{flags:02X}",
        "flags_1a4": 0,
        "flags_1a4_hex": "0x00",
        "bit2": flags & 0x02,
        "bit1": flags & 0x01,
        "bit8": flags & 0x08,
        "action_eligible": bool(flags & 0x02),
    }


def write_save_scan(path: Path, *, include_slot5_route_candidate: bool = True) -> Path:
    slot0 = [record(r"C:\Clash\save\0.dat", 0, 14, 20, 0x00)]
    slot2 = [
        record(r"C:\Clash\save\2.dat", 0, 44, 46, 0x01),
        record(r"C:\Clash\save\2.dat", 1, 1, 23, 0x16),
    ]
    slot5 = [record(r"C:\Clash\save\5.dat", 0, 14, 20, 0x0B if include_slot5_route_candidate else 0x01)]
    blocks = []
    for save, rows in (
        (r"C:\Clash\save\0.dat", slot0),
        (r"C:\Clash\save\2.dat", slot2),
        (r"C:\Clash\save\5.dat", slot5),
    ):
        bit2 = [row for row in rows if row["action_eligible"]]
        blocks.append(
            {
                "save": save,
                "plausible": True,
                "active_records": rows,
                "records_with_bit2": bit2,
                "records_with_bit2_count": len(bit2),
            }
        )
    payload = {
        "passed": True,
        "plausible_blocks": blocks,
        "records_with_bit2": [
            row
            for block in blocks
            for row in block["records_with_bit2"]
        ],
        "summary": {"action_eligible_record_count": sum(len(block["records_with_bit2"]) for block in blocks)},
    }
    output = path / "save-scan.json"
    output.write_text(json.dumps(payload), encoding="utf-8")
    return output


def write_run(
    root: Path,
    name: str,
    *,
    load_slot: int,
    log_text: str,
    passed: bool,
    timed_out: bool = False,
) -> Path:
    run = root / name
    run.mkdir()
    (run / "summary.json").write_text(
        json.dumps(
            {
                "Passed": passed,
                "TimedOut": timed_out,
                "HiddenDesktop": True,
                "UseDdrawProxy": True,
                "Stage": matrix.EXPECTED_STAGE,
                "ExtraProbeTemplate": f"C:/repo/{matrix.EXPECTED_PROBE}",
                "CandidateSha256": "D3FF",
                "LoadSlot": load_slot,
                "Av": False,
                "PngPath": str(run / "surface.png"),
            }
        ),
        encoding="utf-8",
    )
    (run / "cdb-surface-dump.log").write_text(log_text, encoding="utf-8")
    return run


def write_fixture(root: Path, *, slot5_log: str = SLOT5_LOG, slot2_log: str = SLOT2_LOG, include_slot5: bool = True) -> dict[str, Path]:
    return {
        "save": write_save_scan(root, include_slot5_route_candidate=include_slot5),
        "baseline": write_run(root, "baseline", load_slot=0, log_text=BASELINE_LOG, passed=True),
        "slot2": write_run(root, "slot2", load_slot=2, log_text=slot2_log, passed=True),
        "slot5": write_run(root, "slot5", load_slot=5, log_text=slot5_log, passed=False, timed_out=True),
    }


def build(paths: dict[str, Path]) -> dict[str, object]:
    return matrix.build_report(paths["save"], paths["baseline"], paths["slot2"], paths["slot5"])


def test_passes_current_candidate_shape() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        report = build(write_fixture(Path(tmp)))
    assert report["passed"], report
    summary = report["summary"]
    assert summary["route_compatible_candidate"]["save_slot"] == 5
    assert summary["route_compatible_candidate"]["record_index"] == 0
    assert summary["slot2_status"]["status"] == "loads_but_click_misses_castle"
    assert summary["slot5_status"]["status"] == "timeout_before_loadsave"
    assert report["promotion_ready"] is False


def test_fails_without_route_compatible_slot5_record() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        report = build(write_fixture(Path(tmp), include_slot5=False))
    assert not report["passed"]
    assert any("no action-eligible save record matches" in failure for failure in report["failures"])


def test_fails_when_slot5_no_longer_times_out_before_loadsave() -> None:
    slot5_loaded = SLOT5_LOG + (
        "SURFDUMP_LOADSAVE selected_arg=5 selected_global=5 accept=1 choice=5 gd=038c0030\n"
        "SURFDUMP_PLAYGAME gd=038c0030 map=(100,100) scroll=(10,17) surface=038bc8b0 size=(640,480)\n"
    )
    with tempfile.TemporaryDirectory() as tmp:
        paths = write_fixture(Path(tmp), slot5_log=slot5_loaded)
        report = build(paths)
    assert not report["passed"]
    assert any("slot5 exploratory status" in failure for failure in report["failures"])


def test_fails_when_slot2_click_no_longer_misses() -> None:
    slot2_hits = SLOT2_LOG + "NOWNER_BUILDING_TILE map=(43,45) tile=32768 index=1 owner=1 mode=2 active=0 flags=0x16\n"
    with tempfile.TemporaryDirectory() as tmp:
        report = build(write_fixture(Path(tmp), slot2_log=slot2_hits))
    assert not report["passed"]
    assert any("slot2 exploratory status" in failure for failure in report["failures"])


def test_cli_writes_outputs_and_requires_pass() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        paths = write_fixture(root)
        output_json = root / "out.json"
        output_md = root / "out.md"
        result = subprocess.run(
            [
                sys.executable,
                str(Path(matrix.__file__)),
                "--save-scan-json",
                str(paths["save"]),
                "--baseline-run",
                str(paths["baseline"]),
                "--slot2-run",
                str(paths["slot2"]),
                "--slot5-run",
                str(paths["slot5"]),
                "--write-json",
                str(output_json),
                "--write-markdown",
                str(output_md),
                "--require-pass",
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        assert output_json.exists()
        assert output_md.exists()


def run_tests() -> None:
    test_passes_current_candidate_shape()
    test_fails_without_route_compatible_slot5_record()
    test_fails_when_slot5_no_longer_times_out_before_loadsave()
    test_fails_when_slot2_click_no_longer_misses()
    test_cli_writes_outputs_and_requires_pass()


if __name__ == "__main__":
    run_tests()
    print("right_bottom_natural_route_candidate_matrix tests passed")
