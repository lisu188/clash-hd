"""Nine-preset Framed validation identity over the exact frozen Framed recipe.

This profile installs the existing guarded four-border map/minimap chain only.
Native modal/army fallback remains; no Complete HD or Modal Widgets bytes are
borrowed. Construction returns bytes, deterministic metadata and an initial
preferred-address probe, with no file writer, installation or runtime path.
"""
from __future__ import annotations

import ast
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import re
import struct
import sys
import types
import uuid

ROOT = Path(__file__).resolve().parents[2]
STAGE = ("gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-"
         "presentbounds-minimapright-dynvswitch-framed-allpresets-validation")
REVISION = "framed_all_presets_v1"
BASE_SHA256 = "500055d77d03d514e8d3168506bd10f67cd8569bcc450604ff8192f46cdaf3ae"
RESOLUTIONS = ("800x600", "1024x768", "1280x720", "1280x960", "1366x768",
               "1920x1080", "2560x1440", "3440x1440", "3840x2160")
FROZEN_STAGE = ("gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-"
                "presentbounds-minimapright-dynvswitch-combinedui-partialtiles-initialpaint-framed-validation")
RX = 0x60000020
FALSE_CLAIMS = ("installation_ready", "runtime_executed", "manual_input_proof", "promotion_ready",
                "expanded_battle_installed", "launcher_registered", "matrix_registered")
PINNED_SOURCES = {
    "src/patcher/patch_clash95_hd.py": "38021e9a4d21bc9a8bf0c2f9b66379595509446b5177d6f91bab6f677b5e8106",
    "src/patcher/partial_tile_clip.py": "92421c123a75bef119bfa93b438f813ec18dcb073699327cf15b7a1b884bcfad",
    "src/patcher/partial_tile_hooks.py": "71ce9390a3018c80811a1e57b36dc47b59928cb3d9deec364e9b195f94465419",
    "src/patcher/initial_map_paint.py": "79e6d6d180a115b2b59e98600038fa3a31707a373c0095489bb706182078ba91",
    "src/patcher/pe_extension.py": "4d66e7fa3bf17c6260fffaefc8d4e4e8da0ba76ceea7746858c52299f74d7c27",
    "src/patcher/framed_viewport.py": "1d5bc64777cf01c68f587bc3fee2dc7d5024696bd6b1712dab4e6e78f78c4c42",
    "src/patcher/framed_recipe.py": "559b571ce1dd83421f79a58e110cd5b6317807cd68087d7ea77f14c4f4a071b4",
    "src/patcher/four_sided_frame.py": "433fd27fb8afda4a12f5539604f722f18bf8d37885125e30ee9cfb948926c2a9",
    "src/patcher/framed_full_paint.py": "d496fe9eca8ebe02c34f5680aee4fe2683b4b3849d65fe5f4e5f17b4e118c91a",
    "src/patcher/framed_presentation.py": "70619f5c25faac66a668c19f989e55a8d4e4662c24c78286e16c233cc564ab6d",
    "src/patcher/framed_input.py": "a2557f1ca7caf23a957a21bf747ac23d875b27e7706de26d463b98ae221ce810",
    "src/patcher/framed_minimap.py": "90a345f1080f0b69107f99d1ec1687d1a28faab2e72e5daae6bee467fa31a6d7",
    "tools/build_partial_tile_candidate.py": "363eaabfca63e435448355c406e6390e05b4151ffb928114221032c30b2cd255",
    "tools/partial_tile_trace_probe.py": "a20512fa49cc86db67a486f9202d4efa3f9f3745005d11220bf6097661a44729",
    "tools/build_framed_candidate.py": "fbe2f2c571154312329ab23603d8de45fb8ec5fafcdfd10bad4049876dfb14bc",
}
MODULE_ORDER = tuple("src/patcher/" + name + ".py" for name in (
    "framed_viewport", "patch_clash95_hd", "partial_tile_clip", "pe_extension", "framed_recipe",
    "partial_tile_hooks", "four_sided_frame", "framed_full_paint", "initial_map_paint",
    "framed_presentation", "framed_input", "framed_minimap",
)) + ("tools/partial_tile_trace_probe.py", "tools/build_partial_tile_candidate.py", "tools/build_framed_candidate.py")
PREDICATE = re.compile(r"\((wo|by)\(([0-9a-f]{8})\) != ([0-9a-f]+)\)")


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _sources():
    _require(Path(__file__).resolve() == ROOT / "src/patcher/framed_all_presets_candidate.py", "noncanonical Framed constructor path")
    sources = {}
    for name, digest in PINNED_SOURCES.items():
        path = ROOT / name
        _require(path.resolve() == path and path.is_relative_to(ROOT), "noncanonical Framed producer path")
        data = path.read_bytes()
        _require(sha256(data) == digest, "reviewed Framed producer source differs: " + name)
        sources[name] = data
    sources["src/patcher/framed_all_presets_candidate.py"] = Path(__file__).read_bytes()
    return sources


