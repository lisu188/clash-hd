"""Mocked OS-delivery checks; no windows, cursor, runtime or screen capture."""
from contextlib import ExitStack
from copy import deepcopy
import ctypes
import unittest
from unittest.mock import patch

import menu_pulse_click as tool


class Clock:
    def __init__(self):
        self.elapsed = 0.0

    def time(self):
        return 1000.0 + self.elapsed

    def monotonic(self):
        return 100.0 + self.elapsed

    def sleep(self, duration):
        self.elapsed += duration


class DeliveryTests(unittest.TestCase):
    def test_each_event_requires_exactly_one_inserted_input(self):
        events = []
        def delivered(count, pointer, size):
            event = ctypes.cast(pointer, ctypes.POINTER(tool.INPUT)).contents
            events.append((count, size, event.type, event.union.mi.dx, event.union.mi.dy, event.union.mi.dwFlags))
            return 1
        with patch.object(tool.user32, 'SendInput', side_effect=delivered):
            self.assertIsNone(tool.send_rel(12, -8))
            self.assertIsNone(tool.send_button(tool.MOUSEEVENTF_LEFTDOWN))
            self.assertIsNone(tool.send_button(tool.MOUSEEVENTF_LEFTUP))
        self.assertEqual([row[-1] for row in events], [tool.MOUSEEVENTF_MOVE, tool.MOUSEEVENTF_LEFTDOWN, tool.MOUSEEVENTF_LEFTUP])
        self.assertEqual(events[0][2:5], (0, 12, -8))
        self.assertTrue(all(row[:2] == (1, ctypes.sizeof(tool.INPUT)) for row in events))
        for inserted in (0, 2):
            for emit in (lambda: tool.send_rel(1, 1), lambda: tool.send_button(tool.MOUSEEVENTF_LEFTDOWN)):
                with self.subTest(inserted=inserted), patch.object(tool.user32, 'SendInput', return_value=inserted), self.assertRaisesRegex(OSError, f'inserted {inserted}/1'):
                    emit()

    def run_click(self, *, motion_failure=None, release_failure=None, down_failure=None, deadline=None):
        clock = Clock()
        events = []
        motion_count = 0
        def motion(*delta):
            nonlocal motion_count
            motion_count += 1
            events.append(('move', delta))
            if motion_count == 5 and motion_failure is not None:
                raise motion_failure
        def button(flag):
            events.append(('button', flag))
            if flag == tool.MOUSEEVENTF_LEFTDOWN and down_failure is not None:
                raise down_failure
            if flag == tool.MOUSEEVENTF_LEFTUP and release_failure is not None:
                raise release_failure
        with patch.object(tool, 'time', clock), patch.object(tool, 'send_rel', side_effect=motion), patch.object(tool, 'send_button', side_effect=button):
            try:
                result = tool.click_while_pulsing((12, 7), 40, 1, .01, deadline=deadline)
            except BaseException as error:
                return events, error
        return events, result

    def test_completed_delivery_counts_only_after_down_and_up(self):
        events, result = self.run_click()
        self.assertEqual(result, 1)
        self.assertEqual([value for kind, value in events if kind == 'button'], [tool.MOUSEEVENTF_LEFTDOWN, tool.MOUSEEVENTF_LEFTUP])
        self.assertEqual(events[4], ('button', tool.MOUSEEVENTF_LEFTDOWN))

    def test_failed_motion_and_cancellation_always_attempt_release(self):
        for failure in (OSError('motion failed'), KeyboardInterrupt('cancelled')):
            with self.subTest(failure=type(failure).__name__):
                events, result = self.run_click(motion_failure=failure)
                self.assertIs(result, failure)
                self.assertEqual(events[-1], ('button', tool.MOUSEEVENTF_LEFTUP))

    def test_cleanup_failure_preserves_original_failure_with_diagnostic(self):
        failure = OSError('original pulse failure')
        events, result = self.run_click(motion_failure=failure, release_failure=OSError('release rejected'))
        self.assertIs(result, failure)
        self.assertIn('Button-up cleanup also failed: release rejected', result.__notes__)
        self.assertEqual(events[-1], ('button', tool.MOUSEEVENTF_LEFTUP))

    def test_down_or_up_failure_cannot_count_as_complete(self):
        failure = tool.InputDeliveryError(0, 5)
        events, result = self.run_click(down_failure=failure)
        self.assertIs(result, failure)
        self.assertNotIn(('button', tool.MOUSEEVENTF_LEFTUP), events)
        failure = OSError('release rejected')
        events, result = self.run_click(release_failure=failure)
        self.assertIs(result, failure)
        self.assertEqual(events[-1], ('button', tool.MOUSEEVENTF_LEFTUP))

    def test_interrupted_or_unknown_down_delivery_attempts_release(self):
        for failure in (KeyboardInterrupt('cancelled after insertion'), OSError('delivery unknown')):
            with self.subTest(failure=type(failure).__name__):
                events, result = self.run_click(down_failure=failure)
                self.assertIs(result, failure)
                self.assertEqual([value for kind, value in events if kind == 'button'],
                                 [tool.MOUSEEVENTF_LEFTDOWN, tool.MOUSEEVENTF_LEFTUP])

    def test_cancellation_between_down_return_and_hold_attempts_release(self):
        clock = Clock()
        events = []
        interrupted = False
        def button(flag):
            events.append(flag)
        def trace(frame, event, arg):
            nonlocal interrupted
            if (frame.f_code is tool.click_while_pulsing.__code__ and event == 'line'
                    and events == [tool.MOUSEEVENTF_LEFTDOWN] and not interrupted):
                interrupted = True
                raise KeyboardInterrupt('after down returned')
            return trace
        previous = tool.sys.gettrace()
        with patch.object(tool, 'time', clock), patch.object(tool, 'send_rel'), patch.object(tool, 'send_button', side_effect=button):
            try:
                tool.sys.settrace(trace)
                with self.assertRaisesRegex(KeyboardInterrupt, 'after down returned'):
                    tool.click_while_pulsing((1, 1), 40, 1, .01)
            finally:
                tool.sys.settrace(previous)
        self.assertTrue(interrupted)
        self.assertEqual(events, [tool.MOUSEEVENTF_LEFTDOWN, tool.MOUSEEVENTF_LEFTUP])

    def test_deadline_before_press_delivers_nothing_and_held_deadline_releases(self):
        events, result = self.run_click(deadline=1000.0)
        self.assertIsInstance(result, TimeoutError)
        self.assertEqual(events, [])
        events, result = self.run_click(deadline=1000.055)
        self.assertIsInstance(result, TimeoutError)
        self.assertEqual([value for kind, value in events if kind == 'button'], [tool.MOUSEEVENTF_LEFTDOWN, tool.MOUSEEVENTF_LEFTUP])


