#!/usr/bin/env python3
"""PE/RX/RW binding fixtures and Windows SEC_IMAGE admission without execution.

The optional Windows checks write exclusive temporary copies under C:/ClashTests,
create a read-only image section, and close both kernel handles. They never map
a view, create a process, call an entry point, or alter retained failed evidence.
"""
from __future__ import annotations

from dataclasses import replace, FrozenInstanceError
import hashlib
import ctypes
from ctypes import wintypes
import os
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.patcher import pe_modal_extension as tool
from src.patcher import pe_extension as pe
from test_pe_extension import independent_image, rebase

ORIGINAL = Path("C:/Clash/clash95.exe")
RESOLUTIONS = ("800x600", "1024x768", "1280x720", "1280x960", "1920x1080", "802x602")
PRIVATE_ROOT = Path("C:/ClashTests")
FAILED_CANDIDATE = Path("C:/ClashTests/hd-completion/framed-modal-canvas-v1-1024x768-build-20260906-053000/clash95_modal_canvas_1024x768.exe")
FAILED_SHA256 = "17b48dced0e6e75010df67e93c4feb22ca9545cd380084b9a2c383f2eddf5e1b"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def native_image_section(path):
    """Ask the Windows loader to validate layout, without executing image code."""
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateFileW.argtypes = (wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                                  ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE)
    kernel.CreateFileW.restype = wintypes.HANDLE
    kernel.CreateFileMappingW.argtypes = (wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD,
                                         wintypes.DWORD, wintypes.DWORD, wintypes.LPCWSTR)
    kernel.CreateFileMappingW.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
    kernel.CloseHandle.restype = wintypes.BOOL
    handle = kernel.CreateFileW(str(path), 0x80000000, 5, None, 3, 0x80, None)
    if handle == ctypes.c_void_p(-1).value:
        raise ctypes.WinError(ctypes.get_last_error())
    section = None
    try:
        ctypes.set_last_error(0)
        section = kernel.CreateFileMappingW(handle, None, 0x01000002, 0, 0, None)  # SEC_IMAGE | PAGE_READONLY
        error = ctypes.get_last_error() if not section else 0
        return {"accepted": bool(section), "error": error, "view_mapped": False, "process_started": False}
    finally:
        section_closed = not section or kernel.CloseHandle(section)
        file_closed = kernel.CloseHandle(handle)
        if not section_closed or not file_closed:
            raise OSError("SEC_IMAGE fixture failed to close every owned kernel handle")


def independent_section_adjacency(image):
    """Parse literal PE fields without relying on the allocator's permissive parser."""
    nt = struct.unpack_from("<I", image, 60)[0]
    count = struct.unpack_from("<H", image, nt + 6)[0]
    optional = nt + 24
    table = optional + struct.unpack_from("<H", image, nt + 20)[0]
    alignment = struct.unpack_from("<I", image, optional + 32)[0]
    headers = struct.unpack_from("<I", image, optional + 60)[0]
    previous_end = (headers + alignment - 1) // alignment * alignment
    rows = []
    for index in range(count):
        entry = table + 40 * index
        name, virtual_size, rva, raw_size = struct.unpack_from("<8sIII", image, entry)
        end = (rva + max(virtual_size, raw_size) + alignment - 1) // alignment * alignment
        rows.append(dict(name=name.rstrip(b"\0"), rva=rva, virtual_size=virtual_size,
                         expected_rva=previous_end, aligned_end=end, header=entry))
        previous_end = end
    return rows


