#!/usr/bin/env python3
"""Convert QEMU QMP screendump PPM frames to PNG, with basic frame stats.

The QMP ``screendump`` command writes a binary P6 PPM (uncompressed RGB). This
helper turns those into viewable PNGs and reports width/height plus a couple of
cheap content metrics used by the VM guest lanes (``scripts/vm/*``): nonblack
percentage and distinct-colour count. It is pure-stdlib (``struct`` + ``zlib``)
so it needs no third-party image library, matching the repo's other capture
tools (e.g. ``tools/capture_geometry.py``).

Repo-only: reads/writes image files, launches nothing, sends no input.

    python tools/ppm_to_png.py frame.ppm                 # -> frame.png, prints stats
    python tools/ppm_to_png.py frame.ppm out.png
    python tools/ppm_to_png.py --glob 'run/*.ppm'        # batch
"""

from __future__ import annotations

import argparse
import glob as globmod
import struct
import zlib
from pathlib import Path
from typing import NamedTuple


class PpmFrame(NamedTuple):
    width: int
    height: int
    pixels: bytes  # raw RGB, width*height*3 bytes


def parse_ppm(data: bytes) -> PpmFrame:
    """Parse a binary P6 PPM. Raises ValueError on a malformed/partial file."""
    if data[:2] != b"P6":
        raise ValueError("not a binary P6 PPM (bad magic)")
    # Header is 'P6\n<w> <h>\n<maxval>\n' but whitespace between fields may vary,
    # so tokenize the first four whitespace-separated fields robustly.
    fields: list[bytes] = []
    idx = 0
    n = len(data)
    while len(fields) < 4 and idx < n:
        while idx < n and data[idx] in b" \t\r\n":
            idx += 1
        # A '#' comment runs to end of line (rare from QEMU, handled for safety).
        if idx < n and data[idx:idx + 1] == b"#":
            while idx < n and data[idx] not in b"\r\n":
                idx += 1
            continue
        start = idx
        while idx < n and data[idx] not in b" \t\r\n":
            idx += 1
        fields.append(data[start:idx])
    if len(fields) < 4:
        raise ValueError("truncated PPM header")
    _magic, w_b, h_b, max_b = fields[:4]
    width, height = int(w_b), int(h_b)
    # Pixel data starts one whitespace byte after the maxval token.
    pixel_start = idx + 1
    expected = width * height * 3
    pixels = data[pixel_start:pixel_start + expected]
    if len(pixels) < expected:
        raise ValueError(
            f"PPM pixel data short: got {len(pixels)} of {expected} bytes "
            f"(w={width} h={height}) - file may be a partial/mid-write screendump"
        )
    return PpmFrame(width, height, pixels)


def _png_chunk(kind: bytes, payload: bytes) -> bytes:
    crc = zlib.crc32(kind + payload) & 0xFFFFFFFF
    return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", crc)


def write_png(frame: PpmFrame, out_path: Path) -> None:
    w, h, px = frame
    rows = bytearray()
    stride = w * 3
    for y in range(h):
        rows.append(0)  # filter type 0 (None) per scanline
        rows.extend(px[y * stride:(y + 1) * stride])
    data = bytearray(b"\x89PNG\r\n\x1a\n")
    data.extend(_png_chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)))
    data.extend(_png_chunk(b"IDAT", zlib.compress(bytes(rows), 6)))
    data.extend(_png_chunk(b"IEND", b""))
    out_path.write_bytes(bytes(data))


def frame_stats(frame: PpmFrame) -> dict[str, float | int]:
    w, h, px = frame
    total = w * h
    nonblack = 0
    colors: set[bytes] = set()
    for i in range(0, len(px), 3):
        rgb = px[i:i + 3]
        if rgb[0] or rgb[1] or rgb[2]:
            nonblack += 1
        colors.add(rgb)
    return {
        "width": w,
        "height": h,
        "nonblack_percent": round(100.0 * nonblack / total, 2) if total else 0.0,
        "color_count": len(colors),
    }


def convert(ppm_path: Path, png_path: Path | None = None) -> dict[str, float | int]:
    frame = parse_ppm(ppm_path.read_bytes())
    if png_path is None:
        png_path = ppm_path.with_suffix(".png")
    write_png(frame, png_path)
    stats = frame_stats(frame)
    stats["png"] = str(png_path)  # type: ignore[assignment]
    return stats


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Convert QMP screendump PPM to PNG.")
    parser.add_argument("ppm", nargs="?", type=Path, help="input .ppm")
    parser.add_argument("png", nargs="?", type=Path, help="output .png (default: alongside input)")
    parser.add_argument("--glob", help="convert every file matching this glob instead")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.glob:
        matches = sorted(globmod.glob(args.glob))
        if not matches:
            print(f"no files match {args.glob}")
            return 1
        for m in matches:
            stats = convert(Path(m))
            print(f"{m}: {stats['width']}x{stats['height']} "
                  f"nonblack={stats['nonblack_percent']}% colors={stats['color_count']}")
        return 0
    if not args.ppm:
        print("usage: ppm_to_png.py <in.ppm> [out.png] | --glob '<pattern>'")
        return 2
    stats = convert(args.ppm, args.png)
    print(f"{args.ppm}: {stats['width']}x{stats['height']} "
          f"nonblack={stats['nonblack_percent']}% colors={stats['color_count']} -> {stats['png']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
