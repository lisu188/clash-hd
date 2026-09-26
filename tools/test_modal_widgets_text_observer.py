"""Synthetic widget quantity triplets; candidate admission and PE mapping are mocked.

The historical fixture's ABI/state mutations are copied with independent widget
identity and namespace. No original-game build, debugger, or runtime is used.
"""
import copy
from dataclasses import replace
import io
import json
import tempfile
from contextlib import redirect_stdout
import hashlib
from pathlib import Path
import re
import struct
import unittest
from unittest.mock import patch

import modal_widgets_text_observer as observer


SOURCE_ROWS = observer._source_snapshots()


def context(resolution='1024x768'):
    stage, revision = observer.STAGE, observer.REVISION
    loaded = '\n'.join('.echo '+row for row in observer._loaded(stage, resolution, 'a'*64))+'\n'
    sources = {name: observer.sha(SOURCE_ROWS[name].data) for name in observer.context_reader.RECIPE_SOURCE_PATHS}
    text = dict(stage=stage.removesuffix('-modalwidgets-validation')+'-modalprimarytext-validation',
                recipe_revision='owned_modal_primary_text_v1', resolution=resolution, candidate_sha256='1'*64)
    return dict(stage=stage, recipe_revision=revision, resolution=resolution,
                candidate_sha256='a'*64, original_sha256='c'*64, source_hashes=sources,
                authentication_source_hashes=dict(observer.context_reader.AUTHENTICATION_SOURCES),
                context_source_sha256=observer.sha(SOURCE_ROWS['tools/modal_widgets_context.py'].data),
                manifest_path='synthetic.candidate.json', manifest_sha256='e'*64, manifest_canonical_sha256='f'*64,
                manifest={'source_hashes': sources, 'base_candidate': copy.deepcopy(text), 'modal_state_va': 0x610000},
                text_context=text, owner_context={'state_va': 0x610000}, probe=loaded, probe_sha256=observer.sha(loaded.encode()))


def sites():
    return dict(adapter=0x600000, native=observer.text.TEXT_TARGET, return_va=observer.text.TEXT_RETURN,
                call_va=observer.text.TEXT_CALL, state_va=0x610000, byte_spans=[])


def packet(resolution='1024x768'):
    return observer._compose(context(resolution), sites(), SOURCE_ROWS, breakpoint_ids=observer.DEFAULT_IDS, occupied_breakpoints={})


def rows(prepared, quantity=250):
    width, height = map(int, prepared['binding']['resolution'].split('x'))
    value = {name: 0 for name in observer.FIELDS}
    value.update(tid=0x114, eip=sites()['adapter'], esp=0x1F0000, caller=observer.text.TEXT_RETURN,
                 eax=0x123456, ebx=0x345678, ecx=0x456789, edx=quantity & 0xFFFFFFFF,
                 esi=0x56789A, edi=0x6789AB, ebp=observer.canvas.PRIMARY, flags=0xED7,
                 state=sites()['state_va'], phase=1, fault=0, owner_tid=0x114, root_esp=0x1F0100,
                 physical=0x700000, native=0x710000, physical_pixels=0x1000000, native_pixels=0x1800000,
                 map=0x710000, render=observer.canvas.PRIMARY, native_width=640, native_height=480,
                 native_data=0x1800000, native_com=0, native_vtable=observer.canvas.MEMORY_VTABLE,
                 physical_width=width, physical_height=height, physical_data=0x1000000,
                 physical_com=0, physical_vtable=observer.canvas.MEMORY_VTABLE,
                 primary_width=width, primary_height=height, primary_vtable=observer.canvas.PRIMARY_VTABLE,
                 primary_depth=8, primary_backend=0x800000, primary_surface=0x900000)
    value.update((f'arg{i}', n) for i, n in enumerate(prepared['expected_original_args'] + [quantity & 0xFFFFFFFF]))
    native = dict(value, eip=observer.text.TEXT_TARGET)
    native.update((f'arg{i}', n) for i, n in enumerate(prepared['expected_translated_args']))
    returned = dict(native, eip=observer.text.TEXT_RETURN, esp=value['esp'] + 4, eax=0x123, flags=0x202)
    return [('ADAPTER', value), ('NATIVE', native), ('RETURN', returned)]


