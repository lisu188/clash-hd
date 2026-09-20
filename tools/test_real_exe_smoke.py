import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('real_exe_smoke', Path(__file__).with_name('real_exe_smoke.py'))
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)


class RealExeSmokeTests(unittest.TestCase):
    def test_default_dry_run_never_reads_assets_or_creates_output(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            result = subprocess.run([sys.executable, tool.__file__, '--runtime', str(root/'missing'),
                '--manifest', str(root/'missing.json'), '--out', str(root/'output')], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse(json.loads(result.stdout)['executed'])
            self.assertEqual(list(root.iterdir()), [])

    def test_invalid_duration_is_rejected_before_execution(self):
        with tempfile.TemporaryDirectory() as folder:
            for value in ('0', '91', '-1', 'nan'):
                result = subprocess.run([sys.executable, tool.__file__, '--runtime', folder, '--manifest', folder,
                    '--out', str(Path(folder)/'output'), '--seconds', value], capture_output=True, text=True)
                self.assertEqual(result.returncode, 2, result.stdout)
            self.assertEqual(list(Path(folder).iterdir()), [])

    def test_reference_path_escape_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            manifest = {'runtime': {'files': [{'path': '../outside.exe', 'size': 1, 'sha256': 'a'*64}]}}
            with self.assertRaisesRegex(ValueError, 'escapes'):
                tool.verify(root, manifest)

    def test_reference_size_and_hash_mismatch_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root/'clash95.exe').write_bytes(b'not the game')
            for size in (1, 12):
                manifest = {'runtime': {'files': [{'path': 'clash95.exe', 'size': size, 'sha256': 'a'*64}]}}
                with self.assertRaisesRegex(ValueError, 'mismatch'):
                    tool.verify(root, manifest)

    def test_indexed_frame_conversion_remains_diagnostic(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root/'primary-00.raw').write_bytes(bytes(range(256))*1200)
            (root/'primary-00.json').write_text(json.dumps({'width':640, 'height':480, 'pitch':640}))
            result = tool.render(root)
            self.assertEqual(len(result),1)
            self.assertEqual(result[0]['palette_mode'],'grayscale_index_preview')
            self.assertFalse(result[0]['visual_acceptance'])
            self.assertEqual(result[0]['nonzero_indices'], 255*1200)
            self.assertTrue((root/'primary-00.png').is_file())

    def test_observation_completion_requires_end_entry_identity_and_cleanup(self):
        log = ('REAL_LOADED pid=123 base=00400000 entry=004731b6 executable_sections_match=1\n'
               'REAL_EXE_ENTRY observed=1\n'
               'REAL_END entered=1 exited=0 exception_stop=0 elapsed_ms=40000\n'
               'REAL_CLEANUP absent=1 exit=80004005\n')
        self.assertTrue(tool.outcome(log, 0)['observation_complete'])
        cases = [(log, 2), (log.replace('exception_stop=0', 'exception_stop=1'), 4)]
        for line in log.splitlines():
            cases.extend(((log.replace(line+'\n', ''), 0), (log+line+'\n', 0)))
        cases.extend(((log+'REAL_HARNESS_ERROR pause event hr=00000001 winerror=0\n', 0),
                      (log+'REAL_WAIT_ERROR hr=80004005\n', 0)))
        for changed, code in cases:
            with self.subTest(log=changed, code=code):
                self.assertFalse(tool.outcome(changed, code)['observation_complete'])

    def test_first_attempt_pause_failure_is_not_a_completed_observation(self):
        log = ('REAL_LOADED pid=5804 base=00400000 entry=004731b6 executable_sections_match=1\n'
               'REAL_EXE_ENTRY observed=1\nREAL_CLEANUP absent=1 exit=80004005\n'
               'REAL_HARNESS_ERROR pause event hr=00000001 winerror=0\n')
        for code in (0,2):
            result = tool.outcome(log, code)
            self.assertTrue(result['entry_observed'])
            self.assertTrue(result['owned_process_absent'])
            self.assertFalse(result['observation_complete'])
            self.assertEqual(len(result['harness_errors']),1)

    def test_harness_uses_owned_handles_and_no_input_injection(self):
        for text in ('JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE', 'DEBUG_END_ACTIVE_TERMINATE',
                     'AssignProcessToJobObject', 'REAL_EXE_ENTRY observed=1'):
            self.assertIn(text,tool.HARNESS)
        for text in ('SendInput(', 'PostMessage(', 'SetCursorPos(', 'WriteVirtual('):
            self.assertNotIn(text,tool.HARNESS)


if __name__ == '__main__':
    unittest.main(verbosity=2)
