#!/usr/bin/env python3
"""Offline builder integration and output boundaries; no game or debugger.

Actual candidates are constructed only in memory from the optional user-owned
original. CLI file-writing tests substitute explicitly synthetic bytes and map
the private candidate root into a TemporaryDirectory; no game binary is saved.
"""
from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
import ast
import hashlib
import io
import json
from pathlib import Path
import re
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_partial_tile_candidate as builder
from test_pe_extension import independent_image, rebase

ORIGINAL = Path("C:/Clash/clash95.exe")
RESOLUTIONS = ("800x600", "1024x768", "1280x720", "1280x960", "1920x1080", "802x602")
KNOWN_CANDIDATES = {
    "800x600": "b273c16822843d8aa684191e4c2f357e2f7c581bbc3ad7f4175c8d6b057ecae8",
    "1024x768": "b2d0121ee83c6cf861d5a138ca6126acb41a92b6bd43d8129ddd5d357645454e",
}
HOOKS = (("full_converge", 0x4187A0, "833d9069520000"),
         ("full_present", 0x4187B7, "a1fc4c5400"),
         ("incremental", 0x418A90, "535156575583ec08"))
REMOVED = {0x187A2, 0x187B8}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def probe_checks(probe: str):
    """Decode only the generated read-only MASM contract's small grammar."""
    line = next(line for line in probe.splitlines() if "PTILE_CONTRACT_FAIL" in line)
    pattern = r"\((wo|by)\(([0-9a-f]{8})\) != ([0-9a-f]+)\)"
    checks = [(int(va, 16), 2 if reader == "wo" else 1, int(value, 16))
              for reader, va, value in re.findall(pattern, line)]
    if not checks:
        raise AssertionError("missing readable loaded-image conditions")
    residual = re.sub(pattern, "READ", line)
    if not re.fullmatch(r"\.if \(READ(?: \| READ)*\) \{ \.echo PTILE_CONTRACT_FAIL; q \}", residual):
        raise AssertionError("unexpected CDB contract grammar")
    return checks


