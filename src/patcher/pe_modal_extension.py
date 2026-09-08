"""Pure, source-bound modal code/state allocation atop the complete framed image.

No file output or runtime entry exists here. The public operation reconstructs
the whole framed candidate from fresh pinned modules before adding explicit
hooks, RX code/relocations and a separate zeroed RW page. Declared operand
integrity is checked; instruction semantics and omitted operands need the
emitter's independent tests. Allocation is not installation readiness.
"""
from __future__ import annotations

import ast
from dataclasses import replace
from pathlib import Path
import struct
import sys
import types
import uuid
from typing import Sequence

from . import pe_extension as pe

ROOT = Path(__file__).resolve().parents[2]
BASE_STAGE = ("gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-"
              "presentbounds-minimapright-dynvswitch-combinedui-partialtiles-initialpaint-framed-validation")
STAGE = BASE_STAGE.removesuffix("-validation") + "-modalcanvas-validation"
CODE_RESERVATION = 0x20000
STATE_BYTES = 4096
RW_DATA = 0xC0000040
PINNED_SOURCES = {
    "tools/build_framed_candidate.py": "4178745fabb1e2270efcbdc72bf4999f97b0bca23bdad78db743a5db1b724d7a",
    "tools/build_partial_tile_candidate.py": "44cf9eddf53a1597cd49cc3210f56a6f6994fbaf14c77281db7082a7d326e62d",
    "src/patcher/pe_extension.py": "4d66e7fa3bf17c6260fffaefc8d4e4e8da0ba76ceea7746858c52299f74d7c27",
    "src/patcher/patch_clash95_hd.py": "09f383ce7479d4be4c94017e347d6857acbcd364542fd2b72bafe3e1f0924db1",
}


def _source(name: str, expected: str) -> bytes:
    # Names are supplied only by the pinned builder, never by API callers.
    path = (ROOT / name).resolve()
    pe._require(path.is_relative_to(ROOT) and path == ROOT / name,
                "source path is outside the canonical repository")
    source = path.read_bytes()
    pe._identity(source, expected, f"modal bound source {name}")
    return source


class _LocalImports(ast.NodeTransformer):
    """Isolate only local absolute imports; byte-authenticated logic is unchanged."""
    def __init__(self, prefix: str):
        self.prefix = prefix

    def visit_ImportFrom(self, node):
        if not node.level and node.module:
            if node.module == "src" or node.module.startswith("src."):
                node.module = self.prefix + "." + node.module
            elif node.module in ("build_partial_tile_candidate", "partial_tile_trace_probe"):
                node.module = self.prefix + ".tools." + node.module
        return node


def _reconstruct(original: bytes, resolution: str, minimap_viewport: bool):
    """Fresh source modules, including dependencies; do not trust imported tables.

    The fixed import rewrite merely gives this build a unique package namespace.
    All local sources are compiled from the verified byte snapshots, avoiding
    stale pyc files and modified already-imported recipe modules.
    """
    sources = {name: _source(name, digest) for name, digest in PINNED_SOURCES.items()}
    prefix = "_clash95_modal_binding_" + uuid.uuid4().hex
    names, old_path = [], list(sys.path)

    def package(name, directory):
        mod = types.ModuleType(name)
        mod.__path__ = [str(directory)]
        sys.modules[name] = mod
        names.append(name)

    def module(name, source_name):
        mod = types.ModuleType(name)
        mod.__file__ = str(ROOT / source_name)
        mod.__package__ = name.rpartition(".")[0]
        sys.modules[name] = mod
        names.append(name)
        tree = _LocalImports(prefix).visit(ast.parse(sources[source_name], mod.__file__))
        exec(compile(tree, mod.__file__, "exec"), mod.__dict__)
        return mod

    try:
        package(prefix, ROOT)
        package(prefix + ".src", ROOT / "src")
        package(prefix + ".src.patcher", ROOT / "src/patcher")
        package(prefix + ".tools", ROOT / "tools")
        # Read the builder's literal pins without executing any of its imports.
        tree = ast.parse(sources["tools/build_framed_candidate.py"])
        literals = {node.targets[0].id: ast.literal_eval(node.value)
                    for node in tree.body if isinstance(node, ast.Assign)
                    and isinstance(node.targets[0], ast.Name)
                    and node.targets[0].id in ("PINNED_SOURCES", "MINIMAP_SOURCE", "MINIMAP_SOURCE_SHA256")}
        pins = literals["PINNED_SOURCES"] | PINNED_SOURCES
        if minimap_viewport:
            pins[literals["MINIMAP_SOURCE"]] = literals["MINIMAP_SOURCE_SHA256"]
        sources.update({name: _source(name, digest) for name, digest in pins.items()})
        order = ("framed_viewport", "patch_clash95_hd", "partial_tile_clip", "pe_extension",
                 "framed_recipe", "partial_tile_hooks", "four_sided_frame", "framed_full_paint",
                 "initial_map_paint", "framed_presentation", "framed_input")
        for stem in order + (("framed_minimap",) if minimap_viewport else ()):
            module(prefix + ".src.patcher." + stem, f"src/patcher/{stem}.py")
        module(prefix + ".tools.partial_tile_trace_probe", "tools/partial_tile_trace_probe.py")
        module(prefix + ".tools.build_partial_tile_candidate", "tools/build_partial_tile_candidate.py")
        builder = module(prefix + ".tools.build_framed_candidate", "tools/build_framed_candidate.py")
        pe._require(builder.STAGE == BASE_STAGE, "bound builder stage changed")
        image, metadata, _ = builder.build_candidate(original, resolution, minimap_viewport=minimap_viewport)
        # Detect source changes during reconstruction as well as before it.
        for name, digest in pins.items():
            pe._require(_source(name, digest) == sources[name], "source changed during reconstruction")
        return image, metadata, pins
    finally:
        for name in names:
            sys.modules.pop(name, None)
        sys.path[:] = old_path


