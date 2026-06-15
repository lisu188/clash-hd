#!/usr/bin/env python3
"""Tests for load_slot_transition_probe_preview.py."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import load_slot_transition_probe_preview as preview


PROBE_TEMPLATE = """
bp 0044895A ".printf \\"LSTRANS_LOAD_MENU_ENTRY target_slot=__LOAD_SLOT__\\"; ed 00544cfc __LOAD_MOUSE_RAW_X__; ed 00544d00 __LOAD_MOUSE_RAW_Y__; .printf \\"LSTRANS_LATE_MOUSE_SET target_slot=__LOAD_SLOT__ raw=(__LOAD_MOUSE_RAW_X__,__LOAD_MOUSE_RAW_Y__)\\"; gc"
bp 00448A68 ".if (poi(00543d7c) == __LOAD_SLOT__) { ed 00544cfc __LOAD_MOUSE_RAW_X__; ed 00544d00 __LOAD_MOUSE_RAW_Y__; .printf \\"LSTRANS_LATE_FORCE_SELECT target_slot=__LOAD_SLOT__\\"; }; gc"
bp 00448AE3 ".if (poi(00543d7c) == __LOAD_SLOT__) { .printf \\"LSTRANS_LATE_FORCE_ACCEPT target_slot=__LOAD_SLOT__\\"; }; gc"
bp 00444490 ".printf \\"LSTRANS_LOADSAVE target_slot=__LOAD_SLOT__\\"; gc"
bp 0040B660 ".printf \\"LSTRANS_PLAYGAME target_slot=__LOAD_SLOT__\\"; gc"
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
        "summary": {"target_rows": rows},
    }


def geometry_guard(*, rows: list[int] | None = None, passed: bool = True) -> dict[str, object]:
    rows = rows or [3, 4, 5]
    return {
        "passed": passed,
        "summary": {
            "row_geometry": [
                {
                    "slot": slot,
                    "mouse_x": 320,
                    "mouse_y": 166 + (22 * slot),
                    "raw_x": 320 << 6,
                    "raw_y": (166 + (22 * slot)) << 6,
                    "raw_x_hex": f"{320 << 6:08x}",
                    "raw_y_hex": f"{(166 + (22 * slot)) << 6:08x}",
                }
                for slot in rows
            ]
        },
    }


def write_inputs(
    root: Path,
    *,
    plan_payload: dict[str, object] | None = None,
    geometry_payload: dict[str, object] | None = None,
    probe_text: str = PROBE_TEMPLATE,
) -> dict[str, Path]:
    plan_json = write_json(root / "plan.json", plan_payload or run_plan())
    geometry_json = write_json(root / "geometry.json", geometry_payload or geometry_guard())
    probe = root / "transition.cdb"
    probe.write_text(probe_text, encoding="utf-8")
    return {"plan": plan_json, "geometry": geometry_json, "probe": probe}


def build(paths: dict[str, Path]) -> dict[str, object]:
    return preview.build_report(
        run_plan_json=paths["plan"],
        geometry_guard_json=paths["geometry"],
        extra_probe=paths["probe"],
    )


def test_passes_and_previews_rows_3_4_5() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        report = build(write_inputs(Path(tmp)))
    assert report["passed"], report
    assert report["summary"]["target_rows"] == [3, 4, 5]
    assert report["summary"]["preview_count"] == 3
    assert [item["geometry"]["raw_y_hex"] for item in report["previews"]] == [
        "00003a00",
        "00003f80",
        "00004500",
    ]


def test_fails_when_placeholder_survives() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        bad_probe = PROBE_TEMPLATE.replace("__LOAD_MOUSE_RAW_Y__", "__LOAD_MOUSE_RAW_Y_MISS__")
        report = build(write_inputs(Path(tmp), probe_text=bad_probe))
    assert not report["passed"]
    assert any("placeholders" in failure for failure in report["failures"]), report


def test_fails_when_slot_conditions_are_hard_coded() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        bad_probe = PROBE_TEMPLATE.replace("poi(00543d7c) == __LOAD_SLOT__", "poi(00543d7c) == 5")
        report = build(write_inputs(Path(tmp), probe_text=bad_probe))
    assert not report["passed"]
    assert any("parameterize" in failure for failure in report["failures"]), report


def test_fails_when_geometry_rows_do_not_match_plan() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        report = build(write_inputs(Path(tmp), geometry_payload=geometry_guard(rows=[3, 5])))
    assert not report["passed"]
    assert any("geometry_rows_match_target_rows" in failure for failure in report["failures"]), report


def test_fails_when_run_plan_is_not_passing() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        report = build(write_inputs(Path(tmp), plan_payload=run_plan(passed=False)))
    assert not report["passed"]
    assert any("run_plan_passed" in failure for failure in report["failures"]), report


def test_cli_writes_outputs_and_requires_pass() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        paths = write_inputs(root)
        out_json = root / "out.json"
        out_md = root / "out.md"
        result = subprocess.run(
            [
                sys.executable,
                str(Path(preview.__file__)),
                "--run-plan-json",
                str(paths["plan"]),
                "--geometry-guard-json",
                str(paths["geometry"]),
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
        assert "Load Slot Transition Probe Preview" in out_md.read_text(encoding="utf-8")


def run_tests() -> None:
    test_passes_and_previews_rows_3_4_5()
    test_fails_when_placeholder_survives()
    test_fails_when_slot_conditions_are_hard_coded()
    test_fails_when_geometry_rows_do_not_match_plan()
    test_fails_when_run_plan_is_not_passing()
    test_cli_writes_outputs_and_requires_pass()


if __name__ == "__main__":
    run_tests()
    print("load_slot_transition_probe_preview tests passed")
