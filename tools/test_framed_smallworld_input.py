#!/usr/bin/env python3
"""Original-backed full-wrapper CPU fixtures for existing bounded input.

Never starts Clash95, CDB, a wrapper, or sends input. CPU cases use the original
native predicates copied into fixture memory, with a separate scalar oracle.
"""
from __future__ import annotations

from dataclasses import replace
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "tools")]
from src.patcher import framed_bounded_input as target
from src.patcher.framed_viewport import FramedViewport
from src.patcher import framed_input as frozen
from src.patcher import pe_extension as pe
import test_framed_input as legacy


def expected_allowed(width, height, case):
    """Independent scalar oracle, including unchanged ordinary-map exclusions."""
    if case["name"] == "click_gate" and not case.get("click", 1) & 1:
        return False
    if (case.get("bad") or case.get("null_surface") or case.get("primary_surface")
            or case.get("current_player", 0) not in range(5) or not case.get("interactive", 1)
            or case.get("minimap_player", 0) not in range(5)
            or case.get("render_hook", 0x40AD40) != 0x40AD40 or case.get("owner", 0) != 0
            or case.get("post_tile_callback", 0) != 0
            or case.get("callback", 0) not in (0, 0x425120, 0x429EC0)
            or case.get("initial_vtable", 0x50EE24) != 0x50EE24):
        return False
    shift = case.get("shift", 0) & 31
    x = legacy.runner.signed(case.get("raw_x", 100) & 0xFFFFFFFF) >> shift
    y = legacy.runner.signed(case.get("raw_y", 100) & 0xFFFFFFFF) >> shift
    if not (32 <= x < width - 32 and 16 <= y < height - 16):
        return False
    if x >= width - 224 and y >= height - 80:
        return False
    enabled = (case.get("minimap_enabled", 0) and
               case.get("minimap_enabled_player", case.get("minimap_player", 0)) == case.get("minimap_player", 0))
    if enabled:
        mw, mh = case.get("mini_width", 214), case.get("mini_height", 214)
        ml, mt = case.get("mini_left", width - 32 - mw), case.get("mini_top", 16)
        if not (mw > 0 and mh > 0 and ml >= 32 and ml + mw == width - 32 and mt == 16 and mt + mh <= height - 16):
            return False
        if ml <= x < ml + mw and mt <= y < mt + mh:
            return False
    mw, mh = case.get("map_width", 60), case.get("map_height", 60)
    sx, sy = case.get("scroll_x", 10), case.get("scroll_y", 17)
    if not (1 <= mw <= 100 and 1 <= mh <= 100):
        return False
    max_x = max(0, mw - (width - 64) // 64)
    max_y = max(0, mh - (height - 32) // 64)
    return (0 <= sx <= max_x and 0 <= sy <= max_y
            and sx + (x - 32) // 64 < mw and sy + (y - 16) // 64 < mh)


def upgraded_bundle(original, *, base_va, width, height):
    """Bind the existing component's world gate to authenticated full wrappers."""
    bundle = frozen.emit_input_bundle(original, base_va=base_va, width=width, height=height)
    layout = FramedViewport(width, height)
    start = bundle.entries["pixel_guard.minimap_clear"]
    deny = bundle.entries["pixel_guard.deny"]
    offset = start - base_va
    old = target.world_gate(layout, start, deny)
    new = target.world_gate(layout, start, deny, small_world=True)
    if bundle.code[offset:offset + len(old)] != old or len(new) != len(old):
        raise AssertionError("existing bounded input gate differs from authenticated original-backed wrapper")
    code = bundle.code[:offset] + new + bundle.code[offset + len(old):]
    return replace(bundle, code=code)


class OracleTests(unittest.TestCase):
    def test_4k_world_edge_differs_from_frozen_rejection(self):
        good = dict(name="click_gate",map_width=50,map_height=50,scroll_x=0,scroll_y=17,raw_x=3231,raw_y=2096)
        self.assertTrue(expected_allowed(3840,2160,good))
        self.assertFalse(legacy.expected_allowed(3840,2160,good))
        for change in (dict(raw_x=3232),dict(scroll_x=1),dict(scroll_y=18),dict(scroll_x=-1),dict(map_width=101)):
            self.assertFalse(expected_allowed(3840,2160,good | change))


@unittest.skipUnless(legacy.runner.ORIGINAL.is_file(), "requires authenticated original for wrapper and candidate checks")
class OriginalWrapperTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = legacy.runner.ORIGINAL.read_bytes()

    def test_existing_source_pins_and_exactly_two_replacement_spans(self):
        self.assertTrue(target.source_status()["passed"])
        for width,height in ((800,600),(802,602),(1024,768),(3840,2160)):
            old = frozen.emit_input_bundle(self.original,base_va=legacy.runner.BASE,width=width,height=height)
            new = upgraded_bundle(self.original,base_va=legacy.runner.BASE,width=width,height=height)
            offset = old.entries["pixel_guard.minimap_clear"] - old.base_va
            admitted = {offset + axis * 84 + 24 + i for axis in range(2) for i in range(16)}
            self.assertEqual(len(old.code),len(new.code))
            self.assertEqual(old.entries,new.entries)
            self.assertEqual(old.relocations,new.relocations)
            self.assertTrue(all(i in admitted for i,(a,b) in enumerate(zip(old.code,new.code)) if a != b))
            for relocation in old.relocations:
                self.assertTrue(admitted.isdisjoint(range(relocation.offset,relocation.offset+4)))

    def test_actual_existing_4k_candidate_contains_the_tested_complete_wrappers(self):
        image,report = target.build_candidate(self.original,"3840x2160")
        entries = report["parent_build"]["entry_vas"]
        base = entries["framed_input.minimap_gate"]
        bundle = upgraded_bundle(self.original,base_va=base,width=3840,height=2160)
        at = pe.inspect_pe(image).file_offset(base-0x400000,len(bundle.code))
        self.assertEqual(image[at:at+len(bundle.code)],bundle.code)
        self.assertEqual(report["stage"],target.STAGE)
        self.assertEqual(report["full_tiles"],[59,33])
        self.assertEqual(len(report["edits"]),2)
        for name in ("game_runtime_executed","manual_input_proof","promotion_ready","parent_probe_reusable"):
            self.assertIs(report[name],False)

    def test_unknown_original_cannot_supply_native_predicates(self):
        with self.assertRaises(ValueError):
            upgraded_bundle(b"unknown executable",base_va=legacy.runner.BASE,width=3840,height=2160)


@unittest.skipUnless(os.name == "nt" and legacy.runner.CSC.is_file() and legacy.runner.ORIGINAL.is_file(),
                     "requires x86 fixture compiler and authenticated original")
class SmallWorldX86Tests(legacy.InputX86Tests):
    """Reuse only the execution harness; preserve all original exclusion cases.

    Native predicates and complete wrappers execute on synthetic memory. The
    inherited harness checks every preserved GPR, ESP, EFLAGS/DF, call order,
    and unchanged game/global/surface memory for each case.
    """
    def execute(self, width, height, cases, delta=0):
        if (width, height) not in self.cache:
            self.cache[width, height] = upgraded_bundle(self.original, base_va=legacy.runner.BASE,
                                                              width=width, height=height)
        with patch.object(legacy, "expected_allowed", expected_allowed):
            reports = super().execute(width, height, cases, delta=delta)
        self.assertEqual(len(reports), len(cases))
        return reports

    def test_4k_50x50_valid_world_edge_and_outside_clicks(self):
        base = dict(map_width=50, map_height=50, scroll_x=0, scroll_y=17)
        points = [(32,16), (64,48), (3200,2096), (3231,2096), (3232,2096), (3807,2000),
                  (100,2127), (100,2128), (31,100), (100,15)]
        rows = [dict(base, raw_x=x, raw_y=y) for x, y in points]
        rows += [base | change for change in (dict(scroll_x=-1), dict(scroll_x=1), dict(scroll_y=-1),
                                              dict(scroll_y=18), dict(map_width=0), dict(map_height=101))]
        reports = self.execute(3840, 2160, self.both(rows))
        self.assertEqual([reports[i*2+1]["state"][0] for i in range(len(points))], [1,1,1,1,0,0,1,0,0,0])

    def test_small_worlds_one_or_both_axes_and_zero_scroll_limit(self):
        rows = []
        for mw, mh in ((1,1), (10,10), (50,50), (100,10), (10,100), (59,33), (100,100)):
            mx, my = max(0, mw-59), max(0, mh-33)
            for sx, sy in ((0,0), (mx,my), (mx+1,my), (mx,my+1), (-1,0), (0,-1)):
                for x,y in ((32,16), (95,79), (96,80), (672,656), (3232,400)):
                    rows.append(dict(map_width=mw, map_height=mh, scroll_x=sx, scroll_y=sy, raw_x=x, raw_y=y))
        self.execute(3840,2160,self.both(rows))

    def test_small_world_partial_tail_and_shifted_rebased_cpu(self):
        rows = [dict(map_width=10,map_height=7,scroll_x=0,scroll_y=0,raw_x=x,raw_y=y)
                for x,y in ((32,16),(671,463),(672,463),(100,464),(769,500))]
        self.execute(802,602,self.both(rows))
        for delta in (0,0x02000000,0x04000000):
            rows = [dict(map_width=50,map_height=50,scroll_x=0,scroll_y=17,shift=s,
                         raw_x=(x << (s & 31)) & 0xFFFFFFFF,raw_y=(y << (s & 31)) & 0xFFFFFFFF)
                    for s in (0,1,6,31,32,33,255) for x,y in ((100,100),(3231,100),(3232,100),(-1,100))]
            self.execute(3840,2160,self.both(rows),delta=delta)


if __name__ == "__main__":
    unittest.main()
