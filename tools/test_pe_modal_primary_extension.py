"""Independent PE replay/rebase fixtures; synthetic bytes, no process launch."""
from dataclasses import replace
import struct
import sys
from pathlib import Path
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.patcher import pe_extension as pe
from src.patcher import pe_modal_slots_extension as slots
from src.patcher import pe_modal_primary_extension as primary
from test_pe_army_extension import hook
from test_pe_extension import independent_image, rebase
from test_pe_modal_extension import independent_section_adjacency
from test_pe_modal_slots_extension import synthetic_complete, arguments as slots_arguments


def synthetic_slots():
    base=synthetic_complete()
    return slots._extend_verified_image(base,**slots_arguments(base)).image


def arguments(candidate):
    layout=primary.allocation_layout(candidate)
    code=bytearray(b'\x90'*6003)
    code[0]=0xB8;code[4094]=0xA1;code[5001]=0xE8;code[5006]=0xC3
    records=(pe.CodeRelocation(1,'abs32',0x402008,'old mapped BSS address'),
             pe.CodeRelocation(4095,'abs32',layout.code_va+5500,'unaligned cross-page new address'),
             pe.CodeRelocation(5002,'rel32',0x401100,'native relative call'))
    for row in records:
        value=row.target if row.kind=='abs32' else row.target-layout.code_va-row.offset-4
        struct.pack_into('<I',code,row.offset,value&0xffffffff)
    # Mixed E9/E8 and the ten-byte placeholder span match the emitter's shape;
    # instruction semantics and production identities belong to other fixtures.
    hooks=[]
    for i,(va,length) in enumerate(((0x4010A0,5),(0x4010B0,10),(0x4010C0,5),(0x4010D0,5),(0x4010E0,5))):
        site=hook(candidate,va,layout.code_va+32*i,length)
        if i>=2:site=replace(site,new=b'\xE8'+site.new[1:])
        hooks.append(site)
    return dict(code=bytes(code),code_va=layout.code_va,relocations=records,hooks=tuple(hooks),
        binding={'fixture':'non-runtime synthetic primary format'})


