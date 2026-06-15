#!/usr/bin/env python3
"""Tests for load_slot_transition_geometry_guard.py."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import load_slot_transition_geometry_guard as guard


SCRIPT_FORMULA = """
$loadMouseX = 320
$loadMouseY = 166 + (22 * $LoadSlot)
$loadMouseRawX = $loadMouseX -shl 6
$loadMouseRawY = $loadMouseY -shl 6
$extraProbeText = $extraProbeText.Replace('__LOAD_SLOT__', [string]$LoadSlot)
$extraProbeText = $extraProbeText.Replace('__LOAD_MOUSE_RAW_X__', ('{0:x8}' -f $loadMouseRawX))
$extraProbeText = $extraProbeText.Replace('__LOAD_MOUSE_RAW_Y__', ('{0:x8}' -f $loadMouseRawY))
"""

PROBE_TEMPLATE = """
bp 0044895A ".printf \"LSTRANS_LOAD_MENU_ENTRY target_slot=__LOAD_SLOT__\"; ed 00544cfc __LOAD_MOUSE_RAW_X__; ed 00544d00 __LOAD_MOUSE_RAW_Y__; .echo LSTRANS_LATE_MOUSE_SET; gc"
bp 00448A68 ".echo LSTRANS_LATE_FORCE_SELECT; gc"
"""


def write_json(path: Path, payload: dict[str, object]) -> Path:
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def run_plan(*, rows: list[int] | None = None, passed: bool = True) -> dict[str, object]:
    rows = rows or [3, 4, 5]
    return {
        "passed": passed,
        "promotion_ready": False,
        "stable_stage_should_change": False,
        "summary": {
            "target_rows": rows,
            "command_count": len(rows),
            "summary_command_count": len(rows),
        },
        "commands": {
            "hidden_transition_probes": {
                f"slot{slot}_hidden_transition_probe": (
                    "powershell.exe -NoProfile -ExecutionPolicy Bypass "
                    f"-CandidateDir 'C:\\ClashTests\\load-slot-transition\\slot{slot}' "
                    f"-LoadSlot {slot} -ExtraProbeTemplate 'probes/cdb/menu/clash95_load_slot_entry_transition_extra.cdb'"
                )
                for slot in rows
            },
            "summaries": {
                f"slot{slot}_summarize_transition": (
                    "python 'tools\\load_slot_transition_summary.py' "
                    f"'captures\\slot{slot}\\cdb-surface-dump.log' --expected-slot {slot} "
                    "--require-entry --require-slot-match"
                )
                for slot in rows
            },
        },
    }


def write_inputs(root: Path, *, plan_payload: dict[str, object] | None = None, script: str = SCRIPT_FORMULA, probe: str = PROBE_TEMPLATE) -> dict[str, Path]:
    plan_json = write_json(root / "plan.json", plan_payload or run_plan())
    script_path = root / "scripts/cdb/run_cdb_surface_dump.ps1"
    script_path.parent.mkdir(parents=True, exist_ok=True)
    script_path.write_text(script, encoding="utf-8")
    probe_path = root / "transition.cdb"
    probe_path.write_text(probe, encoding="utf-8")
    return {"plan": plan_json, "script": script_path, "probe": probe_path}


def build(paths: dict[str, Path]) -> dict[str, object]:
    return guard.build_guard(
        run_plan_json=paths["plan"],
        surface_dump_script=paths["script"],
        extra_probe=paths["probe"],
    )


def test_passes_and_records_expected_row_geometry() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        report = build(write_inputs(Path(tmp)))
    assert report["passed"], report
    rows = report["summary"]["row_geometry"]
    assert rows[0]["mouse_y"] == 232
    assert rows[1]["mouse_y"] == 254
    assert rows[2]["mouse_y"] == 276
    assert rows[0]["raw_x_hex"] == "00005000"
    assert rows[0]["raw_y_hex"] == "00003a00"
    assert rows[1]["raw_y_hex"] == "00003f80"
    assert rows[2]["raw_y_hex"] == "00004500"


def test_fails_when_formula_drifts() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        bad_script = SCRIPT_FORMULA.replace("166 + (22 * $LoadSlot)", "160 + (22 * $LoadSlot)")
        report = build(write_inputs(Path(tmp), script=bad_script))
    assert not report["passed"]
    assert any("surface_formula_present" in failure for failure in report["failures"]), report


def test_fails_when_placeholder_missing() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        bad_probe = PROBE_TEMPLATE.replace("__LOAD_MOUSE_RAW_Y__", "00000000")
        report = build(write_inputs(Path(tmp), probe=bad_probe))
    assert not report["passed"]
    assert any("__LOAD_MOUSE_RAW_Y__" in failure for failure in report["failures"]), report


def test_fails_when_commands_target_wrong_rows() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        payload = run_plan(rows=[3, 4, 5])
        payload["commands"]["hidden_transition_probes"]["slot5_hidden_transition_probe"] = (
            "powershell.exe -LoadSlot 4 -CandidateDir 'C:\\ClashTests\\load-slot-transition\\slot5'"
        )
        report = build(write_inputs(Path(tmp), plan_payload=payload))
    assert not report["passed"]
    assert any("commands_row_specific" in failure for failure in report["failures"]), report


def test_fails_when_summary_does_not_require_entry() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        payload = run_plan(rows=[3, 4, 5])
        payload["commands"]["summaries"]["slot3_summarize_transition"] = (
            "python parser.py --expected-slot 3 --require-slot-match"
        )
        report = build(write_inputs(Path(tmp), plan_payload=payload))
    assert not report["passed"]
    assert any("summary_commands_require_entry" in failure for failure in report["failures"]), report


def test_cli_writes_outputs_and_requires_pass() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        paths = write_inputs(root)
        out_json = root / "out.json"
        out_md = root / "out.md"
        result = subprocess.run(
            [
                sys.executable,
                str(Path(guard.__file__)),
                "--run-plan-json",
                str(paths["plan"]),
                "--surface-dump-script",
                str(paths["script"]),
                "--extra-probe",
                str(paths["probe"]),
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
        assert json.loads(out_json.read_text(encoding="utf-8"))["passed"] is True
        assert "Load Slot Transition Geometry Guard" in out_md.read_text(encoding="utf-8")


def run_tests() -> None:
    test_passes_and_records_expected_row_geometry()
    test_fails_when_formula_drifts()
    test_fails_when_placeholder_missing()
    test_fails_when_commands_target_wrong_rows()
    test_fails_when_summary_does_not_require_entry()
    test_cli_writes_outputs_and_requires_pass()


if __name__ == "__main__":
    run_tests()
    print("load_slot_transition_geometry_guard tests passed")
