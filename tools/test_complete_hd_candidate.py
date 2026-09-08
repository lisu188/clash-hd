"""Portable fixtures for the integrated candidate boundary; no game execution."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.patcher import complete_hd_candidate as candidate


class CandidateBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.original = b"MZ" + bytes(range(32))
        self.output = self.original[:10] + b"XY" + self.original[12:] + bytes(135)
        self.view = SimpleNamespace(image_base=0x400000, sections=[
            SimpleNamespace(raw_offset=16, raw_size=256, rva=0x1000)
        ])
        self.records = candidate.byte_records(self.original, self.output, self.view)

    def test_every_change_and_appended_byte_replays(self):
        self.assertEqual(candidate.apply_records(self.original, self.records), self.output)
        self.assertEqual(self.records[0]["va"], 0x40000A)
        self.assertTrue(any(row["appended"] for row in self.records))
        self.assertTrue(all(len(bytes.fromhex(row["new_hex"])) <= 64 for row in self.records))

    def test_bad_original_overlap_gap_and_stage_rejected(self):
        with self.assertRaisesRegex(ValueError, "old bytes"):
            candidate.apply_records(self.original[:10] + b"ZZ" + self.original[12:], self.records)
        for mutate in (
            lambda rows: rows.insert(1, deepcopy(rows[0])),
            lambda rows: rows[-1].update(file_offset=rows[-1]["file_offset"] + 1),
            lambda rows: rows[0].update(stage="stable"),
            lambda rows: rows[0].update(new_hex=""),
        ):
            bad = deepcopy(self.records)
            mutate(bad)
            with self.assertRaises(ValueError):
                candidate.apply_records(self.original, bad)

    def test_cannot_truncate_or_build_unknown_original(self):
        with self.assertRaises(ValueError):
            candidate.byte_records(self.original, b"MZ", self.view)
        with self.assertRaisesRegex(ValueError, "unknown original"):
            candidate.build_candidate(self.original, "1920x1080")
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            candidate.apply_records(b"NZ" + self.original[2:], self.records,
                                    expected_base_sha256=candidate.sha256(self.original))

    def test_exclusive_bundle_failure_preserves_preexisting_file(self):
        with tempfile.TemporaryDirectory() as temporary:
            paths = tuple(Path(temporary) / name for name in ("candidate.exe", "candidate.json", "probe.cdb"))
            paths[2].write_bytes(b"belongs to another invocation")
            with self.assertRaises(FileExistsError):
                candidate._write_bundle(paths, (b"candidate", b"manifest", b"probe"))
            self.assertFalse(paths[0].exists())
            self.assertFalse(paths[1].exists())
            self.assertEqual(paths[2].read_bytes(), b"belongs to another invocation")

    def test_timestamp_removal_preserves_evidence_values(self):
        source = {"generated_at": "now", "source_hashes": {"x": "abc"},
                  "predecessor": {"generated_at": "earlier", "passed": False}}
        self.assertEqual(candidate.deterministic(source), {
            "source_hashes": {"x": "abc"}, "predecessor": {"passed": False}})

    def test_output_boundary_rejects_original_and_repo_before_reading(self):
        for output in (Path("C:/Clash/clash95.exe"), ROOT / "candidate.exe", Path("C:/ClashTests/test.json")):
            with self.assertRaises(ValueError):
                candidate.write_candidate(Path("absent.exe"), output, "800x600")


@unittest.skipUnless(Path("C:/Clash/clash95.exe").is_file(), "user-owned original required; no runtime")
class IntegratedBuildTests(unittest.TestCase):
    def test_six_resolutions_reproduce_all_bytes_and_protocols(self):
        original = Path("C:/Clash/clash95.exe").read_bytes()
        for resolution in candidate.RESOLUTIONS:
            with self.subTest(resolution=resolution):
                image, manifest, probe = candidate.build_candidate(original, resolution)
                self.assertEqual(candidate.apply_records(original, manifest["patch_records"],
                                 expected_base_sha256=candidate.BASE_SHA256), image)
                self.assertEqual(manifest["candidate_sha256"], candidate.sha256(image))
                self.assertEqual(manifest["probe_sha256"], candidate.sha256(probe.encode("utf-8")))
                self.assertEqual(manifest["predecessor"]["resolution"], resolution)
                self.assertEqual(manifest["stage"], candidate.STAGE)
                self.assertTrue(manifest["features"]["minimap_viewport"])
                self.assertFalse(manifest["features"]["expanded_battle"])
                self.assertFalse(manifest["runtime_executed"])
                self.assertFalse(manifest["promotion_ready"])
                for field in ("complete_marker", "inherited_marker"):
                    self.assertEqual(probe.splitlines().count(".echo " + manifest["probe_contract"][field]), 1)
                for name, expected in manifest["source_hashes"].items():
                    self.assertEqual(candidate.sha256((ROOT / name).read_bytes()), expected, name)
                if resolution in ("800x600", "1024x768", "1920x1080"):
                    self.assertEqual(candidate.build_candidate(original, resolution), (image, manifest, probe))
        self.assertEqual(Path("C:/Clash/clash95.exe").read_bytes(), original)

    def test_source_changed_during_build_is_rejected(self):
        original = Path("C:/Clash/clash95.exe").read_bytes()
        import build_framed_army_candidate as army
        original_build = army.build_candidate

        def altered(*args, **kwargs):
            image, metadata, probe = original_build(*args, **kwargs)
            metadata["source_sha256"] = dict(metadata["source_sha256"])
            metadata["source_sha256"]["src/patcher/framed_army_input.py"] = "0" * 64
            return image, metadata, probe

        with patch.object(army, "build_candidate", side_effect=altered):
            with self.assertRaisesRegex(ValueError, "source changed"):
                candidate.build_candidate(original, "800x600")


if __name__ == "__main__":
    unittest.main()
