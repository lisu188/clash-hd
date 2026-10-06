"""Uninstalled, source-owned replay of the two clipped memory-line calls.

Only the callback-free native memory-line closure is admitted. Sprite/RLE
providers, the complete battle hook family and runtime acceptance remain open.
"""
from __future__ import annotations

import ast
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
SOURCE = 'src/patcher/battle_profile_line_replay.py'
PRIMITIVE = 'src/patcher/battle_profile_primitive_request.py'
PRIMITIVE_SHA = 'd72ecc813f0c4a6ddead76891efdf7fd27aa1e61c9b9d3483377a37fd996d01f'
BASE_SHA256 = '500055d77d03d514e8d3168506bd10f67cd8569bcc450604ff8192f46cdaf3ae'
LINE_TARGET = 0x403F70
LINE_WINDOWS = (
    (0x430AD5, 'ff5714e954fdffff', 0x430831),
    (0x430B07, 'ff571489ec5d5f5e595bc3', None),
)
REMOVED_OVERLAPS = (0x430AD8, 0x430B0A)
NATIVE_SPANS = (
    ('memory_line', 0x403F70, 0x40403D, '74308b78ce403326e9df50c52c7c522bbc645e6b5001961e3a957e5d9b0ebf5e'),
    ('fill_adapter', 0x473FD8, 0x473FF0, '72d0f071ad4527d35d1d3a72d27ba6c438a17144868c4d381f451485bbcbb3ec'),
    ('fill_closure', 0x487CF0, 0x487D93, '0d817cb2566a6e1c69d28ad408e2c64dbe30f5718e5c9e2a0126d2bc4d8ebc03'),
    ('memory_vtable', 0x50EE24, 0x50EE60, '297030147e736198144db61d9839b9be6372b4d8a679a20db4586c188367fa3e'),
)
FALSE_CLAIMS = ('installed', 'battle_installed', 'installation_ready', 'runtime_verified',
    'manual_input_verified', 'release_accepted', 'promotion_ready', 'arena_drawing_verified',
    'provider_validity_verified', 'sprite_storage_validity_verified', 'intra_decoder_cancellation',
    'process_quit_closure_verified', 'healthy_map_return_verified', 'full_battle_continuity_verified',
    'native_rle_replay_emitted', 'writes_headers', 'writes_owner_page')


@dataclass(frozen=True)
class CodeEmission:
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
    reused_blocks: tuple
    unsafe_va: int
    request_sites: tuple
    request_returns: tuple
    line_post_returns: tuple


@dataclass(frozen=True)
class BattleProfileLineReplayBundle:
    emission: CodeEmission
    primitive_bundle: object
    metadata_json: str
    hook_sites: tuple = ()
    removed_highlow_rvas: tuple = ()

    def metadata(self): return json.loads(self.metadata_json)


def _require(ok, message):
    if not ok: raise ValueError(message)


def _sha(data): return hashlib.sha256(data).hexdigest()


def _load_primitive(raw):
    _require(_sha(raw) == PRIMITIVE_SHA, 'fixed primitive source required')
    name = '_line_frozen_' + uuid.uuid4().hex
    module = types.ModuleType(name); module.__file__ = str(ROOT/PRIMITIVE)
    sys.modules[name] = module
    try: exec(compile(raw, module.__file__, 'exec'), module.__dict__)
    finally:
        if sys.modules.get(name) is not module:
            raise ValueError('frozen primitive namespace identity changed')
        del sys.modules[name]
    return module


def _snapshot():
    _require(Path(__file__).resolve() == ROOT/SOURCE, 'canonical line producer required')
    target = ROOT/PRIMITIVE
    raw = target.read_bytes()
    _require(_sha(raw) == PRIMITIVE_SHA, 'frozen primitive producer differs')
    module = _load_primitive(raw)
    snapshot = module._snapshot()
    _require(_sha(snapshot[PRIMITIVE][0]) == PRIMITIVE_SHA, 'primitive changed during snapshot')
    path = ROOT/SOURCE
    _require(path.resolve(strict=True) == path and path.is_relative_to(ROOT), 'noncanonical line source')
    before = path.stat(); data = path.read_bytes(); after = path.stat()
    stamp = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns)
    _require(stamp(before) == stamp(after), 'line source changed while read')
    snapshot[SOURCE] = data, stamp(after)
    return snapshot


