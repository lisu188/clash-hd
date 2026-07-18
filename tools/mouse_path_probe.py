#!/usr/bin/env python3
"""Move the OS cursor over a Clash95 client path and verify actual positions.

This is a dependency-free cross-check for the PowerShell mouse sweep in
run_cdb_menu_probe.ps1. It verifies the Win32 path requested by the automation;
it does not prove DirectInput consumed those moves.
"""

from __future__ import annotations

import argparse
import ctypes
import json
import subprocess
import sys
import time
from ctypes import wintypes
from pathlib import Path


user32 = ctypes.WinDLL("user32", use_last_error=True)


class RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class INPUT_UNION(ctypes.Union):
    _fields_ = [("mi", MOUSEINPUT)]


class INPUT(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("union", INPUT_UNION)]


WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

user32.EnumWindows.argtypes = [WNDENUMPROC, wintypes.LPARAM]
user32.EnumWindows.restype = wintypes.BOOL
user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user32.GetWindowThreadProcessId.restype = wintypes.DWORD
user32.IsWindowVisible.argtypes = [wintypes.HWND]
user32.IsWindowVisible.restype = wintypes.BOOL
user32.GetClientRect.argtypes = [wintypes.HWND, ctypes.POINTER(RECT)]
user32.GetClientRect.restype = wintypes.BOOL
user32.ClientToScreen.argtypes = [wintypes.HWND, ctypes.POINTER(POINT)]
user32.ClientToScreen.restype = wintypes.BOOL
user32.ScreenToClient.argtypes = [wintypes.HWND, ctypes.POINTER(POINT)]
user32.ScreenToClient.restype = wintypes.BOOL
user32.GetCursorPos.argtypes = [ctypes.POINTER(POINT)]
user32.GetCursorPos.restype = wintypes.BOOL
user32.SetCursorPos.argtypes = [ctypes.c_int, ctypes.c_int]
user32.SetCursorPos.restype = wintypes.BOOL
user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(RECT)]
user32.GetWindowRect.restype = wintypes.BOOL
user32.MoveWindow.argtypes = [
    wintypes.HWND,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    wintypes.BOOL,
]
user32.MoveWindow.restype = wintypes.BOOL
user32.SetWindowPos.argtypes = [
    wintypes.HWND,
    wintypes.HWND,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_uint,
]
user32.SetWindowPos.restype = wintypes.BOOL
user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
user32.ShowWindow.restype = wintypes.BOOL
user32.BringWindowToTop.argtypes = [wintypes.HWND]
user32.BringWindowToTop.restype = wintypes.BOOL
user32.SetForegroundWindow.argtypes = [wintypes.HWND]
user32.SetForegroundWindow.restype = wintypes.BOOL
user32.SendInput.argtypes = [wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int]
user32.SendInput.restype = wintypes.UINT
user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.PostMessageW.restype = wintypes.BOOL
user32.keybd_event.argtypes = [ctypes.c_ubyte, ctypes.c_ubyte, wintypes.DWORD, ctypes.c_void_p]
user32.keybd_event.restype = None
user32.GetSystemMetrics.argtypes = [ctypes.c_int]
user32.GetSystemMetrics.restype = ctypes.c_int
user32.IsWindow.argtypes = [wintypes.HWND]
user32.IsWindow.restype = wintypes.BOOL


ERROR_INVALID_WINDOW_HANDLE = 1400

WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202
MK_LBUTTON = 0x0001
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_ABSOLUTE = 0x8000
MOUSEEVENTF_VIRTUALDESK = 0x4000
SM_XVIRTUALSCREEN = 76
SM_YVIRTUALSCREEN = 77
SM_CXVIRTUALSCREEN = 78
SM_CYVIRTUALSCREEN = 79


def wincheck(ok: int, what: str) -> None:
    if not ok:
        raise ctypes.WinError(ctypes.get_last_error(), what)


def rect_size(rect: RECT) -> tuple[int, int]:
    return int(rect.right - rect.left), int(rect.bottom - rect.top)


def find_window_for_pid(pid: int) -> int | None:
    matches: list[tuple[int, int]] = []

    @WNDENUMPROC
    def callback(hwnd: int, _param: int) -> bool:
        window_pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(window_pid))
        if int(window_pid.value) != pid or not user32.IsWindowVisible(hwnd):
            return True
        rect = RECT()
        if user32.GetClientRect(hwnd, ctypes.byref(rect)):
            width, height = rect_size(rect)
            if width > 0 and height > 0:
                matches.append((width * height, int(hwnd)))
        return True

    user32.EnumWindows(callback, 0)
    if not matches:
        return None
    return max(matches)[1]


