#!/usr/bin/env python3
"""Offline candidate, relocation and read-only minimap-observer integration."""
from __future__ import annotations

import hashlib
from pathlib import Path
import re
import struct
import unittest
from unittest.mock import patch

import build_framed_candidate as builder
import framed_minimap_probe as observer
from test_build_framed_candidate import loaded_checks
from test_pe_extension import independent_image, rebase

ORIGINAL = Path("C:/Clash/clash95.exe")
OLD_IMAGES = {
    "800x600": "7fad16f167205fb34ecbc99a6a1ff6180c710807f99b19f25efb48a8b1c8d15b",
    "1024x768": "3e9969a1e9285a9e65290072ea89cb2a3f224bd118ef267794fd1028ac5d7053",
    "1280x720": "883bdeeb388ca294a2bf37195c0d18ee069ed6e668ffbc4e6a9e905ca3ccf913",
    "1280x960": "e7d0b80f1af5b2d6821037b212c9e8081c48828e97692124fe9c481b9dab8ddc",
    "1920x1080": "5402ca1cb21dff60e6bb8dfbdcc92db73a12515652451f00df9273029a0564ae",
    "802x602": "dd54a298c4ab8e40db67ffff28672854b062c29554a16556a43f872ab28d4e3c",
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def synthetic_main(extra):
    # A non-runnable fixture: only the required shape, not a game route.
    capture = (r'bp 00406FA0 ".if (poi(005202e4) == 0) { .echo FRAMED_CAPTURE_REJECT missing_game_data; q } '
               r'.else { .printf \"FRAMED_MINIMAP enabled=%d origin=(%d,%d) size=(%d,%d)\\n\", 1, 554, 16, 214, 214; '
               r'.printf \"PTILE_TRACE_CLOSED tid=%x eip=%p esp=%p\\n\", @$tid, @eip, @esp; .echo SURFDUMP_HOST_READY; }"')
    return 'bc *\n' + extra + '\n' + capture + '\ng\n\n'


@unittest.skipUnless(ORIGINAL.is_file(), "requires user-owned original; images stay in memory")
class IntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = ORIGINAL.read_bytes()
        cls.results = {r: builder.build_candidate(cls.original, r, minimap_viewport=True) for r in OLD_IMAGES}

    def test_optional_revision_preserves_all_six_previous_images_and_default(self):
        for resolution, expected in OLD_IMAGES.items():
            with self.subTest(resolution=resolution):
                default = builder.build_candidate(self.original, resolution)
                explicit = builder.build_candidate(self.original, resolution, minimap_viewport=False)
                self.assertEqual(digest(default[0]), expected)
                self.assertEqual(default[0], explicit[0])
                self.assertEqual(default[2], explicit[2])
                self.assertNotIn("minimap_viewport", default[1])
                new, metadata, _ = self.results[resolution]
                self.assertNotEqual(new, default[0])
                self.assertTrue(metadata["minimap_viewport"])
                self.assertEqual(metadata["stage"], builder.STAGE)
                self.assertNotIn(metadata["stage"], builder.recipe.patcher.STAGE_GROUPS)

    def test_exact_thirteenth_hook_and_complete_metadata_reconstruction(self):
        for resolution, (image, metadata, _) in self.results.items():
            with self.subTest(resolution=resolution):
                self.assertEqual(len(metadata["hooks"]), 13)
                edit = next(row for row in metadata["hooks"] if row["va"] == 0x40D633)
                self.assertEqual((edit["offset"], edit["old_hex"]), (0xCA33, "a1e4025200"))
                self.assertEqual(bytes.fromhex(edit["new_hex"])[0], 0xE9)
                self.assertEqual({r["rva"] for r in metadata["removed_highlow"]}, {0xB885, 0x187A2, 0x187B8, 0xD634})
                rebuilt = bytearray(self.original)
                for row in (*metadata["selected_patches"], *metadata["edits"]):
                    off = row["offset"]; old = bytes.fromhex(row["old_hex"]); new = bytes.fromhex(row["new_hex"])
                    self.assertEqual(rebuilt[off:off+len(old)], old)
                    if not old: self.assertEqual(off, len(rebuilt))
                    rebuilt[off:off+len(old)] = new
                self.assertEqual(bytes(rebuilt), image)
                self.assertFalse(metadata["runtime_executed"])
                self.assertFalse(metadata["promotion_ready"])
                self.assertEqual(metadata["source_sha256"][builder.MINIMAP_SOURCE], builder.MINIMAP_SOURCE_SHA256)
        self.assertEqual(ORIGINAL.read_bytes(), self.original)

    def test_independent_rebase_and_loaded_checks_cover_new_payload_and_hook(self):
        for image, metadata, probe in self.results.values():
            memory, _, fixups, _ = independent_image(image)
            checks = loaded_checks(probe)
            covered = set()
            for va, size, expected in checks:
                self.assertEqual(int.from_bytes(memory[va-0x400000:va-0x400000+size], "little"), expected)
                covered.update(range(va, va+size))
            self.assertTrue(set(range(0x40D633, 0x40D638)) <= covered)
            self.assertTrue(set(range(metadata["code_va"], metadata["code_va"]+metadata["code_bytes"])) <= covered)
            for delta in (0x2000000, -0x100000):
                moved = rebase(memory, fixups, delta)
                for row in metadata["relocations"]:
                    at = metadata["code_rva"] + row["offset"]
                    if row["kind"] == "abs32":
                        self.assertEqual(struct.unpack_from("<I", moved, at)[0], (row["target"]+delta) & 0xFFFFFFFF)
                    else:
                        self.assertEqual(moved[at:at+4], memory[at:at+4])
                        self.assertEqual((metadata["code_va"]+delta+row["offset"]+4+struct.unpack_from("<i", moved, at)[0]) & 0xFFFFFFFF,
                                         (row["target"]+delta) & 0xFFFFFFFF)

    def test_observer_keeps_canonical_trace_adds_only_readonly_draw_and_state(self):
        for resolution, (image, metadata, extra) in self.results.items():
            source = synthetic_main(extra)
            packet = observer.build_observed_probe(self.original, image, resolution=resolution, rendered_probe=source)
            self.assertEqual(packet["probe"].count(extra.strip()), 1)
            self.assertEqual(packet["canonical_extra_sha256"], digest(extra.encode("ascii")))
            self.assertEqual(packet["source_main_sha256"], digest(source.encode("ascii")))
            self.assertEqual(packet["observed_main_sha256"], digest(packet["probe"].encode("ascii")))
            self.assertEqual([r["breakpoint"] for r in packet["observer_bindings"]], [80, 81])
            self.assertEqual([r["va"] for r in packet["observer_bindings"]],
                             [metadata["minimap_viewport_contract"]["observers"][n] for n in ("memory", "primary")])
            commands = packet["snippet"] + packet["capture_action"]
            self.assertNotRegex(commands, r"(?:^|[;{}])\s*(?:e[bdwq]|r\s+|b[dec]\s)")
            self.assertIn("@eax, @edx, @ebx, @ecx, poi(@esp), poi(@esp+4), @$tid", commands)
            self.assertLess(packet["probe"].index("FRAMED_MINIMAP_VIEWPORT"), packet["probe"].index("FRAMED_MINIMAP enabled"))
            self.assertTrue(all(len(line) < 4096 for line in packet["probe"].splitlines()))
            self.assertFalse(packet["acceptance"])

    def test_observer_rejects_candidate_mutation_wrong_extra_and_occupied_ids(self):
        image, _, extra = self.results["800x600"]
        source = synthetic_main(extra)
        variants = [source.replace(extra, ""), source.replace(extra, extra+extra),
                    source.replace("g\n\n", 'bp80 00401234 "gc"\ng\n'),
                    source.replace("g\n\n", 'bp81 00401234 "gc"\ng\n'),
                    source.replace("g\n\n", 'bd 80\ng\n'),
                    source.replace("FRAMED_CAPTURE_REJECT missing_game_data", "unprotected"),
                    source.replace("FRAMED_MINIMAP enabled", "FRAMED_MINIMAP_OTHER enabled"),
                    source+"\x00"]
        for value in variants:
            with self.assertRaises(ValueError):
                observer.build_observed_probe(self.original, image, resolution="800x600", rendered_probe=value)
        changed = bytearray(image); changed[0xCA33] ^= 1
        with self.assertRaisesRegex(ValueError, "exact minimap-enabled"):
            observer.build_observed_probe(self.original, bytes(changed), resolution="800x600", rendered_probe=source)

    def test_optional_source_pin_and_explicit_boolean_fail_closed(self):
        with patch.object(builder, "MINIMAP_SOURCE_SHA256", "0"*64), self.assertRaisesRegex(ValueError, "reviewed framed source changed"):
            builder.build_candidate(self.original, "800x600", minimap_viewport=True)
        for value in (1, None, "true"):
            with self.assertRaisesRegex(ValueError, "explicit boolean"):
                builder.build_candidate(self.original, "800x600", minimap_viewport=value)


if __name__ == "__main__":
    unittest.main()
