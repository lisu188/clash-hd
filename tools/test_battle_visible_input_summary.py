#!/usr/bin/env python3
"""Fixture tests for visible battle input evidence summary."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "battle_visible_input_summary.py"
sys.path.insert(0, str(ROOT / "tools"))

import battle_visible_input_summary  # noqa: E402


def run_script(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def ready_log() -> str:
    return """
BATTLE_DIRECTINPUT_MOUSE_ACQUIRE eip=0047bd66 result=00000000 hwnd=000d055a device=000f0001
SURFDUMP_LOADSAVE_RETURN selected=0 accept=1 choice=5 gd=033d0030 surface=00f3cc80 size=(640,480)
SURFDUMP_PLAYGAME gd=033d0030 map=(100,100) scroll=(10,17) surface=00f3cc80 size=(640,480)
BATTLE_FORCE_ATTACK_CALL attacker=0 defender=4 attacker_ptr=033f3f16 defender_ptr=033f4a6a attacker_owner=0 defender_owner=1 attacker_xy=(89,9) defender_xy=(90,9)
BATTLE_OWNER_ENTRY source=BattleRunner eip=0042e9e0 ret=0041b14a attacker=033f3f16 defender=033f4a6a result_ptr=00000000 building_ptr=00000000 ebp=033f3f16 surface=0442cc40 width=800 height=600 mouse=(320,166)
BATTLE_COMMAND_INPUT_WINDOW coord_mode=visible-window expected_displayed=(588,440) expected_native=(508,380) mouse=(320,166) raw=(00005000,00002980) click_flag=00000000 button0=0x00 scale=6 list=00514b78
"""


def consumed_log() -> str:
    return (
        ready_log()
        + """
BATTLE_COMMAND_PRE_GATES desc=00514b78 state=0x01 hover_cb=004191f0 click_cb=0042d4e0 type=0x01 mouse=(508,380) click_flag=00000001 button0=0x80
BATTLE_COMMAND_CLICK_GATE_OBSERVED desc=00514b78 eax=1 desc_xy=(498,370) state=0x01 click_cb=0042d4e0 mouse=(508,380) click_flag=00000001 button0=0x80
BATTLE_COMMAND_CALLBACK eip=0042d4e0 ret=00419c63 desc=00514b78 state=0x01 displayed=(508,380)
BATTLE_COMMAND_CALLBACK_RESULT branch=state1 desc=00514b78 state=0x01 surface=0442cc40 size=(800,600)
"""
    )


def write_run(path: Path, log_text: str, *, input_json: dict | None = None, log_name: str = "cdb-visible-input-minimal.log") -> Path:
    path.mkdir(parents=True, exist_ok=True)
    (path / log_name).write_text(log_text.strip() + "\n", encoding="utf-8")
    if input_json is not None:
        (path / "raw-sendinput-click.json").write_text(json.dumps(input_json, indent=2), encoding="ascii")
    return path


def test_ready_run_without_click_is_partial(fixture: Path) -> None:
    run = write_run(fixture / "ready", ready_log())
    summary = battle_visible_input_summary.build_run_summary(run)
    assert summary["command_readiness_proven"] is True, summary
    assert summary["descriptor_target_ok"] is True, summary
    assert summary["real_visible_click_consumed"] is False, summary
    assert "real visible click consumption still open" in summary["classification"], summary


def test_click_consumed_requires_input_and_callback(fixture: Path) -> None:
    input_json = {"dry_run": False, "path_verified": True, "click_path_verified": True, "click_event_count": 3}
    run = write_run(fixture / "consumed", consumed_log(), input_json=input_json)
    summary = battle_visible_input_summary.build_run_summary(run)
    assert summary["command_readiness_proven"] is True, summary
    assert summary["input"]["present"] is True, summary
    assert summary["click_gate_passed"] is True, summary
    assert summary["callback_target_ok"] is True, summary
    assert summary["callback_result_seen"] is True, summary
    assert summary["real_visible_click_consumed"] is True, summary


def test_invalid_cdb_breakpoint_failures_fail_readiness(fixture: Path) -> None:
    run = write_run(
        fixture / "invalid",
        """
Unable to insert breakpoint 26 at 0042e501, Win32 error 0n299
0:000> g
(1fd0.1c44): Break instruction exception - code 80000003 (first chance)
BATTLE_COMMAND_INPUT_WINDOW coord_mode=visible-window expected_displayed=(588,440) expected_native=(508,380) list=00514b78
""",
        log_name="cdb-visible-input-rawsend.log",
    )
    summary = battle_visible_input_summary.build_run_summary(run)
    assert summary["cdb_breakpoint_failure_count"] == 1, summary
    assert summary["cdb_break_instruction_exception_count"] == 1, summary
    assert summary["command_readiness_proven"] is False, summary
    assert "invalid CDB breakpoint failure" in summary["classification"], summary
    assert "invalid CDB break-instruction exception" in summary["classification"], summary


def test_cli_writes_current_artifacts(fixture: Path) -> None:
    ready = write_run(fixture / "ready", ready_log())
    invalid = write_run(
        fixture / "invalid",
        "Unable to remove breakpoint 1 at 0047bd66, Win32 error 0n5\n",
        log_name="cdb-visible-input-rawsend.log",
    )
    out_json = fixture / "summary.json"
    out_md = fixture / "summary.md"
    run = run_script(
        str(ready),
        str(invalid),
        "--write-json",
        str(out_json),
        "--write-markdown",
        str(out_md),
    )
    assert run.returncode == 0, run.stdout + run.stderr
    payload = json.loads(out_json.read_text(encoding="ascii"))
    assert payload["command_ready_run_count"] == 1, payload
    assert payload["click_consumed_run_count"] == 0, payload
    assert payload["invalid_run_count"] == 1, payload
    assert payload["passed"] is False, payload
    assert "Focused completion" in out_md.read_text(encoding="ascii")


def test_aggregate_pass_requires_consumed_click(fixture: Path) -> None:
    ready = write_run(fixture / "ready", ready_log())
    partial = battle_visible_input_summary.build_summary([ready])
    assert partial["command_ready_run_count"] == 1, partial
    assert partial["click_consumed_run_count"] == 0, partial
    assert partial["passed"] is False, partial

    input_json = {"dry_run": False, "path_verified": True, "click_path_verified": True, "click_event_count": 3}
    consumed = write_run(fixture / "consumed", consumed_log(), input_json=input_json)
    complete = battle_visible_input_summary.build_summary([consumed])
    assert complete["command_ready_run_count"] == 1, complete
    assert complete["click_consumed_run_count"] == 1, complete
    assert complete["passed"] is True, complete


def run_tests() -> None:
    fixture = ROOT / ".codex-loop" / "tmp-tests" / "battle-visible-input-summary-fixture"
    shutil.rmtree(fixture, ignore_errors=True)
    fixture.mkdir(parents=True, exist_ok=True)
    try:
        test_ready_run_without_click_is_partial(fixture / "ready-case")
        test_click_consumed_requires_input_and_callback(fixture / "consumed-case")
        test_invalid_cdb_breakpoint_failures_fail_readiness(fixture / "invalid-case")
        test_cli_writes_current_artifacts(fixture / "cli-case")
        test_aggregate_pass_requires_consumed_click(fixture / "aggregate-case")
    finally:
        shutil.rmtree(fixture, ignore_errors=True)


def main() -> int:
    run_tests()
    print("battle visible input summary tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
