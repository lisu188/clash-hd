"""Portable mocked lifecycle/Win32-boundary tests; launches no process."""
from __future__ import annotations

import ctypes as C
import io
import os
from pathlib import PureWindowsPath
import stat
import subprocess
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent))
import owned_hidden_process as hidden


class Log:
    def __init__(self):
        self.flushed = False
        self.closed = False

    def fileno(self):
        return 17

    def writable(self):
        return not self.closed

    def flush(self):
        self.flushed = True


class FakeWindows:
    def __init__(self):
        self.events = []
        self.fail = None
        self.result = None
        self.children = 2
        self.actual = r'C:\host\observer.exe'
        self.creation = 123456
        self.launch_arguments = None

    def event(self, name, *values):
        self.events.append((name, *values))
        if name == self.fail:
            raise OSError('mock failure: ' + name)

    def desktop(self, name):
        self.event('desktop', name)
        return 11

    def job(self):
        self.event('job')
        return 12

    def configure_job(self, job):
        self.event('configure', job)

    def launch(self, executable, command, cwd, block, desktop, stdout, info):
        self.event('launch')
        self.launch_arguments = (executable, command, cwd, block, desktop, stdout)
        info.hProcess, info.hThread, info.dwProcessId, info.dwThreadId = 13, 14, 15, 16
        self.event('created')

    def assign(self, job, process):
        self.event('assign', job, process)

    def identity(self, process):
        self.event('identity', process)
        return self.actual, self.creation

    def resume(self, thread):
        self.event('resume', thread)

    def close_handle(self, handle):
        self.event('close_handle', handle)

    def close_desktop(self, handle):
        self.event('close_desktop', handle)

    def status(self, process, milliseconds):
        self.event('status', process, milliseconds)
        return self.result

    def terminate_job(self, job):
        self.event('terminate_job', job)
        self.children = 0
        if self.result is None:
            self.result = 1

    def terminate_process(self, process):
        self.event('terminate_process', process)
        self.result = 1

    def wait_job_empty(self, job, timeout):
        self.event('job_empty', job, timeout)
        if self.children:
            raise hidden.HiddenProcessError('children remain')


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.api, self.log = FakeWindows(), Log()
        def path(value, kind):
            return str(PureWindowsPath(hidden._absolute_local(value)))
        for target, options in (
            ('_Windows', dict(return_value=self.api)),
            ('_checked_path', dict(side_effect=path)),
        ):
            patcher = patch.object(hidden, target, **options)
            patcher.start()
            self.addCleanup(patcher.stop)
        patcher = patch.object(hidden.os, 'fstat', return_value=SimpleNamespace(st_mode=stat.S_IFREG))
        patcher.start()
        self.addCleanup(patcher.stop)

    def launch(self, **changes):
        values = dict(argv=[r'C:\host\observer.exe', 'argument with space', 'quote"tail\\'],
                      cwd=r'C:\game', env={'SystemRoot': r'C:\Windows'}, stdout=self.log)
        values.update(changes)
        return hidden.OwnedHiddenProcess(**values)

    def test_assign_and_identity_precede_resume_and_stdout_remains_owned(self):
        with self.launch() as process:
            self.assertEqual((process.pid, process.creation_filetime), (15, 123456))
            names = [row[0] for row in self.api.events]
            self.assertLess(names.index('configure'), names.index('launch'))
            self.assertLess(names.index('launch'), names.index('assign'))
            self.assertLess(names.index('assign'), names.index('identity'))
            self.assertLess(names.index('identity'), names.index('resume'))
            self.assertEqual(process.command_line, subprocess.list2cmdline(process.args))
            self.assertTrue(self.log.flushed)
            self.assertIsNone(process.poll())
        self.assertEqual(process.cleanup, dict(host_exited=True, job_empty=True, handles_closed=True, errors=[]))
        self.assertFalse(self.log.closed)
        self.assertEqual(self.api.children, 0)

    def test_normal_host_exit_still_terminates_surviving_children(self):
        process = self.launch()
        self.api.result = 0
        self.assertEqual(process.wait(0), 0)
        self.assertEqual(self.api.children, 2)
        process.close()
        self.assertIn(('terminate_job', 12), self.api.events)
        self.assertEqual(self.api.children, 0)
        self.assertEqual(process.poll(), 0)

    def test_assignment_failure_kills_suspended_host_before_any_resume(self):
        self.api.fail = 'assign'
        with self.assertRaisesRegex(OSError, 'assign'):
            self.launch()
        self.assertNotIn('resume', [row[0] for row in self.api.events])
        self.assertIn(('terminate_process', 13), self.api.events)
        for handle in (12, 13, 14):
            self.assertIn(('close_handle', handle), self.api.events)
        self.assertIn(('close_desktop', 11), self.api.events)

    def test_failure_after_create_still_cleans_retained_process(self):
        self.api.fail = 'created'
        with self.assertRaisesRegex(OSError, 'created'):
            self.launch()
        self.assertIn(('terminate_process', 13), self.api.events)
        self.assertIn(('close_handle', 14), self.api.events)

    def test_bad_identity_and_resume_failure_terminate_whole_job(self):
        for name in ('path', 'creation', 'resume'):
            with self.subTest(name=name):
                self.api.events.clear()
                self.api.result = None
                self.api.actual = r'C:\host\other.exe' if name == 'path' else r'C:\host\observer.exe'
                self.api.creation = 0 if name == 'creation' else 123456
                self.api.fail = 'resume' if name == 'resume' else None
                with self.assertRaises((OSError, hidden.HiddenProcessError)):
                    self.launch()
                self.assertIn(('terminate_job', 12), self.api.events)
                if name != 'resume':
                    self.assertNotIn('resume', [row[0] for row in self.api.events])

    def test_job_configuration_failure_never_launches(self):
        self.api.fail = 'configure'
        with self.assertRaisesRegex(OSError, 'configure'):
            self.launch()
        self.assertNotIn('launch', [row[0] for row in self.api.events])
        self.assertIn(('close_handle', 12), self.api.events)
        self.assertIn(('close_desktop', 11), self.api.events)

    def test_timeout_keeps_ownership_for_explicit_cleanup(self):
        process = self.launch()
        with self.assertRaises(subprocess.TimeoutExpired):
            process.wait(.001)
        self.assertIsNone(process.returncode)
        self.assertEqual(process._info.hProcess, 13)
        process.kill()
        self.assertEqual(process.wait(1), 1)
        process.close()

    def test_exit_code_259_is_not_confused_with_live_process(self):
        with self.launch() as process:
            self.api.result = 259
            self.assertEqual(process.wait(0), 259)

    def test_close_is_idempotent_and_context_propagates_exception(self):
        process = self.launch()
        with self.assertRaisesRegex(ValueError, 'body'):
            with process:
                raise ValueError('body')
        count = len(self.api.events)
        process.close()
        process.kill()
        self.assertEqual(len(self.api.events), count)

    def test_failed_cleanup_is_reported_while_all_handles_are_attempted(self):
        process = self.launch()
        self.api.fail = 'job_empty'
        with self.assertRaisesRegex(hidden.HiddenProcessError, 'job_empty'):
            process.close()
        self.assertFalse(process.cleanup['job_empty'])
        self.assertTrue(process.cleanup['handles_closed'])
        self.assertIn(('close_desktop', 11), self.api.events)

    def test_environment_is_forced_case_insensitively_without_mutating_caller(self):
        env = {'SystemRoot': 'C:\\Windows', 'clash_proxy_present': '1', '_nt_symbol_path': 'remote',
               '_NT_ALT_SYMBOL_PATH': 'remote'}
        original = dict(env)
        with self.launch(env=env) as process:
            self.assertEqual(process.environment['CLASH_PROXY_PRESENT'], '0')
            self.assertEqual(process.environment['_NT_SYMBOL_PATH'], '.')
            self.assertEqual(process.environment['_NT_ALT_SYMBOL_PATH'], '')
            self.assertNotIn('clash_proxy_present', process.environment)
            self.assertTrue(self.api.launch_arguments[3].endswith('\0\0'))
        self.assertEqual(env, original)

    def test_ambiguous_arguments_environment_and_paths_reject_before_api(self):
        cases = [dict(argv='C:\\host\\observer.exe'), dict(argv=[]), dict(argv=['relative.exe']),
                 dict(argv=['C:\\host\\observer.exe', 'bad\0argument']), dict(cwd='C:relative'),
                 dict(cwd='\\\\server\\share'), dict(cwd='C:\\game\\..\\other'),
                 dict(env={'PATH': 'a', 'path': 'b'}), dict(env={'bad=name': 'x'}),
                 dict(env={'A': 'bad\0value'}), dict(argv=['C:\\host\\observer.exe', 'x'*32768])]
        for values in cases:
            with self.subTest(values=list(values)):
                with self.assertRaises((ValueError, TypeError)):
                    self.launch(**values)
        self.assertEqual(self.api.events, [])

    def test_nonfile_stdout_rejects_before_api(self):
        with patch.object(hidden.os, 'fstat', return_value=SimpleNamespace(st_mode=stat.S_IFIFO)):
            with self.assertRaisesRegex(ValueError, 'regular file'):
                self.launch()
        self.assertEqual(self.api.events, [])


