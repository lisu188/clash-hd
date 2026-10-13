"""Uninstalled native destinations for the seventeen remaining content sites.

Complete fresh ContentV2 blocks supply values through their actual admission
receipts. Native MOV destinations and exact scalar tails are restored only for
status one. Every detected rejection reaches UD2, never a borrowed epilogue.
This preparation installs no hook, PE candidate, provider or release proof.
"""
from __future__ import annotations

import ast
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
SOURCE = "src/patcher/battle_profile_content_replay.py"
TILE = "src/patcher/battle_profile_tile_replay.py"
TILE_SHA256 = "2df87c637b5477ed4154a57fd69751f4a7f48712dc73ccac23c133e543a2a8c6"
LOSS = "src/patcher/battle_profile_field_loss.py"
CONTENT = "src/patcher/battle_profile_content_v2.py"
TEMPLATE = "src/patcher/battle_profile_content.py"
TEMPLATE_SHA256 = "52f9ac7f8d52cb40638e91868910d6487cea083be0cc32e622d8fe4a3f8cf3d7"
LEDGER = "src/patcher/battle_profile_continuation.py"
LEDGER_SHA256 = "075bd62a8311f8cc761136bca21063813dfc874ce8d8a5bcf075ebdb664d811f"
CLIP = "src/patcher/partial_tile_clip.py"
BASE_SHA256 = "500055d77d03d514e8d3168506bd10f67cd8569bcc450604ff8192f46cdaf3ae"
HELPER_BYTES = 784
NATIVE_RETURN = HELPER_BYTES + 36
BODY_SP = dict(unit=-64, adjacent=-16, vertical=-8, count=-28)
BODY_SITES = (0x42f7cf, 0x42f84a, 0x42f9af, 0x42f9c3, 0x42f9d7,
              0x42f9ec, 0x42fc5f, 0x42fc92, 0x42fcea, 0x42fd26,
              0x42fd7f, 0x42fdc0, 0x42fe23, 0x42fe68, 0x42febb,
              0x426f44, 0x426f54)
FALSE_CLAIMS = (
    "source_accepted", "source_acceptance", "installed", "battle_installed",
    "expanded_battle_installed", "source_candidate_installed", "installation_ready",
    "standalone_native_callsite_replacement_safe", "native_executed", "game_executed",
    "runtime_executed", "runtime_verified", "manual_input_proof", "manual_input_verified",
    "promotion_ready", "release_accepted", "native_callback_abi_verified",
    "native_stack_capacity_verified", "whole_chain_capacity_verified",
    "native_receiver_validity_verified", "native_argument_validity_verified",
    "provider_validity_verified", "provider_capacity_verified", "provider_lifetime_verified",
    "native_provider_rle_verified", "intra_decoder_cancellation", "provider_early_cancellation",
    "native_continuation_cancellation", "healthy_return_verified", "healthy_native_unwind_verified",
    "process_quit_closure_verified", "atomic_installation_verified",
    "physical_only_clip_admission_verified", "arena_intersection_verified",
    "transient_write_prevention_verified", "cross_thread_immutability_verified",
    "count_entry_record_guard_installed", "non_draw_count_admission",
    "native_count_early_reads_adapted", "native_sentinel_record_verified",
    "downstream_frozen_continuation_compatible", "downstream_frozen_primitive_compatible",
)


def _require(value, message):
    if not value:
        raise ValueError(message)


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _read(path):
    _require(path.is_absolute() and path.is_relative_to(ROOT) and path.resolve(strict=True) == path,
             "canonical content replay source required")
    for item in (path, *path.parents):
        row = item.lstat()
        _require(not item.is_symlink() and not getattr(row, "st_file_attributes", 0) & 0x400,
                 "content replay source reparse forbidden")
    before = path.stat()
    _require(0 < before.st_size <= 2 * 1024 * 1024, "bounded content replay source required")
    with path.open("rb") as stream:
        raw = stream.read(2 * 1024 * 1024 + 1)
    after = path.stat()
    stamp = lambda r: (r.st_dev, r.st_ino, r.st_size, r.st_mtime_ns, getattr(r, "st_file_attributes", 0))
    _require(stamp(before) == stamp(after) and len(raw) == after.st_size,
             "content replay source changed while read")
    return raw, stamp(after)


@contextmanager
def _tile_module(raw):
    _require(type(raw) is bytes and _sha(raw) == TILE_SHA256, "frozen Tile replay producer differs")
    name = "_content_replay_tile_" + uuid.uuid4().hex
    module = types.ModuleType(name)
    module.__file__ = str(ROOT / TILE)
    module.__loaded_source_sha256__ = TILE_SHA256
    module.__canonical_tile_replay_issuer__ = True
    _require(sys.modules.setdefault(name, module) is module, "content replay namespace occupied")
    try:
        exec(compile(raw, module.__file__, "exec"), module.__dict__)
        yield module
    finally:
        replaced = sys.modules.get(name) is not module
        if sys.modules.get(name) is module:
            del sys.modules[name]
        _require(not replaced, "content replay namespace identity changed")


