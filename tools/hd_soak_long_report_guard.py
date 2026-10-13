#!/usr/bin/env python3
"""Validate long HD soak readiness from compact soak-report guards.

This is repo-only. It does not launch Clash95, CDB, wrappers, PowerShell
harnesses, or visible windows. It keeps 2h+ representative-route soak evidence
locked until the short ladder passes and future long-run guard reports exist.

Hidden producers must write their complete source JSON before using the public
environment dispatcher. Its source_report_sha256 binds those exact bytes;
patch_evidence also binds the exact external patch-manifest bytes. Acceptance
regrades both current files and compares source identity and all check records,
instead of treating a saved compact pass flag as enduring proof.
"""

from __future__ import annotations

import argparse
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hd_soak_short_tier_ladder import SHORT_LADDER_STEPS
import hd_soak_report
import hd_soak_short_step_status


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
HIDDEN_ENVIRONMENT = "hidden_cdb_host"
HIDDEN_EVIDENCE_CLASS = "approved_hidden_cdb_host_soak"
HIDDEN_REQUIRED_CHECKS = (
    "schema", "environment", "wrapper_provenance", "marker_provenance",
    "cleanup_provenance", "forced_entry_disclosure", "elapsed_coverage",
    "retained_binary_bytes", "retained_frame_bytes", "retained_log_bytes",
)


def status_text(passed: bool) -> str:
    return "PASS" if passed else "FAIL"


def load_json(path: Path) -> tuple[Any, list[str]]:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig")), []
    except FileNotFoundError:
        return None, []
    except (json.JSONDecodeError, UnicodeError) as exc:
        return None, [f"invalid JSON: {path}: {exc}"]
    except OSError as exc:
        return None, [f"could not read {path}: {exc}"]
    except ValueError as exc:
        return None, [f"could not read {path}: {type(exc).__name__}: {exc}"]


def resolve_ref(path_text: str, *, base: Path = Path(".")) -> Path:
    path = Path(path_text)
    if path.is_absolute():
        return path
    return base / path


def short_ladder_complete(short_step_status: Any) -> bool:
    if not isinstance(short_step_status, dict):
        return False
    steps = short_step_status.get("steps")
    if not isinstance(steps, list) or not all(isinstance(step, dict) for step in steps):
        return False
    recorded_complete = (
        short_step_status.get("passed") is True
        and short_step_status.get("ladder_complete") is True
        and [step.get("id") for step in steps] == [step["id"] for step in SHORT_LADDER_STEPS]
        and all(step.get("passed") is True for step in steps)
    )
    if not recorded_complete:
        return False
    # Saved pass flags are not enduring authority: their exact source and
    # external patch evidence must still pass the environment-aware grader.
    for saved, canonical in zip(steps, SHORT_LADDER_STEPS):
        try:
            _, passed, _, _ = hd_soak_short_step_status.step_status(
                {**saved, **canonical}, prerequisites_passed=True, legacy_report=None,
            )
        except (OSError, ValueError, TypeError, AttributeError, KeyError, OverflowError):
            # Malformed private JSON, inaccessible paths and stale provenance
            # cannot turn a saved complete flag into current ladder authority.
            # Leave the original files untouched and keep long tiers locked.
            return False
        if not passed:
            return False
    return True


def report_check_passed(report: dict[str, Any], check_name: str) -> bool:
    checks = report.get("checks")
    check = checks.get(check_name) if isinstance(checks, dict) else None
    return isinstance(check, dict) and check.get("passed") is True and not check.get("failures")


def check_summary(report: dict[str, Any], check_name: str) -> dict[str, Any]:
    checks = report.get("checks")
    check = checks.get(check_name) if isinstance(checks, dict) else None
    summary = check.get("summary") if isinstance(check, dict) else None
    return summary if isinstance(summary, dict) else {}


def finite_number(value: Any) -> bool:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return False
    try:
        return math.isfinite(value)
    except (OverflowError, ValueError):
        return False


def candidate_sha_from_report(report: dict[str, Any]) -> str:
    top_level = str(report.get("candidate_sha256") or "").strip()
    if top_level:
        return top_level
    patch_summary = check_summary(report, "patch_evidence")
    return str(patch_summary.get("candidate_sha256") or "").strip()


