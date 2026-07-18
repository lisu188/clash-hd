#!/usr/bin/env python3
"""Steer the Clash95 ENGINE cursor with pulse-mode relative input and click.

Why this exists (2026-07-17 diagnosis): the game's menu reads its mouse
position from the DirectInput accumulator, not the Windows cursor.
SetCursorPos is invisible to DirectInput, absolute SendInput moves misscale on
this 2-monitor virtual desktop, and PostMessage clicks/keys are ignored by the
menu widget path. The only automated input the menu consumes is the
battle-lane-proven pulse technique (tools/raw_sendinput_click.py --move-mode
pulse): ONE relative MOUSEEVENTF_MOVE per ~28ms input poll. Each poll displays
the engine cursor at roughly gain*delta (menu gain measured ~4.1-4.9 on this
machine) and then resets the accumulator, so the position only persists while
the pulse stream continues; the button must be pressed and held WHILE pulsing.

This tool aims the engine cursor at engine-space targets using screen-grab
feedback (the engine draws its cursor, so frame diffs give its position),
clicks while pulsing, and verifies each step by frame transition. It reports
honest per-step evidence and never claims OS-cursor drift semantics: the
proof metric is the aimed engine position error plus the observed frame
transition, with the input proof class kept diagnostic (not manual DI proof).

Dependencies: pillow + numpy (same interpreter that runs the soak harness).
"""

from __future__ import annotations

import argparse
import ctypes
import json
import time
from ctypes import wintypes
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageGrab

user32 = ctypes.WinDLL("user32", use_last_error=True)
user32.SetProcessDPIAware()

INPUT_MECHANISM = "pulse-relative-engine-aim"
ENGINE_MODEL = (
    "engine cursor = gain*delta per input poll while one relative pulse per ~28ms "
    "is streamed; accumulator resets each poll; button held while pulsing"
)


class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long), ("right", ctypes.c_long), ("bottom", ctypes.c_long)]


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG), ("mouseData", wintypes.DWORD),
                ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD), ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))]


class INPUT_UNION(ctypes.Union):
    _fields_ = [("mi", MOUSEINPUT)]


class INPUT(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("union", INPUT_UNION)]


WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
user32.EnumWindows.argtypes = [WNDENUMPROC, wintypes.LPARAM]
user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user32.SendInput.argtypes = [wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int]

MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004

MENU_EXIT_ZONE = (245, 258, 360, 310)
MENU_NONBLACK_RANGE = (50.0, 75.0)


def find_window(pid: int) -> int | None:
    result: list[int] = []

    @WNDENUMPROC
    def cb(hwnd, _):
        wpid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(wpid))
        if wpid.value == pid and user32.IsWindowVisible(hwnd):
            r = RECT()
            if user32.GetClientRect(hwnd, ctypes.byref(r)) and r.right > r.left and r.bottom > r.top:
                result.append(int(hwnd))
                return False
        return True

    user32.EnumWindows(cb, 0)
    return result[0] if result else None


def client_geometry(hwnd: int) -> tuple[int, int, int, int]:
    r = RECT()
    user32.GetClientRect(hwnd, ctypes.byref(r))
    pt = POINT(0, 0)
    user32.ClientToScreen(hwnd, ctypes.byref(pt))
    return int(pt.x), int(pt.y), int(r.right - r.left), int(r.bottom - r.top)


user32.GetForegroundWindow.restype = wintypes.HWND
user32.FindWindowW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR]
user32.FindWindowW.restype = wintypes.HWND


def focus(hwnd: int) -> bool:
    """Bring the game window to the foreground and verify it.

    The game's DirectInput mouse is foreground-mode, so injected pulses only
    reach it while its window is the foreground window. Plain BringWindowToTop
    + SetForegroundWindow is used here (this is what the working 2026-07-17
    tool navigation used); the harder dead-poll case is handled by
    wake_foreground's activation cycle, not by AttachThreadInput/Alt tricks
    which were observed to destabilize the game during the intro.
    """
    for _ in range(4):
        if user32.GetForegroundWindow() == hwnd:
            return True
        user32.BringWindowToTop(hwnd)
        user32.SetForegroundWindow(hwnd)
        time.sleep(0.12)
    return user32.GetForegroundWindow() == hwnd


def send_rel(dx: int, dy: int) -> None:
    ev = INPUT()
    ev.type = 0
    ev.union.mi.dx = int(dx)
    ev.union.mi.dy = int(dy)
    ev.union.mi.dwFlags = MOUSEEVENTF_MOVE
    user32.SendInput(1, ctypes.byref(ev), ctypes.sizeof(INPUT))