def _legacy_continuations(original: bytes, candidate: bytes, metadata: dict) -> list[dict]:
    """Authenticate the exact two old centering-wrapper continuation entries.

    These established wrappers occupy the original RW DGROUP cave. Their
    permissions remain unchanged. This is not permission to branch into an
    arbitrary data address: the complete source-generated patch row, its
    original bytes and its PUSHAD/CALL/POPAD/PUSHAD boundary must match.
    Call only after the full canonical framed reconstruction has succeeded.
    """
    base = pe.inspect_pe(candidate)
    pointer_offset = base.file_offset(0x435DAA - base.image_base, 5)
    pointer = candidate[pointer_offset:pointer_offset + 5]
    pe._require(pointer[0] == 0xBB, "canonical action-wrapper pointer opcode differs")
    action = struct.unpack_from("<I", pointer, 1)[0]
    pe._require(action in (0x51316F, 0x51BC20), "unreviewed legacy action-wrapper address")
    result = []
    for entry, callee, group in (
        (0x51B6D0, 0x422020, "castle-overview-center-present-wrapper"),
        (action, 0x435B90, "castle-ui-center-present-wrapper"),
    ):
        offset = base.file_offset(entry - base.image_base, 8)
        rows = [row for row in metadata["selected_patches"]
                if row["offset"] == offset and row["group"] == group]
        pe._require(len(rows) == 1, "missing unique source-bound legacy wrapper patch")
        row = rows[0]
        old, new = bytes.fromhex(row["old_hex"]), bytes.fromhex(row["new_hex"])
        pe._require(len(old) == len(new) >= 8 and base.file_offset(entry-base.image_base, len(new)) == offset
                    and original[offset:offset+len(old)] == old and candidate[offset:offset+len(new)] == new,
                    "legacy wrapper original/canonical source bytes differ")
        prefix = b"\x60\xe8" + struct.pack("<i", callee - entry - 6) + b"\x61\x60"
        pe._require(new[:8] == prefix, "legacy wrapper call/continuation instruction boundary differs")
        pe._require(any(section.name.rstrip(b"\0") == b"DGROUP" and section.characteristics == RW_DATA
                        and section.rva <= entry-base.image_base
                        and entry-base.image_base+len(new) <= section.rva+section.raw_size
                        for section in base.sections), "legacy wrapper is not in the canonical DGROUP cave")
        result.append(dict(target=entry+6, entry_va=entry, offset=offset, span_bytes=len(new),
                           native_callee=callee, group=group, original_hex=old.hex(), framed_hex=new.hex(),
                           original_sha256=pe._sha(old), framed_sha256=pe._sha(new),
                           entry_contract="POPAD then PUSHAD after the exact replayed native CALL"))
    return result


