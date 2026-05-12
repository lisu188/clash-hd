#!/usr/bin/env python3
"""Regression tests for mouse_edge_summary.py."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "mouse_edge_summary.py"
sys.path.insert(0, str(ROOT / "tools"))

import mouse_edge_summary  # noqa: E402


PASS_LOG = """\
0:000> MOUSEEDGE_PLAYGAME gd=0051f000 map=(100,100) scroll=(10,17)
0:000> MOUSEEDGE_INVOKE scroll=(10,17) mouse=(400,300)
0:000> MOUSEEDGE_ENTRY scroll=(10,17) mouse=(400,300)
0:000> MOUSEEDGE_DELTA seq=1 start=(400,300) forced=(480,380) scroll_before=(10,17)
0:000> MOUSEEDGE_STEP seq=1 scroll=(88,91) end12=(100,100) map=(100,100) max_hd=(88,91) max_old=(91,93) mouse=(480,380)
0:000> MOUSEEDGE_REDRAW seq=1 scroll=(88,91) end12=(100,100) map=(100,100) max_hd=(88,91) max_old=(91,93)
0:000> MOUSEEDGE_BOUNDARY_READY steps=1 scroll=(88,91) max_hd=(88,91)
"""


FAIL_LOG = """\
0:000> MOUSEEDGE_PLAYGAME gd=0051f000 map=(100,100) scroll=(10,17)
0:000> MOUSEEDGE_INVOKE scroll=(10,17) mouse=(640,540)
0:000> MOUSEEDGE_ENTRY scroll=(30,37) mouse=(640,540)
0:000> MOUSEEDGE_STEP seq=3 scroll=(40,47) end12=(52,56) map=(100,100) max_hd=(88,91) max_old=(91,93) mouse=(640,540)
AV_MOUSEEDGE
ExceptionAddress: 0040269c (Render_FillRect)
ExceptionCode: c0000005
Attempt to read from address 06af6000
eax=00000000 ebx=11111111 ecx=22222222 edx=33333333 esi=44444444 edi=55555555
"""


def run_summary(log: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(log), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def main() -> int:
    fixture = ROOT / ".codex-loop" / "tmp-tests" / "mouse-edge-summary-fixture"
    shutil.rmtree(fixture, ignore_errors=True)
    fixture.mkdir(parents=True)
    try:
        pass_log = fixture / "pass.log"
        fail_log = fixture / "fail.log"
        pass_json = fixture / "pass-summary.json"
        fail_json = fixture / "fail-summary.json"
        pass_log.write_text(PASS_LOG, encoding="utf-8")
        fail_log.write_text(FAIL_LOG, encoding="utf-8")

        pass_summary = mouse_edge_summary.summarize(pass_log)
        assert pass_summary["boundary_reached"] is True, pass_summary
        assert pass_summary["boundary_ready_rows"] == 1, pass_summary
        assert pass_summary["av_rows"] == 0, pass_summary
        assert pass_summary["overrun_count"] == 0, pass_summary
        final_pass = pass_summary["final_observation"][0]
        assert (final_pass["scrollx"], final_pass["scrolly"]) == (88, 91), final_pass
        assert (final_pass["endx"], final_pass["endy"]) == (100, 100), final_pass

        fail_summary = mouse_edge_summary.summarize(fail_log)
        assert fail_summary["boundary_reached"] is False, fail_summary
        assert fail_summary["av_rows"] == 1, fail_summary
        final_fail = fail_summary["final_observation"][0]
        assert (final_fail["scrollx"], final_fail["scrolly"]) == (40, 47), final_fail
        first_av = fail_summary["first_av"][0]
        assert first_av["exception_address"] == "0040269c", first_av
        assert first_av["access"] == "read", first_av
        assert first_av["access_address"] == "06af6000", first_av
        assert first_av["registers"]["edi"] == "55555555", first_av

        passed = run_summary(
            pass_log,
            "--write-json",
            str(pass_json),
            "--require-hd-boundary",
            "--require-boundary-ready",
            "--expect-final-scroll",
            "88,91",
            "--expect-final-end",
            "100,100",
        )
        assert passed.returncode == 0, passed.stdout + passed.stderr
        written_pass = json.loads(pass_json.read_text(encoding="ascii"))
        assert written_pass["boundary_ready_rows"] == 1, written_pass

        failed = run_summary(
            fail_log,
            "--write-json",
            str(fail_json),
            "--require-hd-boundary",
            "--require-boundary-ready",
            "--expect-final-scroll",
            "88,91",
            "--expect-final-end",
            "100,100",
        )
        assert failed.returncode == 2, failed.stdout + failed.stderr
        assert "HD boundary was not proven cleanly" in failed.stdout, failed.stdout
        assert "MOUSEEDGE_BOUNDARY_READY was not logged" in failed.stdout, failed.stdout
        assert "final scroll did not match" in failed.stdout, failed.stdout
        written_fail = json.loads(fail_json.read_text(encoding="ascii"))
        assert written_fail["first_av"][0]["exception_address"] == "0040269c", written_fail

    finally:
        shutil.rmtree(fixture, ignore_errors=True)

    print("mouse_edge_summary tests: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