def _snapshot():
    tile = _read(ROOT / TILE)
    with _tile_module(tile[0]) as producer:
        result = producer._snapshot()
    own = _read(ROOT / SOURCE)
    _require(result[TILE] == tile and _sha(result[LEDGER][0]) == LEDGER_SHA256 and
             _sha(result[TEMPLATE][0]) == TEMPLATE_SHA256 and
             globals().get("__loaded_source_sha256__") == _sha(own[0]),
             "private unchanged content replay source graph required")
    return result | {SOURCE: own}


def _unchanged(snapshot):
    _require(all(_read(ROOT / name) == receipt for name, receipt in snapshot.items()),
             "content replay source graph changed")


@dataclass(frozen=True)
class Operand:
    instruction_offset: int
    instruction_bytes: int
    offset: int
    kind: str
    role: str
    value: int


@dataclass(frozen=True)
class ContentReplayEmission:
    base_va: int
    state_va: int
    code: bytes
    entries: tuple
    relocations: tuple
    width: int
    height: int
    private_entries: tuple
    body_receipts: tuple
    source_blocks: tuple
    planned_hooks: tuple


@dataclass(frozen=True)
class ContentReplayBundle:
    emission: ContentReplayEmission
    tile_replay_bundle: object
    operand_inventory: tuple
    metadata_json: str
    hook_sites: tuple = ()
    removed_highlow_rvas: tuple = ()

    def metadata(self):
        return json.loads(self.metadata_json)


def _identity(out):
    """Every immutable parent byte, typed field and source receipt matters."""
    return (out.base_va, out.state_va, out.code, out.entries, out.private_entries,
            tuple((r.offset, r.kind, r.target, r.purpose) for r in out.relocations),
            out.width, out.height, tuple(getattr(out, "body_receipts", ())),
            tuple(getattr(out, "source_blocks", ())), tuple(getattr(out, "planned_hooks", ())),
            tuple(getattr(out, "field_call_patches", ())),
            tuple(getattr(out, "field_return_pcs", ())), tuple(getattr(out, "lease_return_pcs", ())),
            tuple(getattr(out, "field_tile_receipts", ())), tuple(getattr(out, "lease_field_receipts", ())))


def _literal(raw, name):
    nodes = [n for n in ast.parse(raw).body if isinstance(n, ast.Assign) and
             any(isinstance(t, ast.Name) and t.id == name for t in n.targets)]
    _require(len(nodes) == 1, "one complete frozen content replay ledger field required")
    return ast.literal_eval(nodes[0].value)


def _frozen_windows(ledger_source):
    _require(type(ledger_source) is bytes and _sha(ledger_source) == LEDGER_SHA256,
             "whole frozen native continuation ledger required")
    template = _read(ROOT / TEMPLATE)[0]
    _require(_sha(template) == TEMPLATE_SHA256, "whole frozen content template required")
    sites = _literal(template, "SITES")
    windows = _literal(ledger_source, "CONTENT_WINDOWS")
    highlow = _literal(ledger_source, "NATIVE_HIGHLOW")
    _require(type(sites) is type(windows) is type(highlow) is tuple and
             len(sites) == len(windows) == 28 and len(highlow) == len(set(highlow)) == 17 and
             tuple(row[0] for row in windows) == tuple(row[0] for row in sites),
             "complete frozen native content replay inventory differs")
    result = []
    for site, (va, window_hex) in zip(sites, windows):
        if site[2] == "tile":
            continue
        operand, window = bytes.fromhex(site[1]), bytes.fromhex(window_hex)
        if operand[:2] == b"\x0f\xbf":
            destination, bits = (operand[2] >> 3) & 7, 32
            _require(len(operand) in (7, 8), "whole native content MOVSX required")
        elif operand[:2] == b"\x66\x8b":
            destination, bits = (operand[2] >> 3) & 7, 16
            _require(len(operand) == 7 and destination == 0, "whole native AX operand required")
        else:
            _require(operand[0] == 0x8a and len(operand) in (6, 7), "whole native byte operand required")
            destination, bits = (operand[1] >> 3) & 7, 8
            _require(destination in (2, 3), "fixed native DL/BL destination required")
        _require(va == site[0] and site[2] in BODY_SP and destination in (0, 1, 2, 3) and
                 window.startswith(operand) and 9 <= len(window) <= 13,
                 "complete native content operand/window required")
        removed = tuple(h - 0x400000 for h in highlow if va <= h < va + len(window))
        result.append((site, window, destination, bits, removed))
    _require(tuple(row[0][0] for row in result) == BODY_SITES and
             tuple(rva for row in result for rva in row[4]) == (0x2f9cc,),
             "seventeen ordered native content windows/one HIGHLOW required")
    return tuple(result)


