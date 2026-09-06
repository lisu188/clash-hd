#!/usr/bin/env python3
"""Exact source-pixel oracle for a prospective native four-sided HD frame.

Reads the user's GFX3.RES and existing surface artifacts only. No proprietary
asset extraction, image editing, candidate construction or runtime is performed.
The four-band geometry is an explicit prospective contract; it does not change
existing patch stages. Sprite5 is a separate tooltip footer, never a repeat tile.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.patcher.framed_viewport import FramedViewport
from hd_layout_asset_composition import Sprite, decode_sprite
from action_bar_surface_audit import bind_screenshot

RESOURCE_SHA256 = "31489538e8b98d180b434151db8260d00edf5ce9dd98e9f80e1d4e0607e3f525"
MEMBER_SHA256 = "8501cbae69c35aa5a804823227bbd56fb21e84b4f1e5c0f15e4419f522c4053d"
BASE_PLACEMENTS = ((0, 0, 0), (1, 314, 0), (2, 0, 237), (3, 315, 238))
BASE_SIZES = ((314, 237), (326, 238), (315, 243), (325, 242))
PROFILE = "native_four_border_tiles_v1"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@dataclass(frozen=True)
class NativeFrame:
    """Indexed640x480 base0..3; transparent terrain; footer5 kept separate."""

    base_pixels: tuple[int | None, ...]
    footer: Sprite
    resource_sha256: str
    member_sha256: str
    member_offset: int
    member_length: int

    @property
    def footer_native_origin(self) -> tuple[int, int]:
        return 155, 465


def load_native_frame(resource: bytes) -> NativeFrame:
    """Authenticate the root LLRS FRAME member and decode in memory only."""
    if digest(resource) != RESOURCE_SHA256:
        raise ValueError("unsupported GFX3.RES identity")
    if resource[:8] != b"llrs\x01\0\0\0":
        raise ValueError("unsupported LLRS header")
    slots, skip = struct.unpack_from("<II", resource, 8)
    directory = 16 + skip
    if not 0 < slots <= 10000 or directory + 4 + slots * 26 > len(resource):
        raise ValueError("invalid root directory bounds")
    count = struct.unpack_from("<I", resource, directory)[0]
    found, active = [], 0
    for i in range(slots):
        entry = directory + 4 + i * 26
        flags, start, size = struct.unpack_from("<III", resource, entry + 14)
        if not flags:
            continue
        active += 1
        if flags not in (1, 2) or start < 16 or size <= 0 or start + size > len(resource):
            raise ValueError("invalid active LLRS root entry")
        name = resource[entry:entry + 14].split(b"\0", 1)[0]
        if name == b"FRAME.S32":
            found.append((flags, start, size))
    if active != count or found != [(1, 1884879, 89593)]:
        raise ValueError("native FRAME root member is missing or ambiguous")
    _, offset, length = found[0]
    member = resource[offset:offset + length]
    if digest(member) != MEMBER_SHA256:
        raise ValueError("unsupported native FRAME identity")
    pixels = [None] * (640 * 480)
    for (index, ax, ay), size in zip(BASE_PLACEMENTS, BASE_SIZES):
        sprite = decode_sprite(member, index)
        if (sprite.width, sprite.height) != size:
            raise ValueError("unexpected native frame-piece geometry")
        for y in range(sprite.height):
            for x in range(sprite.width):
                value = sprite.pixels[y * sprite.width + x]
                if value is not None:
                    pos = (ay + y) * 640 + ax + x
                    if pixels[pos] is not None:
                        raise ValueError("base frame pieces overlap")
                    pixels[pos] = value
    for y in range(480):
        for x in range(640):
            border = x < 32 or x >= 608 or y < 16 or y >= 464
            if (pixels[y * 640 + x] is not None) != border:
                raise ValueError("native base does not exactly cover four frame bands")
    footer = decode_sprite(member, 5)
    if (footer.width, footer.height) != (324, 15) or None in footer.pixels:
        raise ValueError("unsupported opaque tooltip-footer geometry")
    return NativeFrame(tuple(pixels), footer, RESOURCE_SHA256, MEMBER_SHA256, offset, length)


def native_source_xy(x: int, y: int, layout: FramedViewport) -> tuple[int, int] | None:
    """Map a border point to base artwork; preserve corners and clip tile tails."""
    if not (0 <= x < layout.width and 0 <= y < layout.height):
        raise ValueError("point is outside the surface")
    if y < 16 or y >= layout.height - 16:
        sy = y if y < 16 else 464 + y - (layout.height - 16)
        sx = x if x < 32 else 608 + x - (layout.width - 32) if x >= layout.width - 32 else 32 + (x - 32) % 576
        return sx, sy
    if x < 32 or x >= layout.width - 32:
        sx = x if x < 32 else 608 + x - (layout.width - 32)
        return sx, 16 + (y - 16) % 448
    return None


def footer_origin(layout: FramedViewport) -> tuple[int, int]:
    # Preserve native asymmetric x=155 and the tooltip's5px/2px inset;
    # terrain-tooltip-bottom-center already uses OFFX and SHIFTY.
    return 155 + (layout.width - 640) // 2, layout.height - 15


def expected_frame_pixels(frame: NativeFrame, layout: FramedViewport, *, include_footer: bool = True) -> dict:
    """Return expected opaque border pixels, never a rendered image/file."""
    if (len(frame.base_pixels) != 640 * 480 or
            (frame.footer.width, frame.footer.height) != (324, 15) or
            len(frame.footer.pixels) != 324 * 15 or
            any(type(v) is not int or not 0 <= v <= 255 for v in frame.footer.pixels)):
        raise ValueError("invalid native frame/footer shape or pixels")
    result = {}
    for band in layout.frame_bands:
        for y in range(band.top, band.bottom + 1):
            for x in range(band.left, band.right + 1):
                sx, sy = native_source_xy(x, y, layout)
                value = frame.base_pixels[sy * 640 + sx]
                if type(value) is not int or not 0 <= value <= 255:
                    raise ValueError("missing or invalid base frame pixel")
                result[x, y] = value
    if include_footer:
        ax, ay = footer_origin(layout)
        for y in range(frame.footer.height):
            for x in range(frame.footer.width):
                result[ax + x, ay + y] = frame.footer.pixels[y * frame.footer.width + x]
    return result


def audit_surface(raw: bytes, layout: FramedViewport, frame: NativeFrame) -> dict:
    """Require every structural pixel; disclose footer/text uncertainty separately.

    An active tooltip may replace background pixels with glyphs. No arbitrary
    exclusion mask or guessed text is accepted. Footer mismatch is unverified
    tooltip composition, not sufficient evidence of defective background art.
    Whole-frame exact acceptance requires matching footer too; the distinct
    structural result excludes only that fixed, source-derived footer footprint.
    """
    if len(raw) != layout.width * layout.height:
        raise ValueError("raw surface size differs from geometry")
    expected = expected_frame_pixels(frame, layout)
    ax, ay = footer_origin(layout)
    fx1, fy1 = ax + 324, ay + 15
    bands, structural_bad = [], 0
    for name, rect in zip(("top", "bottom", "left", "right"), layout.frame_bands):
        checked, matched, bad = 0, 0, []
        for y in range(rect.top, rect.bottom + 1):
            for x in range(rect.left, rect.right + 1):
                if ax <= x < fx1 and ay <= y < fy1:
                    continue
                checked += 1
                if raw[y * layout.width + x] == expected[x, y]:
                    matched += 1
                elif len(bad) < 8:
                    bad.append([x, y])
        structural_bad += checked - matched
        bands.append(dict(name=name, rectangle_inclusive=list(rect.as_tuple()),
                          checked_pixels=checked, exact_matches=matched,
                          mismatches=checked - matched, first_mismatches=bad))
    footer_matches = sum(raw[y * layout.width + x] == expected[x, y]
                         for y in range(ay, fy1) for x in range(ax, fx1))
    footer_exact = footer_matches == 324 * 15
    structural = structural_bad == 0
    return dict(profile=PROFILE, resolution=layout.resolution,
                passed=structural and footer_exact, structural_border_exact=structural,
                checked_border_pixels=sum(b["checked_pixels"] for b in bands), bands=bands,
                footer=dict(sprite=5, origin=[ax, ay], size=[324, 15], checked_pixels=4860,
                            exact_matches=footer_matches, exact=footer_exact,
                            status="exact_background" if footer_exact else "unverified_background_or_active_tooltip_text"),
                opaque_frame_pixels=len(expected),
                limits="Prospective exact frame profile only. Active tooltip glyphs need separate source-bound evidence; no ignored footer mismatch produces a full pass. Not runtime/input/promotion acceptance.")


def audit_summary(path: Path, frame: NativeFrame) -> dict:
    summary_bytes = path.read_bytes()
    summary = json.loads(summary_bytes.decode("utf-8-sig"))
    width, height = summary["Surface"]["Width"], summary["Surface"]["Height"]
    layout = FramedViewport(width, height)
    if summary["Resolution"] != layout.resolution:
        raise ValueError("summary resolution disagrees with observed surface")
    raw_path, png_path = Path(summary["RawPath"]), Path(summary["PngPath"])
    if raw_path.parent.resolve() != path.parent.resolve() or png_path.parent.resolve() != path.parent.resolve():
        raise ValueError("surface artifacts do not belong to the supplied run")
    raw = raw_path.read_bytes()
    if any(type(n) is not int or n != len(raw)
           for n in (summary["RawBytes"], summary["Surface"]["Bytes"])):
        raise ValueError("raw size differs from summary")
    binding = bind_screenshot(summary, raw, raw_path, png_path, width, height)
    result = audit_surface(raw, layout, frame)
    result.update(stage=summary["Stage"], candidate_sha256=summary["CandidateSha256"],
                  existing_surface_gate_passed=summary["Passed"],
                  summary=dict(path=str(path), sha256=digest(summary_bytes)),
                  raw_surface=dict(path=str(raw_path), sha256=digest(raw)),
                  screenshot=dict(path=str(png_path), sha256=digest(png_path.read_bytes())), binding=binding)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--resource", type=Path, required=True)
    parser.add_argument("--summary", type=Path, action="append", required=True)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()
    frame = load_native_frame(args.resource.read_bytes())
    rows = [audit_summary(p, frame) for p in dict.fromkeys(args.summary)]
    result = dict(schema="clash95_four_border_asset_audit_v1", generated_at=datetime.now(timezone.utc).isoformat(),
                  resource_sha256=frame.resource_sha256, member_sha256=frame.member_sha256,
                  passed=all(row["passed"] for row in rows), screenshots=rows,
                  scope="Existing surfaces and native assets only; no runtime or image modification")
    encoded = json.dumps(result, indent=2) + "\n"
    if args.json_out:
        with args.json_out.open("x", encoding="utf-8") as stream:
            stream.write(encoded)
    print(encoded, end="")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
