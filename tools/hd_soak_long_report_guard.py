#!/usr/bin/env python3
"""Validate long HD soak readiness from compact soak-report guards.

This is repo-only. It does not launch Clash95, CDB, wrappers, PowerShell
harnesses, or visible windows. It keeps 2h+ representative-route soak evidence
locked until the short ladder passes and future long-run guard reports exist.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROTECTED_STABLE_STAGE = (
    "gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-"
    "minimapright-dynvswitch"
)
RUNTIME_POLICY = (
    "repo-only long-soak report guard; does not launch Clash95, CDB, wrappers, "
    "PowerShell harnesses, or visible windows"
)
GUARD_POLICY = (
    "2h+ representative-route soak evidence remains locked until the short "
    "ladder passes and approved opt-in long-run soak report guards prove clean "
    "process, frame, input, artifact, and patch evidence"
)
DEFAULT_JSON = Path("captures/current/hd-soak-long-report-guard-current.json")
DEFAULT_MD = Path("captures/current/hd-soak-long-report-guard-current.md")
DEFAULT_SHORT_STEP_STATUS_JSON = Path("captures/current/hd-soak-short-step-status-current.json")
DEFAULT_PROOF_JSON = Path("captures/current/hd-soak-long-proof-current.json")
REQUIRED_ROUTES = ["map-idle", "map-pan"]
MIN_DURATION_SEC = 7200
SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")


def status_text(passed: bool) -> str:
    return "PASS" if passed else "FAIL"


def load_json(path: Path) -> tuple[Any, list[str]]:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig")), []
    except FileNotFoundError:
        return None, []
    except json.JSONDecodeError as exc:
        return None, [f"invalid JSON: {path}: {exc}"]
    except OSError as exc:
        return None, [f"could not read {path}: {exc}"]


def resolve_ref(path_text: str, *, base: Path = Path(".")) -> Path:
    path = Path(path_text)
    if path.is_absolute():
        return path
    return base / path


def short_ladder_complete(short_step_status: Any) -> bool:
    if not isinstance(short_step_status, dict):
        return False
    return (
        short_step_status.get("passed") is True
        and short_step_status.get("ladder_complete") is True
        and all(step.get("passed") is True for step in (short_step_status.get("steps") or []))
    )


def report_check_passed(report: dict[str, Any], check_name: str) -> bool:
    check = (report.get("checks") or {}).get(check_name)
    return isinstance(check, dict) and check.get("passed") is True


def candidate_sha_from_report(report: dict[str, Any]) -> str:
    top_level = str(report.get("candidate_sha256") or "").strip()
    if top_level:
        return top_level
    patch_summary = ((report.get("checks") or {}).get("patch_evidence") or {}).get("summary") or {}
    return str(patch_summary.get("candidate_sha256") or "").strip()


def validate_long_report(report: Any, *, path: Path | None = None) -> tuple[bool, list[str], dict[str, Any]]:
    failures: list[str] = []
    if not isinstance(report, dict):
        return False, ["long soak report guard must be a JSON object"], {}

    route = str(report.get("route") or "")
    duration_sec = int(report.get("duration_sec") or 0)
    stage = str(report.get("stage") or "")
    candidate_sha256 = candidate_sha_from_report(report)
    overall = report.get("overall") is True or report.get("passed") is True

    if not overall:
        failures.append("long soak report guard is not passing")
    if stage != PROTECTED_STABLE_STAGE:
        failures.append("long soak report guard stage is not the protected stable stage")
    if route not in REQUIRED_ROUTES:
        failures.append(f"long soak route {route!r} is not in required routes {REQUIRED_ROUTES}")
    if duration_sec < MIN_DURATION_SEC:
        failures.append(f"long soak duration_sec {duration_sec} is below {MIN_DURATION_SEC}")
    if not SHA256_RE.match(candidate_sha256):
        failures.append("candidate_sha256 is not a 64-hex digest")

    for check_name in [
        "executed",
        "source_status",
        "protected_stage",
        "tier_route",
        "patch_evidence",
        "promotion_boundary",
        "artifact_locations",
        "capture_integrity",
        "frame_inventory",
        "render_metrics",
        "process_liveness",
        "process_growth",
        "input_responsiveness",
        "summary_consistency",
        "artifact_budget",
    ]:
        if not report_check_passed(report, check_name):
            failures.append(f"required soak guard check is not passing: {check_name}")

    if route == "map-pan" and not report_check_passed(report, "frame_progression"):
        failures.append("map-pan long soak must pass frame_progression")

    summary = {
        "path": str(path) if path else None,
        "route": route,
        "duration_sec": duration_sec,
        "stage": stage,
        "candidate_sha256": candidate_sha256 or None,
        "overall": overall,
    }
    return not failures, failures, summary


def proof_report_paths(proof_data: Any) -> list[str]:
    if not isinstance(proof_data, dict):
        return []
    paths = proof_data.get("report_guards")
    if isinstance(paths, list):
        return [str(path) for path in paths if isinstance(path, str) and path.strip()]
    return []


def build_report(
    *,
    short_step_status_json: Path = DEFAULT_SHORT_STEP_STATUS_JSON,
    proof_json: Path = DEFAULT_PROOF_JSON,
) -> dict[str, Any]:
    short_status, short_failures = load_json(short_step_status_json)
    proof_data, proof_failures = load_json(proof_json)
    failures: list[str] = []
    failures.extend(f"short ladder: {failure}" for failure in short_failures)
    failures.extend(f"proof manifest: {failure}" for failure in proof_failures)

    ladder_complete = short_ladder_complete(short_status)
    if not ladder_complete:
        failures.append("short ladder is not complete; long tiers remain locked")

    proof_present = proof_json.exists()
    report_refs = proof_report_paths(proof_data)
    if not proof_present:
        failures.append(f"long soak proof manifest is missing: {proof_json}")
    elif not report_refs:
        failures.append("long soak proof manifest has no report_guards list")

    route_records: dict[str, dict[str, Any]] = {}
    report_records: list[dict[str, Any]] = []
    for ref in report_refs:
        path = resolve_ref(ref)
        data, load_failures = load_json(path)
        if load_failures:
            failures.extend(f"{ref}: {failure}" for failure in load_failures)
            report_records.append({"path": str(path), "valid": False, "failures": load_failures})
            continue
        valid, report_failures, summary = validate_long_report(data, path=path)
        if valid:
            route_records[str(summary["route"])] = summary
        else:
            failures.extend(f"{ref}: {failure}" for failure in report_failures)
        report_records.append({"path": str(path), "valid": valid, "summary": summary, "failures": report_failures})

    missing_routes = [route for route in REQUIRED_ROUTES if route not in route_records]
    for route in missing_routes:
        failures.append(f"missing passing 2h+ representative route: {route}")

    candidate_shas = sorted(
        {str(record.get("candidate_sha256") or "").lower() for record in route_records.values() if record.get("candidate_sha256")}
    )
    if len(candidate_shas) > 1:
        failures.append(f"representative long-route reports use different candidate SHA-256s: {candidate_shas}")

    overall = not failures
    min_duration = min((record["duration_sec"] for record in route_records.values()), default=0)
    return {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "passed": overall,
        "overall": overall,
        "runtime_policy": RUNTIME_POLICY,
        "guard_policy": GUARD_POLICY,
        "protected_stable_stage": PROTECTED_STABLE_STAGE,
        "status": "pass" if overall else ("locked_short_ladder_incomplete" if not ladder_complete else "blocked_missing_long_proof"),
        "tier": "long2h",
        "route": "representative-routes",
        "duration_sec": min_duration,
        "minimum_duration_sec": MIN_DURATION_SEC,
        "required_routes": REQUIRED_ROUTES,
        "short_ladder": {
            "path": str(short_step_status_json),
            "present": short_status is not None,
            "ladder_complete": ladder_complete,
            "current_step": (short_status or {}).get("current_step") if isinstance(short_status, dict) else None,
        },
        "proof_manifest": {
            "path": str(proof_json),
            "present": proof_present,
            "report_guard_count": len(report_refs),
        },
        "route_records": route_records,
        "report_records": report_records,
        "counts": {
            "required_routes": len(REQUIRED_ROUTES),
            "passing_routes": len(route_records),
            "missing_routes": len(missing_routes),
        },
        "summary": (
            "2h+ representative-route soak evidence passes"
            if overall
            else "2h+ representative-route soak evidence is locked or missing"
        ),
        "next_probe": (
            "complete the short-tier ladder first"
            if not ladder_complete
            else "run approved opt-in 2h+ map-idle and map-pan soak reports"
        ),
        "failures": failures,
    }


def to_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# HD Long Soak Report Guard",
        "",
        f"- Overall: {status_text(bool(report['overall']))}",
        f"- Generated: `{report['generated_at']}`",
        f"- Runtime policy: {report['runtime_policy']}",
        f"- Guard policy: {report['guard_policy']}",
        f"- Status: `{report['status']}`",
        f"- Required routes: `{', '.join(report['required_routes'])}`",
        f"- Passing routes: `{report['counts']['passing_routes']}/{report['counts']['required_routes']}`",
        f"- Minimum duration seconds: `{report['minimum_duration_sec']}`",
        f"- Short ladder complete: `{report['short_ladder']['ladder_complete']}`",
        f"- Proof manifest: `{report['proof_manifest']['path']}` present=`{report['proof_manifest']['present']}`",
        "",
        "## Route Records",
        "",
    ]
    if report["route_records"]:
        for route, record in report["route_records"].items():
            lines.append(f"- `{route}`: duration=`{record['duration_sec']}` path=`{record['path']}`")
    else:
        lines.append("- No passing long-route guard records.")
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
    parser.add_argument("--short-step-status-json", type=Path, default=DEFAULT_SHORT_STEP_STATUS_JSON)
    parser.add_argument("--proof-json", type=Path, default=DEFAULT_PROOF_JSON)
    parser.add_argument("--write-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--write-markdown", "--write-md", dest="write_markdown", type=Path, default=DEFAULT_MD)
    parser.add_argument("--require-pass", action="store_true")
    args = parser.parse_args()

    report = build_report(short_step_status_json=args.short_step_status_json, proof_json=args.proof_json)
    write_outputs(report, args.write_json, args.write_markdown)
    print(f"overall: {status_text(bool(report['overall']))}")
    print(f"runtime-policy: {report['runtime_policy']}")
    print(f"status: {report['status']}")
    print(f"passing-routes: {report['counts']['passing_routes']}/{report['counts']['required_routes']}")
    if report["failures"]:
        print("failures:")
        for failure in report["failures"]:
            print(f"  - {failure}")
    if args.require_pass and not report["overall"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