def _target_mapped(base: pe.PEImage, target: int, kind: str, code_va: int,
                   code_size: int, state_va: int, legacy_targets: frozenset[int] = frozenset()) -> bool:
    if code_va <= target < code_va + code_size:
        return True
    if kind == "abs32" and state_va <= target < state_va + STATE_BYTES:
        return True
    if kind == "rel32" and target in legacy_targets:
        return True
    return any(section.rva <= target - base.image_base < section.rva + section.memory_size
               and (kind == "abs32" or section.characteristics & 0x20000000)
               for section in base.sections)


def _legacy_hook(hook: pe.HookPatch, row: dict, candidate: bytes, base: pe.PEImage,
                 code_va: int, code_size: int, old_locations: tuple[int, ...]):
    """Validate precisely one known six-byte RW wrapper entry replacement.

    The existing PE helper's executable-section rule cannot apply to these
    source-proven legacy RW code caves. Do not pretend DGROUP has RX flags.
    Instead require the exact whole first instruction pair and one E9/NOP
    replacement to new code. All other hooks still use _prepare_hooks.
    """
    pe._require(all(type(value) is int for value in (hook.offset, hook.rva, hook.va))
                and hook.offset == row["offset"] and hook.va == row["entry_va"]
                and hook.rva == hook.va-base.image_base
                and base.file_offset(hook.rva, 6) == hook.offset,
                "legacy wrapper hook VA/RVA/file offset differs")
    pe._require(isinstance(hook.old, bytes) and isinstance(hook.new, bytes)
                and hook.old == bytes.fromhex(row["framed_hex"])[:6]
                and candidate[hook.offset:hook.offset+6] == hook.old,
                "legacy wrapper hook must replace exactly its authenticated first six bytes")
    pe._require(isinstance(hook.purpose, str) and hook.purpose.strip()
                and isinstance(hook.relocations, (tuple, list)) and len(hook.relocations) == 1,
                "legacy wrapper hook requires purpose and exactly one rel32 record")
    record = hook.relocations[0]
    pe._require(all(hasattr(record, key) for key in ("offset", "kind", "target", "purpose")),
                "malformed legacy wrapper hook relocation")
    pe._u32(record.target, "legacy wrapper new-code target")
    pe._require(type(record.offset) is int and record.offset == 1 and record.kind == "rel32"
                and isinstance(record.purpose, str) and record.purpose.strip()
                and code_va <= record.target < code_va+code_size,
                "legacy wrapper replacement requires one relative jump to mapped new code")
    expected = b"\xe9" + struct.pack("<I", (record.target-hook.va-5)&0xFFFFFFFF) + b"\x90"
    pe._require(hook.new == expected, "legacy wrapper hook must be exact E9 plus one NOP")
    pe._require(not any(rva < hook.rva+6 and hook.rva < rva+4 for rva in old_locations),
                "legacy wrapper first six bytes unexpectedly overlap an old HIGHLOW")
    return (pe.ByteEdit(hook.offset, hook.rva, hook.va, hook.old, hook.new, hook.purpose),
            dict(hook_va=hook.va, offset=1, rva=hook.rva+1, kind="rel32",
                 target=record.target, purpose=record.purpose))


