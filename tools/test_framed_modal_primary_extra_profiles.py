#!/usr/bin/env python3
"""Execute the actual inherited HD blitter at the three remaining profiles.

The main primary suite covers 1024x768, 1920x1080 and 802x602. Keeping these
other exact reconstructions separate preserves the aggregate's existing
per-suite deadline. All native inputs are synthetic; no game or debugger runs.
"""
import unittest

import test_framed_modal_primary as primary_fixture


@unittest.skipUnless(primary_fixture.NATIVE_FIXTURE_AVAILABLE,primary_fixture.NATIVE_FIXTURE_REASON)
class PrimaryExtraProfileTests(primary_fixture.PrimaryFixture,unittest.TestCase):
    def test_actual_inherited_hd_blitter_copies_every_pixel_at_remaining_presets(self):
        for width,height in ((800,600),(1280,720),(1280,960)):
            with self.subTest(resolution=f'{width}x{height}'):
                self.check_inherited_hd_profile(width,height)


if __name__=='__main__':unittest.main(verbosity=2)
