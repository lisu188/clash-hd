from __future__ import annotations

from contextlib import redirect_stdout, redirect_stderr
from dataclasses import replace
import copy
import io
import errno
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
from src.patcher import framed_camera as camera
from src.patcher import framed_full_paint as full
from src.patcher import initial_map_paint as initial
from src.patcher import partial_tile_hooks as hooks
from src.patcher import partial_tile_clip as clip
from src.patcher import pe_extension as pe
from src.patcher.framed_viewport import FramedViewport
import build_framed_camera_candidate as cli
from test_pe_extension import synthetic_pe

SIZES = ('800x600', '802x602', '1024x768', '1280x720', '1280x960', '1366x768',
         '1920x1080', '2560x1440', '3440x1440', '3840x2160')
SNAP = 0x22300
DATA_SIZE = 0x23000


def source_emitted_bundle(resolution):
    width, height = map(int, resolution.split('x'))
    base = 0x603000
    layout = FramedViewport(width, height)
    candidate = full.FULL_ENTRY_OLD.ljust(16, b'\0') + (
        b'\xe9' + struct.pack('<i', full.OLD_C5_VA - (full.FRAME_GATE_VA + 5)) + b'\x90'*3).ljust(16, b'\0') + initial.HOOK_OLD
    bundle = hooks.HookBundle(base, bytes.fromhex('b801000000c3'),
        {'composition_guard': base, 'clipped_vtable': base + 0x800, 'draw_frame': base}, (), width, height,
        candidate_sha256=camera.sha(candidate))
    offsets = {full.FULL_ENTRY_VA: 0, full.FRAME_GATE_VA: 16, initial.HOOK_VA: 32}
    with (patch.object(hooks, '_verify_contract'), patch.object(clip, 'file_offset', side_effect=lambda data, va, size: offsets[va]),
          patch.object(clip, '_original_highlow_fields', return_value=set()), patch.object(initial, '_verify_initial_contract')):
        bundle = full.append_full_entry(b'non-game-fixture', candidate, bundle, layout=layout)
        with patch.object(hooks, 'emit_hook_bundle', return_value=bundle):
            bundle = initial.emit_hook_bundle(b'non-game-fixture', candidate, base_va=base, width=width, height=height, layout=layout)
    return replace(bundle, code=bundle.code.ljust(0x900, b'\x90'))


def synthetic_parent(resolution='1280x720'):
    bundle = source_emitted_bundle(resolution)
    data = bytearray(synthetic_pe())
    opt = 0x88
    struct.pack_into('<I', data, opt + 56, 0x203000)
    struct.pack_into('<I', data, opt + 136, 0x202000)
    struct.pack_into('<I', data, opt + 224 + 40 + 16, 0x200000)
    struct.pack_into('<I', data, opt + 224 + 80 + 12, 0x202000)
    result = pe._extend_verified_image(bytes(data), code=bundle.code, code_va=bundle.base_va,
        relocations=bundle.relocations, binding={'stage': camera.PARENT_STAGE, 'resolution': resolution})
    metadata = dict(result.metadata, entry_vas=bundle.entries, minimap_viewport=True, framed_validation=True,
        extension_payload_size=len(bundle.code), extension_payload_sha256=camera.sha(bundle.code))
    return result.image, metadata


