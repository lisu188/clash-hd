#!/usr/bin/env python3
"""Offline PE allocation fixtures; no executable output or process launch."""

from __future__ import annotations

import hashlib
from dataclasses import replace
from pathlib import Path
import struct
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "patcher"))
import pe_extension as tool

ORIGINAL = Path("C:/Clash/clash95.exe")
EXISTING_CANDIDATE = Path("C:/ClashTests/hd-completion/continuity-daydiag-combined-v5-control-20260905-125300/candidate/clash95_hd_surfdump_20260905_130340.exe")
COMBINED800_SHA = "0a75cf35f42efe1e44fba1ac4031eaae5323cdff51aa19d261c36c5bb84691c2"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def synthetic_pe():
    data = bytearray(0x800)
    data[:2] = b"MZ"
    struct.pack_into("<I", data, 0x3C, 0x70)
    data[0x70:0x74] = b"PE\0\0"
    struct.pack_into("<HHIIIHH", data, 0x74, 0x14C, 3, 123456, 0, 0, 224, 0x182)
    opt = 0x88
    struct.pack_into("<H", data, opt, 0x10B)
    struct.pack_into("<I", data, opt + 4, 0x200)
    struct.pack_into("<III", data, opt + 28, 0x400000, 0x1000, 0x200)
    struct.pack_into("<II", data, opt + 56, 0x4000, 0x400)
    struct.pack_into("<I", data, opt + 92, 16)
    struct.pack_into("<II", data, opt + 136, 0x3000, 16)
    # Deliberately use the actual image's unusual zero-VirtualSize convention.
    for index, (name, rva, size, offset, flags) in enumerate((
        (b".text", 0x1000, 0x200, 0x400, 0x60000020),
        (b".bss", 0x2000, 0x1000, 0, 0xC0000080),
        (b".reloc", 0x3000, 0x200, 0x600, 0x42000040),
    )):
        struct.pack_into("<8sIIIIIIHHI", data, opt + 224 + index * 40,
                         name, 0, rva, size, offset, 0, 0, 0, 0, flags)
    data[0x400:0x600] = bytes([0x90]) * 0x200
    for offset, value in ((1, 0x402008), (9, 0x401100), (17, 0x401008)):
        struct.pack_into("<I", data, 0x400 + offset, value)
    struct.pack_into("<II4H", data, 0x600, 0x1000, 16, 0x3001, 0x3009, 0x3011, 0)
    return bytes(data)


def independent_image(data):
    """Small independent loader view; does not call allocator parser helpers."""
    pe = int.from_bytes(data[60:64], "little")
    opt = pe + 24
    count = int.from_bytes(data[pe + 6:pe + 8], "little")
    image_size = int.from_bytes(data[opt + 56:opt + 60], "little")
    headers = int.from_bytes(data[opt + 60:opt + 64], "little")
    memory = bytearray(image_size)
    memory[:headers] = data[:headers]
    sections = []
    for index in range(count):
        pos = opt + 224 + index * 40
        name = data[pos:pos + 8].rstrip(b"\0")
        virtual, rva, raw_size, raw = struct.unpack_from("<IIII", data, pos + 8)
        flags = int.from_bytes(data[pos + 36:pos + 40], "little")
        if raw:
            memory[rva:rva + raw_size] = data[raw:raw + raw_size]
        sections.append((name, rva, max(virtual, raw_size), raw, raw_size, flags))
    reloc_rva, reloc_size = struct.unpack_from("<II", memory, opt + 136)
    position, fixups = reloc_rva, []
    while position < reloc_rva + reloc_size:
        page, size = struct.unpack_from("<II", memory, position)
        assert size >= 8 and size % 4 == 0
        for at in range(position + 8, position + size, 2):
            word = int.from_bytes(memory[at:at + 2], "little")
            assert word >> 12 in (0, 3)
            if word >> 12 == 3:
                fixups.append(page + (word & 4095))
        position += size
    assert position == reloc_rva + reloc_size
    return memory, sections, fixups, (reloc_rva, reloc_size)


