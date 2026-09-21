"""Enumerate launcher presets and observe actual candidate startup without promoting gameplay."""
from __future__ import annotations

import argparse
import ctypes
import hashlib
import importlib
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'tools'), str(ROOT/'src/launcher')]
import bootstrap
bootstrap.ensure_repo_paths()
import core
import presets
import real_exe_smoke as runtime
from src.display_plan import resolve_display_plan

MANIFEST = ROOT/'src/launcher/resolutions.json'
BACKENDS = {'classic':'classic','framed':'framed','completehd':'completehd','modalwidgets':'modalwidgets'}


def digest(path: Path) -> str:
    return runtime.sha(path)


def inventory() -> list[dict]:
    manifest = presets.load_manifest()
    if set(manifest['profiles']) != set(BACKENDS):
        raise ValueError('A launcher profile lacks an explicit runtime backend')
    rows = []
    for profile, definition in manifest['profiles'].items():
        for resolution in definition['resolutions']:
            display = presets.resolve_plan(renderer=profile,resolution=resolution,manifest=manifest)
            rows.append(dict(profile=profile,resolution=resolution,stage=display.stage,
                recipe_revision=display.recipe_revision,manifest_sha256=digest(MANIFEST)))
    return rows


def select_case(profile: str, resolution: str) -> dict:
    matches = [r for r in inventory() if (r['profile'],r['resolution'])==(profile,resolution)]
    if len(matches)!=1: raise ValueError('Select one exact preset from the current launcher manifest')
    return matches[0]


def choose_display(modes: list[dict], width: int, height: int) -> dict | None:
    possible = [m for m in modes if m['width']>=width and m['height']>=height and m['bits']==32
                and m['width']<=4096 and m['height']<=2160]
    return min(possible,key=lambda m:(m['width']*m['height'],m['width'],m['height'],m['frequency'])) if possible else None


class RunnerDisplay:
    def __init__(self, width: int, height: int):
        self.width,self.height=width,height
        self.report=dict(requested=[width,height],changed=False,restored=None,adequate=False)
        self.saved=None

    def current(self):
        mode=ctypes.create_string_buffer(220)
        struct.pack_into('<H',mode,68,220)
        if not self.enum(None,0xffffffff,mode): raise ctypes.WinError()
        return mode

    @staticmethod
    def row(mode):
        bits,w,h,flags,freq=struct.unpack_from('<5I',mode,168)
        return dict(width=w,height=h,bits=bits,frequency=freq)

    def __enter__(self):
        if os.name!='nt' or os.environ.get('GITHUB_ACTIONS')!='true':
            raise ValueError('Display adjustment is restricted to the explicitly executed isolated Actions runner')
        user=ctypes.WinDLL('user32',use_last_error=True)
        user.SetProcessDPIAware()
        self.enum=user.EnumDisplaySettingsW
        self.enum.argtypes=[ctypes.c_wchar_p,ctypes.c_uint32,ctypes.c_void_p];self.enum.restype=ctypes.c_int
        self.change=user.ChangeDisplaySettingsExW
        self.change.argtypes=[ctypes.c_wchar_p,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_uint32,ctypes.c_void_p]
        self.change.restype=ctypes.c_int32
        self.saved=self.current();before=self.row(self.saved)
        modes=[];buffers={}
        for index in range(4096):
            mode=ctypes.create_string_buffer(220);struct.pack_into('<H',mode,68,220)
            if not self.enum(None,index,mode):break
            row=self.row(mode);row['index']=index;modes.append(row);buffers[index]=mode
        self.report.update(before=before,modes=modes)
        chosen=choose_display(modes,self.width,self.height)
        if before['width']>=self.width and before['height']>=self.height:
            self.report['adequate']=True
        elif chosen:
            mode=buffers[chosen['index']]
            test=self.change(None,mode,None,2,None);self.report['test_result']=test
            if test==0:
                actual=self.change(None,mode,None,0,None);self.report['change_result']=actual
                self.report['changed']=actual==0
                if actual==0:time.sleep(1)
        after=self.row(self.current());self.report['after']=after
        self.report['adequate']=after['width']>=self.width and after['height']>=self.height
        return self.report

    def __exit__(self,*_):
        if self.saved is not None and self.report['changed']:
            self.report['restore_result']=self.change(None,self.saved,None,0,None)
            self.report['restored']=self.row(self.current())==self.report['before']
        else:self.report['restored']=True


def stage_candidate(profile: str,resolution: str,reference: Path,output: Path) -> tuple[Path,dict]:
    case=select_case(profile,resolution)
    backend=importlib.import_module(BACKENDS[profile])
    plan=backend.plan_candidate(resolution=resolution,clash_dir=reference,candidates_root=output/'candidates')
    display=core.display_for_plan(plan)
    if (plan.stage,display.recipe_revision)!=(case['stage'],case['recipe_revision']):
        raise ValueError('Launcher backend does not match the advertised profile identity')
    record=backend.ensure_candidate(plan)
    if digest(plan.candidate_exe)!=record['output_sha256']:
        raise ValueError('Prepared launcher candidate bytes differ')
    return plan.candidate_exe,dict(case,launcher_build=record,candidate_sha256=record['output_sha256'])


