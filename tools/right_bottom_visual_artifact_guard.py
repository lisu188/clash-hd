#!/usr/bin/env python3
"""Guard the current right-bottom natural UI visual artifact.

This repo-only guard documents the user's visible concern: the natural
right-bottom action/menu state still looks incomplete because the natural route
does not enter owner/action draw rows. Controlled composition can recover the
lower/right UI, but that is not the same as natural gameplay proof.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_COMPOSE_EVIDENCE_JSON = Path("captures/current/right-bottom-compose-evidence-current.json")
DEFAULT_BLOCKER_TRIAGE_JSON = Path("captures/current/right-bottom-blocker-triage-current.json")
DEFAULT_JSON = Path("captures/current/right-bottom-visual-artifact-guard-current.json")
DEFAULT_MD = Path("captures/current/right-bottom-visual-artifact-guard-current.md")

RUNTIME_POLICY = (
    "repo-only visual artifact guard; reads generated JSON reports and does not "
    "launch Clash95, CDB, wrappers, PowerShell, or visible windows"
)
GUARD_POLICY = (
    "passes only while the current natural right-bottom visual artifact remains "
    "explicitly blocked from promotion: controlled composition is recovered, "
    "natural owner/action rows are absent, and the lower/right natural regions "
    "still show the known black/striped incomplete state"
)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def status_text(passed: bool) -> str:
    return "PASS" if passed else "FAIL"


def _check(compose: dict[str, Any], name: str) -> dict[str, Any]:
    return (compose.get("checks") or {}).get(name) or {}


def _summary(compose: dict[str, Any], name: str) -> dict[str, Any]:
    return _check(compose, name).get("summary") or {}


def _region(bounds: dict[str, Any], name: str) -> dict[str, Any]:
    return bounds.get(name) or {}


def _float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _has_flags(region: dict[str, Any], *flags: str) -> bool:
    present = set(region.get("flags") or [])
    return all(flag in present for flag in flags)


def build_guard(
    *,
    compose_evidence_json: Path = DEFAULT_COMPOSE_EVIDENCE_JSON,
    blocker_triage_json: Path = DEFAULT_BLOCKER_TRIAGE_JSON,
) -> dict[str, Any]:
    failures: list[str] = []
    if not compose_evidence_json.exists():
        failures.append(f"missing right-bottom compose evidence: {compose_evidence_json}")
        compose: dict[str, Any] = {}
    else:
        compose = load_json(compose_evidence_json)

    if not blocker_triage_json.exists():
        failures.append(f"missing right-bottom blocker triage: {blocker_triage_json}")
        triage: dict[str, Any] = {}
    else:
        triage = load_json(blocker_triage_json)

    fullstart = _summary(compose, "right_bottom_compose_fullstart_route")
    natural_ui = _summary(compose, "right_bottom_compose_ui_probe")
    bounds = natural_ui.get("bounds") or {}
    corner = _region(bounds, "bottom_right_ui_corner")
    r8c10 = _region(bounds, "bottom_right_tile_r8c10")
    r8c11 = _region(bounds, "bottom_right_tile_r8c11")
    right_side = _region(bounds, "right_side_below_minimap")

    owner_action_rows = _int(natural_ui.get("rbui_panel_draw")) + _int(natural_ui.get("rbui_action_box"))
    controlled_recovered = bool(
        _check(compose, "right_bottom_compose_fullstart_route").get("passed")
        and _float(fullstart.get("bottom_right_ui_corner_nonblack")) >= 40.0
        and _float(fullstart.get("bottom_right_tile_r8c10_nonblack")) >= 40.0
        and _float(fullstart.get("bottom_right_tile_r8c11_nonblack")) >= 40.0
        and _int(fullstart.get("av_count")) == 0
    )
    natural_rows_absent = bool(
        natural_ui.get("rbui_markers_seen")
        and _int(natural_ui.get("rbui_desc_switch")) > 0
        and _int(natural_ui.get("rbui_viewport_switch")) > 0
        and owner_action_rows == 0
        and _int(natural_ui.get("av_count")) == 0
    )
    natural_visual_artifact_present = bool(
        _float(corner.get("black_percent")) >= 70.0
        and _float(r8c10.get("black_percent")) >= 99.0
        and _float(r8c11.get("black_percent")) >= 99.0
        and _has_flags(corner, "large_black_component", "black_touches_bottom_right")
        and _has_flags(r8c10, "mostly_black", "large_black_component", "black_touches_bottom_right")
        and _has_flags(r8c11, "mostly_black", "large_black_component", "black_touches_bottom_right")
    )
    controlled_vs_natural_gap = bool(
        _float(fullstart.get("bottom_right_tile_r8c10_nonblack")) >= 40.0
        and _float(fullstart.get("bottom_right_tile_r8c11_nonblack")) >= 40.0
        and _float(r8c10.get("nonblack_percent")) <= 1.0
        and _float(r8c11.get("nonblack_percent")) <= 1.0
    )
    triage_non_promoting = bool(
        triage.get("passed")
        and triage.get("classification") == "controlled_recovered_but_natural_route_blocked"
        and triage.get("promotion_ready") is False
        and triage.get("stable_stage_should_change") is False
    )
    compose_non_promoting = bool(
        compose.get("promotion_status") == "validation_stage_only"
        and compose.get("stable_stage_should_change") is False
        and compose.get("passed") is False
    )

    checks = {
        "controlled_composition_recovered": controlled_recovered,
        "natural_owner_action_rows_absent": natural_rows_absent,
        "natural_visual_artifact_present": natural_visual_artifact_present,
        "controlled_vs_natural_visual_gap": controlled_vs_natural_gap,
        "blocker_triage_non_promoting": triage_non_promoting,
        "compose_matrix_non_promoting": compose_non_promoting,
    }
    for name, passed in checks.items():
        if not passed:
            failures.append(f"visual artifact guard failed: {name}")

    status = "natural_ui_visual_artifact_blocked" if not failures else "visual_artifact_guard_stale"
    conclusion = (
        "The striped/out-of-place right-bottom action-menu view is still a "
        "blocked natural UI artifact, not stable evidence. Controlled "
        "composition proves the lower/right UI can be drawn, but natural "
        "gameplay has not entered the owner/action draw path."
    )

    return {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "passed": not failures,
        "runtime_policy": RUNTIME_POLICY,
        "guard_policy": GUARD_POLICY,
        "visual_status": status,
        "promotion_ready": False,
        "stable_stage_should_change": False,
        "source_artifacts": {
            "compose_evidence_json": str(compose_evidence_json),
            "blocker_triage_json": str(blocker_triage_json),
        },
        "checks": checks,
        "observations": {
            "controlled_bottom_right_ui_corner_nonblack": fullstart.get("bottom_right_ui_corner_nonblack"),
            "controlled_r8c10_nonblack": fullstart.get("bottom_right_tile_r8c10_nonblack"),
            "controlled_r8c11_nonblack": fullstart.get("bottom_right_tile_r8c11_nonblack"),
            "natural_owner_action_rows": owner_action_rows,
            "natural_bottom_right_corner_black": corner.get("black_percent"),
            "natural_r8c10_black": r8c10.get("black_percent"),
            "natural_r8c11_black": r8c11.get("black_percent"),
            "natural_right_side_below_minimap_black": right_side.get("black_percent"),
            "natural_corner_flags": corner.get("flags") or [],
            "natural_r8c10_flags": r8c10.get("flags") or [],
            "natural_r8c11_flags": r8c11.get("flags") or [],
        },
        "conclusion": conclusion,
        "failures": failures,
    }


def write_markdown(path: Path, report: dict[str, Any]) -> None:
    observations = report["observations"]
    lines = [
        "# Right-Bottom Visual Artifact Guard",
        "",
        f"- Overall: {status_text(bool(report['passed']))}",
        f"- Generated: `{report['generated_at']}`",
        f"- Runtime policy: {report['runtime_policy']}",
        f"- Guard policy: {report['guard_policy']}",
        f"- Visual status: `{report['visual_status']}`",
        f"- Promotion ready: `{report['promotion_ready']}`",
        f"- stable_stage_should_change: `{report['stable_stage_should_change']}`",
        f"- Conclusion: {report['conclusion']}",
        "",
        "## Checks",
        "",
    ]
    lines.extend(f"- `{name}`: `{status_text(bool(passed))}`" for name, passed in report["checks"].items())
    lines.extend(
        [
            "",
            "## Observations",
            "",
            f"- Controlled lower/right nonblack: corner `{observations.get('controlled_bottom_right_ui_corner_nonblack')}`, r8c10 `{observations.get('controlled_r8c10_nonblack')}`, r8c11 `{observations.get('controlled_r8c11_nonblack')}`",
            f"- Natural owner/action rows: `{observations.get('natural_owner_action_rows')}`",
            f"- Natural black percentages: corner `{observations.get('natural_bottom_right_corner_black')}`, r8c10 `{observations.get('natural_r8c10_black')}`, r8c11 `{observations.get('natural_r8c11_black')}`",
            f"- Natural corner flags: `{observations.get('natural_corner_flags')}`",
            f"- Natural r8c10 flags: `{observations.get('natural_r8c10_flags')}`",
            f"- Natural r8c11 flags: `{observations.get('natural_r8c11_flags')}`",
        ]
    )
    if report["failures"]:
        lines.extend(["", "## Failures", ""])
        lines.extend(f"- {failure}" for failure in report["failures"])
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def write_json(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compose-evidence-json", type=Path, default=DEFAULT_COMPOSE_EVIDENCE_JSON)
    parser.add_argument("--blocker-triage-json", type=Path, default=DEFAULT_BLOCKER_TRIAGE_JSON)
    parser.add_argument("--write-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--write-markdown", type=Path, default=DEFAULT_MD)
    parser.add_argument("--require-pass", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = build_guard(
        compose_evidence_json=args.compose_evidence_json,
        blocker_triage_json=args.blocker_triage_json,
    )
    write_json(args.write_json, report)
    write_markdown(args.write_markdown, report)
    print(f"overall: {status_text(bool(report['passed']))}")
    print(f"visual-status: {report['visual_status']}")
    print(f"promotion-ready: {report['promotion_ready']}")
    for name, passed in report["checks"].items():
        print(f"{name}: {status_text(bool(passed))}")
    if report["failures"]:
        print("failures:")
        for failure in report["failures"]:
            print(f"  - {failure}")
    if args.require_pass and not report["passed"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
