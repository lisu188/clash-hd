from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from dataclasses import replace
import copy
import io
import json
import os
from pathlib import Path
import random
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "tools")]
from src.patcher import framed_bounded_input as target
from src.patcher import framed_bounded_paint as bounded
from src.patcher import framed_camera as camera
from src.patcher import framed_input as inputs
from src.patcher import partial_tile_clip as clip
from src.patcher import pe_extension as pe
from src.patcher.framed_viewport import FramedViewport
import test_framed_bounded_paint as fixture
import build_framed_bounded_input_candidate as cli
from test_pe_extension import independent_image

SIZES = fixture.SIZES
DATA_SIZE = fixture.DATA_SIZE
BASE = 0x100000
GLOBALS = {clip.GAME_DATA_GLOBAL: 0x100, clip.MAP_SURFACE_GLOBAL: 0x104,
    clip.RENDER_HOOK_GLOBAL: 0x108, clip.LOWER_ROW_OWNER_GLOBAL: 0x10c,
    clip.POST_TILE_CALLBACK_GLOBAL: 0x110, clip.TILE_CALLBACK_GLOBAL: 0x114,
    clip.CURRENT_PLAYER_GLOBAL: 0x118, inputs.MOUSE_X: 0x11c, inputs.MOUSE_Y: 0x120,
    inputs.MOUSE_SHIFT: 0x124, inputs.MINIMAP_ORIGIN: 0x128, inputs.MINIMAP_ORIGIN+2: 0x12a,
    inputs.MINIMAP_SIZE: 0x12c, inputs.MINIMAP_SIZE+2: 0x12e,
    clip.MEMORY_VTABLE: 0x300, inputs.PRIMARY_SURFACE: 0x500}
CONTROL = 0x200
STATE = 0x28000
LOG = STATE + 0x100
BUTTON = 0x800


def synthetic_input(key="1280x720", base=BASE):
    original = bytearray()
    offsets = {}
    specs = [(inputs.CLICK_GATE, "f6402c010f95c025ff000000c3")]
    specs.extend((row[1], row[2]) for row in (*inputs.CALL_SITES, *inputs.PANEL_SITES))
    for va, value in specs:
        offsets[va] = len(original)
        original.extend(bytes.fromhex(value))
    with (patch.object(clip, "verify_original"), patch.object(inputs, "NATIVE_CONTRACTS", ()),
          patch.object(inputs, "_native_highlow_vas", return_value=set()),
          patch.object(clip, "file_offset", side_effect=lambda data, va, size: offsets[va])):
        return inputs.emit_input_bundle(bytes(original), base_va=base, width=int(key.split("x")[0]), height=int(key.split("x")[1]))


def input_code(bundle, *, upgraded=True):
    layout = FramedViewport(bundle.width, bundle.height)
    va = bundle.entries["pixel_guard.minimap_clear"]
    deny = bundle.entries["pixel_guard.deny"]
    old = target.world_gate(layout, va, deny)
    offset = va - bundle.base_va
    assert bundle.code[offset:offset+len(old)] == old
    code = bytearray(bundle.code)
    if upgraded:
        code[offset:offset+len(old)] = target.world_gate(layout, va, deny, small_world=True)
    return bytes(code)


def synthetic_parent(key="1280x720"):
    base, parent, metadata = fixture.synthetic_parent(key)
    code, relocations, hooks, removed = bounded._parent_parts(base, parent, metadata)
    mouse = synthetic_input(key, metadata["code_va"]+len(code))
    appended = tuple(replace(row, offset=row.offset+len(code)) for row in mouse.relocations)
    ext = pe._extend_verified_image(base, code=code+mouse.code, code_va=metadata["code_va"],
        relocations=relocations+appended, hooks=hooks, removed_highlow_rvas=removed,
        binding={"stage": camera.PARENT_STAGE, "resolution": key})
    report = dict(metadata, **ext.metadata)
    report.update(entry_vas=metadata["entry_vas"] | {"framed_input."+k: v for k, v in mouse.entries.items()},
                  extension_payload_size=len(code)+len(mouse.code), extension_payload_sha256=ext.metadata["code_sha256"])
    image, bound_report = bounded._extend_verified_parent(base, ext.image, report, key, {})
    return base, image, bound_report


