"""Uninstalled native portrait hit testing and selected-army map admission.

Only the six-byte coordinate-entry JMP and the later five-byte mouse CALL
are described. Native right-click information, left-click selection, hover,
deselection and army switching remain native. No mouse/global/game data is
written. This module creates no candidate and supplies no runtime/input proof.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from pathlib import Path
import struct

from . import framed_input as frozen_input
from . import partial_tile_clip as clip
from . import pe_extension as pe
from .framed_army_viewport import FramedArmyViewport

ROOT = Path(__file__).resolve().parents[2]
BUILDER_SHA256 = "c2da86edc7fb6bc0e7c3ca5ecca6bf4688a33ffa8d574153dab463c4653da4fb"
INPUT_SHA256 = "a2557f1ca7caf23a957a21bf747ac23d875b27e7706de26d463b98ae221ce810"
SELECTED, PRIOR, UNIT = 0x511B58, 0x514194, 0x526FA0
COUNT = 0x422B80
NATIVE_SPANS = (
    (0x423860, 593, "55d007f9abafde52ccbd9cfbcfee64957d819dd7cae1b61bd39d6728a63223be"),
    (0x423AC0, 52, "618769ebb3052673d8cc3169d65eb1a7965bbb51b6a201f3317a9e7660e6d5ef"),
    (0x423B00, 176, "6fe0a2399c46517e54966a8776133249006a3645725ba04adae2bb31e479e104"),
    (0x40A500, 247, "3bb51bbac88db96be6bc62be58d2f9307973cb28cc055ef1cb10fb5618adcc83"),
    (COUNT, 27, "cdc5d1347c3b91a8a1cfa580d29cdcd70a4278dff15f0a2ab27ead01833527f8"),
)
HOOKS = ((0x423875, "8b15fc4c5400", "portrait_hit", 0xE9),
         (0x423984, "e867cf0300", "guarded_map_click", 0xE8))


@dataclass(frozen=True)
class ArmyInputBundle(clip.AdapterBundle):
    hook_sites: tuple[pe.HookPatch, ...] = ()
    removed_highlow_vas: tuple[int, ...] = ()
    candidate_sha256: str = ""
    state_va: int = 0
    source_contract: dict = field(default_factory=dict)


def emit_army_input(original: bytes, candidate: bytes, *, base_va: int,
                    width: int, height: int, minimap_viewport: bool) -> ArmyInputBundle:
    """Return preserving boolean/slot entries and two inseparable hook records.

    owner_state returns1 only for an own interactive selected multi-squad army
    (players0..3, INFO1..4 types0..34), exact prior/index/unit identity, ordinary
    map owner/lower1/post0 and inactive fault-free canonical modal state. It
    does not inspect the render surface/vtable, so an already-authenticated
    clipped composition guard may call it. selected_context adds the frozen
    physical surface, callback and independent minimap-player checks.

    portrait_slot returns1..10 for the relocated native hit row, zero outside;
    native code retains the empty-slot check. guarded_map_click calls the
    native4608F0 predicate FIRST with the original EAX argument, then applies
    the full framed world/minimap/command and complete army-backing exclusion.
    These four callable entries preserve every other GPR, ESP and EFLAGS.

    portrait_hit is a JMP trampoline at the native body stack depth (64 bytes
    below function entry). Valid hits set native ESI=slot and EDI=0; misses set
    EDI=0 and continue the independently gated map path. Invalid selected
    context returns through the native epilogue with EDI=0. No global mouse
    translation is used. Temporary preview armies and foreign/resource-absent
    player4 panels are outside this deliberately bounded own-army lane.

    Install BOTH records together in a separate validation stage, removing
    precisely HIGHLOW RVA23877 displaced by the coordinate JMP. Ordinary map
    guards/composition must separately admit and exclude this same panel; this
    helper alone does not provide complete installation or manual proof.
    """
    if type(original) is not bytes or type(candidate) is not bytes:
        raise ValueError("immutable original/candidate bytes required")
    clip.verify_original(original)
    layout = FramedArmyViewport(width, height)
    if type(minimap_viewport) is not bool:
        raise ValueError("explicit minimap profile boolean required")
    sources = {"tools/build_framed_modal_candidate.py": BUILDER_SHA256,
               "src/patcher/framed_input.py": INPUT_SHA256}
    def pin_sources():
        if any(hashlib.sha256((ROOT / path).read_bytes()).hexdigest() != digest
               for path, digest in sources.items()):
            raise ValueError("frozen army input prerequisite source differs")
    pin_sources()
    from tools import build_framed_modal_candidate as builder
    rebuilt, metadata, _ = builder.build_candidate(
        original, f"{width}x{height}", minimap_viewport=minimap_viewport)
    if candidate != rebuilt:
        raise ValueError("whole prerequisite candidate reconstruction differs")
    for va, size, expected in NATIVE_SPANS:
        for image in (original, candidate):
            pos = clip.file_offset(image, va, size)
            if hashlib.sha256(image[pos:pos + size]).hexdigest() != expected:
                raise ValueError(f"native army input contract differs at {va:08x}")
    state_va = metadata["state_va"]
    # Reuse frozen input semantics privately; no old CALL/scalar records are
    # installed. Change only its explicitly named lower-owner immediate.
    base = frozen_input.emit_input_bundle(original, base_va=base_va, width=width, height=height)
    code = bytearray(base.code)
    lower = [r for r in base.relocations if r.purpose == "lower_row_owner"]
    if len(lower) != 1:
        raise ValueError("frozen lower owner field inventory differs")
    at = lower[0].offset
    if code[at - 2:at] != bytes.fromhex("813d") or code[at + 4:at + 8] != bytes(4):
        raise ValueError("frozen lower owner comparison differs")
    struct.pack_into("<I", code, at + 4, 1)
    a = clip._Assembler(base_va)
    a.code.extend(code); a.relocations.extend(base.relocations)
    a.labels.update({"private." + name: value - base_va for name, value in base.entries.items()})

    def glob(address, purpose): a.absolute(address, purpose)
    def transfer(target, purpose, opcode="e8"):
        a.emit(opcode); at = len(a.code)
        a.relocations.append(clip.Relocation(at, "rel32", target, purpose))
        a.u32(target - base_va - at - 4)
    def result(value):
        a.emit("c744241c"); a.u32(value); a.emit("619dc3")
    def reject(opcode="0f85"): a.branch(opcode, "owner.deny")

    a.label("owner_state"); a.emit("9c60")
    for address, purpose, value in ((clip.RENDER_HOOK_GLOBAL, "render_hook", 0x40AD40),
                                  (clip.LOWER_ROW_OWNER_GLOBAL, "lower_row_owner", 1),
                                  (clip.POST_TILE_CALLBACK_GLOBAL, "post_tile_callback", 0)):
        a.emit("813d"); glob(address, purpose)
        if purpose == "render_hook": glob(value, "ordinary_map_owner")
        else: a.u32(value)
        reject()
    for offset in (0, 8, 36, 52, 56):
        a.emit("833d"); glob(state_va + offset, "army_modal_state." + str(offset)); a.emit("00"); reject()
    a.emit("8b35"); glob(clip.GAME_DATA_GLOBAL, "game_data_global")
    a.emit("81fe00000100"); reject("0f82")
    a.emit("81fe0000f07f"); reject("0f87")
    a.emit("a1"); glob(SELECTED, "army_selected")
    a.emit("3df3010000"); reject("0f87")
    a.emit("3b05"); glob(PRIOR, "army_prior"); reject()
    a.emit("69c0d502000005e63e020001f0"); reject("0f82")
    a.emit("3b05"); glob(UNIT, "army_unit"); reject()
    a.emit("89c58b1d"); glob(clip.CURRENT_PLAYER_GLOBAL, "current_player")
    a.emit("83fb03"); reject("0f87")
    a.emit("0fb6450439d8"); reject()
    a.emit("69c38f05000083bc061323020000"); reject("0f84")
    # No world pointer is formed; only the native signed unit coordinates.
    for unit_offset, map_offset in ((0, 0x222E0), (2, 0x222E4)):
        a.emit("8b86"); a.u32(map_offset)
        a.emit("83f801"); reject("0f8c")
        a.emit("83f864"); reject("0f8f")
        a.emit("0fbf55"); a.emit(f"{unit_offset:02x}")
        a.emit("85d2"); reject("0f8c")
        a.emit("39c2"); reject("0f8d")
    a.emit("89e8"); transfer(COUNT, "native_squad_count")
    a.emit("83f802"); reject("0f8c")
    a.emit("83f80a"); reject("0f8f")
    a.emit("89c331c9")  # EBX=count, ECX=slot.
    a.label("owner.squad")
    a.emit("6bc11f0fbf44050683f822"); reject("0f87")
    a.emit("4139d9"); a.branch("0f8c", "owner.squad")
    result(1)
    a.label("owner.deny"); result(0)

    a.label("selected_context"); a.emit("9c60")
    a.branch("e8", "owner_state"); a.emit("85c0"); a.branch("0f84", "selected.deny")
    a.branch("e8", "private.context_guard"); a.emit("85c0"); a.branch("0f84", "selected.deny")
    result(1)
    a.label("selected.deny"); result(0)

    def mouse():
        a.emit("0fb60d"); glob(frozen_input.MOUSE_SHIFT, "mouse_shift")
        a.emit("8b1d"); glob(frozen_input.MOUSE_X, "mouse_x")
        a.emit("8b15"); glob(frozen_input.MOUSE_Y, "mouse_y")
        a.emit("d3fbd3fa")
    a.label("portrait_slot"); a.emit("9c60")
    a.branch("e8", "selected_context"); a.emit("85c0"); a.branch("0f84", "slot.deny")
    mouse()
    for opcode, value, branch in (("81fb", layout.hit.left, "0f8c"), ("81fb", layout.hit.right, "0f8f"),
                                  ("81fa", layout.hit.top, "0f8c"), ("81fa", layout.hit.bottom, "0f8f")):
        a.emit(opcode); a.u32(value); a.branch(branch, "slot.deny")
    a.emit("89d883e82631d2b926000000f7f1408944241c619dc3")
    a.label("slot.deny"); result(0)

    a.label("guarded_map_click"); a.emit("9c60")
    a.branch("e8", "private.click_gate"); a.emit("85c0"); a.branch("0f84", "map.deny")
    a.branch("e8", "owner_state"); a.emit("85c0"); a.branch("0f84", "map.deny")
    mouse()
    for opcode, value, branch in (("81fb", layout.backing.left, "0f8c"), ("81fb", layout.backing.right, "0f8f"),
                                  ("81fa", layout.backing.top, "0f8c"), ("81fa", layout.backing.bottom, "0f8f")):
        a.emit(opcode); a.u32(value); a.branch(branch, "map.allow")
    a.branch("e9", "map.deny")
    a.label("map.allow"); result(1)
    a.label("map.deny"); result(0)

    a.label("portrait_hit"); a.emit("9c60")
    a.branch("e8", "selected_context"); a.emit("85c0"); a.branch("0f84", "hit.invalid")
    a.branch("e8", "portrait_slot"); a.emit("85c0"); a.branch("0f84", "hit.miss")
    a.emit("4889442404c7042400000000619d")
    transfer(0x4238CA, "native_portrait_hit", "e9")
    a.label("hit.miss"); a.emit("c7042400000000619d")
    transfer(0x42397F, "native_portrait_miss", "e9")
    a.label("hit.invalid"); a.emit("c7042400000000619d")
    transfer(0x423A8D, "native_portrait_invalid", "e9")
    code = a.finish()
    if base_va + len(code) > 0x80000000:
        raise ValueError("army helper exceeds supported x86 allocation")
    entries = {name: base_va + pos for name, pos in a.labels.items()}
    hooks = []
    for va, old_hex, entry, opcode in HOOKS:
        old = bytes.fromhex(old_hex); pos = clip.file_offset(candidate, va, len(old))
        if candidate[pos:pos + len(old)] != old:
            raise ValueError("army hook old bytes differ")
        fields = clip._original_highlow_fields(original, va, len(old))
        if fields != ({2} if va == 0x423875 else set()):
            raise ValueError("army hook HIGHLOW inventory differs")
        target = entries[entry]
        new = bytes((opcode,)) + struct.pack("<i", target - va - 5) + b"\x90" * (len(old) - 5)
        hooks.append(pe.HookPatch(pos, va - 0x400000, va, old, new, entry,
                                 (pe.CodeRelocation(1, "rel32", target, entry),)))
    pin_sources()
    bundle = ArmyInputBundle(base_va, code, entries, tuple(a.relocations), width, height,
        hook_sites=tuple(hooks), removed_highlow_vas=(0x423877,),
        candidate_sha256=hashlib.sha256(candidate).hexdigest(), state_va=state_va,
        source_contract=dict(sources=sources, whole_candidate_reconstructed=True,
                             original_sha256=clip.ORIGINAL_SHA256, native_spans=NATIVE_SPANS,
                             backing=layout.backing.as_tuple(), hit=layout.hit.as_tuple(),
                             native_mouse_untouched=True, installation_ready=False))
    clip.absolute_relocation_offsets(bundle)
    return bundle
