#!/usr/bin/env python3
"""Opt-in final small-world verifier on marked synthetic Windows fixtures.

The original game is never read or loaded. The frozen restricted x86 harness
stops at the loader breakpoint, runs only verifier expressions, and checks
unchanged image bytes, processor context and EIP. No fixture entry is executed.
"""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'tools')]
from src.patcher import complete_small_world_candidate as tool
import test_complete_small_world_candidate as fixtures
import test_framed_loaded_probe_engine as engine

EXPECTED = {'fixed-file': True, 'fixed-block': True, 'aslr': True,
            'corrupt-absolute': False, 'corrupt-highbit': False,
            'missing': False, 'reordered': False, 'unreadable': False}
DWORD_MASK = '0x00000000`ffffffff'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def fixture(*, aslr=False):
    """Actual successor allocator/probe over the explicitly artificial parent."""
    _, image, metadata, _ = fixtures.synthetic_successor(probe=False)
    view = tool.pe.inspect_pe(image)
    changed = bytearray(image)
    # The artificial builder reserves NT headers at 0x40. The frozen engine
    # requires DOS magic there instead. Move only the synthetic header block
    # to 0x80; all 16 section headers still fit in the same 1024-byte header.
    if view.pe_offset < 64 + len(engine.MAGIC):
        header_bytes = 24 + 224 + 40 * len(view.sections)
        new_nt = 0x80
        if new_nt + header_bytes > view.headers_size:
            raise AssertionError('marked fixture NT/section headers exceed existing header')
        block = image[view.pe_offset:view.pe_offset + header_bytes]
        changed[view.pe_offset:new_nt] = bytes(new_nt - view.pe_offset)
        changed[new_nt:new_nt + header_bytes] = block
        struct.pack_into('<I', changed, 0x3C, new_nt)
        view = tool.pe.inspect_pe(bytes(changed))
    changed[64:64 + len(engine.MAGIC)] = engine.MAGIC
    opt = view.optional_offset
    struct.pack_into('<I', changed, opt + 16, 0x10E0)
    struct.pack_into('<HH', changed, opt + 40, 6, 0)
    struct.pack_into('<HH', changed, opt + 48, 6, 0)
    struct.pack_into('<HH', changed, opt + 68, 3, 0x40 if aslr else 0)
    struct.pack_into('<IIII', changed, opt + 72, 0x100000, 0x1000, 0x100000, 0x1000)
    entry_offset = view.file_offset(0x10E0, 2)
    changed[entry_offset:entry_offset + 2] = b'\xeb\xfe'
    highbit_offset = view.sections[0].raw_offset + 0x180
    highbit_rva = view.sections[0].rva + 0x180
    _, fields = tool.pe._old_relocations(image, view)
    if any(highbit_rva < field + 4 and field < highbit_rva + 4 for field in fields):
        raise AssertionError('high-bit fixture literal intersects a relocated field')
    struct.pack_into('<I', changed, highbit_offset, 0xF00DCAFE)
    image = bytes(changed)
    metadata = deepcopy(metadata)
    metadata['candidate_sha256'] = sha(image)
    added = metadata['relocation_contract']['added_rvas']
    helper_start = metadata['helpers']['base_va'] - view.image_base
    helper_end = helper_start + metadata['helpers']['byte_count']
    if (len(added) != 5 or len(set(added)) != 5
            or any(type(rva) is not int or not helper_start <= rva <= helper_end - 4
                   or rva not in fields for rva in added)):
        raise AssertionError('five added absolute fields must belong to actual appended helper')
    script, facts = tool.render_probe(image, metadata)
    # Adjacent RX sections must remain separate mappings after an unaligned
    # HIGHLOW field. Every emitted memory read must fit one actual mapping.
    rx = [section for section in view.sections
          if section.characteristics & 0x20000000 and section.raw_offset]
    boundaries = [section.rva + section.raw_size for section in rx
                  if any(other.rva == section.rva + section.raw_size for other in rx)]
    ranges = facts['checked_ranges']
    if (not boundaries or any(not any(row['rva'] + row['bytes'] == edge for row in ranges)
                              or not any(row['rva'] == edge for row in ranges) for edge in boundaries)):
        raise AssertionError('adjacent executable mappings must retain verifier read boundaries')
    for match in re.finditer(r'\b(by|wo|dwo)\(@\$t19\s*\+\s*0x([0-9a-f]+)\)', script):
        size = {'by': 1, 'wo': 2, 'dwo': 4}[match.group(1)]
        rva = int(match.group(2), 16)
        if rva + size > view.headers_size:
            view.file_offset(rva, size)
    highbit_check = f'((dwo(@$t19+0x{highbit_rva:x}) & {DWORD_MASK}) == 0x00000000`f00dcafe)'
    if highbit_check not in script:
        raise AssertionError('ordinary high-bit DWORD requires explicit unsigned comparison')
    relocated_highbit = struct.unpack_from('<I', image, view.file_offset(0x1020, 4))[0]
    if (0x1020 not in fields or relocated_highbit != 0xF1234567
            or f'((dwo(@$t19+0x1020) & {DWORD_MASK}) == '
               f'((0x00000000`f1234567+@$t19-0x{view.image_base:x}) & {DWORD_MASK}))' not in script):
        raise AssertionError('relocated high-bit DWORD fixture and unsigned verifier required')
    marker = ('CSW_FINAL_OK stage=' + metadata['stage'] + ' resolution=' + metadata['resolution']
              + ' candidate_sha256=' + metadata['candidate_sha256'])
    if facts['acceptance_marker'] != marker:
        raise AssertionError('final verifier facts identity differs')
    if '.echo ' + marker not in script:
        raise AssertionError('final verifier identity marker differs')
    if '\n' in script.replace('\r\n', '') or not script.endswith('\r\n'):
        raise AssertionError('final file-mode verifier requires CRLF')
    if 'OCEM_CONTRACT_PASS' in script:
        raise AssertionError('predecessor marker cannot qualify final successor')
    return image, script, facts, metadata, highbit_offset, marker


