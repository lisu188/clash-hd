"""Whole-image replay, independent relocation, loaded-byte coverage and SEC_IMAGE.

The original is read only. SEC_IMAGE creates an image-section handle without
mapping or executing it. No game, debugger, proxy or candidate process runs.
"""
from contextlib import redirect_stderr
import io
import os
from pathlib import Path
import re
import struct
import tempfile
import unittest
from unittest.mock import patch

import build_framed_modal_primary_candidate as builder
from src.patcher import complete_hd_candidate as complete
from src.patcher import pe_extension as pe
from test_pe_extension import independent_image, rebase
from test_build_framed_modal_candidate import replay
from test_pe_modal_extension import native_image_section

ORIGINAL = Path('C:/Clash/clash95.exe')


def loaded_checks(probe):
    pattern = r'\((wo|by)\(([0-9a-f]{8})\) != ([0-9a-f]+)\)'
    rows = []
    for line in probe.splitlines():
        if '_CONTRACT_FAIL' not in line: continue
        residual = re.sub(pattern, 'READ', line)
        if not re.fullmatch(r'\.if \(READ(?: \| READ)*\) \{ \.echo (?:PTILE|ARMY|MPRIMARY)_CONTRACT_FAIL; q \}', residual):
            raise AssertionError('unexpected loaded-byte check grammar')
        rows.extend((int(va, 16), 2 if kind == 'wo' else 1, int(value, 16))
                    for kind, va, value in re.findall(pattern, line))
    if not rows: raise AssertionError('missing loaded-byte checks')
    return rows


@unittest.skipUnless(ORIGINAL.is_file(), 'user-owned original required for exact recipe reconstruction')
class PrimaryBuildTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = ORIGINAL.read_bytes()
        cls.results = {}
        cls.folder = Path(tempfile.mkdtemp(prefix='clash-modal-primary-loader-', dir='C:/ClashTests')) if os.name == 'nt' else None
        print('Retained primary SEC_IMAGE fixture directory:', cls.folder, flush=True)
        for resolution in complete.RESOLUTIONS:
            cls.results[resolution] = builder.build_candidate(cls.original, resolution)
            print('Built primary fixture:', resolution, cls.results[resolution][1]['candidate_sha256'], flush=True)

    def base(self, metadata):
        slots = metadata['base_candidate']
        base = complete.apply_records(self.original, slots['base_candidate']['patch_records'],
                                      expected_base_sha256=complete.BASE_SHA256)
        self.assertEqual(builder.sha(base), slots['base_candidate_sha256'])
        result = replay(base, slots['edits'])
        self.assertEqual(builder.sha(result), slots['candidate_sha256'])
        return result

    def test_exact_replay_all_bytes_and_sources_preserve_both_predecessors(self):
        for image, metadata, probe in self.results.values():
            base = self.base(metadata)
            self.assertEqual(builder.sha(base), metadata['base_candidate_sha256'])
            self.assertEqual(replay(base, metadata['edits']), image)
            self.assertEqual(builder.sha(image), metadata['candidate_sha256'])
            self.assertEqual(builder.sha(probe.encode()), metadata['probe_sha256'])
            self.assertEqual(metadata['source_hashes'],
                {name: builder.sha((builder.ROOT / name).read_bytes()) for name in metadata['source_hashes']})
            self.assertEqual(metadata['stage'], builder.STAGE)
            self.assertNotEqual(metadata['base_candidate']['stage'], builder.STAGE)
            self.assertEqual(metadata['base_candidate']['base_candidate']['recipe_revision'], 'complete_hd_v1')
            for key in ('runtime_executed', 'installation_ready', 'manual_input_proof',
                        'promotion_ready', 'primary_composition_proven'):
                self.assertFalse(metadata[key])
            self.assertTrue(metadata['probe_contract']['requires_new_stage_consumer'])
        self.assertEqual(ORIGINAL.read_bytes(), self.original)

    def test_independent_loader_rebase_and_image_section_admission(self):
        for resolution, (image, metadata, _) in self.results.items():
            base = self.base(metadata)
            old_memory, old_sections, old_fields, _ = independent_image(base)
            memory, sections, fields, _ = independent_image(image)
            self.assertEqual(sections[:12], old_sections)
            self.assertEqual(len(sections), 13)
            self.assertEqual((sections[-1][0], sections[-1][-1]), (b'.hdprim', pe.RX_CODE))
            new = {metadata['code_rva'] + r['offset'] for r in metadata['relocations'] if r['kind'] == 'abs32'}
            self.assertEqual(set(fields), set(old_fields) | new)
            self.assertEqual(len(fields), len(set(fields)))
            for delta in (-0x100000, 0x2100000):
                moved = rebase(memory, fields, delta)
                old_moved = rebase(old_memory, old_fields, delta)
                for rva in old_fields:
                    self.assertEqual(moved[rva:rva + 4], old_moved[rva:rva + 4])
                for row in metadata['relocations']:
                    rva = metadata['code_rva'] + row['offset']
                    if row['kind'] == 'abs32':
                        self.assertEqual(struct.unpack_from('<I', moved, rva)[0], row['target'] + delta)
                    else:
                        self.assertEqual(moved[rva:rva + 4], memory[rva:rva + 4])
            if self.folder:
                path = self.folder / (resolution + '.bin')
                with path.open('xb') as stream: stream.write(image)
                self.assertEqual(native_image_section(path),
                    dict(accepted=True, error=0, view_mapped=False, process_started=False))

    def test_loaded_probe_covers_all_hooks_new_code_cursor_and_predecessor(self):
        for image, metadata, probe in self.results.values():
            memory, _, _, _ = independent_image(image)
            covered = set()
            for va, size, value in loaded_checks(probe):
                self.assertEqual(int.from_bytes(memory[va - 0x400000:va - 0x400000 + size], 'little'), value)
                covered.update(range(va, va + size))
            spans = [(metadata['code_va'], metadata['code_raw_bytes']), (0x400348, 40),
                     (metadata['base_candidate']['code_va'], metadata['base_candidate']['code_raw_bytes']),
                     (metadata['modal_state_va'], 128), (0x432940, 1006), (0x4E9920, 96)]
            spans += [(va, n) for va, n, _ in builder.primary.NATIVE_SPANS + builder.primary.CURSOR_CONTEXT_SPANS]
            spans += [(va, 12) for va in builder.primary.CURSOR_DESCRIPTORS]
            spans += [(builder.primary.CURSOR_STARTUP_DESCRIPTOR, 12)]
            spans += [(h['va'], len(bytes.fromhex(h['new_hex']))) for h in metadata['hooks']]
            for va, size in spans:
                self.assertTrue(set(range(va, va + size)) <= covered, hex(va))
            self.assertEqual(probe.splitlines().count('.echo ' + metadata['probe_contract']['primary_marker']), 1)
            for token in ('COMPLETEHD_CONTRACT_PASS', 'SLOTS_CONTRACT_PASS', 'ARMY_CONTRACT_PASS'):
                self.assertNotIn('.echo ' + token, probe)
            self.assertIn(f'PTILE_CONTRACT_PASS stage={builder.STAGE} ', probe)

    def test_unknown_original_fails_closed(self):
        with self.assertRaises(ValueError): builder.build_candidate(self.original[:-1], '1024x768')


