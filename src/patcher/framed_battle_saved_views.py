"""Uninstalled, source-bound initial tactical camera adapters.

Both right-start camera calculations are emitted together. The native player
array writers, zero-start branches and seven-row Y calculation remain native.
These two hooks cannot be installed independently of the complete field, HUD,
input, ownership and presentation recipe. No builder or runtime is installed.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from pathlib import Path
import struct

from . import partial_tile_clip as clip
from . import pe_extension as pe
from .framed_battle_viewport import TacticalViewport

ROOT = Path(__file__).resolve().parents[2]
SOURCE = "src/patcher/framed_battle_saved_views.py"
PINNED_SOURCES = {
    "tools/build_framed_army_candidate.py": "ec5989d86d8252c43b7a73c8b2bfd612e5050434adcbeecf58dbe47bf96d1114",
    "src/patcher/framed_battle_viewport.py": "8673e36bd04ded2afc8cc3b9d7ff2fed4c48dae891fe289509b44a9070c23bc6",
}
# Continuous native instruction spans: conditional zero/right-start routes,
# both X writers, the complete Y=trunc((rows-7)/2) writers, and branch tails.
NATIVE_SPANS = {
    "initial_camera": (0x42F1EC, 0x42F275, "6a9ea30b380dcf1989dcb4e5114ca49b5a8dfd258312e81defbca0acc447aac4"),
    "right_start_tails": (0x42F5D9, 0x42F5FF, "a7f6aa1dc37f28d37293e05e02dc2703671b4515e7cdf8eebe3b2d221b009f96"),
}
# Native SUB EAX,7 followed by its complete JMP. There are no HIGHLOW fields.
SITES = {
    "attacker_right": (0x42F5E4, "83e807e90ffcffff", 0x42F1FB, 836),
    "defender_right": (0x42F5F7, "83e807e91ffcffff", 0x42F21E, 840),
}
ARITHMETIC_FLAGS = 0x8D5  # CF, PF, AF, ZF, SF, OF; preserve DF and other bits.


@dataclass(frozen=True)
class BattleSavedViewsBundle(clip.AdapterBundle):
    hook_sites: tuple = ()
    removed_highlow_rvas: tuple = ()
    candidate_sha256: str = ""
    source_contract: dict = field(default_factory=dict)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def verify_sources():
    for name, digest in PINNED_SOURCES.items():
        if sha((ROOT / name).read_bytes()) != digest:
            raise ValueError("reviewed battle saved-view source differs: " + name)
    return dict(PINNED_SOURCES) | {SOURCE: sha((ROOT / SOURCE).read_bytes())}


def _verify_source_snapshot(snapshot):
    if verify_sources() != snapshot:
        raise ValueError("saved-view sources changed during reconstruction")


def _authenticate_native(original, candidate):
    for name, (lo, hi, digest) in NATIVE_SPANS.items():
        for image in (original, candidate):
            off = clip.file_offset(image, lo, hi - lo)
            if sha(image[off:off + hi - lo]) != digest:
                raise ValueError("native saved-camera span differs: " + name)
    for name, (va, value, target, _) in SITES.items():
        old = bytes.fromhex(value)
        for image in (original, candidate):
            off = clip.file_offset(image, va, len(old))
            if image[off:off + len(old)] != old:
                raise ValueError("native saved-camera old bytes differ: " + name)
        if va + len(old) + struct.unpack_from("<i", old, 4)[0] != target:
            raise ValueError("native saved-camera continuation differs: " + name)
        if clip._original_highlow_fields(original, va, len(old)):
            raise ValueError("unexpected saved-camera HIGHLOW field: " + name)


def _emit_code(*, base_va, width, height, admission_va):
    """Emit only isolated code; public image authentication is separate."""
    layout = TacticalViewport(width, height, 20)
    if any(type(x) is not int or not 0x10000 <= x < 0x7FFF0000
           for x in (base_va, admission_va)):
        raise ValueError("explicit x86 code and admission addresses required")
    a = clip._Assembler(base_va)
    entries = {}

    def transfer(op, target, purpose):
        a.emit(op)
        off = len(a.code)
        a.relocations.append(clip.Relocation(off, "rel32", target, purpose))
        a.u32(target - (base_va + off + 4))

    for name, (_, _, continuation, player_offset) in SITES.items():
        entries[name] = base_va + len(a.code)
        a.label(name)
        a.emit("9c60fc")  # PUSHFD/PUSHAD; external admission sees DF=0.
        transfer("e8", admission_va, "required_owned_battle_admission")
        a.emit("83f801"); a.branch("0f85", name + ".native")
        a.emit("813d"); a.absolute(0x5199D8, "battle_render_owner")
        a.absolute(0x42E8B0, "native_battle_owner")
        a.branch("0f85", name + ".native")
        a.emit("8b1d"); a.absolute(0x532048, "battle_state_global")
        a.emit("81fb00000100"); a.branch("0f82", name + ".native")
        a.emit("81fb84f0ff7f"); a.branch("0f87", name + ".native")
        a.emit("f7c303000000"); a.branch("0f85", name + ".native")
        # The external gate owns mapping/lifetime through the native0xF7C
        # allocation. Numeric bounds alone cannot admit any dereference.
        a.emit("83bb2003000007"); a.branch("0f85", name + ".native")
        a.emit("83bb2c03000000"); a.branch("0f85", name + ".native")
        a.emit("8b44241c3b8324030000"); a.branch("0f85", name + ".native")
        a.emit("83f801"); a.branch("0f8c", name + ".native")
        a.emit("83f814"); a.branch("0f8f", name + ".native")
        a.emit("8b8b"); a.u32(player_offset)
        a.emit("83f900"); a.branch("0f8c", name + ".native")
        a.emit("83f904"); a.branch("0f8f", name + ".native")
        a.emit("b9"); a.u32(layout.visible_columns)
        a.emit("39c8"); a.branch("0f8d", name + ".capacity")
        a.emit("89c1"); a.label(name + ".capacity")
        # Exact SUB flags belong to the camera subtraction, rather than the
        # later stack bookkeeping. Merge only its six arithmetic flag bits.
        a.emit("29c88944241c9c5a81e2"); a.u32(ARITHMETIC_FLAGS)
        a.emit("81642420"); a.u32(~ARITHMETIC_FLAGS)
        a.emit("09542420619d")
        transfer("e9", continuation, "native_" + name + "_continuation")
        a.label(name + ".native")
        a.emit("619d83e807")  # Replays native SUB after restoring caller flags.
        transfer("e9", continuation, "native_" + name + "_fallback")
    code = a.finish()
    if (base_va + len(code) > 0x80000000 or
            base_va <= admission_va < base_va + len(code)):
        raise ValueError("saved-camera code wraps or aliases admission")
    bundle = clip.AdapterBundle(base_va, code, entries, tuple(a.relocations), width, height)
    clip.absolute_relocation_offsets(bundle)
    return bundle


def emit_battle_saved_views(original: bytes, candidate: bytes, *, base_va: int,
                            width: int, height: int, admission_va: int,
                            minimap_viewport: bool = True) -> BattleSavedViewsBundle:
    """Return two descriptors, never install or write an executable.

    Entry EAX is the native loaded arena width. Exact1 external admission must
    establish phase2 owner/thread, readable0xF7C state, physical field ownership
    and the complete HUD/input/presentation split. Admission preserves all
    non-EAX registers and flags. Only then are rows7, Y0, matching width1..20
    and this side's player0..4 checked. Admitted EAX=columns-min(columns,V).
    Rejection replays native EAX-7. Both branches preserve every other GPR,
    ESP and the exact SUB flags, including incoming DF and nonarithmetic bits.

    Native zero-start branches and player-array writes are unchanged. Invalid
    context takes native behavior, which is not HD acceptance or hardening of
    malformed native routes. No game state is written by these adapters.
    """
    sources = verify_sources()
    isolated = _emit_code(base_va=base_va, width=width, height=height, admission_va=admission_va)
    if type(original) is not bytes or type(candidate) is not bytes or type(minimap_viewport) is not bool:
        raise ValueError("immutable exact images and boolean minimap required")
    clip.verify_original(original)
    from tools import build_framed_army_candidate as builder
    expected, metadata, _ = builder.build_candidate(original, f"{width}x{height}",
                                                     minimap_viewport=minimap_viewport)
    if candidate != expected:
        raise ValueError("whole current army candidate reconstruction required")
    image = pe.inspect_pe(candidate)
    if base_va < image.image_base + image.image_size:
        raise ValueError("saved-camera code must use a new image allocation")
    _authenticate_native(original, candidate)
    hooks = []
    for name, (va, value, _, _) in SITES.items():
        old = bytes.fromhex(value)
        target = isolated.entries[name]
        new = b"\xe9" + struct.pack("<i", target - va - 5) + b"\x90" * (len(old) - 5)
        hooks.append(pe.HookPatch(image.file_offset(va - image.image_base, len(old)),
            va - image.image_base, va, old, new, "wide tactical initial " + name,
            (pe.CodeRelocation(1, "rel32", target, name),)))
    contract = dict(revision="framed_battle_saved_views_v1",
        source_sha256=metadata["source_sha256"] | sources,
        prerequisite_stage=metadata["stage"], admission_va=admission_va,
        initial_right_x="actual_columns-min(actual_columns,viewport_capacity)",
        required_owned_state_bytes=0xF7C, admitted_player_range=[0, 4],
        rows=7, native_y_zero_for_admitted_rows=True, writes_game_state=False,
        native_zero_start_and_array_writers_preserved=True,
        sub_arithmetic_flags_preserved=True, nonarithmetic_flags_preserved=True,
        native_spans={n: dict(start=lo, end=hi, sha256=digest)
                      for n, (lo, hi, digest) in NATIVE_SPANS.items()},
        integration_required=[
            "Install both initial-camera hooks with the complete field/input/HUD/lifecycle/presentation successor, never alone.",
            "The phase2 admission must authenticate ownership, thread, mapping/lifetime and the complete loaded hook/relocation inventory.",
            "Rendering, per-step animation, HUD hover/descriptor transforms, presentation and restoration remain uninstalled.",
            "A native fallback is not tactical-HD acceptance. Source/CPU evidence is not runtime, manual input or promotion proof."],
        installed=False, runtime_executed=False, input_proof=False, promotion_ready=False)
    bundle = BattleSavedViewsBundle(isolated.base_va, isolated.code, isolated.entries,
        isolated.relocations, width, height, hook_sites=tuple(hooks),
        candidate_sha256=sha(candidate), source_contract=contract)
    clip.absolute_relocation_offsets(bundle)
    _verify_source_snapshot(sources)
    return bundle
