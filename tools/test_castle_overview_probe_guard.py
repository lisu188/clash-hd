#!/usr/bin/env python3
"""Fixture tests for the castle overview focused probe guard."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "castle_overview_probe_guard.py"
sys.path.insert(0, str(ROOT / "tools"))

import castle_overview_probe_guard  # noqa: E402


GOOD_LOG = """
CASTLEOV_HITBOX_OVERVIEW_POST_DRAW main_surface=0a06fd90 main_size=(800,600) overview_surface=0a06fcd0 overview_size=(640,480) owner_screen=0946c71a mouse=(371,107) click_flag=00000001 button0=0x80
CASTLEOV_HITBOX_DISPLAYED_SET target=command86 displayed=(371,107) expected_native=(291,47) raw=(00005cc0,00001ac0) shift=6
CASTLEOV_HITBOX_DISPLAYED_HITTEST_BEGIN displayed=(371,107) expected_native=(291,47) raw=(00005cc0,00001ac0) click_flag=00000001 button0=0x80
CASTLEOV_HITBOX_DISPLAYED_RESULT raw_hit=248 adjusted_hit=0 mouse=(371,107) raw=(00005cc0,00001ac0) target_raw=248
CASTLEOV_HITBOX_DISPLAYED_WRAPPER_OK raw_hit=248 mouse=(371,107) raw=(00005cc0,00001ac0) target_raw=248
CASTLEOV_HITBOX_DESCRIPTOR_INSTALL command=134 callback=0044fe70 text=00000003 arg_count=5171110 owner_screen=0946c71a surface=0a06fd90 sz=(800,600) mouse=(371,107)
CASTLEOV_HITBOX_CLICK_STATE command=134 callback=0044fe70 mouse=(371,107) click_flag=00000001 button0=0x80
CASTLEOV_HITBOX_CLICK_GATE command=134 callback=0044fe70 gate=1 mouse=(371,107) click_flag=00000001 button0=0x80
CASTLEOV_HITBOX_CLICK_GATE_OK command=134 callback=0044fe70 gate=1 displayed=(371,107) native=(291,47) surface=0a06fd90 size=(800,600) base=0a130030 bytes=480000
CASTLEOV_HITBOX_SURFDUMP_READY reason=click_gate_ok surface=0a06fd90 size=(800,600) base=0a130030 bytes=480000 owner_screen=0946c71a exit_flag=0
SURFDUMP_READY redraw_seq=995 surface=0a06fd90 size=(800,600) base=0a130030 bytes=480000
SURFDUMP_HOST_READY
CASTLEOV_HITBOX_CALLBACK_SUPPRESSED command=134 callback=0044fe70 reason=probe_gate_complete
"""


def run_script(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def good_probe_text() -> str:
    markers = "\n".join(castle_overview_probe_guard.REQUIRED_PROBE_MARKERS)
    return f"""
