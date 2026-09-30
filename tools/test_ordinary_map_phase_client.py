"""Portable fake-host phase protocol tests; no process, debugger or game input."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import ordinary_map_phase_client as tool
import ordinary_map_pause_client as pause

CONTROLLER = 'c' * 64
BINDING = 'b' * 64


class FakeHost:
    def __init__(self, directory, identity=None):
        self.directory = directory
        self.session = pause.prepare_control(directory)
        self.identity = identity or dict(pid=4321, creation_filetime=134349000000000000,
                                        image_base=0x400000, candidate_sha256='a'*64)
        self.tick, self.sequence, self.action_index = 1000, 0, 0
        self.alive, self.ignore, self.ignore_completion = True, False, False
        self.lease = ''
        self.pending = None
        self.publish_hook = self.executing_hook = None
        self.requests = []
        self.data = dict(
            schema=tool.SCHEMA, session_id=self.session, request_seq=0, status='ready', lease_id='',
            pid=self.identity['pid'], primary_tid=789, creation_filetime=self.identity['creation_filetime'],
            image_base=self.identity['image_base'], deadline_tick_ms=0, paused=False, phase='ready',
            controller_sha256=CONTROLLER, root_esp=0, held_esp=0, held_eip=0,
            human_entry_seen=False, postpoll_seen=False, action_index=0, capture_index=-1,
            binding_sha256='', target_x=0, target_y=0, dispatch_seen=False, dispatch_eip=0,
            dispatch_esp=0, dispatch_return=0, predicate_observed=False, predicate_value=0,
            return_seen=False, return_eip=0, return_esp=0)
        assert set(self.data) == tool.ACK_KEYS
        self.publish()

    @property
    def delta(self):
        return self.identity['image_base'] - 0x400000

    @property
    def ack_path(self):
        return self.directory/'phase-ack.json'

    def publish(self):
        data = deepcopy(self.data)
        if self.publish_hook:
            self.publish_hook(data)
        assert set(data) == tool.ACK_KEYS
        self.ack_path.write_text(json.dumps(data), encoding='ascii')

    def held(self, lease, phase):
        self.lease = lease
        self.data.update(status='held', lease_id=lease, paused=True, phase=phase,
                         deadline_tick_ms=self.tick+20000, root_esp=0x180000, held_esp=0x180000-28,
                         held_eip=0x40B233+self.delta, human_entry_seen=True, postpoll_seen=True,
                         request_seq=self.sequence, action_index=self.action_index,
                         capture_index=self.action_index)
        self.publish()

    def unheld(self, status):
        self.data.update(status=status, lease_id='', paused=False, phase=status,
                         deadline_tick_ms=0, request_seq=self.sequence)
        self.publish()

    def advance(self, seconds):
        self.tick += max(1, int(seconds*1000))
        if not self.alive or self.ignore:
            return
        if self.pending is not None:
            if self.ignore_completion:
                return
            successor, x, y, binding = self.pending
            self.pending = None
            self.action_index += 1
            held_esp = 0x180000-28
            self.data.update(binding_sha256=binding, target_x=x, target_y=y,
                             dispatch_seen=True, dispatch_eip=0x4084A0+self.delta,
                             dispatch_esp=held_esp-4, dispatch_return=0x40B238+self.delta,
                             predicate_observed=True, predicate_value=1, return_seen=True,
                             return_eip=0x40B238+self.delta, return_esp=held_esp)
            self.held(successor, 'predispatch-after')
            return
        path = self.directory/'phase-request.txt'
        if not path.exists():
            return
        raw = path.read_bytes()
        assert raw.endswith(b'\n') and raw.count(b'\n') == 1 and len(raw) <= 256
        values = raw.decode('ascii').strip().split(' ')
        version, session, sequence, operation, *parts = values
        assert version == 'CLASH_PHASE_V1' and session == self.session
        sequence = int(sequence)
        if sequence == self.sequence:
            return
        assert sequence == self.sequence+1
        self.sequence = sequence
        self.requests.append(values)
        if operation == 'acquire':
            assert len(parts) == 1
            self.held(parts[0], 'predispatch-before')
        elif operation == 'click':
            assert len(parts) == 5 and parts[0] == self.lease
            self.pending = (parts[1], int(parts[2]), int(parts[3]), parts[4])
            self.unheld('executing')
            if self.executing_hook:
                self.executing_hook()
        else:
            assert operation == 'release' and len(parts) == 1 and parts[0] == self.lease
            self.lease = ''
            self.unheld('released')

    def client(self, **changes):
        arguments = dict(identity=self.identity, controller_sha256=CONTROLLER,
                         check_owner=lambda: deepcopy(self.identity), host_alive=lambda: self.alive,
                         clock_ms=lambda: self.tick, sleep=self.advance)
        arguments.update(changes)
        return tool.PhaseClient(self.directory, **arguments)


class PhaseClientTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='clash-phase-fixture-')
        self.addCleanup(temporary.cleanup)
        self.host = FakeHost(Path(temporary.name)/'control')
        self.client = self.host.client()

    def test_ready_acquire_click_successor_release_are_bound_monotonic_transitions(self):
        self.client.wait_ready()
        before = self.client.acquire()
        self.assertIsNone(self.client.check_lease(before))
        after = self.client.click(before, [256, 240], BINDING)
        self.assertNotEqual(before['lease_id'], after['lease_id'])
        self.assertEqual(after, dict(schema=tool.LEASE_SCHEMA, lease_id=self.host.lease,
                                     paused=True, **self.host.identity))
        with self.assertRaisesRegex(tool.LeaseError, 'inactive'):
            self.client.check_lease(before)
        result = tool.verify_dispatch(self.client.receipts[-1], self.host.identity, BINDING)
        self.assertTrue(result['passed'])
        self.assertIn('not OS or manual input', result['proof_scope'])
        self.client.release(after)
        self.assertEqual([row['request_seq'] for row in self.client.receipts], [0, 1, 2, 3])
        self.assertEqual([row['status'] for row in self.client.receipts], ['ready', 'held', 'held', 'released'])
        self.assertEqual([row[3] for row in self.host.requests], ['acquire', 'click', 'release'])
        self.assertEqual(self.host.requests[1][4:], [before['lease_id'], after['lease_id'], '256', '240', BINDING])
        self.assertEqual(list(self.host.directory.glob('*.tmp')), [])
        with self.assertRaises(tool.LeaseError):
            self.client.check_lease(after)

    def test_old_lease_is_invalid_while_native_action_is_executing(self):
        before = self.client.acquire()
        calls = []
        def executing():
            self.assertIsNone(self.client._active)
            self.assertIsNone(self.client._active_sequence)
            self.assertEqual(self.client.ack()['status'], 'executing')
            with self.assertRaisesRegex(tool.LeaseError, 'inactive'):
                self.client.check_lease(before)
            calls.append('executing')
        self.host.executing_hook = executing
        after = self.client.click(before, (256, 240), BINDING)
        self.assertEqual(calls, ['executing'])
        self.assertIsNone(self.client.check_lease(after))
        self.client.release(after)

    def test_nested_acquire_and_late_ready_do_not_replace_active_lease(self):
        lease = self.client.acquire()
        with self.assertRaisesRegex(tool.LeaseError, 'Nested'):
            self.client.acquire()
        with self.assertRaisesRegex(tool.LeaseError, 'session start'):
            self.client.wait_ready()
        self.client.check_lease(lease)
        self.client.release(lease)

    def test_sequential_reads_use_fresh_tokens_and_monotonic_sequences(self):
        first = self.client.acquire()
        self.client.release(first)
        second = self.client.acquire()
        self.assertNotEqual(first['lease_id'], second['lease_id'])
        self.client.release(second)
        self.assertEqual([row['request_seq'] for row in self.client.receipts], [1, 2, 3, 4])

    def test_changed_lease_or_owner_and_host_exit_reject_reads(self):
        lease = self.client.acquire()
        for field, value in [('pid', 1), ('candidate_sha256', 'd'*64), ('lease_id', '0'*32), ('paused', False)]:
            with self.subTest(field=field), self.assertRaises(tool.LeaseError):
                self.client.check_lease(dict(lease, **{field: value}))
        self.host.alive = False
        with self.assertRaisesRegex(tool.LeaseError, 'host exited'):
            self.client.check_lease(lease)
        self.host.alive = True
        self.host.identity['creation_filetime'] += 1
        with self.assertRaisesRegex(tool.LeaseError, 'identity changed'):
            self.client.check_lease(lease)

    def test_local_invalid_points_and_bindings_send_no_action(self):
        lease = self.client.acquire()
        cases = [(point, BINDING) for point in (None, '1,2', [1], [1, 2, 3], [True, 2],
                                              [1.5, 2], [-1, 2], [1, 4096])]
        cases += [([256, 240], digest) for digest in ('', 'B'*64, 'b'*63, 'b'*64+' ', None)]
        for point, digest in cases:
            with self.subTest(point=point, digest=digest), self.assertRaises(tool.LeaseError):
                self.client.click(lease, point, digest)
        self.assertEqual(self.client.sequence, 1)
        self.assertEqual(len(self.host.requests), 1)
        self.client.check_lease(lease)
        self.client.release(lease)

    def test_ack_requires_exact_schema_controller_and_target_identity(self):
        lease = self.client.acquire()
        original = self.host.ack_path.read_text()
        changes = [('schema', 'wrong'), ('controller_sha256', 'd'*64), ('session_id', '0'*32),
                   ('pid', 1), ('creation_filetime', 1), ('image_base', 0x500000), ('primary_tid', 0),
                   ('request_seq', True), ('paused', 1), ('postpoll_seen', False), ('human_entry_seen', False),
                   ('held_eip', 0x40B0D4), ('root_esp', 0), ('root_esp', 0x180001),
                   ('root_esp', 0x7FFE0000), ('held_esp', 0), ('held_esp', 0xffff), ('capture_index', -2),
                   ('target_x', True), ('binding_sha256', 'invalid'), ('request_seq', 1 << 64),
                   ('lease_id', 'bad'), ('phase', 'predispatch-after-unknown'), ('unexpected', 1)]
        for field, value in changes:
            with self.subTest(field=field):
                data = json.loads(original)
                data[field] = value
                self.host.ack_path.write_text(json.dumps(data), encoding='ascii')
                with self.assertRaises(tool.LeaseError):
                    self.client.check_lease(lease)
        data = json.loads(original)
        del data['return_esp']
        self.host.ack_path.write_text(json.dumps(data), encoding='ascii')
        with self.assertRaises(tool.LeaseError):
            self.client.ack()
        self.host.ack_path.write_text(original, encoding='ascii')
        self.client.release(lease)

    def test_duplicate_oversized_and_link_acknowledgments_reject(self):
        original = self.host.ack_path.read_text()
        self.host.ack_path.write_text(original[:-1]+',"pid":4321}', encoding='ascii')
        with self.assertRaisesRegex(tool.LeaseError, 'Duplicate'):
            self.client.wait_ready()
        self.host.ack_path.write_text(' '*4097, encoding='ascii')
        with self.assertRaisesRegex(tool.LeaseError, 'acknowledgment file'):
            self.client.ack()
        self.host.ack_path.write_text(original, encoding='ascii')
        with patch.object(Path, 'is_symlink', return_value=True):
            with self.assertRaisesRegex(tool.LeaseError, 'acknowledgment file'):
                self.client.ack()

    def test_ready_and_unheld_acknowledgments_reject_contradictions(self):
        original = self.host.ack_path.read_text()
        for field, value in [('request_seq', 1), ('lease_id', '0'*32), ('paused', True),
                             ('deadline_tick_ms', 20000), ('phase', 'held'), ('status', 'unknown')]:
            with self.subTest(field=field):
                data = json.loads(original)
                data[field] = value
                self.host.ack_path.write_text(json.dumps(data), encoding='ascii')
                with self.assertRaises(tool.LeaseError):
                    self.client.ack()
        self.host.ack_path.write_text(original, encoding='ascii')

    def test_no_host_response_poisoned_acquisition_cannot_be_retried(self):
        self.host.ignore = True
        with self.assertRaisesRegex(tool.LeaseError, 'Timed out'):
            self.client.acquire(timeout_ms=50)
        self.assertTrue(self.client._poisoned)
        self.assertIsNone(self.client._active)
        self.assertEqual(self.host.sequence, 0)
        with self.assertRaisesRegex(tool.LeaseError, 'cannot be reused'):
            self.client.acquire()

    def test_action_timeout_keeps_old_and_successor_leases_inactive(self):
        lease = self.client.acquire()
        self.host.ignore_completion = True
        with self.assertRaisesRegex(tool.LeaseError, 'Timed out'):
            self.client.click(lease, [256, 240], BINDING, timeout_ms=50)
        self.assertTrue(self.client._poisoned)
        self.assertIsNone(self.client._active)
        self.assertEqual(self.client.receipts[-1]['phase'], 'predispatch-before')
        with self.assertRaises(tool.LeaseError):
            self.client.check_lease(lease)

    def test_release_timeout_invalidates_lease_before_waiting(self):
        lease = self.client.acquire()
        self.host.ignore = True
        with self.assertRaisesRegex(tool.LeaseError, 'Timed out'):
            self.client.release(lease, timeout_ms=50)
        self.assertTrue(self.client._poisoned)
        self.assertIsNone(self.client._active)

    def test_expired_lease_cannot_release_and_session_is_poisoned(self):
        lease = self.client.acquire()
        self.host.tick += 20001
        with self.assertRaisesRegex(tool.LeaseError, 'expired'):
            self.client.release(lease)
        self.assertEqual(self.host.sequence, 1)
        self.assertTrue(self.client._poisoned)

    def test_lease_deadline_must_be_current_and_within_twenty_seconds(self):
        for deadline in ('expired', 'too_long'):
            with self.subTest(deadline=deadline):
                self.setUp()
                def mutate(data):
                    if data['status'] == 'held':
                        data['deadline_tick_ms'] = self.host.tick if deadline == 'expired' else self.host.tick+20001
                self.host.publish_hook = mutate
                with self.assertRaisesRegex(tool.LeaseError, 'expired or exceeds'):
                    self.client.acquire()
                self.assertTrue(self.client._poisoned)
                self.assertIsNone(self.client._active)

    def test_wrong_completion_binding_point_action_and_successor_reject(self):
        changes = [('binding_sha256', 'd'*64), ('target_x', 255), ('target_y', 241),
                   ('action_index', 0), ('action_index', 2), ('lease_id', '0'*32),
                   ('request_seq', 3), ('phase', 'predispatch-before')]
        for field, value in changes:
            with self.subTest(field=field, value=value):
                self.setUp()
                before = self.client.acquire()
                def mutate(data):
                    if data['phase'] == 'predispatch-after':
                        data[field] = value
                self.host.publish_hook = mutate
                with self.assertRaises(tool.LeaseError):
                    self.client.click(before, [256, 240], BINDING)
                self.assertTrue(self.client._poisoned)
                self.assertIsNone(self.client._active)

    def test_acquisition_rejects_post_action_phase(self):
        def mutate(data):
            if data['status'] == 'held':
                data['phase'] = 'predispatch-after'
        self.host.publish_hook = mutate
        with self.assertRaisesRegex(tool.LeaseError, 'before native input'):
            self.client.acquire()

    def test_bad_controller_hash_is_rejected_before_protocol_use(self):
        for digest in ('', 'C'*64, 'c'*63, None):
            with self.subTest(digest=digest), self.assertRaises(tool.LeaseError):
                self.host.client(controller_sha256=digest)

    def test_context_read_exception_releases_the_held_phase(self):
        with self.assertRaisesRegex(ValueError, 'read failed'):
            with self.client.paused():
                raise ValueError('read failed')
        self.assertEqual(self.client.receipts[-1]['status'], 'released')

    def test_relocated_native_call_addresses_are_bound_to_identity(self):
        self.host.identity['image_base'] = 0x1400000
        self.host.data['image_base'] = 0x1400000
        self.host.publish()
        self.client = self.host.client()
        lease = self.client.acquire()
        successor = self.client.click(lease, [256, 240], BINDING)
        ack = self.client.receipts[-1]
        self.assertTrue(tool.verify_dispatch(ack, self.host.identity, BINDING)['passed'])
        broken = dict(ack, dispatch_return=0x40B238)
        with self.assertRaises(tool.LeaseError):
            tool.verify_dispatch(broken, self.host.identity, BINDING)
        self.client.release(successor)

    def test_verify_dispatch_rejects_wrong_target_caller_stack_and_native_predicate_zero(self):
        lease = self.client.acquire()
        successor = self.client.click(lease, [256, 240], BINDING)
        ack = self.client.receipts[-1]
        changes = [('pid', 1), ('creation_filetime', 1), ('image_base', 0x500000),
                   ('binding_sha256', 'd'*64), ('human_entry_seen', False), ('postpoll_seen', False),
                   ('dispatch_seen', False), ('dispatch_seen', 1), ('predicate_observed', False),
                   ('predicate_value', 0), ('predicate_value', True),
                   ('return_seen', False), ('dispatch_eip', 0x408030), ('dispatch_return', 0x406FA1),
                   ('return_eip', 0x406FA1), ('dispatch_esp', ack['dispatch_esp']+4),
                   ('return_esp', ack['return_esp']+4), ('held_esp', ack['held_esp']+4),
                   ('held_eip', 0x40B0D4)]
        for field, value in changes:
            with self.subTest(field=field), self.assertRaises(tool.LeaseError):
                tool.verify_dispatch(dict(ack, **{field: value}), self.host.identity, BINDING)
        shifted = dict(ack, held_esp=ack['held_esp']+64, dispatch_esp=ack['dispatch_esp']+64,
                       return_esp=ack['return_esp']+64)
        with self.assertRaises(tool.LeaseError):
            tool.verify_dispatch(shifted, self.host.identity, BINDING)
        for root_esp in (0x10000, 0x180001, 0x7FFE001C):
            invalid = dict(ack, root_esp=root_esp, held_esp=root_esp-28,
                           dispatch_esp=root_esp-32, return_esp=root_esp-28)
            with self.subTest(root_esp=root_esp), self.assertRaises(tool.LeaseError):
                tool.verify_dispatch(invalid, self.host.identity, BINDING)
        self.client.release(successor)

    def test_real_decoder_and_planner_consume_the_held_phase_without_inferring_selection(self):
        import ordinary_map_input_plan as planner
        import ordinary_map_observation as decoder
        from test_ordinary_map_observation import fixture
        memory, candidate, identity, _ = fixture()
        self.assertEqual(identity, self.host.identity)
        lease = self.client.acquire()
        before = decoder.observe(memory.read, candidate=candidate, identity=identity, sequence=1,
                                 lease=lease, check_lease=self.client.check_lease, stack_indices=(13,))
        plan = planner.plan_input(before['snapshot'], candidate)
        fresh = decoder.observe(memory.read, candidate=candidate, identity=identity, sequence=2,
                                lease=lease, check_lease=self.client.check_lease, stack_indices=(13,))
        planner.revalidate_before_click(plan, fresh['snapshot'], 'select')
        binding = planner.digest(dict(plan=plan, observation=fresh['receipt']))
        successor = self.client.click(lease, plan['selection']['point'], binding)
        self.assertTrue(tool.verify_dispatch(self.client.receipts[-1], identity, binding)['passed'])
        after = decoder.observe(memory.read, candidate=candidate, identity=identity, sequence=3,
                                lease=successor, check_lease=self.client.check_lease, stack_indices=(13,))
        self.assertEqual(after['snapshot']['context']['selected_stack'], -1)
        with self.assertRaises(planner.PlanError):
            planner.verify_selection(plan, before['snapshot'], after['snapshot'])
        self.client.release(successor)


if __name__ == '__main__':
    unittest.main(verbosity=2)
