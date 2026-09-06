"""Actual image construction/rebase and opt-in boundaries; no runtime or output EXE."""
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import re
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

import build_partial_tile_candidate as builder
from test_pe_extension import independent_image, rebase

ORIGINAL = Path('C:/Clash/clash95.exe')
RESOLUTIONS = ('800x600', '1024x768', '1280x720', '1280x960', '1920x1080', '802x602')


@unittest.skipUnless(ORIGINAL.is_file(), 'requires user-owned original for offline construction')
class InitialCandidateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = ORIGINAL.read_bytes()
        cls.results = {r: builder.build_candidate(cls.original, r, initial_paint=True) for r in RESOLUTIONS}

    def test_exact_four_hooks_and_relocation_inventory(self):
        _, _, old_fixups, _ = independent_image(self.original)
        for resolution, (image, metadata, probe) in self.results.items():
            with self.subTest(resolution=resolution):
                memory, sections, fixups, _ = independent_image(image)
                legacy, _, _ = builder.build_candidate(self.original, resolution)
                old_memory, old_sections, _, _ = independent_image(legacy)
                self.assertEqual(len(sections), 8)
                self.assertEqual(sections[-1][0], b'.hdcode')
                self.assertEqual(sections[-1][-1], 0x60000020)
                self.assertEqual(metadata['installed_hook_names'], ['full_converge', 'full_present', 'incremental', 'initial_paint'])
                self.assertEqual(set(old_fixups) - set(fixups), {0x187A2, 0x187B8, 0xB885})
                self.assertIn(0xB88B, fixups)
                self.assertEqual(len(fixups), len(set(fixups)))
                self.assertEqual(memory[0xB88A:0xB894], bytes.fromhex('a1ec025200e8dc7a0100'))
                self.assertEqual(memory[0xB884], 0xE9)
                self.assertEqual(memory[0xB889], 0x90)
                target = 0x40B889 + struct.unpack_from('<i', memory, 0xB885)[0]
                self.assertTrue(metadata['code_va'] <= target < metadata['code_va'] + metadata['code_bytes'])
                # No existing section byte changes from the partial candidate
                # except the newly authenticated first-entry hook.
                memory[0xB884:0xB88A] = old_memory[0xB884:0xB88A]
                for _, rva, size, *_ in old_sections[:-1]:
                    self.assertEqual(memory[rva:rva + size], old_memory[rva:rva + size])
                declared = {metadata['code_rva'] + r['offset'] for r in metadata['relocations'] if r['kind'] == 'abs32'}
                self.assertEqual(set(fixups), (set(old_fixups) - {0x187A2, 0x187B8, 0xB885}) | declared)
                self.assertEqual(metadata['stage'], builder.INITIAL_STAGE)
                self.assertNotEqual(metadata['stage'], builder.patcher.DEFAULT_STAGE)
                self.assertFalse(metadata['runtime_executed'])
                self.assertFalse(metadata['promotion_ready'])
                self.assertEqual(builder.sha(image), metadata['output_sha256'])

    def test_all_edits_reconstruct_and_rebase_without_touching_original(self):
        for image, metadata, _ in self.results.values():
            rebuilt = bytearray(self.original)
            for edit in [*metadata['selected_patches'], *metadata['edits']]:
                offset = edit['offset']
                old, new = bytes.fromhex(edit['old_hex']), bytes.fromhex(edit['new_hex'])
                self.assertEqual(rebuilt[offset:offset + len(old)], old)
                if not old:
                    self.assertEqual(offset, len(rebuilt))
                rebuilt[offset:offset + len(old)] = new
            self.assertEqual(bytes(rebuilt), image)
            memory, _, fixups, _ = independent_image(image)
            for delta in (0x02000000, -0x100000):
                moved = rebase(memory, fixups, delta)
                self.assertEqual(moved[0xB884:0xB88A], memory[0xB884:0xB88A])
                self.assertEqual(struct.unpack_from('<I', moved, 0xB88B)[0], 0x5202EC + delta)
                for r in metadata['relocations']:
                    rva = metadata['code_rva'] + r['offset']
                    if r['kind'] == 'abs32':
                        self.assertEqual(struct.unpack_from('<I', moved, rva)[0], (r['target'] + delta) & 0xffffffff)
                    else:
                        self.assertEqual(moved[rva:rva + 4], memory[rva:rva + 4])
        self.assertEqual(ORIGINAL.read_bytes(), self.original)

    def test_loaded_contract_covers_new_code_shared_join_and_pause_boundary(self):
        for image, metadata, probe in self.results.values():
            memory, _, _, _ = independent_image(image)
            covered = set()
            for reader, address, expected in re.findall(r'\((wo|by)\(([0-9a-f]{8})\) != ([0-9a-f]+)\)', probe):
                address = int(address, 16)
                size = 2 if reader == 'wo' else 1
                actual = int.from_bytes(memory[address - 0x400000:address - 0x400000 + size], 'little')
                self.assertEqual(actual, int(expected, 16))
                covered.update(range(address, address + size))
            admission = metadata['initial_paint_contract']['observer_spans']['admission']['preceding_call']['target_va']
            self.assertTrue(set(range(admission, metadata['code_va'] + metadata['code_bytes'])) <= covered)
            self.assertTrue(set(range(0x40B884, 0x40B894)) <= covered)
            self.assertTrue(set(range(0x406FA0, 0x406FB0)) <= covered)
            self.assertTrue(all(len(line) < 4096 for line in probe.splitlines()))
            ready = metadata['initial_status_vas']['ready']
            self.assertIn(f'bp73 {ready:08x} ', probe)
            self.assertNotIn('bp73 0040b88a ', probe)
            self.assertIn(f'stage={builder.INITIAL_STAGE}', probe)
            self.assertIn('PTILE_EVENT seq=', probe)

    def test_opt_in_preflight_is_in_memory_and_wrong_source_fails_closed(self):
        with tempfile.TemporaryDirectory(prefix='clash-initial-preflight-') as name:
            output = io.StringIO()
            argv = ['builder', '--original', str(ORIGINAL), '--resolution', '800x600', '--initial-map-paint',
                    '--preflight', '--output', str(Path(name) / 'unused.exe')]
            with patch.object(sys, 'argv', argv), redirect_stdout(output):
                self.assertEqual(builder.main(), 0)
            result = json.loads(output.getvalue())
            self.assertEqual(result['stage'], builder.INITIAL_STAGE)
            self.assertEqual(result['candidate_sha256'], builder.sha(self.results['800x600'][0]))
            self.assertFalse(result['runtime_executed'])
            self.assertEqual(list(Path(name).iterdir()), [])
        with patch.object(builder, 'INITIAL_SOURCE_SHA256', '0' * 64):
            with self.assertRaisesRegex(ValueError, 'initial-paint source changed'):
                builder.build_candidate(self.original, '800x600', initial_paint=True)


if __name__ == '__main__':
    unittest.main()
