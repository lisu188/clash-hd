"""Independent synthetic PE checks and opt-in original-backed widget builds."""
from dataclasses import replace
import copy
import os
from pathlib import Path
import re
import struct
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import build_framed_modal_widgets_candidate as builder
from src.patcher import pe_extension as pe
from src.patcher import pe_modal_primary_text_extension as text_format
from test_pe_modal_primary_text_extension import synthetic_primary, arguments as text_arguments
from test_pe_extension import independent_image, rebase
from test_pe_modal_extension import independent_section_adjacency, native_image_section
from test_build_framed_modal_candidate import replay

ORIGINAL = Path('C:/Clash/clash95.exe')


def synthetic_text():
    base = synthetic_primary()
    image = bytearray(text_format._extend_verified_image(base, **text_arguments(base)).image)
    view = pe.inspect_pe(bytes(image))
    for rva, prefix in ((0x1120, b'\x81\x38'), (0x1130, b'\x81\x3b')):
        offset = view.file_offset(rva, 6)
        image[offset:offset + 6] = prefix + struct.pack('<I', 1024)
    return bytes(image)


def fixture(base=None):
    base = synthetic_text() if base is None else base
    view = pe.inspect_pe(base); code_va, _ = builder.allocation_layout(base)
    comparisons = {name: prefix + struct.pack('<I', 1024) for name, prefix in
                   (('single', b'\x81\x38'), ('list', b'\x81\x3b'))}
    state = view.image_base + next(s.rva for s in view.sections if s.name.rstrip(b'\0') == b'.hdstate')
    bundle = builder.widgets._emit_guards(base_va=code_va, state_va=state, owner_va=0x401100,
                                         width=1024, height=768, comparisons=comparisons)
    code = bytearray(bundle.code); relocations = []
    for row in bundle.relocations:
        if row.target == builder.widgets.modal.RENDER:
            row = replace(row, target=0x402008)
            struct.pack_into('<I', code, row.offset, row.target)
        relocations.append(row)
    hooks = tuple(pe.HookPatch(view.file_offset(rva, 6), rva, view.image_base + rva, comparisons[name],
                    b'\xe8' + struct.pack('<i', bundle.entries[name] - view.image_base - rva - 5) + b'\x90',
                    'synthetic.' + name, (pe.CodeRelocation(1, 'rel32', bundle.entries[name], 'synthetic widget entry'),))
                  for name, rva in (('single', 0x1120), ('list', 0x1130)))
    bundle = replace(bundle, code=bytes(code), relocations=tuple(relocations), hook_sites=hooks,
                     source_contract={'native_spans': [dict(va=h.va - 2, size=12) for h in hooks]})
    return base, bundle, dict(code=bundle.code, code_va=code_va, relocations=bundle.relocations,
                             hooks=hooks, binding={'fixture': 'synthetic PE only', 'resolution': '1024x768'})


def probe_fixture(base, bundle):
    image = pe.inspect_pe(base)
    spans = [(0x400000, base[:0x400])]
    for section in image.sections:
        if section.raw_size and section.raw_offset:
            spans.append((image.image_base + section.rva, base[section.raw_offset:section.raw_offset + section.raw_size]))
    marker = f'MPRIMARYTEXT_CONTRACT_PASS stage={builder.text.STAGE} resolution=1024x768 candidate_sha256={builder.sha(base)} revision=owned_modal_primary_text_v1'
    probe = '\n'.join(builder._checked_lines(spans)).replace('MCANVAS_CONTRACT_FAIL', 'MPRIMARYTEXT_CONTRACT_FAIL') + '\n'
    probe += '.echo ' + marker + '\n'
    probe += f'.echo PTILE_CONTRACT_PASS stage={builder.text.STAGE} resolution=1024x768 candidate_sha256={builder.sha(base)}\n'
    probe += '.echo MPRIMARYTEXT_SCOPE owned_modal_primary_text primary_composition_proven=false manual_input_proof=false promotion_ready=false\n'
    return probe, dict(probe_sha256=builder.sha(probe.encode()), probe_contract={'text_marker': marker})


