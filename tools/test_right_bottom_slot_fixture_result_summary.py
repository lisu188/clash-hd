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

COPYBACK_TRACE_LOOPSTATE_LOG = COPYBACK_TRACE_LOOP_STALL_LOG.replace(
    "NOWNER_435BC0_LOOP_LIMIT iter=8 ebx=0 d532210=1 d532218=041bc71a d5322c8=-1",
    "NOWNER_435BC0_POLL count=1 d532210=0 d532218=041bc71a d532220=0 d5322c8=-1 mouse=(180,440) raw=(00002d00,00006e00) d544d04=00000000 button0=0x00 surface=0b100030 size=(640,480)\n"
    "NOWNER_435BC0_WRITE_532218 ret=0051b837 new=041bc71a selected_index=0 hover_slot=-1 surface=0b100030 size=(640,480)\n"
    "NOWNER_435BC0_WRITE_5322C8 ret=0051b837 new=-1 d532218=041bc71a selected_index=0 surface=0b100030 size=(640,480)\n"
    "NOWNER_435BC0_GRID_ROUTE_ENTRY selected_index=0 hover_slot=-1 mouse=(180,440) raw=(00002d00,00006e00)\n"
    "NOWNER_435BC0_GRID_GATE raw_result=0 mouse=(180,440) raw=(00002d00,00006e00)\n"
    "NOWNER_435BC0_GRID_RESULT result=-1 mouse=(180,440) selected_index=0 hover_slot=-1\n"
    "NOWNER_435BC0_POLL_LIMIT count=16 d532210=0 d532218=041bc71a d532220=0 d5322c8=-1 mouse=(4,440) raw=(00000100,00006e00)\n"
    "NOWNER_HITTEST_COMPARE desc=00514ff5 xy=(180,426) flags=0x00 callback=004338e0 mouse=(180,440) raw=(00002d00,00006e00) d544d04=00000000 button0=0x00 eax=00000000\n"
    "NOWNER_435BC0_LOOP_LIMIT iter=8 ebx=0 d532210=1 d532218=041bc71a d5322c8=-1",
)

COPYBACK_TRACE_INPUT_RESAMPLE_LOG = COPYBACK_TRACE_LOOPSTATE_LOG.replace(
    "NOWNER_435BC0_POLL count=1 d532210=0 d532218=041bc71a d532220=0 d5322c8=-1 mouse=(180,440) raw=(00002d00,00006e00) d544d04=00000000 button0=0x00 surface=0b100030 size=(640,480)",
    "NOWNER_435BC0_LOOP_PUMP_CALL iter=1 d532210=0 d532218=041bc71a d532220=0 d5322c8=-1 raw=(00002d00,00006e00) d544d04=00000000 button0=0x00\n"
    "NOWNER_435BC0_PUMP_TICK_RETURN iter=1 ret=00435dde eax=00000000 render=00544cd8 d544d10=00000001 d544d04=00000000 button0=0x00 raw=(00002d00,00006e00) d543d78=00000000 d543d7c=00000000\n"
    "NOWNER_SOURCEHOLD_CB14_PRE iter=1 source=(0x2d00,0x6e00) prev=(0x2d00,0x6e00) flag=0x01 raw=(00002d00,00006e00)\n"
    "NOWNER_435BC0_PUMP_CB14_CALL iter=1 ret=00435dde vtable=0050f204 cb14=004612e0 render=00544cd8 raw=(00002d00,00006e00) d544d04=00000000 button0=0x00\n"
    "NOWNER_435BC0_PUMP_608F0B_CALL iter=1 ret=00435dde render=00544cd8 raw=(00000100,00006e00) d544d04=00000001 button0=0x93\n"
    "NOWNER_435BC0_PUMP_CB04_CALL iter=1 ret=00435dde vtable=0050f204 cb04=004611a0 render=00544cd8 raw=(00000100,00006e00) d544d04=00000001 button0=0x93\n"
    "NOWNER_435BC0_POLL count=1 d532210=0 d532218=041bc71a d532220=0 d5322c8=-1 mouse=(4,440) raw=(00000100,00006e00) d544d04=00000001 button0=0x93 surface=0b100030 size=(640,480)",
)

