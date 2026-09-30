#!/usr/bin/env python3
"""Inherited 1920x1080 modalwidgets admission and constructor CPU fixtures.

The original-backed lane builds one candidate in memory and runs its actual
hook, inherited admission and constructors in Unicorn. Only allocator/free
and the thread import are modeled. Execution stops before the castle body;
no game, debugger, output bundle or dependency install is run. CPU admission
does not establish castle rendering, input, exit, lifecycle or promotion.
"""
from copy import deepcopy
from dataclasses import asdict
from pathlib import Path
import argparse
import inspect
import io
import sys
from types import ModuleType
import unittest
from contextlib import redirect_stderr
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'tools')]
from src.patcher import ordinary_castle_entry_matrix as tool
from src.patcher import pe_extension as pe
from src.patcher import framed_modal_canvas as canvas
import test_ordinary_castle_entry as inherited
import test_ordinary_castle_entry_matrix as format_fixture

ORIGINAL=None
TOOLCHAIN=None
REQUIRE_MACHINE=False
PROFILE='modalwidgets'
RESOLUTION='1920x1080'
WIDTH,HEIGHT=1920,1080


def require_machine_tools():
    """Check the API used by Machine, not merely an importable package name."""
    try:
        from unicorn import Uc,UC_ARCH_X86,UC_MODE_32,UC_HOOK_CODE,UC_HOOK_MEM_WRITE,x86_const
        registers=('EAX','EBX','ECX','EDX','ESI','EDI','EBP','ESP','EFLAGS','EIP')
        if not callable(Uc) or not all(type(value) is int for value in (
                UC_ARCH_X86,UC_MODE_32,UC_HOOK_CODE,UC_HOOK_MEM_WRITE,
                *(getattr(x86_const,'UC_X86_REG_'+name) for name in registers))):
            raise ImportError('Unicorn x86 API differs')
    except (ImportError,AttributeError) as error:
        raise ImportError('Unicorn x86 API unavailable') from error


def reconstruct_parent(image,metadata):
    """Undo authenticated declared edits without building a second predecessor."""
    pe._require(type(image) is bytes and type(metadata) is dict
                and metadata.get('schema')==tool.SCHEMA
                and metadata.get('profile')==PROFILE and metadata.get('resolution')==RESOLUTION
                and metadata.get('stage')==tool.stage(PROFILE)
                and metadata.get('candidate_sha256')==tool.sha(image),
                'matrix candidate identity differs')
    edits=metadata.get('edits')
    pe._require(type(edits) is list and len(edits)>1
                and all(type(row) is dict for row in edits), 'declared matrix edits required')
    appends=[row for row in edits if row.get('old_hex')=='']
    pe._require(len(appends)==1 and appends[0] is edits[-1], 'one final matrix append required')
    parent_size=appends[0].get('offset')
    pe._require(type(parent_size) is int and 0<parent_size<len(image), 'bounded parent extent required')
    restored=bytearray(image)
    for edit in reversed(edits):
        offset=edit.get('offset')
        pe._require(type(offset) is int and offset>=0
                    and type(edit.get('old_hex')) is str and type(edit.get('new_hex')) is str,
                    'declared matrix edit fields differ')
        old,new=bytes.fromhex(edit['old_hex']),bytes.fromhex(edit['new_hex'])
        pe._require(new and restored[offset:offset+len(new)]==new, 'declared candidate bytes differ')
        if not old:
            pe._require(offset==parent_size and offset+len(new)==len(restored), 'append extent differs')
            del restored[offset:]
        else:
            pe._require(len(old)==len(new) and offset+len(old)<=parent_size,
                        'predecessor edit size or extent differs')
            restored[offset:offset+len(new)]=old
    parent=bytes(restored)
    pe._require(len(parent)==parent_size
                and tool.sha(parent)==metadata.get('base_candidate_sha256')
                and type(metadata.get('base_candidate')) is dict
                and metadata['base_candidate'].get('candidate_sha256')==tool.sha(parent),
                'exact reconstructed predecessor SHA-256 differs')
    return parent


