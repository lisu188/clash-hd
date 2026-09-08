#!/usr/bin/env python3
"""Fixture tests for hidden_soak_report_assembler.py plus static guards for the
hidden soak probe and runner (nothing is executed; probe/runner are only read)."""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "hidden_soak_report_assembler.py"
PROBE = ROOT / "probes" / "cdb" / "soak" / "clash95_hidden_soak_route_extra.cdb"
RUNNER = ROOT / "scripts" / "cdb" / "run_hidden_soak.ps1"
sys.path.insert(0, str(ROOT / "tools"))

import hidden_soak_report_assembler as assembler  # noqa: E402


SHA = "a" * 64
BASE_SHA = "500055d77d03d514e8d3168506bd10f67cd8569bcc450604ff8192f46cdaf3ae"
START = datetime(2026, 7, 28, 10, 0, 0, tzinfo=timezone.utc)


def iso(offset_sec: int) -> str:
    return (START + timedelta(seconds=offset_sec)).isoformat()


def frame_rows(count: int, interval: int, *, unique_hashes: int = 1) -> list[dict[str, Any]]:
    rows = []
    for index in range(count):
        hash_index = index % max(1, unique_hashes)
        rows.append(
            {
                "Name": f"frame-{index + 1:04d}",
                "Timestamp": iso(index * interval),
                "Width": 800,
                "Height": 600,
                "Hash": f"{hash_index:02x}" * 32,
                "NonblackPercent": 87.5,
                "UniqueSampleColors": 42,
                "CaptureMode": "hidden-cdb-host-readprocessmemory",
                "RenderEvidence": True,
            }
        )
    return rows


def process_rows(count: int, interval: int) -> list[dict[str, Any]]:
    rows = []
    for index in range(count):
        rows.append(
            {
                "Timestamp": iso(index * interval),
                "HasExited": False,
                "ExitCode": None,
                "WorkingSet64": 50_000_000 + index * 1000,
                "PrivateMemorySize64": 40_000_000 + index * 1000,
                "HandleCount": 200 + (index % 3),
            }
        )
    return rows