COPYBACK_TRACE_4612E0_ENTRY_RETURN_LOG = COPYBACK_TRACE_INPUT_RESAMPLE_LOG.replace(
    "NOWNER_435BC0_PUMP_608F0B_CALL iter=1 ret=00435dde render=00544cd8 raw=(00000100,00006e00) d544d04=00000001 button0=0x93\n",
    "NOWNER_SOURCEHOLD_4612E0_ENTRY iter=1 ret=00460611 source=(0x2d00,0x6e00) prev=(0x2d00,0x6e00) flag=0x01 raw=(00002d00,00006e00) d544d04=00000000 button0=0x00 d543d78=00000001 d543d7c=00000005\n"
    "NOWNER_SOURCEHOLD_4612E0_RETURN iter=1 ret=00435dde eax=00000000 source=(0x0100,0x6e00) prev=(0x2d00,0x6e00) flag=0x01 raw=(00000100,00006e00) d544d04=00000001 button0=0x93 d543d78=00000001 d543d7c=00000005\n"
    "NOWNER_435BC0_PUMP_608F0B_CALL iter=1 ret=00435dde render=00544cd8 raw=(00000100,00006e00) d544d04=00000001 button0=0x93\n",
)

COPYBACK_TRACE_SOURCEHOLD_CALLSITE_LOG = COPYBACK_TRACE_INPUT_RESAMPLE_LOG.replace(
    "NOWNER_435BC0_PUMP_608F0B_CALL iter=1 ret=00435dde render=00544cd8 raw=(00000100,00006e00) d544d04=00000001 button0=0x93\n",
    "NOWNER_SOURCEHOLD_608F0A_PRE iter=1 source=(0x2d00,0x6e00) prev=(0x2d00,0x6e00) flag=0x01 raw=(00002d00,00006e00) d544d04=00000001 button0=0x80\n"
    "NOWNER_435BC0_PUMP_608F0A_CALL iter=1 ret=00435dde render=00544cd8 raw=(00002d00,00006e00) d544d04=00000001 button0=0x80\n"
    "NOWNER_SOURCEHOLD_608F0B_PRE iter=1 source=(0x2d00,0x6e00) prev=(0x2d00,0x6e00) flag=0x01 raw=(00002d00,00006e00) d544d04=00000001 button0=0x80\n"
    "NOWNER_435BC0_PUMP_608F0B_CALL iter=1 ret=00435dde render=00544cd8 raw=(00002d00,00006e00) d544d04=00000001 button0=0x80\n",
)

COPYBACK_TRACE_SOURCEHOLD_COORDS_CALLSITE_LOG = COPYBACK_TRACE_INPUT_RESAMPLE_LOG.replace(
    "NOWNER_435BC0_PUMP_608F0B_CALL iter=1 ret=00435dde render=00544cd8 raw=(00000100,00006e00) d544d04=00000001 button0=0x93\n",
    "NOWNER_SOURCEHOLD_608F0A_COORDS_PRE iter=1 source=(0x2d00,0x6e00) prev=(0x2d00,0x6e00) flag=0x01 raw=(00002d00,00006e00) d544d04=00000000 button0=0x00\n"
    "NOWNER_435BC0_PUMP_608F0A_CALL iter=1 ret=00435dde render=00544cd8 raw=(00002d00,00006e00) d544d04=00000000 button0=0x00\n"
    "NOWNER_SOURCEHOLD_608F0B_COORDS_PRE iter=1 source=(0x2d00,0x6e00) prev=(0x2d00,0x6e00) flag=0x01 raw=(00002d00,00006e00) d544d04=00000000 button0=0x00\n"
    "NOWNER_435BC0_PUMP_608F0B_CALL iter=1 ret=00435dde render=00544cd8 raw=(00002d00,00006e00) d544d04=00000000 button0=0x00\n",
)

