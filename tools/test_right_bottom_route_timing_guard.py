#!/usr/bin/env python3
"""Fixture tests for the right-bottom route timing guard."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "right_bottom_route_timing_guard.py"
sys.path.insert(0, str(ROOT / "tools"))

import right_bottom_route_timing_guard  # noqa: E402
import test_right_bottom_grid_hit_summary  # noqa: E402


SHA = "fixture-sha"


def run_script(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def route_log(*, fullstart: bool = False) -> str:
    prefix = ["SURFDUMP_START_ANIMS_SKIP_DISABLED"] if fullstart else ["SURFDUMP_START_ANIMS_SLEEP_FAST_FORWARD_ENABLED"]
    markers = list(right_bottom_route_timing_guard.ROUTE_SEQUENCE)
    extras = ["TOOLTIP_TEXT", "TOOLTIP_TEXTFMT", "BORDER_TOOLTIP_PRESENT_NULLPTR"]
    return "\n".join(prefix + markers[:16] + extras + markers[16:]) + "\n"


def route_summary(*, fullstart: bool = False, **overrides: object) -> dict[str, object]:
    summary: dict[str, object] = {
        "Passed": True,
        "HiddenDesktop": True,
        "AllowVisibleDesktop": False,
        "UseDdrawProxy": True,
        "Stage": right_bottom_route_timing_guard.EXPECTED_STAGE,
        "CandidateSha256": SHA,
        "NoSkipStartAnims": fullstart,
        "FastForwardStartAnims": not fullstart,
        "SkipMapValidation": True,
        "ExtraProbeTemplate": "C:\\repo\\clash95_post_owner_action_extra.cdb",
        "Surface": {"Width": 800, "Height": 600},
    }
    summary.update(overrides)
    return summary


def grid_summary(**overrides: object) -> dict[str, object]:
    summary: dict[str, object] = {
        "Passed": True,
        "HiddenDesktop": True,
        "AllowVisibleDesktop": False,
        "UseDdrawProxy": True,
        "Stage": right_bottom_route_timing_guard.EXPECTED_STAGE,
        "CandidateSha256": SHA,
        "NoSkipStartAnims": False,
        "FastForwardStartAnims": True,
        "SkipMapValidation": True,
        "ExtraProbeTemplate": "C:\\repo\\clash95_right_bottom_grid_hit_extra.cdb",
        "Surface": {"Width": 800, "Height": 600},
    }
    summary.update(overrides)
    return summary


def write_run(run: Path, summary: dict[str, object], log_text: str) -> None:
    run.mkdir(parents=True)
    (run / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    (run / "cdb-surface-dump.log").write_text(log_text, encoding="utf-8")


def write_fixture(
    fixture: Path,
    *,
    patch_log: str | None = None,
    fullstart_log: str | None = None,
    grid_log: str | None = None,
    patch_summary: dict[str, object] | None = None,
    fullstart_summary: dict[str, object] | None = None,
    grid_summary_data: dict[str, object] | None = None,
) -> argparse.Namespace:
    patch_run = fixture / "patch"
    fullstart_run = fixture / "fullstart"
    grid_run = fixture / "grid"
    write_run(patch_run, patch_summary or route_summary(), patch_log or route_log())
    write_run(fullstart_run, fullstart_summary or route_summary(fullstart=True), fullstart_log or route_log(fullstart=True))
    default_grid_log = "SURFDUMP_PLAYGAME\nSURFDUMP_REDRAW\n" + test_right_bottom_grid_hit_summary.good_log_text()
    write_run(grid_run, grid_summary_data or grid_summary(), grid_log or default_grid_log)
    return argparse.Namespace(patch_run=patch_run, fullstart_run=fullstart_run, grid_run=grid_run)


def test_good_fixture(fixture: Path) -> None:
    args = write_fixture(fixture)
    guard = right_bottom_route_timing_guard.build_guard(args)
    assert guard["passed"] is True, guard
    assert guard["candidate_sha256"] == SHA, guard


def test_missing_route_marker_fails(fixture: Path) -> None:
    missing_marker = "APREDIR_COPYBACK_AFTER_CALL"
    args = write_fixture(fixture, patch_log=route_log().replace(missing_marker, "REMOVED_COPYBACK_MARKER"))
    guard = right_bottom_route_timing_guard.build_guard(args)
    assert guard["passed"] is False, guard
    assert any(missing_marker in failure for failure in guard["failures"]), guard


def test_marker_order_regression_fails(fixture: Path) -> None:
    log = route_log().replace(
        "APPOST_OWNER_SETUP_CALL\nAPPOST_OWNER_FLAG_FORCED",
        "APPOST_OWNER_FLAG_FORCED\nAPPOST_OWNER_SETUP_CALL",
    )
    args = write_fixture(fixture, patch_log=log)
    guard = right_bottom_route_timing_guard.build_guard(args)
    assert guard["passed"] is False, guard
    assert any("marker order regression" in failure for failure in guard["failures"]), guard


def test_summary_safety_regressions_fail(fixture: Path) -> None:
    cases = [
        ("visible", route_summary(HiddenDesktop=False, AllowVisibleDesktop=True), "hidden desktop"),
        ("surface", route_summary(Surface={"Width": 640, "Height": 480}), "surface was"),
        ("stage", route_summary(Stage="stale-stage"), "stage is"),
        ("sha", route_summary(CandidateSha256="other-sha"), "candidate SHA values disagree"),
    ]
    for name, summary, expected in cases:
        args = write_fixture(fixture / name, patch_summary=summary)
        guard = right_bottom_route_timing_guard.build_guard(args)
        assert guard["passed"] is False, guard
        assert any(expected in failure for failure in guard["failures"]), guard


def test_grid_regressions_fail(fixture: Path) -> None:
    good_grid_log = "SURFDUMP_PLAYGAME\nSURFDUMP_REDRAW\n" + test_right_bottom_grid_hit_summary.good_log_text()
    cases = [
        ("wrong-entry", good_grid_log.replace("mouse=(450,73)", "mouse=(451,73)"), "grid hit proof"),
        ("failure-exit", good_grid_log + "\nRBGRID_FAIL_EXIT_ARM selected_index=0 hover_slot=-1 mouse=(450,73)\n", "failure exit"),
        ("av", good_grid_log + "\nAccess violation - code c0000005\n", "access violation"),
    ]
    for name, log_text, expected in cases:
        args = write_fixture(fixture / name, grid_log=log_text)
        guard = right_bottom_route_timing_guard.build_guard(args)
        assert guard["passed"] is False, guard
        assert any(expected in failure for failure in guard["failures"]), guard


def test_cli_writes_outputs_and_fails_closed(fixture: Path) -> None:
    good_args = write_fixture(fixture / "good")
    out_json = fixture / "good-output" / "guard.json"
    out_md = fixture / "good-output" / "guard.md"
    good_run = run_script(
        "--patch-run",
        str(good_args.patch_run),
        "--fullstart-run",
        str(good_args.fullstart_run),
        "--grid-run",
        str(good_args.grid_run),
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
        patch_log=route_log().replace("APPOST_ACTION_CALL", "REMOVED_ACTION_CALL"),
    )
    bad_json = fixture / "bad-output" / "guard.json"
    bad_md = fixture / "bad-output" / "guard.md"
    bad_run = run_script(
        "--patch-run",
        str(bad_args.patch_run),
        "--fullstart-run",
        str(bad_args.fullstart_run),
        "--grid-run",
        str(bad_args.grid_run),
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
    fixture = ROOT / ".codex-loop" / "tmp-tests" / "right-bottom-route-timing-guard-fixture"
    shutil.rmtree(fixture, ignore_errors=True)
    fixture.mkdir(parents=True)
    try:
        test_good_fixture(fixture / "good")
        test_missing_route_marker_fails(fixture / "missing-marker")
        test_marker_order_regression_fails(fixture / "order")
        test_summary_safety_regressions_fail(fixture / "summary")
        test_grid_regressions_fail(fixture / "grid")
        test_cli_writes_outputs_and_fails_closed(fixture / "cli")
    finally:
        shutil.rmtree(fixture, ignore_errors=True)


def main() -> int:
    run_tests()
    print("right-bottom route timing guard tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
