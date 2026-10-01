"""Nine-preset Complete HD reconstruction under a separate validation identity.

The frozen complete_hd_v1 recipe is untouched. This constructor executes exact
reviewed predecessor source snapshots in a private namespace, reconstructs the
entire framed/minimap/modal/army chain, and independently audits the final PE
and original-to-final byte replay. It returns bytes only: no installation,
launcher registration, runtime, manual-input acceptance or stable promotion.
Expanded battle hooks are not installed by this recipe.
"""
from __future__ import annotations

import ast
from contextlib import contextmanager
import hashlib
from pathlib import Path
import struct
import sys
import types
from typing import Any
import uuid

ROOT = Path(__file__).resolve().parents[2]
STAGE = (
    "gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-"
    "presentbounds-minimapright-dynvswitch-completehd-allpresets-validation"
)
REVISION = "complete_hd_all_presets_v1"
BASE_SHA256 = "500055d77d03d514e8d3168506bd10f67cd8569bcc450604ff8192f46cdaf3ae"
RESOLUTIONS = (
    "800x600", "1024x768", "1280x720", "1280x960", "1366x768",
    "1920x1080", "2560x1440", "3440x1440", "3840x2160",
)
ARMY_STAGE = (
    "gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-"
    "presentbounds-minimapright-dynvswitch-combinedui-partialtiles-initialpaint-"
    "framed-modalcanvas-army-validation"
)
ARMY_REVISION = "framed_own_army_native_size_v1"
RX = 0x60000020
RW = 0xC0000040
FALSE_CLAIMS = ("installation_ready", "runtime_executed", "manual_input_proof", "promotion_ready")

