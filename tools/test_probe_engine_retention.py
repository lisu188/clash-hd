#!/usr/bin/env python3
"""Portable failure/retention fixtures; never starts a compiler or debugger."""
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import test_framed_loaded_probe_engine as engine
import test_complete_small_world_probe_engine as small
import test_ordinary_castle_entry_matrix_engine as castle


def disk(_):
    return SimpleNamespace(total=1 << 40, free=1 << 39, used=1 << 39)


def diagnostic_log():
    lines = ['HARNESS_CLOCK frequency=10000000 native=1 error=0',
             'HARNESS_BEGIN base=00400000 mode=block']
    sequence = 0
    for name in engine.PHASES:
        for edge in ('begin', 'end'):
            sequence += 1
            value = 6 if name == 'status' and edge == 'end' else 1 if name == 'compare' and edge == 'end' else 0
            lines.append(f'HARNESS_PHASE seq={sequence} name={name} edge={edge} tick={100 + sequence} qpc=1 error=0 hr=0 value={value}')
    lines += ['HARNESS_END hr=00000000 paused=1 same_ip=1 unchanged=1', 'HARNESS_COMPLETE']
    return '\n'.join(lines) + '\n'


class RetentionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='clash-probe-retention-mock-')
        self.addCleanup(self.temporary.cleanup)
        self.parent = Path(self.temporary.name).resolve()
        self.source = self.parent / 'source.py'
        self.source.write_bytes(b'original source\r\n')
        self.store = engine.ArtifactStore(self.parent, disk_usage=disk)
        self.ledger = engine.CaseLedger(self.store, [self.source])

    def prepare(self, label='fixed-block'):
        return self.ledger.prepare(b'MZ artificial fixture', b'original\r\nprobe\r\n',
                                   test='test_fixture', label=label, mode='block')

    def result(self, row):
        return self.ledger.outcome(row, returncode=0, stdout=diagnostic_log().encode(), stderr=b'')

    def test_pending_is_durable_before_launch(self):
        row = self.prepare()
        saved = json.loads((self.store.root / 'ledger.json').read_bytes())
        self.assertEqual(saved['cases'][0]['status'], 'pending')
        self.assertIsNone(saved['cases'][0]['returncode'])
        self.assertFalse(engine.terminal_cases(saved['cases'], ['fixed-block']))
        self.assertEqual((Path(row['directory']) / 'verify.cdb').read_bytes(), b'original\r\nprobe\r\n')

    def test_original_raw_success_and_atomic_hash_are_retained(self):
        row = self.prepare()
        self.ledger.before_launch(row)
        self.result(row)
        self.assertTrue(engine.terminal_cases([row], ['fixed-block']))
        self.assertEqual(Path(row['stdout']['artifact']['path']).read_bytes(), diagnostic_log().encode())
        self.assertEqual(row['stderr']['artifact']['bytes'], 0)
        self.assertTrue(row['stderr']['available'])

    def test_timeout_partial_bytes_none_and_empty_remain_distinct(self):
        raw = b'HARNESS_BEGIN\xff\x00partial\r\n'
        row = self.prepare()
        error = subprocess.TimeoutExpired(['engine.exe', 'verify.cdb', 'block'], 35, output=raw, stderr=None)
        self.ledger.outcome(row, stdout=error.stdout, stderr=error.stderr, error=error)
        self.assertEqual(Path(row['stdout']['artifact']['path']).read_bytes(), raw)
        self.assertEqual(row['stderr'], {'available': False, 'artifact': None})
        self.assertEqual(row['error']['timeout'], 35)
        self.assertEqual(row['error']['command'], error.cmd)
        self.assertEqual(row['status'], 'failed')
        other = self.prepare('empty-timeout')
        self.ledger.outcome(other, stdout=b'', stderr=b'', error=error)
        self.assertTrue(other['stderr']['available'])
        self.assertEqual(other['stderr']['artifact']['bytes'], 0)
        self.assertIsNotNone(self.ledger.failure)

    def test_nonzero_result_cannot_complete_even_with_all_markers(self):
        row = self.prepare()
        self.ledger.outcome(row, returncode=2, stdout=diagnostic_log().encode(), stderr=b'original error')
        self.assertFalse(engine.terminal_cases([row], ['fixed-block']))

    def test_original_launch_exception_is_sticky(self):
        row = self.prepare()
        self.ledger.outcome(row, error=FileNotFoundError('original engine path missing'))
        self.assertEqual(row['stdout'], {'available': False, 'artifact': None})
        first = self.ledger.failure
        with self.assertRaises(AssertionError):
            self.result(row)
        self.assertEqual(self.ledger.failure, first)

    def test_duplicate_case_cannot_replace_failure(self):
        row = self.prepare()
        self.ledger.outcome(row, error=RuntimeError('first failure'))
        first = self.ledger.failure
        with self.assertRaises(AssertionError):
            self.prepare()
        self.assertEqual(len(self.ledger.records), 1)
        self.assertEqual(self.ledger.failure, first)

    def test_source_candidate_and_script_substitution_prevent_launch(self):
        for kind in ('source', 'probe-fixture.exe', 'verify.cdb'):
            with self.subTest(kind=kind):
                row = self.prepare(kind)
                path = self.source if kind == 'source' else Path(row['directory']) / kind
                original = path.read_bytes()
                path.write_bytes(original + b'changed')
                with self.assertRaises(AssertionError):
                    self.ledger.before_launch(row)
                path.write_bytes(original)
        self.assertIsNotNone(self.ledger.failure)

    def test_postprocess_source_mutation_cannot_publish_pass(self):
        row = self.prepare()
        self.source.write_bytes(b'changed after invocation')
        with self.assertRaises(AssertionError):
            self.result(row)
        self.assertEqual(row['status'], 'failed')
        self.assertEqual(Path(row['stdout']['artifact']['path']).read_bytes(), diagnostic_log().encode())

    def test_failed_atomic_write_keeps_original_and_partial(self):
        original = b'full original\xff\x00'
        with patch.object(engine.os, 'fsync', side_effect=OSError('mock flush failure')):
            with self.assertRaises(engine.RetentionError) as caught:
                self.store.write('failure.bin', original)
        self.assertEqual(caught.exception.original, original)
        self.assertEqual(Path(caught.exception.partial_path).read_bytes(), original)
        self.assertTrue(self.store.failed)
        self.assertIn(original, self.store.pending)

    def test_failed_publish_retains_original_atomic_file(self):
        original = b'original not renamed away'
        with patch.object(engine.os, 'replace', side_effect=OSError('mock rename failure')):
            with self.assertRaises(engine.RetentionError) as caught:
                self.store.write('rename.bin', original)
        self.assertEqual(Path(caught.exception.partial_path).read_bytes(), original)

    def test_postpublication_failure_points_at_retained_final_file(self):
        original = b'original publication'
        original_read = Path.read_bytes
        target = self.store.root / 'published.bin'
        def changed_read(path):
            raw = original_read(path)
            return b'corrupt observed readback' if path == target else raw
        with patch.object(Path, 'read_bytes', changed_read):
            with self.assertRaises(engine.RetentionError) as caught:
                self.store.write(target.name, original)
        self.assertEqual(caught.exception.partial_path, str(target))
        self.assertTrue(target.exists())
        self.assertEqual(caught.exception.original, original)
        self.assertTrue(self.store.failed)

    def test_previous_artifact_mutation_rejects_overwrite(self):
        row = self.store.write('retained.bin', b'first')
        Path(row['path']).write_bytes(b'foreign')
        with self.assertRaises(engine.RetentionError) as caught:
            self.store.write('retained.bin', b'next original')
        self.assertEqual(caught.exception.original, b'next original')
        self.assertEqual(Path(row['path']).read_bytes(), b'foreign')

    def test_reserve_and_capacity_debt_fail_without_creation(self):
        self.store.disk_usage = lambda _: SimpleNamespace(total=1000, free=100, used=900)
        with self.assertRaises(engine.RetentionError) as caught:
            self.store.write('reserve.bin', b'original')
        self.assertEqual(caught.exception.original, b'original')
        self.assertFalse((self.store.root / 'reserve.bin').exists())
        self.store.disk_usage = disk
        self.store.retained = engine.RETENTION_LIMIT
        with self.assertRaises(engine.RetentionError):
            self.store.write('capacity.bin', b'one')
        self.assertFalse((self.store.root / 'capacity.bin').exists())

    def test_original_byte_type_is_required(self):
        for value in ('decoded text', bytearray(b'bytes'), None):
            with self.subTest(value=value), self.assertRaises(TypeError):
                self.store.write('invalid.bin', value)

    def test_failed_clock_missing_reordered_or_signed_hr_cannot_complete(self):
        log = diagnostic_log()
        self.assertTrue(engine.phase_receipt(log))
        rows = log.splitlines()
        variants = [log.replace('qpc=1', 'qpc=0', 1), log.replace('hr=0', 'hr=-2147467259', 1),
                    log.replace('value=6', 'value=0'), log.replace('HARNESS_COMPLETE', ''),
                    log.replace('frequency=10000000', 'frequency=0'),
                    '\n'.join(rows[:3] + rows[4:]), '\n'.join(rows[:2] + [rows[3], rows[2]] + rows[4:]),
                    log + rows[2] + '\n', log + 'HARNESS_ERROR original failure\n',
                    log + 'HARNESS_PHASE malformed original boundary\n',
                    log + 'HARNESS_CLOCK malformed original frequency\n',
                    log + 'HARNESS_COMPLETE\n', log.replace('tick=101', 'tick=9223372036854775808'),
                    log.replace('qpc=1', 'qpc=2147483648', 1)]
        for changed in variants:
            with self.subTest(changed=changed):
                self.assertFalse(engine.phase_receipt(changed))

    def test_all_eight_pending_labels_do_not_mean_completed(self):
        rows = [dict(case=label, status='pending', returncode=None, raw_retention_complete=False,
                     phase_receipt_passed=False) for label in small.EXPECTED]
        self.assertFalse(engine.terminal_cases(rows, small.EXPECTED))
        for item in rows:
            item.update(status='completed', returncode=0, raw_retention_complete=True, phase_receipt_passed=True)
        self.assertTrue(engine.terminal_cases(rows, small.EXPECTED))
        rows[-1]['case'] = rows[0]['case']
        self.assertFalse(engine.terminal_cases(rows, small.EXPECTED))

    def test_external_ci_owned_path_and_optin_are_required(self):
        valid = dict(GITHUB_ACTIONS='true', CLASH_DEBUGGER_INTEGRATION='1', RUNNER_TEMP=str(self.parent),
                     CLASH_PROBE_ENGINE_ARTIFACT_DIR=str(self.parent / 'owned'))
        self.assertEqual(engine.ci_artifact_parent(valid), self.parent / 'owned')
        for change in ({'GITHUB_ACTIONS': 'false'}, {'CLASH_DEBUGGER_INTEGRATION': '0'},
                       {'CLASH_PROBE_ENGINE_ARTIFACT_DIR': str(self.parent)},
                       {'CLASH_PROBE_ENGINE_ARTIFACT_DIR': str(engine.ROOT / 'captures')}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                engine.ci_artifact_parent(dict(valid, **change))

    def test_owned_atomic_budget_accounts_replacements_and_copies(self):
        start = self.store.retained
        self.store.write('replacement.bin', b'12345')
        self.assertEqual(self.store.retained, start + 5)
        self.store.write('replacement.bin', b'12')
        self.assertEqual(self.store.retained, start + 2)
        self.prepare()
        self.assertGreater(self.store.retained, start + 2 + 2 * len(b'MZ artificial fixture'))

    def test_deadlines_security_comparators_and_case_set_are_unchanged(self):
        source = Path(engine.__file__).read_text(encoding='utf-8')
        self.assertIn('timeout=35', source)
        self.assertIn('timeout=60', source)
        self.assertIn('LOAD_LIBRARY_SEARCH_SYSTEM32', engine.HARNESS)
        self.assertIn('DEBUG_ONLY_THIS_PROCESS | CREATE_NO_WINDOW', engine.HARNESS)
        self.assertIn('intact = intact && session.read', engine.HARNESS)
        self.assertEqual(set(small.EXPECTED), {'fixed-file', 'fixed-block', 'aslr', 'corrupt-absolute',
                                            'corrupt-highbit', 'missing', 'reordered', 'unreadable'})

    def test_watchdog_samples_only_self_and_preserves_original_native_scalars(self):
        source = engine.HARNESS
        sample = source.split('static void watchdog_sample(', 1)[1].split('static unsigned __stdcall watchdog_worker', 1)[0]
        self.assertIn('HANDLE self = GetCurrentProcess();', sample)
        self.assertIn('GetProcessTimes(self, &creation, &exit, &kernel, &user)', sample)
        self.assertIn('GetProcessIoCounters(self, &io)', sample)
        self.assertIn('QueryPerformanceCounter(&tick); DWORD qpc_error = GetLastError();', sample)
        self.assertIn('DWORD cpu_error = GetLastError();', sample)
        self.assertIn('DWORD io_error = GetLastError();', sample)
        self.assertIn('InterlockedCompareExchange64(&callback_count, 0, 0)', sample)
        self.assertIn('InterlockedCompareExchange64(&callback_input_bytes, 0, 0)', sample)
        for field in ('qpc_native', 'qpc_error', 'cpu_native', 'cpu_error', 'io_native', 'io_error',
                      'creation', 'exit', 'kernel', 'user', 'read_operations', 'write_operations',
                      'other_operations', 'read_bytes', 'write_bytes', 'other_bytes',
                      'callback_count', 'callback_input_bytes', 'active_before', 'active_after'):
            self.assertIn(field + '=', sample)
        self.assertIn('fprintf(stderr,', sample)
        self.assertNotIn('stdout', sample)
        for forbidden in ('session.', 'control->', 'client->', 'memory->', 'registers->', 'symbols->',
                          'OpenProcess(', 'ReadProcessMemory(', 'ReadVirtual(', 'Execute(', 'ExecuteCommandFile('):
            self.assertNotIn(forbidden, sample)
        self.assertIn('__declspec(align(8)) static volatile LONG64 callback_count', source)
        self.assertIn('__declspec(align(8)) static volatile LONG64 callback_input_bytes', source)
        self.assertIn('InterlockedIncrement64(&callback_count);', source)
        self.assertIn('InterlockedAdd64(&callback_input_bytes, static_cast<LONG64>(strlen(text)));', source)
        self.assertIn('fputs(text, stdout); fflush(stdout); return S_OK;', source)

    def test_watchdog_owned_schedule_join_and_close_cannot_replace_verification(self):
        source = engine.HARNESS
        worker = source.split('static unsigned __stdcall watchdog_worker(', 1)[1].split('struct ExecuteWatchdog {', 1)[0]
        self.assertIn('const DWORD delays[] = {5000, 5000, 10000, 10000};', worker)
        self.assertIn('WaitForSingleObject(state->stop_event, delay)', worker)
        self.assertIn('InterlockedCompareExchange(&state->stop_requested, 0, 0)', worker)
        self.assertIn('_beginthreadex(nullptr, 0, watchdog_worker, state, 0, nullptr)', source)
        self.assertIn('static unsigned __stdcall watchdog_worker', source)
        self.assertIn('doserrno_result=%d doserrno=%lu', source)
        owner = source.split('struct ExecuteWatchdog {', 1)[1].split('struct Session {', 1)[0]
        stop = owner.split('    void stop() {', 1)[1].split('    ~ExecuteWatchdog()', 1)[0]
        ordering = [stop.index(value) for value in ('InterlockedExchange(&state->stop_requested, 1)',
                    'SetEvent(state->stop_event)', 'WaitForSingleObject(thread, INFINITE)',
                    'if (joined != WAIT_OBJECT_0)', 'CloseHandle(thread)', 'CloseHandle(state->stop_event)',
                    'delete state')]
        self.assertEqual(ordering, sorted(ordering))
        self.assertIn('state = nullptr; thread = nullptr;', stop)
        self.assertIn('throw std::runtime_error("Watchdog join failed; unproven ownership retained")', stop)
        self.assertIn('ExecuteWatchdog(const ExecuteWatchdog &) = delete;', owner)
        self.assertIn('try { stop(); }', owner)
        invocation = source.split('        phase("execute", "begin");', 1)[1].split('        phase("flush", "begin");', 1)[0]
        self.assertLess(invocation.index('watchdog.mark_active();'), invocation.index('session.control->Execute('))
        self.assertLess(invocation.index('watchdog.mark_returned();'), invocation.index('phase("execute", "end", executed)'))
        self.assertLess(invocation.index('phase("execute", "end", executed)'), invocation.index('watchdog.stop();'))
        self.assertEqual(invocation.count('session.control->Execute('), 1)
        self.assertEqual(invocation.count('session.control->ExecuteCommandFile('), 1)
        self.assertIn('std::string("$$><") + argv[1]', invocation)
        self.assertNotIn('CSW_', owner)

    def test_watchdog_unavailable_and_measured_zero_stderr_remain_original(self):
        stdout = diagnostic_log().encode()
        prefix = b'HARNESS_EXECUTE_WAIT scheduled_seconds=5 active_before=1 active_after=1 '
        unavailable = prefix + b'qpc_native=0 qpc_error=31 tick=0 cpu_native=0 cpu_error=5 kernel=0 user=0 io_native=0 io_error=5 read_bytes=0 callback_count=0 callback_input_bytes=0\r\n'
        measured = prefix + b'qpc_native=1 qpc_error=0 tick=100 cpu_native=1 cpu_error=0 kernel=0 user=0 io_native=1 io_error=0 read_bytes=0 callback_count=0 callback_input_bytes=0\r\n'
        for label, original in (('unavailable', unavailable), ('measured-zero', measured)):
            row = self.prepare(label)
            self.ledger.outcome(row, returncode=0, stdout=stdout, stderr=original)
            self.assertEqual(Path(row['stdout']['artifact']['path']).read_bytes(), stdout)
            self.assertEqual(Path(row['stderr']['artifact']['path']).read_bytes(), original)
            self.assertEqual(row['log'], stdout.decode() + original.decode())
            self.assertTrue(row['phase_receipt_passed'])
        self.assertNotEqual(unavailable, measured)

    def test_watchdog_progress_cannot_qualify_timeout_or_missing_execute_end(self):
        prefix = b'HARNESS_CLOCK frequency=10000000 native=1 error=0\nHARNESS_BEGIN base=00400000 mode=block\nHARNESS_PHASE seq=1 name=execute edge=begin tick=100 qpc=1 error=0 hr=0 value=0\n'
        progress = b'HARNESS_EXECUTE_WAIT scheduled_seconds=30 active_before=1 active_after=1 qpc_native=1 qpc_error=0 tick=300000100 cpu_native=1 cpu_error=0 kernel=0 user=200000000 io_native=1 io_error=0 read_bytes=14457121 callback_count=0 callback_input_bytes=0\r\n'
        row = self.prepare('watchdog-timeout')
        error = subprocess.TimeoutExpired(['engine.exe', 'verify.cdb', 'block'], 35, output=prefix, stderr=progress)
        self.ledger.outcome(row, stdout=error.stdout, stderr=error.stderr, error=error)
        self.assertEqual(row['status'], 'failed')
        self.assertEqual(row['error']['timeout'], 35)
        self.assertFalse(row['phase_receipt_passed'])
        self.assertFalse(engine.terminal_cases([row], ['watchdog-timeout']))
        self.assertEqual(Path(row['stdout']['artifact']['path']).read_bytes(), prefix)
        self.assertEqual(Path(row['stderr']['artifact']['path']).read_bytes(), progress)

    def test_fallback_diagnostic_exception_cannot_skip_termination_call(self):
        self.assertIn('try { phase("fallback_end", "begin"); }\n'
                      '                catch (...) { fprintf(stderr, "HARNESS_ERROR fallback begin diagnostic failure\\n"); }\n'
                      '                // Diagnostic failures must never suppress the termination attempt.\n'
                      '                HRESULT hr = client->EndSession(DEBUG_END_ACTIVE_TERMINATE);', engine.HARNESS)
        self.assertIn('try { phase("fallback_end", "end", hr); }', engine.HARNESS)

    def synthetic_class(self):
        class Fake(unittest.TestCase):
            _class_cleanups = []
            setUpClass = classmethod(engine.DebuggerEngineTests.setUpClass.__func__)
            save_report = classmethod(engine.DebuggerEngineTests.save_report.__func__)
            execute = engine.DebuggerEngineTests.execute
            def runTest(self):
                pass
        return Fake

    def native_mocks(self):
        environment = dict(GITHUB_ACTIONS='true', CLASH_DEBUGGER_INTEGRATION='1',
                           RUNNER_TEMP=str(self.parent), CLASH_PROBE_ENGINE_ARTIFACT_DIR=str(self.parent / 'native-owned'),
                           CLASH_DEBUGGER_REPORT=str(self.parent / 'external-report.json'))
        original = engine.ArtifactStore
        return (patch.dict(os.environ, environment),
                patch.object(engine, 'ArtifactStore', side_effect=lambda parent: original(parent, disk_usage=disk)),
                patch.object(engine.shutil, 'which', return_value='C:/explicit/mock/cl.exe'),
                patch.object(engine.subprocess, 'CREATE_NO_WINDOW', 0, create=True))

    def test_mocked_class_compiles_and_launches_exact_retained_inputs(self):
        Fake = self.synthetic_class()
        calls = []
        def mocked_run(command, **kwargs):
            calls.append((command, kwargs))
            if kwargs['timeout'] == 60:
                root = Path(kwargs['cwd'])
                (root / 'engine.exe').write_bytes(b'original mock runner')
                (root / 'engine.obj').write_bytes(b'original mock object')
                return subprocess.CompletedProcess(command, 0, b'compiler original\xff', b'')
            directory = Path(kwargs['cwd'])
            self.assertEqual((directory / 'verify.cdb').read_bytes(), b'original\r\n')
            return subprocess.CompletedProcess(command, 0, diagnostic_log().encode(), b'')
        contexts = self.native_mocks()
        with contexts[0], contexts[1], contexts[2], contexts[3], patch.object(engine.subprocess, 'run', side_effect=mocked_run):
            Fake.setUpClass()
            Fake().execute(b'MZ mock', 'original\r\n', label='exact')
            Fake.doClassCleanups()
        report = json.loads((self.parent / 'external-report.json').read_bytes())
        self.assertEqual([call[1]['timeout'] for call in calls], [60, 35])
        self.assertTrue(all(call[1]['capture_output'] is True and 'text' not in call[1] for call in calls))
        self.assertEqual(report['cases'][0]['status'], 'completed')
        self.assertEqual(Path(report['compiler']['stdout']['artifact']['path']).read_bytes(), b'compiler original\xff')
        self.assertTrue((Path(report['artifact_directory']) / 'engine.obj').is_file())
        self.assertFalse(report['game_runtime_executed'])

    def test_mocked_compiler_timeout_retains_files_and_original_missing_stream(self):
        Fake = self.synthetic_class()
        def mocked_run(command, **kwargs):
            (Path(kwargs['cwd']) / 'engine.obj').write_bytes(b'partial original compiler object')
            raise subprocess.TimeoutExpired(command, 60, output=b'original compiler partial\xff', stderr=None)
        contexts = self.native_mocks()
        with contexts[0], contexts[1], contexts[2], contexts[3], patch.object(engine.subprocess, 'run', side_effect=mocked_run):
            with self.assertRaises(subprocess.TimeoutExpired):
                Fake.setUpClass()
            Fake.doClassCleanups()
        report = json.loads((self.parent / 'external-report.json').read_bytes())
        self.assertEqual(report['compiler']['status'], 'failed')
        self.assertEqual(report['compiler']['stderr'], {'available': False, 'artifact': None})
        self.assertEqual(Path(report['compiler']['stdout']['artifact']['path']).read_bytes(), b'original compiler partial\xff')
        self.assertEqual((Path(report['artifact_directory']) / 'engine.obj').read_bytes(), b'partial original compiler object')
        self.assertIsNotNone(report['first_failure'])

    def test_mocked_compiler_write_failure_retains_original_exception_as_cause(self):
        Fake = self.synthetic_class()
        error = subprocess.TimeoutExpired(['explicit compiler'], 60, output=b'full original error\xff', stderr=None)
        contexts = self.native_mocks()
        with contexts[0], contexts[1], contexts[2], contexts[3], patch.object(engine.subprocess, 'run', side_effect=error):
            original = engine.ArtifactStore.observation
            def failed_observation(store, name, raw):
                if name == 'compiler-stdout.bin':
                    raise engine.RetentionError('mock original storage failure', raw)
                return original(store, name, raw)
            # The factory is mocked, so patch the concrete class through our existing store.
            with patch.object(type(self.store), 'observation', failed_observation):
                with self.assertRaises(engine.RetentionError) as caught:
                    Fake.setUpClass()
            self.assertIs(caught.exception.__cause__, error)
            self.assertIs(Fake.compiler_original_error, error)
            self.assertEqual(Fake.compiler_original_streams, (error.stdout, None))
            self.assertEqual(Fake.compiler_receipt['status'], 'failed')
            self.assertFalse(Fake.compiler_receipt['raw_retention_complete'])
            self.assertTrue(Fake.store.failed)
            self.assertIn(error.stdout, Fake.store.pending)
            self.assertIsNotNone(Fake.ledger.failure)
            Fake.doClassCleanups()


class NativeLineEndingTests(unittest.TestCase):
    setUp = RetentionTests.setUp

    @staticmethod
    def endings(log, mode):
        # These are authored fixture lines, not normalization of an observation.
        return ''.join(line + ('\r\n' if mode == 'crlf' or mode == 'mixed' and index % 2 else '\n')
                       for index, line in enumerate(log.splitlines()))

    def test_lf_crlf_and_mixed_phase_receipts_preserve_original_raw_bytes(self):
        for mode in ('lf', 'crlf', 'mixed'):
            with self.subTest(mode=mode):
                log = self.endings(diagnostic_log(), mode)
                raw = log.encode('utf-8')
                self.assertTrue(engine.phase_receipt(log))
                row = self.ledger.prepare(b'MZ explicit mock', b'original\r\n',
                                          test='test_line_endings', label=mode, mode='block')
                self.ledger.outcome(row, returncode=0, stdout=raw, stderr=b'')
                self.assertEqual(row['log'], log)
                self.assertEqual(Path(row['stdout']['artifact']['path']).read_bytes(), raw)
                self.assertEqual(row['stdout']['artifact']['sha256'], engine.probe._sha(raw))
                self.assertTrue(engine.terminal_cases([row], [mode]))
        self.assertTrue(engine.phase_receipt(diagnostic_log().rstrip('\n')))

    def test_extra_or_bare_carriage_returns_and_malformed_terminal_rows_fail(self):
        log = diagnostic_log()
        lines = log.splitlines()
        targets = (lines[0], lines[2], lines[-2], lines[-1])
        for target in targets:
            for terminator in ('\r\r\n', '\r'):
                with self.subTest(target=target, terminator=repr(terminator)):
                    self.assertFalse(engine.phase_receipt(log.replace(target + '\n', target + terminator)))
            with self.subTest(extra=target):
                self.assertFalse(engine.phase_receipt(log + target + '\r\r\n'))
        for suffix in ('HARNESS_END malformed\r\n', 'HARNESS_COMPLETEX\r\n',
                       'HARNESS_COMPLETE trailing\r\n'):
            with self.subTest(suffix=suffix):
                self.assertFalse(engine.phase_receipt(log + suffix))

    def test_crlf_does_not_hide_failed_reordered_or_duplicate_phase_receipts(self):
        log = self.endings(diagnostic_log(), 'crlf')
        lines = log.splitlines(keepends=True)
        variants = (log.replace('qpc=1', 'qpc=0', 1),
                    log.replace('hr=0', 'hr=-2147467259', 1),
                    log.replace('value=6', 'value=0'),
                    ''.join(lines[:2] + [lines[3], lines[2]] + lines[4:]),
                    log + lines[2], log + 'HARNESS_ERROR original failure\r\n')
        for changed in variants:
            with self.subTest(changed=changed):
                self.assertFalse(engine.phase_receipt(changed))

    @staticmethod
    def assertions():
        class Comparisons(unittest.TestCase):
            assert_bound_records = engine.DebuggerEngineTests.assert_bound_records
            assert_pass = engine.DebuggerEngineTests.assert_pass
            assert_rejected = engine.DebuggerEngineTests.assert_rejected
        return Comparisons()

    @staticmethod
    def rendered_identity():
        data, report, scalar = engine.executable_fixture('1366x768')
        script, facts = engine.fixtures.render(data, report, scalar)
        header = next(line[len('.echo '):] for line in script.splitlines()
                      if line.startswith('.echo BNDLOAD contract='))
        result = 'BNDLOAD contract=' + facts['contract_id'] + ' candidate=' + facts['candidate_sha256']
        return facts, header, result

    def test_result_and_mismatch_receipts_accept_only_exact_lf_crlf_or_mixed_lines(self):
        facts, header, result = self.rendered_identity()
        prefix = diagnostic_log() + 'HARNESS_CONTEXT before=014c after=014c\n' + header + '\n'
        expected = [(facts['contract_id'], facts['candidate_sha256'], 'pass', str(facts['required_chunks']))]
        for mode in ('lf', 'crlf', 'mixed'):
            with self.subTest(mode=mode):
                passed = self.endings(prefix + result + ' result=pass chunks=' + str(facts['required_chunks']) + '\n', mode)
                self.assertEqual(engine.RESULT.findall(passed), expected)
                self.assertions().assert_pass(passed, facts)
                failed = self.endings(prefix + 'BNDLOAD_MISMATCH chunk=2\n' + result + ' result=fail\n', mode)
                self.assertEqual(engine.MISMATCH.findall(failed), ['2'])
                self.assertions().assert_rejected(failed)

    def test_duplicate_malformed_or_wrong_result_fields_and_mismatches_cannot_pass(self):
        facts, header, result = self.rendered_identity()
        prefix = diagnostic_log() + 'HARNESS_CONTEXT before=014c after=014c\n' + header + '\r\n'
        valid = result + ' result=pass chunks=' + str(facts['required_chunks']) + '\r\n'
        variants = (prefix + valid + valid, prefix + valid + 'BNDLOAD malformed\r\n',
                    prefix + valid[:-2] + '\r\r\n', prefix + valid[:-2] + '\r',
                    prefix + valid.replace('chunks=' + str(facts['required_chunks']), 'chunks=0'),
                    prefix + valid.replace(facts['contract_id'], 'c' * 64),
                    prefix + valid.replace(facts['candidate_sha256'], 'd' * 64),
                    prefix + valid + 'BNDLOAD_MISMATCH chunk=2\r\n',
                    prefix + valid + 'BNDLOAD_MISMATCH malformed\r\n')
        for changed in variants:
            with self.subTest(changed=changed), self.assertRaises(AssertionError):
                self.assertions().assert_pass(changed, facts)
        failed = result + ' result=fail\r\n'
        for changed in (failed + failed, failed + 'BNDLOAD malformed\r\n',
                        failed[:-2] + '\r\r\n', failed[:-2] + '\r'):
            with self.subTest(changed=changed), self.assertRaises(AssertionError):
                self.assertions().assert_rejected(changed)
        for terminator in ('\r\r\n', '\r'):
            self.assertEqual(engine.MISMATCH.findall('BNDLOAD_MISMATCH chunk=2' + terminator), [])

    def test_rendered_header_is_required_unique_ordered_and_bound_to_stage_resolution_and_ids(self):
        facts, header, result = self.rendered_identity()
        suffix = result + ' result=pass chunks=' + str(facts['required_chunks']) + '\r\n'
        prefix = diagnostic_log() + 'HARNESS_CONTEXT before=014c after=014c\n'
        valid = prefix + header + '\r\n' + suffix
        self.assertions().assert_pass(valid, facts)
        variants = (prefix + suffix, valid + header + '\r\n', prefix + suffix + header + '\r\n',
                    valid.replace(header, header.replace(facts['stage'], 'foreign-stage')),
                    valid.replace(header, header.replace('resolution=1366x768', 'resolution=1280x720')),
                    valid.replace(header, header.replace('resolution=1366x768', 'resolution=01366x768')),
                    valid.replace(header, header.replace(facts['contract_id'], 'e' * 64)),
                    valid.replace(header, header.replace(facts['candidate_sha256'], 'f' * 64)),
                    prefix + header + '\r\r\n' + suffix, valid + 'BNDLOAD unexpected\r\n')
        for changed in variants:
            with self.subTest(changed=changed), self.assertRaises((AssertionError, ValueError)):
                self.assertions().assert_pass(changed, facts)
        # Intentional parser/read failures can omit the result, but the emitted
        # canonical identity header is still required and retained.
        self.assertions().assert_rejected(prefix + header + '\r\nSyntax error\r\n', syntax_valid=False)
        for changed in (prefix, prefix + header + '\r\n' + header + '\r\n',
                        prefix + header.replace(facts['stage'], 'foreign-stage') + '\r\n'):
            with self.subTest(rejected=changed), self.assertRaises((AssertionError, ValueError)):
                self.assertions().assert_rejected(changed, syntax_valid=False)


class CastleReportTests(unittest.TestCase):
    setUp = RetentionTests.setUp

    def owner(self):
        return SimpleNamespace(store=self.store, ledger=self.ledger, records=self.ledger.records,
                               root=self.store.root, compiler_receipt={'status':'completed'})

    def complete(self):
        for label, accepted in castle.EXPECTED.items():
            row = self.ledger.prepare(b'MZ explicit mock', b'mocked original\r\n', test='test_mocked_castle',
                                      label=label, mode='file' if label=='fixed-file' else 'block')
            log = diagnostic_log() + 'HARNESS_CONTEXT before=014c after=014c\n'
            if label == 'aslr':
                log = log.replace('base=00400000','base=00500000')
            log += 'OCEM_CONTRACT_PASS explicit_mock_only\n' if accepted else 'OCEM_INCOMPLETE\n'
            self.ledger.outcome(row, returncode=0, stdout=log.encode(), stderr=b'')

    def report(self):
        destination = self.parent / ('castle-report-' + str(len(list(self.parent.glob('castle-report-*')))) + '.json')
        with patch.dict(os.environ, RUNNER_TEMP=str(self.parent), CLASH_ORDINARY_ENTRY_ENGINE_REPORT=str(destination)):
            castle.MatrixEngineTests.save_report.__func__(self.owner())
        return json.loads(destination.read_bytes())

    def test_seven_terminal_mocked_cases_publish_exact_raw_artifacts(self):
        self.complete()
        report = self.report()
        self.assertTrue(report['completed'])
        self.assertTrue(report['passed'])
        self.assertEqual(report['expected_cases'],7)
        self.assertEqual({row['case'] for row in report['cases']},set(castle.EXPECTED))
        self.assertFalse(report['native_cleanup_verified'])
        self.assertFalse(report['promotion_ready'])
        for row in report['cases']:
            raw = Path(row['stdout']['artifact']['path']).read_bytes()
            self.assertEqual(raw.decode('utf-8'),row['log'])
            self.assertEqual(Path(row['verify.cdb']['path']).read_bytes(),b'mocked original\r\n')

    def test_seven_pending_labels_and_missing_case_cannot_complete(self):
        self.ledger.records.extend(dict(case=label,log='',returncode=None,status='pending',
                                       raw_retention_complete=False,phase_receipt_passed=False)
                                   for label in castle.EXPECTED)
        report = self.report()
        self.assertFalse(report['completed'])
        self.assertFalse(report['passed'])
        self.ledger.records.pop()
        self.assertFalse(self.report()['completed'])

    def test_duplicate_failed_and_false_phase_claims_reject(self):
        self.complete()
        for kind in ('duplicate','failed','missing-phase'):
            with self.subTest(kind=kind):
                row = self.ledger.records[-1]
                saved = dict(row)
                if kind=='duplicate':
                    row['case']=self.ledger.records[0]['case']
                elif kind=='failed':
                    row.update(status='failed',returncode=2)
                else:
                    row['log']=row['log'].replace('HARNESS_COMPLETE','missing original completion')
                    row['phase_receipt_passed']=True
                report = self.report()
                self.assertFalse(report['completed'])
                self.assertFalse(report['passed'])
                row.clear();row.update(saved)

    def test_first_failure_and_retention_debt_are_sticky_even_with_complete_cases(self):
        self.complete()
        self.ledger.fail('retained earlier source failure')
        report = self.report()
        self.assertFalse(report['completed'])
        self.assertFalse(report['passed'])
        self.assertEqual(report['first_failure'],'retained earlier source failure')
        self.store.failed=True
        report=self.report()
        self.assertTrue(report['retention_debt'])
        self.assertFalse(report['passed'])

    def test_all_three_native_workflows_bind_artifacts_in_allowed_step_context(self):
        for workflow,folder in (('framed-probe-engine.yml','framed-probe-engine-artifacts'),
                                ('complete-small-world.yml','complete-small-world-engine-artifacts'),
                                ('ordinary-castle-entry-matrix.yml','castle-matrix-engine-artifacts')):
            with self.subTest(workflow=workflow):
                raw=(engine.ROOT/'.github'/'workflows'/workflow).read_text(encoding='utf-8')
                # GitHub permits runner at step env/run, not jobs.<id>.env.
                for block in re.findall(r'^    env:\n((?:      [^\n]*\n)*)',raw,re.M):
                    self.assertNotIn('runner.',block)
                    self.assertNotIn('CLASH_PROBE_ENGINE_ARTIFACT_DIR',block)
                assignment="$env:CLASH_PROBE_ENGINE_ARTIFACT_DIR = Join-Path $env:RUNNER_TEMP '"+folder+"'"
                self.assertIn(assignment,raw)
                self.assertLess(raw.index(assignment),raw.index('suite = unittest.defaultTestLoader.discover'))


if __name__ == '__main__':
    unittest.main()
