#!/usr/bin/env python3
"""Offline complete-HD army selection; never execute runtime or write evidence.

The native selection-v3 parser is preserved with explicit physical geometry and
inherited ARMY identity. Complete logs are never projected or relabeled. Only
the bound API reconstructs the candidate, manifest, packet and command bytes;
its readiness flag still proves no pixels, cleanup, manual input or promotion.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re

import complete_hd_army_selection_probe as producer
import complete_hd_runtime_context as runtime
import framed_army_selection_trace as frozen
import initial_map_paint_trace as initial_trace

FROZEN_TRACE_SHA256 = '87523a32e3bd108998d03be16c98936549ddfe261c76e30b5ed58b88aa1164cc'
SOURCE_PATHS = (
    'tools/complete_hd_army_selection_trace.py', 'tools/initial_map_paint_trace.py',
    'tools/partial_tile_trace_probe.py', 'tools/framed_army_selection_trace.py',
)
P, PATTERNS, HEX, TEXT = frozen.P, frozen.PATTERNS, frozen.HEX, frozen.TEXT
ERROR = re.compile(frozen.ERROR.pattern + r'|COMPLETEHD_CONTRACT_FAIL|MCANVAS_CONTRACT_FAIL', re.I)
LIMITS = list(frozen.LIMITS) + [
    'Sequence-only diagnostics do not validate the initial-map sequence or authenticate any supplied artifact.',
    'The bound initial-map validator consumes the original complete log and probe with all three loaded contracts; no stage projection or duplicate removal occurs.',
]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    """Use the producer's shared exact JSON types and structural bounds."""
    return producer.canonical_json(value)


def source_receipts():
    if sha(Path(frozen.__file__).read_bytes()) != FROZEN_TRACE_SHA256:
        raise ValueError('frozen native selection-v3 trace source differs')
    return producer.verify_sources() | {
        path: sha((producer.ROOT / path).read_bytes()) for path in SOURCE_PATHS
    }


