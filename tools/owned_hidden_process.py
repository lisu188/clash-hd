"""Explicit Windows private-desktop launch of an owned debugger host.

No shell, foreground APIs, input or capture. The caller authenticates its host
and candidate. The existing real_exe_smoke host suppresses its own error dialogs
before starting the game; this launcher does not change the parent's error mode.
Use a context manager: close() terminates the whole owned job, including children
left behind by a normally exited host. The caller retains ownership of stdout.
"""
from __future__ import annotations

import ctypes as C
import math
import os
from pathlib import Path, PureWindowsPath
import re
import stat
import subprocess
import time
import uuid
from collections.abc import Mapping, Sequence
from contextlib import ExitStack, contextmanager

DWORD = C.c_uint32
HANDLE = C.c_void_p
BOOL = C.c_int32
SIZE_T = C.c_size_t
WAIT_OBJECT_0, WAIT_TIMEOUT, INFINITE = 0, 258, 0xffffffff
CREATE_FLAGS = 0x4 | 0x400 | 0x80000 | 0x08000000  # suspended, Unicode, extended, no console
QUIET_ERROR_MODE = 0x1 | 0x2 | 0x8000


class HiddenProcessError(RuntimeError):
    pass


class STARTUPINFO(C.Structure):
    _fields_ = [('cb', DWORD), ('lpReserved', C.c_wchar_p), ('lpDesktop', C.c_wchar_p),
                ('lpTitle', C.c_wchar_p)] + [(name, DWORD) for name in
                ('dwX', 'dwY', 'dwXSize', 'dwYSize', 'dwXCountChars', 'dwYCountChars',
                 'dwFillAttribute', 'dwFlags')] + [('wShowWindow', C.c_uint16),
                ('cbReserved2', C.c_uint16), ('lpReserved2', C.c_void_p),
                ('hStdInput', HANDLE), ('hStdOutput', HANDLE), ('hStdError', HANDLE)]


class STARTUPINFOEX(C.Structure):
    _fields_ = [('StartupInfo', STARTUPINFO), ('lpAttributeList', C.c_void_p)]


class PROCESS_INFORMATION(C.Structure):
    _fields_ = [('hProcess', HANDLE), ('hThread', HANDLE), ('dwProcessId', DWORD), ('dwThreadId', DWORD)]


class SECURITY_ATTRIBUTES(C.Structure):
    _fields_ = [('nLength', DWORD), ('lpSecurityDescriptor', C.c_void_p), ('bInheritHandle', BOOL)]


class JOB_BASIC_LIMIT(C.Structure):
    _fields_ = [('PerProcessUserTimeLimit', C.c_int64), ('PerJobUserTimeLimit', C.c_int64),
                ('LimitFlags', DWORD), ('MinimumWorkingSetSize', SIZE_T), ('MaximumWorkingSetSize', SIZE_T),
                ('ActiveProcessLimit', DWORD), ('Affinity', SIZE_T), ('PriorityClass', DWORD),
                ('SchedulingClass', DWORD)]


class IO_COUNTERS(C.Structure):
    _fields_ = [(name, C.c_uint64) for name in ('ReadOperationCount', 'WriteOperationCount',
                'OtherOperationCount', 'ReadTransferCount', 'WriteTransferCount', 'OtherTransferCount')]


class JOB_EXTENDED_LIMIT(C.Structure):
    _fields_ = [('BasicLimitInformation', JOB_BASIC_LIMIT), ('IoInfo', IO_COUNTERS)] + [
        (name, SIZE_T) for name in ('ProcessMemoryLimit', 'JobMemoryLimit', 'PeakProcessMemoryUsed', 'PeakJobMemoryUsed')]


class JOB_ACCOUNTING(C.Structure):
    _fields_ = [(name, C.c_int64) for name in ('TotalUserTime', 'TotalKernelTime',
                'ThisPeriodTotalUserTime', 'ThisPeriodTotalKernelTime')] + [(name, DWORD) for name in
                ('TotalPageFaultCount', 'TotalProcesses', 'ActiveProcesses', 'TotalTerminatedProcesses')]


