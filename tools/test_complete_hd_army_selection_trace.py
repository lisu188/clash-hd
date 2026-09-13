"""Synthetic offline complete-HD selection tests; never runtime evidence.

Only candidate reconstruction is stubbed with explicitly synthetic bytes.
Native selection, complete loaded-contract and initial-event parsers stay real.
Actual six-resolution candidate construction belongs to the producer fixtures.
"""
from __future__ import annotations

from contextlib import contextmanager
import copy
import json
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch

import complete_hd_army_selection_trace as trace
import test_framed_army_selection_trace as legacy_fixture
import test_initial_map_paint_trace as initial_fixture

ORIGINAL = b'synthetic original; never executable'
CANDIDATE = b'synthetic complete candidate; never executable'
SAVE = b'synthetic inspected save; never gameplay data'


def manifest_fixture(resolution):
    width, height = map(int, resolution.split('x'))
    return dict(stage=trace.producer.builder.STAGE, resolution=resolution,
        candidate_sha256=trace.sha(CANDIDATE), recipe_revision=trace.producer.builder.REVISION,
        predecessor=dict(stage=trace.frozen.producer.builder.STAGE,
                         army_revision=trace.frozen.producer.builder.REVISION),
        synthetic_fixture=True, geometry=dict(width=width, height=height))


def packet_fixture(resolution='1024x768'):
    width, height = map(int, resolution.split('x'))
    manifest = manifest_fixture(resolution)
    inherited = manifest['predecessor']
    _, extra = initial_fixture.fixture(resolution=resolution, stage=trace.initial_trace.FRAMED_STAGE)
    extra = extra.replace('stage=' + trace.initial_trace.FRAMED_STAGE + ' ', 'stage=' + inherited['stage'] + ' ')
    extra = extra.replace(initial_fixture.SHA, manifest['candidate_sha256'])
    identity = f"resolution={resolution} candidate_sha256={manifest['candidate_sha256']}"
    extra = (f".echo ARMY_CONTRACT_PASS stage={inherited['stage']} {identity} revision={inherited['army_revision']}\n"
        '.echo ARMY_SCOPE own_player_0_to_3_native_size_panel manual_input_proof=false promotion_ready=false\n'
        f".echo COMPLETEHD_CONTRACT_PASS stage={manifest['stage']} {identity} revision={manifest['recipe_revision']}\n" + extra)
    compiled = '$$ SYNTHETIC FIXTURE ONLY; NOT EXECUTABLE\n' + extra
    sites = {80:0x406FA1, 81:0x408131, 82:0x408136, 83:0x406980, 84:0x40A500,
        85:0x423B00, 86:0x423420, 87:0x4080EF, 88:0x423B32, 89:0x423B3C,
        90:0x597000, 91:0x597800, 92:0x597A00}
    return dict(schema='clash95_complete_hd_army_selection_probe_v1', revision=trace.producer.REVISION,
        stage=manifest['stage'], resolution=resolution, width=width, height=height,
        original_sha256=trace.producer.clip.ORIGINAL_SHA256, candidate_sha256=manifest['candidate_sha256'],
        save_sha256=trace.producer.SAVE_SHA256, unit=3, unit_xy=[16,19],
        unit_squad_types=[16,16,1,1,1,1,1,1], controlled_scroll=[10,17], controlled_mouse=[448,176],
        native_predicate_forced=False, capture_dir='C:/ClashCaptures/synthetic-complete-selection-fixture',
        minimap_viewport=True, compiled_probe=compiled, probe_sha256=trace.sha(compiled.encode()),
        initial_extra=extra, initial_extra_sha256=trace.sha(extra.encode()),
        observer_vas={str(n):va for n,va in sites.items()},
        native_call_returns=dict(portraits=0x423B32, redraw=0x423B3C, native_draw=sites[91], composition_draw=sites[92]),
        candidate_manifest_canonical_sha256=trace.sha(trace.canonical(manifest).encode()),
        candidate_recipe=manifest['recipe_revision'], inherited_stage=inherited['stage'],
        inherited_revision=inherited['army_revision'], startup_recipe=trace.producer.compiler.provenance(),
        parent_source_sha256=trace.producer.PARENT_SOURCE_SHA256,
        source_sha256={'synthetic-fixture-only':'a'*64}, manual_input_proof=False,
        promotion_ready=False, runtime_executed=False, capture_class='e0_software_diagnostic', limits=trace.LIMITS)


