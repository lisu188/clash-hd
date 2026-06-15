#!/usr/bin/env python3
"""Fixture tests for the docs consistency guard."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "docs_consistency_guard.py"
sys.path.insert(0, str(ROOT / "tools"))

import docs_consistency_guard  # noqa: E402


STABLE_STAGE = (
    "gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-"
    "presentbounds-minimapright-dynvswitch"
)
RIGHT_BOTTOM_STAGE = STABLE_STAGE + "-rightbottomcompose"
CASTLE_STAGE = STABLE_STAGE + "-castlecenter-all"
MANUAL_IDS = list(docs_consistency_guard.EXPECTED_MANUAL_TARGET_IDS)


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def surface(path: Path, run: str) -> str:
    file_path = path / run / "surface.png"
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_bytes(b"\x89PNG\r\n\x1a\n")
    return str(file_path)


def source_payloads(
    fixture: Path,
    *,
    boundary_counts=(6, 34, 40),
    boundary_passed=True,
    rb_status="validation_stage_only",
    rb_passed=True,
    hd_smoke_has_post_owner_screenshots=True,
) -> argparse.Namespace:
    captures = fixture / "captures"
    screenshots = {
        "normal_post_owner": surface(captures, "cdb-surface-dump-20260506-190037"),
        "forced_visible_post_owner": surface(captures, "cdb-surface-dump-20260506-201114"),
        "right_bottom_owner_route": surface(captures, "cdb-surface-dump-20260513-112339"),
        "right_bottom_compose_probe": surface(captures, "cdb-surface-dump-20260513-115303"),
        "right_bottom_compose_patch": surface(captures, "cdb-surface-dump-20260513-120712"),
        "right_bottom_compose_fullstart_route": surface(captures, "cdb-surface-dump-20260513-122928"),
        "right_bottom_compose_normal_gate": surface(captures, "cdb-surface-dump-20260513-121513"),
        "right_bottom_compose_ui_probe": surface(captures, "cdb-surface-dump-20260513-122200"),
        "right_bottom_grid_hit": surface(captures, "cdb-surface-dump-20260514-140601"),
    }

    refresh_json = fixture / "current-evidence-refresh-current.json"
    boundary_json = fixture / "no-popup-boundary-guard-current.json"
    manual_checklist_json = fixture / "manual-directinput-validation-checklist-current.json"
    manual_template_json = fixture / "manual-directinput-proof-template-report-current.json"
    stable_json = fixture / "stable-stage-guard-current.json"
    rb_matrix_json = fixture / "right-bottom-compose-evidence-current.json"
    rb_decision_json = fixture / "right-bottom-compose-promotion-decision-current.json"
    castle_matrix_json = fixture / "castle-overview-evidence-current.json"
    castle_decision_json = fixture / "castle-overview-promotion-decision-current.json"
    hd_smoke_json = fixture / "hd-map-smoke-current.json"
    post_owner_evidence_json = fixture / "post-owner-evidence-current.json"
    no_popup_map_json = fixture / "no-popup-map-evidence-current.json"
    visible_json = fixture / "visible-runtime-launcher-guard-current.json"
    no_visible_json = fixture / "no-visible-runtime-guard-current.json"

    boundary = {
        "passed": boundary_passed,
        "required_guard_count": boundary_counts[0],
        "required_supporting_report_count": boundary_counts[1],
        "required_report_count": boundary_counts[2],
        "failures": [] if boundary_passed else ["fixture boundary failure"],
    }
    write_json(boundary_json, boundary)
    write_json(
        refresh_json,
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
                    "passed": boundary_passed,
                    "summary": boundary,
                },
                "visible_runtime_launcher_guard": {
                    "passed": True,
                    "summary": {
                        "script_count": 12,
                        "passing_script_count": 12,
                        "inventory_risky_script_count": 15,
                        "inventory_unclassified_risky_script_count": 0,
                        "guard_policy": (
                            "legacy launchers require -AllowVisibleRuntime after "
                            "explicit user approval"
                        ),
                    },
                },
                "no_visible_runtime_guard": {
                    "passed": True,
                    "summary": {"run_count": 19, "hidden_run_count": 19},
                },
                **{
                    name: {"passed": True, "screenshot": path}
                    for name, path in screenshots.items()
                    if name not in {"normal_post_owner", "forced_visible_post_owner"}
                },
            },
        },
    )
    write_json(
        manual_checklist_json,
        {
            "passed": True,
            "status": "pending_manual_validation",
            "no_popup_operator_preference": docs_consistency_guard.NO_POPUP_PREFERENCE,
            "visible_runtime_requires_approval": True,
            "manual_proof_valid": False,
            "promotion_ready": False,
            "stable_stage_should_change": False,
            "items": [{"id": item_id, "status": "pending_manual"} for item_id in MANUAL_IDS],
            "summary": {
                "item_count": 5,
                "pending_count": 5,
                "pending_ids": MANUAL_IDS,
                "promotion_ready": False,
                "stable_stage_should_change": False,
            },
        },
    )
    write_json(
        manual_template_json,
        {
            "passed": True,
            "required_ids": MANUAL_IDS,
            "checked_template_ids": MANUAL_IDS,
        },
    )
    write_json(
        stable_json,
        {
            "passed": True,
            "current_stable_stage": STABLE_STAGE,
            "patcher_default_stage": STABLE_STAGE,
        },
    )
    write_json(
        rb_matrix_json,
        {
            "passed": rb_passed,
            "promotion_status": rb_status,
            "stable_stage_should_change": False,
            "validation_stage": RIGHT_BOTTOM_STAGE,
            "checks": {
                "right_bottom_compose_normal_gate": {
                    "summary": {
                        "active_cells": 108,
                        "blank_active_cells": 13,
                        "visibility_unexplained_blank_cells": 0,
                        "visibility_zero": 13,
                    }
                }
            },
            "key_evidence": {
                "controlled_grid_hit_ok": True,
                "controlled_grid_entry": [450, 73],
                "controlled_grid_result": 0,
                "route_timing_failure_exit_count": 0,
                "route_timing_av_count": 0,
            },
        },
    )
    write_json(
        rb_decision_json,
        {
            "passed": rb_passed,
            "decision": "defer_stable_promotion",
            "stable_stage_should_change": False,
            "validation_stage": RIGHT_BOTTOM_STAGE,
        },
    )
    write_json(
        castle_matrix_json,
        {
            "passed": True,
            "stage": "castlecenter-all",
            "promotion_status": "validation_stage_only",
            "checks": {
                "patch_stage": {
                    "resolved_stage": CASTLE_STAGE,
                    "patches": {"patched": 134, "original": 0, "unexpected": 0, "total": 134},
                }
            },
        },
    )
    write_json(
        castle_decision_json,
        {
            "passed": True,
            "decision": "defer_stable_promotion",
            "stable_stage_should_change": False,
            "validation_stage": "castlecenter-all",
            "resolved_validation_stage": CASTLE_STAGE,
            "proof": {
                "visible_multihit_target_count": 3,
                "dormant_multihit_target_count": 4,
            },
        },
    )
    hd_smoke_payload = {"passed": True, "post_owner_evidence": {}}
    if hd_smoke_has_post_owner_screenshots:
        hd_smoke_payload["post_owner_evidence"] = {
            "normal": {"screenshot": screenshots["normal_post_owner"]},
            "forced_visible": {"screenshot": screenshots["forced_visible_post_owner"]},
        }
    write_json(hd_smoke_json, hd_smoke_payload)
    write_json(
        post_owner_evidence_json,
        {
            "passed": True,
            "normal": {"screenshot": screenshots["normal_post_owner"]},
            "forced_visible": {"screenshot": screenshots["forced_visible_post_owner"]},
        },
    )
    write_json(
        no_popup_map_json,
        {
            "passed": True,
            "normal": {
                "run": "captures\\cdb-surface-dump-20260429-140916",
                "blank_active_count": 13,
                "unexplained_blank_count": 0,
                "visibility_status_counts": {"visibility_zero": 13},
            },
            "forced_visible": {
                "run": "captures\\cdb-surface-dump-20260429-135242",
                "blank_active_count": 0,
                "vedge_visret_nonzero_count": 54,
                "vedge_post_nonblack_count": 54,
            },
        },
    )
    write_json(
        visible_json,
        {
            "passed": True,
            "script_count": 12,
            "passing_script_count": 12,
            "guard_policy": "requires -AllowVisibleRuntime after explicit user approval",
            "inventory": {"risky_script_count": 15, "unclassified_risky_script_count": 0},
        },
    )
    write_json(
        no_visible_json,
        {"passed": True, "run_count": 19, "hidden_run_count": 19},
    )

    codex_doc = fixture / "codex.md"
    readme_doc = fixture / "readme.md"
    evidence_doc = fixture / "evidence.md"
    wiki_doc = fixture / "wiki.md"
    render_docs(
        [codex_doc, readme_doc, evidence_doc, wiki_doc],
        boundary_counts=(6, 34, 40),
        screenshots=screenshots,
        rb_status="validation_stage_only",
    )

    return argparse.Namespace(
        refresh_json=refresh_json,
        boundary_json=boundary_json,
        manual_checklist_json=manual_checklist_json,
        manual_template_json=manual_template_json,
        stable_stage_json=stable_json,
        right_bottom_matrix_json=rb_matrix_json,
        right_bottom_decision_json=rb_decision_json,
        castle_matrix_json=castle_matrix_json,
        castle_decision_json=castle_decision_json,
        hd_map_smoke_json=hd_smoke_json,
        post_owner_evidence_json=post_owner_evidence_json,
        no_popup_map_json=no_popup_map_json,
        visible_runtime_json=visible_json,
        no_visible_runtime_json=no_visible_json,
        evidence_index=evidence_doc,
        codex_loop_docs=(codex_doc,),
        readme_progress_docs=(readme_doc,),
        wiki_summary_docs=(wiki_doc,),
    )


def render_docs(paths: list[Path], *, boundary_counts: tuple[int, int, int], screenshots: dict[str, str], rb_status: str) -> None:
    screenshot_lines = "\n".join(f"![{label}]({path})" for label, path in screenshots.items())
    text = f"""
