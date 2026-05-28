#!/usr/bin/env python3
"""Fixture tests for right_bottom_slot_fixture_result_summary.py."""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

import right_bottom_slot_fixture_result_summary as summary


SUCCESS_LOG = """
SURFDUMP_LOADSAVE selected_arg=0 selected_global=0 accept=1 choice=5 gd=04140030
SURFDUMP_PLAYGAME gd=04140030 map=(100,100) scroll=(10,17) surface=0413c8c0 size=(640,480)
NOWNER_CASTLE_CMD99_GATE gate_before=1 forced_gate=1
NOWNER_CASTLE_HITMAP_SAMPLE surface=0a4eb678 size=(640,480) base=0a460030 displayed=(231,366) displayed_sample=0xfe native=(151,306) native_sample=0x00 bbox_min=(77,306) bbox_min_sample=0xfe bbox_max=(237,426) bbox_max_sample=0xfe expected_raw=254
NOWNER_CASTLE_CMD99_TARGET displayed=(231,366) raw=(000039c0,00005b80)
NOWNER_CASTLE_HIT raw_hit=254 adjusted=6 expected_raw=254
NOWNER_CASTLE_CALLBACK callback=00433c20 eax_arg=041bc71a command=99
NOWNER_433C20_ENTRY ret=0042262e owner_arg=041bc71a owner_flag=0x02 d532150_before=00000000 surface=0a2fed90 size=(800,600)
NOWNER_OWNER_FLAG_TEST owner=041bc71a owner_flag=0x02 bit2=2 bit1=0 bit8=0
NOWNER_OWNER_SCREEN_DESC_DRAW list=00514fc0 d0=(39,426 cb=004338c0) d1=(180,426 cb=004338e0) d2=(1000,426 cb=00433a40) surface=0a2fed90 size=(800,600)
NOWNER_4338E0_ENTRY ret=0042262e eax_desc=00514ff5 owner=041bc71a owner_flag=0x02 d532218=00000000 d5322c8=0 surface=0a2fed90 size=(800,600)
NOWNER_4338E0_SURFDUMP_READY surface=0a2fed90 size=(800,600) base=0a5a0030 bytes=480000 owner=041bc71a owner_flag=0x02 d532150=041bc71a d532218=00000000
NOWNER_ACTION_CALL_WRAPPER ret=0040ae16 owner_arg=041bc71a owner_global=041bc71a owner_flag=0x02 d532218=00000000 d5322c8=0 surface=0a2fed90 size=(800,600)
NOWNER_OWNER_435BC0_ENTRY ret=00433919 owner_arg=041bc71a d532218_before=00000000 d5322c8_before=0 surface=0a2fed90 size=(800,600) mouse=(180,440)
NOWNER_WRAPPER_COPYBACK_DONE surface=0a2fed90 size=(800,600) base=0a5a0030 bytes=480000 d532150=041bc71a d532218=041bc71a d532220=0 d5322c8=-1
SURFDUMP_READY redraw_seq=999 surface=0a2fed90 size=(800,600) base=0a5a0030 bytes=480000
SURFDUMP_HOST_READY
"""

OWNER_FLAG_BLOCKED_LOG = """
SURFDUMP_LOADSAVE selected_arg=0 selected_global=0 accept=1 choice=5 gd=04140030
SURFDUMP_PLAYGAME gd=04140030 map=(100,100) scroll=(10,17) surface=0413c8c0 size=(640,480)
NOWNER_CASTLE_CMD99_GATE gate_before=1 forced_gate=1
NOWNER_CASTLE_CALLBACK callback=00433c20 eax_arg=041bc71a command=99
NOWNER_433C20_ENTRY ret=0042262e owner_arg=041bc71a owner_flag=0x00 d532150_before=00000000 surface=0a2fed90 size=(800,600)
NOWNER_OWNER_FLAG_TEST owner=041bc71a owner_flag=0x00 bit2=0 bit1=0 bit8=0
NOWNER_OWNER_SCREEN_DESC_DRAW list=00514fc0 d0=(39,426 cb=004338c0) d1=(1000,426 cb=004338e0) d2=(1000,426 cb=00433a40) surface=0a2fed90 size=(800,600)
NOWNER_4338E0_OWNER_FLAG_BLOCKED surface=0a2fed90 size=(800,600) base=0a5a0030 bytes=480000 owner=041bc71a owner_flag=0x00 d532150=041bc71a d532218=00000000
SURFDUMP_READY redraw_seq=998 surface=0a2fed90 size=(800,600) base=0a5a0030 bytes=480000
"""