class PrimaryBuilderBoundaryTests(unittest.TestCase):
    def test_cli_rejects_unsafe_paths_before_build(self):
        common = ['--original', str(ORIGINAL), '--resolution', '1024x768']
        for extra in (['--output', str(ORIGINAL)], ['--output', str(builder.ROOT / 'a.exe')],
                      ['--output', 'C:/ClashTests/a.bin'], ['--preflight', '--output', 'C:/ClashTests/a.exe']):
            with patch.object(builder, 'build_candidate') as build, redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                builder.main(common + extra)
            build.assert_not_called()

    def test_existing_bundle_never_overwrites(self):
        with tempfile.TemporaryDirectory(prefix='clash-primary-output-') as folder:
            # Redirect only the allowed-root resolution to this temporary
            # directory; all three real filesystem collision checks still run.
            resolve = Path.resolve
            def allowed_root(path, *args, **kwargs):
                if str(path).replace('\\', '/') == 'C:/ClashTests': return resolve(Path(folder))
                return resolve(path, *args, **kwargs)
            for index, suffix in enumerate(('.exe', '.candidate.json', '.cdb')):
                path = Path(folder) / f'candidate{index}.exe'
                occupied = path.with_suffix(suffix)
                occupied.write_bytes(b'keep')
                with patch.object(Path, 'resolve', allowed_root), patch.object(builder, 'build_candidate') as build:
                    with self.assertRaises(FileExistsError):
                        builder.write_candidate(ORIGINAL, path, '1024x768')
                    build.assert_not_called()
                self.assertEqual(occupied.read_bytes(), b'keep')


if __name__ == '__main__': unittest.main(verbosity=2)
