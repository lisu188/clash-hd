"""Offline, additive PE32 allocation for Clash95 validation code.

No binary is read or written by the builder. The public entry checks the known
original, exact candidate identity, and reconstructs the combined recipe from
caller-pinned patcher source. Only that source file is read. The result contains
bytes and exact edits, never a runnable installation claim. A separate entry
supports explicitly supplied hook spans and their displaced relocation fields.

Format reference: https://learn.microsoft.com/en-us/windows/win32/debug/pe-format
HIGHLOW entries describe explicit 4-byte absolute fields, including unaligned
fields. This module validates declared relocations; it cannot discover omitted
ones or establish that the supplied code is semantically safe.

Preserving old relocation entries does not establish their correctness for
preexisting changed patch bytes or future hook spans. An overwritten absolute
operand may require removal or retargeting of its old relocation. The hook-aware
entry requires explicit removals for exactly the fully displaced old fields;
it does not infer new operand locations or an installation recipe. The new eighth
section also fails the canonical v6 continuity probe's exact seven-section
contract as designed; integration needs a separately bound stage/probe contract.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
import re
import struct
import sys
import types
from typing import Sequence


ORIGINAL_SHA256 = "500055d77d03d514e8d3168506bd10f67cd8569bcc450604ff8192f46cdaf3ae"
PATCHER = Path(__file__).with_name("patch_clash95_hd.py")
U32_LIMIT = 1 << 32
RX_CODE = 0x60000020
SCRATCH_START = 0x300


class PEExtensionError(ValueError):
    """The image or explicit allocation contract cannot be safely accepted."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise PEExtensionError(message)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _identity(data: bytes, expected: str, label: str) -> None:
    _require(isinstance(data, bytes), f"{label} must be immutable bytes")
    _require(isinstance(expected, str) and re.fullmatch(r"[0-9a-fA-F]{64}", expected) is not None,
             f"{label} SHA-256 missing or malformed")
    _require(_sha(data) == expected.lower(), f"{label} SHA-256 mismatch")


def _u32(value: int, label: str) -> int:
    _require(type(value) is int and 0 <= value < U32_LIMIT, f"{label} overflows PE32")
    return value


