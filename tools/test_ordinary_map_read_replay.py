"""Small in-memory synthetic raw-read fixtures; no files, game or runtime proof."""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import unittest
from unittest.mock import patch

import ordinary_map_observation as observer
import ordinary_map_phase_client as phase_client
import ordinary_map_read_replay as tool
from test_ordinary_map_observation import fixture


def case(*, image_base=0x400000, indices=(13,)):
    memory, candidate, identity, lease = fixture(image_base=image_base)
    lease['lease_id'] = 'b' * 32
    phase = {name: 0 for name in phase_client.INT_KEYS}
    phase.update({name: False for name in phase_client.BOOL_KEYS})
    phase.update(schema=phase_client.SCHEMA, session_id='c' * 32,
        status='held', lease_id=lease['lease_id'], phase='predispatch-before',
        controller_sha256='d' * 64, binding_sha256='',
        **{name: identity[name] for name in ('pid', 'creation_filetime', 'image_base')})
    phase.update(primary_tid=4567, request_seq=1, deadline_tick_ms=234567,
        paused=True, human_entry_seen=True, postpoll_seen=True,
        root_esp=0x180000, held_esp=0x180000 - 28,
        held_eip=0x40B233 + image_base - 0x400000, capture_index=100)
    assert set(phase) == phase_client.ACK_KEYS
    checks = []
    def check(value):
        checks.append((len(memory.calls), deepcopy(value)))
        assert value == lease
    arguments = dict(candidate=candidate, identity=identity, sequence=1,
        lease=lease, check_lease=check, phase=phase,
        canonical_probe_sha256='e' * 64, source_hashes=tool.current_source_hashes(),
        stack_indices=indices)
    return memory, arguments, checks


def captured(*, image_base=0x400000, indices=(13,)):
    memory, arguments, checks = case(image_base=image_base, indices=indices)
    value = tool.capture_observation(memory.read, **arguments)
    return memory, arguments, checks, value


def replay(value, *, raw=None, observation=None, binding=None, reseal=False):
    raw = deepcopy(value['raw_capture']) if raw is None else raw
    observation = deepcopy(value['observation']) if observation is None else observation
    return tool.replay_observation(raw, observation,
        expected_binding=deepcopy(value['raw_capture']['binding']) if binding is None else binding,
        expected_capture_sha256=tool.digest(raw) if reseal else value['raw_capture_sha256'],
        expected_observation_sha256=tool.digest(observation) if reseal else value['observation_sha256'])


