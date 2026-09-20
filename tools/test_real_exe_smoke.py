import importlib.util
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('real_exe_smoke', Path(__file__).with_name('real_exe_smoke.py'))
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)


class RealExeSmokeTests(unittest.TestCase):
    def test_default_dry_run_never_reads_assets_or_creates_output(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            result = subprocess.run([sys.executable, tool.__file__, '--runtime', str(root/'missing'),
                '--manifest', str(root/'missing.json'), '--out', str(root/'output')], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse(json.loads(result.stdout)['executed'])
            self.assertEqual(list(root.iterdir()), [])

    def test_invalid_duration_is_rejected_before_execution(self):
        with tempfile.TemporaryDirectory() as folder:
            for value in ('0', '91', '-1', 'nan'):
                result = subprocess.run([sys.executable, tool.__file__, '--runtime', folder, '--manifest', folder,
                    '--out', str(Path(folder)/'output'), '--seconds', value], capture_output=True, text=True)
                self.assertEqual(result.returncode, 2, result.stdout)
            self.assertEqual(list(Path(folder).iterdir()), [])

    def test_reference_path_escape_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            manifest = {'runtime': {'files': [{'path': '../outside.exe', 'size': 1, 'sha256': 'a'*64}]}}
            with self.assertRaisesRegex(ValueError, 'escapes'):
                tool.verify(root, manifest)

    def test_reference_size_and_hash_mismatch_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root/'clash95.exe').write_bytes(b'not the game')
            for size in (1, 12):
                manifest = {'runtime': {'files': [{'path': 'clash95.exe', 'size': size, 'sha256': 'a'*64}]}}
                with self.assertRaisesRegex(ValueError, 'mismatch'):
                    tool.verify(root, manifest)

    def test_indexed_frame_conversion_remains_diagnostic(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root/'primary-00.raw').write_bytes(bytes(range(256))*1200)
            (root/'primary-00.json').write_text(json.dumps({'width':640, 'height':480, 'pitch':640}))
            result = tool.render(root)
            self.assertEqual(len(result),1)
            self.assertEqual(result[0]['palette_mode'],'grayscale_index_preview')
            self.assertFalse(result[0]['visual_acceptance'])
            self.assertEqual(result[0]['nonzero_indices'], 255*1200)
            self.assertTrue((root/'primary-00.png').is_file())

    def test_observation_completion_requires_end_entry_identity_and_cleanup(self):
        log = ('REAL_LOADED pid=123 base=00400000 entry=004731b6 executable_sections_match=1\n'
               'REAL_EXE_ENTRY observed=1\n'
               'REAL_END entered=1 exited=0 exception_stop=0 elapsed_ms=40000\n'
               'REAL_CLEANUP absent=1 exit=80004005\n')
        self.assertTrue(tool.outcome(log, 0)['observation_complete'])
        cases = [(log, 2), (log.replace('exception_stop=0', 'exception_stop=1'), 4)]
        for line in log.splitlines():
            cases.extend(((log.replace(line+'\n', ''), 0), (log+line+'\n', 0)))
        cases.extend(((log+'REAL_HARNESS_ERROR pause event hr=00000001 winerror=0\n', 0),
                      (log+'REAL_WAIT_ERROR hr=80004005\n', 0)))
        for changed, code in cases:
            with self.subTest(log=changed, code=code):
                self.assertFalse(tool.outcome(changed, code)['observation_complete'])

    def test_first_attempt_pause_failure_is_not_a_completed_observation(self):
        log = ('REAL_LOADED pid=5804 base=00400000 entry=004731b6 executable_sections_match=1\n'
               'REAL_EXE_ENTRY observed=1\nREAL_CLEANUP absent=1 exit=80004005\n'
               'REAL_HARNESS_ERROR pause event hr=00000001 winerror=0\n')
        for code in (0,2):
            result = tool.outcome(log, code)
            self.assertTrue(result['entry_observed'])
            self.assertTrue(result['owned_process_absent'])
            self.assertFalse(result['observation_complete'])
            self.assertEqual(len(result['harness_errors']),1)

    def test_hd_recipe_selection_is_explicit_and_dry_run_never_builds(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            base = [sys.executable, tool.__file__, '--runtime', str(root/'missing'),
                    '--manifest', str(root/'missing.json'), '--out', str(root/'output')]
            for recipe in tool.HD_RECIPES:
                for resolution in tool.HD_RESOLUTIONS:
                    command = base + ['--complete-hd', '--hd-only', '--hd-recipe', recipe, '--hd-resolution', resolution]
                    result = subprocess.run(command, capture_output=True, text=True)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    data = json.loads(result.stdout)
                    self.assertFalse(data['executed'])
                    self.assertEqual((data['hd_recipe'], data['hd_resolution'], data['hd_only']),
                                     (recipe, resolution, True))
            for flags in (['--hd-only'], ['--hd-recipe', 'modalwidgets'], ['--hd-resolution', '1920x1080'],
                          ['--complete-hd', '--hd-recipe', 'unknown'], ['--complete-hd', '--hd-resolution', '1600x900']):
                result = subprocess.run(base + flags, capture_output=True, text=True)
                self.assertEqual(result.returncode, 2, result.stdout)
            self.assertEqual(list(root.iterdir()), [])

    def test_hd_only_execution_still_requires_the_diagnostic_proxy(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            result = subprocess.run([sys.executable, tool.__file__, '--runtime', str(root/'missing'),
                '--manifest', str(root/'missing.json'), '--out', str(root/'output'), '--execute',
                '--complete-hd', '--hd-only', '--hd-recipe', 'modalwidgets'], capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertIn('requires the diagnostic proxy', result.stderr)
            self.assertEqual(list(root.iterdir()), [])

    def test_each_hd_bundle_keeps_the_selected_stage_probe_and_file_identities(self):
        sys.path.insert(0, str(Path(tool.__file__).resolve().parents[1]))
        from src.patcher.patch_clash95_hd import DEFAULT_STAGE
        source = 'tools/real_exe_smoke.py'
        for recipe, (module_name, suffix, revision) in tool.HD_RECIPES.items():
            for resolution in tool.HD_RESOLUTIONS:
                with self.subTest(recipe=recipe, resolution=resolution), tempfile.TemporaryDirectory() as folder:
                    root = Path(folder)
                    stage = DEFAULT_STAGE + suffix
                    def write(original, target, selected):
                        self.assertEqual(original, root/'original.exe')
                        self.assertEqual(selected, resolution)
                        target.parent.mkdir(parents=True)
                        data, probe = b'MZ synthetic transport fixture', b'.echo synthetic probe\n'
                        target.write_bytes(data)
                        metadata = dict(stage=stage, recipe_revision=revision, resolution=selected,
                            candidate_sha256=hashlib.sha256(data).hexdigest(), probe_sha256=hashlib.sha256(probe).hexdigest(),
                            source_hashes={source: tool.sha(Path(tool.__file__))})
                        target.with_suffix('.cdb').write_bytes(probe)
                        target.with_suffix('.candidate.json').write_text(json.dumps(metadata, indent=2)+'\n', encoding='utf-8', newline='\n')
                        return metadata
                    builder = SimpleNamespace(STAGE=stage, REVISION=revision, write_candidate=write)
                    with patch('importlib.import_module', return_value=builder) as load:
                        target, metadata = tool.prepare_hd_bundle(root/'original.exe', root, recipe, resolution)
                    load.assert_called_once_with(module_name)
                    self.assertEqual(metadata['stage'], stage)
                    self.assertEqual(metadata['recipe_revision'], revision)
                    self.assertEqual(target.name, 'clash95_hd_1024.exe' if (recipe,resolution)==('completehd','1024x768')
                                     else f'clash95_hd_{recipe}_{resolution}.exe')
                    self.assertFalse((root/'original.exe').exists())

    def test_mixed_stage_and_bundle_tampering_are_rejected(self):
        from src.patcher.patch_clash95_hd import DEFAULT_STAGE
        for defect in ('builder_stage', 'builder_revision', 'stage', 'revision', 'resolution', 'image', 'probe', 'sidecar', 'source'):
            with self.subTest(defect=defect), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                stage = DEFAULT_STAGE + tool.HD_RECIPES['modalwidgets'][1]
                revision = tool.HD_RECIPES['modalwidgets'][2]
                def write(original, target, resolution):
                    target.parent.mkdir(parents=True)
                    target.write_bytes(b'synthetic candidate'); target.with_suffix('.cdb').write_bytes(b'synthetic probe')
                    metadata = dict(stage=stage, recipe_revision=revision, resolution=resolution,
                                    candidate_sha256=tool.sha(target), probe_sha256=tool.sha(target.with_suffix('.cdb')),
                                    source_hashes={'tools/real_exe_smoke.py': tool.sha(Path(tool.__file__))})
                    if defect=='stage': metadata['stage']=DEFAULT_STAGE+'-completehd-validation'
                    if defect=='revision': metadata['recipe_revision']='complete_hd_v1'
                    if defect=='resolution': metadata['resolution']='800x600'
                    if defect=='source': metadata['source_hashes']['tools/real_exe_smoke.py']='0'*64
                    target.with_suffix('.candidate.json').write_text(json.dumps(metadata,indent=2)+'\n',encoding='utf-8',newline='\n')
                    if defect=='image': target.write_bytes(b'tampered')
                    if defect=='probe': target.with_suffix('.cdb').write_bytes(b'tampered')
                    if defect=='sidecar': target.with_suffix('.candidate.json').write_bytes(b'{}')
                    return metadata
                builder = SimpleNamespace(STAGE='wrong' if defect=='builder_stage' else stage,
                                          REVISION='wrong' if defect=='builder_revision' else revision, write_candidate=write)
                with patch('importlib.import_module', return_value=builder), self.assertRaises(ValueError):
                    tool.prepare_hd_bundle(root/'original.exe', root, 'modalwidgets', '1024x768')

    def test_source_drift_and_escaping_names_fail_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); source = root/'source.py'; source.write_bytes(b'original')
            metadata = {'source_hashes': {'source.py': tool.sha(source)}}
            tool.verify_hd_sources(metadata, root)
            source.write_bytes(b'drift')
            with self.assertRaisesRegex(ValueError, 'source changed'): tool.verify_hd_sources(metadata, root)
            for paths in ({}, {'../source.py': 'a'*64}, {'C:/source.py': 'a'*64}, {'a\\b.py': 'a'*64},
                          {'/source.py': 'a'*64}, {'./source.py': 'a'*64}, {'source.py': True}, {'source.py': 'A'*64}):
                with self.subTest(paths=paths), self.assertRaises(ValueError): tool.verify_hd_sources({'source_hashes': paths}, root)
            with patch('importlib.import_module', side_effect=AssertionError('unsupported builder import')):
                for recipe, resolution in (('unknown','1024x768'),('modalwidgets','1600x900')):
                    with self.assertRaises(ValueError): tool.prepare_hd_bundle(root/'original',root,recipe,resolution)

    def test_hd_only_runs_selected_exe_and_rejects_missing_or_wrong_surface(self):
        repo = Path(tool.__file__).resolve().parents[1]
        for dimensions in ([(1920,1080)], [], [(1024,768)], [(1920,1080),(800,600)]):
            with self.subTest(dimensions=dimensions), tempfile.TemporaryDirectory() as folder:
                root=Path(folder).resolve(); runtime=root/'assets'; runtime.mkdir(); output=root/'run'
                original=runtime/'clash95.exe'; original.write_bytes(b'synthetic original')
                (runtime/'ddraw.dll').write_bytes(b'synthetic original wrapper')
                manifest=root/'manifest.json'; manifest.write_text(json.dumps({'runtime': {'empty_directories': []}}))
                proxy=root/'ddraw.dll'; proxy.write_bytes(b'synthetic diagnostic wrapper')
                proxy.with_name('ddraw_surfdump_proxy.build.json').write_text(json.dumps(dict(
                    generated_by='clash-hd-surface-dump-proxy', output_sha256=tool.sha(proxy),
                    source_sha256=tool.sha(repo/'src/ddraw_surfdump_proxy/ddraw_surfdump_proxy.cpp'))))
                engine=root/'engine.exe'; engine.write_bytes(b'synthetic harness')
                metadata=dict(stage='synthetic-widget-stage', recipe_revision='owned_modal_widget_bounds_v1',
                              source_hashes={'tools/real_exe_smoke.py': tool.sha(Path(tool.__file__))})
                def prepare(path, destination, recipe, resolution):
                    self.assertEqual((path, destination, recipe, resolution), (original,output,'modalwidgets','1920x1080'))
                    candidate=destination/'bundle/widget.exe';candidate.parent.mkdir();candidate.write_bytes(b'synthetic HD EXE')
                    metadata['candidate_sha256']=tool.sha(candidate)
                    return candidate, metadata
                log=('REAL_LOADED pid=12 base=00400000 entry=004731b6 executable_sections_match=1\n'
                     'REAL_EXE_ENTRY observed=1\n'
                     'REAL_END entered=1 exited=0 exception_stop=0 elapsed_ms=60000\n'
                     'REAL_CLEANUP absent=1 exit=80004005\n')
                result=SimpleNamespace(returncode=0, stdout=log, stderr='')
                argv=[tool.__file__, '--runtime',str(runtime),'--manifest',str(manifest),'--out',str(output),
                      '--proxy',str(proxy),'--complete-hd','--hd-only','--hd-recipe','modalwidgets',
                      '--hd-resolution','1920x1080','--execute']
                with patch.object(sys,'argv',argv), patch.object(tool,'os',SimpleNamespace(name='nt',environ={})), \
                     patch.object(tool,'ORIGINAL_SHA256',tool.sha(original)), patch.object(tool,'verify',return_value={'fixture':True}), \
                     patch.object(tool,'compile_harness',return_value=engine), patch.object(tool,'prepare_hd_bundle',side_effect=prepare), \
                     patch.object(tool,'render',return_value=[{'width':w,'height':h} for w,h in dimensions]), \
                     patch.object(tool.subprocess,'run',return_value=result) as run, patch('builtins.print'):
                    code=tool.main()
                self.assertEqual(code, 0 if dimensions==[(1920,1080)] else 1,
                                 json.loads((output/'summary.json').read_text()).get('errors'))
                run.assert_called_once()
                command=run.call_args.args[0]
                self.assertEqual(Path(command[1]),output/'work-modalwidgets-proxy/widget.exe')
                report=json.loads((output/'summary.json').read_text())
                self.assertEqual(len(report['runs']),1)
                self.assertEqual(report['runs'][0]['stage'],'synthetic-widget-stage')
                self.assertEqual(report['runs'][0]['resolution'],'1920x1080')
                self.assertEqual(report['runs'][0]['exe_sha256'],metadata['candidate_sha256'])
                self.assertNotIn('complete_hd_manifest',report)
                self.assertFalse(report['runs'][0]['gameplay_verified'])
                self.assertFalse((output/'work-gog').exists())

    def test_debugger_reselects_only_retained_live_owned_identity_while_stopped(self):
        body=tool.HARNESS.split('static void select_owned_primary(Session &s) {',1)[1].split('static void pause_owned',1)[0]
        ordered=('WaitForSingleObject(s.process,0)', 'WaitForSingleObject(s.primary_thread,0)',
                 'GetExecutionStatus', 'status!=DEBUG_STATUS_BREAK', 'GetProcessIdBySystemId(s.owned_pid',
                 'SetCurrentProcessId(process)', 'GetThreadIdBySystemId(s.primary_tid',
                 'SetCurrentThreadId(thread)', 'GetCurrentProcessSystemId(&pid)', 'GetCurrentThreadSystemId(&tid)',
                 'pid!=s.owned_pid || tid!=s.primary_tid', 'GetInstructionOffset(&ip)', 'REAL_CONTEXT')
        self.assertEqual([body.index(part) for part in ordered],sorted(body.index(part) for part in ordered))
        self.assertIn('else if (!crashed) select_owned_primary(s);',tool.HARNESS)
        self.assertIn('CloseHandle(primary_thread)',tool.HARNESS)
        for forbidden in ('WriteVirtual','SetThreadContext','SetExecutionStatus','TerminateProcess'):
            self.assertNotIn(forbidden,body)

    def test_harness_uses_owned_handles_and_no_input_injection(self):
        for text in ('JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE', 'DEBUG_END_ACTIVE_TERMINATE',
                     'AssignProcessToJobObject', 'REAL_EXE_ENTRY observed=1'):
            self.assertIn(text,tool.HARNESS)
        for text in ('SendInput(', 'PostMessage(', 'SetCursorPos(', 'WriteVirtual('):
            self.assertNotIn(text,tool.HARNESS)


if __name__ == '__main__':
    unittest.main(verbosity=2)
