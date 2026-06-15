#!/usr/bin/env python3
"""Check that handoff docs agree with generated current-evidence facts.

This is a repo-only guard. It reads JSON/Markdown artifacts and source notes;
it does not launch Clash95, CDB, wrappers, PowerShell harnesses, or visible
windows.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_REFRESH_JSON = Path("captures/current/current-evidence-refresh-current.json")
DEFAULT_BOUNDARY_JSON = Path("captures/current/no-popup-boundary-guard-current.json")
DEFAULT_MANUAL_CHECKLIST_JSON = Path("captures/current/manual-directinput-validation-checklist-current.json")
DEFAULT_MANUAL_TEMPLATE_JSON = Path("captures/current/manual-directinput-proof-template-report-current.json")
DEFAULT_STABLE_STAGE_JSON = Path("captures/current/stable-stage-guard-current.json")
DEFAULT_RIGHT_BOTTOM_MATRIX_JSON = Path("captures/current/right-bottom-compose-evidence-current.json")
DEFAULT_RIGHT_BOTTOM_DECISION_JSON = Path("captures/current/right-bottom-compose-promotion-decision-current.json")
DEFAULT_CASTLE_MATRIX_JSON = Path("captures/current/castle-overview-evidence-current.json")
DEFAULT_CASTLE_DECISION_JSON = Path("captures/current/castle-overview-promotion-decision-current.json")
DEFAULT_HD_MAP_SMOKE_JSON = Path("captures/current/hd-map-smoke-current.json")
DEFAULT_NO_POPUP_MAP_JSON = Path("captures/current/no-popup-map-evidence-current.json")
DEFAULT_VISIBLE_RUNTIME_JSON = Path("captures/current/visible-runtime-launcher-guard-current.json")
DEFAULT_NO_VISIBLE_RUNTIME_JSON = Path("captures/current/no-visible-runtime-guard-current.json")
DEFAULT_EVIDENCE_INDEX = Path("captures/current/hd-map-evidence-current.md")
DEFAULT_JSON = Path("captures/current/docs-consistency-current.json")
DEFAULT_MD = Path("captures/current/docs-consistency-current.md")

DEFAULT_CODEX_LOOP_DOCS = (
    Path(".codex-loop/NEXT.md"),
    Path(".codex-loop/STATE.md"),
    Path(".codex-loop/TASKS.md"),
)
DEFAULT_README_PROGRESS_DOCS = (
    Path("README.md"),
    Path("docs/hd/HD_MOD_PROGRESS.md"),
)
DEFAULT_WIKI_SUMMARY_DOCS = (
    Path("wiki/sources/current-hd-map-evidence.md"),
    Path("wiki/syntheses/current-clash95-hd-state.md"),
    Path("wiki/syntheses/hd-map-evidence-chain.md"),
    Path("wiki/concepts/active-hd-map-stage.md"),
    Path("wiki/concepts/no-popup-surface-dump.md"),
    Path("wiki/questions/what-manual-directinput-validation-remains.md"),
    Path("wiki/syntheses/right-bottom-ui-and-bottom-tooltip-recovery.md"),
)

EXPECTED_MANUAL_TARGET_IDS = (
    "stable_menu_load",
    "stable_hd_map_input",
    "right_bottom_validation_input",
    "castle_barracks_centered_input",
    "castle_overview_centered_input",
)
MANUAL_TARGET_IDS = list(EXPECTED_MANUAL_TARGET_IDS)

RIGHT_BOTTOM_STAGE_SUFFIX = "rightbottomcompose"
CASTLE_STAGE_SUFFIX = "castlecenter-all"
NO_POPUP_PREFERENCE = (
    "Do not launch Clash95, CDB, wrappers, PowerShell harnesses, or visible windows "
    "unless the user explicitly approves."
)
RUNTIME_POLICY = (
    "repo-only docs/source inspection; does not launch Clash95, CDB, wrappers, "
    "PowerShell harnesses, or visible windows"
)


def repo_path(path: Path) -> Path:
    if path.is_absolute():
        return path
    return REPO_ROOT / path


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(repo_path(path).read_text(encoding="utf-8-sig"))


def read_text(path: Path) -> str:
    return repo_path(path).read_text(encoding="utf-8-sig", errors="replace")


def status_text(passed: bool) -> str:
    return "PASS" if passed else "FAIL"


def check_record(passed: bool, summary: dict[str, Any], failures: list[str] | None = None) -> dict[str, Any]:
    return {
        "passed": passed,
        "summary": summary,
        "failures": failures or [],
    }


def normalize_text(value: str) -> str:
    return value.replace("\\", "/").lower()


def contains_literal(text: str, needle: str | None) -> bool:
    return bool(needle) and normalize_text(needle) in normalize_text(text)


def contains_all(text: str, needles: list[str]) -> bool:
    return all(contains_literal(text, needle) for needle in needles)


def path_variants(path_value: str) -> list[str]:
    normalized = path_value.replace("\\", "/")
    variants = {normalized}
    canonical = canonical_capture_path(path_value)
    if canonical:
        variants.add(canonical.replace("\\", "/"))
    marker = "/captures/"
    if marker in normalized:
        variants.add("captures/" + normalized.split(marker, 1)[1])
    if normalized.endswith("/surface.png"):
        variants.add(normalized.rsplit("/", 1)[0])
    return sorted(variants, key=len, reverse=True)


def canonical_capture_path(path_value: str | None) -> str | None:
    if not path_value:
        return path_value
    path = Path(path_value)
    if path.exists():
        return str(path.resolve())
    normalized = path_value.replace("\\", "/")
    lower = normalized.lower()
    marker = "/captures/"
    suffix: str | None = None
    if marker in lower:
        suffix = normalized[lower.index(marker) + len(marker) :]
    elif lower.startswith("captures/"):
        suffix = normalized[len("captures/") :]
    if not suffix:
        return path_value
    candidates = [REPO_ROOT / "captures" / suffix]
    if suffix.lower().startswith("cdb-surface-dump-"):
        candidates.insert(0, REPO_ROOT / "captures" / "archive" / suffix)
    for candidate in candidates:
        if candidate.exists():
            return str(candidate.resolve())
    return path_value


def contains_path(text: str, path_value: str | None) -> bool:
    if not path_value:
        return False
    text_norm = normalize_text(text)
    return any(normalize_text(variant) in text_norm for variant in path_variants(path_value))


def nested_get(value: dict[str, Any], path: list[str], default: Any = None) -> Any:
    current: Any = value
    for key in path:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return current


def refresh_summary(refresh: dict[str, Any], name: str) -> dict[str, Any]:
    return nested_get(refresh, ["checks", name, "summary"], {}) or {}


def refresh_check(refresh: dict[str, Any], name: str) -> dict[str, Any]:
    return nested_get(refresh, ["checks", name], {}) or {}


def screenshot_from_refresh(refresh: dict[str, Any], name: str) -> str | None:
    return canonical_capture_path(refresh_check(refresh, name).get("screenshot"))


def build_facts(args: argparse.Namespace) -> dict[str, Any]:
    refresh = getattr(args, "refresh_payload", None) or load_json(args.refresh_json)
    boundary = getattr(args, "boundary_payload", None) or load_json(args.boundary_json)
    checklist = load_json(args.manual_checklist_json)
    template = load_json(args.manual_template_json)
    stable = load_json(args.stable_stage_json)
    rb_matrix = load_json(args.right_bottom_matrix_json)
    rb_decision = load_json(args.right_bottom_decision_json)
    castle_matrix = load_json(args.castle_matrix_json)
    castle_decision = load_json(args.castle_decision_json)
    hd_smoke = load_json(args.hd_map_smoke_json)
    no_popup_map = load_json(args.no_popup_map_json)
    visible = load_json(args.visible_runtime_json)
    no_visible = load_json(args.no_visible_runtime_json)

    stable_summary = refresh_summary(refresh, "stable_stage_guard")
    manual_summary = checklist.get("summary") or {}
    boundary_summary = refresh_summary(refresh, "no_popup_boundary_guard")
    visible_summary = refresh_summary(refresh, "visible_runtime_launcher_guard")
    no_visible_summary = refresh_summary(refresh, "no_visible_runtime_guard")

    screenshots = {
        "normal_post_owner": nested_get(hd_smoke, ["post_owner_evidence", "normal", "screenshot"]),
        "forced_visible_post_owner": nested_get(
            hd_smoke, ["post_owner_evidence", "forced_visible", "screenshot"]
        ),
        "right_bottom_owner_route": screenshot_from_refresh(refresh, "right_bottom_owner_route"),
        "right_bottom_compose_probe": screenshot_from_refresh(refresh, "right_bottom_compose_probe"),
        "right_bottom_compose_patch": screenshot_from_refresh(refresh, "right_bottom_compose_patch"),
        "right_bottom_compose_fullstart_route": screenshot_from_refresh(
            refresh, "right_bottom_compose_fullstart_route"
        ),
        "right_bottom_compose_normal_gate": screenshot_from_refresh(
            refresh, "right_bottom_compose_normal_gate"
        ),
        "right_bottom_compose_ui_probe": screenshot_from_refresh(refresh, "right_bottom_compose_ui_probe"),
        "right_bottom_grid_hit": screenshot_from_refresh(refresh, "right_bottom_grid_hit"),
    }
    screenshots = {name: canonical_capture_path(path) for name, path in screenshots.items()}

    return {
        "refresh_passed": refresh.get("passed") is True,
        "stable_stage": stable_summary.get("current_stable_stage")
        or stable.get("current_stable_stage"),
        "patcher_default_stage": stable_summary.get("patcher_default_stage")
        or stable.get("patcher_default_stage"),
        "manual_target_ids": [item.get("id") for item in checklist.get("items", [])],
        "manual_pending_ids": manual_summary.get("pending_ids") or [],
        "template_required_ids": template.get("required_ids") or [],
        "manual_status": checklist.get("status"),
        "manual_item_count": manual_summary.get("item_count"),
        "manual_pending_count": manual_summary.get("pending_count"),
        "manual_proof_valid": checklist.get("manual_proof_valid"),
        "manual_promotion_ready": checklist.get("promotion_ready"),
        "manual_stable_stage_should_change": checklist.get("stable_stage_should_change"),
        "no_popup_preference": checklist.get("no_popup_operator_preference"),
        "visible_runtime_requires_approval": checklist.get("visible_runtime_requires_approval"),
        "visible_runtime_guard": {
            "passed": visible.get("passed"),
            "script_count": visible_summary.get("script_count", visible.get("script_count")),
            "passing_script_count": visible_summary.get(
                "passing_script_count", visible.get("passing_script_count")
            ),
            "guard_policy": visible_summary.get("guard_policy", visible.get("guard_policy")),
            "inventory_risky_script_count": visible_summary.get(
                "inventory_risky_script_count",
                nested_get(visible, ["inventory", "risky_script_count"]),
            ),
            "inventory_unclassified_risky_script_count": visible_summary.get(
                "inventory_unclassified_risky_script_count",
                nested_get(visible, ["inventory", "unclassified_risky_script_count"]),
            ),
        },
        "no_visible_runtime_guard": {
            "passed": no_visible.get("passed"),
            "run_count": no_visible_summary.get("run_count", no_visible.get("run_count")),
            "hidden_run_count": no_visible_summary.get(
                "hidden_run_count", no_visible.get("hidden_run_count")
            ),
        },
        "no_popup_boundary": {
            "passed": boundary.get("passed"),
            "refresh_passed": refresh_check(refresh, "no_popup_boundary_guard").get("passed"),
            "required_guard_count": boundary.get("required_guard_count"),
            "required_supporting_report_count": boundary.get("required_supporting_report_count"),
            "required_report_count": boundary.get("required_report_count"),
            "summary_required_guard_count": boundary_summary.get("required_guard_count"),
            "summary_required_supporting_report_count": boundary_summary.get(
                "required_supporting_report_count"
            ),
            "summary_required_report_count": boundary_summary.get("required_report_count"),
        },
        "no_popup_map": {
            "passed": no_popup_map.get("passed"),
            "normal_run": nested_get(no_popup_map, ["normal", "run"]),
            "normal_blank_active_count": nested_get(no_popup_map, ["normal", "blank_active_count"]),
            "normal_unexplained_blank_count": nested_get(no_popup_map, ["normal", "unexplained_blank_count"]),
            "normal_visibility_zero": nested_get(
                no_popup_map, ["normal", "visibility_status_counts", "visibility_zero"]
            ),
            "forced_run": nested_get(no_popup_map, ["forced_visible", "run"]),
            "forced_blank_active_count": nested_get(no_popup_map, ["forced_visible", "blank_active_count"]),
            "forced_visret_nonzero_count": nested_get(
                no_popup_map, ["forced_visible", "vedge_visret_nonzero_count"]
            ),
            "forced_post_nonblack_count": nested_get(
                no_popup_map, ["forced_visible", "vedge_post_nonblack_count"]
            ),
        },
        "right_bottom": {
            "matrix_passed": rb_matrix.get("passed"),
            "promotion_status": rb_matrix.get("promotion_status"),
            "stable_stage_should_change": rb_matrix.get("stable_stage_should_change"),
            "decision_passed": rb_decision.get("passed"),
            "decision": rb_decision.get("decision"),
            "decision_stable_stage_should_change": rb_decision.get("stable_stage_should_change"),
            "validation_stage": rb_matrix.get("validation_stage") or rb_decision.get("validation_stage"),
            "normal_active_cells": nested_get(
                rb_matrix, ["checks", "right_bottom_compose_normal_gate", "summary", "active_cells"]
            ),
            "normal_blank_active_cells": nested_get(
                rb_matrix, ["checks", "right_bottom_compose_normal_gate", "summary", "blank_active_cells"]
            ),
            "normal_unexplained_blank_cells": nested_get(
                rb_matrix,
                ["checks", "right_bottom_compose_normal_gate", "summary", "visibility_unexplained_blank_cells"],
            ),
            "normal_visibility_zero": nested_get(
                rb_matrix, ["checks", "right_bottom_compose_normal_gate", "summary", "visibility_zero"]
            ),
            "grid_hit_ok": nested_get(rb_matrix, ["key_evidence", "controlled_grid_hit_ok"]),
            "grid_entry": nested_get(rb_matrix, ["key_evidence", "controlled_grid_entry"]),
            "grid_result": nested_get(rb_matrix, ["key_evidence", "controlled_grid_result"]),
            "route_timing_failure_exit_count": nested_get(
                rb_matrix, ["key_evidence", "route_timing_failure_exit_count"]
            ),
            "route_timing_av_count": nested_get(rb_matrix, ["key_evidence", "route_timing_av_count"]),
        },
        "castle": {
            "matrix_passed": castle_matrix.get("passed"),
            "promotion_status": castle_matrix.get("promotion_status"),
            "decision_passed": castle_decision.get("passed"),
            "decision": castle_decision.get("decision"),
            "decision_stable_stage_should_change": castle_decision.get("stable_stage_should_change"),
            "stage": castle_matrix.get("stage") or castle_decision.get("validation_stage"),
            "resolved_stage": nested_get(castle_matrix, ["checks", "patch_stage", "resolved_stage"])
            or castle_decision.get("resolved_validation_stage"),
            "patch_total": nested_get(castle_matrix, ["checks", "patch_stage", "patches", "total"]),
            "patch_patched": nested_get(castle_matrix, ["checks", "patch_stage", "patches", "patched"]),
            "patch_original": nested_get(castle_matrix, ["checks", "patch_stage", "patches", "original"]),
            "patch_unexpected": nested_get(castle_matrix, ["checks", "patch_stage", "patches", "unexpected"]),
            "visible_target_count": nested_get(castle_decision, ["proof", "visible_multihit_target_count"]),
            "dormant_target_count": nested_get(castle_decision, ["proof", "dormant_multihit_target_count"]),
        },
        "screenshots": screenshots,
    }


def generated_fact_checks(facts: dict[str, Any]) -> dict[str, Any]:
    checks: dict[str, Any] = {}

    failures: list[str] = []
    for label in ("manual_target_ids", "manual_pending_ids", "template_required_ids"):
        if tuple(facts.get(label) or []) != EXPECTED_MANUAL_TARGET_IDS:
            failures.append(
                f"{label} is {facts.get(label)}, expected {list(EXPECTED_MANUAL_TARGET_IDS)}"
            )
    if facts.get("manual_item_count") != len(EXPECTED_MANUAL_TARGET_IDS):
        failures.append(f"manual item_count is {facts.get('manual_item_count')}, expected 5")
    if facts.get("manual_pending_count") != len(EXPECTED_MANUAL_TARGET_IDS):
        failures.append(f"manual pending_count is {facts.get('manual_pending_count')}, expected 5")
    if facts.get("manual_status") != "pending_manual_validation":
        failures.append(f"manual status is {facts.get('manual_status')}, expected pending_manual_validation")
    if facts.get("manual_proof_valid") is not False or facts.get("manual_promotion_ready") is not False:
        failures.append("manual proof/promotion flags no longer show a pending non-promoting boundary")
    checks["manual_target_ids"] = check_record(
        not failures,
        {
            "expected_ids": list(EXPECTED_MANUAL_TARGET_IDS),
            "manual_target_ids": facts.get("manual_target_ids"),
            "template_required_ids": facts.get("template_required_ids"),
            "manual_status": facts.get("manual_status"),
            "manual_item_count": facts.get("manual_item_count"),
            "manual_pending_count": facts.get("manual_pending_count"),
        },
        failures,
    )

    failures = []
    if not facts.get("stable_stage"):
        failures.append("stable stage is missing from generated facts")
    if facts.get("stable_stage") != facts.get("patcher_default_stage"):
        failures.append(
            f"stable stage {facts.get('stable_stage')} differs from patcher default "
            f"{facts.get('patcher_default_stage')}"
        )
    checks["stable_stage"] = check_record(
        not failures,
        {
            "stable_stage": facts.get("stable_stage"),
            "patcher_default_stage": facts.get("patcher_default_stage"),
        },
        failures,
    )

    failures = []
    if facts.get("no_popup_preference") != NO_POPUP_PREFERENCE:
        failures.append("no-popup operator preference text drifted")
    if facts.get("visible_runtime_requires_approval") is not True:
        failures.append("visible runtime no longer requires approval in the manual checklist")
    visible = facts["visible_runtime_guard"]
    if visible.get("passed") is not True:
        failures.append("visible runtime launcher guard is not passing")
    if visible.get("script_count") != visible.get("passing_script_count"):
        failures.append("visible runtime launcher guard has non-passing scripts")
    policy = visible.get("guard_policy") or ""
    if "-AllowVisibleRuntime" not in policy or "approval" not in policy.lower():
        failures.append("visible runtime guard policy no longer carries approval wording")
    no_visible = facts["no_visible_runtime_guard"]
    if no_visible.get("passed") is not True:
        failures.append("no-visible runtime guard is not passing")
    if no_visible.get("run_count") != no_visible.get("hidden_run_count"):
        failures.append("not all referenced runtime runs are hidden-desktop runs")
    checks["runtime_boundary"] = check_record(
        not failures,
        {
            "no_popup_preference": facts.get("no_popup_preference"),
            "visible_runtime_requires_approval": facts.get("visible_runtime_requires_approval"),
            "visible_script_count": visible.get("script_count"),
            "visible_passing_script_count": visible.get("passing_script_count"),
            "no_visible_run_count": no_visible.get("run_count"),
            "no_visible_hidden_run_count": no_visible.get("hidden_run_count"),
        },
        failures,
    )

    boundary = facts["no_popup_boundary"]
    failures = []
    if boundary.get("passed") is not True or boundary.get("refresh_passed") is not True:
        failures.append("no-popup boundary guard is not passing")
    for key in (
        "required_guard_count",
        "required_supporting_report_count",
        "required_report_count",
    ):
        summary_key = f"summary_{key}"
        if boundary.get(key) != boundary.get(summary_key):
            failures.append(f"{key} differs between boundary JSON and refresh summary")
    checks["boundary_counts"] = check_record(not failures, boundary, failures)

    no_popup = facts["no_popup_map"]
    rb = facts["right_bottom"]
    failures = []
    if no_popup.get("passed") is not True:
        failures.append("no-popup map evidence matrix is not passing")
    if no_popup.get("normal_blank_active_count") != no_popup.get("normal_visibility_zero"):
        failures.append("no-popup normal blank-active count does not match visibility_zero count")
    if no_popup.get("normal_unexplained_blank_count") != 0:
        failures.append("no-popup normal run has unexplained blank cells")
    if no_popup.get("forced_blank_active_count") != 0:
        failures.append("no-popup forced-visible run has active blank cells")
    if rb.get("normal_unexplained_blank_cells") != 0:
        failures.append("right-bottom normal gate has unexplained blank cells")
    if rb.get("normal_blank_active_cells") != rb.get("normal_visibility_zero"):
        failures.append("right-bottom normal blank-active count does not match visibility_zero count")
    checks["map_boundary_counts"] = check_record(
        not failures,
        {
            "no_popup": no_popup,
            "right_bottom_normal_active_cells": rb.get("normal_active_cells"),
            "right_bottom_normal_blank_active_cells": rb.get("normal_blank_active_cells"),
            "right_bottom_normal_unexplained_blank_cells": rb.get("normal_unexplained_blank_cells"),
            "right_bottom_normal_visibility_zero": rb.get("normal_visibility_zero"),
        },
        failures,
    )

    failures = []
    if rb.get("promotion_status") != "validation_stage_only":
        failures.append(
            f"right-bottom promotion status is {rb.get('promotion_status')}, expected validation_stage_only"
        )
    if rb.get("stable_stage_should_change") is not False:
        failures.append("right-bottom matrix would change stable stage")
    if rb.get("decision") != "defer_stable_promotion":
        failures.append(f"right-bottom decision is {rb.get('decision')}, expected defer_stable_promotion")
    if RIGHT_BOTTOM_STAGE_SUFFIX not in str(rb.get("validation_stage")):
        failures.append("right-bottom validation stage does not reference rightbottomcompose")
    castle = facts["castle"]
    if castle.get("matrix_passed") is not True or castle.get("decision_passed") is not True:
        failures.append("castle validation matrix/decision is not passing")
    if castle.get("promotion_status") != "validation_stage_only":
        failures.append(
            f"castle promotion status is {castle.get('promotion_status')}, expected validation_stage_only"
        )
    if castle.get("decision") != "defer_stable_promotion":
        failures.append(f"castle decision is {castle.get('decision')}, expected defer_stable_promotion")
    if castle.get("decision_stable_stage_should_change") is not False:
        failures.append("castle decision would change stable stage")
    if CASTLE_STAGE_SUFFIX not in str(castle.get("stage")) and CASTLE_STAGE_SUFFIX not in str(castle.get("resolved_stage")):
        failures.append("castle validation stage does not reference castlecenter-all")
    checks["validation_only_status"] = check_record(
        not failures,
        {"right_bottom": rb, "castle": castle},
        failures,
    )

    missing_screenshots = []
    for label, path_value in facts["screenshots"].items():
        if not path_value:
            missing_screenshots.append(f"{label}: missing path")
            continue
        if not repo_path(Path(path_value)).exists():
            missing_screenshots.append(f"{label}: missing file {path_value}")
    checks["screenshot_files"] = check_record(
        not missing_screenshots,
        {"screenshots": facts["screenshots"]},
        missing_screenshots,
    )

    return checks


def doc_group_text(paths: list[Path]) -> tuple[str, list[str]]:
    parts: list[str] = []
    failures: list[str] = []
    for path in paths:
        resolved = repo_path(path)
        if not resolved.exists():
            failures.append(f"missing doc: {path}")
            continue
        parts.append(read_text(path))
    return "\n".join(parts), failures


def contains_boundary_counts(text: str, boundary: dict[str, Any]) -> bool:
    guard = boundary.get("required_guard_count")
    supporting = boundary.get("required_supporting_report_count")
    total = boundary.get("required_report_count")
    exact_tokens = [
        f"required_guard_count={guard}",
        f"required_supporting_report_count={supporting}",
        f"required_report_count={total}",
    ]
    prose_tokens = [
        f"{guard} core",
        f"{supporting} supporting",
        f"{total} required",
    ]
    return contains_all(text, exact_tokens) or contains_all(text, prose_tokens)


def doc_group_checks(facts: dict[str, Any], doc_groups: dict[str, list[Path]]) -> dict[str, Any]:
    checks: dict[str, Any] = {}
    strict_boundary_groups = {"evidence_index", "wiki_summaries"}

    for name, paths in doc_groups.items():
        text, failures = doc_group_text(paths)
        summary: dict[str, Any] = {"paths": [str(path) for path in paths]}

        if not contains_literal(text, facts["stable_stage"]):
            failures.append(f"{name} does not mention stable stage {facts['stable_stage']}")

        manual_count_tokens = [
            "five remaining manual targets",
            "all five required",
            "five required manual",
            "all five targets",
        ]
        if not any(contains_literal(text, token) for token in manual_count_tokens):
            failures.append(f"{name} does not document the five manual-target boundary")
        if name == "wiki_summaries":
            readable_targets = [
                "stable menu load",
                "stable hd map input",
                "right-bottom validation",
                "castle barracks centered input",
                "castle overview centered input",
            ]
            if not all(contains_literal(text, token) for token in readable_targets):
                failures.append(f"{name} does not enumerate the current manual target meanings")

        has_no_popup = contains_literal(text, "no-popup")
        has_approval = contains_literal(text, "explicit user approval") or contains_literal(
            text, "explicitly approves"
        )
        has_visible_switch = contains_literal(text, "-AllowVisibleRuntime")
        if not has_no_popup or not (has_approval or has_visible_switch):
            failures.append(f"{name} does not preserve no-popup/visible-approval wording")

        if not contains_literal(text, RIGHT_BOTTOM_STAGE_SUFFIX) or not (
            contains_literal(text, "validation-only")
            or contains_literal(text, "validation_stage_only")
            or contains_literal(text, "validation-stage only")
        ):
            failures.append(f"{name} does not keep rightbottomcompose validation-only")
        if not contains_literal(text, CASTLE_STAGE_SUFFIX) or not (
            contains_literal(text, "validation-only")
            or contains_literal(text, "validation_stage_only")
            or contains_literal(text, "validation-stage only")
        ):
            failures.append(f"{name} does not keep castlecenter-all validation-only")
        if not contains_literal(text, "stable_stage_should_change=false"):
            failures.append(f"{name} does not document stable_stage_should_change=False")

        has_boundary_pass = contains_literal(text, "no-popup boundary") and contains_literal(text, "pass")
        if not has_boundary_pass:
            failures.append(f"{name} does not document no-popup boundary PASS status")
        if name in strict_boundary_groups and not contains_boundary_counts(
            text, facts["no_popup_boundary"]
        ):
            failures.append(f"{name} does not document current no-popup boundary counts")

        summary.update(
            {
                "stable_stage_found": contains_literal(text, facts["stable_stage"]),
                "no_popup_approval_found": has_no_popup and (has_approval or has_visible_switch),
                "boundary_pass_found": has_boundary_pass,
                "strict_boundary_counts_required": name in strict_boundary_groups,
                "strict_boundary_counts_found": contains_boundary_counts(
                    text, facts["no_popup_boundary"]
                ),
            }
        )
        checks[f"docs_{name}"] = check_record(not failures, summary, failures)

    return checks


def screenshot_doc_checks(facts: dict[str, Any], evidence_index: Path) -> dict[str, Any]:
    text, failures = doc_group_text([evidence_index])
    missing = []
    for label, path_value in facts["screenshots"].items():
        if not contains_path(text, path_value):
            missing.append(f"{label}: {path_value}")
    failures.extend(f"evidence index missing current screenshot path {item}" for item in missing)
    return {
        "docs_current_screenshot_paths": check_record(
            not failures,
            {
                "evidence_index": str(evidence_index),
                "screenshots": facts["screenshots"],
                "missing": missing,
            },
            failures,
        )
    }


def build_guard(args: argparse.Namespace) -> dict[str, Any]:
    facts = build_facts(args)
    checks = generated_fact_checks(facts)
    doc_groups = {
        "codex_loop": list(args.codex_loop_docs),
        "readme_progress": list(args.readme_progress_docs),
        "evidence_index": [args.evidence_index],
        "wiki_summaries": list(args.wiki_summary_docs),
    }
    checks.update(doc_group_checks(facts, doc_groups))
    checks.update(screenshot_doc_checks(facts, args.evidence_index))

    failures: list[str] = []
    for name, check in checks.items():
        if not check.get("passed"):
            failures.extend(f"{name}: {failure}" for failure in check.get("failures", []))

    return {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "passed": not failures,
        "runtime_policy": RUNTIME_POLICY,
        "guard_policy": (
            "generated current-evidence facts must agree with .codex-loop handoff docs, "
            "README/progress notes, the evidence index, and wiki summaries"
        ),
        "facts": facts,
        "doc_groups": {name: [str(path) for path in paths] for name, paths in doc_groups.items()},
        "checks": checks,
        "failures": failures,
    }


def print_guard(guard: dict[str, Any]) -> None:
    print(f"overall: {status_text(bool(guard.get('passed')))}")
    print(f"runtime-policy: {guard['runtime_policy']}")
    print(f"stable-stage: {guard['facts'].get('stable_stage')}")
    print(f"manual-target-ids: {guard['facts'].get('manual_target_ids')}")
    boundary = guard["facts"].get("no_popup_boundary", {})
    print(
        "boundary-counts: guards={guards} supporting={supporting} total={total}".format(
            guards=boundary.get("required_guard_count"),
            supporting=boundary.get("required_supporting_report_count"),
            total=boundary.get("required_report_count"),
        )
    )
    for name, check in guard["checks"].items():
        print(f"{name}: {status_text(bool(check.get('passed')))}")
    if guard["failures"]:
        print("failures:")
        for failure in guard["failures"]:
            print(f"  - {failure}")


def write_markdown(path: Path, guard: dict[str, Any]) -> None:
    facts = guard["facts"]
    boundary = facts["no_popup_boundary"]
    lines = [
        "# Docs Consistency Guard",
        "",
        f"- Overall: {status_text(bool(guard['passed']))}",
        f"- Generated: `{guard['generated_at']}`",
        f"- Runtime policy: {guard['runtime_policy']}",
        f"- Stable stage: `{facts.get('stable_stage')}`",
        f"- Manual target IDs: `{facts.get('manual_target_ids')}`",
        f"- No-popup preference: `{facts.get('no_popup_preference')}`",
        (
            "- No-popup boundary counts: "
            f"`required_guard_count={boundary.get('required_guard_count')}`, "
            f"`required_supporting_report_count={boundary.get('required_supporting_report_count')}`, "
            f"`required_report_count={boundary.get('required_report_count')}`"
        ),
        f"- Right-bottom status: `{facts['right_bottom'].get('promotion_status')}`",
        f"- Castle status: `{facts['castle'].get('promotion_status')}`",
        "",
        "## Checks",
        "",
    ]
    for name, check in guard["checks"].items():
        lines.append(f"- `{name}`: `{status_text(bool(check.get('passed')))}`")
        for failure in check.get("failures", []):
            lines.append(f"  - {failure}")
    lines.extend(["", "## Current Screenshot Paths", ""])
    for label, path_value in facts["screenshots"].items():
        lines.append(f"- `{label}`: `{path_value}`")
    if guard["failures"]:
        lines.extend(["", "## Failures", ""])
        lines.extend(f"- {failure}" for failure in guard["failures"])
    lines.append("")
    repo_path(path).parent.mkdir(parents=True, exist_ok=True)
    repo_path(path).write_text("\n".join(lines), encoding="utf-8")


def write_json(path: Path, guard: dict[str, Any]) -> None:
    repo_path(path).parent.mkdir(parents=True, exist_ok=True)
    repo_path(path).write_text(json.dumps(guard, indent=2) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh-json", type=Path, default=DEFAULT_REFRESH_JSON)
    parser.add_argument("--boundary-json", type=Path, default=DEFAULT_BOUNDARY_JSON)
    parser.add_argument("--manual-checklist-json", type=Path, default=DEFAULT_MANUAL_CHECKLIST_JSON)
    parser.add_argument("--manual-template-json", type=Path, default=DEFAULT_MANUAL_TEMPLATE_JSON)
    parser.add_argument("--stable-stage-json", type=Path, default=DEFAULT_STABLE_STAGE_JSON)
    parser.add_argument("--right-bottom-matrix-json", type=Path, default=DEFAULT_RIGHT_BOTTOM_MATRIX_JSON)
    parser.add_argument("--right-bottom-decision-json", type=Path, default=DEFAULT_RIGHT_BOTTOM_DECISION_JSON)
    parser.add_argument("--castle-matrix-json", type=Path, default=DEFAULT_CASTLE_MATRIX_JSON)
    parser.add_argument("--castle-decision-json", type=Path, default=DEFAULT_CASTLE_DECISION_JSON)
    parser.add_argument("--hd-map-smoke-json", type=Path, default=DEFAULT_HD_MAP_SMOKE_JSON)
    parser.add_argument("--no-popup-map-json", type=Path, default=DEFAULT_NO_POPUP_MAP_JSON)
    parser.add_argument("--visible-runtime-json", type=Path, default=DEFAULT_VISIBLE_RUNTIME_JSON)
    parser.add_argument("--no-visible-runtime-json", type=Path, default=DEFAULT_NO_VISIBLE_RUNTIME_JSON)
    parser.add_argument("--evidence-index", type=Path, default=DEFAULT_EVIDENCE_INDEX)
    parser.add_argument("--doc", type=Path, action="append", default=None)
    parser.add_argument("--codex-loop-doc", type=Path, action="append")
    parser.add_argument("--readme-progress-doc", type=Path, action="append")
    parser.add_argument("--wiki-summary-doc", type=Path, action="append")
    parser.add_argument("--write-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--write-markdown", type=Path, default=DEFAULT_MD)
    parser.add_argument("--require-pass", action="store_true")
    args = parser.parse_args()
    if args.doc:
        args.codex_loop_docs = tuple(args.doc)
        args.readme_progress_docs = tuple(args.doc)
        args.wiki_summary_docs = tuple(args.doc)
        if args.evidence_index == DEFAULT_EVIDENCE_INDEX:
            args.evidence_index = args.doc[0]
    else:
        args.codex_loop_docs = tuple(args.codex_loop_doc or DEFAULT_CODEX_LOOP_DOCS)
        args.readme_progress_docs = tuple(args.readme_progress_doc or DEFAULT_README_PROGRESS_DOCS)
        args.wiki_summary_docs = tuple(args.wiki_summary_doc or DEFAULT_WIKI_SUMMARY_DOCS)
    return args


def main() -> int:
    args = parse_args()
    guard = build_guard(args)
    print_guard(guard)
    if args.write_json:
        write_json(args.write_json, guard)
    if args.write_markdown:
        write_markdown(args.write_markdown, guard)
    if args.require_pass and not guard["passed"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
