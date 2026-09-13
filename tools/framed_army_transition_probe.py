#!/usr/bin/env python3
"""Prepare six controlled native army transitions; never execute the game.

The exact army candidate and save are reconstructed through the frozen selection
producer. Native selection and Map mode callbacks change the state themselves.
This protocol observes each panel branch and complete terrain return, then saves
a stopped software surface. It does not exercise ordinary map input dispatch.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re

import framed_army_selection_probe as base

ROOT = base.ROOT
BASE_SHA256 = "e5476178b80c29cf35ac2c64f8f89cb29a34596f8b3d1aa971ae456d0bbfc2e8"
REVISION = "controlled_native_army_transitions_v1"
STEPS = (
    dict(step=1, name="select-eight", unit=3, old=-1, prior=-1, lower=1, xy=[16, 19], screen=[448, 176], types=[16, 16, 1, 1, 1, 1, 1, 1], branch="open"),
    dict(step=2, name="switch-four", unit=1, old=3, prior=3, lower=1, xy=[15, 22], screen=[384, 368], types=[1, 16, 1, 15], branch="switch"),
    dict(step=3, name="switch-two", unit=2, old=1, prior=1, lower=1, xy=[15, 23], screen=[384, 432], types=[17, 9], branch="switch"),
    dict(step=4, name="single-unit", unit=0, old=2, prior=2, lower=0, xy=[14, 22], screen=[320, 368], types=[5], branch="close"),
    dict(step=5, name="reselect-eight", unit=3, old=0, prior=-1, lower=1, xy=[16, 19], screen=[448, 176], types=[16, 16, 1, 1, 1, 1, 1, 1], branch="open"),
    dict(step=6, name="map-mode-deselect", unit=-1, old=3, prior=3, lower=0, xy=None, screen=None, types=[], branch="close"),
)
NATIVE_SPANS = ((0x408030, 269), (0x406980, 675), (0x40A490, 359),
                (0x423B00, 174), (0x423420, 825), (0x409D80, 76),
                (0x418700, 25), (0x406FA0, 6), (0x511D40, 57))
LIMITS = [
    "The frozen initial-map startup uses controlled menu entry; transition predicate claims begin after its trace closes.",
    "Direct native408030 calls are not the ordinary40B10C/4084A0 map click-dispatch route.",
    "Controlled mouse/button state and native Map mode callback injection are not manual or OS input proof.",
    "No selected index, squad, visibility, occupancy, native predicate result or callback result is forced.",
    "Each stopped E0 copy is software composition; primary-only layers and final visible wrapper remain separate.",
    "These six transitions at1024x768 do not prove portrait clicking, other resolutions, endurance or promotion.",
    "The final sentinel does not resume the interrupted ordinary map call; the host must prove owned cleanup.",
]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def verify_sources():
    if sha(Path(base.__file__).read_bytes()) != BASE_SHA256:
        raise ValueError("frozen selection producer differs")
    return base.verify_sources() | {"tools/framed_army_selection_probe.py": BASE_SHA256}


def _guard(condition, commands):
    return ".if (" + condition + ") { " + commands + " } .else { .echo ATX_REJECT native_contract; q }"


def build_transition_probe(original, candidate, save, *, capture_dir, minimap_viewport=True):
    """Return a deterministic, complete probe packet without writing files."""
    sources = verify_sources()
    prior = base.build_selection_probe(original, candidate, save,
                                      capture_dir=capture_dir, minimap_viewport=minimap_viewport)
    directory = prior["capture_dir"]
    # Exact save hash and candidate reconstruction precede this independent
    # record inventory. The save offsets are not runtime pointer assumptions.
    import struct
    for step in STEPS[:-1]:
        unit = save[147190 + step["unit"] * 725:147190 + (step["unit"] + 1) * 725]
        xy = list(struct.unpack_from("<hh", unit))
        types = [struct.unpack_from("<h", unit, 6 + 31 * j)[0] for j in range(10)]
        if xy != step["xy"] or unit[4] != 0 or types != step["types"] + [-1] * (10 - len(step["types"])):
            raise ValueError("source save transition unit differs")
    read = lambda va, size: base._read(candidate, va, size)
    calls = {"open": base._call_return(candidate, 0x423B37, 0x418700),
             "switch": base._call_return(candidate, 0x40A5E5, 0x423B90),
             "close": base._call_return(candidate, 0x423B5F, 0x418700),
             "deselect": base._call_return(candidate, 0x409DC3, 0x418700)}
    if read(0x423BA9, 5) != bytes.fromhex("e9524bffff"):
        raise ValueError("native switch tail jump differs")
    for va, expected in ((0x409DA8, "890d581b5100"), (0x409D81, "833d581b5100ff"),
                         (0x511D60, "809d4000"), (0x418700, "e982b2140090909090")):
        if read(va, len(bytes.fromhex(expected))) != bytes.fromhex(expected):
            raise ValueError(f"native transition boundary differs at{va:08x}")
    p = base._printf
    same = "(@$tid == @$t2) & (poi(005202e4) == @$t1) & (poi(005199d8) == 0040ad40) & (poi(005202ec) == 0)"
    physical = "(wo(poi(005202e0)) == 0n1024) & (wo(poi(005202e0)+2) == 0n768) & (poi(poi(005202e0)+b8) == 0050ee24)"
    final_owner = "((poi(00511b58) & 0x00000000ffffffff) == (@$t10 & 0x00000000ffffffff)) & (poi(00526994) == @$t18) & (((@$t18 == 1) & (poi(00514194) == @$t10)) | ((@$t18 == 0) & ((poi(00514194) & 0x00000000ffffffff) == 0xffffffff)))"
    records = {}

    def obs(kind, *extra):
        # A uniform read-only receipt makes the parser inspect actual state at
        # every observer, including phase, caller and counters. The exact CDB
        # guard additionally authenticates native stack relationships.
        message = "ATX_OBS kind=" + kind + " step=%d phase=%d tid=%x eip=%p esp=%p selected=%d prior=%d lower=%d owner=%p gd=%p eax=%x ecx=%x edx=%x esi=%x caller=%p draws=(%d,%d,%d) maps=(%d,%d)"
        args = ["@$t0", "@$t4", "@$tid", "@eip", "@esp", "poi(00511b58)", "poi(00514194)", "poi(00526994)",
                "poi(005199d8)", "poi(005202e4)", "@eax", "@ecx", "@edx", "@esi", "poi(@esp)", "@$t5", "@$t6", "@$t7", "@$t16", "@$t17"]
        return p(message, *args) + ("; " + "; ".join(extra) if extra else "")

    def begin(step):
        def number(value):
            return "ffffffff" if value == -1 else "0n" + str(value)
        setup = "; ".join("r @$" + key + "=" + number(value) for key, value in {
            "t0": step["step"], "t4": 1, "t5": 0, "t6": 0, "t7": 0,
            "t10": step["unit"], "t11": step["old"], "t16": 0, "t17": 0,
            "t18": step["lower"], "t19": step["prior"]}.items()) + "; "
        before = same + " & (@esp == @$t3) & ((poi(00511b58) & 0x00000000ffffffff) == (@$t11 & 0x00000000ffffffff)) & ((poi(00514194) & 0x00000000ffffffff) == (@$t19 & 0x00000000ffffffff))"
        if step["screen"]:
            x, y = step["screen"]
            setup += f"r @$t12=0n{step['xy'][0]}; r @$t13=0n{step['xy'][1]}; "
            body = f"ed 00544cfc (0n{x} << by(0054512c)); ed 00544d00 (0n{y} << by(0054512c)); eb 005451c0 80; ed 00544d04 1; "
            body += obs("begin") + "; r esp=@esp-4; ed @esp 00406fa1; r esp=@esp-4; ed @esp 00406980; r eip=00408030; gc"
        else:
            body = "eb 005451c0 00; ed 00544d04 0; " + obs("begin")
            body += "; r eax=00511d40; r esp=@esp-4; ed @esp 00406fa1; r eip=00409d80; gc"
        return setup + _guard(before, body)

    records[101] = (0x4080EF, _guard(same + " & (@$t0 < 6) & (@$t4 == 1) & (@esi == @$t12) & (@ecx == @$t13+@$t13) & (@edx == @$t10) & ((poi(00511b58) & 0x00000000ffffffff) == (@$t11 & 0x00000000ffffffff))",
        "r @$t4=2; " + obs("occupancy", "gc")))
    records[102] = (0x408131, _guard(same + " & (@$t0 < 6) & (@$t4 == 2) & (@eax == 1) & (poi(00511b58) == @$t10) & (@esp == @$t3-0n24)",
        "r @$t4=3; " + obs("selected", "gc")))
    records[103] = (0x408136, obs("selection-failed", ".echo ATX_REJECT selection_failed", "q"))
    records[104] = (0x406980, _guard(same + " & (@$t0 < 6) & (@$t4 == 3) & (@esp == @$t3-4) & (poi(@esp) == 00406fa1)",
        "r @$t4=4; eb 005451c0 00; ed 00544d04 0; " + obs("updater", "gc")))
    records[105] = (0x40A500, _guard(same + " & (((@$t0 < 6) & (@$t4 == 4)) | ((@$t0 == 6) & (@$t4 == 3))) & ((poi(00511b58) & 0x00000000ffffffff) == (@$t10 & 0x00000000ffffffff))",
        "r @$t4=5; " + obs("panel-update", "gc")))
    for number, va, route in ((106, 0x423B00, "open"), (107, 0x423B90, "switch"), (108, 0x423B40, "close")):
        allowed = " | ".join(f"(@$t0 == 0n{s['step']})" for s in STEPS if s["branch"] == route)
        records[number] = (va, _guard(same + " & (@$t4 == 5) & (" + allowed + ")",
            "r @$t4=6; " + obs(route, "gc")))
    draw_entry = prior["observer_vas"]["90"]
    native_return = prior["native_call_returns"]["native_draw"]
    compose_return = prior["native_call_returns"]["composition_draw"]
    records[109] = (draw_entry, _guard(same + " & " + final_owner + " & (@$t18 == 1) & ((@$t4 == 6) | (@$t4 == 7)) & (@$t5 == @$t6) & " +
        f"((poi(@esp) == {native_return:08x}) | (poi(@esp) == {compose_return:08x}))",
        "r @$t5=@$t5+1; r @$t8=@esp; r @$t9=poi(@esp); " + obs("draw-entry", "gc")))
    for number, va, kind in ((110, native_return, "draw-native-return"), (111, compose_return, "draw-composition-return")):
        is_comp = number == 111
        status = "(@eax == 1)" if is_comp else "((@eax == 0) | (@eax == 1))"
        records[number] = (va, _guard(same + " & " + final_owner + f" & (@$t9 == {va:08x}) & (@esp == @$t8+4) & (@$t5 == @$t6+1) & " + status,
            "r @$t6=@$t6+1; " + ("r @$t7=@$t7+1; " if is_comp else "") + obs(kind, "gc")))
    allowed_callers = " | ".join(f"(poi(@esp) == {va:08x})" for va in calls.values())
    records[112] = (0x418700, _guard(same + " & " + final_owner + " & ((@$t4 == 6) | ((@$t0 == 6) & (@$t4 == 8))) & (@$t16 == @$t17) & (" + allowed_callers + ")",
        "r @$t4=@$t4+1; r @$t16=@$t16+1; r @$t14=@esp; r @$t15=poi(@esp); " + obs("map-entry", "gc")))
    for number, (route, va) in enumerate(calls.items(), 113):
        # The switch path tail-jumps from423B90, so its terrain return is the
        # CALL40A5E5 fall-through40A5EA, not an invented local return address.
        allowed = [s["step"] for s in STEPS if s["branch"] == route] if route != "deselect" else [6]
        guard_steps = " | ".join(f"(@$t0 == 0n{n})" for n in allowed)
        phase = 9 if route == "deselect" else 7
        records[number] = (va, _guard(same + " & " + final_owner + f" & (@$t4 == {phase}) & (@$t15 == {va:08x}) & (@esp == @$t14+4) & (@$t16 == @$t17+1) & (" + guard_steps + ")",
            "r @$t4=@$t4+1; r @$t17=@$t17+1; " + obs("map-return", "gc")))
    records[117] = (0x409D81, _guard(same + " & (@$t0 == 6) & (@$t4 == 1) & (@esp == @$t3-8) & (@eax == 00511d40) & (poi(00511d60) == 00409d80) & (poi(00511b58) == 3)",
        "r @$t4=2; " + obs("deselect-entry", "gc")))
    records[118] = (0x409DA8, _guard(same + " & (@$t0 == 6) & (@$t4 == 2) & ((@ecx & 0x00000000ffffffff) == 0xffffffff) & (poi(00511b58) == 3) & (poi(00511b5c) == 3)",
        "r @$t4=3; " + obs("deselect-write", "gc")))
    records[119] = (0x409DB3, _guard(same + " & (@$t0 == 6) & (@$t4 == 8) & " + final_owner,
        obs("deselect-panel-return", "gc")))

    ready_guard = same + " & " + physical + " & " + final_owner + " & (@esp == @$t3) & (@$t5 == @$t6) & "
    ready_guard += "(((@$t0 < 6) & (@$t4 == 8) & (@$t16 == 1) & (@$t17 == 1)) | ((@$t0 == 6) & (@$t4 == 0n10) & (@$t16 == 2) & (@$t17 == 2))) & "
    ready_guard += "(((@$t18 == 1) & (@$t5 >= 2) & (@$t7 >= 1)) | ((@$t18 == 0) & (@$t5 == 0) & (@$t7 == 0)))"
    # Keep this dispatcher below4096 characters by using one bound, source-
    # quiet command file for each checkpoint and next call. No downloaded or
    # caller-supplied debugger command is accepted.
    supplemental = {}
    dispatch = []
    for step in STEPS:
        n = step["step"]
        path = f"{directory}/transition-{n}.cdb"
        line = obs("snapshot") + "\n"
        line += p("ATX_SURFACE step=%d surface=%p base=%p width=%d height=%d vtable=%p", "@$t0", "poi(005202e0)", "poi(poi(005202e0)+4)", "wo(poi(005202e0))", "wo(poi(005202e0)+2)", "poi(poi(005202e0)+b8)").replace(r'\"', '"') + "\n"
        line += f".writemem {directory}/step-{n}.header.raw poi(005202e0) L0n188\n.writemem {directory}/step-{n}.raw poi(poi(005202e0)+4) L0n786432\n"
        if n < len(STEPS):
            line += begin(STEPS[n]).replace(r'\"', '"') + "\n"
        else:
            line += p("ATX_READY tid=%x eip=%p esp=%p selected=%d prior=%d lower=%d owner=%p surface=%p base=%p width=%d height=%d vtable=%p",
                "@$tid", "@eip", "@esp", "poi(00511b58)", "poi(00514194)", "poi(00526994)", "poi(005199d8)", "poi(005202e0)", "poi(poi(005202e0)+4)", "wo(poi(005202e0))", "wo(poi(005202e0)+2)", "poi(poi(005202e0)+b8)").replace(r'\"', '"') + "\n.echo ATX_HOST_READY\n"
        # obs() emits quoted breakpoint text; supplemental files are top-level
        # commands, and therefore need ordinary quotes and single \n escapes.
        line = line.replace(r'\"', '"').replace(r'\\n', r'\n')
        supplemental[path] = line
        dispatch.append((".if" if n == 1 else ".elsif") + f" (@$t0 == 0n{n}) {{ $$>a<\\\"{path}\\\"; }}")
    records[100] = (0x406FA1, _guard(ready_guard, " ".join(dispatch) + " .else { .echo ATX_REJECT step; q }"))

    handoff = p("PTILE_TRACE_CLOSED tid=%x eip=%p esp=%p", "@$tid", "@eip", "@esp") + "; "
    handoff += "; ".join("bd " + str(i) for i in range(70, 78)) + "; "
    guard = "(@eip == 00406fa0) & (@$t14 == 1) & (@$t13 == 4) & (poi(005199d8) == 0040ad40) & (poi(00526994) == 0) & (poi(00526990) == 0) & (poi(005202ec) == 0) & ((poi(00511b58) & 0x00000000ffffffff) == 0xffffffff) & ((poi(00514194) & 0x00000000ffffffff) == 0xffffffff)"
    setup = "r @$t1=poi(005202e4); r @$t2=@$tid; r @$t3=@esp; "
    setup += _guard("(poi(@$t1+222e0) == 0n100) & (poi(@$t1+222e4) == 0n100) & (poi(@$t1+222ec) == 0n17)",
                    "ed @$t1+222e8 0n10; " + "; ".join("be " + str(i) for i in records) + "; " + begin(STEPS[0]))
    handoff += _guard(guard, setup)
    checked = {va + i: value for va, size in NATIVE_SPANS for i, value in enumerate(read(va, size))}
    tests = [f"(by({va:08x}) != 0x{value:02x})" for va, value in sorted(checked.items())]
    bytechecks = "\n".join(".if (" + " | ".join(tests[i:i + 48]) + ") { .echo ATX_REJECT loaded_bytes; q }" for i in range(0, len(tests), 48)) + "\n.echo ATX_BYTES_PASS\n"
    startup = "\n".join(f'bp{number} {va:08x} "{commands}"\nbd {number}' for number, (va, commands) in records.items()) + "\n"
    template = base.render_probe(base.BASE_PROBE.read_text(encoding="utf-8-sig"), "1024x768", base.compiler.producer.builder.BASE_STAGE)["template"]
    template = re.sub(r"(?m)^g$", lambda _: prior["initial_extra"].strip() + "\ng", template)
    compiled = base.compiler.compile_probe(dict(resolution="1024x768", map_probe_template=template, handoff_action=handoff,
        byte_checks_before_first_breakpoint=bytechecks, startup_commands_before_final_g=startup))
    if max(map(len, compiled.splitlines())) >= 4096 or any(max(map(len, s.splitlines())) >= 4096 for s in supplemental.values()):
        raise ValueError("debugger line exceeds admitted transport limit")
    verify_sources()
    return dict(schema="clash95_framed_army_transition_probe_v1", revision=REVISION, stage=prior["stage"], resolution="1024x768",
        width=1024, height=768, candidate_sha256=prior["candidate_sha256"], original_sha256=prior["original_sha256"],
        save_sha256=prior["save_sha256"], capture_dir=directory, minimap_viewport=minimap_viewport,
        steps=json.loads(json.dumps(STEPS)), source_sha256=prior["source_sha256"] | sources,
        compiled_probe=compiled, probe_sha256=sha(compiled.encode("ascii")),
        supplemental_commands=supplemental, supplemental_sha256={name: sha(text.encode("ascii")) for name, text in supplemental.items()},
        initial_extra=prior["initial_extra"], initial_extra_sha256=prior["initial_extra_sha256"],
        observer_vas={str(n): va for n, (va, _) in records.items()}, map_return_vas=calls,
        draw_return_vas=dict(native=native_return, composition=compose_return),
        controlled_input=True, native_predicate_forced=False, selected_value_forced=False,
        runtime_executed=False, manual_input_proof=False, promotion_ready=False, limits=LIMITS)