def log_fixture(packet=None, *, native_status=0, compositions=1):
    packet = packet or packet_fixture()
    # Reuse frozen native record grammar, then prepend independently generated
    # initial events for the actual synthetic resolution. No runtime log is read.
    old = copy.deepcopy(packet)
    old.update(revision='controlled_own_army_native_selection_v3', stage=packet['inherited_stage'])
    native = legacy_fixture.log_fixture(old, warmup=native_status, compositions=compositions)
    native = native[native.index('PTILE_TRACE_CLOSED '):]
    native = native.replace('size=(1024,768)', f"size=({packet['width']},{packet['height']})")
    native = native.replace('width=1024 height=768', f"width={packet['width']} height={packet['height']}")
    lines = ['SHSEL_BYTES_PASS']
    lines.extend(line.removeprefix('.echo ') for line in packet['initial_extra'].splitlines() if line.startswith('.echo '))
    sites = {int(n):int(va,16) for n,va in re.findall(r'(?m)^bp(7[0-7]) ([0-9a-fA-F]{8}) ', packet['initial_extra'])}
    for sequence, event in enumerate(initial_fixture.initial_events(packet['resolution'], framed=True), 1):
        lines.append(f"PTILE_EVENT seq={sequence} bp={event['bp']} tid={initial_fixture.TID:x} eip={sites[event['bp']]:08x} esp={event['esp']:08x}")
        lines.extend(event['records'])
    return '\n'.join(lines) + '\n' + native


@contextmanager
def synthetic_binding(packet, manifest):
    """Stub only reconstruction; all sequence/initial validators remain real."""
    expected = copy.deepcopy(packet)
    expected_manifest = copy.deepcopy(manifest)
    def build(original, candidate, save, *, capture_dir, candidate_manifest, resolution):
        if (original, candidate, save, capture_dir, resolution) != (ORIGINAL, CANDIDATE, SAVE, expected['capture_dir'], expected['resolution']):
            raise ValueError('synthetic reconstruction bytes or options differ')
        if trace.canonical(candidate_manifest) != trace.canonical(expected_manifest):
            raise ValueError('synthetic manifest reconstruction differs')
        return copy.deepcopy(expected)
    def context(candidate_manifest, original, *, resolution, candidate=None, probe=None, **kwargs):
        if original != ORIGINAL or resolution != expected['resolution'] or trace.canonical(candidate_manifest) != trace.canonical(expected_manifest):
            raise ValueError('synthetic complete context differs')
        if candidate is not None and candidate != CANDIDATE or probe is not None and probe != expected['initial_extra']:
            raise ValueError('synthetic complete candidate or canonical probe differs')
        return dict(manifest=copy.deepcopy(expected_manifest), candidate=CANDIDATE,
            probe=expected['initial_extra'], inherited_stage=expected['inherited_stage'], framed={})
    with patch.object(trace.producer, 'build_selection_probe', side_effect=build) as builder, \
         patch.object(trace.runtime, 'verify_context', side_effect=context) as complete:
        yield builder, complete


