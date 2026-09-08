#!/usr/bin/env python3
"""Repo-only contracts for the bounded day diagnostic; never starts game/CDB."""

from __future__ import annotations

import hashlib
import re
import struct
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROBE = ROOT / "probes/cdb/continuity/clash95_continuity_day_diagnostic_extra.cdb"
CAMPAIGN = ROOT / "probes/cdb/continuity/clash95_continuity_campaign_route_extra.cdb"
LOCAL_ASM = Path("C:/Clash/clash95.asm")
LOCAL_ORIGINAL = Path("C:/Clash/clash95.exe")
ORIGINAL_SHA = "500055d77d03d514e8d3168506bd10f67cd8569bcc450604ff8192f46cdaf3ae"
ASM_SHA = "b298e8c85086f542ebc8b02c26904019aa8278d531cbf02a88d785170cbb4436"
CAMPAIGN_SHA = "a0bf5412e371a750b3bc790ebb59ae2957a09ba544f4dc237922a4e9fffc84da"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
import patch_clash95_hd as patcher  # noqa: E402
from render_cdb_surface_probe import BASE_PROBE, render_probe  # noqa: E402

# Native instruction contracts derived from the pinned disassembly. These
# synthetic bytes test the probe's actual predicates; runtime must still pass
# the candidate's complete patch byte gate and these in-process predicates.
NATIVE_BYTES = {
    0x400000: bytes.fromhex("4d5a"), 0x40003C: struct.pack("<I", 0x70),
    0x400070: bytes.fromhex("504500004c010700"),
    0x400084: bytes.fromhex("e000"), 0x400088: bytes.fromhex("0b01"),
    0x4000A4: struct.pack("<I", 0x400000), 0x4000C4: struct.pack("<I", 0x400),
    0x400300: bytes(64),
    0x400340: bytes(16),
    0x40B0C3: bytes.fromhex("e8386c0400"), 0x406FA1: bytes.fromhex("525583ec70"),
    0x40AA60: bytes.fromhex("5351525655"),
    0x40AB2C: bytes.fromhex("3b0dec0252000f8e81000000a1e402520066ff80f6220200a1e4025200"),
    0x40ABB9: bytes.fromhex("a1e4025200"),
    0x40A820: bytes.fromhex("5352565755"),
    0x40A93C: bytes.fromhex("89f0e8ad5f050085c00f85af00000089ea89f0e87c5c0500ebe6"),
    0x40A9FA: bytes.fromhex("b8d84c540031d2e8ca5f0500"),
    0x4608F0: bytes.fromhex("f6402c010f95c025ff000000c3"),
    0x47BFD0: bytes.fromhex("53515283ec6089c3"),
    0x47BFE1: bytes.fromhex("83bb380100000074228d4b34518b430468000100008b1050"),
    0x47BFF9: bytes.fromhex("ff52243d1e000780"),
    0x47C01C: bytes.fromhex("8d542450528b40086a108b0850"),
    0x47C029: bytes.fromhex("ff51243d1e000780"),
    0x4609D0: bytes.fromhex("53515689c189d331f689c8e810ffffff85c0741189f289c8e8e3fbffff85db74e8ffd3ebe489c8e804ffffff85c075e45e595bc3"),
    0x40AA06: bytes.fromhex("ba14000000"),
}


def evaluate(expression: str, memory: dict[int, int], regs: dict[str, int] | None = None) -> int:
    regs = regs or {}
    def literal(match):
        value = match[0]
        if value.startswith("0n"):
            return str(int(value[2:]))
        return str(int(value, 16))
    expression = re.sub(r"\b(?:0n\d+|0x[0-9a-f]+|[0-9][0-9a-f]*|[a-f][0-9a-f]*[0-9][0-9a-f]*)\b", literal, expression)
    expression = re.sub(r"@(\$?\w+)", lambda m: str(regs[m[1]]), expression)
    def read(address, size):
        return sum(memory.get(address+i, 0) << (8*i) for i in range(size))
    return int(eval(expression, {"__builtins__": {}}, {"poi": lambda a: read(a, 4), "wo": lambda a: read(a, 2), "by": lambda a: read(a, 1)}))


def write(memory: dict[int, int], address: int, value: int, size: int = 4):
    for i in range(size):
        memory[address+i] = (value >> (i*8)) & 255


def parse_commands(text: str):
    """Parse the small CDB command subset used here, failing on unknown syntax.

    This executes the probe's actual branch conditions/writes in fixtures; it
    does not pretend to emulate native game routines or debugger execution.
    """
    text = text.replace(r'\"', '"')
    cursor = 0

    def skip():
        nonlocal cursor
        while cursor < len(text) and (text[cursor].isspace() or text[cursor] == ";"):
            cursor += 1

    def enclosed(left, right):
        nonlocal cursor
        skip()
        assert text[cursor] == left, text[cursor:]
        cursor += 1
        start, depth, quoted = cursor, 1, False
        while cursor < len(text):
            char = text[cursor]
            if char == '"' and text[cursor - 1] != "\\":
                quoted = not quoted
            if not quoted:
                depth += (char == left) - (char == right)
                if depth == 0:
                    result = text[start:cursor]
                    cursor += 1
                    return result
            cursor += 1
        raise AssertionError("unclosed CDB group")

    nodes = []
    while cursor < len(text):
        skip()
        if cursor == len(text):
            break
        if text.startswith(".if ", cursor):
            cursor += 4
            condition = enclosed("(", ")")
            yes = parse_commands(enclosed("{", "}"))
            skip()
            no = []
            if text.startswith(".else ", cursor):
                cursor += 6
                no = parse_commands(enclosed("{", "}"))
            nodes.append(("if", condition, yes, no))
            continue
        start, quoted = cursor, False
        while cursor < len(text):
            char = text[cursor]
            if char == '"' and text[cursor - 1] != "\\":
                quoted = not quoted
            if char == ";" and not quoted:
                break
            cursor += 1
        nodes.append(("command", text[start:cursor].strip()))
    return nodes


