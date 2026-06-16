#!/usr/bin/env python3
"""Fixture tests for the manual DirectInput proof template helper."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "manual_directinput_proof_template.py"
sys.path.insert(0, str(ROOT / "tools"))

import manual_directinput_checklist  # noqa: E402
import manual_directinput_proof_template  # noqa: E402


def run_script(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def test_template_fails_as_proof() -> None:
    template = manual_directinput_proof_template.build_template()
    assert template["candidate_path"].startswith("C:\\ClashTests\\manual-directinput\\"), template
    assert "C:\\ClashTests" in template["candidate_path_policy"], template
    assert "C:\\Clash\\clash95.exe" in template["candidate_path_policy"], template
    failures = manual_directinput_checklist.validate_manual_proof_data(template)
    assert failures, template
    assert any("evidence_class" in failure for failure in failures), failures
    assert any("approved_visible_runtime" in failure for failure in failures), failures
    assert any("approval_record" in failure for failure in failures), failures
    assert any("candidate_path" in failure for failure in failures), failures
    assert any("64-hex" in failure for failure in failures), failures
    assert any("no_stale_processes" in failure for failure in failures), failures
    assert any("status pass/passed" in failure for failure in failures), failures
    assert any("no_crash=true" in failure for failure in failures), failures


def test_report_shape() -> None:
    report = manual_directinput_proof_template.build_report(
        Path("captures/current/manual-directinput-proof-template-current.json")
    )
    assert report["passed"] is True, report
    assert report["template_valid_as_proof"] is False, report
    assert report["candidate_path_template"].startswith("C:\\ClashTests\\"), report
    assert "C:\\ClashTests" in report["candidate_path_policy"], report
    assert "repository-local" in report["candidate_path_policy"], report
    assert report["required_ids"] == manual_directinput_checklist.REQUIRED_IDS, report
    assert report["checked_template_ids"] == manual_directinput_checklist.REQUIRED_IDS, report


def test_template_can_become_valid_after_replacing_placeholders() -> None:
    proof = manual_directinput_proof_template.build_template()
    proof["evidence_class"] = "manual_directinput"
    proof["approved_visible_runtime"] = True
    proof["approval_record"] = "User explicitly approved visible manual DirectInput validation."
    proof["candidate_path"] = "C:\\ClashTests\\manual-proof\\clash95_hd_manual.exe"
    proof["executable_sha256"] = "c" * 64
    proof["no_stale_processes"] = True
    for item in proof["checked_items"]:
        item["status"] = "passed"
        item["observed_result"] = f"{item['id']} passed with real mouse input."
        item["evidence"] = f"manual screenshot or notes for {item['id']}"
        item["pass_fail_notes"] = f"{item['id']} passed with no crash."
        item["no_crash"] = True
    failures = manual_directinput_checklist.validate_manual_proof_data(proof)
    assert failures == [], failures


def test_cli_writes_outputs(fixture: Path) -> None:
    out_template = fixture / "template.json"
    out_json = fixture / "report.json"
    out_md = fixture / "report.md"
    run = run_script(
        "--write-template-json",
        str(out_template),
        "--write-json",
        str(out_json),
        "--write-markdown",
        str(out_md),
        "--require-pass",
    )
    assert run.returncode == 0, run.stdout + run.stderr
    template = json.loads(out_template.read_text(encoding="utf-8"))
    report = json.loads(out_json.read_text(encoding="utf-8"))
    assert template["evidence_class"] == "manual_directinput_template", template
    assert template["candidate_path"].startswith("C:\\ClashTests\\"), template
    assert "candidate_path_policy" in template, template
    assert report["passed"] is True, report
    assert report["template_valid_as_proof"] is False, report
    assert "- Candidate path policy:" in out_md.read_text(encoding="utf-8")
    assert "- Template valid as proof: `False`" in out_md.read_text(encoding="utf-8")


def run_tests() -> None:
    fixture = ROOT / ".codex-loop" / "tmp-tests" / "manual-directinput-proof-template-fixture"
    shutil.rmtree(fixture, ignore_errors=True)
    fixture.mkdir(parents=True)
    try:
        test_template_fails_as_proof()
        test_report_shape()
        test_template_can_become_valid_after_replacing_placeholders()
        test_cli_writes_outputs(fixture / "cli")
    finally:
        shutil.rmtree(fixture, ignore_errors=True)


def main() -> int:
    run_tests()
    print("manual DirectInput proof template tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