# Exact producer bytes, including the frozen sibling as a preservation guard.
# No caller-supplied pin, executable identity, emitter or verifier override exists.
PINNED_SOURCES = {
    "src/patcher/complete_hd_candidate.py": "e406149480e9cdf1ba0314f5e9ae735d7b587f61772afac4b0b9e7ce9fd3bd06",
    "src/patcher/four_sided_frame.py": "433fd27fb8afda4a12f5539604f722f18bf8d37885125e30ee9cfb948926c2a9",
    "src/patcher/framed_army_composition.py": "7639e0b96bfc96d0f9c39b6c17126b376cc40e7ab37407b2a86d72bc626c511c",
    "src/patcher/framed_army_draw.py": "6b936157da3aa652a74887b9470318a0df745c7694bda4d7ee79004a23a191e9",
    "src/patcher/framed_army_input.py": "01a3dcc5bb584d53efd809c8fbe2303807b2bdf0e22d095bc3c3155e6c651efb",
    "src/patcher/framed_army_viewport.py": "6f091c2655ee47392541b6d15db24346e3c26dc43158942426bc939a1e158224",
    "src/patcher/framed_full_paint.py": "d496fe9eca8ebe02c34f5680aee4fe2683b4b3849d65fe5f4e5f17b4e118c91a",
    "src/patcher/framed_input.py": "a2557f1ca7caf23a957a21bf747ac23d875b27e7706de26d463b98ae221ce810",
    "src/patcher/framed_minimap.py": "90a345f1080f0b69107f99d1ec1687d1a28faab2e72e5daae6bee467fa31a6d7",
    "src/patcher/framed_modal_canvas.py": "567b025520184a99f1f4f44b23a879ef9c729dcf2917dfa03a277c018cb20054",
    "src/patcher/framed_presentation.py": "70619f5c25faac66a668c19f989e55a8d4e4662c24c78286e16c233cc564ab6d",
    "src/patcher/framed_recipe.py": "559b571ce1dd83421f79a58e110cd5b6317807cd68087d7ea77f14c4f4a071b4",
    "src/patcher/framed_viewport.py": "1d5bc64777cf01c68f587bc3fee2dc7d5024696bd6b1712dab4e6e78f78c4c42",
    "src/patcher/initial_map_paint.py": "79e6d6d180a115b2b59e98600038fa3a31707a373c0095489bb706182078ba91",
    "src/patcher/partial_tile_clip.py": "92421c123a75bef119bfa93b438f813ec18dcb073699327cf15b7a1b884bcfad",
    "src/patcher/partial_tile_hooks.py": "71ce9390a3018c80811a1e57b36dc47b59928cb3d9deec364e9b195f94465419",
    "src/patcher/patch_clash95_hd.py": "38021e9a4d21bc9a8bf0c2f9b66379595509446b5177d6f91bab6f677b5e8106",
    "src/patcher/pe_army_extension.py": "d82ce5c3fb2b0927c6ab541705eb20c4cc7d7d92c889f253f059321c8ec056fb",
    "src/patcher/pe_extension.py": "4d66e7fa3bf17c6260fffaefc8d4e4e8da0ba76ceea7746858c52299f74d7c27",
    "src/patcher/pe_modal_extension.py": "26dca892c289760924031dc9a752de1eecd7ecdeb6ac18f2a6949c1a3b6f233f",
    "tools/build_framed_army_candidate.py": "ec5989d86d8252c43b7a73c8b2bfd612e5050434adcbeecf58dbe47bf96d1114",
    "tools/build_framed_candidate.py": "fbe2f2c571154312329ab23603d8de45fb8ec5fafcdfd10bad4049876dfb14bc",
    "tools/build_framed_modal_candidate.py": "ec7c933fd9112b556636510f0b762076fc5f8c4c2e86bbc704b70f26cddf98d1",
    "tools/build_partial_tile_candidate.py": "363eaabfca63e435448355c406e6390e05b4151ffb928114221032c30b2cd255",
    "tools/partial_tile_trace_probe.py": "a20512fa49cc86db67a486f9202d4efa3f9f3745005d11220bf6097661a44729",
}
MODULE_ORDER = tuple("src/patcher/" + stem + ".py" for stem in (
    "framed_viewport", "patch_clash95_hd", "partial_tile_clip", "pe_extension",
    "framed_recipe", "partial_tile_hooks", "four_sided_frame", "framed_full_paint",
    "initial_map_paint", "framed_presentation", "framed_input", "framed_minimap",
)) + (
    "tools/partial_tile_trace_probe.py", "tools/build_partial_tile_candidate.py",
    "tools/build_framed_candidate.py", "src/patcher/pe_modal_extension.py",
    "src/patcher/framed_modal_canvas.py", "tools/build_framed_modal_candidate.py",
    "src/patcher/pe_army_extension.py", "src/patcher/framed_army_viewport.py",
    "src/patcher/framed_army_input.py", "src/patcher/framed_army_draw.py",
    "src/patcher/framed_army_composition.py", "tools/build_framed_army_candidate.py",
)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _sources() -> dict[str, bytes]:
    result = {}
    for name, digest in PINNED_SOURCES.items():
        path = ROOT / name
        _require(path.resolve() == path and path.is_relative_to(ROOT), "noncanonical producer source path")
        data = path.read_bytes()
        _require(sha256(data) == digest, "reviewed producer source differs: " + name)
        result[name] = data
    return result


class _PrivateImports(ast.NodeTransformer):
    def __init__(self, prefix: str):
        self.prefix = prefix
        self.bare_tools = {Path(name).stem for name in MODULE_ORDER if name.startswith("tools/")}

    def visit_ImportFrom(self, node: ast.ImportFrom) -> ast.ImportFrom:
        if not node.level and node.module:
            if node.module in ("src", "tools") or node.module.startswith(("src.", "tools.")):
                node.module = self.prefix + "." + node.module
            elif node.module in self.bare_tools:
                node.module = self.prefix + ".tools." + node.module
        return node


