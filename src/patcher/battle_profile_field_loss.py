"""Uninstalled loss-aware join for the fresh field/lease/content chain.

Only the two post-Tile receipt CALLs are replaced in an in-memory emission.
No native hook, candidate, provider authority, installation or runtime proof is
produced. Frozen predecessors, including their documented loss gap, are intact.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, replace
import hashlib
import json
from pathlib import Path
import struct
import sys
import types
import uuid

ROOT = Path(__file__).resolve().parents[2]
SOURCE = "src/patcher/battle_profile_field_loss.py"
CONTENT = "src/patcher/battle_profile_content_v2.py"
CONTENT_SHA256 = "681fbf96f79e9c1fa9c64ab70f27057ade97bc4a109f79562c65a383067372c6"
FIELD = "src/patcher/battle_profile_field_v3.py"
LEASE = "src/patcher/battle_profile_stack_lease_v2.py"
CLIP = "src/patcher/partial_tile_clip.py"
BASE_SHA256 = "500055d77d03d514e8d3168506bd10f67cd8569bcc450604ff8192f46cdaf3ae"
HELPER_BYTES, FIELD_BYTES, LEASE_BYTES = 512, 1280, 192
FIELD_EBP, LEASE_EBP, ROOT_ESP, MODE, RESULT = 204, 208, 212, 216, 224
CONTROL_SLOTS = (FIELD_EBP, LEASE_EBP, ROOT_ESP, MODE) + tuple(range(512, 552, 4))
CONTROL_SHADOW = 316
FALSE_CLAIMS = (
    "installed", "battle_installed", "expanded_battle_installed", "installation_ready",
    "source_candidate_installed", "native_executed", "game_executed", "runtime_executed",
    "runtime_verified", "manual_input_proof", "promotion_ready", "release_accepted",
    "next_Tile_cancellation", "native_cancellation_verified", "intraTile_cancellation_verified",
    "native_provider_rle_verified", "provider_capacity_verified", "provider_lifetime_verified",
    "native_callback_abi_verified", "native_stack_capacity_verified", "whole_chain_capacity_verified",
    "healthy_return_verified", "healthy_native_unwind_verified", "atomic_installation_verified",
    "native_continuation_cancellation", "standalone_native_callsite_replacement_safe",
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
             "canonical field loss source required")
    for item in (path, *path.parents):
        row = item.lstat()
        _require(not item.is_symlink() and not getattr(row, "st_file_attributes", 0) & 0x400,
                 "field loss source reparse forbidden")
    before = path.stat()
    _require(0 < before.st_size <= 2 * 1024 * 1024, "bounded field loss source required")
    with path.open("rb") as stream:
        raw = stream.read(2 * 1024 * 1024 + 1)
    after = path.stat()
    stamp = lambda r: (r.st_dev, r.st_ino, r.st_size, r.st_mtime_ns, getattr(r, "st_file_attributes", 0))
    _require(stamp(before) == stamp(after) and len(raw) == after.st_size,
             "field loss source changed while read")
    return raw, stamp(after)


@contextmanager
def _content_module(raw):
    _require(type(raw) is bytes and _sha(raw) == CONTENT_SHA256, "frozen ContentV2 source differs")
    name = "_field_loss_content_" + uuid.uuid4().hex
    module = types.ModuleType(name)
    module.__file__ = str(ROOT / CONTENT)
    module.__loaded_source_sha256__ = CONTENT_SHA256
    module.__canonical_content_v2_issuer__ = True
    _require(sys.modules.setdefault(name, module) is module, "field loss namespace occupied")
    try:
        exec(compile(raw, module.__file__, "exec"), module.__dict__)
        yield module
    finally:
        replaced = sys.modules.get(name) is not module
        if sys.modules.get(name) is module:
            del sys.modules[name]
        _require(not replaced, "field loss namespace identity changed")


def _snapshot():
    content = _read(ROOT / CONTENT)
    with _content_module(content[0]) as module:
        result = module._snapshot()
    own = _read(ROOT / SOURCE)
    _require(result[CONTENT] == content and
             globals().get("__loaded_source_sha256__") == _sha(own[0]),
             "private unchanged field loss issuer required")
    return result | {SOURCE: own}


def _unchanged(snapshot):
    _require(all(_read(ROOT / name) == receipt for name, receipt in snapshot.items()),
             "field loss source graph changed")


@dataclass(frozen=True)
class FieldLossEmission:
    base_va: int
    state_va: int
    code: bytes
    entries: tuple
    relocations: tuple
    width: int
    height: int
    private_entries: tuple
    field_call_patches: tuple


@dataclass(frozen=True)
class FieldLossBundle:
    emission: FieldLossEmission
    joined_field_emission: object
    content_bundle: object
    metadata_json: str
    hook_sites: tuple = ()
    removed_highlow_rvas: tuple = ()

    def metadata(self):
        return json.loads(self.metadata_json)


def _identity(out):
    return (out.base_va, out.state_va, out.code, out.entries, out.private_entries,
            tuple((r.offset, r.kind, r.target, r.purpose) for r in out.relocations),
            out.width, out.height, tuple(getattr(out, "body_receipts", ())))


def _post_calls(field, field_module):
    result = []
    for mode, pc, at, target in field_module._tile_receipts(field):
        _require(field.code[at:at+1] == b"\xe8" and target == dict(field.private_entries)["same_invocation"],
                 "actual post-Tile receipt CALL required")
        rows = [r for r in field.relocations if r.offset == at + 1]
        _require(len(rows) == 1 and rows[0].kind == "rel32" and rows[0].target == target and
                 pc + 5 + struct.unpack_from("<i", field.code, at + 1)[0] == target,
                 "complete post-Tile CALL operand required")
        result.append((mode, pc, field.code[at:at+5]))
    _require(tuple(row[0] for row in result) == (0, 1), "two ordered post-Tile CALLs required")
    return tuple(result)


def _raw_emit(layout, field, lease, content, *, content_module, lease_module, field_module, assembler_module):
    """Explicit synthetic composition boundary, never public admission authority."""
    _, _, _, returns, _ = content_module._parent_receipts(layout, field, lease, field_module, lease_module)
    _require(content.base_va == (lease.base_va + len(lease.code) + 15) & ~15 and
             content.state_va == field.state_va == layout.rw.va and
             (content.width, content.height) == (field.width, field.height) and
             content.base_va + len(content.code) < layout.rx.va + layout.rx.size,
             "complete fresh content prefix required")
    post_calls = _post_calls(field, field_module)
    base = (content.base_va + len(content.code) + 15) & ~15
    state = layout.rw.va
    a = assembler_module._Assembler(base)

    def imm(reg, value):
        a.emit(f"{0xb8+reg:02x}"); a.u32(value)

    def mem(op, reg, bas, off):
        a.emit(op + f"{0x80 | (reg << 3) | bas:02x}")
        if bas == 4:
            a.emit("24")
        a.u32(off)

    def get(reg, off): mem("8b", reg, 5, off)
    def put(reg, off): mem("89", reg, 5, off)
    def load(reg, bas, off): mem("8b", reg, bas, off)
    def match(reg, off): mem("3b", reg, 5, off)
    def add(reg, value): a.emit(f"81{0xc0+reg:02x}"); a.u32(value)
    def cmp(reg, value): a.emit(f"81{0xf8+reg:02x}"); a.u32(value)
    def ne(label): a.branch("0f85", label)
    def eq(label): a.branch("0f84", label)

    def address_cmp(reg, value, purpose):
        a.emit(f"81{0xf8+reg:02x}"); a.absolute(value, purpose)

    def read(reg, va, purpose):
        a.emit("8b" + f"{5 | (reg << 3):02x}"); a.absolute(va, purpose)

    def call(target, purpose):
        a.emit("e8"); at = len(a.code)
        a.relocations.append(assembler_module.Relocation(at, "rel32", target, purpose))
        a.u32(target - base - at - 4)

    def extent(reg, count):
        a.emit(f"f7{0xc0+reg:02x}03000000"); ne("unsafe_control")
        get(2, ROOT_ESP); a.emit("89d1"); add(1, -65536)
        a.emit(f"39{0xc8+reg:02x}"); a.branch("0f82", "unsafe_control")
        a.emit(f"89{0xc0 | (reg << 3):02x}"); add(0, count); a.branch("0f82", "unsafe_control")
        a.emit("39d0"); a.branch("0f87", "unsafe_control")

    def expected_field_return():
        full = "unwind.full." + str(len(a.code))
        done = full + ".done"
        get(0, MODE); a.emit("85c0"); eq(full)
        imm(1, returns[1][1]); a.relocations.append(assembler_module.Relocation(len(a.code)-4, "abs32", returns[1][1], "incremental leased field return"))
        a.branch("e9", done)
        a.label(full)
        imm(1, returns[0][1]); a.relocations.append(assembler_module.Relocation(len(a.code)-4, "abs32", returns[0][1], "full leased field return"))
        a.label(done)

    def unwind_controls(captured=False):
        # Validate real return/saved-EBP words before any ordinary rejection.
        # After Thread, use our independent pre-callback copies, not paired
        # mutable descriptor/actual words supplied by the callback.
        get(7, LEASE_EBP); get(6, FIELD_EBP)
        load(0, 6, FIELD_BYTES + 8); match(0, LEASE_EBP); ne("unsafe_control")
        expected_field_return()
        load(0, 6, FIELD_BYTES + 36); a.emit("39c8"); ne("unsafe_control")
        for off, saved in ((60, LEASE_BYTES + 36), (64, LEASE_BYTES + 8)):
            load(0, 7, saved)
            if captured: match(0, off)
            else: mem("3b", 0, 7, off)
            ne("unsafe_control")

    def canonical():
        # All pointer intervals have passed before the first descriptor read.
        get(7, LEASE_EBP); get(6, FIELD_EBP)
        load(0, 6, FIELD_BYTES + 8); match(0, LEASE_EBP); ne("unsafe_control")
        for off, value in ((0, 0x534c4231), (4, 1), (8, LEASE_BYTES)):
            load(0, 7, off); cmp(0, value); ne("rejected")
        for off, value in ((12, lease.base_va), (16, lease.base_va + len(lease.code))):
            load(0, 7, off); address_cmp(0, value, "exact fresh lease code extent"); ne("rejected")
        load(0, 7, 20); match(0, ROOT_ESP); ne("rejected")
        mem("3b", 0, 6, 16); ne("rejected")
        load(0, 7, 24); read(1, state + 20, "fixed field loss owner thread")
        a.emit("39c8"); ne("rejected"); a.emit("85c0"); eq("rejected")
        mem("3b", 0, 6, 20); ne("rejected")
        load(0, 7, 28); a.emit("89f1"); add(1, FIELD_BYTES + 36); a.emit("39c8"); ne("rejected")
        load(0, 7, 36); a.emit("89f9"); add(1, LEASE_BYTES + 36); a.emit("39c8"); ne("rejected")
        for off, saved in ((60, LEASE_BYTES + 36), (64, LEASE_BYTES + 8)):
            load(0, 7, off); mem("3b", 0, 7, saved); ne("unsafe_control")
        load(0, 7, 40); match(0, MODE); ne("rejected")
        expected_field_return()
        load(0, 6, FIELD_BYTES + 36); a.emit("39c8"); ne("unsafe_control")
        load(0, 7, 32); a.emit("39c8"); ne("rejected")
        # Either latched loss or leaf status2 denies BEFORE Thread/cached reads.
        # Malformed loss/status combinations fail identically; none is adopted.
        load(0, 7, 44); a.emit("85c0"); ne("rejected")
        load(0, 7, 48); cmp(0, 1); a.branch("0f87", "rejected")
        load(0, 7, 52); mem("3b", 0, 7, 56); ne("rejected")
        cmp(0, 65536); a.branch("0f83", "rejected")
        for off in range(68, LEASE_BYTES, 4):
            load(0, 7, off); a.emit("85c0"); ne("rejected")

    for mode, pc, _ in post_calls:
        a.label("post_tile_incremental" if mode else "post_tile_full")
        a.emit("9c60fc81ec"); a.u32(HELPER_BYTES); a.emit("89e5")
        imm(0, mode); put(0, MODE)
        # A genuine CALL consumes one word below FieldEBP. This helper's
        # intrinsic saved EBP and return PC must independently agree with it.
        a.emit("89e8"); add(0, HELPER_BYTES + 40); put(0, FIELD_EBP)
        match(0, HELPER_BYTES + 8); ne("unsafe_control")
        get(0, HELPER_BYTES + 36)
        address_cmp(0, pc + 5, "actual post-Tile gate CALL return"); ne("unsafe_control")
        a.branch("e9", "admit")

    a.label("admit")
    read(0, state, "fixed field loss owner phase"); cmp(0, 2); ne("unsafe_control")
    read(0, state + 36, "fixed field loss owner fault"); a.emit("85c0"); ne("unsafe_control")
    read(0, state + 16, "fixed field loss root"); put(0, ROOT_ESP)
    a.emit("a903000000"); ne("unsafe_control"); cmp(0, 65536); a.branch("0f86", "unsafe_control")
    cmp(0, 0x7fff0000); a.branch("0f83", "unsafe_control")
    a.emit("89ef"); add(7, -44); extent(7, HELPER_BYTES + 84)
    get(7, FIELD_EBP); extent(7, FIELD_BYTES + 40)
    a.emit("89f8"); add(0, FIELD_BYTES + 40); put(0, LEASE_EBP)
    mem("3b", 0, 7, FIELD_BYTES + 8); ne("unsafe_control")
    a.emit("89c7"); extent(7, LEASE_BYTES + 40)
    unwind_controls()
    canonical()
    call(dict(lease.private_entries)["check_fixed_receipt"], "fresh fixed field receipt before cached reads")
    a.emit("83f801"); ne("rejected")
    get(7, LEASE_EBP)
    for off in range(0, LEASE_BYTES, 4):
        load(0, 7, off); put(0, off)
    for index, off in enumerate(CONTROL_SLOTS):
        get(0, off); put(0, CONTROL_SHADOW + 4 * index)
    # The frozen combined routing/same_invocation guards reread cached headers
    # inside their Thread callback boundary. They cannot be reused here: a
    # lease-only loss could otherwise be missed before those reads. Instead,
    # retain the already admitted exact field receipt around this one fixed
    # owning-thread query, then invoke only the callback-free full receipt.
    a.emit("fcff15"); a.absolute(0x4ea4e8, "fixed native owning thread callback")
    a.emit("89e5"); put(0, RESULT)
    for index, off in enumerate(CONTROL_SLOTS):
        get(0, off); match(0, CONTROL_SHADOW + 4 * index); ne("unsafe_control")
    unwind_controls(captured=True)
    # A changed descriptor is never silently repaired, adopted or retried.
    get(7, LEASE_EBP)
    for off in range(0, LEASE_BYTES, 4):
        load(0, 7, off); match(0, off); ne("rejected")
    canonical()
    call(dict(lease.private_entries)["check_fixed_receipt"], "fresh fixed field receipt after callback")
    a.emit("83f801"); ne("rejected")
    get(0, RESULT); match(0, 24); ne("rejected")
    a.emit("55"); get(5, FIELD_EBP)
    call(dict(field.private_entries)["check_invocation"], "callback-free fresh full field receipt")
    a.emit("5d89e5"); cmp(0, 1); ne("rejected")
    imm(0, 1); a.branch("e9", "finish")
    a.label("rejected"); imm(0, 0)
    a.label("finish"); put(0, HELPER_BYTES + 28)
    a.emit("81c4"); a.u32(HELPER_BYTES); a.emit("619dc3")
    a.label("unsafe_control"); a.emit("0f0b")
    code = bytes(a.finish())
    for off, label in a.fixups:
        a.relocations.append(assembler_module.Relocation(off, "rel32", base + a.labels[label], "field_loss_internal:" + label))
    _require(base + len(code) <= layout.rx.va + layout.rx.size, "field loss exceeds fresh RX reservation")
    patches = tuple((mode, pc, old, base + a.labels["post_tile_incremental" if mode else "post_tile_full"])
                    for mode, pc, old in post_calls)
    out = FieldLossEmission(base, state, code,
        tuple((name, base+a.labels[name]) for name in ("post_tile_full", "post_tile_incremental")),
        tuple(a.relocations), field.width, field.height, (("unsafe_control", base+a.labels["unsafe_control"]),), patches)
    assembler_module.absolute_relocation_offsets(out)
    return out


def _emit_code(layout, life, route, field, lease, content, *, content_module, content_kwargs,
               lease_module, field_module, assembler_module):
    expected = content_module._emit_code(layout, life, route, field, lease, **content_kwargs)
    _require(_identity(content) == _identity(expected), "complete canonical fresh ContentV2 bytes/ABI required")
    return _raw_emit(layout, field, lease, content, content_module=content_module,
                     lease_module=lease_module, field_module=field_module, assembler_module=assembler_module)


def _join_field(field, out):
    """Apply exactly two authenticated CALL edits to an emission, not a PE."""
    _require(tuple(row[0] for row in out.field_call_patches) == (0, 1), "two ordered field loss patches required")
    code = bytearray(field.code)
    relocations = list(field.relocations)
    offsets = set()
    for mode, pc, old, target in out.field_call_patches:
        at = pc - field.base_va
        _require(type(old) is bytes and len(old) == 5 and old[0] == 0xe8 and
                 0 <= at <= len(code)-5 and at not in offsets and code[at:at+5] == old and
                 target == dict(out.entries)["post_tile_incremental" if mode else "post_tile_full"],
                 "field loss old CALL bytes/target differ")
        rows = [(n, r) for n, r in enumerate(relocations) if r.offset == at+1]
        _require(len(rows) == 1 and rows[0][1].kind == "rel32" and
                 pc + 5 + struct.unpack_from("<i", old, 1)[0] == rows[0][1].target and
                 rows[0][1].target == dict(field.private_entries)["same_invocation"],
                 "field loss old CALL relocation differs")
        offsets.add(at)
        code[at:at+5] = b"\xe8" + struct.pack("<i", target-pc-5)
        n, row = rows[0]
        relocations[n] = replace(row, target=target, purpose="field_loss_post_tile")
    return replace(field, code=bytes(code), relocations=tuple(relocations))


def _issue(original, profile, resolution):
    _require(type(original) is bytes and _sha(original) == BASE_SHA256, "exact field loss original required")
    snapshot = _snapshot()
    with _content_module(snapshot[CONTENT][0]) as producer:
        parent = producer._issue(original, profile, resolution)
        lease = parent.lease_bundle
        field = lease.field_bundle
        context = field.routing_bundle.lifecycle_bundle.allocation_context
        layout = context.layout
        with producer._modules(snapshot) as modules:
            out = _raw_emit(layout, field.emission, lease.emission, parent.emission,
                content_module=producer, lease_module=modules[LEASE], field_module=modules[FIELD], assembler_module=modules[CLIP])
        joined = _join_field(field.emission, out)
        metadata = dict(schema="clash95_battle_profile_field_loss_v1", profile=profile, resolution=resolution,
            original_sha256=BASE_SHA256, parent_candidate_sha256=_sha(context.parent),
            relayout_parent_sha256=_sha(context.relayout_parent), canonical_probe_sha256=_sha(context.canonical_probe.encode()),
            validation_stage=layout.validation_stage, source_hashes=parent.metadata()["source_hashes"] |
                {name: _sha(raw) for name, (raw, _) in snapshot.items()},
            content_metadata_sha256=_sha(parent.metadata_json.encode()), content_code_sha256=_sha(parent.emission.code),
            lease_code_sha256=_sha(lease.emission.code), field_code_sha256=_sha(field.emission.code),
            joined_field_code_sha256=_sha(joined.code), code_va=out.base_va, code_bytes=len(out.code), code_sha256=_sha(out.code),
            helper_frame_bytes=HELPER_BYTES, field_frame_bytes=FIELD_BYTES, owning_lease_frame_bytes=LEASE_BYTES,
            field_call_patches=[dict(mode=mode, va=pc, code_offset=pc-field.emission.base_va,
                old_bytes=old.hex(), new_bytes=(b"\xe8"+struct.pack("<i",target-pc-5)).hex(), target_va=target,
                group="battle_profile_field_loss_preparation") for mode, pc, old, target in out.field_call_patches],
            unsafe_va=dict(out.private_entries)["unsafe_control"],
            gate_abi="direct post-Tile CALL; EAX0/1; unchanged outer Field draw2 on denial",
            latched_leaf_loss_gate_emitted=True, modeled_next_tile_cancellation=True,
            writes_owner_state=False, writes_descriptor=False, writes_headers=False, writes_pixels=False,
            preparation_only=True, installed_hooks=[], provider_records_emitted=0,
            prefix_rx_remaining_bytes=layout.rx.va+layout.rx.size-out.base_va-len(out.code),
            limitations=[
                "Only an uninstalled emitted-field join is supplied; no PE candidate, native hook or release lane is accepted.",
                "Loss is consumed after a normally returning Tile, not inside native continuations, RLE/provider callbacks or fatal/quit paths.",
                "Unknown helper control/return ancestry stops at UD2; healthy installed unwinding remains unresolved.",
                "The live Thread callback RET/ESP cannot be checked by this caller before a corrupted callback return executes; native callback control/ABI is unproved.",
                "Paired descriptor/outer-control changes already present at post-Tile admission lack an independent pre-Tile receipt; only subsequent callback-time pairs are shadowed here.",
                "Fixed owner/receipt checks are bounded observations, not native stack/mapping, transient-write or cross-thread authority.",
                "Fresh content value helpers still need native operand adapters; frozen continuation/primitive successors are incompatible.",
                "Full atomic installation, provider ownership, clipping, camera/input/animation/presentation/dialog/results remain required.",
            ], **{name: False for name in FALSE_CLAIMS})
    _unchanged(snapshot)
    return FieldLossBundle(out, joined, parent, json.dumps(metadata, sort_keys=True, separators=(",", ":"), allow_nan=False))


def _production_factory():
    # Capture the dispatcher in a separately compiled canonical module, so
    # mutable imported aliases are never production admission authority.
    from hashlib import sha256 as digest
    from pathlib import Path as SourcePath
    from types import ModuleType as SourceModule
    from uuid import uuid4 as unique_name
    from sys import modules as registry
    rejection = ValueError
    path = SourcePath(__file__).absolute()
    if path != path.parents[2] / "src/patcher/battle_profile_field_loss.py":
        raise rejection("canonical field loss producer required")
    root = path.parents[2]
    def read_source(target):
        if target != root / "src/patcher/battle_profile_field_loss.py" or target.resolve(strict=True) != target:
            raise rejection("canonical field loss source required")
        for item in (target, *target.parents):
            row = item.lstat()
            if item.is_symlink() or getattr(row, "st_file_attributes", 0) & 0x400:
                raise rejection("field loss source reparse forbidden")
        before = target.stat()
        if not 0 < before.st_size <= 2 * 1024 * 1024:
            raise rejection("bounded field loss source required")
        with target.open("rb") as stream:
            data = stream.read(2 * 1024 * 1024 + 1)
        after = target.stat()
        stamp = lambda r: (r.st_dev, r.st_ino, r.st_size, r.st_mtime_ns, getattr(r, "st_file_attributes", 0))
        if stamp(before) != stamp(after) or len(data) != after.st_size:
            raise rejection("field loss source changed while read")
        return data, stamp(after)
    raw, receipt = read_source(path)
    name = "_battle_field_loss_issuer_" + unique_name().hex
    module = SourceModule(name); module.__file__ = str(path)
    module.__loaded_source_sha256__ = digest(raw).hexdigest()
    module.__canonical_field_loss_issuer__ = True
    if registry.setdefault(name, module) is not module:
        raise rejection("field loss issuer namespace occupied")
    try:
        exec(compile(raw, str(path), "exec"), module.__dict__)
        issuer = module.__dict__["_issue"]
    finally:
        replaced = registry.get(name) is not module
        if registry.get(name) is module:
            del registry[name]
        if replaced:
            raise rejection("field loss issuer namespace identity changed")
    if read_source(path) != (raw, receipt):
        raise rejection("field loss source changed during capture")

    def dispatch(original, profile, resolution):
        if read_source(path) != (raw, receipt):
            raise rejection("captured field loss source differs")
        try:
            return issuer(original, profile, resolution)
        finally:
            if read_source(path) != (raw, receipt):
                raise rejection("field loss source changed during dispatch")
    return dispatch


if not globals().get("__canonical_field_loss_issuer__", False):
    emit_field_loss = _production_factory()
