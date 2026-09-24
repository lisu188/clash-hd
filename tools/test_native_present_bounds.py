"""Execute the emitted adapter on x86 with a labeled recording blitter."""
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import unittest

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]
from src.patcher import native_present_bounds as tool
from src.patcher import partial_tile_clip as clip
from src.patcher import pe_extension as pe
import test_modal_widget_bounds as fixture
from test_pe_extension import independent_image, rebase
from test_build_framed_modal_candidate import replay

SRC = fixture.DATA + 0x100
PRIMARY = fixture.DATA + 0x200
RECORD = fixture.DATA + 0x10
STRIDE = 128


def model(case):
    left, top, right, bottom = case['rect']
    dx, dy = case.get('dest', (left, top))
    if case.get('foreign_source') or case.get('foreign_destination') or (left & 65535, top & 65535) != (dx & 65535, dy & 65535):
        return (right, bottom, dx, dy)
    left, top, right, bottom = (v & 65535 for v in (left, top, right, bottom))
    w = min(case['source_size'][0], case['primary_size'][0])
    h = min(case['source_size'][1], case['primary_size'][1])
    if not w or not h or left >= w or top >= h or right < left or bottom < top:
        return None
    return (min(right, w - 1), min(bottom, h - 1), dx, dy)


def program(cases):
    guard = tool.emit_guard(fixture.CODE, map_pointer=fixture.DATA, primary=PRIMARY, native_blit=fixture.OWNER)
    spy = clip._Assembler(fixture.OWNER)
    spy.emit('9c608b3d'); spy.u32(RECORD)
    spy.emit('c70701000000')
    for source, target in [(i * 4, 4 + i * 4) for i in range(8)] + [(40 + i * 4, 36 + i * 4) for i in range(4)] + [(32, 52)]:
        spy.emit('8b4424' + f'{source:02x}' + '8947' + f'{target:02x}')
    spy.emit('c744241c63000000619dc21000')
    a = clip._Assembler(fixture.BASE + 0x1000); a.emit('9c60')
    seeds = []
    for index, case in enumerate(cases):
        output = fixture.OUTPUT + index * STRIDE
        left, top, right, bottom = case['rect']
        dx, dy = case.get('dest', (left, top))
        for address, value in ((fixture.DATA, SRC), (SRC, case['source_size'][0] | case['source_size'][1] << 16),
                               (PRIMARY, case['primary_size'][0] | case['primary_size'][1] << 16), (RECORD, output)):
            a.emit('c705'); a.u32(address); a.u32(value)
        a.emit('8925'); a.u32(output + 56)
        for value in (dy, dx, bottom, right): a.emit('68'); a.u32(value)
        registers = [SRC + (256 if case.get('foreign_source') else 0), top, 0x12345678 if case.get('foreign_destination') else 0,
                     left, 0, 0x11223344, 0x22334455, 0x33445566]
        seeds.append(registers)
        for register, value in enumerate(registers):
            if register != 4: a.emit(f'{0xB8 + register:02x}'); a.u32(value)
        a.emit('68'); a.u32(case.get('flags', 0x202)); a.emit('9d')
        a.emit('e8'); a.u32(guard.base_va - a.base - len(a.code) - 4)
        a.emit('a3'); a.u32(output + 60)
        a.emit('9c8f05'); a.u32(output + 64)
        for register in range(8):
            a.emit('89' + f'{5 + register * 8:02x}'); a.u32(output + 72 + register * 4)
        for address, target in ((SRC, 108), (PRIMARY, 112)):
            a.emit('a1'); a.u32(address); a.emit('a3'); a.u32(output + target)
    a.emit('619d31c0c3')
    driver = a.finish()
    if len(driver) >= fixture.CODE - a.base: raise ValueError('Fixture overlaps production guard')
    code = bytearray(0x100000)
    for address, blob in ((a.base, driver), (fixture.CODE, guard.code), (fixture.OWNER, spy.finish())):
        code[address - fixture.BASE:address - fixture.BASE + len(blob)] = blob
    return bytes(code), seeds


class SourceTests(unittest.TestCase):
    def test_exact_source_binding_and_small_guard(self):
        self.assertTrue(all(tool.sha((tool.ROOT / p).read_bytes()) == h for p, h in tool.PINNED.items()))
        a = tool.emit_guard(0x600000); b = tool.emit_guard(0x600000)
        self.assertEqual(a, b); self.assertLess(len(a.code), 512)
        self.assertEqual(len(clip.absolute_relocation_offsets(a)), 3)
        self.assertFalse(a.installation_ready)
        for address in (0, True, -1, 0x80000000):
            with self.assertRaises(ValueError): tool.emit_guard(address)
        with self.assertRaises(ValueError): tool.build_candidate(b'not original', 'framed', '3840x2160')

    def test_reproduced_4k_cursor_rectangles_are_clipped_or_empty(self):
        case = dict(source_size=(640, 480), primary_size=(3840, 2160), rect=(32, 16, 607, 1144))
        self.assertEqual(model(case), (607, 479, 32, 16))
        self.assertIsNone(model(dict(case, rect=(32, 1144, 607, 463))))
        self.assertIsNone(model(dict(case, rect=(1824, 1144, 1900, 1200))))
        self.assertEqual(model(dict(case, foreign_destination=True)), (607, 1144, 32, 16))


