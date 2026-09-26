#!/usr/bin/env python3
"""Portable format/contracts and optional in-memory original-backed checks.

No game, debugger, CPU emulator, output bundle or dependency install is run.
These tests do not establish native execution or lifecycle correctness.
"""
from copy import deepcopy
from dataclasses import asdict
from pathlib import Path
import argparse
import re
import struct
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'tools')]
from src.patcher import ordinary_castle_entry_matrix as tool
from src.patcher import pe_extension as pe
import build_ordinary_castle_entry_matrix_candidate as cli

ORIGINAL = None
PROFILE = 'modalwidgets'
RESOLUTION = '1024x768'


def fixture(count=12, text_pages=1):
    """Explicit synthetic PE; never accepted by the public original-bound API."""
    pe_at, opt, table, base = 0x40, 0x58, 0x138, 0x400000
    data = bytearray(1024)
    data[:2] = b'MZ'; struct.pack_into('<I', data, 0x3C, pe_at)
    data[pe_at:pe_at+4] = b'PE\0\0'
    struct.pack_into('<HHIIIHH', data, pe_at+4, 0x14C, count, 0, 0, 0, 224, 0x182)
    struct.pack_into('<H', data, opt, 0x10B)
    struct.pack_into('<III', data, opt+28, base, 4096, 512)
    struct.pack_into('<I', data, opt+60, 1024)
    struct.pack_into('<I', data, opt+92, 16)
    rva = 4096; code_size = 0
    for index in range(count):
        size = text_pages*4096 if index == 0 else 512
        virtual = size if index == 0 else 4096
        name = '.text' if index == 0 else '.hdmodal' if index == 1 else '.hdstate' if index == 2 else '.hdpblit' if index == count-1 else f'.x{index}'
        flags = 0xC0000040 if index == 2 else pe.RX_CODE
        raw = len(data)
        struct.pack_into('<8sIIIIIIHHI', data, table+40*index, name.encode(), virtual, rva, size, raw, 0, 0, 0, 0, flags)
        data.extend(bytes(size))
        if flags & 0x20: code_size += size
        rva += pe._align(max(size, virtual), 4096)
    struct.pack_into('<I', data, opt+4, code_size)
    struct.pack_into('<I', data, opt+56, rva)
    last_rva, last_raw = struct.unpack_from('<II', data, table+40*(count-1)+12)[0], len(data)-512
    struct.pack_into('<II', data, opt+136, last_rva+0x100, 12)
    struct.pack_into('<IIHH', data, last_raw+0x100, 0x1000, 12, 0x3020, 0)
    struct.pack_into('<I', data, 1024+0x20, 0x4617A0)
    view = pe.inspect_pe(bytes(data))
    hook = base+0x1100
    admission = tool.Admission(base+0x108B, base+0x2000, base+0x200B,
                               hook-10, hook, hook+6, base+0x1180, base+view.sections[2].rva)
    def put(va, value):
        offset = view.file_offset(va-base, len(value)); data[offset:offset+len(value)] = value
    put(admission.comparison, tool.OWNER_CMP)
    put(hook, b'\x0f\x85'+struct.pack('<i', admission.reject-hook-6))
    return bytes(data), admission


def typed_parent(profile='completehd', resolution='1024x768'):
    modal = dict(schema='clash95_framed_modal_candidate_v1', resolution=resolution,
        modal_native_canvas_revision='framed_owned_native_modal_canvas_v1',
        modal_state_offsets=dict(tool.canvas.STATE), modal_state_size=128)
    army = dict(schema='clash95_framed_army_candidate_v1', resolution=resolution, base_candidate=modal)
    node = dict(schema=1, resolution=resolution, stage=tool.complete.STAGE,
                recipe_revision=tool.complete.REVISION, base_sha256=pe.ORIGINAL_SHA256, predecessor=army)
    if profile == 'modalwidgets':
        for kind in ('slots', 'primary', 'primary_text', 'widgets'):
            node = dict(schema=f'clash95_framed_modal_{kind}_candidate_v1', resolution=resolution, base_candidate=node)
    base_stage = tool.complete.STAGE if profile == 'completehd' else tool.complete.STAGE.removesuffix('-validation')+'-modalwidgets-validation'
    return dict(schema='native_map_present_bounds_v1', resolution=resolution, profile=profile,
                base_stage=base_stage, stage=base_stage.removesuffix('-validation')+'-nativepresent-validation',
                recipe_revision=tool.parent_builder.REVISION,
                base_recipe_revision='complete_hd_v1' if profile == 'completehd' else 'owned_modal_widget_bounds_v1',
                original_sha256=pe.ORIGINAL_SHA256, base_candidate=node)


