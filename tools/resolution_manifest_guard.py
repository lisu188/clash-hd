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
    "entries backed by passing hidden-desktop evidence, tile counts matching "
    "the engine formula"
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


def run_dir_is_hidden(root: Path, run_rel: str) -> tuple[bool, str]:
    run_dir = root / run_rel
    if not run_dir.is_dir():
        return False, f"run directory missing: {run_rel}"
    summary = load_json(run_dir / "summary.json")
    if summary is None:
        return False, f"run summary.json missing or invalid: {run_rel}"
    if summary.get("LaunchMode") != "hidden-desktop" or not summary.get("HiddenDesktop"):
        return False, f"run is not hidden-desktop: {run_rel}"
    return True, ""


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
        for run_key in ("normal_run", "forced_run"):
            run_rel = evidence.get(run_key)
            if not run_rel:
                evidence_failures.append(f"{key}: evidence missing {run_key}")
                continue
            hidden, reason = run_dir_is_hidden(root, str(run_rel))
            if not hidden:
                evidence_failures.append(f"{key}: {reason}")
        smoke_rel = evidence.get("smoke_json")
        if not smoke_rel:
            evidence_failures.append(f"{key}: evidence missing smoke_json")
        else:
            smoke = load_json(root / str(smoke_rel))
            if smoke is None:
                evidence_failures.append(f"{key}: smoke matrix missing or invalid: {smoke_rel}")
            elif not smoke.get("passed"):
                evidence_failures.append(f"{key}: smoke matrix is not passing: {smoke_rel}")
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
