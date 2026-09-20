"""Menu-only native CPU regressions and original-backed image reconstruction."""
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
from src.patcher import classic_menu_candidate as tool
from src.patcher import partial_tile_clip as clip
from src.patcher import pe_extension as pe
import test_modal_widget_bounds as fixture
from test_pe_extension import independent_image, rebase
from test_build_framed_modal_candidate import replay


def cpu_program(cases, width, height, records):
    bundle = tool.emit_guards(base_va=fixture.CODE, width=width, height=height, records=records, holder=fixture.DATA+0x400)
    a = clip._Assembler(fixture.BASE+0x1000); a.emit('9c60'); seeds=[]
    for index, (name,x,y,callback,holder,flags) in enumerate(cases):
        for offset,value in ((0,x),(4,y),(12,holder),(32,callback)):
            a.emit('c705');a.u32(fixture.DESCRIPTOR+offset);a.u32(value)
        registers=[0x12345678,0x23456789,0x3456789A,0x456789AB,0,0x56789ABC,0x6789ABCD,0x789ABCDE]
        registers[0 if name=='single' else 3]=fixture.DESCRIPTOR
        seeds.append(registers)
        for register,value in enumerate(registers):
            if register!=4:a.emit(f'{0xb8+register:02x}');a.u32(value)
        target=fixture.OUTPUT+index*64
        a.emit('8925');a.u32(target+36)
        a.emit('68');a.u32(flags);a.emit('9d')
        a.emit('e8');a.u32(bundle.entries[name]-a.base-len(a.code)-4);a.emit('90')
        a.emit('9c8f05');a.u32(target+32)
        for register in range(8):
            a.emit('89'+f'{5+(register<<3):02x}');a.u32(target+register*4)
        for offset,output in ((0,40),(4,44),(12,48),(32,52)):
            a.emit('a1');a.u32(fixture.DESCRIPTOR+offset);a.emit('a3');a.u32(target+output)
    a.emit('619d31c0c3');driver=a.finish()
    if len(driver)>=fixture.CODE-a.base:raise ValueError('fixture driver overlaps actual guard')
    code=bytearray(0x100000);code[0x1000:0x1000+len(driver)]=driver
    code[fixture.CODE-fixture.BASE:fixture.CODE-fixture.BASE+len(bundle.code)]=bundle.code
    return bytes(code),seeds


class MenuSourceTests(unittest.TestCase):
    def test_source_pins_and_resolution_threshold(self):
        self.assertTrue(tool.source_status()['passed'])
        for resolution in ('800x600','1024x768','1142x768','invalid'):
            self.assertFalse(tool.supports(resolution))
        for resolution in ('1144x768','1280x720','1366x768','3840x2160'):
            self.assertTrue(tool.supports(resolution))
        with self.assertRaises(ValueError):tool.build_candidate(b'not original','1920x1080')

    def test_guard_contains_only_menu_records_and_checked_relocation_fields(self):
        records=((832,444,0x447780),(997,436,0x447760))
        a=tool.emit_guards(base_va=0x600000,width=1920,height=1080,records=records)
        b=tool.emit_guards(base_va=0x600000,width=1920,height=1080,records=records)
        self.assertEqual(a,b)
        self.assertEqual(len(clip.absolute_relocation_offsets(a)),6)
        self.assertTrue(all(row.kind=='abs32' for row in a.relocations))
        self.assertEqual(set(row.target for row in a.relocations),{tool.MENU_SPRITES,0x447780,0x447760})
        self.assertFalse(a.installation_ready)
        self.assertEqual(set(a.entries),{'single','list'})
        for altered in ((),records*2,((1,1,0x447780),),((832,444,True),)):
            with self.assertRaises(ValueError):tool.emit_guards(base_va=0x600000,width=1920,height=1080,records=altered)


