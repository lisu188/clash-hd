"""Offline attachment tests. Every process, window and capture boundary is fake."""
from __future__ import annotations

import ast
import copy
import ctypes
from ctypes import wintypes
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import struct
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from PIL import Image

import complete_hd_manual_attach as attach
import complete_hd_manual_attach_win32 as native


def pe_fixture() -> bytes:
    data = bytearray(0x800)
    data[:2] = b"MZ"; struct.pack_into("<I", data, 60, 0x80)
    data[0x80:0x84] = b"PE\0\0"
    struct.pack_into("<HH", data, 0x84, 0x14c, 3)
    struct.pack_into("<H", data, 0x94, 224)
    opt = 0x98
    struct.pack_into("<H", data, opt, 0x10b)
    struct.pack_into("<I", data, opt + 28, 0x400000)
    struct.pack_into("<II", data, opt + 56, 0x4000, 0x200)
    struct.pack_into("<II", data, opt + 96 + 40, 0x3000, 12)
    for index, (name, rva, raw, flags) in enumerate(((b".text", 0x1000, 0x200, 0x60000020),
        (b".data", 0x2000, 0x400, 0xc0000040), (b".reloc", 0x3000, 0x600, 0x42000040))):
        offset = opt + 224 + index * 40
        data[offset:offset + len(name)] = name
        struct.pack_into("<IIII", data, offset + 8, 0x200, rva, 0x200, raw)
        struct.pack_into("<I", data, offset + 36, flags)
    struct.pack_into("<I", data, 0x200, 0x402000)
    struct.pack_into("<IIHH", data, 0x600, 0x1000, 12, 0x3000, 0)
    return bytes(data)


class LoadedImageTests(unittest.TestCase):
    def test_relocation_aware_immutable_image_and_canonical_guard_partition(self):
        data = pe_fixture()
        probe = '(wo(00401000) != 2000) (by(00402000) != 00) (by(00400000) != 4d)'
        contract = native.image_contract(data, 0x700000, probe)
        self.assertEqual(struct.unpack_from('<I', contract['memory'], 0x1000)[0], 0x702000)
        memory = bytearray(contract['memory'])
        memory[0x2000] = 77  # Actual game-owned writable state must be permitted.
        report = native.verify_image(contract, lambda address, size: bytes(memory[address - 0x700000:address - 0x700000 + size]))
        self.assertEqual(report['canonical_guards'], {'immutable_checked': 2, 'runtime_state_excluded': 1})
        memory[0x1004] = 0xcc
        with self.assertRaisesRegex(ValueError, 'immutable bytes'):
            native.verify_image(contract, lambda address, size: bytes(memory[address - 0x700000:address - 0x700000 + size]))
        with self.assertRaisesRegex(ValueError, 'guard disagrees'):
            native.image_contract(data, 0x400000, '(by(00401000) != ff)')

    def test_bad_allocation_relocation_and_writable_code_rejected(self):
        for offset, value, fmt in ((0x178 + 36, 0xe0000020, '<I'),
                                   (0x178 + 12, 0x3f00, '<I'), (0x608, 0x5000, '<H')):
            data = bytearray(pe_fixture()); struct.pack_into(fmt, data, offset, value)
            with self.assertRaises(ValueError): native.image_contract(bytes(data), 0x700000)
        with self.assertRaises(ValueError): native.image_contract(pe_fixture()[:200], 0x400000)


