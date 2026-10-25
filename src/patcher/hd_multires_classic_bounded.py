"""Bounded Classic map cells, retaining native Classic UI and presentation.

The original-bound Classic predecessor is reconstructed before installing eight
narrow hooks. Framed recipes, four-sided chrome and moved command lists are
never used. This module builds bytes in memory and makes no runtime claim.
"""
from __future__ import annotations

import hashlib
import json
import struct

from . import classic_all_presets_candidate as classic
from . import partial_tile_clip as clip
from . import pe_extension as pe

RESOLUTIONS = ("1920x1080", "2560x1440", "3840x2160")
FULL_ENTRY = bytes.fromhex("53515256575583ec18")
INCREMENTAL_ENTRY = bytes.fromhex("535156575583ec08")
FULL_SHA256 = "0bc270a6f9131268c61dad8b65ff8ea04a43fd44371c63b21a4e06ea9b9d5e5c"
MOUSE_CALLS = ((0x4084A9, 0x40DD60, "minimap_gate"),
               (0x407F3C, 0x40DD60, "minimap_gate"),
               (0x408039, 0x4608F0, "click_gate"))


def require(value, message):
    if not value:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _same_json(left, right):
    return json.dumps(left, sort_keys=True, separators=(",", ":")) == json.dumps(right, sort_keys=True, separators=(",", ":"))


def _append(parent, bundle, hooks, removed):
    """Extend only the authenticated final RX tail; retain its old bytes."""
    view = pe.inspect_pe(parent)
    last = view.sections[-1]
    require(last.characteristics == pe.RX_CODE and last.raw_offset + last.raw_size == len(parent),
            "Classic final RX section must own the complete file tail")
    old_table, old_fields = pe._old_relocations(parent, view)
    hook_edits, hook_absolute, _, _ = pe._prepare_hooks(parent, view, hooks, removed,
        old_fields, bundle.base_va, len(bundle.code))
    require(not hook_absolute, "Classic hooks must remain relative transfers")
    fields = clip.absolute_relocation_offsets(bundle)
    new_fields = tuple(bundle.base_va - view.image_base + offset for offset in fields)
    merged = tuple(sorted((*[field for field in old_fields if field not in removed], *new_fields)))
    require(len(set(merged)) == len(merged), "Classic relocation fields overlap")
    table = pe._relocation_blocks(merged)
    within = view.image_size - last.rva
    require(bundle.base_va == view.image_base + view.image_size and
            within == pe._align(last.memory_size, view.section_alignment) and
            0 <= within - last.raw_size <= 256 * 1024, "Classic tail allocation differs")
    table_offset = pe._align(within + len(bundle.code), 4)
    used = table_offset + len(table)
    raw_size, virtual_size = pe._align(used, view.file_alignment), pe._align(used, view.section_alignment)
    require(view.image_base + last.rva + virtual_size < 0x7FFE0000, "Classic extension exceeds user range")
    appended = (bytes(within - last.raw_size) + bundle.code +
        bytes(table_offset - within - len(bundle.code)) + table + bytes(raw_size - used))
    edits = list(hook_edits)
    for offset, data, purpose in (
            (last.header_offset + 8, struct.pack("<I", virtual_size), "Classic bounded VirtualSize"),
            (last.header_offset + 16, struct.pack("<I", raw_size), "Classic bounded raw size"),
            (view.optional_offset + 4, struct.pack("<I", view.size_of_code + raw_size - last.raw_size), "Classic bounded code size"),
            (view.optional_offset + 56, struct.pack("<I", last.rva + virtual_size), "Classic bounded image size"),
            (view.optional_offset + 136, struct.pack("<II", last.rva + table_offset, len(table)), "Classic merged relocations")):
        edits.append(pe.ByteEdit(offset, offset, view.image_base + offset, parent[offset:offset + len(data)], data, purpose))
    edits.append(pe.ByteEdit(len(parent), last.rva + last.raw_size,
        view.image_base + last.rva + last.raw_size, b"", appended, "append Classic bounded code and relocations"))
    image = bytearray(parent)
    for edit in edits:
        require(image[edit.offset:edit.offset + len(edit.old)] == edit.old and
                (edit.old or edit.offset == len(image)), "Classic old-byte edit differs")
        image[edit.offset:edit.offset + len(edit.old)] = edit.new
    image = bytes(image)
    after = pe.inspect_pe(image)
    require(after.sections[:-1] == view.sections[:-1] and
            pe._old_relocations(image, after) == (table, merged), "Classic final layout or relocations differ")
    at = view.file_offset(view.relocation_rva, len(old_table))
    require(image[at:at + len(old_table)] == old_table, "Classic old relocation bytes changed")
    allowed = {edit.offset + i for edit in edits if edit.old for i in range(len(edit.old))}
    require(all(a == b or index in allowed for index, (a, b) in enumerate(zip(parent, image))),
            "undeclared Classic predecessor byte changed")
    return image, edits, len(new_fields)