@contextmanager
def _producer(sources: dict[str, bytes]):
    """Execute authenticated snapshots, never existing import aliases or pyc.

    Empty package search paths make an unexpected import fail rather than load
    unreviewed project code. The predecessor's own nested reconstruction still
    authenticates its complete chain and restores its temporary import state.
    """
    prefix = "_clash95_all_presets_" + uuid.uuid4().hex
    saved_path = list(sys.path)
    try:
        for suffix in ("", ".src", ".src.patcher", ".tools"):
            package = types.ModuleType(prefix + suffix)
            package.__path__ = []
            sys.modules[package.__name__] = package
            if suffix:
                parent, _, leaf = package.__name__.rpartition(".")
                setattr(sys.modules[parent], leaf, package)
        for name in MODULE_ORDER:
            full = prefix + "." + name.removesuffix(".py").replace("/", ".")
            module = types.ModuleType(full)
            module.__file__ = str(ROOT / name)
            module.__package__ = full.rpartition(".")[0]
            sys.modules[full] = module
            setattr(sys.modules[module.__package__], full.rpartition(".")[2], module)
            tree = _PrivateImports(prefix).visit(ast.parse(sources[name], module.__file__))
            exec(compile(tree, module.__file__, "exec"), module.__dict__)
        yield (sys.modules[prefix + ".tools.build_framed_army_candidate"],
               sys.modules[prefix + ".src.patcher.pe_extension"],
               sys.modules[prefix + ".src.patcher.framed_army_viewport"])
    finally:
        for name in list(sys.modules):
            if name == prefix or name.startswith(prefix + "."):
                del sys.modules[name]
        sys.path[:] = saved_path


def _hex(value: Any) -> bytes:
    _require(type(value) is str and len(value) % 2 == 0, "noncanonical byte hex")
    try:
        result = bytes.fromhex(value)
    except ValueError as error:
        raise ValueError("noncanonical byte hex") from error
    _require(result.hex() == value, "noncanonical byte hex")
    return result


def _address(view: Any, offset: int) -> tuple[int | None, int | None]:
    if offset < view.headers_size:
        return offset, view.image_base + offset
    for section in view.sections:
        if section.raw_offset and section.raw_offset <= offset < section.raw_offset + section.raw_size:
            rva = section.rva + offset - section.raw_offset
            return rva, view.image_base + rva
    return None, None


def byte_records(original: bytes, candidate: bytes, view: Any) -> list[dict[str, Any]]:
    """Describe all changed bytes and every appended byte, with final mapping."""
    _require(type(original) is bytes and type(candidate) is bytes and len(candidate) >= len(original),
             "immutable nontruncated images required")
    records = []
    position = 0
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
            old_hex=original[start:position].hex(), new_hex=candidate[start:position].hex(),
            group="complete-hd-all-presets-extension" if start >= len(original) else "complete-hd-all-presets-integrated",
            stage=STAGE, rationale="Exact source reconstruction of framed, minimap, native modal and army layers",
            appended=start >= len(original)))
    return records


def apply_records(original: bytes, records: list[dict[str, Any]], *, expected_base_sha256: str,
                  view: Any) -> bytes:
    """Replay strictly ordered old-byte checks. This primitive grants no acceptance."""
    _require(type(original) is bytes and sha256(original) == expected_base_sha256, "byte replay base SHA-256 differs")
    _require(type(records) is list, "byte records must be an explicit list")
    output = bytearray(original)
    last_end = 0
    for row in records:
        _require(type(row) is dict, "invalid byte record")
        offset = row.get("file_offset")
        _require(type(offset) is int and offset >= last_end and type(row.get("offset")) is int
                 and row["offset"] == offset and row.get("stage") == STAGE, "invalid or overlapping byte record")
        old, new = _hex(row.get("old_hex")), _hex(row.get("new_hex"))
        _require(bool(new) and type(row.get("appended")) is bool and row["appended"] == (offset >= len(original)),
                 "byte record append identity differs")
        _require(type(row.get("rationale")) is str and bool(row["rationale"].strip()), "byte record rationale missing")
        rva, va = _address(view, offset)
        _require((row.get("rva"), row.get("va")) == (rva, va)
                 and (rva is None or type(row.get("rva")) is type(row.get("va")) is int),
                 "byte record VA/RVA mapping differs")
        if old:
            _require(offset + len(old) <= len(original) and len(old) == len(new)
                     and output[offset:offset + len(old)] == old, "byte record old bytes differ")
            output[offset:offset + len(old)] = new
        else:
            _require(offset == len(output) and row["appended"], "appended byte records must be contiguous")
            output.extend(new)
        last_end = offset + len(new)
    return bytes(output)


