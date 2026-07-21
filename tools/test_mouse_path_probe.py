#!/usr/bin/env python3
"""Repo-only pure helper fixtures for mouse_path_probe transition stopping.

The window-handle fixtures below monkeypatch the Win32 surface (IsWindow /
find_window_for_pid / GetClientRect) instead of touching a real window, so this
stays a repo-only test that never launches Clash95 or a visible process.
"""

from __future__ import annotations

import ctypes

import mouse_path_probe as probe


def win_error(winerror: int, text: str) -> OSError:
    """Portable stand-in for ctypes.WinError so the fixtures also run on POSIX."""
    if hasattr(ctypes, "WinError"):
        return ctypes.WinError(winerror, text)
    error = OSError(text)
    error.winerror = winerror
    return error


def test_click_sample_abs_error() -> None:
    click = {
        "events": [
            {"screen_error": [0, 0], "client_error": [0, 0]},
            {"screen_error": [-193, -151], "client_error": [-298, -263]},
        ]
    }
    assert probe.click_sample_abs_error(click) == 298
    assert probe.should_stop_click_repeat(click, True) is True
    assert probe.should_stop_click_repeat(click, False) is False


def test_missing_errors_default_to_zero() -> None:
    assert probe.sample_abs_error({}) == 0
    assert probe.click_sample_abs_error({"events": []}) == 0
    assert probe.should_stop_click_repeat({"events": []}, True) is False


def test_invalid_window_error_is_recognized() -> None:
    invalid = OSError()
    invalid.winerror = probe.ERROR_INVALID_WINDOW_HANDLE
    assert probe.is_invalid_window_error(invalid) is True

    other = OSError()
    other.winerror = 5
    assert probe.is_invalid_window_error(other) is False
    assert probe.is_invalid_window_error(RuntimeError("nope")) is False


class FakeWin32:
    """Scriptable stand-in for the live-handle checks used by WindowTarget."""

    def __init__(self, alive: set[int], resolves: list[int | None]) -> None:
        self.alive = alive
        self.resolves = list(resolves)
        self.resolve_calls = 0

    def is_window(self, hwnd: int) -> int:
        return 1 if hwnd in self.alive else 0

    def find(self, _pid: int) -> int | None:
        self.resolve_calls += 1
        if not self.resolves:
            return None
        return self.resolves.pop(0)


def install(monkey: FakeWin32) -> None:
    probe.user32.IsWindow = monkey.is_window
    probe.find_window_for_pid = monkey.find


def restore(is_window, find) -> None:
    probe.user32.IsWindow = is_window
    probe.find_window_for_pid = find


def test_ensure_reacquires_recreated_window() -> None:
    saved_is_window = probe.user32.IsWindow
    saved_find = probe.find_window_for_pid
    try:
        # 0x111 died (the wrapper recreated it); 0x222 is the new window.
        fake = FakeWin32(alive={0x222}, resolves=[0x222])
        install(fake)
        target = probe.WindowTarget(1234, reacquire_attempts=4, reacquire_delay=0.0)
        target.hwnd = 0x111
        assert target.ensure("intro-skip") == 0x222
        assert target.reacquire_count == 1
        kinds = [event["kind"] for event in target.events]
        assert "window_handle_invalid" in kinds, target.events
        assert "window_reacquired" in kinds, target.events
    finally:
        restore(saved_is_window, saved_find)


def test_ensure_fails_closed_after_bounded_retries() -> None:
    saved_is_window = probe.user32.IsWindow
    saved_find = probe.find_window_for_pid
    try:
        fake = FakeWin32(alive=set(), resolves=[])
        install(fake)
        target = probe.WindowTarget(1234, reacquire_attempts=3, reacquire_delay=0.0)
        target.hwnd = 0x111
        try:
            target.ensure("intro-skip")
        except probe.WindowLostError:
            pass
        else:  # pragma: no cover - fail-closed contract
            raise AssertionError("ensure must fail closed when the window never returns")
        assert fake.resolve_calls >= 1
        assert any(event["kind"] == "window_lost" for event in target.events), target.events
    finally:
        restore(saved_is_window, saved_find)


