"""Exact recipe replay, loaded-byte coverage and nonexecuting PE admission."""
from contextlib import redirect_stderr
import io
import os
from pathlib import Path
import re
import struct
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import build_framed_modal_primary_text_candidate as builder
from src.patcher import complete_hd_candidate as complete
from src.patcher import pe_extension as pe
from test_pe_extension import independent_image, rebase
from test_build_framed_modal_candidate import replay
from test_pe_modal_extension import native_image_section
from test_pe_modal_primary_text_extension import synthetic_primary, arguments as format_arguments

ORIGINAL = Path('C:/Clash/clash95.exe')
# Already-built primary-v1 candidates retained before the additive text work.
PRIMARY_V1_SHA = {
    '1024x768': 'bee7db23414bc7831d32af05ad03d04f800aa795c7af66db1bc1e7b4c9ad11b8',
    '1920x1080': '042e1681aa24d8a42f8391e2c8c7faf68fa32f47ab94551dfb52e164ab240b13',
}


def loaded_checks(probe):
    rows = []
    for line in probe.splitlines():
        if '_CONTRACT_FAIL' not in line:
            continue
        residual = builder.PREDICATE.sub('READ', line)
        if not re.fullmatch(r'\.if \(READ(?: \| READ)*\) \{ \.echo (?:PTILE|ARMY|MPRIMARY|MPRIMARYTEXT)_CONTRACT_FAIL; q \}', residual):
            raise AssertionError('unexpected loaded-byte grammar')
        rows.extend((int(va, 16), 2 if kind == 'wo' else 1, int(value, 16))
                    for kind, va, value in builder.PREDICATE.findall(line))
    if not rows:
        raise AssertionError('missing loaded-byte checks')
    return rows


