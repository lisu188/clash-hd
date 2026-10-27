"""Owned-window operations for a separately approved visible diagnostic only."""
from __future__ import annotations

import ctypes as C
from ctypes import wintypes as W
import struct

from hd_multires_win32 import HiddenJob, _check


class DefaultDesktopJob(HiddenJob):
    """Same suspended/job/handle ownership as hidden sessions, default desktop."""
    def open(self):
        self.desktop_name = "winsta0\\default"
        self.show_window = 1
        self.events.append("approved_default_desktop_selected")
        return self._open_job()


class OwnedWindow:
    def __init__(self, retained_process_guard):
        self.retained_process_guard = retained_process_guard
        self.user = C.WinDLL("user32", use_last_error=True)
        self.gdi = C.WinDLL("gdi32", use_last_error=True)
        signatures = {
            "IsWindow": ([W.HWND], W.BOOL),
            "GetWindowThreadProcessId": ([W.HWND, C.POINTER(W.DWORD)], W.DWORD),
            "GetWindowRect": ([W.HWND, C.POINTER(W.RECT)], W.BOOL),
            "ShowWindow": ([W.HWND, C.c_int], W.BOOL),
            "SetForegroundWindow": ([W.HWND], W.BOOL),
            "GetForegroundWindow": ([], W.HWND),
            "GetWindowDC": ([W.HWND], W.HDC),
            "ReleaseDC": ([W.HWND, W.HDC], C.c_int),
            "PrintWindow": ([W.HWND, W.HDC, W.UINT], W.BOOL),
        }
        for name, (args, result) in signatures.items():
            fn = getattr(self.user, name)
            fn.argtypes, fn.restype = args, result
        signatures = {
            "CreateCompatibleDC": ([W.HDC], W.HDC),
            "CreateCompatibleBitmap": ([W.HDC, C.c_int, C.c_int], W.HBITMAP),
            "SelectObject": ([W.HDC, W.HGDIOBJ], W.HGDIOBJ),
            "DeleteObject": ([W.HGDIOBJ], W.BOOL),
            "DeleteDC": ([W.HDC], W.BOOL),
            "GetDIBits": ([W.HDC, W.HBITMAP, W.UINT, W.UINT, C.c_void_p, C.c_void_p, W.UINT], C.c_int),
        }
        for name, (args, result) in signatures.items():
            fn = getattr(self.gdi, name)
            fn.argtypes, fn.restype = args, result

    def verify(self, hwnd: int, candidate_pid: int):
        self.retained_process_guard()
        if not hwnd or not self.user.IsWindow(hwnd):
            raise ValueError("The candidate did not supply a live owned window.")
        actual = W.DWORD()
        _check(self.user.GetWindowThreadProcessId(hwnd, C.byref(actual)), "GetWindowThreadProcessId")
        if actual.value != candidate_pid:
            raise ValueError("Window ownership differs from the retained candidate PID.")
        self.retained_process_guard()
        return True

    def activate(self, hwnd: int, candidate_pid: int):
        self.verify(hwnd, candidate_pid)
        self.user.ShowWindow(hwnd, 1)
        requested = bool(self.user.SetForegroundWindow(hwnd))
        self.verify(hwnd, candidate_pid)
        return dict(hwnd=hwnd, pid=candidate_pid, activation_requested=requested,
            foreground_verified=int(self.user.GetForegroundWindow() or 0) == hwnd,
            input_injected=False)

    def capture(self, hwnd: int, candidate_pid: int):
        """PrintWindow only: never read the desktop or another window's pixels."""
        self.verify(hwnd, candidate_pid)
        rect = W.RECT()
        _check(self.user.GetWindowRect(hwnd, C.byref(rect)), "GetWindowRect")
        width, height = rect.right - rect.left, rect.bottom - rect.top
        if not (0 < width <= 4096 and 0 < height <= 2304):
            raise ValueError("Owned-window capture exceeds the declared canvas/frame bound.")
        source = _check(self.user.GetWindowDC(hwnd), "GetWindowDC owned window")
        memory = bitmap = previous = None
        errors = []
        try:
            memory = _check(self.gdi.CreateCompatibleDC(source), "CreateCompatibleDC")
            bitmap = _check(self.gdi.CreateCompatibleBitmap(source, width, height), "CreateCompatibleBitmap")
            previous = _check(self.gdi.SelectObject(memory, bitmap), "SelectObject capture bitmap")
            self.verify(hwnd, candidate_pid)
            _check(self.user.PrintWindow(hwnd, memory, 2), "PrintWindow owned window")
            self.verify(hwnd, candidate_pid)
            _check(self.gdi.SelectObject(memory, previous), "Restore selected capture bitmap")
            previous = None
            count = width * height * 4
            header = struct.pack("<IiiHHIIiiII", 40, width, height, 1, 32, 0, count, 0, 0, 0, 0)
            info, pixels = C.create_string_buffer(header), C.create_string_buffer(count)
            if self.gdi.GetDIBits(memory, bitmap, 0, height, pixels, info, 0) != height:
                raise ValueError("Owned-window capture returned incomplete pixel rows.")
            payload = struct.pack("<2sIHHI", b"BM", 54 + count, 0, 0, 54) + header + pixels.raw
        finally:
            if previous and not self.gdi.SelectObject(memory, previous): errors.append("restore bitmap")
            if bitmap and not self.gdi.DeleteObject(bitmap): errors.append("delete bitmap")
            if memory and not self.gdi.DeleteDC(memory): errors.append("delete memory DC")
            if not self.user.ReleaseDC(hwnd, source): errors.append("release owned window DC")
        if errors:
            raise OSError("Owned capture resource cleanup failed: " + ", ".join(errors))
        return payload, dict(width=width, height=height, method="PrintWindow_owned_window",
            visual_correctness_verified=False, tearing_checked=False)
