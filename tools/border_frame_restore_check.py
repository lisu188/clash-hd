#!/usr/bin/env python3
"""Validate the committed border frame-restore band evidence.

Repo-only check for the ``frame-restore-bands`` validation lane. It reads the
committed ``border_frame_bounds.py`` reports (hidden-desktop surfdump proxy and
real-runtime visual-smoke frame), and fails closed unless:

- every expected border band region is present in each analyzed image;
- the HD extension bands are filled (non-black) and their histogram
  authenticity matches against the native source bands passed the gate;
- the gate that produced the evidence recorded thresholds at least as strict
  as this check expects, and passed;
- a real-runtime frame reference is recorded and the referenced capture still
  exists in the repository.

This tool never launches Clash95, CDB, wrappers, or any visible window and
never regenerates evidence; it only validates what is committed.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import border_frame_bounds


REPO_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_EVIDENCE_JSON = Path("captures/current/border-frame-restore-current.json")
DEFAULT_REALRUNTIME_JSON = Path("captures/current/border-frame-restore-realruntime-current.json")
DEFAULT_JSON = Path("captures/current/border-frame-restore-check-current.json")
DEFAULT_MD = Path("captures/current/border-frame-restore-check-current.md")

FRAME_RESTORE_GROUP = "frame-restore-bands"
FRAME_RESTORE_VALIDATION_STAGE = (
    "gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-"
    "presentbounds-minimapright-dynvswitch-framerestore"
)
DEFAULT_PROXY_RUN_TOKEN = "cdb-surface-dump-"
DEFAULT_REAL_RUNTIME_RUN_TOKEN = "visual-smoke-"

REQUIRED_BANDS: tuple[str, ...] = tuple(border_frame_bounds.DEFAULT_REGIONS)
REQUIRED_MATCH_PAIRS: dict[str, str] = dict(border_frame_bounds.DEFAULT_MATCH_PAIRS)
EXTENSION_BANDS: tuple[str, ...] = tuple(REQUIRED_MATCH_PAIRS)
MIN_EXTENSION_NONBLACK_PERCENT = 95.0
MIN_MATCH_SIMILARITY = 0.30

RUNTIME_POLICY = (
    "repo-only committed-evidence validation; does not launch Clash95, CDB, "
    "wrappers, or visible windows"
)
GUARD_POLICY = (
    "committed frame-restore band evidence must keep every border band region, "
    "filled HD extension bands with passing histogram authenticity gates at or "
    "above the frozen thresholds, and a real-runtime frame reference that still "
    "resolves inside the repository"
)


def status_text(passed: bool) -> str:
    return "PASS" if passed else "FAIL"


def resolve_source_frame(value: object, repo_root: Path) -> Path:
    raw = str(value or "").replace("\\", "/")
    path = Path(raw)
    if path.is_absolute():
        return path
    return repo_root / path


def check_image(
    image: dict[str, Any],
    label: str,
    required_run_token: str,
    repo_root: Path,
) -> tuple[dict[str, Any], list[str]]:
    failures: list[str] = []
    source_path = image.get("path")
    normalized_source = str(source_path or "").replace("\\", "/")

    if not normalized_source:
        failures.append(f"{label} evidence image has no source frame path")
    elif required_run_token not in normalized_source:
        failures.append(
            f"{label} evidence frame {normalized_source} does not reference a "
            f"'{required_run_token}' run"
        )

    resolved = resolve_source_frame(source_path, repo_root) if normalized_source else None
    if resolved is not None and not resolved.is_file():
        failures.append(f"{label} evidence source frame is missing: {resolved}")

    regions = {
        str(region.get("name")): region
        for region in image.get("regions") or []
        if isinstance(region, dict)
    }
    missing_bands = sorted(set(REQUIRED_BANDS) - set(regions))
    if missing_bands:
        failures.append(f"{label} evidence is missing border bands: {missing_bands}")

    extension_nonblack: dict[str, Any] = {}
    for band in EXTENSION_BANDS:
        region = regions.get(band)
        if region is None:
            continue
        nonblack = region.get("nonblack_percent")
        extension_nonblack[band] = nonblack
        if not isinstance(nonblack, (int, float)):
            failures.append(f"{label} extension band {band} has no nonblack_percent")
        elif float(nonblack) < MIN_EXTENSION_NONBLACK_PERCENT:
            failures.append(
                f"{label} extension band {band} is not filled: nonblack "
                f"{nonblack}% < {MIN_EXTENSION_NONBLACK_PERCENT}%"
            )

    matches = {
        (str(match.get("dest")), str(match.get("source"))): match
        for match in image.get("matches") or []
        if isinstance(match, dict)
    }
    similarities: dict[str, Any] = {}
    for dest, source in REQUIRED_MATCH_PAIRS.items():
        match = matches.get((dest, source))
        if match is None:
            failures.append(
                f"{label} evidence is missing authenticity match {dest} <- {source}"
            )
            continue
        similarity = match.get("similarity")
        similarities[dest] = similarity
        if not isinstance(similarity, (int, float)):
            failures.append(f"{label} authenticity match {dest} has no similarity")
        elif float(similarity) < MIN_MATCH_SIMILARITY:
            failures.append(
                f"{label} authenticity match {dest} <- {source} similarity "
                f"{similarity} < {MIN_MATCH_SIMILARITY}"
            )

    gate = image.get("gate")
    if not isinstance(gate, dict):
        failures.append(f"{label} evidence has no recorded gate")
        gate = {}
    else:
        if gate.get("passed") is not True:
            failures.append(f"{label} evidence gate did not pass")
        for gate_failure in gate.get("failures") or []:
            failures.append(f"{label} evidence gate failure: {gate_failure}")

    gate_checks = [check for check in gate.get("checks") or [] if isinstance(check, dict)]
    nonblack_checks = {
        str(check.get("region")): check
        for check in gate_checks
        if check.get("kind") == "nonblack"
    }
    match_checks = {
        str(check.get("dest")): check
        for check in gate_checks
        if check.get("kind") == "match"
    }
    for band in EXTENSION_BANDS:
        check = nonblack_checks.get(band)
        if check is None:
            failures.append(f"{label} evidence gate has no nonblack check for {band}")
            continue
        minimum = check.get("minimum_nonblack_percent")
        if not isinstance(minimum, (int, float)) or float(minimum) < MIN_EXTENSION_NONBLACK_PERCENT:
            failures.append(
                f"{label} gate nonblack minimum for {band} is {minimum}, "
                f"expected >= {MIN_EXTENSION_NONBLACK_PERCENT}"
            )
        if check.get("passed") is not True:
            failures.append(f"{label} gate nonblack check for {band} did not pass")
    for dest in REQUIRED_MATCH_PAIRS:
        check = match_checks.get(dest)
        if check is None:
            failures.append(f"{label} evidence gate has no similarity check for {dest}")
            continue
        minimum = check.get("minimum_similarity")
        if not isinstance(minimum, (int, float)) or float(minimum) < MIN_MATCH_SIMILARITY:
            failures.append(
                f"{label} gate similarity minimum for {dest} is {minimum}, "
                f"expected >= {MIN_MATCH_SIMILARITY}"
            )
        if check.get("passed") is not True:
            failures.append(f"{label} gate similarity check for {dest} did not pass")

    summary = {
        "source_frame": normalized_source or None,
        "source_frame_exists": bool(resolved is not None and resolved.is_file()),
        "gate_passed": gate.get("passed") is True,
        "extension_nonblack_percent": extension_nonblack,
        "match_similarity": similarities,
    }
    return summary, failures


def check_evidence_file(
    path: Path,
    *,
    label: str,
    required_run_token: str,
    repo_root: Path,
) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "path": str(path),
        "required_run_token": required_run_token,
        "required_bands": list(REQUIRED_BANDS),
        "required_match_pairs": dict(REQUIRED_MATCH_PAIRS),
        "min_extension_nonblack_percent": MIN_EXTENSION_NONBLACK_PERCENT,
        "min_match_similarity": MIN_MATCH_SIMILARITY,
    }
    if not path.is_file():
        return {
            "passed": False,
            "summary": summary,
            "failures": [f"{label} border evidence is missing: {path}"],
        }
    try:
        report = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as exc:
        return {
            "passed": False,
            "summary": summary,
            "failures": [
                f"{label} border evidence could not be parsed: {type(exc).__name__}: {exc}"
            ],
        }
    if not isinstance(report, dict):
        return {
            "passed": False,
            "summary": summary,
            "failures": [f"{label} border evidence is not a JSON object"],
        }

    failures: list[str] = []
    images = [image for image in report.get("images") or [] if isinstance(image, dict)]
    if not images:
        failures.append(f"{label} border evidence has no analyzed images")

    image_summaries: list[dict[str, Any]] = []
    for image in images:
        image_summary, image_failures = check_image(
            image, label, required_run_token, repo_root
        )
        image_summaries.append(image_summary)
        failures.extend(image_failures)

    summary["image_count"] = len(images)
    summary["images"] = image_summaries
    return {
        "passed": not failures,
        "summary": summary,
        "failures": failures,
    }


def build_check(args: argparse.Namespace) -> dict[str, Any]:
    repo_root = Path(getattr(args, "repo_root", None) or REPO_ROOT)
    checks = {
        "proxy_surface_evidence": check_evidence_file(
            args.evidence_json,
            label="proxy-surface",
            required_run_token=args.proxy_run_token,
            repo_root=repo_root,
        ),
        "real_runtime_evidence": check_evidence_file(
            args.realruntime_json,
            label="real-runtime",
            required_run_token=args.real_runtime_run_token,
            repo_root=repo_root,
        ),
    }
    failures: list[str] = []
    for name, check in checks.items():
        if not check.get("passed"):
            failures.extend(f"{name}: {failure}" for failure in check.get("failures", []))

    real_runtime_frames = [
        image.get("source_frame")
        for image in checks["real_runtime_evidence"]["summary"].get("images", [])
        if image.get("source_frame")
    ]
    return {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "passed": not failures,
        "runtime_policy": RUNTIME_POLICY,
        "guard_policy": GUARD_POLICY,
        "patch_group": FRAME_RESTORE_GROUP,
        "validation_stage": FRAME_RESTORE_VALIDATION_STAGE,
        "real_runtime_frames": real_runtime_frames,
        "checks": checks,
        "failures": failures,
    }


def print_check(report: dict[str, Any]) -> None:
    print(f"overall: {status_text(bool(report['passed']))}")
    print(f"runtime-policy: {report['runtime_policy']}")
    print(f"patch-group: {report['patch_group']}")
    print(f"validation-stage: {report['validation_stage']}")
    print(f"real-runtime-frames: {report['real_runtime_frames']}")
    for name, check in report["checks"].items():
        print(f"{name}: {status_text(bool(check.get('passed')))}")
    if report["failures"]:
        print("failures:")
        for failure in report["failures"]:
            print(f"  - {failure}")


def write_json(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


def write_markdown(path: Path, report: dict[str, Any]) -> None:
    lines = [
        "# Border Frame-Restore Evidence Check",
        "",
        f"- Overall: {status_text(bool(report['passed']))}",
        f"- Generated: `{report['generated_at']}`",
        f"- Runtime policy: {report['runtime_policy']}",
        f"- Guard policy: {report['guard_policy']}",
        f"- Patch group: `{report['patch_group']}`",
        f"- Validation stage: `{report['validation_stage']}`",
        f"- Real-runtime frames: `{report['real_runtime_frames']}`",
        "",
        "## Checks",
        "",
    ]
    for name, check in report["checks"].items():
        summary = check.get("summary") or {}
        lines.append(f"### {name}")
        lines.append("")
        lines.append(f"- Status: {status_text(bool(check.get('passed')))}")
        lines.append(f"- Evidence: `{summary.get('path')}`")
        lines.append(f"- Required run token: `{summary.get('required_run_token')}`")
        lines.append(f"- Analyzed images: `{summary.get('image_count')}`")
        for image in summary.get("images", []):
            lines.append(
                "- Frame `{frame}` (exists=`{exists}` gate=`{gate}`): "
                "extension nonblack `{nonblack}`, similarity `{similarity}`".format(
                    frame=image.get("source_frame"),
                    exists=image.get("source_frame_exists"),
                    gate=image.get("gate_passed"),
                    nonblack=image.get("extension_nonblack_percent"),
                    similarity=image.get("match_similarity"),
                )
            )
        for failure in check.get("failures", []):
            lines.append(f"- Failure: {failure}")
        lines.append("")
    if report["failures"]:
        lines.extend(["## Failures", ""])
        lines.extend(f"- {failure}" for failure in report["failures"])
        lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-json", type=Path, default=DEFAULT_EVIDENCE_JSON)
    parser.add_argument("--realruntime-json", type=Path, default=DEFAULT_REALRUNTIME_JSON)
    parser.add_argument("--proxy-run-token", default=DEFAULT_PROXY_RUN_TOKEN)
    parser.add_argument("--real-runtime-run-token", default=DEFAULT_REAL_RUNTIME_RUN_TOKEN)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--write-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--write-markdown", type=Path, default=DEFAULT_MD)
    parser.add_argument("--require-pass", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = build_check(args)
    print_check(report)
    if args.write_json:
        write_json(args.write_json, report)
    if args.write_markdown:
        write_markdown(args.write_markdown, report)
    if args.require_pass and not report["passed"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
