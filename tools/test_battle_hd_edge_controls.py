"""Source and native x86 fixtures for the new edge-controls validation stage.

No game process starts. CPU helpers use explicit resource/input callback stubs.
Use --source-exe and --toolchain-path for original-backed x86 verification.
"""
from __future__ import annotations
import argparse
from dataclasses import replace
from functools import wraps
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tools')]
from src.patcher import battle_hd_edge_controls as edge
from src.patcher import pe_extension as pe
import build_battle_hd_edge_candidate as cli

SOURCE_EXE = None


def requires_unicorn(test):
    """Admit CPU tests before their imports; CLI strict mode fails in main."""
    @wraps(test)
    def checked(self, *args, **kwargs):
        if not importlib.util.find_spec('unicorn'):
            self.skipTest('optional Unicorn unavailable; use --toolchain-path or --require-machine-tools')
        return test(self, *args, **kwargs)
    return checked


class SourceTests(unittest.TestCase):
    def test_edge_slices_are_unscaled_disjoint_and_do_not_touch_battlefield(self):
        coverage = set()
        for sx, sy, width, height, dx, dy in edge.FRAME_BLITS:
            self.assertTrue(0 <= sx < sx + width <= 640)
            self.assertTrue(0 <= sy < sy + height <= 480)
            self.assertTrue(0 <= dx < dx + width <= 1280)
            self.assertTrue(0 <= dy < dy + height <= 720)
            pixels = {(x, y) for y in range(dy, dy + height) for x in range(dx, dx + width)}
            self.assertFalse(coverage & pixels)
            self.assertFalse(any(32 <= x < 1120 and 136 <= y < 584 for x, y in pixels))
            coverage.update(pixels)
        self.assertEqual(sum(w*h for _, _, w, h, _, _ in edge.SIDEBAR_BLITS), 160*480)
        self.assertTrue(all((x, y) not in coverage for y in range(368, 608) for x in range(1136, 1264)))
        self.assertTrue(all((x,y) in coverage for y in range(368,608) for x in (*range(1120,1136),*range(1264,1280))))
        self.assertEqual(edge.DESCRIPTORS, ((1138,610),(1201,610),(1138,641),(1138,672),(1201,641),(1145,0)))

    def test_original_stage_is_preserved_and_sources_pin_exact_bytes(self):
        self.assertEqual(edge.STAGE, edge.scalar.BATTLE_HD_STAGE + '-edgecontrols-validation')
        self.assertEqual(edge.hud.BATTLE_LAYOUT.sidebar, (1120,120,1280,600))
        self.assertIn(edge._sources()['src/patcher/battle_hd_hud.py'], edge.PINNED['src/patcher/battle_hd_hud.py'])
        with patch.dict(edge.PINNED, {'src/patcher/battle_hd_hud.py': ('0'*64,)}):
            with self.assertRaises(ValueError): edge._sources()

    def test_only_enumerated_lf_crlf_sources_are_accepted_and_report_actual_hashes(self):
        read = Path.read_bytes
        paired = [name for name, accepted in edge.PINNED.items() if len(accepted) == 2]
        self.assertEqual(len(paired), 4)
        for name in paired:
            source = edge.ROOT / name
            lf = read(source).replace(b'\r\n', b'\n')
            crlf = lf.replace(b'\n', b'\r\n')
            self.assertEqual({edge.sha(lf), edge.sha(crlf)}, set(edge.PINNED[name]))
            for data in (lf, crlf):
                with self.subTest(source=name, digest=edge.sha(data)):
                    def read_variant(path):
                        return data if path == source else read(path)
                    with patch.object(Path, 'read_bytes', read_variant):
                        observed = edge._sources()
                    self.assertEqual(observed[name], edge.sha(data))
            for invalid in (lf + b'# non-EOL modification\n', lf.replace(b'\n', b'\r\n', 1)):
                with self.subTest(source=name, invalid=edge.sha(invalid)):
                    def read_invalid(path):
                        return invalid if path == source else read(path)
                    with patch.object(Path, 'read_bytes', read_invalid), self.assertRaises(ValueError):
                        edge._sources()
        for name, accepted in edge.PINNED.items():
            if len(accepted) == 1:
                source = edge.ROOT / name
                invalid = read(source) + b'# changed source\n'
                def read_invalid_single(path):
                    return invalid if path == source else read(path)
                with self.subTest(source=name), patch.object(Path, 'read_bytes', read_invalid_single), self.assertRaises(ValueError):
                    edge._sources()

    def test_wrong_original_and_resolution_are_rejected(self):
        with self.assertRaises(ValueError): edge.build_candidate(bytes(32))
        with self.assertRaises(ValueError): edge._restore_frozen_predecessor(bytes(32))
        for resolution in ('800x600','1920x1080','1280X720',True,None):
            with self.subTest(resolution=resolution), self.assertRaises(ValueError):
                edge.build_candidate(b'', resolution)

    def test_cli_rejects_unsafe_output_before_reading_original(self):
        for output in ('relative.exe','C:/Clash/clash95.exe','C:/ClashTests/bad.txt',str(ROOT/'bad.exe')):
            with self.subTest(output=output), self.assertRaises(ValueError):
                cli.write_candidate('missing-original',output)


class NativeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if SOURCE_EXE is None: raise unittest.SkipTest('explicit --source-exe is required')
        cls.original = SOURCE_EXE.read_bytes()
        cls.current = edge.scalar.apply_patches(cls.original, edge.scalar.select_patches_for(
            edge.scalar.BATTLE_HD_STAGE, edge.scalar.parse_resolution(edge.RESOLUTION)))
        cls.base, cls.frozen_records, _ = edge.predecessor(cls.original)
        cls.image, cls.manifest, cls.probe = edge.build_candidate(cls.original)
        cls.view = pe.inspect_pe(cls.image)
        cls.bundle = edge.emit_helpers(cls.view.image_base + pe.inspect_pe(cls.base).image_size)

    def test_guarded_predecessor_adapter_and_inherited_metadata_replay(self):
        self.assertEqual(edge.sha(self.current), edge.CURRENT_BASE_SHA256)
        self.assertNotEqual(self.current, self.base)
        self.assertEqual([(e.offset, len(e.old), len(e.new)) for e in edge.PREDECESSOR_RESTORATIONS],
                         [(0x05FE61,38,38),(0x060211,38,38),(0x12E200,32,32),(0x12E300,60,60)])
        reconstruction = self.manifest['predecessor_reconstruction']
        self.assertEqual(reconstruction['source_candidate_sha256'], edge.CURRENT_BASE_SHA256)
        self.assertEqual(reconstruction['result_candidate_sha256'], edge.BASE_SHA256)
        restored = bytearray(self.current)
        for record in reconstruction['edits']:
            offset, old, new = record['offset'], bytes.fromhex(record['old_hex']), bytes.fromhex(record['new_hex'])
            self.assertEqual(restored[offset:offset+len(old)], old)
            restored[offset:offset+len(new)] = new
        self.assertEqual(bytes(restored), self.base)
        records = self.manifest['inherited_patch_records']
        self.assertEqual(len(records), 283)
        replay = bytearray(self.original)
        for record in records:
            offset, old, new = record['offset'], bytes.fromhex(record['old_hex']), bytes.fromhex(record['new_hex'])
            self.assertEqual(replay[offset:offset+len(old)], old)
            replay[offset:offset+len(new)] = new
        self.assertEqual(bytes(replay), self.base)
        by_offset = {p.offset: p for p in self.frozen_records}
        self.assertEqual(by_offset[0x05FE61].group, 'mouse-dynamic-origin')
        self.assertEqual(by_offset[0x060211].group, 'viewport-switch-dynamic-surface')
        self.assertEqual(self.base[0x12E200:0x12E220], bytes(32))
        self.assertEqual(self.base[0x12E300:0x12E33C], bytes(60))

    def test_predecessor_adapter_rejects_unknown_input_and_wrong_old_bytes(self):
        changed = bytearray(self.current); changed[-1] ^= 1
        for unknown in (bytes(changed), self.base):
            with self.assertRaises(ValueError): edge._restore_frozen_predecessor(unknown)
        for i, edit in enumerate(edge.PREDECESSOR_RESTORATIONS):
            edits = list(edge.PREDECESSOR_RESTORATIONS)
            edits[i] = replace(edit, old=bytes([edit.old[0] ^ 1]) + edit.old[1:])
            with self.subTest(i=i), patch.object(edge, 'PREDECESSOR_RESTORATIONS', tuple(edits)):
                with self.assertRaisesRegex(ValueError, 'restoration old bytes differ'):
                    edge._restore_frozen_predecessor(self.current)

    def test_predecessor_adapter_rejects_missing_edits_and_changed_result(self):
        for i, edit in enumerate(edge.PREDECESSOR_RESTORATIONS):
            edits = list(edge.PREDECESSOR_RESTORATIONS)
            missing = tuple(edits[:i] + edits[i+1:])
            edits[i] = replace(edit, new=bytes([edit.new[0] ^ 1]) + edit.new[1:])
            for invalid in (missing, tuple(edits)):
                with self.subTest(i=i), patch.object(edge, 'PREDECESSOR_RESTORATIONS', invalid):
                    with self.assertRaises(ValueError): edge._restore_frozen_predecessor(self.current)

    def test_predecessor_metadata_rejects_incomplete_current_hook_inventory(self):
        current = edge.scalar.battle_hd_patches()
        missing = [p for p in current if p.offset != 0x05FE61]
        with patch.object(edge.scalar, 'battle_hd_patches', return_value=missing):
            with self.assertRaisesRegex(ValueError, 'input hook inventory differs'):
                edge._frozen_patch_records(self.original, self.base,
                                           edge.scalar.parse_resolution(edge.RESOLUTION))

    def test_exact_build_replay_preserves_unrelated_bytes_and_relocations(self):
        rebuilt = bytearray(self.base)
        extension = self.manifest['extension']
        for record in [*extension['edits'], *self.manifest['edge_edits']]:
            offset, old, new = record['offset'], bytes.fromhex(record['old_hex']), bytes.fromhex(record['new_hex'])
            self.assertEqual(rebuilt[offset:offset+len(old)],old)
            rebuilt[offset:offset+len(old)] = new
        self.assertEqual(bytes(rebuilt),self.image)
        self.assertEqual(edge.sha(self.base),edge.BASE_SHA256)
        self.assertEqual(edge.sha(self.image),self.manifest['candidate_sha256'])
        before = pe.inspect_pe(self.base)
        self.assertEqual(self.view.sections[:-1],before.sections)
        self.assertEqual(self.view.sections[-1].characteristics,pe.RX_CODE)
        oldtable,oldfields=pe._old_relocations(self.base,before)
        _,newfields=pe._old_relocations(self.image,self.view)
        self.assertTrue(set(oldfields) <= set(newfields))
        start=before.file_offset(before.relocation_rva,len(oldtable))
        self.assertEqual(self.image[start:start+len(oldtable)],oldtable)
        self.assertEqual(len(newfields)-len(oldfields),sum(r.kind=='abs32' for r in self.bundle.relocations))
        self.assertFalse(self.manifest['runtime_executed'])
        self.assertFalse(self.manifest['promotion_ready'])

    def test_both_exact_checkout_forms_build_same_candidate_with_actual_source_hashes(self):
        read = Path.read_bytes
        paired = [name for name, accepted in edge.PINNED.items() if len(accepted) == 2]
        for ending in (b'\n', b'\r\n'):
            replacements = {edge.ROOT / name: read(edge.ROOT / name).replace(b'\r\n', b'\n').replace(b'\n', ending)
                            for name in paired}
            def read_variant(path):
                return replacements[path] if path in replacements else read(path)
            with self.subTest(ending=ending), patch.object(Path, 'read_bytes', read_variant):
                image, metadata, probe = edge.build_candidate(self.original)
            self.assertEqual(image, self.image)
            self.assertEqual(probe, self.probe)
            self.assertEqual(edge.sha(image), '26fa4f69095f8d47480b325e22c70bffb3f6c098760de04164ebd09fb93038e3')
            self.assertEqual(metadata['base_candidate_sha256'], edge.BASE_SHA256)
            for name in paired:
                self.assertEqual(metadata['source_hashes'][name], edge.sha(replacements[edge.ROOT / name]))

    def test_descriptor_callbacks_flags_and_native_hit_path_remain_identical(self):
        original_view=pe.inspect_pe(self.original)
        for i,(x,y) in enumerate(edge.DESCRIPTORS):
            va=0x514B78+53*i
            offset=self.view.file_offset(va-0x400000,53)
            original_offset=original_view.file_offset(va-0x400000,53)
            self.assertEqual(struct.unpack_from('<ii',self.image,offset),(x,y))
            self.assertEqual(self.image[offset+8:offset+53],self.original[original_offset+8:original_offset+53])
        for va,length in ((0x4191F0,0x240),(0x419B80,0x1E0),(0x419DC0,0xA0),(0x42E501,5)):
            a=self.view.file_offset(va-0x400000,length);b=original_view.file_offset(va-0x400000,length)
            self.assertEqual(self.image[a:a+length],self.original[b:b+length])

    def test_loaded_probe_covers_all_original_edits_and_native_observers(self):
        self.assertIn('candidate_sha256='+self.manifest['candidate_sha256'],self.probe)
        self.assertEqual(edge.sha(self.probe.encode()),self.manifest['probe_sha256'])
        self.assertLess(max(map(len,self.probe.splitlines())),4096)
        spans=self.manifest['loaded_probe_spans']
        for edit in self.manifest['edge_edits']:
            self.assertTrue(any(start<=edit['va'] and edit['va']+len(bytes.fromhex(edit['new_hex']))<=start+size for start,size in spans),hex(edit['va']))
        changed=bytearray(self.base)
        changed[self.manifest['edge_edits'][0]['offset']] ^= 1
        with self.assertRaises(ValueError):edge.edits_for(bytes(changed),self.bundle)

    def machine(self):
        if not importlib.util.find_spec('unicorn'):self.skipTest('explicit Unicorn toolchain required')
        from unicorn import Uc,UC_ARCH_X86,UC_MODE_32
        emu=Uc(UC_ARCH_X86,UC_MODE_32)
        emu.mem_map(0x400000,0x200000);emu.mem_map(0x600000,0x20000);emu.mem_map(0x700000,0x10000)
        emu.mem_write(0x400000,self.image[:self.view.headers_size])
        for section in self.view.sections:
            if section.raw_offset:emu.mem_write(0x400000+section.rva,self.image[section.raw_offset:section.raw_offset+section.raw_size])
        return emu

    @requires_unicorn
    def test_helper_cpu_copy_rectangles_and_full_register_abi(self):
        from unicorn import UC_HOOK_CODE
        from unicorn import x86_const as r
        for name in ('frame','stats'):
            for scratch in (0,0x600000):
                for software in ((0,0x604000) if name=='frame' else (0x604000,)):
                    with self.subTest(name=name,scratch=scratch,software=software):
                        emu=self.machine();stack=0x708000;stop=0x5F0000;calls=[]
                        put=lambda a,v:emu.mem_write(a,struct.pack('<I',v))
                        get=lambda a:struct.unpack('<I',emu.mem_read(a,4))[0]
                        put(0x5202E0,software);put(0x600000+184,0x601000);put(0x601000,0x603100);put(stack,stop)
                        regs=[r.UC_X86_REG_EAX,r.UC_X86_REG_EBX,r.UC_X86_REG_ECX,r.UC_X86_REG_EDX,r.UC_X86_REG_ESI,r.UC_X86_REG_EDI,r.UC_X86_REG_EBP]
                        values=[0x101+i*0x111 for i in range(7)]
                        for reg,value in zip(regs,values):emu.reg_write(reg,value)
                        emu.reg_write(r.UC_X86_REG_ESP,stack);emu.reg_write(r.UC_X86_REG_EFLAGS,0xAD7)
                        def ret(extra=0,value=0xaaaa):
                            sp=emu.reg_read(r.UC_X86_REG_ESP);ip=get(sp)
                            for reg,number in zip(regs[:4],(value,0xbbbb,0xcccc,0xdddd)):emu.reg_write(reg,number)
                            emu.reg_write(r.UC_X86_REG_EFLAGS,0x202);emu.reg_write(r.UC_X86_REG_ESP,sp+4+extra);emu.reg_write(r.UC_X86_REG_EIP,ip)
                        def hook(_emu,ip,_size,_data):
                            eax,ebx,ecx,edx=[emu.reg_read(reg) for reg in regs[:4]]
                            if ip==0x566000:ret(value=scratch)
                            elif ip==0x401E60:calls.append(('clear',eax));ret()
                            elif ip==0x4024E0:
                                right,bottom,dx,dy=struct.unpack('<4I',emu.mem_read(emu.reg_read(r.UC_X86_REG_ESP)+4,16))
                                calls.append(('copy',eax,edx,ebx,ecx,right,bottom,dx,dy));ret(16)
                            elif ip==0x603100:calls.append(('free',eax,edx));ret()
                        emu.hook_add(UC_HOOK_CODE,hook);emu.emu_start(self.bundle.entries[name],stop,count=5000)
                        self.assertEqual(emu.reg_read(r.UC_X86_REG_ESP),stack+4)
                        self.assertEqual([emu.reg_read(reg) for reg in regs],values)
                        self.assertEqual(emu.reg_read(r.UC_X86_REG_EFLAGS),0xAD7)
                        if not scratch:self.assertEqual(calls,[]);continue
                        rects=edge.FRAME_BLITS if name=='frame' else edge.SIDEBAR_BLITS[:1]
                        target=0x51D4C0 if name=='frame' else software
                        expected=[('copy',scratch,target,sx,sy,sx+w-1,sy+h-1,dx,dy) for sx,sy,w,h,dx,dy in rects]
                        if name=='frame' and software:expected.append(('copy',0x51D4C0,software,0,0,1279,719,0,0))
                        self.assertEqual([c for c in calls if c[0]=='copy'],expected)
                        self.assertEqual(calls[-1],('free',scratch,2))

    @requires_unicorn
    def test_native_stats_present_and_cursor_clip_follow_top_slice(self):
        from unicorn import UC_HOOK_CODE
        from unicorn import x86_const as r
        for present in (0,1):
            emu=self.machine();stack=0x708000;scene=0x604000;copies=[];clips=[]
            emu.mem_write(stack+0x70,struct.pack('<I',present));emu.mem_write(0x5202E0,struct.pack('<I',scene));emu.reg_write(r.UC_X86_REG_ESP,stack)
            def ret(extra=0):
                sp=emu.reg_read(r.UC_X86_REG_ESP);ip=struct.unpack('<I',emu.mem_read(sp,4))[0]
                emu.reg_write(r.UC_X86_REG_ESP,sp+4+extra);emu.reg_write(r.UC_X86_REG_EIP,ip)
            def hook(_emu,ip,_size,_data):
                if ip==0x405920:ret()
                elif ip==0x460BB0:
                    clips.append(tuple(emu.reg_read(reg) for reg in (r.UC_X86_REG_EDX,r.UC_X86_REG_EBX,r.UC_X86_REG_ECX))+struct.unpack('<I',emu.mem_read(emu.reg_read(r.UC_X86_REG_ESP)+4,4)));ret(4)
                elif ip==0x4024E0:
                    copies.append(tuple(emu.reg_read(reg) for reg in (r.UC_X86_REG_EAX,r.UC_X86_REG_EDX,r.UC_X86_REG_EBX,r.UC_X86_REG_ECX))+struct.unpack('<4I',emu.mem_read(emu.reg_read(r.UC_X86_REG_ESP)+4,16)));ret(16)
            emu.hook_add(UC_HOOK_CODE,hook);emu.emu_start(0x4317CC,0x43181E,count=1000)
            self.assertEqual(emu.reg_read(r.UC_X86_REG_ESP),stack)
            self.assertEqual(copies,[(scene,0,1138,10,1264,354,1138,10)] if present else [])
            self.assertEqual(clips,[(1138,10,1264,354)])

    @requires_unicorn
    def test_native_morale_animation_destination_matches_static_top_stats(self):
        from unicorn import UC_HOOK_CODE
        from unicorn import x86_const as r
        for morale in (0,50,99,100):
            emu=self.machine();stack=0x708000;stop=0x5F0000;scratch=0x600000;device=0x605000;calls=[]
            put=lambda a,v:emu.mem_write(a,struct.pack('<I',v))
            get=lambda a:struct.unpack('<I',emu.mem_read(a,4))[0]
            put(stack,stop);put(0x53210C,morale);put(0x511230,device);put(scratch+184,0x601000);put(0x601000,0x602100);put(0x601000+52,0x602000);emu.reg_write(r.UC_X86_REG_ESP,stack)
            def ret(extra=0,value=None):
                sp=emu.reg_read(r.UC_X86_REG_ESP);ip=get(sp)
                if value is not None:emu.reg_write(r.UC_X86_REG_EAX,value)
                emu.reg_write(r.UC_X86_REG_ESP,sp+4+extra);emu.reg_write(r.UC_X86_REG_EIP,ip)
            def hook(_emu,ip,_size,_data):
                eax,edx,ebx,ecx=[emu.reg_read(reg) for reg in (r.UC_X86_REG_EAX,r.UC_X86_REG_EDX,r.UC_X86_REG_EBX,r.UC_X86_REG_ECX)]
                if ip==0x461C00:self.assertEqual(eax,188);ret(value=scratch)
                elif ip in (0x405EF0,0x405EE0):ret(value=87 if ip==0x405EF0 else 55)
                elif ip==0x403D70:self.assertEqual((edx,ebx),(88,56));ret(value=scratch)
                elif ip==0x405EC0:ret(value=0x606000)
                elif ip==0x602000:ret(28)
                elif ip==0x602100:calls.append(('free',eax,edx));ret()
                elif ip==0x4024E0:
                    calls.append(('copy',eax,edx,ebx,ecx,*struct.unpack('<4I',emu.mem_read(emu.reg_read(r.UC_X86_REG_ESP)+4,16))));ret(16)
            emu.hook_add(UC_HOOK_CODE,hook);emu.emu_start(0x430E90,stop,count=5000)
            self.assertEqual(emu.reg_read(r.UC_X86_REG_ESP),stack+4);self.assertEqual(get(0x511230),device)
            expected=[] if morale>=100 else [('copy',scratch,device,0,0,(100-morale)*88//100,56,1174,26),('free',scratch,2)]
            self.assertEqual(calls,expected,morale)

    @requires_unicorn
    def test_native_hover_reads_top_sidebar_and_rejects_inert_gap(self):
        from unicorn import x86_const as r
        cases=[(535,30,0),(623,83,0),(499,91,1),(623,137,1),(499,145,2),(623,179,2),
               (499,180,3),(623,213,3),(499,214,4),(623,247,4),(499,248,5),(623,281,5),
               (499,282,6),(623,315,6),(499,316,7),(623,349,7),(534,30,-1),(624,83,-1),
               (499,90,-1),(498,91,-1),(499,350,-1),(499,500,-1)]
        for x,y,expected in cases:
            for scale in (0,2,6):
                emu=self.machine();emu.mem_write(0x544CFC,struct.pack('<ii',(x+640)<<scale,y<<scale));emu.mem_write(0x54512C,bytes([scale]));emu.reg_write(r.UC_X86_REG_ESP,0x708000)
                emu.emu_start(0x42E160,0x42E197,count=1000)
                self.assertEqual(emu.reg_read(r.UC_X86_REG_EIP),0x42E197)
                self.assertEqual(emu.reg_read(r.UC_X86_REG_EAX),expected&0xffffffff,(x,y,scale))

    @requires_unicorn
    def test_native_descriptor_draw_reads_the_same_new_origins_without_scaling(self):
        from unicorn import UC_HOOK_CODE
        from unicorn import x86_const as r
        for index,point in enumerate(edge.DESCRIPTORS):
            emu=self.machine();stack=0x708000;stop=0x5F0000;draws=[];desc=0x514B78+53*index
            put=lambda a,v:emu.mem_write(a,struct.pack('<I',v))
            put(stack,stop);put(0x511230,0x51D4C0);put(0x544D10,0);put(0x51D4C0+184,0x601000);put(0x601000+52,0x602000)
            emu.reg_write(r.UC_X86_REG_ESP,stack);emu.reg_write(r.UC_X86_REG_EAX,desc);emu.reg_write(r.UC_X86_REG_EDX,0)
            def ret(extra=0,value=None):
                sp=emu.reg_read(r.UC_X86_REG_ESP);ip=struct.unpack('<I',emu.mem_read(sp,4))[0]
                if value is not None:emu.reg_write(r.UC_X86_REG_EAX,value)
                emu.reg_write(r.UC_X86_REG_ESP,sp+4+extra);emu.reg_write(r.UC_X86_REG_EIP,ip)
            def hook(_emu,ip,_size,_data):
                if ip==0x405EC0:ret(value=0x606000)
                elif ip==0x602000:
                    draws.append((emu.reg_read(r.UC_X86_REG_EBX),emu.reg_read(r.UC_X86_REG_ECX),tuple(struct.unpack('<7i',emu.mem_read(emu.reg_read(r.UC_X86_REG_ESP)+4,28)))))
                    ret(28)
            emu.hook_add(UC_HOOK_CODE,hook);emu.emu_start(0x4191F0,stop,count=5000)
            self.assertEqual(emu.reg_read(r.UC_X86_REG_ESP),stack+4)
            self.assertEqual(draws,[(*point,(-1,-1,-1,-1,1,0,0))])

    @requires_unicorn
    def test_actual_descriptor_hit_routine_calls_original_callbacks_at_new_origins(self):
        from unicorn import UC_HOOK_CODE
        from unicorn import x86_const as r
        width,height=58,28  # Explicit resource-query stubs, not artwork measurements.
        for index,(x,y) in enumerate(edge.DESCRIPTORS):
            for dx,dy,inside in ((1,1,True),(-1,1,False),(1,-1,False),(width-1,1,False),(1,height-1,False),(1,-120 if index<5 else 120,False)):
                for scale in (0,2,6):
                    with self.subTest(index=index,point=(x+dx,y+dy),scale=scale):
                        emu=self.machine();stack=0x708000;stop=0x5f0000;desc=0x514B78+53*index;callbacks=[]
                        get=lambda a:struct.unpack('<I',emu.mem_read(a,4))[0]
                        callback=get(desc+32)
                        emu.mem_write(0x544CFC,struct.pack('<ii',(x+dx)<<scale,(y+dy)<<scale));emu.mem_write(0x54512C,bytes([scale]));emu.mem_write(stack,struct.pack('<I',stop))
                        emu.reg_write(r.UC_X86_REG_EAX,desc);emu.reg_write(r.UC_X86_REG_ESP,stack)
                        def ret(value=0):
                            sp=emu.reg_read(r.UC_X86_REG_ESP);ip=get(sp)
                            emu.reg_write(r.UC_X86_REG_EAX,value);emu.reg_write(r.UC_X86_REG_ESP,sp+4);emu.reg_write(r.UC_X86_REG_EIP,ip)
                        def hook(_emu,ip,_size,_data):
                            if ip==0x405EF0:ret(width)
                            elif ip==0x405EE0:ret(height)
                            elif ip==0x460900:ret(0)
                            elif ip==0x4608F0:ret(1)
                            elif ip==callback:callbacks.append((ip,emu.reg_read(r.UC_X86_REG_EAX)));ret()
                            elif ip in (0x4191F0,0x4229A0,0x422B50):ret()
                        emu.hook_add(UC_HOOK_CODE,hook);emu.emu_start(0x419B80,stop,count=5000)
                        self.assertEqual(emu.reg_read(r.UC_X86_REG_ESP),stack+4)
                        self.assertEqual(callbacks,[(callback,desc)] if inside else [])


def main():
    global SOURCE_EXE
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-exe',type=Path)
    parser.add_argument('--toolchain-path',type=Path)
    parser.add_argument('--require-machine-tools',action='store_true')
    args,rest=parser.parse_known_args();SOURCE_EXE=args.source_exe
    if args.toolchain_path:sys.path.insert(0,str(args.toolchain_path))
    if args.require_machine_tools:
        import unicorn
    unittest.main(argv=[sys.argv[0],*rest])


if __name__=='__main__':main()
