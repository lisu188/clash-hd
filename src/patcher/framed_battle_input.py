"""Uninstalled tactical physical-input, pan and horizontal-centering hooks.

Only authenticated byte recipes are emitted. No candidate is written. Native
seven-row combat state, 64px artwork and occupancy storage remain unchanged.
The external admission helper must establish owner/thread/lifetime and isolated
HUD routing; these hooks alone are not a complete tactical-HD stage.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from pathlib import Path
import struct

from . import partial_tile_clip as clip
from . import pe_extension as pe
from . import framed_battle_coordinates as coordinates
from .framed_battle_viewport import TacticalViewport

ROOT = Path(__file__).resolve().parents[2]
PINNED_SOURCES = {
    "tools/build_framed_army_candidate.py": "4060856f60ab8589f9dbc0ae73df142cf906e4905f3c24aaa6c8292a161bc167",
    "src/patcher/framed_battle_coordinates.py": "47c017a412ec12378785c400fa505baed3ae0825a58e5b1fefad00c67de4260c",
    "src/patcher/framed_battle_viewport.py": "8673e36bd04ded2afc8cc3b9d7ff2fed4c48dae891fe289509b44a9070c23bc6",
}
NATIVE_SPANS = {
    "pan": (0x42C840, 0x42CB4D, "697a9d59eb059ba92a58f475f8286b566f8d4cd7548103e196992f01528bdf61"),
    "hit_prefix": (0x42CB50, 0x42CBC2, "f8e67951754ef1b87d8fc6c4729ba245410c419d4fca96eeb48f818943a9c2f3"),
    "unit_center": (0x426E20, 0x426EE5, "cbdf39ccced6a334e6f9c7473cb22b35e611606488149cbdad38f7647577cd95"),
    "shot_center": (0x429146, 0x429212, "1a489c6d05047a0c3b0348bcc2a3412bd95fbf6cb82e156f51ef5e2cd8521b69"),
    "restore": (0x42E43F, 0x42E487, "0afc58eb9173d19246a5868302023cc44393ec91e9d2c8fdf2363ae0380ebeaf"),
    "restore_epilogue": (0x42E554, 0x42E563, "7c2618e00198ace6cde01a966fc8e30c2e4730435cfb96b547c291e8a6a2079c"),
}
HOOKS = {
    "pan_pixel": (0x42C870, "8b15fc4c5400", (2,)),
    "hit_pixel": (0x42CB58, "8b15fc4c5400", (2,)),
    "key_right": (0x42C942, "83c20739da", ()),
    "drag": (0x42CA2F, "8b15fc4c5400", (2,)),
    "unit_center": (0x426E40, "83ea03899128030000", ()),
    "unit_limit": (0x426E65, "a148205300", (1,)),
    "shot_center": (0x429163, "83e803898228030000", ()),
    "shot_limit": (0x429192, "a148205300", (1,)),
    "restore": (0x42E444, "a148205300", (1,)),
}
GLOBALS = {0x532048: "battle_state_global", 0x5199D8: "battle_render_owner",
           0x42E8B0: "native_battle_owner", 0x544CFC: "mouse_raw_x",
           0x544D00: "mouse_raw_y", 0x54512C: "mouse_shift",
           0x5202EC: "current_player_global"}


@dataclass(frozen=True)
class BattleInputBundle(clip.AdapterBundle):
    hook_sites: tuple = ()
    removed_highlow_rvas: tuple = ()
    candidate_sha256: str = ""
    source_contract: dict = field(default_factory=dict)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def verify_sources():
    for name, expected in PINNED_SOURCES.items():
        if sha((ROOT/name).read_bytes()) != expected:
            raise ValueError("reviewed battle input source differs: " + name)
    return dict(PINNED_SOURCES)


def emit_battle_input(original: bytes, candidate: bytes, *, base_va: int,
                      width: int, height: int, admission_va: int,
                      minimap_viewport: bool = True) -> BattleInputBundle:
    """Emit nine hooks and three public helpers, never install them.

    admission_va preserves all non-EAX registers and flags, returns exactly1
    only for owned, readable, ordinary battle state and isolated wide HUD.
    A non1 admission retains the displaced native path, without HD acceptance.
    Numeric checks cannot prove pointer mapping, ownership or lifetime.

    clamp_requested_x: EAX=live state, EDX=signed request -> EAX clamped X or
    FFFFFFFF. center_requested_x: same, EDX=world X -> centered/clamped X.
    Both allow transient saved/centering Y and invalid stored X: they only
    compute, never write. Native rows/columns must still be7 and1..20. The
    caller must normalize Y to0 before any field draw/index. These helpers
    preserve all non-EAX GPRs/ESP/EFLAGS. mouse_cell returns packed world X/Y
    or FFFFFFFF and requires both stored scroll axes valid.

    Hooks preserve all registers except documented native intermediate values.
    Pixel rejection takes native epilogues BEFORE occupancy access. Right-key
    replays CMP flags with V instead of7. Selected/shot Y calculation/clamps
    remain native. Their obsolete X-clamp blocks are bypassed only after the
    new centered X is stored; all nine hooks must be installed atomically.
    Drag uses the native signed truncating /8 sensitivity within physical
    client X bounds, stores clamped X/Y0, then reaches native redraw/pump.
    Saved-view restore checks player0..4 BEFORE indexing and normalizes both
    axes before redraw; invalid player takes the native turn-return epilogue.
    """
    layout = TacticalViewport(width, height, 20)
    if any(type(x) is not int or not 0x10000 <= x <= 0x7FFF0000 for x in (base_va, admission_va)):
        raise ValueError("explicit x86 code and admission addresses required")
    if type(original) is not bytes or type(candidate) is not bytes or type(minimap_viewport) is not bool:
        raise ValueError("immutable images and explicit minimap selection required")
    clip.verify_original(original)
    sources = verify_sources()
    from tools import build_framed_army_candidate as builder
    from tools import build_framed_modal_candidate as modal_builder
    expected, metadata, _ = builder.build_candidate(original, f"{width}x{height}", minimap_viewport=minimap_viewport)
    if candidate != expected:
        raise ValueError("whole current army candidate reconstruction required")
    image = pe.inspect_pe(candidate)
    def read(data, va, count):
        offset = clip.file_offset(data, va, count)
        return data[offset:offset+count]
    for name, (lo, hi, digest) in NATIVE_SPANS.items():
        if any(sha(read(data, lo, hi-lo)) != digest for data in (original, candidate)):
            raise ValueError("native tactical input span changed: " + name)
    modal = modal_builder.build_candidate(original, f"{width}x{height}", minimap_viewport=minimap_viewport)[0]
    coord = coordinates.emit_battle_coordinates(original, modal, base_va=base_va,
        width=width, height=height, minimap_viewport=minimap_viewport)
    a = clip._Assembler(base_va)
    a.code.extend(coord.code); a.relocations.extend(coord.relocations)
    entries = {"coordinates."+k: v for k,v in coord.entries.items()}

    def absolute(target):
        a.absolute(target, GLOBALS[target])
    def transfer(opcode, target, purpose):
        a.emit(opcode); offset=len(a.code)
        a.relocations.append(clip.Relocation(offset,"rel32",target,purpose))
        a.u32(target-(base_va+offset+4))
    def start(name):
        a.label(name); entries[name]=base_va+len(a.code); a.emit("9c60fc")
    def admission(name):
        transfer("e8",admission_va,"required_battle_admission")
        a.emit("83f801"); a.branch("0f85",name+".native")
    def jump(va, purpose):
        a.emit("619d"); transfer("e9",va,purpose)
    def saved(offset):
        a.emit("894424"+bytes([offset]).hex())
    def result(name):
        a.branch("e9",name+".return")
        a.label(name+".reject"); a.emit("b8ffffffff")
        a.label(name+".return"); saved(28); a.emit("619dc3")

    # Arithmetic helpers intentionally ignore transient native Y. No state
    # dereference precedes admission or identity/alignment/extent checks.
    for name in ("clamp_requested_x","center_requested_x"):
        start(name)
        transfer("e8",admission_va,"required_battle_admission")
        a.emit("83f801"); a.branch("0f85",name+".reject")
        a.emit("8b74241c85f6"); a.branch("0f84",name+".reject")
        a.emit("3b35"); absolute(0x532048); a.branch("0f85",name+".reject")
        a.emit("81fe00000100"); a.branch("0f82",name+".reject")
        a.emit("81fed0fcff7f"); a.branch("0f87",name+".reject")
        a.emit("f7c603000000"); a.branch("0f85",name+".reject")
        a.emit("813d"); absolute(0x5199D8); absolute(0x42E8B0); a.branch("0f85",name+".reject")
        a.emit("83be2003000007"); a.branch("0f85",name+".reject")
        a.emit("8b9e2403000083fb01"); a.branch("0f8c",name+".reject")
        a.emit("83fb14"); a.branch("0f8f",name+".reject")
        a.emit("bf"); a.u32((width-192)//64)
        a.emit("39fb"); a.branch("0f8d",name+".capacity")
        a.emit("89df"); a.label(name+".capacity")
        a.emit("8b442414")
        if name == "center_requested_x":
            a.emit("85c0"); a.branch("0f8c",name+".reject")
            a.emit("39d8"); a.branch("0f8d",name+".reject")
            a.emit("89fac1ea0129d0")  # center uses floor(V/2).
        a.emit("29fb85c0"); a.branch("0f89",name+".positive")
        a.emit("31c0"); a.branch("e9",name+".return")
        a.label(name+".positive"); a.emit("39d8"); a.branch("0f8e",name+".return")
        a.emit("89d8"); result(name)

    start("mouse_cell")
    transfer("e8",admission_va,"required_battle_admission")
    a.emit("83f801"); a.branch("0f85","mouse_cell.reject")
    a.emit("0fb60d"); absolute(0x54512C)
    a.emit("83f91f"); a.branch("0f87","mouse_cell.reject")
    a.emit("8b15"); absolute(0x544CFC); a.emit("d3fa")
    a.emit("a1"); absolute(0x544D00); a.emit("d3f889c1a1"); absolute(0x532048)
    transfer("e8",coord.entries["screen_to_cell"],"battle_screen_to_cell")
    result("mouse_cell")

    for name, destination, rejected in (("pan_pixel",0x42C8BC,0x42C8DF),("hit_pixel",0x42CBC1,0x42CBB8)):
        start(name); admission(name)
        a.branch("e8","mouse_cell"); a.emit("83f8ff"); a.branch("0f84",name+".outside")
        a.emit("89c10fb7c0")
        if name == "pan_pixel":
            saved(16); a.emit("c1e91089c8"); saved(4)
        else:
            saved(4); a.emit("89c28b35"); absolute(0x532048)
            a.emit("2b962803000089d0"); saved(8)  # EBP viewport column.
            a.emit("c1e91089c8"); saved(28)
            # EDI world row; EAX native row, both zero-origin seven-row.
            saved(0)
        a.emit("a1"); absolute(0x532048); saved(20)
        jump(destination,"native_"+name+"_admitted")
        a.label(name+".outside"); jump(rejected,"native_"+name+"_reject")

    start("key_right"); admission("key_right")
    a.emit("a1"); absolute(0x532048)
    transfer("e8",coord.entries["visible_columns"],"battle_visible_columns")
    a.emit("83f8ff"); a.branch("0f84","key_right.native")
    a.emit("03442414"); saved(20)
    a.emit("619d39da")  # EDX=old scroll+V; native CMP EDX,EBX flags.
    transfer("e9",0x42C947,"native_key_right_compare")

    start("drag"); admission("drag")
    a.emit("0fb60d"); absolute(0x54512C)
    a.emit("83f91f"); a.branch("0f87","drag.outside")
    a.emit("a1"); absolute(0x544CFC); a.emit("d3f885c0"); a.branch("0f8c","drag.outside")
    a.emit("3d"); a.u32(width); a.branch("0f8d","drag.outside")
    a.emit("8b74240485f6"); a.branch("0f8c","drag.outside")
    a.emit("81fe"); a.u32(width); a.branch("0f8d","drag.outside")
    a.emit("29f089c2c1fa1f83e20701d0c1f80389c2a1"); absolute(0x532048)
    a.emit("039028030000"); a.branch("0f80","drag.outside")
    a.branch("e8","clamp_requested_x"); a.emit("83f8ff"); a.branch("0f84","drag.outside")
    a.emit("8b15"); absolute(0x532048)
    a.emit("898228030000c7822c03000000000000")
    jump(0x42CAE0,"native_drag_redraw")
    a.label("drag.outside"); jump(0x42CB37,"native_drag_exit")

    for name, destination in (("unit_center",0x426E49),("shot_center",0x42916C)):
        start(name); admission(name)
        a.emit("8b5424"+("14" if name=="unit_center" else "1c"))
        a.emit("a1"); absolute(0x532048)
        a.branch("e8","center_requested_x"); a.emit("83f8ff"); a.branch("0f84",name+".native")
        a.emit("8b15"); absolute(0x532048); a.emit("898228030000")
        saved(20 if name=="unit_center" else 28)
        jump(destination,"native_"+name+"_y")
    for name, destination in (("unit_limit",0x426E8B),("shot_limit",0x4291C1)):
        start(name); admission(name)
        a.emit("a1"); absolute(0x532048); a.emit("8b9028030000")
        a.branch("e8","clamp_requested_x")
        a.emit("83f8ff"); a.branch("0f84",name+".native")
        a.emit("39d0"); a.branch("0f85",name+".native")
        a.emit("a1"); absolute(0x532048); saved(28)
        jump(destination,"native_"+name+"_y_clamp")

    start("restore"); admission("restore")
    a.emit("8b0d"); absolute(0x5202EC)
    a.emit("83f900"); a.branch("0f8c","restore.reject")
    a.emit("83f904"); a.branch("0f8f","restore.reject")
    a.emit("a1"); absolute(0x532048)
    # Prove state before the saved-player array read. The external admission
    # also owns its larger readable lifetime through0xF68 (beyond816bytes).
    a.emit("31d2"); a.branch("e8","clamp_requested_x")
    a.emit("83f8ff"); a.branch("0f84","restore.reject")
    a.emit("a1"); absolute(0x532048)
    a.emit("3d98f0ff7f"); a.branch("0f87","restore.reject")
    a.emit("0fb694485e0f0000")
    a.branch("e8","clamp_requested_x"); a.emit("83f8ff"); a.branch("0f84","restore.reject")
    a.emit("8b15"); absolute(0x532048)
    a.emit("898228030000c7822c03000000000000")
    a.emit("89d0"); saved(28); a.emit("31c0"); saved(20)
    a.emit("8b44240c83c004"); saved(0)
    jump(0x42E482,"native_restore_redraw")
    # The owning lifecycle must classify this unsupported route rather than
    # treating the native turn result as a rendered/input success.
    a.label("restore.reject"); jump(0x42E554,"native_restore_reject")

    hooks=[]; removed=[]
    for name,(va,hexold,fields) in HOOKS.items():
        old=bytes.fromhex(hexold)
        if any(read(data,va,len(old)) != old for data in (original,candidate)):
            raise ValueError("displaced tactical bytes changed: "+name)
        if clip._original_highlow_fields(original,va,len(old)) != set(fields):
            raise ValueError("native hook HIGHLOW inventory differs: "+name)
        a.label(name+".native")
        a.emit("619d")
        at=len(a.code); a.code.extend(old)
        for off in fields:
            target=struct.unpack_from("<I",old,off)[0]
            a.relocations.append(clip.Relocation(at+off,"abs32",target,GLOBALS[target]))
        transfer("e9",va+len(old),"native_"+name+"_fallback")
        target=entries[name]
        new=b"\xe9"+struct.pack("<i",target-va-5)+b"\x90"*(len(old)-5)
        hooks.append(pe.HookPatch(image.file_offset(va-image.image_base,len(old)),va-image.image_base,
            va,old,new,"wide tactical "+name,(pe.CodeRelocation(1,"rel32",target,name),)))
        removed.extend(va-image.image_base+off for off in fields)
    code=a.finish()
    if base_va+len(code)>0x80000000 or base_va <= admission_va < base_va+len(code):
        raise ValueError("input allocation wraps or aliases external admission")
    contract=dict(revision="framed_battle_input_v1",source_sha256=metadata["source_sha256"]|sources,
        prerequisite_stage=metadata["stage"],admission_va=admission_va,
        maximum_visible_columns=layout.visible_columns,field_origin=[32,16],rows=7,
        saved_player_range=[0,4],saved_view_offset=0xF5E,restore_readable_state_bytes=0xF68,
        pixel_indices_checked_before_occupancy=True,center_offset="floor(visible_columns/2)",
        drag_divisor=8,native_y_clamps_preserved=True,
        native_spans={n:dict(start=lo,end=hi,sha256=digest) for n,(lo,hi,digest) in NATIVE_SPANS.items()},
        integration_required=["Install all nine hooks atomically with wide field/HUD/owner lifecycle and input routing.",
          "Normalize initial42E9E0 saved views using clamp_requested_x and Y0 only after required owner admission.",
          "External admission owns readable state, cursor and player-array lifetimes; pointer checks do not establish mapping.",
          "A rejected/legacy fallback is not a tactical-HD pass. No UI, runtime, input or promotion proof is created."],
        installed=False,runtime_executed=False,input_proof=False,promotion_ready=False)
    result_bundle=BattleInputBundle(base_va,code,entries,tuple(a.relocations),width,height,
        hook_sites=tuple(hooks),removed_highlow_rvas=tuple(sorted(removed)),
        candidate_sha256=sha(candidate),source_contract=contract)
    clip.absolute_relocation_offsets(result_bundle);verify_sources()
    return result_bundle
