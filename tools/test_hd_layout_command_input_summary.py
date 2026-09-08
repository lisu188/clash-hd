#!/usr/bin/env python3
"""Synthetic offline fixtures; no approval records or runtime evidence are created in the repository."""
from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import hd_layout_command_input_summary as summary

EVENTS = """HDLAYOUT_INPUT_DESCRIPTOR tid=1a2 desc=00511d40 x=608 y=528 state=2 state3=1 callback=00409d80 mouse_x=640 mouse_y=544 selected_unit=2 width=800 height=600 cursor_meta=005196a0 cursor_sprite=2 cursor_x=640 cursor_y=544
HDLAYOUT_INPUT_HIT_X tid=1a2 desc=00511d40 cursor=640 lower=608 upper_exclusive=671
HDLAYOUT_INPUT_HIT_Y tid=1a2 desc=00511d40 cursor=544 lower=528 upper_exclusive=559
HDLAYOUT_INPUT_GATE_BEFORE tid=1a2 desc=00511d40 callback=00409d80 mouse_x=640 mouse_y=544 click_flag=1 button0=80
HDLAYOUT_INPUT_GATE_OBSERVED tid=1a2 desc=00511d40 eax=1 callback=00409d80 mouse_x=640 mouse_y=544
HDLAYOUT_INPUT_DISPATCH tid=1a2 desc=00511d40 argument=00511d40 eip=00419c5d callback=00409d80 mouse_x=640 mouse_y=544
HDLAYOUT_INPUT_CALLBACK tid=1a2 desc=00511d40 eip=00409d80 ret=00419c60 mouse_x=640 mouse_y=544 selected_unit=2
"""


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def file_ref(path: Path) -> dict:
    return {"path": str(path), "sha256": summary.sha256(path.read_bytes())}


