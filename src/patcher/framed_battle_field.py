"""Uninstalled native-size tactical field drawing and visibility adapters.

The whole current army candidate is reconstructed before emitting any bytes.
Three hook descriptors are returned, never installed. Installation requires a
separate battle owner/lifetime and HUD-routing admission helper plus the exact
input, scroll and presentation integration listed in ``integration_required``.
Native artwork, terrain indices, arena rows and world dimensions are unchanged.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from pathlib import Path
import struct

from . import partial_tile_clip as clip
from . import framed_battle_coordinates as coordinates
from . import pe_extension as pe
from .framed_battle_viewport import TacticalViewport

ROOT = Path(__file__).resolve().parents[2]
PINNED_SOURCES = {
    "tools/build_framed_army_candidate.py": "4060856f60ab8589f9dbc0ae73df142cf906e4905f3c24aaa6c8292a161bc167",
    "src/patcher/framed_battle_coordinates.py": "47c017a412ec12378785c400fa505baed3ae0825a58e5b1fefad00c67de4260c",
    "src/patcher/framed_battle_viewport.py": "8673e36bd04ded2afc8cc3b9d7ff2fed4c48dae891fe289509b44a9070c23bc6",
}
# Continuous GNU objdump2.42 decoding of the authenticated original, 2026-09-06.
# Ends are exclusive. Whole-function hashes avoid identifying opcodes by bytes
# that could equally occur inside operands.
NATIVE_SPANS = {
    "full": (0x430C20, 0x430E8C, "d3b8e051c30ddf810221035894f081c5886a9c2119ca9564dacef82b2279fe43"),
    "incremental_tail": (0x430B64, 0x430C17, "99bb84d6a5609f4c577a18f68b2ac830b0fb2207172a84d0d7ee3238f9bcfdda"),
    "tile": (0x42FFB0, 0x430B12, "d63f254e1d28a6314996b7ecc9d4b3c917351883a8e363b64d5092243d041a4f"),
    "visibility": (0x42C0F0, 0x42C12B, "5412f74f7508ca12ae83e2b28d1b94b84cfacaa95524547bf11f0630b5c4f460"),
}
FULL_CALLS = {0x430C70: 0x42FFB0, 0x430CE3: 0x460F90, 0x430CFE: 0x460F90,
    0x430D1B: 0x460F90, 0x430D36: 0x460F90, 0x430D61: 0x4024E0,
    0x430D8A: 0x4024E0, 0x430D98: 0x461000, 0x430DC0: 0x4024E0,
    0x430DCE: 0x460EA0, 0x430DFB: 0x4024E0, 0x430E27: 0x460F90,
    0x430E4F: 0x4024E0, 0x430E7D: 0x4024E0}
INCREMENTAL_CALLS = {0x430BA6: 0x42FFB0, 0x430BCD: 0x460BB0,
                     0x430BF9: 0x4024E0, 0x430C03: 0x460EA0}
HIGHLOW = {
    "full": (10,16,21,37,60,92,98,104,110,158,191,218,247,274,317,358,372,412,426,471,515,553,599),
    "incremental_tail": (49,57,97,145,155,166),
}
GLOBAL_PURPOSES = {0x532048: "battle_state_global", 0x5202E0: "field_surface_global",
    0x511230: "render_device_global", 0x544CFC: "mouse_raw_x", 0x544D00: "mouse_raw_y",
    0x54512C: "mouse_shift", 0x544D14: "cursor_descriptor_global",
    0x544D10: "cursor_visible", 0x544CD8: "cursor_object"}
CALL_PURPOSES = {0x42FFB0: "native_battle_tile", 0x460F90: "native_cursor_hide",
    0x461000: "native_cursor_background", 0x460EA0: "native_cursor_restore",
    0x4024E0: "native_rectangle_copy", 0x460BB0: "native_cursor_dirty"}


@dataclass(frozen=True)
class BattleFieldBundle(clip.AdapterBundle):
    hook_sites: tuple = ()
    removed_highlow_rvas: tuple = ()
    candidate_sha256: str = ""
    source_contract: dict = field(default_factory=dict)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def verify_sources():
    for name, expected in PINNED_SOURCES.items():
        if sha((ROOT / name).read_bytes()) != expected:
            raise ValueError("reviewed battle field source differs: " + name)
    return dict(PINNED_SOURCES)


def integration_required():
    return [
        "Do not install these three hooks alone. admission_va must prove battle owner/thread/lifetime, physical field ownership and isolated HUD routing.",
        "Replace initial42F2F5->51BA00 centered E0 copy; replace42E4ED->51BAA0 and42E501->51BAF0 whole-screen input transforms.",
        "Isolate430F80 E0 HUD writes beginningx335,42E8B0/42E9E0 primary frame/widgets,42DEC0 primary overlays and42E160 HUD hover. Copy native480..639 slices0..367 and368..479 to the approved right/top and right/bottom anchors.",
        "Add physical pixel admission before42C870 occupancy lookup and42CB50 division/indexing; translate only the admitted field or HUD slice.",
        "Normalize42C840 key/drag,426E20 unit,428880 shot-midpoint,42E9E0 initial saved views and42E3C0 restored origins to0..world_columns-visible_columns. Keep800/804 actual dimensions and seven rows.",
        "Compose all four frame edges and inert padding. Authenticate an atomic new-stage PE build, hooks/HIGHLOW/loaded bytes, lifecycle restoration and runtime evidence separately.",
    ]


def emit_battle_field(original: bytes, candidate: bytes, *, base_va: int,
                      width: int, height: int, admission_va: int,
                      minimap_viewport: bool = True) -> BattleFieldBundle:
    """Return code and native hook descriptions, never an executable.

    draw_full / draw_incremental return EAX1 when drawn,0 when rejected.
    draw_incremental and visible_cell take signed world X in EAX and Y in EDX.
    visible_cell returns0/1 for a valid context,FFFFFFFF for rejected context.
    All helpers preserve every other GPR, ESP and EFLAGS including DF. Native
    callees run with DF clear; the caller's original flags are restored.

    admission_va is a required caller-provided, ABI-preserving EAX0/1 helper.
    It must establish readable state/cursor lifetime, owning thread and separated
    HUD/field composition; this module's numeric checks cannot establish those.
    Rejection writes no globals/pixels and calls no native draw/cursor routine.

    Hook adapters retain byte-authenticated native behavior on rejected context.
    Full/incremental admitted hooks preserve all incoming registers/flags;
    visibility returns the native EAX boolean. Unsupported native continuations
    and their original side effects are intentionally not reimplemented.
    """
    layout = TacticalViewport(width, height, 20)
    if any(type(v) is not int or not 0x10000 <= v <= 0x7FFF0000 for v in (base_va, admission_va)):
        raise ValueError("explicit x86 code/admission addresses required")
    if type(original) is not bytes or type(candidate) is not bytes or type(minimap_viewport) is not bool:
        raise ValueError("immutable images and explicit minimap boolean required")
    clip.verify_original(original)
    sources = verify_sources()
    from tools import build_framed_army_candidate as builder
    from tools import build_framed_modal_candidate as modal_builder
    expected, metadata, _ = builder.build_candidate(original, f"{width}x{height}", minimap_viewport=minimap_viewport)
    if candidate != expected:
        raise ValueError("whole current army candidate reconstruction required")
    image = pe.inspect_pe(candidate)

    def read(data, va, size):
        off = clip.file_offset(data, va, size)
        return data[off:off+size]

    for name, (lo, hi, digest) in NATIVE_SPANS.items():
        if any(sha(read(data, lo, hi-lo)) != digest for data in (original, candidate)):
            raise ValueError("native battle source span differs: " + name)
    modal, _, _ = modal_builder.build_candidate(original, f"{width}x{height}", minimap_viewport=minimap_viewport)
    coord = coordinates.emit_battle_coordinates(original, modal, base_va=base_va,
        width=width, height=height, minimap_viewport=minimap_viewport)
    a = clip._Assembler(base_va)
    a.code.extend(coord.code); a.relocations.extend(coord.relocations)
    entries = {"coordinates." + k: v for k, v in coord.entries.items()}

    def transfer(opcode, target, purpose):
        a.emit(opcode); pos = len(a.code)
        a.relocations.append(clip.Relocation(pos, "rel32", target, purpose))
        a.u32(target - (base_va + pos + 4))

    def absolute(value):
        a.absolute(value, GLOBAL_PURPOSES[value])

    def reject(name, opcode="0f85"):
        a.branch(opcode, name + ".reject")

    def result(value):
        a.emit("c744241c"); a.u32(value); a.emit("619dc3")

    def context(name):
        a.label(name); entries[name] = base_va + len(a.code)
        a.emit("9c60fc")
        transfer("e8", admission_va, "required_battle_admission")
        a.emit("83f801"); reject(name)
        a.emit("a1"); absolute(0x532048)
        transfer("e8", coord.entries["visible_columns"], "battle_visible_columns")
        a.emit("83f8ff"); reject(name, "0f84")
        a.emit("89c5a1"); absolute(0x532048)
        a.emit("8b902803000031c9")
        transfer("e8", coord.entries["visible_world_cell"], "battle_context_scroll")
        a.emit("83f801"); reject(name)
        a.emit("8b35"); absolute(0x5202E0)
        a.emit("81fe00000100"); reject(name, "0f82")
        a.emit("81fe44ffff7f"); reject(name, "0f87")
        a.emit("f7c603000000"); reject(name)
        a.emit("813e"); a.u32(width | height << 16); reject(name)
        a.emit("8b460483f800"); reject(name, "0f84")
        a.emit("3d00000100"); reject(name, "0f82")
        a.emit("3d"); a.u32(0x80000000-width*height); reject(name, "0f87")
        a.emit("81beb8000000"); a.absolute(0x50EE24, "memory_vtable"); reject(name)

    context("draw_full")
    a.emit("a1"); absolute(0x544D14)
    a.emit("3d00000100"); reject("draw_full", "0f82")
    a.emit("3decffff7f"); reject("draw_full", "0f87")
    for offset in (12, 16):
        a.emit("8178" + bytes([offset]).hex() + "00000000"); reject("draw_full", "0f8e")
        a.emit("8178" + bytes([offset]).hex() + "00010000"); reject("draw_full", "0f8f")
    a.emit("ff35"); absolute(0x511230)  # Scoped render owner, outside hidden args.
    a.emit("5589e8c1e00683c02089c24a5250")  # visible, inclusive right, exclusive right.
    a.branch("e8", "native_full_clone")
    a.emit("83c40c5a8915"); absolute(0x511230)
    result(1)
    a.label("draw_full.reject"); result(0)

    for name in ("draw_incremental", "visible_cell"):
        context(name)
        a.emit("8b54241c8b4c2414a1"); absolute(0x532048)
        transfer("e8", coord.entries["visible_world_cell"], "battle_requested_cell")
        if name == "draw_incremental":
            a.emit("83f801"); reject(name)
            a.emit("8b44241c8b542414")
            a.branch("e8", "native_incremental_clone")
            result(1)
            a.label(name + ".reject"); result(0)
        else:
            a.emit("83f8010f94c00fb6c08944241c619dc3")
            a.label(name + ".reject"); result(0xFFFFFFFF)

    # The source clone has36 bytes of saves/locals. Its three hidden arguments
    # are exclusive right at+40, inclusive right at+44, visible columns at+48.
    # CALL adds4. Every replacement keeps its native instruction span length,
    # so all original internal branch targets and stack offsets remain valid.
    a.label("full_limits"); a.emit("8b7c2434bd07000000c3")
    a.label("cursor_overlap")
    a.emit("817c240cd0010000"); a.branch("0f8d", "cursor_disjoint")
    a.emit("83fe10"); a.branch("0f8e", "cursor_disjoint")
    a.emit("3b44242cc3")
    a.label("cursor_disjoint"); a.emit("39c0c3")  # Following native JGE takes no-overlap copy.
    a.label("compare_right"); a.emit("3b7c2430c3")
    a.label("set_right"); a.emit("8b7c2430c3")
    # Four native PUSH-right sites each have12 bytes of preceding arguments.
    # Push EAX, exchange return address into EAX, then onto the stack: RET
    # consumes only that address, leaving the right bound as a native argument.
    a.label("push_right"); a.emit("508b44244087442404870424c3")

    clone_edits = []

    def clone(name, calls, patches):
        lo, hi, _ = NATIVE_SPANS[name]
        a.label("native_" + name + "_clone")
        start = len(a.code); raw = bytearray(read(original, lo, hi-lo))
        fields = clip._original_highlow_fields(original, lo, hi-lo)
        if fields != set(HIGHLOW[name]):
            raise ValueError("native clone HIGHLOW inventory differs: " + name)
        for offset in sorted(fields):
            target = struct.unpack_from("<I", raw, offset)[0]
            a.relocations.append(clip.Relocation(start+offset, "abs32", target, GLOBAL_PURPOSES[target]))
        for va, target in calls.items():
            offset = va-lo
            if raw[offset] != 0xE8 or va+5+struct.unpack_from("<i", raw, offset+1)[0] != target:
                raise ValueError("decoded native CALL boundary differs")
            struct.pack_into("<i", raw, offset+1, target-(base_va+start+offset+5))
            a.relocations.append(clip.Relocation(start+offset+1, "rel32", target, CALL_PURPOSES[target]))
        for va, old, change in patches:
            offset = va-lo; old = bytes.fromhex(old)
            if raw[offset:offset+len(old)] != old:
                raise ValueError("decoded native scalar boundary differs")
            if isinstance(change, str):
                target = base_va+a.labels[change]
                new = b"\xe8"+struct.pack("<i", target-(base_va+start+offset+5))+b"\x90"*(len(old)-5)
                a.relocations.append(clip.Relocation(start+offset+1, "rel32", target, "full_"+change))
            else:
                new = change
            if len(new) != len(old):
                raise ValueError("native clone instruction size changed")
            raw[offset:offset+len(old)] = new
            clone_edits.append(dict(clone=name,source_va=va,source_offset=clip.file_offset(original,va,len(old)),
                emitted_va=base_va+start+offset,old_hex=old.hex(),new_hex=new.hex(),
                purpose=change if isinstance(change,str) else "seven_rows" if va==0x430C66 else "DWORD_zero_y_scroll"))
        a.code.extend(raw)

    clone("full", FULL_CALLS, [
        (0x430C39, "bf07000000", "full_limits"), (0x430C66, "01f8", bytes.fromhex("01e8")),
        (0x430CA8, "3de0010000", "cursor_overlap"),
        (0x430CE8, "81ffdf010000", "compare_right"), (0x430CF0, "bfdf010000", "set_right"),
        (0x430DD3, "81ffdf010000", "compare_right"),
        *[(va, "68df010000", "push_right") for va in (0x430D53,0x430DEF,0x430E43,0x430E71)]])
    a.label("native_incremental_clone")
    a.emit("51565583ec0889c1a1"); absolute(0x532048)
    a.emit("8b2d"); absolute(0x511230)
    # The native successful prefix establishes exactly this register/stack
    # frame. Admission already rejects off-field cells before any array index.
    clone("incremental_tail", INCREMENTAL_CALLS,
          [(0x430B77, "668b982c030000", bytes.fromhex("8b982c03000090"))])

    hooks = []
    for name, va, old, helper in (
        ("full_hook", 0x430C20, "5351525657", "draw_full"),
        ("incremental_hook", 0x430B20, "51565583ec08", "draw_incremental"),
        ("visibility_hook", 0x42C0F0, "53515689c1", "visible_cell")):
        a.label(name); entries[name] = base_va+len(a.code)
        a.emit("9c60"); a.branch("e8", helper)
        a.emit("83f8ff" if helper == "visible_cell" else "83f801")
        a.branch("0f84" if helper == "visible_cell" else "0f85", name+".native")
        if helper == "visible_cell":
            a.emit("8944241c")
        a.emit("619dc3")
        a.label(name+".native"); a.emit("619d")
        expected = bytes.fromhex(old)
        if any(read(data, va, len(expected)) != expected for data in (original, candidate)):
            raise ValueError("native entry hook bytes differ")
        a.emit(old)
        transfer("e9", va+len(expected), "native_"+name+"_continuation")
        target = entries[name]
        new = b"\xe9"+struct.pack("<i", target-va-5)+b"\x90"*(len(expected)-5)
        hooks.append(pe.HookPatch(image.file_offset(va-image.image_base,len(expected)),
            va-image.image_base,va,expected,new,"isolated tactical "+name,
            (pe.CodeRelocation(1,"rel32",target,name),)))

    code = a.finish()
    if base_va+len(code) > 0x80000000 or base_va <= admission_va < base_va+len(code):
        raise ValueError("field code allocation wraps or aliases external admission")
    contract = dict(revision="framed_battle_field_v1", source_sha256=metadata["source_sha256"]|sources,
        prerequisite_stage=metadata["stage"], admission_va=admission_va,
        native_spans={n:dict(start=lo,end=hi,sha256=h) for n,(lo,hi,h) in NATIVE_SPANS.items()},
        full_native_calls=FULL_CALLS, incremental_native_calls=INCREMENTAL_CALLS,
        clone_instruction_edits=clone_edits, native_direction_flag_clear=True,
        full_hidden_arguments=["right_exclusive","right_inclusive","visible_columns"],
        maximum_visible_columns=layout.visible_columns, rows=7, field_origin=[32,16],
        writes_world_dimensions=False, writes_scroll=False, scales_sprites=False,
        integration_required=integration_required(), installed=False, runtime_executed=False,
        pixels_verified=False, input_proof=False, promotion_ready=False)
    result_bundle = BattleFieldBundle(base_va,code,entries,tuple(a.relocations),width,height,
        hook_sites=tuple(hooks),candidate_sha256=sha(candidate),source_contract=contract)
    clip.absolute_relocation_offsets(result_bundle)
    verify_sources()
    return result_bundle
