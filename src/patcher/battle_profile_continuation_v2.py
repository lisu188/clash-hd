"""Uninstalled fresh post-normal-return adapters after Atomic Unit/Count V2.

The frozen continuation remains unchanged. This successor emits the 43 exact
normal-return windows and two tail-JMP joins to the current field-loss gates.
Unknown/lost control terminates at UD2; no native unwind, provider, installed
hook, candidate or healthy battle-return acceptance is supplied.
"""
from __future__ import annotations

import ast
from contextlib import contextmanager, ExitStack
from dataclasses import dataclass, replace
import hashlib
import json
from pathlib import Path
import struct
import sys
import types
import uuid

ROOT = Path(__file__).resolve().parents[2]
SOURCE = "src/patcher/battle_profile_continuation_v2.py"
PARENT = "src/patcher/battle_profile_adjacent_unit_v2.py"
PARENT_SHA = "b2ae87457bd2344d9e6650032dba46d03a680e2303946acb75abaf0508f5ead8"
LEDGER = "src/patcher/battle_profile_continuation.py"
LEDGER_SHA = "075bd62a8311f8cc761136bca21063813dfc874ce8d8a5bcf075ebdb664d811f"
TEMPLATE = "src/patcher/battle_profile_content.py"
CLIP = "src/patcher/partial_tile_clip.py"
PE = "src/patcher/pe_extension.py"
LOSS = "src/patcher/battle_profile_field_loss.py"
BASE_SHA = "500055d77d03d514e8d3168506bd10f67cd8569bcc450604ff8192f46cdaf3ae"
PROFILES = ("classic", "framed", "completehd", "modalwidgets")
RESOLUTIONS = ("1920x1080", "2560x1440", "3840x2160")
HELPER_BYTES, CONTROL_SHADOW = 1280, 784
EARLY_UNIT_POSTS = (0x42f932, 0x42f95b, 0x42fbbd, 0x42fc1e)
FINAL_ADJACENT_POST, MOTION, ACTIVE = 0x42ffa4, 0x523f70, 0x512360
FALSE_CLAIMS = ("installed", "battle_installed", "expanded_battle_installed", "installation_ready",
    "native_executed", "runtime_verified", "native_callback_abi_verified", "native_stack_capacity_verified",
    "whole_chain_capacity_verified", "historical_motion_authority_verified", "provider_validity_verified",
    "provider_lifetime_verified", "intra_decoder_cancellation", "healthy_native_unwind_verified",
    "healthy_map_return_verified", "atomic_installation_verified", "manual_input_proof",
    "release_accepted", "promotion_ready")


def _require(value, message):
    if not value:
        raise ValueError(message)


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _read(path):
    _require(path.is_absolute() and path.is_relative_to(ROOT) and path.resolve(strict=True) == path,
             "canonical fresh continuation source required")
    for item in (path, *path.parents):
        stat = item.lstat()
        _require(not item.is_symlink() and not getattr(stat, "st_file_attributes", 0) & 0x400,
                 "continuation source reparse forbidden")
    before = path.stat()
    _require(0 < before.st_size <= 2*1024*1024, "bounded continuation source required")
    with path.open("rb") as stream:
        raw = stream.read(2*1024*1024+1)
    after = path.stat()
    stamp = lambda row: (row.st_dev, row.st_ino, row.st_size, row.st_mtime_ns, getattr(row, "st_file_attributes", 0))
    _require(stamp(before) == stamp(after) and len(raw) == after.st_size,
             "continuation source changed while read")
    return raw, stamp(after)


@contextmanager
def _parent_module(raw):
    _require(type(raw) is bytes and _sha(raw) == PARENT_SHA, "whole frozen Atomic Unit V2 source required")
    name = "_fresh_continuation_parent_"+uuid.uuid4().hex
    module = types.ModuleType(name)
    module.__file__ = str(ROOT/PARENT)
    module.__loaded_source_sha256__ = PARENT_SHA
    module.__canonical_adjacent_unit_v2_issuer__ = True
    _require(sys.modules.setdefault(name, module) is module, "continuation namespace occupied")
    try:
        exec(compile(raw, module.__file__, "exec"), module.__dict__)
        yield module
    finally:
        changed = sys.modules.get(name) is not module
        if not changed:
            del sys.modules[name]
        _require(not changed, "continuation namespace changed")