class CameraByteTests(unittest.TestCase):
    def test_authenticated_source_pins_stay_unchanged(self):
        status = camera.source_status()
        self.assertTrue(status['passed'])
        self.assertEqual(len(status['checks']), 14)
        self.assertEqual(status['builder_sha256'], camera.PARENT_BUILDER_SHA256)

    def test_old_gate_matches_actual_existing_emitters_at_every_resolution(self):
        for key in SIZES:
            with self.subTest(resolution=key):
                bundle = source_emitted_bundle(key)
                layout = FramedViewport(*map(int, key.split('x')))
                for kind, name, reject in (('full_redraw', 'hook_framed_full_entry', 'framed_full_reject'),
                                            ('initial_paint', 'initial_paint_admission', 'initial_admission_reject')):
                    start = bundle.entries[name]
                    prefix = camera._prefix(kind, start, bundle.entries)
                    offset = start - bundle.base_va
                    self.assertEqual(bundle.code[offset:offset+len(prefix)], prefix)
                    offset += len(prefix)
                    old = camera.old_gate(layout, bundle.base_va+offset, bundle.entries[reject])
                    self.assertEqual(bundle.code[offset:offset+124], old)

    def test_only_two_equal_length_guard_spans_change_and_reconstruct_image(self):
        for key in SIZES:
            with self.subTest(resolution=key):
                parent, metadata = synthetic_parent(key)
                frozen = copy.deepcopy(metadata)
                image, report = camera._upgrade_verified_parent(parent, metadata, key)
                self.assertEqual(metadata, frozen)
                self.assertEqual(len(image), len(parent))
                self.assertEqual(pe.inspect_pe(image), pe.inspect_pe(parent))
                self.assertEqual(len(report['edits']), 2)
                changed, rebuilt = set(), bytearray(parent)
                for edit in report['edits']:
                    offset = edit['offset']
                    old, new = bytes.fromhex(edit['old_hex']), bytes.fromhex(edit['new_hex'])
                    self.assertEqual((len(old), len(new)), (124, 124))
                    self.assertEqual(parent[offset:offset+124], old)
                    self.assertEqual(edit['va'], 0x400000 + edit['rva'])
                    rebuilt[offset:offset+124] = new
                    changed.update(range(offset, offset+124))
                self.assertEqual(bytes(rebuilt), image)
                self.assertTrue(all(i in changed for i, (a, b) in enumerate(zip(parent, image)) if a != b))
                self.assertEqual(report['output_sha256'], camera.sha(image))
                self.assertEqual(report['stage'], camera.STAGE)
                self.assertNotEqual(report['stage'], metadata['stage'])
                for key in ('game_runtime_executed', 'manual_input_proof', 'promotion_ready', 'parent_probe_reusable'):
                    self.assertIs(report[key], False)

    def test_unknown_original_is_rejected_before_source_or_parent_builder(self):
        with patch.object(camera, 'source_status') as source:
            for data in (b'', b'non-game fixture', bytearray(10), None):
                with self.subTest(data=data), self.assertRaises(ValueError):
                    camera.build_candidate(data, '1280x720')
            source.assert_not_called()

    def test_changed_old_gate_and_entry_prefix_fail_without_mutating_input(self):
        parent, metadata = synthetic_parent()
        for name, delta in (('hook_framed_full_entry', 0), ('hook_framed_full_entry', 37),
                            ('initial_paint_admission', 0), ('initial_paint_admission', 55)):
            mutated = bytearray(parent)
            pos = pe.inspect_pe(parent).file_offset(metadata['entry_vas'][name] - 0x400000 + delta, 1)
            mutated[pos] ^= 1
            mutated = bytes(mutated)
            tampered = copy.deepcopy(metadata)
            tampered['output_sha256'] = camera.sha(mutated)
            code_offset = pe.inspect_pe(parent).file_offset(metadata['code_va'] - 0x400000, metadata['code_bytes'])
            tampered['extension_payload_sha256'] = tampered['code_sha256'] = camera.sha(mutated[code_offset:code_offset+metadata['code_bytes']])
            with self.subTest(name=name, delta=delta), self.assertRaisesRegex(ValueError, 'prefix|old-byte'):
                camera._upgrade_verified_parent(mutated, tampered, '1280x720')

    def test_wrong_profile_source_shape_and_payload_identity_are_rejected(self):
        parent, metadata = synthetic_parent()
        for key, value in (('stage', camera.STAGE), ('resolution', '800x600'), ('minimap_viewport', False),
                           ('framed_validation', False), ('output_sha256', '0'*64), ('extension_payload_sha256', '0'*64),
                           ('extension_payload_size', 0), ('code_bytes', True), ('code_va', True), ('entry_vas', {}), ('relocations', None)):
            with self.subTest(key=key), self.assertRaises(ValueError):
                camera._upgrade_verified_parent(parent, metadata | {key: value}, '1280x720')
        for key in ('1280X720', '01280x0720', '1367x768'):
            with self.assertRaises(ValueError):
                camera._upgrade_verified_parent(parent, metadata, key)

    def test_relocation_overlap_is_rejected_instead_of_repinning(self):
        parent, metadata = synthetic_parent()
        va = metadata['entry_vas']['hook_framed_full_entry'] + 37
        altered = copy.deepcopy(metadata)
        altered['relocations'].append({'offset': va-metadata['code_va'], 'kind': 'rel32', 'target': va, 'purpose': 'synthetic conflict'})
        with self.assertRaisesRegex(ValueError, 'relocation'):
            camera._upgrade_verified_parent(parent, altered, '1280x720')
        parsed = pe.inspect_pe(parent)
        reloc, locations = pe._old_relocations(parent, parsed)
        with patch.object(pe, '_old_relocations', return_value=(reloc, locations + (va-0x400000,))):
            with self.assertRaisesRegex(ValueError, 'HIGHLOW'):
                camera._upgrade_verified_parent(parent, metadata, '1280x720')

    def test_repeated_application_is_not_accepted_as_parent(self):
        parent, metadata = synthetic_parent()
        image, report = camera._upgrade_verified_parent(parent, metadata, '1280x720')
        with self.assertRaises(ValueError):
            camera._upgrade_verified_parent(image, report, '1280x720')
        forged = dict(metadata, output_sha256=camera.sha(image), extension_payload_sha256=report['extension_payload_sha256'],
                      code_sha256=report['extension_payload_sha256'])
        with self.assertRaisesRegex(ValueError, 'old-byte'):
            camera._upgrade_verified_parent(image, forged, '1280x720')

    def test_rebase_invariance_and_allocation_bounds(self):
        layout = FramedViewport(3840, 2160)
        for emitter in (camera.old_gate, camera.camera_gate):
            self.assertEqual(emitter(layout, 0x600000, 0x600500), emitter(layout, 0x700000, 0x700500))
            for va, reject in ((True, 0x500000), (0xFFFFFF80, 0x600000), (0x600000, 0x600001), (-1, 0x500000)):
                with self.assertRaises(ValueError):
                    emitter(layout, va, reject)