@contextmanager
def _modules(snapshot):
    primitive = _load_primitive(snapshot[PRIMITIVE][0])
    with primitive._modules(snapshot) as modules:
        old = modules[PRIMITIVE]
        name = old.__package__ + '.battle_profile_line_replay'
        module = types.ModuleType(name)
        module.__file__ = str(ROOT/SOURCE); module.__package__ = old.__package__
        module.__loaded_source_sha256__ = _sha(snapshot[SOURCE][0])
        module.__canonical_line_issuer__ = True
        sys.modules[name] = module
        setattr(sys.modules[old.__package__], 'battle_profile_line_replay', module)
        try:
            exec(compile(snapshot[SOURCE][0], module.__file__, 'exec'), module.__dict__)
            modules[SOURCE] = module
            yield modules
        finally:
            if sys.modules.get(name) is not module:
                raise ValueError('private line namespace identity changed')
            del sys.modules[name]
            package = sys.modules.get(old.__package__)
            if package is not None and getattr(package,'battle_profile_line_replay',None) is module:
                delattr(package,'battle_profile_line_replay')


def _replace(text, old, new):
    _require(text.count(old) == 1, 'fixed line composition boundary differs: ' + old[:70])
    return text.replace(old, new)


def _guard_factory(primitive, content, source, continuation):
    # Recompose the one authenticated guard. An external CALL to a frozen
    # private helper cannot establish the new intrinsic return-PC authority.
    captured = {}
    class Capture:
        def __call__(self, text, filename, mode):
            captured['text'] = text
            return compile(text, filename, mode)
    tree = ast.parse((ROOT/PRIMITIVE).read_bytes())
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == '_request_guard')
    scope = dict(primitive.__dict__); scope['compile'] = Capture()
    exec(compile(ast.get_source_segment((ROOT/PRIMITIVE).read_text(), node),
        str(ROOT/SOURCE) + ':guard_factory', 'exec'), scope)
    scope['_request_guard'](content, source, continuation)
    text = captured['text']
    text = _replace(text, 'admission_sites,thunk_returns):', 'admission_sites,thunk_returns,line_post_returns):')
    text = _replace(text,
        "        get(0,512);cmpva(0,thunk_returns[number],'source-owned intrinsic thunk CALL return PC');ne(reject)",
        "        get(0,512)\n"
        "        if number in (85,86):\n"
        "            cmpva(0,thunk_returns[number],'source-owned intrinsic line pre CALL return PC');eq(f'line.intrinsic.{number}')\n"
        "            cmpva(0,line_post_returns[number-85],'source-owned intrinsic line post CALL return PC');ne(reject)\n"
        "            a.label(f'line.intrinsic.{number}')\n"
        "        else:cmpva(0,thunk_returns[number],'source-owned intrinsic thunk CALL return PC');ne(reject)")
    # Older post-return adapters permit a coherent loss receipt so they can
    # finish their scoped return. A replay must admit zero loss after all
    # fixed/Thread/control comparisons, before cached surface/WORLD reads.
    text = _replace(text,
        "    a.emit('55');get(5,FIELD_EBP);call(field_check,'private current V2 complete content receipt');a.emit('5d');cmp(0,1);ne(reject)",
        "    get(0,SITE);cmp(0,85);a.branch('0f82','line.loss.gate.done')\n"
        "    get(7,LEASE_EBP);load(0,7,44);a.emit('85c0');ne(reject)\n"
        "    a.label('line.loss.gate.done')\n"
        "    a.emit('55');get(5,FIELD_EBP);call(field_check,'private current V2 complete content receipt');a.emit('5d');cmp(0,1);ne(reject)")
    env = dict(content.__dict__); env['REQUEST_SITES'] = primitive.REQUEST_SITES
    exec(compile(text, str(ROOT/SOURCE) + ':shared_guard', 'exec'), env)
    return env['_emit_guard']