def native_fixture(text_pages=35):
    image, _ = fixture(12, text_pages)
    view = pe.inspect_pe(image); data = bytearray(image)
    enter = view.image_base+view.sections[1].rva
    root = enter+0x79E; hook = enter+0x75; reject = enter+0x230
    def put(va, value):
        offset = view.file_offset(va-view.image_base, len(value)); data[offset:offset+len(value)] = value
    # Grow synthetic modal raw storage to contain these instructions, retaining
    # its RVA reservation. The fixture's simple 512-byte storage cannot hold it.
    modal_section = view.sections[1]
    extra = 4096-modal_section.raw_size
    insertion = modal_section.raw_offset+modal_section.raw_size
    data[insertion:insertion] = bytes(extra)
    struct.pack_into('<I', data, modal_section.header_offset+16, 4096)
    for section in view.sections[2:]:
        struct.pack_into('<I', data, section.header_offset+20, section.raw_offset+extra)
    struct.pack_into('<I', data, view.optional_offset+4, view.size_of_code+extra)
    view = pe.inspect_pe(bytes(data))
    put(enter+0x6B, tool.OWNER_CMP)
    put(hook, b'\x0f\x85'+struct.pack('<i', reject-hook-6))
    put(reject, bytes.fromhex('c744241c00000000619dc3'))
    wrapper = bytes.fromhex('9c608d442424e8')+struct.pack('<i', enter-root-11)+bytes.fromhex('619d5351525657e9')+struct.pack('<i', 0x422185-root-23)
    put(root, wrapper); put(0x422180, b'\xe9'+struct.pack('<i', root-0x422185))
    put(tool.NATIVE_CALLER, bytes.fromhex('e811340000'))
    put(0x41ED54, bytes.fromhex('8b1dd89951008935d8995100'))
    modal = dict(modal_entry_vas={'try_enter': enter, 'root_entry': root},
                 state_va=view.image_base+view.sections[2].rva, code_va=enter)
    return bytes(data), modal


