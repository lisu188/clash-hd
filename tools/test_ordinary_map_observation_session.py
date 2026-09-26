"""Portable integration of real decoder/client APIs over synthetic bytes."""
from pathlib import Path
import tempfile
import unittest

import ordinary_map_input_plan as planner
import ordinary_map_observation as decoder
import ordinary_map_observation_session as tool
from ordinary_map_pause_client import LeaseError
from test_ordinary_map_pause_client import FakeHost
from test_ordinary_map_observation import fixture


class SessionTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='clash-observation-session-')
        self.addCleanup(temporary.cleanup)
        self.host = FakeHost(Path(temporary.name)/'control')
        self.client = self.host.client()
        self.memory, self.candidate, _, _ = fixture()
        self.session = tool.ObservationSession(
            self.client, self.memory.read, candidate=self.candidate, stack_indices=[13])

    def test_decoded_plan_has_matching_pause_resume_and_expired_authority(self):
        result = self.session.read()
        plan = planner.plan_input(result['snapshot'], self.candidate)
        self.assertEqual(plan['selection']['stack_index'], 13)
        self.assertEqual(plan['movement']['destination'], [11, 11])
        transaction = result['host_transaction']
        self.assertEqual(transaction['paused']['status'], 'paused')
        self.assertEqual(transaction['resumed']['status'], 'resumed')
        self.assertEqual(transaction['paused']['lease_id'], transaction['resumed']['lease_id'])
        self.assertEqual(transaction['paused']['lease_id'], result['receipt']['lease']['lease_id'])
        self.assertEqual(transaction['resumed']['request_seq'], transaction['paused']['request_seq']+1)
        self.assertEqual(result['receipt']['observation_sha256'], planner.digest(result['snapshot']))
        with self.assertRaisesRegex(LeaseError, 'inactive'):
            self.client.check_lease(result['receipt']['lease'])
        self.assertFalse(plan['runtime_executed'])

    def test_memory_reads_happen_only_while_the_host_acknowledges_this_pause(self):
        calls = []
        def read(address, size):
            self.assertEqual(self.client.ack()['status'], 'paused')
            self.client.check_lease(self.client._active)
            calls.append((address, size))
            return self.memory.read(address, size)
        self.session.read_exact = read
        result = self.session.read()
        self.assertEqual(len(calls), result['receipt']['read_calls'])
        self.assertGreater(len(calls), 10)
        self.assertEqual(self.client.ack()['status'], 'resumed')

    def test_distinct_observations_have_monotonic_sequences_and_new_leases(self):
        first, second = self.session.read(), self.session.read()
        self.assertEqual(first['snapshot']['sequence'], 1)
        self.assertEqual(second['snapshot']['sequence'], 2)
        self.assertNotEqual(first['receipt']['lease']['lease_id'], second['receipt']['lease']['lease_id'])
        self.assertEqual(self.host.seq, 4)

    def test_decoder_failure_resumes_and_consumes_sequence_without_returning_proof(self):
        self.session.read_exact = lambda address, size: b''
        with self.assertRaises(decoder.ObservationError):
            self.session.read()
        self.assertEqual(self.client.ack()['status'], 'resumed')
        self.session.read_exact = self.memory.read
        self.assertEqual(self.session.read()['snapshot']['sequence'], 2)

    def test_resume_failure_prevents_returning_an_otherwise_valid_observation(self):
        advance = self.host.advance
        def ignore_resume(seconds):
            path = self.host.root/'request.txt'
            if path.exists() and b' resume ' in path.read_bytes():
                self.host.ignore = True
            advance(seconds)
        self.client.sleep = ignore_resume
        with self.assertRaisesRegex(LeaseError, 'Timed out'):
            self.session.read()
        self.assertTrue(self.client._poisoned)
        self.assertFalse(self.session._reading)

    def test_lease_expiry_during_reads_rejects_without_resuming_expired_target(self):
        def expire(address, size):
            self.host.tick += 20001
            return self.memory.read(address, size)
        self.session.read_exact = expire
        with self.assertRaisesRegex(decoder.ObservationError, 'live paused lease') as raised:
            self.session.read()
        self.assertIsInstance(raised.exception.__cause__, LeaseError)
        self.assertIn('expired', str(raised.exception.__cause__))
        self.assertIn('Read-lease release failed', raised.exception.__notes__[0])
        self.assertEqual(self.host.seq, 1)
        self.assertTrue(self.client._poisoned)

    def test_wrong_candidate_fails_before_memory_read_and_releases_pause(self):
        self.session.candidate['sha256'] = 'b'*64
        with self.assertRaises(decoder.ObservationError):
            self.session.read()
        self.assertEqual(self.memory.calls, [])
        self.assertEqual(self.client.ack()['status'], 'resumed')

    def test_caller_metadata_and_returned_receipts_cannot_mutate_next_observation(self):
        self.candidate['stage'] = 'caller-mutated'
        first = self.session.read()
        self.assertNotEqual(first['receipt']['candidate']['stage'], self.candidate['stage'])
        first['host_transaction']['resumed']['status'] = 'tampered'
        first['receipt']['lease']['pid'] = 999
        second = self.session.read()
        self.assertEqual(second['host_transaction']['resumed']['status'], 'resumed')
        self.assertEqual(second['receipt']['lease']['pid'], self.host.identity['pid'])

    def test_nested_observation_is_rejected_and_outer_pause_is_released(self):
        self.session.read_exact = lambda address, size: self.session.read()
        with self.assertRaisesRegex(decoder.ObservationError, 'exact read failed') as raised:
            self.session.read()
        self.assertIsInstance(raised.exception.__cause__, LeaseError)
        self.assertIn('Nested observation', str(raised.exception.__cause__))
        self.assertEqual(self.client.ack()['status'], 'resumed')

    def test_changed_target_identity_fails_before_acquiring_a_pause(self):
        self.client.identity['pid'] += 1
        with self.assertRaisesRegex(LeaseError, 'target identity changed'):
            self.session.read()
        self.assertEqual(self.host.seq, 0)


if __name__ == '__main__':
    unittest.main(verbosity=2)
