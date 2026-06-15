#!/usr/bin/env python3
"""Fixture tests for load_slot_transition_probe_guard.py."""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

import load_slot_transition_probe_guard as guard


PROBE_TEXT = """
.echo fixture
r @$t18=0
r @$t19=0
bp 00447780 ".printf \\"LSTRANS_LOAD_CALLBACK_ENTRY __LOAD_SLOT__\\"; ed 00543d7c 5; ed 00543d78 1; r eip=poi(@esp); r esp=@esp+4; gc"
bp 00419C60 ".printf \\"LSTRANS_AFTER_MAIN_CALLBACK __LOAD_SLOT__\\"; gc"
bp 00447BF1 ".printf \\"LSTRANS_MAIN_WAIT_GATE __LOAD_SLOT__\\"; gc"
bp 00447C0D ".printf \\"LSTRANS_WAIT_LOOP_PUMP __LOAD_SLOT__\\"; gc"
bp 00447C1E ".printf \\"LSTRANS_WAIT_LOOP_COMPARE __LOAD_SLOT__\\"; gc"
bp 00447C26 ".printf \\"LSTRANS_WAIT_LOOP_EXIT __LOAD_SLOT__\\"; gc"
bp 00447C3A ".printf \\"LSTRANS_MAIN_SWITCH_DISPATCH __LOAD_SLOT__\\"; gc"
bp 00447D61 ".printf \\"LSTRANS_MAIN_DISPATCH_POLL\\"; gc"
bp 0044895A ".printf \\"LSTRANS_LOAD_MENU_ENTRY\\"; ed 00544cfc __LOAD_MOUSE_RAW_X__; ed 00544d00 __LOAD_MOUSE_RAW_Y__; .printf \\"LSTRANS_LATE_MOUSE_SET\\"; gc"
bp 0044A140 ".printf \\"LSTRANS_LOAD_SLOT_DRAW\\"; gc"
bp 00448A45 ".printf \\"LSTRANS_LOAD_MENU_LOOP\\"; gc"
bp 00448A68 ".if (poi(00543d7c) == __LOAD_SLOT__) { .printf \\"LSTRANS_LATE_FORCE_SELECT\\"; }; gc"
bp 00448AE3 ".if (poi(00543d7c) == __LOAD_SLOT__) { .printf \\"LSTRANS_LATE_FORCE_ACCEPT\\"; }; gc"
bp 0044A110 ".printf \\"LSTRANS_LOAD_ACCEPT_CALL\\"; gc"
bp 00444490 ".printf \\"LSTRANS_LOADSAVE\\"; gc"
bp 0040B660 ".printf \\"LSTRANS_PLAYGAME\\"; gc"
"""

RUNNER_TEXT = """
param([switch]$LateLoadSlotForcingOnly)
if ($ExtraProbeTemplate) {
    $preEntryLoadCoordAction = if ($LateLoadSlotForcingOnly) {
        'SURFDUMP_PRE_ENTRY_SLOT_DEFERRED __PRE_ENTRY_LOAD_COORD_ACTION__'
    }
    $extraProbeText = (Get-Content -LiteralPath $ExtraProbeTemplate -Raw).Trim()
    $extraProbeText = $extraProbeText.Replace('__LOAD_SLOT__', [string]$LoadSlot)
    $extraProbeText = $extraProbeText.Replace('__LOAD_MOUSE_RAW_X__', ('{0:x8}' -f $loadMouseRawX))
    $extraProbeText = $extraProbeText.Replace('__LOAD_MOUSE_RAW_Y__', ('{0:x8}' -f $loadMouseRawY))
    if ($extraProbeText -match '(?m)^\\s*g\\s*$') {
        throw "Extra CDB probe template must not contain a standalone g command: $ExtraProbeTemplate"
    }
    $probeText = [regex]::Replace($probeText, $playGamePattern, ($extraProbeText + 'bp 0040B660 '), 1)
}
"""


