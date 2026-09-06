#!/usr/bin/env python3
"""Repo-only event protocol fixtures; never execute a debugger or candidate."""
from __future__ import annotations

import hashlib
from pathlib import Path
import re
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import partial_tile_trace_probe as trace

ROOT = Path(__file__).resolve().parents[1]
SITES = {70: 0x56326E, 71: 0x5632A6, 72: 0x5632C9, 73: 0x563500,
         74: 0x418AFA, 75: 0x56310C, 76: 0x563480, 77: 0x563530}
MEMBERS = {70: 'PTILE_STATUS hook=full_converge', 71: 'PTILE_STATUS hook=full_present',
           72: 'PTILE_INCREMENTAL_INPUT', 73: 'PTILE_MAP_READY',
           74: 'PTILE_NATIVE_NOOP_EXIT', 75: 'PTILE_COMPOSITION_GUARD',
           76: 'PTILE_INITIAL_ADMISSION', 77: 'PTILE_INITIAL_RETURN'}


def source_probe(*, initial=True, newline='\n'):
    lines = ['.echo PTILE_CONTRACT_PASS stage=synthetic resolution=800x600 candidate_sha256=' + 'a'*64,
             '.echo PTILE_SCOPE guarded_map_only manual_input_proof=false promotion_ready=false']
    for bp in range(70, 78 if initial else 76):
        body = f'.printf \\"{MEMBERS[bp]} tid=%x esp=%p\\\\n\\", @$tid, @esp; '
        if bp == 72:
            body += '.printf \\"PTILE_STATUS hook=incremental tid=%x esp=%p\\\\n\\", @$tid, @esp; '
        lines.append(f'bp{bp} {SITES[bp]:08x} "{body}gc"')
    lines.append('bd 70; bd 71; bd 72; bd 74; bd 75')
    return newline.join(lines) + newline


def record(bp, *, tid=0x1234, esp=0xEDC74):
    identity = f'tid={tid:x} esp={esp:08x}'
    return {
        76: [f'PTILE_INITIAL_ADMISSION status=1 {identity}'],
        73: ['PTILE_MAP_READY owner=0040ad40 size=(800,600)'],
        70: [f'PTILE_STATUS hook=full_converge status=1 {identity} owner=0040ad40 tile=00000000 post=00000000 lower=00000000 player=0'],
        71: [f'PTILE_STATUS hook=full_present status=1 {identity} owner=0040ad40 tile=00000000 post=00000000 lower=00000000 player=0'],
        77: [f'PTILE_INITIAL_RETURN {identity} result=0'],
        75: [f'PTILE_COMPOSITION_GUARD {identity} status=1 world=(90,8) cell=(80,-9) present=1 caller=004166fa'],
        72: [f'PTILE_INCREMENTAL_INPUT {identity} world=(90,8) caller=004166fa gd=038e0030 map=(100,100) scroll=(10,17) vtable=0050ee24',
             f'PTILE_STATUS hook=incremental status=0 {identity} owner=0040ad40 tile=00000000 post=00000000 lower=00000000 player=0'],
        74: [f'PTILE_NATIVE_NOOP_EXIT {identity} world=(90,8) caller=004166fa gd=038e0030 map=(100,100) scroll=(10,17) vtable=0050ee24'],
    }[bp]


def event(seq, bp, *, tid=0x1234, esp=0xEDC74):
    return [f'PTILE_EVENT seq={seq} bp={bp} tid={tid:x} eip={SITES[bp]:08x} esp={esp:08x}',
            *record(bp, tid=tid, esp=esp)]


def valid_lines():
    lines = ['PTILE_CONTRACT_PASS stage=synthetic', 'PTILE_SCOPE guarded_map_only']
    for seq, bp in enumerate((76, 73, 70, 71, 77, 75, 72, 74), 1):
        lines.extend(event(seq, bp))
    return lines + ['PTILE_TRACE_CLOSED tid=1234 eip=00406fa0 esp=000edc98', 'SURFDUMP_HOST_READY']


