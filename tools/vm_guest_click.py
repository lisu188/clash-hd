#!/usr/bin/env python3
"""Aim the Clash95 GUEST cursor over QMP relative input with screendump feedback.

This is the guest-side analog of tools/menu_pulse_click.py (the host pulse lane).
The host lane cannot run while the workstation is locked, and its OS-level
relative moves are also invisible to a headless Win98 guest; QMP input events are
injected by the hypervisor instead and are unaffected by the host session state.

Design of THIS lane (repo-only, offline-testable, opens no socket):

  * Frame feedback reuses tools/ppm_to_png.py to decode each QMP ``screendump``
    PPM, then reuses the existing frame-diff primitives from
    tools/menu_pulse_click.py (``cursor_from_diff`` / ``diff_clusters`` /
    ``changed_pixels``) rather than reimplementing them. The per-point aim error
    and the frame-transition verification therefore have the SAME evidence shape
    as the host pulse lane.

  * Aiming EMITS QMP ``input-send-event`` op payloads (relative moves + button,
    or absolute moves via usb-tablet). It never opens a socket here: the wire
    transport is an INJECTED callable/interface (a :class:`GuestSender`), so the
    socket layer is swapped in at execution time and the aiming logic is
    unit-testable offline with a fake VM + synthetic PPM frames.

  * The guest cursor uses PS/2 relative accumulation, so before each point the
    cursor is SATURATED to a known (0,0) origin (large negative relative moves
    the guest clamps), then walked toward the target in sub-acceleration-threshold
    steps, correcting against the measured cursor position each iteration. This
    mirrors the qmp ``clickrel`` saturate+step technique.

Honesty: guest evidence is a DISTINCT proof class. Everything emitted here is
labelled ``approved_guest_win98_directdraw`` (see :data:`GUEST_PROOF_CLASS`) and
is NEVER the host ``manual_directinput`` class. Host-only process telemetry is
not obtainable from inside a headless guest and is not synthesised here.

Live QMP execution against a running VM is separately approval-gated and is NOT
wired in this repo-only lane; the CLI only offers an offline op-plan dry run.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

import numpy as np

import menu_pulse_click
import ppm_to_png

# ---------------------------------------------------------------------------
# Identity / honesty labels
# ---------------------------------------------------------------------------
INPUT_MECHANISM = "qmp-guest-relative-aim"
ENGINE_MODEL = (
    "guest cursor = PS/2 relative accumulation; saturate to (0,0) origin, then "
    "walk toward the target in sub-acceleration-threshold steps while diffing "
    "screendump frames to measure the cursor, correcting the residual each pass"
)
# The guest lane is a DISTINCT proof class and must never be recorded as the
# host manual_directinput class.
GUEST_PROOF_CLASS = "approved_guest_win98_directdraw"
# This module encodes QMP input events but opens no socket itself.
OPENS_SOCKET = False

# QMP absolute-axis range for usb-tablet (0..32767), matching qmp_win.ps1.
ABS_AXIS_MAX = 32767
MOUSE_LEFT = "left"


# ---------------------------------------------------------------------------
# QMP op encoders (mirror clash-disassembly/tools/vm/qmp.py + scripts/vm/qmp_win.ps1)
# ---------------------------------------------------------------------------
def encode_rel_move(dx: int, dy: int) -> dict[str, Any]:
    """One relative move as a single input-send-event (x then y rel axes)."""
    return {
        "execute": "input-send-event",
        "arguments": {
            "events": [
                {"type": "rel", "data": {"axis": "x", "value": int(dx)}},
                {"type": "rel", "data": {"axis": "y", "value": int(dy)}},
            ]
        },
    }


def encode_abs_move(px: int, py: int, width: int, height: int) -> dict[str, Any]:
    """Absolute move (needs usb-tablet); pixel px,py scaled to 0..32767."""
    if width <= 0 or height <= 0:
        raise ValueError(f"invalid absolute frame size {width}x{height}")
    ax = int(round(px / width * ABS_AXIS_MAX))
    ay = int(round(py / height * ABS_AXIS_MAX))
    return {
        "execute": "input-send-event",
        "arguments": {
            "events": [
                {"type": "abs", "data": {"axis": "x", "value": ax}},
                {"type": "abs", "data": {"axis": "y", "value": ay}},
            ]
        },
    }


def encode_button(down: bool, button: str = MOUSE_LEFT) -> dict[str, Any]:
    return {
        "execute": "input-send-event",
        "arguments": {"events": [{"type": "btn", "data": {"button": button, "down": bool(down)}}]},
    }


def encode_screendump(path: str | Path) -> dict[str, Any]:
    return {"execute": "screendump", "arguments": {"filename": str(path)}}


def _sign(value: int) -> int:
    return (value > 0) - (value < 0)


def step_moves(dx: int, dy: int, max_step: int) -> list[tuple[int, int]]:
    """Break a relative move into sub-threshold steps (mirrors qmp_win moverel).

    Small steps stay below the guest pointer-acceleration threshold so the walk
    is ~1:1 and predictable. Returns an empty list for a zero move.
    """
    dx, dy = int(dx), int(dy)
    max_step = max(1, int(max_step))
    cx = cy = 0
    out: list[tuple[int, int]] = []
    while cx != dx or cy != dy:
        sx = _sign(dx - cx) * min(max_step, abs(dx - cx))
        sy = _sign(dy - cy) * min(max_step, abs(dy - cy))
        out.append((sx, sy))
        cx += sx
        cy += sy
    return out


# ---------------------------------------------------------------------------
# Frame decode: reuse ppm_to_png, hand menu_pulse_click the array shape it wants
# ---------------------------------------------------------------------------
def frame_to_array(frame: ppm_to_png.PpmFrame) -> np.ndarray:
    """PpmFrame -> (height, width, 3) int16, the shape menu_pulse_click diffs."""
    arr = np.frombuffer(frame.pixels, dtype=np.uint8)
    arr = arr.reshape(frame.height, frame.width, 3)
    return arr.astype(np.int16)


def parse_frame_bytes(data: bytes) -> np.ndarray:
    return frame_to_array(ppm_to_png.parse_ppm(data))


def parse_frame_file(path: str | Path) -> np.ndarray:
    return parse_frame_bytes(Path(path).read_bytes())


def wait_stable_frame_file(
    path: str | Path,
    *,
    expected_min_bytes: int = 15 + 640 * 480 * 3,
    max_reads: int = 40,
    sleep_fn: Callable[[float], None] | None = None,
    interval_sec: float = 0.25,
) -> np.ndarray:
    """Read a screendump only once its file SIZE has settled, then decode it.

    QEMU's screendump is not atomic: a header read a moment after the request can
    catch a partial/mid-write file and (the 2026-07-19 bug) misread an 800x600 HD
    frame as 640x480. This mirrors hd_vm_drive_menu.ps1's size-stable Save-Shot so
    the partial-frame misread is not reintroduced; ppm_to_png.parse_ppm then
    fails closed on any still-short frame. Live wiring passes a real sleep_fn;
    offline callers (fully-written fixtures) can leave it None.
    """
    p = Path(path)
    last = -1
    stable = 0
    for _ in range(max(1, max_reads)):
        if p.exists():
            size = p.stat().st_size
            if size == last and size >= expected_min_bytes - 64:
                stable += 1
            else:
                stable = 0
            last = size
            if stable >= 2:
                break
        if sleep_fn is not None:
            sleep_fn(interval_sec)
        else:
            break
    return parse_frame_file(p)


# ---------------------------------------------------------------------------
# Injected transport seam
# ---------------------------------------------------------------------------
# A Transport is any callable(command: dict) -> response that delivers one QMP
# command. In production it is a socket-backed client (swapped in at execution
# time); in tests it is a fake VM. This module never constructs a socket.
Transport = Callable[[dict[str, Any]], Any]


class GuestSender:
    """Interface the aim loop drives: move / click / capture a guest frame."""

    def saturate(self, step: int, count: int) -> None:
        raise NotImplementedError

    def move_rel(self, dx: int, dy: int) -> None:
        raise NotImplementedError

    def move_abs(self, px: int, py: int) -> None:
        raise NotImplementedError

    def click(self, hold_ms: int, button: str = MOUSE_LEFT, repeats: int = 1) -> None:
        raise NotImplementedError

    def capture(self) -> np.ndarray:
        raise NotImplementedError


class QmpGuestSender(GuestSender):
    """GuestSender that encodes QMP ops and delivers them via an injected transport.

    It opens no socket: ``transport`` is supplied by the caller (a socket client
    at execution time, a fake VM in tests). ``read_frame`` decodes the screendump
    the transport produced; production wiring should pass ``wait_stable_frame_file``
    so the partial-frame gotcha stays fixed.
    """

    def __init__(
        self,
        transport: Transport,
        *,
        screendump_path: str | Path,
        read_frame: Callable[[str | Path], np.ndarray] = parse_frame_file,
        max_step_px: int = 8,
        width: int = 800,
        height: int = 600,
    ) -> None:
        self.transport = transport
        self.screendump_path = Path(screendump_path)
        self.read_frame = read_frame
        self.max_step_px = max(1, int(max_step_px))
        self.width = int(width)
        self.height = int(height)
        self.sent_commands: list[dict[str, Any]] = []

    def _send(self, command: dict[str, Any]) -> Any:
        self.sent_commands.append(command)
        return self.transport(command)

    def _rel_event(self, dx: int, dy: int) -> None:
        self._send(encode_rel_move(dx, dy))

    def saturate(self, step: int, count: int) -> None:
        # Big single negative moves the guest clamps to the (0,0) origin (not
        # sub-stepped: saturation deliberately overshoots).
        for _ in range(max(0, int(count))):
            self._rel_event(-abs(int(step)), -abs(int(step)))

    def move_rel(self, dx: int, dy: int) -> None:
        for sx, sy in step_moves(dx, dy, self.max_step_px):
            self._rel_event(sx, sy)

    def move_abs(self, px: int, py: int) -> None:
        self._send(encode_abs_move(px, py, self.width, self.height))

    def click(self, hold_ms: int, button: str = MOUSE_LEFT, repeats: int = 1) -> None:
        for _ in range(max(1, int(repeats))):
            self._send(encode_button(True, button))
            self._send(encode_button(False, button))

    def capture(self) -> np.ndarray:
        self._send(encode_screendump(self.screendump_path))
        return self.read_frame(self.screendump_path)


# ---------------------------------------------------------------------------
# Aim configuration + core loop (mirrors menu_pulse_click.aim evidence shape)
# ---------------------------------------------------------------------------
@dataclass
class AimConfig:
    tolerance_px: int = 8
    initial_scale: float = 1.0
    max_iterations: int = 12
    max_no_motion: int = 3
    max_step_px: int = 8
    saturate_step_px: int = 300
    saturate_count: int = 12
    click_hold_ms: int = 120
    click_repeats: int = 1
    transition_min_pixels: int = 12000
    scale_bounds: tuple[float, float] = (0.25, 4.0)
    abs_mode: bool = False
    abs_width: int = 800
    abs_height: int = 600
    reveal_step_px: int = 40


def _refine_scale(scale: float, prev: tuple[int, int], npos: tuple[int, int],
                  delta: tuple[int, int], bounds: tuple[float, float]) -> float:
    """Estimate guest steps->pixels ratio from the observed vs commanded motion."""
    ratios: list[float] = []
    if delta[0]:
        ratios.append((npos[0] - prev[0]) / delta[0])
    if delta[1]:
        ratios.append((npos[1] - prev[1]) / delta[1])
    ratios = [r for r in ratios if bounds[0] <= r <= bounds[1]]
    if ratios:
        return sum(ratios) / len(ratios)
    return scale


def aim_point(
    sender: GuestSender,
    target: tuple[int, int],
    config: AimConfig,
    *,
    prev_frame: np.ndarray | None = None,
    last_pos: tuple[int, int] | None = None,
    scale: float | None = None,
) -> dict[str, Any]:
    """Converge the guest cursor on ``target`` and report honest per-point evidence.

    Fails closed: if the injected VM never moves the cursor (identical frames ->
    no diff -> no measured position), it records ``stuck`` and NEVER reports
    convergence. Convergence requires a MEASURED cursor position within tolerance,
    so a stuck VM can never produce a false pass.
    """
    scale = config.initial_scale if scale is None else scale
    result: dict[str, Any] = {
        "target": list(target),
        "iterations": [],
        "converged": False,
        "aimed_pos": None,
        "aim_error_px": None,
        "move_delta": None,
        "scale": round(scale, 3),
        "no_motion_iterations": 0,
        "stuck": False,
    }
    frame = sender.capture() if prev_frame is None else prev_frame
    pos = last_pos
    no_motion = 0

    for it in range(config.max_iterations):
        if pos is None:
            # No known position yet: nudge toward the target to reveal the cursor.
            step = config.reveal_step_px
            delta = (_sign(target[0]) * min(step, abs(target[0])) or step,
                     _sign(target[1]) * min(step, abs(target[1])) or step)
        else:
            residual = (target[0] - pos[0], target[1] - pos[1])
            delta = (int(round(residual[0] / scale)), int(round(residual[1] / scale)))
            if delta == (0, 0):
                # Rounded residual is zero: already at the target within a step.
                result.update({
                    "converged": True,
                    "aimed_pos": list(pos),
                    "aim_error_px": max(abs(pos[0] - target[0]), abs(pos[1] - target[1])),
                    "move_delta": [0, 0],
                    "scale": round(scale, 3),
                })
                break

        if config.abs_mode:
            sender.move_abs(target[0], target[1])
        else:
            sender.move_rel(*delta)
        curr = sender.capture()
        changed = int(menu_pulse_click.changed_pixels(frame, curr))
        npos = menu_pulse_click.cursor_from_diff(frame, curr, pos)
        row: dict[str, Any] = {
            "it": it,
            "delta": list(delta),
            "pos": list(npos) if npos else None,
            "changed_pixels": changed,
        }
        result["iterations"].append(row)
        frame = curr

        if npos is None:
            no_motion += 1
            result["no_motion_iterations"] = no_motion
            if no_motion >= config.max_no_motion:
                result["stuck"] = True
                break
            continue
        no_motion = 0

        prev_pos = pos
        if prev_pos is not None and delta != (0, 0) and not config.abs_mode:
            scale = _refine_scale(scale, prev_pos, npos, delta, config.scale_bounds)
            row["scale"] = round(scale, 3)
        pos = npos
        err = max(abs(npos[0] - target[0]), abs(npos[1] - target[1]))
        row["aim_error_px"] = err
        if err <= config.tolerance_px:
            result.update({
                "converged": True,
                "aimed_pos": list(npos),
                "aim_error_px": err,
                "move_delta": list(delta),
                "scale": round(scale, 3),
            })
            break

    if not result["converged"] and pos is not None:
        result["aimed_pos"] = list(pos)
        result["aim_error_px"] = max(abs(pos[0] - target[0]), abs(pos[1] - target[1]))
    result["scale"] = round(scale, 3)
    result["last_frame"] = frame
    result["last_pos"] = pos
    return result


def click_and_verify(sender: GuestSender, pre_frame: np.ndarray, config: AimConfig) -> dict[str, Any]:
    """Click while at the aimed point and verify a frame transition occurred.

    Reuses menu_pulse_click.changed_pixels so a transition is reported when the
    post-click frame differs and NONE when it is identical, exactly like the host
    lane. The post frame is returned so the caller can rebaseline.
    """
    sender.click(config.click_hold_ms, repeats=config.click_repeats)
    after = sender.capture()
    changed = int(menu_pulse_click.changed_pixels(pre_frame, after))
    return {
        "clicked": True,
        "changed_pixels": changed,
        "transition_verified": bool(changed > config.transition_min_pixels),
        "post_frame": after,
    }


def parse_points(text: str) -> list[tuple[str, int, int]]:
    """Reuse menu_pulse_click's 'x,y' / 'name:x,y' point parser."""
    return menu_pulse_click.parse_points(text)


