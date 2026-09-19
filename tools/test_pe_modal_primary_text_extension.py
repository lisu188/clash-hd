"""Independent fourteen-section PE replay/rebase and fail-closed fixtures."""
from dataclasses import replace
from pathlib import Path
import struct
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.patcher import pe_extension as pe
from src.patcher import pe_modal_primary_extension as primary
from src.patcher import pe_modal_primary_text_extension as text
from test_pe_modal_primary_extension import synthetic_slots, arguments as primary_arguments
from test_pe_extension import independent_image, rebase
from test_pe_modal_extension import independent_section_adjacency
from test_pe_army_extension import hook


def synthetic_primary():
    base = synthetic_slots()
    image = bytearray(primary._extend_verified_image(base, **primary_arguments(base)).image)
    view = pe.inspect_pe(bytes(image))
    offset = view.file_offset(0x10F0, 5)
    image[offset:offset + 5] = b'\xe8' + struct.pack('<i', 0x401100 - 0x4010F0 - 5)
    return bytes(image)


def arguments(candidate):
    layout = text.allocation_layout(candidate)
    code = bytearray(b'\x90' * 6003)
    rows = (pe.CodeRelocation(1, 'abs32', 0x402008, 'mapped original data'),
            pe.CodeRelocation(4095, 'abs32', layout.code_va + 5500, 'new code across page'),
            pe.CodeRelocation(5002, 'rel32', 0x401100, 'native text target stand-in'))
    for row in rows:
        value = row.target if row.kind == 'abs32' else row.target - layout.code_va - row.offset - 4
        struct.pack_into('<I', code, row.offset, value & 0xffffffff)
    site = hook(candidate, 0x4010F0, layout.code_va, 5)
    site = replace(site, new=b'\xe8' + site.new[1:])
    return dict(code=bytes(code), code_va=layout.code_va, relocations=rows, hooks=(site,),
                binding={'fixture': 'synthetic primary-text PE format only'})