def wait_for_window(pid: int, timeout: float) -> int:
    deadline = time.time() + timeout
    while time.time() < deadline:
        hwnd = find_window_for_pid(pid)
        if hwnd:
            return hwnd
        time.sleep(0.1)
    raise TimeoutError(f"no visible window found for pid {pid}")


def client_rect_and_origin(hwnd: int) -> tuple[RECT, POINT]:
    rect = RECT()
    wincheck(user32.GetClientRect(hwnd, ctypes.byref(rect)), "GetClientRect")
    origin = POINT(0, 0)
    wincheck(user32.ClientToScreen(hwnd, ctypes.byref(origin)), "ClientToScreen")
    return rect, origin


class WindowLostError(RuntimeError):
    """The target window vanished and could not be re-acquired for the pid."""


def is_invalid_window_error(exc: BaseException) -> bool:
    """True for ERROR_INVALID_WINDOW_HANDLE, i.e. the handle was recreated."""
    return getattr(exc, "winerror", None) == ERROR_INVALID_WINDOW_HANDLE


def window_alive(hwnd: int) -> bool:
    return bool(hwnd) and bool(user32.IsWindow(hwnd))


class WindowTarget:
    """A pid-anchored window handle that is re-resolved at every input phase.

    Why this exists (2026-07-18 diagnosis): the GOG/DirectDraw wrapper destroys
    and recreates its top-level window across the intro->menu mode switch, and
    the window is transiently desktop-sized while the switch is in flight (a
    2560x1440 client was sampled at 20:41:19 on a run whose real client is
    800x600). Any handle cached across that boundary is stale, so the first
    Win32 call using it fails with WinError 1400 (ERROR_INVALID_WINDOW_HANDLE)
    - which is exactly how the 2026-07-18 short2 run died, as an unhandled
    traceback inside client_rect_and_origin with zero frames captured.

    Every geometry/input phase therefore goes through this object, which
    validates the cached handle with IsWindow, re-acquires it for the pid with
    a bounded retry/backoff when it died, and only fails closed (WindowLostError)
    once the retries are exhausted. Failing closed is preserved: the caller
    still reports path_verified false, it just does so with honest evidence
    instead of a crash.
    """

    def __init__(
        self,
        pid: int,
        reacquire_attempts: int = 12,
        reacquire_delay: float = 0.25,
    ) -> None:
        self.pid = int(pid)
        self.hwnd = 0
        self.previous_hwnd = 0
        self.reacquire_attempts = max(1, int(reacquire_attempts))
        self.reacquire_delay = max(0.0, float(reacquire_delay))
        self.reacquire_count = 0
        self.events: list[dict] = []
        self.stability: dict | None = None

    def record(self, kind: str, phase: str, **fields: object) -> None:
        event = {"kind": kind, "phase": phase, "hwnd": int(self.hwnd) or None}
        event.update(fields)
        self.events.append(event)

    def acquire(self, timeout: float, phase: str) -> int:
        """Resolve a visible window for the pid, waiting up to timeout seconds."""
        deadline = time.time() + max(0.0, float(timeout))
        while True:
            found = find_window_for_pid(self.pid)
            if found:
                # previous_hwnd survives invalidate() so a recreated window is
                # reported as a re-acquisition rather than a first acquisition.
                previous = self.hwnd or self.previous_hwnd
                self.hwnd = int(found)
                if previous and previous != self.hwnd:
                    self.reacquire_count += 1
                    self.record(
                        "window_reacquired",
                        phase,
                        previous_hwnd=int(previous),
                    )
                return self.hwnd
            if time.time() >= deadline:
                break
            time.sleep(0.1)
        self.record(
            "window_lost",
            phase,
            previous_hwnd=int(self.hwnd or self.previous_hwnd) or None,
        )
        raise WindowLostError(f"no visible window found for pid {self.pid} at {phase}")

    def invalidate(self, phase: str, reason: str) -> None:
        if self.hwnd:
            self.previous_hwnd = int(self.hwnd)
            self.record("window_handle_invalid", phase, reason=reason)
        self.hwnd = 0

    def ensure(self, phase: str) -> int:
        """Return a handle that is live right now, re-acquiring if it died."""
        if window_alive(self.hwnd):
            return self.hwnd
        if self.hwnd:
            self.invalidate(phase, "IsWindow returned false")
        return self.acquire(self.reacquire_attempts * self.reacquire_delay, phase)

    def geometry(self, phase: str) -> tuple[int, RECT, POINT]:
        """Read client geometry from a handle validated at read time.

        IsWindow can still go stale between the check and the read, so an
        ERROR_INVALID_WINDOW_HANDLE from the read itself is treated as another
        recreation and retried rather than raised at the caller.
        """
        last_error: BaseException | None = None
        for _ in range(self.reacquire_attempts):
            hwnd = self.ensure(phase)
            try:
                rect, origin = client_rect_and_origin(hwnd)
            except OSError as exc:
                if not is_invalid_window_error(exc):
                    raise
                last_error = exc
                self.invalidate(phase, str(exc))
                time.sleep(self.reacquire_delay)
                continue
            return hwnd, rect, origin
        self.record("window_lost", phase, reason=str(last_error))
        raise WindowLostError(
            f"client geometry unavailable for pid {self.pid} at {phase}: {last_error}"
        )

    def wait_stable(
        self,
        phase: str,
        samples: int = 2,
        poll_sec: float = 0.35,
        timeout: float = 8.0,
    ) -> dict:
        """Wait for the handle AND the client size to repeat across samples.

        This is the mode-switch settle gate, and it is a measurement rather
        than a sleep: input is only worth sending once the same window has
        reported the same client size on consecutive polls, which is precisely
        what is false while the wrapper is swapping display modes. Every
        sample is recorded so a run can be read honestly either way; a timeout
        is reported as stable=false and left to the caller's own gates rather
        than inventing a new hard failure.
        """
        required = max(1, int(samples))
        deadline = time.time() + max(0.0, float(timeout))
        observations: list[dict] = []
        streak: list[tuple[int, tuple[int, int]]] = []
        stable = False
        self.stability = {
            "stable": False,
            "required_consecutive_samples": required,
            "timeout_sec": float(timeout),
            "poll_sec": float(poll_sec),
            "samples": observations,
        }
        while True:
            hwnd, rect, _origin = self.geometry(phase)
            size = rect_size(rect)
            observations.append({"hwnd": int(hwnd), "client_size": [size[0], size[1]]})
            entry = (int(hwnd), size)
            if streak and streak[-1] == entry:
                streak.append(entry)
            else:
                streak = [entry]
            if len(streak) >= required:
                stable = True
                break
            if time.time() >= deadline:
                break
            time.sleep(max(0.0, float(poll_sec)))
        self.stability["stable"] = stable
        self.stability["samples_taken"] = len(observations)
        return self.stability