def _undo_edits(candidate: bytes, metadata: dict[str, Any], pe: Any) -> bytes:
    """Independently reconstruct the entire immediate parent from declared edits."""
    view = pe.inspect_pe(candidate)
    edits = metadata.get("edits")
    _require(type(edits) is list and bool(edits), "complete predecessor edits missing")
    decoded = []
    for row in edits:
        _require(type(row) is dict and type(row.get("offset")) is int and row["offset"] >= 0,
                 "invalid predecessor edit offset")
        offset = row["offset"]
        old, new = _hex(row.get("old_hex")), _hex(row.get("new_hex"))
        rva, va = _address(view, offset)
        _require(type(row.get("rva")) is int and type(row.get("va")) is int
                 and (row["rva"], row["va"]) == (rva, va), "predecessor edit mapping differs")
        _require(bool(new) and (not old or len(old) == len(new))
                 and candidate[offset:offset + len(new)] == new, "predecessor edit final bytes differ")
        decoded.append((offset, old, new))
    decoded.sort(key=lambda item: item[0])
    _require(all(a[0] + len(a[2]) <= b[0] for a, b in zip(decoded, decoded[1:])), "predecessor edits overlap")
    appends = [row for row in decoded if not row[1]]
    _require(bool(appends), "predecessor append missing")
    base_length = appends[0][0]
    end = base_length
    for offset, _, new in appends:
        _require(offset == end, "predecessor append gap")
        end += len(new)
    _require(end == len(candidate), "predecessor append does not own the complete final tail")
    parent = bytearray(candidate[:base_length])
    for offset, old, new in decoded:
        if old:
            _require(offset + len(new) <= base_length, "predecessor edit crosses append boundary")
            parent[offset:offset + len(old)] = old
    parent = bytes(parent)
    _require(sha256(parent) == metadata.get("input_sha256"), "reconstructed predecessor SHA-256 differs")
    return parent