class MenuCpuTests(unittest.TestCase):
    setUpClass=classmethod(fixture.NativeGuardTests.setUpClass.__func__)

    def execute(self,cases,width,height,records):
        code,seeds=cpu_program(cases,width,height,records)
        path=self.folder/'menu-guard-input.bin'
        if self.runner:
            path.write_bytes(code);command=[str(self.runner),str(path),str(len(cases)*64)]
            flags={'creationflags':subprocess.CREATE_NO_WINDOW}
        else:
            path.write_bytes(fixture.elf(code,len(cases)*64));path.chmod(0o700)
            command=[str(path)];flags={}
        result=subprocess.run(command,capture_output=True,timeout=20,**flags)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(len(result.stdout),len(cases)*64)
        return list(struct.iter_unpack('<16I',result.stdout)),seeds

    def test_all_menu_profiles_preserve_registers_stack_flags_and_unknown_descriptors(self):
        for width,height in ((1144,768),(1280,720),(1280,960),(1366,768),(1920,1080),(2560,1440),(3440,1440),(3840,2160)):
            ox,oy=(width-640)//2,(height-480)//2
            records=tuple((x+ox,y+oy,fixture.OWNER+i*16) for i,(x,y) in enumerate(((152,168),(357,136),(388,204))))
            cases=[]
            for name in ('single','list'):
                for flags in (0x202,0xED7):
                    for x,y,callback in records:
                        cases += [(name,x,y,callback,fixture.DATA+0x400,flags),
                                  (name,x,y,callback,fixture.DATA+0x404,flags),
                                  (name,x+1,y,callback,fixture.DATA+0x400,flags),
                                  (name,x,y+1,callback,fixture.DATA+0x400,flags),
                                  (name,x,y,callback+1,fixture.DATA+0x400,flags)]
                    for x in (-2147483648,-1,0,639,640,1000,width-1,width,2147483647):
                        cases.append((name,x,records[0][1],fixture.OWNER+100,fixture.DATA+0x400,flags))
            rows,seeds=self.execute(cases,width,height,records)
            for case,row,seed in zip(cases,rows,seeds):
                name,x,y,callback,holder,flags=case
                bound=width if (x,y,callback) in records and holder==fixture.DATA+0x400 else 640
                seed[4]=row[9]
                with self.subTest(width=width,case=case):
                    self.assertEqual(list(row[:8]),seed)
                    self.assertEqual(row[8]&fixture.MASK,fixture.comparison_flags(x,bound,flags&0x400))
                    self.assertEqual(row[10:14],(x&0xffffffff,y,holder,callback))

    def test_parked_x1000_remains_hidden_without_hiding_a_real_menu_at_that_coordinate(self):
        records=((1000,400,fixture.OWNER),)
        cases=[('single',1000,400,fixture.OWNER,fixture.DATA+0x400,0x202),
               ('single',1000,400,fixture.OWNER+16,fixture.DATA+0x400,0x202),
               ('list',1000,400,fixture.OWNER,fixture.DATA+0x404,0x202)]
        rows,_=self.execute(cases,1920,1080,records)
        self.assertEqual([((r[8]>>7)^(r[8]>>11))&1 for r in rows],[1,0,0])


@unittest.skipUnless(Path('C:/Clash/clash95.exe').is_file(),'exact original executable required')
class MenuOriginalTests(unittest.TestCase):
    def test_all_advertised_affected_profiles_replay_and_relocate_with_only_two_hooks(self):
        original=Path('C:/Clash/clash95.exe').read_bytes()
        original_hash=tool.sha(original)
        output=[]
        for resolution in ('1280x720','1280x960','1366x768','1920x1080','2560x1440','3440x1440','3840x2160'):
            with self.subTest(resolution=resolution):
                image,metadata,probe=tool.build_candidate(original,resolution)
                profile=tool.scalar.parse_resolution(resolution)
                base=tool.scalar.apply_patches(original,tool.scalar.select_patches_for(tool.scalar.DEFAULT_STAGE,profile))
                self.assertEqual(replay(base,metadata['edits']),image)
                old=pe.inspect_pe(base);new=pe.inspect_pe(image)
                self.assertEqual(new.sections[:7],old.sections)
                self.assertEqual(len(new.sections),8)
                self.assertEqual(tuple(row['va'] for row in metadata['hooks']),(0x419d63,0x419d8c))
                self.assertTrue(16 <= len(metadata['menu_records']) <= 20)
                self.assertEqual(metadata['new_highlow_count'],2*(1+len(metadata['menu_records'])))
                memory,_,fields,_=independent_image(image);oldmem,_,oldfields,_=independent_image(base)
                for delta in (-0x100000,0x2100000):
                    shifted=rebase(memory,fields,delta);oldshift=rebase(oldmem,oldfields,delta)
                    for rva in oldfields:self.assertEqual(shifted[rva:rva+4],oldshift[rva:rva+4])
                    for relocation in metadata['relocations']:
                        rva=metadata['code_rva']+relocation['offset']
                        self.assertEqual(struct.unpack_from('<I',shifted,rva)[0],relocation['target']+delta)
                checks=re.findall(r'\(by\(([0-9a-f]{8})\) != ([0-9a-f]+)\)',probe)
                self.assertTrue(checks)
                for address,value in checks:self.assertEqual(memory[int(address,16)-old.image_base],int(value,16))
                self.assertEqual(tool.sha(probe.encode()),metadata['probe_sha256'])
                self.assertEqual(metadata['source_hashes'],{name:tool.sha((tool.ROOT/name).read_bytes()) for name in metadata['source_hashes']})
                self.assertFalse(metadata['promotion_ready'])
                output.append({key:metadata[key] for key in ('resolution','candidate_sha256','base_candidate_sha256','code_bytes','new_highlow_count','source_hashes')})
        self.assertEqual(tool.sha(Path('C:/Clash/clash95.exe').read_bytes()),original_hash)
        report=os.environ.get('CLASSIC_MENU_RESULT')
        if report:Path(report).write_text(json.dumps(dict(schema=1,profiles=output,original_unchanged=True),indent=2))


if __name__=='__main__':unittest.main(verbosity=2)