def _source_block(content, index):
    parent = dict(content.private_entries)
    receipts = content.body_receipts
    _require(len(receipts) == 28 and tuple(row[0] for row in receipts[11:]) == BODY_SITES and
             tuple(parent) == ("capture_inputs", "capture_stack", "admit_body", "fixed_receipt",
                               "unsafe_control", "finish_rejected", "finish_valid"),
             "complete source-owned content body/finish ABI required")
    va, entry, payload, pc, denied, fault, valid = receipts[index]
    end = receipts[index + 1][1] if index + 1 < len(receipts) else parent["finish_rejected"]
    lo, hi = entry - content.base_va, end - content.base_va
    raw = content.code[lo:hi]
    _require(0 <= lo < hi <= len(content.code) and
             raw[:11] == b"\x9c\x60\xfc\x81\xec" + struct.pack("<I", HELPER_BYTES) + b"\x89\xe5" and
             entry < pc < payload < valid < fault < denied < end,
             "complete 784-byte source-owned ContentV2 block required")
    at = pc - content.base_va - 4
    rows = [r for r in content.relocations if r.offset == at]
    _require(content.code[at - 1] == 0xe8 and len(rows) == 1 and
             (rows[0].kind, rows[0].target, rows[0].purpose) ==
             ("rel32", parent["admit_body"], "content_v2_internal:admit_body"),
             "actual complete ContentV2 body admission CALL required")
    return va, entry, payload, pc, denied, fault, valid, end, lo, hi, raw, at


def _raw_emit(layout, field, lease, content, loss, joined_field, tile, *, content_module,
              assembler_module, ledger_source):
    """Explicit synthetic emission boundary, never production admission."""
    windows = _frozen_windows(ledger_source)
    _require(loss.base_va == (content.base_va + len(content.code) + 15) & ~15 and
             tile.base_va == (loss.base_va + len(loss.code) + 15) & ~15 and
             joined_field.base_va == field.base_va and
             tile.state_va == loss.state_va == content.state_va == field.state_va == lease.state_va == layout.rw.va and
             (tile.width, tile.height) == (content.width, content.height) == (loss.width, loss.height) ==
             (field.width, field.height), "complete fresh content replay prefix extent required")
    base = (tile.base_va + len(tile.code) + 15) & ~15
    a = assembler_module._Assembler(base)
    parent = dict(content.private_entries)
    assembler_module.absolute_relocation_offsets(content)
    assembler_module.absolute_relocation_offsets(tile)
    sources, hooks, bodies = [], [], []

    def transfer(target, purpose, opcode="e9"):
        a.emit(opcode)
        at = len(a.code)
        a.relocations.append(assembler_module.Relocation(at, "rel32", target, purpose))
        a.u32(target - base - at - 4)

    def internal(at, label):
        struct.pack_into("<I", a.code, at, 0)
        a.fixups.append((at, label))

    def tail_preconditions(va):
        if va == 0x42f9c3:
            # The displaced ADD addresses the eight-entry, 64-byte table by
            # native EDI. Parent admission has captured this exact register.
            a.emit("89c38b85"); a.u32(400)
            a.emit("a907000000"); a.branch("0f85", "unsafe_control")
            a.emit("83f840"); a.branch("0f83", "unsafe_control")
            a.emit("89d8")
        elif va == 0x42f9ec:
            # The compared owner belongs to SELF, not necessarily the payload
            # neighbor INDEX. UNIT_S-28 is a captured/rechecked ancestor word.
            a.emit("89c38bb5"); a.u32(216)
            a.emit("8b46e481f8"); a.u32(22 * 31)
            a.branch("0f83", "unsafe_control")
            a.emit("31d2b91f000000f7f185d2"); a.branch("0f85", "unsafe_control")
            a.emit("6bc01f8b8d"); a.u32(372)
            a.emit("01c8"); a.branch("0f82", "unsafe_control")
            a.emit("3b85"); a.u32(420)
            a.branch("0f85", "unsafe_control")
            a.emit("89d8")

    def scalar_tail(site, window, removed):
        va = site[0]
        tail = window[len(bytes.fromhex(site[1])):]
        allowed = (b"\x6b\xc0\x58", b"\x83\xf8\xff", b"\x01\xd8\x6b\xc0\x28",
                   b"\x03\x87\x38\x33\x51\x00", b"\x3a\x9a\x56\x03\x00\x00",
                   b"\x83\xf8\x1b", b"\x83\xf9\xff", b"\x3a\x57\x02")
        _require(tail in allowed, "closed exact native content scalar tail required")
        at = len(a.code)
        a.emit(tail.hex())
        if removed:
            _require(va == 0x42f9c3 and removed == (0x2f9cc,) and
                     tail == b"\x03\x87\x38\x33\x51\x00",
                     "complete stolen neighbor-table HIGHLOW operand required")
            a.relocations.append(assembler_module.Relocation(at + 2, "abs32", 0x513338,
                "native_content_scalar_highlow"))

    for number, (site, window, destination, bits, removed) in enumerate(windows, 11):
        va, old_entry, old_payload, old_pc, old_denied, old_fault, old_valid, old_end, lo, hi, raw, admit_at = _source_block(content, number)
        _require(va == site[0], "ordered source-owned content body required")
        start, entry = len(a.code), base + len(a.code)
        dispatch, guard = f"finish_{va:06x}", f"admit_{va:06x}"
        a.label(f"site_{va:06x}")
        a.emit(raw.hex())
        for row in content.relocations:
            if not lo <= row.offset < hi:
                continue
            _require(row.offset + 4 <= hi, "content replay relocation crosses source boundary")
            at = start + row.offset - lo
            if row.kind == "abs32":
                a.relocations.append(assembler_module.Relocation(at, "abs32", row.target,
                    "content_replay_source_absolute:" + row.purpose))
            elif row.offset == admit_at:
                internal(at, guard)
            elif old_entry <= row.target < old_end:
                _require(row.kind == "rel32", "source-owned internal content relative required")
                target = entry + row.target - old_entry
                struct.pack_into("<i", a.code, at, target - base - at - 4)
                a.relocations.append(assembler_module.Relocation(at, "rel32", target,
                    "content_replay_internal:source_block"))
            elif row.target in (parent["finish_rejected"], parent["finish_valid"]):
                _require(row.kind == "rel32" and a.code[at - 1] == 0xe9,
                         "outer content replay finish JMP required")
                internal(at, dispatch)
            else:
                _require(row.kind == "rel32" and row.target == parent["capture_inputs"] and
                         a.code[at - 1] == 0xe8, "unexpected external content block transfer")
                struct.pack_into("<i", a.code, at, row.target - base - at - 4)
                a.relocations.append(assembler_module.Relocation(at, "rel32", row.target,
                    "content_replay_capture_inputs"))
        a.label(dispatch)
        a.emit("83fa01"); a.branch("0f85", "unsafe_control")
        a.emit("39ec"); a.branch("0f85", "unsafe_control")
        a.emit("8b95"); a.u32(NATIVE_RETURN)
        a.emit("81fa"); a.absolute(va + 5, "natural native content body CALL return")
        a.branch("0f85", "unsafe_control")
        tail_preconditions(va)
        saved_destination = HELPER_BYTES + {0: 28, 1: 24, 2: 20, 3: 16}[destination]
        a.emit("668985" if bits == 16 else "8885" if bits == 8 else "8985")
        a.u32(saved_destination)
        a.emit("81c4"); a.u32(HELPER_BYTES)
        a.emit("619d8d642404")
        scalar_tail(site, window, removed)
        transfer(va + len(window), "native_content_resume")
        a.label(guard)
        a.emit("8d4c240439cd"); a.branch("0f85", "unsafe_control")
        a.emit("8b042481f8")
        a.absolute(entry + old_pc - old_entry, "actual content adapter admission CALL return")
        a.branch("0f85", "unsafe_control")
        transfer(parent["admit_body"], "native_content_admission_parent")
        bodies.append((va, entry, entry + old_payload - old_entry, entry + old_pc - old_entry,
                       entry + old_denied - old_entry, entry + old_fault - old_entry,
                       entry + old_valid - old_entry, base + a.labels[dispatch], va + len(window)))
        sources.append((va, old_entry, old_end, _sha(raw), entry, old_pc))
        hooks.append((va, window, entry, "content_operand", removed))
    a.label("unsafe_control"); a.emit("0f0b")
    code = bytes(a.finish())
    for off, label in a.fixups:
        a.relocations.append(assembler_module.Relocation(off, "rel32", base + a.labels[label],
            "content_replay_internal:" + label))
    _require(base + len(code) <= layout.rx.va + layout.rx.size,
             "content replay exceeds fresh RX reservation")
    out = ContentReplayEmission(base, layout.rw.va, code,
        tuple((f"site_{va:06x}", base + a.labels[f"site_{va:06x}"]) for va in BODY_SITES),
        tuple(a.relocations), field.width, field.height,
        (("unsafe_control", base + a.labels["unsafe_control"]),) +
        tuple((f"admit_{va:06x}", base + a.labels[f"admit_{va:06x}"]) for va in BODY_SITES),
        tuple(bodies), tuple(sources), tuple(hooks))
    assembler_module.absolute_relocation_offsets(out)
    _operand_inventory(out, content, ledger_source=ledger_source)
    return out


