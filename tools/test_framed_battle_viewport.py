"""Independent geometry expectations; no game, patch, debugger or input."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.patcher.framed_battle_viewport import TacticalViewport

# Audited preset expectations, independent of the production capacity formula.
PRESET_CASES = ((800,600,9),(1024,768,13),(1280,720,17),(1280,960,17),
                (1366,768,18),(1920,1080,20),(2560,1440,20),
                (3440,1440,20),(3840,2160,20))
GEOMETRY_CASES = ((640,480,7), *PRESET_CASES, (802,602,9))


class TacticalGeometry(unittest.TestCase):
    def test_resolution_columns_and_unchanged_rows(self):
        for width,height,columns in GEOMETRY_CASES:
            v=TacticalViewport(width,height,20)
            self.assertEqual(v.visible_columns,columns)
            self.assertEqual(v.arena.as_tuple(),(32,16,31+64*columns,463))
            self.assertLess(v.arena.right,v.hud.left)
            self.assertEqual(v.max_scroll_x,20-columns)

    def test_every_cell_round_trip_and_boundary_rejection(self):
        for width,height,capacity in GEOMETRY_CASES:
            for world in (1,16,20):
                v=TacticalViewport(width,height,world)
                visible=min(world,capacity)
                for scroll in range(world-visible+1):
                    for column in range(world):
                        for row in range(7):
                            box=v.world_cell_rect(column,row,scroll_x=scroll)
                            if not scroll<=column<scroll+visible:
                                self.assertIsNone(box)
                                continue
                            x,y=32+64*(column-scroll),16+64*row
                            self.assertEqual(box.as_tuple(),(x,y,x+63,y+63))
                            for point in ((x,y),(x+63,y+63)):
                                self.assertEqual(v.screen_to_cell(*point,scroll_x=scroll),(column,row))
                    for point in ((-1,16),(31,16),(32,15),(32,464),(width-1,32),
                                  (32+visible*64,16),(32,height-1),(width,height)):
                        self.assertIsNone(v.screen_to_cell(*point,scroll_x=scroll))

    def test_world_smaller_than_screen_never_negative_scroll(self):
        for width,height,capacity in GEOMETRY_CASES:
            for world in range(1,21):
                v=TacticalViewport(width,height,world)
                end=max(0,world-capacity)
                self.assertEqual(v.visible_columns,min(world,capacity))
                for requested,expected in ((-0x80000000,0),(-10,0),(0,0),(100,end),(0x7fffffff,end)):
                    self.assertEqual(v.clamp_scroll(requested),expected)
                self.assertEqual(v.screen_to_cell(v.arena.right,463,scroll_x=end),(world-1,6))

    def test_hud_anchor_and_input_are_native_size(self):
        native=((498,370),(561,370),(498,401),(498,432),(561,401),(505,0))
        for width,height,_ in GEOMETRY_CASES:
            v=TacticalViewport(width,height,20)
            displayed=((width-142,height-110),(width-79,height-110),
                       (width-142,height-79),(width-142,height-48),
                       (width-79,height-79),(width-135,0))
            for source,destination in zip(native,displayed):
                self.assertEqual(v.native_hud_to_screen(*source),destination)
                self.assertEqual(v.hud_to_native(*destination),source)
            self.assertEqual([p.source.as_tuple() for p in v.hud_slices],
                             [(480,0,639,367),(480,368,639,479)])
            for part,size in zip(v.hud_slices,((160,368),(160,112))):
                self.assertEqual((part.source.width,part.source.height),size)
                self.assertEqual((part.destination.width,part.destination.height),size)
                self.assertTrue(v.surface.contains(part.destination))
            self.assertIsNone(v.hud_to_native(width-161,100))

    def test_unused_field_and_hud_pixels_remain_noninteractive(self):
        for width,height,capacity in GEOMETRY_CASES:
            for world in (1,16,20):
                v=TacticalViewport(width,height,world)
                gap=32+64*min(world,capacity)
                if gap<v.hud.left:
                    for x in (gap,v.hud.left-1):
                        for y in (16,463):
                            self.assertIsNone(v.screen_to_cell(x,y,scroll_x=0))
                            self.assertIsNone(v.hud_to_native(x,y))
                if height>480:
                    for y in (368,height-113):
                        self.assertIsNone(v.hud_to_native(width-80,y))
                        self.assertIsNone(v.screen_to_cell(width-80,y,scroll_x=0))

    def test_four_frame_edges_partition_outer_bands(self):
        for width,height,_ in GEOMETRY_CASES:
            v=TacticalViewport(width,height,20)
            self.assertEqual([r.as_tuple() for r in v.frame_bands],
                             [(0,0,width-1,15),(0,height-16,width-1,height-1),
                              (0,16,31,height-17),(width-16,16,width-1,height-17)])
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
