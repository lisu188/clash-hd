#!/usr/bin/env python3
"""Synthetic image fixtures for resolution-aware minimap coverage masks."""

import json
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib
from pathlib import Path

import map_tile_coverage as coverage
from capture_geometry import Image


def write_fixture_png(path: Path, width: int = 160, height: int = 120) -> None:
    # Small patterned image: pure fixture data, not a capture or game asset.
    raw = b"".join(b"\0" + bytes((40 + (x*y) % 200 for x in range(width*3))) for y in range(height))
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind+data))
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


class CoverageTests(unittest.TestCase):
    def test_800_mask_preserved(self):
        self.assertEqual(coverage.default_masks(800), coverage.DEFAULT_MASKS)

    def test_shifted_mask_does_not_hide_old_minimap_region(self):
        image = Image(1280, 720, [(0, 0, 0)] * (1280*720))
        masks = list(coverage.default_masks(1280).items())
        def stats(rect):
            return coverage.cell_stats(image, rect, masks, 1280, 720, 12, 5.0, 0, 20.0)
        old = stats((672, 16, 735, 79))
        new = stats((1184, 16, 1247, 79))
        self.assertEqual(old["masked_pixels"], 0)
        self.assertIn("blank", old["flags"])
        self.assertEqual(new["masked_percent"], 100)
        self.assertIn("insufficient_unmasked", new["flags"])
        self.assertNotIn("blank", new["flags"])

    def test_cli_uses_requested_grid_and_right_anchor_and_preserves_overrides(self):
        with tempfile.TemporaryDirectory(prefix="clash-coverage-fixture-") as folder:
            png, out = Path(folder)/"fixture.png", Path(folder)/"coverage.json"
            write_fixture_png(png)
            for width, height in ((800, 600), (802, 602), (1024, 768), (1280, 720), (1280, 960), (1920, 1080)):
                cols, rows = (width-32)//64, (height-16)//64
                command = [sys.executable, "-B", str(Path(coverage.__file__)), str(png), "--logical-width", str(width), "--logical-height", str(height), "--columns", str(cols), "--rows", str(rows), "--bottom-row-active-cols", str(cols), "--write-json", str(out)]
                result = subprocess.run(command, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                report = json.loads(out.read_text())
                self.assertEqual(report["masks"], [{"name": "hd_minimap", "logical_rect": [width-214, 16, width-1, 229]}])
                self.assertEqual(report["images"][0]["summary"]["active_cells"], cols*rows)
                last = report["images"][0]["cells"][-1]
                self.assertEqual(last["logical_rect"], [32+(cols-1)*64, 16+(rows-1)*64, 31+cols*64, 15+rows*64])
            result = subprocess.run(command + ["--no-default-masks", "--mask", "custom:1,2,3,4"], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(out.read_text())["masks"], [{"name": "custom", "logical_rect": [1, 2, 3, 4]}])

    def test_framed_stage_uses_all_clipped_ceiling_cells_and_actual_minimap(self):
        # Independent dimensions/counts; no use of the producer's geometry for
        # expected values. Cell areas must partition only the terrain rectangle.
        profiles=((800,600,12,9),(802,602,12,9),(1024,768,15,12),(1280,720,19,11),
                  (1280,960,19,15),(1920,1080,29,17))
        for w,h,cols,rows in profiles:
            g=coverage.framed_coverage_geometry(coverage.FRAMED_STAGE,w,h,
                      minimap_enabled=True,minimap_width=134,minimap_height=94)
            self.assertEqual((g['columns'],g['rows']),(cols,rows))
            self.assertEqual(g['terrain'],[32,16,w-33,h-17])
            self.assertEqual(g['masks'],[('framed_commands',(w-224,h-80,w-33,h-17)),
                                         ('hd_minimap',(w-166,16,w-33,109))])
            self.assertEqual(len(g['cells']),cols*rows)
            self.assertTrue(all(c['active'] for c in g['cells']))
            self.assertEqual(g['cells'][-1]['logical_rect'],(32+(cols-1)*64,16+(rows-1)*64,w-33,h-17))
            self.assertTrue(g['cells'][-1]['partial'])
            area=0
            for c in g['cells']:
                l,t,r,b=c['logical_rect'];self.assertTrue(32<=l<=r<=w-33 and 16<=t<=b<=h-17)
                area+=(r-l+1)*(b-t+1)
            self.assertEqual(area,(w-64)*(h-32))

    def test_observed_minimap_does_not_hide_unrelated_terrain_and_disabled_has_no_mask(self):
        image=Image(1280,720,[(0,0,0)]*(1280*720))
        g=coverage.framed_coverage_geometry(coverage.FRAMED_STAGE,1280,720,
                  minimap_enabled=True,minimap_width=134,minimap_height=94)
        outside=coverage.cell_stats(image,(1080,16,1111,79),g['masks'],1280,720,12,5,0,20)
        inside=coverage.cell_stats(image,(1120,16,1183,79),g['masks'],1280,720,12,5,0,20)
        self.assertEqual(outside['masked_pixels'],0);self.assertIn('blank',outside['flags'])
        self.assertEqual(inside['masked_percent'],100);self.assertIn('insufficient_unmasked',inside['flags'])
        disabled=coverage.framed_coverage_geometry(coverage.FRAMED_STAGE,1280,720,minimap_enabled=False)
        self.assertEqual([n for n,_ in disabled['masks']],['framed_commands'])
        unmasked=coverage.cell_stats(image,(1120,16,1183,79),disabled['masks'],1280,720,12,5,0,20)
        self.assertEqual(unmasked['masked_pixels'],0);self.assertIn('blank',unmasked['flags'])

    def test_framed_observation_and_stage_errors_fail_closed(self):
        base=dict(stage=coverage.FRAMED_STAGE,width=800,height=600,minimap_enabled=True,
                  minimap_width=214,minimap_height=214)
        for change in ({'minimap_enabled':None},{'minimap_enabled':1},{'minimap_width':None},
                       {'minimap_height':None},{'minimap_width':0},{'minimap_height':-1},
                       {'minimap_width':True},{'minimap_width':1000},{'minimap_height':1000},
                       {'stage':'synthetic-validation'},{'stage':coverage.FRAMED_STAGE+'-typo'},
                       {'minimap_enabled':False},{'width':801}):
            with self.assertRaises(ValueError):coverage.framed_coverage_geometry(**(base|change))

    def test_framed_cli_records_stage_masks_partial_cells_and_rejects_overrides(self):
        with tempfile.TemporaryDirectory(prefix='clash-framed-coverage-fixture-') as folder:
            png,out=Path(folder)/'fixture.png',Path(folder)/'coverage.json'
            command=[sys.executable,'-B',str(Path(coverage.__file__)),str(png),
                     '--stage',coverage.FRAMED_STAGE,'--write-json',str(out)]
            for w,h,enabled in ((800,600,1),(802,602,0)):
                write_fixture_png(png,w,h)
                options=['--logical-width',str(w),'--logical-height',str(h),'--minimap-enabled',str(enabled)]
                if enabled:options+=['--minimap-width','134','--minimap-height','94']
                run=subprocess.run(command+options,capture_output=True,text=True)
                self.assertEqual(run.returncode,0,run.stderr)
                report=json.loads(out.read_text());profile=report['framed_profile'];cells=report['images'][0]['cells']
                self.assertEqual(profile['stage'],coverage.FRAMED_STAGE)
                self.assertEqual(profile['terrain'],[32,16,w-33,h-17])
                self.assertEqual(profile['minimap']['enabled'],bool(enabled))
                self.assertEqual(cells[-1]['logical_rect'],[736,528,w-33,h-17]);self.assertTrue(cells[-1]['partial'])
                self.assertEqual(report['images'][0]['summary']['active_cells'],108)
                self.assertEqual(report['parameters']['bottom_row_active_cols'],12)
            for extra in (['--columns','12'],['--rows','9'],['--bottom-row-active-cols','0'],
                          ['--origin-x','0'],['--origin-y','0'],['--tile-size','32'],['--no-default-masks'],
                          ['--mask','everything:0,0,801,601'],['--minimap-enabled','2']):
                run=subprocess.run(command+options+extra,capture_output=True,text=True)
                self.assertNotEqual(run.returncode,0,extra)
            for invalid in ([],['--minimap-enabled','1'],['--minimap-enabled','1','--minimap-width','214']):
                run=subprocess.run(command+invalid,capture_output=True,text=True)
                self.assertNotEqual(run.returncode,0,invalid)

    def test_framed_capture_physical_dimensions_are_not_inferred_from_scaled_image(self):
        with tempfile.TemporaryDirectory(prefix='clash-framed-coverage-size-fixture-') as folder:
            png=Path(folder)/'fixture.png';write_fixture_png(png)
            run=subprocess.run([sys.executable,'-B',str(Path(coverage.__file__)),str(png),
                  '--stage',coverage.FRAMED_STAGE,'--minimap-enabled','0'],capture_output=True,text=True)
            self.assertNotEqual(run.returncode,0)
            self.assertIn('framed capture dimensions differ',run.stderr)


if __name__ == "__main__":
    unittest.main()