class CallerReceiptTests(unittest.TestCase):
    def run_caller(self, mode, failure=None):
        frame = object()
        emitted = []
        def aim(*args, **kwargs):
            return dict(frame=frame, hwnd=1, last_pos=(10, 10), gain=4.0,
                        converged=True, aimed_pos=[10, 10], pulse_delta=[2, 2])
        argv = ['menu-pulse', '--pid', '123', '--resolution', '1024x768',
                '--map-nonblack', '0', '--click-repeats', '1', '--'+mode, 'select:10,10']
        with ExitStack() as scope:
            scope.enter_context(patch.object(tool.sys, 'platform', 'win32'))
            scope.enter_context(patch.object(tool.sys, 'argv', argv))
            for name, value in (('find_window', 1), ('live_hwnd', 1), ('focus', True),
                                ('nonblack_percent', 0.0), ('unique_sample_colors', 1),
                                ('target_accessibility', {'accessible': True}),
                                ('grab_retry', (1, frame)), ('changed_pixels', 50000)):
                scope.enter_context(patch.object(tool, name, return_value=value))
            scope.enter_context(patch.object(tool, 'aim', side_effect=aim))
            scope.enter_context(patch.object(tool.time, 'sleep'))
            scope.enter_context(patch.object(tool, 'emit', side_effect=lambda result, path: emitted.append(deepcopy(result))))
            clicked = scope.enter_context(patch.object(tool, 'click_while_pulsing', side_effect=failure, return_value=1))
            code = tool.main()
        self.assertEqual(len(emitted), 1)
        self.assertIn('deadline', clicked.call_args.kwargs)
        return code, emitted[0]['steps'][0]

    def test_both_callers_emit_failed_delivery_without_a_click_claim(self):
        for mode in ('steps', 'aim-points'):
            failure = OSError('button delivery rejected')
            failure.add_note('release receipt unavailable')
            with self.subTest(mode=mode):
                code, row = self.run_caller(mode, failure)
                self.assertEqual(code, 2)
                self.assertFalse(row['clicked'])
                self.assertFalse(row['transition_verified'])
                self.assertNotIn('click_count', row)
                self.assertIn('button delivery rejected', row['delivery_error'])
                self.assertEqual(row['delivery_notes'], ['release receipt unavailable'])

    def test_both_callers_distinguish_delivery_from_native_consumption(self):
        for mode in ('steps', 'aim-points'):
            with self.subTest(mode=mode):
                code, row = self.run_caller(mode)
                self.assertEqual(code, 0)
                self.assertTrue(row['clicked'])
                self.assertEqual(row['click_count'], 1)
                self.assertIn('native consumption remains unverified', row['delivery_scope'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
