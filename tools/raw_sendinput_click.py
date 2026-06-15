#!/usr/bin/env python3
"""Send raw OS cursor/click input at absolute screen coordinates.

This is a narrow companion to mouse_path_probe.py for debugger sessions where
HWND operations can block because CDB is repeatedly stopping the target UI
thread. It does not prove game consumption by itself; pair its JSON with CDB
DirectInput/button/callback rows.
"""

from __future__ import annotations

import argparse
import ctypes
import json
import sys
import time
from ctypes import wintypes
from pathlib import Path


MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004


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


def parse_points(value: str) -> list[tuple[int, int]]:
    points: list[tuple[int, int]] = []
    for item in value.split(";"):
        text = item.strip()
        if not text:
            continue
        x_text, y_text = text.split(",", 1)
        points.append((int(x_text), int(y_text)))
    if not points:
        raise ValueError("at least one screen point is required")
    return points


def load_user32() -> ctypes.WinDLL:
    if sys.platform != "win32":
        raise SystemExit("raw_sendinput_click.py requires Windows")
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    user32.SetCursorPos.argtypes = [ctypes.c_int, ctypes.c_int]
    user32.SetCursorPos.restype = wintypes.BOOL
    user32.GetCursorPos.argtypes = [ctypes.POINTER(POINT)]
    user32.GetCursorPos.restype = wintypes.BOOL
    user32.SendInput.argtypes = [wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int]
    user32.SendInput.restype = wintypes.UINT
    return user32


def wincheck(ok: int, what: str) -> None:
    if not ok:
        raise ctypes.WinError(ctypes.get_last_error(), what)


def get_cursor_pos(user32: ctypes.WinDLL) -> tuple[int, int]:
    point = POINT()
    wincheck(user32.GetCursorPos(ctypes.byref(point)), "GetCursorPos")
    return int(point.x), int(point.y)


def send_mouse_input(user32: ctypes.WinDLL, flags: int) -> int:
    event = INPUT()
    event.type = 0
    event.union.mi.dwFlags = flags
    sent = user32.SendInput(1, ctypes.byref(event), ctypes.sizeof(INPUT))
    if sent != 1:
        raise ctypes.WinError(ctypes.get_last_error(), "SendInput")
    return int(sent)


def click_point(
    user32: ctypes.WinDLL,
    x: int,
    y: int,
    hold_sec: float,
    repeat: int,
    interval_sec: float,
) -> dict:
    row: dict = {
        "requested_screen": [int(x), int(y)],
        "samples": [],
        "clicks": [],
    }
    wincheck(user32.SetCursorPos(int(x), int(y)), "SetCursorPos")
    time.sleep(0.05)
    before = get_cursor_pos(user32)
    row["samples"].append({"phase": "after_move", "actual_screen": list(before)})

    for repeat_index in range(repeat):
        click: dict = {"repeat_index": repeat_index, "hold_ms": int(round(hold_sec * 1000))}
        click["before_down"] = list(get_cursor_pos(user32))
        click["sendinput_down"] = send_mouse_input(user32, MOUSEEVENTF_LEFTDOWN)
        time.sleep(hold_sec)
        click["after_down"] = list(get_cursor_pos(user32))
        click["sendinput_up"] = send_mouse_input(user32, MOUSEEVENTF_LEFTUP)
        time.sleep(0.04)
        click["after_up"] = list(get_cursor_pos(user32))
        row["clicks"].append(click)
        time.sleep(interval_sec)

    after = get_cursor_pos(user32)
    row["samples"].append({"phase": "after_clicks", "actual_screen": list(after)})
    row["screen_error"] = [int(after[0] - x), int(after[1] - y)]
    return row


def build_dry_run(points: list[tuple[int, int]], hold_ms: int, repeat: int) -> dict:
    return {
        "dry_run": True,
        "points": [
            {
                "requested_screen": [int(x), int(y)],
                "clicks": [{"repeat_index": index, "hold_ms": hold_ms} for index in range(repeat)],
            }
            for x, y in points
        ],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Send raw SendInput clicks at absolute screen coordinates.")
    parser.add_argument("--screen-points", required=True, help="semicolon-separated screen points, e.g. 668,520")
    parser.add_argument("--click-hold-ms", type=int, default=300)
    parser.add_argument("--click-repeat", type=int, default=3)
    parser.add_argument("--interval-ms", type=int, default=120)
    parser.add_argument("--settle-sec", type=float, default=0.25)
    parser.add_argument("--json", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    points = parse_points(args.screen_points)
    if args.dry_run:
        result = build_dry_run(points, args.click_hold_ms, args.click_repeat)
    else:
        user32 = load_user32()
        time.sleep(args.settle_sec)
        result = {
            "dry_run": False,
            "points": [
                click_point(
                    user32,
                    x,
                    y,
                    args.click_hold_ms / 1000.0,
                    args.click_repeat,
                    args.interval_ms / 1000.0,
                )
                for x, y in points
            ],
        }
        result["click_event_count"] = sum(len(row["clicks"]) for row in result["points"])
        result["path_verified"] = all(max(abs(v) for v in row["screen_error"]) <= 1 for row in result["points"])

    text = json.dumps(result, indent=2)
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(text, encoding="ascii")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
