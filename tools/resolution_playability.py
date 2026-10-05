"""Explicit real-game menu, campaign and map-input diagnostics for launcher presets."""
from __future__ import annotations

import argparse
import ctypes as C
from ctypes import wintypes as W
import hashlib
import json
import os
import re
import shutil
import stat
from pathlib import Path
import subprocess
import sys
import time
import uuid
from copy import deepcopy
from unittest.mock import patch

import launcher_resolution_matrix as matrix
import run_original_game_smoke as owned

MENU_RGB_SHA256 = '064467053c1c8a1fcbc3a897b4379e7b788339d3ae8e22fa8fa978be2d6f0ca7'
STATE_HELPER = r'''
static void map_state(Session &s, const std::string &out, int sample) {
    try {
        ULONG data=s.word(0x5202e4);
        if (!data) return;
        ULONG w=s.word(data+0x222e0), h=s.word(data+0x222e4);
        ULONG x=s.word(data+0x222e8), y=s.word(data+0x222ec);
        char name[80]; sprintf_s(name,"/map-state-%02d.json",sample);
        std::ofstream f(out+name);
        f<<"{\"game_data\":"<<data<<",\"world_width\":"<<w<<",\"world_height\":"<<h
         <<",\"scroll_x\":"<<static_cast<LONG>(x)<<",\"scroll_y\":"<<static_cast<LONG>(y)
         <<",\"map_active_word\":"<<s.word(0x527c24)<<",\"native_modal_word\":"<<s.word(0x52698c)
         <<",\"render_hook\":"<<s.word(0x5199d8)<<",\"post_callback\":"<<s.word(0x526990)
         <<",\"lower_owner\":"<<s.word(0x526994)<<",\"current_player\":"<<s.word(0x5202ec)
         <<",\"selected_stack\":"<<s.word(0x511b58)<<",\"previous_stack\":"<<s.word(0x511b5c)
         <<",\"panel_stack\":"<<s.word(0x514194)
         <<",\"map_surface\":"<<s.word(0x5202e0)
         <<",\"map_extent\":"<<(s.word(0x5202e0)?s.word(s.word(0x5202e0)):0)
         <<",\"map_pixels\":"<<(s.word(0x5202e0)?s.word(s.word(0x5202e0)+4):0)
         <<",\"map_vtable\":"<<(s.word(0x5202e0)?s.word(s.word(0x5202e0)+0xb8):0)
         <<",\"primary_extent\":"<<s.word(0x51d4c0)
         <<",\"cursor_raw_x\":"<<s.word(0x544cfc)<<",\"cursor_raw_y\":"<<s.word(0x544d00)
         <<",\"cursor_shift\":"<<static_cast<unsigned>(s.read(0x54512c,1)[0])<<"}\n";
        if (!f) throw std::runtime_error("map state write failed");
    } catch(const std::exception &e) { printf("REAL_MAP_STATE_UNAVAILABLE sample=%d reason=%s\n",sample,e.what()); }
}
'''


def observation_source(source: str) -> str:
    marker='static void snapshot(Session &s,const std::string &out,int sample,bool proxy) {'
    if source.count(marker)!=1 or source.count('seconds>90')!=1:
        raise ValueError('Unexpected native observation source')
    return source.replace(marker,STATE_HELPER+'\n'+marker+'\n    map_state(s,out,sample);').replace('seconds>90','seconds>180')


def fit_size(width: int, height: int, limit_w: int, limit_h: int) -> tuple[int,int]:
    if any(type(n) is not int or n<=0 for n in (width,height,limit_w,limit_h)):
        raise ValueError('Positive integer dimensions required')
    scale=min(1.0,limit_w/width,limit_h/height)
    return max(1,int(width*scale)),max(1,int(height*scale))


def indexed_image(path: Path):
    from PIL import Image
    meta=json.loads(path.read_text(encoding='utf-8'))
    w,h,pitch=(meta[k] for k in ('width','height','pitch'))
    if any(type(n) is not int for n in (w,h,pitch)) or not (640<=w<=3840 and 480<=h<=2160 and w<=pitch<=8192):
        raise ValueError('Unexpected primary dimensions')
    raw=path.with_suffix('.raw').read_bytes()
    palette=path.with_name(path.stem+'-palette.bin').read_bytes()
    if len(raw)!=pitch*h or len(palette)!=1024 or meta.get('proxy_private_palette') is not True:
        raise ValueError('Primary or palette identity incomplete')
    image=Image.frombytes('P',(w,h),raw,'raw','P',pitch,1)
    image.putpalette(bytes(v for i in range(0,1024,4) for v in palette[i:i+3]))
    return image.convert('RGB'),b''.join(raw[y*pitch:y*pitch+w] for y in range(h))


def menu_identity(image) -> dict:
    w,h=image.size
    if w<640 or h<480:raise ValueError('Primary is smaller than the native menu')
    x,y=(w-640)//2,(h-480)//2
    native=image.convert('RGB').crop((x,y,x+640,y+480))
    raw=bytearray(native.tobytes())
    for row in range(32):raw[row*640*3:(row*640+32)*3]=b'\0'*(32*3)
    digest=hashlib.sha256(raw).hexdigest()
    return dict(matches_original=digest==MENU_RGB_SHA256,rgb_sha256=digest,
                expected_rgb_sha256=MENU_RGB_SHA256,native_bounds=[x,y,x+640,y+480],
                excluded_native_rectangle=[0,0,32,32],exclusion='Original initial cursor only; no control overlaps this corner')



def stage_present_override(original: Path, profile: str, resolution: str, out: Path,
                           baseline_exe: Path, baseline: dict):
    from src.patcher import native_present_bounds as correction
    image, metadata, probe = correction.build_candidate(original.read_bytes(), profile, resolution)
    if metadata['base_candidate_sha256'] != baseline['candidate_sha256'] or matrix.digest(baseline_exe) != baseline['candidate_sha256']:
        raise ValueError('Presentation correction predecessor differs from the actual launcher build')
    if (metadata['profile'] != profile or metadata['resolution'] != resolution
            or metadata['recipe_revision'] != correction.REVISION
            or metadata['candidate_sha256'] != hashlib.sha256(image).hexdigest()
            or metadata['probe_sha256'] != hashlib.sha256(probe.encode()).hexdigest()):
        raise ValueError('Presentation correction returned mismatched candidate identity')
    matrix.runtime.verify_hd_sources({'source_hashes': metadata['source_hashes']}, matrix.ROOT)
    directory=out/'native-present';directory.mkdir(exist_ok=False)
    target=directory/f'clash95_{profile}_{resolution}_nativepresent.exe'
    for path,data in ((target,image),(target.with_suffix('.candidate.json'),(json.dumps(metadata,indent=2)+'\n').encode()),
                      (target.with_suffix('.cdb'),probe.encode())):
        with path.open('xb') as stream:stream.write(data)
    if matrix.digest(target) != metadata['candidate_sha256']:
        raise ValueError('Presentation candidate write differs')
    return target,dict(baseline,stage=metadata['stage'],recipe_revision=metadata['recipe_revision'],
        candidate_sha256=metadata['candidate_sha256'],predecessor_launcher_build=baseline['launcher_build'],
        launcher_build=dict(output_sha256=metadata['candidate_sha256'],source_sha256=metadata['source_hashes']),
        experimental_override=metadata)


def selected_unit(states: list[dict]) -> bool:
    return any(type(s.get('selected_stack')) is int and 0 <= s['selected_stack'] < 500
               and s.get('render_hook') == 0x40ad40 and s.get('map_active_word', 0) != 0
               and 1 <= s.get('world_width', 0) <= 100 and 1 <= s.get('world_height', 0) <= 100
               for s in states)


def full_observation(log: str, returncode: int) -> dict:
    record = matrix.runtime.outcome(log, returncode)
    endings = re.findall(r'^REAL_END entered=1 exited=0 exception_stop=0 elapsed_ms=([0-9]+)$', log, re.M)
    record['requested_interval_completed'] = len(endings) == 1 and int(endings[0]) >= 110000
    record['observation_complete'] = record['observation_complete'] and record['requested_interval_completed']
    return record


def input_success(record: dict) -> bool:
    rows=record.get('steps',[])
    return bool(rows) and record.get('all_steps_accounted') is True and all(
        r.get('clicked') is True and r.get('aim',{}).get('converged') is True for r in rows)


def screen_context(state: dict) -> dict:
    """Classify the measured native owner; map buffers can survive castle entry."""
    owner=state.get('render_hook')
    result=dict(render_hook=owner,ordinary_map=False)
    if type(owner) is not int:
        return dict(result,screen='unknown',reason='Missing or invalid native render owner')
    if owner==0x422020:
        return dict(result,screen='castle_overview',reason='Castle owns the native renderer')
    if owner!=0x40ad40:
        return dict(result,screen='other_native_screen',reason='Ordinary map does not own the native renderer')
    for name in ('game_data','map_active_word','map_surface','map_pixels'):
        value=state.get(name)
        if type(value) is not int or not 0<value<=0xffffffff:
            return dict(result,screen='invalid_map_context',reason='Missing or invalid '+name)
    if type(state.get('native_modal_word')) is not int or state['native_modal_word']!=0:
        return dict(result,screen='invalid_map_context',reason='Native modal state is active or unavailable')
    for axis,extent in (('x','width'),('y','height')):
        size=state.get('world_'+extent);scroll=state.get('scroll_'+axis)
        if (type(size) is not int or not 1<=size<=100 or type(scroll) is not int
                or not 0<=scroll<size):
            return dict(result,screen='invalid_map_context',reason='Invalid world or scroll '+axis)
    return dict(result,screen='ordinary_map',ordinary_map=True,reason='Native map owner and context observed')


