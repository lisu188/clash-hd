"""Nine-preset Classic source reconstruction, preserving the frozen recipes.

The two narrow presets use the unchanged scalar stage. Seven wider presets
use its existing menu-only extension. This constructor adds no patch bytes,
performs no file output, and supplies no runtime or release acceptance.
"""
from __future__ import annotations

from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import re
import struct
import sys
import types
from typing import Any
import uuid

ROOT = Path(__file__).resolve().parents[2]
STABLE_STAGE = ("gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-"
                "presentbounds-minimapright-dynvswitch")
STAGE = STABLE_STAGE + "-classic-allpresets-validation"
REVISION = "classic_all_presets_v1"
BASE_SHA256 = "500055d77d03d514e8d3168506bd10f67cd8569bcc450604ff8192f46cdaf3ae"
RESOLUTIONS = ("800x600", "1024x768", "1280x720", "1280x960", "1366x768",
               "1920x1080", "2560x1440", "3440x1440", "3840x2160")
SCALAR_REVISION = "classic-frozen-800-v1"
MENU_REVISION = "classic_menu_widgets_v1"
MENU_STAGE = STABLE_STAGE + "-menuwidgets-validation"
SOURCE = "src/patcher/classic_all_presets_candidate.py"
PINNED_SOURCES = {
    "src/patcher/framed_viewport.py": "1d5bc64777cf01c68f587bc3fee2dc7d5024696bd6b1712dab4e6e78f78c4c42",
    "src/patcher/patch_clash95_hd.py": "38021e9a4d21bc9a8bf0c2f9b66379595509446b5177d6f91bab6f677b5e8106",
    "src/patcher/partial_tile_clip.py": "92421c123a75bef119bfa93b438f813ec18dcb073699327cf15b7a1b884bcfad",
    "src/patcher/pe_extension.py": "4d66e7fa3bf17c6260fffaefc8d4e4e8da0ba76ceea7746858c52299f74d7c27",
    "src/patcher/classic_menu_candidate.py": "0f32f76ab321cf4793020064a7491fb0e7b8a9c4a1ed0f9c73a81e34f6538473",
}
MODULE_ORDER = tuple(PINNED_SOURCES)
FALSE_CLAIMS = ("installation_ready", "runtime_executed", "gameplay_verified", "manual_input_proof",
                "expanded_battle_installed", "launcher_registered", "matrix_registered", "promotion_ready")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _canonical(value: Any) -> str:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError) as error:
        raise ValueError("noncanonical metadata") from error


def _same(actual: Any, expected: Any, message: str) -> None:
    _require(_canonical(actual) == _canonical(expected), message)


def _sources() -> dict[str, bytes]:
    result = {}
    for name, digest in PINNED_SOURCES.items():
        path = ROOT / name
        _require(path.resolve() == path and path.is_relative_to(ROOT), "noncanonical producer source path")
        result[name] = path.read_bytes()
        _require(sha256(result[name]) == digest, "reviewed producer source differs: " + name)
    return result


@contextmanager
def _producer(sources: dict[str, bytes]):
    """Execute exact snapshots with private relative imports and no pyc/aliases."""
    _require(type(sources) is dict and set(sources) == set(PINNED_SOURCES)
             and all(type(sources[name]) is bytes and sha256(sources[name]) == digest
                     for name, digest in PINNED_SOURCES.items()), "producer snapshot identity differs")
    prefix = "_clash95_classic_all_presets_" + uuid.uuid4().hex
    before_path = list(sys.path)
    try:
        for suffix in ("", ".src", ".src.patcher"):
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
            exec(compile(sources[name], module.__file__, "exec"), module.__dict__)
        scalar = sys.modules[prefix + ".src.patcher.patch_clash95_hd"]
        menu = sys.modules[prefix + ".src.patcher.classic_menu_candidate"]
        parser = sys.modules[prefix + ".src.patcher.pe_extension"]
        _require(scalar.DEFAULT_STAGE == STABLE_STAGE and scalar.EXPECTED_SHA256 == BASE_SHA256
                 and menu.STAGE == MENU_STAGE and menu.REVISION == MENU_REVISION
                 and menu.MIN_WIDTH == 1144 and menu.scalar is scalar and menu.pe is parser,
                 "frozen predecessor constants or import identities differ")
        yield scalar, menu, parser
    finally:
        for name in list(sys.modules):
            if name == prefix or name.startswith(prefix + "."):
                del sys.modules[name]
        sys.path[:] = before_path