class DiagnosticTests(unittest.TestCase):
    def bad(self, log, packet=None):
        result = trace.evaluate_trace(log, packet or packet_fixture())
        self.assertFalse(result['passed'], result)
        self.assertTrue(result['failures'])
        self.assertFalse(result['ready_for_host_capture'])
        return result

    def test_six_physical_geometries_preserve_native_fallback_and_composition(self):
        for resolution in trace.producer.builder.RESOLUTIONS:
            packet = packet_fixture(resolution)
            for status in (0, 1):
                for count in (1, 3):
                    with self.subTest(resolution=resolution, status=status, compositions=count):
                        result = trace.evaluate_trace(log_fixture(packet, native_status=status, compositions=count), packet)
                        self.assertTrue(result['passed'], result['failures'])
                        self.assertEqual(result['selection_sequence']['native_warmup_fallbacks'], int(status == 0))
                        self.assertEqual(result['selection_sequence']['counters']['composition'], count)
                        self.assertEqual(len(result['selection_sequence']['handoff_diagnostics']), 3)
                        self.assertIsNone(result['initial_map_trace'])
                        self.assertTrue(result['sequence_only'])
                        for key in ('source_authenticated','whole_candidate_bound','candidate_manifest_bound','ready_for_host_capture',
                                    'runtime_accepted','pixels_verified','cleanup_verified','manual_input_proof','promotion_ready'):
                            self.assertFalse(result[key], key)

    def test_every_native_record_missing_or_duplicated_is_rejected(self):
        lines = log_fixture().splitlines()
        for index, line in enumerate(lines):
            if not line.startswith(('SHSEL_', 'ARMY_')): continue
            with self.subTest(line=line):
                self.bad('\n'.join(lines[:index] + lines[index+1:]))
                self.bad('\n'.join(lines[:index] + [line] + lines[index:]))

    def test_all_three_loaded_contracts_have_exact_identity_and_order(self):
        packet = packet_fixture(); log = log_fixture(packet); lines = log.splitlines()
        markers = ('ARMY_CONTRACT_PASS', 'COMPLETEHD_CONTRACT_PASS', 'PTILE_CONTRACT_PASS')
        positions = [next(i for i,text in enumerate(lines) if text.startswith(marker)) for marker in markers]
        for index, marker in zip(positions, markers):
            line = lines[index]
            with self.subTest(marker=marker):
                self.bad('\n'.join(lines[:index] + lines[index+1:]), packet)
                self.bad('\n'.join(lines[:index] + [line] + lines[index:]), packet)
                for changed in (line.replace(packet['candidate_sha256'], 'b'*64), line.replace('stage=', 'stage=wrong-'),
                                '0:000> '+line, line.lower(), line+' extra=1'):
                    if changed != line: self.bad(log.replace(line, changed), packet)
                moved = lines.copy(); moved.pop(index); moved.append(line); self.bad('\n'.join(moved), packet)
                for content,digest in (('compiled_probe','probe_sha256'),('initial_extra','initial_extra_sha256')):
                    changed = copy.deepcopy(packet)
                    changed[content] = changed[content].replace('.echo '+line+'\n', '')
                    changed[digest] = trace.sha(changed[content].encode())
                    self.bad(log, changed)
        for first, second in zip(positions, positions[1:]):
            changed = lines.copy(); changed[first],changed[second] = changed[second],changed[first]
            self.bad('\n'.join(changed), packet)

    def test_native_abi_state_sentinels_draw_returns_and_failures(self):
        log = log_fixture()
        mutations = (
            ('world=(16,19)','world=(16,18)'), ('selected_before=-1','selected_before=3'),
            ('eax=1','eax=0'), ('caller=00406fa1','caller=00406fa0'),
            ('eip=00406fa1','eip=00406fa0'), ('vtable=0050ee24','vtable=0050ee74'),
            ('owner=0040ad40','owner=00422020'), ('width=1024','width=800'),
            ('size=(1024,768)','size=(1024,766)'), ('surface=00900000','surface=0051d4c0'),
            ('base=00a00000 width','base=00a01000 width'), ('prior=3 lower=1','prior=2 lower=1'),
            ('t14=1 t13=4','t14=0 t13=4'), ('selected=(ffffffffffffffff,-1)','selected=(ffffffffffffffff,3)'),
            ('gd=00600000','gd=00000000'), ('unit_xy=1','unit_xy=0'),
            ('selected=1 prior=1','selected=0 prior=1'), ('count=2','count=3'),
            ('esp=000fe004','esp=000fe000'), ('esp=000ff004','esp=000ff008'),
            ('route=composition tid=abc','route=composition tid=abd'), ('esp=000fe000','esp=000fe001'),
            ('caller=00597a00','caller=00597800'), ('status=0 count=1','status=2 count=1'),
            ('status=1 count=2','status=0 count=2'), ('SHSEL_BEGIN','shsel_begin'))
        for old,new in mutations:
            with self.subTest(mutation=(old,new)):
                self.assertIn(old, log); self.bad(log.replace(old,new))
        self.bad(log_fixture(compositions=0))
        for tail in ('SHSEL_REJECT native_contract','SHSEL_SELECTION_FAIL selected=-1 eax=0','COMPLETEHD_CONTRACT_FAIL bytes',
                     'MCANVAS_CONTRACT_FAIL bytes','AV_SURFDUMP c0000005','Syntax error','timeout reached',
                     'SURFDUMP_APP_REQUEST_QUIT','PTILE_REJECT offscreen','SHSEL_UNKNOWN value=1',
                     '0:000> SHSEL_HOST_READY','SURFDUMP_REDRAW tick=999'):
            self.bad(log + tail + '\n')
        lines = log.splitlines()
        for first,second in (('SHSEL_ARMY_OPEN','SHSEL_ARMY_DRAW'),
                ('SHSEL_DRAW_RETURN route=native','SHSEL_PAIRED event=before-redraw'),
                ('SHSEL_PAIRED event=after-redraw','SHSEL_READY')):
            changed=lines.copy(); a=next(i for i,v in enumerate(changed) if v.startswith(first)); b=next(i for i,v in enumerate(changed) if v.startswith(second))
            changed[a],changed[b]=changed[b],changed[a]; self.bad('\n'.join(changed))

    def test_pixel_extent_uses_each_exact_resolution(self):
        for resolution in trace.producer.builder.RESOLUTIONS:
            p=packet_fixture(resolution); log=log_fixture(p)
            maximum=0x100000000-p['width']*p['height']
            valid=log.replace('base=00a00000',f'base={maximum:08x}')
            self.assertTrue(trace.evaluate_trace(valid,p)['passed'])
            self.bad(log.replace('base=00a00000',f'base={maximum+1:08x}'),p)

    def test_packet_protocol_types_native_calls_and_claims_are_strict(self):
        p=packet_fixture(); log=log_fixture(p)
        cases=(('stage',p['inherited_stage']),('revision','controlled_own_army_native_selection_v3'),('resolution','640x480'),
            ('inherited_stage',p['stage']),('inherited_revision','wrong'),('candidate_recipe','wrong'),
            ('width',1024.0),('unit',True),('unit_xy',[16.0,19]),('controlled_scroll',[10,18]),
            ('native_predicate_forced',0),('minimap_viewport',False),('manual_input_proof',True),('runtime_executed',True),
            ('candidate_manifest_canonical_sha256','invalid'),('save_sha256','b'*64),('compiled_probe','changed'),
            ('initial_extra','changed'),('parent_source_sha256','b'*64),('source_sha256',{}),('startup_recipe',None))
        for key,value in cases:
            changed=copy.deepcopy(p); changed[key]=value; self.bad(log,changed)
        for key in p['native_call_returns']:
            changed=copy.deepcopy(p); changed['native_call_returns'][key]+=1; self.bad(log,changed)
        for key in ('80','87','88','90','91','92'):
            changed=copy.deepcopy(p); changed['observer_vas'][key]=True; self.bad(log,changed)
        self.assertFalse(trace.evaluate_trace(log,None)['passed'])


