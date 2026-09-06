#!/usr/bin/env python3
"""Read the supported user-owned LLRS assets and check native layout pixels.

No extraction files, image transforms, runtime, or input are produced. The
historical screenshot-difference diagnostic is deliberately not used here.
"""
from __future__ import annotations

import hashlib
import struct
from dataclasses import dataclass
from typing import Any


RESOURCE_SHA256 = "86b43f5e01350d9d9dfbf02a91fd3f83809050474875c2f3c4e640519f437116"
PANEL_IDS = (0, 1, 6, 7, 14)


def resource_member(data: bytes, name: str) -> bytes:
    """Follow the native LLRS directory entries, never search payload strings.

    4791A0: 16-byte header, root slots at +8, skip count at +12.
    478770/4789F0: directory count then 26-byte slots; entry name[14],
    flags, absolute offset, length. Native child slot count is (length-4)//26.
    """
    if len(data) < 20 or data[:8] != b"llrs\x01\0\0\0":
        raise ValueError("unsupported LLRS resource header")
    slots, skip = struct.unpack_from("<II", data, 8)
    offset, length = 16 + skip, 4 + slots * 26
    for component in ("GFX", name):
        if not 0 < slots <= 10000 or offset < 16 or offset + length > len(data):
            raise ValueError("LLRS directory bounds are invalid")
        count = struct.unpack_from("<I", data, offset)[0]
        found = []
        active = 0
        for index in range(slots):
            position = offset + 4 + index * 26
            flags, start, size = struct.unpack_from("<III", data, position + 14)
            if not flags:
                continue
            active += 1
            if flags not in (1, 2) or start < 16 or size <= 0 or start + size > len(data):
                raise ValueError("LLRS active entry is invalid")
            label = data[position:position + 14].split(b"\0", 1)[0].decode("ascii")
            if label == component:
                found.append((flags, start, size))
        if active != count or len(found) != 1:
            raise ValueError(f"LLRS requires exactly one valid {component} entry")
        flags, offset, length = found[0]
        if component == "GFX":
            if flags != 2:
                raise ValueError("LLRS GFX entry is not a directory")
            slots = (length - 4) // 26
        elif flags != 1:
            raise ValueError("LLRS requested asset is not a file")
    return data[offset:offset + length]


@dataclass(frozen=True)
class Sprite:
    width: int
    height: int
    pixels: tuple[int | None, ...]


def decode_sprite(data: bytes, index: int) -> Sprite:
    """Decode native indexed literals, transparent runs and shared literals.

    405BC9/406260 describe the offset table and 10-byte sprite header.
    The indexed renderer's literal/back-reference branch and 406540 confirm:
    high bit skips pixels; zero reads a backwards LE32 offset relative to
    that offset's address, referring to an earlier literal count and bytes.
    Back-references may cross sprite boundaries inside the same S32 member.
    """
    if len(data) < 4096 or type(index) is not int or not 0 <= index < 1024:
        raise ValueError("invalid S32 member or index")
    offsets = struct.unpack_from("<1024I", data)
    count = next((i for i, value in enumerate(offsets) if value == 0), 1024)
    if (index >= count or any(offsets[count:]) or offsets[0] != 4096
            or any(a >= b for a, b in zip(offsets[:count], offsets[1:count]))):
        raise ValueError("invalid S32 offset table")
    start = offsets[index]
    end = offsets[index + 1] if index + 1 < count else len(data)
    if not 4096 <= start < end <= len(data) or start + 10 > end:
        raise ValueError("S32 sprite bounds are invalid")
    width, height, encoding = struct.unpack_from("<HHH", data, start)
    if encoding != 0 or not 0 < width <= 800 or not 0 < height <= 600:
        raise ValueError("unsupported S32 sprite dimensions or encoding")
    position = start + 10
    pixels: list[int | None] = []
    for _ in range(height):
        row: list[int | None] = []
        while len(row) < width:
            if position >= end:
                raise ValueError("truncated S32 row")
            run = data[position]
            position += 1
            if run & 128:
                run &= 127
                values = [None] * run
            else:
                if run == 0:
                    if position + 4 > end:
                        raise ValueError("truncated S32 backwards reference")
                    distance = struct.unpack_from("<I", data, position)[0]
                    source = position - distance
                    if not 4096 <= source < position - 1:
                        raise ValueError("S32 backwards reference is outside earlier member data")
                    run = data[source]
                    if not 0 < run < 128 or source + 1 + run > position - 1:
                        raise ValueError("S32 backwards reference is not a complete earlier literal")
                    values = list(data[source + 1:source + 1 + run])
                    position += 4
                else:
                    if position + run > end:
                        raise ValueError("truncated S32 literal")
                    values = list(data[position:position + run])
                    position += run
            if not run or len(row) + run > width:
                raise ValueError("S32 run exceeds its row")
            row.extend(values)
        pixels.extend(row)
    if position != end:
        raise ValueError("S32 sprite has unconsumed data")
    return Sprite(width, height, tuple(pixels))