def _emit_code(layout, life, route, field, lease, content, loss, joined_field, tile, *,
               tile_module, tile_kwargs, content_module, assembler_module, ledger_source):
    """Reconstruct the complete fresh chain for explicit synthetic fixtures."""
    expected = tile_module._emit_code(layout, life, route, field, lease, content, loss, joined_field,
                                      **tile_kwargs)
    _require(_identity(tile) == _identity(expected),
             "complete canonical Tile replay bytes/source blocks/windows/receipts required")
    return _raw_emit(layout, field, lease, content, loss, joined_field, tile,
        content_module=content_module, assembler_module=assembler_module, ledger_source=ledger_source)


def _decode(code):
    """Closed authored source/native scalar dialect; address roles are explicit."""
    cursor, rows = 0, []
    while cursor < len(code):
        start, fields = cursor, []
        opcode = code[cursor]; cursor += 1; memory = False
        if opcode in (0x9c, 0x9d, 0x60, 0x61, 0xfc, 0xc3, 0x55, 0x5d, 0x4b):
            pass
        elif 0xb8 <= opcode <= 0xbf or opcode in (0xa9, 0x3d):
            fields.append((cursor, 4, "immediate")); cursor += 4
        elif opcode in (0xe8, 0xe9):
            fields.append((cursor, 4, "relative")); cursor += 4
        elif opcode == 0x0f:
            _require(cursor < len(code), "truncated content replay escape")
            sub = code[cursor]; cursor += 1
            if sub == 0x0b:
                pass
            elif 0x80 <= sub <= 0x8f:
                fields.append((cursor, 4, "relative")); cursor += 4
            else:
                _require(sub in (0xb6, 0xb7, 0xbf), "content replay extended load differs")
                memory = True
        elif opcode == 0x66:
            _require(cursor < len(code) and code[cursor] in (0x8b, 0x89),
                     "content replay word prefix differs")
            cursor += 1; memory = True
        else:
            _require(opcode in (0x81, 0x83, 0x8b, 0x89, 0x88, 0x3b, 0x39, 0x3a, 0x03,
                                0x85, 0xf7, 0xff, 0x31, 0x29, 0x01, 0xc1, 0x6b, 0x8d, 0xd1),
                     "unknown content replay opcode at " + hex(start))
            memory = True
        if memory:
            _require(cursor < len(code), "truncated content replay ModRM")
            modrm = code[cursor]; cursor += 1; mode, rm = modrm >> 6, modrm & 7
            if mode != 3 and rm == 4:
                _require(cursor < len(code), "truncated content replay SIB")
                sib = code[cursor]; fields.append((cursor, 1, "sib")); cursor += 1
                if mode == 0 and sib & 7 == 5:
                    fields.append((cursor, 4, "memory_address")); cursor += 4
            if mode == 0 and rm == 5:
                fields.append((cursor, 4, "memory_address")); cursor += 4
            elif mode == 1:
                fields.append((cursor, 1, "displacement")); cursor += 1
            elif mode == 2:
                fields.append((cursor, 4, "displacement")); cursor += 4
            if opcode == 0x81 or opcode == 0xf7 and (modrm >> 3) & 7 == 0:
                fields.append((cursor, 4, "immediate")); cursor += 4
            elif opcode in (0x83, 0xc1, 0x6b):
                fields.append((cursor, 1, "immediate")); cursor += 1
        _require(start < cursor <= len(code), "truncated content replay instruction")
        rows.append((start, cursor, tuple(fields)))
    return tuple(rows)


