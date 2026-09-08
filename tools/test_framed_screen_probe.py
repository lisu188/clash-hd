"""Offline exact-image and actual CDB-command fixtures; no game/debugger or EXE output."""
from __future__ import annotations

from pathlib import Path
import struct
import unittest

import framed_screen_probe as probe
from test_continuity_day_diagnostic_probe import evaluate, parse_commands, printf_observation, write

ORIGINAL = Path("C:/Clash/clash95.exe")
RESOLUTIONS = ("800x600", "1024x768", "1280x720", "1280x960", "1920x1080", "802x602")


class Memory(dict):
    def get(self, key, default=None):
        if key not in self:
            raise AssertionError(f"unsafe or unprepared memory read at{key:08x}")
        return self[key]


def run(body, memory, regs, enabled, observations):
    """Execute the emitted command subset, never native x86 or CDB.

    Return a terminal reason. In particular gc terminates the command so a
    fixture cannot silently execute a later branch after native continuation.
    """
    def execute(nodes):
        for node in nodes:
            if node[0] == "if":
                result = execute(node[2] if evaluate(node[1], memory, regs) else node[3])
                if result:
                    return result
                continue
            command = node[1]
            if command in ("q", "gc"):
                return command
            if command.startswith(("bd ", "be ")):
                operation, value = command.split()
                (enabled.add if operation == "be" else enabled.discard)(int(value))
            elif command.startswith("r "):
                name, expr = command[2:].split("=", 1)
                regs[name.strip().removeprefix("@")] = evaluate(expr, memory, regs) & 0xFFFFFFFF
            elif command.startswith(("eb ", "ed ")):
                address, value = command[3:].split(" ", 1)
                write(memory, evaluate(address, memory, regs), evaluate(value, memory, regs), 1 if command[:2] == "eb" else 4)
            elif command.startswith(".printf "):
                observations.append(printf_observation(command, memory, regs))
            elif command.startswith(".echo "):
                observations.append(command[6:])
            else:
                raise AssertionError(f"unsupported actual command {command}")
        return None
    return execute(parse_commands(body))


def state(width=800, height=600, index=0):
    gd, surface, pixels, overview_surface = 0x10000000, 0x20000000, 0x21000000, 0x22000000
    owner = gd + 0x7C6EA + 467*index
    memory = Memory()
    for address, value, size in (
        (0x5202E4, gd, 4), (0x5202E0, surface, 4), (0x5199D8, 0x40AD40, 4),
        (0x526994, 0, 4), (0x526990, 0, 4), (gd+0x222E0, 100, 4), (gd+0x222E4, 100, 4),
        (surface, width, 2), (surface+2, height, 2), (surface+4, pixels, 4), (surface+0xB8, 0x50EE24, 4),
        (owner, 14, 1), (owner+1, 20, 1), (owner+2, 0, 1), (owner+0x1A0, 0, 1), (owner+0x1A4, 0, 1),
        (gd+0x2231F, 1, 4), (0x526A64, owner, 4), (0x526A68, overview_surface, 4),
        (0x511230, surface, 4), (0x544D10, 0, 4), (0x51D4C0, width, 2), (0x51D4C2, height, 2),
        (0x51D578, 0x50ECB0, 4),
    ):
        write(memory, address, value, size)
    regs = {"$tid": 0x2345, "eip": 0x406FA0, "esp": 0x1000000, "eax": 17,
            "ebx": 99, "ecx": 88, "edx": 77, "esi": 0, "ebp": index*467,
            "$t0": 0, "$t14": 1, "$t13": 4, "$t7": 1}
    return memory, regs, set(range(70, 78)), []


