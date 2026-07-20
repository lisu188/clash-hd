#!/usr/bin/env python3
"""Assemble the manual DirectInput proof manifest from an approved VM run.

The HD mod is mechanically complete; the only remaining completion work is
capturing *real* visible mouse-click evidence for the five required targets and
feeding it to the promotion-decision tools (see
``reports/hd_completion_certainty.md``). This tool turns the artifacts of an
approved visible runtime session -- captured by either the Windows Sandbox
driver (``scripts/smoke/run_clash_hd_full_validation.ps1``) or the Linux/wine
driver (``tools/run_hd_linux_validation.py``) -- into
``captures/current/manual-directinput-proof-current.json`` in the exact schema
``tools/manual_directinput_checklist.py`` validates.

It is deliberately **fail-closed**: it never invents a passing observation. Each
target must carry a real ``observed_result`` / ``evidence`` / ``pass_fail_notes``
and ``no_crash=true`` (sourced from the run manifest or an operator
``--observations`` file). Anything still holding a template placeholder, missing,
or not marked ``pass`` leaves the manifest invalid, and the tool exits non-zero
so the promotion gate cannot be satisfied by an empty run.

Input run-manifest shape (both drivers emit this)::

    {
      "runner": "linux-wine" | "windows-sandbox",
      "approved_visible_runtime": true,
      "approval_record": "<free text or link to the approval>",
      "no_stale_processes": true,
      "candidate_path": "C:\\ClashTests\\...\\<primary-candidate>.exe",
      "executable_sha256": "<64 hex>",
      "targets": [
        {"id": "stable_menu_load", "candidate_path": "...", "executable_sha256": "...",
         "artifacts": ["...png"], "observed_result": "...", "evidence": "...",
         "pass_fail_notes": "...", "no_crash": true, "status": "pass"},
        ...
      ]
    }

An ``--observations`` file (optional) has the same per-target fields keyed by id;
it is merged over the run-manifest targets so a human can fill observations after
the capture without editing the machine-written run manifest.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import manual_directinput_checklist


DEFAULT_OUTPUT = Path("captures/current/manual-directinput-proof-current.json")
RUNTIME_POLICY = (
    "repo-only manifest assembler; reads approved-run artifacts and writes the "
    "manual DirectInput proof JSON; does not launch Clash95, CDB, wrappers, "
    "PowerShell, or visible windows"
)
GUARD_POLICY = (
    "fail-closed: a target only passes when the approved run supplies a real "
    "observed_result, evidence, pass_fail_notes, no_crash=true, and status=pass; "
    "placeholders never validate"
)

# Per-target observation fields carried into checked_items.
OBSERVATION_FIELDS = ("observed_result", "evidence", "pass_fail_notes")
# Informational extras kept alongside (ignored by the checklist validator).
EXTRA_ITEM_FIELDS = ("candidate_path", "executable_sha256", "artifacts")

_STAGE_BY_ID = {item["id"]: item["stage"] for item in manual_directinput_checklist.CHECKLIST_ITEMS}
_TITLE_BY_ID = {item["id"]: item["title"] for item in manual_directinput_checklist.CHECKLIST_ITEMS}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _targets_by_id(raw: Any) -> dict[str, dict[str, Any]]:
    """Accept either a list of target objects or a dict keyed by id."""
    result: dict[str, dict[str, Any]] = {}
    if isinstance(raw, dict):
        for key, value in raw.items():
            if isinstance(value, dict):
                item = dict(value)
                item.setdefault("id", key)
                result[str(item["id"])] = item
    elif isinstance(raw, list):
        for value in raw:
            if isinstance(value, dict) and value.get("id"):
                result[str(value["id"])] = dict(value)
    return result


def _coerce_bool(value: Any) -> Any:
    """Normalize truthy strings/bools; leave anything else untouched for validation."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str) and value.strip().lower() in {"true", "pass", "passed", "yes"}:
        return True
    if isinstance(value, str) and value.strip().lower() in {"false", "fail", "failed", "no"}:
        return False
    return value


def build_checked_item(item_id: str, merged: dict[str, Any]) -> dict[str, Any]:
    checked: dict[str, Any] = {
        "id": item_id,
        "title": _TITLE_BY_ID.get(item_id, merged.get("title", item_id)),
        "stage": _STAGE_BY_ID[item_id],  # authoritative stage, never taken from input
        "status": str(merged.get("status", "pending")),
        "no_crash": _coerce_bool(merged.get("no_crash", False)),
    }
    for field in OBSERVATION_FIELDS:
        checked[field] = merged.get(field, "")
    for field in EXTRA_ITEM_FIELDS:
        if field in merged:
            checked[field] = merged[field]
    return checked


