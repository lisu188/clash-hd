#!/usr/bin/env python3
"""Original-backed byte and Unicorn tests; never start the game or a debugger."""
from pathlib import Path
import argparse
import struct
import re
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'tools')]
from src.patcher import ordinary_castle_entry as tool
from src.patcher import pe_extension as pe
from src.patcher import framed_modal_canvas as canvas
import build_ordinary_castle_entry_candidate as cli

ORIGINAL = None
REQUIRE_MACHINE = False
TOOLCHAIN = None


def put32(emu, address, value):
    emu.mem_write(address, struct.pack('<I', value & 0xFFFFFFFF))


class SourceTests(unittest.TestCase):
    def test_gate_fits_fixed_unused_padding_and_has_no_absolute_operands(self):
        gate, operands = tool.emit_gate()
        self.assertEqual(len(gate), 96)
        self.assertEqual(gate[4:10], bytes.fromhex('e8000000005f'))
        self.assertEqual({r['kind'] for r in operands}, {'rel32', 'eip_relative_disp32'})
        for row in operands:
            displacement = struct.unpack_from('<i', gate, row['offset'])[0]
            anchor = tool.GATE+row['offset']+4 if row['kind']=='rel32' else row['anchor']
            self.assertEqual(anchor+displacement, row['target'])
        self.assertLessEqual(tool.GATE+len(gate), 0x647C00)

    def test_loaded_probe_read_error_cannot_reach_completion(self):
        with patch.object(tool, '_read', return_value=bytes(123)):
            probe=tool._probe(b'image',((0x400000,123),))
        self.assertEqual(probe.splitlines()[1],'r @$t19=0')
        checks=[line for line in probe.splitlines() if line.startswith('.if ((by(')]
        rows=[]
        for line in checks:
            match=re.search(r'\.else \{ \.if \(@\$t19 != 0n(\d+)\).*\.else \{ r @\$t19=0n(\d+) \} \}',line)
            self.assertIsNotNone(match)
            rows.append(tuple(map(int,match.groups())))
        self.assertEqual(rows,[(0,1),(1,2),(2,3)])
        final=probe.splitlines()[-1]
        self.assertTrue(final.startswith('.if (@$t19 == 0n3) { .echo ORDINARY_CASTLE_CONTRACT_PASS '))
        self.assertIn('.else { .echo ORDINARY_CASTLE_INCOMPLETE; q }',final)
        self.assertFalse(any(line.startswith('.echo ORDINARY_CASTLE_CONTRACT_PASS') for line in probe.splitlines()))
        for error_index in range(len(rows)):
            counter=0;rejected=False
            for index,(expected,advance) in enumerate(rows):
                if index==error_index:continue  # CDB aborts unreadable expression line.
                if counter!=expected:rejected=True;break
                counter=advance
            self.assertTrue(rejected or counter!=len(rows))

    def test_wrong_original_and_resolution_fail_before_parent_build(self):
        with patch.object(tool.parent_builder, 'build_candidate') as parent:
            with self.assertRaises(ValueError): tool.build_candidate(b'unknown')
            with self.assertRaises(ValueError): tool.build_candidate(b'', '800x600')
            parent.assert_not_called()

    def test_output_paths_are_checked_before_reading_original(self):
        for target in ('C:/Clash/clash95.exe', str(ROOT/'candidate.exe'), 'C:/ClashTests/bad.txt'):
            with self.subTest(target=target), self.assertRaises(ValueError):
                cli.write_candidate('missing-original.exe', target)

    def test_stage_and_runtime_limits_are_explicit(self):
        self.assertTrue(tool.STAGE.endswith('-ordinarycastleentry-validation'))
        self.assertNotEqual(tool.STAGE, tool.PARENT_STAGE)
        self.assertIn('1024x768', tool.LIMITS[0])
        self.assertIn('targeted', tool.LIMITS[3])


class NativeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if ORIGINAL is None: raise unittest.SkipTest('--source-exe required for original-backed tests')
        cls.original = Path(ORIGINAL).read_bytes()
        cls.image, cls.meta, cls.probe = tool.build_candidate(cls.original)
        cls.parent = bytearray(cls.image)
        for edit in cls.meta['edits']:
            old = bytes.fromhex(edit['old_hex'])
            cls.parent[edit['offset']:edit['offset']+len(old)] = old
        cls.parent = bytes(cls.parent)
        cls.view = pe.inspect_pe(cls.image)

    def test_only_declared_branch_and_padding_bytes_change(self):
        self.assertEqual(tool.sha(self.parent), tool.PARENT_SHA256)
        allowed = set()
        for edit in self.meta['edits']:
            self.assertEqual(edit['va']-0x400000, edit['rva'])
            old, new = bytes.fromhex(edit['old_hex']), bytes.fromhex(edit['new_hex'])
            self.assertEqual(len(old), len(new))
            self.assertEqual(self.parent[edit['offset']:edit['offset']+len(old)], old)
            allowed.update(range(edit['offset'], edit['offset']+len(old)))
        changed = {n for n,(a,b) in enumerate(zip(self.parent,self.image)) if a != b}
        self.assertTrue(changed)
        self.assertLessEqual(changed, allowed)
        self.assertEqual({e['va'] for e in self.meta['edits']}, {tool.HOOK, tool.GATE})
        self.assertEqual(pe.inspect_pe(self.parent), self.view)
        self.assertEqual(pe._old_relocations(self.parent,self.view), pe._old_relocations(self.image,self.view))
        self.assertEqual(self.image[:self.view.headers_size], self.parent[:self.view.headers_size])

    def test_exact_parent_rejects_tampered_native_source_hook_or_padding(self):
        for va in (tool.NATIVE_CALLER, tool.HOOK, tool.GATE):
            changed = bytearray(self.parent)
            offset = self.view.file_offset(va-0x400000,1)
            changed[offset] ^= 1
            with self.subTest(va=hex(va)), patch.object(tool.parent_builder,'build_candidate',
                    return_value=(bytes(changed),self.meta['base_candidate'],'')):
                with self.assertRaisesRegex(ValueError,'predecessor SHA-256'):
                    tool.build_candidate(self.original)

    def test_old_byte_and_zero_padding_checks_fail_independently(self):
        changed = bytearray(self.parent)
        offset = self.view.file_offset(tool.HOOK-0x400000,6)
        changed[offset] ^= 1
        with self.assertRaisesRegex(ValueError,'old bytes'):
            tool._checked_edit(bytes(changed),tool.HOOK,tool.OLD_BRANCH,b'\x90'*6,'test branch')
        changed = bytearray(self.parent)
        changed[self.view.file_offset(tool.GATE-0x400000,1)] = 1
        with self.assertRaisesRegex(ValueError,'padding is not zero'): tool._layout(bytes(changed))

    def test_targeted_probe_binds_gate_and_native_caller_without_runtime_claim(self):
        for va in (tool.HOOK, tool.GATE, tool.NATIVE_CALLER, tool.TRY_ENTER, tool.ROOT_WRAPPER):
            self.assertIn(f'by({va:08x})',self.probe)
        self.assertEqual(self.meta['probe_sha256'], tool.sha(self.probe.encode()))
        self.assertFalse(self.meta['runtime_executed'])
        self.assertFalse(self.meta['manual_input_proof'])
        self.assertFalse(self.meta['promotion_ready'])
        self.assertEqual(self.meta['source_hashes'][tool.SOURCE],tool.sha((ROOT/tool.SOURCE).read_bytes()))

    def machine(self, **options):
        try:
            import unicorn
            from unicorn import x86_const
        except ImportError:
            if REQUIRE_MACHINE: self.fail('--require-machine-tools requires Unicorn')
            self.skipTest('Unicorn unavailable; use --toolchain or --require-machine-tools')
        return Machine(self.image, **options)

    def test_actual_parent_rejects_native_route_successor_admits_without_owner_write(self):
        machine = self.machine()
        original = Machine(self.parent).run()
        result = machine.run()
        self.assertEqual((original['result'],original['allocations'],original['phase']), (0,[],0))
        self.assertEqual((result['result'],result['allocations'],result['phase']), (1,[188,307200],1))
        self.assertEqual(result['owner'],0x4617A0)
        self.assertEqual(result['native_dimensions'],640 | (480<<16))
        self.assertEqual(result['native_pixels'],Machine.PIXELS)
        self.assertTrue(result['pixels_cleared'])
        self.assertEqual(result['state_root'],Machine.ROOT_STACK)
        self.assertEqual(result['state_allocations'],1)
        self.assertEqual(result['frees'],[])
        self.assertEqual(result['map'],Machine.NATIVE)
        self.assertEqual(result['render'],Machine.NATIVE)
        self.assertTrue(result['preserved'])

    def test_original_map_owner_path_keeps_register_and_flag_abi(self):
        for delta in (0,0x100000):
            with self.subTest(delta=hex(delta)):
                result = self.machine(owner=0x40AD40, saved_ebx=0x12345678,
                                      saved_esi=0x23456789, root_return=0x456789,
                                      delta=delta).run()
                self.assertEqual((result['result'],result['phase']), (1,1))
                self.assertTrue(result['preserved'])
                self.assertEqual(result['owner'],0x40AD40+delta)

    def test_each_native_caller_context_mismatch_rejects_without_allocation(self):
        cases = (
            dict(owner=0x422020), dict(owner=0x4617A1),
            dict(saved_ebx=0x40AD41), dict(saved_esi=0x4617A1),
            dict(root_return=0x41ED70), dict(bad_argument=True),
            dict(bad_public_return=True),
        )
        for case in cases:
            with self.subTest(case=case):
                result = self.machine(**case).run()
                self.assertEqual((result['result'],result['phase'],result['allocations']), (0,0,[]))
                self.assertEqual(result['map'],Machine.PHYSICAL)
                self.assertEqual(result['render'],Machine.PHYSICAL)
                if not case.get('bad_public_return'): self.assertTrue(result['preserved'])

    def test_inherited_prerequisites_remain_closed(self):
        cases = (dict(map_width=640), dict(map_vtable=1), dict(map_null=True),
                 dict(lower=1), dict(post=1), dict(primary_width=640),
                 dict(primary_vtable=1),dict(depth=16),dict(backend_null=True),
                 dict(backend_surface_null=True),dict(thread_id=0),
                 dict(render_invalid=True),dict(phase=1),dict(fault=2))
        for case in cases:
            with self.subTest(case=case):
                result = self.machine(**case).run()
                self.assertEqual((result['result'],result['allocations']), (0,[]))
                self.assertTrue(result['preserved'])
                self.assertEqual(result['state_fault'],5 if case.get('phase') else case.get('fault',0))

    def test_original_allocator_rollback_and_primary_render_target(self):
        for failure in (1,2):
            with self.subTest(failure=failure):
                result = self.machine(fail_allocation=failure).run()
                self.assertEqual((result['result'],result['phase']), (0,0))
                self.assertEqual(result['allocations'],[188,307200][:failure])
                self.assertEqual(result['frees'],[] if failure==1 else [Machine.NATIVE])
                self.assertEqual(result['pending'],(0,0))
                self.assertEqual(result['map'],Machine.PHYSICAL)
                self.assertTrue(result['preserved'])
        result = self.machine(render_primary=True).run()
        self.assertEqual(result['result'],1)
        self.assertEqual(result['saved_render'],canvas.PRIMARY)

    def test_native_route_relocated_image_and_varied_incoming_flags(self):
        for delta in (0,0x100000):
            for flags in (0x202,0xED7):
                with self.subTest(delta=hex(delta),flags=hex(flags)):
                    result = self.machine(delta=delta,flags=flags).run()
                    self.assertEqual(result['result'],1)
                    self.assertTrue(result['preserved'])
                    self.assertEqual(result['owner'],0x4617A0+delta)
                    self.assertEqual(result['native_vtable'],canvas.MEMORY_VTABLE+delta)


