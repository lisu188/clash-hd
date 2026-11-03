#!/usr/bin/env python3
"""Small source/assembly checks only for the uninstalled fresh Line port.

No original file, pixel arena, complete profile/RAM bundle, native line body,
Windows process or CPU interpreter is opened. Passing these checks does not
establish canonical full-emission, native ABI, pixels or runtime acceptance.
"""
from __future__ import annotations
import ast
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT),str(ROOT/"tools")]
from src.patcher import battle_profile_line_replay_v2 as tool
from src.patcher import battle_profile_primitive_request_v2 as request
from src.patcher import partial_tile_clip as clip
import test_battle_profile_primitive_request_v2 as prior

CAPACITY_PLAN = {}


def source_closure():
    return prior.source_closure()|{name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in
        (tool.SOURCE,"tools/test_battle_profile_line_replay_v2.py")}


def tiny_guard_inputs():
    # Explicit synthetic symbols, never a canonical context or producer input.
    layout = SimpleNamespace(profile="completehd",rx=SimpleNamespace(va=0x600000,size=0x40000),
        rw=SimpleNamespace(va=0x640000,size=0x10000),
        protected_spans=(SimpleNamespace(role="parent:.hdstate",va=0x5f0000,size=4096),))
    field = SimpleNamespace(width=3840,height=2160,private_entries=(("check_invocation",0x601000),))
    lease = SimpleNamespace(base_va=0x602000,code=b"\x90"*16,
        field_return_pcs=((0,0x603111),(1,0x603222)),lease_return_pcs=((0,0x603333),(1,0x603444)))
    supplied = prior.previous.arguments()
    kwargs = {name:supplied[name] for name in
        ("atomic_module","content_module","template_module","template_source","assembler_module")}
    kwargs["continuation"] = prior.previous.tool
    args = (layout,field,lease,0x608000,0x607100,tuple(0x606000+16*n for n in range(56)),prior.ROWS)
    return args,kwargs


def tiny_thunks(new):
    base = 0x600000
    assembler = clip._Assembler(base)
    entries,calls,posts,native = [],[],[],[]
    if new:
        returns = tool._append_requests(assembler,base,entries,calls,sites=request.REQUEST_SITES,
            posts=posts,native_returns=native,relocation=clip.Relocation)
    else:returns = request._append_requests(assembler,base,entries,calls)
    assembler.labels.update(helper=0x2000,unsafe_control=0x2100)
    code = bytes(assembler.finish())
    return SimpleNamespace(base=base,code=code,entries=entries,returns=returns,posts=posts,native=native,
        fixups=assembler.fixups,relocations=assembler.relocations)