def write_fixture(root: Path, *, stage: str = summary.SUPPORTED_STAGES[0], candidate_bytes: bytes | None = None,
                  resource_bytes: bytes | None = None, descriptor_prefix: str = "") -> Path:
    """Return a complete, explicitly synthetic manifest for offline consumer tests."""
    root.mkdir(parents=True, exist_ok=True)
    candidate = root / "synthetic-candidate.exe"
    candidate.write_bytes(candidate_bytes if candidate_bytes is not None else b"synthetic fixture candidate; never executable")
    wrapper, config = root / "ddraw.dll", root / "wrapper.ini"
    wrapper.write_bytes(b"synthetic fixture wrapper; never executable")
    config.write_text("synthetic fixture wrapper configuration", encoding="utf-8")
    identity = {
        "run_id": "synthetic-fixture-run", "candidate_path": str(candidate.resolve()),
        "candidate_sha256": summary.sha256(candidate.read_bytes()), "stage": stage,
        "resolution": [800, 600], "environment": "host_visible", "input_method": "manual_directinput",
        "wrapper": {**file_ref(wrapper), "config": file_ref(config), "mode": "proxy-present"},
        "input_plan": summary.INPUT_PLAN,
        "hwnd": "0x00123456", "started_at": "2026-09-05T10:01:00+00:00", "finished_at": "2026-09-05T10:02:00+00:00",
    }
    plan_path = root / "execution-plan.json"
    debugger = root / "synthetic-cdb.exe"
    debugger.write_bytes(b"synthetic fixture debugger; never executable")
    plan = {"identity": {key: identity[key] for key in summary.APPROVAL_BINDINGS if key != "execution_plan_sha256"},
        "cdb": file_ref(debugger), "producer_source": file_ref(summary.SESSION_PRODUCER),
        "wrapper_script": file_ref(summary.REPO_ROOT / "scripts/smoke/run_hd_layout_input_probe.ps1"),
        "observation_template": file_ref(summary.PROBE), "summary_source": file_ref(Path(summary.__file__)),
        "launch_environment": summary.launch_environment_policy("proxy-present")}
    if resource_bytes is not None:
        resource = root / "DATA/minimum.res"
        resource.parent.mkdir(parents=True)
        resource.write_bytes(resource_bytes)
        plan["assets"] = {"work_dir": str(root.resolve()), "directories": ["DATA"],
            "files": [{**file_ref(resource), "relative_path": "DATA/minimum.res", "size_bytes": len(resource_bytes)}],
            "scope": "synthetic offline resource fixture only"}
    write_json(plan_path, plan)
    identity["execution_plan_sha256"] = file_ref(plan_path)["sha256"]
    rendered = root / "observation.cdb"
    rendered.write_text(summary.render_probe(identity), encoding="utf-8")
    startup = root / "startup.cdb"
    startup.write_text(summary.render_probe(identity) + "\ng\n", encoding="utf-8")
    log = root / "observation.log"
    header = summary.render_probe(identity).splitlines()[0].removeprefix(".echo ")
    if descriptor_prefix and not descriptor_prefix.endswith("\n"):
        descriptor_prefix += "\n"
    log.write_text(header + "\n" + descriptor_prefix + EVENTS, encoding="utf-8")
    approval = root / "synthetic-approval.json"
    write_json(approval, {
        "approved": True, "record_kind": "user_approval",
        "approval_text": "SYNTHETIC TEST FIXTURE ONLY; not actual user approval.",
        "approved_at": "2026-09-05T10:00:00+00:00", "expires_at": "2026-09-05T10:03:00+00:00",
        "identity": {key: identity[key] for key in summary.APPROVAL_BINDINGS},
    })
    receipt_path = root / "session-receipt.json"
    write_json(receipt_path, {"schema_version": 1, "executed": True,
        "producer_source": file_ref(summary.SESSION_PRODUCER), "plan": file_ref(plan_path),
        "identity": identity, "approval": file_ref(approval), "candidate_pid": 123, "cdb_pid": 122,
        "candidate_parent_pid": 122, "hwnd_pid": 123,
        "candidate_creation_filetime": int((summary.timestamp(identity["started_at"]).timestamp() + 11644473601) * 10000000),
        "process_image_path": identity["candidate_path"], "process_image_sha256": identity["candidate_sha256"],
        "launch_environment": {"policy": plan["launch_environment"],
            "effective_environment_sha256": summary.sha256(b"synthetic fixture environment; no real process")},
        "candidate_dpi_awareness": 2, "window_dpi_awareness": 2, "physical_client_size": [800, 600],
        "startup_probe": file_ref(startup),
        "click_observation_start_line": 1 + len(descriptor_prefix.splitlines()),
        "launch_command": [str(debugger), "-hd", "-logo", str(log), "-cf", str(startup), identity["candidate_path"]],
        "cleanup": {"candidate_stopped": True, "cdb_stopped": True}, "failures": []})
    manifest = {
        "schema_version": 1, "executed": True, "identity": identity,
        "raw_log": file_ref(log), "approval": file_ref(approval), "session_receipt": file_ref(receipt_path),
        "probe": {"template_path": str(summary.PROBE), "template_sha256": summary.sha256(summary.PROBE.read_bytes()),
                  "rendered_path": str(rendered), "rendered_sha256": summary.sha256(rendered.read_bytes())},
    }
    path = root / "synthetic-manifest.json"
    write_json(path, manifest)
    return path


def replace_log(path: Path, transform) -> None:
    manifest = summary.read_object(path)
    log = Path(manifest["raw_log"]["path"])
    log.write_text(transform(log.read_text(encoding="utf-8")), encoding="utf-8")
    manifest["raw_log"] = file_ref(log)
    write_json(path, manifest)


def test_observed_sequence_preserves_scope() -> None:
    for stage in summary.SUPPORTED_STAGES:
        with tempfile.TemporaryDirectory() as temporary:
            manifest = write_fixture(Path(temporary), stage=stage)
            report = summary.build_report(manifest)
        assert report["passed"], report["failures"]
        assert report["status"] == "observed"
        assert report["command_click_alignment"] and report["panel_click_callback_proof"]
        assert report["manual_directinput_proof"] is False and report["promotion_ready"] is False
        assert report["approval"]["passed"] is True
        assert len(report["matched_sequence"]) == 7
        assert report["matched_sequence"][-1]["values"]["ret"] == 0x419C60


def test_missing_and_incomplete_are_distinct() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        assert summary.build_report(root / "missing.json")["status"] == "missing_evidence"
        manifest = write_fixture(root)
        replace_log(manifest, lambda text: "\n".join(text.splitlines()[:-1]) + "\n")
        report = summary.build_report(manifest)
        assert report["status"] == "incomplete_evidence", report
        assert not report["panel_click_callback_proof"]


