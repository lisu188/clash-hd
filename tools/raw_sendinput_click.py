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


MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_ABSOLUTE = 0x8000
MOUSEEVENTF_VIRTUALDESK = 0x4000
SM_XVIRTUALSCREEN = 76
SM_YVIRTUALSCREEN = 77
SM_CXVIRTUALSCREEN = 78
SM_CYVIRTUALSCREEN = 79


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


def parse_rel_segments(value: str, point_count: int) -> list[list[tuple[int, int]]]:
    """Parse per-point relative-move legs.

    Format: per-point entries separated by ';', each entry is one or more
    'dx,dy' legs separated by '|'. A single entry applies to every point.
    """
    entries = [entry.strip() for entry in value.split(";")]
    per_point: list[list[tuple[int, int]]] = []
    for entry in entries:
        legs: list[tuple[int, int]] = []
        for leg in entry.split("|"):
            leg = leg.strip()
            if not leg:
                continue
            dx_text, dy_text = leg.split(",", 1)
            legs.append((int(dx_text), int(dy_text)))
        per_point.append(legs)
    if len(per_point) == 1:
        per_point = per_point * point_count
    if len(per_point) != point_count:
        raise ValueError("pre-move-rel entry count must be 1 or match screen point count")
    return per_point


def load_user32() -> ctypes.WinDLL:
    if sys.platform != "win32":
        raise SystemExit("raw_sendinput_click.py requires Windows")
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    user32.SetCursorPos.argtypes = [ctypes.c_int, ctypes.c_int]
    user32.SetCursorPos.restype = wintypes.BOOL
    user32.GetSystemMetrics.argtypes = [ctypes.c_int]
    user32.GetSystemMetrics.restype = ctypes.c_int
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


def send_mouse_input(user32: ctypes.WinDLL, flags: int, dx: int = 0, dy: int = 0) -> int:
    event = INPUT()
    event.type = 0
    event.union.mi.dx = dx
    event.union.mi.dy = dy
    event.union.mi.dwFlags = flags
    sent = user32.SendInput(1, ctypes.byref(event), ctypes.sizeof(INPUT))
    if sent != 1:
        raise ctypes.WinError(ctypes.get_last_error(), "SendInput")
    return int(sent)


def send_absolute_move(user32: ctypes.WinDLL, screen_x: int, screen_y: int) -> int:
    """Inject an absolute MOVE via SendInput (raw-input visible, unlike SetCursorPos).

    Matches mouse_path_probe.py's proven normalization: the engine's DirectInput
    quarter-scale absolute samples only update from injected MOVE events.
    """
    left = int(user32.GetSystemMetrics(SM_XVIRTUALSCREEN))
    top = int(user32.GetSystemMetrics(SM_YVIRTUALSCREEN))
    width = max(1, int(user32.GetSystemMetrics(SM_CXVIRTUALSCREEN)))
    height = max(1, int(user32.GetSystemMetrics(SM_CYVIRTUALSCREEN)))
    norm_x = int(round(((screen_x - left) * 65535) / max(1, width - 1)))
    norm_y = int(round(((screen_y - top) * 65535) / max(1, height - 1)))
    return send_mouse_input(
        user32, MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_VIRTUALDESK, norm_x, norm_y
    )


def servo_to_point(
    user32: ctypes.WinDLL,
    x: int,
    y: int,
    duration_sec: float,
    interval_sec: float = 0.004,
) -> dict:
    """Closed-loop cursor hold: keep correcting toward (x, y) with relative moves.

    A DirectInput exclusive-mode mouse on modern Windows keeps snapping the
    cursor back to the screen center; the engine's per-poll sample is the
    quartered cursor position, so the cursor must be AT the target when a poll
    lands. Relative MOVE events both move the cursor and feed the raw-input
    stream the DI sample derives from.
    """
    deadline = time.time() + duration_sec
    corrections = 0
    iterations = 0
    while time.time() < deadline:
        pos = get_cursor_pos(user32)
        delta_x = int(x) - pos[0]
        delta_y = int(y) - pos[1]
        if delta_x or delta_y:
            send_mouse_input(user32, MOUSEEVENTF_MOVE, delta_x, delta_y)
            corrections += 1
        iterations += 1
        time.sleep(interval_sec)
    final = get_cursor_pos(user32)
    return {
        "target": [int(x), int(y)],
        "iterations": iterations,
        "corrections": corrections,
        "final_cursor": list(final),
    }