NO_LOAD_LOG = """
NOWNER_CASTLE_CMD99_GATE gate_before=1 forced_gate=1
NOWNER_433C20_ENTRY ret=0042262e owner_arg=041bc71a owner_flag=0x02 d532150_before=00000000 surface=0a2fed90 size=(800,600)
NOWNER_OWNER_FLAG_TEST owner=041bc71a owner_flag=0x02 bit2=2 bit1=0 bit8=0
"""

OWNER_LOOP_NO_ACTION_LOG = """
SURFDUMP_LOADSAVE selected_arg=0 selected_global=0 accept=1 choice=5 gd=04140030
SURFDUMP_PLAYGAME gd=04140030 map=(100,100) scroll=(10,17) surface=0413c8c0 size=(640,480)
NOWNER_CASTLE_CMD99_GATE gate_before=1 forced_gate=1
NOWNER_CASTLE_CALLBACK callback=00433c20 eax_arg=041bc71a command=99
NOWNER_433C20_ENTRY ret=0042262e owner_arg=041bc71a owner_flag=0x02 d532150_before=00000000 surface=0a2fed90 size=(800,600)
NOWNER_OWNER_FLAG_TEST owner=041bc71a owner_flag=0x02 bit2=2 bit1=0 bit8=0
"""

OWNER_ACTION_PRELUDE_STALL_LOG = """
SURFDUMP_LOADSAVE selected_arg=0 selected_global=0 accept=1 choice=5 gd=04140030
SURFDUMP_PLAYGAME gd=04140030 map=(100,100) scroll=(10,17) surface=0413c8c0 size=(640,480)
NOWNER_CASTLE_CMD99_GATE gate_before=1 forced_gate=1
NOWNER_CASTLE_CALLBACK callback=00433c20 eax_arg=041bc71a command=99
NOWNER_433C20_ENTRY ret=0042262e owner_arg=041bc71a owner_flag=0x02 d532150_before=00000000 surface=0a2fed90 size=(800,600)
NOWNER_OWNER_FLAG_TEST owner=041bc71a owner_flag=0x02 bit2=2 bit1=0 bit8=0
NOWNER_4338E0_ENTRY ret=00419c60 eax_desc=00514ff5 owner=041bc71a owner_flag=0x02 d532218=00000000 d5322c8=0 surface=0a2fed90 size=(800,600)
NOWNER_419ED0_ENTRY desc=00514ff5 ret=004338e6 state=1 sound=004f78c8
NOWNER_419ED0_SOUND_PREP desc=00514ff5 sound=004f78c8 ret=004338e6
NOWNER_4338E0_AFTER_SELECT owner=041bc71a owner_flag=0x02 d532218=00000000 d5322c8=0
NOWNER_4338E0_AFTER_GATE owner=041bc71a owner_flag=0x02
NOWNER_4338E0_PRE_PUMP ret=00419c60 render=00544cd8 d544d10=00000001 surface=0a2fed90 size=(800,600)
NOWNER_4338E0_PUMP_ENTRY ret=0043390f render=00544cd8 d544d10=00000001
"""