def _snapshot():
    parent = _read(ROOT/PARENT)
    with _parent_module(parent[0]) as module:
        result = module._snapshot()
    own = _read(ROOT/SOURCE)
    ledger = _read(ROOT/LEDGER)
    _require(_sha(ledger[0]) == LEDGER_SHA and result[LEDGER] == ledger
             and globals().get("__loaded_source_sha256__") == _sha(own[0]),
             "private complete continuation source graph required")
    return result | {SOURCE: own}


def _unchanged(snapshot):
    _require(all(_read(ROOT/name) == row for name, row in snapshot.items()),
             "fresh continuation source graph changed")


@contextmanager
def _graph(parent_module, snapshot):
    with ExitStack() as stack:
        body = stack.enter_context(parent_module._body_module(snapshot[parent_module.PARENT][0]))
        entry = stack.enter_context(body._entry_module(snapshot[parent_module.ENTRY][0]))
        replay = stack.enter_context(entry._replay_module(snapshot[parent_module.REPLAY][0]))
        tile = stack.enter_context(replay._tile_module(snapshot[parent_module.TILE][0]))
        loss = stack.enter_context(tile._loss_module(snapshot[parent_module.LOSS][0]))
        content = stack.enter_context(loss._content_module(snapshot[parent_module.CONTENT][0]))
        modules = stack.enter_context(content._modules(snapshot))
        yield content, modules


def _ledger(raw):
    _require(type(raw) is bytes and _sha(raw) == LEDGER_SHA, "complete frozen continuation ledger required")
    tree = ast.parse(raw)
    def literal(name):
        nodes = [node for node in tree.body if isinstance(node, ast.Assign)
                 and any(isinstance(target, ast.Name) and target.id == name for target in node.targets)]
        _require(len(nodes) == 1, "one frozen continuation ledger field required")
        return ast.literal_eval(nodes[0].value)
    rows, highlow = literal("POST_WINDOWS"), literal("NATIVE_HIGHLOW")
    _require(len(rows) == 43 and len({va for va, _, _ in rows}) == 43
             and all(family in ("unit", "adjacent", "tile") for _, family, _ in rows),
             "exact 43 normal-return windows required")
    return rows, highlow


@dataclass(frozen=True)
class GuardEmission:
    base_va: int
    state_va: int
    code: bytes
    entries: tuple
    relocations: tuple
    width: int
    height: int
    private_entries: tuple


@dataclass(frozen=True)
class ContinuationV2Emission:
    base_va: int
    state_va: int
    code: bytes
    entries: tuple
    relocations: tuple
    width: int
    height: int
    private_entries: tuple
    planned_hooks: tuple
    field_call_patches: tuple
    adapter_receipts: tuple
    guard_source_sha256: str
    source_transforms: tuple


@dataclass(frozen=True)
class ContinuationV2Bundle:
    emission: ContinuationV2Emission
    joined_field_emission: object
    adjacent_unit_bundle: object
    metadata_json: str
    hook_sites: tuple = ()
    removed_highlow_rvas: tuple = ()

    def metadata(self):
        return json.loads(self.metadata_json)


