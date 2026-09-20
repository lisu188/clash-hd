"""Explicit native input against one isolated, authenticated launcher candidate."""
from __future__ import annotations

import argparse
import ctypes
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

import launcher_resolution_matrix as matrix
import run_original_game_smoke as owned


def route(text: str, resolution: str) -> str:
    width,height=map(int,resolution.split('x'))
    result=[]
    for item in text.split(';'):
        match=re.fullmatch(r'([a-z][a-z0-9-]{0,39}):([0-9]{1,3}),([0-9]{1,3})',item)
        if not match:raise ValueError('Use named native-menu points: campaign:224,185')
        name,x,y=match[1],int(match[2]),int(match[3])
        if not 0<=x<640 or not 0<=y<480:raise ValueError('Native menu point out of bounds')
        result.append(f'{name}:{x+(width-640)//2},{y+(height-480)//2}')
    if not 1<=len(result)<=4:raise ValueError('One to four explicitly named steps are required')
    return ';'.join(result)


def observe(args) -> dict:
    case=matrix.select_case(args.profile,args.resolution)
    steps=route(args.steps,args.resolution)
    reference=args.runtime.resolve();out=args.out.resolve();root=matrix.ROOT
    if os.name!='nt' or os.environ.get('GITHUB_ACTIONS')!='true':
        raise ValueError('Native input is restricted to an explicitly executed disposable Windows runner')
    if out.exists() or not out.is_relative_to(Path('C:/ClashTests').resolve()) or any(out.is_relative_to(p) or p.is_relative_to(out) for p in (root,reference)):
        raise ValueError('New isolated output under C:/ClashTests is required')
    out.mkdir(parents=True);capture=out/'capture';capture.mkdir()
    report=dict(schema=1,case=case,approval_text=args.approval_text,native_input_requested=steps,
                errors=[],input_attempted=False,gameplay_verified=False,manual_input_proof=False,promotion_ready=False)
    baseline=None;engine_process=None;handle=None;kernel=None
    try:
        manifest=json.loads(args.manifest.read_text(encoding='utf-8-sig'))
        baseline=matrix.runtime.verify(reference,manifest)
        proxy=args.proxy.resolve();build=json.loads(proxy.with_name('ddraw_surfdump_proxy.build.json').read_text(encoding='utf-8-sig'))
        if build.get('generated_by')!='clash-hd-surface-dump-proxy' or matrix.digest(proxy)!=build['output_sha256'].lower() or matrix.digest(root/'src/ddraw_surfdump_proxy/ddraw_surfdump_proxy.cpp')!=build['source_sha256'].lower():
            raise ValueError('Proxy source/build identity differs')
        exe,record=matrix.stage_candidate(args.profile,args.resolution,reference,out)
        report.update(built=record,proxy_build=build)
        engine=matrix.runtime.compile_harness(out)
        work=out/'work';shutil.copytree(reference,work)
        for name in manifest['runtime']['empty_directories']:
            path=(work/name).resolve()
            if not path.is_relative_to(work):raise ValueError('Nonlocal runtime directory')
            path.mkdir(parents=True,exist_ok=True)
        target=work/exe.name
        if target.exists():raise ValueError('Candidate filename collides with reference')
        shutil.copy2(exe,target);shutil.copy2(proxy,work/'ddraw.dll')
        display=matrix.RunnerDisplay(*map(int,args.resolution.split('x')))
        log_path=capture/'debugger.log'
        try:
            with display as configuration, log_path.open('w',encoding='utf-8') as log:
                report['display']=configuration
                if not configuration['adequate']:raise ValueError('Full visible client required before native input')
                command=[str(engine),str(target),str(capture),'90','proxy']
                env=dict(os.environ,CLASH_PROXY_PRESENT='1',_NT_SYMBOL_PATH='.',_NT_ALT_SYMBOL_PATH='')
                started=time.monotonic()
                engine_process=subprocess.Popen(command,cwd=work,env=env,stdout=log,stderr=subprocess.STDOUT)
                pid=None
                while time.monotonic()-started<40 and engine_process.poll() is None:
                    text=log_path.read_text(encoding='utf-8',errors='replace')
                    records=re.findall(r'^REAL_LOADED pid=([0-9]+) base=00400000 entry=[0-9a-f]+ executable_sections_match=1$',text,re.M)
                    if len(records)==1 and 'REAL_EXE_ENTRY observed=1' in text and (capture/'primary-00.json').is_file() and time.monotonic()-started>=12:
                        pid=int(records[0]);break
                    time.sleep(.25)
                if pid is None:raise RuntimeError('No authenticated live entry and first primary sample before input deadline')
                kernel,_,_=owned.win32()
                handle=owned.require(kernel.OpenProcess(0x1000|0x100000,False,pid),'Open owned game for input identity')
                identity=owned.process_identity(kernel,handle)
                if Path(identity['path']).resolve()!=target.resolve() or kernel.WaitForSingleObject(handle,0)!=258:
                    raise ValueError('Input owner no longer matches authenticated candidate')
                report['input_owner']=dict(identity,pid=pid,exe_sha256=matrix.digest(target))
                tool=root/('tools/runner_menu_input.py' if args.runner_focus else 'tools/menu_pulse_click.py');report['input_tool_sha256']=matrix.digest(tool)
                input_command=[sys.executable,str(tool),'--pid',str(pid),'--resolution',args.resolution,
                               '--steps',steps,'--map-nonblack','0','--click-repeats','1','--click-hold-ms','500',
                               '--deadline-sec','25','--final-settle-ms','2500','--json',str(out/'input.json')]
                if args.runner_focus:
                    input_command.extend(['--allow-foreground-attach','--approval-text',args.approval_text,
                                          '--owner-creation',str(identity['creation_filetime'])])
                report['input_attempted']=True
                try:
                    sent=subprocess.run(input_command,capture_output=True,text=True,errors='replace',timeout=45)
                    (out/'input.log').write_text(sent.stdout+'\n'+sent.stderr,encoding='utf-8')
                    report['input_exit']=sent.returncode
                    if (out/'input.json').exists():report['input']=json.loads((out/'input.json').read_text())
                except subprocess.TimeoutExpired as error:
                    report['errors'].append('Native input helper timeout: '+str(error))
                engine_process.wait(timeout=max(1,started+180-time.monotonic()))
        finally:
            report['display']=display.report
            if handle and kernel:kernel.CloseHandle(handle);handle=None
            if engine_process is not None and engine_process.poll() is None:
                engine_process.kill();engine_process.wait(timeout=10)
        log=log_path.read_text(encoding='utf-8',errors='replace')
        report['outcome']=matrix.runtime.outcome(log,engine_process.returncode)
        report['snapshots']=matrix.runtime.render(capture)
        report['candidate_unchanged']=matrix.digest(target)==record['candidate_sha256']==matrix.digest(exe)
        report['original_unchanged']=matrix.digest(work/'clash95.exe')==matrix.runtime.ORIGINAL_SHA256
        sources=record['launcher_build'].get('source_sha256')
        if isinstance(sources,dict):matrix.runtime.verify_hd_sources({'source_hashes':sources},root)
        report['input_transition_observed']=bool(report.get('input_exit')==0 and report.get('input',{}).get('all_steps_accounted') is True and
            len(report.get('input',{}).get('steps',[]))==len(steps.split(';')) and
            all(r.get('transition_verified') is True and r.get('clicked') is True for r in report.get('input',{}).get('steps',[])))
        if (work/'ddraw_surfdump_proxy.log').exists():shutil.copy2(work/'ddraw_surfdump_proxy.log',capture/'proxy.log')
    except Exception as error:
        report['errors'].append(f'{type(error).__name__}: {error}')
    finally:
        if handle and kernel:kernel.CloseHandle(handle)
        if engine_process is not None and engine_process.poll() is None:
            engine_process.kill();engine_process.wait(timeout=10)
        try:report['reference_assets_unchanged']=baseline is not None and matrix.runtime.verify(reference,manifest)==baseline
        except Exception as error:report['reference_assets_unchanged']=False;report['errors'].append(str(error))
        report['source_commit']=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
        report['source_sha256']=matrix.digest(Path(__file__))
        (out/'input-report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    return report


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile',choices=tuple(matrix.BACKENDS),default='modalwidgets')
    parser.add_argument('--resolution',default='1024x768')
    parser.add_argument('--steps',default='campaign:224,185')
    parser.add_argument('--runtime',type=Path);parser.add_argument('--manifest',type=Path)
    parser.add_argument('--proxy',type=Path);parser.add_argument('--out',type=Path)
    parser.add_argument('--execute',action='store_true');parser.add_argument('--allow-native-input',action='store_true')
    parser.add_argument('--approval-text')
    parser.add_argument('--runner-focus',action='store_true')
    args=parser.parse_args()
    try:case=matrix.select_case(args.profile,args.resolution);points=route(args.steps,args.resolution)
    except ValueError as error:parser.error(str(error))
    if not args.execute:
        print(json.dumps(dict(executed=False,case=case,steps=points,input_injected=False)));return 0
    if not args.allow_native_input or not args.approval_text or not args.approval_text.strip():
        parser.error('Native input requires both explicit flags and the actual approval text')
    if not all((args.runtime,args.manifest,args.proxy,args.out)):parser.error('runtime, manifest, proxy and out are required')
    report=observe(args);print(json.dumps(report,indent=2))
    return int(bool(report['errors']) or not report.get('input_transition_observed') or not report.get('reference_assets_unchanged') or
               not report.get('outcome',{}).get('observation_complete') or
               not report.get('candidate_unchanged') or not report.get('original_unchanged'))


if __name__=='__main__':raise SystemExit(main())