def event_line(event, values):
    return 'MWTEXT_EVENT event=' + event + ' ' + ' '.join(f'{key}={values[key]:08x}' for key in observer.FIELDS)


def trace(prepared, events=None):
    return '\n'.join(prepared['expected_loaded_records'] + [prepared['contract_line']] +
                     [event_line(name, value) for name, value in (rows(prepared) if events is None else events)]) + '\n'


class TextObserverTests(unittest.TestCase):
    def test_all_six_profiles_and_signed_values_preserve_bounded_scope(self):
        for resolution in observer.context_reader.RESOLUTIONS:
            prepared = packet(resolution)
            for quantity in (0, 250, -1, -2147483648, 2147483647):
                with self.subTest(resolution=resolution, quantity=quantity):
                    result = observer.evaluate_sequence(trace(prepared, rows(prepared, quantity)), prepared)
                    self.assertTrue(result['sequence_passed'], result['failures'])
                    self.assertEqual(result['signed_quantity'], quantity)
                    self.assertEqual(result['observed_event_count'], 3)
                    self.assertFalse(result['source_authenticated'])
                    self.assertFalse(result['text_call_observed'])
                    self.assertFalse(result['runtime_accepted'])
                    self.assertFalse(result['manual_input_proof'])
                    self.assertFalse(result['promotion_ready'])

    def test_fragment_is_disabled_read_only_dword_observation_with_declared_ids(self):
        prepared = packet()
        self.assertEqual(prepared['arm_command'], 'be 150 151 152')
        self.assertEqual(prepared['disarm_command'], 'bd 150 151 152')
        commands = prepared['breakpoint_commands']
        self.assertEqual([commands[str(n)]['event'] for n in observer.DEFAULT_IDS], list(observer.EVENTS))
        self.assertIn('dwo(@esp) == 00432c6b', commands['151']['body'])
        self.assertIn('dwo(@esp+4)', commands['150']['body'])
        self.assertIn('dwo(@esp+0)', commands['152']['body'])
        self.assertIn('dwo(@esp+18)', commands['150']['body'])
        self.assertIn('dwo(@esp+14)', commands['152']['body'])
        self.assertNotIn('poi(', prepared['fragment'])
        self.assertNotRegex(prepared['fragment'], r'(?i)(?:^|[;{]\s*)\s*(?:e[bdwq]|r\s|\.call|g\s*=|q\b)')
        for number in observer.DEFAULT_IDS:
            self.assertIn(f'\r\nbd {number}\r\n', prepared['fragment'])
        self.assertTrue(prepared['fragment'].endswith('\r\n'))
        self.assertNotIn('\n', prepared['fragment'].replace('\r\n', ''))
        self.assertTrue(all(len(line.encode('ascii')) < 4096 for line in prepared['fragment'].splitlines()))
        self.assertEqual(observer.sha(prepared['fragment'].encode('ascii')), prepared['fragment_sha256'])

    def test_breakpoint_id_and_address_collisions_and_wrong_types_rejected(self):
        cases = [((150, 150, 152), {}), ((True, 151, 152), {}), ((150, 151, 1000), {}),
                 ((150, 151), {}), (observer.DEFAULT_IDS, {150: 0x401000}),
                 (observer.DEFAULT_IDS, {1: observer.text.TEXT_TARGET}),
                 (observer.DEFAULT_IDS, {'150': 0x401000}), (observer.DEFAULT_IDS, {1: True})]
        for ids, occupied in cases:
            with self.subTest(ids=ids, occupied=occupied), self.assertRaises(ValueError):
                observer._compose(context(), sites(), SOURCE_ROWS, breakpoint_ids=ids, occupied_breakpoints=occupied)
        prepared = observer._compose(context(), sites(), SOURCE_ROWS, breakpoint_ids=(170, 171, 172), occupied_breakpoints={150: 0x401000})
        self.assertEqual(prepared['arm_command'], 'be 170 171 172')

    def test_line_overflow_rejected_without_clipping(self):
        with patch.object(observer, '_printf', return_value='x' * 4096), self.assertRaisesRegex(ValueError, 'line limit'):
            packet()

    def test_loaded_probe_stage_recipe_sha_and_source_context_mismatches_rejected(self):
        for key, value in (('stage', 'old-stage'), ('recipe_revision', 'old'), ('resolution', '900x700'),
                           ('candidate_sha256', '1' * 64), ('probe_sha256', '0' * 64), ('source_hashes', {})):
            data = context(); data[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                observer._compose(data, sites(), SOURCE_ROWS, breakpoint_ids=observer.DEFAULT_IDS, occupied_breakpoints={})

    def test_duplicate_missing_reordered_and_unknown_events_preserved_as_failure(self):
        prepared = packet(); good = rows(prepared)
        cases = [good[:2], good[1:], good + [good[2]], [good[1], good[0], good[2]], good[:1] + good]
        for changed in cases:
            with self.subTest(count=len(changed)):
                result = observer.evaluate_sequence(trace(prepared, changed), prepared)
                self.assertFalse(result['sequence_passed'])
                self.assertEqual(result['observed_event_count'], len(changed))
                self.assertEqual(len(result['raw_records']), len(changed) + 6)
        for extra in ('MWTEXT_EVENT event=UNKNOWN', ' MWTEXT_EVENT event=RETURN', 'MWTEXT_OBSERVER_REJECT event=NATIVE reason=header_pointer'):
            result = observer.evaluate_sequence(trace(prepared) + extra + '\n', prepared)
            self.assertFalse(result['sequence_passed'])
            self.assertEqual(result['raw_records'][-1]['text'], extra)

    def test_startup_identity_duplicate_reorder_cross_candidate_and_prefixed_records_fail(self):
        prepared = packet(); good = trace(prepared); lines = good.splitlines()
        changes = ['\n'.join(lines[1:]), '\n'.join([lines[1], lines[0]] + lines[2:]),
                   '\n'.join(lines[:3] + [lines[1]] + lines[3:]),
                   '\n'.join(lines[:2] + lines[3:4] + lines[2:3] + lines[4:]),
                   good.replace('candidate_sha256=' + 'a' * 64, 'candidate_sha256=' + 'b' * 64, 1),
                   '0:000> ' + good, good.replace('MWIDGETS_SCOPE', 'MPRIMARY_SCOPE', 1),
                   good + 'MPRIMARY_CONTRACT_PASS stage=old candidate_sha256=' + 'b' * 64,
                   good + 'PTILE_CONTRACT_PASS stage=old candidate_sha256=' + 'a' * 64]
        for changed in changes:
            with self.subTest(changed=changed[:80]):
                self.assertFalse(observer.evaluate_sequence(changed, prepared)['sequence_passed'])

    def test_wrong_thread_stack_return_context_and_saved_registers_fail(self):
        prepared = packet()
        mutations = [(0, 'caller', 0x432C6C), (1, 'tid', 0x115), (1, 'esp', 0x1F0004),
                     (2, 'esp', 0x1F0000), (2, 'eip', 0x432C6C), (1, 'ebp', 0),
                     (1, 'eax', 0), (1, 'flags', 0xED6), (2, 'ebx', 0),
                     (0, 'render', 0x700000), (2, 'map', 0x700000), (1, 'root_esp', 0x1F0104)]
        for index, key, value in mutations:
            changed = rows(prepared); changed[index][1][key] = value
            with self.subTest(index=index, key=key):
                self.assertFalse(observer.evaluate_sequence(trace(prepared, changed), prepared)['sequence_passed'])

    def test_native_return_allows_cdecl_volatile_register_changes(self):
        for resolution in observer.context_reader.RESOLUTIONS:
            prepared = packet(resolution)
            for quantity in (0, 250, -1, -2147483648, 2147483647):
                for registers in (('eax',), ('ecx',), ('edx',), ('eax', 'ecx', 'edx')):
                    changed = rows(prepared, quantity)
                    for key in registers:
                        changed[2][1][key] = changed[1][1][key] ^ 0xFFFFFFFF
                    with self.subTest(resolution=resolution, quantity=quantity, registers=registers):
                        result = observer.evaluate_sequence(trace(prepared, changed), prepared)
                        self.assertTrue(result['sequence_passed'], result['failures'])
                        self.assertEqual(result['signed_quantity'], quantity)
                        self.assertEqual(result['raw_records'][-1]['values'], changed[2][1])
                        for key in ('source_authenticated', 'text_call_observed', 'runtime_accepted',
                                    'manual_input_proof', 'promotion_ready'):
                            self.assertFalse(result[key])

    def test_native_return_rejects_each_cdecl_saved_register_change(self):
        for resolution in observer.context_reader.RESOLUTIONS:
            prepared = packet(resolution)
            for key in ('ebx', 'esi', 'edi', 'ebp'):
                changed = rows(prepared)
                changed[2][1][key] ^= 1
                with self.subTest(resolution=resolution, register=key):
                    result = observer.evaluate_sequence(trace(prepared, changed), prepared)
                    self.assertFalse(result['sequence_passed'])
                    self.assertTrue(any('native formatter did not preserve its saved registers' in failure
                                        for failure in result['failures']), result['failures'])
                    self.assertEqual(result['observed_event_count'], 3)
                    self.assertEqual(result['raw_records'][-1]['values'], changed[2][1])
                    self.assertFalse(result['text_call_observed'])
                    self.assertFalse(result['runtime_accepted'])

    def test_adapter_still_preserves_every_incoming_general_register(self):
        for resolution in observer.context_reader.RESOLUTIONS:
            prepared = packet(resolution)
            for key in ('eax', 'ebx', 'ecx', 'edx', 'esi', 'edi', 'ebp'):
                changed = rows(prepared)
                changed[1][1][key] ^= 1
                with self.subTest(resolution=resolution, register=key):
                    result = observer.evaluate_sequence(trace(prepared, changed), prepared)
                    self.assertFalse(result['sequence_passed'])
                    self.assertTrue(any('adapter changed incoming native registers' in failure
                                        for failure in result['failures']), result['failures'])
                    self.assertEqual(result['raw_records'][-2]['values'], changed[1][1])

    def test_owner_geometry_fault_com_pointer_alias_and_backend_failures(self):
        prepared = packet()
        mutations = [('phase', 0), ('fault', 4), ('state', 0x620000), ('owner_tid', 0x115),
                     ('native_width', 800), ('physical_height', 600), ('native_com', 1),
                     ('native_vtable', 0), ('physical_data', 0), ('native', 0x700000),
                     ('native_pixels', 0x1000000), ('physical_pixels', 0x7FFFFFF0),
                     ('primary_depth', 16), ('primary_vtable', 0), ('primary_backend', 0), ('primary_surface', 0)]
        for key, value in mutations:
            changed = rows(prepared)
            for _, row in changed: row[key] = value
            with self.subTest(key=key):
                self.assertFalse(observer.evaluate_sequence(trace(prepared, changed), prepared)['sequence_passed'])

    def test_coordinates_alignment_format_and_signed_quantity_must_match_at_both_boundaries(self):
        prepared = packet()
        for index in range(3):
            for arg in range(6):
                if index == 0 and arg == 5: continue
                changed = rows(prepared); changed[index][1][f'arg{arg}'] ^= 1
                with self.subTest(index=index, arg=arg):
                    self.assertFalse(observer.evaluate_sequence(trace(prepared, changed), prepared)['sequence_passed'])

    def test_full_width_quantity_bits_are_required_and_not_signed_decimal_reparsed(self):
        prepared = packet(); good = trace(prepared, rows(prepared, -1))
        self.assertIn('arg5=ffffffff', good)
        for bad in ('arg5=-1', 'arg5=ffffffffffffffff', 'arg5=100000000'):
            result = observer.evaluate_sequence(good.replace('arg5=ffffffff', bad, 1), prepared)
            self.assertFalse(result['sequence_passed'])

    def test_unrelated_records_are_not_rewritten_and_original_failures_are_preserved(self):
        prepared = packet()
        passing = 'MCAP_CANVAS event=other_observation\n' + trace(prepared) + 'MPCOMP_EVENT event=other_observation\n'
        self.assertTrue(observer.evaluate_sequence(passing, prepared)['sequence_passed'])
        for failure in ('MCAP_REJECT reason=old_failure', 'MPRIMARYTEXT_CONTRACT_FAIL', 'Syntax error in command',
                        'Memory access error at 00000000', 'Access violation - code c0000005 (first chance)',
                        'Unable to insert breakpoint 151 at 0040c150, Win32 error 0n998',
                        'bp151 at 0040c150 failed', 'Command file execution failed'):
            result = observer.evaluate_sequence(passing + failure + '\n', prepared)
            self.assertFalse(result['sequence_passed'], failure)
            self.assertTrue(any('failure' in f or 'rejected' in f for f in result['failures']))
            self.assertEqual(result['raw_records'][-1]['text'], failure)

    def test_malformed_or_mutated_diagnostic_packet_fails_without_source_claim(self):
        prepared = packet()
        cases = [{}, None]
        for key in ('expected_loaded_records', 'contract_line', 'expected_original_args', 'expected_translated_args'):
            changed = copy.deepcopy(prepared); del changed[key]; cases.append(changed)
        changed = copy.deepcopy(prepared); changed['expected_translated_args'][0] += 1; cases.append(changed)
        for altered in cases:
            with self.subTest(altered=altered is None):
                result = observer.evaluate_sequence(trace(prepared), altered)
                self.assertFalse(result['sequence_passed'])
                self.assertFalse(result['source_authenticated'])

    def test_public_preparation_authenticates_before_observer_derivation(self):
        expected = context()
        with patch.object(observer.context_reader, 'load_context', return_value=expected) as load, \
             patch.object(observer, '_sites', return_value=sites()) as bind:
            prepared = observer.build_fragment(b'original', b'candidate', Path('bundle.candidate.json'), occupied_breakpoints={})
        load.assert_called_once_with(b'original', b'candidate', Path('bundle.candidate.json'))
        bind.assert_called_once_with(b'candidate', expected['text_context'])
        self.assertEqual(prepared['binding']['candidate_sha256'], 'a' * 64)
        with patch.object(observer.context_reader, 'load_context', side_effect=ValueError('unknown candidate')), \
             patch.object(observer, '_sites') as bind, self.assertRaisesRegex(ValueError, 'unknown'):
            observer.build_fragment(b'original', b'candidate', Path('bundle.candidate.json'), occupied_breakpoints={})
        bind.assert_not_called()

    def test_full_validator_regenerates_packet_fragment_and_never_turns_failed_sequence_into_pass(self):
        prepared = packet(); log = trace(prepared)
        with patch.object(observer, 'build_fragment', return_value=prepared) as regenerate:
            result = observer.validate_trace(log, b'o', b'c', Path('m'), prepared, prepared['fragment'], occupied_breakpoints={})
            self.assertTrue(result['source_authenticated']); self.assertTrue(result['text_call_observed'])
            self.assertFalse(result['runtime_accepted'])
            regenerate.assert_called_once()
            failed = observer.validate_trace(log + event_line(*rows(prepared)[2]), b'o', b'c', Path('m'), prepared, prepared['fragment'], occupied_breakpoints={})
            self.assertTrue(failed['source_authenticated']); self.assertFalse(failed['sequence_passed']); self.assertFalse(failed['text_call_observed'])
            changed = copy.deepcopy(prepared); changed['expected_translated_args'][0] += 1
            with self.assertRaisesRegex(ValueError, 'regeneration'):
                observer.validate_trace(log, b'o', b'c', Path('m'), changed, prepared['fragment'], occupied_breakpoints={})
            with self.assertRaisesRegex(ValueError, 'regeneration'):
                observer.validate_trace(log, b'o', b'c', Path('m'), prepared, prepared['fragment'] + 'gc\n', occupied_breakpoints={})

    def test_site_binding_authenticates_code_tail_call_cleanup_and_native_spans(self):
        base = 0x600000
        code = b'\x9c\x60\x61\x9d\xe9' + struct.pack('<i', observer.text.TEXT_TARGET - base - 9)
        call = b'\xe8' + struct.pack('<i', base - observer.text.TEXT_CALL - 5)
        native = b'\x53\x51\x52\xc3'
        image = {(base, len(code)): code, (observer.text.TEXT_CALL, 5): call,
                 (observer.text.TEXT_RETURN, 3): b'\x83\xc4\x18', (observer.text.TEXT_FORMAT, 3): b'%d\0',
                 (observer.text.TEXT_TARGET, 4): native}
        manifest = dict(code_va=base, code_bytes=len(code), code_sha256=hashlib.sha256(code).hexdigest(),
                        text_entry_vas={'quantity': base}, modal_state_va=0x610000)
        def bind():
            with patch.object(observer.inherited.pe, 'inspect_pe', return_value=object()), \
                 patch.object(observer.inherited, '_read', side_effect=lambda candidate, view, va, size: image[(va, size)]), \
                 patch.object(observer.text, 'NATIVE_SPANS', ((observer.text.TEXT_TARGET, 4, observer.sha(native)),)):
                return observer._sites(b'synthetic image', manifest)
        self.assertEqual(bind()['adapter'], base)
        for key in tuple(image):
            old = image[key]; image[key] = bytes([old[0] ^ 1]) + old[1:]
            with self.subTest(key=key), self.assertRaises(ValueError): bind()
            image[key] = old

# Exact source-generated echo records; no runtime observations.
# widget-1024.cdb SHA256 008c667627b540fe703915c09c03ae157b6289ca8992148457d917cd66607941.
CANONICAL_ECHO_LINES = ('.echo === Partial-tile validation installed-hook diagnostic ===', '.echo MWIDGETS_CONTRACT_PASS stage=gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-completehd-modalwidgets-validation resolution=1024x768 candidate_sha256=ebea660f885da43896ad5e4303e6e7d7fe112def6c897b4c26312df8505376e5 revision=owned_modal_widget_bounds_v1', '.echo MWIDGETS_SCOPE owned_modal_widget_bounds primary_composition_proven=false manual_input_proof=false promotion_ready=false', '.echo ARMY_SCOPE own_player_0_to_3_native_size_panel manual_input_proof=false promotion_ready=false', '.echo PTILE_CONTRACT_PASS stage=gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-completehd-modalwidgets-validation resolution=1024x768 candidate_sha256=ebea660f885da43896ad5e4303e6e7d7fe112def6c897b4c26312df8505376e5', '.echo PTILE_SCOPE guarded_map_only manual_input_proof=false promotion_ready=false')


class WidgetAdmissionTests(unittest.TestCase):
    def test_canonical_generated_echo_stream_uses_real_widget_startup_order(self):
        data=context()
        data['candidate_sha256']='ebea660f885da43896ad5e4303e6e7d7fe112def6c897b4c26312df8505376e5'
        data['probe']='\n'.join(CANONICAL_ECHO_LINES)+'\n';data['probe_sha256']=observer.sha(data['probe'].encode())
        prepared=observer._compose(data,sites(),SOURCE_ROWS,breakpoint_ids=observer.DEFAULT_IDS,occupied_breakpoints={})
        expected=[CANONICAL_ECHO_LINES[i].removeprefix('.echo ') for i in (1,2,3,4,5)]
        self.assertEqual(prepared['expected_loaded_records'],expected)
        authentic_startup='\n'.join(row.removeprefix('.echo ') for row in CANONICAL_ECHO_LINES)+'\n'
        log=authentic_startup+prepared['contract_line']+'\n'+'\n'.join(event_line(*row) for row in rows(prepared))+'\n'
        self.assertTrue(observer.evaluate_sequence(log,prepared)['sequence_passed'])
        reordered='\n'.join([expected[2],expected[0],expected[1],prepared['contract_line']])+'\n'
        self.assertFalse(observer.evaluate_sequence(reordered+'\n'.join(event_line(*row) for row in rows(prepared)),prepared)['sequence_passed'])

    def test_inherited_text_identity_and_owner_cannot_be_relabeled(self):
        for key, changed in (('stage', observer.STAGE), ('candidate_sha256', 'a'*64), ('resolution', '800x600')):
            data=context(); data['text_context'][key]=changed
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'genuine inherited'):
                observer._compose(data, sites(), SOURCE_ROWS, breakpoint_ids=observer.DEFAULT_IDS, occupied_breakpoints={})
        data=context(); data['owner_context']['state_va']+=4
        with self.assertRaisesRegex(ValueError, 'genuine inherited'):
            observer._compose(data, sites(), SOURCE_ROWS, breakpoint_ids=observer.DEFAULT_IDS, occupied_breakpoints={})

    def test_legacy_text_events_and_prefixed_or_duplicate_startup_are_retained(self):
        prepared=packet(); good=trace(prepared)
        samples=('MPTEXT_EVENT event=RETURN', 'MPRIMARYTEXT_CONTRACT_PASS stage=old',
                 'x_MWTEXT_EVENT event=RETURN', 'x_PTILE_CONTRACT_PASS malformed',
                 'x_MWIDGETS_CONTRACT_PASS malformed', 'MWTEXT_OBSERVER_REJECT event=ADAPTER')
        for row in samples:
            result=observer.evaluate_sequence(good+row+'\n'+row+'\n',prepared)
            self.assertFalse(result['sequence_passed'])
            self.assertEqual([r['text'] for r in result['raw_records'][-2:]], [row,row])
            self.assertEqual([r['line'] for r in result['raw_records'][-2:]], [10,11])
        for index in range(6):
            lines=good.splitlines(); lines.insert(index,lines[index])
            self.assertFalse(observer.evaluate_sequence('\n'.join(lines),prepared)['sequence_passed'])

    def test_predecessor_and_duplicate_scopes_remain_reserved_diagnostics(self):
        prepared=packet();good=trace(prepared)
        for row in ('MPRIMARY_SCOPE forged predecessor scope','MCANVAS_SCOPE forged predecessor scope',
                    'ARMY_SCOPE corrupted','PTILE_SCOPE corrupted', prepared['expected_loaded_records'][2],
                    prepared['expected_loaded_records'][4]):
            result=observer.evaluate_sequence(good+row+'\n'+row+'\n',prepared)
            self.assertFalse(result['sequence_passed'],row)
            self.assertEqual([r['text'] for r in result['raw_records'][-2:]],[row,row])
            self.assertEqual([r['line'] for r in result['raw_records'][-2:]],[10,11])

    def test_malformed_packet_keeps_every_raw_record_and_debugger_failure(self):
        prepared=packet(); log=trace(prepared)+'x_MWTEXT_REJECT duplicate\nx_MWTEXT_REJECT duplicate\nSyntax error in command\n'
        expected=observer._raw_records(log)
        for invalid in ({}, None, {'schema': observer.SCHEMA, 'protocol_revision':observer.PROTOCOL}):
            result=observer.evaluate_sequence(log,invalid)
            self.assertEqual(result['raw_records'],expected)
            self.assertEqual(result['observed_event_count'],3)
            self.assertFalse(result['source_authenticated'])

    def test_strict_json_rejects_duplicates_nonfinite_nonobjects_and_deep_inputs(self):
        invalid=(b'{"x":1,"x":2}', b'{"nested":{"x":1,"x":2}}', b'{"x":NaN}', b'{"x":Infinity}',
                 b'{"x":1e999}', b'[]', b'null', b'1', b'{"x":'+b'['*10000+b'0'+b']'*10000+b'}',
                 b'{"x":'*10000+b'0'+b'}'*10000)
        for raw in invalid:
            with self.subTest(prefix=raw[:30]), self.assertRaises(ValueError): observer.parse_object(raw)
        self.assertEqual(observer.parse_object(b'{"n":1,"b":true,"list":[0,false,null]}'),
                         {'n':1,'b':True,'list':[0,False,None]})
        nested=[]; child=nested
        for _ in range(10000): child.append([]); child=child[0]
        with self.assertRaisesRegex(ValueError,'nesting'): observer.canonical(nested)

    def test_inventory_json_rejects_ambiguous_ids_and_preserves_exact_types(self):
        for raw in (b'{"0":1,"0":2}', b'{"01":4198400}', b'{"+1":4198400}', b'{"1000":4198400}'):
            with self.assertRaises(ValueError): observer.parse_inventory(raw)
        self.assertEqual(observer.parse_inventory(b'{"1":4198400}'),{1:4198400})
        with self.assertRaises(ValueError):
            observer._compose(context(),sites(),SOURCE_ROWS,breakpoint_ids=observer.DEFAULT_IDS,
                              occupied_breakpoints=observer.parse_inventory(b'{"1":true}'))

    def test_all_dependency_sources_are_bound_and_reread_after_admission(self):
        self.assertEqual(set(SOURCE_ROWS),observer.SOURCES)
        self.assertTrue(observer.context_reader.RECIPE_SOURCE_PATHS.issubset(SOURCE_ROWS))
        prepared=packet()
        self.assertEqual(set(prepared['binding']['preparation_source_hashes']),observer.SOURCES)
        real=observer.context_reader._snapshot
        for name in ('tools/modal_primary_text_observer.py','src/patcher/framed_modal_canvas.py',
                     'tools/modal_primary_text_context.py','tools/modal_widgets_text_observer.py'):
            changed=False
            def snapshot(path):
                row=real(path)
                return replace(row,data=row.data+b'\n') if changed and Path(path)==observer.ROOT/name else row
            def admit(*args):
                nonlocal changed
                changed=True
                return context()
            with self.subTest(name=name), patch.object(observer.context_reader,'_snapshot',side_effect=snapshot), \
                 patch.object(observer.context_reader,'load_context',side_effect=admit), \
                 patch.object(observer,'_sites',return_value=sites()), self.assertRaises(ValueError):
                observer.build_fragment(b'o',b'c',Path('synthetic.candidate.json'),occupied_breakpoints={})

    def test_frozen_helper_drift_rejected_before_authentication(self):
        with patch.dict(observer.PINS,{'tools/modal_primary_text_observer.py':'0'*64}), \
             patch.object(observer.context_reader,'load_context') as auth, self.assertRaisesRegex(ValueError,'frozen'):
            observer.build_fragment(b'o',b'c',Path('synthetic.candidate.json'),occupied_breakpoints={})
        auth.assert_not_called()

    def test_exact_packet_types_crlf_and_failed_admission_preserve_raw_diagnostics(self):
        prepared=packet(); log=trace(prepared)+'MWTEXT_REJECT original\nMWTEXT_REJECT original\n'
        self.assertEqual(prepared['fragment_encoding'],'ascii');self.assertEqual(prepared['fragment_line_endings'],'CRLF')
        changes=[]
        for key,value in (('prepared',1),('fragment_line_endings','LF'),('breakpoint_commands',{})):
            altered=copy.deepcopy(prepared);altered[key]=value;changes.append((altered,prepared['fragment']))
        changes.append((prepared,prepared['fragment'].replace('\r\n','\n')))
        with patch.object(observer,'build_fragment',return_value=prepared):
            for altered,fragment in changes:
                with self.assertRaises(observer.AdmissionError) as caught:
                    observer.validate_trace(log,b'o',b'c',Path('m'),altered,fragment,occupied_breakpoints={})
                result=caught.exception.diagnostic
                self.assertFalse(result['sequence_passed']);self.assertFalse(result['source_authenticated'])
                self.assertEqual(result['raw_records'],observer._raw_records(log))
        with patch.object(observer,'build_fragment',side_effect=ValueError('candidate rejected')):
            with self.assertRaises(observer.AdmissionError) as caught:
                observer.validate_trace(log,b'o',b'c',Path('m'),prepared,prepared['fragment'],occupied_breakpoints={})
        self.assertIn('candidate rejected',caught.exception.diagnostic['failures'][0])
        self.assertEqual(caught.exception.diagnostic['raw_records'],observer._raw_records(log))

    def test_cli_malformed_packet_retains_log_and_returns_failure_without_rebuild(self):
        prepared=packet(); log=trace(prepared)+'MWTEXT_REJECT original\n'
        with tempfile.TemporaryDirectory(prefix='clash-widget-text-cli-') as folder:
            root=Path(folder).resolve()
            for name,data in {'original':b'o','candidate':b'c','inventory':b'{}','packet':b'{"x":NaN}',
                              'fragment':prepared['fragment'].encode('ascii'),'log':log.encode()}.items():
                (root/name).write_bytes(data)
            argv=['tool','--original',str(root/'original'),'--candidate',str(root/'candidate'),
                  '--candidate-manifest',str(root/'m.candidate.json'),'--occupied-breakpoints',str(root/'inventory'),
                  '--packet',str(root/'packet'),'--fragment',str(root/'fragment'),'--log',str(root/'log')]
            output=io.StringIO()
            with patch('sys.argv',argv),patch.object(observer,'build_fragment') as build,redirect_stdout(output):
                status=observer.main()
            self.assertEqual(status,1);build.assert_not_called()
            self.assertEqual(json.loads(output.getvalue())['raw_records'],observer._raw_records(log))


if __name__ == '__main__':
    unittest.main(verbosity=2)
