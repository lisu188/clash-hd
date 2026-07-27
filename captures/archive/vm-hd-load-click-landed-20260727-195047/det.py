#!/usr/bin/env python3
"""Deterministic placement driver for the Clash HD Win98 guest.

Model discovered empirically: the engine cursor sprite position on each axis is
a deterministic function of the MOST-RECENT nonzero relative delta on that axis
(an unbound usb-tablet resets the per-axis baseline, so relative moves do not
accumulate). The map is linear & repeatable: pos ~= 4.0*delta + 14, saturating
near 521. So sprite_x is set by rel(dx,0) and sprite_y by rel(0,dy),
independently. We invert the calibrated table to place the sprite, verify by
frame diff, and refine by +/-1 delta. Only PS/2 relative input; no absolute.
"""
from __future__ import annotations
import time, json
from pathlib import Path
import numpy as np
import qmpclient as Q

D = Path(__file__).resolve().parent


def load_bg():
    w, h, px = Q.parse_ppm((D / "bg.ppm").read_bytes())
    return np.frombuffer(px, np.uint8).reshape(h, w, 3)


class Det:
    def __init__(self, port=4445, log_path=None):
        self.q = Q.Qmp(port=port, log_path=log_path or str(D / "logs" / "det.jsonl"))
        self.bg = load_bg()
        cur = json.load(open(D / "curve.json"))
        self.fx = {int(k): v for k, v in cur["fx"].items()}
        self.fy = {int(k): v for k, v in cur["fy"].items()}
        self._i = 0

    def snap(self, tag):
        self._i += 1
        name = f"{tag}_{self._i:03d}.ppm"
        img = Q.grab(self.q, D / name)
        return img, name

    def locate(self, tag="loc", near=None, radius=90):
        img, name = self.snap(tag)
        m = Q.changed_mask(img, self.bg, 45)
        if near is not None:
            H, W = m.shape
            yy, xx = np.ogrid[0:H, 0:W]
            m = m & ((xx - near[0]) ** 2 + (yy - near[1]) ** 2 <= radius * radius)
        return Q.blob(m), img, name

    def _invert(self, table, target):
        # nearest-by-position delta, then linear refine
        best = min(table.items(), key=lambda kv: abs(kv[1] - target))
        return best[0]

    def _invert_interp(self, table, target):
        """Linear-interpolated inverse: pick the delta whose calibrated position
        brackets `target` and interpolate for sub-unit accuracy."""
        pts = sorted(table.items(), key=lambda kv: kv[1])  # by position
        # clamp
        if target <= pts[0][1]:
            return pts[0][0]
        if target >= pts[-1][1]:
            return pts[-1][0]
        for (d0, p0), (d1, p1) in zip(pts, pts[1:]):
            if p0 <= target <= p1:
                if p1 == p0:
                    return d0
                frac = (target - p0) / (p1 - p0)
                return int(round(d0 + frac * (d1 - d0)))
        return pts[-1][0]

    def place_open(self, tx, ty):
        """Open-loop deterministic placement via curve inversion (no frame
        feedback). Use on screens where the menu background diff is invalid."""
        dx = self._invert_interp(self.fx, tx)
        dy = self._invert_interp(self.fy, ty)
        self.set_x(dx); self.set_y(dy)
        return dx, dy

    def build_screen_bg(self, tag="sbg"):
        """Build a cursorless background for the CURRENT screen by placing the
        cursor at several far-apart open-loop positions and taking the per-pixel
        median (the cursor moves, the screen stays)."""
        frames = []
        for (tx, ty) in [(90, 90), (500, 110), (110, 480), (500, 480), (300, 300)]:
            self.place_open(tx, ty)
            img, _ = self.snap(tag)
            frames.append(img)
        med = np.median(np.stack(frames).astype(np.uint8), axis=0).astype(np.uint8)
        return med

    def set_x(self, dx):
        self.q.rel(int(dx), 0); self.q._log("set_x", dx=int(dx)); time.sleep(0.26)

    def set_y(self, dy):
        self.q.rel(0, int(dy)); self.q._log("set_y", dy=int(dy)); time.sleep(0.26)

    def place(self, tx, ty, tol=6, tag="pl", max_ref=6, verbose=True):
        dx = self._invert(self.fx, tx)
        dy = self._invert(self.fy, ty)
        self.set_x(dx); self.set_y(dy)
        last = None
        for it in range(max_ref):
            b, _, name = self.locate(tag, near=last)
            if b is None:
                b, _, name = self.locate(tag, near=None)
            if b is None:
                if verbose: print("  place: cursor not found")
                return None, dx, dy
            cx, cy = b["center"]; last = (cx, cy)
            ex, ey = tx - cx, ty - cy
            if verbose:
                print(f"  place it{it} d=({dx},{dy}) center=({cx:.0f},{cy:.0f}) err=({ex:.0f},{ey:.0f})")
            if abs(ex) <= tol and abs(ey) <= tol:
                return (cx, cy), dx, dy
            if abs(ex) > tol:
                dx += int(round(ex / 4.0)) or (1 if ex > 0 else -1)
                dx = max(16, min(128, dx)); self.set_x(dx)
            if abs(ey) > tol:
                dy += int(round(ey / 4.0)) or (1 if ey > 0 else -1)
                dy = max(16, min(128, dy)); self.set_y(dy)
        b, _, _ = self.locate(tag, near=last)
        return (b["center"] if b else None), dx, dy

    def click(self, hold=0.14):
        self.q.click(hold=hold)

    def close(self):
        self.q.close()
