"""Independent in-memory loader, rebase, edit-replay and probe checks."""
from pathlib import Path
from contextlib import redirect_stderr
import io
import re
import struct
import sys
import unittest
from unittest.mock import patch

import build_framed_army_candidate as builder
from test_pe_extension import independent_image, rebase
from test_build_framed_modal_candidate import replay

ORIGINAL = Path('C:/Clash/clash95.exe')
RESOLUTIONS = ('800x600','1024x768','1280x720','1280x960','1920x1080','802x602')


def loaded_checks(probe):
    pattern = r'\((wo|by)\(([0-9a-f]{8})\) != ([0-9a-f]+)\)'
    result = []
    for line in probe.splitlines():
        if not any(word in line for word in ('PTILE_CONTRACT_FAIL','ARMY_CONTRACT_FAIL')):
            continue
        residual = re.sub(pattern,'READ',line)
        if not re.fullmatch(r'\.if \(READ(?: \| READ)*\) \{ \.echo (?:PTILE|ARMY)_CONTRACT_FAIL; q \}',residual):
            raise AssertionError('unexpected load-check grammar')
        result.extend((int(va,16),2 if kind=='wo' else 1,int(value,16))
                      for kind,va,value in re.findall(pattern,line))
    if not result:
        raise AssertionError('missing load checks')
    return result


@unittest.skipUnless(ORIGINAL.is_file(),'user-owned original required; all candidates remain in memory')
class ArmyBuildTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = ORIGINAL.read_bytes()
        cls.results = {r:builder.build_candidate(cls.original,r,minimap_viewport=True) for r in RESOLUTIONS}

    def base(self,metadata):
        modal = metadata['base_candidate']
        framed = modal['base_candidate']
        previous = replay(self.original,[*framed['selected_patches'],*framed['edits']])
        return replay(previous,modal['edits'])

    def test_replay_stage_and_original_preservation(self):
        for resolution,(image,metadata,probe) in self.results.items():
            with self.subTest(resolution=resolution):
                base = self.base(metadata)
                self.assertEqual(builder.sha(base),metadata['base_candidate_sha256'])
                self.assertEqual(replay(base,metadata['edits']),image)
                self.assertEqual(metadata['output_sha256'],builder.sha(image))
                self.assertEqual(metadata['stage'],builder.STAGE)
                self.assertTrue(metadata['stage'].endswith('-modalcanvas-army-validation'))
                self.assertNotEqual(metadata['stage'],metadata['base_candidate']['stage'])
                self.assertEqual(metadata['initial_probe_sha256'],builder.sha(probe.encode()))
                self.assertEqual(len(metadata['hooks']),10)
                for key in ('runtime_executed','installation_ready','manual_input_proof','promotion_ready'):
                    self.assertFalse(metadata[key],key)
        self.assertEqual(ORIGINAL.read_bytes(),self.original)

    def test_independent_loader_relocations_and_native_hook_targets(self):
        for resolution,(image,metadata,_) in self.results.items():
            with self.subTest(resolution=resolution):
                base = self.base(metadata)
                _,old_sections,old_fixups,_ = independent_image(base)
                memory,sections,fixups,_ = independent_image(image)
                self.assertEqual(sections[:-1],old_sections)
                self.assertEqual((sections[-1][0],sections[-1][-1]),(b'.hdarmy',0x60000020))
                self.assertEqual(len(fixups),len(set(fixups)))
                removed = {row['rva'] for row in metadata['removed_highlow']}
                added = {metadata['code_rva']+r['offset'] for r in metadata['relocations'] if r['kind']=='abs32'}
                self.assertEqual(set(fixups),(set(old_fixups)-removed)|added)
                self.assertEqual(len(removed),7)
                self.assertIn(0x418786-0x400000,removed)
                self.assertIn(0x423877-0x400000,removed)
                for delta in (-0x100000,0x02000000):
                    moved = rebase(memory,fixups,delta)
                    for row in metadata['relocations']:
                        rva = metadata['code_rva']+row['offset']
                        if row['kind']=='abs32':
                            self.assertEqual(struct.unpack_from('<I',moved,rva)[0],(row['target']+delta)&0xffffffff)
                        else:
                            self.assertEqual(moved[rva:rva+4],memory[rva:rva+4])
                    for row in metadata['hooks']:
                        raw = bytes.fromhex(row['new_hex']);rva=row['rva']
                        self.assertEqual(moved[rva:rva+len(raw)],raw)
                        self.assertIn(raw[0],(0xe8,0xe9))
                        target = row['va']+5+struct.unpack_from('<i',raw,1)[0]
                        self.assertTrue(metadata['code_va']<=target<metadata['code_va']+metadata['code_bytes'])

    def test_load_probe_binds_actual_code_hooks_modal_state_and_headers(self):
        for resolution,(image,metadata,probe) in self.results.items():
            with self.subTest(resolution=resolution):
                memory,sections,_,_ = independent_image(image)
                covered = set()
                for va,size,value in loaded_checks(probe):
                    actual=memory[va-0x400000:va-0x400000+size]
                    self.assertEqual(int.from_bytes(actual,'little'),value)
                    covered.update(range(va,va+size))
                    for i in range(size):
                        changed=bytearray(actual);changed[i]^=1
                        self.assertNotEqual(int.from_bytes(changed,'little'),value)
                for row in metadata['hooks']:
                    self.assertTrue(set(range(row['va'],row['va']+len(bytes.fromhex(row['new_hex']))))<=covered)
                for row in metadata['base_candidate']['authenticated_legacy_continuations']:
                    self.assertTrue(set(range(row['entry_va'],row['entry_va']+row['span_bytes']))<=covered)
                for section in sections:
                    if section[0] in (b'.hdcode',b'.hdmodal',b'.hdarmy'):
                        # Declared code bytes, including the modified old payload,
                        # must be checked. Loader padding need not be executable.
                        count = metadata['code_bytes'] if section[0]==b'.hdarmy' else (
                            metadata['base_candidate']['base_candidate']['extension_payload_size']
                            if section[0]==b'.hdcode' else metadata['base_candidate']['code_bytes'])
                        start=0x400000+section[1]
                        self.assertTrue(set(range(start,start+count))<=covered)
                self.assertEqual(sum(line.startswith('.echo ARMY_CONTRACT_PASS ') for line in probe.splitlines()),1)
                self.assertEqual(sum(line.startswith('.echo PTILE_CONTRACT_PASS ') for line in probe.splitlines()),1)
                self.assertNotIn('MCANVAS_CONTRACT_PASS',probe)
                self.assertNotIn('ed 00400300',probe.lower())

    def test_original_and_variant_changes_fail_closed(self):
        with self.assertRaises(ValueError):
            builder.build_candidate(self.original[:-1]+bytes([self.original[-1]^1]),'1024x768',minimap_viewport=True)
        for flag in (None,1,'true'):
            with self.assertRaises(ValueError):
                builder.build_candidate(self.original,'1024x768',minimap_viewport=flag)


