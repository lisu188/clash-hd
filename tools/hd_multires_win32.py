"""Task-owned hidden desktop and suspended-process job, with no visible fallback."""
from __future__ import annotations

import ctypes as C
from ctypes import wintypes as W
import os
from pathlib import Path
import subprocess
import time
import uuid

DWORD, SIZE_T, HANDLE = W.DWORD, C.c_size_t, W.HANDLE


class StartupInfo(C.Structure):
    _fields_ = [("cb", DWORD), ("lpReserved", W.LPWSTR), ("lpDesktop", W.LPWSTR),
        ("lpTitle", W.LPWSTR), *[(n, DWORD) for n in ("dwX", "dwY", "dwXSize", "dwYSize",
        "dwXCountChars", "dwYCountChars", "dwFillAttribute", "dwFlags")],
        ("wShowWindow", W.WORD), ("cbReserved2", W.WORD), ("lpReserved2", C.c_void_p),
        ("hStdInput", HANDLE), ("hStdOutput", HANDLE), ("hStdError", HANDLE)]


class ProcessInfo(C.Structure):
    _fields_ = [("process", HANDLE), ("thread", HANDLE), ("pid", DWORD), ("tid", DWORD)]


class BasicLimits(C.Structure):
    _fields_ = [("process_time", C.c_longlong), ("job_time", C.c_longlong), ("flags", DWORD),
        ("minimum_ws", SIZE_T), ("maximum_ws", SIZE_T), ("active_limit", DWORD),
        ("affinity", SIZE_T), ("priority", DWORD), ("scheduling", DWORD)]


class IoCounters(C.Structure):
    _fields_ = [(n, C.c_ulonglong) for n in ("read_ops", "write_ops", "other_ops", "read_bytes", "write_bytes", "other_bytes")]


class ExtendedLimits(C.Structure):
    _fields_ = [("basic", BasicLimits), ("io", IoCounters), *[(n, SIZE_T) for n in
        ("process_memory", "job_memory", "peak_process", "peak_job")]]


class Accounting(C.Structure):
    _fields_ = [(n, C.c_longlong) for n in ("user", "kernel", "period_user", "period_kernel")] + [
        (n, DWORD) for n in ("faults", "total", "active", "terminated")]


class MemoryCounters(C.Structure):
    _fields_ = [("cb", DWORD), ("faults", DWORD)] + [(n, SIZE_T) for n in
        ("peak_ws", "working_set", "peak_paged", "paged", "peak_nonpaged", "nonpaged", "pagefile", "peak_pagefile", "private")]


def _api():
    if os.name != "nt":
        raise OSError("The hidden native session requires Windows.")
    kernel, user, psapi = C.WinDLL("kernel32", use_last_error=True), C.WinDLL("user32", use_last_error=True), C.WinDLL("psapi", use_last_error=True)
    signatures = {
        "CreateJobObjectW": ([C.c_void_p, W.LPCWSTR], HANDLE),
        "SetInformationJobObject": ([HANDLE, C.c_int, C.c_void_p, DWORD], W.BOOL),
        "QueryInformationJobObject": ([HANDLE, C.c_int, C.c_void_p, DWORD, C.c_void_p], W.BOOL),
        "AssignProcessToJobObject": ([HANDLE, HANDLE], W.BOOL),
        "IsProcessInJob": ([HANDLE, HANDLE, C.POINTER(W.BOOL)], W.BOOL),
        "CreateProcessW": ([W.LPCWSTR, W.LPWSTR, C.c_void_p, C.c_void_p, W.BOOL, DWORD,
            C.c_void_p, W.LPCWSTR, C.POINTER(StartupInfo), C.POINTER(ProcessInfo)], W.BOOL),
        "ResumeThread": ([HANDLE], DWORD), "CloseHandle": ([HANDLE], W.BOOL),
        "TerminateJobObject": ([HANDLE, W.UINT], W.BOOL), "TerminateProcess": ([HANDLE, W.UINT], W.BOOL),
        "WaitForSingleObject": ([HANDLE, DWORD], DWORD),
        "GetExitCodeProcess": ([HANDLE, C.POINTER(DWORD)], W.BOOL),
        "OpenProcess": ([DWORD, W.BOOL, DWORD], HANDLE),
        "GetProcessTimes": ([HANDLE, *[C.POINTER(W.FILETIME)] * 4], W.BOOL),
        "QueryFullProcessImageNameW": ([HANDLE, DWORD, W.LPWSTR, C.POINTER(DWORD)], W.BOOL),
        "GetProcessHandleCount": ([HANDLE, C.POINTER(DWORD)], W.BOOL),
        "ReadProcessMemory": ([HANDLE, C.c_void_p, C.c_void_p, SIZE_T, C.POINTER(SIZE_T)], W.BOOL),
    }
    for name, (args, result) in signatures.items():
        fn = getattr(kernel, name)
        fn.argtypes, fn.restype = args, result
    user.CreateDesktopW.argtypes, user.CreateDesktopW.restype = [W.LPCWSTR, C.c_void_p, C.c_void_p, DWORD, DWORD, C.c_void_p], HANDLE
    user.CloseDesktop.argtypes, user.CloseDesktop.restype = [HANDLE], W.BOOL
    psapi.GetProcessMemoryInfo.argtypes, psapi.GetProcessMemoryInfo.restype = [HANDLE, C.POINTER(MemoryCounters), DWORD], W.BOOL
    return kernel, user, psapi