def _authored_contract(out, content, ledger_source):
    """Independently rebuild every permitted byte and operand role.

    No relocation declaration in ``out`` selects an address or changes an
    instruction's meaning. The native indexed table displacement is the sole
    explicit displacement/HIGHLOW exception, not a numeric-VA heuristic.
    """
    windows = _frozen_windows(ledger_source)
    parent = dict(content.private_entries)
    expected, fields, bodies, sources, hooks, entries, guards = bytearray(), {}, [], [], [], [], []
    pending = []

    def field(at, kind, target, purpose):
        _require(at not in fields, "duplicate authored content replay operand")
        fields[at] = (kind, target, purpose)

    def emit(raw):
        expected.extend(bytes.fromhex(raw))

    def u32(value):
        expected.extend(struct.pack("<I", value & 0xffffffff))

    def unsafe(opcode):
        emit(opcode); pending.append(len(expected)); u32(0)

    def absolute(value, purpose):
        field(len(expected), "abs32", value, purpose); u32(value)

    def relative(value, purpose):
        field(len(expected), "rel32", value, purpose); u32(0)

    for number, (site, window, destination, bits, removed) in enumerate(windows, 11):
        va, old_entry, old_payload, old_pc, old_denied, old_fault, old_valid, old_end, lo, hi, raw, admit_at = _source_block(content, number)
        _require(va == site[0], "authored content body ordering differs")
        start, entry = len(expected), out.base_va + len(expected)
        dispatch = entry + len(raw)
        expected.extend(raw)
        source_admit = None
        source_finishes = []
        for row in content.relocations:
            if not lo <= row.offset < hi:
                continue
            _require(row.offset + 4 <= hi, "authored content relocation crosses source block")
            at = start + row.offset - lo
            if row.kind == "abs32":
                field(at, "abs32", row.target, "content_replay_source_absolute:" + row.purpose)
            elif row.offset == admit_at:
                _require(row.kind == "rel32" and row.target == parent["admit_body"] and
                         row.purpose == "content_v2_internal:admit_body" and raw[row.offset - lo - 1] == 0xe8,
                         "whole authored content admission CALL differs")
                source_admit = at
            elif old_entry <= row.target < old_end:
                _require(row.kind == "rel32", "authored content internal relative required")
                field(at, "rel32", entry + row.target - old_entry, "content_replay_internal:source_block")
            elif row.target in (parent["finish_rejected"], parent["finish_valid"]):
                _require(row.kind == "rel32" and raw[row.offset - lo - 1] == 0xe9,
                         "authored outer content finish JMP required")
                source_finishes.append(at)
            else:
                _require(row.kind == "rel32" and row.target == parent["capture_inputs"] and
                         raw[row.offset - lo - 1] == 0xe8, "authored content capture CALL differs")
                field(at, "rel32", row.target, "content_replay_capture_inputs")
        emit("83fa01"); unsafe("0f85")
        emit("39ec"); unsafe("0f85")
        emit("8b95"); u32(NATIVE_RETURN)
        emit("81fa"); absolute(va + 5, "natural native content body CALL return")
        unsafe("0f85")
        if va == 0x42f9c3:
            emit("89c38b85"); u32(400)
            emit("a907000000"); unsafe("0f85")
            emit("83f840"); unsafe("0f83")
            emit("89d8")
        elif va == 0x42f9ec:
            emit("89c38bb5"); u32(216)
            emit("8b46e481f8"); u32(682)
            unsafe("0f83")
            emit("31d2b91f000000f7f185d2"); unsafe("0f85")
            emit("6bc01f8b8d"); u32(372)
            emit("01c8"); unsafe("0f82")
            emit("3b85"); u32(420)
            unsafe("0f85")
            emit("89d8")
        emit("668985" if bits == 16 else "8885" if bits == 8 else "8985")
        u32(HELPER_BYTES + {0: 28, 1: 24, 2: 20, 3: 16}[destination])
        emit("81c4"); u32(HELPER_BYTES)
        emit("619d8d642404")
        tail = window[len(bytes.fromhex(site[1])):]
        if removed:
            _require(va == 0x42f9c3 and removed == (0x2f9cc,) and
                     tail == b"\x03\x87\x38\x33\x51\x00",
                     "exact authored native neighbor-table displacement required")
            field(len(expected) + 2, "abs32", 0x513338, "native_content_scalar_highlow")
        expected.extend(tail)
        emit("e9"); relative(va + len(window), "native_content_resume")
        guard = out.base_va + len(expected)
        emit("8d4c240439cd"); unsafe("0f85")
        emit("8b042481f8")
        absolute(entry + old_pc - old_entry, "actual content adapter admission CALL return")
        unsafe("0f85")
        emit("e9"); relative(parent["admit_body"], "native_content_admission_parent")
        _require(source_admit is not None and source_finishes, "complete authored content CALL/finish required")
        field(source_admit, "rel32", guard, f"content_replay_internal:admit_{va:06x}")
        for at in source_finishes:
            field(at, "rel32", dispatch, f"content_replay_internal:finish_{va:06x}")
        bodies.append((va, entry, entry + old_payload - old_entry, entry + old_pc - old_entry,
                       entry + old_denied - old_entry, entry + old_fault - old_entry,
                       entry + old_valid - old_entry, dispatch, va + len(window)))
        sources.append((va, old_entry, old_end, _sha(raw), entry, old_pc))
        hooks.append((va, window, entry, "content_operand", removed))
        entries.append((f"site_{va:06x}", entry))
        guards.append((f"admit_{va:06x}", guard))
    terminal = out.base_va + len(expected)
    emit("0f0b")
    for at in pending:
        field(at, "rel32", terminal, "content_replay_internal:unsafe_control")
    for at, (kind, target, _) in fields.items():
        struct.pack_into("<I", expected, at,
            target if kind == "abs32" else (target - out.base_va - at - 4) & 0xffffffff)
    _require(out.entries == tuple(entries) and
             out.private_entries == (("unsafe_control", terminal),) + tuple(guards) and
             out.body_receipts == tuple(bodies) and out.source_blocks == tuple(sources) and
             out.planned_hooks == tuple(hooks), "complete authored content receipt/window inventory differs")
    _require(out.code == bytes(expected), "complete authored content source/native finish bytes differ")
    return fields


