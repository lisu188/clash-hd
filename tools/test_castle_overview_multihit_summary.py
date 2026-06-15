#!/usr/bin/env python3
"""Fixture tests for the castle overview multi-hitbox summary parser."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "castle_overview_multihit_summary.py"
sys.path.insert(0, str(ROOT / "tools"))

import castle_overview_multihit_summary  # noqa: E402


TARGETS = (
    (0, 0xF8, 0x86, 0x0044FE70),
    (1, 0xFE, 0x63, 0x00433C20),
    (2, 0xFF, 0x87, 0x0042B0A0),
)


def run_script(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def write_log(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")
    return path


def good_log_text() -> str:
    lines: list[str] = []
    for index, raw, command, callback in TARGETS:
        lines.extend(
            [
                (
                    "CASTLEOV_MULTI_TARGET_SET "
                    f"index={index} raw=0x{raw:02x} command=0x{command:02x} "
                    f"callback=0x{callback:08x} expected_gate=1"
                ),
                f"CASTLEOV_MULTI_HITTEST_RESULT index={index} raw_hit=0x{raw:02x}",
                (
                    "CASTLEOV_MULTI_DESCRIPTOR_INSTALL "
                    f"index={index} command=0x{command:02x} callback=0x{callback:08x}"
                ),
                (
                    "CASTLEOV_MULTI_CLICK_GATE "
                    f"index={index} command=0x{command:02x} callback=0x{callback:08x} gate=1"
                ),
                (
                    "CASTLEOV_MULTI_TARGET_DONE "
                    f"index={index} command=0x{command:02x} callback=0x{callback:08x} gate=1 raw=0x{raw:02x}"
                ),
            ]
        )
    lines.append("CASTLEOV_MULTI_SURFDUMP_READY size=(800,600)")
    return "\n".join(lines)


def test_good_log_summary(fixture: Path) -> None:
    log = write_log(fixture / "good.log", good_log_text())
    summary = castle_overview_multihit_summary.parse_log(log)
    assert summary["all_targets_ok"] is True, summary
    assert summary["callback_called"] is False, summary
    assert summary["av_count"] == 0, summary
    assert summary["last_ready"]["size"] == [800, 600], summary
    assert len(summary["targets"]) == 3, summary
    assert all(
        target["raw_ok"] and target["descriptor_ok"] and target["gate_ok"] and target["completion_ok"]
        for target in summary["targets"].values()
    ), summary


def test_cli_required_flags_pass_and_write_outputs(fixture: Path) -> None:
    log = write_log(fixture / "good.log", good_log_text())
    out_json = fixture / "summary.json"
    out_md = fixture / "summary.md"
    run = run_script(
        str(log),
        "--require-ready",
        "--require-800x600",
        "--require-all-targets",
        "--forbid-callback",
        "--write-json",
        str(out_json),
        "--write-md",
        str(out_md),
    )
    assert run.returncode == 0, run.stdout + run.stderr
    written = json.loads(out_json.read_text(encoding="utf-8"))
    assert written["all_targets_ok"] is True, written
    assert "- All targets ok: True" in out_md.read_text(encoding="utf-8")


def test_cli_required_flags_fail_closed(fixture: Path) -> None:
    cases = [
        ("missing-ready", good_log_text().replace("CASTLEOV_MULTI_SURFDUMP_READY size=(800,600)", ""), "--require-ready"),
        ("wrong-size", good_log_text().replace("size=(800,600)", "size=(640,480)"), "--require-800x600"),
        ("raw-mismatch", good_log_text().replace("raw_hit=0xf8", "raw_hit=0xfa", 1), "--require-all-targets"),
        ("descriptor-mismatch", good_log_text().replace("callback=0x0044fe70", "callback=0x00420000", 2), "--require-all-targets"),
        ("gate-mismatch", good_log_text().replace("gate=1", "gate=0", 1), "--require-all-targets"),
        ("missing-completion", good_log_text().replace("CASTLEOV_MULTI_TARGET_DONE", "REMOVED_TARGET_DONE", 1), "--require-all-targets"),
        (
            "completion-mismatch",
            good_log_text().replace(
                "CASTLEOV_MULTI_TARGET_DONE index=0 command=0x86 callback=0x0044fe70 gate=1 raw=0xf8",
                "CASTLEOV_MULTI_TARGET_DONE index=0 command=0x86 callback=0x0044fe70 gate=1 raw=0xfa",
            ),
            "--require-all-targets",
        ),
        ("callback-called", good_log_text() + "\nCASTLEOV_MULTI_CALLBACK_CALL index=0", "--forbid-callback"),
    ]
    for name, text, flag in cases:
        log = write_log(fixture / f"{name}.log", text)
        run = run_script(str(log), flag)
        assert run.returncode == 2, f"{name}: {run.stdout}{run.stderr}"

    av_log = write_log(fixture / "av.log", good_log_text() + "\nAccess violation - code c0000005")
    av_run = run_script(str(av_log))
    assert av_run.returncode == 2, av_run.stdout + av_run.stderr


def run_tests() -> None:
    fixture = ROOT / ".codex-loop" / "tmp-tests" / "castle-overview-multihit-summary-fixture"
    shutil.rmtree(fixture, ignore_errors=True)
    fixture.mkdir(parents=True)
    try:
        test_good_log_summary(fixture / "parse")
        test_cli_required_flags_pass_and_write_outputs(fixture / "cli-pass")
        test_cli_required_flags_fail_closed(fixture / "cli-fail")
    finally:
        shutil.rmtree(fixture, ignore_errors=True)


def main() -> int:
    run_tests()
    print("castle overview multihit summary tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