def emit(original: bytes, *, base_va: int, width: int, height: int):
    """Emit preserving native-call adapters and bounded Classic cells."""
    require(f"{width}x{height}" in RESOLUTIONS, "unsupported Classic HD geometry")
    clip.verify_original(original)
    tx, ty = (width - 32) // 64, (height - 16) // 64
    cx, cy = (width - 32 + 63) // 64, (height - 16 + 63) // 64
    trial = clip.emit_adapters(original, base_va=base_va, width=width, height=height,
        _clipped_vtable_va=0, clip_origin=(32, 16), clip_end=(width - 1, height - 1))
    table_offset = (len(trial.code) + 15) & ~15
    table_va = base_va + table_offset
    primitives = clip.emit_adapters(original, base_va=base_va, width=width, height=height,
        _clipped_vtable_va=table_va, clip_origin=(32, 16), clip_end=(width - 1, height - 1))
    a = clip._Assembler(base_va)
    a.code.extend(primitives.code)
    a.relocations.extend(primitives.relocations)
    a.code.extend(bytes(table_offset - len(a.code)))
    table = list(clip.VTABLE_ENTRIES)
    for slot, name in ((5, "line"), (6, "outline"), (7, "fill"), (13, "sprite")):
        table[slot] = primitives.entries[name]
    for index, target in enumerate(table):
        if target:
            a.absolute(target, "classic_vtable_" + str(index))
        else:
            a.u32(0)
    a.labels.update({name: va - base_va for name, va in primitives.entries.items()})

    def glob(address, purpose):
        a.absolute(address, purpose)

    def transfer(opcode, target, purpose):
        a.emit(opcode)
        offset = len(a.code)
        a.relocations.append(clip.Relocation(offset, "rel32", target, purpose))
        a.u32(target - base_va - offset - 4)

    def native(name):
        transfer("e8", clip.NATIVE_TARGETS[name], "classic_native_" + name)

    def bad(opcode="0f85", target="context.reject"):
        a.branch(opcode, target)

    a.label("context")
    a.emit("9c6089e5")
    for address, value, name in ((clip.RENDER_HOOK_GLOBAL, 0x40AD40, "ordinary_map"),
            (clip.LOWER_ROW_OWNER_GLOBAL, 0, "lower_owner"), (clip.POST_TILE_CALLBACK_GLOBAL, 0, "post_owner")):
        a.emit("813d"); glob(address, name)
        if value:
            glob(value, name + "_target")
        else:
            a.u32(0)
        bad()
    a.emit("a1"); glob(clip.TILE_CALLBACK_GLOBAL, "tile_callback")
    a.emit("85c0"); a.branch("0f84", "context.callback")
    for target in (0x425120, 0x429EC0):
        a.emit("3d"); glob(target, "tile_callback_target")
        a.branch("0f84", "context.callback")
    a.branch("e9", "context.reject")
    a.label("context.callback")
    a.emit("a1"); glob(clip.MAP_SURFACE_GLOBAL, "map_surface")
    a.emit("85c0"); bad("0f84")
    a.emit("3d"); glob(0x51D4C0, "primary_surface"); bad("0f84")
    a.emit("8138"); a.u32(width | height << 16); bad()
    a.emit("83780400"); bad("0f84")
    a.emit("81b8b8000000"); glob(clip.MEMORY_VTABLE, "memory_vtable")
    a.branch("0f84", "context.table")
    a.emit("81b8b8000000"); glob(table_va, "classic_clipped_vtable"); bad()
    a.label("context.table")
    a.emit("8b15"); glob(clip.GAME_DATA_GLOBAL, "game_data")
    a.emit("85d2"); bad("0f84")
    a.emit("a1"); glob(clip.CURRENT_PLAYER_GLOBAL, "current_player")
    a.emit("83f805"); bad("0f83")
    a.emit("83bac73e020005"); bad("0f83")
    for dimension in (0x222E0, 0x222E4):
        a.emit("8b82"); a.u32(dimension)
        a.emit("83f801"); bad("0f8c")
        a.emit("83f864"); bad("0f8f")
    a.emit("c7451c0100000089ec619dc3")
    a.label("context.reject")
    a.emit("c7451c0000000089ec619dc3")

    a.label("clamp_camera")
    a.emit("9c608b15"); glob(clip.GAME_DATA_GLOBAL, "game_data")
    for dimension, scroll, count, axis in ((0x222E0, 0x222E8, tx, "x"), (0x222E4, 0x222EC, ty, "y")):
        a.emit("8b82"); a.u32(dimension)
        a.emit("2d"); a.u32(count)
        a.branch("0f89", "clamp.max_" + axis)
        a.emit("31c0")
        a.label("clamp.max_" + axis)
        a.emit("8b8a"); a.u32(scroll)
        a.emit("85c9790231c939c17e0289c1898a"); a.u32(scroll)
    a.emit("619dc3")

    a.label("cell")
    a.emit("9c6089e583ec40")
    # -4 map, -8 vtable, -12 render, -16/-20 L/T, -24/-28 R/B,
    # -32 game, -36/-40 worldX/Y, -44 cursor, -48 status, -52/-56 column/row.
    a.emit("8b451c85c0"); bad("0f88", "cell.reject")
    a.emit("3d"); a.u32(cx); bad("0f8d", "cell.reject")
    a.emit("8945cc8b451085c0"); bad("0f88", "cell.reject")
    a.emit("3d"); a.u32(cy); bad("0f8d", "cell.reject")
    a.emit("8945c88b450483f801"); bad("0f87", "cell.reject")
    a.emit("55"); a.branch("e8", "context"); a.emit("5d83f801"); bad("0f85", "cell.reject")
    a.emit("8b35"); glob(clip.GAME_DATA_GLOBAL, "game_data")
    a.emit("8975e0")
    for dimension, scroll, count, index, out, axis in (
            (0x222E0, 0x222E8, tx, 0xCC, 0xDC, "x"), (0x222E4, 0x222EC, ty, 0xC8, 0xD8, "y")):
        a.emit("8b86"); a.u32(dimension)
        a.emit("2d"); a.u32(count)
        a.branch("0f89", "cell.max_" + axis)
        a.emit("31c0")
        a.label("cell.max_" + axis)
        a.emit("8b96"); a.u32(scroll)
        a.emit("85d2"); bad("0f88", "cell.reject")
        a.emit("39c2"); bad("0f8f", "cell.reject")
        a.emit("0355" + bytes([index]).hex() + "8955" + bytes([out]).hex())
    for source, origin, limit, start, end, axis in ((0xCC, 32, width, 0xF0, 0xE8, "x"),
                                                  (0xC8, 16, height, 0xEC, 0xE4, "y")):
        a.emit("8b45" + bytes([source]).hex() + "c1e00605"); a.u32(origin)
        a.emit("8945" + bytes([start]).hex() + "83c03f3d"); a.u32(limit - 1)
        a.branch("0f8e", "cell.end_" + axis)
        a.emit("b8"); a.u32(limit - 1)
        a.label("cell.end_" + axis)
        a.emit("8945" + bytes([end]).hex())
    a.emit("a1"); glob(clip.MAP_SURFACE_GLOBAL, "map_surface")
    a.emit("8945fc8b90b80000008955f8a1"); glob(clip.RENDER_DEVICE_GLOBAL, "render_device")
    a.emit("8945f48b45fcc780b8000000"); glob(table_va, "classic_clipped_vtable")
    a.emit("a3"); glob(clip.RENDER_DEVICE_GLOBAL, "render_device")
    a.emit("8b45dc3b86e0220200"); a.branch("0f8d", "cell.clear")
    a.emit("8b45d83b86e4220200"); a.branch("0f8d", "cell.clear")
    # Only form the native record pointer after both actual-world bounds.
    a.emit("695ddc78050000035de08b55d86bd20e01d38b45f08b55ec55")
    native("tile")
    a.emit("5dc745d001000000"); a.branch("e9", "cell.restore")
    a.label("cell.clear")
    a.emit("8b45fc8b55f08b4de88b5dec556a01ff75e4")
    a.branch("e8", "fill"); a.emit("5d8b45f08b55ec8b4de48b5de855")
    native("minimap")
    a.emit("5dc745d002000000")
    a.label("cell.restore")
    a.emit("8b45fc8b55f88990b80000008b45f4a3"); glob(clip.RENDER_DEVICE_GLOBAL, "render_device")
    a.emit("837d0400"); a.branch("0f84", "cell.done")
    a.emit("a1"); glob(clip.CURSOR_VISIBLE_GLOBAL, "cursor_visible")
    a.emit("8945d4558b45e440508b55f08b4de8418b5decb8"); glob(0x544CD8, "cursor_object")
    native("dirty")
    a.emit("5d558b45fc31d28b5df08b4decff75ecff75f0ff75e4ff75e8")
    native("blit")
    a.emit("5d837dd400"); a.branch("0f84", "cell.done")
    a.emit("55b8"); glob(0x544CD8, "cursor_object"); native("cursor"); a.emit("5d")
    a.label("cell.done")
    a.emit("8b45d089451c89ec619dc3")
    a.label("cell.reject")
    a.emit("c7451c0000000089ec619dc3")

    a.label("full_tile")
    a.emit("9c6089e555"); a.branch("e8", "context"); a.emit("5d83f801")
    a.branch("0f85", "full_tile.unsupported")
    a.emit("8b451c83e820c1f8068b5d1483eb10c1fb0631f655")
    a.branch("e8", "cell"); a.emit("5d89451c89ec619dc3")
    a.label("full_tile.unsupported")
    a.emit("813d"); glob(clip.RENDER_HOOK_GLOBAL, "render_hook"); glob(0x40AD40, "ordinary_map")
    a.branch("0f84", "full_tile.reject")
    a.emit("89ec619d"); transfer("e9", clip.NATIVE_TARGETS["tile"], "classic_unknown_owner_tile")
    a.label("full_tile.reject"); a.emit("c7451c0000000089ec619dc3")

    a.label("full_trampoline"); a.emit(FULL_ENTRY.hex())
    transfer("e9", 0x418709, "classic_full_native_body")
    a.label("full_entry")
    a.emit("9c6089e555"); a.branch("e8", "context"); a.emit("5d83f801")
    a.branch("0f85", "full.fallback")
    a.emit("55"); a.branch("e8", "clamp_camera"); a.emit("5d")
    a.label("full.fallback")
    a.emit("813d"); glob(clip.RENDER_HOOK_GLOBAL, "render_hook"); glob(0x40AD40, "ordinary_map")
    # A known map owner with a failed context must not enter native pointer
    # formation. Successful admission reaches the trampoline directly below.
    a.branch("0f85", "full.native")
    a.emit("55"); a.branch("e8", "context"); a.emit("5d83f801")
    a.branch("0f85", "full.reject")
    a.label("full.native")
    a.emit("89ec619d"); a.branch("e9", "full_trampoline")
    a.label("full.reject"); a.emit("c7451c0000000089ec619dc3")

    a.label("partial_tail")
    a.emit("9c6089e583ec0455"); a.branch("e8", "context"); a.emit("5d83f801")
    a.branch("0f85", "partial.done")
    # Native full redraw treats every nonzero EBP as present. The cell API
    # uses an exact boolean, so normalize only the private copy.
    a.emit("8b450885c00f95c00fb6c08945fc")
    for row in range(cy):
        for col in range(cx):
            if row < ty and col < tx:
                continue
            a.emit("b8"); a.u32(col); a.emit("bb"); a.u32(row)
            a.emit("8b75fc55"); a.branch("e8", "cell"); a.emit("5d")
    a.label("partial.done")
    a.emit("89ec619d833d"); glob(clip.POST_TILE_CALLBACK_GLOBAL, "post_tile_callback")
    a.emit("00"); transfer("e9", 0x4187A7, "classic_full_converge_resume")

    a.label("incremental")
    a.emit("9c6089e555"); a.branch("e8", "context"); a.emit("5d83f801")
    a.branch("0f85", "incremental.fallback")
    a.emit("8b35"); glob(clip.GAME_DATA_GLOBAL, "game_data")
    a.emit("8b451c2b86e82202008b5d142b9eec220200be0100000055")
    a.branch("e8", "cell"); a.emit("5d89451c89ec619dc3")
    a.label("incremental.fallback")
    a.emit("813d"); glob(clip.RENDER_HOOK_GLOBAL, "render_hook"); glob(0x40AD40, "ordinary_map")
    a.branch("0f84", "incremental.reject")
    a.emit("89ec619d" + INCREMENTAL_ENTRY.hex())
    transfer("e9", 0x418A98, "classic_incremental_native_body")
    a.label("incremental.reject"); a.emit("c7451c0000000089ec619dc3")

    a.label("pixel_world")
    a.emit("9c6089e58b35"); glob(clip.GAME_DATA_GLOBAL, "game_data")
    a.emit("0fb60d"); glob(0x54512C, "mouse_shift")
    a.emit("8b1d"); glob(0x544CFC, "mouse_x")
    a.emit("8b15"); glob(0x544D00, "mouse_y")
    a.emit("d3fbd3fa83fb20"); bad("0f8c", "pixel.reject")
    a.emit("81fb"); a.u32(width); bad("0f8d", "pixel.reject")
    a.emit("83fa10"); bad("0f8c", "pixel.reject")
    a.emit("81fa"); a.u32(height); bad("0f8d", "pixel.reject")
    for dim, scroll, count, axis in ((0x222E0, 0x222E8, tx, "x"), (0x222E4, 0x222EC, ty, "y")):
        a.emit("8b86"); a.u32(dim)
        a.emit("2d"); a.u32(count)
        a.branch("0f89", "pixel.max_" + axis); a.emit("31c0")
        a.label("pixel.max_" + axis)
        a.emit("8bbe"); a.u32(scroll)
        a.emit("85ff"); bad("0f8c", "pixel.reject")
        a.emit("39c7"); bad("0f8f", "pixel.reject")
        a.emit("89d8" if axis == "x" else "89d0")
        a.emit("83e820c1f806" if axis == "x" else "83e810c1f806")
        a.emit("01f83b86"); a.u32(dim); bad("0f8d", "pixel.reject")
    a.emit("c7451c0100000089ec619dc3")
    a.label("pixel.reject"); a.emit("c7451c0000000089ec619dc3")
    for name, target, active in (("minimap_gate", 0x40DD60, False), ("click_gate", 0x4608F0, True)):
        a.label(name); a.emit("9c6089e555"); a.branch("e8", "context"); a.emit("5d83f801")
        a.branch("0f85", name + ".fallback")
        if active:
            a.emit("8b451c"); transfer("e8", target, "classic_native_click")
            a.emit("85c0"); a.branch("0f84", name + ".deny")
        transfer("e8", 0x40DD60, "classic_native_minimap")
        a.emit("85c0"); a.branch("0f85", name + ".deny")
        a.emit("55"); a.branch("e8", "pixel_world"); a.emit("5d85c0")
        a.branch("0f84", name + ".deny")
        a.emit("c7451c"); a.u32(1 if active else 0); a.emit("89ec619dc3")
        a.label(name + ".deny")
        a.emit("c7451c"); a.u32(0 if active else 1); a.emit("89ec619dc3")
        a.label(name + ".fallback")
        a.emit("813d"); glob(clip.RENDER_HOOK_GLOBAL, "render_hook"); glob(0x40AD40, "ordinary_map")
        a.branch("0f84", name + ".deny")
        a.emit("89ec619d")
        transfer("e9", target, "classic_native_mouse_fallback")

    code = a.finish()
    for offset, label in a.fixups:
        a.relocations.append(clip.Relocation(offset, "rel32", base_va + a.labels[label], "classic_internal_" + label))
    bundle = clip.AdapterBundle(base_va, code, {name: base_va + offset for name, offset in a.labels.items()},
        tuple(a.relocations), width, height)
    clip.absolute_relocation_offsets(bundle)
    return bundle


