#!/usr/bin/env python3
"""Compile/validate the constructed initial battle protocol, without runtime.

Sequence-only observations never authorize a host read. Full validation binds
the unchanged save, original, whole candidate, packet and generated probe
before projecting exactly one initial-map stage token to its existing parser.
Every malformed, repeated or rejected battle record remains in the report.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re

import framed_battle_initial_probe as producer
import initial_map_paint_trace

sha = producer.sha
H = r"[0-9a-fA-F]{1,8}"
D = r"[0-9]{1,10}"
S = r"[a-z0-9_-]+"
SHA = r"[a-f0-9]{64}"
ID = rf"tid=(?P<tid>{H}) eip=(?P<eip>{H}) esp=(?P<esp>{H})"
P = {
    'BINIT_BYTE_CONTRACT_PASS': rf"candidate_sha256=(?P<sha>{SHA}) route=(?P<route>{S})",
    'BINIT_CONTRACT': rf"stage=(?P<stage>{S}) resolution=(?P<resolution>[0-9]{{3,4}}x[0-9]{{3,4}}) candidate_sha256=(?P<sha>{SHA}) save_sha256=(?P<save_sha>{SHA}) route=(?P<route>{S}) protocol=(?P<protocol>{S}) runtime_acceptance=0",
    'BINIT_HANDOFF': ID+rf" gd=(?P<gd>{H}) surface=(?P<surface>{H}) base=(?P<base>{H}) size=\((?P<width>{D}),(?P<height>{D})\) owner=0040ad40 player=0",
    'BINIT_INACTIVE': ID+rf" event=(?P<event>HANDOFF|READY) state=(?P<state>{H}) checked_bytes=128 all_zero=1",
    'BINIT_FORCE_CALL': ID+" entry=0041ad20 attacker=0 defender=4 ebx=0 sentinel=00406fa1 forced=1",
    'BINIT_PROLOGUE': ID+" after_first_push=1 saved_ebx=0 sentinel=00406fa1",
    'BINIT_ACTORS': ID+rf" gd=(?P<gd>{H}) attacker=(?P<attacker>{H}) defender=(?P<defender>{H}) old_attacker_xy=\(14,22\) defender_xy=\(90,9\) owners=\(0,1\) first_types=\(5,5\) squad_counts=\(1,1\) map=\(100,100\) control_flags=\(1,0\)",
    'BINIT_MUTATION': ID+rf" xy_address=(?P<xy_address>{H}) old_xy=(?P<old_xy>{H}) new_xy=00090059 flag_address=0051d01c old_flag=(?P<old_flag>{H}) new_flag=1 isolated_fixture=1",
    'BINIT_MUTATION_DONE': ID+rf" xy_address=(?P<xy_address>{H}) xy=(?P<xy>{H}) flag=(?P<flag>{H})",
    'BINIT_ELIGIBLE': ID+rf" eax=(?P<eax>{H}) attacker=(?P<attacker>{H})",
    'BINIT_UI_GATE': ID+rf" ecx=(?P<ecx>{H}) flag=(?P<flag>{H})",
    'BINIT_RUNNER_CALL': ID+rf" attacker=(?P<attacker>{H}) defender=(?P<defender>{H}) ebx=(?P<ebx>{H}) ecx=(?P<ecx>{H}) argument=(?P<argument>{H})",
    'BINIT_RUNNER_ENTRY': ID+rf" attacker=(?P<attacker>{H}) defender=(?P<defender>{H}) caller=(?P<caller>{H}) argument=(?P<argument>{H})",
    'BINIT_PRESENT_CALL': ID+rf" target=0051ba00 battle=(?P<battle>{H}) owner=(?P<owner>{H}) player=(?P<player>{D}) selected=(?P<selected>{D}) selected_type=(?P<selected_type>{D}) resources=\((?P<background>{H}),(?P<buttons>{H}),(?P<animation>{H}),(?P<corpses>{H}),(?P<frame>{H})\)",
    'BINIT_WRAPPER_ENTRY': ID+rf" caller=(?P<caller>{H}) cursor=(?P<cursor>{H})",
    'BINIT_PRESENT_RETURN': ID+" caller=0042f2f5 wrapper=0051ba00",
    'BINIT_SURFDUMP_READY': ID+rf" surface=(?P<surface>{H}) base=(?P<base>{H}) size=\((?P<width>{D}),(?P<height>{D})\) bytes=(?P<bytes>{D}) vtable=0050ee24 owner=0042e8b0 state=(?P<state>{H}) capture=physical_battle_e0 manual_input_proof=0",
    'BINIT_SURFDUMP_HOST_READY': '',
}
REGEX = {k:re.compile(k+(' '+v if v else '')) for k,v in P.items()}
TEXT = {'sha','stage','resolution','save_sha','route','protocol','event'}
DECIMAL = {'width','height','bytes','player','selected','selected_type'}
ORDER = ['BYTE_CONTRACT_PASS','CONTRACT','HANDOFF','INACTIVE','FORCE_CALL','PROLOGUE','ACTORS',
         'MUTATION','MUTATION_DONE','ELIGIBLE','UI_GATE','RUNNER_CALL','RUNNER_ENTRY','PRESENT_CALL',
         'WRAPPER_ENTRY','PRESENT_RETURN','INACTIVE','SURFDUMP_READY','SURFDUMP_HOST_READY']
DEPTHS = [(None,None),(None,None),(0x406FA0,0),(0x406FA0,0),(0x406FA0,0),
          (0x41AD21,8),(0x41AD21,8),(0x41AD21,8),(0x41AD21,8),(0x41AE05,860),
          (0x41B05E,860),(0x41B145,864),(0x42E9E0,868),(0x42F2F5,1036),
          (0x51BA00,1040),(0x42F2FA,1036),(0x42F2FA,1036),(0x42F2FA,1036),(None,None)]


def compile_probe(packet):
    return producer.compiler.compile_probe(packet)


def evaluate_sequence(log, packet):
    failures, rows = [], []
    def fail(text, line=None):
        failures.append((f'line {line}: ' if line else '')+text)
    def require(ok,text,line=None):
        if not ok: fail(text,line)
    try:
        width,height=map(int,packet['resolution'].split('x'))
        if (packet['stage'],packet['route'],packet['protocol_revision'],packet['save_sha256']) != (
                producer.STAGE,producer.ROUTE,producer.PROTOCOL,producer.SAVE_SHA256):
            raise ValueError('unsupported stage/route/protocol/save')
    except (KeyError,TypeError,ValueError,AttributeError) as error:
        return dict(sequence_passed=False,ready_for_host_capture=False,source_authenticated=False,
                    failures=[str(error)],raw_records=rows,surface=None)
    for n,text in enumerate(log.splitlines(),1):
        if re.search(r'BINIT_REJECT|AV_SURFDUMP|SURFDUMP_INVALID|SURFDUMP_APP_REQUEST_QUIT|PTILE_REJECT|MCANVAS_CONTRACT_FAIL|\bMCAP_|\bMODAL_|syntax error|couldn.t resolve|access violation',text,re.I):
            fail('runtime/probe rejection or debugger error',n)
        if re.search(r'\bBINIT_',text,re.I):
            marker=text.split(' ',1)[0]
            match=REGEX.get(marker)
            match=match.fullmatch(text) if match else None
            row=dict(line=n,marker=marker,text=text,values=None)
            if match:
                row['values']={k:v if k in TEXT else int(v,10 if k in DECIMAL else 16) for k,v in match.groupdict().items()}
            else: fail('unknown, malformed or prefixed battle record',n)
            rows.append(row)
        elif re.search(r'\bSURFDUMP_HOST_READY\b',text):
            fail('ordinary-map host-ready is forbidden in this battle lane',n)
    require([r['marker'] for r in rows]==['BINIT_'+x for x in ORDER],
            'battle sequence is missing, duplicated, out of order or contains extra records')
    # First values are useful diagnostics only; the ordered list above rejects
    # all duplicates rather than silently merging them into a passing report.
    first={}
    for r in rows:
        if r['values'] is not None: first.setdefault(r['marker'],r['values'])
    def v(name):return first.get('BINIT_'+name,{})
    contract=v('CONTRACT')
    for name in ('BYTE_CONTRACT_PASS','CONTRACT'):
        require(v(name).get('sha')==packet.get('candidate_sha256') and v(name).get('route')==producer.ROUTE,
                'loaded candidate/route contract mismatch')
    require((contract.get('stage'),contract.get('resolution'),contract.get('save_sha'),contract.get('protocol'))==
            (producer.STAGE,packet['resolution'],producer.SAVE_SHA256,producer.PROTOCOL),'startup contract differs')
    h=v('HANDOFF');tid=h.get('tid',0);sp=h.get('esp',0);gd=h.get('gd',0)
    require(0<tid<=0xffffffff and 0x10000<=sp<=0xffffffff and sp%4==0,'handoff thread/stack invalid')
    require(0x10000<=gd<=0xfff00000,'game-data pointer invalid')
    for r,(name,(eip,depth)) in zip(rows,zip(ORDER,DEPTHS)):
        values=r['values'] or {}
        if eip is not None:
            require((values.get('tid'),values.get('eip'),values.get('esp'))==(tid,eip,sp-depth)
                    and 0x10000<=sp-depth<=0xffffffff,
                    f'{name} native thread/EIP/ESP differs',r['line'])
    inactive=[r for r in rows if r['marker']=='BINIT_INACTIVE']
    require([(r['values'] or {}).get('event') for r in inactive]==['HANDOFF','READY'],'inactive state observations differ')
    for r in inactive:
        require((r['values'] or {}).get('state')==packet.get('canvas_state_va'),'wrong inactive modal state',r['line'])
    a=v('ACTORS');attacker=gd+producer.UNIT_BASE;defender=attacker+4*producer.UNIT_SIZE
    require((a.get('gd'),a.get('attacker'),a.get('defender'))==(gd,attacker,defender),'actor addresses differ')
    mut=v('MUTATION');done=v('MUTATION_DONE')
    require((mut.get('xy_address'),mut.get('old_xy'))==(attacker,0x0016000e),'old actor mutation binding differs')
    require((done.get('xy_address'),done.get('xy'),done.get('flag'))==(attacker,0x00090059,1),'actual mutation readback differs')
    require((v('ELIGIBLE').get('eax'),v('ELIGIBLE').get('attacker'))==(1,attacker),'native eligibility failed or wrong actor')
    require((v('UI_GATE').get('ecx'),v('UI_GATE').get('flag'))==(1,1),'native UI gate failed')
    for name in ('RUNNER_CALL','RUNNER_ENTRY'):
        r=v(name)
        require((r.get('attacker'),r.get('defender'),r.get('argument'))==(attacker,defender,0),'runner actor/argument ABI differs')
    require((v('RUNNER_CALL').get('ebx'),v('RUNNER_CALL').get('ecx'))==(0,0),'unit-versus-unit native boolean ABI differs')
    require(v('RUNNER_ENTRY').get('caller')==0x41B14A,'runner native return differs')
    p=v('PRESENT_CALL')
    require(0x10000<=p.get('battle',0)<=0xffffe000 and p.get('owner')==0x42e8b0
            and 0<=p.get('player',99)<=4 and 0<=p.get('selected',99)<=21 and 0<=p.get('selected_type',99)<=40,
            'battle data/owner/player/selection invalid')
    require(all(0<p.get(k,0)<=0xffffffff for k in ('background','buttons','animation','corpses','frame')),
            'battle resources missing')
    require((v('WRAPPER_ENTRY').get('caller'),v('WRAPPER_ENTRY').get('cursor'))==(0x42F2FA,0x544CD8),
            'inherited present wrapper call differs')
    ready=v('SURFDUMP_READY')
    for r in (h,ready):
        require((r.get('width'),r.get('height'))==(width,height),'physical E0 dimensions differ')
        require(0x10000<=r.get('surface',0)<=0xffffff44 and r.get('surface')!=0x51d4c0
                and 0x10000<=r.get('base',0)<=0x100000000-width*height,'physical E0 pointer range invalid')
    require((ready.get('surface'),ready.get('base'))==(h.get('surface'),h.get('base')),'physical E0/pixels changed since handoff')
    require(ready.get('bytes')==width*height and ready.get('state')==packet.get('canvas_state_va'),'ready byte count/state differs')
    loaded=(f"MCANVAS_CONTRACT_PASS stage={producer.STAGE} resolution={packet['resolution']} "
            f"candidate_sha256={packet.get('candidate_sha256')} revision={producer.builder.REVISION} "
            f"state={packet.get('canvas_state_va',0):08x} state_bytes=4096")
    loaded_rows=[(n,t) for n,t in enumerate(log.splitlines(),1) if re.search(r'\bMCANVAS_',t,re.I)]
    require([t for _,t in loaded_rows]==[loaded,'MCANVAS_SCOPE owned_castle_canvas_only manual_input_proof=false promotion_ready=false'],
            'whole modal-candidate loaded-byte contract/scope differs')
    if len(rows)>=2 and len(loaded_rows)==2:
        require(rows[0]['line']<loaded_rows[0][0]<loaded_rows[1][0]<rows[1]['line'],
                'native/whole-candidate/startup loaded contracts out of order')
    closes=[(n,t) for n,t in enumerate(log.splitlines(),1) if 'PTILE_TRACE_CLOSED' in t]
    expected_close=f'PTILE_TRACE_CLOSED tid={tid:x} eip=00406fa0 esp={sp:08x}'
    require(len(closes)==1 and closes[0][1]==expected_close,'initial-map closure identity differs')
    if len(closes)==1 and len(rows)>2: require(closes[0][0]<rows[2]['line'],'battle handoff precedes initial-map closure')
    hosts=[r['line'] for r in rows if r['marker']=='BINIT_SURFDUMP_HOST_READY']
    if hosts:
        for n,t in enumerate(log.splitlines(),1):
            if n>hosts[0] and re.search(r'\b(?:SURFDUMP_(?:REDRAW|READY|PLAYGAME)|PTILE_)',t,re.I):
                fail('game/map trace continued after paused battle readiness',n)
    return dict(sequence_passed=not failures,ready_for_host_capture=False,source_authenticated=False,
        raw_records=rows,failures=failures,surface=ready or None,
        mutation=mut or None,manual_input_proof=False,promotion_ready=False)


def evaluate_trace(log, *, original, candidate, save, packet, generated_probe):
    failures=[];sequence=None;initial=None;projection=None
    source=dict(original_sha256=sha(original),candidate_sha256=sha(candidate),save_sha256=sha(save),
        generated_probe_sha256=sha(generated_probe),log_sha256=sha(log.encode('utf8')),
        validator_sha256=sha(Path(__file__).read_bytes()))
    if not isinstance(packet,dict):packet={};failures.append('packet must be an object')
    try:
        rebuilt=producer.build_probe(original,candidate,save,candidate_sha256=packet['candidate_sha256'],
            stage=packet['stage'],resolution=packet['resolution'],route=packet['route'],
            minimap_viewport=packet['minimap_viewport'])
        if rebuilt!=packet:raise ValueError('packet differs from exact current source/save/candidate reconstruction')
        compiled=compile_probe(rebuilt)
        observed=generated_probe.decode('ascii').replace('\r\n','\n')
        source['generated_probe_canonical_lf_sha256']=sha(observed.encode('ascii'))
        if observed!=compiled:raise ValueError('whole generated probe differs from canonical battle compilation')
        sequence=evaluate_sequence(log,packet);failures.extend(sequence['failures'])
        _,_,extra,_=producer.canonical_template(original,packet['resolution'],minimap_viewport=packet['minimap_viewport'])
        projected_log,projected_extra,projection=producer.compiler._project_initial(log,extra,packet)
        initial=initial_map_paint_trace.evaluate_trace(projected_log,projected_extra,resolution=packet['resolution'],
            candidate_sha256=packet['candidate_sha256'],stage=producer.builder.BASE_STAGE)
        failures.extend('initial map trace: '+f for f in initial['failures'])
        contracts=[r for r in sequence['raw_records'] if r['marker']=='BINIT_CONTRACT']
        events=initial['event_integrity']['events']
        if len(contracts)!=1 or not events or contracts[0]['line']>=events[0]['line']:
            failures.append('battle startup contract must precede initial map execution')
    except (KeyError,TypeError,ValueError,UnicodeError,OSError) as error:failures.append(str(error))
    return dict(schema='clash95_framed_battle_initial_trace_v1',passed=not failures,ready_for_host_capture=not failures,
        stage=packet.get('stage'),resolution=packet.get('resolution'),route=packet.get('route'),
        candidate_sha256=sha(candidate),source=source,battle_sequence=sequence,initial_map_trace=initial,
        initial_map_projection=projection,surface=sequence.get('surface') if sequence else None,failures=failures,
        runtime_accepted=False,cleanup_verified=False,manual_input_proof=False,promotion_ready=False,limits=producer.LIMITS)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--prepare',action='store_true')
    for name in ('original','candidate','save','log','packet','probe'):
        p.add_argument('--'+name,type=Path,required=name in ('original','candidate','save'))
    for name in ('candidate-sha256','stage','resolution','route'):p.add_argument('--'+name)
    p.add_argument('--minimap-viewport',action='store_true')
    a=p.parse_args()
    try:
        original,candidate,save=a.original.read_bytes(),a.candidate.read_bytes(),a.save.read_bytes()
        if a.prepare:
            if not all((a.candidate_sha256,a.stage,a.resolution,a.route)):raise ValueError('prepare requires SHA/stage/resolution/route')
            packet=producer.build_probe(original,candidate,save,candidate_sha256=a.candidate_sha256,stage=a.stage,
                resolution=a.resolution,route=a.route,minimap_viewport=a.minimap_viewport)
            compiled=compile_probe(packet)
            report=dict(prepared=True,runtime_ready=False,packet=packet,probe=compiled,probe_sha256=sha(compiled.encode('ascii')))
        else:
            if not all((a.log,a.packet,a.probe)):raise ValueError('validation requires log/packet/probe')
            raw=a.log.read_bytes()
            report=evaluate_trace(raw.decode('utf8-sig'),original=original,candidate=candidate,save=save,
                packet=json.loads(a.packet.read_text(encoding='utf8-sig')),generated_probe=a.probe.read_bytes())
            report['source']['log_raw_sha256']=sha(raw)
    except (OSError,ValueError,TypeError,KeyError,UnicodeError) as error:
        report=dict(prepared=False,passed=False,ready_for_host_capture=False,failures=[str(error)],manual_input_proof=False,promotion_ready=False)
    print(json.dumps(report,indent=2))
    return 0 if report.get('prepared') or report.get('passed') else 2


if __name__=='__main__':raise SystemExit(main())
