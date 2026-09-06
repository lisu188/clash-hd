#!/usr/bin/env python3
"""Offline boundary fixtures. Every process, window, screen and runtime call is fake."""
from __future__ import annotations

import argparse
import contextlib
import copy
from datetime import datetime, timedelta, timezone
import io
import json
from pathlib import Path
import struct
import sys
import tempfile
from types import SimpleNamespace
from unittest import mock

import hd_layout_observation_manifest as harness
import hd_layout_command_input_summary as summary
import test_hd_layout_command_input_summary as fixtures


def fake_pe() -> bytes:
    result = bytearray(256)
    result[:2] = b"MZ"
    struct.pack_into("<I", result, 60, 128)
    result[128:134] = b"PE\0\0L\x01"
    return bytes(result)


@contextlib.contextmanager
def planned(root: Path):
    candidate_root, captures = root / "candidates", root / "captures"
    work = candidate_root / "isolated"
    work.mkdir(parents=True); captures.mkdir()
    candidate, wrapper, config, debugger = (work / "clash95_layout.exe", work / "ddraw.dll", work / "wrapper.ini", root / "cdb.exe")
    candidate.write_bytes(b"synthetic candidate; never executable")
    wrapper.write_bytes(fake_pe()); debugger.write_bytes(fake_pe()); config.write_text("fixture config", encoding="utf-8")
    for relative in harness.REQUIRED_ASSET_DIRECTORIES:
        (work / relative).mkdir(parents=True, exist_ok=True)
    for relative in harness.REQUIRED_ASSET_FILES:
        (work / relative).write_bytes(b"synthetic test asset; not game material")
    args = argparse.Namespace(candidate=candidate, stage=summary.SUPPORTED_STAGES[-1], wrapper=wrapper,
        wrapper_config=config, wrapper_mode="proxy-present", cdb=debugger, output_dir=captures / "run",
        run_id="synthetic-offline-run", timeout_seconds=30)
    with mock.patch.object(harness, "CANDIDATE_ROOT", candidate_root), mock.patch.object(harness, "OUTPUT_ROOT", captures), \
            mock.patch.object(harness, "validate_candidate") as gate:
        plan = harness.build_plan(args)
        plan_path = root / "plan.json"; plan_path.write_bytes(harness.plan_bytes(plan))
        now = datetime.now(timezone.utc)
        approval_path = root / "synthetic-user-approval.json"
        identity = {**plan["identity"], "execution_plan_sha256": harness.file_ref(plan_path)["sha256"]}
        approval = {"record_kind": "user_approval", "approved": True,
            "approval_text": "SYNTHETIC OFFLINE TEST ONLY. Not actual user approval.",
            "approved_at": (now - timedelta(minutes=1)).isoformat(), "expires_at": (now + timedelta(minutes=10)).isoformat(),
            "identity": identity}
        harness.write_json(approval_path, approval)
        yield args, plan, plan_path, approval_path, gate


def rejects(function, text: str = "") -> None:
    try:
        function()
    except (ValueError, OSError) as exc:
        assert text.lower() in str(exc).lower(), str(exc)
    else:
        raise AssertionError("unsafe or invalid request was accepted")


def test_candidate_reconstruction_and_pe_checks() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        path = root / "fixture.exe"
        patch = SimpleNamespace(offset=2, old=b"CD", new=b"xy")
        patcher = SimpleNamespace(select_patches=lambda stage: [patch], EXPECTED_SHA256=summary.sha256(b"ABCDEF"))
        path.write_bytes(b"ABxyEF")
        with mock.patch("patch_stage_report.load_patcher", return_value=patcher):
            harness.validate_candidate(path, summary.SUPPORTED_STAGES[-1])
            path.write_bytes(b"ZBxyEF")
            rejects(lambda: harness.validate_candidate(path, summary.SUPPORTED_STAGES[-1]), "original SHA")
            path.write_bytes(b"ABCDEF")
            rejects(lambda: harness.validate_candidate(path, summary.SUPPORTED_STAGES[-1]), "byte mismatch")
        path.write_bytes(fake_pe()); harness.require_x86_pe(path)
        path.write_bytes(fake_pe().replace(b"L\x01", b"d\x86"))
        rejects(lambda: harness.require_x86_pe(path), "x86")


