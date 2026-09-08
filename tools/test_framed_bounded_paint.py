from __future__ import annotations

from dataclasses import replace
from contextlib import redirect_stdout, redirect_stderr
import copy
import errno
import io
import json
import os
from pathlib import Path
import random
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tools')]
from src.patcher import framed_bounded_paint as bounded
from src.patcher import framed_camera as camera
from src.patcher import partial_tile_clip as clip
from src.patcher import pe_extension as pe
from src.patcher.framed_viewport import FramedViewport
import build_framed_bounded_candidate as cli
import test_framed_camera as fixture
from test_pe_extension import independent_image

SIZES = fixture.SIZES
BASE = 0x100000
DATA_SIZE = 0x60000
GLOBALS = {clip.GAME_DATA_GLOBAL: 0x100, clip.MAP_SURFACE_GLOBAL: 0x104,
           clip.RENDER_DEVICE_GLOBAL: 0x108, clip.LOWER_ROW_OWNER_GLOBAL: 0x10c,
           clip.TILE_CALLBACK_GLOBAL: 0x110, clip.CURSOR_VISIBLE_GLOBAL: 0x114,
           clip.MEMORY_VTABLE: 0x300}
CONTROL = 0x120
LOG = 0x28000
SURFACE = 0x400


def u32(v):
    return struct.pack('<I', v & 0xffffffff)


def synthetic_parent(key='1280x720'):
    parent, metadata = fixture.synthetic_parent(key)
    base = bytearray(parent)
    for row in reversed(metadata['edits']):
        off, old, new = row['offset'], bytes.fromhex(row['old_hex']), bytes.fromhex(row['new_hex'])
        assert bytes(base[off:off+len(new)]) == new
        base[off:off+len(new)] = old
    metadata['entry_vas'].update({name: metadata['code_va'] for name in bounded.HELPERS})
    return bytes(base), parent, metadata