def test_geometry_retries_invalid_window_handle_then_succeeds() -> None:
    saved_is_window = probe.user32.IsWindow
    saved_find = probe.find_window_for_pid
    saved_rect = probe.client_rect_and_origin
    try:
        fake = FakeWin32(alive={0x111, 0x222}, resolves=[0x222])
        install(fake)
        calls: list[int] = []

        def flaky(hwnd: int):
            calls.append(hwnd)
            if hwnd == 0x111:
                # The handle passed IsWindow and still died before the read;
                # that race is exactly what must be retried, not raised.
                raise win_error(probe.ERROR_INVALID_WINDOW_HANDLE, "GetClientRect")
            rect = probe.RECT(0, 0, 800, 600)
            return rect, probe.POINT(10, 20)

        probe.client_rect_and_origin = flaky
        target = probe.WindowTarget(1234, reacquire_attempts=4, reacquire_delay=0.0)
        target.hwnd = 0x111
        hwnd, rect, origin = target.geometry("client-size")
        assert hwnd == 0x222
        assert probe.rect_size(rect) == (800, 600)
        assert (origin.x, origin.y) == (10, 20)
        assert calls == [0x111, 0x222], calls
    finally:
        probe.client_rect_and_origin = saved_rect
        restore(saved_is_window, saved_find)


def test_geometry_reraises_unrelated_win32_errors() -> None:
    saved_is_window = probe.user32.IsWindow
    saved_find = probe.find_window_for_pid
    saved_rect = probe.client_rect_and_origin
    try:
        fake = FakeWin32(alive={0x111}, resolves=[])
        install(fake)

        def denied(_hwnd: int):
            raise win_error(5, "GetClientRect")

        probe.client_rect_and_origin = denied
        target = probe.WindowTarget(1234, reacquire_attempts=3, reacquire_delay=0.0)
        target.hwnd = 0x111
        try:
            target.geometry("client-size")
        except OSError as exc:
            assert probe.is_invalid_window_error(exc) is False
        else:  # pragma: no cover - unrelated errors must not be swallowed
            raise AssertionError("non-1400 Win32 errors must propagate")
    finally:
        probe.client_rect_and_origin = saved_rect
        restore(saved_is_window, saved_find)


def test_wait_stable_requires_consecutive_matching_samples() -> None:
    saved_is_window = probe.user32.IsWindow
    saved_find = probe.find_window_for_pid
    saved_rect = probe.client_rect_and_origin
    try:
        fake = FakeWin32(alive={0x222}, resolves=[])
        install(fake)
        # Mid-mode-switch the wrapper reports a desktop-sized client (the
        # 2560x1440 sample from 2026-07-18) before settling at 800x600.
        sizes = [(2560, 1440), (800, 600), (800, 600)]

        def sized(_hwnd: int):
            width, height = sizes.pop(0)
            return probe.RECT(0, 0, width, height), probe.POINT(0, 0)

        probe.client_rect_and_origin = sized
        target = probe.WindowTarget(1234, reacquire_attempts=4, reacquire_delay=0.0)
        target.hwnd = 0x222
        stability = target.wait_stable("pre-input", samples=2, poll_sec=0.0, timeout=5.0)
        assert stability["stable"] is True, stability
        assert stability["samples_taken"] == 3, stability
        assert stability["samples"][0]["client_size"] == [2560, 1440], stability
        assert stability["samples"][-1]["client_size"] == [800, 600], stability
    finally:
        probe.client_rect_and_origin = saved_rect
        restore(saved_is_window, saved_find)


def test_wait_stable_reports_timeout_without_claiming_stability() -> None:
    saved_is_window = probe.user32.IsWindow
    saved_find = probe.find_window_for_pid
    saved_rect = probe.client_rect_and_origin
    try:
        fake = FakeWin32(alive={0x222}, resolves=[])
        install(fake)
        toggle = [0]

        def flapping(_hwnd: int):
            toggle[0] += 1
            width = 800 if toggle[0] % 2 else 2560
            return probe.RECT(0, 0, width, 600), probe.POINT(0, 0)

        probe.client_rect_and_origin = flapping
        target = probe.WindowTarget(1234, reacquire_attempts=4, reacquire_delay=0.0)
        target.hwnd = 0x222
        stability = target.wait_stable("pre-input", samples=2, poll_sec=0.0, timeout=0.0)
        assert stability["stable"] is False, stability
        assert stability["samples_taken"] >= 1, stability
    finally:
        probe.client_rect_and_origin = saved_rect
        restore(saved_is_window, saved_find)


if __name__ == "__main__":
    test_click_sample_abs_error()
    test_missing_errors_default_to_zero()
    test_invalid_window_error_is_recognized()
    test_ensure_reacquires_recreated_window()
    test_ensure_fails_closed_after_bounded_retries()
    test_geometry_retries_invalid_window_handle_then_succeeds()
    test_geometry_reraises_unrelated_win32_errors()
    test_wait_stable_requires_consecutive_matching_samples()
    test_wait_stable_reports_timeout_without_claiming_stability()
    print("mouse_path_probe tests passed")