class ArmyBuilderBoundaryTests(unittest.TestCase):
    def test_pinned_source_mismatch_fails_without_editing_files(self):
        with patch.dict(builder.PINNED_SOURCES,{'src/patcher/framed_army_input.py':'0'*64}):
            with self.assertRaisesRegex(ValueError,'SHA-256 mismatch'):
                builder.verify_sources()

    def test_cli_rejects_protected_repo_and_invalid_outputs_before_build(self):
        common=['build_framed_army_candidate.py','--original',str(ORIGINAL),'--resolution','1024x768']
        cases=[
            ['--output',str(ORIGINAL),'--report-json','C:/ClashTests/a.json','--probe-out','C:/ClashTests/a.cdb'],
            ['--output',str(builder.ROOT/'candidate.exe'),'--report-json','C:/ClashTests/a.json','--probe-out','C:/ClashTests/a.cdb'],
            ['--output','C:/ClashTests/a.exe','--report-json','C:/ClashTests/a.exe','--probe-out','C:/ClashTests/a.cdb'],
            ['--output','C:/ClashTests/a.bin','--report-json','C:/ClashTests/a.json','--probe-out','C:/ClashTests/a.cdb'],
            ['--preflight','--output','C:/ClashTests/a.exe'],
        ]
        for args in cases:
            with self.subTest(args=args),patch.object(sys,'argv',common+args),redirect_stderr(io.StringIO()),\
                    patch.object(builder,'build_candidate') as build:
                with self.assertRaises(SystemExit) as caught:
                    builder.main()
                self.assertEqual(caught.exception.code,2)
                build.assert_not_called()


if __name__=='__main__':
    unittest.main()