OWNER_ACTION_RENDER_BEGIN_STALL_LOG = """
SURFDUMP_LOADSAVE selected_arg=0 selected_global=0 accept=1 choice=5 gd=04140030
SURFDUMP_PLAYGAME gd=04140030 map=(100,100) scroll=(10,17) surface=0413c8c0 size=(640,480)
NOWNER_CASTLE_CMD99_GATE gate_before=1 forced_gate=1
NOWNER_CASTLE_CALLBACK callback=00433c20 eax_arg=041bc71a command=99
NOWNER_433C20_ENTRY ret=0042262e owner_arg=041bc71a owner_flag=0x02 d532150_before=00000000 surface=0a2fed90 size=(800,600)
NOWNER_OWNER_FLAG_TEST owner=041bc71a owner_flag=0x02 bit2=2 bit1=0 bit8=0
NOWNER_4338E0_ENTRY ret=00419c60 eax_desc=00514ff5 owner=041bc71a owner_flag=0x02 d532218=00000000 d5322c8=0 surface=0a2fed90 size=(800,600)
NOWNER_419ED0_ENTRY desc=00514ff5 ret=004338e6 state=1 sound=004f78c8
NOWNER_419ED0_SOUND_PREP desc=00514ff5 sound=004f78c8 ret=004338e6
NOWNER_419ED0_SOUND_RETURN desc=00514ff5 ret=004338e6 eax=004f78c8
NOWNER_419ED0_STATE6_READY desc=00514ff5 ret=004338e6 state=1 d544cd8=00544cd8
NOWNER_419ED0_RENDER_BEGIN desc=00514ff5 ret=004338e6 d544d10=00000001 render=00000001
NOWNER_RENDER_BEGIN_ENTRY ret=00419efa render=00545198 callback=00544cd8 d544d10=00000001 surface=0a2fed90 size=(800,600)
NOWNER_RENDER_BEGIN_LOOP count=0 render=00545198 callback=00544cd8 d544d10=00000001
NOWNER_RENDER_BEGIN_FLIP_RESULT count=0 eax=00000001 render=00545198 callback=00544cd8 d544d10=00000001
NOWNER_RENDER_BEGIN_DD_PUMP_CALL count=0 render=00545198 callback=00544cd8 d544d10=00000001
NOWNER_DD_PUMP_ENTRY count=0 ret=004609ed render=00545198 edx=00000000 d544d10=00000001 surface=0a2fed90 size=(800,600)
NOWNER_DD_PUMP_MSG_PUMP_CALL count=0 ret=004609ed render=00545198 d544d10=00000001
"""

OWNER_ACTION_RENDER_FLAG_HELD_LOG = """
SURFDUMP_LOADSAVE selected_arg=0 selected_global=0 accept=1 choice=5 gd=04140030
SURFDUMP_PLAYGAME gd=04140030 map=(100,100) scroll=(10,17) surface=0413c8c0 size=(640,480)
NOWNER_CASTLE_CMD99_GATE gate_before=1 forced_gate=1
NOWNER_CASTLE_CALLBACK callback=00433c20 eax_arg=041bc71a command=99
NOWNER_433C20_ENTRY ret=0042262e owner_arg=041bc71a owner_flag=0x02 d532150_before=00000000 surface=0a2fed90 size=(800,600)
NOWNER_OWNER_FLAG_TEST owner=041bc71a owner_flag=0x02 bit2=2 bit1=0 bit8=0
NOWNER_4338E0_ENTRY ret=00419c60 eax_desc=00514ff5 owner=041bc71a owner_flag=0x02 d532218=00000000 d5322c8=0 d544d10=00000001 d544d04=00000001 button0=0x80 raw=(00002d00,00006e00) d543d78=00000000 d543d7c=00000000 surface=0a2fed90 size=(800,600)
NOWNER_419ED0_ENTRY desc=00514ff5 ret=004338e6 state=1 sound=004f78c8
NOWNER_419ED0_RENDER_BEGIN desc=00514ff5 ret=004338e6 d544d10=00000001 d544d04=00000001 button0=0x80 raw=(00002d00,00006e00) d543d78=00000000 d543d7c=00000000 render=00544cd8
NOWNER_RENDER_BEGIN_ENTRY ret=00419efa render=00544cd8 callback=00000000 d544d10=00000001 d544d04=00000001 button0=0x80 raw=(00002d00,00006e00) d543d78=00000000 d543d7c=00000000 surface=0a2fed90 size=(800,600)
NOWNER_RENDER_BEGIN_LOOP iter=1 render=00544cd8 callback=00000000 d544d10=00000001 d544d04=00000001 button0=0x80 raw=(00002d00,00006e00) d543d78=00000000 d543d7c=00000000
NOWNER_RENDER_BEGIN_FLIP_RESULT iter=1 eax=00000001 render=00544cd8 callback=00000000 d544d10=00000001 d544d04=00000001 button0=0x80 raw=(00002d00,00006e00) d543d78=00000000 d543d7c=00000000
NOWNER_RENDER_BEGIN_DD_PUMP_CALL iter=1 render=00544cd8 callback=00000000 d544d10=00000001 d544d04=00000001 button0=0x80 raw=(00002d00,00006e00) d543d78=00000000 d543d7c=00000000
NOWNER_DD_PUMP_ENTRY iter=1 ret=004609ed render=00544cd8 edx=00000000 d544d10=00000001 d544d04=00000001 button0=0x80 raw=(00002d00,00006e00) d543d78=00000000 d543d7c=00000000 surface=0a2fed90 size=(800,600)
NOWNER_RENDER_BEGIN_DD_PUMP_RETURN iter=1 eax=00000000 render=00544cd8 callback=00000000 d544d10=00000001 d544d04=00000001 button0=0x80 raw=(00002d00,00006e00) d543d78=00000000 d543d7c=00000000
NOWNER_RENDER_BEGIN_LOOP iter=8 render=00544cd8 callback=00000000 d544d10=00000001 d544d04=00000001 button0=0x80 raw=(00002d00,00006e00) d543d78=00000000 d543d7c=00000000
NOWNER_RENDER_BEGIN_LOST_RESULT iter=8 eax=00000001 render=00544cd8 callback=00000000 d544d10=00000001 d544d04=00000001 button0=0x80 raw=(00002d00,00006e00) d543d78=00000000 d543d7c=00000000
NOWNER_RENDER_BEGIN_ITERATION_LIMIT iter=8 lost_eax=00000001 d544d04=00000001 button0=0x80 raw=(00002d00,00006e00) d543d78=00000000 d543d7c=00000000
"""