class BoundTests(unittest.TestCase):
    def setUp(self):
        # Synthetic identities are explicitly confined to this fixture context.
        self.original_pin=patch.object(trace.producer.clip,'ORIGINAL_SHA256',trace.sha(ORIGINAL))
        self.save_pin=patch.object(trace.producer,'SAVE_SHA256',trace.sha(SAVE))
        self.original_pin.start(); self.save_pin.start()
        self.addCleanup(self.original_pin.stop); self.addCleanup(self.save_pin.stop)
        self.packet=packet_fixture(); self.manifest=manifest_fixture('1024x768')

    def evaluate(self, packet=None, log=None, **changes):
        p=packet or self.packet
        args=dict(original=ORIGINAL,candidate=CANDIDATE,save=SAVE,generated_probe=p['compiled_probe'].encode(),candidate_manifest=self.manifest)
        args.update(changes)
        return trace.evaluate_bound_trace(log if log is not None else log_fixture(p),p,**args)

    def test_bound_all_six_geometries_use_unchanged_log_and_complete_context(self):
        for resolution in trace.producer.builder.RESOLUTIONS:
            p=packet_fixture(resolution); manifest=manifest_fixture(resolution); log=log_fixture(p)
            with synthetic_binding(p,manifest), patch.object(trace.initial_trace,'evaluate_trace',wraps=trace.initial_trace.evaluate_trace) as initial:
                result=self.evaluate(p,log,candidate_manifest=manifest,generated_probe=p['compiled_probe'].replace('\n','\r\n').encode())
                self.assertTrue(result['passed'],result['failures'])
                self.assertTrue(result['source_authenticated']); self.assertTrue(result['whole_candidate_bound'])
                self.assertTrue(result['candidate_manifest_bound']); self.assertTrue(result['ready_for_host_capture'])
                self.assertTrue(result['initial_map_trace']['passed']); self.assertFalse(result['sequence_only'])
                self.assertEqual(initial.call_args.args,(log,p['initial_extra']))
                self.assertEqual(initial.call_args.kwargs,dict(resolution=resolution,candidate_sha256=p['candidate_sha256'],
                    stage=p['stage'],candidate_manifest=manifest,original=ORIGINAL))
                for key in ('initial_log_projected','runtime_accepted','pixels_verified','cleanup_verified','manual_input_proof','promotion_ready'):
                    self.assertFalse(result[key],key)

    def test_wrong_bytes_or_types_fail_before_reconstruction(self):
        with synthetic_binding(self.packet,self.manifest) as (builder,context):
            for key,value in (('original',ORIGINAL+b'x'),('candidate',CANDIDATE+b'x'),('save',SAVE+b'x'),
                              ('original',bytearray(ORIGINAL)),('candidate','text'),('generated_probe',bytearray(b'x'))):
                result=self.evaluate(**{key:value}); self.assertFalse(result['passed']); self.assertFalse(result['source_authenticated'])
            builder.assert_not_called(); context.assert_not_called()

    def test_packet_manifest_command_types_and_extra_bytes_fail(self):
        with synthetic_binding(self.packet,self.manifest):
            for suffix in (b'gc\n',b'\n',b'\r',b'\xef\xbb\xbf'):
                result=self.evaluate(generated_probe=self.packet['compiled_probe'].encode()+suffix)
                self.assertFalse(result['passed']); self.assertFalse(result['ready_for_host_capture'])
            changed=copy.deepcopy(self.packet); changed['source_sha256']['extra']='f'*64
            self.assertFalse(self.evaluate(changed)['passed'])
            for value in (1024.0,True):
                manifest=copy.deepcopy(self.manifest); manifest['geometry']['width']=value
                self.assertFalse(self.evaluate(candidate_manifest=manifest)['passed'])
                changed=copy.deepcopy(self.packet); changed['candidate_manifest_canonical_sha256']=trace.sha(trace.canonical(manifest).encode())
                self.assertFalse(self.evaluate(changed,candidate_manifest=manifest)['passed'])
            changed=copy.deepcopy(self.packet); changed['startup_recipe']['runtime_executed']=0
            self.assertFalse(self.evaluate(changed)['passed'])

    def test_initial_native_failures_duplicates_and_missing_complete_contract_stay_failed(self):
        p=self.packet; log=log_fixture(p)
        with synthetic_binding(p,self.manifest):
            for old,new in (('PTILE_EVENT seq=4','PTILE_EVENT seq=3'),('PTILE_STATUS hook=full_present status=1','PTILE_STATUS hook=full_present status=0'),
                            ('PTILE_INITIAL_RETURN','PTILE_UNKNOWN'),('SHSEL_SELECTION_WRITE selected=3 eax=1','SHSEL_SELECTION_WRITE selected=3 eax=0')):
                result=self.evaluate(log=log.replace(old,new)); self.assertFalse(result['passed']); self.assertFalse(result['ready_for_host_capture'])
            failed=log.split('SHSEL_BEGIN')[0]+'SHSEL_REJECT native_contract\n'
            result=self.evaluate(log=failed); self.assertFalse(result['passed']); self.assertTrue(result['initial_map_trace']['passed'])
            for marker in ('ARMY_CONTRACT_PASS','COMPLETEHD_CONTRACT_PASS','PTILE_CONTRACT_PASS'):
                line=next(line for line in log.splitlines() if line.startswith(marker))
                for replacement in ('',line+'\n'+line,line.replace(p['candidate_sha256'],'b'*64)):
                    result=self.evaluate(log=log.replace(line,replacement)); self.assertFalse(result['passed']); self.assertFalse(result['initial_map_trace']['passed'])

    def test_source_drift_frozen_parent_and_complete_helper_failure_fail_closed(self):
        with synthetic_binding(self.packet,self.manifest):
            with patch.object(trace,'FROZEN_TRACE_SHA256','0'*64):
                self.assertFalse(self.evaluate()['passed'])
            real=trace.source_receipts(); altered=real|{'changed':'0'*64}
            with patch.object(trace,'source_receipts',side_effect=[real,altered]):
                result=self.evaluate(); self.assertFalse(result['passed']); self.assertFalse(result['source_authenticated'])
            with patch.object(trace.runtime,'verify_context',side_effect=ValueError('wrong complete bytes')):
                result=self.evaluate(); self.assertFalse(result['passed']); self.assertFalse(result['ready_for_host_capture'])

    def test_manifest_reader_rejects_duplicate_and_nonfinite_json(self):
        with tempfile.TemporaryDirectory(prefix='clash-complete-selection-json-') as folder:
            path=Path(folder)/'synthetic.json'
            for text in ('{"stage":"a","stage":"b"}','{"number":NaN}','{"number":Infinity}'):
                path.write_text(text,encoding='utf-8')
                with self.assertRaises(ValueError): trace.producer.read_manifest(path)

    def test_cyclic_and_deep_direct_packet_and_manifest_inputs_fail_before_helpers(self):
        cyclic_dict = {}; cyclic_dict['self'] = cyclic_dict
        cyclic_list = []; cyclic_list.append(cyclic_list)
        deep = None
        for _ in range(2048):
            deep = [deep]
        log = log_fixture(self.packet)
        with synthetic_binding(self.packet, self.manifest) as (builder, context):
            for label, value in (('cyclic object', cyclic_dict), ('cyclic array', cyclic_list), ('deep array', deep)):
                with self.subTest(input=label):
                    with self.assertRaises(ValueError):
                        trace.canonical(value)
                    packet = dict(self.packet, invalid_structure=value)
                    diagnostic = trace.evaluate_trace(log, packet)
                    self.assertFalse(diagnostic['passed']); self.assertTrue(diagnostic['failures'])
                    bound = self.evaluate(packet, log)
                    self.assertFalse(bound['passed']); self.assertTrue(bound['failures'])
                    self.assertFalse(bound['source_authenticated']); self.assertFalse(bound['ready_for_host_capture'])
                    manifest = dict(self.manifest, invalid_structure=value)
                    bound = self.evaluate(log=log, candidate_manifest=manifest)
                    self.assertFalse(bound['passed']); self.assertTrue(bound['failures'])
                    self.assertFalse(bound['source_authenticated']); self.assertFalse(bound['ready_for_host_capture'])
            builder.assert_not_called(); context.assert_not_called()