class InputByteTests(unittest.TestCase):
    def test_all_existing_source_pins_and_bounded_renderer_source_match(self):
        self.assertTrue(target.source_status()["passed"])
        self.assertEqual(camera.sha(Path(bounded.__file__).read_bytes()), target.BOUNDED_SOURCE_SHA256)

    def test_old_world_checks_match_the_actual_input_emitter_at_ten_resolutions(self):
        for key in SIZES:
            with self.subTest(key=key):
                bundle = synthetic_input(key)
                old, new = bundle.code, input_code(bundle)
                start = bundle.entries["pixel_guard.minimap_clear"]-bundle.base_va
                allowed = {start+axis*target.AXIS_BYTES+target.LIMIT_OFFSET+i for axis in (0, 1) for i in range(16)}
                self.assertEqual(len(old), len(new))
                self.assertTrue(all(i in allowed for i, (a,b) in enumerate(zip(old,new)) if a!=b))
                self.assertEqual(new[-11:], old[-11:])

    def test_two_exact_edits_reconstruct_the_final_image_without_changing_renderer(self):
        for key in SIZES:
            with self.subTest(key=key):
                base, parent, metadata = synthetic_parent(key)
                frozen = copy.deepcopy(metadata)
                image, report = target._upgrade_verified_parent(parent, metadata, key)
                self.assertEqual(metadata, frozen)
                self.assertEqual(len(parent), len(image))
                self.assertEqual(pe.inspect_pe(parent), pe.inspect_pe(image))
                rebuilt, allowed = bytearray(parent), set()
                self.assertEqual(len(report["edits"]), 2)
                for row in report["edits"]:
                    offset = row["offset"]
                    old, new = bytes.fromhex(row["old_hex"]), bytes.fromhex(row["new_hex"])
                    self.assertEqual((len(old), len(new)), (16,16))
                    self.assertEqual(parent[offset:offset+16], old)
                    self.assertEqual(row["va"]-0x400000, row["rva"])
                    rebuilt[offset:offset+16] = new
                    allowed.update(range(offset,offset+16))
                self.assertEqual(bytes(rebuilt), image)
                self.assertTrue(all(i in allowed for i, (a,b) in enumerate(zip(parent,image)) if a!=b))
                self.assertEqual(report["output_sha256"], camera.sha(image))
                self.assertTrue(report["small_world_input_enabled"])
                self.assertTrue(report["bounded_small_world_paint"])
                for field in ("game_runtime_executed", "manual_input_proof", "promotion_ready", "parent_probe_reusable"):
                    self.assertIs(report[field], False)
                self.assertEqual(report["parent_build"], metadata)
                self.assertEqual(report["stage"], target.STAGE)

    def test_signed_world_guard_does_not_introduce_relocations_or_new_allocations(self):
        _, parent, metadata = synthetic_parent()
        image, report = target._upgrade_verified_parent(parent, metadata, "1280x720")
        before, p1, f1, _ = independent_image(parent)
        after, p2, f2, _ = independent_image(image)
        self.assertEqual(f1, f2)
        self.assertEqual(p1, p2)
        for row in metadata["relocations"]:
            off = metadata["code_rva"]+row["offset"]
            self.assertEqual(before[off:off+4], after[off:off+4])
        self.assertEqual(pe._old_relocations(parent, pe.inspect_pe(parent)), pe._old_relocations(image, pe.inspect_pe(image)))

    def test_rejects_wrong_stage_incomplete_entries_and_evidence_claims(self):
        _, parent, metadata = synthetic_parent()
        changes = [("stage", camera.PARENT_STAGE),("schema", "unknown"),("resolution", "800x600"),
            ("bounded_small_world_paint",False),("camera_clamp",False),("minimap_viewport",False),
            ("small_world_input_enabled",True),("validation_stage_only",False),("code_sha256","0"*64),
            ("code_bytes",True),("entry_vas",{}),("relocations",None),
            ("game_runtime_executed",True),("manual_input_proof",True),("promotion_ready",True)]
        for key, value in changes:
            with self.subTest(key=key), self.assertRaises(ValueError):
                target._upgrade_verified_parent(parent, metadata | {key:value}, "1280x720")

    def test_old_checks_and_labels_remain_authenticated_even_with_updated_hashes(self):
        _, parent, metadata = synthetic_parent()
        parsed = pe.inspect_pe(parent)
        start = parsed.file_offset(metadata["entry_vas"][target.ENTRY]-parsed.image_base,190)
        code_start = parsed.file_offset(metadata["code_va"]-parsed.image_base, metadata["code_bytes"])
        for offset in (0, target.LIMIT_OFFSET, target.AXIS_BYTES+target.LIMIT_OFFSET, 179):
            data = bytearray(parent); data[start+offset] ^= 1
            altered = dict(metadata, output_sha256=camera.sha(data), code_sha256=camera.sha(data[code_start:code_start+metadata["code_bytes"]]))
            with self.subTest(offset=offset), self.assertRaisesRegex(ValueError,"old bytes"):
                target._upgrade_verified_parent(bytes(data),altered,"1280x720")
        altered = dict(metadata,entry_vas=metadata["entry_vas"] | {target.DENY: metadata["entry_vas"][target.DENY]+1})
        with self.assertRaisesRegex(ValueError,"denial label"):
            target._upgrade_verified_parent(parent,altered,"1280x720")

    def test_relocation_overlap_malformed_inventory_and_double_application_reject(self):
        _, parent, metadata = synthetic_parent()
        va = metadata["entry_vas"][target.ENTRY]+target.LIMIT_OFFSET
        altered = copy.deepcopy(metadata)
        altered["relocations"].append({"offset":va-metadata["code_va"], "kind":"rel32"})
        with self.assertRaisesRegex(ValueError,"relocation"):
            target._upgrade_verified_parent(parent,altered,"1280x720")
        table, fields = pe._old_relocations(parent,pe.inspect_pe(parent))
        with patch.object(pe,"_old_relocations",return_value=(table,fields+(va-0x400000,))):
            with self.assertRaisesRegex(ValueError,"HIGHLOW"):
                target._upgrade_verified_parent(parent,metadata,"1280x720")
        for row in ({"offset":True,"kind":"rel32"},{"offset":0,"kind":"guess"},{"offset":-1,"kind":"abs32"}):
            with self.assertRaises(ValueError):
                target._upgrade_verified_parent(parent, metadata | {"relocations":[row]}, "1280x720")
        image, report = target._upgrade_verified_parent(parent,metadata,"1280x720")
        with self.assertRaises(ValueError):
            target._upgrade_verified_parent(image,report,"1280x720")
        with self.assertRaisesRegex(ValueError,"old bytes"):
            target._upgrade_verified_parent(image, metadata | {"output_sha256":report["output_sha256"],"code_sha256":report["code_sha256"]},"1280x720")

    def test_unknown_original_and_source_drift_fail_before_parent_build(self):
        with patch.object(bounded,"build_candidate") as build:
            for data in (None,b"",b"synthetic",bytearray(4)):
                with self.assertRaises(ValueError): target.build_candidate(data,"1280x720")
            build.assert_not_called()
        with patch.object(target,"BOUNDED_SOURCE_SHA256","0"*64):
            with self.assertRaisesRegex(ValueError,"bounded renderer source"):
                target.source_status()

    def test_native_fixture_resolves_every_operand_without_unexpected_absolute_pointers(self):
        for key in SIZES:
            for entry in ("click_gate","minimap_gate"):
                code, fixups = native_image(key,entry)
                self.assertLess(len(code),0x20000)
                self.assertTrue(fixups)
                self.assertTrue(all(0 <= p <= len(code)-4 and kind in (0,1) for p,kind,value in fixups))

    def test_emitter_rejects_wrong_geometry_flags_addresses_and_rebases_identically(self):
        layout = FramedViewport(1366,768)
        va = 0x600000; end = va+2*target.AXIS_BYTES+11
        for kwargs in ({"small_world":1},{"va":-1},{"deny_va":va},{"va":True},{"va":0x7ffffffe}):
            args = dict(layout=layout,va=va,deny_va=end);args.update(kwargs)
            with self.assertRaises(ValueError):target.world_gate(**args)
        self.assertEqual(target.world_gate(layout,va,end,small_world=True),target.world_gate(layout,va+0x100000,end+0x100000,small_world=True))


