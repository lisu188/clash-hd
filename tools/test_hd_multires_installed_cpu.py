#!/usr/bin/env python3
"""Optional original-backed CPU checks of all twelve installed HD candidates.

The PE is independently loaded/rebased in RAM. Installed full/incremental
hooks, cell clipping and mouse guards execute; native Tile/fill/minimap,
presentation and click returns are explicit models. No game process, native
decoder, pixel rendering, input device, output executable or release proof is
supplied. Default checks are source/synthetic only and never open the original.
"""
from __future__ import annotations

import argparse
import ast
from datetime import datetime, timezone
import gc
import hashlib
import json
from pathlib import Path
import struct
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "tools")]
from src.patcher import hd_multires_candidate as candidate
from src.patcher import partial_tile_clip as clip
from src.patcher import framed_input as inputs
from test_pe_extension import independent_image, rebase, synthetic_pe

ORIGINAL = None
CELLS = tuple((p, r) for p in candidate.PROFILES for r in candidate.RESOLUTIONS)
SELECTED = CELLS
ROWS = []
FALSE_CLAIMS = ("game_runtime_executed", "native_tile_executed", "native_fill_executed",
    "native_callback_abi_verified", "pixel_rendering_verified", "manual_input_proof",
    "endurance_completed", "release_accepted", "promotion_ready")


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def geometry(profile, resolution):
    width, height = map(int, resolution.split("x"))
    right, bottom = (width - 1, height - 1) if profile == "classic" else (width - 33, height - 17)
    full = ((right + 1 - 32) // 64, (bottom + 1 - 16) // 64)
    cover = ((right + 1 - 32 + 63) // 64, (bottom + 1 - 16 + 63) // 64)
    return width, height, right, bottom, full, cover


def parts(metadata):
    """Only the fixed predecessor links; aliases/cycles never select a node."""
    nodes, seen, current = [], set(), metadata
    for _ in range(24):
        if type(current) is not dict or id(current) in seen:
            raise ValueError("invalid installed-candidate predecessor chain")
        nodes.append(current); seen.add(id(current))
        links = [current[k] for k in ("predecessor", "base_candidate", "parent_build")
                 if type(current.get(k)) is dict]
        if len(links) > 1:
            raise ValueError("ambiguous installed-candidate predecessor chain")
        if not links:
            return nodes
        current = links[0]
    raise ValueError("installed-candidate predecessor depth exceeds bound")


class Machine:
    """PE bytes stay intact; CODE callbacks model only named dependencies."""
    HEAP, HEAP_SIZE = 0x10000000, 0xA0000
    STACK, STACK_SIZE, STOP = 0x20000000, 0x10000, 0x30000000
    GD, SURFACE, PIXELS, BUTTON = HEAP, HEAP + 0x90000, HEAP + 0x91000, HEAP + 0x92000

    def __init__(self, image, metadata, *, delta=0):
        import unicorn as u
        from unicorn import x86_const as x
        self.u, self.delta = u, delta
        self.cpu = u.Uc(u.UC_ARCH_X86, u.UC_MODE_32)
        self.regs = {n: getattr(x, "UC_X86_REG_" + n) for n in
            ("EAX", "EBX", "ECX", "EDX", "ESI", "EDI", "EBP", "ESP", "EFLAGS", "EIP")}
        self.profile, self.resolution = metadata["profile"], metadata["resolution"]
        self.width, self.height, self.right, self.bottom, self.full, self.cover = geometry(self.profile, self.resolution)
        self.capability = metadata["bounded_world"]
        nodes = parts(metadata)
        framed = [n for n in nodes if n.get("schema") == "clash95_pe_extension_v1" and n.get("framed_validation") is True]
        self.entries = {} if self.profile == "classic" else framed[0]["entry_vas"]
        self.helper = self.capability["helper"]["entries"]
        memory, sections, fixups, _ = independent_image(image)
        self.loaded = bytes(rebase(memory, fixups, delta))
        self.base = 0x400000 + delta
        self.cpu.mem_map(self.base, len(self.loaded)); self.cpu.mem_write(self.base, self.loaded)
        self.code_ranges = [(self.base + rva, raw_size) for _, rva, _, _, raw_size, flags in sections if flags & 0x20000000]
        for address, size in ((self.HEAP, self.HEAP_SIZE), (self.STACK, self.STACK_SIZE), (self.STOP, 4096)):
            self.cpu.mem_map(address, size)
        self.events, self.writes = [], []
        self.cpu.hook_add(u.UC_HOOK_CODE, self.observe)
        self.cpu.hook_add(u.UC_HOOK_MEM_WRITE, self.observe_write)
        self.world = (1, 1)
        self.seed()

    def put(self, address, value, size=4):
        self.cpu.mem_write(address, (value & ((1 << (size * 8)) - 1)).to_bytes(size, "little"))

    def word(self, address, size=4):
        return int.from_bytes(self.cpu.mem_read(address, size), "little")

    def glob(self, address, value, size=4):
        self.put(address + self.delta, value, size)

    def reg(self, name):
        return self.cpu.reg_read(self.regs[name])

    def seed(self, *, world=(1, 1), scroll=(0, 0), **options):
        self.world, self.options = world, options
        for address, value in ((clip.GAME_DATA_GLOBAL, self.GD), (clip.MAP_SURFACE_GLOBAL, self.SURFACE),
                (clip.RENDER_DEVICE_GLOBAL, 0x12345000), (clip.RENDER_HOOK_GLOBAL, 0x40AD40 + self.delta),
                (clip.LOWER_ROW_OWNER_GLOBAL, 0), (clip.POST_TILE_CALLBACK_GLOBAL, 0),
                (clip.TILE_CALLBACK_GLOBAL, 0), (clip.CURRENT_PLAYER_GLOBAL, 0),
                (clip.CURSOR_VISIBLE_GLOBAL, 0), (clip.COMMAND_SPRITES_GLOBAL, self.PIXELS),
                (clip.TURN_SPRITES_GLOBAL, self.PIXELS), (clip.TOOLTIP_SURFACE_GLOBAL, 0),
                (0x544D14, self.BUTTON)):
            self.glob(address, value)
        for offset, value in zip((0x222E0, 0x222E4, 0x222E8, 0x222EC), (*world, *scroll)):
            self.put(self.GD + offset, value)
        self.put(self.GD + 0x23EC7, 0)
        for player in range(5):
            self.put(self.GD + 0x22313 + 1423 * player, 1)
            self.put(self.GD + 0x2230F + 1423 * player, int(options.get("minimap", False)))
        self.put(self.SURFACE, self.width, 2); self.put(self.SURFACE + 2, self.height, 2)
        self.put(self.SURFACE + 4, self.PIXELS)
        self.put(self.SURFACE + 0xB8, clip.MEMORY_VTABLE + self.delta)
        self.glob(inputs.MOUSE_X, options.get("x", 32)); self.glob(inputs.MOUSE_Y, options.get("y", 16))
        self.glob(inputs.MOUSE_SHIFT, options.get("shift", 0), 1)
        self.glob(inputs.MINIMAP_ORIGIN, self.width - 246, 2); self.glob(inputs.MINIMAP_ORIGIN + 2, 16, 2)
        self.glob(inputs.MINIMAP_SIZE, 214, 2); self.glob(inputs.MINIMAP_SIZE + 2, 214, 2)
        self.put(self.BUTTON + 0x2C, options.get("click", 1), 1)

    def return_model(self, value=1, pop=0):
        sp = self.reg("ESP")
        self.cpu.reg_write(self.regs["EAX"], value)
        self.cpu.reg_write(self.regs["ESP"], sp + 4 + pop)
        self.cpu.reg_write(self.regs["EIP"], self.word(sp))

    def observe_write(self, cpu, access, address, size, value, user):
        if not (self.STACK <= address and address + size <= self.STACK + self.STACK_SIZE):
            self.writes.append((address, size, value))

    def observe(self, cpu, pc, size, user):
        if pc == self.stop:
            self.returned = True; cpu.emu_stop(); return
        # Native draw callbacks use the same register/stack contracts as the
        # existing bounded-paint and Classic fixtures. No original body runs.
        targets = {clip.NATIVE_TARGETS[n] + self.delta: n for n in
                   ("tile", "fill", "minimap", "dirty", "blit", "cursor")}
        name = targets.get(pc)
        if name == "tile":
            column, rest = divmod(self.reg("EBX") - self.GD, 1400)
            row, tail = divmod(rest, 14)
            assert tail == 0 and 0 <= column < self.world[0] and 0 <= row < self.world[1]
            self.events.append((name, column, row, self.reg("EAX"), self.reg("EDX")))
        elif name == "fill":
            rect = self.reg("EDX"), self.reg("EBX"), self.reg("ECX"), self.word(self.reg("ESP") + 4)
            assert 32 <= rect[0] <= rect[2] <= self.right and 16 <= rect[1] <= rect[3] <= self.bottom
            self.events.append((name, *rect))
        elif name:
            self.events.append((name,))
        if name:
            self.return_model(pop={"fill": 8, "dirty": 4, "blit": 16}.get(name, 0)); return
        if pc in (inputs.CLICK_GATE + self.delta, inputs.MINIMAP_GATE + self.delta):
            click = pc == inputs.CLICK_GATE + self.delta
            self.events.append(("native_click" if click else "native_minimap",))
            self.return_model(int(bool(self.options.get("click", 1))) if click else int(self.options.get("native_minimap", 0)))
            return
        for name in ("draw_frame", "compose_panel", "present_map_rect"):
            if name in self.entries and pc == self.entries[name] + self.delta:
                self.events.append((name, self.reg("EAX"), self.reg("EBX"), self.reg("ECX"), self.reg("EDX")))
                self.return_model(0 if self.options.get("fail") == name else 1); return

    def invoke(self, kind, *, x=0, y=0, present=0):
        entry = {"full": 0x418700, "incremental": 0x418A90, "click": 0x408039}[kind] + self.delta
        self.stop = entry + 5 if kind == "click" else self.STOP
        self.returned = False; self.events.clear(); self.writes.clear()
        initial = dict(EAX=present if kind == "full" else self.BUTTON if kind == "click" else x,
            EBX=0x22334455, ECX=0x33445566, EDX=y if kind == "incremental" else 0x44556677,
            ESI=0x55667788, EDI=0x66778899, EBP=0x778899AA, ESP=self.STACK + 0xC000, EFLAGS=0xED7)
        self.put(initial["ESP"], self.STOP)
        for name, value in initial.items():
            self.cpu.reg_write(self.regs[name], value & 0xFFFFFFFF)
        self.cpu.emu_start(entry, self.STOP + 1, count=3000000)
        assert self.returned, (kind, hex(self.reg("EIP")))
        actual = {n: self.reg(n) for n in initial}
        assert actual["ESP"] == initial["ESP"] + (0 if kind == "click" else 4)
        for name in ("EBX", "ECX", "EDX", "ESI", "EDI", "EBP"):
            assert actual[name] == initial[name], (kind, name, actual[name], initial[name])
        if kind != "full" or self.profile != "classic":
            assert actual["EFLAGS"] & 0xCD5 == initial["EFLAGS"] & 0xCD5
        allowed = {self.GD + 0x222E8, self.GD + 0x222EC,
                   self.SURFACE + 0xB8, clip.RENDER_DEVICE_GLOBAL + self.delta}
        assert all(size == 4 and address in allowed for address, size, _ in self.writes), (kind, self.writes)
        for va, count in self.code_ranges:
            assert bytes(self.cpu.mem_read(va, count)) == self.loaded[va-self.base:va-self.base+count], "candidate executable bytes changed"
        return actual["EAX"]


class AuthoringTests(unittest.TestCase):
    def test_exact_twelve_geometry_and_synthetic_relocation_loader(self):
        self.assertEqual(len(CELLS), 12)
        for profile, resolution in CELLS:
            width, height, right, bottom, full, cover = geometry(profile, resolution)
            self.assertLessEqual(full[0], cover[0]); self.assertLessEqual(full[1], cover[1])
            self.assertEqual(bottom, height - (1 if profile == "classic" else 17))
            self.assertEqual(right, width - (1 if profile == "classic" else 33))
        memory, _, fields, _ = independent_image(synthetic_pe())
        rebased = rebase(memory, fields, 0x30000)
        for field in fields:
            self.assertEqual(struct.unpack_from("<I", rebased, field)[0], struct.unpack_from("<I", memory, field)[0] + 0x30000)

    def test_ambiguous_and_cyclic_metadata_cannot_select_installed_entries(self):
        with self.assertRaises(ValueError): parts(dict(predecessor={}, base_candidate={}))
        cyclic = {}; cyclic["predecessor"] = cyclic
        with self.assertRaises(ValueError): parts(cyclic)

    def test_fixture_never_reemits_guards_or_starts_a_game(self):
        tree = ast.parse(Path(__file__).read_bytes())
        calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)]
        self.assertFalse(any(n.func.attr.startswith("emit") or n.func.attr in
            ("Popen", "CreateProcessW", "write_bytes", "write_text") for n in calls))