def _audit_army(candidate: bytes, metadata: dict[str, Any], pe: Any) -> tuple[bytes, dict[str, Any]]:
    """Final allocation, ownership, installed bytes and complete relocation gate."""
    _require(metadata.get("output_sha256") == sha256(candidate), "army output identity differs")
    parent = _undo_edits(candidate, metadata, pe)
    before, final = pe.inspect_pe(parent), pe.inspect_pe(candidate)
    _require(len(before.sections) == 10 and len(final.sections) == 11 and final.sections[:10] == before.sections,
             "army section ownership differs")
    code = final.sections[-1]
    _require(code.name.rstrip(b"\0") == b".hdarmy" and code.characteristics == RX
             and code.virtual_size == 0x20000 and code.raw_offset == len(parent)
             and code.raw_offset + code.raw_size == len(candidate)
             and code.header_offset == 0x2F8 and code.rva == before.image_size,
             "army allocation or protection differs")
    _require((final.section_alignment, final.file_alignment, final.headers_size) == (4096, 512, 1024)
             and final.image_size == code.rva + code.virtual_size
             and all(a.rva + pe._align(a.memory_size, 4096) == b.rva
                     for a, b in zip(final.sections, final.sections[1:])), "final PE extents differ")
    _require(metadata.get("state_va") is None and type(metadata.get("state_bytes")) is int
             and metadata["state_bytes"] == 0 and metadata.get("state_raw_offset") is None
             and metadata.get("state_characteristics") is None, "unexpected army mutable storage")
    _require(all(metadata.get(key) is False for key in FALSE_CLAIMS), "predecessor acceptance claim must remain false")
    _require(metadata.get("retired_header_scratch") == dict(start=0x300, end_exclusive=0x348,
             legacy_day_diagnostic_allowed=False), "retired header diagnostic policy differs")
    size = metadata.get("code_bytes")
    _require(type(size) is int and 0 < size <= code.raw_size
             and metadata.get("code_va") == final.image_base + code.rva
             and metadata.get("code_rva") == code.rva
             and metadata.get("code_raw_bytes") == code.raw_size
             and metadata.get("code_virtual_bytes") == code.virtual_size
             and metadata.get("code_characteristics") == RX, "army code extent identity differs")
    payload = candidate[code.raw_offset:code.raw_offset + size]
    _require(metadata.get("code_sha256") == sha256(payload), "army code SHA-256 differs")
    hooks = metadata.get("hooks")
    _require(type(hooks) is list and len(hooks) == 10, "ten army hooks required")
    hook_by_va = {}
    hook_spans = []
    for row in hooks:
        offset, rva, va = row.get("offset"), row.get("rva"), row.get("va")
        old, new = _hex(row.get("old_hex")), _hex(row.get("new_hex"))
        _require(all(type(value) is int for value in (offset, rva, va)) and bool(old) and len(old) == len(new)
                 and va == final.image_base + rva and final.file_offset(rva, len(new)) == offset
                 and parent[offset:offset + len(old)] == old and candidate[offset:offset + len(new)] == new
                 and any(s.characteristics & 0x20000000 and s.rva <= rva
                         and rva + len(new) <= s.rva + s.raw_size for s in before.sections), "army installed hook differs")
        _require(va not in hook_by_va, "duplicate army hook")
        hook_by_va[va] = row
        hook_spans.append((rva, rva + len(new)))
    hook_spans.sort()
    _require(all(a[1] <= b[0] for a, b in zip(hook_spans, hook_spans[1:])), "army hooks overlap")
    old_table, old_locations = pe._old_relocations(parent, before)
    removed_rows = metadata.get("removed_highlow")
    _require(type(removed_rows) is list, "explicit displaced relocation inventory missing")
    removed = set()
    for row in removed_rows:
        rva = row.get("rva")
        _require(type(rva) is int and rva in old_locations and rva not in removed
                 and row.get("va") == before.image_base + rva and row.get("offset") == before.file_offset(rva, 4)
                 and _hex(row.get("old_hex")) == parent[row["offset"]:row["offset"] + 4], "displaced HIGHLOW identity differs")
        removed.add(rva)
    displaced = set()
    for rva in old_locations:
        for start, end in hook_spans:
            if rva < end and start < rva + 4:
                _require(start <= rva and rva + 4 <= end, "army hook partially displaces HIGHLOW")
                displaced.add(rva)
    _require(removed == displaced, "army HIGHLOW removal inventory differs")
    added, operand_spans = [], []
    fields = metadata.get("relocations")
    hook_fields = metadata.get("hook_relocations")
    _require(type(fields) is list and type(hook_fields) is list, "explicit relocation fields missing")
    for row, hook_field in [(r, False) for r in fields] + [(r, True) for r in hook_fields]:
        offset, kind, target = row.get("offset"), row.get("kind"), row.get("target")
        _require(type(offset) is int and kind in ("abs32", "rel32") and type(target) is int
                 and 0 <= target < 2**32 and type(row.get("purpose")) is str and bool(row["purpose"].strip()),
                 "invalid declared relocation field")
        if hook_field:
            hook = hook_by_va.get(row.get("hook_va"))
            _require(hook is not None and 0 <= offset <= len(_hex(hook["new_hex"])) - 4
                     and row.get("rva") == hook["rva"] + offset, "hook relocation mapping differs")
            field_rva = hook["rva"] + offset
        else:
            _require(0 <= offset <= size - 4, "code relocation outside army payload")
            field_rva = code.rva + offset
        target_rva = target - final.image_base
        _require(any(s.rva <= target_rva < s.rva + s.memory_size
                     and (kind == "abs32" or s.characteristics & 0x20000000) for s in final.sections),
                 "declared relocation target is unowned or non-executable")
        actual = struct.unpack_from("<I", candidate, final.file_offset(field_rva, 4))[0]
        expected = target if kind == "abs32" else (target - final.image_base - field_rva - 4) & 0xFFFFFFFF
        _require(actual == expected, "declared relocation operand differs")
        operand_spans.append(field_rva)
        if kind == "abs32":
            added.append(field_rva)
    operand_spans.sort()
    _require(all(a + 4 <= b for a, b in zip(operand_spans, operand_spans[1:])), "declared relocation operands overlap")
    expected_locations = sorted((set(old_locations) - removed) | set(added))
    _require(len(expected_locations) == len(old_locations) - len(removed) + len(added), "new HIGHLOW aliases inherited field")
    table, actual_locations = pe._old_relocations(candidate, final)
    _require(list(actual_locations) == expected_locations and table == pe._relocation_blocks(expected_locations)
             and metadata.get("old_relocation_sha256") == sha256(old_table)
             and metadata.get("merged_relocation_sha256") == sha256(table)
             and metadata.get("old_highlow_count") == len(old_locations)
             and metadata.get("retained_highlow_count") == len(old_locations) - len(removed)
             and metadata.get("new_highlow_count") == len(added), "complete merged HIGHLOW inventory differs")
    table_offset = pe._align(size, 4)
    _require(final.relocation_rva == code.rva + table_offset and metadata.get("relocation_rva") == final.relocation_rva
             and metadata.get("relocation_bytes") == final.relocation_size
             and candidate[code.raw_offset + size:code.raw_offset + table_offset] == bytes(table_offset - size)
             and candidate[code.raw_offset + table_offset + len(table):] == bytes(code.raw_size - table_offset - len(table)),
             "army directory location or allocation padding differs")
    old_offset = before.file_offset(before.relocation_rva, before.relocation_size)
    _require(candidate[old_offset:old_offset + len(old_table)] == old_table, "inherited relocation table overwritten")
    return parent, dict(section_count=len(final.sections), army_hook_count=len(hooks),
        army_operand_count=len(operand_spans), merged_highlow_count=len(actual_locations),
        old_highlow_count=len(old_locations), removed_highlow_count=len(removed),
        army_code_bytes=size, army_raw_bytes=code.raw_size, army_reserved_bytes=code.virtual_size)