def integrate(parent: bytes, metadata: dict, *, original: bytes, profile: str = "classic",
              resolution: str, selected_stage: str):
    require(profile == "classic" and resolution in RESOLUTIONS and type(parent) is type(original) is bytes,
            "exact Classic HD parent and original required")
    require(selected_stage == classic.STABLE_STAGE + "-classic-hd-multires-validation",
            "exact Classic multiresolution validation stage required")
    clip.verify_original(original)
    expected, context, _ = classic.build_candidate(original, resolution)
    require(parent == expected and _same_json(metadata, context), "Classic parent reconstruction differs")
    start = clip.file_offset(original, 0x418700, 0x390)
    require(sha(original[start:start + 0x390]) == FULL_SHA256, "native full function contract differs")
    view = pe.inspect_pe(parent)
    width, height = map(int, resolution.split("x"))
    bundle = emit(original, base_va=view.image_base + view.image_size, width=width, height=height)
    hooks = []
    removed = []
    windows = [(0x418700, FULL_ENTRY, "full_entry"),
        (0x418766, b"\xe8" + struct.pack("<i", 0x416850 - 0x41876B), "full_tile"),
        (0x4189F5, b"\xe8" + struct.pack("<i", 0x416850 - 0x4189FA), "full_tile"),
        (0x4187A0, bytes.fromhex("833d9069520000"), "partial_tail"),
        (0x418A90, INCREMENTAL_ENTRY, "incremental")]
    windows += [(va, b"\xe8" + struct.pack("<i", target - va - 5), entry) for va, target, entry in MOUSE_CALLS]
    for va, old, entry in windows:
        offset = clip.file_offset(parent, va, len(old))
        require(parent[offset:offset + len(old)] == old, "Classic native hook old bytes differ")
        target = bundle.entries[entry]
        opcode = b"\xe8" if entry == "full_tile" or entry in ("minimap_gate", "click_gate") else b"\xe9"
        new = opcode + struct.pack("<i", target - va - 5) + b"\x90" * (len(old) - 5)
        fields = clip._original_highlow_fields(original, va, len(old))
        require(fields == ({2} if va == 0x4187A0 else set()), "native hook relocation fields differ")
        removed.extend(va - view.image_base + field for field in fields)
        hooks.append(pe.HookPatch(offset, va - view.image_base, va, old, new, "classic_bounded_" + entry,
            (pe.CodeRelocation(1, "rel32", target, "classic_bounded_" + entry),)))
    image, edits, added = _append(parent, bundle, hooks, tuple(removed))
    return image, dict(bounded_small_world_integrated=True, small_world_input_enabled=True,
        camera_clamp=True, classic_style_preserved=True, framed_builder_used=False,
        terrain=[32, 16, width - 1, height - 1],
        helper=dict(va=bundle.base_va, byte_count=len(bundle.code), sha256=sha(bundle.code), entries=bundle.entries),
        edits=[dict(edit.metadata(), group="classic-bounded-world", stage=selected_stage,
                    rationale="Bound actual-world drawing and input while retaining native Classic UI.") for edit in edits],
        native_hooks=len(hooks), added_highlow_count=added,
        input_scope="Actual-world admission for three existing ordinary-map mouse CALLs; native panel branches retained.",
        runtime_executed=False, manual_input_proof=False, promotion_ready=False)