def synthetic_framed():
    """Independent eight-section PE with zero header slots at 680/720."""
    data = bytearray(0x1200)
    data[:2] = b"MZ"
    struct.pack_into("<I", data, 60, 0x70)
    data[0x70:0x74] = b"PE\0\0"
    struct.pack_into("<HHIIIHH", data, 0x74, 0x14C, 8, 123456, 0, 0, 224, 0x182)
    opt = 0x88
    struct.pack_into("<H", data, opt, 0x10B)
    struct.pack_into("<I", data, opt + 4, 0x400)
    struct.pack_into("<III", data, opt + 28, 0x400000, 4096, 512)
    struct.pack_into("<II", data, opt + 56, 0x9000, 1024)
    struct.pack_into("<I", data, opt + 92, 16)
    struct.pack_into("<II", data, opt + 136, 0x7000, 16)
    for index, (name, rva, size, raw, flags) in enumerate((
        (b".text", 0x1000, 512, 0x400, 0x60000020),
        (b".bss", 0x2000, 4096, 0, 0xC0000080),
        (b".rdata", 0x3000, 512, 0x600, 0x40000040),
        (b".data", 0x4000, 512, 0x800, 0xC0000040),
        (b".idata", 0x5000, 512, 0xA00, 0xC0000040),
        (b".debug", 0x6000, 512, 0xC00, 0x40000040),
        (b".reloc", 0x7000, 512, 0xE00, 0x42000040),
        (b".hdcode", 0x8000, 512, 0x1000, 0x60000020),
    )):
        struct.pack_into("<8sIIIIIIHHI", data, opt + 224 + 40 * index,
                         name, 0, rva, size, raw, 0, 0, 0, 0, flags)
    data[0x400:0x600] = b"\x90" * 512
    for offset, target in ((1, 0x402008), (9, 0x401100), (17, 0x401008)):
        struct.pack_into("<I", data, 0x400 + offset, target)
    data[0x400] = 0xB8
    struct.pack_into("<II4H", data, 0xE00, 0x1000, 16, 0x3001, 0x3009, 0x3011, 0)
    return bytes(data)


def payload(base, state):
    code = bytearray(b"\x90" * 6003)
    records = (
        pe.CodeRelocation(1, "abs32", state, "RW state first byte"),
        pe.CodeRelocation(8, "abs32", state + 4095, "RW state final byte"),
        pe.CodeRelocation(4095, "abs32", base + 5500, "cross-page internal code pointer"),
        pe.CodeRelocation(24, "abs32", 0x402008, "existing mapped BSS"),
        pe.CodeRelocation(5002, "rel32", 0x401008, "native relative call"),
    )
    for r in records:
        struct.pack_into("<I", code, r.offset,
                         r.target if r.kind == "abs32" else (r.target - base - r.offset - 4) & 0xFFFFFFFF)
    return bytes(code), records


def jump_hook(candidate, va, target):
    image = pe.inspect_pe(candidate)
    off = image.file_offset(va - image.image_base, 5)
    return pe.HookPatch(off, va - image.image_base, va, candidate[off:off+5],
        b"\xe9" + struct.pack("<i", target - va - 5), "synthetic explicit modal hook",
        (pe.CodeRelocation(1, "rel32", target, "modal entry"),))