class _PrivateImports(ast.NodeTransformer):
    def __init__(self, prefix):
        self.prefix = prefix
        self.bare_tools = {Path(name).stem for name in MODULE_ORDER if name.startswith("tools/")}
    def visit_ImportFrom(self, node):
        if not node.level and node.module:
            if node.module in ("src", "tools") or node.module.startswith(("src.", "tools.")):
                node.module = self.prefix + "." + node.module
            elif node.module in self.bare_tools:
                node.module = self.prefix + ".tools." + node.module
        return node


@contextmanager
def _producer(sources):
    """Authenticated private snapshots; public aliases and pyc grant no admission."""
    prefix = "_clash95_framed_all_presets_" + uuid.uuid4().hex
    saved_path = list(sys.path)
    try:
        for suffix in ("", ".src", ".src.patcher", ".tools"):
            package = types.ModuleType(prefix + suffix)
            package.__path__ = []
            sys.modules[package.__name__] = package
            if suffix:
                owner, _, leaf = package.__name__.rpartition(".")
                setattr(sys.modules[owner], leaf, package)
        modules = {}
        for name in MODULE_ORDER:
            full = prefix + "." + name.removesuffix(".py").replace("/", ".")
            module = types.ModuleType(full)
            module.__file__ = str(ROOT / name)
            module.__package__ = full.rpartition(".")[0]
            sys.modules[full] = module
            setattr(sys.modules[module.__package__], full.rpartition(".")[2], module)
            tree = _PrivateImports(prefix).visit(ast.parse(sources[name], module.__file__))
            exec(compile(tree, module.__file__, "exec"), module.__dict__)
            _require(Path(module.__file__).resolve() == ROOT / name and module.__name__ == full,
                     "private Framed module identity differs")
            modules[name] = module
        yield modules
    finally:
        for name in list(sys.modules):
            if name == prefix or name.startswith(prefix + "."):
                del sys.modules[name]
        sys.path[:] = saved_path


def _hex(value):
    _require(type(value) is str and len(value) % 2 == 0, "noncanonical byte hex")
    try:
        result = bytes.fromhex(value)
    except ValueError as error:
        raise ValueError("noncanonical byte hex") from error
    _require(result.hex() == value, "noncanonical byte hex")
    return result


def _address(view, offset):
    if offset < view.headers_size:
        return offset, view.image_base + offset
    for section in view.sections:
        if section.raw_offset and section.raw_offset <= offset < section.raw_offset + section.raw_size:
            rva = section.rva + offset - section.raw_offset
            return rva, view.image_base + rva
    return None, None


def byte_records(original, candidate, view):
    _require(type(original) is type(candidate) is bytes and len(candidate) >= len(original), "immutable nontruncated images required")
    records, position = [], 0
    while position < len(candidate):
        if position < len(original) and original[position] == candidate[position]:
            position += 1
            continue
        start = position
        limit = min(start + 64, len(original) if start < len(original) else len(candidate))
        while position < limit and (position >= len(original) or original[position] != candidate[position]):
            position += 1
        rva, va = _address(view, start)
        records.append(dict(offset=start, file_offset=start, rva=rva, va=va,
            old_hex=original[start:position].hex(), new_hex=candidate[start:position].hex(), stage=STAGE,
            group="framed-all-presets-extension" if start >= len(original) else "framed-all-presets-integrated",
            rationale="Exact source reconstruction of the Framed scalar, map, four-border, input and minimap chain",
            appended=start >= len(original)))
    return records