def _absolute_local(value):
    value = os.fspath(value)
    if not isinstance(value, str) or not re.match(r'^[A-Za-z]:[\\/]', value):
        raise ValueError('An absolute local Windows path is required')
    if any(c in value for c in '\0\r\n') or ':' in value[2:] or '..' in PureWindowsPath(value).parts:
        raise ValueError('Ambiguous or nonlocal launch path')
    return value


def _checked_path(value, kind):
    path = Path(_absolute_local(value))
    for part in (path, *path.parents):
        info = part.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
            raise ValueError('Reparse-point launch paths are unsupported')
    resolved = path.resolve(strict=True)
    if not (resolved.is_file() if kind == 'file' else resolved.is_dir()):
        raise ValueError('Launch path has the wrong kind')
    if kind == 'file' and resolved.suffix.lower() != '.exe':
        raise ValueError('An explicit .exe host is required; no command interpreter')
    return str(resolved)


def _environment(env):
    if not isinstance(env, Mapping):
        raise TypeError('An explicit environment mapping is required')
    result, seen = {}, set()
    for key, value in env.items():
        if (type(key) is not str or type(value) is not str or not key or '=' in key or
                '\0' in key or '\0' in value or key.upper() in seen):
            raise ValueError('Invalid or case-ambiguous Windows environment')
        seen.add(key.upper())
        result[key] = value
    forced = {'CLASH_PROXY_PRESENT': '0', '_NT_SYMBOL_PATH': '.', '_NT_ALT_SYMBOL_PATH': ''}
    result = {key: value for key, value in result.items() if key.upper() not in forced}
    result.update(forced)
    block = '\0'.join(key + '=' + result[key] for key in sorted(result, key=str.upper)) + '\0\0'
    if len(block.encode('utf-16-le')) > 1024 * 1024:
        raise ValueError('Environment exceeds the bounded launch size')
    return result, block


def _milliseconds(timeout):
    if timeout is None:
        return INFINITE
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or timeout < 0:
        raise ValueError('Timeout must be finite, nonnegative seconds or None')
    milliseconds = math.ceil(timeout * 1000)
    if milliseconds >= INFINITE:
        raise ValueError('Timeout exceeds the native wait bound')
    return milliseconds