def send_button(flag: int) -> None:
    ev = INPUT()
    ev.type = 0
    ev.union.mi.dwFlags = flag
    user32.SendInput(1, ctypes.byref(ev), ctypes.sizeof(INPUT))


def grab(hwnd: int) -> np.ndarray | None:
    ox, oy, w, h = client_geometry(hwnd)
    if w <= 0 or h <= 0:
        return None
    # ImageGrab.grab can transiently raise OSError("screen grab failed")
    # during wrapper display transitions; retry briefly rather than treating
    # it as a lost window.
    for attempt in range(4):
        try:
            img = ImageGrab.grab(bbox=(ox, oy, ox + w, oy + h), all_screens=True)
            break
        except OSError:
            time.sleep(0.25)
    else:
        return None
    if img.size != (800, 600):
        img = img.resize((800, 600), Image.NEAREST)
    return np.asarray(img.convert("RGB"), dtype=np.int16)


def wake_foreground(hwnd: int) -> bool:
    """Focus AWAY then back to force the engine to re-acquire DirectInput.

    The menu can initialize with a dead mouse poll when its window was not the
    active window at init. A plain SetForegroundWindow while the window is
    already foreground does nothing, so this deliberately activates the
    taskbar first, then the game, producing the WM_ACTIVATEAPP transition the
    engine needs. Never minimizes (minimize/restore intermittently loses the
    wrapper window)."""
    tray = user32.FindWindowW("Shell_TrayWnd", None)
    if tray:
        user32.SetForegroundWindow(tray)
        time.sleep(0.4)
    focus(hwnd)
    time.sleep(0.4)
    return user32.GetForegroundWindow() == hwnd


def grab_retry(pid: int, hwnd: int, attempts: int = 5) -> tuple[int, np.ndarray | None]:
    for _ in range(attempts):
        found = find_window(pid)
        if found:
            hwnd = found
            frame = grab(hwnd)
            if frame is not None:
                return hwnd, frame
        time.sleep(0.6)
    return hwnd, None


def nonblack_percent(arr: np.ndarray) -> float:
    return float((arr.max(axis=2) > 12).mean() * 100.0)


def unique_sample_colors(arr: np.ndarray) -> int:
    sample = arr[::4, ::4, :].reshape(-1, 3)
    return int(np.unique(sample, axis=0).shape[0])


def looks_like_map(arr: np.ndarray, min_nonblack: float) -> bool:
    """Gameplay map: high nonblack AND rich palette (bright intro/logo screens
    can exceed the nonblack bar but have few distinct colors)."""
    return nonblack_percent(arr) >= min_nonblack and unique_sample_colors(arr) >= 300


def diff_clusters(a: np.ndarray, b: np.ndarray) -> list[dict[str, Any]]:
    mask = (np.abs(a - b).max(axis=2) > 24)
    ys, xs = np.nonzero(mask)
    if len(xs) == 0:
        return []
    out: list[dict[str, Any]] = []
    for x, y in zip(xs.tolist(), ys.tolist()):
        for c in out:
            x0, y0, x1, y1 = c["bbox"]
            if x0 - 32 <= x <= x1 + 32 and y0 - 32 <= y <= y1 + 32:
                c["bbox"] = [min(x0, x), min(y0, y), max(x1, x), max(y1, y)]
                c["count"] += 1
                break
        else:
            out.append({"bbox": [x, y, x, y], "count": 1})
    merged = True
    while merged:
        merged = False
        for i in range(len(out)):
            for j in range(i + 1, len(out)):
                a0, b0, a1, b1 = out[i]["bbox"]
                c0, d0, c1, d1 = out[j]["bbox"]
                if a0 - 32 <= c1 and c0 - 32 <= a1 and b0 - 32 <= d1 and d0 - 32 <= b1:
                    out[i]["bbox"] = [min(a0, c0), min(b0, d0), max(a1, c1), max(b1, d1)]
                    out[i]["count"] += out[j]["count"]
                    del out[j]
                    merged = True
                    break
            if merged:
                break
    out.sort(key=lambda c: -c["count"])
    return out


def changed_pixels(a: np.ndarray, b: np.ndarray) -> int:
    return int((np.abs(a - b).max(axis=2) > 24).sum())


