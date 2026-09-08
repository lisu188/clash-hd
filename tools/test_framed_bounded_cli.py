from contextlib import redirect_stdout, redirect_stderr
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
import build_framed_bounded_candidate as cli


class BoundedOutputTests(unittest.TestCase):
    def test_new_outputs_are_verified_and_reported_without_executing_them(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source, output, report = root/'source.exe', root/'new.exe', root/'new.json'
            source.write_bytes(b'synthetic original')
            image = b'synthetic candidate, never executed'
            metadata = {'output_sha256': cli.camera.sha(image), 'game_runtime_executed': False}
            with patch.object(cli, '_outputs', return_value=(output,report)), patch.object(cli.bounded, 'build_candidate', return_value=(image,metadata)), redirect_stdout(io.StringIO()) as out:
                code = cli.main(['--original',str(source),'--resolution','1366x768','--output',str(output),'--report-json',str(report)])
            self.assertEqual(code,0)
            self.assertEqual(output.read_bytes(),image)
            self.assertEqual(json.loads(report.read_text())['output_sha256'],cli.camera.sha(image))
            self.assertEqual(json.loads(out.getvalue())['stage'],cli.bounded.STAGE)
            self.assertIs(json.loads(out.getvalue())['written'],True)
            self.assertIs(json.loads(out.getvalue())['game_runtime_executed'],False)
            self.assertEqual(source.read_bytes(),b'synthetic original')

    def test_unknown_original_is_rejected_in_preflight(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp)/'source.exe'; source.write_bytes(b'unknown')
            with redirect_stderr(io.StringIO()), redirect_stdout(io.StringIO()):
                self.assertEqual(cli.main(['--original',str(source),'--resolution','1366x768','--preflight']),1)

    def test_racing_output_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); source, output, report = root/'source.exe', root/'new.exe', root/'new.json'
            source.write_bytes(b'synthetic original')
            def build(*args):
                output.write_bytes(b'other writer')
                return b'new', {'output_sha256':cli.camera.sha(b'new')}
            with patch.object(cli,'_outputs',return_value=(output,report)), patch.object(cli.bounded,'build_candidate',side_effect=build), redirect_stderr(io.StringIO()):
                self.assertEqual(cli.main(['--original',str(source),'--resolution','1366x768','--output',str(output),'--report-json',str(report)]),1)
            self.assertEqual(output.read_bytes(),b'other writer')
            self.assertFalse(report.exists())


if __name__ == '__main__':
    unittest.main()
