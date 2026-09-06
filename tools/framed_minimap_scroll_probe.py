#!/usr/bin/env python3
"""Prepare exact hidden minimap-scroll commands, without executing or writing.

The host must validate and capture at both pauses. This packet never grants
runtime, manual-input, visual, cleanup or promotion acceptance.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re

import build_framed_candidate as builder
import framed_screen_trace as startup
from render_cdb_surface_probe import BASE_PROBE, render_probe

STAGE = builder.STAGE
SUPPORTED = ("1024x768", "802x602")
GD = "poi(005202e4)"
SOURCE_SPANS = ((0x40DC10, 283, "efc84e280a1845d15f51687db427964017c8d1ba8e3c8b40adcf7964303bb576"),)
NATIVE = {0x40B0E0: "e82b2b0000", 0x40B0E5: "e8c6370000", 0x40DC10: "5351525657",
          0x40DC1A: "e8d12c050085c0", 0x4608F0: "f6402c010f95c025ff000000c3",
          0x40DCEC: "e80faa00005f5e5a595bc3", 0x40D62E: "e8ad4effff"}
LIMITS = ["Prepared commands only; no runtime host integration or approval is supplied.",
          "Native mouse globals, controlled CALL dispatch and one query-result override are disclosed; manual input is false.",
          "One ordinary player-0 scroll invocation; world, scale, candidate and stage cannot be substituted.",
          "Two paused memory-map/backing snapshots are required; primary-only composition is outside this evidence class.",
          "The host must retain exact process identities, enforce a deadline, preserve failures and stop debugger before game."]


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def packet_hash(packet: dict) -> str:
    return sha(json.dumps(packet, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii"))


def printf(text: str, *args: str) -> str:
    return '.printf \\"' + text + r'\\n\"' + (", " + ", ".join(args) if args else "")


def guard(test: str, action: str, reason: str) -> str:
    return f'.if ({test}) {{ {action} }} .else {{ .echo MMSC_REJECT reason={reason}; q }}'


def emit_identity(name: str, tail: str = "", *args: str) -> str:
    return printf(f"MMSC_{name} tid=%x eip=%p esp=%p" + (" " + tail if tail else ""), "@$tid", "@eip", "@esp", *args)


def commands(width: int, height: int, target: tuple[int, int], metadata: dict) -> dict:
    tx, ty = (width-64)//64, (height-32)//64
    sx, sy = target
    identity = "(@$tid == @$t2)"
    phase = lambda n, va, sp: f"(@$t0 == 0n{n}) & {identity} & (@eip == {va:08x}) & (@esp == {sp})"
    # Separate nested pointer guards avoid dereferencing nulls even though CDB &
    # does not provide short-circuit evaluation.
    common = (f"(poi(005199d8) == 0040ad40) & (poi(0052698c) == 0) & (poi(00526990) == 0) & (poi(00526994) == 0) & "
              f"(poi(005202ec) == 0) & (poi(@$t3+23ec7) == 0) & (poi(@$t3+2230f) != 0) & (poi(@$t3+22313) != 0) & "
              f"(poi(@$t3+222e0) >= 0n{tx}) & (poi(@$t3+222e0) <= 0n100) & (poi(@$t3+222e4) >= 0n{ty}) & (poi(@$t3+222e4) <= 0n100) & "
              f"(wo(@$t4) == 0n{width}) & (wo(@$t4+2) == 0n{height}) & (poi(@$t4+4) != 0) & (poi(@$t4+b8) == 0050ee24) & "
              f"(poi(@$t5+4) != 0) & (poi(@$t5+b8) == 0050ee24) & (@$t4 != @$t5) & (@$t4 != 0051d4c0) & (@$t5 != 0051d4c0) & "
              f"(by(0054512c) <= 8) & ((by(00523f54) == 2) | (by(00523f54) == 4)) & "
              f"(wo(00523348) == poi(@$t3+222e0)*by(00523f54)+0n14) & (wo(0052334a) == poi(@$t3+222e4)*by(00523f54)+0n14) & "
              f"(wo(@$t5) == wo(00523348)) & (wo(@$t5+2) == wo(0052334a)) & "
              f"(wo(00523344) == 0n{width-32}-wo(00523348)) & (wo(00523344) >= 0n32) & (wo(00523346) == 0n16) & "
              f"(wo(0052334a)+0n16 <= 0n{height-16}) & (((poi(@$t3+222e0)*poi(@$t3+222e4) <= 0n2500) & (by(00523f54) == 4)) | "
              f"((poi(@$t3+222e0)*poi(@$t3+222e4) > 0n2500) & (by(00523f54) == 2)))")
    def state(which):
        return "; ".join((
            emit_identity("STATE", f"phase={which} gd=%p world=(%d,%d) scroll=(%d,%d) scale=%d origin=(%d,%d) shift=%d mouse=(%x,%x)",
                          "@$t3", "poi(@$t3+222e0)", "poi(@$t3+222e4)", "poi(@$t3+222e8)", "poi(@$t3+222ec)", "by(00523f54)", "wo(00523344)", "wo(00523346)", "by(0054512c)", "poi(00544cfc)", "poi(00544d00)"),
            printf(f"MMSC_SURFACE phase={which} map=%p size=(%d,%d) base=%p vtable=%p backing=%p bsize=(%d,%d) bbase=%p bvtable=%p render=%p",
                   "@$t4", "wo(@$t4)", "wo(@$t4+2)", "poi(@$t4+4)", "poi(@$t4+b8)", "@$t5", "wo(@$t5)", "wo(@$t5+2)", "poi(@$t5+4)", "poi(@$t5+b8)", "poi(00511230)"),
            printf(f"MMSC_CONTEXT phase={which} owner=%p tile=%p post=%p lower=%p player=%d selector=%d enabled=%d",
                   "poi(005199d8)", "poi(0052698c)", "poi(00526990)", "poi(00526994)", "poi(005202ec)", "poi(@$t3+23ec7)", "(poi(@$t3+2230f) != 0)"),
            f".echo MMSC_HOST_READY phase={which}"))
    before = [guard("(@eip == 00406fa0) & (@$t14 == 1) & (@$t13 == 4) & (@$t7 == 1) & (@$tid != 0) & (@esp != 0) & ((@esp & 3) == 0)",
                    emit_identity("BEGIN") + "; r @$t0=1; r @$t1=@esp; r @$t2=@$tid; r @$t3=poi(005202e4); r @$t4=poi(005202e0); r @$t5=poi(0052334c)", "initial_pause"),
              guard("(@$t3 != 0) & (@$t4 != 0) & (@$t5 != 0)", ".echo MMSC_POINTERS_BOUND", "pointers"),
              guard(common, ".echo MMSC_OBJECTS_BOUND", "object_context"),
              guard(f"(poi(@$t3+222e8) >= 0) & (poi(@$t3+222ec) >= 0) & (poi(@$t3+222e8) <= poi(@$t3+222e0)-0n{tx}) & (poi(@$t3+222ec) <= poi(@$t3+222e4)-0n{ty}) & "
                    f"(0n{sx} < poi(@$t3+222e0)) & (0n{sy} < poi(@$t3+222e4)) & (0n{sx} <= poi(@$t3+222e0)-0n{tx}+1) & (0n{sy} <= poi(@$t3+222e4)-0n{ty}+1)",
                    "r @$t6=poi(@$t3+222e8); r @$t7=poi(@$t3+222ec); r @$t8=poi(00544cfc); r @$t9=poi(00544d00); "
                    f"r @$t10=(wo(00523344)+7+0n{sx}*by(00523f54))<<by(0054512c); r @$t11=(wo(00523346)+7+0n{sy}*by(00523f54))<<by(0054512c); "
                    f"r @$t12=0n{sx}; r @$t13=0n{sy}; "
                    f".if (@$t12 > poi(@$t3+222e0)-0n{tx}) {{ r @$t12=poi(@$t3+222e0)-0n{tx}; }}; "
                    f".if (@$t13 > poi(@$t3+222e4)-0n{ty}) {{ r @$t13=poi(@$t3+222e4)-0n{ty}; }}", "scroll_bounds"),
              guard("(@$t12 != @$t6) | (@$t13 != @$t7)", state("before"), "unchanged_target")]
    continuation = [guard(phase(1, 0x406FA0, "@$t1") + " & (poi(005202e4) == @$t3) & (poi(005202e0) == @$t4) & (poi(0052334c) == @$t5)", ".echo MMSC_CONTINUE_BOUND", "continue_identity"),
                    guard(common + " & (poi(@$t3+222e8) == @$t6) & (poi(@$t3+222ec) == @$t7) & (poi(00544cfc) == @$t8) & (poi(00544d00) == @$t9)",
                          emit_identity("DISPATCH", f"requested=({sx},{sy}) expected=(%d,%d) old_mouse=(%x,%x) new_mouse=(%x,%x) call=0040b0e0 forced=1 manual_input_proof=0", "@$t12", "@$t13", "@$t8", "@$t9", "@$t10", "@$t11") +
                          "; ed 00544cfc @$t10; ed 00544d00 @$t11; r @$t0=2; r @$t15=0; r @$t16=0; r @$t17=0; r @$t18=0; r eip=0040b0e0", "continue_state")]
    bps = {}
    def bp(number, va, test, action):
        bps[number] = (va, guard(f"(@eip == {va:08x}) & ({test})", action, f"bp{number}"))
    bp(82, 0x40DC10, phase(2, 0x40DC10, "@$t1-4") + " & (poi(@esp) == 0040b0e5)", emit_identity("ENTRY", "caller=%p", "poi(@esp)") + "; r @$t0=3; gc")
    bp(83, 0x40DC1F, phase(3, 0x40DC1F, "@$t1-0n24") + " & ((@eax == 0) | (@eax == 1))", emit_identity("GATE", "observed=%d replacement=1 forced=1 manual_input_proof=0", "@eax") + "; r eax=1; r @$t0=4; gc")
    unchanged = "(poi(005202e4) == @$t3) & (poi(005202e0) == @$t4) & (poi(0052334c) == @$t5)"
    stored = "(poi(@$t3+222e8) == @$t12) & (poi(@$t3+222ec) == @$t13)"
    bp(84, 0x40DCEC, phase(4, 0x40DCEC, "@$t1-0n24") + f" & {unchanged} & {stored} & (@eax == 1)", emit_identity("FULL_CALL", "scroll=(%d,%d) present=1", "poi(@$t3+222e8)", "poi(@$t3+222ec)") + "; r @$t0=5; gc")
    active = "((@$t0 == 5) | (@$t0 == 6) | (@$t0 == 7)) & " + identity
    bp(85, 0x40D62E, active + " & (@$t17 == 0) & (@eax == @$t5) & (@edx == @$t4)",
       emit_identity("REPAIR_CALL", "source=%p target=%p rect=(%d,%d,%d,%d) dest=(%d,%d)", "@eax", "@edx", "@ebx", "@ecx", "poi(@esp)", "poi(@esp+4)", "poi(@esp+8)", "poi(@esp+0c)") + "; r @$t17=@esp; gc")
    bp(86, 0x40D633, active + " & (@$t17 != 0) & (@esp == @$t17+0n16)", emit_identity("REPAIR_RETURN") + "; r @$t17=0; r @$t15=@$t15+1; gc")
    obs = metadata["minimap_viewport_contract"]
    bp(87, obs["observers"]["memory"], active + " & (@$t18 == 0) & (@eax == @$t4) & (poi(@esp+4) == 4c)",
       emit_identity("DRAW_CALL", "target=%p rect=(%d,%d,%d,%d) color=%x scroll=(%d,%d)", "@eax", "@edx", "@ebx", "@ecx", "poi(@esp)", "poi(@esp+4)", "poi(@$t3+222e8)", "poi(@$t3+222ec)") + "; r @$t18=@esp; gc")
    bp(88, obs["afterdraw_status"], active + " & (@$t18 != 0) & (@esp == @$t18+0n12) & (@eax == 1)", emit_identity("DRAW_RETURN", "status=%d", "@eax") + "; r @$t18=0; r @$t16=@$t16+1; gc")
    for number, key, old_phase in ((89, "full_converge", 5), (90, "full_present", 6)):
        va = metadata["status_vas"][key]
        bp(number, va, phase(old_phase, va, "@$t1-0n172") + " & (@eax == 1) & (@$t17 == 0) & (@$t18 == 0)",
           emit_identity("FULL_STATUS", f"hook={key} status=%d", "@eax") + f"; r @$t0=0n{old_phase+1}; gc")
    bp(91, 0x40DCF1, phase(7, 0x40DCF1, "@$t1-0n24") + " & (@$t15 > 0) & (@$t16 > 0) & (@$t17 == 0) & (@$t18 == 0)",
       emit_identity("FULL_RETURN", "repair_count=%d draw_count=%d", "@$t15", "@$t16") + "; r @$t0=8; gc")
    bp(92, 0x40B0E5, phase(8, 0x40B0E5, "@$t1") + f" & {unchanged} & {stored}",
       emit_identity("CALLBACK_RETURN", "scroll=(%d,%d) result=%x", "poi(@$t3+222e8)", "poi(@$t3+222ec)", "@eax") +
       "; ed 00544cfc @$t8; ed 00544d00 @$t9; " + printf("MMSC_MOUSE_RESTORED values=(%x,%x)", "poi(00544cfc)", "poi(00544d00)") + "; r @$t0=9; " + state("after"))
    bps[93] = (obs["observers"]["primary"], ".echo MMSC_REJECT reason=unexpected_primary_outline; q")
    return dict(before_action="\n".join(before)+"\n", continue_action="\n".join(continuation)+"\n", breakpoints=bps)


def build_packet(original: bytes, candidate: bytes, *, candidate_sha256: str, stage: str,
                 resolution: str, requested_scroll: tuple[int, int]) -> dict:
    if type(original) is not bytes or type(candidate) is not bytes:
        raise ValueError("original and candidate must be actual executable byte buffers")
    if stage != STAGE or resolution not in SUPPORTED:
        raise ValueError("only the exact framed stage and reviewed 1024/802 scroll lanes are supported")
    if (not isinstance(requested_scroll, (tuple, list)) or len(requested_scroll) != 2 or
            any(type(n) is not int or not 0 <= n <= 99 for n in requested_scroll)):
        raise ValueError("requested scroll must be two bounded native integer coordinates")
    if not isinstance(candidate_sha256, str) or not re.fullmatch("[0-9a-f]{64}", candidate_sha256) or sha(candidate) != candidate_sha256:
        raise ValueError("candidate identity mismatch")
    image, metadata, extra = builder.build_candidate(original, resolution, minimap_viewport=True)
    if candidate != image:
        raise ValueError("candidate differs from the complete optional minimap reconstruction")
    if metadata["layout_contract"].get("full_status_to_caller_before_call") != 148:
        raise ValueError("the reviewed framed full-call stack ABI changed")
    spans = []
    for va, length, digest in SOURCE_SPANS:
        off = builder.clip.file_offset(original, va, length)
        if sha(original[off:off+length]) != digest:
            raise ValueError("original scroll function source span differs")
        spans.append(dict(va=va, offset=off, size=length, original_sha256=digest,
                          candidate_hex=candidate[off:off+length].hex()))
    for va, expected in NATIVE.items():
        off = builder.clip.file_offset(original, va, len(bytes.fromhex(expected)))
        if original[off:off+len(bytes.fromhex(expected))].hex() != expected:
            raise ValueError(f"native instruction contract differs at {va:08x}")
        spans.append(dict(va=va, offset=off, size=len(bytes.fromhex(expected)), original_hex=expected,
                          candidate_hex=candidate[off:off+len(bytes.fromhex(expected))].hex()))
    width, height = map(int, resolution.split("x"))
    actions = commands(width, height, tuple(requested_scroll), metadata)
    checks = []
    for row in spans:
        data = bytes.fromhex(row["candidate_hex"])
        for offset in range(0, len(data), 48):
            condition = " & ".join(f"(by({row['va']+i:08x}) == {value:02x})" for i, value in enumerate(data[offset:offset+48], offset))
            checks.append(guard(condition, ".echo MMSC_BYTE_SEGMENT_PASS", "loaded_native_bytes"))
    checks.append(f".echo MMSC_BOUND stage={stage} resolution={resolution} candidate_sha256={candidate_sha256} target=({requested_scroll[0]},{requested_scroll[1]})")
    template = render_probe(BASE_PROBE.read_text(encoding="utf-8-sig"), resolution, STAGE)["template"]
    if len(re.findall(r"(?m)^g$", template)) != 1:
        raise ValueError("canonical initial map continuation changed")
    template = re.sub(r"(?m)^g$", lambda _: extra.strip()+"\ng", template)
    # The reviewed compiler supplies only the fixed fast-animation / load-slot-0
    # substitutions. Its packet fields are constructed here, never caller data.
    initial = startup.compile_probe(dict(map_probe_template=template, resolution=resolution,
        handoff_action=printf("PTILE_TRACE_CLOSED tid=%x eip=%p esp=%p", "@$tid", "@eip", "@esp")+"; .echo SURFDUMP_HOST_READY;",
        byte_checks_before_first_breakpoint="\n".join(checks)+"\n", startup_commands_before_final_g=""))
    # After the host has authenticated the original closed trace, disable every
    # completed producer before declaring this separate command phase.
    definitions = ["bd *"]
    for number, (va, body) in actions["breakpoints"].items():
        definitions.extend((f'bp{number} {va:08x} "{body}"', f"bd {number}"))
    def top_level(text):
        return text.replace(r'\"', '"').replace(r'\\n', r'\n')
    before = "\n".join(definitions)+"\n"+top_level(actions["before_action"])
    continuation = top_level(actions["continue_action"])+"\n".join(f"be {number}" for number in actions["breakpoints"])+"\ng\n"
    for text in (initial, before, continuation):
        text.encode("ascii")
        if any(len(line) >= 4096 for line in text.splitlines()):
            raise ValueError("command line exceeds the reviewed CDB4096-byte bound")
    hashes = {str(Path(path).resolve()): sha(Path(path).read_bytes()) for path in
              (__file__, builder.__file__, startup.__file__, BASE_PROBE)}
    return dict(schema="clash95_framed_minimap_scroll_packet_v1", prepared=True, runtime_ready=False,
        stage=stage, resolution=resolution, candidate_sha256=sha(candidate), original_sha256=sha(original),
        minimap_viewport=True, requested_scroll=list(requested_scroll), source_sha256=hashes,
        native_spans=spans, canonical_extra_sha256=sha(extra.encode("ascii")),
        initial_probe=initial, initial_probe_sha256=sha(initial.encode("ascii")),
        before_commands=before, before_commands_sha256=sha(before.encode("ascii")),
        continue_commands=continuation, continue_commands_sha256=sha(continuation.encode("ascii")),
        before_action=actions["before_action"], continue_action=actions["continue_action"],
        breakpoint_commands={str(k): dict(va=v[0], body=v[1]) for k,v in actions["breakpoints"].items()},
        layout_contract=metadata["layout_contract"], minimap_contract=metadata["minimap_viewport_contract"],
        capture_contract=dict(phases=["before","after"], frame_pitch="width", backing_pitch="worldW*scale+14",
                              before_eip=0x406FA0, after_eip=0x40B0E5, paused=True,
                              require_exact_log_prefix_and_snapshot_hashes=True, host_integration_implemented=False,
                              transport="Only reconstructed command files through an owned redirected CDB input pipe, retaining the same paused process.",
                              current_eip="Resume at the native CALL40B0E0; callee-entry observer follows an executed CALL, not a newly assigned current-EIP breakpoint."),
        manual_input_proof=False, promotion_ready=False, limits=LIMITS)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("original", "candidate"):
        parser.add_argument("--"+name, type=Path, required=True)
    for name in ("candidate-sha256", "stage", "resolution"):
        parser.add_argument("--"+name, required=True)
    parser.add_argument("--target-x", type=int, required=True)
    parser.add_argument("--target-y", type=int, required=True)
    args = parser.parse_args()
    try:
        packet = build_packet(args.original.read_bytes(), args.candidate.read_bytes(), candidate_sha256=args.candidate_sha256,
                              stage=args.stage, resolution=args.resolution, requested_scroll=(args.target_x,args.target_y))
    except (OSError, ValueError) as exc:
        parser.exit(2, f"scroll preparation refused: {exc}\n")
    print(json.dumps(packet, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