class InstalledTests(unittest.TestCase):
    def test_actual_installed_hooks_small_worlds_partial_edges_scroll_and_input(self):
        original = ORIGINAL.read_bytes()
        self.assertEqual(sha(original), candidate.ORIGINAL_SHA256)
        for profile, resolution in SELECTED:
            image, metadata, probe = candidate.build_candidate(original, resolution, profile=profile)
            self.assertEqual(sha(image), metadata["candidate_sha256"])
            self.assertEqual(sha(probe.encode()), metadata["probe_sha256"])
            sources = dict(metadata["source_hashes"])
            self.assertTrue(all(sha((ROOT / name).read_bytes()) == digest for name, digest in sources.items()))
            for name in ("runtime_verified", "runtime_executed", "manual_input_proof", "promotion_ready"):
                self.assertIs(metadata[name], False)
            del probe
            row = dict(profile=profile, resolution=resolution, bases=[], full_calls=0, incremental_calls=0, input_calls=0)
            for delta in (0, 0x30000):
                m = Machine(image, metadata, delta=delta)
                for world, camera in (((2, 3), (0x7FFFFFFF, -1)),
                                      ((2, 100), (-1, 0x7FFFFFFF))):
                  for present in (0, 1):
                    with self.subTest(profile=profile, resolution=resolution, delta=delta, present=present, world=world):
                        m.seed(world=world, scroll=camera)
                        result = m.invoke("full", present=present)
                        sx, sy = 0, max(0, world[1] - m.full[1]) if camera[1] > 0 else 0
                        self.assertEqual((m.word(m.GD + 0x222E8), m.word(m.GD + 0x222EC)), (sx, sy))
                        tiles = [event for event in m.events if event[0] == "tile"]
                        fills = [event for event in m.events if event[0] == "fill"]
                        wanted = {(sx+x, sy+y) for y in range(m.cover[1]) for x in range(m.cover[0])
                                  if sx+x < world[0] and sy+y < world[1]}
                        self.assertEqual({event[1:3] for event in tiles}, wanted)
                        self.assertEqual(len(tiles), len(wanted))
                        self.assertEqual(len(fills), m.cover[0] * m.cover[1] - len(wanted))
                        self.assertIn(("fill", 32 + 64 * (m.cover[0] - 1), 16 + 64 * (m.cover[1] - 1), m.right, m.bottom), fills)
                        self.assertEqual(m.word(m.SURFACE + 0xB8), clip.MEMORY_VTABLE + delta)
                        if profile != "classic":
                            self.assertEqual(result, 1)
                            self.assertEqual([e[0] for e in m.events][-3:] if present else [e[0] for e in m.events][-2:],
                                ["draw_frame", "compose_panel", "present_map_rect"] if present else ["draw_frame", "compose_panel"])
                        row["full_calls"] += 1
                for point, expected in (((0, 0), 1), ((1, 2), 1), ((2, 0), 2), ((0, 3), 2), ((m.cover[0] - 1, m.cover[1] - 1), 2)):
                    m.seed(world=(2, 3))
                    # The framed installed hook restores its incoming EAX;
                    # helper status1/2 is consumed before POPAD. Classic's
                    # successor explicitly returns that status instead.
                    self.assertEqual(m.invoke("incremental", x=point[0], y=point[1]),
                                     expected if profile == "classic" else point[0])
                    self.assertEqual(bool([e for e in m.events if e[0] == "tile"]), expected == 1)
                    self.assertEqual(bool([e for e in m.events if e[0] == "fill"]), expected == 2)
                    row["incremental_calls"] += 1
                # A real last partial cell is drawn when its world exists;
                # the same screen cell above was explicitly cleared.
                m.seed(world=m.cover)
                corner = (m.cover[0] - 1, m.cover[1] - 1)
                self.assertEqual(m.invoke("incremental", x=corner[0], y=corner[1]),
                                 1 if profile == "classic" else corner[0])
                self.assertEqual([e[1:3] for e in m.events if e[0] == "tile"], [corner])
                self.assertFalse([e for e in m.events if e[0] == "fill"])
                row["incremental_calls"] += 1
                # Actual installed mouse CALL; no complete UI path is executed.
                right, bottom = m.right, m.bottom
                cases = [(32, 16, True), (159, 207, True), (160, 16, False), (32, 208, False),
                    (31, 16, False), (32, 15, False), (right + 1, 16, False), (32, bottom + 1, False)]
                for x, y, allowed in cases:
                    m.seed(world=(2, 3), x=x, y=y)
                    self.assertEqual(m.invoke("click"), int(allowed), (profile, resolution, x, y))
                    self.assertEqual(m.writes, [])
                    row["input_calls"] += 1
                for x, y in (() if profile == "classic" else
                             ((m.width - 224, m.height - 80), (m.width - 33, m.height - 17))):
                    m.seed(world=(100, 100), x=x, y=y)
                    self.assertEqual(m.invoke("click"), 0)
                    row["input_calls"] += 1
                for context in (dict(world=(0, 3)), dict(world=(2, 101)),
                                dict(world=(2, 3), scroll=(1, 0)), dict(world=(2, 3), scroll=(0, -1)),
                                dict(world=(2, 3), x=-1), dict(world=(2, 3), click=0),
                                dict(world=(2, 3), native_minimap=1)):
                    m.seed(**context)
                    self.assertEqual(m.invoke("click"), 0, context)
                    self.assertEqual(m.writes, [])
                    row["input_calls"] += 1
                m.seed(world=(2, 3), x=64, y=32, shift=1)
                self.assertEqual(m.invoke("click"), 1)
                row["input_calls"] += 1
                if profile != "classic":
                    m.seed(world=(100, 100), x=m.width-246, y=16, minimap=True)
                    self.assertEqual(m.invoke("click"), 0)
                    row["input_calls"] += 1
                row["bases"].append(0x400000 + delta)
                del m; gc.collect()
            self.assertTrue(all(sha((ROOT / name).read_bytes()) == digest for name, digest in sources.items()))
            row.update(candidate_sha256=sha(image), passed=True, **{name: False for name in FALSE_CLAIMS})
            row["source_closure_sha256"] = sha(json.dumps(sources, sort_keys=True, separators=(",", ":")).encode())
            ROWS.append(row)
            print(json.dumps(row), flush=True)
            del image, metadata; gc.collect()
        self.assertEqual(ORIGINAL.read_bytes(), original)