def test_dry_run_is_file_only_and_emits_exact_approval_command() -> None:
    with tempfile.TemporaryDirectory() as directory, planned(Path(directory)) as (args, plan, plan_path, approval, gate):
        with mock.patch.object(harness, "WindowsSession", side_effect=AssertionError("Win32 used in dry run")), \
                mock.patch.object(harness.subprocess, "Popen", side_effect=AssertionError("process launched in dry run")), \
                mock.patch.object(sys, "argv", ["offline", "--plan", str(plan_path), "--approval-path", str(approval)]), \
                contextlib.redirect_stdout(io.StringIO()) as output:
            assert harness.main() == 0
        packet = json.loads(output.getvalue())
        assert packet["executed"] is False and not args.output_dir.exists()
        assert packet["plan"] == plan and packet["plan_saved"] is True
        assert packet["execution_plan_sha256"] == harness.file_ref(plan_path)["sha256"]
        assert "hwnd" not in packet["approval_identity"]
        assert packet["execution_command"] == [sys.executable, "-B", str(Path(harness.__file__).resolve()),
            "--plan", str(plan_path), "--approval", str(approval), "--execute", "--allow-visible-runtime"]
        assert packet["plan"]["inject_input"] is False
        gate.assert_called()
        for key, value in (("candidate", Path(r"C:\Clash\clash95.exe")), ("output_dir", args.candidate.parent),
                           ("stage", summary.STABLE_STAGE), ("wrapper_mode", "hidden"), ("timeout_seconds", 901),
                           ("wrapper", args.wrapper_config)):
            bad = copy.copy(args); setattr(bad, key, value)
            rejects(lambda: harness.build_plan(bad))


def test_execution_fails_before_runtime_without_exact_fresh_approval() -> None:
    for mutation in ("no_flag", "no_approval", "template", "wrong_sha", "wrong_plan", "predicted_hwnd", "expired", "stale", "too_short", "changed_wrapper", "changed_source", "changed_asset", "missing_asset", "missing_cache_dir", "existing_output"):
        with tempfile.TemporaryDirectory() as directory, planned(Path(directory)) as (args, plan, path, approval_path, _):
            record = summary.read_object(approval_path)
            if mutation == "no_approval":
                approval_path.unlink()
            elif mutation == "template":
                record["approved"] = False
            elif mutation in ("wrong_sha", "wrong_plan"):
                record["identity"]["candidate_sha256" if mutation == "wrong_sha" else "execution_plan_sha256"] = "a" * 64
            elif mutation == "predicted_hwnd":
                record["identity"]["hwnd"] = "0x12345"
            elif mutation in ("expired", "stale", "too_short"):
                now = datetime.now(timezone.utc)
                if mutation == "expired": record["expires_at"] = (now - timedelta(seconds=1)).isoformat()
                if mutation == "stale": record["approved_at"] = (now - timedelta(days=1)).isoformat()
                if mutation == "too_short": record["expires_at"] = (now + timedelta(seconds=20)).isoformat()
            elif mutation == "changed_wrapper":
                args.wrapper.write_bytes(fake_pe() + b"unexpected bytes")
            elif mutation == "changed_source":
                plan["producer_source"]["sha256"] = "0" * 64; harness.write_json(path, plan)
            elif mutation == "changed_asset":
                (args.candidate.parent / "save/0.dat").write_bytes(b"different synthetic map state")
            elif mutation == "missing_asset":
                (args.candidate.parent / "DATA/MAPS.RES").unlink()
            elif mutation == "missing_cache_dir":
                (args.candidate.parent / "GFX/CACHE").rmdir()
            elif mutation == "existing_output":
                args.output_dir.mkdir()
            if mutation != "no_approval": harness.write_json(approval_path, record)
            factory = mock.Mock(side_effect=AssertionError("runtime API crossed invalid approval boundary"))
            with mock.patch.object(harness.subprocess, "Popen", side_effect=AssertionError("runtime launched")):
                rejects(lambda: harness.execute(path, approval_path, allow_visible_runtime=mutation != "no_flag", session_factory=factory))
            factory.assert_not_called()
            assert args.output_dir.exists() is (mutation == "existing_output")