def _align(value: int, alignment: int) -> int:
    return _u32((value + alignment - 1) // alignment * alignment, "aligned size")


def _unpack(fmt: str, data: bytes, offset: int):
    _require(0 <= offset <= len(data) - struct.calcsize(fmt), "truncated PE field")
    return struct.unpack_from(fmt, data, offset)


@dataclass(frozen=True)
class Section:
    name: bytes
    header_offset: int
    virtual_size: int
    rva: int
    raw_size: int
    raw_offset: int
    characteristics: int

    @property
    def memory_size(self) -> int:
        # The known Watcom image uses zero VirtualSize for every section and
        # nonzero SizeOfRawData with PointerToRawData=0 for its .bss extent.
        return max(self.virtual_size, self.raw_size)


@dataclass(frozen=True)
class PEImage:
    pe_offset: int
    optional_offset: int
    image_base: int
    section_alignment: int
    file_alignment: int
    image_size: int
    headers_size: int
    size_of_code: int
    sections: tuple[Section, ...]
    relocation_rva: int
    relocation_size: int

    def file_offset(self, rva: int, size: int) -> int:
        _require(type(rva) is int and type(size) is int and rva >= 0 and size > 0,
                 "invalid mapped range")
        matches = [s.raw_offset + rva - s.rva for s in self.sections
                   if s.raw_offset != 0 and s.rva <= rva and rva + size <= s.rva + s.raw_size]
        _require(len(matches) == 1, "unmapped or ambiguous file-backed RVA")
        return matches[0]

    def contains_memory(self, rva: int, size: int = 1) -> bool:
        return sum(s.rva <= rva and rva + size <= s.rva + s.memory_size for s in self.sections) == 1


def inspect_pe(data: bytes) -> PEImage:
    """Strict PE32 layout parsing, including this image's unbacked .bss."""
    _require(isinstance(data, bytes) and data[:2] == b"MZ", "invalid DOS signature")
    pe, = _unpack("<I", data, 0x3C)
    _require(pe >= 0x40 and pe % 8 == 0 and data[pe:pe + 4] == b"PE\0\0", "invalid PE signature/alignment")
    machine, count, _, symbols, symbol_count, optional_size, flags = _unpack("<HHIIIHH", data, pe + 4)
    _require(machine == 0x14C and 1 <= count < 96 and optional_size == 224,
             "unsupported machine/section count/optional header")
    _require(symbols == symbol_count == 0 and flags & 2 and not flags & (1 | 0x2000),
             "unsupported symbols, DLL, or stripped relocations")
    opt = pe + 24
    magic, = _unpack("<H", data, opt)
    _require(magic == 0x10B, "expected PE32 optional header")
    code_size, = _unpack("<I", data, opt + 4)
    base, section_align, file_align = _unpack("<III", data, opt + 28)
    image_size, headers_size, checksum = _unpack("<III", data, opt + 56)
    directories, = _unpack("<I", data, opt + 92)
    _require(directories == 16 and checksum == 0, "unsupported directory count or nonzero checksum")
    _require(base > 0 and base % 0x10000 == 0, "invalid image base")
    _require(512 <= file_align <= 65536 and file_align & (file_align - 1) == 0,
             "invalid file alignment")
    _require(section_align >= max(4096, file_align) and section_align & (section_align - 1) == 0,
             "unsupported section alignment")
    _require(headers_size > 0 and headers_size % file_align == 0 and headers_size <= len(data),
             "invalid SizeOfHeaders")
    table = opt + optional_size
    _require(table + count * 40 <= headers_size, "section table exceeds headers")
    _require(image_size > 0 and image_size % section_align == 0 and base + image_size <= U32_LIMIT,
             "invalid or overflowing SizeOfImage")
    sections = []
    last_memory_end = _align(headers_size, section_align)
    raw_ranges = []
    for index in range(count):
        pos = table + index * 40
        name, virtual, rva, raw_size, raw, rel, lines, rel_count, line_count, characteristics = _unpack("<8sIIIIIIHHI", data, pos)
        _require(not any((rel, lines, rel_count, line_count)), "unsupported section COFF relocations/line numbers")
        _require(rva % section_align == 0 and rva >= last_memory_end, "overlapping/misaligned section RVA")
        extent = max(virtual, raw_size)
        _require(extent > 0 and rva + extent < U32_LIMIT, "empty or overflowing section")
        last_memory_end = _align(rva + extent, section_align)
        _require(raw_size % file_align == 0, "misaligned raw section size")
        if raw == 0:
            _require(characteristics & 0x80 and not characteristics & 0x60,
                     "non-BSS section lacks raw storage")
        else:
            _require(raw_size > 0 and raw % file_align == 0 and raw >= headers_size
                     and raw + raw_size <= len(data), "invalid raw section range")
            raw_ranges.append((raw, raw + raw_size))
        sections.append(Section(name, pos, virtual, rva, raw_size, raw, characteristics))
    _require(last_memory_end == image_size, "SizeOfImage does not match section extents")
    ordered_raw = sorted(raw_ranges)
    _require(ordered_raw and all(a[1] <= b[0] for a, b in zip(ordered_raw, ordered_raw[1:])),
             "overlapping file-backed sections")
    _require(ordered_raw[-1][1] == len(data) and len(data) % file_align == 0,
             "overlay or unaligned file end is unsupported")
    _require(code_size == sum(s.raw_size for s in sections if s.characteristics & 0x20),
             "SizeOfCode does not match code sections")
    directory = [_unpack("<II", data, opt + 96 + i * 8) for i in range(16)]
    _require(directory[4] == (0, 0), "signed images/certificate overlays are unsupported")
    reloc_rva, reloc_size = directory[5]
    _require(reloc_rva > 0 and reloc_size >= 8, "base relocation directory is required")
    result = PEImage(pe, opt, base, section_align, file_align, image_size, headers_size,
                     code_size, tuple(sections), reloc_rva, reloc_size)
    for rva, size in directory:
        _require(bool(rva) == bool(size), "partial data-directory entry")
        if rva:
            result.file_offset(rva, size)
    return result


def _old_relocations(data: bytes, pe: PEImage) -> tuple[bytes, tuple[int, ...]]:
    offset = pe.file_offset(pe.relocation_rva, pe.relocation_size)
    raw = data[offset:offset + pe.relocation_size]
    position, previous_page = 0, -1
    locations = []
    while position < len(raw):
        page, size = _unpack("<II", raw, position)
        _require(page % 4096 == 0 and page > previous_page and page < pe.image_size,
                 "duplicate, unordered, or invalid relocation page")
        _require(size >= 8 and size % 4 == 0 and position + size <= len(raw),
                 "malformed relocation block size")
        for word, in struct.iter_unpack("<H", raw[position + 8:position + size]):
            kind, delta = word >> 12, word & 4095
            _require(kind in (0, 3), "unsupported base relocation type")
            if kind == 3:
                location = page + delta
                pe.file_offset(location, 4)
                locations.append(location)
        previous_page, position = page, position + size
    ordered = sorted(locations)
    _require(all(a + 4 <= b for a, b in zip(ordered, ordered[1:])),
             "duplicate or overlapping base relocations")
    return raw, tuple(locations)


@dataclass(frozen=True)
class CodeRelocation:
    offset: int
    kind: str
    target: int
    purpose: str


@dataclass(frozen=True)
class HookPatch:
    offset: int
    rva: int
    va: int
    old: bytes
    new: bytes
    purpose: str
    relocations: tuple[CodeRelocation, ...] = ()


@dataclass(frozen=True)
class ByteEdit:
    offset: int
    rva: int
    va: int
    old: bytes
    new: bytes
    purpose: str

    def metadata(self) -> dict:
        return {"offset": self.offset, "rva": self.rva, "va": self.va,
                "old_hex": self.old.hex(), "new_hex": self.new.hex(), "purpose": self.purpose}


@dataclass(frozen=True)
class ExtensionResult:
    image: bytes
    edits: tuple[ByteEdit, ...]
    metadata: dict
    installation_ready: bool = False


def extension_code_va(original: bytes) -> int:
    """Preferred VA to give the emitter; no candidate or payload is created."""
    _identity(original, ORIGINAL_SHA256, "original")
    pe = inspect_pe(original)
    return _u32(pe.image_base + pe.image_size, "extension code VA")


def _prepare_hooks(candidate: bytes, pe: PEImage, hooks: Sequence[HookPatch],
                   removed_highlow_rvas: Sequence[int], old_locations: tuple[int, ...],
                   code_va: int, code_size: int) -> tuple[list[ByteEdit], list[int], list[dict], list[dict]]:
    """Validate whole displaced fields before changing a single byte."""
    edits, added, normalized = [], [], []
    for hook in hooks:
        _require(isinstance(hook, HookPatch), "hook must be an explicit HookPatch record")
        _require(isinstance(hook.old, bytes) and isinstance(hook.new, bytes)
                 and len(hook.old) == len(hook.new) > 0 and hook.old != hook.new,
                 "hook old/new bytes must be nonempty, distinct, and equal length")
        _require(all(type(value) is int and 0 <= value < U32_LIMIT for value in (hook.offset, hook.rva, hook.va))
                 and hook.va == pe.image_base + hook.rva, "hook VA/RVA/file-offset identity mismatch")
        _require(pe.file_offset(hook.rva, len(hook.old)) == hook.offset, "hook file-offset mapping mismatch")
        _require(any(s.characteristics & 0x20000000 and s.rva <= hook.rva
                     and hook.rva + len(hook.old) <= s.rva + s.raw_size for s in pe.sections),
                 "hook span is not executable file-backed code")
        _require(candidate[hook.offset:hook.offset + len(hook.old)] == hook.old, "hook old bytes mismatch")
        _require(isinstance(hook.purpose, str) and hook.purpose.strip(), "hook purpose missing")
        fields = []
        for relocation in hook.relocations:
            _require(all(hasattr(relocation, key) for key in ("offset", "kind", "target", "purpose")),
                     "malformed hook relocation")
            off, kind, target, purpose = relocation.offset, relocation.kind, relocation.target, relocation.purpose
            _require(type(off) is int and 0 <= off <= len(hook.new) - 4, "hook relocation outside replacement bytes")
            _u32(target, "hook relocation target")
            _require(kind in ("abs32", "rel32") and isinstance(purpose, str) and purpose.strip(),
                     "unsupported hook relocation kind or missing purpose")
            _require(pe.contains_memory(target - pe.image_base) or code_va <= target < code_va + code_size,
                     "hook relocation target is unmapped")
            actual, = struct.unpack_from("<I", hook.new, off)
            expected = target if kind == "abs32" else (target - (hook.va + off + 4)) & 0xFFFFFFFF
            _require(actual == expected, "hook relocation target/value mismatch")
            fields.append(off)
            normalized.append({"hook_va": hook.va, "offset": off, "rva": hook.rva + off,
                               "kind": kind, "target": target, "purpose": purpose})
            if kind == "abs32":
                added.append(hook.rva + off)
        fields.sort()
        _require(all(a + 4 <= b for a, b in zip(fields, fields[1:])), "duplicate or overlapping hook relocation fields")
        edits.append(ByteEdit(hook.offset, hook.rva, hook.va, hook.old, hook.new, hook.purpose))
    ordered_hooks = sorted(edits, key=lambda edit: edit.rva)
    _require(all(a.rva + len(a.old) <= b.rva for a, b in zip(ordered_hooks, ordered_hooks[1:])),
             "overlapping hook spans")
    displaced = set()
    for location in old_locations:
        for hook in ordered_hooks:
            if location < hook.rva + len(hook.old) and hook.rva < location + 4:
                _require(hook.rva <= location and location + 4 <= hook.rva + len(hook.old),
                         "hook partially overlaps an old HIGHLOW field")
                displaced.add(location)
    _require(all(type(rva) is int and 0 <= rva < U32_LIMIT for rva in removed_highlow_rvas),
             "invalid removed HIGHLOW RVA")
    removals = set(removed_highlow_rvas)
    _require(len(removals) == len(removed_highlow_rvas), "duplicate HIGHLOW removal")
    _require(removals == displaced, "HIGHLOW removals must exactly match fully displaced fields")
    removed_rows = []
    for rva in sorted(removals):
        offset = pe.file_offset(rva, 4)
        removed_rows.append({"rva": rva, "va": pe.image_base + rva, "offset": offset,
                             "old_hex": candidate[offset:offset + 4].hex()})
    return edits, added, normalized, removed_rows


def _relocation_blocks(locations: Sequence[int]) -> bytes:
    ordered = sorted(locations)
    _require(all(a + 4 <= b for a, b in zip(ordered, ordered[1:])), "duplicate or overlapping merged HIGHLOW fields")
    pages: dict[int, list[int]] = {}
    for rva in ordered:
        pages.setdefault(rva & ~4095, []).append(0x3000 | (rva & 4095))
    result = bytearray()
    for page, words in sorted(pages.items()):
        if len(words) % 2:
            words.append(0)
        result.extend(struct.pack("<II", page, 8 + len(words) * 2))
        result.extend(struct.pack("<" + "H" * len(words), *words))
    return bytes(result)


def _extend_verified_image(candidate: bytes, *, code: bytes, code_va: int,
                           relocations: Sequence[CodeRelocation], binding: dict,
                           hooks: Sequence[HookPatch] = (),
                           removed_highlow_rvas: Sequence[int] = ()) -> ExtensionResult:
    """Private format operation; production callers must use the bound entry."""
    pe = inspect_pe(candidate)
    slot = pe.sections[-1].header_offset + 40
    _require(slot + 40 <= min(pe.headers_size, SCRATCH_START), "new header would overlap reserved scratch")
    _require(candidate[slot:slot + 40] == bytes(40), "new section-header slot is not zero")
    _require(all(s.name.rstrip(b"\0") != b".hdcode" for s in pe.sections), "extension section already exists")
    _require(isinstance(code, bytes) and len(code) > 0, "code must be nonempty immutable bytes")
    expected_va = _u32(pe.image_base + pe.image_size, "extension VA")
    _require(type(code_va) is int and code_va == expected_va, "emitter code VA differs from allocated VA")
    _u32(code_va + len(code), "code address extent")
    old_table, old_locations = _old_relocations(candidate, pe)
    normalized = []
    absolute_rvas = []
    for relocation in relocations:
        _require(all(hasattr(relocation, k) for k in ("offset", "kind", "target", "purpose")), "malformed code relocation")
        off, kind, target, purpose = relocation.offset, relocation.kind, relocation.target, relocation.purpose
        _require(type(off) is int and 0 <= off <= len(code) - 4, "code relocation offset outside payload")
        _u32(target, "relocation target")
        _require(isinstance(purpose, str) and purpose.strip(), "relocation purpose missing")
        _require(kind in ("abs32", "rel32"), "unsupported code relocation kind")
        _require(pe.contains_memory(target - pe.image_base) or code_va <= target < code_va + len(code),
                 "code relocation target is unmapped")
        value, = struct.unpack_from("<I", code, off)
        expected = target if kind == "abs32" else (target - (code_va + off + 4)) & 0xFFFFFFFF
        _require(value == expected, "code relocation target/value mismatch")
        normalized.append({"offset": off, "kind": kind, "target": target, "purpose": purpose})
        if kind == "abs32":
            absolute_rvas.append(pe.image_size + off)
    ordered_fields = sorted(row["offset"] for row in normalized)
    _require(all(a + 4 <= b for a, b in zip(ordered_fields, ordered_fields[1:])),
             "duplicate or overlapping code relocations")
    hook_edits, hook_absolute_rvas, hook_fields, removed_rows = _prepare_hooks(
        candidate, pe, hooks, removed_highlow_rvas, old_locations, code_va, len(code))
    removed_set = set(removed_highlow_rvas)
    retained = tuple(rva for rva in old_locations if rva not in removed_set)
    expected_locations = retained + tuple(hook_absolute_rvas) + tuple(absolute_rvas)
    merged = bool(removed_highlow_rvas or hook_absolute_rvas)
    table_offset = _align(len(code), 4)
    # The no-hook path keeps its old table byte-for-byte, including padding.
    # Hook removals/new fields require one merged block per page. Only the copy
    # in .hdcode changes; the original raw .reloc section remains untouched.
    table = _relocation_blocks(expected_locations) if merged else old_table + _relocation_blocks(absolute_rvas)
    _require(len(table) >= 8, "extension would remove the entire relocation directory")
    payload = code + bytes(table_offset - len(code)) + table
    raw_size = _align(len(payload), pe.file_alignment)
    new_image_size = _align(pe.image_size + len(payload), pe.section_alignment)
    _u32(pe.image_base + new_image_size, "extended image address extent")
    _u32(len(candidate) + raw_size, "extended file size")
    header = struct.pack("<8sIIIIIIHHI", b".hdcode\0", len(payload), pe.image_size,
                         raw_size, len(candidate), 0, 0, 0, 0, RX_CODE)
    edits = list(hook_edits)

    def change(offset: int, new: bytes, purpose: str, rva: int | None = None, append: bool = False):
        old = b"" if append else candidate[offset:offset + len(new)]
        _require(append and offset == len(candidate) or not append and len(old) == len(new), "invalid edit range")
        address = offset if rva is None else rva
        edits.append(ByteEdit(offset, address, pe.image_base + address, old, new, purpose))

    change(pe.pe_offset + 6, struct.pack("<H", len(pe.sections) + 1), "NumberOfSections")
    change(pe.optional_offset + 4, struct.pack("<I", _u32(pe.size_of_code + raw_size, "SizeOfCode")), "SizeOfCode")
    change(pe.optional_offset + 56, struct.pack("<I", new_image_size), "SizeOfImage")
    change(pe.optional_offset + 96 + 5 * 8,
           struct.pack("<II", pe.image_size + table_offset, len(table)), "base relocation directory")
    change(slot, header, ".hdcode section header")
    change(len(candidate), payload + bytes(raw_size - len(payload)), "append RX code and complete relocation table",
           pe.image_size, append=True)
    result = bytearray(candidate)
    for edit in edits:
        _require(bytes(result[edit.offset:edit.offset + len(edit.old)]) == edit.old, "old-byte edit check failed")
        result[edit.offset:edit.offset + len(edit.old)] = edit.new
    result_bytes = bytes(result)
    extended = inspect_pe(result_bytes)
    preserved_table, combined_locations = _old_relocations(result_bytes, extended)
    _require(sorted(combined_locations) == sorted(expected_locations)
             and (merged or preserved_table[:len(old_table)] == old_table),
             "combined relocation table did not preserve all unrelated entries")
    metadata = {
        "schema": "clash95_pe_extension_v1", **binding, "input_sha256": _sha(candidate),
        "output_sha256": _sha(result_bytes), "code_sha256": _sha(code),
        "code_va": code_va, "code_rva": pe.image_size, "code_bytes": len(code),
        "section": ".hdcode", "characteristics": RX_CODE,
        "append_offset": len(candidate), "append_bytes": raw_size,
        "old_relocation_sha256": _sha(old_table), "old_highlow_count": len(old_locations),
        "new_highlow_count": len(absolute_rvas) + len(hook_absolute_rvas), "relocations": normalized,
        "edits": [edit.metadata() for edit in edits], "installation_ready": False,
        "limits": (
            "Allocation and declared relocation integrity only. Preserving old relocation entries does not "
            "prove their correctness for preexisting changed patch bytes or future hook spans; overwritten "
            "absolute operands may require separately verified removal/retargeting. The eighth section "
            "intentionally fails the canonical v6 continuity probe's seven-section contract and requires "
            "a separately bound stage/probe contract. No hook installation, relocation completeness, "
            "runtime, manual-input, or promotion proof."
        ),
    }
    if hooks:
        metadata.update({"hooks": [edit.metadata() for edit in hook_edits], "hook_relocations": hook_fields,
                         "removed_highlow": removed_rows, "retained_highlow_count": len(retained),
                         "relocation_directory_merged": merged})
        metadata["limits"] = (
            "Only the declared equal-length hook spans and relocation fields are validated. No complete "
            "installation recipe, instruction-boundary proof, undeclared operand completeness, runtime, "
            "manual-input, or promotion proof. Relocation correctness of unrelated preexisting patch bytes "
            "remains separate. The eighth section requires a separately bound validation stage/probe contract."
        )
    return ExtensionResult(result_bytes, tuple(edits), metadata)


def _bind_combined_candidate(original: bytes, candidate: bytes, *, expected_candidate_sha256: str,
                             expected_patcher_sha256: str, stage: str, resolution: str) -> dict:
    _identity(original, ORIGINAL_SHA256, "original")
    _identity(candidate, expected_candidate_sha256, "candidate")
    original_pe = inspect_pe(original)
    _require(len(candidate) == len(original) and candidate[:original_pe.headers_size] == original[:original_pe.headers_size],
             "candidate changed original PE headers or length")
    source = PATCHER.read_bytes()
    _identity(source, expected_patcher_sha256, "patcher source")
    module_name = "_clash95_pe_extension_pinned_recipe"
    module = types.ModuleType(module_name)
    module.__file__ = str(PATCHER)
    previous = sys.modules.get(module_name)
    sys.modules[module_name] = module
    try:
        exec(compile(source, str(PATCHER), "exec"), module.__dict__)
        _require(stage == module.DEFAULT_STAGE + "-combinedui-validation", "only the combined validation recipe is supported")
        _require(isinstance(resolution, str), "resolution must be a canonical string")
        profile = module.parse_resolution(resolution)
        _require(profile.key == resolution, "resolution is not canonical")
        patches = module.select_patches_for(stage, profile)
        rebuilt = bytearray(original)
        ranges = []
        recipe_rows = []
        for patch in patches:
            off, old, new = patch.offset, patch.old, patch.new
            _require(type(off) is int and len(old) == len(new) > 0 and off >= original_pe.headers_size
                     and off + len(old) <= len(original), "invalid selected patch range")
            _require(original[off:off + len(old)] == old, "selected patch old bytes mismatch")
            ranges.append((off, off + len(old)))
            rebuilt[off:off + len(new)] = new
            recipe_rows.append({"offset": off, "old_hex": old.hex(), "new_hex": new.hex(), "group": patch.group})
        ranges.sort()
        _require(all(a[1] <= b[0] for a, b in zip(ranges, ranges[1:])), "selected recipe contains overlapping patches")
        _require(bytes(rebuilt) == candidate, "candidate differs from the selected stage/resolution recipe")
    finally:
        if previous is None:
            del sys.modules[module_name]
        else:
            sys.modules[module_name] = previous
    return {"original_sha256": ORIGINAL_SHA256, "patcher_sha256": _sha(source), "stage": stage,
            "resolution": resolution, "selected_patches": recipe_rows}


def extend_combined_candidate(original: bytes, candidate: bytes, *, expected_candidate_sha256: str,
                              expected_patcher_sha256: str, stage: str, resolution: str,
                              code: bytes, code_va: int,
                              relocations: Sequence[CodeRelocation]) -> ExtensionResult:
    """Bind a candidate to the pinned combined recipe, then allocate in memory.

    The caller pins both source and candidate identities. The full candidate is
    reconstructed after verifying each selected old byte and nonoverlap;
    arbitrary candidate edits or a mislabeled resolution cannot qualify through
    SHA alone. AdapterBundle.relocations records use the same explicit fields
    as CodeRelocation. rel32 fields are verified and never become HIGHLOW.
    """
    binding = _bind_combined_candidate(original, candidate, expected_candidate_sha256=expected_candidate_sha256,
                                       expected_patcher_sha256=expected_patcher_sha256, stage=stage, resolution=resolution)
    return _extend_verified_image(candidate, code=code, code_va=code_va, relocations=relocations, binding=binding)


def extend_combined_candidate_with_hooks(original: bytes, candidate: bytes, *, expected_candidate_sha256: str,
                                         expected_patcher_sha256: str, stage: str, resolution: str,
                                         validation_stage: str, code: bytes, code_va: int,
                                         relocations: Sequence[CodeRelocation], hooks: Sequence[HookPatch],
                                         removed_highlow_rvas: Sequence[int]) -> ExtensionResult:
    """Pure, explicit hook/relocation operation under a new validation identity.

    This is not an installation recipe: callers supply every exact old/new
    span, new relocation field, and authorized validation-stage name, and are
    responsible for independent instruction-boundary proof. Old HIGHLOW removals must exactly match complete
    fields overlapped by the hooks. Partial overlaps are never accepted, even
    when adjacent hook records together cover an old field.
    """
    _require(isinstance(validation_stage, str) and re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*-validation", validation_stage) is not None
             and validation_stage != stage, "a distinct explicit validation-stage identity is required")
    _require(bool(hooks), "hook-aware operation requires explicit hooks")
    binding = _bind_combined_candidate(original, candidate, expected_candidate_sha256=expected_candidate_sha256,
                                       expected_patcher_sha256=expected_patcher_sha256, stage=stage, resolution=resolution)
    binding.update(base_stage=stage, stage=validation_stage)
    return _extend_verified_image(candidate, code=code, code_va=code_va, relocations=relocations, binding=binding,
                                  hooks=hooks, removed_highlow_rvas=removed_highlow_rvas)


def _bind_framed_candidate(original: bytes, candidate: bytes, *, expected_candidate_sha256: str,
                           expected_patcher_sha256: str, expected_recipe_sha256: str,
                           expected_geometry_sha256: str, resolution: str) -> dict:
    """Reconstruct the separate framed base from pinned source, never SHA alone.

    Compile fresh recipe/geometry/patcher modules, so the bound table is not
    supplied by mutable imported module state. The framed scalar module itself
    authenticates every allowed source slot; PE validation independently checks
    original bytes, nonoverlap, header/length preservation and the complete image.
    """
    _identity(original, ORIGINAL_SHA256, "original")
    _identity(candidate, expected_candidate_sha256, "framed candidate")
    original_pe = inspect_pe(original)
    _require(len(candidate) == len(original) and candidate[:original_pe.headers_size] == original[:original_pe.headers_size],
             "framed candidate changed original PE headers or length")
    paths = (("patcher", PATCHER, expected_patcher_sha256),
             ("geometry", PATCHER.with_name("framed_viewport.py"), expected_geometry_sha256),
             ("recipe", PATCHER.with_name("framed_recipe.py"), expected_recipe_sha256))
    modules, previous = {}, {}
    try:
        package_name = "_clash95_pe_framed_binding"
        package = types.ModuleType(package_name)
        package.__path__ = [str(PATCHER.parent)]
        previous[package_name] = sys.modules.get(package_name)
        sys.modules[package_name] = package
        for label, path, digest in paths:
            source = path.read_bytes()
            _identity(source, digest, f"framed {label} source")
            name = f"{package_name}.{path.stem}"
            module = types.ModuleType(name)
            module.__file__ = str(path)
            module.__package__ = package_name
            previous[name] = sys.modules.get(name)
            sys.modules[name] = module
            exec(compile(source, str(path), "exec"), module.__dict__)
            modules[label] = module
        recipe = modules["recipe"]
        _require(isinstance(resolution, str), "resolution must be a canonical string")
        profile = modules["patcher"].parse_resolution(resolution)
        _require(profile.key == resolution, "resolution is not canonical")
        planned = recipe.canonical_candidate(original, profile.width, profile.height)
        rebuilt, ranges, rows = bytearray(original), [], []
        for patch in planned.patches:
            off, old, new = patch.offset, patch.old, patch.new
            _require(type(off) is int and len(old) == len(new) > 0 and off >= original_pe.headers_size
                     and off + len(old) <= len(original), "invalid framed patch range")
            _require(original[off:off+len(old)] == old, "framed patch old bytes mismatch")
            ranges.append((off, off+len(old)))
            rebuilt[off:off+len(new)] = new
            rows.append({"offset":off,"old_hex":old.hex(),"new_hex":new.hex(),"group":patch.group})
        ranges.sort()
        _require(all(a[1] <= b[0] for a,b in zip(ranges,ranges[1:])), "framed recipe contains overlapping patches")
        _require(bytes(rebuilt) == planned.image == candidate, "candidate differs from the exact framed recipe")
        return {"original_sha256":ORIGINAL_SHA256,"patcher_sha256":expected_patcher_sha256,
                "framed_recipe_sha256":expected_recipe_sha256,"framed_geometry_sha256":expected_geometry_sha256,
                "stage":recipe.FRAME_BASE_STAGE,"source_stage":recipe.SOURCE_STAGE,
                "resolution":resolution,"selected_patches":rows,"framed_recipe":planned.metadata}
    finally:
        for name, saved in previous.items():
            if saved is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = saved


def extend_framed_candidate_with_hooks(original: bytes, candidate: bytes, *, expected_candidate_sha256: str,
                                       expected_patcher_sha256: str, expected_recipe_sha256: str,
                                       expected_geometry_sha256: str, resolution: str,
                                       validation_stage: str, code: bytes, code_va: int,
                                       relocations: Sequence[CodeRelocation], hooks: Sequence[HookPatch],
                                       removed_highlow_rvas: Sequence[int]) -> ExtensionResult:
    """Install explicit hooks only after independently binding the framed base.

    This opt-in path does not extend the legacy combined binder's accepted
    recipes. Scalar base provenance and later executable hook edits remain
    separate metadata, and all existing PE/old-byte/relocation gates apply.
    """
    expected_stage = ("gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-"
                      "presentbounds-minimapright-dynvswitch-combinedui-partialtiles-initialpaint-framed-validation")
    _require(validation_stage == expected_stage, "the reviewed framed-validation stage is required")
    _require(bool(hooks), "framed operation requires explicit hooks")
    binding = _bind_framed_candidate(original,candidate,expected_candidate_sha256=expected_candidate_sha256,
                                     expected_patcher_sha256=expected_patcher_sha256,
                                     expected_recipe_sha256=expected_recipe_sha256,
                                     expected_geometry_sha256=expected_geometry_sha256,resolution=resolution)
    _require(validation_stage != binding["stage"], "the framed base is not an installed validation stage")
    binding.update(base_stage=binding["stage"],stage=validation_stage)
    return _extend_verified_image(candidate,code=code,code_va=code_va,relocations=relocations,binding=binding,
                                  hooks=hooks,removed_highlow_rvas=removed_highlow_rvas)
