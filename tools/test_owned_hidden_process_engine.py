"""Opt-in native private-desktop/job fixture; never launches the game or captures UI.

Without --execute, only the portable report fixtures run. Native outputs and
failure diagnostics are retained in a new explicitly supplied scratch directory.
"""
from __future__ import annotations

import argparse
import ctypes as C
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import unittest

import owned_hidden_process as owned

ROOT = Path(__file__).resolve().parents[1]
CASES = ('parent-and-child-waiting', 'parent-exits-first')
MARKER = 'CLASH_OWNED_DESKTOP_FIXTURE_V1'
SOURCE = r'''
#include <windows.h>
#include <stdio.h>
#include <string>
#include <vector>
#include <stdexcept>

static const char *marker="CLASH_OWNED_DESKTOP_FIXTURE_V1";
static std::wstring desktop() {
    wchar_t value[256]={}; DWORD length=0;
    if (!GetUserObjectInformationW(GetThreadDesktop(GetCurrentThreadId()),UOI_NAME,value,sizeof(value),&length))
        throw std::runtime_error("desktop query failed");
    return value;
}
static void record(const std::wstring &directory,const wchar_t *role,DWORD child) {
    auto name=desktop();
    for (wchar_t c:name) if (!(c>='a'&&c<='z') && !(c>='A'&&c<='Z') && !(c>='0'&&c<='9') && c!='_')
        throw std::runtime_error("unexpected desktop name");
    std::wstring file=directory+L"/"+role+L".json", temporary=file+L".tmp";
    FILE *output=nullptr;
    if (_wfopen_s(&output,temporary.c_str(),L"wb") || !output) throw std::runtime_error("record open failed");
    int result=fprintf(output,"{\"marker\":\"%s\",\"role\":\"%ls\",\"pid\":%lu,\"child_pid\":%lu,\"desktop\":\"%ls\"}\n",
        marker,role,GetCurrentProcessId(),child,name.c_str());
    if (fclose(output) || result<0 || !MoveFileExW(temporary.c_str(),file.c_str(),MOVEFILE_WRITE_THROUGH))
        throw std::runtime_error("record publish failed");
}
int wmain(int argc,wchar_t **argv) {
    SetErrorMode(SEM_FAILCRITICALERRORS|SEM_NOGPFAULTERRORBOX|SEM_NOOPENFILEERRORBOX);
    try {
        if (argc!=4 || (wcscmp(argv[1],L"--parent") && wcscmp(argv[1],L"--child")) ||
            (wcscmp(argv[3],L"wait") && wcscmp(argv[3],L"exit"))) return 2;
        std::wstring directory=argv[2];
        if (!wcscmp(argv[1],L"--child")) {
            record(directory,L"child",0);
            Sleep(60000); return 0;
        }
        wchar_t executable[32768]={};
        DWORD size=GetModuleFileNameW(nullptr,executable,32768);
        if (!size || size>=32768) throw std::runtime_error("module path failed");
        std::wstring command=L"\""+std::wstring(executable)+L"\" --child \""+directory+L"\" wait";
        std::vector<wchar_t> buffer(command.begin(),command.end()); buffer.push_back(0);
        STARTUPINFOW startup={}; startup.cb=sizeof(startup);
        // Null lpDesktop intentionally exercises inheritance from the hidden parent.
        PROCESS_INFORMATION child={};
        if (!CreateProcessW(executable,buffer.data(),nullptr,nullptr,FALSE,CREATE_NO_WINDOW,
                            nullptr,nullptr,&startup,&child)) throw std::runtime_error("child creation failed");
        CloseHandle(child.hThread); CloseHandle(child.hProcess);
        record(directory,L"parent",child.dwProcessId);
        const char output[]="CLASH_OWNED_FIXTURE_STDOUT\n", error[]="CLASH_OWNED_FIXTURE_STDERR\n";
        DWORD wrote=0;
        if (!WriteFile(GetStdHandle(STD_OUTPUT_HANDLE),output,sizeof(output)-1,&wrote,nullptr) || wrote!=sizeof(output)-1)
            throw std::runtime_error("stdout unavailable");
        if (!WriteFile(GetStdHandle(STD_ERROR_HANDLE),error,sizeof(error)-1,&wrote,nullptr) || wrote!=sizeof(error)-1)
            throw std::runtime_error("stderr unavailable");
        ULONGLONG end=GetTickCount64()+60000;
        while (GetTickCount64()<end) {
            if (!wcscmp(argv[3],L"exit") && GetFileAttributesW((directory+L"/exit-parent").c_str())!=INVALID_FILE_ATTRIBUTES)
                return 0;
            Sleep(10);
        }
        return 0;
    } catch (const std::exception &error) {
        fprintf(stderr,"CLASH_OWNED_FIXTURE_FAILURE %s winerror=%lu\n",error.what(),GetLastError());
        return 3;
    }
}
'''


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def report_payload(records, *, setup_error=None, compiled=None, source_hashes=None):
    completed = (len(records) == len(CASES) and {row['case'] for row in records} == set(CASES)
                 and all(row.get('completed') is True for row in records))
    return dict(schema='clash95_owned_hidden_process_engine_v1',
                recorded_utc=datetime.now(timezone.utc).isoformat(),
                game_runtime_executed=False, manual_input_proof=False, desktop_capture_executed=False,
                fixture_runtime_executed=any(row.get('parent_entry_observed') is True or
                    row.get('child_entry_observed') is True for row in records),
                expected_cases=len(CASES), completed=completed,
                passed=completed and setup_error is None and all(row.get('passed') is True for row in records),
                setup_error=setup_error, source_sha256=source_hashes, compiled_fixture=compiled, cases=records,
                scope='Native synthetic parent/child desktop inheritance and owned job cleanup only; no game, debugger, input or capture')