def test_plan_requires_local_route_assets_without_unrelated_artifacts() -> None:
    with tempfile.TemporaryDirectory() as directory, planned(Path(directory)) as (args, plan, _, _, _):
        inventory = plan["assets"]
        assert set(inventory["directories"]) == set(harness.REQUIRED_ASSET_DIRECTORIES)
        files = {item["relative_path"].lower(): item for item in inventory["files"]}
        assert {"save/0.dat", "save/0.fac", "save/2.dat", "save/2.fac"} <= files.keys()
        assert files["save/0.dat"]["sha256"] == summary.sha256(b"synthetic test asset; not game material")
        unrelated = args.candidate.parent / "old-unrelated-debugger-note.log"
        unrelated.write_text("unrelated synthetic file", encoding="utf-8")
        assert harness.asset_inventory(args.candidate.parent) == inventory
        required = args.candidate.parent / "save/0.fac"
        required.unlink()
        rejects(lambda: harness.build_plan(args), "required asset")


def test_child_environment_is_local_case_insensitive_and_plan_bound() -> None:
    inherited = {"SystemRoot": r"C:\Windows", "__compat_layer": "DPIUNAWARE RUNASADMIN",
                 "ClAsH_PrOxY_PRESENT": "0", "clash_proxy_diagnostic": "unsafe inherited switch",
                 "SYNTHETIC_SECRET": "fixture-private-value"}
    for mode in ("proxy-present", "gog"):
        environment, receipt = harness.prepare_launch_environment(mode, inherited)
        assert environment["__COMPAT_LAYER"] == "HIGHDPIAWARE"
        assert "__compat_layer" not in environment and "clash_proxy_diagnostic" not in environment
        assert environment.get("CLASH_PROXY_PRESENT") == ("1" if mode == "proxy-present" else None)
        assert receipt["policy"] == summary.launch_environment_policy(mode)
        assert "fixture-private-value" not in json.dumps(receipt)
        assert len(receipt["effective_environment_sha256"]) == 64
        other = harness.prepare_launch_environment(mode, {**inherited, "HOST_ONLY": "different execution shell"})[1]
        assert other["policy"] == receipt["policy"]
        assert other["effective_environment_sha256"] != receipt["effective_environment_sha256"]
    assert inherited["__compat_layer"] == "DPIUNAWARE RUNASADMIN"
    with tempfile.TemporaryDirectory() as directory, planned(Path(directory)) as (_, plan, _, _, _):
        with mock.patch.dict(harness.os.environ, {"HOST_ONLY": "different shell", "__COMPAT_LAYER": "DPIUNAWARE"}):
            harness.verify_plan(plan)
        altered = copy.deepcopy(plan)
        altered["launch_environment"]["set"]["__COMPAT_LAYER"] = "DPIUNAWARE"
        rejects(lambda: harness.verify_plan(altered), "plan differs")


def test_native_dpi_queries_reject_unaware_and_api_failure() -> None:
    import ctypes
    state = {"process": 2, "window": 2, "hr": 0}
    session = object.__new__(harness.WindowsSession)
    session.ctypes = ctypes
    def get_awareness(handle, value):
        assert handle == "owned-handle"
        value._obj.value = state["process"]
        return state["hr"]
    session.shcore = SimpleNamespace(GetProcessDpiAwareness=get_awareness)
    session.user = SimpleNamespace(GetWindowDpiAwarenessContext=lambda hwnd: "measured-context",
                                  GetAwarenessFromDpiAwarenessContext=lambda context: state["window"])
    for awareness in (1, 2):
        state.update(process=awareness, window=awareness)
        assert session.process_dpi_awareness({"handle": "owned-handle"}) == awareness
        assert session.window_dpi_awareness(0x1234) == awareness
    for awareness in (-1, 0, 3):
        state.update(process=awareness, window=awareness)
        rejects(lambda: session.process_dpi_awareness({"handle": "owned-handle"}), "not DPI-aware")
        rejects(lambda: session.window_dpi_awareness(0x1234), "not DPI-aware")
    state.update(process=2, hr=-2147024891)
    rejects(lambda: session.process_dpi_awareness({"handle": "owned-handle"}), "not DPI-aware")


def test_observer_requires_actual_per_monitor_coordinates() -> None:
    import ctypes
    for setter_result, measured in ((True, 2), (False, 2), (True, 1), (False, 1), (True, 0), (False, -1)):
        session = object.__new__(harness.WindowsSession)
        session.ctypes = ctypes
        setter = mock.Mock(return_value=setter_result)
        session.user = SimpleNamespace(SetProcessDpiAwarenessContext=setter,
            GetThreadDpiAwarenessContext=lambda: "measured-context",
            GetAwarenessFromDpiAwarenessContext=lambda context: measured)
        if measured == 2:
            session.enable_native_capture_coordinates()
        else:
            rejects(session.enable_native_capture_coordinates, "per-monitor")
        assert setter.call_args.args[0].value == ctypes.c_void_p(-4).value