COPYBACK_TRACE_ACTION_CLICK_NATIVE_LOG = COPYBACK_TRACE_SUCCESS_LOG.replace(
    "NOWNER_435BC0_LOOP_HEAD iter=1 ebx=0 d532210=0 d532218=041bc71a d5322c8=-1 surface=0b100030 size=(640,480) raw=(00002d00,00006e00) d544d04=00000000 button0=0x00",
    "NOWNER_435BC0_LOOP_HEAD iter=1 ebx=0 d532210=0 d532218=041bc71a d5322c8=-1 surface=0b100030 size=(640,480) raw=(00002d00,00006e00) d544d04=00000000 button0=0x00\n"
    "NOWNER_ACTION_FORCE_NATIVE target=bottom-left-action pass_index=1 native=(81,441) raw=(00001440,00006e40) click_flag=00000001 button0=0x80 selected_index=0 hover_slot=-1 action_state=0\n"
    "NOWNER_ACTION_DESCRIPTOR_ENTRY desc=0051519a mouse=(81,441) raw=(00001440,00006e40) click_flag=00000001 button0=0x80 selected_index=0 hover_slot=-1 action_state=0\n"
    "NOWNER_ACTION_WIDGET_PRE_GATES desc=0051519a reason=native_action_rearm click_flag=00000001 button0=0x80 mouse=(81,441)\n"
    "NOWNER_ACTION_WIDGET_CLICK_GATE desc=0051519a desc_xy=(81,441) state=0x00 hover_cb=00435610 click_cb=00435620 type=0x00 mouse=(81,441) click_flag=00000001 button0=0x80\n"
    "NOWNER_ACTION_WIDGET_CLICK_GATE_RET desc=0051519a click_gate=1 click_cb=00435620 state=0x00 mouse=(81,441) click_flag=00000001\n"
    "NOWNER_ACTION_DESCRIPTOR_CALLBACK desc=0051519a callback=00435620 desc_xy=(81,441) state=0x00 mouse=(81,441) action_state=0\n"
    "NOWNER_ACTION_DESCRIPTOR_RESULT result=1 pass_index=1 mouse=(81,441) action_state=0\n"
    "NOWNER_ACTION_CLICK_435620_ENTRY desc=0051519a mouse=(81,441) action_state_before=0 selected_index=0 hover_slot=-1\n"
    "NOWNER_ACTION_CLICK_435620_BEFORE_SET edx=1 action_state_before=0\n"
    "NOWNER_ACTION_CLICK_EXIT_SET pass_index=1 action_state=1 selected_index=0 hover_slot=-1",
)