class BoundedByteTests(unittest.TestCase):
    def test_source_identities_and_all_existing_pins_match(self):
        self.assertEqual(camera.sha(Path(camera.__file__).read_bytes()), bounded.CAMERA_SOURCE_SHA256)
        self.assertTrue(camera.source_status()['passed'])

    def test_final_image_is_reconstructed_from_scalar_base_and_exact_edits(self):
        for key in SIZES:
            with self.subTest(resolution=key):
                base, parent, metadata = synthetic_parent(key)
                frozen = copy.deepcopy(metadata)
                image, report = bounded._extend_verified_parent(base, parent, metadata, key, {})
                self.assertEqual(metadata, frozen)
                rebuilt = bytearray(base)
                for row in report['edits']:
                    off, old, new = row['offset'], bytes.fromhex(row['old_hex']), bytes.fromhex(row['new_hex'])
                    self.assertEqual(bytes(rebuilt[off:off+len(old)]), old)
                    rebuilt[off:off+len(old)] = new
                self.assertEqual(bytes(rebuilt), image)
                self.assertEqual(report['output_sha256'], camera.sha(image))
                self.assertEqual(len(report['payload_edits']), 2)
                self.assertTrue(all(len(bytes.fromhex(e['new_hex'])) == 124 for e in report['payload_edits']))
                self.assertEqual(report['stage'], bounded.STAGE)
                for field in ('game_runtime_executed', 'manual_input_proof', 'promotion_ready',
                              'small_world_input_enabled', 'parent_probe_reusable'):
                    self.assertIs(report[field], False)
                self.assertEqual(len(pe.inspect_pe(image).sections), len(pe.inspect_pe(parent).sections))
                self.assertEqual(image[pe.inspect_pe(base).headers_size:len(base)], base[pe.inspect_pe(base).headers_size:])

    def test_parent_must_reconstruct_exactly_and_unknown_helper_targets_reject(self):
        base, parent, metadata = synthetic_parent()
        for change in ({'entry_vas': metadata['entry_vas'] | {'cell': 0}},
                       {'entry_vas': metadata['entry_vas'] | {'cell': metadata['code_va']-1}},
                       {'input_sha256': '0'*64, 'code_sha256': '0'*64},
                       {'stage': bounded.STAGE}, {'relocations': []}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                bounded._extend_verified_parent(base, parent, metadata | change, '1280x720', {})
        changed = bytearray(base); changed[0x480] ^= 1
        with self.assertRaisesRegex(ValueError, 'reconstruction'):
            bounded._extend_verified_parent(bytes(changed), parent, metadata, '1280x720', {})

    def test_parent_gate_oldbytes_and_relocation_conflicts_still_fail(self):
        base, parent, metadata = synthetic_parent()
        mutated = bytearray(parent)
        field = metadata['entry_vas']['hook_framed_full_entry'] + 37
        pos = pe.inspect_pe(parent).file_offset(field-0x400000, 1)
        mutated[pos] ^= 1
        altered = dict(metadata, output_sha256=camera.sha(mutated))
        with self.assertRaises(ValueError):
            bounded._extend_verified_parent(base, bytes(mutated), altered, '1280x720', {})
        metadata['relocations'].append({'offset': field-metadata['code_va'], 'kind': 'rel32', 'target': field, 'purpose': 'conflict'})
        with self.assertRaisesRegex(ValueError, 'relocation'):
            bounded._extend_verified_parent(base, parent, metadata, '1280x720', {})

    def test_existing_payload_only_changes_declared_spans(self):
        base, parent, metadata = synthetic_parent('1366x768')
        image, report = bounded._extend_verified_parent(base, parent, metadata, '1366x768', {})
        p = pe.inspect_pe(parent).file_offset(metadata['code_va']-0x400000, metadata['code_bytes'])
        n = pe.inspect_pe(image).file_offset(report['code_va']-0x400000, report['code_bytes'])
        edited = set()
        for e in report['payload_edits']:
            start = e['va'] - report['code_va']; edited.update(range(start,start+124))
        self.assertTrue(all(i in edited for i in range(metadata['code_bytes']) if parent[p+i] != image[n+i]))
        self.assertGreater(report['code_bytes'], metadata['code_bytes'])

    def test_independent_loader_rebases_all_declared_absolute_operands(self):
        base, parent, metadata = synthetic_parent()
        image, report = bounded._extend_verified_parent(base, parent, metadata, '1280x720', {})
        memory, _, fields, _ = independent_image(image)
        original, _, original_fields, _ = independent_image(parent)
        self.assertTrue(set(original_fields) <= set(fields))
        delta = 0x200000
        relocated = bytearray(memory)
        for field in fields:
            struct.pack_into('<I', relocated, field, struct.unpack_from('<I',memory,field)[0]+delta)
        for row in report['relocations']:
            field = report['code_rva'] + row['offset']
            before = struct.unpack_from('<I', memory, field)[0]
            after = struct.unpack_from('<I', relocated, field)[0]
            self.assertEqual(after, before + delta if row['kind']=='abs32' else before)
        self.assertEqual(report['new_highlow_count'], len([r for r in report['relocations'] if r['kind']=='abs32']))

    def test_admission_is_validated_before_calling_any_parent_builder(self):
        with patch.object(camera, 'source_status') as status:
            for original in (b'', b'synthetic', None, bytearray(4)):
                with self.assertRaises(ValueError):
                    bounded.build_candidate(original,'1280x720')
            status.assert_not_called()

    def test_emitter_rejects_invalid_allocations_and_dependencies(self):
        entries = {name: BASE for name in bounded.HELPERS}
        for va in (True, -1, 0, 0x80000000):
            with self.assertRaises(ValueError):
                bounded.emit_helpers(FramedViewport(800,600),base_va=va,entries=entries)
        for wrong in ({}, entries | {'cell': BASE+0x2000}, entries | {'cell': True}):
            with self.assertRaises(ValueError):
                bounded.emit_helpers(FramedViewport(800,600),base_va=BASE+0x1000,entries=wrong)

    def test_native_fixture_images_resolve_every_data_and_code_reference(self):
        for key in SIZES:
            code, fixups, _ = native_image(key)
            native_image(key,'full_dispatch')
            self.assertLess(len(code), 0x20000)
            self.assertTrue(fixups)
            self.assertTrue(all(0 <= p <= len(code)-4 and kind in (0,1) for p,kind,target in fixups))

    def test_cli_preflight_writes_nothing_and_never_starts_game(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp)/'original.exe'; source.write_bytes(b'synthetic original')
            out = Path(temp)/'absent'/'candidate.exe'
            with patch.object(bounded,'build_candidate',return_value=(b'candidate',{'output_sha256':camera.sha(b'candidate')})), redirect_stdout(io.StringIO()):
                code = cli.main(['--original',str(source),'--resolution','1280x720','--preflight','--output',str(out)])
            self.assertEqual(code,0)
            self.assertFalse(out.parent.exists())
            with patch.object(bounded,'build_candidate') as build, redirect_stderr(io.StringIO()):
                code = cli.main(['--original',str(source),'--resolution','1280x720','--output',str(source),'--report-json',str(Path(temp)/'report.json')])
            self.assertEqual(code,1); build.assert_not_called()


def native_image(key, entry='bounded_full', bad_cell=False):
    layout = FramedViewport(*map(int,key.split('x')))
    prefix_size = 0x200
    with patch.object(clip,'verify_original'), patch.object(clip,'verify_edge_prerequisites'):
        cell = clip.emit_edge_dispatch(b'synthetic',b'synthetic',base_va=BASE+prefix_size,
                                      width=layout.width,height=layout.height,layout=layout)
    a = clip._Assembler(BASE)
    a.code.extend(bytes(prefix_size)); a.code.extend(cell.code)
    a.relocations.extend(replace(r,offset=r.offset+prefix_size) for r in cell.relocations)
    stub_entries = {}
    for name, tag, argc in (('tile',1,0),('fill',2,8),('minimap',3,0),
                            ('composition_guard',4,0),('draw_frame',5,0),('compose_panel',6,0),('present_map_rect',7,0)):
        stub_entries[name] = BASE+len(a.code)
        a.emit('9c608b15'); a.absolute(clip.GAME_DATA_GLOBAL,'game_data_global')
        a.emit('8b8a4001000081f940100000'); a.branch('0f8d',name+'.overflow')
        a.emit('89c8c1e0058d8402'); a.u32(LOG)
        a.emit('c78000000000'); a.u32(tag)
        for dest,src in ((4,28),(8,16),(12,24),(16,20),(20,4)):
            a.emit('8b5c24'+bytes([src]).hex()+'8958'+bytes([dest]).hex())
        if name=='fill':a.emit('8b5c2428895814')
        a.emit('8b1d'); a.absolute(clip.MAP_SURFACE_GLOBAL,'map_surface_global')
        a.emit('8b9bb80000008958188b1d'); a.absolute(clip.RENDER_DEVICE_GLOBAL,'render_device_global')
        a.emit('89581cff8240010000')
        if name in ('composition_guard','draw_frame','compose_panel','present_map_rect'):
            offset = CONTROL + {'composition_guard':4,'draw_frame':8,'compose_panel':12,'present_map_rect':16}[name]
            a.emit('8b82'); a.u32(offset); a.emit('8944241c')
        a.emit('619d')
        a.emit('c2'+struct.pack('<H',argc).hex() if argc else 'c3')
        a.label(name+'.overflow'); a.emit('0f0b')
    if bad_cell:
        cell_entry=BASE+len(a.code)
        a.emit('b8'); a.u32(3); a.emit('c3')
    else:
        cell_entry=cell.entries['cell']
    entries={name:stub_entries[name] for name in bounded.HELPERS if name!='cell'} | {'cell':cell_entry}
    helper=bounded.emit_helpers(layout,base_va=BASE+len(a.code),entries=entries)
    off=len(a.code);a.code.extend(helper.code)
    a.relocations.extend(replace(r,offset=r.offset+off) for r in helper.relocations)
    target=helper.entries.get(entry)
    if entry=='full_dispatch':
        target=BASE+len(a.code)
        gate_va=target+camera.GATE_OFFSETS['full_redraw']
        native_tail=bytes.fromhex('c7451c0700000089ec619dc3')
        reject_tail=bytes.fromhex('c7451c0000000089ec619dc3')
        fallback_tail=bytes.fromhex('c7451c0800000089ec619dc3')
        labels={'composition_guard':entries['composition_guard'],
                'framed_full_reject':gate_va+124+len(native_tail),
                'framed_full_fallback':gate_va+124+len(native_tail)+len(reject_tail)}
        prefix=camera._prefix('full_redraw',target,labels)
        prefix_offset=len(a.code);a.code.extend(prefix)
        self_address=prefix.index(bytes.fromhex('8b15'))+2
        a.relocations.append(clip.Relocation(prefix_offset+self_address,'abs32',clip.GAME_DATA_GLOBAL,'game_data_global'))
        gate, relocations=bounded._gate('full_redraw',gate_va,labels['framed_full_reject'],helper)
        gate_offset=len(a.code);a.code.extend(gate)
        a.relocations.extend(replace(r,offset=r.offset+gate_offset) for r in relocations)
        a.code.extend(native_tail+reject_tail+fallback_tail)
    wrapper=clip._Assembler(BASE)
    wrapper.emit('9c608b5424288992600100008992000100008d8a00040000898a04010000')
    wrapper.emit('8d8a00030000898ab8040000')
    wrapper.emit('b8');wrapper.absolute(cell.entries['clipped_vtable'],'clipped_vtable')
    wrapper.emit('89826401000083ba3401000000')
    wrapper.branch('0f84','fixture.table_set')
    wrapper.emit('8982b8040000')
    wrapper.label('fixture.table_set')
    wrapper.emit('8d8a00100000898a04040000')
    wrapper.emit('c7820801000000503412')
    wrapper.emit('bb22222222b933333333bd55555555be66666666bf777777778b8220010000')
    wrapper.emit('68470200009d')
    bounded._transfer(wrapper,'e8',target,'fixture_entry')
    wrapper.emit('9c608b7c244c')
    for i in range(9):
        wrapper.emit('8b4c24'+bytes([i*4]).hex()+'898f');wrapper.u32(0x180+i*4)
    wrapper.emit('619d8944241c619dc3')
    assert len(wrapper.code)<prefix_size
    a.code[:len(wrapper.code)]=wrapper.finish()
    a.relocations.extend(wrapper.relocations)
    fixups=[]
    for r in a.relocations:
        if r.kind=='abs32':
            if r.target in GLOBALS:
                fixups.append((r.offset,1,GLOBALS[r.target]))
            elif BASE <= r.target < BASE+len(a.code):
                fixups.append((r.offset,0,r.target-BASE))
            elif r.purpose.startswith('vtable_entry_') or r.purpose=='cursor_object':
                fixups.append((r.offset,0,prefix_size-2))
                a.code[prefix_size-2:prefix_size]=b'\x0f\x0b'
            elif r.purpose not in ('road_callback','build_callback'):
                raise AssertionError(('unknown absolute',r))
        else:
            target = stub_entries.get(r.purpose,r.target)
            if target in clip.NATIVE_TARGETS.values() and r.purpose not in stub_entries:
                target=BASE+prefix_size-2
                a.code[prefix_size-2:prefix_size]=b'\x0f\x0b'
            if not BASE <= target < BASE+len(a.code):
                raise AssertionError(('unknown relative',r,target))
            struct.pack_into('<i',a.code,r.offset,target-(BASE+r.offset+4))
    return bytes(a.code),fixups,layout


LINUX = r'''
typedef unsigned int U;
static unsigned char code[0x20000] __attribute__((aligned(4096)));
static unsigned char data[0x60000];
static int call(int n,int a,int b,int c){int r;__asm__ volatile("int $0x80":"=a"(r):"a"(n),"b"(a),"c"(b),"d"(c):"memory","cc");return r;}
static int readall(void*p,int n){unsigned char*q=p;while(n){int k=call(3,0,(int)q,n);if(k<=0)return 0;q+=k;n-=k;}return 1;}
static int writeall(void*p,int n){unsigned char*q=p;while(n){int k=call(4,1,(int)q,n);if(k<=0)return 0;q+=k;n-=k;}return 1;}
void _start(void){U h[3],f[3];if(!readall(h,12)||!h[0]||h[0]>sizeof(code)||h[1]>100||h[2]>10000||!readall(code,h[0]))goto fail;
for(U i=0;i<h[2];i++){if(!readall(f,12)||f[0]>h[0]-4||f[1]>1||f[2]>=(f[1]?sizeof(data):h[0]))goto fail;*(U*)(code+f[0])=(U)(f[1]?data:code)+f[2];}
if(call(125,(int)code,sizeof(code),5))goto fail;
for(U i=0;i<h[1];i++){if(!readall(data,sizeof(data)))goto fail;U result=((U(*)(void*))code)(data);if(!writeall(&result,4)||!writeall(data,sizeof(data)))goto fail;}
call(1,0,0,0);fail:call(1,2,0,0);}
'''
WINDOWS = r'''
using System;using System.IO;using System.Runtime.InteropServices;
class Worker{
[DllImport("kernel32",SetLastError=true)]static extern IntPtr VirtualAlloc(IntPtr a,UIntPtr n,uint t,uint p);
[DllImport("kernel32",SetLastError=true)]static extern bool VirtualProtect(IntPtr a,UIntPtr n,uint p,out uint old);
[DllImport("kernel32")]static extern bool VirtualFree(IntPtr a,UIntPtr n,uint t);
[DllImport("kernel32")]static extern bool FlushInstructionCache(IntPtr p,IntPtr a,UIntPtr n);
[DllImport("kernel32")]static extern IntPtr GetCurrentProcess();
[UnmanagedFunctionPointer(CallingConvention.Cdecl)]delegate uint Gate(IntPtr p);
static int Main(){IntPtr code=IntPtr.Zero,data=IntPtr.Zero;try{
var r=new BinaryReader(Console.OpenStandardInput());var w=new BinaryWriter(Console.OpenStandardOutput());
int size=r.ReadInt32(),count=r.ReadInt32(),n=r.ReadInt32();if(size<1||size>0x20000||count<0||count>100||n<0||n>10000)return 2;
byte[] bytes=r.ReadBytes(size);if(bytes.Length!=size)return 2;
code=VirtualAlloc(IntPtr.Zero,(UIntPtr)0x20000,0x3000,4);data=Marshal.AllocHGlobal(0x60000);if(code==IntPtr.Zero)return 2;
for(int i=0;i<n;i++){int off=r.ReadInt32(),kind=r.ReadInt32(),target=r.ReadInt32();if(off<0||off>size-4||kind<0||kind>1||target<0||target>=(kind==1?0x60000:size))return 2;Array.Copy(BitConverter.GetBytes((kind==1?data:code).ToInt32()+target),0,bytes,off,4);}
Marshal.Copy(bytes,0,code,size);uint old;if(!VirtualProtect(code,(UIntPtr)0x20000,0x20,out old)||!FlushInstructionCache(GetCurrentProcess(),code,(UIntPtr)size))return 2;
var gate=(Gate)Marshal.GetDelegateForFunctionPointer(code,typeof(Gate));
for(int i=0;i<count;i++){byte[] buf=r.ReadBytes(0x60000);if(buf.Length!=0x60000)return 2;Marshal.Copy(buf,0,data,buf.Length);uint result=gate(data);Marshal.Copy(data,buf,0,buf.Length);w.Write(result);w.Write(buf);}w.Flush();return 0;
}catch(Exception e){Console.Error.WriteLine(e);return 2;}finally{if(data!=IntPtr.Zero)Marshal.FreeHGlobal(data);if(code!=IntPtr.Zero)VirtualFree(code,UIntPtr.Zero,0x8000);}}}
'''


class BoundedNativeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='bounded-native-');cls.addClassCleanup(cls.temp.cleanup)
        root=Path(cls.temp.name)
        if os.name=='nt':
            compiler=Path(os.environ.get('WINDIR','C:/Windows'))/'Microsoft.NET/Framework/v4.0.30319/csc.exe'
            if not compiler.is_file():raise unittest.SkipTest('native x86 compiler unavailable')
            cls.exe=root/'worker.exe';source=root/'worker.cs';source.write_text(WINDOWS)
            command=[str(compiler),'/nologo','/platform:x86','/optimize+','/out:'+str(cls.exe),str(source)]
        else:
            compiler=shutil.which('gcc')
            if not compiler:raise unittest.SkipTest('gcc unavailable')
            cls.exe=root/'worker';source=root/'worker.c';source.write_text(LINUX)
            command=[compiler,'-m32','-nostdlib','-static','-fno-pie','-no-pie','-fno-stack-protector','-fno-builtin','-Os','-Wl,-e,_start',str(source),'-o',str(cls.exe)]
        cls.options={'creationflags':subprocess.CREATE_NO_WINDOW} if os.name=='nt' else {}
        result=subprocess.run(command,capture_output=True,text=True,timeout=60,**cls.options)
        if result.returncode:raise AssertionError(result.stdout+result.stderr)
        try: result=subprocess.run([str(cls.exe)],input=struct.pack('<III',1,0,0)+b'\xc3',capture_output=True,timeout=10,**cls.options)
        except OSError as exc:
            if exc.errno==errno.ENOEXEC:raise unittest.SkipTest('host cannot execute i386') from exc
            raise
        if result.returncode:raise AssertionError(result.stderr)

    def execute(self,key,cases,entry='bounded_full',bad_cell=False):
        code,fixups,layout=native_image(key,entry,bad_cell)
        payload=bytearray(struct.pack('<III',len(code),len(cases),len(fixups))+code+b''.join(struct.pack('<III',*f) for f in fixups))
        inputs=[]
        for case in cases:
            data=bytearray(b'\xa5'*DATA_SIZE)
            for start,end in ((0x100,0x1b0),(0x300,0x500),(LOG,DATA_SIZE)):
                data[start:end]=bytes(end-start)
            struct.pack_into('<4i',data,0x222e0,*case['world'])
            struct.pack_into('<I',data,SURFACE,layout.width|(layout.height<<16))
            struct.pack_into('<6I',data,CONTROL,case.get('present',0),case.get('guard',1),case.get('frame',1),case.get('panel',1),case.get('blit',1),case.get('clipped',0))
            struct.pack_into('<I',data,0x110,case.get('callback',0))
            struct.pack_into('<I',data,0x10c,case.get('owner',0))
            inputs.append(bytes(data));payload.extend(data)
        result=subprocess.run([str(self.exe)],input=bytes(payload),capture_output=True,timeout=30,**self.options)
        self.assertEqual(result.returncode,0,result.stderr.decode(errors='replace'))
        self.assertEqual(len(result.stdout),len(cases)*(DATA_SIZE+4))
        reports=[]
        for i,(case,initial) in enumerate(zip(cases,inputs)):
            start=i*(DATA_SIZE+4);status=struct.unpack_from('<I',result.stdout,start)[0];data=result.stdout[start+4:start+4+DATA_SIZE]
            address=struct.unpack_from('<I',data,0x160)[0]
            count=struct.unpack_from('<I',data,0x140)[0]
            self.assertLessEqual(count,4160)
            events=[struct.unpack_from('<8I',data,LOG+j*32) for j in range(count)]
            regs=struct.unpack_from('<9I',data,0x180)
            self.assertEqual((regs[0],regs[1],regs[2],regs[4],regs[6]),(0x77777777,0x66666666,0x55555555,0x22222222,0x33333333))
            self.assertEqual(regs[5],address)
            self.assertEqual(regs[7],status)
            self.assertEqual(regs[8]&0xcd5,0x247&0xcd5)
            self.assertEqual(struct.unpack_from('<I',data,SURFACE+184)[0],
                struct.unpack_from('<I',data,0x164)[0] if case.get('clipped') else address+0x300)
            self.assertEqual(struct.unpack_from('<I',data,0x108)[0],0x12345000)
            self.assertEqual(data[0x500:0x222e0],initial[0x500:0x222e0])
            self.assertEqual(data[0x222f0:LOG],initial[0x222f0:LOG])
            reports.append((status,struct.unpack_from('<4i',data,0x222e0),events,address))
        return reports

    def test_real_cell_dispatch_draws_valid_tiles_and_clears_full_partial_outside_cells(self):
        for key in SIZES:
            layout=FramedViewport(*map(int,key.split('x')))
            cases=[{'world':(1,1,99,-1)},{'world':(3,2,0,0)}, {'world':(layout.full_tiles[0]-1,100,999,999)},
                   {'world':(100,layout.full_tiles[1]-1,999,999),'present':1}]
            for case,(status,world,events,base) in zip(cases,self.execute(key,cases)):
                with self.subTest(resolution=key,world=world):
                    self.assertEqual(status,1)
                    w,h,sx,sy=world
                    self.assertEqual((sx,sy),(min(max(case['world'][2],0),max(0,w-layout.full_tiles[0])),min(max(case['world'][3],0),max(0,h-layout.full_tiles[1]))))
                    expected=[]; clear_rects=[]
                    for row in range(layout.ceil_tiles[1]):
                        for col in range(layout.ceil_tiles[0]):
                            l,t=32+64*col,16+64*row;r,b=min(l+63,layout.width-33),min(t+63,layout.height-17)
                            if sx+col<w and sy+row<h: expected.append((1,l,base+1400*(sx+col)+14*(sy+row),t))
                            else:
                                expected.extend(((2,base+SURFACE,t,l),(3,l,r,t)))
                                clear_rects.append((l,t,r,b))
                    calls=[e for e in events if e[0] in (1,2,3)]
                    self.assertEqual([(e[0],e[1],e[2],e[4]) for e in calls],expected)
                    self.assertEqual([(e[4],e[2],e[3],e[5]) for e in calls if e[0]==2],clear_rects)
                    tags=[e[0] for e in events]
                    self.assertEqual(tags[0],4)
                    self.assertEqual(tags[-3:] if case.get('present') else tags[-2:], [5,6,7] if case.get('present') else [5,6])
                    for event in events:
                        if event[0] in (5,6,7):self.assertEqual(event[6],base+0x300)
                    if case.get('present'):
                        last=events[-1];self.assertEqual((last[1],last[2],last[3],last[4]),(0,0,layout.width-1,layout.height-1))

    def test_invalid_world_guard_and_flag_rejections_do_not_draw(self):
        cases=[{'world':v} for v in ((0,2,0,0),(2,0,0,0),(-1,2,99,99),(101,2,-1,99),(2,101,99,-1))]
        cases += [{'world':(3,2,99,99),'guard':0},{'world':(3,2,99,99),'present':2}]
        for case,(status,world,events,_) in zip(cases,self.execute('1280x720',cases)):
            self.assertEqual(status,0)
            self.assertEqual(world,case['world'])
            self.assertTrue(all(e[0]==4 for e in events))

    def test_failed_cell_frame_panel_or_present_never_becomes_success(self):
        for field in ('frame','panel','blit'):
            case={'world':(3,2,0,0),'present':1,field:0}
            status,_,events,_=self.execute('1280x720',[case])[0]
            self.assertEqual(status,0)
            tags=[e[0] for e in events]
            if field=='frame':self.assertNotIn(6,tags);self.assertNotIn(7,tags)
            if field=='panel':self.assertNotIn(7,tags)
        status,_,events,_=self.execute('1280x720',[{'world':(3,2,0,0)}],bad_cell=True)[0]
        self.assertEqual(status,0);self.assertEqual([e[0] for e in events],[4])
        for field in ('callback','owner'):
            status,_,events,_=self.execute('1280x720',[{'world':(3,2,0,0),field:1}])[0]
            self.assertEqual(status,0);self.assertTrue(all(e[0] not in (5,6,7) for e in events))

    def test_fitting_worlds_are_left_for_native_full_loop(self):
        for key in SIZES:
            layout=FramedViewport(*map(int,key.split('x')))
            cases=[{'world':(100,100,99,99)}, {'world':(*layout.full_tiles,99,99)}]
            for status,world,events,_ in self.execute(key,cases):
                self.assertEqual(status,0)
                self.assertEqual([e[0] for e in events],[4])
                self.assertEqual(world[2:],(max(0,world[0]-layout.full_tiles[0]),max(0,world[1]-layout.full_tiles[1])))

    def test_actual_full_entry_prefix_and_dispatch_preserve_the_native_route(self):
        cases=[{'world':(100,100,99,99)}, {'world':(3,2,99,99),'present':1},
               {'world':(0,2,99,99)}, {'world':(3,2,99,99),'guard':0}]
        results=self.execute('1280x720',cases,entry='full_dispatch')
        self.assertEqual([r[0] for r in results],[7,1,0,8])
        self.assertEqual(results[0][1],(100,100,81,90))
        self.assertEqual([e[0] for e in results[0][2]],[4])
        self.assertEqual(results[1][1],(3,2,0,0))
        self.assertEqual(results[1][2][-1][0],7)
        self.assertEqual(results[2][1],cases[2]['world'])
        self.assertEqual(results[3][1],cases[3]['world'])

    def test_nested_clipped_table_is_restored_after_success_and_failure(self):
        cases=[{'world':(3,2,0,0),'clipped':1,'present':1},
               {'world':(3,2,0,0),'clipped':1,'frame':0},
               {'world':(3,2,0,0),'clipped':1,'panel':0}]
        results=self.execute('1366x768',cases)
        self.assertEqual([r[0] for r in results],[1,0,0])
        for _,_,events,address in results:
            for e in events:
                if e[0] in (5,6,7):self.assertEqual(e[6],address+0x300)

    def test_small_world_admission_clamps_signed_extremes_and_preserves_dimensions(self):
        rng=random.Random(19)
        for key in SIZES:
            layout=FramedViewport(*map(int,key.split('x')))
            cases=[{'world':(rng.randint(1,100),rng.randint(1,100),rng.choice((-2147483648,-1,0,99,2147483647)),rng.choice((-2147483648,-1,0,99,2147483647)))} for _ in range(12)]
            for case,(status,world,events,_) in zip(cases,self.execute(key,cases,entry='admit_world')):
                w,h,x,y=case['world'];self.assertEqual(status,2 if w<layout.full_tiles[0] or h<layout.full_tiles[1] else 1)
                self.assertEqual(world,(w,h,min(max(x,0),max(0,w-layout.full_tiles[0])),min(max(y,0),max(0,h-layout.full_tiles[1]))))
                self.assertEqual(events,[])


if __name__=='__main__':
    unittest.main()