class PrimaryTextBuildFixture:
    @classmethod
    def setUpClass(cls):
        cls.original = ORIGINAL.read_bytes()
        cls.results = {}
        cls.folder = Path(tempfile.mkdtemp(prefix='clash-primary-text-loader-', dir='C:/ClashTests')) if os.name == 'nt' else None
        print('Retained nonexecuting SEC_IMAGE fixture directory:', cls.folder, flush=True)
        for resolution in (cls.resolution,):
            cls.results[resolution] = builder.build_candidate(cls.original, resolution)
            print('Built primary-text fixture:', resolution, cls.results[resolution][1]['candidate_sha256'], flush=True)

    def base(self, metadata):
        primary = metadata['base_candidate']
        slots = primary['base_candidate']
        complete_context = slots['base_candidate']
        image = complete.apply_records(self.original, complete_context['patch_records'], expected_base_sha256=complete.BASE_SHA256)
        self.assertEqual(builder.sha(image), slots['base_candidate_sha256'])
        image = replay(image, slots['edits'])
        self.assertEqual(builder.sha(image), primary['base_candidate_sha256'])
        image = replay(image, primary['edits'])
        self.assertEqual(builder.sha(image), metadata['base_candidate_sha256'])
        return image

    def test_exact_replay_all_original_bytes_and_source_bindings(self):
        for resolution, (image, metadata, probe) in self.results.items():
            with self.subTest(resolution=resolution):
                base = self.base(metadata)
                self.assertEqual(replay(base, metadata['edits']), image)
                self.assertEqual(builder.sha(image), metadata['candidate_sha256'])
                self.assertEqual(builder.sha(probe.encode()), metadata['probe_sha256'])
                self.assertEqual(metadata['source_hashes'],
                                 {name: builder.sha((builder.ROOT / name).read_bytes()) for name in metadata['source_hashes']})
                self.assertEqual(metadata['stage'], builder.STAGE)
                self.assertEqual(metadata['recipe_revision'], 'owned_modal_primary_text_v1')
                self.assertEqual(metadata['base_candidate']['stage'], builder.primary.STAGE)
                self.assertEqual(metadata['base_candidate']['recipe_revision'], 'owned_modal_primary_v1')
                if resolution in PRIMARY_V1_SHA:
                    self.assertEqual(builder.sha(base), PRIMARY_V1_SHA[resolution])
                self.assertEqual(metadata['hooks'][0]['va'], 0x432C66)
                self.assertEqual(metadata['hooks'][0]['old_hex'], 'e8e594fdff')
                self.assertEqual(len(metadata['hooks']), 1)
                for key in ('runtime_executed', 'installation_ready', 'manual_input_proof', 'promotion_ready', 'primary_composition_proven'):
                    self.assertIs(metadata[key], False)
        self.assertEqual(ORIGINAL.read_bytes(), self.original)

    def test_independent_loader_rebase_and_native_image_section_admission(self):
        for resolution, (image, metadata, _) in self.results.items():
            with self.subTest(resolution=resolution):
                base = self.base(metadata)
                old_memory, old_sections, old_fields, _ = independent_image(base)
                memory, sections, fields, _ = independent_image(image)
                self.assertEqual(sections[:13], old_sections)
                self.assertEqual(len(sections), 14)
                self.assertEqual((sections[-1][0], sections[-1][-1]), (b'.hdptxt', pe.RX_CODE))
                new = {metadata['code_rva'] + row['offset'] for row in metadata['relocations'] if row['kind'] == 'abs32'}
                self.assertEqual(set(fields), set(old_fields) | new)
                self.assertEqual(len(fields), len(set(fields)))
                for delta in (-0x100000, 0x2100000):
                    moved = rebase(memory, fields, delta); old_moved = rebase(old_memory, old_fields, delta)
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
                    with path.open('xb') as stream:
                        stream.write(image)
                    self.assertEqual(native_image_section(path), dict(accepted=True, error=0, view_mapped=False, process_started=False))

    def test_probe_keeps_all_predecessor_checks_and_covers_text_and_new_header(self):
        for resolution, (image, metadata, probe) in self.results.items():
            with self.subTest(resolution=resolution):
                memory, _, _, _ = independent_image(image)
                covered = set()
                for va, size, value in loaded_checks(probe):
                    self.assertEqual(int.from_bytes(memory[va - 0x400000:va - 0x400000 + size], 'little'), value)
                    covered.update(range(va, va + size))
                spans = [(metadata['code_va'], metadata['code_raw_bytes']), (0x400370, 40),
                         (0x432C66, 5), (metadata['modal_state_va'], 128)]
                previous = metadata['base_candidate']
                for ancestor in (previous, previous['base_candidate']):
                    spans.append((ancestor['code_va'], ancestor['code_raw_bytes']))
                spans.extend((row['va'], len(bytes.fromhex(row['new_hex']))) for row in previous['hooks'])
                spans.extend((va, size) for va, size, _ in builder.text.NATIVE_SPANS)
                spans.append((builder.text.TEXT_FORMAT, 3))
                for va, size in spans:
                    self.assertTrue(set(range(va, va + size)) <= covered, hex(va))
                self.assertEqual(probe.splitlines().count('.echo ' + metadata['probe_contract']['text_marker']), 1)
                for marker in ('MPRIMARY_CONTRACT_PASS', 'SLOTS_CONTRACT_PASS', 'ARMY_CONTRACT_PASS', 'COMPLETEHD_CONTRACT_PASS'):
                    self.assertNotIn('.echo ' + marker, probe)
                self.assertIn(f'PTILE_CONTRACT_PASS stage={builder.STAGE} ', probe)
                self.assertTrue(all(len(line.encode('ascii')) < 4096 for line in probe.splitlines()))

    def test_emitter_wrong_predecessor_hash_or_source_contract_rejected(self):
        image, metadata, _ = self.results[self.resolution]
        base = self.base(metadata); context = metadata['base_candidate']
        for candidate_sha, source_hashes in ((builder.sha(base), {}), ('0' * 64, context['source_hashes'])):
            fake = SimpleNamespace(candidate_sha256=candidate_sha, source_contract={'source_hashes': source_hashes})
            with (patch.object(builder.primary, 'build_candidate', return_value=(base, context, '')),
                  patch.object(builder.text, 'emit_modal_primary_text', return_value=fake),
                  self.assertRaisesRegex(ValueError, 'emitter.*context differ')):
                builder.build_candidate(self.original, self.resolution)


