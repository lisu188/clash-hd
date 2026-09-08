#!/usr/bin/env python3
"""Build a distinct, unpromoted partial-tile candidate from the known original.

No runtime is started. Candidate and full byte-edit metadata stay outside the
repository. The stable patcher and its default stage remain unchanged.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.patcher import partial_tile_clip as clip
from src.patcher import partial_tile_hooks as hooks
from src.patcher import patch_clash95_hd as patcher
from src.patcher import pe_extension as pe

BASE_STAGE = hooks.COMBINED_STAGE
STAGE = BASE_STAGE.removesuffix("-validation") + "-partialtiles-validation"
INITIAL_STAGE = STAGE.removesuffix("-validation") + "-initialpaint-validation"
FRAMED_STAGE = INITIAL_STAGE.removesuffix("-validation") + "-framed-validation"
INITIAL_SOURCE_SHA256 = "79e6d6d180a115b2b59e98600038fa3a31707a373c0095489bb706182078ba91"
PINNED_SOURCES = {
    "src/patcher/patch_clash95_hd.py": "05f31359f93a0eb0b319679ee524b21c05cd3e86e485b7ebb92afc8e6da29f31",
    "src/patcher/partial_tile_clip.py": "92421c123a75bef119bfa93b438f813ec18dcb073699327cf15b7a1b884bcfad",
    "src/patcher/partial_tile_hooks.py": "71ce9390a3018c80811a1e57b36dc47b59928cb3d9deec364e9b195f94465419",
    "src/patcher/pe_extension.py": "4d66e7fa3bf17c6260fffaefc8d4e4e8da0ba76ceea7746858c52299f74d7c27",
}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build_candidate(original: bytes, resolution: str, *, initial_paint: bool = False):
    for name, expected in PINNED_SOURCES.items():
        if sha((ROOT / name).read_bytes()) != expected:
            raise ValueError(f"reviewed source changed: {name}")
    clip.verify_original(original)
    profile = patcher.parse_resolution(resolution)
    if profile.key != resolution:
        raise ValueError("resolution must use canonical WxH spelling")
    recipe = patcher.select_patches_for(BASE_STAGE, profile)
    combined = patcher.apply_patches(original, recipe)
    emitter = hooks.emit_hook_bundle
    sources = dict(PINNED_SOURCES)
    stage = STAGE
    if initial_paint:
        from src.patcher import initial_map_paint as initial
        # Pin this independently reviewed adapter before enabling file output.
        initial_source = "src/patcher/initial_map_paint.py"
        if sha((ROOT / initial_source).read_bytes()) != INITIAL_SOURCE_SHA256:
            raise ValueError("reviewed initial-paint source changed")
        sources[initial_source] = INITIAL_SOURCE_SHA256
        emitter = initial.emit_hook_bundle
        stage = INITIAL_STAGE
    bundle = emitter(original, combined, base_va=pe.extension_code_va(original),
                     width=profile.width, height=profile.height)
    patches = []
    for site in bundle.hook_sites:
        jump = b"\xe9" + struct.pack("<i", site.entry_va - (site.va + 5))
        new = jump + b"\x90" * (len(site.old_bytes) - len(jump))
        patches.append(pe.HookPatch(site.offset, site.rva, site.va, site.old_bytes, new,
            f"partial-tile {site.name} trampoline; preserve native fallback and caller state",
            (pe.CodeRelocation(1, "rel32", site.entry_va, f"{site.name} branch"),)))
    result = pe.extend_combined_candidate_with_hooks(
        original, combined, expected_candidate_sha256=sha(combined),
        expected_patcher_sha256=PINNED_SOURCES["src/patcher/patch_clash95_hd.py"],
        stage=BASE_STAGE, validation_stage=stage, resolution=resolution,
        code=bundle.code, code_va=bundle.base_va, relocations=bundle.relocations,
        hooks=patches, removed_highlow_rvas=tuple(
            va - hooks.IMAGE_BASE for site in bundle.hook_sites for va in site.removed_highlow_vas))
    metadata = dict(result.metadata)
    metadata.update(generated_at=datetime.now(timezone.utc).isoformat(),
                    source_sha256=sources,
                    installed_hook_names=[site.name for site in bundle.hook_sites],
                    status_vas=bundle.status_vas, runtime_executed=False,
                    validation_stage_only=True, promotion_ready=False,
                    supported_composition="Guarded ordinary map and AI banner; unsupported modal/army owners fall back to native and are not HD proof")
    if initial_paint:
        metadata.update(initial_status_vas=bundle.initial_status_vas,
                        initial_paint_contract=bundle.initial_contract,
                        initial_paint=True,
                        initial_paint_scope="First PlayGame entry after UI resources, admitted ordinary map only")
    return result.image, metadata, make_probe(result.image, bundle)


def make_probe(candidate: bytes, bundle) -> str:
    image = pe.inspect_pe(candidate)
    initial = getattr(bundle, "initial_status_vas", None)
    layout = getattr(bundle, "layout_contract", {})
    framed = bool(layout)
    if framed and (not initial or layout.get("full_status_to_caller_before_call") != 148):
        raise ValueError("framed probe requires the reviewed initial/full-stack contract")
    stage = FRAMED_STAGE if framed else INITIAL_STAGE if initial else STAGE
    # Validate loaded PE and installed jumps before arming any diagnostic BPs.
    spans = [(0x400000, b"MZ"), (0x400000 + image.pe_offset, b"PE\0\0"),
             (0x400000 + image.pe_offset + 6, struct.pack("<H", len(image.sections))),
             (0x400000 + image.optional_offset + 56, struct.pack("<I", image.image_size))]
    # PlayGame installs the ordinary map owner before this native join, then
    # calls UI_SetCurrentPlayer. Earlier full redraws belong to initialization.
    ready_va = initial["ready"] if initial else 0x40B88A
    ready_bytes = (bytes.fromhex("b801000000e8") + struct.pack("<i", 0x418700 - (ready_va + 10))
                   if initial else bytes.fromhex("a1ec025200"))
    ready_offset = clip.file_offset(candidate, ready_va, len(ready_bytes))
    if candidate[ready_offset:ready_offset + len(ready_bytes)] != ready_bytes:
        raise ValueError("native map-owner readiness join changed")
    spans.append((ready_va, ready_bytes))
    if initial:
        # Bind every byte of the new adapter and its shared native UI join.
        entry = bundle.base_va if framed else bundle.entries["initial_paint_admission"]
        spans.append((entry, bundle.code[entry - bundle.base_va:]))
        shared = bytes.fromhex("a1ec025200e8dc7a0100")
        shared_offset = clip.file_offset(candidate, 0x40B88A, len(shared))
        if candidate[shared_offset:shared_offset + len(shared)] != shared:
            raise ValueError("initial paint changed the shared next-player UI join")
        spans.append((0x40B88A, shared))
        update_bytes = bytes.fromhex("51525583ec708b15f002520085d2740f")
        update_offset = clip.file_offset(candidate, 0x406FA0, len(update_bytes))
        if candidate[update_offset:update_offset + len(update_bytes)] != update_bytes:
            raise ValueError("initial paint capture update boundary changed")
        spans.append((0x406FA0, update_bytes))
    # Authenticate the native admission/early-return path and the emitted
    # composition-guard call before observing offscreen no-op fallbacks.
    native_offset = clip.file_offset(candidate, 0x418A98, 0x6B)
    native_admission = candidate[native_offset:native_offset + 0x6B]
    if native_admission[-9:] != bytes.fromhex("83c4085d5f5e595bc3"):
        raise ValueError("native incremental epilogue changed")
    spans.append((0x418A98, native_admission))
    guard_va = bundle.entries["cell_composed"] + 12
    guard_offset = clip.file_offset(candidate, guard_va - 12, 15)
    guard_prefix = candidate[guard_offset:guard_offset + 15]
    if (guard_prefix[:8] != bytes.fromhex("6089e583ec0455e8") or
            guard_prefix[12:] != bytes.fromhex("5d85c0") or
            guard_va + struct.unpack_from("<i", guard_prefix, 8)[0] != bundle.entries["composition_guard"]):
        raise ValueError("emitted cell composition guard call changed")
    spans.append((guard_va - 12, guard_prefix))
    for site in bundle.hook_sites:
        spans.append((site.va, candidate[site.offset:site.offset + len(site.old_bytes)]))
    conditions = []
    for va, data in spans:
        for offset in range(0, len(data), 2):
            part = data[offset:offset + 2]
            reader = "wo" if len(part) == 2 else "by"
            conditions.append(f"{reader}({va + offset:08x}) != {int.from_bytes(part, 'little'):x}")
    lines = [".echo === Partial-tile validation installed-hook diagnostic ==="]
    chunk_size = 60 if initial else len(conditions)
    for start in range(0, len(conditions), chunk_size):
        lines.append(".if (" + " | ".join(f"({c})" for c in conditions[start:start + chunk_size])
                     + ") { .echo PTILE_CONTRACT_FAIL; q }")
    lines.extend([
        f".echo PTILE_CONTRACT_PASS stage={stage} resolution={bundle.width}x{bundle.height} candidate_sha256={sha(candidate)}",
        ".echo PTILE_SCOPE guarded_map_only manual_input_proof=false promotion_ready=false"])
    for bp, (name, va) in enumerate(bundle.status_vas.items(), 70):
        allowed = "(@eax != 1) & (@eax != 2)" if name == "incremental" else "@eax != 1"
        input_probe = ""
        if name == "incremental":
            # PUSHFD/PUSHAD is still intact after the helper returns. Inspect
            # saved input coordinates, not EAX's returned status. Keep the
            # input and status rows for every call. Offscreen status zero
            # additionally requires the guard and native-exit observations;
            # the harness pairs all three using actual thread/stack identity.
            input_probe = (
                '.if (poi(005202e4) == 0) { .echo PTILE_REJECT missing_game_data; q } .else { '
                '.printf \\"PTILE_INCREMENTAL_INPUT tid=%x esp=%p world=(%d,%d) caller=%p gd=%p map=(%d,%d) scroll=(%d,%d) vtable=%p\\\\n\\", '
                '@$tid, @esp, poi(@esp+1c), poi(@esp+14), poi(@esp+24), poi(005202e4), '
                'poi(poi(005202e4)+222e0), poi(poi(005202e4)+222e4), '
                'poi(poi(005202e4)+222e8), poi(poi(005202e4)+222ec), poi(poi(005202e0)+b8); }; '
            )
        rejection = f'.if ({allowed}) {{ .echo PTILE_REJECT {name}; q }}; '
        if name == "incremental":
            gd = "poi(005202e4)"
            wx, wy = "poi(@esp+1c)", "poi(@esp+14)"
            mw, mh = f"poi({gd}+222e0)", f"poi({gd}+222e4)"
            sx, sy = f"poi({gd}+222e8)", f"poi({gd}+222ec)"
            terrain_width = bundle.width - (64 if framed else 32)
            terrain_height = bundle.height - (32 if framed else 16)
            tx, ty = terrain_width // 64, terrain_height // 64
            cx, cy = (terrain_width + 63) // 64, (terrain_height + 63) // 64
            conditions = ["@eax == 0", f"{mw} >= 1", f"{mw} <= 0n100", f"{mh} >= 1", f"{mh} <= 0n100",
                f"{wx} >= 0", f"{wx} < {mw}", f"{wy} >= 0", f"{wy} < {mh}", f"{sx} >= 0", f"{sy} >= 0",
                f"(({mw} >= 0n{tx}) & ({sx} <= {mw}-0n{tx})) | (({mw} < 0n{tx}) & ({sx} == 0))",
                f"(({mh} >= 0n{ty}) & ({sy} <= {mh}-0n{ty})) | (({mh} < 0n{ty}) & ({sy} == 0))",
                f"({wx} < {sx}) | ({wx} >= {sx}+0n{cx}) | ({wy} < {sy}) | ({wy} >= {sy}+0n{cy})",
                "poi(005199d8) == 0040ad40", "poi(0052698c) == 0", "poi(00526990) == 0",
                "poi(00526994) == 0", "poi(005202ec) == 0", "poi(poi(005202e0)+b8) == 0050ee24"]
            noop = " & ".join(f"({condition})" for condition in conditions)
            rejection = (f'.if ({allowed}) {{ .if ({noop}) {{ }} .else {{ .echo PTILE_REJECT incremental; q }}; }}; ')
        lines.append(f'bp{bp} {va:08x} ".if (@$t14 != 0) {{ '
            '.if (poi(005202e0) == 0) { .echo PTILE_REJECT null_surface; q } .else { '
            f'.if ((wo(poi(005202e0)) == 0n{bundle.width}) & (wo(poi(005202e0)+2) == 0n{bundle.height})) {{ '
            + input_probe +
            f'.printf \\"PTILE_STATUS hook={name} status=%d tid=%x esp=%p owner=%p tile=%p post=%p lower=%p player=%d\\\\n\\", '
            '@eax, @$tid, @esp, poi(005199d8), poi(0052698c), poi(00526990), poi(00526994), poi(005202ec); '
            + rejection +
            '} .else { .echo PTILE_REJECT unexpected_surface_size; q }; }; }; gc"')
    lines.extend([
        'bp74 00418afa ".if (poi(005202e4) == 0) { .echo PTILE_REJECT noop_missing_game_data; q } .else { '
        '.if (poi(005202e0) == 0) { .echo PTILE_REJECT noop_null_surface; q } .else { '
        '.printf \\"PTILE_NATIVE_NOOP_EXIT tid=%x esp=%p world=(%d,%d) caller=%p gd=%p map=(%d,%d) scroll=(%d,%d) vtable=%p\\\\n\\", '
        '@$tid, @esp, @eax, @edx, poi(@esp+1c), poi(005202e4), poi(poi(005202e4)+222e0), '
        'poi(poi(005202e4)+222e4), poi(poi(005202e4)+222e8), poi(poi(005202e4)+222ec), poi(poi(005202e0)+b8); }; }; gc"',
        f'bp75 {guard_va:08x} ".printf \\"PTILE_COMPOSITION_GUARD tid=%x esp=%p status=%d world=(%d,%d) cell=(%d,%d) present=%d caller=%p\\\\n\\", '
        '@$tid, @esp, @eax, poi(@esp+0n112), poi(@esp+0n104), poi(@esp+0n36), poi(@esp+0n24), poi(@esp+0n12), poi(@esp+0n120); '
        '.if (@eax != 1) { .echo PTILE_REJECT composition_guard; q }; gc"',
        "bd 70; bd 71; bd 72; bd 74; bd 75",
        f'bp73 {ready_va:08x} ".if (poi(005202e0) == 0) {{ .echo PTILE_REJECT map_ready_null; q }} .else {{ '
        f'.if ((wo(poi(005202e0)) == 0n{bundle.width}) & (wo(poi(005202e0)+2) == 0n{bundle.height}) & (poi(005199d8) == 0040ad40)) {{ '
        '.printf \\"PTILE_MAP_READY owner=%p size=(%d,%d)\\\\n\\", poi(005199d8), wo(poi(005202e0)), wo(poi(005202e0)+2); '
        + ('be 70; be 71; be 72; be 74; be 75; be 77; bd 73; ' if initial else
           'be 70; be 71; be 72; be 74; be 75; bd 73; ') +
        '} .else { .echo PTILE_REJECT map_ready_owner_or_dimensions; q }; }; gc"'])
    if initial:
        lines.extend([
            f'bp76 {initial["admission"]:08x} ".printf \\\"PTILE_INITIAL_ADMISSION status=%d tid=%x esp=%p\\\\n\\\", @eax, @$tid, @esp; '
            '.if (@eax != 1) { .echo PTILE_REJECT initial_paint_admission; q }; gc"',
            f'bp77 {initial["paint_return"]:08x} ".printf \\\"PTILE_INITIAL_RETURN tid=%x esp=%p result=%x\\\\n\\\", @$tid, @esp, @eax; gc"',
            'bd 77',
        ])
        from partial_tile_trace_probe import instrument_probe
        return instrument_probe("\n".join(lines) + "\n", reset_bp=76)
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--resolution", required=True)
    parser.add_argument("--report-json", type=Path)
    parser.add_argument("--probe-out", type=Path)
    parser.add_argument("--preflight", action="store_true", help="Verify/build in memory only; produce no files")
    parser.add_argument("--initial-map-paint", action="store_true", help="Opt into the distinct initial-paint validation stage")
    args = parser.parse_args()
    build_options = {"initial_paint": True} if args.initial_map_paint else {}
    stage = INITIAL_STAGE if args.initial_map_paint else STAGE
    if args.preflight:
        candidate, metadata, _ = build_candidate(args.original.read_bytes(), args.resolution, **build_options)
        print(json.dumps({"stage": stage, "resolution": args.resolution,
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
    # Exclusive creation also closes the exists-check/write race.
    with outputs[0].open("xb") as stream:
        stream.write(candidate)
    with outputs[1].open("x", encoding="utf-8") as stream:
        json.dump(metadata, stream, indent=2)
        stream.write("\n")
    with outputs[2].open("x", encoding="utf-8") as stream:
        stream.write(probe)
    print(json.dumps({"stage": stage, "resolution": args.resolution,
                      "candidate_sha256": sha(candidate), "candidate": str(outputs[0]),
                      "hooks": metadata["installed_hook_names"], "runtime_executed": False}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
