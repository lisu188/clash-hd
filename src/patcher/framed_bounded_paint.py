"""Opt-in small-world full repaint using the existing guarded cell renderer."""
from __future__ import annotations

from dataclasses import replace
import importlib
from pathlib import Path
import struct
from typing import Any

from . import framed_camera as camera
from . import partial_tile_clip as clip
from . import pe_extension as pe
from .framed_viewport import FramedViewport

ROOT = Path(__file__).resolve().parents[2]
CAMERA_SOURCE_SHA256 = "c86e20700cd4716ad0905bcc2cb868c0f4fcfad91b984b38bf513b3829b9d798"
STAGE = camera.PARENT_STAGE.removesuffix("-validation") + "-bounded-paint-validation"
HELPERS = ("composition_guard", "cell", "draw_frame", "compose_panel", "present_map_rect")


def _transfer(a, opcode: str, target: int, purpose: str) -> None:
    camera._u32(target)
    a.emit(opcode)
    offset = len(a.code)
    delta = target - (a.base + offset + 4)
    camera.require(-(1 << 31) <= delta < 1 << 31, "relative transfer overflows x86")
    a.u32(delta)
    a.relocations.append(clip.Relocation(offset, "rel32", target, purpose))


def emit_helpers(layout: FramedViewport, *, base_va: int, entries: dict[str, int]) -> clip.AdapterBundle:
    camera.require(isinstance(layout, FramedViewport), "expected framed viewport")
    camera.require(type(base_va) is int and 0x10000 <= base_va <= 0x7FFE0000, "invalid x86 allocation")
    camera.require(isinstance(entries, dict) and all(type(entries.get(n)) is int
                   and 0x10000 <= entries[n] < base_va for n in HELPERS), "missing or non-parent helper entry")
    a = clip._Assembler(base_va)

    def call(name: str) -> None:
        a.emit("55")
        _transfer(a, "e8", entries[name], "bounded_" + name)
        a.emit("5d")

    a.label("admit_world")
    a.emit("9c6089e585d2")
    a.branch("0f84", "admit.reject")
    for dimension in camera.MAP_DIMENSIONS:
        a.emit("8b82"); a.u32(dimension)
        a.emit("83f801"); a.branch("0f8c", "admit.reject")
        a.emit("83f864"); a.branch("0f8f", "admit.reject")
    a.emit("bb01000000")
    for axis, (dimension, scroll, count) in enumerate(zip(camera.MAP_DIMENSIONS, camera.MAP_SCROLL, layout.full_tiles)):
        a.emit("8b82"); a.u32(dimension)
        a.emit("2d"); a.u32(count)
        a.branch("0f89", "admit.max" + str(axis))
        a.emit("31c0bb02000000")
        a.label("admit.max" + str(axis))
        a.emit("8b8a"); a.u32(scroll)
        a.emit("85c9790231c939c17e0289c1898a"); a.u32(scroll)
    a.emit("895d1c89ec619dc3")
    a.label("admit.reject")
    a.emit("c7451c0000000089ec619dc3")

    a.label("bounded_full")
    a.emit("9c6089e583ec18837d1c01")
    a.branch("0f87", "bounded.reject")
    call("composition_guard")
    a.emit("83f801"); a.branch("0f85", "bounded.reject")
    a.emit("8b15"); a.absolute(clip.GAME_DATA_GLOBAL, "game_data_global")
    a.emit("55"); a.branch("e8", "admit_world"); a.emit("5d83f802")
    a.branch("0f85", "bounded.reject")
    a.emit("a1"); a.absolute(clip.MAP_SURFACE_GLOBAL, "map_surface_global")
    a.emit("8945fc8b88b8000000894df8a1")
    a.absolute(clip.RENDER_DEVICE_GLOBAL, "render_device_global")
    a.emit("8945f4c745f000000000")
    a.label("bounded.row")
    a.emit("c745ec00000000")
    a.label("bounded.column")
    a.emit("8b45ec8b5df031f6")
    call("cell")
    a.emit("83f801"); a.branch("0f84", "bounded.next")
    a.emit("83f802"); a.branch("0f85", "bounded.failed")
    a.label("bounded.next")
    a.emit("ff45ec817dec"); a.u32(layout.ceil_tiles[0]); a.branch("0f8c", "bounded.column")
    a.emit("ff45f0817df0"); a.u32(layout.ceil_tiles[1]); a.branch("0f8c", "bounded.row")
    a.emit("8b45fcc780b8000000"); a.absolute(clip.MEMORY_VTABLE, "memory_vtable")
    call("draw_frame")
    a.emit("83f801"); a.branch("0f85", "bounded.failed")
    call("compose_panel")
    a.emit("83f801"); a.branch("0f85", "bounded.failed")
    a.emit("837d1c00"); a.branch("0f84", "bounded.success")
    a.emit("31c031dbb9"); a.u32(layout.width - 1)
    a.emit("ba"); a.u32(layout.height - 1)
    call("present_map_rect")
    a.emit("83f801"); a.branch("0f85", "bounded.failed")
    a.label("bounded.success")
    a.emit("c7451c01000000"); a.branch("e9", "bounded.restore")
    a.label("bounded.failed")
    a.emit("c7451c00000000")
    a.label("bounded.restore")
    a.emit("8b45fc8b4df88988b80000008b45f4a3")
    a.absolute(clip.RENDER_DEVICE_GLOBAL, "render_device_global")
    a.emit("89ec619dc3")
    a.label("bounded.reject")
    a.emit("c7451c0000000089ec619dc3")
    code = a.finish()
    camera.require(base_va + len(code) < 0x80000000, "bounded helper exceeds x86 range")
    bundle = clip.AdapterBundle(base_va, code, {n: base_va + p for n, p in a.labels.items()},
                                tuple(a.relocations), layout.width, layout.height)
    clip.absolute_relocation_offsets(bundle)
    return bundle


