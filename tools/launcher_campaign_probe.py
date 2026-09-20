"""Observe actual OS-input campaign transitions without modifying game state."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import traceback
from unittest.mock import patch

import launcher_resolution_sweep as sweep
import real_exe_smoke as smoke

ROUTES = {'campaign': 0x447700, 'campaign_choice': 0x448B90, 'map_entry': 0x40B660}
DISASSEMBLY_COMMIT = '1a4b06280b88962e27d600b2670ee44acb316daf'


def native_observer(source):
    anchor = '        s.command("sxe av"); s.command("sxe eh");'
    setup = '''        const ULONG observed_sites[] = {0x447700,0x448b90,0x40b660};
        for (ULONG address : observed_sites) {
            IDebugBreakpoint *watch=nullptr;
            check(s.control->AddBreakpoint(DEBUG_BREAKPOINT_CODE,DEBUG_ANY_ID,&watch),"route breakpoint");
            check(watch->SetOffset(address),"route breakpoint address");
            check(watch->AddFlags(DEBUG_BREAKPOINT_ENABLED|DEBUG_BREAKPOINT_ONE_SHOT),"route breakpoint flags");
            watch->Release();
        }
'''
    branch = '                else if (type==DEBUG_EVENT_EXCEPTION) {'
    observe = '''                else if (type==DEBUG_EVENT_BREAKPOINT && (ip==0x447700 || ip==0x448b90 || ip==0x40b660)) {
                    ULONG tid=0; check(s.system->GetCurrentThreadSystemId(&tid),"observed route thread");
                    const char *event=ip==0x447700?"campaign":ip==0x448b90?"campaign_choice":"map_entry";
                    printf("ROUTE_NATIVE event=%s ip=%08llx tid=%lu raw_x=%ld raw_y=%ld game_data=%08lx\\n",
                        event,ip,tid,static_cast<LONG>(s.word(0x544cfc)),static_cast<LONG>(s.word(0x544d00)),s.word(0x5202e4));
                    fflush(stdout);
                }
'''
    if source.count(anchor) != 1 or source.count(branch) != 1 or source.count('seconds>90') != 1:
        raise ValueError('Native observer insertion contract changed')
    return source.replace(anchor, setup+anchor).replace(branch, observe+branch).replace('seconds>90', 'seconds>240')


def events(log):
    found = []
    for line in log.splitlines():
        if not line.startswith('ROUTE_NATIVE '):
            continue
        match = re.fullmatch(r'ROUTE_NATIVE event=(campaign|campaign_choice|map_entry) ip=([0-9a-f]{8}) tid=([0-9]+) raw_x=(-?[0-9]+) raw_y=(-?[0-9]+) game_data=([0-9a-f]{8})', line)
        if match is None or int(match[2],16) != ROUTES[match[1]]:
            raise ValueError('Malformed or mismatched native route observation')
        found.append(dict(event=match[1],ip=match[2],tid=int(match[3]),raw_x=int(match[4]),raw_y=int(match[5]),game_data=match[6]))
    if len({row['event'] for row in found}) != len(found):
        raise ValueError('Duplicated one-shot route event')
    return found


def read_log(path):
    return path.read_text(encoding='utf-8',errors='replace') if path.exists() else ''


def wait_for(process, path, predicate, seconds):
    end = time.monotonic()+seconds
    while time.monotonic()<end:
        text = read_log(path)
        if predicate(text):
            return text
        if process.poll() is not None:
            break
        time.sleep(.2)
    raise RuntimeError('Required observed native boundary was not reached')


def run(args):
    case = next((row for row in sweep.inventory()['cases'] if row['profile']==args.profile and row['resolution']==args.resolution),None)
    if case is None:
        raise ValueError('Unsupported launcher profile/resolution')
    if not args.execute:
        return dict(executed=False, case=case, actions=['campaign button','first campaign choice'], manual_input_proof=False)
    root=Path(__file__).resolve().parents[1];reference=args.runtime.resolve();out=args.out.resolve()
    if os.name!='nt' or not args.approval_text or not args.approval_text.strip():
        raise ValueError('Explicit current-task input approval and native Windows required')
    if out.exists() or not out.is_relative_to(Path('C:/ClashTests').resolve()) or any(
            out.is_relative_to(p) or p.is_relative_to(out) for p in (root,reference)):
        raise ValueError('New isolated output under C:/ClashTests is required')
    out.mkdir(parents=True);capture=out/'evidence';capture.mkdir()
    report=dict(schema=1,case=case,approval_text=args.approval_text,input_kind='automated_relative_SendInput',
        disassembly_commit=DISASSEMBLY_COMMIT,source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),
        source_sha256=smoke.sha(Path(__file__)),base_harness_sha256=smoke.sha(Path(smoke.__file__)),
        actions=[],errors=[],manual_input_proof=False,promotion_ready=False)
    baseline=None;process=None;logpath=capture/'debugger.log'
    try:
        manifest=json.loads(args.manifest.read_text(encoding='utf-8-sig'));baseline=smoke.verify(reference,manifest)
        sweep.verify_proxy(args.proxy.resolve())
        work=out/'work';shutil.copytree(reference,work)
        for name in manifest['runtime']['empty_directories']:
            target=work/name
            if not target.resolve().is_relative_to(work):raise ValueError('Escaping empty directory')
            target.mkdir(parents=True,exist_ok=True)
        plan,built=sweep.prepare(case,work,out/'candidates')
        report['build']=built
        executable=work/'campaign-probe.exe';shutil.copy2(plan.candidate_exe,executable)
        shutil.copy2(args.proxy,work/'ddraw.dll')
        source=native_observer(smoke.HARNESS);report['native_observer_sha256']=hashlib.sha256(source.encode()).hexdigest()
        with patch.object(smoke,'HARNESS',source):engine=smoke.compile_harness(out)
        report['engine_sha256']=smoke.sha(engine)
        with logpath.open('w',encoding='utf-8',newline='\n') as log:
            process=subprocess.Popen([str(engine),str(executable),str(capture),'140','proxy'],cwd=work,
                env={**os.environ,'_NT_SYMBOL_PATH':'.','_NT_ALT_SYMBOL_PATH':'','CLASH_PROXY_PRESENT':'1'},
                stdout=log,stderr=subprocess.STDOUT)
            text=wait_for(process,logpath,lambda text:'REAL_PRIMARY sample=0 ' in text,45)
            loaded=re.search(r'^REAL_LOADED pid=([0-9]+) ',text,re.M)
            if loaded is None:raise ValueError('No actual process identity')
            pid=int(loaded[1]);report['pid']=pid
            for label,native_target,expected in [('campaign',(225,185),'campaign'),('first_campaign',(225,305),'campaign_choice')]:
                if process.poll() is not None or 'REAL_CLEANUP' in read_log(logpath):
                    raise RuntimeError('Owned game ended before input')
                x=native_target[0]+(case['width']-640)//2;y=native_target[1]+(case['height']-480)//2
                command=[sys.executable,str(root/'tools/menu_pulse_click.py'),'--pid',str(pid),'--resolution',case['resolution'],
                    '--aim-points',f'{label}:{x},{y}','--click-repeats','1','--click-hold-ms','400',
                    '--point-settle-ms','1000','--deadline-sec','20','--json',str(capture/(label+'-input.json'))]
                result=subprocess.run(command,capture_output=True,text=True,errors='replace',timeout=35)
                (capture/(label+'-input.log')).write_text(result.stdout+'\n'+result.stderr,encoding='utf-8')
                row=dict(label=label,target=[x,y],input_returncode=result.returncode);report['actions'].append(row)
                text=wait_for(process,logpath,lambda text:any(r['event']==expected for r in events(text)),5)
                row['native_callback_observed']=True
                time.sleep(4)
            text=wait_for(process,logpath,lambda text:any(r['event']=='map_entry' for r in events(text)),50)
            report['map_entry_observed']=True
            process.wait(timeout=160)
        text=read_log(logpath)
        report['runtime']=smoke.outcome(text,process.returncode)
        report['native_events']=events(text)
        report['samples']=smoke.render(capture)
        report['candidate_unchanged']=smoke.sha(executable)==built['output_sha256']
        report['original_copy_unchanged']=smoke.sha(work/'clash95.exe')==smoke.ORIGINAL_SHA256
    except Exception:
        report['errors'].append(traceback.format_exc())
    finally:
        if process is not None and process.poll() is None:
            try:process.wait(timeout=180)
            except subprocess.TimeoutExpired:
                process.kill();process.wait(timeout=10);report['errors'].append('Observer exceeded timeout; owned job closes with observer')
        text=read_log(logpath)
        report['runtime']=smoke.outcome(text,process.returncode if process is not None else -1)
        try:report['native_events']=events(text);report['samples']=smoke.render(capture)
        except Exception:report['errors'].append(traceback.format_exc())
        try:report['reference_unchanged']=baseline is not None and smoke.verify(reference,manifest)==baseline
        except Exception:report['reference_unchanged']=False;report['errors'].append(traceback.format_exc())
        (capture/'report.json').write_bytes(sweep.canonical(report))
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--profile',choices=tuple(sweep.BACKENDS),default='modalwidgets')
    p.add_argument('--resolution',default='1024x768')
    p.add_argument('--runtime',type=Path);p.add_argument('--manifest',type=Path);p.add_argument('--proxy',type=Path);p.add_argument('--out',type=Path)
    p.add_argument('--execute',action='store_true');p.add_argument('--approval-text')
    args=p.parse_args()
    if args.execute and not all((args.runtime,args.manifest,args.proxy,args.out,args.approval_text)):
        p.error('Execution requires assets, proxy, isolated output and actual approval')
    result=run(args);print(json.dumps(result,indent=2))
    return 0 if not args.execute else int(bool(result['errors']) or not result.get('map_entry_observed'))


if __name__=='__main__':raise SystemExit(main())