class CameraCLITests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='clash-camera-cli-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.game = self.root / 'game'
        self.game.mkdir()
        self.original = self.game / 'clash95.exe'
        self.original.write_bytes(b'unknown original fixture')

    def test_preflight_never_creates_files_even_with_output_arguments(self):
        with patch.object(cli.camera, 'build_candidate', return_value=(b'image', {'output_sha256': camera.sha(b'image')})):
            with redirect_stdout(io.StringIO()):
                code = cli.main(['--original', str(self.original), '--resolution', '1280x720', '--preflight',
                                 '--output', str(self.original), '--report-json', str(self.root/'missing/report.json')])
        self.assertEqual(code, 0)
        self.assertEqual(self.original.read_bytes(), b'unknown original fixture')
        self.assertFalse((self.root/'missing').exists())

    def test_unsafe_existing_and_game_outputs_fail_before_build(self):
        for output, report in ((self.original, self.root/'report.json'), (self.root/'a.exe', self.root/'a.exe'),
                               (self.root/'wrong.txt', self.root/'a.json'), (ROOT/'x.exe', ROOT/'x.json')):
            with patch.object(cli.camera, 'build_candidate') as build, redirect_stderr(io.StringIO()):
                code = cli.main(['--original', str(self.original), '--resolution', '1280x720', '--output', str(output), '--report-json', str(report)])
            self.assertEqual(code, 1)
            build.assert_not_called()

    def test_unknown_executable_is_not_a_successful_preflight(self):
        with redirect_stderr(io.StringIO()), redirect_stdout(io.StringIO()):
            code = cli.main(['--original', str(self.original), '--resolution', '1366x768', '--preflight'])
        self.assertEqual(code, 1)

    def test_exclusive_creation_rejects_a_racing_file(self):
        output, report = self.root/'new.exe', self.root/'new.json'
        def build(*args):
            output.write_bytes(b'preexisting data from another writer')
            return b'new', {'output_sha256': camera.sha(b'new')}
        with (patch.object(cli, '_outputs', return_value=(output, report)), patch.object(cli.camera, 'build_candidate', side_effect=build),
              redirect_stderr(io.StringIO())):
            code = cli.main(['--original', str(self.original), '--resolution', '1280x720', '--output', str(output), '--report-json', str(report)])
        self.assertEqual(code, 1)
        self.assertEqual(output.read_bytes(), b'preexisting data from another writer')
        self.assertFalse(report.exists())


