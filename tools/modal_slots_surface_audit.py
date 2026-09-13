#!/usr/bin/env python3
"""Re-evaluate exact slots trace, paused captures and owned-process cleanup.

Accept only native-to-physical mirror pixels. This never grants primary/visible
composition, natural input, native modal exit, battle return or promotion.
"""
from pathlib import Path
import argparse
import hashlib
import json

import modal_slots_barracks_trace as trace

ROOT=Path(__file__).resolve().parents[1]
SOURCE_PATHS={
    'host_path': 'scripts/cdb/run_modal_slots_barracks_capture.ps1',
    'producer': 'tools/modal_slots_barracks_probe.py',
    'trace': 'tools/modal_slots_barracks_trace.py',
    'converter': 'tools/cdb_surface_dump_to_png.py',
    'proxy_source': 'src/ddraw_surfdump_proxy/ddraw_surfdump_proxy.cpp',
}


def sha(data):return hashlib.sha256(data).hexdigest()


def mirror_pixels(native,physical,width,height):
    if type(width) is not int or type(height) is not int or width<640 or height<480:
        raise ValueError('native/physical dimensions invalid')
    if len(native)!=640*480 or len(physical)!=width*height:
        raise ValueError('raw canvas lengths differ from exact strides')
    ox,oy=(width-640)//2,(height-480)//2
    mismatches=0;outside=0
    for y in range(height):
        row=physical[y*width:(y+1)*width]
        if oy<=y<oy+480:
            mismatches+=sum(a!=b for a,b in zip(row[ox:ox+640],native[(y-oy)*640:(y-oy+1)*640]))
            outside+=sum(value!=0 for value in row[:ox])+sum(value!=0 for value in row[ox+640:])
        else:outside+=sum(value!=0 for value in row)
    slots=[]
    for y in (75,206):
        for x in (126,197,268,339,410,481):
            nonzero=sum(value!=0 for yy in range(y,y+64) for value in native[yy*640+x:yy*640+x+32])
            different=sum(native[yy*640+xx]!=physical[(yy+oy)*width+xx+ox]
                for yy in range(y,y+64) for xx in range(x,x+32))
            slots.append(dict(x=x,y=y,width=32,height=64,native_nonzero_pixels=nonzero,mirror_mismatches=different))
    return dict(passed=mismatches==0 and outside==0 and all(s['native_nonzero_pixels']>0 for s in slots),
        centered_mismatches=mismatches,outside_nonzero_pixels=outside,slots=slots,
        primary_composition_proven=False)


