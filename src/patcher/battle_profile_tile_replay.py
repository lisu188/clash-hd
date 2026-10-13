"""Uninstalled native Tile operand replay after the fresh loss-aware chain.

Eleven complete source-owned ContentV2 blocks supply checked values. A new
native-ABI finish restores the original destination/flags and replays the exact
stolen scalar tail. Denial and faults stop at UD2; no native epilogue is borrowed.
No PE, hook, provider record, game execution or acceptance is supplied here.
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
SOURCE = "src/patcher/battle_profile_tile_replay.py"
LOSS = "src/patcher/battle_profile_field_loss.py"
LOSS_SHA256 = "3d473676828e13fc24853c3bf7f08d7e92e2a3f682bd31226e50cbf9f9258163"
CONTENT = "src/patcher/battle_profile_content_v2.py"
CONTENT_SHA256 = "681fbf96f79e9c1fa9c64ab70f27057ade97bc4a109f79562c65a383067372c6"
TEMPLATE = "src/patcher/battle_profile_content.py"
TEMPLATE_SHA256 = "52f9ac7f8d52cb40638e91868910d6487cea083be0cc32e622d8fe4a3f8cf3d7"
LEDGER = "src/patcher/battle_profile_continuation.py"
LEDGER_SHA256 = "075bd62a8311f8cc761136bca21063813dfc874ce8d8a5bcf075ebdb664d811f"
CLIP = "src/patcher/partial_tile_clip.py"
BASE_SHA256 = "500055d77d03d514e8d3168506bd10f67cd8569bcc450604ff8192f46cdaf3ae"
HELPER_BYTES = 784
NATIVE_RETURN = HELPER_BYTES + 36
TILE_SITES = (0x43026f, 0x430375, 0x4303e7, 0x430459, 0x4304b4,
              0x43055a, 0x4305da, 0x430649, 0x4306a7, 0x4302b4, 0x43050a)
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
    "downstream_frozen_continuation_compatible", "downstream_frozen_primitive_compatible",
)


def _require(value, message):
    if not value:
        raise ValueError(message)


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _read(path):
    _require(path.is_absolute() and path.is_relative_to(ROOT) and path.resolve(strict=True) == path,
             "canonical Tile replay source required")
    for item in (path, *path.parents):
        row = item.lstat()
        _require(not item.is_symlink() and not getattr(row, "st_file_attributes", 0) & 0x400,
                 "Tile replay source reparse forbidden")
    before = path.stat()
    _require(0 < before.st_size <= 2 * 1024 * 1024, "bounded Tile replay source required")
    with path.open("rb") as stream:
        raw = stream.read(2 * 1024 * 1024 + 1)
    after = path.stat()
    stamp = lambda r: (r.st_dev, r.st_ino, r.st_size, r.st_mtime_ns, getattr(r, "st_file_attributes", 0))
    _require(stamp(before) == stamp(after) and len(raw) == after.st_size,
             "Tile replay source changed while read")
    return raw, stamp(after)


@contextmanager
def _loss_module(raw):
    _require(type(raw) is bytes and _sha(raw) == LOSS_SHA256, "frozen field-loss producer differs")
    name = "_tile_replay_loss_" + uuid.uuid4().hex
    module = types.ModuleType(name)
    module.__file__ = str(ROOT / LOSS)
    module.__loaded_source_sha256__ = LOSS_SHA256
    module.__canonical_field_loss_issuer__ = True
    _require(sys.modules.setdefault(name, module) is module, "Tile replay namespace occupied")
    try:
        exec(compile(raw, module.__file__, "exec"), module.__dict__)
        yield module
    finally:
        replaced = sys.modules.get(name) is not module
        if sys.modules.get(name) is module:
            del sys.modules[name]
        _require(not replaced, "Tile replay namespace identity changed")


def _snapshot():
    loss = _read(ROOT / LOSS)
    with _loss_module(loss[0]) as producer:
        result = producer._snapshot()
    own, ledger = _read(ROOT / SOURCE), _read(ROOT / LEDGER)
    _require(result[LOSS] == loss and _sha(ledger[0]) == LEDGER_SHA256 and
             _sha(result[CONTENT][0]) == CONTENT_SHA256 and
             _sha(result[TEMPLATE][0]) == TEMPLATE_SHA256 and
             globals().get("__loaded_source_sha256__") == _sha(own[0]),
             "private unchanged Tile replay source graph required")
    return result | {SOURCE: own, LEDGER: ledger}


def _unchanged(snapshot):
    _require(all(_read(ROOT / name) == receipt for name, receipt in snapshot.items()),
             "Tile replay source graph changed")


@dataclass(frozen=True)
class Operand:
    instruction_offset: int
    instruction_bytes: int
    offset: int
    kind: str
    role: str
    value: int


@dataclass(frozen=True)
class TileReplayEmission:
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
class TileReplayBundle:
    emission: TileReplayEmission
    field_loss_bundle: object
    operand_inventory: tuple
    metadata_json: str
    hook_sites: tuple = ()
    removed_highlow_rvas: tuple = ()

    def metadata(self):
        return json.loads(self.metadata_json)


def _identity(out):
    return (out.base_va, out.state_va, out.code, out.entries, out.private_entries,
            tuple((r.offset, r.kind, r.target, r.purpose) for r in out.relocations),
            out.width, out.height, tuple(getattr(out, "body_receipts", ())),
            tuple(getattr(out, "field_call_patches", ())))


def _literal(raw, name):
    tree = ast.parse(raw)
    nodes = [n for n in tree.body if isinstance(n, ast.Assign) and
             any(isinstance(t, ast.Name) and t.id == name for t in n.targets)]
    _require(len(nodes) == 1, "one complete frozen Tile ledger field required")
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
             "complete frozen native Tile ledger inventory differs")
    result = []
    for site, (va, window_hex) in zip(sites, windows):
        if site[2] != "tile":
            continue
        operand, window = bytes.fromhex(site[1]), bytes.fromhex(window_hex)
        _require(va == site[0] and operand[:2] == b"\x0f\xbf" and len(operand) == 8 and
                 window.startswith(operand) and 10 <= len(window) <= 13,
                 "complete native Tile operand/window required")
        destination = (operand[2] >> 3) & 7
        _require(destination in (0, 7), "fixed native Tile MOVSX destination required")
        removed = tuple(h - 0x400000 for h in highlow if va <= h < va + len(window))
        result.append((site, window, destination, removed))
    _require(tuple(row[0][0] for row in result) == TILE_SITES and
             tuple(rva for row in result for rva in row[3]) == (0x30462,),
             "eleven ordered native Tile windows/one HIGHLOW required")
    return tuple(result)


def _raw_emit(layout, field, lease, content, loss, joined_field, *, content_module,
              assembler_module, ledger_source):
    """Explicit synthetic emission boundary, never production admission."""
    windows = _frozen_windows(ledger_source)
    _require(loss.base_va == (content.base_va + len(content.code) + 15) & ~15 and
             joined_field.base_va == field.base_va and
             loss.state_va == content.state_va == field.state_va == lease.state_va == layout.rw.va and
             (content.width, content.height) == (loss.width, loss.height) == (field.width, field.height),
             "complete fresh Tile replay prefix extent required")
    base = (loss.base_va + len(loss.code) + 15) & ~15
    a = assembler_module._Assembler(base)
    parent_private = dict(content.private_entries)
    _require(tuple(parent_private) == ("capture_inputs", "capture_stack", "admit_body", "fixed_receipt",
                                      "unsafe_control", "finish_rejected", "finish_valid"),
             "explicit fresh ContentV2 finish ABI required")
    receipts = content.body_receipts
    _require(len(receipts) == 28 and tuple(row[0] for row in receipts[:11]) == TILE_SITES,
             "complete source-owned Tile body receipts required")
    assembler_module.absolute_relocation_offsets(content)
    sources, hooks, bodies = [], [], []

    def transfer(target, purpose, opcode="e9"):
        a.emit(opcode)
        at = len(a.code)
        a.relocations.append(assembler_module.Relocation(at, "rel32", target, purpose))
        a.u32(target - base - at - 4)

    def internal(at, label):
        struct.pack_into("<I", a.code, at, 0)
        a.fixups.append((at, label))

    def scalar_tail(window, operand_bytes, va, removed):
        tail = window[operand_bytes:]
        _require(tail in (b"\x31\xff", b"\x83\xff\xff", b"\x39\xdf", b"\x6b\xc0\x58") or
                 len(tail) == 5 and tail[0] == 0xa1 and removed == (0x30462,),
                 "closed exact native Tile scalar tail required")
        at = len(a.code)
        a.emit(tail.hex())
        if removed:
            _require(va + operand_bytes + 1 - 0x400000 == removed[0] and tail[0] == 0xa1,
                     "complete stolen Tile HIGHLOW operand required")
            a.relocations.append(assembler_module.Relocation(at + 1, "abs32",
                struct.unpack_from("<I", tail, 1)[0], "native_tile_scalar_highlow"))

    for index, (site, window, destination, removed) in enumerate(windows):
        va = site[0]
        _, old_entry, old_payload, old_admit_return, old_denied, old_fault, old_valid = receipts[index]
        old_end = receipts[index + 1][1]
        lo, hi = old_entry - content.base_va, old_end - content.base_va
        raw = content.code[lo:hi]
        _require(0 <= lo < hi <= len(content.code) and
                 raw[:11] == b"\x9c\x60\xfc\x81\xec" + struct.pack("<I", HELPER_BYTES) + b"\x89\xe5" and
                 old_entry < old_admit_return < old_payload < old_valid < old_fault < old_denied < old_end,
                 "complete 784-byte ContentV2 Tile block receipt required")
        admit_at = old_admit_return - content.base_va - 4
        rows = [r for r in content.relocations if r.offset == admit_at]
        _require(content.code[admit_at - 1] == 0xe8 and len(rows) == 1 and
                 (rows[0].kind, rows[0].target, rows[0].purpose) ==
                 ("rel32", parent_private["admit_body"], "content_v2_internal:admit_body"),
                 "actual whole ContentV2 admission CALL required")
        start, entry = len(a.code), base + len(a.code)
        dispatch, guard = f"finish_{va:06x}", f"admit_{va:06x}"
        a.label(f"site_{va:06x}")
        a.emit(raw.hex())
        for row in content.relocations:
            if not lo <= row.offset < hi:
                continue
            _require(row.offset + 4 <= hi, "Tile block relocation crosses source boundary")
            at = start + row.offset - lo
            if row.kind == "abs32":
                a.relocations.append(assembler_module.Relocation(at, "abs32", row.target,
                    "tile_replay_source_absolute:" + row.purpose))
            elif row.offset == admit_at:
                internal(at, guard)
            elif old_entry <= row.target < old_end:
                target = entry + row.target - old_entry
                struct.pack_into("<i", a.code, at, target - base - at - 4)
                a.relocations.append(assembler_module.Relocation(at, "rel32", target,
                    "tile_replay_internal:source_block"))
            elif row.target in (parent_private["finish_rejected"], parent_private["finish_valid"]):
                _require(a.code[at - 1] == 0xe9, "outer Tile finish JMP required")
                internal(at, dispatch)
            else:
                _require(row.kind == "rel32" and row.target == parent_private["capture_inputs"] and
                         a.code[at - 1] == 0xe8, "unexpected external Tile block transfer")
                struct.pack_into("<i", a.code, at, row.target - base - at - 4)
                a.relocations.append(assembler_module.Relocation(at, "rel32", row.target,
                    "tile_replay_capture_inputs"))
        a.label(dispatch)
        # Only a valid payload reaches native instructions. The parent has
        # checked its captured input/control, but grants no failure unwind.
        a.emit("83fa01"); a.branch("0f85", "unsafe_control")
        a.emit("39ec"); a.branch("0f85", "unsafe_control")
        a.emit("8b95"); a.u32(NATIVE_RETURN)
        a.emit("81fa"); a.absolute(va + 5, "natural native Tile body CALL return")
        a.branch("0f85", "unsafe_control")
        saved_destination = HELPER_BYTES + (28 if destination == 0 else 0)
        a.emit("8985"); a.u32(saved_destination)
        a.emit("81c4"); a.u32(HELPER_BYTES)
        # POPFD precedes LEA: discarding the CALL word must not alter flags.
        a.emit("619d8d642404")
        scalar_tail(window, len(bytes.fromhex(site[1])), va, removed)
        transfer(va + len(window), "native_tile_resume")
        a.label(guard)
        # One actual adapter CALL, not a fabricated return word or supplied PC.
        a.emit("8d4c240439cd"); a.branch("0f85", "unsafe_control")
        a.emit("8b042481f8")
        a.absolute(entry + old_admit_return - old_entry, "actual Tile adapter admission CALL return")
        a.branch("0f85", "unsafe_control")
        transfer(parent_private["admit_body"], "native_tile_admission_parent")
        bodies.append((va, entry, entry + old_payload - old_entry, entry + old_admit_return - old_entry,
                       entry + old_denied - old_entry, entry + old_fault - old_entry,
                       entry + old_valid - old_entry, base + a.labels[dispatch], va + len(window)))
        sources.append((va, old_entry, old_end, _sha(raw), entry, old_admit_return))
        hooks.append((va, window, entry, "tile_operand", removed))
    a.label("unsafe_control"); a.emit("0f0b")
    code = bytes(a.finish())
    for off, label in a.fixups:
        a.relocations.append(assembler_module.Relocation(off, "rel32", base + a.labels[label],
            "tile_replay_internal:" + label))
    _require(base + len(code) <= layout.rx.va + layout.rx.size,
             "Tile replay exceeds fresh RX reservation")
    out = TileReplayEmission(base, layout.rw.va, code,
        tuple((f"site_{va:06x}", base + a.labels[f"site_{va:06x}"]) for va in TILE_SITES),
        tuple(a.relocations), field.width, field.height,
        (("unsafe_control", base + a.labels["unsafe_control"]),) +
        tuple((f"admit_{va:06x}", base + a.labels[f"admit_{va:06x}"]) for va in TILE_SITES),
        tuple(bodies), tuple(sources), tuple(hooks))
    assembler_module.absolute_relocation_offsets(out)
    _operand_inventory(out, content, ledger_source=ledger_source)
    return out


def _emit_code(layout, life, route, field, lease, content, loss, joined_field, *,
               loss_module, loss_kwargs, content_module, assembler_module, ledger_source):
    expected = loss_module._emit_code(layout, life, route, field, lease, content, **loss_kwargs)
    _require(_identity(loss) == _identity(expected), "complete canonical fresh field-loss bytes/ABI required")
    expected_join = loss_module._join_field(field, expected)
    _require(_identity(joined_field) == _identity(expected_join),
             "complete canonical two-CALL joined FieldV3 required")
    return _raw_emit(layout, field, lease, content, loss, joined_field,
        content_module=content_module, assembler_module=assembler_module, ledger_source=ledger_source)


def _decode(code):
    """Closed authored body/native-finish dialect, with typed operand fields."""
    cursor, rows = 0, []
    while cursor < len(code):
        start, fields = cursor, []
        opcode = code[cursor]; cursor += 1; memory = False
        if opcode in (0x9c, 0x9d, 0x60, 0x61, 0xfc, 0xc3, 0x55, 0x5d, 0x4b):
            pass
        elif 0xb8 <= opcode <= 0xbf or opcode == 0xa9:
            fields.append((cursor, 4, "immediate")); cursor += 4
        elif opcode == 0xa1:
            fields.append((cursor, 4, "memory_address")); cursor += 4
        elif opcode in (0xe8, 0xe9):
            fields.append((cursor, 4, "relative")); cursor += 4
        elif opcode == 0x0f:
            _require(cursor < len(code), "truncated Tile replay escape")
            sub = code[cursor]; cursor += 1
            if sub == 0x0b:
                pass
            elif 0x80 <= sub <= 0x8f:
                fields.append((cursor, 4, "relative")); cursor += 4
            else:
                _require(sub in (0xb6, 0xb7, 0xbf), "Tile replay extended load differs")
                memory = True
        else:
            _require(opcode in (0x81, 0x83, 0x8b, 0x89, 0x3b, 0x39, 0x85, 0xf7,
                                0xff, 0x31, 0x29, 0x01, 0xc1, 0x6b, 0x8d, 0xd1),
                     "unknown Tile replay opcode at " + hex(start))
            memory = True
        if memory:
            _require(cursor < len(code), "truncated Tile replay ModRM")
            modrm = code[cursor]; cursor += 1; mode, rm = modrm >> 6, modrm & 7
            if mode != 3 and rm == 4:
                _require(cursor < len(code), "truncated Tile replay SIB")
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
        _require(start < cursor <= len(code), "truncated Tile replay instruction")
        rows.append((start, cursor, tuple(fields)))
    return tuple(rows)


def _authored_contract(out, content, ledger_source):
    """Reconstruct every allowed byte/operand from complete parent receipts.

    Numeric address resemblance is never a relocation role. In particular,
    helper-size and stack displacement scalars cannot become abs32 fields.
    This closed contract does not consult the supplied relocation declarations.
    """
    windows = _frozen_windows(ledger_source)
    parent = dict(content.private_entries)
    receipts = content.body_receipts
    _require(len(receipts) == 28 and tuple(row[0] for row in receipts[:11]) == TILE_SITES,
             "complete authored Tile body receipts required")
    expected, fields, bodies, sources, hooks, entries, guards = bytearray(), {}, [], [], [], [], []
    pending = []

    def field(at, kind, target, purpose):
        _require(at not in fields, "duplicate authored Tile operand")
        fields[at] = (kind, target, purpose)

    def zero_rel(at, target, purpose):
        field(at, "rel32", target, purpose)

    for index, (site, window, destination, removed) in enumerate(windows):
        va = site[0]
        _, old_entry, old_payload, old_admit_return, old_denied, old_fault, old_valid = receipts[index]
        old_end = receipts[index + 1][1]
        lo, hi = old_entry - content.base_va, old_end - content.base_va
        raw = content.code[lo:hi]
        _require(0 <= lo < hi <= len(content.code) and
                 old_entry < old_admit_return < old_payload < old_valid < old_fault < old_denied < old_end,
                 "complete canonical Tile block boundaries required")
        start, entry = len(expected), out.base_va + len(expected)
        dispatch = entry + len(raw)
        tail = window[len(bytes.fromhex(site[1])):]
        guard = dispatch + 53 + len(tail) + 5
        admit_at = old_admit_return - content.base_va - 4
        expected.extend(raw)
        for row in content.relocations:
            if not lo <= row.offset < hi:
                continue
            _require(row.offset + 4 <= hi, "authored Tile relocation crosses source block")
            at = start + row.offset - lo
            if row.kind == "abs32":
                field(at, "abs32", row.target, "tile_replay_source_absolute:" + row.purpose)
            elif row.offset == admit_at:
                _require(row.kind == "rel32" and row.target == parent["admit_body"] and
                         row.purpose == "content_v2_internal:admit_body" and raw[row.offset - lo - 1] == 0xe8,
                         "complete authored Tile admission CALL required")
                zero_rel(at, guard, f"tile_replay_internal:admit_{va:06x}")
            elif old_entry <= row.target < old_end:
                _require(row.kind == "rel32", "authored Tile internal relative operand required")
                zero_rel(at, entry + row.target - old_entry, "tile_replay_internal:source_block")
            elif row.target in (parent["finish_rejected"], parent["finish_valid"]):
                _require(row.kind == "rel32" and raw[row.offset - lo - 1] == 0xe9,
                         "authored outer Tile finish JMP required")
                zero_rel(at, dispatch, f"tile_replay_internal:finish_{va:06x}")
            else:
                _require(row.kind == "rel32" and row.target == parent["capture_inputs"] and
                         raw[row.offset - lo - 1] == 0xe8, "authored Tile capture CALL differs")
                zero_rel(at, row.target, "tile_replay_capture_inputs")
        suffix_start = len(expected)
        suffix = bytearray(bytes.fromhex(
            "83fa010f850000000039ec0f85000000008b95") + struct.pack("<I", NATIVE_RETURN) +
            bytes.fromhex("81fa") + struct.pack("<I", va + 5) + bytes.fromhex("0f85000000008985") +
            struct.pack("<I", HELPER_BYTES + (28 if destination == 0 else 0)) +
            bytes.fromhex("81c4") + struct.pack("<I", HELPER_BYTES) + bytes.fromhex("619d8d642404"))
        _require(len(suffix) == 53, "complete native Tile finish contract required")
        suffix.extend(tail)
        suffix.extend(bytes.fromhex("e9000000008d4c240439cd0f85000000008b042481f8") +
                      struct.pack("<I", entry + old_admit_return - old_entry) +
                      bytes.fromhex("0f8500000000e900000000"))
        _require(len(suffix) == 53 + len(tail) + 5 + 32,
                 "complete native Tile guard contract required")
        expected.extend(suffix)
        for relative in (5, 13, 31):
            pending.append((suffix_start + relative, "tile_replay_internal:unsafe_control"))
        field(suffix_start + 25, "abs32", va + 5, "natural native Tile body CALL return")
        if removed:
            _require(tail[0] == 0xa1 and len(tail) == 5 and
                     removed == (0x30462,) and struct.unpack_from("<I", tail, 1)[0] == 0x512360,
                     "exact authored native Tile A1/HIGHLOW required")
            field(suffix_start + 54, "abs32", 0x512360, "native_tile_scalar_highlow")
        zero_rel(suffix_start + 54 + len(tail), va + len(window), "native_tile_resume")
        guard_start = guard - out.base_va
        for relative in (8, 23):
            pending.append((guard_start + relative, "tile_replay_internal:unsafe_control"))
        field(guard_start + 17, "abs32", entry + old_admit_return - old_entry,
              "actual Tile adapter admission CALL return")
        zero_rel(guard_start + 28, parent["admit_body"], "native_tile_admission_parent")
        bodies.append((va, entry, entry + old_payload - old_entry, entry + old_admit_return - old_entry,
                       entry + old_denied - old_entry, entry + old_fault - old_entry,
                       entry + old_valid - old_entry, dispatch, va + len(window)))
        sources.append((va, old_entry, old_end, _sha(raw), entry, old_admit_return))
        hooks.append((va, window, entry, "tile_operand", removed))
        entries.append((f"site_{va:06x}", entry))
        guards.append((f"admit_{va:06x}", guard))
    unsafe = out.base_va + len(expected)
    expected.extend(b"\x0f\x0b")
    for at, purpose in pending:
        zero_rel(at, unsafe, purpose)
    for at, (kind, target, _) in fields.items():
        struct.pack_into("<I", expected, at,
            target if kind == "abs32" else (target - out.base_va - at - 4) & 0xffffffff)
    _require(out.entries == tuple(entries) and
             out.private_entries == (("unsafe_control", unsafe),) + tuple(guards) and
             out.body_receipts == tuple(bodies) and out.source_blocks == tuple(sources) and
             out.planned_hooks == tuple(hooks), "complete authored Tile receipt/window inventory differs")
    _require(out.code == bytes(expected), "complete authored Tile source/native finish bytes differ")
    return fields


def _operand_inventory(out, content, *, ledger_source=None):
    if ledger_source is None:
        ledger_source = _read(ROOT / LEDGER)[0]
    authored = _authored_contract(out, content, ledger_source)
    rows = _decode(out.code)
    starts = {start for start, _, _ in rows}
    declared = {r.offset: r for r in out.relocations}
    _require(len(declared) == len(out.relocations), "duplicate Tile replay operand")
    _require({at: (r.kind, r.target, r.purpose) for at, r in declared.items()} == authored,
             "exact authored Tile absolute/relative operand roles differ")
    consumed, records = set(), []
    parent = dict(content.private_entries)
    resumes = {va + len(raw) for va, raw, *_ in out.planned_hooks}
    for start, end, fields in rows:
        for at, size, role in fields:
            row = declared.get(at)
            value = int.from_bytes(out.code[at:at + size], "little")
            if role == "relative":
                _require(row is not None and row.kind == "rel32", "missing Tile replay relative operand")
                value = out.base_va + at + 4 + struct.unpack_from("<i", out.code, at)[0]
                _require(value == row.target, "Tile replay relative target differs")
                if out.base_va <= value < out.base_va + len(out.code):
                    _require(value - out.base_va in starts and row.purpose.startswith("tile_replay_internal:"),
                             "Tile replay internal instruction boundary differs")
                    typed = "internal_transfer"
                else:
                    contract = {"tile_replay_capture_inputs": (0xe8, {parent["capture_inputs"]}),
                                "native_tile_admission_parent": (0xe9, {parent["admit_body"]}),
                                "native_tile_resume": (0xe9, resumes)}
                    _require(row.purpose in contract and out.code[start] == contract[row.purpose][0] and
                             value in contract[row.purpose][1], "unexpected external Tile replay transfer")
                    typed = row.purpose
                kind = "rel32"
            elif row is not None:
                _require(size == 4 and role in ("immediate", "memory_address") and
                         row.kind == "abs32" and value == row.target, "Tile replay absolute operand differs")
                kind, typed = "abs32", "authored_address"
            else:
                _require(role != "memory_address", "missing Tile replay memory relocation")
                kind, typed = "scalar" + str(size * 8), role
            if row is not None:
                consumed.add(at)
            records.append(Operand(start, end - start, at, kind, typed, value))
    _require(consumed == set(declared) and all(va - out.base_va in starts for _, va in out.entries + out.private_entries),
             "Tile replay relocation/entry boundary differs")
    return tuple(sorted(records, key=lambda row: row.offset))


def _authenticate_windows(original, relayout_parent, clip, pe, ledger_source):
    windows = _frozen_windows(ledger_source)
    for image in (original, relayout_parent):
        parsed = pe.inspect_pe(image)
        _, relocations = pe._old_relocations(image, parsed)
        actual = {parsed.image_base + rva for rva in relocations if
                  any(site[0] <= parsed.image_base + rva < site[0] + len(raw) for site, raw, _, _ in windows)}
        _require(actual == {0x430462}, "complete selected native Tile HIGHLOW inventory differs")
        for site, raw, _, _ in windows:
            at = clip.file_offset(image, site[0], len(raw))
            _require(image[at:at + len(raw)] == raw, "whole native Tile operand/scalar window differs")


def _issue(original, profile, resolution):
    _require(type(original) is bytes and _sha(original) == BASE_SHA256, "exact Tile replay original required")
    snapshot = _snapshot()
    with _loss_module(snapshot[LOSS][0]) as producer:
        parent = producer._issue(original, profile, resolution)
        content_bundle = parent.content_bundle
        lease_bundle = content_bundle.lease_bundle
        field_bundle = lease_bundle.field_bundle
        context = field_bundle.routing_bundle.lifecycle_bundle.allocation_context
        layout = context.layout
        with producer._content_module(snapshot[CONTENT][0]) as content_module:
            with content_module._modules(snapshot) as modules:
                clip = modules[CLIP]
                _authenticate_windows(original, context.relayout_parent, clip,
                    modules["src/patcher/pe_extension.py"], snapshot[LEDGER][0])
                out = _raw_emit(layout, field_bundle.emission, lease_bundle.emission, content_bundle.emission,
                    parent.emission, parent.joined_field_emission, content_module=content_module,
                    assembler_module=clip, ledger_source=snapshot[LEDGER][0])
        inventory = _operand_inventory(out, content_bundle.emission)
        metadata = dict(schema="clash95_battle_profile_tile_replay_v1", profile=profile, resolution=resolution,
            original_sha256=BASE_SHA256, parent_candidate_sha256=_sha(context.parent),
            relayout_parent_sha256=_sha(context.relayout_parent), canonical_probe_sha256=_sha(context.canonical_probe.encode()),
            validation_stage=layout.validation_stage, source_hashes=parent.metadata()["source_hashes"] |
                {name: _sha(raw) for name, (raw, _) in snapshot.items()},
            field_loss_metadata_sha256=_sha(parent.metadata_json.encode()),
            field_loss_code_sha256=_sha(parent.emission.code), joined_field_code_sha256=_sha(parent.joined_field_emission.code),
            content_code_sha256=_sha(content_bundle.emission.code), content_metadata_sha256=_sha(content_bundle.metadata_json.encode()),
            field_tile_return_receipts=content_bundle.metadata()["field_tile_return_receipts"],
            lease_field_return_receipts=content_bundle.metadata()["lease_field_return_receipts"],
            field_loss_post_tile_call_patches=parent.metadata()["field_call_patches"],
            code_va=out.base_va, code_bytes=len(out.code), code_sha256=_sha(out.code),
            helper_frame_bytes=HELPER_BYTES, helper_checked_interval_bytes=HELPER_BYTES + 84,
            helper_low_watermark=-44, native_body_return_offset=NATIVE_RETURN,
            native_body_sp_offset=HELPER_BYTES + 40, native_tile_entry_sp_offset=HELPER_BYTES + 108,
            native_tile_live_ebp_offset=HELPER_BYTES + 88, field_ebp_offset=HELPER_BYTES + 112,
            owning_lease_ebp_offset=HELPER_BYTES + 1432,
            emitted_native_movsx_replay=True, emitted_native_scalar_tail_replay=True,
            selected_native_sites=list(TILE_SITES), body_return_receipts=out.body_receipts,
            body_return_receipt_fields=("native_site_va", "entry_va", "payload_va", "admit_return_pc",
                "denied_va", "fault_va", "valid_va", "finish_dispatch_va", "native_resume_va"),
            source_blocks=[dict(native_va=va, parent_entry_va=entry, parent_end_va=end,
                parent_block_sha256=digest, adapter_entry_va=adapter, parent_admit_return_pc=pc)
                for va, entry, end, digest, adapter, pc in out.source_blocks],
            planned_native_windows=[dict(va=va, rva=va - 0x400000,
                file_offset=clip.file_offset(original, va, len(raw)), old_bytes=raw.hex(),
                new_bytes=(b"\xe8" + struct.pack("<i", target - va - 5) + b"\x90" * (len(raw) - 5)).hex(),
                target_va=target, role=role, removed_highlow_rvas=list(removed),
                group="battle_profile_tile_replay_preparation") for va, raw, target, role, removed in out.planned_hooks],
            operand_inventory=[dict(instruction_offset=r.instruction_offset, instruction_bytes=r.instruction_bytes,
                offset=r.offset, kind=r.kind, role=r.role, value=r.value) for r in inventory],
            unsafe_va=dict(out.private_entries)["unsafe_control"],
            parent_unsafe_va=dict(content_bundle.emission.private_entries)["unsafe_control"],
            failure_behavior="EDX0/2/unknown status or changed current controls stops UD2; no native epilogue or continuation",
            writes_owner_state=False, writes_descriptor=False, writes_headers=False, writes_pixels=False,
            preparation_only=True, installed_hooks=[], provider_records_emitted=0,
            prefix_rx_remaining_bytes=layout.rx.va + layout.rx.size - out.base_va - len(out.code),
            limitations=[
                "Eleven Tile value/scalar adapters are emitted in RAM only; no PE, installed hook or release lane is supplied.",
                "Denial and malformed payload stop UD2. No native early-cleanup epilogue, loss write or healthy unwind is authorized.",
                "The native helper frame/return observations do not establish native callback ABI, mapped stack capacity or installation safety.",
                "The live Thread callback RET/ESP cannot be checked by this caller before a corrupted callback return executes.",
                "Pre-existing paired control/descriptor changes, transient writes and cross-thread mutation remain unproved.",
                "Unit/Adjacent/Vertical/Count reads, Count entry/non-draw callers and post-normal-return continuation gates remain unadapted.",
                "Provider/RLE ownership and cancellation, native receiver/arguments, clipping, camera/input/animation/presentation/dialog/results/quit and full atomic installation remain required.",
            ], **{name: False for name in FALSE_CLAIMS})
    _unchanged(snapshot)
    return TileReplayBundle(out, parent, inventory, json.dumps(metadata, sort_keys=True, separators=(",", ":"), allow_nan=False))


def _production_factory():
    from hashlib import sha256 as digest
    from pathlib import Path as SourcePath
    from types import ModuleType as SourceModule
    from uuid import uuid4 as unique_name
    from sys import modules as registry
    rejection = ValueError
    path = SourcePath(__file__).absolute()
    if path != path.parents[2] / "src/patcher/battle_profile_tile_replay.py":
        raise rejection("canonical Tile replay producer required")
    root = path.parents[2]
    def read_source(target):
        if target != root / "src/patcher/battle_profile_tile_replay.py" or target.resolve(strict=True) != target:
            raise rejection("canonical Tile replay source required")
        for item in (target, *target.parents):
            row = item.lstat()
            if item.is_symlink() or getattr(row, "st_file_attributes", 0) & 0x400:
                raise rejection("Tile replay source reparse forbidden")
        before = target.stat()
        if not 0 < before.st_size <= 2 * 1024 * 1024:
            raise rejection("bounded Tile replay source required")
        with target.open("rb") as stream:
            raw = stream.read(2 * 1024 * 1024 + 1)
        after = target.stat()
        stamp = lambda r: (r.st_dev, r.st_ino, r.st_size, r.st_mtime_ns, getattr(r, "st_file_attributes", 0))
        if stamp(before) != stamp(after) or len(raw) != after.st_size:
            raise rejection("Tile replay source changed while read")
        return raw, stamp(after)
    raw, receipt = read_source(path)
    name = "_battle_tile_replay_issuer_" + unique_name().hex
    module = SourceModule(name); module.__file__ = str(path)
    module.__loaded_source_sha256__ = digest(raw).hexdigest()
    module.__canonical_tile_replay_issuer__ = True
    if registry.setdefault(name, module) is not module:
        raise rejection("Tile replay issuer namespace occupied")
    try:
        exec(compile(raw, str(path), "exec"), module.__dict__)
        issuer = module.__dict__["_issue"]
    finally:
        replaced = registry.get(name) is not module
        if registry.get(name) is module:
            del registry[name]
        if replaced:
            raise rejection("Tile replay issuer namespace identity changed")
    if read_source(path) != (raw, receipt):
        raise rejection("Tile replay source changed during capture")
    def dispatch(original, profile, resolution):
        if read_source(path) != (raw, receipt):
            raise rejection("captured Tile replay source differs")
        try:
            return issuer(original, profile, resolution)
        finally:
            if read_source(path) != (raw, receipt):
                raise rejection("Tile replay source changed during dispatch")
    return dispatch


if not globals().get("__canonical_tile_replay_issuer__", False):
    emit_tile_replay = _production_factory()
