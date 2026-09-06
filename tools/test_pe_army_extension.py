"""Pure PE edits/rebases and optional SEC_IMAGE admission; never execute code.

Windows admission creates exclusive .bin fixtures outside the repo, opens only
read-only image-section handles, and closes them. No view, process, debugger,
game entry or proprietary runtime candidate is launched. Test files are retained.
"""
from __future__ import annotations

from dataclasses import replace
import os
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.patcher import pe_army_extension as army
from src.patcher import pe_extension as pe
import test_pe_modal_extension as previous
from test_pe_modal_extension import independent_section_adjacency, native_image_section
from test_pe_extension import independent_image, rebase

ORIGINAL=Path('C:/Clash/clash95.exe')
C099=Path('C:/ClashTests/hd-completion/framed-modal-canvas-v2-1024x768-build-20260906-054000/clash95_modal_canvas_1024x768_v2.exe')
C099_SHA='c09940fac48e903538dd3a35688efb5ca5a65edaa6ad42cf6c804ca1c008d18d'
RESOLUTIONS=('800x600','1024x768','1280x720','1280x960','1920x1080','802x602')


def synthetic_modal():
    return previous.ModalFormatTests().build().image


def payload(layout):
    code=bytearray(b'\x90'*6003)
    code[0]=0xB8;code[4094]=0xA1;code[5001]=0xE8;code[5006]=0xC3
    records=(pe.CodeRelocation(1,'abs32',layout.state_va if layout.state_va else 0x402008,'state/BSS address'),
             pe.CodeRelocation(4095,'abs32',layout.code_va+5500,'unaligned cross-page code address'),
             pe.CodeRelocation(5002,'rel32',0x401100,'native relative call'))
    for row in records:
        struct.pack_into('<I',code,row.offset,row.target if row.kind=='abs32'
                         else (row.target-layout.code_va-row.offset-4)&0xFFFFFFFF)
    return bytes(code),records


def hook(candidate,va,target,length=5):
    image=pe.inspect_pe(candidate);off=image.file_offset(va-image.image_base,length)
    return pe.HookPatch(off,va-image.image_base,va,candidate[off:off+length],
        b'\xe9'+struct.pack('<i',target-va-5)+b'\x90'*(length-5),'synthetic source-bound hook',
        (pe.CodeRelocation(1,'rel32',target,'relative army entry'),))


def arguments(candidate,state_bytes=4096,actual=False):
    layout=army.allocation_layout(candidate,state_bytes=state_bytes);code,rows=payload(layout)
    # On actual source only the verified native 423420 six PUSH entry is used;
    # synthetic tests have an independent five-NOP slot with no old relocation.
    site=hook(candidate,0x423420 if actual else 0x401060,layout.code_va,6 if actual else 5)
    return dict(code=code,code_va=layout.code_va,state_va=layout.state_va,state_bytes=state_bytes,
                relocations=rows,hooks=(site,),removed_highlow_rvas=(),
                binding={'fixture':'offline allocation, not executable semantics'})