def cursor_from_diff(prev: np.ndarray, curr: np.ndarray, last_pos: tuple[int, int] | None) -> tuple[int, int] | None:
    clusters = diff_clusters(prev, curr)
    if not clusters:
        return None
    if last_pos is None:
        x0, y0, _x1, _y1 = clusters[0]["bbox"]
        return (x0, y0)
    for c in clusters:
        x0, y0, x1, y1 = c["bbox"]
        if not (x0 - 4 <= last_pos[0] <= x1 + 4 and y0 - 4 <= last_pos[1] <= y1 + 4):
            return (x0, y0)
    x0, y0, x1, y1 = clusters[0]["bbox"]
    cands = [(x0, y0), (max(0, x1 - 24), y0), (x0, max(0, y1 - 20)), (max(0, x1 - 24), max(0, y1 - 20))]
    return max(cands, key=lambda p: abs(p[0] - last_pos[0]) + abs(p[1] - last_pos[1]))


def pulse_stream(delta: tuple[int, int], duration: float, interval: float) -> None:
    end = time.time() + duration
    while time.time() < end:
        send_rel(*delta)
        time.sleep(interval)


def click_while_pulsing(delta: tuple[int, int], hold_ms: int, repeats: int, interval: float) -> int:
    clicks = 0
    for _ in range(repeats):
        for _ in range(4):
            send_rel(*delta)
            time.sleep(interval)
        send_button(MOUSEEVENTF_LEFTDOWN)
        t_end = time.time() + hold_ms / 1000.0
        while time.time() < t_end:
            send_rel(*delta)
            time.sleep(interval)
        send_button(MOUSEEVENTF_LEFTUP)
        clicks += 1
        for _ in range(3):
            send_rel(*delta)
            time.sleep(interval)
        time.sleep(0.12)
    return clicks


def aim(pid: int, hwnd: int, target: tuple[int, int], gain: float, prev: np.ndarray,
        last_pos: tuple[int, int] | None, interval: float, tolerance: int,
        deadline: float, max_iterations: int = 8) -> dict[str, Any]:
    result: dict[str, Any] = {"target": list(target), "iterations": [], "converged": False,
                              "aimed_pos": None, "aim_error_px": None, "pulse_delta": None, "gain": gain,
                              "wakes": 0}
    pos = last_pos
    frame = prev
    # Prime the engine's input acquisition before the first aim.
    wake_foreground(hwnd)
    no_motion_streak = 0
    for it in range(max_iterations):
        if time.time() > deadline:
            result["deadline_hit"] = True
            break
        delta = (int(round(target[0] / gain)), int(round(target[1] / gain)))
        foreground_ok = focus(hwnd)
        pulse_stream(delta, 0.6, interval)
        time.sleep(0.15)
        hwnd, curr = grab_retry(pid, hwnd, attempts=3)
        if curr is None:
            result["window_lost"] = True
            break
        npos = cursor_from_diff(frame, curr, pos)
        row = {"it": it, "delta": list(delta), "pos": list(npos) if npos else None,
               "foreground_ok": foreground_ok}
        result["iterations"].append(row)
        frame = curr
        if npos is None:
            no_motion_streak += 1
            # Dead poll: force an activation cycle to re-acquire DirectInput,
            # then re-baseline against the current frame.
            if no_motion_streak <= 3:
                wake_foreground(hwnd)
                result["wakes"] += 1
                hwnd, refreshed = grab_retry(pid, hwnd, attempts=2)
                if refreshed is not None:
                    frame = refreshed
            continue
        no_motion_streak = 0
        gx = npos[0] / delta[0] if delta[0] else None
        gy = npos[1] / delta[1] if delta[1] else None
        gains = [g for g in (gx, gy) if g is not None and 1.0 < g < 12.0]
        if gains:
            gain = sum(gains) / len(gains)
        row["gain"] = round(gain, 3)
        pos = npos
        err = max(abs(npos[0] - target[0]), abs(npos[1] - target[1]))
        if err <= tolerance:
            result.update({"converged": True, "aimed_pos": list(npos), "aim_error_px": err,
                           "pulse_delta": list(delta), "gain": round(gain, 3)})
            break
    if not result["converged"] and pos is not None:
        result["aimed_pos"] = list(pos)
        result["aim_error_px"] = max(abs(pos[0] - target[0]), abs(pos[1] - target[1]))
        result["gain"] = round(gain, 3)
    result["frame"] = frame
    result["hwnd"] = hwnd
    result["last_pos"] = pos
    return result