def image_audit(folder: Path,resolution: str,snapshots: list[dict]) -> dict:
    from PIL import Image
    import numpy as np
    width,height=map(int,resolution.split('x'))
    result=dict(primary_count=len(snapshots),requested_size=False,stable_primary=False,
                nonempty_primary=False,window_primary_identical=False,window_compared=False)
    if len(snapshots)<3:return result
    result['requested_size']=all((s['width'],s['height'])==(width,height) for s in snapshots)
    if not result['requested_size']:return result
    result['stable_primary']=len({s['raw_sha256'] for s in snapshots[-3:]})==1
    result['nonempty_primary']=all(s['nonzero_indices']>10000 for s in snapshots[-3:])
    primary=np.array(Image.open(folder/snapshots[-1]['png']).convert('RGB'))
    ox,oy=(width-640)//2,(height-480)//2
    result['native_menu_bounds']=[ox,oy,ox+640,oy+480]
    mask=np.ones((height,width),dtype=bool);mask[oy:oy+480,ox:ox+640]=False
    mask[:32,:32]=False
    result['outer_nonblack_pixels_except_initial_cursor']=int(np.count_nonzero(np.any(primary!=0,axis=2)&mask))
    cropped=Image.fromarray(primary[oy:oy+480,ox:ox+640]);cropped.save(folder/'native-menu.png')
    result['native_menu_png_sha256']=digest(folder/'native-menu.png')
    windows=sorted(folder.glob('window-*.png'))
    if windows:
        last=np.array(Image.open(windows[-1]).convert('RGB'))
        result['window_compared']=True
        result['window_dimensions']=[int(last.shape[1]),int(last.shape[0])]
        if last.shape==primary.shape:
            different=np.any(last!=primary,axis=2);yy,xx=np.nonzero(different)
            result['window_mismatches']=int(len(xx))
            result['window_mismatch_bounds']=None if not len(xx) else [int(xx.min()),int(yy.min()),int(xx.max())+1,int(yy.max())+1]
            result['window_primary_identical']=not len(xx)
    return result


