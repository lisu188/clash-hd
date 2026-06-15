#!/usr/bin/env python3
"""Tests for load_slot_transition_run_plan.py."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import load_slot_transition_run_plan as plan


def write_json(path: Path, payload: dict[str, object]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def entry_gap(*, rows: list[int] | None = None, passed: bool = True) -> dict[str, object]:
    return {
        "passed": passed,
        "promotion_ready": False,
        "gap_classification": "after_main_load_callback_before_load_menu_case_entry",
        "summary": {
            "blocked_rows": rows or [3, 4, 5],
            "slot2_post_entry_success": True,
            "recent_slot5_same_gap": True,
        },
    }


def probe_guard(
    *,
    passed: bool = True,
    early_descriptor_avoided: bool = True,
    slot_conditions_parameterized: bool = True,
    placeholders: bool = True,
) -> dict[str, object]:
    return {
        "passed": passed,
        "summary": {
            "probe": "probes/cdb/menu/clash95_load_slot_entry_transition_extra.cdb",
            "surface_dump_script": "scripts/cdb/run_cdb_surface_dump.ps1",
            "late_entry_breakpoint": "0044895A",
            "early_descriptor_breakpoint_avoided": early_descriptor_avoided,
            "slot_conditions_parameterized": slot_conditions_parameterized,
            "extra_probe_placeholders_replaced": placeholders,
            "late_load_slot_forcing_only_supported": True,
        },
    }


def write_inputs(root: Path, *, gap: dict[str, object] | None = None, guard: dict[str, object] | None = None) -> dict[str, Path]:
    gap_json = write_json(root / "entry-gap.json", gap or entry_gap())
    guard_json = write_json(root / "probe-guard.json", guard or probe_guard())
    surface = root / "scripts/cdb/run_cdb_surface_dump.ps1"
    surface.parent.mkdir(parents=True, exist_ok=True)
    surface.write_text("# surface dump\n", encoding="utf-8")
    extra = root / "transition.cdb"
    extra.write_text(".echo transition\n", encoding="utf-8")
    parser = root / "summary.py"
    parser.write_text("# parser\n", encoding="utf-8")
    return {"gap": gap_json, "guard": guard_json, "surface": surface, "extra": extra, "parser": parser}


def build(paths: dict[str, Path], repo_root: Path) -> dict[str, object]:
    return plan.build_plan(
        entry_gap_json=paths["gap"],
        probe_guard_json=paths["guard"],
        surface_dump_script=paths["surface"],
        extra_probe=paths["extra"],
        result_parser=paths["parser"],
        candidate_root=Path(r"C:\ClashTests\load-slot-transition"),
        repo_root=repo_root,
    )


def test_passes_and_builds_hidden_commands() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        report = build(write_inputs(root), root)
    assert report["passed"], report
    assert report["summary"]["target_rows"] == [3, 4, 5]
    assert report["summary"]["command_count"] == 3
    assert report["promotion_ready"] is False
    for slot in (3, 4, 5):
        command = report["commands"]["hidden_transition_probes"][f"slot{slot}_hidden_transition_probe"]
        assert "-UseDdrawProxy" in command
        assert "-FastForwardStartAnims" in command
        assert "-SkipMapValidation" in command
        assert "-LateLoadSlotForcingOnly" in command
        assert f"-LoadSlot {slot}" in command
        assert "-ExtraProbeTemplate" in command
        assert "-AllowVisibleDesktop" not in command
        assert "-AllowVisibleRuntime" not in command
        summary = report["commands"]["summaries"][f"slot{slot}_summarize_transition"]
        assert f"--expected-slot {slot}" in summary
        assert "--require-entry" in summary
        assert "--require-slot-match" in summary


def test_fails_when_blocked_rows_change() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        report = build(write_inputs(root, gap=entry_gap(rows=[4, 5])), root)
    assert not report["passed"]
    assert any("blocked rows" in failure for failure in report["failures"]), report


def test_fails_when_probe_guard_fails() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        report = build(write_inputs(root, guard=probe_guard(passed=False)), root)
    assert not report["passed"]
    assert any("probe guard is not passing" in failure for failure in report["failures"]), report


def test_fails_when_early_descriptor_forcing_returns() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        report = build(write_inputs(root, guard=probe_guard(early_descriptor_avoided=False)), root)
    assert not report["passed"]
    assert any("early descriptor" in failure for failure in report["failures"]), report


def test_fails_when_placeholder_replacement_missing() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        report = build(write_inputs(root, guard=probe_guard(placeholders=False)), root)
    assert not report["passed"]
    assert any("placeholders" in failure for failure in report["failures"]), report


def test_fails_when_slot_conditions_are_not_parameterized() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        report = build(write_inputs(root, guard=probe_guard(slot_conditions_parameterized=False)), root)
    assert not report["passed"]
    assert any("parameterized" in failure for failure in report["failures"]), report


def test_fails_when_candidate_root_inside_repo() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        paths = write_inputs(root)
        report = plan.build_plan(
            entry_gap_json=paths["gap"],
            probe_guard_json=paths["guard"],
            surface_dump_script=paths["surface"],
            extra_probe=paths["extra"],
            result_parser=paths["parser"],
            candidate_root=root / "candidate",
            repo_root=root,
        )
    assert not report["passed"]
    assert any("inside the repository" in failure for failure in report["failures"]), report


def test_cli_writes_outputs_and_requires_pass() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        paths = write_inputs(root)
        out_json = root / "out.json"
        out_md = root / "out.md"
        result = subprocess.run(
            [
                sys.executable,
                str(Path(plan.__file__)),
                "--entry-gap-json",
                str(paths["gap"]),
                "--probe-guard-json",
                str(paths["guard"]),
                "--surface-dump-script",
                str(paths["surface"]),
                "--extra-probe",
                str(paths["extra"]),
                "--result-parser",
                str(paths["parser"]),
                "--repo-root",
                str(root),
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
        assert "Load Slot Transition Run Plan" in out_md.read_text(encoding="utf-8")


def run_tests() -> None:
    test_passes_and_builds_hidden_commands()
    test_fails_when_blocked_rows_change()
    test_fails_when_probe_guard_fails()
    test_fails_when_early_descriptor_forcing_returns()
    test_fails_when_placeholder_replacement_missing()
    test_fails_when_slot_conditions_are_not_parameterized()
    test_fails_when_candidate_root_inside_repo()
    test_cli_writes_outputs_and_requires_pass()


if __name__ == "__main__":
    run_tests()
    print("load_slot_transition_run_plan tests passed")
