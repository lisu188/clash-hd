"""Uninstalled draw-only Count entry, after the fresh content replay chain.

An actual Unit admission prefix and complete private ContentV2 guard are
cloned from canonical receipts. Only the Unit-type proposed native return is
changed. The admitted Count input is bounded before its first native read.
No payload prefix guess, old 640-byte helper, native cleanup or result is used.
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
SOURCE = "src/patcher/battle_profile_count_entry.py"
REPLAY = "src/patcher/battle_profile_content_replay.py"
REPLAY_SHA256 = "bafc8fd0cdd8350a85b3ca0cd0d91005d603d6db99b10359c401b50d083248f3"
TILE = "src/patcher/battle_profile_tile_replay.py"
LOSS = "src/patcher/battle_profile_field_loss.py"
CONTENT = "src/patcher/battle_profile_content_v2.py"
TEMPLATE = "src/patcher/battle_profile_content.py"
TEMPLATE_SHA256 = "52f9ac7f8d52cb40638e91868910d6487cea083be0cc32e622d8fe4a3f8cf3d7"
CLIP = "src/patcher/partial_tile_clip.py"
BASE_SHA256 = "500055d77d03d514e8d3168506bd10f67cd8569bcc450604ff8192f46cdaf3ae"
HELPER_BYTES, NATIVE_RETURN = 784, 820
NATIVE_CALL, NATIVE_RET, NATIVE_COUNT = 0x42f956, 0x42f95b, 0x426ef0
PARENT_SITE, PARENT_SITE_NUMBER = 0x42f84a, 12
COUNT_END = 0x426f75
COUNT_SHA256 = "a97ca326a029c59233d0e8881e5eed3004c8e168d24fd7248a5a78c48c65cf90"
PREFIX_RECEIPT_FIELDS = ("native_call_va", "parent_site_va", "parent_entry_va", "parent_payload_va",
    "parent_admit_return_pc", "parent_denied_va", "parent_prefix_sha256", "adapter_entry_va",
    "adapter_suffix_va", "adapter_admit_return_pc")
PRIVATE_RECEIPT_FIELDS = ("parent_start_va", "parent_end_va", "parent_sha256", "clone_start_va",
    "clone_end_va", "parent_changed_operand_offset", "clone_changed_operand_offset")
GUARD_RECEIPT_FIELDS = ("intrinsic_guard_va", "actual_admit_return_pc", "cloned_admit_va",
    "cloned_capture_inputs_va", "local_unsafe_va")
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
    "native_count_instruction_execution_verified", "native_count_parity_verified",
    "downstream_frozen_continuation_compatible", "downstream_frozen_primitive_compatible",
)


def _require(value, message):
    if not value:
        raise ValueError(message)


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _read(path):
    _require(path.is_absolute() and path.is_relative_to(ROOT) and path.resolve(strict=True) == path,
             "canonical Count entry source required")
    for item in (path, *path.parents):
        row = item.lstat()
        _require(not item.is_symlink() and not getattr(row, "st_file_attributes", 0) & 0x400,
                 "Count entry source reparse forbidden")
    before = path.stat()
    _require(0 < before.st_size <= 2 * 1024 * 1024, "bounded Count entry source required")
    with path.open("rb") as stream:
        raw = stream.read(2 * 1024 * 1024 + 1)
    after = path.stat()
    stamp = lambda r: (r.st_dev, r.st_ino, r.st_size, r.st_mtime_ns, getattr(r, "st_file_attributes", 0))
    _require(stamp(before) == stamp(after) and len(raw) == after.st_size,
             "Count entry source changed while read")
    return raw, stamp(after)


@contextmanager
def _replay_module(raw):
    _require(type(raw) is bytes and _sha(raw) == REPLAY_SHA256, "frozen content replay producer differs")
    name = "_count_entry_replay_" + uuid.uuid4().hex
    module = types.ModuleType(name)
    module.__file__ = str(ROOT / REPLAY)
    module.__loaded_source_sha256__ = REPLAY_SHA256
    module.__canonical_content_replay_issuer__ = True
    _require(sys.modules.setdefault(name, module) is module, "Count entry namespace occupied")
    try:
        exec(compile(raw, module.__file__, "exec"), module.__dict__)
        yield module
    finally:
        replaced = sys.modules.get(name) is not module
        if sys.modules.get(name) is module:
            del sys.modules[name]
        _require(not replaced, "Count entry namespace identity changed")


def _snapshot():
    replay = _read(ROOT / REPLAY)
    with _replay_module(replay[0]) as producer:
        result = producer._snapshot()
    own = _read(ROOT / SOURCE)
    _require(result[REPLAY] == replay and _sha(result[TEMPLATE][0]) == TEMPLATE_SHA256 and
             globals().get("__loaded_source_sha256__") == _sha(own[0]),
             "private unchanged Count entry source graph required")
    return result | {SOURCE: own}


def _unchanged(snapshot):
    _require(all(_read(ROOT / name) == receipt for name, receipt in snapshot.items()),
             "Count entry source graph changed")


@dataclass(frozen=True)
class Operand:
    instruction_offset: int
    instruction_bytes: int
    offset: int
    kind: str
    role: str
    value: int


@dataclass(frozen=True)
class CountEntryEmission:
    base_va: int
    state_va: int
    code: bytes
    entries: tuple
    relocations: tuple
    width: int
    height: int
    private_entries: tuple
    prefix_receipt: tuple
    private_clone_receipt: tuple
    guard_receipts: tuple
    source_blocks: tuple
    planned_hooks: tuple


@dataclass(frozen=True)
class CountEntryBundle:
    emission: CountEntryEmission
    content_replay_bundle: object
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
            tuple(getattr(out, "source_blocks", ())), tuple(getattr(out, "planned_hooks", ())),
            tuple(getattr(out, "field_call_patches", ())),
            tuple(getattr(out, "field_return_pcs", ())), tuple(getattr(out, "lease_return_pcs", ())),
            tuple(getattr(out, "field_tile_receipts", ())), tuple(getattr(out, "lease_field_receipts", ())))


def _literal(raw, name):
    nodes = [n for n in ast.parse(raw).body if isinstance(n, ast.Assign) and
             any(isinstance(t, ast.Name) and t.id == name for t in n.targets)]
    _require(len(nodes) == 1, "one complete frozen Count ledger field required")
    return ast.literal_eval(nodes[0].value)


def _native_contract(template_source):
    _require(type(template_source) is bytes and _sha(template_source) == TEMPLATE_SHA256,
             "whole frozen Count native/source ledger required")
    sites = _literal(template_source, "SITES")
    spans = _literal(template_source, "NATIVE_SPANS")
    prologues = _literal(template_source, "PROLOGUES")
    _require(type(sites) is tuple and len(sites) == 28 and
             sites[PARENT_SITE_NUMBER] == (PARENT_SITE, "0fbf8254030000", "unit", "unit_type", 0, 0) and
             spans["count"] == (NATIVE_COUNT, COUNT_END, COUNT_SHA256),
             "whole frozen Unit admission/Count span contract differs")
    rows = [row for row in prologues if row[0] == NATIVE_COUNT]
    _require(rows == [(NATIVE_COUNT, "53515256575583ec0489c7")],
             "whole frozen Count native prologue differs")
    return b"\xe8" + struct.pack("<i", NATIVE_COUNT - NATIVE_RET), bytes.fromhex(rows[0][1])


def _source_receipts(content, field, template_source):
    _native_contract(template_source)
    private = dict(content.private_entries)
    _require(tuple(private) == ("capture_inputs", "capture_stack", "admit_body", "fixed_receipt",
                               "unsafe_control", "finish_rejected", "finish_valid") and
             len(content.body_receipts) == 28, "complete fresh Count admission parent required")
    site, entry, payload, pc, denied, fault, valid = content.body_receipts[PARENT_SITE_NUMBER]
    _require(site == PARENT_SITE and entry < pc < payload < valid < fault < denied and
             dict(content.entries)["site_42f84a"] == entry, "actual Unit admission prefix receipt differs")
    lo, hi = entry - content.base_va, payload - content.base_va
    prefix = content.code[lo:hi]
    _require(0 <= lo < hi <= len(content.code) and
             prefix[:11] == b"\x9c\x60\xfc\x81\xec" + struct.pack("<I", HELPER_BYTES) + b"\x89\xe5" and
             prefix[-12:-6] == b"\x81\xf8\x01\0\0\0" and prefix[-6:-4] == b"\x0f\x85",
             "whole actual 784-byte Unit prefix required")
    calls = [r for r in content.relocations if lo <= r.offset < hi and r.kind == "rel32"]
    capture = [r for r in calls if r.target == private["capture_inputs"] and
               r.purpose == "content_v2_internal:capture_inputs" and content.code[r.offset - 1] == 0xe8]
    admission = [r for r in calls if r.offset == pc - content.base_va - 4 and
                 r.target == private["admit_body"] and r.purpose == "content_v2_internal:admit_body" and
                 content.code[r.offset - 1] == 0xe8]
    rejection = [r for r in calls if r.offset == hi - 4 and r.target == denied and
                 r.purpose == "content_v2_internal:site_42f84a.denied"]
    _require(len(capture) == len(admission) == len(rejection) == 1 and len(calls) == 3,
             "whole Unit prefix capture/admission/denial transfers required")
    private_lo, private_hi = private["capture_inputs"], content.base_va + len(content.code)
    _require(payload < private["finish_rejected"] <= private["finish_valid"] < private_lo < private_hi and
             private_lo < private["capture_stack"] < private["admit_body"] < private["fixed_receipt"] <
             private["unsafe_control"] == private_hi - 2 and content.code[-2:] == b"\x0f\x0b",
             "complete actual private ContentV2 region required")
    p_lo = private_lo - content.base_va
    replacements = [r for r in content.relocations if p_lo <= r.offset < len(content.code) and
                    (r.kind, r.target, r.purpose) ==
                    ("abs32", PARENT_SITE + 5, "fixed proposed body CALL return PC")]
    _require(len(replacements) == 1 and
             content.code[replacements[0].offset - 2:replacements[0].offset] == b"\x81\xf8" and
             struct.unpack_from("<I", content.code, replacements[0].offset)[0] == PARENT_SITE + 5,
             "one exact proposed Unit return CMP operand required")
    check = dict(field.private_entries)["check_invocation"]
    external = [r for r in content.relocations if p_lo <= r.offset < len(content.code) and
                r.kind == "rel32" and not private_lo <= r.target < private_hi]
    _require(len(external) == 1 and external[0].target == check and
             external[0].purpose == "private current V2 complete content receipt" and
             content.code[external[0].offset - 1] == 0xe8,
             "sole callback-free external field receipt CALL required")
    return dict(site=site, entry=entry, payload=payload, pc=pc, denied=denied,
        prefix_lo=lo, prefix_hi=hi, prefix=prefix, capture_offset=capture[0].offset,
        admission_offset=admission[0].offset, rejection_offset=rejection[0].offset,
        private_lo=private_lo, private_hi=private_hi, private_offset=p_lo,
        private=content.code[p_lo:], changed_offset=replacements[0].offset,
        private_entries=tuple((name, va) for name, va in content.private_entries if private_lo <= va < private_hi),
        field_check=check)


def _raw_emit(layout, field, lease, content, loss, joined_field, tile, content_replay, *,
              content_module, assembler_module, template_source):
    """Explicit synthetic boundary; the public constructor reconstructs privately."""
    source = _source_receipts(content, field, template_source)
    _require(content_replay.base_va == (tile.base_va + len(tile.code) + 15) & ~15 and
             tile.base_va == (loss.base_va + len(loss.code) + 15) & ~15 and
             loss.base_va == (content.base_va + len(content.code) + 15) & ~15 and
             joined_field.base_va == field.base_va and
             content_replay.state_va == tile.state_va == loss.state_va == content.state_va ==
             field.state_va == lease.state_va == layout.rw.va and
             (content_replay.width, content_replay.height) == (tile.width, tile.height) ==
             (content.width, content.height) == (field.width, field.height),
             "complete fresh Count entry prefix extent required")
    base = (content_replay.base_va + len(content_replay.code) + 15) & ~15
    a = assembler_module._Assembler(base)
    assembler_module.absolute_relocation_offsets(content)
    assembler_module.absolute_relocation_offsets(content_replay)

    def internal(at, label):
        struct.pack_into("<I", a.code, at, 0)
        a.fixups.append((at, label))

    def transfer(target, purpose, opcode="e9"):
        a.emit(opcode)
        at = len(a.code)
        a.relocations.append(assembler_module.Relocation(at, "rel32", target, purpose))
        a.u32(target - base - at - 4)

    def get(reg, offset):
        a.emit("8b" + f"{0x85 | reg << 3:02x}"); a.u32(offset)

    a.label("count_entry"); a.emit(source["prefix"].hex())
    for row in content.relocations:
        if not source["prefix_lo"] <= row.offset < source["prefix_hi"]:
            continue
        _require(row.offset + 4 <= source["prefix_hi"] and row.kind == "rel32",
                 "exact Unit prefix relative-only inventory required")
        at = row.offset - source["prefix_lo"]
        labels = {source["capture_offset"]: "clone.capture_inputs",
                  source["admission_offset"]: "admission_guard",
                  source["rejection_offset"]: "unsafe_control"}
        _require(row.offset in labels, "unexpected Unit prefix operand")
        internal(at, labels[row.offset])
    a.label("admitted")
    a.emit("39ec"); a.branch("0f85", "unsafe_control")
    get(2, NATIVE_RETURN)
    a.emit("81fa"); a.absolute(NATIVE_RET, "natural Count draw CALL return")
    a.branch("0f85", "unsafe_control")
    # Admission EAX=1 is not Count's input. The original input is a saved DWORD.
    get(0, 428); get(7, 372)
    a.emit("29f881c0"); a.u32(-852)
    a.emit("81f8"); a.u32(22 * 31); a.branch("0f83", "unsafe_control")
    a.emit("31d2b91f000000f7f185d2"); a.branch("0f85", "unsafe_control")
    get(6, 428)
    a.emit("0fb746048b8f"); a.u32(804)
    a.emit("39c8"); a.branch("0f83", "unsafe_control")
    a.emit("0fb756068b8f"); a.u32(800)
    a.emit("39ca"); a.branch("0f83", "unsafe_control")
    # Keep the authentic native return word. POPAD restores Count's original
    # EAX/EDX/other inputs; neither value/status finish nor LEA ESP,+4 is used.
    a.emit("81c4"); a.u32(HELPER_BYTES); a.emit("619d")
    transfer(NATIVE_COUNT, "native_count_entry")
    a.label("admission_guard")
    a.emit("8d4c240439cd"); a.branch("0f85", "unsafe_control")
    a.emit("8b042481f8")
    a.absolute(base + source["pc"] - source["entry"], "actual Count adapter admission CALL return")
    a.branch("0f85", "unsafe_control")
    a.branch("e9", "clone.admit_body")
    a.label("unsafe_control"); a.emit("0f0b")
    clone = base + len(a.code)
    private_start = len(a.code)
    a.emit(source["private"].hex())
    for name, va in source["private_entries"]:
        a.labels["clone." + name] = private_start + va - source["private_lo"]
    for row in content.relocations:
        if not source["private_offset"] <= row.offset < len(content.code):
            continue
        _require(row.offset + 4 <= len(content.code), "private Count relocation crosses complete region")
        at = private_start + row.offset - source["private_offset"]
        if row.kind == "abs32":
            target = NATIVE_RET if row.offset == source["changed_offset"] else row.target
            purpose = "count_entry_private_native_return" if row.offset == source["changed_offset"] else (
                "count_entry_private_absolute:" + row.purpose)
            struct.pack_into("<I", a.code, at, target)
            a.relocations.append(assembler_module.Relocation(at, "abs32", target, purpose))
        else:
            _require(row.kind == "rel32", "private Count typed relative operand required")
            if source["private_lo"] <= row.target < source["private_hi"]:
                target, purpose = clone + row.target - source["private_lo"], "count_entry_internal:private"
            else:
                _require(row.target == source["field_check"] and a.code[at - 1] == 0xe8 and
                         row.purpose == "private current V2 complete content receipt",
                         "private Count external receipt differs")
                target, purpose = row.target, "count_entry_field_receipt"
            struct.pack_into("<i", a.code, at, target - base - at - 4)
            a.relocations.append(assembler_module.Relocation(at, "rel32", target, purpose))
    code = bytes(a.finish())
    for off, label in a.fixups:
        a.relocations.append(assembler_module.Relocation(off, "rel32", base + a.labels[label],
            "count_entry_internal:" + label))
    _require(base + len(code) <= layout.rx.va + layout.rx.size, "Count entry exceeds fresh RX reservation")
    old_call, _ = _native_contract(template_source)
    changed = private_start + source["changed_offset"] - source["private_offset"]
    prefix_receipt = (NATIVE_CALL, PARENT_SITE, source["entry"], source["payload"], source["pc"],
        source["denied"], _sha(source["prefix"]), base, base + a.labels["admitted"], base + source["pc"] - source["entry"])
    private_receipt = (source["private_lo"], source["private_hi"], _sha(source["private"]),
        clone, base + len(code), source["changed_offset"], changed)
    guard = (base + a.labels["admission_guard"], prefix_receipt[-1],
        base + a.labels["clone.admit_body"], clone, base + a.labels["unsafe_control"])
    private_entries = tuple((name if name != "unsafe_control" else "private_unsafe_control",
                            base + a.labels["clone." + name]) for name, _ in source["private_entries"])
    out = CountEntryEmission(base, layout.rw.va, code, (("count_entry", base),), tuple(a.relocations),
        field.width, field.height, private_entries + (("admission_guard", guard[0]), ("unsafe_control", guard[-1])),
        prefix_receipt, private_receipt, guard,
        (("unit_admission_prefix", source["entry"], source["payload"], _sha(source["prefix"]), base,
          base + a.labels["admitted"]),
         ("private_admission", source["private_lo"], source["private_hi"], _sha(source["private"]), clone, base + len(code))),
        ((NATIVE_CALL, old_call, base, "count_entry", ()),))
    assembler_module.absolute_relocation_offsets(out)
    _operand_inventory(out, content, field, template_source=template_source)
    return out


def _emit_code(layout, life, route, field, lease, content, loss, joined_field, tile, content_replay, *,
               content_replay_module, content_replay_kwargs, content_module, assembler_module, template_source):
    expected = content_replay_module._emit_code(layout, life, route, field, lease, content, loss, joined_field, tile,
                                                **content_replay_kwargs)
    _require(_identity(content_replay) == _identity(expected),
             "complete canonical content replay bytes/source blocks/windows/receipts required")
    return _raw_emit(layout, field, lease, content, loss, joined_field, tile, content_replay,
        content_module=content_module, assembler_module=assembler_module, template_source=template_source)


def _decode(code):
    """Closed private ContentV2/Count-suffix dialect with typed scalar fields."""
    cursor, rows = 0, []
    while cursor < len(code):
        start, fields = cursor, []
        opcode = code[cursor]; cursor += 1; memory = False
        if opcode in (0x9c, 0x9d, 0x60, 0x61, 0xfc, 0xc3, 0x55, 0x5d, 0x4b):
            pass
        elif opcode == 0xf3:
            _require(cursor < len(code) and code[cursor] == 0xaf, "Count private REP dialect differs")
            cursor += 1
        elif 0xb8 <= opcode <= 0xbf or opcode == 0xa9:
            fields.append((cursor, 4, "immediate")); cursor += 4
        elif opcode in (0xe8, 0xe9):
            fields.append((cursor, 4, "relative")); cursor += 4
        elif opcode == 0x0f:
            _require(cursor < len(code), "truncated Count escape")
            sub = code[cursor]; cursor += 1
            if sub == 0x0b:
                pass
            elif 0x80 <= sub <= 0x8f:
                fields.append((cursor, 4, "relative")); cursor += 4
            else:
                _require(sub in (0xb6, 0xb7, 0xbf), "Count extended load differs")
                memory = True
        else:
            _require(opcode in (0x81, 0x83, 0x8b, 0x89, 0x3b, 0x39, 0x85, 0xf7,
                                0xff, 0x31, 0x29, 0x01, 0xc1, 0x6b, 0x8d, 0xd1),
                     "unknown Count entry opcode at " + hex(start))
            memory = True
        if memory:
            _require(cursor < len(code), "truncated Count ModRM")
            modrm = code[cursor]; cursor += 1; mode, rm = modrm >> 6, modrm & 7
            if mode != 3 and rm == 4:
                _require(cursor < len(code), "truncated Count SIB")
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
        _require(start < cursor <= len(code), "truncated Count entry instruction")
        rows.append((start, cursor, tuple(fields)))
    return tuple(rows)


def _authored_contract(out, content, field_emission, template_source):
    """Independently reconstruct the exact clone and authorized substitution.

    Operand declarations in ``out`` cannot select new roles. Every private
    byte, prefix receipt, source mapping and native transfer is reconstructed.
    """
    source = _source_receipts(content, field_emission, template_source)
    expected, fields, pending = bytearray(source["prefix"]), {}, []

    def field(at, kind, target, purpose):
        _require(at not in fields, "duplicate authored Count operand")
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

    suffix = out.base_va + len(expected)
    emit("39ec"); unsafe("0f85")
    emit("8b95"); u32(820)
    emit("81fa"); absolute(NATIVE_RET, "natural Count draw CALL return")
    unsafe("0f85")
    emit("8b85"); u32(428)
    emit("8bbd"); u32(372)
    emit("29f881c0"); u32(-852)
    emit("81f8"); u32(682); unsafe("0f83")
    emit("31d2b91f000000f7f185d2"); unsafe("0f85")
    emit("8bb5"); u32(428)
    emit("0fb746048b8f"); u32(804)
    emit("39c8"); unsafe("0f83")
    emit("0fb756068b8f"); u32(800)
    emit("39ca"); unsafe("0f83")
    emit("81c4"); u32(784); emit("619de9"); relative(NATIVE_COUNT, "native_count_entry")
    guard = out.base_va + len(expected)
    emit("8d4c240439cd"); unsafe("0f85")
    emit("8b042481f8")
    actual_pc = out.base_va + source["pc"] - source["entry"]
    absolute(actual_pc, "actual Count adapter admission CALL return")
    unsafe("0f85")
    emit("e9"); guard_target = len(expected); u32(0)
    terminal = out.base_va + len(expected)
    emit("0f0b")
    clone = out.base_va + len(expected)
    private_start = len(expected)
    expected.extend(source["private"])
    for row in content.relocations:
        if source["prefix_lo"] <= row.offset < source["prefix_hi"]:
            _require(row.offset + 4 <= source["prefix_hi"] and row.kind == "rel32",
                     "whole authored Unit prefix relative inventory required")
            at = row.offset - source["prefix_lo"]
            if row.offset == source["capture_offset"]:
                target, purpose = clone, "count_entry_internal:clone.capture_inputs"
            elif row.offset == source["admission_offset"]:
                target, purpose = guard, "count_entry_internal:admission_guard"
            else:
                _require(row.offset == source["rejection_offset"], "unknown authored prefix operand")
                target, purpose = terminal, "count_entry_internal:unsafe_control"
            field(at, "rel32", target, purpose)
        elif source["private_offset"] <= row.offset < len(content.code):
            _require(row.offset + 4 <= len(content.code), "whole authored private operand required")
            at = private_start + row.offset - source["private_offset"]
            if row.kind == "abs32":
                target = NATIVE_RET if row.offset == source["changed_offset"] else row.target
                purpose = "count_entry_private_native_return" if row.offset == source["changed_offset"] else (
                    "count_entry_private_absolute:" + row.purpose)
                field(at, "abs32", target, purpose)
            else:
                _require(row.kind == "rel32", "authored private Count relative required")
                if source["private_lo"] <= row.target < source["private_hi"]:
                    target, purpose = clone + row.target - source["private_lo"], "count_entry_internal:private"
                else:
                    _require(row.target == source["field_check"] and
                             row.purpose == "private current V2 complete content receipt" and
                             content.code[row.offset - 1] == 0xe8,
                             "authored sole Count external field CALL differs")
                    target, purpose = row.target, "count_entry_field_receipt"
                field(at, "rel32", target, purpose)
    cloned_entries = tuple((name if name != "unsafe_control" else "private_unsafe_control",
                           clone + va - source["private_lo"]) for name, va in source["private_entries"])
    cloned_admit = clone + dict(source["private_entries"])["admit_body"] - source["private_lo"]
    field(guard_target, "rel32", cloned_admit, "count_entry_internal:clone.admit_body")
    for at in pending:
        field(at, "rel32", terminal, "count_entry_internal:unsafe_control")
    for at, (kind, target, _) in fields.items():
        struct.pack_into("<I", expected, at,
            target if kind == "abs32" else (target - out.base_va - at - 4) & 0xffffffff)
    changed = private_start + source["changed_offset"] - source["private_offset"]
    old_call, _ = _native_contract(template_source)
    prefix_receipt = (NATIVE_CALL, PARENT_SITE, source["entry"], source["payload"], source["pc"],
        source["denied"], _sha(source["prefix"]), out.base_va, suffix, actual_pc)
    private_receipt = (source["private_lo"], source["private_hi"], _sha(source["private"]),
        clone, out.base_va + len(expected), source["changed_offset"], changed)
    blocks = (("unit_admission_prefix", source["entry"], source["payload"], _sha(source["prefix"]), out.base_va, suffix),
              ("private_admission", source["private_lo"], source["private_hi"], _sha(source["private"]), clone,
               out.base_va + len(expected)))
    _require(out.entries == (("count_entry", out.base_va),) and
             out.private_entries == cloned_entries + (("admission_guard", guard), ("unsafe_control", terminal)) and
             out.prefix_receipt == prefix_receipt and out.private_clone_receipt == private_receipt and
             out.guard_receipts == (guard, actual_pc, cloned_admit, clone, terminal) and out.source_blocks == blocks and
             out.planned_hooks == ((NATIVE_CALL, old_call, out.base_va, "count_entry", ()),),
             "complete authored Count prefix/private/window receipts differ")
    _require(out.code == bytes(expected), "complete authored Count prefix/private/suffix bytes differ")
    return fields


def _operand_inventory(out, content, field, *, template_source=None):
    if template_source is None:
        template_source = _read(ROOT / TEMPLATE)[0]
    authored = _authored_contract(out, content, field, template_source)
    rows = _decode(out.code)
    starts = {start for start, _, _ in rows}
    declared = {r.offset: r for r in out.relocations}
    _require(len(declared) == len(out.relocations), "duplicate Count entry operand")
    _require({at: (r.kind, r.target, r.purpose) for at, r in declared.items()} == authored,
             "exact authored Count absolute/relative operand roles differ")
    consumed, records = set(), []
    field_check = dict(field.private_entries)["check_invocation"]
    for start, end, fields in rows:
        for at, size, role in fields:
            row = declared.get(at)
            value = int.from_bytes(out.code[at:at + size], "little")
            if role == "relative":
                _require(row is not None and row.kind == "rel32", "missing Count entry relative operand")
                value = out.base_va + at + 4 + struct.unpack_from("<i", out.code, at)[0]
                _require(value == row.target, "Count relative target differs")
                if out.base_va <= value < out.base_va + len(out.code):
                    _require(value - out.base_va in starts and row.purpose.startswith("count_entry_internal:"),
                             "Count internal target/instruction boundary differs")
                    typed = "internal_transfer"
                else:
                    allowed = {"count_entry_field_receipt": (0xe8, field_check),
                               "native_count_entry": (0xe9, NATIVE_COUNT)}
                    _require(row.purpose in allowed and (out.code[start], value) == allowed[row.purpose],
                             "Count external CALL/JMP differs")
                    typed = row.purpose
                kind = "rel32"
            elif row is not None:
                _require(size == 4 and role in ("immediate", "memory_address") and
                         row.kind == "abs32" and value == row.target, "Count explicit absolute operand differs")
                kind, typed = "abs32", "authored_address"
            else:
                _require(role != "memory_address", "missing Count memory relocation")
                kind, typed = "scalar" + str(size * 8), role
            if row is not None:
                consumed.add(at)
            records.append(Operand(start, end - start, at, kind, typed, value))
    _require(consumed == set(declared) and all(va - out.base_va in starts for _, va in out.entries + out.private_entries),
             "Count relocation/entry boundary differs")
    return tuple(sorted(records, key=lambda row: row.offset))


def _authenticate_native(original, relayout_parent, clip, *, template_source=None):
    if template_source is None:
        template_source = _read(ROOT / TEMPLATE)[0]
    old_call, prologue = _native_contract(template_source)
    for image in (original, relayout_parent):
        at = clip.file_offset(image, NATIVE_CALL, len(old_call))
        _require(image[at:at + len(old_call)] == old_call, "whole native Count draw CALL differs")
        at = clip.file_offset(image, NATIVE_COUNT, COUNT_END - NATIVE_COUNT)
        span = image[at:at + COUNT_END - NATIVE_COUNT]
        _require(len(span) == COUNT_END - NATIVE_COUNT and _sha(span) == COUNT_SHA256 and span.startswith(prologue),
                 "whole native Count span/prologue differs")


def _issue(original, profile, resolution):
    _require(type(original) is bytes and _sha(original) == BASE_SHA256, "exact Count entry original required")
    snapshot = _snapshot()
    with _replay_module(snapshot[REPLAY][0]) as producer:
        parent = producer._issue(original, profile, resolution)
        tile_bundle = parent.tile_replay_bundle
        loss_bundle = tile_bundle.field_loss_bundle
        content_bundle = loss_bundle.content_bundle
        lease_bundle = content_bundle.lease_bundle
        field_bundle = lease_bundle.field_bundle
        context = field_bundle.routing_bundle.lifecycle_bundle.allocation_context
        layout = context.layout
        with producer._tile_module(snapshot[TILE][0]) as tile_module:
            with tile_module._loss_module(snapshot[LOSS][0]) as loss_module:
                with loss_module._content_module(snapshot[CONTENT][0]) as content_module:
                    with content_module._modules(snapshot) as modules:
                        clip = modules[CLIP]
                        _authenticate_native(original, context.relayout_parent, clip, template_source=snapshot[TEMPLATE][0])
                        out = _raw_emit(layout, field_bundle.emission, lease_bundle.emission, content_bundle.emission,
                            loss_bundle.emission, loss_bundle.joined_field_emission, tile_bundle.emission, parent.emission,
                            content_module=content_module, assembler_module=clip, template_source=snapshot[TEMPLATE][0])
        inventory = _operand_inventory(out, content_bundle.emission, field_bundle.emission,
                                       template_source=snapshot[TEMPLATE][0])
        meta = parent.metadata()
        metadata = dict(schema="clash95_battle_profile_count_entry_v1", profile=profile, resolution=resolution,
            original_sha256=BASE_SHA256, parent_candidate_sha256=_sha(context.parent),
            relayout_parent_sha256=_sha(context.relayout_parent), canonical_probe_sha256=_sha(context.canonical_probe.encode()),
            validation_stage=layout.validation_stage, source_hashes=meta["source_hashes"] |
                {name: _sha(raw) for name, (raw, _) in snapshot.items()},
            content_replay_code_sha256=_sha(parent.emission.code),
            content_replay_metadata_sha256=_sha(parent.metadata_json.encode()),
            tile_replay_code_sha256=_sha(tile_bundle.emission.code), field_loss_code_sha256=_sha(loss_bundle.emission.code),
            joined_field_code_sha256=_sha(loss_bundle.joined_field_emission.code),
            content_code_sha256=_sha(content_bundle.emission.code),
            field_tile_return_receipts=meta["field_tile_return_receipts"],
            lease_field_return_receipts=meta["lease_field_return_receipts"],
            field_loss_post_tile_call_patches=meta["field_loss_post_tile_call_patches"],
            code_va=out.base_va, code_bytes=len(out.code), code_sha256=_sha(out.code),
            helper_frame_bytes=HELPER_BYTES, helper_checked_interval_bytes=868, helper_low_watermark=-44,
            native_body_return_offset=NATIVE_RETURN, native_body_sp_offset=824,
            native_unit_entry_sp_offset=888, native_unit_live_ebp_offset=876,
            count_entry_emitted=True, draw_only_native_return_pc=NATIVE_RET,
            parent_site=PARENT_SITE, parent_site_number=PARENT_SITE_NUMBER, parent_family="unit",
            prefix_receipt=out.prefix_receipt, prefix_receipt_fields=PREFIX_RECEIPT_FIELDS,
            private_clone_receipt=out.private_clone_receipt, private_clone_receipt_fields=PRIVATE_RECEIPT_FIELDS,
            guard_receipts=out.guard_receipts, guard_receipt_fields=GUARD_RECEIPT_FIELDS,
            source_blocks=[dict(role=role, parent_start_va=lo, parent_end_va=hi, parent_sha256=digest,
                clone_start_va=start, clone_end_va=end) for role, lo, hi, digest, start, end in out.source_blocks],
            private_native_return_change=dict(parent_operand_offset=out.private_clone_receipt[-2],
                clone_operand_offset=out.private_clone_receipt[-1], old_value=PARENT_SITE + 5, new_value=NATIVE_RET,
                instruction="CMP EAX, imm32", role="fixed proposed body CALL return PC"),
            input_record_policy="captured EAX428 equals WORLD372+852+31*n, unsigned n<22; uint16+4/+6 below current columns/rows",
            native_span=dict(start_va=NATIVE_COUNT, end_va=COUNT_END, sha256=COUNT_SHA256),
            planned_native_windows=[dict(va=va, rva=va - 0x400000,
                file_offset=clip.file_offset(original, va, len(raw)), old_bytes=raw.hex(),
                new_bytes=(b"\xe8" + struct.pack("<i", target - va - 5)).hex(),
                target_va=target, role=role, removed_highlow_rvas=list(removed),
                group="battle_profile_count_entry_preparation") for va, raw, target, role, removed in out.planned_hooks],
            operand_inventory=[dict(instruction_offset=r.instruction_offset, instruction_bytes=r.instruction_bytes,
                offset=r.offset, kind=r.kind, role=r.role, value=r.value) for r in inventory],
            unsafe_va=dict(out.private_entries)["unsafe_control"],
            private_unsafe_va=dict(out.private_entries)["private_unsafe_control"],
            failure_behavior="any rejected admission, invalid record/coordinate or unknown control stops UD2; no native cleanup or fake Count result",
            writes_owner_state=False, writes_descriptor=False, writes_headers=False, writes_pixels=False,
            preparation_only=True, installed_hooks=[], provider_records_emitted=0,
            prefix_rx_remaining_bytes=layout.rx.va + layout.rx.size - out.base_va - len(out.code),
            limitations=[
                "The Count entry adapter and complete private admission clone are emitted in RAM only; no candidate, hook or release lane is installed.",
                "Only original draw CALL42F956 with natural RET42F95B is admitted;426F95/431D7A and WORLD+821 sentinel authority remain excluded.",
                "Numeric record membership/coordinates precede Count entry, but genuine Count instructions and native receiver/argument/lifetime validity are not verified.",
                "All modeled registers/flags and the authentic native CALL word are preserved; no healthy native unwind or cleanup is supplied on rejection.",
                "The numeric 784-byte frame and868-byte checked interval supply no mapped/native or whole-chain stack capacity proof.",
                "The live Thread callback RET/ESP cannot be checked by this caller before a corrupted callback return executes.",
                "Pre-existing paired control/descriptor changes, transient writes and cross-thread mutation remain unproved.",
                "Post-normal-return gates, primitive/line successors, provider/RLE ownership/cancellation, receiver/arguments, clipping, camera/input/animation/presentation/dialog/results/quit and atomic installation remain required.",
            ], **{name: False for name in FALSE_CLAIMS})
    _unchanged(snapshot)
    return CountEntryBundle(out, parent, inventory,
        json.dumps(metadata, sort_keys=True, separators=(",", ":"), allow_nan=False))


def _production_factory():
    from hashlib import sha256 as digest
    from pathlib import Path as SourcePath
    from types import ModuleType as SourceModule
    from uuid import uuid4 as unique_name
    from sys import modules as registry
    rejection = ValueError
    path = SourcePath(__file__).absolute()
    if path != path.parents[2] / "src/patcher/battle_profile_count_entry.py":
        raise rejection("canonical Count entry producer required")
    root = path.parents[2]
    def read_source(target):
        if target != root / "src/patcher/battle_profile_count_entry.py" or target.resolve(strict=True) != target:
            raise rejection("canonical Count entry source required")
        for item in (target, *target.parents):
            row = item.lstat()
            if item.is_symlink() or getattr(row, "st_file_attributes", 0) & 0x400:
                raise rejection("Count entry source reparse forbidden")
        before = target.stat()
        if not 0 < before.st_size <= 2 * 1024 * 1024:
            raise rejection("bounded Count entry source required")
        with target.open("rb") as stream:
            raw = stream.read(2 * 1024 * 1024 + 1)
        after = target.stat()
        stamp = lambda r: (r.st_dev, r.st_ino, r.st_size, r.st_mtime_ns, getattr(r, "st_file_attributes", 0))
        if stamp(before) != stamp(after) or len(raw) != after.st_size:
            raise rejection("Count entry source changed while read")
        return raw, stamp(after)
    raw, receipt = read_source(path)
    name = "_battle_count_entry_issuer_" + unique_name().hex
    module = SourceModule(name); module.__file__ = str(path)
    module.__loaded_source_sha256__ = digest(raw).hexdigest()
    module.__canonical_count_entry_issuer__ = True
    if registry.setdefault(name, module) is not module:
        raise rejection("Count entry issuer namespace occupied")
    try:
        exec(compile(raw, str(path), "exec"), module.__dict__)
        issuer = module.__dict__["_issue"]
    finally:
        replaced = registry.get(name) is not module
        if registry.get(name) is module:
            del registry[name]
        if replaced:
            raise rejection("Count entry issuer namespace identity changed")
    if read_source(path) != (raw, receipt):
        raise rejection("Count entry source changed during capture")
    def dispatch(original, profile, resolution):
        if read_source(path) != (raw, receipt):
            raise rejection("captured Count entry source differs")
        try:
            return issuer(original, profile, resolution)
        finally:
            if read_source(path) != (raw, receipt):
                raise rejection("Count entry source changed during dispatch")
    return dispatch


if not globals().get("__canonical_count_entry_issuer__", False):
    emit_count_entry = _production_factory()