class RawReadReplayTests(unittest.TestCase):
    def assertRejected(self, result):
        self.assertFalse(result['passed'])
        self.assertFalse(result['raw_replay_passed'])
        self.assertTrue(result['failures'])
        self.assertTrue(all(result[name] is False for name in tool.FALSE_CLAIMS))

    def test_default_observation_and_native_calls_are_unchanged(self):
        memory, arguments, checks, value = captured()
        baseline_memory, baseline_arguments, baseline_checks = case()
        baseline = observer.observe(baseline_memory.read, **{name: baseline_arguments[name]
            for name in ('candidate', 'identity', 'sequence', 'lease', 'check_lease', 'stack_indices')})
        self.assertEqual(value['observation'], baseline)
        self.assertEqual(memory.calls, baseline_memory.calls)
        self.assertEqual(checks, baseline_checks)
        self.assertEqual(set(baseline), {'snapshot', 'receipt'})

    def test_every_read_and_successful_lease_check_is_retained(self):
        memory, _, checks, value = captured()
        events = value['raw_capture']['events']
        reads = [row for row in events if row['kind'] == 'read']
        self.assertEqual([(row['address'], row['size']) for row in reads], memory.calls)
        self.assertEqual([row['ordinal'] for row in reads], list(range(1, len(reads) + 1)))
        self.assertEqual({row['phase'] for row in reads}, tool.READ_PHASES)
        self.assertEqual([row['phase'] for row in events if row['kind'] == 'lease'],
                         ['before_initial', 'before_rereads', 'after_rereads'])
        self.assertEqual(len(checks), 3)
        self.assertEqual(sum(row['size'] for row in reads), value['observation']['receipt']['total_read_bytes'])
        for row in reads:
            self.assertEqual(sha256(bytes.fromhex(row['data_hex'])).hexdigest(), row['sha256'])
        self.assertEqual(observer.MAX_UNIQUE_BYTES, 600_000)
        self.assertEqual(observer.MAX_TOTAL_BYTES, 2_000_000)
        self.assertEqual(observer.MAX_READ_CALLS, 2_000)
        self.assertEqual(observer.MAX_SINGLE_READ, 362_500)

    def test_replay_recomputes_state_at_both_bases_without_runtime_claims(self):
        for image_base, indices in ((0x400000, (13,)), (0x500000, (13,)), (0x400000, None)):
            with self.subTest(image_base=image_base, all_stacks=indices is None):
                value = captured(image_base=image_base, indices=indices)[3]
                result = replay(value)
                self.assertTrue(result['raw_replay_passed'], result)
                self.assertTrue(result['recorded_lease_consistency'])
                self.assertTrue(result['candidate_binding_matched'])
                self.assertTrue(result['phase_binding_matched'])
                self.assertFalse(result['passed'])
                self.assertTrue(all(result[name] is False for name in tool.FALSE_CLAIMS))
                self.assertEqual(result['unique_read_bytes'], value['observation']['receipt']['unique_read_bytes'])

    def test_canonical_serialization_has_no_writes_and_rejects_duplicate_keys(self):
        value = captured()[3]
        encoded = tool.canonical_bytes(value['raw_capture'])
        self.assertEqual(tool.decode_capture(encoded), value['raw_capture'])
        self.assertEqual(sha256(encoded).hexdigest(), value['raw_capture_sha256'])
        for data in (b'{"schema":1,"schema":2}', b'{"bad":NaN}', b'{"bad":Infinity}',
                     encoded + b'\n', b'{}\xff'):
            with self.subTest(data=data[:40]), self.assertRaises(tool.ReplayError):
                tool.decode_capture(data)
        for data in (b'', bytearray(b'{}')):
            with self.assertRaises(tool.ReplayError):
                tool.decode_capture(data)
        for data in (b'[' * 5000 + b'0' + b']' * 5000,
                     b'[' * 65 + b'0' + b']' * 65,
                     b' ' * (tool.MAX_CAPTURE_BYTES + 1), b'{"value":1e999}'):
            with self.subTest(malformed_size=len(data)), self.assertRaises(tool.ReplayError):
                tool.decode_capture(data)
        with patch.object(tool, 'MAX_JSON_NODES', 5), self.assertRaises(tool.ReplayError):
            tool.canonical_bytes([0] * 6)

    def test_rehashed_mutations_do_not_replace_the_independent_artifact_hash(self):
        value = captured()[3]
        raw = deepcopy(value['raw_capture'])
        row = next(row for row in raw['events'] if row['kind'] == 'read')
        data = bytearray.fromhex(row['data_hex'])
        data[-1] ^= 1
        row.update(data_hex=data.hex(), sha256=sha256(data).hexdigest())
        self.assertRejected(replay(value, raw=raw))
        altered = deepcopy(value['observation'])
        altered['snapshot']['world']['scroll_x'] += 1
        altered['receipt']['observation_sha256'] = tool.digest(altered['snapshot'])
        self.assertRejected(replay(value, observation=altered))

    def test_changed_decoded_state_and_receipt_fail_even_with_resealed_fixture_hashes(self):
        value = captured()[3]
        for mutation in ('state', 'receipt', 'purposes', 'count', 'numeric-type', 'boolean-type'):
            with self.subTest(mutation=mutation):
                observation = deepcopy(value['observation'])
                if mutation == 'state':
                    observation['snapshot']['world']['scroll_x'] += 1
                elif mutation == 'receipt':
                    observation['receipt']['added_selected_indices'] = [14]
                elif mutation == 'purposes':
                    observation['receipt']['read_set'][0]['purposes'] = ['invented purpose']
                elif mutation == 'count':
                    observation['receipt']['read_calls'] += 1
                elif mutation == 'numeric-type':
                    observation['snapshot']['sequence'] = 1.0
                else:
                    observation['snapshot']['sequence'] = True
                raw = deepcopy(value['raw_capture'])
                observation['receipt']['observation_sha256'] = tool.digest(observation['snapshot'])
                raw['observation_sha256'] = tool.digest(observation)
                raw['events'][-1].update(snapshot_sha256=tool.digest(observation['snapshot']),
                    receipt_sha256=tool.digest(observation['receipt']))
                self.assertRejected(replay(value, raw=raw, observation=observation, reseal=True))

    def test_missing_extra_reordered_aliased_and_inconsistent_reads_fail(self):
        value = captured()[3]
        for mutation in ('missing', 'extra', 'reorder', 'alias', 'phase', 'reread', 'lease', 'lease-order', 'unknown-key'):
            with self.subTest(mutation=mutation):
                raw = deepcopy(value['raw_capture'])
                events = raw['events']
                positions = [index for index, row in enumerate(events) if row['kind'] == 'read']
                if mutation == 'missing':
                    events.pop(positions[-1])
                elif mutation == 'extra':
                    events.insert(positions[0], deepcopy(events[positions[0]]))
                elif mutation == 'reorder':
                    events[positions[0]], events[positions[1]] = events[positions[1]], events[positions[0]]
                elif mutation == 'alias':
                    events[positions[0]]['address'] += 1
                elif mutation == 'phase':
                    events[positions[0]]['phase'] = 'complete'
                elif mutation == 'reread':
                    row = next(row for row in events if row['kind'] == 'read' and row['phase'] == 'anchor_first')
                    data = bytearray.fromhex(row['data_hex'])
                    data[-1] ^= 1
                    row.update(data_hex=data.hex(), sha256=sha256(data).hexdigest())
                elif mutation == 'lease':
                    events[1]['lease']['creation_filetime'] += 1
                elif mutation == 'lease-order':
                    events[1]['phase'] = 'after_rereads'
                else:
                    events[positions[0]]['unexpected'] = False
                ordinal = 0
                for row in events:
                    if row['kind'] == 'read':
                        ordinal += 1
                        row['ordinal'] = ordinal
                self.assertRejected(replay(value, raw=raw, reseal=True))

    def test_authenticated_candidate_process_phase_probe_and_sources_cannot_be_rebound(self):
        value = captured()[3]
        for mutation in ('candidate', 'pid', 'creation', 'base', 'tid', 'session', 'controller', 'probe', 'source', 'phase', 'sequence'):
            with self.subTest(mutation=mutation):
                binding = deepcopy(value['raw_capture']['binding'])
                if mutation == 'candidate':
                    binding['candidate']['sha256'] = '1' * 64
                    binding['identity']['candidate_sha256'] = '1' * 64
                    binding['lease']['candidate_sha256'] = '1' * 64
                elif mutation in ('pid', 'creation', 'base'):
                    name = {'pid': 'pid', 'creation': 'creation_filetime', 'base': 'image_base'}[mutation]
                    increment = 0x10000 if mutation == 'base' else 1
                    for item in ('identity', 'lease', 'phase'):
                        binding[item][name] += increment
                    if mutation == 'base':
                        binding['phase']['held_eip'] += increment
                elif mutation == 'tid':
                    binding['phase']['primary_tid'] += 1
                elif mutation == 'session':
                    binding['phase']['session_id'] = '2' * 32
                elif mutation == 'controller':
                    binding['phase']['controller_sha256'] = '2' * 64
                elif mutation == 'probe':
                    binding['canonical_probe_sha256'] = '2' * 64
                elif mutation == 'source':
                    binding['source_hashes'][tool.SOURCE_PATHS[0]] = '2' * 64
                elif mutation == 'phase':
                    binding['phase']['phase'] = 'predispatch-after'
                else:
                    binding['sequence'] = True
                self.assertRejected(replay(value, binding=binding))

    def test_all_loaded_dependency_paths_and_class_aliases_are_fixed(self):
        for module in (tool, observer, tool.planner, phase_client, tool.pause_client,
                       tool.geometry, tool.army_geometry):
            with self.subTest(module=module.__name__), patch.object(module, '__file__',
                    str(tool.ROOT / 'foreign-checkout' / Path(module.__file__).name)), self.assertRaises(tool.ReplayError):
                tool.current_source_hashes()
        for module, name in ((observer, 'planner'), (tool.planner, 'FramedViewport'),
                             (tool.planner, 'Rect'), (tool.planner, 'FramedArmyViewport'),
                             (tool.army_geometry, 'FramedViewport'), (tool.army_geometry, 'Rect'),
                             (phase_client, 'PauseClient')):
            with self.subTest(alias=name), patch.object(module, name, object()), self.assertRaises(tool.ReplayError):
                tool.current_source_hashes()
        with patch.object(tool, 'ROOT', tool.ROOT / 'foreign-checkout'), self.assertRaises(tool.ReplayError):
            tool.current_source_hashes()

    def test_source_snapshot_rechecks_bytes_and_capture_rechecks_after_reads(self):
        original = Path.read_bytes
        count = 0
        def changed_second_read(path):
            nonlocal count
            data = original(path)
            if path == tool.ROOT / tool.SOURCE_PATHS[1]:
                count += 1
                if count == 2:
                    return data + b'# synthetic changed source\n'
            return data
        with patch.object(Path, 'read_bytes', changed_second_read), self.assertRaises(tool.ReplayError):
            tool.current_source_hashes()
        memory, arguments, _ = case()
        started = False
        def mark_started(memory, address, size):
            nonlocal started
            started = True
        memory.hook = mark_started
        def changed_after_capture(path):
            data = original(path)
            return data + b'# synthetic changed source\n' if started and path == tool.ROOT / tool.SOURCE_PATHS[1] else data
        with patch.object(Path, 'read_bytes', changed_after_capture), self.assertRaises(tool.CaptureFailure) as failure:
            tool.capture_observation(memory.read, **arguments)
        self.assertFalse(failure.exception.raw_diagnostics['observation_complete'])
        self.assertEqual(failure.exception.raw_diagnostics['schema'], tool.PARTIAL_SCHEMA)

    def test_failed_consistency_reads_remain_partial_diagnostics(self):
        memory, arguments, _ = case()
        seen = 0
        def change_reread(memory, address, size):
            nonlocal seen
            if address == 0x5202E0:
                seen += 1
                if seen == 2:
                    memory.pack(address + 12, 'I', 1)
        memory.hook = change_reread
        with self.assertRaises(tool.CaptureFailure) as failure:
            tool.capture_observation(memory.read, **arguments)
        partial = failure.exception.raw_diagnostics
        self.assertEqual(partial['schema'], tool.PARTIAL_SCHEMA)
        self.assertFalse(partial['observation_complete'])
        self.assertEqual(partial['events'][-1]['kind'], 'read')
        self.assertEqual(partial['events'][-1]['phase'], 'anchor_first')
        self.assertTrue(all(partial[name] is False for name in tool.FALSE_CLAIMS))
        value = captured()[3]
        self.assertRejected(replay(value, raw=partial, reseal=True))

    def test_forbidden_proof_and_wrong_types_never_pass(self):
        value = captured()[3]
        for field in tool.FALSE_CLAIMS:
            for replacement in (True, 0):
                raw = deepcopy(value['raw_capture'])
                raw[field] = replacement
                self.assertRejected(replay(value, raw=raw, reseal=True))
        for replacement in (True, 1.0):
            raw = deepcopy(value['raw_capture'])
            next(row for row in raw['events'] if row['kind'] == 'read')['ordinal'] = replacement
            self.assertRejected(replay(value, raw=raw, reseal=True))
        for invalid in (float('nan'), float('inf'), (1, 2), {'key': bytearray(b'bad')}):
            with self.assertRaises(tool.ReplayError):
                tool.canonical_bytes(invalid)

    def test_sink_is_synchronous_and_does_not_mutate_observer_inputs(self):
        memory, arguments, _ = case()
        observed = []
        def sink(event):
            observed.append(event['kind'])
            event.clear()
        result = observer.observe(memory.read, raw_sink=sink, **{name: arguments[name]
            for name in ('candidate', 'identity', 'sequence', 'lease', 'check_lease', 'stack_indices')})
        self.assertEqual(result['snapshot']['sequence'], 1)
        self.assertEqual(observed[0], 'context')
        async def async_sink(event):
            return None
        for invalid in (async_sink, lambda event: True, False):
            memory, arguments, _ = case()
            with self.assertRaises(observer.ObservationError):
                observer.observe(memory.read, raw_sink=invalid, **{name: arguments[name]
                    for name in ('candidate', 'identity', 'sequence', 'lease', 'check_lease', 'stack_indices')})

    def test_existing_read_limits_apply_to_capture_and_replay(self):
        for constant, limit in (('MAX_UNIQUE_BYTES', 1), ('MAX_TOTAL_BYTES', 1),
                                ('MAX_READ_CALLS', 1), ('MAX_SINGLE_READ', 1)):
            memory, arguments, _ = case()
            with self.subTest(constant=constant), patch.object(observer, constant, limit), self.assertRaises(observer.ObservationError):
                tool.capture_observation(memory.read, **arguments)
        value = captured()[3]
        for constant, limit in (('MAX_TOTAL_BYTES', 1), ('MAX_READ_CALLS', 1), ('MAX_SINGLE_READ', 1)):
            with self.subTest(replay_constant=constant), patch.object(observer, constant, limit):
                self.assertRejected(replay(value))


if __name__ == '__main__':
    unittest.main()
