#!/usr/bin/env python3
"""Frame plan geometry and independent source-pixel checks; no game execution.

The optional asset tests read the user's FRAME member in memory only. They do
not create images, extract resources, install a hook or alter a game binary.
Actual synthetic x86 ABI checks live in test_four_sided_frame_x86.py.
"""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import struct
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.patcher import four_sided_frame as frame
from src.patcher import partial_tile_clip as clip
from src.patcher.framed_viewport import FramedViewport
import frame_surface_audit as oracle
from hd_layout_asset_composition import decode_sprite

SIZES = ((640, 480), (800, 600), (1024, 768), (1280, 720), (1280, 960), (1920, 1080), (802, 602))
RESOURCE = Path("C:/Clash/DATA/GFX3.RES")
ORIGINAL = Path("C:/Clash/clash95.exe")


class PlanTests(unittest.TestCase):
    def test_base_clips_partition_borders_and_footer_overlays_once(self):
        for width, height in SIZES:
            with self.subTest(size=(width, height)):
                layout = FramedViewport(width, height)
                plan = frame.frame_draw_plan(layout)
                self.assertEqual([d.sprite for d in plan if d.band == "footer"], [5])
                self.assertEqual(plan[-1].band, "footer")
                self.assertEqual((plan[-1].x, plan[-1].y), (155 + (width - 640) // 2, height - 15))
                observed = set()
                for draw in plan[:-1]:
                    self.assertIn(draw.sprite, range(4))
                    self.assertTrue(layout.surface.contains(draw.clip))
                    self.assertIsNone(layout.terrain.intersection(draw.clip))
                    pixels = {(x, y) for y in range(draw.clip.top, draw.clip.bottom + 1)
                              for x in range(draw.clip.left, draw.clip.right + 1)}
                    self.assertFalse(observed & pixels, "base clips must not overlap")
                    observed |= pixels
                    sprite_width, sprite_height = frame.SPRITE_SIZES[draw.sprite]
                    self.assertTrue(0 <= draw.clip.left - draw.x <= draw.clip.right - draw.x < sprite_width)
                    self.assertTrue(0 <= draw.clip.top - draw.y <= draw.clip.bottom - draw.y < sprite_height)
                expected = {(x, y) for band in layout.frame_bands for y in range(band.top, band.bottom + 1)
                            for x in range(band.left, band.right + 1)}
                self.assertEqual(observed, expected)
                self.assertEqual(len(observed), width * height - (width - 64) * (height - 32))
                self.assertIsNone(layout.action_bar.intersection(plan[-1].clip))

    def test_maximum_dimensions_have_bounded_calls_and_clipped_tails(self):
        layout = FramedViewport(8192, 8192)
        plan = frame.frame_draw_plan(layout)
        self.assertLess(len(plan), 160)
        self.assertEqual(sum(d.clip.area for d in plan[:-1]),
                         layout.surface.area - layout.terrain.area)
        self.assertTrue(all(layout.surface.contains(d.clip) for d in plan))
        self.assertTrue(all(layout.terrain.intersection(d.clip) is None for d in plan))
        with self.assertRaises(ValueError):
            frame.frame_draw_plan((800, 600))


@unittest.skipUnless(RESOURCE.is_file(), "requires the user's FRAME resource for exact source pixels")
class SourcePixelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        resource = RESOURCE.read_bytes()
        cls.native = oracle.load_native_frame(resource)
        member = resource[cls.native.member_offset:cls.native.member_offset + cls.native.member_length]
        cls.sprites = {index: decode_sprite(member, index) for index in (0, 1, 2, 3, 5)}

    def paint(self, layout, plan):
        # An in-memory reference canvas, not an edited or generated screenshot.
        # Independent Sprite decoding applies each native draw's destination
        # origin and inclusive clip, including transparent pixels.
        canvas = bytearray([0xA5]) * layout.surface.area
        for draw in plan:
            sprite = self.sprites[draw.sprite]
            for y in range(draw.clip.top, draw.clip.bottom + 1):
                for x in range(draw.clip.left, draw.clip.right + 1):
                    sx, sy = x - draw.x, y - draw.y
                    if not (0 <= sx < sprite.width and 0 <= sy < sprite.height):
                        continue
                    value = sprite.pixels[sy * sprite.width + sx]
                    if value is not None:
                        canvas[y * layout.width + x] = value
        return canvas

    def test_seven_layouts_match_independent_exact_artwork_oracle(self):
        for size in SIZES:
            with self.subTest(size=size):
                layout = FramedViewport(*size)
                canvas = self.paint(layout, frame.frame_draw_plan(layout))
                expected = oracle.expected_frame_pixels(self.native, layout)
                self.assertTrue(all(canvas[y * layout.width + x] == value for (x, y), value in expected.items()))
                self.assertTrue(oracle.audit_surface(bytes(canvas), layout, self.native)["passed"])
                terrain = layout.terrain
                for y in range(terrain.top, terrain.bottom + 1):
                    start = y * layout.width + terrain.left
                    self.assertEqual(canvas[start:start + terrain.width], b"\xA5" * terrain.width,
                                     "frame draws must preserve every terrain/control pixel")

    def test_native_layout_preserves_original_composite_and_four_corners(self):
        layout = FramedViewport(640, 480)
        canvas = self.paint(layout, frame.frame_draw_plan(layout))
        native = list(self.native.base_pixels)
        sprite = self.native.footer
        for y in range(15):
            native[(465 + y) * 640 + 155:(465 + y) * 640 + 479] = sprite.pixels[y * 324:(y + 1) * 324]
        self.assertEqual(canvas, bytes(0xA5 if value is None else value for value in native))
        for width, height in SIZES[1:]:
            layout = FramedViewport(width, height)
            hd = self.paint(layout, frame.frame_draw_plan(layout))
            for x0, y0, sx, sy in ((0, 0, 0, 0), (width - 32, 0, 608, 0),
                                   (0, height - 16, 0, 464), (width - 32, height - 16, 608, 464)):
                for y in range(16):
                    self.assertEqual(hd[(y0 + y) * width + x0:(y0 + y) * width + x0 + 32],
                                     canvas[(sy + y) * 640 + sx:(sy + y) * 640 + sx + 32])

    def test_missing_bands_shifted_artwork_and_omitted_footer_fail(self):
        layout = FramedViewport(1024, 768)
        plan = frame.frame_draw_plan(layout)
        mutations = [tuple(d for d in plan if d.band != band) for band in ("right", "bottom", "footer")]
        mutations.append(tuple(replace(d, x=d.x + 1) if d.band == "right" else d for d in plan))
        for bad in mutations:
            self.assertFalse(oracle.audit_surface(bytes(self.paint(layout, bad)), layout, self.native)["passed"])


@unittest.skipUnless(ORIGINAL.is_file(), "requires the user's original for authenticated native ABI")
class EmitterContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = ORIGINAL.read_bytes()

    def test_emission_is_uninstalled_and_relocation_inventory_is_exact(self):
        for size in SIZES:
            with self.subTest(size=size):
                bundle = frame.emit_frame_helper(self.original, base_va=0x562000, width=size[0], height=size[1])
                self.assertFalse(bundle.installation_ready)
                self.assertEqual(bundle.entries["draw_frame"], bundle.base_va)
                self.assertEqual(bundle.code[:7].hex(), "9c6089e583ec1c")
                self.assertEqual(bundle.code[-5:].hex(), "89ec619dc3")
                plan = frame.frame_draw_plan(FramedViewport(*size))
                transfers = [r for r in bundle.relocations if r.kind == "rel32"]
                self.assertEqual(len(transfers), len(plan))
                self.assertEqual({(r.purpose, r.target) for r in transfers}, {("sprite", 0x402E80)})
                purposes = {r.purpose for r in bundle.relocations if r.kind == "abs32"}
                self.assertEqual(purposes, {"map_surface_global", "memory_vtable", "render_device_global",
                                           "frame_sprites_global", "primary_surface"})
                absolute = clip.absolute_relocation_offsets(bundle)
                self.assertEqual(len(absolute), len(plan) + 6)
                rebased = bytearray(bundle.code)
                for offset in absolute:
                    struct.pack_into("<I", rebased, offset, struct.unpack_from("<I", rebased, offset)[0] + 0x100000)
                for item in bundle.relocations:
                    actual = struct.unpack_from("<I", rebased, item.offset)[0]
                    expected = (item.target + 0x100000 if item.kind == "abs32"
                                else item.target - (bundle.base_va + item.offset + 4))
                    self.assertEqual(actual, expected & 0xFFFFFFFF)

    def test_changed_original_or_invalid_allocation_fails_closed(self):
        corrupted = bytearray(self.original)
        corrupted[0x100] ^= 1
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            frame.emit_frame_helper(bytes(corrupted), base_va=0x562000, width=800, height=600)
        for base in (True, -1, 0x80000000):
            with self.assertRaises(ValueError):
                frame.emit_frame_helper(self.original, base_va=base, width=800, height=600)
        for width, height in ((639, 480), (800, 601), (8194, 600), (True, 600)):
            with self.assertRaises(ValueError):
                frame.emit_frame_helper(self.original, base_va=0x562000, width=width, height=height)


if __name__ == "__main__":
    unittest.main()
