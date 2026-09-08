"""Independent geometry expectations; no game, patch, debugger or input."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.patcher.framed_battle_viewport import TacticalViewport


class TacticalGeometry(unittest.TestCase):
    def test_resolution_columns_and_unchanged_rows(self):
        for width, height, columns in ((640,480,7),(800,600,9),(1024,768,13),
                (1280,720,17),(1280,960,17),(1920,1080,20),(802,602,9)):
            v=TacticalViewport(width,height,20)
            self.assertEqual(v.visible_columns, columns)
            self.assertEqual(v.arena.as_tuple(),(32,16,31+64*columns,463))
            self.assertLess(v.arena.right,v.hud.left)
            self.assertEqual(v.max_scroll_x,20-columns)

    def test_every_cell_round_trip_and_boundary_rejection(self):
        for width,height in ((800,600),(802,602),(1024,768),(1280,720),(1920,1080)):
            v=TacticalViewport(width,height,20)
            for scroll in range(v.max_scroll_x+1):
                for column in range(20):
                    for row in range(7):
                        box=v.world_cell_rect(column,row,scroll_x=scroll)
                        if box is None:
                            self.assertFalse(scroll<=column<scroll+v.visible_columns)
                            continue
                        for point in ((box.left,box.top),(box.right,box.bottom)):
                            self.assertEqual(v.screen_to_cell(*point,scroll_x=scroll),(column,row))
                for point in ((-1,16),(31,16),(32,15),(32,464),(width-1,32),
                              (v.arena.right+1,16),(32,height-1),(width,height)):
                    self.assertIsNone(v.screen_to_cell(*point,scroll_x=scroll))

    def test_world_smaller_than_screen_never_negative_scroll(self):
        for world in range(1,21):
            for width in (640,800,1024,1920):
                v=TacticalViewport(width,600,world)
                self.assertGreater(v.visible_columns,0)
                self.assertLessEqual(v.visible_columns,world)
                self.assertEqual(v.clamp_scroll(-10),0)
                self.assertEqual(v.clamp_scroll(100),max(0,world-v.visible_columns))
                self.assertEqual(v.screen_to_cell(v.arena.right,463,scroll_x=v.max_scroll_x),(world-1,6))

    def test_hud_anchor_and_input_are_native_size(self):
        for width,height in ((640,480),(800,600),(1024,768),(1280,960),(1920,1080),(802,602)):
            v=TacticalViewport(width,height,20)
            self.assertEqual(v.native_hud_to_screen(508,380),(width-132,height-100))
            self.assertEqual(v.hud_to_native(width-132,height-100),(508,380))
            self.assertEqual(v.native_hud_to_screen(500,100),(width-140,100))
            self.assertIsNone(v.hud_to_native(width-161,100))
            if height>480:
                self.assertIsNone(v.hud_to_native(width-100,368))
            for part in v.hud_slices:
                self.assertEqual(part.source.area,part.destination.area)
                self.assertTrue(v.surface.contains(part.destination))

    def test_four_frame_edges_partition_outer_bands(self):
        v=TacticalViewport(1024,768,20)
        self.assertEqual([r.as_tuple() for r in v.frame_bands],
                         [(0,0,1023,15),(0,752,1023,767),(0,16,31,751),(1008,16,1023,751)])
        for i,first in enumerate(v.frame_bands):
            for second in v.frame_bands[i+1:]:
                self.assertIsNone(first.intersection(second))

    def test_invalid_geometry_and_unsafe_index_inputs_fail(self):
        for args in ((True,600,20),(800,600,False),(800,600,21),(800,600,0),
                     (639,480,7),(800,479,20),(803,602,20),(8194,600,20)):
            with self.assertRaises(ValueError):TacticalViewport(*args)
        v=TacticalViewport(1024,768,20)
        for scroll in (-1,8,True,0.5):
            with self.assertRaises(ValueError):v.screen_to_cell(32,16,scroll_x=scroll)
        for column,row in ((20,0),(0,7),(-1,0),(0,-1),(False,0)):
            with self.assertRaises(ValueError):v.world_cell_rect(column,row,scroll_x=0)


if __name__=='__main__':unittest.main()