class _Windows:
    def __init__(self):
        if os.name != 'nt':
            raise OSError('Owned hidden processes require Windows')
        self.kernel = C.WinDLL('kernel32', use_last_error=True)
        self.user = C.WinDLL('user32', use_last_error=True)
        signatures = {
            'CloseHandle': ([HANDLE], BOOL), 'CreateJobObjectW': ([C.c_void_p, C.c_wchar_p], HANDLE),
            'SetInformationJobObject': ([HANDLE, C.c_int32, C.c_void_p, DWORD], BOOL),
            'QueryInformationJobObject': ([HANDLE, C.c_int32, C.c_void_p, DWORD, C.c_void_p], BOOL),
            'AssignProcessToJobObject': ([HANDLE, HANDLE], BOOL), 'TerminateJobObject': ([HANDLE, DWORD], BOOL),
            'TerminateProcess': ([HANDLE, DWORD], BOOL), 'ResumeThread': ([HANDLE], DWORD),
            'WaitForSingleObject': ([HANDLE, DWORD], DWORD), 'GetExitCodeProcess': ([HANDLE, C.POINTER(DWORD)], BOOL),
            'GetCurrentProcess': ([], HANDLE),
            'DuplicateHandle': ([HANDLE, HANDLE, HANDLE, C.POINTER(HANDLE), DWORD, BOOL, DWORD], BOOL),
            'CreateFileW': ([C.c_wchar_p, DWORD, DWORD, C.c_void_p, DWORD, DWORD, HANDLE], HANDLE),
            'InitializeProcThreadAttributeList': ([C.c_void_p, DWORD, DWORD, C.POINTER(SIZE_T)], BOOL),
            'UpdateProcThreadAttribute': ([C.c_void_p, DWORD, SIZE_T, C.c_void_p, SIZE_T, C.c_void_p, C.c_void_p], BOOL),
            'DeleteProcThreadAttributeList': ([C.c_void_p], None),
            'GetThreadErrorMode': ([], DWORD), 'SetThreadErrorMode': ([DWORD, C.POINTER(DWORD)], BOOL),
            'CreateProcessW': ([C.c_wchar_p, C.c_wchar_p, C.c_void_p, C.c_void_p, BOOL, DWORD,
                                C.c_void_p, C.c_wchar_p, C.POINTER(STARTUPINFOEX), C.POINTER(PROCESS_INFORMATION)], BOOL),
            'QueryFullProcessImageNameW': ([HANDLE, DWORD, C.c_wchar_p, C.POINTER(DWORD)], BOOL),
            'GetProcessTimes': ([HANDLE, C.c_void_p, C.c_void_p, C.c_void_p, C.c_void_p], BOOL),
        }
        for name, (args, result) in signatures.items():
            fn = getattr(self.kernel, name)
            fn.argtypes, fn.restype = args, result
        self.user.CreateDesktopW.argtypes = [C.c_wchar_p, C.c_void_p, C.c_void_p, DWORD, DWORD, C.c_void_p]
        self.user.CreateDesktopW.restype = HANDLE
        self.user.CloseDesktop.argtypes, self.user.CloseDesktop.restype = [HANDLE], BOOL

    @staticmethod
    def check(ok, label):
        if not ok:
            raise OSError(C.get_last_error(), label)
        return ok

    def desktop(self, name):
        return self.check(self.user.CreateDesktopW(name, None, None, 0, 0x000F01FF, None), 'CreateDesktopW')

    def job(self):
        return self.check(self.kernel.CreateJobObjectW(None, None), 'CreateJobObjectW')

    def configure_job(self, job):
        limits = JOB_EXTENDED_LIMIT()
        limits.BasicLimitInformation.LimitFlags = 0x2000  # KILL_ON_JOB_CLOSE; never permit breakaway
        self.check(self.kernel.SetInformationJobObject(job, 9, C.byref(limits), C.sizeof(limits)), 'SetInformationJobObject')

    def close_handle(self, handle):
        self.check(self.kernel.CloseHandle(handle), 'CloseHandle')

    def close_desktop(self, handle):
        self.check(self.user.CloseDesktop(handle), 'CloseDesktop')

    @contextmanager
    def quiet_launch(self):
        previous = DWORD()
        self.check(self.kernel.SetThreadErrorMode(self.kernel.GetThreadErrorMode() | QUIET_ERROR_MODE,
                                                  C.byref(previous)), 'SetThreadErrorMode')
        try:
            yield
        finally:
            self.check(self.kernel.SetThreadErrorMode(previous.value, None), 'Restore thread error mode')

    def launch(self, executable, command, cwd, block, desktop_name, stdout, info):
        import msvcrt
        with ExitStack() as cleanup:
            cleanup.enter_context(self.quiet_launch())
            output = HANDLE()
            current = self.kernel.GetCurrentProcess()
            self.check(self.kernel.DuplicateHandle(current, msvcrt.get_osfhandle(stdout.fileno()), current,
                                                  C.byref(output), 0, True, 2), 'Duplicate stdout handle')
            cleanup.callback(self.close_handle, output.value)
            security = SECURITY_ATTRIBUTES(C.sizeof(SECURITY_ATTRIBUTES), None, True)
            stdin = self.kernel.CreateFileW('NUL', 0x80000000, 3, C.byref(security), 3, 0x80, None)
            self.check(stdin not in (None, 0, C.c_void_p(-1).value), 'Open private NUL stdin')
            cleanup.callback(self.close_handle, stdin)
            size = SIZE_T()
            ok = self.kernel.InitializeProcThreadAttributeList(None, 1, 0, C.byref(size))
            if ok or C.get_last_error() != 122 or not 0 < size.value <= 1024 * 1024:
                raise HiddenProcessError('Unexpected handle-list allocation query')
            attributes = C.create_string_buffer(size.value)
            self.check(self.kernel.InitializeProcThreadAttributeList(attributes, 1, 0, C.byref(size)), 'Initialize handle list')
            cleanup.callback(self.kernel.DeleteProcThreadAttributeList, attributes)
            handles = (HANDLE * 2)(stdin, output.value)
            self.check(self.kernel.UpdateProcThreadAttribute(attributes, 0, 0x20002, handles,
                        C.sizeof(handles), None, None), 'Restrict inherited handles')
            startup = STARTUPINFOEX()
            startup.StartupInfo.cb = C.sizeof(startup)
            startup.StartupInfo.lpDesktop = desktop_name
            startup.StartupInfo.dwFlags = 0x1 | 0x100  # SHOWWINDOW | USESTDHANDLES
            startup.StartupInfo.wShowWindow = 0
            startup.StartupInfo.hStdInput = stdin
            startup.StartupInfo.hStdOutput = startup.StartupInfo.hStdError = output.value
            startup.lpAttributeList = C.cast(attributes, C.c_void_p)
            command_buffer, environment = C.create_unicode_buffer(command), C.create_unicode_buffer(block)
            self.check(self.kernel.CreateProcessW(executable, command_buffer, None, None, True, CREATE_FLAGS,
                        environment, cwd, C.byref(startup), C.byref(info)), 'CreateProcessW on private desktop')

    def assign(self, job, process):
        self.check(self.kernel.AssignProcessToJobObject(job, process), 'Assign suspended host to job')

    def identity(self, process):
        path, size = C.create_unicode_buffer(32768), DWORD(32768)
        self.check(self.kernel.QueryFullProcessImageNameW(process, 0, path, C.byref(size)), 'Query retained image path')
        creation, ended, kernel, user = (C.c_uint64() for _ in range(4))
        self.check(self.kernel.GetProcessTimes(process, C.byref(creation), C.byref(ended),
                                               C.byref(kernel), C.byref(user)), 'Get retained creation time')
        return path.value, creation.value

    def resume(self, thread):
        if self.kernel.ResumeThread(thread) != 1:
            raise HiddenProcessError('Unexpected suspended host thread count')

    def status(self, process, milliseconds):
        result = self.kernel.WaitForSingleObject(process, milliseconds)
        if result == WAIT_TIMEOUT:
            return None
        if result != WAIT_OBJECT_0:
            raise HiddenProcessError('Retained process wait failed: ' + str(result))
        code = DWORD()
        self.check(self.kernel.GetExitCodeProcess(process, C.byref(code)), 'Get retained process exit code')
        return code.value

    def terminate_job(self, job):
        self.check(self.kernel.TerminateJobObject(job, 1), 'Terminate owned job')

    def terminate_process(self, process):
        self.check(self.kernel.TerminateProcess(process, 1), 'Terminate suspended unassigned host')

    def wait_job_empty(self, job, timeout):
        deadline = time.monotonic() + timeout
        while True:
            info = JOB_ACCOUNTING()
            self.check(self.kernel.QueryInformationJobObject(job, 1, C.byref(info), C.sizeof(info), None), 'Query owned job accounting')
            if info.ActiveProcesses == 0:
                return
            if time.monotonic() >= deadline:
                raise HiddenProcessError('Owned job still contains active processes')
            time.sleep(.01)