class ModalFormatTests(unittest.TestCase):
    def args(self, candidate=None):
        candidate = synthetic_framed() if candidate is None else candidate
        base = pe.inspect_pe(candidate)
        va = base.image_base + base.image_size
        code, relocs = payload(va, va + 0x20000)
        return dict(code=code, code_va=va, state_va=va+0x20000, relocations=relocs,
                    hooks=(jump_hook(candidate, 0x401040, va),), removed_highlow_rvas=(),
                    binding={"fixture": "synthetic PE; no runtime proof"})

    def build(self, candidate=None, **overrides):
        candidate = synthetic_framed() if candidate is None else candidate
        return tool._extend_verified_image(candidate, **(self.args(candidate) | overrides))

    def test_exact_rx_rw_layout_zero_state_and_immutable_replay_preservation(self):
        before = synthetic_framed()
        result = self.build()
        memory, sections, fixups, directory = independent_image(result.image)
        old_memory, old_sections, old_fixups, _ = independent_image(before)
        self.assertEqual(sections[:-2], old_sections)
        self.assertEqual(sections[-2][0], b".hdmodal")
        self.assertEqual(sections[-1][0], b".hdstate")
        self.assertEqual(sections[-2][-1], 0x60000020)
        self.assertEqual(sections[-1][-1], 0xC0000040)
        self.assertFalse(sections[-2][-1] & 0x80000000)
        self.assertFalse(sections[-1][-1] & 0x20000000)
        self.assertEqual(sections[-1][1] - sections[-2][1], 0x20000)
        self.assertEqual(sections[-1][2], 4096)
        self.assertEqual(memory[sections[-1][1]:sections[-1][1]+4096], bytes(4096))
        self.assertEqual(result.image[-4096:], bytes(4096))
        self.assertEqual(result.image[768:1024], before[768:1024])
        self.assertEqual(result.image[0xE00:0xF00], before[0xE00:0xF00])
        self.assertEqual(fixups, sorted(old_fixups + [0x9001, 0x9008, 0x9018, 0x9FFF]))
        self.assertEqual(struct.unpack_from("<I", result.image, 0x88 + 8)[0], 4096)
        self.assertEqual(directory[0], 0x9000 + 6004)
        reconstructed, touched = bytearray(before), set()
        for edit in result.edits:
            self.assertIsInstance(edit.old, bytes)
            self.assertIsInstance(edit.new, bytes)
            self.assertEqual(reconstructed[edit.offset:edit.offset+len(edit.old)], edit.old)
            reconstructed[edit.offset:edit.offset+len(edit.old)] = edit.new
            touched.update(range(edit.offset, edit.offset + len(edit.old)))
            self.assertEqual(edit.va, 0x400000 + edit.rva)
        self.assertEqual(bytes(reconstructed), result.image)
        self.assertTrue(all(a == result.image[i] for i, a in enumerate(before) if i not in touched))
        with self.assertRaises(FrozenInstanceError):
            result.edits[0].offset = 0
        self.assertFalse(result.installation_ready)
        for field in ("installation_ready", "runtime_executed", "manual_input_proof", "promotion_ready"):
            self.assertIs(result.metadata[field], False)
        self.assertEqual(result.metadata["output_sha256"], sha(result.image))
        layout = independent_section_adjacency(result.image)
        self.assertEqual(layout[-2]["virtual_size"], tool.CODE_RESERVATION)
        self.assertTrue(all(row["rva"] == row["expected_rva"] for row in layout), layout)

    def test_short_rx_payload_still_reserves_adjacent_loader_extent(self):
        result = self.build()
        layout = independent_section_adjacency(result.image)
        self.assertLess(result.metadata["code_raw_bytes"], tool.CODE_RESERVATION)
        self.assertEqual(layout[-2]["virtual_size"], tool.CODE_RESERVATION)
        self.assertEqual(layout[-2]["aligned_end"], layout[-1]["rva"])
        broken = bytearray(result.image)
        struct.pack_into("<I", broken, layout[-2]["header"] + 8, result.metadata["code_raw_bytes"])
        # The old permissive parser admitted the nonoverlapping virtual gap.
        pe.inspect_pe(bytes(broken))
        old_layout = independent_section_adjacency(broken)
        self.assertLess(old_layout[-2]["aligned_end"], old_layout[-1]["rva"])

    def test_independent_rebase_state_code_existing_fields_and_rel32(self):
        result = self.build()
        memory, _, fields, _ = independent_image(result.image)
        old_memory, old_sections, old_fields, _ = independent_image(synthetic_framed())
        for delta in (-0x100000, 0x2100000):
            rebased = rebase(memory, fields, delta)
            old_rebased = rebase(old_memory, old_fields, delta)
            for _, rva, size, *_ in old_sections:
                # Only the declared five-byte hook differs in old memory.
                if rva == 0x1000:
                    self.assertEqual(rebased[rva:rva+64], old_rebased[rva:rva+64])
                    self.assertEqual(rebased[rva+69:rva+size], old_rebased[rva+69:rva+size])
                else:
                    self.assertEqual(rebased[rva:rva+size], old_rebased[rva:rva+size])
            for r in self.args()["relocations"]:
                actual = struct.unpack_from("<I", rebased, 0x9000+r.offset)[0]
                expected = (r.target+delta) & 0xFFFFFFFF if r.kind == "abs32" else struct.unpack_from("<I", memory, 0x9000+r.offset)[0]
                self.assertEqual(actual, expected)
            hook = self.args()["hooks"][0]
            displacement = struct.unpack_from("<i", rebased, hook.rva+1)[0]
            self.assertEqual(hook.va+delta+5+displacement, self.args()["code_va"]+delta)
            self.assertEqual(rebased[0x29000:0x2A000], bytes(4096))

    def test_precise_displaced_highlow_and_new_hook_state_operand(self):
        candidate = synthetic_framed()
        args = self.args()
        first = jump_hook(candidate, 0x401000, args["code_va"])
        second = pe.HookPatch(0x480, 0x1080, 0x401080, candidate[0x480:0x485],
            b"\xb8"+struct.pack("<I", args["state_va"]), "explicit state operand",
            (pe.CodeRelocation(1, "abs32", args["state_va"], "state"),))
        result = self.build(hooks=(first, second), removed_highlow_rvas=(0x1001,))
        _, _, fields, _ = independent_image(result.image)
        self.assertNotIn(0x1001, fields)
        self.assertIn(0x1081, fields)
        self.assertIn(0x1009, fields)
        self.assertIn(0x1011, fields)
        self.assertEqual(result.image[0xE00:0xE10], candidate[0xE00:0xE10])
        for removals in ((), (0x1009,), (0x1001, 0x1009), (0x1001, 0x1001)):
            with self.subTest(removals=removals), self.assertRaises(pe.PEExtensionError):
                self.build(hooks=(first,), removed_highlow_rvas=removals)
        partial = replace(first, old=first.old[:4], new=first.new[:4], relocations=())
        with self.assertRaisesRegex(pe.PEExtensionError, "partially overlaps"):
            self.build(hooks=(partial,), removed_highlow_rvas=(0x1001,))

    def test_header_flags_layout_and_state_corruption_rejected(self):
        cases = ((680, b"X"), (720, b"X"), (640, b".hdmodal"),
                 (640+36, struct.pack("<I", 0xE0000020)),
                 (0x74, struct.pack("<H", 0x8664)),
                 (0x88+56, struct.pack("<I", 0xA000)),
                 (640+20, struct.pack("<I", 0xE00)),
                 (0x88+136, struct.pack("<I", 0x7001)))
        for off, value in cases:
            data = bytearray(synthetic_framed()); data[off:off+len(value)] = value
            with self.subTest(offset=off, value=value), self.assertRaises(pe.PEExtensionError):
                tool._extend_verified_image(bytes(data), **self.args())
        for state in (bytes(4095), bytes(4097), bytes(4095)+b"X", bytearray(4096), None):
            with self.subTest(state_type=type(state)), self.assertRaises(pe.PEExtensionError):
                self.build(state=state)
        for options in (dict(code_va=True), dict(code_va=0x40A000), dict(state_va=0x42A000),
                        dict(state_va=True), dict(code=b""), dict(code=bytearray(30)), dict(hooks=()),
                        dict(hooks=iter(self.args()["hooks"])), dict(relocations=None),
                        dict(removed_highlow_rvas=iter(()))):
            with self.subTest(options=options), self.assertRaises(pe.PEExtensionError):
                self.build(**options)

    def test_unmapped_gap_state_end_and_invalid_relative_target_fail(self):
        args = self.args()
        targets = (("abs32", args["code_va"]+len(args["code"])),
                   ("abs32", args["state_va"]-1), ("abs32", args["state_va"]+4096),
                   ("rel32", args["state_va"]), ("rel32", 0x402008))
        for kind, target in targets:
            code = bytearray(args["code"])
            struct.pack_into("<I", code, 1, target if kind == "abs32" else (target-args["code_va"]-5)&0xFFFFFFFF)
            record = pe.CodeRelocation(1, kind, target, "negative target")
            with self.subTest(kind=kind, target=target), self.assertRaisesRegex(pe.PEExtensionError, "target"):
                self.build(code=bytes(code), relocations=(record,))
            hook = replace(args["hooks"][0], new=b"\xb8"+struct.pack("<I", target if kind == "abs32" else (target-0x401045)&0xFFFFFFFF),
                relocations=(pe.CodeRelocation(1, kind, target, "negative hook target"),))
            with self.assertRaises(pe.PEExtensionError):
                self.build(hooks=(hook,))

    def test_bad_relocation_values_overlap_kinds_offsets_and_hooks_rejected(self):
        args = self.args(); record = args["relocations"][0]
        bad = ((replace(record, offset=-1),), (replace(record, offset=len(args["code"])-3),),
               (replace(record, target=record.target+4),), (replace(record, target=True),),
               (replace(record, kind="HIGHLOW"),), (replace(record, purpose=""),),
               (record, record), (object(),))
        for records in bad:
            with self.subTest(records=records), self.assertRaises(pe.PEExtensionError):
                self.build(relocations=records)
        hook = args["hooks"][0]
        for hooks in ((replace(hook, old=b"X"*5),), (replace(hook, offset=hook.offset+1),),
                      (replace(hook, va=hook.va+1),), (hook, hook),
                      (replace(hook, relocations=(replace(hook.relocations[0], target=hook.va),)),),
                      (replace(hook, relocations=hook.relocations*2),),
                      (replace(hook, rva=0x7000, va=0x407000, offset=0xE00, old=synthetic_framed()[0xE00:0xE05]),)):
            with self.subTest(hooks=hooks), self.assertRaises(pe.PEExtensionError):
                self.build(hooks=hooks)

    def test_code_and_relocation_combined_reservation_limit(self):
        # Exact capacity is allowed; one additional code byte requiring another
        # aligned raw page must fail even when code alone is under 128 KiB.
        old_table, _ = pe._old_relocations(synthetic_framed(), pe.inspect_pe(synthetic_framed()))
        capacity = 0x20000-len(old_table)
        accepted = self.build(code=b"\x90"*capacity, relocations=())
        self.assertEqual(accepted.metadata["code_raw_bytes"], 0x20000)
        for length in (capacity+1, 0x20000, 0x20001):
            with self.subTest(length=length), self.assertRaisesRegex(pe.PEExtensionError, "128 KiB"):
                self.build(code=b"\x90"*length, relocations=())