# Each exact build includes two independent primary-v1 reconstructions. These
# six dotted suites keep the existing aggregate's 600-second budget per suite.
@unittest.skipUnless(ORIGINAL.is_file(), 'user-owned original required for exact source recipe')
class PrimaryText800BuildTests(PrimaryTextBuildFixture, unittest.TestCase):
    resolution = '800x600'


@unittest.skipUnless(ORIGINAL.is_file(), 'user-owned original required for exact source recipe')
class PrimaryText1024BuildTests(PrimaryTextBuildFixture, unittest.TestCase):
    resolution = '1024x768'


@unittest.skipUnless(ORIGINAL.is_file(), 'user-owned original required for exact source recipe')
class PrimaryText720BuildTests(PrimaryTextBuildFixture, unittest.TestCase):
    resolution = '1280x720'


@unittest.skipUnless(ORIGINAL.is_file(), 'user-owned original required for exact source recipe')
class PrimaryText960BuildTests(PrimaryTextBuildFixture, unittest.TestCase):
    resolution = '1280x960'


@unittest.skipUnless(ORIGINAL.is_file(), 'user-owned original required for exact source recipe')
class PrimaryText1080BuildTests(PrimaryTextBuildFixture, unittest.TestCase):
    resolution = '1920x1080'


@unittest.skipUnless(ORIGINAL.is_file(), 'user-owned original required for exact source recipe')
class PrimaryText802BuildTests(PrimaryTextBuildFixture, unittest.TestCase):
    resolution = '802x602'


class PrimaryTextBoundaryTests(unittest.TestCase):
    def test_unknown_original_rejected_before_any_predecessor_work(self):
        with patch.object(builder.primary, 'build_candidate') as build:
            with self.assertRaises(ValueError): builder.build_candidate(b'unknown', '1024x768')
            build.assert_not_called()

    def test_absolute_and_repository_boundaries_before_input_or_build(self):
        with tempfile.TemporaryDirectory(prefix='primary-text-output-boundary-') as folder:
            allowed = Path(folder).resolve(); checkout = allowed / 'repo'; checkout.mkdir()
            original_cwd = Path.cwd(); resolve = Path.resolve
            def map_allowed(path, *args, **kwargs):
                if str(path).replace('\\', '/') == 'C:/ClashTests': return allowed
                return resolve(path, *args, **kwargs)
            try:
                os.chdir(checkout)
                with patch.object(builder, 'ROOT', checkout), patch.object(Path, 'resolve', map_allowed):
                    for output in ('candidate.exe', str(checkout / 'candidate.exe'), str(allowed / 'a.bin')):
                        with (self.subTest(output=output), patch.object(builder, 'build_candidate') as build,
                              redirect_stderr(io.StringIO()), self.assertRaises(SystemExit)):
                            builder.main(['--original', 'absent-original.exe', '--resolution', '1024x768', '--output', output])
                        build.assert_not_called()
                        with self.assertRaises(ValueError): builder.write_candidate(Path('absent-original.exe'), Path(output), '1024x768')
                    self.assertEqual(builder.checked_output_path(allowed / 'candidate.exe'), allowed / 'candidate.exe')
                    with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                        builder.main(['--original', 'absent-original.exe', '--resolution', '1024x768',
                                      '--preflight', '--output', str(allowed / 'candidate.exe')])
            finally:
                os.chdir(original_cwd)

    def test_existing_three_part_bundle_never_overwrites(self):
        with tempfile.TemporaryDirectory(prefix='primary-text-collision-') as folder:
            allowed = Path(folder).resolve(); resolve = Path.resolve
            def map_allowed(path, *args, **kwargs):
                if str(path).replace('\\', '/') == 'C:/ClashTests': return allowed
                return resolve(path, *args, **kwargs)
            for index, suffix in enumerate(('.exe', '.candidate.json', '.cdb')):
                target = allowed / f'candidate{index}.exe'; occupied = target.with_suffix(suffix)
                occupied.write_bytes(b'keep original artifact')
                with patch.object(Path, 'resolve', map_allowed), patch.object(builder, 'build_candidate') as build:
                    with self.assertRaises(FileExistsError): builder.write_candidate(Path('absent-original.exe'), target, '1024x768')
                    build.assert_not_called()
                self.assertEqual(occupied.read_bytes(), b'keep original artifact')