def printf_observation(command, memory, regs):
    """Evaluate the producer's actual printf arguments, without a CDB process.

    This narrow formatter supports only the numeric formats used by this
    probe. Missing event registers or unsupported syntax fail the fixture.
    """
    match = re.fullmatch(r'\.printf "(.*?)", (.*)', command)
    assert match, command
    fmt, arguments = match.groups()
    values = iter(evaluate(arg.strip(), memory, regs)
                  for arg in arguments.split(","))

    def format_value(match):
        spec = match[0]
        value = next(values)
        if spec == "%p":
            return f"{value & 0xffffffff:08x}"
        return spec % value

    rendered = re.sub(r"%0?\d*[dxp]", format_value, fmt)
    assert next(values, None) is None, "unused printf arguments"
    assert "%" not in rendered, "unsupported printf format"
    return rendered.removesuffix(r"\\n")


def run_commands(nodes, memory, regs, markers, enabled_breakpoints=None,
                 observations=None):
    """Return True only when the real probe command requests debugger quit."""
    for node in nodes:
        if node[0] == "if":
            branch = node[2] if evaluate(node[1], memory, regs) else node[3]
            if run_commands(branch, memory, regs, markers, enabled_breakpoints,
                            observations):
                return True
            continue
        command = node[1]
        if command == "q":
            return True
        if command == "gc":
            continue
        if command.startswith(("be ", "bd ")):
            markers.append("BREAKPOINT_" + command.replace(" ", "_"))
            if enabled_breakpoints is not None:
                # Explicit CDB breakpoint IDs are decimal. Model only their
                # command-controlled enable state, not native execution.
                breakpoint_id = int(command.split()[1])
                if command.startswith("be "):
                    enabled_breakpoints.add(breakpoint_id)
                else:
                    enabled_breakpoints.discard(breakpoint_id)
            continue
        if command.startswith("ed "):
            address, expr = command[3:].split(" ", 1)
            write(memory, evaluate(address, memory, regs), evaluate(expr, memory, regs))
        elif command.startswith("r "):
            reg, expr = command[2:].split("=", 1)
            regs[reg.strip().removeprefix("@")] = evaluate(expr, memory, regs) & 0xffffffff
        elif command.startswith((".echo ", ".printf ")):
            markers.extend(re.findall(r"\bDAYDIAG_[A-Z_]+\b", command))
            if observations is not None:
                observations.append(printf_observation(command, memory, regs)
                                    if command.startswith(".printf ")
                                    else command.removeprefix(".echo "))
        else:
            raise AssertionError(f"unsupported probe command: {command}")
    return False


class DayDiagnosticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = PROBE.read_text(encoding="ascii")
        cls.control = next(line for line in cls.text.splitlines() if re.match(r"bp\d* 00406FA1 ", line))
        cls.commands = {
            int(line.split()[1], 16): parse_commands(line.split('"', 1)[1][:-1])
            for line in cls.text.splitlines() if re.match(r"bp\d* ", line)
        }

    def diagnostic_state(self, *, active=31, day=20, mode=0):
        memory = {}
        write(memory, 0x5202E4, 0x10000000)
        write(memory, 0x100222F6, day, 2)
        write(memory, 0x400304, mode)
        for player in range(5):
            write(memory, 0x100222F8 + player * 1423, (active >> player) & 1)
        regs = {reg: 0x11220000 + i * 0x100 for i, reg in enumerate(
            ("eax", "ebx", "ecx", "edx", "esi", "edi", "ebp", "efl"))}
        regs.update(esp=0x800000, eip=0x406FA1)
        markers = []
        quit_requested = run_commands(self.commands[0x40B0C3], memory, regs, markers)
        return memory, regs, markers, quit_requested

    def test_actual_byte_predicates_accept_native_and_reject_each_changed_byte(self):
        predicates = [line.split(".if (", 1)[1].split(") { .echo", 1)[0] for line in self.text.splitlines() if line.startswith(".if ")]
        self.assertEqual(len(predicates), 7)
        memory = {address+i: value for address, data in NATIVE_BYTES.items() for i, value in enumerate(data)}
        self.assertTrue(all(not evaluate(p, memory) for p in predicates))
        # Every checked instruction/layout/padding byte must reject corruption.
        for address, data in NATIVE_BYTES.items():
            for i in range(len(data)):
                broken = {**memory, address+i: memory[address+i] ^ 1}
                self.assertTrue(any(evaluate(p, broken) for p in predicates), hex(address+i))

    def test_instruction_boundary_derivation(self):
        # cmp+jle+mov+incw places the post-increment breakpoint at40AB44.
        sequence = [bytes.fromhex("3b0dec025200"), b"\x0f\x8e"+struct.pack("<i", 0x40ABB9-0x40AB38), bytes.fromhex("a1e4025200"), bytes.fromhex("66ff80f6220200")]
        self.assertEqual(0x40AB2C + sum(map(len, sequence)), 0x40AB44)
        mouse_prefix = bytes.fromhex("8d542450528b40086a108b0850")
        keyboard_prefix = bytes.fromhex("83bb380100000074228d4b34518b430468000100008b1050")
        self.assertEqual(0x47C01C+len(mouse_prefix), 0x47C029)
        self.assertEqual(0x47BFE1+len(keyboard_prefix), 0x47BFF9)
        self.assertEqual(0x47C029+len(bytes.fromhex("ff5124")), 0x47C02C)
        self.assertEqual(0x47BFF9+len(bytes.fromhex("ff5224")), 0x47BFFC)
        # mov eax,esi (2) + direct call(5) -> TEST EAX,EAX at40A943.
        self.assertEqual(0x40A93C+2+5, 0x40A943)
        banner = NATIVE_BYTES[0x40A93C]
        self.assertEqual(0x40A943 + struct.unpack_from("<i", banner, 3)[0], 0x4608F0)
        self.assertEqual(0x40A94B + struct.unpack_from("<i", banner, 11)[0], 0x40A9FA)
        release = NATIVE_BYTES[0x4609D0]
        self.assertEqual(0x4609E0 + struct.unpack_from("<i", release, 12)[0], 0x4608F0)
        self.assertEqual(0x4609FC + struct.unpack_from("<i", release, 40)[0], 0x460900)
        self.assertEqual(release[16:18], bytes.fromhex("85c0"))
        self.assertEqual(release[44:46], bytes.fromhex("85c0"))
        self.assertEqual(release[-4:], bytes.fromhex("5e595bc3"))

    def test_verified_input_stack_layout_matches_each_observation_site(self):
        # Interpret only the independently identified stack-changing opcodes.
        # The complete spans are pinned by actual candidate predicates and the
        # known-original PE check below; no byte scanning infers instructions.
        prologue = NATIVE_BYTES[0x47BFD0]
        self.assertEqual(prologue[:6], bytes.fromhex("53515283ec60"))
        self.assertEqual(NATIVE_BYTES[0x47BFE1][12:13], b"\x51")
        self.assertEqual(NATIVE_BYTES[0x47BFE1][16:21], bytes.fromhex("6800010000"))
        self.assertEqual(NATIVE_BYTES[0x47BFE1][-1:], b"\x50")
        self.assertEqual(NATIVE_BYTES[0x47C01C][4:5], b"\x52")
        self.assertEqual(NATIVE_BYTES[0x47C01C][8:10], bytes.fromhex("6a10"))
        self.assertEqual(NATIVE_BYTES[0x47C01C][-1:], b"\x50")
        for entry_esp in (0x800000, 0xEDC68, 0x100004):
            poll_esp = entry_esp - 4  # first PUSH EBX has executed
            locals_esp = entry_esp - 3 * 4 - prologue[5]
            call_esp = locals_esp - 3 * 4
            return_esp = call_esp + 3 * 4  # COM stdcall removes its arguments
            self.assertEqual(call_esp, poll_esp - 0x74)
            self.assertEqual(return_esp, poll_esp - 0x68)

    def test_actual_input_printf_records_event_thread_sites_and_stack_without_writes(self):
        for tid, poll_esp in ((0x3AC, 0xEDC64), (0xFFF0, 0x700000)):
            with self.subTest(tid=tid, poll_esp=poll_esp):
                memory, regs, markers, _ = self.diagnostic_state(mode=1)
                write(memory, 0x400300, 2)
                regs.update({"$tid": tid, "eip": 0x47BFD1,
                             "esp": poll_esp, "eax": 0x545198})
                write(memory, poll_esp + 4, 0x460A61)
                write(memory, 0x545198 + 0x134, 1)
                write(memory, 0x545198 + 0x138, 1)
                observations = []
                before_regs = dict(regs)
                self.assertFalse(run_commands(self.commands[0x47BFD1], memory,
                                             regs, markers, observations=observations))
                self.assertEqual(regs, before_regs)
                self.assertEqual(observations, [
                    "DAYDIAG_INPUT_POLL_ENTRY ret=00460a61 object=00545198 "
                    "mouse_enabled=1 keyboard_enabled=1 joystick_enabled=0 "
                    f"tid={tid:x} eip=0047bfd1 esp={poll_esp:08x}"])
                for device, call, ret, table_register, size in (
                    ("mouse", 0x47C029, 0x47C02C, "ecx", 16),
                    ("keyboard", 0x47BFF9, 0x47BFFC, "edx", 256),
                ):
                    regs.update(eip=call, esp=poll_esp - 0x74)
                    regs[table_register] = 0x600000
                    write(memory, 0x600024, 0x6BFA7680)
                    before_memory, before_regs = dict(memory), dict(regs)
                    self.assertFalse(run_commands(self.commands[call], memory,
                                                 regs, markers, observations=observations))
                    self.assertEqual((memory, regs), (before_memory, before_regs))
                    self.assertEqual(observations[-1],
                        f"DAYDIAG_GETDEVICESTATE_CALL device={device} "
                        f"target=6bfa7680 bytes={size} tid={tid:x} "
                        f"eip={call:08x} esp={poll_esp - 0x74:08x}")
                    regs.update(eip=ret, esp=poll_esp - 0x68, eax=0x8007000C)
                    write(memory, 0x5451C0, 0x99, 1)
                    write(memory, 0x5451C8, 0x86, 1)
                    before_memory, before_regs = dict(memory), dict(regs)
                    self.assertFalse(run_commands(self.commands[ret], memory,
                                                 regs, markers, observations=observations))
                    self.assertEqual((memory, regs), (before_memory, before_regs))
                    buttons = " lbtn=99 rbtn=86" if device == "keyboard" else ""
                    self.assertEqual(observations[-1],
                        f"DAYDIAG_GETDEVICESTATE_RETURN device={device} "
                        f"hresult=8007000c{buttons} tid={tid:x} "
                        f"eip={ret:08x} esp={poll_esp - 0x68:08x}")

    def test_duplicate_and_foreign_thread_events_are_retained_without_filtering(self):
        memory, regs, markers, _ = self.diagnostic_state(mode=1)
        write(memory, 0x400300, 2)
        write(memory, 0x400304, 0x101)
        regs.update({"$tid": 0x3AC, "eip": 0x47C02C,
                     "esp": 0xEDBFC, "eax": 0x8007000C})
        observations = []
        before_memory, before_regs = dict(memory), dict(regs)
        for _ in range(2):
            self.assertFalse(run_commands(self.commands[0x47C02C], memory,
                                         regs, markers, observations=observations))
        self.assertEqual(len(observations), 2)
        self.assertEqual(observations[0], observations[1])
        self.assertEqual((memory, regs), (before_memory, before_regs))
        regs.update({"$tid": 0x44C, "esp": 0x700000})
        self.assertFalse(run_commands(self.commands[0x47C02C], memory,
                                     regs, markers, observations=observations))
        self.assertEqual(len(observations), 3)
        self.assertTrue(observations[-1].endswith("tid=44c eip=0047c02c esp=00700000"))
        self.assertEqual(markers.count("DAYDIAG_GETDEVICESTATE_RETURN"), 3)
        # Absent debugger identity is an error, never an invented thread ID.
        del regs["$tid"]
        with self.assertRaises(KeyError):
            run_commands(self.commands[0x47C02C], memory, regs, markers,
                         observations=observations)

    def test_phase_identity_is_observed_before_control_mutations(self):
        memory, regs, markers, _ = self.diagnostic_state(mode=1)
        regs["$tid"] = 0x3AC
        write(memory, 0x7FFE0320, 128)
        observations = []
        saved_esp = regs["esp"]
        self.assertFalse(run_commands(self.commands[0x406FA1], memory,
                                     regs, markers, observations=observations))
        self.assertTrue(observations[-1].endswith(
            f"saved_esp={saved_esp:08x} mechanism=forced_native_call "
            f"tid=3ac eip=00406fa1 esp={saved_esp:08x}"))
        self.assertEqual((regs["esp"], regs["eip"]), (saved_esp - 4, 0x40AA60))
        for site, marker in ((0x40A820, "BANNER_ENTRY"), (0x40A9FA, "BANNER_EXIT")):
            regs.update(eip=site, esp=saved_esp - 0x100)
            self.assertFalse(run_commands(self.commands[site], memory,
                                         regs, markers, observations=observations))
            self.assertTrue(observations[-1].startswith(f"DAYDIAG_{marker} "))
            self.assertTrue(observations[-1].endswith(
                f"tid=3ac eip={site:08x} esp={regs['esp']:08x}"))
        regs.update(eip=0x4609D0, eax=0x544CD8)
        write(memory, regs["esp"], 0x40AA06)
        self.assertFalse(run_commands(self.commands[0x4609D0], memory,
                                     regs, markers, observations=observations))
        self.assertTrue(observations[-1].endswith(
            f"esp={regs['esp']:08x} tid=3ac eip=004609d0"))
        regs.update(eip=0x40AA06, esp=regs["esp"] + 4)
        self.assertFalse(run_commands(self.commands[0x40AA06], memory,
                                     regs, markers, observations=observations))
        self.assertTrue(observations[-2].startswith("DAYDIAG_RELEASE_RETURN "))
        self.assertTrue(observations[-2].endswith(
            f"esp={regs['esp']:08x} tid=3ac eip=0040aa06"))
        self.assertEqual(observations[-1], "DAYDIAG_INPUT_TRACE_END phase=release_wait")
        regs.update(eip=0x406FA1, esp=saved_esp)
        write(memory, 0x5202EC, 1)
        self.assertFalse(run_commands(self.commands[0x406FA1], memory,
                                     regs, markers, observations=observations))
        self.assertTrue(observations[-1].startswith("DAYDIAG_NEXT_RETURN "))
        self.assertTrue(observations[-1].endswith(
            f"esp={saved_esp:08x} tid=3ac eip=00406fa1"))

    def test_real_register_save_restore_and_nested_return_exclusion(self):
        saves = re.findall(r"ed (004003[0-3][0-9a-f]) @(eax|ebx|ecx|edx|esi|edi|ebp|efl|esp);", self.control)
        restores = re.findall(r"r (eax|ebx|ecx|edx|esi|edi|ebp|efl)=poi\((004003[0-3][0-9a-f])\);", self.control)
        self.assertEqual({reg for _, reg in saves}, {"eax", "ebx", "ecx", "edx", "esi", "edi", "ebp", "efl", "esp"})
        self.assertEqual({reg for reg, _ in restores}, {reg for _, reg in saves}-{"esp"})
        for seed in range(31):
            before = {reg: ((seed+1)*0x10101+i*0x112233)&0xffffffff for i, (_, reg) in enumerate(saves)}
            memory = {}
            for addr, reg in saves:
                write(memory, int(addr, 16), before[reg])
            after = {reg: 0xDEADBEEF for reg in before}
            after["esp"] = before["esp"]  # actual native RET pops synthetic address
            for reg, addr in restores:
                after[reg] = evaluate(f"poi({addr})", memory)
            self.assertEqual(before, after)
            write(memory, 0x40033C, 2)
            condition = re.search(r"\.if \((\(poi\(0040033c\) == 2\).*?)\) \{", self.control)[1]
            self.assertTrue(evaluate(condition, memory, {"esp": before["esp"]}))
            for delta in (-4, -128, 4):
                self.assertFalse(evaluate(condition, memory, {"esp": before["esp"]+delta}))

    def test_caps_observe_default_single_ack_and_no_gamedata_writes(self):
        self.assertIn("\ned 00400304 0\n", self.text)
        self.assertIn("poi(00400308) >= 5", self.control)
        self.assertIn("(poi(00400304) & 0xff)", self.text)
        self.assertIn("(poi(00400304)+0x100)", self.text)
        self.assertIn("(poi(00400304) >> 8) <= 0n16", self.text)
        self.assertIn("(poi(00400304) & 0xffffff00) | 2", self.text)
        self.assertIn("DAYDIAG_OBSERVED_BANNER_INPUT_WAIT acknowledgment_not_attempted=1; q }", self.text)
        self.assertEqual(self.text.count("r eax=1;"), 1)
        self.assertNotRegex(self.text, r"\b(?:eb|ew|ed)\s+(?:005[0-9a-f]+|poi\(|@\$t)")
        self.assertNotIn("004443E0", self.text.upper())
        # Probe-only mutations are bounded verified header padding, one synthetic stack
        # return address and explicitly disclosed debugger register changes.
        destinations = re.findall(r"\bed (\S+)", self.text)
        self.assertTrue(all(d == "@esp" or 0x400300 <= int(d, 16) <= 0x40034C for d in destinations))

    def test_actual_control_wraps_active_five_slot_orders_and_u16_day(self):
        # Native nextPlayer increments modulo five and skips zero active flags;
        # its day branch runs only when the selected index is below the old one.
        for active in range(3, 32, 2):
            for initial_day in (20, 65535):
                memory, regs, markers, quit_requested = self.diagnostic_state(active=active, day=initial_day)
                self.assertFalse(quit_requested)
                player, day, tick = 0, initial_day, 0
                for advance in range(active.bit_count()):
                    before = dict(regs)
                    tick += 128
                    write(memory, 0x7FFE0320, tick)
                    self.assertFalse(run_commands(self.commands[0x406FA1], memory, regs, markers))
                    self.assertEqual(regs["eip"], 0x40AA60)
                    self.assertEqual(regs["esp"], before["esp"] - 4)
                    self.assertEqual(evaluate("poi(@esp)", memory, regs), 0x406FA1)
                    # A redraw nested inside nextPlayer cannot restore caller
                    # state or manufacture the injected call's return marker.
                    nested = dict(regs, esp=regs["esp"] - 128, eip=0x406FA1)
                    returns_before = markers.count("DAYDIAG_NEXT_RETURN")
                    self.assertFalse(run_commands(self.commands[0x406FA1], memory, nested, markers))
                    self.assertEqual(markers.count("DAYDIAG_NEXT_RETURN"), returns_before)
                    selected = (player + 1) % 5
                    while not active & (1 << selected):
                        selected = (selected + 1) % 5
                    if selected < player:
                        day = (day + 1) & 65535
                    player = selected
                    write(memory, 0x5202EC, player)
                    write(memory, 0x100222F6, day, 2)
                    for reg in ("eax", "ebx", "ecx", "edx", "esi", "edi", "ebp", "efl"):
                        regs[reg] = 0xDEADBEEF
                    regs.update(esp=before["esp"], eip=0x406FA1)
                    self.assertFalse(run_commands(self.commands[0x406FA1], memory, regs, markers))
                    for reg in before.keys() - {"$t0"}:
                        self.assertEqual(regs[reg], before[reg], (active, initial_day, advance, reg))
                self.assertEqual(player, 0)
                self.assertEqual(day, (initial_day + 1) & 65535)
                self.assertEqual(markers.count("DAYDIAG_FULL_DAY_RETURNED"), 1)
                # The surface is released at a later redraw, not at native RET.
                self.assertEqual(regs["$t7"], 1)
                self.assertNotIn("DAYDIAG_POST_DAY_REDRAW", markers)
                self.assertFalse(run_commands(self.commands[0x406FA1], memory, regs, markers))
                self.assertEqual(regs["$t7"], 0)
                self.assertEqual(regs["$t13"], 4)
                self.assertEqual(markers.count("DAYDIAG_POST_DAY_REDRAW"), 1)

    def test_actual_control_rejects_inactive_start_wrong_player_and_missing_wrap(self):
        self.assertTrue(self.diagnostic_state(active=30)[3])
        for returned_day, returned_player, advance in ((20, 0, 5), (21, 1, 1), (22, 0, 1)):
            memory, regs, markers, _ = self.diagnostic_state()
            write(memory, 0x400300, 2)
            write(memory, 0x400308, advance)
            write(memory, 0x400310, regs["esp"])
            write(memory, 0x5202EC, returned_player)
            write(memory, 0x100222F6, returned_day, 2)
            self.assertTrue(run_commands(self.commands[0x406FA1], memory, regs, markers))
            self.assertNotIn("DAYDIAG_FULL_DAY_RETURNED", markers)
            self.assertEqual(regs["$t7"], 1)

    def test_actual_banner_observes_eight_and_allows_only_one_disclosed_ack(self):
        for mode in (0, 1):
            memory, regs, markers, _ = self.diagnostic_state(mode=mode)
            write(memory, 0x400300, 2)
            regs["eax"] = 0
            for poll in range(1, 9):
                quit_requested = run_commands(self.commands[0x40A943], memory, regs, markers)
                self.assertEqual(quit_requested, poll == 8 and mode == 0)
                self.assertEqual(regs["eax"], int(poll == 8 and mode == 1))
            if mode == 0:
                self.assertNotIn("DAYDIAG_FORCED_BANNER_ACK", markers)
                self.assertIn("DAYDIAG_OBSERVED_BANNER_INPUT_WAIT", markers)
            else:
                self.assertEqual(markers.count("DAYDIAG_FORCED_BANNER_ACK"), 1)
                self.assertEqual(evaluate("poi(00400304) & 0xff", memory), 2)
                # A new advance resets only its sample/poll counters, retaining
                # consumed mode2. No second forced acknowledgment is possible.
                write(memory, 0x400338, 0)
                regs["eax"] = 0
                for poll in range(1, 9):
                    quit_requested = run_commands(self.commands[0x40A943], memory, regs, markers)
                    self.assertEqual(quit_requested, poll == 8)
                self.assertEqual(regs["eax"], 0)
                self.assertEqual(markers.count("DAYDIAG_FORCED_BANNER_ACK"), 1)


    def test_hot_breakpoints_are_late_armed_and_physically_disabled_at_trace_cap(self):
        ids = [int(v) for v in re.findall(r"(?m)^bp(\d+) ", self.text)]
        self.assertEqual(ids, list(range(80, 96)))
        self.assertEqual([int(v) for v in re.findall(r"(?m)^bd (\d+)$", self.text)], list(range(81, 96)))
        memory, regs, markers, _ = self.diagnostic_state()
        self.assertTrue(all(f"BREAKPOINT_be_{i}" in markers for i in range(81, 87)))
        self.assertFalse(any(f"BREAKPOINT_be_{i}" in markers for i in range(87, 96)))
        write(memory, 0x7FFE0320, 128)
        self.assertFalse(run_commands(self.commands[0x406FA1], memory, regs, markers))
        self.assertTrue(all(f"BREAKPOINT_be_{i}" in markers for i in range(87, 92)))
        for _ in range(17):
            self.assertFalse(run_commands(self.commands[0x47BFD1], memory, regs, markers))
        self.assertEqual(markers.count("DAYDIAG_INPUT_POLL_ENTRY"), 16)
        self.assertEqual(markers.count("DAYDIAG_INPUT_TRACE_LIMIT"), 1)
        self.assertTrue(all(f"BREAKPOINT_bd_{i}" in markers for i in range(87, 92)))

    def test_release_wait_observation_stops_at_eight_without_mutating_buttons(self):
        for button in ("left", "right"):
            memory, regs, markers, _ = self.diagnostic_state()
            write(memory, 0x400300, 2)
            regs["eax"] = 0x544CD8
            write(memory, regs["esp"], 0x40AA06)
            self.assertFalse(run_commands(self.commands[0x40A9FA], memory, regs, markers))
            self.assertTrue(all(f"BREAKPOINT_be_{i}" in markers for i in range(92, 96)))
            self.assertFalse(run_commands(self.commands[0x4609D0], memory, regs, markers))
            regs["ecx"] = 0x544CD8
            write(memory, 0x544D04, 1 if button == "left" else 2)
            write(memory, 0x5451C0, 0x87, 1)
            write(memory, 0x5451C8, 0xED, 1)
            before_buttons = {addr: memory.get(addr) for addr in (0x544D04, 0x5451C0, 0x5451C8)}
            for poll in range(1, 9):
                regs["eax"] = int(button == "left")
                stop = run_commands(self.commands[0x4609E0], memory, regs, markers)
                if button == "right":
                    self.assertFalse(stop)
                    regs["eax"] = 1
                    stop = run_commands(self.commands[0x4609FC], memory, regs, markers)
                self.assertEqual(stop, poll == 8)
            self.assertEqual(markers.count("DAYDIAG_OBSERVED_RELEASE_INPUT_WAIT"), 1)
            self.assertEqual(before_buttons, {addr: memory.get(addr) for addr in before_buttons})
            self.assertEqual(regs["eax"], 1)

    def test_release_return_requires_actual_call_stack_and_no_held_buttons(self):
        for delta in (4, 0, 8):
            memory, regs, markers, _ = self.diagnostic_state()
            write(memory, 0x400300, 2)
            regs["eax"] = 0x544CD8
            write(memory, regs["esp"], 0x40AA06)
            initial_esp = regs["esp"]
            self.assertFalse(run_commands(self.commands[0x4609D0], memory, regs, markers))
            regs.update(eax=0, ecx=0x544CD8)
            self.assertFalse(run_commands(self.commands[0x4609E0], memory, regs, markers))
            self.assertFalse(run_commands(self.commands[0x4609FC], memory, regs, markers))
            regs["esp"] = initial_esp + delta
            self.assertEqual(run_commands(self.commands[0x40AA06], memory, regs, markers), delta != 4)
            self.assertEqual("DAYDIAG_RELEASE_RETURN" in markers, delta == 4)
            self.assertEqual("DAYDIAG_INPUT_TRACE_END" in markers, delta == 4)

    def test_verified_release_return_closes_input_trace_before_later_native_work(self):
        for mode in (0, 1):
            for delta in (4, 0, 8):
                with self.subTest(mode=mode, return_esp_delta=delta):
                    memory, regs, markers, _ = self.diagnostic_state(mode=mode)
                    write(memory, 0x400300, 2)
                    regs["eax"] = 0x544CD8
                    write(memory, regs["esp"], 0x40AA06)
                    initial_esp = regs["esp"]
                    self.assertFalse(run_commands(self.commands[0x4609D0], memory, regs, markers))
                    regs.update(eax=0, ecx=0x544CD8)
                    self.assertFalse(run_commands(self.commands[0x4609E0], memory, regs, markers))
                    self.assertFalse(run_commands(self.commands[0x4609FC], memory, regs, markers))
                    enabled = set(range(87, 96))
                    markers.clear()
                    regs["esp"] = initial_esp + delta
                    stopped = run_commands(self.commands[0x40AA06], memory, regs, markers, enabled)
                    if delta != 4:
                        self.assertTrue(stopped)
                        self.assertEqual(markers, ["DAYDIAG_FAIL"])
                        self.assertEqual(enabled, set(range(87, 96)))
                        self.assertEqual(evaluate("poi(00400340)", memory), 1)
                        continue
                    self.assertFalse(stopped)
                    self.assertEqual(markers, ["DAYDIAG_RELEASE_RETURN",
                                             *(f"BREAKPOINT_bd_{i}" for i in range(87, 92)),
                                             "DAYDIAG_INPUT_TRACE_END",
                                             *(f"BREAKPOINT_bd_{i}" for i in range(92, 96))])
                    self.assertEqual(enabled, set())
                    self.assertEqual(evaluate("poi(00400340)", memory), 0)
                    # Try later hits at every input/release address using the
                    # actual bp-ID mapping. Disabled breakpoints emit nothing.
                    before = list(markers)
                    for breakpoint_id, address in re.findall(r"(?m)^bp(\d+) ([0-9A-F]{8}) ", self.text):
                        if 87 <= int(breakpoint_id) <= 95 and int(breakpoint_id) in enabled:
                            run_commands(self.commands[int(address, 16)], memory, regs, markers, enabled)
                    self.assertEqual(markers, before)
                    # A repeated direct entry into the command body is inert,
                    # too: the completed release phase cannot close twice.
                    self.assertFalse(run_commands(self.commands[0x40AA06], memory, regs, markers, enabled))
                    self.assertEqual(markers, before)
                    self.assertEqual(evaluate("poi(00400304) & 0xff", memory), mode)
        release_line = next(line for line in self.text.splitlines() if line.startswith("bp95 "))
        self.assertIn(".echo DAYDIAG_INPUT_TRACE_END phase=release_wait;", release_line)
        self.assertEqual(self.text.count("DAYDIAG_INPUT_TRACE_END"), 1)

    def test_controlled_release_changes_only_one_query_per_button_with_real_counts(self):
        for held in ("both", "right"):
            memory, regs, markers, _ = self.diagnostic_state(mode=1)
            write(memory, 0x400300, 2)
            regs["eax"] = 0x544CD8
            write(memory, regs["esp"], 0x40AA06)
            self.assertFalse(run_commands(self.commands[0x4609D0], memory, regs, markers))
            regs["ecx"] = 0x544CD8
            write(memory, 0x544D04, 3 if held == "both" else 2)
            write(memory, 0x5451C0, 0x87, 1)
            write(memory, 0x5451C8, 0xED, 1)
            buttons = {a: memory.get(a) for a in (0x544D04, 0x5451C0, 0x5451C8)}
            for poll in range(1, 9):
                regs["eax"] = int(held == "both")
                self.assertFalse(run_commands(self.commands[0x4609E0], memory, regs, markers))
                self.assertEqual(regs["eax"], int(held == "both" and poll < 8))
                if regs["eax"] == 0:
                    regs["eax"] = 1
                    self.assertFalse(run_commands(self.commands[0x4609FC], memory, regs, markers))
                    self.assertEqual(regs["eax"], int(poll < 8))
            state = evaluate("poi(0040034c)", memory)
            self.assertEqual(state >> 8, 1 if held == "both" else 8)
            self.assertEqual(state & 0xFF, 3 if held == "both" else 2)
            self.assertEqual(markers.count("DAYDIAG_FORCED_RELEASE"), 2 if held == "both" else 1)
            self.assertEqual(buttons, {a: memory.get(a) for a in buttons})
            self.assertNotIn("DAYDIAG_OBSERVED_RELEASE_INPUT_WAIT", markers)
            # A later release entry resets the observation counter, but cannot
            # silently reuse a consumed per-button override.
            regs["eax"] = 0x544CD8
            self.assertFalse(run_commands(self.commands[0x4609D0], memory, regs, markers))
            before = markers.count("DAYDIAG_FORCED_RELEASE")
            for poll in range(1, 9):
                regs["eax"] = int(held == "both")
                stopped = run_commands(self.commands[0x4609E0], memory, regs, markers)
                if held == "right":
                    self.assertFalse(stopped)
                    regs["eax"] = 1
                    stopped = run_commands(self.commands[0x4609FC], memory, regs, markers)
                self.assertEqual(stopped, poll == 8)
            self.assertEqual(markers.count("DAYDIAG_FORCED_RELEASE"), before)

    def test_stable_and_combined800_keep_native_contract_and_allow_extra_renderer(self):
        template = BASE_PROBE.read_text()
        for stage in (patcher.DEFAULT_STAGE, patcher.DEFAULT_STAGE + "-combinedui-validation"):
            patches = patcher.select_patches_for(stage, patcher.PROFILE_800)
            for va, data in NATIVE_BYTES.items():
                offset = va - 0x400000 - (0 if va < 0x401000 else 0xC00)
                for patch in patches:
                    self.assertFalse(patch.offset < offset + len(data) and
                                     offset < patch.offset + len(bytes.fromhex(patch.new_hex)),
                                     (stage, hex(va), patch.group))
            recipe = render_probe(template, "800x600", stage, extra_probe=True)
            self.assertEqual(recipe["template"], template)
            with self.assertRaisesRegex(ValueError, "custom/extra probes"):
                render_probe(template, "1024x768", stage, extra_probe=True)
        self.assertNotIn("expected_candidate_sha=", self.text)
        self.assertIn("candidate_sha_source=matching_outer_byte_report", self.text)

    def test_source_syntax_and_existing_proof_preserved(self):
        self.assertTrue(self.text.startswith(".echo === Clash95 bounded day-transition diagnostic v7 ===\n"))
        self.assertEqual(hashlib.sha256(CAMPAIGN.read_bytes()).hexdigest(), CAMPAIGN_SHA)
        self.assertNotRegex(self.text, r"(?m)^\s*g\s*$")
        addresses = re.findall(r"(?m)^bp\d* ([0-9A-F]{8}) ", self.text)
        self.assertEqual(len(addresses), len(set(addresses)))
        self.assertNotIn("00406FA0", addresses)
        self.assertNotIn("0047BFD0", addresses)
        for line in self.text.splitlines():
            self.assertEqual(line.count("{"), line.count("}"), line[:45])
            self.assertLess(len(line), 4096)
            if re.match(r"bp\d* ", line):
                self.assertTrue(line.endswith('gc"'))
        self.assertLess(self.text.index("DAYDIAG_CONTRACT_PASS"), self.text.index("ed 00400300 0"))
        self.assertNotIn("q;", self.text)
        for line in self.text.splitlines():
            if any(f"DAYDIAG_CONTRACT_FAIL {name};" in line for name in (
                "route_entries", "day_boundaries", "banner_button_boundaries", "input_boundaries"
            )):
                self.assertNotIn("poi(", line)
                self.assertTrue(all(int(value, 16) <= 65535 for value in re.findall(r"!= (0x[0-9a-f]+)", line)))
                self.assertIn("db ", line)

    @unittest.skipUnless(LOCAL_ASM.exists(), "user-owned disassembly not present; runtime byte gate remains mandatory")
    def test_pinned_native_disassembly_supports_input_interpretation(self):
        raw = LOCAL_ASM.read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), ASM_SHA)
        text = raw.decode("utf-8", errors="replace")
        boolean = text.split("DD_IsFlipping   proc near", 1)[1].split("DD_IsFlipping   endp", 1)[0]
        self.assertIn("test    byte ptr [eax+2Ch], 1", boolean)
        self.assertNotIn("call", boolean)
        polling = text.split("Time_Sleep      proc near", 1)[1].split("Time_Sleep      endp", 1)[0]
        self.assertIn("call    dword ptr [edx+24h]", polling)
        self.assertIn("call    dword ptr [ecx+24h]", polling)
        updater = text.split("sub_460A50      proc near", 1)[1].split("sub_460A50      endp", 1)[0]
        self.assertIn("test    ds:byte_5451C0, 80h", updater)
        self.assertIn("inc     dword ptr [edx+2Ch]", updater)
        turns = text.split("nextPlayer      proc near", 1)[1].split("nextPlayer      endp", 1)[0]
        self.assertIn("mov     ebx, 5", turns)
        self.assertIn("idiv    ebx", turns)
        self.assertIn("cmp     dword ptr [edx+eax+222F8h], 0", turns)
        self.assertRegex(turns, r"cmp     ecx, ds:dword_5202EC\s+jle     loc_40ABB9\s+mov     eax, ds:gameData\s+inc     word ptr \[eax\+222F6h\]")

    @unittest.skipUnless(LOCAL_ORIGINAL.exists(), "user-owned original not present; runtime byte gate remains mandatory")
    def test_contract_bytes_match_known_original_pe_without_writes(self):
        raw = LOCAL_ORIGINAL.read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), ORIGINAL_SHA)
        pe = struct.unpack_from("<I", raw, 0x3C)[0]
        section_count = struct.unpack_from("<H", raw, pe + 6)[0]
        optional_size = struct.unpack_from("<H", raw, pe + 20)[0]
        image_base = struct.unpack_from("<I", raw, pe + 24 + 28)[0]
        sections = [struct.unpack_from("<8sIIII", raw, pe + 24 + optional_size + i * 40)
                    for i in range(section_count)]
        self.assertEqual(pe + 24 + optional_size + section_count * 40, 0x280)
        self.assertLessEqual(pe + 24 + optional_size + section_count * 40, 0x300)
        self.assertGreaterEqual(struct.unpack_from("<I", raw, pe + 24 + 60)[0], 0x34C)
        for va, expected in NATIVE_BYTES.items():
            rva = va - image_base
            if rva < 0x1000:
                offset = rva
            else:
                matches = [file_offset + rva - section_rva
                           for _, _, section_rva, file_size, file_offset in sections
                           if section_rva <= rva and rva + len(expected) <= section_rva + file_size]
                self.assertEqual(len(matches), 1)
                offset = matches[0]
                # All diagnostic instructions are in this original's .text;
                # this is the mapping used in the source-only overlap check.
                self.assertEqual(offset, va - 0x400000 - 0xC00)
            self.assertEqual(raw[offset:offset + len(expected)], expected, hex(va))


if __name__ == "__main__":
    unittest.main()
