"""Boundary and non-overlap checks for the observed native387x66 asset."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.patcher.framed_army_viewport import FramedArmyViewport


class ArmyGeometryTests(unittest.TestCase):
    def test_native_artwork_fits_all_six_profiles(self):
        for width, height in ((800,600),(1024,768),(1280,720),(1280,960),(1920,1080),(802,602)):
            with self.subTest(resolution=(width,height)):
                p = FramedArmyViewport(width,height)
                self.assertEqual((p.backing.width,p.backing.height),(387,66))
                self.assertTrue(p.framed.terrain.contains(p.backing))
                self.assertIsNone(p.backing.intersection(p.framed.action_bar))
                for edge in p.framed.frame_bands:
                    self.assertIsNone(p.backing.intersection(edge))
                for slot in range(10):
                    self.assertTrue(p.backing.contains(p.portrait(slot)))
                    self.assertEqual((p.portrait(slot).width,p.portrait(slot).height),(32,64))

    def test_every_hit_boundary_and_unoccupied_slot(self):
        p = FramedArmyViewport(1024,768)
        for slot in range(10):
            for x in (38+slot*38,75+slot*38):
                for y in (686,749):
                    self.assertEqual(p.pixel_to_slot(x,y),slot)
        for xy in ((37,686),(418,686),(38,685),(38,750),(-1,700),(0,700)):
            self.assertIsNone(p.pixel_to_slot(*xy))
        self.assertIsNone(p.pixel_to_slot(38+8*38,686,8))
        self.assertEqual(p.pixel_to_slot(38+7*38,686,8),7)

    def test_decorative_pixels_exclude_map_without_becoming_slot(self):
        p = FramedArmyViewport(802,602)
        for xy in ((32,520),(418,585),(38,585)):
            self.assertTrue(p.excludes_map_pixel(*xy))
            self.assertIsNone(p.pixel_to_slot(*xy))
        for xy in ((31,520),(419,585),(32,519),(32,586)):
            self.assertFalse(p.excludes_map_pixel(*xy))

    def test_invalid_geometry_fails(self):
        for dims in ((640,480),(800,599),(801,600),(800,True),(8194,600)):
            with self.assertRaises(ValueError):
                FramedArmyViewport(*dims)


if __name__ == '__main__':
    unittest.main()
