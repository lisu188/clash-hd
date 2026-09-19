#!/usr/bin/env python3
"""Prepare a source-bound primary-stage barracks probe; never run the game.

The pinned predecessor supplies only pure native route/owned-canvas command
builders. The actual primary manifest, full-image contract and checkpoints
are reconstructed separately. All new observers read native state; the only
target writes remain the explicitly disclosed inherited controlled route.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import re
import struct
from types import SimpleNamespace

import build_framed_modal_primary_candidate as builder
import modal_slots_barracks_probe as inherited
from modal_primary_candidate_context import load_context
from src.patcher import framed_modal_canvas as canvas
from render_cdb_surface_probe import BASE_PROBE, FRAMED_STAGE as MAP_STAGE, render_probe

STAGE = builder.STAGE
PROTOCOL_REVISION = 'primary_barracks_owned_canvas_v1'
HELPER_SOURCE = 'tools/modal_slots_barracks_probe.py'
HELPER_SHA256 = '2d82a009fa38e33bcc74483d2b9b479934f8a5ce20e37a6e99c7c5e84efb32f3'
CAPTURE_SOURCES = ('tools/modal_primary_candidate_context.py', 'tools/modal_primary_barracks_probe.py',
    'tools/modal_primary_barracks_trace.py', 'tools/modal_primary_initial_trace.py',
    'tools/render_cdb_surface_probe.py', 'tools/initial_map_paint_trace.py',
    'scripts/cdb/run_cdb_surface_dump.ps1', 'scripts/cdb/run_modal_primary_capture.ps1',
    HELPER_SOURCE)
ROUTES, PENDING, COMMON = inherited.ROUTES, inherited.PENDING, inherited.COMMON
DUMP_TOKEN, IMAGE_BASE, PRESENT, SENTINEL = inherited.DUMP_TOKEN, inherited.IMAGE_BASE, inherited.PRESENT, inherited.SENTINEL
ARTWORK_CALLS, BLIT_CALLS, LOAD_CALLS = inherited.ARTWORK_CALLS, inherited.BLIT_CALLS, inherited.LOAD_CALLS
_printf, _read, _native_spans, _reject = inherited._printf, inherited._read, inherited._native_spans, inherited._reject
LIMITS = inherited.LIMITS + [
    'Primary-stage observations are separate from predecessor slots proof; no old-stage packet or trace is relabeled.',
    'Four paused checkpoints observe native publication, the initial unselected placeholder call and first presentation only.',
    'The first checkpoint precedes all twelve slot copies; it is deliberately an incomplete barracks screen.',
    'The selected panel, other modal routes, ordinary input, cursor movement, exit and promotion are unproven.',
    'New breakpoints assign debugger pseudo-registers only. Native helper calls, cursor state, pixels and target registers are never synthesized.',
]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def check_helpers():
    if sha((builder.ROOT / HELPER_SOURCE).read_bytes()) != HELPER_SHA256:
        raise ValueError('frozen native route helper changed')


def _guard(test, body, reason):
    return '.if (' + test + ') { ' + body + ' } .else { .echo MPCAP_REJECT reason=' + reason + '; q }'


def primary_observers(manifest, candidate):
    """Use declared relocation identities, then verify every installed CALL."""
    entries, code = manifest['primary_entry_vas'], manifest['code_va']
    def calls(purpose, target, count):
        rows = [r for r in manifest['relocations'] if r['purpose'] == purpose]
        if len(rows) != count:
            raise ValueError('primary observer relocation count differs: ' + purpose)
        result = []
        for row in rows:
            if row['kind'] != 'rel32' or row['target'] != target:
                raise ValueError('primary observer relocation target differs')
            va = code + row['offset'] - 1
            if _read(candidate, va, 5)[1] != b'\xe8' + struct.pack('<i', target-va-5):
                raise ValueError('primary observer CALL bytes differ')
            result.append(va)
        return sorted(result)
    remove, = calls('native cursor remove before full copy', 0x460F90, 1)
    draw, = calls('native cursor capture and redraw after full copy', 0x460EA0, 1)
    direct, cursor = calls('original HD blitter on physical mirror', 0x4E9920, 2)
    if not direct < remove < cursor < draw:
        raise ValueError('primary native publication layout differs')
    if (_read(candidate,direct+5,2)[1] != b'\x58\xc3'
            or _read(candidate,draw+5,3)[1] != b'\x61\x9d\xc3'
            or _read(candidate,0x432F9E,3)[1] != b'\xff\x56\x34'):
        raise ValueError('primary return or placeholder native instruction differs')
    return dict(full_entry=entries['full_blit'], full_fallback=entries['full.fallback'],
        remove_call=remove, remove_entry=0x460F90, remove_return=remove+5,
        publish_call_direct=direct, publish_return_direct=direct+5,
        publish_call_cursor=cursor, publish_return_cursor=cursor+5, publish_entry=0x4E9920,
        draw_call=draw, draw_entry=0x460EA0, draw_return=draw+5,
        full_return_direct=direct+6, full_return_cursor=draw+7,
        cursor_rect=0x460BB0, placeholder_before=0x432F9E, placeholder_after=0x432FA1)


def checkpoint_contract(observers):
    if any(type(value) is not int or not 0 < value < 2**32 for value in observers.values()):
        raise ValueError('primary observer addresses must be exact positive 32-bit integers')
    return [dict(name=name,index=index,eips=eips) for index,(name,eips) in enumerate((
        ('full-published',[observers['publish_return_direct'],observers['publish_return_cursor']]),
        ('placeholder-before',[observers['placeholder_before']]),
        ('placeholder-after',[observers['placeholder_after']]),('final-ready',[0x433E77])))]


def _event(name):
    return _printf('MPCAP_EVENT event='+name+' tid=%x eip=%p esp=%p full_esp=%p '
        'route_state=%d cursor=%d eax=%p caller=%p parent=%p',
        '@$tid','@eip','@esp','@$t8','@$t0','poi(00544d10)','@eax','poi(@esp)','poi(@$t8)')


def _checkpoint_records(metadata, width, height, name, index):
    state=metadata['state_va']; at=lambda field:f'poi({state+canvas.STATE[field]:08x})'
    record = inherited._canvas_record(metadata,'CHECKPOINT') + '; ' + _printf(
        f'MPCAP_CHECKPOINT name={name} index={index} tid=%x eip=%p esp=%p '
        'surface=%p size=(%d,%d) base=%p bytes=%d owner=%p render=%p cursor=%d',
        '@$tid','@eip','@esp',at('physical'),f'0n{width}',f'0n{height}',at('physical_pixels'),
        f'0n{width*height}','@$t1','poi(00511230)','poi(00544d10)')
    return inherited._canvas_guard(metadata,width,height,record,mirrors=3)


def checkpoint_script(packet, name):
    """Canonical read-only prefix for the adapter's four quiet command files.

    Keeping these commands outside quoted breakpoints preserves CDB's hard
    4096-byte input-line bound, including the inherited final readiness body.
    The adapter must bind all four complete files and insert each before the
    corresponding HOST_READY marker. The request alone never permits capture.
    """
    expected=checkpoint_contract(packet['primary_observers'])
    declared=packet.get('checkpoints')
    if (not isinstance(declared,list) or declared != expected
            or any(type(item.get('index')) is not int or not isinstance(item.get('eips'),list)
                   or any(type(value) is not int for value in item['eips']) for item in declared)):
        raise ValueError('primary checkpoint contract differs')
    matches=[item for item in expected if item['name']==name]
    if len(matches)!=1:raise ValueError('unsupported primary checkpoint')
    item=matches[0];width,height=map(int,packet['resolution'].split('x'))
    eip=' | '.join(f'(@eip == {value:08x})' for value in item['eips'])
    body=_checkpoint_records({'state_va':packet['canvas_state_va']},width,height,name,item['index'])
    body=_guard(f'(@$t19 == 0n{item["index"]+1}) & ({eip})',body,'checkpoint_script_context')
    return body.replace(r'\\n',r'\n').replace(r'\"','"')+'\n'


def _checkpoint(metadata, width, height, name, index):
    return f'.echo MPCAP_CHECKPOINT_REQUEST name={name}; .echo MPCAP_HOST_READY name={name}'


def _commands(route, width, height, castle_index, availability, metadata):
    handoff, commands = inherited._commands(route,width,height,castle_index,availability,metadata)
    obs=metadata['primary_observers']; state=metadata['state_va']
    native=f'poi({state+canvas.STATE["native"]:08x})'
    physical=f'poi({state+canvas.STATE["physical"]:08x})'
    # The nearly full original map handoff line is untouched. Arm additions
    # at the already authenticated overview prologue, before any full blit.
    route_test='((@$t0 == 2) & (@$t9 == 9)) | ((@$t0 == 8) & (@$t9 == 0n14))'
    full_test=f'(@$tid == @$t2) & ({route_test})'
    extra={}
    next_id=103
    def add(key,body):
        nonlocal next_id
        if next_id==110:next_id=112
        if any(va==obs[key] for va,_ in commands.values()) or any(va==obs[key] for va,_ in extra.values()):
            raise ValueError('primary observer VA collides with existing breakpoint')
        extra[next_id]=(obs[key],_guard(f'@eip == {obs[key]:08x}',body,'observer_eip'))
        next_id+=1
    def event(key,name,phase,next_phase,depth,condition='1',tail='gc'):
        test=f'({full_test}) & (@$t18 == 0n{phase}) & (@esp == (@$t8-0n{depth})) & ({condition})'
        body=_event(name)+f'; r @$t18=0n{next_phase}; '+tail
        add(key,_guard(test,body,name.replace('-','_')))
    entry=_guard(f'({full_test}) & (@$t18 == 0) & (@esp == @$t8) & (@eax == {native}) & (poi(00544d10) <= 1)',
        inherited._canvas_guard(metadata,width,height,_event('full-entry')+'; r @$t18=1; gc',mirrors=(0,2)),'full_entry')
    add('full_entry',entry)
    event('remove_call','remove-call',1,2,36,'(@eax == 00544cd8) & (poi(00544d10) == 1)')
    event('remove_return','remove-return',20,3,36,'poi(00544d10) == 0')
    for kind,phase in (('direct',1),('cursor',3)):
        event('publish_call_'+kind,'publish-call',phase,4,4,f'(@eax == {physical}) & (poi(00544d10) == 0)')
        stop=_guard('(@$t19 == 0) & (@$t0 == 8)',
            'r @$t19=1; '+_checkpoint(metadata,width,height,'full-published',0),'first_checkpoint')
        event('publish_return_'+kind,'publish-return',40,5,4,
              f'(@eax == {physical}) & (poi(00544d10) == 0)',
              '.if (@$t0 == 8) { '+stop+' } .else { gc }')
    event('draw_call','draw-call',5,6,36,'(@eax == 00544cd8) & (poi(00544d10) == 0)')
    event('draw_return','draw-return',60,7,36,'poi(00544d10) == 1')
    event('full_return_direct','full-return',5,0,0,f'(@eax == {native}) & (poi(00544d10) == 0)')
    event('full_return_cursor','full-return',7,0,0,f'(@eax == {native}) & (poi(00544d10) == 1)')
    # These shared native entries only belong to this adapter when their
    # actual return word is one of its exact source-derived continuations.
    # Ordinary native callers remain covered by the inherited route/Lock lane.
    for key,name,phase,next_phase,depth,returns,eax in (
        ('remove_entry','remove-entry',2,20,40,[obs['remove_return']],'00544cd8'),
        ('publish_entry','publish-entry',4,40,8,[obs['publish_return_direct'],obs['publish_return_cursor']],physical),
        ('draw_entry','draw-entry',6,60,40,[obs['draw_return']],'00544cd8')):
        caller=' | '.join(f'(poi(@esp) == {va:08x})' for va in returns)
        observed=_guard(f'({full_test}) & (@$t18 == 0n{phase}) & (@esp == (@$t8-0n{depth})) & (@eax == {eax})',
            _event(name)+f'; r @$t18=0n{next_phase}; gc',name.replace('-','_'))
        add(key,f'.if ({caller}) {{ {observed} }} .else {{ gc }}')
    add('full_fallback',_guard(f'(@$t18 == 0) & (poi(@esp+1c) != {native})','gc','owned_full_blit_fallback'))
    # The initial route must remain unselected. Cursor bounds have already
    # passed through the emitted active adapter when this native entry fires.
    dx,dy=(width-640)//2,(height-480)//2
    resource='poi(00532144)'; sprite=f'poi({resource}+64)'
    # x86 CDB can sign-extend poi's stored DWORD -1 to ULONG64 while the
    # user-mode literal remains unsigned. Compare the exact native DWORD.
    admission=f'(@$tid == @$t2) & (@$t0 == 8) & (@$t9 == 0n15) & (@$t18 == 0) & (@$t19 == 1) & ((poi(00532188) & 0x00000000ffffffff) == 0xffffffff)'
    rect=_printf('MPCAP_CURSOR_RECT tid=%x eip=%p esp=%p eax=%p x=%d right=%d y=%d bottom=%d caller=%p cursor=%d',
        '@$tid','@eip','@esp','@eax','@edx','@ecx','@ebx','poi(@esp+4)','poi(@esp)','poi(00544d10)')
    # Attempt A reached this caller but the compact rejection did not record
    # which admission/argument clause failed. Observe bounded scalar operands
    # only after rejection; never follow an unvalidated heap pointer.
    rect_context=_printf('MPCAP_CURSOR_RECT_CONTEXT tid=%x eip=%p esp=%p ebp=%p eax=%p '
        'x=%d right=%d y=%d bottom=%d caller=%p expected_tid=%x root_esp=%p '
        'route_state=%d canvas_phase=%d publish_phase=%d checkpoint_index=%d selected=%p '
        'cursor=%d resource=%p render=%p state_phase=%d state_fault=%d',
        '@$tid','@eip','@esp','@ebp','@eax','@edx','@ecx','@ebx','poi(@esp+4)','poi(@esp)',
        '@$t2','@$t3','@$t0','@$t9','@$t18','@$t19','poi(00532188)','poi(00544d10)',
        resource,'poi(00511230)',f'poi({state+canvas.STATE["phase"]:08x})',f'poi({state+canvas.STATE["fault"]:08x})')
    rect_test=f'({admission}) & (@esp == (@$t3-0n168)) & (@eax == 00544cd8) & (@edx == 0n{220+dx}) & (@ebx == 0n{289+dy})'
    rect_guard=_guard(rect_test,_guard(f'{resource} != 0',_guard(f'{sprite} != 0',
        _guard(f'(@ecx == (0n{220+dx}+wo({sprite}))) & (poi(@esp+4) == (0n{289+dy}+wo({sprite}+2)))',
               rect+'; gc','cursor_rect_extent'),'cursor_rect_sprite'),'cursor_rect_resource'),'cursor_rect')
    rejection='.echo MPCAP_REJECT reason=cursor_rect; q'
    if rect_guard.count(rejection)!=1:raise ValueError('unique cursor-rectangle rejection seam missing')
    rect_guard=rect_guard.replace(rejection,rect_context+'; '+rejection,1)
    add('cursor_rect',f'.if (poi(@esp) == 00432f61) {{ '+rect_guard+' } .else { gc }')
    placeholder=_printf('MPCAP_PLACEHOLDER tid=%x eip=%p esp=%p primary=%p vtable=%p sprite=%p resource=%p index=25 '
        'x=%d y=%d size=(%d,%d) parent=%p args=(%x,%x,%x,%x,%x,%x,%x)',
        '@$tid','@eip','@esp','@eax','@esi','@edx',resource,'@ebx','@ecx','wo(@edx)','wo(@edx+2)','poi(@ebp+18)',
        *[f'poi(@esp+0x{i*4:x})' for i in range(7)])
    args=' & '.join(f'((poi(@esp+0x{i*4:x}) & 0x00000000ffffffff) == 0xffffffff)' if i<4 else f'(poi(@esp+0x{i*4:x}) == 0)' for i in range(7))
    before_test=f'({admission}) & (@esp == (@$t3-0n188)) & (@ebp == (@$t3-0n116)) & (poi(@ebp+18) == 00433e4e) & (@eax == 0051d4c0) & (@esi == 0050eec4) & (@ebx == 0n{220+dx}) & (@ecx == 0n{289+dy}) & ({args})'
    before=_guard(before_test,_guard(f'{resource} != 0',_guard(f'({sprite} != 0) & (@edx == {sprite})',
        placeholder+'; r @$t19=2; '+_checkpoint(metadata,width,height,'placeholder-before',1),'placeholder_sprite'),'placeholder_resource'),'placeholder_before')
    add('placeholder_before',before)
    after_test='(@$tid == @$t2) & (@$t0 == 8) & (@$t9 == 0n15) & (@$t18 == 0) & (@$t19 == 2) & (@esp == (@$t3-0n160)) & (@ebp == (@$t3-0n116)) & (poi(@ebp+18) == 00433e4e)'
    add('placeholder_after',_guard(after_test,'r @$t19=3; '+_checkpoint(metadata,width,height,'placeholder-after',2),'placeholder_after'))
    ids=' '.join(str(number) for number in extra)
    va,body=commands[81]
    if body.count('r @$t0=2;')!=1:raise ValueError('unique overview arming seam missing')
    commands[81]=(va,body.replace('r @$t0=2;',f'r @$t0=2; r @$t18=0; r @$t19=0; be {ids};',1))
    va,body=commands[87]
    if body.count('; gc')!=1:raise ValueError('unique primary Lock arming seam missing')
    commands[87]=(va,body.replace('; gc','; .echo MPCAP_PRIMARY_OBSERVERS_ARM; gc',1))
    va,body=commands[89]
    token='.echo MCAP_SURFDUMP_HOST_READY'
    if body.count(token)!=1:raise ValueError('unique final checkpoint seam missing')
    final=_guard('(@$t18 == 0) & (@$t19 == 3)','r @$t19=4; '+_checkpoint(metadata,width,height,'final-ready',3),'final_checkpoint')
    body=body.replace(token,token+'; '+final,1)
    # Preserve each inherited rejection predicate and distinct reason while
    # reserving room for the adapter's bounded external command-file path.
    for reason in ('canvas_trace_incomplete','canvas_objects','canvas_ownership'):
        verbose=inherited._reject(reason)
        if body.count(verbose)!=1:raise ValueError('unique final rejection seam missing')
        body=body.replace(verbose,'.echo MPCAP_REJECT reason='+reason+'; q',1)
    commands[89]=(va,body)
    commands.update(extra)
    return handoff,commands


def canonical_template(original, resolution, *, candidate, candidate_manifest, minimap_viewport=True):
    check_helpers()
    if minimap_viewport is not True:raise ValueError('primary stage always includes minimap correction')
    context=load_context(original,candidate,candidate_manifest)
    manifest=context['manifest']
    if manifest['resolution']!=resolution:raise ValueError('candidate manifest resolution differs')
    slots=manifest['base_candidate']
    owner=slots['base_candidate']['predecessor']['base_candidate']
    metadata=dict(owner,source_sha256=manifest['source_hashes'],slots_metadata=slots,
        primary_metadata=manifest,primary_observers=primary_observers(manifest,candidate),
        manifest_binding=dict(path=context['manifest_path'],sha256=context['manifest_sha256']))
    extra=context['probe']
    template=render_probe(BASE_PROBE.read_text(encoding='utf-8-sig'),resolution,MAP_STAGE)['template']
    if len(re.findall(r'(?m)^g$',template))!=1 or not template.rstrip().endswith('\ng'):
        raise ValueError('canonical map template must have one final startup continuation')
    template=re.sub(r'(?m)^g$',lambda _:extra.strip()+'\ng',template)
    return candidate,metadata,extra,template



def build_screen_probe(original: bytes, candidate: bytes, *, candidate_sha256: str,
                       stage: str, resolution: str, route: str, availability: str,
                       castle_index: int, candidate_manifest: Path, rendered_probe: str | None = None, minimap_viewport: bool = True):
    if stage != STAGE:
        raise ValueError("exact framed validation stage required")
    if route != "barracks":
        raise ValueError("unsupported or pending route: " + PENDING.get(route, str(route)))
    if availability not in ("existing_flags", "construct_all"):
        raise ValueError("explicit existing_flags or construct_all availability required")
    if type(castle_index) is not int or not 0 <= castle_index <= 3:
        raise ValueError("only inspected castle indices0..3 are supported")
    if minimap_viewport is not True:
        raise ValueError("primary stage requires minimap_viewport to be exactly true")
    if not re.fullmatch(r"[0-9a-fA-F]{64}", candidate_sha256 or "") or sha(candidate) != candidate_sha256.lower():
        raise ValueError("candidate SHA-256 mismatch")
    rebuilt, metadata, extra, expected = canonical_template(original, resolution, candidate=candidate, candidate_manifest=candidate_manifest, minimap_viewport=minimap_viewport)
    if candidate != rebuilt:
        raise ValueError("candidate differs from exact framed reconstruction and options")
    if rendered_probe is not None and (not isinstance(rendered_probe, str) or rendered_probe.replace("\r\n", "\n") != expected):
        raise ValueError("expected unchanged canonical renderer template with unchanged standard extra")
    if expected.count(DUMP_TOKEN) != 1:
        raise ValueError("canonical template must have one unique dump-action token")
    check_helpers()
    selected = ROUTES[route]
    spans = dict(COMMON)
    for r in (ROUTES["castle_overview"], selected):
        if r.name != "castle_overview": spans[r.entry_va] = r.entry_bytes
        spans[r.present_call_va] = (b"\xe8" + struct.pack("<i", PRESENT - r.stop_va)).hex()
        spans[r.stop_va] = r.return_bytes
        if r.branch_va is not None:
            spans[r.branch_va] = (b"\xb9" + struct.pack("<I", r.entry_va)).hex()
    spans.update(_native_spans(selected))
    records, conditions = [], []
    for va, old_hex in sorted(spans.items()):
        old = bytes.fromhex(old_hex)
        if _read(original, va, len(old))[1] != old:
            raise ValueError(f"native source instruction span differs at{va:08x}")
        offset, new = _read(candidate, va, len(old))
        if new != old:
            raise ValueError(f"selected native observation span changed at{va:08x}")
        records.append(dict(va=va, rva=va-IMAGE_BASE, offset=offset, old_hex=old_hex, candidate_hex=new.hex()))
        conditions.extend(f"(by({va+i:08x}) != 0x{value:02x})" for i, value in enumerate(new))
    # These checks are top-level commands, outside a quoted breakpoint body.
    loaded_rejection = _reject('loaded_bytes').replace(r'\"', '"').replace(r'\\n', r'\n')
    byte_checks = "\n".join(f".if ({' | '.join(conditions[i:i+48])}) {{ {loaded_rejection} }}"
                             for i in range(0, len(conditions), 48)) + "\n"
    byte_checks += f".echo MCAP_BYTE_CONTRACT_PASS candidate_sha256={candidate_sha256.lower()} route={route}\n"
    profile = SimpleNamespace(width=int(resolution.split("x")[0]), height=int(resolution.split("x")[1]))
    handoff, commands = _commands(selected, profile.width, profile.height, castle_index, availability, metadata)
    # IDs80..90 are separate from the canonical implicit base and numbered
    # 70..77 observers. Reject a future expansion into those IDs or sites.
    implicit_count = 0
    for line in expected.splitlines():
        match = re.match(r'^bp\s*(?:(\d+)\s+)?([0-9a-fA-F]{8})\s+"', line)
        if not match:
            continue
        bp = int(match[1]) if match[1] else implicit_count
        if match[1] is None:
            implicit_count += 1
        if bp >= 80 or int(match[2], 16) in {va for va, _ in commands.values()}:
            raise ValueError("canonical breakpoint ID/site collides with modal probe")
    # The one canonical startup-animation token can add at most six implicit
    # breakpoints in the existing harness. Keep that expansion below our IDs.
    if implicit_count + 6 >= 80:
        raise ValueError("canonical startup breakpoint expansion reaches modal IDs")
    startup = (f".echo MCAP_CONTRACT stage={stage} resolution={resolution} candidate_sha256={candidate_sha256.lower()} "
               f"route={route} availability={availability} castle_index={castle_index} protocol={PROTOCOL_REVISION} runtime_acceptance=0\n")
    for bp, (va, body) in commands.items():
        startup += f'bp{bp} {va:08x} "{body}"\nbd {bp}\n'
    handoff_line = next(line for line in expected.splitlines() if DUMP_TOKEN in line)
    if any(len(line) >= 4096 for text in (byte_checks, startup, handoff_line.replace(DUMP_TOKEN, handoff)) for line in text.splitlines()):
        raise ValueError("modal command exceeds CDB4096-byte line limit")
    return dict(schema="clash95_modal_primary_probe_packet_v1", prepared=True, runtime_ready=False,
        stage=stage, resolution=resolution, protocol_revision=PROTOCOL_REVISION, candidate_sha256=sha(candidate), original_sha256=sha(original),
        minimap_viewport=minimap_viewport, source_sha256=metadata["source_sha256"],
        producer_sha256=sha(Path(__file__).read_bytes()), base_probe_sha256=sha(BASE_PROBE.read_bytes()),
        canonical_extra_sha256=sha(extra.encode("utf-8")), map_template_sha256=sha(expected.encode("ascii")),
        route=asdict(selected), stop_va=selected.stop_va, castle_index=castle_index, availability=availability,
        canvas_state_va=metadata["state_va"], canvas_state_offsets=metadata["modal_state_offsets"],
        canvas_observer_vas=metadata["modal_observer_vas"], canvas_entry_vas=metadata["modal_entry_vas"],
        canvas_revision=metadata['modal_native_canvas_revision'], builder_sha256=sha(Path(builder.__file__).read_bytes()),
        capture_source_hashes={name:sha((builder.ROOT/name).read_bytes()) for name in CAPTURE_SOURCES},
        candidate_manifest=metadata["manifest_binding"], recipe_revision=builder.REVISION,
        candidate_extra=extra, slot_entry_vas=metadata["slots_metadata"]["slot_entry_vas"],
        primary_observers=metadata["primary_observers"], primary_entry_vas=metadata["primary_metadata"]["primary_entry_vas"],
        checkpoints=checkpoint_contract(metadata["primary_observers"]), helper_binding=dict(path=HELPER_SOURCE,sha256=HELPER_SHA256),
        availability_proof="controlled route; natural selection is not established",
        map_probe_template=expected, dump_action_token=DUMP_TOKEN, handoff_action=handoff,
        byte_checks_before_first_breakpoint=byte_checks, startup_commands_before_final_g=startup,
        breakpoint_commands={str(k): {"va": v[0], "body": v[1]} for k,v in commands.items()},
        byte_spans=records, return_sentinel_va=SENTINEL, expected_capture_surface="borrowed physical HD mirror at owned canvas state.physical; E0 remains native640",
        final_ready_marker="MCAP_SURFDUMP_READY", final_host_marker="MPCAP_HOST_READY name=final-ready",
        required_host_contract="Hidden non-presenting proxy; enforce a600-second total deadline and120-second per-validator bound; capture only exact primary-stage checkpoints after accepted ordered route, zero slots at first checkpoint and twelve subsequently; terminate only owned game/debugger and bind cleanup.",
        prior_map_snapshot="Existing SURFDUMP_READY/SCROLL_VISDUMP remain diagnostic and are not modal readiness.",
        paused_capture=True, forced_os_input=False, forced_gate_result=route != "castle_overview",
        forced_native_dispatch=True, manual_input_proof=False,
        promotion_ready=False, pending_routes=PENDING, limits=LIMITS)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--candidate-sha256", required=True)
    parser.add_argument("--stage", required=True)
    parser.add_argument("--resolution", required=True)
    parser.add_argument("--route", choices=("barracks",), required=True)
    parser.add_argument("--candidate-manifest", required=True, type=Path)
    parser.add_argument("--availability", choices=("existing_flags", "construct_all"), required=True)
    parser.add_argument("--castle-index", type=int, required=True)
    parser.add_argument("--minimap-viewport", action="store_true")
    args = parser.parse_args()
    try:
        original, candidate = args.original.read_bytes(), args.candidate.read_bytes()
        packet = build_screen_probe(original, candidate, candidate_sha256=args.candidate_sha256,
            stage=args.stage, resolution=args.resolution, route=args.route, availability=args.availability,
            castle_index=args.castle_index, candidate_manifest=args.candidate_manifest, minimap_viewport=True)
    except (OSError, ValueError) as exc:
        parser.exit(2, f"modal probe preparation refused: {exc}\n")
    print(json.dumps(packet, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
