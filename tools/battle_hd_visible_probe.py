#!/usr/bin/env python3
"""Prepare the exact expanded-battle visible probe; never launch or inject input.

This is a standalone CDB startup file, not an extra for the surface-dump host.
Startup/loading and one constructed Unit_Attack call are disclosed mutations.
Once battle starts, observers do not change native input, gates, commands,
arena, camera, banners or dialogs. The eventual synthetic call return restores
only its saved caller CPU frame and the disclosed battle-UI preference.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import struct


ORIGINAL_SHA256 = "500055d77d03d514e8d3168506bd10f67cd8569bcc450604ff8192f46cdaf3ae"
CANDIDATE_SHA256 = "7d04fe9005515dad4e618df507103946265d7e2a6421287281c1fc5f112d1e47"
SAVE_SHA256 = "4f2182409d209985a527f07c4116b19e44332416698d6acb0a3d35ae68db8a89"
STAGE = "gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-castlecenter-all-battlehd"
RESOLUTION = "1280x720"
PROTOCOL = "expanded_battle_visible_observers_v2"
IMAGE_BASE = 0x400000
DEBUGGER_SETUP_COMMANDS = ("bc *", ".expr /s masm", "n 16")
MAIN_STARTUP_SLEEP_VA = 0x44789A
WORKER_SLEEP_VAS = (0x46E4D0, 0x46E6DF, 0x46FD01)
DESCRIPTORS = tuple(0x514B78 + i * 53 for i in range(6))
DESCRIPTOR_XY = ((1138, 490), (1201, 490), (1138, 521), (1138, 552), (1201, 521), (1145, 120))
CALLBACKS = (0x42D4E0, 0x42D3A0, 0x42D5B0, 0x42D670, 0x42D560, 0x42D6F0)
# IDs are decimal in bp/bd/be commands. No implicit IDs or inherited probe.
FIRST_OBSERVER_ID = 20
LAST_BREAKPOINT_ID = 59
SAVE_BYTES = 586414


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_va(data: bytes, va: int, size: int) -> tuple[int, bytes]:
    """Map only complete, unambiguous raw PE32 sections, never virtual padding."""
    try:
        if data[:2] != b"MZ":
            raise ValueError("not MZ")
        pe = struct.unpack_from("<I", data, 0x3C)[0]
        if data[pe:pe + 4] != b"PE\0\0" or struct.unpack_from("<H", data, pe + 4)[0] != 0x14C:
            raise ValueError("not x86 PE")
        opt = pe + 24
        if struct.unpack_from("<H", data, opt)[0] != 0x10B or struct.unpack_from("<I", data, opt + 28)[0] != IMAGE_BASE:
            raise ValueError("not fixed-base PE32")
        table = opt + struct.unpack_from("<H", data, pe + 20)[0]
        rva, matches = va - IMAGE_BASE, []
        for i in range(struct.unpack_from("<H", data, pe + 6)[0]):
            _, start, raw_size, raw = struct.unpack_from("<IIII", data, table + 40 * i + 8)
            if size > 0 and start <= rva and rva + size <= start + raw_size:
                offset = raw + rva - start
                if offset + size <= len(data):
                    matches.append((offset, data[offset:offset + size]))
        if len(matches) != 1:
            raise ValueError(f"VA {va:08x} is not in one complete raw section")
        return matches[0]
    except struct.error as exc:
        raise ValueError("truncated PE") from exc


def printf(event: str, fields: str = "", *args: str) -> str:
    """Unescaped command body; breakpoint() applies the one quoting layer."""
    text = "BHDV_" + event + " tid=%x eip=%p esp=%p" + (" " + fields if fields else "")
    return '.printf "' + text + r'\n", ' + ", ".join(("@$tid", "@eip", "@esp", *args))


def reject(reason: str) -> str:
    return printf("REJECT", "reason=" + reason) + "; q"


def guard(condition: str, body: str, reason: str) -> str:
    return f".if ({condition}) {{ {body} }} .else {{ {reject(reason)} }}"


def breakpoint(number: int, va: int, body: str) -> str:
    escaped = body.replace("\\", "\\\\").replace('"', '\\"')
    return f'bp{number} {va:08x} "{escaped}"'


MOUSE = ("poi(00544cfc)>>by(0054512c)", "poi(00544d00)>>by(0054512c)")
BOUNDS = tuple(f"poi({a:08x})>>by(0054512c)" for a in (0x544CE8, 0x544CEC, 0x544CF0, 0x544CF4))
ACTIVE = "(@$t0 >= 3) & (@$t0 <= 4) & (@$tid == @$t1)"
DESCRIPTOR_EBX = "(" + " | ".join(f"(@ebx == {a:08x})" for a in DESCRIPTORS) + ")"


def snapshot_commands(indices=range(6), *, include_layout=True) -> str:
    """Read-only live snapshot, usable at readiness and at a host-owned pause."""
    state = "poi(00532048)"
    layout = printf("LAYOUT", "battle=%p surface=%p size=(%d,%d) renderer=%p owner=%p arena=(%d,%d) camera=(%d,%d) input_bounds=(%d,%d,%d,%d) mouse=(%d,%d) selected=%d player=%d attack=%d",
        state, "poi(005202e0)", "wo(poi(005202e0))", "wo(poi(005202e0)+2)", "poi(00511230)", "poi(005199d8)",
        f"poi({state}+0n804)", f"poi({state}+0n800)", f"poi({state}+0n808)", f"poi({state}+0n812)", *BOUNDS, *MOUSE,
        "poi(00511b58)", "poi(005202ec)", "poi(0053205c)")
    parts = [layout] if include_layout else []
    for i in indices:
        desc = DESCRIPTORS[i]
        # Native419B80 uses +14 as the hit sprite, falling back to +10 at-1.
        # The pinned descriptors all use a real +14 index. Guard it before
        # traversing the resource table. Native hit right/bottom exclude its
        # last pixel (CMP x, origin+width-1 / JGE).
        sprite = f"poi(poi(00532050)+poi({desc+20:08x})*4)"
        row = printf("DESCRIPTOR", f"index={i} desc={desc:08x} xy=(%d,%d) size=(%d,%d) hit_right_bottom_exclusive=(%d,%d) state=%x hover=%p callback=%p type=%x sprite=%d sprite_ptr=%p",
            f"poi({desc:08x})", f"poi({desc+4:08x})", f"wo({sprite})", f"wo({sprite}+2)",
            f"poi({desc:08x})+wo({sprite})-1", f"poi({desc+4:08x})+wo({sprite}+2)-1", f"by({desc+8:08x})",
            f"poi({desc+28:08x})", f"poi({desc+32:08x})", f"by({desc+48:08x})", f"poi({desc+20:08x})", sprite)
        x, y = DESCRIPTOR_XY[i]
        parts.append(guard(f"(poi({desc:08x}) == 0n{x}) & (poi({desc+4:08x}) == 0n{y}) & (poi({desc+32:08x}) == {CALLBACKS[i]:08x})"
            + f" & (poi({desc+12:08x}) == 00532050) & (poi({desc+20:08x}) < 0n32) & (poi({desc+20:08x}) >= 0)",
            guard(f"({sprite} >= 00010000) & ({sprite} <= 0n4294963200)", row, "descriptor_sprite_pointer"), "descriptor_contract"))
    unit_type = "wo(poi(00532048)+poi(00511b58)*0n31+0n852)"
    if include_layout:
        parts.append(guard("(poi(00511b58) >= 0) & (poi(00511b58) <= 0n21)",
            guard(f"({unit_type} <= 0n40)", printf("SELECTED_COMMAND_FLAGS", "unit=%d type=%d attack_available=%d attack_enabled=%d",
                "poi(00511b58)", unit_type, f"by(0051257e+{unit_type}*0n88)", f"by(00512582+{unit_type}*0n88)"), "unit_type"), "unit_index"))
    return guard("(poi(00532048) >= 00010000) & (poi(00532048) <= 0n4294959104) & (poi(005202e0) >= 00010000) & (poi(00532050) >= 00010000)", "; ".join(parts), "snapshot_pointers")


def snapshot_script() -> str:
    """Canonical multi-line snapshot file for independent host reconstruction."""
    return "\n".join(snapshot_commands(pair, include_layout=(pair == (0, 1))) for pair in ((0, 1), (2, 3), (4, 5))) + "\n"


def commands() -> dict[int, tuple[int, str, str]]:
    """ID -> (VA, body, class). Only setup/restore classes mutate the target."""
    result = {}
    def add(i, va, body, kind="observer"):
        result[i] = (va, body, kind)
    # Fast-forward only the main startup Sleep. The three worker Sleep sites
    # are deliberately never instrumented: run-01 stopped on46E6DF in a
    # worker immediately after the main thread disabled its startup probes.
    # A queued breakpoint event is consistent with that log, not reproduced
    # proof of the mechanism. Omitting worker breakpoints also preserves their
    # native delays and avoids needing to retire a live worker breakpoint.
    # Native resource initialization and all DirectInput calls still run.
    for i, va in enumerate((MAIN_STARTUP_SLEEP_VA,)):
        add(i, va, f".if (@$t0 == 0) {{ .if (@$t18 < 0n8) {{ " + printf("FORCED_STARTUP_SLEEP", f"next={va+7:08x}")
            + f"; r @$t18=@$t18+1; }}; r eip={va+7:08x}; r esp=@esp+4; }}; gc", "setup")
    main = "ed 00544cfc (0n540<<by(0054512c)); ed 00544d00 (0n278<<by(0054512c)); eb 005451c0 80; ed 00544d04 1"
    load = "ed 00544cfc (0n320<<by(0054512c)); ed 00544d00 (0n166<<by(0054512c)); eb 005451c0 80; ed 00544d04 1"
    add(4, 0x419B80, f".if (@$t0 == 0) {{ .if (poi(00543d7c) != 5) {{ {main}; }} .else {{ {load}; }}; }}; gc", "setup")
    add(5, 0x419C51, ".if ((@$t0 == 0) & (poi(00543d7c) != 5)) { r eax=1; } .elsif ((" + ACTIVE + ") & " + DESCRIPTOR_EBX
        + " & (@eax != 0) & (@$t13 < 0n256)) { " + printf("COMMAND_CLICK_GATE", "desc=%p result=%d state=%x mouse=(%d,%d) callback=%p",
            "@ebx", "@eax", "by(@ebx+8)", *MOUSE, "poi(@ebx+20)") + "; r @$t13=@$t13+1; }; gc", "setup")
    add(6, 0x447780, ".if (@$t0 == 0) { " + printf("FORCED_LOAD_ROUTE", "choice=5 input_proof=0")
        + "; ed 00543d7c 5; ed 00543d78 1; r eip=poi(@esp); r esp=@esp+4; }; gc", "setup")
    add(7, 0x448A68, f".if ((@$t0 == 0) & (poi(00543d7c) == 5)) {{ {load}; r eax=1; }}; gc", "setup")
    add(8, 0x448AE3, ".if ((@$t0 == 0) & (poi(00543d7c) == 5)) { r eax=1; }; gc", "setup")
    add(9, 0x40B660, ".if (@$t0 == 0) { " + guard("(poi(005202e4) >= 00010000) & (poi(005202ec) == 0)",
        "; ".join(f"bd {i}" for i in (0, 4, 6, 7, 8, 9)) + "; r @$t0=1; eb 005451c0 00; ed 00544d04 0; "
        + printf("FORCED_LOAD_COMPLETE", "gd=%p slot=0 mouse_latch_released=1 input_proof=0", "poi(005202e4)"), "loaded_map") + "; }; gc", "setup")
    actor_contract = ("(poi(@$t3+0n140000) == 0n100) & (poi(@$t3+0n140004) == 0n100) & (poi(005202ec) == 0)"
        " & (poi(@$t3+23ee6) == 0016000e) & (by(@$t3+23eea) == 0) & (wo(@$t3+23eec) == 5)"
        " & (poi(@$t3+24a3a) == 0009005a) & (by(@$t3+24a3e) == 1) & (wo(@$t3+24a40) == 5)"
        " & (poi(@$t3+22313) == 1) & (poi(@$t3+228a2) == 0)")
    forced = "r @$t3=poi(005202e4); " + guard(actor_contract,
        "r @$t1=@$tid; r @$t2=@esp; r @$t4=poi(0051d01c); "
        + printf("FORCED_BATTLE_SETUP", "attacker=0 defender=4 gd=%p attacker_old_xy=(14,22) attacker_new_xy=(89,9) defender_xy=(90,9) flag_address=0051d01c old_flag=%x new_flag=1 caller_esp=%p input_proof=0",
                 "@$t3", "@$t4", "@$t2")
        + "; ed @$t3+23ee6 00090059; ed 0051d01c 1; r esp=@esp-0n36; ed @esp @edi @esi @ebp (@esp+0n36) @ebx @edx @ecx @eax @efl; "
          "r esp=@esp-4; ed @esp 0040b0c3; r eax=0; r edx=4; r ebx=0; r @$t0=2; r eip=0041ad20", "known_slot0_actors")
    restore = guard("(@$tid == @$t1) & (@esp == @$t2-0n36)",
        printf("FORCED_CALL_RETURN", "saved_esp=%p battle=%p owner=%p restore_flag=%x", "@$t2", "poi(00532048)", "poi(005199d8)", "@$t4")
        + "; ed 0051d01c @$t4; r edi=poi(@esp); r esi=poi(@esp+4); r ebp=poi(@esp+8); r ebx=poi(@esp+0n16); r edx=poi(@esp+0n20); "
          "r ecx=poi(@esp+0n24); r eax=poi(@esp+0n28); r efl=poi(@esp+0n32); r esp=@esp+0n36; r @$t0=5; bd 10; bd 11; bd 12; "
        + printf("CALLER_RESTORED", "map_continuation=0040b0c3 natural_route=0"), "forced_call_return_identity")
    add(10, 0x40B0C3, ".if (@$t0 == 1) { " + forced + "; } .elsif (@$t0 >= 2) { " + restore + "; }; gc", "setup_restore")
    add(11, 0x41CE7A, ".if ((@$t0 == 2) & (@$tid == @$t1)) { .if (@$t7 == 0) { r @$t5=poi(00544cfc); r @$t6=poi(00544d00); r @$t7=1; }; "
        + printf("FORCED_ENTRY_DIALOG", "old_eax=%p point=(%d,%d) input_proof=0", "@eax", "poi(@esp+10c)+1", "@ebx+1")
        + "; ed 00544cfc ((poi(@esp+10c)+1)<<by(0054512c)); ed 00544d00 ((@ebx+1)<<by(0054512c)); r eax=1; }; gc", "setup")
    add(12, 0x41B043, ".if ((@$t0 == 2) & (@$t7 == 1)) { " + printf("ENTRY_DIALOG_RETURN", "choice=%d restore_raw=(%p,%p)", "@eax", "@$t5", "@$t6")
        + "; ed 00544cfc @$t5; ed 00544d00 @$t6; r @$t7=0; }; gc", "setup")
    add(13, 0x42E9E0, guard("(@$t0 == 2) & (@$tid == @$t1)",
        printf("NATIVE_BATTLE_ENTRY", "caller=%p attacker=%p defender=%p", "poi(@esp)", "@eax", "@edx")
        + "; r @$t0=3; bd 11; bd 12; " + "; ".join(f"be {i}" for i in range(20, 57) if i != 25) + "; gc", "battle_entry_identity"))
    ready_contract = ("(wo(poi(005202e0)) == 0n1280) & (wo(poi(005202e0)+2) == 0n720) & (poi(005199d8) == 0042e8b0)"
        " & (poi(poi(00532048)+0n804) >= 1) & (poi(poi(00532048)+0n804) <= 0n20)"
        " & (poi(poi(00532048)+0n800) == 7) & (poi(poi(00532048)+0n812) == 0)"
        " & (poi(poi(00532048)+0n808) >= 0) & (((poi(poi(00532048)+0n804) <= 0n17) & (poi(poi(00532048)+0n808) == 0))"
        " | ((poi(poi(00532048)+0n804) > 0n17) & (poi(poi(00532048)+0n808) <= poi(poi(00532048)+0n804)-0n17)))")
    add(14, 0x42F2FA, guard("(@$t0 == 3) & (@$tid == @$t1) & (poi(00532048) >= 00010000) & (poi(005202e0) >= 00010000)",
        guard(ready_contract, printf("INITIAL_PRESENT_RETURN", "caller=0042f2f5") + "; " + snapshot_commands((0,)) + "; bd 14; gc", "expanded_layout"), "ready_pointers"))
    # Acquisition executes natively. These are the HRESULT return sites, not
    # the old bypass points. Logging never changes EAX or its following TEST.
    for i, va, name in ((15, 0x47BD6F, "mouse"), (16, 0x47BDB7, "keyboard")):
        add(i, va, ".if (@$t19 < 0n16) { " + printf("ACQUIRE_RETURN", f"device_kind={name} hresult=%p device=%p hwnd=%p", "@eax", "poi(@esi+8)" if name == "mouse" else "poi(@esi+4)", "poi(005452dc)") + "; r @$t19=@$t19+1; }; gc")
    # Consecutive native instruction boundaries divide the six-descriptor
    # snapshot below CDB's command length limit. They do not skip instructions.
    for i, va, indices in ((17, 0x42F304, (1, 2)), (18, 0x42F309, (3, 4))):
        add(i, va, guard("(@$t0 == 3) & (@$tid == @$t1)", snapshot_commands(indices, include_layout=False) + f"; bd {i}; gc", "ready_snapshot_phase"))
    add(19, 0x42F311, guard("(@$t0 == 3) & (@$tid == @$t1)", snapshot_commands((5,), include_layout=False) + "; r @$t0=4; bd 19; "
        + printf("READY", "stage=" + STAGE + " resolution=1280x720 geometry_observed=1 input_proof=0 manual_proof=0") + "; gc", "ready_phase"))
    # Grid output is change/button driven. The same call's decision is logged
    # before its own downstream native input gates, without changing flags.
    changed = f"(({MOUSE[0]}) != @$t10) | (({MOUSE[1]}) != @$t11) | (by(005451c0) != 0) | (poi(00544d04) != 0)"
    add(20, 0x42CB50, f"r @$t7=0; .if (@$t12 >= 0n256) {{ bd 20; bd 21; bd 22; " + printf("LIMIT", "category=grid budget=256 observers_disabled=1") + f"; }} .elsif ({ACTIVE}) {{ .if ({changed}) {{ r @$t7=1; r @$t10={MOUSE[0]}; r @$t11={MOUSE[1]}; r @$t12=@$t12+1; "
        + printf("GRID_ENTER", "seq=%d caller=%p mouse=(%d,%d) button=%x latch=%x camera=(%d,%d)", "@$t12", "poi(@esp)", *MOUSE, "by(005451c0)", "poi(00544d04)", "poi(poi(00532048)+0n808)", "poi(poi(00532048)+0n812)") + "; }; }; gc")
    add(21, 0x42CBC1, ".if (@$t7 == 1) { " + printf("GRID_VALID", "seq=%d local=(%d,%d) world=(%d,%d) state=%p", "@$t12", "@ebp", "@eax", "@esi", "@edi", "@edx") + "; r @$t7=0; }; gc")
    add(22, 0x42CBB8, ".if (@$t7 == 1) { " + printf("GRID_REJECTED", "seq=%d eax=%p mouse=(%d,%d)", "@$t12", "@eax", *MOUSE) + "; r @$t7=0; }; gc")
    # Device HRESULT and returned buffer are always reported together. Failed
    # reads remain failed evidence, even if the caller later consumes garbage.
    add(23, 0x47C02C, ".if (@$t8 >= 0n512) { bd 23; " + printf("LIMIT", "category=device_reads budget=512 observers_disabled=1")
        + "; } .elsif ((@$t0 >= 3) & (@$t0 <= 5) & (@$tid == @$t1) & (@ebx == 00545198)) { .if ((@$t8 < 8) | (@eax != @$t9) | (poi(@esp+50) != 0) | (poi(@esp+54) != 0) | (poi(@esp+5c) != @$t16)) { "
        + printf("DEVICE_READ_RETURN", "seq=%d hresult=%p input_valid=%d device=%p caller=%p buffer=%p delta=(%d,%d,%d) buttons=%x mouse_before=(%d,%d)", "@$t8", "@eax", "(@eax == 0)", "poi(@ebx+8)", "poi(@esp+6c)", "@esp+50", "poi(@esp+50)", "poi(@esp+54)", "poi(@esp+58)", "poi(@esp+5c)", *MOUSE)
        + "; r @$t8=@$t8+1; r @$t9=@eax; r @$t16=poi(@esp+5c); }; }; gc")
    def bounded(i, va, event, fields="", args=(), condition=ACTIVE, counter=15, limit=96):
        add(i, va, f".if (@$t{counter} >= 0n{limit}) {{ bd {i}; " + printf("LIMIT", f"observer={i} budget={limit} observers_disabled=1")
            + f"; }} .elsif ({condition}) {{ " + printf(event, fields, *args)
            + f"; r @$t{counter}=@$t{counter}+1; }}; gc")
    bounded(24, 0x419C28, "COMMAND_PRE_GATES", "desc=%p state=%x mouse=(%d,%d) callback=%p", ("@ebx", "by(@ebx+8)", *MOUSE, "poi(@ebx+20)"), ACTIVE + " & " + DESCRIPTOR_EBX + " & ((@$t13 < 6) | (by(005451c0) != 0) | (poi(00544d04) != 0))", 13, 256)
    bounded(26, 0x419C5D, "COMMAND_DISPATCH", "desc=%p callback=%p state=%x mouse=(%d,%d)", ("@ebx", "poi(@ebx+20)", "by(@ebx+8)", *MOUSE), ACTIVE + " & " + DESCRIPTOR_EBX, 13, 256)
    bounded(27, 0x419CD8, "HOVER_TEXT", "desc=%p text=%p state=%x mouse=(%d,%d)", ("@ebx", "@ebp", "by(@ebx+8)", *MOUSE),
        ACTIVE + " & " + DESCRIPTOR_EBX + " & ((@ebx != @$t5) | (@ebp != @$t6))", 14, 128)
    va, body, kind = result[27]
    result[27] = (va, body.replace("r @$t14=@$t14+1", "r @$t5=@ebx; r @$t6=@ebp; r @$t14=@$t14+1"), kind)
    for i, va in enumerate(CALLBACKS, 28):
        bounded(i, va, "COMMAND_CALLBACK", "desc=%p caller=%p mouse=(%d,%d) attack=%d", ("@eax", "poi(@esp)", *MOUSE, "poi(0053205c)"), counter=13, limit=256)
    bounded(34, 0x419C60, "COMMAND_RETURN", "desc=%p state=%x attack=%d mouse=(%d,%d)", ("@ebx", "by(@ebx+8)", "poi(0053205c)", *MOUSE), ACTIVE + " & " + DESCRIPTOR_EBX, 13, 256)
    bounded(35, 0x42D980, "BANNER_DRAW", "rect=(%d,%d,%d,%d) renderer=%p", ("poi(@esp+34)", "poi(@esp+28)", "poi(@esp+20)", "poi(@esp+1c)", "poi(00511230)"))
    bounded(36, 0x42DA84, "BANNER_RESTORED", "renderer=%p expected=%p mouse=(%d,%d)", ("poi(00511230)", "poi(@esp+30)", *MOUSE))
    bounded(37, 0x42DDAF, "DIALOG_DRAW", "rect=(%d,%d,%d,%d) no=(%d,%d) yes=(%d,%d) callbacks=(%p,%p)", ("poi(@esp+bc)", "poi(@esp+c0)", "poi(@esp+b4)", "poi(@esp+c4)", "poi(@esp)", "poi(@esp+4)", "poi(@esp+0n53)", "poi(@esp+0n57)", "poi(@esp+0n32)", "poi(@esp+0n85)"))
    bounded(38, 0x42DE84, "DIALOG_RESTORED", "renderer=%p expected=%p result=%d mouse=(%d,%d)", ("poi(00511230)", "poi(@esp+b0)", "poi(00532080)", *MOUSE))
    bounded(39, 0x42DAB0, "DIALOG_YES_CALLBACK", "caller=%p desc=%p", ("poi(@esp)", "@eax"))
    bounded(40, 0x42E5A0, "RESULTS_ENTRY", "battle=%p", ("poi(00532048)",))
    bounded(41, 0x42F471, "RESULTS_RETURN", "result=%d battle=%p", ("@ebp", "poi(00532048)"))
    bounded(42, 0x42F5B1, "OWNER_RESTORED", "battle=%p renderer=%p owner=%p expected_owner=%p bounds=(%d,%d,%d,%d)", ("poi(00532048)", "poi(00511230)", "poi(005199d8)", "poi(@esp+84)", *BOUNDS))
    bounded(43, 0x41B14A, "UNIT_ATTACK_CONTINUATION", "result=%d battle=%p owner=%p", ("@eax", "poi(00532048)", "poi(005199d8)"))
    bounded(44, 0x406FA0, "MAP_REDRAW", "battle=%p owner=%p surface=%p size=(%d,%d)", ("poi(00532048)", "poi(005199d8)", "poi(005202e0)", "wo(poi(005202e0))", "wo(poi(005202e0)+2)"), "(@$t0 == 5) & (@$tid == @$t1)", 17, 16)
    bounded(45, 0x42E4F7, "CAMERA_AFTER_PAN", "camera=(%d,%d) arena=(%d,%d) mouse=(%d,%d)", ("poi(poi(00532048)+0n808)", "poi(poi(00532048)+0n812)", "poi(poi(00532048)+0n804)", "poi(poi(00532048)+0n800)", *MOUSE), ACTIVE + " & (poi(poi(00532048)+0n808) != @$t18)", 14, 128)
    va, body, kind = result[45]
    result[45] = (va, body.replace("r @$t14=@$t14+1", "r @$t18=poi(poi(00532048)+0n808); r @$t14=@$t14+1"), kind)
    bounded(46, 0x426E20, "RECENTER_ENTRY", "selected=%d camera=(%d,%d)", ("@eax", "poi(poi(00532048)+0n808)", "poi(poi(00532048)+0n812)"))
    bounded(47, 0x460AF0, "CURSOR_REQUEST", "caller=%p request=(%d,%d) mouse=(%d,%d)", ("poi(@esp)", "(@edx & 0xffff)", "(@ebx & 0xffff)", *MOUSE))
    bounded(48, 0x460B1A, "CURSOR_RETURN", "caller=%p mouse=(%d,%d) raw=(%p,%p)", ("poi(@esp)", *MOUSE, "poi(005451a8)", "poi(005451ac)"))
    bounded(49, 0x460EA1, "PRESENT_BODY", "caller=%p object=%p surface=%p size=(%d,%d)", ("poi(@esp+4)", "@eax", "poi(005202e0)", "wo(poi(005202e0))", "wo(poi(005202e0)+2)"), counter=19, limit=32)
    bounded(50, 0x42E506, "COMMAND_SCAN_RETURN", "result=%d mouse=(%d,%d)", ("@eax", *MOUSE), ACTIVE + " & (@eax != 0)", 13, 256)
    bounded(51, 0x47C03C, "MOUSE_REACQUIRE_OR_COPY", "caller=%p eax=%p logical=(%d,%d)", ("poi(@esp+6c)", "@eax", *MOUSE), ACTIVE + " & (@ebx == 00545198) & (@$t9 != 0)", 19, 32)
    bounded(52, 0x42CBCC, "GRID_RIGHT_GATE", "result=%d world=(%d,%d) mouse=(%d,%d)", ("@eax", "@esi", "@edi", *MOUSE), ACTIVE + " & (@eax != 0)", 13, 256)
    # The next three observers cover native grid command branches. Their
    # exact sites are byte-bound but no branch result is changed or inferred.
    bounded(53, 0x42E53E, "TURN_LOOP_CONTINUATION", "selected=%d attack=%d mouse=(%d,%d)", ("poi(00511b58)", "poi(0053205c)", *MOUSE), ACTIVE + " & (poi(00544d04) != 0)", 14, 128)
    bounded(54, 0x42F4E1, "RESULTS_MESSAGE_RETURN", "renderer=%p owner=%p", ("poi(00511230)", "poi(005199d8)"))
    bounded(55, 0x42DAE0, "DIALOG_ENTRY", "caller=%p renderer=%p", ("poi(@esp)", "poi(00511230)"))
    bounded(56, 0x42D730, "BANNER_ENTRY", "caller=%p renderer=%p", ("poi(@esp)", "poi(00511230)"))
    return result


def validate_commands(rows: dict[int, tuple[int, str, str]]) -> None:
    """Fail on observer writes, unknown IDs, duplicate sites and command growth."""
    sites = {}
    for number, (va, body, kind) in rows.items():
        if not 0 <= number <= LAST_BREAKPOINT_ID or kind not in {"observer", "setup", "setup_restore"}:
            raise ValueError("unallocated breakpoint or command class")
        if va in sites:
            raise ValueError("breakpoint site collision")
        sites[va] = number
        if kind == "observer" and re.search(r"(?:^|[;{}]\s*)\s*(?:e[bdwq]\s|r\s+(?:@?(?:eax|ebx|ecx|edx|esi|edi|ebp|esp|eip|efl))\s*=)", body, re.I):
            raise ValueError(f"observer {number} mutates target")
        if len(breakpoint(number, va, body)) > 4000:
            raise ValueError("CDB command exceeds4095-byte limit")
        for referenced in re.findall(r"\b(?:bd|be|bc)\s+([0-9]+)(?=[\s;}]|$)", body):
            if int(referenced) not in rows:
                raise ValueError(f"breakpoint {number} references undefined ID {referenced}")
    if any(va in (0x47BD66, 0x47BDAE, 0x47BF30) for va in sites):
        raise ValueError("native acquisition/poll bypass site forbidden")
    if any(va in WORKER_SLEEP_VAS for va in sites):
        raise ValueError("worker Sleep breakpoints forbidden")


def build_probe(original: bytes, candidate: bytes, save: bytes, *, stage=STAGE, resolution=RESOLUTION) -> tuple[str, dict]:
    if stage != STAGE or resolution != RESOLUTION:
        raise ValueError("only exact battle-HD stage at1280x720 is supported")
    for label, data, expected in (("original", original, ORIGINAL_SHA256), ("candidate", candidate, CANDIDATE_SHA256), ("save", save, SAVE_SHA256)):
        if sha(data) != expected:
            raise ValueError(label + " SHA256 mismatch")
    if len(save) != SAVE_BYTES:
        raise ValueError("slot0 size mismatch")
    rows = commands()
    validate_commands(rows)
    spans = []
    # Source records cover the complete7-byte main startup skip and16 bytes around
    # every observer. Wider native routines authenticate descriptor dimensions,
    # native acquisition and every input-read ABI used in our expressions.
    requested = {(va, 16) for va, _, _ in rows.values()}
    requested.update(((0x405EC0, 64), (0x419B80, 448), (0x47BD20, 192), (0x47BFD0, 176), (0x460AF0, 43)))
    requested.update((desc, 53) for desc in DESCRIPTORS)
    checks = []
    for va, size in sorted(requested):
        offset, current = read_va(candidate, va, size)
        old_offset, old = read_va(original, va, size)
        spans.append(dict(va=va, rva=va-IMAGE_BASE, offset=offset, original_offset=old_offset, old_hex=old.hex(), candidate_hex=current.hex()))
        # Byte comparisons are intentionally insensitive to pointer-width and
        # debugger MASM high-bit dword expansion.
        terms = [f"(by({va+i:08x}) != 0x{value:02x})" for i, value in enumerate(current)]
        for start in range(0, len(terms), 48):
            checks.append(f".if ({' | '.join(terms[start:start+48])}) {{ " + reject(f"loaded_bytes_{va+start:08x}") + " }")
    for va in (MAIN_STARTUP_SLEEP_VA,):
        if read_va(candidate, va, 7)[1] != bytes.fromhex("2eff15c0a54e00"):
            raise ValueError("reviewed Sleep instruction differs")
    lines = [".echo BHDV_STANDALONE reviewed_visible_session_required=1 no_input_injection_by_producer=1", *DEBUGGER_SETUP_COMMANDS,
        'sxe -c ".echo BHDV_EXCEPTION_AV; .exr -1; r; kb; q" av', *checks,
        f".echo BHDV_BYTE_CONTRACT candidate_sha256={CANDIDATE_SHA256} stage={STAGE} resolution={RESOLUTION} save_sha256={SAVE_SHA256}",
        ".echo BHDV_SETUP_DISCLOSURE forced_menu_load=1 forced_adjacent_attack=1 forced_entry_dialog_if_seen=1 native_acquisition=1 native_worker_sleep=1 battle_gate_forcing=0 manual_proof=0",
        *(f"r @$t{i}=0" for i in range(20)), "r @$t10=0xffffffff", "r @$t11=0xffffffff"]
    for number, (va, body, _) in rows.items():
        lines.append(breakpoint(number, va, body))
        if number >= FIRST_OBSERVER_ID:
            lines.append(f"bd {number}")
    lines.append("g")
    script = "\n".join(lines) + "\n"
    packet = dict(schema="clash95_battle_hd_visible_probe_v1", protocol=PROTOCOL, prepared=True, runtime_observed=False,
        stage=stage, resolution=resolution, candidate_sha256=sha(candidate), original_sha256=sha(original), save_sha256=sha(save), save_bytes=len(save),
        probe_sha256=sha(script.encode("ascii")), producer_sha256=sha(Path(__file__).read_bytes()), byte_spans=spans,
        breakpoints={str(k): dict(va=v[0], kind=v[2]) for k, v in rows.items()}, reserved_breakpoint_ids=[0, LAST_BREAKPOINT_ID],
        pseudo_registers="t0..t19 exclusive", readiness_marker="BHDV_READY", reject_marker="BHDV_REJECT", native_directinput_preserved=True,
        forced_setup=True, forced_battle_gates=False, forced_command_states=False, automated_input_proof=False, manual_input_proof=False, promotion_ready=False,
        startup_policy=dict(main_sleep_fast_forward_va=MAIN_STARTUP_SLEEP_VA, native_worker_sleep_vas=list(WORKER_SLEEP_VAS), worker_sleep_breakpoints=False),
        host_requirements=["Fresh explicit visible/input/capture approval and exact wrapper/configuration hashes belong to the session host.",
            "Verify candidate and unchanged private slot0 immediately before launch. Use a fresh standalone x86 CDB session with this script only.",
            "Retain owned process identity/start time, client geometry/DPI, input events and task-owned cleanup. No coordinate fallback.",
            "Wait for BHDV_READY and six live BHDV_DESCRIPTOR rows. Refresh live descriptors before each target decision.",
            "BHDV_DEVICE_READ_RETURN input_valid=1 means HRESULT zero only; it does not prove visible or manual input.",
            "Forced adjacent battle entry changes the live attacker position and UI preference. Do not save this isolated run.",
            "Logging is bounded and incomplete after its category limit. Marker absence does not prove an input was rejected.",
            "Visible pixels, successful input/callback chains, natural battle completion and restored-map interaction require separate observations."],
        host_read_contract=dict(surface_global=0x5202E0, battle_global=0x532048, input_shift=0x54512C, mouse_raw=[0x544CFC,0x544D00],
            input_bounds=[0x544CE8,0x544CEC,0x544CF0,0x544CF4], descriptors=list(DESCRIPTORS), descriptor_bytes=53,
            descriptor_fields=dict(x=0,y=4,state=8,resource_table_global=12,normal_sprite=16,hit_sprite=20,hover_callback=28,click_callback=32),
            arena_columns=804, arena_rows=800, camera_x=808, camera_y=812))
    return script, packet


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original", required=True, type=Path)
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--save", required=True, type=Path, help="unchanged original slot0.dat")
    parser.add_argument("--output-dir", required=True, type=Path, help="new external session preparation directory")
    parser.add_argument("--stage", default=STAGE)
    parser.add_argument("--resolution", default=RESOLUTION)
    args = parser.parse_args()
    script, packet = build_probe(args.original.read_bytes(), args.candidate.read_bytes(), args.save.read_bytes(), stage=args.stage, resolution=args.resolution)
    args.output_dir.mkdir(parents=True, exist_ok=False)
    probe = args.output_dir / "battle-hd-visible.cdb"
    snapshot = args.output_dir / "battle-hd-live-snapshot.cdb"
    probe.write_bytes(script.encode("ascii"))
    snapshot.write_bytes(snapshot_script().encode("ascii"))
    packet.update(original_path=str(args.original.resolve()), candidate_path=str(args.candidate.resolve()), save_path=str(args.save.resolve()),
        probe_path=str(probe.resolve()), snapshot_path=str(snapshot.resolve()), snapshot_sha256=sha(snapshot.read_bytes()))
    (args.output_dir / "battle-hd-visible-probe.json").write_text(json.dumps(packet, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(dict(prepared=True, launched=False, probe=str(probe.resolve()), packet=str((args.output_dir / "battle-hd-visible-probe.json").resolve()))))


if __name__ == "__main__":
    main()
