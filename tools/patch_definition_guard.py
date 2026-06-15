#!/usr/bin/env python3
"""Statically verify Clash95 HD patch/stage definitions.

This guard imports patch definitions only. It does not read, build, or execute
any game executable.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import patch_clash95_hd


DEFAULT_JSON = Path("captures/current/patch-definition-current.json")
DEFAULT_MD = Path("captures/current/patch-definition-current.md")
RUNTIME_POLICY = "repo-only patch-table inspection; does not read, build, or execute game executables"
EXPECTED_STABLE_STAGE = (
    "gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-"
    "presentbounds-minimapright-dynvswitch"
)
RIGHT_BOTTOM_VALIDATION_STAGE = EXPECTED_STABLE_STAGE + "-rightbottomcompose"
CASTLECENTER_STAGE = EXPECTED_STABLE_STAGE + "-castlecenter"
CASTLECENTER_HITBOX_STAGE = EXPECTED_STABLE_STAGE + "-castlecenter-hitbox"
CASTLECENTER_ALL_STAGE = EXPECTED_STABLE_STAGE + "-castlecenter-all"
BATTLECENTER_STAGE = CASTLECENTER_ALL_STAGE + "-battlecenter"
BATTLECENTER_INPUTPROBE_STAGE = BATTLECENTER_STAGE + "-inputprobe"
VALIDATION_ONLY_GROUPS = {
    "right-bottom-compose-proof",
    "castle-ui-center-present",
    "castle-ui-center-present-wrapper",
    "castle-ui-centered-input",
    "castle-overview-center-present-wrapper",
    "castle-overview-centered-input",
    "battle-ui-center-present-wrapper",
    "battle-grid-centered-input",
    "battle-ui-centered-input",
}
VALIDATION_STAGE_EXTRAS = {
    RIGHT_BOTTOM_VALIDATION_STAGE: {"right-bottom-compose-proof"},
    CASTLECENTER_STAGE: {"castle-ui-center-present"},
    CASTLECENTER_HITBOX_STAGE: {"castle-ui-center-present", "castle-ui-centered-input"},
    CASTLECENTER_ALL_STAGE: {
        "castle-ui-center-present-wrapper",
        "castle-ui-centered-input",
        "castle-overview-center-present-wrapper",
        "castle-overview-centered-input",
    },
    BATTLECENTER_STAGE: {
        "castle-ui-center-present-wrapper",
        "castle-ui-centered-input",
        "castle-overview-center-present-wrapper",
        "castle-overview-centered-input",
        "battle-ui-center-present-wrapper",
    },
    BATTLECENTER_INPUTPROBE_STAGE: {
        "castle-ui-center-present-wrapper",
        "castle-ui-centered-input",
        "castle-overview-center-present-wrapper",
        "castle-overview-centered-input",
        "battle-ui-center-present-wrapper",
        "battle-grid-centered-input",
        "battle-ui-centered-input",
    },
}


def status_text(passed: bool) -> str:
    return "PASS" if passed else "FAIL"


def patch_group_counts(patches: list[Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for patch in patches:
        counts[patch.group] = counts.get(patch.group, 0) + 1
    return dict(sorted(counts.items()))


def patch_span(patch: Any) -> tuple[int, int]:
    old = bytes.fromhex(patch.old_hex)
    return patch.offset, patch.offset + len(old)


def patch_identity(patch: Any) -> tuple[str, int, str, str]:
    return patch.group, patch.offset, patch.old_hex.lower(), patch.new_hex.lower()


def stage_selected_patches(module: Any, stage: str) -> list[Any]:
    groups = set(module.STAGE_GROUPS[stage])
    return [patch for patch in module.PATCHES if patch.group in groups]


def incompatible_overlaps(module: Any, stage: str) -> list[str]:
    patches = stage_selected_patches(module, stage)
    failures: list[str] = []
    for index, left in enumerate(patches):
        left_start, left_end = patch_span(left)
        for right in patches[index + 1 :]:
            right_start, right_end = patch_span(right)
            if left_start >= right_end or right_start >= left_end:
                continue
            if patch_identity(left) == patch_identity(right):
                continue
            failures.append(
                f"{stage}: overlapping selected patches at 0x{max(left_start, right_start):06x}: "
                f"{left.group}@0x{left.offset:06x} conflicts with {right.group}@0x{right.offset:06x}"
            )
    return failures


def build_guard(args: argparse.Namespace, module: Any = patch_clash95_hd) -> dict[str, Any]:
    failures: list[str] = []
    patches = list(module.PATCHES)
    patch_groups = {patch.group for patch in patches}
    stage_groups = {stage: tuple(groups) for stage, groups in module.STAGE_GROUPS.items()}
    stable_stage = getattr(module, "DEFAULT_STAGE", None)
    stable_groups = set(stage_groups.get(EXPECTED_STABLE_STAGE, ()))

    if stable_stage != EXPECTED_STABLE_STAGE:
        failures.append(f"patcher DEFAULT_STAGE is {stable_stage!r}, expected {EXPECTED_STABLE_STAGE!r}")
    if EXPECTED_STABLE_STAGE not in stage_groups:
        failures.append(f"expected stable stage is missing: {EXPECTED_STABLE_STAGE}")

    unknown_group_refs: dict[str, list[str]] = {}
    for stage, groups in stage_groups.items():
        unknown = sorted(set(groups) - patch_groups)
        if unknown:
            unknown_group_refs[stage] = unknown
            failures.append(f"{stage} references unknown patch groups: {unknown}")

    validation_groups_in_stable = sorted(VALIDATION_ONLY_GROUPS & stable_groups)
    if validation_groups_in_stable:
        failures.append(f"validation-only groups leaked into stable stage: {validation_groups_in_stable}")

    validation_stage_summaries: dict[str, dict[str, Any]] = {}
    for stage, extras in VALIDATION_STAGE_EXTRAS.items():
        groups = set(stage_groups.get(stage, ()))
        expected = stable_groups | extras
        missing = sorted(expected - groups)
        unexpected = sorted(groups - expected)
        validation_stage_summaries[stage] = {
            "groups": sorted(groups),
            "expected_extras": sorted(extras),
            "missing": missing,
            "unexpected": unexpected,
        }
        if not groups:
            failures.append(f"validation stage is missing: {stage}")
        if missing:
            failures.append(f"{stage} is missing expected stable/validation groups: {missing}")
        if unexpected:
            failures.append(f"{stage} has unexpected groups beyond stable plus expected extras: {unexpected}")

    overlap_failures: list[str] = []
    for stage in sorted(stage_groups):
        if stage in unknown_group_refs:
            continue
        overlap_failures.extend(incompatible_overlaps(module, stage))
    failures.extend(overlap_failures)

    return {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "passed": not failures,
        "runtime_policy": RUNTIME_POLICY,
        "guard_policy": "patch stage definitions must reference real groups, keep validation-only groups out of stable, keep validation stages scoped to stable plus expected extras, and avoid incompatible selected offset overlaps",
        "expected_stable_stage": EXPECTED_STABLE_STAGE,
        "patcher_default_stage": stable_stage,
        "patch_count": len(patches),
        "patch_group_count": len(patch_groups),
        "stage_count": len(stage_groups),
        "patch_group_counts": patch_group_counts(patches),
        "stable_groups": sorted(stable_groups),
        "validation_only_groups": sorted(VALIDATION_ONLY_GROUPS),
        "validation_groups_in_stable": validation_groups_in_stable,
        "validation_stage_summaries": validation_stage_summaries,
        "unknown_group_refs": unknown_group_refs,
        "overlap_failure_count": len(overlap_failures),
        "failures": failures,
    }


def print_guard(guard: dict[str, Any]) -> None:
    print(f"overall: {status_text(bool(guard['passed']))}")
    print(f"runtime-policy: {guard['runtime_policy']}")
    print(f"patcher-default-stage: {guard['patcher_default_stage']}")
    print(f"patch-groups: {guard['patch_group_count']}")
    print(f"stages: {guard['stage_count']}")
    if guard["failures"]:
        print("failures:")
        for failure in guard["failures"]:
            print(f"  - {failure}")


def write_markdown(path: Path, guard: dict[str, Any]) -> None:
    lines = [
        "# Patch Definition Guard",
        "",
        f"- Overall: {status_text(bool(guard['passed']))}",
        f"- Generated: `{guard['generated_at']}`",
        f"- Runtime policy: {guard['runtime_policy']}",
        f"- Guard policy: {guard['guard_policy']}",
        f"- Expected stable stage: `{guard['expected_stable_stage']}`",
        f"- Patcher default stage: `{guard['patcher_default_stage']}`",
        f"- Patch count: `{guard['patch_count']}`",
        f"- Patch groups: `{guard['patch_group_count']}`",
        f"- Stages: `{guard['stage_count']}`",
        f"- Validation-only groups in stable: `{guard['validation_groups_in_stable']}`",
        f"- Incompatible selected overlaps: `{guard['overlap_failure_count']}`",
        "",
        "## Validation Stages",
        "",
    ]
    for stage, summary in guard["validation_stage_summaries"].items():
        lines.append(
            f"- `{stage}` extras=`{summary['expected_extras']}` missing=`{summary['missing']}` unexpected=`{summary['unexpected']}`"
        )
    if guard["failures"]:
        lines.extend(["", "## Failures", ""])
        lines.extend(f"- {failure}" for failure in guard["failures"])
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
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