def run_aim_points(
    sender: GuestSender,
    points: list[tuple[str, int, int]],
    config: AimConfig,
    *,
    aim_only: bool = False,
    saturate: bool = True,
) -> dict[str, Any]:
    """Aim (and optionally click) each guest validation point; emit host-shaped evidence."""
    result: dict[str, Any] = {
        "input_mechanism": INPUT_MECHANISM,
        "engine_model": ENGINE_MODEL,
        "proof_class": GUEST_PROOF_CLASS,
        "transport": "qmp-guest",
        "mode": "aim-points",
        "aim_only": bool(aim_only),
        "abs_mode": bool(config.abs_mode),
        "aim_points": [{"name": name, "target": [x, y]} for name, x, y in points],
        "steps": [],
        "aim_points_total": len(points),
        "aim_points_converged": 0,
    }
    scale = config.initial_scale
    converged = 0

    for name, tx, ty in points:
        # Re-establish a known origin per point (matches the qmp clickrel cadence).
        last_pos: tuple[int, int] | None = None
        if saturate and not config.abs_mode:
            sender.saturate(config.saturate_step_px, config.saturate_count)
            last_pos = (0, 0)
        frame = sender.capture()

        row: dict[str, Any] = {"name": name, "target": [tx, ty]}
        aimed = aim_point(sender, (tx, ty), config, prev_frame=frame,
                          last_pos=last_pos, scale=scale)
        frame = aimed.pop("last_frame")
        aimed_last_pos = aimed.pop("last_pos")
        scale = float(aimed.get("scale") or scale)
        row["aim"] = aimed
        row["converged"] = bool(aimed["converged"])

        if not aimed["converged"]:
            row["clicked"] = False
            row["transition_verified"] = False
            result["steps"].append(row)
            continue
        converged += 1

        if aim_only:
            row["clicked"] = False
            row["aim_only"] = True
            result["steps"].append(row)
            continue

        verify = click_and_verify(sender, frame, config)
        frame = verify.pop("post_frame")
        row.update(verify)
        result["steps"].append(row)

    result["aim_points_converged"] = converged
    result["all_points_converged"] = converged == len(points)
    result["all_steps_accounted"] = len(result["steps"]) == len(points)
    return result


