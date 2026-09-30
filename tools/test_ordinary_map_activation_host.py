"""Portable activation-observer source contracts; no compiler or target process."""
from __future__ import annotations

import hashlib
from pathlib import Path
import re
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import ordinary_map_activation_host as host
import ordinary_map_pause_host as pause
import ordinary_map_phase_host as phase
import ordinary_map_startup as startup
import real_exe_smoke as smoke
import resolution_playability as runtime
from src.patcher import partial_tile_clip


def parent_source():
    return phase.render_source(pause.render_source(startup.render_source(
        runtime.observation_source(smoke.HARNESS), 1920, 1080)))


def between(first, last):
    return host.CONTROLLER_SOURCE.split(first, 1)[1].split(last, 1)[0]


class ActivationHostTests(unittest.TestCase):
    def test_transform_reverses_exactly_to_current_composed_parent(self):
        parent = parent_source()
        transformed = host.render_source(parent)
        for old, new in reversed(host.source_replacements()):
            self.assertEqual(transformed.count(new), 1)
            transformed = transformed.replace(new, old, 1)
        self.assertEqual(transformed, parent)

    def test_existing_startup_phase_and_strict_input_contracts_remain_present(self):
        parent = parent_source()
        transformed = host.render_source(parent)
        for source in (pause.CONTROLLER_SOURCE, runtime.STATE_HELPER):
            self.assertIn(source, transformed)
        phase_definition = parent.split('struct NativePhaseController {', 1)[1].split(host._SNAPSHOT, 1)[0]
        self.assertIn(phase_definition, transformed)
        self.assertIn('cursor overflow or existing native button input', transformed)
        self.assertIn('write_input(0x544D04,1,0)', transformed)
        self.assertEqual(transformed.count('struct StartupController {'), 1)
        self.assertEqual(transformed.count('struct NativePhaseController {'), 1)

    def test_missing_or_duplicated_composition_anchors_fail_closed(self):
        parent = parent_source()
        for old, _new in host.source_replacements():
            for defect in (parent.replace(old, '', 1), parent + old):
                with self.subTest(anchor=old.splitlines()[0]), self.assertRaisesRegex(ValueError, 'anchor'):
                    host.render_source(defect)

    def test_reordered_handlers_and_constructors_or_false_startup_binding_fail(self):
        parent = parent_source()
        constructors = host._CONSTRUCTORS.splitlines(keepends=True)
        handlers = host._EVENT.splitlines(keepends=True)
        defects = (
            parent.replace(host._CONSTRUCTORS, constructors[1] + constructors[0] + constructors[2]),
            parent.replace(host._EVENT, handlers[1] + handlers[0]),
            parent.replace('&startup.retired);', 'nullptr);'),
            parent.replace(host._CONSTRUCTORS, '\n'.join(constructors)),
        )
        for defect in defects:
            with self.assertRaisesRegex(ValueError, 'anchor'): host.render_source(defect)

    def test_requires_all_owned_controllers_and_rejects_reapplication_or_nontext(self):
        parent = parent_source()
        for declaration in ('struct StartupController {', 'struct PauseLeaseController {', 'struct NativePhaseController {'):
            with self.assertRaisesRegex(ValueError, 'controllers required'):
                host.render_source(parent.replace(declaration, 'struct MissingController {'))
        with self.assertRaisesRegex(ValueError, 'already contains'):
            host.render_source(host.render_source(parent))
        with self.assertRaises(TypeError): host.render_source(b'not text')

    def test_one_primary_hardware_slot_and_no_target_writes_or_activation_requests(self):
        source = host.CONTROLLER_SOURCE
        self.assertEqual(source.count('AddBreakpoint('), 1)
        self.assertIn('AddBreakpoint(DEBUG_BREAKPOINT_DATA,DEBUG_ANY_ID,&bp)', source)
        self.assertIn('SetDataParameters(1,DEBUG_BREAK_EXECUTE)', source)
        self.assertIn('SetMatchThreadId(engine_thread)', source)
        rotate = between('    void rotate(', '    void emit(')
        self.assertNotIn('AddBreakpoint(', rotate)
        self.assertIn('bp->SetOffset(target)', rotate)
        for forbidden in ('WriteVirtual', 'SetValue', 'SetInstructionOffset', 'SetStackOffset',
                          'SendInput', 'PostMessage', 'SendMessage', 'SetForegroundWindow',
                          'SetCursorPos', 'DEBUG_BREAKPOINT_CODE', 's.command(', 'approval_record'):
            self.assertNotIn(forbidden, source)

    def test_initial_arm_binds_existing_host_interval_before_first_go(self):
        source = host.render_source(parent_source())
        constructor = source.index('        NativeActivationController activation(')
        start = source.index('ULONGLONG start=GetTickCount64(),next=start+10000;')
        arm = source.index('        activation.arm_initial(start,start+')
        go = source.index(host._GO)
        self.assertLess(source.index('        StartupController startup('), constructor)
        self.assertLess(source.index('        NativePhaseController phases('), constructor)
        self.assertLess(constructor, start)
        self.assertLess(start, arm)
        self.assertLess(arm, go)
        initial = between('    void arm_initial(', '    void require_pending_deadline(')
        self.assertIn('host_start>now', initial)
        self.assertIn('bound<=now', initial)
        self.assertIn('bound-host_start<10000 || bound-host_start>180000', initial)
        self.assertIn('host_deadline=bound', initial)
        self.assertLess(initial.index('verify_anchors()'), initial.index('AddBreakpoint('))
        self.assertIn('!startup_retired || *startup_retired', source)

    def test_startup_handles_first_activation_before_foreign_phase_rejection(self):
        source = host.render_source(parent_source())
        ordered = ('if (startup.on_event(', 'if (activation.on_event(', 'if (phases.on_event(')
        self.assertLess(source.index(ordered[0]), source.index(ordered[1]))
        self.assertLess(source.index(ordered[1]), source.index(ordered[2]))
        self.assertIn('            activation.service();\n' + host._SERVICE, source)
        self.assertIn('        activation.finish();\n' + host._FINISH, source)

    def test_owned_event_requires_exact_retained_process_thread_bp_and_instruction(self):
        event = between('    bool on_event(', '        char fields[768];')
        for guard in ('info.Id!=bp_id', 'current_id!=bp_id', 'process!=engine_process',
                      'thread!=engine_thread', 'used!=sizeof(info)', 'ip!=target', 'offset!=target',
                      'reg("eip")!=target', 'breakpoint_type!=DEBUG_BREAKPOINT_DATA',
                      'processor_type!=IMAGE_FILE_MACHINE_I386', 'data_size!=1', 'access!=DEBUG_BREAK_EXECUTE'):
            self.assertIn(guard, event)
        context = between('    void retained_context()', '    void verify_anchors()')
        for guard in ('owner.verify_token()', 'owner.verify_owner()', 'status!=DEBUG_STATUS_BREAK',
                      'pid!=s.owned_pid', 'tid!=s.primary_tid', 'process!=engine_process', 'thread!=engine_thread'):
            self.assertIn(guard, context)

    def test_native_lowword_skips_and_mouse_then_keyboard_order_are_retained(self):
        source = host.CONTROLLER_SOURCE
        self.assertIn('low=wparam&0xffff', source)
        self.assertIn('rotate(low<=1?outer_call():0x4618A6,low<=1?OuterCall:WndProcRet)', source)
        outer = between('        if(step==OuterCall)', '        if(step==DeviceCall)')
        self.assertLess(outer.index('if(mouse_ready)devices.push_back(true)'),
                        outer.index('if(keyboard_ready)devices.push_back(false)'))
        self.assertIn('if(s.word(address(0x5452D4)))throw', outer)
        self.assertIn('devices.empty()?OuterReturn:DeviceCall', outer)
        self.assertIn('low==1?(mouse?0x47BF63:0x47BF4D):(mouse?0x47BFB3:0x47BF9D)', source)
        self.assertIn('return low==1?0x1c:0x20', source)

    def test_stack_arguments_device_and_hresult_pairing_before_next_call(self):
        call = between('        if(step==DeviceCall)', '        if(step==DeviceReturn)')
        returned = between('        if(step==DeviceReturn)', '        if(step==OuterReturn)')
        for guard in ('reg("esp")!=branch_esp-20', 'reg("eax")!=device', 'reg("edx")!=vtable',
                      's.word(branch_esp-20)!=device', '!pointer(device)', '!pointer(vtable,method_slot()+4)'):
            self.assertIn(guard, call)
        identity = between('    void require_device()', '    void resume()')
        self.assertIn('s.word(branch_esp-4)!=address(outer_return())', identity)
        self.assertIn('s.word(device_field())!=device', identity)
        self.assertIn('s.word(device)!=vtable', identity)
        self.assertIn('s.word(vtable+method_slot())!=method', identity)
        self.assertIn('reg("esp")!=branch_esp-16', returned)
        self.assertLess(returned.index('last_hresult=reg("eax")'), returned.index('emit("device_return"'))
        self.assertLess(returned.index('emit("device_return"'), returned.index('++device_index'))
        self.assertIn('result!=(devices.empty()?address(0x545198):last_hresult)', host.CONTROLLER_SOURCE)

    def test_wndproc_return_is_pre_ret_with_unchanged_native_arguments(self):
        pending = between('    void require_pending()', '    ULONG outer_call()')
        for guard in ('s.word(entry_esp)!=wndproc_return', 's.word(branch_esp+20)!=hwnd',
                      's.word(branch_esp+24)!=message', 's.word(branch_esp+28)!=wparam',
                      's.word(branch_esp+32)!=lparam'):
            self.assertIn(guard, pending)
        end = between('        if(step==WndProcRet)', '        throw std::runtime_error("activation owned breakpoint')
        self.assertIn('reg("esp")!=entry_esp || reg("eax")!=0', end)
        self.assertIn('address(0x4618A6),entry_esp,entry_esp,wndproc_return,hwnd,message,wparam,low,lparam', end)

    def test_deadline_and_cap_never_extend_and_incomplete_transactions_fail(self):
        source = host.CONTROLLER_SOURCE
        self.assertEqual(host.PENDING_MS, 20000)
        self.assertEqual(host.MAX_TRANSACTIONS, 16)
        self.assertIn('pending_deadline=tick+20000', source)
        self.assertIn('if(pending_deadline>host_deadline)pending_deadline=host_deadline', source)
        self.assertIn('now>=host_deadline || now>=pending_deadline', source)
        self.assertIn('tick>~static_cast<ULONGLONG>(0)-20000', source)
        self.assertIn('tx!=transactions || transactions>=16', source)
        self.assertIn('if(transactions==16)retire("transaction_cap")', source)
        service = between('    void service()', '    bool on_event(')
        self.assertIn('require_pending_deadline()', service)
        self.assertNotIn('s.word(', service)
        retire = between('    void retire(', '    void service()')
        self.assertLess(retire.index('if(pending)throw'), retire.index('clear()'))
        self.assertLess(retire.index('clear()'), retire.index('emit("finish"'))
        self.assertLess(retire.index('clear()'), retire.index('ULONGLONG tick=GetTickCount64()'))
        self.assertIn('if(!strcmp(reason,"host_interval") && tick>=host_deadline)reason="host_deadline"', retire)
        self.assertIn('emit("finish",0,fields,tick)', retire)
        finish = between('    void finish()', '\n};')
        self.assertIn('if(!enabled || finished)return', finish)
        self.assertIn('if(pending)throw', finish)
        self.assertIn('retire("host_interval")', finish)

    def test_log_protocol_has_exact_common_and_kind_fields_and_no_acceptance(self):
        common = between('    void emit(', '    void arm_initial(')
        keys = set(re.findall(r'\\"([a-z_0-9]+)\\":', common))
        self.assertEqual(keys, set('schema kind tx pid tid creation_filetime image_base controller_sha256 session_id tick_ms startup_retired'.split()))
        cases = {
            'start': ('    void arm_initial(', '    void require_pending_deadline(', 'initial_stop_armed host_start_tick_ms deadline_tick_ms max_transactions'),
            'activation': ('        if(step==Activation)', '        require_pending();', 'branch_esp entry_esp hwnd message wparam wparam_low16 lparam wndproc_return deadline_tick_ms'),
            'outer_call': ('        if(step==OuterCall)', '        if(step==DeviceCall)', 'operation call_va return_va call_esp backend mouse_ready keyboard_ready joystick_ready'),
            'device_call': ('        if(step==DeviceCall)', '        if(step==DeviceReturn)', 'device_kind call_va return_va call_esp device vtable method'),
            'device_return': ('        if(step==DeviceReturn)', '        if(step==OuterReturn)', 'device_kind return_va return_esp hresult'),
            'outer_return': ('        if(step==OuterReturn)', '        if(step==WndProcRet)', 'return_va return_esp eax'),
            'end': ('        if(step==WndProcRet)', '        throw std::runtime_error("activation owned breakpoint', 'epilogue_va epilogue_esp entry_esp wndproc_return hwnd message wparam wparam_low16 lparam'),
            'finish': ('    void retire(', '    void service()', 'transactions pending reason'),
        }
        for kind, (first, last, expected) in cases.items():
            with self.subTest(kind=kind):
                self.assertEqual(set(re.findall(r'\\"([a-z_0-9]+)\\":', between(first, last))), set(expected.split()))
        self.assertIn('printf("REAL_ACTIVATION_V1 %s\\n",json);fflush(stdout)', common)
        self.assertIn('seen_retired && !*startup_retired', common)
        for forbidden in ('hidden_success', 'manual_input_proof', 'promotion_ready', 'input_verified'):
            self.assertNotIn(forbidden, host.CONTROLLER_SOURCE)

    def test_source_identity_and_candidate_loaded_pins_precede_hardware_arm(self):
        source = host.render_source(parent_source())
        self.assertIn('return "' + hashlib.sha256(Path(host.__file__).read_bytes()).hexdigest() + '";', source)
        self.assertNotIn('@ACTIVATION_', source)
        for va, raw in host.NATIVE_ANCHORS.items():
            self.assertIn(f'anchor(0x{va:06X},"{raw}");', source)
        anchor = between('    void anchor(', '    NativeActivationController(')
        self.assertIn('StartupController::disk_read(disk,va,expected.size())!=expected', anchor)
        self.assertIn('s.read(address(va),static_cast<ULONG>(expected.size()))!=expected', anchor)

    def test_independent_native_body_pins_and_startup_bypass_disjointness(self):
        self.assertEqual(host.ORIGINAL_SHA256, '500055d77d03d514e8d3168506bd10f67cd8569bcc450604ff8192f46cdaf3ae')
        expected = {0x47BF30: 'f1a3c7b2e62c0f7c977f18b5a0f134477d84663344abd79e221130ec85ab0827',
                    0x47BF80: '9d0b0e3bfb56272638bce0f20594ed763c12262f8f4c5b755bdab7031088bef8'}
        for va, digest in expected.items():
            body = bytes.fromhex(host.NATIVE_ANCHORS[va])
            self.assertEqual(len(body), 69)
            self.assertEqual(hashlib.sha256(body).hexdigest(), digest)
            self.assertEqual(body[0x36:0x38], b'\xEB\xD6')  # Mouse return jumps back to keyboard test.
        self.assertEqual(host.NATIVE_ANCHORS[0x46189A], '891dd499510031c05d5f5e5bc21000')
        for va, raw in host.NATIVE_ANCHORS.items():
            for bypass in (0x47BD66, 0x47BDAE, 0x47BFD0):
                self.assertFalse(va <= bypass < va + len(bytes.fromhex(raw)))

    def test_unknown_original_fails_before_any_offset_lookup(self):
        with patch.object(partial_tile_clip, 'file_offset') as lookup:
            for data in (b'not an original', bytearray(b'not bytes'), None):
                with self.assertRaisesRegex(ValueError, 'Unknown original'): host.verify_original_anchors(data)
            lookup.assert_not_called()

    def test_all_old_byte_checks_fail_independently_in_tiny_artificial_mapping(self):
        data = bytearray()
        offsets = {}
        for va, raw in host.NATIVE_ANCHORS.items():
            offsets[va] = len(data)
            data.extend(bytes.fromhex(raw))
            data.extend(b'\xA5' * 4)
        original = bytes(data)
        def offset(_data, va, size):
            self.assertEqual(size, len(bytes.fromhex(host.NATIVE_ANCHORS[va])))
            return offsets[va]
        with patch.object(partial_tile_clip, 'file_offset', side_effect=offset):
            with patch.object(host, 'ORIGINAL_SHA256', hashlib.sha256(original).hexdigest()):
                self.assertEqual(host.verify_original_anchors(original), host.NATIVE_ANCHORS)
            for va, at in offsets.items():
                changed = bytearray(original)
                changed[at] ^= 1
                changed = bytes(changed)
                # Reauthenticate the artificial fixture to reach each independent byte guard.
                with self.subTest(va=hex(va)), patch.object(host, 'ORIGINAL_SHA256', hashlib.sha256(changed).hexdigest()):
                    with self.assertRaisesRegex(ValueError, f'anchor differs at {va:08x}'):
                        host.verify_original_anchors(changed)


if __name__ == '__main__':
    unittest.main(verbosity=2)
