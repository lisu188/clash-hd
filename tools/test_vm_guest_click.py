#!/usr/bin/env python3
"""Offline tests for vm_guest_click.py.

Drives the guest aiming core with a FAKE QMP transport and synthetic PPM frames
(no socket, no live VM). The fake VM writes real P6 PPMs that the tool decodes
through the real ppm_to_png path, so the QMP encoding, the frame decode, and the
menu_pulse_click diff primitives are all exercised end to end. The fake sender
lets us assert: convergence on a target with per-point aim error, scale refinement
under guest acceleration, a transition reported only when frames differ, and a
FAIL-CLOSED result (no false convergence) when the VM never moves.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import vm_guest_click as vg  # noqa: E402

BG_NORMAL = 20
BG_TRANSITION = 90
CURSOR = 255
BLOCK = 12


class FakeVm:
    """A synthetic QMP transport: processes input-send-event/screendump commands.

    It models a guest cursor moved by relative events (times ``move_scale`` to
    emulate pointer acceleration), clamped in-frame, and renders a real PPM on
    screendump. ``stuck`` ignores all motion (the never-moves case); a click flips
    the background when ``transition_on_click`` is set (the transition case).
    """

    def __init__(self, out_dir: Path, *, width: int = 320, height: int = 240,
                 move_scale: float = 1.0, stuck: bool = False,
                 transition_on_click: bool = False, start: tuple[int, int] = (77, 55)):
        self.out_dir = Path(out_dir)
        self.width = width
        self.height = height
        self.move_scale = move_scale
        self.stuck = stuck
        self.transition_on_click = transition_on_click
        self.fcx = float(start[0])
        self.fcy = float(start[1])
        self.bg = BG_NORMAL
        self.click_count = 0
        self.screendumps = 0

    # -- cursor model -------------------------------------------------------
    def _clamp(self) -> None:
        self.fcx = min(max(self.fcx, 0.0), float(self.width - BLOCK))
        self.fcy = min(max(self.fcy, 0.0), float(self.height - BLOCK))

    def _apply_rel(self, dx: int, dy: int) -> None:
        if self.stuck:
            return
        self.fcx += self.move_scale * dx
        self.fcy += self.move_scale * dy
        self._clamp()

    def _apply_abs(self, ax: int, ay: int) -> None:
        if self.stuck:
            return
        self.fcx = ax / vg.ABS_AXIS_MAX * self.width
        self.fcy = ay / vg.ABS_AXIS_MAX * self.height
        self._clamp()

    # -- rendering ----------------------------------------------------------
    def _render(self, path: Path) -> None:
        arr = np.full((self.height, self.width, 3), self.bg, dtype=np.uint8)
        cx, cy = int(round(self.fcx)), int(round(self.fcy))
        arr[cy:cy + BLOCK, cx:cx + BLOCK, :] = CURSOR
        body = f"P6\n{self.width} {self.height}\n255\n".encode("ascii") + arr.tobytes()
        path.write_bytes(body)

    # -- transport callable -------------------------------------------------
    def __call__(self, command: dict):
        execute = command.get("execute")
        if execute == "screendump":
            self.screendumps += 1
            self._render(Path(command["arguments"]["filename"]))
            return {"return": {}}
        if execute == "input-send-event":
            events = command["arguments"]["events"]
            dx = dy = 0
            ax = ay = None
            for ev in events:
                etype = ev["type"]
                data = ev["data"]
                if etype == "rel":
                    if data["axis"] == "x":
                        dx = data["value"]
                    else:
                        dy = data["value"]
                elif etype == "abs":
                    if data["axis"] == "x":
                        ax = data["value"]
                    else:
                        ay = data["value"]
                elif etype == "btn":
                    if not data["down"]:  # button up completes a click
                        self.click_count += 1
                        if self.transition_on_click:
                            self.bg = BG_TRANSITION
            if ax is not None and ay is not None:
                self._apply_abs(ax, ay)
            elif dx or dy:
                self._apply_rel(dx, dy)
            return {"return": {}}
        return {"return": {}}


def make_sender(vm: FakeVm, tmp: Path) -> vg.QmpGuestSender:
    return vg.QmpGuestSender(vm, screendump_path=tmp / "shot.ppm",
                             width=vm.width, height=vm.height)


# ---------------------------------------------------------------------------
# Encoder / helper unit tests
# ---------------------------------------------------------------------------
def test_encoders_match_wire_format(tmp: Path) -> None:
    rel = vg.encode_rel_move(-300, -300)
    assert rel["execute"] == "input-send-event"
    axes = [(e["data"]["axis"], e["data"]["value"]) for e in rel["arguments"]["events"]]
    assert axes == [("x", -300), ("y", -300)], rel

    abs_cmd = vg.encode_abs_move(400, 300, 800, 600)
    vals = {e["data"]["axis"]: e["data"]["value"] for e in abs_cmd["arguments"]["events"]}
    assert vals["x"] == round(400 / 800 * vg.ABS_AXIS_MAX), vals
    assert vals["y"] == round(300 / 600 * vg.ABS_AXIS_MAX), vals

    down = vg.encode_button(True)
    assert down["arguments"]["events"][0]["data"] == {"button": "left", "down": True}
    shot = vg.encode_screendump("x.ppm")
    assert shot == {"execute": "screendump", "arguments": {"filename": "x.ppm"}}


def test_step_moves_are_sub_threshold(tmp: Path) -> None:
    steps = vg.step_moves(20, -5, 8)
    assert all(abs(sx) <= 8 and abs(sy) <= 8 for sx, sy in steps), steps
    assert (sum(sx for sx, _ in steps), sum(sy for _, sy in steps)) == (20, -5)
    assert vg.step_moves(0, 0, 8) == []


def test_frame_decode_reuses_ppm_to_png(tmp: Path) -> None:
    vm = FakeVm(tmp, start=(10, 10))
    p = tmp / "decode.ppm"
    vm._render(p)
    arr = vg.parse_frame_file(p)
    assert arr.shape == (vm.height, vm.width, 3), arr.shape
    assert arr.dtype == np.int16


# ---------------------------------------------------------------------------
# Aim-loop behaviour
# ---------------------------------------------------------------------------
def test_converges_and_records_aim_error(tmp: Path) -> None:
    vm = FakeVm(tmp, move_scale=1.0)
    sender = make_sender(vm, tmp)
    cfg = vg.AimConfig()
    result = vg.run_aim_points(sender, [("map-center", 180, 140)], cfg, aim_only=True)

    assert result["proof_class"] == vg.GUEST_PROOF_CLASS
    assert result["proof_class"] != "manual_directinput"
    assert result["all_points_converged"] is True
    step = result["steps"][0]
    assert step["converged"] is True
    aim = step["aim"]
    assert aim["aimed_pos"] == [180, 140], aim
    assert aim["aim_error_px"] == 0, aim
    assert aim["stuck"] is False
    # every measured iteration carries a per-point aim error
    measured = [row for row in aim["iterations"] if row["pos"] is not None]
    assert measured and all("aim_error_px" in row for row in measured), aim["iterations"]


def test_refines_scale_under_guest_acceleration(tmp: Path) -> None:
    # A 1.5x accelerated guest: dead-reckoning overshoots, so convergence MUST
    # come from the feedback loop refining the scale, not a lucky single move.
    vm = FakeVm(tmp, move_scale=1.5)
    sender = make_sender(vm, tmp)
    cfg = vg.AimConfig(tolerance_px=8)
    # Saturate to a real (0,0) origin so last_pos=(0,0) is truthful.
    sender.saturate(cfg.saturate_step_px, cfg.saturate_count)
    aimed = vg.aim_point(sender, (180, 140), cfg, last_pos=(0, 0))
    assert aimed["converged"] is True, aimed
    assert aimed["aim_error_px"] <= cfg.tolerance_px, aimed
    assert 1.2 <= aimed["scale"] <= 1.9, aimed["scale"]
    assert len(aimed["iterations"]) >= 2, aimed["iterations"]


def test_fails_closed_when_vm_never_moves(tmp: Path) -> None:
    vm = FakeVm(tmp, stuck=True)
    sender = make_sender(vm, tmp)
    cfg = vg.AimConfig(max_no_motion=3, max_iterations=8)
    result = vg.run_aim_points(sender, [("stuck", 180, 140)], cfg, aim_only=True)

    step = result["steps"][0]
    assert step["converged"] is False, step
    assert result["all_points_converged"] is False
    aim = step["aim"]
    assert aim["stuck"] is True, aim
    assert aim["no_motion_iterations"] >= cfg.max_no_motion, aim
    # No measured position was ever recorded -> no possibility of a false pass.
    assert all(row["pos"] is None for row in aim["iterations"]), aim["iterations"]
    assert aim["converged"] is False


def test_transition_reported_only_when_frame_changes(tmp: Path) -> None:
    cfg = vg.AimConfig()

    moving = FakeVm(tmp / "t", transition_on_click=True)
    (tmp / "t").mkdir(exist_ok=True)
    s1 = make_sender(moving, tmp / "t")
    pre = s1.capture()
    verify = vg.click_and_verify(s1, pre, cfg)
    assert verify["transition_verified"] is True, verify
    assert verify["changed_pixels"] > cfg.transition_min_pixels

    static = FakeVm(tmp / "s", transition_on_click=False)
    (tmp / "s").mkdir(exist_ok=True)
    s2 = make_sender(static, tmp / "s")
    pre2 = s2.capture()
    verify2 = vg.click_and_verify(s2, pre2, cfg)
    assert verify2["transition_verified"] is False, verify2
    assert verify2["changed_pixels"] == 0, verify2


def test_click_path_emits_button_ops(tmp: Path) -> None:
    vm = FakeVm(tmp, transition_on_click=True)
    sender = make_sender(vm, tmp)
    cfg = vg.AimConfig()
    result = vg.run_aim_points(sender, [("centered", 160, 120)], cfg)
    step = result["steps"][0]
    assert step["clicked"] is True and step["transition_verified"] is True, step
    # the exact QMP button ops reached the transport
    downs = [c for c in sender.sent_commands
             if c["execute"] == "input-send-event"
             and c["arguments"]["events"][0]["type"] == "btn"
             and c["arguments"]["events"][0]["data"]["down"] is True]
    assert downs, "no button-down op was emitted"
    # a saturate op (big negative relative move) was emitted before aiming
    assert vg.encode_rel_move(-cfg.saturate_step_px, -cfg.saturate_step_px) in sender.sent_commands


def test_absolute_mode_uses_usb_tablet_events(tmp: Path) -> None:
    vm = FakeVm(tmp, move_scale=1.0)
    sender = make_sender(vm, tmp)
    cfg = vg.AimConfig(abs_mode=True, abs_width=vm.width, abs_height=vm.height)
    sender.saturate(cfg.saturate_step_px, cfg.saturate_count)
    aimed = vg.aim_point(sender, (150, 110), cfg, last_pos=(0, 0))
    assert aimed["converged"] is True, aimed
    assert any(
        c["arguments"]["events"][0]["type"] == "abs"
        for c in sender.sent_commands if c["execute"] == "input-send-event"
    ), "no absolute move op emitted in abs mode"


# ---------------------------------------------------------------------------
# CLI: offline dry-run plan opens no socket; --execute is gated
# ---------------------------------------------------------------------------
def test_cli_dry_run_plan_opens_no_socket(tmp: Path) -> None:
    out = tmp / "plan.json"
    rc = vg.main(["--aim-points", "load:120,90;edge:300,10", "--json", str(out)])
    assert rc == 0
    import json
    report = json.loads(out.read_text(encoding="ascii"))
    assert report["opens_socket"] is False
    assert report["proof_class"] == vg.GUEST_PROOF_CLASS
    assert report["point_count"] == 2
    ops = report["plan"][0]["ops"]
    assert ops[0]["execute"] == "input-send-event"
    assert ops[-1]["arguments"]["events"][0]["type"] == "btn"


def test_cli_execute_is_gated(tmp: Path) -> None:
    try:
        vg.main(["--aim-points", "x:10,10", "--execute"])
    except SystemExit as exc:
        assert "approval-gated" in str(exc), exc
    else:
        raise AssertionError("--execute was not gated")


def main() -> int:
    tests = [
        test_encoders_match_wire_format,
        test_step_moves_are_sub_threshold,
        test_frame_decode_reuses_ppm_to_png,
        test_converges_and_records_aim_error,
        test_refines_scale_under_guest_acceleration,
        test_fails_closed_when_vm_never_moves,
        test_transition_reported_only_when_frame_changes,
        test_click_path_emits_button_ops,
        test_absolute_mode_uses_usb_tablet_events,
        test_cli_dry_run_plan_opens_no_socket,
        test_cli_execute_is_gated,
    ]
    with tempfile.TemporaryDirectory() as raw:
        tmp = Path(raw)
        for t in tests:
            t(tmp)
            print(f"PASS {t.__name__}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