def apply_records(original, records, *, expected_base_sha256, view):
    _require(type(original) is bytes and sha256(original) == expected_base_sha256, "byte replay base SHA-256 differs")
    _require(type(records) is list, "explicit byte records required")
    output, end = bytearray(original), 0
    for row in records:
        _require(type(row) is dict and type(row.get("offset")) is type(row.get("file_offset")) is int
                 and row["offset"] == row["file_offset"] >= end and row.get("stage") == STAGE, "invalid or overlapping byte record")
        offset, old, new = row["offset"], _hex(row.get("old_hex")), _hex(row.get("new_hex"))
        _require(bool(new) and type(row.get("appended")) is bool and row["appended"] == (offset >= len(original))
                 and type(row.get("rationale")) is str and row["rationale"].strip(), "invalid replay append/rationale")
        rva, va = _address(view, offset)
        _require((row.get("rva"), row.get("va")) == (rva, va)
                 and (rva is None or type(row.get("rva")) is type(row.get("va")) is int), "byte-record mapping differs")
        if old:
            _require(offset + len(old) <= len(original) and len(old) == len(new)
                     and output[offset:offset + len(old)] == old, "byte-record old bytes differ")
            output[offset:offset + len(old)] = new
        else:
            _require(offset == len(output) and row["appended"], "appended byte records must be contiguous")
            output.extend(new)
        end = offset + len(new)
    return bytes(output)


def _undo(candidate, metadata, pe):
    view = pe.inspect_pe(candidate)
    rows = metadata.get("edits")
    _require(type(rows) is list and bool(rows), "Framed extension edits missing")
    decoded = []
    for row in rows:
        offset, old, new = row.get("offset"), _hex(row.get("old_hex")), _hex(row.get("new_hex"))
        _require(type(offset) is int and offset >= 0 and bool(new) and (not old or len(old) == len(new))
                 and type(row.get("rva")) is type(row.get("va")) is int
                 and (row["rva"], row["va"]) == _address(view, offset)
                 and candidate[offset:offset + len(new)] == new, "Framed declared edit differs")
        decoded.append((offset, old, new))
    decoded.sort()
    _require(all(a[0] + len(a[2]) <= b[0] for a, b in zip(decoded, decoded[1:])), "Framed extension edits overlap")
    appends = [row for row in decoded if not row[1]]
    _require(len(appends) == 1 and appends[0][0] + len(appends[0][2]) == len(candidate), "Framed complete tail ownership differs")
    base_length = appends[0][0]
    base = bytearray(candidate[:base_length])
    for offset, old, new in decoded:
        if old:
            _require(offset + len(new) <= base_length, "Framed edit crosses append boundary")
            base[offset:offset + len(old)] = old
    base = bytes(base)
    _require(sha256(base) == metadata.get("input_sha256"), "reconstructed scalar parent SHA-256 differs")
    return base


def _geometry_contract(metadata, resolution, geometry):
    width, height = map(int, resolution.split("x"))
    layout = geometry.FramedViewport(width, height)
    contract = metadata.get("layout_contract", {})
    _require(contract.get("profile") == "native_four_border_tiles_v1"
             and contract.get("physical_surface") == [0, 0, width - 1, height - 1]
             and contract.get("terrain") == list(layout.terrain.as_tuple())
             and contract.get("full_tiles") == list(layout.full_tiles)
             and contract.get("unsupported_context_is_native_fallback") is True,
             "Framed geometry or native fallback contract differs")
    bands = metadata.get("frame_presentation_contract", {}).get("frame_bands_inclusive")
    _require(type(bands) in (tuple, list) and [list(row) for row in bands] == [list(row.as_tuple()) for row in layout.frame_bands],
             "all four Framed presentation bands required")
    _require(metadata.get("minimap_viewport_revision") == "framed_minimap_actual_terrain_v1"
             and metadata.get("minimap_viewport_contract", {}).get("statuses", {}).get("2") == "preserved native640 fallback",
             "Framed minimap fallback identity differs")
    return dict(physical_surface=list(layout.surface.as_tuple()), terrain=list(layout.terrain.as_tuple()),
                frame_bands=[list(row.as_tuple()) for row in layout.frame_bands],
                action_cells=[list(row.as_tuple()) for row in layout.action_cells],
                minimap_right_anchor=layout.minimap_right_anchor, native_modal_fallback_retained=True)


