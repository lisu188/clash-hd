"""Portable activation integration fixtures; no native host is executed."""
from contextlib import ExitStack
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import ordinary_map_activation_host as activation
import ordinary_map_phase_host as phase
import ordinary_map_phase_client as phase_client
import ordinary_map_pause_client as pause
import owned_hidden_process as hidden
import resolution_playability as runtime
import test_ordinary_map_activation_trace as logs
from test_ordinary_map_phase_client import FakeHost, CONTROLLER
import test_resolution_playability as prior


class ActivationIntegrationTests(unittest.TestCase):
    def ready(self):
        temporary = tempfile.TemporaryDirectory(prefix='clash-activation-ready-')
        self.addCleanup(temporary.cleanup)
        fake = FakeHost(Path(temporary.name)/'control')
        peer = phase_client.PhaseClient(fake.directory, controller_sha256=CONTROLLER,
            identity=fake.identity, check_owner=lambda: deepcopy(fake.identity), host_alive=lambda: True,
            clock_ms=lambda: fake.tick, sleep=fake.advance)
        return peer.wait_ready()

    def test_authenticated_ready_uses_separate_observer_digest_before_retirement(self):
        ready = self.ready()
        original = deepcopy(ready)
        expected = runtime.activation_trace_identity(ready, phase_sha256=CONTROLLER,
            controller_sha256=activation.source_sha256())
        self.assertEqual(set(expected), logs.trace.IDENTITY_KEYS)
        self.assertEqual(expected['controller_sha256'], activation.source_sha256())
        self.assertNotEqual(expected['controller_sha256'], ready['controller_sha256'])
        self.assertEqual(expected['tid'], ready['primary_tid'])
        self.assertEqual(ready, original)
        report = runtime.activation_diagnostics(logs.log(logs.records(identity=expected)), expected)
        self.assertTrue(report['complete'], report['errors'])
        self.assertFalse(report['transactions'][0]['activation']['startup_retired'])
        for name in ('manual_input_proof', 'gameplay_verified', 'promotion_ready',
                     'callback_return_observed', 'all_activation_events_observed'):
            self.assertFalse(report[name])

    def test_unvalidated_readiness_or_wrong_phase_digest_is_rejected(self):
        ready = self.ready()
        defects = [dict(ready, status='held'), dict(ready, phase='held'),
                   dict(ready, request_seq=True), dict(ready, request_seq=1),
                   dict(ready, paused=True), dict(ready, lease_id='a'*32),
                   dict(ready, deadline_tick_ms=1), dict(ready, schema='other'),
                   dict(ready, controller_sha256='d'*64), dict(ready, extra=1)]
        for bad in defects:
            with self.subTest(defect=bad), self.assertRaisesRegex(ValueError, 'readiness'):
                runtime.activation_trace_identity(bad, phase_sha256=CONTROLLER,
                    controller_sha256=activation.source_sha256())
        for digest in (None, True, '', 'A'*64, 'a'*63):
            with self.subTest(digest=digest), self.assertRaisesRegex(ValueError, 'digests'):
                runtime.activation_trace_identity(ready, phase_sha256=CONTROLLER,
                    controller_sha256=digest)

    def test_log_cannot_supply_its_own_missing_or_wrong_expected_identity(self):
        log = logs.log(logs.records())
        with self.assertRaisesRegex(ValueError, 'owned readiness identity'):
            runtime.activation_diagnostics(log, None)
        for key, value in (('pid', 201), ('tid', 202), ('creation_filetime', 1),
                           ('image_base', 0x500000), ('session_id', 'c'*32),
                           ('controller_sha256', 'd'*64)):
            with self.subTest(field=key):
                report = runtime.activation_diagnostics(log, dict(logs.IDENTITY, **{key:value}))
                self.assertFalse(report['complete'])
                self.assertEqual(report['observed_device_returns'], 0)

    def test_driver_composition_preserves_existing_phase_bytes_and_initial_arm(self):
        source = runtime.native_phase_source(1920, 1080)
        self.assertEqual(source.count('NativeActivationController activation('), 1)
        self.assertLess(source.index('activation.arm_initial('), source.index('"run actual code"'))
        self.assertLess(source.index('startup.on_event('), source.index('activation.on_event('))
        self.assertLess(source.index('activation.on_event('), source.index('phases.on_event('))
        self.assertEqual(hashlib.sha256(Path(phase.__file__).read_bytes()).hexdigest(),
            '1569262c0455112da2eebf3bfdc4947f4405b328ff258a384683713017244a6c')
        self.assertIn(activation.source_sha256(), source)

    def test_diagnostic_completeness_does_not_accept_failed_gameplay(self):
        report = dict(errors=[], actions=[], activation_trace=runtime.activation_diagnostics(
            logs.log(logs.records()), logs.IDENTITY))
        self.assertTrue(report['activation_trace']['complete'])
        self.assertFalse(runtime.hidden_success(report))

    def test_early_startup_failure_retains_bound_diagnostics_without_phase_actions(self):
        # Reuse only the prior tiny artificial-file setup; all native boundaries
        # below are mocked. No original image or candidate is executable.
        fixture = prior.HiddenDiskReserveTests('test_prelaunch_uses_only_remaining_scratch_and_reaches_mock_boundary_one_byte_above')
        self.addCleanup(fixture.doCleanups)
        value = fixture.fixture()
        original_path = runtime.Path
        baseline = value.baseline
        ready = self.ready()
        ready.update(controller_sha256=phase.source_sha256())
        identity = {key:ready[key] for key in ('pid', 'creation_filetime', 'image_base')}
        expected = runtime.activation_trace_identity(ready, phase_sha256=phase.source_sha256(),
            controller_sha256=runtime.matrix.digest(value.checkout/'tools/ordinary_map_activation_host.py'))
        trace_log = logs.log(logs.records(identity=expected))
        trace_log += f"REAL_LOADED pid={identity['pid']} base={identity['image_base']:x} entry=401000 executable_sections_match=1\n"
        trace_log += 'REAL_EXE_ENTRY observed=1\n'

        class Host:
            pid, creation_filetime, desktop_name = 333, 1, 'artificial-private-desktop'
            returncode = 2
            cleanup = {'fixture_only': True}
            def __init__(self, argv, **kwargs):
                control = Path(argv[-2])
                (control/'phase-ack.json').write_text(json.dumps(ready), encoding='ascii')
                kwargs['stdout'].write(trace_log)
                kwargs['stdout'].flush()
            def poll(self): return self.returncode
            def wait(self, **kwargs): return self.returncode
            def close(self): pass

        def compile_fixture(out):
            engine = out/'engine.exe'; engine.write_bytes(b'Artificial non-executable fixture')
            (out/'real-exe-engine.cpp').write_bytes(b'Artificial source fixture')
            return engine

        with ExitStack() as stack:
            stack.enter_context(patch.object(runtime, 'os', SimpleNamespace(name='nt', environ={})))
            stack.enter_context(patch.object(runtime, 'Path', side_effect=lambda path:
                value.allowed if str(path)=='C:/ClashTests' else original_path(path)))
            stack.enter_context(patch.object(runtime.matrix, 'ROOT', value.checkout))
            stack.enter_context(patch.object(pause, 'checked_directory', side_effect=lambda path:path.resolve()))
            stack.enter_context(patch.object(pause, 'prepare_control', side_effect=lambda path:path.mkdir()))
            stack.enter_context(patch.object(runtime.subprocess, 'check_output', return_value='a'*40+'\n'))
            stack.enter_context(patch.object(runtime.owned, 'verify_assets', return_value=baseline))
            stack.enter_context(patch.object(runtime, 'prepared_small_world_candidate', return_value=(value.exe, value.built)))
            stack.enter_context(patch.object(runtime, 'native_phase_source', return_value='Artificial source'))
            stack.enter_context(patch.object(runtime.matrix.runtime, 'compile_harness', side_effect=compile_fixture))
            stack.enter_context(patch.object(runtime, 'require_hidden_disk_reserve'))
            stack.enter_context(patch.object(hidden, 'OwnedHiddenProcess', Host))
            target = SimpleNamespace(read_exact=None, check_owner=lambda:None, handle=1,
                kernel=SimpleNamespace(WaitForSingleObject=lambda *args:0), close=lambda:None)
            stack.enter_context(patch.object(pause, 'RetainedTarget', return_value=target))
            peer = SimpleNamespace(wait_ready=lambda:deepcopy(ready))
            stack.enter_context(patch.object(phase_client, 'PhaseClient', return_value=peer))
            actions = stack.enter_context(patch.object(runtime, 'measured_actions'))
            stack.enter_context(patch.object(runtime.matrix.runtime, 'render', return_value=[]))
            stack.enter_context(patch.object(runtime.matrix.runtime, 'verify_hd_sources'))
            stack.enter_context(patch.object(runtime, 'audit_prepared_small_world'))
            stack.enter_context(patch.object(runtime.matrix.runtime, 'ORIGINAL_SHA256', baseline['clash95.exe']['sha256']))
            report = runtime.run_hidden(value.args)
        actions.assert_not_called()
        self.assertFalse(report['passed'])
        self.assertTrue(any('startup did not retire' in error for error in report['errors']))
        self.assertEqual(report['activation_identity'], expected)
        self.assertTrue(report['activation_trace']['complete'], report['activation_trace']['errors'])
        self.assertNotIn('phase_receipts', report)
        self.assertNotIn('owner', report)
        self.assertNotIn('startup_retired_before_actions', report)
        self.assertFalse(report['gameplay_verified'])
        self.assertEqual(json.loads((value.args.out/'playability.json').read_text()), report)


if __name__ == '__main__':
    unittest.main()