def _operand_inventory(out, content, *, ledger_source=None):
    if ledger_source is None:
        ledger_source = _read(ROOT / LEDGER)[0]
    authored = _authored_contract(out, content, ledger_source)
    rows = _decode(out.code)
    starts = {start for start, _, _ in rows}
    declared = {r.offset: r for r in out.relocations}
    _require(len(declared) == len(out.relocations), "duplicate content replay operand")
    _require({at: (r.kind, r.target, r.purpose) for at, r in declared.items()} == authored,
             "exact authored content absolute/relative operand roles differ")
    consumed, records = set(), []
    parent = dict(content.private_entries)
    resumes = {va + len(raw) for va, raw, *_ in out.planned_hooks}
    for start, end, fields in rows:
        for at, size, role in fields:
            row = declared.get(at)
            value = int.from_bytes(out.code[at:at + size], "little")
            if role == "relative":
                _require(row is not None and row.kind == "rel32", "missing content replay relative operand")
                value = out.base_va + at + 4 + struct.unpack_from("<i", out.code, at)[0]
                _require(value == row.target, "content replay relative target differs")
                if out.base_va <= value < out.base_va + len(out.code):
                    _require(value - out.base_va in starts and row.purpose.startswith("content_replay_internal:"),
                             "content replay internal instruction boundary differs")
                    typed = "internal_transfer"
                else:
                    contract = {"content_replay_capture_inputs": (0xe8, {parent["capture_inputs"]}),
                                "native_content_admission_parent": (0xe9, {parent["admit_body"]}),
                                "native_content_resume": (0xe9, resumes)}
                    _require(row.purpose in contract and out.code[start] == contract[row.purpose][0] and
                             value in contract[row.purpose][1], "unexpected external content replay transfer")
                    typed = row.purpose
                kind = "rel32"
            elif row is not None:
                table = row.purpose == "native_content_scalar_highlow"
                _require(size == 4 and row.kind == "abs32" and value == row.target and
                         (role in ("immediate", "memory_address") or
                          table and role == "displacement" and row.target == 0x513338 and
                          out.code[start:at] == b"\x03\x87"),
                         "content replay explicit absolute operand differs")
                kind, typed = "abs32", "native_table_base_displacement" if table else "authored_address"
            else:
                _require(role != "memory_address", "missing content replay memory relocation")
                kind, typed = "scalar" + str(size * 8), role
            if row is not None:
                consumed.add(at)
            records.append(Operand(start, end - start, at, kind, typed, value))
    _require(consumed == set(declared) and all(va - out.base_va in starts for _, va in out.entries + out.private_entries),
             "content replay relocation/entry boundary differs")
    return tuple(sorted(records, key=lambda row: row.offset))