def _check(value, action):
    if not value:
        raise OSError(C.get_last_error() if hasattr(C, "get_last_error") else 0, action)
    return value


class HiddenJob:
    """Retain process handles and kill-on-close membership before first resume."""
    def __init__(self):
        self.kernel, self.user, self.psapi = _api()
        self.desktop = self.job = None
        self.desktop_name = None
        self.show_window = 0
        self.processes = []
        self.threads = []
        self.name = "ClashHD-" + uuid.uuid4().hex
        self.events = []
        self.cleanup_errors = []
        self.last_cleanup = None

    def open(self):
        self.desktop = _check(self.user.CreateDesktopW(self.name, None, None, 0, 0x1ff, None), "CreateDesktopW")
        self.desktop_name = "winsta0\\" + self.name
        self.events.append("hidden_desktop_created")
        return self._open_job()

    def _open_job(self):
        try:
            self.job = _check(self.kernel.CreateJobObjectW(None, None), "CreateJobObjectW")
            limits = ExtendedLimits()
            limits.basic.flags = 0x2000  # KILL_ON_JOB_CLOSE, no breakaway.
            _check(self.kernel.SetInformationJobObject(self.job, 9, C.byref(limits), C.sizeof(limits)), "SetInformationJobObject")
            actual = ExtendedLimits()
            _check(self.kernel.QueryInformationJobObject(self.job, 9, C.byref(actual), C.sizeof(actual), None), "QueryInformationJobObject limits")
            if actual.basic.flags != 0x2000:
                raise ValueError("Job kill-on-close/no-breakaway limits were not read back exactly.")
            self.events.append("kill_on_close_job_verified")
        except BaseException as error:
            cleanup = self.close()
            if hasattr(error, "add_note"):
                error.add_note("Open-time owned cleanup: " + repr(cleanup))
            raise
        return self

    def identify(self, handle, pid):
        path, count = C.create_unicode_buffer(32768), DWORD(32768)
        _check(self.kernel.QueryFullProcessImageNameW(handle, 0, path, C.byref(count)), "QueryFullProcessImageNameW")
        times = [W.FILETIME() for _ in range(4)]
        _check(self.kernel.GetProcessTimes(handle, *[C.byref(t) for t in times]), "GetProcessTimes")
        member = W.BOOL()
        _check(self.kernel.IsProcessInJob(handle, self.job, C.byref(member)), "IsProcessInJob")
        if not member.value:
            raise ValueError("Retained process is not a member of the task-owned job.")
        return dict(pid=int(pid), image_path=path.value,
            creation_filetime=(times[0].dwHighDateTime << 32) | times[0].dwLowDateTime,
            task_job_member=True)

    def spawn(self, executable: Path, arguments: list[str], cwd: Path, environment: dict[str, str]):
        if not self.desktop_name or not self.job:
            raise RuntimeError("Hidden desktop and verified job must exist before process creation.")
        startup, info = StartupInfo(), ProcessInfo()
        startup.cb, startup.lpDesktop, startup.dwFlags, startup.wShowWindow = C.sizeof(startup), self.desktop_name, 1, self.show_window
        command = C.create_unicode_buffer(subprocess.list2cmdline([str(executable), *arguments]))
        block = C.create_unicode_buffer("\0".join(f"{k}={v}" for k, v in sorted(environment.items(), key=lambda p: p[0].upper())) + "\0\0")
        _check(self.kernel.CreateProcessW(str(executable), command, None, None, False,
            0x4 | 0x400 | 0x08000000, block, str(cwd), C.byref(startup), C.byref(info)), "CreateProcessW hidden suspended")
        self.processes.append((info.process, info.pid))
        self.threads.append(info.thread)
        self.events.append("process_created_suspended")
        try:
            _check(self.kernel.AssignProcessToJobObject(self.job, info.process), "AssignProcessToJobObject")
            identity = self.identify(info.process, info.pid)
            if os.path.normcase(identity["image_path"]) != os.path.normcase(str(executable.resolve())):
                raise ValueError("Created process image differs from the requested tool.")
            self.events.append("process_membership_and_generation_verified")
            if self.kernel.ResumeThread(info.thread) != 1:
                raise OSError(C.get_last_error() if hasattr(C, "get_last_error") else 0,
                              "ResumeThread did not resume exactly one suspension")
            self.events.append("process_resumed")
            return info.process, identity
        except BaseException:
            # This handle belongs only to the process just created by this task.
            if not self.kernel.TerminateProcess(info.process, 0x4844):
                self.cleanup_errors.append("Termination of the just-created process failed")
            if self.kernel.WaitForSingleObject(info.process, 5000) != 0:
                self.cleanup_errors.append("The just-created process did not terminate within its cleanup deadline")
            raise

    def adopt(self, pid: int, expected_path: Path, created_after: int):
        handle = _check(self.kernel.OpenProcess(0x1000 | 0x10 | 0x100000 | 0x400, False, pid), "OpenProcess owned debuggee")
        try:
            identity = self.identify(handle, pid)
            if (os.path.normcase(identity["image_path"]) != os.path.normcase(str(expected_path.resolve()))
                    or identity["creation_filetime"] < created_after):
                raise ValueError("Debuggee path or generation differs from this session.")
            self.processes.append((handle, pid))
            return handle, identity
        except BaseException:
            self.kernel.CloseHandle(handle)
            raise

    def alive(self, handle):
        result = self.kernel.WaitForSingleObject(handle, 0)
        if result not in (0, 258):
            raise C.WinError(C.get_last_error(), "WaitForSingleObject")
        return result == 258

    def telemetry(self, handle):
        memory, handles = MemoryCounters(), DWORD()
        memory.cb = C.sizeof(memory)
        _check(self.psapi.GetProcessMemoryInfo(handle, C.byref(memory), C.sizeof(memory)), "GetProcessMemoryInfo")
        _check(self.kernel.GetProcessHandleCount(handle, C.byref(handles)), "GetProcessHandleCount")
        return dict(working_set=int(memory.working_set), private_bytes=int(memory.private), handles=int(handles.value))

    def exit_code(self, handle):
        code = DWORD()
        _check(self.kernel.GetExitCodeProcess(handle, C.byref(code)), "GetExitCodeProcess")
        return int(code.value)

    def read(self, handle, address: int, count: int):
        if not (0x10000 <= address < 0x80000000 and 0 < count <= 3840 * 2160 and address + count <= 0x80000000):
            raise ValueError("Surface read exceeds the selected PE32/native-frame bounds.")
        target, received = C.create_string_buffer(count), SIZE_T()
        _check(self.kernel.ReadProcessMemory(handle, address, target, count, C.byref(received)), "ReadProcessMemory")
        if received.value != count:
            raise ValueError("Native surface read returned partial bytes.")
        return target.raw

    def close(self):
        if not any((self.desktop, self.job, self.processes, self.threads)) and self.last_cleanup is not None:
            return dict(self.last_cleanup)
        errors, drained = list(self.cleanup_errors), self.job is None and not self.processes
        if self.job:
            if not self.kernel.TerminateJobObject(self.job, 0x4844):
                errors.append("TerminateJobObject failed: " + str(C.get_last_error()))
            deadline = time.monotonic() + 5
            while True:
                accounting = Accounting()
                if not self.kernel.QueryInformationJobObject(self.job, 1, C.byref(accounting), C.sizeof(accounting), None):
                    errors.append("Job accounting query failed")
                    break
                if accounting.active == 0:
                    drained = True
                    break
                if time.monotonic() >= deadline:
                    errors.append("Owned job still has active processes")
                    break
                time.sleep(0.05)
        # An assignment failure may leave a task-created process outside the
        # job. Empty job accounting alone cannot prove that process is gone.
        for handle, process_id in self.processes:
            if self.kernel.WaitForSingleObject(handle, 5000) != 0:
                self.kernel.TerminateProcess(handle, 0x4844)
                if self.kernel.WaitForSingleObject(handle, 5000) != 0:
                    errors.append("Retained owned process remains unsignaled: " + str(process_id))
        for handle in [*self.threads, *[h for h, _ in self.processes], self.job]:
            if handle and not self.kernel.CloseHandle(handle):
                errors.append("CloseHandle failed")
        if self.desktop and not self.user.CloseDesktop(self.desktop):
            errors.append("CloseDesktop failed")
        self.threads, self.processes, self.job, self.desktop = [], [], None, None
        self.desktop_name = None
        self.last_cleanup = dict(task_job_drained=drained, all_handles_closed=not errors,
                    cleanup_verified=drained and not errors, errors=errors, events=list(self.events))
        return dict(self.last_cleanup)