def default_points(width: int, height: int) -> list[tuple[int, int]]:
    return [
        (width // 2, height // 2),
        (120, 120),
        (320, 285),
        (480, 260),
        (max(0, width - 80), max(0, height - 80)),
        (width // 2, height // 2),
    ]


def parse_points(value: str | None, width: int, height: int) -> list[tuple[int, int]]:
    if not value:
        return default_points(width, height)
    points: list[tuple[int, int]] = []
    for item in value.split(";"):
        x_text, y_text = item.split(",", 1)
        points.append((int(x_text), int(y_text)))
    return points


def make_mouse_input(flags: int) -> INPUT:
    event = INPUT()
    event.type = 0
    event.union.mi.dwFlags = flags
    return event


def send_mouse_input(flags: int) -> int:
    event = make_mouse_input(flags)
    sent = user32.SendInput(1, ctypes.byref(event), ctypes.sizeof(INPUT))
    if sent != 1:
        raise ctypes.WinError(ctypes.get_last_error(), "SendInput")
    return int(sent)


def send_absolute_move(screen_x: int, screen_y: int) -> int:
    left = int(user32.GetSystemMetrics(SM_XVIRTUALSCREEN))
    top = int(user32.GetSystemMetrics(SM_YVIRTUALSCREEN))
    width = max(1, int(user32.GetSystemMetrics(SM_CXVIRTUALSCREEN)))
    height = max(1, int(user32.GetSystemMetrics(SM_CYVIRTUALSCREEN)))
    norm_x = int(round(((screen_x - left) * 65535) / max(1, width - 1)))
    norm_y = int(round(((screen_y - top) * 65535) / max(1, height - 1)))

    event = INPUT()
    event.type = 0
    event.union.mi.dx = norm_x
    event.union.mi.dy = norm_y
    event.union.mi.dwFlags = MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_VIRTUALDESK
    sent = user32.SendInput(1, ctypes.byref(event), ctypes.sizeof(INPUT))
    if sent != 1:
        raise ctypes.WinError(ctypes.get_last_error(), "SendInput absolute move")
    return int(sent)


def get_cursor_pos() -> POINT:
    point = POINT()
    wincheck(user32.GetCursorPos(ctypes.byref(point)), "GetCursorPos")
    return point


def send_relative_move(delta_x: int, delta_y: int) -> int:
    event = INPUT()
    event.type = 0
    event.union.mi.dx = int(delta_x)
    event.union.mi.dy = int(delta_y)
    event.union.mi.dwFlags = MOUSEEVENTF_MOVE
    sent = user32.SendInput(1, ctypes.byref(event), ctypes.sizeof(INPUT))
    if sent != 1:
        raise ctypes.WinError(ctypes.get_last_error(), "SendInput relative move")
    return int(sent)


def clamp_delta(value: int, limit: int) -> int:
    if value > limit:
        return limit
    if value < -limit:
        return -limit
    return value


def send_relative_move_to(
    screen_x: int,
    screen_y: int,
    max_steps: int = 24,
    step_limit: int = 64,
    step_sleep: float = 0.015,
) -> int:
    sent_total = 0
    for _ in range(max_steps):
        current = get_cursor_pos()
        delta_x = int(screen_x - current.x)
        delta_y = int(screen_y - current.y)
        if abs(delta_x) <= 1 and abs(delta_y) <= 1:
            break

        step_x = clamp_delta(delta_x, step_limit)
        step_y = clamp_delta(delta_y, step_limit)
        if step_x == 0 and delta_x != 0:
            step_x = 1 if delta_x > 0 else -1
        if step_y == 0 and delta_y != 0:
            step_y = 1 if delta_y > 0 else -1

        send_relative_move(step_x, step_y)
        sent_total += 1
        time.sleep(step_sleep)
    return sent_total


def send_relative_delta_path(
    delta_x: int,
    delta_y: int,
    max_steps: int = 128,
    step_limit: int = 24,
    step_sleep: float = 0.02,
) -> int:
    sent_total = 0
    remaining_x = int(delta_x)
    remaining_y = int(delta_y)
    while sent_total < max_steps and (remaining_x != 0 or remaining_y != 0):
        step_x = clamp_delta(remaining_x, step_limit)
        step_y = clamp_delta(remaining_y, step_limit)
        if step_x == 0 and remaining_x != 0:
            step_x = 1 if remaining_x > 0 else -1
        if step_y == 0 and remaining_y != 0:
            step_y = 1 if remaining_y > 0 else -1

        send_relative_move(step_x, step_y)
        remaining_x -= step_x
        remaining_y -= step_y
        sent_total += 1
        time.sleep(step_sleep)
    return sent_total


def move_cursor(
    screen_x: int,
    screen_y: int,
    mode: str,
    relative_max_steps: int,
    relative_step_limit: int,
    relative_step_sleep: float,
) -> str:
    if mode == "none":
        return "none"
    if mode == "setcursor":
        wincheck(user32.SetCursorPos(screen_x, screen_y), "SetCursorPos")
        return "setcursor"
    if mode == "sendinput-absolute":
        send_absolute_move(screen_x, screen_y)
        return "sendinput-absolute"
    if mode == "sendinput-relative":
        steps = send_relative_move_to(
            screen_x,
            screen_y,
            max_steps=relative_max_steps,
            step_limit=relative_step_limit,
            step_sleep=relative_step_sleep,
        )
        return f"sendinput-relative:{steps}"
    if mode == "sendinput-client-delta":
        return "sendinput-client-delta:deferred"

    try:
        wincheck(user32.SetCursorPos(screen_x, screen_y), "SetCursorPos")
        return "setcursor"
    except OSError:
        send_absolute_move(screen_x, screen_y)
        return "sendinput-absolute"


user32.GetForegroundWindow.restype = wintypes.HWND


def make_lparam(client_x: int, client_y: int) -> int:
    return ((client_y & 0xFFFF) << 16) | (client_x & 0xFFFF)


def post_left_button(hwnd: int, message: int, wparam: int, client_x: int, client_y: int) -> bool:
    return bool(user32.PostMessageW(hwnd, message, wparam, make_lparam(client_x, client_y)))


def sample_cursor(
    hwnd: int,
    phase: str,
    requested_client: tuple[int, int],
    requested_screen: tuple[int, int],
) -> dict:
    actual = POINT()
    try:
        wincheck(user32.GetCursorPos(ctypes.byref(actual)), "GetCursorPos")
    except OSError as exc:
        return {
            "phase": phase,
            "requested_client": [int(requested_client[0]), int(requested_client[1])],
            "requested_screen": [int(requested_screen[0]), int(requested_screen[1])],
            "actual_screen": None,
            "actual_client": None,
            "screen_error": [999999, 999999],
            "client_error": [999999, 999999],
            "cursor_error": str(exc),
        }
    actual_client = POINT(actual.x, actual.y)
    try:
        wincheck(user32.ScreenToClient(hwnd, ctypes.byref(actual_client)), "ScreenToClient")
    except OSError as exc:
        return {
            "phase": phase,
            "requested_client": [int(requested_client[0]), int(requested_client[1])],
            "requested_screen": [int(requested_screen[0]), int(requested_screen[1])],
            "actual_screen": [int(actual.x), int(actual.y)],
            "actual_client": None,
            "screen_error": [int(actual.x - requested_screen[0]), int(actual.y - requested_screen[1])],
            "client_error": [999999, 999999],
            "cursor_error": str(exc),
        }
    return {
        "phase": phase,
        "requested_client": [int(requested_client[0]), int(requested_client[1])],
        "requested_screen": [int(requested_screen[0]), int(requested_screen[1])],
        "actual_screen": [int(actual.x), int(actual.y)],
        "actual_client": [int(actual_client.x), int(actual_client.y)],
        "screen_error": [int(actual.x - requested_screen[0]), int(actual.y - requested_screen[1])],
        "client_error": [int(actual_client.x - requested_client[0]), int(actual_client.y - requested_client[1])],
    }


def send_mapped_click(
    hwnd: int,
    client_x: int,
    client_y: int,
    screen_x: int,
    screen_y: int,
    mode: str,
    hold_sec: float,
) -> dict:
    events = [
        sample_cursor(hwnd, "before_click", (client_x, client_y), (screen_x, screen_y)),
    ]
    result: dict = {"mode": mode, "hold_ms": int(round(hold_sec * 1000)), "events": events}

    if mode in {"sendinput", "both"}:
        result["sendinput_down"] = send_mouse_input(MOUSEEVENTF_LEFTDOWN)
        time.sleep(hold_sec)
        events.append(sample_cursor(hwnd, "after_sendinput_down", (client_x, client_y), (screen_x, screen_y)))
        result["sendinput_up"] = send_mouse_input(MOUSEEVENTF_LEFTUP)
        time.sleep(0.04)
        events.append(sample_cursor(hwnd, "after_sendinput_up", (client_x, client_y), (screen_x, screen_y)))

    if mode in {"postmessage", "both"}:
        result["postmessage_down"] = post_left_button(hwnd, WM_LBUTTONDOWN, MK_LBUTTON, client_x, client_y)
        time.sleep(hold_sec)
        events.append(sample_cursor(hwnd, "after_postmessage_down", (client_x, client_y), (screen_x, screen_y)))
        result["postmessage_up"] = post_left_button(hwnd, WM_LBUTTONUP, 0, client_x, client_y)
        time.sleep(0.04)
        events.append(sample_cursor(hwnd, "after_postmessage_up", (client_x, client_y), (screen_x, screen_y)))

    events.append(sample_cursor(hwnd, "after_click", (client_x, client_y), (screen_x, screen_y)))
    return result


def send_space_pulses(count: int, interval: float) -> None:
    for _ in range(count):
        user32.keybd_event(0x20, 0, 0, None)
        time.sleep(0.05)
        user32.keybd_event(0x20, 0, 0x0002, None)
        time.sleep(interval)


def sample_abs_error(sample: dict) -> int:
    values: list[int] = []
    for key in ("screen_error", "client_error"):
        for value in sample.get(key) or []:
            try:
                values.append(abs(int(value)))
            except (TypeError, ValueError):
                pass
    return max(values or [0])


def click_sample_abs_error(click: dict) -> int:
    return max((sample_abs_error(sample) for sample in click.get("events") or []), default=0)


def should_stop_click_repeat(click: dict, stop_on_drift: bool) -> bool:
    return stop_on_drift and click_sample_abs_error(click) > 1


def move_path(
    target: WindowTarget,
    points: list[tuple[int, int]],
    interval: float,
    click: bool,
    click_mode: str,
    move_mode: str,
    click_hold_sec: float,
    click_repeat: int,
    stop_click_repeat_on_drift: bool,
    client_delta_origin: tuple[int, int],
    relative_max_steps: int,
    relative_step_limit: int,
    relative_step_sleep: float,
) -> dict:
    hwnd, rect, origin = target.geometry("move-path")
    width, height = rect_size(rect)
    rows = []
    window_lost = False
    window_lost_reason = None
    logical_x, logical_y = client_delta_origin
    for index, (client_x, client_y) in enumerate(points):
        # Re-validate before every point: the wrapper can recreate (and move)
        # its window between two points of the same path, which shifts the
        # client origin. Recomputing the screen target from the fresh origin
        # keeps the sampled drift honest instead of measuring against a window
        # that no longer exists.
        try:
            step_hwnd, _step_rect, step_origin = target.geometry(f"point-{index}")
        except WindowLostError as exc:
            window_lost = True
            window_lost_reason = str(exc)
            break
        window_reacquired = step_hwnd != hwnd
        hwnd = step_hwnd
        origin = step_origin
        screen_x = int(origin.x + client_x)
        screen_y = int(origin.y + client_y)
        logical_delta = [0, 0]
        if move_mode == "sendinput-client-delta":
            logical_delta = [int(client_x - logical_x), int(client_y - logical_y)]
            steps = send_relative_delta_path(
                logical_delta[0],
                logical_delta[1],
                max_steps=relative_max_steps,
                step_limit=relative_step_limit,
                step_sleep=relative_step_sleep,
            )
            logical_x, logical_y = client_x, client_y
            move_method = f"sendinput-client-delta:{steps}"
        else:
            move_method = move_cursor(
                screen_x,
                screen_y,
                move_mode,
                relative_max_steps,
                relative_step_limit,
                relative_step_sleep,
            )
        time.sleep(0.05)
        sample = sample_cursor(hwnd, "after_move", (client_x, client_y), (screen_x, screen_y))
        row = {
            "index": index,
            "client": [client_x, client_y],
            "hwnd": int(hwnd),
            "window_reacquired": bool(window_reacquired),
            "move_mode": move_mode,
            "move_method": move_method,
            "logical_delta": logical_delta,
            "logical_estimated_client": [client_x, client_y] if move_mode == "sendinput-client-delta" else None,
            "requested_screen": [screen_x, screen_y],
            "actual_screen": sample["actual_screen"],
            "actual_client": sample["actual_client"],
            "error": sample["screen_error"],
            "client_error": sample["client_error"],
            "samples": [sample],
            "clicks": [],
            "click_repeat_stop_reason": None,
            "click_repeat_stop_error": None,
            "click_repeat_stop_index": None,
        }
        if click:
            for repeat_index in range(click_repeat):
                click_map = send_mapped_click(
                    hwnd,
                    client_x,
                    client_y,
                    screen_x,
                    screen_y,
                    click_mode,
                    click_hold_sec,
                )
                click_map["repeat_index"] = repeat_index
                row["clicks"].append(click_map)
                row["samples"].extend(click_map["events"])
                repeat_error = click_sample_abs_error(click_map)
                if should_stop_click_repeat(click_map, stop_click_repeat_on_drift):
                    row["click_repeat_stop_reason"] = "sample_drift_after_click"
                    row["click_repeat_stop_error"] = repeat_error
                    row["click_repeat_stop_index"] = repeat_index
                    break
                time.sleep(0.04)
        rows.append(row)
        time.sleep(interval)
    points_completed = len(rows)
    all_points_visited = points_completed == len(points)
    max_abs_error = max((max(abs(row["error"][0]), abs(row["error"][1])) for row in rows), default=0)
    samples = [sample for row in rows for sample in row["samples"]]
    max_sample_abs_error = max(
        (
            max(
                abs(sample["screen_error"][0]),
                abs(sample["screen_error"][1]),
                abs(sample["client_error"][0]),
                abs(sample["client_error"][1]),
            )
            for sample in samples
        ),
        default=0,
    )
    return {
        "hwnd": hwnd,
        "client_size": [width, height],
        "client_origin_screen": [int(origin.x), int(origin.y)],
        "window_lost": window_lost,
        "window_lost_reason": window_lost_reason,
        "window_reacquire_count": target.reacquire_count,
        "window_events": target.events,
        "points_requested": len(points),
        "points_completed": points_completed,
        "all_points_visited": all_points_visited,
        "points": rows,
        "max_abs_error": max_abs_error,
        "max_sample_abs_error": max_sample_abs_error,
        "click_event_count": sum(len(row["clicks"]) for row in rows),
        "click_repeat_requested": click_repeat,
        "click_repeat_stop_observed": any(row["click_repeat_stop_reason"] for row in rows),
        "click_repeat_stop_reasons": [
            row["click_repeat_stop_reason"]
            for row in rows
            if row["click_repeat_stop_reason"]
        ],
        # Fail closed: a path that lost its window, or that never visited every
        # requested point, is not a verified path no matter how small the drift
        # measured on the points it did reach.
        "path_verified": all_points_visited and not window_lost and max_abs_error <= 1,
        "click_path_verified": (
            all_points_visited and not window_lost and max_sample_abs_error <= 1
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Move and verify a Win32 mouse path over a Clash95 client window.")
    parser.add_argument("--exe", type=Path, help="optional executable to launch")
    parser.add_argument("--workdir", type=Path, default=Path(r"C:\Clash"))
    parser.add_argument("--pid", type=int, help="existing process id to target")
    parser.add_argument("--window-timeout", type=float, default=10.0)
    parser.add_argument("--settle-sec", type=float, default=1.0)
    parser.add_argument("--interval-ms", type=int, default=500)
    parser.add_argument("--points", help="semicolon-separated client points, e.g. 400,300;120,120")
    parser.add_argument("--move-window", nargs=2, type=int, metavar=("X", "Y"))
    parser.add_argument("--space-pulses", type=int, default=0)
    parser.add_argument("--space-interval-ms", type=int, default=500)
    parser.add_argument("--click", action="store_true")
    parser.add_argument(
        "--move-mode",
        choices=("setcursor", "sendinput-absolute", "sendinput-relative", "sendinput-client-delta", "auto", "none"),
        default="setcursor",
        help="cursor movement API to use before sampling/clicking",
    )
    parser.add_argument(
        "--client-delta-origin",
        default="1,1",
        help="logical x,y origin for sendinput-client-delta mode",
    )
    parser.add_argument("--relative-max-steps", type=int, default=128, help="maximum relative move chunks")
    parser.add_argument("--relative-step-limit", type=int, default=24, help="maximum pixels per relative move chunk")
    parser.add_argument("--relative-step-sleep-ms", type=int, default=20, help="sleep between relative move chunks")
    parser.add_argument(
        "--click-mode",
        choices=("sendinput", "postmessage", "both"),
        default="sendinput",
        help="forced click mechanism to map at each client point",
    )
    parser.add_argument("--click-hold-ms", type=int, default=120, help="button-down hold time for forced clicks")
    parser.add_argument("--click-repeat", type=int, default=1, help="number of forced clicks at each point")
    parser.add_argument(
        "--stop-click-repeat-on-drift",
        action="store_true",
        help="stop repeated clicks after sampled cursor/client drift during transition-safe intro prep",
    )
    parser.add_argument(
        "--window-stable-samples",
        type=int,
        default=2,
        help="consecutive samples that must report the same hwnd and client size "
        "before input is sent (mode-switch settle gate)",
    )
    parser.add_argument("--window-stable-poll-ms", type=int, default=350, help="delay between settle-gate samples")
    parser.add_argument(
        "--window-stable-timeout-sec",
        type=float,
        default=8.0,
        help="maximum wait for the settle gate; a timeout is reported, not silently ignored",
    )
    parser.add_argument(
        "--window-reacquire-attempts",
        type=int,
        default=12,
        help="bounded retries used to re-acquire a window the wrapper recreated",
    )
    parser.add_argument("--window-reacquire-delay-ms", type=int, default=250, help="delay between re-acquire attempts")
    parser.add_argument("--kill-owned", action="store_true", help="terminate the launched process after the probe")
    parser.add_argument("--json", type=Path, help="write JSON result")
    return parser.parse_args()


def emit_result(result: dict, json_path: Path | None) -> None:
    text = json.dumps(result, indent=2)
    if json_path:
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(text, encoding="ascii")
    print(text)


def main() -> int:
    args = parse_args()
    process: subprocess.Popen | None = None
    if args.exe:
        process = subprocess.Popen([str(args.exe)], cwd=str(args.workdir))
        pid = int(process.pid)
    elif args.pid:
        pid = int(args.pid)
    else:
        raise SystemExit("provide --exe or --pid")

    target = WindowTarget(
        pid,
        reacquire_attempts=args.window_reacquire_attempts,
        reacquire_delay=args.window_reacquire_delay_ms / 1000.0,
    )
    try:
        hwnd = target.acquire(args.window_timeout, "initial")
        user32.ShowWindow(hwnd, 5)
        if args.move_window:
            # Reposition asynchronously and without resizing. MoveWindow(bRepaint=
            # True) sends a synchronous WM_* to the target window; a game stuck in
            # a modal input loop (e.g. the battle command screen) never pumps its
            # queue, so the call blocks forever. SWP_ASYNCWINDOWPOS posts the
            # request instead of sending it. SWP_NOSIZE preserves the window size
            # (the surfdump present proxy already sized it to the mode resolution).
            SWP_NOSIZE = 0x0001
            SWP_NOZORDER = 0x0004
            SWP_NOACTIVATE = 0x0010
            SWP_ASYNCWINDOWPOS = 0x4000
            user32.SetWindowPos(
                hwnd, None, args.move_window[0], args.move_window[1], 0, 0,
                SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE | SWP_ASYNCWINDOWPOS,
            )
            time.sleep(0.15)
        hwnd = target.ensure("foreground")
        user32.BringWindowToTop(hwnd)
        user32.SetForegroundWindow(hwnd)
        foreground_verified = (user32.GetForegroundWindow() == hwnd)
        time.sleep(args.settle_sec)

        # Settle gate BEFORE any input: the intro->menu mode switch recreates
        # and resizes the window, and stimuli aimed at the pre-switch handle are
        # thrown away (or crash, pre-fix). Wait for the same handle to report
        # the same client size twice in a row instead of sleeping and hoping.
        def settle(phase: str) -> dict:
            return target.wait_stable(
                phase,
                samples=args.window_stable_samples,
                poll_sec=args.window_stable_poll_ms / 1000.0,
                timeout=args.window_stable_timeout_sec,
            )

        stability_gates = [settle("pre-input")]

        if args.space_pulses:
            target.ensure("space-pulses")
            send_space_pulses(args.space_pulses, args.space_interval_ms / 1000.0)
            # The space pulses ARE the intro-skip stimulus, so they are what
            # triggers the display-mode switch, and the window transiently
            # resizes to the desktop while it is in flight (observed 800x600 ->
            # 2560x1440 -> 800x600 on 2026-07-18, which is how a bogus client
            # size reached the geometry read below). Settle again afterwards so
            # the client size the path is measured against is the real one.
            stability_gates.append(settle("post-space-pulses"))

        # The effective gate is the last one taken; window_stability keeps that
        # shape so existing readers of .stable stay correct.
        stability = stability_gates[-1]
        hwnd, rect, _origin = target.geometry("client-size")
        width, height = rect_size(rect)
        points = parse_points(args.points, width, height)
        client_delta_origin_points = parse_points(args.client_delta_origin, width, height)
        if len(client_delta_origin_points) != 1:
            raise SystemExit("--client-delta-origin expects one x,y point")
        result = move_path(
            target,
            points,
            args.interval_ms / 1000.0,
            args.click,
            args.click_mode,
            args.move_mode,
            args.click_hold_ms / 1000.0,
            args.click_repeat,
            args.stop_click_repeat_on_drift,
            client_delta_origin_points[0],
            args.relative_max_steps,
            args.relative_step_limit,
            args.relative_step_sleep_ms / 1000.0,
        )
        result.update({
            "pid": pid,
            "exe": str(args.exe) if args.exe else None,
            "foreground_verified": bool(foreground_verified),
            "window_stability": stability,
            "window_stability_gates": stability_gates,
        })
        emit_result(result, args.json)
        return 0 if result["path_verified"] else 2
    except WindowLostError as exc:
        # Fail closed with evidence instead of an unhandled traceback: the
        # harness reads this JSON, and "the wrapper recreated/destroyed the
        # window and it never came back" is a materially different diagnosis
        # from "the probe crashed", which is all the 2026-07-18 run could say.
        emit_result(
            {
                "pid": pid,
                "exe": str(args.exe) if args.exe else None,
                "path_verified": False,
                "click_path_verified": False,
                "window_lost": True,
                "window_lost_reason": str(exc),
                "window_reacquire_count": target.reacquire_count,
                "window_events": target.events,
                "window_stability": target.stability,
                "points": [],
                "click_event_count": 0,
                "click_repeat_stop_observed": False,
                "click_repeat_stop_reasons": [],
                "max_abs_error": None,
                "max_sample_abs_error": None,
            },
            args.json,
        )
        return 4
    finally:
        if process and args.kill_owned:
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=3)


if __name__ == "__main__":
    if sys.platform != "win32":
        raise SystemExit("mouse_path_probe.py requires Windows")
    raise SystemExit(main())