def parse_steps(text: str) -> list[tuple[str, int, int]]:
    steps: list[tuple[str, int, int]] = []
    for item in text.split(";"):
        item = item.strip()
        if not item:
            continue
        name, coords = item.split(":", 1)
        x_text, y_text = coords.split(",", 1)
        steps.append((name.strip(), int(x_text), int(y_text)))
    if not steps:
        raise ValueError("at least one step is required")
    return steps


def parse_points(text: str) -> list[tuple[str, int, int]]:
    """Parse aim points as 'x,y' or 'name:x,y', auto-naming the unnamed ones.

    The manual DirectInput run plan carries bare 'x,y;x,y' follow-up point
    lists, so bare coordinates must stay accepted; named points keep the
    emitted evidence rows readable when a caller supplies names.
    """
    points: list[tuple[str, int, int]] = []
    for item in text.split(";"):
        item = item.strip()
        if not item:
            continue
        name = f"point-{len(points):02d}"
        coords = item
        if ":" in item:
            name, coords = item.split(":", 1)
            name = name.strip()
        x_text, y_text = coords.split(",", 1)
        points.append((name, int(x_text), int(y_text)))
    if not points:
        raise ValueError("at least one aim point is required")
    return points


def run_aim_points(
    args: argparse.Namespace,
    result: dict[str, Any],
    hwnd: int,
    frame: np.ndarray,
    interval: float,
    deadline: float,
) -> int:
    """Aim (and optionally click) validation points on an already-loaded screen.

    Unlike --steps this never skips on the map fingerprint and never treats a
    small frame delta as a failure: follow-up validation points (map edges,
    minimap corners, castle descriptors, recovered lower/right action UI) can
    legitimately redraw only a handful of pixels. What is proven per point is
    the aimed ENGINE cursor position error; the frame delta is recorded as
    observed so a run can report honestly either way.
    """
    points = parse_points(args.aim_points)
    result["aim_points"] = [{"name": name, "target": [x, y]} for name, x, y in points]
    result["aim_only"] = bool(args.aim_only)
    last_pos: tuple[int, int] | None = (0, 0)
    gain = args.initial_gain
    converged = 0

    for name, tx, ty in points:
        row: dict[str, Any] = {
            "name": name,
            "target": [tx, ty],
            "pre_nonblack": round(nonblack_percent(frame), 2),
            "pre_unique_colors": unique_sample_colors(frame),
        }
        if time.time() > deadline:
            row["deadline_hit"] = True
            result["steps"].append(row)
            break

        aimed = aim(args.pid, hwnd, (tx, ty), gain, frame, last_pos, interval,
                    args.aim_tolerance, deadline)
        frame = aimed.pop("frame")
        hwnd = aimed.pop("hwnd")
        last_pos = aimed.pop("last_pos")
        gain = float(aimed.get("gain") or gain)
        row["aim"] = aimed
        row["converged"] = bool(aimed.get("converged"))
        if not aimed.get("converged"):
            row["clicked"] = False
            row["transition_verified"] = False
            result["steps"].append(row)
            if aimed.get("window_lost"):
                break
            continue
        converged += 1

        if args.aim_only:
            row["clicked"] = False
            row["aim_only"] = True
            result["steps"].append(row)
            continue

        pos = tuple(aimed["aimed_pos"])
        nb = row["pre_nonblack"]
        menu_like = MENU_NONBLACK_RANGE[0] <= nb <= MENU_NONBLACK_RANGE[1]
        if menu_like and (MENU_EXIT_ZONE[0] <= pos[0] <= MENU_EXIT_ZONE[2]
                          and MENU_EXIT_ZONE[1] <= pos[1] <= MENU_EXIT_ZONE[3]):
            # The expected screen never loaded and the aim landed on the menu
            # Exit control; refuse rather than quit the game.
            row["clicked"] = False
            row["transition_verified"] = False
            row["refused_exit_zone"] = True
            result["steps"].append(row)
            continue

        click_foreground_ok = focus(hwnd)
        row["click_foreground_ok"] = click_foreground_ok
        if not click_foreground_ok:
            row["clicked"] = False
            row["transition_verified"] = False
            row["foreground_denied"] = True
            result["steps"].append(row)
            continue

        pre_click = frame
        delta = tuple(aimed["pulse_delta"])
        row["clicked"] = True
        row["click_count"] = click_while_pulsing(delta, args.click_hold_ms, args.click_repeats, interval)
        time.sleep(args.point_settle_ms / 1000.0)
        hwnd, after = grab_retry(args.pid, hwnd)
        if after is None:
            row["transition_verified"] = False
            row["window_lost_after_click"] = True
            result["steps"].append(row)
            break
        row["changed_pixels"] = changed_pixels(pre_click, after)
        row["post_nonblack"] = round(nonblack_percent(after), 2)
        row["post_unique_colors"] = unique_sample_colors(after)
        row["transition_verified"] = row["changed_pixels"] > args.transition_min_pixels
        frame = after
        last_pos = None  # screen changed; cursor location unknown until next diff
        result["steps"].append(row)

    result["final_nonblack"] = round(nonblack_percent(frame), 2)
    result["all_steps_accounted"] = len(result["steps"]) == len(points)
    result["aim_points_total"] = len(points)
    result["aim_points_converged"] = converged
    emit(result, args.json)
    return 0 if (converged == len(points) and result["all_steps_accounted"]) else 2


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pid", type=int, required=True)
    ap.add_argument("--steps",
                    help="ROUTE mode: semicolon list of name:engineX,engineY steps, e.g. "
                         "'load-button:302,211;load-slot0:320,166'. Routes menu screens and stops "
                         "once the gameplay map fingerprint appears.")
    ap.add_argument("--aim-points",
                    help="AIM-POINTS mode: semicolon list of engineX,engineY (or name:engineX,engineY) "
                         "validation points on an ALREADY-loaded screen. Every point is aimed with the "
                         "same frame-diff feedback loop and clicked while pulsing, but nothing is skipped "
                         "on a map fingerprint and a small frame delta is not a failure: follow-up "
                         "validation points can legitimately redraw only a few pixels. The proof carried "
                         "per point is the aimed engine position error; the frame delta is reported as "
                         "observed.")
    ap.add_argument("--aim-only", action="store_true",
                    help="--aim-points: aim at every point without clicking")
    ap.add_argument("--transition-min-pixels", type=int, default=12000,
                    help="changed-pixel count above which a post-click frame delta counts as a "
                         "verified transition")
    ap.add_argument("--point-settle-ms", type=int, default=1200,
                    help="--aim-points: settle time after each clicked point before the post frame")
    ap.add_argument("--map-nonblack", type=float, default=85.0,
                    help="skip remaining steps once the frame nonblack%% reaches this (0 disables)")
    ap.add_argument("--aim-tolerance", type=int, default=10)
    ap.add_argument("--click-hold-ms", type=int, default=700)
    ap.add_argument("--click-repeats", type=int, default=3)
    ap.add_argument("--pulse-interval-ms", type=int, default=28)
    ap.add_argument("--initial-gain", type=float, default=4.4)
    ap.add_argument("--settle-ms", type=int, default=1600)
    ap.add_argument("--final-settle-ms", type=int, default=3500)
    ap.add_argument("--deadline-sec", type=int, default=120)
    ap.add_argument(
        "--probe-only",
        action="store_true",
        help="aim at the first step target WITHOUT clicking; exit 0 only if the "
        "engine cursor responded and converged (interactive-menu liveness probe)",
    )
    ap.add_argument("--json", type=Path)
    args = ap.parse_args()

    if bool(args.steps) == bool(args.aim_points):
        ap.error("exactly one of --steps or --aim-points is required")

    deadline = time.time() + args.deadline_sec
    interval = args.pulse_interval_ms / 1000.0
    steps = parse_steps(args.steps) if args.steps else []
    result: dict[str, Any] = {
        "input_mechanism": INPUT_MECHANISM,
        "engine_model": ENGINE_MODEL,
        "mode": "aim-points" if args.aim_points else ("probe-only" if args.probe_only else "route-steps"),
        "pid": args.pid,
        "steps": [],
        "map_reached": False,
        "final_nonblack": None,
        "all_steps_accounted": False,
    }

    hwnd = None
    for _ in range(40):
        hwnd = find_window(args.pid)
        if hwnd:
            break
        time.sleep(0.25)
    if not hwnd:
        result["error"] = "no visible window for pid"
        emit(result, args.json)
        return 3

    hwnd, frame = grab_retry(args.pid, hwnd)
    if frame is None:
        result["error"] = "could not grab client frame"
        emit(result, args.json)
        return 3

    if args.aim_points:
        return run_aim_points(args, result, hwnd, frame, interval, deadline)

    if args.probe_only:
        name, tx, ty = steps[0]
        result["probe_only"] = True
        probe = aim(args.pid, hwnd, (tx, ty), args.initial_gain, frame, (0, 0),
                    interval, args.aim_tolerance, deadline, max_iterations=4)
        probe.pop("frame", None)
        probe.pop("hwnd", None)
        probe.pop("last_pos", None)
        result["steps"].append({"name": name, "target": [tx, ty], "probe_only": True, "aim": probe})
        result["cursor_alive"] = any(row.get("pos") for row in probe.get("iterations") or [])
        result["all_steps_accounted"] = True
        emit(result, args.json)
        return 0 if (probe.get("converged") and result["cursor_alive"]) else 2

    last_pos: tuple[int, int] | None = (0, 0)
    gain = args.initial_gain
    ok = True
    for index, (name, tx, ty) in enumerate(steps):
        nb = nonblack_percent(frame)
        row: dict[str, Any] = {"name": name, "target": [tx, ty], "pre_nonblack": round(nb, 2),
                               "pre_unique_colors": unique_sample_colors(frame)}
        if args.map_nonblack > 0 and looks_like_map(frame, args.map_nonblack):
            row["skipped_map_reached"] = True
            result["steps"].append(row)
            result["map_reached"] = True
            continue
        row["skipped_map_reached"] = False
        if time.time() > deadline:
            row["deadline_hit"] = True
            result["steps"].append(row)
            ok = False
            break
        aimed = aim(args.pid, hwnd, (tx, ty), gain, frame, last_pos, interval, args.aim_tolerance, deadline)
        frame = aimed.pop("frame")
        hwnd = aimed.pop("hwnd")
        last_pos = aimed.pop("last_pos")
        gain = float(aimed.get("gain") or gain)
        row["aim"] = aimed
        if not aimed.get("converged"):
            row["clicked"] = False
            row["transition_verified"] = False
            result["steps"].append(row)
            ok = False
            break
        pos = tuple(aimed["aimed_pos"])
        menu_like = MENU_NONBLACK_RANGE[0] <= nb <= MENU_NONBLACK_RANGE[1]
        if menu_like and MENU_EXIT_ZONE[0] <= pos[0] <= MENU_EXIT_ZONE[2] and MENU_EXIT_ZONE[1] <= pos[1] <= MENU_EXIT_ZONE[3]:
            row["clicked"] = False
            row["transition_verified"] = False
            row["refused_exit_zone"] = True
            result["steps"].append(row)
            ok = False
            break
        pre_click = frame
        click_foreground_ok = focus(hwnd)
        row["click_foreground_ok"] = click_foreground_ok
        if not click_foreground_ok:
            row["clicked"] = False
            row["transition_verified"] = False
            row["foreground_denied"] = True
            result["steps"].append(row)
            ok = False
            break
        delta = tuple(aimed["pulse_delta"])
        row["clicked"] = True
        row["click_count"] = click_while_pulsing(delta, args.click_hold_ms, args.click_repeats, interval)
        settle = args.final_settle_ms if index == len(steps) - 1 else args.settle_ms
        time.sleep(settle / 1000.0)
        hwnd, after = grab_retry(args.pid, hwnd)
        if after is None:
            row["transition_verified"] = False
            row["window_lost_after_click"] = True
            result["steps"].append(row)
            ok = False
            break
        changed = changed_pixels(pre_click, after)
        post_nb = nonblack_percent(after)
        row["changed_pixels"] = changed
        row["post_nonblack"] = round(post_nb, 2)
        row["post_unique_colors"] = unique_sample_colors(after)
        row["transition_verified"] = changed > args.transition_min_pixels
        frame = after
        last_pos = None  # screen changed; cursor location unknown until next diff
        result["steps"].append(row)
        if args.map_nonblack > 0 and looks_like_map(after, args.map_nonblack):
            result["map_reached"] = True

    # allow the map to finish loading after the last click before the final read
    if not result["map_reached"] and ok and args.map_nonblack > 0:
        for _ in range(6):
            time.sleep(1.2)
            hwnd, f = grab_retry(args.pid, hwnd, attempts=2)
            if f is None:
                break
            frame = f
            if looks_like_map(frame, args.map_nonblack):
                result["map_reached"] = True
                break

    result["final_nonblack"] = round(nonblack_percent(frame), 2)
    result["all_steps_accounted"] = len(result["steps"]) == len(steps)
    emit(result, args.json)
    if not ok:
        return 2
    return 0


def emit(result: dict[str, Any], json_path: Path | None) -> None:
    text = json.dumps(result, indent=2)
    if json_path:
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(text, encoding="ascii")
    print(text)


if __name__ == "__main__":
    raise SystemExit(main())