@unittest.skipUnless(os.name == 'nt' and os.environ.get('CLASH_DEBUGGER_INTEGRATION') == '1',
                     'opt-in isolated Windows debugger-engine lane required')
class SmallWorldEngineTests(unittest.TestCase):
    setUpClass = classmethod(engine.DebuggerEngineTests.setUpClass.__func__)
    execute = engine.DebuggerEngineTests.execute

    @classmethod
    def save_report(cls):
        destination = os.environ.get('CLASH_COMPLETE_SMALL_WORLD_ENGINE_REPORT')
        if not destination:
            return
        cases = []
        for record in cls.records:
            item = dict(record)
            label, log = item['case'], item['log']
            image, _, facts, metadata, _, marker = fixture(aslr=label == 'aslr')
            final_lines = re.findall(r'^CSW_FINAL_OK[^\r\n]*', log, re.M)
            accepted = (final_lines == [marker] and 'CSW_BASE_INVALID' not in log
                        and not re.search(r'^CSW_CHUNK_\d+_BAD', log, re.M))
            rejected = not final_lines and 'CSW_INCOMPLETE' in log
            receipt = ('HARNESS_END hr=00000000 paused=1 same_ip=1 unchanged=1' in log
                       and 'HARNESS_CONTEXT before=014c after=014c' in log)
            actual = re.search(r'^HARNESS_BEGIN base=([0-9a-f]+)', log, re.M)
            relocated = bool(actual and int(actual.group(1), 16) != tool.pe.inspect_pe(image).image_base)
            item.update(expected_acceptance=EXPECTED.get(label), observed_acceptance=accepted,
                        observed_rejection=rejected, expected_final_marker=marker,
                        paused_unchanged_receipt=receipt,
                        actual_relocation_verified=relocated if label == 'aslr' else None,
                        added_helper_highlow_rvas=metadata['relocation_contract']['added_rvas'],
                        probe_required_chunks=facts['required_chunks'],
                        passed=(label in EXPECTED and item.get('status') == 'completed'
                                and item.get('raw_retention_complete') is True
                                and engine.phase_receipt(log) and item['returncode'] == 0 and receipt
                                and 'Syntax error' not in log and (label != 'aslr' or relocated)
                                and (accepted if EXPECTED.get(label) else rejected)))
            cases.append(item)
        completed = (engine.terminal_cases(cases, EXPECTED)
                     and cls.ledger.failure is None and not cls.store.failed)
        report = dict(schema='clash95_complete_small_world_debugger_fixture_v1',
                      generator_sha256=sha(Path(tool.__file__).read_bytes()),
                      fixture_source_sha256=sha(Path(__file__).read_bytes()),
                      synthetic_builder_source_sha256=sha(Path(fixtures.__file__).read_bytes()),
                      harness_source_sha256=sha(Path(engine.__file__).read_bytes()),
                      engine='system x86 DbgEng', fixture_only=True,
                      original_game_read=False, game_runtime_executed=False,
                      fixture_entry_executed=False, manual_input_proof=False, promotion_ready=False,
                      expected_cases=len(EXPECTED), completed=completed,
                      first_failure=cls.ledger.failure, retention_debt=cls.store.failed,
                      artifact_directory=str(cls.root), compiler=cls.compiler_receipt,
                      passed=completed and all(item['passed'] for item in cases), cases=cases)
        engine.publish_report(cls, destination, report)

    def accepted(self, log, marker):
        self.assertEqual(re.findall(r'^CSW_FINAL_OK[^\r\n]*', log, re.M), [marker], log)
        self.assertNotIn('CSW_BASE_INVALID', log)
        self.assertNotRegex(log, re.compile(r'^CSW_CHUNK_\d+_BAD', re.M), log)
        self.assertNotIn('OCEM_CONTRACT_PASS', log)
        self.assertNotIn('Syntax error', log)
        self.assertIn('HARNESS_END hr=00000000 paused=1 same_ip=1 unchanged=1', log)
        self.assertIn('HARNESS_CONTEXT before=014c after=014c', log)

    def rejected(self, log):
        self.assertNotRegex(log, re.compile(r'^CSW_FINAL_OK', re.M), log)
        self.assertIn('CSW_INCOMPLETE', log)
        self.assertNotIn('OCEM_CONTRACT_PASS', log)
        self.assertNotIn('Syntax error', log)
        self.assertIn('HARNESS_END hr=00000000 paused=1 same_ip=1 unchanged=1', log)
        self.assertIn('HARNESS_CONTEXT before=014c after=014c', log)

    def test_fixed_image_high_bit_word_and_real_crlf_file(self):
        image, script, _, _, _, marker = fixture()
        for mode in ('file', 'block'):
            with self.subTest(mode=mode):
                self.accepted(self.execute(image, script, mode=mode, label='fixed-' + mode), marker)

    def test_actual_loader_relocation_of_all_five_added_helper_fields(self):
        image, script, _, metadata, _, marker = fixture(aslr=True)
        fields = metadata['relocation_contract']['added_rvas']
        self.assertEqual(len(fields), 5)
        view = tool.pe.inspect_pe(image)
        for rva in fields:
            value = struct.unpack_from('<I', image, view.file_offset(rva, 4))[0]
            self.assertIn(f'((dwo(@$t19+0x{rva:x}) & {DWORD_MASK}) == '
                          f'((0x00000000`{value:08x}+@$t19-0x{view.image_base:x}) & {DWORD_MASK}))', script)
        log = self.execute(image, script, label='aslr')
        self.accepted(log, marker)
        actual = re.search(r'^HARNESS_BEGIN base=([0-9a-f]+)', log, re.M)
        self.assertIsNotNone(actual, log)
        self.assertNotEqual(int(actual.group(1), 16), view.image_base, 'ASLR coverage missing')

    def test_corrupted_new_absolute_helper_field_cannot_pass(self):
        image, script, _, metadata, _, _ = fixture()
        changed = bytearray(image)
        offset = tool.pe.inspect_pe(image).file_offset(metadata['relocation_contract']['added_rvas'][0], 4)
        changed[offset] ^= 1
        self.rejected(self.execute(bytes(changed), script, label='corrupt-absolute'))

    def test_corrupted_high_bit_nonrelocated_word_cannot_pass(self):
        image, script, _, _, offset, _ = fixture()
        changed = bytearray(image)
        changed[offset] ^= 1
        self.rejected(self.execute(bytes(changed), script, label='corrupt-highbit'))

    def test_missing_and_reordered_chunks_cannot_advance_completion(self):
        image, script, _, _, _, _ = fixture()
        lines = script.splitlines()
        chunks = [i for i, line in enumerate(lines) if re.search(r'CSW_CHUNK_\d+_BAD', line)]
        self.assertGreater(len(chunks), 2)
        missing = lines[:]
        missing.pop(chunks[0])
        reordered = lines[:]
        reordered[chunks[0]], reordered[chunks[1]] = reordered[chunks[1]], reordered[chunks[0]]
        for label, altered in (('missing', missing), ('reordered', reordered)):
            with self.subTest(label=label):
                self.rejected(self.execute(image, '\r\n'.join(altered) + '\r\n', label=label))

    def test_unreadable_memory_cannot_advance_completion(self):
        image, script, _, _, _, _ = fixture()
        changed, count = re.subn(r'dwo\(@\$t19\+0x[0-9a-f]+\)', 'dwo(0)', script, count=1)
        self.assertEqual(count, 1)
        self.rejected(self.execute(image, changed, label='unreadable'))


if __name__ == '__main__':
    unittest.main()