def checks(probe):
    rows = []
    for line in probe.splitlines():
        if '_CONTRACT_FAIL' not in line: continue
        residual = builder.text.PREDICATE.sub('READ', line)
        if not re.fullmatch(r'\.if \(READ(?: \| READ)*\) \{ \.echo (?:PTILE|ARMY|MPRIMARY|MPRIMARYTEXT|MWIDGETS)_CONTRACT_FAIL; q \}', residual):
            raise AssertionError('unexpected loaded-byte grammar: ' + residual[:100])
        rows.extend((int(va, 16), 2 if kind == 'wo' else 1, int(value, 16))
                    for kind, va, value in builder.text.PREDICATE.findall(line))
    if not rows: raise AssertionError('no loaded-byte checks')
    return rows


class WidgetFormatTests(unittest.TestCase):
    def test_replay_and_independent_rebase_preserve_every_old_header_and_relocation(self):
        base, bundle, arguments = fixture(); before = pe.inspect_pe(base)
        result = builder._extend_verified_image(base, **arguments)
        after = pe.inspect_pe(result.image)
        self.assertEqual(replay(base, result.metadata['edits']), result.image)
        self.assertEqual(after.sections[:14], before.sections)
        self.assertEqual(len(after.sections), 15)
        self.assertEqual((after.sections[-1].name.rstrip(b'\0'), after.sections[-1].header_offset,
                          after.sections[-1].characteristics), (b'.hdwgt', 0x398, pe.RX_CODE))
        self.assertEqual(after.image_size - before.image_size, 0x20000)
        self.assertEqual(result.image[0x3C0:0x400], base[0x3C0:0x400])
        self.assertTrue(all(r['rva'] == r['expected_rva'] for r in independent_section_adjacency(result.image)))
        changed = {i for e in result.edits for i in range(e.offset, e.offset + len(e.old))}
        self.assertTrue(all(b == result.image[i] for i, b in enumerate(base) if i not in changed))
        old_memory, _, old_fields, _ = independent_image(base)
        memory, sections, fields, _ = independent_image(result.image)
        expected = old_fields + [bundle.base_va - before.image_base + r.offset for r in bundle.relocations if r.kind == 'abs32']
        self.assertEqual(fields, sorted(expected)); self.assertEqual(len(fields), len(set(fields)))
        self.assertEqual(result.metadata['new_highlow_count'], 8)
        for delta in (-0x100000, 0x2100000):
            moved = rebase(memory, fields, delta); old_moved = rebase(old_memory, old_fields, delta)
            for rva in old_fields: self.assertEqual(moved[rva:rva + 4], old_moved[rva:rva + 4])
            for row in bundle.relocations:
                rva = bundle.base_va - before.image_base + row.offset
                if row.kind == 'abs32': self.assertEqual(struct.unpack_from('<I', moved, rva)[0], row.target + delta)
                else: self.assertEqual(moved[rva:rva + 4], memory[rva:rva + 4])
            for hook in bundle.hook_sites:
                self.assertEqual(hook.va + delta + 5 + struct.unpack_from('<i', moved, hook.rva + 1)[0],
                                 hook.relocations[0].target + delta)
        for key in ('installation_ready', 'runtime_executed', 'manual_input_proof', 'promotion_ready'):
            self.assertIs(result.metadata[key], False)

    def test_both_complete_cmp_hooks_old_bytes_and_exact_relocations_are_required(self):
        base, bundle, args = fixture(); first, second = args['hooks']
        changes = [dict(hooks=()), dict(hooks=(first,)), dict(hooks=(first, first)), dict(hooks=None),
                   dict(hooks=(replace(first, old=b'\0' * 6), second)),
                   dict(hooks=(replace(first, new=b'\xe9' + first.new[1:]), second)),
                   dict(hooks=(replace(first, new=first.new[:-1]), second)),
                   dict(hooks=(replace(first, old=None), second)),
                   dict(hooks=(replace(first, relocations=None), second)),
                   dict(hooks=(replace(first, relocations=(object(),)), second)),
                   dict(hooks=(replace(first, offset=first.offset + 1), second))]
        for field in ({'offset': True}, {'offset': 2}, {'target': 0x402008}, {'kind': 'abs32'}, {'target': True}):
            changes.append(dict(hooks=(replace(first, relocations=(replace(first.relocations[0], **field),)), second)))
        for change in changes:
            with self.subTest(change=repr(change)[:90]), self.assertRaises(ValueError):
                builder._extend_verified_image(base, **(args | change))

    def test_layout_permissions_reserved_header_and_code_fields_fail_closed(self):
        base, _, args = fixture(); image = pe.inspect_pe(base)
        for offset in (0x398, 0x3A0, 0x3BF):
            bad = bytearray(base); bad[offset] = 1
            with self.assertRaises(ValueError): builder.allocation_layout(bytes(bad))
        for section in image.sections[-7:]:
            bad = bytearray(base); struct.pack_into('<I', bad, section.header_offset + 36, section.characteristics ^ 0x80000000)
            with self.assertRaises(ValueError): builder.allocation_layout(bytes(bad))
        with self.assertRaises(ValueError): builder.allocation_layout(synthetic_primary())
        for change in (dict(code=b''), dict(code=bytearray(args['code'])), dict(code=b'\x90' * 4096),
                       dict(code_va=args['code_va'] + 4096), dict(relocations=None), dict(binding=None),
                       dict(relocations=(object(),)), dict(relocations=args['relocations'] * 2)):
            with self.subTest(change=change.keys()), self.assertRaises(ValueError):
                builder._extend_verified_image(base, **(args | change))
        for field in ({'offset': True}, {'offset': -1}, {'kind': 'HIGH'}, {'target': 0}, {'target': True}, {'purpose': ''}):
            rows = (replace(args['relocations'][0], **field),) + args['relocations'][1:]
            with self.subTest(field=field), self.assertRaises(ValueError):
                builder._extend_verified_image(base, **(args | {'relocations': rows}))
        bad = bytearray(args['code']); bad[args['relocations'][0].offset] ^= 1
        with self.assertRaisesRegex(ValueError, 'operand'): builder._extend_verified_image(base, **(args | {'code': bytes(bad)}))

    def test_loaded_probe_rebinds_only_declared_edits_and_covers_full_new_payload(self):
        base, bundle, args = fixture(); result = builder._extend_verified_image(base, **args)
        old_probe, context = probe_fixture(base, bundle)
        probe, marker = builder.make_probe(base, result.image, context, old_probe, bundle, result.metadata)
        memory, _, _, _ = independent_image(result.image)
        covered = set()
        for va, size, expected in checks(probe):
            self.assertEqual(int.from_bytes(memory[va - 0x400000:va - 0x400000 + size], 'little'), expected)
            covered.update(range(va, va + size))
        for va, size in ((bundle.base_va, result.metadata['code_raw_bytes']), (0x400398, 40), (0x40111E, 12), (0x40112E, 12)):
            self.assertTrue(set(range(va, va + size)) <= covered, hex(va))
        self.assertEqual(probe.splitlines().count('.echo ' + marker), 1)
        self.assertNotIn('.echo MPRIMARYTEXT_CONTRACT_PASS', probe)
        self.assertNotIn('.echo MPRIMARYTEXT_SCOPE', probe)
        self.assertIn(f'PTILE_CONTRACT_PASS stage={builder.STAGE}', probe)
        self.assertTrue(all(len(line.encode('ascii')) < 4096 for line in probe.splitlines()))
        with self.assertRaisesRegex(ValueError, 'exact predecessor probe'):
            builder.make_probe(base, result.image, context, old_probe + '\n', bundle, result.metadata)
        altered = bytearray(result.image); altered[pe.inspect_pe(result.image).file_offset(0x1150, 1)] ^= 1
        with self.assertRaisesRegex(ValueError, 'outside declared edits'):
            builder.make_probe(base, bytes(altered), context, old_probe, bundle, result.metadata)
        for bad in (old_probe.replace('.echo ' + context['probe_contract']['text_marker'], ''),
                    old_probe + '.echo ' + context['probe_contract']['text_marker'] + '\n'):
            changed = dict(context, probe_sha256=builder.sha(bad.encode()))
            with self.assertRaisesRegex(ValueError, 'startup/scope'):
                builder.make_probe(base, result.image, changed, bad, bundle, result.metadata)

    def test_public_builder_rejects_unknown_original_and_noncanonical_profiles(self):
        with patch.object(builder.widgets, '_verified_bundle') as emit:
            for resolution in ('1024x768', '900x700', '01024x0768'):
                with self.assertRaises(ValueError): builder.build_candidate(b'unknown original', resolution)
            emit.assert_not_called()

    def test_output_restrictions_and_existing_bundle_before_original_read(self):
        for value in ('candidate.exe', str(builder.ROOT / 'candidate.exe')):
            with patch.object(builder, 'build_candidate') as build, self.assertRaises(ValueError):
                builder.write_candidate(Path('absent-original'), Path(value), '1024x768')
            build.assert_not_called()
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / 'candidate.exe'
            for suffix in ('.exe', '.cdb', '.candidate.json'):
                occupied = target.with_suffix(suffix); occupied.write_bytes(b'existing')
                with patch.object(builder.text, 'checked_output_path', return_value=target), \
                     patch.object(builder, 'build_candidate') as build, self.assertRaises(FileExistsError):
                    builder.write_candidate(Path('absent-original'), target, '1024x768')
                build.assert_not_called(); self.assertEqual(occupied.read_bytes(), b'existing'); occupied.unlink()


