#!/usr/bin/env python3
"""Build a separate native-canvas validation image without starting a runtime.

The entire previous framed candidate is reconstructed before adding six modal
hooks, RX code, and a separate zeroed RW state page. Original and prior recipe
bytes remain independently reproducible. This does not establish modal input,
visual correctness, lifecycle runtime evidence, or promotion readiness.
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
from src.patcher import framed_modal_canvas as canvas
from src.patcher import pe_extension as pe
from src.patcher import pe_modal_extension as extension
from build_partial_tile_candidate import make_probe as make_base_probe

STAGE = extension.STAGE
BASE_STAGE = extension.BASE_STAGE
REVISION = "framed_owned_native_modal_canvas_v1"
CANDIDATE_ROOT = Path("C:/ClashTests")
CAPTURE_ROOT = Path("C:/ClashCaptures")
ORIGINAL_PATH = Path("C:/Clash/clash95.exe")
# Deliberately fails closed until each new source has completed its independent
# fixtures and review. No source-pin override is accepted by API or CLI.
PINNED_SOURCES = {
    "src/patcher/framed_modal_canvas.py": "567b025520184a99f1f4f44b23a879ef9c729dcf2917dfa03a277c018cb20054",
    "src/patcher/pe_modal_extension.py": "92405bf37ab887242982f2748f120aff471006b73a8cb929db39f06d1ca7eee9",
}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def verify_sources() -> dict[str, str]:
    for name, expected in PINNED_SOURCES.items():
        pe._identity((ROOT / name).read_bytes(), expected, f"reviewed modal source {name}")
    return dict(PINNED_SOURCES)


def _checked_lines(spans: list[tuple[int, bytes]]) -> list[str]:
    conditions = []
    for va, data in spans:
        for offset in range(0, len(data), 2):
            part = data[offset:offset + 2]
            reader = "wo" if len(part) == 2 else "by"
            conditions.append(f"{reader}({va + offset:08x}) != {int.from_bytes(part, 'little'):x}")
    return [".if (" + " | ".join(f"({c})" for c in conditions[start:start + 60])
            + ") { .echo MCANVAS_CONTRACT_FAIL; q }" for start in range(0, len(conditions), 60)]


def _initial_probe(candidate: bytes, base: bytes, base_metadata: dict, modal, extension_metadata: dict) -> str:
    """Preserve the map observers with new headers, identity and modal checks.

    Only source-generated metadata is supplied internally. The complete old
    payload remains byte-identical. This is a load-time probe: its zero-state
    checks must run before entering the first castle, never on an active modal.
    """
    width, height = map(int, base_metadata["resolution"].split("x"))
    code_va, size = base_metadata["code_va"], base_metadata["extension_payload_size"]
    offset = pe.inspect_pe(base).file_offset(code_va - 0x400000, size)
    old_code = base[offset:offset + size]
    new_offset = pe.inspect_pe(candidate).file_offset(code_va - 0x400000, size)
    if candidate[new_offset:new_offset + size] != old_code:
        raise ValueError("modal integration changed the initial/framed code payload")
    bundle = SimpleNamespace(
        base_va=code_va, code=old_code, width=width, height=height,
        entries=base_metadata["entry_vas"], status_vas=base_metadata["status_vas"],
        initial_status_vas=base_metadata["initial_status_vas"],
        layout_contract=base_metadata["layout_contract"],
        hook_sites=tuple(SimpleNamespace(va=row["va"], offset=row["offset"],
                                        old_bytes=bytes.fromhex(row["old_hex"]))
                         for row in base_metadata["hooks"]))
    probe = make_base_probe(candidate, bundle)
    old_contract = f".echo PTILE_CONTRACT_PASS stage={BASE_STAGE} resolution={width}x{height} candidate_sha256={sha(candidate)}"
    new_contract = old_contract.replace(f"stage={BASE_STAGE} ", f"stage={STAGE} ", 1)
    if probe.splitlines().count(old_contract) != 1:
        raise ValueError("the canonical initial-map probe contract changed")
    loaded = pe.inspect_pe(candidate)
    # Full section headers bind flags/strides/storage, including RX versus RW.
    # The merged relocation directory is static and lives in non-discardable
    # .hdmodal storage. Authenticate its pair and complete table as well.
    spans = [(0x400000 + section.header_offset,
              candidate[section.header_offset:section.header_offset + 40])
             for section in loaded.sections]
    spans.extend((site.va, site.new) for site in modal.hook_sites)
    spans.extend(((modal.base_va, modal.code), (modal.state_va, bytes(extension.STATE_BYTES))))
    # Preserve the authenticated old wrapper tails used by inactive fallback.
    # Their first six bytes now contain our hook, so read the final installed
    # bytes over the complete source-authenticated span, not the old prefix.
    for row in extension_metadata["authenticated_legacy_continuations"]:
        offset = loaded.file_offset(row["entry_va"] - 0x400000, row["span_bytes"])
        spans.append((row["entry_va"], candidate[offset:offset + row["span_bytes"]]))
    relocation_offset = loaded.file_offset(loaded.relocation_rva, loaded.relocation_size)
    spans.extend(((0x400000 + loaded.optional_offset + 136,
                   candidate[loaded.optional_offset + 136:loaded.optional_offset + 144]),
                  (0x400000 + loaded.relocation_rva,
                   candidate[relocation_offset:relocation_offset + loaded.relocation_size])))
    checks = _checked_lines(spans)
    checks.append(f".echo MCANVAS_CONTRACT_PASS stage={STAGE} resolution={width}x{height} "
                  f"candidate_sha256={sha(candidate)} revision={REVISION} "
                  f"state={modal.state_va:08x} state_bytes={extension.STATE_BYTES}")
    checks.append(".echo MCANVAS_SCOPE owned_castle_canvas_only manual_input_proof=false promotion_ready=false")
    # Every modal loaded-byte check precedes all initial trace breakpoints.
    return probe.replace(old_contract, "\n".join(checks + [new_contract]), 1)


def build_candidate(original: bytes, resolution: str, *, minimap_viewport: bool = False):
    sources = verify_sources()
    if type(minimap_viewport) is not bool:
        raise ValueError("minimap_viewport must be an explicit boolean")
    pe._identity(original, pe.ORIGINAL_SHA256, "original")
    base, base_metadata, base_sources = extension._reconstruct(original, resolution, minimap_viewport)
    previous = pe.inspect_pe(base)
    code_va = previous.image_base + previous.image_size
    state_va = code_va + extension.CODE_RESERVATION
    width, height = map(int, resolution.split("x"))
    modal = canvas.emit_modal_canvas(original, base, base_va=code_va, state_va=state_va,
                                     width=width, height=height)
    if len(modal.hook_sites) != 6 or len({site.va for site in modal.hook_sites}) != 6:
        raise ValueError("all six distinct modal hooks are required")
    if modal.state_size > extension.STATE_BYTES or modal.candidate_sha256 != sha(base):
        raise ValueError("modal emitter state or candidate binding differs")
    # These six sites replace relative calls/jumps or register pushes; none
    # displaces an absolute operand. The allocator independently rejects a
    # missing removal should that contract ever change.
    result = extension.extend_framed_candidate_with_modal(
        original, base, expected_candidate_sha256=sha(base), resolution=resolution,
        minimap_viewport=minimap_viewport, validation_stage=STAGE,
        code=modal.code, code_va=modal.base_va, state_va=modal.state_va,
        relocations=modal.relocations, hooks=modal.hook_sites, removed_highlow_rvas=())
    probe = _initial_probe(result.image, base, base_metadata, modal, result.metadata)
    metadata = dict(result.metadata)
    metadata.update(
        schema="clash95_framed_modal_candidate_v1", generated_at=datetime.now(timezone.utc).isoformat(),
        source_sha256=base_sources | sources,
        builder_sha256=sha(Path(__file__).read_bytes()),
        base_candidate_sha256=sha(base), base_candidate=base_metadata,
        modal_native_canvas=True, modal_native_canvas_revision=REVISION,
        modal_canvas_contract=modal.source_contract,
        modal_state_offsets=modal.state_offsets, modal_state_size=modal.state_size,
        modal_entry_vas=modal.entries, modal_observer_vas=modal.observer_vas,
        installed_hook_names=[site.purpose for site in modal.hook_sites],
        initial_probe_sha256=sha(probe.encode("utf-8")),
        initial_probe_contract=dict(stage=STAGE, preserved_map_recipe_stage=BASE_STAGE,
                                    source_recipe_bytes_unchanged=True, requires_new_stage_consumer=True),
        validation_stage_only=True, installation_ready=False,
        runtime_executed=False, manual_input_proof=False, promotion_ready=False,
        supported_composition="Owned native castle canvas and centered physical memory mirror; "
                              "no generic modal, primary-only layer, input or lifecycle runtime proof")
    # Refuse file output if either independently reviewed new source changed
    # while the complete candidate was being generated.
    verify_sources()
    return result.image, metadata, probe


def _outputs(args, parser) -> list[Path]:
    if not all((args.output, args.report_json, args.probe_out)):
        parser.error("output, report-json and probe-out are required unless using preflight")
    paths = [p.resolve() for p in (args.output, args.report_json, args.probe_out)]
    protected = {args.original.resolve(), ORIGINAL_PATH.resolve()}
    if len(set(paths)) != 3 or any(p in protected or p.is_relative_to(ROOT) for p in paths):
        parser.error("distinct artifacts must stay outside the repository and original")
    if not paths[0].is_relative_to(CANDIDATE_ROOT.resolve()) or paths[0].suffix.lower() != ".exe":
        parser.error("candidate must be a distinctly named .exe under C:/ClashTests")
    roots = (CANDIDATE_ROOT.resolve(), CAPTURE_ROOT.resolve())
    if any(not any(p.is_relative_to(root) for root in roots) for p in paths[1:]):
        parser.error("reports and probes must stay under C:/ClashTests or C:/ClashCaptures")
    if paths[1].suffix.lower() != ".json" or paths[2].suffix.lower() != ".cdb":
        parser.error("report and probe must use .json and .cdb extensions")
    if any(p.exists() for p in paths):
        parser.error("refusing to overwrite an existing artifact")
    return paths


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original", required=True, type=Path)
    parser.add_argument("--resolution", required=True)
    parser.add_argument("--minimap-viewport", action="store_true")
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--report-json", type=Path)
    parser.add_argument("--probe-out", type=Path)
    args = parser.parse_args()
    if args.preflight and any((args.output, args.report_json, args.probe_out)):
        parser.error("preflight accepts no output paths")
    paths = [] if args.preflight else _outputs(args, parser)
    candidate, metadata, probe = build_candidate(args.original.read_bytes(), args.resolution,
                                                 minimap_viewport=args.minimap_viewport)
    if args.preflight:
        print(json.dumps(dict(stage=STAGE, candidate_sha256=sha(candidate), resolution=args.resolution,
                              source_sha256=metadata["source_sha256"], preflight_passed=True,
                              runtime_executed=False, promotion_ready=False)))
        return 0
    for path in paths:
        path.parent.mkdir(parents=True, exist_ok=True)
    # Acquire all three files exclusively before writing any candidate bytes.
    # A racing path creation fails closed, preserving any already-created empty
    # artifacts for inspection rather than cleaning up somebody else's files.
    with ExitStack() as stack:
        streams = [stack.enter_context(path.open("xb")) for path in paths]
        streams[0].write(candidate)
        streams[1].write((json.dumps(metadata, indent=2) + "\n").encode("utf-8"))
        streams[2].write(probe.encode("utf-8"))
    print(json.dumps(dict(stage=STAGE, candidate_sha256=sha(candidate), output=str(paths[0]),
                          runtime_executed=False, promotion_ready=False)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
