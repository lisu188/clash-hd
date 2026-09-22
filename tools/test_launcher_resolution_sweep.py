"""Source-only matrix coverage and startup-diagnostic boundary tests."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import launcher_resolution_sweep as tool


class ResolutionSweepTests(unittest.TestCase):
    def test_every_advertised_profile_and_resolution_is_planned(self):
        plan = tool.inventory()
        manifest = tool.presets.load_manifest()
        expected = {(profile, resolution) for profile, config in manifest['profiles'].items()
                    for resolution in config['resolutions']}
        self.assertEqual({(r['profile'], r['resolution']) for r in plan['cases']}, expected)
        self.assertEqual(plan['count'], len(expected))
        self.assertEqual(plan['count'], 30)
        self.assertIn(('classic', '3840x2160'), expected)
        self.assertIn(('framed', '3440x1440'), expected)
        self.assertIn(('modalwidgets', '802x602'), expected)
        self.assertEqual(plan['manifest_sha256'], hashlib.sha256(tool.canonical(manifest)).hexdigest())
        self.assertFalse(plan['game_runtime_executed'])
        self.assertFalse(plan['custom_exhaustively_executed'])

    def test_all_startup_passes_never_substitute_for_gameplay(self):
        plan = tool.inventory()
        rows = [dict(tool.base_record(case), startup_passed=True) for case in plan['cases']]
        report = tool.aggregate(plan, rows)
        self.assertTrue(report['startup_matrix_passed'])
        self.assertEqual(report['observed'], 30)
        self.assertFalse(report['all_resolutions_working'])
        self.assertFalse(report['promotion_ready'])
        self.assertTrue(all(report['gameplay_missing'].values()))

    def test_missing_duplicate_unknown_or_mixed_recipe_rows_are_not_accepted(self):
        plan = tool.inventory()
        rows = [dict(tool.base_record(case), startup_passed=True) for case in plan['cases']]
        self.assertFalse(tool.aggregate(plan, rows[:-1])['startup_matrix_passed'])
        self.assertFalse(tool.aggregate(plan, [])['all_resolutions_working'])
        for changed in (rows + [rows[0]], [dict(rows[0], id='missing/800x600')],
                        [dict(rows[0], stage='different')], [dict(rows[0], recipe_revision='different')]):
            with self.assertRaises(ValueError):
                tool.aggregate(plan, changed)
        with self.assertRaises(ValueError):
            tool.aggregate(dict(plan, cases=[]), [])
        for value in (False, None, 1, 'true'):
            changed = [dict(rows[0], startup_passed=value)] + rows[1:]
            self.assertFalse(tool.aggregate(plan, changed)['startup_matrix_passed'])

    def test_no_profile_is_silently_removed_from_matrix(self):
        manifest = tool.presets.load_manifest()
        del manifest['profiles']['modalwidgets']
        with self.assertRaises(ValueError):
            tool.inventory(manifest)
        manifest = tool.presets.load_manifest()
        manifest['profiles']['classic']['stage'] += '-wrong'
        with self.assertRaises(ValueError):
            tool.inventory(manifest)

    def test_default_and_profile_filtered_plans_never_launch_or_create_output(self):
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder) / 'out'
            for profile in ('classic', 'framed', 'completehd', 'modalwidgets'):
                result = subprocess.run([sys.executable, tool.__file__, '--profile', profile, '--out', str(out)],
                                        capture_output=True, text=True, timeout=20)
                self.assertEqual(result.returncode, 0, result.stderr)
                plan = json.loads(result.stdout)
                self.assertTrue(all(r['profile'] == profile for r in plan['cases']))
                self.assertFalse(plan['game_runtime_executed'])
                self.assertFalse(out.exists())
            result = subprocess.run([sys.executable, tool.__file__, '--profile', 'modalwidgets', '--resolution', '3840x2160'],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertFalse(out.exists())

    def test_startup_requires_real_completion_dimensions_nonblank_stable_and_palette(self):
        case = tool.inventory()['cases'][0]
        log = ('REAL_LOADED pid=123 base=00400000 entry=004731b6 executable_sections_match=1\n'
               'REAL_EXE_ENTRY observed=1\n'
               'REAL_END entered=1 exited=0 exception_stop=0 elapsed_ms=30000\n'
               'REAL_CLEANUP absent=1 exit=80004005\n')
        sample = dict(width=case['width'], height=case['height'], nonzero_indices=250000,
                      raw_sha256='a'*64, palette_mode='paused_diagnostic_proxy_private_palette')
        with patch.object(tool.smoke, 'render', return_value=[sample.copy(), sample.copy()]):
            good = tool.startup_audit(Path('synthetic'), case, log, 0)
            self.assertTrue(good['passed'])
            self.assertFalse(good['gameplay_verified'])
            self.assertFalse(good['menu_visual_acceptance'])
            self.assertFalse(good['full_visible_composition'])
            self.assertFalse(tool.startup_audit(Path('synthetic'), case, log, 2)['passed'])
            self.assertFalse(tool.startup_audit(Path('synthetic'), case, log.replace('exited=0', 'exited=1'), 0)['passed'])
        for samples in ([], [sample.copy()], [sample.copy(), dict(sample, width=1920)],
                        [sample.copy(), dict(sample, raw_sha256='b'*64)],
                        [sample.copy(), dict(sample, nonzero_indices=0)],
                        [sample.copy(), dict(sample, palette_mode='grayscale_index_preview')]):
            with patch.object(tool.smoke, 'render', return_value=samples):
                self.assertFalse(tool.startup_audit(Path('synthetic'), case, log, 0)['passed'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
