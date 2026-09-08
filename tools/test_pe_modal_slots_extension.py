"""Independent PE layout, replay, rebase and fail-closed allocation fixtures."""
from dataclasses import replace
import struct
import sys
from pathlib import Path
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.patcher import pe_extension as pe
from src.patcher import pe_army_extension as army
from src.patcher import pe_modal_slots_extension as slots
from test_pe_army_extension import synthetic_modal, arguments as army_arguments, hook
from test_pe_extension import independent_image, rebase
from test_pe_modal_extension import independent_section_adjacency


def synthetic_complete():
    image=synthetic_modal()
    return army._extend_verified_image(image,**army_arguments(image,state_bytes=0)).image


def arguments(candidate):
    layout=slots.allocation_layout(candidate)
    code=bytearray(b'\x90'*6003)
    code[0]=0xB8;code[4094]=0xA1;code[5001]=0xE8;code[5006]=0xC3
    records=(pe.CodeRelocation(1,'abs32',0x402008,'old mapped address'),
             pe.CodeRelocation(4095,'abs32',layout.code_va+5500,'unaligned cross-page new address'),
             pe.CodeRelocation(5002,'rel32',0x401100,'native relative call'))
    for row in records:
        value=row.target if row.kind=='abs32' else row.target-layout.code_va-row.offset-4
        struct.pack_into('<I',code,row.offset,value&0xffffffff)
    return dict(code=bytes(code),code_va=layout.code_va,relocations=records,
        hooks=(hook(candidate,0x401080,layout.code_va),),binding={'fixture':'non-runtime synthetic format'})


class SlotsFormatTests(unittest.TestCase):
    def build(self,**changes):
        candidate=synthetic_complete()
        return slots._extend_verified_image(candidate,**(arguments(candidate)|changes))

    def test_twelve_sections_preserve_old_headers_and_replay_every_edit(self):
        base=synthetic_complete();before=pe.inspect_pe(base);result=self.build();after=pe.inspect_pe(result.image)
        self.assertEqual(len(after.sections),12);self.assertEqual(after.sections[:11],before.sections)
        self.assertEqual(after.sections[-1].name,b'.hdslots')
        self.assertEqual((after.sections[-1].header_offset,after.sections[-1].characteristics),(0x320,pe.RX_CODE))
        self.assertEqual(result.image[0x348:0x400],base[0x348:0x400])
        self.assertTrue(all(row['rva']==row['expected_rva'] for row in independent_section_adjacency(result.image)))
        replay=bytearray(base);changed=set()
        for row in result.edits:
            self.assertEqual(bytes(replay[row.offset:row.offset+len(row.old)]),row.old)
            replay[row.offset:row.offset+len(row.old)]=row.new
            changed.update(range(row.offset,row.offset+len(row.old)))
        self.assertEqual(bytes(replay),result.image)
        self.assertTrue(all(byte==result.image[i] for i,byte in enumerate(base) if i not in changed))

    def test_independent_loader_and_rebase_keep_every_old_fixup(self):
        base=synthetic_complete();result=self.build();layout=slots.allocation_layout(base)
        old_memory,_,old_fields,_=independent_image(base)
        memory,_,fields,_=independent_image(result.image)
        self.assertEqual(fields,sorted(old_fields+[layout.code_rva+1,layout.code_rva+4095]))
        for delta in (-0x100000,0x2100000):
            moved=rebase(memory,fields,delta);old_moved=rebase(old_memory,old_fields,delta)
            for rva in old_fields:self.assertEqual(moved[rva:rva+4],old_moved[rva:rva+4])
            self.assertEqual(struct.unpack_from('<I',moved,layout.code_rva+1)[0],0x402008+delta)
            self.assertEqual(struct.unpack_from('<I',moved,layout.code_rva+4095)[0],layout.code_va+5500+delta)
            self.assertEqual(moved[layout.code_rva+5002:layout.code_rva+5006],memory[layout.code_rva+5002:layout.code_rva+5006])
        before=pe.inspect_pe(base);off=before.file_offset(before.relocation_rva,before.relocation_size)
        self.assertEqual(result.image[off:off+before.relocation_size],base[off:off+before.relocation_size])

    def test_header_collision_wrong_layout_and_gap_are_rejected(self):
        base=synthetic_complete()
        with self.assertRaises(ValueError):slots.allocation_layout(synthetic_modal())
        for offset in (0x320,0x327,0x33F,0x347):
            bad=bytearray(base);bad[offset]=1
            with self.assertRaisesRegex(ValueError,'header'):slots.allocation_layout(bytes(bad))
        bad=bytearray(base);view=pe.inspect_pe(base)
        struct.pack_into('<I',bad,view.sections[-1].header_offset+36,0xE0000020)
        with self.assertRaisesRegex(ValueError,'protections'):slots.allocation_layout(bytes(bad))
        struct.pack_into('<I',bad,view.sections[-1].header_offset+36,pe.RX_CODE)
        struct.pack_into('<I',bad,view.sections[-3].header_offset+8,view.sections[-3].raw_size)
        with self.assertRaisesRegex(ValueError,'nonadjacent'):slots.allocation_layout(bytes(bad))

    def test_bad_address_payload_old_bytes_and_conflicting_hook_fail(self):
        base=synthetic_complete();a=arguments(base)
        for overrides in (dict(code_va=a['code_va']+4096),dict(code=b''),dict(code=b'\x90'*slots.CODE_RESERVATION),
            dict(hooks=()),dict(hooks=a['hooks']*2),dict(relocations=None),dict(hooks=(replace(a['hooks'][0],old=b'\0'*5),))):
            with self.assertRaises(ValueError):self.build(**overrides)
        # A hook that would displace an existing HIGHLOW is rejected; this
        # allocator has no option to silently remove historical fixups.
        with self.assertRaises(ValueError):self.build(hooks=(hook(base,0x401000,a['code_va']),))

    def test_bad_relocation_alias_overlap_value_and_target_fail(self):
        a=arguments(synthetic_complete())
        for mode in ('duplicate','overlap','wrong_value','unmapped','nonexec'):
            code=bytearray(a['code']);rows=list(a['relocations'])
            if mode=='duplicate':rows.append(rows[0])
            elif mode=='overlap':rows.append(replace(rows[0],offset=2))
            elif mode=='wrong_value':code[1]^=1
            elif mode=='unmapped':rows[0]=replace(rows[0],target=0x1234);struct.pack_into('<I',code,1,0x1234)
            else:
                rows[-1]=replace(rows[-1],target=0x402008)
                struct.pack_into('<I',code,5002,(0x402008-a['code_va']-5006)&0xffffffff)
            with self.subTest(mode=mode),self.assertRaises(ValueError):self.build(code=bytes(code),relocations=tuple(rows))


if __name__=='__main__':unittest.main(verbosity=2)