def build_proof(run_manifest: dict[str, Any], observations: dict[str, Any] | None) -> dict[str, Any]:
    run_targets = _targets_by_id(run_manifest.get("targets"))
    obs_targets = _targets_by_id(observations.get("targets") if observations else None)

    # Top-level observation overrides (approval note, primary candidate, etc.).
    top: dict[str, Any] = {}
    for source in (run_manifest, observations or {}):
        for key in (
            "approved_visible_runtime",
            "approval_record",
            "candidate_path",
            "executable_sha256",
            "no_stale_processes",
        ):
            if source.get(key) not in (None, ""):
                top[key] = source[key]

    checked_items = []
    for item_id in manual_directinput_checklist.REQUIRED_IDS:
        merged: dict[str, Any] = {}
        merged.update(run_targets.get(item_id, {}))
        merged.update(obs_targets.get(item_id, {}))
        checked_items.append(build_checked_item(item_id, merged))

    proof = {
        "evidence_class": "manual_directinput",
        "approved_visible_runtime": _coerce_bool(top.get("approved_visible_runtime", False)),
        "approval_record": top.get("approval_record", "REPLACE_WITH_APPROVAL_NOTE_OR_LINK"),
        "candidate_path": top.get("candidate_path", ""),
        "executable_sha256": top.get("executable_sha256", ""),
        "no_stale_processes": _coerce_bool(top.get("no_stale_processes", False)),
        "checked_items": checked_items,
    }
    return proof


def build_report(
    proof: dict[str, Any],
    *,
    output_path: Path,
    run_manifest_path: Path,
    observations_path: Path | None,
) -> dict[str, Any]:
    failures = manual_directinput_checklist.validate_manual_proof_data(proof)
    passed = not failures
    passing_ids = [
        item.get("id")
        for item in proof.get("checked_items", [])
        if isinstance(item, dict) and str(item.get("status", "")).lower() in manual_directinput_checklist.PASS_STATUSES
    ]
    return {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "runtime_policy": RUNTIME_POLICY,
        "guard_policy": GUARD_POLICY,
        "output_path": str(output_path),
        "run_manifest": str(run_manifest_path),
        "observations": str(observations_path) if observations_path else None,
        "passed": passed,
        "manual_proof_valid": passed,
        "required_ids": list(manual_directinput_checklist.REQUIRED_IDS),
        "passing_ids": passing_ids,
        "checked_item_count": len(proof.get("checked_items", [])),
        "executable_sha256": proof.get("executable_sha256"),
        "candidate_path": proof.get("candidate_path"),
        "failures": failures,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-manifest", type=Path, required=True, help="Run manifest JSON from an approved VM run")
    parser.add_argument("--observations", type=Path, help="Optional operator observations JSON merged over the run manifest")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Where to write the proof manifest")
    parser.add_argument("--write-report-json", type=Path, help="Also write the assembler report JSON here")
    parser.add_argument(
        "--require-valid",
        action="store_true",
        help="Exit non-zero unless the assembled proof passes checklist validation",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    run_manifest = load_json(args.run_manifest)
    if not isinstance(run_manifest, dict):
        print("run manifest must be a JSON object")
        return 2
    observations = None
    if args.observations:
        observations = load_json(args.observations)
        if not isinstance(observations, dict):
            print("observations must be a JSON object")
            return 2

    proof = build_proof(run_manifest, observations)
    report = build_report(
        proof,
        output_path=args.output,
        run_manifest_path=args.run_manifest,
        observations_path=args.observations,
    )

    # Always write the working manifest so the operator can inspect/complete it;
    # validity is reported separately and gates the exit code.
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(proof, indent=2) + "\n", encoding="utf-8")
    if args.write_report_json:
        args.write_report_json.parent.mkdir(parents=True, exist_ok=True)
        args.write_report_json.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    print(f"runtime-policy: {report['runtime_policy']}")
    print(f"output: {report['output_path']}")
    print(f"manual-proof-valid: {report['manual_proof_valid']}")
    print(f"passing-ids: {report['passing_ids']}")
    if report["failures"]:
        print("failures:")
        for failure in report["failures"]:
            print(f"  - {failure}")

    if args.require_valid and not report["passed"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
