#!/usr/bin/env python3
"""Validate explicit CDB-only promotion override manifests.

This validator is repo-only. It records whether an override manifest is absent
(the current safe state), or validates a supplied manifest before promotion
decision helpers may use CDB-only evidence in place of manual DirectInput proof.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_JSON = Path("captures/current/promotion-override-manifest-current.json")
DEFAULT_MD = Path("captures/current/promotion-override-manifest-current.md")
RUNTIME_POLICY = "repo-only manifest validation; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows"
SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")
PLACEHOLDER_RE = re.compile(r"replace_|placeholder|todo", re.IGNORECASE)
APPROVAL_RE = re.compile(r"user\s+explicitly\s+approv|explicit\s+user\s+approval", re.IGNORECASE)
REQUIRED_FIELD_GROUPS = {
    "evidence_class": ("evidence_class", "manifest_type"),
    "approved_cdb_only_promotion": ("approved_cdb_only_promotion", "explicit_user_approval"),
    "manual_bypass_reason": ("manual_bypass_reason", "manual_directinput_bypass_reason"),
    "no_stale_processes": ("no_stale_processes", "no_stale_process_result"),
}


def status_text(passed: bool) -> str:
    return "PASS" if passed else "FAIL"


def real_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip()) and not PLACEHOLDER_RE.search(value)


def load_json(path: Path) -> tuple[Any, list[str]]:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig")), []
    except FileNotFoundError:
        return None, [f"override manifest is missing: {path}"]
    except json.JSONDecodeError as exc:
        return None, [f"override manifest is not valid JSON: {exc}"]
    except OSError as exc:
        return None, [f"could not read override manifest {path}: {exc}"]


def target_scope_matches(value: Any, target_scope: str | None) -> bool:
    if target_scope is None:
        return True
    if isinstance(value, str):
        scopes = {value}
    elif isinstance(value, list):
        scopes = {item for item in value if isinstance(item, str)}
        scopes.add("all") if "all" in scopes else None
    else:
        return False
    return target_scope in scopes or "all" in scopes


def validate_manifest_data(
    manifest: Any,
    *,
    target_scope: str | None = None,
    candidate_stage: str | None = None,
    candidate_sha256: str | None = None,
) -> list[str]:
    failures: list[str] = []
    if not isinstance(manifest, dict):
        return ["override manifest must be a JSON object"]
    for logical, aliases in REQUIRED_FIELD_GROUPS.items():
        if not any(alias in manifest for alias in aliases):
            failures.append(f"override manifest missing required field: {logical}")
    for field in ["approval_record", "target_scope", "candidate_stage", "candidate_sha256", "accepted_risk", "evidence_refs"]:
        if field not in manifest:
            failures.append(f"override manifest missing required field: {field}")

    evidence_class = manifest.get("evidence_class")
    manifest_type = manifest.get("manifest_type")
    if evidence_class != "cdb_only_promotion_override" and manifest_type != "promotion_override":
        failures.append("override manifest evidence_class must be cdb_only_promotion_override")
    approved = manifest.get("approved_cdb_only_promotion") is True or manifest.get("explicit_user_approval") is True
    if not approved:
        failures.append("override manifest must record approved_cdb_only_promotion=true")
    bypass_reason = manifest.get("manual_bypass_reason", manifest.get("manual_directinput_bypass_reason"))
    approval_record = manifest.get("approval_record")
    for field, value in [
        ("approval_record", approval_record),
        ("accepted_risk", manifest.get("accepted_risk")),
        ("manual_bypass_reason", bypass_reason),
    ]:
        if not real_text(value):
            failures.append(f"override manifest must include a non-placeholder {field}")
    if real_text(bypass_reason):
        lower_reason = str(bypass_reason).lower()
        if "manual" not in lower_reason or "directinput" not in lower_reason:
            failures.append("override manifest manual_bypass_reason must explain bypassing manual DirectInput proof")
    if real_text(approval_record) and not APPROVAL_RE.search(str(approval_record)):
        failures.append("override manifest approval_record must document explicit user approval")
    if not target_scope_matches(manifest.get("target_scope"), target_scope):
        failures.append(f"override manifest target_scope does not include {target_scope}")
    stage = manifest.get("candidate_stage")
    if not real_text(stage):
        failures.append("override manifest must include a non-placeholder candidate_stage")
    elif candidate_stage and stage != candidate_stage:
        failures.append(f"override manifest candidate_stage is {stage}, expected {candidate_stage}")
    sha = manifest.get("candidate_sha256")
    if not isinstance(sha, str) or not SHA256_RE.match(sha):
        failures.append("override manifest must include a 64-hex candidate_sha256")
    elif candidate_sha256 and sha.lower() != candidate_sha256.lower():
        failures.append("override manifest candidate_sha256 does not match the evidence candidate")
    evidence_refs = manifest.get("evidence_refs")
    if not isinstance(evidence_refs, list) or not evidence_refs:
        failures.append("override manifest must include a nonempty evidence_refs list")
    elif any(not real_text(item) for item in evidence_refs):
        failures.append("override manifest evidence_refs must be non-placeholder strings")
    no_stale_process_result = manifest.get("no_stale_process_result")
    no_stale_result_ok = False
    if isinstance(no_stale_process_result, dict) and no_stale_process_result.get("passed") is True:
        try:
            no_stale_result_ok = int(no_stale_process_result.get("matching_process_count") or 0) == 0
        except (TypeError, ValueError):
            no_stale_result_ok = False
    no_stale_ok = manifest.get("no_stale_processes") is True or no_stale_result_ok
    if not no_stale_ok:
        failures.append("override manifest must record no_stale_processes=true")
    return failures


def validate_manifest(
    path: Path | None,
    *,
    target_scope: str | None = None,
    candidate_stage: str | None = None,
    candidate_sha256: str | None = None,
    expected_target_scope: str | None = None,
    expected_candidate_stage: str | None = None,
    expected_candidate_sha256: str | None = None,
) -> dict[str, Any]:
    if target_scope is None:
        target_scope = expected_target_scope
    if candidate_stage is None:
        candidate_stage = expected_candidate_stage
    if candidate_sha256 is None:
        candidate_sha256 = expected_candidate_sha256
    if path is None:
        return {
            "path": None,
            "supplied": False,
            "valid": False,
            "summary": {
                "target_scope": None,
                "candidate_stage": None,
                "candidate_sha256": None,
                "evidence_ref_count": 0,
            },
            "failures": [],
        }
    manifest, load_failures = load_json(path)
    failures = list(load_failures)
    if not failures:
        failures.extend(
            validate_manifest_data(
                manifest,
                target_scope=target_scope,
                candidate_stage=candidate_stage,
                candidate_sha256=candidate_sha256,
            )
        )
    return {
        "path": str(path),
        "supplied": True,
        "valid": not failures,
        "summary": {
            "target_scope": manifest.get("target_scope") if isinstance(manifest, dict) else None,
            "candidate_stage": manifest.get("candidate_stage") if isinstance(manifest, dict) else None,
            "candidate_sha256": manifest.get("candidate_sha256") if isinstance(manifest, dict) else None,
            "evidence_ref_count": len(manifest.get("evidence_refs", [])) if isinstance(manifest, dict) else 0,
            "no_stale_processes": (
                manifest.get("no_stale_processes")
                if isinstance(manifest, dict) and "no_stale_processes" in manifest
                else (
                    manifest.get("no_stale_process_result", {}).get("passed")
                    if isinstance(manifest, dict) and isinstance(manifest.get("no_stale_process_result"), dict)
                    else None
                )
            ),
        },
        "failures": failures,
    }


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    validation = validate_manifest(
        args.manifest,
        target_scope=args.target_scope,
        candidate_stage=args.candidate_stage,
        candidate_sha256=args.candidate_sha256,
    )
    # No manifest is the safe current state; supplied invalid manifests fail.
    failures = validation["failures"] if validation["supplied"] else []
    return {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "passed": not failures,
        "runtime_policy": RUNTIME_POLICY,
        "guard_policy": "CDB-only promotion requires an explicit valid override manifest; absence of a manifest keeps current evidence override-inactive",
        "override_active": bool(validation["valid"]),
        "override_manifest": validation,
        "failures": failures,
    }


def print_report(report: dict[str, Any]) -> None:
    print(f"overall: {status_text(bool(report['passed']))}")
    print(f"runtime-policy: {report['runtime_policy']}")
    print(f"override-active: {report['override_active']}")
    if report["failures"]:
        print("failures:")
        for failure in report["failures"]:
            print(f"  - {failure}")


def write_markdown(path: Path, report: dict[str, Any]) -> None:
    manifest = report["override_manifest"]
    lines = [
        "# Promotion Override Manifest",
        "",
        f"- Overall: {status_text(bool(report['passed']))}",
        f"- Generated: `{report['generated_at']}`",
        f"- Runtime policy: {report['runtime_policy']}",
        f"- Guard policy: {report['guard_policy']}",
        f"- Override active: `{report['override_active']}`",
        f"- Manifest path: `{manifest['path']}`",
        f"- Manifest supplied: `{manifest['supplied']}`",
        f"- Manifest valid: `{manifest['valid']}`",
        f"- Target scope: `{manifest['summary'].get('target_scope')}`",
        f"- Candidate stage: `{manifest['summary'].get('candidate_stage')}`",
        f"- Candidate SHA-256: `{manifest['summary'].get('candidate_sha256')}`",
        f"- Evidence refs: `{manifest['summary'].get('evidence_ref_count')}`",
    ]
    if report["failures"]:
        lines.extend(["", "## Failures", ""])
        lines.extend(f"- {failure}" for failure in report["failures"])
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--target-scope")
    parser.add_argument("--candidate-stage")
    parser.add_argument("--candidate-sha256")
    parser.add_argument("--write-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--write-markdown", type=Path, default=DEFAULT_MD)
    parser.add_argument("--require-pass", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = build_report(args)
    print_report(report)
    if args.write_json:
        args.write_json.parent.mkdir(parents=True, exist_ok=True)
        args.write_json.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if args.write_markdown:
        write_markdown(args.write_markdown, report)
    if args.require_pass and not report["passed"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