class PrimaryFormatTests(unittest.TestCase):
    def build(self,**changes):
        candidate=synthetic_slots()
        return primary._extend_verified_image(candidate,**(arguments(candidate)|changes))

    def test_thirteen_sections_preserve_old_headers_and_replay_every_edit(self):
        base=synthetic_slots();before=pe.inspect_pe(base);result=self.build();after=pe.inspect_pe(result.image)
        self.assertEqual(len(after.sections),13);self.assertEqual(after.sections[:12],before.sections)
        last=after.sections[-1]
        self.assertEqual(last.name.rstrip(b'\0'),b'.hdprim')
        self.assertEqual((last.header_offset,last.characteristics,last.virtual_size),(0x348,pe.RX_CODE,0x20000))
        self.assertFalse(last.characteristics&0x80000000)
        self.assertEqual((last.rva,last.raw_offset),(before.image_size,len(base)))
        self.assertEqual(after.image_size,before.image_size+0x20000)
        self.assertEqual(after.headers_size,1024)
        self.assertEqual(result.image[0x370:0x400],base[0x370:0x400])
        self.assertTrue(all(row['rva']==row['expected_rva'] for row in independent_section_adjacency(result.image)))
        replay=bytearray(base);changed=set()
        for row in result.edits:
            self.assertEqual(bytes(replay[row.offset:row.offset+len(row.old)]),row.old)
            self.assertEqual(row.va,before.image_base+row.rva)
            replay[row.offset:row.offset+len(row.old)]=row.new
            changed.update(range(row.offset,row.offset+len(row.old)))
        self.assertEqual(bytes(replay),result.image)
        self.assertTrue(all(byte==result.image[i] for i,byte in enumerate(base) if i not in changed))
        self.assertEqual([len(row.old) for row in result.edits[:5]],[5,10,5,5,5])
        for site,row in zip(arguments(base)['hooks'],result.metadata['hooks']):
            self.assertEqual(row['old_hex'],site.old.hex());self.assertEqual(row['new_hex'],site.new.hex())
            self.assertEqual(result.image[site.offset:site.offset+len(site.new)],site.new)
        for name in ('installation_ready','runtime_executed','manual_input_proof','promotion_ready'):
            self.assertFalse(result.metadata[name])
        self.assertFalse(result.installation_ready)

    def test_independent_loader_and_rebase_keep_all_old_and_exact_new_fixups(self):
        base=synthetic_slots();result=self.build();a=arguments(base);layout=primary.allocation_layout(base)
        old_memory,_,old_fields,_=independent_image(base)
        memory,sections,fields,directory=independent_image(result.image)
        self.assertEqual(fields,sorted(old_fields+[layout.code_rva+1,layout.code_rva+4095]))
        self.assertEqual(sections[-1][0],b'.hdprim')
        self.assertEqual(directory,(result.metadata['relocation_rva'],result.metadata['relocation_bytes']))
        for delta in (-0x100000,0x2100000):
            moved=rebase(memory,fields,delta);old_moved=rebase(old_memory,old_fields,delta)
            for rva in old_fields:self.assertEqual(moved[rva:rva+4],old_moved[rva:rva+4])
            for row in a['relocations']:
                offset=layout.code_rva+row.offset
                if row.kind=='abs32':self.assertEqual(struct.unpack_from('<I',moved,offset)[0],row.target+delta)
                else:self.assertEqual(moved[offset:offset+4],memory[offset:offset+4])
            for site in a['hooks']:
                displacement=struct.unpack_from('<i',moved,site.rva+1)[0]
                self.assertEqual(site.va+delta+5+displacement,site.relocations[0].target+delta)
                self.assertEqual(moved[site.rva:site.rva+len(site.new)],site.new)
        before=pe.inspect_pe(base);off=before.file_offset(before.relocation_rva,before.relocation_size)
        self.assertEqual(result.image[off:off+before.relocation_size],base[off:off+before.relocation_size])
        self.assertEqual(result.metadata['old_highlow_count'],len(old_fields))
        self.assertEqual(result.metadata['new_highlow_count'],2)
        self.assertEqual(result.metadata['removed_highlow'],[])

    def test_declared_hook_absolute_field_is_merged_and_rebased(self):
        base=synthetic_slots();a=arguments(base);sites=list(a['hooks']);site=sites[0]
        target=a['code_va']+256
        sites[0]=replace(site,new=b'\xB8'+struct.pack('<I',target),
            relocations=(pe.CodeRelocation(1,'abs32',target,'synthetic explicit hook address'),))
        result=self.build(hooks=tuple(sites));memory,_,fields,_=independent_image(result.image)
        _,_,old_fields,_=independent_image(base)
        expected=sorted(old_fields+[primary.allocation_layout(base).code_rva+1,
            primary.allocation_layout(base).code_rva+4095,site.rva+1])
        self.assertEqual(fields,expected)
        self.assertEqual(struct.unpack_from('<I',rebase(memory,fields,0x110000),site.rva+1)[0],target+0x110000)
        self.assertEqual(result.metadata['new_highlow_count'],3)

    def test_header_collision_wrong_layout_permissions_and_gaps_fail_closed(self):
        base=synthetic_slots();view=pe.inspect_pe(base)
        for wrong in (synthetic_complete(),self.build().image):
            with self.assertRaisesRegex(ValueError,'twelve-section'):primary.allocation_layout(wrong)
        for offset in (0x348,0x34F,0x36F):
            bad=bytearray(base);bad[offset]=1
            with self.subTest(offset=offset),self.assertRaisesRegex(ValueError,'header'):
                primary.allocation_layout(bytes(bad))
        bad=bytearray(base);bad[view.sections[-1].header_offset]=ord('X')
        with self.assertRaisesRegex(ValueError,'twelve-section'):primary.allocation_layout(bytes(bad))
        for index in (-5,-4,-3,-2,-1):
            bad=bytearray(base);position=view.sections[index].header_offset+36
            # Flip WRITE only, leaving code-size classification unchanged.
            struct.pack_into('<I',bad,position,view.sections[index].characteristics^0x80000000)
            with self.subTest(index=index),self.assertRaisesRegex(ValueError,'protections'):
                primary.allocation_layout(bytes(bad))
        bad=bytearray(base)
        struct.pack_into('<I',bad,view.sections[-2].header_offset+8,view.sections[-2].raw_size)
        with self.assertRaisesRegex(ValueError,'nonadjacent'):primary.allocation_layout(bytes(bad))
        bad=bytearray(base);struct.pack_into('<I',bad,view.optional_offset+60,512)
        with self.assertRaises(ValueError):primary.allocation_layout(bytes(bad))

    def test_bad_address_size_old_bytes_identity_and_five_hook_contract_fail(self):
        base=synthetic_slots();a=arguments(base);site=a['hooks'][0]
        cases=(dict(code_va=a['code_va']+4096),dict(code=b''),dict(code=bytearray(a['code'])),
            dict(code=b'\x90'*primary.CODE_RESERVATION),dict(hooks=()),dict(hooks=a['hooks'][:-1]),
            dict(hooks=a['hooks']+(site,)),dict(relocations=None),dict(binding=None),
            dict(hooks=(replace(site,old=b'\0'*5),)+a['hooks'][1:]),
            dict(hooks=(replace(site,va=site.va+1),)+a['hooks'][1:]),
            dict(hooks=(replace(site,offset=site.offset+1),)+a['hooks'][1:]),
            dict(hooks=(replace(site,new=site.new[:-1]),)+a['hooks'][1:]))
        for changes in cases:
            with self.subTest(changes=tuple(changes)),self.assertRaises(ValueError):self.build(**changes)
        # Code alone fits, but the complete relocation directory does not.
        with self.assertRaisesRegex(ValueError,'reservation'):
            self.build(code=b'\x90'*(primary.CODE_RESERVATION-1),relocations=())

    def test_overlapping_hooks_and_displaced_old_highlow_are_rejected(self):
        base=synthetic_slots();a=arguments(base)
        for replacement in (a['hooks'][0],hook(base,0x4010A3,a['code_va']),
                            hook(base,0x401000,a['code_va']),hook(base,0x401003,a['code_va'])):
            sites=list(a['hooks']);sites[1]=replacement
            with self.subTest(va=replacement.va),self.assertRaises(ValueError):self.build(hooks=tuple(sites))
        # Same length is insufficient: the entire hook must map executable data.
        readonly=next(s for s in pe.inspect_pe(base).sections if s.raw_offset and not s.characteristics&0x20000000)
        with self.assertRaisesRegex(ValueError,'not executable'):
            self.build(hooks=(hook(base,0x400000+readonly.rva+0x80,a['code_va']),)+a['hooks'][1:])

    def test_invalid_code_relocation_kind_overlap_value_and_target_fail(self):
        a=arguments(synthetic_slots())
        for mode in ('duplicate','overlap','wrong_value','unmapped','nonexec','offset','boolean_offset',
                     'past_end','kind','purpose','overflow_target','malformed'):
            code=bytearray(a['code']);rows=list(a['relocations'])
            if mode=='duplicate':rows.append(rows[0])
            elif mode=='overlap':
                # Both operands independently encode valid mapped destinations;
                # only their overlapping four-byte spans make them invalid.
                code[10:15]=bytes(5)
                rows.extend((pe.CodeRelocation(10,'rel32',a['code_va']+14,'first overlap'),
                             pe.CodeRelocation(11,'rel32',a['code_va']+15,'second overlap')))
            elif mode=='wrong_value':code[1]^=1
            elif mode=='unmapped':rows[0]=replace(rows[0],target=0x1234);struct.pack_into('<I',code,1,0x1234)
            elif mode=='nonexec':
                rows[-1]=replace(rows[-1],target=0x402008)
                struct.pack_into('<I',code,5002,(0x402008-a['code_va']-5006)&0xffffffff)
            elif mode=='offset':rows[0]=replace(rows[0],offset=-1)
            elif mode=='boolean_offset':rows[0]=replace(rows[0],offset=True)
            elif mode=='past_end':rows[0]=replace(rows[0],offset=len(code)-3)
            elif mode=='kind':rows[0]=replace(rows[0],kind='HIGH')
            elif mode=='purpose':rows[0]=replace(rows[0],purpose=' ')
            elif mode=='overflow_target':rows[0]=replace(rows[0],target=1<<32)
            else:rows[0]=object()
            with self.subTest(mode=mode):
                message='overlapping primary relocation' if mode in ('duplicate','overlap') else '.*'
                with self.assertRaisesRegex(ValueError,message):self.build(code=bytes(code),relocations=tuple(rows))

    def test_malformed_historical_relocations_fail_before_any_output(self):
        base=synthetic_slots();a=arguments(base);view=pe.inspect_pe(base)
        offset=view.file_offset(view.relocation_rva,view.relocation_size)
        for mode in ('kind','block_size','page','duplicate'):
            bad=bytearray(base)
            if mode=='kind':struct.pack_into('<H',bad,offset+8,0xA001)
            elif mode=='block_size':struct.pack_into('<I',bad,offset+4,9)
            elif mode=='page':struct.pack_into('<I',bad,offset,0x1001)
            else:bad[offset+10:offset+12]=bad[offset+8:offset+10]
            with self.subTest(mode=mode),self.assertRaises(ValueError):
                primary._extend_verified_image(bytes(bad),**a)
        self.assertEqual(synthetic_slots(),base)

    def test_invalid_hook_relocation_value_permissions_and_declared_fields_fail(self):
        base=synthetic_slots();a=arguments(base);site=a['hooks'][0];row=site.relocations[0]
        for mode in ('duplicate','wrong_value','nonexec','kind','offset','missing','malformed'):
            changed=site
            if mode=='duplicate':changed=replace(site,relocations=(row,row))
            elif mode=='wrong_value':changed=replace(site,new=site.new[:1]+bytes(4))
            elif mode=='nonexec':
                changed=replace(site,new=b'\xE9'+struct.pack('<i',0x402008-site.va-5),
                    relocations=(replace(row,target=0x402008),))
            elif mode=='kind':changed=replace(site,relocations=(replace(row,kind='HIGH'),))
            elif mode=='offset':changed=replace(site,relocations=(replace(row,offset=2),))
            elif mode=='missing':changed=replace(site,relocations=None)
            else:changed=replace(site,relocations=(object(),))
            with self.subTest(mode=mode),self.assertRaises(ValueError):self.build(hooks=(changed,)+a['hooks'][1:])


if __name__=='__main__':unittest.main(verbosity=2)