def rebase(memory, fixups, delta):
    result = bytearray(memory)
    for rva in fixups:
        old = int.from_bytes(result[rva:rva + 4], "little")
        result[rva:rva + 4] = ((old + delta) & 0xFFFFFFFF).to_bytes(4, "little")
    return result


class PEExtensionTests(unittest.TestCase):
    def code(self, base=0x404000):
        payload = bytearray([0x90] * 6003)
        records = (
            tool.CodeRelocation(1, "abs32", 0x402008, "unbacked BSS object"),
            tool.CodeRelocation(4095, "abs32", 0x401100, "field crosses page boundary"),
            tool.CodeRelocation(5002, "abs32", base + 5500, "internal code pointer"),
            tool.CodeRelocation(10, "rel32", 0x401008, "native relative transfer"),
        )
        for record in records:
            value = record.target if record.kind == "abs32" else (record.target - (base + record.offset + 4)) & 0xFFFFFFFF
            struct.pack_into("<I", payload, record.offset, value)
        return bytes(payload), records

    def build(self, candidate=None, *, code=None, records=None, base=0x404000):
        default_code, default_records = self.code(base)
        return tool._extend_verified_image(synthetic_pe() if candidate is None else candidate,
                                           code=default_code if code is None else code, code_va=base,
                                           relocations=default_records if records is None else records,
                                           binding={"fixture": "synthetic, not runtime proof"})

    def test_additive_rx_section_complete_metadata_and_independent_loader(self):
        original = synthetic_pe()
        result = self.build(original)
        memory, sections, fixups, directory = independent_image(result.image)
        before_memory, before_sections, before_fixups, before_directory = independent_image(original)
        self.assertEqual(sections[:-1], before_sections)
        self.assertEqual(sections[-1][0], b".hdcode")
        self.assertEqual(sections[-1][-1], 0x60000020)
        self.assertFalse(sections[-1][-1] & 0x80000000)
        self.assertEqual(sections[-1][1], 0x4000)
        self.assertEqual(fixups, before_fixups + [0x4001, 0x4FFF, 0x538A])
        self.assertEqual(memory[directory[0]:directory[0] + before_directory[1]],
                         before_memory[before_directory[0]:sum(before_directory)])
        self.assertEqual(result.image[len(original):len(original) + 6003], self.code()[0])
        self.assertEqual(result.image[0x300:0x400], original[0x300:0x400])
        self.assertEqual(result.image[0x400:len(original)], original[0x400:])
        # Rebuild independently from the exact old/new records and verify every
        # original byte outside the declared header edits is unchanged.
        rebuilt = bytearray(original)
        touched = set()
        for edit in result.edits:
            self.assertEqual(bytes(rebuilt[edit.offset:edit.offset + len(edit.old)]), edit.old)
            rebuilt[edit.offset:edit.offset + len(edit.old)] = edit.new
            touched.update(range(edit.offset, edit.offset + len(edit.old)))
            self.assertEqual(edit.va, 0x400000 + edit.rva)
        self.assertEqual(bytes(rebuilt), result.image)
        self.assertTrue(all(original[i] == result.image[i] for i in range(len(original)) if i not in touched))
        self.assertEqual(result.edits[-1].old, b"")
        self.assertEqual(result.edits[-1].offset, len(original))
        self.assertFalse(result.installation_ready)
        self.assertFalse(result.metadata["installation_ready"])
        self.assertEqual(result.metadata["old_highlow_count"], 3)
        self.assertEqual(result.metadata["new_highlow_count"], 3)

    def test_independent_rebase_preserves_old_fields_and_rebases_only_abs32(self):
        original = synthetic_pe()
        result = self.build(original)
        new_memory, sections, new_fixups, _ = independent_image(result.image)
        old_memory, old_sections, old_fixups, _ = independent_image(original)
        for delta in (0x100000, -0x100000, 0x2100000):
            old_rebased = rebase(old_memory, old_fixups, delta)
            new_rebased = rebase(new_memory, new_fixups, delta)
            for _, rva, size, *_ in old_sections:
                self.assertEqual(old_rebased[rva:rva + size], new_rebased[rva:rva + size])
            for record in self.code()[1]:
                location = 0x4000 + record.offset
                actual = int.from_bytes(new_rebased[location:location + 4], "little")
                if record.kind == "abs32":
                    self.assertEqual(actual, (record.target + delta) & 0xFFFFFFFF)
                else:
                    self.assertEqual(new_memory[location:location + 4], new_rebased[location:location + 4])

    def test_zero_virtual_size_bss_is_memory_but_not_file_backed(self):
        pe = tool.inspect_pe(synthetic_pe())
        self.assertTrue(pe.contains_memory(0x2008))
        with self.assertRaisesRegex(tool.PEExtensionError, "file-backed"):
            pe.file_offset(0x2008, 4)
        memory, _, _, _ = independent_image(synthetic_pe())
        self.assertEqual(memory[0x2000:0x3000], bytes(4096))

    def test_fail_closed_layout_cases(self):
        mutations = {
            "signature": (0x70, b"PX\0\0"),
            "machine": (0x74, struct.pack("<H", 0x8664)),
            "stripped relocations": (0x86, struct.pack("<H", 0x183)),
            "checksum": (0xC8, struct.pack("<I", 1)),
            "signature directory": (0x88 + 128, struct.pack("<II", 0x800, 8)),
            "section alignment": (0xA8, struct.pack("<I", 0x1800)),
            "file alignment": (0xAC, struct.pack("<I", 0x300)),
            "image extent": (0xC0, struct.pack("<I", 0x5000)),
            "raw overlap": (0x168 + 80 + 20, struct.pack("<I", 0x400)),
            "memory overlap": (0x168 + 80 + 12, struct.pack("<I", 0x2000)),
            "raw overflow": (0x168 + 80 + 16, struct.pack("<I", 0x1000)),
            "nonzero header slot": (0x1E0, b"X"),
            "BSS without uninitialized flag": (0x168 + 40 + 36, struct.pack("<I", 0xC0000040)),
            "unmapped directory": (0x88 + 136, struct.pack("<II", 0x2000, 16)),
            "overflow image base": (0xA4, struct.pack("<I", 0xFFFF0000)),
        }
        for label, (offset, replacement) in mutations.items():
            with self.subTest(label=label):
                data = bytearray(synthetic_pe())
                data[offset:offset + len(replacement)] = replacement
                with self.assertRaises(tool.PEExtensionError):
                    if label == "overflow image base":
                        self.build(bytes(data), base=0xFFFF4000, code=bytes(0xC001), records=())
                    else:
                        self.build(bytes(data))
        for data in (synthetic_pe() + bytes(512), synthetic_pe()[:-1], b"MZ"):
            with self.assertRaises(tool.PEExtensionError):
                self.build(data)

    def test_malformed_duplicate_unmapped_and_unsupported_old_relocations(self):
        changes = ((0x604, struct.pack("<I", 7)), (0x604, struct.pack("<I", 14)),
                   (0x604, struct.pack("<I", 20)), (0x600, struct.pack("<I", 0x1001)),
                   (0x608, struct.pack("<H", 0xA001)), (0x60A, struct.pack("<H", 0x3001)),
                   (0x60A, struct.pack("<H", 0x3003)), (0x608, struct.pack("<H", 0x3FFF)),
                   (0x600, struct.pack("<I", 0x2000)))
        for offset, replacement in changes:
            data = bytearray(synthetic_pe())
            data[offset:offset + len(replacement)] = replacement
            with self.subTest(offset=offset, replacement=replacement.hex()), self.assertRaises(tool.PEExtensionError):
                self.build(bytes(data))
        data = bytearray(synthetic_pe())
        struct.pack_into("<II", data, 0x610, 0x1000, 8)
        struct.pack_into("<I", data, 0x88 + 140, 24)
        with self.assertRaisesRegex(tool.PEExtensionError, "duplicate"):
            self.build(bytes(data))

    def test_explicit_relocation_contract_rejects_bad_offsets_values_and_kinds(self):
        code, records = self.code()
        invalid = [records + (records[0],),
                   (tool.CodeRelocation(2, "abs32", 0x402008, "overlap"), *records),
                   (tool.CodeRelocation(-1, "abs32", 0x402008, "negative"),),
                   (tool.CodeRelocation(len(code) - 3, "abs32", 0x402008, "truncated"),),
                   (tool.CodeRelocation(True, "abs32", 0x402008, "bool"),),
                   (tool.CodeRelocation(1, "abs64", 0x402008, "unsupported"),),
                   (tool.CodeRelocation(1, "abs32", 0x402008, ""),),
                   (tool.CodeRelocation(1, "abs32", 0x402009, "wrong target"),),
                   (tool.CodeRelocation(1, "abs32", 0x7FFE0320, "external address"),),
                   (tool.CodeRelocation(1, "abs32", 0x403800, "unmapped section gap"),),
                   (object(),)]
        for bad in invalid:
            with self.subTest(records=bad), self.assertRaises(tool.PEExtensionError):
                self.build(code=code, records=bad)
        with self.assertRaisesRegex(tool.PEExtensionError, "code VA"):
            self.build(base=0x405000)
        with self.assertRaises(tool.PEExtensionError):
            self.build(code=b"", records=())

    def test_no_new_absolute_fields_still_preserves_whole_old_relocation_table(self):
        result = self.build(code=b"\xC3", records=())
        self.assertEqual(result.metadata["new_highlow_count"], 0)
        self.assertEqual(independent_image(result.image)[2], independent_image(synthetic_pe())[2])

    def hook(self, rva=0x1000, size=7, *, kind="rel32", target=0x404000):
        candidate = synthetic_pe()
        offset = 0x400 + rva - 0x1000
        opcode = b"\xE9" if kind == "rel32" else b"\xB8"
        value = (target - (0x400000 + rva + 5)) & 0xFFFFFFFF if kind == "rel32" else target
        new = opcode + struct.pack("<I", value) + b"\x90" * (size - 5)
        return tool.HookPatch(offset, rva, 0x400000 + rva, candidate[offset:offset + size], new,
                              "synthetic hook, not an installation recipe",
                              (tool.CodeRelocation(1, kind, target, "explicit hook operand"),))

    def hook_build(self, hooks, removed):
        code, records = self.code()
        return tool._extend_verified_image(synthetic_pe(), code=code, code_va=0x404000,
                                           relocations=records, hooks=hooks, removed_highlow_rvas=removed,
                                           binding={"stage": "synthetic-hook-validation", "base_stage": "synthetic"})

    def test_hooks_remove_only_displaced_fields_and_merge_retargeted_absolute_fields(self):
        jump = self.hook()
        absolute = self.hook(0x1008, kind="abs32", target=0x404100)
        result = self.hook_build((jump, absolute), (0x1001, 0x1009))
        memory, sections, fixups, directory = independent_image(result.image)
        original = synthetic_pe()
        before, old_sections, old_fixups, _ = independent_image(original)
        self.assertEqual(fixups, [0x1009, 0x1011, 0x4001, 0x4FFF, 0x538A])
        self.assertEqual(result.image[0x600:0x800], original[0x600:0x800])
        self.assertEqual(result.metadata["retained_highlow_count"], 1)
        self.assertEqual(result.metadata["new_highlow_count"], 4)
        self.assertEqual([row["rva"] for row in result.metadata["removed_highlow"]], [0x1001, 0x1009])
        self.assertTrue(result.metadata["relocation_directory_merged"])
        self.assertEqual(result.edits[:2], (
            tool.ByteEdit(jump.offset, jump.rva, jump.va, jump.old, jump.new, jump.purpose),
            tool.ByteEdit(absolute.offset, absolute.rva, absolute.va, absolute.old, absolute.new, absolute.purpose)))
        # The new directory has one block for the old page, despite both a
        # retained old field and a retargeted absolute hook field on that page.
        self.assertEqual(struct.unpack_from("<II", memory, directory[0]), (0x1000, 12))
        for delta in (0x100000, -0x100000):
            expected = rebase(before, old_fixups, delta)
            for hook in (jump, absolute):
                expected[hook.rva:hook.rva + len(hook.new)] = hook.new
                for field in hook.relocations:
                    if field.kind == "abs32":
                        struct.pack_into("<I", expected, hook.rva + field.offset, (field.target + delta) & 0xFFFFFFFF)
            rebased = rebase(memory, fixups, delta)
            for _, rva, size, *_ in old_sections:
                self.assertEqual(rebased[rva:rva + size], expected[rva:rva + size])
            self.assertEqual(rebased[jump.rva:jump.rva + len(jump.new)], jump.new)
            self.assertEqual(int.from_bytes(rebased[0x1009:0x100D], "little"), 0x404100 + delta)
            corrupted = rebase(memory, fixups + [0x1001], delta)
            self.assertNotEqual(corrupted[jump.rva:jump.rva + len(jump.new)], jump.new)

    def test_hook_removal_list_and_whole_field_coverage_fail_closed(self):
        hook = self.hook()
        for removals in ((), (0x1001, 0x1009), (0x1009,), (0x401001,), (0x1001, 0x1001), (True,)):
            with self.subTest(removals=removals), self.assertRaises(tool.PEExtensionError):
                self.hook_build((hook,), removals)
        for partial in (self.hook(0x1003, size=5), self.hook(0x1000, size=5)):
            # First partial clips the beginning of 1001..1004. The second ends
            # exactly at1005 and therefore covers it; shorten that one by1.
            if partial.rva == 0x1000:
                partial = replace(partial, old=partial.old[:-1], new=b"\x90" * 4, relocations=())
            with self.subTest(partial=partial.rva), self.assertRaisesRegex(tool.PEExtensionError, "partially overlaps"):
                self.hook_build((partial,), (0x1001,))
        with self.assertRaisesRegex(tool.PEExtensionError, "exactly match"):
            self.hook_build((self.hook(0x1020, size=8),), (0x1001,))

    def test_hook_mapping_old_bytes_overlap_and_new_operand_contract_are_required(self):
        hook = self.hook()
        mutations = (replace(hook, offset=hook.offset + 1), replace(hook, rva=hook.rva + 1),
                     replace(hook, va=hook.va + 1), replace(hook, old=bytes(7)),
                     replace(hook, new=hook.new[:-1]), replace(hook, new=hook.old),
                     replace(hook, purpose=""), replace(hook, offset=True),
                     replace(hook, relocations=(replace(hook.relocations[0], offset=4),)),
                     replace(hook, relocations=(replace(hook.relocations[0], target=0x404001),)),
                     replace(hook, relocations=(replace(hook.relocations[0], kind="abs64"),)),
                     replace(hook, relocations=(replace(hook.relocations[0], target=0x7FFE0320),)),
                     replace(hook, relocations=hook.relocations * 2))
        for bad in mutations:
            with self.subTest(hook=bad), self.assertRaises(tool.PEExtensionError):
                self.hook_build((bad,), (0x1001,))
        with self.assertRaisesRegex(tool.PEExtensionError, "overlapping hook spans"):
            self.hook_build((hook, hook), (0x1001,))
        with self.assertRaises(tool.PEExtensionError):
            self.hook_build((replace(hook, offset=0x600, rva=0x3000, va=0x403000,
                                     old=synthetic_pe()[0x600:0x607]),), ())

    def test_hook_without_displaced_relocation_preserves_original_directory_copy(self):
        hook = self.hook(0x1020, size=8)
        result = self.hook_build((hook,), ())
        self.assertEqual(result.metadata["removed_highlow"], [])
        self.assertFalse(result.metadata["relocation_directory_merged"])
        memory, _, _, directory = independent_image(result.image)
        self.assertEqual(memory[directory[0]:directory[0] + 16], synthetic_pe()[0x600:0x610])

    def test_public_entry_does_not_accept_fixture_or_unknown_original(self):
        with self.assertRaisesRegex(tool.PEExtensionError, "original SHA"):
            tool.extension_code_va(synthetic_pe())
        with self.assertRaisesRegex(tool.PEExtensionError, "original SHA"):
            tool.extend_combined_candidate(synthetic_pe(), synthetic_pe(), expected_candidate_sha256=digest(synthetic_pe()),
                expected_patcher_sha256=digest(tool.PATCHER.read_bytes()), stage="fake", resolution="800x600",
                code=b"\xC3", code_va=0x404000, relocations=())

    @unittest.skipUnless(ORIGINAL.exists(), "known user-owned original unavailable; no binary fixture is shipped")
    def test_actual_original_combined_recipes_and_existing_candidate_read_only(self):
        import patch_clash95_hd as patcher
        original = ORIGINAL.read_bytes()
        self.assertEqual(digest(original), tool.ORIGINAL_SHA256)
        base = tool.extension_code_va(original)
        self.assertEqual(base, 0x562000)
        stage = patcher.DEFAULT_STAGE + "-combinedui-validation"
        patcher_sha = digest(tool.PATCHER.read_bytes())
        for resolution in ("800x600", "1024x768", "802x602"):
            patches = patcher.select_patches_for(stage, patcher.parse_resolution(resolution))
            candidate = bytearray(original)
            for patch in patches:
                self.assertEqual(candidate[patch.offset:patch.offset + len(patch.old)], patch.old)
                candidate[patch.offset:patch.offset + len(patch.new)] = patch.new
            candidate = bytes(candidate)
            if resolution == "800x600":
                self.assertEqual(digest(candidate), COMBINED800_SHA)
                if EXISTING_CANDIDATE.exists():
                    self.assertEqual(EXISTING_CANDIDATE.read_bytes(), candidate)
            # Synthetic six-kilobyte payload, explicitly not the live emitter.
            code = bytearray([0x90] * 6003)
            struct.pack_into("<I", code, 1, 0x5202E4)
            record = tool.CodeRelocation(1, "abs32", 0x5202E4, "fixture game-data global")
            kwargs = dict(expected_candidate_sha256=digest(candidate), expected_patcher_sha256=patcher_sha,
                          stage=stage, resolution=resolution, code=bytes(code), code_va=base, relocations=(record,))
            result = tool.extend_combined_candidate(original, candidate, **kwargs)
            self.assertEqual(result.metadata["old_highlow_count"], 32435)
            self.assertEqual(result.metadata["new_highlow_count"], 1)
            self.assertEqual(result.edits[-2].offset, 0x280)
            self.assertEqual(result.image[0x2A8:0x400], original[0x2A8:0x400])
            before, old_sections, old_fixups, _ = independent_image(candidate)
            after, _, new_fixups, _ = independent_image(result.image)
            for delta in (0x100000, -0x100000):
                old_rebased, new_rebased = rebase(before, old_fixups, delta), rebase(after, new_fixups, delta)
                for _, rva, size, *_ in old_sections:
                    self.assertEqual(old_rebased[rva:rva + size], new_rebased[rva:rva + size])
            for changed in ({"expected_candidate_sha256": "0" * 64}, {"expected_patcher_sha256": "0" * 64},
                            {"stage": patcher.DEFAULT_STAGE}, {"resolution": "1280x720"}):
                with self.assertRaises(tool.PEExtensionError):
                    tool.extend_combined_candidate(original, candidate, **(kwargs | changed))
            for offset in (0x300, 0x401):
                changed_candidate = bytearray(candidate)
                changed_candidate[offset] ^= 1
                with self.assertRaises(tool.PEExtensionError):
                    tool.extend_combined_candidate(original, bytes(changed_candidate),
                        **(kwargs | {"expected_candidate_sha256": digest(changed_candidate)}))
        self.assertEqual(ORIGINAL.read_bytes(), original)

    @unittest.skipUnless(ORIGINAL.exists(), "known user-owned original unavailable; no binary fixture is shipped")
    def test_actual_redraw_hook_displaces_4187a2_and_incremental_eight_bytes_displace_none(self):
        import patch_clash95_hd as patcher
        original = ORIGINAL.read_bytes()
        self.assertEqual(digest(original), tool.ORIGINAL_SHA256)
        stage = patcher.DEFAULT_STAGE + "-combinedui-validation"
        candidate = patcher.apply_patches(original, patcher.select_patches_for(stage, patcher.PROFILE_800))
        pe = tool.inspect_pe(candidate)
        _, old_locations = tool._old_relocations(candidate, pe)
        self.assertIn(0x187A2, old_locations)
        self.assertFalse(any(location < 0x18A98 and 0x18A90 < location + 4 for location in old_locations))
        base = tool.extension_code_va(original)
        hooks = []
        for va, expected in ((0x4187A0, bytes.fromhex("833d9069520000")),
                             (0x418A90, bytes.fromhex("535156575583ec08"))):
            rva = va - pe.image_base
            offset = pe.file_offset(rva, len(expected))
            self.assertEqual(candidate[offset:offset + len(expected)], expected)
            new = b"\xE9" + struct.pack("<i", base - (va + 5)) + b"\x90" * (len(expected) - 5)
            hooks.append(tool.HookPatch(offset, rva, va, expected, new,
                                       "source-verified span fixture, not a runnable hook recipe",
                                       (tool.CodeRelocation(1, "rel32", base, "fixture transfer"),)))
        kwargs = dict(expected_candidate_sha256=COMBINED800_SHA,
                      expected_patcher_sha256=digest(tool.PATCHER.read_bytes()), stage=stage,
                      validation_stage="synthetic-native-hook-validation", resolution="800x600",
                      code=b"\xC3" + bytes(6000), code_va=base, relocations=(), hooks=tuple(hooks),
                      removed_highlow_rvas=(0x187A2,))
        result = tool.extend_combined_candidate_with_hooks(original, candidate, **kwargs)
        self.assertEqual(result.metadata["base_stage"], stage)
        self.assertEqual(result.metadata["stage"], "synthetic-native-hook-validation")
        self.assertEqual(result.metadata["removed_highlow"], [
            {"rva": 0x187A2, "va": 0x4187A2, "offset": 0x17BA2, "old_hex": "90695200"}])
        self.assertEqual(result.metadata["retained_highlow_count"], 32434)
        before, old_sections, old_fixups, old_directory = independent_image(candidate)
        after, _, new_fixups, _ = independent_image(result.image)
        self.assertEqual(new_fixups, sorted(set(old_fixups) - {0x187A2}))
        old_reloc = pe.file_offset(*old_directory)
        self.assertEqual(result.image[old_reloc:old_reloc + old_directory[1]], candidate[old_reloc:old_reloc + old_directory[1]])
        for delta in (0x100000, -0x100000):
            expected = rebase(before, old_fixups, delta)
            for hook in hooks:
                expected[hook.rva:hook.rva + len(hook.new)] = hook.new
            observed = rebase(after, new_fixups, delta)
            for _, rva, size, *_ in old_sections:
                self.assertEqual(observed[rva:rva + size], expected[rva:rva + size])
        for changes in ({"removed_highlow_rvas": ()}, {"removed_highlow_rvas": (0x187A2, 0x18A9A)},
                        {"validation_stage": stage}, {"validation_stage": "stable"},
                        {"validation_stage": ""}, {"hooks": ()}):
            with self.assertRaises(tool.PEExtensionError):
                tool.extend_combined_candidate_with_hooks(original, candidate, **(kwargs | changes))
        self.assertFalse(result.installation_ready)
        self.assertEqual(ORIGINAL.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
