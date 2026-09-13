#!/usr/bin/env python3
"""Offline exact Complete-HD native whole-army movement trace validation.

The preserved native v3 sequence uses explicit complete-stage identities.
The copied selection baseline is parsed in its own namespace through READY;
no legacy stop marker is manufactured. Three measured headers bind the paused
E0 observations. Pixels, final primary composition and cleanup remain separate.
Native input may change inside pathfinding, cursor refresh and animation calls.
The three observed DD_Pump sites are paired, not an exhaustive input audit.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import struct

import complete_hd_army_movement_probe as producer
import complete_hd_army_selection_trace as selection
import framed_army_movement_state as state

PRODUCER_SHA256 = 'd048d355feffc6594c99c1a5f333bb55cc1ad654b6e463b00ae1bed8e9383e63'
HELPERS = {
    'tools/framed_army_movement_state.py': '32bd424b3933b3fb831659d715f0c576e9959818d0e123beb304684e21c8fbe7',
    'tools/complete_hd_army_selection_trace.py': 'bd00dd162ba0a085b18c1bfbe0a9b3c67117657a62fcec01fdd77ba2ad395528',
}
H, D = selection.frozen.H, selection.frozen.D
canonical = selection.canonical


def source_receipts():
    if sha(Path(producer.__file__).read_bytes()) != PRODUCER_SHA256:
        raise ValueError('reviewed complete movement producer differs')
    for path, expected in HELPERS.items():
        if sha((producer.ROOT / path).read_bytes()) != expected:
            raise ValueError('reviewed movement trace helper differs: ' + path)
    return selection.source_receipts() | producer.verify_sources() | HELPERS | {
        'tools/complete_hd_army_movement_trace.py': sha(Path(__file__).read_bytes())}


ID=rf'tid=(?P<tid>{H}) eip=(?P<eip>{H}) esp=(?P<esp>{H})'
PATTERNS={
    'WMOV_'+name:re.compile('WMOV_'+name+(' '+pattern if pattern else ''))
    for name,pattern in {
        'BYTES_PASS':'','HOST_READY':'',
        'CONTRACT':r'revision=(?P<revision>[a-z0-9_]+) candidate_sha256=(?P<candidate_hash>[0-9a-f]{64}) save_sha256=(?P<save_hash>[0-9a-f]{64}) source=\(16,19\) target=\(18,19\) clicks=2',
        'MOUSE':rf'click=(?P<click>{D}) '+ID+rf' raw=\((?P<mouse_x>{H}),(?P<mouse_y>{H})\) shift=(?P<shift>{H})',
        'PUMP':rf'kind=(?P<kind>[a-z-]+) count=(?P<count>{D}) phase=(?P<phase>{D}) '+ID+rf' eax=(?P<eax>{H}) edx=(?P<edx>{H}) raw=\((?P<mouse_x>{H}),(?P<mouse_y>{H})\) shift=(?P<shift>{H}) buttons=(?P<buttons>{H}) accumulator=(?P<accumulator>{H}) secondary=(?P<secondary>{H})',
        'SURFACE':rf'checkpoint=(?P<checkpoint>{D}) '+ID+rf' surface=(?P<surface>{H}) base=(?P<base>{H}) width=(?P<width>{D}) height=(?P<height>{D}) vtable=(?P<vtable>{H})',
        'OBS':rf'kind=(?P<kind>[a-z-]+) click=(?P<click>{D}) phase=(?P<phase>{D}) '+ID+
            rf' caller=(?P<caller>{H}) eax=(?P<eax>{H}) ebx=(?P<ebx>{H}) ecx=(?P<ecx>{H}) edx=(?P<edx>{H}) esi=(?P<esi>{H}) edi=(?P<edi>{H}) ebp=(?P<ebp>{H}) selected=(?P<selected>{D}) prior=(?P<prior>{D}) lower=(?P<lower>{D}) unit=(?P<unit>{H}) xy=\((?P<x>{D}),(?P<y>{D})\) path=\((?P<path_count>{D}),(?P<path0>{H}),(?P<path1>{H})\) ap=\('+','.join(rf'(?P<ap{i}>{D})' for i in range(8))+rf'\) occupancy=\((?P<occ0>{H}),(?P<occ1>{H}),(?P<occ2>{H})\) buttons=(?P<buttons>{H}) accumulator=(?P<accumulator>{H}) steps=(?P<steps>{D}) draws=\((?P<entries>{D}),(?P<returns>{D}),(?P<compositions>{D})\)',

    }.items()
}
PATTERNS.update({'WMOV_BASE_'+name:re.compile('WMOV_BASE_'+name+(' '+pattern if pattern else ''))
                 for name,pattern in selection.P.items() if name!='HOST_READY'})
HEX=selection.HEX|{'ebx','ecx','edx','esi','edi','ebp','unit','buttons','accumulator','secondary','path0','path1','occ0','occ1','occ2','mouse_x','mouse_y','shift'}
TEXT=selection.TEXT|{'kind','revision','candidate_hash','save_hash'}
ERROR=re.compile(selection.ERROR.pattern+r'|WMOV_(?:REJECT|BASE_REJECT|BASE_SELECTION_FAIL)|\b(?:SHSEL_|MCAP_|MODAL_|ATX_|PTGL_|MPRI_)|memory access error|CreateProcess failed|error 193',re.I)
SITES=dict(zip(range(100,133),(
    0x4084A1,0x4084AE,0x40856D,0x408594,0x408733,0x4087E1,0x4099E3,
    0x409A6C,0x4147A0,0x409A71,0x409AB5,0x409CA6,0x4609D0,0x4609E0,
    0x4609FC,0x409CAB,0x409CB5,0x409CBE,0x409BC5,0x409BCA,0x409C0E,
    0x410330,0x4108DF,0x4108E4,0x410747,0x410AF7,0x4105F7,0x410615,
    0x409C13,0x409C18,0x409C21,0x423050,0x409C81)))
PUMPS=[dict(kind=kind,call=call,returned=returned,phase=phase,stack_depth=depth,pending_identity=identity)
       for kind,call,returned,phase,depth,identity in (
           ('pathfinder',0x414B3F,0x414B44,29,388,1),
           ('animation',0x410DAE,0x410DB3,54,328,2),
           ('delay',0x410C91,0x410C96,51,328,3))]
SITES.update({133+2*n+delta:p[key] for n,p in enumerate(PUMPS) for delta,key in ((0,'call'),(1,'returned'))})
LIMITS=producer.LIMITS+[
    'Baseline READY continues into this protocol; no missing legacy stop marker is manufactured.',
    'Sequence-only diagnostics do not authenticate supplied artifacts or validate the initial-map event sequence; they cannot authorize host capture.',
    'Bound validation retains every observed event, including the full initial-map trace and final log tail, without namespace/stage projection or duplicate removal.',
    'Bound headers and army records establish the observed three checkpoints only. Pixel correctness, host ownership, cleanup and runtime acceptance are separate.',
    'The exact two-step desert cost5/10 route is checked here; the state helper independently reports all record deltas without a general movement-cost oracle.',
    'Input values are measured observations inside native pathfinding, cursor refresh and execution intervals. The three paired DD_Pump sites are not every backend call, OS-delivery proof or an input-stability assertion.',
]


def sha(data):return hashlib.sha256(data).hexdigest()


def snapshot_paths(packet):
    directory=packet['capture_dir']
    return [dict(checkpoint=n,header_path=f'{directory}/{name}.header.raw',raw_path=f'{directory}/{name}.raw',unit_path=f'{directory}/{name}.unit.raw')
            for n,name in enumerate(('movement-before','movement-preview','movement-after'))]


def _packet(packet):
    if type(packet) is not dict:raise ValueError('packet must be an object')
    canonical(packet)
    for key in ('width','height','unit','expected_path_count','mouse_shift_max','max_pump_calls_per_click'):
        if type(packet.get(key)) is not int:raise ValueError('exact integer packet field required: '+key)
    for key in ('source_xy','destination_xy','controlled_scroll','controlled_mouse','expected_initial_ap','expected_final_ap','expected_path_words'):
        if type(packet.get(key)) is not list or any(type(v) is not int for v in packet[key]):raise ValueError('exact integer packet vector required: '+key)
    resolution=packet.get('resolution')
    if resolution not in producer.base.builder.RESOLUTIONS:raise ValueError('unsupported complete movement resolution')
    width,height=map(int,resolution.split('x'))
    expected=('clash95_complete_hd_army_movement_probe_v1',producer.REVISION,producer.base.builder.STAGE,resolution,width,height)
    if tuple(packet.get(k) for k in ('schema','revision','stage','resolution','width','height'))!=expected:
        raise ValueError('unsupported movement packet identity')
    if (packet.get('unit'),packet.get('source_xy'),packet.get('destination_xy'),packet.get('controlled_scroll'),packet.get('controlled_mouse'),packet.get('expected_initial_ap'),packet.get('expected_final_ap'),packet.get('expected_path_count'),packet.get('expected_path_words'))!=(
            3,[16,19],[18,19],[10,17],[576,176],list(producer.INITIAL_AP),[v-10 for v in producer.INITIAL_AP],2,list(producer.PATH_WORDS)):
        raise ValueError('inspected army/route/AP/cost contract differs')
    if packet.get('mouse_shift_max')!=21:raise ValueError('signed-safe mouse shift contract differs')
    if packet.get('max_pump_calls_per_click')!=1024 or canonical(packet.get('pump_observers'))!=canonical(PUMPS):
        raise ValueError('exact three native pump pairs and count bound required')
    if packet.get('save_sha256')!=producer.base.SAVE_SHA256 or packet.get('original_sha256')!=producer.base.clip.ORIGINAL_SHA256:
        raise ValueError('known original/save identity differs')
    for key in ('candidate_sha256','original_sha256','save_sha256','candidate_manifest_canonical_sha256'):
        if not isinstance(packet.get(key),str) or not re.fullmatch('[0-9a-f]{64}',packet[key]):raise ValueError('invalid '+key)
    for key in ('native_predicate_forced','selected_value_forced','flag_value_forced','movement_state_forced','runtime_executed','manual_input_proof','promotion_ready'):
        if packet.get(key) is not False:raise ValueError('packet cannot claim '+key)
    if packet.get('controlled_input') is not True or packet.get('controlled_release') is not True or packet.get('minimap_viewport') is not True:
        raise ValueError('controlled route/release/profile disclosure required')
    if (packet.get('inherited_stage'),packet.get('inherited_revision'),packet.get('candidate_recipe')) != (
            selection.frozen.producer.builder.STAGE,selection.frozen.producer.builder.REVISION,producer.base.builder.REVISION):
        raise ValueError('complete recipe or inherited army identity differs')
    if packet.get('parent_source_sha256') != producer.PARENT_SOURCE_SHA256:
        raise ValueError('frozen native movement ancestry differs')
    if packet.get('capture_class') != 'e0_software_diagnostic':
        raise ValueError('software capture disclosure differs')
    if type(packet.get('source_sha256')) is not dict or not packet['source_sha256'] or type(packet.get('startup_recipe')) is not dict:
        raise ValueError('source and startup provenance required')
    if producer.base.capture_directory(packet.get('capture_dir'))!=packet['capture_dir']:raise ValueError('canonical capture path required')
    for content,digest in (('compiled_probe','probe_sha256'),('initial_extra','initial_extra_sha256')):
        if not isinstance(packet.get(content),str) or sha(packet[content].encode('ascii'))!=packet.get(digest):raise ValueError('embedded '+content+' differs')
    paths={f"{packet['capture_dir']}/movement-checkpoint-{n}.cdb" for n in range(3)}
    commands=packet.get('supplemental_commands');hashes=packet.get('supplemental_sha256')
    if not isinstance(commands,dict) or not isinstance(hashes,dict) or set(commands)!=paths or set(hashes)!=paths:
        raise ValueError('exact three supplemental commands required')
    for path,text in commands.items():
        if not isinstance(text,str) or sha(text.encode('ascii'))!=hashes[path]:raise ValueError('supplemental command hash differs')
    if packet.get('movement_observer_vas')!={str(n):va for n,va in SITES.items()}:raise ValueError('native movement observer mapping differs')
    sites=packet.get('baseline_observer_vas',{});returns=packet.get('baseline_native_call_returns',{})
    if not isinstance(sites,dict) or set(sites)!={str(n) for n in range(80,93)} or not isinstance(returns,dict):raise ValueError('complete baseline mappings required')
    if set(returns) != {'portraits','redraw','native_draw','composition_draw'} or any(type(v) is not int for v in returns.values()):
        raise ValueError('exact baseline return mapping required')
    fixed={80:0x406FA1,81:0x408131,82:0x408136,83:0x406980,84:0x40A500,
           85:0x423B00,86:0x423420,87:0x4080EF,88:0x423B32,89:0x423B3C}
    if any(type(v) is not int or not 0x400000<=v<0x80000000 for v in sites.values()) or any(sites[str(n)]!=va for n,va in fixed.items()):
        raise ValueError('native baseline observer mapping differs')
    if len({sites['90'],sites['91'],sites['92']})!=3:raise ValueError('draw observer sites must be distinct')
    if returns.get('portraits')!=0x423B32 or returns.get('redraw')!=0x423B3C:raise ValueError('baseline native return mapping differs')
    for name,n in (('native_draw',91),('composition_draw',92)):
        if type(returns.get(name)) is not int or not 0x400000<=returns[name]<0x80000000 or sites[str(n)]!=returns[name]:raise ValueError('emitted draw mapping differs')


def _sequence(log,packet):
    failures=[];rows=[];events=[];snapshots=[];baseline_draws=[];clicks=[];ready=None
    def require(ok,message,line=None):
        if not ok:failures.append((f'line {line}: ' if line else '')+message)
    for n,text in enumerate(log.splitlines(),1):
        if ERROR.search(text):require(False,'runtime/debugger failure retained',n)
        if re.search(r'\bWMOV_',text,re.I):
            marker=text.split(' ',1)[0];pattern=PATTERNS.get(marker);match=pattern.fullmatch(text) if pattern else None
            v={k:x if k in TEXT else int(x,16 if k in HEX else 10) for k,x in match.groupdict().items()} if match else None
            row=dict(line=n,text=text,marker=marker,values=v);rows.append(row)
            if v is None:require(False,'malformed, prefixed or unknown movement record',n);continue
            for key,value in v.items():
                if key not in TEXT|HEX:require(-0x80000000<=value<=0x7fffffff,'decimal value outside signed x86 range',n)
            for key in ('tid','esp'):
                if key in v:require(v[key]>0 and (key!='esp' or 0x10000<=v[key]<0x80000000 and v[key]%4==0),'invalid '+key,n)
            if marker not in ('WMOV_BYTES_PASS','WMOV_BASE_BYTES_PASS','WMOV_CONTRACT'):events.append(row)
        elif re.search(r'\bSURFDUMP_HOST_READY\b',text,re.I):require(False,'ordinary map readiness is forbidden',n)
    pos=0;tid=sp=gd=0;surface=None;baseline_fallbacks=0
    def take(marker,kind=None):
        nonlocal pos
        if pos>=len(events):raise ValueError('incomplete movement sequence: expected '+(kind or marker))
        row=events[pos];pos+=1;v=row['values']
        if row['marker']!=marker or kind is not None and v.get('kind')!=kind:
            raise ValueError(f"line {row['line']}: expected {kind or marker}, got {row['marker']} {v.get('kind','')}")
        return v,row['line']
    def baseline(name):return take('WMOV_BASE_'+name)
    def physical(v,line):
        require((v['width'],v['height'],v.get('vtable',0x50EE24))==(packet['width'],packet['height'],0x50EE24),'physical memory geometry/vtable differs',line)
        require(0x10000<=v['surface']<=0xffffff44 and v['surface']%4==0 and v['surface']!=0x51D4C0 and
                0x10000<=v['base']<=0x100000000-packet['width']*packet['height'],'physical surface/pixel range invalid',line)
        if surface:require((v['surface'],v['base'])==(surface['surface'],surface['base']),'E0/pixel ownership changed',line)
    def snapshot(n):
        v,line=take('WMOV_SURFACE');physical(v,line)
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
            while pos<len(events) and events[pos]['marker']=='WMOV_BASE_DRAW_ENTRY':
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
        checkpoint_states=[None,None,None]
        all_draws=[];all_pumps=[];mouse_records=[];run_shift=None
        for click in (1,2):
            records=[];counts=[0,0,0];steps=0;phase=20 if click==1 else 40
            pump_count=0;pathfinder_pumps=0;held=True
            expected_xy=(16,19);expected_ap=list(producer.INITIAL_AP)
            expected_queue=0 if click==1 else 2
            expected_occupancy=[3,0xffff,0xffff]
            def check_common(v,line,kind,*,depth=None,eip=None,caller=None,registers=None,check_state=True):
                require((v['click'],v['phase'],v['tid'],v['selected'],v['prior'],v['lower'],v['unit'],v['steps'])==
                        (click,phase,tid,3,3,1,gd+149349,steps),kind+' phase/thread/army/step identity differs',line)
                require(0<=v['buttons']<=3 and 0<=v['accumulator']<=255,kind+' native input field outside source bounds',line)
                if held:require((v['buttons'],v['accumulator'])==(1,0x80),kind+' initial controlled click differs',line)
                if kind.endswith('-release-after'):
                    require((v['buttons'],v['accumulator'])==(0,0),kind+' explicit release did not clear both input fields',line)
                if kind in ('release-entry','execute-entry'):
                    require(v['buttons']==0,kind+' native release entry buttons differ',line)
                require([v['entries'],v['returns'],v['compositions']]==counts,kind+' observed draw counters differ',line)
                if depth is not None:require(v['esp']==sp-depth,kind+' native stack differs',line)
                if eip is not None:require(v['eip']==eip,kind+' native observation site differs',line)
                if caller is not None:require(v['caller']==caller,kind+' native caller differs',line)
                for key,value in (registers or {}).items():require(v[key]==value,kind+' native '+key+' differs',line)
                require(0<=v['path_count']<=2 and all(0<=v['ap'+str(i)]<=255 for i in range(8)),kind+' native record scalar outside bounds',line)
                if check_state:
                    require((v['x'],v['y'])==expected_xy,kind+' native XY differs',line)
                    require([v['ap'+str(i)] for i in range(8)]==expected_ap,kind+' native AP/cost differs',line)
                    require(v['path_count']==expected_queue,kind+' native queue count differs',line)
                    require([v['occ'+str(i)] for i in range(3)]==expected_occupancy,kind+' native occupancy differs',line)
                if expected_queue and kind not in ('track-call','track-entry','track-return'):
                    require((v['path0'],v['path1'])==tuple(producer.PATH_WORDS),kind+' actual stored path/cumulative costs differ',line)
                records.append(dict(v,line=line))
            def consume_intervals():
                nonlocal pump_count,pathfinder_pumps
                # Native render callbacks may occur within a route phase. They
                # remain ordered, nonnested, thread/stack/caller paired, and
                # preserve every non-EAX GPR. State commits have their own
                # exact source sites; an animation-time draw is not a commit.
                while pos<len(events):
                    current=events[pos]
                    if current['marker']=='WMOV_PUMP':
                        a,al=take('WMOV_PUMP');kind=a['kind'].removesuffix('-call')
                        p=next((p for p in PUMPS if p['kind']==kind),None)
                        if p is None or a['kind']!=kind+'-call':raise ValueError('pump return lacks an immediately pending native call')
                        allowed=(click==1 and kind=='pathfinder' and steps==0 or click==2 and kind!='pathfinder' and steps in (1,2))
                        require(allowed and phase==p['phase'],'pump is outside its native movement phase/step',al)
                        pump_count+=1
                        require(pump_count<=1024,'native pump count exceeds bound',al)
                        b,bl=take('WMOV_PUMP',kind+'-return')
                        for v,line,site in ((a,al,p['call']),(b,bl,p['returned'])):
                            require((v['count'],v['phase'],v['tid'],v['eip'],v['esp'])==
                                    (pump_count,phase,tid,site,sp-p['stack_depth']),'pump count/phase/thread/site/native stack differs',line)
                            require(all(0<=v[k]<=255 for k in ('shift','accumulator','secondary')) and 0<=v['buttons']<=3,
                                    'native pump input fields outside measured source bounds',line)
                            require(all(0<=v[k]<=0xffffffff for k in ('mouse_x','mouse_y','eax','edx')),'native pump DWORD fields exceed x86 width',line)
                        require((a['eax'],a['edx'])==(0x544CD8,0),'native pump call input ABI differs',al)
                        # No returned EAX predicate or raw-input equality is
                        # invented: native polling may alter every input field.
                        pathfinder_pumps+=int(kind=='pathfinder')
                        all_pumps.append(dict(click=click,kind=kind,call=dict(a,line=al),returned=dict(b,line=bl)))
                        continue
                    if current['marker']!='WMOV_OBS' or current['values'].get('kind')!='draw-entry':break
                    a,al=take('WMOV_OBS','draw-entry');counts[0]+=1
                    require(counts[0]<=512 and counts[0]==counts[1]+1,'draw admission count/nesting differs',al)
                    check_common(a,al,'draw-entry',eip=packet['baseline_observer_vas']['90'],check_state=False)
                    require(sp-4096<=a['esp']<sp,'draw native stack outside observed call',al)
                    if a['caller']==packet['baseline_native_call_returns']['native_draw']:route='native'
                    elif a['caller']==packet['baseline_native_call_returns']['composition_draw']:route='composition'
                    else:raise ValueError('draw helper has unsupported native caller')
                    b,bl=take('WMOV_OBS','draw-'+route+'-return');counts[1]+=1;counts[2]+=int(route=='composition')
                    check_common(b,bl,'draw-'+route+'-return',eip=a['caller'],registers=dict(eax=1),check_state=False)
                    require(b['esp']==a['esp']+4,'draw RET stack pairing differs',bl)
                    require(all(a[k]==b[k] for k in ('ebx','ecx','edx','esi','edi','ebp')),'preserving draw helper changed GPRs',bl)
                    require(all(a[k]==b[k] for k in ('x','y','path_count','path0','path1')+tuple('ap'+str(i) for i in range(8))+tuple('occ'+str(i) for i in range(3))),
                            'draw helper changed captured army movement state',bl)
                    all_draws.append(dict(click=click,phase=phase,entry=dict(a,line=al),returned=dict(b,line=bl)))
            def obs(kind,next_phase,eip,depth,*,caller=None,registers=None):
                nonlocal phase
                consume_intervals();phase=next_phase
                v,line=take('WMOV_OBS',kind)
                check_common(v,line,kind,depth=depth,eip=eip,caller=caller,registers=registers)
                return v,line
            def release(kind,eip,depth):
                nonlocal held
                before,bl=obs(kind+'-release-before',phase,eip,depth)
                held=False
                after,al=obs(kind+'-release-after',phase,eip,depth)
                ignored={'kind','buttons','accumulator'}
                require(all(before[k]==after[k] for k in before if k not in ignored),'controlled release changed more than two input fields',al)
            measured,ml=take('WMOV_MOUSE')
            require((measured['click'],measured['tid'],measured['eip'],measured['esp'])==(click,tid,0x406FA1,sp),'controlled mouse checkpoint identity differs',ml)
            shift=measured['shift']
            require(0<=shift<=21,'controlled signed x86 mouse shift outside0..21',ml)
            if 0<=shift<=21:require((measured['mouse_x'],measured['mouse_y'])==(576<<shift,176<<shift),'actual raw mouse does not encode the requested destination',ml)
            if run_shift is None:run_shift=shift
            require(shift==run_shift,'native input shift changed between controlled clicks',ml)
            mouse_records.append(dict(measured,line=ml))
            entered,entered_line=obs('begin',phase,0x406FA1,0)
            if click==1:checkpoint_states[0]=entered
            else:checkpoint_states[1]=entered
            start_phase=phase
            obs('post-push',start_phase+1,0x4084A1,8,caller=entered['ebx'])
            obs('framed-admission-return',start_phase+2,0x4084AE,116,registers=dict(eax=0))
            obs('left-sample-return',start_phase+3,0x40856D,116,registers=dict(eax=1))
            obs('fog-return',start_phase+4,0x408594,116,registers=dict(eax=0xffffffff))
            obs('right-return',start_phase+5,0x408733,116,registers=dict(eax=0))
            obs('left-return',start_phase+6,0x4087E1,116,registers=dict(eax=1))
            obs('empty-target-return',start_phase+7,0x4099E3,116,registers=dict(eax=0,ebp=18))
            if click==1:
                obs('track-call',28,0x409A6C,120,caller=19,registers=dict(eax=3,edx=16,ecx=18,ebx=19))
                obs('track-entry',29,0x4147A0,124,caller=0x409A71,registers=dict(eax=3,edx=16,ecx=18,ebx=19))
                held=False
                found,fl=obs('track-return',30,0x409A71,116)
                require(pathfinder_pumps>=1,'native pathfinder lacks a completed DD_Pump pair',fl)
                require(0x10000<=found['eax']<=0xfffffe00,'native pathfinder returned invalid result allocation',fl)
                expected_queue=2
                obs('track-copied',31,0x409AB5,116)
                obs('preview-wait-call',32,0x409CA6,116)
                release('preview',0x409CA6,116)
                obs('release-entry',33,0x4609D0,120,caller=0x409CAB,registers=dict(eax=0x544CD8,edx=0))
                obs('release-left-return',34,0x4609E0,132,registers=dict(eax=0))
                obs('release-right-return',35,0x4609FC,132,registers=dict(eax=0))
                obs('release-return',36,0x409CAB,116,registers=dict(eax=0))
                obs('preview-redraw-return',37,0x409CB5,116)
                require(counts[0]==counts[1] and counts[2]>=1,'preview lacks completed native composition')
                returned,rl=obs('preview-ret',38,0x409CBE,4,caller=0x406FA1)
            else:
                obs('affordability-call',48,0x409BC5,116,registers=dict(eax=3))
                obs('affordability-return',49,0x409BCA,116,registers=dict(eax=1))
                obs('execute-call',50,0x409C0E,116,registers=dict(eax=3,edx=1))
                release('execute',0x409C0E,116)
                obs('execute-entry',51,0x410330,120,caller=0x409C13,registers=dict(eax=3,edx=1))
                for step in (1,2):
                    obs('spend-call',52,0x4108DF,328,registers=dict(eax=gd+149349,edx=5))
                    steps=step;expected_ap=[v-5*step for v in producer.INITIAL_AP]
                    obs('spend-return',53,0x4108E4,328)
                    expected_queue=2-step
                    obs('path-decrement',54,0x410747,328)
                    expected_xy=(16+step,19);expected_occupancy=[0xffff,3,0xffff] if step==1 else [0xffff,0xffff,3]
                    obs('xy-occupancy-commit',51,0x410AF7,328,registers=dict(edi=gd+149349))
                obs('execute-redraw-return',55,0x4105F7,328)
                require(counts[0]==counts[1] and counts[2]>=1,'settled move lacks completed native composition')
                obs('execute-ret',56,0x410615,120,caller=0x409C13)
                obs('execute-return',57,0x409C13,116)
                obs('updater-return',58,0x409C18,116)
                require(counts[0]==counts[1] and counts[2]>=1,'updater lacks completed native composition')
                returned,rl=obs('world-ret',59,0x409C21,4,caller=0x406FA1)
            require(all(entered[k]==returned[k] for k in ('ebx','ecx','edx','esi','edi','ebp')),'native world call failed to preserve GPRs',rl)
            snapshot(click)
            if click==2:
                ready,ready_line=obs('ready',59,0x406FA1,0)
                require(all(ready[k]==returned[k] for k in ('eax','ebx','ecx','edx','esi','edi','ebp')),'native return to sentinel changed registers',ready_line)
                checkpoint_states[2]=ready
            clicks.append(dict(click=click,observations=records,draw_entries=counts[0],draw_returns=counts[1],composition_returns=counts[2],steps=steps,pump_calls=pump_count,pathfinder_pump_calls=pathfinder_pumps))
        _,stop_line=take('WMOV_HOST_READY')
        require(pos==len(events),'unexpected movement records after final readiness')
        for n,text in enumerate(log.splitlines(),1):
            if n>stop_line and re.search(r'\b(?:PTILE_|SURFDUMP_(?:REDRAW|READY|PLAYGAME))',text,re.I):require(False,'game execution continued after stopped readiness',n)
        closes=[(n,t) for n,t in enumerate(log.splitlines(),1) if re.search(r'\bPTILE_TRACE_CLOSED\b',t,re.I)]
        require(len(closes)==1 and closes[0][1]==f'PTILE_TRACE_CLOSED tid={tid:x} eip=00406fa0 esp={sp:08x}' and closes[0][0]<handoff_line<begin_line,'initial closure/native handoff identity differs')
    except (KeyError,ValueError,TypeError) as error:require(False,str(error))
    army=[(n,t) for n,t in enumerate(log.splitlines(),1) if re.search(r'\bARMY_',t,re.I)]
    contract=f"ARMY_CONTRACT_PASS stage={packet['inherited_stage']} resolution={packet['resolution']} candidate_sha256={packet['candidate_sha256']} revision={packet['inherited_revision']}"
    scope='ARMY_SCOPE own_player_0_to_3_native_size_panel manual_input_proof=false promotion_ready=false'
    require([t for _,t in army]==[contract,scope],'complete army loaded-byte contract/scope differs')
    first_events=[n for n,t in enumerate(log.splitlines(),1) if t.startswith('PTILE_EVENT ')]
    startup_names=('WMOV_BASE_BYTES_PASS','ARMY_CONTRACT_PASS','ARMY_SCOPE','COMPLETEHD_CONTRACT_PASS','PTILE_CONTRACT_PASS','PTILE_SCOPE','WMOV_BYTES_PASS','WMOV_CONTRACT')
    startup=[]
    for name in startup_names:
        found=[n for n,text in enumerate(log.splitlines(),1) if text==name or text.startswith(name+' ')]
        require(len(found)==1,'exactly one startup '+name+' required')
        if len(found)==1:startup.append(found[0])
    require(len(startup)==8 and startup==sorted(set(startup)) and first_events and startup[-1]<first_events[0],
            'loaded byte/army/initial contracts differ from canonical producer startup order')
    movement_contract=f"WMOV_CONTRACT revision={producer.REVISION} candidate_sha256={packet['candidate_sha256']} save_sha256={packet['save_sha256']} source=(16,19) target=(18,19) clicks=2"
    require([r['text'] for r in rows if r['marker']=='WMOV_CONTRACT']==[movement_contract],'complete movement revision/candidate/save/route contract differs')
    failures.extend(selection._loaded_contracts(log,packet))
    require(len(snapshots)==3 and ready is not None,'three snapshots and final true native RET required')
    return dict(passed=not failures,failures=failures,raw_records=rows,baseline_draw_calls=baseline_draws,
                baseline_native_fallbacks=baseline_fallbacks,mouse=mouse_records if 'mouse_records' in locals() else [],clicks=clicks,draw_calls=all_draws if 'all_draws' in locals() else [],pump_calls=all_pumps if 'all_pumps' in locals() else [],snapshots=snapshots,
                checkpoint_states=checkpoint_states if 'checkpoint_states' in locals() else [],
                surface=snapshots[-1] if len(snapshots)==3 and ready else None,ready=ready)


def _result(packet, **updates):
    result=dict(schema='clash95_complete_hd_army_movement_trace_v1',passed=False,
        source_authenticated=False,whole_candidate_bound=False,candidate_manifest_bound=False,
        all_supplemental_commands_bound=False,snapshot_headers_verified=False,snapshot_units_verified=False,
        movement_state=None,ready_for_host_capture=False,
        stage=packet.get('stage') if type(packet) is dict else None,
        resolution=packet.get('resolution') if type(packet) is dict else None,
        movement_sequence=None,initial_map_trace=None,initial_log_projected=False,sequence_only=True,
        surface=None,snapshots=[],source={},failures=[],runtime_accepted=False,pixels_verified=False,
        cleanup_verified=False,manual_input_proof=False,promotion_ready=False,limits=LIMITS)
    result.update(updates)
    return result


def evaluate_trace(log, packet):
    """Untrusted diagnostic only; no initial-context or host-capture authority."""
    report=_result(packet)
    try:
        if type(log) is not str:raise ValueError('decoded log text required')
        _packet(packet)
        sequence=_sequence(log,packet)
        report.update(movement_sequence=sequence,surface=sequence['surface'],snapshots=sequence['snapshots'])
        report['failures'].extend(sequence['failures'])
    except (KeyError,TypeError,ValueError,UnicodeError,OSError) as error:
        report['failures'].append(str(error))
    report['passed']=not report['failures']
    return report


def evaluate_bound_trace(log, packet, *, original, candidate, save, candidate_manifest,
                         generated_probe, supplemental_commands):
    """Bind all four actual commands and the untouched complete initial log.

    Passing readiness precedes the host's independent memory reads. This API
    never treats log lines as proof that dump files exist or pixels are correct.
    """
    report=_result(packet)
    try:
        if type(log) is not str:raise ValueError('decoded log text required')
        if any(type(v) is not bytes for v in (original,candidate,save,generated_probe)):
            raise ValueError('immutable original/candidate/save/probe bytes required')
        if type(candidate_manifest) is not dict:raise ValueError('complete candidate manifest object required')
        _packet(packet)
        for name,data in (('original',original),('candidate',candidate),('save',save)):
            if sha(data)!=packet[name+'_sha256']:raise ValueError(name+' bytes differ from packet identity')
        manifest_json=canonical(candidate_manifest)
        if sha(manifest_json.encode())!=packet['candidate_manifest_canonical_sha256']:
            raise ValueError('candidate manifest canonical JSON differs from packet')
        sources=source_receipts()
        source=dict(source_sha256=sources,log_text_sha256=sha(log.encode()),
            original_sha256=sha(original),candidate_sha256=sha(candidate),save_sha256=sha(save),
            candidate_manifest_canonical_sha256=sha(manifest_json.encode()))
        report['source']=source
        rebuilt=producer.build_movement_probe(original,candidate,save,capture_dir=packet['capture_dir'],
            candidate_manifest=candidate_manifest,resolution=packet['resolution'])
        if canonical(rebuilt)!=canonical(packet):
            raise ValueError('packet differs from entire source/candidate/save/manifest reconstruction')
        command=generated_probe.decode('ascii').replace('\r\n','\n')
        if command!=packet['compiled_probe']:raise ValueError('actual main command differs from canonical packet')
        expected=packet['supplemental_commands']
        if type(supplemental_commands) is not dict or any(type(k) is not str for k in supplemental_commands) or set(supplemental_commands)!=set(expected):
            raise ValueError('all three exact actual supplemental files required')
        receipts={}
        for path,raw in supplemental_commands.items():
            if type(raw) is not bytes or raw.decode('ascii').replace('\r\n','\n')!=expected[path]:
                raise ValueError('actual supplemental bytes differ: '+path)
            receipts[path]=dict(raw_sha256=sha(raw),bytes=len(raw),canonical_lf_sha256=packet['supplemental_sha256'][path])
        source.update(probe_raw_sha256=sha(generated_probe),probe_canonical_lf_sha256=sha(command.encode('ascii')),
            packet_canonical_sha256=sha(canonical(packet).encode()),supplemental_commands=receipts)
        report=evaluate_trace(log,packet)
        report['source']=source
        initial=selection.initial_trace.evaluate_trace(log,packet['initial_extra'],resolution=packet['resolution'],
            candidate_sha256=packet['candidate_sha256'],stage=packet['stage'],candidate_manifest=candidate_manifest,original=original)
        report['initial_map_trace']=initial
        report['failures'].extend('initial map: '+error for error in initial['failures'])
        if source_receipts()!=sources:raise ValueError('movement trace sources changed during reconstruction')
        report.update(source_authenticated=True,whole_candidate_bound=True,candidate_manifest_bound=True,
            all_supplemental_commands_bound=True,sequence_only=False)
        report['passed']=not report['failures']
        report['ready_for_host_capture']=report['passed']
    except (KeyError,TypeError,ValueError,UnicodeError,OSError) as error:
        report['failures'].append(str(error))
        report.update(passed=False,ready_for_host_capture=False,source_authenticated=False,
            whole_candidate_bound=False,candidate_manifest_bound=False,all_supplemental_commands_bound=False)
    return report


def evaluate_bound_capture(log, packet, *, original, candidate, save, candidate_manifest,
                           generated_probe, supplemental_commands, snapshot_headers, snapshot_units):
    """Add three measured headers and full unit-record comparisons to readiness."""
    report=evaluate_bound_trace(log,packet,original=original,candidate=candidate,save=save,
        candidate_manifest=candidate_manifest,generated_probe=generated_probe,supplemental_commands=supplemental_commands)
    if not report['ready_for_host_capture']:return report
    source=report['source']
    sources=source['source_sha256']
    try:
        paths={x['header_path'] for x in snapshot_paths(packet)}
        if type(snapshot_headers) is not dict or any(type(k) is not str for k in snapshot_headers) or set(snapshot_headers)!=paths:
            raise ValueError('all three exact measured snapshot headers required')
        header_receipts=[]
        for observed in report['snapshots']:
            path=observed['header_path'];raw=snapshot_headers[path]
            if type(raw) is not bytes or len(raw)!=188:raise ValueError('measured header must be188 bytes: '+path)
            width,height,base=struct.unpack_from('<HHI',raw);vtable=struct.unpack_from('<I',raw,0xB8)[0]
            if (width,height,base,vtable)!=(packet['width'],packet['height'],observed['base'],0x50EE24):raise ValueError('measured header disagrees with paused observation: '+path)
            header_receipts.append(dict(path=path,sha256=sha(raw),bytes=len(raw),checkpoint=observed['checkpoint'],surface=observed['surface'],base=base,width=width,height=height,vtable=vtable))
        if len(header_receipts)!=3:report['failures'].append('three complete paused header observations unavailable')
        else:report['snapshot_headers_verified']=True
        source['snapshot_headers']=header_receipts
        unit_paths={x['unit_path'] for x in snapshot_paths(packet)}
        if type(snapshot_units) is not dict or any(type(k) is not str for k in snapshot_units) or set(snapshot_units)!=unit_paths:
            raise ValueError('all three exact measured 725-byte army records required')
        unit_receipts=[];state_inputs=[]
        states=report['movement_sequence']['checkpoint_states']
        if len(states)!=3 or any(v is None for v in states):raise ValueError('three source-observed checkpoint states unavailable')
        for observed,values in zip(report['snapshots'],states):
            path=observed['unit_path'];raw=snapshot_units[path]
            if type(raw) is not bytes or len(raw)!=725:raise ValueError('measured army record must be725 bytes: '+path)
            record=state.decode_unit(raw)
            if (record['xy']!=[values['x'],values['y']] or record['owner']!=0 or record['path_count']!=values['path_count'] or
                [s['ap'] for s in record['slots'][:8]]!=[values['ap'+str(i)] for i in range(8)] or
                struct.unpack_from('<II',raw,320)!=(values['path0'],values['path1'])):
                raise ValueError('measured army record disagrees with actual checkpoint state: '+path)
            unit_receipts.append(dict(path=path,sha256=sha(raw),bytes=725,checkpoint=observed['checkpoint'],unit=values['unit']))
            # These context values are guarded by the exact reconstructed own
            # predicate before each emitted snapshot/OBS. They are not values
            # inferred from pixel appearance or from the record's existence.
            state_inputs.append(state.MovementSnapshot(raw,values['selected'],values['prior'],0,(0,)*10))
        comparison=state.compare_movement_state(original,save,baseline=state_inputs[0],preview=state_inputs[1],settled=state_inputs[2],destination=(18,19))
        report['movement_state']=comparison;source['snapshot_units']=unit_receipts
        source['checkpoint_context_origin']='selected/prior are raw OBS fields; player0 and ten zero flags are prerequisites of the source-bound emitted checkpoint predicates'
        if not comparison['passed']:report['failures'].extend('movement state: '+x for x in comparison['failures'])
        report['snapshot_units_verified']=len(unit_receipts)==3
        try:
            if source_receipts() != sources:raise ValueError('movement trace sources changed during capture validation')
        except (OSError,ValueError):
            report.update(source_authenticated=False,whole_candidate_bound=False,candidate_manifest_bound=False,
                all_supplemental_commands_bound=False)
            raise
        report['passed']=not report['failures']
        report['ready_for_host_capture']=report['passed']
        return report
    except (KeyError,TypeError,ValueError,UnicodeError,OSError) as error:
        report['failures'].append(str(error))
        report.update(passed=False,ready_for_host_capture=False,snapshot_headers_verified=False,snapshot_units_verified=False)
        return report


def _existing_snapshots(paths):
    # Missing files remain missing in the strict required-set comparison. This
    # preserves the already parsed native failure instead of discarding it in
    # the CLI before evaluation. Other I/O errors remain explicit failures.
    result={}
    for path in paths:
        try:result[path]=Path(path).read_bytes()
        except FileNotFoundError:pass
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('log','packet','original','candidate','save','probe','candidate-manifest'):parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--captured-snapshots',action='store_true',help='also require all three measured header and army files')
    args=parser.parse_args()
    try:
        packet=producer.base.read_manifest(args.packet);_packet(packet);raw=args.log.read_bytes()
        inputs=dict(original=args.original.read_bytes(),candidate=args.candidate.read_bytes(),save=args.save.read_bytes(),
            candidate_manifest=producer.base.read_manifest(args.candidate_manifest),generated_probe=args.probe.read_bytes(),
            supplemental_commands={path:Path(path).read_bytes() for path in packet['supplemental_commands']})
        if args.captured_snapshots:
            inputs.update(snapshot_headers=_existing_snapshots(x['header_path'] for x in snapshot_paths(packet)),
                snapshot_units=_existing_snapshots(x['unit_path'] for x in snapshot_paths(packet)))
            report=evaluate_bound_capture(raw.decode('utf-8-sig'),packet,**inputs)
        else:report=evaluate_bound_trace(raw.decode('utf-8-sig'),packet,**inputs)
        report['source']['log_raw_sha256']=sha(raw)
    except (OSError,ValueError,UnicodeError) as error:report=_result(None,failures=[str(error)])
    print(json.dumps(report,indent=2));return 0 if report['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