def _guard_source(atomic_module, content_module, template_source, template_module, rows):
    source, _, _, namespace = atomic_module._whole_model_source(content_module, template_source, template_module)
    transforms = []
    def edit(old, new):
        nonlocal source
        _require(source.count(old) == 1, "one exact fresh post-return source transformation required: "+old[:70])
        source = source.replace(old, new)
        transforms.append((old, new, 1))
    begin = source.index("    for number,row in enumerate(SITES):\n")
    end = source.index("    # Only outer helper paths", begin)
    edit(source[begin:end], "")
    edit("tuple((f'site_{va:06x}',base+a.labels[f'site_{va:06x}']) for va,*_ in SITES)", "()")
    edit("extent(7,HELPER_BYTES+84,reject)", "extent(7,HELPER_BYTES+140,reject)")
    old = "        load(0,7,0);cmpva(0,va+5,'fixed proposed body CALL return PC');ne(reject)\n"
    edit(old, old+"        a.emit('8d4c240439cd');ne(reject)\n"
         "        a.emit('8b0424');cmpva(0,admit_return_pc,'fixed continuation helper admission CALL return');ne(reject)\n"
         "        get(0,HELPER_BYTES+36);cmpva(0,thunk_returns[number],'fixed continuation outer thunk CALL return');ne(reject)\n"
         "        get(7,NATIVE_S)\n")
    edit("    get(0,SITE);cmp(0,9);eq('tile.index.receipt');cmp(0,10);ne('tile.index.done')\n"
         "    a.label('tile.index.receipt');get(7,TILE_S);add(7,-44);record(7,4,reject)\n", "")
    early = tuple(i for i, (va, _, _) in enumerate(rows) if va in EARLY_UNIT_POSTS)
    edit("        get(0,SITE);cmp(0,0);eq(label+'.early')\n",
         "        get(0,SITE)\n        for early_post in early_unit_posts:cmp(0,early_post);eq(label+'.early')\n")
    final = next(i for i, (va, _, _) in enumerate(rows) if va == FINAL_ADJACENT_POST)
    edit("    a.label('ebp.adjacent');get(7,TILE_S);load(7,7,-24)\n",
         "    a.label('ebp.adjacent');get(0,SITE);cmp(0,final_adjacent_post);ne('post.adjacent.ordinary')\n"
         "    read(0,MOTION_SOURCE,'fixed final Adjacent post-return motion');a.emit('85c0');a.branch('0f89',reject);put(0,Y)\n"
         "    read(0,ACTIVE_SOURCE,'fixed final Adjacent post-return active identity');cmp(0,22);a.branch('0f83',reject);put(0,INDEX)\n"
         "    get(7,Y);jump('ebp.compare')\n"
         "    a.label('post.adjacent.ordinary');get(7,TILE_S);load(7,7,-24)\n")
    edit("    motion_witness('after');match(0,INDEX);ne(reject)\n",
         "    get(0,KIND);cmp(0,2);eq('post.adjacent.witness.done')\n"
         "    motion_witness('after');match(0,INDEX);ne(reject)\n"
         "    a.label('post.adjacent.witness.done')\n")
    control = tuple(namespace["AUTHORITY_LOCALS"]) + tuple(namespace["INPUT_SLOTS"] if "INPUT_SLOTS" in namespace else range(400, 436, 4))
    control += tuple(range(HELPER_BYTES, HELPER_BYTES+92, 4)) + (-4,)
    _require(CONTROL_SHADOW+4*len(control) < HELPER_BYTES and CONTROL_SHADOW >= 772,
             "post-return control shadows overlap live fields")
    namespace.update(HELPER_BYTES=HELPER_BYTES, CONTROL_SLOTS=control, CONTROL_SHADOW=CONTROL_SHADOW,
        SITES=tuple((va, "", family, "post", 0, 0) for va, family, _ in rows),
        early_unit_posts=early, final_adjacent_post=final, CodeEmission=GuardEmission)
    return source, tuple(transforms), namespace, control


def _raw_guard(layout, field, lease, guard_base, admit_return_pc, thunk_returns, rows, *, atomic_module,
               content_module, template_module, template_source, assembler_module):
    source, transforms, namespace, control = _guard_source(atomic_module, content_module,
        template_source, template_module, rows)
    modal = [span for span in layout.protected_spans if span.role == "parent:.hdstate"]
    _require(len(modal) == int(layout.profile in ("completehd", "modalwidgets")), "post-return modal identity differs")
    plan = {"profile": layout.profile}
    def captured(supplied, parent):
        _require(supplied is plan and parent is lease, "canonical fresh post-return lease required")
        return layout.rx.va, layout.rw.va, field.width, field.height, dict(field.private_entries)["check_invocation"]
    namespace.update(_layout=captured, model_base=guard_base,
        modal_va=None if not modal else modal[0].va,
        protected_intervals=((layout.rx.va, layout.rx.va+layout.rx.size), (layout.rw.va, layout.rw.va+layout.rw.size))+
            (() if not modal else ((modal[0].va, modal[0].va+modal[0].size),)),
        admit_return_pc=admit_return_pc, thunk_returns=thunk_returns)
    exec(compile(source, str(ROOT/SOURCE)+"#atomic_post_return_guard", "exec"), namespace)
    parent = assembler_module._Assembler
    class CompleteAssembler(parent):
        def finish(self):
            code = super().finish()
            for offset, label in self.fixups:
                self.relocations.append(assembler_module.Relocation(offset, "rel32", self.base+self.labels[label],
                    "post_return_guard_internal:"+label))
            return code
    assembler = types.SimpleNamespace(_Assembler=CompleteAssembler, Relocation=assembler_module.Relocation,
        absolute_relocation_offsets=assembler_module.absolute_relocation_offsets)
    guard = namespace["_versioned_emit_code"](plan, lease, assembler_module=assembler)
    _require(guard.base_va == guard_base and guard.entries == (), "fresh post-return guard extent differs")
    return guard, source, transforms, control