def _audit_final(original: bytes, candidate: bytes, metadata: dict[str, Any], resolution: str,
                 pe: Any, geometry: Any) -> dict[str, Any]:
    _require(metadata.get("stage") == ARMY_STAGE and metadata.get("army_revision") == ARMY_REVISION
             and metadata.get("resolution") == resolution and metadata.get("minimap_viewport") is True
             and metadata.get("original_sha256") == BASE_SHA256, "reconstructed recipe identity differs")
    parent, audit = _audit_army(candidate, metadata, pe)
    modal = metadata.get("base_candidate")
    _require(type(modal) is dict and modal.get("output_sha256") == sha256(parent)
             and metadata.get("base_candidate_sha256") == sha256(parent)
             and all(modal.get(key) is False for key in FALSE_CLAIMS), "modal ancestry or acceptance identity differs")
    framed = _undo_edits(parent, modal, pe)
    _require(modal.get("base_candidate_sha256") == sha256(framed)
             and modal.get("base_candidate", {}).get("output_sha256") == sha256(framed), "framed ancestry differs")
    final, initial = pe.inspect_pe(candidate), pe.inspect_pe(original)
    _require(len(initial.sections) == 7 and final.sections[:7] == initial.sections
             and final.image_base == initial.image_base
             and struct.unpack_from("<I", candidate, final.optional_offset + 16)[0]
                 == struct.unpack_from("<I", original, initial.optional_offset + 16)[0]
             and tuple(s.name.rstrip(b"\0") for s in final.sections[-4:]) == (b".hdcode", b".hdmodal", b".hdstate", b".hdarmy")
             and tuple(s.characteristics for s in final.sections[-4:]) == (RX, RX, RW, RX), "original or extension ownership differs")
    modal_section, state = final.sections[-3:-1]
    _require(modal_section.virtual_size == 0x20000 and modal_section.raw_size == modal.get("code_raw_bytes")
             and modal.get("code_va") == final.image_base + modal_section.rva
             and type(modal.get("code_bytes")) is int and 0 < modal["code_bytes"] <= modal_section.raw_size
             and sha256(candidate[modal_section.raw_offset:modal_section.raw_offset + modal["code_bytes"]]) == modal.get("code_sha256"),
             "final modal code identity differs")
    _require(state.virtual_size == state.raw_size == modal.get("state_bytes") == 4096
             and state.rva == modal_section.rva + modal_section.virtual_size
             and state.raw_offset == modal.get("state_raw_offset") and modal.get("state_va") == final.image_base + state.rva
             and candidate[state.raw_offset:state.raw_offset + state.raw_size] == bytes(4096), "modal state allocation or initialization differs")
    _require(type(modal.get("hooks")) is list and len(modal["hooks"]) == 6, "six modal hooks required")
    for row in modal["hooks"]:
        new = _hex(row.get("new_hex"))
        _require(type(row.get("va")) is type(row.get("rva")) is type(row.get("offset")) is int
                 and row["va"] == final.image_base + row["rva"]
                 and final.file_offset(row["rva"], len(new)) == row["offset"]
                 and candidate[row["offset"]:row["offset"] + len(new)] == new, "final modal hook differs")
    width, height = map(int, resolution.split("x"))
    layout = geometry.FramedArmyViewport(width, height)
    contracts = metadata.get("army_contracts", {})
    mouse, draw, panel = (contracts.get(name, {}) for name in ("input", "draw", "composition"))
    backing, hit = list(layout.backing.as_tuple()), list(layout.hit.as_tuple())
    _require(list(mouse.get("backing", [])) == list(panel.get("backing", [])) == draw.get("backing_rect") == backing
             and list(mouse.get("hit", [])) == list(panel.get("hit", [])) == hit
             and mouse.get("whole_candidate_reconstructed") is True and mouse.get("native_mouse_untouched") is True
             and draw.get("candidate_reconstructed") is True and draw.get("portrait_origin") == [38, height - 81]
             and draw.get("portrait_size") == [32, 64] and draw.get("slot_pitch") == 38
             and draw.get("minimap_viewport") is True and draw.get("requires_readable_thread_owned_context") is True
             and draw.get("requires_canonical_memory_vtable") is True and draw.get("native_fallback_retained") is True
             and panel.get("unsupported_owner_is_original_fallback") is True
             and panel.get("original_generators_unchanged") is True and panel.get("runtime_executed") is False,
             "army ownership or resolution geometry contract differs")
    audit.update(modal_parent_sha256=sha256(parent), framed_parent_sha256=sha256(framed),
                 modal_state_bytes=4096, native_portrait_size=[32, 64], army_backing=backing, army_hit=hit)
    return audit