def main():
    global ORIGINAL, SELECTED
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original-backed", type=Path)
    parser.add_argument("--cell", action="append", choices=[p + "/" + r for p, r in CELLS])
    parser.add_argument("--report", type=Path, help="write one small exclusive source/model receipt; never executable bytes")
    args = parser.parse_args()
    if args.cell and args.original_backed is None:
        parser.error("--cell requires --original-backed")
    if args.report is not None and args.original_backed is None:
        parser.error("--report requires --original-backed")
    ORIGINAL = args.original_backed
    if args.cell:
        SELECTED = tuple(tuple(value.split("/")) for value in args.cell)
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(AuthoringTests)
    if ORIGINAL is not None:
        suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(InstalledTests))
    fixture_sha = sha(Path(__file__).read_bytes())
    result = unittest.TextTestRunner(verbosity=2, failfast=True).run(suite)
    if sha(Path(__file__).read_bytes()) != fixture_sha:
        raise ValueError("installed-candidate CPU fixture changed during execution")
    if not result.wasSuccessful() or result.skipped:
        return 1
    if args.report is not None:
        report = dict(schema="hd_multires_installed_cpu_fixture_v1", generated_at=datetime.now(timezone.utc).isoformat(),
            fixture_source_sha256=fixture_sha, original_sha256=candidate.ORIGINAL_SHA256,
            expected_cells=[p + "/" + r for p, r in SELECTED], cells=ROWS,
            all_twelve_cells_checked=len(ROWS) == 12 and set(SELECTED) == set(CELLS),
            tests_run=result.testsRun, skipped=0, passed=True,
            limitation="Installed candidate RAM bytes and authored callback models; no native drawing, Windows gameplay, device input, endurance or release acceptance.",
            **{name: False for name in FALSE_CLAIMS})
        with args.report.open("x", encoding="utf-8", newline="\n") as stream:
            json.dump(report, stream, indent=2); stream.write("\n")
    print("Source/synthetic checks only; original not opened." if ORIGINAL is None else
        f"Installed-candidate modeled CPU checks passed for {len(ROWS)} selected cells; no native gameplay/input/release acceptance.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