def _packet(packet):
    if type(packet) is not dict:
        raise ValueError('packet must be an object')
    canonical(packet)
    if (packet.get('schema'), packet.get('revision'), packet.get('stage')) != (
            'clash95_complete_hd_army_selection_probe_v1', producer.REVISION, producer.builder.STAGE):
        raise ValueError('unsupported complete army packet identity')
    resolution = packet.get('resolution')
    if resolution not in producer.builder.RESOLUTIONS:
        raise ValueError('unsupported complete army resolution')
    width, height = map(int, resolution.split('x'))
    for key in ('width', 'height', 'unit'):
        if type(packet.get(key)) is not int:
            raise ValueError('exact integer field required: ' + key)
    if (packet['width'], packet['height'], packet['unit']) != (width, height, 3):
        raise ValueError('packet dimensions or army index differ')
    for key, expected in (
            ('unit_xy', [16, 19]), ('unit_squad_types', [16,16,1,1,1,1,1,1]),
            ('controlled_scroll', [10, 17]), ('controlled_mouse', [448, 176])):
        value = packet.get(key)
        if type(value) is not list or any(type(x) is not int for x in value) or value != expected:
            raise ValueError('inspected native route vector differs: ' + key)
    for key in ('native_predicate_forced', 'manual_input_proof', 'promotion_ready', 'runtime_executed'):
        if packet.get(key) is not False:
            raise ValueError('packet cannot claim ' + key)
    if packet.get('minimap_viewport') is not True or packet.get('capture_class') != 'e0_software_diagnostic':
        raise ValueError('complete minimap/software capture disclosure differs')
    if (packet.get('inherited_stage'), packet.get('inherited_revision'), packet.get('candidate_recipe')) != (
            frozen.producer.builder.STAGE, frozen.producer.builder.REVISION, producer.builder.REVISION):
        raise ValueError('complete recipe or inherited army identity differs')
    if packet.get('parent_source_sha256') != producer.PARENT_SOURCE_SHA256:
        raise ValueError('native producer ancestry differs')
    if packet.get('save_sha256') != producer.SAVE_SHA256 or packet.get('original_sha256') != producer.clip.ORIGINAL_SHA256:
        raise ValueError('known original/save identity differs')
    for key in ('candidate_sha256', 'original_sha256', 'save_sha256', 'candidate_manifest_canonical_sha256'):
        if type(packet.get(key)) is not str or not re.fullmatch('[0-9a-f]{64}', packet[key]):
            raise ValueError('invalid ' + key)
    if producer.capture_directory(packet.get('capture_dir')) != packet['capture_dir']:
        raise ValueError('canonical capture directory required')
    for content, digest in (('compiled_probe', 'probe_sha256'), ('initial_extra', 'initial_extra_sha256')):
        if type(packet.get(content)) is not str or sha(packet[content].encode('ascii')) != packet.get(digest):
            raise ValueError('embedded ' + content + ' differs')
    returns, sites = packet.get('native_call_returns'), packet.get('observer_vas')
    if type(returns) is not dict or type(sites) is not dict or set(sites) != {str(n) for n in range(80, 93)}:
        raise ValueError('complete native observer mapping required')
    if set(returns) != {'portraits', 'redraw', 'native_draw', 'composition_draw'} or any(type(v) is not int for v in returns.values()):
        raise ValueError('complete native call-return mapping required')
    fixed = {80:0x406FA1, 81:0x408131, 82:0x408136, 83:0x406980, 84:0x40A500,
             85:0x423B00, 86:0x423420, 87:0x4080EF, 88:0x423B32, 89:0x423B3C}
    if returns['portraits'] != fixed[88] or returns['redraw'] != fixed[89]:
        raise ValueError('native portrait/redraw return boundary differs')
    if any(type(v) is not int or not 0x400000 <= v < 0x80000000 for v in sites.values()):
        raise ValueError('native observer address differs')
    if any(sites[str(n)] != va for n, va in fixed.items()):
        raise ValueError('native selection observer boundary differs')
    for key, number in (('native_draw', '91'), ('composition_draw', '92')):
        if returns[key] != sites[number]:
            raise ValueError('emitted draw return binding differs')
    if len({sites['90'], sites['91'], sites['92']}) != 3:
        raise ValueError('draw entry and return sites must be distinct')
    if type(packet.get('source_sha256')) is not dict or not packet['source_sha256']:
        raise ValueError('producer source provenance required')
    if type(packet.get('startup_recipe')) is not dict:
        raise ValueError('startup recipe provenance required')