class AuthoringTests(unittest.TestCase):
    def test_parent_pin_lazy_public_boundary_and_nonacceptance(self):
        self.assertEqual(hashlib.sha256((ROOT/tool.PARENT).read_bytes()).hexdigest(),tool.PARENT_SHA)
        with patch.object(tool,"_issue",side_effect=AssertionError("mutable Line issuer used")):
            for value in (b"",b"authored PE",bytearray(b"authored PE"),None):
                with self.assertRaisesRegex(ValueError,"exact fresh Line original"):
                    tool.emit_line_replay_v2(value,"completehd","3840x2160")
        self.assertIn("native_line_execution_verified",tool.FALSE_CLAIMS)
        self.assertIn("native_stack_capacity_verified",tool.FALSE_CLAIMS)
        self.assertIn("atomic_installation_verified",tool.FALSE_CLAIMS)

    def test_two_call_ports_and_unchanged_eleven_query_thunks(self):
        old,new = tiny_thunks(False),tiny_thunks(True)
        old_start = dict(old.entries)["request_11"]-old.base
        new_start = dict(new.entries)["request_11"]-new.base
        self.assertEqual(old_start,new_start);self.assertEqual(old.code[:old_start],new.code[:new_start])
        self.assertEqual(len(new.returns),13);self.assertEqual(len(new.posts),2);self.assertEqual(len(new.native),2)
        calls = [row for row in new.relocations if row.purpose == "closed fresh memory Line replay"]
        self.assertEqual(len(calls),2);self.assertTrue(all(row.kind == "rel32" and row.target == tool.LINE_TARGET for row in calls))
        self.assertEqual(new.code.count(bytes.fromhex("83c450619d8d64240c")),2)
        self.assertEqual(new.code.count(bytes.fromhex("8944246c9c5889442470")),2)
        self.assertEqual(tool.REMOVED_OVERLAPS,(0x430ad8,0x430b0a))
        self.assertEqual(tuple(pc+3 for pc,_,_ in tool.LINE_WINDOWS),tool.REMOVED_OVERLAPS)
        self.assertEqual(bytes.fromhex(tool.LINE_WINDOWS[0][1])[3:],bytes.fromhex("e954fdffff"))
        self.assertEqual(bytes.fromhex(tool.LINE_WINDOWS[1][1])[3:],bytes.fromhex("89ec5d5f5e595bc3"))

    def test_phase_vtable_guard_and_conservative_unchanged_rx_capacity_plan(self):
        args,kwargs = tiny_guard_inputs();posts = (0x607000,0x607080)
        old = request._raw_guard(*args,**kwargs)[0]
        new = tool._guard_factory(request,list(posts))(*args,**kwargs)[0]
        old_thunks,new_thunks = tiny_thunks(False),tiny_thunks(True)
        guard_delta = len(new.code)-len(old.code)
        prefix_delta = len(new_thunks.code)-len(old_thunks.code)+15
        extra_upper = ((prefix_delta+15)//16)*16+guard_delta
        self.assertGreater(guard_delta,0);self.assertGreater(prefix_delta,0)
        self.assertLessEqual(extra_upper,2990)
        self.assertEqual({row.target for row in new.relocations if row.purpose == "literal memory Line vtable"},{tool.MEMORY_VTABLE})
        self.assertEqual({row.target for row in new.relocations if row.purpose == "fixed Line post-helper CALL return"},set(posts))
        self.assertEqual(len([row for row in new.relocations if row.purpose == "fixed Line pre-helper CALL return"]),2)
        CAPACITY_PLAN.update(scope="Synthetic symbols and source-byte size bound only; not canonical full-emission proof",
            parent_minimum_rx_remaining_bytes=2990,shared_guard_delta_bytes=guard_delta,
            thunk_delta_bytes=len(new_thunks.code)-len(old_thunks.code),helper_phase_delta_bytes=15,
            prefix_alignment_quantum_bytes=16,additional_rx_upper_bound_bytes=extra_upper,
            conservative_remaining_rx_lower_bound_bytes=2990-extra_upper,
            rx_expanded=False,rw_borrowed=False,full_emission_verified=False,native_line_executed=False)

    def test_exact_generated_helper_phase_composition_without_parent_emission(self):
        raw = (ROOT/tool.PARENT).read_bytes()
        seen = []
        class Captured(Exception):pass
        def compiler(source,filename,mode):
            self.assertEqual(filename,str(ROOT/request.SOURCE)+"#whole_shared_composition")
            result = tool._composition_source(source)
            compile(result,str(ROOT/tool.SOURCE)+"#authoring_only",mode)
            seen.append(result);raise Captured()
        namespace = dict(request.__dict__)|{"compile":compiler}
        exec(compile(tool._function(raw,"_raw_emit"),str(ROOT/tool.SOURCE)+"#capture_only","exec"),namespace)
        with self.assertRaises(Captured):namespace["_raw_emit"](continuation=prior.previous.tool)
        self.assertEqual(len(seen),1)
        self.assertEqual(seen[0].count("a.u32(HELPER_BYTES+40);a.emit('83f801');branch('normal.finish','0f84')"),1)
        with self.assertRaises(ValueError):tool._composition_source(seen[0])


def run_tests():
    before = source_closure()
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(AuthoringTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if source_closure() != before:raise ValueError("small Line authoring source closure changed")
    if not result.wasSuccessful() or result.skipped or result.testsRun != 4:raise AssertionError("small Line authoring checks failed")
    print(json.dumps(CAPACITY_PLAN,sort_keys=True))
    print("Small source/assembly authoring PASS; full emission, CPU/native line, pixels, installation and runtime unverified.")
    return result.testsRun


if __name__ == "__main__":
    run_tests()
