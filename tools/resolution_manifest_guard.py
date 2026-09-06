#!/usr/bin/env python3
"""Verify the launcher resolution status manifest stays consistent.

This is a repo-only metadata guard. It reads `src/launcher/resolutions.json`,
the patcher's stable-stage constant, and the evidence artifacts referenced by
stable/validated entries; it does not launch Clash95, CDB, wrappers,
PowerShell, or any visible GUI process.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

DEFAULT_MANIFEST = Path("src/launcher/resolutions.json")
DEFAULT_JSON = Path("captures/current/resolution-manifest-guard-current.json")
DEFAULT_MD = Path("captures/current/resolution-manifest-guard-current.md")
RUNTIME_POLICY = (
    "repo-only metadata inspection; does not launch Clash95, CDB, wrappers, "
    "PowerShell, or visible windows"
)
GUARD_POLICY = (
    "exactly one stable resolution (the 800x600 default), stable/validated "
    "entries backed by passing hidden-desktop evidence whose dimensions, stage, "
    "candidate SHA and run references agree with its passing patch metadata and "
    "smoke matrix, tile counts matching the engine formula"
)

RESOLUTION_KEY_RE = re.compile(r"^([1-9]\d{2,3})x([1-9]\d{2,3})$")
VALID_STATUSES = ("stable", "validated", "experimental")
EXPECTED_DEFAULT = "800x600"
TILE_SIZE = 64
TILE_ORIGIN_X = 32
TILE_ORIGIN_Y = 16


def status_text(passed: bool) -> str:
    return "PASS" if passed else "FAIL"


def check_record(name: str, passed: bool, summary: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "name": name,
        "passed": passed,
        "summary": summary or {},
        "failures": [] if passed else [name],
    }


def expected_tiles(width: int, height: int) -> tuple[int, int]:
    return (
        (width - TILE_ORIGIN_X) // TILE_SIZE,
        (height - TILE_ORIGIN_Y) // TILE_SIZE,
    )


def load_json(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError):
        return None
    return payload if isinstance(payload, dict) else None


def patcher_stable_stage() -> str | None:
    try:
        import patch_clash95_hd  # noqa: PLC0415

        return str(patch_clash95_hd.DEFAULT_STAGE)
    except Exception:  # pragma: no cover - import failure is a guard failure
        return None


def metadata_path(root: Path, value: str) -> Path:
    # Archived metadata uses Windows separators even in portable checkouts.
    return (root / value.replace("\\", "/")).resolve()


def candidate_sha(value: Any) -> str | None:
    return value.lower() if isinstance(value, str) and re.fullmatch(r"[0-9a-fA-F]{64}", value) else None


def surface_matches(surface: Any, width: int, height: int) -> bool:
    return isinstance(surface, dict) and all(
        type(surface.get(field)) is int and surface[field] == expected
        for field, expected in (("Width", width), ("Height", height), ("Bytes", width * height))
    )


def evidence_binding_failures(root: Path, key: str, evidence: dict[str, Any], stage: str | None) -> list[str]:
    failures: list[str] = []
    match = RESOLUTION_KEY_RE.fullmatch(key)
    if not match:
        return ["cannot bind evidence for an invalid resolution key"]
    width, height = int(match[1]), int(match[2])
    smoke_ref = evidence.get("smoke_json")
    smoke_path = metadata_path(root, smoke_ref) if isinstance(smoke_ref, str) and smoke_ref else None
    smoke = load_json(smoke_path) if smoke_path and smoke_path.suffix.lower() == ".json" else None
    if smoke is None:
        return ["smoke matrix missing or invalid: smoke_json must reference a JSON metadata artifact"]
    if smoke.get("passed") is not True or smoke.get("failures"):
        failures.append("smoke matrix is not passing")
    if smoke.get("resolution") != key:
        failures.append(f"smoke resolution {smoke.get('resolution')!r} does not match {key}")

    patch = smoke.get("patch_stage")
    if not isinstance(patch, dict):
        patch = {}
    sha = candidate_sha(patch.get("sha256"))
    if sha is None:
        failures.append("patch gate candidate SHA-256 is missing or invalid")
    if not stage or patch.get("stage") != stage:
        failures.append("patch gate stage does not match manifest stable_stage")
    patch_gate = patch.get("current_hd_map_gate") or {}
    if (patch.get("passed") is not True or patch.get("failures")
            or not isinstance(patch_gate, dict) or patch_gate.get("passed") is not True
            or patch_gate.get("failures")):
        failures.append("smoke patch gate is not passing")

    report_ref = smoke.get("patch_report_json")
    report_path = metadata_path(root, report_ref) if isinstance(report_ref, str) and report_ref else None
    report = load_json(report_path) if report_path and report_path.suffix.lower() == ".json" else None
    if report is None:
        failures.append("smoke must reference an existing patch_report_json metadata artifact")
    else:
        # The established archived-report schema predates resolution support.
        # Only an absent key means 800x600; explicit null never means legacy.
        report_resolution = report.get("resolution", EXPECTED_DEFAULT)
        if report_resolution != key:
            failures.append(f"patch report resolution {report_resolution!r} does not match {key}")
        if report.get("stage") != stage:
            failures.append("patch report stage does not match manifest stable_stage")
        if sha is None or candidate_sha(report.get("exe_sha256")) != sha:
            failures.append("patch report candidate SHA-256 does not match smoke patch gate")
        gate = report.get("current_hd_map_gate")
        if not isinstance(gate, dict) or gate.get("passed") is not True or gate.get("failures"):
            failures.append("patch report current_hd_map_gate is not passing")
        count = report.get("patch_count")
        counts = report.get("status_counts")
        if (type(count) is not int or count <= 0 or not isinstance(counts, dict)
                or any(type(value) is not int or value < 0 for value in counts.values())
                or counts.get("patched") != count or sum(counts.values()) != count
                or counts.get("original", 0) != 0 or counts.get("unexpected", 0) != 0):
            failures.append("patch report does not prove every selected byte patched without original/unexpected records")
        embedded_counts = patch.get("patches")
        if (not isinstance(embedded_counts, dict)
                or any(type(embedded_counts.get(field)) is not int or embedded_counts.get(field) != expected
                       for field, expected in (("total", count), ("patched", count), ("original", 0), ("unexpected", 0)))):
            failures.append("smoke patch counts do not match the patch report")
        if patch.get("archived") is True:
            source = patch.get("source")
            if not isinstance(source, str) or metadata_path(root, source) != report_path:
                failures.append("archived patch gate source does not match patch_report_json")

    post_owner = smoke.get("post_owner_evidence")
    if not isinstance(post_owner, dict):
        post_owner = {}
    if post_owner.get("passed") is not True:
        failures.append("smoke post-owner evidence is not passing")
    for run_key, smoke_key in (("normal_run", "normal"), ("forced_run", "forced_visible")):
        run_ref = evidence.get(run_key)
        if not isinstance(run_ref, str) or not run_ref:
            failures.append(f"evidence missing {run_key}")
            continue
        run_path = metadata_path(root, run_ref)
        summary = load_json(run_path / "summary.json")
        if summary is None:
            failures.append(f"{run_key} summary.json missing or invalid")
            continue
        if summary.get("LaunchMode") != "hidden-desktop" or summary.get("HiddenDesktop") is not True:
            failures.append(f"{run_key} is not hidden-desktop")
        if summary.get("Passed") is not True:
            failures.append(f"{run_key} is not passing")
        if summary.get("Stage") != stage:
            failures.append(f"{run_key} stage does not match manifest stable_stage")
        if sha is None or candidate_sha(summary.get("CandidateSha256")) != sha:
            failures.append(f"{run_key} candidate SHA-256 does not match smoke patch gate")
        if not surface_matches(summary.get("Surface"), width, height):
            failures.append(f"{run_key} surface dimensions/bytes do not match {key}")
        row = post_owner.get(smoke_key)
        if not isinstance(row, dict):
            row = {}
        if row.get("passed") is not True or row.get("present") is not True or row.get("failures"):
            failures.append(f"smoke {smoke_key} row is missing or not passing")
        row_run = row.get("run")
        if not isinstance(row_run, str) or metadata_path(root, row_run) != run_path:
            failures.append(f"smoke {smoke_key} run does not match manifest {run_key}")
        if sha is None or candidate_sha(row.get("candidate_sha256")) != sha:
            failures.append(f"smoke {smoke_key} candidate SHA-256 does not match patch gate")
        if not surface_matches(row.get("surface"), width, height):
            failures.append(f"smoke {smoke_key} surface dimensions/bytes do not match {key}")
    return failures


def build_guard(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(args.root)
    manifest_path = root / args.manifest
    checks: dict[str, Any] = {}
    failures: list[str] = []
    check_specs: dict[str, tuple[bool, dict[str, Any], str]] = {}

    manifest = load_json(manifest_path)
    if manifest is None or manifest.get("schema") != 1 or not isinstance(
        manifest.get("resolutions"), dict
    ):
        guard = {
            "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
            "passed": False,
            "runtime_policy": RUNTIME_POLICY,
            "guard_policy": GUARD_POLICY,
            "manifest": str(args.manifest),
            "checks": {},
            "failures": [f"manifest missing, invalid, or wrong schema: {manifest_path}"],
        }
        return guard

    resolutions: dict[str, Any] = manifest["resolutions"]

    bad_keys = [key for key in resolutions if not RESOLUTION_KEY_RE.match(key)]
    bad_statuses = {
        key: entry.get("status")
        for key, entry in resolutions.items()
        if entry.get("status") not in VALID_STATUSES
    }
    check_specs["resolution_keys_valid"] = (
        not bad_keys and not bad_statuses,
        {"bad_keys": bad_keys, "bad_statuses": bad_statuses},
        f"invalid resolution keys or statuses: {bad_keys} {bad_statuses}",
    )

    stable_keys = [
        key for key, entry in resolutions.items() if entry.get("status") == "stable"
    ]
    default_key = manifest.get("default")
    check_specs["single_stable_default"] = (
        stable_keys == [args.expected_default] and default_key == args.expected_default,
        {"stable_keys": stable_keys, "default": default_key},
        f"exactly one stable entry ({args.expected_default}) must equal the default",
    )

    expected_stage = args.expected_stable_stage or patcher_stable_stage()
    check_specs["stable_stage_matches"] = (
        expected_stage is not None and manifest.get("stable_stage") == expected_stage,
        {
            "manifest_stable_stage": manifest.get("stable_stage"),
            "expected_stable_stage": expected_stage,
        },
        "manifest stable_stage must match the patcher DEFAULT_STAGE",
    )

    tile_mismatches: dict[str, Any] = {}
    for key, entry in resolutions.items():
        match = RESOLUTION_KEY_RE.match(key)
        tiles = entry.get("tiles")
        if not match or tiles is None:
            continue
        expected = expected_tiles(int(match.group(1)), int(match.group(2)))
        if tuple(tiles) != expected:
            tile_mismatches[key] = {"manifest": tiles, "expected": list(expected)}
    check_specs["tiles_formula"] = (
        not tile_mismatches,
        {"mismatches": tile_mismatches},
        f"tile counts must follow floor((W-32)/64) x floor((H-16)/64): {tile_mismatches}",
    )

    evidence_failures: list[str] = []
    evidence_checked: list[str] = []
    for key, entry in resolutions.items():
        status = entry.get("status")
        if status not in ("stable", "validated"):
            continue
        evidence_checked.append(key)
        evidence = entry.get("evidence")
        if not isinstance(evidence, dict):
            evidence_failures.append(f"{key}: {status} entry has no evidence block")
            continue
        evidence_failures.extend(
            f"{key}: {failure}"
            for failure in evidence_binding_failures(root, key, evidence, expected_stage)
        )
    check_specs["evidence_backed"] = (
        not evidence_failures,
        {"checked": evidence_checked, "failures": evidence_failures},
        "; ".join(evidence_failures) or "stable/validated entries must be evidence-backed",
    )

    bounds = manifest.get("custom_bounds") or {}
    minimum = bounds.get("min") or []
    maximum = bounds.get("max") or []
    bounds_ok = (
        len(minimum) == 2
        and len(maximum) == 2
        and minimum[0] >= 800
        and minimum[1] >= 600
        and maximum[0] >= minimum[0]
        and maximum[1] >= minimum[1]
    )
    check_specs["custom_bounds_sane"] = (
        bounds_ok,
        {"min": minimum, "max": maximum},
        "custom bounds must be at least 800x600 and max must not be below min",
    )

    for name, (passed, summary, failure) in check_specs.items():
        checks[name] = check_record(name, bool(passed), summary)
        if not passed:
            checks[name]["failures"] = [failure]
            failures.append(f"{name}: {failure}")

    return {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "passed": not failures,
        "runtime_policy": RUNTIME_POLICY,
        "guard_policy": GUARD_POLICY,
        "manifest": str(args.manifest),
        "resolution_count": len(resolutions),
        "status_counts": {
            status: sum(
                1 for entry in resolutions.values() if entry.get("status") == status
            )
            for status in VALID_STATUSES
        },
        "checks": checks,
        "failures": failures,
    }


def print_guard(guard: dict[str, Any]) -> None:
    print(f"overall: {status_text(guard['passed'])}")
    print(f"runtime-policy: {guard['runtime_policy']}")
    print(f"guard-policy: {guard['guard_policy']}")
    for name, check in guard["checks"].items():
        print(f"{name}: {status_text(bool(check.get('passed')))}")
    if guard["failures"]:
        print("failures:")
        for failure in guard["failures"]:
            print(f"  - {failure}")


def write_markdown(path: Path, guard: dict[str, Any]) -> None:
    lines = [
        "# Resolution Manifest Guard",
        "",
        f"- Overall: {status_text(guard['passed'])}",
        f"- Generated: `{guard['generated_at']}`",
        f"- Runtime policy: {guard['runtime_policy']}",
        f"- Guard policy: {guard['guard_policy']}",
        f"- Manifest: `{guard['manifest']}`",
        f"- Resolutions: `{guard.get('resolution_count', 0)}`",
        f"- Status counts: `{guard.get('status_counts', {})}`",
        "",
        "## Checks",
        "",
    ]
    for name, check in guard["checks"].items():
        lines.append(f"- `{name}`: `{status_text(bool(check.get('passed')))}`")
        for failure in check.get("failures", []):
            lines.append(f"  - {failure}")
    if guard["failures"]:
        lines.extend(["", "## Failures", ""])
        lines.extend(f"- {failure}" for failure in guard["failures"])
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=REPO_ROOT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--expected-default", default=EXPECTED_DEFAULT)
    parser.add_argument("--expected-stable-stage", default=None)
    parser.add_argument("--write-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--write-markdown", type=Path, default=DEFAULT_MD)
    parser.add_argument("--require-pass", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    guard = build_guard(args)
    print_guard(guard)
    if args.write_json:
        args.write_json.parent.mkdir(parents=True, exist_ok=True)
        args.write_json.write_text(json.dumps(guard, indent=2) + "\n", encoding="utf-8")
    if args.write_markdown:
        write_markdown(args.write_markdown, guard)
    if args.require_pass and not guard["passed"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
