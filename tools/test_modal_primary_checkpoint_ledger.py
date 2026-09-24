"""Synthetic, file-backed query-ledger fixtures. No target or native API runs."""
import copy
from datetime import datetime
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import modal_primary_checkpoint_ledger as tool


PRIMARY = (('primary', 220), ('backend', 176), ('surface_full', 32), ('palette', 1036),
           ('proxy_header', 512), ('proxy_getpalette', 83), ('surface', 4),
           ('surface_vtable', 144), ('palette_vtable', 28))
CURSOR = (('state', 68), ('descriptor', 40), ('resource', 4112), ('sprite_header', 10),
          ('backing_header', 188), ('backing_pixels', 4096), ('barracks_pointer', 4),
          ('barracks_resource', 4112), ('placeholder_sprite_header', 10))


def region(address=0x1000000, size=0x2000000):
    return dict(address=address, size=size, state=0x1000, protect=4,
                allocation_base=0x1000000, allocation_protect=4, type=0x20000)


class Fixture:
    def __init__(self, root, stream='primary', resolution='800x600', checkpoint='final-ready', sample=1, mbi=48):
        self.stream = stream
        self.directory = root / checkpoint / f'capture-{sample}'
        self.directory.mkdir(parents=True)
        trace = self.directory.parent / 'capture-prefix.log'
        trace.write_bytes(b'SYNTHETIC checkpoint fixture; no game observations\n')
        seconds = datetime(2026, 9, 19, 12) - datetime(1601, 1, 1)
        self.binding = dict(stage=tool.STAGE, recipe_revision=tool.RECIPE, candidate_sha256='a' * 64,
                            resolution=resolution, run_id='synthetic-ledger-fixture',
                            checkpoint=dict(name=checkpoint, index=tool.CHECKPOINTS.index(checkpoint)), capture_index=sample,
                            game_identity=dict(process_id=1234, path='C:/ClashTests/synthetic-ledger/game.exe',
                                               creation_filetime=(seconds.days * 86400 + seconds.seconds) * 10000000,
                                               creation_utc='2026-09-19T12:00:00.0000000Z', handle_retained=True),
                            trace=self.artifact(trace))
        self.receipt = dict(revision=tool.REVISION, region_scheme=tool.SCHEME, stream=stream,
                            binding=copy.deepcopy(self.binding), reads={}, regions=[region()])
        self.order = []
        for phase in ('before', 'after'):
            self.receipt['reads'][phase] = {}
            for index, (name, size) in enumerate(PRIMARY if stream == 'primary' else CURSOR):
                filename = 'barracks-pointer' if name == 'barracks_pointer' else name
                path = self.directory / f'{stream}-{phase}-{filename}.raw'
                path.write_bytes(bytes([index + 1]) * size)
                row = self.artifact(path, 0x1000000 + index * 0x10000 + 8)
                self.receipt['reads'][phase][name] = row
                self.order.append(row)
            if stream == 'primary' and phase == 'before':
                width, height = map(int, resolution.split('x'))
                path = self.directory / 'primary.raw'
                path.write_bytes(bytes(width * height))
                self.receipt['pixels'] = self.artifact(path, 0x2000000)
                self.order.append(self.receipt['pixels'])
        self.rows = [dict(kind='header', revision=tool.REVISION, scheme=tool.SCHEME, stream=stream,
                          binding=copy.deepcopy(self.binding), page_size=4096, mbi_bytes=mbi)]
        for index, row in enumerate(self.order, 1):
            # Legitimate nested tails: VirtualQueryEx starts at each requested
            # page, so all later matching observations are subsets of row one.
            start = row['address'] & ~4095
            self.rows += [dict(kind='query', read_index=index, query_index=1,
                               request={key: row[key] for key in ('path', 'address', 'bytes')}, cursor=row['address'],
                               requested_mbi_bytes=mbi, returned_mbi_bytes=mbi, region=region(start, 0x3000000 - start)),
                          dict(kind='read', read_index=index, artifact=copy.deepcopy(row))]
        self.write()

    @staticmethod
    def artifact(path, address=None):
        data = path.read_bytes()
        row = dict(path=str(path), bytes=len(data), sha256=tool.sha(data))
        if address is not None:
            row['address'] = address
        return row

    def write(self, raw=None):
        path = self.directory / f'{self.stream}-query-ledger.jsonl'
        if raw is None:
            raw = ('\n'.join(json.dumps(row, separators=(',', ':')) for row in self.rows) + '\n').encode()
        path.write_bytes(raw)
        self.receipt['query_ledger'] = dict(self.artifact(path), scheme=tool.SCHEME, records=len(self.rows))

    def audit(self):
        return tool.audit_checkpoint_ledger(self.receipt, stream=self.stream,
                                            capture_dir=self.directory, expected_binding=self.binding)


class CheckpointLedgerTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='clash-query-ledger-fixture-')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.serial = 0

    def fixture(self, **kwargs):
        self.serial += 1
        return Fixture(self.root / str(self.serial), **kwargs)

    def rejected(self, fixture, match=None):
        with self.assertRaises(tool.LedgerError) as caught:
            fixture.audit()
        if match is not None:
            self.assertRegex(str(caught.exception), match)
        result = caught.exception.diagnostics
        self.assertFalse(result['ledger_valid'])
        for key in ('source_authenticated', 'live_process_authenticated', 'runtime_accepted',
                    'primary_composition_proven', 'manual_input_proof', 'promotion_ready'):
            self.assertIs(result[key], False)
        return result

    def test_both_closed_read_orders_across_six_resolutions_and_mbi_layouts(self):
        for stream in ('primary', 'cursor'):
            for resolution in tool.RESOLUTIONS:
                for mbi in (28, 48):
                    with self.subTest(stream=stream, resolution=resolution, mbi=mbi):
                        fixture = self.fixture(stream=stream, resolution=resolution, mbi=mbi)
                        result = fixture.audit()
                        count = 19 if stream == 'primary' else 18
                        self.assertTrue(result['ledger_valid'])
                        self.assertEqual((result['reads'], result['queries'], result['records']), (count, count, 1 + count * 2))
                        self.assertEqual(result['certificate'], [region()])
                        self.assertEqual(len(result['raw_records']), 1 + count * 2)
                        self.assertFalse(result['source_authenticated'])
                        self.assertFalse(result['runtime_accepted'])

    def test_all_checkpoint_indices_allow_three_individual_samples_without_stability_claim(self):
        for checkpoint in tool.CHECKPOINTS:
            for sample in (1, 2, 3):
                with self.subTest(checkpoint=checkpoint, sample=sample):
                    result = self.fixture(checkpoint=checkpoint, sample=sample).audit()
                    self.assertTrue(result['ledger_valid'])
                    self.assertFalse({'clean_stable_pair', 'three_matched_captures', 'stability_proven'} & result.keys())
            fixture = self.fixture(checkpoint=checkpoint)
            fixture.binding['capture_index'] = 4
            self.rejected(fixture, 'capture index')

    def test_primary_read_can_cross_multiple_compatible_query_regions(self):
        fixture = self.fixture()
        first = fixture.rows[19]  # Primary pixels follow nine before reads.
        self.assertEqual(first['read_index'], 10)
        first['region'] = region(0x2000000, 4096)
        second = copy.deepcopy(first)
        second.update(query_index=2, cursor=0x2001000, region=region(0x2001000, 0xfff000))
        fixture.rows.insert(20, second)
        fixture.write()
        self.assertEqual(fixture.audit()['queries'], 20)

    def test_historical_revisions_streams_and_read_lists_cannot_substitute(self):
        for key, value in (('revision', 'slots_cached_primary_v2'), ('region_scheme', 'old'), ('stream', 'cursor')):
            fixture = self.fixture(); fixture.receipt[key] = value
            self.rejected(fixture)
        fixture = self.fixture(); del fixture.rows[0]['revision']; fixture.write()
        self.rejected(fixture, 'header')
        fixture = self.fixture(); fixture.receipt['expected_reads'] = fixture.order
        self.rejected(fixture, 'fields')
        fixture = self.fixture(stream='cursor'); del fixture.receipt['regions']
        self.rejected(fixture, 'fields')

    def test_wrong_stage_resolution_checkpoint_process_or_trace_binding_rejected(self):
        changes = [('stage', 'primary-v1'), ('recipe_revision', 'old'), ('resolution', '900x700'),
                   ('candidate_sha256', 'b' * 64), ('run_id', 'other'), ('capture_index', 2)]
        for key, value in changes:
            fixture = self.fixture(); fixture.receipt['binding'][key] = value
            self.rejected(fixture, 'binding')
        for key, value in (('process_id', 1235), ('process_id', True), ('handle_retained', 1),
                           ('creation_filetime', 1), ('creation_utc', '2026-09-19T12:00:01.0000000Z')):
            fixture = self.fixture(); fixture.receipt['binding']['game_identity'][key] = value
            self.rejected(fixture, 'binding')
        fixture = self.fixture(); fixture.rows[0]['binding']['trace']['sha256'] = '0' * 64; fixture.write()
        self.rejected(fixture, 'header')
        fixture = self.fixture(); Path(fixture.binding['trace']['path']).write_bytes(b'changed trace')
        self.rejected(fixture, 'hash')

    def test_invalid_outer_expectations_fail_without_source_or_process_claim(self):
        cases = [('stage', 'primary-v1'), ('resolution', '900x700'), ('candidate_sha256', 'A' * 64),
                 ('run_id', '../other'), ('capture_index', True), ('capture_index', 0)]
        for key, value in cases:
            fixture = self.fixture(); fixture.binding[key] = value
            self.rejected(fixture)
        for key, value in (('creation_utc', '2026-13-19T12:00:00.0000000Z'), ('creation_filetime', 1),
                           ('handle_retained', 1), ('path', 'relative.exe')):
            fixture = self.fixture(); fixture.binding['game_identity'][key] = value
            self.rejected(fixture)
        fixture = self.fixture(checkpoint='full-published'); fixture.binding['capture_index'] = 4
        self.rejected(fixture)

    def test_each_missing_or_extra_read_rejected_for_primary_and_cursor(self):
        for stream, shapes in (('primary', PRIMARY), ('cursor', CURSOR)):
            for phase in ('before', 'after'):
                for name, _ in shapes:
                    fixture = self.fixture(stream=stream); del fixture.receipt['reads'][phase][name]
                    self.rejected(fixture, 'inventory')
            fixture = self.fixture(stream=stream); fixture.receipt['reads']['before']['extra'] = fixture.order[0]
            self.rejected(fixture, 'inventory')

    def test_cursor_actual_pointer_before_target_order_required(self):
        fixture = self.fixture(stream='cursor')
        a, b = 1 + 6 * 2, 1 + 7 * 2
        self.assertIn('barracks-pointer.raw', fixture.rows[a]['request']['path'])
        self.assertIn('barracks_resource.raw', fixture.rows[b]['request']['path'])
        fixture.rows[a:a + 4] = fixture.rows[b:b + 2] + fixture.rows[a:a + 2]
        fixture.write()
        self.rejected(fixture, 'sequence')

    def test_missing_reordered_extra_or_uncompleted_queries_rejected_and_retained(self):
        for mutation in ('missing_query', 'missing_read', 'repeat_query', 'extra_query', 'reordered'):
            fixture = self.fixture(stream='cursor')
            if mutation == 'missing_query': del fixture.rows[1]
            elif mutation == 'missing_read': del fixture.rows[2]
            elif mutation == 'repeat_query': fixture.rows.insert(2, copy.deepcopy(fixture.rows[1]))
            elif mutation == 'extra_query': fixture.rows.append(copy.deepcopy(fixture.rows[1]))
            else: fixture.rows[1], fixture.rows[3] = fixture.rows[3], fixture.rows[1]
            fixture.write()
            result = self.rejected(fixture)
            self.assertEqual(len(result['raw_records']), len(fixture.rows))
            self.assertEqual(result['ledger']['sha256'], fixture.receipt['query_ledger']['sha256'])

    def test_every_query_identity_field_exact_including_bool_float(self):
        for key, value in (('kind', 'failure'), ('read_index', True), ('read_index', 1.0), ('query_index', 2),
                           ('cursor', 0x1001000), ('requested_mbi_bytes', 28), ('returned_mbi_bytes', 0),
                           ('returned_mbi_bytes', 47), ('returned_mbi_bytes', 48.0)):
            fixture = self.fixture(); fixture.rows[1][key] = value; fixture.write()
            self.rejected(fixture)
        fixture = self.fixture(); fixture.rows[1]['request']['bytes'] = 1; fixture.write()
        self.rejected(fixture)
        fixture = self.fixture(); fixture.rows[2]['artifact']['sha256'] = '0' * 64; fixture.write()
        self.rejected(fixture)

    def test_allocation_attribute_conflicts_and_unreadable_or_invalid_pages_fail(self):
        for key, value in (('allocation_base', 0x1010000), ('allocation_protect', 2), ('type', 0x40000),
                           ('state', 0x2000), ('protect', 0x104), ('size', 0), ('size', 0x100000000),
                           ('address', 1), ('address', 0xffffffff), ('protect', True), ('protect', 4.0)):
            fixture = self.fixture(); fixture.rows[3]['region'][key] = value; fixture.write()
            result = self.rejected(fixture)
            self.assertEqual(result['raw_records'][3]['record']['region'][key], value)
        fixture = self.fixture(); fixture.rows[1]['region'] = region(0x1001000, 4096); fixture.write()
        self.rejected(fixture, 'gap')
        fixture = self.fixture(); del fixture.rows[1]['region']['type']; fixture.write()
        self.rejected(fixture)

    def test_regions_required_and_equal_entire_ledger_not_a_subset(self):
        for stream in ('primary', 'cursor'):
            for value in (None, [], [region(0x1000000, 4096)], [region(), region()]):
                fixture = self.fixture(stream=stream); fixture.receipt['regions'] = value
                self.rejected(fixture)
            fixture = self.fixture(stream=stream)
            fixture.rows.append(copy.deepcopy(fixture.rows[1]))
            fixture.rows[-1]['region']['allocation_protect'] = 2
            fixture.write()
            self.rejected(fixture, 'extra')

    def test_read_files_require_fixed_extent_name_and_identical_paused_pair(self):
        for key, value in (('bytes', 219), ('bytes', True), ('address', -1), ('address', 0xffffffff), ('sha256', '0' * 64)):
            fixture = self.fixture(); fixture.receipt['reads']['before']['primary'][key] = value
            self.rejected(fixture)
        fixture = self.fixture(); fixture.receipt['reads']['before']['primary']['path'] = fixture.order[1]['path']
        self.rejected(fixture, 'filename')
        fixture = self.fixture(); target = Path(fixture.order[0]['path']); target.write_bytes(b'changed')
        self.rejected(fixture, 'hash')

    def test_json_ambiguity_nonfinite_blank_truncated_and_extra_records_fail(self):
        for raw in (b'{"kind":"header","kind":"query"}\n', b'{"x":{"a":1,"\\u0061":2}}\n',
                    b'{"x":NaN}\n', b'{"x":Infinity}\n', b'{"x":1e999}\n', b'{}\n\n', b'\xff\n', b'[]\n'):
            fixture = self.fixture(); fixture.write(raw)
            result = self.rejected(fixture)
            self.assertTrue(result['raw_records'])
        fixture = self.fixture(); raw = Path(fixture.receipt['query_ledger']['path']).read_bytes()
        fixture.write(raw[:-1])
        self.assertEqual(len(self.rejected(fixture, 'truncated')['raw_records']), len(fixture.rows))
        fixture = self.fixture(); fixture.receipt['query_ledger']['records'] = True
        self.rejected(fixture, 'integer')

    def test_header_types_and_extra_fields_cannot_impersonate_contract(self):
        for key, value in (('page_size', 4096.0), ('mbi_bytes', 48.0), ('stream', 'cursor'), ('extra', True)):
            fixture = self.fixture(); fixture.rows[0][key] = value; fixture.write()
            self.rejected(fixture)

    def test_deep_json_failure_retains_malformed_and_all_following_rows(self):
        for opening, closing in ((b'[', b']'), (b'{"nested":', b'}')):
            with self.subTest(opening=opening):
                fixture = self.fixture()
                path = Path(fixture.receipt['query_ledger']['path'])
                malformed = b'{"nested":' + opening * 10000 + b'0' + closing * 10000 + b'}'
                raw = malformed + b'\n' + path.read_bytes()
                fixture.write(raw)
                fixture.receipt['query_ledger']['records'] = len(fixture.rows) + 1
                result = self.rejected(fixture, 'JSON nesting')
                self.assertEqual(len(result['raw_records']), len(fixture.rows) + 1)
                rejected = result['raw_records'][0]
                self.assertEqual(rejected['text'], malformed.decode('ascii'))
                self.assertIsNone(rejected['record'])
                self.assertIn('JSON nesting', rejected['parse_error'])
                self.assertEqual([row['record'] for row in result['raw_records'][1:]], fixture.rows)
                self.assertEqual(path.read_bytes(), raw)

    def test_excessive_row_count_retains_artifact_without_unbounded_diagnostics(self):
        fixture = self.fixture()
        raw = b'{}\n' * 65537
        fixture.write(raw)
        fixture.receipt['query_ledger']['records'] = 65537
        result = self.rejected(fixture, 'line count')
        self.assertEqual(result['raw_records'], [])
        artifact = fixture.receipt['query_ledger']
        self.assertEqual(result['ledger'], {key: artifact[key] for key in ('path', 'bytes', 'sha256')})
        self.assertEqual(Path(artifact['path']).read_bytes(), raw)

    def test_absolute_external_paths_and_hardlink_aliases_required(self):
        fixture = self.fixture()
        with self.assertRaises(tool.LedgerError):
            tool.audit_checkpoint_ledger(fixture.receipt, stream='primary', capture_dir=Path('relative'), expected_binding=fixture.binding)
        with patch.object(tool, 'ROOT', self.root):
            self.rejected(fixture, 'external')
        fixture = self.fixture()
        before, after = (Path(fixture.receipt['reads'][phase]['primary']['path']) for phase in ('before', 'after'))
        after.unlink()
        try: os.link(before, after)
        except OSError as error: self.skipTest('hardlinks unavailable: ' + str(error))
        self.rejected(fixture, 'alias')

    def test_ledger_artifact_and_bound_trace_or_source_drift_rejected(self):
        for target_kind in ('ledger', 'trace', 'source'):
            fixture = self.fixture(); original = tool._snapshot; calls = {}
            if target_kind == 'ledger': target = Path(fixture.receipt['query_ledger']['path'])
            elif target_kind == 'trace': target = Path(fixture.binding['trace']['path'])
            else: target = tool.ROOT / next(iter(tool.PINS))
            def drift(path):
                result = original(path)
                if Path(path) == target:
                    calls[str(path)] = calls.get(str(path), 0) + 1
                    if calls[str(path)] == 2:
                        return tool._Snapshot(result.path, result.data + b'changed', result.stamp)
                return result
            with patch.object(tool, '_snapshot', side_effect=drift):
                self.rejected(fixture, 'changed')
        fixture = self.fixture(); fixture.receipt['query_ledger']['sha256'] = '0' * 64
        self.rejected(fixture, 'hash')

    def test_helper_source_pin_checked_without_mutating_frozen_source(self):
        fixture = self.fixture(); pins = dict(tool.PINS); pins[next(iter(pins))] = '0' * 64
        with patch.object(tool, 'PINS', pins):
            self.rejected(fixture, 'dependency changed')

    def test_actual_oversized_file_rejected_before_reading_bytes(self):
        path = self.root / 'oversized-synthetic.bin'
        with path.open('wb') as stream:
            stream.truncate(64 * 1024 * 1024 + 1)
        with patch.object(Path, 'read_bytes', side_effect=AssertionError('unbounded file read')):
            with self.assertRaisesRegex(ValueError, 'actual file size'):
                tool._snapshot(path)


if __name__ == '__main__':
    unittest.main(verbosity=2)
