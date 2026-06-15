#!/usr/bin/env python3
"""Fixture tests for the castle overview visual/catalog gate."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "castle_overview_gate.py"
sys.path.insert(0, str(ROOT / "tools"))

import castle_overview_gate  # noqa: E402


def run_script(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def prepare_run(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    (path / "cdb-surface-dump.log").write_text("fixture\n", encoding="utf-8")
    (path / "surface.png").write_bytes(b"fixture-png")
    return path


def catalog_payload(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "marker_counts": {"CASTLECAT_SURFDUMP_READY": 1, "CASTLECAT_OVERVIEW_POST_DRAW": 1},
        "av_count": 0,
        "commands": list(castle_overview_gate.DEFAULT_COMMANDS),
        "commands_hex": [f"0x{command:02X}" for command in castle_overview_gate.DEFAULT_COMMANDS],
        "descriptors": [],
        "last_surface": {"size": [800, 600]},
        "last_overview_post_draw": {"main_size": [800, 600]},
        "classification": [],
    }
    payload.update(overrides)
    return payload


def geometry_payload(*, passed: bool = True) -> dict[str, Any]:
    return {
        "image": {"width": 800, "height": 600},
        "gate": {
            "passed": passed,
            "centered_nonblack_percent": 95.0 if passed else 30.0,
            "max_margin_nonblack_percent": 0.0 if passed else 20.0,
        },
    }


def visual_payload(*, passed: bool = True) -> dict[str, Any]:
    return {
        "passed": passed,
        "vertical_high_percent": 4.0 if passed else 24.0,
        "horizontal_high_percent": 3.0,
        "vertical_stripe_excess_percent": 1.0 if passed else 21.0,
        "mean_diff_ratio": 1.3 if passed else 3.8,
    }


def action_payload(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "marker_counts": {"APBARRACKS_SURFDUMP_READY": 1},
        "av_count": 0,
        "descriptor_click_ok": True,
        "controlled_4356c0_ok": True,
    }
    payload.update(overrides)
    return payload


def with_fake_parsers(
    *,
    catalog: dict[str, Any] | None = None,
    overview_geometry_passed: bool = True,
    overview_visual_passed: bool = True,
    barracks_action: dict[str, Any] | None = None,
    barracks_geometry_passed: bool = True,
    callback: Callable[[], None],
) -> None:
    original_catalog_parse = castle_overview_gate.castle_interior_catalog_summary.parse_log
    original_action_parse = castle_overview_gate.castle_barracks_action_click_summary.parse_log
    original_analyze = castle_overview_gate.castle_ui_center_geometry.analyze
    original_visual_analyze = castle_overview_gate.analyze_visual_integrity
    analyze_calls = {"count": 0}

    def analyze(_path: Path, *, threshold: int, max_echo_percent: float) -> dict[str, Any]:
        analyze_calls["count"] += 1
        if analyze_calls["count"] == 1:
            return geometry_payload(passed=overview_geometry_passed)
        return geometry_payload(passed=barracks_geometry_passed)

    try:
        castle_overview_gate.castle_interior_catalog_summary.parse_log = (
            lambda _path: catalog if catalog is not None else catalog_payload()
        )
        castle_overview_gate.castle_barracks_action_click_summary.parse_log = (
            lambda _path, **_kwargs: barracks_action if barracks_action is not None else action_payload()
        )
        castle_overview_gate.castle_ui_center_geometry.analyze = analyze
        castle_overview_gate.analyze_visual_integrity = (
            lambda _path: visual_payload(passed=overview_visual_passed)
        )
        callback()
    finally:
        castle_overview_gate.castle_interior_catalog_summary.parse_log = original_catalog_parse
        castle_overview_gate.castle_barracks_action_click_summary.parse_log = original_action_parse
        castle_overview_gate.castle_ui_center_geometry.analyze = original_analyze
        castle_overview_gate.analyze_visual_integrity = original_visual_analyze


def build_gate(fixture: Path) -> dict[str, Any]:
    return castle_overview_gate.build_gate(
        run_dir=prepare_run(fixture / "overview"),
        expected_commands=castle_overview_gate.DEFAULT_COMMANDS,
        threshold=12,
        max_echo_percent=25.0,
        barracks_run=prepare_run(fixture / "barracks"),
    )


def test_gate_passes_with_catalog_geometry_and_barracks(fixture: Path) -> None:
    def assertions() -> None:
        gate = build_gate(fixture)
        assert gate["passed"] is True, gate
        assert gate["catalog"]["ready"] is True, gate
        assert gate["geometry"]["gate"]["passed"] is True, gate
        assert gate["visual_integrity"]["passed"] is True, gate
        assert gate["barracks_baseline"]["passed"] is True, gate

    with_fake_parsers(callback=assertions)


def test_gate_fails_for_overview_regressions(fixture: Path) -> None:
    cases = {
        "no-ready": catalog_payload(marker_counts={"CASTLECAT_OVERVIEW_POST_DRAW": 1}),
        "av": catalog_payload(av_count=1),
        "no-post-draw": catalog_payload(marker_counts={"CASTLECAT_SURFDUMP_READY": 1}),
        "wrong-post-draw-size": catalog_payload(last_overview_post_draw={"main_size": [640, 480]}),
        "wrong-surface-size": catalog_payload(last_surface={"size": [640, 480]}),
        "missing-command": catalog_payload(commands=[0x63], commands_hex=["0x63"]),
    }
    for name, catalog in cases.items():
        def assertions(name: str = name) -> None:
            gate = build_gate(fixture / name)
            assert gate["passed"] is False, gate
            assert gate["failures"], gate

        with_fake_parsers(catalog=catalog, callback=assertions)

    def geometry_assertions() -> None:
        gate = build_gate(fixture / "geometry")
        assert gate["passed"] is False, gate
        assert any("centered 800x600 geometry gate failed" in failure for failure in gate["failures"]), gate

    with_fake_parsers(overview_geometry_passed=False, callback=geometry_assertions)

    def visual_assertions() -> None:
        gate = build_gate(fixture / "visual")
        assert gate["passed"] is False, gate
        assert any("overview visual integrity gate failed" in failure for failure in gate["failures"]), gate

    with_fake_parsers(overview_visual_passed=False, callback=visual_assertions)


def test_gate_fails_for_barracks_regressions(fixture: Path) -> None:
    cases = {
        "no-ready": action_payload(marker_counts={}),
        "av": action_payload(av_count=1),
        "descriptor": action_payload(descriptor_click_ok=False),
        "controlled": action_payload(controlled_4356c0_ok=False),
    }
    for name, action in cases.items():
        def assertions(name: str = name) -> None:
            gate = build_gate(fixture / name)
            assert gate["passed"] is False, gate
            assert any("barracks baseline regression" in failure for failure in gate["failures"]), gate

        with_fake_parsers(barracks_action=action, callback=assertions)

    def geometry_assertions() -> None:
        gate = build_gate(fixture / "barracks-geometry")
        assert gate["passed"] is False, gate
        assert any("barracks baseline regression" in failure for failure in gate["failures"]), gate

    with_fake_parsers(barracks_geometry_passed=False, callback=geometry_assertions)


def test_cli_writes_outputs_and_fails_closed(fixture: Path) -> None:
    missing = fixture / "missing"
    out_json = fixture / "gate.json"
    out_md = fixture / "gate.md"
    run = run_script(
        str(missing / "overview"),
        "--barracks-run",
        str(missing / "barracks"),
        "--write-json",
        str(out_json),
        "--write-markdown",
        str(out_md),
        "--require-pass",
    )
    assert run.returncode == 2, run.stdout + run.stderr
    written = json.loads(out_json.read_text(encoding="utf-8"))
    assert written["passed"] is False, written
    assert "- Overall: FAIL" in out_md.read_text(encoding="utf-8")


def run_tests() -> None:
    fixture = ROOT / ".codex-loop" / "tmp-tests" / "castle-overview-gate-fixture"
    shutil.rmtree(fixture, ignore_errors=True)
    fixture.mkdir(parents=True)
    try:
        test_gate_passes_with_catalog_geometry_and_barracks(fixture / "pass")
        test_gate_fails_for_overview_regressions(fixture / "overview-failures")
        test_gate_fails_for_barracks_regressions(fixture / "barracks-failures")
        test_cli_writes_outputs_and_fails_closed(fixture / "cli")
    finally:
        shutil.rmtree(fixture, ignore_errors=True)


def main() -> int:
    run_tests()
    print("castle overview gate tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
