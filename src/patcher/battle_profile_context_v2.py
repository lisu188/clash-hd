"""Versioned battle allocation admission and PE file relayout, in memory only.

Canonical all-preset parents are reconstructed independently through the frozen
V1 authority. This successor reserves fresh RX/RW addresses for future complete
re-emission. It installs no sections, code, records, providers or hooks. Modal
header growth moves file storage without changing loaded RVAs; every changed
file-offset field is inventoried. Provider bytes are a reservation, not proven
catalog capacity or a resource lifetime contract.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import struct
import sys
import types
import uuid

ROOT = Path(__file__).resolve().parents[2]
SOURCE = "src/patcher/battle_profile_context_v2.py"
PREDECESSOR = "src/patcher/battle_profile_context.py"
PREDECESSOR_SHA256 = "be3bbca018c415895ba7e79e64862512f330297fb56b4d8321f8f6d378c38500"
BASE_SHA256 = "500055d77d03d514e8d3168506bd10f67cd8569bcc450604ff8192f46cdaf3ae"
PROFILES = ("classic", "framed", "completehd", "modalwidgets")
RESOLUTIONS = ("800x600", "1024x768", "1280x720", "1280x960", "1366x768",
               "1920x1080", "2560x1440", "3440x1440", "3840x2160")
REVISION = "battle_profile_context_v2"
RX_BYTES = 0x40000
RW_BYTES = 0x10000
STATE_PAGE_BYTES = 4096
STATE_BYTES = 128
PROVIDER_SCHEMA = "unpopulated_provider_reservation_v1"
RX_FLAGS, RW_FLAGS = 0x60000020, 0xC0000040
FALSE_CLAIMS = ("battle_installed", "expanded_battle_installed", "installation_ready",
                "runtime_executed", "manual_input_proof", "promotion_ready", "release_accepted",
                "provider_capacity_verified", "provider_lifetime_verified", "atomic_installation_verified")


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _align(value, alignment):
    _require(type(value) is int and 0 <= value < 0x80000000, "bounded integer extent required")
    result = (value + alignment - 1) // alignment * alignment
    _require(result < 0x80000000, "aligned extent overflows")
    return result


def _stamp(row):
    return (row.st_dev, row.st_ino, row.st_size, row.st_mtime_ns,
            getattr(row, "st_file_attributes", 0))


def _read_path(path, root):
    """Reject links/reparse ancestors and mid-read replacement before execution."""
    _require(path.is_absolute() and root.is_absolute() and path.is_relative_to(root)
             and path.resolve(strict=True) == path and root.resolve(strict=True) == root,
             "noncanonical source path")
    for item in (path, *path.parents):
        row = item.lstat()
        _require(not item.is_symlink() and not getattr(row, "st_file_attributes", 0) & 0x400,
                 "source reparse path forbidden")
    before = path.stat()
    data = path.read_bytes()
    after = path.stat()
    _require(_stamp(before) == _stamp(after) and len(data) == after.st_size,
             "source changed during read")
    return data, _stamp(after)


@dataclass(frozen=True)
class FileOffsetEdit:
    offset: int
    old: bytes
    new: bytes
    role: str


@dataclass(frozen=True)
class ProtectedSpan:
    va: int
    size: int
    role: str


@dataclass(frozen=True)
class Allocation:
    name: bytes
    va: int
    rva: int
    raw_offset: int
    size: int
    header_offset: int
    characteristics: int


@dataclass(frozen=True)
class Geometry:
    world_columns: int
    visible_columns: int
    max_scroll_x: int
    arena: tuple[int, int, int, int]
    gutter_before_hud: int


@dataclass(frozen=True)
class BattleAllocationLayout:
    profile: str
    resolution: str
    validation_stage: str
    rx: Allocation
    rw: Allocation
    battle_state_va: int
    battle_state_bytes: int
    protected_state_page_bytes: int
    provider_va: int
    provider_reservation_bytes: int
    provider_schema: str
    headers_before: int
    headers_after: int
    insertion_offset: int
    insertion_bytes: int
    original_section_count: int
    parent_section_count: int
    future_section_count: int
    future_image_size: int
    future_file_size: int
    file_offset_edits: tuple[FileOffsetEdit, ...]
    protected_spans: tuple[ProtectedSpan, ...]
    highlow_rvas: tuple[int, ...]
    geometry: tuple[Geometry, ...]


@dataclass(frozen=True)
class BattleProfileContextV2:
    parent: bytes
    relayout_parent: bytes
    parent_metadata_json: str
    canonical_probe: str
    layout: BattleAllocationLayout
    metadata_json: str

    def metadata(self):
        # A convenient copy, never authority for installation or admission.
        return json.loads(self.metadata_json)


@dataclass(frozen=True)
class _Section:
    name: bytes
    header: int
    virtual_size: int
    rva: int
    raw_size: int
    raw: int
    reloc: int
    lines: int
    reloc_count: int
    line_count: int
    flags: int

    @property
    def extent(self):
        return max(self.virtual_size, self.raw_size)


@dataclass(frozen=True)
class _PE:
    data: bytes
    pe: int
    opt: int
    table: int
    headers: int
    image_size: int
    sections: tuple[_Section, ...]
    directories: tuple[tuple[int, int], ...]
    file_offsets: tuple[tuple[int, int, str], ...]
    highlow: tuple[int, ...]

    def file_offset(self, rva, size):
        _require(type(rva) is type(size) is int and rva >= 0 and size > 0,
                 "invalid RVA range")
        rows = [s.raw + rva - s.rva for s in self.sections
                if s.raw and s.rva <= rva and rva + size <= s.rva + s.raw_size]
        _require(len(rows) == 1, "unmapped or ambiguous RVA extent")
        return rows[0]


def _unpack(fmt, data, offset):
    _require(type(data) is bytes and type(offset) is int
             and 0 <= offset <= len(data) - struct.calcsize(fmt), "truncated PE field")
    return struct.unpack_from(fmt, data, offset)


def _parse(data):
    """Bounded PE32 file-offset schema; auxiliary/unknown resources fail closed.

    COFF symbols without auxiliary records, 10B section relocations, 6B line
    records, WIN_CERTIFICATE chains and selected IMAGE_DEBUG_DIRECTORY payloads
    have explicit ownership. Unknown overlay/gap bytes or offset schemas reject.
    Signature validity is not preserved or claimed by this offline relayout.
    """
    _require(type(data) is bytes and data[:2] == b"MZ", "immutable PE32 required")
    pe, = _unpack("<I", data, 60)
    _require(pe >= 64 and pe % 8 == 0 and data[pe:pe + 4] == b"PE\0\0", "PE signature differs")
    machine, count, _, symbols, symbol_count, optional, flags = _unpack("<HHIIIHH", data, pe + 4)
    _require(machine == 0x14C and 7 <= count < 94 and optional == 224
             and flags & 2 and not flags & (1 | 0x2000), "unsupported PE machine/header")
    opt, table = pe + 24, pe + 248
    magic, = _unpack("<H", data, opt)
    base, section_align, file_align = _unpack("<III", data, opt + 28)
    image_size, headers, checksum = _unpack("<III", data, opt + 56)
    directory_count, = _unpack("<I", data, opt + 92)
    _require((magic, base, section_align, file_align, directory_count, checksum)
             == (0x10B, 0x400000, 4096, 512, 16, 0), "historical PE32 alignment/identity differs")
    _require(headers in (0x400, 0x800) and table + count * 40 <= headers <= len(data)
             and image_size % 4096 == 0 and base + image_size < 0x80000000,
             "PE section/header bounds differ")
    sections, owned, file_offsets = [], [], []
    end_rva = _align(headers, 4096)
    names = set()
    for index in range(count):
        at = table + 40 * index
        name, virtual, rva, size, raw, rel, lines, rel_count, line_count, permission = _unpack("<8sIIIIIIHHI", data, at)
        _require(name.rstrip(b"\0") and name not in names, "duplicate/empty section name")
        names.add(name)
        _require(rva == end_rva and max(virtual, size) > 0 and size % 512 == 0,
                 "section RVA ownership or alignment differs")
        end_rva = _align(rva + max(virtual, size), 4096)
        if raw:
            _require(size > 0 and raw % 512 == 0 and headers <= raw <= len(data) - size,
                     "section raw bounds differ")
            owned.append((raw, raw + size, "section"))
            file_offsets.append((at + 20, raw, "section_raw"))
        else:
            _require(permission & 0x80 and not permission & 0x60 and size > 0,
                     "only historical BSS may lack storage")
        _require(bool(rel) == bool(rel_count) and bool(lines) == bool(line_count)
                 and rel_count != 0xFFFF and not permission & 0x01000000,
                 "section relocation/line schema differs")
        for pointer, number, width, field, role in ((rel, rel_count, 10, at + 24, "section_coff_relocations"),
                                                   (lines, line_count, 6, at + 28, "section_line_numbers")):
            if pointer:
                _require(pointer >= headers and pointer <= len(data) - number * width,
                         "section auxiliary file range differs")
                owned.append((pointer, pointer + number * width, role))
                file_offsets.append((field, pointer, role))
        sections.append(_Section(name, at, virtual, rva, size, raw, rel, lines, rel_count, line_count, permission))
    _require(end_rva == image_size, "SizeOfImage differs")
    code_size, = _unpack("<I", data, opt + 4)
    _require(code_size == sum(s.raw_size for s in sections if s.flags & 0x20), "SizeOfCode differs")
    directories = tuple(_unpack("<II", data, opt + 96 + 8 * i) for i in range(16))
    temporary = _PE(data, pe, opt, table, headers, image_size, tuple(sections), directories, (), ())
    _require(directories[15] == (0, 0), "reserved data directory differs")
    for index, (rva, size) in enumerate(directories):
        _require(bool(rva) == bool(size), "unbalanced data directory")
        if rva and index != 4:
            # Header resident directories can overlap future section entries.
            # Their internal resources are not silently moved or authorized.
            temporary.file_offset(rva, size)
    _require(bool(symbols) == bool(symbol_count) and symbol_count < 0x100000,
             "COFF symbol schema differs")
    if symbols:
        end = symbols + symbol_count * 18
        length, = _unpack("<I", data, end)
        _require(symbols >= headers and 4 <= length <= len(data) - end, "COFF symbol/string extent differs")
        for index in range(symbol_count):
            at = symbols + index * 18
            _require(data[at + 17] == 0, "COFF auxiliary symbols have unsupported file-offset schema")
            zero, string = _unpack("<II", data, at)
            if zero == 0:
                _require(4 <= string < length and b"\0" in data[end + string:end + length],
                         "COFF symbol string offset differs")
        owned.append((symbols, end + length, "coff_symbols"))
        file_offsets.append((pe + 12, symbols, "coff_symbol_table"))
    for s in sections:
        for index in range(s.reloc_count):
            rva, symbol, kind = _unpack("<IIH", data, s.reloc + 10 * index)
            _require(rva < s.extent and symbol < symbol_count and kind in (6, 7, 0x14),
                     "section COFF relocation record differs")
        for index in range(s.line_count):
            address, line = _unpack("<IH", data, s.lines + 6 * index)
            _require((line == 0 and address < symbol_count) or
                     (line > 0 and address < s.extent), "section line record differs")
    security, security_size = directories[4]
    if security:
        _require(security % 8 == 0 and security >= headers and security <= len(data) - security_size,
                 "security file extent differs")
        cursor, end = security, security + security_size
        while cursor < end:
            length, revision, kind = _unpack("<IHH", data, cursor)
            _require(8 <= length <= end - cursor and revision in (0x100, 0x200) and kind == 2,
                     "unknown certificate schema")
            padded = (length + 7) // 8 * 8
            _require(cursor + padded <= end and not any(data[cursor + length:cursor + padded]),
                     "certificate padding differs")
            cursor += padded
        _require(cursor == end, "certificate extent differs")
        owned.append((security, end, "certificate"))
        file_offsets.append((opt + 128, security, "security_directory"))
    debug_rva, debug_size = directories[6]
    if debug_rva:
        _require(debug_size % 28 == 0 and debug_size // 28 <= 4096, "debug directory extent differs")
        at = temporary.file_offset(debug_rva, debug_size)
        for index in range(debug_size // 28):
            row = at + index * 28
            _, _, _, _, kind, size, rva, pointer = _unpack("<IIHHIIII", data, row)
            _require(kind in (2, 4, 12, 16) and bool(pointer) == bool(size), "unknown debug payload schema")
            if pointer:
                _require(pointer >= headers and pointer <= len(data) - size, "debug payload file extent differs")
                if rva:
                    _require(temporary.file_offset(rva, size) == pointer, "debug RVA/file identity differs")
                    # Mapped debug bytes are already owned by the entire section.
                else:
                    owned.append((pointer, pointer + size, "debug_payload"))
                file_offsets.append((row + 24, pointer, "debug_payload"))
    ordered = sorted(owned)
    _require(ordered and all(a[1] <= b[0] for a, b in zip(ordered, ordered[1:])),
             "overlapping file-offset resources")
    cursor = headers
    for start, end, _ in ordered:
        _require(cursor <= start and not any(data[cursor:start]), "unknown overlay or gap bytes")
        cursor = end
    _require(cursor == len(data) or (len(data) % 512 == 0 and not any(data[cursor:])),
             "unknown trailing overlay")
    # Every HIGHLOW must retain its RVA, loaded operand, and relocation bytes.
    reloc_rva, reloc_size = directories[5]
    _require(reloc_rva and reloc_size, "base relocation directory required")
    reloc_at = temporary.file_offset(reloc_rva, reloc_size)
    cursor, fixups, last_page = reloc_at, [], -1
    while cursor < reloc_at + reloc_size:
        page, block_size = _unpack("<II", data, cursor)
        _require(page % 4096 == 0 and page > last_page and block_size >= 8
                 and block_size % 4 == 0 and cursor + block_size <= reloc_at + reloc_size,
                 "relocation block differs")
        last_page = page
        for at in range(cursor + 8, cursor + block_size, 2):
            entry, = _unpack("<H", data, at)
            kind, delta = entry >> 12, entry & 4095
            _require(kind in (0, 3) and (kind != 0 or delta == 0), "unknown relocation type")
            if kind == 3:
                temporary.file_offset(page + delta, 4)
                fixups.append(page + delta)
        cursor += block_size
    _require(cursor == reloc_at + reloc_size and len(set(fixups)) == len(fixups)
             and all(a + 4 <= b for a, b in zip(sorted(fixups), sorted(fixups)[1:])),
             "overlapping or duplicate relocations")
    # File-offset edits must never be mistaken for loaded absolute VA operands.
    for rva in fixups:
        at = temporary.file_offset(rva, 4)
        _require(all(at + 4 <= field or field + 4 <= at for field, _, _ in file_offsets),
                 "HIGHLOW overlaps file-offset field")
    return _PE(data, pe, opt, table, headers, image_size, tuple(sections), directories,
               tuple(file_offsets), tuple(sorted(fixups)))


def _validate_reservations(rx_bytes, rw_bytes, provider_schema):
    _require(type(rx_bytes) is type(rw_bytes) is int and (rx_bytes, rw_bytes) == (0x40000, 0x10000),
             "fixed V2 reservation contract required")
    _require(type(provider_schema) is str and provider_schema == "unpopulated_provider_reservation_v1",
             "unknown provider reservation schema")


def _relayout(parent, target_headers):
    before = _parse(parent)
    _require(type(target_headers) is int and target_headers in (0x400, 0x800)
             and target_headers >= before.headers, "unsupported header growth")
    delta = target_headers - before.headers
    _require(not delta or before.headers == 0x400, "unexpected header growth source")
    result = bytearray(parent[:before.headers] + bytes(delta) + parent[before.headers:])
    edits = []

    def edit(old_at, old, new, role):
        at = old_at + (delta if old_at >= before.headers else 0)
        _require(result[at:at + 4] == struct.pack("<I", old), "file-offset old bytes differ")
        _require(new < 0x80000000, "retargeted file offset overflows")
        replacement = struct.pack("<I", new)
        if old != new:
            edits.append(FileOffsetEdit(at, bytes(result[at:at + 4]), replacement, role))
            result[at:at + 4] = replacement

    edit(before.opt + 60, before.headers, target_headers, "SizeOfHeaders")
    for at, pointer, role in before.file_offsets:
        edit(at, pointer, pointer + delta, role)
    edits.sort(key=lambda row: row.offset)
    _require(all(a.offset + len(a.old) <= b.offset for a, b in zip(edits, edits[1:])),
             "overlapping file-offset edits")
    emitted = bytes(result)
    _verify_relayout(parent, emitted, target_headers, tuple(edits))
    return emitted, tuple(edits)


def _verify_relayout(parent, result, target_headers, edits):
    _require(type(parent) is type(result) is bytes and type(edits) is tuple,
             "immutable relayout receipt required")
    old, new = _parse(parent), _parse(result)
    delta = target_headers - old.headers
    _require(new.headers == target_headers and len(result) == len(parent) + delta,
             "header relayout extent differs")
    expected = bytearray(parent[:old.headers] + bytes(delta) + parent[old.headers:])
    canonical = []
    fields = [(old.opt + 60, old.headers, target_headers, "SizeOfHeaders")]
    fields += [(at, pointer, pointer + delta, role) for at, pointer, role in old.file_offsets]
    for at, previous, next_value, role in fields:
        if previous == next_value:
            continue
        destination = at + (delta if at >= old.headers else 0)
        raw_old, raw_new = struct.pack("<I", previous), struct.pack("<I", next_value)
        _require(expected[destination:destination + 4] == raw_old, "relayout inventory old bytes differ")
        canonical.append(FileOffsetEdit(destination, raw_old, raw_new, role))
        expected[destination:destination + 4] = raw_new
    _require(tuple(sorted(canonical, key=lambda row: row.offset)) == edits and bytes(expected) == result,
             "undeclared parent-prefix edit or forged file-offset inventory")
    _require(len(old.sections) == len(new.sections) and old.image_size == new.image_size
             and old.highlow == new.highlow, "loaded section/relocation identity differs")
    for a, b in zip(old.sections, new.sections):
        _require((a.name, a.virtual_size, a.rva, a.raw_size, a.flags, a.reloc_count, a.line_count)
                 == (b.name, b.virtual_size, b.rva, b.raw_size, b.flags, b.reloc_count, b.line_count),
                 "loaded section ownership differs")
        if a.raw:
            # Debug pointer fields are file offsets within section storage. All
            # other loaded bytes, including every absolute operand, are exact.
            chunk = bytearray(parent[a.raw:a.raw + a.raw_size])
            for edit in edits:
                if b.raw <= edit.offset < b.raw + b.raw_size:
                    offset = edit.offset - b.raw
                    _require(chunk[offset:offset + 4] == edit.old, "mapped offset repair old bytes differ")
                    chunk[offset:offset + 4] = edit.new
            _require(bytes(chunk) == result[b.raw:b.raw + b.raw_size], "loaded section bytes differ")
    for rva in old.highlow:
        _require(parent[old.file_offset(rva, 4):old.file_offset(rva, 4) + 4]
                 == result[new.file_offset(rva, 4):new.file_offset(rva, 4) + 4],
                 "loaded HIGHLOW operand differs")
    reloc_rva, reloc_size = old.directories[5]
    _require(old.directories == new.directories or
             all(a == b for i, (a, b) in enumerate(zip(old.directories, new.directories)) if i != 4),
             "RVA data directory changed")
    _require(parent[old.file_offset(reloc_rva, reloc_size):old.file_offset(reloc_rva, reloc_size) + reloc_size]
             == result[new.file_offset(reloc_rva, reloc_size):new.file_offset(reloc_rva, reloc_size) + reloc_size],
             "base relocation bytes differ")


def _layout(original, parent, profile, resolution, parent_stage):
    """Pure schema boundary; this function supplies no production authority."""
    _require(type(profile) is str and profile in PROFILES and type(resolution) is str
             and resolution in RESOLUTIONS and type(parent_stage) is str and parent_stage.endswith("-allpresets-validation"),
             "fixed profile/preset/validation parent required")
    _validate_reservations(RX_BYTES, RW_BYTES, PROVIDER_SCHEMA)
    original_pe, pe = _parse(original), _parse(parent)
    _require(len(original_pe.sections) == 7 and pe.headers == original_pe.headers == 0x400,
             "historical seven-section/header identity differs")
    _require(pe.sections[:7] == original_pe.sections, "original section headers changed")
    # Parent loaded bytes may contain authenticated recipe patches. Production
    # reconstruction binds them; format validation cannot invent old-byte proof.
    width, height = map(int, resolution.split("x"))
    suffix = () if profile == "classic" and width < 1144 else (b".hdcode",)
    if profile in ("completehd", "modalwidgets"):
        suffix = (b".hdcode", b".hdmodal", b".hdstate", b".hdarmy")
        if profile == "modalwidgets":
            suffix += (b".hdslots", b".hdprim", b".hdptxt", b".hdwgt")
    _require(tuple(s.name.rstrip(b"\0") for s in pe.sections[7:]) == suffix
             and all(s.flags == (RW_FLAGS if s.name.rstrip(b"\0") == b".hdstate" else RX_FLAGS)
                     for s in pe.sections[7:]), "historical profile sections differ")
    slot = pe.table + 40 * len(pe.sections)
    expected_slot = (0x280 if not suffix else 0x2A8) if profile in ("classic", "framed") else (0x320 if profile == "completehd" else 0x3C0)
    _require(slot == expected_slot and parent[slot:min(slot + 80, pe.headers)] == bytes(min(80, pe.headers - slot)),
             "unused future header slots are not zero")
    target_headers = 0x800 if profile == "modalwidgets" else 0x400
    _require(slot + 80 <= target_headers and (profile not in ("classic", "framed") or slot + 80 <= 0x300),
             "header scratch/section extent differs")
    relayout, edits = _relayout(parent, target_headers)
    moved = _parse(relayout)
    _require(relayout[slot:slot + 80] == bytes(80), "future header slots differ after growth")
    for s in pe.sections:
        if s.name.rstrip(b"\0") == b".hdstate":
            _require(s.virtual_size == s.raw_size == 4096 and not any(parent[s.raw:s.raw + s.raw_size]),
                     "inherited modal page zero state differs")
    rx_rva = pe.image_size
    rw_rva = rx_rva + RX_BYTES
    future_image = rw_rva + RW_BYTES
    _require(0x400000 + future_image < 0x80000000, "future allocations overflow x86 user space")
    raw = _align(len(relayout), 512)
    _require(raw == len(relayout), "canonical allocation append boundary must be file aligned")
    rx = Allocation(b".hdb2rx", 0x400000 + rx_rva, rx_rva, raw, RX_BYTES, slot, RX_FLAGS)
    rw = Allocation(b".hdb2rw", 0x400000 + rw_rva, rw_rva, raw + RX_BYTES, RW_BYTES, slot + 40, RW_FLAGS)
    spans = tuple(ProtectedSpan(0x400000 + s.rva, _align(s.extent, 4096), "parent:" + s.name.rstrip(b"\0").decode("ascii"))
                  for s in pe.sections)
    spans += (ProtectedSpan(rx.va, RX_BYTES, "future_rx_reservation"),
              ProtectedSpan(rw.va, STATE_PAGE_BYTES, "future_battle_state_page"),
              ProtectedSpan(rw.va + STATE_PAGE_BYTES, RW_BYTES - STATE_PAGE_BYTES, "future_unpopulated_provider_reservation"))
    _require(all(a.va + a.size <= b.va for a, b in zip(spans, spans[1:])), "protected ownership ranges overlap")
    capacity = min(20, (width - 160 - 32) // 64)
    _require(capacity >= 1 and height >= 600, "unsupported battle geometry")
    geometry = tuple(Geometry(n, min(n, capacity), max(0, n - capacity),
                             (32, 16, 32 + min(n, capacity) * 64 - 1, 463),
                             width - 160 - (32 + min(n, capacity) * 64)) for n in range(1, 21))
    layout = BattleAllocationLayout(profile, resolution, parent_stage + "-battle-context-v2-validation",
        rx, rw, rw.va, STATE_BYTES, STATE_PAGE_BYTES, rw.va + STATE_PAGE_BYTES, RW_BYTES - STATE_PAGE_BYTES,
        PROVIDER_SCHEMA, pe.headers, target_headers, pe.headers, target_headers - pe.headers,
        7, len(pe.sections), len(pe.sections) + 2, future_image, rw.raw_offset + RW_BYTES,
        edits, spans, moved.highlow, geometry)
    return relayout, layout


@contextmanager
def _private_predecessor(raw):
    name = "_battle_context_v2_parent_" + uuid.uuid4().hex
    module = types.ModuleType(name)
    module.__file__ = str(ROOT / PREDECESSOR)
    sys.modules[name] = module
    try:
        exec(compile(raw, module.__file__, "exec"), module.__dict__)
        yield module
    finally:
        _require(sys.modules.get(name) is module, "private predecessor namespace identity changed")
        del sys.modules[name]


def _sources(profile):
    own, own_stamp = _read_path(ROOT / SOURCE, ROOT)
    loaded = globals().get("__loaded_source_sha256__")
    _require(type(loaded) is str and loaded == _sha(own), "canonical loaded V2 source differs")
    raw, stamp = _read_path(ROOT / PREDECESSOR, ROOT)
    _require(_sha(raw) == PREDECESSOR_SHA256, "frozen context source differs")
    with _private_predecessor(raw) as predecessor:
        snapshots, _ = predecessor._source_snapshot(profile)
    records = {SOURCE: (own, own_stamp), PREDECESSOR: (raw, stamp)}
    for name, source in snapshots.items():
        current, source_stamp = _read_path(ROOT / name, ROOT)
        _require(current == source, "source differs from frozen parent snapshot")
        records[name] = current, source_stamp
    return records


def _check_sources(records):
    for name, receipt in records.items():
        _require(_read_path(ROOT / name, ROOT) == receipt, "source closure changed during context admission")


def _issue(original, profile, resolution):
    _require(type(original) is bytes and _sha(original) == BASE_SHA256, "exact original required")
    _require(type(profile) is str and profile in PROFILES and type(resolution) is str and resolution in RESOLUTIONS,
             "fixed profile/preset required")
    records = _sources(profile)
    _check_sources(records)
    with _private_predecessor(records[PREDECESSOR][0]) as predecessor:
        parent_context = predecessor.build_parent_context(original, profile, resolution)
        # V1 performs two independent full-byte/typed-metadata/probe builds and
        # authenticates every inherited state reference. It remains frozen.
        parent_metadata = parent_context.parent_metadata()
        relayout, layout = _layout(original, parent_context.candidate, profile, resolution, parent_metadata["stage"])
        typed = parent_context.parent_metadata_json
        probe = parent_context.canonical_probe
    _check_sources(records)
    metadata = dict(schema="clash95_battle_profile_context_v2", revision=REVISION,
        profile=profile, resolution=resolution, stage=layout.validation_stage,
        original_sha256=BASE_SHA256, parent_sha256=_sha(parent_context.candidate),
        relayout_parent_sha256=_sha(relayout), canonical_parent_probe_sha256=_sha(probe.encode()),
        source_hashes={name: _sha(raw) for name, (raw, _) in records.items()},
        allocation_plan_only=True, canonical_parent_reconstructed=True,
        header_relayout_emitted=layout.insertion_bytes != 0, new_sections_emitted=False,
        rx_bytes=RX_BYTES, rw_bytes=RW_BYTES, fresh_state_bytes=STATE_BYTES,
        protected_state_page_bytes=STATE_PAGE_BYTES,
        provider_reservation_bytes=layout.provider_reservation_bytes, provider_schema=PROVIDER_SCHEMA,
        provider_records_emitted=0, provider_catalog_capacity=None,
        zero_initialization_required=True, final_recipe_and_probe_unemitted=True,
        signature_validity_verified=False,
        limitations=["Header relayout only; no candidate is saved and no new section/code/state/provider/hook is installed.",
            "The canonical parent probe belongs to the unchanged parent, not the relayout or a future battle successor.",
            "Every future emitter must re-emit and fully relocate for these new code/state addresses; historical emitters are not compatible installers.",
            "The unpopulated provider reservation has no proven record schema, resource capacity, constructor identity, lifetime or cancellation coverage.",
            "Signed-file authentication and unknown auxiliary/overlay/header resource schemas are not admitted.",
            "RLE/provider cancellation, animation/dialog/results/input/camera/restoration and complete atomic installation remain unproved.",
            "All 36 runtime, visual, human-input, endurance and promotion combinations remain separately required."],
        **{name: False for name in FALSE_CLAIMS})
    return BattleProfileContextV2(parent_context.candidate, relayout, typed, probe, layout,
        json.dumps(metadata, sort_keys=True, separators=(",", ":"), allow_nan=False))


def build_allocation_context(original, profile, resolution):
    raise ValueError("captured canonical V2 factory required")


def _production_factory():
    # The dispatcher captures an independently compiled issuer, canonical path
    # reader and original identity. Mutable public module helpers are not used.
    from hashlib import sha256 as digest
    from pathlib import Path as SourcePath
    from types import ModuleType as SourceModule
    from uuid import uuid4 as unique_name
    from sys import modules as registry
    exact_type, exact_bytes, rejection = type, bytes, ValueError
    compile_source, execute_source = compile, exec
    path = SourcePath(__file__).absolute()
    root = path.parents[2]
    if path != root / "src/patcher/battle_profile_context_v2.py":
        raise rejection("canonical V2 producer path required")

    def read():
        if path.resolve(strict=True) != path or root.resolve(strict=True) != root:
            raise rejection("canonical V2 source path required")
        for item in (path, *path.parents):
            row = item.lstat()
            if item.is_symlink() or getattr(row, "st_file_attributes", 0) & 0x400:
                raise rejection("V2 source reparse path forbidden")
        before = path.stat(); raw = path.read_bytes(); after = path.stat()
        def stamp(value):
            return value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns, getattr(value, "st_file_attributes", 0)
        if stamp(before) != stamp(after) or len(raw) != after.st_size:
            raise rejection("canonical V2 source changed while read")
        return raw, stamp(after)

    source, initial = read()
    source_digest = digest(source).hexdigest()
    name = "_battle_context_v2_issuer_" + unique_name().hex
    module = SourceModule(name)
    module.__file__ = str(path)
    module.__loaded_source_sha256__ = source_digest
    module.__canonical_context_v2_issuer__ = True
    registry[name] = module
    try:
        execute_source(compile_source(source, str(path), "exec"), module.__dict__)
        issuer = module.__dict__["_issue"]
    finally:
        if registry.get(name) is not module:
            raise rejection("canonical V2 issuer namespace identity changed")
        del registry[name]
    if read() != (source, initial):
        raise rejection("canonical V2 source changed during factory capture")
    original_digest = "500055d77d03d514e8d3168506bd10f67cd8569bcc450604ff8192f46cdaf3ae"

    def dispatch(original, profile, resolution):
        if exact_type(original) is not exact_bytes or digest(original).hexdigest() != original_digest:
            raise rejection("exact original required")
        raw, stamp = read()
        if digest(raw).hexdigest() != source_digest:
            raise rejection("captured canonical V2 source differs")
        try:
            return issuer(original, profile, resolution)
        finally:
            if read() != (raw, stamp):
                raise rejection("canonical V2 source changed during dispatch")
    return dispatch


if not globals().get("__canonical_context_v2_issuer__", False):
    build_allocation_context = _production_factory()