# ---------------------------------------------------------------------------
# Offline op-plan (dry run): encode the QMP ops a run WOULD send, no socket
# ---------------------------------------------------------------------------
def plan_ops(points: list[tuple[str, int, int]], config: AimConfig) -> list[dict[str, Any]]:
    """Encode the saturate/move/click op sequence per point for offline inspection.

    This is a PLAN, not aim evidence: without live frames there is no feedback
    loop, so the move is the first-pass best guess (absolute if usb-tablet mode,
    otherwise the target scaled by the initial step ratio and sub-stepped).
    """
    plan: list[dict[str, Any]] = []
    for name, tx, ty in points:
        ops: list[dict[str, Any]] = []
        if config.abs_mode:
            ops.append(encode_abs_move(tx, ty, config.abs_width, config.abs_height))
        else:
            for _ in range(config.saturate_count):
                ops.append(encode_rel_move(-config.saturate_step_px, -config.saturate_step_px))
            gx = int(round(tx / config.initial_scale))
            gy = int(round(ty / config.initial_scale))
            for sx, sy in step_moves(gx, gy, config.max_step_px):
                ops.append(encode_rel_move(sx, sy))
        for _ in range(max(1, config.click_repeats)):
            ops.append(encode_button(True))
            ops.append(encode_button(False))
        plan.append({"name": name, "target": [tx, ty], "op_count": len(ops), "ops": ops})
    return plan