@unittest.skipUnless(ORIGINAL.is_file(), "requires read-only user-owned original")
class ModalBindingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = ORIGINAL.read_bytes()
        cls.bases = {(res, flag): tool._reconstruct(cls.original, res, flag)[0]
                     for res in RESOLUTIONS for flag in (False, True)}

    def args(self, resolution="1024x768", flag=True):
        image = self.bases[resolution, flag]
        base = pe.inspect_pe(image)
        code_va = base.image_base+base.image_size
        code, records = payload(code_va, code_va+0x20000)
        return dict(expected_candidate_sha256=sha(image), resolution=resolution, minimap_viewport=flag,
                    validation_stage=tool.STAGE, code=code, code_va=code_va, state_va=code_va+0x20000,
                    relocations=records, hooks=(jump_hook(image, 0x422180, code_va),), removed_highlow_rvas=())

    def test_six_resolutions_both_minimap_profiles_whole_binding_and_preservation(self):
        original_sha = sha(self.original)
        for (res, flag), image in self.bases.items():
            with self.subTest(resolution=res, minimap=flag):
                result = tool.extend_framed_candidate_with_modal(self.original, image, **self.args(res, flag))
                before = pe.inspect_pe(image); after = pe.inspect_pe(result.image)
                self.assertEqual(after.sections[:-2], before.sections)
                self.assertEqual(after.sections[-1].rva, before.image_size+0x20000)
                self.assertEqual(after.image_size, before.image_size+0x21000)
                self.assertEqual(len(result.metadata["hooks"]), 1)
                self.assertEqual(result.metadata["original_hook_spans"][0]["original_hex"], "5351525657")
                self.assertEqual(result.metadata["base_stage"], tool.BASE_STAGE)
                self.assertEqual(result.metadata["stage"], tool.STAGE)
                self.assertIs(result.metadata["minimap_viewport"], flag)
                self.assertEqual(result.metadata["source_sha256"]["src/patcher/pe_extension.py"], tool.PINNED_SOURCES["src/patcher/pe_extension.py"])
                self.assertEqual(result.image[768:1024], image[768:1024])
                # Preserve complete old .hdcode including its relocation bytes.
                section = before.sections[-1]
                self.assertEqual(result.image[section.raw_offset:section.raw_offset+section.raw_size],
                                 image[section.raw_offset:section.raw_offset+section.raw_size])
        self.assertEqual(sha(ORIGINAL.read_bytes()), original_sha)

    def test_bad_original_hash_entire_candidate_resolution_minimap_stage(self):
        image = self.bases["1024x768", True]
        args = self.args()
        wrong = bytearray(image); wrong[-1] ^= 1
        cases = ((self.original, bytes(wrong), args | dict(expected_candidate_sha256=sha(wrong))),
                 (self.original[:-1], image, args),
                 (self.original, image, args | dict(expected_candidate_sha256="0"*64)),
                 (self.original, image, args | dict(resolution="800x600")),
                 (self.original, image, args | dict(resolution="01024x768")),
                 (self.original, image, args | dict(minimap_viewport=False)),
                 (self.original, image, args | dict(minimap_viewport=1)),
                 (self.original, image, args | dict(validation_stage=tool.BASE_STAGE)),
                 (self.original, image, args | dict(validation_stage="unreviewed-validation")))
        for original, candidate, opts in cases:
            with self.subTest(resolution=opts["resolution"], stage=opts["validation_stage"]), self.assertRaises(ValueError):
                tool.extend_framed_candidate_with_modal(original, candidate, **opts)

    def test_source_tamper_and_arbitrary_paths_fail_without_writes(self):
        real_read = Path.read_bytes
        for name in ("tools/build_framed_candidate.py", "src/patcher/pe_extension.py",
                     "src/patcher/patch_clash95_hd.py", "src/patcher/framed_minimap.py"):
            def corrupt(path, *, selected=ROOT/name):
                data = real_read(path)
                return data+b"\n# tamper\n" if path == selected else data
            with self.subTest(name=name), patch.object(Path, "read_bytes", corrupt), self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
                tool.extend_framed_candidate_with_modal(self.original, self.bases["1024x768", True], **self.args())
        with self.assertRaisesRegex(ValueError, "source path"):
            tool._source("../outside.py", "0"*64)
        with self.assertRaises(TypeError):
            tool.extend_framed_candidate_with_modal(self.original, self.bases["1024x768", True],
                                                   **self.args(), output=Path("C:/Clash/clash95.exe"))

    def test_fresh_binding_ignores_poisoned_imported_builder_and_restores_namespace(self):
        import build_framed_candidate as old
        image = self.bases["1024x768", True]
        wrong = bytearray(image); wrong[0x400] ^= 1; wrong = bytes(wrong)
        path_before = list(sys.path)
        names_before = {name for name in sys.modules if name.startswith("_clash95_modal_binding_")}
        with patch.object(old, "build_candidate", return_value=(wrong, {}, "")), patch.object(old.recipe, "canonical_candidate", side_effect=AssertionError("stale module reused")):
            with self.assertRaisesRegex(ValueError, "entire canonical framed"):
                tool.extend_framed_candidate_with_modal(self.original, wrong,
                    **(self.args() | dict(expected_candidate_sha256=sha(wrong))))
            result = tool.extend_framed_candidate_with_modal(self.original, image, **self.args())
            self.assertEqual(result.metadata["input_sha256"], sha(image))
        self.assertEqual(sys.path, path_before)
        self.assertEqual({name for name in sys.modules if name.startswith("_clash95_modal_binding_")}, names_before)

    def test_old_hdcode_cannot_be_overwritten_by_modal_hook(self):
        image = self.bases["1024x768", True]; base = pe.inspect_pe(image)
        hook = jump_hook(image, base.image_base+base.sections[-1].rva, self.args()["code_va"])
        with self.assertRaisesRegex(ValueError, "file-backed"):
            tool.extend_framed_candidate_with_modal(self.original, image, **(self.args() | dict(hooks=(hook,))))

    def test_actual_frozen_modal_bundle_all_profiles_and_exact_legacy_entries(self):
        from src.patcher import framed_modal_canvas as canvas
        for (res, flag), candidate in self.bases.items():
            with self.subTest(resolution=res, minimap=flag):
                args = self.args(res, flag)
                width, height = map(int, res.split("x"))
                bundle = canvas.emit_modal_canvas(self.original, candidate, base_va=args["code_va"],
                    state_va=args["state_va"], width=width, height=height)
                args.update(code=bundle.code, relocations=bundle.relocations, hooks=bundle.hook_sites)
                result = tool.extend_framed_candidate_with_modal(self.original, candidate, **args)
                layout = independent_section_adjacency(result.image)
                self.assertEqual(layout[-2]["virtual_size"], tool.CODE_RESERVATION)
                self.assertTrue(all(row["rva"] == row["expected_rva"] for row in layout), layout)
                if os.name == "nt" and PRIVATE_ROOT.is_dir():
                    # These fresh copies exist only for nonexecuting loader
                    # admission. Verify cleanup stays in the explicitly named root.
                    with tempfile.TemporaryDirectory(prefix="pe-modal-sec-image-", dir=PRIVATE_ROOT) as directory:
                        private = Path(directory).resolve()
                        self.assertTrue(private.is_relative_to(PRIVATE_ROOT.resolve()))
                        path = private / f"modal-{res}-minimap{int(flag)}.exe"
                        with path.open("xb") as stream:
                            stream.write(result.image)
                        self.assertEqual(sha(path.read_bytes()), sha(result.image))
                        admitted = native_image_section(path)
                        self.assertTrue(admitted["accepted"], {"resolution": res, "minimap": flag, **admitted})
                        self.assertFalse(admitted["view_mapped"])
                        self.assertFalse(admitted["process_started"])
                entries = result.metadata["authenticated_legacy_continuations"]
                self.assertEqual({row["target"] for row in entries},
                    {0x51B6D6, 0x513175 if res == "800x600" else 0x51BC26})
                self.assertEqual(len(result.metadata["hooks"]), 6)
                self.assertEqual(len(result.metadata["relocations"]), len(bundle.relocations))
                old_memory, old_sections, _, _ = independent_image(candidate)
                memory, sections, fixups, _ = independent_image(result.image)
                self.assertEqual(sections[:-2], old_sections)
                for row in entries:
                    source = bytes.fromhex(row["framed_hex"])
                    self.assertEqual(candidate[row["offset"]:row["offset"]+len(source)], source)
                    self.assertEqual(sha(source), row["framed_sha256"])
                    # The hooked first six bytes change; the source-bound
                    # continuation and all existing section flags stay exact.
                    self.assertEqual(result.image[row["offset"]+6:row["offset"]+len(source)], source[6:])
                for delta in (-0x100000, 0x2100000):
                    rebased = rebase(memory, fixups, delta)
                    for record in bundle.relocations:
                        field = args["code_va"]-0x400000+record.offset
                        actual = struct.unpack_from("<I", rebased, field)[0]
                        if record.kind == "abs32":
                            self.assertEqual(actual, (record.target+delta)&0xFFFFFFFF)
                        else:
                            signed = struct.unpack_from("<i", rebased, field)[0]
                            self.assertEqual((args["code_va"]+delta+record.offset+4+signed)&0xFFFFFFFF,
                                             (record.target+delta)&0xFFFFFFFF)

    def test_legacy_permissions_are_exact_bound_continuations_not_rw_exemption(self):
        for res in ("800x600", "1024x768"):
            image = self.bases[res, True]; args = self.args(res, True)
            allowed = (0x51B6D6, 0x513175 if res == "800x600" else 0x51BC26)
            targets = allowed + tuple(address+delta for address in allowed for delta in (-1,1)) + (
                0x51B6D0, 0x51D4C0, 0x5202E0, args["state_va"],
                0x51BC26 if res == "800x600" else 0x513175)
            for target in targets:
                with self.subTest(resolution=res, target=hex(target)):
                    code = bytearray(args["code"])
                    struct.pack_into("<I", code, 5002, (target-args["code_va"]-5006)&0xFFFFFFFF)
                    records = args["relocations"][:-1] + (pe.CodeRelocation(5002,"rel32",target,"test continuation"),)
                    opts = args | dict(code=bytes(code), relocations=records)
                    if target in allowed:
                        result = tool.extend_framed_candidate_with_modal(self.original, image, **opts)
                        self.assertEqual(result.metadata["relocations"][-1]["target"], target)
                    else:
                        with self.assertRaisesRegex(ValueError,"target"):
                            tool.extend_framed_candidate_with_modal(self.original, image, **opts)

    def test_legacy_original_canonical_span_and_instruction_boundary_are_bound(self):
        image, metadata, _ = tool._reconstruct(self.original, "1024x768", True)
        records = tool._legacy_continuations(self.original, image, metadata)
        for row in records:
            # Corrupt just the first real continuation byte, preserving the
            # rest of the image and supplying its actual changed SHA.
            bad = bytearray(image); bad[row["offset"]+6] ^= 1; bad = bytes(bad)
            with self.assertRaisesRegex(ValueError,"entire canonical framed"):
                tool.extend_framed_candidate_with_modal(self.original, bad,
                    **(self.args() | dict(expected_candidate_sha256=sha(bad))))
            with self.assertRaisesRegex(ValueError,"source bytes differ"):
                tool._legacy_continuations(self.original, bad, metadata)
            changed_rows = [dict(r) for r in metadata["selected_patches"]]
            selected = next(r for r in changed_rows if r["offset"] == row["offset"])
            changed = bytearray.fromhex(selected["new_hex"]); changed[6] ^= 1
            selected["new_hex"] = changed.hex()
            with self.assertRaisesRegex(ValueError,"instruction boundary"):
                tool._legacy_continuations(self.original, bad, metadata | dict(selected_patches=changed_rows))

    def test_only_exact_source_bound_rw_hook_prefix_can_change(self):
        image, metadata, _ = tool._reconstruct(self.original, "1024x768", True)
        rows = tool._legacy_continuations(self.original, image, metadata)
        args = self.args(); base = pe.inspect_pe(image)
        for row in rows:
            old = bytes.fromhex(row["framed_hex"])[:6]
            va = row["entry_va"]
            new = b"\xe9" + struct.pack("<i", args["code_va"]-va-5) + b"\x90"
            hook = pe.HookPatch(row["offset"], va-0x400000, va, old, new, "exact wrapper hook",
                (pe.CodeRelocation(1,"rel32",args["code_va"],"new modal entry"),))
            result = tool.extend_framed_candidate_with_modal(self.original,image,**(args|dict(hooks=(hook,))))
            self.assertEqual(result.image[row["offset"]:row["offset"]+6],new)
            self.assertEqual(pe.inspect_pe(result.image).sections[:-2],base.sections)
            mutations = (replace(hook,old=old[:-1],new=new[:-1]),
                replace(hook,old=old+b"\x61",new=new+b"\x90"), replace(hook,new=b"\xe8"+new[1:]),
                replace(hook,new=new[:-1]+b"\xcc"), replace(hook,offset=hook.offset+1),
                replace(hook,rva=hook.rva+1),replace(hook,purpose=""),
                replace(hook,relocations=()), replace(hook,relocations=hook.relocations*2),
                replace(hook,relocations=(replace(hook.relocations[0],offset=2),)),
                replace(hook,relocations=(replace(hook.relocations[0],kind="abs32"),)))
            for bad in mutations:
                with self.subTest(entry=hex(va),hook=bad), self.assertRaises(pe.PEExtensionError):
                    tool._legacy_hook(bad,row,image,base,args["code_va"],len(args["code"]),())
            with self.assertRaisesRegex(pe.PEExtensionError,"old HIGHLOW"):
                tool._legacy_hook(hook,row,image,base,args["code_va"],len(args["code"]),(hook.rva+1,))
            with self.assertRaisesRegex(pe.PEExtensionError,"overlapping"):
                tool.extend_framed_candidate_with_modal(self.original,image,**(args|dict(hooks=(hook,hook))))
            for target in (0x422020,args["state_va"],args["code_va"]+len(args["code"])):
                bad = replace(hook,new=b"\xe9"+struct.pack("<i",target-va-5)+b"\x90",
                    relocations=(pe.CodeRelocation(1,"rel32",target,"outside new code"),))
                with self.subTest(target=hex(target)),self.assertRaisesRegex(pe.PEExtensionError,"mapped new code"):
                    tool._legacy_hook(bad,row,image,base,args["code_va"],len(args["code"]),())
            for target_va in (va+1,va+6):
                bad = jump_hook(image,target_va,args["code_va"])
                with self.subTest(unknown_rw=hex(target_va)),self.assertRaisesRegex(pe.PEExtensionError,"not executable"):
                    tool.extend_framed_candidate_with_modal(self.original,image,**(args|dict(hooks=(bad,))))


class PreservedLoaderFailureTests(unittest.TestCase):
    @unittest.skipUnless(os.name == "nt" and FAILED_CANDIDATE.is_file(), "preserved Windows loader failure unavailable")
    def test_preserved_invalid_candidate_still_rejects_193_without_changes(self):
        before = FAILED_CANDIDATE.read_bytes()
        self.assertEqual(sha(before), FAILED_SHA256)
        rows = independent_section_adjacency(before)
        self.assertEqual(rows[-2]["virtual_size"], 0x11198)
        self.assertEqual(rows[-1]["rva"] - rows[-1]["expected_rva"], 0xE000)
        admitted = native_image_section(FAILED_CANDIDATE)
        self.assertFalse(admitted["accepted"])
        self.assertEqual(admitted["error"], 193)
        self.assertEqual(sha(FAILED_CANDIDATE.read_bytes()), FAILED_SHA256)


if __name__ == "__main__":
    unittest.main()
