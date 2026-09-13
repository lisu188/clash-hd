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

import modal_slots_barracks_trace as modal
import modal_slots_primary_surface as primary

ROOT = Path(__file__).resolve().parents[1]
PINS = {
    'tools/modal_slots_primary_surface.py': 'd905d43e2781849ed54d862e78725af98f188b7d47ec3f5dae3796c01ee10442',
}
PRIMARY_SOURCES = ('tools/modal_slots_primary_capture.py','tools/modal_slots_primary_surface.py',
                   'scripts/cdb/run_modal_slots_primary_capture.ps1')
REVISION = 'slots_cached_primary_v1'
SNAPSHOT_ORIGIN = {'source':'tools/framed_primary_surface.py',
                  'sha256':PINS['tools/modal_slots_primary_surface.py']}
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


def proxy_context(manifest_path):
    """Require the actual historical pinned binary and genuine source manifest."""
    path=Path(manifest_path).resolve();data=path.read_bytes();manifest=json.loads(data)
    image_path=Path(manifest['output']).resolve();source_path=Path(manifest['source']).resolve()
    image=image_path.read_bytes()
    source_hash=sha(source_path.read_bytes())
    if (manifest.get('generated_by')!='clash-hd-surface-dump-proxy' or image_path.name.lower()!='ddraw.dll'
            or sha(image)!=primary.SUPPORTED_PROXY_SHA256
            or manifest.get('output_sha256','').lower()!=primary.SUPPORTED_PROXY_SHA256
            or source_hash!=primary.SUPPORTED_PROXY_SOURCE_SHA256
            or manifest.get('source_sha256','').lower()!=source_hash
            or sha((ROOT/'src/ddraw_surfdump_proxy/ddraw_surfdump_proxy.cpp').read_bytes())!=source_hash):
        raise ValueError('primary capture requires the exact pinned proxy binary and matching recorded/current source')
    proxy=primary._Proxy(image,primary.SUPPORTED_PROXY_SHA256,0x10000000)
    if proxy.raw(GET_PALETTE_RVA,len(GET_PALETTE_BYTES))!=GET_PALETTE_BYTES:
        raise ValueError('pinned GetPalette implementation differs')
    if path.read_bytes()!=data:raise ValueError('proxy manifest changed during verification')
    return dict(path=str(path),sha256=sha(data),output=str(image_path),source=str(source_path),
                proxy_sha256=sha(image),source_sha256=source_hash)


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
                        source_hashes={name:sha((ROOT/name).read_bytes()) for name in PRIMARY_SOURCES},snapshot_origin=SNAPSHOT_ORIGIN,
                        proxy_manifest=proxy_context(contract['proxy_manifest']['path']),
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


def prepare(original,candidate,*,ready_file,proxy_manifest,**kwargs):
    check_pins()
    _,observed=modal.producer._read(original,LOCK_START,len(LOCK_BYTES))
    _,installed=modal.producer._read(candidate,LOCK_START,len(LOCK_BYTES))
    if observed!=LOCK_BYTES or installed!=LOCK_BYTES: raise ValueError('native Lock call/return bytes changed')
    packet=modal.producer.build_screen_probe(original,candidate,**kwargs)
    packet['primary_capture']=dict(revision=REVISION,dependencies=PINS,lock_start=LOCK_START,lock_bytes=LOCK_BYTES.hex(),
        source_hashes={name:sha((ROOT/name).read_bytes()) for name in PRIMARY_SOURCES},snapshot_origin=SNAPSHOT_ORIGIN,
        proxy_manifest=proxy_context(proxy_manifest),palette_pointer_offset=PALETTE_POINTER_OFFSET,
        proxy_sha256=primary.SUPPORTED_PROXY_SHA256,ready_file=ready_file)
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
        castle_index=packet['castle_index'],minimap_viewport=packet['minimap_viewport'],ready_file=packet['primary_capture']['ready_file'],
        candidate_manifest=Path(packet['candidate_manifest']['path']),proxy_manifest=packet['primary_capture']['proxy_manifest']['path'])
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


