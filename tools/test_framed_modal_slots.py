#!/usr/bin/env python3
"""Execute the new slot x86 with the frozen real canvas lifecycle x86.

Reuse the canvas fixture's actual native constructors/destructors and allocator
recorders. The additional native partial-blit ABI recorder preserves native
stack cleanup, exposes its received arguments and deliberately clobbers volatile
registers/flags. No game, debugger, wrapper or candidate process is launched.
"""
from pathlib import Path
import hashlib
import json
import os
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.patcher import complete_hd_candidate as complete
from src.patcher import framed_modal_canvas as modal
from src.patcher import framed_modal_slots as slots
from src.patcher import pe_extension as pe
import build_framed_candidate as framed
import test_framed_modal_canvas as canvas

SLOT_CODE = canvas.BASE + 0xB000
BLIT = canvas.BASE + 0x9A00
OBS = canvas.RECORD + 0x200

INVOKE = r'''
 static Dictionary<string,object> Slot(int entry,Dictionary<string,object> c,int index,int width,int height){
  int x=Get(c,"slot_x",126+71*(index%6)),y=Get(c,"slot_y",75+131*(index/6));
  int[] args={Get(c,"right",x+32),Get(c,"bottom",y+64),Get(c,"dest_x",x),Get(c,"dest_y",y)};
  int[] regs={Get(c,"source",Read(S+8)),y,Get(c,"destination",0),x,0,0x44556677,0x55667788,0x66778899};
  int[] before=new int[128/4];for(int i=0;i<before.Length;i++)before[i]=Read(S+i*4);
  byte[] physical=new byte[width*height];Marshal.Copy((IntPtr)F,physical,0,physical.Length);
  byte[] native=new byte[307200];Marshal.Copy((IntPtr)P,native,0,native.Length);
  var b=new List<byte>();b.Add(0x9c);b.Add(0x60);b.Add(0x89);b.Add(0x25);Imm(b,R+0x90);
  for(int i=3;i>=0;i--){b.Add(0x68);Imm(b,args[i]);}
  for(int i=0;i<8;i++)if(i!=4){b.Add((byte)(0xb8+i));Imm(b,regs[i]);}
  b.Add(0x68);Imm(b,0xED7);b.Add(0x9d);b.Add(0xe8);Imm(b,entry-(B+0xA000+b.Count+4));
  for(int i=0;i<8;i++){b.Add(0x89);b.Add((byte)(5+(i<<3)));Imm(b,R+0xA0+i*4);}
  b.Add(0x9c);b.Add(0x58);Abs(b,0xa3,R+0xC0);b.Add(0x61);b.Add(0x9d);b.Add(0x31);b.Add(0xc0);b.Add(0xc3);
  Bytes(B+0xA000,b.ToArray());((Entry)Marshal.GetDelegateForFunctionPointer((IntPtr)(B+0xA000),typeof(Entry)))();
  bool copied=Read(R+0x200+32)!=args[2];
  int ox=(width-640)/2,oy=(height-480)/2;bool oracle=true,intact=true,local=true;
  int differences=0;
  for(int yy=0;yy<height;yy++)for(int xx=0;xx<width;xx++){
   byte expected=physical[yy*width+xx];
   bool inside=xx>=x+ox&&xx<=x+ox+32&&yy>=y+oy&&yy<=y+oy+64;
   if(copied&&inside)expected=native[(yy-oy)*640+xx-ox];
   byte actual=Marshal.ReadByte((IntPtr)F,yy*width+xx);
   if(actual!=expected)oracle=false;
   if(actual!=physical[yy*width+xx]){differences++;if(!inside)local=false;}
  }
  for(int i=0;i<native.Length;i++)if(Marshal.ReadByte((IntPtr)P,i)!=native[i])intact=false;
  bool state=true;for(int i=0;i<before.Length;i++)if(i!=9&&Read(S+i*4)!=before[i])state=false;
  return new Dictionary<string,object>{{"slot",index},{"copied",copied},{"pixel_oracle",oracle},{"only_dirty_rect",local},
   {"source_intact",intact},{"state_unchanged_except_fault",state},{"differences",differences},
   {"esp",Read(R+0xB0)==Read(R+0x90)},{"flags",Read(R+0xC0)&0xCD5},{"incoming_flags",Read(R+0x228)&0xCD5},
   {"eax",Read(R+0xA0)},{"ecx",Read(R+0xA4)},{"edx",Read(R+0xA8)},{"ebx",Read(R+0xAC)},
   {"preserved",Read(R+0xB4)==regs[5]&&Read(R+0xB8)==regs[6]&&Read(R+0xBC)==regs[7]},
   {"seen",new int[]{Read(R+0x200),Read(R+0x204),Read(R+0x208),Read(R+0x20C),Read(R+0x210),Read(R+0x214),Read(R+0x218),Read(R+0x21C),Read(R+0x220),Read(R+0x224)}},
   {"fault",Read(S+36)},{"phase",Read(S)},{"alloc_calls",Read(R)},{"free_calls",Read(R+4)},
   {"canaries",IsFill(P-16,16,0xD7)&&IsFill(P+307200,16,0xD7)&&IsFill(F-16,16,0xD7)&&IsFill(F+width*height,16,0xD7)&&IsFill(S+128,16,0xD7)}};
 }
'''
CSHARP = canvas.CSHARP.replace(' static int Main()', INVOKE + '\n static int Main()')
CSHARP = CSHARP.replace('int arg=name==', '''if(name.StartsWith("slot")){steps.Add(Slot(I(entries["slot_blit"]),c,int.Parse(name.Substring(4)),width,height));continue;}
    int arg=name==''')