def _probe(inherited: str, metadata: dict[str, Any], resolution: str, digest: str,
           producer_digest: str) -> tuple[str, dict[str, Any]]:
    inherited_marker = f".echo PTILE_CONTRACT_PASS stage={ARMY_STAGE} resolution={resolution} candidate_sha256={digest}"
    army_marker = (f".echo ARMY_CONTRACT_PASS stage={ARMY_STAGE} resolution={resolution} "
                   f"candidate_sha256={digest} revision={ARMY_REVISION}")
    _require(type(inherited) is str, "inherited probe must be text")
    lines = inherited.splitlines()
    _require(metadata.get("initial_probe_sha256") == sha256(inherited.encode())
             and lines.count(inherited_marker) == lines.count(army_marker) == 1
             and lines.index(army_marker) < lines.index(inherited_marker)
             and any("ARMY_CONTRACT_FAIL" in line for line in lines[:lines.index(army_marker)]),
             "inherited loaded-byte probe identity differs")
    marker = (f".echo COMPLETEHD_ALL_PRESETS_CONTRACT_PASS stage={STAGE} resolution={resolution} "
              f"candidate_sha256={digest} revision={REVISION} producer_sha256={producer_digest}")
    _require(marker not in inherited and "COMPLETEHD_CONTRACT_PASS" not in inherited, "unexpected sibling probe identity")
    probe = inherited.replace(inherited_marker, marker + "\n" + inherited_marker, 1)
    _require(probe.replace(marker + "\n", "", 1) == inherited, "inherited probe predicates changed")
    return probe, dict(complete_marker=marker.removeprefix(".echo "),
        inherited_marker=inherited_marker.removeprefix(".echo "), army_marker=army_marker.removeprefix(".echo "),
        inherited_stage=ARMY_STAGE, inherited_probe_sha256=sha256(inherited.encode()),
        requires_loaded_byte_checks=True, all_inherited_checks_required=True,
        scope="Initial ordinary-map observer only; battle, input, lifecycle and endurance require independent evidence")