Stable stage `{STABLE_STAGE}`.
Manual DirectInput validation checklist: PASS, five remaining manual targets,
all five required manual target IDs, all five targets pending.
Current checklist entries are stable menu load, stable HD map input,
right-bottom validation-stage input, castle barracks centered input, and full
castle overview centered input.
No-popup hidden-desktop evidence is preferred; visible/manual runs require
explicit user approval and `-AllowVisibleRuntime`.
Do not launch Clash95, CDB, wrappers, PowerShell harnesses, or visible windows
unless the user explicitly approves.
The `rightbottomcompose` stage is validation-only with
`promotion_status={rb_status}` and `stable_stage_should_change=False`.
The `castlecenter-all` matrix remains validation-stage only with
`promotion_status=validation_stage_only` and `stable_stage_should_change=False`.
The no-popup boundary guard reports PASS with
`required_guard_count={boundary_counts[0]}`,
`required_supporting_report_count={boundary_counts[1]}`, and
`required_report_count={boundary_counts[2]}`.
The no-popup map evidence has 13 blank active cells, zero unexplained blanks,
and forced-visible zero active blank cells. The right-bottom normal gate has
108 active cells, 13 blank active cells, zero unexplained blanks, and
visibility_zero=13.
{screenshot_lines}
"""
    for path in paths:
        write_text(path, text)


def run_script(args: argparse.Namespace, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--refresh-json",
            str(args.refresh_json),
            "--boundary-json",
            str(args.boundary_json),
            "--manual-checklist-json",
            str(args.manual_checklist_json),
            "--manual-template-json",
            str(args.manual_template_json),
            "--stable-stage-json",
            str(args.stable_stage_json),
            "--right-bottom-matrix-json",
            str(args.right_bottom_matrix_json),
            "--right-bottom-decision-json",
            str(args.right_bottom_decision_json),
            "--castle-matrix-json",
            str(args.castle_matrix_json),
            "--castle-decision-json",
            str(args.castle_decision_json),
            "--hd-map-smoke-json",
            str(args.hd_map_smoke_json),
            "--post-owner-evidence-json",
            str(args.post_owner_evidence_json),
            "--no-popup-map-json",
            str(args.no_popup_map_json),
            "--visible-runtime-json",
            str(args.visible_runtime_json),
            "--no-visible-runtime-json",
            str(args.no_visible_runtime_json),
            "--evidence-index",
            str(args.evidence_index),
            "--codex-loop-doc",
            str(args.codex_loop_docs[0]),
            "--readme-progress-doc",
            str(args.readme_progress_docs[0]),
            "--wiki-summary-doc",
            str(args.wiki_summary_docs[0]),
            *extra,
        ],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def test_good_fixture(fixture: Path) -> None:
    args = source_payloads(fixture)
    guard = docs_consistency_guard.build_guard(args)
    assert guard["passed"] is True, guard


def test_post_owner_screenshot_fallback(fixture: Path) -> None:
    args = source_payloads(fixture, hd_smoke_has_post_owner_screenshots=False)
    guard = docs_consistency_guard.build_guard(args)
    assert guard["passed"] is True, guard
    screenshots = guard["facts"]["screenshots"]
    assert screenshots["normal_post_owner"].endswith("cdb-surface-dump-20260506-190037\\surface.png")
    assert screenshots["forced_visible_post_owner"].endswith("cdb-surface-dump-20260506-201114\\surface.png")


def test_stale_boundary_counts_fail(fixture: Path) -> None:
    args = source_payloads(fixture, boundary_counts=(7, 35, 42))
    guard = docs_consistency_guard.build_guard(args)
    assert guard["passed"] is False, guard
    assert any("boundary counts" in failure for failure in guard["failures"]), guard


def test_stale_boundary_status_fails(fixture: Path) -> None:
    args = source_payloads(fixture, boundary_passed=False)
    guard = docs_consistency_guard.build_guard(args)
    assert guard["passed"] is False, guard
    assert any("no-popup boundary guard is not passing" in failure for failure in guard["failures"]), guard


def test_stale_validation_status_fails(fixture: Path) -> None:
    args = source_payloads(fixture, rb_status="promoted_to_stable")
    guard = docs_consistency_guard.build_guard(args)
    assert guard["passed"] is False, guard
    assert any("right-bottom promotion status" in failure for failure in guard["failures"]), guard


def test_nonpassing_right_bottom_defer_remains_consistent(fixture: Path) -> None:
    args = source_payloads(fixture, rb_passed=False)
    guard = docs_consistency_guard.build_guard(args)
    assert guard["passed"] is True, guard


def test_cli_writes_outputs_and_fails_closed(fixture: Path) -> None:
    args = source_payloads(fixture / "good")
    out_json = fixture / "out" / "docs.json"
    out_md = fixture / "out" / "docs.md"
    good = run_script(
        args,
        "--write-json",
        str(out_json),
        "--write-markdown",
        str(out_md),
        "--require-pass",
    )
    assert good.returncode == 0, good.stdout + good.stderr
    assert json.loads(out_json.read_text(encoding="utf-8"))["passed"] is True
    assert "- Overall: PASS" in out_md.read_text(encoding="utf-8")

    bad_args = source_payloads(fixture / "bad", boundary_counts=(8, 34, 41))
    bad_json = fixture / "bad-out" / "docs.json"
    bad_md = fixture / "bad-out" / "docs.md"
    bad = run_script(
        bad_args,
        "--write-json",
        str(bad_json),
        "--write-markdown",
        str(bad_md),
        "--require-pass",
    )
    assert bad.returncode == 2, bad.stdout + bad.stderr
    assert json.loads(bad_json.read_text(encoding="utf-8"))["passed"] is False
    assert "- Overall: FAIL" in bad_md.read_text(encoding="utf-8")


def run_tests() -> None:
    fixture = ROOT / ".codex-loop" / "tmp-tests" / "docs-consistency-guard-fixture"
    shutil.rmtree(fixture, ignore_errors=True)
    fixture.mkdir(parents=True)
    try:
        test_good_fixture(fixture / "good")
        test_post_owner_screenshot_fallback(fixture / "post-owner-fallback")
        test_stale_boundary_counts_fail(fixture / "stale-counts")
        test_stale_boundary_status_fails(fixture / "stale-status")
        test_stale_validation_status_fails(fixture / "stale-validation")
        test_nonpassing_right_bottom_defer_remains_consistent(fixture / "right-bottom-nonpassing")
        test_cli_writes_outputs_and_fails_closed(fixture / "cli")
    finally:
        shutil.rmtree(fixture, ignore_errors=True)


def main() -> int:
    run_tests()
    print("docs consistency guard tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
