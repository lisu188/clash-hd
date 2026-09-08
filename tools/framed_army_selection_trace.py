#!/usr/bin/env python3
"""Offline army-selection observations; full acceptance reconstructs all inputs.

No game, debugger, input, capture or artifact writer is used. The sequence-only
API is diagnostic. The bound API authenticates the original, save, complete
candidate, packet and compiled probe before projecting one initial stage token.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re

import framed_army_selection_probe as producer
import initial_map_paint_trace as initial_trace

PRODUCER_SHA256='e5476178b80c29cf35ac2c64f8f89cb29a34596f8b3d1aa971ae456d0bbfc2e8'
H=r'[0-9a-fA-F]{1,8}'
H64=r'[0-9a-fA-F]{1,16}'
D=r'-?[0-9]{1,10}'
ID=rf'tid=(?P<tid>{H}) eip=(?P<eip>{H}) esp=(?P<esp>{H})'
SEL=rf'selected=(?P<selected>{D}) prior=(?P<prior>{D}) lower=(?P<lower>{D})'
P={
 'BYTES_PASS':'',
 'HANDOFF':rf'eip=(?P<eip>{H}) t14=(?P<t14>{H64}) t13=(?P<t13>{H64}) gd=(?P<gd>{H}) owner=(?P<owner>{H}) lower=(?P<lower_raw>{H}) post=(?P<post>{H}) player=\((?P<player_raw>{H}),(?P<player>{D})\) selected=\((?P<selected_raw>{H64}),(?P<selected>{D})\) prior=\((?P<prior_raw>{H64}),(?P<prior>{D})\)',
 'HANDOFF_CHECKS':r'eip=(?P<check_eip>[01]) t14=(?P<check_t14>[01]) t13=(?P<check_t13>[01]) owner=(?P<check_owner>[01]) lower=(?P<check_lower>[01]) post=(?P<check_post>[01]) player=(?P<check_player>[01]) selected=(?P<check_selected>[01]) prior=(?P<check_prior>[01])',
 'WORLD_CHECKS':r'width=(?P<check_width>[01]) height=(?P<check_height>[01]) scroll_y=(?P<check_scroll_y>[01]) unit_xy=(?P<check_unit_xy>[01]) unit_owner=(?P<check_unit_owner>[01])',
 'BEGIN':ID+rf' old_scroll=\((?P<old_x>{D}),(?P<old_y>{D})\) selected=(?P<selected>{D}) prior=(?P<prior>{D})',
 'CONTROLLED':r'scroll=\(10,17\) screen=\(448,176\) unit=3 world=\(16,19\) predicate_forced=0 native_entry=00408030 updater=00406980',
 'OCCUPANCY':r'world=\(16,19\) unit=3 selected_before=-1 player=0',
 'SELECTION_WRITE':rf'selected=(?P<selected>{D}) eax=(?P<eax>{H}) tid=(?P<tid>{H}) esp=(?P<esp>{H})',
 'UPDATER':SEL+rf' caller=(?P<caller>{H})',
 'PANEL_UPDATE':SEL,'ARMY_OPEN':SEL,'ARMY_DRAW':SEL,
 'DRAW_ENTRY':rf'tid=(?P<tid>{H}) esp=(?P<esp>{H}) caller=(?P<caller>{H}) count=(?P<count>{D}) font7_cache=(?P<font7_cache>{H})',
 'DRAW_RETURN':rf'route=(?P<route>native|composition) tid=(?P<tid>{H}) esp=(?P<esp>{H}) status=(?P<status>{D}) count=(?P<count>{D})',
 'PAIRED':rf'event=(?P<event>before-redraw|after-redraw) '+SEL+rf' surface=(?P<surface>{H}) base=(?P<base>{H}) size=\((?P<width>{D}),(?P<height>{D})\)',
 'READY':ID+' '+SEL+rf' owner=(?P<owner>{H}) surface=(?P<surface>{H}) base=(?P<base>{H}) width=(?P<width>{D}) height=(?P<height>{D}) vtable=(?P<vtable>{H})',
 'HOST_READY':'',
}
PATTERNS={'SHSEL_'+k:re.compile('SHSEL_'+k+(' '+v if v else '')) for k,v in P.items()}
HEX={'tid','eip','esp','eax','caller','font7_cache','surface','base','owner','vtable','t14','t13','gd','lower_raw','post','player_raw','selected_raw','prior_raw'}
TEXT={'route','event'}
ERROR=re.compile(r'SHSEL_REJECT|SHSEL_SELECTION_FAIL|ARMY_CONTRACT_FAIL|PTILE_REJECT|PTILE_CONTRACT_FAIL|'
 r'AV_SURFDUMP|SURFDUMP_INVALID|SURFDUMP_APP_REQUEST_QUIT|syntax error|couldn.t resolve|access violation|'
 r'\btimeout\b|\btimed out\b|second chance|unhandled exception',re.I)
LIMITS=[
 'Controlled native selection and observed draw sequencing only; no natural/manual input proof.',
 'Native draw status0 is retained as legacy fallback, not relocated artwork success. Every observed composition must return1.',
 'Ready E0 identity does not authenticate copied pixels, final visible composition, cleanup or normal return from the interrupted map call.',
 'Only DRAW_ENTRY/RETURN, BEGIN, SELECTION_WRITE and READY print their thread/stack; other native checks are bound producer guards.',
 'Sequence-only results do not authorize capture. Full source/candidate/probe reconstruction is mandatory for ready_for_host_capture.',
]


def sha(data):return hashlib.sha256(data).hexdigest()


def _packet(packet):
    if not isinstance(packet,dict):raise ValueError('packet must be an object')
    if (packet.get('schema'),packet.get('stage'),packet.get('resolution'))!=(
        'clash95_framed_army_selection_probe_v1',producer.builder.STAGE,'1024x768') or packet.get('revision') not in (
            'controlled_own_army_native_selection_v1','controlled_own_army_native_selection_v2',
            'controlled_own_army_native_selection_v3'):
        raise ValueError('unsupported army packet schema/revision/stage/resolution')
    if (packet.get('width'),packet.get('height'),packet.get('unit'),packet.get('unit_xy'),
        packet.get('unit_squad_types'),packet.get('save_sha256'))!=(
        1024,768,3,[16,19],[16,16,1,1,1,1,1,1],producer.SAVE_SHA256):
        raise ValueError('packet dimensions or inspected save/unit contract differs')
    if (packet.get('controlled_scroll'),packet.get('controlled_mouse'),packet.get('native_predicate_forced'))!=([10,17],[448,176],False):
        raise ValueError('controlled route disclosure differs')
    for name in ('manual_input_proof','promotion_ready','runtime_executed'):
        if packet.get(name) is not False:raise ValueError('packet cannot claim '+name)
    if type(packet.get('minimap_viewport')) is not bool:raise ValueError('minimap profile missing')
    for name in ('candidate_sha256','original_sha256','save_sha256'):
        if not isinstance(packet.get(name),str) or not re.fullmatch('[0-9a-f]{64}',packet[name]):
            raise ValueError('invalid packet '+name)
    for content,digest in (('compiled_probe','probe_sha256'),('initial_extra','initial_extra_sha256')):
        if not isinstance(packet.get(content),str) or sha(packet[content].encode('ascii'))!=packet.get(digest):
            raise ValueError('embedded '+content+' SHA differs')
    returns=packet.get('native_call_returns',{})
    if not isinstance(returns,dict) or not isinstance(packet.get('observer_vas'),dict):
        raise ValueError('native return/observer mappings required')
    if returns.get('portraits')!=0x423B32 or returns.get('redraw')!=0x423B3C:
        raise ValueError('native portrait/redraw return boundary differs')
    for name,bp in (('native_draw','91'),('composition_draw','92')):
        value=returns.get(name)
        if type(value) is not int or not 0x10000<=value<=0xffffffff or packet.get('observer_vas',{}).get(bp)!=value:
            raise ValueError('emitted draw observer binding differs')


def _sequence(log,packet):
    failures=[];rows=[];draws=[];pairs=[];diagnostics=[];pending=None;phase=0;entries=returns=0
    tid=sp=0;native=[];composition=[];ready=None
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
                require(packet['revision'] in ('controlled_own_army_native_selection_v2','controlled_own_army_native_selection_v3') and phase==1,
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
                require(len(diagnostics)==(0 if packet['revision'].endswith('_v1') else 3),
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
                require((v['selected'],v['prior'],v['lower'],v['width'],v['height'])==(3,3,1,1024,768),
                        'paired snapshot selection or dimensions differ',line)
                pairs.append(dict(v,line=line));phase=10 if before else 11
            elif marker=='READY':
                require(phase==11 and pending is None and entries==returns and composition,'READY lacks complete native/redraw sequence',line)
                require((v['tid'],v['eip'],v['esp'],v['selected'],v['prior'],v['lower'],v['owner'],v['width'],v['height'],v['vtable'])==
                        (tid,0x406FA1,sp,3,3,1,0x40AD40,1024,768,0x50EE24),'ready identity/state/physical memory target differs',line)
                ready=dict(v,line=line);phase=12
            elif marker=='HOST_READY':require(phase==12,'host readiness is premature/repeated',line);phase=13
        elif re.search(r'\bSURFDUMP_HOST_READY\b',text):fail('ordinary map host-ready is forbidden in this lane',line)
        if phase==13 and re.search(r'\b(?:SURFDUMP_(?:REDRAW|READY|PLAYGAME)|PTILE_)',text,re.I):
            fail('game/map execution continued after stopped readiness',line)
    require(phase==13 and pending is None,'complete stopped selection sequence is missing')
    require(len(pairs)==2 and [r['event'] for r in pairs]==['before-redraw','after-redraw'],'exact paired snapshots required')
    for row in pairs+([ready] if ready else []):
        require(0x10000<=row['surface']<=0xffffff44 and row['surface']!=0x51d4c0 and
                0x10000<=row['base']<=0x100000000-786432,'surface/pixel range invalid',row['line'])
    if ready:
        require(all((p['surface'],p['base'])==(ready['surface'],ready['base']) for p in pairs),'paired E0/pixel ownership changed')
    closes=[(n,t) for n,t in enumerate(log.splitlines(),1) if re.search(r'\bPTILE_TRACE_CLOSED\b',t,re.I)]
    close=f'PTILE_TRACE_CLOSED tid={tid:x} eip=00406fa0 esp={sp:08x}'
    begins=[r['line'] for r in rows if r['marker']=='SHSEL_BEGIN']
    require(len(closes)==1,'one initial closure required')
    if begins:require(len(closes)==1 and closes[0][1]==close,'initial closure thread/stack identity differs')
    if closes and begins:require(closes[0][0]<begins[0],'selection begins before trace closure')
    if closes and diagnostics:require(closes[0][0]<diagnostics[0]['line'],'diagnostics precede initial trace closure')
    contract=(f"ARMY_CONTRACT_PASS stage={packet['stage']} resolution=1024x768 candidate_sha256={packet['candidate_sha256']} revision={producer.builder.REVISION}")
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


def _project(log,extra,packet):
    old=f"PTILE_CONTRACT_PASS stage={packet['stage']} resolution=1024x768 candidate_sha256={packet['candidate_sha256']}"
    new=old.replace('stage='+packet['stage']+' ','stage='+initial_trace.FRAMED_STAGE+' ',1)
    outputs=[];binding=dict(kind='one_exact_initial_contract_stage_token',source_stage=packet['stage'],projected_stage=initial_trace.FRAMED_STAGE)
    for name,text,prefix in (('log',log,''),('extra',extra,'.echo ')):
        lines=text.splitlines(keepends=True)
        found=[i for i,line in enumerate(lines) if line.rstrip('\r\n')==prefix+old]
        if len(found)!=1:raise ValueError('exactly one current-candidate initial '+name+' contract required')
        at=found[0];changed=lines.copy();changed[at]=changed[at].replace(old,new,1)
        output=''.join(changed)
        binding[name]=dict(original_sha256=sha(text.encode()),projected_sha256=sha(output.encode()),contract_line=at+1)
        outputs.append(output)
    return *outputs,binding


def evaluate_trace(log,packet):
    """Diagnostic evaluation only: packet hashes are checked, never trusted as proof."""
    failures=[];sequence=initial=projection=None
    try:
        if not isinstance(log,str):raise ValueError('log must be decoded text')
        _packet(packet)
        sequence=_sequence(log,packet);failures.extend(sequence['failures'])
        projected,extra,projection=_project(log,packet['initial_extra'],packet)
        initial=initial_trace.evaluate_trace(projected,extra,resolution='1024x768',
                        candidate_sha256=packet['candidate_sha256'],stage=initial_trace.FRAMED_STAGE)
        failures.extend('initial map: '+f for f in initial['failures'])
    except (KeyError,TypeError,ValueError,UnicodeError) as error:failures.append(str(error))
    return dict(schema='clash95_framed_army_selection_trace_v1',passed=not failures,
                source_authenticated=False,whole_candidate_bound=False,ready_for_host_capture=False,
                stage=packet.get('stage') if isinstance(packet,dict) else None,
                selection_sequence=sequence,initial_map_trace=initial,initial_projection=projection,
                surface=sequence.get('surface') if sequence else None,failures=failures,
                runtime_accepted=False,pixels_verified=False,cleanup_verified=False,
                manual_input_proof=False,promotion_ready=False,limits=LIMITS)


def evaluate_bound_trace(log,packet,*,original,candidate,save,generated_probe):
    """Authenticate every input before accepting a new-stage initial projection."""
    provenance=dict(validator_sha256=sha(Path(__file__).read_bytes()),producer_sha256=sha(Path(producer.__file__).read_bytes()))
    try:
        if not isinstance(log,str):raise ValueError('log must be decoded text')
        _packet(packet)
        if provenance['producer_sha256']!=PRODUCER_SHA256:
            raise ValueError('reviewed army selection producer source differs')
        if any(type(data) is not bytes for data in (original,candidate,save,generated_probe)):
            raise ValueError('immutable original/candidate/save/probe bytes required')
        rebuilt=producer.build_selection_probe(original,candidate,save,capture_dir=packet['capture_dir'],
                                                minimap_viewport=packet['minimap_viewport'])
        if sha(Path(producer.__file__).read_bytes())!=PRODUCER_SHA256:
            raise ValueError('producer source changed during reconstruction')
        if rebuilt!=packet:raise ValueError('packet differs from whole current producer/source/candidate/save reconstruction')
        canonical=generated_probe.decode('ascii').replace('\r\n','\n')
        if canonical!=packet['compiled_probe']:raise ValueError('compiled probe differs from exact canonical packet')
        provenance.update(original_sha256=sha(original),candidate_sha256=sha(candidate),save_sha256=sha(save),
                          probe_raw_sha256=sha(generated_probe),probe_canonical_lf_sha256=sha(canonical.encode('ascii')),
                          log_text_sha256=sha(log.encode()),packet_sha256=sha(json.dumps(packet,sort_keys=True,separators=(',',':')).encode()))
        report=evaluate_trace(log,packet)
        report.update(source_authenticated=True,whole_candidate_bound=True,ready_for_host_capture=report['passed'],source=provenance)
        return report
    except (KeyError,TypeError,ValueError,UnicodeError,OSError) as error:
        return dict(schema='clash95_framed_army_selection_trace_v1',passed=False,source_authenticated=False,
                    whole_candidate_bound=False,ready_for_host_capture=False,source=provenance,
                    failures=[str(error)],selection_sequence=None,initial_map_trace=None,initial_projection=None,
                    surface=None,runtime_accepted=False,pixels_verified=False,cleanup_verified=False,
                    manual_input_proof=False,promotion_ready=False,limits=LIMITS)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('log','packet','original','candidate','save','probe'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args()
    try:
        raw=a.log.read_bytes()
        report=evaluate_bound_trace(raw.decode('utf8-sig'),json.loads(a.packet.read_text(encoding='utf8-sig')),
            original=a.original.read_bytes(),candidate=a.candidate.read_bytes(),save=a.save.read_bytes(),generated_probe=a.probe.read_bytes())
        report['source']['log_raw_sha256']=sha(raw)
    except (OSError,ValueError,UnicodeError) as error:report=dict(passed=False,failures=[str(error)])
    print(json.dumps(report,indent=2));return 0 if report['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
