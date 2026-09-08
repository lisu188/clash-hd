"""Whole-image rebuild/replay, loaded-byte probe, rebase and SEC_IMAGE checks.

SEC_IMAGE only opens read-only image-section handles; it never maps or executes
an image, starts a process, game, debugger or wrapper. Raw fixtures stay external.
"""
from contextlib import redirect_stderr
from dataclasses import replace
import io
import json
import os
from pathlib import Path
import re
import struct
import tempfile
import unittest
from unittest.mock import patch

import build_framed_modal_slots_candidate as builder
from src.patcher import complete_hd_candidate as complete
from src.patcher import pe_extension as pe
from test_pe_extension import independent_image,rebase
from test_pe_modal_extension import native_image_section
from test_build_framed_modal_candidate import replay

ORIGINAL=Path('C:/Clash/clash95.exe')


def loaded_checks(probe):
    pattern=r'\((wo|by)\(([0-9a-f]{8})\) != ([0-9a-f]+)\)'
    rows=[]
    for line in probe.splitlines():
        if '_CONTRACT_FAIL' not in line:continue
        residual=re.sub(pattern,'READ',line)
        if not re.fullmatch(r'\.if \(READ(?: \| READ)*\) \{ \.echo (?:PTILE|ARMY|SLOTS)_CONTRACT_FAIL; q \}',residual):
            raise AssertionError('unexpected loaded-byte check grammar')
        rows.extend((int(va,16),2 if kind=='wo' else 1,int(value,16)) for kind,va,value in re.findall(pattern,line))
    return rows