def decode_assets(data: bytes) -> dict[str, Any]:
    if hashlib.sha256(data).hexdigest() != RESOURCE_SHA256:
        raise ValueError("minimum.res is not the supported source asset identity")
    panel = resource_member(data, "MAP_BUTT.S32")
    mouse = resource_member(data, "MOUSE.S32")
    palette = resource_member(data, "MAP.PAL")
    # LoadPalCOL (401CC0) skips eight bytes; 401B20 reads 256 RGB triples.
    if len(palette) != 776 or struct.unpack_from("<I", palette)[0] != 776:
        raise ValueError("unsupported MAP.PAL header or length")
    sprites = {index: decode_sprite(panel, index) for index in PANEL_IDS}
    if any((sprite.width, sprite.height) != (64, 32) for sprite in sprites.values()):
        raise ValueError("panel sprites do not match the native descriptor dimensions")
    if any(None in sprites[index].pixels for index in (0, 1, 6, 7)):
        raise ValueError("native base panel sprites must be opaque")
    return {"panel": sprites, "mouse": {index: decode_sprite(mouse, index) for index in (2, 3)},
            "palette": tuple(tuple(palette[i:i + 3]) for i in range(8, 776, 3)),
            "members": {"MAP_BUTT.S32": hashlib.sha256(panel).hexdigest(),
                        "MOUSE.S32": hashlib.sha256(mouse).hexdigest(),
                        "MAP.PAL": hashlib.sha256(palette).hexdigest()}}


def sprite_pixels(sprite: Sprite, left: int, top: int) -> dict[tuple[int, int], int]:
    return {(left + x, top + y): value for y in range(sprite.height) for x in range(sprite.width)
            if (value := sprite.pixels[y * sprite.width + x]) is not None}


def expected_panel(assets: dict, state: dict, anchor: tuple[int, int], index: int,
                   hovered: bool = False) -> dict[tuple[int, int], int]:
    pixels = sprite_pixels(assets["panel"][index], *anchor)
    if hovered:
        pixels.update(sprite_pixels(assets["panel"][14], *anchor))
    cursor = sprite_pixels(assets["mouse"][state["cursor_sprite"]], state["cursor_x"], state["cursor_y"])
    pixels.update({point: value for point, value in cursor.items() if point in pixels})
    return pixels


def pixels_match(image: Any, pixels: dict, palette: tuple) -> bool:
    """Require every specified source pixel at the exact native anchor.

    1200x900 is accepted only for exact 3:2 nearest-neighbour replication.
    A filtered DPI capture needs its own validated sampling profile; it is
    never made passing by a colour tolerance or a changed-area threshold.
    """
    if (image.width, image.height) not in ((800, 600), (1200, 900)):
        return False
    scale = image.width // 400  # native 2/2 or exact replicated 3/2
    for (x, y), value in pixels.items():
        if not 0 <= x < 800 or not 0 <= y < 600:
            return False
        for py in range((y * scale + 1) // 2, ((y + 1) * scale + 1) // 2):
            for px in range((x * scale + 1) // 2, ((x + 1) * scale + 1) // 2):
                if image.rgb_at(px, py) != palette[value]:
                    return False
    return bool(pixels)


def check_frame(image: Any, assets: dict, state: dict, phase: str) -> list[str]:
    failures = []
    for anchor, index, hover in (((608, 528), 1, phase == "panel_hover"),
                                 ((608, 560), 6 if state["state3"] == 1 else 7, False)):
        if not pixels_match(image, expected_panel(assets, state, anchor, index, hover), assets["palette"]):
            failures.append(f"{phase} source sprite {index} or hover/cursor composition differs at {anchor}")
    cursor = sprite_pixels(assets["mouse"][state["cursor_sprite"]], state["cursor_x"], state["cursor_y"])
    if not pixels_match(image, cursor, assets["palette"]):
        failures.append(f"{phase} native cursor pixels do not match their recorded sprite and position")
    for anchor, variants in (((416, 400), (0, 1)), ((416, 432), (6, 7))):
        for index in variants:
            for hovered in (False, True):
                if pixels_match(image, expected_panel(assets, state, anchor, index, hovered), assets["palette"]):
                    failures.append(f"{phase} retains source panel sprite {index} at legacy anchor {anchor}")
    return failures