def _sequence(log,packet):
    failures=[];rows=[];draws=[];pairs=[];diagnostics=[];pending=None;phase=0;entries=returns=0
    tid=sp=0;native=[];composition=[];ready=None
    width,height=packet['width'],packet['height']
    def fail(message,line=None):failures.append((f'line {line}: ' if line else '')+message)
    def require(ok,message,line=None):
        if not ok:fail(message,line)
    for line,text in enumerate(log.splitlines(),1):
        if ERROR.search(text):fail('runtime/debugger rejection retained',line)
        if re.search(r'\bSHSEL_',text,re.I):
            marker=text.split(' ',1)[0];pattern=PATTERNS.get(marker)
            match=pattern.fullmatch(text) if pattern else None
            values=({k:v if k in TEXT else int(v,16 if k in HEX else 10)
                     for k,v in match.groupdict().items()} if match else None)
            rows.append(dict(line=line,text=text,marker=marker,values=values))
            if values is None:fail('malformed, unknown or prefixed selection record',line);continue
            if any(not -0x80000000<=v<=0x7fffffff for k,v in values.items() if k not in TEXT|HEX):
                fail('decimal value outside x86 signed range',line)
            marker=marker.removeprefix('SHSEL_');v=values
            for key in ('tid','esp'):
                if key in v:require(v[key]>0 and (key!='esp' or v[key]>=0x10000 and v[key]%4==0),'invalid '+key,line)
            if marker=='BYTES_PASS':
                require(phase==0,'byte contract missing/repeated/out of order',line);phase=1
            elif marker in ('HANDOFF','HANDOFF_CHECKS','WORLD_CHECKS'):
                require(packet['revision']==producer.REVISION and phase==1,
                        'undeclared or out-of-phase handoff diagnostic',line)
                wanted=('HANDOFF','HANDOFF_CHECKS','WORLD_CHECKS')
                require(len(diagnostics)<3 and marker==wanted[min(len(diagnostics),2)],
                        'handoff diagnostics missing, repeated or reordered',line)
                diagnostics.append(dict(marker=marker,values=v,line=line))
                if marker=='HANDOFF':
                    require((v['eip'],v['t14'],v['t13'],v['owner'],v['lower_raw'],v['post'],v['player_raw'],v['player'],v['selected'],v['prior'])==
                            (0x406FA0,1,4,0x40AD40,0,0,0,0,-1,-1), 'handoff diagnostic context differs',line)
                    require(0x10000<=v['gd']<=0xfff00000 and v['selected_raw'] in (0xffffffff,0xffffffffffffffff)
                            and v['prior_raw'] in (0xffffffff,0xffffffffffffffff),'handoff pointer/raw selection differs',line)
                else:require(all(value==1 for value in v.values()),'an actual handoff/world predicate failed',line)
            elif marker=='BEGIN':
                require(phase==1,'BEGIN out of order or repeated',line);phase=2
                require(len(diagnostics)==3,
                        'required handoff diagnostics missing before BEGIN',line)
                tid,sp=v['tid'],v['esp']
                require((v['eip'],v['selected'],v['prior'],v['old_y'])==(0x406FA0,-1,-1,17),
                        'handoff entry/selection/known vertical scroll differs',line)
                require(0<=v['old_x']<=100,'old scroll outside known world',line)
            elif marker in ('CONTROLLED','OCCUPANCY','SELECTION_WRITE','UPDATER','PANEL_UPDATE','ARMY_OPEN','ARMY_DRAW'):
                expected={'CONTROLLED':2,'OCCUPANCY':3,'SELECTION_WRITE':4,'UPDATER':5,'PANEL_UPDATE':6,'ARMY_OPEN':7,'ARMY_DRAW':8}[marker]
                require(phase==expected,marker+' missing/repeated/out of order',line);phase=expected+1
                if marker=='SELECTION_WRITE':
                    require((v['selected'],v['eax'],v['tid'],v['esp'])==(3,1,tid,sp-24),'native selection result/thread/stack differs',line)
                if marker in ('UPDATER','PANEL_UPDATE','ARMY_OPEN','ARMY_DRAW'):
                    require((v['selected'],v['prior'],v['lower'])==(3,3 if marker=='ARMY_DRAW' else -1,1 if marker=='ARMY_DRAW' else 0),
                            marker+' selection ownership differs',line)
                if marker=='UPDATER':require(v['caller']==0x406FA1,'updater return sentinel differs',line)
            elif marker=='DRAW_ENTRY':
                require(phase in (9,10) and pending is None,'draw entry outside open draw phase or overlaps call',line)
                entries+=1
                require(v['tid']==tid and v['count']==entries and entries==returns+1,'draw entry counter/thread differs',line)
                require(v['caller'] in (packet['native_call_returns']['native_draw'],packet['native_call_returns']['composition_draw']),
                        'draw caller is not an authenticated observer',line)
                pending=dict(v,line=line)
            elif marker=='DRAW_RETURN':
                require(phase in (9,10) and pending is not None,'draw return lacks pending entry',line)
                returns+=1
                require(v['tid']==tid and v['count']==returns and returns==entries,'draw return counter/thread differs',line)
                if pending:
                    expected_caller=packet['native_call_returns']['native_draw' if v['route']=='native' else 'composition_draw']
                    require(v['esp']==pending['esp']+4 and pending['caller']==expected_caller,
                            'draw return stack or native caller differs',line)
                require(v['status'] in ((0,1) if v['route']=='native' else (1,)),'draw status is not accepted for this route',line)
                observation=dict(entry=pending,returned=dict(v,line=line),relocated_draw=v['status']==1)
                draws.append(observation)
                (native if v['route']=='native' else composition).append(observation)
                pending=None
            elif marker=='PAIRED':
                before=v['event']=='before-redraw'
                require(phase==(9 if before else 10),'paired snapshot missing/repeated/out of order',line)
                require(pending is None and entries==returns and entries>=1 and len(native)>=1,
                        'paired snapshot has missing/incomplete draw calls',line)
                if not before:require(len(composition)>=1,'post-redraw lacks successful composition',line)
                require((v['selected'],v['prior'],v['lower'],v['width'],v['height'])==(3,3,1,width,height),
                        'paired snapshot selection or dimensions differ',line)
                pairs.append(dict(v,line=line));phase=10 if before else 11
            elif marker=='READY':
                require(phase==11 and pending is None and entries==returns and composition,'READY lacks complete native/redraw sequence',line)
                require((v['tid'],v['eip'],v['esp'],v['selected'],v['prior'],v['lower'],v['owner'],v['width'],v['height'],v['vtable'])==
                        (tid,0x406FA1,sp,3,3,1,0x40AD40,width,height,0x50EE24),'ready identity/state/physical memory target differs',line)
                ready=dict(v,line=line);phase=12
            elif marker=='HOST_READY':require(phase==12,'host readiness is premature/repeated',line);phase=13
        elif re.search(r'\bSURFDUMP_HOST_READY\b',text):fail('ordinary map host-ready is forbidden in this lane',line)
        if phase==13 and re.search(r'\b(?:SURFDUMP_(?:REDRAW|READY|PLAYGAME)|PTILE_)',text,re.I):
            fail('game/map execution continued after stopped readiness',line)
    require(phase==13 and pending is None,'complete stopped selection sequence is missing')
    require(len(pairs)==2 and [r['event'] for r in pairs]==['before-redraw','after-redraw'],'exact paired snapshots required')
    for row in pairs+([ready] if ready else []):
        require(0x10000<=row['surface']<=0xffffff44 and row['surface']!=0x51d4c0 and
                0x10000<=row['base']<=0x100000000-width*height,'surface/pixel range invalid',row['line'])
    if ready:
        require(all((p['surface'],p['base'])==(ready['surface'],ready['base']) for p in pairs),'paired E0/pixel ownership changed')
    closes=[(n,t) for n,t in enumerate(log.splitlines(),1) if re.search(r'\bPTILE_TRACE_CLOSED\b',t,re.I)]
    close=f'PTILE_TRACE_CLOSED tid={tid:x} eip=00406fa0 esp={sp:08x}'
    begins=[r['line'] for r in rows if r['marker']=='SHSEL_BEGIN']
    require(len(closes)==1,'one initial closure required')
    if begins:require(len(closes)==1 and closes[0][1]==close,'initial closure thread/stack identity differs')
    if closes and begins:require(closes[0][0]<begins[0],'selection begins before trace closure')
    if closes and diagnostics:require(closes[0][0]<diagnostics[0]['line'],'diagnostics precede initial trace closure')
    contract=(f"ARMY_CONTRACT_PASS stage={packet['inherited_stage']} resolution={packet['resolution']} candidate_sha256={packet['candidate_sha256']} revision={packet['inherited_revision']}")
    scope='ARMY_SCOPE own_player_0_to_3_native_size_panel manual_input_proof=false promotion_ready=false'
    army_rows=[(n,t) for n,t in enumerate(log.splitlines(),1) if re.search(r'\bARMY_',t,re.I)]
    require([t for _,t in army_rows]==[contract,scope],'complete army loaded-byte contract/scope differs')
    bytes_rows=[r['line'] for r in rows if r['marker']=='SHSEL_BYTES_PASS']
    events=[n for n,t in enumerate(log.splitlines(),1) if t.startswith('PTILE_EVENT ')]
    if len(bytes_rows)==1 and len(army_rows)==2 and events:
        require(bytes_rows[0]<army_rows[0][0]<army_rows[1][0]<events[0], 'native/army byte checks must precede initial execution')
    else:fail('native/army/initial startup contracts incomplete')
    return dict(passed=not failures,failures=failures,raw_records=rows,draw_calls=draws,handoff_diagnostics=diagnostics,
                counters=dict(entries=entries,returns=returns,native=len(native),composition=len(composition)),
                native_warmup_fallbacks=sum(d['returned']['status']==0 for d in native),
                native_relocated_draw_observed=any(d['returned']['status']==1 for d in native),
                composition_draw_observed=bool(composition) and all(d['returned']['status']==1 for d in composition),
                paired_observations=pairs,surface=ready)


