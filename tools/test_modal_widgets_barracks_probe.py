"""Offline widget probe assembly fixtures; no game, debugger or capture.

Pure cases explicitly mock only candidate admission and VA-to-fixture mapping.
Native byte checks, relocation checks and inherited command assembly still run.
An optional existing external widget bundle exercises real admission once.
"""
from __future__ import annotations

import copy
from dataclasses import replace
import os
from pathlib import Path
import re
import struct
import tempfile
import unittest
from unittest.mock import patch

import modal_widgets_barracks_probe as probe


def native_bytes():
    original = bytearray(0x300000)
    selected = probe.primary.ROUTES['barracks']
    spans = dict(probe.primary.COMMON)
    for route in (probe.primary.ROUTES['castle_overview'], selected):
        if route.name != 'castle_overview':
            spans[route.entry_va] = route.entry_bytes
        spans[route.present_call_va] = (b'\xe8' + struct.pack('<i', probe.primary.PRESENT-route.stop_va)).hex()
        spans[route.stop_va] = route.return_bytes
        if route.branch_va is not None:
            spans[route.branch_va] = (b'\xb9' + struct.pack('<I', route.entry_va)).hex()
    spans.update(probe.primary._native_spans(selected))
    for va, value in spans.items():
        raw = bytes.fromhex(value); at = va-probe.primary.IMAGE_BASE
        original[at:at+len(raw)] = raw
    candidate = bytearray(original)
    primary = dict(stage='synthetic-primary-stage', recipe_revision='synthetic-primary-v1',
        candidate_sha256='1'*64, code_va=0x680000,
        primary_entry_vas={'full_blit': 0x680010, 'full.fallback': 0x680080}, relocations=[])
    for va, target, purpose in (
        (0x680100, 0x4E9920, 'original HD blitter on physical mirror'),
        (0x680200, 0x460F90, 'native cursor remove before full copy'),
        (0x680300, 0x4E9920, 'original HD blitter on physical mirror'),
        (0x680400, 0x460EA0, 'native cursor capture and redraw after full copy')):
        at = va-probe.primary.IMAGE_BASE
        candidate[at:at+5] = b'\xe8' + struct.pack('<i', target-va-5)
        primary['relocations'].append(dict(purpose=purpose, kind='rel32', target=target,
                                          offset=va-primary['code_va']+1))
    for va, raw in ((0x680105, b'\x58\xc3'), (0x680405, b'\x61\x9d\xc3'), (0x432F9E, b'\xff\x56\x34')):
        at = va-probe.primary.IMAGE_BASE; candidate[at:at+len(raw)] = raw
    return bytes(original), bytes(candidate), primary


def synthetic_read(image, va, size):
    """Flat fixture address map, explicitly not a PE loader or real candidate."""
    offset = va-probe.primary.IMAGE_BASE
    if not 0 <= offset <= len(image)-size:
        raise ValueError('synthetic fixture address outside map')
    return offset, image[offset:offset+size]


class AssemblyTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='clash-widget-probe-fixture-')
        self.addCleanup(temporary.cleanup)
        self.folder = Path(temporary.name).resolve()
        self.original, self.candidate, ancestor = native_bytes()
        source_hashes = {name: probe.sha((probe.ROOT/name).read_bytes())
                         for name in probe.context_reader.RECIPE_SOURCE_PATHS}
        owner = dict(state_va=0x596000, modal_state_offsets=dict(probe.primary.canvas.STATE),
            modal_entry_vas={'is_active': 0x576100}, modal_native_canvas_revision='synthetic-canvas-v1',
            modal_observer_vas={'root_after_replayed_pushes': 0x5767B0, 'overview_after_native_draw': 0x5767E0})
        complete = dict(stage='synthetic-complete-stage', recipe_revision='synthetic-complete-v1', candidate_sha256='4'*64)
        slots = dict(stage='synthetic-slots-stage', recipe_revision='synthetic-slots-v1', candidate_sha256='2'*64,
                     slot_entry_vas={'after_dirty_copy': 0x5F0100}, base_candidate=complete)
        text = dict(stage='synthetic-text-stage', recipe_revision='synthetic-text-v1', candidate_sha256='3'*64)
        self.context = dict(stage=probe.STAGE, recipe_revision=probe.REVISION, resolution='1024x768',
            original_sha256=probe.sha(self.original), candidate_sha256=probe.sha(self.candidate),
            manifest=dict(source_hashes=source_hashes, widget_entry_vas={'single': 0x690000, 'list': 0x690100}),
            manifest_path=str(self.folder/'synthetic.candidate.json'), manifest_sha256='5'*64,
            manifest_canonical_sha256='6'*64, source_hashes=source_hashes,
            context_source_sha256=probe.sha(Path(probe.context_reader.__file__).read_bytes()),
            authentication_source_hashes=dict(probe.context_reader.AUTHENTICATION_SOURCES),
            text_context=text, primary_context=ancestor, slots_context=slots, owner_context=owner)
        self.refresh_extra()
        self.read = patch.object(probe.primary, '_read', side_effect=synthetic_read).start()
        self.addCleanup(patch.stopall)
        self.auth = patch.object(probe.context_reader, 'load_context', side_effect=lambda *args: copy.deepcopy(self.context)).start()

    def refresh_extra(self):
        context = self.context; digest = context['candidate_sha256']; resolution = context['resolution']
        context['probe'] = (f'.echo PTILE_CONTRACT_PASS stage={probe.STAGE} resolution={resolution} candidate_sha256={digest}\n'
            f'.echo MWIDGETS_CONTRACT_PASS stage={probe.STAGE} resolution={resolution} candidate_sha256={digest} revision={probe.REVISION}\n'
            '.echo MWIDGETS_SCOPE owned_modal_widget_bounds primary_composition_proven=false manual_input_proof=false promotion_ready=false\n')
        context['probe_sha256'] = probe.sha(context['probe'].encode())

    def build(self, **changes):
        arguments = dict(candidate_sha256=probe.sha(self.candidate), stage=probe.STAGE,
            resolution=self.context['resolution'], candidate_manifest=Path(self.context['manifest_path']))
        arguments.update(changes)
        return probe.build_screen_probe(self.original, self.candidate, **arguments)

    def test_all_six_geometries_keep_actual_identity_and_one_authentication(self):
        for resolution in probe.context_reader.RESOLUTIONS:
            with self.subTest(resolution=resolution):
                self.context['resolution'] = resolution; self.refresh_extra(); self.auth.reset_mock()
                packet = self.build()
                self.auth.assert_called_once_with(self.original, self.candidate, Path(self.context['manifest_path']))
                self.assertEqual(packet['schema'], probe.SCHEMA)
                self.assertEqual(packet['protocol_revision'], probe.PROTOCOL)
                self.assertEqual(packet['recipe_revision'], probe.REVISION)
                self.assertEqual(len(packet['source_sha256']), 36)
                self.assertEqual(packet['authentication_source_hashes'], probe.context_reader.AUTHENTICATION_SOURCES)
                self.assertEqual(packet['canonical_extra_sha256'], self.context['probe_sha256'])
                self.assertEqual(packet['candidate_extra'], self.context['probe'])
                self.assertIn('MWIDGETS_CONTRACT_PASS', packet['compiled_probe'])
                self.assertIn('protocol='+probe.PROTOCOL+' runtime_acceptance=0', packet['compiled_probe'])
                self.assertEqual(packet['compiled_probe_sha256'], probe.sha(packet['compiled_probe'].encode('ascii')))
                self.assertEqual(packet['compiled_probe_format'], dict(encoding='ascii', line_endings='LF',
                    hash_scope='prepared_text_bytes', runtime_command_file=False))
                self.assertNotIn('\r', packet['compiled_probe'])
                self.assertFalse(re.search(r'__[A-Z0-9_]+__', packet['compiled_probe']))
                self.assertEqual(len(packet['occupied_breakpoints']), len(set(packet['occupied_breakpoints'].values())))
                self.assertTrue(all(len(line.encode('ascii')) < 4096 for line in packet['compiled_probe'].splitlines()))
                for key in ('runtime_ready', 'runtime_accepted', 'compiled_probe_complete_for_runtime',
                            'primary_composition_proven', 'manual_input_proof', 'promotion_ready', 'availability_mutated'):
                    self.assertIs(packet[key], False)
                self.assertEqual(packet['pending_integrations'], probe.PENDING)
                self.assertNotIn('110', packet['occupied_breakpoints']); self.assertNotIn('111', packet['occupied_breakpoints'])

    def test_genuine_ancestor_addresses_and_identities_are_not_widget_relabels(self):
        packet = self.build()
        for name in ('text_context', 'primary_context', 'slots_context'):
            self.assertEqual(packet['ancestor_identities'][name]['candidate_sha256'], self.context[name]['candidate_sha256'])
            self.assertNotEqual(packet['ancestor_identities'][name]['stage'], probe.STAGE)
        self.assertEqual(packet['ancestor_identities']['complete_context'], self.context['slots_context']['base_candidate'])
        self.assertEqual(packet['canvas_state_va'], self.context['owner_context']['state_va'])
        self.assertEqual(packet['primary_entry_vas'], self.context['primary_context']['primary_entry_vas'])
        self.assertEqual(packet['primary_observers']['publish_call_direct'], 0x680100)
        self.assertEqual(packet['widget_entry_vas'], self.context['manifest']['widget_entry_vas'])

    def test_route_is_exact_pure_existing_flags_assembly_for_all_castles(self):
        for index in range(4):
            packet = self.build(castle_index=index)
            metadata = dict(self.context['owner_context'], slots_metadata=self.context['slots_context'],
                primary_metadata=self.context['primary_context'], primary_observers=packet['primary_observers'])
            handoff, commands = probe.primary._commands(probe.primary.ROUTES['barracks'], 1024, 768, index, 'existing_flags', metadata)
            self.assertEqual(packet['handoff_action'], handoff)
            self.assertEqual(packet['breakpoint_commands'], {str(k): dict(va=v[0], body=v[1]) for k, v in commands.items()})
            self.assertTrue(packet['forced_native_dispatch']); self.assertTrue(packet['forced_gate_result'])
            self.assertFalse(packet['forced_os_input']); self.assertFalse(packet['availability_mutated'])
            self.assertNotIn('MCAP_CONSTRUCT_ALL', packet['compiled_probe'])

    def test_public_arguments_fail_before_candidate_rebuild(self):
        invalid = [dict(stage='primary'), dict(resolution='3840x2160'), dict(route='school'),
            dict(availability='construct_all'), dict(castle_index=True), dict(castle_index=-1),
            dict(castle_index=4), dict(minimap_viewport=False), dict(candidate_sha256='F'*64),
            dict(candidate_sha256='0'*64)]
        for changes in invalid:
            with self.subTest(changes=changes), self.assertRaises(ValueError): self.build(**changes)
        self.auth.assert_not_called()

    def test_context_stage_resolution_revision_and_sources_fail_closed(self):
        for key, value in (('stage', 'primary'), ('recipe_revision', 'different'), ('resolution', '800x600'),
                           ('candidate_sha256', '0'*64)):
            with self.subTest(field=key), patch.dict(self.context, {key: value}), self.assertRaises(ValueError):
                self.build(resolution='1024x768')
        self.context['source_hashes'] = dict(self.context['source_hashes']); self.context['source_hashes'].pop(next(iter(self.context['source_hashes'])))
        with self.assertRaisesRegex(ValueError, 'complete widget recipe sources'): self.build()

    def test_widget_startup_rejects_wrong_missing_duplicate_or_old_markers(self):
        original = self.context['probe']
        for changed in (original.replace('MWIDGETS_CONTRACT_PASS', 'MPRIMARYTEXT_CONTRACT_PASS'),
                        original.replace(probe.REVISION, 'different'), original+original,
                        original.replace('.echo PTILE_CONTRACT_PASS', '.echo IGNORED'),
                        original+'.echo MPRIMARY_CONTRACT_PASS old\n'):
            with self.subTest(changed=changed[-60:]):
                self.context.update(probe=changed, probe_sha256=probe.sha(changed.encode()))
                with self.assertRaises(ValueError): self.build()
        self.context.update(probe=original, probe_sha256='0'*64)
        with self.assertRaises(ValueError): self.build()

    def test_rendered_template_override_must_be_exact(self):
        packet = self.build()
        self.assertEqual(self.build(rendered_probe=packet['map_probe_template'])['compiled_probe'], packet['compiled_probe'])
        for changed in (packet['map_probe_template']+'\n.echo extra\n', 3):
            with self.assertRaisesRegex(ValueError, 'unchanged canonical widget template'): self.build(rendered_probe=changed)

    def test_original_native_instruction_mutation_fails(self):
        image = bytearray(self.original); image[0x422028-probe.primary.IMAGE_BASE] ^= 1; self.original = bytes(image)
        with self.assertRaisesRegex(ValueError, 'native source span differs'): self.build()

    def test_candidate_native_instruction_mutation_fails_despite_mocked_admission(self):
        image = bytearray(self.candidate); image[0x422028-probe.primary.IMAGE_BASE] ^= 1; self.candidate = bytes(image)
        self.context['candidate_sha256'] = probe.sha(self.candidate); self.refresh_extra()
        with self.assertRaisesRegex(ValueError, 'widget native observation span changed'): self.build()

    def test_candidate_call_return_and_placeholder_bytes_are_independently_checked(self):
        original = self.candidate
        for va in (0x680100, 0x680200, 0x680300, 0x680400, 0x680105, 0x680405, 0x432F9E):
            with self.subTest(va=hex(va)):
                image = bytearray(original); image[va-probe.primary.IMAGE_BASE] ^= 1; self.candidate = bytes(image)
                self.context['candidate_sha256'] = probe.sha(self.candidate); self.refresh_extra()
                with self.assertRaisesRegex(ValueError, 'primary .* differ'): self.build()

    def test_relocation_identity_and_colliding_observer_sites_are_rejected(self):
        ancestor = self.context['primary_context']
        with patch.dict(ancestor['relocations'][0], target=0x460F90), self.assertRaisesRegex(ValueError, 'relocation target'): self.build()
        with patch.dict(ancestor['primary_entry_vas'], full_blit=0x432F9E), self.assertRaisesRegex(ValueError, 'collides'): self.build()

    def test_frozen_helper_source_drift_is_rejected_before_rebuild(self):
        with patch.dict(probe.PINS, {'tools/modal_primary_barracks_probe.py': '0'*64}), self.assertRaisesRegex(ValueError, 'frozen widget observation helper'):
            self.build()
        self.auth.assert_not_called()

    def test_geometry_wrapper_source_drift_is_rejected_before_and_after_admission(self):
        self.assertIn('patch_clash95_hd.py', probe.PINS)
        real = probe.context_reader._snapshot
        for after_admission in (False, True):
            changed = not after_admission
            def snapshot(path):
                row = real(path)
                return replace(row, data=row.data+b'\n# altered geometry wrapper\n') if changed and Path(path) == probe.ROOT/'patch_clash95_hd.py' else row
            def admit(*args):
                nonlocal changed
                changed = True
                return copy.deepcopy(self.context)
            self.auth.reset_mock(); self.auth.side_effect = admit
            with self.subTest(after_admission=after_admission), patch.object(probe.context_reader, '_snapshot', side_effect=snapshot):
                with self.assertRaisesRegex(ValueError, 'frozen widget observation helper changed: patch_clash95_hd.py'): self.build()
            self.assertEqual(self.auth.call_count, int(after_admission))

    def test_preparation_source_drift_during_admission_is_rejected(self):
        real = probe.context_reader._snapshot; changed = False
        def snapshot(path):
            row = real(path)
            return replace(row, data=row.data+b'\n') if changed and Path(path).name == Path(probe.__file__).name else row
        def admit(*args):
            nonlocal changed
            changed = True
            return copy.deepcopy(self.context)
        self.auth.side_effect = admit
        with patch.object(probe.context_reader, '_snapshot', side_effect=snapshot), self.assertRaisesRegex(ValueError, 'source changed during preparation'):
            self.build()

    def test_complete_packet_regeneration_authenticates_once_and_rejects_mutations(self):
        packet = self.build(); self.auth.reset_mock()
        self.assertEqual(probe.regenerate_packet(self.original, self.candidate, packet), packet)
        self.auth.assert_called_once()
        for field, value in (('runtime_accepted', True), ('prepared', 1), ('compiled_probe', 'g\n'),
                             ('canonical_extra_sha256', '0'*64), ('authentication_source_hashes', {}),
                             ('compiled_probe_format', {}),
                             ('occupied_breakpoints', {}), ('pending_integrations', [])):
            changed = copy.deepcopy(packet); changed[field] = value; self.auth.reset_mock()
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'complete authenticated regeneration'):
                probe.regenerate_packet(self.original, self.candidate, changed)
            self.auth.assert_called_once()

    def test_checkpoint_scripts_preserve_four_native_pauses_without_admitting_capture(self):
        packet = self.build()
        self.assertEqual([row['name'] for row in packet['checkpoints']],
                         ['full-published', 'placeholder-before', 'placeholder-after', 'final-ready'])
        for row in packet['checkpoints']:
            script = probe.checkpoint_script(packet, row['name'])
            self.assertEqual(script, probe.primary.checkpoint_script(packet, row['name']))
            self.assertIn('MPCAP_CHECKPOINT name='+row['name'], script)
            self.assertNotIn('MPCAP_HOST_READY', script)
        old = dict(packet, stage='primary')
        with self.assertRaises(ValueError): probe.checkpoint_script(old, 'final-ready')
        malformed = copy.deepcopy(packet); malformed['checkpoints'][0]['index'] = False
        with self.assertRaises(ValueError): probe.checkpoint_script(malformed, 'full-published')

    def test_compile_rejects_token_boundaries_and_oversized_lines(self):
        packet = self.build(); harness = (probe.ROOT/'scripts/cdb/run_cdb_surface_dump.ps1').read_bytes()
        geometry = {'load_mouse': (300, 200)}
        for template in (packet['map_probe_template'].replace('bc *\n', ''),
                         packet['map_probe_template']+'\ng\n',
                         packet['map_probe_template'].replace(probe.primary.DUMP_TOKEN, '__UNKNOWN__'),
                         packet['map_probe_template'].replace('bc *\n', 'bc *\n.echo '+'x'*4096+'\n')):
            with self.assertRaises(ValueError): probe._compile(dict(packet, map_probe_template=template), geometry, harness)


