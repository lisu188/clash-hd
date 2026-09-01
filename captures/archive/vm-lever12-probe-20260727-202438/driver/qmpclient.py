#!/usr/bin/env python3
"""Persistent QMP-over-TCP client for the Clash HD guest (port 4445).

PS/2 relative mouse only. One socket, many events -> no per-move PowerShell
spawn, precise control of event count / delta / inter-event delay. Every input
command is appended to a JSONL log so guest evidence carries a qmp_input_log_ref.
"""
from __future__ import annotations
import socket, json, time
from pathlib import Path
import numpy as np


class Qmp:
    def __init__(self, port=4445, host="127.0.0.1", log_path=None):
        self.sock = socket.create_connection((host, port), timeout=15)
        self.f = self.sock.makefile("rwb")
        self.f.readline()  # greeting
        self._cmd({"execute": "qmp_capabilities"})
        self.log_path = Path(log_path) if log_path else None
        if self.log_path:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def _cmd(self, obj):
        self.f.write((json.dumps(obj) + "\r\n").encode()); self.f.flush()
        # read until we get a return/error (skip async events)
        while True:
            line = self.f.readline()
            if not line:
                raise RuntimeError("qmp closed")
            msg = json.loads(line)
            if "return" in msg or "error" in msg:
                return msg

    def _log(self, kind, **kw):
        if self.log_path:
            rec = {"t": time.time(), "kind": kind, **kw}
            with self.log_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(rec) + "\n")

    def screendump(self, path):
        r = self._cmd({"execute": "screendump", "arguments": {"filename": str(path)}})
        return r

    def rel(self, dx, dy):
        self._cmd({"execute": "input-send-event", "arguments": {"events": [
            {"type": "rel", "data": {"axis": "x", "value": int(dx)}},
            {"type": "rel", "data": {"axis": "y", "value": int(dy)}},
        ]}})

    def move(self, dx, dy, step=8, delay=0.012):
        """Accumulating relative move in `step`-sized events, logged."""
        self._log("move", dx=int(dx), dy=int(dy), step=step, delay=delay)
        cx = cy = 0
        tx, ty = int(dx), int(dy)
        while cx != tx or cy != ty:
            sx = max(-step, min(step, tx - cx))
            sy = max(-step, min(step, ty - cy))
            self.rel(sx, sy)
            cx += sx; cy += sy
            if delay:
                time.sleep(delay)

    def home(self, n=12, step=40, reps=40, delay=0.004):
        """Drive hard to top-left. Many small negative events (accumulate)."""
        self._log("home", n=n, step=step, reps=reps)
        for _ in range(n):
            for _ in range(reps):
                self.rel(-step, -step)
                if delay:
                    time.sleep(delay)

    def click(self, hold=0.12):
        self._log("click", hold=hold)
        self._cmd({"execute": "input-send-event", "arguments": {"events": [
            {"type": "btn", "data": {"button": "left", "down": True}}]}})
        time.sleep(hold)
        self._cmd({"execute": "input-send-event", "arguments": {"events": [
            {"type": "btn", "data": {"button": "left", "down": False}}]}})

    def close(self):
        try:
            self.sock.close()
        except Exception:
            pass


def parse_ppm(data: bytes):
    if data[:2] != b"P6":
        raise ValueError("not P6")
    fields = []; idx = 0; n = len(data)
    while len(fields) < 4 and idx < n:
        while idx < n and data[idx] in b" \t\r\n": idx += 1
        start = idx
        while idx < n and data[idx] not in b" \t\r\n": idx += 1
        fields.append(data[start:idx])
    _m, wb, hb, mb = fields[:4]
    w, h = int(wb), int(hb); ps = idx + 1
    exp = w * h * 3
    px = data[ps:ps + exp]
    if len(px) < exp:
        raise ValueError(f"short {len(px)}/{exp}")
    return w, h, px


def grab(q: Qmp, path, retries=5):
    path = Path(path)
    for a in range(retries):
        q.screendump(path)
        time.sleep(0.12)
        try:
            w, h, px = parse_ppm(path.read_bytes())
            return np.frombuffer(px, np.uint8).reshape(h, w, 3).copy()
        except Exception:
            if a == retries - 1:
                raise
            time.sleep(0.2)


def changed_mask(cur, ref, thresh=45):
    d = np.abs(cur.astype(np.int16) - ref.astype(np.int16)).max(axis=2)
    return d > thresh


def blob(mask, region=None):
    m = mask
    if region:
        x0, y0, x1, y1 = region
        sub = np.zeros_like(m); sub[y0:y1, x0:x1] = m[y0:y1, x0:x1]; m = sub
    ys, xs = np.where(m)
    if len(xs) == 0:
        return None
    x_lo, x_hi = np.percentile(xs, [3, 97])
    y_lo, y_hi = np.percentile(ys, [3, 97])
    return {"count": int(len(xs)),
            "bbox": [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())],
            "center": [float((x_lo + x_hi) / 2), float((y_lo + y_hi) / 2)],
            "topleft": [int(xs.min()), int(ys.min())]}
