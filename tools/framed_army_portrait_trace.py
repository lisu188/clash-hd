#!/usr/bin/env python3
"""Offline, source-bound native portrait-toggle trace validation.

The copied selection baseline is parsed in its own namespace through READY;
no legacy stop marker is manufactured. Three measured headers bind the paused
E0 observations. Pixels, final primary composition and cleanup remain separate.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import struct

import framed_army_portrait_probe as producer
import framed_army_selection_trace as selection

PRODUCER_SHA256='e2978cde61e979154d70949f6e2ba205ccc41241149b3fd847d73c4bb598d5f8'
HELPERS={
    'tools/framed_army_selection_trace.py':'87523a32e3bd108998d03be16c98936549ddfe261c76e30b5ed58b88aa1164cc',
    'tools/initial_map_paint_trace.py':'845edda7ac563afe602dc3f6a388fe7e1874d6c6f128d1a938f8ce9ac2aa1021',
    'tools/partial_tile_trace_probe.py':'a20512fa49cc86db67a486f9202d4efa3f9f3745005d11220bf6097661a44729',
}
H=selection.H;D=selection.D
ID=rf'tid=(?P<tid>{H}) eip=(?P<eip>{H}) esp=(?P<esp>{H})'
PATTERNS={
    'PTGL_'+name:re.compile('PTGL_'+name+(' '+pattern if pattern else ''))
    for name,pattern in {
        'BYTES_PASS':'','HOST_READY':'',
        'SURFACE':rf'checkpoint=(?P<checkpoint>{D}) '+ID+rf' surface=(?P<surface>{H}) base=(?P<base>{H}) width=(?P<width>{D}) height=(?P<height>{D}) vtable=(?P<vtable>{H})',
        'OBS':rf'kind=(?P<kind>[a-z-]+) toggle=(?P<toggle>{D}) phase=(?P<phase>{D}) '+ID+
            rf' caller=(?P<caller>{H}) eax=(?P<eax>{H}) ecx=(?P<ecx>{H}) edx=(?P<edx>{H}) esi=(?P<esi>{H}) edi=(?P<edi>{H}) selected=(?P<selected>{D}) prior=(?P<prior>{D}) lower=(?P<lower>{D}) unit=(?P<unit>{H}) mouse_raw=\((?P<mouse_x>{H}),(?P<mouse_y>{H})\) shift=(?P<shift>{H}) buttons=(?P<buttons>{H}) accumulator=(?P<accumulator>{H}) flags=\('+','.join(rf'(?P<flag{i}>{H})' for i in range(10))+rf'\) draws=\((?P<entries>{D}),(?P<returns>{D}),(?P<compositions>{D})\)',
    }.items()
}
PATTERNS.update({'PTGL_BASE_'+name:re.compile('PTGL_BASE_'+name+(' '+pattern if pattern else ''))
                 for name,pattern in selection.P.items() if name!='HOST_READY'})
HEX=selection.HEX|{'ecx','edx','esi','edi','unit','mouse_x','mouse_y','shift','buttons','accumulator'}|{'flag'+str(i) for i in range(10)}
TEXT=selection.TEXT|{'kind'}
ERROR=re.compile(selection.ERROR.pattern+r'|PTGL_(?:REJECT|BASE_REJECT|BASE_SELECTION_FAIL)|\b(?:SHSEL_|MCAP_|MODAL_|ATX_)|memory access error|CreateProcess failed|error 193',re.I)
SITES={100:0x423861,101:0x4238CA,102:0x4238E3,103:0x423937,104:0x423952,
       105:0x42395A,106:0x423964,107:0x418700,108:0x423970,109:0x4609D0,
       110:0x4609E0,111:0x4609FC,112:0x42397A,113:0x423989,114:0x423A99,
       115:0x423991,116:0x423A59}
LIMITS=producer.LIMITS+[
    'Baseline READY is a continuation checkpoint, not an old selection HOST_READY.',
    'All ten observed flag DWORDs must follow 0->slot0=1->0; the parser never removes duplicate records.',
    'Measured 188-byte headers prove the three E0 dimensions/pointer/vtable contracts only; pixel content and cleanup are separate.',
]


def sha(data):return hashlib.sha256(data).hexdigest()


def snapshot_paths(packet):
    directory=packet['capture_dir']
    return [dict(checkpoint=n,header_path=f'{directory}/{name}.header.raw',raw_path=f'{directory}/{name}.raw')
            for n,name in enumerate(('portrait-before','portrait-after-1','portrait-after-2'))]


def _packet(packet):
    if not isinstance(packet,dict):raise ValueError('packet must be an object')
    expected=('clash95_framed_army_portrait_probe_v1',producer.REVISION,producer.base.builder.STAGE,'1024x768',1024,768)
    if tuple(packet.get(k) for k in ('schema','revision','stage','resolution','width','height'))!=expected:
        raise ValueError('unsupported portrait packet identity')
    if (packet.get('unit'),packet.get('slot'),packet.get('unit_xy'),packet.get('unit_squad_types'),packet.get('controlled_scroll'),packet.get('controlled_mouse'),packet.get('flag_vectors'))!=(
            3,0,[16,19],[16,16,1,1,1,1,1,1],[10,17],[54,719],[[0]*10,[1]+[0]*9,[0]*10]):
        raise ValueError('inspected army/portrait/toggle contract differs')
    if packet.get('save_sha256')!=producer.base.SAVE_SHA256 or packet.get('original_sha256')!=producer.base.clip.ORIGINAL_SHA256:
        raise ValueError('known original/save identity differs')
    for key in ('candidate_sha256','original_sha256','save_sha256'):
        if not isinstance(packet.get(key),str) or not re.fullmatch('[0-9a-f]{64}',packet[key]):raise ValueError('invalid '+key)
    for key in ('native_predicate_forced','selected_value_forced','flag_value_forced','runtime_executed','manual_input_proof','promotion_ready'):
        if packet.get(key) is not False:raise ValueError('packet cannot claim '+key)
    if packet.get('controlled_input') is not True or packet.get('controlled_release') is not True or type(packet.get('minimap_viewport')) is not bool:
        raise ValueError('controlled route/release/profile disclosure required')
    if producer.base.capture_directory(packet.get('capture_dir'))!=packet['capture_dir']:raise ValueError('canonical capture path required')
    for content,digest in (('compiled_probe','probe_sha256'),('initial_extra','initial_extra_sha256')):
        if not isinstance(packet.get(content),str) or sha(packet[content].encode('ascii'))!=packet.get(digest):raise ValueError('embedded '+content+' differs')
    paths={f"{packet['capture_dir']}/portrait-checkpoint-{n}.cdb" for n in range(3)}
    commands=packet.get('supplemental_commands');hashes=packet.get('supplemental_sha256')
    if not isinstance(commands,dict) or not isinstance(hashes,dict) or set(commands)!=paths or set(hashes)!=paths:
        raise ValueError('exact three supplemental commands required')
    for path,text in commands.items():
        if not isinstance(text,str) or sha(text.encode('ascii'))!=hashes[path]:raise ValueError('supplemental command hash differs')
    if packet.get('portrait_observer_vas')!={str(n):va for n,va in SITES.items()}:raise ValueError('native portrait observer mapping differs')
    sites=packet.get('baseline_observer_vas',{});returns=packet.get('baseline_native_call_returns',{})
    if not isinstance(sites,dict) or set(sites)!={str(n) for n in range(80,93)} or not isinstance(returns,dict):raise ValueError('complete baseline mappings required')
    if returns.get('portraits')!=0x423B32 or returns.get('redraw')!=0x423B3C:raise ValueError('baseline native return mapping differs')
    for name,n in (('native_draw',91),('composition_draw',92)):
        if type(returns.get(name)) is not int or not 0x400000<=returns[name]<0x80000000 or sites[str(n)]!=returns[name]:raise ValueError('emitted draw mapping differs')


def _sequence(log,packet):
    failures=[];rows=[];events=[];snapshots=[];baseline_draws=[];toggles=[];ready=None
    def require(ok,message,line=None):
        if not ok:failures.append((f'line {line}: ' if line else '')+message)
    for n,text in enumerate(log.splitlines(),1):
        if ERROR.search(text):require(False,'runtime/debugger failure retained',n)
        if re.search(r'\bPTGL_',text,re.I):
            marker=text.split(' ',1)[0];pattern=PATTERNS.get(marker);match=pattern.fullmatch(text) if pattern else None
            v={k:x if k in TEXT else int(x,16 if k in HEX else 10) for k,x in match.groupdict().items()} if match else None
            row=dict(line=n,text=text,marker=marker,values=v);rows.append(row)
            if v is None:require(False,'malformed, prefixed or unknown portrait record',n);continue
            for key,value in v.items():
                if key not in TEXT|HEX:require(-0x80000000<=value<=0x7fffffff,'decimal value outside signed x86 range',n)
            for key in ('tid','esp'):
                if key in v:require(v[key]>0 and (key!='esp' or 0x10000<=v[key]<0x80000000 and v[key]%4==0),'invalid '+key,n)
            if marker not in ('PTGL_BYTES_PASS','PTGL_BASE_BYTES_PASS'):events.append(row)
        elif re.search(r'\bSURFDUMP_HOST_READY\b',text,re.I):require(False,'ordinary map readiness is forbidden',n)
    pos=0;tid=sp=gd=0;surface=None;baseline_fallbacks=0
    def take(marker,kind=None):
        nonlocal pos
        if pos>=len(events):raise ValueError('incomplete portrait sequence: expected '+(kind or marker))
        row=events[pos];pos+=1;v=row['values']
        if row['marker']!=marker or kind is not None and v.get('kind')!=kind:
            raise ValueError(f"line {row['line']}: expected {kind or marker}, got {row['marker']} {v.get('kind','')}")
        return v,row['line']
    def baseline(name):return take('PTGL_BASE_'+name)
    def physical(v,line):
        require((v['width'],v['height'],v.get('vtable',0x50EE24))==(1024,768,0x50EE24),'physical memory geometry/vtable differs',line)
        require(0x10000<=v['surface']<=0xffffff44 and v['surface']%4==0 and v['surface']!=0x51D4C0 and
                0x10000<=v['base']<=0x100000000-786432,'physical surface/pixel range invalid',line)
        if surface:require((v['surface'],v['base'])==(surface['surface'],surface['base']),'E0/pixel ownership changed',line)
    def snapshot(n):
        v,line=take('PTGL_SURFACE');physical(v,line)
        require((v['checkpoint'],v['tid'],v['eip'],v['esp'])==(n,tid,0x406FA1,sp),'snapshot checkpoint/thread/native stack differs',line)
        snapshots.append(dict(v,line=line,**{k:x for k,x in snapshot_paths(packet)[n].items() if k!='checkpoint'}))
        return v,line
    try:
        v,line=baseline('HANDOFF');gd=v['gd'];handoff_line=line
        require((v['eip'],v['t14'],v['t13'],v['owner'],v['lower_raw'],v['post'],v['player_raw'],v['player'],v['selected'],v['prior'])==
                (0x406FA0,1,4,0x40AD40,0,0,0,0,-1,-1),'baseline handoff context differs',line)
        require(0x10000<=gd<=0xfff00000 and v['selected_raw'] in (0xffffffff,0xffffffffffffffff) and v['prior_raw'] in (0xffffffff,0xffffffffffffffff),'baseline raw pointer/sentinel differs',line)
        for name in ('HANDOFF_CHECKS','WORLD_CHECKS'):
            v,line=baseline(name);require(all(x==1 for x in v.values()),'actual baseline predicate failed',line)
        v,line=baseline('BEGIN');tid,sp=v['tid'],v['esp'];begin_line=line
        require((v['eip'],v['selected'],v['prior'],v['old_y'])==(0x406FA0,-1,-1,17) and 0<=v['old_x']<=100,'baseline native entry/scroll differs',line)
        baseline('CONTROLLED');baseline('OCCUPANCY')
        v,line=baseline('SELECTION_WRITE');require((v['selected'],v['eax'],v['tid'],v['esp'])==(3,1,tid,sp-24),'native selection result/thread/stack differs',line)
        for name in ('UPDATER','PANEL_UPDATE','ARMY_OPEN','ARMY_DRAW'):
            v,line=baseline(name);require((v['selected'],v['prior'],v['lower'])==(3,3 if name=='ARMY_DRAW' else -1,1 if name=='ARMY_DRAW' else 0),'baseline ownership differs',line)
            if name=='UPDATER':require(v['caller']==0x406FA1,'baseline updater sentinel differs',line)
        count=0
        for route,delta,event in (('native',192,'before-redraw'),('composition',316,'after-redraw')):
            route_count=0
            while pos<len(events) and events[pos]['marker']=='PTGL_BASE_DRAW_ENTRY':
                a,al=baseline('DRAW_ENTRY');b,bl=baseline('DRAW_RETURN');count+=1;route_count+=1
                caller=packet['baseline_native_call_returns'][route+'_draw' if route=='native' else 'composition_draw']
                require((a['tid'],a['esp'],a['caller'],a['count'])==(tid,sp-delta,caller,count),'baseline draw entry/caller/count differs',al)
                require((b['route'],b['tid'],b['esp'],b['count'])==(route,tid,sp-delta+4,count),'baseline draw return pairing differs',bl)
                require(b['status'] in ((0,1) if route=='native' else (1,)),'baseline draw status differs',bl)
                baseline_fallbacks+=int(route=='native' and b['status']==0)
                baseline_draws.append(dict(entry=dict(a,line=al),returned=dict(b,line=bl)))
            require(route_count>=1,'baseline lacks '+route+' draw return')
            v,line=baseline('PAIRED');require(v['event']==event and (v['selected'],v['prior'],v['lower'])==(3,3,1),'baseline paired checkpoint differs',line)
            physical(v,line)
            if surface is None:surface=v
        v,line=baseline('READY');physical(v,line)
        require((v['tid'],v['eip'],v['esp'],v['selected'],v['prior'],v['lower'],v['owner'])==(tid,0x406FA1,sp,3,3,1,0x40AD40),'baseline continuation identity differs',line)
        snapshot(0)
        for toggle in (1,2):
            records=[];counts=[0,0,0];shift=None;flag=toggle-1;buttons=1;accumulator=0x80
            def obs(kind,phase,eip,delta,*,caller=None,registers=None):
                nonlocal shift
                v,line=take('PTGL_OBS',kind);records.append(dict(v,line=line))
                require((v['toggle'],v['phase'],v['tid'],v['eip'],v['esp'],v['selected'],v['prior'],v['lower'],v['unit'])==
                        (toggle,phase,tid,eip,sp-delta,3,3,1,gd+149349),kind+' identity/phase/native stack/ownership differs',line)
                require([v['entries'],v['returns'],v['compositions']]==counts,kind+' draw counters differ',line)
                require([v['flag'+str(i)] for i in range(10)]==[flag]+[0]*9,kind+' complete native flag vector differs',line)
                if shift is None:shift=v['shift']
                require(v['shift']==shift and 0<=shift<=21 and (v['mouse_x'],v['mouse_y'])==(54<<shift,719<<shift),kind+' shifted native mouse differs',line)
                require((v['buttons'],v['accumulator'])==(buttons,accumulator),kind+' controlled button/release state differs',line)
                if caller is not None:require(v['caller']==caller,kind+' native caller differs',line)
                for key,value in (registers or {}).items():require(v[key]==value,kind+' native '+key+' differs',line)
                return v,line
            entered,entered_line=obs('begin',20,0x406FA1,0)
            obs('post-push',21,0x423861,8,caller=entered['edx'])
            obs('portrait-hit',22,0x4238CA,68,registers=dict(esi=0,edi=0))
            obs('right-return',23,0x4238E3,68,registers=dict(eax=0,esi=0))
            obs('left-return',24,0x423937,68,registers=dict(eax=1,esi=0))
            before_xor,_=obs('xor-before',25,0x423952,68,registers=dict(eax=16,esi=0))
            flag=2-toggle
            after_xor,xor_line=obs('xor-after',26,0x42395A,68,registers=dict(esi=0))
            require(all(before_xor[k]==after_xor[k] for k in ('eax','ecx','edx','esi','edi','caller')),'memory XOR changed native GPR/stack contents',xor_line)
            def draw(route,phase,delta):
                counts[0]+=1;caller=packet['baseline_native_call_returns'][route+'_draw' if route=='native' else 'composition_draw']
                a,al=obs('draw-entry',phase,packet['baseline_observer_vas']['90'],delta,caller=caller)
                counts[1]+=1;counts[2]+=int(route=='composition')
                b,bl=obs('draw-'+route+'-return',phase,caller,delta-4,registers=dict(eax=1))
                require(all(a[k]==b[k] for k in ('ecx','edx','esi','edi')),'preserving draw helper changed native GPRs',bl)
            draw('native',26,188)
            obs('native-draw-return',27,0x423964,68)
            obs('map-entry',28,0x418700,72,caller=0x423970,registers=dict(eax=1,edx=0))
            draw('composition',28,312)
            map_return,_=obs('map-return',29,0x423970,68)
            release_before,_=obs('release-before',29,0x423970,68)
            buttons=accumulator=0
            release_after,release_line=obs('release-after',29,0x423970,68)
            require(all(map_return[k]==release_before[k]==release_after[k] for k in ('eax','ecx','edx','esi','edi','caller')),
                    'controlled release changed native GPR/stack contents',release_line)
            obs('release-entry',30,0x4609D0,72,caller=0x42397A,registers=dict(eax=0x544CD8,edx=0))
            obs('release-left-return',31,0x4609E0,84,registers=dict(eax=0))
            obs('release-right-return',32,0x4609FC,84,registers=dict(eax=0))
            obs('release-return',33,0x42397A,68,registers=dict(eax=0))
            obs('secondary-map-return',34,0x423989,68,registers=dict(eax=0,esi=0,edi=1))
            returned,return_line=obs('portrait-return',35,0x423A99,4,caller=0x406FA1,registers=dict(eax=1))
            require(all(entered[k]==returned[k] for k in ('ecx','edx','esi','edi')),'native portrait call failed to preserve GPRs',return_line)
            snapshot(toggle)
            if toggle==2:
                ready,ready_line=obs('ready',35,0x406FA1,0,registers=dict(eax=1))
                require(all(ready[k]==returned[k] for k in ('ecx','edx','esi','edi')),'GPRs changed after true native return',ready_line)
            toggles.append(dict(toggle=toggle,initial_flags=[toggle-1]+[0]*9,final_flags=[2-toggle]+[0]*9,
                                observations=records,draw_entries=counts[0],draw_returns=counts[1],composition_returns=counts[2]))
        _,stop_line=take('PTGL_HOST_READY')
        require(pos==len(events),'unexpected portrait records after final readiness')
        for n,text in enumerate(log.splitlines(),1):
            if n>stop_line and re.search(r'\b(?:PTILE_|SURFDUMP_(?:REDRAW|READY|PLAYGAME))',text,re.I):require(False,'game execution continued after stopped readiness',n)
        closes=[(n,t) for n,t in enumerate(log.splitlines(),1) if re.search(r'\bPTILE_TRACE_CLOSED\b',t,re.I)]
        require(len(closes)==1 and closes[0][1]==f'PTILE_TRACE_CLOSED tid={tid:x} eip=00406fa0 esp={sp:08x}' and closes[0][0]<handoff_line<begin_line,'initial closure/native handoff identity differs')
    except (KeyError,ValueError,TypeError) as error:require(False,str(error))
    army=[(n,t) for n,t in enumerate(log.splitlines(),1) if re.search(r'\bARMY_',t,re.I)]
    contract=f"ARMY_CONTRACT_PASS stage={packet['stage']} resolution=1024x768 candidate_sha256={packet['candidate_sha256']} revision={producer.base.builder.REVISION}"
    scope='ARMY_SCOPE own_player_0_to_3_native_size_panel manual_input_proof=false promotion_ready=false'
    require([t for _,t in army]==[contract,scope],'complete army loaded-byte contract/scope differs')
    first_events=[n for n,t in enumerate(log.splitlines(),1) if t.startswith('PTILE_EVENT ')]
    # The frozen compiler emits baseline checks before the initial extra. The
    # added portrait checks are inserted before its first NUMBERED breakpoint,
    # after that extra's ARMY/PTILE contracts, and still before any execution.
    # Authenticate this exact producer order; do not move/drop observed rows.
    startup_names=('PTGL_BASE_BYTES_PASS','ARMY_CONTRACT_PASS','ARMY_SCOPE',
                   'PTILE_CONTRACT_PASS','PTILE_SCOPE','PTGL_BYTES_PASS')
    startup=[]
    for name in startup_names:
        found=[n for n,text in enumerate(log.splitlines(),1) if text==name or text.startswith(name+' ')]
        require(len(found)==1,'exactly one startup '+name+' required')
        if len(found)==1:startup.append(found[0])
    require(len(startup)==6 and startup==sorted(set(startup)) and first_events and startup[-1]<first_events[0],
            'loaded byte/army/initial contracts differ from canonical producer startup order')
    require(len(snapshots)==3 and ready is not None,'three snapshots and final native return required')
    return dict(passed=not failures,failures=failures,raw_records=rows,baseline_draw_calls=baseline_draws,
                baseline_native_fallbacks=baseline_fallbacks,toggles=toggles,snapshots=snapshots,
                surface=snapshots[-1] if len(snapshots)==3 and ready else None,ready=ready)


def _result(packet,**updates):
    result=dict(schema='clash95_framed_army_portrait_trace_v1',passed=False,source_authenticated=False,
        whole_candidate_bound=False,all_supplemental_commands_bound=False,snapshot_headers_verified=False,
        ready_for_host_capture=False,stage=packet.get('stage') if isinstance(packet,dict) else None,
        portrait_sequence=None,initial_map_trace=None,initial_projection=None,surface=None,snapshots=[],source={},failures=[],
        runtime_accepted=False,pixels_verified=False,cleanup_verified=False,manual_input_proof=False,promotion_ready=False,limits=LIMITS)
    result.update(updates);return result


def evaluate_trace(log,packet):
    """Diagnostic only. This API never authenticates a caller-supplied packet."""
    report=_result(packet)
    try:
        if not isinstance(log,str):raise ValueError('decoded log text required')
        _packet(packet);sequence=_sequence(log,packet)
        report.update(portrait_sequence=sequence,surface=sequence['surface'],snapshots=sequence['snapshots'])
        report['failures'].extend(sequence['failures'])
        projected,extra,binding=selection._project(log,packet['initial_extra'],packet)
        initial=selection.initial_trace.evaluate_trace(projected,extra,resolution='1024x768',candidate_sha256=packet['candidate_sha256'],stage=selection.initial_trace.FRAMED_STAGE)
        report.update(initial_map_trace=initial,initial_projection=binding)
        report['failures'].extend('initial map: '+x for x in initial['failures'])
    except (KeyError,TypeError,ValueError,UnicodeError) as error:report['failures'].append(str(error))
    report['passed']=not report['failures'];return report


def evaluate_bound_trace(log,packet,*,original,candidate,save,generated_probe,supplemental_commands,snapshot_headers):
    """Reconstruct all commands and bind all three measured native headers."""
    source=dict(validator_sha256=sha(Path(__file__).read_bytes()),producer_sha256=sha(Path(producer.__file__).read_bytes()))
    report=None
    try:
        if not isinstance(log,str):raise ValueError('decoded log text required')
        _packet(packet)
        def sources():
            if sha(Path(producer.__file__).read_bytes())!=PRODUCER_SHA256:raise ValueError('reviewed portrait producer differs')
            for path,expected in HELPERS.items():
                if sha((producer.ROOT/path).read_bytes())!=expected:raise ValueError('reviewed trace helper differs: '+path)
        sources()
        if any(type(x) is not bytes for x in (original,candidate,save,generated_probe)):raise ValueError('immutable original/candidate/save/probe bytes required')
        rebuilt=producer.build_portrait_probe(original,candidate,save,capture_dir=packet['capture_dir'],minimap_viewport=packet['minimap_viewport'])
        sources()
        if rebuilt!=packet:raise ValueError('packet differs from entire source/candidate/save/command reconstruction')
        canonical=generated_probe.decode('ascii').replace('\r\n','\n')
        if canonical!=packet['compiled_probe']:raise ValueError('generated main probe differs from canonical packet')
        commands=packet['supplemental_commands']
        if not isinstance(supplemental_commands,dict) or set(supplemental_commands)!=set(commands):raise ValueError('all three exact actual supplemental files required')
        receipts={}
        for path,raw in supplemental_commands.items():
            if type(raw) is not bytes or raw.decode('ascii').replace('\r\n','\n')!=commands[path]:raise ValueError('actual supplemental bytes differ: '+path)
            receipts[path]=dict(raw_sha256=sha(raw),bytes=len(raw),canonical_lf_sha256=packet['supplemental_sha256'][path])
        source.update(original_sha256=sha(original),candidate_sha256=sha(candidate),save_sha256=sha(save),
            probe_raw_sha256=sha(generated_probe),probe_canonical_lf_sha256=sha(canonical.encode('ascii')),
            packet_sha256=sha(json.dumps(packet,sort_keys=True,separators=(',',':')).encode()),
            log_text_sha256=sha(log.encode()),supplemental_commands=receipts,helper_sha256=HELPERS)
        report=evaluate_trace(log,packet)
        report.update(source_authenticated=True,whole_candidate_bound=True,all_supplemental_commands_bound=True,source=source)
        paths={x['header_path'] for x in snapshot_paths(packet)}
        if not isinstance(snapshot_headers,dict) or set(snapshot_headers)!=paths:raise ValueError('all three exact measured snapshot headers required')
        header_receipts=[]
        for observed in report['snapshots']:
            path=observed['header_path'];raw=snapshot_headers[path]
            if type(raw) is not bytes or len(raw)!=188:raise ValueError('measured header must be188 bytes: '+path)
            width,height,base=struct.unpack_from('<HHI',raw);vtable=struct.unpack_from('<I',raw,0xB8)[0]
            if (width,height,base,vtable)!=(1024,768,observed['base'],0x50EE24):raise ValueError('measured header disagrees with paused observation: '+path)
            header_receipts.append(dict(path=path,sha256=sha(raw),bytes=len(raw),checkpoint=observed['checkpoint'],surface=observed['surface'],base=base,width=width,height=height,vtable=vtable))
        if len(header_receipts)!=3:report['failures'].append('three complete paused header observations unavailable')
        else:report['snapshot_headers_verified']=True
        source['snapshot_headers']=header_receipts
        report['passed']=not report['failures'];report['ready_for_host_capture']=report['passed'];return report
    except (KeyError,TypeError,ValueError,UnicodeError,OSError) as error:
        if report is not None:
            report['failures'].append(str(error));report.update(passed=False,ready_for_host_capture=False,snapshot_headers_verified=False)
            return report
        return _result(packet,source=source,failures=[str(error)])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('log','packet','original','candidate','save','probe'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args()
    try:
        packet=json.loads(args.packet.read_text(encoding='utf-8-sig'));_packet(packet);raw=args.log.read_bytes()
        report=evaluate_bound_trace(raw.decode('utf-8-sig'),packet,original=args.original.read_bytes(),candidate=args.candidate.read_bytes(),save=args.save.read_bytes(),
            generated_probe=args.probe.read_bytes(),supplemental_commands={path:Path(path).read_bytes() for path in packet['supplemental_commands']},
            snapshot_headers={x['header_path']:Path(x['header_path']).read_bytes() for x in snapshot_paths(packet)})
        report['source']['log_raw_sha256']=sha(raw)
    except (OSError,ValueError,UnicodeError) as error:report=_result(None,failures=[str(error)])
    print(json.dumps(report,indent=2));return 0 if report['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
