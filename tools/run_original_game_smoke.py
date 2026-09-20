"""Explicitly approved, bounded original-game launch on an isolated Windows runner."""
from __future__ import annotations

import argparse
import ctypes as C
from ctypes import wintypes as W
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import struct
import subprocess
import sys
import time
import traceback

ORIGINAL_SHA = '500055d77d03d514e8d3168506bd10f67cd8569bcc450604ff8192f46cdaf3ae'
ASSET_COMMIT = '84a1e4bcf131e6bb75b39fc5e10941dd0b801767'


def sha(path: Path) -> str:
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


def verify_assets(root: Path, manifest: dict) -> dict:
    runtime = manifest['runtime']
    expected = {}
    for row in runtime['files']:
        name = row['path']
        relative = PurePosixPath(name)
        if relative.is_absolute() or '..' in relative.parts or str(relative) != name or '\\' in name:
            raise ValueError('Noncanonical asset path: ' + name)
        path = root.joinpath(*relative.parts)
        if name in expected or not path.resolve().is_relative_to(root.resolve()) or path.is_symlink():
            raise ValueError('Duplicate or escaping asset path: ' + name)
        if path.stat().st_size != row['size'] or sha(path) != row['sha256']:
            raise ValueError('Asset checksum/size differs or Git LFS content is unresolved: ' + name)
        expected[name] = dict(bytes=row['size'], sha256=row['sha256'])
    actual = {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}
    if actual != expected.keys() or len(expected) != runtime['file_count']:
        raise ValueError('Runtime file inventory differs')
    if sum(row['bytes'] for row in expected.values()) != runtime['total_bytes']:
        raise ValueError('Runtime total size differs')
    if expected.get('clash95.exe', {}).get('sha256') != ORIGINAL_SHA:
        raise ValueError('Unknown original executable')
    return expected


def win32():
    if os.name != 'nt':
        raise OSError('Native Windows is required; no emulation is implicit')
    kernel = C.WinDLL('kernel32', use_last_error=True)
    user = C.WinDLL('user32', use_last_error=True)
    gdi = C.WinDLL('gdi32', use_last_error=True)
    def bind(lib, name, result, *args):
        fn = getattr(lib, name); fn.restype = result; fn.argtypes = list(args); return fn
    bind(kernel, 'CreateJobObjectW', W.HANDLE, C.c_void_p, W.LPCWSTR)
    bind(kernel, 'SetInformationJobObject', W.BOOL, W.HANDLE, C.c_int, C.c_void_p, W.DWORD)
    bind(kernel, 'AssignProcessToJobObject', W.BOOL, W.HANDLE, W.HANDLE)
    bind(kernel, 'TerminateJobObject', W.BOOL, W.HANDLE, W.UINT)
    bind(kernel, 'TerminateProcess', W.BOOL, W.HANDLE, W.UINT)
    bind(kernel, 'ResumeThread', W.DWORD, W.HANDLE)
    bind(kernel, 'WaitForSingleObject', W.DWORD, W.HANDLE, W.DWORD)
    bind(kernel, 'CloseHandle', W.BOOL, W.HANDLE)
    bind(kernel, 'GetExitCodeProcess', W.BOOL, W.HANDLE, C.POINTER(W.DWORD))
    bind(kernel, 'OpenProcess', W.HANDLE, W.DWORD, W.BOOL, W.DWORD)
    bind(kernel, 'GetProcessTimes', W.BOOL, W.HANDLE, *([C.POINTER(W.FILETIME)] * 4))
    bind(kernel, 'QueryFullProcessImageNameW', W.BOOL, W.HANDLE, W.DWORD, W.LPWSTR, C.POINTER(W.DWORD))
    bind(user, 'GetWindowThreadProcessId', W.DWORD, W.HWND, C.POINTER(W.DWORD))
    bind(user, 'GetWindowTextW', C.c_int, W.HWND, W.LPWSTR, C.c_int)
    bind(user, 'GetClassNameW', C.c_int, W.HWND, W.LPWSTR, C.c_int)
    bind(user, 'GetWindowRect', W.BOOL, W.HWND, C.POINTER(W.RECT))
    bind(user, 'IsWindowVisible', W.BOOL, W.HWND)
    bind(user, 'IsHungAppWindow', W.BOOL, W.HWND)
    bind(user, 'PrintWindow', W.BOOL, W.HWND, W.HDC, W.UINT)
    bind(user, 'GetWindowDC', W.HDC, W.HWND)
    bind(user, 'ReleaseDC', C.c_int, W.HWND, W.HDC)
    bind(gdi, 'CreateCompatibleDC', W.HDC, W.HDC)
    bind(gdi, 'DeleteDC', W.BOOL, W.HDC)
    bind(gdi, 'DeleteObject', W.BOOL, W.HANDLE)
    bind(gdi, 'SelectObject', W.HANDLE, W.HDC, W.HANDLE)
    bind(gdi, 'CreateDIBSection', W.HBITMAP, W.HDC, C.c_void_p, W.UINT, C.POINTER(C.c_void_p), W.HANDLE, W.DWORD)
    bind(gdi, 'BitBlt', W.BOOL, W.HDC, C.c_int, C.c_int, C.c_int, C.c_int, W.HDC, C.c_int, C.c_int, W.DWORD)
    user.SetProcessDPIAware()
    return kernel, user, gdi