class InputCLITests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="bounded-input-cli-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.original = self.root/"game"/"clash95.exe"
        self.original.parent.mkdir()
        self.original.write_bytes(b"synthetic-not-a-game")

    def test_preflight_is_memory_only_even_with_output_arguments(self):
        output = self.root/"missing"/"candidate.exe"
        with patch.object(target,"build_candidate",return_value=(b"image",{"output_sha256":camera.sha(b"image")})),redirect_stdout(io.StringIO()):
            result = cli.main(["--original",str(self.original),"--resolution","1366x768","--preflight","--output",str(output)])
        self.assertEqual(result,0)
        self.assertFalse(output.parent.exists())
        self.assertEqual(self.original.read_bytes(),b"synthetic-not-a-game")

    def test_unknown_original_and_unsafe_existing_destinations_fail(self):
        with redirect_stderr(io.StringIO()):
            self.assertEqual(cli.main(["--original",str(self.original),"--resolution","1366x768","--preflight"]),1)
        for out,rep in ((self.original,self.root/"x.json"),(ROOT/"x.exe",ROOT/"x.json"),(self.root/"x.exe",self.root/"x.exe")):
            with patch.object(target,"build_candidate") as build,redirect_stderr(io.StringIO()):
                self.assertEqual(cli.main(["--original",str(self.original),"--resolution","1366x768","--output",str(out),"--report-json",str(rep)]),1)
            build.assert_not_called()

    def test_successful_exclusive_write_has_matching_report_and_does_not_touch_original(self):
        out,rep = self.root/"candidate.exe",self.root/"candidate.json"
        with (patch.object(cli,"_outputs",return_value=(out,rep)),
              patch.object(target,"build_candidate",return_value=(b"candidate",{"output_sha256":camera.sha(b"candidate")})),redirect_stdout(io.StringIO())):
            self.assertEqual(cli.main(["--original",str(self.original),"--resolution","1280x720","--output",str(out),"--report-json",str(rep)]),0)
        self.assertEqual(json.loads(rep.read_text())["output_sha256"],camera.sha(out.read_bytes()))
        self.assertEqual(self.original.read_bytes(),b"synthetic-not-a-game")

    def test_racing_writer_is_not_overwritten(self):
        out,rep = self.root/"candidate.exe",self.root/"candidate.json"
        def build(*_):
            out.write_bytes(b"another-writer")
            return b"ours",{"output_sha256":camera.sha(b"ours")}
        with patch.object(cli,"_outputs",return_value=(out,rep)),patch.object(target,"build_candidate",side_effect=build),redirect_stderr(io.StringIO()):
            self.assertEqual(cli.main(["--original",str(self.original),"--resolution","1280x720","--output",str(out),"--report-json",str(rep)]),1)
        self.assertEqual(out.read_bytes(),b"another-writer")
        self.assertFalse(rep.exists())