def _raw_emit(layout, field, lease, content, loss, joined_field, atomic_model, atomic_adapters, atomic_entry, *,
              atomic_module, content_module, template_module, template_source, ledger_source,
              loss_module, assembler_module):
    rows, highlow = _ledger(ledger_source)
    _require(layout.profile in PROFILES and layout.resolution in RESOLUTIONS
             and layout.rx.size == 0x40000 and layout.rw.size == 0x10000
             and layout.provider_schema == "unpopulated_provider_reservation_v1",
             "fixed fresh empty-provider continuation context required")
    atomic_module._model_operand_inventory(atomic_model, content, field, template_source=template_source)
    atomic_module._adapter_operand_inventory(atomic_adapters, atomic_model, ledger_source=ledger_source)
    atomic_module._entry_operand_inventory(atomic_entry, atomic_model, field, template_source=template_source)
    expected_field = loss_module._join_field(field, loss)
    _require(atomic_module._identity(joined_field) == atomic_module._identity(expected_field),
             "complete canonical field-loss join required")
    base = (atomic_entry.base_va+len(atomic_entry.code)+15)&~15
    a = assembler_module._Assembler(base)
    hooks, receipts, entries, calls = [], [], [], []
    def transfer(target, purpose, opcode="e9"):
        a.emit(opcode); offset = len(a.code)
        a.relocations.append(assembler_module.Relocation(offset, "rel32", target, purpose))
        a.u32(target-base-offset-4)
    def branch(label, opcode="e9"):
        a.branch(opcode, label)
    def replay(raw, va):
        position = 0
        while position < len(raw):
            tail = raw[position:]
            if tail[0] == 0xe9:
                transfer(va+position+5+struct.unpack_from("<i", raw, position+1)[0], "post_native_jmp")
                position += 5; continue
            if 0x70 <= tail[0] <= 0x7f:
                transfer(va+position+2+struct.unpack_from("<b", raw, position+1)[0], "post_native_condition",
                         "0f"+f"{tail[0]+16:02x}")
                position += 2; continue
            if tail[:2] == b"\x0f\x85":
                transfer(va+position+6+struct.unpack_from("<i", raw, position+2)[0], "post_native_condition", "0f85")
                position += 6; continue
            size = _scalar_length(raw, position)
            start = len(a.code)
            a.emit(raw[position:position+size].hex())
            for field_va in highlow:
                if va+position <= field_va < va+position+size:
                    old = field_va-va
                    _require(old+4 <= position+size, "post-return HIGHLOW splits an instruction")
                    a.relocations.append(assembler_module.Relocation(start+old-position, "abs32",
                        struct.unpack_from("<I", raw, old)[0], "post_native_highlow"))
            position += size
    for number, (va, family, raw_hex) in enumerate(rows):
        name = f"post_{va:06x}"
        a.label(name); entries.append((name, base+len(a.code)))
        a.emit("9c60fc83ec10c7042400000000c744240400000000c7442408"); a.u32(number)
        a.emit("c744240c"); a.u32(("tile", "unit", "adjacent", "vertical", "count").index(family))
        branch("helper", "e8"); calls.append(base+len(a.code))
        a.emit("83f801"); branch("unsafe_control", "0f85")
        a.emit("83c410619d8d642404")
        raw = bytes.fromhex(raw_hex)
        tail = base+len(a.code)
        replay(raw, va)
        transfer(va+len(raw), "post_native_resume")
        hooks.append((va, raw, dict(entries)[name], "fresh_post_normal_return",
                      tuple(field-0x400000 for field in highlow if va <= field < va+len(raw))))
        receipts.append((va, family, dict(entries)[name], calls[-1], tail, va+len(raw)))
    field_patches = []
    for mode, pc, original, target in loss.field_call_patches:
        at = pc-joined_field.base_va
        expected = b"\xe8"+struct.pack("<i", target-pc-5)
        _require(joined_field.code[at:at+5] == expected, "actual joined field post-Tile CALL differs")
        name = "field_post_incremental" if mode else "field_post_full"
        a.label(name); wrapper = base+len(a.code); entries.append((name, wrapper))
        transfer(target, "fresh_field_loss_tail_join")
        field_patches.append((mode, pc, expected, wrapper))
    a.label("helper"); a.emit("9c60fc81ec"); a.u32(HELPER_BYTES); a.emit("89e5")
    branch("guard.capture_inputs", "e8")
    for slot in tuple(range(200, 236, 4))+tuple(range(240, 392, 4)):
        a.emit("c785"); a.u32(slot); a.u32(0)
    a.emit("8b85"); a.u32(HELPER_BYTES+48); a.emit("8985"); a.u32(200)
    a.emit("8b85"); a.u32(HELPER_BYTES+52); a.emit("8985"); a.u32(204)
    a.emit("8d85"); a.u32(HELPER_BYTES+92); a.emit("8985"); a.u32(208)
    branch("guard.admit_body", "e8"); admit_return = base+len(a.code)
    a.emit("83f801"); branch("unsafe_control", "0f85")
    a.emit("8985"); a.u32(HELPER_BYTES+28)
    a.emit("89ec81c4"); a.u32(HELPER_BYTES); a.emit("619dc3")
    a.label("unsafe_control"); a.emit("0f0b")
    guard_base = (base+len(a.code)+15)&~15
    guard, source, transforms, control = _raw_guard(layout, field, lease, guard_base, admit_return, tuple(calls), rows,
        atomic_module=atomic_module, content_module=content_module, template_module=template_module,
        template_source=template_source, assembler_module=assembler_module)
    for name, va in guard.private_entries:
        a.labels["guard."+name] = va-base
    code = bytes(a.finish())
    for offset, label in a.fixups:
        a.relocations.append(assembler_module.Relocation(offset, "rel32", base+a.labels[label],
            "fresh_post_internal:"+label))
    code += b"\x90"*(guard_base-base-len(code))+guard.code
    a.relocations.extend(assembler_module.Relocation(row.offset+guard_base-base, row.kind, row.target, row.purpose)
                         for row in guard.relocations)
    _require(base+len(code) <= layout.rx.va+layout.rx.size, "fresh continuation exceeds canonical RX reservation")
    private = (("helper", base+a.labels["helper"]), ("unsafe_control", base+a.labels["unsafe_control"]),
               ("admit_body", dict(guard.private_entries)["admit_body"]))
    private += tuple(("guard."+name, va) for name, va in guard.private_entries if "unsafe" in name)
    out = ContinuationV2Emission(base, layout.rw.va, code, tuple(entries), tuple(a.relocations), field.width, field.height,
        private, tuple(hooks), tuple(field_patches), tuple(receipts), _sha(source.encode()), transforms)
    assembler_module.absolute_relocation_offsets(out)
    _require(len(out.planned_hooks) == 43 and len(out.field_call_patches) == 2
             and len({row.offset for row in out.relocations}) == len(out.relocations),
             "complete fresh continuation window/field/operand inventory required")
    return out