def test_incomplete_and_unrecognized_state_readiness() -> None:
    rows = summary.parse_events(fixtures.EVENTS)[0]
    assert not harness.state_ready(rows, "panel_hover")
    rows[0]["values"]["state"] = 6
    assert harness.state_ready(rows, "panel_hover")
    assert not harness.state_ready(rows, "arbitrary")
    assert not harness.state_ready([], "map")
    bad = copy.deepcopy(rows); bad[0]["values"]["selected_unit"] = -1
    assert not harness.state_ready(bad, "panel_hover")
    for state3 in (0, 3, 4, 5, 6, 7):
        bad = copy.deepcopy(rows); bad[0]["values"]["state3"] = state3
        assert not harness.state_ready(bad, "panel_hover")
    for key, value in (("cursor_meta", 0x5196C8), ("cursor_sprite", 3), ("cursor_x", 639), ("cursor_y", 543)):
        bad = copy.deepcopy(rows); bad[0]["values"][key] = value
        assert not harness.state_ready(bad, "panel_hover")
    rows[0]["values"].update(mouse_x=320, mouse_y=300, state=2,
                             cursor_meta=0x5196C8, cursor_sprite=3, cursor_x=320, cursor_y=300)
    assert harness.state_ready(rows, "map")
    for native_state in (0, 1, 3, 4, 5, 6, 7):
        bad = copy.deepcopy(rows); bad[0]["values"]["state"] = native_state
        assert not harness.state_ready(bad, "map")
    for key, value in (("cursor_meta", 0x5196A0), ("cursor_sprite", 2), ("cursor_x", 319), ("cursor_y", 299)):
        bad = copy.deepcopy(rows); bad[0]["values"][key] = value
        assert not harness.state_ready(bad, "map")
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "partial.log"
        path.write_text(fixtures.EVENTS.splitlines()[0] + "\nHDLAYOUT_INPUT_GATE_OBSERVED tid=", encoding="utf-8")
        snapshot = harness.read_snapshot(path)
        assert len(snapshot["rows"]) == 1
        ref = harness.descriptor_reference(snapshot)
        raw = path.read_bytes()
        assert ref["line"] == 1 and raw[ref["prefix_bytes"]-1:ref["prefix_bytes"]] == b"\n"
        assert ref["prefix_sha256"] == summary.sha256(raw[:ref["prefix_bytes"]])