class PrimaryTextProbeTests(unittest.TestCase):
    def setUp(self):
        base = bytearray(synthetic_primary()); view = pe.inspect_pe(bytes(base))
        self.format_va = 0x401180
        offset = view.file_offset(self.format_va - view.image_base, 3)
        base[offset:offset + 3] = b'%d\0'; self.base = bytes(base)
        args = format_arguments(self.base)
        result = builder.extension._extend_verified_image(self.base, **args)
        self.image = result.image
        self.metadata = dict(result.metadata, resolution='1024x768')
        self.bundle = SimpleNamespace(hook_sites=args['hooks'])
        marker = (f'MPRIMARY_CONTRACT_PASS stage={builder.primary.STAGE} resolution=1024x768 '
                  f'candidate_sha256={builder.sha(self.base)} revision={builder.primary.REVISION}')
        spans = [(view.image_base, self.base[:view.headers_size]),
                 (args['hooks'][0].va, args['hooks'][0].old), (self.format_va, b'%d\0')]
        bss = next(section for section in view.sections if not section.raw_offset and section.raw_size)
        spans.append((view.image_base + bss.rva + 8, bytes(12)))
        lines = [line.replace('MCANVAS_CONTRACT_FAIL', 'MPRIMARY_CONTRACT_FAIL')
                 for line in builder._checked_lines(spans)]
        lines += ['.echo ' + marker,
                  f'.echo PTILE_CONTRACT_PASS stage={builder.primary.STAGE} resolution=1024x768 candidate_sha256={builder.sha(self.base)}',
                  '.echo MPRIMARY_SCOPE owned_modal_primary primary_composition_proven=false manual_input_proof=false promotion_ready=false']
        self.probe = '\n'.join(lines) + '\n'
        self.context = dict(probe_sha256=builder.sha(self.probe.encode()), probe_contract=dict(primary_marker=marker))
        self.addCleanup(patch.stopall)
        patch.object(builder.text, 'NATIVE_SPANS', ((args['hooks'][0].va, 5, 'fixture'),)).start()
        patch.object(builder.text, 'TEXT_FORMAT', self.format_va).start()

    def make(self, **changes):
        args = dict(base=self.base, candidate=self.image, context=self.context,
                    old_probe=self.probe, bundle=self.bundle, metadata=self.metadata)
        return builder.make_probe(**(args | changes))

    def test_inherited_checks_rebind_only_declared_changes(self):
        probe, marker = self.make()
        memory, _, _, _ = independent_image(self.image)
        for va, size, expected in loaded_checks(probe):
            self.assertEqual(int.from_bytes(memory[va - 0x400000:va - 0x400000 + size], 'little'), expected)
        self.assertIn('.echo ' + marker, probe)
        self.assertNotIn('.echo MPRIMARY_CONTRACT_PASS', probe)

    def test_changed_probe_hash_and_self_consistent_wrong_predicate_rejected(self):
        changed = builder.PREDICATE.sub(lambda match: match.group().replace(' != ', ' != f'), self.probe, count=1)
        with self.assertRaisesRegex(ValueError, 'probe hash'): self.make(old_probe=changed)
        context = dict(self.context, probe_sha256=builder.sha(changed.encode()))
        with self.assertRaisesRegex(ValueError, 'predicate differs'): self.make(old_probe=changed, context=context)

    def test_changed_hook_without_declared_edit_rejected(self):
        metadata = dict(self.metadata, edits=self.metadata['edits'][1:])
        with self.assertRaisesRegex(ValueError, 'outside declared edits'): self.make(metadata=metadata)

    def test_missing_scope_and_contract_marker_rejected(self):
        for marker in ('MPRIMARY_SCOPE', 'MPRIMARY_CONTRACT_PASS'):
            changed = '\n'.join(line for line in self.probe.splitlines() if marker not in line) + '\n'
            context = dict(self.context, probe_sha256=builder.sha(changed.encode()))
            with self.subTest(marker=marker), self.assertRaisesRegex(ValueError, 'marker required'):
                self.make(old_probe=changed, context=context)


if __name__ == '__main__': unittest.main(verbosity=2)