class FakeSession:
    def __init__(self, plan):
        self.plan, self.closed, self.captured = plan, False, 0
        self.process = {"pid": plan['attachment']['pid'], "creation_filetime": plan['attachment']['creation_filetime'],
                        "path": plan['attachment']['process_path']}
        self.memories, self.inventory = {}, []
        for index, name in enumerate(('candidate', 'wrapper')):
            artifact = plan['artifacts'][name]
            base = 0x400000 + index * 0x300000
            contract = native.image_contract(Path(artifact['path']).read_bytes(), base)
            self.memories[base] = bytearray(contract['memory'])
            self.inventory.append({'path': artifact['path'], 'base': base, 'size': contract['image_size']})

    def identity(self): return copy.deepcopy(self.process)
    def modules(self): return copy.deepcopy(self.inventory)
    def read(self, address, size):
        for base, memory in self.memories.items():
            if base <= address < base + len(memory):
                return bytes(memory[address - base:address - base + size])
        raise OSError('invalid fake memory read')
    def placement(self, points):
        plan = self.plan; a = plan['attachment']; client = [*a['client_origin'], *plan['client_size']]
        return {'hwnd': a['hwnd'], 'client': client, 'dpi_awareness': 2,
                'targets': [{'accessible': True, 'client': client, 'logical_size': plan['client_size'],
                             'screen_target': [p[0] + client[0], p[1] + client[1]], 'target_hwnd': a['hwnd'],
                             'point_hwnd': a['hwnd'], 'point_root_hwnd': a['hwnd'], 'monitor': [-1920, 0, 1920, 1080]}
                            for p in points]}
    def capture(self, *, before_attempt):
        before_attempt()
        self.captured += 1
        return Image.new('RGB', tuple(self.plan['client_size']), (10, 20, 30))
    def close(self): self.closed = True; return True


class AttachmentTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix='complete-attach-offline-')
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.capture = self.root / 'capture'; self.capture.mkdir()
        self.scope = patch.object(attach, 'CAPTURE_ROOT', self.capture)
        self.scope.start(); self.addCleanup(self.scope.stop)
        self.game = self.root / 'candidate'; self.game.mkdir()
        self.candidate = self.game / 'fixture.exe'; self.candidate.write_bytes(pe_fixture())
        self.wrapper = self.game / 'ddraw.dll'; self.wrapper.write_bytes(pe_fixture())
        self.configuration = self.game / 'ddraw.ini'; self.configuration.write_text('fixture only')
        self.manifest = self.game / 'fixture.candidate.json'; self.manifest.write_text('{}')
        self.probe = self.game / 'fixture.cdb'; self.probe.write_text('(wo(00401000) != 2000) (by(00402000) != 00)')
        self.context = {'identity': {'stage': attach.evidence.STAGE, 'recipe_revision': attach.evidence.RECIPE_REVISION,
            'resolution': '800x600', 'candidate_sha256': attach.reference(self.candidate)['sha256'],
            'base_sha256': 'a' * 64, 'metadata_sha256': attach.reference(self.manifest)['sha256'],
            'probe_sha256': attach.reference(self.probe)['sha256']}, 'byte_rebuild_passed': True,
            'candidate_path': str(self.candidate), 'metadata_path': str(self.manifest), 'probe_path': str(self.probe),
            'source_hashes': {'tools/complete_hd_manual_attach.py': attach.reference(Path(attach.__file__))['sha256']}}
        self.basis = self.capture / 'point-basis.txt'; self.basis.write_text('SYNTHETIC OFFLINE TARGET BASIS, no runtime evidence')
        self.targets = self.capture / 'targets.json'
        self.target_value = {'schema': 'complete_hd_attachment_targets_v1', 'candidate_identity': self.context['identity'],
                             'target_id': attach.evidence.MANUAL_IDS[2],
                             'points': [{'id': 'first-command', 'logical': [608, 536], 'basis': attach.reference(self.basis)}]}
        self.targets.write_text(json.dumps(self.target_value))
        self.plan = self.build()
        self.plan_path = self.capture / 'plan.json'; attach.write_new(self.plan_path, self.plan)
        self.now = datetime(2026, 9, 8, 12, tzinfo=timezone.utc)
        self.approval = self.capture / 'fixture-approval.json'
        # Explicit synthetic unit-test data, never a usable user approval file.
        self.approval_value = {'record_kind': 'user_approval', 'approved': True,
            'approval_text': 'SYNTHETIC OFFLINE FIXTURE ONLY, no actual user approval',
            'identity': attach.approval_identity(self.plan, attach.reference(self.plan_path)['sha256']),
            'approved_at': (self.now - timedelta(minutes=1)).isoformat(),
            'expires_at': (self.now + timedelta(minutes=20)).isoformat()}
        self.approval.write_text(json.dumps(self.approval_value))
        self.sessions = []

    def loader(self, path):
        self.assertEqual(path, self.manifest.resolve())
        return copy.deepcopy(self.context)

    def build(self, **kwargs):
        values = dict(candidate_manifest=self.manifest, wrapper=self.wrapper, configuration=self.configuration,
            target_file=self.targets, pid=100, creation_filetime=123456789, hwnd=0x1234, client_origin=[0, 0],
            output_dir=self.capture / 'run', run_id='offline-fixture', context_loader=self.loader)
        values.update(kwargs)
        return attach.build_plan(**values)

    def factory(self, plan):
        session = FakeSession(plan); self.sessions.append(session); return session

    def run_fake(self, factory=None):
        with patch.object(subprocess, 'run', side_effect=AssertionError('no subprocess')), \
             patch.object(subprocess, 'Popen', side_effect=AssertionError('no process launch')):
            return attach.execute(self.plan_path, self.approval, allow_visible_runtime=True, context_loader=self.loader,
                session_factory=factory or self.factory, now=self.now, tear_analyzer=lambda *a: {'clean': True, 'verdict': 'synthetic_fixture'})

    def test_plan_reads_only_and_never_accepts_human_proof(self):
        with patch.object(native, 'WindowsAttachment', side_effect=AssertionError('no Win32 while planning')):
            plan = self.build(); attach.verify_plan(plan, context_loader=self.loader)
        self.assertFalse((self.capture / 'run').exists())
        for key in ('executed', 'manual_input_accepted', 'release_ready', 'runtime_ready'):
            self.assertIs(plan[key], False)
        self.assertIs(plan['ownership']['process_termination_permitted'], False)
        self.assertEqual(plan['schedule']['captures_per_checkpoint'], 3)

    def test_three_distinct_original_frames_retained_handle_closed_owner_untouched(self):
        result = self.run_fake()
        self.assertTrue(result['passed']); self.assertEqual(self.sessions[0].captured, 3)
        self.assertTrue(self.sessions[0].closed)
        frames = result['captures'][0]['frames']
        self.assertEqual(len({row['path'] for row in frames}), 3)
        self.assertEqual(len(frames[0]['placement_before']['targets']), 6)
        self.assertFalse(result['manual_input_accepted']); self.assertFalse(result['external_process_cleanup_verified'])
        self.assertTrue((self.capture / 'run' / 'capture-receipt.json').exists())
        self.assertTrue((self.capture / 'run' / 'summary.json').exists())

    def test_missing_stale_mismatched_approval_reject_before_session_initialization(self):
        with patch.object(native, 'WindowsAttachment', side_effect=AssertionError('approval gate must precede Win32')):
            for value in (dict(self.approval_value, approved=False),
                          dict(self.approval_value, expires_at=(self.now - timedelta(seconds=1)).isoformat()),
                          dict(self.approval_value, identity=dict(self.approval_value['identity'], scope='launch')),
                          dict(self.approval_value, approved_at='2026-09-08T12:00:00'),
                          dict(self.approval_value, expires_at=(self.now + timedelta(seconds=30)).isoformat())):
                self.approval.write_text(json.dumps(value))
                with self.assertRaises(ValueError): self.run_fake()
            self.approval.unlink()
            with self.assertRaises(FileNotFoundError): self.run_fake()
        self.assertEqual(self.sessions, [])
        self.assertFalse((self.capture / 'run').exists())

    def test_changed_bundle_wrapper_configuration_basis_and_plan_fail_before_capture(self):
        for file in (self.candidate, self.wrapper, self.configuration, self.basis, self.probe, self.manifest):
            before = file.read_bytes(); file.write_bytes(before + b'changed')
            with self.assertRaises(ValueError): self.run_fake()
            file.write_bytes(before)
        plan = copy.deepcopy(self.plan); plan['manual_input_accepted'] = True
        self.plan_path.write_text(json.dumps(plan))
        with self.assertRaises(ValueError): self.run_fake()
        self.assertEqual(self.sessions, [])

    def test_reused_pid_identity_failure_preserves_summary_and_closes_only_handle(self):
        def reused(plan):
            session = self.factory(plan); session.process['creation_filetime'] += 1; return session
        result = self.run_fake(reused)
        self.assertFalse(result['passed']); self.assertIn('stale/reused PID', result['failures'][0])
        self.assertTrue(self.sessions[0].closed); self.assertEqual(self.sessions[0].captured, 0)

    def test_inaccessible_actual_target_blocks_capture_even_if_corners_accessible(self):
        def occluded(plan):
            session = self.factory(plan); original = session.placement
            def placement(points):
                result = original(points); result['targets'][-1]['accessible'] = False; return result
            session.placement = placement; return session
        result = self.run_fake(occluded)
        self.assertFalse(result['passed']); self.assertIn('inaccessible', result['failures'][0])
        self.assertEqual(self.sessions[0].captured, 0)

    def test_wrong_loaded_wrapper_or_code_is_not_authenticated_by_same_pid(self):
        session = FakeSession(self.plan)
        session.inventory[1]['path'] = str(self.game / 'other.dll')
        with self.assertRaisesRegex(ValueError, 'loaded module missing'):
            attach.measured_identity(self.plan, session)
        session = FakeSession(self.plan); session.memories[0x400000][0x1004] = 0xcc
        with self.assertRaisesRegex(ValueError, 'immutable bytes'):
            attach.measured_identity(self.plan, session)

    def test_mid_capture_window_change_retains_original_frame_and_failure(self):
        def moving(plan):
            session = self.factory(plan); original = session.placement
            def placement(points):
                result = original(points)
                if session.captured: result['client'][0] += 1
                return result
            session.placement = placement; return session
        result = self.run_fake(moving)
        self.assertFalse(result['passed']); self.assertEqual(len(result['captures'][0]['frames']), 1)
        self.assertEqual(result['captures'][0]['frames'][0]['result'], 'pending_postcapture_validation')
        self.assertTrue(Path(result['captures'][0]['frames'][0]['path']).is_file())

    def test_bounded_target_inputs_and_previous_output_reject(self):
        for key, value in (('pid', 0), ('pid', True), ('creation_filetime', 0), ('hwnd', 0),
                           ('checkpoints', 13), ('duration_seconds', 301), ('client_origin', [0, 1, 2])):
            with self.assertRaises(ValueError): self.build(**{key: value})
        for points in ([], self.target_value['points'] * 33,
                       [dict(self.target_value['points'][0], logical=[800, 0])]):
            self.targets.write_text(json.dumps(dict(self.target_value, points=points)))
            with self.assertRaises(ValueError): self.build()
        self.targets.write_text(json.dumps(self.target_value))
        (self.capture / 'run').mkdir()
        with self.assertRaises(ValueError): self.build()

    def test_deadline_crossed_during_measurement_prevents_first_capture(self):
        clock = [0.0]
        def slow(plan):
            session = self.factory(plan); original = session.placement
            def placement(points):
                value = original(points); clock[0] = 61.0; return value
            session.placement = placement; return session
        result = attach.execute(self.plan_path, self.approval, allow_visible_runtime=True,
            context_loader=self.loader, session_factory=slow, now=self.now, monotonic=lambda: clock[0],
            tear_analyzer=lambda *a: {'clean': True})
        self.assertFalse(result['passed']); self.assertIn('interval expired', result['failures'][0])
        self.assertEqual(self.sessions[0].captured, 0); self.assertTrue(self.sessions[0].closed)

    def test_native_capture_boundary_checks_deadline_before_single_backend_attempt(self):
        # Construct the source boundary without its Win32 initializer.
        session = object.__new__(native.WindowsAttachment); session.plan = self.plan
        class Pulse:
            @staticmethod
            def client_geometry(hwnd): return (0, 0, 800, 600)
            class ImageGrab:
                @staticmethod
                def grab(**kwargs): raise AssertionError('expired capture must not start')
        session.pulse = Pulse()
        def expired(): raise ValueError('expired before native attempt')
        with self.assertRaisesRegex(ValueError, 'expired before native'):
            session.capture(before_attempt=expired)

    def test_native_placement_never_reacquires_stale_or_foreign_hwnd(self):
        # No Win32 constructor or API is used: these native functions are fakes.
        session = object.__new__(native.WindowsAttachment)
        session.plan, session.c, session.w = self.plan, ctypes, wintypes
        def forbidden(*args, **kwargs):
            raise AssertionError('stale/foreign handle must not trigger window search')
        def foreign_owner(hwnd, owner):
            ctypes.cast(owner, ctypes.POINTER(wintypes.DWORD)).contents.value = self.plan['attachment']['pid'] + 1
            return 123
        session.pulse = SimpleNamespace(live_hwnd=forbidden)
        session.session = SimpleNamespace(window=forbidden, user=SimpleNamespace(
            IsWindow=lambda hwnd: False, GetWindowThreadProcessId=forbidden, IsWindowVisible=forbidden))
        with self.assertRaisesRegex(ValueError, 'HWND is stale'):
            session.placement([[0, 0]])
        session.session.user.IsWindow = lambda hwnd: True
        session.session.user.GetWindowThreadProcessId = foreign_owner
        with self.assertRaisesRegex(ValueError, 'different process'):
            session.placement([[0, 0]])

    def test_unexpected_capture_exception_preserves_receipt_summary_and_handle_cleanup(self):
        def failing(plan):
            session = self.factory(plan)
            def capture(**kwargs): raise RuntimeError('synthetic native backend failure')
            session.capture = capture
            return session
        result = self.run_fake(failing)
        self.assertFalse(result['passed'])
        self.assertIn('synthetic native backend failure', result['failures'])
        self.assertTrue(self.sessions[0].closed)
        original = json.loads((self.capture / 'run' / 'capture-receipt.json').read_text())
        final = json.loads((self.capture / 'run' / 'summary.json').read_text())
        self.assertEqual(original['failures'], result['failures'])
        self.assertEqual(final, result)

    def test_changed_approval_during_capture_keeps_partial_material(self):
        def change(plan):
            session = self.factory(plan); original = session.capture
            def capture(**kwargs):
                frame = original(**kwargs)
                self.approval.write_text(json.dumps(dict(self.approval_value, approval_text='changed')))
                return frame
            session.capture = capture; return session
        result = self.run_fake(change)
        self.assertFalse(result['passed']); self.assertIn('approval changed', result['failures'][0])
        self.assertEqual(self.sessions[0].captured, 1); self.assertTrue(self.sessions[0].closed)

    def test_handle_cleanup_failure_cannot_pass(self):
        def unclosed(plan):
            session = self.factory(plan); session.close = lambda: False; return session
        result = self.run_fake(unclosed)
        self.assertFalse(result['passed']); self.assertIn('did not close', result['failures'][0])
        self.assertIs(result['external_process_cleanup_verified'], False)

    def test_analysis_failure_retains_earlier_receipt_and_captured_bytes(self):
        def fail(*args): raise RuntimeError('synthetic analysis failure')
        result = attach.execute(self.plan_path, self.approval, allow_visible_runtime=True,
            context_loader=self.loader, session_factory=self.factory, now=self.now, tear_analyzer=fail)
        original = json.loads((self.capture / 'run' / 'capture-receipt.json').read_text())
        self.assertFalse(result['passed']); self.assertTrue(original['capture_complete'])
        self.assertEqual(original['failures'], [])
        self.assertIn('synthetic analysis failure', result['failures'][0])
        for row in original['captures'][0]['frames']:
            self.assertEqual(attach.reference(Path(row['path']))['sha256'], row['sha256'])

    def test_unexpected_cleanup_exception_preserves_failed_receipt_and_summary(self):
        def failing(plan):
            session = self.factory(plan)
            def close(): raise RuntimeError('synthetic close failure')
            session.close = close
            return session
        result = self.run_fake(failing)
        self.assertFalse(result['passed'])
        self.assertFalse(result['observation_handle_closed'])
        self.assertTrue(any('synthetic close failure' in text for text in result['failures']))
        for filename in ('capture-receipt.json', 'summary.json'):
            saved = json.loads((self.capture / 'run' / filename).read_text())
            self.assertEqual(saved['failures'], result['failures'])

    def test_native_source_exposes_no_launch_input_focus_move_or_termination_calls(self):
        forbidden = {'Popen', 'run', 'start', 'TerminateProcess', 'SetForegroundWindow', 'MoveWindow',
                     'SetWindowPos', 'SendInput', 'PostMessage', 'WriteProcessMemory', 'SuspendThread'}
        for path in (Path(attach.__file__), Path(native.__file__)):
            tree = ast.parse(path.read_text())
            calls = {node.func.attr for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)}
            self.assertFalse(calls & forbidden, calls & forbidden)


if __name__ == '__main__': unittest.main(verbosity=2)
