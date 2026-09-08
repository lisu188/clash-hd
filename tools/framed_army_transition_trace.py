#!/usr/bin/env python3
"""Offline six-step native transition validator, with complete input binding.

This tool never runs a debugger, captures pixels or writes evidence. Diagnostic
sequence acceptance is distinct from full source/candidate/command binding and
from the host's runtime, pixel and cleanup claims.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re

import framed_army_transition_probe as producer
import framed_army_selection_trace as selection

PRODUCER_SHA256 = '5e6807869583bd6850c98c14ae6e539ca93f6b43540773101a720266bcfceed5'
SELECTION_TRACE_SHA256 = '87523a32e3bd108998d03be16c98936549ddfe261c76e30b5ed58b88aa1164cc'
INITIAL_HELPERS = {
    'tools/initial_map_paint_trace.py':'845edda7ac563afe602dc3f6a388fe7e1874d6c6f128d1a938f8ce9ac2aa1021',
    'tools/partial_tile_trace_probe.py':'a20512fa49cc86db67a486f9202d4efa3f9f3745005d11220bf6097661a44729',
}
H = r'[0-9a-fA-F]{1,8}'
D = r'-?[0-9]{1,10}'
IDENTITY = rf'tid=(?P<tid>{H}) eip=(?P<eip>{H}) esp=(?P<esp>{H})'
STATE = rf'selected=(?P<selected>{D}) prior=(?P<prior>{D}) lower=(?P<lower>{D})'
SURFACE = rf'surface=(?P<surface>{H}) base=(?P<base>{H}) width=(?P<width>{D}) height=(?P<height>{D}) vtable=(?P<vtable>{H})'
PATTERNS = {
    'ATX_BYTES_PASS': re.compile('ATX_BYTES_PASS'),
    'ATX_OBS': re.compile(rf'ATX_OBS kind=(?P<kind>[a-z-]+) step=(?P<step>{D}) phase=(?P<phase>{D}) '+IDENTITY+' '+STATE+
        rf' owner=(?P<owner>{H}) gd=(?P<gd>{H}) eax=(?P<eax>{H}) ecx=(?P<ecx>{H}) edx=(?P<edx>{H}) esi=(?P<esi>{H}) caller=(?P<caller>{H}) '+
        rf'draws=\((?P<entries>{D}),(?P<returns>{D}),(?P<compositions>{D})\) maps=\((?P<maps>{D}),(?P<map_returns>{D})\)'),
    'ATX_SURFACE': re.compile(rf'ATX_SURFACE step=(?P<step>{D}) '+SURFACE),
    'ATX_READY': re.compile('ATX_READY '+IDENTITY+' '+STATE+rf' owner=(?P<owner>{H}) '+SURFACE),
    'ATX_HOST_READY': re.compile('ATX_HOST_READY'),
}
HEX = {'tid','eip','esp','owner','gd','eax','ecx','edx','esi','caller','surface','base','vtable'}
ERROR = re.compile(selection.ERROR.pattern + r'|ATX_REJECT|\b(?:SHSEL_|MCAP_|MODAL_)|\b(?:error 193|CreateProcess failed|memory access error)',re.I)
NATIVE_SITES = {'100':0x406FA1,'101':0x4080EF,'102':0x408131,'103':0x408136,
    '104':0x406980,'105':0x40A500,'106':0x423B00,'107':0x423B90,'108':0x423B40,
    '112':0x418700,'113':0x423B3C,'114':0x40A5EA,'115':0x423B64,'116':0x409DC8,
    '117':0x409D81,'118':0x409DA8,'119':0x409DB3}
LIMITS = [
    'Controlled direct native selection and Map-mode callbacks; ordinary map dispatch and manual input are not proved.',
    'Native draw return0 is disclosed legacy fallback. Each populated panel requires native and successful composition returns.',
    'Six stopped E0 identities do not authenticate pixels, artwork, final primary composition, cleanup or normal game exit.',
    'Sequence-only output cannot authorize capture; full original/candidate/save/probe and six supplemental-file reconstruction is required.',
]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def _packet(packet):
    if not isinstance(packet,dict):
        raise ValueError('packet must be an object')
    if (packet.get('schema'),packet.get('revision'),packet.get('stage'),packet.get('resolution'),packet.get('width'),packet.get('height')) != (
            'clash95_framed_army_transition_probe_v1',producer.REVISION,producer.base.builder.STAGE,'1024x768',1024,768):
        raise ValueError('unsupported transition packet identity')
    if packet.get('steps') != list(producer.STEPS):
        raise ValueError('exact six real-save transition steps required')
    if packet.get('save_sha256') != producer.base.SAVE_SHA256 or packet.get('original_sha256') != producer.base.clip.ORIGINAL_SHA256:
        raise ValueError('known original/save identity differs')
    for key in ('candidate_sha256','original_sha256','save_sha256'):
        if not isinstance(packet.get(key),str) or not re.fullmatch('[0-9a-f]{64}',packet[key]):
            raise ValueError('invalid packet '+key)
    for key in ('native_predicate_forced','selected_value_forced','runtime_executed','manual_input_proof','promotion_ready'):
        if packet.get(key) is not False:
            raise ValueError('packet cannot claim '+key)
    if packet.get('controlled_input') is not True or type(packet.get('minimap_viewport')) is not bool:
        raise ValueError('controlled route and minimap disclosure required')
    directory = producer.base.capture_directory(packet.get('capture_dir'))
    if directory != packet['capture_dir']:
        raise ValueError('canonical capture path required')
    for text_key,hash_key in (('compiled_probe','probe_sha256'),('initial_extra','initial_extra_sha256')):
        if not isinstance(packet.get(text_key),str) or sha(packet[text_key].encode('ascii')) != packet.get(hash_key):
            raise ValueError('embedded '+text_key+' hash differs')
    paths = {f'{directory}/transition-{n}.cdb' for n in range(1,7)}
    commands = packet.get('supplemental_commands'); hashes = packet.get('supplemental_sha256')
    if not isinstance(commands,dict) or not isinstance(hashes,dict) or set(commands)!=paths or set(hashes)!=paths:
        raise ValueError('exact six supplemental command files required')
    for name,text in commands.items():
        if not isinstance(text,str) or sha(text.encode('ascii'))!=hashes[name]:
            raise ValueError('supplemental command hash differs: '+name)
    sites=packet.get('observer_vas'); returns=packet.get('draw_return_vas')
    if not isinstance(sites,dict) or set(sites)!={str(n) for n in range(100,120)} or not isinstance(returns,dict) or set(returns)!={'native','composition'}:
        raise ValueError('complete observer and draw-return mapping required')
    if any(type(value) is not int or not 0x400000<=value<0x80000000 for value in sites.values()):
        raise ValueError('invalid native/emitted observer address')
    if any(sites[key]!=value for key,value in NATIVE_SITES.items()) or sites['110']!=returns['native'] or sites['111']!=returns['composition']:
        raise ValueError('native/emitted observer identity differs')
    if packet.get('map_return_vas')!={'open':0x423B3C,'switch':0x40A5EA,'close':0x423B64,'deselect':0x409DC8}:
        raise ValueError('native complete-map return mapping differs')


def _sequence(log,packet):
    failures=[]; rows=[]; events=[]; surfaces=[]; draw_calls=[]; map_calls=[]; steps=[]
    def require(ok,message,line=None):
        if not ok: failures.append((f'line {line}: ' if line else '')+message)
    for n,text in enumerate(log.splitlines(),1):
        if ERROR.search(text): require(False,'runtime/debugger failure retained',n)
        if re.search(r'\bATX_',text,re.I):
            marker=text.split(' ',1)[0]; pattern=PATTERNS.get(marker)
            match=pattern.fullmatch(text) if pattern else None
            values=({k:v if k=='kind' else int(v,16 if k in HEX else 10) for k,v in match.groupdict().items()} if match else None)
            row=dict(line=n,text=text,marker=marker,values=values);rows.append(row)
            if values is None:
                require(False,'malformed, prefixed or unknown transition record',n);continue
            for key,value in values.items():
                if key!='kind' and key not in HEX: require(-0x80000000<=value<=0x7fffffff,'decimal value outside signed x86 range',n)
            for key in ('tid','esp'):
                if key in values:require(values[key]>0 and (key!='esp' or values[key]>=0x10000 and values[key]%4==0),'invalid '+key,n)
            events.append(row)
    pos=0; tid=sp=gd=None; ready=None
    def take(marker,kind=None):
        nonlocal pos
        if pos>=len(events):
            raise ValueError('incomplete transition sequence: expected '+(kind or marker))
        row=events[pos];pos+=1;v=row['values']
        if row['marker']!=marker or kind is not None and v.get('kind')!=kind:
            raise ValueError(f"line {row['line']}: expected {kind or marker}, got {row['marker']} {v.get('kind','')}")
        return v,row['line']
    def peek(kind):
        return pos<len(events) and events[pos]['marker']=='ATX_OBS' and events[pos]['values'].get('kind')==kind
    try:
        _,byte_line=take('ATX_BYTES_PASS')
        previous_lower=0
        for step in packet['steps']:
            n=step['step']; populated=step['lower']==1; deselect=n==6
            counts=[0,0,0,0,0]
            pre=(step['old'],step['prior'],previous_lower)
            changed=(step['unit'],step['prior'],previous_lower)
            final=(step['unit'],step['unit'] if populated else -1,step['lower'])
            def obs(kind,phase,state,eip,esp=None,caller=None):
                nonlocal tid,sp,gd
                v,line=take('ATX_OBS',kind)
                if kind=='begin' and n==1:
                    tid,sp,gd=v['tid'],v['esp'],v['gd']
                    require(0x10000<=gd<=0xfff00000,'invalid game-data identity',line)
                require((v['step'],v['phase'],v['tid'],v['eip'],v['owner'],v['gd'])==
                        (n,phase,tid,eip,0x40AD40,gd),kind+' step/phase/thread/site/owner/game-data differs',line)
                require((v['selected'],v['prior'],v['lower'])==state,kind+' selection ownership differs',line)
                require([v[k] for k in ('entries','returns','compositions','maps','map_returns')]==counts,kind+' counters differ',line)
                if esp is not None:require(v['esp']==esp,kind+' native ESP differs',line)
                if caller is not None:require(v['caller']==caller,kind+' native caller differs',line)
                return v,line
            begin,line=obs('begin',1,pre,0x406FA0 if n==1 else 0x406FA1,sp)
            if not deselect:
                v,line=obs('occupancy',2,pre,0x4080EF,sp-24)
                require((v['esi'],v['ecx'],v['edx'])==(step['xy'][0],2*step['xy'][1],step['unit']),'actual occupancy/world registers differ',line)
                v,line=obs('selected',3,changed,0x408131,sp-24)
                require(v['eax']==1,'native selected result is not1',line)
                obs('updater',4,changed,0x406980,sp-4,0x406FA1)
            else:
                v,line=obs('deselect-entry',2,pre,0x409D81,sp-8)
                require(v['eax']==0x511D40,'Map-mode descriptor argument differs',line)
                v,line=obs('deselect-write',3,pre,0x409DA8,sp-16)
                require(v['ecx']==0xffffffff,'native deselect store operand differs',line)
            obs('panel-update',5,changed,0x40A500,sp-(20 if deselect else 48),0x409DB3 if deselect else 0x40A4F2)
            branch=step['branch']
            branch_site={'open':0x423B00,'switch':0x423B90,'close':0x423B40}[branch]
            branch_caller={'open':0x40A5F3,'switch':0x40A5EA,'close':0x40A51F}[branch]
            obs(branch,6,changed,branch_site,sp-(36 if deselect else 64),branch_caller)
            def draw(route,phase):
                counts[0]+=1
                entry,line=obs('draw-entry',phase,final,packet['observer_vas']['109'],caller=packet['draw_return_vas'][route])
                counts[1]+=1
                if route=='composition':counts[2]+=1
                returned,return_line=obs('draw-'+route+'-return',phase,final,packet['draw_return_vas'][route],entry['esp']+4)
                require(returned['eax'] in ((0,1) if route=='native' else (1,)),route+' draw status rejected',return_line)
                require(all(returned[k]==entry[k] for k in ('ecx','edx','esi')),route+' draw changed a preserved observed register',return_line)
                if route=='native':require(entry['esp']==sp-(192 if branch=='open' else 184),'native draw-helper stack depth differs',line)
                draw_calls.append(dict(step=n,route=route,entry=dict(entry,line=line),returned=dict(returned,line=return_line),
                                       relocated_draw=returned['eax']==1))
            if populated:draw('native',6)
            def full_map(route,phase,entry_sp):
                counts[3]+=1
                entry,line=obs('map-entry',phase,final,0x418700,entry_sp,packet['map_return_vas'][route])
                if populated:
                    start=counts[2]
                    while peek('draw-entry'):draw('composition',phase)
                    require(counts[2]>start,'complete map lacks successful composition',line)
                counts[4]+=1
                returned,ret_line=obs('map-return',phase+1,final,packet['map_return_vas'][route],entry_sp+4)
                require(all(returned[k]==entry[k] for k in ('ecx','edx','esi')),'complete map changed a preserved observed register',ret_line)
                map_calls.append(dict(step=n,route=route,entry=dict(entry,line=line),returned=dict(returned,line=ret_line)))
            map_sp=sp-(48 if deselect else 64 if branch=='switch' else 76)
            full_map(branch,7,map_sp)
            if deselect:
                obs('deselect-panel-return',8,final,0x409DB3,sp-16)
                full_map('deselect',9,sp-20)
            snap,snap_line=obs('snapshot',10 if deselect else 8,final,0x406FA1,sp)
            v,surface_line=take('ATX_SURFACE')
            require((v['step'],v['width'],v['height'],v['vtable'])==(n,1024,768,0x50EE24),'step surface geometry/vtable differs',surface_line)
            surfaces.append(dict(v,line=surface_line))
            steps.append(dict(step=n,name=step['name'],final_state=dict(selected=final[0],prior=final[1],lower=final[2]),
                              snapshot_line=snap_line,counters=dict(zip(('entries','returns','compositions','maps','map_returns'),counts))))
            previous_lower=step['lower']
        v,line=take('ATX_READY');ready=dict(v,line=line)
        require((v['tid'],v['eip'],v['esp'],v['selected'],v['prior'],v['lower'],v['owner'],v['width'],v['height'],v['vtable'])==
                (tid,0x406FA1,sp,-1,-1,0,0x40AD40,1024,768,0x50EE24),'final readiness differs',line)
        _,host_line=take('ATX_HOST_READY')
        require(pos==len(events),'extra transition record after complete readiness')
        for row in surfaces+[ready]:
            require(0x10000<=row['surface']<=0xffffff44 and row['surface']!=0x51D4C0 and 0x10000<=row['base']<=0x100000000-786432,'invalid E0 memory range',row['line'])
            require((row['surface'],row['base'])==(ready['surface'],ready['base']),'physical E0/pixels changed between steps',row['line'])
        closes=[(i,t) for i,t in enumerate(log.splitlines(),1) if re.search(r'\bPTILE_TRACE_CLOSED\b',t,re.I)]
        expected_close=f'PTILE_TRACE_CLOSED tid={tid:x} eip=00406fa0 esp={sp:08x}'
        require(len(closes)==1 and closes[0][1]==expected_close,'exact initial closure identity required')
        first=next(r['line'] for r in rows if r['values'] and r['values'].get('kind')=='begin')
        if closes:
            require(closes[0][0]<first,'transition begins before initial closure')
            for i,text in enumerate(log.splitlines(),1):
                if i>closes[0][0] and re.search(r'\b(?:PTILE_|SURFDUMP_(?:REDRAW|READY|PLAYGAME|HOST_READY))',text,re.I):
                    require(False,'map execution/marker after closed initial trace',i)
        contract=f"ARMY_CONTRACT_PASS stage={packet['stage']} resolution=1024x768 candidate_sha256={packet['candidate_sha256']} revision={producer.base.builder.REVISION}"
        scope='ARMY_SCOPE own_player_0_to_3_native_size_panel manual_input_proof=false promotion_ready=false'
        army=[(i,t) for i,t in enumerate(log.splitlines(),1) if re.search(r'\bARMY_',t,re.I)]
        require([t for _,t in army]==[contract,scope],'exact army contract and scope required')
        initial=[i for i,t in enumerate(log.splitlines(),1) if t.startswith('PTILE_EVENT ')]
        require(len(army)==2 and initial and byte_line<army[0][0]<army[1][0]<initial[0],'loaded byte contracts must precede execution')
    except (KeyError,TypeError,ValueError) as error:
        failures.append(str(error))
    return dict(passed=not failures,failures=failures,raw_records=rows,steps=steps,draw_calls=draw_calls,map_calls=map_calls,
                native_fallbacks=sum(d['route']=='native' and d['returned']['eax']==0 for d in draw_calls),
                surfaces=surfaces,surface=ready)


def _result(packet,**updates):
    report=dict(schema='clash95_framed_army_transition_trace_v1',passed=False,source_authenticated=False,
                whole_candidate_bound=False,all_supplemental_commands_bound=False,ready_for_host_capture=False,
                stage=packet.get('stage') if isinstance(packet,dict) else None,transition_sequence=None,
                initial_map_trace=None,initial_projection=None,surface=None,failures=[],runtime_accepted=False,
                pixels_verified=False,cleanup_verified=False,manual_input_proof=False,promotion_ready=False,limits=LIMITS)
    report.update(updates);return report


def evaluate_trace(log,packet):
    """Sequence diagnostics only; no packet or supplied hash becomes provenance."""
    report=_result(packet)
    try:
        if not isinstance(log,str):raise ValueError('decoded log text required')
        _packet(packet)
        seq=_sequence(log,packet);report['transition_sequence']=seq;report['surface']=seq['surface']
        report['failures'].extend(seq['failures'])
        projected,extra,binding=selection._project(log,packet['initial_extra'],packet)
        report['initial_projection']=binding
        initial=selection.initial_trace.evaluate_trace(projected,extra,resolution='1024x768',
                         candidate_sha256=packet['candidate_sha256'],stage=selection.initial_trace.FRAMED_STAGE)
        report['initial_map_trace']=initial;report['failures'].extend('initial map: '+f for f in initial['failures'])
    except (KeyError,TypeError,ValueError,UnicodeError) as error:report['failures'].append(str(error))
    report['passed']=not report['failures'];return report


def evaluate_bound_trace(log,packet,*,original,candidate,save,generated_probe,supplemental_commands):
    """Rebuild all six source files before accepting any stage projection.

    supplemental_commands must map every exact packet path to actual immutable
    bytes read from disk. No embedded command string substitutes for those bytes.
    Windows CRLF is recorded and canonicalized only to the producer's exact LF.
    """
    provenance={}
    try:
        provenance=dict(validator_sha256=sha(Path(__file__).read_bytes()),producer_sha256=sha(Path(producer.__file__).read_bytes()),
                        initial_projection_helper_sha256=sha(Path(selection.__file__).read_bytes()))
        if provenance['producer_sha256']!=PRODUCER_SHA256 or provenance['initial_projection_helper_sha256']!=SELECTION_TRACE_SHA256:
            raise ValueError('reviewed transition producer or projection helper source differs')
        helper_hashes={path:sha((producer.ROOT/path).read_bytes()) for path in INITIAL_HELPERS}
        if helper_hashes!=INITIAL_HELPERS:
            raise ValueError('reviewed initial trace/event helper source differs')
        provenance['initial_helpers_sha256']=helper_hashes
        if not isinstance(log,str):raise ValueError('decoded log text required')
        _packet(packet)
        if any(type(b) is not bytes for b in (original,candidate,save,generated_probe)):
            raise ValueError('immutable original/candidate/save/probe bytes required')
        if not isinstance(supplemental_commands,dict) or set(supplemental_commands)!=set(packet['supplemental_commands']) or any(type(b) is not bytes for b in supplemental_commands.values()):
            raise ValueError('actual bytes of all six exact supplemental paths required')
        rebuilt=producer.build_transition_probe(original,candidate,save,capture_dir=packet['capture_dir'],minimap_viewport=packet['minimap_viewport'])
        if sha(Path(producer.__file__).read_bytes())!=PRODUCER_SHA256:
            raise ValueError('transition producer changed during reconstruction')
        if rebuilt!=packet:raise ValueError('whole candidate/save/source/packet reconstruction differs')
        canonical=generated_probe.decode('ascii').replace('\r\n','\n')
        if canonical!=packet['compiled_probe']:raise ValueError('compiled probe differs from canonical packet')
        command_receipts={}
        for path,data in supplemental_commands.items():
            text=data.decode('ascii').replace('\r\n','\n')
            if text!=packet['supplemental_commands'][path]:raise ValueError('actual supplemental command differs: '+path)
            command_receipts[path]=dict(raw_sha256=sha(data),canonical_lf_sha256=sha(text.encode('ascii')),raw_bytes=len(data))
        provenance.update(original_sha256=sha(original),candidate_sha256=sha(candidate),save_sha256=sha(save),
            probe_raw_sha256=sha(generated_probe),probe_canonical_lf_sha256=sha(canonical.encode('ascii')),
            supplemental_commands=command_receipts,log_text_sha256=sha(log.encode()),
            packet_sha256=sha(json.dumps(packet,sort_keys=True,separators=(',',':')).encode()))
        report=evaluate_trace(log,packet)
        report.update(source_authenticated=True,whole_candidate_bound=True,all_supplemental_commands_bound=True,
                      ready_for_host_capture=report['passed'],source=provenance)
        return report
    except (KeyError,TypeError,ValueError,UnicodeError,OSError) as error:
        return _result(packet,failures=[str(error)],source=provenance)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('log','packet','original','candidate','save','probe'):
        parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args()
    try:
        packet=json.loads(args.packet.read_text(encoding='utf-8-sig'));_packet(packet)
        raw=args.log.read_bytes()
        report=evaluate_bound_trace(raw.decode('utf-8-sig'),packet,original=args.original.read_bytes(),candidate=args.candidate.read_bytes(),
            save=args.save.read_bytes(),generated_probe=args.probe.read_bytes(),
            supplemental_commands={path:Path(path).read_bytes() for path in packet['supplemental_commands']})
        report['source']['log_raw_sha256']=sha(raw)
    except (OSError,ValueError,UnicodeError) as error:report=_result(None,failures=[str(error)])
    print(json.dumps(report,indent=2));return 0 if report['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