@unittest.skipUnless(ORIGINAL.is_file() and os.environ.get('CLASH_WIDGET_RESOLUTION') in ('1024x768', '1920x1080'),
                     'pinned original and explicit widget profile required')
class WidgetOriginalBuildTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = ORIGINAL.read_bytes(); cls.resolution = os.environ['CLASH_WIDGET_RESOLUTION']
        cls.image, cls.metadata, cls.probe = builder.build_candidate(cls.original, cls.resolution)
        base = bytearray(cls.image)
        for edit in reversed(cls.metadata['edits']):
            old, new = bytes.fromhex(edit['old_hex']), bytes.fromhex(edit['new_hex'])
            if bytes(base[edit['offset']:edit['offset'] + len(new)]) != new: raise AssertionError('reverse edit mismatch')
            base[edit['offset']:edit['offset'] + len(new)] = old
        cls.base = bytes(base)
        print('Built exact widget candidate:', cls.resolution, cls.metadata['candidate_sha256'], flush=True)

    def test_exact_original_recipe_replay_bindings_and_two_real_dispatcher_hooks(self):
        context = self.metadata['base_candidate']; primary = context['base_candidate']; slots = primary['base_candidate']
        foundation = slots['base_candidate']
        image = builder.complete.apply_records(self.original, foundation['patch_records'], expected_base_sha256=builder.complete.BASE_SHA256)
        for ancestor in (slots, primary, context, self.metadata):
            self.assertEqual(builder.sha(image), ancestor['base_candidate_sha256'])
            image = replay(image, ancestor['edits'])
            self.assertEqual(builder.sha(image), ancestor['candidate_sha256'])
        self.assertEqual(image, self.image)
        self.assertEqual(self.metadata['source_hashes'],
                         {name: builder.sha((builder.ROOT / name).read_bytes()) for name in self.metadata['source_hashes']})
        self.assertEqual(tuple(h['va'] for h in self.metadata['hooks']), (0x419D63, 0x419D8C))
        self.assertEqual(len(self.metadata['hooks']), 2)
        self.assertEqual(context['stage'], builder.text.STAGE)
        self.assertEqual(self.metadata['stage'], builder.STAGE)
        for hook in self.metadata['hooks']:
            self.assertEqual(bytes.fromhex(hook['old_hex'])[2:], struct.pack('<I', int(self.resolution.split('x')[0])))
            self.assertEqual(bytes.fromhex(hook['new_hex'])[-1:], b'\x90')
        for key in ('runtime_executed', 'installation_ready', 'manual_input_proof', 'promotion_ready', 'primary_composition_proven'):
            self.assertIs(self.metadata[key], False)
        self.assertEqual(ORIGINAL.read_bytes(), self.original)

    def test_independent_rebase_native_section_admission_and_old_headers(self):
        memory, sections, fields, _ = independent_image(self.image)
        old_memory, old_sections, old_fields, _ = independent_image(self.base)
        self.assertEqual(len(sections), 15); self.assertEqual(sections[:14], old_sections)
        new_fields = [self.metadata['code_rva'] + row['offset'] for row in self.metadata['relocations'] if row['kind'] == 'abs32']
        self.assertEqual(fields, sorted(old_fields + new_fields))
        for delta in (-0x100000, 0x2100000):
            moved = rebase(memory, fields, delta); old_moved = rebase(old_memory, old_fields, delta)
            for rva in old_fields: self.assertEqual(moved[rva:rva + 4], old_moved[rva:rva + 4])
            for row in self.metadata['relocations']:
                rva = self.metadata['code_rva'] + row['offset']
                if row['kind'] == 'abs32': self.assertEqual(struct.unpack_from('<I', moved, rva)[0], row['target'] + delta)
                else: self.assertEqual(moved[rva:rva + 4], memory[rva:rva + 4])
        if os.name == 'nt':
            with tempfile.TemporaryDirectory(prefix='widget-loader-', dir='C:/ClashTests') as folder:
                path = Path(folder) / 'candidate.bin'; path.write_bytes(self.image)
                self.assertEqual(native_image_section(path), dict(accepted=True, error=0, view_mapped=False, process_started=False))

    def test_full_loaded_probe_and_original_adapter_instruction_core_match(self):
        memory, _, _, _ = independent_image(self.image); covered = set()
        for va, size, value in checks(self.probe):
            self.assertEqual(int.from_bytes(memory[va - 0x400000:va - 0x400000 + size], 'little'), value)
            covered.update(range(va, va + size))
        for va, size in ((0x419D60, 18), (0x419D80, 64), (0x400398, 40),
                         (self.metadata['modal_state_va'], 128), (self.metadata['code_va'], self.metadata['code_raw_bytes']),
                         (self.metadata['base_candidate']['code_va'], self.metadata['base_candidate']['code_raw_bytes'])):
            self.assertTrue(set(range(va, va + size)) <= covered, hex(va))
        width, height = map(int, self.resolution.split('x'))
        comparisons = {name: bytes.fromhex(hook['old_hex']) for name, hook in zip(('single', 'list'), self.metadata['hooks'])}
        bundle = builder.widgets._emit_guards(base_va=self.metadata['code_va'], state_va=self.metadata['modal_state_va'],
                    owner_va=self.metadata['modal_entry_vas']['is_active'], width=width, height=height, comparisons=comparisons)
        self.assertEqual(builder.sha(bundle.code), self.metadata['code_sha256'])
        self.assertEqual(bundle.entries, self.metadata['widget_entry_vas'])
        self.assertEqual(self.probe.splitlines().count('.echo ' + self.metadata['probe_contract']['widgets_marker']), 1)
        self.assertNotIn('.echo MPRIMARYTEXT_CONTRACT_PASS', self.probe)
        self.assertEqual(ORIGINAL.read_bytes(), self.original)


if __name__ == '__main__': unittest.main(verbosity=2)