def run_status_probe(row: str, *, dimensions=(640, 480), pointer=0x12340000,
                     owner=0x40AD40, status=0, gameplay=1,
                     game_data=0x23450000, world=(17, 23), map_size=(100, 100),
                     scroll=(11, 19), esp=0xEDC00, tid=0x3AC,
                     caller=0x40AE5A, vtable=0x50EE24, callbacks=(0, 0, 0),
                     player=0, stack_fields=None):
    """Interpret the emitted probe's bounded conditional grammar offline.

    No CDB is launched. Unlike a duplicate Python state machine, branch order
    and conditions come from the actual emitted command, including printf
    arguments. Null or undeclared memory reads raise immediately. Only
    breakpoint enable/disable state may change; memory/register writes fail.
    """
    match = re.fullmatch(r'bp\d+ [0-9a-f]{8} "(.*)"', row)
    if not match:
        raise AssertionError("unsupported breakpoint command")
    source = match[1].replace(r'\"', '"')
    position = 0

    def whitespace():
        nonlocal position
        while position < len(source) and (source[position].isspace() or source[position] == ";"):
            position += 1

    def block(nested=False):
        nonlocal position
        nodes = []
        while position < len(source):
            whitespace()
            if position == len(source):
                break
            if source[position] == "}":
                if not nested: raise AssertionError("unbalanced closing brace")
                position += 1
                return nodes
            if source.startswith(".if", position):
                position += 3; whitespace()
                if source[position] != "(": raise AssertionError("missing conditional expression")
                start = position+1; depth = 1; position += 1
                while depth:
                    if position >= len(source): raise AssertionError("unterminated condition")
                    if source[position] == "(": depth += 1
                    elif source[position] == ")": depth -= 1
                    position += 1
                condition = source[start:position-1]; whitespace()
                if source[position] != "{": raise AssertionError("missing conditional block")
                position += 1; yes = block(True); whitespace(); no = []
                if source.startswith(".else", position):
                    position += 5; whitespace()
                    if source[position] != "{": raise AssertionError("missing else block")
                    position += 1; no = block(True)
                nodes.append(("if", condition, yes, no))
            else:
                start = position; quoted = False
                while position < len(source):
                    char = source[position]
                    if char == '"': quoted = not quoted
                    if not quoted and char in ";}": break
                    position += 1
                if quoted: raise AssertionError("unterminated printf string")
                nodes.append(("command", source[start:position].strip()))
        if nested: raise AssertionError("unterminated conditional block")
        return nodes

    program = block()
    state = {"events": [], "reads": [], "writes": [], "quit": False,
             "enabled": {70: False, 71: False, 72: False, 73: True, 74: False, 75: False}}
    memory = {0x5202E0: pointer, 0x5199D8: owner, 0x5202E4: game_data,
              0x52698C: callbacks[0], 0x526990: callbacks[1],
              0x526994: callbacks[2], 0x5202EC: player,
              esp + 0x1C: world[0] & 0xFFFFFFFF,
              esp + 0x14: world[1] & 0xFFFFFFFF,
              esp + 0x24: caller}
    memory.update({esp + offset: value & 0xFFFFFFFF
                   for offset, value in (stack_fields or {}).items()})
    if pointer:
        memory[pointer + 0xB8] = vtable
    if game_data:
        memory.update({game_data + offset: value & 0xFFFFFFFF for offset, value in
                       zip((0x222E0, 0x222E4, 0x222E8, 0x222EC), (*map_size, *scroll))})
    before_memory = dict(memory)

    def evaluate(expression):
        tokens = re.findall(r"@\$t14|@\$tid|@eax|@edx|@esp|0n\d+|[0-9][0-9a-f]*|[a-f][0-9a-f]*[0-9][0-9a-f]*|poi|wo|==|!=|>=|<=|[()&|+<>-]|\s+", expression)
        if "".join(tokens) != expression:
            raise AssertionError("unsupported MASM expression")
        converted = []
        for token in tokens:
            if token == "@$t14": converted.append("gameplay")
            elif token == "@$tid": converted.append("tid")
            elif token == "@eax": converted.append("status")
            elif token == "@edx": converted.append("world_y")
            elif token == "@esp": converted.append("esp")
            elif token.startswith("0n"): converted.append(str(int(token[2:])))
            elif re.fullmatch(r"[0-9a-f]+", token): converted.append(str(int(token, 16)))
            else: converted.append(token)

        def visit(node):
            if isinstance(node, ast.Constant) and type(node.value) is int: return node.value
            if isinstance(node, ast.Name):
                return {"gameplay": gameplay, "status": status, "esp": esp,
                        "tid": tid, "world_y": world[1]}[node.id]
            if isinstance(node, ast.BinOp):
                left, right = visit(node.left), visit(node.right)
                if isinstance(node.op, ast.BitAnd): return left & right
                if isinstance(node.op, ast.BitOr): return left | right
                if isinstance(node.op, ast.Add): return left + right
                if isinstance(node.op, ast.Sub): return left - right
            if isinstance(node, ast.Compare) and len(node.ops) == 1:
                left, right = visit(node.left), visit(node.comparators[0])
                if isinstance(node.ops[0], ast.Eq): return int(left == right)
                if isinstance(node.ops[0], ast.NotEq): return int(left != right)
                if isinstance(node.ops[0], ast.Lt): return int(left < right)
                if isinstance(node.ops[0], ast.LtE): return int(left <= right)
                if isinstance(node.ops[0], ast.Gt): return int(left > right)
                if isinstance(node.ops[0], ast.GtE): return int(left >= right)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and len(node.args) == 1:
                address = visit(node.args[0]); state["reads"].append((node.func.id, address))
                if node.func.id == "poi":
                    if address not in memory:
                        raise AssertionError(f"invalid or null dword dereference: {address:08x}")
                    return memory[address]
                if node.func.id == "wo" and pointer and address in (pointer, pointer+2):
                    return dimensions[(address-pointer)//2]
                raise AssertionError("invalid or null surface dereference")
            raise AssertionError("unsupported condition AST")

        return visit(ast.parse("".join(converted), mode="eval").body)

    def execute(nodes):
        for node in nodes:
            if state["quit"]: return
            if node[0] == "if": execute(node[2] if evaluate(node[1]) else node[3])
            else:
                command = node[1]
                if command == "q": state["quit"] = True
                elif command == "gc": pass
                elif command.startswith(".echo "): state["events"].append(command[6:])
                elif command.startswith('.printf "'):
                    quoted = re.fullmatch(r'\.printf "(.*?)", (.*)', command)
                    if not quoted: raise AssertionError("unsupported printf grammar")
                    fmt, arguments = quoted.groups()
                    values = iter(evaluate(arg.strip()) for arg in arguments.split(","))
                    def format_value(match):
                        spec, value = match[0], next(values)
                        if spec == "%p": return f"{value & 0xFFFFFFFF:08x}"
                        if spec.endswith("x"): return spec % (value & 0xFFFFFFFF)
                        if value & 0x80000000: value = (value & 0xFFFFFFFF) - 0x100000000
                        return spec % value
                    rendered = re.sub(r"%0?\d*[dxp]", format_value, fmt)
                    if next(values, None) is not None or "%" in rendered:
                        raise AssertionError("printf format/argument mismatch")
                    state["events"].append(rendered.removesuffix(r"\\n"))
                elif re.fullmatch(r"b[ed] 7[0-5]", command):
                    state["enabled"][int(command[3:])] = command[1] == "e"
                else: raise AssertionError("unsupported or mutating debugger command: "+command)
    execute(program)
    if memory != before_memory:
        raise AssertionError("observation probe changed memory")
    return state


@unittest.skipUnless(ORIGINAL.is_file(), "requires user-owned original for byte construction")
class ConstructionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = ORIGINAL.read_bytes()
        cls.before_sha = digest(cls.original)
        cls.results = {resolution: builder.build_candidate(cls.original, resolution)
                       for resolution in RESOLUTIONS}

    def test_diagnostic_only_changes_preserve_known_candidate_images(self):
        for resolution, expected in KNOWN_CANDIDATES.items():
            self.assertEqual(digest(self.results[resolution][0]), expected)
        self.assertEqual(digest(ORIGINAL.read_bytes()), self.before_sha)

    def test_six_resolutions_have_exact_hooks_and_additive_rx_allocation(self):
        _, original_sections, original_fixups, _ = independent_image(self.original)
        self.assertEqual(len(original_fixups), 32435)
        for resolution, (image, metadata, _) in self.results.items():
            with self.subTest(resolution=resolution):
                profile = builder.patcher.parse_resolution(resolution)
                recipe = builder.patcher.select_patches_for(builder.BASE_STAGE, profile)
                combined = builder.patcher.apply_patches(self.original, recipe)
                bundle = builder.hooks.emit_hook_bundle(self.original, combined,
                    base_va=0x562000, width=profile.width, height=profile.height)
                memory, sections, fixups, _ = independent_image(image)
                combined_memory, _, _, _ = independent_image(combined)
                self.assertEqual(sections[:-1], original_sections)
                self.assertEqual(sections[-1][0], b".hdcode")
                self.assertEqual(sections[-1][1], 0x162000)
                self.assertEqual(sections[-1][-1], 0x60000020)
                self.assertFalse(sections[-1][-1] & 0x80000000, "code section must not be writable")
                self.assertEqual(memory[0x162000:0x162000+len(bundle.code)], bundle.code)
                for name, va, old_hex in HOOKS:
                    rva = va - 0x400000
                    old = bytes.fromhex(old_hex)
                    self.assertEqual(combined_memory[rva:rva+len(old)], old)
                    self.assertEqual(memory[rva], 0xE9)
                    target = va + 5 + struct.unpack_from("<i", memory, rva+1)[0]
                    self.assertEqual(target, bundle.entries["hook_"+name])
                    self.assertEqual(memory[rva+5:rva+len(old)], b"\x90"*(len(old)-5))
                    self.assertTrue(0x562000 <= target < 0x562000+len(bundle.code))
                    self.assertEqual(metadata["status_vas"][name], bundle.status_vas[name])
                declared = {0x162000+r.offset for r in bundle.relocations if r.kind == "abs32"}
                self.assertEqual(len(declared), 115)
                self.assertEqual(set(fixups), (set(original_fixups)-REMOVED) | declared)
                self.assertEqual(len(fixups), len(set(fixups)), "duplicate HIGHLOW entry")
                self.assertEqual(set(original_fixups)-set(fixups), REMOVED)
                self.assertEqual({r["rva"] for r in metadata["removed_highlow"]}, REMOVED)
                self.assertEqual(metadata["retained_highlow_count"], 32433)
                self.assertEqual(metadata["new_highlow_count"], 115)
                self.assertEqual(metadata["output_sha256"], digest(image))
                self.assertEqual(metadata["input_sha256"], digest(combined))
                self.assertEqual(metadata["stage"], builder.STAGE)
                self.assertNotEqual(metadata["stage"], builder.patcher.DEFAULT_STAGE)
                self.assertTrue(metadata["stage"].endswith("-partialtiles-validation"))
                self.assertEqual(metadata["resolution"], resolution)
                self.assertFalse(metadata["runtime_executed"])
                self.assertFalse(metadata["promotion_ready"])
                self.assertFalse(metadata["installation_ready"])
                self.assertTrue(metadata["validation_stage_only"])
                self.assertEqual(metadata["installed_hook_names"], [item[0] for item in HOOKS])
        self.assertEqual(digest(ORIGINAL.read_bytes()), self.before_sha)

    def test_edit_records_reconstruct_all_bytes_without_unreported_changes(self):
        for resolution, (image, metadata, _) in self.results.items():
            with self.subTest(resolution=resolution):
                rebuilt = bytearray(self.original)
                for item in metadata["selected_patches"]:
                    offset = item["offset"]
                    old, new = bytes.fromhex(item["old_hex"]), bytes.fromhex(item["new_hex"])
                    self.assertEqual(rebuilt[offset:offset+len(old)], old)
                    rebuilt[offset:offset+len(old)] = new
                self.assertEqual(digest(rebuilt), metadata["input_sha256"])
                combined = bytes(rebuilt)
                for edit in metadata["edits"]:
                    offset = edit["offset"]
                    old, new = bytes.fromhex(edit["old_hex"]), bytes.fromhex(edit["new_hex"])
                    self.assertEqual(edit["va"], 0x400000+edit["rva"])
                    self.assertEqual(rebuilt[offset:offset+len(old)], old)
                    if not old:
                        self.assertEqual(offset, len(rebuilt), "append must not insert into existing bytes")
                    rebuilt[offset:offset+len(old)] = new
                self.assertEqual(bytes(rebuilt), image)
                # Every original section byte is preserved except the exact
                # three new hook spans. Headers and appended storage are separate.
                before, sections, _, _ = independent_image(combined)
                after, _, _, _ = independent_image(image)
                for _, va, old_hex in HOOKS:
                    rva = va-0x400000
                    after[rva:rva+len(bytes.fromhex(old_hex))] = before[rva:rva+len(bytes.fromhex(old_hex))]
                for _, rva, size, *_ in sections:
                    self.assertEqual(after[rva:rva+size], before[rva:rva+size])

    def test_independent_loader_rebase_keeps_jumps_relative_and_moves_explicit_pointers(self):
        for resolution, (image, metadata, _) in self.results.items():
            memory, _, fixups, _ = independent_image(image)
            for delta in (0x02000000, -0x100000):
                moved = rebase(memory, fixups, delta)
                for name, va, old_hex in HOOKS:
                    rva = va-0x400000
                    self.assertEqual(moved[rva:rva+len(bytes.fromhex(old_hex))], memory[rva:rva+len(bytes.fromhex(old_hex))])
                    target = va+delta+5+struct.unpack_from("<i", moved, rva+1)[0]
                    baseline_target = va+5+struct.unpack_from("<i", memory, rva+1)[0]
                    self.assertEqual(target, baseline_target+delta, (resolution, name))
                for relocation in metadata["relocations"]:
                    rva = metadata["code_rva"]+relocation["offset"]
                    actual = struct.unpack_from("<I", moved, rva)[0]
                    if relocation["kind"] == "abs32":
                        self.assertEqual(actual, (relocation["target"]+delta) & 0xFFFFFFFF)
                    else:
                        self.assertEqual(moved[rva:rva+4], memory[rva:rva+4])

    def test_probe_checks_real_loaded_headers_and_every_installed_hook_byte(self):
        for resolution, (image, metadata, probe) in self.results.items():
            with self.subTest(resolution=resolution):
                memory, _, _, _ = independent_image(image)
                checks = probe_checks(probe)
                self.assertTrue(all(int.from_bytes(memory[va-0x400000:va-0x400000+size], "little") == expected
                                    for va, size, expected in checks))
                guarded = set().union(*(set(range(va, va+size)) for va, size, _ in checks))
                for _, va, old_hex in HOOKS:
                    self.assertTrue(set(range(va, va+len(bytes.fromhex(old_hex)))) <= guarded)
                # Independent mutation oracle: every checked loaded byte can
                # trigger rejection, including single-byte jump padding.
                for va in guarded:
                    changed = bytearray(memory); changed[va-0x400000] ^= 1
                    self.assertTrue(any(int.from_bytes(changed[p-0x400000:p-0x400000+n], "little") != value
                                        for p, n, value in checks))
                self.assertLess(probe.index("PTILE_CONTRACT_FAIL"), probe.index("bp70 "))
                self.assertIn(f"stage={builder.STAGE} resolution={resolution} candidate_sha256={digest(image)}", probe)
                self.assertIn("manual_input_proof=false promotion_ready=false", probe)
                rows = [line for line in probe.splitlines() if line.startswith("bp")]
                self.assertEqual(len(rows), 6)
                for number, (name, va) in enumerate(metadata["status_vas"].items(), 70):
                    row = next(line for line in rows if line.startswith(f"bp{number} "))
                    self.assertTrue(row.startswith(f'bp{number} {va:08x} ".if (@$t14 != 0) {{ '))
                    self.assertIn(f"PTILE_STATUS hook={name} status=%d tid=%x esp=%p", row)
                    self.assertIn(r'\\n\", @eax, @$tid, @esp', row)
                    predicate = "(@eax != 1) & (@eax != 2)" if name == "incremental" else "@eax != 1"
                    if name == "incremental":
                        self.assertIn(f".if ({predicate}) {{ .if (", row)
                        self.assertIn(".else { .echo PTILE_REJECT incremental; q }", row)
                    else:
                        self.assertIn(f".if ({predicate}) {{ .echo PTILE_REJECT {name}; q }}", row)
                    self.assertTrue(row.endswith('; }; gc"'))
                    self.assertEqual(row.count(r'\"'), 4 if name == "incremental" else 2,
                                     "inner printf quoting differs")
                self.assertIsNone(re.search(r"(?:^|[;{])\s*(?:e[bdwq]|r\s+(?:eip|esp|eax))\b", probe),
                                  "observation probe must not force memory or input/callback state")

    def test_emitted_ready_entry_arms_observers_only_for_initialized_hd_map(self):
        for resolution, (_, _, probe) in self.results.items():
            requested = tuple(map(int, resolution.split("x")))
            ready_row = next(line for line in probe.splitlines() if line.startswith("bp73 "))
            self.assertIn('bd 70; bd 71; bd 72; bd 74; bd 75\nbp73 ', probe)
            ready = run_status_probe(ready_row, dimensions=requested)
            self.assertFalse(ready["quit"])
            self.assertEqual(ready["enabled"], {70: True, 71: True, 72: True, 73: False, 74: True, 75: True})
            self.assertEqual(len(ready["events"]), 1)
            self.assertTrue(ready["events"][0].startswith("PTILE_MAP_READY "))
            self.assertEqual(ready["writes"], [])
            for dims, owner in (((640, 480), 0x4617A0), (requested, 0x4617A0),
                                ((requested[0], 480), 0x40AD40), ((640, requested[1]), 0x40AD40)):
                rejected = run_status_probe(ready_row, dimensions=dims, owner=owner)
                self.assertTrue(rejected["quit"])
                self.assertEqual(rejected["events"], ["PTILE_REJECT map_ready_owner_or_dimensions"])
                self.assertFalse(any(rejected["enabled"][bp] for bp in (70, 71, 72, 74, 75)))
            null = run_status_probe(ready_row, pointer=0)
            self.assertTrue(null["quit"])
            self.assertFalse(any(reader == "wo" for reader, _ in null["reads"]))
            for row in (line for line in probe.splitlines() if re.match(r"bp7[0-2] ", line)):
                name = re.search(r"PTILE_STATUS hook=(\w+)", row)[1]
                for status in (0, 1, 2, 3, -1):
                    hd = run_status_probe(row, dimensions=requested, status=status)
                    self.assertEqual(hd["writes"], [])
                    status_index = 1 if name == "incremental" else 0
                    self.assertTrue(hd["events"][status_index].startswith("PTILE_STATUS "))
                    self.assertEqual(hd["quit"], status not in ((1, 2) if name == "incremental" else (1,)))
                null = run_status_probe(row, pointer=0)
                self.assertTrue(null["quit"])
                self.assertEqual(null["events"], ["PTILE_REJECT null_surface"])
                self.assertFalse(any(method == "wo" for method, _ in null["reads"]))
                for wrong in ((320, 200), (640, 480), (requested[0], 480), (640, requested[1])):
                    rejected = run_status_probe(row, dimensions=wrong, status=1)
                    self.assertTrue(rejected["quit"])
                    self.assertEqual(rejected["events"], ["PTILE_REJECT unexpected_surface_size"])
                inactive = run_status_probe(row, pointer=0, gameplay=0)
                self.assertEqual(inactive["events"], [])
                self.assertEqual(inactive["reads"], [])
                self.assertEqual(inactive["writes"], [])

    def test_readiness_join_bytes_are_checked_and_no_header_scratch_is_used(self):
        image, metadata, probe = self.results["800x600"]
        parsed = builder.pe.inspect_pe(image)
        section_table_end = parsed.optional_offset+224+len(parsed.sections)*40
        self.assertLessEqual(section_table_end, 0x300)
        self.assertGreaterEqual(parsed.headers_size, 0x304)
        self.assertEqual(image[0x300:0x304], bytes(4))
        guarded = set().union(*(set(range(va, va+size)) for va, size, _ in probe_checks(probe)))
        self.assertTrue(set(range(0x40B88A, 0x40B88F)) <= guarded)
        self.assertNotIn("ed 00400300", probe)
        combined = builder.patcher.apply_patches(self.original, builder.patcher.select_patches_for(
            builder.BASE_STAGE, builder.patcher.parse_resolution("800x600")))
        bundle = builder.hooks.emit_hook_bundle(self.original, combined, base_va=metadata["code_va"], width=800, height=600)
        offset = builder.clip.file_offset(image, 0x40B88A, 5)
        for at in range(offset, offset + 5):
            changed = bytearray(image); changed[at] ^= 1
            with self.assertRaisesRegex(ValueError, "readiness join changed"):
                builder.make_probe(bytes(changed), bundle)

    def test_incremental_observation_uses_saved_caller_frame_and_precedes_strict_status(self):
        # Derive the offsets from PUSHFD followed by x86 PUSHAD, independently
        # of the emitted printf. The helper has returned at the status site,
        # leaving this frame intact and EAX holding its status instead of X.
        registers = dict(eax=77, ecx=0x11223344, edx=83, ebx=0x55667788,
                         ebp=0x99AABBCC, esi=0x13572468, edi=0x24681357)
        entry_esp, return_address = 0x800000, 0x40AE5A
        stack = {entry_esp: return_address}
        top = entry_esp - 4
        stack[top] = 0x202
        registers["esp"] = top
        for reg in ("eax", "ecx", "edx", "ebx", "esp", "ebp", "esi", "edi"):
            top -= 4
            stack[top] = registers[reg]
        self.assertEqual(stack[top + 0x1C], 77)
        self.assertEqual(stack[top + 0x14], 83)
        self.assertEqual(stack[top + 0x24], return_address)

        for resolution, (_, _, probe) in self.results.items():
            dims = tuple(map(int, resolution.split("x")))
            row = next(line for line in probe.splitlines() if line.startswith("bp72 "))
            self.assertLess(row.index("PTILE_INCREMENTAL_INPUT"), row.index("PTILE_STATUS"))
            for world, scroll, status in (((77, 83), (11, 19), 1),
                                          ((-1, 100), (-4, 7), 0),
                                          ((0, -1), (40, 60), 2)):
                with self.subTest(resolution=resolution, world=world, status=status):
                    observed = run_status_probe(row, dimensions=dims, status=status,
                        world=world, scroll=scroll, esp=top, tid=0x49C,
                        caller=return_address, game_data=0x23450000,
                        map_size=(99, 97), vtable=0x50EE24)
                    self.assertEqual(observed["events"][0],
                        f"PTILE_INCREMENTAL_INPUT tid=49c esp={top:08x} "
                        f"world=({world[0]},{world[1]}) caller=0040ae5a gd=23450000 "
                        f"map=(99,97) scroll=({scroll[0]},{scroll[1]}) vtable=0050ee24")
                    self.assertTrue(observed["events"][1].startswith(
                        f"PTILE_STATUS hook=incremental status={status} tid=49c esp={top:08x} "))
                    self.assertEqual(observed["quit"], status not in (1, 2))
                    if status == 0:
                        self.assertEqual(observed["events"][2], "PTILE_REJECT incremental")
                    else:
                        self.assertEqual(len(observed["events"]), 2)
                    self.assertEqual(observed["writes"], [])
                    self.assertEqual(observed["enabled"], {70: False, 71: False, 72: False, 73: True, 74: False, 75: False})
                    for address in (top + 0x1C, top + 0x14, top + 0x24,
                                    0x234722E0, 0x234722E4, 0x234722E8,
                                    0x234722EC, 0x123400B8):
                        self.assertIn(("poi", address), observed["reads"])
            null = run_status_probe(row, dimensions=dims, status=1, game_data=0)
            self.assertTrue(null["quit"])
            self.assertEqual(null["events"], ["PTILE_REJECT missing_game_data"])
            self.assertIn(("poi", 0x5202E4), null["reads"])
            self.assertFalse(any(address in (0x222E0, 0x222E4, 0x222E8, 0x222EC)
                                 for _, address in null["reads"]))
            self.assertFalse(any(address >= 0x23450000 for _, address in null["reads"]))
            self.assertEqual(null["writes"], [])
            # A mutation added to the observation body must fail the fixture,
            # rather than becoming part of a permissive command interpreter.
            changed = row.replace('.printf \\"PTILE_INCREMENTAL_INPUT',
                                  'ed 005202e4 1; .printf \\"PTILE_INCREMENTAL_INPUT', 1)
            self.assertNotEqual(changed, row)
            with self.assertRaisesRegex(AssertionError, "mutating debugger command"):
                run_status_probe(changed, dimensions=dims, status=1)

    def test_status_zero_is_fatal_for_every_intersecting_full_or_partial_cell(self):
        for resolution, (_, _, probe) in self.results.items():
            width, height = map(int, resolution.split("x"))
            row = next(line for line in probe.splitlines() if line.startswith("bp72 "))
            floor_x, floor_y = (width - 32) // 64, (height - 16) // 64
            ceil_x, ceil_y = (width - 32 + 63) // 64, (height - 16 + 63) // 64
            sx, sy = 11, 19
            xs = {sx - 1, sx, sx + floor_x - 1, sx + floor_x,
                  sx + ceil_x - 1, sx + ceil_x}
            ys = {sy - 1, sy, sy + floor_y - 1, sy + floor_y,
                  sy + ceil_y - 1, sy + ceil_y}
            for wx in sorted(xs):
                for wy in sorted(ys):
                    # Independent pixel-intersection oracle: a tile with even
                    # one gameplay pixel on screen must not be admitted as an
                    # offscreen no-op, including the fractional edge cells.
                    left, top = 32 + (wx - sx) * 64, 16 + (wy - sy) * 64
                    visible = max(left, 32) < min(left + 64, width) and max(top, 16) < min(top + 64, height)
                    actual = run_status_probe(row, dimensions=(width, height),
                                              world=(wx, wy), scroll=(sx, sy), status=0)
                    self.assertEqual(actual["quit"], visible, (resolution, wx, wy))
                    self.assertTrue(actual["events"][0].startswith("PTILE_INCREMENTAL_INPUT "))
                    self.assertTrue(actual["events"][1].startswith("PTILE_STATUS hook=incremental status=0 "))
                    self.assertEqual(len(actual["events"]), 3 if visible else 2)
                    self.assertEqual(actual["writes"], [])
            # Exact native floor-clamped scroll maxima are admitted; one tile
            # past either maximum is invalid even for an offscreen request.
            maximum = (100 - floor_x, 100 - floor_y)
            self.assertFalse(run_status_probe(row, dimensions=(width, height),
                world=(0, 0), scroll=maximum, status=0)["quit"])
            for bad in ((maximum[0] + 1, maximum[1]), (maximum[0], maximum[1] + 1)):
                self.assertTrue(run_status_probe(row, dimensions=(width, height),
                    world=(0, 0), scroll=bad, status=0)["quit"])
            for map_size, world in (((1, 100), (0, 99)), ((100, 1), (99, 0))):
                self.assertFalse(run_status_probe(row, dimensions=(width, height),
                    world=world, map_size=map_size, scroll=(0, 0), status=0)["quit"])
                bad = (1, 0) if map_size[0] == 1 else (0, 1)
                self.assertTrue(run_status_probe(row, dimensions=(width, height),
                    world=world, map_size=map_size, scroll=bad, status=0)["quit"])

    def test_offscreen_zero_rejects_invalid_map_world_scroll_owner_callbacks_and_vtable(self):
        cases = [dict(map_size=(0, 100)), dict(map_size=(101, 100)),
                 dict(map_size=(100, 0)), dict(map_size=(100, 101)),
                 dict(world=(-1, 60)), dict(world=(100, 60)),
                 dict(world=(60, -1)), dict(world=(60, 100)),
                 dict(scroll=(-1, 19)), dict(scroll=(11, -1)),
                 dict(owner=0x4617A0), dict(callbacks=(0x416850, 0, 0)),
                 dict(callbacks=(0, 0x4352B3, 0)), dict(callbacks=(0, 0, 1)),
                 dict(player=1), dict(vtable=0x51E780), dict(vtable=0)]
        for resolution, (_, _, probe) in self.results.items():
            dimensions = tuple(map(int, resolution.split("x")))
            row = next(line for line in probe.splitlines() if line.startswith("bp72 "))
            good = dict(dimensions=dimensions, world=(60, 60), status=0)
            self.assertFalse(run_status_probe(row, **good)["quit"])
            for change in cases:
                with self.subTest(resolution=resolution, change=change):
                    result = run_status_probe(row, **(good | change))
                    self.assertTrue(result["quit"])
                    self.assertEqual(result["events"][-1], "PTILE_REJECT incremental")
                    self.assertEqual(result["writes"], [])
            for status in (3, -1, 0xFFFFFFFF):
                self.assertTrue(run_status_probe(row, **(good | dict(status=status)))["quit"])
            # Null GD must quit in the outer nested guard before the new
            # non-short-circuit MASM predicate could dereference its fields.
            null = run_status_probe(row, **(good | dict(game_data=0)))
            self.assertEqual(null["events"], ["PTILE_REJECT missing_game_data"])
            self.assertFalse(any(address in (0x222E0, 0x222E4, 0x222E8, 0x222EC)
                                 for _, address in null["reads"]))

    def test_native_exit_and_composition_guard_emit_unmodified_context_and_reject_bad_guard(self):
        for resolution, (_, _, probe) in self.results.items():
            dimensions = tuple(map(int, resolution.split("x")))
            native = next(line for line in probe.splitlines() if line.startswith("bp74 "))
            guard = next(line for line in probe.splitlines() if line.startswith("bp75 "))
            self.assertTrue(native.startswith('bp74 00418afa "'))
            # Native fallback saves five registers + eight local bytes. It
            # reaches the epilogue with raw EAX/EDX and caller at ESP+28.
            exit_state = run_status_probe(native, dimensions=dimensions,
                world=(60, 70), status=60, esp=0x800000, tid=0x49C,
                stack_fields={28: 0x40AE5A})
            self.assertEqual(exit_state["events"], [
                "PTILE_NATIVE_NOOP_EXIT tid=49c esp=00800000 world=(60,70) "
                "caller=0040ae5a gd=23450000 map=(100,100) scroll=(11,19) vtable=0050ee24"])
            self.assertFalse(exit_state["quit"])
            self.assertEqual(exit_state["writes"], [])
            for null, reason in ((dict(game_data=0), "noop_missing_game_data"),
                                 (dict(pointer=0), "noop_null_surface")):
                result = run_status_probe(native, **null)
                self.assertTrue(result["quit"])
                self.assertEqual(result["events"], ["PTILE_REJECT " + reason])
                self.assertFalse(any(address in (0x222E0, 0x222E4, 0x222E8, 0x222EC)
                                     for _, address in result["reads"]))
            frame = {112: 60, 104: 70, 36: 49, 24: 51, 12: 1, 120: 0x40AE5A}
            for status in (0, 1, 2, -1):
                result = run_status_probe(guard, status=status, esp=0x700000,
                                          tid=0x49C, stack_fields=frame)
                self.assertEqual(result["events"][0],
                    f"PTILE_COMPOSITION_GUARD tid=49c esp=00700000 status={status} "
                    "world=(60,70) cell=(49,51) present=1 caller=0040ae5a")
                self.assertEqual(result["quit"], status != 1)
                self.assertEqual(result["writes"], [])
                if status != 1:
                    self.assertEqual(result["events"][-1], "PTILE_REJECT composition_guard")

    def test_noop_native_path_and_guard_return_instruction_contracts_are_complete(self):
        for resolution, (image, metadata, probe) in self.results.items():
            combined = builder.patcher.apply_patches(self.original, builder.patcher.select_patches_for(
                builder.BASE_STAGE, builder.patcher.parse_resolution(resolution)))
            width, height = map(int, resolution.split("x"))
            bundle = builder.hooks.emit_hook_bundle(self.original, combined,
                base_va=metadata["code_va"], width=width, height=height)
            guard_start = bundle.entries["cell_composed"]
            guarded = set().union(*(set(range(va, va + size)) for va, size, _ in probe_checks(probe)))
            self.assertTrue(set(range(0x418A98, 0x418B03)) <= guarded)
            self.assertTrue(set(range(guard_start, guard_start + 15)) <= guarded)
            prefix_offset = builder.clip.file_offset(image, guard_start, 15)
            prefix = image[prefix_offset:prefix_offset + 15]
            self.assertEqual(prefix[:8], bytes.fromhex("6089e583ec0455e8"))
            self.assertEqual(prefix[12:], bytes.fromhex("5d85c0"))
            self.assertEqual(guard_start + 12 + struct.unpack_from("<i", prefix, 8)[0],
                             bundle.entries["composition_guard"])
            self.assertIn(f"bp75 {guard_start + 12:08x} ", probe)
            # Every byte that determines the observer boundary or its direct
            # callee is checked before the generated probe is returned.
            for relative in range(15):
                changed = bytearray(image)
                changed[prefix_offset + relative] ^= 1
                with self.assertRaisesRegex(ValueError, "composition guard call changed"):
                    builder.make_probe(bytes(changed), bundle)
            epilogue = builder.clip.file_offset(image, 0x418AFA, 9)
            for relative in range(9):
                changed = bytearray(image)
                changed[epilogue + relative] ^= 1
                with self.assertRaisesRegex(ValueError, "incremental epilogue changed"):
                    builder.make_probe(bytes(changed), bundle)
            self.assertTrue(all(len(line) < 4096 for line in probe.splitlines()))

    def test_actual_cli_preflight_builds_only_in_memory_even_with_output_arguments(self):
        with tempfile.TemporaryDirectory(prefix="clash-partial-preflight-") as name:
            temp = Path(name)
            argv = ["build_partial_tile_candidate.py", "--original", str(ORIGINAL),
                    "--resolution", "800x600", "--preflight", "--output", str(temp/"no.exe"),
                    "--report-json", str(temp/"no.json"), "--probe-out", str(temp/"no.cdb")]
            output = io.StringIO()
            with patch.object(sys, "argv", argv), redirect_stdout(output), redirect_stderr(io.StringIO()):
                self.assertEqual(builder.main(), 0)
            result = json.loads(output.getvalue())
            self.assertTrue(result["preflight_passed"])
            self.assertFalse(result["runtime_executed"])
            self.assertEqual(result["candidate_sha256"], digest(self.results["800x600"][0]))
            self.assertEqual(list(temp.iterdir()), [])

    def test_source_identity_original_and_canonical_resolution_fail_closed(self):
        with tempfile.TemporaryDirectory(prefix="clash-builder-sources-") as name:
            root = Path(name)
            for relative in builder.PINNED_SOURCES:
                target = root/relative; target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes((builder.ROOT/relative).read_bytes())
            for relative in builder.PINNED_SOURCES:
                target = root/relative; old = target.read_bytes(); target.write_bytes(old+b"\n# fixture mutation\n")
                with patch.object(builder, "ROOT", root), self.assertRaisesRegex(ValueError, "reviewed source changed"):
                    builder.build_candidate(self.original, "800x600")
                target.write_bytes(old)
        changed = bytearray(self.original); changed[0x1000] ^= 1
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            builder.build_candidate(bytes(changed), "800x600")
        for resolution in ("0800x0600", "800X600", "800x600 ", "799x600"):
            with self.subTest(resolution=resolution), self.assertRaises(ValueError):
                builder.build_candidate(self.original, resolution)


class CLIBoundaryTests(unittest.TestCase):
    def invoke(self, original, output, report, probe):
        argv = ["build_partial_tile_candidate.py", "--original", str(original),
                "--output", str(output), "--resolution", "800x600",
                "--report-json", str(report), "--probe-out", str(probe)]
        with patch.object(sys, "argv", argv), redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            return builder.main()

    def test_unsafe_and_existing_outputs_are_rejected_before_build_or_input_read(self):
        with tempfile.TemporaryDirectory(prefix="clash-builder-boundary-") as name:
            temp = Path(name); missing_original = temp/"does-not-exist.exe"
            candidate = Path("C:/ClashTests")/temp.name/"candidate.exe"
            report, probe = temp/"report.json", temp/"probe.cdb"
            existing = temp/"existing.json"; existing.write_bytes(b"preserve me")
            cases = ((candidate, report, report), (candidate, missing_original, probe),
                     (builder.ROOT/"candidate.exe", report, probe),
                     (candidate, builder.ROOT/"report.json", probe),
                     (candidate, report, builder.ROOT/"probe.cdb"),
                     (temp/"candidate.exe", report, probe),
                     (Path("C:/ClashTests/../Clash/candidate.exe"), report, probe),
                     (candidate.with_suffix(".dll"), report, probe),
                     (candidate, existing, probe))
            with patch.object(builder, "build_candidate", side_effect=AssertionError("unsafe output reached build")) as build:
                for output, metadata, template in cases:
                    with self.subTest(output=str(output), report=str(metadata), probe=str(template)):
                        with self.assertRaises(SystemExit) as result:
                            self.invoke(missing_original, output, metadata, template)
                        self.assertEqual(result.exception.code, 2)
                build.assert_not_called()
            self.assertEqual(existing.read_bytes(), b"preserve me")
            self.assertFalse(report.exists()); self.assertFalse(probe.exists())

    def test_exclusive_creation_and_race_preserve_existing_synthetic_artifacts(self):
        with tempfile.TemporaryDirectory(prefix="clash-builder-exclusive-") as name:
            temp = Path(name); private = temp/"private-candidates"
            original = temp/"synthetic-source.bin"; original.write_bytes(b"synthetic source, not game bytes")
            output, report, probe = private/"candidate.exe", temp/"report.json", temp/"probe.cdb"
            real_path = Path

            def fixture_path(value):
                return private if str(value) == "C:/ClashTests" else real_path(value)

            value = (b"synthetic non-PE candidate", {"installed_hook_names": [x[0] for x in HOOKS]},
                     ".echo synthetic fixture; no runtime\n")
            with patch.object(builder, "Path", side_effect=fixture_path), patch.object(builder, "build_candidate", return_value=value) as build:
                self.assertEqual(self.invoke(original, output, report, probe), 0)
                build.assert_called_once_with(original.read_bytes(), "800x600")
                self.assertEqual(output.read_bytes(), value[0])
                self.assertEqual(json.loads(report.read_text()), value[1])
                self.assertEqual(probe.read_text(), value[2])
                with self.assertRaises(SystemExit):
                    self.invoke(original, output, report, probe)
                self.assertEqual(build.call_count, 1)
            other = private/"raced.exe"; other_report, other_probe = temp/"race.json", temp/"race.cdb"

            def race(*_):
                other.write_bytes(b"owned by concurrent fixture")
                return value

            with patch.object(builder, "Path", side_effect=fixture_path), patch.object(builder, "build_candidate", side_effect=race):
                with self.assertRaises(FileExistsError):
                    self.invoke(original, other, other_report, other_probe)
            self.assertEqual(other.read_bytes(), b"owned by concurrent fixture")
            self.assertFalse(other_report.exists()); self.assertFalse(other_probe.exists())
            self.assertEqual(original.read_bytes(), b"synthetic source, not game bytes")


if __name__ == "__main__":
    unittest.main()
