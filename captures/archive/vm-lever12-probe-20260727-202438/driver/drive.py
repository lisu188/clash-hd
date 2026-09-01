"""Paced driver helpers for the Clash HD Win98 guest (port 4445, -NoUsb).
Pacing rules (hard): every rel/btn event -> sleep >=0.2s; every screendump ->
sleep >=1.0s and verify full 1440015-byte file before reading."""
from __future__ import annotations
import time, json
from pathlib import Path
import numpy as np
import qmpclient as Q

D = Path(__file__).resolve().parent
SH = D / "shots"
SH.mkdir(exist_ok=True)
FULL = 1440015  # 800x600 P6 ppm size

_ctr = [0]

def paced_grab(q, tag):
    _ctr[0] += 1
    p = SH / f"{tag}_{_ctr[0]:03d}.ppm"
    for attempt in range(6):
        q.screendump(p)
        time.sleep(1.05)
        if p.exists() and p.stat().st_size == FULL:
            w,h,px = Q.parse_ppm(p.read_bytes())
            return np.frombuffer(px, np.uint8).reshape(h,w,3).copy(), p
        time.sleep(0.4)
    raise RuntimeError(f"grab failed for {p}")

def rel(q, dx, dy, settle=0.22):
    q.rel(int(dx), int(dy))
    time.sleep(settle)

def home(q, rounds=14, burst=20):
    """Drive hard up-left; alternate magnitude so consecutive events differ."""
    for r in range(rounds):
        mag = 40 if r % 2 == 0 else 44
        for _ in range(burst):
            q.rel(-mag, -mag)
            mag = 40 if mag == 44 else 44
            time.sleep(0.03)
        time.sleep(0.05)
    time.sleep(0.4)

def changed_mask(cur, ref, thresh=45):
    return Q.changed_mask(cur, ref, thresh)

def blob(mask):
    return Q.blob(mask)

def locate(cur, bg, thresh=45, near=None, radius=140):
    m = Q.changed_mask(cur, bg, thresh)
    if near is not None:
        H,W = m.shape
        yy,xx = np.ogrid[0:H,0:W]
        m = m & ((xx-near[0])**2 + (yy-near[1])**2 <= radius*radius)
    return Q.blob(m)

def build_bg(q, tag="bg"):
    """Scatter the cursor over the static menu and median frames -> cursorless bg.
    Uses a variety of (dx,dy) magnitudes/signs so the cursor lands in different
    spots regardless of accumulate-vs-deterministic model."""
    home(q)
    frames = []
    scatter = [(20,0),(0,20),(60,40),(-30,10),(40,-20),(90,90),(-50,-50),
               (120,30),(30,120),(-80,60),(70,-40),(200,200)]
    for (dx,dy) in scatter:
        rel(q, dx, dy)
        img,_ = paced_grab(q, tag)
        frames.append(img)
    med = np.median(np.stack(frames).astype(np.uint8), axis=0).astype(np.uint8)
    np.save(D/"bg.npy", med)
    return med
