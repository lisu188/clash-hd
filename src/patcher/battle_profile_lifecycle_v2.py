"""Fresh-address tactical HUD lifecycle re-emission; never installed.

The captured production issuer privately reconstructs the canonical V2 parent
and allocation. A bounded, audited transformation of the frozen lifecycle
template re-emits every instruction and operand for the new RX/fresh RW layout.
Native callbacks remain original ABI targets, not modeled production providers.

This empty-provider preparation rejects nonzero new RW padding/reservation and
nonzero inherited modal tail beyond 128 bytes. The latter is a restrictive
unsupported-tail admission, not proof of native dynamic writers or stable game
compatibility. First 128-byte records retain complete snapshot comparisons.
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
SOURCE = "src/patcher/battle_profile_lifecycle_v2.py"
CONTEXT = "src/patcher/battle_profile_context_v2.py"
TEMPLATE = "src/patcher/battle_profile_lifecycle.py"
CLIP = "src/patcher/partial_tile_clip.py"
PE = "src/patcher/pe_extension.py"
V1_CONTEXT = "src/patcher/battle_profile_context.py"
VIEWPORT = "src/patcher/framed_viewport.py"
PINNED_SOURCES = {
    CONTEXT: "d0a8b27ae4d07b290a449c1c875d4b574d329d2a9ac6b1397a2753f7d10ee5c9",
    TEMPLATE: "dccb907b09d002691cad679219942ac5a8ffcb2798af4c96b0b1768dbd9e9f44",
    V1_CONTEXT: "be3bbca018c415895ba7e79e64862512f330297fb56b4d8321f8f6d378c38500",
    CLIP: "92421c123a75bef119bfa93b438f813ec18dcb073699327cf15b7a1b884bcfad",
    PE: "4d66e7fa3bf17c6260fffaefc8d4e4e8da0ba76ceea7746858c52299f74d7c27",
    VIEWPORT: "1d5bc64777cf01c68f587bc3fee2dc7d5024696bd6b1712dab4e6e78f78c4c42",
}
BASE_SHA256 = "500055d77d03d514e8d3168506bd10f67cd8569bcc450604ff8192f46cdaf3ae"
FALSE_CLAIMS = ("installed", "battle_installed", "expanded_battle_installed", "installation_ready",
                "runtime_executed", "manual_input_proof", "promotion_ready", "release_accepted",
                "provider_capacity_verified", "provider_lifetime_verified", "atomic_installation_verified")


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _read(path, root):
    _require(path.is_absolute() and path.is_relative_to(root) and path.resolve(strict=True) == path,
             "canonical lifecycle V2 source required")
    for item in (path, *path.parents):
        row = item.lstat()
        _require(not item.is_symlink() and not getattr(row, "st_file_attributes", 0) & 0x400,
                 "lifecycle V2 reparse path forbidden")
    before = path.stat(); data = path.read_bytes(); after = path.stat()
    stamp = lambda row: (row.st_dev, row.st_ino, row.st_size, row.st_mtime_ns,
                         getattr(row, "st_file_attributes", 0))
    _require(stamp(before) == stamp(after) and len(data) == after.st_size, "source changed while read")
    return data, stamp(after)


def _snapshot():
    snapshot = {name: _read(ROOT / name, ROOT) for name in (*PINNED_SOURCES, SOURCE)}
    _require(all(_sha(snapshot[name][0]) == digest for name, digest in PINNED_SOURCES.items()),
             "frozen lifecycle V2 source pin differs")
    _require(globals().get("__loaded_source_sha256__") == _sha(snapshot[SOURCE][0]),
             "privately loaded lifecycle V2 source required")
    return snapshot


def _unchanged(snapshot):
    _require(all(_read(ROOT / name, ROOT) == receipt for name, receipt in snapshot.items()),
             "lifecycle V2 source closure changed")


@contextmanager
def _modules(snapshot):
    prefix = "_battle_lifecycle_v2_" + uuid.uuid4().hex
    owned, modules = {}, {}
    try:
        for suffix in ("", ".src", ".src.patcher"):
            module = types.ModuleType(prefix + suffix)
            module.__path__ = []
            _require(sys.modules.setdefault(module.__name__, module) is module,
                     "private lifecycle V2 namespace occupied")
            owned[module.__name__] = module
            if suffix:
                parent, _, leaf = module.__name__.rpartition(".")
                setattr(sys.modules[parent], leaf, module)
        for name in (VIEWPORT, PE, CLIP, V1_CONTEXT, CONTEXT, TEMPLATE):
            full = prefix + "." + name.removesuffix(".py").replace("/", ".")
            module = types.ModuleType(full)
            module.__file__ = str(ROOT / name)
            module.__package__ = full.rpartition(".")[0]
            module.__loaded_source_sha256__ = _sha(snapshot[name][0])
            _require(sys.modules.setdefault(full, module) is module,
                     "private lifecycle V2 namespace occupied")
            owned[full] = module
            setattr(sys.modules[module.__package__], full.rpartition(".")[2], module)
            exec(compile(snapshot[name][0], module.__file__, "exec"), module.__dict__)
            modules[name] = module
        yield modules
    finally:
        replaced = any(sys.modules.get(name) is not module for name, module in owned.items())
        for name, module in reversed(tuple(owned.items())):
            if sys.modules.get(name) is module:
                del sys.modules[name]
        _require(not replaced, "private lifecycle V2 namespace identity changed")


@dataclass(frozen=True)
class LifecycleV2Bundle:
    emission: object
    allocation_context: object
    planned_hooks: tuple
    removed_highlow_rvas: tuple[int, ...]
    metadata_json: str

    def metadata(self):
        return json.loads(self.metadata_json)


def _plan(layout):
    """Exact value validation for the explicitly synthetic emission boundary."""
    profile, resolution = layout.profile, layout.resolution
    _require(type(profile) is str and profile in ("classic", "framed", "completehd", "modalwidgets")
             and type(resolution) is str and resolution in ("800x600", "1024x768", "1280x720", "1280x960",
                 "1366x768", "1920x1080", "2560x1440", "3440x1440", "3840x2160"),
             "fixed lifecycle V2 selector required")
    rx, rw = layout.rx, layout.rw
    _require(all(type(n) is int for n in (rx.va, rx.rva, rx.size, rw.va, rw.rva, rw.size))
             and rx.va % 4096 == rw.va % 4096 == 0 and rx.va - rx.rva == 0x400000
             and rx.size == 0x40000 and rw.size == 0x10000 and rw.va == rx.va + rx.size
             and rw.rva == rx.rva + rx.size and rw.va + rw.size < 0x80000000
             and rx.characteristics == 0x60000020 and rw.characteristics == 0xC0000040
             and layout.battle_state_va == rw.va and layout.battle_state_bytes == 128
             and layout.protected_state_page_bytes == 4096
             and layout.provider_va == rw.va + 4096 and layout.provider_reservation_bytes == 61440
             and layout.provider_schema == "unpopulated_provider_reservation_v1",
             "fresh lifecycle V2 allocation contract differs")
    inherited = [row for row in layout.protected_spans if row.role == "parent:.hdstate"]
    _require(len(inherited) == (1 if profile in ("completehd", "modalwidgets") else 0),
             "inherited modal allocation count differs")
    modal = None if not inherited else inherited[0].va
    if modal is not None:
        _require(inherited[0].size == 4096 and type(modal) is int and modal % 4096 == 0
                 and 0x400000 <= modal < rx.va and modal + 4096 <= rx.va,
                 "inherited modal page must remain separate and protected")
    return dict(profile=profile, resolution=resolution, allocation_plan_only=True, battle_installed=False,
        rx=dict(va=rx.va, rva=rx.rva, virtual_reservation=rx.size, characteristics=rx.characteristics),
        rw=dict(va=rw.va, used_bytes=128, page_bytes=4096, page_offset=0,
                reservation_bytes=rw.size, characteristics=rw.characteristics)), modal


def _versioned_template(raw, template_module):
    """Transform only the pinned complete function, then compile fresh code.

    Exact replacement counts are an authored versioned source ledger. The
    predecessor is never modified or invoked with a spoofed allocation plan.
    """
    _require(type(raw) is bytes and _sha(raw) == PINNED_SOURCES[TEMPLATE], "frozen lifecycle template differs")
    tree = ast.parse(raw)
    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "_emit_code"]
    _require(len(functions) == 1, "one complete lifecycle emitter template required")
    source = ast.get_source_segment(raw.decode("utf-8"), functions[0])
    ledger = []

    def replace(old, new, count=1):
        nonlocal source
        _require(source.count(old) == count, "versioned lifecycle template edit boundary differs")
        ledger.append((old, new, count))
        source = source.replace(old, new)

    replace("def _emit_code(", "def _versioned_emit_code(")
    replace("0x20000", "0x40000", 3)
    replace('plan["rw"]["page_offset"] == (0 if modal_state_va is None else 0x100)',
            'plan["rw"]["page_offset"] == 0 and plan["rw"]["reservation_bytes"] == 0x10000')
    replace("and state == modal_state_va + 0x100", "and modal_state_va + 4096 <= base and state == base + 0x40000")
    replace("state_page = state if modal_state_va is None else modal_state_va", "state_page = state")
    replace('a.emit("b9"); address(state_page,"lifecycle RW page extent"); disjoint(reg,size,1,4096,reject,label+".state")',
            'a.emit("b9"); address(state_page,"lifecycle V2 whole RW reservation"); disjoint(reg,size,1,65536,reject,label+".state")')
    replace('disjoint(reg,size,1,128,reject,label+".modal")', 'disjoint(reg,size,1,4096,reject,label+".modal")')
    old_start = source.index("    def outside_state_page(")
    old_end = source.index("    def allocation_interval(", old_start)
    old = source[old_start:old_end]
    new = '''    def outside_state_page(reg, size, reject):
        a.emit("b9"); address(state_page,"owned lifecycle V2 RW reservation")
        disjoint(reg,size,1,65536,reject,reject+".rw"+str(len(a.code)))
        a.emit("b9"); address(base,"owned lifecycle V2 RX reservation")
        disjoint(reg,size,1,262144,reject,reject+".rx"+str(len(a.code)))
        if modal_state_va is not None:
            a.emit("b9"); address(modal_state_va,"entire inherited modal page")
            disjoint(reg,size,1,4096,reject,reject+".modalpage"+str(len(a.code)))
    def protected_zero(reject):
        tag = "v2_zero_" + str(len(a.code))
        a.emit("60")
        for start,size,purpose in ((state+128,65536-128,"empty V2 RW state/provider tail"),):
            a.emit("31c0b9"); a.u32(size//4)
            a.emit("bf"); address(start,purpose); a.emit("f3af")
            a.branch("0f85",tag+".reject")
        if modal_state_va is not None:
            a.emit("31c0b9"); a.u32((4096-128)//4)
            a.emit("bf"); address(modal_state_va+128,"restrictive zero inherited modal tail")
            a.emit("f3af"); a.branch("0f85",tag+".reject")
        a.emit("61"); a.branch("e9",tag+".done")
        a.label(tag+".reject"); a.emit("61"); a.branch("e9",reject)
        a.label(tag+".done")
'''
    replace(old, new)
    # Record comparisons plus the complete empty-tail policy run after every
    # Thread/native callback and before following cached heap objects.
    replace('    rollback_globals = (MAP,RENDER,OWNER,LOWER,POST,BATTLE,PRIMARY,',
            '        protected_zero(reject)\n    rollback_globals = (MAP,RENDER,OWNER,LOWER,POST,BATTLE,PRIMARY,')
    replace('a.label("try_enter"); save(); imm("enter_status",0)',
            'a.label("try_enter"); save(); protected_zero("enter.reject"); imm("enter_status",0)')
    replace('    def owned(phase,reject,owner):\n',
            '    def owned(phase,reject,owner):\n        protected_zero(reject)\n')
    # Rollback has its own snapshot, so legitimate previously latched fault4
    # remains diagnostic while mutations during the Thread query cannot become
    # newly accepted cleanup receipts. No unchecked cached object is followed.
    replace('a.label("enter.rollback"); thread(); local_cmp(0,LS["tid"]); ne("enter.untrusted")',
            'a.label("enter.rollback"); protected_zero("enter.untrusted"); rollback_snapshot(); thread(); local_cmp(0,LS["tid"]); ne("enter.untrusted"); rollback_stable("enter.untrusted")')
    # A bad constructor EAX is not a reason to skip its complete post-callback
    # receipt check. Keep that result in a spare bounded local DWORD first.
    replace('call(CTOR,"nonallocating native base constructor")\n    local_cmp(0,LS["header"]); ne("enter.rollback")\n    entry_snapshot("enter.changed")',
            'call(CTOR,"nonallocating native base constructor")\n    local_store(0,60); entry_snapshot("enter.changed")\n    local_read(0,60); local_cmp(0,LS["header"]); ne("enter.rollback")')
    namespace = dict(template_module.__dict__)
    exec(compile(source, str(ROOT / SOURCE) + "#pinned_versioned_template", "exec"), namespace)
    return namespace["_versioned_emit_code"], tuple(ledger)


def _emit_code(layout, *, template_source, template_module, assembler_module):
    """Explicit pure fixture boundary; caller layouts are not production authority."""
    plan, modal = _plan(layout)
    emitter, ledger = _versioned_template(template_source, template_module)
    original_assembler = assembler_module._Assembler
    relocation = assembler_module.Relocation

    class CompleteAssembler(original_assembler):
        def finish(self):
            code = super().finish()
            for offset, label in self.fixups:
                self.relocations.append(relocation(offset, "rel32", self.base + self.labels[label],
                    "v2_owned_branch:" + label))
            return code

    isolated = types.SimpleNamespace(_Assembler=CompleteAssembler, Relocation=relocation,
        absolute_relocation_offsets=assembler_module.absolute_relocation_offsets)
    emission = emitter(plan, modal_state_va=modal, assembler_module=isolated)
    _validate_emission(emission, layout, assembler_module)
    return emission


def _validate_emission(emission, layout, assembler_module):
    plan, modal = _plan(layout)
    _require(emission.base_va == layout.rx.va and emission.state_va == layout.rw.va
             and type(emission.code) is bytes and 0 < len(emission.code) < 0x40000,
             "fresh lifecycle V2 emitted allocation differs")
    assembler_module.absolute_relocation_offsets(emission)
    names = {name for name, _ in emission.entries}
    _require(names == {"try_enter", "bind_or_abort", "try_leave", "finish_return", "root_entry",
             "bind_allocation", "leave_before_free", "root_epilogue"}, "complete lifecycle entry family differs")
    for row in emission.relocations:
        if row.purpose.startswith("state.") or "own state" in row.purpose:
            _require(row.kind == "abs32" and layout.rw.va <= row.target < layout.rw.va + 128
                     and (row.target - layout.rw.va) % 4 == 0, "battle state operand escaped fresh RW record")
        if row.purpose.startswith("v2_owned_branch:"):
            _require(row.kind == "rel32" and emission.base_va <= row.target < emission.base_va + len(emission.code),
                     "owned branch target escaped emitted code")


def _issue(original, profile, resolution):
    _require(type(original) is bytes and _sha(original) == BASE_SHA256, "exact original required")
    snapshot = _snapshot()
    with _modules(snapshot) as modules:
        context = modules[CONTEXT].build_allocation_context(original, profile, resolution)
        layout = context.layout
        old = modules[TEMPLATE]
        parent_metadata = modules[V1_CONTEXT]._restore_metadata(json.loads(context.parent_metadata_json))
        context_metadata = context.metadata()
        legacy_plan = dict(profile=profile, resolution=resolution, original_sha256=BASE_SHA256,
            parent_stage=parent_metadata["stage"], parent_revision=parent_metadata["recipe_revision"],
            candidate_sha256=_sha(context.parent), source_hashes=context_metadata["source_hashes"])
        root_contract = old._authenticate_native(original, context.parent, modules[PE], modules[CLIP],
            profile=profile, parent_metadata=parent_metadata, plan=legacy_plan)
        if profile in ("completehd", "modalwidgets"):
            # Recompute the frozen declared inventory from this canonical parent;
            # it does not establish dynamic arithmetic or unknown tail writers.
            # V2 already independently reconstructs the complete parent. Use
            # the frozen inventory checker on those authenticated bytes rather
            # than performing redundant complete candidate reconstruction.
            prior_context = modules[V1_CONTEXT]
            inherited_sources, inherited_stamps = prior_context._source_snapshot(profile)
            inventory = prior_context._state_inventory(context.parent, parent_metadata, profile,
                modules[PE].inspect_pe(context.parent), modules[PE], inherited_sources)
            prior_context._unchanged(inherited_sources, inherited_stamps)
            _require(inventory["inherited_extent"][1] - inventory["inherited_extent"][0] == 128,
                     "inherited live-field inventory extent differs")
        else:
            inventory = None
        emission = _emit_code(layout, template_source=snapshot[TEMPLATE][0], template_module=old,
                              assembler_module=modules[CLIP])
        entries = dict(emission.entries)
        view = modules[CONTEXT]._parse(context.relayout_parent)
        hooks, removed = [], []
        for name, (va, raw, _) in old.SITES.items():
            before = bytes.fromhex(raw)
            at = view.file_offset(va - 0x400000, len(before))
            _require(context.relayout_parent[at:at + len(before)] == before,
                     "relayout lifecycle whole old hook bytes differ")
            op = b"\xe8" if name == "leave_before_free" else b"\xe9"
            after = op + struct.pack("<i", entries[name] - va - 5) + b"\x90" * (len(before) - 5)
            fields = tuple(sorted(va - 0x400000 + offset for offset in
                modules[CLIP]._original_highlow_fields(original, va, len(before))))
            _require(all(field in layout.highlow_rvas for field in fields), "stolen HIGHLOW parent inventory differs")
            hooks.append((name, at, va, before, after, entries[name], fields))
            removed.extend(fields)
        _, ledger = _versioned_template(snapshot[TEMPLATE][0], old)
        metadata = dict(schema="clash95_battle_profile_lifecycle_v2", profile=profile, resolution=resolution,
            original_sha256=BASE_SHA256, allocation_context_sha256=_sha(context.metadata_json.encode()),
            parent_candidate_sha256=_sha(context.parent), relayout_parent_sha256=_sha(context.relayout_parent),
            source_hashes=context_metadata["source_hashes"] | {name: _sha(raw) for name, (raw, _) in snapshot.items()},
            code_va=emission.base_va, state_va=emission.state_va, code_bytes=len(emission.code),
            code_sha256=_sha(emission.code), rx_reservation_bytes=0x40000, rx_remaining_bytes=0x40000-len(emission.code),
            rw_reservation_bytes=0x10000, state_bytes=128, state_offsets=old.STATE,
            provider_records_emitted=0, provider_capacity=None,
            new_rw_tail_policy="exact zero required [state+128,state+65536); no provider records",
            inherited_tail_policy="nonzero [modal+128,modal+4096) unsupported by this restrictive preparation",
            inherited_state_inventory=inventory, inherited_native_root_contract=root_contract,
            template_source_sha256=PINNED_SOURCES[TEMPLATE],
            template_edit_inventory=[dict(old=previous, new=next_value, count=count) for previous,next_value,count in ledger],
            helper_stack_snapshot_bytes=384, zero_scan_extra_stack_bytes=32,
            maximum_added_helper_stack_bytes=456,
            native_spans={name:dict(start=lo,end_exclusive=hi,sha256=digest) for name,(lo,hi,digest) in old.NATIVE_SPANS.items()},
            emission_preparation_only=True, native_callbacks_modeled_by_fixture=True,
            native_body_executed_by_fixture=False, transient_write_prevention_verified=False,
            cross_thread_immutability_verified=False,
            limitations=["Uninstalled fresh-address lifecycle only; hooks are descriptions and no candidate is saved.",
                "Zero scans reject persisted changes; they do not prevent transient native/cross-thread writes.",
                "Inherited field inventory covers declared offsets and HIGHLOWs, not dynamic writers; nonzero modal tail is explicitly unsupported.",
                "Native allocation-null cleanup preserves the fatal route and claims no healthy map return.",
                "Provider records/capacity/lifetime, RLE cancellation, drawing/input/camera/animation/dialog/results, quit and complete atomic installation remain unproved.",
                "All runtime/manual/endurance/promotion acceptance remains separately required."],
            **{name:False for name in FALSE_CLAIMS})
    _unchanged(snapshot)
    return LifecycleV2Bundle(emission, context, tuple(hooks), tuple(sorted(set(removed))),
        json.dumps(metadata, sort_keys=True, separators=(",", ":"), allow_nan=False))


def emit_lifecycle_v2(original, profile, resolution):
    raise ValueError("captured canonical lifecycle V2 factory required")


def _production_factory():
    from hashlib import sha256 as digest
    from pathlib import Path as SourcePath
    from types import ModuleType as SourceModule
    from uuid import uuid4 as unique_name
    from sys import modules as registry
    exact_type, exact_bytes, rejection = type, bytes, ValueError
    compile_source, execute_source = compile, exec
    path = SourcePath(__file__).absolute(); root = path.parents[2]
    if path != root / "src/patcher/battle_profile_lifecycle_v2.py":
        raise rejection("canonical lifecycle V2 producer required")

    def read():
        if path.resolve(strict=True) != path:
            raise rejection("canonical lifecycle V2 source required")
        for item in (path, *path.parents):
            row = item.lstat()
            if item.is_symlink() or getattr(row,"st_file_attributes",0) & 0x400:
                raise rejection("lifecycle V2 source reparse forbidden")
        before=path.stat(); raw=path.read_bytes(); after=path.stat()
        def stamp(row):
            return row.st_dev,row.st_ino,row.st_size,row.st_mtime_ns,getattr(row,"st_file_attributes",0)
        if stamp(before) != stamp(after) or len(raw) != after.st_size:
            raise rejection("lifecycle V2 source changed while read")
        return raw,stamp(after)

    raw,stamp=read(); identity=digest(raw).hexdigest()
    name="_battle_lifecycle_v2_issuer_"+unique_name().hex
    module=SourceModule(name);module.__file__=str(path)
    module.__loaded_source_sha256__=identity;module.__canonical_lifecycle_v2_issuer__=True
    if registry.setdefault(name,module) is not module:
        raise rejection("canonical lifecycle V2 issuer namespace occupied")
    try:
        execute_source(compile_source(raw,str(path),"exec"),module.__dict__)
        issuer=module.__dict__["_issue"]
    finally:
        if registry.get(name) is not module:
            raise rejection("canonical lifecycle V2 issuer replaced")
        del registry[name]
    if read() != (raw,stamp):
        raise rejection("canonical lifecycle V2 source changed during capture")
    original_digest="500055d77d03d514e8d3168506bd10f67cd8569bcc450604ff8192f46cdaf3ae"

    def dispatch(original,profile,resolution):
        if exact_type(original) is not exact_bytes or digest(original).hexdigest() != original_digest:
            raise rejection("exact original required")
        current,receipt=read()
        if digest(current).hexdigest() != identity:
            raise rejection("captured lifecycle V2 source differs")
        try:
            return issuer(original,profile,resolution)
        finally:
            if read() != (current,receipt):
                raise rejection("lifecycle V2 source changed during dispatch")
    return dispatch


if not globals().get("__canonical_lifecycle_v2_issuer__",False):
    emit_lifecycle_v2 = _production_factory()