def synthetic_candidate():
    """Explicit format fixture; never passed to the original-bound builder."""
    parent,admission=format_fixture.fixture(count=16)
    image,report=tool.extend_tail(parent,admission,PROFILE)
    metadata=dict(report,schema=tool.SCHEMA,profile=PROFILE,resolution=RESOLUTION,
                  stage=tool.stage(PROFILE),candidate_sha256=tool.sha(image),
                  base_candidate_sha256=tool.sha(parent),
                  base_candidate={'candidate_sha256':tool.sha(parent)})
    return parent,image,metadata


class PortableTests(unittest.TestCase):
    def test_legacy_signature_constants_and_default_memory_layout_remain_intact(self):
        machine=inherited.Machine
        signature=inspect.signature(machine)
        self.assertIsNone(signature.parameters['admission'].default)
        self.assertEqual((signature.parameters['width'].default,signature.parameters['height'].default),(1024,768))
        self.assertEqual(signature.parameters['admission'].kind,inspect.Parameter.KEYWORD_ONLY)
        self.assertEqual((machine.HEAP,machine.PHYSICAL,machine.NATIVE,machine.BACKEND),
                         (0x1000000,0x1001000,0x1002000,0x1003000))
        self.assertEqual((machine.PHYSICAL_PIXELS,machine.PIXELS,machine.API),(0x1010000,0x1100000,0x1800000))
        self.assertEqual(machine.pixel_layout(1024,768),(machine.PIXELS,0x200000))

    def test_hd_physical_and_native_pixel_spans_are_disjoint_and_mapped(self):
        machine=inherited.Machine
        pixels,heap_size=machine.pixel_layout(WIDTH,HEIGHT)
        self.assertGreaterEqual(pixels,machine.PHYSICAL_PIXELS+WIDTH*HEIGHT)
        self.assertEqual(pixels&0xFFF,0)
        self.assertGreaterEqual(machine.HEAP+heap_size,pixels+307200)
        self.assertLessEqual(machine.HEAP+heap_size,machine.API)
        regions=sorted(((machine.PHYSICAL,machine.PHYSICAL+188),
                        (machine.NATIVE,machine.NATIVE+188),(machine.BACKEND,machine.BACKEND+0x204),
                        (machine.PHYSICAL_PIXELS,machine.PHYSICAL_PIXELS+WIDTH*HEIGHT),(pixels,pixels+307200)))
        self.assertTrue(all(first[1]<=second[0] for first,second in zip(regions,regions[1:])))
        self.assertEqual((pixels,heap_size),(machine.HEAP+0x20B000,0x256000))
        self.assertEqual(machine.PIXELS,0x1100000)
        for dimensions in ((0,1080),(1920,0),(-1,1080),(True,1080),(65536,1080),(65535,65535)):
            with self.subTest(dimensions=dimensions),self.assertRaises(ValueError):
                machine.pixel_layout(*dimensions)

    def test_untyped_admission_rejects_before_importing_machine_tools(self):
        for admission in ({'state':0x600000},object(),0):
            with self.subTest(admission=admission),self.assertRaisesRegex(TypeError,'typed matrix Admission'):
                inherited.Machine(b'',admission=admission,width=WIDTH,height=HEIGHT)

    def test_missing_or_partial_unicorn_api_cannot_satisfy_required_machine_tools(self):
        incomplete=ModuleType('unicorn')
        with patch.dict(sys.modules,{'unicorn':incomplete}),self.assertRaisesRegex(ImportError,'x86 API unavailable'):
            require_machine_tools()
        incomplete.Uc=lambda:None
        for name in ('UC_ARCH_X86','UC_MODE_32','UC_HOOK_CODE','UC_HOOK_MEM_WRITE'):
            setattr(incomplete,name,1)
        incomplete.x86_const=ModuleType('unicorn.x86_const')
        with patch.dict(sys.modules,{'unicorn':incomplete}),self.assertRaisesRegex(ImportError,'x86 API unavailable'):
            require_machine_tools()

    def test_required_machine_cli_rejects_missing_original_before_any_machine_build(self):
        with patch.multiple(sys.modules[__name__],ORIGINAL=ORIGINAL,TOOLCHAIN=TOOLCHAIN,REQUIRE_MACHINE=REQUIRE_MACHINE),\
                patch.object(sys,'argv',[__file__,'--require-machine-tools']),redirect_stderr(io.StringIO()),\
                patch.object(tool,'build_candidate') as build,patch(__name__+'.require_machine_tools') as dependency:
            with self.assertRaises(SystemExit) as error:main()
        self.assertEqual(error.exception.code,2)
        build.assert_not_called();dependency.assert_not_called()

    def test_parent_reconstruction_truncates_append_and_reverses_every_declared_edit(self):
        parent,image,metadata=synthetic_candidate()
        self.assertEqual(reconstruct_parent(image,metadata),parent)
        before,after=pe.inspect_pe(parent),pe.inspect_pe(image)
        self.assertEqual(len(metadata['edits']),6)
        self.assertGreater(len(image),len(parent))
        self.assertEqual(before.sections[:-1],after.sections[:-1])
        self.assertEqual(pe._old_relocations(parent,before),pe._old_relocations(image,after))

    def test_parent_reconstruction_rejects_candidate_edit_append_and_parent_identity_mismatches(self):
        _parent,image,metadata=synthetic_candidate()
        changes=[]
        for field,value in (('schema','other'),('profile','completehd'),('resolution','1024x768'),
                            ('candidate_sha256','0'*64),('base_candidate_sha256','0'*64)):
            altered=deepcopy(metadata);altered[field]=value;changes.append((field,image,altered))
        altered=deepcopy(metadata);altered['base_candidate']['candidate_sha256']='0'*64
        changes.append(('typed_parent_sha',image,altered))
        altered=deepcopy(metadata);altered['edits'][0]['new_hex']='90'*6
        changes.append(('declared_new_bytes',image,altered))
        altered=deepcopy(metadata);altered['edits'][0]['old_hex']='90'*6
        changes.append(('declared_old_bytes',image,altered))
        altered=deepcopy(metadata);altered['edits']=altered['edits'][1:]
        changes.append(('missing_edit',image,altered))
        altered=deepcopy(metadata);altered['edits'].insert(0,deepcopy(altered['edits'][0]))
        changes.append(('duplicate_edit',image,altered))
        altered=deepcopy(metadata);altered['edits'].reverse()
        changes.append(('reordered_append',image,altered))
        altered=deepcopy(metadata);altered['edits'][-1]['offset']+=1
        changes.append(('append_offset',image,altered))
        altered=deepcopy(metadata);altered['candidate_sha256']=tool.sha(image+b'\0')
        changes.append(('unreported_tail',image+b'\0',altered))
        for name,changed,altered in changes:
            with self.subTest(name=name),self.assertRaises(ValueError):reconstruct_parent(changed,altered)


class OriginalMachineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if ORIGINAL is None:raise unittest.SkipTest('--source-exe required; original-backed inherited CPU cases not run')
        try:require_machine_tools()
        except ImportError:
            if REQUIRE_MACHINE:raise AssertionError('--require-machine-tools requires Unicorn')
            raise unittest.SkipTest('Unicorn unavailable; use --toolchain or --require-machine-tools')
        cls.original=Path(ORIGINAL).read_bytes()
        cls.image,cls.metadata,cls.probe=tool.build_candidate(cls.original,PROFILE,RESOLUTION)
        cls.parent=reconstruct_parent(cls.image,cls.metadata)
        cls.modal=tool.modal_ancestor(cls.metadata['base_candidate'],PROFILE,RESOLUTION)
        cls.admission=tool.derive_admission(cls.original,cls.parent,cls.modal)
        if asdict(cls.admission)!=cls.metadata['admission']:
            raise AssertionError('authenticated Admission differs from matrix metadata')

    def machine(self,image=None,**options):
        return inherited.Machine(self.image if image is None else image,admission=self.admission,
                                 width=WIDTH,height=HEIGHT,**options)

    def test_actual_modalwidgets_1920_admission_is_derived_from_exact_parent_and_keeps_scope_honest(self):
        self.assertEqual(tool.sha(self.original),pe.ORIGINAL_SHA256)
        self.assertEqual(self.metadata['schema'],tool.SCHEMA)
        self.assertEqual(self.metadata['recipe_revision'],tool.REVISION)
        self.assertEqual((self.metadata['profile'],self.metadata['resolution']),(PROFILE,RESOLUTION))
        self.assertEqual(tool.sha(self.image),self.metadata['candidate_sha256'])
        self.assertEqual(tool.sha(self.parent),self.metadata['base_candidate_sha256'])
        self.assertEqual(self.admission.try_enter,self.modal['modal_entry_vas']['try_enter'])
        self.assertEqual(self.admission.state,self.modal['state_va'])
        self.assertEqual(self.admission.wrapper_return,self.modal['modal_entry_vas']['root_entry']+11)
        machine=self.machine()
        self.assertEqual((machine.state_va,machine.try_enter,machine.wrapper_return),
                         (self.admission.state,self.admission.try_enter,self.admission.wrapper_return))
        self.assertEqual(pe._old_relocations(self.parent,pe.inspect_pe(self.parent)),
                         pe._old_relocations(self.image,pe.inspect_pe(self.image)))
        for key in ('runtime_executed','manual_input_proof','promotion_ready','bounded_small_world_integrated'):
            self.assertFalse(self.metadata[key])
        self.assertIn(tool.SOURCE,self.metadata['source_hashes'])
        for source,expected in self.metadata['source_hashes'].items():
            with self.subTest(source=source):self.assertEqual(tool.sha((ROOT/source).read_bytes()),expected)
        self.assertEqual(tool.sha(self.probe.encode()),self.metadata['probe_sha256'])

    def test_native_parent_rejects_and_matrix_admits_without_owner_write(self):
        parent=self.machine(self.parent).run()
        machine=self.machine();result=machine.run()
        self.assertEqual((parent['result'],parent['allocations'],parent['phase']),(0,[],0))
        self.assertEqual((result['result'],result['allocations'],result['phase']),(1,[188,307200],1))
        self.assertEqual(result['owner'],0x4617A0)
        self.assertEqual((result['map'],result['render']),(machine.NATIVE,machine.NATIVE))
        self.assertEqual((result['state_root'],result['state_allocations']),(machine.ROOT_STACK,1))
        self.assertEqual(result['frees'],[])
        self.assertTrue(result['preserved'])

    def test_actual_inherited_ctors_keep_640_canvas_allocation_and_disjoint_1920_pixels(self):
        machine=self.machine();result=machine.run()
        self.assertEqual(result['result'],1)
        self.assertEqual(result['native_dimensions'],640|(480<<16))
        self.assertEqual(result['native_pixels'],machine.PIXELS)
        self.assertEqual(result['native_vtable'],canvas.MEMORY_VTABLE)
        self.assertEqual(machine.word(machine.PHYSICAL),WIDTH|(HEIGHT<<16))
        self.assertEqual(machine.word(machine.PHYSICAL+4),machine.PHYSICAL_PIXELS)
        self.assertGreaterEqual(machine.PIXELS,machine.PHYSICAL_PIXELS+WIDTH*HEIGHT)
        self.assertTrue(result['pixels_cleared'])
        self.assertEqual(result['unexpected_writes'],[])
        self.assertTrue(result['preserved'])

    def test_native_canvas_clear_cannot_touch_physical_hd_pixels(self):
        machine=self.machine()
        physical=b'\x5B'*(WIDTH*HEIGHT)
        machine.u.mem_write(machine.PHYSICAL_PIXELS,physical)
        result=machine.run()
        self.assertEqual(result['result'],1)
        self.assertEqual(result['allocations'],[188,307200])
        self.assertTrue(result['pixels_cleared'])
        self.assertEqual(bytes(machine.u.mem_read(machine.PHYSICAL_PIXELS,len(physical))),physical)
        self.assertTrue(result['preserved'])

    def test_original_owner_path_preserves_inherited_register_and_flag_abi(self):
        for delta in (0,0x100000):
            with self.subTest(delta=hex(delta)):
                result=self.machine(owner=0x40AD40,saved_ebx=0x12345678,saved_esi=0x23456789,
                                    root_return=0x456789,delta=delta).run()
                self.assertEqual((result['result'],result['phase']),(1,1))
                self.assertEqual(result['owner'],0x40AD40+delta)
                self.assertTrue(result['preserved'])

    def test_native_caller_context_mismatches_reject_before_any_allocation(self):
        cases=(dict(owner=0x422020),dict(owner=0x4617A1),dict(saved_ebx=0x40AD41),
               dict(saved_esi=0x4617A1),dict(root_return=0x41ED70),dict(bad_argument=True),
               dict(bad_public_return=True))
        for options in cases:
            with self.subTest(options=options):
                machine=self.machine(**options);result=machine.run()
                self.assertEqual((result['result'],result['phase'],result['allocations']),(0,0,[]))
                self.assertEqual((result['map'],result['render']),(machine.PHYSICAL,machine.PHYSICAL))
                if not options.get('bad_public_return'):self.assertTrue(result['preserved'])

    def test_inherited_geometry_and_lifecycle_prerequisites_remain_closed(self):
        cases=(dict(map_width=640),dict(map_height=768),dict(map_vtable=1),dict(map_null=True),
               dict(lower=1),dict(post=1),dict(primary_width=640),dict(primary_height=768),
               dict(primary_vtable=1),dict(depth=16),dict(backend_null=True),
               dict(backend_surface_null=True),dict(thread_id=0),dict(render_invalid=True),
               dict(phase=1),dict(fault=2))
        for options in cases:
            with self.subTest(options=options):
                result=self.machine(**options).run()
                self.assertEqual((result['result'],result['allocations']),(0,[]))
                self.assertTrue(result['preserved'])
                self.assertEqual(result['state_fault'],5 if options.get('phase') else options.get('fault',0))

    def test_original_allocation_failures_roll_back_without_replacing_physical_surfaces(self):
        for failure in (1,2):
            with self.subTest(failure=failure):
                machine=self.machine(fail_allocation=failure);result=machine.run()
                self.assertEqual((result['result'],result['phase']),(0,0))
                self.assertEqual(result['allocations'],[188,307200][:failure])
                self.assertEqual(result['frees'],[] if failure==1 else [machine.NATIVE])
                self.assertEqual(result['pending'],(0,0))
                self.assertEqual((result['map'],result['render']),(machine.PHYSICAL,machine.PHYSICAL))
                self.assertTrue(result['preserved'])

    def test_primary_render_ownership_is_saved_and_native_map_is_selected(self):
        machine=self.machine(render_primary=True);result=machine.run()
        self.assertEqual(result['result'],1)
        self.assertEqual(result['saved_render'],canvas.PRIMARY)
        self.assertEqual((result['map'],result['render']),(machine.NATIVE,machine.NATIVE))
        self.assertTrue(result['preserved'])

    def test_native_admission_rebases_and_preserves_varied_incoming_flags(self):
        for delta in (0,0x100000):
            for flags in (0x202,0xED7):
                with self.subTest(delta=hex(delta),flags=hex(flags)):
                    result=self.machine(delta=delta,flags=flags).run()
                    self.assertEqual(result['result'],1)
                    self.assertEqual(result['owner'],0x4617A0+delta)
                    self.assertEqual(result['native_vtable'],canvas.MEMORY_VTABLE+delta)
                    self.assertTrue(result['preserved'])


def main():
    global ORIGINAL,TOOLCHAIN,REQUIRE_MACHINE
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-exe',type=Path)
    parser.add_argument('--toolchain',type=Path)
    parser.add_argument('--require-machine-tools',action='store_true')
    args,remaining=parser.parse_known_args()
    ORIGINAL,TOOLCHAIN,REQUIRE_MACHINE=args.source_exe,args.toolchain,args.require_machine_tools
    if TOOLCHAIN:sys.path.insert(0,str(TOOLCHAIN))
    if REQUIRE_MACHINE:
        if ORIGINAL is None:parser.error('--require-machine-tools requires --source-exe')
        try:require_machine_tools()
        except ImportError:parser.error('--require-machine-tools requires Unicorn')
    unittest.main(argv=[sys.argv[0],*remaining],verbosity=2)


if __name__=='__main__':main()