def _config_from_args(args: argparse.Namespace) -> AimConfig:
    return AimConfig(
        tolerance_px=args.tolerance,
        initial_scale=args.initial_scale,
        max_iterations=args.max_iterations,
        max_no_motion=args.max_no_motion,
        max_step_px=args.max_step,
        saturate_step_px=args.saturate_step,
        saturate_count=args.saturate_count,
        click_hold_ms=args.click_hold_ms,
        click_repeats=args.click_repeats,
        transition_min_pixels=args.transition_min_pixels,
        abs_mode=args.abs_mode,
        abs_width=args.abs_width,
        abs_height=args.abs_height,
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--aim-points", required=True,
                    help="semicolon list of engineX,engineY (or name:engineX,engineY) guest points")
    ap.add_argument("--aim-only", action="store_true", help="plan aim without a click")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", default=True,
                      help="(default) emit the offline QMP op plan; opens no socket")
    mode.add_argument("--execute", action="store_true",
                      help="live QMP run against a VM (separately approval-gated; not wired here)")
    ap.add_argument("--abs-mode", action="store_true", help="usb-tablet absolute positioning")
    ap.add_argument("--abs-width", type=int, default=800)
    ap.add_argument("--abs-height", type=int, default=600)
    ap.add_argument("--tolerance", type=int, default=8)
    ap.add_argument("--initial-scale", type=float, default=1.0)
    ap.add_argument("--max-iterations", type=int, default=12)
    ap.add_argument("--max-no-motion", type=int, default=3)
    ap.add_argument("--max-step", type=int, default=8)
    ap.add_argument("--saturate-step", type=int, default=300)
    ap.add_argument("--saturate-count", type=int, default=12)
    ap.add_argument("--click-hold-ms", type=int, default=120)
    ap.add_argument("--click-repeats", type=int, default=1)
    ap.add_argument("--transition-min-pixels", type=int, default=12000)
    ap.add_argument("--json", type=Path)
    return ap.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.execute:
        raise SystemExit(
            "live QMP guest execution is separately approval-gated and is not wired in this "
            "repo-only lane; supply a socket-backed transport to run_aim_points() under an "
            "approved visible-runtime pass instead"
        )
    points = parse_points(args.aim_points)
    config = _config_from_args(args)
    plan = plan_ops(points, config)
    report = {
        "input_mechanism": INPUT_MECHANISM,
        "engine_model": ENGINE_MODEL,
        "proof_class": GUEST_PROOF_CLASS,
        "opens_socket": OPENS_SOCKET,
        "mode": "dry-run-op-plan",
        "abs_mode": bool(config.abs_mode),
        "aim_only": bool(args.aim_only),
        "point_count": len(points),
        "plan": plan,
    }
    text = json.dumps(report, indent=2)
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(text, encoding="ascii")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
