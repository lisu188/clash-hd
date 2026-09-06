#!/usr/bin/env python3
"""Independent pixel/bounds oracles for pure framed geometry; no game/runtime."""
from __future__ import annotations

from dataclasses import FrozenInstanceError
from itertools import combinations
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "patcher"))
from framed_viewport import FramedViewport, Rect, WorldView


# Literal expectations derived from reserved 32/16 native artwork bands,
# independent of implementation properties. Entries: full, ceil, remainder,
# partial count, first descriptor anchor.
CASES = {
    (640, 480): ((9, 7), (9, 7), (0, 0), 0, (416, 400)),
    (800, 600): ((11, 8), (12, 9), (32, 56), 20, (576, 520)),
    (1024, 768): ((15, 11), (15, 12), (0, 32), 15, (800, 688)),
    (1280, 720): ((19, 10), (19, 11), (0, 48), 19, (1056, 640)),
    (1280, 960): ((19, 14), (19, 15), (0, 32), 19, (1056, 880)),
    (1920, 1080): ((29, 16), (29, 17), (0, 24), 29, (1696, 1000)),
    (802, 602): ((11, 8), (12, 9), (34, 58), 20, (578, 522)),
}


class FramedViewportTests(unittest.TestCase):
    def test_native_geometry_is_exact(self):
        view = FramedViewport(640, 480)
        self.assertEqual(view.surface.as_tuple(), (0, 0, 639, 479))
        self.assertEqual(view.terrain.as_tuple(), (32, 16, 607, 463))
        self.assertEqual([cell.as_tuple() for cell in view.action_cells], [
            (416, 400, 479, 431), (480, 400, 543, 431), (544, 400, 607, 431),
            (416, 432, 479, 463), (480, 432, 543, 463), (544, 432, 607, 463)])
        self.assertEqual(view.minimap_right_anchor, 608)
        self.assertEqual(view.minimap_box(214, 214).as_tuple(), (394, 16, 607, 229))
        self.assertIsNone(view.minimap_box(214, 214).intersection(view.action_bar))

    def test_presets_and_nondivisible_custom(self):
        for size, (full, ceil, remainder, count, action) in CASES.items():
            with self.subTest(size=size):
                view = FramedViewport(*size)
                self.assertEqual(view.full_tiles, full)
                self.assertEqual(view.ceil_tiles, ceil)
                self.assertEqual(view.partial_pixels, remainder)
                self.assertEqual(len(view.world_view(100, 100).cells(partial_only=True)), count)
                self.assertEqual((view.action_bar.left, view.action_bar.top), action)
                self.assertEqual(view.resolution, f"{size[0]}x{size[1]}")

    def test_disjoint_frame_and_terrain_exactly_partition_surface(self):
        for size in CASES:
            view = FramedViewport(*size)
            regions = (*view.frame_bands, view.terrain)
            self.assertTrue(all(view.surface.contains(rect) for rect in regions))
            self.assertEqual(sum(rect.area for rect in regions), view.surface.area)
            for first, second in combinations(regions, 2):
                self.assertIsNone(first.intersection(second))
            # Independently walk representative full rows, including all
            # corners and border/interior transitions; each pixel has one owner.
            for y in (0, 15, 16, size[1] // 2, size[1] - 17, size[1] - 16, size[1] - 1):
                owners = [0] * size[0]
                for rect in regions:
                    if rect.top <= y <= rect.bottom:
                        for x in range(rect.left, rect.right + 1):
                            owners[x] += 1
                self.assertEqual(set(owners), {1})

    def test_controls_overlay_terrain_without_touching_frame(self):
        for size in CASES:
            view = FramedViewport(*size)
            self.assertEqual(len(view.action_cells), 6)
            self.assertEqual(sum(rect.area for rect in view.action_cells), view.action_bar.area)
            self.assertTrue(all(view.action_bar.contains(rect) for rect in view.action_cells))
            for a, b in combinations(view.action_cells, 2):
                self.assertIsNone(a.intersection(b))
            for rect in (*view.action_cells, view.minimap_box(214, 214)):
                self.assertTrue(view.terrain.contains(rect))
                self.assertTrue(all(band.intersection(rect) is None for band in view.frame_bands))
            self.assertEqual(view.action_cells[-1].right, size[0] - 33)
            self.assertEqual(view.action_cells[-1].bottom, size[1] - 17)
            self.assertEqual({(rect.width, rect.height) for rect in view.action_cells}, {(64, 32)})

    def test_tiles_partition_terrain_with_exact_partial_corner(self):
        for size in CASES:
            view = FramedViewport(*size)
            cells = view.world_view(100, 100).cells()
            self.assertEqual(sum(cell.rect.area for cell in cells), view.terrain.area)
            self.assertEqual(len({(cell.column, cell.row) for cell in cells}), len(cells))
            self.assertTrue(all(view.terrain.contains(cell.rect) for cell in cells))
            for a, b in combinations(cells, 2):
                self.assertIsNone(a.rect.intersection(b.rect))
            # Independent tile starts counted via range, not floor/ceil fields.
            expected = {(x, y) for y in range(16, size[1] - 16, 64)
                        for x in range(32, size[0] - 32, 64)}
            self.assertEqual({(cell.rect.left, cell.rect.top) for cell in cells}, expected)
            partials = view.world_view(100, 100).cells(partial_only=True)
            self.assertEqual(partials, tuple(cell for cell in cells if cell.partial))
            if all(view.partial_pixels):
                corner = cells[-1]
                self.assertEqual((corner.rect.width, corner.rect.height), view.partial_pixels)
                self.assertEqual(partials.count(corner), 1)

    def test_far_scroll_preserves_full_final_world_tile_and_clears_partial_tails(self):
        for size in CASES:
            view = FramedViewport(*size)
            start = view.world_view(100, 100)
            self.assertTrue(all(cell.in_world for cell in start.cells()))
            scroll = start.max_scroll
            far = view.world_view(100, 100, *scroll)
            self.assertTrue(far.native_full_loop_safe)
            far.require_native_full_loop()
            self.assertEqual([(cell.world_x, cell.world_y) for cell in far.cells()
                              if cell.in_world and cell.world_x == 99 and cell.world_y == 99], [(99, 99)])
            last = next(cell for cell in far.cells() if (cell.world_x, cell.world_y) == (99, 99))
            self.assertEqual((last.rect.width, last.rect.height), (64, 64))
            self.assertTrue(all(not cell.in_world for cell in far.cells(partial_only=True)))
            for bad in ((scroll[0] + 1, scroll[1]), (scroll[0], scroll[1] + 1), (-1, 0), (0, -1)):
                with self.assertRaises(ValueError):
                    view.world_view(100, 100, *bad)

    def test_smaller_world_plan_does_not_approve_unsafe_native_full_loop(self):
        for size in CASES:
            view = FramedViewport(*size)
            tiny = view.world_view(3, 2)
            self.assertEqual(tiny.max_scroll, (0, 0))
            self.assertFalse(tiny.native_full_loop_safe)
            with self.assertRaises(ValueError):
                tiny.require_native_full_loop()
            self.assertEqual({(cell.world_x, cell.world_y) for cell in tiny.cells() if cell.in_world},
                             {(x, y) for x in range(3) for y in range(2)})
            # Small-world clearing includes full cells, not just partial strips.
            self.assertTrue(any(not cell.in_world and not cell.partial for cell in tiny.cells()))
            for dims in ((100, 1), (1, 100)):
                narrow = view.world_view(*dims)
                self.assertFalse(narrow.native_full_loop_safe)
            equal = view.world_view(*view.full_tiles)
            self.assertTrue(equal.native_full_loop_safe)
            self.assertEqual(equal.max_scroll, (0, 0))
            self.assertTrue(all(not cell.in_world for cell in equal.cells(partial_only=True)))

    def test_minimap_uses_actual_dimensions_and_exclusive_anchor(self):
        view = FramedViewport(802, 602)
        for width, height in ((1, 1), (214, 214), (113, 79), (738, 570)):
            box = view.minimap_box(width, height)
            self.assertEqual((box.width, box.height), (width, height))
            self.assertEqual((box.right + 1, box.top), (770, 16))
            self.assertTrue(view.terrain.contains(box))
        for dims in ((0, 214), (214, 0), (739, 100), (100, 571), (-1, 100), (True, 10), (1.0, 2)):
            with self.assertRaises(ValueError):
                view.minimap_box(*dims)

    def test_invalid_bounds_types_and_mutation_rejected(self):
        for size in ((638, 480), (640, 478), (641, 480), (640, 481), (8194, 600),
                     (800, 8194), (0, 0), (True, 600), (800.0, 600), ("800", 600)):
            with self.assertRaises(ValueError):
                FramedViewport(*size)
        largest = FramedViewport(8192, 8192).world_view(100, 100)
        self.assertFalse(largest.native_full_loop_safe)
        view = FramedViewport(800, 600)
        for dims in ((0, 100), (100, 0), (101, 100), (100, 101), (-1, 1), (True, 10), (1.0, 2)):
            with self.assertRaises(ValueError):
                view.world_view(*dims)
        for cell in ((-1, 0), (0, -1), (12, 0), (0, 9), (True, 1), (0.0, 0)):
            with self.assertRaises(ValueError):
                view.cell_rect(*cell)
        with self.assertRaises(ValueError):
            WorldView(None, 100, 100)
        with self.assertRaises(ValueError):
            view.world_view(100, 100, scroll_x=True)
        with self.assertRaises(ValueError):
            view.world_view(100, 100).cells(partial_only=1)
        with self.assertRaises(FrozenInstanceError):
            view.width = 1024
        with self.assertRaises(FrozenInstanceError):
            view.terrain.right = 799

    def test_rectangle_inclusive_semantics_and_invalid_shapes(self):
        pixel = Rect(3, 4, 3, 4)
        self.assertEqual((pixel.width, pixel.height, pixel.area), (1, 1, 1))
        self.assertEqual(Rect(0, 0, 3, 4).intersection(pixel), pixel)
        self.assertIsNone(Rect(0, 0, 2, 4).intersection(pixel))
        self.assertFalse(pixel.contains(Rect(3, 4, 4, 4)))
        for coords in ((-1, 0, 1, 1), (0, -1, 1, 1), (1, 0, 0, 1), (0, 1, 1, 0), (True, 0, 1, 1)):
            with self.assertRaises(ValueError):
                Rect(*coords)


if __name__ == "__main__":
    unittest.main()
