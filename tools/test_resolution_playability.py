"""Pure source, snapshot, menu identity and fitted-display regressions."""
from contextlib import ExitStack,redirect_stderr,redirect_stdout
from copy import deepcopy
import ast
import hashlib
import inspect
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
        flags=['--mode','foreground-diagnostic','--execute','--approval-text','test','--runtime','a','--manifest','b','--proxy','c','--out','d']
        success=dict(errors=[],menu_and_campaign_input_passed=True,map_controls_pixels_passed=True,
                     outcome={'observation_complete':True},reference_unchanged=True,retained_process_exited=True,native_input_passed=True,unit_selected_observed=True)
        for field in (None,'menu_and_campaign_input_passed','map_controls_pixels_passed','outcome','reference_unchanged','retained_process_exited','native_input_passed','unit_selected_observed'):
            row=dict(success)
            if field:row[field]={'observation_complete':False} if field=='outcome' else False
            with patch.object(sys,'argv',['test',*flags]),patch.object(tool,'run',return_value=row),redirect_stdout(io.StringIO()):
                self.assertEqual(tool.main(),0 if field is None else 1)


class HiddenAcceptanceTests(unittest.TestCase):
    @staticmethod
    def passing_report():
        return dict(errors=[],ordinary_controlled_input_passed=True,
            actions=[dict(name='select',passed=True,native_dispatch={'passed':True},
                          state_transition={'selection_state_transition':True}),
                     dict(name='move',passed=True,native_dispatch={'passed':True},
                          state_transition={'movement_state_transition':True})],
            outcome={'observation_complete':True},reference_unchanged=True,candidate_unchanged=True,
            working_original_unchanged=True,retained_process_exited=True,sources_unchanged=True,
            startup_retired_before_actions=True,map_controls_pixels_passed=True,
            host_cleanup=dict(host_exited=True,job_empty=True,handles_closed=True),
            native_input_passed=False,manual_input_proof=False,promotion_ready=False)

    def test_hidden_success_requires_every_identity_cleanup_and_interval_gate(self):
        good=self.passing_report()
        self.assertTrue(tool.hidden_success(good))
        for name in ('ordinary_controlled_input_passed','reference_unchanged','candidate_unchanged',
                     'working_original_unchanged','retained_process_exited','sources_unchanged',
                     'startup_retired_before_actions','map_controls_pixels_passed'):
            for value in (False,None,1):
                bad=deepcopy(good);bad[name]=value
                with self.subTest(field=name,value=value):self.assertFalse(tool.hidden_success(bad))
        for name in ('host_exited','job_empty','handles_closed'):
            bad=deepcopy(good);bad['host_cleanup'][name]=False
            with self.subTest(cleanup=name):self.assertFalse(tool.hidden_success(bad))
        for mutation in (lambda r:r.update(errors=['failed']),
                         lambda r:r.update(outcome={'observation_complete':False}),
                         lambda r:r.pop('host_cleanup')):
            bad=deepcopy(good);mutation(bad);self.assertFalse(tool.hidden_success(bad))

    def test_hidden_acceptance_rejects_duplicate_unproven_or_incomplete_actions(self):
        good=self.passing_report()
        for actions in ([],good['actions'][:1],list(reversed(good['actions'])),
                        [good['actions'][0]]*2,[dict(passed=True)]*2):
            self.assertFalse(tool.hidden_success(dict(good,actions=actions)))
        for index in (0,1):
            for field in ('passed','native_dispatch','state_transition'):
                for missing in (True,False):
                    bad=deepcopy(good)
                    if missing:bad['actions'][index].pop(field)
                    else:bad['actions'][index][field]=False if field=='passed' else {}
                    with self.subTest(action=index,field=field,missing=missing):
                        self.assertFalse(tool.hidden_success(bad))

    def test_default_hidden_cli_uses_controlled_acceptance_without_os_input_claim(self):
        flags=['--execute','--approval-text','test','--runtime','a','--manifest','b','--proxy','c','--out','d']
        for passed in (True,False):
            report=self.passing_report()
            if not passed:report['actions'][1]['state_transition']={}
            with patch.object(sys,'argv',['test',*flags]),patch.object(tool,'run',return_value=report) as run,redirect_stdout(io.StringIO()):
                self.assertEqual(tool.main(),0 if passed else 1)
            self.assertEqual(run.call_args.args[0].mode,'hidden-controlled')
        self.assertFalse(self.passing_report()['manual_input_proof'])

    def test_explicit_mode_routes_only_to_its_matching_driver(self):
        from types import SimpleNamespace
        for mode in ('hidden-controlled','foreground-diagnostic'):
            with patch.object(tool,'run_hidden',return_value='hidden') as hidden,patch.object(tool,'run_foreground',return_value='foreground') as foreground:
                self.assertEqual(tool.run(SimpleNamespace(mode=mode)),'hidden' if mode=='hidden-controlled' else 'foreground')
                self.assertEqual(hidden.call_count,int(mode=='hidden-controlled'))
                self.assertEqual(foreground.call_count,int(mode=='foreground-diagnostic'))

    def test_hidden_map_actions_have_no_fixed_click_or_os_delivery_path(self):
        source=inspect.getsource(tool.measured_actions)
        tree=ast.parse(source)
        clicks=[node for node in ast.walk(tree) if isinstance(node,ast.Call) and
                isinstance(node.func,ast.Attribute) and node.func.attr=='click']
        self.assertEqual(len(clicks),1)
        self.assertIsInstance(clicks[0].args[1],ast.Subscript)
        self.assertEqual(ast.unparse(clicks[0].args[1]),"validation['point']")
        self.assertIn('planner.revalidate_before_click(plan,before,action)',source)
        self.assertIn('planner.verify_selection',source);self.assertIn('planner.verify_movement',source)
        hidden_source=source+inspect.getsource(tool.run_hidden)
        for forbidden in ('run_input(', 'SendInput(', 'SetCursorPos(', 'runner_menu_input', '--aim-points'):
            self.assertNotIn(forbidden,hidden_source)
        composed=tool.native_phase_source(1024,768)
        self.assertIn('if (!phases.enabled && GetTickCount64()>=next)',composed)
        self.assertIn('snapshot(s,out,capture_index,proxy)',composed)
        self.assertLess(composed.index('if (startup.on_event('),composed.index('if (phases.on_event('))