def revalidate_hidden_source(report: dict[str, Any]) -> list[str]:
    """Regrade the exact full report; a saved compact pass is not authority."""
    source_ref = report.get("source_report")
    if not isinstance(source_ref, str) or not source_ref.strip():
        return ["hidden long guard has no exact source_report reference"]
    source_path = resolve_ref(source_ref)
    source, read_failures = load_json(source_path)
    failures = [f"hidden source_report: {failure}" for failure in read_failures]
    if not isinstance(source, dict):
        return failures + [f"hidden source_report is missing or is not an object: {source_path}"]
    if hd_soak_report.normalized_path_text(source.get("report_json")) != hd_soak_report.normalized_path_text(source_ref):
        failures.append("hidden source_report identity does not match its report_json reference")
    if source.get("route") == "map-pan":
        pan_interval = source.get("pan_interval_sec")
        detail = source.get("pan_mechanism_detail")
        if pan_interval is None and isinstance(detail, dict):
            pan_interval = detail.get("pan_interval_sec")
        if pan_interval != 10:
            failures.append("hidden source_report requires canonical pan_interval_sec=10 for map-pan")
    try:
        fresh = hd_soak_report.evaluate_report_for_environment(source)
    except (OSError, ValueError, TypeError, AttributeError, KeyError, OverflowError) as exc:
        return failures + [f"hidden source_report revalidation raised {type(exc).__name__}: {exc}"]
    if fresh.get("overall") is not True:
        failures.extend(
            f"hidden source_report revalidation: {failure}"
            for failure in (fresh.get("failures") or ["environment-aware grader did not pass"])
        )
    recorded_digest = report.get("source_report_sha256")
    if (not isinstance(recorded_digest, str) or not SHA256_RE.fullmatch(recorded_digest)
            or fresh.get("source_report_sha256") != recorded_digest):
        failures.append("hidden source_report exact byte SHA-256 is missing or changed")
    if report.get("source_report_binding_errors"):
        failures.append("hidden source_report compact guard retained binding errors")
    if fresh.get("source_report_binding_errors"):
        failures.extend(f"hidden source_report binding: {error}" for error in fresh["source_report_binding_errors"])
    patch_digest = check_summary(fresh, "patch_evidence").get("patch_stage_report_sha256")
    if not isinstance(patch_digest, str) or not SHA256_RE.fullmatch(patch_digest):
        failures.append("hidden source_report has no exact patch_stage_report byte SHA-256")
    if patch_digest != check_summary(report, "patch_evidence").get("patch_stage_report_sha256"):
        failures.append("hidden patch_stage_report exact byte SHA-256 is missing or changed")
    for field in (
        "environment", "evidence_class", "stage", "tier", "route", "duration_sec",
        "sample_interval_sec", "candidate_sha256", "input_responsiveness", "entry_mechanism", "pan_mechanism",
    ):
        if report.get(field) != fresh.get(field):
            failures.append(f"hidden source_report {field} no longer matches the compact guard")
    if report.get("checks") != fresh.get("checks"):
        failures.append("hidden source_report checks no longer match the compact guard")
    return failures