def test_fake_owned_session_runs_to_receipt_and_stops_only_owned_handles(failure: str = "") -> None:
    """Exercise the orchestrator with fake processes/Win32/captures; never launch."""
    from PIL import Image
    with tempfile.TemporaryDirectory() as directory, planned(Path(directory)) as (args, plan, path, approval, _):
        state = {"phase": "map", "clock": 0.0, "terminated": False, "closed": [], "captures": []}
        log = args.output_dir / "observation.log"
        def append_observation():
            if failure == "stale_capture" and state["captures"]:
                return
            if state["phase"] == "click":
                text = fixtures.EVENTS.replace("state=2", "state=6")
                if failure == "click_selection": text = text.replace("selected_unit=2", "selected_unit=3")
            else:
                text = fixtures.EVENTS.splitlines()[0] + "\n"
                if state["phase"] == "map":
                    text = text.replace("mouse_x=640 mouse_y=544", "mouse_x=320 mouse_y=300")
                    text = text.replace("cursor_meta=005196a0 cursor_sprite=2 cursor_x=640 cursor_y=544",
                                        "cursor_meta=005196c8 cursor_sprite=3 cursor_x=320 cursor_y=300")
                else:
                    text = text.replace("state=2", "state=6")
                    if failure == "phase_selection": text = text.replace("selected_unit=2", "selected_unit=3")
                    if failure == "phase_state3": text = text.replace("state3=1", "state3=2")
            with log.open("a", encoding="utf-8") as stream:
                if failure == "transient_state" and state["captures"]:
                    stream.write(text.replace("state=2", "state=6"))
                if failure == "transient_cursor" and state["captures"]:
                    stream.write(text.replace("cursor_x=320", "cursor_x=321"))
                stream.write(text)
        class FakeProcess:
            pid = 122
            def poll(self): return 0 if state["terminated"] else None
            def terminate(self): state["terminated"] = True
            def wait(self, timeout): return 0
            def kill(self): raise AssertionError("unexpected debugger kill")
        class FakeSession:
            kernel = SimpleNamespace(CloseHandle=lambda handle: state["closed"].append(handle))
            def candidate_child(self, parent, candidate, earliest):
                assert parent == 122 and candidate == args.candidate
                return {"pid": 123, "parent_pid": 122, "path": str(candidate), "creation_filetime": earliest + 100, "handle": "owned-kernel-handle"}
            def window(self, proc_id):
                assert proc_id == 123
                return None if failure == "missing_window" else 0x123456
            def process_dpi_awareness(self, owned):
                assert owned["handle"] == "owned-kernel-handle"
                if failure == "unaware_process": raise ValueError("owned candidate is not DPI-aware")
                return 2
            def window_dpi_awareness(self, hwnd):
                assert hwnd == 0x123456
                if failure == "unaware_window": raise ValueError("owned candidate window is not DPI-aware")
                return 2
            def capture(self, hwnd, proc_id, identity, target):
                assert (hwnd, proc_id) == (0x123456, 123)
                if failure == "capture": raise ValueError("synthetic capture failure")
                state["captures"].append(target)
                Image.new("RGB", (800, 600), (30, 70, 20)).save(target)
                sidecar = target.with_suffix(".json")
                harness.write_json(sidecar, {"fixture_only": True})
                return {**harness.file_ref(target), "sidecar": harness.file_ref(sidecar)}
            def stop_candidate(self, owned):
                assert owned["handle"] == "owned-kernel-handle"
                state["candidate_stopped"] = True
                return failure != "cleanup"
        real_pair = harness.stable_pair
        def pair(*values):
            result = real_pair(*values)
            state["phase"] = "panel_hover" if state["phase"] == "map" else "click"
            return result
        def launch(command, **kwargs):
            assert command[-1] == str(args.candidate) and kwargs["env"]["CLASH_PROXY_PRESENT"] == "1"
            assert kwargs["env"]["__COMPAT_LAYER"] == "HIGHDPIAWARE"
            identity = {**plan["identity"], "execution_plan_sha256": harness.file_ref(path)["sha256"]}
            log.write_text(summary.render_probe(identity).splitlines()[0].removeprefix(".echo ") + "\n", encoding="utf-8")
            append_observation()
            return FakeProcess()
        def sleep(seconds):
            state["clock"] += seconds
            append_observation()
        with mock.patch.object(harness.subprocess, "Popen", side_effect=launch) as launched, \
                mock.patch.object(harness, "stable_pair", side_effect=pair), \
                mock.patch.object(harness.time, "sleep", side_effect=sleep), \
                mock.patch.object(harness.time, "monotonic", side_effect=lambda: state["clock"]), \
                contextlib.redirect_stdout(io.StringIO()):
            result = harness.execute(path, approval, allow_visible_runtime=True, session_factory=FakeSession)
        assert result["passed"] is (not failure), result
        assert launched.call_count == 1 and state["candidate_stopped"] and state["terminated"]
        assert state["closed"] == ["owned-kernel-handle"]
        expected_captures = {"capture": 0, "missing_window": 0, "stale_capture": 1, "transient_state": 1,
                             "transient_cursor": 1, "phase_selection": 2, "phase_state3": 2,
                             "unaware_process": 0, "unaware_window": 0}.get(failure, 4)
        assert len(state["captures"]) == expected_captures
        receipt = summary.read_object(args.output_dir / "session-receipt.json")
        assert receipt["hwnd_pid"] == (None if failure == "missing_window" else 123)
        assert receipt["candidate_pid"] == 123 and receipt["candidate_parent_pid"] == receipt["cdb_pid"] == 122
        assert receipt["cleanup"] == {"candidate_stopped": failure != "cleanup", "cdb_stopped": True}
        report = summary.build_report(args.output_dir / "command-input-manifest.json")
        assert report["passed"] is (not failure)
        assert not report["manual_directinput_proof"] and not report["promotion_ready"]
        if not failure:
            assert receipt["candidate_dpi_awareness"] == receipt["window_dpi_awareness"] == 2
            assert receipt["physical_client_size"] == [800, 600]
            assert receipt["launch_environment"]["policy"] == plan["launch_environment"]
            assert len(receipt["launch_environment"]["effective_environment_sha256"]) == 64
            composition = summary.read_object(args.output_dir / "composition.json")
            raw = log.read_bytes()
            parsed = {row["line"]: row for row in summary.parse_events(raw.decode("utf-8"))[0]}
            previous_line = 0
            for phase in ("map", "panel_hover"):
                for frame in composition["frames"][phase]:
                    metadata = summary.read_object(Path(frame["sidecar"]["path"]))
                    for field in ("InputObservationBefore", "InputObservationAfter"):
                        ref = metadata[field]
                        assert ref["prefix_sha256"] == summary.sha256(raw[:ref["prefix_bytes"]])
                        assert ref["line"] > previous_line
                        observed = parsed[ref["line"]]
                        assert observed["marker"] == "DESCRIPTOR"
                        assert observed["values"]["state"] == (2 if phase == "map" else 6)
                        assert (observed["values"]["selected_unit"], observed["values"]["state3"]) == (2, 1)
                        previous_line = ref["line"]
            assert receipt["click_observation_start_line"] >= previous_line
            assert report["matched_sequence"][0]["line"] > receipt["click_observation_start_line"]