LINUX_WORKER = r'''
typedef unsigned int U;
static unsigned char code[4096] __attribute__((aligned(4096)));
static unsigned char data[0x23000];
static int syscall3(int n, int a, int b, int c) {
    int r; __asm__ volatile("int $0x80" : "=a"(r) : "a"(n), "b"(a), "c"(b), "d"(c) : "memory", "cc"); return r;
}
static int readall(void *p, int n) {
    unsigned char *q=p; while(n) { int k=syscall3(3,0,(int)q,n); if(k<=0)return 0; q+=k;n-=k;}return 1;
}
void _start(void) {
    U h[2], out[15];
    if(!readall(h,8)||!h[0]||h[0]>4096||h[1]>10000||!readall(code,h[0]))goto fail;
    if(syscall3(125,(int)code,4096,5))goto fail;
    for(U c=0;c<h[1];c++) {
        for(U i=0;i<sizeof(data);i++)data[i]=0xA5;
        if(!readall(data+0x222e0,16))goto fail;
        out[0]=((int(*)(void*))code)(data);
        for(U j=0;j<4;j++)out[j+1]=((U*)(data+0x222e0))[j];
        for(U j=0;j<9;j++)out[j+5]=((U*)(data+0x22300))[j];
        out[14]=0;
        for(U i=0;i<sizeof(data);i++)
            if(!(i>=0x222e0&&i<0x222f0)&&!(i>=0x22300&&i<0x22324)&&data[i]!=0xA5)out[14]=1;
        if(syscall3(4,1,(int)out,60)!=60)goto fail;
    }
    syscall3(1,0,0,0);
fail: syscall3(1,2,0,0);
}
'''
WINDOWS_WORKER = r'''
using System; using System.IO; using System.Runtime.InteropServices;
public class Native {
[DllImport("kernel32.dll", SetLastError=true)] static extern IntPtr VirtualAlloc(IntPtr a,UIntPtr n,uint t,uint p);
[DllImport("kernel32.dll", SetLastError=true)] static extern bool VirtualProtect(IntPtr a,UIntPtr n,uint p,out uint old);
[DllImport("kernel32.dll")] static extern bool VirtualFree(IntPtr a,UIntPtr n,uint t);
[DllImport("kernel32.dll")] static extern bool FlushInstructionCache(IntPtr p,IntPtr a,UIntPtr n);
[DllImport("kernel32.dll")] static extern IntPtr GetCurrentProcess();
[UnmanagedFunctionPointer(CallingConvention.Cdecl)] delegate int Gate(IntPtr data);
public static int Main() {
IntPtr code=IntPtr.Zero, data=IntPtr.Zero;
try {
var r=new BinaryReader(Console.OpenStandardInput());var w=new BinaryWriter(Console.OpenStandardOutput());
int size=r.ReadInt32(), count=r.ReadInt32();if(size<1||size>4096||count<0||count>10000)return 2;
byte[] bytes=r.ReadBytes(size);if(bytes.Length!=size)return 2;
code=VirtualAlloc(IntPtr.Zero,(UIntPtr)4096,0x3000,4); if(code==IntPtr.Zero)return 2;
Marshal.Copy(bytes,0,code,size);uint old;if(!VirtualProtect(code,(UIntPtr)4096,0x20,out old))return 2;
if(!FlushInstructionCache(GetCurrentProcess(),code,(UIntPtr)size))return 2;
Gate gate=(Gate)Marshal.GetDelegateForFunctionPointer(code,typeof(Gate));
data=Marshal.AllocHGlobal(0x23000);byte[] buffer=new byte[0x23000];
for(int c=0;c<count;c++) {
for(int i=0;i<buffer.Length;i++)buffer[i]=0xA5;
byte[] state=r.ReadBytes(16);if(state.Length!=16)return 2;Array.Copy(state,0,buffer,0x222e0,16);
Marshal.Copy(buffer,0,data,buffer.Length);int result=gate(data);Marshal.Copy(data,buffer,0,buffer.Length);
w.Write(result);for(int j=0;j<4;j++)w.Write(BitConverter.ToInt32(buffer,0x222e0+j*4));
for(int j=0;j<9;j++)w.Write(BitConverter.ToInt32(buffer,0x22300+j*4));
int bad=0;for(int i=0;i<buffer.Length;i++)if(!(i>=0x222e0&&i<0x222f0)&&!(i>=0x22300&&i<0x22324)&&buffer[i]!=0xA5)bad=1;
w.Write(bad);
}w.Flush();return 0;
}catch(Exception e){Console.Error.WriteLine(e);return 2;}
finally {if(data!=IntPtr.Zero)Marshal.FreeHGlobal(data);if(code!=IntPtr.Zero)VirtualFree(code,UIntPtr.Zero,0x8000);}
}}
'''