def _authenticate_windows(original, relayout_parent, clip, pe, ledger_source):
    windows = _frozen_windows(ledger_source)
    for image in (original, relayout_parent):
        parsed = pe.inspect_pe(image)
        _, relocations = pe._old_relocations(image, parsed)
        actual = {parsed.image_base + rva for rva in relocations if
                  any(site[0] <= parsed.image_base + rva < site[0] + len(raw) for site, raw, _, _, _ in windows)}
        _require(actual == {0x42f9cc}, "complete selected native content HIGHLOW inventory differs")
        for site, raw, _, _, _ in windows:
            at = clip.file_offset(image, site[0], len(raw))
            _require(image[at:at + len(raw)] == raw, "whole native content operand/scalar window differs")


def _issue(original, profile, resolution):
    _require(type(original) is bytes and _sha(original) == BASE_SHA256, "exact content replay original required")
    snapshot = _snapshot()
    with _tile_module(snapshot[TILE][0]) as producer:
        parent = producer._issue(original, profile, resolution)
        loss_bundle = parent.field_loss_bundle
        content_bundle = loss_bundle.content_bundle
        lease_bundle = content_bundle.lease_bundle
        field_bundle = lease_bundle.field_bundle
        context = field_bundle.routing_bundle.lifecycle_bundle.allocation_context
        layout = context.layout
        with producer._loss_module(snapshot[LOSS][0]) as loss_module:
            with loss_module._content_module(snapshot[CONTENT][0]) as content_module:
                with content_module._modules(snapshot) as modules:
                    clip = modules[CLIP]
                    _authenticate_windows(original, context.relayout_parent, clip,
                        modules["src/patcher/pe_extension.py"], snapshot[LEDGER][0])
                    out = _raw_emit(layout, field_bundle.emission, lease_bundle.emission, content_bundle.emission,
                        loss_bundle.emission, loss_bundle.joined_field_emission, parent.emission,
                        content_module=content_module, assembler_module=clip, ledger_source=snapshot[LEDGER][0])
        inventory = _operand_inventory(out, content_bundle.emission, ledger_source=snapshot[LEDGER][0])
        meta = parent.metadata()
        metadata = dict(schema="clash95_battle_profile_content_replay_v1", profile=profile, resolution=resolution,
            original_sha256=BASE_SHA256, parent_candidate_sha256=_sha(context.parent),
            relayout_parent_sha256=_sha(context.relayout_parent), canonical_probe_sha256=_sha(context.canonical_probe.encode()),
            validation_stage=layout.validation_stage, source_hashes=meta["source_hashes"] |
                {name: _sha(raw) for name, (raw, _) in snapshot.items()},
            tile_replay_code_sha256=_sha(parent.emission.code), tile_replay_metadata_sha256=_sha(parent.metadata_json.encode()),
            field_loss_code_sha256=_sha(loss_bundle.emission.code),
            joined_field_code_sha256=_sha(loss_bundle.joined_field_emission.code),
            content_code_sha256=_sha(content_bundle.emission.code), content_metadata_sha256=_sha(content_bundle.metadata_json.encode()),
            field_tile_return_receipts=meta["field_tile_return_receipts"],
            lease_field_return_receipts=meta["lease_field_return_receipts"],
            field_loss_post_tile_call_patches=meta["field_loss_post_tile_call_patches"],
            code_va=out.base_va, code_bytes=len(out.code), code_sha256=_sha(out.code),
            helper_frame_bytes=HELPER_BYTES, helper_checked_interval_bytes=HELPER_BYTES + 84,
            helper_low_watermark=-44, native_body_return_offset=NATIVE_RETURN,
            native_body_sp_offset=HELPER_BYTES + 40,
            owning_family_entry_sp_offsets={family: HELPER_BYTES + 40 - delta for family, delta in BODY_SP.items()},
            emitted_native_destination_replay=True, emitted_native_scalar_tail_replay=True,
            emitted_partial_ax_replay=True, emitted_partial_bl_dl_replay=True,
            selected_native_sites=list(BODY_SITES), native_family_counts=dict(vertical=1, unit=5, adjacent=9, count=2),
            body_return_receipts=out.body_receipts,
            body_return_receipt_fields=("native_site_va", "entry_va", "payload_va", "admit_return_pc",
                "denied_va", "fault_va", "valid_va", "finish_dispatch_va", "native_resume_va"),
            source_blocks=[dict(native_va=va, parent_entry_va=entry, parent_end_va=end,
                parent_block_sha256=digest, adapter_entry_va=adapter, parent_admit_return_pc=pc)
                for va, entry, end, digest, adapter, pc in out.source_blocks],
            scalar_tail_guards={"0x42f9c3": "captured EDI is eight-aligned and unsigned below 64 before relocated 64-byte table ADD",
                "0x42f9ec": "captured EDX equals WORLD+SELF offset from captured UNIT_S-28; offset unsigned below 22*31 and divisible by31, not neighbor INDEX",
                "0x426f54": "parent admitted captured EDI exactly WORLD+852+n*31 with unsigned n<22 before native owner CMP"},
            planned_native_windows=[dict(va=va, rva=va - 0x400000,
                file_offset=clip.file_offset(original, va, len(raw)), old_bytes=raw.hex(),
                new_bytes=(b"\xe8" + struct.pack("<i", target - va - 5) + b"\x90" * (len(raw) - 5)).hex(),
                target_va=target, role=role, removed_highlow_rvas=list(removed),
                group="battle_profile_content_replay_preparation") for va, raw, target, role, removed in out.planned_hooks],
            operand_inventory=[dict(instruction_offset=r.instruction_offset, instruction_bytes=r.instruction_bytes,
                offset=r.offset, kind=r.kind, role=r.role, value=r.value) for r in inventory],
            unsafe_va=dict(out.private_entries)["unsafe_control"],
            parent_unsafe_va=dict(content_bundle.emission.private_entries)["unsafe_control"],
            failure_behavior="EDX0/2/unknown status or changed controls stops UD2; no native epilogue, descriptor loss write or continuation",
            writes_owner_state=False, writes_descriptor=False, writes_headers=False, writes_pixels=False,
            preparation_only=True, installed_hooks=[], provider_records_emitted=0,
            prefix_rx_remaining_bytes=layout.rx.va + layout.rx.size - out.base_va - len(out.code),
            limitations=[
                "Seventeen remaining content adapters are emitted in RAM only; no PE, installed hook or release lane is supplied.",
                "Full destinations and AX/BL/DL preserve their native unaffected bits before exact scalar tails; this is no native callsite-safety proof.",
                "Denial and malformed payload stop UD2. No cleanup epilogue, loss write or healthy native unwind is authorized.",
                "Count remains draw-only42F95B. Early Count reads, non-draw426F95/431D7A and WORLD+821 sentinel authority remain unadapted/unproved.",
                "The numeric helper/ancestry bounds establish no mapped/native stack capacity, genuine callback ABI or whole-chain capacity.",
                "The live Thread callback RET/ESP cannot be checked by this caller before a corrupted callback return executes.",
                "Pre-existing paired control/descriptor changes, transient writes and cross-thread mutation remain unproved.",
                "Post-normal-return gates, primitive/line successors, provider/RLE ownership/cancellation, receiver/arguments, clipping, camera/input/animation/presentation/dialog/results/quit and atomic installation remain required.",
            ], **{name: False for name in FALSE_CLAIMS})
    _unchanged(snapshot)
    return ContentReplayBundle(out, parent, inventory,
        json.dumps(metadata, sort_keys=True, separators=(",", ":"), allow_nan=False))


