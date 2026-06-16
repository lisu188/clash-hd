#!/usr/bin/env python3
"""Validate compact HD state-continuity evidence.

This guard is repo-only. It does not launch Clash95, CDB, wrappers,
PowerShell harnesses, or visible windows. It defines the compact evidence
schema needed before save/load, turn advancement, or campaign-route continuity
can count toward the endurance release checklist.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_JSON = Path("captures/current/hd-continuity-current.json")
DEFAULT_MD = Path("captures/current/hd-continuity-current.md")
DEFAULT_PROOF_JSON = Path("captures/current/hd-continuity-proof-current.json")
RUNTIME_POLICY = (
    "repo-only continuity status; does not launch Clash95, CDB, wrappers, "
    "PowerShell harnesses, or visible windows"
)
GUARD_POLICY = (
    "save/load, turn, and campaign continuity remain blocked until a compact "
    "approved proof manifest documents an isolated test-save workflow, stable "
    "stage/candidate identity shared by every continuity lane, state hashes, "
    "route observations, and no live save mutation"
)
PROTECTED_STABLE_STAGE = (
    "gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-"
    "minimapright-dynvswitch"
)
SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")
PLACEHOLDER_RE = re.compile(r"replace_|placeholder|todo", re.IGNORECASE)
FORBIDDEN_REPO_SUFFIXES = {
    ".exe",
    ".dll",
    ".dmp",
    ".dump",
    ".iso",
    ".bin",
    ".sav",
    ".save",
    ".dat",
}
CHECK_DEFS: dict[str, dict[str, Any]] = {
    "save_load_roundtrip": {
        "title": "Safe save/load roundtrip continuity",
        "required_true": ["roundtrip_completed", "safe_test_save", "isolated_workdir"],
        "required_false": ["live_save_mutated", "state_desync_detected"],
        "required_sha": ["before_state_sha256", "after_state_sha256"],
        "minimum_duration_sec": 0,
        "next_probe": "run an approved isolated save/load roundtrip after short-tier stability",
    },
    "turn_advancement": {
        "title": "Turn advancement without state desync",
        "required_true": ["turn_advanced", "safe_test_save", "isolated_workdir"],
        "required_false": ["live_save_mutated", "state_desync_detected"],
        "required_sha": ["before_state_sha256", "after_state_sha256"],
        "minimum_duration_sec": 0,
        "next_probe": "run an approved deterministic turn-advance route after save/load is safe",
    },
    "campaign_routes": {
        "title": "Representative campaign route continuity",
        "required_true": ["route_completed", "safe_test_save", "isolated_workdir"],
        "required_false": ["live_save_mutated", "state_desync_detected", "palette_corruption_detected"],
        "required_sha": ["before_state_sha256", "after_state_sha256"],
        "minimum_duration_sec": 600,
        "next_probe": "run a representative campaign route after short and medium tiers are stable",
    },
}
ALLOWED_PROOF_CLASSES = {
    "approved_visible_runtime",
    "approved_manual_runtime",
    "approved_hidden_cdb_continuity",
}


def status_text(passed: bool) -> str:
    return "PASS" if passed else "FAIL"


def real_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip()) and not PLACEHOLDER_RE.search(value)


def load_json(path: Path) -> tuple[Any, list[str]]:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig")), []
    except FileNotFoundError:
        return None, []
    except json.JSONDecodeError as exc:
        return None, [f"continuity proof manifest is not valid JSON: {path}: {exc}"]
    except OSError as exc:
        return None, [f"could not read continuity proof manifest {path}: {exc}"]


def is_under(path: str, root: str) -> bool:
    normalized = path.replace("/", "\\").lower()
    root_norm = root.rstrip("\\/").replace("/", "\\").lower()
    return normalized == root_norm or normalized.startswith(root_norm + "\\")


def artifact_path_failures(artifacts: Any) -> list[str]:
    failures: list[str] = []
    if not isinstance(artifacts, list) or not artifacts:
        return ["proof must include nonempty evidence_refs"]
    for artifact in artifacts:
        if not real_text(artifact):
            failures.append("evidence_refs must contain non-placeholder strings")
            continue
        value = str(artifact)
        suffix = Path(value.replace("\\", "/")).suffix.lower()
        if is_under(value, "C:\\Clash\\save"):
            failures.append(f"evidence ref must not point at live C:\\Clash\\save: {value}")
        if value.lower().startswith("captures/") or value.lower().startswith("captures\\"):
            if suffix in FORBIDDEN_REPO_SUFFIXES:
                failures.append(f"repo evidence ref must not be a forbidden artifact: {value}")
    return failures


def validate_common_proof(check_id: str, proof: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    proof_class = proof.get("proof_class")
    if proof_class not in ALLOWED_PROOF_CLASSES:
        failures.append(f"{check_id}: proof_class must be one of {sorted(ALLOWED_PROOF_CLASSES)}")
    if proof.get("approved") is not True:
        failures.append(f"{check_id}: approved must be true")
    if proof.get("stage") != PROTECTED_STABLE_STAGE:
        failures.append(f"{check_id}: stage must be the protected stable stage")
    if not isinstance(proof.get("candidate_sha256"), str) or not SHA256_RE.match(str(proof.get("candidate_sha256"))):
        failures.append(f"{check_id}: candidate_sha256 must be a 64-hex digest")
    if not real_text(proof.get("approval_record")):
        failures.append(f"{check_id}: approval_record must be present and non-placeholder")
    if not real_text(proof.get("summary")):
        failures.append(f"{check_id}: summary must be present and non-placeholder")
    for field in ["route", "start_marker", "end_marker", "before_observation", "after_observation"]:
        if not real_text(proof.get(field)):
            failures.append(f"{check_id}: {field} must be present and non-placeholder")
    if real_text(proof.get("start_marker")) and proof.get("start_marker") == proof.get("end_marker"):
        failures.append(f"{check_id}: start_marker and end_marker must differ")
    route_markers = proof.get("route_markers")
    if not isinstance(route_markers, list) or not route_markers:
        failures.append(f"{check_id}: route_markers must be a nonempty list")
    else:
        for marker in route_markers:
            if not real_text(marker):
                failures.append(f"{check_id}: route_markers must contain non-placeholder strings")
                break
    failures.extend(f"{check_id}: {failure}" for failure in artifact_path_failures(proof.get("evidence_refs")))
    return failures


def validate_check_proof(check_id: str, proof: Any) -> tuple[bool, list[str], dict[str, Any]]:
    definition = CHECK_DEFS[check_id]
    if not isinstance(proof, dict):
        return False, [f"{check_id}: compact proof is missing"], {}

    failures = validate_common_proof(check_id, proof)
    for field in definition["required_true"]:
        if proof.get(field) is not True:
            failures.append(f"{check_id}: {field} must be true")
    for field in definition["required_false"]:
        if proof.get(field) is not False:
            failures.append(f"{check_id}: {field} must be false")
    for field in definition["required_sha"]:
        if not isinstance(proof.get(field), str) or not SHA256_RE.match(str(proof.get(field))):
            failures.append(f"{check_id}: {field} must be a 64-hex digest")
    try:
        duration_sec = int(proof.get("duration_sec") or 0)
    except (TypeError, ValueError):
        duration_sec = 0
    if duration_sec < int(definition["minimum_duration_sec"]):
        failures.append(
            f"{check_id}: duration_sec {duration_sec} is below {definition['minimum_duration_sec']}"
        )

    summary = {
        "proof_class": proof.get("proof_class"),
        "candidate_sha256": proof.get("candidate_sha256"),
        "duration_sec": duration_sec,
        "route": proof.get("route"),
        "start_marker": proof.get("start_marker"),
        "end_marker": proof.get("end_marker"),
        "route_marker_count": len(proof.get("route_markers") or []) if isinstance(proof.get("route_markers"), list) else 0,
        "before_observation": proof.get("before_observation"),
        "after_observation": proof.get("after_observation"),
        "evidence_ref_count": len(proof.get("evidence_refs") or []) if isinstance(proof.get("evidence_refs"), list) else 0,
        "summary": proof.get("summary"),
    }
    return not failures, failures, summary


def build_report(proof_json: Path | None = DEFAULT_PROOF_JSON) -> dict[str, Any]:
    proof_data: Any = None
    proof_load_failures: list[str] = []
    proof_manifest = {
        "path": str(proof_json) if proof_json else None,
        "present": False,
        "valid_json": False,
    }
    if proof_json:
        proof_data, proof_load_failures = load_json(proof_json)
        proof_manifest["present"] = proof_json.exists()
        proof_manifest["valid_json"] = proof_data is not None and not proof_load_failures

    proofs = proof_data.get("proofs") if isinstance(proof_data, dict) else {}
    if not isinstance(proofs, dict):
        proofs = {}

    checks: dict[str, dict[str, Any]] = {}
    failures: list[str] = list(proof_load_failures)
    for check_id, definition in CHECK_DEFS.items():
        proof = proofs.get(check_id)
        passed, check_failures, summary = validate_check_proof(check_id, proof)
        status = "pass" if passed else ("blocked_invalid_proof" if proof is not None else "blocked_missing_proof")
        checks[check_id] = {
            "id": check_id,
            "title": definition["title"],
            "passed": passed,
            "status": status,
            "summary": (
                "continuity proof passes"
                if passed
                else "continuity proof is missing or not sufficient for release"
            ),
            "next_probe": definition["next_probe"],
            "required_true": definition["required_true"],
            "required_false": definition["required_false"],
            "required_sha": definition["required_sha"],
            "minimum_duration_sec": definition["minimum_duration_sec"],
            "proof_summary": summary,
            "failures": check_failures,
        }
        failures.extend(check_failures)

    candidate_shas = sorted(
        {
            str((check.get("proof_summary") or {}).get("candidate_sha256") or "").lower()
            for check in checks.values()
            if check.get("passed") and (check.get("proof_summary") or {}).get("candidate_sha256")
        }
    )
    if len(candidate_shas) > 1:
        mismatch_failure = f"continuity proofs use different candidate SHA-256s: {candidate_shas}"
        failures.append(mismatch_failure)
        for check in checks.values():
            if check.get("passed"):
                check["passed"] = False
                check["status"] = "blocked_candidate_mismatch"
                check["summary"] = "continuity proof candidate does not match other continuity lanes"
                check.setdefault("failures", []).append(mismatch_failure)

    counts = {
        "total": len(checks),
        "passed": sum(1 for check in checks.values() if check["passed"]),
        "blocked": sum(1 for check in checks.values() if not check["passed"]),
    }
    return {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "passed": counts["passed"] == counts["total"],
        "runtime_policy": RUNTIME_POLICY,
        "guard_policy": GUARD_POLICY,
        "protected_stable_stage": PROTECTED_STABLE_STAGE,
        "proof_manifest": proof_manifest,
        "candidate_sha256s": candidate_shas,
        "checks": checks,
        "counts": counts,
        "failures": failures,
    }


def to_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# HD Continuity Status",
        "",
        f"- Overall: {status_text(bool(report['passed']))}",
        f"- Generated: `{report['generated_at']}`",
        f"- Runtime policy: {report['runtime_policy']}",
        f"- Guard policy: {report['guard_policy']}",
        f"- Proof manifest: `{report['proof_manifest']['path']}` present=`{report['proof_manifest']['present']}`",
        f"- Checks passed: `{report['counts']['passed']}/{report['counts']['total']}`",
        "",
        "## Checks",
        "",
    ]
    for check in report["checks"].values():
        lines.append(
            f"- `{check['id']}`: status=`{check['status']}` passed=`{check['passed']}` - {check['summary']}"
        )
    if report["failures"]:
        lines.extend(["", "## Failures", ""])
        lines.extend(f"- {failure}" for failure in report["failures"])
    lines.append("")
    return "\n".join(lines)


def write_outputs(report: dict[str, Any], json_path: Path | None, md_path: Path | None) -> None:
    if json_path:
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(report, indent=2) + "\n", encoding="ascii")
    if md_path:
        md_path.parent.mkdir(parents=True, exist_ok=True)
        md_path.write_text(to_markdown(report), encoding="ascii")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--proof-json", type=Path, default=DEFAULT_PROOF_JSON)
    parser.add_argument("--write-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--write-markdown", "--write-md", dest="write_markdown", type=Path, default=DEFAULT_MD)
    parser.add_argument("--require-pass", action="store_true")
    args = parser.parse_args()

    report = build_report(args.proof_json)
    write_outputs(report, args.write_json, args.write_markdown)
    print(f"overall: {status_text(bool(report['passed']))}")
    print(f"runtime-policy: {report['runtime_policy']}")
    print(f"checks: {report['counts']['passed']}/{report['counts']['total']} passed")
    if report["failures"]:
        print("failures:")
        for failure in report["failures"]:
            print(f"  - {failure}")
    if args.require_pass and not report["passed"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
