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

    def test_selected_unit_requires_live_map_context_and_bounded_index(self):
        state=dict(selected_stack=6,render_hook=0x40ad40,map_active_word=1,world_width=50,world_height=50)
        self.assertTrue(tool.selected_unit([state]))
        for key,value in (('selected_stack',True),('selected_stack',0xffffffff),('selected_stack',500),
                          ('render_hook',0x4617a0),('map_active_word',0),('world_width',0),('world_height',101)):
            self.assertFalse(tool.selected_unit([dict(state,**{key:value})]))
        self.assertFalse(tool.selected_unit([]))

    def test_early_exit_or_short_observation_is_not_full_runtime_success(self):
        prefix=('REAL_LOADED pid=123 base=00400000 entry=004731b6 executable_sections_match=1\n'
                'REAL_EXE_ENTRY observed=1\n')
        suffix='\nREAL_CLEANUP absent=1 exit=80004005\n'
        end='REAL_END entered=1 exited=0 exception_stop=0 elapsed_ms=110000'
        self.assertTrue(tool.full_observation(prefix+end+suffix,0)['observation_complete'])
        for value in (end.replace('110000','109999'),end.replace('exited=0','exited=1'),end.replace('exception_stop=0','exception_stop=1')):
            self.assertFalse(tool.full_observation(prefix+value+suffix,0)['observation_complete'])

    def test_override_checks_actual_predecessor_recipe_and_probe_before_output(self):
        from src.patcher import native_present_bounds as correction
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);base=root/'baseline.exe';base.write_bytes(b'synthetic predecessor')
            original=root/'original.exe';original.write_bytes(b'synthetic original')
            image=b'synthetic new candidate';probe='synthetic probe'
            original_metadata=dict(profile='classic',resolution='3840x2160',recipe_revision=correction.REVISION,
                base_candidate_sha256=tool.matrix.digest(base),candidate_sha256=hashlib.sha256(image).hexdigest(),
                probe_sha256=hashlib.sha256(probe.encode()).hexdigest(),stage='synthetic-nativepresent-validation',
                source_hashes={'tools/resolution_playability.py':tool.matrix.digest(Path(tool.__file__))})
            baseline=dict(candidate_sha256=tool.matrix.digest(base),launcher_build={'fixture':True})
            for key,value in (('base_candidate_sha256','a'*64),('candidate_sha256','b'*64),('probe_sha256','c'*64),
                              ('profile','framed'),('resolution','800x600'),('recipe_revision','legacy')):
                metadata=dict(original_metadata,**{key:value})
                with patch.object(correction,'build_candidate',return_value=(image,metadata,probe)),self.assertRaises(ValueError):
                    tool.stage_present_override(original,'classic','3840x2160',root,base,baseline)
                self.assertFalse((root/'native-present').exists())
            with patch.object(correction,'build_candidate',return_value=(image,original_metadata,probe)):
                target,built=tool.stage_present_override(original,'classic','3840x2160',root,base,baseline)
            self.assertEqual(target.read_bytes(),image)
            self.assertEqual(built['recipe_revision'],correction.REVISION)
            self.assertEqual(built['predecessor_launcher_build'],baseline['launcher_build'])
            self.assertEqual(base.read_bytes(),b'synthetic predecessor')

    @staticmethod
    def map_state(**overrides):
        return dict(dict(render_hook=0x40ad40,game_data=0x3800000,map_active_word=0x4100000,
                         map_surface=0x4200000,map_pixels=0x4300000,native_modal_word=0,
                         world_width=50,world_height=50,scroll_x=26,scroll_y=39),**overrides)

    def test_screen_owner_takes_precedence_over_retained_map_buffers(self):
        self.assertTrue(tool.screen_context(self.map_state())['ordinary_map'])
        result=tool.screen_context(self.map_state(render_hook=0x422020))
        self.assertEqual(result['screen'],'castle_overview');self.assertFalse(result['ordinary_map'])
        self.assertFalse(tool.screen_context(self.map_state(render_hook=0x4617a0))['ordinary_map'])

    def test_map_context_rejects_partial_modal_and_malformed_observations(self):
        for key,value in (('render_hook',True),('game_data',0),('map_active_word',False),('map_surface',None),
                          ('map_pixels',0xffffffff+1),('native_modal_word',1),('native_modal_word',False),
                          ('world_width',101),('world_height','50'),('scroll_x',-1),('scroll_y',50),('scroll_y',True)):
            with self.subTest(key=key,value=value):
                self.assertFalse(tool.screen_context(self.map_state(**{key:value}))['ordinary_map'])
        for key in self.map_state():
            state=self.map_state();del state[key]
            self.assertFalse(tool.screen_context(state)['ordinary_map'])

    def test_snapshot_requires_same_index_state_and_paused_primary(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);path=root/'primary-10.json';state=root/'map-state-10.json'
            path.write_text(json.dumps({'paused':True}))
            (root/'map-state-09.json').write_text(json.dumps(self.map_state()))
            self.assertFalse(tool.primary_context(path)['ordinary_map'])
            state.write_text(json.dumps(self.map_state()))
            result=tool.primary_context(path)
            self.assertTrue(result['ordinary_map']);self.assertEqual(result['state_sample'],state.name)
            self.assertEqual(result['state_sha256'],hashlib.sha256(state.read_bytes()).hexdigest())
            self.assertEqual(result['primary_metadata_sha256'],hashlib.sha256(path.read_bytes()).hexdigest())
            for value in ({},{'paused':1},{'paused':False},[]):
                path.write_text(json.dumps(value));self.assertFalse(tool.primary_context(path)['ordinary_map'])
            path.write_text(json.dumps({'paused':True}))
            for value in ('incomplete','[]','null'):
                state.write_text(value);self.assertFalse(tool.primary_context(path)['ordinary_map'])

    def test_final_castle_samples_are_retained_but_never_audited_as_map(self):
        import frame_surface_audit as frame
        import action_bar_surface_audit as bar
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            for index in range(4):
                (root/f'primary-{index:02}.json').write_text(json.dumps({'paused':True}))
                state=self.map_state(render_hook=0x40ad40 if index==0 else 0x422020)
                (root/f'map-state-{index:02}.json').write_text(json.dumps(state))
            with patch.object(frame,'audit_surface',side_effect=AssertionError('not a map')), \
                 patch.object(bar,'compare_cells',side_effect=AssertionError('not a map')), \
                 patch.object(tool,'indexed_image',side_effect=AssertionError('not a map')):
                rows=tool.validate_map_pixels(root,root/'absent-artwork','modalwidgets','1024x768')
            self.assertEqual([r['sample'] for r in rows],['primary-01.json','primary-02.json','primary-03.json'])
            self.assertTrue(all(r['screen_context']['screen']=='castle_overview' for r in rows))
            self.assertTrue(all(not r['map_audit_applicable'] and r['frame'] is None and r['action_cells']==[] for r in rows))
            self.assertFalse(tool.map_controls_passed(rows))

    def test_actual_map_still_runs_both_artwork_audits_and_keeps_pixel_failures(self):
        import frame_surface_audit as frame
        import action_bar_surface_audit as bar
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            (root/'gfx3.res').write_bytes(b'fixture');(root/'minimum.res').write_bytes(b'fixture')
            for index in range(3):
                (root/f'primary-{index:02}.json').write_text(json.dumps({'paused':True}))
                (root/f'map-state-{index:02}.json').write_text(json.dumps(self.map_state()))
            cells=[dict(cell=i,exact_source_match=True) for i in range(6)]
            with patch.object(frame,'load_native_frame',return_value=object()), \
                 patch.object(bar,'load_sprites',return_value=({},'fixture')), \
                 patch.object(tool,'indexed_image',return_value=(Image.new('RGB',(1024,768)),b'fixture')), \
                 patch.object(frame,'audit_surface',return_value={'structural_border_exact':True}) as edges, \
                 patch.object(bar,'compare_cells',return_value=cells) as actions:
                rows=tool.validate_map_pixels(root,root,'framed','1024x768')
                self.assertEqual(edges.call_count,3);self.assertEqual(actions.call_count,3)
                self.assertTrue(tool.map_controls_passed(rows))
                edges.return_value={'structural_border_exact':False}
                self.assertFalse(tool.map_controls_passed(tool.validate_map_pixels(root,root,'framed','1024x768')))
                edges.return_value={'structural_border_exact':True};cells[-1]['exact_source_match']=False
                self.assertFalse(tool.map_controls_passed(tool.validate_map_pixels(root,root,'framed','1024x768')))
                cells[-1]['exact_source_match']=True
                edges.reset_mock()
                classic=tool.validate_map_pixels(root,root,'classic','1024x768')
                self.assertTrue(tool.map_controls_passed(classic));edges.assert_not_called()
                self.assertTrue(all(r['frame'] is None and r['frame_source_sha256'] is None for r in classic))

    def test_map_pass_requires_three_applicable_samples_and_all_six_cells(self):
        row=dict(map_audit_applicable=True,screen_context={'ordinary_map':True},frame_required=True,
                 frame={'structural_border_exact':True},action_cells=[{}]*6,action_cells_exact=True)
        self.assertTrue(tool.map_controls_passed([row]*3))
        for changed in (dict(row,map_audit_applicable=False),dict(row,screen_context={'ordinary_map':False}),
                        dict(row,action_cells=[{}]*5),dict(row,action_cells_exact=False),
                        dict(row,frame={'structural_border_exact':False}),dict(row,frame_required=None)):
            self.assertFalse(tool.map_controls_passed([row,row,changed]))
        self.assertFalse(tool.map_controls_passed([row]*2))
        self.assertFalse(tool.map_controls_passed([row]*4))

    def test_success_requires_input_pixels_cleanup_and_original_identity(self):
        flags=['--execute','--approval-text','test','--runtime','a','--manifest','b','--proxy','c','--out','d']
        success=dict(errors=[],menu_and_campaign_input_passed=True,map_controls_pixels_passed=True,
                     outcome={'observation_complete':True},reference_unchanged=True,retained_process_exited=True,native_input_passed=True,unit_selected_observed=True)
        for field in (None,'menu_and_campaign_input_passed','map_controls_pixels_passed','outcome','reference_unchanged','retained_process_exited','native_input_passed','unit_selected_observed'):
            row=dict(success)
            if field:row[field]={'observation_complete':False} if field=='outcome' else False
            with patch.object(sys,'argv',['test',*flags]),patch.object(tool,'run',return_value=row),redirect_stdout(io.StringIO()):
                self.assertEqual(tool.main(),0 if field is None else 1)


if __name__=='__main__':unittest.main(verbosity=2)