CSHARP = CSHARP.replace('else if(kv.Key=="root_esp")', 'else if(kv.Key=="fault")W(S+36,I(kv.Value));else if(kv.Key=="root_esp")')


def payload(original, owner, bundle, cases):
    data = canvas.payload(original, owner, cases)
    code = bytearray(bundle.code)
    for r in bundle.relocations:
        if bundle.base_va <= r.target < bundle.base_va + len(bundle.code):
            value = SLOT_CODE + r.target - bundle.base_va
        elif bundle.modal_state_va <= r.target < bundle.modal_state_va + 128:
            value = canvas.STATE + r.target - bundle.modal_state_va
        elif r.target == bundle.modal_active_va:
            value = canvas.BASE + owner.entries['is_active'] - owner.base_va
        elif r.target == slots.NATIVE_BLIT:
            value = BLIT
        else:
            raise AssertionError(hex(r.target))
        if r.kind == 'rel32': value -= SLOT_CODE + r.offset + 4
        struct.pack_into('<I', code, r.offset, value & 0xffffffff)
    data['stubs'][str(SLOT_CODE)] = code.hex()
    # Capture entry arguments and flags without perturbing their original
    # values. Native 4024E0 preserves ESI/EDI/EBP and returns with RET 16.
    b = bytearray()
    for reg, pos in ((0, 0), (1, 4), (2, 8), (3, 12), (6, 16), (7, 20)):
        b += b'\x89' + bytes([5 + reg * 8]) + canvas.u32(OBS + pos)
    b += b'\x9c\x58\xa3' + canvas.u32(OBS + 40)
    for stack, pos in ((4, 24), (8, 28), (12, 32), (16, 36)):
        b += b'\x8b\x44\x24' + bytes([stack]) + b'\xa3' + canvas.u32(OBS + pos)
    for reg, value in ((0, 0x1234AABB), (1, 0x2234AABB), (2, 0x3234AABB), (3, 0x4234AABB)):
        b += bytes([0xB8 + reg]) + canvas.u32(value)
    b += b'\x68' + canvas.u32(0x202) + b'\x9d\xc2\x10\x00'
    data['stubs'][str(BLIT)] = b.hex()
    data['entries']['slot_blit'] = SLOT_CODE
    return data