def _append_replays(a, base, content_emission, admissions, thunk_returns, local_calls, clip, width):
    # The fixed private primitive producer is loaded from its pinned snapshot;
    # only this authored version changes the two owning line-thunk tails.
    source = (ROOT/PRIMITIVE).read_bytes()
    module = _load_primitive(source)
    tree = ast.parse(source)
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == '_append_requests')
    text = ast.get_source_segment(source.decode(), node)
    text = _replace(text, '    returns=[]', '    returns=[];line_posts=[]')
    text = _replace(text,
        "        mem('89',2,4,100);a.label('request.return.'+str(i))\n"
        "        returns.append(base+len(a.code));a.emit('83c450619dc3')",
        "        a.label('request.return.'+str(i));returns.append(base+len(a.code))\n"
        "        if kind=='line':\n"
        "            _line_tail(a,base,i,local_calls,clip,line_posts)\n"
        "        else:mem('89',2,4,100);a.emit('83c450619dc3')")
    text = _replace(text,
        "    call('admit_body');cmp(0,1);branch('0f85','request.unsafe')",
        "    call('admit_body');cmp(0,1);branch('0f85','request.unsafe')\n"
        "    get(0,224);put(0,680);imm(0,1);put(0,684)")
    text = _replace(text, '    return tuple(returns)',
        "    _append_post_helper(a,base,content_emission,local_calls,clip)\n"
        "    return tuple(returns),tuple(line_posts)")
    env = dict(module.__dict__)
    env.update(_line_tail=_line_tail, _append_post_helper=_append_post_helper)
    exec(compile(text, str(ROOT/SOURCE) + ':request_tails', 'exec'), env)
    return env['_append_requests'](a, base, content_emission, admissions, thunk_returns, local_calls, clip, width)


def _line_tail(a, base, index, local_calls, clip, posts):
    label = 'line.' + str(index)
    def branch(op, target): a.branch(op, target)
    def call(target):
        a.emit('e8'); at = len(a.code); a.u32(0)
        a.fixups.append((at, target)); local_calls.append((at, target))
    # Prepared, Empty, malformed/fault are distinct. Unknown values cannot
    # authorize a native call or a normal native cleanup.
    a.emit('83fa01'); branch('0f84', label+'.prepared')
    a.emit('83fa03'); branch('0f84', label+'.complete')
    a.emit('83fa02'); branch('0f84', label+'.fault')
    a.emit('83fa04'); branch('0f85', 'request.unsafe')
    a.label(label+'.fault'); a.emit('ba02000000'); branch('e9', 'fault_dispatch')
    a.label(label+'.prepared')
    # Record fields + own ESP16: receiver20, clipped X/Y/endX/endY32..44,
    # exact colorFlags48. Original caller arguments remain above the thunk.
    a.emit('8b4424248b5424308b5c24348b4c2438ff742440ff742440fc')
    a.emit('e8'); at = len(a.code)
    a.relocations.append(clip.Relocation(at, 'rel32', LINE_TARGET, 'closed native memory-line replay'))
    a.u32(LINE_TARGET-base-at-4)
    a.label(label+'.native_return')
    # Native RET8 completed once. Preserve all native output registers/flags
    # separately from the post-helper's EAX/EDX result. MOVs preserve flags.
    a.emit('8944246c9c5889442470897c245089742454896c2458895c246089542464894c24688b44246c')
    call('line.post_helper'); posts.append(base+len(a.code))
    a.emit('83fa01'); branch('0f85', 'request.unsafe')
    a.label(label+'.complete')
    # Consume the genuine own CALL return plus the original native8B args.
    # This is a fixed admitted continuation, not a borrowed unwinding jump.
    a.emit('83c450619d8d64240c')
    if index == 11:
        a.emit('e9'); at = len(a.code)
        a.relocations.append(clip.Relocation(at, 'rel32', 0x430831, 'exact horizontal Tile continuation'))
        a.u32(0x430831-base-at-4)
    else:
        a.emit('89ec5d5f5e595bc3')


def _append_post_helper(a, base, content_emission, local_calls, clip):
    def mem(op, reg, off): a.emit(op+f'{0x85|(reg<<3):02x}'); a.u32(off)
    a.label('line.post_helper'); a.emit('9c60fc81ec'); a.u32(640); a.emit('89e5')
    a.emit('e8'); at = len(a.code); target = dict(content_emission.private_entries)['capture_inputs']
    a.relocations.append(clip.Relocation(at, 'rel32', target, 'fixed native-output input capture'))
    a.u32(target-base-at-4)
    mem('8b', 0, 688); mem('89', 0, 200)
    a.emit('8d85'); a.u32(796); mem('89', 0, 208)
    a.emit('e8'); at = len(a.code); a.u32(0)
    a.fixups.append((at, 'admit_body')); local_calls.append((at, 'admit_body'))
    a.emit('83f801'); a.branch('0f85', 'request.unsafe')
    # This is control/current-invocation admission only. Native-result EAX is
    # never classified as a surface or request receiver after the native call.
    mem('8b', 0, 224); mem('89', 0, 680)
    a.emit('b801000000'); mem('89', 0, 684)
    mem('8b', 0, 428); a.emit('ba01000000')
    last = dict(content_emission.entries)['site_426f54']-content_emission.base_va
    denied = last+69+struct.unpack_from('<i', content_emission.code, last+65)[0]
    finish = denied+10+struct.unpack_from('<i', content_emission.code, denied+6)[0]
    a.emit('e9'); at = len(a.code); target = content_emission.base_va+finish
    a.relocations.append(clip.Relocation(at, 'rel32', target, 'fixed640B native-output helper finish'))
    a.u32(target-base-at-4)