def _owned_target(row, before, after, patches):
    target_rva = row["target"] - after.image_base
    if any(s.rva <= target_rva < s.rva + s.memory_size
           and (row["kind"] == "abs32" or s.characteristics & 0x20000000) for s in after.sections):
        return True
    # The frozen C5 fallback is authored in the legacy DGROUP cave. Admit
    # only the exact purpose, destination, section and scalar-owned range.
    # This preserves the recipe without granting generic executable data.
    return (row["kind"] == "rel32" and row["target"] == 0x51BE00
            and row["purpose"] == "framed_gate_old_c5_fallback"
            and sum(p["offset"] == 0x11A000 and p["group"] == "frame-restore-bands"
                    and len(_hex(p["new_hex"])) == 256 for p in patches) == 1
            and any(s.name.rstrip(b"\0") == b"DGROUP" and s.characteristics == 0xC0000040
                    and s.rva <= target_rva and target_rva + 256 <= s.rva + s.raw_size for s in before.sections)
            and before.file_offset(target_rva, 256) == 0x11A000)


def _admit_source_context(candidate, metadata, source_context):
    """Admit the complete inventory from a separately reconstructed producer.

    Structural checks can validate supplied operands but cannot discover an
    omitted rel32 or hook field. The private caller must first reconstruct the
    pinned frozen producer independently; incoming metadata supplies no source
    of truth. Only its top-level wall-clock generation stamp is immaterial.
    """
    _require(type(candidate) is bytes and type(metadata) is dict
             and type(source_context) is tuple and len(source_context) == 2
             and type(source_context[0]) is bytes and type(source_context[1]) is dict
             and source_context[1] is not metadata, "independent Framed source context required")
    expected_image, expected_metadata = source_context
    _require(candidate == expected_image, "independent frozen Framed source bytes differ")
    _require(_canonical(_deterministic(metadata)) == _canonical(_deterministic(expected_metadata)),
             "complete frozen Framed source metadata identity differs")