def _loaded_contracts(log, packet):
    """Retain exact inherited and complete identities, including their order."""
    identity = f"resolution={packet['resolution']} candidate_sha256={packet['candidate_sha256']}"
    contracts = (
        f"ARMY_CONTRACT_PASS stage={packet['inherited_stage']} {identity} revision={packet['inherited_revision']}",
        f"COMPLETEHD_CONTRACT_PASS stage={packet['stage']} {identity} revision={packet['candidate_recipe']}",
        f"PTILE_CONTRACT_PASS stage={packet['inherited_stage']} {identity}",
    )
    failures, locations = [], []
    lines = log.splitlines()
    events = [n for n, text in enumerate(lines) if text.startswith('PTILE_EVENT ')]
    for contract in contracts:
        marker = contract.split()[0]
        matching = [n for n, text in enumerate(lines) if re.search(r'\b' + marker + r'\b', text, re.I)]
        if len(matching) != 1 or lines[matching[0]] != contract:
            failures.append('missing, repeated, prefixed or mismatched ' + marker)
        else:
            locations.append(matching[0])
        for name in ('initial_extra', 'compiled_probe'):
            if packet[name].splitlines().count('.echo ' + contract) != 1:
                failures.append(name + ' lacks exact ' + marker)
    if len(locations) != 3 or locations != sorted(set(locations)) or not events or locations[-1] >= events[0]:
        failures.append('ARMY/COMPLETEHD/PTILE contracts must precede initial execution in source order')
    for n, text in enumerate(lines):
        if re.search(r'\bCOMPLETEHD_', text, re.I) and text != contracts[1]:
            failures.append(f'line {n+1}: unknown or failed complete contract retained')
    return failures