def make_samples(route: str = "map-idle", **overrides: Any) -> dict[str, Any]:
    duration = 120
    interval = 30
    count = (duration // interval) + 1
    samples: dict[str, Any] = {
        "schema": "hidden_cdb_host_soak_samples_v1",
        "generated_at": iso(0),
        "executed": True,
        "environment": "hidden_cdb_host",
        "route": route,
        "duration_sec": duration,
        "frame_interval_sec": interval,
        "duration_ticks": duration * 64,
        "pan_interval_sec": 10 if route == "map-pan" else None,
        "stage": assembler.PROTECTED_STABLE_STAGE,
        "input_exe": r"C:\Clash\clash95.exe",
        "input_sha256": BASE_SHA,
        "candidate": r"C:\ClashTests\hd-soak\hidden\run\clash95_hd_hidden_soak.exe",
        "candidate_sha256": SHA,
        "patch_stage_report": r"C:\ClashCaptures\hd-soak\hidden\run\patch-stage.json",
        "workdir": r"C:\Clash",
        "output_directory": r"C:\ClashCaptures\hd-soak\hidden\run",
        "load_slot": 2,
        "cdb_log": r"C:\ClashCaptures\hd-soak-hidden\run\hidden-soak-cdb.log",
        "generated_probe": r"C:\ClashCaptures\hd-soak-hidden\run\probe.generated.cdb",
        "launch_mode": "hidden-desktop",
        "frame_read_method": "host_readprocessmemory",
        "surface_base": "0x00b40000",
        "ready_marker": {
            "source": "SOAK_SURFDUMP_READY", "redraw_seq": 4, "surface": "00a00000",
            "base": "00b40000", "width": 800, "height": 600, "bytes": 480000,
        },
        "route_start_marker": {
            "route_ticks": duration * 64, "pan": int(route == "map-pan"), "player": 0,
            "tick": 1000, "game_data": "00c00000", "scroll_x": 4, "scroll_y": 6,
        },
        "route_end_marker": {
            "route_ticks": duration * 64, "pan": int(route == "map-pan"),
            "hits": 8192, "tick_delta": duration * 64, "player": 0, "scroll_x": 4, "scroll_y": 6,
        },
        "pan_events": [
            {"phase": index % 4, "x": 4 + int(index % 4 in (1, 2)),
             "y": 6 + int(index % 4 in (2, 3)), "hits": (index + 1) * 500,
             "tick_delta": (index + 1) * 640}
            for index in range(11)
        ] if route == "map-pan" else [],
        "proxy": {
            "used": True, "path": r"C:\ClashTests\hd-soak\hidden\run\ddraw.dll",
            "sha256": "b" * 64,
            "build_manifest": r"C:\ClashTests\hd-soak\hidden\run\ddraw_surfdump_proxy.build.json",
            "log": r"C:\ClashTests\hd-soak\hidden\run\ddraw_surfdump_proxy.log",
            "present_enabled": False,
        },
        "cleanup": {"game_stopped": True, "cdb_stopped": True, "errors": []},
        "elapsed_coverage": {
            "formula": "duration_sec - sample_interval_sec - 2", "required_sec": duration - interval - 2,
            "frame_elapsed_sec": duration, "process_elapsed_sec": duration, "passed": True,
        },
        "surface": {
            "Base": "00b40000",
            "Width": 800,
            "Height": 600,
            "Bytes": 480000,
            "Source": "SOAK_SURFDUMP_READY",
        },
        "ready_observed": True,
        "soak_route_start_observed": True,
        "soak_route_end_observed": True,
        "heartbeat_count": 4,
        "pan_event_count": 11 if route == "map-pan" else 0,
        "av_observed": False,
        "surface_invalid_observed": False,
        "app_request_quit_observed": False,
        "cdb_exit_before_duration": False,
        "game_exit_before_duration": False,
        "clean_stop": True,
        "clean_stop_mechanism": "harness_stop_after_route_end",
        "exit_code": None,
        "process_exited_unexpectedly": False,
        "input_responsiveness": "not_applicable_hidden",
        "runner_failures": [],
        "capture_errors": [],
        "frame_samples": frame_rows(count, interval, unique_hashes=3 if route == "map-pan" else 1),
        "process_samples": process_rows(count, interval),
        "artifact_bytes": 5_000_000,
        "max_artifact_mb": 250,
        "max_working_set_growth_mb": 64,
        "max_private_memory_growth_mb": 64,
        "max_handle_growth": 128,
        "report_json": r"C:\ClashCaptures\hd-soak-hidden\run\report.json",
        "report_markdown": r"C:\ClashCaptures\hd-soak-hidden\run\RUN-SUMMARY.md",
    }
    samples.update(overrides)
    return samples


def test_passing_map_idle() -> None:
    report = assembler.assemble_report(make_samples("map-idle"))
    assert report["passed"] is True, report["failures"]
    assert report["environment"] == "hidden_cdb_host"
    assert report["evidence_class"] == "approved_hidden_cdb_host_soak"
    assert report["input_responsiveness"] == "not_applicable_hidden"
    assert report["entry_mechanism_detail"]["forced"] is True
    assert report["entry_mechanism"] == "cdb_breakpoint_forced_loader_entry"
    assert report["pan_mechanism"] == "none"
    assert report["frame_stability_class"] == "stable_idle"
    assert report["tier"] == "short2"
    assert report["working_set_growth_bytes"] == 4000
    assert report["clean_stop"] is True


def test_passing_map_pan_discloses_forced_pan() -> None:
    report = assembler.assemble_report(make_samples("map-pan"))
    assert report["passed"] is True, report["failures"]
    assert report["pan_mechanism"] == "cdb_forced_scroll_write"
    assert report["pan_mechanism_detail"]["forced"] is True
    assert report["pan_mechanism_detail"]["pan_event_count"] == 11
    assert report["frame_progress_expected"] is True
    assert report["frame_stability_class"] == "progressing"


def test_map_pan_without_pan_events_fails() -> None:
    report = assembler.assemble_report(make_samples("map-pan", pan_events=[], pan_event_count=0))
    assert report["passed"] is False
    assert any("no SOAK_PAN_SET" in failure for failure in report["failures"])


def test_map_pan_single_hash_fails() -> None:
    samples = make_samples("map-pan")
    samples["frame_samples"] = frame_rows(5, 30, unique_hashes=1)
    report = assembler.assemble_report(samples)
    assert report["passed"] is False
    assert any("frame progression required" in failure for failure in report["failures"])


def test_map_idle_with_pan_events_fails() -> None:
    report = assembler.assemble_report(make_samples("map-idle", pan_events=make_samples("map-pan")["pan_events"], pan_event_count=11))
    assert report["passed"] is False
    assert any("idle route must not pan" in failure for failure in report["failures"])


def test_av_and_missing_markers_fail() -> None:
    report = assembler.assemble_report(make_samples("map-idle", av_observed=True))
    assert report["passed"] is False
    assert any("access violation" in failure for failure in report["failures"])

    report = assembler.assemble_report(make_samples("map-idle", ready_marker=None))
    assert report["passed"] is False
    assert any("ready_marker is missing" in failure for failure in report["failures"])

    report = assembler.assemble_report(make_samples("map-idle", route_end_marker=None))
    assert report["passed"] is False
    assert any("route_end_marker is missing" in failure for failure in report["failures"])


def test_exit_before_duration_fails() -> None:
    report = assembler.assemble_report(
        make_samples(
            "map-idle",
            game_exit_before_duration=True,
            process_exited_unexpectedly=True,
            exit_code=-1,
            clean_stop=False,
            cleanup={"game_stopped": False, "cdb_stopped": True, "errors": []},
        )
    )
    assert report["passed"] is False
    assert any("exited before the soak duration" in failure for failure in report["failures"])
    assert any("did not stop the run cleanly" in failure for failure in report["failures"])


def test_fabricated_input_metric_fails() -> None:
    report = assembler.assemble_report(make_samples("map-idle", input_max_abs_error=0))
    assert report["passed"] is False
    assert any("refusing fields: input_max_abs_error" in failure for failure in report["failures"])

    report = assembler.assemble_report(
        make_samples("map-idle", route_results=[{"Name": "fake", "MaxAbsError": 0}])
    )
    assert report["passed"] is False
    assert any("refusing fields: route_results" in failure for failure in report["failures"])

    report = assembler.assemble_report(make_samples("map-idle", input_responsiveness=0))
    assert report["passed"] is False
    assert any("must record the 'not_applicable_hidden' sentinel" in failure for failure in report["failures"])


def test_sentinel_is_stamped_even_on_failure() -> None:
    report = assembler.assemble_report(make_samples("map-idle", av_observed=True))
    assert report["environment"] == "hidden_cdb_host"
    assert report["input_responsiveness"] == "not_applicable_hidden"
    assert report["entry_mechanism_detail"]["forced"] is True


def test_missing_host_process_metrics_fail() -> None:
    samples = make_samples("map-idle")
    samples["process_samples"] = process_rows(1, 30)
    report = assembler.assemble_report(samples)
    assert report["passed"] is False
    assert any("process sample count 1 is below 2" in failure for failure in report["failures"])
    assert any("REQUIRED" in failure and "working_set_growth_bytes" in failure for failure in report["failures"])


def test_render_thresholds_and_size_fail_closed() -> None:
    samples = make_samples("map-idle")
    for frame in samples["frame_samples"]:
        frame["NonblackPercent"] = 0.5
    report = assembler.assemble_report(samples)
    assert report["passed"] is False
    assert any("minimum nonblack percent" in failure for failure in report["failures"])

    samples = make_samples("map-idle")
    samples["frame_samples"][0]["Width"] = 640
    samples["frame_samples"][0]["Height"] = 480
    report = assembler.assemble_report(samples)
    assert report["passed"] is False
    assert any("were not 800x600" in failure for failure in report["failures"])


def test_wrong_capture_mode_fails() -> None:
    samples = make_samples("map-idle")
    samples["frame_samples"][0]["CaptureMode"] = "screen"
    report = assembler.assemble_report(samples)
    assert report["passed"] is False
    assert any("hidden-cdb-host-readprocessmemory" in failure for failure in report["failures"])


def test_elapsed_coverage_gap_fails() -> None:
    samples = make_samples("map-idle")
    samples["frame_samples"] = frame_rows(2, 5)
    report = assembler.assemble_report(samples)
    assert report["passed"] is False
    assert any("frame sample elapsed coverage" in failure for failure in report["failures"])


def test_missing_or_forged_provenance_fails() -> None:
    for field in ("ready_marker", "route_start_marker", "route_end_marker", "proxy", "cleanup", "elapsed_coverage"):
        samples = make_samples()
        samples.pop(field)
        report = assembler.assemble_report(samples)
        assert not report["passed"], field
        assert any(field in failure for failure in report["failures"]), report["failures"]
    for field, value in (("present_enabled", True), ("sha256", "invalid"), ("used", False)):
        samples = make_samples()
        samples["proxy"][field] = value
        assert not assembler.assemble_report(samples)["passed"], (field, value)
    samples = make_samples()
    samples["route_end_marker"]["tick_delta"] = 10
    assert not assembler.assemble_report(samples)["passed"]
    samples = make_samples()
    samples["elapsed_coverage"]["frame_elapsed_sec"] = 999
    assert not assembler.assemble_report(samples)["passed"]


def test_reports_pass_shared_hidden_grader(fixture: Path) -> None:
    from hd_soak_report import evaluate_report_for_environment

    fixture.mkdir(parents=True, exist_ok=True)
    patch_path = fixture / "patch-stage.json"
    patch_path.write_text(json.dumps({
        "stage": assembler.PROTECTED_STABLE_STAGE, "exe_sha256": SHA,
        "expected_base_sha256": BASE_SHA, "patch_count": 2,
        "status_counts": {"patched": 2}, "current_hd_map_gate": {"passed": True},
    }), encoding="ascii")
    for route in ("map-idle", "map-pan"):
        report = assembler.assemble_report(make_samples(route, patch_stage_report=str(patch_path)))
        guard = evaluate_report_for_environment(report)
        assert guard["overall"], guard["failures"]


def test_runner_structured_marker_parser(fixture: Path) -> None:
    """Run only two source-extracted pure functions, never the runtime script."""
    powershell = Path(r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe")
    if not powershell.exists():
        return  # Windows-only parser coverage; portable assembler checks still run.
    fixture.mkdir(parents=True, exist_ok=True)
    helper = fixture / "parse-only.ps1"
    helper.write_text(r'''
param([string]$Runner, [string]$Log, [string]$Route)
$ErrorActionPreference = 'Stop'
$tokens = $null
$parseErrors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile($Runner, [ref]$tokens, [ref]$parseErrors)
if ($parseErrors.Count) { throw ($parseErrors | Out-String) }
foreach ($functionName in @('Parse-SoakLog', 'Get-RouteValidationFailures')) {
    $definition = $ast.Find({ param($node) $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -eq $functionName }, $true)
    if (-not $definition) { throw "Function not found: $functionName" }
    Invoke-Expression $definition.Extent.Text
}
$observed = Parse-SoakLog -LogText ([System.IO.File]::ReadAllText($Log))
$failures = @(Get-RouteValidationFailures -Observations $observed -ExpectedRoute $Route -ExpectedDurationTicks 7680 -ExpectedPanIntervalTicks 640)
[ordered]@{
    ready = @($observed.ReadyRows).Count; starts = @($observed.RouteStarts).Count; ends = @($observed.RouteEnds).Count
    heartbeat = @($observed.Heartbeats).Count; pan = @($observed.PanEvents).Count
    av = $observed.AvObserved; invalid = $observed.SurfaceInvalidObserved; quit = $observed.AppRequestQuitObserved
    failures = $failures
} | ConvertTo-Json -Depth 5
''', encoding="ascii")
    prose = ".echo SOAK_ROUTE_END and AV_SURFDUMP SURFDUMP_INVALID SURFDUMP_APP_REQUEST_QUIT\n"

    def parse(log: str, route: str = "map-idle") -> dict[str, Any]:
        log_path = fixture / "input.log"
        log_path.write_text(log, encoding="ascii")
        result = subprocess.run(
            [str(powershell), "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(helper), "-Runner", str(RUNNER),
             "-Log", str(log_path), "-Route", route], capture_output=True, text=True, check=False,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        return json.loads(result.stdout)

    observed = parse(prose)
    assert observed["ready"] == observed["starts"] == observed["ends"] == 0, observed
    assert not any(observed[field] for field in ("av", "invalid", "quit")), observed
    assert observed["failures"], observed

    ready = "SOAK_SURFDUMP_READY redraw_seq=4 surface=00a00000 size=(800,600) base=00b40000 bytes=480000\n"
    start = "SOAK_ROUTE_START route_ticks=7680 pan=0 player=0 tick=1000 gd=00c00000 scroll=(4,6)\n"
    heartbeat = "SOAK_HEARTBEAT hits=2048 tickdelta=2000 player=0 scroll=(4,6)\n"
    end = "SOAK_ROUTE_END route_ticks=7680 pan=0 hits=8192 tickdelta=7680 player=0 scroll=(4,6)\n"
    idle = prose + start + ready + heartbeat + end
    observed = parse(idle)
    assert not observed["failures"], observed
    assert observed["ready"] == observed["starts"] == observed["ends"] == observed["heartbeat"] == 1, observed
    assert parse(idle.replace("tickdelta=7680", "tickdelta=10"))["failures"]

    pan_plan = "SOAK_PAN_PLAN base=(4,6) delta=(1,1) max=(20,20) safe=1\n"
    pan_events = "".join(
        f"SOAK_PAN_SET phase={event['phase']} x={event['x']} y={event['y']} hits={event['hits']} "
        f"tickdelta={event['tick_delta']} delta=(1,1)\n"
        for event in make_samples("map-pan")["pan_events"]
    )
    pan = prose + start.replace("pan=0", "pan=1") + ready + pan_plan + heartbeat + pan_events + end.replace("pan=0", "pan=1")
    assert not parse(pan, "map-pan")["failures"]
    assert parse(pan.replace("phase=1 x=5", "phase=1 x=99"), "map-pan")["failures"]
    # A real short30 run logged event 7 at 5121 after scheduling it at 5120,
    # then event 8 at 5760. Keep rejecting that 639-tick observation: fixing
    # the producer's clock sampling must not relax the evidence interval.
    split_clock_pan = pan.replace("tickdelta=5120", "tickdelta=5121")
    observed = parse(split_clock_pan, "map-pan")
    assert any("SOAK_PAN_SET event 8 is not ordered" in failure for failure in observed["failures"]), observed


def test_cli_writes_outputs_and_require_pass_fails_closed(fixture: Path) -> None:
    samples_path = fixture / "samples.json"
    samples_path.parent.mkdir(parents=True, exist_ok=True)
    samples_path.write_text(
        json.dumps(make_samples("map-idle", av_observed=True), indent=2), encoding="ascii"
    )
    out_json = fixture / "report.json"
    out_md = fixture / "RUN-SUMMARY.md"
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            str(samples_path),
            "--write-json",
            str(out_json),
            "--write-markdown",
            str(out_md),
            "--require-pass",
        ],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    assert result.returncode == 1, result.stdout + result.stderr
    report = json.loads(out_json.read_text(encoding="ascii"))
    assert report["passed"] is False
    assert report["environment"] == "hidden_cdb_host"
    md = out_md.read_text(encoding="ascii")
    assert "environment" in md and "hidden_cdb_host" in md
    assert "FORCED entry (disclosed)" in md
    assert "not_applicable_hidden" in md


def test_cli_passing_samples_exit_zero(fixture: Path) -> None:
    samples_path = fixture / "samples.json"
    samples_path.parent.mkdir(parents=True, exist_ok=True)
    samples_path.write_text(json.dumps(make_samples("map-pan"), indent=2), encoding="ascii")
    out_json = fixture / "report.json"
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(samples_path), "--write-json", str(out_json), "--require-pass"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads(out_json.read_text(encoding="ascii"))
    assert report["passed"] is True, report["failures"]


# --- static guards: probe -----------------------------------------------------

def test_probe_placeholder_contract_and_safety() -> None:
    text = PROBE.read_text(encoding="ascii")
    # Placeholder contract: the runner substitutes complete CDB literals.
    for placeholder in ("__SOAK_DURATION_TICKS__", "__SOAK_PAN__", "__PAN_INTERVAL_TICKS__"):
        assert placeholder in text, f"probe is missing placeholder {placeholder}"
    # No standalone g command (the composition guard would reject it).
    assert not re.search(r"(?m)^\s*g\s*$", text), "probe must not contain a standalone g command"
    # Echo text must be semicolon-free.
    for line in text.splitlines():
        if line.startswith(".echo"):
            assert ";" not in line, f"echo line contains a semicolon: {line}"
    # Scratch stays inside the proven DOS-stub window 00400040-0040006c
    # (e_lfanew is 0x70; the PE header starts at 00400070).
    for match in re.finditer(r"\bed (00[0-9a-fA-F]{6})\b", text):
        address = int(match.group(1), 16)
        if 0x00400000 <= address < 0x00500000:
            assert 0x00400040 <= address <= 0x0040006C, f"scratch write outside proven stub window: {match.group(1)}"
    # Only the base-dump latch registers t7/t13 are touched; all 20 $t registers
    # are base-template-owned and $t20 does not exist.
    for match in re.finditer(r"r @\$t(\d+)\s*=", text):
        assert match.group(1) in {"7", "13"}, f"probe writes base-owned register $t{match.group(1)}"
    # No next-player advances anywhere (day-wrap hang avoidance).
    assert "0040AA60" not in text, "probe must not call the next-player routine"
    # The forced-pan writes target the documented scroll fields.
    assert "0n140008" in text and "0n140012" in text
    # Soak marker rows the runner and assembler depend on.
    for marker in ("SOAK_ROUTE_START", "SOAK_SURFDUMP_READY", "SOAK_HEARTBEAT", "SOAK_PAN_SET", "SOAK_ROUTE_END"):
        assert marker in text, f"probe is missing marker {marker}"


def test_runner_static_contract() -> None:
    text = RUNNER.read_text(encoding="ascii")
    # Placeholder substitution for the soak contract.
    for placeholder in ("__SOAK_DURATION_TICKS__", "__SOAK_PAN__", "__PAN_INTERVAL_TICKS__"):
        assert placeholder in text, f"runner never substitutes {placeholder}"
    # Honesty sentinel is hardcoded, never computed.
    assert "input_responsiveness = 'not_applicable_hidden'" in text
    # Hidden desktop only; no visible fallback switch exists.
    assert "CreateDesktop" in text
    assert "AllowVisibleDesktop" not in text
    # Fail-closed markers.
    for marker in ("AV_SURFDUMP", "SOAK_ROUTE_END", "SURFDUMP_INVALID", "SURFDUMP_APP_REQUEST_QUIT"):
        assert marker in text, f"runner does not watch for {marker}"
    # Environment stamp flows into the samples payload.
    assert "hidden_cdb_host" in text
    # Real reads, not fabrication: the ReadProcessMemory path is present.
    assert "ReadProcessMemory" in text


def test_probe_deadlines_and_observations_share_one_clock_sample() -> None:
    """The target clock keeps moving while a breakpoint command is evaluated."""
    lines = PROBE.read_text(encoding="ascii").splitlines()
    start = next(line for line in lines if line.startswith("bp 0040B0C3 "))
    redraw = next(line for line in lines if line.startswith("bp 00406FA1 "))
    assert start.count("poi(7ffe0320)") == 1
    assert "ed 00400054 poi(00400044)" in start
    assert "__SOAK_PAN__, poi(005202ec), poi(00400044)," in start
    assert redraw.count("poi(7ffe0320)") == 1
    assert ".if (poi(0040004c) == 2) { ed 0040004c poi(7ffe0320);" in redraw
    assert "ed 00400054 poi(0040004c)" in redraw
    assert "poi(0040004c)-poi(00400054)" in redraw
    # Heartbeat, route deadline/end, and pan observation all use that latch.
    assert redraw.count("poi(0040004c)-poi(00400044)") == 4


def run_tests() -> None:
    with tempfile.TemporaryDirectory(prefix="clash-hidden-soak-tests-") as temporary:
        fixture = Path(temporary)
        test_passing_map_idle()
        test_passing_map_pan_discloses_forced_pan()
        test_map_pan_without_pan_events_fails()
        test_map_pan_single_hash_fails()
        test_map_idle_with_pan_events_fails()
        test_av_and_missing_markers_fail()
        test_exit_before_duration_fails()
        test_fabricated_input_metric_fails()
        test_sentinel_is_stamped_even_on_failure()
        test_missing_host_process_metrics_fail()
        test_render_thresholds_and_size_fail_closed()
        test_wrong_capture_mode_fails()
        test_elapsed_coverage_gap_fails()
        test_missing_or_forged_provenance_fails()
        test_reports_pass_shared_hidden_grader(fixture / "shared-grader")
        test_runner_structured_marker_parser(fixture / "parser")
        test_cli_writes_outputs_and_require_pass_fails_closed(fixture / "cli-fail")
        test_cli_passing_samples_exit_zero(fixture / "cli-pass")
        test_probe_placeholder_contract_and_safety()
        test_probe_deadlines_and_observations_share_one_clock_sample()
        test_runner_static_contract()


def main() -> int:
    run_tests()
    print("hidden soak report assembler tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