def evaluate(summary_path):
    path=Path(summary_path).resolve();raw=path.read_bytes();summary=json.loads(raw)
    failures=[];captures=[];parsed=None
    def require(value,message):
        if not value:failures.append(message)
    def bound_file(row):
        data=Path(row['path']).read_bytes()
        if sha(data)!=row['sha256']:raise ValueError('artifact SHA differs: '+str(row['path']))
        return data
    try:
        require(summary.get('schema')=='clash95_modal_slots_capture_v1','wrong capture schema')
        require(summary.get('passed') is True and summary.get('executed') is True,'capture summary is not an affirmative success')
        failures.extend('original capture failure: '+str(x) for x in summary.get('failures',[]))
        plan=summary['plan']
        require(plan['stage']==trace.producer.STAGE,'capture stage differs')
        require(plan.get('minimap_viewport') is True,'minimap candidate context missing')
        out_dir=Path(plan['out_dir']).resolve()
        require(path==out_dir/'summary.json','summary is outside its exact planned output path')
        for label in ('original','input_candidate','candidate_path','candidate_manifest','proxy_path','host_path','producer','trace','converter',
                      'proxy_source','proxy_input','proxy_manifest','python','cdb'):
            key={'original':'original_sha256','input_candidate':'candidate_sha256','candidate_path':'candidate_sha256',
                 'candidate_manifest':'candidate_manifest_sha256','proxy_path':'proxy_sha256',
                 'host_path':'host_sha256','producer':'producer_sha256','trace':'trace_sha256','converter':'converter_sha256',
                 'proxy_source':'proxy_source_sha256','proxy_input':'proxy_sha256','proxy_manifest':'proxy_manifest_sha256',
                 'python':'python_sha256','cdb':'cdb_sha256'}[label]
            require(sha(Path(plan[label]).read_bytes())==plan[key],label+' changed since capture plan')
        for label,relative in SOURCE_PATHS.items():
            require(Path(plan[label]).resolve()==(ROOT/relative).resolve(),label+' is not the current canonical source path')
        for name,filename in (('packet','packet.json'),('probe','modal-slots-barracks.cdb'),
                              ('final_log','cdb.log'),('capture_prefix','capture-prefix.log')):
            require(Path(summary[name]['path']).resolve()==out_dir/filename,name+' is outside its exact planned output path')
        original=Path(plan['original']).read_bytes();candidate=Path(plan['candidate_path']).read_bytes()
        packet=json.loads(bound_file(summary['packet']));probe=bound_file(summary['probe'])
        log=bound_file(summary['final_log']);prefix=bound_file(summary['capture_prefix'])
        require(log.startswith(prefix),'final log lost or changed original capture prefix')
        parsed=trace.evaluate_trace(log.decode('utf-8-sig'),original=original,candidate=candidate,packet=packet,generated_probe=probe)
        require(parsed.get('passed') is True and parsed.get('ready_for_host_capture') is True,'trace is not an affirmative capture acceptance')
        failures.extend('re-evaluated trace: '+x for x in parsed['failures'])
        # The rebuilt packet authenticates the intended route and candidate.
        # A self-consistent host plan must not relabel it or select other source
        # files merely by refreshing that plan's own path/hash pairs.
        for key in ('stage','resolution','castle_index','availability','minimap_viewport','candidate_sha256',
                    'original_sha256','stop_va','canvas_state_va','canvas_state_offsets'):
            require(plan[key]==packet[key],'plan/packet '+key+' differs')
        require(plan['route']==packet['route']['name'],'plan/packet route differs')
        width,height=map(int,packet['resolution'].split('x'))
        require(type(plan['width']) is int and type(plan['height']) is int
                and (plan['width'],plan['height'])==(width,height),'plan dimensions differ from packet resolution')
        require(plan['probe_sha256']==sha(probe),'plan probe SHA differs from compiled artifact')
        for label,relative in SOURCE_PATHS.items():
            if label in ('host_path','producer','trace'):
                key='host_sha256' if label=='host_path' else label+'_sha256'
                require(plan[key]==packet['capture_source_hashes'][relative],label+' hash differs from rebuilt packet source')
        ready_rows=[row for row in (parsed.get('modal_sequence') or {}).get('raw_records',[])
                    if row['marker']=='MCAP_CANVAS' and (row.get('values') or {}).get('event')=='READY']
        require(len(ready_rows)==1,'one source-bound owned-canvas readiness required')
        ready=ready_rows[0]['values'] if len(ready_rows)==1 else {}
        require(packet['candidate_manifest']=={'path':str(Path(plan['candidate_manifest']).resolve()),'sha256':plan['candidate_manifest_sha256']},
                'packet/host manifest context differs')
        require(summary.get('clean_stable_pair') is True,'paused capture stability not affirmative')
        rows=summary.get('snapshots',[]);require(len(rows)==3,'three original paused captures required')
        require(summary.get('snapshot')==rows[0] if rows else False,'primary summary snapshot differs from first capture')
        keys=[]
        for index,row in enumerate(rows,1):
            physical=bound_file(row);native=bound_file(row['native'])
            folder=out_dir/('capture-'+str(index))
            require(Path(row['path']).resolve()==folder/'surface.raw' and Path(row['native']['path']).resolve()==folder/'native-surface.raw',
                    'raw capture path is not this run/index; reused or mixed evidence refused')
            require(row.get('paused') is True and row.get('capture')=='owned_physical_mirror','capture class/pause differs')
            require((row['width'],row['height'],row['pitch'])==(plan['width'],plan['height'],plan['width']),'physical geometry differs')
            require((row['native']['width'],row['native']['height'],row['native']['pitch'])==(640,480,640),'native stride differs')
            headers=[]
            for name in ('state','e0','physical_header','native_header'):
                for phase in ('before','after'):
                    require(Path(row['reads'][phase][name]['path']).resolve()==folder/('surface-'+phase+'-'+name+'.raw'),
                            'header/state path is not this run/index/phase: '+name)
                before=bound_file(row['reads']['before'][name]);after=bound_file(row['reads']['after'][name])
                require(before==after,'paused ownership/header changed: '+name)
                expected_address={'state':packet['canvas_state_va'],'e0':0x5202E0,
                                  'physical_header':ready.get('physical'),'native_header':ready.get('native')}[name]
                require(row['reads']['before'][name]['address']==expected_address and row['reads']['after'][name]['address']==expected_address,
                        'header/state capture address differs: '+name)
                def word(offset,size=4):return int.from_bytes(before[offset:offset+size],'little')
                if name=='state':
                    expected=dict(phase=1,physical=ready.get('physical'),native=ready.get('native'),
                        root_esp=ready.get('root_esp'),owner_tid=ready.get('tid'),enter_status=1,
                        mirror_status=1,leave_status=0,fault=0,allocations=1,frees=0,mirrors=3,
                        pending_header=0,pending_pixels=0,native_pixels=ready.get('native_pixels'),physical_pixels=ready.get('physical_pixels'))
                    require(len(before)==128 and all(word(trace.producer.canvas.STATE[key])==value for key,value in expected.items()),
                            'captured ownership state differs from ordered trace')
                elif name=='e0':require(len(before)==4 and word(0)==ready.get('native'),'captured E0 is not owned native canvas')
                else:
                    native_header=name=='native_header'
                    expected=(640,480,ready.get('native_pixels')) if native_header else (plan['width'],plan['height'],ready.get('physical_pixels'))
                    require(len(before)==188 and (word(0,2),word(2,2),word(4))==expected and word(184)==0x50EE24,
                            'captured memory header differs: '+name)
                    if native_header:require(word(172)==0,'native canvas unexpectedly owns COM interface')
                headers.append(sha(before))
            require(row.get('physical')==ready.get('physical') and row.get('physical_pixels')==ready.get('physical_pixels')
                    and row['native'].get('surface')==ready.get('native') and row['native'].get('base')==ready.get('native_pixels'),
                    'pixel artifact addresses differ from source-bound readiness')
            require(len(summary.get('candidates',[]))==1 and row.get('game_identity')==summary['candidates'][0],
                    'capture belongs to another process identity')
            keys.append((sha(physical),sha(native),*headers))
            result=mirror_pixels(native,physical,plan['width'],plan['height'])
            captures.append(dict(physical_path=row['path'],native_path=row['native']['path'],**result))
            require(result['passed'],'native/physical mirror mismatch, blank native slot, or uncleared outer region')
        require(bool(keys) and all(value==keys[0] for value in keys),'three paused pixels/ownership captures differ')
        cleanup=summary['cleanup'];children=cleanup.get('candidates',[])
        require(cleanup.get('desktop_closed') is True,'hidden desktop cleanup missing')
        require(len(children)==1 and len(summary.get('candidates',[]))==1,'exactly one owned candidate cleanup required')
        for row in [cleanup.get('cdb')]+children:
            require(isinstance(row,dict) and row.get('absent') is True and row.get('handle_closed') is True,'owned process absence/handle close missing')
        if cleanup.get('cdb'):require(cleanup['cdb'].get('identity')==summary.get('cdb'),'debugger cleanup identity differs')
        if len(children)==1:require(children[0].get('identity')==summary['candidates'][0],'candidate cleanup identity differs')
        identities=[summary.get('cdb')]+summary.get('candidates',[])
        require(len(identities)==2 and all(isinstance(row,dict) and type(row.get('process_id')) is int and row['process_id']>0
            and type(row.get('creation_filetime')) is int and row['creation_filetime']>0 and row.get('handle_retained') is True for row in identities),
            'measured retained-handle process identity is incomplete')
        if len(identities)==2 and all(isinstance(row,dict) for row in identities):
            debugger,game=identities
            require(debugger.get('process_id')!=game.get('process_id') and game.get('parent_process_id')==debugger.get('process_id')
                and game.get('candidate_sha256')==plan['candidate_sha256'],'candidate parent/hash identity differs')
            require(Path(game.get('path','')).resolve()==Path(plan['candidate_path']).resolve()
                and Path(debugger.get('path','')).resolve()==Path(plan['cdb']).resolve(),'retained process image path differs')
    except (OSError,ValueError,TypeError,KeyError,IndexError,UnicodeError) as error:
        failures.append(str(error))
    return dict(schema='clash95_modal_slots_surface_audit_v1',passed=not failures,
        summary_path=str(path),summary_sha256=sha(raw),source_sha256=sha(Path(__file__).read_bytes()),
        stage=summary.get('plan',{}).get('stage'),candidate_sha256=summary.get('plan',{}).get('candidate_sha256'),
        captures=captures,trace=parsed,failures=failures,proof_class='hidden_forced_barracks_native_physical_mirror',
        primary_composition_proven=False,visible_composition_proof=False,manual_input_proof=False,
        native_modal_exit_proven=False,promotion_ready=False)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--summary',required=True,type=Path)
    args=parser.parse_args()
    try:report=evaluate(args.summary)
    except (OSError,ValueError,TypeError,KeyError) as error:
        report=dict(passed=False,failures=[str(error)],promotion_ready=False)
    print(json.dumps(report,indent=2));return 0 if report['passed'] else 2


if __name__=='__main__':raise SystemExit(main())
