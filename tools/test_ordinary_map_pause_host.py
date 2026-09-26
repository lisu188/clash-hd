"""Portable source-transform checks; no compilation, target or debugger launch."""
from __future__ import annotations

import unittest

import ordinary_map_pause_host as host
import real_exe_smoke


class PauseHostSourceTests(unittest.TestCase):
    def test_only_declared_source_changes_are_applied(self):
        original = real_exe_smoke.HARNESS
        rendered = host.render_source(original)
        self.assertIs(original, real_exe_smoke.HARNESS)
        for old, new in reversed(host.SOURCE_REPLACEMENTS):
            self.assertEqual(rendered.count(new), 1)
            rendered = rendered.replace(new, old, 1)
        self.assertEqual(rendered, original)

    def test_each_missing_anchor_fails_closed(self):
        for old, _new in host.SOURCE_REPLACEMENTS:
            with self.subTest(anchor=old), self.assertRaisesRegex(ValueError, 'anchor'):
                host.render_source(real_exe_smoke.HARNESS.replace(old, '', 1))

    def test_each_duplicated_anchor_fails_closed(self):
        for old, _new in host.SOURCE_REPLACEMENTS:
            with self.subTest(anchor=old), self.assertRaisesRegex(ValueError, 'anchor'):
                host.render_source(real_exe_smoke.HARNESS + old)

    def test_second_application_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'already contains'):
            host.render_source(host.render_source(real_exe_smoke.HARNESS))

    def test_non_source_input_is_rejected(self):
        for value in (None, b'code', 42):
            with self.subTest(value=value), self.assertRaises(TypeError):
                host.render_source(value)

    def test_unrelated_source_text_is_preserved(self):
        original = real_exe_smoke.HARNESS + '\n// independent harness annotation\n'
        self.assertTrue(host.render_source(original).endswith('// independent harness annotation\n'))

    def test_legacy_invocation_keeps_control_disabled(self):
        rendered = host.render_source(real_exe_smoke.HARNESS)
        self.assertIn('if (argc!=5 && argc!=6) return 2;', rendered)
        self.assertIn('PauseLeaseController leases(s,argc==6?argv[5]:nullptr,base);', rendered)
        constructor = host.CONTROLLER_SOURCE.split('PauseLeaseController(Session &owner,', 1)[1]
        self.assertLess(constructor.index('if (!control_directory) return;'),
                        constructor.index('enabled=true;'))
        self.assertIn('if (!enabled || ready_published || !entered) return;', rendered)
        self.assertIn('if (!enabled || !ready_published) return;', rendered)

    def test_entry_readiness_and_loop_service_are_at_owned_boundaries(self):
        rendered = host.render_source(real_exe_smoke.HARNESS)
        main = rendered.split('int main(int argc,char **argv) {', 1)[1]
        self.assertLess(main.index('REAL_LOADED'), main.index('PauseLeaseController leases'))
        self.assertIn('leases.service();\n            HRESULT hr=s.control->WaitForEvent(0,1000);', main)
        self.assertIn('"continue actual code");\n                leases.publish_ready(entered);', main)
        self.assertEqual(main.count('leases.publish_ready('), 1)
        self.assertLess(main.index('entered=true;'), main.index('leases.publish_ready(entered);'))


if __name__ == '__main__':
    unittest.main()
