#!/usr/bin/env python3
"""Regression tests for no-popup guard helpers."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BOUNDARY_SCRIPT = ROOT / "tools" / "no_popup_boundary_guard.py"
SURFACE_POLICY_SCRIPT = ROOT / "tools" / "surface_dump_policy_guard.py"
sys.path.insert(0, str(ROOT / "tools"))

import no_popup_boundary_guard  # noqa: E402
import surface_dump_policy_guard  # noqa: E402


def run_script(script: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(script), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def refresh_payload(fixture: Path, *, failed_guard: str | None = None) -> dict:
    checks: dict[str, dict] = {}
    for name, requirement in no_popup_boundary_guard.REQUIRED_REPORTS.items():
        report = fixture / requirement["markdown"]
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(f"# {name}\n", encoding="utf-8")
        passed = name != failed_guard
        checks[name] = {
            "passed": passed,
            "markdown": str(report),
            "json": str(report.with_suffix(".json")),
            "failures": [] if passed else ["intentional fixture failure"],
        }
    return {"passed": failed_guard is None, "checks": checks}


def write_evidence_index(path: Path, *, missing_link: str | None = None) -> None:
    lines = ["# Evidence", ""]
    for requirement in no_popup_boundary_guard.REQUIRED_REPORTS.values():
        markdown = requirement["markdown"]
        if markdown == missing_link:
            continue
        lines.append(f"- [{markdown}]({markdown})")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def good_surface_dump_script() -> str:
    return r"""
param(
    [switch]$AllowVisibleDesktop
)

$launchMode = 'hidden-desktop'

if ($AllowVisibleDesktop) {
    $launchMode = 'visible-desktop-explicit'
    $cdbProcess = Start-Process -FilePath $Cdb -ArgumentList $cdbArgs -WindowStyle Hidden
}
else {
    $launch = Start-CdbOnHiddenDesktop -CdbPath $Cdb -Arguments $cdbArgs -WorkingDirectory $WorkDir -DesktopName $desktopName
}

throw "CreateDesktop failed with Win32 error 5. Refusing visible fallback without -AllowVisibleDesktop."

$summary = [pscustomobject]@{
    HiddenDesktop = (-not $AllowVisibleDesktop)
    AllowVisibleDesktop = [bool]$AllowVisibleDesktop
}