def require(value, label):
    if not value:
        raise C.WinError(C.get_last_error(), label)
    return value


def process_identity(kernel, handle):
    creation, exit_time, system, cpu = (W.FILETIME() for _ in range(4))
    require(kernel.GetProcessTimes(handle, C.byref(creation), C.byref(exit_time), C.byref(system), C.byref(cpu)), 'GetProcessTimes')
    name = C.create_unicode_buffer(32768); length = W.DWORD(len(name))
    require(kernel.QueryFullProcessImageNameW(handle, 0, name, C.byref(length)), 'QueryFullProcessImageName')
    return dict(path=name.value, creation_filetime=(creation.dwHighDateTime << 32) | creation.dwLowDateTime,
                cpu_100ns=((system.dwHighDateTime << 32) | system.dwLowDateTime) + ((cpu.dwHighDateTime << 32) | cpu.dwLowDateTime))


def windows_for(user, pid):
    result = []
    callback_type = C.WINFUNCTYPE(W.BOOL, W.HWND, W.LPARAM)
    @callback_type
    def callback(hwnd, _):
        owner = W.DWORD(); user.GetWindowThreadProcessId(hwnd, C.byref(owner))
        if owner.value == pid:
            title, cls = C.create_unicode_buffer(1024), C.create_unicode_buffer(256)
            user.GetWindowTextW(hwnd, title, len(title)); user.GetClassNameW(hwnd, cls, len(cls))
            rect = W.RECT(); valid = bool(user.GetWindowRect(hwnd, C.byref(rect)))
            result.append(dict(hwnd=int(hwnd), title=title.value, window_class=cls.value,
                               visible=bool(user.IsWindowVisible(hwnd)), hung=bool(user.IsHungAppWindow(hwnd)),
                               rect=[rect.left, rect.top, rect.right, rect.bottom] if valid else None))
        return True
    user.EnumWindows.argtypes = [callback_type, W.LPARAM]
    require(user.EnumWindows(callback, 0), 'EnumWindows')
    return result


def capture_window(hwnd, pid, creation, destination, method):
    from PIL import Image
    kernel, user, gdi = win32()
    handle = require(kernel.OpenProcess(0x1000 | 0x100000, False, pid), 'OpenProcess')
    dc = memory = bitmap = old = None
    try:
        owner = W.DWORD(); user.GetWindowThreadProcessId(hwnd, C.byref(owner))
        if owner.value != pid or process_identity(kernel, handle)['creation_filetime'] != creation:
            raise ValueError('Capture window or process identity changed')
        if kernel.WaitForSingleObject(handle, 0) != 258:
            raise ValueError('Capture owner has exited')
        rect = W.RECT(); require(user.GetWindowRect(hwnd, C.byref(rect)), 'GetWindowRect')
        width, height = rect.right - rect.left, rect.bottom - rect.top
        if not 16 <= width <= 4096 or not 16 <= height <= 4096:
            raise ValueError('Capture bounds outside supported range')
        dc = require(user.GetWindowDC(hwnd), 'GetWindowDC')
        memory = require(gdi.CreateCompatibleDC(dc), 'CreateCompatibleDC')
        info = C.create_string_buffer(struct.pack('<IiiHHIIiiII', 40, width, -height, 1, 32, 0, width * height * 4, 0, 0, 0, 0))
        bits = C.c_void_p()
        bitmap = require(gdi.CreateDIBSection(dc, info, 0, C.byref(bits), None, 0), 'CreateDIBSection')
        old = require(gdi.SelectObject(memory, bitmap), 'SelectObject')
        C.memset(bits, 0, width * height * 4)
        ok = user.PrintWindow(hwnd, memory, 0) if method == 'printwindow' else gdi.BitBlt(memory, 0, 0, width, height, dc, 0, 0, 0x00CC0020)
        require(ok, method)
        raw = C.string_at(bits, width * height * 4)
        image = Image.frombytes('RGB', (width, height), raw, 'raw', 'BGRX')
        if destination.exists():
            raise FileExistsError(destination)
        image.save(destination)
        return dict(path=destination.name, method=method, width=width, height=height, png_sha256=sha(destination),
                    rgb_sha256=hashlib.sha256(image.tobytes()).hexdigest(), extrema=image.getextrema(),
                    distinct_colors=len(image.getcolors(width * height) or []), game_rendering_accepted=False)
    finally:
        if old and memory: gdi.SelectObject(memory, old)
        if bitmap: gdi.DeleteObject(bitmap)
        if memory: gdi.DeleteDC(memory)
        if dc: user.ReleaseDC(hwnd, dc)
        kernel.CloseHandle(handle)