def audit_final_log(receipt,*,packet,probe,ready_bytes):
    """Recheck the final debugger tail; a valid paused prefix cannot hide it."""
    if receipt.get('failures') != []:
        raise ValueError('host failures must remain failed before primary acceptance')
    plan=receipt['plan'];root=Path(plan['out_dir']).resolve()
    final=receipt['final_log'];prefix=receipt['capture_prefix']
    if (Path(final['path']).resolve()!=root/'cdb.log'
            or Path(prefix['path']).resolve()!=root/'capture-prefix.log'
            or final.get('capture_prefix_preserved') is not True):
        raise ValueError('final log/prefix path or preservation receipt differs')
    raw=_artifact(final);paused=_artifact(prefix)
    if not raw.startswith(paused):raise ValueError('final log does not preserve the actual paused prefix')
    result=evaluate_trace(raw.decode('utf-8-sig'),original=Path(plan['original']).read_bytes(),
        candidate=Path(plan['candidate_path']).read_bytes(),packet=packet,generated_probe=probe,
        ready_script_bytes=ready_bytes)
    if result.get('passed') is not True or result.get('failures') != []:
        raise ValueError('complete final initial/modal/slots/primary trace failed: '+str(result.get('failures')))
    return dict(complete_final_trace_passed=True,final_log_sha256=sha(raw),paused_prefix_sha256=sha(paused))


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
    if manifest['proxy_module']['size']!=primary._Proxy(proxy_image,primary.SUPPORTED_PROXY_SHA256,base).size:
        raise ValueError('loaded proxy module extent differs from pinned image')
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


