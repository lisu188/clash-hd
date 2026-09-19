"""Fast synthetic observation/trace fixtures; no game or debugger is launched."""
import copy
import hashlib
from pathlib import Path
import re
import struct
import unittest
from unittest.mock import patch

import modal_primary_text_observer as observer


def context(resolution='1024x768'):
    stage, revision = observer.context_reader.STAGE, observer.context_reader.REVISION
    loaded = (f'.echo MPRIMARYTEXT_CONTRACT_PASS stage={stage} resolution={resolution} '
              f'candidate_sha256={"a" * 64} revision={revision}\n'
              '.echo MPRIMARYTEXT_SCOPE owned_modal_primary_text primary_composition_proven=false manual_input_proof=false promotion_ready=false\n')
    sources = {'synthetic_fixture_source.py': 'b' * 64}
    return dict(stage=stage, recipe_revision=revision, resolution=resolution,
                candidate_sha256='a' * 64, original_sha256='c' * 64, source_hashes=sources,
                context_source_sha256='d' * 64, manifest_path='synthetic.candidate.json',
                manifest_sha256='e' * 64, manifest_canonical_sha256='f' * 64,
                manifest={'source_hashes': sources}, probe=loaded, probe_sha256=observer.sha(loaded.encode()))


def sites():
    return dict(adapter=0x600000, native=observer.text.TEXT_TARGET, return_va=observer.text.TEXT_RETURN,
                call_va=observer.text.TEXT_CALL, state_va=0x610000, byte_spans=[])


def packet(resolution='1024x768'):
    return observer._compose(context(resolution), sites(), breakpoint_ids=observer.DEFAULT_IDS, occupied_breakpoints={})


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
    return 'MPTEXT_EVENT event=' + event + ' ' + ' '.join(f'{key}={values[key]:08x}' for key in observer.FIELDS)


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
                observer._compose(context(), sites(), breakpoint_ids=ids, occupied_breakpoints=occupied)
        prepared = observer._compose(context(), sites(), breakpoint_ids=(170, 171, 172), occupied_breakpoints={150: 0x401000})
        self.assertEqual(prepared['arm_command'], 'be 170 171 172')

    def test_line_overflow_rejected_without_clipping(self):
        with patch.object(observer, '_printf', return_value='x' * 4096), self.assertRaisesRegex(ValueError, 'line limit'):
            packet()

    def test_loaded_probe_stage_recipe_sha_and_source_context_mismatches_rejected(self):
        for key, value in (('stage', 'old-stage'), ('recipe_revision', 'old'), ('resolution', '900x700'),
                           ('candidate_sha256', '1' * 64), ('probe_sha256', '0' * 64), ('source_hashes', {})):
            data = context(); data[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                observer._compose(data, sites(), breakpoint_ids=observer.DEFAULT_IDS, occupied_breakpoints={})

    def test_duplicate_missing_reordered_and_unknown_events_preserved_as_failure(self):
        prepared = packet(); good = rows(prepared)
        cases = [good[:2], good[1:], good + [good[2]], [good[1], good[0], good[2]], good[:1] + good]
        for changed in cases:
            with self.subTest(count=len(changed)):
                result = observer.evaluate_sequence(trace(prepared, changed), prepared)
                self.assertFalse(result['sequence_passed'])
                self.assertEqual(result['observed_event_count'], len(changed))
                self.assertEqual(len(result['raw_records']), len(changed) + 3)
        for extra in ('MPTEXT_EVENT event=UNKNOWN', ' MPTEXT_EVENT event=RETURN', 'MPTEXT_OBSERVER_REJECT event=NATIVE reason=header_pointer'):
            result = observer.evaluate_sequence(trace(prepared) + extra + '\n', prepared)
            self.assertFalse(result['sequence_passed'])
            self.assertEqual(result['raw_records'][-1]['text'], extra)

    def test_startup_identity_duplicate_reorder_cross_candidate_and_prefixed_records_fail(self):
        prepared = packet(); good = trace(prepared); lines = good.splitlines()
        changes = ['\n'.join(lines[1:]), '\n'.join([lines[1], lines[0]] + lines[2:]),
                   '\n'.join(lines[:3] + [lines[1]] + lines[3:]),
                   '\n'.join(lines[:2] + lines[3:4] + lines[2:3] + lines[4:]),
                   good.replace('candidate_sha256=' + 'a' * 64, 'candidate_sha256=' + 'b' * 64, 1),
                   '0:000> ' + good, good.replace('MPRIMARYTEXT_SCOPE', 'MPRIMARY_SCOPE', 1),
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
        bind.assert_called_once_with(b'candidate', expected['manifest'])
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
            with patch.object(observer.pe, 'inspect_pe', return_value=object()), \
                 patch.object(observer, '_read', side_effect=lambda candidate, view, va, size: image[(va, size)]), \
                 patch.object(observer.text, 'NATIVE_SPANS', ((observer.text.TEXT_TARGET, 4, observer.sha(native)),)):
                return observer._sites(b'synthetic image', manifest)
        self.assertEqual(bind()['adapter'], base)
        for key in tuple(image):
            old = image[key]; image[key] = bytes([old[0] ^ 1]) + old[1:]
            with self.subTest(key=key), self.assertRaises(ValueError): bind()
            image[key] = old


if __name__ == '__main__':
    unittest.main(verbosity=2)
