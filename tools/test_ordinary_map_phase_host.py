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
        self.assertIn('strcmp(argv[4],"proxy")==0,&startup.retired);', source)
        for old, new in reversed(host.source_replacements(startup_composed=True)):
            self.assertEqual(source.count(new), 1)
            source = source.replace(new, old, 1)
        expected = pause.render_source(startup.render_source(runtime.observation_source(smoke.HARNESS), 1024, 768))
        self.assertEqual(source, expected)

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
        self.assertIn('strcmp(argv[4],"proxy")==0,nullptr);', rendered)
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
        self.assertIn('arm(phase_bp,phase_id,0x40B0D4); state=AwaitPostpoll; start_mouse_poll(); go(); return;',waiting)
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

    def test_native_mouse_body_and_three_whitelisted_call_sites_are_authenticated(self):
        native = bytes.fromhex(host.MOUSE_NATIVE_BYTES)
        self.assertEqual(len(native), 154)
        self.assertEqual(hashlib.sha256(native).hexdigest(), host.MOUSE_NATIVE_SHA256)
        self.assertEqual(native[0x47C029-0x47BFD0:0x47C02C-0x47BFD0], bytes.fromhex('ff5124'))
        self.assertEqual(native[0x47C02C-0x47BFD0:0x47C03C-0x47BFD0],
                         bytes.fromhex('3d1e00078075098b4308508b10ff521c'))
        self.assertEqual(native[0x47C065-0x47BFD0:], bytes.fromhex('e977ffffff'))
        self.assertEqual(host.NATIVE_ANCHORS[0x47BFD0], host.MOUSE_NATIVE_BYTES)
        for call, raw, returned in ((0x4463B8, 'e8135c0300', 0x4463BD),
                                    (0x46092B, 'e8a0b60100', 0x460930),
                                    (0x460A5C, 'e86fb50100', 0x460A61)):
            self.assertEqual(host.NATIVE_ANCHORS[call], raw)
            self.assertEqual(call+5, returned)
            displacement = int.from_bytes(bytes.fromhex(raw)[1:], 'little', signed=True)
            self.assertEqual(returned+displacement, 0x47BFD0)
        # 460A61 is a permitted patched continuation, outside the native CALL5.
        self.assertFalse(any(a <= 0x460A61 < a+len(bytes.fromhex(raw))
                             for a, raw in host.NATIVE_ANCHORS.items()))

    def test_genuine_startup_retirement_is_required_only_for_enabled_native_mode(self):
        source = host.CONTROLLER_SOURCE
        constructor = source.split('    NativePhaseController(', 1)[1].split('    ~NativePhaseController', 1)[0]
        self.assertLess(constructor.index('if (!mode) return;'), constructor.index('if (!startup_retired)'))
        self.assertLess(constructor.index('if (!startup_retired)'), constructor.index('enabled=true;'))
        retired = source.split('    void require_startup_retired()', 1)[1].split('    static std::string bytes_hex', 1)[0]
        self.assertIn('!startup_retired || !*startup_retired', retired)
        human = source.split('        if (human) {', 1)[1].split('        deadline(transition_deadline);', 1)[0]
        self.assertLess(human.index('require_startup_retired();'), human.index('root_esp=stack();'))
        self.assertIn('human_return=s.word(root_esp);', human)
        import ordinary_map_startup as startup
        parent = pause.render_source(startup.render_source(runtime.observation_source(smoke.HARNESS), 1920, 1080))
        for defective in (parent.replace(host._STARTUP_CONSTRUCTOR, '', 1),
                          parent+host._STARTUP_CONSTRUCTOR,
                          parent.replace('struct StartupController {', 'struct OtherStartupController {', 1)):
            with self.assertRaisesRegex(ValueError, 'Startup composition'):
                host.render_source(defective)
        with self.assertRaises(TypeError):
            host.source_replacements(startup_composed='true')

    def test_mouse_trace_uses_one_rotating_hardware_slot_between_actions_only(self):
        source = host.CONTROLLER_SOURCE
        self.assertEqual(source.count('IDebugBreakpoint *mouse_bp=nullptr;'), 1)
        telemetry = source.split('    void require_mouse_epoch()', 1)[1].split('    void remember(', 1)[0]
        self.assertEqual(re.findall(r'arm\(mouse_bp,mouse_id,(0x[0-9A-F]+)\)', telemetry),
                         ['0x47C029', '0x47C02C', '0x47C065', '0x47C029'])
        self.assertIn('(state!=AwaitPostpoll && state!=AwaitCaller) || return_bp', telemetry)
        self.assertIn('bool mouse=mouse_bp && event.Id==mouse_id;', source)
        owner_event = source.split('    bool on_event(', 1)[1]
        self.assertLess(owner_event.index('used!=sizeof(event)'), owner_event.index('if (mouse) { mouse_event(ip);'))
        self.assertIn('actual_process!=process || actual_thread!=thread', owner_event)
        self.assertIn('process!=owned_process || thread!=primary', owner_event)
        self.assertIn('current_ip!=ip || breakpoint_ip!=ip', telemetry)
        self.assertEqual(source.count('start_mouse_poll();'), 3)
        returned = source.split('        if (returned && state==AwaitPredicateOrReturn', 1)[1]
        self.assertLess(returned.index('clear_bp(return_bp,return_id);'), returned.index('start_mouse_poll();'))

    def test_mouse_epoch_is_time_count_and_retained_stack_bounded(self):
        self.assertEqual(host.LEASE_MS, 20_000)
        self.assertEqual(host.MOUSE_POLL_LIMIT, 64)
        self.assertEqual(host.MOUSE_STACK_SPAN, 0x4000)
        source = host.CONTROLLER_SOURCE
        telemetry = source.split('    void require_mouse_epoch()', 1)[1].split('    void remember(', 1)[0]
        for contract in ('deadline(mouse_deadline)', 'transition_deadline-now>20000',
                         'mouse_polls>=64', 'root_esp<0x14000', 'root_esp-0x4000',
                         'static_cast<ULONGLONG>(mouse_call_esp)+12', 'entry=frame+0x6c,buffer=frame+0x50',
                         'entry>static_cast<ULONGLONG>(root_esp)-28', 'buffer+16>root_esp',
                         'entry+4>root_esp', 's.word(root_esp)!=human_return'):
            self.assertIn(contract, telemetry)
        self.assertIn('mouse_epoch==0xffffffff', telemetry)
        self.assertEqual(telemetry.count('stack()!=mouse_frame_esp'), 2)

    def test_mouse_call_keeps_device_args_vtable_method_and_caller_bound(self):
        source = host.CONTROLLER_SOURCE
        telemetry = source.split('    void mouse_device_identity()', 1)[1].split('    void retire_mouse_poll()', 1)[0]
        for contract in ('reg("ebx")!=address(0x545198)', 'word(0x5451A0)!=mouse_device',
                         's.word(mouse_device)!=mouse_vtable', 's.word(mouse_vtable+0x24)!=mouse_method',
                         's.word(mouse_entry_esp)!=mouse_caller', 's.word(mouse_call_esp+4)!=16',
                         's.word(mouse_call_esp+8)!=mouse_buffer', 'reg("eax")!=device || reg("ecx")!=vtable',
                         'device<0x10000 || device>=0x7ffe0000 || (device&3)',
                         'vtable<0x10000 || vtable>0x7ffe0000-0x28 || (vtable&3)',
                         'method<0x10000 || method>=0x7ffe0000',
                         'device!=mouse_device || vtable!=mouse_vtable || method!=mouse_method',
                         'mouse_caller!=address(0x4463BD)', 'mouse_caller!=address(0x460930)',
                         'mouse_caller!=address(0x460A61)'):
            self.assertIn(contract, telemetry)
        self.assertEqual(telemetry.count('mouse_device_identity();'), 3)

    def test_mouse_hresult_and_exact_full_backend_copy_words_are_observed_read_only(self):
        source = host.CONTROLLER_SOURCE
        telemetry = source.split('    void mouse_event(', 1)[1].split('    void retire_mouse_poll()', 1)[0]
        for forbidden in ('WriteVirtual(', 'write_input(', 'SetValue(', 'SetValues(', 'SetInstructionOffset(',
                          'SetStackOffset(', 's.command(', 'ack(', 'snapshot('):
            self.assertNotRegex(telemetry, r'\b'+re.escape(forbidden))
        returned = telemetry.split('mouse_step==MouseReturn', 1)[1].split('mouse_step==MouseCopy', 1)[0]
        self.assertLess(returned.index('mouse_hresult=eax();'), returned.index('mouse_device_identity();'))
        self.assertLess(returned.index('mouse_log("return"'), returned.index('arm(mouse_bp,mouse_id,0x47C065)'))
        for contract in ('s.read(mouse_buffer,16)', 'memcpy(&x,local.data(),4)', 'memcpy(&y,local.data()+4,4)',
                         'bx=word(0x5451A8),by=word(0x5451AC)', 'primary=word(0x5451C0)',
                         'middle=word(0x5451C4),secondary=word(0x5451C8)',
                         'bx!=x || by!=y || primary!=local[12] || secondary!=local[13] || middle!=local[14]'):
            self.assertIn(contract, telemetry)
        self.assertNotIn('mouse_hresult==', telemetry)
        self.assertNotIn('mouse_hresult!=', telemetry)
        self.assertIn('word(0x544D04),word(0x544CFC),word(0x544D00)', telemetry)

    def test_trace_rows_have_exact_consumer_fields_without_changing_ack(self):
        source = host.CONTROLLER_SOURCE
        common = source.split('    void mouse_log(', 1)[1].split('    void require_mouse_epoch()', 1)[0]
        common_keys = set(re.findall(r'\\"([a-z_0-9]+)\\":', common))
        self.assertEqual(common_keys, set('schema kind epoch action_index pid tid creation_filetime image_base root_esp controller_sha256 session_id'.split()))
        self.assertIn('REAL_MOUSE_POLL_V1 %s\\n', common)
        self.assertIn(host.MOUSE_POLL_SCHEMA, common)
        regions = {
            'start': source.split('    void start_mouse_poll()', 1)[1].split('    void mouse_device_identity()', 1)[0],
            'call': source.split('mouse_step==MouseCall &&', 1)[1].split('mouse_step==MouseReturn &&', 1)[0],
            'return': source.split('mouse_step==MouseReturn &&', 1)[1].split('mouse_step==MouseCopy &&', 1)[0],
            'copy': source.split('mouse_step==MouseCopy &&', 1)[1].split('    void retire_mouse_poll()', 1)[0],
            'end': source.split('    void retire_mouse_poll()', 1)[1].split('    void remember(', 1)[0],
        }
        expected = {
            'start': 'startup_retired deadline_tick_ms',
            'call': 'poll caller call_esp frame_esp entry_esp backend device vtable method buffer pre_hex',
            'return': 'poll return_esp hresult post_hex',
            'copy': 'poll copy_esp local_hex backend_x backend_y primary middle secondary resolved raw_x raw_y',
            'end': 'polls pending retired_before_hold reason',
        }
        for kind, region in regions.items():
            self.assertEqual(set(re.findall(r'\\"([a-z_0-9]+)\\":', region)), set(expected[kind].split()))
            self.assertIn('mouse_log("'+kind+'",fields)', region)

    def test_telemetry_retires_before_any_held_capture_ack_or_input_and_rejects_pending(self):
        source = host.CONTROLLER_SOURCE
        retirement = source.split('    void retire_mouse_poll()', 1)[1].split('    void remember(', 1)[0]
        self.assertIn('state!=AwaitCaller || mouse_pending || mouse_step!=MouseCall || mouse_polls!=mouse_poll', retirement)
        self.assertLess(retirement.index('clear_bp(mouse_bp,mouse_id);'), retirement.index('mouse_log("end"'))
        caller = source.split('phase && state==AwaitCaller &&', 1)[1].split('phase && state==AwaitDispatch &&', 1)[0]
        self.assertLess(caller.index('retire_mouse_poll();'), caller.index('hold();'))
        held = source.split('    void hold()', 1)[1].split('    bool on_event(', 1)[0]
        self.assertLess(held.index('mouse_active || mouse_bp || mouse_pending'), held.index('snapshot('))
        self.assertLess(held.index('snapshot('), held.index('ack("held"'))
        click = source.split('    void click(', 1)[1].split('    void hold()', 1)[0]
        self.assertLess(click.index('mouse_active || mouse_bp || mouse_pending'), click.index('ack("executing"'))
        self.assertLess(click.index('mouse_active || mouse_bp || mouse_pending'), click.index('write_input('))
        finish = source.split('    void finish()', 1)[1]
        self.assertIn('mouse_active || mouse_bp || mouse_pending', finish)


if __name__ == '__main__':
    unittest.main(verbosity=2)
