import hashlib
import subprocess
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import launcher_campaign_probe as tool


class CampaignProbeTests(unittest.TestCase):
    def test_dry_run_imports_no_native_tools_and_never_launches(self):
        with patch.object(tool.subprocess,'Popen',side_effect=AssertionError('no launch')):
            result=tool.run(SimpleNamespace(profile='modalwidgets',resolution='1024x768',execute=False))
        self.assertFalse(result['executed'])
        self.assertFalse(result['manual_input_proof'])
        self.assertEqual(result['actions'],['campaign button','first campaign choice'])

    def test_unknown_profile_or_resolution_is_not_silently_substituted(self):
        for profile,resolution in [('wrong','1024x768'),('modalwidgets','3840x2160')]:
            with self.assertRaises(ValueError):
                tool.run(SimpleNamespace(profile=profile,resolution=resolution,execute=False))

    def test_observer_only_adds_source_bound_read_only_callbacks(self):
        source=tool.native_observer(tool.smoke.HARNESS)
        self.assertIn('0x447700,0x448b90,0x40b660',source)
        self.assertIn('DEBUG_BREAKPOINT_ONE_SHOT',source)
        self.assertEqual(source.count('ROUTE_NATIVE'),1)
        for forbidden in ('WriteVirtual','SetThreadContext','SetValues','s.command("ed','s.command("r eip'):
            self.assertNotIn(forbidden,source)
        for old in ('seconds>90','        s.command("sxe av"); s.command("sxe eh");'):
            with self.assertRaises(ValueError):
                tool.native_observer(tool.smoke.HARNESS.replace(old,''))

    def test_no_callback_and_wrong_ip_are_never_input_success(self):
        self.assertEqual(tool.events('REAL_EXE_ENTRY observed=1\n'),[])
        line='ROUTE_NATIVE event=campaign ip=00447700 tid=42 raw_x=123 raw_y=-456 game_data=00510000'
        self.assertEqual(tool.events(line)[0]['event'],'campaign')
        self.assertEqual(tool.events(line)[0]['raw_y'],-456)
        for bad in (line+'\n'+line,line.replace('00447700','00447720'),line.replace('campaign','unobserved'),line+' extra'):
            with self.assertRaises(ValueError):tool.events(bad)

    def test_explicit_execution_needs_asset_and_approval_arguments(self):
        result=subprocess.run([sys.executable,tool.__file__,'--execute'],capture_output=True,text=True,timeout=10)
        self.assertEqual(result.returncode,2)
        self.assertIn('actual approval',result.stderr)


if __name__=='__main__':unittest.main(verbosity=2)
