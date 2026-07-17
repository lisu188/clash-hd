#!/usr/bin/env python3
"""Repo-only pure helper fixtures for mouse_path_probe transition stopping."""

from __future__ import annotations

import mouse_path_probe as probe


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


if __name__ == "__main__":
    test_click_sample_abs_error()
    test_missing_errors_default_to_zero()
    print("mouse_path_probe tests passed")