@unittest.skipUnless(ORIGINAL.is_file(),'user-owned original required')
class SlotsBuildTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original=ORIGINAL.read_bytes();cls.results={}
        cls.folder=Path(tempfile.mkdtemp(prefix='clash-modal-slots-loader-',dir='C:/ClashTests')) if os.name=='nt' else None
        print('Retained slots SEC_IMAGE fixture directory:',cls.folder,flush=True)
        for resolution in complete.RESOLUTIONS:
            cls.results[resolution]=builder.build_candidate(cls.original,resolution)
            print('Built slots fixture:',resolution,cls.results[resolution][1]['candidate_sha256'],flush=True)

    def base(self,metadata):
        return complete.apply_records(self.original,metadata['base_candidate']['patch_records'],expected_base_sha256=complete.BASE_SHA256)

    def test_exact_replay_preserves_v1_and_original(self):
        for resolution,(image,metadata,probe) in self.results.items():
            base=self.base(metadata)
            self.assertEqual(builder.sha(base),metadata['base_candidate_sha256'])
            self.assertEqual(replay(base,metadata['edits']),image)
            self.assertEqual(builder.sha(image),metadata['candidate_sha256'])
            self.assertEqual(builder.sha(probe.encode()),metadata['probe_sha256'])
            self.assertEqual(metadata['base_candidate']['stage'],complete.STAGE)
            self.assertEqual(metadata['stage'],builder.STAGE)
            self.assertNotEqual(metadata['base_candidate']['candidate_sha256'],metadata['candidate_sha256'])
            self.assertEqual(metadata['source_hashes'],{name:builder.sha((builder.ROOT/name).read_bytes()) for name in metadata['source_hashes']})
            for key in ('runtime_executed','installation_ready','manual_input_proof','promotion_ready','primary_composition_proven'):
                self.assertFalse(metadata[key])
        self.assertEqual(ORIGINAL.read_bytes(),self.original)

    def test_independent_loader_rebase_and_windows_section_admission(self):
        for resolution,(image,metadata,probe) in self.results.items():
            base=self.base(metadata);old_memory,old_sections,old_fields,_=independent_image(base)
            memory,sections,fields,_=independent_image(image)
            self.assertEqual(sections[:11],old_sections)
            self.assertEqual((sections[-1][0],sections[-1][-1]),(b'.hdslots',pe.RX_CODE))
            new={metadata['code_rva']+row['offset'] for row in metadata['relocations'] if row['kind']=='abs32'}
            self.assertEqual(set(fields),set(old_fields)|new)
            self.assertEqual(len(fields),len(set(fields)))
            for delta in (-0x100000,0x2100000):
                moved=rebase(memory,fields,delta);old_moved=rebase(old_memory,old_fields,delta)
                for rva in old_fields:self.assertEqual(moved[rva:rva+4],old_moved[rva:rva+4])
                for row in metadata['relocations']:
                    rva=metadata['code_rva']+row['offset']
                    if row['kind']=='abs32':self.assertEqual(struct.unpack_from('<I',moved,rva)[0],row['target']+delta)
                    else:self.assertEqual(moved[rva:rva+4],memory[rva:rva+4])
            if self.folder:
                path=self.folder/(resolution+'.bin')
                with path.open('xb') as stream:stream.write(image)
                self.assertEqual(native_image_section(path),dict(accepted=True,error=0,view_mapped=False,process_started=False))

    def test_probe_authenticates_new_code_headers_hook_and_owned_canvas(self):
        for resolution,(image,metadata,probe) in self.results.items():
            memory,sections,_,_=independent_image(image);covered=set()
            for va,size,value in loaded_checks(probe):
                actual=memory[va-0x400000:va-0x400000+size]
                self.assertEqual(int.from_bytes(actual,'little'),value)
                covered.update(range(va,va+size))
            ranges=[(metadata['code_va'],metadata['code_raw_bytes']),
                    (0x432940,1006),(0x4024E0,867),(metadata['modal_state_va'],128),(0x400320,40)]
            for start,size in ranges:self.assertTrue(set(range(start,start+size))<=covered)
            self.assertEqual(probe.splitlines().count('.echo '+metadata['probe_contract']['slot_marker']),1)
            self.assertNotIn('.echo COMPLETEHD_CONTRACT_PASS',probe)
            self.assertNotIn('.echo ARMY_CONTRACT_PASS',probe)
            self.assertIn(f'PTILE_CONTRACT_PASS stage={builder.STAGE} ',probe)
            self.assertNotIn('ed 00400300',probe.lower())

    def test_unknown_original_and_source_changes_fail_closed(self):
        with self.assertRaises(ValueError):builder.build_candidate(self.original[:-1],'1024x768')
        result=self.results['1024x768'];base=self.base(result[1]);context=result[1]['base_candidate']
        with patch.object(complete,'build_candidate',return_value=(base,dict(context,recipe_revision='unknown'),'')):
            with self.assertRaisesRegex(ValueError,'v1'):builder.build_candidate(self.original,'1024x768')


class SlotsBuilderBoundaryTests(unittest.TestCase):
    def test_cli_rejects_unsafe_paths_before_build(self):
        common=['--original',str(ORIGINAL),'--resolution','1024x768']
        for extra in (['--output',str(ORIGINAL)],['--output',str(builder.ROOT/'a.exe')],
                      ['--output','C:/ClashTests/a.bin'],['--preflight','--output','C:/ClashTests/a.exe']):
            with patch.object(builder,'build_candidate') as build,redirect_stderr(io.StringIO()),self.assertRaises(SystemExit):
                builder.main(common+extra)
            build.assert_not_called()

    def test_existing_bundle_never_overwrites(self):
        with tempfile.TemporaryDirectory(prefix='clash-slots-output-') as folder:
            output=Path(folder)/'candidate.exe';output.write_bytes(b'keep')
            with patch.object(builder,'build_candidate') as build,self.assertRaises((ValueError,FileExistsError)):
                builder.write_candidate(ORIGINAL,output,'1024x768')
            self.assertEqual(output.read_bytes(),b'keep');build.assert_not_called()


if __name__=='__main__':unittest.main(verbosity=2)
