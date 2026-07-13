#!/usr/bin/env python3
"""Check that project documentation agrees with generated Clash95 HD state.

This is a repo-only guard. It reads JSON and Markdown artifacts and does not
launch Clash95, CDB, wrappers, PowerShell harnesses, or visible windows.
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
DEFAULT_POST_OWNER_EVIDENCE_JSON = Path("captures/current/post-owner-evidence-current.json")
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
DEFAULT_PROJECT_SUMMARY_DOCS = (
    Path("README.md"),
    Path("AGENTS.md"),
    Path("docs/hd/WORKING_WITH_THIS_REPO.md"),
)
DEFAULT_WIKI_SUMMARY_DOCS = DEFAULT_PROJECT_SUMMARY_DOCS

EXPECTED_MANUAL_TARGET_IDS = (
    "stable_menu_load",
    "stable_hd_map_input",
    "right_bottom_validation_input",
    "castle_barracks_centered_input",
    "castle_overview_centered_input",
)
NO_POPUP_PREFERENCE = (
    "Do not launch Clash95, CDB, wrappers, PowerShell harnesses, or visible windows "
    "unless the user explicitly approves."
)
RUNTIME_POLICY = (
    "repo-only docs/source inspection; does not launch Clash95, CDB, wrappers, "
    "PowerShell harnesses, or visible windows"
)

LEGACY_PATHS = (
    Path("wiki"),
    Path("meta/templates"),
    Path("meta/workflows"),
    Path("raw/inbox"),
    Path("raw/processed"),
    Path("tools/wiki_lint.py"),
    Path("tools/wiki_search.py"),
)


def repo_path(path: Path) -> Path:
    return path if path.is_absolute() else REPO_ROOT / path


def load_json(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    resolved = repo_path(path)
    if not resolved.exists():
        return {}
    try:
        return json.loads(resolved.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}


def read_text(path: Path) -> tuple[str, str | None]:
    resolved = repo_path(path)
    if not resolved.exists():
        return "", f"missing document: {path}"
    try:
        return resolved.read_text(encoding="utf-8-sig", errors="replace"), None
    except OSError as exc:
        return "", f"could not read {path}: {type(exc).__name__}: {exc}"


def check_record(passed: bool, summary: dict[str, Any], failures: list[str]) -> dict[str, Any]:
    return {"passed": passed, "summary": summary, "failures": failures}


def nested_get(value: dict[str, Any], keys: tuple[str, ...]) -> Any:
    current: Any = value
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def supplied_payload(args: argparse.Namespace, name: str, path_name: str) -> dict[str, Any]:
    payload = getattr(args, name, None)
    if isinstance(payload, dict):
        return payload
    return load_json(getattr(args, path_name, None))


def build_facts(args: argparse.Namespace) -> dict[str, Any]:
    refresh = supplied_payload(args, "refresh_payload", "refresh_json")
    boundary = supplied_payload(args, "boundary_payload", "boundary_json")
    stable = load_json(getattr(args, "stable_stage_json", DEFAULT_STABLE_STAGE_JSON))
    checklist = load_json(getattr(args, "manual_checklist_json", DEFAULT_MANUAL_CHECKLIST_JSON))
    right_bottom = load_json(getattr(args, "right_bottom_matrix_json", DEFAULT_RIGHT_BOTTOM_MATRIX_JSON))
    castle = load_json(getattr(args, "castle_matrix_json", DEFAULT_CASTLE_MATRIX_JSON))

    refresh_checks = refresh.get("checks") or {}
    stable_summary = (refresh_checks.get("stable_stage_guard") or {}).get("summary") or {}
    boundary_summary = (refresh_checks.get("no_popup_boundary_guard") or {}).get("summary") or {}
    stable_stage = (
        stable_summary.get("current_stable_stage")
        or stable.get("current_stable_stage")
        or stable.get("stage")
    )
    patcher_default_stage = (
        stable_summary.get("patcher_default_stage")
        or stable.get("patcher_default_stage")
        or stable_stage
    )
    items = checklist.get("items") or []
    manual_ids = [item.get("id") for item in items if item.get("id")]

    return {
        "refresh_passed": refresh.get("passed"),
        "stable_stage": stable_stage,
        "patcher_default_stage": patcher_default_stage,
        "manual_target_ids": manual_ids,
        "manual_status": checklist.get("status"),
        "manual_promotion_ready": checklist.get("promotion_ready")
        if "promotion_ready" in checklist
        else nested_get(checklist, ("summary", "promotion_ready")),
        "visible_runtime_requires_approval": checklist.get("visible_runtime_requires_approval"),
        "no_popup_preference": checklist.get("no_popup_operator_preference"),
        "boundary_passed": boundary.get("passed")
        if "passed" in boundary
        else (refresh_checks.get("no_popup_boundary_guard") or {}).get("passed"),
        "boundary_counts": {
            "required_guard_count": boundary.get("required_guard_count", boundary_summary.get("required_guard_count")),
            "required_supporting_report_count": boundary.get(
                "required_supporting_report_count",
                boundary_summary.get("required_supporting_report_count"),
            ),
            "required_report_count": boundary.get("required_report_count", boundary_summary.get("required_report_count")),
        },
        "right_bottom_promotion_status": right_bottom.get("promotion_status"),
        "right_bottom_stable_stage_should_change": right_bottom.get("stable_stage_should_change"),
        "castle_promotion_status": castle.get("promotion_status"),
        "castle_stable_stage_should_change": castle.get("stable_stage_should_change"),
    }


def unique_paths(paths: list[Path]) -> list[Path]:
    result: list[Path] = []
    seen: set[str] = set()
    for path in paths:
        key = str(path).replace("\\", "/").lower()
        if key not in seen:
            seen.add(key)
            result.append(path)
    return result


def configured_docs(args: argparse.Namespace) -> dict[str, list[Path]]:
    codex = list(getattr(args, "codex_loop_docs", DEFAULT_CODEX_LOOP_DOCS))
    progress = list(getattr(args, "readme_progress_docs", DEFAULT_README_PROGRESS_DOCS))
    supplied_summaries = list(getattr(args, "wiki_summary_docs", ()))
    project = [path for path in supplied_summaries if not str(path).replace("\\", "/").startswith("wiki/")]
    if not project:
        project = list(DEFAULT_PROJECT_SUMMARY_DOCS)
    evidence = getattr(args, "evidence_index", DEFAULT_EVIDENCE_INDEX)
    return {
        "handoff": unique_paths(codex),
        "project": unique_paths(progress + project),
        "evidence": [evidence],
    }


def build_guard(args: argparse.Namespace) -> dict[str, Any]:
    facts = build_facts(args)
    doc_groups = configured_docs(args)
    checks: dict[str, Any] = {}

    state_failures: list[str] = []
    if not facts.get("stable_stage"):
        state_failures.append("stable stage is missing")
    if facts.get("stable_stage") != facts.get("patcher_default_stage"):
        state_failures.append("stable stage differs from patcher default stage")
    manual_ids = facts.get("manual_target_ids") or []
    if manual_ids and tuple(manual_ids) != EXPECTED_MANUAL_TARGET_IDS:
        state_failures.append(f"manual target IDs differ from {list(EXPECTED_MANUAL_TARGET_IDS)}")
    if facts.get("manual_promotion_ready") is True:
        state_failures.append("manual promotion is unexpectedly ready")
    if facts.get("visible_runtime_requires_approval") is False:
        state_failures.append("visible runtime no longer requires approval")
    if facts.get("boundary_passed") is False:
        state_failures.append("no-popup boundary is failing")
    checks["generated_state"] = check_record(not state_failures, facts, state_failures)

    texts: dict[str, str] = {}
    for group, paths in doc_groups.items():
        failures: list[str] = []
        parts: list[str] = []
        for path in paths:
            text, failure = read_text(path)
            if failure:
                failures.append(failure)
            else:
                parts.append(text)
        texts[group] = "\n".join(parts)
        checks[f"documents_{group}"] = check_record(
            not failures,
            {"paths": [str(path) for path in paths]},
            failures,
        )

    project_text = texts.get("project", "")
    identity_failures: list[str] = []
    lowered_project = project_text.lower()
    if "clash95 hd" not in lowered_project and "clash-hd" not in lowered_project:
        identity_failures.append("project documentation does not identify Clash95 HD")
    if "# llm wiki" in lowered_project or "generic llm-friendly knowledge repository" in lowered_project:
        identity_failures.append("project documentation still presents the repository as an LLM wiki")
    if facts.get("stable_stage") and str(facts["stable_stage"]).lower() not in lowered_project:
        identity_failures.append("project documentation does not mention the protected stable stage")
    if "explicit" not in lowered_project or "approval" not in lowered_project:
        identity_failures.append("project documentation does not preserve explicit approval requirements")
    checks["project_identity"] = check_record(
        not identity_failures,
        {"stable_stage": facts.get("stable_stage")},
        identity_failures,
    )

    legacy_present = [str(path) for path in LEGACY_PATHS if repo_path(path).exists()]
    checks["legacy_scaffold_absent"] = check_record(
        not legacy_present,
        {"checked_paths": [str(path) for path in LEGACY_PATHS]},
        [f"legacy scaffold still exists: {path}" for path in legacy_present],
    )

    failures: list[str] = []
    for name, check in checks.items():
        failures.extend(f"{name}: {failure}" for failure in check.get("failures", []))

    return {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "passed": not failures,
        "runtime_policy": RUNTIME_POLICY,
        "guard_policy": (
            "generated project state must agree with Clash95 HD documentation, protected-stage and "
            "approval boundaries must remain visible, and the removed knowledge-base scaffold must stay absent"
        ),
        "facts": facts,
        "doc_groups": {name: [str(path) for path in paths] for name, paths in doc_groups.items()},
        "checks": checks,
        "failures": failures,
    }


def status_text(passed: bool) -> str:
    return "PASS" if passed else "FAIL"


def print_guard(guard: dict[str, Any]) -> None:
    print(f"overall: {status_text(bool(guard.get('passed')))}")
    print(f"runtime-policy: {guard['runtime_policy']}")
    print(f"stable-stage: {guard['facts'].get('stable_stage')}")
    for name, check in guard["checks"].items():
        print(f"{name}: {status_text(bool(check.get('passed')))}")
    if guard["failures"]:
        print("failures:")
        for failure in guard["failures"]:
            print(f"  - {failure}")


def write_markdown(path: Path, guard: dict[str, Any]) -> None:
    facts = guard["facts"]
    counts = facts.get("boundary_counts") or {}
    lines = [
        "# Docs Consistency Guard",
        "",
        f"- Overall: {status_text(bool(guard['passed']))}",
        f"- Generated: `{guard['generated_at']}`",
        f"- Runtime policy: {guard['runtime_policy']}",
        f"- Stable stage: `{facts.get('stable_stage')}`",
        f"- Manual target IDs: `{facts.get('manual_target_ids')}`",
        f"- No-popup boundary passed: `{facts.get('boundary_passed')}`",
        (
            "- No-popup boundary counts: "
            f"`required_guard_count={counts.get('required_guard_count')}`, "
            f"`required_supporting_report_count={counts.get('required_supporting_report_count')}`, "
            f"`required_report_count={counts.get('required_report_count')}`"
        ),
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
    repo_path(path).parent.mkdir(parents=True, exist_ok=True)
    repo_path(path).write_text("\n".join(lines), encoding="utf-8")


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
    parser.add_argument("--post-owner-evidence-json", type=Path, default=DEFAULT_POST_OWNER_EVIDENCE_JSON)
    parser.add_argument("--no-popup-map-json", type=Path, default=DEFAULT_NO_POPUP_MAP_JSON)
    parser.add_argument("--visible-runtime-json", type=Path, default=DEFAULT_VISIBLE_RUNTIME_JSON)
    parser.add_argument("--no-visible-runtime-json", type=Path, default=DEFAULT_NO_VISIBLE_RUNTIME_JSON)
    parser.add_argument("--evidence-index", type=Path, default=DEFAULT_EVIDENCE_INDEX)
    parser.add_argument("--codex-loop-doc", type=Path, action="append")
    parser.add_argument("--readme-progress-doc", type=Path, action="append")
    parser.add_argument("--project-summary-doc", type=Path, action="append")
    parser.add_argument("--write-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--write-markdown", type=Path, default=DEFAULT_MD)
    parser.add_argument("--require-pass", action="store_true")
    args = parser.parse_args()
    args.codex_loop_docs = tuple(args.codex_loop_doc or DEFAULT_CODEX_LOOP_DOCS)
    args.readme_progress_docs = tuple(args.readme_progress_doc or DEFAULT_README_PROGRESS_DOCS)
    args.wiki_summary_docs = tuple(args.project_summary_doc or DEFAULT_PROJECT_SUMMARY_DOCS)
    return args


def main() -> int:
    args = parse_args()
    guard = build_guard(args)
    print_guard(guard)
    if args.write_json:
        repo_path(args.write_json).parent.mkdir(parents=True, exist_ok=True)
        repo_path(args.write_json).write_text(json.dumps(guard, indent=2) + "\n", encoding="utf-8")
    if args.write_markdown:
        write_markdown(args.write_markdown, guard)
    if args.require_pass and not guard["passed"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