def test_native_selected_sprite_state_contract() -> None:
    for state in (0, 1, 2, 3, 4, 5, 6, 7, 10):
        with tempfile.TemporaryDirectory() as temporary:
            manifest = write_fixture(Path(temporary))
            replace_log(manifest, lambda text: text.replace("state=2", f"state={state:x}"))
            report = summary.build_report(manifest)
        assert report["passed"] is (state in (2, 6)), (state, report)
    # This is a read-only byte check when the user-owned original is present.
    # Fresh clones without proprietary material still run all synthetic cases.
    original = Path(r"C:\Clash\clash95.exe")
    if not original.is_file():
        print("native state byte check: unavailable (user-owned original absent)")
        return
    data = original.read_bytes()
    assert summary.sha256(data) == "500055d77d03d514e8d3168506bd10f67cd8569bcc450604ff8192f46cdaf3ae"
    def at(address: int, expected: str):
        expected_bytes = bytes.fromhex(expected)
        assert data[address-0x400C00:address-0x400C00+len(expected_bytes)] == expected_bytes, hex(address)
    # Compare selected==-1, branch to selected path; ECX=1 vs EDI=2 writes
    # at descriptor+8. Exact call [EBX+20] precedes both visual-state tests.
    at(0x40A362, "83 3d 58 1b 51 00 ff 75 61")
    at(0x40A36D, "b9 01 00 00 00")
    at(0x40A37E, "89 0d 48 1d 51 00")
    at(0x40A3CC, "bf 02 00 00 00")
    at(0x40A3DB, "89 3d 48 1d 51 00")
    at(0x419C5D, "ff 53 20 f6 43 08 01 74 05 be 03 00 00 00 f6 43 08 02")


def test_click_boundary_rejects_an_earlier_success_and_invalid_state3() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        manifest = write_fixture(Path(temporary), descriptor_prefix=EVENTS)
        replace_log(manifest, lambda text: "\n".join(text.splitlines()[:-1]) + "\n")
        report = summary.build_report(manifest)
        assert report["passed"] is False and report["status"] == "incomplete_evidence", report
    for state3 in (0, 3, 4, 5, 6, 7):
        with tempfile.TemporaryDirectory() as temporary:
            manifest = write_fixture(Path(temporary))
            replace_log(manifest, lambda text: text.replace("state3=1", f"state3={state3}"))
            report = summary.build_report(manifest)
        assert report["passed"] is False, (state3, report)


def test_gate_callback_hitbox_and_thread_must_match_in_order() -> None:
    changes = (
        ("eax=1", "eax=0"), ("click_flag=1", "click_flag=0"), ("button0=80", "button0=0"),
        ("upper_exclusive=671", "upper_exclusive=672"), ("upper_exclusive=559", "upper_exclusive=560"),
        ("x=608 y=528", "x=416 y=400"), ("ret=00419c60", "ret=00419c63"),
        ("eip=00409d80", "eip=0042d4e0"), ("argument=00511d40", "argument=00514b78"),
        ("selected_unit=2", "selected_unit=-1"),
        ("HDLAYOUT_INPUT_CALLBACK tid=1a2", "HDLAYOUT_INPUT_CALLBACK tid=2b3"),
        ("HDLAYOUT_INPUT_GATE_OBSERVED tid=1a2 desc=00511d40", "HDLAYOUT_INPUT_GATE_OBSERVED tid=1a2 desc=00514b78"),
    )
    for old, new in changes:
        with tempfile.TemporaryDirectory() as temporary:
            manifest = write_fixture(Path(temporary))
            replace_log(manifest, lambda text: text.replace(old, new))
            report = summary.build_report(manifest)
        assert not report["passed"], (old, report)
        assert report["status"] == "incomplete_evidence", (old, report)
    with tempfile.TemporaryDirectory() as temporary:
        manifest = write_fixture(Path(temporary))
        replace_log(manifest, lambda text: "\n".join([*text.splitlines()[:5], text.splitlines()[6], text.splitlines()[5], text.splitlines()[7]]) + "\n")
        report = summary.build_report(manifest)
        assert not report["passed"], report