class BreakpointTests(unittest.TestCase):
    def test_expanded_implicit_ids_follow_real_declaration_order(self):
        result = probe._breakpoints('bp2 00401000 "gc"\nbp 00402000 "gc"\nbp 00403000 "gc"\nbp 00404000 "gc"\n')
        self.assertEqual(result, {'0': 0x402000, '1': 0x403000, '2': 0x401000, '3': 0x404000})

    def test_expanded_address_id_range_and_grammar_conflicts_fail(self):
        for command in ('bp 00401000 "gc"\nbp0 00402000 "gc"',
                        'bp1 00401000 "gc"\nbp2 00401000 "gc"',
                        'bp1000 00401000 "gc"', 'bp 00000000 "gc"', 'bp /w condition 00401000 "gc"'):
            with self.subTest(command=command), self.assertRaises(ValueError): probe._breakpoints(command)


class ActualBundleTests(unittest.TestCase):
    @unittest.skipUnless(os.environ.get('CLASH_WIDGET_BARRACKS_MANIFEST'), 'opt-in existing external widget bundle required')
    def test_existing_bundle_authenticates_and_compiles_actual_widget_candidate_once(self):
        path = Path(os.environ['CLASH_WIDGET_BARRACKS_MANIFEST']).resolve()
        raw = path.read_bytes(); manifest = probe.context_reader.parse_manifest(raw)
        candidate_path = path.with_name(path.name.removesuffix('.candidate.json')+'.exe')
        original = Path('C:/Clash/clash95.exe').read_bytes(); candidate = candidate_path.read_bytes()
        reader = probe.context_reader.load_context
        with patch.object(probe.context_reader, 'load_context', wraps=reader) as auth:
            packet = probe.build_screen_probe(original, candidate, candidate_sha256=probe.sha(candidate), stage=probe.STAGE,
                resolution=manifest['resolution'], candidate_manifest=path)
        auth.assert_called_once()
        self.assertEqual(packet['candidate_manifest']['sha256'], probe.sha(raw))
        self.assertEqual(packet['source_sha256'], manifest['source_hashes'])
        self.assertFalse(packet['runtime_accepted'])
        self.assertEqual(len(packet['checkpoints']), 4)
        self.assertIn('MWIDGETS_CONTRACT_PASS stage='+probe.STAGE, packet['compiled_probe'])
        self.assertEqual(probe.sha(Path('C:/Clash/clash95.exe').read_bytes()), probe.context_reader.ORIGINAL_SHA256)
        output = os.environ.get('CLASH_WIDGET_BARRACKS_PACKET')
        if output:
            artifact = Path(output).resolve()
            self.assertFalse(artifact.is_relative_to(probe.ROOT), 'actual preparation artifacts must remain external')
            with artifact.open('xb') as stream:
                stream.write((probe.canonical(packet)+'\n').encode('utf-8'))
        print('ACTUAL_WIDGET_BARRACKS_PREPARATION candidate_sha256='+packet['candidate_sha256']+
              ' manifest_sha256='+packet['candidate_manifest']['sha256']+' resolution='+packet['resolution']+
              ' compiled_probe_sha256='+packet['compiled_probe_sha256']+' runtime_accepted=false')


if __name__ == '__main__':
    unittest.main()