def native_image(key, entry="click_gate", upgraded=True, base=BASE):
    prefix = 0x200
    mouse = synthetic_input(key,base+prefix)
    a = clip._Assembler(base)
    a.code.extend(bytes(prefix));a.code.extend(input_code(mouse,upgraded=upgraded))
    a.relocations.extend(replace(r,offset=r.offset+prefix) for r in mouse.relocations)
    stubs = {}
    for name,tag in (("native_click_gate",2),("native_minimap_gate",1)):
        stubs[name] = base+len(a.code)
        a.emit("9c608b35");a.absolute(0x7abc0000,"fixture_data_pointer")
        a.emit("8b8e");a.u32(LOG)
        a.emit("83f904");a.branch("0f83",name+".overflow")
        a.emit("89c8c1e0048d8406");a.u32(LOG+4)
        a.emit("c700");a.u32(tag)
        a.emit("8b54241c895004ff86");a.u32(LOG)
        if name=="native_minimap_gate":
            a.emit("8b86");a.u32(CONTROL);a.emit("8944241c619dc3")
        else:
            a.emit("619df6402c010f95c025ff000000c3")
        a.label(name+".overflow");a.emit("0f0b")
    wrapper = clip._Assembler(base)
    wrapper.emit("9c608b5424288992");wrapper.u32(STATE+40)
    wrapper.emit("8992000100008d82000400008982040100008d8a00100000898a04040000")
    wrapper.emit("8d8a000300008988b8000000")
    wrapper.emit("83ba0402000000");wrapper.branch("0f84","surface.ok")
    wrapper.emit("c7820401000000000000")
    wrapper.label("surface.ok")
    wrapper.emit("83ba0802000000");wrapper.branch("0f84","table.ok")
    wrapper.emit("c780b800000000000000")
    wrapper.label("table.ok")
    wrapper.emit("83ba0c02000000");wrapper.branch("0f84","game.ok")
    wrapper.emit("c7820001000000000000")
    wrapper.label("game.ok")
    wrapper.emit("8d82");wrapper.u32(BUTTON)
    wrapper.emit("bb22222222b933333333ba44444444bd55555555be66666666bf77777777")
    wrapper.emit("68d70e00009d")
    bounded._transfer(wrapper,"e8",mouse.entries[entry],"input_entry")
    wrapper.emit("9c608b7c244c")
    for i in range(9):
        wrapper.emit("8b4c24"+bytes([i*4]).hex()+"898f");wrapper.u32(STATE+i*4)
    wrapper.emit("619d8944241c619dc3")
    assert len(wrapper.code)<prefix
    a.code[:len(wrapper.code)]=wrapper.finish()
    a.relocations.extend(wrapper.relocations)
    fixups=[]
    for r in a.relocations:
        if r.kind=="abs32":
            if r.purpose=="fixture_data_pointer":fixups.append((r.offset,1,STATE+40))
            elif r.target in GLOBALS:fixups.append((r.offset,1,GLOBALS[r.target]))
            else:assert r.purpose in ("ordinary_map_owner","supported_tile_callback"),r
        else:
            address = stubs.get(r.purpose,r.target)
            assert base <= address < base+len(a.code),(r,address)
            struct.pack_into("<i",a.code,r.offset,address-base-r.offset-4)
    return bytes(a.code),fixups


