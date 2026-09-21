"""Pure source, snapshot, menu identity and fitted-display regressions."""
from contextlib import redirect_stderr,redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image
import resolution_playability as tool


class PlayabilityTests(unittest.TestCase):
    def test_display_fit_covers_every_launcher_preset_without_changing_primary(self):
        for case in tool.matrix.inventory():
            width,height=map(int,case['resolution'].split('x'))
            for screen in ((1024,768),(1920,1080),(3840,2160)):
                w,h=tool.fit_size(width,height,*screen)
                self.assertLessEqual(w,screen[0]);self.assertLessEqual(h,screen[1])
                self.assertLessEqual(abs(w*height-h*width),max(width,height))
                if width<=screen[0] and height<=screen[1]:self.assertEqual((w,h),(width,height))
        for args in ((0,480,1920,1080),(800,600,True,768)):
            with self.assertRaises(ValueError):tool.fit_size(*args)

    def test_whole_menu_identity_excludes_only_cursor_corner_not_missing_labels(self):
        native=Image.new('RGB',(640,480),(40,50,60))
        raw=bytearray(native.tobytes())
        for y in range(32):raw[y*640*3:(y*640+32)*3]=b'\0'*96
        with patch.object(tool,'MENU_RGB_SHA256',hashlib.sha256(raw).hexdigest()):
            image=Image.new('RGB',(1920,1080));image.paste(native,(640,300))
            self.assertTrue(tool.menu_identity(image)['matches_original'])
            image.putpixel((650,310),(99,88,77))
            self.assertTrue(tool.menu_identity(image)['matches_original'])
            image.putpixel((864,485),(0,0,0))
            self.assertFalse(tool.menu_identity(image)['matches_original'])

    def test_primary_conversion_handles_padded_rows_and_requires_complete_palette(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'primary-00.json';w,h,pitch=802,602,804
            raw=(bytes([7])*w+b'\xff\xff')*h
            path.write_text(json.dumps(dict(width=w,height=h,pitch=pitch,proxy_private_palette=True)))
            path.with_suffix('.raw').write_bytes(raw)
            pal=path.with_name('primary-00-palette.bin');pal.write_bytes(bytes(v for i in range(256) for v in (i,i,255-i,0)))
            image,tight=tool.indexed_image(path)
            self.assertEqual(image.size,(w,h));self.assertEqual(image.getpixel((w-1,h-1)),(7,7,248))
            self.assertEqual(tight,bytes([7])*(w*h))
            pal.write_bytes(b'incomplete')
            with self.assertRaises(ValueError):tool.indexed_image(path)

    def test_source_has_no_undefined_module_dependencies(self):
        import builtins
        import symtable
        source=Path(tool.__file__).read_text()
        root=symtable.symtable(source,tool.__file__,'exec')
        known=set(vars(builtins)) | {s.get_name() for s in root.get_symbols() if s.is_assigned() or s.is_imported()} | {'__name__','__file__'}
        pending=[root]
        missing=set()
        while pending:
            table=pending.pop();pending.extend(table.get_children())
            missing.update(s.get_name() for s in table.get_symbols() if s.is_global() and s.is_referenced() and s.get_name() not in known)
        self.assertEqual(missing,set())

    def test_state_observer_does_not_add_breakpoints_or_mutate_game_state(self):
        original=tool.matrix.runtime.HARNESS
        generated=tool.observation_source(original)
        self.assertEqual(generated.count('AddBreakpoint('),original.count('AddBreakpoint('))
        self.assertIn('map_state(s,out,sample);',generated)
        for name in ('WriteVirtual(','SetThreadContext(','.call ','SetCurrentThreadId('):
            self.assertNotIn(name,tool.STATE_HELPER)
        with self.assertRaises(ValueError):tool.observation_source(generated)

    def test_input_receipt_rejects_missing_or_partial_aims(self):
        valid=dict(all_steps_accounted=True,steps=[dict(clicked=True,aim={'converged':True})])
        self.assertTrue(tool.input_success(valid))
        for value in ({},dict(all_steps_accounted=True,steps=[]),dict(valid,all_steps_accounted=False),
                      dict(valid,steps=[dict(clicked=True,aim={'converged':False})])):
            self.assertFalse(tool.input_success(value))

    def test_dry_run_and_missing_approval_never_start_runtime(self):
        with patch.object(sys,'argv',['test']),patch.object(tool,'run',side_effect=AssertionError('no runtime')),redirect_stdout(io.StringIO()) as output:
            self.assertEqual(tool.main(),0);self.assertFalse(json.loads(output.getvalue())['executed'])
        with patch.object(sys,'argv',['test','--execute']),patch.object(tool,'run',side_effect=AssertionError('no runtime')),redirect_stderr(io.StringIO()),self.assertRaises(SystemExit) as status:
            tool.main()
        self.assertEqual(status.exception.code,2)

    def test_current_classic_matrix_routes_the_actual_corrected_launcher(self):
        self.assertEqual(tool.matrix.BACKENDS['classic'],'classic')
        case=tool.matrix.select_case('classic','3840x2160')
        self.assertEqual(case['recipe_revision'],'classic_menu_widgets_v1')
        self.assertTrue(case['stage'].endswith('-menuwidgets-validation'))

    def test_success_requires_input_pixels_cleanup_and_original_identity(self):
        flags=['--execute','--approval-text','test','--runtime','a','--manifest','b','--proxy','c','--out','d']
        success=dict(errors=[],menu_and_campaign_input_passed=True,map_controls_pixels_passed=True,
                     outcome={'observation_complete':True},reference_unchanged=True,retained_process_exited=True,native_input_passed=True)
        for field in (None,'menu_and_campaign_input_passed','map_controls_pixels_passed','outcome','reference_unchanged','retained_process_exited','native_input_passed'):
            row=dict(success)
            if field:row[field]={'observation_complete':False} if field=='outcome' else False
            with patch.object(sys,'argv',['test',*flags]),patch.object(tool,'run',return_value=row),redirect_stdout(io.StringIO()):
                self.assertEqual(tool.main(),0 if field is None else 1)


if __name__=='__main__':unittest.main(verbosity=2)