def audit_triplet(receipt,*,proxy_image,trace,packet):
    """Bind all three native/physical/primary samples and exact owned cleanup."""
    from modal_slots_surface_audit import mirror_pixels
    def need(value,message):
        if not value:raise ValueError(message)
    need(receipt.get('schema')=='clash95_slots_primary_triplet_v1','wrong primary triplet receipt')
    need(trace.get('passed') is True and trace.get('primary_sequence',{}).get('passed') is True,
         'whole initial/modal/slots/primary trace required before snapshot acceptance')
    plan=receipt['plan'];root=Path(plan['out_dir']).resolve()
    need(plan['schema']=='clash95_modal_slots_primary_capture_plan_v1','wrong primary plan')
    for key in ('stage','resolution','castle_index','availability','minimap_viewport','candidate_sha256',
                'original_sha256','canvas_state_va','canvas_state_offsets','stop_va'):
        need(plan[key]==packet[key],'plan/packet '+key+' differs')
    width,height=map(int,packet['resolution'].split('x'))
    need(plan['route']==packet['route']['name']=='barracks' and
         type(plan['width']) is int and type(plan['height']) is int and
         (plan['width'],plan['height'])==(width,height),'primary plan route/geometry differs')
    sources={'host_path':'scripts/cdb/run_modal_slots_primary_capture.ps1',
             'producer':'tools/modal_slots_primary_capture.py','trace':'tools/modal_slots_primary_capture.py',
             'primary_source':'tools/modal_slots_primary_surface.py','converter':'tools/cdb_surface_dump_to_png.py',
             'proxy_source':'src/ddraw_surfdump_proxy/ddraw_surfdump_proxy.cpp'}
    for name,relative in sources.items():
        path=Path(plan[name]).resolve();key='host_sha256' if name=='host_path' else name+'_sha256'
        digest=sha(path.read_bytes())
        need(path==(ROOT/relative).resolve() and digest==plan[key],name+' canonical source changed')
        if relative in packet['primary_capture']['source_hashes']:
            need(digest==packet['primary_capture']['source_hashes'][relative],name+' differs from rebuilt primary packet')
    for name,key in (('original','original_sha256'),('input_candidate','candidate_sha256'),('candidate_path','candidate_sha256'),
                     ('candidate_manifest','candidate_manifest_sha256'),('proxy_input','proxy_sha256'),('proxy_path','proxy_sha256'),
                     ('proxy_manifest','proxy_manifest_sha256'),('python','python_sha256'),('cdb','cdb_sha256')):
        need(sha(Path(plan[name]).read_bytes())==plan[key],name+' planned file changed')
    bound_proxy=packet['primary_capture']['proxy_manifest']
    need(str(Path(plan['proxy_manifest']).resolve())==bound_proxy['path'] and
         plan['proxy_manifest_sha256']==bound_proxy['sha256'] and
         plan['proxy_sha256']==sha(proxy_image)==primary.SUPPORTED_PROXY_SHA256,'proxy manifest/actual image differs')
    need(str(Path(plan['candidate_manifest']).resolve())==packet['candidate_manifest']['path'] and
         plan['candidate_manifest_sha256']==packet['candidate_manifest']['sha256'],'candidate sidecar plan differs')
    for name,filename in (('packet','packet.json'),('probe','modal-slots-barracks.cdb'),('capture_prefix','capture-prefix.log')):
        need(Path(receipt[name]['path']).resolve()==root/filename,'triplet '+name+' path differs')
        data=Path(receipt[name]['path']).read_bytes()
        need(sha(data)==receipt[name]['sha256'],'triplet '+name+' hash differs')
        if name=='packet':need(json.loads(data)==packet,'triplet packet differs')
        if name=='probe':need(sha(data)==plan['probe_sha256']==trace['source']['generated_probe_sha256'],'triplet probe differs')
        if name=='capture_prefix':need(sha(data)==trace['source']['log_raw_sha256'],'triplet trace prefix differs')
    ready_path=Path(plan['primary_ready_path']).resolve()
    need(ready_path==root/'primary-ready.cdb' and str(ready_path)==str(Path(packet['primary_capture']['ready_file']).resolve())
         and sha(ready_path.read_bytes())==plan['primary_ready_sha256']==trace['source']['primary_ready_script_sha256'],
         'primary ready-file binding differs')
    final=audit_final_log(receipt,packet=packet,probe=Path(receipt['probe']['path']).read_bytes(),
                          ready_bytes=ready_path.read_bytes())
    identities=[receipt['cdb'],*receipt['candidates']]
    need(len(identities)==2 and all(type(i.get('process_id')) is int and i['process_id']>0 and
         type(i.get('creation_filetime')) is int and i['creation_filetime']>0 and i.get('handle_retained') is True for i in identities),
         'exact retained process identities required')
    debugger,owner=identities
    need(debugger['process_id']!=owner['process_id'] and owner['parent_process_id']==debugger['process_id'] and
         owner['creation_filetime']>=debugger['creation_filetime'] and owner['candidate_sha256']==plan['candidate_sha256'] and
         Path(debugger['path']).resolve()==Path(plan['cdb']).resolve() and
         Path(owner['path']).resolve()==Path(plan['candidate_path']).resolve(),'candidate parent/time/path identity differs')
    cleanup=receipt['cleanup']
    need(cleanup.get('desktop_closed') is True and len(cleanup['candidates'])==1,'owned cleanup incomplete')
    for result,identity in zip((cleanup['cdb'],cleanup['candidates'][0]),identities):
        need(result.get('absent') is True and result.get('handle_closed') is True and result['identity']==identity,
             'retained-handle absence/cleanup identity differs')
    need(receipt.get('clean_stable_pair') is True and len(receipt['snapshots'])==3,'three stable matched captures required')
    ready=[r['values'] for r in trace['modal_sequence']['raw_records'] if r['marker']=='MCAP_CANVAS' and r['values']['event']=='READY']
    need(len(ready)==1,'one owned-canvas readiness required');ready=ready[0]
    comparisons=[];results=[]
    for index,row in enumerate(receipt['snapshots'],1):
        folder=root/f'capture-{index}';sample=row['primary']
        need(row['game_identity']==sample['game_identity']==owner and sample['run_id']==root.name,
             'matched sample belongs to another process/run')
        need(row.get('paused') is True and sample.get('paused') is True and row.get('capture')=='owned_physical_mirror',
             'matched capture is not a paused owned canvas')
        need(Path(row['path']).resolve()==folder/'surface.raw' and
             Path(row['native']['path']).resolve()==folder/'native-surface.raw','native/physical sample path differs')
        physical=_artifact(row);native=_artifact(row['native'])
        need((row['width'],row['height'],row['pitch'])==(width,height,width) and
             (row['native']['width'],row['native']['height'],row['native']['pitch'])==(640,480,640),'sample strides differ')
        need((row['physical'],row['physical_pixels'],row['native']['surface'],row['native']['base'])==
             tuple(ready[k] for k in ('physical','physical_pixels','native','native_pixels')),'sample native/physical pointers differ')
        headers=[]
        for name in ('state','e0','physical_header','native_header'):
            records=[row['reads'][phase][name] for phase in ('before','after')]
            for phase,record in zip(('before','after'),records):
                need(Path(record['path']).resolve()==folder/f'surface-{phase}-{name}.raw','native state/header sample path differs')
            data=_artifact(records[0]);need(data==_artifact(records[1]),'native ownership/header changed across sample')
            address={'state':packet['canvas_state_va'],'e0':0x5202E0,'physical_header':ready['physical'],'native_header':ready['native']}[name]
            need(all(r['address']==address for r in records),'native state/header address differs')
            def word(offset,size=4):return int.from_bytes(data[offset:offset+size],'little')
            if name=='state':
                expected=dict(phase=1,physical=ready['physical'],native=ready['native'],root_esp=ready['root_esp'],owner_tid=ready['tid'],
                    enter_status=1,mirror_status=1,leave_status=0,fault=0,allocations=1,frees=0,mirrors=3,
                    pending_header=0,pending_pixels=0,native_pixels=ready['native_pixels'],physical_pixels=ready['physical_pixels'])
                need(len(data)==128 and all(word(modal.producer.canvas.STATE[k])==v for k,v in expected.items()),'native ownership differs from trace')
            elif name=='e0':need(len(data)==4 and word(0)==ready['native'],'E0 does not own native canvas')
            else:
                expected=(640,480,ready['native_pixels']) if name=='native_header' else (width,height,ready['physical_pixels'])
                need(len(data)==188 and (word(0,2),word(2,2),word(4))==expected and word(184)==0x50EE24,'native/physical header differs')
                if name=='native_header':need(word(172)==0,'native canvas owns COM interface')
            headers.append(sha(data))
        need(Path(sample['pixels']['path']).resolve()==folder/'primary.raw' and
             Path(sample['palette_entries']['path']).resolve()==folder/'primary-palette.bin','primary pixels/palette sample path differs')
        for phase in ('before','after'):
            for name,record in sample['reads'][phase].items():
                need(Path(record['path']).resolve()==folder/f'primary-{phase}-{name}.raw','primary header sample path differs')
        need(Path(sample['proxy_module']['path']).resolve()==Path(plan['proxy_path']).resolve(),'sample loaded proxy path differs')
        primary_result=audit_snapshot(sample,proxy_image=proxy_image,trace=trace)
        mirror=mirror_pixels(native,physical,width,height)
        need(mirror['passed'],'sample native/physical mirror or twelve slots differ')
        comparisons.append((sha(physical),sha(native),sha(_artifact(sample['pixels'])),sha(_artifact(sample['palette_entries'])),
                            *headers,*[sample['reads']['before'][k]['sha256'] for k in sorted(sample['reads']['before'])]))
        results.append(dict(index=index,primary=primary_result,mirror=mirror))
    need(all(value==comparisons[0] for value in comparisons),'three matched sample bytes differ')
    return dict(cached_primary_snapshot_valid=True,three_matched_captures=True,samples=results,final_trace=final,
                candidate_sha256=packet['candidate_sha256'],stage=packet['stage'],resolution=packet['resolution'],
                proof_class='hidden_forced_barracks_native_physical_cached_primary',
                primary_composition_proven=False,visible_composition_proof=False,manual_input_proof=False,
                native_modal_exit_proven=False,promotion_ready=False)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--prepare',action='store_true')
    for name in ('original','candidate','log','packet','probe','snapshot-manifest','proxy','candidate-manifest','proxy-manifest'):
        ap.add_argument('--'+name,type=Path,required=name in ('original','candidate'))
    for name in ('candidate-sha256','stage','resolution','route','availability','ready-file'):ap.add_argument('--'+name)
    ap.add_argument('--castle-index',type=int);ap.add_argument('--minimap-viewport',action='store_true');args=ap.parse_args()
    try:
        original,candidate=args.original.read_bytes(),args.candidate.read_bytes()
        if args.prepare:
            report=prepare(original,candidate,candidate_sha256=args.candidate_sha256,stage=args.stage,resolution=args.resolution,
                route=args.route,availability=args.availability,castle_index=args.castle_index,minimap_viewport=True,ready_file=args.ready_file,
                candidate_manifest=args.candidate_manifest,proxy_manifest=args.proxy_manifest)
        else:
            raw=args.log.read_bytes();packet=json.loads(args.packet.read_text(encoding='utf-8-sig'))
            if Path(packet['primary_capture']['ready_file']).read_bytes()!=ready_script().encode('ascii'):
                raise ValueError('whole primary readiness script differs')
            report=evaluate_trace(raw.decode('utf-8-sig'),original=original,candidate=candidate,packet=packet,generated_probe=args.probe.read_bytes(),
                ready_script_bytes=Path(packet['primary_capture']['ready_file']).read_bytes())
            report['source']['log_raw_sha256']=sha(raw)
            if args.snapshot_manifest:
                try:
                    report['primary_snapshot']=audit_triplet(json.loads(args.snapshot_manifest.read_text(encoding='utf-8-sig')),
                        proxy_image=args.proxy.read_bytes(),trace=report,packet=packet)
                except (ValueError,KeyError,TypeError,OSError,AttributeError) as error:
                    report['failures'].append('primary triplet: '+str(error))
                    report['passed']=report['ready_for_host_capture']=False
        code=0 if report.get('prepared') or report.get('passed') else 2
    except (ValueError,KeyError,TypeError,OSError,AttributeError) as error:
        report=dict(passed=False,prepared=False,ready_for_host_capture=False,failures=[str(error)],manual_input_proof=False,promotion_ready=False);code=2
    print(json.dumps(report,indent=2));return code


if __name__=='__main__':raise SystemExit(main())