class OwnedHiddenProcess:
    """Launch directly; close/context exit terminates and verifies the owned tree.

    poll/wait report the host's exit only. Only close() verifies whole-job cleanup.
    TimeoutExpired from wait leaves the process owned and available for cleanup.
    No candidate authentication, ordinary input, or rendered-state proof is implied.
    """
    def __init__(self, argv, cwd, env, stdout):
        if not isinstance(argv, Sequence) or isinstance(argv, (str, bytes)) or not 1 <= len(argv) <= 256:
            raise ValueError('A bounded nonempty argv sequence is required')
        self.args = tuple(os.fspath(value) for value in argv)
        if any(type(value) is not str or any(c in value for c in '\0\r\n') for value in self.args):
            raise ValueError('Invalid native launch argument')
        self.executable, self.cwd = _checked_path(self.args[0], 'file'), _checked_path(cwd, 'directory')
        self.args = (self.executable, *self.args[1:])
        self.command_line = subprocess.list2cmdline(self.args)
        if len(self.command_line.encode('utf-16-le')) // 2 >= 32767:
            raise ValueError('Command line exceeds Windows limit')
        self.environment, block = _environment(env)
        if not stdout.writable() or not stat.S_ISREG(os.fstat(stdout.fileno()).st_mode):
            raise ValueError('stdout must be an open writable regular file')
        stdout.flush()
        self._api = _Windows()
        self._desktop = self._job = None
        self._info = PROCESS_INFORMATION()
        self._assigned = self._closed = False
        self.returncode = None
        self.cleanup = None
        self.pid = self.creation_filetime = None
        self.desktop_name = 'ClashOwnedHost_' + uuid.uuid4().hex
        try:
            self._desktop = self._api.desktop(self.desktop_name)
            self._job = self._api.job()
            self._api.configure_job(self._job)
            self._api.launch(self.executable, self.command_line, self.cwd, block, self.desktop_name, stdout, self._info)
            if not self._info.hProcess or not self._info.hThread or not self._info.dwProcessId:
                raise HiddenProcessError('Incomplete created-process ownership')
            self.pid = self._info.dwProcessId
            self._api.assign(self._job, self._info.hProcess)
            self._assigned = True
            actual, self.creation_filetime = self._api.identity(self._info.hProcess)
            if _checked_path(actual, 'file').casefold() != self.executable.casefold() or self.creation_filetime <= 0:
                raise HiddenProcessError('Retained host identity differs')
            self._api.resume(self._info.hThread)
            self._api.close_handle(self._info.hThread)
            self._info.hThread = None
        except BaseException as error:
            try:
                self.close()
            except BaseException as cleanup_error:
                raise HiddenProcessError(f'Hidden launch failed ({error}); cleanup also failed ({cleanup_error})') from error
            raise

    def poll(self):
        if self.returncode is None:
            if self._closed or not self._info.hProcess:
                raise HiddenProcessError('No retained host handle')
            self.returncode = self._api.status(self._info.hProcess, 0)
        return self.returncode

    def wait(self, timeout=None):
        milliseconds = _milliseconds(timeout)
        if self.returncode is None:
            if self._closed or not self._info.hProcess:
                raise HiddenProcessError('No retained host handle')
            self.returncode = self._api.status(self._info.hProcess, milliseconds)
            if self.returncode is None:
                raise subprocess.TimeoutExpired(self.args, timeout)
        return self.returncode

    def kill(self):
        if self._closed:
            return
        if self._assigned:
            self._api.terminate_job(self._job)
        elif self._info.hProcess and self.poll() is None:
            self._api.terminate_process(self._info.hProcess)

    def close(self):
        if self._closed:
            return
        errors = []
        def attempt(operation):
            try:
                operation()
                return True
            except BaseException as error:
                errors.append(str(error))
                return False
        attempt(self.kill)
        exited = not self._info.hProcess or attempt(lambda: self.wait(5))
        empty = not self._assigned or attempt(lambda: self._api.wait_job_empty(self._job, 5))
        for owner, name, closer in ((self._info, 'hThread', self._api.close_handle),
                                     (self, '_job', self._api.close_handle),
                                     (self._info, 'hProcess', self._api.close_handle),
                                     (self, '_desktop', self._api.close_desktop)):
            handle = getattr(owner, name)
            if handle and attempt(lambda handle=handle, closer=closer: closer(handle)):
                setattr(owner, name, None)
        self._closed = not any((self._info.hThread, self._info.hProcess, self._job, self._desktop))
        self.cleanup = dict(host_exited=exited, job_empty=empty, handles_closed=self._closed, errors=errors)
        if errors:
            raise HiddenProcessError('Owned hidden-process cleanup failed: ' + '; '.join(errors))

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        self.close()
        return False