def _extend_verified_image(candidate: bytes, *, code: bytes, code_va: int, state_va: int,
                           relocations: Sequence[pe.CodeRelocation], hooks: Sequence[pe.HookPatch],
                           removed_highlow_rvas: Sequence[int], binding: dict,
                           state: bytes = bytes(STATE_BYTES),
                           legacy_continuations: tuple[dict, ...] = ()) -> pe.ExtensionResult:
    """Private format core. Production callers must use the bound public API."""
    pe._require(all(isinstance(items, (tuple, list)) for items in (hooks, relocations, removed_highlow_rvas)),
                "hooks, relocations and removals must be explicit sequences")
    base = pe.inspect_pe(candidate)
    pe._require(len(base.sections) == 8 and base.sections[-1].name.rstrip(b"\0") == b".hdcode"
                and base.sections[-1].characteristics == pe.RX_CODE,
                "expected the eight-section framed RX candidate")
    pe._require(base.section_alignment == STATE_BYTES and base.file_alignment == 512,
                "modal allocation requires canonical 4096/512 alignment")
    slot = base.sections[-1].header_offset + 40
    pe._require(slot == 680 and slot + 80 == 760 and slot + 80 <= min(base.headers_size, pe.SCRATCH_START),
                "modal section headers would overlap reserved scratch")
    pe._require(candidate[slot:slot + 80] == bytes(80), "modal header slots are not zero")
    pe._require(not any(s.name.rstrip(b"\0") in (b".hdmodal", b".hdstate") for s in base.sections),
                "modal sections already exist")
    pe._require(isinstance(code, bytes) and 0 < len(code) <= CODE_RESERVATION,
                "code must be nonempty immutable bytes within the 128 KiB reservation")
    pe._require(isinstance(state, bytes) and state == bytes(STATE_BYTES),
                "modal state must be exactly 4096 immutable zero bytes")
    pe._require(type(code_va) is int and code_va == base.image_base + base.image_size,
                "modal code VA differs from the end of the canonical image")
    pe._require(type(state_va) is int and state_va == code_va + CODE_RESERVATION,
                "modal state VA differs from code VA plus 128 KiB")
    pe._u32(state_va + STATE_BYTES, "modal address extent")
    pe._require(bool(hooks), "modal operation requires explicit hooks")
    old_table, old_locations = pe._old_relocations(candidate, base)
    legacy_targets = frozenset(row["target"] for row in legacy_continuations)
    fields, normalized, new_absolute = [], [], []
    for relocation in relocations:
        pe._require(all(hasattr(relocation, k) for k in ("offset", "kind", "target", "purpose")),
                    "malformed modal code relocation")
        off, kind, target, purpose = relocation.offset, relocation.kind, relocation.target, relocation.purpose
        pe._require(type(off) is int and 0 <= off <= len(code) - 4, "modal relocation outside code")
        pe._u32(target, "modal relocation target")
        pe._require(kind in ("abs32", "rel32") and isinstance(purpose, str) and purpose.strip(),
                    "invalid modal relocation kind/purpose")
        pe._require(_target_mapped(base, target, kind, code_va, len(code), state_va, legacy_targets),
                    "modal relocation target is unmapped or non-executable relative target")
        expected = target if kind == "abs32" else (target - code_va - off - 4) & 0xFFFFFFFF
        pe._require(struct.unpack_from("<I", code, off)[0] == expected, "modal relocation target/value mismatch")
        fields.append(off)
        normalized.append(dict(offset=off, kind=kind, target=target, purpose=purpose))
        if kind == "abs32":
            new_absolute.append(base.image_size + off)
    fields.sort()
    pe._require(all(a + 4 <= b for a, b in zip(fields, fields[1:])), "overlapping modal relocation fields")
    # Extend only the memory lookup with the known RW state range. Ordinary
    # hooks retain every existing allocator check. The two authenticated legacy
    # RW prefixes use the narrower _legacy_hook contract below; their actual
    # section flags stay unchanged. The state page cannot become a hook span.
    memory_view = replace(base, sections=base.sections + (
        pe.Section(b".hdstate", slot + 40, STATE_BYTES, state_va - base.image_base, 0, 0, RW_DATA),))
    for hook in hooks:
        pe._require(isinstance(hook, pe.HookPatch), "modal hook must be a HookPatch")
        for relocation in hook.relocations:
            pe._require(all(hasattr(relocation, k) for k in ("kind", "target")), "malformed hook relocation")
            pe._u32(relocation.target, "hook relocation target")
            pe._require(_target_mapped(base, relocation.target, relocation.kind, code_va, len(code), state_va, legacy_targets),
                        "modal hook target is unmapped or non-executable relative target")
    known_entries = {row["entry_va"]: row for row in legacy_continuations}
    standard, legacy_edits, legacy_fields = [], [], []
    for hook in hooks:
        if hook.va in known_entries:
            edit, field = _legacy_hook(hook, known_entries[hook.va], candidate, base, code_va, len(code), old_locations)
            legacy_edits.append(edit); legacy_fields.append(field)
        else:
            standard.append(hook)
    hook_edits, hook_absolute, hook_fields, removed_rows = pe._prepare_hooks(
        candidate, memory_view, standard, removed_highlow_rvas, old_locations, code_va, len(code))
    hook_edits += legacy_edits
    hook_fields += legacy_fields
    ordered_hooks = sorted(hook_edits, key=lambda edit: edit.rva)
    pe._require(all(a.rva+len(a.old) <= b.rva for a, b in zip(ordered_hooks, ordered_hooks[1:])),
                "overlapping standard/legacy hook spans")
    order = {hook.va: index for index, hook in enumerate(hooks)}
    hook_edits.sort(key=lambda edit: order[edit.va])
    hook_fields.sort(key=lambda row: (order[row["hook_va"]], row["offset"]))
    removed = set(removed_highlow_rvas)
    retained = tuple(rva for rva in old_locations if rva not in removed)
    expected_locations = retained + tuple(hook_absolute) + tuple(new_absolute)
    table = pe._relocation_blocks(expected_locations)
    pe._require(len(table) >= 8, "modal relocation directory is empty")
    table_offset = pe._align(len(code), 4)
    payload = code + bytes(table_offset - len(code)) + table
    code_raw = pe._align(len(payload), base.file_alignment)
    pe._require(code_raw <= CODE_RESERVATION, "modal code plus relocation table exceeds 128 KiB")
    state_raw_offset = len(candidate) + code_raw
    pe._u32(state_raw_offset + STATE_BYTES, "modal file size")
    new_image_size = state_va - base.image_base + STATE_BYTES
    # Windows image sections must remain adjacent after SectionAlignment.
    # State lives at a fixed +128 KiB ABI offset; cover that reservation with
    # the RX section's zero-filled virtual tail, without padding its raw file.
    header = struct.pack("<8sIIIIIIHHI", b".hdmodal", CODE_RESERVATION, base.image_size,
                         code_raw, len(candidate), 0, 0, 0, 0, pe.RX_CODE)
    state_header = struct.pack("<8sIIIIIIHHI", b".hdstate", STATE_BYTES, state_va - base.image_base,
                               STATE_BYTES, state_raw_offset, 0, 0, 0, 0, RW_DATA)
    edits = list(hook_edits)

    def change(offset, data, purpose, rva=None, append=False):
        old = b"" if append else candidate[offset:offset + len(data)]
        pe._require((append and offset == len(candidate)) or (not append and len(old) == len(data)),
                    "invalid modal byte-edit range")
        address = offset if rva is None else rva
        edits.append(pe.ByteEdit(offset, address, base.image_base + address, old, data, purpose))

    change(base.pe_offset + 6, struct.pack("<H", 10), "NumberOfSections")
    change(base.optional_offset + 4, struct.pack("<I", pe._u32(base.size_of_code + code_raw, "SizeOfCode")), "SizeOfCode")
    initialized = struct.unpack_from("<I", candidate, base.optional_offset + 8)[0]
    change(base.optional_offset + 8, struct.pack("<I", pe._u32(initialized + STATE_BYTES, "SizeOfInitializedData")),
           "SizeOfInitializedData")
    change(base.optional_offset + 56, struct.pack("<I", new_image_size), "SizeOfImage")
    change(base.optional_offset + 136, struct.pack("<II", base.image_size + table_offset, len(table)),
           "complete merged base relocation directory")
    change(slot, header, ".hdmodal RX section header")
    change(slot + 40, state_header, ".hdstate RW section header")
    # Separate append edits preserve each section's actual VA/file mapping.
    change(len(candidate), payload + bytes(code_raw - len(payload)), "append RX code and merged relocations",
           base.image_size, append=True)
    edits.append(pe.ByteEdit(state_raw_offset, state_va - base.image_base, state_va, b"", state,
                             "append zeroed RW modal state"))
    ordered_old = sorted((e.offset, e.offset + len(e.old)) for e in edits if e.old)
    pe._require(all(a[1] <= b[0] for a, b in zip(ordered_old, ordered_old[1:])), "overlapping modal byte edits")
    result = bytearray(candidate)
    for edit in edits:
        pe._require(result[edit.offset:edit.offset + len(edit.old)] == edit.old
                    and (bool(edit.old) or edit.offset == len(result)), "modal old-byte edit check failed")
        result[edit.offset:edit.offset + len(edit.old)] = edit.new
    image = bytes(result)
    final = pe.inspect_pe(image)
    pe._require(all(a.rva + pe._align(a.memory_size, base.section_alignment) == b.rva
                    for a, b in zip(final.sections, final.sections[1:])),
                "modal sections must have adjacent virtual extents")
    _, actual_locations = pe._old_relocations(image, final)
    pe._require(sorted(actual_locations) == sorted(expected_locations), "merged modal relocations changed unrelated entries")
    pe._require(final.sections[:-2] == base.sections and image[state_raw_offset:] == bytes(STATE_BYTES),
                "old sections changed or modal state is not zero")
    old_reloc_offset = base.file_offset(base.relocation_rva, base.relocation_size)
    pe._require(image[old_reloc_offset:old_reloc_offset + len(old_table)] == old_table,
                "original framed relocation bytes were overwritten")
    metadata = dict(schema="clash95_pe_modal_extension_v1", **binding,
        input_sha256=pe._sha(candidate), output_sha256=pe._sha(image), code_sha256=pe._sha(code),
        code_va=code_va, code_rva=base.image_size, code_bytes=len(code), code_raw_bytes=code_raw,
        code_virtual_bytes=CODE_RESERVATION,
        code_characteristics=pe.RX_CODE, state_va=state_va, state_bytes=STATE_BYTES,
        state_raw_offset=state_raw_offset, state_characteristics=RW_DATA, state_sha256=pe._sha(state),
        old_relocation_sha256=pe._sha(old_table), merged_relocation_sha256=pe._sha(table),
        relocation_rva=base.image_size + table_offset, relocation_bytes=len(table),
        old_highlow_count=len(old_locations), retained_highlow_count=len(retained),
        new_highlow_count=len(new_absolute) + len(hook_absolute), removed_highlow=removed_rows,
        relocations=normalized, hook_relocations=hook_fields, hooks=[e.metadata() for e in hook_edits],
        edits=[e.metadata() for e in edits], installation_ready=False, runtime_executed=False,
        manual_input_proof=False, promotion_ready=False,
        limits="Exact framed input, allocation and declared hook/relocation fields only. No instruction-boundary, "
               "omitted-operand, modal semantics, runtime, manual input or promotion proof.")
    return pe.ExtensionResult(image, tuple(edits), metadata)