def run_game(game: Path, output: Path, seconds: int, approval_text: str) -> dict:
    if not approval_text or not approval_text.strip() or type(seconds) is not int or not 25 <= seconds <= 240:
        raise ValueError('Explicit approval and a bounded observation duration are required')
    if sha(game) != ORIGINAL_SHA:
        raise ValueError('Only the exact original executable can be launched')
    import _winapi
    kernel, user, _ = win32()
    class Basic(C.Structure):
        _fields_ = [('process_time', C.c_int64), ('job_time', C.c_int64), ('flags', W.DWORD),
                    ('min_ws', C.c_size_t), ('max_ws', C.c_size_t), ('active', W.DWORD),
                    ('affinity', C.c_size_t), ('priority', W.DWORD), ('scheduling', W.DWORD)]
    class Extended(C.Structure):
        _fields_ = [('basic', Basic), ('io', C.c_uint64 * 6), ('process_memory', C.c_size_t),
                    ('job_memory', C.c_size_t), ('peak_process', C.c_size_t), ('peak_job', C.c_size_t)]
    job = process = thread = None
    report = dict(schema=1, process_created=False, primary_thread_resumed=False, observations=[], errors=[],
                  game_executable_sha256=sha(game), input_method='none', debugger_attached=False,
                  gameplay_verified=False, manual_input_proof=False, promotion_ready=False)
    try:
        job = require(kernel.CreateJobObjectW(None, None), 'CreateJobObject')
        limits = Extended(); limits.basic.flags = 0x2000
        require(kernel.SetInformationJobObject(job, 9, C.byref(limits), C.sizeof(limits)), 'Kill-on-close job configuration')
        env = dict(os.environ, __COMPAT_LAYER='')
        process, thread, pid, tid = _winapi.CreateProcess(str(game), subprocess.list2cmdline([str(game)]),
            None, None, False, 0x4, env, str(game.parent), subprocess.STARTUPINFO())
        report.update(process_created=True, pid=pid, tid=tid, identity=process_identity(kernel, process))
        require(kernel.AssignProcessToJobObject(job, process), 'Assign suspended game to owned job')
        report['job_assigned_before_resume'] = True
        if kernel.ResumeThread(thread) == 0xFFFFFFFF:
            raise C.WinError()
        report['primary_thread_resumed'] = True
        kernel.CloseHandle(thread); thread = None
        start = time.monotonic()
        for checkpoint in sorted({2, 8, 20, *range(40, seconds, 40), seconds}):
            delay = max(0, checkpoint - (time.monotonic() - start))
            ended = kernel.WaitForSingleObject(process, int(delay * 1000))
            exit_code = W.DWORD(); require(kernel.GetExitCodeProcess(process, C.byref(exit_code)), 'GetExitCodeProcess')
            row = dict(elapsed_seconds=round(time.monotonic() - start, 3), alive=ended == 258,
                       exit_code=exit_code.value, exit_hex=f'{exit_code.value:08x}', windows=[], captures=[])
            report['observations'].append(row)
            if ended not in (0, 258):
                raise C.WinError(C.get_last_error(), 'WaitForSingleObject failed')
            if ended == 0:
                report['natural_exit_code'] = exit_code.value
                break
            row['identity'] = process_identity(kernel, process)
            row['windows'] = windows_for(user, pid)
            for window in [w for w in row['windows'] if w['visible'] and w['rect']][:3]:
                for method in ('bitblt', 'printwindow'):
                    name = output / f'game-{checkpoint:02}-{window["hwnd"]:x}-{method}.png'
                    command = [sys.executable, str(Path(__file__).resolve()), '--capture', str(window['hwnd']), str(pid),
                               str(report['identity']['creation_filetime']), str(name), method, '--approval-text', approval_text]
                    try:
                        result = subprocess.run(command, capture_output=True, text=True, timeout=5)
                        item = json.loads(result.stdout) if result.returncode == 0 else dict(error=result.stderr[-5000:], exit_code=result.returncode)
                    except (subprocess.TimeoutExpired, ValueError) as error:
                        item = dict(error=str(error), method=method)
                    row['captures'].append(item)
            write_json(output / 'runtime-progress.json', report)
        report['alive_before_cleanup'] = kernel.WaitForSingleObject(process, 0) == 258
    except Exception:
        report['errors'].append(traceback.format_exc())
    finally:
        if job:
            report['job_terminated'] = bool(kernel.TerminateJobObject(job, 0xD1A6))
        if process:
            if kernel.WaitForSingleObject(process, 5000) != 0:
                report['fallback_terminate'] = bool(kernel.TerminateProcess(process, 0xD1A6))
            report['owned_process_exited'] = kernel.WaitForSingleObject(process, 5000) == 0
        closed = [bool(kernel.CloseHandle(handle)) for handle in (thread, process, job) if handle]
        report['handles_closed'] = all(closed)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--assets', type=Path)
    parser.add_argument('--manifest', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--approval-text')
    parser.add_argument('--seconds', type=int, default=40)
    parser.add_argument('--capture', nargs=5, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.capture:
        if not args.approval_text or not args.approval_text.strip():
            parser.error('Capture requires the actual explicit approval text')
        hwnd, pid, creation, name, method = args.capture
        if method not in ('bitblt', 'printwindow'): parser.error('Unknown capture method')
        print(json.dumps(capture_window(int(hwnd), int(pid), int(creation), Path(name), method)))
        return 0
    if not all((args.assets, args.manifest, args.output)):
        parser.error('assets, manifest and output are required')
    if not 25 <= args.seconds <= 240: parser.error('seconds must be between 25 and 240')
    source, out = args.assets.resolve(), args.output.resolve()
    repo = Path(__file__).resolve().parents[1]
    if out.exists() or any(out.is_relative_to(p) or p.is_relative_to(out) for p in (source, repo)):
        parser.error('output must be a new isolated directory, outside source and checkout')
    if not args.execute:
        print(json.dumps(dict(executed=False, assets=str(source), output=str(out), requires_explicit_approval=True)))
        return 0
    if os.name != 'nt' or not args.approval_text or not args.approval_text.strip():
        parser.error('Native Windows and the actual explicit approval text are required')
    out.mkdir(parents=True)
    manifest = json.loads(args.manifest.read_text(encoding='utf-8-sig'))
    report = dict(schema=1, started_at=datetime.now(timezone.utc).isoformat(), approval_text=args.approval_text,
                  asset_commit=ASSET_COMMIT, manifest_sha256=sha(args.manifest), harness_sha256=sha(Path(__file__)),
                  source_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=repo, text=True).strip(),
                  stage='original_unpatched_gog', wrapper='original GOG ddraw.dll', errors=[], gameplay_verified=False,
                  manual_input_proof=False, promotion_ready=False)
    evidence = out / 'evidence'; evidence.mkdir()
    before = None
    try:
        before = verify_assets(source, manifest)
        report['asset_files'] = before
        work = out / 'game'; shutil.copytree(source, work)
        for name in manifest['runtime']['empty_directories']:
            relative = PurePosixPath(name)
            if relative.is_absolute() or '..' in relative.parts: raise ValueError('Invalid empty directory')
            work.joinpath(*relative.parts).mkdir(parents=True, exist_ok=True)
        verify_assets(work, manifest)
        report['runtime'] = run_game(work / 'clash95.exe', evidence, args.seconds, args.approval_text)
        report['original_exe_unchanged'] = sha(work / 'clash95.exe') == ORIGINAL_SHA
        report['work_changes'] = [name for name, value in before.items() if not (work / name).is_file() or sha(work / name) != value['sha256']]
        report['new_work_files'] = [p.relative_to(work).as_posix() for p in work.rglob('*') if p.is_file() and p.relative_to(work).as_posix() not in before]
    except Exception:
        report['errors'].append(traceback.format_exc())
    finally:
        try: report['reference_assets_unchanged'] = before is not None and verify_assets(source, manifest) == before
        except Exception: report['reference_assets_unchanged'] = False; report['errors'].append(traceback.format_exc())
        write_json(evidence / 'original-game-launch.json', report)
    runtime = report.get('runtime', {})
    return 0 if (runtime.get('primary_thread_resumed') and runtime.get('owned_process_exited')
                 and report.get('reference_assets_unchanged') and not report['errors'] and not runtime['errors']) else 1


if __name__ == '__main__':
    raise SystemExit(main())