def _compose(modules, snapshot, plan, checked, lease, field, assembler):
    primitive = modules[PRIMITIVE]
    tree = ast.parse(snapshot[PRIMITIVE][0])
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == '_compose')
    text = ast.get_source_segment(snapshot[PRIMITIVE][0].decode(), node)
    text = _replace(text, 'request_returns=_append_requests(', 'request_returns,line_post_returns=_append_requests(')
    text = _replace(text,
        'REQUEST_SITES,request_returns)\")', 'REQUEST_SITES,request_returns,line_post_returns)\")')
    text = _replace(text,
        "        '_request_guard(content,snapshot[CONTENT][0],continuation_authority)')",
        "        '_line_guard(content,snapshot[CONTENT][0],continuation_authority)')\n"
        "    text=_replace(text,'thunk_returns=tuple(thunk_returns))','thunk_returns=tuple(thunk_returns),line_post_returns=line_post_returns)')")
    text = _replace(text,
        'env.update(CodeEmission=CodeEmission,_append_requests=_append_requests,_request_guard=_request_guard,',
        'env.update(CodeEmission=CodeEmission,_append_requests=_append_replays,_line_guard=_line_guard,')
    text = _replace(text, "('request_helper',base+a.labels['request.helper']),",
        "('line_post_helper',base+a.labels['line.post_helper']),('request_helper',base+a.labels['request.helper']),")
    # _compose generates another fixed source function: each replacement must
    # land at its whole authenticated predecessor source boundary.
    env = dict(primitive.__dict__)
    env.update(CodeEmission=CodeEmission, _append_replays=_append_replays,
        _line_guard=lambda content, source, continuation: _guard_factory(primitive, content, source, continuation))
    exec(compile(text, str(ROOT/SOURCE)+':line_composition', 'exec'), env)
    out = env['_compose'](modules, snapshot, plan, checked, lease, field, assembler)
    _require(len(out.line_post_returns) == 2 and len(set(out.line_post_returns)) == 2, 'two genuine post-line PCs required')
    overlaps = tuple(h for h in out.planned_hooks if h[0] in REMOVED_OVERLAPS)
    _require(tuple(h[0] for h in overlaps) == REMOVED_OVERLAPS and all(not h[4] for h in overlaps),
        'fixed overlapping post-hook inventory differs')
    hooks = tuple(h for h in out.planned_hooks if h[0] not in REMOVED_OVERLAPS)
    hooks += tuple((pc, bytes.fromhex(raw), dict(out.entries)['adapter_'+str(85+i)], 'line_replay', ())
        for i, (pc, raw, _) in enumerate(LINE_WINDOWS))
    _require(len({h[0] for h in hooks}) == len(hooks), 'duplicate line hook start')
    intervals = sorted((pc, pc+len(raw)) for pc, raw, *_ in hooks)
    _require(all(end <= start for (_, end), (start, _) in zip(intervals, intervals[1:])), 'overlapping successor hook windows')
    _require(out.base_va+len(out.code) <= plan['rx']['va']+0x20000, 'line replay exceeds unchanged RX reservation')
    assembler.absolute_relocation_offsets(out)
    return replace(out, planned_hooks=hooks)


def _emit_code(plan, content_emission, lease_emission, field_emission, *, assembler_module):
    """Pure synthetic boundary; the public API independently rebuilds parents."""
    snapshot = _snapshot()
    with _modules(snapshot) as modules:
        out = modules[SOURCE]._compose(modules, snapshot, plan, content_emission,
            lease_emission, field_emission, assembler_module)
    _require(_snapshot() == snapshot, 'line sources changed during composition')
    return out