@unittest.skipUnless(os.name == 'nt' and Path('C:/Clash/clash95.exe').is_file() and canvas.CSC.is_file(),
                     'user-owned original and Windows x86 fixture compiler required')
class SlotsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = Path('C:/Clash/clash95.exe').read_bytes()
        cls.cache = {}
        cls.temp = tempfile.TemporaryDirectory(prefix='clash-modal-slots-fixture-')
        source = Path(cls.temp.name) / 'Fixture.cs'; source.write_text(CSHARP)
        cls.exe = Path(cls.temp.name) / 'Fixture.exe'
        result = subprocess.run([str(canvas.CSC), '/nologo', '/platform:x86', '/r:System.Web.Extensions.dll',
            '/out:' + str(cls.exe), str(source)], capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
        if result.returncode: raise AssertionError(result.stdout + result.stderr)

    @classmethod
    def tearDownClass(cls): cls.temp.cleanup()

    @classmethod
    def bundles(cls, width=1024, height=768):
        if (width, height) not in cls.cache:
            candidate, context, probe = complete.build_candidate(cls.original, f'{width}x{height}')
            base_va = pe.inspect_pe(candidate).image_size + 0x400000
            bundle = slots.emit_modal_slots(cls.original, candidate, base_va=base_va, width=width, height=height)
            meta = context['predecessor']['base_candidate']
            framed_base = framed.build_candidate(cls.original, f'{width}x{height}', minimap_viewport=True)[0]
            owner = modal.emit_modal_canvas(cls.original, framed_base, base_va=meta['code_va'],
                state_va=meta['state_va'], width=width, height=height)
            cls.cache[width, height] = candidate, context, probe, owner, bundle
        return cls.cache[width, height]

    def run_cases(self, cases, width=1024, height=768):
        _, _, _, owner, bundle = self.bundles(width, height)
        result = subprocess.run([str(self.exe)], input=json.dumps(payload(self.original, owner, bundle, cases)),
            capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        rows = json.loads(result.stdout)
        for row in rows:
            for step in row:
                self.assertTrue(step['esp'], step); self.assertTrue(step['canaries'], step)
                if 'slot' in step:
                    for key in ('pixel_oracle', 'only_dirty_rect', 'source_intact', 'state_unchanged_except_fault', 'preserved'):
                        self.assertTrue(step[key], step)
                    self.assertEqual(step['flags'], 0)
                    self.assertEqual(step['incoming_flags'], canvas.FLAGS & canvas.MASK)
                    self.assertEqual([step[k] for k in ('eax','ecx','edx','ebx')],
                        [0x1234AABB,0x2234AABB,0x3234AABB,0x4234AABB])
        return rows

    def test_every_slot_copies_inclusive_native_rectangle_and_translates_only_destination(self):
        for width,height in ((800,600),(1024,768),(1280,720),(1280,960),(1920,1080),(802,602)):
            rows = self.run_cases([dict(steps=['try_enter','paint',f'slot{i}','try_leave']) for i in range(12)], width,height)
            for i,row in enumerate(rows):
                s=row[1];x=126+71*(i%6);y=75+131*(i//6)
                self.assertTrue(s['copied'],s)
                self.assertGreater(s['differences'], 2000)
                self.assertEqual(s['seen'],[canvas.NATIVE,y,0,x,0x55667788,0x66778899,
                    x+32,y+64,x+(width-640)//2,y+(height-480)//2])
                self.assertEqual((s['alloc_calls'],s['free_calls'],s['fault']),(2,0,0))
                self.assertEqual((row[-1]['phase'],row[-1]['free_calls']),(0,2))

    def test_inactive_failed_allocation_and_after_destruction_keep_native_call(self):
        rows=self.run_cases([dict(steps=['slot0']),dict(allocation_failure=1,steps=['try_enter','slot0']),
            dict(allocation_failure=2,steps=['try_enter','slot0']),dict(steps=['try_enter','try_leave','slot0'])])
        for row in rows:
            s=row[-1];self.assertFalse(s['copied']);self.assertEqual(s['differences'],0)
            self.assertEqual(s['seen'][6:],[158,139,126,75])

    def test_successful_copy_preserves_incoming_flags_before_native_callee(self):
        step=self.run_cases([dict(steps=['try_enter','paint','slot11'])])[0][-1]
        self.assertTrue(step['copied'])
        self.assertEqual(step['seen'][6:],[513,270,673,350])
        self.assertEqual(step['incoming_flags'],canvas.FLAGS & canvas.MASK)

    def test_latched_fault_bad_thread_pointer_and_header_never_copy(self):
        mutations=[dict(fault=5),dict(tid=124),dict(native_width=800),dict(map_pointer=canvas.PHYSICAL),
            dict(native_pixels=canvas.PIXELS+4),dict(physical_pixels=canvas.PHYSPIX+4),
            dict(native_com=1),dict(native_pixels=canvas.PHYSPIX,owned_native_pixels=canvas.PHYSPIX)]
        for row in self.run_cases([dict(steps=['try_enter','paint',m,'slot0']) for m in mutations]):
            s=row[-1];self.assertFalse(s['copied']);self.assertEqual(s['differences'],0)
            self.assertIn(s['fault'],(4,5));self.assertEqual(s['free_calls'],0)

    def test_unexpected_source_destination_and_rectangle_delegate_unchanged(self):
        changes=[dict(source=0),dict(destination=canvas.PRIMARY),dict(slot_x=127),dict(slot_x=-1),
            dict(slot_y=76),dict(right=157),dict(bottom=138),dict(dest_x=127),dict(dest_y=76)]
        for row in self.run_cases([dict(c,steps=['try_enter','paint','slot0']) for c in changes]):
            s=row[-1];self.assertFalse(s['copied']);self.assertEqual(s['differences'],0);self.assertEqual(s['fault'],0)

    def test_only_one_checked_call_and_complete_identity_no_historical_image_edits(self):
        candidate,context,probe,owner,b=self.bundles()
        self.assertFalse(b.installation_ready);self.assertEqual(len(b.hook_sites),1)
        self.assertEqual(b.candidate_sha256,hashlib.sha256(candidate).hexdigest())
        h=b.hook_sites[0];self.assertEqual(h.va,0x432C0B);self.assertEqual(h.old,slots.EXPECTED_CALL)
        self.assertEqual(h.new[0],0xE8);self.assertEqual(h.va+5+struct.unpack_from('<i',h.new,1)[0],b.base_va)
        self.assertEqual(b.source_contract['new_state_bytes'],0)
        self.assertEqual(b.source_contract['stage'],slots.STAGE)
        self.assertEqual(b.modal_active_va,owner.entries['is_active'])
        self.assertNotIn('mirror',b.entries)
        self.assertEqual(complete.build_candidate(self.original,'1024x768')[0],candidate)

    def test_wrong_candidate_old_bytes_base_sha_and_allocation_fail_closed(self):
        candidate,context,probe,owner,b=self.bundles()
        kwargs=dict(base_va=b.base_va,width=1024,height=768)
        with self.assertRaises(ValueError):slots.emit_modal_slots(self.original[:-1],candidate,**kwargs)
        with self.assertRaises(ValueError):slots.emit_modal_slots(self.original,candidate[:-1],**kwargs)
        with self.assertRaises(ValueError):slots.emit_modal_slots(self.original,candidate,**dict(kwargs,base_va=b.base_va-4096))
        # Independent old-byte rejection even if a future predecessor returned
        # the same altered bytes: whole-image identity is not the only gate.
        altered=bytearray(candidate);altered[b.hook_sites[0].offset]^=1;altered=bytes(altered)
        with patch.object(complete,'build_candidate',return_value=(altered,context,probe)):
            with self.assertRaisesRegex(ValueError,'old bytes'):slots.emit_modal_slots(self.original,altered,**kwargs)


if __name__ == '__main__': unittest.main()
