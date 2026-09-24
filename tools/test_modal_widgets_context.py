"""Offline boundary fixtures; synthetic builders never establish game proof."""
import copy
from dataclasses import replace
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import modal_widgets_context as context


class WidgetContextTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='mwgctx-')
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.repo = self.folder / 'repo'
        self.bundle = self.folder / 'bundle'
        self.bundle.mkdir()
        self.sources = {}
        for name in sorted(context.RECIPE_SOURCE_PATHS):
            path = self.repo / name
            path.parent.mkdir(parents=True, exist_ok=True)
            raw = (context.ROOT / name).read_bytes()
            self.sources[name] = context.sha(raw)
            path.write_bytes(raw)
        for name in context.AUTHENTICATION_SOURCES:
            target = self.repo / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((context.ROOT / name).read_bytes())
        self.original = b'synthetic original bytes'
        self.candidate = b'synthetic widget candidate bytes'
        self.probe = '.echo synthetic widget-context fixture\n'
        self.path = self.bundle / 'fixture.candidate.json'
        self.exe = self.bundle / 'fixture.exe'
        self.command = self.bundle / 'fixture.cdb'
        self.installed = self.folder / 'installed.exe'
        self.installed.write_bytes(self.original)
        self.manifest = self.make_manifest()
        self.write_bundle()
        self.root_patch = patch.object(context, 'ROOT', self.repo)
        self.root_patch.start(); self.addCleanup(self.root_patch.stop)
        self.original_patch = patch.object(context, 'ORIGINAL_SHA256', context.sha(self.original))
        self.original_patch.start(); self.addCleanup(self.original_patch.stop)
        self.path_patch = patch.object(context, 'ORIGINAL_PATH', self.installed)
        self.path_patch.start(); self.addCleanup(self.path_patch.stop)
        self.build_patch = patch.object(context.builder, 'build_candidate',
                                       return_value=(self.candidate, self.manifest, self.probe))
        self.build = self.build_patch.start(); self.addCleanup(self.build_patch.stop)

    def make_manifest(self):
        prefix = context.STAGE.removesuffix('-modalwidgets-validation')
        entries = {'is_active': 0x600000}
        owner = dict(state_va=0x601000, modal_entry_vas=entries, native_spans=[(0x432ED0, 2032, 'a' * 64)])
        complete = dict(stage=prefix + '-validation', recipe_revision='complete_hd_v1',
                        candidate_sha256='1' * 64, resolution='800x600',
                        predecessor={'base_candidate': owner})
        def child(base, suffix, revision, digest):
            return dict(stage=prefix + suffix, recipe_revision=revision, resolution='800x600',
                        candidate_sha256=digest, base_stage=base['stage'],
                        base_candidate_sha256=base['candidate_sha256'], input_sha256=base['candidate_sha256'],
                        base_candidate=base)
        slots = child(complete, '-modalslots-validation', 'owned_barracks_dirty_slots_v1', '2' * 64)
        primary = child(slots, '-modalprimary-validation', 'owned_modal_primary_v1', '3' * 64)
        text = child(primary, '-modalprimarytext-validation', 'owned_modal_primary_text_v1', '4' * 64)
        manifest = child(text, '-modalwidgets-validation', context.REVISION, context.sha(self.candidate))
        manifest.update(schema=context.SCHEMA,
                        original_sha256=context.sha(self.original), output_sha256=context.sha(self.candidate),
                        probe_sha256=context.sha(self.probe.encode()), source_hashes=dict(self.sources),
                        modal_state_va=0x601000, modal_entry_vas=entries, integer_field=1,
                        flag=False, allocation={'code_va': 0x602000, 'bytes': 4096},
                        probe_contract={'stage': context.STAGE})
        return manifest

    def write_bundle(self, manifest=None):
        self.path.write_bytes((json.dumps(self.manifest if manifest is None else manifest) + '\n').encode())
        self.exe.write_bytes(self.candidate)
        self.command.write_bytes(self.probe.encode())

    def load(self):
        return context.load_context(self.original, self.candidate, self.path)

    def test_exact_bundle_returns_distinct_real_ancestor_contexts(self):
        result = self.load()
        self.build.assert_called_once_with(self.original, '800x600')
        self.assertEqual(result['candidate_sha256'], context.sha(self.candidate))
        self.assertEqual(result['manifest_sha256'], context.sha(self.path.read_bytes()))
        self.assertEqual(result['manifest_canonical_sha256'], context.sha(context.canonical_json(self.manifest).encode()))
        self.assertEqual(result['stage'], context.STAGE)
        self.assertEqual(result['text_context']['stage'], self.manifest['base_candidate']['stage'])
        self.assertNotEqual(result['text_context']['stage'], result['stage'])
        self.assertEqual(result['primary_context']['candidate_sha256'], '3' * 64)
        self.assertEqual(result['slots_context']['candidate_sha256'], '2' * 64)
        self.assertEqual(result['owner_context']['state_va'], 0x601000)
        self.assertEqual(result['owner_context']['native_spans'], [[0x432ED0, 2032, 'a' * 64]])
        self.assertFalse({'passed', 'runtime_accepted', 'promotion_ready', 'manual_input_proof'} & result.keys())
        for name, depth in (('text_context', 1), ('primary_context', 2), ('slots_context', 3)):
            result[name]['stage'] = 'changed'
            nested = result['manifest']
            for _ in range(depth): nested = nested['base_candidate']
            self.assertNotEqual(nested['stage'], 'changed')
        result['owner_context']['state_va'] = 1
        nested = result['manifest']['base_candidate']['base_candidate']['base_candidate']['base_candidate']
        self.assertEqual(nested['predecessor']['base_candidate']['state_va'], 0x601000)
        self.assertEqual(len(result['source_hashes']), 36)
        self.assertEqual(result['authentication_source_hashes'], context.AUTHENTICATION_SOURCES)

    def test_ambiguous_json_rejected_before_builder(self):
        cases = [b'[]', b'{"x":1,"x":2}', b'{"a":{"x":1,"\\u0078":1}}',
                 b'{"x":NaN}', b'{"x":Infinity}', b'{"x":-Infinity}', b'{"x":1e999}', b'\xff']
        for raw in cases:
            with self.subTest(raw=raw):
                self.path.write_bytes(raw)
                with self.assertRaises((ValueError, UnicodeError)):
                    self.load()
        self.build.assert_not_called()

    def test_typed_metadata_or_allocation_edits_rejected(self):
        cases = [('integer_field', True), ('integer_field', 1.0), ('flag', 0),
                 ('allocation', {'code_va': 0x603000, 'bytes': 4096}),
                 ('probe_contract', {'stage': 'predecessor'})]
        for name, value in cases:
            with self.subTest(name=name, value=value):
                mutated = copy.deepcopy(self.manifest); mutated[name] = value
                self.write_bundle(mutated)
                with self.assertRaisesRegex(ValueError, 'typed source rebuild'):
                    self.load()

    def test_stage_resolution_revision_or_identity_mix_rejected(self):
        cases = [('stage', self.manifest['base_candidate']['stage']), ('recipe_revision', 'owned_modal_primary_v1'),
                 ('schema', 'other'), ('resolution', '1920x1080'), ('resolution', True),
                 ('candidate_sha256', '0' * 64), ('original_sha256', '0' * 64),
                 ('probe_sha256', '0' * 64), ('base_candidate_sha256', '0' * 64),
                 ('input_sha256', '0' * 64)]
        for name, value in cases:
            with self.subTest(name=name):
                mutated = copy.deepcopy(self.manifest); mutated[name] = value
                self.write_bundle(mutated)
                with self.assertRaises(ValueError):
                    self.load()
        self.build.assert_not_called()

    def test_mutated_ancestor_cannot_replace_widget_context(self):
        cases = [('stage', 'other'), ('recipe_revision', 'other'), ('resolution', '1024x768'),
                 ('candidate_sha256', '5' * 64)]
        for depth in range(4):
            for name, value in cases:
                with self.subTest(depth=depth, name=name):
                    mutated = copy.deepcopy(self.manifest)
                    child = mutated
                    for _ in range(depth + 1): child = child['base_candidate']
                    child[name] = value
                    self.write_bundle(mutated)
                    with self.assertRaises(ValueError): self.load()
        self.build.assert_not_called()

    def test_owner_state_or_entries_mismatch_rejected(self):
        for key, value in [('state_va', 0x602000), ('modal_entry_vas', {'is_active': 0x600010})]:
            mutated = copy.deepcopy(self.manifest)
            owner = mutated['base_candidate']['base_candidate']['base_candidate']['base_candidate']['predecessor']['base_candidate']
            owner[key] = value
            self.write_bundle(mutated)
            with self.assertRaisesRegex(ValueError, 'owner context differs'): self.load()
        self.build.assert_not_called()

    def test_unknown_original_and_mutable_bytes_rejected(self):
        for original, candidate in [(b'unknown', self.candidate), (bytearray(self.original), self.candidate),
                                    (self.original, bytearray(self.candidate))]:
            with self.subTest(original=type(original), candidate=type(candidate)):
                with self.assertRaises(ValueError): context.load_context(original, candidate, self.path)
        self.build.assert_not_called()

    def test_mismatched_or_missing_siblings_rejected(self):
        for target in (self.path, self.exe, self.command):
            for content in (None, b'other candidate or command'):
                with self.subTest(target=target.name, content=content):
                    self.write_bundle()
                    if content is None: target.unlink()
                    else: target.write_bytes(content)
                    with self.assertRaises((OSError, ValueError)): self.load()
        self.build.assert_not_called()

    def test_source_paths_and_pins_fail_before_source_reads(self):
        names = ('../outside.py', '/outside.py', 'C:/outside.py', 'tools/../outside.py',
                 'tools//outside.py', 'tools/./outside.py', r'tools\outside.py',
                 'Tools/outside.py', 'tools/outside.txt')
        for name in names:
            with self.subTest(name=name):
                mutated = copy.deepcopy(self.manifest); mutated['source_hashes'][name] = 'a' * 64
                self.write_bundle(mutated)
                with patch.object(context, '_source_snapshots') as reads:
                    with self.assertRaisesRegex(ValueError, 'canonical repo-relative'):
                        self.load()
                    reads.assert_not_called()
        for key in context.FROZEN_SOURCES:
            for change in ('wrong', 'missing'):
                with self.subTest(pin=key, change=change):
                    mutated = copy.deepcopy(self.manifest)
                    if change == 'wrong': mutated['source_hashes'][key] = '0' * 64
                    else: del mutated['source_hashes'][key]
                    self.write_bundle(mutated)
                    with self.assertRaisesRegex(ValueError, 'frozen widget/text source identity|recipe source path set'):
                        self.load()
        self.build.assert_not_called()

    def test_missing_or_extra_recipe_source_rejected_before_resolution(self):
        # The entire 36-source inventory is admitted before even resolving a
        # caller-declared path; syntactically valid additions confer no trust.
        keys = sorted(context.RECIPE_SOURCE_PATHS)
        cases = []
        for key in keys:
            missing = dict(self.sources); del missing[key]
            cases.append(missing)
        extra = dict(self.sources, **{'tools/current_evidence_refresh.py': 'a' * 64})
        cases.extend([extra, dict(context.FROZEN_SOURCES)])
        for sources in cases:
            with self.subTest(keys=len(sources)):
                # ROOT is already a resolved concrete fixture path. Any call
                # beyond its one root resolution would inspect declared paths.
                resolve = Path.resolve
                calls = []
                def counted(path, *args, **kwargs):
                    calls.append(path)
                    return resolve(path, *args, **kwargs)
                with patch.object(Path, 'resolve', counted):
                    with self.assertRaisesRegex(ValueError, 'recipe source path set'):
                        context._source_paths(sources)
                self.assertEqual(calls, [self.repo])
        self.build.assert_not_called()

    def test_source_byte_mismatch_rejected_before_builder(self):
        key = next(iter(context.FROZEN_SOURCES)); path = self.repo / key
        path.write_bytes(path.read_bytes() + b'\n# changed\n')
        with self.assertRaisesRegex(ValueError, 'source hash differs'): self.load()
        self.build.assert_not_called()

    def test_hardlinked_source_alias_rejected(self):
        key, alias = sorted(context.RECIPE_SOURCE_PATHS - context.FROZEN_SOURCES.keys())[:2]
        (self.repo / alias).unlink()
        try: os.link(self.repo / key, self.repo / alias)
        except OSError as error: self.skipTest('hardlinks unavailable: ' + str(error))
        mutated = copy.deepcopy(self.manifest); mutated['source_hashes'][alias] = self.sources[key]
        self.write_bundle(mutated)
        with self.assertRaisesRegex(ValueError, 'source files alias'): self.load()
        self.build.assert_not_called()

    def test_checkout_and_original_alias_boundaries(self):
        inside = self.repo / 'candidate.candidate.json'
        with self.assertRaisesRegex(ValueError, 'outside the active checkout'):
            context.load_context(self.original, self.candidate, inside)
        alias = self.folder / 'installed.candidate.json'
        with self.assertRaisesRegex(ValueError, 'original executable'):
            context.load_context(self.original, self.candidate, alias)
        with self.assertRaisesRegex(ValueError, 'suffix'):
            context.load_context(self.original, self.candidate, self.folder / 'other.json')
        self.build.assert_not_called()

    def test_drift_during_rebuild_rejected(self):
        source = self.repo / next(iter(context.FROZEN_SOURCES))
        for target in (self.path, self.exe, self.command, source):
            with self.subTest(target=target.name):
                before = target.read_bytes()
                def changed(*args):
                    target.write_bytes(before + b' ')
                    return self.candidate, self.manifest, self.probe
                self.build.side_effect = changed
                try:
                    with self.assertRaisesRegex(ValueError, 'changed|source hash differs'): self.load()
                finally: target.write_bytes(before)
        self.build.side_effect = None
        # Exercise a same-byte identity/metadata change without touching sources.
        def touched(*args):
            stat = self.exe.stat()
            os.utime(self.exe, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1000000000))
            return self.candidate, self.manifest, self.probe
        self.build.side_effect = touched
        with self.assertRaisesRegex(ValueError, 'bundle changed'): self.load()

    def test_context_reader_drift_rejected_without_editing_real_source(self):
        reader = Path(context.__file__).resolve()
        snapshot = context._snapshot
        reads = []
        def changed(path):
            result = snapshot(path)
            if Path(path).resolve() == reader:
                reads.append(result)
                if len(reads) == 2:
                    return replace(result, data=result.data + b'\n# simulated drift\n')
            return result
        with patch.object(context, '_snapshot', side_effect=changed):
            with self.assertRaisesRegex(ValueError, 'context or recipe source changed'): self.load()
        self.assertEqual(len(reads), 2)
        self.assertEqual(reader.read_bytes(), reads[0].data)

    def test_malformed_ancestor_and_missing_owner_fail_before_builder(self):
        for depth in range(4):
            for value in (None, [], 1, True, 'older stage'):
                with self.subTest(depth=depth, value=value):
                    mutated = copy.deepcopy(self.manifest)
                    parent = mutated
                    for _ in range(depth): parent = parent['base_candidate']
                    parent['base_candidate'] = value
                    self.write_bundle(mutated)
                    with self.assertRaises(ValueError): self.load()
        for value in (None, [], {}, {'base_candidate': None}, {'base_candidate': {}}):
            mutated = copy.deepcopy(self.manifest)
            parent = mutated
            for _ in range(4): parent = parent['base_candidate']
            parent['predecessor'] = value
            self.write_bundle(mutated)
            with self.assertRaises(ValueError): self.load()
        self.build.assert_not_called()

    def test_source_map_types_and_digest_types_fail_before_builder(self):
        key = next(iter(self.sources))
        cases = [None, [], {}, True, 'source hash map']
        for value in (None, True, 0, 1.0, [], {}, 'a' * 63, 'a' * 65, 'A' * 64, 'z' * 64):
            sources = dict(self.sources); sources[key] = value
            cases.append(sources)
        for sources in cases:
            with self.subTest(sources=repr(sources)[:100]):
                mutated = copy.deepcopy(self.manifest); mutated['source_hashes'] = sources
                self.write_bundle(mutated)
                with self.assertRaises(ValueError): self.load()
        self.build.assert_not_called()

    def test_deep_typed_metadata_is_compared_without_python_numeric_aliases(self):
        for path, value in ((('base_candidate', 'base_candidate', 'base_candidate', 'base_candidate',
                             'predecessor', 'base_candidate', 'native_spans'), [[0x432ED0, 2032.0, 'a' * 64]]),
                            (('allocation', 'code_va'), float(0x602000)),
                            (('modal_entry_vas', 'is_active'), float(0x600000))):
            mutated = copy.deepcopy(self.manifest); target = mutated
            for name in path[:-1]: target = target[name]
            target[path[-1]] = value
            self.write_bundle(mutated)
            with self.assertRaisesRegex(ValueError, 'typed source rebuild|owner context differs'): self.load()

    def test_bundle_hardlinks_and_original_hardlink_rejected(self):
        self.command.unlink()
        try: os.link(self.exe, self.command)
        except OSError as error: self.skipTest('hardlinks unavailable: ' + str(error))
        with self.assertRaisesRegex(ValueError, 'bundle files alias'): self.load()
        self.command.unlink()
        self.command.write_bytes(self.probe.encode())
        self.exe.unlink()
        os.link(self.installed, self.exe)
        with self.assertRaisesRegex(ValueError, 'original executable'): self.load()
        self.build.assert_not_called()

    def test_inherited_authentication_dependency_pin_and_drift_fail_closed(self):
        name = next(iter(context.AUTHENTICATION_SOURCES))
        source = self.repo / name
        saved = source.read_bytes()
        source.write_bytes(saved + b'\n# pre-existing change\n')
        with self.assertRaisesRegex(ValueError, 'source hash differs'): self.load()
        self.build.assert_not_called()
        source.write_bytes(saved)
        def changed(*args):
            source.write_bytes(saved + b'\n# reconstruction-time change\n')
            return self.candidate, self.manifest, self.probe
        self.build.side_effect = changed
        with self.assertRaisesRegex(ValueError, 'source hash differs'): self.load()
        source.write_bytes(saved)
        def touched(*args):
            stat = source.stat()
            os.utime(source, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1000000000))
            return self.candidate, self.manifest, self.probe
        self.build.side_effect = touched
        with self.assertRaisesRegex(ValueError, 'context or recipe source changed'): self.load()

    def test_rebuild_candidate_probe_and_source_failures_propagate(self):
        for result in [(b'wrong', self.manifest, self.probe), (bytearray(self.candidate), self.manifest, self.probe),
                       (self.candidate, self.manifest, 'wrong'), (self.candidate, self.manifest, self.probe.encode())]:
            self.build.return_value = result
            with self.assertRaisesRegex(ValueError, 'frozen widget-source rebuild'): self.load()
        self.build.side_effect = ValueError('native expected old bytes differ')
        with self.assertRaisesRegex(ValueError, 'native expected old bytes differ'): self.load()


if __name__ == '__main__':
    unittest.main()