REAL_ORIGINAL = Path('C:/Clash/clash95.exe')
REAL_SAVE = Path('C:/Clash/save/0.dat')
REAL_DIRECTORY = Path('C:/ClashTests/completehd-validation-20260908/prepared-1024x768')
REAL_CANDIDATE = REAL_DIRECTORY / 'clash95_hd_complete_1024x768.exe'
REAL_MANIFEST = REAL_DIRECTORY / 'clash95_hd_complete_1024x768.candidate.json'


@unittest.skipUnless(all(path.is_file() for path in (REAL_ORIGINAL, REAL_SAVE)),
                     'read-only original/save unavailable')
class RealBoundTests(unittest.TestCase):
    def test_actual_complete_bundle_reconstruction_with_synthetic_log_only(self):
        # Actual user-owned inputs, producer, complete context and both parsers.
        # The invented log is a fixture only, never an observation or artifact.
        original, save = REAL_ORIGINAL.read_bytes(), REAL_SAVE.read_bytes()
        candidate, manifest, _ = trace.producer.builder.build_candidate(original, '1024x768')
        manifest = json.loads(json.dumps(manifest))
        if REAL_MANIFEST.is_file() and REAL_CANDIDATE.is_file():
            prepared = trace.producer.read_manifest(REAL_MANIFEST)
            if trace.canonical(prepared) != trace.canonical(manifest):
                # The recorded worktree bundle has three absolute source-path
                # receipts from its original checkout. Never repin that file.
                with self.assertRaisesRegex(ValueError, 'manifest differs from exact source reconstruction'):
                    trace.producer.build_selection_probe(original, REAL_CANDIDATE.read_bytes(), save,
                        capture_dir='C:/ClashCaptures/offline-stale-complete-selection-fixture',
                        candidate_manifest=prepared, resolution='1024x768')
        packet = trace.producer.build_selection_probe(original, candidate, save,
            capture_dir='C:/ClashCaptures/offline-complete-selection-bound-fixture',
            candidate_manifest=manifest, resolution='1024x768')
        log = log_fixture(packet)
        args = dict(original=original, candidate=candidate, save=save,
            generated_probe=packet['compiled_probe'].replace('\n', '\r\n').encode('ascii'),
            candidate_manifest=manifest)
        result = trace.evaluate_bound_trace(log, packet, **args)
        self.assertTrue(result['passed'], result['failures'])
        self.assertTrue(result['source_authenticated']); self.assertTrue(result['whole_candidate_bound'])
        self.assertTrue(result['candidate_manifest_bound']); self.assertTrue(result['initial_map_trace']['passed'])
        self.assertTrue(result['ready_for_host_capture'])
        for key in ('runtime_accepted', 'pixels_verified', 'cleanup_verified', 'manual_input_proof', 'promotion_ready'):
            self.assertFalse(result[key], key)
        for key in ('original', 'candidate', 'save'):
            changed = dict(args); data = bytearray(changed[key]); data[-1] ^= 1; changed[key] = bytes(data)
            failed = trace.evaluate_bound_trace(log, packet, **changed)
            self.assertFalse(failed['passed']); self.assertFalse(failed['source_authenticated'])
        # Wrong command bytes fail the actual equality boundary; no producer or
        # complete-context implementation is replaced with a cached test stub.
        failed = trace.evaluate_bound_trace(log, packet, **(args | {'generated_probe': args['generated_probe'] + b'gc\n'}))
        self.assertFalse(failed['passed']); self.assertFalse(failed['ready_for_host_capture'])
        with patch.object(trace, 'FROZEN_TRACE_SHA256', '0' * 64):
            self.assertFalse(trace.evaluate_bound_trace(log, packet, **args)['passed'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