class PrimaryTextFormatTests(unittest.TestCase):
    def build(self, **changes):
        base = synthetic_primary()
        return text._extend_verified_image(base, **(arguments(base) | changes))

    def test_replay_preserves_every_old_header_and_unedited_byte(self):
        base = synthetic_primary(); before = pe.inspect_pe(base); result = self.build()
        after = pe.inspect_pe(result.image)
        self.assertEqual(after.sections[:13], before.sections)
        self.assertEqual(len(after.sections), 14)
        last = after.sections[-1]
        self.assertEqual((last.name.rstrip(b'\0'), last.header_offset, last.characteristics),
                         (b'.hdptxt', 0x370, pe.RX_CODE))
        self.assertEqual((last.rva, last.raw_offset, last.virtual_size),
                         (before.image_size, len(base), 0x20000))
        self.assertEqual(after.image_size, before.image_size + 0x20000)
        self.assertEqual(result.image[0x398:0x400], base[0x398:0x400])
        self.assertTrue(all(row['rva'] == row['expected_rva'] for row in independent_section_adjacency(result.image)))
        replay = bytearray(base); changed = set()
        for edit in result.edits:
            self.assertEqual(bytes(replay[edit.offset:edit.offset + len(edit.old)]), edit.old)
            self.assertEqual(edit.va, before.image_base + edit.rva)
            replay[edit.offset:edit.offset + len(edit.old)] = edit.new
            changed.update(range(edit.offset, edit.offset + len(edit.old)))
        self.assertEqual(bytes(replay), result.image)
        self.assertTrue(all(value == result.image[index] for index, value in enumerate(base) if index not in changed))
        self.assertEqual(len(result.metadata['hooks']), 1)
        for key in ('installation_ready', 'runtime_executed', 'manual_input_proof', 'promotion_ready'):
            self.assertIs(result.metadata[key], False)

    def test_independent_rebase_preserves_old_relocations_and_exact_new_fields(self):
        base = synthetic_primary(); result = self.build(); args = arguments(base)
        old_memory, _, old_fields, _ = independent_image(base)
        memory, sections, fields, directory = independent_image(result.image)
        layout = text.allocation_layout(base)
        self.assertEqual(fields, sorted(old_fields + [layout.code_rva + 1, layout.code_rva + 4095]))
        self.assertEqual(sections[-1][0], b'.hdptxt')
        self.assertEqual(directory, (result.metadata['relocation_rva'], result.metadata['relocation_bytes']))
        for delta in (-0x100000, 0x2100000):
            moved = rebase(memory, fields, delta); old_moved = rebase(old_memory, old_fields, delta)
            for rva in old_fields:
                self.assertEqual(moved[rva:rva + 4], old_moved[rva:rva + 4])
            for row in args['relocations']:
                offset = layout.code_rva + row.offset
                if row.kind == 'abs32':
                    self.assertEqual(struct.unpack_from('<I', moved, offset)[0], row.target + delta)
                else:
                    self.assertEqual(moved[offset:offset + 4], memory[offset:offset + 4])
            site = args['hooks'][0]
            self.assertEqual(site.va + delta + 5 + struct.unpack_from('<i', moved, site.rva + 1)[0],
                             args['code_va'] + delta)
        view = pe.inspect_pe(base); offset = view.file_offset(view.relocation_rva, view.relocation_size)
        self.assertEqual(result.image[offset:offset + view.relocation_size], base[offset:offset + view.relocation_size])
        self.assertEqual(result.metadata['removed_highlow'], [])

    def test_layout_collision_count_permissions_and_gaps_rejected(self):
        base = synthetic_primary(); view = pe.inspect_pe(base)
        for wrong in (synthetic_slots(), self.build().image):
            with self.assertRaisesRegex(ValueError, 'thirteen-section'): text.allocation_layout(wrong)
        for offset in (0x370, 0x377, 0x397):
            bad = bytearray(base); bad[offset] = 1
            with self.subTest(offset=offset), self.assertRaisesRegex(ValueError, 'header'):
                text.allocation_layout(bytes(bad))
        for index in (-6, -5, -4, -3, -2, -1):
            bad = bytearray(base)
            struct.pack_into('<I', bad, view.sections[index].header_offset + 36,
                             view.sections[index].characteristics ^ 0x80000000)
            with self.subTest(index=index), self.assertRaisesRegex(ValueError, 'protections'):
                text.allocation_layout(bytes(bad))
        bad = bytearray(base)
        struct.pack_into('<I', bad, view.sections[-2].header_offset + 8, view.sections[-2].raw_size)
        with self.assertRaisesRegex(ValueError, 'nonadjacent'): text.allocation_layout(bytes(bad))

    def test_only_one_exact_five_byte_call_and_declared_displacement_allowed(self):
        args = arguments(synthetic_primary()); site = args['hooks'][0]
        changed = (dict(hooks=()), dict(hooks=(site, site)), dict(code_va=args['code_va'] + 4096),
                   dict(hooks=(replace(site, old=b'\0' * 5),)), dict(hooks=(replace(site, new=b'\xe9' + site.new[1:]),)),
                   dict(hooks=(replace(site, new=site.new[:-1]),)), dict(hooks=(replace(site, old=None),)),
                   dict(hooks=(replace(site, relocations=()),)), dict(hooks=(replace(site, relocations=None),)),
                   dict(hooks=(replace(site, relocations=(site.relocations[0], site.relocations[0])),)),
                   dict(hooks=(replace(site, offset=site.offset + 1),)), dict(hooks=(replace(site, va=site.va + 1),)))
        for change in changed:
            with self.subTest(change=change.keys()), self.assertRaises(ValueError): self.build(**change)
        for field in (dict(offset=True), dict(offset=2), dict(kind='abs32'), dict(target=0x402008), dict(target=1 << 32)):
            changed_site = replace(site, relocations=(replace(site.relocations[0], **field),))
            with self.subTest(field=field), self.assertRaises(ValueError): self.build(hooks=(changed_site,))

    def test_code_size_relocations_and_reservation_fail_closed(self):
        args = arguments(synthetic_primary())
        for change in (dict(code=b''), dict(code=bytearray(args['code'])), dict(code=b'\x90' * text.CODE_RESERVATION),
                       dict(relocations=None), dict(binding=None), dict(relocations=(object(),)),
                       dict(relocations=args['relocations'] + (args['relocations'][0],)),
                       dict(code=b'\x90' * (text.CODE_RESERVATION - 1), relocations=())):
            with self.subTest(change=change.keys()), self.assertRaises(ValueError): self.build(**change)
        for field in (dict(offset=-1), dict(offset=True), dict(offset=len(args['code']) - 3),
                      dict(kind='HIGH'), dict(purpose=''), dict(target=0x1234), dict(target=1 << 32)):
            rows = (replace(args['relocations'][0], **field),) + args['relocations'][1:]
            with self.subTest(field=field), self.assertRaises(ValueError): self.build(relocations=rows)

    def test_changed_old_call_malformed_old_relocations_and_displaced_highlow_rejected(self):
        base = synthetic_primary(); args = arguments(base); view = pe.inspect_pe(base)
        bad = bytearray(base); bad[args['hooks'][0].offset + 1] ^= 1
        with self.assertRaisesRegex(ValueError, 'old bytes'): text._extend_verified_image(bytes(bad), **args)
        offset = view.file_offset(view.relocation_rva, view.relocation_size)
        for mode in ('kind', 'size', 'duplicate'):
            bad = bytearray(base)
            if mode == 'kind': struct.pack_into('<H', bad, offset + 8, 0xA001)
            elif mode == 'size': struct.pack_into('<I', bad, offset + 4, 9)
            else: bad[offset + 10:offset + 12] = bad[offset + 8:offset + 10]
            with self.subTest(mode=mode), self.assertRaises(ValueError): text._extend_verified_image(bytes(bad), **args)
        # A fabricated CALL at a historical relocation remains rejected even
        # though its own expected-old-byte record matches the supplied image.
        bad = bytearray(base); at = view.file_offset(0x1000, 5)
        bad[at:at + 5] = b'\xe8' + bytes(4)
        site = hook(bytes(bad), 0x401000, args['code_va'], 5)
        site = replace(site, new=b'\xe8' + site.new[1:])
        with self.assertRaises(ValueError): text._extend_verified_image(bytes(bad), **(args | dict(hooks=(site,))))


if __name__ == '__main__': unittest.main(verbosity=2)