def _scalar_length(raw, position):
    tail = raw[position:]; opcode = tail[0]
    if opcode == 0x3a: return 2 if tail[1]&0xc0 == 0xc0 else 6
    if opcode in (0x31, 0x39, 0x85, 0x01): return 2 if tail[1]&0xc0 == 0xc0 else 7
    if opcode in (0x43, 0x5d, 0x5f, 0x5e): return 1
    if opcode == 0x83: return 4 if tail[1] == 0x7d else 3
    if opcode == 0x6b: return 3
    if opcode in (0xa1, 0xa3, 0xba): return 5
    if opcode in (0x03, 0x3b): return 6
    if opcode == 0x8b: return 3 if tail[1] in (0x45, 0x55, 0x5d, 0x7d, 4) else 6
    if opcode == 0x8d: return 7
    if opcode == 0x89: return 2
    raise ValueError("unsupported whole post-return scalar instruction")


def _join_field(joined, out):
    _require(tuple(row[0] for row in out.field_call_patches) == (0, 1)
             and len({row[1] for row in out.field_call_patches}) == 2,
             "two ordered unique fresh field tail joins required")
    code, relocations = bytearray(joined.code), list(joined.relocations)
    for mode, pc, old, target in out.field_call_patches:
        name = "field_post_incremental" if mode else "field_post_full"
        wrapper = target-out.base_va
        _require(dict(out.entries).get(name) == target and out.code[wrapper:wrapper+1] == b"\xe9",
                 "source-owned field tail wrapper entry required")
        native_target = pc+5+struct.unpack_from("<i", old, 1)[0]
        wrappers = [row for row in out.relocations if row.offset == wrapper+1]
        _require(len(wrappers) == 1 and
                 (wrappers[0].kind, wrappers[0].target, wrappers[0].purpose) ==
                 ("rel32", native_target, "fresh_field_loss_tail_join") and
                 target+5+struct.unpack_from("<i", out.code, wrapper+1)[0] == native_target,
                 "complete callback-free field tail wrapper required")
        at = pc-joined.base_va
        rows = [(index, row) for index, row in enumerate(relocations) if row.offset == at+1]
        _require(code[at:at+5] == old and len(rows) == 1 and rows[0][1].kind == "rel32"
                 and rows[0][1].purpose == "field_loss_post_tile", "complete fresh field-loss CALL receipt required")
        code[at:at+5] = b"\xe8"+struct.pack("<i", target-pc-5)
        index, row = rows[0]
        relocations[index] = replace(row, target=target, purpose="continuation_v2_field_loss_tail")
    return replace(joined, code=bytes(code), relocations=tuple(relocations))