def _result(packet, *, failures=None, source=None):
    return dict(schema='clash95_complete_hd_army_selection_trace_v1', passed=False,
        stage=packet.get('stage') if isinstance(packet, dict) else None,
        resolution=packet.get('resolution') if isinstance(packet, dict) else None,
        source_authenticated=False, whole_candidate_bound=False, candidate_manifest_bound=False,
        ready_for_host_capture=False, selection_sequence=None, initial_map_trace=None,
        initial_log_projected=False, sequence_only=True, surface=None,
        source=source or {}, failures=failures or [], runtime_accepted=False,
        pixels_verified=False, cleanup_verified=False, manual_input_proof=False,
        promotion_ready=False, limits=LIMITS)


def evaluate_trace(log, packet):
    """Untrusted sequence diagnostic; no initial-context or capture authority."""
    report = _result(packet)
    try:
        if type(log) is not str:
            raise ValueError('decoded log text required')
        _packet(packet)
        sequence = _sequence(log, packet)
        report.update(selection_sequence=sequence, surface=sequence['surface'])
        report['failures'] = sequence['failures'] + _loaded_contracts(log, packet)
        report['passed'] = not report['failures']
    except (KeyError, TypeError, ValueError, UnicodeError, OSError) as error:
        report['failures'].append(str(error))
    return report


