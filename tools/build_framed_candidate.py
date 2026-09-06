#!/usr/bin/env python3
"""Build the guarded four-border validation candidate; never start a runtime.

The protected recipe stays unchanged. This explicit builder binds a separate
framed scalar base, every installed hook, all extension bytes and relocations.
File output uses exclusive creation outside the repository and original.
"""
from __future__ import annotations

import argparse
from dataclasses import replace
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
from src.patcher import partial_tile_clip as clip
from src.patcher import partial_tile_hooks as hooks
from src.patcher import initial_map_paint as initial
from src.patcher import framed_recipe as recipe
from src.patcher import framed_presentation as presentation
from src.patcher import framed_input as inputs
from src.patcher import pe_extension as pe
from src.patcher.framed_viewport import FramedViewport
from build_partial_tile_candidate import FRAMED_STAGE as STAGE, make_probe

# Frozen after source review and the focused emitted-x86 fixtures. Any source
# change requires review and explicit repinning before candidate file output.
PINNED_SOURCES = {
    "src/patcher/patch_clash95_hd.py": "09f383ce7479d4be4c94017e347d6857acbcd364542fd2b72bafe3e1f0924db1",
    "src/patcher/partial_tile_clip.py": "92421c123a75bef119bfa93b438f813ec18dcb073699327cf15b7a1b884bcfad",
    "src/patcher/partial_tile_hooks.py": "71ce9390a3018c80811a1e57b36dc47b59928cb3d9deec364e9b195f94465419",
    "src/patcher/initial_map_paint.py": "79e6d6d180a115b2b59e98600038fa3a31707a373c0095489bb706182078ba91",
    "src/patcher/pe_extension.py": "4d66e7fa3bf17c6260fffaefc8d4e4e8da0ba76ceea7746858c52299f74d7c27",
    "src/patcher/framed_viewport.py": "1d5bc64777cf01c68f587bc3fee2dc7d5024696bd6b1712dab4e6e78f78c4c42",
    "src/patcher/framed_recipe.py": "0c694cdec4071efe94276a334615f7c16cfe9523e86e454ec8db44dc986fc54d",
    "src/patcher/four_sided_frame.py": "433fd27fb8afda4a12f5539604f722f18bf8d37885125e30ee9cfb948926c2a9",
    "src/patcher/framed_full_paint.py": "d496fe9eca8ebe02c34f5680aee4fe2683b4b3849d65fe5f4e5f17b4e118c91a",
    "src/patcher/framed_presentation.py": "70619f5c25faac66a668c19f989e55a8d4e4662c24c78286e16c233cc564ab6d",
    "src/patcher/framed_input.py": "a2557f1ca7caf23a957a21bf747ac23d875b27e7706de26d463b98ae221ce810",
    "tools/build_partial_tile_candidate.py": "44cf9eddf53a1597cd49cc3210f56a6f6994fbaf14c77281db7082a7d326e62d",
    "tools/partial_tile_trace_probe.py": "a20512fa49cc86db67a486f9202d4efa3f9f3745005d11220bf6097661a44729",
}
MINIMAP_SOURCE = "src/patcher/framed_minimap.py"
MINIMAP_SOURCE_SHA256 = "90a345f1080f0b69107f99d1ec1687d1a28faab2e72e5daae6bee467fa31a6d7"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build_candidate(original: bytes, resolution: str, *, minimap_viewport: bool = False):
    if type(minimap_viewport) is not bool:
        raise ValueError("minimap_viewport must be an explicit boolean")
    sources = dict(PINNED_SOURCES)
    if minimap_viewport:
        sources[MINIMAP_SOURCE] = MINIMAP_SOURCE_SHA256
    for name, expected in sources.items():
        if sha((ROOT / name).read_bytes()) != expected:
            raise ValueError(f"reviewed framed source changed: {name}")
    clip.verify_original(original)
    profile = recipe.patcher.parse_resolution(resolution)
    if profile.key != resolution:
        raise ValueError("resolution must use canonical WxH spelling")
    layout = FramedViewport(profile.width, profile.height)
    base = recipe.canonical_candidate(original, layout.width, layout.height)
    bundle = initial.emit_hook_bundle(original, base.image, base_va=pe.extension_code_va(original),
                                     width=layout.width, height=layout.height, layout=layout)
    frame = presentation.emit_framed_presentation(original, base_va=bundle.base_va + len(bundle.code),
                                                  width=layout.width, height=layout.height)
    mouse = inputs.emit_input_bundle(original, base_va=frame.base_va + len(frame.code),
                                     width=layout.width, height=layout.height)
    additions = [("frame_presentation", frame), ("framed_input", mouse)]
    minimap = None
    if minimap_viewport:
        from src.patcher import framed_minimap
        minimap = framed_minimap.emit_minimap_bundle(
            original, base_va=mouse.base_va + len(mouse.code), width=layout.width,
            height=layout.height, clipped_vtable_va=bundle.entries["clipped_vtable"])
        additions.append(("framed_minimap", minimap))
    code = bundle.code + b"".join(addition.code for _, addition in additions)
    relocations = list(bundle.relocations)
    entries = dict(bundle.entries)
    for prefix, addition in additions:
        relocations.extend(replace(reloc, offset=reloc.offset + addition.base_va - bundle.base_va)
                           for reloc in addition.relocations)
        entries.update({f"{prefix}.{name}": va for name, va in addition.entries.items()})
    jump_sites = bundle.hook_sites + frame.hook_sites
    if minimap is not None:
        jump_sites += minimap.hook_sites
    explicit_sites = mouse.hook_sites + mouse.scalar_patches
    bundle = replace(bundle, code=code, entries=entries, relocations=tuple(relocations),
                     hook_sites=jump_sites + explicit_sites)
    clip.absolute_relocation_offsets(bundle)
    patches = []
    for site in jump_sites:
        jump = b"\xe9" + struct.pack("<i", site.entry_va - (site.va + 5))
        new = jump + b"\x90" * (len(site.old_bytes) - len(jump))
        patches.append(pe.HookPatch(site.offset, site.rva, site.va, site.old_bytes, new,
            f"four-border {site.name}; guarded ordinary map with native fallback",
            (pe.CodeRelocation(1, "rel32", site.entry_va, f"{site.name} branch"),)))
    for site in explicit_sites:
        patches.append(pe.HookPatch(site.offset, site.rva, site.va, site.old_bytes, site.new_bytes,
                                    f"four-border input {site.name}", site.relocations))
    removed = tuple(va - hooks.IMAGE_BASE for site in bundle.hook_sites for va in site.removed_highlow_vas)
    result = pe.extend_framed_candidate_with_hooks(
        original, base.image, expected_candidate_sha256=sha(base.image),
        expected_patcher_sha256=PINNED_SOURCES["src/patcher/patch_clash95_hd.py"],
        expected_recipe_sha256=PINNED_SOURCES["src/patcher/framed_recipe.py"],
        expected_geometry_sha256=PINNED_SOURCES["src/patcher/framed_viewport.py"],
        resolution=resolution, validation_stage=STAGE, code=code, code_va=bundle.base_va,
        relocations=bundle.relocations, hooks=patches, removed_highlow_rvas=removed)
    metadata = dict(result.metadata)
    metadata.update(generated_at=datetime.now(timezone.utc).isoformat(), source_sha256=sources,
                    installed_hook_names=[site.name for site in bundle.hook_sites],
                    status_vas=bundle.status_vas, initial_status_vas=bundle.initial_status_vas,
                    initial_paint_contract=bundle.initial_contract, initial_paint=True,
                    layout_contract=bundle.layout_contract, framed_validation=True,
                    frame_presentation_status_vas=frame.status_vas,
                    frame_presentation_contract=frame.native_contract, entry_vas=bundle.entries,
                    extension_payload_sha256=sha(code), extension_payload_size=len(code),
                    runtime_executed=False, validation_stage_only=True, promotion_ready=False,
                    manual_input_proof=False,
                    supported_composition="Guarded ordinary map and AI banner only; unsupported modal/army owners use native fallback and are not framed HD proof")
    if minimap is not None:
        metadata.update(minimap_viewport=True, minimap_viewport_contract=minimap.native_contract,
                        minimap_viewport_status_vas=minimap.status_vas,
                        minimap_viewport_revision="framed_minimap_actual_terrain_v1")
    return result.image, metadata, make_probe(result.image, bundle)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--resolution", required=True)
    parser.add_argument("--report-json", type=Path)
    parser.add_argument("--probe-out", type=Path)
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--minimap-viewport", action="store_true",
                        help="add the source-bound minimap outline for actual framed terrain pixels")
    args = parser.parse_args()
    build_options = {"minimap_viewport": True} if args.minimap_viewport else {}
    if args.preflight:
        candidate, metadata, _ = build_candidate(args.original.read_bytes(), args.resolution, **build_options)
        print(json.dumps({"stage": STAGE, "resolution": args.resolution,
                          "candidate_sha256": sha(candidate), "preflight_passed": True,
                          "source_sha256": metadata["source_sha256"], "runtime_executed": False}))
        return 0
    if not all((args.output, args.report_json, args.probe_out)):
        parser.error("output, report-json and probe-out are required unless using preflight")
    outputs = [args.output.resolve(), args.report_json.resolve(), args.probe_out.resolve()]
    if len(set(outputs)) != 3 or any(p == args.original.resolve() or p.is_relative_to(ROOT) for p in outputs):
        parser.error("distinct output artifacts must stay outside the repository and original")
    if not outputs[0].is_relative_to(Path("C:/ClashTests").resolve()) or outputs[0].suffix.lower() != ".exe":
        parser.error("candidate must be a distinctly named .exe under C:/ClashTests")
    if any(p.exists() for p in outputs):
        parser.error("refusing to overwrite an existing artifact")
    candidate, metadata, probe = build_candidate(args.original.read_bytes(), args.resolution, **build_options)
    for path in outputs:
        path.parent.mkdir(parents=True, exist_ok=True)
    with outputs[0].open("xb") as stream:
        stream.write(candidate)
    with outputs[1].open("x", encoding="utf-8") as stream:
        json.dump(metadata, stream, indent=2)
        stream.write("\n")
    with outputs[2].open("x", encoding="utf-8") as stream:
        stream.write(probe)
    print(json.dumps({"stage": STAGE, "candidate_sha256": sha(candidate),
                      "output": str(outputs[0]), "runtime_executed": False}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
