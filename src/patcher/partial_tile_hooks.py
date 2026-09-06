"""Offline hook trampolines appended to the guarded partial-tile code bundle.

No executable is written or installed. HookSite records describe the displaced
instructions and original HIGHLOW fields an eventual installer must replace.
After-call status VAs expose EAX to a future probe before original state is
restored. Unsupported owners use native fallback; that is not HD render proof.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib

from . import partial_tile_clip as clip
from . import patch_clash95_hd as patcher
from .framed_viewport import FramedViewport


COMBINED_STAGE = (
    "gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-"
    "presentbounds-minimapright-dynvswitch-combinedui-validation"
)
IMAGE_BASE = 0x400000
CURSOR_X_GLOBAL = 0x544CFC
# Audited complete native sub_418700 through its final RET/alignment. At the
# hook sites native var_30 == [ESP] is unused. The only native write to that
# slot is 004188E2 (four arguments have moved ESP by -16); its reads at
# 004188F0/004188FE follow that write. Earlier [ESP+10h] at 004187CC is a
# different local. The exact function plus canonical frame cave bind this
# lifetime, including branch targets; this is not a guessed global scratch.
FULL_REDRAW_ORIGINAL_SHA256 = "0bc270a6f9131268c61dad8b65ff8ea04a43fd44371c63b21a4e06ea9b9d5e5c"
FULL_STATUS_SAVED_FRAME_OFFSET = 36  # Native [ESP] below PUSHFD + PUSHAD.
SITES = (
    ("full_converge", 0x4187A0, bytes.fromhex("833d9069520000"), 0x4187A7, (0x4187A2,)),
    ("full_present", 0x4187B7, bytes.fromhex("a1fc4c5400"), 0x4187BC, (0x4187B8,)),
    ("incremental", 0x418A90, bytes.fromhex("535156575583ec08"), 0x418A98, ()),
)
NATIVE_SURROUNDINGS = {
    0x4187A7: bytes.fromhex("7406ff1590695200"),
    0x4187AF: bytes.fromhex("85ed0f84ec010000"),
    0x4187BC: bytes.fromhex("8a0d2c515400d3f88b15144d5400"),
    0x4189A3: bytes.fromhex("83c4185d5f5e5a595bc3"),
    0x418A98: bytes.fromhex("8b35e40252008b8ee8220200"),
    0x418AFA: bytes.fromhex("83c4085d5f5e595bc3"),
}


@dataclass(frozen=True)
class HookSite:
    name: str
    offset: int
    va: int
    old_bytes: bytes
    entry_va: int
    fallback_va: int
    removed_highlow_vas: tuple[int, ...]

    @property
    def rva(self) -> int:
        return self.va - IMAGE_BASE


@dataclass(frozen=True)
class HookBundle(clip.AdapterBundle):
    hook_sites: tuple[HookSite, ...] = ()
    status_vas: dict[str, int] = field(default_factory=dict)
    candidate_sha256: str = ""
    layout_contract: dict = field(default_factory=dict)


def _verify_contract(original: bytes, candidate: bytes, width: int, height: int,
                     layout: FramedViewport | None = None) -> None:
    clip.verify_original(original)
    off = clip.file_offset(original, 0x418700, 0x390)
    if hashlib.sha256(original[off:off + 0x390]).hexdigest() != FULL_REDRAW_ORIGINAL_SHA256:
        raise ValueError("native full-redraw local lifetime differs")
    profile = patcher.parse_resolution(f"{width}x{height}")
    if layout is None:
        recipe = patcher.select_patches_for(COMBINED_STAGE, profile)
    else:
        from .framed_recipe import select_patches_for
        clip._terrain_end(width, height, layout)
        recipe = select_patches_for(profile)
    for patch in recipe:
        if original[patch.offset:patch.offset + len(patch.old)] != patch.old:
            raise ValueError("combined recipe old bytes differ from known original")
    if patcher.apply_patches(original, recipe) != candidate:
        raise ValueError("candidate is not the exact combined validation recipe")
    for va, expected in NATIVE_SURROUNDINGS.items():
        off = clip.file_offset(original, va, len(expected))
        if original[off:off + len(expected)] != expected:
            raise ValueError(f"native surrounding instructions differ at 0x{va:08X}")
        # The existing frame-restoration trampoline replaces only this gate.
        # Exact candidate reconstruction above authenticates its complete
        # width-specific cave, present-flag branch and return to 004187B7.
        if va != 0x4187AF:
            off = clip.file_offset(candidate, va, len(expected))
            if candidate[off:off + len(expected)] != expected:
                raise ValueError(f"candidate continuation differs at 0x{va:08X}")
    for _, va, expected, _, removed in SITES:
        for data in (original, candidate):
            off = clip.file_offset(data, va, len(expected))
            if data[off:off + len(expected)] != expected:
                raise ValueError(f"hook old bytes differ at 0x{va:08X}")
        fields = clip._original_highlow_fields(original, va, len(expected))
        if {va + pos for pos in fields} != set(removed):
            raise ValueError("displaced native HIGHLOW inventory differs")


def emit_hook_bundle(original: bytes, candidate: bytes, *, base_va: int,
                     width: int, height: int, layout: FramedViewport | None = None) -> HookBundle:
    """Return guarded renderer plus three uninstalled native-ABI trampolines.

    Full convergence is reached after terrain and before the native owner
    callback. Full presentation is reached only after the existing frame hook
    and its EBP present gate. Incremental entry receives world X in EAX and Y
    in EDX. All calls save flags/GPR; fallback replays displaced instructions.
    Full convergence stores its exact status in the per-invocation native
    var_30 stack slot; full presentation requires that status to be exactly 1.
    Native fallback initializes that local before its original reads. There
    is no global latch, and nested redraw calls have separate native frames.
    The incremental helper's 1/2 mean drawn/cleared; only these statuses return
    directly. Full presentation requires exactly 1 before skipping its native
    presentation path. Full convergence always continues through native CMP.
    """
    _verify_contract(original, candidate, width, height, layout)
    bundle = clip.emit_map_composition(original, candidate, base_va=base_va,
                                       width=width, height=height, layout=layout)
    a = clip._Assembler(base_va)
    a.code.extend(bundle.code)
    a.relocations.extend(bundle.relocations)
    status_vas: dict[str, int] = {}

    def transfer(opcode: str, target: int, purpose: str) -> None:
        a.emit(opcode)
        pos = len(a.code)
        a.relocations.append(clip.Relocation(pos, "rel32", target, purpose))
        a.u32(target - (base_va + pos + 4))

    def start(name: str) -> None:
        a.label("hook_" + name)
        a.emit("9c60")  # PUSHFD/PUSHAD; caller flags below the GPR frame.

    def call(name: str, helper: str) -> None:
        transfer("e8", bundle.entries[helper], "hook_helper_" + helper)
        a.label("hook_" + name + "_status")
        status_vas[name] = base_va + len(a.code)

    start("full_converge")
    if layout is not None:
        # Native full tiles used the scoped clipped vtable. Return to the
        # authenticated memory table before drawing frame/overlay owners.
        # The outer full-entry wrapper restores its exact saved table on RET.
        a.emit("a1");a.absolute(clip.MAP_SURFACE_GLOBAL,"map_surface_global")
        a.emit("85c0");a.branch("0f84","full_converge.table_done")
        a.emit("81b8b8000000");a.absolute(bundle.entries["clipped_vtable"],"clipped_vtable")
        a.branch("0f85","full_converge.table_done")
        a.emit("c780b8000000");a.absolute(clip.MEMORY_VTABLE,"memory_vtable")
        a.label("full_converge.table_done")
    a.emit("31c0")  # Render partial edges offscreen; retain native owner tail.
    call("full_converge", "edge_full_composed")
    a.emit("894424" + bytes([FULL_STATUS_SAVED_FRAME_OFFSET]).hex())
    a.emit("619d833d")
    a.absolute(clip.POST_TILE_CALLBACK_GLOBAL, "hook_post_tile_callback")
    a.emit("00")
    transfer("e9", 0x4187A7, "hook_resume_full_converge")

    start("full_present")
    a.emit("837c24" + bytes([FULL_STATUS_SAVED_FRAME_OFFSET]).hex() + "01")
    a.branch("0f85", "hook_full_present_reject")
    a.emit("b8");a.u32(32 if layout is None else 0)
    a.emit("bb");a.u32(16 if layout is None else 0)
    a.emit("b9"); a.u32(width - 1)
    a.emit("ba"); a.u32(height - 1)
    call("full_present", "present_map_rect")
    a.emit("83f801")
    a.branch("0f85", "hook_full_present_reject")
    a.emit("619d")
    transfer("e9", 0x4189A3, "hook_native_full_epilogue")
    a.label("hook_full_present_reject")
    a.emit("619da1")
    a.absolute(CURSOR_X_GLOBAL, "hook_cursor_x")
    transfer("e9", 0x4187BC, "hook_resume_full_present")

    start("incremental")
    call("incremental", "cell_incremental_composed")
    a.emit("83f801")
    a.branch("0f84", "hook_incremental_handled")
    a.emit("83f802")
    a.branch("0f85", "hook_incremental_reject")
    a.label("hook_incremental_handled")
    a.emit("619dc3")
    a.label("hook_incremental_reject")
    a.emit("619d" + SITES[2][2].hex())
    transfer("e9", 0x418A98, "hook_resume_incremental")

    entries = dict(bundle.entries)
    entries.update({name: base_va + pos for name, pos in a.labels.items()})
    sites = tuple(HookSite(name, clip.file_offset(candidate, va, len(old)), va, old,
                           entries["hook_" + name], fallback, removed)
                  for name, va, old, fallback, removed in SITES)
    result = HookBundle(base_va, a.finish(), entries, tuple(a.relocations), width, height,
                        False, sites, status_vas, hashlib.sha256(candidate).hexdigest())
    if layout is not None:
        from .framed_full_paint import append_full_entry
        result = append_full_entry(original, candidate, result, layout=layout)
    clip.absolute_relocation_offsets(result)
    return result