def _geometry(resolution: str) -> dict[str, Any]:
    _require(type(resolution) is str and resolution in RESOLUTIONS,
             "only the nine canonical Classic presets are admitted")
    width, height = map(int, resolution.split("x"))
    tx, ty = (width - 32) // 64, (height - 16) // 64
    return dict(width=width, height=height, origin=[32, 16], full_tiles=[tx, ty],
                terrain=[32, 16, 32 + 64 * tx - 1, 16 + 64 * ty - 1],
                partial_pixels=[(width - 32) % 64, (height - 16) % 64],
                native_offset=[(width - 640) // 2, (height - 480) // 2],
                minimap_right_anchor=width, minimap_viewport=False, framed_map=False,
                coverage_policy="Frozen native full-tile grid and legacy partial strips",
                small_world_renderer_installed=False)


def _selected(resolution: str) -> tuple[str, str]:
    width = _geometry(resolution)["width"]
    return (MENU_REVISION, MENU_STAGE) if width >= 1144 else (SCALAR_REVISION, STABLE_STAGE)


def _hex(value: Any) -> bytes:
    _require(type(value) is str and len(value) % 2 == 0, "noncanonical byte hex")
    try:
        result = bytes.fromhex(value)
    except ValueError as error:
        raise ValueError("noncanonical byte hex") from error
    _require(result.hex() == value, "noncanonical byte hex")
    return result


def _address(view: Any, offset: int, size: int = 1) -> tuple[int, int]:
    _require(type(offset) is type(size) is int and offset >= 0 and size > 0, "invalid byte mapping")
    if offset + size <= view.headers_size:
        return offset, view.image_base + offset
    matches = [section.rva + offset - section.raw_offset for section in view.sections
               if section.raw_offset and section.raw_offset <= offset
               and offset + size <= section.raw_offset + section.raw_size]
    _require(len(matches) == 1, "bytes do not map to one file-backed PE span")
    return matches[0], view.image_base + matches[0]


def _scalar_replay(original: bytes, patches: Any) -> bytes:
    _require(type(original) is bytes and isinstance(patches, (list, tuple)) and bool(patches),
             "immutable original and explicit scalar patches required")
    spans, output = [], bytearray(original)
    for patch in patches:
        offset, old, new = patch.offset, patch.old, patch.new
        _require(type(offset) is int and offset >= 0 and type(old) is type(new) is bytes
                 and len(old) == len(new) > 0 and offset + len(old) <= len(original)
                 and original[offset:offset + len(old)] == old, "scalar old bytes or extent differ")
        spans.append((offset, offset + len(old)))
        output[offset:offset + len(new)] = new
    spans.sort()
    _require(all(a[1] <= b[0] for a, b in zip(spans, spans[1:])), "scalar patch spans overlap")
    return bytes(output)


def _audit_scalar(original: bytes, candidate: bytes, patches: Any, resolution: str, parser: Any) -> dict:
    geometry = _geometry(resolution)
    _require(type(candidate) is bytes and _scalar_replay(original, patches) == candidate,
             "scalar original-to-final reconstruction differs")
    before, final = parser.inspect_pe(original), parser.inspect_pe(candidate)
    _require(len(before.sections) == 7 and final == before
             and original[:before.headers_size] == candidate[:final.headers_size],
             "scalar PE/header ownership differs")
    table, locations = parser._old_relocations(original, before)
    _require(parser._old_relocations(candidate, final) == (table, locations),
             "scalar relocation directory differs")
    _require(all(_address(final, patch.offset, len(patch.new)) for patch in patches), "scalar mapping differs")
    return dict(section_count=7, menu_hook_count=0, new_state_bytes=0,
                scalar_patch_count=len(patches), geometry=geometry,
                original_sections_unchanged=True, relocation_directory_unchanged=True,
                highlow_count=len(locations), inherited_operand_completeness_proven=False,
                only_frozen_predecessor_bytes=True)


def _wide_contract(original: bytes, base: bytes, patches: Any, resolution: str, menu: Any, parser: Any):
    """Independently re-emit the frozen menu extension from native records."""
    layout = _geometry(resolution)
    _require(_selected(resolution)[0] == MENU_REVISION, "wide predecessor required")
    _audit_scalar(original, base, patches, resolution, parser)
    profile = menu.scalar.parse_resolution(resolution)
    records, tables = menu._native_records(original, base, profile)
    before = parser.inspect_pe(base)
    bundle = menu.emit_guards(base_va=before.image_base + before.image_size,
                              width=layout["width"], height=layout["height"], records=records)
    hooks, windows = [], []
    for index, (name, address, size, within) in enumerate(menu.SITES):
        offset = before.file_offset(address - before.image_base, size)
        native = original[offset:offset + size]
        _require(base[offset:offset + size] == native, "menu dispatcher window differs")
        old = native[within:within + 6]
        _require(old == menu.PREFIXES[index] + struct.pack("<I", 640), "native menu CMP differs")
        va, target = address + within, bundle.entries[name]
        hooks.append(parser.HookPatch(offset + within, va - before.image_base, va, old,
            b"\xe8" + struct.pack("<i", target - va - 5) + b"\x90", "classic_menu." + name,
            (parser.CodeRelocation(1, "rel32", target, "menu-only descriptor bound"),)))
        windows.append(dict(va=address, bytes=size, predecessor_sha256=sha256(native)))
    result = parser._extend_verified_image(base, code=bundle.code, code_va=bundle.base_va,
        relocations=bundle.relocations, hooks=tuple(hooks), binding=dict(stage=MENU_STAGE,
        recipe_revision=MENU_REVISION, base_stage=STABLE_STAGE, resolution=resolution,
        original_sha256=BASE_SHA256, base_candidate_sha256=sha256(base)))
    spans = [(before.image_base, result.image[:before.headers_size])]
    spans += [(_address(before, patch.offset, len(patch.new))[1],
               result.image[patch.offset:patch.offset + len(patch.new)]) for patch in patches]
    for row in tables + windows:
        offset = before.file_offset(row["va"] - before.image_base, row["bytes"])
        spans.append((row["va"], result.image[offset:offset + row["bytes"]]))
    spans.append((bundle.base_va, result.image[result.metadata["append_offset"]:]))
    expected = dict(result.metadata, schema="clash95_classic_menu_candidate_v1",
        candidate_sha256=sha256(result.image), source_hashes=dict(menu.PINNED) | {
            menu.SOURCE: sha256((ROOT / menu.SOURCE).read_bytes())},
        menu_records=[dict(x=x, y=y, callback=callback) for x, y, callback in records],
        menu_tables=tables, dispatcher_windows=windows, entry_vas=bundle.entries,
        patch_records=[dict(group=patch.group, offset=patch.offset, old_hex=patch.old.hex(),
                            new_hex=patch.new.hex()) for patch in patches],
        policy="Only exact original menu/campaign/multiplayer/options/load x/y/callback records "
               "with the native menu holder use the physical bound; every other descriptor retains signed x<640.",
        runtime_executed=False, gameplay_verified=False, manual_input_proof=False, promotion_ready=False)
    probe = menu.loaded_probe(result.image, expected, spans)
    expected["probe_sha256"] = sha256(probe.encode())
    return result.image, expected, probe, spans


def _audit_wide(original: bytes, base: bytes, candidate: bytes, metadata: dict, inherited: str,
                patches: Any, resolution: str, menu: Any, parser: Any) -> tuple[dict, list]:
    _require(type(candidate) is bytes and type(metadata) is dict and type(inherited) is str,
             "immutable wide candidate and exact metadata/probe required")
    expected, contract, probe, spans = _wide_contract(original, base, patches, resolution, menu, parser)
    _require(candidate == expected, "wide byte/header/code/relocation reconstruction differs")
    _same(metadata, contract, "wide metadata, hooks, operands or predecessor identity differ")
    _require(inherited == probe, "canonical frozen menu probe differs")
    before, final = parser.inspect_pe(base), parser.inspect_pe(candidate)
    section = final.sections[-1]
    _require(len(final.sections) == 8 and final.sections[:7] == before.sections
             and section.name.rstrip(b"\0") == b".hdcode" and section.characteristics == parser.RX_CODE
             and section.header_offset == 0x280 and section.rva == before.image_size
             and section.raw_offset == len(base) and section.raw_offset + section.raw_size == len(candidate),
             "wide extension ownership differs")
    old_table, old_locations = parser._old_relocations(base, before)
    table, locations = parser._old_relocations(candidate, final)
    declared = [row for row in metadata["relocations"] if row["kind"] == "abs32"]
    _require(set(locations) == set(old_locations) | {section.rva + row["offset"] for row in declared}
             and len(locations) == len(old_locations) + len(declared) and table.startswith(old_table),
             "complete menu HIGHLOW inventory differs")
    return dict(section_count=8, menu_hook_count=2, new_state_bytes=0,
                scalar_patch_count=len(patches), geometry=_geometry(resolution),
                original_sections_unchanged=True, declared_menu_operand_count=len(metadata["relocations"]),
                highlow_count=len(locations), menu_operand_reemission_verified=True,
                inherited_operand_completeness_proven=False, only_frozen_predecessor_bytes=True), spans


def byte_records(original: bytes, candidate: bytes, view: Any) -> list[dict]:
    _require(type(original) is type(candidate) is bytes and len(candidate) >= len(original),
             "immutable nontruncated byte images required")
    records, position = [], 0
    while position < len(candidate):
        if position < len(original) and original[position] == candidate[position]:
            position += 1
            continue
        start = position
        limit = min(start + 64, len(original) if start < len(original) else len(candidate))
        while position < limit and (position >= len(original) or original[position] != candidate[position]):
            position += 1
        rva, va = _address(view, start, position - start)
        records.append(dict(offset=start, file_offset=start, rva=rva, va=va,
            old_hex=original[start:position].hex(), new_hex=candidate[start:position].hex(),
            stage=STAGE, group="classic-all-presets-frozen-predecessor",
            rationale="Exact original-to-selected frozen Classic predecessor reconstruction",
            appended=start >= len(original)))
    return records


def apply_records(original: bytes, records: list, *, expected_base_sha256: str, view: Any) -> bytes:
    _require(type(original) is bytes and sha256(original) == expected_base_sha256 and type(records) is list,
             "byte replay base identity or record type differs")
    output, last_end = bytearray(original), 0
    for row in records:
        _require(type(row) is dict and set(row) == {"offset", "file_offset", "rva", "va", "old_hex", "new_hex",
                 "stage", "group", "rationale", "appended"}, "byte record schema differs")
        offset = row["file_offset"]
        old, new = _hex(row["old_hex"]), _hex(row["new_hex"])
        _require(type(offset) is type(row["offset"]) is int and offset == row["offset"] and offset >= last_end
                 and bool(new) and row["stage"] == STAGE and row["group"] == "classic-all-presets-frozen-predecessor"
                 and type(row["rationale"]) is str and bool(row["rationale"].strip())
                 and type(row["appended"]) is bool and row["appended"] == (offset >= len(original)),
                 "byte record extent, stage or type differs")
        rva, va = _address(view, offset, len(new))
        _require(type(row["rva"]) is type(row["va"]) is int and (row["rva"], row["va"]) == (rva, va),
                 "byte record address differs")
        if old:
            _require(len(old) == len(new) and offset + len(old) <= len(original)
                     and output[offset:offset + len(old)] == old, "byte record old bytes differ")
            output[offset:offset + len(new)] = new
        else:
            _require(row["appended"] and offset == len(output), "appended byte records must be contiguous")
            output.extend(new)
        last_end = offset + len(new)
    return bytes(output)


def _probe(candidate: bytes, resolution: str, producer_digest: str, spans: list, parser: Any,
           inherited: str | None = None) -> tuple[str, dict]:
    revision, predecessor_stage = _selected(resolution)
    _require(type(candidate) is bytes and type(producer_digest) is str
             and re.fullmatch("[0-9a-f]{64}", producer_digest) is not None
             and type(spans) is list and bool(spans), "canonical probe inputs required")
    view, values = parser.inspect_pe(candidate), {}
    for va, data in spans:
        _require(type(va) is int and type(data) is bytes and bool(data), "invalid probe span")
        rva = va - view.image_base
        if 0 <= rva and rva + len(data) <= view.headers_size:
            offset = rva
        else:
            offset = view.file_offset(rva, len(data))
        _require(candidate[offset:offset + len(data)] == data, "probe bytes differ from final candidate")
        for index, value in enumerate(data):
            address = va + index
            _require(address not in values or values[address] == value, "conflicting probe spans")
            values[address] = value
    if revision == MENU_REVISION:
        _require(type(inherited) is str, "wide frozen probe is required")
        reads = re.findall(r"by\(([0-9a-f]{8})\) != ([0-9a-f]+)", inherited)
        _require(bool(reads) and all(values.get(int(address, 16)) == int(value, 16) for address, value in reads),
                 "inherited menu predicate missing or changed")
    else:
        _require(inherited is None, "narrow Classic has no menu predecessor probe")
    conditions = [f"(by({address:08x}) != {value:x})" for address, value in sorted(values.items())]
    lines = [".echo === Classic all-presets source-bound loaded-byte diagnostic ==="]
    for start in range(0, len(conditions), 90):
        lines.append(".if (" + " | ".join(conditions[start:start + 90])
                     + ") { .echo CLASSICALLPRESETS_CONTRACT_FAIL; q }")
    marker = (f"CLASSICALLPRESETS_CONTRACT_PASS stage={STAGE} resolution={resolution} "
              f"candidate_sha256={sha256(candidate)} revision={REVISION} producer_sha256={producer_digest} "
              f"predecessor_revision={revision} predecessor_stage={predecessor_stage}")
    lines += [".echo " + marker,
              ".echo CLASSICALLPRESETS_SCOPE preferred_address_loaded_bytes_only runtime_verified=false "
              "expanded_battle=false manual_input_proof=false promotion_ready=false"]
    _require(all(len(line.encode("ascii")) < 4096 for line in lines), "probe line exceeds CDB limit")
    probe = "\n".join(lines) + "\n"
    return probe, dict(marker=marker, loaded_predicate_count=len(values),
        inherited_probe_sha256=None if inherited is None else sha256(inherited.encode()),
        all_inherited_menu_predicates_required=revision == MENU_REVISION,
        preferred_address_only=True, runtime_observation_protocol=False,
        scope="Static initial loaded-byte checks; no loader rebase, startup, input, screen, lifecycle or endurance proof")


def build_candidate(original: bytes, resolution: str) -> tuple[bytes, dict, str]:
    _require(type(original) is bytes and sha256(original) == BASE_SHA256,
             "unknown original executable SHA-256; no identity override exists")
    geometry = _geometry(resolution)
    snapshots = _sources()
    producer_path = Path(__file__).resolve()
    _require(producer_path == ROOT / SOURCE, "noncanonical constructor path")
    producer = producer_path.read_bytes()
    producer_digest = sha256(producer)
    revision, predecessor_stage = _selected(resolution)
    with _producer(snapshots) as (scalar, menu, parser):
        patches = tuple(scalar.select_patches_for(STABLE_STAGE, scalar.parse_resolution(resolution)))
        base = _scalar_replay(original, patches)
        inherited = None
        if revision == MENU_REVISION:
            candidate, predecessor, inherited = menu.build_candidate(original, resolution)
            audit, spans = _audit_wide(original, base, candidate, predecessor, inherited,
                                       patches, resolution, menu, parser)
        else:
            candidate = base
            audit = _audit_scalar(original, candidate, patches, resolution, parser)
            predecessor = dict(stage=STABLE_STAGE, recipe_revision=SCALAR_REVISION, resolution=resolution,
                original_sha256=BASE_SHA256, candidate_sha256=sha256(candidate), scalar_patch_count=len(patches))
            view = parser.inspect_pe(candidate)
            spans = [(view.image_base, candidate[:view.headers_size])]
            spans += [(_address(view, patch.offset, len(patch.new))[1], patch.new) for patch in patches]
        view = parser.inspect_pe(candidate)
        raw = view.file_offset(view.relocation_rva, view.relocation_size)
        spans.append((view.image_base + view.relocation_rva, candidate[raw:raw + view.relocation_size]))
        records = byte_records(original, candidate, view)
        _require(apply_records(original, records, expected_base_sha256=BASE_SHA256, view=view) == candidate,
                 "full original-to-final byte replay differs")
        probe, probe_contract = _probe(candidate, resolution, producer_digest, spans, parser, inherited)
    _require(_sources() == snapshots and producer_path.read_bytes() == producer,
             "producer source changed during reconstruction")
    sources = {name: sha256(data) for name, data in snapshots.items()} | {SOURCE: producer_digest}
    metadata = dict(schema="clash95_classic_all_presets_candidate_v1", profile="classic", stage=STAGE,
        recipe_revision=REVISION, resolution=resolution, base_sha256=BASE_SHA256,
        candidate_sha256=sha256(candidate), candidate_bytes=len(candidate), source_hashes=sources,
        predecessor_recipe=revision, predecessor_stage=predecessor_stage, predecessor=predecessor,
        geometry=geometry, structural_gate=audit, patch_records=records,
        probe_sha256=sha256(probe.encode()), probe_contract=probe_contract,
        validation_stage_only=True, **{name: False for name in FALSE_CLAIMS},
        limitations=["Candidate bytes exactly preserve the selected frozen Classic recipe; this stage adds no patches.",
                     "Classic full-tile and partial-strip behavior is retained, including unfinished frame/footer and composition proof.",
                     "Small-world safety, source-declared inherited operand completeness and loader rebasing are unproven.",
                     "The canonical probe checks preferred-address initial loaded bytes, not runtime behavior or acceptance.",
                     "Expanded battle, visible/manual input, continuity, endurance and promotion remain independent missing evidence."])
    return candidate, metadata, probe