def _deterministic(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _deterministic(item) for key, item in value.items() if key != "generated_at"}
    if isinstance(value, (tuple, list)):
        return [_deterministic(item) for item in value]
    return value


def build_candidate(original: bytes, resolution: str) -> tuple[bytes, dict[str, Any], str]:
    _require(type(original) is bytes and sha256(original) == BASE_SHA256,
             "unknown original executable SHA-256; all-presets recipe has no override")
    _require(type(resolution) is str and resolution in RESOLUTIONS, "only the nine canonical validation presets are admitted")
    sources = _sources()
    producer_path = Path(__file__).resolve()
    _require(producer_path == ROOT / "src/patcher/complete_hd_all_presets_candidate.py", "noncanonical constructor path")
    producer_bytes = producer_path.read_bytes()
    producer_digest = sha256(producer_bytes)
    with _producer(sources) as (army, pe, geometry):
        _require(army.STAGE == ARMY_STAGE and army.REVISION == ARMY_REVISION, "bound producer revision differs")
        candidate, predecessor, inherited = army.build_candidate(original, resolution, minimap_viewport=True)
        audit = _audit_final(original, candidate, predecessor, resolution, pe, geometry)
        view = pe.inspect_pe(candidate)
        records = byte_records(original, candidate, view)
        _require(apply_records(original, records, expected_base_sha256=BASE_SHA256, view=view) == candidate,
                 "complete byte replay differs")
    digest = sha256(candidate)
    probe, probe_contract = _probe(inherited, predecessor, resolution, digest, producer_digest)
    _require(_sources() == sources and producer_path.read_bytes() == producer_bytes, "producer source changed during reconstruction")
    expected_sources = {name: sha256(data) for name, data in sources.items()}
    _require(all(expected_sources.get(name) == digest for name, digest in predecessor["source_sha256"].items())
             and predecessor.get("builder_sha256") == expected_sources["tools/build_framed_army_candidate.py"],
             "predecessor source identities differ from exact producer snapshots")
    expected_sources["src/patcher/complete_hd_all_presets_candidate.py"] = producer_digest
    metadata = dict(schema="clash95_complete_hd_all_presets_candidate_v1", stage=STAGE,
        recipe_revision=REVISION, resolution=resolution, base_sha256=BASE_SHA256,
        candidate_sha256=digest, candidate_bytes=len(candidate), source_hashes=expected_sources,
        patch_records=records, structural_gate=audit, probe_sha256=sha256(probe.encode()),
        probe_contract=probe_contract, predecessor=_deterministic(predecessor),
        features=dict(framed_map=True, minimap_viewport=True, native_modal_canvas=True,
                      army_panel=True, centered_native_battle=True, expanded_battle=False),
        expanded_battle_installed=False, launcher_registered=False, validation_stage_only=True,
        installation_ready=False, runtime_executed=False, manual_input_proof=False, promotion_ready=False,
        limitations=["Source reconstruction and PE/byte integrity are separate from runtime or stable acceptance.",
                     "Inherited rendering, input, frame continuity and hidden-soak failures require fresh exact-candidate evidence.",
                     "Expanded battle hooks are uninstalled; the initial-map probe cannot establish battle behavior.",
                     "Declared operands come from the pinned emitter; validation does not discover omitted fields or prove instruction semantics.",
                     "The inherited preferred-address probe is not a loader-rebased verifier or complete runtime observation protocol.",
                     "Custom sizes and the historical 802x602 diagnostic are not admitted by this nine-preset recipe."])
    return candidate, metadata, probe
