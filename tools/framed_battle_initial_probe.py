#!/usr/bin/env python3
"""Prepare one disclosed hidden battle entry; never execute or write a game.

Only the known original slot0 fixture, attacker0 and defender4 are supported.
After canonical initial-map closure, native PUSH EBX is observed before any
actor memory is changed. The exact original actor fields are checked there;
then one packed XY dword and the native battle-UI preference are written and
logged. Native eligibility, attack setup and the entire battle runner remain
in control. No input result, battle result, artwork or readiness is fabricated.
The final pause precedes turn/input processing and offers physical E0 only.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import re
import struct

import framed_modal_canvas_probe as shared
import framed_modal_canvas_trace as compiler

builder = shared.builder
STAGE = builder.STAGE
PROTOCOL = "constructed_slot0_initial_battle_v1"
ROUTE = "constructed_slot0_unit0_vs_unit4"
SAVE_SHA256 = "4f2182409d209985a527f07c4116b19e44332416698d6acb0a3d35ae68db8a89"
SHARED_SHA256 = "52edf115a5240111a62882069fff548460116ad2d7ee7a06d775f25494c36fe6"
COMPILER_SHA256 = "2f0ef571acdbc6892c775cc97698d535b56355c8086080713d3dfec040a6d3ba"
IMAGE_BASE = 0x400000
ATTACK, RUNNER, PRESENT_CALL, PRESENT_RETURN = 0x41AD20, 0x42E9E0, 0x42F2F5, 0x42F2FA
SENTINEL, WRAPPER = 0x406FA1, 0x51BA00
UNIT_BASE, UNIT_SIZE = 0x23EE6, 0x2D5
NATIVE_SPANS = (
    (0x406FA0, 6, "b95857700390dc837e06339f4a2a31ef9bad0b75b0fc1a6e2d344ffa598d540c"),
    (ATTACK, 1068, "6f9f97da9708edb7e23620d6e1ddcd629236862b81ff65ff3035a64e234fbddc"),
    (0x412100, 101, "bfbd7729bc885a47f2a52232f6a56c5d53ec15ef27dca0f38c2367153dd44419"),
    (0x412B60, 48, "764c2b5f3e6b45e2a9395e70ef3115257130d6fc280aee030b5f445f52a631c9"),
    (0x422B80, 27, "cdc5d1347c3b91a8a1cfa580d29cdcd70a4278dff15f0a2ab27ead01833527f8"),
    (0x42D4E0, 32, "8117fcd35e34c2cf52b40e3cafd3cf1ca19d1274c0b575dcddd8df302b2165ab"),
    (RUNNER, 2345, "403c7202f89f42ad25e50e77904e5dd734700a936ea35849767ece90c6e4a063"),
)
LIMITS = [
    "Preparation and trace validation only; a separately reviewed hidden host, deadline and owned-process cleanup are required.",
    "Slot0 unit0 XY14,22 is changed to89,9 beside unit4 at90,9; 51D01C is forced to1. Every old/new value is disclosed.",
    "Only selected live fields and the source-bound native squad-count/eligibility gates are asserted; this is not natural movement or world-occupancy proof.",
    "No save is written by this probe. Host must bind a private copied slot0 file to the exact packet SHA before launch and preserve inputs afterward.",
    "Canonical initial-map loading retains its existing disclosed loader/input mechanism. Battle entry itself uses no OS input or forced native predicate result.",
    "The first native PUSH executes before actor validation; no actor reads or actor mutation occur before that observer in Unit_Attack.",
    "Physical E0 is an inherited centered battle software surface, not the primary surface or an owned castle-canvas mirror.",
    "Primary-only overlays, visible composition, battle commands/outcomes, natural input and promotion are not proven.",
    "The intentional pause at42F2FA does not prove battle completion or return to the interrupted map call.",
]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canonical_template(original, resolution, *, minimap_viewport=False):
    for module, expected in ((shared, SHARED_SHA256), (compiler, COMPILER_SHA256)):
        if sha(Path(module.__file__).read_bytes()) != expected:
            raise ValueError("reviewed canonical map compiler/producer dependency changed")
    return shared.canonical_template(original, resolution, minimap_viewport=minimap_viewport)


def _printf(text, *args):
    return shared._printf(text, *args)


def _reject(reason):
    return _printf("BINIT_REJECT reason=" + reason + " phase=%d tid=%x eip=%p esp=%p", "@$t0", "@$tid", "@eip", "@esp") + "; q"


def _guard(condition, body, reason):
    return f".if ({condition}) {{ {body} }} .else {{ {_reject(reason)} }}"


def _zero_state(state_va):
    # The entire used RW-state object must remain untouched, including pending
    # allocations and immutable pixel identities. Its4096-byte allocation and
    # initial zeros are separately authenticated by the whole builder extra.
    return "((" + " | ".join(f"poi({state_va+i:08x})" for i in range(0, 128, 4)) + ") == 0)"


def _surface(width, height):
    return (f"(poi(005202e0) == @$t4) & (wo(@$t4) == 0n{width}) & (wo(@$t4+2) == 0n{height})"
            " & (poi(@$t4+4) == @$t5) & (poi(@$t4+b8) == 0050ee24)")


def _commands(width, height, state_va):
    ident = "tid=%x eip=%p esp=%p"
    ia = ("@$tid", "@eip", "@esp")
    zero = _zero_state(state_va)
    def record(name, tail="", args=()):
        return _printf("BINIT_" + name + " " + ident + (" " + tail if tail else ""), *ia, *args)
    def step(phase, va, depth, condition, body):
        check = (f"(@$t0 == 0n{phase}) & (@$tid == @$t2) & (@eip == {va:08x})"
                 f" & (@esp == @$t3-0n{depth})")
        # Stack identity is checked before any stack-based dereference.
        return _guard(check, _guard(condition, body, "native_contract"), "native_identity")
    def state_record(event):
        return record("INACTIVE", f"event={event} state={state_va:08x} checked_bytes=128 all_zero=1")
    closed = _printf("PTILE_TRACE_CLOSED " + ident, *ia)
    disable = "; ".join("bd " + str(n) for n in range(70, 78))
    arm = "; ".join("be " + str(n) for n in range(80, 90))
    handoff = _guard("(@eip == 00406fa0) & (@$t14 == 1) & (@$t13 == 4) & (@$t7 == 1)",
        "r @$t1=poi(005202e4); r @$t4=poi(005202e0); " + _guard(
            "(@$t1 >= 00010000) & (@$t1 <= 0n4293918720) & (@$t4 >= 00010000) & (@$t4 != 0051d4c0)",
            "r @$t5=poi(@$t4+4); " + _guard(
                f"(@$t5 >= 00010000) & (@$t5 <= 0n{0x100000000-width*height}) & " + _surface(width, height)
                + " & (poi(005199d8) == 0040ad40) & (poi(00526990) == 0) & (poi(00526994) == 0) & (poi(005202ec) == 0)",
                _guard(zero,
                    closed + "; " + disable + "; r @$t0=1; r @$t2=@$tid; r @$t3=@esp; "
                    + record("HANDOFF", "gd=%p surface=%p base=%p size=(%d,%d) owner=0040ad40 player=0",
                             ("@$t1", "@$t4", "@$t5", "wo(@$t4)", "wo(@$t4+2)"))
                    + "; " + state_record("HANDOFF") + "; "
                    + record("FORCE_CALL", "entry=0041ad20 attacker=0 defender=4 ebx=0 sentinel=00406fa1 forced=1")
                    + "; r eax=0; r edx=4; r ebx=0; r esp=@esp-4; ed @esp 00406fa1; "
                    + arm + "; r eip=0041ad20; gc", "active_modal_state"), "map_surface"), "null_map"), "map_handoff")
    # The first native instruction has only pushed the deliberately supplied
    # EBX0. Actor checks and the two data writes occur before native reads.
    actors = ("(poi(005202e4) == @$t1) & (poi(@$t1+222e0) == 0n100) & (poi(@$t1+222e4) == 0n100)"
              " & (poi(005202ec) == 0) & (poi(@$t1+22313) == 1) & (poi(@$t1+228a2) == 0)"
              " & (poi(@$t6) == 0016000e) & (by(@$t6+4) == 0) & (wo(@$t6+6) == 5)"
              " & (wo(@$t6+25) == 0xffff) & (by(@$t6+2d0) == 0)"
              " & (poi(@$t8) == 0009005a) & (by(@$t8+4) == 1) & (wo(@$t8+6) == 5)"
              " & (wo(@$t8+25) == 0xffff) & (by(@$t8+2d0) == 0)")
    prologue = step(1, 0x41AD21, 8, "(poi(@esp) == 0) & (poi(@esp+4) == 00406fa1) & (@eax == 0) & (@edx == 4) & (@ebx == 0)",
        "r @$t6=@$t1+23ee6; r @$t8=@$t1+24a3a; " + _guard(actors,
        record("PROLOGUE", "after_first_push=1 saved_ebx=0 sentinel=00406fa1") + "; "
        + record("ACTORS", "gd=%p attacker=%p defender=%p old_attacker_xy=(14,22) defender_xy=(90,9) owners=(0,1) first_types=(5,5) squad_counts=(1,1) map=(100,100) control_flags=(1,0)", ("@$t1", "@$t6", "@$t8"))
        + "; r @$t12=poi(0051d01c); "
        + record("MUTATION", "xy_address=%p old_xy=%x new_xy=00090059 flag_address=0051d01c old_flag=%x new_flag=1 isolated_fixture=1", ("@$t6", "poi(@$t6)", "@$t12"))
        + "; ed @$t6 00090059; ed 0051d01c 1; "
        + record("MUTATION_DONE", "xy_address=%p xy=%x flag=%x", ("@$t6", "poi(@$t6)", "poi(0051d01c)"))
        + "; r @$t0=2; gc", "known_actors"))
    runner_args = "(@eax == @$t6) & (@edx == @$t8) & (@ebx == 0) & (@ecx == 0)"
    battle_state = ("(poi(00532048) >= 00010000) & (poi(00532048) <= 0n4294959104)"
                    " & (poi(005199d8) == 0042e8b0) & (poi(005202e4) == @$t1)"
                    " & (poi(0053204c) != 0) & (poi(00532050) != 0) & (poi(00532054) != 0)"
                    " & (poi(00532058) != 0) & (poi(005202bc) != 0) & (poi(005202ec) <= 4)"
                    " & (poi(00511b58) <= 0n21)")
    # Native runner assigns these globals from battle+344 and battle+F68;
    # the source-authenticated command helper indexes31-byte squads at+354.
    # Only evaluate these nested pointer reads after battle_state bounds pass.
    selection = ("(poi(poi(00532048)+344) == poi(005202ec))"
                 " & (poi(poi(00532048)+poi(005202ec)*4+0xf68) == poi(00511b58))"
                 " & (wo(poi(00532048)+poi(00511b58)*1f+354) <= 0n40)")
    present = step(5, PRESENT_CALL, 1036, "(@eax == 00544cd8) & " + battle_state,
        _guard(selection, record("PRESENT_CALL", "target=0051ba00 battle=%p owner=%p player=%d selected=%d selected_type=%d resources=(%p,%p,%p,%p,%p)",
               ("poi(00532048)", "poi(005199d8)", "poi(005202ec)", "poi(00511b58)",
                "wo(poi(00532048)+poi(00511b58)*1f+354)",
                "poi(0053204c)", "poi(00532050)", "poi(00532054)", "poi(00532058)", "poi(005202bc)"))
        + "; r @$t0=6; gc", "battle_selection"))
    ready = step(7, PRESENT_RETURN, 1036, battle_state,
        _guard(zero + " & " + _surface(width, height) + " & " + selection,
            record("PRESENT_RETURN", "caller=0042f2f5 wrapper=0051ba00") + "; " + state_record("READY")
            + "; " + record("SURFDUMP_READY", f"surface=%p base=%p size=({width},{height}) bytes={width*height} vtable=0050ee24 owner=0042e8b0 state={state_va:08x} capture=physical_battle_e0 manual_input_proof=0",
                              ("@$t4", "@$t5"))
            + "; r @$t0=8; " + "; ".join(f"bd {n}" for n in range(80,90))
            + "; .echo BINIT_SURFDUMP_HOST_READY", "capture_ownership"))
    commands = {
        80: (SENTINEL, _reject("unexpected_attack_return")),
        81: (0x41AD21, prologue),
        82: (0x41AE05, step(2, 0x41AE05, 860,
            "(@eax == 1) & (@ebp == @$t6) & (poi(@$t6) == 00090059) & (poi(@$t8) == 0009005a)",
            record("ELIGIBLE", "eax=%x attacker=%p", ("@eax", "@ebp")) + "; r @$t0=3; gc")),
        83: (0x41B05E, step(3, 0x41B05E, 860, "(@ecx == 1) & (@ebp == @$t6) & (poi(0051d01c) == 1)",
            record("UI_GATE", "ecx=%x flag=%x", ("@ecx", "poi(0051d01c)")) + "; r @$t0=4; gc")),
        84: (0x41B145, step(4, 0x41B145, 864, runner_args + " & (poi(@esp) == 0)",
            record("RUNNER_CALL", "attacker=%p defender=%p ebx=%x ecx=%x argument=%x", ("@eax", "@edx", "@ebx", "@ecx", "poi(@esp)")) + "; r @$t0=5; gc")),
        85: (RUNNER, step(5, RUNNER, 868, runner_args + " & (poi(@esp) == 0041b14a) & (poi(@esp+4) == 0)",
            record("RUNNER_ENTRY", "attacker=%p defender=%p caller=%p argument=%x", ("@eax", "@edx", "poi(@esp)", "poi(@esp+4)"))
            + "; r @$t0=9; gc")),
        86: (PRESENT_CALL, present.replace("@$t0 == 0n5", "@$t0 == 0n9", 1)),
        87: (WRAPPER, step(6, WRAPPER, 1040, "(@eax == 00544cd8) & (poi(@esp) == 0042f2fa)",
            record("WRAPPER_ENTRY", "caller=%p cursor=%p", ("poi(@esp)", "@eax")) + "; r @$t0=7; gc")),
        88: (PRESENT_RETURN, ready),
        89: (0x41B14A, _reject("unexpected_runner_return")),
    }
    return handoff, commands


def build_probe(original, candidate, save, *, candidate_sha256, stage, resolution,
                route, minimap_viewport=False):
    if stage != STAGE or route != ROUTE or type(minimap_viewport) is not bool:
        raise ValueError("exact stage, constructed route and boolean minimap profile required")
    if sha(save) != SAVE_SHA256 or len(save) != 586414:
        raise ValueError("only the authenticated unchanged original slot0 fixture is supported")
    if not re.fullmatch(r"[0-9a-fA-F]{64}", candidate_sha256 or "") or sha(candidate) != candidate_sha256.lower():
        raise ValueError("candidate SHA mismatch")
    rebuilt, metadata, extra, template = canonical_template(original, resolution, minimap_viewport=minimap_viewport)
    if candidate != rebuilt:
        raise ValueError("candidate differs from whole canonical modal builder reconstruction")
    records, conditions = [], []
    for va, size, original_digest in NATIVE_SPANS:
        off, old = shared._read(original, va, size)
        new = shared._read(candidate, va, size)[1]
        if sha(old) != original_digest:
            raise ValueError(f"native source span mismatch at{va:08x}")
        expected = bytearray(old)
        if va == RUNNER:
            i = PRESENT_CALL-va
            expected[i:i+5] = b'\xe8' + struct.pack('<i', WRAPPER-PRESENT_RETURN)
        if bytes(expected) != new:
            raise ValueError(f"battle native span has an unreviewed change at{va:08x}")
        records.append(dict(va=va, rva=va-IMAGE_BASE, offset=off, old_hex=old.hex(), candidate_hex=new.hex()))
    off, wrapper = shared._read(candidate, WRAPPER, 160)
    records.append(dict(va=WRAPPER, rva=WRAPPER-IMAGE_BASE, offset=off,
                        old_hex=shared._read(original, WRAPPER, 160)[1].hex(), candidate_hex=wrapper.hex()))
    for row in records:
        conditions.extend(f"(by({row['va']+i:08x}) != 0x{v:02x})" for i,v in enumerate(bytes.fromhex(row['candidate_hex'])))
    reject = _reject("loaded_bytes").replace(r'\"', '"').replace(r'\\n', r'\n')
    checks = '\n'.join(f".if ({' | '.join(conditions[i:i+48])}) {{ {reject} }}" for i in range(0,len(conditions),48))+'\n'
    checks += f".echo BINIT_BYTE_CONTRACT_PASS candidate_sha256={sha(candidate)} route={route}\n"
    width,height = map(int,resolution.split('x'))
    handoff, commands = _commands(width,height,metadata['state_va'])
    startup = (f".echo BINIT_CONTRACT stage={stage} resolution={resolution} candidate_sha256={sha(candidate)} "
               f"save_sha256={SAVE_SHA256} route={route} protocol={PROTOCOL} runtime_acceptance=0\n")
    for bp,(va,body) in commands.items():
        startup += f'bp{bp} {va:08x} "{body}"\nbd {bp}\n'
    packet = dict(schema='clash95_framed_battle_initial_probe_packet_v1',prepared=True,runtime_ready=False,
        stage=stage,resolution=resolution,route=route,protocol_revision=PROTOCOL,candidate_sha256=sha(candidate),
        original_sha256=sha(original),save_sha256=SAVE_SHA256,save_bytes=len(save),minimap_viewport=minimap_viewport,
        source_sha256=metadata['source_sha256'],producer_sha256=sha(Path(__file__).read_bytes()),
        shared_producer_sha256=SHARED_SHA256,shared_compiler_sha256=COMPILER_SHA256,
        builder_sha256=sha(Path(builder.__file__).read_bytes()),base_probe_sha256=sha(shared.BASE_PROBE.read_bytes()),
        map_probe_template=template,canonical_extra_sha256=sha(extra.encode()),map_template_sha256=sha(template.encode('ascii')),
        byte_checks_before_first_breakpoint=checks,startup_commands_before_final_g=startup,handoff_action=handoff,
        breakpoint_commands={str(k):dict(va=v[0],body=v[1]) for k,v in commands.items()},byte_spans=records,
        canvas_state_va=metadata['state_va'],state_bytes=128,stop_va=PRESENT_RETURN,return_sentinel_va=SENTINEL,
        expected_capture_surface='physical_battle_e0',final_host_marker='BINIT_SURFDUMP_HOST_READY',
        host_read_contract=dict(surface_global=0x5202E0,state_va=metadata['state_va'],state_bytes=128,state_all_zero=True,
            header_bytes=188,header_reads=2,state_reads=2,e0_reads=2,pixel_reads=1,vtable=0x50EE24,
            pause_va=PRESENT_RETURN,deadline_seconds=120,primary_capture=False),
        forced_native_dispatch=True,forced_gate_result=False,forced_os_input=False,manual_input_proof=False,
        natural_route_proof=False,promotion_ready=False,limits=LIMITS)
    # The compiler inventories all implicit/explicit IDs after fixed startup
    # expansion, so both site collisions and the real combined line limit fail.
    compiler.compile_probe(packet)
    return packet