def _audit(original, candidate, metadata, resolution, pe, geometry, *, source_context=None):
    """Source admission, original/scalar replay, ownership and operand audit."""
    _admit_source_context(candidate, metadata, source_context)
    _require(metadata.get("original_sha256") == BASE_SHA256 and metadata.get("stage") == FROZEN_STAGE
             and metadata.get("resolution") == resolution and resolution in RESOLUTIONS
             and metadata.get("output_sha256") == sha256(candidate)
             and metadata.get("minimap_viewport") is metadata.get("framed_validation") is metadata.get("initial_paint") is True
             and all(metadata.get(key) is False for key in FALSE_CLAIMS[:4]), "frozen Framed identity or acceptance differs")
    scalar = _undo(candidate, metadata, pe)
    before, after, initial = pe.inspect_pe(scalar), pe.inspect_pe(candidate), pe.inspect_pe(original)
    section = after.sections[-1]
    _require(len(initial.sections) == len(before.sections) == 7 and len(after.sections) == 8
             and after.sections[:7] == before.sections == initial.sections
             and scalar[:initial.headers_size] == original[:initial.headers_size] and len(scalar) == len(original)
             and section.name.rstrip(b"\0") == b".hdcode" and section.characteristics == RX
             and section.header_offset == 0x280 and section.rva == initial.image_size
             and section.raw_offset == len(original) and section.raw_offset + section.raw_size == len(candidate)
             and (after.section_alignment, after.file_alignment, after.headers_size) == (4096, 512, 1024)
             and after.image_base == initial.image_base and after.size_of_code == initial.size_of_code + section.raw_size
             and all(a.rva + pe._align(a.memory_size, 4096) == b.rva for a, b in zip(after.sections, after.sections[1:]))
             and candidate[after.optional_offset + 16:after.optional_offset + 20] == original[initial.optional_offset + 16:initial.optional_offset + 20],
             "Framed section allocation or original PE ownership differs")
    patches = metadata.get("selected_patches")
    _require(type(patches) is list and bool(patches), "Framed scalar patch inventory missing")
    rebuilt, spans = bytearray(original), []
    for row in patches:
        offset, old, new = row.get("offset"), _hex(row.get("old_hex")), _hex(row.get("new_hex"))
        _require(type(offset) is int and initial.headers_size <= offset and bool(old) and len(old) == len(new)
                 and original[offset:offset + len(old)] == old and type(row.get("group")) is str and row["group"].strip(),
                 "Framed scalar old bytes or patch identity differs")
        rebuilt[offset:offset + len(old)] = new
        spans.append((offset, offset + len(old)))
    spans.sort()
    _require(all(a[1] <= b[0] for a, b in zip(spans, spans[1:])) and bytes(rebuilt) == scalar,
             "full Framed scalar reconstruction differs")
    size = metadata.get("code_bytes")
    _require(type(size) is int and 0 < size <= section.raw_size and metadata.get("code_va") == after.image_base + section.rva
             and metadata.get("code_rva") == section.rva and metadata.get("section") == ".hdcode"
             and metadata.get("characteristics") == RX and metadata.get("append_offset") == len(original)
             and metadata.get("append_bytes") == section.raw_size
             and metadata.get("extension_payload_size") == size
             and metadata.get("code_sha256") == metadata.get("extension_payload_sha256") == sha256(candidate[section.raw_offset:section.raw_offset + size]),
             "Framed code identity differs")
    hooks, by_va, hook_spans = metadata.get("hooks"), {}, []
    _require(type(hooks) is list and bool(hooks) and type(metadata.get("installed_hook_names")) is list
             and len(hooks) == len(metadata["installed_hook_names"])
             and len(set(metadata["installed_hook_names"])) == len(hooks), "Framed native hook inventory differs")
    for row in hooks:
        offset, rva, va = row.get("offset"), row.get("rva"), row.get("va")
        old, new = _hex(row.get("old_hex")), _hex(row.get("new_hex"))
        _require(type(offset) is type(rva) is type(va) is int and va == after.image_base + rva
                 and bool(old) and len(old) == len(new) and before.file_offset(rva, len(old)) == offset
                 and scalar[offset:offset + len(old)] == old and candidate[offset:offset + len(new)] == new
                 and any(s.characteristics & 0x20000000 and s.rva <= rva and rva + len(new) <= s.rva + s.raw_size for s in before.sections)
                 and va not in by_va, "Framed installed native hook differs")
        by_va[va] = row
        hook_spans.append((rva, rva + len(new)))
    hook_spans.sort()
    _require(all(a[1] <= b[0] for a, b in zip(hook_spans, hook_spans[1:])), "Framed native hooks overlap")
    old_table, old_fields = pe._old_relocations(scalar, before)
    removed, displaced = set(), set()
    _require(type(metadata.get("removed_highlow")) is list, "Framed removed HIGHLOW inventory missing")
    for row in metadata["removed_highlow"]:
        rva = row.get("rva")
        _require(type(rva) is int and rva in old_fields and rva not in removed
                 and row.get("va") == before.image_base + rva and row.get("offset") == before.file_offset(rva, 4)
                 and _hex(row.get("old_hex")) == scalar[row["offset"]:row["offset"] + 4], "Framed displaced HIGHLOW differs")
        removed.add(rva)
    for rva in old_fields:
        for start, end in hook_spans:
            if start < rva + 4 and rva < end:
                _require(start <= rva and rva + 4 <= end, "Framed partially displaced HIGHLOW")
                displaced.add(rva)
    _require(removed == displaced, "Framed HIGHLOW removal inventory differs")
    fields, hook_fields = metadata.get("relocations"), metadata.get("hook_relocations")
    _require(type(fields) is list and type(hook_fields) is list, "Framed declared operands missing")
    added, operands = [], []
    for row, native in [(r, False) for r in fields] + [(r, True) for r in hook_fields]:
        offset, target, kind = row.get("offset"), row.get("target"), row.get("kind")
        _require(type(offset) is type(target) is int and 0 <= target < 2**32 and kind in ("abs32", "rel32")
                 and type(row.get("purpose")) is str and row["purpose"].strip(), "invalid Framed declared operand")
        if native:
            hook = by_va.get(row.get("hook_va"))
            _require(hook is not None and 0 <= offset <= len(_hex(hook["new_hex"])) - 4
                     and row.get("rva") == hook["rva"] + offset, "Framed hook operand mapping differs")
            rva = hook["rva"] + offset
        else:
            _require(0 <= offset <= size - 4, "Framed operand exceeds code payload")
            rva = section.rva + offset
        target_rva = target - after.image_base
        _require(_owned_target(row, before, after, patches), "Framed operand target is unowned or non-executable")
        expected = target if kind == "abs32" else (target - after.image_base - rva - 4) & 0xFFFFFFFF
        _require(struct.unpack_from("<I", candidate, after.file_offset(rva, 4))[0] == expected, "Framed declared operand differs")
        operands.append(rva)
        if kind == "abs32":
            added.append(rva)
    operands.sort()
    _require(all(a + 4 <= b for a, b in zip(operands, operands[1:])), "Framed declared operands overlap")
    expected_fields = sorted((set(old_fields) - removed) | set(added))
    _require(len(expected_fields) == len(old_fields) - len(removed) + len(added), "Framed HIGHLOW aliases inherited field")
    table, actual = pe._old_relocations(candidate, after)
    merged = bool(removed or any(row["kind"] == "abs32" for row in hook_fields))
    expected_table = pe._relocation_blocks(expected_fields) if merged else old_table + pe._relocation_blocks(added)
    _require(sorted(actual) == expected_fields and table == expected_table
             and metadata.get("relocation_directory_merged") is merged
             and metadata.get("old_relocation_sha256") == sha256(old_table)
             and metadata.get("old_highlow_count") == len(old_fields)
             and metadata.get("retained_highlow_count") == len(old_fields) - len(removed)
             and metadata.get("new_highlow_count") == len(added), "Framed complete HIGHLOW inventory differs")
    table_at = pe._align(size, 4)
    _require(after.relocation_rva == section.rva + table_at and section.virtual_size == table_at + len(table)
             and section.raw_size == pe._align(section.virtual_size, 512)
             and candidate[section.raw_offset + size:section.raw_offset + table_at] == bytes(table_at - size)
             and candidate[section.raw_offset + section.virtual_size:] == bytes(section.raw_size - section.virtual_size)
             and candidate[before.file_offset(before.relocation_rva, len(old_table)):
                           before.file_offset(before.relocation_rva, len(old_table)) + len(old_table)] == old_table,
             "Framed directory location or padding differs")
    # Every extension edit owns a hook, one of five header fields or the tail.
    allowed = {row["offset"] for row in hooks} | {before.pe_offset + 6, before.optional_offset + 4,
        before.optional_offset + 56, before.optional_offset + 136, section.header_offset, len(scalar)}
    _require(len(metadata["edits"]) == len(hooks) + 6 and {row["offset"] for row in metadata["edits"]} == allowed,
             "Framed extension edit ownership differs")
    audit = _geometry_contract(metadata, resolution, geometry)
    audit.update(section_count=8, new_mutable_state_bytes=0, hook_count=len(hooks), scalar_patch_count=len(patches),
                 merged_highlow_count=len(actual), displaced_highlow_count=len(removed), code_bytes=size,
                 legacy_dgroup_fallback_retained=any(row["purpose"] == "framed_gate_old_c5_fallback" for row in fields),
                 scalar_parent_sha256=sha256(scalar))
    return audit


