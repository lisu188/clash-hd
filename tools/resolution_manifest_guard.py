#!/usr/bin/env python3
"""Verify the launcher resolution status manifest stays consistent.

This is a repo-only metadata guard. It reads `src/launcher/resolutions.json`,
the patcher's stable-stage constant, and the evidence artifacts referenced by
stable/validated entries; it does not launch Clash95, CDB, wrappers,
PowerShell, or any visible GUI process.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
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
    def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"), object_pairs_hook=unique_object)
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


def build_legacy_guard(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(args.root)
    manifest_path = root / args.manifest
    checks: dict[str, Any] = {}
    failures: list[str] = []
    check_specs: dict[str, tuple[bool, dict[str, Any], str]] = {}

    manifest = load_json(manifest_path)
    if (manifest is None or type(manifest.get("schema")) is not int or manifest.get("schema") != 1
            or not isinstance(manifest.get("resolutions"), dict)
            or any(not isinstance(entry, dict) for entry in manifest.get("resolutions", {}).values())):
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
        if not isinstance(tiles, list) or tiles != list(expected):
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
    bounds = bounds if isinstance(bounds, dict) else {}
    minimum = bounds.get("min") or []
    maximum = bounds.get("max") or []
    bounds_ok = (
        isinstance(minimum, list) and isinstance(maximum, list)
        and len(minimum) == 2 and len(maximum) == 2
        and all(type(value) is int for value in minimum + maximum)
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


def source_pins(profiles: set[str]) -> dict[str, str]:
    """Read reviewed declarations without importing or executing a builder.

    The guard's checkout supplies the contracts; --root selects the inspected
    source/evidence tree, so changing its pin declaration cannot bless itself.
    """
    names = ["src/patcher/patch_clash95_hd.py", "src/display_plan.py", "src/launcher/presets.py"]
    builders = []
    if profiles - {"classic"}:
        builders = ["build_partial_tile_candidate", "build_framed_candidate"]
    if "completehd" in profiles:
        builders += ["build_framed_modal_candidate", "build_framed_army_candidate"]
        names.append("src/patcher/complete_hd_candidate.py")
    pins: dict[str, str] = {}
    for builder in builders:
        name = f"tools/{builder}.py"
        names.append(name)
        values = {}
        for node in ast.parse((REPO_ROOT / name).read_bytes()).body:
            if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                key = node.targets[0].id
                if key in {"PINNED_SOURCES", "MINIMAP_SOURCE", "MINIMAP_SOURCE_SHA256", "INITIAL_SOURCE_SHA256"}:
                    if key in values:
                        raise ValueError(f"duplicate source contract: {name}/{key}")
                    values[key] = ast.literal_eval(node.value)
        declared = dict(values["PINNED_SOURCES"])
        if builder == "build_framed_candidate":
            declared[values["MINIMAP_SOURCE"]] = values["MINIMAP_SOURCE_SHA256"]
        if builder == "build_partial_tile_candidate":
            declared["src/patcher/initial_map_paint.py"] = values["INITIAL_SOURCE_SHA256"]
        for path, expected in declared.items():
            if path in pins and pins[path] != expected:
                raise ValueError(f"conflicting source contract: {path}")
            pins[path] = expected
    for name in names:
        actual = hashlib.sha256((REPO_ROOT / name).read_bytes()).hexdigest()
        if name in pins and pins[name] != actual:
            raise ValueError(f"reviewed generator source changed: {name}")
        pins[name] = actual
    return pins


def _artifact(root: Path, relative: str) -> Path:
    path = Path(relative)
    target = (root / path).resolve()
    if path.is_absolute() or not target.is_relative_to(root.resolve()):
        raise ValueError(f"evidence/source path escapes repository: {relative}")
    return target


def _profile_evidence(root: Path, key: str, entry: dict[str, Any], config: dict[str, Any]) -> list[str]:
    """Bind the retained hidden component evidence; this is not release proof."""
    failures = []
    evidence = entry.get("evidence") or {}
    width, height = map(int, key.split("x"))
    digests = []
    import patch_clash95_hd as patcher
    for name in ("normal_run", "forced_run"):
        try:
            run = load_json(_artifact(root, evidence[name]) / "summary.json") or {}
            surface = run.get("Surface") or {}
            digest = run.get("CandidateSha256", "").lower()
            if (run.get("Passed") is not True or run.get("LaunchMode") != "hidden-desktop"
                    or run.get("HiddenDesktop") is not True or run.get("AllowVisibleDesktop") is True
                    or run.get("TimedOut") is True or run.get("Av") is True):
                failures.append(f"{key}/{name}: not passing hidden-desktop evidence")
            if (run.get("Stage") != config["stage"] or surface.get("Width") != width
                    or surface.get("Height") != height or surface.get("Bytes") != width * height
                    or ("Resolution" in run and run["Resolution"] != key)):
                failures.append(f"{key}/{name}: stage/resolution differs from profile")
            if (not re.fullmatch(r"[0-9a-f]{64}", digest)
                    or run.get("InputSha256", "").lower() != patcher.EXPECTED_SHA256.lower()):
                failures.append(f"{key}/{name}: missing or unknown executable identity")
            digests.append(digest)
        except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
            failures.append(f"{key}/{name}: {exc}")
    try:
        smoke = load_json(_artifact(root, evidence["smoke_json"])) or {}
        patch = smoke.get("patch_stage") or {}
        digests.append(patch.get("sha256", "").lower())
        if (smoke.get("passed") is not True or smoke.get("resolution") != key
                or patch.get("passed") is not True or patch.get("stage") != config["stage"]):
            failures.append(f"{key}/smoke_json: passing stage/resolution context is absent")
        for name, smoke_name in (("normal_run", "normal"), ("forced_run", "forced_visible")):
            row = (smoke.get("post_owner_evidence") or {}).get(smoke_name) or {}
            if (row.get("passed") is not True
                    or _artifact(root, row.get("run", "")) != _artifact(root, evidence[name])
                    or row.get("candidate_sha256", "").lower() != digests[-1]):
                failures.append(f"{key}/smoke_json: {smoke_name} references another run/candidate")
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        failures.append(f"{key}/smoke_json: {exc}")
    if len(digests) != 3 or len(set(digests)) != 1:
        failures.append(f"{key}: normal, forced and smoke candidate SHA values disagree")
    return failures


def build_guard(args: argparse.Namespace) -> dict[str, Any]:
    manifest = load_json(Path(args.root) / args.manifest)
    if not manifest or manifest.get("schema") != 2:
        return build_legacy_guard(args)
    root = Path(args.root)
    checks: dict[str, Any] = {}
    failures: list[str] = []

    def check(name: str, errors: list[str], **details: Any) -> None:
        checks[name] = check_record(name, not errors, details)
        checks[name]["failures"] = errors
        failures.extend(f"{name}: {error}" for error in errors)

    from src.launcher import presets
    try:
        presets.validate_manifest(manifest)
        check("profile_schema", [])
    except (ValueError, TypeError, AttributeError) as exc:
        check("profile_schema", [str(exc)])
        return {
            "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
            "passed": False, "schema": 2, "runtime_policy": RUNTIME_POLICY, "guard_policy": GUARD_POLICY,
            "manifest": str(args.manifest), "promotion_ready": False, "checks": checks, "failures": failures,
        }
    profiles = manifest.get("profiles")
    profiles = profiles if isinstance(profiles, dict) else {}
    expected_stage = args.expected_stable_stage or patcher_stable_stage()
    errors = []
    if manifest.get("stable_stage") != expected_stage or not expected_stage:
        errors.append("stable_stage must equal the patcher DEFAULT_STAGE")
    if manifest.get("default") != EXPECTED_DEFAULT or manifest.get("default_renderer") != "classic":
        errors.append("the stable default must remain Classic 800x600")
    stable = []
    tile_errors, evidence_errors, status_errors, recipe_errors = [], [], [], []
    suffixes = {"classic": "", "framed": "-combinedui-partialtiles-initialpaint-framed-validation", "completehd": "-completehd-validation"}
    for renderer, config in profiles.items():
        if not isinstance(config, dict) or renderer not in suffixes:
            continue  # Already rejected by the shared schema validator.
        if config.get("stage") != str(expected_stage) + suffixes[renderer]:
            recipe_errors.append(f"{renderer}: exact stage does not match its recipe")
        if config.get("default") != EXPECTED_DEFAULT:
            errors.append(f"{renderer}: default must remain 800x600")
        entries = config.get("resolutions")
        if not isinstance(entries, dict):
            continue
        for key, entry in entries.items():
            if not isinstance(entry, dict):
                continue
            status = entry.get("status")
            if status == "stable":
                stable.append(f"{renderer}/{key}")
            if renderer != "classic" and status != "experimental":
                status_errors.append(f"{renderer}/{key}: recipe has no promoted evidence verifier; must remain experimental")
            if not RESOLUTION_KEY_RE.fullmatch(key):
                continue
            if entry.get("tiles") is not None:
                width, height = map(int, key.split("x"))
                if renderer == "classic":
                    tiles = expected_tiles(width, height)
                else:
                    from src.patcher.framed_viewport import FramedViewport
                    tiles = FramedViewport(width, height).full_tiles
                if entry["tiles"] != list(tiles):
                    tile_errors.append(f"{renderer}/{key}: tile counts differ from {list(tiles)}")
            if renderer == "classic" and status in {"stable", "validated"}:
                evidence_errors.extend(_profile_evidence(root, key, entry, config))
    if stable != ["classic/800x600"]:
        errors.append(f"exactly Classic 800x600 must be stable, found {stable}")
    check("single_stable_default", errors, stable=stable)
    check("profile_recipes", recipe_errors)
    check("experimental_profiles", status_errors)
    check("tiles_formula", tile_errors, framed_formula="FramedViewport.full_tiles; four reserved borders")
    check("evidence_backed", evidence_errors, scope="retained hidden component evidence; no whole-release eligibility")
    source_checks, source_errors = {}, []
    try:
        for name, expected in source_pins(set(profiles)).items():
            try:
                actual = hashlib.sha256(_artifact(root, name).read_bytes()).hexdigest()
            except OSError:
                actual = None
            source_checks[name] = {"expected_sha256": expected, "actual_sha256": actual, "passed": actual == expected}
            if actual != expected:
                source_errors.append(f"source identity mismatch: {name}")
    except (OSError, ValueError, KeyError, TypeError, SyntaxError) as exc:
        source_errors.append(str(exc))
    check("source_context", source_errors, sources=source_checks)
    return {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "passed": not failures, "runtime_policy": RUNTIME_POLICY,
        "guard_policy": "schema-2 exact profile recipe, evidence scope and source context; Classic 800x600 stable default; other renderers experimental",
        "manifest": str(args.manifest), "schema": 2, "profile_count": len(profiles),
        "resolution_count": len(manifest.get("resolutions") or {}),
        "status_counts": {status: sum(1 for config in profiles.values() if isinstance(config, dict)
            for entry in (config.get("resolutions") or {}).values() if isinstance(entry, dict) and entry.get("status") == status)
            for status in VALID_STATUSES},
        "promotion_ready": False, "checks": checks, "failures": failures,
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