def _authenticate_native(original, candidate, modules):
    primitive = modules[PRIMITIVE]; primitive._authenticate_native(original, candidate, modules)
    clip = modules['src/patcher/partial_tile_clip.py']; pe = modules['src/patcher/pe_extension.py']
    for image in (original, candidate):
        parsed = pe.inspect_pe(image); _, relocs = pe._old_relocations(image, parsed)
        for name, lo, hi, digest in NATIVE_SPANS:
            at = clip.file_offset(image, lo, hi-lo)
            _require(_sha(image[at:at+hi-lo]) == digest, 'closed line native span differs: '+name)
            expected = tuple(range(0x10EE24, 0x10EE60, 4)) if name == 'memory_vtable' else ()
            _require(tuple(sorted(r for r in relocs if lo <= parsed.image_base+r < hi)) == expected,
                'closed line span HIGHLOW inventory differs: '+name)
        for pc, raw, _ in LINE_WINDOWS:
            raw = bytes.fromhex(raw); at = clip.file_offset(image, pc, len(raw))
            _require(image[at:at+len(raw)] == raw, 'whole native line CALL/continuation window differs')
            _require(not any(pc <= parsed.image_base+r < pc+len(raw) for r in relocs), 'unexpected line-window relocation')


def _emit_authenticated(original, profile, resolution):
    snapshot = _snapshot()
    _require(globals().get('__loaded_source_sha256__') == _sha(snapshot[SOURCE][0]), 'private line producer required')
    _require(type(original) is bytes and _sha(original) == BASE_SHA256, 'exact original required')
    with _modules(snapshot) as modules:
        predecessor = modules[PRIMITIVE].emit_battle_profile_primitive_request(original, profile, resolution)
        old = predecessor.metadata(); plan = old['allocation_plan']
        context = modules['src/patcher/battle_profile_context.py'].build_parent_context(original, profile, resolution)
        _require(context.allocation_plan() == plan, 'independent line parent/allocation required')
        _authenticate_native(original, context.candidate, modules)
        checked = predecessor.continuation_bundle.content_bundle
        clip = modules['src/patcher/partial_tile_clip.py']
        out = _compose(modules, snapshot, plan, checked.emission, checked.lease_bundle.emission,
            checked.lease_bundle.field_bundle.emission, clip)
        metadata = dict(schema='clash95_battle_profile_line_replay_v1', profile=profile, resolution=resolution,
            original_sha256=BASE_SHA256, parent_candidate_sha256=plan['candidate_sha256'], allocation_plan=plan,
            source_hashes=old['source_hashes'] | {n:_sha(raw) for n,(raw,_) in snapshot.items()},
            predecessor_code_sha256=_sha(predecessor.emission.code), code_va=out.base_va,
            code_bytes=len(out.code), code_sha256=_sha(out.code),
            rx_used_bytes=out.base_va+len(out.code)-plan['rx']['va'],
            rx_remaining_bytes=plan['rx']['va']+0x20000-out.base_va-len(out.code),
            helper_frame_bytes=640, thunk_frame_bytes=116, request_frame_bytes=64,
            callback_snapshot_bytes=864, maximum_owned_helper_stack_extent=1712,
            field_frame_bytes=1280, lease_frame_bytes=192, owner_page_bytes=4096,
            native_line_replay_emitted=True, baseline_scalar_continuation_replay_emitted=True,
            closed_memory_line_normal_return_source_verified=True, physical_line_receiver_checked=True,
            synthetic_pixel_oracle_only=True, original_native_body_executed_by_fixture=False,
            preparation_only=True, native_line_target=LINE_TARGET, native_line_ret_bytes=8,
            statuses=dict(prepared=1, malformed=2, empty=3, receiver_fault=4),
            empty_behavior='no native invocation; retain incoming registers/flags and follow admitted fixed Tile continuation',
            failure_behavior='malformed/receiver fault latches owned loss and executes resource-free Tile epilogue; unknown control/current receipt stops exact UD2',
            removed_overlapping_post_hook_starts=list(REMOVED_OVERLAPS),
            removed_highlow_rvas=[], line_post_returns=list(out.line_post_returns),
            line_intrinsic_pre_returns=list(out.request_returns[-2:]),
            line_native_return_pcs=[out.base_va+r.offset+4 for r in out.relocations
                if r.kind=='rel32' and r.target==LINE_TARGET],
            original_arguments_preserved=True, native_arguments='clipped request coordinates; exact original color flags; private duplicate native8B arguments',
            line_windows=[dict(pc=pc, old_bytes=raw, original_return_pc=pc+3, genuine_outer_return_pc=pc+5,
                normal_continuation=continuation) for pc,raw,continuation in LINE_WINDOWS],
            native_spans=[dict(name=n,start=lo,end=hi,sha256=d) for n,lo,hi,d in NATIVE_SPANS],
            planned_hooks=[dict(va=pc, old_bytes=raw.hex(), role=role, target_va=target,
                new_bytes=(b'\xe8'+struct.pack('<i',target-pc-5)+b'\x90'*(len(raw)-5)).hex(),
                removed_highlow_rvas=list(rs)) for pc,raw,target,role,rs in out.planned_hooks],
            limitations=[
                'No hook, candidate, field substitution or complete battle family is installed.',
                'Only the two owned physical memory-line requests replay a native primitive; sprites/RLE/providers remain unadmitted.',
                'Fixtures intercept the native target and model pixels/outputs/RET8; no original native body or Windows runtime was executed.',
                'The native memory-line normal closure has no provider/allocator/OS callback; added Thread queries retain complete fixed/control/current receipts.',
                'A clipped-empty request is an explicit new no-write disposition, not original native output parity.',
                'Resource-free Tile epilogue admission is not healthy map return, render restoration, fatal shutdown or process-quit closure.',
                'Unknown ancestry, stack/control mutation and current-receipt loss stop UNSAFE; there is no partial-write fallback.',
                'Cross-thread immutability, native content producer invariants, presentation/input/camera/animations/dialogs and atomic installation remain unproved.',
            ], **{name:False for name in FALSE_CLAIMS})
    _require(_snapshot() == snapshot, 'line sources changed during public emission')
    return BattleProfileLineReplayBundle(out, predecessor, json.dumps(metadata, sort_keys=True, separators=(',',':'), allow_nan=False))


