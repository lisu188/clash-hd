"""Opt-in runner-only foreground adapter around the unchanged pulse input engine."""
from __future__ import annotations

import argparse
import ctypes as C
from ctypes import wintypes as W
import json
import os
from pathlib import Path
import sys
import time

import menu_pulse_click as pulse
import run_original_game_smoke as owned


def attach_pairs(current: int, foreground: int, target: int) -> list[tuple[int,int]]:
    if type(current) is not int or type(target) is not int or current<=0 or target<=0:
        raise ValueError('Valid current and owned window thread IDs required')
    return [(current,other) for other in dict.fromkeys((foreground,target)) if other>0 and other!=current]


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__,add_help=False)
    parser.add_argument('--approval-text',required=True)
    parser.add_argument('--owner-creation',type=int,required=True)
    parser.add_argument('--allow-foreground-attach',action='store_true')
    args,remaining=parser.parse_known_args()
    if not args.approval_text.strip() or not args.allow_foreground_attach or os.name!='nt' or os.environ.get('GITHUB_ACTIONS')!='true':
        parser.error('Explicit foreground opt-in on an isolated Windows Actions runner is required')
    if remaining.count('--pid')!=1 or remaining.count('--json')!=1 or '--observe-only' in remaining:
        parser.error('One owned PID and output are required; manual observation cannot use this adapter')
    pid=int(remaining[remaining.index('--pid')+1]);output=Path(remaining[remaining.index('--json')+1]).resolve()
    if pid<=0 or args.owner_creation<=0 or not output.is_relative_to(Path('C:/ClashTests').resolve()):
        parser.error('Owned process identity and isolated output are required')
    kernel,user,_=owned.win32()
    handle=owned.require(kernel.OpenProcess(0x1000|0x100000,False,pid),'retain input owner')
    original_focus=pulse.focus;original_argv=sys.argv
    records=[]
    def identity_matches():
        return kernel.WaitForSingleObject(handle,0)==258 and owned.process_identity(kernel,handle)['creation_filetime']==args.owner_creation
    try:
        if not identity_matches():raise ValueError('Input process creation identity differs')
        kernel.GetCurrentThreadId.restype=W.DWORD
        user.GetForegroundWindow.restype=W.HWND
        user.AttachThreadInput.argtypes=[W.DWORD,W.DWORD,W.BOOL];user.AttachThreadInput.restype=W.BOOL
        user.SetForegroundWindow.argtypes=[W.HWND];user.SetForegroundWindow.restype=W.BOOL
        user.BringWindowToTop.argtypes=[W.HWND];user.BringWindowToTop.restype=W.BOOL
        def focus(hwnd):
            owner=W.DWORD();target=int(user.GetWindowThreadProcessId(hwnd,C.byref(owner)))
            if owner.value!=pid or not identity_matches():
                records.append(dict(target=int(hwnd),owner_rejected=True));return False
            if original_focus(hwnd):
                records.append(dict(target=int(hwnd),plain_focus=True));return True
            foreground=user.GetForegroundWindow();foreground_owner=W.DWORD()
            foreground_thread=int(user.GetWindowThreadProcessId(foreground,C.byref(foreground_owner))) if foreground else 0
            current=int(kernel.GetCurrentThreadId())
            row=dict(target=int(hwnd),current_thread=current,target_thread=target,foreground=int(foreground or 0),
                     foreground_thread=foreground_thread,foreground_pid=foreground_owner.value,attached=[],detached=[])
            records.append(row)
            attached=[]
            try:
                for left,right in attach_pairs(current,foreground_thread,target):
                    C.set_last_error(0);ok=bool(user.AttachThreadInput(left,right,True))
                    row['attached'].append(dict(left=left,right=right,ok=ok,error=C.get_last_error()))
                    if not ok:return False
                    attached.append((left,right))
                row['bring_result']=bool(user.BringWindowToTop(hwnd))
                row['foreground_result']=bool(user.SetForegroundWindow(hwnd))
            finally:
                for left,right in reversed(attached):
                    C.set_last_error(0);ok=bool(user.AttachThreadInput(left,right,False))
                    row['detached'].append(dict(left=left,right=right,ok=ok,error=C.get_last_error()))
            time.sleep(.2)
            row['observed_foreground']=int(user.GetForegroundWindow() or 0)
            row['verified']=row['observed_foreground']==int(hwnd) and identity_matches() and all(r['ok'] for r in row['detached'])
            return row['verified']
        pulse.focus=focus
        sys.argv=[str(Path(pulse.__file__)),*remaining]
        return pulse.main()
    finally:
        pulse.focus=original_focus;sys.argv=original_argv
        kernel.CloseHandle(handle)
        receipt=dict(schema=1,approval_text=args.approval_text,owner_pid=pid,owner_creation=args.owner_creation,
                     strategy='explicit runner-only temporary input-queue attachment after plain focus fails',
                     pulse_source_sha256=owned.sha(Path(pulse.__file__)),adapter_sha256=owned.sha(Path(__file__)),
                     calls=records,manual_input_proof=False)
        output.with_suffix('.focus.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':raise SystemExit(main())