def _authenticate_native(original, relayout_parent, clip, pe, ledger_source):
    rows, highlow = _ledger(ledger_source)
    for image in (original, relayout_parent):
        parsed = pe.inspect_pe(image)
        _, relocations = pe._old_relocations(image, parsed)
        wanted = {va for va in highlow if any(pc <= va < pc+len(bytes.fromhex(raw)) for pc, _, raw in rows)}
        actual = {parsed.image_base+rva for rva in relocations
                  if any(pc <= parsed.image_base+rva < pc+len(bytes.fromhex(raw)) for pc, _, raw in rows)}
        _require(actual == wanted, "whole normal-return HIGHLOW inventory differs")
        for pc, _, raw in rows:
            expected = bytes.fromhex(raw)
            at = clip.file_offset(image, pc, len(expected))
            _require(image[at:at+len(expected)] == expected, "whole native normal-return window differs")


def _issue(original, profile, resolution):
    _require(type(original) is bytes and _sha(original) == BASE_SHA, "exact continuation V2 original required")
    _require(profile in PROFILES and resolution in RESOLUTIONS, "selected continuation V2 profile/preset required")
    snapshot = _snapshot()
    with _parent_module(snapshot[PARENT][0]) as atomic:
        parent = atomic._issue(original, profile, resolution)
        body = parent.count_body_bundle
        replay = body.count_entry_bundle.content_replay_bundle
        loss_bundle = replay.tile_replay_bundle.field_loss_bundle
        content = loss_bundle.content_bundle
        lease, field = content.lease_bundle, content.lease_bundle.field_bundle
        context = field.routing_bundle.lifecycle_bundle.allocation_context
        with _graph(atomic, snapshot) as (content_module, modules):
            # The canonical parent includes every frozen native span, caller,
            # Count entry/body contract and selected original-byte override.
            _authenticate_native(original, context.relayout_parent, modules[CLIP], modules[PE], snapshot[LEDGER][0])
            out = _raw_emit(context.layout, field.emission, lease.emission, content.emission,
                loss_bundle.emission, loss_bundle.joined_field_emission, parent.model_emission,
                parent.emission, parent.count_entry_emission, atomic_module=atomic,
                content_module=content_module, template_module=modules[TEMPLATE], template_source=snapshot[TEMPLATE][0],
                ledger_source=snapshot[LEDGER][0], loss_module=_loss_module(snapshot), assembler_module=modules[CLIP])
        joined = _join_field(loss_bundle.joined_field_emission, out)
        metadata = dict(schema="clash95_battle_profile_continuation_v2", profile=profile, resolution=resolution,
            original_sha256=BASE_SHA, parent_candidate_sha256=_sha(context.parent),
            relayout_parent_sha256=_sha(context.relayout_parent), validation_stage=context.layout.validation_stage,
            source_hashes=parent.metadata()["source_hashes"] | {name: _sha(row[0]) for name, row in snapshot.items()},
            code_sha256=_sha(out.code), code_va=out.base_va, code_bytes=len(out.code),
            atomic_model_sha256=_sha(parent.model_emission.code), atomic_adapters_sha256=_sha(parent.emission.code),
            count_entry_sha256=_sha(parent.count_entry_emission.code), joined_field_sha256=_sha(joined.code),
            normal_return_windows=43, field_loss_tail_joins=2, helper_frame_bytes=HELPER_BYTES,
            outer_thunk_bytes=16, control_shadow_offset=CONTROL_SHADOW,
            guard_source_sha256=out.guard_source_sha256,
            prefix_rx_remaining_bytes=context.layout.rx.va+context.layout.rx.size-out.base_va-len(out.code),
            provider_schema=context.layout.provider_schema, provider_records_emitted=0,
            tail_policy="unchanged exact-zero fresh/inherited provider tails",
            early_unit_post_sites=list(EARLY_UNIT_POSTS), final_adjacent_post_site=FINAL_ADJACENT_POST,
            final_adjacent_policy="exact source site and current negative motion/active identity; no dead Unit frame or historical witness",
            failure_behavior="UD2 for unknown/lost control; no native epilogue or installed cancellation",
            preparation_only=True, installed_hooks=[], candidate_written=False,
            limitations=["Normal-return scalar replay is not cancellation inside native Tile, sprite, RLE or provider callbacks.",
                "Current motion/identity equality is not historical call-time authority or transient/cross-thread immutability.",
                "Field tail joins retain the separately scoped canonical field-loss policy and actual return PCs.",
                "Numeric helper/RX bounds are not native mapped stack or complete-chain capacity.",
                "Primitive/line/provider/presentation/input/camera/results/quit and atomic installation remain unfinished."],
            **{name: False for name in FALSE_CLAIMS})
    _unchanged(snapshot)
    return ContinuationV2Bundle(out, joined, parent, json.dumps(metadata, sort_keys=True, separators=(",", ":")))


