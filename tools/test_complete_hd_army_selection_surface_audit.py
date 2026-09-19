"""Generated pixel/artifact fixtures only; no game, debugger or runtime proof.

The file-graph fixture mocks only native-asset authentication and the complete
trace reconstruction boundary. Every pixel, artifact hash, header, PNG and
ownership-consistency check remains real. Production exposes no such bypass.
"""
import copy
import json
from pathlib import Path
import struct
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import complete_hd_army_selection_surface_audit as audit
from hd_layout_asset_composition import Sprite
from test_frame_surface_audit import synthetic_frame, surface


def assets_fixture():
    return dict(frame=synthetic_frame(),
                action={i: Sprite(64, 32, tuple(10 + (i * 17 + x + y * 3) % 190 for y in range(32) for x in range(64)))
                        for i in range(12)} | {14: Sprite(64, 32, (None,) * 2048)},
                portraits={i: Sprite(32, 64, tuple(30 + (i + x * 7 + y) % 140 for y in range(64) for x in range(32))) for i in (1, 16)},
                backing=Sprite(387, 66, tuple(180 + (x + y * 3) % 50 for y in range(66) for x in range(387))),
                members={'synthetic_assets': True})


def pixel_fixture(layout, assets):
    raw = surface(assets['frame'], layout.framed)
    def put(sprite, left, top):
        for y in range(sprite.height):
            for x in range(sprite.width):
                value = sprite.pixels[y * sprite.width + x]
                if value is not None:
                    raw[(top + y) * layout.width + left + x] = value
    put(assets['backing'], layout.backing.left, layout.backing.top)
    for i, kind in enumerate(audit.TYPES):
        rect = layout.portrait(i)
        put(assets['portraits'][kind], rect.left, rect.top)
    for i, rect in enumerate(layout.framed.action_cells):
        put(assets['action'][i * 2], rect.left, rect.top)
    return bytes(raw)


class PixelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.assets = assets_fixture()

    def test_all_six_geometries_and_every_body_backing_frame_and_cell(self):
        for width, height in ((800, 600), (1024, 768), (1280, 720), (1280, 960), (1920, 1080), (802, 602)):
            layout = audit.FramedArmyViewport(width, height)
            raw = pixel_fixture(layout, self.assets)
            result = audit.audit_pixels(raw, layout, self.assets)
            self.assertTrue(result['passed'], (width, height, result))
            self.assertEqual(result['exposed_backing']['checked_pixels'], 9158)
            self.assertEqual(len(audit.backing_bytes(raw, layout)), 25542)
            self.assertEqual(len(result['portrait_bodies']['slots']), 8)
            self.assertTrue(all(r['checked_pixels'] == 928 for r in result['portrait_bodies']['slots']))

    def test_single_pixel_in_every_required_region_fails(self):
        layout = audit.FramedArmyViewport(1024, 768)
        baseline = pixel_fixture(layout, self.assets)
        points = [(0, 0), (1023, 400), (0, 400), (40, 767), (347, 753), (418, 751)]
        points += [(r.left + 2, r.top + 2) for r in layout.framed.action_cells]
        points += [(layout.portrait(i).left + 9, layout.portrait(i).top + 21) for i in range(8)]
        for x, y in points:
            raw = bytearray(baseline); raw[y * 1024 + x] ^= 1
            self.assertFalse(audit.audit_pixels(bytes(raw), layout, self.assets)['passed'], (x, y))

    def test_count_region_is_disclosed_not_misrepresented_as_body_proof(self):
        layout = audit.FramedArmyViewport(800, 600)
        raw = bytearray(pixel_fixture(layout, self.assets))
        rect = layout.portrait(0); raw[(rect.top + 53) * 800 + rect.left + 10] ^= 1
        self.assertTrue(audit.audit_pixels(bytes(raw), layout, self.assets)['passed'])

    def test_truncated_raw_and_malformed_or_transparent_source_fail_closed(self):
        layout = audit.FramedArmyViewport(800, 600); raw = pixel_fixture(layout, self.assets)
        for value in (raw[:-1], raw + b'x', bytearray(raw)):
            with self.assertRaises(ValueError): audit.audit_pixels(value, layout, self.assets)
        for sprite in (Sprite(32, 64, ()), Sprite(32, 64, (None,) * 2048), Sprite(32, 64, (256,) * 2048)):
            broken = self.assets | {'portraits': self.assets['portraits'] | {16: sprite}}
            with self.assertRaises(ValueError): audit.audit_pixels(raw, layout, broken)

    def test_unknown_real_resources_never_gain_source_authority(self):
        with self.assertRaisesRegex(ValueError, 'minimum.res'):
            audit.load_assets(b'synthetic', b'synthetic')