def extend_framed_candidate_with_modal(original: bytes, candidate: bytes, *, expected_candidate_sha256: str,
                                       resolution: str, minimap_viewport: bool, validation_stage: str,
                                       code: bytes, code_va: int, state_va: int,
                                       relocations: Sequence[pe.CodeRelocation], hooks: Sequence[pe.HookPatch],
                                       removed_highlow_rvas: Sequence[int],
                                       state: bytes = bytes(STATE_BYTES)) -> pe.ExtensionResult:
    """Bind original, exact entire framed image and source chain, then allocate.

    The six modal hook semantics belong to the separate emitter. This allocator
    authenticates every supplied original/base byte span and declared operand;
    it accepts no filenames, custom builder paths, source-pin overrides or file
    outputs. The separate modal stage cannot be the protected or framed stage.
    """
    pe._identity(original, pe.ORIGINAL_SHA256, "original")
    pe._identity(candidate, expected_candidate_sha256, "framed input candidate")
    pe._require(validation_stage == STAGE, "the reviewed modalcanvas validation stage is required")
    pe._require(type(minimap_viewport) is bool, "minimap_viewport must be explicit bool")
    pe._require(isinstance(resolution, str), "resolution must be canonical WxH")
    pe._require(all(isinstance(items, (tuple, list)) for items in (hooks, relocations, removed_highlow_rvas)),
                "hooks, relocations and removals must be explicit sequences")
    rebuilt, base_metadata, source_pins = _reconstruct(original, resolution, minimap_viewport)
    pe._require(rebuilt == candidate and pe._sha(rebuilt) == expected_candidate_sha256.lower(),
                "input differs from the entire canonical framed candidate")
    base, initial = pe.inspect_pe(candidate), pe.inspect_pe(original)
    continuations = _legacy_continuations(original, candidate, base_metadata)
    original_spans = []
    for hook in hooks:
        pe._require(isinstance(hook, pe.HookPatch), "modal hook must be a HookPatch")
        # Native/cave hook sites must exist in the original image; newly emitted
        # code belongs in .hdmodal rather than modifying the old .hdcode payload.
        offset = initial.file_offset(hook.rva, len(hook.old))
        pe._require(offset == hook.offset and hook.va == initial.image_base + hook.rva,
                    "modal hook does not map to the authenticated original")
        old = original[offset:offset + len(hook.old)]
        original_spans.append(dict(offset=offset, rva=hook.rva, va=hook.va, original_hex=old.hex(),
                                   original_sha256=pe._sha(old), framed_hex=hook.old.hex()))
    binding = dict(original_sha256=pe.ORIGINAL_SHA256, base_stage=BASE_STAGE, stage=STAGE,
                   resolution=resolution, minimap_viewport=minimap_viewport, source_sha256=source_pins,
                   original_hook_spans=original_spans, base_image_size=base.image_size,
                   base_code_sha256=base_metadata["extension_payload_sha256"],
                   authenticated_legacy_continuations=continuations)
    return _extend_verified_image(candidate, code=code, code_va=code_va, state_va=state_va,
        relocations=relocations, hooks=hooks, removed_highlow_rvas=removed_highlow_rvas, binding=binding, state=state,
        legacy_continuations=tuple(continuations))