class PortableTests(unittest.TestCase):
    def test_public_matrix_and_unknown_original_reject_before_parent_build(self):
        self.assertEqual(len(tool.RESOLUTIONS), 6)
        self.assertNotIn('3840x2160', tool.RESOLUTIONS)
        with patch.object(tool.parent_builder, 'build_candidate') as parent:
            for profile, resolution in (('framed','1024x768'), ('modalwidgets','3840x2160'), ('completehd','1024x768')):
                with self.subTest(profile=profile, resolution=resolution), self.assertRaises(ValueError):
                    tool.build_candidate(b'unknown', profile, resolution)
            parent.assert_not_called()

    def test_typed_ancestor_matrix_rejects_wrong_path_and_identity(self):
        for profile in tool.PROFILES:
            for resolution in tool.RESOLUTIONS:
                parent = typed_parent(profile, resolution)
                self.assertEqual(tool.modal_ancestor(parent, profile, resolution)['modal_state_offsets'], tool.canvas.STATE)
                for key, bad in (('profile','classic'), ('resolution','3840x2160'), ('schema','other'), ('stage','wrong'), ('recipe_revision','wrong')):
                    altered = deepcopy(parent); altered[key] = bad
                    with self.subTest(profile=profile, resolution=resolution, key=key), self.assertRaises(ValueError):
                        tool.modal_ancestor(altered, profile, resolution)
        parent = typed_parent(); parent['base_candidate']['predecessor']['base_candidate']['modal_state_offsets']['root_esp'] = 24
        with self.assertRaises(ValueError): tool.modal_ancestor(parent, 'completehd', '1024x768')

    def test_modal_addresses_derive_from_verified_entries_not_1024_constants(self):
        for pages in (35, 37):
            image, modal = native_fixture(pages)
            result = tool.derive_admission(image, image, modal)
            self.assertEqual(result.try_enter, modal['code_va'])
            self.assertEqual(result.wrapper_return, modal['modal_entry_vas']['root_entry']+11)
            self.assertEqual((result.hook-result.try_enter, result.reject-result.try_enter), (0x75,0x230))
            view = pe.inspect_pe(image)
            for va in (result.comparison, result.hook, result.root_wrapper, 0x422180, tool.NATIVE_CALLER):
                bad = bytearray(image); bad[view.file_offset(va-view.image_base,1)] ^= 1
                with self.subTest(va=hex(va)), self.assertRaises(ValueError):
                    tool.derive_admission(image, bytes(bad), modal)

    def test_gate_all_address_operands_and_branch_destinations_are_relative(self):
        _, admission = fixture()
        for code_va in (0x500000,0x648000,0x780000):
            gate, operands = tool.emit_gate(code_va, admission)
            self.assertEqual(len(gate),96)
            self.assertEqual(gate[4:10],bytes.fromhex('e8000000005f'))
            self.assertEqual({r['kind'] for r in operands},{'rel32','eip_relative_disp32'})
            for row in operands:
                value = struct.unpack_from('<i',gate,row['offset'])[0]
                anchor = code_va+row['offset']+4 if row['kind']=='rel32' else row['anchor']
                self.assertEqual(anchor+value,row['target'])
            accepted = 2+struct.unpack_from('<b',gate,1)[0]
            self.assertEqual(gate[accepted],0xE9)
            self.assertEqual(code_va+accepted+5+struct.unpack_from('<i',gate,accepted+1)[0],admission.accept)
            self.assertEqual(gate[accepted-2:accepted],b'\x61\x9d')

    def test_tail_extension_preserves_sections_bytes_and_relocations(self):
        for profile, count in (('completehd',12), ('modalwidgets',16)):
            parent, admission = fixture(count); before = pe.inspect_pe(parent)
            image, report = tool.extend_tail(parent, admission, profile); after = pe.inspect_pe(image)
            self.assertEqual(len(after.sections),count)
            self.assertEqual(after.sections[:-1],before.sections[:-1])
            self.assertEqual(pe._old_relocations(parent,before),pe._old_relocations(image,after))
            self.assertEqual(report['code_va'],before.image_base+before.image_size)
            permitted = set()
            restored = bytearray(image[:len(parent)])
            for edit in report['edits']:
                old,new=bytes.fromhex(edit['old_hex']),bytes.fromhex(edit['new_hex'])
                self.assertEqual(image[edit['offset']:edit['offset']+len(new)],new)
                if old:
                    self.assertEqual(parent[edit['offset']:edit['offset']+len(old)],old)
                    permitted.update(range(edit['offset'],edit['offset']+len(old)))
                    restored[edit['offset']:edit['offset']+len(old)]=old
            self.assertEqual(bytes(restored),parent)
            self.assertTrue(all(a==b or index in permitted for index,(a,b) in enumerate(zip(parent,image))))

    def test_tail_format_and_hook_mismatch_fail_closed(self):
        parent, admission = fixture(); view=pe.inspect_pe(parent)
        changes = ((view.sections[-1].header_offset,b'.wrong\0\0'),
                   (view.sections[-1].header_offset+36,struct.pack('<I',0xE0000020)),
                   (view.file_offset(admission.hook-view.image_base,1),b'\x90'))
        for offset, value in changes:
            altered=bytearray(parent);altered[offset:offset+len(value)]=value
            with self.subTest(offset=offset), self.assertRaises(ValueError):
                tool.extend_tail(bytes(altered),admission,'completehd')
        with self.assertRaises(ValueError):tool.extend_tail(parent,admission,'modalwidgets')

    def test_probe_binds_final_image_and_stalls_on_any_read_error(self):
        parent, admission=fixture();image,report=tool.extend_tail(parent,admission,'completehd')
        metadata=dict(schema=tool.SCHEMA,profile='completehd',resolution='1024x768',
                      stage=tool.stage('completehd'),candidate_sha256=tool.sha(image))
        probe,facts=tool.render_probe(image,metadata)
        self.assertTrue(probe.endswith('\r\n'))
        self.assertNotIn('\n',probe.replace('\r\n',''))
        self.assertGreater(facts['checked_bytes'],4096)
        self.assertTrue(facts['relocation_aware']);self.assertFalse(facts['mutable_data_included'])
        self.assertIn('((0x4617a0+@$t19-0x400000) & 0xffffffff)',probe)
        self.assertIn('OCEM_CONTRACT_PASS',probe.splitlines()[-2])
        self.assertFalse(any(line.startswith('.echo OCEM_CONTRACT_PASS') for line in probe.splitlines()))
        rows=[line for line in probe.splitlines() if 'OCEM_MISMATCH' in line]
        self.assertEqual(len(rows),facts['required_chunks'])
        for number,line in enumerate(rows):
            self.assertIn(f'(@$t18 == 0n{number})',line)
            self.assertIn(f'r @$t18=0n{number+1}',line)
        for missing in (0,len(rows)//2,len(rows)-1):
            counter=0
            for number in range(len(rows)):
                if number != missing and counter==number:counter+=1
            self.assertLess(counter,len(rows))
        altered=dict(metadata,candidate_sha256='0'*64)
        with self.assertRaises(ValueError):tool.render_probe(image,altered)

    def test_cli_rejects_unsafe_output_before_reading_original(self):
        with patch.object(tool,'build_candidate') as build:
            for target in ('C:/Clash/clash95.exe',str(ROOT/'candidate.exe'),'C:/ClashTests/bad.txt'):
                with self.subTest(target=target),self.assertRaises(ValueError):
                    cli.write_candidate('missing.exe',target,'completehd','1024x768')
            build.assert_not_called()


class OriginalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if ORIGINAL is None:raise unittest.SkipTest('--source-exe required; original-backed matrix case not run')
        cls.original=Path(ORIGINAL).read_bytes()
        cls.image,cls.metadata,cls.probe=tool.build_candidate(cls.original,PROFILE,RESOLUTION)

    def test_original_bound_successor_has_honest_scope_and_complete_replay(self):
        self.assertEqual(tool.sha(self.image),self.metadata['candidate_sha256'])
        self.assertFalse(self.metadata['runtime_executed'])
        self.assertFalse(self.metadata['bounded_small_world_integrated'])
        self.assertFalse(self.metadata['predecessor_probe_reusable'])
        append=self.metadata['edits'][-1]
        parent=bytearray(self.image[:append['offset']])
        for edit in self.metadata['edits'][:-1]:
            old=bytes.fromhex(edit['old_hex']);parent[edit['offset']:edit['offset']+len(old)]=old
        self.assertEqual(tool.sha(parent),self.metadata['base_candidate_sha256'])
        self.assertEqual(tool.sha(self.probe.encode()),self.metadata['probe_sha256'])


def main():
    global ORIGINAL,PROFILE,RESOLUTION
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-exe',type=Path)
    parser.add_argument('--profile',choices=tool.PROFILES,default=PROFILE)
    parser.add_argument('--resolution',choices=tool.RESOLUTIONS,default=RESOLUTION)
    args,remaining=parser.parse_known_args()
    ORIGINAL,PROFILE,RESOLUTION=args.source_exe,args.profile,args.resolution
    unittest.main(argv=[sys.argv[0],*remaining])


if __name__=='__main__':main()