def primary_context(path: Path) -> dict:
    """Use only state recorded at this primary's paused snapshot, never a neighbor."""
    match=re.fullmatch(r'primary-([0-9]+)\.json',path.name)
    if not match:raise ValueError('Unexpected primary sample name')
    state_path=path.with_name('map-state-'+match[1]+'.json')
    result=dict(state_sample=state_path.name,ordinary_map=False,screen='unavailable')
    try:
        metadata_raw=path.read_bytes();state_raw=state_path.read_bytes()
        metadata=json.loads(metadata_raw);state=json.loads(state_raw)
        if not isinstance(metadata,dict) or not isinstance(state,dict):
            raise ValueError('Snapshot metadata and state must be objects')
        if metadata.get('paused') is not True:
            raise ValueError('Primary is not a paused snapshot')
        result.update(screen_context(state),primary_metadata_sha256=hashlib.sha256(metadata_raw).hexdigest(),
                      state_sha256=hashlib.sha256(state_raw).hexdigest())
    except (OSError,ValueError,TypeError) as error:
        result['reason']='Matching paused screen context unavailable: '+str(error)
    return result


def map_controls_passed(rows: list[dict]) -> bool:
    return len(rows)==3 and all(
        r.get('map_audit_applicable') is True
        and r.get('screen_context',{}).get('ordinary_map') is True
        and len(r.get('action_cells',[]))==6 and r.get('action_cells_exact') is True
        and (r.get('frame_required') is False or
             r.get('frame_required') is True and r.get('frame',{}).get('structural_border_exact') is True)
        for r in rows)


def validate_map_pixels(capture: Path, reference: Path, profile: str, resolution: str) -> list[dict]:
    import frame_surface_audit as frame
    import action_bar_surface_audit as bar
    from src.patcher.framed_viewport import FramedViewport
    def resource(name):
        found=[p for p in reference.rglob('*') if p.is_file() and p.name.lower()==name]
        if len(found)!=1:raise ValueError('Ambiguous resource: '+name)
        return found[0].read_bytes()
    layout=FramedViewport(*map(int,resolution.split('x')))
    rows=[];artwork=sprites=member=None
    paths=sorted(capture.glob('primary-*.json'))
    for path in paths[-3:]:
        context=primary_context(path)
        row=dict(sample=path.name,screen_context=context,map_audit_applicable=context['ordinary_map'],
                 frame_required=profile!='classic',frame=None,action_cells=[],action_cells_exact=False)
        if not context['ordinary_map']:
            row['audit_skipped_reason']=context['reason']
            rows.append(row)
            continue
        if sprites is None:
            artwork=frame.load_native_frame(resource('gfx3.res')) if profile!='classic' else None
            sprites,member=bar.load_sprites(resource('minimum.res'))
        image,raw=indexed_image(path)
        if image.size!=(layout.width,layout.height):raise ValueError('Final primary size differs')
        edges=frame.audit_surface(raw,layout,artwork) if profile!='classic' else None
        geometry_stage=bar.FRAMED_STAGE if profile!='classic' else None
        cells=bar.compare_cells(raw,layout.width,layout.height,sprites,stage=geometry_stage)
        row.update(frame=edges,action_cells=cells,action_cells_exact=len(cells)==6 and all(c['exact_source_match'] for c in cells),
                   frame_source_sha256=frame.RESOURCE_SHA256 if profile!='classic' else None,
                   action_source_sha256=bar.RESOURCE_SHA256,action_member_sha256=member)
        rows.append(row)
    return rows


def prepare_client(user, pid: int, width: int, height: int) -> dict:
    windows=[r for r in owned.windows_for(user,pid) if r['visible'] and r['window_class']=='Clash']
    if len(windows)!=1:raise ValueError('Expected one owned Clash window')
    hwnd=windows[0]['hwnd']
    user.GetClientRect.argtypes=[W.HWND,C.POINTER(W.RECT)];user.GetClientRect.restype=W.BOOL
    user.GetSystemMetrics.argtypes=[C.c_int];user.GetSystemMetrics.restype=C.c_int
    user.SetWindowPos.argtypes=[W.HWND,W.HWND,C.c_int,C.c_int,C.c_int,C.c_int,W.UINT]
    user.SetWindowPos.restype=W.BOOL
    bounds=(user.GetSystemMetrics(0),user.GetSystemMetrics(1))
    target=fit_size(width,height,*bounds)
    client=W.RECT();owned.require(user.GetClientRect(hwnd,C.byref(client)),'Get owned client')
    before=[client.right,client.bottom]
    if tuple(before)!=target:
        outer=W.RECT();owned.require(user.GetWindowRect(hwnd,C.byref(outer)),'Get owned window')
        dw=outer.right-outer.left-client.right;dh=outer.bottom-outer.top-client.bottom
        owned.require(user.SetWindowPos(hwnd,None,0,0,target[0]+dw,target[1]+dh,0x4000|0x0004|0x0010),'Fit owned diagnostic window')
        end=time.monotonic()+3
        while time.monotonic()<end:
            owned.require(user.GetClientRect(hwnd,C.byref(client)),'Measure resized owned client')
            if (client.right,client.bottom)==target:break
            time.sleep(.05)
    if (client.right,client.bottom)!=target:raise ValueError('Owned client did not reach the requested fitted size')
    return dict(hwnd=hwnd,before=before,client_size=list(target),primary_size=[width,height],
                desktop_size=list(bounds),scaled=target!=(width,height),native_pixel_display=target==(width,height))