COPYBACK_TRACE_ACTION_CLICK_DISPLAY_LOG = COPYBACK_TRACE_SUCCESS_LOG.replace(
    "NOWNER_435BC0_LOOP_HEAD iter=1 ebx=0 d532210=0 d532218=041bc71a d5322c8=-1 surface=0b100030 size=(640,480) raw=(00002d00,00006e00) d544d04=00000000 button0=0x00",
    "NOWNER_435BC0_LOOP_HEAD iter=1 ebx=0 d532210=0 d532218=041bc71a d5322c8=-1 surface=0b100030 size=(640,480) raw=(00002d00,00006e00) d544d04=00000000 button0=0x00\n"
    "NOWNER_ACTION_FORCE_DISPLAY target=bottom-left-action pass_index=1 displayed=(161,501) expected_native=(81,441) raw=(00002840,00007d40) click_flag=00000001 button0=0x80 selected_index=0 hover_slot=-1 action_state=0\n"
    "NOWNER_ACTION_DESCRIPTOR_ENTRY desc=0051519a mouse=(81,441) raw=(00001440,00006e40) click_flag=00000001 button0=0x80 selected_index=0 hover_slot=-1 action_state=0\n"
    "NOWNER_ACTION_WIDGET_PRE_GATES desc=0051519a reason=centered_input_display_click click_flag=00000001 button0=0x80 mouse=(81,441)\n"
    "NOWNER_ACTION_WIDGET_CLICK_GATE desc=0051519a desc_xy=(41,425) state=0x01 hover_cb=00419770 click_cb=00435620 type=0x02 mouse=(81,441) click_flag=00000001 button0=0x80\n"
    "NOWNER_ACTION_WIDGET_CLICK_GATE_RET desc=0051519a click_gate=1 click_cb=00435620 state=0x01 mouse=(81,441) click_flag=00000001\n"
    "NOWNER_ACTION_DESCRIPTOR_CALLBACK desc=0051519a callback=00435620 desc_xy=(41,425) state=0x01 mouse=(81,441) action_state=0\n"
    "NOWNER_ACTION_DESCRIPTOR_RESULT result=3 pass_index=1 mouse=(4,441) action_state=1\n"
    "NOWNER_ACTION_CLICK_435620_ENTRY desc=0051519a mouse=(81,441) action_state_before=0 selected_index=0 hover_slot=-1\n"
    "NOWNER_ACTION_CLICK_435620_BEFORE_SET edx=1 action_state_before=0\n"
    "NOWNER_ACTION_CLICK_EXIT_SET pass_index=1 action_state=1 selected_index=0 hover_slot=-1",
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


def test_owner_action_loopstate_trace_fields() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        report = summary.parse_log(write_log(Path(tmp), COPYBACK_TRACE_LOOPSTATE_LOG), expected_slot=0)
    assert report["status"] == "owner_action_435bc0_loop_stalled", report
    assert report["stock_loopstate_marker_count"] >= 4
    assert report["stock_grid_marker_count"] >= 3
    assert report["descriptor_hittest_marker_count"] == 1
    assert report["owner_435bc0_poll_count"] == 1
    assert report["owner_435bc0_poll_limit_count"] == 1
    assert report["owner_435bc0_write_532218_count"] == 1
    assert report["owner_435bc0_write_5322c8_count"] == 1
    assert report["owner_435bc0_grid_route_count"] == 1
    assert report["owner_435bc0_grid_gate_count"] == 1
    assert report["owner_435bc0_grid_result_count"] == 1
    assert report["last_owner_435bc0_poll"]["mouse"] == [180, 440]
    assert report["last_owner_435bc0_grid_result"]["result"] == -1


def test_owner_action_input_resample_trace_fields() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        report = summary.parse_log(
            write_log(Path(tmp), COPYBACK_TRACE_INPUT_RESAMPLE_LOG),
            expected_slot=0,
            proof_class="natural_slot5_right_bottom_input_resample",
        )
    assert report["status"] == "owner_action_435bc0_loop_stalled", report
    assert report["owner_435bc0_pump_tick_return_count"] == 1
    assert report["owner_435bc0_pump_cb14_call_count"] == 1
    assert report["owner_435bc0_pump_608f0b_call_count"] == 1
    assert report["sourcehold_marker_count"] == 1
    assert report["sourcehold_callsite_marker_count"] == 1
    assert report["sourcehold_4612e0_marker_count"] == 0
    assert report["input_source_cb14_4612e0_seen"] is True
    assert report["input_source_status"] == "cb14_4612e0_callsite_seen_inner_offsets_unverified"
    assert report["real_input_click_proven"] is False
    assert report["last_sourcehold"]["source"] == [0x2D00, 0x6E00]
    assert report["first_owner_435bc0_pump_tick_return"]["raw"] == [0x2D00, 0x6E00]
    assert report["first_owner_435bc0_pump_cb14_call"]["raw"] == [0x2D00, 0x6E00]
    assert report["first_owner_435bc0_pump_608f0b_call"]["raw"] == [0x0100, 0x6E00]
    assert report["last_owner_435bc0_pump_tick_return"]["raw"] == [0x2D00, 0x6E00]
    assert report["last_owner_435bc0_pump_cb14_call"]["cb14"] == 0x004612E0
    assert report["last_owner_435bc0_pump_608f0b_call"]["raw"] == [0x0100, 0x6E00]
    assert report["last_owner_435bc0_poll"]["mouse"] == [4, 440]


def test_owner_action_4612e0_entry_return_trace_fields() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        report = summary.parse_log(
            write_log(Path(tmp), COPYBACK_TRACE_4612E0_ENTRY_RETURN_LOG),
            expected_slot=0,
            proof_class="natural_slot5_right_bottom_input_resample",
        )
    assert report["status"] == "owner_action_435bc0_loop_stalled", report
    assert report["sourcehold_marker_count"] == 3
    assert report["sourcehold_callsite_marker_count"] == 1
    assert report["sourcehold_4612e0_marker_count"] == 2
    assert report["input_source_cb14_4612e0_seen"] is True
    assert report["input_source_status"] == "cb14_4612e0_inner_offsets_seen"
    assert report["real_input_click_proven"] is False
    assert report["last_sourcehold_marker"] == "NOWNER_SOURCEHOLD_4612E0_RETURN"
    assert report["last_sourcehold"]["source"] == [0x0100, 0x6E00]
    assert report["last_sourcehold"]["d544d04"] == 1
    assert report["last_sourcehold"]["button0"] == 0x93


def test_owner_action_callsite_sourcehold_trace_fields() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        report = summary.parse_log(
            write_log(Path(tmp), COPYBACK_TRACE_SOURCEHOLD_CALLSITE_LOG),
            expected_slot=0,
            proof_class="natural_slot5_right_bottom_sourcehold_callsite",
        )
    assert report["status"] == "owner_action_435bc0_loop_stalled", report
    assert report["sourcehold_marker_count"] == 3
    assert report["sourcehold_callsite_marker_count"] == 3
    assert report["sourcehold_4612e0_marker_count"] == 0
    assert report["input_source_status"] == "cb14_4612e0_callsite_seen_inner_offsets_unverified"
    assert report["last_sourcehold_marker"] == "NOWNER_SOURCEHOLD_608F0B_PRE"
    assert report["last_sourcehold"]["raw"] == [0x2D00, 0x6E00]
    assert report["owner_435bc0_pump_608f0a_call_count"] == 1
    assert report["last_owner_435bc0_pump_608f0b_call"]["raw"] == [0x2D00, 0x6E00]


def test_owner_action_coords_callsite_sourcehold_trace_fields() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        report = summary.parse_log(
            write_log(Path(tmp), COPYBACK_TRACE_SOURCEHOLD_COORDS_CALLSITE_LOG),
            expected_slot=0,
            proof_class="natural_slot5_right_bottom_sourcehold_coords_callsite",
        )
    assert report["status"] == "owner_action_435bc0_loop_stalled", report
    assert report["sourcehold_marker_count"] == 3
    assert report["sourcehold_callsite_marker_count"] == 3
    assert report["sourcehold_4612e0_marker_count"] == 0
    assert report["input_source_status"] == "cb14_4612e0_callsite_seen_inner_offsets_unverified"
    assert report["last_sourcehold_marker"] == "NOWNER_SOURCEHOLD_608F0B_COORDS_PRE"
    assert report["last_sourcehold"]["raw"] == [0x2D00, 0x6E00]
    assert report["last_sourcehold"]["d544d04"] == 0
    assert report["last_sourcehold"]["button0"] == 0
    assert report["last_owner_435bc0_pump_608f0b_call"]["raw"] == [0x2D00, 0x6E00]
    assert report["last_owner_435bc0_pump_608f0b_call"]["d544d04"] == 0


def test_owner_action_native_click_trace_fields() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        report = summary.parse_log(
            write_log(Path(tmp), COPYBACK_TRACE_ACTION_CLICK_NATIVE_LOG),
            expected_slot=0,
            proof_class="natural_slot5_right_bottom_action_click_native",
        )
    assert report["status"] == "owner_action_copyback_reached", report
    assert report["action_click_marker_count"] == 10
    assert report["action_click_force_count"] == 1
    assert report["input_source_status"] == "debugger_forced_action_click_only"
    assert report["real_input_click_proven"] is False
    assert report["debugger_forced_click_only"] is True
    assert report["action_descriptor_entry_count"] == 1
    assert report["action_widget_click_gate_ret_count"] == 1
    assert report["action_descriptor_callback_count"] == 1
    assert report["action_descriptor_result_count"] == 1
    assert report["action_click_435620_entry_count"] == 1
    assert report["action_click_exit_set_count"] == 1
    assert report["last_action_click_marker"] == "NOWNER_ACTION_CLICK_EXIT_SET"
    assert report["last_action_force"]["raw"] == [0x1440, 0x6E40]
    assert report["last_action_force"]["native"] == [81, 441]
    assert report["last_action_descriptor_callback"]["callback"] == 0x00435620
    assert report["last_action_descriptor_result"]["result"] == 1
    assert report["last_action_click_exit_set"]["action_state"] == 1
    assert report["wrapper_copyback_count"] == 1


def test_owner_action_display_click_transform_trace_fields() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        report = summary.parse_log(
            write_log(Path(tmp), COPYBACK_TRACE_ACTION_CLICK_DISPLAY_LOG),
            expected_slot=0,
            proof_class="natural_slot5_right_bottom_action_click_centered_input",
        )
    assert report["status"] == "owner_action_copyback_reached", report
    assert report["action_click_marker_count"] == 10
    assert report["action_click_force_count"] == 1
    assert report["input_source_status"] == "debugger_forced_action_click_only"
    assert report["real_input_click_proven"] is False
    assert report["debugger_forced_click_only"] is True
    assert report["action_click_native_force_count"] == 0
    assert report["action_click_display_force_count"] == 1
    assert report["last_action_force_marker"] == "NOWNER_ACTION_FORCE_DISPLAY"
    assert report["last_action_force"]["displayed"] == [161, 501]
    assert report["last_action_force"]["expected_native"] == [81, 441]
    assert report["last_action_force"]["raw"] == [0x2840, 0x7D40]
    assert report["last_action_descriptor_callback"]["callback"] == 0x00435620
    assert report["last_action_descriptor_callback"]["mouse"] == [81, 441]
    assert report["last_action_click_exit_set"]["action_state"] == 1
    assert report["wrapper_copyback_count"] == 1


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


def test_descriptor_hit_scan_timeout_stack_classification() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        log = write_log(root, COPYBACK_TRACE_LOOPSTATE_LOG)
        (root / "timeout-stack.log").write_text(
            "eax=ffffed00 ebx=0051526e\n"
            "eip=00419b8d\n"
            "000edb28 00419dd9\n",
            encoding="utf-8",
        )
        report = summary.parse_log(log, expected_slot=0)
    assert report["timeout_stack_classification"] == "descriptor_hit_scan", report


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
    test_owner_action_loopstate_trace_fields()
    test_owner_action_input_resample_trace_fields()
    test_owner_action_4612e0_entry_return_trace_fields()
    test_owner_action_callsite_sourcehold_trace_fields()
    test_owner_action_coords_callsite_sourcehold_trace_fields()
    test_timeout_stack_classification()
    test_descriptor_hit_scan_timeout_stack_classification()
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
