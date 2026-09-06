"""Uninstalled four-band presenter and native406740 entry wrapper.

No process, candidate, hook or resource is written. The native-entry wrapper
falls back to original code before admitted HD map state. Its admitted path
draws FRAME sprites only to the memory map, then uses the native blitter for
four disjoint primary bands. That matches native frame-entry footer clearing;
it is NOT a full-render tail that can overwrite primary-only tooltip text.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib

from . import four_sided_frame as frame
from . import partial_tile_clip as clip
from .framed_viewport import FramedViewport


NATIVE_ENTRY = 0x406740
NATIVE_FALLBACK = 0x406745
ENTRY_BYTES = bytes.fromhex("5351525657")
NATIVE_FRAME_SIZE = 0x237
NATIVE_FRAME_SHA256 = "a20d7a53afbd8c71dd12bac5d597fdc95493d7ae8338ab52f9ae809f125728f5"
PRIMARY_VTABLE = 0x50EEC4
NATIVE_SPANS = {
    0x4024E0: "56575589e581ec1001000089c689d7895df8894dfc85c07505bec0d4510085ff7505bfc0d45100",
    0x402783: "5f5ec21000",
    0x402818: "5f5ec21000",
    0x40283E: "5f5ec21000",
    0x4046B2: "c740dcc4ee50002ddc000000",  # Constructor sets +B8 to primary vtable.
    0x405660: "8b80bc000000c3",           # Read backend, not memory pixels+4.
    0x405680: "83b8cc0000000075078b80bc000000c3",
    0x405640: "31c0c3",                 # Memory source has no direct backend.
    0x50EE60: "40564000",               # Memory +3C ->405640, therefore CPU copy.
    0x50EECC: "104b4000",               # Primary +8 ->404B10 pixel iterator.
    0x404B29: "578bb9b800000089c8ff5740c702b4ed500089d1894204e8fbec0600",
    0x47385D: "8b86a4000000c746386c0000006a008b1850ff5364",  # COM Lock(+64).
    0x473883: "8b86a4000000508b10ff526c",                  # Lost-surface Restore(+6C).
    0x4738B0: "515283c0388b506c508b0a52ff91800000005a59c3", # Iterator Unlock(+80).
    0x404808: "c786bc00000000000000",     # Non8bpp explicitly has no direct backend.
    0x406971: "5f5e5a595bc3",
    # Both current callers overwrite EAX after the native frame call.
    0x40AD4D: "e8eeb9ffff8b15e00252008b0dec025200",
    0x40B789: "e8b2afffffb801000000bbd3010000",
}


@dataclass(frozen=True)
class FrameEntryHook:
    name: str
    offset: int
    va: int
    old_bytes: bytes
    entry_va: int
    fallback_va: int
    removed_highlow_vas: tuple[int, ...] = ()

    @property
    def rva(self) -> int:
        return self.va - 0x400000


@dataclass(frozen=True)
class FramedPresentationBundle(clip.AdapterBundle):
    hook_sites: tuple[FrameEntryHook, ...] = ()
    status_vas: dict[str, int] = field(default_factory=dict)
    native_contract: dict = field(default_factory=dict)


def _verify_native(original: bytes) -> None:
    clip.verify_original(original)
    offset = clip.file_offset(original, NATIVE_ENTRY, NATIVE_FRAME_SIZE)
    if hashlib.sha256(original[offset:offset + NATIVE_FRAME_SIZE]).hexdigest() != NATIVE_FRAME_SHA256:
        raise ValueError("native frame entry/return contract differs")
    for va, expected_hex in NATIVE_SPANS.items():
        expected = bytes.fromhex(expected_hex)
        offset = clip.file_offset(original, va, len(expected))
        if original[offset:offset + len(expected)] != expected:
            raise ValueError(f"native frame presentation ABI differs at {va:08x}")


def emit_framed_presentation(original: bytes, *, base_va: int,
                             width: int, height: int) -> FramedPresentationBundle:
    """Append two entrypoints to the authenticated standalone frame helper.

    ``present_frame_bands`` takes strict EAX=0/1. Zero returns1 with no drawing,
    primary access or native calls. One admits only the exact requested memory
    map, ordinary owner40AD40 with zero post/lower owners, and an initialized
    same-size 8bpp primary object. It returns1 after four4024E0 calls, or0 before
    any call on rejection. It preserves non-EAX GPR, flags/stack and the exact
    caller render pointer. It copies existing map pixels, including the footer;
    it does not prove those pixels were drawn or are correct.

    ``native_frame_entry`` is a prospective replacement for406740's five PUSHes.
    It admits the same state, runs draw_frame then present_frame_bands, and leaves
    g_RenderDevice=primary as native code did. GPR/flags/stack are preserved,
    including entry EAX (the native function has no stable EAX result contract).
    After-call status VAs expose admission/draw/present results independently of
    that restored EAX. Rejection restores entry state, replays the five PUSHes
    and transfers to406745. Native fallback is not a successful HD observation.

    The primary is NOT a memory surface: require vtable50EEC4, physical W/H,
    depth8 at+D4, backend+BC with COM surface+A4 and its Lock/Restore/Unlock
    methods; no +4 pixel or pre-lock backend+5C pixel requirement is imposed.
    Native loader ownership/lifetime remains necessary for all nonnull pointers.
    No direct primary sprite call, tooltip/input operation or installation occurs.
    """
    _verify_native(original)
    layout = FramedViewport(width, height)
    original_bundle = frame.emit_frame_helper(original, base_va=base_va, width=width, height=height)
    a = clip._Assembler(base_va)
    a.code.extend(original_bundle.code)
    a.relocations.extend(original_bundle.relocations)
    a.labels["draw_frame"] = original_bundle.entries["draw_frame"] - base_va
    statuses = {}

    def pointer(value: int, purpose: str) -> None:
        a.absolute(value, purpose)

    def status(name: str) -> None:
        statuses[name] = base_va + len(a.code)

    # Shared, fully preserving except EAX, side-effect-free admission. Only
    # source-owned live objects are dereferenced; never a null map pointer.
    a.label("frame_presentation_admission")
    a.emit("9c60")
    for address, expected, purpose in ((clip.RENDER_HOOK_GLOBAL, 0x40AD40, "render_hook"),
                                        (clip.POST_TILE_CALLBACK_GLOBAL, 0, "post_tile_callback"),
                                        (clip.LOWER_ROW_OWNER_GLOBAL, 0, "lower_row_owner")):
        a.emit("813d"); pointer(address, purpose)
        if expected:
            pointer(expected, "ordinary_map_owner")
        else:
            a.u32(0)
        a.branch("0f85", "admission_reject")
    a.emit("a1"); pointer(clip.MAP_SURFACE_GLOBAL, "map_surface_global")
    a.emit("85c0"); a.branch("0f84", "admission_reject")
    a.emit("3d"); pointer(frame.PRIMARY_SURFACE, "primary_surface")
    a.branch("0f84", "admission_reject")
    a.emit("8138"); a.u32(width | (height << 16))
    a.branch("0f85", "admission_reject")
    a.emit("83780400"); a.branch("0f84", "admission_reject")
    a.emit("81b8b8000000"); pointer(clip.MEMORY_VTABLE, "memory_vtable")
    a.branch("0f85", "admission_reject")
    a.emit("b8"); pointer(frame.PRIMARY_SURFACE, "primary_surface")
    a.emit("8138"); a.u32(width | (height << 16))
    a.branch("0f85", "admission_reject")
    a.emit("81b8b8000000"); pointer(PRIMARY_VTABLE, "primary_vtable")
    a.branch("0f85", "admission_reject")
    a.emit("83b8d400000008"); a.branch("0f85", "admission_reject")
    a.emit("8b80bc00000085c0"); a.branch("0f84", "admission_reject")
    a.emit("8b80a400000085c0"); a.branch("0f84", "admission_reject")
    a.emit("8b0085c0"); a.branch("0f84", "admission_reject")
    for method_offset in (0x64, 0x6C, 0x80):
        a.emit("83b8"); a.u32(method_offset); a.emit("00")
        a.branch("0f84", "admission_reject")
    a.emit("c744241c01000000619dc3")
    a.label("admission_reject")
    a.emit("c744241c00000000619dc3")

    a.label("present_frame_bands")
    a.emit("9c6089e583ec04a1"); pointer(clip.RENDER_DEVICE_GLOBAL, "render_device_global")
    a.emit("8945fc837d1c00"); a.branch("0f84", "present_noop")
    a.emit("837d1c01"); a.branch("0f85", "present_reject")
    a.branch("e8", "frame_presentation_admission")
    a.emit("83f801"); a.branch("0f85", "present_reject")
    for band in layout.frame_bands:
        if not layout.surface.contains(band) or band.intersection(layout.terrain) is not None:
            raise ValueError("frame copy rectangle violates physical/frame bounds")
        # Preserve our frame pointer across a destructive but ABI-clean callee.
        a.emit("55b8"); pointer(frame.PRIMARY_SURFACE, "primary_surface")
        a.emit("a3"); pointer(clip.RENDER_DEVICE_GLOBAL, "render_device_global")
        for value in (band.top, band.left, band.bottom, band.right):
            a.emit("68"); a.u32(value)
        a.emit("a1"); pointer(clip.MAP_SURFACE_GLOBAL, "map_surface_global")
        a.emit("31d2bb"); a.u32(band.left)
        a.emit("b9"); a.u32(band.top)
        a.emit("fc")
        a.native_transfer("blit")
        a.emit("5d")
    # This observation marks completed calls, not an uninterpreted native EAX.
    # The public presenter result is installed in the saved EAX below.
    status("present_calls_completed")
    a.label("present_noop")
    a.emit("c7451c01000000"); a.branch("e9", "present_restore")
    a.label("present_reject")
    a.emit("c7451c00000000")
    a.label("present_restore")
    a.emit("8b45fca3"); pointer(clip.RENDER_DEVICE_GLOBAL, "render_device_global")
    a.emit("89ec619dc3")

    a.label("native_frame_entry")
    a.emit("9c60")
    a.branch("e8", "frame_presentation_admission")
    status("native_admission")
    a.emit("83f801"); a.branch("0f85", "native_fallback")
    a.branch("e8", "draw_frame")
    status("native_draw")
    a.emit("83f801"); a.branch("0f85", "native_fallback")
    a.emit("b801000000")
    a.branch("e8", "present_frame_bands")
    status("native_present")
    a.emit("83f801"); a.branch("0f85", "native_fallback")
    a.emit("b8"); pointer(frame.PRIMARY_SURFACE, "primary_surface")
    a.emit("a3"); pointer(clip.RENDER_DEVICE_GLOBAL, "render_device_global")
    a.emit("619dc3")
    a.label("native_fallback")
    a.emit("619d" + ENTRY_BYTES.hex())
    a.emit("e9")
    a.relocations.append(clip.Relocation(len(a.code), "rel32", NATIVE_FALLBACK, "native_frame_fallback"))
    a.u32(NATIVE_FALLBACK - (base_va + len(a.code) + 4))

    code = a.finish()
    if base_va + len(code) > 0x80000000:
        raise ValueError("presentation bundle exceeds supported x86 allocation")
    entries = dict(original_bundle.entries)
    entries.update({name: base_va + pos for name, pos in a.labels.items()})
    hook = FrameEntryHook("native_frame", clip.file_offset(original, NATIVE_ENTRY, 5),
                          NATIVE_ENTRY, ENTRY_BYTES, entries["native_frame_entry"], NATIVE_FALLBACK)
    result = FramedPresentationBundle(base_va, code, entries, tuple(a.relocations), width, height,
        installation_ready=False, hook_sites=(hook,), status_vas=statuses,
        native_contract={"entry_va": NATIVE_ENTRY, "native_frame_sha256": NATIVE_FRAME_SHA256,
                         "native_frame_size": NATIVE_FRAME_SIZE, "displaced_highlow": [],
                         "primary_vtable": PRIMARY_VTABLE, "primary_depth": 8,
                         "primary_backend_offset": 0xBC, "primary_pixels_offset_4_required": False,
                         "backend_com_surface_offset": 0xA4,
                         "com_methods_required": [0x64, 0x6C, 0x80],
                         "backend_pixels_before_lock_required": False,
                         "frame_bands_inclusive": [rect.as_tuple() for rect in layout.frame_bands],
                         "return_eax_is_native_success": False,
                         "full_render_tail_must_preserve_primary_tooltip": True})
    clip.absolute_relocation_offsets(result)
    return result
