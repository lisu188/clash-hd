#!/usr/bin/env python3
"""Opt-in x86 debugger verifier checks on marked synthetic fixtures only.

No proprietary image is loaded and no fixture instruction is executed. The
shared restricted harness verifies the target stays paused and unchanged.
"""
import json
import os
from pathlib import Path
import re
import struct
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'tools')]
from src.patcher import ordinary_castle_entry_matrix as tool
import test_framed_loaded_probe_engine as engine


def fixture(aslr=False):
    image, _, _ = engine.executable_fixture(aslr=aslr)
    view=tool.pe.inspect_pe(image)
    # Exercise high-bit DWORD constants without touching the unreachable entry.
    changed=bytearray(image)
    offset=view.sections[0].raw_offset+0x180
    struct.pack_into('<I',changed,offset,0xF00DCAFE)
    image=bytes(changed)
    metadata=dict(schema=tool.SCHEMA,profile='completehd',resolution='1280x720',
                  stage=tool.stage('completehd'),candidate_sha256=tool.sha(image))
    script,facts=tool.render_probe(image,metadata)
    return image,script,facts,offset


@unittest.skipUnless(os.name=='nt' and os.environ.get('CLASH_DEBUGGER_INTEGRATION')=='1',
                     'opt-in isolated Windows debugger-engine lane required')
class MatrixEngineTests(unittest.TestCase):
    setUpClass=classmethod(engine.DebuggerEngineTests.setUpClass.__func__)
    execute=engine.DebuggerEngineTests.execute

    @classmethod
    def save_report(cls):
        destination=os.environ.get('CLASH_ORDINARY_ENTRY_ENGINE_REPORT')
        if not destination:
            return
        expected={'fixed-file':True, 'fixed-block':True, 'aslr':True,
                  'corrupt-rx':False, 'missing':False, 'reordered':False,
                  'unreadable':False}
        cases=[]
        for record in cls.records:
            item=dict(record)
            label,log=item['case'],item['log']
            should_accept=expected.get(label)
            pass_count=len(re.findall(r'^OCEM_CONTRACT_PASS ',log,re.M))
            accepted=(pass_count==1 and 'OCEM_MISMATCH' not in log
                      and 'OCEM_INCOMPLETE' not in log)
            rejected=('OCEM_CONTRACT_PASS' not in log and 'OCEM_INCOMPLETE' in log)
            receipt=('HARNESS_END hr=00000000 paused=1 same_ip=1 unchanged=1' in log
                     and 'HARNESS_CONTEXT before=014c after=014c' in log)
            relocated=True
            if label=='aslr':
                match=re.search(r'HARNESS_BEGIN base=([0-9a-f]+)',log)
                preferred=tool.pe.inspect_pe(fixture(aslr=True)[0]).image_base
                relocated=bool(match and int(match.group(1),16)!=preferred)
            item.update(expected_acceptance=should_accept,
                        observed_acceptance=accepted,
                        observed_rejection=rejected,
                        paused_unchanged_receipt=receipt,
                        actual_relocation_verified=relocated if label=='aslr' else None,
                        passed=(label in expected and item['returncode']==0 and receipt
                                and 'Syntax error' not in log and relocated
                                and (accepted if should_accept else rejected)))
            cases.append(item)
        complete=(len(cases)==len(expected)
                  and {item['case'] for item in cases}==set(expected))
        Path(destination).write_text(json.dumps(dict(
            schema='clash95_ordinary_entry_matrix_debugger_fixture_v1',
            generator_sha256=tool.sha(Path(tool.__file__).read_bytes()),
            fixture_source_sha256=tool.sha(Path(__file__).read_bytes()),
            harness_source_sha256=tool.sha(Path(engine.__file__).read_bytes()),
            engine='system x86 DbgEng',fixture_only=True,
            game_runtime_executed=False,manual_input_proof=False,
            expected_cases=len(expected),completed=complete,
            passed=complete and all(item['passed'] for item in cases),
            cases=cases),indent=2)+'\n',encoding='utf-8')

    def accepted(self,log):
        self.assertEqual(len(re.findall(r'^OCEM_CONTRACT_PASS ',log,re.M)),1,log)
        self.assertNotIn('OCEM_MISMATCH',log)
        self.assertNotIn('OCEM_INCOMPLETE',log)
        self.assertNotIn('Syntax error',log)
        self.assertIn('HARNESS_END hr=00000000 paused=1 same_ip=1 unchanged=1',log)
        self.assertIn('HARNESS_CONTEXT before=014c after=014c',log)

    def rejected(self,log):
        self.assertNotIn('OCEM_CONTRACT_PASS',log)
        self.assertIn('OCEM_INCOMPLETE',log)
        self.assertNotIn('Syntax error',log)

    def test_fixed_image_high_bit_words_and_block_file(self):
        data,script,_,_=fixture()
        for mode in ('file','block'):
            with self.subTest(mode=mode):
                self.accepted(self.execute(data,script,mode=mode,label='fixed-'+mode))

    def test_actual_loader_relocation_and_high_bit_words(self):
        data,script,_,_=fixture(aslr=True)
        log=self.execute(data,script,label='aslr')
        self.accepted(log)
        actual=int(re.search(r'HARNESS_BEGIN base=([0-9a-f]+)',log).group(1),16)
        self.assertNotEqual(actual,tool.pe.inspect_pe(data).image_base,'ASLR coverage missing')

    def test_corrupted_executable_bytes_cannot_pass(self):
        data,script,_,offset=fixture()
        changed=bytearray(data);changed[offset]^=1
        self.rejected(self.execute(bytes(changed),script,label='corrupt-rx'))

    def test_missing_or_reordered_chunks_cannot_pass(self):
        data,script,_,_=fixture()
        lines=script.splitlines()
        chunks=[i for i,line in enumerate(lines) if line.startswith('.if ((@$t19 != 0) & (@$t18 == 0n') and 'OCEM_MISMATCH' in line]
        self.assertGreater(len(chunks),2)
        missing=lines[:];missing.pop(chunks[0])
        reordered=lines[:]
        reordered[chunks[0]],reordered[chunks[1]]=reordered[chunks[1]],reordered[chunks[0]]
        for label,altered in [('missing',missing),('reordered',reordered)]:
            with self.subTest(label=label):
                self.rejected(self.execute(data,'\r\n'.join(altered)+'\r\n',label=label))

    def test_unreadable_memory_cannot_advance_completion(self):
        data,script,_,_=fixture()
        changed,count=re.subn(r'dwo\(@\$t19\+0x[0-9a-f]+\)', 'dwo(0)',script,count=1)
        self.assertEqual(count,1)
        self.rejected(self.execute(data,changed,label='unreadable'))


if __name__=='__main__':
    unittest.main()
