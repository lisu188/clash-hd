#!/usr/bin/env python3
"""Bind the new modal-primary route to actual paused cached-primary reads.

Preparation and evaluation are offline. This module never starts a debugger,
calls COM, sends input, or substitutes an old-stage packet or runtime receipt.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import struct

import modal_primary_barracks_trace as route
import modal_slots_primary_surface as reader

ROOT = Path(__file__).resolve().parents[1]
CHECKPOINTS = ('full-published', 'placeholder-before', 'placeholder-after', 'final-ready')
REVISION = 'owned_modal_primary_capture_v1'
READER_SHA256 = 'd905d43e2781849ed54d862e78725af98f188b7d47ec3f5dae3796c01ee10442'
SOURCES = ('tools/modal_primary_capture.py', 'tools/modal_primary_surface_audit.py',
           'tools/modal_slots_primary_surface.py', 'tools/hd_layout_asset_composition.py',
           'scripts/cdb/run_modal_primary_capture.ps1')
LOCK_START = 0x47385D
LOCK_BYTES = bytes.fromhex('8b86a4000000c746386c0000006a008b1850ff536489c33dc2017688740889d85f5e5a595bc3')
GET_PALETTE_RVA = 0x2070
GET_PALETTE_BYTES = bytes.fromhex('558bec51837d0c007507b857000780eb458b450883781c0074158b4d088b511c8b45088b481c8b12518b4204ffd0908b4d0c8b55088b421c89018b4d0883791c007409c745fc00000000eb07c745fc3c027688')
H, I = r'[0-9a-fA-F]{1,8}', r'[0-9]{1,9}'
PATTERNS = {
    'MPRI_LOCK_CALL': rf'tid=(?P<tid>{H}) esp=(?P<esp>{H}) backend=(?P<backend>{H}) surface=(?P<surface>{H}) descriptor=(?P<descriptor>{H}) rect=(?P<rect>{H}) flags=(?P<flags>{H}) event=(?P<event>{H})',
    'MPRI_LOCK_RETURN': rf'tid=(?P<tid>{H}) esp=(?P<esp>{H}) backend=(?P<backend>{H}) hr=(?P<hr>{H}) surface=(?P<surface>{H}) descriptor=(?P<descriptor>{H}) pixels=(?P<pixels>{H}) size=\((?P<width>{I}),(?P<height>{I})\) pitch=(?P<pitch>{I})',
    'MPRI_CHECKPOINT': rf'name=(?P<name>[a-z-]+) tid=(?P<tid>{H}) eip=(?P<eip>{H}) esp=(?P<esp>{H}) backend=(?P<backend>{H}) surface=(?P<surface>{H}) palette=(?P<palette>{H}) pixels=(?P<pixels>{H}) size=\((?P<width>{I}),(?P<height>{I})\) pitch=(?P<pitch>{I})',
}
REGEX = {name: re.compile(name+' '+pattern) for name,pattern in PATTERNS.items()}
LIMITS = [
    'A passed named prefix authorizes only its paused host read; later checkpoints remain unproved.',
    'This is a controlled native barracks placeholder route, not ordinary input or selected-panel branch coverage.',
    'The pinned proxy allocation and current attached palette are required; visible-wrapper composition is separate.',
    'Recorded owned cleanup, pixel correctness, native exit, other facilities, and promotion require separate checks.',
]


def sha(data): return hashlib.sha256(data).hexdigest()
def need(value, message):
    if not value: raise ValueError(message)
def canonical(value): return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True)
def integer(value, label, low=0, high=0xffffffff):
    need(type(value) is int and low<=value<=high,label+' is not an exact bounded integer')
    return value


def path_value(value):
    need(isinstance(value,(str,Path)) and str(value), 'nonempty artifact path required')
    path=Path(value).absolute()
    for item in (path,*path.parents):
        if item.exists():
            st=item.lstat()
            need(not item.is_symlink() and not getattr(item,'is_junction',lambda:False)()
                 and not getattr(st,'st_file_attributes',0)&0x400, 'reparse artifact or ancestor: '+str(item))
    return path.resolve()


class Artifacts:
    """Retain immutable bytes, reject aliases/reparse paths and recheck drift."""
    def __init__(self): self.files={}
    def read(self,path,*,expected=None,size=None):
        p=path_value(path)
        data=p.read_bytes()
        if p in self.files: need(data==self.files[p], 'artifact changed while auditing: '+str(p))
        else:self.files[p]=data
        if expected is not None:need(type(expected) is str and re.fullmatch('[0-9a-f]{64}',expected) and sha(data)==expected,'artifact hash differs: '+str(p))
        if size is not None:need(type(size) is int and len(data)==size,'artifact byte count differs: '+str(p))
        return data
    def artifact(self,record,*,path=None,size=None,address=None):
        need(type(record) is dict,'artifact receipt required')
        if path is not None:need(path_value(record['path'])==path_value(path),'artifact path differs')
        if address is not None:need(integer(record.get('address'),'read address',1)==address,'read address differs')
        count=integer(record['bytes'],'read bytes',1) if 'bytes' in record else None
        if size is not None:need(count is not None,'exact byte-count receipt required')
        if size is not None:need(count==size,'read extent differs')
        return self.read(record['path'],expected=record['sha256'],size=count)
    def json(self,path):return route.strict_json_object(self.read(path))
    def unchanged(self):
        for path,data in self.files.items():need(path_value(path).read_bytes()==data,'bound artifact drift: '+str(path))
    def receipts(self):return [dict(path=str(p),bytes=len(b),sha256=sha(b)) for p,b in self.files.items()]


def check_reader():
    need(sha((ROOT/'tools/modal_slots_primary_surface.py').read_bytes())==READER_SHA256,'frozen pure primary reader changed')


def proxy_context(manifest_path):
    path=path_value(manifest_path);raw=path.read_bytes();manifest=route.strict_json_object(raw)
    output=path_value(manifest['output']);source=path_value(manifest['source'])
    image=output.read_bytes();source_data=source.read_bytes()
    need(manifest.get('generated_by')=='clash-hd-surface-dump-proxy' and output.name.lower()=='ddraw.dll', 'unsupported proxy manifest')
    need(sha(image)==reader.SUPPORTED_PROXY_SHA256==manifest.get('output_sha256','').lower(), 'exact pinned proxy image required')
    need(sha(source_data)==reader.SUPPORTED_PROXY_SOURCE_SHA256==manifest.get('source_sha256','').lower(), 'exact pinned proxy source required')
    need((ROOT/'src/ddraw_surfdump_proxy/ddraw_surfdump_proxy.cpp').read_bytes()==source_data,'current proxy source differs')
    proxy=reader._Proxy(image,reader.SUPPORTED_PROXY_SHA256,0x10000000)
    need(proxy.raw(GET_PALETTE_RVA,len(GET_PALETTE_BYTES))==GET_PALETTE_BYTES,'pinned GetPalette bytes differ')
    need(path.read_bytes()==raw and output.read_bytes()==image and source.read_bytes()==source_data,'proxy inputs changed during preparation')
    return dict(path=str(path),sha256=sha(raw),output=str(output),source=str(source),
                proxy_sha256=sha(image),source_sha256=sha(source_data))


def _guard(condition,body):return '.if ('+condition+') { '+body+' } .else { .echo MPRI_REJECT invalid_primary; q }'
def _printf(fmt,*args):return route.producer._printf(fmt,*args)


def ready_script(name, packet):
    need(name in CHECKPOINTS,'unsupported checkpoint')
    backend='poi(0051d57c)';surface=f'poi({backend}+a4)'
    record=_printf('MPRI_CHECKPOINT name='+name+' tid=%x eip=%p esp=%p backend=%p surface=%p palette=%p pixels=%p size=(%d,%d) pitch=%d',
        '@$tid','@eip','@esp',backend,surface,f'poi({surface}+1c)',f'poi({backend}+5c)',
        'wo(0051d4c0)','wo(0051d4c2)',f'poi({backend}+48)')
    native=route.producer.checkpoint_script(packet,name)
    primary=(_guard(backend+' != 0',_guard(surface+' != 0',_guard(f'poi({surface}+1c) != 0',record)))
             .replace(r'\\n',r'\n').replace(r'\"','"')+'\n')
    return native.rstrip()+'\n'+primary


def additions():
    b='poi(0051d57c)'
    call=_printf('MPRI_LOCK_CALL tid=%x esp=%p backend=%p surface=%p descriptor=%p rect=%p flags=%x event=%p',
        '@$tid','@esp','@esi','poi(@esp)','poi(@esp+8)','poi(@esp+4)','poi(@esp+c)','poi(@esp+10)')
    ret=_printf('MPRI_LOCK_RETURN tid=%x esp=%p backend=%p hr=%x surface=%p descriptor=%p pixels=%p size=(%d,%d) pitch=%d',
        '@$tid','@esp','@esi','@eax','poi(@esi+a4)','@edi','poi(@esi+5c)','poi(@esi+44)','poi(@esi+40)','poi(@esi+48)')
    commands=(f'bp110 0047386f ".if (({b} != 0) & (@esi == {b})) {{ {call} }}; gc"\n'
              f'bp111 00473872 ".if (({b} != 0) & (@esi == {b})) {{ {ret} }}; gc"\nbd 110 111\n')
    checks=' & '.join(f'(by({LOCK_START+i:08x}) == {v:02x})' for i,v in enumerate(LOCK_BYTES))
    return commands,_guard(checks,'.echo MPRI_NATIVE_CONTRACT_PASS')+'\n'


def contract(proxy_manifest,ready_files):
    check_reader()
    need(type(ready_files) is dict and set(ready_files)==set(CHECKPOINTS),'four exact ready files required')
    paths={}
    for name,value in ready_files.items():
        value=str(value)
        need(re.fullmatch(r'[A-Za-z]:[\\/][\x20-\x7e]+',value) and not re.search(r'[$";\r\n]|\.\.',value) and len(value)<512,'unsafe checkpoint command path')
        paths[name]=str(path_value(value))
    need(len(set(paths.values()))==4,'checkpoint command paths must be distinct')
    return dict(revision=REVISION,reader_sha256=READER_SHA256,source_hashes={p:sha((ROOT/p).read_bytes()) for p in SOURCES},
                proxy_manifest=proxy_context(proxy_manifest),ready_files=paths,
                lock_start=LOCK_START,lock_bytes=LOCK_BYTES.hex(),checkpoint_names=list(CHECKPOINTS))


def compile_probe(packet):
    base=copy.deepcopy(packet);c=base.pop('primary_capture')
    need(canonical(c)==canonical(contract(c['proxy_manifest']['path'],c['ready_files'])),
         'primary capture contract differs')
    generated=route.compile_probe(base)
    ids={int(m[1]) for m in re.finditer(r'(?im)^\s*bp(\d+)(?=\s)',generated)}
    need(not ids&{110,111},'primary Lock breakpoint IDs collide')
    commands,checks=additions()
    base['startup_commands_before_final_g']+=commands
    base['byte_checks_before_first_breakpoint']+=checks
    generated=route.compile_probe(base)
    token='.echo MPCAP_PRIMARY_OBSERVERS_ARM'
    need(generated.count(token)==1,'unique facility Lock-arm seam required')
    generated=generated.replace(token,'be 110 111; '+token)
    for name in CHECKPOINTS:
        token='.echo MPCAP_HOST_READY name='+name
        need(generated.count(token)==(2 if name=='full-published' else 1),'exact checkpoint stop seams required: '+name)
        path=c['ready_files'][name].replace('\\','/')
        generated=generated.replace(token,'$$>a<\\"'+path+'\\"; '+token)
    need(all(len(line)<4096 for line in generated.splitlines()),'CDB command exceeds transport bound')
    return generated


def prepare(original,candidate,*,proxy_manifest,ready_files,**kwargs):
    for image in (original,candidate):
        _,data=route.producer._read(image,LOCK_START,len(LOCK_BYTES));need(data==LOCK_BYTES,'native primary Lock bytes differ')
    packet=route.producer.build_screen_probe(original,candidate,**kwargs)
    packet['primary_capture']=contract(proxy_manifest,ready_files)
    probe=compile_probe(packet)
    return dict(prepared=True,runtime_ready=False,packet=packet,probe=probe,probe_sha256=sha(probe.encode('ascii')),
                ready_scripts={name:dict(path=packet['primary_capture']['ready_files'][name],text=ready_script(name,packet),
                    sha256=sha(ready_script(name,packet).encode('ascii'))) for name in CHECKPOINTS})


class PrimaryObservationError(ValueError):
    """A failed primary sequence with every original reserved-namespace row."""
    def __init__(self,message,records,*,route_report=None):
        super().__init__(message)
        self.raw_records=records
        self.route_report=copy.deepcopy(route_report)


def primary_observation_records(log):
    return [dict(line=n,marker=line.split(' ',1)[0],text=line)
            for n,line in enumerate(log.splitlines(),1) if re.search(r'MPRI_',line,re.I)]


def primary_failure_diagnostics(error):
    result=dict(primary_observation_records=error.raw_records)
    if error.route_report is not None:result['primary_route_diagnostics']=error.route_report
    return result


def evaluate_primary_sequence(log,packet,core,checkpoint):
    try:
        return _evaluate_primary_sequence(log,packet,core,checkpoint)
    except ValueError as error:
        raise PrimaryObservationError(str(error),primary_observation_records(log),route_report=core) from error


def _evaluate_primary_sequence(log,packet,core,checkpoint):
    expected=CHECKPOINTS[:CHECKPOINTS.index(checkpoint or 'final-ready')+1]
    rows=[];pairs=[];pending=None;points=[];contract_lines=[]
    core_points=core['primary_route_sequence']['checkpoints']
    screens=[r for r in core['modal_sequence']['raw_records'] if r['marker']=='MCAP_SCREEN_ENTRY']
    need(len(screens)==1,'one authenticated facility entry required')
    screen_line=screens[0]['line']
    for number,line in enumerate(log.splitlines(),1):
        if line=='MPRI_NATIVE_CONTRACT_PASS':contract_lines.append(number);continue
        if not re.search(r'MPRI_',line,re.I):continue
        key=line.split(' ',1)[0];match=REGEX.get(key)
        match=match.fullmatch(line) if match else None
        need(match is not None,f'line {number}: malformed/rejected primary observation')
        values={k:(v if k=='name' else int(v,10 if k in ('width','height','pitch') else 16)) for k,v in match.groupdict().items()}
        row=dict(line=number,marker=key,text=line,values=values);rows.append(row)
        if key=='MPRI_LOCK_CALL':
            need(number>screen_line,'primary Lock observation precedes facility observer arming')
            need(pending is None,'overlapping primary Lock calls')
            need((values['rect'],values['flags'],values['event'])==(0,1,0),'full NULL-rect flags1 Lock required')
            need(values['descriptor']==values['backend']+0x38 and values['surface']>0,'primary Lock call object differs')
            pending=row
        elif key=='MPRI_LOCK_RETURN':
            need(pending is not None,'primary Lock return without call')
            a=pending['values'];w,h=map(int,packet['resolution'].split('x'))
            need(all(values[k]==a[k] for k in ('tid','backend','surface','descriptor')) and values['esp']==a['esp']+20,'native primary Lock stdcall pairing differs')
            need(values['hr']==0 and (values['width'],values['height'],values['pitch'])==(w,h,w),'primary Lock result/pitch differs')
            pairs.append(dict(call=pending,returned=row));pending=None
        else:
            index=len(points);need(index<len(expected) and values['name']==expected[index],'primary checkpoint order differs')
            need(pending is None and pairs,'checkpoint requires a completed current primary Lock')
            native=core_points[index];v=native['values'];last=pairs[-1]
            need(native['name']==values['name'] and native['index']==index,'core/primary checkpoint identity differs')
            need(all(values[k]==v[k] for k in ('tid','eip','esp')),'checkpoint machine identity differs')
            need(last['returned']['line']<number and all(values[k]==last['returned']['values'][k]
                for k in ('tid','backend','surface','pixels','width','height','pitch')),'checkpoint has stale or different primary descriptor')
            need(values['palette']>0,'checkpoint requires current attached palette')
            need(number==native['line']+1 and native['host_ready_line']==number+1,
                 'primary observation must be exactly between native checkpoint and host marker')
            need(0<values['pixels']<=0xffffffff-values['width']*values['height'], 'primary pixel range wraps')
            points.append(dict(name=values['name'],index=index,line=number,values=values,canvas=native['canvas'],last_lock=last))
    need(len(contract_lines)==1 and pairs and contract_lines[0]<pairs[0]['call']['line'],'native Lock byte contract missing or duplicated')
    need(pending is None and len(points)==len(expected),'incomplete primary checkpoint prefix')
    need(rows[-1]['marker']=='MPRI_CHECKPOINT','primary observation after final paused checkpoint')
    return dict(passed=True,checkpoints=points,raw_records=rows,lock_pairs=pairs,checkpoint=expected[-1],limits=LIMITS)


def evaluate_trace(log,*,original,candidate,packet,generated_probe,ready_scripts,checkpoint=None):
    need(checkpoint is None or checkpoint in CHECKPOINTS,'invalid checkpoint scope')
    raw=log if type(log) is bytes else log.encode('utf-8');text=raw.decode('utf-8-sig')
    check_reader();compiled=compile_probe(packet)
    need(generated_probe.decode('ascii').replace('\r\n','\n')==compiled,'entire actual primary probe differs')
    need(set(ready_scripts)==set(CHECKPOINTS),'all four actual checkpoint scripts required')
    for name,data in ready_scripts.items():need(data==ready_script(name,packet).encode('ascii'),'checkpoint script differs: '+name)
    base=copy.deepcopy(packet);base.pop('primary_capture')
    core=route.evaluate_trace(text,original=original,candidate=candidate,packet=base,
                             generated_probe=route.compile_probe(base).encode('ascii'),checkpoint=checkpoint)
    if core.get('passed') is not True or core.get('failures')!=[]:
        raise PrimaryObservationError('core primary route failed: '+str(core.get('failures')),
                                      primary_observation_records(text),route_report=core)
    sequence=evaluate_primary_sequence(text,packet,core,checkpoint)
    core['base_route_source']=copy.deepcopy(core['source'])
    core['source'].update(log_raw_sha256=sha(raw),generated_probe_sha256=sha(generated_probe),
        generated_probe_canonical_lf_sha256=sha(compiled.encode('ascii')),validator_sha256=sha(Path(__file__).read_bytes()),
        ready_script_sha256={n:sha(b) for n,b in ready_scripts.items()})
    core.update(primary_sequence=sequence,capture_checkpoint=sequence['checkpoints'][-1],checkpoint=sequence['checkpoint'],
                complete_route_proven=sequence['checkpoint']=='final-ready',primary_capture_revision=REVISION)
    return core


def validate_loaded_proxy_header(captured,proxy_image,proxy_base):
    proxy=reader._Proxy(proxy_image,reader.SUPPORTED_PROXY_SHA256,proxy_base)
    offset=reader._u32(proxy_image,0x3c)+24+28
    need(type(captured) is bytes and len(captured)==512 and offset+4<=512,'unsupported loaded proxy header extent')
    expected=bytearray(proxy_image[:512]);struct.pack_into('<I',expected,offset,proxy_base)
    need(captured==bytes(expected),'loaded proxy header differs beyond measured ImageBase')
    return dict(image_size=proxy.size,image_base_offset=offset,preferred_base=proxy.preferred,measured_load_base=proxy_base,
                captured_header_sha256=sha(captured),rule='exact_pinned_header_with_only_ImageBase_equal_measured_load_base')


def audit_snapshot(manifest,*,proxy_image,trace,artifacts):
    """Consume an authentic named checkpoint, never legacy-ready projection."""
    need(trace.get('passed') is True,'freshly authenticated checkpoint trace required')
    cp=trace['capture_checkpoint'];v=cp['values'];last=cp['last_lock'];owner=manifest['game_identity']
    phases=[]
    for phase in ('before','after'):
        phases.append({name:reader.Read(integer(row['address'],'read address',1),artifacts.artifact(row))
                       for name,row in manifest['reads'][phase].items()})
    before,after=phases;need(before==after,'primary reads changed across paused capture')
    for name in (*reader.Snapshot.__dataclass_fields__,'surface_full','proxy_header','proxy_getpalette'):
        need(name in before,'missing primary read: '+name)
    need(before['surface_full'].address==v['surface'] and len(before['surface_full'].data)==32
         and reader._u32(before['surface_full'].data,28)==v['palette'],'attached palette pointer differs')
    need(before['surface_full'].data[:4]==before['surface'].data,'repeated COM vtable differs')
    module=manifest['proxy_module'];base=integer(module['base'],'proxy base',1)
    header=validate_loaded_proxy_header(before['proxy_header'].data,proxy_image,base)
    need(before['proxy_header'].address==base and before['proxy_getpalette'].address==base+GET_PALETTE_RVA
         and before['proxy_getpalette'].data==GET_PALETTE_BYTES,'loaded proxy read address or implementation differs')
    need(module['sha256']==reader.SUPPORTED_PROXY_SHA256 and module['size']==header['image_size'],'loaded proxy identity differs')
    need(owner['candidate_sha256']==trace['candidate_sha256'] and manifest['trace_sha256']==trace['source']['log_raw_sha256'],'host/candidate/prefix binding differs')
    identity=dict(run_id=manifest['run_id'],process_id=owner['process_id'],process_start=owner['creation_utc'],
        candidate_sha256=trace['candidate_sha256'],proxy_sha256=reader.SUPPORTED_PROXY_SHA256,thread_id=v['tid'],
        trace_sha256=manifest['trace_sha256'],capture_boundary='MPCAP_HOST_READY:'+cp['name'],ready_line=cp['line'],
        last_primary_lock_line=last['returned']['line'],current_palette_line=cp['line'])
    fields={k:identity[k] for k in ('run_id','process_id','process_start','candidate_sha256','proxy_sha256','thread_id','trace_sha256','capture_boundary')}
    a,r=last['call'],last['returned']
    lock=dict(fields,schema='clash95_full_primary_lock_v1',line=r['line'],call_line=a['line'],call_eip=reader.LOCK_CALL,
        return_eip=reader.LOCK_RETURN,call_esp=a['values']['esp'],return_esp=r['values']['esp'],hresult=r['values']['hr'],
        rect_is_null=a['values']['rect']==0,flags=a['values']['flags'],event_handle=a['values']['event'],
        **{k:r['values'][k] for k in ('backend','surface','descriptor','pixels','width','height','pitch')},
        descriptor_sha256=sha(before['backend'].data[0x38:0xA4]))
    palette=dict(fields,schema='clash95_current_primary_palette_v1',line=cp['line'],surface=v['surface'],palette=v['palette'],
                 entries_address=v['palette']+12,entries_sha256=sha(before['palette'].data[12:]),entry_count=256)
    raw=artifacts.artifact(manifest['pixels']);regions=[reader.Region(**x) for x in manifest['regions']]
    for name,value in before.items():reader._read(value,value.address,len(value.data),name,regions)
    snapshots=[reader.Snapshot(**{k:phase[k] for k in reader.Snapshot.__dataclass_fields__}) for phase in phases]
    result=reader.validate_snapshot(*snapshots,reader.Read(manifest['pixels']['address'],raw),width=v['width'],height=v['height'],
        proxy_image=proxy_image,expected_proxy_sha256=reader.SUPPORTED_PROXY_SHA256,proxy_base=base,regions=regions,
        identity=identity,lock_observation=lock,palette_observation=palette)
    need(artifacts.artifact(manifest['palette_entries'],size=1024)==before['palette'].data[12:],'palette extraction differs')
    result.update(loaded_proxy_header=header,checkpoint=cp['name'])
    return result


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--prepare',action='store_true')
    for name in ('original','candidate','candidate-manifest','proxy-manifest','log','packet','probe','out-dir','snapshot-manifest','proxy'):
        ap.add_argument('--'+name,type=Path,required=name in ('original','candidate'))
    for name in ('candidate-sha256','stage','resolution','route','availability'):ap.add_argument('--'+name)
    ap.add_argument('--castle-index',type=int);ap.add_argument('--minimap-viewport',action='store_true')
    ap.add_argument('--checkpoint',choices=CHECKPOINTS);args=ap.parse_args(argv)
    try:
        original,candidate=args.original.read_bytes(),args.candidate.read_bytes()
        if args.prepare:
            need(args.out_dir is not None,'preparation requires --out-dir')
            ready_files={n:str(path_value(args.out_dir)/('primary-'+n+'.cdb')) for n in CHECKPOINTS}
            result=prepare(original,candidate,ready_files=ready_files,proxy_manifest=args.proxy_manifest,
                candidate_sha256=args.candidate_sha256,stage=args.stage,resolution=args.resolution,route=args.route,
                availability=args.availability,castle_index=args.castle_index,candidate_manifest=args.candidate_manifest,minimap_viewport=True)
        else:
            packet=route.strict_json_object(args.packet.read_bytes())
            scripts={n:path_value(p).read_bytes() for n,p in packet['primary_capture']['ready_files'].items()}
            if args.snapshot_manifest:
                import modal_primary_surface_audit as audit
                artifacts=Artifacts();receipt=artifacts.json(args.snapshot_manifest)
                need(path_value(args.snapshot_manifest)==path_value(receipt['plan']['out_dir'])/'primary-triplet.json',
                     'canonical primary triplet path required')
                need(args.proxy is not None and path_value(args.proxy)==path_value(receipt['plan']['proxy_path']),
                     'actual planned proxy path required')
                for actual,expected in ((args.log,receipt['capture_prefix']['path']),(args.packet,receipt['packet']['path']),
                    (args.probe,receipt['probe']['path']),(args.original,receipt['plan']['original']),
                    (args.candidate,receipt['plan']['candidate_path'])):
                    need(path_value(actual)==path_value(expected),'triplet CLI artifact role differs')
                need(args.checkpoint in (None,'final-ready'),'full triplet cannot be scoped to an earlier prefix')
                snapshot=audit.bind_triplet(receipt,reader=artifacts)
                passed=snapshot['primary_composition_proven'] is True
                result=dict(passed=passed,ready_for_host_capture=False,primary_snapshot=snapshot,
                    source=snapshot['final_trace_source'],audit_log_scope='complete retained final log and all four nested capture prefixes',
                    failures=[] if passed else ['primary draw-order pixels differ'],manual_input_proof=False,promotion_ready=False)
            else:
                result=evaluate_trace(args.log.read_bytes(),original=original,candidate=candidate,packet=packet,
                                      generated_probe=args.probe.read_bytes(),ready_scripts=scripts,checkpoint=args.checkpoint)
        code=0 if result.get('prepared') or result.get('passed') else 2
    except (ValueError,KeyError,TypeError,OSError,AttributeError,UnicodeError) as error:
        result=dict(passed=False,prepared=False,ready_for_host_capture=False,failures=[str(error)],manual_input_proof=False,promotion_ready=False);code=2
        if isinstance(error,PrimaryObservationError):result.update(primary_failure_diagnostics(error))
    print(json.dumps(result,indent=2));return code


if __name__=='__main__':raise SystemExit(main())