class Machine:
    """Execute the real hook, try_enter, base ctor and member ctor in Unicorn.

    The allocator, rollback free and OS thread import are explicit ABI models.
    Execution stops before the real castle body; no game is launched.
    """
    HEAP=0x1000000
    PHYSICAL=HEAP+0x1000
    NATIVE=HEAP+0x2000
    BACKEND=HEAP+0x3000
    PHYSICAL_PIXELS=HEAP+0x10000
    PIXELS=HEAP+0x100000
    API=0x1800000
    STACK=0x2000000
    ROOT_STACK=STACK+0x8000
    FLAGS_MASK=0xCD5

    def __init__(self,image,**options):
        from unicorn import Uc,UC_ARCH_X86,UC_MODE_32
        from unicorn import x86_const as r
        self.options=options;self.r=r;self.delta=options.get('delta',0)
        self.u=Uc(UC_ARCH_X86,UC_MODE_32)
        view=pe.inspect_pe(image)
        self.u.mem_map(view.image_base+self.delta,view.image_size)
        self.u.mem_write(view.image_base+self.delta,image[:view.headers_size])
        for s in view.sections:
            if s.raw_offset and s.raw_size:
                self.u.mem_write(view.image_base+self.delta+s.rva,image[s.raw_offset:s.raw_offset+s.raw_size])
        _,fields=pe._old_relocations(image,view)
        for field in fields:
            addr=view.image_base+self.delta+field
            put32(self.u,addr,self.word(addr)+self.delta)
        self.u.mem_map(self.HEAP,0x200000)
        self.u.mem_map(self.API,0x1000)
        self.u.mem_map(self.STACK,0x10000)
        self.allocations=[];self.frees=[];self.result=None;self.unexpected_writes=[]
        self.u.mem_write(self.PIXELS,b'\xA7'*307200)
        self.u.mem_write(self.API,b'\xc3')
        for va,value in ((canvas.MAP,0 if options.get('map_null') else self.PHYSICAL),
                         (canvas.RENDER,self.PHYSICAL),(canvas.HOOK_OWNER,options.get('owner',0x4617A0)+self.delta),
                         (0x526994,options.get('lower',0)),(0x526990,options.get('post',0)),
                         (canvas.THREAD_IAT,self.API)):
            put32(self.u,self.address(va),value)
        put32(self.u,self.PHYSICAL,options.get('map_width',1024)|(768<<16))
        put32(self.u,self.PHYSICAL+4,self.PHYSICAL_PIXELS)
        put32(self.u,self.PHYSICAL+0xB8,options.get('map_vtable',canvas.MEMORY_VTABLE+self.delta))
        primary=self.address(canvas.PRIMARY)
        for offset,value in ((0,options.get('primary_width',1024)|(768<<16)),
                             (0xB8,options.get('primary_vtable',canvas.PRIMARY_VTABLE+self.delta)),
                             (0xD4,options.get('depth',8)),(0xBC,0 if options.get('backend_null') else self.BACKEND)):
            put32(self.u,primary+offset,value)
        put32(self.u,self.BACKEND+0xA4,0 if options.get('backend_surface_null') else self.BACKEND+0x200)
        if options.get('render_primary'): put32(self.u,self.address(canvas.RENDER),primary)
        if options.get('render_invalid'): put32(self.u,self.address(canvas.RENDER),self.PHYSICAL+4)
        put32(self.u,self.address(tool.STATE),options.get('phase',0))
        put32(self.u,self.address(tool.STATE)+36,options.get('fault',0))
        put32(self.u,self.ROOT_STACK,self.address(options.get('root_return',tool.NATIVE_RETURN)))
        self.seeds={'EAX':7,'ECX':7,'EDX':2,'EBX':options.get('saved_ebx',0x40AD40)+self.delta,
                    'ESI':options.get('saved_esi',0x4617A0)+self.delta,'EDI':0x12345678,'EBP':17}
        for name,value in self.seeds.items():self.u.reg_write(getattr(r,'UC_X86_REG_'+name),value)
        self.u.reg_write(r.UC_X86_REG_ESP,self.ROOT_STACK)
        self.u.reg_write(r.UC_X86_REG_EFLAGS,options.get('flags',0xED7))

    def address(self,va):return va+self.delta
    def word(self,address):return struct.unpack('<I',self.u.mem_read(address,4))[0]
    def state(self,name):return self.word(self.address(tool.STATE)+canvas.STATE[name])
    def ret(self,value=None):
        if value is not None:self.u.reg_write(self.r.UC_X86_REG_EAX,value)
        sp=self.u.reg_read(self.r.UC_X86_REG_ESP)
        self.u.reg_write(self.r.UC_X86_REG_EIP,self.word(sp))
        self.u.reg_write(self.r.UC_X86_REG_ESP,sp+4)

    def run(self):
        from unicorn import UC_HOOK_CODE,UC_HOOK_MEM_WRITE
        r=self.r
        def hook(emu,address,size,user):
            if address==self.address(tool.TRY_ENTER):
                if self.options.get('bad_argument'):emu.reg_write(r.UC_X86_REG_EAX,self.ROOT_STACK+4)
                if self.options.get('bad_public_return'):
                    put32(emu,emu.reg_read(r.UC_X86_REG_ESP),self.API+0x100)
            if address==self.API:
                self.ret(self.options.get('thread_id',123))
            elif address==self.address(canvas.ALLOC):
                size=emu.reg_read(r.UC_X86_REG_EAX)
                if size not in (188,307200):raise AssertionError('unexpected allocator size')
                self.allocations.append(size)
                value=self.NATIVE if size==188 else self.PIXELS
                self.ret(0 if len(self.allocations)==self.options.get('fail_allocation') else value)
            elif address==self.address(canvas.FREE):
                self.frees.append(emu.reg_read(r.UC_X86_REG_EAX));self.ret()
            elif address==self.address(tool.WRAPPER_RETURN):
                self.result=emu.reg_read(r.UC_X86_REG_EAX)
            elif address==self.API+0x100:
                self.result=emu.reg_read(r.UC_X86_REG_EAX);emu.emu_stop()
            elif address==self.address(0x422185):
                emu.emu_stop()
        def memory_write(emu,access,address,size,value,user):
            allowed=((self.STACK,self.STACK+0x10000),(self.NATIVE,self.NATIVE+188),
                     (self.PIXELS,self.PIXELS+307200),(self.address(tool.STATE),self.address(tool.STATE)+128),
                     (self.address(canvas.MAP),self.address(canvas.MAP)+4),
                     (self.address(canvas.RENDER),self.address(canvas.RENDER)+4))
            if not any(start<=address and address+size<=end for start,end in allowed):
                self.unexpected_writes.append((address,size))
        self.u.hook_add(UC_HOOK_CODE,hook)
        self.u.hook_add(UC_HOOK_MEM_WRITE,memory_write)
        self.u.emu_start(self.address(0x422180),self.API+0x200,count=250000)
        preserved=all(self.u.reg_read(getattr(r,'UC_X86_REG_'+name))==value for name,value in self.seeds.items())
        preserved &= not self.unexpected_writes
        preserved &= self.u.reg_read(r.UC_X86_REG_ESP)==self.ROOT_STACK-20
        preserved &= (self.u.reg_read(r.UC_X86_REG_EFLAGS)&self.FLAGS_MASK)==(self.options.get('flags',0xED7)&self.FLAGS_MASK)
        return dict(result=self.result,allocations=self.allocations,frees=self.frees,phase=self.state('phase'),
            owner=self.word(self.address(canvas.HOOK_OWNER)),map=self.word(self.address(canvas.MAP)),
            render=self.word(self.address(canvas.RENDER)),saved_render=self.state('saved_render'),
            native_dimensions=self.word(self.NATIVE),native_pixels=self.word(self.NATIVE+4),
            native_vtable=self.word(self.NATIVE+0xB8),
            pixels_cleared=bytes(self.u.mem_read(self.PIXELS,307200))==bytes(307200),
            state_root=self.state('root_esp'),state_allocations=self.state('allocations'),
            state_fault=self.state('fault'),pending=(self.state('pending_header'),self.state('pending_pixels')),
            unexpected_writes=self.unexpected_writes,preserved=bool(preserved))


def main():
    global ORIGINAL,REQUIRE_MACHINE,TOOLCHAIN
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-exe',type=Path)
    parser.add_argument('--toolchain',type=Path)
    parser.add_argument('--require-machine-tools',action='store_true')
    args,remaining=parser.parse_known_args()
    ORIGINAL=args.source_exe;REQUIRE_MACHINE=args.require_machine_tools;TOOLCHAIN=args.toolchain
    if TOOLCHAIN:sys.path.insert(0,str(TOOLCHAIN))
    if REQUIRE_MACHINE:
        if ORIGINAL is None:parser.error('--require-machine-tools requires --source-exe')
        try:import unicorn
        except ImportError:parser.error('--require-machine-tools requires Unicorn')
    unittest.main(argv=[sys.argv[0],*remaining])


if __name__=='__main__':main()