def run_foreground(args) -> dict:
    case=matrix.select_case(args.profile,args.resolution)
    root=matrix.ROOT;reference=args.runtime.resolve();out=args.out.resolve()
    if os.name!='nt' or os.environ.get('GITHUB_ACTIONS')!='true':raise ValueError('Disposable Windows Actions runner required')
    if out.exists() or not out.is_relative_to(Path('C:/ClashTests').resolve()) or any(
        out.is_relative_to(p) or p.is_relative_to(out) for p in (root,reference)):
        raise ValueError('New external candidate output required')
    out.mkdir(parents=True);capture=out/'capture';capture.mkdir()
    report=dict(schema=1,case=case,approval_text=args.approval_text,actions=[],errors=[],
        gameplay_verified=False,manual_input_proof=False,promotion_ready=False,
        capture_scope='Actual primary plus fitted diagnostic-proxy window; no shipped-wrapper acceptance')
    proc=handle=kernel=None;baseline=None;work=out/'work';logpath=capture/'debugger.log'
    try:
        manifest=json.loads(args.manifest.read_text(encoding='utf-8-sig'))
        baseline=matrix.runtime.verify(reference,manifest)
        proxy=args.proxy.resolve();build=json.loads(proxy.with_name('ddraw_surfdump_proxy.build.json').read_text(encoding='utf-8-sig'))
        if build.get('generated_by')!='clash-hd-surface-dump-proxy' or matrix.digest(proxy)!=build['output_sha256'].lower() or matrix.digest(root/'src/ddraw_surfdump_proxy/ddraw_surfdump_proxy.cpp')!=build['source_sha256'].lower():
            raise ValueError('Proxy build identity differs')
        exe,built=matrix.stage_candidate(args.profile,args.resolution,reference,out)
        if args.native_present_bounds:
            exe,built=stage_present_override(reference/'clash95.exe',args.profile,args.resolution,out,exe,built)
        report.update(built=built,proxy_build=build,executed_stage=built['stage'],executed_revision=built['recipe_revision'])
        with patch.object(matrix.runtime,'HARNESS',observation_source(matrix.runtime.HARNESS)):
            engine=matrix.runtime.compile_harness(out)
        report['engine_sha256']=matrix.digest(engine)
        shutil.copytree(reference,work)
        for name in manifest['runtime']['empty_directories']:
            directory=(work/name).resolve()
            if not directory.is_relative_to(work):raise ValueError('Escaping runtime directory')
            directory.mkdir(parents=True,exist_ok=True)
        target=work/exe.name
        if target.exists():raise ValueError('Candidate collides with original')
        shutil.copy2(exe,target);shutil.copy2(proxy,work/'ddraw.dll')
        width,height=map(int,args.resolution.split('x'))
        display=matrix.RunnerDisplay(min(width,1920),min(height,1080))
        with display as configuration,logpath.open('w',encoding='utf-8') as log:
            report['display']=configuration
            begin=time.monotonic()
            proc=subprocess.Popen([str(engine),str(target),str(capture),'110','proxy'],cwd=work,
                env=dict(os.environ,CLASH_PROXY_PRESENT='1',_NT_SYMBOL_PATH='.',_NT_ALT_SYMBOL_PATH=''),stdout=log,stderr=subprocess.STDOUT)
            while time.monotonic()-begin<35 and proc.poll() is None and not (capture/'primary-00.json').exists():time.sleep(.15)
            if not (capture/'primary-00.json').is_file():raise ValueError('No initial primary sample')
            import re
            text=logpath.read_text(encoding='utf-8',errors='replace')
            records=re.findall(r'^REAL_LOADED pid=(\d+) base=00400000 entry=[0-9a-f]+ executable_sections_match=1$',text,re.M)
            if len(records)!=1 or 'REAL_EXE_ENTRY observed=1' not in text:raise ValueError('No authenticated game entry')
            pid=int(records[0]);kernel,user,_=owned.win32()
            handle=owned.require(kernel.OpenProcess(0x1000|0x100000,False,pid),'Retain owned input target')
            identity=owned.process_identity(kernel,handle)
            if Path(identity['path']).resolve()!=target:raise ValueError('Input image path differs')
            report['owner']=dict(identity,pid=pid)
            report['client']=prepare_client(user,pid,width,height)
            image,_=indexed_image(capture/'primary-00.json');report['menu']=menu_identity(image)
            if not report['menu']['matches_original']:raise ValueError('Native menu pixels differ from original; input not attempted')
            def wait_until(seconds):
                while time.monotonic()<begin+seconds:
                    if proc.poll() is not None:raise RuntimeError('Observation host exited before input phase')
                    time.sleep(.1)
            def click(name,points,phase):
                if kernel.WaitForSingleObject(handle,0)!=258 or owned.process_identity(kernel,handle)['creation_filetime']!=identity['creation_filetime']:
                    raise ValueError('Input owner exited or changed')
                destination=out/(name+'.json')
                command=[sys.executable,str(root/'tools/runner_menu_input.py'),'--allow-foreground-attach','--engine-coordinate-feedback',
                    '--approval-text',args.approval_text,'--owner-creation',str(identity['creation_filetime']),
                    '--pid',str(pid),'--resolution',args.resolution,phase,points,'--click-repeats','1',
                    '--click-hold-ms','400','--point-settle-ms','1800','--deadline-sec','20','--map-nonblack','0',
                    '--final-settle-ms','1200','--aim-tolerance','4','--json',str(destination)]
                result=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,errors='replace',timeout=30)
                (out/(name+'.log')).write_text(result.stdout,encoding='utf-8')
                data=json.loads(destination.read_text()) if destination.is_file() else {}
                row=dict(name=name,elapsed_seconds=round(time.monotonic()-begin,3),returncode=result.returncode,
                         passed=result.returncode==0 and input_success(data),result=data)
                report['actions'].append(row)
                return row['passed']
            wait_until(12)
            ox,oy=(width-640)//2,(height-480)//2
            if not click('campaign',f'campaign:{224+ox},{185+oy};first-campaign:{225+ox},{305+oy}','--steps'):
                raise ValueError('Campaign input did not complete')
            report['ordinary_input_pending'] = 'Foreground campaign diagnostic has no native action-boundary transport; fixed map clicks are disabled'
            proc.wait(timeout=max(1,begin+170-time.monotonic()))
        report['display']=display.report
    except Exception as error:
        report['errors'].append(f'{type(error).__name__}: {error}')
    finally:
        if proc is not None and proc.poll() is None:
            try:proc.wait(timeout=125)
            except subprocess.TimeoutExpired:proc.kill();proc.wait(timeout=10);report['errors'].append('Observation host exceeded deadline')
        if handle and kernel:
            report['retained_process_exited']=kernel.WaitForSingleObject(handle,5000)==0
            kernel.CloseHandle(handle)
        if logpath.exists():
            report['outcome']=full_observation(logpath.read_text(encoding='utf-8',errors='replace'),proc.returncode if proc else -1)
        try:
            report['snapshots']=matrix.runtime.render(capture)
            report['states']=[dict(sample=p.name,**json.loads(p.read_text())) for p in sorted(capture.glob('map-state-*.json'))]
            if report['snapshots']:report['map_pixels']=validate_map_pixels(capture,reference,args.profile,args.resolution)
        except Exception as error:report['errors'].append('Capture audit: '+str(error))
        try:
            report['reference_unchanged']=baseline is not None and matrix.runtime.verify(reference,manifest)==baseline
            report['candidate_unchanged']=matrix.digest(target)==built['candidate_sha256']==matrix.digest(exe)
            sources=built['launcher_build'].get('source_sha256')
            if isinstance(sources,dict):matrix.runtime.verify_hd_sources({'source_hashes':sources},root)
            report['working_original_unchanged']=matrix.digest(work/'clash95.exe')==matrix.runtime.ORIGINAL_SHA256
        except Exception as error:report['errors'].append('Identity audit: '+str(error))
        report['menu_and_campaign_input_passed']=not report['errors'] and report.get('menu',{}).get('matches_original') is True and all(
            a['passed'] for a in report['actions'] if a['name']=='campaign') and any(a['name']=='campaign' for a in report['actions'])
        report['unit_selected_observed']=False  # Legacy scalar samples cannot prove an action's exact transition.
        report['native_input_passed']=False  # Cursor/OS-delivery receipts do not prove native map input.
        report['map_controls_pixels_passed']=map_controls_passed(report.get('map_pixels',[]))
        report['source_commit']=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
        report['source_hashes']={name:matrix.digest(root/name) for name in ('tools/resolution_playability.py','tools/launcher_resolution_matrix.py','tools/real_exe_smoke.py','tools/runner_menu_input.py','tools/menu_pulse_click.py','src/launcher/resolutions.json')}
        (out/'playability.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return report


def prepared_candidate(path: Path, case: dict) -> tuple[Path, dict]:
    """Reuse only an intact, current source-bound launcher build receipt."""
    receipt=json.loads(path.read_text(encoding='utf-8-sig'))
    if not isinstance(receipt,dict) or set(receipt)!={'path','built'}:
        raise ValueError('Exact prepared launcher receipt required')
    exe=Path(receipt['path']).resolve();built=receipt['built']
    if any(built.get(k)!=v for k,v in case.items()):
        raise ValueError('Prepared build differs from the current launcher case')
    build=built['launcher_build'];expected=built['candidate_sha256']
    if (build.get('base_sha256')!=matrix.runtime.ORIGINAL_SHA256 or
            build.get('output_sha256')!=expected or matrix.digest(exe)!=expected):
        raise ValueError('Prepared executable or original identity differs')
    for key in ('profile','resolution','stage','recipe_revision'):
        if build['display_plan'].get(key if key!='profile' else 'renderer')!=case[key]:
            raise ValueError('Prepared display plan differs: '+key)
    metadata_path=Path(build['candidate_manifest']['path']).resolve()
    if (metadata_path!=exe.with_suffix('.candidate.json') or
            matrix.digest(metadata_path)!=build['candidate_manifest']['sha256']):
        raise ValueError('Prepared candidate manifest differs')
    metadata=json.loads(metadata_path.read_text(encoding='utf-8'))
    original_field,schema=('base_sha256',1) if case['profile']=='completehd' else (
        'original_sha256','clash95_framed_modal_widgets_candidate_v1')
    if (metadata.get('schema')!=schema or metadata.get(original_field)!=matrix.runtime.ORIGINAL_SHA256 or
            metadata.get('candidate_sha256')!=expected or
            any(metadata.get(k)!=case[k] for k in ('stage','resolution','recipe_revision')) or
            metadata.get('source_hashes')!=build.get('source_sha256')):
        raise ValueError('Prepared metadata or source inventory differs')
    matrix.runtime.verify_hd_sources(metadata,matrix.ROOT)
    artifacts=build.get('artifact_sha256')
    if not isinstance(artifacts,dict) or set(artifacts)!={exe.name,metadata_path.name,exe.with_suffix('.cdb').name}:
        raise ValueError('Prepared artifact inventory differs')
    for name,digest in artifacts.items():
        if matrix.digest(exe.parent/name)!=digest:
            raise ValueError('Prepared artifact changed: '+name)
    return exe,built


PREPARED_MATRIX_SCHEMA='clash95_prepared_ordinary_castle_entry_matrix_v1'
PREPARED_SMALL_WORLD_SCHEMA='clash95_prepared_complete_small_world_v1'
MATRIX_BUNDLE_MAX_BYTES=64*1024**2
SMALL_WORLD_PRODUCER='tools/build_complete_small_world_candidate.py'
SMALL_WORLD_SCOPES=dict(validation_stage_only=True,installation_ready=False,
    runtime_executed=False,manual_input_proof=False,promotion_ready=False,
    bounded_small_world_integrated=True,small_world_input_enabled=True,
    camera_clamp=True,predecessor_probe_reusable=False)


def matrix_candidate_case(profile: str, resolution: str) -> dict:
    from src.patcher import ordinary_castle_entry_matrix as builder
    if profile not in builder.PROFILES or resolution not in builder.RESOLUTIONS:
        raise ValueError('Prepared matrix requires a supported complete profile and six-resolution case')
    return dict(schema=builder.SCHEMA,profile=profile,resolution=resolution,
                stage=builder.stage(profile),recipe_revision=builder.REVISION)


def small_world_candidate_case(profile: str, resolution: str) -> dict:
    from src.patcher import complete_small_world_candidate as builder
    if profile not in builder.PROFILES or resolution not in builder.RESOLUTIONS:
        raise ValueError('Prepared small-world requires a supported complete profile and six-resolution case')
    return dict(schema=builder.SCHEMA,profile=profile,resolution=resolution,
                stage=builder.stage(profile),recipe_revision=builder.REVISION)


def candidate_case(args) -> dict:
    if getattr(args,'prepared_small_world_candidate',None) is not None:
        if (args.mode!='hidden-controlled' or getattr(args,'prepared_build',None) is not None
                or getattr(args,'prepared_matrix_candidate',None) is not None
                or getattr(args,'native_present_bounds',False)):
            raise ValueError('Prepared small-world requires hidden-controlled mode without another prepared candidate or presentation override')
        return small_world_candidate_case(args.profile,args.resolution)
    if getattr(args,'prepared_matrix_candidate',None) is not None:
        if (args.mode!='hidden-controlled' or getattr(args,'prepared_build',None) is not None
                or getattr(args,'native_present_bounds',False)):
            raise ValueError('Prepared matrix requires hidden-controlled mode without launcher receipt or presentation override')
        return matrix_candidate_case(args.profile,args.resolution)
    return matrix.select_case(args.profile,args.resolution)


def _matrix_plain_path(path: Path) -> Path:
    raw=Path(path).absolute()
    for item in (raw,*raw.parents):
        if (item.is_symlink() or getattr(item,'is_junction',lambda:False)()
                or (item.exists() and getattr(item.stat(),'st_file_attributes',0)&0x400)):
            raise ValueError('Prepared matrix path follows a link, junction or reparse point')
    return raw.resolve()


def _matrix_bytes(path: Path) -> bytes:
    path=_matrix_plain_path(path)
    if not path.is_file() or not 0<path.stat().st_size<=MATRIX_BUNDLE_MAX_BYTES:
        raise ValueError('Prepared matrix requires a nonempty bounded regular file: '+str(path))
    data=path.read_bytes()
    if not 0<len(data)<=MATRIX_BUNDLE_MAX_BYTES:
        raise ValueError('Prepared matrix file size changed: '+str(path))
    return data


def _matrix_unique_object(pairs):
    value={}
    for key,item in pairs:
        if key in value:raise ValueError('Duplicate prepared matrix JSON field: '+key)
        value[key]=item
    return value


def _matrix_sources(metadata: dict) -> None:
    matrix.runtime.verify_hd_sources(metadata,matrix.ROOT)
    for name in metadata['source_hashes']:
        _matrix_plain_path(matrix.ROOT/name)


def prepared_matrix_candidate(exe: Path, *, original: Path, profile: str,
                              resolution: str) -> tuple[Path, dict]:
    """Authenticate one distinct source-built matrix bundle; never write or launch."""
    from src.patcher import ordinary_castle_entry_matrix as builder
    case=matrix_candidate_case(profile,resolution)
    exe=_matrix_plain_path(exe);original=_matrix_plain_path(original)
    if (exe.suffix.lower()!='.exe' or exe.is_relative_to(matrix.ROOT.resolve())
            or exe.is_relative_to(original.parent)):
        raise ValueError('Prepared matrix executable must be external to repository and original assets')
    paths=(exe,exe.with_suffix('.candidate.json'),exe.with_suffix('.cdb'))
    before={path:_matrix_bytes(path) for path in paths}
    original_bytes=_matrix_bytes(original)
    if hashlib.sha256(original_bytes).hexdigest()!=builder.pe.ORIGINAL_SHA256:
        raise ValueError('Prepared matrix original executable identity differs')
    metadata=json.loads(before[paths[1]].decode('utf-8'),object_pairs_hook=_matrix_unique_object)
    if (type(metadata) is not dict or any(type(metadata.get(k)) is not type(v) or metadata.get(k)!=v
            for k,v in case.items()) or metadata.get('original_sha256')!=builder.pe.ORIGINAL_SHA256):
        raise ValueError('Prepared matrix schema, recipe, case or original identity differs')
    scopes=dict(validation_stage_only=True,runtime_executed=False,manual_input_proof=False,
                promotion_ready=False,bounded_small_world_integrated=False,predecessor_probe_reusable=False)
    if any(metadata.get(k) is not v for k,v in scopes.items()):
        raise ValueError('Prepared matrix source-only evidence scope differs')
    producer='tools/build_ordinary_castle_entry_matrix_candidate.py'
    sources=metadata.get('source_hashes')
    if type(sources) is not dict or not {builder.SOURCE,producer}<=sources.keys():
        raise ValueError('Prepared matrix source and CLI producer identities required')
    _matrix_sources(metadata)
    producer_before=matrix.digest(matrix.ROOT/producer)
    image,expected,probe=builder.build_candidate(original_bytes,profile,resolution)
    expected=dict(expected,source_hashes=dict(expected['source_hashes']))
    expected['source_hashes'][producer]=producer_before
    if (any(type(expected.get(k)) is not type(v) or expected.get(k)!=v for k,v in case.items())
            or expected.get('original_sha256')!=builder.pe.ORIGINAL_SHA256
            or any(expected.get(k) is not v for k,v in scopes.items())
            or hashlib.sha256(image).hexdigest()!=expected.get('candidate_sha256')
            or hashlib.sha256(probe.encode()).hexdigest()!=expected.get('probe_sha256')):
        raise ValueError('Reconstructed matrix builder identity differs')
    if (before[exe]!=image or before[paths[1]]!=(json.dumps(expected,indent=2)+'\n').encode()
            or before[paths[2]]!=probe.encode()):
        raise ValueError('Prepared matrix executable, complete metadata or CRLF probe differs from source reconstruction')
    _matrix_sources(expected)
    if (_matrix_bytes(original)!=original_bytes or matrix.digest(matrix.ROOT/producer)!=producer_before
            or any(_matrix_plain_path(path)!=path or _matrix_bytes(path)!=data for path,data in before.items())):
        raise ValueError('Prepared matrix original, producer or bundle changed during authentication')
    provenance=dict(schema=PREPARED_MATRIX_SCHEMA,candidate_schema=case['schema'],
        **{key:case[key] for key in ('profile','resolution','stage','recipe_revision')},
        candidate_sha256=expected['candidate_sha256'],original_sha256=builder.pe.ORIGINAL_SHA256,
        candidate_manifest=dict(path=str(paths[1]),sha256=hashlib.sha256(before[paths[1]]).hexdigest()),
        probe=dict(path=str(paths[2]),sha256=expected['probe_sha256']),
        artifact_sha256={path.name:hashlib.sha256(data).hexdigest() for path,data in before.items()},
        source_sha256=dict(expected['source_hashes']),authentication_scope='Exact source reconstruction and bundle bytes only',
        probe_executed=False,runtime_executed=False,manual_input_proof=False,promotion_ready=False)
    return exe,dict(case,candidate_sha256=expected['candidate_sha256'],prepared_matrix=provenance)


def _prepared_file_snapshot(path: Path) -> tuple[bytes,dict]:
    """Read one bounded plain file without accepting replacement during read."""
    path=_matrix_plain_path(path)
    def identity():
        info=path.stat(follow_symlinks=False)
        if not stat.S_ISREG(info.st_mode):raise ValueError('Prepared candidate requires a regular file')
        return dict(device=info.st_dev,inode=info.st_ino,size=info.st_size,mtime_ns=info.st_mtime_ns)
    before=identity();data=_matrix_bytes(path)
    if identity()!=before or _matrix_plain_path(path)!=path:
        raise ValueError('Prepared candidate file changed while reading: '+str(path))
    return data,before


def _small_world_sources(metadata: dict) -> dict:
    _matrix_sources(metadata)
    identities={}
    for name,digest in metadata['source_hashes'].items():
        data,identity=_prepared_file_snapshot(matrix.ROOT/name)
        if hashlib.sha256(data).hexdigest()!=digest:
            raise ValueError('Prepared small-world source changed while reading: '+name)
        identities[name]=identity
    return identities


def prepared_small_world_candidate(exe: Path, *, original: Path, profile: str,
                                   resolution: str) -> tuple[Path,dict]:
    """Bind the distinct successor to one source reconstruction; no file writes."""
    from src.patcher import complete_small_world_candidate as builder
    case=small_world_candidate_case(profile,resolution)
    exe=_matrix_plain_path(exe);original=_matrix_plain_path(original)
    if (exe.suffix.lower()!='.exe' or exe.is_relative_to(matrix.ROOT.resolve())
            or exe.is_relative_to(original.parent)):
        raise ValueError('Prepared small-world executable must be external to repository and original assets')
    paths=(exe,exe.with_suffix('.candidate.json'),exe.with_suffix('.cdb'))
    before={path:_prepared_file_snapshot(path) for path in paths}
    original_bytes,original_identity=_prepared_file_snapshot(original)
    if hashlib.sha256(original_bytes).hexdigest()!=builder.pe.ORIGINAL_SHA256:
        raise ValueError('Prepared small-world original executable identity differs')
    metadata=json.loads(before[paths[1]][0].decode('utf-8'),object_pairs_hook=_matrix_unique_object)
    if (type(metadata) is not dict or any(type(metadata.get(k)) is not type(v) or metadata.get(k)!=v
            for k,v in case.items()) or metadata.get('original_sha256')!=builder.pe.ORIGINAL_SHA256):
        raise ValueError('Prepared small-world schema, recipe, case or original identity differs')
    if any(metadata.get(k) is not v for k,v in SMALL_WORLD_SCOPES.items()):
        raise ValueError('Prepared small-world source-only evidence scope differs')
    sources=metadata.get('source_hashes')
    if type(sources) is not dict or not {builder.SOURCE,SMALL_WORLD_PRODUCER}<=sources.keys():
        raise ValueError('Prepared small-world source and CLI producer identities required')
    source_before=_small_world_sources(metadata)
    producer_before=sources[SMALL_WORLD_PRODUCER]
    image,expected,probe=builder.build_candidate(original_bytes,profile,resolution)
    if type(expected) is not dict or type(expected.get('source_hashes')) is not dict or type(image) is not bytes or type(probe) is not str:
        raise ValueError('Reconstructed small-world builder result differs')
    expected=dict(expected,source_hashes=dict(expected['source_hashes']))
    expected['source_hashes'][SMALL_WORLD_PRODUCER]=producer_before
    if (any(type(expected.get(k)) is not type(v) or expected.get(k)!=v for k,v in case.items())
            or expected.get('original_sha256')!=builder.pe.ORIGINAL_SHA256
            or any(expected.get(k) is not v for k,v in SMALL_WORLD_SCOPES.items())
            or hashlib.sha256(image).hexdigest()!=expected.get('candidate_sha256')
            or hashlib.sha256(probe.encode('ascii')).hexdigest()!=expected.get('probe_sha256')
            or not probe.endswith('\r\n') or any(ch in probe.replace('\r\n','') for ch in '\r\n')):
        raise ValueError('Reconstructed small-world builder identity differs')
    if (before[exe][0]!=image or before[paths[1]][0]!=(json.dumps(expected,indent=2)+'\n').encode('utf-8')
            or before[paths[2]][0]!=probe.encode('ascii')):
        raise ValueError('Prepared small-world executable, complete metadata or CRLF probe differs from source reconstruction')
    if (_small_world_sources(expected)!=source_before or _prepared_file_snapshot(original)!=(original_bytes,original_identity)
            or any(_matrix_plain_path(path)!=path or _prepared_file_snapshot(path)!=snapshot for path,snapshot in before.items())):
        raise ValueError('Prepared small-world original, sources or bundle changed during authentication')
    provenance=dict(schema=PREPARED_SMALL_WORLD_SCHEMA,candidate_schema=case['schema'],
        **{key:case[key] for key in ('profile','resolution','stage','recipe_revision')},
        candidate_sha256=expected['candidate_sha256'],original_sha256=builder.pe.ORIGINAL_SHA256,
        original=dict(path=str(original),sha256=builder.pe.ORIGINAL_SHA256,identity=original_identity),
        candidate_manifest=dict(path=str(paths[1]),sha256=hashlib.sha256(before[paths[1]][0]).hexdigest()),
        probe=dict(path=str(paths[2]),sha256=expected['probe_sha256']),
        artifact_sha256={path.name:hashlib.sha256(snapshot[0]).hexdigest() for path,snapshot in before.items()},
        artifact_identity={path.name:snapshot[1] for path,snapshot in before.items()},
        source_sha256=dict(expected['source_hashes']),source_identity=source_before,
        authentication_scope='Exact source reconstruction and bundle bytes only',
        probe_executed=False,runtime_executed=False,manual_input_proof=False,promotion_ready=False)
    return exe,dict(case,candidate_sha256=expected['candidate_sha256'],prepared_small_world=provenance)


def _candidate_origins(built: dict) -> None:
    if sum(key in built for key in ('launcher_build','prepared_matrix','prepared_small_world'))>1:
        raise ValueError('Ambiguous prepared candidate provenance')


def candidate_sources(built: dict) -> dict:
    _candidate_origins(built)
    if 'prepared_small_world' in built:
        provenance=built['prepared_small_world']
        if type(provenance) is not dict or provenance.get('schema')!=PREPARED_SMALL_WORLD_SCHEMA:
            raise ValueError('Prepared small-world provenance schema differs')
        if (provenance.get('candidate_schema')!=built.get('schema')
                or any(type(provenance.get(k)) is not type(built.get(k)) or provenance.get(k)!=built.get(k)
                       for k in ('profile','resolution','stage','recipe_revision','candidate_sha256'))
                or any(provenance.get(k) is not False for k in ('probe_executed','runtime_executed','manual_input_proof','promotion_ready'))
                or type(provenance.get('source_sha256')) is not dict):
            raise ValueError('Prepared small-world provenance and candidate context differ')
        return provenance['source_sha256']
    if 'prepared_matrix' in built:
        provenance=built['prepared_matrix']
        if ('launcher_build' in built or type(provenance) is not dict
                or provenance.get('schema')!=PREPARED_MATRIX_SCHEMA):
            raise ValueError('Ambiguous prepared matrix provenance')
        if (provenance.get('candidate_schema')!=built.get('schema')
                or any(type(provenance.get(k)) is not type(built.get(k)) or provenance.get(k)!=built.get(k)
                       for k in ('profile','resolution','stage','recipe_revision','candidate_sha256'))):
            raise ValueError('Prepared matrix provenance and candidate context differ')
        return provenance['source_sha256']
    return built['launcher_build']['source_sha256']


def candidate_context(built: dict) -> dict:
    import ordinary_map_input_plan as planner
    _candidate_origins(built)
    if 'prepared_small_world' in built:
        case=small_world_candidate_case(built['profile'],built['resolution'])
        if any(type(built.get(k)) is not type(v) or built.get(k)!=v for k,v in case.items()):
            raise ValueError('Prepared small-world context identity differs')
        candidate_sources(built)
    elif 'prepared_matrix' in built:
        case=matrix_candidate_case(built['profile'],built['resolution'])
        if any(type(built.get(k)) is not type(v) or built.get(k)!=v for k,v in case.items()):
            raise ValueError('Prepared matrix context identity differs')
        candidate_sources(built)
    context=dict(schema=planner.CANDIDATE_SCHEMA,sha256=built['candidate_sha256'],stage=built['stage'],
                 profile=built['profile'],resolution=built['resolution'],layout=planner.LAYOUT)
    planner.candidate_contract(context)
    return context


def audit_prepared_matrix(exe: Path, built: dict) -> None:
    provenance=built['prepared_matrix'];candidate_sources(built)
    paths=(exe,exe.with_suffix('.candidate.json'),exe.with_suffix('.cdb'))
    if (provenance['candidate_manifest']['path']!=str(paths[1]) or provenance['probe']['path']!=str(paths[2])
            or set(provenance['artifact_sha256'])!={path.name for path in paths}
            or provenance['artifact_sha256'].get(exe.name)!=built['candidate_sha256']
            or provenance['candidate_manifest']['sha256']!=provenance['artifact_sha256'].get(paths[1].name)
            or provenance['probe']['sha256']!=provenance['artifact_sha256'].get(paths[2].name)
            or any(hashlib.sha256(_matrix_bytes(path)).hexdigest()!=provenance['artifact_sha256'][path.name]
                   for path in paths)):
        raise ValueError('Prepared matrix bundle changed after authentication')
    _matrix_sources({'source_hashes':candidate_sources(built)})


def audit_prepared_small_world(exe: Path, built: dict) -> None:
    candidate_context(built);provenance=built['prepared_small_world']
    paths=(exe,exe.with_suffix('.candidate.json'),exe.with_suffix('.cdb'))
    if (provenance['candidate_manifest']['path']!=str(paths[1]) or provenance['probe']['path']!=str(paths[2])
            or set(provenance['artifact_sha256'])!={path.name for path in paths}
            or set(provenance['artifact_identity'])!={path.name for path in paths}
            or provenance['artifact_sha256'].get(exe.name)!=built['candidate_sha256']
            or provenance['candidate_manifest']['sha256']!=provenance['artifact_sha256'].get(paths[1].name)
            or provenance['probe']['sha256']!=provenance['artifact_sha256'].get(paths[2].name)):
        raise ValueError('Prepared small-world artifact provenance differs')
    snapshots={path:_prepared_file_snapshot(path) for path in paths}
    if any(hashlib.sha256(snapshot[0]).hexdigest()!=provenance['artifact_sha256'][path.name]
           or snapshot[1]!=provenance['artifact_identity'][path.name] for path,snapshot in snapshots.items()):
        raise ValueError('Prepared small-world bundle changed after authentication')
    metadata=json.loads(snapshots[paths[1]][0].decode('utf-8'),object_pairs_hook=_matrix_unique_object)
    case=small_world_candidate_case(built['profile'],built['resolution'])
    if (type(metadata) is not dict or any(type(metadata.get(k)) is not type(v) or metadata.get(k)!=v for k,v in case.items())
            or metadata.get('candidate_sha256')!=built['candidate_sha256']
            or metadata.get('probe_sha256')!=provenance['probe']['sha256']
            or any(metadata.get(k) is not v for k,v in SMALL_WORLD_SCOPES.items())
            or metadata.get('source_hashes')!=candidate_sources(built)):
        raise ValueError('Prepared small-world metadata or source provenance differs from retained manifest')
    if _small_world_sources(metadata)!=provenance['source_identity']:
        raise ValueError('Prepared small-world source identity changed after authentication')
    original=provenance['original'];data,identity=_prepared_file_snapshot(Path(original['path']))
    if (original['sha256']!=metadata['original_sha256'] or original['sha256']!=provenance['original_sha256']
            or hashlib.sha256(data).hexdigest()!=original['sha256'] or identity!=original['identity']):
        raise ValueError('Prepared small-world original changed after authentication')


def native_phase_source(width: int, height: int) -> str:
    import ordinary_map_startup as startup
    import ordinary_map_pause_host as pause
    import ordinary_map_phase_host as phase
    import ordinary_map_activation_host as activation
    return activation.render_source(phase.render_source(pause.render_source(
        startup.render_source(observation_source(matrix.runtime.HARNESS),width,height))))


RAW_OBSERVATION_ALLOWANCE = 32 * 1024**2
RAW_OBSERVATION_SCRATCH = (128 + 32) * 1024**2


def raw_observation_context(exe: Path, built: dict) -> dict:
    """Bind a canonical sidecar to the already authenticated candidate bundle."""
    import ordinary_map_read_replay as raw
    if 'launcher_build' in built or not any(key in built for key in ('prepared_matrix','prepared_small_world')):
        raise ValueError('Raw observations require an independently reconstructed prepared matrix or small-world bundle')
    root=matrix.ROOT.resolve()
    if (raw.ROOT.resolve()!=root or Path(__file__).resolve()!=root/'tools/resolution_playability.py'):
        raise ValueError('Raw observation helpers must come from the calling checkout')
    candidate=candidate_context(built)
    sources=deepcopy(candidate_sources(built))
    matrix.runtime.verify_hd_sources({'source_hashes':sources},root)
    provenance=built.get('prepared_small_world',built.get('prepared_matrix',built.get('launcher_build')))
    paths=(exe,exe.with_suffix('.candidate.json'),exe.with_suffix('.cdb'))
    if (type(provenance) is not dict or type(provenance.get('artifact_sha256')) is not dict
            or set(provenance['artifact_sha256'])!={path.name for path in paths}
            or provenance.get('candidate_manifest',{}).get('path')!=str(paths[1].resolve())):
        raise ValueError('Raw observation requires the exact candidate bundle provenance')
    snapshots={path:_prepared_file_snapshot(path) for path in paths}
    artifacts={str(path.resolve()):dict(sha256=hashlib.sha256(data).hexdigest(),identity=identity)
               for path,(data,identity) in snapshots.items()}
    if (any(artifacts[str(path.resolve())]['sha256']!=provenance['artifact_sha256'][path.name] for path in paths)
            or artifacts[str(exe.resolve())]['sha256']!=candidate['sha256']
            or artifacts[str(paths[1].resolve())]['sha256']!=provenance['candidate_manifest'].get('sha256')):
        raise ValueError('Raw observation candidate bundle differs from its authenticated provenance')
    metadata=json.loads(snapshots[paths[1]][0].decode('utf-8'),object_pairs_hook=_matrix_unique_object)
    probe_sha=artifacts[str(paths[2].resolve())]['sha256']
    if (type(metadata) is not dict or metadata.get('candidate_sha256')!=candidate['sha256']
            or any(type(metadata.get(name)) is not type(built[name]) or metadata.get(name)!=built[name]
                   for name in ('stage','resolution','recipe_revision'))
            or not raw.same(metadata.get('source_hashes'),sources) or metadata.get('probe_sha256')!=probe_sha
            or ('probe' in provenance and (provenance['probe'].get('path')!=str(paths[2].resolve())
                                          or provenance['probe'].get('sha256')!=probe_sha))):
        raise ValueError('Raw observation canonical probe or metadata binding differs')
    try:snapshots[paths[2]][0].decode('ascii')
    except UnicodeError as error:raise ValueError('Raw observation canonical probe must be ASCII') from error
    context=dict(candidate=candidate,canonical_probe_sha256=probe_sha,
                 source_hashes=raw.current_source_hashes(),candidate_sources=sources,artifacts=artifacts)
    audit_raw_observation_context(context)
    return context


def audit_raw_observation_context(context: dict) -> None:
    import ordinary_map_read_replay as raw
    if raw.ROOT.resolve()!=matrix.ROOT.resolve() or not raw.same(context['source_hashes'],raw.current_source_hashes()):
        raise ValueError('Frozen raw observation source snapshot differs')
    matrix.runtime.verify_hd_sources({'source_hashes':context['candidate_sources']},matrix.ROOT)
    for name,expected in context['artifacts'].items():
        data,identity=_prepared_file_snapshot(Path(name))
        if not raw.same(identity,expected['identity']) or hashlib.sha256(data).hexdigest()!=expected['sha256']:
            raise ValueError('Raw observation candidate/probe artifact changed: '+name)


def _atomic_raw_bytes(directory: Path, name: str, data: bytes) -> None:
    """Publish one immutable file exclusively; failed write remnants are retained."""
    import ordinary_map_read_replay as raw
    if type(data) is not bytes or not 0<len(data)<=raw.MAX_CAPTURE_BYTES or not re.fullmatch(r'[a-z-]+\.json',name):
        raise ValueError('Bounded canonical raw artifact required')
    directory=_matrix_plain_path(directory)
    destination=directory/name
    if destination.exists() or destination.is_symlink():raise ValueError('Raw artifact collision: '+str(destination))
    require_hidden_disk_reserve(matrix.ROOT,directory,scratch_bytes=RAW_OBSERVATION_SCRATCH,
                                phase='before-raw-retention-write')
    temporary=directory/('.pending-'+uuid.uuid4().hex)
    with temporary.open('xb') as stream:
        stream.write(data);stream.flush();os.fsync(stream.fileno())
    # link is an exclusive atomic publish on both supported source-test hosts.
    # The successful temporary is then removed, leaving one retained file link.
    os.link(temporary,destination,follow_symlinks=False)
    temporary.unlink()
    saved,identity=_prepared_file_snapshot(destination)
    if saved!=data or destination.stat().st_nlink!=1:
        raise ValueError('Raw artifact changed during retention')


def retain_raw_observation(out: Path, name: str, context: dict, binding: dict,
                           report: dict, *, captured=None, partial=None, error='') -> dict:
    """Commit a separate index last; partial reads never become successful proof."""
    import ordinary_map_read_replay as raw
    if (captured is None)==(partial is None) or not re.fullmatch('map-(before-plan|(?:before|after)-(select|move))',name):
        raise ValueError('Exact complete or partial raw observation required')
    out=_matrix_plain_path(out)
    if not out.is_dir() or out.is_relative_to(matrix.ROOT.resolve()) or matrix.ROOT.resolve().is_relative_to(out):
        raise ValueError('Raw observation output must remain external to source control')
    complete=captured is not None
    raw_value=captured['raw_capture'] if complete else partial
    files={'raw.json':raw.canonical_bytes(raw_value)}
    hashes={name:hashlib.sha256(data).hexdigest() for name,data in files.items()}
    if complete:
        files['observation.json']=raw.canonical_bytes(captured['observation'])
        hashes['observation.json']=hashlib.sha256(files['observation.json']).hexdigest()
        replay=raw.replay_observation(raw.decode_capture(files['raw.json']),
            raw.decode_capture(files['observation.json']),expected_binding=binding,
            expected_capture_sha256=hashes['raw.json'],expected_observation_sha256=hashes['observation.json'])
    else:
        replay=dict(schema=raw.REPLAY_SCHEMA,passed=False,raw_replay_passed=False,
                    failures=[error or 'Partial recorded observation'],**{key:False for key in raw.FALSE_CLAIMS})
    files['replay.json']=raw.canonical_bytes(replay)
    index=dict(schema='clash95_ordinary_map_raw_index_v1',name=name,binding=deepcopy(binding),
        candidate_bundle=deepcopy(context),observation_complete=complete,
        artifacts={key:dict(sha256=hashlib.sha256(data).hexdigest(),bytes=len(data)) for key,data in files.items()},
        passed=False,**{key:False for key in raw.FALSE_CLAIMS})
    files['index.json']=raw.canonical_bytes(index)
    count=sum(len(data) for data in files.values())
    if (any(len(data)>raw.MAX_CAPTURE_BYTES for data in files.values())
            or report.get('raw_observation_bytes',0)+count>RAW_OBSERVATION_ALLOWANCE):
        raise ValueError('Raw observation retention exceeds its 32MiB allowance')
    require_hidden_disk_reserve(matrix.ROOT,out,scratch_bytes=RAW_OBSERVATION_SCRATCH,
                                phase='before-raw-retention-directory')
    root=out/'raw-observations'
    rows=report.setdefault('raw_observations',[])
    if not rows:root.mkdir(exist_ok=False)
    root=_matrix_plain_path(root);directory=root/name;directory.mkdir(exist_ok=False)
    row=dict(name=name,path=str(directory),index_committed=False,observation_complete=complete,
             raw_replay_passed=False,passed=False,**{key:False for key in raw.FALSE_CLAIMS})
    rows.append(row)
    for filename,data in files.items():_atomic_raw_bytes(directory,filename,data)
    row.update(index_committed=True,index_sha256=hashlib.sha256(files['index.json']).hexdigest(),
               artifacts=index['artifacts'],raw_replay_passed=replay['raw_replay_passed'])
    report['raw_observation_bytes']=report.get('raw_observation_bytes',0)+count
    return row


def measured_actions(peer, read_exact, candidate: dict, out: Path, report: dict, *, raw_context=None) -> None:
    """Read, revalidate and commit through the SAME held native input boundary."""
    import ordinary_map_observation as decoder
    import ordinary_map_input_plan as planner
    from ordinary_map_phase_client import verify_dispatch
    sequence=0;lease=None
    report['observations']=[];report['actions']=[]
    def observe(name, indices=None):
        nonlocal sequence
        sequence+=1
        if raw_context is None:
            value=decoder.observe(read_exact,candidate=candidate,identity=peer.identity,
                sequence=sequence,lease=lease,check_lease=peer.check_lease,stack_indices=indices)
        else:
            import ordinary_map_read_replay as raw
            phase=peer.ack()
            binding=dict(schema=raw.BINDING_SCHEMA,candidate=deepcopy(candidate),identity=deepcopy(peer.identity),
                sequence=sequence,lease=deepcopy(lease),phase=deepcopy(phase),
                canonical_probe_sha256=raw_context['canonical_probe_sha256'],
                source_hashes=deepcopy(raw_context['source_hashes']),
                requested_stack_indices=list(range(decoder.STACK_COUNT)) if indices is None else sorted(indices))
            captured=None
            try:
                if not raw.same(candidate,raw_context['candidate']):raise ValueError('Raw observation candidate context differs')
                audit_raw_observation_context(raw_context)
                raw.validate_binding(binding)
                captured=raw.capture_observation(read_exact,candidate=candidate,identity=peer.identity,
                    sequence=sequence,lease=lease,check_lease=peer.check_lease,stack_indices=indices,
                    phase=phase,canonical_probe_sha256=raw_context['canonical_probe_sha256'],
                    source_hashes=raw_context['source_hashes'])
                if not raw.same(phase,peer.ack()):raise ValueError('Held native phase changed during raw observation')
                audit_raw_observation_context(raw_context)
            except Exception as error:
                partial=getattr(error,'raw_diagnostics',None)
                if partial is None:
                    events=[] if captured is None else captured['raw_capture']['events']
                    partial=dict(schema=raw.PARTIAL_SCHEMA,binding=deepcopy(binding),events=deepcopy(events),
                                 observation_complete=False,**{key:False for key in raw.FALSE_CLAIMS})
                retain_raw_observation(out,name,raw_context,binding,report,partial=partial,error=str(error))
                raise
            row=retain_raw_observation(out,name,raw_context,binding,report,captured=captured)
            if not row['raw_replay_passed']:raise ValueError('Retained raw observation failed its independent replay')
            peer.check_lease(lease)
            value=captured['observation']
        value['native_phase']=peer.ack()
        destination=out/(name+'.json')
        destination.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
        report['observations'].append(dict(name=name,path=str(destination),sha256=matrix.digest(destination),
            capture_index=value['native_phase']['capture_index'],receipt=value['receipt']))
        print(json.dumps(dict(milestone=name,capture_index=value['native_phase']['capture_index'])),flush=True)
        return value['snapshot']
    try:
        lease=peer.acquire()
        initial=observe('map-before-plan')
        plan=planner.plan_input(initial,candidate)
        (out/'measured-plan.json').write_text(json.dumps(plan,indent=2)+'\n',encoding='utf-8')
        report['plan_sha256']=matrix.digest(out/'measured-plan.json')
        indices=tuple(s['index'] for s in plan['basis']['stacks'])
        for action in ('select','move'):
            before=observe('map-before-'+action,indices)
            validation=planner.revalidate_before_click(plan,before,action)
            held=peer.ack()
            binding=dict(plan_sha256=report['plan_sha256'],action=action,
                         validation=validation,held_phase=held)
            binding_sha256=planner.digest(binding)
            row=dict(name=action,passed=False,point=validation['point'],
                     binding=binding,binding_sha256=binding_sha256)
            report['actions'].append(row)
            lease=peer.click(lease,validation['point'],binding_sha256)
            row['dispatch_receipt']=peer.ack()
            after=observe('map-after-'+action,indices)
            row['native_dispatch']=verify_dispatch(row['dispatch_receipt'],peer.identity,binding_sha256)
            if action=='select' and after['context']['previous_stack']!=before['context']['selected_stack']:
                raise planner.PlanError('ordinary 4084A0 selection did not preserve the exact old selected index')
            verifier=planner.verify_selection if action=='select' else planner.verify_movement
            row['state_transition']=verifier(plan,before,after)
            row['passed']=True
        report['ordinary_controlled_input_passed']=True
    finally:
        # If click failed the old lease was consumed; never release or reuse it.
        if lease is not None and peer._active==lease and not peer._poisoned:
            try:report['phase_release']=peer.release(lease)
            except Exception as error:report['errors'].append('Phase release: '+str(error))
        report['phase_receipts']=peer.receipts


def mouse_poll_diagnostics(log: str, receipts: list[dict]) -> dict:
    """Bind read-only poll records to the already authenticated phase identity."""
    from ordinary_map_input_poll_trace import parse_trace
    if not receipts:
        raise ValueError('Mouse poll trace has no authenticated phase identity')
    ack=receipts[0]
    expected={name:ack[name] for name in ('pid','creation_filetime','image_base',
                                         'controller_sha256','session_id')}
    expected['tid']=ack['primary_tid']
    return parse_trace(log,expected)


def activation_trace_identity(ready: dict, *, phase_sha256: str, controller_sha256: str) -> dict:
    """Derive diagnostics from PhaseClient's authenticated initial ready receipt.

    The caller must first retain/authenticate the target and validate this ready
    receipt through PhaseClient. The activation observer has its own frozen
    controller digest; it must not inherit the phase controller's identity.
    """
    from ordinary_map_phase_client import SCHEMA, ACK_KEYS
    if (type(ready) is not dict or set(ready)!=ACK_KEYS or ready['schema']!=SCHEMA
            or ready['status']!='ready' or ready['phase']!='ready'
            or type(ready['request_seq']) is not int or ready['request_seq']!=0
            or ready['paused'] is not False or ready['lease_id']!=''
            or ready['deadline_tick_ms']!=0 or ready['controller_sha256']!=phase_sha256):
        raise ValueError('Activation trace requires an authenticated initial phase readiness receipt')
    if any(type(value) is not str or re.fullmatch('[0-9a-f]{64}',value) is None
           for value in (phase_sha256,controller_sha256)):
        raise ValueError('Activation trace requires frozen controller digests')
    identity={key:ready[key] for key in ('pid','creation_filetime','image_base','session_id')}
    identity.update(tid=ready['primary_tid'],controller_sha256=controller_sha256)
    return identity


def activation_diagnostics(log: str, identity: dict | None) -> dict:
    """Read-only observed-call diagnostics, independent of input acceptance."""
    from ordinary_map_activation_trace import parse_trace
    if identity is None:
        raise ValueError('Activation trace has no authenticated owned readiness identity')
    return parse_trace(log,identity)


def hidden_success(report: dict) -> bool:
    return (not report['errors'] and report.get('ordinary_controlled_input_passed') is True and
            [a.get('name') for a in report.get('actions',[])]==['select','move'] and
            all(a.get('passed') is True and a.get('native_dispatch',{}).get('passed') is True and
                a.get('state_transition',{}).get(key) is True for a,key in zip(report['actions'],
                    ('selection_state_transition','movement_state_transition'))) and
            report.get('outcome',{}).get('observation_complete') is True and
            all(report.get(k) is True for k in ('reference_unchanged','candidate_unchanged',
                'working_original_unchanged','retained_process_exited','sources_unchanged',
                'startup_retired_before_actions','map_controls_pixels_passed')) and
            all(report.get('host_cleanup',{}).get(k) is True for k in ('host_exited','job_empty','handles_closed')))


def require_hidden_disk_reserve(root, output_directory, *, runtime_bytes=0,
                                scratch_bytes=0, phase):
    """Check fresh checkout/output usage without caching or lowering reserves."""
    if any(type(value) is not int or value < 0 for value in (runtime_bytes,scratch_bytes)):
        raise ValueError(f'{phase}: invalid disk budget')
    checkout=shutil.disk_usage(root)
    output=shutil.disk_usage(output_directory)
    for label,path,usage,budget in (('checkout',root,checkout,0),
                                   ('output',output_directory,output,runtime_bytes+scratch_bytes)):
        if usage.free*10<=usage.total or (usage.free-budget)*10<=usage.total:
            raise ValueError(f'{phase}: {label} disk reserve failed for {path} '
                             f'(free={usage.free}, total={usage.total}, required_bytes={budget}; '
                             'more than ten-percent free required)')


def run_hidden(args) -> dict:
    import ordinary_map_input_plan as planner
    import ordinary_map_phase_host as phase_host
    from ordinary_map_phase_client import PhaseClient
    from ordinary_map_pause_client import RetainedTarget, prepare_control, checked_directory, unique_object
    from owned_hidden_process import OwnedHiddenProcess
    case=candidate_case(args)
    root=matrix.ROOT;reference=args.runtime.resolve();out=checked_directory(args.out)
    retain_raw=getattr(args,'retain_raw_observations',False)
    if type(retain_raw) is not bool:raise ValueError('Raw observation option must be boolean')
    if retain_raw and not any(getattr(args,key,None) is not None for key in
                              ('prepared_matrix_candidate','prepared_small_world_candidate')):
        raise ValueError('Raw observations require an independently reconstructed prepared matrix or small-world bundle')
    scratch_bytes=RAW_OBSERVATION_SCRATCH if retain_raw else 128*1024**2
    if os.name!='nt' or args.profile not in ('completehd','modalwidgets'):
        raise ValueError('Hidden native input requires Windows and a complete framed army profile')
    if args.native_present_bounds:
        raise ValueError('Hidden input uses the exact launcher candidate, without a presentation override')
    if out.exists() or not out.is_relative_to(Path('C:/ClashTests').resolve()) or any(
            out.is_relative_to(p) or p.is_relative_to(out) for p in (root,reference)):
        raise ValueError('New external candidate output required')
    if retain_raw:
        require_hidden_disk_reserve(root,out.parent,scratch_bytes=scratch_bytes,phase='before-output-directory')
    else:require_hidden_disk_reserve(root,out.parent,phase='before-output-directory')
    out.mkdir(parents=True);capture=out/'capture';capture.mkdir()
    report=dict(schema=2,mode='hidden-controlled',case=case,approval_text=args.approval_text,
        actions=[],errors=[],ordinary_controlled_input_passed=False,native_input_passed=False,
        os_input_executed=False,manual_input_proof=False,gameplay_verified=False,promotion_ready=False,
        proof_scope='controlled native ordinary handler with measured input fields; no OS or manual input',
        capture_scope='Private desktop and non-presenting proxy; paused software surface only',
        startup_scope='Bounded controlled native slot-zero loading; overrides retire at PlayGame before human input')
    source_names=('tools/resolution_playability.py','tools/launcher_resolution_matrix.py','tools/real_exe_smoke.py',
        'tools/run_original_game_smoke.py','tools/owned_hidden_process.py','tools/ordinary_map_startup.py',
        'tools/ordinary_map_phase_host.py','tools/ordinary_map_phase_client.py','tools/ordinary_map_input_poll_trace.py',
        'tools/ordinary_map_activation_host.py','tools/ordinary_map_activation_trace.py',
        'tools/ordinary_map_pause_host.py',
        'tools/ordinary_map_pause_client.py','tools/ordinary_map_observation.py','tools/ordinary_map_input_plan.py',
        'src/launcher/resolutions.json')
    if retain_raw:
        import ordinary_map_read_replay as raw
        if raw.ROOT.resolve()!=root.resolve():raise ValueError('Raw observer loaded from another checkout')
        source_names+=tuple(name for name in raw.SOURCE_PATHS if name not in source_names)
        report['raw_observation_retention_requested']=True
    report['source_hashes']={n:matrix.digest(root/n) for n in source_names}
    report['source_commit']=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
    source_copy=out/'source'
    for name,digest in report['source_hashes'].items():
        destination=source_copy/name;destination.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(root/name,destination)
        if matrix.digest(destination)!=digest:raise ValueError('Source changed before freezing: '+name)
    proc=retained=peer=None;baseline=manifest=built=exe=target=raw_context=None
    work=out/'work';logpath=capture/'debugger.log'
    try:
        manifest=json.loads(args.manifest.read_text(encoding='utf-8-sig'))
        baseline=owned.verify_assets(reference,manifest)
        runtime_bytes=sum(r['bytes'] for r in baseline.values())
        require_hidden_disk_reserve(root,out,runtime_bytes=runtime_bytes,scratch_bytes=scratch_bytes,
                                    phase='verified-runtime-assets')
        report['runtime_manifest_sha256']=matrix.digest(args.manifest)
        proxy=args.proxy.resolve()
        build=json.loads(proxy.with_name('ddraw_surfdump_proxy.build.json').read_text(encoding='utf-8-sig'))
        if (build.get('generated_by')!='clash-hd-surface-dump-proxy' or matrix.digest(proxy)!=build['output_sha256'].lower()
                or matrix.digest(root/'src/ddraw_surfdump_proxy/ddraw_surfdump_proxy.cpp')!=build['source_sha256'].lower()):
            raise ValueError('Proxy build identity differs')
        if getattr(args,'prepared_small_world_candidate',None) is not None:
            exe,built=prepared_small_world_candidate(args.prepared_small_world_candidate,original=reference/'clash95.exe',
                                                    profile=args.profile,resolution=args.resolution)
        elif getattr(args,'prepared_matrix_candidate',None) is not None:
            exe,built=prepared_matrix_candidate(args.prepared_matrix_candidate,original=reference/'clash95.exe',
                                                profile=args.profile,resolution=args.resolution)
        elif args.prepared_build:
            exe,built=prepared_candidate(args.prepared_build,case)
            report['prepared_build_receipt_sha256']=matrix.digest(args.prepared_build)
        else:exe,built=matrix.stage_candidate(args.profile,args.resolution,reference,out)
        report.update(built=built,proxy_build=build,executed_stage=built['stage'],executed_revision=built['recipe_revision'])
        if retain_raw:raw_context=raw_observation_context(exe,built)
        width,height=map(int,args.resolution.split('x'))
        source=native_phase_source(width,height)
        with patch.object(matrix.runtime,'HARNESS',source):
            require_hidden_disk_reserve(root,out,runtime_bytes=runtime_bytes,scratch_bytes=scratch_bytes,
                                        phase='before-harness-compile')
            engine=matrix.runtime.compile_harness(out)
        report.update(engine_sha256=matrix.digest(engine),engine_source_sha256=matrix.digest(out/'real-exe-engine.cpp'))
        require_hidden_disk_reserve(root,out,runtime_bytes=runtime_bytes,scratch_bytes=scratch_bytes,
                                    phase='before-runtime-copy')
        shutil.copytree(reference,work)
        if owned.verify_assets(work,manifest)!=baseline:
            raise ValueError('Working assets differ after copying')
        for name in manifest['runtime']['empty_directories']:
            directory=(work/name).resolve()
            if not directory.is_relative_to(work):raise ValueError('Escaping runtime directory')
            directory.mkdir(parents=True,exist_ok=True)
        target=work/exe.name
        if target.exists() or (work/'ddraw.dll').exists():raise ValueError('Candidate/proxy collides with runtime assets')
        shutil.copy2(exe,target);shutil.copy2(proxy,work/'ddraw.dll')
        control=out/'control';prepare_control(control)
        with logpath.open('w',encoding='utf-8') as log:
            if retain_raw:audit_raw_observation_context(raw_context)
            require_hidden_disk_reserve(root,out,scratch_bytes=scratch_bytes,phase='before-owned-launch')
            proc=OwnedHiddenProcess([str(engine),str(target),str(capture),'110','proxy',str(control),'native-phase-v1'],
                cwd=work,env=os.environ,stdout=log)
            report['host']=dict(pid=proc.pid,creation_filetime=proc.creation_filetime,desktop=proc.desktop_name)
            end=time.monotonic()+30
            ready=control/'phase-ack.json'
            while not ready.exists() and proc.poll() is None and time.monotonic()<end:time.sleep(.02)
            if not ready.is_file():raise ValueError('Native host produced no ready acknowledgment')
            if ready.stat().st_size>4096:raise ValueError('Oversize native acknowledgment')
            ack=json.loads(ready.read_text(encoding='ascii'),object_pairs_hook=unique_object)
            identity={k:ack[k] for k in ('pid','creation_filetime','image_base')}
            identity['candidate_sha256']=built['candidate_sha256']
            text=logpath.read_text(encoding='utf-8',errors='replace')
            loaded=re.findall(r'^REAL_LOADED pid=(\d+) base=([0-9a-f]+) entry=[0-9a-f]+ executable_sections_match=1$',text,re.M)
            if len(loaded)!=1 or (int(loaded[0][0]),int(loaded[0][1],16))!=(identity['pid'],identity['image_base']) or 'REAL_EXE_ENTRY observed=1' not in text:
                raise ValueError('Native acknowledgment has no matching loaded-code/entry authentication')
            retained=RetainedTarget(identity=identity,candidate_path=target)
            peer=PhaseClient(control,controller_sha256=phase_host.source_sha256(),identity=identity,
                check_owner=retained.check_owner,host_alive=lambda:proc.poll() is None)
            ready=peer.wait_ready()
            report['activation_identity']=activation_trace_identity(ready,
                phase_sha256=phase_host.source_sha256(),
                controller_sha256=report['source_hashes']['tools/ordinary_map_activation_host.py'])
            startup_deadline=time.monotonic()+60
            while True:
                text=logpath.read_text(encoding='utf-8',errors='replace')
                if 'OWNED_STARTUP_RETIRED ' in text and 'REAL_PHASE_HUMAN ' in text:break
                if proc.poll() is not None or time.monotonic()>=startup_deadline:
                    raise ValueError('Controlled startup did not retire before the natural human loop')
                time.sleep(.02)
            report['startup_retired_before_actions']=True
            report['owner']=identity
            candidate=candidate_context(built)
            if retain_raw:measured_actions(peer,retained.read_exact,candidate,out,report,raw_context=raw_context)
            else:measured_actions(peer,retained.read_exact,candidate,out,report)
            proc.wait(timeout=130)
    except Exception as error:
        report['errors'].append(f'{type(error).__name__}: {error}')
    finally:
        if proc is not None:
            try:
                if proc.poll() is None:proc.wait(timeout=125)
            except subprocess.TimeoutExpired:report['errors'].append('Hidden native host exceeded bounded interval')
            finally:
                try:proc.close()
                except Exception as error:report['errors'].append('Owned host cleanup: '+str(error))
                report['host_cleanup']=proc.cleanup
                report['host_returncode']=proc.returncode
        if retained is not None:
            report['retained_process_exited']=retained.kernel.WaitForSingleObject(retained.handle,5000)==0
            retained.close()
        if logpath.exists():
            text=logpath.read_text(encoding='utf-8',errors='replace')
            report['outcome']=full_observation(text,proc.returncode if proc else -1)
            report['debugger_log_sha256']=matrix.digest(logpath)
            try:
                report['activation_trace']=activation_diagnostics(text,report.get('activation_identity'))
            except Exception as error:
                report['activation_trace_error']=f'{type(error).__name__}: {error}'
            try:
                report['mouse_poll_trace']=mouse_poll_diagnostics(text,report.get('phase_receipts',[]))
            except Exception as error:
                report['mouse_poll_trace_error']=f'{type(error).__name__}: {error}'
        try:
            report['snapshots']=matrix.runtime.render(capture)
            if report['snapshots']:
                report['map_pixels']=validate_map_pixels(capture,reference,args.profile,args.resolution)
        except Exception as error:report['errors'].append('Capture audit: '+str(error))
        try:
            report['reference_unchanged']=baseline is not None and owned.verify_assets(reference,manifest)==baseline
            if built is not None and target is not None:
                report['candidate_unchanged']=matrix.digest(target)==built['candidate_sha256']==matrix.digest(exe)
                matrix.runtime.verify_hd_sources({'source_hashes':candidate_sources(built)},root)
                if 'prepared_matrix' in built:audit_prepared_matrix(exe,built)
                if 'prepared_small_world' in built:audit_prepared_small_world(exe,built)
                if retain_raw:audit_raw_observation_context(raw_context)
                report['working_original_unchanged']=matrix.digest(work/'clash95.exe')==matrix.runtime.ORIGINAL_SHA256
            report['sources_unchanged']=report['source_hashes']=={n:matrix.digest(root/n) for n in source_names}
            if not report['sources_unchanged']:raise ValueError('Driver/controller source changed during run')
        except Exception as error:report['errors'].append('Identity audit: '+str(error))
        report['unit_selected_observed']=any(a['name']=='select' and a['passed'] for a in report['actions'])
        report['map_controls_pixels_passed']=map_controls_passed(report.get('map_pixels',[]))
        report['passed']=hidden_success(report)
        (out/'playability.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return report


def run(args) -> dict:
    return run_hidden(args) if args.mode=='hidden-controlled' else run_foreground(args)

def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile',choices=tuple(matrix.BACKENDS),default='modalwidgets')
    parser.add_argument('--resolution',default='1024x768')
    parser.add_argument('--mode',choices=('hidden-controlled','foreground-diagnostic'),default='hidden-controlled')
    parser.add_argument('--prepared-build',type=Path)
    parser.add_argument('--prepared-matrix-candidate',type=Path)
    parser.add_argument('--prepared-small-world-candidate',type=Path)
    for name in ('runtime','manifest','proxy','out'):parser.add_argument('--'+name,type=Path)
    parser.add_argument('--execute',action='store_true');parser.add_argument('--approval-text')
    parser.add_argument('--native-present-bounds',action='store_true')
    parser.add_argument('--retain-raw-observations',action='store_true',
        help='Retain bounded canonical memory reads for offline replay; hidden-controlled with a reconstructed prepared matrix or small-world candidate only')
    args=parser.parse_args()
    if args.retain_raw_observations and args.mode!='hidden-controlled':
        parser.error('Raw observation retention requires hidden-controlled mode')
    if args.retain_raw_observations and not (args.prepared_matrix_candidate or args.prepared_small_world_candidate):
        parser.error('Raw observations require an independently reconstructed prepared matrix or small-world bundle')
    try:case=candidate_case(args)
    except ValueError as error:parser.error(str(error))
    if not args.execute:
        print(json.dumps(dict(executed=False,case=case,mode=args.mode,actions=['controlled-slot0-startup','measured-select','measured-one-cell-move'] if args.mode=='hidden-controlled' else ['campaign-diagnostic'])));return 0
    if not args.approval_text or not args.approval_text.strip() or not all((args.runtime,args.manifest,args.proxy,args.out)):
        parser.error('Execution requires explicit approval, assets, source-bound proxy and isolated output')
    report=run(args);print(json.dumps(report,indent=2))
    if args.mode == 'hidden-controlled':
        return int(not hidden_success(report))
    return int(bool(report['errors']) or not report.get('menu_and_campaign_input_passed') or not report.get('map_controls_pixels_passed')
               or not report.get('outcome',{}).get('observation_complete') or not report.get('reference_unchanged') or not report.get('retained_process_exited') or not report.get('native_input_passed') or not report.get('unit_selected_observed'))


if __name__=='__main__':raise SystemExit(main())
