#!/usr/bin/env python3
"""Prepare source-bound hidden castle probe packets; never run a debugger.

The packet requires a separate host integration. Its canonical map template
retains initial trace/visibility observations. Only its unique dump-action
token is replaced after the fourth update; that action closes the PTILE trace
and disables its observers before a disclosed forced native castle call.

Facilities traverse the initialized overview's real case branch, resource
prelude and CALL ECX. The input loop is bypassed and the flipping gate result
is forced once, explicitly. This is never a natural click or manual-input
proof. Capture is paused after the selected first Render_Present call returns;
that function includes cursor composition, not a guarantee of visible output.
Only the physical memory map is offered to the host. Primary-only overlays
remain outside that capture. Unexpected native return quits as a failure.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
import re
import struct
import sys

import build_framed_candidate as builder
from render_cdb_surface_probe import BASE_PROBE, render_probe

STAGE = builder.STAGE
DUMP_TOKEN = "__SURFACE_DUMP_ACTION__"
OVERVIEW = 0x422180
PRESENT = 0x460EA0
SENTINEL = 0x406FA1
LOOP = 0x4223C1
GATE = 0x422590
CALLBACK = 0x42262C
IMAGE_BASE = 0x400000


@dataclass(frozen=True)
class Route:
    name: str
    entry_va: int
    branch_va: int | None
    command: int | None
    present_call_va: int
    local_stack_bytes: int
    entry_bytes: str
    return_bytes: str
    artwork: str

    @property
    def stop_va(self):
        return self.present_call_va + 5


ROUTES = {
    r.name: r for r in (
        Route("castle_overview", OVERVIEW, None, None, 0x42239A, 56,
              "53515256575583ec2089c5", "89f231c9b8d84c5400", "castle overview"),
        Route("hospital", 0x43DCE0, 0x4226DD, 0x99, 0x43DE4E, 1044,
              "5352565781ec000400008a400225ff000000", "890dbc38540059", "dw_20 hospital"),
        Route("school", 0x43D8E0, 0x42277B, 0x9C, 0x43DA4E, 1044,
              "5352565781ec000400008a400225ff000000", "890da438540059", "dw_20 school"),
        Route("workshop", 0x43DEE0, 0x42274F, 0x9F, 0x43E04E, 1044,
              "5352565781ec000400008a400225ff000000", "890dc838540059", "dw_20 workshop"),
        Route("smith", 0x43DAE0, 0x4227A7, 0xA6, 0x43DC4E, 1044,
              "5352565781ec000400008a400225ff000000", "890db038540059", "dw_20 smith"),
        Route("barracks", 0x433C20, 0x422709, 0x63, 0x433E72, 24,
              "515257555653a350215300", "b8d84c5400", "dw_12 first of three initial present calls"),
        Route("peasants", 0x42B0A0, 0x4227D3, 0x87, 0x42B35E, 1048,
              "53515256575581ec0004000089c6a3f41c5300", "31c0bf40485100a3e81c5300", "dw_15"),
    )
}
PENDING = {
    "court": "Entry0044FE70 is known; its branch-dependent complete draw/first-present contract is not yet implemented.",
    "recruitment": "4338E0→435BC0 needs separately authenticated initialized barracks state and selection/admission.",
    "battle_initial": "Forced opposing-unit construction and battle admission/presentation need a separate contract.",
    "battle_command": "No framed modal command/forced-input contract is implemented.",
    "battle_results": "No completed result-route contract is implemented.",
    "tower": "Hit F9 dispatches to the default overview branch; no callable interior is proven.",
    "dw_14": "Native436300 has no verified reachable caller in the inventory.",
}

# Native instruction spans, deliberately independent of candidate bytes. The
# complete original and candidate are also authenticated, not pattern-scanned.
COMMON = {
    SENTINEL: "525583ec70",
    LOOP: "b801000000e8a5f1030085c00f8407010000",
    GATE: "85c00f8429feffff85c90f8421feffff",
    CALLBACK: "ffd18b0dd8995100",
    0x4225E2: "b8a017460039c00f8420020000b8c0d4510031d2",
    0x4225F6: "e84524feff89c2b8a0174600506833e74e006839e74e008b1dd8995100a3d8995100e8036bffffa1e402520005eac6070083c40c01e8ffd1",
    PRESENT: "565583ec0489c6a1104d540085c07406",
}
LIMITS = [
    "Packet preparation only; a separately reviewed modal host lane and actual runtime evidence are required.",
    "Controlled native call/case dispatch and one forced flipping-gate result are not natural or manual input.",
    "existing_flags means no availability writes; it does not establish that a dormant hit-map building was naturally selectable.",
    "construct_all writes only the selected isolated castle feature bytes1A0=1F and1A4=01, with old/new observations; no save is written by the probe.",
    "The stop precedes subsequent input processing and intentionally does not return to the interrupted map call.",
    "The physical memory-map capture may omit primary-only text/cursor/HUD layers and cannot prove final wrapper composition.",
    "Host timeout, candidate ownership/cleanup, parser ordering, original map-trace acceptance and image inspection remain mandatory separate evidence.",
    "Only castle indices0..3 from the inspected fixture range are admitted; castle coordinates/owner/world bounds are rechecked live.",
]


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read(image: bytes, va: int, size: int):
    pe = builder.pe.inspect_pe(image)
    if pe.image_base != IMAGE_BASE:
        raise ValueError("only the source-bound fixed image-base lane is supported")
    offset = pe.file_offset(va - IMAGE_BASE, size)
    return offset, image[offset:offset + size]


def _printf(text: str, *args: str):
    return '.printf \\"' + text + r'\\n\"' + (", " + ", ".join(args) if args else "")


def _reject(reason: str, *, expected_state: int | None = None,
            expected_eip: int | None = None, expected_esp: str | None = None):
    # Register-only diagnostics remain safe even when a null/byte guard fails.
    # 'unbound' means that guard makes no claim about that particular value.
    state = str(expected_state) if expected_state is not None else "unbound"
    eip = f"{expected_eip:08x}" if expected_eip is not None else "unbound"
    tid = "%x" if expected_state is not None else "unbound"
    esp = "%p" if expected_esp is not None else "unbound"
    args = ["@$t0", "@$tid"]
    if expected_state is not None:
        args.append("@$t2")
    args.extend(("@eip", "@esp"))
    if expected_esp is not None:
        args.append(expected_esp)
    return _printf(f"MODAL_REJECT reason={reason} actual_t0=%d expected_t0={state} "
                   f"actual_tid=%x expected_tid={tid} actual_eip=%p expected_eip={eip} "
                   f"actual_esp=%p expected_esp={esp}", *args) + "; q"


def _guard(test: str, yes: str, reason: str, **expected):
    return f".if ({test}) {{ {yes} }} .else {{ {_reject(reason, **expected)} }}"


def _state(number: int, extra: str = ""):
    return f"(@$t0 == 0n{number}) & (@$tid == @$t2)" + (" & " + extra if extra else "")


def _capture(route: Route, width: int, height: int):
    # Never dereference a null surface; fixed primary object is observations
    # only. Only the native memory target offers linear pixels to the host.
    emit = (
        "r @$t0=0n10; "
        + _printf(f"MODAL_SURFDUMP_READY route={route.name} tid=%x eip=%p esp=%p "
                  "surface=%p size=(%d,%d) base=%p bytes=%d owner=%p "
                  "render=%p primary=0051d4c0 primary_size=(%d,%d) primary_vtable=%p "
                  "capture=memory_map manual_input_proof=0",
                  "@$tid", "@eip", "@esp", "@$t11", "@$t12", "@$t15", "@$t16", "@$t17",
                  "@$t1", "poi(00511230)", "wo(0051d4c0)", "wo(0051d4c2)", "poi(0051d578)")
        + "; .echo MODAL_SURFDUMP_HOST_READY"
    )
    return "r @$t11=poi(005202e0); " + _guard("@$t11 != 0",
        "r @$t12=wo(@$t11); r @$t15=wo(@$t11+2); r @$t16=poi(@$t11+4); r @$t17=@$t12*@$t15; "
        + _guard(f"(@$t12 == 0n{width}) & (@$t15 == 0n{height}) & (@$t16 != 0) & (poi(@$t11+b8) == 0050ee24)",
                 emit, "capture_surface"), "null_capture_surface")


def _commands(route: Route, width: int, height: int, castle_index: int, availability: str):
    observation = _printf("MODAL_CASTLE_STATE index=%d ptr=%p owner=%d xy=(%d,%d) flags=(%x,%x) style=%d",
        f"0n{castle_index}", "@$t1", "by(@$t1+2)", "by(@$t1)", "by(@$t1+1)",
        "by(@$t1+1a0)", "by(@$t1+1a4)", "poi(poi(005202e4)+2231f+by(@$t1+2)*58f)")
    map_observation = _printf("MODAL_MAP_HANDOFF tid=%x eip=%p esp=%p render_hook=%p lower=%p post=%p surface=%p size=(%d,%d)",
        "@$tid", "@eip", "@esp", "poi(005199d8)", "poi(00526994)", "poi(00526990)",
        "poi(005202e0)", "wo(poi(005202e0))", "wo(poi(005202e0)+2)")
    construct = ""
    if availability == "construct_all":
        construct = "; eb @$t1+1a0 1f; eb @$t1+1a4 01; " + _printf(
            "MODAL_AVAILABILITY_FORCED flags=(%x,%x) isolated_fixture=1", "by(@$t1+1a0)", "by(@$t1+1a4)")
    arm = "; ".join(f"be {i}" for i in range(80, 84 if route.name == "castle_overview" else 91))
    invoke = (map_observation + "; " + observation + construct + "; r @$t0=1; r @$t2=@$tid; r @$t3=@esp; " + arm
              + "; " + _printf(f"MODAL_FORCE_CALL route={route.name} availability={availability} "
                  "entry=00422180 index=%d tid=%x original_esp=%p return_sentinel=00406fa1 forced=1",
                  f"0n{castle_index}", "@$tid", "@esp")
              + f"; r esp=@esp-4; ed @esp {SENTINEL:08x}; r @$t4=@esp; r eax=0n{castle_index}; r eip={OVERVIEW:08x}; gc")
    if availability == "construct_all":
        invoke = _guard("((by(@$t1+1a0) & 0xe0) == 0) & ((by(@$t1+1a4) & 0xfe) == 0)",
                        invoke, "unreviewed_availability_bits")
    owner_test = ("(by(@$t1+2) <= 4) & (by(@$t1) < poi(poi(005202e4)+222e0)) & "
                  "(by(@$t1+1) < poi(poi(005202e4)+222e4)) & "
                  "(poi(poi(005202e4)+222e0) <= 0n100) & (poi(poi(005202e4)+222e4) <= 0n100) & "
                  f"(wo(poi(005202e0)) == 0n{width}) & (wo(poi(005202e0)+2) == 0n{height}) & "
                  "(poi(poi(005202e0)+4) != 0) & (poi(poi(005202e0)+b8) == 0050ee24)")
    handoff = (_printf("PTILE_TRACE_CLOSED tid=%x eip=%p esp=%p", "@$tid", "@eip", "@esp")
               + "; " + "; ".join(f"bd {i}" for i in range(70, 78)) + "; "
               + _guard("(@eip == 00406fa0) & (@$t14 == 1) & (@$t13 == 4) & (@$t7 == 1) & (poi(005202e4) != 0) & "
                        "(poi(005202e0) != 0) & (poi(005199d8) == 0040ad40) & (poi(00526994) == 0) & (poi(00526990) == 0)",
                    f"r @$t1=poi(005202e4)+7c6ea+0n{castle_index * 467}; "
                    + _guard(owner_test, invoke, "castle_owner_bounds"), "map_handoff"))
    commands = {80: (SENTINEL, _reject("unexpected_native_return"))}
    # CDB continuation at a newly assigned EIP can execute that instruction
    # without reporting its entry breakpoint. Observe the next boundary after
    # the authenticated native PUSH EBX (53), without emulating its write.
    commands[81] = (OVERVIEW + 1, _guard(_state(1, f"(@eax == 0n{castle_index}) & (@esp == (@$t4-4)) & (poi(@esp+4) == 00406fa1) & (poi(@esp) == @ebx)"),
        "r @$t0=2; " + _printf("MODAL_OVERVIEW_PROLOGUE tid=%x eip=%p esp=%p index=%d after_first_push=1 saved_ebx=%p return_sentinel=%p",
            "@$tid", "@eip", "@esp", "@eax", "poi(@esp)", "poi(@esp+4)") + "; gc", "overview_prologue",
        expected_state=1, expected_eip=OVERVIEW+1, expected_esp="@$t4-4"))
    commands[82] = (0x42239A, _guard(_state(2, "(@esp == (@$t4-0n56)) & (poi(00526a64) == @$t1) & (@eax == 00544cd8)"),
        "r @$t0=3; " + _printf("MODAL_OVERVIEW_PRESENT_CALL tid=%x esp=%p cursor_active=%d", "@$tid", "@esp", "poi(00544d10)") + "; gc", "overview_present_call",
        expected_state=2, expected_eip=0x42239A, expected_esp="@$t4-0n56"))
    commands[83] = (0x42239F, _guard(_state(3, "(@esp == (@$t4-0n56)) & (poi(00526a64) == @$t1)"),
        "r @$t0=4; " + _printf("MODAL_OVERVIEW_PRESENT_RETURN tid=%x eip=%p esp=%p", "@$tid", "@eip", "@esp")
        + "; " + (_capture(route, width, height) if route.name == "castle_overview" else "gc"), "overview_present_return",
        expected_state=3, expected_eip=0x42239F, expected_esp="@$t4-0n56"))
    if route.name != "castle_overview":
        dispatch = ("r @$t0=5; " + _printf(f"MODAL_FORCED_DISPATCH route={route.name} branch={route.branch_va:08x} "
                     "skip_input_loop=1 old_render=%p new_render=%p", "poi(00511230)", "poi(00526a68)")
                    + f"; ed 00511230 poi(00526a68); r eip={route.branch_va:08x}; gc")
        commands[84] = (LOOP, _guard(_state(4, f"(@esp == (@$t4-0n56)) & (@ebp == 0n{castle_index * 467}) & (@esi == 0) & (poi(00526a68) != 0)"),
            dispatch, "overview_loop", expected_state=4, expected_eip=LOOP, expected_esp="@$t4-0n56"))
        commands[85] = (GATE, _guard(_state(5, f"(@esp == (@$t4-0n56)) & (@ecx == {route.entry_va:08x}) & (@esi == 0n{route.command})"),
            "r @$t0=6; " + _printf("MODAL_FLIP_GATE_FORCED tid=%x esp=%p original=%x forced=1 callback=%p command=%d",
                "@$tid", "@esp", "@eax", "@ecx", "@esi") + "; r eax=1; gc", "native_gate",
            expected_state=5, expected_eip=GATE, expected_esp="@$t4-0n56"))
        commands[86] = (CALLBACK, _guard(_state(6, f"(@esp == (@$t4-0n56)) & (@eax == @$t1) & (@ecx == {route.entry_va:08x}) & (poi(005199d8) == 004617a0)"),
            "r @$t0=7; r @$t5=@esp; " + _printf("MODAL_CALLBACK_CALL tid=%x esp=%p callback=%p owner=%p render_hook=%p",
                "@$tid", "@esp", "@ecx", "@eax", "poi(005199d8)") + "; gc", "callback_call",
            expected_state=6, expected_eip=CALLBACK, expected_esp="@$t4-0n56"))
        commands[87] = (route.entry_va, _guard(_state(7, "(@esp == (@$t5-4)) & (poi(@esp) == 0042262e) & (@eax == @$t1)"),
            "r @$t0=8; r @$t6=@esp; " + _printf(f"MODAL_SCREEN_ENTRY route={route.name} tid=%x eip=%p esp=%p owner=%p",
                "@$tid", "@eip", "@esp", "@eax") + "; gc", "screen_entry",
            expected_state=7, expected_eip=route.entry_va, expected_esp="@$t5-4"))
        stack = f"(@esp == (@$t6-0n{route.local_stack_bytes}))"
        commands[88] = (route.present_call_va, _guard(_state(8, stack + " & (@eax == 00544cd8)"),
            "r @$t0=9; " + _printf(f"MODAL_PRESENT_CALL route={route.name} tid=%x eip=%p esp=%p cursor_active=%d",
                "@$tid", "@eip", "@esp", "poi(00544d10)") + "; gc", "screen_present_call",
            expected_state=8, expected_eip=route.present_call_va, expected_esp=f"@$t6-0n{route.local_stack_bytes}"))
        commands[89] = (route.stop_va, _guard(_state(9, stack),
            _printf(f"MODAL_PRESENT_RETURN route={route.name} tid=%x eip=%p esp=%p", "@$tid", "@eip", "@esp")
            + "; " + _capture(route, width, height), "screen_present_return",
            expected_state=9, expected_eip=route.stop_va, expected_esp=f"@$t6-0n{route.local_stack_bytes}"))
        commands[90] = (CALLBACK + 2, _reject("unexpected_callback_return"))
    commands = {bp: (va, _guard(f"@eip == {va:08x}", body, "breakpoint_eip", expected_eip=va))
                for bp, (va, body) in commands.items()}
    return handoff, commands


def canonical_template(original: bytes, resolution: str, *, minimap_viewport: bool = False):
    image, metadata, extra = builder.build_candidate(original, resolution, minimap_viewport=minimap_viewport)
    base = BASE_PROBE.read_text(encoding="utf-8-sig")
    template = render_probe(base, resolution, STAGE)["template"]
    if len(re.findall(r"(?m)^g$", template)) != 1 or not template.rstrip().endswith("\ng"):
        raise ValueError("canonical map template must have one final startup continuation")
    template = re.sub(r"(?m)^g$", lambda _: extra.strip() + "\ng", template)
    return image, metadata, extra, template


def build_screen_probe(original: bytes, candidate: bytes, *, candidate_sha256: str,
                       stage: str, resolution: str, route: str, availability: str,
                       castle_index: int, rendered_probe: str, minimap_viewport: bool = False):
    if stage != STAGE:
        raise ValueError("exact framed validation stage required")
    if route not in ROUTES:
        raise ValueError("unsupported or pending route: " + PENDING.get(route, str(route)))
    if availability not in ("existing_flags", "construct_all"):
        raise ValueError("explicit existing_flags or construct_all availability required")
    if type(castle_index) is not int or not 0 <= castle_index <= 3:
        raise ValueError("only inspected castle indices0..3 are supported")
    if type(minimap_viewport) is not bool:
        raise ValueError("minimap_viewport must be an explicit boolean")
    if not re.fullmatch(r"[0-9a-fA-F]{64}", candidate_sha256 or "") or sha(candidate) != candidate_sha256.lower():
        raise ValueError("candidate SHA-256 mismatch")
    rebuilt, metadata, extra, expected = canonical_template(original, resolution, minimap_viewport=minimap_viewport)
    if candidate != rebuilt:
        raise ValueError("candidate differs from exact framed reconstruction and options")
    if not isinstance(rendered_probe, str) or rendered_probe.replace("\r\n", "\n") != expected:
        raise ValueError("expected unchanged canonical renderer template with unchanged standard extra")
    if expected.count(DUMP_TOKEN) != 1:
        raise ValueError("canonical template must have one unique dump-action token")
    selected = ROUTES[route]
    spans = dict(COMMON)
    for r in (ROUTES["castle_overview"], selected):
        spans[r.entry_va] = r.entry_bytes
        spans[r.present_call_va] = (b"\xe8" + struct.pack("<i", PRESENT - r.stop_va)).hex()
        spans[r.stop_va] = r.return_bytes
        if r.branch_va is not None:
            spans[r.branch_va] = (b"\xb9" + struct.pack("<I", r.entry_va)).hex()
    records, conditions = [], []
    for va, old_hex in sorted(spans.items()):
        old = bytes.fromhex(old_hex)
        if _read(original, va, len(old))[1] != old:
            raise ValueError(f"native source instruction span differs at{va:08x}")
        offset, new = _read(candidate, va, len(old))
        if new != old:
            raise ValueError(f"selected native observation span changed at{va:08x}")
        records.append(dict(va=va, rva=va-IMAGE_BASE, offset=offset, old_hex=old_hex, candidate_hex=new.hex()))
        conditions.extend(f"(by({va+i:08x}) != 0x{value:02x})" for i, value in enumerate(new))
    # These checks are top-level commands, outside a quoted breakpoint body.
    loaded_rejection = _reject('loaded_bytes').replace(r'\"', '"').replace(r'\\n', r'\n')
    byte_checks = "\n".join(f".if ({' | '.join(conditions[i:i+48])}) {{ {loaded_rejection} }}"
                             for i in range(0, len(conditions), 48)) + "\n"
    byte_checks += f".echo MODAL_BYTE_CONTRACT_PASS candidate_sha256={candidate_sha256.lower()} route={route}\n"
    profile = builder.recipe.patcher.parse_resolution(resolution)
    handoff, commands = _commands(selected, profile.width, profile.height, castle_index, availability)
    # IDs80..90 are separate from the canonical implicit base and numbered
    # 70..77 observers. Reject a future expansion into those IDs or sites.
    implicit_count = 0
    for line in expected.splitlines():
        match = re.match(r'^bp\s*(?:(\d+)\s+)?([0-9a-fA-F]{8})\s+"', line)
        if not match:
            continue
        bp = int(match[1]) if match[1] else implicit_count
        if match[1] is None:
            implicit_count += 1
        if bp >= 80 or int(match[2], 16) in {va for va, _ in commands.values()}:
            raise ValueError("canonical breakpoint ID/site collides with modal probe")
    # The one canonical startup-animation token can add at most six implicit
    # breakpoints in the existing harness. Keep that expansion below our IDs.
    if implicit_count + 6 >= 80:
        raise ValueError("canonical startup breakpoint expansion reaches modal IDs")
    startup = (f".echo MODAL_CONTRACT stage={stage} resolution={resolution} candidate_sha256={candidate_sha256.lower()} "
               f"route={route} availability={availability} castle_index={castle_index} runtime_acceptance=0\n")
    for bp, (va, body) in commands.items():
        startup += f'bp{bp} {va:08x} "{body}"\nbd {bp}\n'
    handoff_line = next(line for line in expected.splitlines() if DUMP_TOKEN in line)
    if any(len(line) >= 4096 for text in (byte_checks, startup, handoff_line.replace(DUMP_TOKEN, handoff)) for line in text.splitlines()):
        raise ValueError("modal command exceeds CDB4096-byte line limit")
    return dict(schema="clash95_framed_screen_probe_packet_v1", prepared=True, runtime_ready=False,
        stage=stage, resolution=resolution, candidate_sha256=sha(candidate), original_sha256=sha(original),
        minimap_viewport=minimap_viewport, source_sha256=metadata["source_sha256"],
        producer_sha256=sha(Path(__file__).read_bytes()), base_probe_sha256=sha(BASE_PROBE.read_bytes()),
        canonical_extra_sha256=sha(extra.encode("utf-8")), map_template_sha256=sha(expected.encode("ascii")),
        route=asdict(selected), stop_va=selected.stop_va, castle_index=castle_index, availability=availability,
        availability_proof="controlled route; natural selection is not established",
        map_probe_template=expected, dump_action_token=DUMP_TOKEN, handoff_action=handoff,
        byte_checks_before_first_breakpoint=byte_checks, startup_commands_before_final_g=startup,
        breakpoint_commands={str(k): {"va": v[0], "body": v[1]} for k,v in commands.items()},
        byte_spans=records, return_sentinel_va=SENTINEL, expected_capture_surface="physical native memory map at poi(005202e0)",
        final_ready_marker="MODAL_SURFDUMP_READY", final_host_marker="MODAL_SURFDUMP_HOST_READY",
        required_host_contract="Hidden non-presenting proxy; enforce a120-second deadline; capture only MODAL readiness after accepted ordered route; terminate only owned game/debugger and bind cleanup.",
        prior_map_snapshot="Existing SURFDUMP_READY/SCROLL_VISDUMP remain diagnostic and are not modal readiness.",
        paused_capture=True, forced_os_input=False, forced_gate_result=route != "castle_overview",
        forced_native_dispatch=True, manual_input_proof=False,
        promotion_ready=False, pending_routes=PENDING, limits=LIMITS)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--candidate-sha256", required=True)
    parser.add_argument("--stage", required=True)
    parser.add_argument("--resolution", required=True)
    parser.add_argument("--route", choices=tuple(ROUTES), required=True)
    parser.add_argument("--availability", choices=("existing_flags", "construct_all"), required=True)
    parser.add_argument("--castle-index", type=int, required=True)
    parser.add_argument("--minimap-viewport", action="store_true")
    args = parser.parse_args()
    try:
        original, candidate = args.original.read_bytes(), args.candidate.read_bytes()
        template = canonical_template(original, args.resolution, minimap_viewport=args.minimap_viewport)[3]
        packet = build_screen_probe(original, candidate, candidate_sha256=args.candidate_sha256,
            stage=args.stage, resolution=args.resolution, route=args.route, availability=args.availability,
            castle_index=args.castle_index, rendered_probe=template, minimap_viewport=args.minimap_viewport)
    except (OSError, ValueError) as exc:
        parser.exit(2, f"modal probe preparation refused: {exc}\n")
    print(json.dumps(packet, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
