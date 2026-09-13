#!/usr/bin/env python3
"""Additive, source-bound cached-primary observation and offline capture audit.

No debugger, process, COM method, game or image is started by this module.
The unchanged modal protocol proves its original native/physical canvas lane.
This additional lane observes real primary Lock calls and the attached palette.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import re
import struct

import framed_modal_canvas_trace as modal
import framed_primary_surface as primary

ROOT = Path(__file__).resolve().parents[1]
PINS = {
    'scripts/cdb/run_framed_modal_canvas_capture.ps1': '8873f885d7a5405a8a570e70e3b09e31081dcbd339b33b9e92b465274b58d9ba',
    'tools/framed_modal_canvas_probe.py': '57c183d21ec5a696e715b8b3fca39ede14e107bc75102cc9553346053da47b3d',
    'tools/framed_modal_canvas_trace.py': '2f0ef571acdbc6892c775cc97698d535b56355c8086080713d3dfec040a6d3ba',
    'tools/framed_primary_surface.py': 'd905d43e2781849ed54d862e78725af98f188b7d47ec3f5dae3796c01ee10442',
}
REVISION = 'modal_cached_primary_v1'
LOCK_START = 0x47385D
LOCK_BYTES = bytes.fromhex('8b86a4000000c746386c0000006a008b1850ff536489c33dc2017688740889d85f5e5a595bc3')
GET_PALETTE_RVA = 0x2070
GET_PALETTE_BYTES = bytes.fromhex('558bec51837d0c007507b857000780eb458b450883781c0074158b4d088b511c8b45088b481c8b12518b4204ffd0908b4d0c8b55088b421c89018b4d0883791c007409c745fc00000000eb07c745fc3c027688')
PALETTE_POINTER_OFFSET = 0x1C
H = r'[0-9a-fA-F]{1,8}'
I = r'[0-9]{1,9}'
PATTERNS = {
 'MPRI_LOCK_CALL': rf'tid=(?P<tid>{H}) esp=(?P<esp>{H}) backend=(?P<backend>{H}) surface=(?P<surface>{H}) descriptor=(?P<descriptor>{H}) rect=(?P<rect>{H}) flags=(?P<flags>{H}) event=(?P<event>{H})',
 'MPRI_LOCK_RETURN': rf'tid=(?P<tid>{H}) esp=(?P<esp>{H}) backend=(?P<backend>{H}) hr=(?P<hr>{H}) surface=(?P<surface>{H}) descriptor=(?P<descriptor>{H}) pixels=(?P<pixels>{H}) size=\((?P<width>{I}),(?P<height>{I})\) pitch=(?P<pitch>{I})',
 'MPRI_READY': rf'tid=(?P<tid>{H}) eip=(?P<eip>{H}) esp=(?P<esp>{H}) backend=(?P<backend>{H}) surface=(?P<surface>{H}) palette=(?P<palette>{H}) pixels=(?P<pixels>{H}) size=\((?P<width>{I}),(?P<height>{I})\) pitch=(?P<pitch>{I})',
 'MPRI_HOST_READY': '',
}
REGEX = {k: re.compile(k + (' '+v if v else '')) for k,v in PATTERNS.items()}
DECIMAL = {'width','height','pitch'}
LIMITS = [
 'Captured proxy-primary memory is a separate layer observation, not visible-wrapper or manual-input proof.',
 'The unchanged modal route remains a disclosed forced dispatch; this lane adds no input, render call or game-memory writes.',
 'Only the pinned proxy fixed allocation and FakeSurface/FakePalette layouts are supported.',
 'Freshness means observed successful full primary Lock after this facility entry and unchanged cached identity through the paused read.',
 'Pixel correctness, every late UI layer, interaction, modal exit/destruction and promotion remain separate claims.',
]


def sha(data): return hashlib.sha256(data).hexdigest()


def check_pins():
    for name,digest in PINS.items():
        if sha((ROOT/name).read_bytes()) != digest:
            raise ValueError('frozen primary dependency changed: '+name)


def _printf(fmt,*args):
    return modal.producer._printf(fmt,*args)


def _guard(condition,body):
    return '.if ('+condition+') { '+body+' } .else { .echo MPRI_REJECT invalid_primary; q }'


def additions():
    """All new observers are read-only: no target register/memory writes."""
    b='poi(0051d57c)'
    s=f'poi({b}+a4)'
    call=_printf('MPRI_LOCK_CALL tid=%x esp=%p backend=%p surface=%p descriptor=%p rect=%p flags=%x event=%p',
        '@$tid','@esp','@esi','poi(@esp)','poi(@esp+8)','poi(@esp+4)','poi(@esp+c)','poi(@esp+10)')
    ret=_printf('MPRI_LOCK_RETURN tid=%x esp=%p backend=%p hr=%x surface=%p descriptor=%p pixels=%p size=(%d,%d) pitch=%d',
        '@$tid','@esp','@esi','@eax','poi(@esi+a4)','@edi','poi(@esi+5c)','poi(@esi+44)','poi(@esi+40)','poi(@esi+48)')
    # CDB's explicit ID is attached to bp. "bp 110 ADDRESS" sets an
    # automatically numbered breakpoint at address0x110 instead.
    commands=(f'bp110 0047386f ".if (({b} != 0) & (@esi == {b})) {{ {call} }}; gc"\n'
              f'bp111 00473872 ".if (({b} != 0) & (@esi == {b})) {{ {ret} }}; gc"\n'
              'bd 110 111\n')
    ready=_printf('MPRI_READY tid=%x eip=%p esp=%p backend=%p surface=%p palette=%p pixels=%p size=(%d,%d) pitch=%d',
        '@$tid','@eip','@esp',b,s,f'poi({s}+1c)',f'poi({b}+5c)','wo(0051d4c0)','wo(0051d4c2)',f'poi({b}+48)')
    ready=_guard(b+' != 0',_guard(s+' != 0',_guard(f'poi({s}+1c) != 0',ready+'; .echo MPRI_HOST_READY')))
    checks=' & '.join(f'(by({LOCK_START+i:08x}) == {value:02x})' for i,value in enumerate(LOCK_BYTES))
    contract=_guard(checks,'.echo MPRI_NATIVE_CONTRACT_PASS')+'\n'
    return commands,ready,contract


def compile_probe(packet):
    base=copy.deepcopy(packet)
    contract=base.pop('primary_capture')
    path=contract.get('ready_file')
    if (not isinstance(path,str) or not re.fullmatch(r'[A-Za-z]:[\\/][\x20-\x7e]+',path)
            or re.search(r'[$";\r\n]|\.\.',path) or len(path)>512):
        raise ValueError('canonical primary command path must be bounded and delimiter-free')
    if contract != dict(revision=REVISION,dependencies=PINS,lock_start=LOCK_START,lock_bytes=LOCK_BYTES.hex(),
                        palette_pointer_offset=PALETTE_POINTER_OFFSET,proxy_sha256=primary.SUPPORTED_PROXY_SHA256,ready_file=path):
        raise ValueError('primary protocol contract differs')
    commands,ready,checks=additions()
    original=modal.compile_probe(base)
    explicit_ids={int(match[1],10) for match in re.finditer(r'(?im)^\s*bp(\d+)(?=\s)',original)}
    if explicit_ids & {110,111}:
        raise ValueError('primary breakpoint IDs collide')
    base['handoff_action']='be 110 111; '+base['handoff_action']
    base['startup_commands_before_final_g'] += commands
    base['byte_checks_before_first_breakpoint'] += checks
    generated=modal.compile_probe(base)
    token='.echo MCAP_SURFDUMP_HOST_READY'
    if generated.count(token)!=1: raise ValueError('unique modal readiness insertion missing')
    # Keep the supplied Windows path in the bound packet and host filesystem
    # reads. Only its serialization INSIDE the quoted breakpoint command uses
    # forward slashes: CDB otherwise consumes Windows backslashes as escapes.
    cdb_path=path.replace('\\','/')
    # This command is inside a BP's nested .if body. Its semicolon terminates
    # the file command before the closing brace, which is not part of a path.
    generated=generated.replace(token,token+'; $$>a<\\"'+cdb_path+'\\";')
    if any(len(line)>=4096 for line in generated.splitlines()): raise ValueError('primary command exceeds CDB line bound')
    return generated


def ready_script():
    # Commands execute as a separate quiet file, outside any BP quoted string.
    return additions()[1].replace(r'\\n',r'\n').replace(r'\"','"')+'\n'


def prepare(original,candidate,*,ready_file,**kwargs):
    check_pins()
    _,observed=modal.producer._read(original,LOCK_START,len(LOCK_BYTES))
    _,installed=modal.producer._read(candidate,LOCK_START,len(LOCK_BYTES))
    if observed!=LOCK_BYTES or installed!=LOCK_BYTES: raise ValueError('native Lock call/return bytes changed')
    _,_,_,template=modal.producer.canonical_template(original,kwargs['resolution'],minimap_viewport=kwargs['minimap_viewport'])
    packet=modal.producer.build_screen_probe(original,candidate,rendered_probe=template,**kwargs)
    packet['primary_capture']=dict(revision=REVISION,dependencies=PINS,lock_start=LOCK_START,lock_bytes=LOCK_BYTES.hex(),
        palette_pointer_offset=PALETTE_POINTER_OFFSET,proxy_sha256=primary.SUPPORTED_PROXY_SHA256,ready_file=ready_file)
    probe=compile_probe(packet)
    return dict(prepared=True,runtime_ready=False,packet=packet,probe=probe,probe_sha256=sha(probe.encode('ascii')),
                ready_script=ready_script(),ready_script_sha256=sha(ready_script().encode('ascii')))


def evaluate_primary_sequence(log,packet,modal_report):
    failures=[];rows=[];pairs=[];pending=None;ready=None;host=None
    def need(value,message):
        if not value: failures.append(message)
    w,h=map(int,packet['resolution'].split('x'))
    source_rows=(modal_report.get('modal_sequence') or {}).get('raw_records',[])
    surface=modal_report.get('surface') or {}
    entry_name='MCAP_OVERVIEW_PROLOGUE' if packet['route']['name']=='castle_overview' else 'MCAP_SCREEN_ENTRY'
    entries=[r for r in source_rows if r['marker']==entry_name]
    modal_hosts=[r['line'] for r in source_rows if r['marker']=='MCAP_SURFDUMP_HOST_READY']
    native_contract=[]
    for number,text in enumerate(log.splitlines(),1):
        if not re.search(r'\bMPRI_',text,re.I):continue
        if text=='MPRI_NATIVE_CONTRACT_PASS':native_contract.append(number);continue
        marker=text.split(' ',1)[0];match=REGEX.get(marker);match=match.fullmatch(text) if match else None
        row=dict(line=number,marker=marker,text=text,values=None);rows.append(row)
        if not match: failures.append(f'line {number}: malformed/unknown primary record');continue
        v={k:int(value,10 if k in DECIMAL else 16) for k,value in match.groupdict().items()};row['values']=v
        if ready is not None and marker!='MPRI_HOST_READY':failures.append('primary record after paused readiness')
        if marker=='MPRI_LOCK_CALL':
            need(pending is None,'overlapping primary Lock call');pending=row
            need((v['rect'],v['flags'],v['event'])==(0,1,0),'primary Lock is not full NULL-rect/flags1/event0')
            need(v['descriptor']==v['backend']+0x38 and v['surface']>0,'primary Lock descriptor/object differs')
        elif marker=='MPRI_LOCK_RETURN':
            need(pending is not None,'primary Lock return has no call')
            if pending:
                a=pending['values'];need(all(v[k]==a[k] for k in ('tid','backend','surface','descriptor')) and v['esp']==a['esp']+20,'primary Lock stdcall pairing differs')
                need(v['hr']==0 and (v['width'],v['height'],v['pitch'])==(w,h,w) and 0<v['pixels']<=2**32-w*h,'primary Lock failed or descriptor unsupported')
                pairs.append(dict(call=pending,returned=row));pending=None
        elif marker=='MPRI_READY':
            need(ready is None and pending is None,'duplicate readiness or unfinished Lock');ready=row
            need((v['width'],v['height'],v['pitch'])==(w,h,w) and all(v[k]>0 for k in ('backend','surface','palette','pixels')),'paused primary descriptor invalid')
            need(all(v[k]==surface.get(k) for k in ('tid','eip','esp')),'primary/native capture boundary differs')
        elif marker=='MPRI_HOST_READY':
            need(host is None and ready is not None and number==ready['line']+1,'primary host marker must immediately follow READY');host=number
    need(len(native_contract)==1,'one native primary byte contract required')
    need(ready is not None and host is not None and pending is None and len(pairs)>0,'incomplete primary observation')
    need(len(entries)==1 and len(modal_hosts)==1,'one modal entry and paused host marker required')
    if ready and pairs and len(entries)==len(modal_hosts)==1:
        last=pairs[-1];a=last['returned']['values'];v=ready['values']
        need(native_contract and native_contract[0]<pairs[0]['call']['line'],'native byte contract must precede observations')
        need(entries[0]['line']<last['call']['line']<last['returned']['line']<modal_hosts[0]<ready['line'],'last successful primary Lock is stale or outside route boundary')
        need(all(v[k]==a[k] for k in ('tid','backend','surface','pixels','width','height','pitch')),'current primary differs from last Lock')
    return dict(passed=not failures,failures=failures,raw_records=rows,lock_pairs=pairs,ready=ready,
                last_lock=pairs[-1] if pairs else None,host_ready_line=host,limits=LIMITS)


def evaluate_trace(log,*,original,candidate,packet,generated_probe,ready_script_bytes):
    check_pins()
    rebuilt=prepare(original,candidate,candidate_sha256=packet['candidate_sha256'],stage=packet['stage'],
        resolution=packet['resolution'],route=packet['route']['name'],availability=packet['availability'],
        castle_index=packet['castle_index'],minimap_viewport=packet['minimap_viewport'],ready_file=packet['primary_capture']['ready_file'])
    if (rebuilt['packet']!=packet or generated_probe.decode('ascii').replace('\r\n','\n')!=rebuilt['probe']
            or ready_script_bytes!=rebuilt['ready_script'].encode('ascii')):
        raise ValueError('whole primary packet/probe differs from source reconstruction')
    base=copy.deepcopy(packet);base.pop('primary_capture')
    result=modal.evaluate_trace(log,original=original,candidate=candidate,packet=base,
                               generated_probe=modal.compile_probe(base).encode('ascii'))
    result['base_modal_source']=copy.deepcopy(result['source'])
    sequence=evaluate_primary_sequence(log,packet,result)
    result['primary_sequence']=sequence
    result['failures'] += sequence['failures']
    result['passed']=result['ready_for_host_capture']=not result['failures']
    result['source'].update(generated_probe_sha256=sha(generated_probe),validator_sha256=sha(Path(__file__).read_bytes()),
        generated_probe_canonical_lf_sha256=sha(rebuilt['probe'].encode('ascii')),primary_ready_script_sha256=sha(ready_script_bytes),primary_dependencies=PINS)
    result['primary_protocol_revision']=REVISION;result['limits']=result['limits']+LIMITS
    return result


def _artifact(record):
    data=Path(record['path']).read_bytes()
    if len(data)!=record['bytes'] or sha(data)!=record['sha256']:raise ValueError('captured artifact count/hash differs')
    return data


def audit_snapshot(manifest,*,proxy_image,trace):
    """Validate producer-written host reads against an already revalidated trace.

    The CLI below revalidates full source/candidate/probe/log independently.
    No caller-authored passed flag substitutes for that reconstruction.
    """
    if not trace.get('passed') or not trace.get('primary_sequence',{}).get('passed'):raise ValueError('complete primary trace required')
    before={};after={}
    for dest,phase in ((before,'before'),(after,'after')):
        for name,record in manifest['reads'][phase].items():dest[name]=primary.Read(record['address'],_artifact(record))
    if before!=after:raise ValueError('captured primary identities changed')
    for name in ('surface_full','proxy_header','proxy_getpalette'):
        if name not in before:raise ValueError('missing current attached palette/module read')
    v=trace['primary_sequence']['ready']['values'];owner=manifest['game_identity']
    if before['surface_full'].address!=v['surface'] or len(before['surface_full'].data)!=32 or primary._u32(before['surface_full'].data,28)!=v['palette']:
        raise ValueError('live attached palette pointer differs')
    if before['surface_full'].data[:4]!=before['surface'].data:raise ValueError('repeated COM vtable reads differ')
    if before['proxy_header'].data!=proxy_image[:512] or before['proxy_getpalette'].data!=GET_PALETTE_BYTES:
        raise ValueError('loaded proxy header/GetPalette implementation differs')
    base=manifest['proxy_module']['base']
    if before['proxy_header'].address!=base or before['proxy_getpalette'].address!=base+GET_PALETTE_RVA:raise ValueError('proxy read addresses differ')
    if manifest['proxy_module']['sha256']!=primary.SUPPORTED_PROXY_SHA256:raise ValueError('unsupported live proxy identity')
    if owner['candidate_sha256']!=trace['candidate_sha256'] or manifest['trace_sha256']!=trace['source']['log_raw_sha256']:
        raise ValueError('host/trace/candidate binding differs')
    row=trace['primary_sequence']['last_lock'];a=row['call'];r=row['returned'];ready=trace['primary_sequence']['ready']
    identity=dict(run_id=manifest['run_id'],process_id=owner['process_id'],process_start=owner['creation_utc'],
        candidate_sha256=trace['candidate_sha256'],proxy_sha256=primary.SUPPORTED_PROXY_SHA256,thread_id=v['tid'],
        trace_sha256=manifest['trace_sha256'],capture_boundary='MPRI_HOST_READY',ready_line=ready['line'],
        last_primary_lock_line=r['line'],current_palette_line=ready['line'])
    fields={k:identity[k] for k in ('run_id','process_id','process_start','candidate_sha256','proxy_sha256','thread_id','trace_sha256','capture_boundary')}
    lock=dict(fields,schema='clash95_full_primary_lock_v1',line=r['line'],call_line=a['line'],call_eip=primary.LOCK_CALL,
        return_eip=primary.LOCK_RETURN,call_esp=a['values']['esp'],return_esp=r['values']['esp'],hresult=r['values']['hr'],
        rect_is_null=a['values']['rect']==0,flags=a['values']['flags'],event_handle=a['values']['event'],
        **{k:r['values'][k] for k in ('backend','surface','descriptor','pixels','width','height','pitch')},
        descriptor_sha256=sha(before['backend'].data[0x38:0xA4]))
    pal=dict(fields,schema='clash95_current_primary_palette_v1',line=ready['line'],surface=v['surface'],palette=v['palette'],
        entries_address=v['palette']+12,entries_sha256=sha(before['palette'].data[12:]),entry_count=256)
    pixels=manifest['pixels'];raw=_artifact(pixels)
    regions=[primary.Region(**r) for r in manifest['regions']]
    for name in ('surface_full','proxy_header','proxy_getpalette'):
        read=before[name];primary._read(read,read.address,len(read.data),name,regions)
    snapshots=[primary.Snapshot(**{k:x[k] for k in primary.Snapshot.__dataclass_fields__}) for x in (before,after)]
    result=primary.validate_snapshot(*snapshots,primary.Read(pixels['address'],raw),width=v['width'],height=v['height'],
        proxy_image=proxy_image,expected_proxy_sha256=primary.SUPPORTED_PROXY_SHA256,proxy_base=base,
        regions=regions,identity=identity,lock_observation=lock,palette_observation=pal)
    if _artifact(manifest['palette_entries'])!=before['palette'].data[12:]:raise ValueError('PNG palette does not match current attached entries')
    result.update(source_authenticated=True,host_receipt_consistent=True,read_plan=primary.primary_read_plan(v['width'],v['height']))
    return result


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--prepare',action='store_true')
    for name in ('original','candidate','log','packet','probe','snapshot-manifest','proxy'):
        ap.add_argument('--'+name,type=Path,required=name in ('original','candidate'))
    for name in ('candidate-sha256','stage','resolution','route','availability','ready-file'):ap.add_argument('--'+name)
    ap.add_argument('--castle-index',type=int);ap.add_argument('--minimap-viewport',action='store_true');args=ap.parse_args()
    try:
        original,candidate=args.original.read_bytes(),args.candidate.read_bytes()
        if args.prepare:
            report=prepare(original,candidate,candidate_sha256=args.candidate_sha256,stage=args.stage,resolution=args.resolution,
                route=args.route,availability=args.availability,castle_index=args.castle_index,minimap_viewport=args.minimap_viewport,ready_file=args.ready_file)
        else:
            raw=args.log.read_bytes();packet=json.loads(args.packet.read_text(encoding='utf-8-sig'))
            if Path(packet['primary_capture']['ready_file']).read_bytes()!=ready_script().encode('ascii'):
                raise ValueError('whole primary readiness script differs')
            report=evaluate_trace(raw.decode('utf-8-sig'),original=original,candidate=candidate,packet=packet,generated_probe=args.probe.read_bytes(),
                ready_script_bytes=Path(packet['primary_capture']['ready_file']).read_bytes())
            report['source']['log_raw_sha256']=sha(raw)
            if args.snapshot_manifest:
                report['primary_snapshot']=audit_snapshot(json.loads(args.snapshot_manifest.read_text(encoding='utf-8-sig')),
                    proxy_image=args.proxy.read_bytes(),trace=report)
        code=0 if report.get('prepared') or report.get('passed') else 2
    except (ValueError,KeyError,TypeError,OSError,AttributeError) as error:
        report=dict(passed=False,prepared=False,ready_for_host_capture=False,failures=[str(error)],manual_input_proof=False,promotion_ready=False);code=2
    print(json.dumps(report,indent=2));return code


if __name__=='__main__':raise SystemExit(main())