def _loss_module(snapshot):
    # No public imported alias selects the field join implementation.
    module = types.ModuleType("_continuation_loss_"+uuid.uuid4().hex)
    module.__file__ = str(ROOT/LOSS)
    module.__canonical_field_loss_issuer__ = True
    module.__loaded_source_sha256__ = _sha(snapshot[LOSS][0])
    name = module.__name__
    _require(sys.modules.setdefault(name, module) is module, "fresh loss namespace occupied")
    try:
        exec(compile(snapshot[LOSS][0], module.__file__, "exec"), module.__dict__)
    finally:
        _require(sys.modules.get(name) is module, "fresh loss namespace changed")
        del sys.modules[name]
    return module


def _production_factory():
    from hashlib import sha256
    from pathlib import Path as SourcePath
    from types import ModuleType
    from sys import modules
    from uuid import uuid4
    reject = ValueError
    path = SourcePath(__file__).absolute()
    if path != path.parents[2]/SOURCE:
        raise reject("canonical fresh continuation producer required")
    raw, stamp = _read(path)
    module = ModuleType("_fresh_continuation_issuer_"+uuid4().hex)
    module.__file__ = str(path)
    module.__loaded_source_sha256__ = sha256(raw).hexdigest()
    module.__canonical_continuation_v2_issuer__ = True
    if modules.setdefault(module.__name__, module) is not module:
        raise reject("fresh continuation issuer occupied")
    try:
        exec(compile(raw, str(path), "exec"), module.__dict__)
        issue, read = module._issue, module._read
    finally:
        if modules.get(module.__name__) is not module:
            raise reject("fresh continuation issuer changed")
        del modules[module.__name__]
    if read(path) != (raw, stamp):
        raise reject("fresh continuation source changed during capture")
    def dispatch(original, profile, resolution):
        if read(path) != (raw, stamp):
            raise reject("captured continuation source differs")
        try:
            return issue(original, profile, resolution)
        finally:
            if read(path) != (raw, stamp):
                raise reject("captured continuation source changed")
    return dispatch


if not globals().get("__canonical_continuation_v2_issuer__", False):
    emit_continuation_v2 = _production_factory()
