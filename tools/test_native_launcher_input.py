"""Nonexecuting native-input boundaries and resolution translation."""
from contextlib import redirect_stdout,redirect_stderr
import io
import json
import sys
import unittest
from unittest.mock import patch
import native_launcher_input as tool

class NativeInputTests(unittest.TestCase):
    def test_every_preset_translates_the_same_native_menu_target(self):
        for row in tool.matrix.inventory():
            w,h=map(int,row['resolution'].split('x'))
            self.assertEqual(tool.route('campaign:224,185',row['resolution']),f'campaign:{224+(w-640)//2},{185+(h-480)//2}')

    def test_route_rejects_malformed_and_out_of_native_bounds(self):
        for value in ('','exit:640,12','x:1,480','x:-1,3','unknown space:1,2','a:1,2;'*5,'x:1,2;','x:1,2\n'):
            with self.subTest(value=value),self.assertRaises(ValueError):tool.route(value,'1024x768')

    def test_default_cli_never_invokes_runtime_or_input(self):
        with patch.object(sys,'argv',['test']),patch.object(tool,'observe',side_effect=AssertionError('no game')),redirect_stdout(io.StringIO()) as stream:
            self.assertEqual(tool.main(),0)
            self.assertFalse(json.loads(stream.getvalue())['input_injected'])

    def test_execution_requires_the_separate_native_input_opt_in(self):
        for flags in (['--execute'],['--execute','--allow-native-input'],['--execute','--approval-text','test'],
                      ['--execute','--allow-native-input','--approval-text','   ']):
            with self.subTest(flags=flags),patch.object(sys,'argv',['test',*flags]),patch.object(tool,'observe',side_effect=AssertionError('no game')),redirect_stderr(io.StringIO()),self.assertRaises(SystemExit) as status:
                tool.main()
            self.assertEqual(status.exception.code,2)

    def test_input_success_cannot_hide_runtime_or_identity_failure(self):
        argv=['test','--execute','--allow-native-input','--approval-text','test',
              '--runtime','runtime','--manifest','manifest','--proxy','proxy','--out','out']
        report=dict(errors=[],input_transition_observed=True,reference_assets_unchanged=True,
                    outcome={'observation_complete':True},candidate_unchanged=True,original_unchanged=True)
        for failure in (None,'errors','input_transition_observed','reference_assets_unchanged','outcome','candidate_unchanged','original_unchanged'):
            row=dict(report)
            if failure=='errors':row[failure]=['actual failure']
            elif failure=='outcome':row[failure]={'observation_complete':False}
            elif failure:row[failure]=False
            with self.subTest(failure=failure),patch.object(sys,'argv',argv),patch.object(tool,'observe',return_value=row),redirect_stdout(io.StringIO()):
                self.assertEqual(tool.main(),0 if failure is None else 1)

if __name__=='__main__':unittest.main(verbosity=2)
