"""Generated movement artifacts only: no game, debugger or runtime evidence.

Synthetic source/trace boundaries are mocked explicitly; all path, hash, record,
header, PNG, pixel and cleanup bindings execute normally. The trace mock rejects
any changed immutable argument, making accidental omitted binding observable.
"""
import copy
import json
from pathlib import Path
import struct
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import complete_hd_army_movement_surface_audit as audit
from test_complete_hd_army_selection_surface_audit import assets_fixture, pixel_fixture


def unit_fixture(phase):
    data = bytearray(725)
    struct.pack_into('<hh', data, 0, 18 if phase == 2 else 16, 19)
    for i, kind in enumerate((16, 16, 1, 1, 1, 1, 1, 1, -1, -1)):
        struct.pack_into('<h', data, 6 + 31 * i, kind)
        if i < 8:
            data[14 + 31 * i] = (26 if i == 0 else 22 if i == 1 else 16) - (10 if phase == 2 else 0)
            data[15 + 31 * i] = 100
            data[19 + 31 * i] = 2 if phase == 2 else 0  # Spent-turn bit is not status badge bit4.
    if phase == 1:
        struct.pack_into('<iII', data, 316, 2, 0x000A1312, 0x00051311)
    data[5] = phase  # Native facing may change independently of portrait inputs.
    return bytes(data)


