"""Explicit real-game menu, campaign and map-input diagnostics for launcher presets."""
from __future__ import annotations

import argparse
import ctypes as C
from ctypes import wintypes as W
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
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
         <<",\"map_active_word\":"<<s.word(0x527c24)<<",\"native_modal_word\":"<<s.word(0x52698c)<<"}\n";
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


def input_success(record: dict) -> bool:
    rows=record.get('steps',[])
    return bool(rows) and record.get('all_steps_accounted') is True and all(
        r.get('clicked') is True and r.get('aim',{}).get('converged') is True for r in rows)


def validate_map_pixels(capture: Path, reference: Path, profile: str, resolution: str) -> list[dict]:
    import frame_surface_audit as frame
    import action_bar_surface_audit as bar
    from src.patcher.framed_viewport import FramedViewport
    def resource(name):
        found=[p for p in reference.rglob('*') if p.is_file() and p.name.lower()==name]
        if len(found)!=1:raise ValueError('Ambiguous resource: '+name)
        return found[0].read_bytes()
    artwork=frame.load_native_frame(resource('gfx3.res'))
    sprites,member=bar.load_sprites(resource('minimum.res'))
    layout=FramedViewport(*map(int,resolution.split('x')))
    rows=[]
    paths=sorted(capture.glob('primary-*.json'))
    for path in paths[-3:]:
        image,raw=indexed_image(path)
        if image.size!=(layout.width,layout.height):raise ValueError('Final primary size differs')
        edges=frame.audit_surface(raw,layout,artwork) if profile!='classic' else None
        geometry_stage=bar.FRAMED_STAGE if profile!='classic' else None
        cells=bar.compare_cells(raw,layout.width,layout.height,sprites,stage=geometry_stage)
        rows.append(dict(sample=path.name,frame=edges,action_cells=cells,
            action_cells_exact=all(c['exact_source_match'] for c in cells),
            frame_required=profile!='classic',frame_source_sha256=frame.RESOURCE_SHA256,
            action_source_sha256=bar.RESOURCE_SHA256,action_member_sha256=member))
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


def run(args) -> dict:
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
        report.update(built=built,proxy_build=build)
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
                command=[sys.executable,str(root/'tools/runner_menu_input.py'),'--allow-foreground-attach',
                    '--approval-text',args.approval_text,'--owner-creation',str(identity['creation_filetime']),
                    '--pid',str(pid),'--resolution',args.resolution,phase,points,'--click-repeats','1',
                    '--click-hold-ms','400','--point-settle-ms','1800','--deadline-sec','20','--map-nonblack','0',
                    '--final-settle-ms','1200','--json',str(destination)]
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
            wait_until(43)
            click('dismiss','dismiss:320,220','--aim-points')
            wait_until(58)
            click('select-unit','select-unit:320,365','--aim-points')
            wait_until(75)
            click('preview-move','preview-move:384,430','--aim-points')
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
            report['outcome']=matrix.runtime.outcome(logpath.read_text(encoding='utf-8',errors='replace'),proc.returncode if proc else -1)
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
        report['native_input_passed']=len(report['actions'])==4 and all(a['passed'] for a in report['actions'])
        report['map_controls_pixels_passed']=len(report.get('map_pixels',[]))==3 and all(
            r['action_cells_exact'] and (not r['frame_required'] or r['frame']['structural_border_exact']) for r in report['map_pixels'])
        report['source_commit']=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
        report['source_hashes']={name:matrix.digest(root/name) for name in ('tools/resolution_playability.py','tools/launcher_resolution_matrix.py','tools/real_exe_smoke.py','tools/runner_menu_input.py','tools/menu_pulse_click.py','src/launcher/resolutions.json')}
        (out/'playability.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return report


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile',choices=tuple(matrix.BACKENDS),default='modalwidgets')
    parser.add_argument('--resolution',default='1024x768')
    for name in ('runtime','manifest','proxy','out'):parser.add_argument('--'+name,type=Path)
    parser.add_argument('--execute',action='store_true');parser.add_argument('--approval-text')
    args=parser.parse_args();case=matrix.select_case(args.profile,args.resolution)
    if not args.execute:
        print(json.dumps(dict(executed=False,case=case,actions=['campaign','dismiss','select-unit','preview-move'])));return 0
    if not args.approval_text or not args.approval_text.strip() or not all((args.runtime,args.manifest,args.proxy,args.out)):
        parser.error('Execution requires explicit approval, assets, source-bound proxy and isolated output')
    report=run(args);print(json.dumps(report,indent=2))
    return int(bool(report['errors']) or not report.get('menu_and_campaign_input_passed') or not report.get('map_controls_pixels_passed')
               or not report.get('outcome',{}).get('observation_complete') or not report.get('reference_unchanged') or not report.get('retained_process_exited') or not report.get('native_input_passed'))


if __name__=='__main__':raise SystemExit(main())
