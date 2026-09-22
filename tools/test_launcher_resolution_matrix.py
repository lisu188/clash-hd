"""Inventory and synthetic image/selection tests; no game or display API runs."""
from contextlib import redirect_stdout
import copy
import ctypes
import io
import json
from pathlib import Path
import struct
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import launcher_resolution_matrix as tool


class ResolutionMatrixTests(unittest.TestCase):
    def test_inventory_covers_every_profile_preset_once(self):
        expected=tool.presets.load_manifest()['profiles']
        rows=tool.inventory()
        self.assertEqual(len(rows),30)
        self.assertEqual({(r['profile'],r['resolution']) for r in rows},
                         {(p,r) for p,d in expected.items() for r in d['resolutions']})
        self.assertEqual(len({(r['profile'],r['resolution']) for r in rows}),len(rows))
        self.assertEqual(len({r['resolution'] for r in rows}),10)
        self.assertTrue(all(r['manifest_sha256']==tool.digest(tool.MANIFEST) for r in rows))

    def test_no_missing_backend_or_unadvertised_combo_can_silently_run(self):
        manifest=copy.deepcopy(tool.presets.load_manifest());manifest['profiles']['unknown']={}
        with patch.object(tool.presets,'load_manifest',return_value=manifest),self.assertRaises(ValueError):tool.inventory()
        for pair in (('modalwidgets','1366x768'),('classic','802x602'),('bad','800x600'),('framed','1600x900')):
            with self.subTest(pair=pair),self.assertRaises(ValueError):tool.select_case(*pair)

    def test_matrix_and_dry_run_never_start_process_or_change_display(self):
        for flags in (['--matrix'],['--profile','classic','--resolution','3840x2160']):
            with patch.object(sys,'argv',['test',*flags]),patch.object(tool,'run_case',side_effect=AssertionError('no runtime')),redirect_stdout(io.StringIO()) as stream:
                self.assertEqual(tool.main(),0)
                data=json.loads(stream.getvalue())
                self.assertTrue('include' in data or data['executed'] is False)

    def test_display_choice_requires_both_dimensions_and_32_bit_pixels(self):
        rows=[dict(width=w,height=h,bits=b,frequency=60) for w,h,b in
              ((1024,768,32),(3840,2160,32),(1920,1080,32),(1280,960,32),(1366,768,16))]
        self.assertEqual(tool.choose_display(rows,1280,720)['width'],1280)
        self.assertEqual(tool.choose_display(rows,1366,768)['width'],1920)
        self.assertEqual(tool.choose_display(rows,3440,1440)['width'],3840)
        self.assertIsNone(tool.choose_display(rows,4096,2160))
        with patch.object(tool,'os',SimpleNamespace(name='nt',environ={})),self.assertRaises(ValueError):
            with tool.RunnerDisplay(1920,1080):pass

    def test_devmode_layout_extracts_documented_fields(self):
        raw=ctypes.create_string_buffer(220);struct.pack_into('<5I',raw,168,32,3840,2160,0,60)
        self.assertEqual(tool.RunnerDisplay.row(raw),dict(width=3840,height=2160,bits=32,frequency=60))

    def test_stage_backend_identity_and_output_digest_are_mandatory(self):
        case=tool.select_case('modalwidgets','1920x1080')
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);exe=root/'candidate';exe.write_bytes(b'synthetic candidate')
            plan=SimpleNamespace(stage=case['stage'],candidate_exe=exe)
            record={'output_sha256':tool.digest(exe)}
            backend=SimpleNamespace(plan_candidate=lambda **kw:plan,ensure_candidate=lambda p:record)
            with patch.object(tool,'select_case',return_value=case),patch.object(tool.importlib,'import_module',return_value=backend),patch.object(tool.core,'display_for_plan',return_value=SimpleNamespace(recipe_revision=case['recipe_revision'])):
                path,built=tool.stage_candidate('modalwidgets','1920x1080',root/'original',root/'output')
                self.assertEqual(path,exe);self.assertEqual(built['case'] if 'case' in built else built['profile'],'modalwidgets')
                record['output_sha256']='a'*64
                with self.assertRaises(ValueError):tool.stage_candidate('modalwidgets','1920x1080',root/'original',root/'output')
                plan.stage='wrong'
                with self.assertRaises(ValueError):tool.stage_candidate('modalwidgets','1920x1080',root/'original',root/'output')

    def test_clipped_or_wrong_size_window_is_not_full_window_proof(self):
        import numpy as np
        from PIL import Image
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);w,h=1920,1080;x,y=(w-640)//2,(h-480)//2
            pixels=np.zeros((h,w,3),dtype=np.uint8);pixels[y:y+480,x:x+640]=[123,21,199]
            Image.fromarray(pixels).save(root/'primary.png')
            snapshots=[dict(width=w,height=h,png='primary.png',raw_sha256='a'*64,nonzero_indices=100000)]*3
            Image.fromarray(pixels).save(root/'window-01.png')
            good=tool.image_audit(root,'1920x1080',snapshots)
            self.assertTrue(good['requested_size']);self.assertTrue(good['window_primary_identical'])
            self.assertEqual(good['outer_nonblack_pixels_except_initial_cursor'],0)
            clipped=pixels.copy();clipped[:,1024:]=0;Image.fromarray(clipped).save(root/'window-01.png')
            bad=tool.image_audit(root,'1920x1080',snapshots)
            self.assertFalse(bad['window_primary_identical'])
            self.assertEqual(bad['window_mismatches'],0 if x+640<=1024 else (x+640-1024)*480)
            Image.fromarray(pixels[:,:1000]).save(root/'window-01.png')
            self.assertFalse(tool.image_audit(root,'1920x1080',snapshots)['window_primary_identical'])
            self.assertFalse(tool.image_audit(root,'1920x1080',[])['requested_size'])
            changed=copy.deepcopy(snapshots);changed[-1]['width']=1280
            self.assertFalse(tool.image_audit(root,'1920x1080',changed)['requested_size'])

    def test_receipt_summary_never_promotes_gameplay_or_swallows_missing_cases(self):
        reports=[dict(case=r,build_passed=True,startup_observed=True,full_window_observed=True) for r in tool.inventory()]
        summary=tool.summarize(reports)
        self.assertTrue(summary['all_startups_observed']);self.assertFalse(summary['all_gameplay_verified'])
        self.assertFalse(summary['custom_resolution_coverage']);self.assertFalse(summary['promotion_ready'])
        for wrong in (reports[:-1],reports+[reports[0]],reports+[dict(case={})]):
            with self.subTest(count=len(wrong)):
                self.assertFalse(tool.summarize(wrong)['all_startups_observed'])
        altered=copy.deepcopy(reports);altered[0]['case']['manifest_sha256']='0'*64
        self.assertFalse(tool.summarize(altered)['all_startups_observed'])
        altered=copy.deepcopy(reports);altered[0]['startup_observed']=1
        self.assertFalse(tool.summarize(altered)['all_startups_observed'])


if __name__=='__main__':unittest.main(verbosity=2)