class CommandTests(unittest.TestCase):
    def advance(self, name, availability="existing_flags", index=0):
        route = probe.ROUTES[name]
        handoff, commands = probe._commands(route, 800, 600, index, availability)
        memory, regs, enabled, observed = state(index=index)
        self.assertEqual(run(handoff, memory, regs, enabled, observed), "gc")
        self.assertTrue(observed[0].startswith("PTILE_TRACE_CLOSED tid=2345 eip=00406fa0"))
        self.assertFalse(enabled & set(range(70, 78)))
        self.assertEqual(regs["eip"], 0x422180)
        self.assertEqual(regs["esp"], 0x1000000-4)
        self.assertEqual(evaluate("poi(@esp)", memory, regs), 0x406FA1)
        snapshots = {}
        def hit(number, **changes):
            regs.update(changes)
            regs["eip"] = commands[number][0]
            snapshots[number] = (Memory(memory), regs.copy(), enabled.copy())
            return run(commands[number][1], memory, regs, enabled, observed)
        # CDB may skip a breakpoint at the newly assigned current EIP. No
        # entry event is synthesized: execute the native opcode 53 (PUSH EBX)
        # in this fixture, then hit the next instruction boundary.
        self.assertEqual(bytes.fromhex(probe.ROUTES['castle_overview'].entry_bytes)[0], 0x53)
        self.assertNotIn(0x422180, [va for va, _ in commands.values()])
        regs['esp'] -= 4
        write(memory, regs['esp'], regs['ebx'])
        self.assertEqual(hit(81), "gc")
        self.assertEqual(hit(82, esp=regs["$t4"]-56, eax=0x544CD8), "gc")
        result = hit(83)
        if name != "castle_overview":
            self.assertEqual(result, "gc")
            self.assertEqual(hit(84, esi=0), "gc")
            self.assertEqual(regs["eip"], route.branch_va)
            # Native case/descriptor prelude, not emulated by the fixture.
            self.assertEqual(hit(85, eax=0, ecx=route.entry_va, esi=route.command), "gc")
            self.assertEqual(regs["eax"], 1)
            write(memory, 0x5199D8, 0x4617A0)
            self.assertEqual(hit(86, eax=regs["$t1"]), "gc")
            regs["esp"] -= 4
            write(memory, regs["esp"], 0x42262E)
            self.assertEqual(hit(87), "gc")
            self.assertEqual(hit(88, esp=regs["$t6"]-route.local_stack_bytes, eax=0x544CD8), "gc")
            result = hit(89)
        self.assertIsNone(result)
        self.assertEqual(observed[-1], "MODAL_SURFDUMP_HOST_READY")
        self.assertIn("capture=memory_map", observed[-2])
        self.assertNotIn("SURFDUMP_HOST_READY", observed[:-1])
        return memory, regs, enabled, observed, commands, snapshots

    def test_all_supported_routes_observe_real_callback_and_first_return(self):
        for name in probe.ROUTES:
            with self.subTest(route=name):
                _, _, _, rows, _, _ = self.advance(name)
                if name != "castle_overview":
                    order = ["MODAL_FORCED_DISPATCH", "MODAL_FLIP_GATE_FORCED", "MODAL_CALLBACK_CALL",
                             "MODAL_SCREEN_ENTRY", "MODAL_PRESENT_CALL", "MODAL_PRESENT_RETURN", "MODAL_SURFDUMP_READY"]
                    found = [next(i for i,row in enumerate(rows) if row.startswith(marker)) for marker in order]
                    self.assertEqual(found, sorted(found))
                    self.assertIn("original=0 forced=1", next(row for row in rows if row.startswith("MODAL_FLIP_GATE")))

    def test_observed_flags_unchanged_constructed_changes_exact_two_bytes(self):
        first = self.advance("hospital", index=2)
        second = self.advance("hospital", availability="construct_all", index=2)
        changed = {k for k in first[0] if first[0][k] != second[0][k]}
        owner = 0x1007C6EA + 467*2
        self.assertEqual(changed, {owner+0x1A0, owner+0x1A4})
        self.assertEqual(second[0][owner+0x1A0], 0x1F)
        self.assertEqual(second[0][owner+0x1A4], 1)
        self.assertTrue(any("MODAL_AVAILABILITY_FORCED" in row for row in second[3]))

    def test_handoff_failures_never_write_target_or_invoke(self):
        handoff, _ = probe._commands(probe.ROUTES["hospital"], 800, 600, 0, "construct_all")
        cases = [("register", "eip", 0x406FA1), ("register", "$t13", 5), ("register", "$t7", 0),
                 ("memory", 0x5202E4, 0), ("memory", 0x5202E0, 0), ("memory", 0x5199D8, 0x4617A0),
                 ("memory", 0x526994, 1), ("memory", 0x526990, 1), ("memory", 0x200000B8, 0x50ECB0),
                 ("memory", 0x20000004, 0), ("memory", 0x20000000, 640)]
        for kind, key, value in cases:
            with self.subTest(case=(kind,key,value)):
                memory, regs, enabled, observed = state()
                if kind == "register": regs[key] = value
                else: write(memory, key, value)
                before = dict(memory)
                self.assertEqual(run(handoff, memory, regs, enabled, observed), "q")
                self.assertEqual(memory, before)
                self.assertFalse(any(row.startswith("MODAL_FORCE_CALL") for row in observed))

    def test_wrong_thread_stack_identity_missing_phase_and_duplicate_fail(self):
        _, _, _, _, commands, snapshots = self.advance("school")
        for number in range(81, 90):
            for mode in ("thread", "phase", "eip", "stack"):
                with self.subTest(bp=number, mode=mode):
                    original_memory, original_regs, original_enabled = snapshots[number]
                    memory, regs, enabled, observed = Memory(original_memory), original_regs.copy(), original_enabled.copy(), []
                    # Change exactly one property of the actual valid snapshot.
                    if mode == "thread": regs["$tid"] += 1
                    elif mode == "phase": regs["$t0"] = 99
                    elif mode == "eip": regs["eip"] += 1
                    else:
                        regs["esp"] += 16
                        write(memory, regs["esp"], 0)
                        write(memory, regs["esp"]+4, 0)
                    self.assertEqual(run(commands[number][1], memory, regs, enabled, observed), "q")
                    self.assertFalse(any(row == "MODAL_SURFDUMP_HOST_READY" for row in observed))
        memory, regs, enabled, observed, commands, _ = self.advance("school")
        self.assertEqual(run(commands[89][1], memory, regs, enabled, observed), "q")
        self.assertEqual(observed.count("MODAL_SURFDUMP_HOST_READY"), 1)

    def test_capture_null_wrong_dimensions_and_primary_fail_closed(self):
        for address,value,size in ((0x5202E0,0,4),(0x20000000,640,2),(0x20000002,480,2),
                                  (0x20000004,0,4),(0x200000B8,0x50ECB0,4)):
            memory, regs, enabled, observed = state()
            write(memory,address,value,size)
            self.assertEqual(run(probe._capture(probe.ROUTES['school'],800,600),memory,regs,enabled,observed),'q')
            self.assertNotIn('MODAL_SURFDUMP_HOST_READY',observed)

    def test_unexpected_return_always_quits_without_resuming_native_code(self):
        _, commands = probe._commands(probe.ROUTES['castle_overview'],800,600,0,'existing_flags')
        memory,regs,enabled,observed=state(); regs['eip']=0x406FA1
        self.assertEqual(run(commands[80][1],memory,regs,enabled,observed),'q')
        self.assertEqual(len(observed), 1)
        self.assertTrue(observed[0].startswith('MODAL_REJECT reason=unexpected_native_return '))
        _, commands = probe._commands(probe.ROUTES['school'],800,600,0,'existing_flags')
        regs['eip']=0x42262E; observed=[]
        self.assertEqual(run(commands[90][1],memory,regs,enabled,observed),'q')
        self.assertEqual(len(observed), 1)
        self.assertTrue(observed[0].startswith('MODAL_REJECT reason=unexpected_callback_return '))

    def test_post_push_observation_requires_native_saved_ebx_and_return_sentinel(self):
        _, _, _, rows, commands, snapshots = self.advance('castle_overview')
        self.assertEqual(commands[81][0], 0x422181)
        prologue = next(row for row in rows if row.startswith('MODAL_OVERVIEW_PROLOGUE '))
        self.assertIn('esp=00fffff8', prologue)
        self.assertIn('after_first_push=1 saved_ebx=00000063 return_sentinel=00406fa1', prologue)
        self.assertFalse(any(row.startswith('MODAL_OVERVIEW_ENTRY') for row in rows))
        for failure in ('missing_push', 'wrong_sentinel', 'wrong_saved_ebx', 'wrong_index'):
            with self.subTest(failure=failure):
                mem, reg, enabled = snapshots[81]
                mem, reg, enabled, observed = Memory(mem), reg.copy(), enabled.copy(), []
                if failure == 'missing_push':
                    reg['esp'] = reg['$t4']
                    write(mem, reg['esp']+4, 0)
                elif failure == 'wrong_sentinel': write(mem, reg['esp']+4, 0x406FA0)
                elif failure == 'wrong_saved_ebx': write(mem, reg['esp'], reg['ebx']+1)
                else: reg['eax'] = 1
                self.assertEqual(run(commands[81][1], mem, reg, enabled, observed), 'q')
                self.assertEqual(reg['$t0'], 1)
                self.assertFalse(any(row.startswith('MODAL_OVERVIEW_PROLOGUE ') for row in observed))
                self.assertIn('actual_t0=1 expected_t0=1', observed[0])
                self.assertIn('actual_tid=2345 expected_tid=2345', observed[0])
                self.assertIn('actual_eip=00422181 expected_eip=00422181', observed[0])
                self.assertIn('expected_esp=00fffff8', observed[0])

    def test_skipped_prologue_remains_rejected_with_actionable_expected_state(self):
        _, _, _, _, commands, snapshots = self.advance('castle_overview')
        memory, regs, enabled = snapshots[82]
        memory, regs, enabled, observed = Memory(memory), regs.copy(), enabled.copy(), []
        regs['$t0'] = 1  # The original failure: present reached without entry.
        self.assertEqual(run(commands[82][1], memory, regs, enabled, observed), 'q')
        self.assertIn('actual_t0=1 expected_t0=2', observed[0])
        self.assertIn('actual_eip=0042239a expected_eip=0042239a', observed[0])
        self.assertIn('actual_esp=00ffffc4 expected_esp=00ffffc4', observed[0])
        self.assertNotIn('MODAL_SURFDUMP_HOST_READY', observed)

    def test_independent_stack_and_native_call_contracts(self):
        # Native entry pushes + local bytes, including facilities' one saved
        # ECX that is still on-stack at the present return (POP is later).
        for name in ('school','smith','hospital','workshop'):
            self.assertEqual(probe.ROUTES[name].local_stack_bytes,4*4+0x400+4)
        self.assertEqual(probe.ROUTES['peasants'].local_stack_bytes,6*4+0x400)
        self.assertEqual(probe.ROUTES['barracks'].local_stack_bytes,6*4)
        self.assertEqual(probe.ROUTES['castle_overview'].local_stack_bytes,6*4+0x20)
        self.assertEqual(probe.CALLBACK+len(bytes.fromhex('ffd1')),0x42262E)
        self.assertEqual(probe.ROUTES['school'].stop_va,0x43DA53)
        self.assertEqual(probe.ROUTES['castle_overview'].stop_va,0x42239F)
        self.assertNotEqual(probe.ROUTES['castle_overview'].stop_va,0x422333)