class ArmyFormatTests(unittest.TestCase):
    def build(self,**overrides):
        candidate=synthetic_modal()
        return army._extend_verified_image(candidate,**(arguments(candidate)|overrides))

    def test_layout_keeps_old_headers_offsets_and_retires_only_new_stage_scratch(self):
        candidate=synthetic_modal();args=arguments(candidate);result=self.build()
        old=pe.inspect_pe(candidate);new=pe.inspect_pe(result.image)
        self.assertEqual(new.sections[:10],old.sections)
        self.assertEqual(new.headers_size,old.headers_size)
        self.assertEqual([s.header_offset for s in new.sections[-2:]],[0x2F8,0x320])
        self.assertEqual([s.name.rstrip(b'\0') for s in new.sections[-2:]],[b'.hdarmy',b'.hdarw'])
        self.assertEqual([s.characteristics for s in new.sections[-2:]],[0x60000020,0xC0000040])
        self.assertEqual(result.image[0x348:0x400],candidate[0x348:0x400])
        self.assertEqual(new.sections[-2].virtual_size,0x20000)
        self.assertEqual(new.sections[-1].rva,new.sections[-2].rva+0x20000)
        self.assertEqual(result.image[new.sections[-1].raw_offset:],bytes(4096))
        self.assertEqual(result.metadata['retired_header_scratch'],dict(start=0x300,end_exclusive=0x348,legacy_day_diagnostic_allowed=False))
        replay=bytearray(candidate);touched=set()
        for edit in result.edits:
            self.assertEqual(replay[edit.offset:edit.offset+len(edit.old)],edit.old)
            replay[edit.offset:edit.offset+len(edit.old)]=edit.new
            touched.update(range(edit.offset,edit.offset+len(edit.old)))
            self.assertEqual(edit.va,old.image_base+edit.rva)
        self.assertEqual(bytes(replay),result.image)
        self.assertTrue(all(byte==result.image[i] for i,byte in enumerate(candidate) if i not in touched))
        for name in ('installation_ready','runtime_executed','manual_input_proof','promotion_ready'):
            self.assertFalse(result.metadata[name])
        self.assertEqual(result.metadata['hooks'][0]['new_hex'],args['hooks'][0].new.hex())

    def test_independent_rebase_preserves_old_fixups_and_relative_displacements(self):
        candidate=synthetic_modal();result=self.build();layout=army.allocation_layout(candidate)
        old_memory,old_sections,old_fields,_=independent_image(candidate)
        memory,sections,fields,_=independent_image(result.image)
        self.assertEqual(fields,sorted(old_fields+[layout.code_rva+1,layout.code_rva+4095]))
        for delta in (-0x100000,0x2100000):
            rebased=rebase(memory,fields,delta);old_rebased=rebase(old_memory,old_fields,delta)
            for rva in old_fields:self.assertEqual(rebased[rva:rva+4],old_rebased[rva:rva+4])
            self.assertEqual(struct.unpack_from('<I',rebased,layout.code_rva+1)[0],layout.state_va+delta)
            self.assertEqual(struct.unpack_from('<I',rebased,layout.code_rva+4095)[0],layout.code_va+5500+delta)
            self.assertEqual(rebased[layout.code_rva+5002:layout.code_rva+5006],memory[layout.code_rva+5002:layout.code_rva+5006])
            self.assertEqual(rebased[0x1061:0x1065],memory[0x1061:0x1065])
        before=pe.inspect_pe(candidate);off=before.file_offset(before.relocation_rva,before.relocation_size)
        self.assertEqual(result.image[off:off+before.relocation_size],candidate[off:off+before.relocation_size])

    def test_displaced_absolute_operand_removal_is_exact(self):
        candidate=synthetic_modal();a=arguments(candidate)
        site=hook(candidate,0x401000,a['code_va'])
        result=army._extend_verified_image(candidate,**(a|dict(hooks=(site,),removed_highlow_rvas=(0x1001,))))
        _,_,fields,_=independent_image(result.image)
        self.assertNotIn(0x1001,fields)
        for removals in ((),(0x1001,0x1009),(0x1001,0x1001)):
            with self.subTest(removals=removals),self.assertRaises(pe.PEExtensionError):
                army._extend_verified_image(candidate,**(a|dict(hooks=(site,),removed_highlow_rvas=removals)))
        partial=hook(candidate,0x401002,a['code_va'])
        with self.assertRaisesRegex(pe.PEExtensionError,'partially'):
            army._extend_verified_image(candidate,**(a|dict(hooks=(partial,),removed_highlow_rvas=(0x1001,))))

    def test_new_absolute_hook_targets_rw_and_rebases_at_its_actual_field(self):
        candidate=synthetic_modal();a=arguments(candidate)
        old=a['hooks'][0]
        site=replace(old,new=b'\xb8'+struct.pack('<I',a['state_va']+4095),
                     relocations=(pe.CodeRelocation(1,'abs32',a['state_va']+4095,'last RW byte'),))
        result=army._extend_verified_image(candidate,**(a|dict(hooks=(site,))))
        memory,_,fields,_=independent_image(result.image)
        self.assertIn(site.rva+1,fields)
        for delta in (-0x100000,0x2100000):
            actual=struct.unpack_from('<I',rebase(memory,fields,delta),site.rva+1)[0]
            self.assertEqual(actual,a['state_va']+4095+delta)
        bad=replace(site,new=b'\xb8'+struct.pack('<I',a['state_va']+4096),
                    relocations=(replace(site.relocations[0],target=a['state_va']+4096),))
        with self.assertRaises(pe.PEExtensionError):
            army._extend_verified_image(candidate,**(a|dict(hooks=(bad,))))

    def test_optional_rw_full_native_backing_and_boundaries(self):
        candidate=synthetic_modal()
        for size in (0,4096,0x8000,0x4C000,army.MAX_STATE_BYTES):
            with self.subTest(size=size):
                a=arguments(candidate,size);r=army._extend_verified_image(candidate,**a)
                p=pe.inspect_pe(r.image)
                self.assertEqual(len(p.sections),11+bool(size))
                self.assertEqual(p.sections[-1].characteristics,0xC0000040 if size else 0x60000020)
                self.assertEqual(r.metadata['state_bytes'],size)
                self.assertTrue(all(s['rva']==s['expected_rva'] for s in independent_section_adjacency(r.image)))
        for size in (-4096,1,4095,army.MAX_STATE_BYTES+4096,True):
            with self.assertRaises(pe.PEExtensionError):army.allocation_layout(candidate,state_bytes=size)

    def test_nonzero_header_and_legacy_scratch_collision_fail(self):
        candidate=synthetic_modal()
        for offset in (0x2F8,0x300,0x320,0x347):
            data=bytearray(candidate);data[offset]=1
            with self.subTest(offset=offset),self.assertRaises(pe.PEExtensionError):army.allocation_layout(bytes(data))
        self.assertEqual(army.RETIRED_HEADER_SCRATCH,(0x300,0x348))

    def test_existing_section_gap_is_not_admitted(self):
        candidate=bytearray(synthetic_modal());p=pe.inspect_pe(bytes(candidate))
        struct.pack_into('<I',candidate,p.sections[-2].header_offset+8,p.sections[-2].raw_size)
        pe.inspect_pe(bytes(candidate))  # The legacy permissive parser allows a gap.
        with self.assertRaisesRegex(pe.PEExtensionError,'nonadjacent'):army.allocation_layout(bytes(candidate))

    def test_wrong_layout_addresses_and_oversized_payload_fail(self):
        a=arguments(synthetic_modal())
        for key,value in [('code_va',a['code_va']+4096),('state_va',a['state_va']+4096),('code',b''),
                          ('code',b'\x90'*army.CODE_RESERVATION),('hooks',()),('relocations',None)]:
            with self.subTest(key=key),self.assertRaises(pe.PEExtensionError):self.build(**{key:value})

    def test_relocation_alias_target_and_value_guards(self):
        a=arguments(synthetic_modal())
        for kind in ('duplicate','overlap','unmapped','nonexec','wrong_value'):
            code=bytearray(a['code']);rows=list(a['relocations'])
            if kind=='duplicate':rows.append(rows[0])
            elif kind=='overlap':rows.append(replace(rows[0],offset=2))
            elif kind=='unmapped':rows[0]=replace(rows[0],target=0x1234);struct.pack_into('<I',code,1,0x1234)
            elif kind=='nonexec':rows[-1]=replace(rows[-1],target=a['state_va']);struct.pack_into('<I',code,5002,(a['state_va']-a['code_va']-5006)&0xFFFFFFFF)
            else:code[1]^=1
            with self.subTest(kind=kind),self.assertRaises(pe.PEExtensionError):self.build(code=bytes(code),relocations=tuple(rows))
        with self.assertRaises(pe.PEExtensionError):self.build(hooks=(replace(a['hooks'][0],old=b'\0'*5),))


