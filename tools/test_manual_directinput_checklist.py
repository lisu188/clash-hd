#!/usr/bin/env python3
"""Fixture tests for the manual DirectInput validation checklist."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "manual_directinput_checklist.py"
sys.path.insert(0, str(ROOT / "tools"))

import manual_directinput_checklist  # noqa: E402


def run_script(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def args_for(**overrides: object) -> argparse.Namespace:
    values = {
        "manual_proof": None,
        "allow_cdb_only_promotion": False,
        "repo_root": None,
    }
    values.update(overrides)
    return argparse.Namespace(**values)


def write_valid_manual_proof(path: Path) -> None:
    proof = {
        "evidence_class": "manual_directinput",
        "approved_visible_runtime": True,
        "approval_record": "User explicitly approved visible manual DirectInput validation.",
        "candidate_path": "C:\\ClashTests\\manual-proof\\clash95_hd_manual.exe",
        "executable_sha256": "A" * 64,
        "no_stale_processes": True,
        "checked_items": [
            {
                "id": item["id"],
                "stage": item["stage"],
                "status": "passed",
                "observed_result": f"{item['id']} manual route passed with real mouse input.",
                "evidence": f"manual screenshot or notes for {item['id']}",
                "pass_fail_notes": f"{item['id']} passed; no crash observed.",
                "no_crash": True,
            }
            for item in manual_directinput_checklist.CHECKLIST_ITEMS
        ],
    }
    path.write_text(json.dumps(proof, indent=2) + "\n", encoding="utf-8")


def _checked_items() -> list[dict[str, object]]:
    return [
        {
            "id": item["id"],
            "stage": item["stage"],
            "status": "passed",
            "observed_result": f"{item['id']} guest route passed with real QMP input.",
            "evidence": f"guest frame evidence for {item['id']}",
            "pass_fail_notes": f"{item['id']} passed in guest; no crash observed.",
            "no_crash": True,
        }
        for item in manual_directinput_checklist.CHECKLIST_ITEMS
    ]


def write_valid_guest_proof(path: Path, repo_root: Path, frame_count: int = 2) -> list[str]:
    """Write a valid approved_guest_win98_directdraw proof.

    Frame evidence files are created under ``repo_root`` and referenced with
    repo-relative paths so the validator's existence check resolves them.
    """
    frames_dir = repo_root / "guest-frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    refs: list[str] = []
    for index in range(frame_count):
        frame = frames_dir / f"guest-frame-{index}.ppm"
        frame.write_bytes(b"P6\n8 6\n255\n" + b"\x00" * (8 * 6 * 3))
        refs.append(frame.relative_to(repo_root).as_posix())
    proof = {
        "evidence_class": "approved_guest_win98_directdraw",
        "approved_visible_runtime": True,
        "approval_record": "User explicitly approved a guest Win98 DirectDraw validation pass.",
        "candidate_path": "C:\\ClashTests\\manual-directinput\\clash95_hd_guest.exe",
        "executable_sha256": "B" * 64,
        "no_stale_processes": True,
        "guest_machine_id": "clash-hd-vm",
        "qmp_input_log_ref": "captures/current/guest-qmp-input-log.jsonl",
        "candidate_sha256_staged_in_guest": "C" * 64,
        "frame_evidence_refs": refs,
        "checked_items": _checked_items(),
    }
    path.write_text(json.dumps(proof, indent=2) + "\n", encoding="utf-8")
    return refs


def test_guest_proof_marks_promotion_ready(fixture: Path) -> None:
    proof = fixture / "guest-proof.json"
    write_valid_guest_proof(proof, fixture)
    checklist = manual_directinput_checklist.build_checklist(
        args_for(manual_proof=proof, repo_root=fixture)
    )
    assert checklist["passed"] is True, checklist
    assert checklist["manual_proof_supplied"] is True, checklist
    assert checklist["manual_proof_valid"] is True, checklist
    assert checklist["promotion_ready"] is True, checklist
    assert (
        checklist["manual_proof_summary"]["evidence_class"]
        == "approved_guest_win98_directdraw"
    ), checklist


def test_guest_proof_missing_machine_id_fails_closed(fixture: Path) -> None:
    proof = fixture / "guest-no-machine.json"
    write_valid_guest_proof(proof, fixture)
    payload = json.loads(proof.read_text(encoding="utf-8"))
    del payload["guest_machine_id"]
    proof.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    checklist = manual_directinput_checklist.build_checklist(
        args_for(manual_proof=proof, repo_root=fixture)
    )
    assert checklist["manual_proof_valid"] is False, checklist
    assert any("guest_machine_id" in failure for failure in checklist["failures"]), checklist


def test_guest_proof_placeholder_qmp_log_fails_closed(fixture: Path) -> None:
    proof = fixture / "guest-placeholder-qmp.json"
    write_valid_guest_proof(proof, fixture)
    payload = json.loads(proof.read_text(encoding="utf-8"))
    payload["qmp_input_log_ref"] = "REPLACE_WITH_QMP_LOG_PATH"
    proof.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    checklist = manual_directinput_checklist.build_checklist(
        args_for(manual_proof=proof, repo_root=fixture)
    )
    assert checklist["manual_proof_valid"] is False, checklist
    assert any("qmp_input_log_ref" in failure for failure in checklist["failures"]), checklist


def test_guest_proof_non_hex_staged_sha_fails_closed(fixture: Path) -> None:
    proof = fixture / "guest-bad-sha.json"
    write_valid_guest_proof(proof, fixture)
    payload = json.loads(proof.read_text(encoding="utf-8"))
    payload["candidate_sha256_staged_in_guest"] = "not-a-sha"
    proof.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    checklist = manual_directinput_checklist.build_checklist(
        args_for(manual_proof=proof, repo_root=fixture)
    )
    assert checklist["manual_proof_valid"] is False, checklist
    assert any(
        "candidate_sha256_staged_in_guest" in failure for failure in checklist["failures"]
    ), checklist


def test_guest_proof_empty_frame_refs_fails_closed(fixture: Path) -> None:
    proof = fixture / "guest-empty-frames.json"
    write_valid_guest_proof(proof, fixture)
    payload = json.loads(proof.read_text(encoding="utf-8"))
    payload["frame_evidence_refs"] = []
    proof.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    checklist = manual_directinput_checklist.build_checklist(
        args_for(manual_proof=proof, repo_root=fixture)
    )
    assert checklist["manual_proof_valid"] is False, checklist
    assert any("frame_evidence_refs" in failure for failure in checklist["failures"]), checklist


def test_guest_proof_nonexistent_frame_ref_fails_closed(fixture: Path) -> None:
    proof = fixture / "guest-missing-frame.json"
    write_valid_guest_proof(proof, fixture)
    payload = json.loads(proof.read_text(encoding="utf-8"))
    payload["frame_evidence_refs"].append("guest-frames/does-not-exist.ppm")
    proof.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    checklist = manual_directinput_checklist.build_checklist(
        args_for(manual_proof=proof, repo_root=fixture)
    )
    assert checklist["manual_proof_valid"] is False, checklist
    assert any("does not exist" in failure for failure in checklist["failures"]), checklist


def test_guest_proof_frame_ref_under_live_tree_fails_closed(fixture: Path) -> None:
    proof = fixture / "guest-live-frame.json"
    write_valid_guest_proof(proof, fixture)
    payload = json.loads(proof.read_text(encoding="utf-8"))
    payload["frame_evidence_refs"].append("C:\\Clash\\save\\guest-frame.ppm")
    proof.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    checklist = manual_directinput_checklist.build_checklist(
        args_for(manual_proof=proof, repo_root=fixture)
    )
    assert checklist["manual_proof_valid"] is False, checklist
    assert any(
        "must not be under C:\\Clash" in failure for failure in checklist["failures"]
    ), checklist


def test_host_manifest_cannot_borrow_guest_field_to_skip_host_field(fixture: Path) -> None:
    # A host manifest that drops a host field (executable_sha256) but carries a
    # guest-only field (candidate_sha256_staged_in_guest) must still fail on the
    # missing host field; the guest field is not a substitute.
    proof = fixture / "host-borrow-guest.json"
    write_valid_manual_proof(proof)
    payload = json.loads(proof.read_text(encoding="utf-8"))
    del payload["executable_sha256"]
    payload["candidate_sha256_staged_in_guest"] = "D" * 64
    payload["guest_machine_id"] = "clash-hd-vm"
    proof.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    checklist = manual_directinput_checklist.build_checklist(
        args_for(manual_proof=proof, repo_root=fixture)
    )
    assert checklist["manual_proof_valid"] is False, checklist
    assert any("executable_sha256" in failure for failure in checklist["failures"]), checklist


def test_guest_manifest_cannot_skip_host_field(fixture: Path) -> None:
    # A guest manifest that omits a shared host field (no_stale_processes) must
    # still fail on that host field even though every guest field is present.
    proof = fixture / "guest-skip-host.json"
    write_valid_guest_proof(proof, fixture)
    payload = json.loads(proof.read_text(encoding="utf-8"))
    payload["no_stale_processes"] = False
    proof.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    checklist = manual_directinput_checklist.build_checklist(
        args_for(manual_proof=proof, repo_root=fixture)
    )
    assert checklist["manual_proof_valid"] is False, checklist
    assert any("no_stale_processes" in failure for failure in checklist["failures"]), checklist


def test_default_checklist_passes_but_blocks_promotion() -> None:
    checklist = manual_directinput_checklist.build_checklist(args_for())
    assert checklist["passed"] is True, checklist
    assert checklist["promotion_ready"] is False, checklist
    assert checklist["stable_stage_should_change"] is False, checklist
    assert checklist["summary"]["pending_count"] == len(manual_directinput_checklist.REQUIRED_IDS), checklist


def test_checklist_records_no_popup_operator_preference() -> None:
    checklist = manual_directinput_checklist.build_checklist(args_for())
    preference = checklist.get("no_popup_operator_preference", "")
    assert "Do not launch Clash95, CDB, wrappers, PowerShell harnesses" in preference, checklist
    assert "unless the user explicitly approves" in preference, checklist
    assert preference in checklist["checklist_policy"], checklist


def test_missing_required_item_fails_closed() -> None:
    items = [
        item
        for item in manual_directinput_checklist.CHECKLIST_ITEMS
        if item["id"] != "castle_overview_centered_input"
    ]
    checklist = manual_directinput_checklist.build_checklist(args_for(), items=items)
    assert checklist["passed"] is False, checklist
    assert any("castle_overview_centered_input" in failure for failure in checklist["failures"]), checklist


def test_missing_required_field_fails_closed() -> None:
    items = [dict(item) for item in manual_directinput_checklist.CHECKLIST_ITEMS]
    items[0]["input_route"] = ""
    checklist = manual_directinput_checklist.build_checklist(args_for(), items=items)
    assert checklist["passed"] is False, checklist
    assert any("input_route" in failure for failure in checklist["failures"]), checklist


def test_manual_proof_path_marks_promotion_ready(fixture: Path) -> None:
    proof = fixture / "manual-proof.json"
    write_valid_manual_proof(proof)
    checklist = manual_directinput_checklist.build_checklist(args_for(manual_proof=proof))
    assert checklist["passed"] is True, checklist
    assert checklist["manual_proof_supplied"] is True, checklist
    assert checklist["manual_proof_valid"] is True, checklist
    assert checklist["promotion_ready"] is True, checklist


def test_placeholder_manual_proof_fails_closed(fixture: Path) -> None:
    proof = fixture / "placeholder-proof.json"
    proof.write_text('{"manual_input": "placeholder"}\n', encoding="utf-8")
    checklist = manual_directinput_checklist.build_checklist(args_for(manual_proof=proof))
    assert checklist["passed"] is False, checklist
    assert checklist["manual_proof_supplied"] is True, checklist
    assert checklist["manual_proof_valid"] is False, checklist
    assert checklist["promotion_ready"] is False, checklist
    assert any("evidence_class" in failure for failure in checklist["failures"]), checklist


def test_manual_proof_requires_observations_crash_and_process_hygiene(fixture: Path) -> None:
    proof = fixture / "missing-observation-proof.json"
    write_valid_manual_proof(proof)
    payload = json.loads(proof.read_text(encoding="utf-8"))
    payload["no_stale_processes"] = False
    payload["checked_items"][0]["evidence"] = "REPLACE_WITH_SCREENSHOT_OR_NOTES"
    payload["checked_items"][1]["no_crash"] = False
    proof.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    checklist = manual_directinput_checklist.build_checklist(args_for(manual_proof=proof))
    assert checklist["passed"] is False, checklist
    assert checklist["manual_proof_valid"] is False, checklist
    assert any("no_stale_processes" in failure for failure in checklist["failures"]), checklist
    assert any("non-placeholder evidence" in failure for failure in checklist["failures"]), checklist
    assert any("no_crash=true" in failure for failure in checklist["failures"]), checklist


def test_manual_proof_rejects_live_or_repo_candidate_paths(fixture: Path) -> None:
    live_proof = fixture / "live-original-proof.json"
    write_valid_manual_proof(live_proof)
    live_payload = json.loads(live_proof.read_text(encoding="utf-8"))
    live_payload["candidate_path"] = "C:\\Clash\\clash95.exe"
    live_proof.write_text(json.dumps(live_payload, indent=2) + "\n", encoding="utf-8")
    live_checklist = manual_directinput_checklist.build_checklist(args_for(manual_proof=live_proof))

    repo_proof = fixture / "repo-candidate-proof.json"
    write_valid_manual_proof(repo_proof)
    repo_payload = json.loads(repo_proof.read_text(encoding="utf-8"))
    repo_payload["candidate_path"] = str(ROOT / "clash95_hd_manual.exe")
    repo_proof.write_text(json.dumps(repo_payload, indent=2) + "\n", encoding="utf-8")
    repo_checklist = manual_directinput_checklist.build_checklist(args_for(manual_proof=repo_proof))

    assert live_checklist["manual_proof_valid"] is False, live_checklist
    assert repo_checklist["manual_proof_valid"] is False, repo_checklist
    assert any("must not be the live original" in failure for failure in live_checklist["failures"]), live_checklist
    assert any("must be under C:\\ClashTests" in failure for failure in repo_checklist["failures"]), repo_checklist


def test_explicit_cdb_only_override_marks_promotion_ready() -> None:
    checklist = manual_directinput_checklist.build_checklist(
        args_for(allow_cdb_only_promotion=True)
    )
    assert checklist["passed"] is True, checklist
    assert checklist["manual_proof_supplied"] is False, checklist
    assert checklist["promotion_ready"] is True, checklist


def test_cli_writes_outputs_and_fails_promotion_ready(fixture: Path) -> None:
    out_json = fixture / "manual-checklist.json"
    out_md = fixture / "manual-checklist.md"
    good = run_script(
        "--write-json",
        str(out_json),
        "--write-markdown",
        str(out_md),
        "--require-pass",
    )
    assert good.returncode == 0, good.stdout + good.stderr
    assert json.loads(out_json.read_text(encoding="utf-8"))["passed"] is True
    assert "- Overall: PASS" in out_md.read_text(encoding="utf-8")

    blocked = run_script(
        "--write-json",
        str(fixture / "blocked.json"),
        "--write-markdown",
        str(fixture / "blocked.md"),
        "--require-promotion-ready",
    )
    assert blocked.returncode == 2, blocked.stdout + blocked.stderr
    assert json.loads((fixture / "blocked.json").read_text(encoding="utf-8"))["promotion_ready"] is False

    bad_proof = fixture / "bad-proof.json"
    bad_proof.write_text('{"manual_input": "placeholder"}\n', encoding="utf-8")
    invalid = run_script(
        "--manual-proof",
        str(bad_proof),
        "--write-json",
        str(fixture / "invalid.json"),
        "--write-markdown",
        str(fixture / "invalid.md"),
        "--require-pass",
    )
    assert invalid.returncode == 2, invalid.stdout + invalid.stderr
    invalid_payload = json.loads((fixture / "invalid.json").read_text(encoding="utf-8"))
    assert invalid_payload["manual_proof_valid"] is False


def run_tests() -> None:
    fixture = ROOT / ".codex-loop" / "tmp-tests" / "manual-directinput-fixture"
    shutil.rmtree(fixture, ignore_errors=True)
    fixture.mkdir(parents=True)
    try:
        test_default_checklist_passes_but_blocks_promotion()
        test_checklist_records_no_popup_operator_preference()
        test_missing_required_item_fails_closed()
        test_missing_required_field_fails_closed()
        test_manual_proof_path_marks_promotion_ready(fixture)
        test_placeholder_manual_proof_fails_closed(fixture)
        test_manual_proof_requires_observations_crash_and_process_hygiene(fixture)
        test_manual_proof_rejects_live_or_repo_candidate_paths(fixture)
        test_guest_proof_marks_promotion_ready(fixture)
        test_guest_proof_missing_machine_id_fails_closed(fixture)
        test_guest_proof_placeholder_qmp_log_fails_closed(fixture)
        test_guest_proof_non_hex_staged_sha_fails_closed(fixture)
        test_guest_proof_empty_frame_refs_fails_closed(fixture)
        test_guest_proof_nonexistent_frame_ref_fails_closed(fixture)
        test_guest_proof_frame_ref_under_live_tree_fails_closed(fixture)
        test_host_manifest_cannot_borrow_guest_field_to_skip_host_field(fixture)
        test_guest_manifest_cannot_skip_host_field(fixture)
        test_explicit_cdb_only_override_marks_promotion_ready()
        test_cli_writes_outputs_and_fails_promotion_ready(fixture)
    finally:
        shutil.rmtree(fixture, ignore_errors=True)


def main() -> int:
    run_tests()
    print("manual DirectInput checklist tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