def write_fixture(root: Path, *, probe_text: str = PROBE_TEXT, runner_text: str = RUNNER_TEXT) -> dict[str, Path]:
    probe = root / "transition.cdb"
    runner = root / "scripts/cdb/run_cdb_surface_dump.ps1"
    probe.write_text(probe_text, encoding="utf-8")
    runner.parent.mkdir(parents=True, exist_ok=True)
    runner.write_text(runner_text, encoding="utf-8")
    return {"probe": probe, "runner": runner}


def build(paths: dict[str, Path]) -> dict[str, object]:
    return guard.build_guard(paths["probe"], paths["runner"])


def test_passes_current_transition_probe_shape() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        report = build(write_fixture(Path(tmp)))
    assert report["passed"], report
    assert report["summary"]["late_entry_breakpoint"] == "0044895A"
    assert report["summary"]["early_descriptor_breakpoint_avoided"] is True


def test_fails_if_probe_has_early_descriptor_breakpoint() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        report = build(write_fixture(Path(tmp), probe_text=PROBE_TEXT + "\nbp 00419B80 \".printf \\\"SURFDUMP_LOAD_COORD\\\"; gc\"\n"))
    assert not report["passed"]
    assert any("00419B80" in failure or "SURFDUMP_LOAD_COORD" in failure for failure in report["failures"])


def test_fails_if_probe_has_standalone_go() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        report = build(write_fixture(Path(tmp), probe_text=PROBE_TEXT + "\ng\n"))
    assert not report["passed"]
    assert any("standalone g" in failure for failure in report["failures"])


def test_fails_if_probe_uses_unsupported_temp_register() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        report = build(write_fixture(Path(tmp), probe_text=PROBE_TEXT + "\nr @$t20=0\n"))
    assert not report["passed"]
    assert any("@$t20" in failure for failure in report["failures"])


def test_fails_if_callback_marker_does_not_preserve_skip() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        probe_text = PROBE_TEXT.replace(
            "ed 00543d7c 5; ed 00543d78 1; r eip=poi(@esp); r esp=@esp+4; ",
            "",
        )
        report = build(write_fixture(Path(tmp), probe_text=probe_text))
    assert not report["passed"]
    assert any("skip-main-load-callback" in failure for failure in report["failures"])


def test_fails_if_runner_does_not_replace_extra_placeholders() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        runner = RUNNER_TEXT.replace("$extraProbeText = $extraProbeText.Replace('__LOAD_MOUSE_RAW_Y__'", "# missing")
        report = build(write_fixture(Path(tmp), runner_text=runner))
    assert not report["passed"]
    assert any("__LOAD_MOUSE_RAW_Y__" in failure for failure in report["failures"])


def test_fails_if_late_select_accept_are_hard_coded_to_slot5() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        probe_text = PROBE_TEXT.replace("poi(00543d7c) == __LOAD_SLOT__", "poi(00543d7c) == 5")
        report = build(write_fixture(Path(tmp), probe_text=probe_text))
    assert not report["passed"]
    assert any("__LOAD_SLOT__" in failure and ("00448A68" in failure or "00448AE3" in failure) for failure in report["failures"])


def test_cli_writes_outputs_and_requires_pass() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        paths = write_fixture(root)
        out_json = root / "guard.json"
        out_md = root / "guard.md"
        result = subprocess.run(
            [
                sys.executable,
                str(Path(guard.__file__)),
                "--probe",
                str(paths["probe"]),
                "--surface-dump-script",
                str(paths["runner"]),
                "--write-json",
                str(out_json),
                "--write-markdown",
                str(out_md),
                "--require-pass",
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        assert out_json.exists()
        assert out_md.exists()


def run_tests() -> None:
    test_passes_current_transition_probe_shape()
    test_fails_if_probe_has_early_descriptor_breakpoint()
    test_fails_if_probe_has_standalone_go()
    test_fails_if_probe_uses_unsupported_temp_register()
    test_fails_if_callback_marker_does_not_preserve_skip()
    test_fails_if_runner_does_not_replace_extra_placeholders()
    test_fails_if_late_select_accept_are_hard_coded_to_slot5()
    test_cli_writes_outputs_and_requires_pass()


if __name__ == "__main__":
    run_tests()
    print("load_slot_transition_probe_guard tests passed")