class NativeTests(unittest.TestCase):
    setUpClass = classmethod(fixture.NativeGuardTests.setUpClass.__func__)

    def test_native_guard_preserves_abi_and_clips_all_supported_extents(self):
        cases = []
        for dimensions in ((800, 600), (802, 602), (1024, 768), (1280, 720), (1280, 960), (1366, 768), (1920, 1080), (2560, 1440), (3440, 1440), (3840, 2160)):
            w, h = dimensions
            for source in ((640, 480), dimensions):
                for rect in ((32, 16, 607, 1144), (32, 1144, 607, 463), (0, 0, w - 1, h - 1),
                             (0, 0, 0, 0), (w - 1, h - 1, w + 5, h + 5), (65535, 0, 0, 0), (32, 20, 0, 16)):
                    for flags in (0x202, 0xED7):
                        cases.append(dict(source_size=source, primary_size=dimensions, rect=rect, flags=flags))
        base = dict(source_size=(640, 480), primary_size=(3840, 2160), rect=(32, 16, 607, 1144))
        cases += [dict(base, **extra) for extra in ({'foreign_source': True}, {'foreign_destination': True},
                  {'dest': (33, 16)}, {'dest': (32, 17)}, {'source_size': (0, 480)}, {'primary_size': (3840, 0)})]
        code, seeds = program(cases)
        path = self.folder / 'present-fixture.bin'
        if self.runner:
            path.write_bytes(code); command = [str(self.runner), str(path), str(len(cases) * STRIDE)]
            flags = {'creationflags': subprocess.CREATE_NO_WINDOW}
        else:
            path.write_bytes(fixture.elf(code, len(cases) * STRIDE)); path.chmod(0o700); command = [str(path)]; flags = {}
        result = subprocess.run(command, capture_output=True, timeout=20, **flags)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(result.stdout), len(cases) * STRIDE)
        for case, seed, row in zip(cases, seeds, struct.iter_unpack('<32I', result.stdout)):
            expected = model(case)
            with self.subTest(case=case):
                self.assertEqual(row[0], int(expected is not None))
                self.assertEqual(row[15], 99 if expected is not None else 0)
                seed[0] = row[15]; seed[4] = row[14]
                self.assertEqual(tuple(row[18:26]), tuple(v & 0xFFFFFFFF for v in seed))
                self.assertEqual(row[16] & fixture.MASK, case.get('flags', 0x202) & fixture.MASK)
                if expected is not None: self.assertEqual(row[9:13], expected)
                self.assertEqual(row[27], case['source_size'][0] | case['source_size'][1] << 16)
                self.assertEqual(row[28], case['primary_size'][0] | case['primary_size'][1] << 16)
        print('NATIVE_PRESENT_CPU_CASES=' + str(len(cases)), flush=True)


@unittest.skipUnless(os.environ.get('NATIVE_PRESENT_ORIGINAL'), 'original asset path required')
class OriginalTests(unittest.TestCase):
    def test_actual_predecessors_and_patches_replay_and_relocate(self):
        original = Path(os.environ['NATIVE_PRESENT_ORIGINAL']).read_bytes()
        rows = []
        for profile, resolution in (('classic', '800x600'), ('classic', '3840x2160'), ('framed', '3840x2160'),
                                    ('completehd', '1920x1080'), ('modalwidgets', '1024x768')):
            with self.subTest(profile=profile, resolution=resolution):
                image, metadata, probe = tool.build_candidate(original, profile, resolution)
                base, parent, _, _ = tool.predecessor(original, profile, resolution)
                self.assertEqual(replay(base, metadata['edits']), image)
                before, after = pe.inspect_pe(base), pe.inspect_pe(image)
                self.assertEqual(after.sections[:-1], before.sections)
                self.assertEqual(len(metadata['hooks']), 5)
                self.assertEqual(metadata['new_highlow_count'], 3)
                offset = after.file_offset(tool.BLIT - after.image_base, tool.BLIT_SIZE)
                self.assertEqual(tool.sha(image[offset:offset + tool.BLIT_SIZE]), tool.BLIT_SHA256)
                memory, _, fields, _ = independent_image(image)
                old_memory, _, old_fields, _ = independent_image(base)
                for delta in (-0x100000, 0x2100000):
                    rebased = rebase(memory, fields, delta); old_rebased = rebase(old_memory, old_fields, delta)
                    for rva in old_fields: self.assertEqual(rebased[rva:rva + 4], old_rebased[rva:rva + 4])
                    for r in metadata['relocations']:
                        if r['kind'] == 'abs32':
                            self.assertEqual(struct.unpack_from('<I', rebased, metadata['code_va'] - before.image_base + r['offset'])[0], r['target'] + delta)
                self.assertEqual(metadata['source_hashes'], {p: tool.sha((tool.ROOT / p).read_bytes()) for p in metadata['source_hashes']})
                self.assertEqual(tool.sha(probe.encode()), metadata['probe_sha256'])
                rows.append({k: metadata[k] for k in ('profile', 'resolution', 'stage', 'candidate_sha256', 'base_candidate_sha256', 'source_hashes', 'hooks')})
        report = os.environ.get('NATIVE_PRESENT_REPORT')
        if report: Path(report).write_text(json.dumps(dict(profiles=rows, original_unchanged=tool.sha(original) == pe.ORIGINAL_SHA256), indent=2))


if __name__ == '__main__': unittest.main(verbosity=2)
