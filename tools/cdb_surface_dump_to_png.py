#!/usr/bin/env python3
"""Convert a Clash95 CDB 8-bit surface dump into a PNG visualization."""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
import zlib
from pathlib import Path
from typing import Any


PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def png_chunk(kind: bytes, payload: bytes) -> bytes:
    crc = zlib.crc32(kind)
    crc = zlib.crc32(payload, crc) & 0xFFFFFFFF
    return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", crc)


def load_palette(path: Path | None) -> tuple[bytes | None, str]:
    if path is None:
        return None, "grayscale-index"
    palette = path.read_bytes()
    expected = 256 * 4
    if len(palette) < expected:
        raise ValueError(f"palette dump is too small: expected at least {expected} bytes, found {len(palette)}")
    palette = palette[:expected]
    if all(palette[offset] == 0 and palette[offset + 1] == 0 and palette[offset + 2] == 0 for offset in range(0, expected, 4)):
        return None, "grayscale-index-empty-palette"
    return palette, "directdraw-palette"


def palette_rgb(palette: bytes | None, value: int) -> tuple[int, int, int]:
    if palette is None:
        return value, value, value
    offset = value * 4
    return palette[offset], palette[offset + 1], palette[offset + 2]


def indices_to_rgb_rows(indices: bytes, width: int, height: int, pitch: int, palette: bytes | None) -> bytes:
    rows = bytearray()
    for y in range(height):
        rows.append(0)  # filter type 0
        row = indices[y * pitch : y * pitch + width]
        if len(row) != width:
            raise ValueError(f"short row {y}: expected {width} bytes, found {len(row)}")
        for value in row:
            rows.extend(palette_rgb(palette, value))
    return bytes(rows)


def write_png(path: Path, indices: bytes, width: int, height: int, pitch: int, palette: bytes | None) -> bytes:
    raw_rows = indices_to_rgb_rows(indices, width, height, pitch, palette)
    payload = bytearray(PNG_SIGNATURE)
    payload.extend(
        png_chunk(
            b"IHDR",
            struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0),
        )
    )
    payload.extend(png_chunk(b"IDAT", zlib.compress(raw_rows, level=9)))
    payload.extend(png_chunk(b"IEND", b""))
    png = bytes(payload)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(png)
    return png


def convert(
    raw_path: Path,
    output_path: Path,
    width: int,
    height: int,
    pitch: int | None,
    metadata_path: Path | None,
    log_path: Path | None,
    palette_path: Path | None,
) -> dict[str, Any]:
    if width <= 0 or height <= 0:
        raise ValueError("width and height must be positive")
    effective_pitch = pitch or width
    if effective_pitch < width:
        raise ValueError("pitch must be greater than or equal to width")

    raw = raw_path.read_bytes()
    expected = effective_pitch * height
    if len(raw) < expected:
        raise ValueError(f"raw dump is too small: expected at least {expected} bytes, found {len(raw)}")
    used = raw[:expected]
    palette, palette_mode = load_palette(palette_path)
    png = write_png(output_path, used, width, height, effective_pitch, palette)
    metadata = {
        "raw_path": str(raw_path),
        "png_path": str(output_path),
        "log_path": str(log_path) if log_path else None,
        "palette_path": str(palette_path) if palette_path else None,
        "width": width,
        "height": height,
        "pitch": effective_pitch,
        "palette_mode": palette_mode,
        "raw_bytes": len(raw),
        "used_bytes": len(used),
        "raw_sha256": sha256(raw),
        "used_sha256": sha256(used),
        "png_sha256": sha256(png),
    }
    if metadata_path:
        metadata_path.parent.mkdir(parents=True, exist_ok=True)
        metadata_path.write_text(json.dumps(metadata, indent=2), encoding="ascii")
    return metadata


def run_self_test() -> int:
    root = Path(__file__).resolve().parents[1] / ".codex-loop" / "tmp-tests" / "cdb-surface-dump"
    root.mkdir(parents=True, exist_ok=True)
    raw_path = root / "selftest.raw"
    png_path = root / "selftest.png"
    metadata_path = root / "selftest.json"
    width = 16
    height = 8
    raw = bytes((x + y * width) & 0xFF for y in range(height) for x in range(width))
    raw_path.write_bytes(raw)
    metadata = convert(raw_path, png_path, width, height, None, metadata_path, None, None)
    png = png_path.read_bytes()
    if not png.startswith(PNG_SIGNATURE):
        raise AssertionError("self-test PNG signature mismatch")
    if metadata["width"] != width or metadata["height"] != height:
        raise AssertionError("self-test metadata dimensions mismatch")
    if metadata["raw_sha256"] != sha256(raw):
        raise AssertionError("self-test raw hash mismatch")
    print(f"self-test passed: {png_path}")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("raw", nargs="?", type=Path, help="raw 8-bit surface dump")
    parser.add_argument("--width", type=int)
    parser.add_argument("--height", type=int)
    parser.add_argument("--pitch", type=int, help="bytes per source row; defaults to width")
    parser.add_argument("--output", type=Path, help="PNG output path")
    parser.add_argument("--metadata", type=Path, help="metadata JSON output path")
    parser.add_argument("--log", type=Path, help="source CDB log path for metadata")
    parser.add_argument("--palette", type=Path, help="optional 256-entry DirectDraw PALETTEENTRY dump")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        return args
    missing = []
    for name in ("raw", "width", "height", "output"):
        if getattr(args, name) is None:
            missing.append(f"--{name}" if name != "raw" else "raw")
    if missing:
        parser.error("missing required arguments: " + ", ".join(missing))
    return args


def main() -> int:
    args = parse_args()
    if args.self_test:
        return run_self_test()
    metadata = convert(args.raw, args.output, args.width, args.height, args.pitch, args.metadata, args.log, args.palette)
    print(
        "wrote {png} ({width}x{height}, pitch={pitch}, raw_sha256={raw}, png_sha256={pngsha})".format(
            png=metadata["png_path"],
            width=metadata["width"],
            height=metadata["height"],
            pitch=metadata["pitch"],
            raw=metadata["raw_sha256"],
            pngsha=metadata["png_sha256"],
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
