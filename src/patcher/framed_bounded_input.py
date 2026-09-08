"""Opt-in read-only mouse admission for the bounded small-world renderer."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from . import framed_bounded_paint as bounded
from . import framed_camera as camera
from . import pe_extension as pe
from .framed_viewport import FramedViewport

ROOT = Path(__file__).resolve().parents[2]
BOUNDED_SOURCE_SHA256 = "4fcadd0130058d0f6d0f542ff4579a96c72e5030b5d5784e53563271dbf822ff"
STAGE = bounded.STAGE.removesuffix("-validation") + "-input-validation"
AXIS_BYTES = 84
LIMIT_OFFSET = 24
LIMIT_BYTES = 16
ENTRY = "framed_input.pixel_guard.minimap_clear"
DENY = "framed_input.pixel_guard.deny"


def world_gate(layout: FramedViewport, va: int, deny_va: int, *, small_world: bool = False) -> bytes:
    camera.require(isinstance(layout, FramedViewport) and type(small_world) is bool, "invalid input geometry or option")
    camera._u32(va)
    camera._u32(deny_va)
    camera.require(0x10000 <= va and va + 2 * AXIS_BYTES + 22 <= 0x80000000,
                   "invalid input gate allocation")
    camera.require(deny_va == va + 2 * AXIS_BYTES + 11, "input denial label is not the exact continuation")
    a = camera._Code(va)
    for dimension, scroll, count, axis in zip(camera.MAP_DIMENSIONS, camera.MAP_SCROLL, layout.full_tiles, ("x", "y")):
        start = len(a.data)
        a.emit("8b86"); a.integer(dimension)
        a.emit("83f801"); a.branch("0f8c", deny_va)
        a.emit("83f864"); a.branch("0f8f", deny_va)
        camera.require(len(a.data) - start == LIMIT_OFFSET, "input limit offset differs")
        if small_world:
            a.emit("2d"); a.integer(count)
            a.emit("790231c0" + "90" * 7)
        else:
            a.emit("3d"); a.integer(count); a.branch("0f8c", deny_va)
            a.emit("2d"); a.integer(count)
        a.emit("8bbe"); a.integer(scroll)
        a.emit("85ff"); a.branch("0f8c", deny_va)
        a.emit("39c7"); a.branch("0f8f", deny_va)
        a.emit("89d8" if axis == "x" else "89d0")
        a.emit("83e820c1f806" if axis == "x" else "83e810c1f806")
        a.emit("01f83b86"); a.integer(dimension); a.branch("0f8d", deny_va)
        camera.require(len(a.data) - start == AXIS_BYTES, "input axis size differs")
    for result in (1, 0):
        a.emit("c744241c"); a.integer(result); a.emit("619dc3")
    return bytes(a.data)


def _upgrade_verified_parent(parent: bytes, metadata: dict[str, Any], resolution: str):
    from . import patch_clash95_hd as patcher
    camera.require(type(parent) is bytes and isinstance(metadata, dict), "invalid bounded parent")
    profile = patcher.parse_resolution(resolution)
    camera.require(profile.key == resolution, "resolution must use canonical WxH spelling")
    layout = FramedViewport(profile.width, profile.height)
    camera.require(metadata.get("schema") == "clash95_bounded_paint_v1"
        and metadata.get("stage") == bounded.STAGE and metadata.get("resolution") == resolution
        and metadata.get("bounded_small_world_paint") is True and metadata.get("camera_clamp") is True
        and metadata.get("minimap_viewport") is True and metadata.get("small_world_input_enabled") is False
        and metadata.get("validation_stage_only") is True and metadata.get("output_sha256") == camera.sha(parent),
        "bounded parent identity differs")
    camera.require(all(metadata.get(n) is False for n in ("game_runtime_executed", "manual_input_proof", "promotion_ready", "parent_probe_reusable")),
                   "parent evidence boundary differs")
    image = pe.inspect_pe(parent)
    code_va, code_size = metadata.get("code_va"), metadata.get("code_bytes")
    camera._u32(code_va)
    camera.require(type(code_size) is int and code_size > 0, "invalid parent code size")
    section = image.sections[-1]
    camera.require(section.name.rstrip(b"\0") == b".hdcode" and section.characteristics == pe.RX_CODE
        and code_va == image.image_base + section.rva and code_size <= section.raw_size,
        "bounded extension layout differs")
    code_offset = image.file_offset(code_va - image.image_base, code_size)
    camera.require(camera.sha(parent[code_offset:code_offset + code_size]) == metadata.get("code_sha256"),
                   "bounded payload identity differs")
    entries = metadata.get("entry_vas")
    camera.require(isinstance(entries, dict) and all(type(entries.get(n)) is int
        and code_va <= entries[n] < code_va + code_size for n in (ENTRY, DENY)), "input entries are incomplete")
    start, deny = entries[ENTRY], entries[DENY]
    old = world_gate(layout, start, deny)
    new = world_gate(layout, start, deny, small_world=True)
    camera.require(start + len(old) <= code_va + code_size, "input gate exceeds parent payload")
    gate_offset = image.file_offset(start - image.image_base, len(old))
    camera.require(parent[gate_offset:gate_offset + len(old)] == old, "input world gate old bytes differ")
    relocation_table, locations = pe._old_relocations(parent, image)
    relocs = metadata.get("relocations")
    camera.require(isinstance(relocs, list), "parent relocation inventory missing")
    for row in relocs:
        camera.require(isinstance(row, dict) and type(row.get("offset")) is int
            and 0 <= row["offset"] <= code_size - 4 and row.get("kind") in ("abs32", "rel32"),
            "invalid parent relocation record")
    edits = []
    result = bytearray(parent)
    for axis in range(2):
        within = axis * AXIS_BYTES + LIMIT_OFFSET
        offset, va = gate_offset + within, start + within
        rva = va - image.image_base
        camera.require(not any(rva < field + 4 and field < rva + LIMIT_BYTES for field in locations),
                       "input edit intersects a HIGHLOW relocation")
        camera.require(not any(va < code_va + row["offset"] + 4 and code_va + row["offset"] < va + LIMIT_BYTES for row in relocs),
                       "input edit intersects a declared relocation")
        before, after = old[within:within + LIMIT_BYTES], new[within:within + LIMIT_BYTES]
        camera.require(bytes(result[offset:offset + LIMIT_BYTES]) == before, "input old bytes changed before write")
        result[offset:offset + LIMIT_BYTES] = after
        edits.append({"name": "world_" + ("x" if axis == 0 else "y"), "offset": offset, "va": va, "rva": rva,
            "old_hex": before.hex(), "new_hex": after.hex(), "group": "framed-bounded-input", "stage": STAGE,
            "rationale": "Use max(0, world-full viewport) for read-only mouse admission; retain world-coordinate, overlay and stale-camera rejection."})
    result = bytes(result)
    camera.require(result[gate_offset:gate_offset + len(new)] == new, "input gate reconstruction differs")
    camera.require(pe.inspect_pe(result) == image and pe._old_relocations(result, image) == (relocation_table, locations),
                   "input patch changed PE layout or relocation directory")
    report = {"schema": "clash95_bounded_input_v1", "stage": STAGE, "parent_stage": bounded.STAGE,
        "resolution": resolution, "parent_sha256": camera.sha(parent), "output_sha256": camera.sha(result),
        "code_va": code_va, "code_bytes": code_size, "code_sha256": camera.sha(result[code_offset:code_offset + code_size]),
        "edits": edits, "parent_build": metadata, "relocation_directory_sha256": camera.sha(relocation_table),
        "highlow_count": len(locations), "full_tiles": list(layout.full_tiles),
        "bounded_small_world_paint": True, "small_world_input_enabled": True, "camera_clamp": True, "minimap_viewport": True,
        "input_scope": "Existing ordinary-map minimap_gate and click_gate mouse wrappers only; input does not mutate camera or target memory.",
        "validation_stage_only": True, "game_runtime_executed": False, "manual_input_proof": False,
        "promotion_ready": False, "parent_probe_reusable": False,
        "limits": "No keyboard/edge-scroll/minimap-navigation rewrite, additional screen support, callback execution proof or gameplay qualification. Stale cameras still reject until repaint clamps them. Parent metadata and probes describe the intermediate stage; apply these edits after parent_build."}
    return result, report


def source_status() -> dict[str, Any]:
    camera.require(Path(bounded.__file__).resolve() == ROOT / "src/patcher/framed_bounded_paint.py"
        and camera.sha(Path(bounded.__file__).read_bytes()) == BOUNDED_SOURCE_SHA256, "reviewed bounded renderer source changed")
    camera.require(camera.sha(Path(camera.__file__).read_bytes()) == bounded.CAMERA_SOURCE_SHA256,
                   "reviewed camera source changed")
    return camera.source_status()


def build_candidate(original: bytes, resolution: str):
    camera.require(type(original) is bytes and camera.sha(original) == pe.ORIGINAL_SHA256, "unknown original executable SHA-256")
    source_status()
    parent, metadata = bounded.build_candidate(original, resolution)
    image, report = _upgrade_verified_parent(parent, metadata, resolution)
    report["original_sha256"] = camera.sha(original)
    report["source_sha256"] = {**metadata["source_sha256"],
        "src/patcher/framed_bounded_input.py": camera.sha(Path(__file__).read_bytes())}
    return image, report
