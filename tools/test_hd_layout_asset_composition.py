#!/usr/bin/env python3
"""Synthetic LLRS/S32 fixtures. No proprietary pixels or runtime are included."""
from __future__ import annotations

import hashlib
import struct
from unittest import mock

import hd_layout_asset_composition as assets


def fixture_s32(sprites: list[assets.Sprite]) -> bytes:
    data = bytearray(4096)
    literals: dict[bytes, int] = {}
    for index, sprite in enumerate(sprites):
        struct.pack_into("<I", data, index * 4, len(data))
        data.extend(struct.pack("<5H", sprite.width, sprite.height, 0, 1, 0))
        for y in range(sprite.height):
            row = sprite.pixels[y * sprite.width:(y + 1) * sprite.width]
            x = 0
            while x < len(row):
                transparent = row[x] is None
                end = x + 1
                while end < len(row) and (row[end] is None) == transparent and end - x < 127:
                    end += 1
                if transparent:
                    data.append(128 + end - x)
                else:
                    values = bytes(row[x:end])
                    if values in literals and len(values) > 5:
                        data.append(0)
                        data.extend(struct.pack("<I", len(data) - literals[values]))
                    else:
                        literals[values] = len(data)
                        data.append(len(values))
                        data.extend(values)
                x = end
    return bytes(data)


def fixture_resource() -> bytes:
    panels = [assets.Sprite(64, 32, tuple(
        (180 + x % 3 if x in (0, 63) or y in (0, 31) else None) if index == 14
        else 20 + (index * 13 + x // 4 + y // 3) % 80
        for y in range(32) for x in range(64))) for index in range(15)]
    mice = [assets.Sprite(9 + index, 11 + index, tuple(
        120 + index + y % 4 if x <= y // 2 else None
        for y in range(11 + index) for x in range(9 + index))) for index in range(4)]
    palette = struct.pack("<II", 776, 0) + bytes(
        component for index in range(256) for component in (index, (index * 3) % 150, (index * 7) % 140))
    members = {"MAP_BUTT.S32": fixture_s32(panels), "MOUSE.S32": fixture_s32(mice), "MAP.PAL": palette}
    root, child = 16, 16 + 4 + 2 * 26
    data = bytearray(child + 4 + 4 * 26)
    struct.pack_into("<4sIII", data, 0, b"llrs", 1, 2, 0)
    struct.pack_into("<I", data, root, 1)
    struct.pack_into("<14sIII", data, root + 4, b"GFX", 2, child, 4 + 4 * 26)
    struct.pack_into("<I", data, child, len(members))
    for index, (name, payload) in enumerate(members.items()):
        struct.pack_into("<14sIII", data, child + 4 + index * 26, name.encode(), 1, len(data), len(payload))
        data.extend(payload)
    return bytes(data)


def fixture_assets() -> dict:
    data = fixture_resource()
    with mock.patch.object(assets, "RESOURCE_SHA256", hashlib.sha256(data).hexdigest()):
        return assets.decode_assets(data)


def rejects(action, fragment: str) -> None:
    try:
        action()
    except ValueError as exc:
        assert fragment in str(exc), exc
    else:
        raise AssertionError(f"invalid fixture accepted: {fragment}")


def run_tests() -> None:
    resource = fixture_resource()
    decoded = fixture_assets()
    assert decoded["panel"][14].pixels[65] is None
    assert decoded["panel"][1].pixels[0] == 33
    assert decoded["mouse"][3].pixels[1] is None
    # Actual native backwards references include references into prior sprites.
    first = assets.Sprite(12, 2, (20,) * 24)
    shared = fixture_s32([first, first])
    assert assets.decode_sprite(shared, 1) == first
    start = struct.unpack_from("<I", shared, 4)[0]
    assert shared[start + 10] == 0
    bad = bytearray(shared)
    struct.pack_into("<I", bad, start + 11, 0)
    rejects(lambda: assets.decode_sprite(bytes(bad), 1), "outside earlier")
    bad = bytearray(shared)
    bad[4096 + 10] = 127
    rejects(lambda: assets.decode_sprite(bytes(bad), 0), "truncated")
    bad = bytearray(shared)
    struct.pack_into("<H", bad, 4096 + 4, 1)
    rejects(lambda: assets.decode_sprite(bytes(bad), 0), "encoding")
    bad = bytearray(resource)
    bad[:4] = b"fake"
    rejects(lambda: assets.resource_member(bytes(bad), "MAP.PAL"), "header")
    child = 16 + 4 + 2 * 26
    bad = bytearray(resource)
    # Duplicate active directory entries cannot select a convenient payload.
    bad[child + 4 + 3 * 26:child + 4 + 4 * 26] = bad[child + 4:child + 4 + 26]
    struct.pack_into("<I", bad, child, 4)
    rejects(lambda: assets.resource_member(bytes(bad), "MAP_BUTT.S32"), "exactly one")
    bad = bytearray(resource)
    struct.pack_into("<I", bad, child + 4 + 18, len(bad) + 10)
    rejects(lambda: assets.resource_member(bytes(bad), "MAP_BUTT.S32"), "entry is invalid")
    rejects(lambda: assets.decode_assets(resource), "source asset identity")
    with mock.patch.object(assets, "RESOURCE_SHA256", hashlib.sha256(resource).hexdigest()):
        assert assets.decode_assets(resource)["members"] == decoded["members"]
        rejects(lambda: assets.decode_assets(resource[:-1]), "source asset identity")


if __name__ == "__main__":
    run_tests()
    print("HD layout native asset composition tests passed")
