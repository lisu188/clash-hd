#!/usr/bin/env python3
"""Fixture tests for the project documentation consistency guard."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "docs_consistency_guard.py"
sys.path.insert(0, str(ROOT / "tools"))

import docs_consistency_guard


STABLE_STAGE = (
    "gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-"
    "presentbounds-minimapright-dynvswitch"
)


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def fixture_args(root: Path) -> argparse.Namespace:
    refresh = root / "refresh.json"
    boundary = root / "boundary.json"
    checklist = root / "checklist.json"
    stable = root / "stable.json"
    right_bottom = root / "right-bottom.json"
    castle = root / "castle.json"
    project = root / "project.md"
    handoff = root / "handoff.md"
    evidence = root / "evidence.md"

    write_json(
        refresh,
        {
            "passed": True,
            "checks": {
                "stable_stage_guard": {
                    "passed": True,
                    "summary": {
                        "current_stable_stage": STABLE_STAGE,
                        "patcher_default_stage": STABLE_STAGE,
                    },
                },
                "no_popup_boundary_guard": {
                    "passed": True,
                    "summary": {
                        "required_guard_count": 7,
                        "required_supporting_report_count": 90,
                        "required_report_count": 97,
                    },
                },
            },
        },
    )
    write_json(
        boundary,
        {
            "passed": True,
            "required_guard_count": 7,
            "required_supporting_report_count": 90,
            "required_report_count": 97,
        },
    )
    write_json(
        checklist,
        {
            "status": "pending_manual_validation",
            "visible_runtime_requires_approval": True,
            "promotion_ready": False,
            "no_popup_operator_preference": docs_consistency_guard.NO_POPUP_PREFERENCE,
            "items": [
                {"id": item_id, "status": "pending_manual"}
                for item_id in docs_consistency_guard.EXPECTED_MANUAL_TARGET_IDS
            ],
        },
    )
    write_json(
        stable,
        {
            "passed": True,
            "current_stable_stage": STABLE_STAGE,
            "patcher_default_stage": STABLE_STAGE,
        },
    )
    write_json(
        right_bottom,
        {
            "passed": True,
            "promotion_status": "validation_stage_only",
            "stable_stage_should_change": False,
        },
    )
    write_json(
        castle,
        {
            "passed": True,
            "promotion_status": "validation_stage_only",
            "stable_stage_should_change": False,
        },
    )

    project_text = (
        "# Clash95 HD\n\n"
        f"Protected stable stage: `{STABLE_STAGE}`.\n\n"
        "Visible and manual runtime requires fresh explicit user approval.\n"
        "No-popup repository checks remain the default.\n"
    )
    write_text(project, project_text)
    write_text(handoff, f"Current Clash95 HD stable stage: `{STABLE_STAGE}`.\n")
    write_text(evidence, "# Current Clash95 HD evidence\n")

    return argparse.Namespace(
        refresh_json=refresh,
        boundary_json=boundary,
        manual_checklist_json=checklist,
        manual_template_json=root / "manual-template.json",
        stable_stage_json=stable,
        right_bottom_matrix_json=right_bottom,
        right_bottom_decision_json=root / "right-bottom-decision.json",
        castle_matrix_json=castle,
        castle_decision_json=root / "castle-decision.json",
        hd_map_smoke_json=root / "hd-smoke.json",
        post_owner_evidence_json=root / "post-owner.json",
        no_popup_map_json=root / "no-popup.json",
        visible_runtime_json=root / "visible.json",
        no_visible_runtime_json=root / "no-visible.json",
        evidence_index=evidence,
        codex_loop_docs=(handoff,),
        readme_progress_docs=(project,),
        wiki_summary_docs=(project,),
    )


def test_passes_project_documentation() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        args = fixture_args(Path(temporary))
        guard = docs_consistency_guard.build_guard(args)
        assert guard["passed"], guard["failures"]
        assert guard["checks"]["project_identity"]["passed"]
        assert guard["checks"]["legacy_scaffold_absent"]["passed"]


def test_rejects_legacy_repository_identity() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        args = fixture_args(root)
        project = args.wiki_summary_docs[0]
        write_text(project, "# LLM Wiki\n\nA generic LLM-friendly knowledge repository.\n")
        guard = docs_consistency_guard.build_guard(args)
        assert not guard["passed"]
        assert not guard["checks"]["project_identity"]["passed"]


def test_rejects_stable_stage_drift() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        args = fixture_args(root)
        write_json(
            args.stable_stage_json,
            {
                "passed": True,
                "current_stable_stage": STABLE_STAGE,
                "patcher_default_stage": STABLE_STAGE + "-drift",
            },
        )
        args.refresh_json = root / "missing-refresh.json"
        guard = docs_consistency_guard.build_guard(args)
        assert not guard["passed"]
        assert not guard["checks"]["generated_state"]["passed"]


def test_cli_writes_outputs_and_fails_closed() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        args = fixture_args(root)
        output_json = root / "output.json"
        output_md = root / "output.md"
        command = [
            sys.executable,
            str(SCRIPT),
            "--refresh-json",
            str(args.refresh_json),
            "--boundary-json",
            str(args.boundary_json),
            "--manual-checklist-json",
            str(args.manual_checklist_json),
            "--stable-stage-json",
            str(args.stable_stage_json),
            "--right-bottom-matrix-json",
            str(args.right_bottom_matrix_json),
            "--castle-matrix-json",
            str(args.castle_matrix_json),
            "--evidence-index",
            str(args.evidence_index),
            "--codex-loop-doc",
            str(args.codex_loop_docs[0]),
            "--readme-progress-doc",
            str(args.readme_progress_docs[0]),
            "--project-summary-doc",
            str(args.wiki_summary_docs[0]),
            "--write-json",
            str(output_json),
            "--write-markdown",
            str(output_md),
            "--require-pass",
        ]
        result = subprocess.run(command, capture_output=True, text=True, cwd=ROOT)
        assert result.returncode == 0, result.stdout + result.stderr
        assert output_json.exists()
        assert output_md.exists()

        write_text(args.wiki_summary_docs[0], "# LLM Wiki\n")
        result = subprocess.run(command, capture_output=True, text=True, cwd=ROOT)
        assert result.returncode == 2


def run_tests() -> None:
    test_passes_project_documentation()
    test_rejects_legacy_repository_identity()
    test_rejects_stable_stage_drift()
    test_cli_writes_outputs_and_fails_closed()


if __name__ == "__main__":
    run_tests()
    print("docs consistency guard tests: PASS")