class MovementGraph:
    """Explicit movement-host graph, without converting any selection summary."""
    def __init__(self, root):
        self.root = root; self.run = root / 'capture'; self.run.mkdir()
        self.work = root / 'work'; (self.work / 'DATA').mkdir(parents=True); (self.work / 'save').mkdir()
        self.assets = assets_fixture(); self.layout = audit.FramedArmyViewport(800, 600)
        self.raws = {}
        for index, name in enumerate(audit.CHECKPOINTS):
            raw = bytearray(pixel_fixture(self.layout, self.assets))
            raw[200 * 800 + 300] = 10 + index  # Expected map change outside audited chrome.
            self.raws[name] = bytes(raw)
        self.units = {name: unit_fixture(i) for i, name in enumerate(audit.CHECKPOINTS)}
        p = self.plan = dict(schema=audit.PLAN_SCHEMA, stage=audit.bar.COMPLETE_HD_STAGE,
                            resolution='800x600', width=800, height=600, out_dir=str(self.run), work_dir=str(self.work),
                            environment='hidden_cdb_host', child_environment={'CLASH_PROXY_PRESENT':'0', 'parent_environment_modified':False},
                            **{name:False for name in audit.FALSE_FLAGS})
        for key in ('original', 'input_candidate', 'candidate_path', 'proxy_input', 'proxy_path', 'cdb', 'python'):
            path = root / (key + '.fixture')
            path.write_bytes(b'synthetic ' + (b'candidate' if 'candidate' in key else b'proxy' if 'proxy' in key else key.encode()))
            p[key] = str(path)
        for key, relative in (('host_path','scripts/cdb/run_complete_hd_army_movement_capture.ps1'),
                              ('producer','tools/complete_hd_army_movement_probe.py'), ('trace','tools/complete_hd_army_movement_trace.py'),
                              ('converter','tools/cdb_surface_dump_to_png.py'), ('proxy_source','src/ddraw_surfdump_proxy/ddraw_surfdump_proxy.cpp')):
            p[key] = str((audit.ROOT / relative).resolve())
        self.write(self.work / 'save/0.dat', b'synthetic save'); p['save'] = str(self.work / 'save/0.dat')
        self.write(self.work / 'DATA/minimum.res', b'synthetic minimum'); self.write(self.work / 'DATA/GFX3.RES', b'synthetic gfx3')
        p['assets_before'] = {path.relative_to(self.work).as_posix():audit.sha(path.read_bytes()) for path in self.work.rglob('*') if path.is_file()}
        manifest = root / 'candidate.json'; self.manifest = {'synthetic_manifest':True}; self.json(manifest, self.manifest)
        p['candidate_manifest'] = str(manifest)
        p['candidate_manifest_canonical_sha256'] = audit.sha(audit.canonical(self.manifest).encode())
        for key, role in (('original_sha256','original'), ('candidate_sha256','candidate_path'), ('save_sha256','save'),
                          ('proxy_sha256','proxy_path'), ('proxy_source_sha256','proxy_source')):
            p[key] = audit.sha(Path(p[role]).read_bytes())
        proxy_manifest = root / 'proxy-manifest.json'
        self.json(proxy_manifest, dict(generated_by='clash-hd-surface-dump-proxy', source=p['proxy_source'], output=p['proxy_input'],
                                      source_sha256=p['proxy_source_sha256'].upper(), output_sha256=p['proxy_sha256'].upper()))
        p['proxy_manifest'] = str(proxy_manifest); p['proxy_manifest_sha256'] = audit.sha(proxy_manifest.read_bytes())
        self.probe = b'synthetic movement main\n'; p['probe_sha256'] = audit.sha(self.probe)
        self.packet = dict(stage=p['stage'], resolution=p['resolution'], capture_dir=self.run.as_posix(), supplemental_commands={})
        self.commands = {}
        p['supplemental_commands'] = []
        for i in range(3):
            packet_path = f'{self.run.as_posix()}/movement-checkpoint-{i}.cdb'
            data = f'synthetic quiet checkpoint {i}\n'.encode(); self.commands[packet_path] = data
            path = self.run / f'movement-checkpoint-{i}.cdb'; self.write(path, data)
            self.packet['supplemental_commands'][packet_path] = {'synthetic_command':True}
            p['supplemental_commands'].append(self.receipt(path) | dict(packet_path=packet_path, checkpoint=i))
        self.json(self.run / 'packet.json', self.packet); self.write(self.run / 'complete-hd-army-movement.cdb', self.probe)
        roles = ('original','input_candidate','save','candidate_manifest','host_path','producer','trace','converter','cdb','python',
                 'proxy_input','proxy_source','proxy_manifest')
        p['identities'] = [self.receipt(Path(p[key])) for key in roles]
        self.write(self.run / 'host.ps1', Path(p['host_path']).read_bytes())
        cdb = dict(path=p['cdb'], process_id=101, creation_filetime=1010, handle_retained=True)
        game = dict(path=p['candidate_path'], process_id=102, creation_filetime=1020, handle_retained=True,
                    parent_process_id=101, candidate_sha256=p['candidate_sha256'])
        header = bytearray(188); struct.pack_into('<HHI', header, 0, 800, 600, 0x300000); struct.pack_into('<I', header, 184, 0x50ee24)
        self.header = bytes(header)
        self.surfaces = [dict(checkpoint=i, surface=0x210000, base=0x300000, width=800, height=600, vtable=0x50ee24,
                              **{k:v for k,v in row.items() if k != 'checkpoint'}) for i,row in enumerate(audit.trace.snapshot_paths(self.packet))]
        prefix = b'synthetic native movement observed\n'; final = prefix + b'synthetic debugger cleanup\n'
        self.write(self.run / 'capture-prefix.log', prefix); self.write(self.run / 'cdb.log', final)
        self.fresh = dict(passed=True, ready_for_host_capture=True, source_authenticated=True, whole_candidate_bound=True,
                          candidate_manifest_bound=True, all_supplemental_commands_bound=True, snapshot_headers_verified=True,
                          snapshot_units_verified=True, sequence_only=False, initial_log_projected=False, movement_state={'passed':True},
                          movement_sequence={'synthetic_sequence':True, 'ready':{'unit':0x400000}},
                          surface=self.surfaces[-1], snapshots=self.surfaces, failures=[],
                          source=dict(original_sha256=p['original_sha256'], candidate_sha256=p['candidate_sha256'], save_sha256=p['save_sha256'],
                                      probe_raw_sha256=p['probe_sha256'], candidate_manifest_canonical_sha256=p['candidate_manifest_canonical_sha256'],
                                      source_sha256={}, supplemental_commands={}, snapshot_headers=[], snapshot_units=[]))
        self.summary = dict(schema=audit.HOST_SCHEMA, passed=True, executed=True, cleanup_verified=True, clean_stable_pair=True,
                            source_and_input_identities_unchanged=True, status='bounded_hidden_complete_hd_army_movement_capture', failures=[], plan=p,
                            checkpoint_palette_scope=audit.PALETTE_SCOPE,
                            frame_verified=False, action_bar_verified=False, **{name:False for name in audit.FALSE_FLAGS},
                            packet=self.receipt(self.run / 'packet.json'), probe=self.receipt(self.run / 'complete-hd-army-movement.cdb'),
                            supplemental_commands=copy.deepcopy(p['supplemental_commands']), capture_prefix=self.receipt(self.run / 'capture-prefix.log'),
                            final_trace_attempted=True,
                            final_log=self.receipt(self.run / 'cdb.log') | dict(capture_prefix_preserved=True,unchanged_during_final_validation=True,
                                                                            validator_log_identity_matched=True), cdb=cdb, candidates=[game],
                            assets_after=copy.deepcopy(p['assets_before']), checkpoints=[], snapshots=[],
                            cleanup=dict(cdb=dict(identity=cdb, absent=True, handle_closed=True),
                                         candidates=[dict(identity=game, absent=True, handle_closed=True)], desktop_closed=True))
        for i, name in enumerate(audit.CHECKPOINTS):
            row = dict(checkpoint=i, name=name, surface=self.surfaces[i])
            for kind, suffix, data in (('raw','.raw',self.raws[name]), ('header','.header.raw',self.header), ('unit','.unit.raw',self.units[name])):
                path = self.run / (name + suffix); self.write(path, data); row[kind] = self.receipt(path)
            self.summary['checkpoints'].append(row)
        for label in audit.FINALS:
            folder = self.run / label; folder.mkdir(); self.write(folder / 'surface.raw', self.raws['movement-after'])
            row = self.receipt(folder / 'surface.raw') | dict(width=800, height=600, pitch=800, pixel_reads=1, header_reads=2, e0_reads=2, unit_reads=2,
                                                            paused=True, capture='e0_software_diagnostic', game_identity=game, surface=0x210000,
                                                            base=0x300000, unit_address=0x400000, unit_sha256=audit.sha(self.units['movement-after']), reads={})
            for phase in ('before','after'):
                row['reads'][phase] = {}
                for name, data, address in (('e0',struct.pack('<I',0x210000),0x5202e0), ('header',self.header,0x210000),
                                             ('unit',self.units['movement-after'],0x400000)):
                    path = folder / f'surface-{phase}-{name}.raw'; self.write(path, data)
                    row['reads'][phase][name] = self.receipt(path) | {'address':address}
            self.summary['snapshots'].append(row)
        self.summary['snapshot'] = self.summary['snapshots'][0]
        palette = root / 'palette.fixture'; self.write(palette, bytes(v for i in range(256) for v in (i,(i*3)%256,(i*7)%256,0)))
        p['palette_path'] = str(palette); self.summary['palette'] = self.receipt(palette)
        for name in audit.CHECKPOINTS: self.refresh_checkpoint_png(name)
        self.write(self.run / 'surface.raw', self.raws['movement-after'])
        self.summary['png'] = self.convert('surface')
        self.expected_inputs = dict(original=Path(p['original']).read_bytes(), candidate=Path(p['candidate_path']).read_bytes(),
                                    save=Path(p['save']).read_bytes(), candidate_manifest=self.manifest, generated_probe=self.probe,
                                    supplemental_commands=copy.deepcopy(self.commands),
                                    snapshot_headers={row['header_path']:self.header for row in self.surfaces},
                                    snapshot_units={row['unit_path']:self.units[name] for row,name in zip(self.surfaces,audit.CHECKPOINTS)})
        self.refresh_traces(); self.persist()

    @staticmethod
    def write(path,data): path.write_bytes(data)
    @staticmethod
    def json(path,value): path.write_text(json.dumps(value),encoding='utf-8')
    @staticmethod
    def receipt(path): return dict(path=str(path),sha256=audit.sha(path.read_bytes()),bytes=path.stat().st_size)
    def convert(self,name):
        return audit.png.convert(self.run / f'{name}.raw',self.run / f'{name}.png',800,600,800,self.run / f'{name}.png.json',
                                 self.run / 'capture-prefix.log',Path(self.plan['palette_path']))
    def refresh_checkpoint_png(self,name):
        row = self.summary['checkpoints'][audit.CHECKPOINTS.index(name)]
        row['raw'] = self.receipt(self.run / f'{name}.raw'); row['png'] = self.convert(name)
    def refresh_traces(self):
        for name,log in (('trace','capture-prefix.log'),('final_trace','cdb.log')):
            value = copy.deepcopy(self.fresh); value['source']['log_raw_sha256'] = audit.sha((self.run / log).read_bytes())
            self.summary[name] = value; self.json(self.run / ('trace.json' if name == 'trace' else 'trace-final.json'),value)
    def persist(self):
        self.plan = self.summary['plan']; self.json(self.run / 'plan.json',self.plan); self.json(self.run / 'summary.json',self.summary)
    def bound(self,log,packet,**inputs):
        result = copy.deepcopy(self.fresh)
        if audit.canonical(packet) != audit.canonical(self.packet) or inputs != self.expected_inputs:
            result['passed'] = False; result['failures'] = ['synthetic full-source boundary rejected changed immutable arguments']
        return result
    def evaluate(self):
        self.persist()
        with patch.object(audit.selection,'load_assets',return_value=self.assets), \
             patch.object(audit,'verify_native_panel_contract',return_value=[{'synthetic_native_contract':True}]), \
             patch.object(audit.trace,'evaluate_bound_capture',side_effect=self.bound), \
             patch.object(audit.trace,'evaluate_trace',return_value={'passed':True,'movement_sequence':self.fresh['movement_sequence']}):
            return audit.audit_summary(self.run / 'summary.json',self.work)


