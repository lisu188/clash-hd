#!/usr/bin/env python3
"""Prepare a source-bound, controlled native army-selection diagnostic.

Preparation only: no process, debugger, window, input or capture is run. The
generated probe closes the unchanged first-four-update observation lane, sets
one disclosed map scroll/mouse state, and calls native408030 then406980. Actual
selection, army drawing and its post-terrain redraw must succeed before the
stop-only sentinel offers an E0 software surface to a separate reviewed host.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PureWindowsPath
import re
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
import build_framed_army_candidate as builder
import framed_modal_canvas_trace as compiler
from render_cdb_surface_probe import BASE_PROBE, render_probe
from src.patcher import partial_tile_clip as clip

RESOLUTION = "1024x768"
SAVE_SHA256 = "4f2182409d209985a527f07c4116b19e44332416698d6acb0a3d35ae68db8a89"
REVISION = "controlled_own_army_native_selection_v3"
PINNED_SOURCES = {
    "tools/build_framed_army_candidate.py": "4060856f60ab8589f9dbc0ae73df142cf906e4905f3c24aaa6c8292a161bc167",
    "tools/framed_modal_canvas_trace.py": "2f0ef571acdbc6892c775cc97698d535b56355c8086080713d3dfec040a6d3ba",
    "tools/framed_modal_canvas_probe.py": "57c183d21ec5a696e715b8b3fca39ede14e107bc75102cc9553346053da47b3d",
    "tools/render_cdb_surface_probe.py": "1cd3103c434a898e0104b519932f1ce30be259888885f251422a8b71d3a9d02f",
    "probes/cdb/render/clash95_surface_dump_probe.cdb": "6346ca89d5c3e8b63fbb6c96839c48920aa9eb039523f49b442f7fc47fef7df8",
}
NATIVE_BOUNDARIES = {
    0x406FA0: "51", 0x406FA1: "52", 0x408030: "53", 0x408131: "5e",
    0x408136: "31c0", 0x406980: "53", 0x40A500: "51", 0x423B00: "53",
    0x423420: "53", 0x4080EF: "3b15581b5100", 0x423B32: "b801000000", 0x423B3C: "5a",
}
LIMITS = [
    "Controlled scroll/mouse writes and native call injection are not natural or manual input proof.",
    "No native click predicate, selected-unit value, squad, visibility or availability is forced.",
    "The original four-update trace must be separately validated under the exact new-stage projection.",
    "Native EAX draw returns and paired stopped E0 copies are distinct from visual/frame/input acceptance.",
    "Native draw status0 means authenticated legacy fallback, not relocated-draw success; composition must return1.",
    "The stop does not resume the interrupted map call or prove normal exit/destruction.",
    "Private-host retained process identities, deadline and verified cleanup remain separately required.",
    "E0 software pixels may omit primary-only tooltip/cursor/HUD composition; no promotion is implied.",
]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def verify_sources():
    for path, digest in PINNED_SOURCES.items():
        if sha((ROOT / path).read_bytes()) != digest:
            raise ValueError("reviewed army selection source differs: " + path)
    return dict(PINNED_SOURCES)


def capture_directory(value: str) -> str:
    """A literal ASCII Windows child path safe inside CDB command strings."""
    if type(value) is not str or not value or re.search(r'[^A-Za-z0-9_./:\\-]', value):
        raise ValueError("capture path must use literal ASCII path characters")
    path = PureWindowsPath(value)
    if (not path.is_absolute() or path.drive.lower() != "c:" or
            any(p in (".", "..") for p in re.split(r"[/\\]", value)) or
            len(path.parts) < 3 or path.parts[1].lower() != "clashcaptures" or
            any(":" in part for part in path.parts[1:])):
        raise ValueError("capture directory must be a child of C:/ClashCaptures")
    return path.as_posix()


def _read(image, va, size):
    off = clip.file_offset(image, va, size)
    return image[off:off + size]


def _call_return(image, call_va, target):
    """Check a source-identified CALL opcode/target, then derive next PC."""
    code = _read(image, call_va, 5)
    if code[0] != 0xE8 or call_va + 5 + struct.unpack("<i", code[1:])[0] != target:
        raise ValueError(f"CALL instruction boundary/target differs at {call_va:08x}")
    return call_va + 5


def _printf(message, *args):
    if any(c in message for c in '\n\r";'):
        raise ValueError("invalid debugger diagnostic text")
    return '.printf \\"' + message + r'\\n\"' + (", " + ", ".join(args) if args else "")


def _guard(condition, body):
    return ".if (" + condition + ") { " + body + " } .else { .echo SHSEL_REJECT native_contract; q }"


def build_selection_probe(original: bytes, candidate: bytes, save_bytes: bytes, *,
                          capture_dir: str, minimap_viewport: bool = True) -> dict:
    """Return a deterministic packet, command text and initial observer text.

    Reconstructs the entire1024x768 candidate from the pinned army builder.
    No caller-supplied metadata or probe overrides are accepted. The caller
    owns any output directories and runtime host; this function writes none.
    """
    sources = verify_sources()
    directory = capture_directory(capture_dir)
    if type(original) is not bytes or type(candidate) is not bytes or type(save_bytes) is not bytes:
        raise ValueError("immutable original/candidate/save bytes required")
    if type(minimap_viewport) is not bool:
        raise ValueError("explicit minimap boolean required")
    clip.verify_original(original)
    if sha(save_bytes) != SAVE_SHA256:
        raise ValueError("exact inspected slot0 save required")
    unit = save_bytes[147190 + 3*725:147190 + 4*725]
    types = [struct.unpack_from("<h", unit, 6 + 31*j)[0] for j in range(10)]
    if unit[:5] != bytes.fromhex("1000130000") or types != [16, 16, 1, 1, 1, 1, 1, 1, -1, -1]:
        raise ValueError("inspected unit3 coordinate/owner/eight-squad contract differs")
    rebuilt, metadata, initial_extra = builder.build_candidate(
        original, RESOLUTION, minimap_viewport=minimap_viewport)
    if rebuilt != candidate:
        raise ValueError("whole army candidate reconstruction differs")
    for va, hexbytes in NATIVE_BOUNDARIES.items():
        expected = bytes.fromhex(hexbytes)
        if _read(candidate, va, len(expected)) != expected:
            raise ValueError(f"native observation instruction differs at {va:08x}")
    before = _call_return(candidate, 0x423B2D, 0x423420)
    after = _call_return(candidate, 0x423B37, 0x418700)
    entries = metadata["army_entry_vas"]
    draw_entry = entries["draw.draw_army"]
    native_hook = entries["draw.native_suffix_hook"]
    if _read(candidate, draw_entry, 2) != bytes.fromhex("9c60") or _read(candidate, native_hook, 2) != bytes.fromhex("9c60"):
        raise ValueError("emitted army entry prologue differs")
    native_return = _call_return(candidate, native_hook + 2, draw_entry)
    compose_return = entries["composition.compose.draw_return"]
    if (_call_return(candidate, compose_return - 5, draw_entry) != compose_return or
            _read(candidate, compose_return, 3) != bytes.fromhex("83f801") or
            _read(candidate, native_return, 2) != bytes.fromhex("85c0")):
        raise ValueError("emitted army draw-return observer differs")

    p = _printf
    same = "(@$tid == @$t2) & (poi(005202e4) == @$t1)"
    own = same + " & (poi(00511b58) == 3) & (poi(00514194) == 3) & (poi(00526994) == 1)"
    surface = ("(wo(poi(005202e0)) == 0n1024) & (wo(poi(005202e0)+2) == 0n768) & "
               "(poi(poi(005202e0)+4) >= 00010000) & (poi(poi(005202e0)+4) <= fff40000)")
    records = {}
    records[80] = (0x406FA1, _guard(own + " & (@esp == @$t3) & (@$t0 == 9) & (@$t5 == @$t6) & (@$t7 >= 1)",
        "r @$t0=10; " + p("SHSEL_READY tid=%x eip=%p esp=%p selected=%d prior=%d lower=%d owner=%p surface=%p base=%p width=%d height=%d vtable=%p",
        "@$tid", "@eip", "@esp", "poi(00511b58)", "poi(00514194)", "poi(00526994)", "poi(005199d8)",
        "poi(005202e0)", "poi(poi(005202e0)+4)", "wo(poi(005202e0))", "wo(poi(005202e0)+2)",
        "poi(poi(005202e0)+b8)") + "; .echo SHSEL_HOST_READY"))
    records[81] = (0x408131, _guard(same + " & (@$t0 == 2) & (@eax == 1) & (poi(00511b58) == 3) & (@esp == @$t3-0n24)",
        "r @$t0=3; " + p("SHSEL_SELECTION_WRITE selected=%d eax=%x tid=%x esp=%p", "poi(00511b58)", "@eax", "@$tid", "@esp") + "; gc"))
    records[82] = (0x408136, p("SHSEL_SELECTION_FAIL selected=%d eax=%x", "poi(00511b58)", "@eax") + "; .echo SHSEL_REJECT selection_failed; q")
    records[83] = (0x406980, _guard(same + " & (@$t0 == 3) & (@esp == @$t3-4) & (poi(@esp) == 00406fa1)",
        "r @$t0=4; eb 005451c0 00; ed 00544d04 0; " + p("SHSEL_UPDATER selected=%d prior=%d lower=%d caller=%p",
        "poi(00511b58)", "poi(00514194)", "poi(00526994)", "poi(@esp)") + "; gc"))
    for number, va, phase, name in ((84, 0x40A500, 4, "PANEL_UPDATE"), (85, 0x423B00, 5, "ARMY_OPEN"), (86, 0x423420, 6, "ARMY_DRAW")):
        records[number] = (va, _guard(same + f" & (@$t0 == {phase}) & (poi(00511b58) == 3)",
            f"r @$t0={phase+1}; " + p("SHSEL_" + name + " selected=%d prior=%d lower=%d", "poi(00511b58)", "poi(00514194)", "poi(00526994)") + "; gc"))
    records[87] = (0x4080EF, _guard(same + " & (@$t0 == 1) & (@esi == 0n16) & (@ecx == 0n38) & (@edx == 3) & ((poi(00511b58) & 0x00000000ffffffff) == 0xffffffff) & (poi(005202ec) == 0)",
        "r @$t0=2; " + p("SHSEL_OCCUPANCY world=(%d,%d) unit=%d selected_before=%d player=%d", "@esi", "@ecx>>1", "@edx", "poi(00511b58)", "poi(005202ec)") + "; gc"))
    for number, va, phase, name in ((88, before, 7, "before-redraw"), (89, after, 8, "after-redraw")):
        extra_guard = " & (@$t5 >= 1) & (@$t5 == @$t6) & (@$t4 <= 1)" + (" & (@$t7 >= 1)" if number == 89 else "")
        body = f"r @$t0={phase+1}; " + p("SHSEL_PAIRED event=" + name + " selected=%d prior=%d lower=%d surface=%p base=%p size=(%d,%d)",
            "poi(00511b58)", "poi(00514194)", "poi(00526994)", "poi(005202e0)", "poi(poi(005202e0)+4)", "wo(poi(005202e0))", "wo(poi(005202e0)+2)")
        body += f"; .writemem {directory}/{name}.raw poi(poi(005202e0)+4) L0n786432; gc"
        records[number] = (va, _guard(own + f" & (@$t0 == {phase}) & " + surface + extra_guard, body))
    records[90] = (draw_entry, _guard(own + f" & ((@$t0 == 7) | (@$t0 == 8)) & (@$t5 == @$t6) & ((poi(@esp) == {native_return:08x}) | (poi(@esp) == {compose_return:08x}))",
        "r @$t5=@$t5+1; r @$t8=@esp; r @$t9=poi(@esp); " + p("SHSEL_DRAW_ENTRY tid=%x esp=%p caller=%p count=%d font7_cache=%p", "@$tid", "@esp", "poi(@esp)", "@$t5", "poi(00511f20)") + "; gc"))
    for number, va, label in ((91, native_return, "native"), (92, compose_return, "composition")):
        body = "r @$t6=@$t6+1; " + ("r @$t7=@$t7+1; " if label == "composition" else "r @$t4=@eax; ")
        body += p("SHSEL_DRAW_RETURN route=" + label + " tid=%x esp=%p status=%d count=%d", "@$tid", "@esp", "@eax", "@$t6") + "; gc"
        status = "(@eax == 1)" if label == "composition" else "((@eax == 0) | (@eax == 1))"
        records[number] = (va, _guard(own + f" & (@$t9 == {va:08x}) & (@esp == @$t8+4) & {status} & (@$t5 == @$t6+1)", body))

    handoff = p("PTILE_TRACE_CLOSED tid=%x eip=%p esp=%p", "@$tid", "@eip", "@esp") + "; "
    handoff += "; ".join("bd " + str(i) for i in range(70, 78)) + "; "
    handoff_conditions = ["(@eip == 00406fa0)", "(@$t14 == 1)", "(@$t13 == 4)",
        "(poi(005199d8) == 0040ad40)", "(poi(00526994) == 0)", "(poi(00526990) == 0)",
        "(poi(005202ec) == 0)", "((poi(00511b58) & 0x00000000ffffffff) == 0xffffffff)",
        "((poi(00514194) & 0x00000000ffffffff) == 0xffffffff)"]
    conditions = " & ".join(handoff_conditions)
    # DWORD sentinel identity is explicit: this x86 CDB sign-extends poi's
    # 0xffffffff to ULONG64, while the user-mode numeric literal is unsigned.
    # Read-only diagnosis precedes the guard. %I64x exposes the
    # evaluator's full integer, while %d shows the stored DWORD as signed.
    # This identifies a rejected state/comparison without presuming its cause.
    handoff += p("SHSEL_HANDOFF eip=%p t14=%I64x t13=%I64x gd=%p owner=%p lower=%x post=%x player=(%x,%d) selected=(%I64x,%d) prior=(%I64x,%d)",
        "@eip", "@$t14", "@$t13", "poi(005202e4)", "poi(005199d8)", "poi(00526994)", "poi(00526990)",
        "poi(005202ec)", "poi(005202ec)", "poi(00511b58)", "poi(00511b58)", "poi(00514194)", "poi(00514194)") + "; "
    handoff += p("SHSEL_HANDOFF_CHECKS eip=%d t14=%d t13=%d owner=%d lower=%d post=%d player=%d selected=%d prior=%d",
        *handoff_conditions) + "; "
    setup = "r @$t1=poi(005202e4); r @$t2=@$tid; r @$t3=@esp; r @$t0=1; r @$t4=ffffffff; r @$t5=0; r @$t6=0; r @$t7=0; "
    body = p("SHSEL_BEGIN tid=%x eip=%p esp=%p old_scroll=(%d,%d) selected=%d prior=%d", "@$tid", "@eip", "@esp", "poi(@$t1+222e8)", "poi(@$t1+222ec)", "poi(00511b58)", "poi(00514194)")
    body += "; ed @$t1+222e8 0n10; ed 00544cfc (0n448 << by(0054512c)); ed 00544d00 (0n176 << by(0054512c)); eb 005451c0 80; ed 00544d04 1; "
    body += p("SHSEL_CONTROLLED scroll=(10,17) screen=(448,176) unit=3 world=(16,19) predicate_forced=0 native_entry=00408030 updater=00406980")
    body += "; " + "; ".join("be " + str(i) for i in records)
    body += "; r esp=@esp-4; ed @esp 00406fa1; r esp=@esp-4; ed @esp 00406980; r eip=00408030; gc"
    world_conditions = ["(poi(@$t1+222e0) == 0n100)", "(poi(@$t1+222e4) == 0n100)",
        "(poi(@$t1+222ec) == 0n17)", "(poi(@$t1+24765) == 00130010)", "(by(@$t1+24769) == 0)"]
    setup += p("SHSEL_WORLD_CHECKS width=%d height=%d scroll_y=%d unit_xy=%d unit_owner=%d", *world_conditions) + "; "
    setup += _guard(" & ".join(world_conditions), body)
    handoff += _guard(conditions, setup)

    checked = {}
    for va, size in ((0x408030, 269), (0x406980, 675), (0x40A490, 112), (0x40A500, 247),
                     (0x423B00, 63), (0x423420, 825), (0x406FA0, 6)):
        checked.update({va + i: value for i, value in enumerate(_read(candidate, va, size))})
    checks = [f"(by({va:08x}) != 0x{value:02x})" for va, value in sorted(checked.items())]
    bytechecks = "\n".join(".if (" + " | ".join(checks[i:i+48]) + ") { .echo SHSEL_REJECT loaded_bytes; q }" for i in range(0, len(checks), 48))
    bytechecks += "\n.echo SHSEL_BYTES_PASS\n"
    startup = "\n".join(f'bp{number} {va:08x} "{commands}"\nbd {number}' for number, (va, commands) in records.items()) + "\n"
    template = render_probe(BASE_PROBE.read_text(encoding="utf-8-sig"), RESOLUTION, compiler.producer.builder.BASE_STAGE)["template"]
    template = re.sub(r"(?m)^g$", lambda _: initial_extra.strip() + "\ng", template)
    command_packet = dict(resolution=RESOLUTION, map_probe_template=template, handoff_action=handoff,
                         byte_checks_before_first_breakpoint=bytechecks, startup_commands_before_final_g=startup)
    compiled = compiler.compile_probe(command_packet)
    verify_sources()
    return dict(schema="clash95_framed_army_selection_probe_v1", revision=REVISION, stage=builder.STAGE,
        resolution=RESOLUTION, width=1024, height=768, candidate_sha256=sha(candidate), original_sha256=sha(original),
        save_sha256=SAVE_SHA256, unit=3, unit_xy=[16, 19], unit_squad_types=types[:8],
        controlled_scroll=[10, 17], controlled_mouse=[448, 176], native_predicate_forced=False,
        capture_dir=directory, minimap_viewport=minimap_viewport, compiled_probe=compiled, probe_sha256=sha(compiled.encode("ascii")),
        initial_extra=initial_extra, initial_extra_sha256=sha(initial_extra.encode("ascii")),
        observer_vas={str(number): va for number, (va, _) in records.items()},
        native_call_returns={"portraits": before, "redraw": after, "native_draw": native_return, "composition_draw": compose_return},
        source_sha256=metadata["source_sha256"] | sources, manual_input_proof=False, promotion_ready=False,
        runtime_executed=False, capture_class="e0_software_diagnostic", limits=LIMITS)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original", required=True, type=Path)
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--save", required=True, type=Path)
    parser.add_argument("--capture-dir", required=True)
    parser.add_argument("--minimap-viewport", action="store_true")
    args = parser.parse_args()
    directory = Path(capture_directory(args.capture_dir))
    if os.name != "nt" or directory.exists():
        parser.error("CLI output requires a new Windows directory under C:/ClashCaptures")
    packet = build_selection_probe(args.original.read_bytes(), args.candidate.read_bytes(), args.save.read_bytes(),
        capture_dir=args.capture_dir, minimap_viewport=args.minimap_viewport)
    directory.mkdir(parents=True, exist_ok=False)
    for name, data in (("selection.cdb", packet["compiled_probe"].encode("ascii")),
                       ("initial.cdb", packet["initial_extra"].encode("ascii")),
                       ("packet.json", (json.dumps(packet, indent=2) + "\n").encode("utf-8"))):
        with (directory / name).open("xb") as stream:
            stream.write(data)
    print(json.dumps(dict(packet=str(directory / "packet.json"), stage=packet["stage"],
                         probe_sha256=packet["probe_sha256"], runtime_executed=False)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