def test_provenance_approval_and_observation_purity_fail_closed() -> None:
    for mutation in ("log_hash", "candidate_identity", "unknown_stage", "stable_stage", "hidden", "manual_template",
                     "expired", "stale_approval", "approval_identity", "malformed_approval", "probe_mutation", "forced_marker", "runtime_error",
                     "target_register_write", "target_input_write",
                     "duplicate_identity", "duplicate_field", "printf_echo_only", "missing_log"):
        with tempfile.TemporaryDirectory() as temporary:
            manifest_path = write_fixture(Path(temporary))
            manifest = summary.read_object(manifest_path)
            if mutation == "log_hash":
                manifest["raw_log"]["sha256"] = "0" * 64
            elif mutation == "candidate_identity":
                manifest["identity"]["candidate_sha256"] = "a" * 64
            elif mutation in ("unknown_stage", "stable_stage"):
                manifest["identity"]["stage"] = "unknown" if mutation == "unknown_stage" else summary.STABLE_STAGE
            elif mutation == "hidden":
                manifest["identity"]["environment"] = "hidden_cdb_host"
            elif mutation in ("manual_template", "expired", "stale_approval", "approval_identity", "malformed_approval"):
                approval_path = Path(manifest["approval"]["path"])
                approval = summary.read_object(approval_path)
                if mutation == "manual_template":
                    approval["approved"] = False
                elif mutation == "expired":
                    approval["expires_at"] = "2026-09-05T09:59:00+00:00"
                elif mutation == "stale_approval":
                    approval["approved_at"] = "2026-09-04T09:00:00+00:00"
                elif mutation == "malformed_approval":
                    approval["identity"] = ["not an object"]
                else:
                    approval["identity"]["run_id"] = "other-run"
                write_json(approval_path, approval)
                manifest["approval"] = file_ref(approval_path)
            elif mutation == "probe_mutation":
                rendered = Path(manifest["probe"]["rendered_path"])
                rendered.write_text(rendered.read_text(encoding="utf-8") + "\nr eax=1\n", encoding="utf-8")
                manifest["probe"]["rendered_sha256"] = summary.sha256(rendered.read_bytes())
            elif mutation == "missing_log":
                Path(manifest["raw_log"]["path"]).unlink()
            else:
                transformations = {
                    "forced_marker": lambda text: text + "HDLAYOUT_PANEL_REDRAW_INVOKE forced=1\n",
                    "runtime_error": lambda text: text + "Unable to insert breakpoint 0 at 00419c51\n",
                    "target_register_write": lambda text: text + "0:000> r eax=1\n",
                    "target_input_write": lambda text: text + "0:000> ed 00544d04 1\n",
                    "duplicate_identity": lambda text: text + text.splitlines()[0] + "\n",
                    "duplicate_field": lambda text: text.replace("eax=1", "eax=1 eax=1"),
                    "printf_echo_only": lambda text: "\n".join('0:000> .echo ' + line for line in text.splitlines()) + "\n",
                }
                replace_log(manifest_path, transformations[mutation])
                manifest = summary.read_object(manifest_path)
            write_json(manifest_path, manifest)
            report = summary.build_report(manifest_path)
        assert not report["passed"], (mutation, report)
        assert report["status"] == ("missing_evidence" if mutation == "missing_log" else "invalid_evidence"), (mutation, report)
        assert not report["command_click_alignment"] and not report["panel_click_callback_proof"]


def test_probe_has_only_observation_commands_and_verified_addresses() -> None:
    probe = summary.PROBE.read_text(encoding="utf-8")
    assert not re.search(r"(?:^|[;{])\s*(?:r\s|e[bwdq]\s|\.call\b|g\s*=)", probe, re.MULTILINE)
    assert re.findall(r"^bp ([0-9A-F]+)", probe, re.MULTILINE) == [
        "00419B88", "00419BE5", "00419C20", "00419C47", "00419C51", "00419C5D", "00409D80"]
    assert probe.count("; gc\"") == 7