class ReportTests(unittest.TestCase):
    def test_setup_failure_or_unobserved_launch_is_not_fixture_execution(self):
        for rows in ([], [dict(case=CASES[0], completed=True, passed=False, host_started=True)]):
            result = report_payload(rows, setup_error='setup failed')
            self.assertFalse(result['fixture_runtime_executed'])
            self.assertFalse(result['passed'])
            self.assertFalse(result['completed'])

    def test_both_distinct_finished_cases_are_required(self):
        rows = [dict(case=name, completed=True, passed=True, parent_entry_observed=True,
                     child_entry_observed=True) for name in CASES]
        self.assertTrue(report_payload(rows)['passed'])
        for invalid in (rows[:1], [rows[0], rows[0]], [rows[0], dict(rows[1], completed=False)]):
            self.assertFalse(report_payload(invalid)['passed'])
        self.assertFalse(report_payload(rows, setup_error='source changed')['passed'])

    def test_observed_parent_with_unproven_child_reports_partial_execution(self):
        result = report_payload([dict(case=CASES[0], parent_entry_observed=True,
                                      child_entry_observed=False, completed=True, passed=False)])
        self.assertTrue(result['fixture_runtime_executed'])
        self.assertFalse(result['passed'])
        self.assertFalse(result['game_runtime_executed'])


def checked_new_path(path, parent):
    path = Path(owned._absolute_local(path))
    for current in (path, *path.parents):
        if current.exists() and (current.is_symlink() or getattr(current, 'is_junction', lambda:False)()):
            raise ValueError('Fixture path traverses a link or junction')
    path = path.resolve()
    if path.exists() or not path.is_relative_to(parent.resolve()) or path == parent.resolve():
        raise ValueError('A new fixture path inside the designated directory is required')
    if any(c in str(path) for c in '\"&|<>%\r\n') or not str(path).isascii():
        raise ValueError('Fixture build paths must be simple literal ASCII paths')
    return path