def _loaded_bytes(candidate, view, va, size):
    output = bytearray()
    for rva in range(va - view.image_base, va - view.image_base + size):
        if 0 <= rva < view.headers_size:
            output.append(candidate[rva])
        else:
            matches = [s for s in view.sections if s.rva <= rva < s.rva + s.memory_size]
            _require(len(matches) == 1, "Framed loaded predicate unmapped or ambiguous")
            section = matches[0]
            relative = rva - section.rva
            output.append(candidate[section.raw_offset + relative] if section.raw_offset and relative < section.raw_size else 0)
    return bytes(output)


def _probe(candidate, metadata, inherited, resolution, producer_digest, pe):
    digest, view = sha256(candidate), pe.inspect_pe(candidate)
    old_marker = f".echo PTILE_CONTRACT_PASS stage={FROZEN_STAGE} resolution={resolution} candidate_sha256={digest}"
    _require(type(inherited) is str and inherited.splitlines().count(old_marker) == 1
             and inherited.count("_CONTRACT_PASS") == 1 and any("PTILE_CONTRACT_FAIL" in line for line in inherited.splitlines()[:inherited.splitlines().index(old_marker)]),
             "canonical frozen Framed probe identity differs")
    matches = list(PREDICATE.finditer(inherited))
    _require(bool(matches), "Framed inherited loaded predicates missing")
    for match in matches:
        kind, address, expected = match.groups()
        _require(int.from_bytes(_loaded_bytes(candidate, view, int(address, 16), 2 if kind == "wo" else 1), "little") == int(expected, 16),
                 "Framed inherited loaded predicate differs")
    section = view.sections[-1]
    spans = [(view.image_base, candidate[:view.headers_size]),
             (view.image_base + section.rva, candidate[section.raw_offset:section.raw_offset + section.raw_size])]
    spans += [(row["va"], _hex(row["new_hex"])) for row in metadata["hooks"]]
    conditions = []
    for va, data in spans:
        for offset in range(0, len(data), 2):
            part = data[offset:offset + 2]
            reader = "wo" if len(part) == 2 else "by"
            conditions.append(f"({reader}({va + offset:08x}) != {int.from_bytes(part, 'little'):x})")
    checks = [".if (" + " | ".join(conditions[index:index + 60]) + ") { .echo FRAMED_ALL_PRESETS_CONTRACT_FAIL; q }"
              for index in range(0, len(conditions), 60)]
    marker = (f"FRAMED_ALL_PRESETS_CONTRACT_PASS stage={STAGE} resolution={resolution} candidate_sha256={digest} "
              f"revision={REVISION} producer_sha256={producer_digest}")
    probe = inherited.replace(old_marker, "\n".join(checks + [".echo " + marker]), 1)
    _require(probe.count("_CONTRACT_PASS") == 1 and all(len(line.encode("ascii")) < 4096 for line in probe.splitlines()),
             "Framed ancestor marker or debugger line limit differs")
    _require(probe.replace("\n".join(checks + [".echo " + marker]), old_marker, 1) == inherited,
             "Framed inherited observer changed")
    return probe, dict(complete_marker=marker, retired_ancestor_markers=[old_marker],
        inherited_probe_sha256=sha256(inherited.encode()), inherited_predicate_count=len(matches),
        all_inherited_checks_required=True, requires_loaded_byte_checks=True,
        preferred_address_only=True, initial_map_only=True,
        scope="Initial ordinary map at preferred addresses only; native modal fallback, input, loader rebasing and endurance require independent evidence")


