#!/usr/bin/env python3
"""Closed-loop frame-feedback aim driver for the Clash HD Win98 guest.

- Locates the engine cursor reference-free by diffing against a median-built
  cursorless background (bg.ppm); the changed-blob center is the cursor.
- Moves ONLY via PS/2 relative single events, well spaced, never repeating an
  identical (dx,dy) (QEMU drops a rel event identical to its predecessor).
- Proportional control with per-step re-location; converges to a target blob
  center, then clicks in place. No absolute input is ever used.
"""
from __future__ import annotations
import time, json, argparse
from pathlib import Path
import numpy as np
import qmpclient as Q

D = Path(__file__).resolve().parent


def load_bg(path):
    w, h, px = Q.parse_ppm(Path(path).read_bytes())
    return np.frombuffer(px, np.uint8).reshape(h, w, 3)


class Aim:
    def __init__(self, port=4445, bg_path=None, log_path=None, shot_dir=None):
        self.q = Q.Qmp(port=port, log_path=log_path)
        self.bg = load_bg(bg_path or (D / "bg.ppm"))
        self.shot_dir = Path(shot_dir or D)
        self.shot_dir.mkdir(parents=True, exist_ok=True)
        self._last = None
        self._i = 0
        self._jit = 0
        self._last_center = None

    def snap(self, tag):
        self._i += 1
        name = f"{tag}_{self._i:03d}.ppm"
        return Q.grab(self.q, self.shot_dir / name), name

    def locate(self, tag="loc", thresh=45, near=None, radius=140):
        """Locate the cursor blob. If `near`=(x,y) given, only consider changed
        pixels within `radius` of it (rejects tear/noise far from the cursor)."""
        img, name = self.snap(tag)
        m = Q.changed_mask(img, self.bg, thresh)
        if near is not None:
            H, W = m.shape
            yy, xx = np.ogrid[0:H, 0:W]
            within = (xx - near[0]) ** 2 + (yy - near[1]) ** 2 <= radius * radius
            m = m & within
        b = Q.blob(m)
        return b, img, name

    def move_once(self, dx, dy, settle=0.26):
        """One PS/2 relative event. A ±1 jitter alternates on BOTH axes every
        call so no per-axis delta ever repeats (QEMU drops a repeated delta)."""
        dx = int(round(dx)); dy = int(round(dy))
        if dx == 0 and dy == 0:
            return
        self._jit ^= 1
        j = 1 if self._jit else -1
        # jitter toward the intended direction so it never reverses progress
        dx += j if dx >= 0 else -j
        dy += j if dy >= 0 else -j
        self.q.rel(dx, dy)
        self.q._log("aim_rel", dx=dx, dy=dy)
        self._last = (dx, dy)
        time.sleep(settle)

    def home(self, rounds=18, burst=25):
        # drive up-left with alternating magnitudes so no two consecutive events
        # are identical (avoids the dedup drop), each large enough to clamp.
        for r in range(rounds):
            mag = 30 if (r % 2 == 0) else 34
            for _ in range(burst):
                self.q.rel(-mag, -mag); mag = 30 if mag == 34 else 34
                time.sleep(0.002)
            time.sleep(0.04)
        self._last = None
        time.sleep(0.4)

    def aim_to(self, tx, ty, tol=8.0, max_iter=28, gain=0.55, cap=16,
               tag="aim", verbose=True):
        """Drive the cursor blob center to (tx,ty). Small capped steps keep the
        move in the ~1.4x near-linear gain zone. Returns (ok, center, history)."""
        hist = []
        near = self._last_center  # windowed locate once we have a fix
        for it in range(max_iter):
            b, _, name = self.locate(tag, near=near)
            if b is None:
                b, _, name = self.locate(tag, near=None)  # reacquire full-frame
            if b is None:
                self.move_once(6, 5)
                hist.append({"iter": it, "center": None, "note": "lost"})
                continue
            cx, cy = b["center"]
            self._last_center = (cx, cy)
            near = (cx, cy)
            ex, ey = tx - cx, ty - cy
            err = (ex * ex + ey * ey) ** 0.5
            hist.append({"iter": it, "center": [cx, cy], "err": round(err, 1), "shot": name})
            if verbose:
                print(f"  [{tag}] it{it:2d} center=({cx:.0f},{cy:.0f}) err={err:.1f} e=({ex:.0f},{ey:.0f})")
            if err <= tol:
                return True, (cx, cy), hist
            step_x = max(-cap, min(cap, ex * gain))
            step_y = max(-cap, min(cap, ey * gain))
            if abs(step_x) < 3 and abs(ex) >= 2:
                step_x = 3 if ex > 0 else -3
            if abs(step_y) < 3 and abs(ey) >= 2:
                step_y = 3 if ey > 0 else -3
            self.move_once(step_x, step_y)
        b, _, _ = self.locate(tag, near=near)
        if b:
            self._last_center = tuple(b["center"])
        return False, (b["center"] if b else None), hist

    def click(self, hold=0.14):
        self.q.click(hold=hold)

    def close(self):
        self.q.close()