def compile_fixture(directory):
    cpp, executable = directory/'owned-process-fixture.cpp', directory/'owned-process-fixture.exe'
    cpp.write_text(SOURCE, encoding='ascii', newline='\n')
    vswhere = Path(os.environ['ProgramFiles(x86)'])/'Microsoft Visual Studio/Installer/vswhere.exe'
    discovery = subprocess.run([str(vswhere), '-latest', '-products', '*', '-requires',
        'Microsoft.VisualStudio.Component.VC.Tools.x86.x64', '-property', 'installationPath'],
        capture_output=True, text=True, timeout=30, creationflags=subprocess.CREATE_NO_WINDOW)
    (directory/'compiler-discovery.log').write_text(discovery.stdout+discovery.stderr, encoding='utf-8')
    if discovery.returncode or not discovery.stdout.strip():
        raise RuntimeError('No MSVC x86 installation found')
    vcvars = Path(discovery.stdout.strip())/'VC/Auxiliary/Build/vcvars32.bat'
    command = directory/'compile.cmd'
    command.write_text(f'@echo off\ncall "{vcvars}" >nul\nif errorlevel 1 exit /b %ERRORLEVEL%\n'
        f'cl /nologo /EHsc /W4 /O2 /MT "{cpp}" /Fo"{directory / "fixture.obj"}" '
        f'/Fe"{executable}" /link /MACHINE:X86 user32.lib\nexit /b %ERRORLEVEL%\n', encoding='ascii')
    shell = Path(os.environ['SystemRoot'])/'System32/cmd.exe'
    result = subprocess.run([str(shell), '/d', '/c', str(command)], cwd=directory,
        capture_output=True, text=True, timeout=60, creationflags=subprocess.CREATE_NO_WINDOW)
    (directory/'compile.log').write_text(result.stdout+result.stderr, encoding='utf-8')
    if result.returncode:
        raise RuntimeError('Synthetic fixture compilation failed: '+result.stdout+result.stderr)
    return executable, dict(cpp_sha256=digest(cpp), executable_sha256=digest(executable),
                           compiler_command_sha256=digest(command), executable=str(executable))


def require(value, message):
    if not value:
        raise AssertionError(message)


def wait_record(path, process, role, deadline):
    while time.monotonic() < deadline:
        if path.exists():
            result = json.loads(path.read_text(encoding='ascii'))
            require(set(result) == {'marker','role','pid','child_pid','desktop'} and
                    result['marker'] == MARKER and result['role'] == role,
                    'Synthetic entry record differs')
            return result
        require(process.poll() is None, 'Synthetic parent exited before record '+role)
        time.sleep(.01)
    raise TimeoutError('No synthetic entry record: '+role)