def _gate(kind: str, va: int, reject: int, helper: clip.AdapterBundle):
    a = clip._Assembler(va)
    if kind == "full_redraw":
        a.emit("55")
    _transfer(a, "e8", helper.entries["admit_world"], "bounded_world_admission")
    if kind == "full_redraw":
        a.emit("5d")
    a.emit("85c0")
    _transfer(a, "0f84", reject, "bounded_invalid_world")
    if kind == "full_redraw":
        a.emit("83f801")
        _transfer(a, "0f84", va + camera.GATE_SIZE, "bounded_native_full_continuation")
        a.emit("8b451c55")
        _transfer(a, "e8", helper.entries["bounded_full"], "bounded_small_world_full")
        a.emit("5d89451c89ec619dc3")
    else:
        _transfer(a, "e9", va + camera.GATE_SIZE, "bounded_initial_continuation")
    camera.require(len(a.code) <= camera.GATE_SIZE, "bounded dispatch exceeds existing guard")
    a.code.extend(b"\x90" * (camera.GATE_SIZE - len(a.code)))
    return a.finish(), a.relocations


def _parent_parts(base: bytes, parent: bytes, metadata: dict[str, Any]):
    image = pe.inspect_pe(parent)
    code_va, code_size = metadata["code_va"], metadata["code_bytes"]
    start = image.file_offset(code_va - image.image_base, code_size)
    code = parent[start:start + code_size]
    relocs = tuple(pe.CodeRelocation(**row) for row in metadata["relocations"])
    hook_relocs = metadata.get("hook_relocations", [])
    hooks = tuple(pe.HookPatch(row["offset"], row["rva"], row["va"], bytes.fromhex(row["old_hex"]),
        bytes.fromhex(row["new_hex"]), row["purpose"], tuple(pe.CodeRelocation(field["offset"], field["kind"],
        field["target"], field["purpose"]) for field in hook_relocs if field["hook_va"] == row["va"]))
        for row in metadata.get("hooks", []))
    removed = tuple(row["rva"] for row in metadata.get("removed_highlow", []))
    replay = pe._extend_verified_image(base, code=code, code_va=code_va, relocations=relocs,
        hooks=hooks, removed_highlow_rvas=removed, binding={})
    camera.require(replay.image == parent, "parent reconstruction differs from authenticated candidate")
    return code, relocs, hooks, removed