$summaryObject = [pscustomobject]@{
    HiddenDesktop = (-not $AllowVisibleDesktop)
    AllowVisibleDesktop = [bool]$AllowVisibleDesktop
}
"""


def test_boundary_guard(fixture: Path) -> None:
    evidence = fixture / "evidence.md"
    refresh_json = fixture / "refresh.json"
    out_json = fixture / "boundary.json"
    out_md = fixture / "boundary.md"

    write_evidence_index(evidence)
    refresh_json.write_text(json.dumps(refresh_payload(fixture)), encoding="utf-8")
    good_args = argparse.Namespace(refresh_json=refresh_json, evidence_index=evidence)
    good = no_popup_boundary_guard.build_guard(good_args)
    assert good["passed"] is True, good
    assert good["required_guard_count"] == 6, good
    assert "visible_runtime_launcher_guard" in good["required_guards"], good

    good_run = run_script(
        BOUNDARY_SCRIPT,
        "--refresh-json",
        str(refresh_json),
        "--evidence-index",
        str(evidence),
        "--write-json",
        str(out_json),
        "--write-markdown",
        str(out_md),
        "--require-pass",
    )
    assert good_run.returncode == 0, good_run.stdout + good_run.stderr
    assert out_json.is_file(), out_json
    assert out_md.is_file(), out_md

    for requirement in no_popup_boundary_guard.REQUIRED_REPORTS.values():
        missing_link = requirement["markdown"]
        write_evidence_index(evidence, missing_link=missing_link)
        missing = no_popup_boundary_guard.build_guard(good_args)
        assert missing["passed"] is False, missing
        assert any(missing_link in failure for failure in missing["failures"]), missing

    write_evidence_index(evidence)
    missing_check_payload = refresh_payload(fixture)
    missing_check_payload["checks"].pop("process_hygiene_guard")
    refresh_json.write_text(json.dumps(missing_check_payload), encoding="utf-8")
    missing_check = no_popup_boundary_guard.build_guard(good_args)
    assert missing_check["passed"] is False, missing_check
    assert any("missing refresh check: process_hygiene_guard" in failure for failure in missing_check["failures"]), missing_check

    for support_name in no_popup_boundary_guard.REQUIRED_SUPPORTING_REPORTS:
        missing_support_payload = refresh_payload(fixture)
        missing_support_payload["checks"].pop(support_name)
        refresh_json.write_text(json.dumps(missing_support_payload), encoding="utf-8")
        missing_support = no_popup_boundary_guard.build_guard(good_args)
        assert missing_support["passed"] is False, missing_support
        assert any(
            f"missing refresh check: {support_name}" in failure
            for failure in missing_support["failures"]
        ), missing_support

    failed_payload = refresh_payload(fixture, failed_guard="surface_dump_policy_guard")
    refresh_json.write_text(json.dumps(failed_payload), encoding="utf-8")
    failed = no_popup_boundary_guard.build_guard(good_args)
    assert failed["passed"] is False, failed
    assert any("refresh check is not passing: surface_dump_policy_guard" in failure for failure in failed["failures"]), failed


def test_surface_dump_policy_guard(fixture: Path) -> None:
    good_script = fixture / "scripts/cdb/run_cdb_surface_dump.ps1"
    bad_script = fixture / "bad_surface_dump.ps1"
    out_json = fixture / "surface-policy.json"
    out_md = fixture / "surface-policy.md"
    good_script.parent.mkdir(parents=True, exist_ok=True)
    good_script.write_text(good_surface_dump_script(), encoding="utf-8")
    bad_script.write_text(
        good_surface_dump_script().replace("visible-desktop-explicit", "visible-desktop"),
        encoding="utf-8",
    )

    good_args = argparse.Namespace(script=good_script)
    good = surface_dump_policy_guard.build_guard(good_args)
    assert good["passed"] is True, good

    good_run = run_script(
        SURFACE_POLICY_SCRIPT,
        "--script",
        str(good_script),
        "--write-json",
        str(out_json),
        "--write-markdown",
        str(out_md),
        "--require-pass",
    )
    assert good_run.returncode == 0, good_run.stdout + good_run.stderr
    assert out_json.is_file(), out_json
    assert out_md.is_file(), out_md

    bad = surface_dump_policy_guard.build_guard(argparse.Namespace(script=bad_script))
    assert bad["passed"] is False, bad
    assert "visible_branch_requires_explicit_switch" in bad["failures"][0], bad

    bad_json = fixture / "bad-surface-policy.json"
    bad_md = fixture / "bad-surface-policy.md"
    bad_run = run_script(
        SURFACE_POLICY_SCRIPT,
        "--script",
        str(bad_script),
        "--write-json",
        str(bad_json),
        "--write-markdown",
        str(bad_md),
        "--require-pass",
    )
    assert bad_run.returncode == 2, bad_run.stdout + bad_run.stderr
    assert bad_json.is_file(), bad_json
    assert bad_md.is_file(), bad_md


def run_tests() -> None:
    fixture = ROOT / ".codex-loop" / "tmp-tests" / "no-popup-guards-fixture"
    shutil.rmtree(fixture, ignore_errors=True)
    fixture.mkdir(parents=True)
    try:
        test_boundary_guard(fixture)
        test_surface_dump_policy_guard(fixture)
    finally:
        shutil.rmtree(fixture, ignore_errors=True)


def main() -> int:
    run_tests()
    print("no-popup guard tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