OWNER_ACTION_RENDER_BEGIN_RETURN_LOG = """
SURFDUMP_LOADSAVE selected_arg=0 selected_global=0 accept=1 choice=5 gd=04140030
SURFDUMP_PLAYGAME gd=04140030 map=(100,100) scroll=(10,17) surface=0413c8c0 size=(640,480)
NOWNER_CASTLE_CMD99_GATE gate_before=1 forced_gate=1
NOWNER_CASTLE_CALLBACK callback=00433c20 eax_arg=041bc71a command=99
NOWNER_433C20_ENTRY ret=0042262e owner_arg=041bc71a owner_flag=0x02 d532150_before=00000000 surface=0a2fed90 size=(800,600)
NOWNER_OWNER_FLAG_TEST owner=041bc71a owner_flag=0x02 bit2=2 bit1=0 bit8=0
NOWNER_4338E0_ENTRY ret=00419c60 eax_desc=00514ff5 owner=041bc71a owner_flag=0x02 d532218=00000000 d5322c8=0 surface=0a2fed90 size=(800,600)
NOWNER_419ED0_ENTRY desc=00514ff5 ret=004338e6 state=1 sound=004f78c8
NOWNER_419ED0_RENDER_BEGIN desc=00514ff5 ret=004338e6 d544d10=00000001 render=00000001
NOWNER_RENDER_BEGIN_ENTRY ret=00419efa render=00545198 callback=00544cd8 d544d10=00000000 surface=0a2fed90 size=(800,600)
NOWNER_RENDER_BEGIN_LOOP count=0 render=00545198 callback=00544cd8 d544d10=00000000
NOWNER_RENDER_BEGIN_FLIP_RESULT count=0 eax=00000000 render=00545198 callback=00544cd8 d544d10=00000000
NOWNER_RENDER_BEGIN_LOST_RESULT count=1 eax=00000000 render=00545198 callback=00544cd8 d544d10=00000000
NOWNER_RENDER_BEGIN_EXIT ret=00419efa render=00545198 callback=00544cd8 d544d10=00000000
NOWNER_419ED0_RENDER_BEGIN_RETURN desc=00514ff5 ret=004338e6 eax=00000000 d544d10=00000000
"""

OWNER_ACTION_CLICK_RELEASE_DRAW_LOG = SUCCESS_LOG.replace(
    "NOWNER_4338E0_ENTRY ret=0042262e eax_desc=00514ff5 owner=041bc71a owner_flag=0x02 d532218=00000000 d5322c8=0 surface=0a2fed90 size=(800,600)",
    "NOWNER_4338E0_ENTRY ret=0042262e eax_desc=00514ff5 owner=041bc71a owner_flag=0x02 d532218=00000000 d5322c8=0 d544d10=00000001 d544d04=00000001 button0=0x80 raw=(00002d00,00006e00) d543d78=00000000 d543d7c=00000000 surface=0a2fed90 size=(800,600)\n"
    "NOWNER_RELEASE_OWNER_DESC_CLICK before_d544d04=00000001 before_button0=0x80 after_d544d04=00000000 after_button0=0x00 raw=(00002d00,00006e00) d543d78=00000000 d543d7c=00000000 reason=post_4338e0_entry\n"
    "NOWNER_RENDER_BEGIN_EXIT ret=00419efa render=00544cd8 callback=00000000 d544d10=00000001 d544d04=00000000 button0=0x00 raw=(00002d00,00006e00) d543d78=00000000 d543d7c=00000000 iter=1",
)

