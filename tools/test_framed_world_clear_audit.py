#!/usr/bin/env python3
"""Synthetic clearing pixels and context stand-ins; no game or CDB execution."""
from __future__ import annotations

import copy
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import framed_world_clear_audit as audit


def set_rect(surface,layout,rect,value):
    for y in range(rect.top,rect.bottom+1):
        surface[y*layout.width+rect.left:y*layout.width+rect.right+1]=bytes([value])*rect.width


def pair_for(view):
    layout=view.layout
    before=bytearray([7])*(layout.width*layout.height);after=bytearray(before)
    for cell in view.cells():
        if not cell.in_world:set_rect(after,layout,cell.rect,audit.CLEAR_INDEX)
    return before,after,bytearray([255])*audit.VISIBILITY_BYTES


class PixelOracleTests(unittest.TestCase):
    def test_framed_presets_and_802_partial_right_bottom_and_corner(self):
        covered=set()
        for width,height in ((800,600),(1024,768),(1280,720),(1366,768),(1600,900),(1920,1080),(802,602)):
            with self.subTest(resolution=(width,height)):
                layout=audit.geometry.FramedViewport(width,height)
                fitting=layout.world_view(100,100)
                view=layout.world_view(100,100,*fitting.max_scroll)
                result=audit.audit_pixels(*(bytes(v) for v in pair_for(view)),view)
                self.assertTrue(result['pixel_contract_passed'],result['failures'])
                self.assertEqual(result['nonclear_pixels_remaining'],0)
                self.assertEqual(result['unchanged_nonclear_pixels'],0)
                self.assertGreater(result['changed_to_clear_pixels'],0)
                self.assertTrue(view.native_full_loop_safe)
                for row in result['cells']:
                    if not row['in_world']:
                        self.assertTrue(row['partial']);covered.add(tuple(v>=100 for v in row['world']))
                        self.assertEqual(row['changed_to_clear_pixels'],row['pixels'])
                        rect=row['rectangle']
                        self.assertGreaterEqual(rect[0],32);self.assertGreaterEqual(rect[1],16)
                        self.assertLessEqual(rect[2],width-33);self.assertLessEqual(rect[3],height-17)
        self.assertEqual(covered,{(True,False),(False,True),(True,True)})

    def test_world_smaller_than_viewport_requires_full_and_partial_clear_cells(self):
        layout=audit.geometry.FramedViewport(802,602)
        for world in ((1,1),(3,2),(layout.full_tiles[0]-1,layout.full_tiles[1]-1)):
            view=layout.world_view(*world)
            result=audit.audit_pixels(*(bytes(v) for v in pair_for(view)),view)
            self.assertTrue(result['pixel_contract_passed'],result['failures'])
            self.assertFalse(view.native_full_loop_safe)
            self.assertGreater(result['outside_world_full_cells'],0)
            self.assertGreater(result['outside_world_partial_cells'],0)
            self.assertFalse(result['runtime_acceptance']);self.assertFalse(result['release_eligible'])

    def test_literal_zero_is_not_the_source_clear_index(self):
        layout=audit.geometry.FramedViewport(800,600);view=layout.world_view(3,2)
        before,after,visibility=pair_for(view)
        for cell in view.cells():
            if not cell.in_world:set_rect(after,layout,cell.rect,0)
        result=audit.audit_pixels(bytes(before),bytes(after),bytes(visibility),view)
        self.assertFalse(result['pixel_contract_passed'])
        self.assertGreater(result['nonclear_pixels_remaining'],0)
        self.assertEqual(result['changed_to_clear_pixels'],0)
        self.assertEqual(result['clear_index'],1)

    def test_stale_and_other_nonclear_pixels_have_separate_failure_counts(self):
        view=audit.geometry.FramedViewport(800,600).world_view(3,2)
        before,after,visibility=pair_for(view)
        cell=next(cell for cell in view.cells() if not cell.in_world)
        offset=cell.rect.top*view.layout.width+cell.rect.left
        after[offset]=before[offset];after[offset+1]=9
        result=audit.audit_pixels(bytes(before),bytes(after),bytes(visibility),view)
        self.assertFalse(result['pixel_contract_passed'])
        self.assertEqual(result['nonclear_pixels_remaining'],2)
        self.assertEqual(result['unchanged_nonclear_pixels'],1)
        self.assertEqual(len(result['failures']),2)

    def test_every_outside_world_cell_requires_actual_transition_witness(self):
        view=audit.geometry.FramedViewport(800,600).world_view(3,2)
        before,after,visibility=pair_for(view)
        cell=next(cell for cell in view.cells() if not cell.in_world)
        set_rect(before,view.layout,cell.rect,1)
        result=audit.audit_pixels(bytes(before),bytes(after),bytes(visibility),view)
        self.assertFalse(result['pixel_contract_passed'])
        self.assertEqual(result['nonclear_pixels_remaining'],0)
        self.assertEqual(result['unwitnessed_outside_world_cells'],[f'r{cell.row}c{cell.column}'])
        unchanged=audit.audit_pixels(bytes(after),bytes(after),bytes(visibility),view)
        self.assertFalse(unchanged['pixel_contract_passed']);self.assertEqual(unchanged['changed_to_clear_pixels'],0)

    def test_visible_blanks_require_exact_bitmap_bit_with_no_old_visibility(self):
        view=audit.geometry.FramedViewport(800,600).world_view(100,100,89,92)
        before,after,visibility=pair_for(view);cell=view.cell(0,0)
        for value in (0,1):
            set_rect(after,view.layout,cell.rect,value)
            result=audit.audit_pixels(bytes(before),bytes(after),bytes(visibility),view)
            self.assertFalse(result['pixel_contract_passed'])
            self.assertEqual(result['unexplained_visible_blank_cells'],['r0c0'])
        offset=cell.world_x*13+(cell.world_y>>3)
        visibility[offset]&=255^(1<<(cell.world_y&7))
        result=audit.audit_pixels(bytes(before),bytes(after),bytes(visibility),view)
        self.assertTrue(result['pixel_contract_passed'],result['failures'])
        self.assertEqual(result['zero_visibility_blank_cells'],['r0c0'])
        visibility[offset]|=1<<(cell.world_y&7)
        self.assertFalse(audit.audit_pixels(bytes(before),bytes(after),bytes(visibility),view)['pixel_contract_passed'])

    def test_border_damage_wrong_lengths_missing_cells_and_invalid_geometry_fail(self):
        view=audit.geometry.FramedViewport(800,600).world_view(3,2)
        before,after,visibility=pair_for(view);after[0]=9
        result=audit.audit_pixels(bytes(before),bytes(after),bytes(visibility),view)
        self.assertFalse(result['pixel_contract_passed']);self.assertEqual(result['border_changed_pixels'],1)
        for values in ((before[:-1],after,visibility),(before,after,visibility[:-1])):
            with self.assertRaises(ValueError):audit.audit_pixels(*(bytes(v) for v in values),view)
        with self.assertRaises(ValueError):view.layout.world_view(3,2,1,0)
        with self.assertRaises(ValueError):view.layout.world_view(True,2)
        full=view.layout.world_view(100,100)
        no_clear=audit.audit_pixels(*(bytes(v) for v in pair_for(full)),full)
        self.assertFalse(no_clear['pixel_contract_passed']);self.assertIn('no outside-world',no_clear['failures'][0])


class BoundArtifactTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).resolve();self.pair=self.root/'pair.json'
        self.manifest=self.root/'synthetic.candidate.json';self.original=self.root/'synthetic-original.bin'
        self.original.write_bytes(b'explicit synthetic original, not game material')
        # Only the proprietary candidate reconstruction is replaced. Actual
        # clear instruction parsing, source hashes, geometry and raw checks run.
        candidate=bytes.fromhex('8b45fc8b55f08b4de88b5dec556a01ff75e4e8')+b'\0'*4
        self.metadata=dict(stage=audit.complete_context.complete.STAGE,resolution='800x600',
            candidate_sha256=audit.sha(candidate),base_sha256=audit.sha(self.original.read_bytes()),
            recipe_revision='synthetic-context-stand-in',probe_sha256='a'*64,
            source_hashes={Path(module.__file__).resolve().relative_to(audit.ROOT).as_posix():audit.sha(Path(module.__file__).read_bytes())
                           for module in (audit.geometry,audit.clipping)})
        self.manifest.write_text(json.dumps(self.metadata),encoding='utf-8')
        self.context=dict(manifest=self.metadata,candidate=candidate)
        mock=patch.object(audit.complete_context,'load_context',return_value=self.context)
        mock.start();self.addCleanup(mock.stop)
        self.view=audit.geometry.FramedViewport(800,600).world_view(3,2)
        self.data=dict(schema=audit.SCHEMA,
            candidate={key:self.metadata[key] for key in audit.IDENTITY_KEYS if key!='manifest_sha256'},
            geometry_sha256=audit.sha(Path(audit.geometry.__file__).read_bytes()),world=[3,2],scroll=[0,0],
            surface_format=audit.SURFACE_FORMAT)
        self.data['candidate']['manifest_sha256']=audit.sha(self.manifest.read_bytes())
        for name,pixels in zip(('before','after','visibility'),pair_for(self.view)):
            path=self.root/(name+'.bin');path.write_bytes(pixels);self.data[name]=audit.reference(path)
        self.write()

    def write(self):self.pair.write_text(json.dumps(self.data),encoding='utf-8')
    def evaluate(self):return audit.build_report(self.pair,self.manifest,self.original)

    def test_exact_declared_artifacts_pass_only_pixel_contract_and_are_unchanged(self):
        before={p.name:p.read_bytes() for p in self.root.iterdir()}
        result=self.evaluate()
        self.assertTrue(result['pixel_contract_passed'],result['failures'])
        self.assertFalse(result['runtime_acceptance']);self.assertFalse(result['release_eligible'])
        self.assertFalse(result['native_capture_recipe_available'])
        self.assertFalse(result['complete_candidate_small_world_supported'])
        self.assertFalse(result['geometry']['native_full_loop_safe'])
        self.assertEqual(result['observation_authenticity'],'unverified_declared_pair')
        self.assertEqual(before,{p.name:p.read_bytes() for p in self.root.iterdir()})

    def test_mixed_candidate_cross_resolution_recipe_hashes_booleans_masks_and_aliases_fail(self):
        good=copy.deepcopy(self.data)
        mutations=[lambda d:d['candidate'].update(candidate_sha256='b'*64),
            lambda d:d['candidate'].update(resolution='1024x768'),lambda d:d['candidate'].update(stage='other'),
            lambda d:d['candidate'].update(recipe_revision='other'),lambda d:d['candidate'].update(probe_sha256='b'*64),
            lambda d:d['candidate'].update(manifest_sha256='b'*64),lambda d:d.update(geometry_sha256='b'*64),
            lambda d:d['after'].update(sha256='b'*64),lambda d:d.update(after=d['before']),
            lambda d:d.update(passed=True),lambda d:d.update(masks=[]),
            lambda d:d.update(surface_format='composed-primary'),lambda d:d.update(world=[True,2]),
            lambda d:d.update(scroll=[1,0]),lambda d:d.update(world=[3,2,4])]
        for mutate in mutations:
            self.data=copy.deepcopy(good);mutate(self.data);self.write()
            result=self.evaluate();self.assertFalse(result['pixel_contract_passed'],mutate)
            self.assertFalse(result['runtime_acceptance']);self.assertTrue(result['failures'])

    def test_rehashed_raw_mutation_and_wrong_native_clear_call_fail(self):
        path=Path(self.data['after']['path']);data=bytearray(path.read_bytes())
        cell=next(c for c in self.view.cells() if not c.in_world)
        data[cell.rect.top*800+cell.rect.left]=0;path.write_bytes(data)
        self.data['after']=audit.reference(path);self.write()
        result=self.evaluate();self.assertFalse(result['pixel_contract_passed'])
        self.assertEqual(result['pixel_audit']['nonclear_pixels_remaining'],1)
        for candidate in (self.context['candidate'].replace(b'\x6a\x01',b'\x6a\x00'),self.context['candidate']*2,b''):
            context=copy.deepcopy(self.context);context['candidate']=candidate
            context['manifest']['candidate_sha256']=audit.sha(candidate)
            with self.assertRaisesRegex(ValueError,'exact index-1'):audit.clear_contract(context)
        context=copy.deepcopy(self.context)
        context['manifest']['source_hashes']['src/patcher/partial_tile_clip.py']='c'*64
        with self.assertRaisesRegex(ValueError,'source differs'):audit.clear_contract(context)

    def test_manifest_changes_during_candidate_reconstruction_are_not_rebound(self):
        def changing_context(*args,**kwargs):
            self.data['candidate']['candidate_sha256']='b'*64
            self.write()
            return self.context
        with patch.object(audit.complete_context,'load_context',side_effect=changing_context):
            result=self.evaluate()
        self.assertFalse(result['pixel_contract_passed'])
        self.assertTrue(any('changed during audit' in failure for failure in result['failures']))

    def test_existing_output_is_immutable_and_failed_analysis_has_nonzero_exit(self):
        output=self.root/'result.json';output.write_bytes(b'earlier failure must remain')
        argv=['audit','--pair-manifest',str(self.pair),'--candidate-manifest',str(self.manifest),
              '--original',str(self.original),'--output',str(output)]
        with patch.object(audit.sys,'argv',argv),contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as error:audit.main()
        self.assertEqual(error.exception.code,2);self.assertEqual(output.read_bytes(),b'earlier failure must remain')
        argv[-1]=str(self.root/'new-rejected.json')
        self.data['after']['sha256']='0'*64;self.write()
        with patch.object(audit.sys,'argv',argv),contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(audit.main(),2)
        result=audit.read_json(argv[-1]);self.assertFalse(result['pixel_contract_passed'])
        self.assertFalse(result['release_eligible']);self.assertTrue(result['failures'])


if __name__=='__main__':unittest.main()
