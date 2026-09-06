"""Synthetic source-cell checks; no proprietary fixtures or runtime."""
import unittest
import json
from pathlib import Path
import tempfile

from action_bar_surface_audit import compare_cells, load_sprites, audit_summary, digest, FRAMED_STAGE
from cdb_surface_dump_to_png import convert
from hd_layout_asset_composition import Sprite


class ActionBarAuditTests(unittest.TestCase):
    def setUp(self):
        self.sprites = {i: Sprite(64, 32, tuple(
            20 + i * 16 + (x + 3 * y) % 13 for y in range(32) for x in range(64)))
            for i in range(12)}
        self.sprites[14] = Sprite(64, 32, tuple(
            240 if x in (0, 63) or y in (0, 31) else None
            for y in range(32) for x in range(64)))

    def frame(self, width, height, *, legacy=False, hover=False, framed=False):
        raw = bytearray(width * height)
        x0, y0 = (416, 400) if legacy else (width - 224, height - 80) if framed else (width - 192, height - 72)
        for cell in range(6):
            for y in range(32):
                for x in range(64):
                    value = self.sprites[cell * 2 + 1].pixels[y * 64 + x]
                    overlay = self.sprites[14].pixels[y * 64 + x]
                    raw[(y0 + cell // 3 * 32 + y) * width + x0 + cell % 3 * 64 + x] = (
                        overlay if hover and overlay is not None else value)
        return raw

    def test_complete_bar_at_each_resolution_and_hover(self):
        for width, height in ((800, 600), (1024, 768), (1280, 720), (1920, 1080), (802, 602)):
            for hover in (False, True):
                with self.subTest(size=(width, height), hover=hover):
                    cells = compare_cells(self.frame(width, height, hover=hover), width, height, self.sprites)
                    self.assertTrue(all(c["exact_source_match"] for c in cells))
                    self.assertEqual(cells[-1]["anchor"], [width - 64, height - 40])

    def test_one_missing_pixel_fails_only_affected_cell(self):
        raw = self.frame(800, 600)
        raw[591 * 800 + 799] = 0
        cells = compare_cells(raw, 800, 600, self.sprites)
        self.assertEqual([c["exact_source_match"] for c in cells], [True] * 5 + [False])
        self.assertEqual(cells[-1]["closest_source_variant"]["mismatched_pixels"], 1)

    def test_partial_overwrite_reports_exact_surviving_rows_without_pass(self):
        raw = self.frame(1024, 768)
        for y in range(696, 720):
            raw[y * 1024 + 832:y * 1024 + 1024] = bytes(192)
        cells = compare_cells(raw, 1024, 768, self.sprites)
        self.assertEqual([c["exact_source_match"] for c in cells], [False] * 3 + [True] * 3)
        self.assertEqual(cells[0]["closest_source_variant"]["exact_rows"], list(range(24, 32)))

    def test_legacy_bar_does_not_pass_hd_anchor(self):
        raw = self.frame(800, 600, legacy=True)
        self.assertFalse(any(c["exact_source_match"] for c in compare_cells(raw, 800, 600, self.sprites)))
        self.assertTrue(all(c["exact_source_match"] for c in compare_cells(raw, 800, 600, self.sprites, legacy=True)))

    def test_bad_source_and_surface_fail_closed(self):
        with self.assertRaises(ValueError):
            load_sprites(b"unknown resource")
        for raw, width, height in ((bytes(10), 800, 600), (bytes(640 * 480), 639, 480)):
            with self.assertRaises(ValueError):
                compare_cells(raw, width, height, self.sprites)

    def test_truncated_empty_and_invalid_sprites_fail_closed(self):
        for sprite in (Sprite(64, 32, ()), Sprite(64, 32, (0,) * 10),
                       Sprite(64, 32, (None,) * 2048), Sprite(64, 32, (256,) * 2048)):
            with self.assertRaises(ValueError):
                compare_cells(self.frame(800, 600), 800, 600, self.sprites | {0: sprite})

    def test_framed_stage_selects_complete_six_cells_without_reclassifying_old_anchors(self):
        for width,height in ((800,600),(1024,768),(1280,720),(1280,960),(1920,1080),(802,602)):
            raw=self.frame(width,height,framed=True,hover=True)
            cells=compare_cells(raw,width,height,self.sprites,stage=FRAMED_STAGE)
            self.assertTrue(all(c['exact_source_match'] for c in cells))
            self.assertEqual([c['anchor'] for c in cells],
                             [[width-224+64*(i%3),height-80+32*(i//3)] for i in range(6)])
            self.assertFalse(any(c['exact_source_match'] for c in compare_cells(raw,width,height,self.sprites)))
            self.assertFalse(any(c['exact_source_match'] for c in
                                 compare_cells(self.frame(width,height),width,height,self.sprites,stage=FRAMED_STAGE)))
            raw[(height-17)*width+width-33]=0
            failed=compare_cells(raw,width,height,self.sprites,stage=FRAMED_STAGE)
            self.assertEqual([c['exact_source_match'] for c in failed],[True]*5+[False])

    def test_unknown_framed_stage_and_conflicting_legacy_choice_fail_closed(self):
        raw=self.frame(800,600,framed=True)
        for stage in (FRAMED_STAGE+'-typo',FRAMED_STAGE.upper(),'framed-validation',True):
            with self.assertRaises(ValueError):compare_cells(raw,800,600,self.sprites,stage=stage)
        with self.assertRaises(ValueError):compare_cells(raw,800,600,self.sprites,stage=FRAMED_STAGE,legacy=True)
        with self.assertRaises(ValueError):compare_cells(bytes(801*600),801,600,self.sprites,stage=FRAMED_STAGE)

    def test_framed_summary_uses_its_bound_stage_and_keeps_failed_runtime_separate(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);raw_path=root/'surface.raw';png_path=root/'surface.png'
            metadata_path=root/'surface.png.json';summary_path=root/'summary.json';candidate=root/'candidate.fixture'
            raw_path.write_bytes(self.frame(800,600,framed=True));candidate.write_bytes(b'synthetic identity')
            metadata=convert(raw_path,png_path,800,600,800,metadata_path,None,None)
            summary=dict(RawPath=str(raw_path),PngPath=str(png_path),PngMetadata=str(metadata_path),
                         PngSha256=metadata['png_sha256'],CandidatePath=str(candidate),
                         CandidateSha256=digest(candidate.read_bytes()),RawBytes=480000,
                         Surface=dict(Width=800,Height=600,Bytes=480000),Resolution='800x600',
                         Stage=FRAMED_STAGE,Passed=False)
            summary_path.write_text(json.dumps(summary))
            result=audit_summary(summary_path,self.sprites)
            self.assertTrue(result['all_six_cells_match_source']);self.assertFalse(result['surface_gate_passed'])
            self.assertEqual(result['stage'],FRAMED_STAGE)
            summary['Stage']='synthetic-validation';summary_path.write_text(json.dumps(summary))
            self.assertFalse(audit_summary(summary_path,self.sprites)['all_six_cells_match_source'])
            summary['Stage']=FRAMED_STAGE+'-typo';summary_path.write_text(json.dumps(summary))
            with self.assertRaises(ValueError):audit_summary(summary_path,self.sprites)

    def test_screenshot_is_bound_to_raw_palette_metadata_and_candidate(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw_path, png_path = root / "surface.raw", root / "surface.png"
            metadata_path, summary_path, candidate = root / "surface.png.json", root / "summary.json", root / "candidate.fixture"
            raw_path.write_bytes(self.frame(800, 600))
            candidate.write_bytes(b"synthetic identity only, not an executable")
            metadata = convert(raw_path, png_path, 800, 600, 800, metadata_path, None, None)
            summary = {"RawPath": str(raw_path), "PngPath": str(png_path), "PngMetadata": str(metadata_path),
                       "PngSha256": metadata["png_sha256"], "CandidatePath": str(candidate),
                       "CandidateSha256": digest(candidate.read_bytes()), "RawBytes": 480000,
                       "Surface": {"Width": 800, "Height": 600, "Bytes": 480000},
                       "Resolution": "800x600", "Stage": "synthetic-validation", "Passed": True}
            summary_path.write_text(json.dumps(summary), encoding="utf-8")
            self.assertTrue(audit_summary(summary_path, self.sprites)["all_six_cells_match_source"])
            original_png = png_path.read_bytes()
            png_path.write_bytes(b"unrelated PNG")
            with self.assertRaises(ValueError):
                audit_summary(summary_path, self.sprites)
            # Updating both claimed PNG hashes cannot disguise unrelated pixels.
            summary["PngSha256"] = metadata["png_sha256"] = digest(png_path.read_bytes())
            summary_path.write_text(json.dumps(summary), encoding="utf-8")
            metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "does not encode"):
                audit_summary(summary_path, self.sprites)
            png_path.write_bytes(original_png)
            summary["PngSha256"] = metadata["png_sha256"] = digest(original_png)
            summary_path.write_text(json.dumps(summary), encoding="utf-8")
            metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
            candidate.write_bytes(b"other candidate")
            with self.assertRaisesRegex(ValueError, "candidate file SHA"):
                audit_summary(summary_path, self.sprites)


if __name__ == "__main__":
    unittest.main()