def _production_factory():
    from hashlib import sha256 as digest
    from pathlib import Path as SourcePath
    from types import ModuleType as SourceModule
    from uuid import uuid4 as unique_name
    from sys import modules as registry
    rejection = ValueError
    path = SourcePath(__file__).absolute()
    if path != path.parents[2] / "src/patcher/battle_profile_content_replay.py":
        raise rejection("canonical content replay producer required")
    root = path.parents[2]
    def read_source(target):
        if target != root / "src/patcher/battle_profile_content_replay.py" or target.resolve(strict=True) != target:
            raise rejection("canonical content replay source required")
        for item in (target, *target.parents):
            row = item.lstat()
            if item.is_symlink() or getattr(row, "st_file_attributes", 0) & 0x400:
                raise rejection("content replay source reparse forbidden")
        before = target.stat()
        if not 0 < before.st_size <= 2 * 1024 * 1024:
            raise rejection("bounded content replay source required")
        with target.open("rb") as stream:
            raw = stream.read(2 * 1024 * 1024 + 1)
        after = target.stat()
        stamp = lambda r: (r.st_dev, r.st_ino, r.st_size, r.st_mtime_ns, getattr(r, "st_file_attributes", 0))
        if stamp(before) != stamp(after) or len(raw) != after.st_size:
            raise rejection("content replay source changed while read")
        return raw, stamp(after)
    raw, receipt = read_source(path)
    name = "_battle_content_replay_issuer_" + unique_name().hex
    module = SourceModule(name); module.__file__ = str(path)
    module.__loaded_source_sha256__ = digest(raw).hexdigest()
    module.__canonical_content_replay_issuer__ = True
    if registry.setdefault(name, module) is not module:
        raise rejection("content replay issuer namespace occupied")
    try:
        exec(compile(raw, str(path), "exec"), module.__dict__)
        issuer = module.__dict__["_issue"]
    finally:
        replaced = registry.get(name) is not module
        if registry.get(name) is module:
            del registry[name]
        if replaced:
            raise rejection("content replay issuer namespace identity changed")
    if read_source(path) != (raw, receipt):
        raise rejection("content replay source changed during capture")
    def dispatch(original, profile, resolution):
        if read_source(path) != (raw, receipt):
            raise rejection("captured content replay source differs")
        try:
            return issuer(original, profile, resolution)
        finally:
            if read_source(path) != (raw, receipt):
                raise rejection("content replay source changed during dispatch")
    return dispatch


if not globals().get("__canonical_content_replay_issuer__", False):
    emit_content_replay = _production_factory()