def pulse_deltas(
    user32: ctypes.WinDLL,
    deltas: list[tuple[int, int]],
    duration_sec: float,
    interval_sec: float,
) -> dict:
    """Emit one small relative MOVE per interval, cycling through deltas.

    Empirical engine model (battle command loop, this machine): each input
    poll resets the DirectInput accumulator to the screen center and every
    injected relative delta is applied x8; the poll reads accumulator/4.
    One pulse per poll window therefore lands the engine mouse at
    (center + 8*delta)/4 * 4 = center + 8*delta in displayed coordinates.
    Zero or two pulses in a window produce out-of-bounds readings the
    engine's bounds guard rejects harmlessly.
    """
    deadline = time.time() + duration_sec
    sent = 0
    index = 0
    while time.time() < deadline:
        delta_x, delta_y = deltas[index % len(deltas)]
        send_mouse_input(user32, MOUSEEVENTF_MOVE, int(delta_x), int(delta_y))
        sent += 1
        index += 1
        time.sleep(interval_sec)
    return {"deltas": [list(d) for d in deltas], "pulses": sent}


def send_relative_move(
    user32: ctypes.WinDLL,
    total_dx: int,
    total_dy: int,
    step: int,
    interval_sec: float,
) -> dict:
    """Emit MOUSEEVENTF_MOVE relative deltas summing to (total_dx, total_dy).

    Unlike SetCursorPos, injected relative MOVE events enter the raw-input
    stream, so DirectInput consumers (the game's accumulated mouse position)
    observe them. Deltas are chunked into steps so per-event clamping or
    smoothing in the input stack cannot swallow one large jump.
    """
    row: dict = {
        "requested_rel": [int(total_dx), int(total_dy)],
        "step": int(step),
        "events": 0,
    }
    row["cursor_before"] = list(get_cursor_pos(user32))
    remaining_x = int(total_dx)
    remaining_y = int(total_dy)
    step = max(1, int(step))
    while remaining_x != 0 or remaining_y != 0:
        move_x = max(-step, min(step, remaining_x))
        move_y = max(-step, min(step, remaining_y))
        send_mouse_input(user32, MOUSEEVENTF_MOVE, move_x, move_y)
        row["events"] += 1
        remaining_x -= move_x
        remaining_y -= move_y
        if interval_sec > 0:
            time.sleep(interval_sec)
    row["cursor_after"] = list(get_cursor_pos(user32))
    return row