def _json_value(value):
    """Normalize only JSON containers; preserve every value and numeric type."""
    if type(value) is dict:
        _require(all(type(key) is str for key in value), "Framed metadata keys must be strings")
        return {key: _json_value(item) for key, item in value.items()}
    if type(value) in (list, tuple):
        return [_json_value(item) for item in value]
    _require(type(value) in (str, int, float, bool, type(None)), "Framed metadata has a non-JSON type")
    return value


def _canonical(value):
    try:
        return json.dumps(_json_value(value), sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError) as error:
        raise ValueError("noncanonical Framed metadata") from error


def _deterministic(value):
    """Omit only the predecessor's top-level generation stamp, never nested fields."""
    _require(type(value) is dict, "Framed predecessor metadata must be an object")
    result = _json_value(value)
    result.pop("generated_at", None)
    return result


def build_candidate(original: bytes, resolution: str):
    _require(type(original) is bytes and sha256(original) == BASE_SHA256, "unknown original executable SHA-256; Framed successor has no override")
    _require(type(resolution) is str and resolution in RESOLUTIONS, "only the nine canonical Framed validation presets are admitted")
    sources = _sources()
    producer_digest = sha256(sources["src/patcher/framed_all_presets_candidate.py"])
    with _producer(sources) as modules:
        builder, pe, geometry = (modules[name] for name in ("tools/build_framed_candidate.py",
            "src/patcher/pe_extension.py", "src/patcher/framed_viewport.py"))
        _require(builder.STAGE == FROZEN_STAGE and builder.MINIMAP_SOURCE_SHA256 == PINNED_SOURCES[builder.MINIMAP_SOURCE],
                 "frozen Framed producer identity differs")
        candidate, inherited_metadata, inherited_probe = builder.build_candidate(original, resolution, minimap_viewport=True)
        expected_candidate, expected_metadata, expected_probe = builder.build_candidate(original, resolution, minimap_viewport=True)
        _require(type(inherited_probe) is type(expected_probe) is str and inherited_probe == expected_probe,
                 "independently reconstructed frozen Framed probe differs")
        expected_sources = {name: sha256(data) for name, data in sources.items()}
        _require(inherited_metadata.get("source_sha256") == {name: digest for name, digest in expected_sources.items()
                 if name not in ("tools/build_framed_candidate.py", "src/patcher/framed_all_presets_candidate.py")},
                 "Framed producer source inventory differs")
        audit = _audit(original, candidate, inherited_metadata, resolution, pe, geometry,
                       source_context=(expected_candidate, expected_metadata))
        view = pe.inspect_pe(candidate)
        records = byte_records(original, candidate, view)
        _require(apply_records(original, records, expected_base_sha256=BASE_SHA256, view=view) == candidate,
                 "full original-to-final Framed replay differs")
        probe, contract = _probe(candidate, inherited_metadata, inherited_probe, resolution, producer_digest, pe)
    _require(_sources() == sources, "Framed source changed during reconstruction")
    metadata = dict(schema="clash95_framed_all_presets_candidate_v1", stage=STAGE, recipe_revision=REVISION,
        profile="Framed", resolution=resolution, base_sha256=BASE_SHA256, candidate_sha256=sha256(candidate),
        candidate_bytes=len(candidate), source_hashes=expected_sources, producer_sha256=producer_digest,
        patch_records=records, structural_gate=audit, predecessor=_deterministic(inherited_metadata),
        probe_sha256=sha256(probe.encode()), probe_contract=contract, validation_stage_only=True,
        features=dict(framed_map=True, four_frame_bands=True, minimap_viewport=True, native_modal_fallback=True,
                      owned_modal_canvas=False, expanded_battle=False), **{key: False for key in FALSE_CLAIMS},
        limitations=["Source/PE/byte reconstruction is separate from runtime or stable acceptance.",
                     "Ordinary map and AI banner are guarded; unsupported modal and army owners retain native fallback.",
                     "The initial preferred-address probe is not a loader-rebased or full route verifier.",
                     "The source-owned 0x51BE00 DGROUP fallback is preserved; deployment execution protections require native validation.",
                     "Declared operands are source-bound; validation does not discover undeclared operands or prove instruction semantics.",
                     "Expanded battle, launcher registration, manual input, final-wrapper composition and endurance remain separate.",
                     "Custom dimensions, 802x602 and arbitrary originals are not admitted."])
    return candidate, metadata, probe