class InstrumentationTests(unittest.TestCase):
    def test_only_prefix_is_added_and_original_bytes_survive(self):
        for newline in ('\n', '\r\n'):
            original = source_probe(newline=newline)
            transformed = trace.instrument_probe(original, reset_bp=76)
            recovered = []
            for line in transformed.splitlines(keepends=True):
                match = trace._BP.fullmatch(line.rstrip('\r\n'))
                if match:
                    prefix = trace._prefix(int(match['bp']), 76)
                    self.assertTrue(match['body'].startswith(prefix))
                    start = match.start('body')
                    line = line[:start] + line[start + len(prefix):]
                    # The added prefix has only debugger-counter writes and output.
                    self.assertRegex(prefix, r'^(?:r @\$t9 = 0; )?r @\$t9 = @\$t9 \+ 1; \.printf ')
                    self.assertNotRegex(prefix, r'\b(?:ed|eb|ew|eq|eza|r (?:eax|esp|eip))\b')
                recovered.append(line)
            self.assertEqual(''.join(recovered), original)
            self.assertEqual(transformed.count('PTILE_EVENT'), 8)
            self.assertEqual(transformed.count('r @$t9 = 0;'), 1)

    def test_declared_breakpoint_case_and_address_case_are_preserved(self):
        original = source_probe().replace('bp70', 'BP 70').replace('0056326e', '0056326E')
        output = trace.instrument_probe(original, reset_bp=76)
        self.assertIn('BP 70 0056326E "', output)
        self.assertTrue(trace.validate_event_integrity('\n'.join(valid_lines()), output, reset_bp=76)['passed'])

    def test_legacy_reset_is_explicit_and_initial_breakpoints_are_required(self):
        old = trace.instrument_probe(source_probe(initial=False), reset_bp=73)
        self.assertIn('bp73 00563500 "r @$t9 = 0;', old)
        with self.assertRaises(ValueError): trace.instrument_probe(source_probe(initial=False), reset_bp=76)
        with self.assertRaises(ValueError): trace.instrument_probe(source_probe(), reset_bp=73)
        with self.assertRaises(ValueError): trace.instrument_probe(source_probe(), reset_bp=72)

    def test_fail_closed_on_unknown_duplicate_or_reinstrumented_grammar(self):
        original = source_probe()
        cases = [original.replace('bp70 ', 'bu70 '), original.replace('bp70 ', 'bp80 '),
                 original.replace('bp70 ', ' bp70 '), original.replace('bp71 ', 'bp70 '),
                 original.replace('005632a6', '0056326e'), original.replace('bp70 0056326e', 'bp70 module!entry'),
                 original.replace('bp70 0056326e', 'bp70 00000000'),
                 original.replace('PTILE_COMPOSITION_GUARD', 'UNKNOWN_GUARD'),
                 original + 'r @$t9 = 77\n', original + '\x00',
                 original.replace('gc"', 'gc"; g', 1),
                 original.replace('gc"', 'a'*4096+'gc"', 1),
                 trace.instrument_probe(original, reset_bp=76)]
        for value in cases:
            with self.subTest(value=value[:80]), self.assertRaises(ValueError):
                trace.instrument_probe(value, reset_bp=76)

    def test_base_counter_is_gated_to_pregame(self):
        base = (ROOT/'probes/cdb/render/clash95_surface_dump_probe.cdb').read_text()
        uses = [line for line in base.splitlines() if re.search(r'\$t9\b', line)]
        self.assertEqual(len(uses), 2)
        self.assertEqual(uses[0], 'r @$t9 = 0')
        self.assertTrue(uses[1].startswith('bp 00448A45 ".if (@$t14 == 0) {'))
        self.assertIn('bp 0040B660 ".if (poi(005202e4) != 0) { r @$t14 = 1;', base)

    def test_saved_actual_probe_grammar_when_artifacts_are_available(self):
        runs = (
            (Path(r'C:\ClashCaptures\hd-completion\partialtiles-noop-v4-800x600-20260905\cdb-surface-dump-20260905-201619\partial-tile-installed.extra.cdb'),
             'f966ef9b99a3c0cd9f441807ff0d74aa3a8ae9dc8f2b3bbb5525dda7f90d0acb'),
            (Path(r'C:\ClashCaptures\hd-completion\partialtiles-noop-v4-1024x768-20260905\cdb-surface-dump-20260905-202225\partial-tile-installed.extra.cdb'),
             '621a62501583bc118972616df8bb70a48cd5bf5a660977eec1dc93eb9331c54a'))
        available = [item for item in runs if item[0].exists()]
        if not available:
            self.skipTest('optional frozen probe text artifacts are unavailable')
        for path, digest in available:
            raw=path.read_bytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(),digest)
            original=raw.decode('ascii')
            instrumented=trace.instrument_probe(original,reset_bp=73)
            rows,sites=trace._probe_rows(instrumented,73,instrumented=True)
            recovered=''.join(line.replace(trace._prefix(bp,73),'',1) if match else line
                              for line,match,bp in rows)
            self.assertEqual(recovered,original)
            self.assertEqual(sites[74],0x418AFA)
            self.assertEqual(sites[73],0x40B88A)

    def test_added_prefix_cannot_overflow_command_line(self):
        original=source_probe()
        lines=original.splitlines()
        target=next(i for i,s in enumerate(lines) if s.startswith('bp70 '))
        pad=4080-len(lines[target])
        lines[target]=lines[target].replace('gc"',' '*pad+'gc"')
        self.assertEqual(len(lines[target]),4080)
        with self.assertRaisesRegex(ValueError,'instrumented breakpoint exceeds'):
            trace.instrument_probe('\n'.join(lines)+'\n',reset_bp=76)