COPYBACK_TRACE_SUCCESS_LOG = SUCCESS_LOG.replace(
    "NOWNER_OWNER_435BC0_ENTRY ret=00433919 owner_arg=041bc71a d532218_before=00000000 d5322c8_before=0 surface=0a2fed90 size=(800,600) mouse=(180,440)",
    "NOWNER_WRAPPER_ENTRY ret=00433919 owner_arg=041bc71a d532218=00000000 d5322c8=0 surface=0a2fed90 size=(800,600) raw=(00002d00,00006e00) d544d04=00000000 button0=0x00\n"
    "NOWNER_WRAPPER_ALLOC_RESULT alloc=0b100030 saved_surface=0a2fed90 current_surface=0a2fed90\n"
    "NOWNER_WRAPPER_TEMP_SURFACE temp_surface=0b100030 saved_surface=0a2fed90 current_surface=0b100030 size=(640,480)\n"
    "NOWNER_WRAPPER_CALL_STOCK_435BC0 owner_arg=041bc71a saved_surface=0a2fed90 temp_surface=0b100030 current_surface=0b100030 d532218=00000000 d5322c8=0\n"
    "NOWNER_OWNER_435BC0_ENTRY ret=0051b837 owner_arg=041bc71a d532218_before=00000000 d5322c8_before=0 surface=0b100030 size=(640,480) mouse=(180,440)\n"
    "NOWNER_435BC0_LOOP_HEAD iter=1 ebx=0 d532210=0 d532218=041bc71a d5322c8=-1 surface=0b100030 size=(640,480) raw=(00002d00,00006e00) d544d04=00000000 button0=0x00\n"
    "NOWNER_435BC0_RETURN eax=00000000 d532218=041bc71a d532220=0 d5322c8=-1 surface=0b100030 size=(640,480)\n"
    "NOWNER_WRAPPER_STOCK_RETURN eax=00000000 saved_surface=0a2fed90 temp_surface=0b100030 current_surface=0b100030 d532218=041bc71a d532220=0 d5322c8=-1\n"
    "NOWNER_WRAPPER_RESTORE_SURFACE saved_surface=0a2fed90 temp_surface=0b100030 current_surface=0a2fed90 size=(800,600)\n"
    "NOWNER_WRAPPER_COPYBACK_CALL dst_surface=0a2fed90 src_surface=0b100030 rect=(80,60,639,479) d532218=041bc71a d532220=0 d5322c8=-1\n"
    "NOWNER_WRAPPER_COPYBACK_RETURN eax=00000000 d532218=041bc71a d532220=0 d5322c8=-1 surface=0a2fed90 size=(800,600)\n"
    "NOWNER_WRAPPER_PRESENT_CALL render=00544cd8 surface=0a2fed90 size=(800,600)",
)

COPYBACK_TRACE_STOCK_RETURN_NO_COPYBACK_LOG = COPYBACK_TRACE_SUCCESS_LOG.replace(
    "NOWNER_WRAPPER_RESTORE_SURFACE saved_surface=0a2fed90 temp_surface=0b100030 current_surface=0a2fed90 size=(800,600)\n"
    "NOWNER_WRAPPER_COPYBACK_CALL dst_surface=0a2fed90 src_surface=0b100030 rect=(80,60,639,479) d532218=041bc71a d532220=0 d5322c8=-1\n"
    "NOWNER_WRAPPER_COPYBACK_RETURN eax=00000000 d532218=041bc71a d532220=0 d5322c8=-1 surface=0a2fed90 size=(800,600)\n"
    "NOWNER_WRAPPER_PRESENT_CALL render=00544cd8 surface=0a2fed90 size=(800,600)\n"
    "NOWNER_WRAPPER_COPYBACK_DONE surface=0a2fed90 size=(800,600) base=0a5a0030 bytes=480000 d532150=041bc71a d532218=041bc71a d532220=0 d5322c8=-1",
    "",
)