def run_case(args) -> dict:
    case=select_case(args.profile,args.resolution)
    if os.name!='nt':raise ValueError('Real candidate execution requires Windows')
    reference=args.runtime.resolve();output=args.out.resolve()
    if output.exists() or any(output.is_relative_to(p) or p.is_relative_to(output) for p in (reference,ROOT)):
        raise ValueError('Use a new output outside the checkout and reference assets')
    if not output.is_relative_to(Path('C:/ClashTests').resolve()):
        raise ValueError('Runtime candidate output must be under C:/ClashTests')
    output.mkdir(parents=True)
    report=dict(schema=1,case=case,errors=[],build_passed=False,gameplay_verified=False,
                manual_input_proof=False,promotion_ready=False,full_stage_probe_executed=False,
                wrapper_scope='source-built diagnostic DirectDraw; not shipped GOG wrapper')
    baseline=None
    try:
        manifest=json.loads(args.manifest.read_text(encoding='utf-8-sig'))
        baseline=runtime.verify(reference,manifest)
        proxy=args.proxy.resolve();proxy_manifest=json.loads(proxy.with_name('ddraw_surfdump_proxy.build.json').read_text(encoding='utf-8-sig'))
        if proxy_manifest.get('generated_by')!='clash-hd-surface-dump-proxy' or digest(proxy)!=proxy_manifest['output_sha256'].lower() or digest(ROOT/'src/ddraw_surfdump_proxy/ddraw_surfdump_proxy.cpp')!=proxy_manifest['source_sha256'].lower():
            raise ValueError('Diagnostic proxy build identity differs')
        report['proxy_build']=proxy_manifest
        exe,built=stage_candidate(args.profile,args.resolution,reference,output)
        report.update(build_passed=True,built=built)
        engine=runtime.compile_harness(output)
        report['engine_sha256']=digest(engine)
        work=output/'work';shutil.copytree(reference,work)
        for name in manifest['runtime']['empty_directories']:
            path=(work/name).resolve()
            if not path.is_relative_to(work):raise ValueError('Nonlocal runtime directory')
            path.mkdir(parents=True,exist_ok=True)
        target=work/exe.name
        if target.exists():raise ValueError('Candidate filename collides with a reference file')
        shutil.copy2(exe,target);shutil.copy2(proxy,work/'ddraw.dll')
        capture=output/'capture';capture.mkdir()
        width,height=map(int,args.resolution.split('x'))
        display=RunnerDisplay(width,height)
        try:
            with display as setting:
                report['display']=setting
                command=[str(engine),str(target),str(capture),str(args.seconds),'proxy']
                env=dict(os.environ,CLASH_PROXY_PRESENT='1',_NT_SYMBOL_PATH='.',_NT_ALT_SYMBOL_PATH='')
                begin=time.monotonic()
                result=subprocess.run(command,cwd=work,env=env,capture_output=True,text=True,errors='replace',timeout=args.seconds+100)
                report['elapsed_seconds']=round(time.monotonic()-begin,3)
                log=result.stdout+'\n'+result.stderr
                (capture/'debugger.log').write_text(log,encoding='utf-8')
                report['outcome']=runtime.outcome(log,result.returncode)
                report['returncode']=result.returncode
        finally:report['display']=display.report
        snapshots=runtime.render(capture)
        report['snapshots']=snapshots
        report['images']=image_audit(capture,args.resolution,snapshots)
        report['candidate_unchanged']=digest(target)==built['candidate_sha256']==digest(exe)
        report['working_original_unchanged']=digest(work/'clash95.exe')==runtime.ORIGINAL_SHA256
        record=built['launcher_build']
        sources=record.get('source_sha256')
        if isinstance(sources,dict):runtime.verify_hd_sources({'source_hashes':sources},ROOT)
        report['candidate_sources_unchanged']=bool(sources) if args.profile!='classic' else None
        report['startup_observed']=bool(report['outcome']['observation_complete'] and report['images']['requested_size']
            and report['images']['stable_primary'] and report['images']['nonempty_primary'] and report['candidate_unchanged'])
        report['full_window_observed']=bool(report['startup_observed'] and report['images']['window_primary_identical'] and report['display']['adequate'])
        if (work/'ddraw_surfdump_proxy.log').exists():
            shutil.copy2(work/'ddraw_surfdump_proxy.log',capture/'proxy.log')
    except Exception as error:
        report['errors'].append(f'{type(error).__name__}: {error}')
    finally:
        try:report['reference_assets_unchanged']=baseline is not None and runtime.verify(reference,manifest)==baseline
        except Exception as error:report['reference_assets_unchanged']=False;report['errors'].append(str(error))
        report['source_commit']=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
        report['source_hashes']={p:digest(ROOT/p) for p in ('tools/launcher_resolution_matrix.py','tools/real_exe_smoke.py','src/launcher/resolutions.json')}
        (output/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return report


def summarize(reports: list[dict]) -> dict:
    expected={(r['profile'],r['resolution']):r for r in inventory()}
    seen={};invalid=[]
    for report in reports:
        case=report.get('case',{});key=(case.get('profile'),case.get('resolution'))
        if key not in expected or key in seen or case!=expected.get(key):
            invalid.append(list(key));continue
        seen[key]=report
    missing=[dict(profile=p,resolution=r) for p,r in expected if (p,r) not in seen]
    rows=[]
    for key,case in expected.items():
        r=seen.get(key,{})
        rows.append(dict(case,build_passed=r.get('build_passed') is True,startup_observed=r.get('startup_observed') is True,
                         full_window_observed=r.get('full_window_observed') is True,errors=r.get('errors',[]),
                         gameplay_verified=False))
    return dict(schema=1,cases=rows,expected_count=len(expected),observed_count=len(seen),missing=missing,invalid=invalid,
                all_startups_observed=not missing and not invalid and all(r['startup_observed'] for r in rows),
                all_full_windows_observed=not missing and not invalid and all(r['full_window_observed'] for r in rows),
                all_gameplay_verified=False,custom_resolution_coverage=False,promotion_ready=False,
                evidence_scope='index of exact-manifest runtime receipts; not independent artifact or gameplay acceptance')


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--matrix',action='store_true')
    parser.add_argument('--summarize',type=Path)
    parser.add_argument('--profile',choices=tuple(BACKENDS))
    parser.add_argument('--resolution')
    parser.add_argument('--runtime',type=Path)
    parser.add_argument('--manifest',type=Path)
    parser.add_argument('--proxy',type=Path)
    parser.add_argument('--out',type=Path)
    parser.add_argument('--seconds',type=int,default=35)
    parser.add_argument('--execute',action='store_true')
    args=parser.parse_args()
    if args.matrix:
        if args.execute:parser.error('Matrix enumeration never executes a game')
        print(json.dumps({'include':inventory()},separators=(',',':')));return 0
    if args.summarize:
        reports=[json.loads(p.read_text(encoding='utf-8')) for p in sorted(args.summarize.rglob('report.json'))]
        report=summarize(reports)
        print(json.dumps(report,indent=2));return int(not report['all_startups_observed'])
    try:case=select_case(args.profile,args.resolution)
    except ValueError as error:parser.error(str(error))
    if not 25<=args.seconds<=90:parser.error('Observation interval must be between 25 and 90 seconds')
    if not args.execute:
        print(json.dumps(dict(executed=False,case=case)));return 0
    if not all((args.runtime,args.manifest,args.proxy,args.out)):parser.error('runtime, manifest, proxy and out are required')
    report=run_case(args)
    print(json.dumps(report,indent=2))
    return int(bool(report['errors']) or not report.get('startup_observed') or not report.get('reference_assets_unchanged'))


if __name__=='__main__':raise SystemExit(main())