class PreparedCandidateTests(unittest.TestCase):
    def fixture(self,profile):
        from types import SimpleNamespace
        temporary=tempfile.TemporaryDirectory(prefix='clash-prepared-receipt-')
        self.addCleanup(temporary.cleanup)
        root=Path(temporary.name)
        exe=root/'synthetic.exe';exe.write_bytes(b'Non-executable prepared-candidate fixture')
        probe=exe.with_suffix('.cdb');probe.write_text('Synthetic probe, never executed\n',encoding='ascii')
        metadata_path=exe.with_suffix('.candidate.json')
        case=tool.matrix.select_case(profile,'1024x768')
        sources={'tools/test_resolution_playability.py':tool.matrix.digest(Path(__file__))}
        original_field,schema=('base_sha256',1) if profile=='completehd' else (
            'original_sha256','clash95_framed_modal_widgets_candidate_v1')
        metadata=dict(schema=schema,candidate_sha256=tool.matrix.digest(exe),source_hashes=sources,
                      **{original_field:tool.matrix.runtime.ORIGINAL_SHA256},
                      **{key:case[key] for key in ('stage','resolution','recipe_revision')})
        build=dict(base_sha256=tool.matrix.runtime.ORIGINAL_SHA256,output_sha256=tool.matrix.digest(exe),
                   display_plan=dict(renderer=profile,**{key:case[key] for key in ('stage','resolution','recipe_revision')}),
                   candidate_manifest=dict(path=str(metadata_path)),source_sha256=deepcopy(sources),
                   artifact_sha256={exe.name:tool.matrix.digest(exe),probe.name:tool.matrix.digest(probe)})
        receipt=dict(path=str(exe),built=dict(case,candidate_sha256=tool.matrix.digest(exe),launcher_build=build))
        value=SimpleNamespace(exe=exe,probe=probe,metadata_path=metadata_path,metadata=metadata,
                              case=case,build=build,receipt=receipt,path=root/'receipt.json')
        self.write(value,metadata=True)
        return value

    @staticmethod
    def write(value,*,metadata=False):
        if metadata:
            value.metadata_path.write_text(json.dumps(value.metadata),encoding='utf-8')
            digest=tool.matrix.digest(value.metadata_path)
            value.build['candidate_manifest']['sha256']=digest
            value.build['artifact_sha256'][value.metadata_path.name]=digest
        value.path.write_text(json.dumps(value.receipt),encoding='utf-8')

    def test_both_profile_schemas_accept_only_intact_source_bound_artifacts(self):
        for profile in ('completehd','modalwidgets'):
            with self.subTest(profile=profile):
                value=self.fixture(profile)
                before={p.name:p.read_bytes() for p in value.path.parent.iterdir()}
                exe,built=tool.prepared_candidate(value.path,value.case)
                self.assertEqual(exe,value.exe.resolve());self.assertEqual(built,value.receipt['built'])
                self.assertEqual(before,{p.name:p.read_bytes() for p in value.path.parent.iterdir()})

    def test_current_launcher_case_and_display_plan_cannot_be_substituted(self):
        for profile in ('completehd','modalwidgets'):
            for key in ('profile','resolution','stage','recipe_revision','manifest_sha256'):
                value=self.fixture(profile);value.receipt['built'][key]='stale'
                self.write(value)
                with self.subTest(profile=profile,case=key),self.assertRaisesRegex(ValueError,'current launcher case'):
                    tool.prepared_candidate(value.path,value.case)
            for key in ('renderer','resolution','stage','recipe_revision'):
                value=self.fixture(profile);value.build['display_plan'][key]='other'
                self.write(value)
                with self.subTest(profile=profile,display=key),self.assertRaisesRegex(ValueError,'display plan'):
                    tool.prepared_candidate(value.path,value.case)

    def test_original_checksum_and_schema_are_specific_to_the_profile(self):
        for profile in ('completehd','modalwidgets'):
            expected,alternate=('base_sha256','original_sha256') if profile=='completehd' else (
                'original_sha256','base_sha256')
            for defect in ('wrong-schema','missing-field','wrong-original','wrong-build-original'):
                value=self.fixture(profile)
                if defect=='wrong-schema':
                    value.metadata['schema']='clash95_framed_modal_widgets_candidate_v1' if profile=='completehd' else 1
                elif defect=='missing-field':value.metadata[alternate]=value.metadata.pop(expected)
                elif defect=='wrong-original':value.metadata[expected]='a'*64
                else:value.build['base_sha256']='b'*64
                self.write(value,metadata=True)
                with self.subTest(profile=profile,defect=defect),self.assertRaises(ValueError):
                    tool.prepared_candidate(value.path,value.case)

    def test_changed_executable_metadata_and_probe_each_fail_closed(self):
        for field in ('exe','metadata_path','probe'):
            value=self.fixture('modalwidgets');target=getattr(value,field)
            target.write_bytes(target.read_bytes()+b'changed')
            with self.subTest(changed=field),self.assertRaises(ValueError):
                tool.prepared_candidate(value.path,value.case)

    def test_stale_source_and_rebound_metadata_identity_still_fail(self):
        for defect in ('source','candidate','stage','resolution','recipe_revision'):
            value=self.fixture('completehd')
            if defect=='source':
                value.metadata['source_hashes']['tools/test_resolution_playability.py']='c'*64
                value.build['source_sha256']=deepcopy(value.metadata['source_hashes'])
            elif defect=='candidate':value.metadata['candidate_sha256']='d'*64
            else:value.metadata[defect]='stale'
            self.write(value,metadata=True)
            with self.subTest(defect=defect),self.assertRaisesRegex(ValueError,'HD source changed|metadata or source inventory'):
                tool.prepared_candidate(value.path,value.case)

    def test_receipt_manifest_path_and_exact_artifact_inventory_are_bound(self):
        for defect in ('extra-receipt','manifest-path','extra-artifact','missing-artifact'):
            value=self.fixture('modalwidgets')
            if defect=='extra-receipt':value.receipt['unbound']='field'
            elif defect=='manifest-path':value.build['candidate_manifest']['path']=str(value.path.parent/'other.json')
            elif defect=='extra-artifact':value.build['artifact_sha256']['other.exe']='a'*64
            else:value.build['artifact_sha256'].pop(value.probe.name)
            self.write(value)
            with self.subTest(defect=defect),self.assertRaises(ValueError):
                tool.prepared_candidate(value.path,value.case)