def expected(key, case):
    width,height=map(int,key.split("x"))
    if (case.get("entry","click_gate")=="click_gate" and not (case.get("click",1)&1)):
        return False
    if (case.get("null_surface") or case.get("bad_vtable") or case.get("null_game") or
        case.get("render_hook",0x40ad40)!=0x40ad40 or case.get("owner",0) or case.get("post",0) or
        case.get("callback",0) not in (0,0x425120,0x429ec0) or case.get("player",0) not in range(5) or
        not case.get("interactive",1) or case.get("minimap_player",0) not in range(5) or case.get("native_minimap",0)):
        return False
    w,h,sx,sy=case.get("world",(3,2,0,0))
    x,y=case.get("point",(32,16))
    shift=case.get("shift",0)&31
    x=(x if x<0x80000000 else x-0x100000000)>>shift
    y=(y if y<0x80000000 else y-0x100000000)>>shift
    if not (32<=x<width-32 and 16<=y<height-16) or (x>=width-224 and y>=height-80):return False
    if case.get("minimap_enabled",0):
        mw,mh=case.get("mini_size",(214,214))
        left,top=case.get("mini_origin",(width-32-mw,16))
        if not (mw>0 and mh>0 and left>=32 and left+mw==width-32 and top==16 and top+mh<=height-16):return False
        if left<=x<left+mw and top<=y<top+mh:return False
    return (1<=w<=100 and 1<=h<=100 and 0<=sx<=max(0,w-(width-64)//64)
        and 0<=sy<=max(0,h-(height-32)//64) and sx+(x-32)//64<w and sy+(y-16)//64<h)


class NativeInputTests(unittest.TestCase):
    setUpClass = classmethod(fixture.BoundedNativeTests.setUpClass.__func__)

    def execute(self,key,cases,entry="click_gate",upgraded=True,base=BASE):
        code,fixups=native_image(key,entry,upgraded,base)
        payload=bytearray(struct.pack("<III",len(code),len(cases),len(fixups))+code+b"".join(struct.pack("<III",*f) for f in fixups))
        before=[]
        width,height=map(int,key.split("x"))
        for case in cases:
            data=bytearray(b"\xa5"*DATA_SIZE)
            data[0x100:0x1000]=bytes(0xf00);data[STATE:STATE+0x200]=bytes(0x200)
            struct.pack_into("<4i",data,0x222e0,*case.get("world",(3,2,0,0)))
            def put(off,value):struct.pack_into("<I",data,off,value&0xffffffff)
            for off,value in ((0x108,case.get("render_hook",0x40ad40)),(0x10c,case.get("owner",0)),
                (0x110,case.get("post",0)),(0x114,case.get("callback",0)),(0x118,case.get("player",0)),
                (0x11c,case.get("point",(32,16))[0]),(0x120,case.get("point",(32,16))[1]),(0x124,case.get("shift",0)),
                (0x23ec7,case.get("minimap_player",0)),(BUTTON+44,case.get("click",1)),
                (CONTROL,case.get("native_minimap",0)),(CONTROL+4,case.get("null_surface",0)),
                (CONTROL+8,case.get("bad_vtable",0)),(CONTROL+12,case.get("null_game",0)),(0x400,width|(height<<16))):put(off,value)
            for p in range(5):
                put(0x22313+1423*p,case.get("interactive",1))
                put(0x2230f+1423*p,case.get("minimap_enabled",0))
            mw,mh=case.get("mini_size",(214,214));left,top=case.get("mini_origin",(width-32-mw,16))
            struct.pack_into("<4H",data,0x128,left,top,mw,mh)
            before.append(bytes(data));payload.extend(data)
        result=subprocess.run([str(self.exe)],input=bytes(payload),capture_output=True,timeout=30,**self.options)
        self.assertEqual(result.returncode,0,result.stderr.decode(errors="replace"))
        self.assertEqual(len(result.stdout),len(cases)*(DATA_SIZE+4))
        reports=[]
        for i,(case,initial) in enumerate(zip(cases,before)):
            start=i*(DATA_SIZE+4);status=struct.unpack_from("<I",result.stdout,start)[0]
            data=result.stdout[start+4:start+4+DATA_SIZE]
            pointer=struct.unpack_from("<I",data,STATE+40)[0]
            count=struct.unpack_from("<I",data,LOG)[0]
            events=[struct.unpack_from("<4I",data,LOG+4+j*16) for j in range(count)]
            self.assertLessEqual(count,2)
            registers=struct.unpack_from("<9I",data,STATE)
            self.assertEqual(registers[:3],(0x77777777,0x66666666,0x55555555))
            self.assertEqual(registers[4:7],(0x22222222,0x44444444,0x33333333))
            self.assertEqual(registers[7],status)
            self.assertEqual(registers[8]&0xcd5,0xed7&0xcd5)
            if entry=="click_gate":
                self.assertEqual(events[0][:2],(2,pointer+BUTTON))
            expected_data=bytearray(initial)
            for off,value in ((0x100,0 if case.get("null_game") else pointer),
                (0x104,0 if case.get("null_surface") else pointer+0x400), (0x404,pointer+0x1000),
                (0x4b8,0 if case.get("bad_vtable") else pointer+0x300)):
                struct.pack_into("<I",expected_data,off,value)
            expected_data[STATE:STATE+0x200]=data[STATE:STATE+0x200]
            self.assertEqual(data,bytes(expected_data),"input changed target memory outside fixture records")
            allowed=expected(key,case | {"entry":entry})
            if not upgraded:
                w,h,_,_=case.get("world",(3,2,0,0))
                allowed=allowed and w>=(width-64)//64 and h>=(height-32)//64
            self.assertEqual(status,int(allowed if entry=="click_gate" else not allowed),case)
            reports.append((status,events))
        return reports

    def test_small_maps_valid_tiles_and_cleared_regions_at_every_resolution(self):
        for key in SIZES:
            width,height=map(int,key.split("x"))
            points=[(32,16),(95,79),(96,16),(223,143),(224,143),(223,144),(width-33,height-17)]
            cases=[{"world":world,"point":p} for world in ((1,1,0,0),(3,2,0,0),(1,100,0,5),(100,1,5,0)) for p in points]
            for entry in ("click_gate","minimap_gate"):
                with self.subTest(key=key,entry=entry):self.execute(key,cases,entry)

    def test_large_map_results_match_original_mouse_gates(self):
        rng=random.Random(35)
        for key in SIZES:
            w,h=map(int,key.split("x"))
            cases=[{"world":(100,100,0,0),"point":(rng.randrange(w),rng.randrange(h))} for _ in range(45)]
            for entry in ("click_gate","minimap_gate"):
                new=self.execute(key,cases,entry)
                old=self.execute(key,cases,entry,upgraded=False)
                self.assertEqual([r[0] for r in new],[r[0] for r in old])

    def test_invalid_world_and_unclamped_camera_are_denied_without_writes(self):
        cases=[{"world":v} for v in ((0,1,0,0),(1,0,0,0),(101,1,0,0),(1,101,0,0),(-1,2,0,0),
            (3,2,1,0),(3,2,0,1),(3,2,-1,0),(3,2,0,-1),(3,2,-2147483648,2147483647),(100,100,99,99))]
        for entry in ("click_gate","minimap_gate"):
            self.execute("1366x768",cases,entry)

    def test_frame_six_action_cells_and_full_minimap_footprint_remain_excluded(self):
        for key in SIZES:
            w,h=map(int,key.split("x"));world=(100,1,0,0)
            points=[(31,16),(32,15),(w-32,16),(32,h-16),(w-225,h-80)]
            for row in range(2):
                for col in range(3):
                    l,t=w-224+col*64,h-80+row*32
                    points.extend([(l,t),(l+63,t+31)])
            cases=[{"world":(100,100,0,0),"point":p} for p in points]
            mw,mh=134,94;left=w-32-mw
            cases += [{"world":world,"point":p,"minimap_enabled":1,"mini_size":(mw,mh)} for p in
                ((left-1,16),(left,16),(left+1,17),(w-33,16),(w-33,109),(left,110))]
            for entry in ("click_gate","minimap_gate"):self.execute(key,cases,entry)

    def test_unknown_owners_callbacks_and_players_do_not_gain_access(self):
        cases=[{key:value} for key,value in (("owner",1),("post",1),("callback",1),("render_hook",0),
            ("player",5),("player",-1),("interactive",0),("minimap_player",5),("minimap_player",-1),
            ("null_surface",1),("bad_vtable",1))]
        for entry in ("click_gate","minimap_gate"):
            reports=self.execute("1280x720",cases,entry)
            self.assertTrue(all([e[0] for e in events]==([2] if entry=="click_gate" else []) for _,events in reports))
        for cb in (0,0x425120,0x429ec0):self.execute("1280x720",[{"callback":cb,"player":p} for p in range(5)])

    def test_native_click_first_and_minimap_rejection_still_control_admission(self):
        reports=self.execute("1280x720",[{"click":0},{"native_minimap":1},{}])
        self.assertEqual([[e[0] for e in events] for _,events in reports],[[2],[2,1],[2,1]])
        self.assertEqual([s for s,_ in reports],[0,0,1])
        self.execute("1280x720",[{"click":0,"null_game":1}])
        self.execute("1280x720",[{"null_game":1}],entry="minimap_gate")

    def test_signed_shifted_mouse_coordinates_and_rebased_code(self):
        cases=[{"point":p,"shift":shift} for shift in (0,1,6,31,32,38) for p in
            ((32<<6,16<<6),(95<<6,79<<6),(-1,100),(-2147483648,100),(2147483647,2147483647))]
        a=self.execute("1366x768",cases)
        b=self.execute("1366x768",cases,base=0x700000)
        self.assertEqual([r[0] for r in a],[r[0] for r in b])

    def test_bad_minimap_dimensions_or_stale_anchor_cannot_reach_world(self):
        cases=[{"minimap_enabled":1,"point":(32,16),**change} for change in
            ({"mini_size":(0,10)},{"mini_size":(134,0)},{"mini_origin":(1,16)},
             {"mini_origin":(1034,17)},{"mini_size":(214,710)})]
        for entry in ("click_gate","minimap_gate"):self.execute("1280x720",cases,entry)


if __name__ == "__main__":
    unittest.main()