def test_capture_api_records_measured_metadata_and_rejects_wrong_window() -> None:
    import ctypes
    from ctypes import wintypes as w
    from PIL import Image
    from PIL import ImageGrab
    state = {"pid": 123, "center": 0x1234}
    def get_pid(hwnd, value): value._obj.value = state["pid"]; return 1
    def get_rect(hwnd, value): value._obj.right = 800; value._obj.bottom = 600; return 1
    def origin(hwnd, value): value._obj.x = 100; value._obj.y = 200; return 1
    session = object.__new__(harness.WindowsSession)
    session.ctypes, session.w = ctypes, w
    session.user = SimpleNamespace(GetWindowThreadProcessId=get_pid, IsWindowVisible=lambda hwnd: True,
        GetClientRect=get_rect, ClientToScreen=origin, WindowFromPoint=lambda point: state["center"], GetAncestor=lambda hwnd, mode: hwnd,
        GetWindowDpiAwarenessContext=lambda hwnd: "context", GetAwarenessFromDpiAwarenessContext=lambda context: 2)
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "frame.png"
        identity = {"run_id": "fixture-run", "candidate_sha256": "a" * 64, "stage": summary.SUPPORTED_STAGES[-1]}
        with mock.patch.object(ImageGrab, "grab", return_value=Image.new("RGB", (800, 600), (30, 70, 20))) as grab:
            ref = session.capture(0x1234, 123, identity, path)
            grab.assert_called_once_with(bbox=(100, 200, 900, 800), all_screens=True)
            metadata = summary.read_object(Path(ref["sidecar"]["path"]))
            assert metadata["Hash"] == harness.file_ref(path)["sha256"]
            assert metadata["RunId"] == "fixture-run" and metadata["CandidateSha256"] == "a" * 64
            assert metadata["TargetHwnd"] == metadata["CenterWindowHwnd"] == "0x1234"
            assert metadata["CaptureId"] and summary.timestamp(metadata["CapturedAt"])
            assert metadata["ClientSize"] == [800, 600]
            assert metadata["WindowDpiAwareness"] == 2
            state["pid"] = 999
            rejects(lambda: session.capture(0x1234, 123, identity, path), "client changed")
            state["pid"] = 123; state["center"] = 0x5678
            rejects(lambda: session.capture(0x1234, 123, identity, path), "occluded")
            assert grab.call_count == 1


def run_tests() -> None:
    test_candidate_reconstruction_and_pe_checks()
    test_dry_run_is_file_only_and_emits_exact_approval_command()
    test_execution_fails_before_runtime_without_exact_fresh_approval()
    test_plan_requires_local_route_assets_without_unrelated_artifacts()
    test_child_environment_is_local_case_insensitive_and_plan_bound()
    test_native_dpi_queries_reject_unaware_and_api_failure()
    test_observer_requires_actual_per_monitor_coordinates()
    test_incomplete_and_unrecognized_state_readiness()
    for failure in ("", "capture", "cleanup", "missing_window", "stale_capture", "transient_state", "transient_cursor",
                    "phase_selection", "phase_state3", "click_selection", "unaware_process", "unaware_window"):
        test_fake_owned_session_runs_to_receipt_and_stops_only_owned_handles(failure)
    test_capture_api_records_measured_metadata_and_rejects_wrong_window()


if __name__ == "__main__":
    run_tests()
    print("hd_layout_observation_manifest tests: PASS (offline fakes only)")