COPYBACK_TRACE_LOOP_STALL_LOG = COPYBACK_TRACE_SUCCESS_LOG.replace(
    "NOWNER_435BC0_RETURN eax=00000000 d532218=041bc71a d532220=0 d5322c8=-1 surface=0b100030 size=(640,480)\n"
    "NOWNER_WRAPPER_STOCK_RETURN eax=00000000 saved_surface=0a2fed90 temp_surface=0b100030 current_surface=0b100030 d532218=041bc71a d532220=0 d5322c8=-1\n"
    "NOWNER_WRAPPER_RESTORE_SURFACE saved_surface=0a2fed90 temp_surface=0b100030 current_surface=0a2fed90 size=(800,600)\n"
    "NOWNER_WRAPPER_COPYBACK_CALL dst_surface=0a2fed90 src_surface=0b100030 rect=(80,60,639,479) d532218=041bc71a d532220=0 d5322c8=-1\n"
    "NOWNER_WRAPPER_COPYBACK_RETURN eax=00000000 d532218=041bc71a d532220=0 d5322c8=-1 surface=0a2fed90 size=(800,600)\n"
    "NOWNER_WRAPPER_PRESENT_CALL render=00544cd8 surface=0a2fed90 size=(800,600)\n"
    "NOWNER_WRAPPER_COPYBACK_DONE surface=0a2fed90 size=(800,600) base=0a5a0030 bytes=480000 d532150=041bc71a d532218=041bc71a d532220=0 d5322c8=-1",
    "NOWNER_435BC0_LOOP_LIMIT iter=8 ebx=0 d532210=1 d532218=041bc71a d5322c8=-1",
)

LOADSAVE_CONFLICT_LOG = SUCCESS_LOG.replace(
    "SURFDUMP_LOADSAVE selected_arg=0 selected_global=0",
    "SURFDUMP_LOADSAVE selected_arg=0 selected_global=1",
)

LOADSAVE_WRONG_SLOT_LOG = SUCCESS_LOG.replace(
    "SURFDUMP_LOADSAVE selected_arg=0 selected_global=0",
    "SURFDUMP_LOADSAVE selected_arg=1 selected_global=1",
)


def write_log(root: Path, text: str) -> Path:
    path = root / "fixture.log"
    path.write_text(text, encoding="utf-8")
    return path


def test_success_classification() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        report = summary.parse_log(write_log(Path(tmp), SUCCESS_LOG), expected_slot=0)
    assert report["status"] == "owner_action_draw_reached", report
    assert report["proof_class"] == "non_natural_isolated_fixture", report
    assert report["load_success"] is True
    assert report["owner_bit2_set"] is True
    assert report["owner_action_route_count"] >= 1
    assert report["owner_action_draw_count"] >= 1
    assert report["expected_slot_match"] is True
    assert report["loadsave_slot_consistent"] is True
    assert report["loadsave_slot_expected_match"] is True
    assert report["castle_hitmap_sample"]["displayed_sample"] == 0xFE
    assert report["castle_cmd99_target"]["displayed"] == [231, 366]
    assert report["castle_hit_count"] == 1


def test_owner_flag_blocked_classification() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        report = summary.parse_log(write_log(Path(tmp), OWNER_FLAG_BLOCKED_LOG), expected_slot=0)
    assert report["status"] == "owner_flag_still_blocked", report
    assert report["owner_bit2_set"] is False
    assert report["marker_counts"]["NOWNER_4338E0_OWNER_FLAG_BLOCKED"] == 1


def test_no_load_classification() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        report = summary.parse_log(write_log(Path(tmp), NO_LOAD_LOG), expected_slot=0)
    assert report["status"] == "load_not_reached", report
    assert report["load_success"] is False


def test_owner_loop_without_action_classification() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        report = summary.parse_log(write_log(Path(tmp), OWNER_LOOP_NO_ACTION_LOG), expected_slot=0)
    assert report["status"] == "owner_loop_no_action", report
    assert report["owner_bit2_set"] is True
    assert report["owner_action_route_count"] == 0


def test_owner_action_prelude_stall_classification() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        report = summary.parse_log(write_log(Path(tmp), OWNER_ACTION_PRELUDE_STALL_LOG), expected_slot=0)
    assert report["status"] == "owner_action_prelude_stalled", report
    assert report["owner_bit2_set"] is True
    assert report["owner_action_route_count"] == 1
    assert report["owner_action_draw_count"] == 0
    assert report["owner_action_prelude_count"] >= 1


def test_owner_action_render_begin_stall_classification() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        report = summary.parse_log(write_log(Path(tmp), OWNER_ACTION_RENDER_BEGIN_STALL_LOG), expected_slot=0)
    assert report["status"] == "owner_action_ddraw_wait_stalled", report
    assert report["owner_action_render_begin_reached"] is True
    assert report["owner_action_render_begin_returned"] is False
    assert report["owner_action_ddraw_wait_stalled"] is True
    assert report["dd_pump_entry_count"] == 1
    assert report["dd_pump_msg_pump_call_count"] == 1
    assert report["owner_action_draw_count"] == 0