class MeasuredActionsTests(unittest.TestCase):
    def setUp(self):
        self.new_case()

    def new_case(self):
        import ordinary_map_input_plan as planner
        from test_ordinary_map_input_plan import fixture,selected,moved
        from test_ordinary_map_phase_client import FakeHost
        temporary=tempfile.TemporaryDirectory(prefix='clash-measured-driver-')
        self.addCleanup(temporary.cleanup)
        self.out=Path(temporary.name)
        self.candidate,self.initial=fixture()
        self.states=[deepcopy(self.initial),deepcopy(self.initial),selected(self.initial,3),
                     selected(self.initial,4),moved(self.initial,5)]
        self.host=FakeHost(self.out/'control',identity=self.initial['identity'])
        self.peer=self.host.client()
        self.report=dict(errors=[],ordinary_controlled_input_passed=False)
        self.events=[];self.observations=[];self.observation_error_at=None;self.release_error=None
        self.planner=planner

    def run_actions(self):
        import ordinary_map_observation as decoder
        original_revalidate=self.planner.revalidate_before_click
        original_click=self.peer.click
        original_release=self.peer.release
        def unused_read(address,size):
            raise AssertionError('This driver fixture supplies decoded synthetic states, not native memory')
        def observe(read_exact,**kwargs):
            self.assertIs(read_exact,unused_read)
            self.assertEqual(kwargs['identity'],self.peer.identity)
            self.assertEqual(kwargs['candidate'],self.candidate)
            kwargs['check_lease'](kwargs['lease'])
            sequence=kwargs['sequence']
            lease=deepcopy(kwargs['lease'])
            self.events.append(('observe',sequence,lease['lease_id']))
            self.observations.append(dict(sequence=sequence,lease=lease,indices=kwargs['stack_indices']))
            if sequence==self.observation_error_at:raise decoder.ObservationError('fixture read failed')
            snapshot=deepcopy(self.states[sequence-1]);snapshot['sequence']=sequence
            return dict(snapshot=snapshot,receipt=dict(observation_sha256=self.planner.digest(snapshot),
                                                       lease=lease,read_calls=17))
        def revalidate(plan,before,action):
            result=original_revalidate(plan,before,action)
            self.events.append(('revalidate',action,before['sequence'],self.peer._active['lease_id']))
            return result
        def click(lease,point,binding):
            self.peer.check_lease(lease)
            self.assertEqual(self.events[-1][0],'revalidate')
            self.assertEqual(self.events[-1][-1],lease['lease_id'])
            self.events.append(('click',tuple(point),lease['lease_id']))
            return original_click(lease,point,binding)
        def release(lease):
            self.events.append(('release',lease['lease_id']))
            if self.release_error:raise self.release_error
            return original_release(lease)
        with ExitStack() as scope:
            scope.enter_context(patch.object(decoder,'observe',side_effect=observe))
            scope.enter_context(patch.object(self.planner,'revalidate_before_click',side_effect=revalidate))
            self.clicked=scope.enter_context(patch.object(self.peer,'click',side_effect=click))
            self.released=scope.enter_context(patch.object(self.peer,'release',side_effect=release))
            scope.enter_context(redirect_stdout(io.StringIO()))
            tool.measured_actions(self.peer,unused_read,self.candidate,self.out,self.report)

    def test_real_planner_transitions_commit_only_after_same_held_lease_revalidation(self):
        self.run_actions()
        self.assertTrue(self.report['ordinary_controlled_input_passed'])
        self.assertEqual([row['name'] for row in self.report['actions']],['select','move'])
        self.assertTrue(self.report['actions'][0]['state_transition']['selection_state_transition'])
        self.assertTrue(self.report['actions'][1]['state_transition']['movement_state_transition'])
        self.assertTrue(all(row['native_dispatch']['passed'] for row in self.report['actions']))
        leases=[row['lease']['lease_id'] for row in self.observations]
        self.assertEqual(leases[0],leases[1]);self.assertEqual(leases[2],leases[3])
        self.assertEqual(len(set(leases)),3)
        self.assertEqual([row['sequence'] for row in self.observations],[1,2,3,4,5])
        self.assertIsNone(self.observations[0]['indices'])
        self.assertTrue(all(row['indices']==(13,) for row in self.observations[1:]))
        self.assertEqual([call.args[1] for call in self.clicked.call_args_list],[[256,240],[320,240]])
        self.assertEqual([row[3] for row in self.host.requests],['acquire','click','click','release'])
        self.released.assert_called_once()
        self.assertEqual(self.released.call_args.args[0]['lease_id'],leases[-1])
        for row in self.report['observations']:
            self.assertEqual(tool.matrix.digest(Path(row['path'])),row['sha256'])

    def test_stale_preselection_read_prevents_any_click_and_releases_initial_lease(self):
        self.states[1]['world']['scroll_x']+=1
        with self.assertRaises(self.planner.PlanError):self.run_actions()
        self.clicked.assert_not_called();self.released.assert_called_once()
        self.assertFalse(self.report['ordinary_controlled_input_passed'])
        self.assertEqual(self.report['actions'],[])
        self.assertEqual(self.host.data['status'],'released')

    def test_changed_premove_ap_stops_before_second_click(self):
        self.states[3]['stacks'][0]['slots'][0]['ap']-=1
        with self.assertRaises(self.planner.PlanError):self.run_actions()
        self.assertEqual(self.clicked.call_count,1)
        self.assertEqual([row['name'] for row in self.report['actions']],['select'])
        self.assertTrue(self.report['actions'][0]['passed'])
        self.assertFalse(self.report['ordinary_controlled_input_passed'])
        self.released.assert_called_once()

    def test_native_call_receipt_cannot_replace_an_actual_selection_change(self):
        self.states[2]=deepcopy(self.initial)
        with self.assertRaises(self.planner.PlanError):self.run_actions()
        self.assertEqual(self.clicked.call_count,1)
        row=self.report['actions'][0]
        self.assertTrue(row['native_dispatch']['passed'])
        self.assertFalse(row['passed']);self.assertNotIn('state_transition',row)
        self.released.assert_called_once()

    def test_selecting_a_different_army_is_not_the_planned_selection(self):
        state=self.states[2]
        state['context'].update(selected_stack=14,panel_stack=14,
                                active_stack=state['context']['game_data']+147174+725*14)
        with self.assertRaises(self.planner.PlanError):self.run_actions()
        self.assertEqual(self.clicked.call_count,1)
        self.assertFalse(self.report['actions'][0]['passed'])
        self.released.assert_called_once()

    def test_ordinary_dispatch_cannot_reuse_the_previous_index_contract_of_408030(self):
        # The state-only planner also supports native 408030, which preserves
        # previous_stack. This driver observes 4084A0 and must require its store
        # of the old selected index (-1 here), despite an otherwise valid state.
        for state in self.states:state['context']['previous_stack']=7
        self.states[1]['sequence']=2
        plan=self.planner.plan_input(self.states[0],self.candidate)
        self.assertTrue(self.planner.verify_selection(plan,self.states[1],self.states[2])['selection_state_transition'])
        with self.assertRaises(self.planner.PlanError):self.run_actions()
        self.assertEqual(self.clicked.call_count,1)
        row=self.report['actions'][0]
        self.assertTrue(row['native_dispatch']['passed'])
        self.assertFalse(row['passed']);self.assertNotIn('state_transition',row)
        self.assertFalse(self.report['ordinary_controlled_input_passed'])
        self.released.assert_called_once()

    def test_movement_requires_both_occupancies_every_ap_charge_coordinates_and_queue(self):
        mutations=(lambda s:s['tiles'][0].update(occupant=13),
                   lambda s:s['tiles'][1].update(occupant=65535),
                   lambda s:s['stacks'][0]['slots'][1].update(ap=22),
                   lambda s:s['stacks'][0].update(x=10),
                   lambda s:s['stacks'][0].update(queue_count=1))
        for index,mutation in enumerate(mutations):
            if index:self.new_case()
            mutation(self.states[4])
            with self.subTest(defect=index),self.assertRaises(self.planner.PlanError):self.run_actions()
            self.assertEqual(self.clicked.call_count,2)
            self.assertTrue(self.report['actions'][0]['passed'])
            self.assertFalse(self.report['actions'][1]['passed'])
            self.assertFalse(self.report['ordinary_controlled_input_passed'])
            self.released.assert_called_once()

    def test_false_native_predicate_rejects_even_if_decoded_selection_looks_correct(self):
        def reject(data):
            if data['status']=='held' and data['phase']=='predispatch-after':data['predicate_value']=0
        self.host.publish_hook=reject
        from ordinary_map_pause_client import LeaseError
        with self.assertRaisesRegex(LeaseError,'not accepted'):self.run_actions()
        self.assertEqual(self.clicked.call_count,1)
        self.assertFalse(self.report['actions'][0]['passed'])
        self.assertNotIn('state_transition',self.report['actions'][0])
        self.released.assert_called_once()

    def test_failed_after_read_releases_the_successor_not_the_consumed_lease(self):
        import ordinary_map_observation as decoder
        self.observation_error_at=3
        with self.assertRaisesRegex(decoder.ObservationError,'fixture read failed'):self.run_actions()
        self.released.assert_called_once()
        released=self.released.call_args.args[0]['lease_id']
        self.assertNotEqual(released,self.observations[0]['lease']['lease_id'])
        self.assertEqual(released,self.observations[-1]['lease']['lease_id'])
        self.assertEqual(self.host.data['status'],'released')

    def test_failed_consumed_click_never_releases_the_old_lease(self):
        from ordinary_map_pause_client import LeaseError
        def fail():raise LeaseError('fixture transport failed after consumption')
        self.host.executing_hook=fail
        with self.assertRaisesRegex(LeaseError,'after consumption'):self.run_actions()
        self.assertTrue(self.peer._poisoned);self.assertIsNone(self.peer._active)
        self.released.assert_not_called()
        self.assertEqual([row[3] for row in self.host.requests],['acquire','click'])
        self.assertFalse(self.report['ordinary_controlled_input_passed'])

    def test_release_failure_is_retained_and_prevents_hidden_acceptance(self):
        from ordinary_map_pause_client import LeaseError
        self.release_error=LeaseError('fixture release failed')
        self.run_actions()
        self.assertTrue(self.report['ordinary_controlled_input_passed'])
        self.assertEqual(self.report['errors'],['Phase release: fixture release failed'])
        self.assertFalse(tool.hidden_success(self.report))
        self.assertTrue(self.report['phase_receipts'])


if __name__=='__main__':unittest.main(verbosity=2)