def evaluate_bound_trace(log, packet, *, original, candidate, save, generated_probe, candidate_manifest):
    """Reconstruct source/candidate/packet, then validate untouched complete logs."""
    report = _result(packet)
    try:
        if type(log) is not str:
            raise ValueError('decoded log text required')
        if any(type(value) is not bytes for value in (original, candidate, save, generated_probe)):
            raise ValueError('immutable original/candidate/save/probe bytes required')
        if type(candidate_manifest) is not dict:
            raise ValueError('complete candidate manifest object required')
        _packet(packet)
        for name, data in (('original', original), ('candidate', candidate), ('save', save)):
            if sha(data) != packet[name + '_sha256']:
                raise ValueError(name + ' bytes differ from packet identity')
        manifest_json = canonical(candidate_manifest)
        if sha(manifest_json.encode()) != packet['candidate_manifest_canonical_sha256']:
            raise ValueError('candidate manifest canonical JSON differs from packet')
        sources = source_receipts()
        source = dict(source_sha256=sources, frozen_trace_sha256=FROZEN_TRACE_SHA256,
            log_text_sha256=sha(log.encode()), original_sha256=sha(original),
            candidate_sha256=sha(candidate), save_sha256=sha(save),
            candidate_manifest_canonical_sha256=sha(manifest_json.encode()))
        report['source'] = source
        rebuilt = producer.build_selection_probe(original, candidate, save,
            capture_dir=packet['capture_dir'], candidate_manifest=candidate_manifest,
            resolution=packet['resolution'])
        if canonical(rebuilt) != canonical(packet):
            raise ValueError('packet differs from entire source/candidate/save/manifest reconstruction')
        command = generated_probe.decode('ascii').replace('\r\n', '\n')
        if command != packet['compiled_probe']:
            raise ValueError('actual command bytes differ from canonical packet')
        source.update(probe_raw_sha256=sha(generated_probe),
            probe_canonical_lf_sha256=sha(command.encode('ascii')),
            packet_canonical_sha256=sha(canonical(packet).encode()))
        report = evaluate_trace(log, packet)
        report['source'] = source
        # The helper reconstructs the complete manifest and canonical initial
        # probe again. It sees every original line, including failed markers.
        initial = initial_trace.evaluate_trace(log, packet['initial_extra'],
            resolution=packet['resolution'], candidate_sha256=packet['candidate_sha256'],
            stage=packet['stage'], candidate_manifest=candidate_manifest, original=original)
        report['initial_map_trace'] = initial
        report['failures'].extend('initial map: ' + error for error in initial['failures'])
        if source_receipts() != sources:
            raise ValueError('selection trace sources changed during reconstruction')
        report.update(source_authenticated=True, whole_candidate_bound=True,
            candidate_manifest_bound=True, sequence_only=False)
        report['passed'] = not report['failures']
        report['ready_for_host_capture'] = report['passed']
    except (KeyError, TypeError, ValueError, UnicodeError, OSError) as error:
        report['failures'].append(str(error))
        report.update(passed=False, ready_for_host_capture=False, source_authenticated=False,
            whole_candidate_bound=False, candidate_manifest_bound=False)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('log', 'packet', 'original', 'candidate', 'save', 'probe', 'candidate-manifest'):
        parser.add_argument('--' + name, required=True, type=Path)
    args = parser.parse_args()
    try:
        raw = args.log.read_bytes()
        report = evaluate_bound_trace(raw.decode('utf-8-sig'), producer.read_manifest(args.packet),
            original=args.original.read_bytes(), candidate=args.candidate.read_bytes(),
            save=args.save.read_bytes(), generated_probe=args.probe.read_bytes(),
            candidate_manifest=producer.read_manifest(args.candidate_manifest))
        report['source']['log_raw_sha256'] = sha(raw)
    except (OSError, ValueError, UnicodeError) as error:
        report = _result(None, failures=[str(error)])
    print(json.dumps(report, indent=2))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
