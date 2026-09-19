"""Execute the additive quantity adapter and real inherited owner in synthetic x86.

No game, debugger or wrapper is launched. Native formatted text is an independent
cdecl argument/ABI recorder; its observed six arguments are the pixel-placement
contract. The production emitter independently rebuilds its exact predecessor.
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

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.patcher import framed_modal_primary_text as text
from src.patcher import framed_modal_canvas as modal
from src.patcher import pe_extension as pe
from src.patcher import partial_tile_clip as clip
import build_framed_modal_primary_candidate as builder
import test_framed_modal_canvas as canvas
from test_framed_modal_primary import owner_from_verified_slots

CODE, NATIVE, SITE, OBS, FORMAT = (canvas.BASE + n for n in (0xB000, 0xC000, 0xAE00, 0xF0200, 0xD1000))

INVOKE = r'''
 static Dictionary<string,object> TextCall(int entry,Dictionary<string,object> c,int width,int height){
  const int O=B+0xF0200,T=B+0xAE00;
  Fill(O,128,0);W(G+4,Get(c,"text_render",D));
  byte[] state=new byte[128];Marshal.Copy((IntPtr)S,state,0,128);
  int[] args={Get(c,"left",545),Get(c,"right",613),Get(c,"y",53),Get(c,"align",3),Get(c,"format",B+0xD1000),Get(c,"quantity",250)};
  int[] seed={0x12345678,0x11223344,args[5],0x33445566,0,Get(c,"ebp",D),0x55667788,0x66778899};
  var b=new List<byte>();b.Add(0x9c);b.Add(0x60);b.Add(0x89);b.Add(0x25);Imm(b,R+0x90);
  b.Add(0x68);Imm(b,0x13572468);b.Add(0x68);Imm(b,0x24681357);
  for(int i=5;i>=0;i--){b.Add(0x68);Imm(b,args[i]);}
  for(int i=0;i<8;i++)if(i!=4){b.Add((byte)(0xb8+i));Imm(b,seed[i]);}
  b.Add(0x68);Imm(b,0xED7);b.Add(0x9d);
  b.Add(0xe9);Imm(b,T-(B+0xA000+b.Count+4));Bytes(B+0xA000,b.ToArray());
  var site=new List<byte>();site.Add(0xe8);Imm(site,entry-T-5);
  // Record native clobbers and flags BEFORE the original caller's ADD ESP,18h.
  for(int i=0;i<8;i++){site.Add(0x89);site.Add((byte)(5+(i<<3)));Imm(site,R+0xA0+i*4);}
  site.Add(0x9c);site.Add(0x58);Abs(site,0xa3,R+0xC0);
  site.AddRange(new byte[]{0x83,0xc4,0x18});
  site.AddRange(new byte[]{0x89,0x25});Imm(site,R+0xC4);
  site.Add(0x58);Abs(site,0xa3,R+0xC8);site.Add(0x58);Abs(site,0xa3,R+0xCC);
  site.Add(0x61);site.Add(0x9d);site.Add(0x31);site.Add(0xc0);site.Add(0xc3);Bytes(T,site.ToArray());
  ((Entry)Marshal.GetDelegateForFunctionPointer((IntPtr)(B+0xA000),typeof(Entry)))();
  int[] seen=new int[8],returned=new int[8],observedArgs=new int[6];
  for(int i=0;i<8;i++){seen[i]=Read(O+i*4);returned[i]=Read(R+0xA0+i*4);}
  for(int i=0;i<6;i++)observedArgs[i]=Read(O+36+i*4);
  int priorFault=BitConverter.ToInt32(state,36),fault=Read(S+36);
  bool same=true;for(int i=0;i<128;i++)if((i<36||i>=40)&&Marshal.ReadByte((IntPtr)S,i)!=state[i])same=false;
  return new Dictionary<string,object>{{"call","text"},{"args",args},{"seen_args",observedArgs},{"seed",seed},{"seen",seen},{"returned",returned},
   {"incoming_flags",Read(O+32)&0xCD5},{"return_flags",Read(R+0xC0)&0xCD5},{"native_calls",Read(O+64)},
   {"native_return",Read(O+60)},{"esp",Read(R+0xC4)==Read(R+0x90)-8},{"callee_esp",returned[4]==seen[4]+4},
   {"stack_canaries",Read(R+0xC8)==0x24681357&&Read(R+0xCC)==0x13572468},{"state_unchanged_except_owner_fault",same},
   {"fault_before",priorFault},{"fault",fault},
   {"map",Read(G)},{"render",Read(G+4)},{"canaries",IsFill(P-16,16,0xD7)&&IsFill(P+307200,16,0xD7)&&IsFill(F-16,16,0xD7)&&IsFill(F+width*height,16,0xD7)&&IsFill(S+128,16,0xD7)}};
 }
'''
CSHARP = canvas.CSHARP.replace(' static int Main()', INVOKE + '\n static int Main()')
CSHARP = CSHARP.replace('int arg=name==', 'if(name=="text"){steps.Add(TextCall(I(entries[name]),c,width,height));continue;}\n    int arg=name==')
CSHARP = CSHARP.replace('else if(kv.Key=="root_esp")', 'else if(kv.Key=="fault")W(S+36,I(kv.Value));else if(kv.Key=="root_esp")')


def payload(original, owner, bundle, cases, *, wrong_return=False):
    data = canvas.payload(original, owner, cases)
    code = bytearray(bundle.code)
    mapping = {modal.RENDER: canvas.GLOBAL + 4, modal.PRIMARY: canvas.PRIMARY,
               text.TEXT_TARGET: NATIVE, text.TEXT_RETURN: SITE + (6 if wrong_return else 5),
               text.TEXT_FORMAT: FORMAT}
    for row in bundle.relocations:
        if bundle.base_va <= row.target < bundle.base_va + len(bundle.code):
            value = CODE + row.target - bundle.base_va
        elif bundle.modal_state_va <= row.target < bundle.modal_state_va + 128:
            value = canvas.STATE + row.target - bundle.modal_state_va
        elif row.target in owner.entries.values():
            value = canvas.BASE + row.target - owner.base_va
        else:
            value = mapping[row.target]
        if row.kind == 'rel32': value -= CODE + row.offset + 4
        struct.pack_into('<I', code, row.offset, value & 0xFFFFFFFF)
    data['stubs'][str(CODE)] = code.hex()
    data['entries']['text'] = CODE + bundle.entries['quantity'] - bundle.base_va
    # Record exact native entry registers/flags/return and all six cdecl args.
    a = clip._Assembler(NATIVE)
    for reg in range(8):
        a.emit('89' + bytes([5 + reg * 8]).hex()); a.u32(OBS + reg * 4)
    a.emit('9c8f05'); a.u32(OBS + 32)
    a.emit('9c60ff05'); a.u32(OBS + 64)
    for source, dest in [(36, 60)] + [(40 + i * 4, 36 + i * 4) for i in range(6)]:
        a.emit('8b4424' + bytes([source]).hex() + 'a3'); a.u32(OBS + dest)
    a.emit('619d')
    # Native formatter returns EAX and restores EBX/ECX/EDX; preserve its natural
    # result rather than restoring the wrapper's incoming EAX after delegation.
    a.emit('b8'); a.u32(0x1357AABB)
    a.emit('68020200009dc3')
    data['stubs'][str(NATIVE)] = a.finish().hex()
    return data


AVAILABLE = os.name == 'nt' and canvas.CSC.is_file() and Path('C:/Clash/clash95.exe').is_file()


class TextFixture:
    """Helper-only mixin; six independently bounded discovery groups below."""
    @classmethod
    def setUpClass(cls):
        cls.original = Path('C:/Clash/clash95.exe').read_bytes(); cls.cache = {}
        cls.temp = tempfile.TemporaryDirectory(prefix='clash-modal-primary-text-fixture-')
        source = Path(cls.temp.name) / 'Fixture.cs'; source.write_text(CSHARP)
        cls.exe = Path(cls.temp.name) / 'Fixture.exe'
        r = subprocess.run([str(canvas.CSC), '/nologo', '/platform:x86', '/r:System.Web.Extensions.dll',
                            '/out:' + str(cls.exe), str(source)], capture_output=True, text=True,
                           creationflags=subprocess.CREATE_NO_WINDOW, timeout=30)
        if r.returncode: raise AssertionError(r.stdout + r.stderr)

    @classmethod
    def tearDownClass(cls): cls.temp.cleanup()

    @classmethod
    def bundles(cls, w=1024, h=768):
        if (w, h) not in cls.cache:
            candidate, context, _ = builder.build_candidate(cls.original, f'{w}x{h}')
            bundle = text.emit_modal_primary_text(cls.original, candidate,
                base_va=pe.inspect_pe(candidate).image_base + pe.inspect_pe(candidate).image_size, width=w, height=h)
            owner = owner_from_verified_slots(candidate, context['base_candidate'], w, h)
            cls.cache[w, h] = candidate, context, owner, bundle
        return cls.cache[w, h]

    def run_cases(self, cases, w=1024, h=768, *, wrong_return=False):
        candidate, context, owner, bundle = self.bundles(w, h)
        data = payload(self.original, owner, bundle, cases, wrong_return=wrong_return)
        r = subprocess.run([str(self.exe)], input=json.dumps(data), capture_output=True, text=True,
                           creationflags=subprocess.CREATE_NO_WINDOW, timeout=45)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        rows = json.loads(r.stdout)
        for row in rows:
            for s in row:
                self.assertTrue(s['esp'], s); self.assertTrue(s['canaries'], s)
                if s.get('call') != 'text': continue
                for key in ('callee_esp', 'stack_canaries', 'state_unchanged_except_owner_fault'): self.assertTrue(s[key], s)
                self.assertIn(s['fault'], (s['fault_before'], 4) if s['fault_before'] == 0 else (s['fault_before'],), s)
                self.assertEqual(s['native_calls'], 1, s)
                self.assertEqual(s['native_return'], SITE + 5, s)
                self.assertEqual(s['incoming_flags'], canvas.FLAGS & canvas.MASK, s)
                self.assertEqual(s['return_flags'], 0, s)
                self.assertEqual(s['returned'][0], 0x1357AABB, s)
                for reg in range(8):
                    if reg != 4: self.assertEqual(s['seen'][reg], s['seed'][reg], s)
                    if reg not in (0, 4): self.assertEqual(s['returned'][reg], s['seed'][reg], s)
                self.assertEqual(s['seen_args'][3:], s['args'][3:], s)
        return rows

    def check_profile(self, w, h):
        cases = [dict(quantity=value, steps=['try_enter', 'text']) for value in (0, 250, -1, 2147483647, -2147483648)]
        for row in self.run_cases(cases, w, h):
            s = row[-1]
            self.assertEqual(s['seen_args'][:3], [545 + (w - 640) // 2, 613 + (w - 640) // 2, 53 + (h - 480) // 2])
            self.assertEqual((s['map'], s['render'], s['fault']), (canvas.NATIVE, canvas.PRIMARY, 0))


@unittest.skipUnless(AVAILABLE, 'user-owned original and Windows x86 fixture compiler required')
class PrimaryTextTests(TextFixture, unittest.TestCase):
    def test_1024_centered_coordinates_signed_quantities_and_native_cdecl_abi(self):
        self.check_profile(1024, 768)

    def test_wrong_shape_render_owner_fault_and_inactive_keep_all_native_arguments(self):
        cases = [dict(steps=['text']), dict(text_render=canvas.NATIVE, steps=['try_enter', 'text'])]
        for key, value in (('left', 544), ('right', 614), ('y', 54), ('align', 2), ('format', FORMAT + 4), ('ebp', 0)):
            cases.append(dict({key: value}, steps=['try_enter', 'text']))
        for mutation in ({'fault': 1}, {'tid': 124}, {'phase': 2}, {'native_width': 800},
                         {'map_pointer': canvas.PHYSICAL}, {'native_pixels': canvas.PIXELS + 4}, {'native_com': 1}):
            expected_fault = 1 if 'fault' in mutation else 0 if 'phase' in mutation else 4
            cases.append(dict(expected_fault=expected_fault, steps=['try_enter', mutation, 'text']))
        cases += [dict(allocation_failure=n, steps=['try_enter', 'text']) for n in (1, 2)]
        for case, row in zip(cases, self.run_cases(cases)):
            self.assertEqual(row[-1]['seen_args'], row[-1]['args'])
            if 'expected_fault' in case: self.assertEqual(row[-1]['fault'], case['expected_fault'])
        row = self.run_cases([dict(steps=['try_enter', 'text'])], wrong_return=True)[0]
        self.assertEqual(row[-1]['seen_args'], row[-1]['args'])

    def test_admission_relocations_sources_and_native_windows(self):
        candidate, context, owner, bundle = self.bundles()
        self.assertEqual(bundle.candidate_sha256, hashlib.sha256(candidate).hexdigest())
        self.assertEqual(bundle.source_contract['source_hashes'], dict(context['source_hashes'], **{
            'src/patcher/framed_modal_primary_text.py': hashlib.sha256(Path(text.__file__).read_bytes()).hexdigest()}))
        self.assertEqual(len(bundle.hook_sites), 1); self.assertFalse(bundle.installation_ready)
        hook = bundle.hook_sites[0]
        self.assertEqual((hook.va, hook.offset, hook.old), (0x432C66, 0x32066, bytes.fromhex('e8e594fdff')))
        self.assertEqual(hook.new[0], 0xE8)
        self.assertEqual(hook.va + 5 + struct.unpack('<i', hook.new[1:])[0], bundle.entries['quantity'])
        self.assertEqual(bundle.modal_state_va, owner.state_va)
        self.assertEqual(bundle.modal_entry_vas, owner.entries)
        self.assertGreater(len(clip.absolute_relocation_offsets(bundle)), 0)
        for va, size, digest in text.NATIVE_SPANS:
            self.assertEqual(hashlib.sha256(modal._read(candidate, va, size)).hexdigest(), digest)
        args = dict(base_va=bundle.base_va, width=1024, height=768)
        with self.assertRaisesRegex(ValueError, 'original'):
            text.emit_modal_primary_text(bytes(len(self.original)), candidate, **args)
        for dimension in ('width', 'height'):
            invalid = dict(args); invalid[dimension] = float(invalid[dimension])
            with self.assertRaisesRegex(ValueError, 'integer'):
                text.emit_modal_primary_text(self.original, candidate, **invalid)
        for base in (bundle.base_va + 1, bundle.base_va - 4096, True):
            with self.subTest(base=base), self.assertRaisesRegex(ValueError, 'aligned'):
                text.emit_modal_primary_text(self.original, candidate, **dict(args, base_va=base))
        for va in (text.TEXT_CALL, text.TEXT_TARGET, 0x40BEE0, 0x40BC00, text.TEXT_FORMAT):
            changed = bytearray(candidate); view = pe.inspect_pe(candidate)
            changed[view.file_offset(va - view.image_base, 1)] ^= 1
            with self.subTest(va=hex(va)), self.assertRaisesRegex(ValueError, 'native'):
                text.emit_modal_primary_text(self.original, bytes(changed), **args)

    def test_unknown_candidate_with_unchanged_native_call_is_rejected_by_whole_reconstruction(self):
        candidate, context, owner, bundle = self.bundles()
        changed = bytearray(candidate); changed[-1] ^= 1
        with self.assertRaisesRegex(ValueError, 'exact primary-v1 candidate'):
            text.emit_modal_primary_text(self.original, bytes(changed), base_va=bundle.base_va, width=1024, height=768)


@unittest.skipUnless(AVAILABLE, 'user-owned original and Windows x86 fixture compiler required')
class PrimaryText800Tests(TextFixture, unittest.TestCase):
    def test_800_centered_coordinates_signed_quantities_and_native_cdecl_abi(self): self.check_profile(800, 600)


@unittest.skipUnless(AVAILABLE, 'user-owned original and Windows x86 fixture compiler required')
class PrimaryText720Tests(TextFixture, unittest.TestCase):
    def test_720_centered_coordinates_signed_quantities_and_native_cdecl_abi(self): self.check_profile(1280, 720)


@unittest.skipUnless(AVAILABLE, 'user-owned original and Windows x86 fixture compiler required')
class PrimaryText960Tests(TextFixture, unittest.TestCase):
    def test_960_centered_coordinates_signed_quantities_and_native_cdecl_abi(self): self.check_profile(1280, 960)


@unittest.skipUnless(AVAILABLE, 'user-owned original and Windows x86 fixture compiler required')
class PrimaryText1080Tests(TextFixture, unittest.TestCase):
    def test_1080_centered_coordinates_signed_quantities_and_native_cdecl_abi(self): self.check_profile(1920, 1080)


@unittest.skipUnless(AVAILABLE, 'user-owned original and Windows x86 fixture compiler required')
class PrimaryTextFractionalTests(TextFixture, unittest.TestCase):
    def test_802_centered_coordinates_signed_quantities_and_native_cdecl_abi(self): self.check_profile(802, 602)


if __name__ == '__main__':
    # Default discovers every group. The aggregate registry can name each
    # dotted class separately under its unchanged 600-second per-suite budget.
    unittest.main(verbosity=2)
