"""Bounded map tails for authenticated multi-resolution framed predecessors.

The caller reconstructs the entire original-bound predecessor first. This
module changes only checked render/input guards and appends the existing
bounded painter. It makes no runtime or release claim.
"""
from __future__ import annotations

from dataclasses import asdict
import hashlib
import struct

from . import framed_bounded_input as mouse
from . import framed_bounded_paint as paint
from . import framed_camera as camera
from . import partial_tile_clip as clip
from . import pe_extension as pe
from .framed_viewport import FramedViewport


def _require(value: bool, message: str) -> None:
    if not value:
        raise ValueError(message)


def _sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _nodes(metadata: dict):
    """Walk only the defined predecessor links; reject cycles and excess depth."""
    seen = set()
    for _ in range(24):
        _require(type(metadata) is dict and id(metadata) not in seen,
                 "invalid or cyclic predecessor metadata")
        seen.add(id(metadata))
        yield metadata
        links = [metadata[k] for k in ("predecessor", "base_candidate", "parent_build")
                 if type(metadata.get(k)) is dict]
        _require(len(links) <= 1, "ambiguous predecessor link")
        if not links:
            return
        metadata = links[0]
    raise ValueError("predecessor depth exceeds bounded inventory")


def integrate(parent: bytes, metadata: dict, *, profile: str, resolution: str,
              selected_stage: str) -> tuple[bytes, dict]:
    _require(type(parent) is bytes and profile in ("framed", "completehd", "modalwidgets")
             and type(metadata) is dict and metadata.get("candidate_sha256") == _sha(parent)
             and metadata.get("resolution") == resolution,
             "exact reconstructed framed predecessor required")
    width, height = map(int, resolution.split("x"))
    layout = FramedViewport(width, height)
    view = pe.inspect_pe(parent)
    nodes = list(_nodes(metadata))
    framed = [n for n in nodes if n.get("schema") == "clash95_pe_extension_v1"
              and n.get("framed_validation") is True]
    _require(len(framed) == 1, "one authenticated framed payload required")
    framed = framed[0]
    entries = framed.get("entry_vas")
    _require(type(entries) is dict and type(framed.get("code_va")) is int
             and type(framed.get("code_bytes")) is int, "framed payload inventory missing")
    extent = (framed["code_va"], framed["code_va"] + framed["code_bytes"])
    _require(all(type(entries.get(k)) is int and extent[0] <= entries[k] < extent[1]
                 for k in (*paint.HELPERS, "hook_framed_full_entry", "framed_full_reject",
                           "initial_paint_admission", "initial_admission_reject",
                           mouse.ENTRY, mouse.DENY)), "framed entries escape their payload")
    last = view.sections[-1]
    _require(last.characteristics == pe.RX_CODE
             and last.raw_offset + last.raw_size == len(parent),
             "last predecessor section must own the RX file tail")
    old_table, old_fields = pe._old_relocations(parent, view)
    helper_va = view.image_base + view.image_size
    helper = paint.emit_helpers(layout, base_va=helper_va, entries=entries)
    _require(len(helper.code) == 481, "bounded painter size differs")
    edits = []

    def read(va, count):
        offset = view.file_offset(va - view.image_base, count)
        return parent[offset:offset + count]

    def change(name, va, old, new, owner):
        _require(owner[0] <= va and va + len(old) <= owner[1]
                 and len(old) == len(new) and read(va, len(old)) == old,
                 "authenticated old guard differs: " + name)
        rva = va - view.image_base
        _require(not any(rva < f + 4 and f < rva + len(old) for f in old_fields),
                 "guard overlaps a HIGHLOW field: " + name)
        edit = pe.ByteEdit(view.file_offset(rva, len(old)), rva, va, old, new, name)
        edits.append(edit)

    for kind, entry_name, reject_name in (
            ("full_redraw", "hook_framed_full_entry", "framed_full_reject"),
            ("initial_paint", "initial_paint_admission", "initial_admission_reject")):
        entry, reject = entries[entry_name], entries[reject_name]
        prefix = camera._prefix(kind, entry, entries)
        _require(read(entry, len(prefix)) == prefix, "render admission prefix differs")
        at = entry + camera.GATE_OFFSETS[kind]
        replacement, relocs = paint._gate(kind, at, reject, helper)
        _require(all(r.kind == "rel32" for r in relocs), "dispatch must remain PIC")
        change("render." + kind, at, camera.old_gate(layout, at, reject), replacement, extent)

    input_owners = [("ordinary", entries, mouse.ENTRY, mouse.DENY, extent)]
    if profile != "framed":
        army = [n for n in nodes if n.get("schema") == "clash95_framed_army_candidate_v1"]
        _require(len(army) == 1, "one authenticated army payload required")
        army = army[0]
        army_entries = army.get("army_entry_vas")
        _require(type(army_entries) is dict and type(army.get("code_va")) is int
                 and type(army.get("code_bytes")) is int, "army payload inventory missing")
        input_owners.append(("army", army_entries, "input.private.pixel_guard.minimap_clear",
                             "input.private.pixel_guard.deny",
                             (army["code_va"], army["code_va"] + army["code_bytes"])))
    for owner, inventory, entry_name, deny_name, owner_extent in input_owners:
        start, deny = inventory.get(entry_name), inventory.get(deny_name)
        _require(type(start) is type(deny) is int, "input inventory missing: " + owner)
        old = mouse.world_gate(layout, start, deny)
        new = mouse.world_gate(layout, start, deny, small_world=True)
        _require(read(start, len(old)) == old, "input gate differs: " + owner)
        for axis, offset in zip(("x", "y"), (24, 108)):
            change("input." + owner + "." + axis, start + offset,
                   old[offset:offset + 16], new[offset:offset + 16], owner_extent)

    ordered = sorted(edits, key=lambda e: e.offset)
    _require(all(a.offset + len(a.old) <= b.offset for a, b in zip(ordered, ordered[1:])),
             "bounded guards overlap")
    within = view.image_size - last.rva
    _require(within == pe._align(last.memory_size, view.section_alignment)
             and 0 <= within - last.raw_size <= 256 * 1024,
             "unexpected predecessor tail backing gap")
    added = tuple(helper_va - view.image_base + offset
                  for offset in clip.absolute_relocation_offsets(helper))
    _require(len(added) == 5 and not set(added) & set(old_fields),
             "bounded helper relocation inventory differs")
    all_fields = tuple(sorted((*old_fields, *added)))
    table = pe._relocation_blocks(all_fields)
    table_offset = pe._align(within + len(helper.code), 4)
    used = table_offset + len(table)
    raw_size = pe._align(used, view.file_alignment)
    virtual_size = pe._align(used, view.section_alignment)
    _require(view.image_base + last.rva + virtual_size < 0x7ffe0000,
             "bounded extension exceeds user address space")
    appended = (bytes(within - last.raw_size) + helper.code
                + bytes(table_offset - within - len(helper.code)) + table + bytes(raw_size - used))
    for offset, data, purpose in (
            (last.header_offset + 8, struct.pack("<I", virtual_size), "bounded VirtualSize"),
            (last.header_offset + 16, struct.pack("<I", raw_size), "bounded SizeOfRawData"),
            (view.optional_offset + 4, struct.pack("<I", view.size_of_code + raw_size - last.raw_size),
             "bounded SizeOfCode"),
            (view.optional_offset + 56, struct.pack("<I", last.rva + virtual_size), "bounded SizeOfImage"),
            (view.optional_offset + 136, struct.pack("<II", last.rva + table_offset, len(table)),
             "bounded merged relocation directory")):
        edits.append(pe.ByteEdit(offset, offset, view.image_base + offset,
                                 parent[offset:offset + len(data)], data, purpose))
    edits.append(pe.ByteEdit(len(parent), last.rva + last.raw_size,
                             view.image_base + last.rva + last.raw_size, b"", appended,
                             "append bounded painter and merged relocation directory"))
    result = bytearray(parent)
    for edit in edits:
        _require(result[edit.offset:edit.offset + len(edit.old)] == edit.old
                 and (edit.old or edit.offset == len(result)), "old bytes changed during integration")
        result[edit.offset:edit.offset + len(edit.old)] = edit.new
    result = bytes(result)
    after = pe.inspect_pe(result)
    _require(after.sections[:-1] == view.sections[:-1]
             and pe._old_relocations(result, after) == (table, all_fields),
             "bounded PE layout or relocations differ")
    old_at = view.file_offset(view.relocation_rva, view.relocation_size)
    _require(result[old_at:old_at + len(old_table)] == old_table,
             "inherited relocation bytes changed")
    allowed = {edit.offset + i for edit in edits if edit.old for i in range(len(edit.old))}
    _require(all(a == b or i in allowed for i, (a, b) in enumerate(zip(parent, result))),
             "undeclared predecessor byte changed")
    records = [dict(e.metadata(), group="hd-multires-bounded", stage=selected_stage,
                    rationale="Bounded map repaint and actual-world input admission; preserve fitting-world paths.")
               for e in edits]
    return result, dict(bounded_small_world_integrated=True, small_world_input_enabled=True,
        camera_clamp=True, full_tiles=list(layout.full_tiles), ceil_tiles=list(layout.ceil_tiles),
        guard_count=len(ordered), edits=records,
        helper=dict(va=helper_va, byte_count=len(helper.code), sha256=_sha(helper.code),
                    entries=helper.entries, relocations=[asdict(r) for r in helper.relocations]),
        added_highlow_rvas=list(added), merged_highlow_count=len(all_fields),
        input_scope="Ordinary-map and owned army click/minimap admission; screen-route and device proof remain separate.",
        runtime_executed=False, manual_input_proof=False, promotion_ready=False)