def run_case(executable, directory, case, executable_sha256):
    directory.mkdir()
    row = dict(case=case, passed=False, completed=False, host_started=False,
               parent_entry_observed=False, child_entry_observed=False, errors=[])
    native = owned._Windows()
    native.kernel.OpenProcess.argtypes = [owned.DWORD, owned.BOOL, owned.DWORD]
    native.kernel.OpenProcess.restype = owned.HANDLE
    native.kernel.IsProcessInJob.argtypes = [owned.HANDLE, owned.HANDLE, C.POINTER(owned.BOOL)]
    native.kernel.IsProcessInJob.restype = owned.BOOL
    process = None
    retained = {}
    logfile = directory/'stdout-stderr.log'
    try:
        with logfile.open('w', encoding='ascii', newline='\n') as log:
            process = owned.OwnedHiddenProcess([str(executable), '--parent', str(directory),
                'exit' if case == 'parent-exits-first' else 'wait'], cwd=directory,
                env=dict(os.environ), stdout=log)
            row['host_started'] = True
            duplicate = owned.HANDLE()
            current = native.kernel.GetCurrentProcess()
            native.check(native.kernel.DuplicateHandle(current, process._info.hProcess, current,
                         C.byref(duplicate), 0, False, 2), 'Retain independent parent handle')
            retained['parent'] = duplicate.value
            deadline = time.monotonic()+10
            parent = wait_record(directory/'parent.json', process, 'parent', deadline)
            row['parent_entry_observed'] = True
            child = wait_record(directory/'child.json', process, 'child', deadline)
            row['child_entry_observed'] = True
            require(parent['pid'] == process.pid and parent['child_pid'] == child['pid'] and child['child_pid'] == 0,
                    'Reported parent/child identity differs')
            require(parent['desktop'] == child['desktop'] == process.desktop_name and
                    process.desktop_name.startswith('ClashOwnedHost_'), 'Native private desktop inheritance differs')
            row['native_records'] = dict(parent=parent, child=child)
            child_handle = native.kernel.OpenProcess(0x1000 | 0x100000 | 0x1, False, child['pid'])
            native.check(child_handle, 'Retain synthetic child handle')
            retained['child'] = child_handle
            identities = {}
            for name, handle in retained.items():
                actual, creation = native.identity(handle)
                require(Path(actual).resolve() == executable.resolve() and creation >= process.creation_filetime,
                        'Retained synthetic image path or creation time differs')
                require(native.status(handle, 0) is None, 'Synthetic process exited before cleanup test')
                inside = owned.BOOL()
                native.check(native.kernel.IsProcessInJob(handle, process._job, C.byref(inside)), 'Query fixture job membership')
                require(inside.value == 1, 'Synthetic process escaped the owned job')
                identities[name] = dict(path=actual, creation_filetime=creation, in_owned_job=True)
            row['retained_identities'] = identities
            if case == 'parent-exits-first':
                (directory/'exit-parent').write_text('explicit parent exit\n', encoding='ascii')
                require(process.wait(timeout=5) == 0, 'Synthetic parent did not exit normally')
                require(native.status(retained['child'], 0) is None, 'Child did not survive parent exit')
                row['parent_exit_before_cleanup'] = True
                row['child_live_after_parent_exit'] = True
            else:
                require(process.poll() is None, 'Parent not live before whole-job cleanup')
                row['parent_and_child_live_before_cleanup'] = True
            process.close()
            row['cleanup'] = process.cleanup
            exits = {name:native.status(handle, 5000) for name, handle in retained.items()}
            require(all(code is not None for code in exits.values()), 'Retained owned process survived job cleanup')
            row['retained_exit_codes'] = exits
            require(process.cleanup == dict(host_exited=True, job_empty=True, handles_closed=True, errors=[]),
                    'Wrapper cleanup was not fully verified')
            require(not log.closed and log.writable(), 'Wrapper closed the caller-owned stdout stream')
            log.write('CALLER_STDOUT_REMAINS_OPEN\n')
            log.flush()
            row['stdout_remained_caller_owned'] = True
        text = logfile.read_text(encoding='ascii')
        for marker in ('CLASH_OWNED_FIXTURE_STDOUT', 'CLASH_OWNED_FIXTURE_STDERR', 'CALLER_STDOUT_REMAINS_OPEN'):
            require(marker in text, 'Expected output handle marker missing: '+marker)
        require(digest(executable) == executable_sha256, 'Synthetic executable changed during test')
        row.update(passed=True, executable_unchanged=True, stdout_stderr_verified=True)
    except BaseException as error:
        row['errors'].append(type(error).__name__+': '+str(error))
    finally:
        if process is not None:
            try:
                process.close()
                row.setdefault('cleanup', process.cleanup)
            except BaseException as error:
                row['errors'].append('Wrapper cleanup: '+str(error))
        for name, handle in retained.items():
            try:
                if native.status(handle, 0) is None:
                    native.terminate_process(handle)
                    require(native.status(handle, 5000) is not None, 'Fallback retained fixture cleanup failed')
                    row.setdefault('fallback_terminations', []).append(name)
                    row['errors'].append('Fallback termination required for '+name)
            except BaseException as error:
                row['errors'].append('Retained cleanup '+name+': '+str(error))
            finally:
                try:
                    native.close_handle(handle)
                except BaseException as error:
                    row['errors'].append('Close retained '+name+': '+str(error))
        row['completed'] = True
        row['passed'] = row['passed'] and not row['errors']
        if logfile.exists():
            row['log_sha256'] = digest(logfile)
    return row


def execute(scratch, report):
    require(os.name == 'nt', 'Native fixture requires Windows')
    scratch = checked_new_path(scratch, Path('C:/ClashTests'))
    report = checked_new_path(report, ROOT/'reports')
    records, compiled, setup_error = [], None, None
    sources = {name:digest(ROOT/name) for name in ('tools/owned_hidden_process.py',
                                                  'tools/test_owned_hidden_process_engine.py')}
    started = time.monotonic()
    scratch.mkdir(parents=True)
    try:
        executable, compiled = compile_fixture(scratch)
        for index, case in enumerate(CASES):
            records.append(run_case(executable, scratch/f'case-{index+1}', case, compiled['executable_sha256']))
        require(all(digest(ROOT/name) == expected for name, expected in sources.items()), 'Fixture sources changed during execution')
    except BaseException as error:
        setup_error = type(error).__name__+': '+str(error)
    result = report_payload(records, setup_error=setup_error, compiled=compiled, source_hashes=sources)
    result.update(scratch=str(scratch), elapsed_seconds=round(time.monotonic()-started, 3))
    report.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--scratch', type=Path)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    if not args.execute:
        result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ReportTests))
        return int(not result.wasSuccessful())
    if args.scratch is None or args.report is None:
        parser.error('--execute requires new --scratch and --report paths')
    result = execute(args.scratch, args.report)
    print(json.dumps(result, indent=2))
    return int(not result['passed'])


if __name__ == '__main__':
    raise SystemExit(main())