@unittest.skipUnless(ORIGINAL.is_file(),'user-owned original unavailable')
class CanonicalArmyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original=ORIGINAL.read_bytes();pe._identity(cls.original,pe.ORIGINAL_SHA256,'original fixture')

    def test_all_twelve_reconstructed_inputs_and_windows_image_admission(self):
        folder=Path(tempfile.mkdtemp(prefix='clash-pe-army-fixtures-',dir='C:/ClashTests')) if os.name=='nt' else None
        print('Retained SEC_IMAGE fixture directory:',folder,flush=True)
        hashes={}
        for resolution in RESOLUTIONS:
            for minimap in (False,True):
                with self.subTest(resolution=resolution,minimap=minimap):
                    base,metadata,pins=army._reconstruct_modal(self.original,resolution,minimap)
                    a=arguments(base,0x4C000,actual=True)
                    self.assertEqual(a['hooks'][0].old,bytes.fromhex('535152565755'))
                    result=army._extend_verified_image(base,**a)
                    hashes[resolution,minimap]=pe._sha(base)
                    self.assertTrue(all(s['rva']==s['expected_rva'] for s in independent_section_adjacency(result.image)))
                    before=pe.inspect_pe(base);after=pe.inspect_pe(result.image)
                    self.assertEqual(after.sections[:10],before.sections)
                    if resolution=='1024x768' and minimap:self.assertEqual(pe._sha(base),C099_SHA)
                    if folder:
                        path=folder/f'{resolution}-minimap-{int(minimap)}-allocation.bin'
                        with path.open('xb') as out:out.write(result.image)
                        self.assertEqual(native_image_section(path),dict(accepted=True,error=0,view_mapped=False,process_started=False))
        self.assertTrue(all(hashes[r,False]!=hashes[r,True] for r in RESOLUTIONS))

    def test_public_binding_rejects_stale_imported_builder_and_noncanonical_bytes(self):
        if not C099.is_file():self.skipTest('retained exact C099 input unavailable')
        base=C099.read_bytes();self.assertEqual(pe._sha(base),C099_SHA)
        a=arguments(base,actual=True);a.pop('binding')
        from tools import build_framed_modal_candidate as cached
        with patch.object(cached,'build_candidate',side_effect=AssertionError('must not use imported cache')):
            result=army.extend_modal_candidate_with_army(self.original,base,expected_candidate_sha256=C099_SHA,
                resolution='1024x768',minimap_viewport=True,validation_stage=army.STAGE,**a)
        self.assertEqual(result.metadata['base_candidate_sha256'],C099_SHA)
        self.assertTrue(result.metadata['minimap_viewport'])
        changed=bytearray(base);changed[0x1234]^=1
        with self.assertRaisesRegex(pe.PEExtensionError,'entire source-reconstructed'):
            army.extend_modal_candidate_with_army(self.original,bytes(changed),expected_candidate_sha256=pe._sha(bytes(changed)),
                resolution='1024x768',minimap_viewport=True,validation_stage=army.STAGE,**a)
        with self.assertRaisesRegex(pe.PEExtensionError,'entire source-reconstructed'):
            army.extend_modal_candidate_with_army(self.original,base,expected_candidate_sha256=C099_SHA,
                resolution='1024x768',minimap_viewport=False,validation_stage=army.STAGE,**a)

    def test_public_stage_original_source_and_options_fail_closed(self):
        if not C099.is_file():self.skipTest('retained exact C099 input unavailable')
        base=C099.read_bytes();a=arguments(base,actual=True);a.pop('binding')
        args=dict(expected_candidate_sha256=C099_SHA,resolution='1024x768',minimap_viewport=True,
                  validation_stage=army.STAGE,**a)
        for override in ({'validation_stage':army.BASE_STAGE},{'minimap_viewport':None},{'expected_candidate_sha256':'0'*64}):
            with self.assertRaises(pe.PEExtensionError):army.extend_modal_candidate_with_army(self.original,base,**(args|override))
        with self.assertRaises(pe.PEExtensionError):army.extend_modal_candidate_with_army(b'wrong',base,**args)
        with patch.dict(army.PINNED_SOURCES,{'tools/build_framed_modal_candidate.py':'0'*64}):
            with self.assertRaisesRegex(pe.PEExtensionError,'SHA-256'):army.extend_modal_candidate_with_army(self.original,base,**args)


if __name__=='__main__':unittest.main(verbosity=2)
