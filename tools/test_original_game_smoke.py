"""Offline input/boundary tests; these never launch a game or capture a screen."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import run_original_game_smoke as tool


class SmokeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'assets'; self.root.mkdir()
        self.data = b'MZ synthetic fixture only'
        (self.root / 'clash95.exe').write_bytes(self.data)
        self.digest = hashlib.sha256(self.data).hexdigest()
        self.manifest = dict(runtime=dict(files=[dict(path='clash95.exe', size=len(self.data), sha256=self.digest)],
                                         file_count=1, total_bytes=len(self.data)))
        self.guard = patch.object(tool, 'ORIGINAL_SHA', self.digest); self.guard.start(); self.addCleanup(self.guard.stop)

    def test_full_manifest_and_original_identity(self):
        self.assertEqual(tool.verify_assets(self.root, self.manifest),
                         {'clash95.exe': dict(bytes=len(self.data), sha256=self.digest)})
        with patch.object(tool, 'ORIGINAL_SHA', '0' * 64), self.assertRaises(ValueError):
            tool.verify_assets(self.root, self.manifest)

    def test_changed_missing_lfs_and_extra_files_fail(self):
        for data in (b'MZ changed', b'version https://git-lfs.github.com/spec/v1\n'):
            (self.root / 'clash95.exe').write_bytes(data)
            with self.assertRaises(ValueError): tool.verify_assets(self.root, self.manifest)
        (self.root / 'clash95.exe').write_bytes(self.data)
        (self.root / 'extra').write_bytes(b'x')
        with self.assertRaises(ValueError): tool.verify_assets(self.root, self.manifest)
        (self.root / 'clash95.exe').unlink()
        with self.assertRaises(OSError): tool.verify_assets(self.root, self.manifest)

    def test_traversal_duplicates_and_totals_fail(self):
        for name in ('../clash95.exe', '/clash95.exe', 'a/../clash95.exe', 'a\\clash95.exe', './clash95.exe'):
            bad = copy.deepcopy(self.manifest); bad['runtime']['files'][0]['path'] = name
            with self.subTest(name=name), self.assertRaises(ValueError): tool.verify_assets(self.root, bad)
        for key in ('file_count', 'total_bytes'):
            bad = copy.deepcopy(self.manifest); bad['runtime'][key] += 1
            with self.assertRaises(ValueError): tool.verify_assets(self.root, bad)
        bad = copy.deepcopy(self.manifest); bad['runtime']['files'] *= 2
        with self.assertRaises(ValueError): tool.verify_assets(self.root, bad)

    def test_default_is_nonexecuting_and_does_not_create_output(self):
        output = Path(self.temp.name) / 'new'
        result = subprocess.run([sys.executable, tool.__file__, '--assets', str(self.root),
                                 '--manifest', 'does-not-exist.json', '--output', str(output)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIs(json.loads(result.stdout)['executed'], False)
        self.assertFalse(output.exists())

    def test_existing_and_overlapping_output_fail_before_reads(self):
        for output in (self.root, self.root / 'child', Path(self.temp.name), Path(tool.__file__).parent / 'run-artifacts'):
            result = subprocess.run([sys.executable, tool.__file__, '--assets', str(self.root),
                                     '--manifest', 'absent', '--output', str(output)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 2, result.stderr)

    def test_execution_requires_actual_explicit_approval(self):
        output = Path(self.temp.name) / 'new'
        result = subprocess.run([sys.executable, tool.__file__, '--assets', str(self.root), '--manifest', 'absent',
                                 '--output', str(output), '--execute'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertFalse(output.exists())

    def test_capture_worker_requires_explicit_approval_before_windows_calls(self):
        output = Path(self.temp.name) / 'capture.png'
        result = subprocess.run([sys.executable, tool.__file__, '--capture', '1', '1', '1', str(output), 'bitblt'],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn('Capture requires', result.stderr)
        self.assertFalse(output.exists())

    def test_direct_runner_checks_approval_duration_and_original_before_windows(self):
        game = self.root / 'clash95.exe'
        for seconds, approval in ((25, ''), (25, '   '), (True, 'authorized'), (25.0, 'authorized'),
                                  (24, 'authorized'), (241, 'authorized')):
            with self.subTest(seconds=seconds, approval=approval), self.assertRaises(ValueError):
                tool.run_game(game, self.root, seconds, approval)
        game.write_bytes(b'MZ changed original')
        with self.assertRaisesRegex(ValueError, 'exact original'):
            tool.run_game(game, self.root, 180, 'authorized test fixture')


if __name__ == '__main__': unittest.main(verbosity=2)