bp 00422544 ".printf \\"CASTLEOV_HITBOX_DISPLAYED_RESULT raw_hit=%d\\n\\", @eax; gc"
bp 0042257E ".printf \\"CASTLEOV_HITBOX_DESCRIPTOR_INSTALL command=%d callback=%p\\n\\", @esi, @ecx; gc"
bp 00422590 ".printf \\"CASTLEOV_HITBOX_CLICK_GATE command=%d callback=%p gate=%d\\n\\", @esi, @ecx, @eax; gc"
bp 0042262C ".printf \\"CASTLEOV_HITBOX_CALLBACK_CALL callback=%p\\n\\", @ecx; gc"
{markers}
"""


def mutate_address(address: str) -> str:
    return f"{int(address, 16) + 1:08X}"


def write_fixture(
    fixture: Path,
    *,
    probe_text: str | None = None,
    parser_text: str | None = None,
    patcher_text: str | None = None,
    log_text: str = GOOD_LOG,
) -> argparse.Namespace:
    run = fixture / "captures" / "cdb-surface-dump-20260512-160404"
    run.mkdir(parents=True)
    (run / "cdb-surface-dump.log").write_text(log_text, encoding="utf-8")
    probe = fixture / "probe.cdb"
    parser = fixture / "summary.py"
    patcher = fixture / "patcher.py"
    probe.write_text(probe_text if probe_text is not None else good_probe_text(), encoding="utf-8")
    parser.write_text(
        parser_text if parser_text is not None else "\n".join(castle_overview_probe_guard.REQUIRED_PROBE_MARKERS),
        encoding="utf-8",
    )
    patcher.write_text(patcher_text if patcher_text is not None else "# no forbidden markers here\n", encoding="utf-8")
    return argparse.Namespace(
        probe_script=probe,
        summary_parser=parser,
        patcher=patcher,
        focused_run=run,
    )


def test_good_fixture(fixture: Path) -> None:
    args = write_fixture(fixture)
    guard = castle_overview_probe_guard.build_guard(args)
    assert guard["passed"] is True, guard


def test_missing_breakpoint_fails(fixture: Path) -> None:
    for address in castle_overview_probe_guard.REQUIRED_BREAKPOINTS:
        args = write_fixture(
            fixture / f"missing-{address}",
            probe_text=good_probe_text().replace(f"bp {address}", f"bp {mutate_address(address)}"),
        )
        guard = castle_overview_probe_guard.build_guard(args)
        assert guard["passed"] is False, guard
        assert any(f"missing breakpoint {address}" in failure for failure in guard["failures"]), guard


def test_missing_probe_marker_fails(fixture: Path) -> None:
    for index, marker in enumerate(castle_overview_probe_guard.REQUIRED_PROBE_MARKERS):
        args = write_fixture(
            fixture / f"missing-probe-marker-{marker.lower()}",
            probe_text=good_probe_text().replace(marker, f"REMOVED_PROBE_MARKER_{index}"),
        )
        guard = castle_overview_probe_guard.build_guard(args)
        assert guard["passed"] is False, guard
        assert any(f"missing probe marker {marker}" in failure for failure in guard["failures"]), guard


def test_missing_parser_marker_fails(fixture: Path) -> None:
    parser_text = "\n".join(castle_overview_probe_guard.REQUIRED_PROBE_MARKERS)
    for index, marker in enumerate(castle_overview_probe_guard.REQUIRED_PROBE_MARKERS):
        args = write_fixture(
            fixture / f"missing-parser-marker-{marker.lower()}",
            parser_text=parser_text.replace(marker, f"REMOVED_PARSER_MARKER_{index}"),
        )
        guard = castle_overview_probe_guard.build_guard(args)
        assert guard["passed"] is False, guard
        assert any(f"summary parser does not recognize marker: {marker}" in failure for failure in guard["failures"]), guard


def test_forbidden_marker_fails(fixture: Path) -> None:
    for marker in castle_overview_probe_guard.FORBIDDEN_MARKERS:
        for target in ("probe", "parser", "patcher"):
            kwargs = {
                "probe_text": good_probe_text(),
                "parser_text": "\n".join(castle_overview_probe_guard.REQUIRED_PROBE_MARKERS),
                "patcher_text": "# no forbidden markers here\n",
            }
            kwargs[f"{target}_text"] += f"\n{marker}\n"
            args = write_fixture(fixture / f"forbidden-{target}-{marker.lower()}", **kwargs)
            guard = castle_overview_probe_guard.build_guard(args)
            assert guard["passed"] is False, guard
            assert any(marker in failure for failure in guard["failures"]), guard


def test_av_log_fails(fixture: Path) -> None:
    args = write_fixture(fixture, log_text=GOOD_LOG + "\ncode c0000005 access violation\n")
    guard = castle_overview_probe_guard.build_guard(args)
    assert guard["passed"] is False, guard
    assert any("AV rows" in failure for failure in guard["failures"]), guard


def test_focused_log_missing_proof_fails(fixture: Path) -> None:
    cases = {
        "missing-ready": (
            GOOD_LOG.replace("CASTLEOV_HITBOX_SURFDUMP_READY", "REMOVED_HITBOX_READY").replace(
                "SURFDUMP_READY", "REMOVED_READY"
            ),
            "surface-ready marker",
        ),
        "wrong-ready-size": (
            GOOD_LOG.replace("size=(800,600)", "size=(640,480)"),
            "ready surface was",
        ),
        "wrong-main-size": (
            GOOD_LOG.replace("main_size=(800,600)", "main_size=(640,480)"),
            "overview post-draw main surface",
        ),
        "wrong-overview-size": (
            GOOD_LOG.replace("overview_size=(640,480)", "overview_size=(800,600)"),
            "native overview surface",
        ),
        "displayed-miss": (
            GOOD_LOG.replace(
                "CASTLEOV_HITBOX_DISPLAYED_RESULT raw_hit=248",
                "CASTLEOV_HITBOX_DISPLAYED_RESULT raw_hit=0",
            ),
            "displayed-coordinate target hit",
        ),
        "missing-wrapper-ok": (
            GOOD_LOG.replace("CASTLEOV_HITBOX_DISPLAYED_WRAPPER_OK", "REMOVED_DISPLAYED_WRAPPER_OK"),
            "binary wrapper success",
        ),
        "descriptor-mismatch": (
            GOOD_LOG.replace(
                "CASTLEOV_HITBOX_DESCRIPTOR_INSTALL command=134",
                "CASTLEOV_HITBOX_DESCRIPTOR_INSTALL command=135",
            ),
            "descriptor command/callback install",
        ),
        "click-gate-mismatch": (
            GOOD_LOG.replace(
                "CASTLEOV_HITBOX_CLICK_GATE command=134 callback=0044fe70 gate=1",
                "CASTLEOV_HITBOX_CLICK_GATE command=135 callback=0044fe70 gate=0",
            ).replace(
                "CASTLEOV_HITBOX_CLICK_GATE_OK command=134 callback=0044fe70 gate=1",
                "CASTLEOV_HITBOX_CLICK_GATE_OK command=135 callback=0044fe70 gate=0",
            ),
            "stock click gate",
        ),
        "missing-suppression": (
            GOOD_LOG.replace("CASTLEOV_HITBOX_CALLBACK_SUPPRESSED", "REMOVED_CALLBACK_SUPPRESSED"),
            "callback suppression",
        ),
        "callback-entered": (
            GOOD_LOG
            + "\nCASTLEOV_HITBOX_CALLBACK_CALL callback=0044fe70 eax_arg=00000000 command=134 owner_screen=0946c71a mouse=(371,107)\n",
            "callback was entered",
        ),
    }
    for name, (log_text, expected_failure) in cases.items():
        args = write_fixture(fixture / name, log_text=log_text)
        guard = castle_overview_probe_guard.build_guard(args)
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
        "--patcher",
        str(good_args.patcher),
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

    parser_text = "\n".join(castle_overview_probe_guard.REQUIRED_PROBE_MARKERS)
    removed_marker = next(iter(castle_overview_probe_guard.REQUIRED_PROBE_MARKERS))
    bad_args = write_fixture(
        fixture / "bad",
        parser_text=parser_text.replace(removed_marker, "REMOVED_REQUIRED_PARSER_MARKER"),
    )
    bad_json = fixture / "bad-output" / "guard.json"
    bad_md = fixture / "bad-output" / "guard.md"
    bad_run = run_script(
        "--probe-script",
        str(bad_args.probe_script),
        "--summary-parser",
        str(bad_args.summary_parser),
        "--patcher",
        str(bad_args.patcher),
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
    fixture = ROOT / ".codex-loop" / "tmp-tests" / "castle-overview-probe-guard-fixture"
    shutil.rmtree(fixture, ignore_errors=True)
    fixture.mkdir(parents=True)
    try:
        test_good_fixture(fixture / "good")
        test_missing_breakpoint_fails(fixture / "missing-breakpoint")
        test_missing_probe_marker_fails(fixture / "missing-probe-marker")
        test_missing_parser_marker_fails(fixture / "missing-parser-marker")
        test_forbidden_marker_fails(fixture / "forbidden-marker")
        test_av_log_fails(fixture / "av-log")
        test_focused_log_missing_proof_fails(fixture / "focused-log-missing-proof")
        test_cli_writes_outputs_and_fails_closed(fixture / "cli")
    finally:
        shutil.rmtree(fixture, ignore_errors=True)


def main() -> int:
    run_tests()
    print("castle overview probe guard tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