class CaptureGraph:
    """Retained host-shaped files explicitly containing synthetic observations."""
    def __init__(self, root):
        self.root = root; self.run = root / 'capture'; self.run.mkdir()
        self.work = root / 'work'; (self.work / 'DATA').mkdir(parents=True); (self.work / 'save').mkdir()
        self.assets = assets_fixture(); self.layout = audit.FramedArmyViewport(800, 600)
        self.raw = pixel_fixture(self.layout, self.assets)
        self.plan = dict(schema=audit.PLAN_SCHEMA, stage=audit.bar.COMPLETE_HD_STAGE, resolution='800x600', width=800, height=600,
                         out_dir=str(self.run), work_dir=str(self.work), environment='hidden_cdb_host',
                         child_environment={'CLASH_PROXY_PRESENT': '0', 'parent_environment_modified': False},
                         **{name: False for name in audit.FALSE_FLAGS})
        p = self.plan
        for key in ('original', 'input_candidate', 'candidate_path', 'proxy_input', 'proxy_path', 'cdb', 'python'):
            path = root / (key + '.fixture'); path.write_bytes(b'synthetic ' + (b'candidate' if 'candidate' in key else b'proxy' if 'proxy' in key else key.encode()))
            p[key] = str(path)
        for key, relative in (('host_path', 'scripts/cdb/run_complete_hd_army_selection_capture.ps1'),
                              ('producer', 'tools/complete_hd_army_selection_probe.py'), ('trace', 'tools/complete_hd_army_selection_trace.py'),
                              ('converter', 'tools/cdb_surface_dump_to_png.py')):
            p[key] = str((audit.ROOT / relative).resolve())
        self.write(self.work / 'save/0.dat', b'synthetic save')
        p['save'] = str(self.work / 'save/0.dat')
        self.write(self.work / 'DATA/minimum.res', b'synthetic minimum')
        self.write(self.work / 'DATA/GFX3.RES', b'synthetic gfx3')
        p['assets_before'] = {path.relative_to(self.work).as_posix(): audit.sha(path.read_bytes()) for path in self.work.rglob('*') if path.is_file()}
        manifest = root / 'candidate.json'; self.json(manifest, {'synthetic_manifest': True})
        p['candidate_manifest'] = str(manifest)
        p['candidate_manifest_canonical_sha256'] = audit.sha(audit.canonical({'synthetic_manifest': True}).encode())
        for key, file in (('original_sha256', 'original'), ('candidate_sha256', 'candidate_path'), ('save_sha256', 'save'), ('proxy_sha256', 'proxy_path')):
            p[key] = audit.sha(Path(p[file]).read_bytes())
        self.probe = b'synthetic canonical probe\n'; p['probe_sha256'] = audit.sha(self.probe)
        packet = {'stage':p['stage'], 'resolution':p['resolution'], 'unit_squad_types':audit.TYPES, 'capture_dir':str(self.run)}
        self.json(self.run / 'packet.json', packet)
        self.write(self.run / 'complete-hd-army-selection.cdb', self.probe)
        p['identities'] = [self.receipt(Path(p[key])) for key in ('original', 'input_candidate', 'save', 'candidate_manifest', 'host_path', 'producer', 'trace', 'converter', 'cdb', 'python', 'proxy_input')]
        self.write(self.run / 'host.ps1', Path(p['host_path']).read_bytes())
        cdb = dict(path=p['cdb'], process_id=101, creation_filetime=1010, handle_retained=True)
        game = dict(path=p['candidate_path'], process_id=102, creation_filetime=1020, handle_retained=True, parent_process_id=101, candidate_sha256=p['candidate_sha256'])
        self.ready = dict(surface=0x210000, base=0x300000, width=800, height=600)
        prefix = b'synthetic native selection observed\n'; final = prefix + b'synthetic debugger cleanup\n'
        self.write(self.run / 'capture-prefix.log', prefix); self.write(self.run / 'cdb.log', final)
        self.fresh = dict(passed=True, ready_for_host_capture=True, source_authenticated=True, whole_candidate_bound=True,
                          selection_sequence={'synthetic_sequence':True}, surface=self.ready,
                          source=dict(original_sha256=p['original_sha256'], candidate_sha256=p['candidate_sha256'], save_sha256=p['save_sha256'],
                                      probe_raw_sha256=p['probe_sha256'], candidate_manifest_canonical_sha256=p['candidate_manifest_canonical_sha256'], source_sha256={}), failures=[])
        final_trace = copy.deepcopy(self.fresh); final_trace['source']['log_raw_sha256'] = audit.sha(final)
        prefix_trace = copy.deepcopy(self.fresh); prefix_trace['source']['log_raw_sha256'] = audit.sha(prefix)
        self.json(self.run / 'trace.json', prefix_trace); self.json(self.run / 'trace-final.json', final_trace)
        self.summary = dict(schema=audit.HOST_SCHEMA, passed=True, executed=True, cleanup_verified=True, clean_stable_pair=True,
                            source_and_input_identities_unchanged=True, status='bounded_hidden_complete_hd_army_selection_capture', failures=[], plan=p,
                            frame_verified=False, action_bar_verified=False, **{name:False for name in audit.FALSE_FLAGS},
                            packet=self.receipt(self.run / 'packet.json'), probe=self.receipt(self.run / 'complete-hd-army-selection.cdb'),
                            capture_prefix=self.receipt(self.run / 'capture-prefix.log'), final_log=self.receipt(self.run / 'cdb.log') | {'capture_prefix_preserved':True},
                            final_trace=final_trace, trace=prefix_trace, cdb=cdb, candidates=[game], assets_after=copy.deepcopy(p['assets_before']),
                            cleanup=dict(cdb=dict(identity=cdb, absent=True, handle_closed=True),
                                         candidates=[dict(identity=game, absent=True, handle_closed=True)], desktop_closed=True), snapshots=[])
        for label in audit.LABELS[:2]:
            self.write(self.run / (label + '.raw'), self.raw); self.summary[label] = self.receipt(self.run / (label + '.raw'))
        header = bytearray(188); struct.pack_into('<HHI', header, 0, 800, 600, self.ready['base']); struct.pack_into('<I', header, 184, 0x50ee24)
        for label in audit.LABELS[2:]:
            folder = self.run / label; folder.mkdir(); self.write(folder / 'surface.raw', self.raw)
            row = self.receipt(folder / 'surface.raw') | dict(width=800, height=600, pitch=800, pixel_reads=1, header_reads=2, e0_reads=2,
                                                           paused=True, capture='e0_software_diagnostic', game_identity=game,
                                                           surface=self.ready['surface'], base=self.ready['base'], reads={})
            for phase in ('before', 'after'):
                row['reads'][phase] = {}
                for name, data, address in (('e0', struct.pack('<I', self.ready['surface']), 0x5202e0), ('header', bytes(header), self.ready['surface'])):
                    path = folder / ('surface-' + phase + '-' + name + '.raw'); self.write(path, data)
                    row['reads'][phase][name] = self.receipt(path) | {'address': address}
            self.summary['snapshots'].append(row)
        self.summary['snapshot'] = self.summary['snapshots'][0]
        palette_path = root / 'palette.fixture'; palette_path.write_bytes(bytes(v for i in range(256) for v in (i, i, i, 0)))
        p['palette_path'] = str(palette_path); self.summary['palette'] = self.receipt(palette_path)
        self.write(self.run / 'surface.raw', self.raw)
        self.summary['png'] = audit.png.convert(self.run / 'surface.raw', self.run / 'surface.png', 800, 600, 800,
                                              self.run / 'surface.png.json', self.run / 'capture-prefix.log', palette_path)
        self.persist()

    def write(self, path, data): path.write_bytes(data)
    def json(self, path, value): path.write_text(json.dumps(value), encoding='utf-8')
    def receipt(self, path): return dict(path=str(path), sha256=audit.sha(path.read_bytes()), bytes=path.stat().st_size)
    def persist(self):
        self.plan = self.summary['plan']
        self.json(self.run / 'plan.json', self.plan); self.json(self.run / 'summary.json', self.summary)
    def evaluate(self):
        self.persist()
        with patch.object(audit, 'load_assets', return_value=self.assets), \
             patch.object(audit.trace, 'evaluate_bound_trace', side_effect=lambda *a, **kw: copy.deepcopy(self.fresh)), \
             patch.object(audit.trace, 'evaluate_trace', return_value={'passed':True, 'selection_sequence':self.fresh['selection_sequence']}):
            return audit.audit_summary(self.run / 'summary.json', self.work)


class HostArtifactTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.graph = CaptureGraph(Path(self.temp.name))

    def test_bound_synthetic_graph_checks_every_capture_and_preserves_limits(self):
        result = self.graph.evaluate()
        self.assertTrue(result['passed'], result['failures'])
        self.assertEqual(set(result['captures']), set(audit.LABELS))
        self.assertTrue(result['complete_backing']['passed']); self.assertTrue(result['screenshot']['passed'])
        for key in (*audit.FALSE_FLAGS, 'runtime_accepted', 'count_text_verified', 'map_unit_artwork_verified', 'cleanup_observed_by_this_audit'):
            self.assertIs(result[key], False)

    def test_host_false_null_and_excessive_claims_never_pass(self):
        original = copy.deepcopy(self.graph.summary)
        for key, values in (('passed', [False, None, 1]), ('cleanup_verified', [False, None]), ('clean_stable_pair', [False, None]),
                            ('manual_input_proof', [True, None]), ('frame_verified', [True]), ('promotion_ready', [True])):
            for value in values:
                self.graph.summary = copy.deepcopy(original); self.graph.summary[key] = value
                result = self.graph.evaluate(); self.assertFalse(result['passed'], (key, value)); self.assertTrue(result['failures'])

    def test_missing_and_truncated_raw_fail_even_with_true_host_flags(self):
        path = self.graph.run / 'before-redraw.raw'; path.write_bytes(self.graph.raw[:-1])
        result = self.graph.evaluate(); self.assertFalse(result['passed']); self.assertIn('SHA-256', str(result['failures']))
        path.unlink(); self.assertFalse(self.graph.evaluate()['passed'])

    def test_full_backing_change_outside_body_is_required_for_aggregate(self):
        path = self.graph.run / 'before-redraw.raw'; raw = bytearray(self.graph.raw)
        rect = self.graph.layout.portrait(0); raw[(rect.top + 53) * 800 + rect.left + 10] ^= 1
        path.write_bytes(raw); self.graph.summary['before-redraw'] = self.graph.receipt(path)
        result = self.graph.evaluate()
        self.assertFalse(result['passed'], result)
        self.assertTrue(result['captures']['before-redraw']['passed'])
        self.assertFalse(result['complete_backing']['passed'])

    def test_before_redraw_frame_failure_cannot_hide_behind_good_final(self):
        path = self.graph.run / 'before-redraw.raw'; raw = bytearray(self.graph.raw); raw[0] ^= 1
        path.write_bytes(raw); self.graph.summary['before-redraw'] = self.graph.receipt(path)
        result = self.graph.evaluate()
        self.assertFalse(result['passed']); self.assertFalse(result['captures']['before-redraw']['frame']['passed'])
        self.assertTrue(result['captures']['capture-1']['passed'])

    def test_new_candidate_receipt_cannot_replace_complete_trace_authority(self):
        self.graph.fresh['passed'] = False; self.graph.fresh['failures'] = ['synthetic source reconstruction rejected']
        result = self.graph.evaluate(); self.assertFalse(result['passed']); self.assertIn('source-bound trace failed', str(result['failures']))

    def test_source_drift_and_inventory_addition_are_bound(self):
        path = Path(self.graph.plan['python']); path.write_bytes(b'drift')
        self.assertFalse(self.graph.evaluate()['passed'])
        path.write_bytes(b'synthetic python'); (self.graph.work / 'added.fixture').write_bytes(b'unplanned')
        result = self.graph.evaluate(); self.assertFalse(result['passed']); self.assertIn('inventory changed', str(result['failures']))

    def test_png_rehash_cannot_disguise_unrelated_pixels(self):
        path = self.graph.run / 'surface.png'; path.write_bytes(b'unrelated PNG')
        metadata = self.graph.summary['png']; metadata['png_sha256'] = audit.sha(path.read_bytes())
        self.graph.json(self.graph.run / 'surface.png.json', metadata)
        result = self.graph.evaluate(); self.assertFalse(result['passed']); self.assertIn('does not encode', str(result['failures']))

    def test_artifact_drift_clears_authority_but_preserves_measured_pixels(self):
        real_pixels = audit.audit_pixels
        calls = 0
        def change_after_measurement(*args):
            nonlocal calls
            result = real_pixels(*args); calls += 1
            if calls == 5:
                path = self.graph.run / 'surface.png'
                path.write_bytes(path.read_bytes() + b'drift after verification')
            return result
        with patch.object(audit, 'audit_pixels', side_effect=change_after_measurement):
            result = self.graph.evaluate()
        self.assertIn('artifact changed during audit', str(result['failures']))
        for flag in ('passed', 'source_authenticated', 'pixels_verified', 'cleanup_receipts_verified', 'ready_for_bounded_selection_review'):
            self.assertIs(result[flag], False, flag)
        self.assertEqual(len(result['captures']), 5)
        self.assertTrue(all(row['passed'] for row in result['captures'].values()))
        self.assertTrue(result['complete_backing']['passed'])

    def test_snapshot_alias_missing_triplet_header_and_cleanup_identity_reject(self):
        original = copy.deepcopy(self.graph.summary)
        mutations = [lambda s: s['snapshots'].pop(), lambda s: s['snapshots'][1].update(width=True),
                     lambda s: s['snapshots'][1]['reads']['before']['e0'].update(address=1),
                     lambda s: s['cleanup']['candidates'][0].update(absent=False),
                     lambda s: s['candidates'][0].update(parent_process_id=101.0),
                     lambda s: s['candidates'][0].update(creation_filetime=1000),
                     lambda s: s['plan']['child_environment'].update(parent_environment_modified=0),
                     lambda s: s['snapshot'].update(paused=None)]
        for mutate in mutations:
            self.graph.summary = copy.deepcopy(original); mutate(self.graph.summary)
            self.assertFalse(self.graph.evaluate()['passed'])

    def test_symbolic_capture_directory_cannot_alias_retained_observations(self):
        target = self.graph.run / 'capture-1'
        alias = self.graph.run / 'capture-alias'
        try:
            alias.symlink_to(target, target_is_directory=True)
        except (NotImplementedError, OSError) as error:
            self.skipTest('host does not permit creation of a synthetic directory symlink: ' + str(error))
        with self.assertRaisesRegex(ValueError, 'symbolic-link'):
            audit.path_value(str(alias / 'surface.raw'))

    def test_windows_reparse_attribute_on_existing_ancestor_is_rejected(self):
        target = self.graph.run / 'capture-2'
        real_lstat = Path.lstat
        def observed_attributes(path, *args, **kwargs):
            info = real_lstat(path, *args, **kwargs)
            if path == target:
                return SimpleNamespace(st_mode=info.st_mode, st_file_attributes=0x400)
            return info
        with patch.object(Path, 'lstat', autospec=True, side_effect=observed_attributes):
            result = self.graph.evaluate()
        self.assertFalse(result['passed'])
        self.assertIn('reparse or symbolic-link artifact path', str(result['failures']))

    def test_wrong_resource_root_duplicate_json_and_numeric_alias_reject(self):
        self.graph.persist()
        result = audit.audit_summary(self.graph.run / 'summary.json', Path(self.temp.name))
        self.assertFalse(result['passed']); self.assertIn('resource-root', str(result['failures']))
        path = self.graph.run / 'summary.json'; path.write_text('{"schema":1,"schema":2}')
        self.assertIn('duplicate JSON key', str(audit.audit_summary(path, self.graph.work)['failures']))
        self.graph.plan['width'] = 800.0
        self.assertFalse(self.graph.evaluate()['passed'])


if __name__ == '__main__':
    unittest.main()