class PanelTests(unittest.TestCase):
    def test_ap_spending_and_path_changes_do_not_change_number_or_status_inputs(self):
        self.assertEqual(audit.panel_inputs(unit_fixture(0)),audit.panel_inputs(unit_fixture(2)))
        self.assertEqual(audit.panel_inputs(unit_fixture(1)),audit.panel_inputs(unit_fixture(2)))
        record = bytearray(unit_fixture(2)); record[19] |= 4
        self.assertNotEqual(audit.panel_inputs(bytes(record)),audit.panel_inputs(unit_fixture(0)))
        for value in (b'x',bytearray(unit_fixture(0)),None):
            with self.assertRaises(ValueError): audit.panel_inputs(value)

    def test_native_instruction_contract_rejects_changed_field_or_badge(self):
        data = bytearray(0x100); data[0x6b:0x70] = bytes.fromhex('0fbe44020f'); data[7:12] = bytes.fromhex('f644021304')
        with patch.object(audit,'file_offset',side_effect=lambda data,va,size:va-0x423600):
            self.assertEqual(len(audit.verify_native_panel_contract(bytes(data))),2)
            for offset in (0x6f,11):
                broken = bytearray(data); broken[offset] ^= 1
                with self.assertRaisesRegex(ValueError,'native portrait'): audit.verify_native_panel_contract(bytes(broken))


class ArtifactTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.graph = MovementGraph(Path(self.temp.name))
    def test_complete_graph_checks_six_observations_and_four_pngs(self):
        result = self.graph.evaluate(); self.assertTrue(result['passed'],result['failures'])
        self.assertEqual(set(result['captures']),set(audit.LABELS)); self.assertEqual(len(result['screenshots']),4)
        self.assertTrue(result['complete_backing']['passed']); self.assertEqual(result['complete_backing']['checked_pixels_per_capture'],25542)
        self.assertTrue(result['unit_records_verified'])
        for name in audit.CHECKPOINTS: self.assertIn('final proxy palette',result['screenshots'][name]['palette_scope'])
        for key in (*audit.FALSE_FLAGS,'runtime_accepted','count_text_verified','map_unit_artwork_verified','cleanup_observed_by_this_audit'):
            self.assertIs(result[key],False)
    def test_all_supplemental_commands_are_required_even_with_rehashed_receipts(self):
        for i in range(3):
            path = self.graph.run / f'movement-checkpoint-{i}.cdb'; original = path.read_bytes(); path.write_bytes(original+b'changed')
            row = self.graph.plan['supplemental_commands'][i]; row.update(self.graph.receipt(path))
            self.graph.summary['supplemental_commands'] = copy.deepcopy(self.graph.plan['supplemental_commands'])
            result = self.graph.evaluate(); self.assertFalse(result['passed']); self.assertIn('immutable arguments',str(result['failures']))
            path.write_bytes(original); row.update(self.graph.receipt(path)); self.graph.summary['supplemental_commands']=copy.deepcopy(self.graph.plan['supplemental_commands'])
        path.unlink(); self.assertFalse(self.graph.evaluate()['passed'])
    def test_each_checkpoint_header_and_unit_is_bound_to_trace(self):
        for row in self.graph.summary['checkpoints']:
            for key in ('header','unit'):
                path = Path(row[key]['path']); original = path.read_bytes(); data = bytearray(original); data[20] ^= 1; path.write_bytes(data)
                row[key] = self.graph.receipt(path)
                result=self.graph.evaluate(); self.assertFalse(result['passed']); self.assertIn('immutable arguments',str(result['failures']))
                path.write_bytes(original); row[key]=self.graph.receipt(path)
    def test_main_command_cannot_be_replaced_with_new_plan_receipts(self):
        path=self.graph.run/'complete-hd-army-movement.cdb'; path.write_bytes(path.read_bytes()+b'changed')
        self.graph.summary['probe']=self.graph.receipt(path); self.graph.plan['probe_sha256']=audit.sha(path.read_bytes())
        result=self.graph.evaluate(); self.assertFalse(result['passed']); self.assertIn('immutable arguments',str(result['failures']))
    def test_missing_truncated_checkpoint_and_missing_final_fail(self):
        path=self.graph.run/'movement-preview.raw'; original=path.read_bytes(); path.write_bytes(original[:-1])
        self.graph.summary['checkpoints'][1]['raw']=self.graph.receipt(path)
        self.assertFalse(self.graph.evaluate()['passed']); path.unlink(); self.assertFalse(self.graph.evaluate()['passed'])
        path.write_bytes(original); self.graph.summary['checkpoints'][1]['raw']=self.graph.receipt(path)
        (self.graph.run/'capture-3/surface-after-unit.raw').unlink(); self.assertFalse(self.graph.evaluate()['passed'])
    def test_intermediate_frame_action_body_and_backing_failure_cannot_hide(self):
        points=[(0,0),(799,200),(0,200),(40,599),(235,585),(418,583)]
        points += [(r.left+2,r.top+2) for r in self.graph.layout.framed.action_cells]
        points += [(self.graph.layout.portrait(i).left+5,self.graph.layout.portrait(i).top+21) for i in range(8)]
        path=self.graph.run/'movement-preview.raw'; original=path.read_bytes()
        for x,y in points:
            data=bytearray(original); data[y*800+x]^=1; path.write_bytes(data); self.graph.refresh_checkpoint_png('movement-preview')
            result=self.graph.evaluate(); self.assertFalse(result['passed'],(x,y))
            self.assertIn('movement-preview',result['captures'],(x,y,result['failures']))
            self.assertFalse(result['captures']['movement-preview']['passed'])
            self.assertTrue(result['captures']['capture-1']['passed'])
        path.write_bytes(original)
    def test_full_backing_count_region_drift_fails_without_glyph_claim(self):
        path=self.graph.run/'movement-before.raw'; raw=bytearray(path.read_bytes()); rect=self.graph.layout.portrait(7)
        raw[(rect.top+53)*800+rect.left+10]^=1; path.write_bytes(raw); self.graph.refresh_checkpoint_png('movement-before')
        result=self.graph.evaluate(); self.assertFalse(result['passed']); self.assertTrue(result['captures']['movement-before']['passed'])
        self.assertFalse(result['complete_backing']['passed']); self.assertIs(result['count_text_verified'],False)
    def test_health_or_status_change_blocks_backing_stability_even_with_same_pixels(self):
        raws={name:self.graph.raws['movement-after'] for name in audit.LABELS}
        for offset,delta in ((15,1),(19,4)):
            units=copy.deepcopy(self.graph.units); data=bytearray(units['movement-after']); data[offset]^=delta; units['movement-after']=bytes(data)
            result=audit.audit_panel_stability(raws,units,self.graph.layout)
            self.assertFalse(result['passed']); self.assertTrue(result['complete_backing_unchanged']); self.assertFalse(result['panel_inputs_unchanged'])
    def test_whole_final_header_must_equal_movement_after(self):
        for row in self.graph.summary['snapshots']:
            for phase in ('before','after'):
                receipt=row['reads'][phase]['header']; path=Path(receipt['path']); data=bytearray(path.read_bytes()); data[100]^=1
                path.write_bytes(data); receipt.update(self.graph.receipt(path))
        result=self.graph.evaluate(); self.assertFalse(result['passed']); self.assertIn('complete surface header changed',str(result['failures']))
    def test_final_unit_and_final_pixel_comparisons_cannot_be_rehashed_away(self):
        row=self.graph.summary['snapshots'][2]; path=Path(row['reads']['before']['unit']['path']); original=path.read_bytes()
        path.write_bytes(original[:-1]+bytes([original[-1]^1])); row['reads']['before']['unit'].update(self.graph.receipt(path))
        result=self.graph.evaluate(); self.assertFalse(result['passed']); self.assertIn('final unit record changed',str(result['failures']))
        path.write_bytes(original); row['reads']['before']['unit'].update(self.graph.receipt(path))
        path=Path(row['path']); data=bytearray(path.read_bytes()); data[200*800+300]^=1; path.write_bytes(data); row.update(self.graph.receipt(path))
        result=self.graph.evaluate(); self.assertFalse(result['passed']); self.assertIn('final stopped pixels differ',str(result['failures']))
    def test_unrelated_png_and_wrong_palette_provenance_fail_after_rehash(self):
        metadata=self.graph.summary['checkpoints'][0]['png']; path=self.graph.run/'movement-before.png'; original=path.read_bytes()
        path.write_bytes(b'unrelated png'); metadata['png_sha256']=audit.sha(path.read_bytes()); self.graph.json(self.graph.run/'movement-before.png.json',metadata)
        result=self.graph.evaluate(); self.assertFalse(result['passed']); self.assertIn('does not encode',str(result['failures']))
        path.write_bytes(original); self.graph.refresh_checkpoint_png('movement-before')
        metadata=self.graph.summary['checkpoints'][0]['png']; metadata['palette_path']=self.graph.plan['original']
        self.graph.json(self.graph.run/'movement-before.png.json',metadata)
        result=self.graph.evaluate(); self.assertFalse(result['passed']); self.assertIn('PNG path differs: palette_path',str(result['failures']))
    def test_source_and_inventory_drift_fail(self):
        path=Path(self.graph.plan['python']); original=path.read_bytes(); path.write_bytes(b'drift')
        self.assertFalse(self.graph.evaluate()['passed']); path.write_bytes(original)
        (self.graph.work/'added.fixture').write_bytes(b'unplanned'); result=self.graph.evaluate()
        self.assertFalse(result['passed']); self.assertIn('inventory changed',str(result['failures']))
    def test_host_null_numeric_alias_excessive_claim_and_cleanup_fail(self):
        original=copy.deepcopy(self.graph.summary)
        mutations=[lambda s:s.update(passed=None),lambda s:s.update(executed=1),lambda s:s.update(clean_stable_pair=False),
                   lambda s:s.update(manual_input_proof=True),lambda s:s.update(frame_verified=True),lambda s:s.update(count_text_verified=True),
                   lambda s:s.update(checkpoint_palette_scope='independently observed palette at every checkpoint'),
                   lambda s:s.update(final_trace_attempted=None),lambda s:s['final_log'].update(validator_log_identity_matched=1),
                   lambda s:s['final_log'].update(unchanged_during_final_validation=False),
                   lambda s:s['plan']['child_environment'].update(parent_environment_modified=0),
                   lambda s:s['snapshots'][2].update(unit_reads=True),lambda s:s['snapshots'][2].update(unit_address=1),
                   lambda s:s['cleanup']['candidates'][0].update(absent=False),lambda s:s['candidates'][0].update(parent_process_id=101.0),
                   lambda s:s['checkpoints'][0].update(checkpoint=False),lambda s:s['snapshots'].pop()]
        for mutate in mutations:
            self.graph.summary=copy.deepcopy(original); mutate(self.graph.summary); self.assertFalse(self.graph.evaluate()['passed'])
    def test_artifact_drift_clears_authority_preserves_measured_diagnostics(self):
        original=audit.selection.audit_pixels; calls=0
        def after_pixels(*args):
            nonlocal calls
            result=original(*args); calls+=1
            if calls==6:
                path=self.graph.run/'surface.png'; path.write_bytes(path.read_bytes()+b'drift after verification')
            return result
        with patch.object(audit.selection,'audit_pixels',side_effect=after_pixels): result=self.graph.evaluate()
        self.assertIn('artifact changed during audit',str(result['failures']))
        for key in ('passed','source_authenticated','unit_records_verified','pixels_verified','cleanup_receipts_verified','ready_for_bounded_movement_review'):
            self.assertIs(result[key],False)
        self.assertEqual(len(result['captures']),6); self.assertTrue(all(row['passed'] for row in result['captures'].values()))
    def test_reparse_ancestor_cannot_reuse_an_observation(self):
        target=self.graph.run/'capture-2'; original=Path.lstat
        def attributes(path,*args,**kwargs):
            info=original(path,*args,**kwargs)
            return SimpleNamespace(st_mode=info.st_mode,st_file_attributes=0x400) if path==target else info
        with patch.object(Path,'lstat',autospec=True,side_effect=attributes): result=self.graph.evaluate()
        self.assertFalse(result['passed']); self.assertIn('reparse or symbolic-link',str(result['failures']))
    def test_bad_asset_oracle_is_not_accepted_by_production(self):
        self.graph.persist()
        with self.assertRaises(ValueError): audit.selection.load_assets(b'synthetic',b'synthetic')
        result=audit.audit_summary(self.graph.run/'summary.json',self.graph.work)
        self.assertFalse(result['passed']); self.assertFalse(result['source_authenticated'])


if __name__=='__main__': unittest.main()