def test_owner_action_render_flag_held_classification() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        report = summary.parse_log(write_log(Path(tmp), OWNER_ACTION_RENDER_FLAG_HELD_LOG), expected_slot=0)
    assert report["status"] == "owner_action_render_flag_held", report
    assert report["render_flag_held_during_spin"] is True
    assert report["render_flag_bit01_count"] > 0
    assert report["render_begin_iteration_limit_count"] == 1
    assert report["render_flag_unique_values"] == [1]


def test_owner_action_render_begin_return_classification() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        report = summary.parse_log(write_log(Path(tmp), OWNER_ACTION_RENDER_BEGIN_RETURN_LOG), expected_slot=0)
    assert report["status"] == "owner_action_render_begin_returned", report
    assert report["owner_action_render_begin_reached"] is True
    assert report["owner_action_render_begin_returned"] is True
    assert report["render_begin_exit_count"] == 1
    assert report["owner_action_draw_count"] == 0


def test_owner_action_click_release_draw_fields() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        report = summary.parse_log(write_log(Path(tmp), OWNER_ACTION_CLICK_RELEASE_DRAW_LOG), expected_slot=0)
    assert report["status"] == "owner_action_draw_reached", report
    assert report["owner_desc_release_count"] == 1
    assert report["last_owner_desc_release"]["after_d544d04"] == 0
    assert report["last_owner_desc_release"]["after_button0"] == 0
    assert report["render_begin_exit_count"] == 1
    assert report["wrapper_copyback_count"] == 1


def test_owner_action_copyback_trace_reached_classification() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        report = summary.parse_log(write_log(Path(tmp), COPYBACK_TRACE_SUCCESS_LOG), expected_slot=0)
    assert report["status"] == "owner_action_copyback_reached", report
    assert report["copyback_path_marker_count"] > 0
    assert report["wrapper_entry_count"] == 1
    assert report["wrapper_call_stock_count"] == 1
    assert report["owner_435bc0_return_count"] == 1
    assert report["wrapper_stock_return_count"] == 1
    assert report["wrapper_copyback_call_count"] == 1
    assert report["wrapper_copyback_return_count"] == 1
    assert report["wrapper_copyback_count"] == 1


def test_owner_action_copyback_trace_stalled_after_stock_return() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        report = summary.parse_log(
            write_log(Path(tmp), COPYBACK_TRACE_STOCK_RETURN_NO_COPYBACK_LOG),
            expected_slot=0,
        )
    assert report["status"] == "owner_action_copyback_not_reached", report
    assert report["wrapper_stock_return_count"] == 1
    assert report["owner_435bc0_return_count"] == 1
    assert report["wrapper_copyback_count"] == 0


def test_owner_action_copyback_trace_loop_stalled() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        report = summary.parse_log(write_log(Path(tmp), COPYBACK_TRACE_LOOP_STALL_LOG), expected_slot=0)
    assert report["status"] == "owner_action_435bc0_loop_stalled", report
    assert report["owner_435bc0_loop_limit_count"] == 1
    assert report["owner_435bc0_return_count"] == 0
    assert report["wrapper_stock_return_count"] == 0
    assert report["wrapper_copyback_count"] == 0


def test_timeout_stack_classification() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        log = write_log(root, OWNER_ACTION_RENDER_BEGIN_STALL_LOG)
        (root / "timeout-stack.log").write_text(
            "USER32!PeekMessageA+0x14d\n"
            "000edb00 00461b58\n"
            "000edb4c 004605df\n",
            encoding="utf-8",
        )
        report = summary.parse_log(log, expected_slot=0)
    assert report["timeout_stack_classification"] == "peekmessage_dd_pump", report


def test_av_fails_closed() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        report = summary.parse_log(write_log(Path(tmp), SUCCESS_LOG + "\nAV_SURFDUMP code c0000005\n"), expected_slot=0)
    assert report["status"] == "access_violation", report
    assert report["av_count"] == 1


def test_loadsave_conflict_fails_closed() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        report = summary.parse_log(write_log(Path(tmp), LOADSAVE_CONFLICT_LOG), expected_slot=0)
    assert report["status"] == "slot_mismatch", report
    assert report["loadsave_slot_consistent"] is False
    assert report["expected_slot_match"] is False


