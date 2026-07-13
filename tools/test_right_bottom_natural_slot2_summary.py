#!/usr/bin/env python3
"""Fixture tests for right_bottom_natural_slot2_summary.py."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import right_bottom_natural_slot2_summary as summary


GOOD_LOG = """\
SURFDUMP_LOADSAVE selected_arg=2 selected_global=2 accept=1 choice=5 gd=04140030
SURFDUMP_PLAYGAME gd=04140030 map=(50,50) scroll=(7,9) surface=0321c958 size=(640,480)
RBNAT_SLOT2_TARGET gd=04140030 record=1 record_ptr=041bc8ed pos=(1,23) owner=1 mode=2 flags=0x16 flag_1a4=0x00 tile=32769 map=(50,50) player=0 minimap_active=1 surface=0a07ee10 size=(800,600)
RBNAT_MINIMAP_INPUT origin=(586,16) scale=4 target=(593,103) expected_scroll=(0,20) formula=(origin+7,origin+7+20*scale) raw=(00009440,000019c0)
RBNAT_MINIMAP_RESULT scroll=(0,20) target=(0,20) button0=0x80 click=00000001
NOWNER_FORCE_MAP_CASTLE_CLICK screen=(96,224) expected_map=(1,23) expected_scroll=(0,20) raw=(00001800,00003800)
NOWNER_MAP_TILE map=(1,23) mouse=(96,224) selected=-1 current=0
NOWNER_REARM_MAP_COMMIT map=(1,23) mouse=(96,224)
NOWNER_BUILDING_TILE map=(1,23) tile=32769 index=1 record_ptr=041bc8ed owner=1 mode=2 active=1 flags=0x16
NOWNER_CASTLE_OVERVIEW_ENTRY ret=0041ed6f castle_index=1 expected_index=1 main_surface=0a07ee10 size=(800,600)
NOWNER_CASTLE_OVERVIEW_POST_DRAW overview_surface=0a3ab478 size=(640,480) owner_screen=041bc8ed
NOWNER_CASTLE_HITMAP_SAMPLE surface=0a3ab478 size=(640,480) base=0a430030 native=(151,306) native_sample=0xfe expected_raw=254
NOWNER_CASTLE_CMD99_TARGET native=(151,306) raw=(000025c0,00004c80)
NOWNER_CASTLE_HIT raw_hit=254 adjusted=6 expected_raw=254
NOWNER_CASTLE_DESCRIPTOR command=99 callback=00433c20 owner_screen=041bc8ed
NOWNER_CASTLE_CMD99_GATE gate_before=1 forced_gate=0
NOWNER_CASTLE_CALLBACK callback=00433c20 eax_arg=041bc8ed command=99
NOWNER_433C20_ENTRY ret=0042262e owner_arg=041bc8ed expected_owner=041bc8ed owner_flag=0x16 d532150_before=00000000 surface=0a07ee10 size=(800,600)
NOWNER_OWNER_FLAG_TEST owner=041bc8ed owner_flag=0x16 bit2=2 bit1=0 bit8=0
NOWNER_WRITE_532154 continue_full ret=00422020 d532150=041bc8ed d53214c=00000001 d532154=0a016110 owner_flag=0x16
NOWNER_OWNER_SCREEN_DESC_DRAW list=00514fc0 d0=(39,426 cb=004338c0) d1=(155,426 cb=004338e0) d2=(272,426 cb=00433a40) surface=0a07ee10 size=(800,600)
NOWNER_FORCE_OWNER_DESC_CLICK native=(180,440) raw=(00002d00,00006e00) d1=(155,426 cb=004338e0) owner=041bc8ed owner_flag=0x16
NOWNER_HITTEST_ENTRY count=2 desc=00514ff5 xy=(155,426) flags=0x01 hit=004338e0 mouse=(180,440) click=00000001 button0=0x80
NOWNER_DESCRIPTOR_CALLBACK desc=00514ff5 xy=(155,426) flags=0x01 callback=004338e0 mouse=(180,440)
NOWNER_4338E0_ENTRY ret=00419c60 eax_desc=00514ff5 owner=041bc8ed owner_flag=0x16 d532218=00000000 d5322c8=0 surface=0a07ee10 size=(800,600)
NOWNER_RELEASE_OWNER_DESC_CLICK before_d544d04=00000001 before_button0=0x80 after_d544d04=00000000 after_button0=0x00 raw=(00002d00,00006e00) reason=post_4338e0_entry
NOWNER_4338E0_AFTER_SELECT owner=041bc8ed owner_flag=0x16 d532218=00000000 d5322c8=0 eax=00000001
NOWNER_4338E0_AFTER_GATE owner=041bc8ed owner_flag=0x16 surface=0a07ee10 size=(800,600)
NOWNER_4338E0_POST_PUMP owner=041bc8ed owner_flag=0x16 surface=0a07ee10 size=(800,600)
NOWNER_ACTION_CALL_STOCK target=00435bc0 owner_arg=041bc8ed owner_global=041bc8ed owner_flag=0x16 surface=0a07ee10 size=(800,600) nativecenter_wrapper=0
NOWNER_OWNER_435BC0_ENTRY ret=00433919 owner_arg=041bc8ed d532218_before=00000000 d5322c8_before=0 surface=0a07ee10 size=(800,600) direct_stock=1
RBUI_DESC_SWITCH seq=0 ret=004347f0 eax=00515130 d5202e0=0a07ee10 sz=(800,600)
RBUI_VIEWPORT_SWITCH seq=0 ret=00435120 obj=00544cd8 meta=005196a0 meta_is_map=1 meta_is_menu=0
RBUI_PANEL_DRAW seq=0 ret=00435c10 d5202e0=0a07ee10 sz=(800,600) selected=0 action=0
RBUI_GRID_DRAW seq=0 ret=00435c20 d532218=041bc8ed d53221c=00000000 selected=0 list0=1 d5202e0=0a07ee10 sz=(800,600)
RBUI_STATUS_DRAW seq=0 ret=00435c30 d532218=041bc8ed selected=0 surface=0a07ee10 size=(800,600)
RBNAT_STATUS_COMPOSE_ENTER hook=004352b3 cave=005132e0 return=004352b8 surface=0a07ee10 size=(800,600) src_ltrb=(401,288,593,357) dst=(586,528)
RBNAT_STATUS_COMPOSE_DONE return=004352b8 surface=0a07ee10 size=(800,600)
RBUI_ACTION_BOX seq=0 ret=00435c40 d532218=041bc8ed d5202e0=0a07ee10 sz=(800,600) box_ltrb=(285,350,450,425)
RBNAT_ACTION_COMPOSE_ENTER hook=00435da5 cave=00513e80 return=00435daa surface=0a07ee10 size=(800,600) src_ltrb=(285,350,450,425) dst=(285,524)
RBNAT_ACTION_COMPOSE_DONE return=00435daa surface=0a07ee10 size=(800,600) base=0a320030 bytes=480000 status_state=2 action_state=2 panel_draws=1 grid_draws=1 status_draws=1 action_draws=1 desc_switches=1 viewport_switches=1
SURFDUMP_READY redraw_seq=992 surface=0a07ee10 size=(800,600) base=0a320030 bytes=480000
SURFDUMP_HOST_READY
"""


def make_run(root: Path, log: str = GOOD_LOG, **summary_overrides: object) -> Path:
    run_dir = root / "cdb-surface-dump-fixture"
    run_dir.mkdir(parents=True)
    data: dict[str, object] = {
        "Passed": True,
        "Error": None,
        "LaunchMode": "hidden-desktop",
        "HiddenDesktop": True,
        "AllowVisibleDesktop": False,
        "TimedOut": False,
        "StoppedAfterDump": True,
        "HostDumpedMemory": True,
        "Stage": summary.EXPECTED_STAGE,
        "InputSha256": summary.EXPECTED_INPUT_SHA256,
        "CandidateSha256": summary.EXPECTED_CANDIDATE_SHA256,
        "LoadSlot": 2,
        "UseDdrawProxy": True,
        "NoSkipStartAnims": False,
        "FastForwardStartAnims": True,
        "ForceVisibleEdges": False,
        "PostOwnerForceVisibleSeven": False,
        "SkipMapValidation": True,
        "LateLoadSlotForcingOnly": True,
        "ExtraProbeTemplate": str(summary.DEFAULT_PROBE),
        "Surface": {
            "RedrawSeq": 992,
            "Surface": "0a07ee10",
            "Width": 800,
            "Height": 600,
            "Base": "0a320030",
            "Bytes": 480000,
        },
        "RawBytes": 480000,
        "PngPath": str(run_dir / "surface.png"),
    }
    data.update(summary_overrides)
    (run_dir / "summary.json").write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    (run_dir / "cdb-surface-dump.log").write_text(log, encoding="utf-8")
    (run_dir / "surface.png").write_bytes(b"fixture")
    return run_dir


def test_good_run_passes_and_preserves_evidence_limits() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        report = summary.analyze_run(make_run(Path(tmp)))
    assert report["passed"] is True, report["failures"]
    assert report["status"] == "pass"
    assert report["proof_class"] == summary.PROOF_CLASS
    assert report["facts"]["target"]["position"] == [1, 23]
    assert report["facts"]["target"]["flags"] == 0x16
    assert report["facts"]["minimap"]["target"] == [593, 103]
    assert report["facts"]["compose_done"]["viewport_switches"] == 1
    limits = report["evidence_limits"]
    assert limits["owner_flag_forced"] is False
    assert limits["scroll_forced"] is False
    assert limits["command_gate_forced"] is False
    assert limits["direct_route_forced"] is False
    assert limits["debugger_forced_coordinates"] is True
    assert limits["selection_reset_forced"] is True
    assert limits["real_input_proven"] is False


def test_wrong_record_flag_fails_closed() -> None:
    bad_log = GOOD_LOG.replace(
        "record=1 record_ptr=041bc8ed pos=(1,23) owner=1 mode=2 flags=0x16",
        "record=1 record_ptr=041bc8ed pos=(1,23) owner=1 mode=2 flags=0x15",
        1,
    )
    with tempfile.TemporaryDirectory() as tmp:
        report = summary.analyze_run(make_run(Path(tmp), bad_log))
    assert report["passed"] is False
    assert "slot2_record1_target_fact_mismatch" in report["failures"]


def test_loadsave_requires_slot2_and_verified_load_choice() -> None:
    wrong_choice = GOOD_LOG.replace("choice=5", "choice=2", 1)
    with tempfile.TemporaryDirectory() as tmp:
        report = summary.analyze_run(make_run(Path(tmp), wrong_choice))
    assert report["passed"] is False
    assert "loadsave_not_consistently_slot2" in report["failures"]

    wrong_selected = GOOD_LOG.replace(
        "selected_arg=2 selected_global=2 accept=1 choice=5",
        "selected_arg=2 selected_global=1 accept=1 choice=5",
        1,
    )
    with tempfile.TemporaryDirectory() as tmp:
        report = summary.analyze_run(make_run(Path(tmp), wrong_selected))
    assert report["passed"] is False
    assert "loadsave_not_consistently_slot2" in report["failures"]


def test_missing_or_misordered_compose_marker_fails_closed() -> None:
    missing = GOOD_LOG.replace(
        "RBNAT_STATUS_COMPOSE_DONE return=004352b8 surface=0a07ee10 size=(800,600)\n",
        "",
    )
    with tempfile.TemporaryDirectory() as tmp:
        report = summary.analyze_run(make_run(Path(tmp), missing))
    assert report["passed"] is False
    assert any("RBNAT_STATUS_COMPOSE_DONE" in failure for failure in report["failures"])

    first = GOOD_LOG.index("RBUI_PANEL_DRAW")
    second = GOOD_LOG.index("RBUI_GRID_DRAW")
    panel_line_end = GOOD_LOG.index("\n", first) + 1
    grid_line_end = GOOD_LOG.index("\n", second) + 1
    panel_line = GOOD_LOG[first:panel_line_end]
    grid_line = GOOD_LOG[second:grid_line_end]
    misordered = GOOD_LOG[:first] + grid_line + panel_line + GOOD_LOG[grid_line_end:]
    with tempfile.TemporaryDirectory() as tmp:
        report = summary.analyze_run(make_run(Path(tmp), misordered))
    assert report["passed"] is False
    assert "missing_ordered_marker:RBUI_GRID_DRAW" in report["failures"]


def test_visible_fallback_or_wrong_profile_fails_closed() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        report = summary.analyze_run(
            make_run(
                Path(tmp),
                AllowVisibleDesktop=True,
                LaunchMode="visible-desktop",
                LateLoadSlotForcingOnly=False,
            )
        )
    assert report["passed"] is False
    assert "profile_check_failed:hidden_launch_mode" in report["failures"]
    assert "profile_check_failed:visible_fallback_disabled" in report["failures"]
    assert "profile_check_failed:late_load_slot_forcing_only" in report["failures"]


def test_static_guard_rejects_forbidden_mutations_and_control_flow() -> None:
    original = summary.DEFAULT_PROBE.read_text(encoding="utf-8")
    bad_lines = (
        "eb @$t6+0n416 16",       # saved owner flag
        "ed @$t5+0n140008 0",     # map scroll
        "r eax=1",                # command-gate forcing
        "r eip=00433c20",         # direct route
        "ed 00532210 1",          # modal exit/action state
    )
    for index, line in enumerate(bad_lines):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / f"bad-{index}.cdb"
            path.write_text(original + "\n" + line + "\n", encoding="utf-8")
            guard = summary.guard_probe(path)
        assert guard["passed"] is False, (line, guard)
        assert guard["failures"], line


def test_runtime_forcing_marker_fails_closed() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        report = summary.analyze_run(make_run(Path(tmp), GOOD_LOG + "forced_gate=1\n"))
    assert report["passed"] is False
    assert "forced_gate=1" in report["runtime_forbidden_hits"]


def test_cli_writes_json_and_markdown_and_require_pass() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        run_dir = make_run(root)
        out_json = root / "out" / "summary.json"
        out_md = root / "out" / "summary.md"
        result = subprocess.run(
            [
                sys.executable,
                str(Path(summary.__file__)),
                str(run_dir),
                "--write-json",
                str(out_json),
                "--write-markdown",
                str(out_md),
                "--require-pass",
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        assert json.loads(out_json.read_text(encoding="utf-8"))["passed"] is True
        markdown = out_md.read_text(encoding="utf-8")
        assert "Overall: **PASS**" in markdown
        assert "real_input_proven`" in markdown


def test_cli_require_pass_returns_two_for_failure() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        run_dir = make_run(Path(tmp), GOOD_LOG.replace("forced_gate=0", "forced_gate=1"))
        result = subprocess.run(
            [sys.executable, str(Path(summary.__file__)), str(run_dir), "--require-pass"],
            text=True,
            capture_output=True,
            check=False,
        )
    assert result.returncode == 2, result.stdout + result.stderr


def run_tests() -> None:
    test_good_run_passes_and_preserves_evidence_limits()
    test_wrong_record_flag_fails_closed()
    test_loadsave_requires_slot2_and_verified_load_choice()
    test_missing_or_misordered_compose_marker_fails_closed()
    test_visible_fallback_or_wrong_profile_fails_closed()
    test_static_guard_rejects_forbidden_mutations_and_control_flow()
    test_runtime_forcing_marker_fails_closed()
    test_cli_writes_json_and_markdown_and_require_pass()
    test_cli_require_pass_returns_two_for_failure()


if __name__ == "__main__":
    run_tests()
    print("right_bottom_natural_slot2_summary tests passed")
