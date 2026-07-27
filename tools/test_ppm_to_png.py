#!/usr/bin/env python3
"""Fixture tests for ppm_to_png.py."""

from __future__ import annotations

import struct
import sys
import tempfile
import zlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import ppm_to_png  # noqa: E402


def make_ppm(path: Path, width: int, height: int, pixel_at) -> Path:
    body = bytearray(f"P6\n{width} {height}\n255\n".encode("ascii"))
    for y in range(height):
        for x in range(width):
            body.extend(bytes(pixel_at(x, y)))
    path.write_bytes(bytes(body))
    return path


def read_png_ihdr(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n", "bad PNG signature"
    # First chunk after the signature must be IHDR.
    length = struct.unpack(">I", data[8:12])[0]
    assert data[12:16] == b"IHDR", "first chunk is not IHDR"
    w, h = struct.unpack(">II", data[16:24])
    # Verify every chunk CRC so we know write_png produced a valid file.
    pos = 8
    while pos < len(data):
        clen = struct.unpack(">I", data[pos:pos + 4])[0]
        kind = data[pos + 4:pos + 8]
        payload = data[pos + 8:pos + 8 + clen]
        crc = struct.unpack(">I", data[pos + 8 + clen:pos + 12 + clen])[0]
        assert (zlib.crc32(kind + payload) & 0xFFFFFFFF) == crc, f"bad CRC on {kind!r}"
        pos += 12 + clen
        if kind == b"IEND":
            break
    return w, h


def test_roundtrip_dimensions(tmp: Path) -> None:
    ppm = make_ppm(tmp / "a.ppm", 8, 4, lambda x, y: (x * 30, y * 60, 10))
    stats = ppm_to_png.convert(ppm)
    assert stats["width"] == 8 and stats["height"] == 4, stats
    assert read_png_ihdr(Path(stats["png"])) == (8, 4)


def test_nonblack_and_color_stats(tmp: Path) -> None:
    # Half the rows black, half a solid colour -> 50% nonblack, 2 colours.
    def px(x: int, y: int):
        return (0, 0, 0) if y < 2 else (12, 34, 56)
    frame = ppm_to_png.parse_ppm((make_ppm(tmp / "b.ppm", 4, 4, px)).read_bytes())
    s = ppm_to_png.frame_stats(frame)
    assert s["nonblack_percent"] == 50.0, s
    assert s["color_count"] == 2, s


def test_partial_frame_rejected(tmp: Path) -> None:
    # A screendump read mid-write is shorter than w*h*3 - must fail closed, never
    # silently produce a garbage/black image (the exact bug that misread an
    # 800x600 HD frame as 640x480).
    p = tmp / "partial.ppm"
    good = (make_ppm(tmp / "full.ppm", 10, 10, lambda x, y: (1, 2, 3))).read_bytes()
    p.write_bytes(good[: len(good) - 30])  # drop 10 pixels' worth
    try:
        ppm_to_png.parse_ppm(p.read_bytes())
    except ValueError as exc:
        assert "short" in str(exc).lower(), exc
    else:
        raise AssertionError("partial PPM was accepted")


def test_bad_magic_rejected(tmp: Path) -> None:
    p = tmp / "bad.ppm"
    p.write_bytes(b"P3\n2 2\n255\n" + b"\x00" * 12)
    try:
        ppm_to_png.parse_ppm(p.read_bytes())
    except ValueError as exc:
        assert "magic" in str(exc).lower() or "P6" in str(exc), exc
    else:
        raise AssertionError("non-P6 PPM was accepted")


def test_explicit_output_path(tmp: Path) -> None:
    ppm = make_ppm(tmp / "c.ppm", 3, 3, lambda x, y: (255, 255, 255))
    out = tmp / "nested" / "explicit.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    stats = ppm_to_png.convert(ppm, out)
    assert Path(stats["png"]) == out and out.exists()
    assert stats["nonblack_percent"] == 100.0, stats


def main() -> int:
    tests = [
        test_roundtrip_dimensions,
        test_nonblack_and_color_stats,
        test_partial_frame_rejected,
        test_bad_magic_rejected,
        test_explicit_output_path,
    ]
    with tempfile.TemporaryDirectory() as raw:
        tmp = Path(raw)
        for t in tests:
            t(tmp)
            print(f"PASS {t.__name__}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
