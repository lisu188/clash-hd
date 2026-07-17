#!/usr/bin/env python3
"""Guard the resolved right-bottom natural UI visual-artifact question.

This repo-only guard used to document the rows-absent blocker. That expectation
is retired (user ruling 2026-07-14: slot5-as-slot0 fixture accepted as
natural-draw evidence): the bare-map natural route correctly draws no
owner/action rows because the unmodified slot-0 save's only player-owned record
has owner_flag=0x00, which parks descriptor 004338E0 off-screen. The guard now
validates the resolved state coherently: controlled composition recovered, the
accepted fixture natural-draw evidence still valid, the compose matrix passing
with promotion still deferred, and blocker triage still non-promoting.
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
NON_PROMOTING_TRIAGE_CLASSIFICATIONS = {
    "controlled_recovered_but_natural_route_blocked",
    "controlled_recovered_but_natural_route_nonpromoting",
}

RUNTIME_POLICY = (
    "repo-only visual artifact guard; reads generated JSON reports and does not "
    "launch Clash95, CDB, wrappers, PowerShell, or visible windows"
)
FIXTURE_NATURAL_DRAW_RULING = (
    "user ruling 2026-07-14: slot5-as-slot0 fixture accepted as natural-draw evidence"
)
GUARD_POLICY = (
    "passes only while the resolved right-bottom state holds: controlled "
    "composition is recovered, the accepted slot5-as-slot0 fixture natural-draw "
    "evidence remains valid (user ruling 2026-07-14: slot5-as-slot0 fixture "
    "accepted as natural-draw evidence), the compose evidence matrix passes with "
    "promotion still deferred, and blocker triage remains non-promoting"
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
    fixture = natural_ui.get("fixture") or {}
    fixture_markers = fixture.get("marker_counts") or {}

    owner_action_rows = _int(natural_ui.get("rbui_panel_draw")) + _int(natural_ui.get("rbui_action_box"))
    controlled_recovered = bool(
        _check(compose, "right_bottom_compose_fullstart_route").get("passed")
        and _float(fullstart.get("bottom_right_ui_corner_nonblack")) >= 40.0
        and _float(fullstart.get("bottom_right_tile_r8c10_nonblack")) >= 40.0
        and _float(fullstart.get("bottom_right_tile_r8c11_nonblack")) >= 40.0
        and _int(fullstart.get("av_count")) == 0
    )
    # user ruling 2026-07-14: slot5-as-slot0 fixture accepted as natural-draw evidence.
    # The retired rows-absent expectation is replaced by the same fixture marker
    # requirements the compose probe enforces, read from the compose matrix payload.
    fixture_natural_draw_accepted = bool(
        natural_ui.get("natural_draw_source") == "slot5_as_slot0_fixture"
        and _int(fixture_markers.get("NOWNER_435BC0_PANEL_DRAW")) >= 1
        and _int(fixture_markers.get("NOWNER_435BC0_GRID_DRAW")) >= 1
        and _int(fixture_markers.get("NOWNER_WRAPPER_COPYBACK_DONE")) >= 1
        and fixture.get("av_count") == 0
        and _int(natural_ui.get("av_count")) == 0
    )
    triage_non_promoting = bool(
        triage.get("passed")
        and triage.get("classification") in NON_PROMOTING_TRIAGE_CLASSIFICATIONS
        and triage.get("promotion_ready") is False
        and triage.get("stable_stage_should_change") is False
    )
    compose_passing_promotion_deferred = bool(
        compose.get("passed") is True
        and compose.get("promotion_status") == "validation_stage_only"
        and compose.get("stable_stage_should_change") is False
    )

    checks = {
        "controlled_composition_recovered": controlled_recovered,
        "fixture_natural_draw_accepted": fixture_natural_draw_accepted,
        "compose_matrix_passing_promotion_deferred": compose_passing_promotion_deferred,
        "blocker_triage_non_promoting": triage_non_promoting,
    }
    for name, passed in checks.items():
        if not passed:
            failures.append(f"visual artifact guard failed: {name}")

    status = "fixture_natural_draw_accepted" if not failures else "visual_artifact_guard_stale"
    conclusion = (
        "The right-bottom natural-draw artifact question is resolved by the "
        "accepted slot5-as-slot0 fixture evidence (user ruling 2026-07-14: "
        "slot5-as-slot0 fixture accepted as natural-draw evidence). The bare-map "
        "natural route correctly draws no owner/action rows (owner_flag=0x00 parks "
        "the descriptor off-screen), controlled composition recovers the lower/right "
        "UI, and stable promotion remains deferred pending manual input proof."
    )

    return {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "passed": not failures,
        "runtime_policy": RUNTIME_POLICY,
        "guard_policy": GUARD_POLICY,
        "fixture_ruling": FIXTURE_NATURAL_DRAW_RULING,
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
            "natural_draw_source": natural_ui.get("natural_draw_source"),
            "fixture_run": fixture.get("fixture_run"),
            "fixture_marker_counts": fixture_markers or None,
            "fixture_av_count": fixture.get("av_count"),
            "fixture_proof_class": fixture.get("proof_class"),
            "natural_bottom_right_corner_black": corner.get("black_percent"),
            "natural_r8c10_black": r8c10.get("black_percent"),
            "natural_r8c11_black": r8c11.get("black_percent"),
            "natural_right_side_below_minimap_black": right_side.get("black_percent"),
            "triage_classification": triage.get("classification"),
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
        f"- Fixture ruling: {report['fixture_ruling']}",
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
            f"- Natural owner/action rows (bare map, physically-correct absence): `{observations.get('natural_owner_action_rows')}`",
            f"- Natural draw source: `{observations.get('natural_draw_source')}`",
            f"- Fixture run: `{observations.get('fixture_run')}`",
            f"- Fixture marker counts: `{observations.get('fixture_marker_counts')}`",
            f"- Fixture AV count: `{observations.get('fixture_av_count')}`",
            f"- Fixture proof class: `{observations.get('fixture_proof_class')}`",
            f"- Natural black percentages: corner `{observations.get('natural_bottom_right_corner_black')}`, r8c10 `{observations.get('natural_r8c10_black')}`, r8c11 `{observations.get('natural_r8c11_black')}`",
            f"- Triage classification: `{observations.get('triage_classification')}`",
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