def click_point(
    user32: ctypes.WinDLL,
    x: int,
    y: int,
    hold_sec: float,
    repeat: int,
    interval_sec: float,
    pre_move_rel: list[tuple[int, int]] | None = None,
    rel_step: int = 8,
    rel_interval_sec: float = 0.004,
    skip_set_cursor: bool = False,
    move_mode: str = "setcursor",
    recenter_after_rel: bool = False,
    servo_interval_sec: float = 0.028,
    pulse: list[tuple[int, int]] | None = None,
) -> dict:
    row: dict = {
        "requested_screen": [int(x), int(y)],
        "move_mode": move_mode,
        "samples": [],
        "clicks": [],
    }
    if not skip_set_cursor and move_mode in ("setcursor", "both"):
        wincheck(user32.SetCursorPos(int(x), int(y)), "SetCursorPos")
        time.sleep(0.05)
    if move_mode in ("sendinput-absolute", "both"):
        row["absolute_moves"] = send_absolute_move(user32, int(x), int(y))
        time.sleep(0.05)
    if pre_move_rel:
        row["pre_move_rel"] = [
            send_relative_move(user32, leg_dx, leg_dy, rel_step, rel_interval_sec)
            for leg_dx, leg_dy in pre_move_rel
        ]
        time.sleep(0.05)
        if recenter_after_rel:
            # Park the OS cursor back over the intended screen point so the
            # button events land on the target window; SetCursorPos does not
            # disturb the DirectInput accumulator the relative legs just set.
            wincheck(user32.SetCursorPos(int(x), int(y)), "SetCursorPos recenter")
            row["recentered"] = True
            time.sleep(0.05)
    before = get_cursor_pos(user32)
    row["samples"].append({"phase": "after_move", "actual_screen": list(before)})

    for repeat_index in range(repeat):
        click: dict = {"repeat_index": repeat_index, "hold_ms": int(round(hold_sec * 1000))}
        if move_mode in ("sendinput-absolute", "both"):
            # Refresh the absolute sample right before the press so the engine's
            # per-frame DirectInput poll pairs the press with the target coords.
            row["absolute_moves"] = row.get("absolute_moves", 0) + send_absolute_move(
                user32, int(x), int(y)
            )
            time.sleep(0.03)
        if move_mode == "servo":
            click["servo_pre"] = servo_to_point(user32, x, y, 0.2, servo_interval_sec)
        click["before_down"] = list(get_cursor_pos(user32))
        click["sendinput_down"] = send_mouse_input(user32, MOUSEEVENTF_LEFTDOWN)
        if move_mode == "servo":
            # Keep the cursor pinned on the target for the whole hold so the
            # engine's DirectInput polls sample the target position while the
            # button is down. The engine resets its accumulator to screen
            # center at each poll and every event adds its full delta, so the
            # servo interval should approximate one correction per engine poll.
            click["servo_hold"] = servo_to_point(user32, x, y, hold_sec, servo_interval_sec)
        elif move_mode == "pulse" and pulse:
            click["pulse_hold"] = pulse_deltas(user32, pulse, hold_sec, servo_interval_sec)
        else:
            time.sleep(hold_sec)
        click["after_down"] = list(get_cursor_pos(user32))
        click["sendinput_up"] = send_mouse_input(user32, MOUSEEVENTF_LEFTUP)
        time.sleep(0.04)
        click["after_up"] = list(get_cursor_pos(user32))
        row["clicks"].append(click)
        time.sleep(interval_sec)

    after = get_cursor_pos(user32)
    row["samples"].append({"phase": "after_clicks", "actual_screen": list(after)})
    if (pre_move_rel and not recenter_after_rel) or skip_set_cursor:
        # The OS cursor was intentionally moved relative to (or independent of)
        # the requested point; verify stability against the pre-click sample.
        row["screen_error"] = [int(after[0] - before[0]), int(after[1] - before[1])]
    else:
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
    parser.add_argument(
        "--pre-move-rel",
        help="relative MOUSEEVENTF_MOVE legs emitted before clicking (reaches "
        "DirectInput raw-delta consumers, unlike SetCursorPos). Per-point entries "
        "separated by ';', multi-leg entries by '|', e.g. '-3000,-3000|588,440;0,0'",
    )
    parser.add_argument(
        "--recenter-after-rel",
        action="store_true",
        help="after the relative legs, SetCursorPos back to the screen point so "
        "clicks land on the target window without disturbing the DI accumulator",
    )
    parser.add_argument("--rel-step", type=int, default=8, help="max counts per relative MOVE event")
    parser.add_argument("--rel-interval-ms", type=int, default=4)
    parser.add_argument(
        "--servo-interval-ms",
        type=int,
        default=28,
        help="servo correction cadence; aim for one correction per engine input poll",
    )
    parser.add_argument(
        "--skip-set-cursor",
        action="store_true",
        help="do not SetCursorPos to the screen point first (pure relative walk)",
    )
    parser.add_argument(
        "--pulse-delta",
        help="pulse mode deltas: one or more 'dx,dy' pairs separated by ';', "
        "cycled one pulse per servo interval during each button hold",
    )
    parser.add_argument(
        "--move-mode",
        choices=("setcursor", "sendinput-absolute", "both", "servo", "pulse"),
        default="setcursor",
        help="how to position before clicking; sendinput-absolute injects raw-input "
        "visible MOVE events that DirectInput consumers observe; servo keeps "
        "correcting the cursor onto the target with relative moves through each "
        "button hold (defeats exclusive-mode recentering)",
    )
    parser.add_argument("--json", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    points = parse_points(args.screen_points)
    rel_segments: list[list[tuple[int, int]]] | None = None
    if args.pre_move_rel:
        rel_segments = parse_rel_segments(args.pre_move_rel, len(points))
    pulse: list[tuple[int, int]] | None = None
    if args.pulse_delta:
        pulse = parse_points(args.pulse_delta)
    if args.dry_run:
        result = build_dry_run(points, args.click_hold_ms, args.click_repeat)
        if rel_segments is not None:
            result["pre_move_rel"] = [
                [list(leg) for leg in legs] for legs in rel_segments
            ]
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
                    pre_move_rel=rel_segments[index] if rel_segments else None,
                    rel_step=args.rel_step,
                    rel_interval_sec=args.rel_interval_ms / 1000.0,
                    skip_set_cursor=args.skip_set_cursor,
                    move_mode=args.move_mode,
                    recenter_after_rel=args.recenter_after_rel,
                    servo_interval_sec=args.servo_interval_ms / 1000.0,
                    pulse=pulse,
                )
                for index, (x, y) in enumerate(points)
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
