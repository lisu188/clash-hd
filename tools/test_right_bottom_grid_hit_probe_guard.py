#!/usr/bin/env python3
"""Fixture tests for the right-bottom controlled grid-hit probe guard."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "right_bottom_grid_hit_probe_guard.py"
sys.path.insert(0, str(ROOT / "tools"))

import right_bottom_grid_hit_probe_guard  # noqa: E402
import test_right_bottom_grid_hit_summary  # noqa: E402


def run_script(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def good_probe_text() -> str:
    markers = "\n".join(right_bottom_grid_hit_probe_guard.REQUIRED_PROBE_MARKERS)
    breakpoints = "\n".join(
        f'bp {address} ".printf \\"{index}\\n\\"; gc"'
        for index, address in enumerate(right_bottom_grid_hit_probe_guard.REQUIRED_BREAKPOINTS)
    )
    return f"{breakpoints}\n{markers}\n"


def mutate_address(address: str) -> str:
    return f"{int(address, 16) + 1:08X}"


def good_summary(**overrides: object) -> dict[str, object]:
    summary: dict[str, object] = {
        "Passed": True,
        "HiddenDesktop": True,
        "AllowVisibleDesktop": False,
        "UseDdrawProxy": True,
        "FastForwardStartAnims": True,
        "SkipMapValidation": True,
        "Stage": right_bottom_grid_hit_probe_guard.EXPECTED_STAGE,
        "ExtraProbeTemplate": "C:\\repo\\clash95_right_bottom_grid_hit_extra.cdb",
        "Surface": {"Width": 800, "Height": 600},
    }
    summary.update(overrides)
    return summary


def write_fixture(
    fixture: Path,
    *,
    probe_text: str | None = None,
    parser_text: str | None = None,
    log_text: str | None = None,
    summary: dict[str, object] | None = None,
) -> argparse.Namespace:
    run = fixture / "captures" / "cdb-surface-dump-20260514-140601"
    run.mkdir(parents=True)
    (run / "cdb-surface-dump.log").write_text(
        (log_text if log_text is not None else test_right_bottom_grid_hit_summary.good_log_text()).strip() + "\n",
        encoding="utf-8",
    )
    (run / "summary.json").write_text(
        json.dumps(summary if summary is not None else good_summary(), indent=2) + "\n",
        encoding="utf-8",
    )
    probe = fixture / "probe.cdb"
    parser = fixture / "summary.py"
    probe.write_text(probe_text if probe_text is not None else good_probe_text(), encoding="utf-8")
    parser.write_text(
        parser_text
        if parser_text is not None
        else "\n".join(right_bottom_grid_hit_probe_guard.REQUIRED_PROBE_MARKERS),
        encoding="utf-8",
    )
    return argparse.Namespace(
        probe_script=probe,
        summary_parser=parser,
        focused_run=run,
    )


def test_good_fixture(fixture: Path) -> None:
    args = write_fixture(fixture)
    guard = right_bottom_grid_hit_probe_guard.build_guard(args)
    assert guard["passed"] is True, guard


def test_missing_breakpoint_fails(fixture: Path) -> None:
    for address in right_bottom_grid_hit_probe_guard.REQUIRED_BREAKPOINTS:
        args = write_fixture(
            fixture / f"missing-{address}",
            probe_text=good_probe_text().replace(f"bp {address}", f"bp {mutate_address(address)}"),
        )
        guard = right_bottom_grid_hit_probe_guard.build_guard(args)
        assert guard["passed"] is False, guard
        assert any(f"missing breakpoint {address}" in failure for failure in guard["failures"]), guard


def test_missing_probe_marker_fails(fixture: Path) -> None:
    for index, marker in enumerate(right_bottom_grid_hit_probe_guard.REQUIRED_PROBE_MARKERS):
        args = write_fixture(
            fixture / f"missing-probe-marker-{marker.lower()}",
            probe_text=good_probe_text().replace(marker, f"REMOVED_PROBE_MARKER_{index}"),
        )
        guard = right_bottom_grid_hit_probe_guard.build_guard(args)
        assert guard["passed"] is False, guard
        assert any(f"missing probe marker {marker}" in failure for failure in guard["failures"]), guard


def test_missing_parser_marker_fails(fixture: Path) -> None:
    parser_text = "\n".join(right_bottom_grid_hit_probe_guard.REQUIRED_PROBE_MARKERS)
    for index, marker in enumerate(right_bottom_grid_hit_probe_guard.REQUIRED_PROBE_MARKERS):
        args = write_fixture(
            fixture / f"missing-parser-marker-{marker.lower()}",
            parser_text=parser_text.replace(marker, f"REMOVED_PARSER_MARKER_{index}"),
        )
        guard = right_bottom_grid_hit_probe_guard.build_guard(args)
        assert guard["passed"] is False, guard
        assert any(f"summary parser does not recognize marker: {marker}" in failure for failure in guard["failures"]), guard


def test_focused_log_regressions_fail(fixture: Path) -> None:
    good_log = test_right_bottom_grid_hit_summary.good_log_text()
    cases = {
        "missing-ready": (
            {"log_text": good_log.replace("RBGRID_SURFDUMP_READY", "REMOVED_READY").replace("SURFDUMP_READY", "REMOVED_SURF")},
            "ready state",
        ),
        "wrong-entry": (
            {"log_text": good_log.replace("mouse=(450,73)", "mouse=(451,73)")},
            "native coordinate",
        ),
        "wrong-result": (
            {"log_text": good_log.replace("RBGRID_GRID_RESULT result=0", "RBGRID_GRID_RESULT result=1")},
            "native coordinate",
        ),
        "failure-exit": (
            {"log_text": good_log + "\nRBGRID_FAIL_EXIT_ARM selected_index=0 hover_slot=-1 mouse=(450,73)\n"},
            "failure exit",
        ),
        "av": (
            {"log_text": good_log + "\nAccess violation - code c0000005\n"},
            "AV rows",
        ),
        "visible-desktop": (
            {"summary": good_summary(HiddenDesktop=False, AllowVisibleDesktop=True)},
            "not hidden-desktop",
        ),
        "wrong-stage": (
            {"summary": good_summary(Stage="stale-stage")},
            "stage was",
        ),
        "wrong-surface": (
            {"summary": good_summary(Surface={"Width": 640, "Height": 480})},
            "surface was",
        ),
        "missing-probe-template": (
            {"summary": good_summary(ExtraProbeTemplate="other.cdb")},
            "extra probe template",
        ),
    }
    for name, (kwargs, expected_failure) in cases.items():
        args = write_fixture(fixture / name, **kwargs)
        guard = right_bottom_grid_hit_probe_guard.build_guard(args)
        assert guard["passed"] is False, guard
        assert any(expected_failure in failure for failure in guard["failures"]), guard


def test_cli_writes_outputs_and_fails_closed(fixture: Path) -> None:
    good_args = write_fixture(fixture / "good")
    out_json = fixture / "good-output" / "guard.json"
    out_md = fixture / "good-output" / "guard.md"
    good_run = run_script(
        "--probe-script",
        str(good_args.probe_script),
        "--summary-parser",
        str(good_args.summary_parser),
        "--focused-run",
        str(good_args.focused_run),
        "--write-json",
        str(out_json),
        "--write-markdown",
        str(out_md),
        "--require-pass",
    )
    assert good_run.returncode == 0, good_run.stdout + good_run.stderr
    assert json.loads(out_json.read_text(encoding="utf-8"))["passed"] is True
    assert "- Overall: PASS" in out_md.read_text(encoding="utf-8")

    bad_args = write_fixture(
        fixture / "bad",
        summary=good_summary(HiddenDesktop=False, AllowVisibleDesktop=True),
    )
    bad_json = fixture / "bad-output" / "guard.json"
    bad_md = fixture / "bad-output" / "guard.md"
    bad_run = run_script(
        "--probe-script",
        str(bad_args.probe_script),
        "--summary-parser",
        str(bad_args.summary_parser),
        "--focused-run",
        str(bad_args.focused_run),
        "--write-json",
        str(bad_json),
        "--write-markdown",
        str(bad_md),
        "--require-pass",
    )
    assert bad_run.returncode == 2, bad_run.stdout + bad_run.stderr
    assert json.loads(bad_json.read_text(encoding="utf-8"))["passed"] is False
    assert "- Overall: FAIL" in bad_md.read_text(encoding="utf-8")


def run_tests() -> None:
    fixture = ROOT / ".codex-loop" / "tmp-tests" / "right-bottom-grid-hit-probe-guard-fixture"
    shutil.rmtree(fixture, ignore_errors=True)
    fixture.mkdir(parents=True)
    try:
        test_good_fixture(fixture / "good")
        test_missing_breakpoint_fails(fixture / "missing-breakpoint")
        test_missing_probe_marker_fails(fixture / "missing-probe-marker")
        test_missing_parser_marker_fails(fixture / "missing-parser-marker")
        test_focused_log_regressions_fail(fixture / "focused-log-regressions")
        test_cli_writes_outputs_and_fails_closed(fixture / "cli")
    finally:
        shutil.rmtree(fixture, ignore_errors=True)


def main() -> int:
    run_tests()
    print("right-bottom grid hit probe guard tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