def _extend_verified_parent(base: bytes, parent: bytes, metadata: dict[str, Any], resolution: str,
                            binding: dict[str, Any]):
    _, camera_report = camera._upgrade_verified_parent(parent, metadata, resolution)
    code, relocs, hooks, removed = _parent_parts(base, parent, metadata)
    code_va = metadata["code_va"]
    layout = FramedViewport(*map(int, resolution.split("x")))
    entries = metadata["entry_vas"]
    camera.require(all(type(entries.get(n)) is int and code_va <= entries[n] < code_va + len(code)
                       for n in HELPERS), "bounded helper targets lie outside authenticated payload")
    helper = emit_helpers(layout, base_va=code_va + len(code), entries=entries)
    new_code = bytearray(code + helper.code)
    new_relocs = list(relocs) + [replace(r, offset=r.offset + len(code)) for r in helper.relocations]
    edits = []
    for row in camera_report["edits"]:
        offset = row["va"] - code_va
        replacement, fields = _gate(row["name"], row["va"], row["reject_va"], helper)
        camera.require(new_code[offset:offset + camera.GATE_SIZE].hex() == row["old_hex"], "old guard changed")
        new_code[offset:offset + camera.GATE_SIZE] = replacement
        new_relocs.extend(replace(r, offset=r.offset + offset) for r in fields)
        edits.append(dict(row, new_hex=replacement.hex(), group="framed-bounded-paint", stage=STAGE,
                          rationale="Admit bounded world/camera; route small full redraws through checked cell traversal."))
    result = pe._extend_verified_image(base, code=bytes(new_code), code_va=code_va, relocations=new_relocs,
        hooks=hooks, removed_highlow_rvas=removed, binding={**binding, "stage": STAGE, "resolution": resolution})
    report = dict(result.metadata, schema="clash95_bounded_paint_v1", parent_sha256=camera.sha(parent),
        parent_stage=camera.PARENT_STAGE, parent_payload_sha256=camera.sha(code),
        payload_edits=edits, appended_helper={"va": helper.base_va, "bytes": len(helper.code),
        "sha256": camera.sha(helper.code), "entry_vas": helper.entries},
        entry_vas={**entries, **{"bounded." + n: va for n, va in helper.entries.items()}},
        camera_clamp=True, bounded_small_world_paint=True, minimap_viewport=True,
        full_tiles=list(layout.full_tiles), ceil_tiles=list(layout.ceil_tiles),
        small_world_input_enabled=False, parent_probe_reusable=False,
        validation_stage_only=True, game_runtime_executed=False, manual_input_proof=False, promotion_ready=False,
        limits="Rendering-only experimental stage. Native full loop retained for fitting worlds; small worlds use guarded cells. Existing small-world mouse rejection remains. Old probes/evidence do not apply. No gameplay or screen-transition qualification.")
    return result.image, report


def build_candidate(original: bytes, resolution: str):
    camera.require(type(original) is bytes and camera.sha(original) == pe.ORIGINAL_SHA256, "unknown original executable SHA-256")
    camera.require(camera.sha(Path(camera.__file__).read_bytes()) == CAMERA_SOURCE_SHA256, "reviewed camera source changed")
    status = camera.source_status()
    builder = importlib.import_module("build_framed_candidate")
    camera.require(Path(builder.__file__).resolve() == ROOT / "tools/build_framed_candidate.py", "unexpected parent builder")
    parent, metadata, _ = builder.build_candidate(original, resolution, minimap_viewport=True)
    from . import framed_recipe as recipe
    width, height = map(int, resolution.split("x"))
    base = recipe.canonical_candidate(original, width, height).image
    binding = pe._bind_framed_candidate(original, base, expected_candidate_sha256=camera.sha(base),
        expected_patcher_sha256=status["checks"]["src/patcher/patch_clash95_hd.py"]["actual_sha256"],
        expected_recipe_sha256=status["checks"]["src/patcher/framed_recipe.py"]["actual_sha256"],
        expected_geometry_sha256=status["checks"]["src/patcher/framed_viewport.py"]["actual_sha256"], resolution=resolution)
    image, report = _extend_verified_parent(base, parent, metadata, resolution, binding)
    report["source_sha256"] = {"tools/build_framed_candidate.py": status["builder_sha256"],
        **{n: r["actual_sha256"] for n, r in status["checks"].items()},
        "src/patcher/framed_camera.py": CAMERA_SOURCE_SHA256,
        "src/patcher/framed_bounded_paint.py": camera.sha(Path(__file__).read_bytes())}
    return image, report