class NativeBoundaryTests(unittest.TestCase):
    def test_fixed_width_structures_have_windows_abi_sizes(self):
        is64 = C.sizeof(C.c_void_p) == 8
        self.assertEqual(C.sizeof(hidden.STARTUPINFO), 104 if is64 else 68)
        self.assertEqual(C.sizeof(hidden.STARTUPINFOEX), 112 if is64 else 72)
        self.assertEqual(C.sizeof(hidden.JOB_EXTENDED_LIMIT), 144 if is64 else 112)
        self.assertEqual(C.sizeof(hidden.JOB_ACCOUNTING), 48)

    def test_native_startup_inherits_only_two_private_handles(self):
        api = hidden._Windows.__new__(hidden._Windows)
        api.kernel = Mock()
        api.kernel.GetCurrentProcess.return_value = 101
        api.kernel.GetThreadErrorMode.return_value = 0x40
        def error_mode(mode, previous):
            if previous is not None:
                C.cast(previous, C.POINTER(hidden.DWORD)).contents.value = 0x40
            return True
        api.kernel.SetThreadErrorMode.side_effect = error_mode
        api.kernel.CloseHandle.return_value = True
        api.kernel.CreateFileW.return_value = 201
        def duplicate(*args):
            C.cast(args[3], C.POINTER(hidden.HANDLE)).contents.value = 200
            return True
        api.kernel.DuplicateHandle.side_effect = duplicate
        def initialize(attributes, count, flags, pointer):
            C.cast(pointer, C.POINTER(hidden.SIZE_T)).contents.value = 128
            return attributes is not None
        api.kernel.InitializeProcThreadAttributeList.side_effect = initialize
        inherited = []
        def update(attributes, flags, kind, handles, size, previous, returned):
            self.assertEqual(kind, 0x20002)
            inherited.extend(handles)
            self.assertEqual(size, 2*C.sizeof(hidden.HANDLE))
            return True
        api.kernel.UpdateProcThreadAttribute.side_effect = update
        observed = {}
        def create(executable, command, pa, ta, inherit, flags, block, cwd, startup_pointer, info_pointer):
            startup = C.cast(startup_pointer, C.POINTER(hidden.STARTUPINFOEX)).contents
            observed.update(executable=executable, command=command.value, cwd=cwd, flags=flags,
                            desktop=startup.StartupInfo.lpDesktop, inherit=inherit,
                            stdin=startup.StartupInfo.hStdInput, stdout=startup.StartupInfo.hStdOutput,
                            stderr=startup.StartupInfo.hStdError, show=startup.StartupInfo.wShowWindow,
                            startup_flags=startup.StartupInfo.dwFlags, attributes=startup.lpAttributeList)
            info = C.cast(info_pointer, C.POINTER(hidden.PROCESS_INFORMATION)).contents
            info.hProcess, info.hThread = 300, 301
            return True
        api.kernel.CreateProcessW.side_effect = create
        info = hidden.PROCESS_INFORMATION()
        with patch.dict(sys.modules, {'msvcrt': SimpleNamespace(get_osfhandle=lambda fd: 77)}), \
             patch.object(C, 'get_last_error', return_value=122, create=True):
            api.launch('C:\\host.exe', 'C:\\host.exe "argument"', 'C:\\game', 'A=B\0\0',
                       'private-test-desktop', Log(), info)
        self.assertEqual(inherited, [201, 200])
        self.assertEqual((observed['stdin'], observed['stdout'], observed['stderr']), (201, 200, 200))
        self.assertEqual(observed['desktop'], 'private-test-desktop')
        self.assertEqual(observed['flags'], 0x08080404)
        self.assertTrue(observed['inherit'])
        self.assertEqual(observed['show'], 0)
        self.assertEqual(observed['startup_flags'], 0x101)
        self.assertTrue(observed['attributes'])
        self.assertEqual((info.hProcess, info.hThread), (300, 301))
        self.assertEqual([c.args[0] for c in api.kernel.CloseHandle.call_args_list], [201, 200])
        api.kernel.DeleteProcThreadAttributeList.assert_called_once()
        self.assertEqual(api.kernel.SetThreadErrorMode.call_args_list[0].args[0], 0x8043)
        self.assertEqual(api.kernel.SetThreadErrorMode.call_args_list[-1].args[0], 0x40)

    def test_job_flag_only_kills_on_close_without_breakaway(self):
        api = hidden._Windows.__new__(hidden._Windows)
        api.kernel = Mock()
        def configure(job, kind, pointer, size):
            limit = C.cast(pointer, C.POINTER(hidden.JOB_EXTENDED_LIMIT)).contents
            self.assertEqual((job, kind, size), (12, 9, C.sizeof(hidden.JOB_EXTENDED_LIMIT)))
            self.assertEqual(limit.BasicLimitInformation.LimitFlags, 0x2000)
            return True
        api.kernel.SetInformationJobObject.side_effect = configure
        api.configure_job(12)

    def test_native_wait_failure_is_not_a_successful_exit(self):
        api = hidden._Windows.__new__(hidden._Windows)
        api.kernel = Mock()
        api.kernel.WaitForSingleObject.return_value = 0xffffffff
        with self.assertRaises(hidden.HiddenProcessError):
            api.status(13, 0)
        api.kernel.GetExitCodeProcess.assert_not_called()

    def test_timeout_validation_and_rounding(self):
        self.assertEqual(hidden._milliseconds(None), 0xffffffff)
        self.assertEqual(hidden._milliseconds(.0001), 1)
        for value in (-1, True, float('nan'), float('inf'), 4294967.295):
            with self.subTest(value=value), self.assertRaises(ValueError):
                hidden._milliseconds(value)

    @unittest.skipIf(os.name == 'nt', 'Non-Windows rejection applies on other hosts')
    def test_nonwindows_backend_refuses_native_launch(self):
        with self.assertRaisesRegex(OSError, 'Windows'):
            hidden._Windows()


if __name__ == '__main__':
    unittest.main()