def native_function(layout, new=True, base=0x100000):
    outer = bytearray(bytes.fromhex('9c608b54242852'))
    for opcode, value in ((0xB8, 0x11111111), (0xBB, 0x22222222), (0xB9, 0x33333333),
                          (0xBA, 0x44444444), (0xBD, 0x55555555), (0xBE, 0x66666666), (0xBF, 0x77777777)):
        outer += bytes([opcode]) + struct.pack('<I', value)
    outer += bytes.fromhex('68470200009d')
    call = len(outer)
    outer += b'\xe8' + b'\0'*4
    outer += bytes.fromhex('9c608b7c2424')
    for i in range(9):
        outer += bytes.fromhex('8b4c24') + bytes([i*4]) + bytes.fromhex('898f') + struct.pack('<I', SNAP+i*4)
    outer += bytes.fromhex('619d83c4048944241c619dc3')
    inner = len(outer)
    struct.pack_into('<i', outer, call+1, inner-call-5)
    gate_va = base + inner + 6
    success = bytes.fromhex('c744241c01000000619dc3')
    reject = bytes.fromhex('c744241c00000000619dc3')
    emitter = camera.camera_gate if new else camera.old_gate
    return bytes(outer) + bytes.fromhex('9c608b542428') + emitter(layout, gate_va, gate_va+124+len(success)) + success + reject


class NativeCameraTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='camera-native-')
        cls.addClassCleanup(cls.temp.cleanup)
        folder = Path(cls.temp.name)
        if os.name == 'nt':
            compiler = Path(os.environ.get('WINDIR', 'C:/Windows'))/'Microsoft.NET/Framework/v4.0.30319/csc.exe'
            if not compiler.is_file():
                raise unittest.SkipTest('x86 C# fixture compiler unavailable')
            cls.exe = folder/'fixture.exe'
            source = folder/'fixture.cs'; source.write_text(WINDOWS_WORKER, encoding='utf-8')
            command = [str(compiler), '/nologo', '/platform:x86', '/optimize+', '/out:'+str(cls.exe), str(source)]
        else:
            compiler = shutil.which('gcc')
            if not compiler:
                raise unittest.SkipTest('gcc for freestanding x86 fixtures unavailable')
            cls.exe = folder/'fixture'
            source = folder/'fixture.c'; source.write_text(LINUX_WORKER, encoding='utf-8')
            command = [compiler, '-m32', '-nostdlib', '-static', '-fno-pie', '-no-pie', '-fno-stack-protector',
                       '-fno-builtin', '-Os', '-Wl,-e,_start', str(source), '-o', str(cls.exe)]
        cls.process_options = {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}
        built = subprocess.run(command, capture_output=True, text=True, timeout=60, **cls.process_options)
        if built.returncode:
            raise AssertionError(built.stdout+built.stderr)
        try:
            probe = subprocess.run([str(cls.exe)], input=struct.pack('<II', 1, 0)+b'\xc3', capture_output=True, timeout=10, **cls.process_options)
        except OSError as exc:
            if exc.errno == errno.ENOEXEC:
                raise unittest.SkipTest('host cannot execute the 32-bit native fixture') from exc
            raise
        if probe.returncode:
            raise AssertionError(f'native worker preflight failed: {probe.returncode}: {probe.stderr!r}')

    def run_cases(self, layout, cases, new=True, base=0x100000):
        code = native_function(layout, new=new, base=base)
        payload = struct.pack('<II', len(code), len(cases))+code+b''.join(struct.pack('<4i', *c) for c in cases)
        result = subprocess.run([str(self.exe)], input=payload, capture_output=True, timeout=30, **self.process_options)
        self.assertEqual(result.returncode, 0, result.stderr.decode(errors='replace'))
        self.assertEqual(len(result.stdout), 60*len(cases))
        rows = list(struct.iter_unpack('<15I', result.stdout))
        for case, row in zip(cases, rows):
            with self.subTest(case=case):
                self.assertEqual(row[5:8], (0x77777777, 0x66666666, 0x55555555))
                self.assertEqual(row[9:12], (0x22222222, 0x44444444, 0x33333333))
                self.assertEqual(row[12], row[0])
                self.assertEqual(row[13] & 0xCD5, 0x247 & 0xCD5)
                self.assertEqual(row[14], 0, 'native gate wrote outside its declared memory')
                self.assertEqual(row[1:3], tuple(n & 0xFFFFFFFF for n in case[:2]))
        return rows

    def test_signed_extremes_and_far_edge_recovery_for_all_resolutions(self):
        positions = (-2147483648, -1, 0, 1, 40, 81, 90, 99, 100, 2147483647)
        for key in SIZES:
            layout = FramedViewport(*map(int, key.split('x')))
            cases = [(100, 100, x, y) for x in positions for y in positions]
            rows = self.run_cases(layout, cases)
            for case, row in zip(cases, rows):
                self.assertEqual(row[0], 1)
                self.assertEqual(row[3:5], tuple(min(max(case[i+2], 0), 100-layout.full_tiles[i]) for i in (0, 1)))

    def test_invalid_or_small_world_rejection_preserves_both_camera_axes(self):
        for key in SIZES:
            layout = FramedViewport(*map(int, key.split('x')))
            tx, ty = layout.full_tiles
            cases = [(w, h, -20, 2147483647) for w, h in ((0, 100), (100, 0), (-1, 100), (100, -1),
                     (101, 100), (100, 101), (tx-1, 100), (100, ty-1), (3, 2), (100, 2147483647))]
            for case, row in zip(cases, self.run_cases(layout, cases)):
                self.assertEqual(row[0], 0)
                self.assertEqual(row[3:5], (case[2] & 0xFFFFFFFF, case[3] & 0xFFFFFFFF))

    def test_already_valid_cameras_match_original_gates_and_preserve_state(self):
        rng = random.Random(317)
        for key in SIZES:
            layout = FramedViewport(*map(int, key.split('x')))
            cases = []
            for _ in range(100):
                w, h = (rng.randint(layout.full_tiles[i], 100) for i in (0, 1))
                cases.append((w, h, rng.randint(0, w-layout.full_tiles[0]), rng.randint(0, h-layout.full_tiles[1])))
            old = self.run_cases(layout, cases, new=False)
            new = self.run_cases(layout, cases)
            for a, b in zip(old, new):
                self.assertEqual(a[:8]+a[9:], b[:8]+b[9:])
                self.assertEqual(b[0], 1)

    def test_cross_resolution_camera_and_exact_world_fit(self):
        cases = [(100, 100, 89, 92), (19, 10, 89, 92), (19, 10, 0, 0)]
        layout = FramedViewport(1280, 720)
        rows = self.run_cases(layout, cases)
        self.assertEqual([r[3:5] for r in rows], [(81, 90), (0, 0), (0, 0)])
        self.assertEqual(self.run_cases(layout, [cases[0]], new=False)[0][0], 0)

    def test_rebased_machine_code_executes_identically(self):
        layout = FramedViewport(3840, 2160)
        cases = [(100, 100, 99, 99), (100, 100, -1, -1), (40, 30, 99, 99)]
        a = self.run_cases(layout, cases, base=0x100000)
        b = self.run_cases(layout, cases, base=0x700000)
        for x, y in zip(a, b):
            self.assertEqual(x[:8]+x[9:], y[:8]+y[9:])


if __name__ == '__main__':
    unittest.main()
