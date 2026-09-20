"""Nonexecuting selection and opt-in checks for the isolated focus adapter."""
from contextlib import redirect_stderr
import io
import sys
import unittest
from unittest.mock import patch
import runner_menu_input as tool

class RunnerFocusTests(unittest.TestCase):
    def test_thread_pairs_are_unique_and_never_attach_a_thread_to_itself(self):
        self.assertEqual(tool.attach_pairs(1,2,3),[(1,2),(1,3)])
        self.assertEqual(tool.attach_pairs(1,2,2),[(1,2)])
        self.assertEqual(tool.attach_pairs(1,1,2),[(1,2)])
        self.assertEqual(tool.attach_pairs(1,0,1),[])
        for args in ((0,2,3),(1,2,0),(True,2,3),(1,2,False)):
            with self.assertRaises(ValueError):tool.attach_pairs(*args)

    def test_no_native_windows_calls_without_explicit_runner_opt_in(self):
        for flags in ([],['--approval-text','test','--owner-creation','1']):
            with patch.object(sys,'argv',['test',*flags]),patch.object(tool.owned,'win32',side_effect=AssertionError('no Windows')),redirect_stderr(io.StringIO()),self.assertRaises(SystemExit) as error:
                tool.main()
            self.assertEqual(error.exception.code,2)

if __name__=='__main__':unittest.main(verbosity=2)