class EventIntegrityTests(unittest.TestCase):
    def check(self, lines, *, passed=False):
        output = trace.validate_event_integrity('\n'.join(lines),
            trace.instrument_probe(source_probe(), reset_bp=76), reset_bp=76)
        self.assertEqual(output['passed'], passed, output['errors'])
        self.assertEqual(len(output['raw_records']), sum('PTILE_' in line.upper() for line in lines))
        return output

    def test_whole_command_membership_and_terminal_boundary(self):
        report = self.check(valid_lines(), passed=True)
        self.assertEqual([e['seq'] for e in report['events']], list(range(1, 9)))
        self.assertEqual([r['marker'] for r in report['events'][6]['records']],
                         ['PTILE_INCREMENTAL_INPUT', 'PTILE_STATUS'])
        self.assertEqual(report['boundary_records'][0]['eip'], 0x406FA0)

    def test_replayed_block_fails_without_dropping_raw_records(self):
        lines = valid_lines()
        pos = next(i for i, line in enumerate(lines) if line.startswith('PTILE_EVENT seq=7 '))
        repeated = lines[:pos+3] + lines[pos:pos+3] + lines[pos+3:]
        report = self.check(repeated)
        self.assertTrue(any('sequence' in e for e in report['errors']))
        self.assertEqual(sum(e['seq'] == 7 for e in report['events']), 2)

    def test_reexecuted_command_retains_distinct_sequence_identity(self):
        # Output integrity alone must not confuse a new command execution with
        # output replay. Native pairing remains the caller's separate failure.
        lines = valid_lines()
        close = next(i for i, line in enumerate(lines) if line.startswith('PTILE_TRACE_CLOSED'))
        lines[close:close] = event(9, 72)
        report = self.check(lines, passed=True)
        self.assertEqual(report['events'][-1]['records'][0]['text'], report['events'][6]['records'][0]['text'])
        self.assertNotEqual(report['events'][-1]['seq'], report['events'][6]['seq'])

    def test_reset_reexecution_missing_gap_overflow_and_wrong_site_fail(self):
        for replacement in ('seq=0', 'seq=2', 'seq=4294967296'):
            lines = valid_lines(); lines[2] = lines[2].replace('seq=1', replacement)
            self.check(lines)
        for edit in (lambda s:s.replace('eip=00563480','eip=00563481'),
                     lambda s:s.replace('tid=1234','tid=0'),
                     lambda s:s.replace('esp=000edc74','esp=100000000'),
                     lambda s:s.replace('bp=76','bp=77')):
            lines = valid_lines(); lines[2] = edit(lines[2]); self.check(lines)
        lines = valid_lines(); lines[4:4] = event(1, 76); self.check(lines)
        lines = valid_lines(); del lines[2]; self.check(lines)

    def test_each_record_identity_is_bound_to_its_command(self):
        lines = valid_lines()
        for i, row in enumerate(lines):
            if not row.startswith('PTILE_') or row.startswith(('PTILE_EVENT', 'PTILE_TRACE_CLOSED')):
                continue
            for field in ('tid', 'esp'):
                if field + '=' not in row: continue
                for replacement in (field+'=deadbeef', field+'=nothex', field+'=1 '+field+'=1'):
                    with self.subTest(line=i, field=field, replacement=replacement):
                        changed=lines.copy(); changed[i]=re.sub(field+r'=[^ ]+', replacement, row)
                        self.check(changed)

    def test_missing_duplicate_wrong_order_unknown_or_wrong_hook_fail(self):
        lines=valid_lines()
        first = next(i for i, line in enumerate(lines) if line.startswith('PTILE_INCREMENTAL_INPUT'))
        cases=[lines[:first]+lines[first+1:], lines[:first]+[lines[first]]+lines[first:],
               lines[:first]+[lines[first+1],lines[first]]+lines[first+2:]]
        for replacement in ('PTILE_UNKNOWN tid=1234 esp=000edc74',
                            'PTILE_REJECT incremental', 'ptile_incremental_input tid=1234 esp=000edc74',
                            'noise PTILE_INCREMENTAL_INPUT tid=1234 esp=000edc74'):
            changed=lines.copy();changed[first]=replacement;cases.append(changed)
        changed=lines.copy();changed[first+1]=changed[first+1].replace('hook=incremental','hook=full_present');cases.append(changed)
        for value in cases: self.check(value)

    def test_truncated_final_printf_and_unfinished_event_fail(self):
        for tail in ('PTILE_EVENT seq=9 bp=75 tid=1234 eip=0056310c esp=',
                     'PTILE_COMPOSITION_GUARD tid=1234 esp='):
            self.check(valid_lines()[:-2]+[tail])
        self.check(valid_lines()[:-2]+event(9,75)[:1])

    def test_close_ends_membership_and_all_later_ptile_output_fails(self):
        good=valid_lines()
        for tail in (event(9,75),[record(74)[0]],[good[-2]],['PTILE_UNKNOWN'],['PTILE_REJECT incremental']):
            self.check(good+tail)
        self.check([good[-2]]+good)
        self.check(good[:-2]+['PTILE_TRACE_CLOSED tid=0 eip=00406fa0 esp=000edc98'])

    def test_old_uninstrumented_failures_cannot_qualify(self):
        self.check([row for row in valid_lines() if not row.startswith('PTILE_EVENT')])
        report=trace.validate_event_integrity('\n'.join(valid_lines()),source_probe(),reset_bp=76)
        self.assertFalse(report['passed'])
        self.assertEqual(len(report['raw_records']),len(valid_lines())-1)


if __name__ == '__main__':
    unittest.main()
