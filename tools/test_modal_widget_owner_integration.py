"""Execute installed widget guards with the actual inherited owner in x86.

The exact original-backed widget builder authenticates every ancestor. This
fixture relocates its installed guards and inherited modal code into synthetic
memory, including real is_active, try_enter and try_leave instructions. The
existing canvas fixture supplies labeled allocation/thread/game-body recorders
and cloned original constructors/destructors. No game, debugger, wrapper,
input, pixels from gameplay, or runtime acceptance is involved.

Windows x86 .NET and the user-owned original are required. The default profile
is 1024x768; CLASH_WIDGET_RESOLUTION may select another canonical profile.
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
from src.patcher import framed_modal_canvas as modal
from src.patcher import partial_tile_clip as clip
import build_framed_modal_widgets_candidate as builder
import test_framed_modal_canvas as canvas
from test_framed_modal_primary import owner_from_verified_slots
from test_modal_widget_bounds import comparison_flags

ORIGINAL = Path('C:/Clash/clash95.exe')
CODE, SINGLE, LIST, DESCRIPTOR = (canvas.BASE + n for n in (0xB000, 0xAE00, 0xAF00, 0xF0200))
INVOKE = r'''
 static Dictionary<string,object> WidgetCall(int entry,string name,Dictionary<string,object> c,int width,int height){
  const int X=B+0xF0200;
  W(G+4,Get(c,"widget_render",Read(G+4)));Fill(X,53,0x91);W(X,Get(c,"x",1000));
  byte[] state=new byte[128],globals=new byte[28],descriptor=new byte[53],native=new byte[188],physical=new byte[188];
  Marshal.Copy((IntPtr)S,state,0,state.Length);Marshal.Copy((IntPtr)G,globals,0,globals.Length);
  Marshal.Copy((IntPtr)X,descriptor,0,descriptor.Length);Marshal.Copy((IntPtr)N,native,0,native.Length);Marshal.Copy((IntPtr)H,physical,0,physical.Length);
  int[] seed={name=="single"?X:0x12345678,name=="list"?X:0x11223344,0x22334455,0x33445566,0,0x44556677,0x55667788,0x66778899};
  var b=new List<byte>();b.Add(0x9c);b.Add(0x60);b.Add(0x89);b.Add(0x25);Imm(b,R+0x90);
  b.Add(0x68);Imm(b,0x13572468);b.Add(0x68);Imm(b,0x24681357);
  for(int i=0;i<8;i++)if(i!=4){b.Add((byte)(0xb8+i));Imm(b,seed[i]);}
  b.Add(0x68);Imm(b,Get(c,"flags",0xED7));b.Add(0x9d);
  b.Add(0xe8);Imm(b,entry-(B+0xA000+b.Count+4));
  for(int i=0;i<8;i++){b.Add(0x89);b.Add((byte)(5+(i<<3)));Imm(b,R+0xA0+i*4);}
  b.Add(0x9c);b.Add(0x58);Abs(b,0xa3,R+0xC0);b.Add(0x89);b.Add(0x25);Imm(b,R+0xC4);
  b.Add(0x58);Abs(b,0xa3,R+0xC8);b.Add(0x58);Abs(b,0xa3,R+0xCC);
  b.Add(0x61);b.Add(0x9d);b.Add(0x31);b.Add(0xc0);b.Add(0xc3);Bytes(B+0xA000,b.ToArray());
  ((Entry)Marshal.GetDelegateForFunctionPointer((IntPtr)(B+0xA000),typeof(Entry)))();
  int[] returned=new int[8];for(int i=0;i<8;i++)returned[i]=Read(R+0xA0+i*4);
  bool same=true;for(int i=0;i<128;i++)if((i<36||i>=40)&&Marshal.ReadByte((IntPtr)S,i)!=state[i])same=false;
  bool other=true;int[] addresses={G,X,N,H};byte[][] snapshots={globals,descriptor,native,physical};
  for(int n=0;n<addresses.Length;n++)for(int i=0;i<snapshots[n].Length;i++)if(Marshal.ReadByte((IntPtr)addresses[n],i)!=snapshots[n][i])other=false;
  return new Dictionary<string,object>{{"call",name},{"seed",seed},{"returned",returned},{"flags",Read(R+0xC0)&0xCD5},
   {"expected_esp",Read(R+0x90)-8},{"esp",Read(R+0xC4)==Read(R+0x90)-8},
   {"stack_canaries",Read(R+0xC8)==0x24681357&&Read(R+0xCC)==0x13572468},
   {"state_unchanged_except_owner_fault",same},{"headers_globals_descriptor_unchanged",other},
   {"fault_before",BitConverter.ToInt32(state,36)},{"fault",Read(S+36)},{"phase",Read(S)},
   {"map",Read(G)},{"render",Read(G+4)},
   {"canaries",IsFill(P-16,16,0xD7)&&IsFill(P+307200,16,0xD7)&&IsFill(F-16,16,0xD7)&&IsFill(F+width*height,16,0xD7)&&IsFill(S+128,16,0xD7)}};
 }
'''
CSHARP = canvas.CSHARP.replace(' static int Main()', INVOKE + '\n static int Main()')
CSHARP = CSHARP.replace('int arg=name==',
    'if(name=="single"||name=="list"){steps.Add(WidgetCall(I(entries[name]),name,c,width,height));continue;}\n    int arg=name==')
CSHARP = CSHARP.replace('else if(kv.Key=="root_esp")',
    'else if(kv.Key=="fault")W(S+36,I(kv.Value));else if(kv.Key=="root_esp")')


def payload(original, candidate, metadata, owner, cases):
    """Map real installed instructions; no ownership validator replacement."""
    data = canvas.payload(original, owner, cases)
    base, size = metadata['code_va'], metadata['code_bytes']
    code = bytearray(modal._read(candidate, base, size))
    if hashlib.sha256(code).hexdigest() != metadata['code_sha256']:
        raise AssertionError('installed widget code hash differs')
    for row in metadata['relocations']:
        target = row['target']
        if base <= target < base + size:
            value = CODE + target - base
        elif owner.state_va <= target < owner.state_va + 128:
            value = canvas.STATE + target - owner.state_va
        elif target == metadata['modal_entry_vas']['is_active'] == owner.entries['is_active']:
            value = canvas.BASE + target - owner.base_va
        elif target == modal.RENDER:
            value = canvas.GLOBAL + 4
        else:
            raise AssertionError('unexpected widget relocation target: ' + hex(target))
        if row['kind'] == 'rel32': value -= CODE + row['offset'] + 4
        struct.pack_into('<I', code, row['offset'], value & 0xFFFFFFFF)
    data['stubs'][str(CODE)] = code.hex()
    for name, site, hook in zip(('single', 'list'), (SINGLE, LIST), metadata['hooks']):
        installed = bytearray(modal._read(candidate, hook['va'], 6))
        if installed.hex() != hook['new_hex'] or installed[0] != 0xE8 or installed[5] != 0x90:
            raise AssertionError('installed widget CALL/NOP differs')
        target = hook['va'] + 5 + struct.unpack_from('<i', installed, 1)[0]
        if target != metadata['widget_entry_vas'][name]:
            raise AssertionError('installed widget hook target differs')
        struct.pack_into('<i', installed, 1, CODE + target - base - site - 5)
        # This RET is fixture continuation only. The genuine candidate's
        # original JL is checked separately; the fixture records returned CMP
        # flags before any arithmetic or managed-code continuation executes.
        data['stubs'][str(site)] = (installed + b'\xc3').hex()
        data['entries'][name] = site
    return data


AVAILABLE = os.name == 'nt' and canvas.CSC.is_file() and ORIGINAL.is_file()


@unittest.skipUnless(AVAILABLE, 'user-owned original and Windows x86 .NET compiler required')
class WidgetOwnerIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = ORIGINAL.read_bytes()
        cls.resolution = os.environ.get('CLASH_WIDGET_RESOLUTION', '1024x768')
        if cls.resolution not in builder.complete.RESOLUTIONS:
            raise ValueError('canonical CLASH_WIDGET_RESOLUTION required')
        cls.width, cls.height = map(int, cls.resolution.split('x'))
        cls.candidate, cls.metadata, _ = builder.build_candidate(cls.original, cls.resolution)
        slots = cls.metadata['base_candidate']['base_candidate']['base_candidate']
        cls.owner = owner_from_verified_slots(cls.candidate, slots, cls.width, cls.height)
        cls.temp = tempfile.TemporaryDirectory(prefix='clash-widget-real-owner-')
        cls.addClassCleanup(cls.temp.cleanup)
        source = Path(cls.temp.name) / 'Fixture.cs'; source.write_text(CSHARP)
        cls.exe = Path(cls.temp.name) / 'Fixture.exe'
        result = subprocess.run([str(canvas.CSC), '/nologo', '/platform:x86', '/r:System.Web.Extensions.dll',
            '/out:' + str(cls.exe), str(source)], capture_output=True, text=True,
            creationflags=subprocess.CREATE_NO_WINDOW, timeout=30)
        if result.returncode: raise AssertionError(result.stdout + result.stderr)
        print('Authenticated widget/real-owner fixture:', cls.resolution, cls.metadata['candidate_sha256'], flush=True)

    def run_cases(self, cases):
        data = payload(self.original, self.candidate, self.metadata, self.owner, cases)
        result = subprocess.run([str(self.exe)], input=json.dumps(data), capture_output=True, text=True,
            creationflags=subprocess.CREATE_NO_WINDOW, timeout=45)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        rows = json.loads(result.stdout)
        self.assertEqual(len(rows), len(cases))
        for case, steps in zip(cases, rows):
            widgets = [step for step in steps if step.get('call') in ('single', 'list')]
            self.assertEqual(len(widgets), sum(step in ('single', 'list') for step in case['steps'] if isinstance(step, str)))
            for step in steps:
                self.assertTrue(step['esp'], step); self.assertTrue(step['canaries'], step)
                if 'call' not in step:
                    self.assertTrue(step['gprs'], step)
                    self.assertEqual(step['flags'], canvas.FLAGS & canvas.MASK, step)
                    continue
                for key in ('stack_canaries', 'state_unchanged_except_owner_fault', 'headers_globals_descriptor_unchanged'):
                    self.assertTrue(step[key], step)
                expected = list(step['seed']); expected[4] = step['expected_esp']
                self.assertEqual(step['returned'], expected, step)
        self.assertEqual(ORIGINAL.read_bytes(), self.original)
        return [[s for s in row if s.get('call') in ('single', 'list')] for row in rows]

    def assert_compare(self, step, x, bound, flags=0xED7):
        expected = comparison_flags(x, bound, flags & 0x400)
        self.assertEqual(step['flags'], expected, step)
        self.assertEqual(((step['flags'] >> 7) ^ (step['flags'] >> 11)) & 1, int(x < bound), step)

    def test_actual_installed_guards_and_real_owner_source_binding(self):
        self.assertEqual(self.metadata['candidate_sha256'], hashlib.sha256(self.candidate).hexdigest())
        self.assertEqual(self.metadata['modal_entry_vas'], self.owner.entries)
        self.assertEqual(self.metadata['modal_state_va'], self.owner.state_va)
        self.assertEqual(self.metadata['source_hashes'],
            {name: hashlib.sha256((builder.ROOT / name).read_bytes()).hexdigest() for name in self.metadata['source_hashes']})
        for va, branch in ((0x419D69, b'\x7c\x02'), (0x419D92, b'\x7c\x0f')):
            self.assertEqual(modal._read(self.candidate, va, 2), branch)
            self.assertEqual(modal._read(self.original, va, 2), branch)
        data = payload(self.original, self.candidate, self.metadata, self.owner, [])
        self.assertEqual(data['code'], canvas.payload(self.original, self.owner, [])['code'])
        self.assertEqual(set(data['stubs']) - set(canvas.payload(self.original, self.owner, [])['stubs']),
                         {str(CODE), str(SINGLE), str(LIST)})

    def test_owned_native_boundaries_and_exact_cmp_abi(self):
        coordinates = (-2147483648, -1, 0, 639, 640, 999, 1000, self.width - 1, self.width, 2147483647)
        cases = [dict(x=x, flags=flags, steps=['try_enter', 'single', 'list'])
                 for x in coordinates for flags in (0x202, 0xED7)]
        for case, row in zip(cases, self.run_cases(cases)):
            for step in row:
                self.assert_compare(step, case['x'], 640, case['flags'])
                self.assertEqual((step['phase'], step['fault'], step['map'], step['render']),
                                 (1, 0, canvas.NATIVE, canvas.NATIVE))

    def test_primary_physical_inactive_and_failed_allocation_keep_hd_width(self):
        contexts = [dict(steps=[]), dict(widget_render=canvas.PRIMARY, steps=['try_enter']),
                    dict(widget_render=canvas.PHYSICAL, steps=['try_enter']),
                    dict(widget_render=canvas.PRIMARY, steps=['try_enter', {'tid': 124}])]
        contexts += [dict(allocation_failure=n, steps=['try_enter']) for n in (1, 2)]
        cases = [dict(context, x=x, steps=context['steps'] + ['single', 'list'])
                 for context in contexts for x in (639, 640, 1000, self.width - 1, self.width)]
        for case, row in zip(cases, self.run_cases(cases)):
            for step in row:
                self.assert_compare(step, case['x'], self.width)
                self.assertEqual(step['fault'], 0)

    def test_invalid_real_ownership_latches_fault_and_suppresses_both_branches(self):
        mutations = [({'fault': n}, n) for n in (1, 4, 7)] + [({'phase': n}, 0) for n in (0, 2)]
        mutations += [(mutation, 4) for mutation in (
            {'tid': 124}, {'native_width': 800}, {'map_pointer': canvas.PHYSICAL},
            {'native_pixels': canvas.PIXELS + 4}, {'native_com': 1},
            {'physical_pixels': canvas.PHYSPIX + 4}, {'owned_native_pixels': canvas.PIXELS + 4},
            {'entered_physical_pixels': canvas.PHYSPIX + 4})]
        cases = [dict(x=x, steps=['try_enter', mutation, *order], expected_fault=fault)
                 for mutation, fault in mutations for x in (-1, 0, 639, 1000)
                 for order in (('single', 'list'), ('list', 'single'))]
        for case, row in zip(cases, self.run_cases(cases)):
            for step in row:
                self.assert_compare(step, case['x'], case['x'])
                self.assertEqual(step['fault'], case['expected_fault'])
            self.assertEqual(row[-1]['fault_before'], case['expected_fault'])

    def test_real_owner_leave_restores_physical_width(self):
        cases = [dict(x=1000, render_primary=primary,
                      steps=['try_enter', 'single', 'list', 'try_leave', 'single', 'list']) for primary in (0, 1)]
        for case, row in zip(cases, self.run_cases(cases)):
            for step in row[:2]: self.assert_compare(step, 1000, 640)
            for step in row[2:]:
                self.assert_compare(step, 1000, self.width)
                self.assertEqual((step['phase'], step['fault'], step['map'], step['render']),
                                 (0, 0, canvas.PHYSICAL, canvas.PRIMARY if case['render_primary'] else canvas.PHYSICAL))


if __name__ == '__main__': unittest.main(verbosity=2)