def validate_long_report(report: Any, *, path: Path | None = None) -> tuple[bool, list[str], dict[str, Any]]:
    failures: list[str] = []
    if not isinstance(report, dict):
        return False, ["long soak report guard must be a JSON object"], {}

    route = str(report.get("route") or "")
    duration_value = report.get("duration_sec")
    if not finite_number(duration_value):
        duration_sec = 0
        failures.append("long soak duration_sec must be a finite number")
    else:
        duration_sec = duration_value
    stage = str(report.get("stage") or "")
    candidate_sha256 = candidate_sha_from_report(report)
    overall = report.get("overall", report.get("passed")) is True
    if "overall" in report and "passed" in report and report["overall"] != report["passed"]:
        failures.append("long soak report guard has conflicting overall/passed status")
    if report.get("failures"):
        failures.append("long soak report guard still records failures")
    # Hidden host endurance keeps its provenance and non-input contract all
    # the way into release evidence. Guest diagnostics do not supply the host
    # process checks required by this ladder.
    environment = report.get("environment", "host_visible")
    evidence_class = report.get("evidence_class")
    if not isinstance(environment, str) or environment not in {"host_visible", HIDDEN_ENVIRONMENT}:
        failures.append(f"unsupported long-soak host environment: {environment!r}")
    elif environment == "host_visible":
        if evidence_class not in (None, "host_visible_runtime_soak"):
            failures.append("visible-host long soak has a mismatched evidence_class")
        # Historical visible reports can omit environment metadata entirely,
        # but explicit foreign receipts cannot be erased by changing only the
        # top-level labels. Keep hidden/guest proofs out of this legacy path.
        environment_receipt = check_summary(report, "environment")
        source_ref = report.get("source_report")
        source = None
        if isinstance(source_ref, str) and source_ref.strip():
            source, source_read_failures = load_json(resolve_ref(source_ref))
            failures.extend(f"visible source_report: {error}" for error in source_read_failures)
        source_is_foreign = isinstance(source, dict) and (
            source.get("environment") in (HIDDEN_ENVIRONMENT, hd_soak_report.GUEST_ENVIRONMENT)
            or source.get("schema") == "hidden_cdb_host_soak_report_v1"
            or source.get("input_responsiveness") in ("not_applicable_hidden", "not_applicable_guest")
        )
        if (report.get("expected_environment") not in (None, "host_visible")
                or report.get("expected_evidence_class") not in (None, hd_soak_report.HOST_EVIDENCE_CLASS)
                or environment_receipt.get("environment") not in (None, "host_visible")
                or environment_receipt.get("expected_environment") not in (None, "host_visible")
                or environment_receipt.get("evidence_class") not in (None, hd_soak_report.HOST_EVIDENCE_CLASS)
                or environment_receipt.get("expected_evidence_class") not in (None, hd_soak_report.HOST_EVIDENCE_CLASS)
                or check_summary(report, "schema").get("schema") == "hidden_cdb_host_soak_report_v1"
                or report.get("schema") == "hidden_cdb_host_soak_report_v1"
                or report.get("input_responsiveness") in ("not_applicable_hidden", "not_applicable_guest")
                or check_summary(report, "input_responsiveness").get("required_sentinel")
                   in ("not_applicable_hidden", "not_applicable_guest") or source_is_foreign):
            failures.append("visible-host long soak carries explicit foreign proof-class/source/sentinel summaries")
    else:
        if evidence_class != HIDDEN_EVIDENCE_CLASS:
            failures.append("hidden long soak has a mismatched evidence_class")
        if report.get("input_responsiveness") != "not_applicable_hidden":
            failures.append("hidden long soak must disclose input_responsiveness=not_applicable_hidden")
        mechanisms = {
            "entry_mechanism": hd_soak_report.HIDDEN_ENTRY_MECHANISM,
            "pan_mechanism": (hd_soak_report.HIDDEN_PAN_MECHANISM if route == "map-pan"
                              else hd_soak_report.HIDDEN_NO_PAN_MECHANISM),
        }
        for field, expected in mechanisms.items():
            if report.get(field) != expected:
                failures.append(f"hidden long soak {field} must be {expected!r}")
        for check_name in HIDDEN_REQUIRED_CHECKS:
            if not report_check_passed(report, check_name):
                failures.append(f"required hidden soak guard check is not passing: {check_name}")
        environment_summary = check_summary(report, "environment")
        if (environment_summary.get("environment") != environment
                or environment_summary.get("evidence_class") != evidence_class):
            failures.append("hidden environment check summary does not match report identity")
        disclosure = check_summary(report, "forced_entry_disclosure")
        if disclosure.get("route") != route or any(
            disclosure.get(field) != expected for field, expected in mechanisms.items()
        ):
            failures.append("hidden forced_entry_disclosure summary does not match route/mechanisms")
        sentinel = check_summary(report, "input_responsiveness")
        if (sentinel.get("present") is not True
                or sentinel.get("input_responsiveness") != "not_applicable_hidden"
                or sentinel.get("required_sentinel") != "not_applicable_hidden"):
            failures.append("hidden input_responsiveness check summary does not bind the required sentinel")
        coverage = check_summary(report, "elapsed_coverage")
        interval = report.get("sample_interval_sec")
        if interval != 30 or isinstance(interval, bool):
            failures.append("hidden long soak requires canonical sample_interval_sec=30")
        if (not finite_number(interval) or interval <= 0
                or coverage.get("duration_sec") != duration_sec
                or coverage.get("sample_interval_sec") != interval):
            failures.append("hidden elapsed_coverage summary does not match duration/sample interval")
        elif finite_number(duration_sec):
            required_elapsed = max(0.0, duration_sec - interval - 2)
            if (coverage.get("required_elapsed_sec") != required_elapsed
                    or any(not finite_number(coverage.get(field)) or coverage[field] < required_elapsed
                           for field in ("frame_elapsed_sec", "process_elapsed_sec"))):
                failures.append("hidden elapsed_coverage does not cover the shared duration - interval - 2 bound")
        proxy = check_summary(report, "wrapper_provenance")
        if (proxy.get("used") is not True or not SHA256_RE.fullmatch(str(proxy.get("sha256") or ""))
                or not hd_soak_report.presentation_is_disabled(proxy.get("present_enabled"))
                or any(not isinstance(proxy.get(field), str) or not proxy[field].strip()
                       for field in ("path", "build_manifest", "log"))):
            failures.append("hidden wrapper_provenance summary does not bind a non-presenting proxy")
        if check_summary(report, "schema").get("schema") != "hidden_cdb_host_soak_report_v1":
            failures.append("hidden schema summary does not identify the hidden report protocol")
        markers = check_summary(report, "marker_provenance")
        expected_pan = int(route == "map-pan")
        if not all(
            isinstance(markers.get(field), dict)
            and markers[field].get("route_ticks") == duration_sec * 64
            and markers[field].get("pan") == expected_pan
            for field in ("route_start_marker", "route_end_marker")
        ):
            failures.append("hidden marker_provenance summary does not bind duration and route pan flag")
        start_marker = markers.get("route_start_marker")
        end_marker = markers.get("route_end_marker")
        if isinstance(start_marker, dict) and isinstance(end_marker, dict):
            tick_delta = end_marker.get("tick_delta")
            hits = end_marker.get("hits")
            if (not finite_number(tick_delta) or tick_delta < duration_sec * 64
                    or type(hits) is not int or hits <= 0
                    or type(end_marker.get("player")) is not int
                    or end_marker.get("player") != start_marker.get("player")):
                failures.append("hidden marker_provenance summary lacks complete terminal ticks/hits/player continuity")
        cleanup = check_summary(report, "cleanup_provenance")
        if (cleanup.get("game_stopped") is not True or cleanup.get("cdb_stopped") is not True
                or cleanup.get("errors") != []):
            failures.append("hidden cleanup_provenance summary does not verify both stopped processes")
        failures.extend(revalidate_hidden_source(report))

    patch_candidate = str(check_summary(report, "patch_evidence").get("candidate_sha256") or "").strip()
    if (not SHA256_RE.fullmatch(patch_candidate)
            or patch_candidate.lower() != candidate_sha256.lower()):
        failures.append("candidate_sha256 does not match patch_evidence summary")

    if not overall:
        failures.append("long soak report guard is not passing")
    if stage != PROTECTED_STABLE_STAGE:
        failures.append("long soak report guard stage is not the protected stable stage")
    if route not in REQUIRED_ROUTES:
        failures.append(f"long soak route {route!r} is not in required routes {REQUIRED_ROUTES}")
    if not MIN_DURATION_SEC <= duration_sec < float("inf"):
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
        "environment": environment,
        "evidence_class": evidence_class,
        "input_responsiveness": report.get("input_responsiveness"),
        "entry_mechanism": report.get("entry_mechanism"),
        "pan_mechanism": report.get("pan_mechanism"),
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
            lines.append(
                f"- `{route}`: environment=`{record.get('environment') or 'host_visible'}` "
                f"duration=`{record['duration_sec']}` path=`{record['path']}`"
            )
            if record.get("environment") == HIDDEN_ENVIRONMENT:
                lines.append(
                    f"  - Evidence class: `{record.get('evidence_class')}`; "
                    f"input responsiveness: `{record.get('input_responsiveness')}`."
                )
                lines.append(f"  - Entry mechanism: {record.get('entry_mechanism')}")
                if route == "map-pan":
                    lines.append(f"  - Pan mechanism: {record.get('pan_mechanism')}")
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
