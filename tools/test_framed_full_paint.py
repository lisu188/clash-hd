#!/usr/bin/env python3
"""Execute framed full-paint adapters in a temporary no-window x86 fixture.

The authenticated native prologue/epilogue execute; terrain/UI/presentation
bodies are independent synthetic recorders, never game calls. Original bytes
are read only. No candidate, debugger, input or capture is produced.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.patcher import framed_full_paint as full
from src.patcher import framed_recipe as recipe
from src.patcher import initial_map_paint as initial
from src.patcher import partial_tile_clip as clip
from src.patcher import partial_tile_hooks as hooks
from src.patcher import patch_clash95_hd as patcher
from src.patcher.framed_viewport import FramedViewport
import test_partial_tile_clip as runner
import test_partial_tile_hooks as hook_runner
from test_initial_map_paint import flags, rel32, u32, POST_UI, SAVED_EDI

BASE = runner.BASE
BODY, EDGE, PRESENT, CONVERGED = (BASE + n for n in (0x9000, 0x9400, 0x9800, 0x9C00))
EPILOGUE, OLD_C5, FAILED_PRESENT, SHIM = (BASE + n for n in (0xA000, 0xA400, 0xA800, 0xAC00))
GUARD, UI, PAINT, RESUME = (BASE + n for n in (0xB000, 0xB400, 0xB800, 0xBC00))
FULL_EPILOGUE = bytes.fromhex("83c4185d5f5e5a595bc3")
SIZES = ((800, 600), (1024, 768), (1280, 720), (1280, 960), (1920, 1080), (802, 602))
# Independently generated from the pre-integration source copies, before the
# new framed path. These bind every byte of all three legacy payload layers.
LEGACY = {
 (800,600): ("6fec014cffd2473977214acbc4318c14f2f797f4f0aaf212c288a60a97dddae1", "aad5232d1e71e0e714f9c56badf0929916a73fe3246c6c0d8d657ad17dca3d43", "ec8c6e8fb862a423f0bf024f2c2e4b1c51a2551b6e7e223fcf3e466beedefff9"),
 (1024,768): ("9da275e94ee2a3a95e621892b90629b0010180bb12cdcf5bda0d671f3d9a68a6", "4577c57ae85c2ad20e46640b2cb9db2d0e1ec16773eeb6760603861ef8b019f4", "b1775d3c40b430e0340d0597730ce546e83a73c2c49dfead1d33c4c55ee7494b"),
 (1280,720): ("5e2531a03aa7cb027d79eefaa2f44639494c43f2d2a4b66ada60c1a48c339c54", "3bb9b3e282ad8163143dc7dfd5ad1dea9f8903d2c20ec317adaaa34963c7d07c", "87655323c4786d09ba6a147378cc0d7f9e17b54eb0d8b0422c2f9dd838e5313c"),
 (1280,960): ("fd5ac7cb3306924acf31fca51f177b339f01b5d91ae781cce19744ef31cf2711", "97e152adee5d131cf2dd6ccd2e9378600c1f57f832245f299a288aa6bdf85df0", "bec681da5dd3fd3540676f1aebb5e2737ad4ab18afa86c8dff51e10d012a4d34"),
 (1920,1080): ("1a91fcd9cbde56be3ece0f759e795fa1e18f8a422470ccb181c3f2b92efa56c6", "96b737b78ca527bf107537a722646794be492ebc4ac7c55d7799f396fc6f640c", "ab8bd5fef50cef39e57f4fd05d772538c9fe674b519b79fd8e1c6deb60a8cdcf"),
 (802,602): ("7da9ee699584c75edc6a8a2378fbc6786a21a2da4a137b26a8be1b0ed6f5ff0d", "fb25a0f2fbb08b5ad790a5c8d23f2b888db68ca3f61549e1f240f2168608317c", "403eadc57efa0c866e8adfb025c787768de1123e74219cbdd5f82e748b819565"),
}


def observe(kind, delta=0):
    """Record native entry GPR/flags/SP plus measured surface/render pointers."""
    out = bytearray(hook_runner.recorder(kind, delta)[:-2])
    out += b"\xa1" + u32(runner.SURFACE + 184 + delta) + bytes.fromhex("894728")
    out += b"\xa1" + u32(runner.GLOBAL + 8 + delta) + bytes.fromhex("89472c619d")
    return out


@unittest.skipUnless(runner.ORIGINAL.is_file(), "requires user-owned original for byte verification")
class ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = runner.ORIGINAL.read_bytes()
        cls.cache = {}

    def bundle(self, width=800, height=600):
        key = (width, height)
        if key not in self.cache:
            candidate = recipe.canonical_candidate(self.original, width, height).image
            layout = FramedViewport(width, height)
            result = initial.emit_hook_bundle(self.original, candidate, base_va=BASE,
                                              width=width, height=height, layout=layout)
            self.cache[key] = candidate, result
        return self.cache[key]

    def test_legacy_default_and_explicit_none_match_prior_all_resolution_bytes(self):
        for (w, h), digests in LEGACY.items():
            candidate = patcher.apply_patches(self.original, patcher.select_patches_for(
                hooks.COMBINED_STAGE, patcher.parse_resolution(f"{w}x{h}")))
            for function, expected in zip((clip.emit_map_composition, hooks.emit_hook_bundle,
                                           initial.emit_hook_bundle), digests):
                for kwargs in ({}, {"layout": None}):
                    result = function(self.original, candidate, base_va=BASE, width=w, height=h, **kwargs)
                    self.assertEqual(hashlib.sha256(result.code).hexdigest(), expected)

    def test_all_resolution_hook_contracts_and_complete_relocations(self):
        for w, h in SIZES:
            candidate, bundle = self.bundle(w, h)
            self.assertFalse(bundle.installation_ready)
            self.assertEqual(bundle.initial_contract["stack"]["full_status_plus_to_ready"], 148)
            self.assertEqual(bundle.layout_contract["full_entry_extra_stack_bytes"], 60)
            self.assertEqual(bundle.initial_contract["full_tiles"], [(w-64)//64, (h-32)//64])
            new_sites = {s.name: s for s in bundle.hook_sites}
            self.assertEqual(set(new_sites), {"full_converge", "full_present", "incremental",
                                              "framed_full_entry", "framed_frame_gate", "initial_paint"})
            for name in ("framed_full_entry", "framed_frame_gate"):
                site = new_sites[name]
                self.assertEqual(candidate[site.offset:site.offset+len(site.old_bytes)], site.old_bytes)
                self.assertEqual(site.removed_highlow_vas, ())
                self.assertEqual(site.rva, site.va - 0x400000)
            self.assertEqual(new_sites["framed_full_entry"].old_bytes, bytes.fromhex("53515256575583ec18"))
            offsets = clip.absolute_relocation_offsets(bundle)
            self.assertEqual(len(offsets), len(set(offsets)))
            for r in bundle.relocations:
                actual = struct.unpack_from("<I", bundle.code, r.offset)[0]
                expected = r.target if r.kind == "abs32" else r.target-(BASE+r.offset+4)
                self.assertEqual(actual, expected & 0xFFFFFFFF, r)

    def test_changed_native_entry_or_c5_and_wrong_layout_fail_closed(self):
        candidate, _ = self.bundle()
        for va in (0x418700, 0x418708, 0x4187AF, 0x4187B6, 0x51BE00):
            altered = bytearray(candidate)
            altered[clip.file_offset(candidate, va, 1)] ^= 1
            with self.assertRaises(ValueError):
                initial.emit_hook_bundle(self.original, bytes(altered), base_va=BASE, width=800,
                                         height=600, layout=FramedViewport(800, 600))
        with self.assertRaises(ValueError):
            hooks.emit_hook_bundle(self.original, candidate, base_va=BASE, width=800,
                                   height=600, layout=FramedViewport(1024, 768))


@unittest.skipUnless(os.name == "nt" and runner.CSC.is_file() and runner.ORIGINAL.is_file(),
                     "requires local no-window x86 compiler and original")
class X86Tests(unittest.TestCase):
    bundle = ContractTests.bundle

    @classmethod
    def setUpClass(cls):
        cls.original = runner.ORIGINAL.read_bytes()
        cls.cache = {}
        cls.temp = tempfile.TemporaryDirectory(prefix="clash-framed-full-fixture-")
        cls.exe = Path(cls.temp.name) / "fixture.exe"
        source = runner.CSHARP
        changes = {
            "Save(b,0x15,Output+36);": "Save(b,0x15,Output+36);b.AddRange(new byte[]{0x9c,0x8f,0x05});Imm(b,Output+16);",
            "new int[]{0,4,8,12,20,24,28,32,36}": "new int[]{0,4,8,12,20,24,28,32,36,16}",
            'W(Global+60,Get(c,"turn_sprites",Sprite));':
                'W(Global+60,Get(c,"turn_sprites",Sprite));W(Global+64,Sprite);W(Global+84,Get(c,"nested",0));',
        }
        for anchor, replacement in changes.items():
            if source.count(anchor) != 1:
                raise AssertionError("shared no-window runner contract changed")
            source = source.replace(anchor, replacement)
        path = Path(cls.temp.name) / "fixture.cs"
        path.write_text(source, encoding="utf-8")
        ran = subprocess.run([str(runner.CSC), "/nologo", "/platform:x86", "/optimize+",
                              "/r:System.Web.Extensions.dll", f"/out:{cls.exe}", str(path)],
                             capture_output=True, text=True, timeout=60, creationflags=subprocess.CREATE_NO_WINDOW)
        if ran.returncode:
            raise AssertionError(ran.stdout + ran.stderr)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def execute(self, changes=None, *, width=800, height=600, delta=0, edge=1, present=1,
                guard=None, initial_path=False, gate_only=None, composition=None, present_real=False):
        candidate, bundle = self.bundle(width, height)
        code = bytearray(bundle.code)
        self.assertLess(len(code), 0x8000)
        globals_map = dict(runner.GLOBALS, initial_info_sprites=runner.GLOBAL+64,
                           hook_post_tile_callback=runner.GLOBAL+28, hook_cursor_x=runner.GLOBAL+20)
        transfers = {"framed_native_full_body": BODY, "hook_helper_edge_full_composed": EDGE,
                     "hook_helper_present_map_rect": PRESENT, "hook_resume_full_converge": CONVERGED,
                     "framed_gate_full_present": bundle.entries["hook_full_present"],
                     "framed_gate_native_epilogue": EPILOGUE, "framed_gate_old_c5_fallback": OLD_C5,
                     "hook_native_full_epilogue": EPILOGUE, "hook_resume_full_present": FAILED_PRESENT,
                     "initial_native_ui": UI, "initial_native_full_paint": PAINT,
                     "initial_native_resume": RESUME}
        if guard is not None:
            transfers["framed_full_composition_guard"] = GUARD
        if present_real:
            transfers.update(dirty=EDGE, blit=PRESENT, cursor=CONVERGED)
        for r in bundle.relocations:
            if r.kind == "abs32":
                struct.pack_into("<I", code, r.offset, globals_map.get(r.purpose, r.target)+delta)
            elif r.purpose in transfers:
                struct.pack_into("<I", code, r.offset, (transfers[r.purpose]-(BASE+r.offset+4)) & 0xFFFFFFFF)
        desc = bytearray(candidate[clip.file_offset(candidate, clip.COMMAND_DESCRIPTORS, 322):][:322])
        for i in range(6):
            struct.pack_into("<I", desc, 53*i+12, runner.GLOBAL+36+delta)
            struct.pack_into("<I", desc, 53*i+28, 0x4191F0+delta)

        body = observe(10, delta)
        body += bytes.fromhex("89c5a1") + u32(runner.GLOBAL+delta)  # native MOV EBP,EAX; select map
        body += b"\xa3" + u32(runner.GLOBAL+8+delta)
        # Optional same-thread recursion while the outer table is clipped.
        body += bytes.fromhex("833d") + u32(runner.GLOBAL+84+delta) + b"\0\x0f\x84"
        skip_at = len(body); body += bytes(4)
        body += bytes.fromhex("ff0d") + u32(runner.GLOBAL+84+delta) + bytes.fromhex("b801000000")
        rel32(body, BODY, bundle.entries["hook_framed_full_entry"], 0xE8)
        body += observe(18, delta)
        struct.pack_into("<i", body, skip_at, len(body)-(skip_at+4))
        rel32(body, BODY, bundle.entries["hook_full_converge"])
        converge = observe(13, delta)
        rel32(converge, CONVERGED, bundle.entries["hook_framed_frame_gate"])
        edge_stub = observe(11, delta) + hook_runner.helper_stub(edge, delta, kind=21)
        present_stub = observe(12, delta) + hook_runner.helper_stub(present, delta, kind=22)
        epilogue = observe(14, delta) + FULL_EPILOGUE[:-1] + flags() + b"\xb8" + u32(0x76543210) + b"\xc3"
        old = observe(15, delta)
        rel32(old, OLD_C5, EPILOGUE)
        failed = observe(16, delta)
        rel32(failed, FAILED_PRESENT, EPILOGUE)
        ui = observe(30, delta)
        for opcode, value in zip((0xB8,0xBB,0xB9,0xBA,0xBE,0xBF,0xBD), POST_UI):
            ui += bytes([opcode]) + u32(value)
        ui += flags() + b"\xc3"
        paint = observe(31, delta)
        rel32(paint, PAINT, bundle.entries["hook_framed_full_entry"])
        resume = observe(32, delta) + b"\xc3"
        shim = bytearray(flags())
        if initial_path:
            shim += b"\x68" + u32(SAVED_EDI)
            rel32(shim, SHIM, bundle.entries["hook_initial_paint"])
        elif gate_only is not None:
            shim += full.FULL_ENTRY_OLD + bytes.fromhex("89c5c70424") + u32(gate_only)
            rel32(shim, SHIM, bundle.entries["hook_framed_frame_gate"])
        else:
            entry = "edge_full_composed" if composition is not None else "present_map_rect" if present_real else "hook_framed_full_entry"
            rel32(shim, SHIM, bundle.entries[entry])
        stubs = {BODY: body, EDGE: edge_stub, PRESENT: present_stub, CONVERGED: converge,
                 EPILOGUE: epilogue, OLD_C5: old, FAILED_PRESENT: failed, SHIM: shim,
                 GUARD: hook_runner.helper_stub(guard or 0, delta, kind=20), UI: ui, PAINT: paint, RESUME: resume}
        if composition is not None:
            for name, address, status, kind in (("edge_full", EDGE, edge, 40),
                    ("draw_frame", BODY, composition[0], 41), ("compose_panel", CONVERGED, composition[1], 42),
                    ("present_map_rect", PRESENT, present, 43)):
                offset = bundle.entries[name]-BASE
                code[offset:offset+5] = b"\xe9" + u32(address-(BASE+offset+5))
                stubs[address] = observe(kind,delta) + hook_runner.helper_stub(status,delta,kind=kind+10)
        if present_real:
            stubs[EDGE] = runner.recorder(60,1,delta=delta)
            stubs[PRESENT] = runner.recorder(61,4,delta=delta)
            stubs[CONVERGED] = runner.recorder(62,0,delta=delta)
        case = dict(regs=[1,0x123456,0x654321,29], args=[], entry=SHIM+delta)
        case.update(changes or {})
        if case.get("initial_vtable") == "clipped":
            case["initial_vtable"] = bundle.entries["clipped_vtable"]+delta
        payload = dict(code=code.hex(), width=width, height=height, base=BASE+delta,
                       image_delta=delta, descriptor_bytes=desc.hex(), cases=[case],
                       stubs={str(va+delta): bytes(data).hex() for va,data in stubs.items()})
        ran = subprocess.run([str(self.exe)], input=json.dumps(payload), capture_output=True,
                             text=True, timeout=30, creationflags=subprocess.CREATE_NO_WINDOW)
        self.assertEqual(ran.returncode, 0, ran.stdout+ran.stderr)
        result = json.loads(ran.stdout)[0]
        self.assertEqual(result["state"][4], result["state"][5], "native stack imbalance")
        return result, bundle

    def test_full_entry_clips_before_native_body_and_restores_native_result(self):
        for w,h in SIZES:
            for delta in (0, 0x02000000):
                result,bundle = self.execute(width=w,height=h,delta=delta)
                rows = result["records"]
                self.assertEqual([r[0] for r in rows], [10,11,21,13,12,22,14])
                self.assertEqual(rows[0][10], bundle.entries["clipped_vtable"]+delta)
                self.assertEqual(rows[1][10], clip.MEMORY_VTABLE+delta)
                self.assertEqual(rows[4][1:5], [0,0,w-1,h-1])
                self.assertEqual(result["vtable"], clip.MEMORY_VTABLE+delta)
                self.assertEqual(result["state"][0:4], [0x76543210,0x11223344,0x55667788,0x99AABBCC])
                self.assertEqual(result["state"][6:9], [0x123456,0x654321,29])
                self.assertEqual(result["state"][9] & hook_runner.ARITHMETIC_FLAGS, hook_runner.INITIAL_FLAGS)

    def test_bad_world_or_scroll_rejects_before_native_body_and_table_change(self):
        for w,h in ((800,600),(1024,768),(1920,1080)):
            tx,ty=(w-64)//64,(h-32)//64
            for change in ({"map_width":0},{"map_height":101},{"map_width":tx-1},
                           {"map_height":ty-1},{"scroll_x":-1},{"scroll_y":-1},
                           {"scroll_x":60-tx+1},{"scroll_y":60-ty+1}):
                result,_=self.execute(change,width=w,height=h)
                self.assertEqual(result["records"], [], change)
                self.assertEqual(result["state"][0],0)
                self.assertEqual(result["vtable"],clip.MEMORY_VTABLE)

    def test_unsupported_guard_preserves_original_native_fallback(self):
        for delta in (0,0x02000000):
            for status in (0,2,0xFFFFFFFF):
                result,_=self.execute(guard=status,edge=0,delta=delta)
                self.assertEqual([r[0] for r in result["records"]], [20,10,11,21,13,15,14])
                self.assertEqual(result["records"][1][1:8], [1,0x123456,0x654321,29,0x11223344,0x55667788,0x99AABBCC])
                self.assertEqual(result["records"][1][10],clip.MEMORY_VTABLE+delta)

    def test_only_exact_one_latch_bypasses_c5_and_present_flag_controls_primary(self):
        for delta in (0,0x02000000):
            for latch in (0,1,2,0xFFFFFFFF):
                for flag in (0,1):
                    result,_=self.execute({"regs":[flag,2,3,4]},gate_only=latch,delta=delta)
                    kinds=[r[0] for r in result["records"]]
                    self.assertEqual(kinds, [12,22,14] if latch==flag==1 else [14] if latch==1 else [15,14])
            for edge in (0,1,2,0xFFFFFFFF):
                for present in (0,1,2):
                    result,_=self.execute(edge=edge,present=present,delta=delta)
                    kinds=[r[0] for r in result["records"]]
                    self.assertEqual(kinds,[10,11,21,13]+([12,22]+([] if present==1 else [16]) if edge==1 else [15])+[14])

    def test_nested_full_calls_restore_exact_outer_clipping_table(self):
        for delta in (0,0x02000000):
            for entry_table in ("clipped",clip.MEMORY_VTABLE+delta):
                result,bundle=self.execute({"nested":1,"initial_vtable":entry_table},delta=delta)
                rows=result["records"]
                self.assertEqual([r[0] for r in rows],[10,10,11,21,13,12,22,14,18,11,21,13,12,22,14])
                self.assertEqual(rows[8][10],bundle.entries["clipped_vtable"]+delta)
                expected=bundle.entries["clipped_vtable"]+delta if entry_table=="clipped" else entry_table
                self.assertEqual(result["vtable"],expected)
                self.assertEqual(rows[4][9]-rows[11][9],-112, "nested native invocation must own a distinct frame")

    def test_actual_initial_and_full_hook_path_proves_148_byte_stack_relation(self):
        for w,h in ((800,600),(1024,768),(802,602)):
            for delta in (0,0x02000000):
                result,bundle=self.execute(width=w,height=h,delta=delta,initial_path=True)
                rows=result["records"]
                self.assertEqual([r[0] for r in rows],[30,31,10,11,21,13,12,22,14,32])
                self.assertEqual(rows[1][9]-rows[3][9],148)
                self.assertEqual(rows[3][9],rows[6][9])
                self.assertEqual(rows[-1][1:8],POST_UI)
                self.assertEqual(result["render"],0x12345000)
                self.assertEqual(bundle.initial_contract["stack"]["full_status_plus_to_ready"],148)

    def test_actual_composer_orders_edges_frame_overlays_then_optional_presentation(self):
        for delta in (0,0x02000000):
            for flag in (0,1):
                for edge,frame,panel,present in ((1,1,1,1),(0,1,1,1),(1,0,1,1),
                        (1,2,1,1),(1,0xFFFFFFFF,1,1),(1,1,0,1),(1,1,1,0)):
                    result,_=self.execute({"regs":[flag,2,3,4]},delta=delta,edge=edge,
                                           composition=(frame,panel),present=present)
                    expected=[40,50]
                    if edge:
                        expected += [41,51]
                        if frame==1:
                            expected += [42,52]
                            if panel and flag:
                                expected += [43,53]
                    self.assertEqual([r[0] for r in result["records"]],expected)
                    passed=edge and frame==1 and panel and (not flag or present)
                    self.assertEqual(result["state"][0],int(bool(passed)))
                    if 43 in expected:
                        row=next(r for r in result["records"] if r[0]==43)
                        self.assertEqual(row[1:5],[0,0,799,599])

    def test_actual_fullphysical_presenter_preserves_every_primary_tooltip_pixel(self):
        for w,h in ((800,600),(1024,768)):
            for delta in (0,0x02000000):
                for tooltip in (0,1):
                    result,_=self.execute({"regs":[0,0,w-1,h-1],"tooltip":tooltip},
                                           width=w,height=h,delta=delta,present_real=True)
                    self.assertEqual(result["state"][0],1)
                    copies=[r for r in result["records"] if r[0]==61]
                    self.assertEqual(len(copies),3 if tooltip else 1)
                    rectangles=[]
                    for row in copies:
                        self.assertEqual(row[1],runner.SURFACE+delta)
                        self.assertEqual(row[4],0,"native primary destination sentinel")
                        self.assertEqual(row[7:9],row[2:4],"copy destination must match source origin")
                        rectangles.append((row[2],row[3],row[5],row[6]))
                    # Independent disjoint inclusive-area oracle, including
                    # each surface corner and every reserved frame band.
                    tl,tr=160+(w-640)//2,473+(w-640)//2
                    expected=[(0,0,w-1,h-15),(0,h-14,tl-1,h-1),(tr+1,h-14,w-1,h-1)] if tooltip else [(0,0,w-1,h-1)]
                    self.assertEqual(rectangles,expected)
                    area=sum((r-l+1)*(b-t+1) for l,t,r,b in rectangles)
                    self.assertEqual(area,w*h-((tr-tl+1)*14 if tooltip else 0))


if __name__ == "__main__":
    unittest.main()
