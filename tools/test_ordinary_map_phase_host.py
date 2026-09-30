"""Portable source contracts; no compiler, debugger, game or native input."""
from __future__ import annotations

import hashlib
from pathlib import Path
import re
import unittest

import ordinary_map_phase_host as host
import ordinary_map_pause_host as pause
import real_exe_smoke as smoke
import resolution_playability as runtime


def parent_source():
    return pause.render_source(runtime.observation_source(smoke.HARNESS))


class PhaseHostTests(unittest.TestCase):
    def test_only_explicit_replacements_change_the_parent(self):
        parent = parent_source()
        rendered = host.render_source(parent)
        for old, new in reversed(host.source_replacements()):
            self.assertEqual(rendered.count(new), 1)
            rendered = rendered.replace(new, old, 1)
        self.assertEqual(rendered, parent)

    def test_observation_and_strict_generic_pause_contracts_are_preserved(self):
        rendered = host.render_source(parent_source())
        self.assertIn(pause.CONTROLLER_SOURCE, rendered)
        self.assertIn(runtime.STATE_HELPER, rendered)
        self.assertIn('    map_state(s,out,sample);', rendered)
        self.assertIn('seconds>180', rendered)

    def test_startup_composition_preserves_handler_order_and_owned_controllers(self):
        import ordinary_map_startup as startup
        source = startup.render_source(runtime.observation_source(smoke.HARNESS), 1024, 768)
        source = host.render_source(pause.render_source(source))
        self.assertLess(source.index('if (startup.on_event('), source.index('if (phases.on_event('))
        self.assertLess(source.index('if (phases.on_event('), source.index('if (ip==entry && !entered)'))
        for declaration in ('StartupController startup(', 'PauseLeaseController leases(', 'NativePhaseController phases('):
            self.assertEqual(source.count(declaration), 1)
        self.assertIn(pause.CONTROLLER_SOURCE, source)

    def test_missing_and_duplicate_anchors_reject(self):
        source = parent_source()
        for old, _new in host.source_replacements():
            with self.subTest(anchor=old, defect='missing'), self.assertRaisesRegex(ValueError, 'anchor'):
                host.render_source(source.replace(old, '', 1))
            with self.subTest(anchor=old, defect='duplicate'), self.assertRaisesRegex(ValueError, 'anchor'):
                host.render_source(source+old)

    def test_requires_generic_parent_and_rejects_second_application(self):
        with self.assertRaisesRegex(ValueError, 'generic pause'):
            host.render_source(smoke.HARNESS)
        with self.assertRaisesRegex(ValueError, 'already contains'):
            host.render_source(host.render_source(parent_source()))
        with self.assertRaises(TypeError):
            host.render_source(b'not text')

    def test_explicit_mode_keeps_five_and_six_argument_paths_disabled(self):
        rendered = host.render_source(parent_source())
        self.assertIn('argc!=5 && argc!=6 && argc!=7', rendered)
        self.assertIn('leases(s,argc>=6?argv[5]:nullptr,base)', rendered)
        self.assertIn('phases(leases,argc==7?argv[6]:nullptr', rendered)
        constructor = host.CONTROLLER_SOURCE.split('NativePhaseController(PauseLeaseController &parent,', 1)[1]
        self.assertLess(constructor.index('if (!mode) return;'), constructor.index('enabled=true;'))
        self.assertIn('strcmp(mode,"native-phase-v1")', constructor)
        self.assertIn('if (phases.enabled) phases.service(); else leases.service();', rendered)
        self.assertIn('if (!phases.enabled && GetTickCount64()>=next)', rendered)

    def test_native_dispatcher_anchor_excludes_the_patched_minimap_call(self):
        self.assertEqual(host.NATIVE_ANCHORS[0x4084A0], '53515256575583ec58')
        for address, value in host.NATIVE_ANCHORS.items():
            self.assertFalse(address <= 0x4084A9 < address+len(bytes.fromhex(value)))
        self.assertEqual(host.NATIVE_ANCHORS[0x40B233], 'e868d2ffff')
        self.assertEqual(host.NATIVE_ANCHORS[0x40B238], 'e9dcfeffff')
        self.assertEqual(host.NATIVE_ANCHORS[0x4087DC], 'e80f810500')
        self.assertEqual(host.NATIVE_ANCHORS[0x4608F0], 'f6402c010f95c025ff000000c3')

    def test_controller_identity_is_embedded_and_all_byte_anchors_are_emitted(self):
        rendered = host.render_source(parent_source())
        expected = hashlib.sha256(Path(host.__file__).read_bytes()).hexdigest()
        self.assertIn('return "'+expected+'";', rendered)
        self.assertNotIn('@PHASE_', rendered)
        for index, address in enumerate(host.NATIVE_ANCHORS):
            self.assertEqual(rendered.count(f'anchor(0x{address:06X},anchor_{index},sizeof(anchor_{index}));'), 1)

    def test_acknowledgment_has_the_exact_client_contract(self):
        acknowledgment = host.CONTROLLER_SOURCE.split('    void ack(', 1)[1].split('    void publish_ready', 1)[0]
        keys = re.findall(r'\\"([a-z_0-9]+)\\":', acknowledgment)
        expected = set('schema session_id request_seq status lease_id pid primary_tid creation_filetime image_base deadline_tick_ms paused phase controller_sha256 root_esp held_esp held_eip human_entry_seen postpoll_seen action_index capture_index binding_sha256 target_x target_y dispatch_seen dispatch_eip dispatch_esp dispatch_return predicate_observed predicate_value return_seen return_eip return_esp'.split())
        self.assertEqual(set(keys), expected)
        self.assertEqual(len(keys), len(expected))
        self.assertIn('char json[4096]', acknowledgment)
        self.assertIn('MOVEFILE_REPLACE_EXISTING|MOVEFILE_WRITE_THROUGH', acknowledgment)

    def test_maximum_canonical_click_request_fits_existing_bounded_reader(self):
        wire = f'CLASH_PHASE_V1 {"f"*32} {2**64-1} click {"e"*32} {"d"*32} 3839 2159 {"c"*64}\n'
        self.assertLessEqual(len(wire.encode('ascii')), 256)
        self.assertIn('owner.read_file("phase-request.txt",wire,last_sequence==0)', host.CONTROLLER_SOURCE)
        self.assertIn('generic pause requests forbidden in native phase mode', host.CONTROLLER_SOURCE)

    def test_target_write_scope_is_only_the_three_input_fields(self):
        source = host.CONTROLLER_SOURCE
        self.assertEqual(source.count('WriteVirtual('), 1)
        self.assertIn('original!=0x544CFC && original!=0x544D00 && original!=0x544D04', source)
        self.assertEqual(re.findall(r'write_input\((0x[0-9A-F]+),', source),
                         ['0x544CFC', '0x544D00', '0x544D04', '0x544D04'])
        for forbidden in ('SetValue(', 'SetValues(', 'SetThreadContext(', 'SetInstructionOffset(',
                          'SetStackOffset(', 'SendInput(', 'PostMessage(', 'SuspendThread(',
                          'EnumWindows(', 's.command('):
            self.assertNotIn(forbidden, source)
        self.assertIn('DEBUG_BREAKPOINT_DATA', source)
        self.assertIn('SetDataParameters(1,DEBUG_BREAK_EXECUTE)', source)
        self.assertNotIn('DEBUG_BREAKPOINT_CODE', source)

    def test_first_human_entry_waits_for_acquisition_without_running_startup_phases(self):
        source=host.CONTROLLER_SOURCE
        self.assertNotIn('AwaitHuman',source)
        service=source.split('    void service() {',1)[1].split('    void write_input(',1)[0]
        self.assertLess(service.index('if (!human_entry_seen) return;'),service.index('request(next)'))
        waiting=source.split('    void await_first_acquire() {',1)[1].split('    void service() {',1)[0]
        self.assertIn('first_human_acquire_waited || state!=Idle || !human_entry_seen',waiting)
        self.assertIn('first_human_acquire_waited=true;',waiting)
        self.assertIn('ULONGLONG until=GetTickCount64()+20000;',waiting)
        self.assertIn('deadline(until); owner.verify_owner(); reject_mixed_mailbox();',waiting)
        self.assertIn('deadline(until); accept_acquire(next);',waiting)
        self.assertIn('arm(phase_bp,phase_id,0x40B0D4); state=AwaitPostpoll; go(); return;',waiting)
        self.assertEqual(waiting.count('go();'),1)
        for forbidden in ('ack(', 'write_input(', 'pause_owned(', 'WaitForEvent(', 'SetValue('):
            self.assertNotIn(forbidden,waiting)
        acquisition=source.split('    void accept_acquire(',1)[1].split('    void await_first_acquire()',1)[0]
        self.assertIn('state!=Idle || next.operation!="acquire"',acquisition)
        self.assertIn('remember(next.lease); accept(next);',acquisition)
        human=source.split('        if (human) {',1)[1].split('        deadline(transition_deadline);',1)[0]
        self.assertIn('ip!=address(0x40B0A0) || state!=Idle',human)
        self.assertIn('bool first=!human_entry_seen;',human)
        self.assertIn('if (first) { await_first_acquire(); return true; }',human)
        self.assertLess(human.index('REAL_PHASE_HUMAN'),human.index('await_first_acquire();'))

    def test_human_and_caller_view_logs_read_only_measured_camera_and_cursor(self):
        source=host.CONTROLLER_SOURCE
        trace=source.split('    void trace_view(',1)[1].split('    void clear_bp(',1)[0]
        for expected in ('owner.verify_owner();', 'word(0x5202E4)', 'gd>0x7ffe0000-140016',
                         's.word(gd+140008)', 's.word(gd+140012)', 'word(0x544CFC)',
                         'word(0x544D00)', 's.read(address(0x54512C),1)', 'REAL_PHASE_VIEW'):
            self.assertIn(expected,trace)
        for forbidden in ('WriteVirtual(', 'write_input(', 'SetValue(', 's.command('):
            self.assertNotIn(forbidden,trace)
        self.assertEqual(source.count('trace_view("human-entry")'),1)
        self.assertEqual(source.count('trace_view("caller-hold")'),1)

    def test_exact_input_diagnostics_precede_unchanged_rejection_and_any_write(self):
        source=host.CONTROLLER_SOURCE
        click=source.split('    void click(',1)[1].split('    void hold() {',1)[0]
        for expected in ('word(0x544D04)', 's.read(address(0x5451C0),1)',
                         's.read(address(0x5451C8),1)', 'REAL_PHASE_PRECLICK',
                         'raw_target_valid=%d raw_target_x=%llu raw_target_y=%llu',
                         'resolved=%08lx primary=%02lx secondary=%02lx',
                         'x=shift<=31?static_cast<ULONGLONG>(next.x)<<shift:0',
                         'y=shift<=31?static_cast<ULONGLONG>(next.y)<<shift:0',
                         'x>0x7fffffff || y>0x7fffffff || resolved!=0 || (primary&0x80) || (secondary&0x80)'):
            self.assertIn(expected,click)
        diagnostic=click.index('REAL_PHASE_PRECLICK')
        self.assertLess(diagnostic,click.index('if (width<640'))
        self.assertLess(diagnostic,click.index('if (x>0x7fffffff'))
        self.assertLess(click.index('phase cursor overflow or existing native button input'),click.index('remember(next.successor)'))
        self.assertLess(click.index('phase cursor overflow or existing native button input'),click.index('write_input('))
        trace=source.split('    void trace_view(',1)[1].split('    void clear_bp(',1)[0]
        for expected in ('word(0x544D04)', 's.read(address(0x5451C0),1)',
                         's.read(address(0x5451C8),1)', 'word(0x51D4C0)',
                         'resolved=%08lx primary=%02lx secondary=%02lx'):
            self.assertIn(expected,trace)
        self.assertNotIn('write_input(',trace)

    def test_removed_breakpoint_lifetime_is_owned_by_dbgeng(self):
        source=host.CONTROLLER_SOURCE
        self.assertNotIn('->Release(',source)
        clear=source.split('    void clear_bp(',1)[1].split('    void arm(',1)[0]
        self.assertLess(clear.index('bp=nullptr;'),clear.index('RemoveBreakpoint(removed)'))
        self.assertLess(clear.index('id=DEBUG_ANY_ID;'),clear.index('RemoveBreakpoint(removed)'))
        self.assertNotIn('removed->',clear)
        self.assertIn('check(s.control->RemoveBreakpoint(removed)',clear)
        destructor=source.split('    ~NativePhaseController() {',1)[1].split('    void remember(',1)[0]
        self.assertEqual(destructor.count('RemoveBreakpoint('),1)

    def test_natural_phase_order_and_return_guard_remain_explicit(self):
        source = host.CONTROLLER_SOURCE
        self.assertIn('arm(human_bp,human_id,0x40B0A0)', source)
        self.assertIn('arm(phase_bp,phase_id,0x40B0D4)', source)
        self.assertIn('arm(phase_bp,phase_id,0x40B233)', source)
        self.assertIn('arm(phase_bp,phase_id,0x4084A0)', source)
        self.assertIn('arm(phase_bp,phase_id,0x4087E1); arm(return_bp,return_id,0x40B238)', source)
        self.assertIn('stack()!=root_esp-32 || s.word(stack())!=address(0x40B238)', source)
        self.assertIn('stack()!=dispatch_esp-112', source)
        self.assertIn('stack()!=root_esp-28', source)
        self.assertIn('predicate_value=eax()', source)
        self.assertIn('predicate_value>1', source)
        self.assertNotIn('predicate_value!=1', source)
        self.assertIn('snapshot(s,out,capture_index,proxy)', source)


if __name__ == '__main__':
    unittest.main(verbosity=2)