def test_prelaunch_approval_and_measured_session_cannot_be_rebound() -> None:
    for mutation in ("missing_receipt", "wrong_parent", "wrong_window_owner", "same_pid", "reused_process", "cleanup",
                     "session_failure", "wrong_process_path", "wrong_process_sha", "forced_startup", "wrong_launch",
                     "wrong_plan", "predicted_hwnd_approval", "changed_wrapper", "missing_environment", "wrong_environment",
                     "bad_environment_digest", "unaware_process", "unaware_window", "boolean_awareness", "filtered_client"):
        with tempfile.TemporaryDirectory() as temporary:
            path = write_fixture(Path(temporary))
            manifest = summary.read_object(path)
            receipt_path = Path(manifest["session_receipt"]["path"])
            receipt = summary.read_object(receipt_path)
            if mutation == "missing_receipt":
                receipt_path.unlink()
            elif mutation == "wrong_parent": receipt["candidate_parent_pid"] = 888
            elif mutation == "wrong_window_owner": receipt["hwnd_pid"] = 888
            elif mutation == "same_pid": receipt["candidate_pid"] = receipt["cdb_pid"]
            elif mutation == "reused_process": receipt["candidate_creation_filetime"] = 1
            elif mutation == "cleanup": receipt["cleanup"]["candidate_stopped"] = False
            elif mutation == "session_failure": receipt["failures"] = ["no stable capture pair"]
            elif mutation == "wrong_process_path": receipt["process_image_path"] = r"C:\Clash\clash95.exe"
            elif mutation == "wrong_process_sha": receipt["process_image_sha256"] = "f" * 64
            elif mutation == "missing_environment": receipt.pop("launch_environment")
            elif mutation == "wrong_environment": receipt["launch_environment"]["policy"]["set"]["__COMPAT_LAYER"] = "DPIUNAWARE"
            elif mutation == "bad_environment_digest": receipt["launch_environment"]["effective_environment_sha256"] = "unknown"
            elif mutation == "unaware_process": receipt["candidate_dpi_awareness"] = 0
            elif mutation == "unaware_window": receipt["window_dpi_awareness"] = 0
            elif mutation == "boolean_awareness": receipt["candidate_dpi_awareness"] = True
            elif mutation == "filtered_client": receipt["physical_client_size"] = [1200, 900]
            elif mutation == "forced_startup":
                startup = Path(receipt["startup_probe"]["path"])
                startup.write_text(startup.read_text(encoding="utf-8") + "r eax=1\n", encoding="utf-8")
                receipt["startup_probe"] = file_ref(startup)
            elif mutation == "wrong_launch": receipt["launch_command"][-1] = r"C:\Clash\clash95.exe"
            elif mutation == "wrong_plan":
                plan = Path(receipt["plan"]["path"])
                record = summary.read_object(plan); record["identity"]["input_plan"] = {"inject_input": True}
                write_json(plan, record); receipt["plan"] = file_ref(plan)
            elif mutation == "predicted_hwnd_approval":
                approval_path = Path(manifest["approval"]["path"])
                approval = summary.read_object(approval_path)
                approval["identity"]["hwnd"] = manifest["identity"]["hwnd"]
                write_json(approval_path, approval)
                manifest["approval"] = receipt["approval"] = file_ref(approval_path)
            elif mutation == "changed_wrapper":
                Path(manifest["identity"]["wrapper"]["path"]).write_bytes(b"different wrapper")
            if mutation != "missing_receipt":
                write_json(receipt_path, receipt)
                manifest["session_receipt"] = file_ref(receipt_path)
            write_json(path, manifest)
            report = summary.build_report(path)
        assert report["passed"] is False, (mutation, report)
        assert report["status"] == ("missing_evidence" if mutation == "missing_receipt" else "invalid_evidence"), (mutation, report)


def test_cli_writes_only_requested_temporary_outputs() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        manifest = write_fixture(root)
        output = root / "summary.json"
        markdown = root / "summary.md"
        command = [sys.executable, "-B", str(Path(summary.__file__)), str(manifest),
                   "--write-json", str(output), "--write-markdown", str(markdown), "--require-pass"]
        run = subprocess.run(command, capture_output=True, text=True, check=False)
        assert run.returncode == 0, run.stdout + run.stderr
        assert summary.read_object(output)["passed"] is True
        assert "Manual DirectInput proof: False" in markdown.read_text(encoding="utf-8")
        replace_log(manifest, lambda text: text.replace("eax=1", "eax=0"))
        run = subprocess.run(command, capture_output=True, text=True, check=False)
        assert run.returncode == 2, run.stdout + run.stderr
        assert summary.read_object(output)["passed"] is False


def run_tests() -> None:
    test_observed_sequence_preserves_scope()
    test_missing_and_incomplete_are_distinct()
    test_native_selected_sprite_state_contract()
    test_click_boundary_rejects_an_earlier_success_and_invalid_state3()
    test_gate_callback_hitbox_and_thread_must_match_in_order()
    test_provenance_approval_and_observation_purity_fail_closed()
    test_probe_has_only_observation_commands_and_verified_addresses()
    test_prelaunch_approval_and_measured_session_cannot_be_rebound()
    test_cli_writes_only_requested_temporary_outputs()


if __name__ == "__main__":
    run_tests()
    print("hd_layout_command_input_summary tests: PASS")