def emit_battle_profile_line_replay(original, profile, resolution):
    # Private source namespaces need only _emit_authenticated. A namespace
    # that suppresses bootstrap must never obtain a public bypass dispatcher.
    raise ValueError('captured canonical line production factory required')


def _production_factory():
    # Capture canonical source authority once. Public helper aliases and
    # constants are deliberately absent from the returned dispatch path.
    from hashlib import sha256 as digest
    from pathlib import Path as SourcePath
    from types import ModuleType as SourceModule
    from uuid import uuid4 as unique_name
    from sys import modules as registry
    exact_type, exact_bytes, rejection = type, bytes, ValueError
    compile_source, execute_source = compile, exec
    path = SourcePath(__file__).resolve(strict=True)
    root = path.parents[2]
    if path != root/'src/patcher/battle_profile_line_replay.py':
        raise rejection('canonical line producer required')

    def read_source():
        before = path.stat(); raw = path.read_bytes(); after = path.stat()
        def stamp(value):
            return value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns
        if stamp(before) != stamp(after):
            raise rejection('canonical line source changed while read')
        return raw, stamp(after)

    source, initial_stamp = read_source()
    source_digest = digest(source).hexdigest()
    name = '_line_canonical_issuer_' + unique_name().hex
    module = SourceModule(name)
    module.__file__ = str(path)
    module.__loaded_source_sha256__ = source_digest
    module.__canonical_line_issuer__ = True
    registry[name] = module
    try:
        execute_source(compile_source(source, str(path), 'exec'), module.__dict__)
        issuer = module.__dict__['_emit_authenticated']
    finally:
        if registry.get(name) is not module:
            raise rejection('canonical line issuer module identity changed')
        del registry[name]
    if read_source() != (source, initial_stamp):
        raise rejection('canonical line source changed during factory capture')
    original_digest = '500055d77d03d514e8d3168506bd10f67cd8569bcc450604ff8192f46cdaf3ae'

    def dispatch(original, profile, resolution):
        if exact_type(original) is not exact_bytes or digest(original).hexdigest() != original_digest:
            raise rejection('exact original required')
        raw, stamp = read_source()
        if digest(raw).hexdigest() != source_digest:
            raise rejection('captured canonical line source differs')
        try:
            result = issuer(original, profile, resolution)
        finally:
            if read_source() != (raw, stamp):
                raise rejection('canonical line source changed during dispatch')
        return result
    return dispatch


if not globals().get('__canonical_line_issuer__', False):
    emit_battle_profile_line_replay = _production_factory()