@unittest.skipUnless(ORIGINAL.is_file(), 'user-owned original required for offline exact reconstruction')
class ImageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original=ORIGINAL.read_bytes()
        cls.prepared={r:probe.canonical_template(cls.original,r) for r in RESOLUTIONS}

    def packet(self, resolution='800x600', route='school', **overrides):
        image,_,_,template=self.prepared[resolution]
        args=dict(candidate_sha256=probe.sha(image),stage=probe.STAGE,resolution=resolution,route=route,
                  availability='existing_flags',castle_index=0,rendered_probe=template)
        args.update(overrides)
        return probe.build_screen_probe(self.original,image,**args)

    def test_actual_six_geometry_packets_bind_exact_candidate_and_keep_map_template(self):
        for resolution in RESOLUTIONS:
            with self.subTest(resolution=resolution):
                packet=self.packet(resolution)
                self.assertEqual(packet['map_probe_template'],self.prepared[resolution][3])
                self.assertEqual(packet['map_probe_template'].count(probe.DUMP_TOKEN),1)
                self.assertIn('SCROLL_VISDUMP',packet['map_probe_template'])
                self.assertIn('SURFDUMP_READY',packet['map_probe_template'])
                self.assertIn(self.prepared[resolution][2].strip(),packet['map_probe_template'])
                self.assertFalse(packet['runtime_ready']); self.assertFalse(packet['manual_input_proof'])
                self.assertTrue(packet['paused_capture'])
                self.assertEqual(packet['final_ready_marker'],'MODAL_SURFDUMP_READY')
                self.assertLess(max(map(len,packet['startup_commands_before_final_g'].splitlines())),4096)
                line=next(x for x in packet['map_probe_template'].splitlines() if probe.DUMP_TOKEN in x)
                self.assertLess(len(line.replace(probe.DUMP_TOKEN,packet['handoff_action'])),4096)

    def test_all_native_spans_and_loaded_predicates_authenticate_actual_image(self):
        for name in probe.ROUTES:
            with self.subTest(route=name):
                packet=self.packet(route=name)
                memory=Memory()
                diagnostic_regs={'$t0':0,'$tid':0x1234,'eip':0x401000,'esp':0x1000000}
                self.assertIn('.printf "MODAL_REJECT reason=loaded_bytes ',packet['byte_checks_before_first_breakpoint'])
                self.assertNotIn(r'\"',packet['byte_checks_before_first_breakpoint'])
                self.assertNotIn(r'\\n',packet['byte_checks_before_first_breakpoint'])
                for span in packet['byte_spans']:
                    for i,byte in enumerate(bytes.fromhex(span['old_hex'])): memory[span['va']+i]=byte
                self.assertIsNone(run(packet['byte_checks_before_first_breakpoint'],memory,{},set(),[]))
                for span in packet['byte_spans']:
                    va=span['va']; old=memory[va]; memory[va]^=1
                    self.assertEqual(run(packet['byte_checks_before_first_breakpoint'],memory,diagnostic_regs,set(),[]),'q')
                    memory[va]=old
                call=next(row for row in packet['byte_spans'] if row['va']==probe.ROUTES[name].present_call_va)
                self.assertEqual(call['va']+5+struct.unpack('<i',bytes.fromhex(call['old_hex'])[1:])[0],0x460EA0)
                entry=next(row for row in packet['byte_spans'] if row['va']==0x422180)
                self.assertTrue(entry['old_hex'].startswith('5351'))  # PUSH EBX; PUSH ECX
                self.assertEqual(packet['breakpoint_commands']['81']['va'],0x422181)

    def test_unknown_options_candidate_and_changed_template_fail_closed(self):
        for overrides in ({'route':'court'},{'route':'recruitment'},{'route':'tower'},
                          {'route':'battle_initial'},{'availability':'natural'},{'castle_index':4},
                          {'castle_index':True},{'minimap_viewport':1},{'stage':'stable'},
                          {'candidate_sha256':'0'*64},{'rendered_probe':self.prepared['800x600'][3].replace('SCROLL_VISDUMP','HIDDEN')},
                          {'rendered_probe':self.prepared['800x600'][3]+probe.DUMP_TOKEN}):
            with self.subTest(overrides=overrides),self.assertRaises(ValueError): self.packet(**overrides)
        image,_,_,template=self.prepared['800x600']; bad=bytearray(image); bad[-1]^=1
        with self.assertRaisesRegex(ValueError,'reconstruction'):
            probe.build_screen_probe(self.original,bytes(bad),candidate_sha256=probe.sha(bad),stage=probe.STAGE,
                resolution='800x600',route='school',availability='existing_flags',castle_index=0,rendered_probe=template)

    def test_crlf_template_normalization_is_explicit_and_no_output_files(self):
        packet=self.packet(rendered_probe=self.prepared['800x600'][3].replace('\n','\r\n'))
        self.assertEqual(packet['map_template_sha256'],probe.sha(self.prepared['800x600'][3].encode('ascii')))
        self.assertFalse(any(x in packet['startup_commands_before_final_g'].lower() for x in ('.writemem','sendinput','postmessage')))
        self.assertFalse(any(x in packet['handoff_action'].lower() for x in ('00544cfc','00544d00','005451c0')))


if __name__ == '__main__':
    unittest.main()