def test_loadsave_wrong_slot_fails_closed() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        report = summary.parse_log(write_log(Path(tmp), LOADSAVE_WRONG_SLOT_LOG), expected_slot=0)
    assert report["status"] == "slot_mismatch", report
    assert report["loadsave_slot_consistent"] is True
    assert report["loadsave_slot_expected_match"] is False
    assert report["expected_slot_match"] is False


def test_cli_writes_outputs_and_requires_owner_action() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        log = write_log(root, SUCCESS_LOG)
        out_json = root / "summary.json"
        out_md = root / "summary.md"
        result = subprocess.run(
            [
                sys.executable,
                str(Path(summary.__file__)),
                str(log),
                "--expected-slot",
                "0",
                "--write-json",
                str(out_json),
                "--write-md",
                str(out_md),
                "--require-load-success",
                "--require-slot-match",
                "--require-owner-bit2",
                "--require-owner-action",
                "--require-owner-action-draw",
                "--require-wrapper-copyback",
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        assert out_json.exists()
        assert out_md.exists()
        assert "non_natural_isolated_fixture" in out_md.read_text(encoding="utf-8")


def test_cli_accepts_click_release_requirements() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        log = write_log(root, OWNER_ACTION_CLICK_RELEASE_DRAW_LOG)
        result = subprocess.run(
            [
                sys.executable,
                str(Path(summary.__file__)),
                str(log),
                "--expected-slot",
                "0",
                "--require-load-success",
                "--require-slot-match",
                "--require-owner-bit2",
                "--require-owner-action",
                "--require-owner-action-draw",
                "--require-click-release",
                "--require-render-begin-exit",
                "--require-wrapper-copyback",
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        assert result.returncode == 0, result.stdout + result.stderr


def test_cli_accepts_copyback_path_requirement() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        log = write_log(root, COPYBACK_TRACE_SUCCESS_LOG)
        result = subprocess.run(
            [
                sys.executable,
                str(Path(summary.__file__)),
                str(log),
                "--expected-slot",
                "0",
                "--require-load-success",
                "--require-slot-match",
                "--require-owner-bit2",
                "--require-owner-action",
                "--require-owner-action-draw",
                "--require-copyback-path",
                "--require-wrapper-copyback",
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        assert result.returncode == 0, result.stdout + result.stderr


def test_cli_fails_when_owner_action_required_but_blocked() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        log = write_log(Path(tmp), OWNER_FLAG_BLOCKED_LOG)
        result = subprocess.run(
            [
                sys.executable,
                str(Path(summary.__file__)),
                str(log),
                "--expected-slot",
                "0",
                "--require-owner-action",
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        assert result.returncode == 2, result.stdout + result.stderr


def test_cli_fails_when_slot_match_required_but_loadsave_conflicts() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        log = write_log(Path(tmp), LOADSAVE_CONFLICT_LOG)
        result = subprocess.run(
            [
                sys.executable,
                str(Path(summary.__file__)),
                str(log),
                "--expected-slot",
                "0",
                "--require-load-success",
                "--require-slot-match",
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        assert result.returncode == 2, result.stdout + result.stderr


def run_tests() -> None:
    test_success_classification()
    test_owner_flag_blocked_classification()
    test_no_load_classification()
    test_owner_loop_without_action_classification()
    test_owner_action_prelude_stall_classification()
    test_owner_action_render_begin_stall_classification()
    test_owner_action_render_flag_held_classification()
    test_owner_action_render_begin_return_classification()
    test_owner_action_click_release_draw_fields()
    test_owner_action_copyback_trace_reached_classification()
    test_owner_action_copyback_trace_stalled_after_stock_return()
    test_owner_action_copyback_trace_loop_stalled()
    test_timeout_stack_classification()
    test_av_fails_closed()
    test_loadsave_conflict_fails_closed()
    test_loadsave_wrong_slot_fails_closed()
    test_cli_writes_outputs_and_requires_owner_action()
    test_cli_accepts_click_release_requirements()
    test_cli_accepts_copyback_path_requirement()
    test_cli_fails_when_owner_action_required_but_blocked()
    test_cli_fails_when_slot_match_required_but_loadsave_conflicts()


if __name__ == "__main__":
    run_tests()
    print("right_bottom_slot_fixture_result_summary tests passed")
