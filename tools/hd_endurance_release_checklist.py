#!/usr/bin/env python3
"""Build the HD endurance release-horizon checklist from current evidence.

This is a repo-only aggregator. It reads compact JSON evidence reports and does
not launch Clash95, CDB, wrappers, PowerShell harnesses, or visible windows.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROTECTED_STABLE_STAGE = (
    "gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-"
    "minimapright-dynvswitch"
)
RUNTIME_POLICY = (
    "repo-only endurance release checklist; does not launch Clash95, CDB, "
    "wrappers, PowerShell harnesses, or visible windows"
)

DEFAULT_JSON = Path("captures/current/hd-endurance-release-checklist-current.json")
DEFAULT_MD = Path("captures/current/hd-endurance-release-checklist-current.md")
DEFAULT_STABLE_STAGE_JSON = Path("captures/current/stable-stage-guard-current.json")
DEFAULT_NO_POPUP_JSON = Path("captures/current/no-popup-map-evidence-current.json")
DEFAULT_SHORT_SOAK_JSON = Path("captures/current/hd-soak-report-guard-current.json")
DEFAULT_SHORT_STEP_STATUS_JSON = Path("captures/current/hd-soak-short-step-status-current.json")
DEFAULT_LONG_SOAK_JSON = Path("captures/current/hd-soak-long-report-guard-current.json")
DEFAULT_MANUAL_JSON = Path("captures/current/manual-directinput-validation-checklist-current.json")
DEFAULT_RIGHT_BOTTOM_JSON = Path("captures/current/right-bottom-compose-promotion-decision-current.json")
DEFAULT_CASTLE_JSON = Path("captures/current/castle-overview-promotion-decision-current.json")
DEFAULT_BATTLE_JSON = Path("captures/current/battle-ui-evidence-current.json")
DEFAULT_COMPLETION_JSON = Path("captures/current/current-completion-summary-current.json")
DEFAULT_CONTINUITY_JSON = Path("captures/current/hd-continuity-current.json")
DEFAULT_EXE_ARTIFACT_JSON = Path("captures/current/exe-artifact-guard-current.json")
DEFAULT_PROCESS_HYGIENE_JSON = Path("captures/current/process-hygiene-guard-current.json")


def status_text(passed: bool) -> str:
    return "PASS" if passed else "FAIL"


def load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8-sig"))


def nested(data: dict[str, Any] | None, *keys: str, default: Any = None) -> Any:
    value: Any = data or {}
    for key in keys:
        if not isinstance(value, dict) or key not in value:
            return default
        value = value[key]
    return value


def source_state(data: dict[str, Any] | None) -> str:
    if data is None:
        return "missing"
    if bool(data.get("passed") or data.get("overall")):
        return "pass"
    return "blocked"


def missing_or_blocked(data: dict[str, Any] | None) -> str:
    return "missing" if data is None else "blocked"


def manual_item(manual: dict[str, Any] | None, item_id: str) -> dict[str, Any] | None:
    for item in (manual or {}).get("items") or []:
        if item.get("id") == item_id:
            return item
    return None


def manual_item_passed(manual: dict[str, Any] | None, item_id: str) -> bool:
    item = manual_item(manual, item_id)
    if not item:
        return False
    status = str(item.get("status") or "").lower()
    return bool(item.get("proof_valid")) or status in {"accepted", "passed", "valid", "complete"}


def continuity_check_passed(continuity: dict[str, Any] | None, check_id: str) -> bool:
    if continuity is None:
        return False
    checks = continuity.get("checks") or {}
    value = checks.get(check_id)
    if isinstance(value, dict):
        return bool(value.get("passed"))
    return bool(value)


def continuity_check_summary(
    continuity: dict[str, Any] | None,
    check_id: str,
    label: str,
    passed: bool,
) -> str:
    if passed:
        return f"{label} proof passes"
    if continuity is None:
        return f"{label} proof is absent"
    value = (continuity.get("checks") or {}).get(check_id)
    if isinstance(value, dict):
        status = value.get("status") or "blocked"
        summary = value.get("summary") or "proof is not sufficient for release"
        return f"{label} proof blocked ({status}): {summary}"
    return f"{label} proof is blocked"


def long_soak_summary(long_soak: dict[str, Any] | None, passed: bool) -> str:
    if passed:
        return "2h+ soak evidence exists and passes"
    if long_soak is None:
        return "no 2h+ representative-route soak report is present"
    status = long_soak.get("status") or "blocked"
    summary = long_soak.get("summary") or "2h+ representative-route soak evidence is not sufficient for release"
    return f"2h+ representative-route soak blocked ({status}): {summary}"


def short_step_by_id(short_step_status: dict[str, Any] | None, step_id: str) -> dict[str, Any] | None:
    for step in (short_step_status or {}).get("steps") or []:
        if step.get("id") == step_id:
            return step
    return None


def canonical_short_step_passed(short_step_status: dict[str, Any] | None, step_id: str) -> bool:
    step = short_step_by_id(short_step_status, step_id)
    if not step:
        return False
    summary = step.get("summary") or {}
    return (
        bool(short_step_status and short_step_status.get("passed"))
        and step.get("status") == "pass"
        and step.get("passed") is True
        and step.get("tier") == "short2"
        and step.get("route") == "menu-idle"
        and summary.get("guard_present") is True
        and summary.get("guard_overall") is True
        and summary.get("executed") is True
    )


def artifact_path_exists(value: Any) -> bool:
    if not value:
        return False
    return Path(str(value).replace("\\", "/")).exists()


def summary_bool_or_path_exists(summary: dict[str, Any], key: str, paths: dict[str, Any], path_key: str) -> bool:
    if key in summary:
        return bool(summary.get(key))
    return artifact_path_exists(paths.get(path_key))


def short_soak_requirement_details(
    short_soak: dict[str, Any] | None,
    short_step_status: dict[str, Any] | None,
    step_id: str,
) -> dict[str, Any]:
    current_step = (short_step_status or {}).get("current_step") or {}
    step = short_step_by_id(short_step_status, step_id) or {}
    summary = step.get("summary") or {}
    paths = step.get("paths") or {}
    return {
        "global_report_guard": {
            "source_report": (short_soak or {}).get("source_report"),
            "source_report_selection": (short_soak or {}).get("source_report_selection"),
            "canonical_first_step_report": (short_soak or {}).get("canonical_first_step_report"),
            "canonical_first_step_present": (short_soak or {}).get("canonical_first_step_present"),
            "canonical_runtime_report_missing": (short_soak or {}).get("canonical_runtime_report_missing"),
            "overall": (short_soak or {}).get("overall"),
            "failure_count": len((short_soak or {}).get("failures") or []),
        },
        "short_step_status": {
            "current_step": current_step.get("id"),
            "current_step_status": current_step.get("status"),
            "ladder_complete": (short_step_status or {}).get("ladder_complete"),
            "canonical_report_present": summary_bool_or_path_exists(
                summary, "canonical_report_present", paths, "report_json"
            ),
            "guard_present": summary_bool_or_path_exists(summary, "guard_present", paths, "guard_json"),
            "triage_present": summary_bool_or_path_exists(summary, "triage_present", paths, "triage_json"),
            "guard_overall": summary.get("guard_overall"),
            "executed": summary.get("executed"),
        },
        "canonical_outputs": {
            "report_json": paths.get("report_json"),
            "guard_json": paths.get("guard_json"),
            "triage_json": paths.get("triage_json"),
        },
    }


def short_soak_requirement_summary(
    short_soak: dict[str, Any] | None,
    short_step_status: dict[str, Any] | None,
    short_soak_ok: bool,
    canonical_short_soak_ok: bool,
) -> str:
    if short_soak_ok:
        return (
            "canonical short2 menu-idle step status passes"
            if canonical_short_soak_ok
            else "short2 menu-idle soak report guard passes"
        )
    details = short_soak_requirement_details(short_soak, short_step_status, "short2_menu_idle")
    canonical_path = (details["global_report_guard"].get("canonical_first_step_report") or "")
    canonical_missing = details["global_report_guard"].get("canonical_runtime_report_missing")
    step_report_present = details["short_step_status"].get("canonical_report_present")
    current_status = details["short_step_status"].get("current_step_status")
    if canonical_missing is True and canonical_path and step_report_present is not True:
        return (
            "short2 visible-runtime soak has not produced passing frame/process evidence; "
            f"canonical report is missing: {canonical_path}"
        )
    if current_status:
        return (
            "short2 visible-runtime soak has not produced passing frame/process evidence; "
            f"current short-step status is {current_status}"
        )
    return "short2 visible-runtime soak has not produced passing frame/process evidence"


def requirement(
    requirement_id: str,
    title: str,
    status: str,
    evidence: list[str],
    summary: str,
    next_probe: str,
    category: str,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    row = {
        "id": requirement_id,
        "title": title,
        "category": category,
        "status": status,
        "passed": status == "pass",
        "evidence": evidence,
        "summary": summary,
        "next_probe": next_probe,
    }
    if details is not None:
        row["details"] = details
    return row


def build_checklist(args: argparse.Namespace) -> dict[str, Any]:
    sources = {
        "stable_stage": args.stable_stage_json,
        "no_popup_map": args.no_popup_json,
        "short_soak": args.short_soak_json,
        "short_step_status": args.short_step_status_json,
        "long_soak": args.long_soak_json,
        "manual_directinput": args.manual_json,
        "right_bottom": args.right_bottom_json,
        "castle_overview": args.castle_json,
        "battle_ui": args.battle_json,
        "current_completion": args.completion_json,
        "continuity": args.continuity_json,
        "exe_artifact": args.exe_artifact_json,
        "process_hygiene": args.process_hygiene_json,
    }
    stable = load_json(args.stable_stage_json)
    no_popup = load_json(args.no_popup_json)
    short_soak = load_json(args.short_soak_json)
    short_step_status = load_json(args.short_step_status_json)
    long_soak = load_json(args.long_soak_json)
    manual = load_json(args.manual_json)
    right_bottom = load_json(args.right_bottom_json)
    castle = load_json(args.castle_json)
    battle = load_json(args.battle_json)
    completion = load_json(args.completion_json)
    continuity = load_json(args.continuity_json)
    exe_artifact = load_json(args.exe_artifact_json)
    process_hygiene = load_json(args.process_hygiene_json)

    stable_checks = stable.get("checks") if stable else {}
    stable_ok = (
        stable is not None
        and stable.get("current_stable_stage") == PROTECTED_STABLE_STAGE
        and stable.get("patcher_default_stage") == PROTECTED_STABLE_STAGE
        and nested(stable_checks, "patcher_default_stage", "passed") is True
        and nested(stable_checks, "stable_stage_validation_groups_absent", "passed") is True
    )
    no_popup_ok = bool(no_popup and no_popup.get("passed"))
    legacy_short_soak_ok = bool(short_soak and short_soak.get("overall") and short_soak.get("tier") == "short2")
    canonical_short_soak_ok = canonical_short_step_passed(short_step_status, "short2_menu_idle")
    short_soak_ok = legacy_short_soak_ok or canonical_short_soak_ok
    short_soak_status = "pass" if short_soak_ok else ("missing" if not short_soak and not short_step_status else "blocked")
    long_soak_ok = bool(
        long_soak
        and long_soak.get("overall")
        and int(long_soak.get("duration_sec") or 0) >= 7200
    )
    manual_valid = bool(manual and manual.get("manual_proof_valid"))
    rb_manual_ok = bool(right_bottom and right_bottom.get("manual_input_proof_valid"))
    rb_ready = bool(
        rb_manual_ok
        or str((right_bottom or {}).get("decision") or "").lower()
        in {"ready_for_stable_promotion", "promote_stable", "release_ready"}
    )
    castle_manual_ok = bool(castle and castle.get("manual_input_proof_valid"))
    castle_ready = bool(
        castle_manual_ok
        or str((castle or {}).get("decision") or "").lower()
        in {"ready_for_stable_promotion", "promote_stable", "release_ready"}
    )
    battle_ready = bool(
        battle
        and battle.get("passed")
        and str(battle.get("promotion_status") or "").lower() not in {"validation_stage_only", "blocked"}
    )
    exe_ok = bool(exe_artifact and exe_artifact.get("passed"))
    process_ok = bool(process_hygiene and process_hygiene.get("passed"))
    save_load_ok = continuity_check_passed(continuity, "save_load_roundtrip")
    turn_ok = continuity_check_passed(continuity, "turn_advancement")
    campaign_ok = continuity_check_passed(continuity, "campaign_routes")
    no_speculative_promotion = (
        bool(stable_ok)
        and (right_bottom or {}).get("stable_stage_should_change") is False
        and (castle or {}).get("stable_stage_should_change") is False
        and (battle or {}).get("stable_stage_should_change") is False
        and (manual or {}).get("stable_stage_should_change") is False
    )

    requirements = [
        requirement(
            "protected_stable_stage",
            "Protected default HD stage remains clean",
            "pass" if stable_ok else source_state(stable),
            [str(args.stable_stage_json)],
            "default stage and validation-only group boundary are intact"
            if stable_ok
            else "stable-stage guard does not prove the protected boundary",
            "fix stable-stage guard failures before considering any soak result",
            "patch boundary",
        ),
        requirement(
            "current_no_popup_map",
            "Current no-popup HD map evidence remains valid",
            "pass" if no_popup_ok else source_state(no_popup),
            [str(args.no_popup_json)],
            "hidden/no-popup map evidence still passes" if no_popup_ok else "no-popup map evidence is not passing",
            "refresh no-popup map evidence before runtime endurance claims",
            "render baseline",
        ),
        requirement(
            "short2_menu_idle_soak",
            "First short2 menu-idle soak passes",
            short_soak_status,
            [str(args.short_soak_json), str(args.short_step_status_json)],
            short_soak_requirement_summary(short_soak, short_step_status, short_soak_ok, canonical_short_soak_ok),
            "run the approval-gated short2 menu-idle soak on the protected stage",
            "endurance",
            short_soak_requirement_details(short_soak, short_step_status, "short2_menu_idle"),
        ),
        requirement(
            "long_soak_representative_routes",
            "2h+ representative-route soak passes",
            "pass" if long_soak_ok else source_state(long_soak),
            [str(args.long_soak_json)],
            long_soak_summary(long_soak, long_soak_ok),
            "add long-tier reports only after short2/short10/short30 are stable",
            "endurance",
        ),
        requirement(
            "stable_menu_real_input",
            "Stable menu load has real input proof",
            "pass" if manual_item_passed(manual, "stable_menu_load") else missing_or_blocked(manual),
            [str(args.manual_json)],
            "manual menu-load proof is accepted"
            if manual_item_passed(manual, "stable_menu_load")
            else "menu-load proof remains pending manual DirectInput validation",
            "collect approved manual menu-load proof or keep promotion blocked",
            "manual input",
        ),
        requirement(
            "stable_hd_map_real_input",
            "HD map input has no drift under real input",
            "pass" if manual_item_passed(manual, "stable_hd_map_input") else missing_or_blocked(manual),
            [str(args.manual_json)],
            "manual HD map input proof is accepted"
            if manual_item_passed(manual, "stable_hd_map_input")
            else "HD map input proof remains pending manual DirectInput validation",
            "collect approved manual map input proof after short soak is stable",
            "manual input",
        ),
        requirement(
            "right_bottom_action_menu",
            "Right-bottom action/menu is naturally or manually proven",
            "pass" if rb_ready else missing_or_blocked(right_bottom),
            [str(args.right_bottom_json), str(args.manual_json)],
            "right-bottom promotion proof is ready"
            if rb_ready
            else "right-bottom action/menu remains validation-only or manual-proof blocked",
            "replace debugger-forced action-click proof with natural or approved manual input proof",
            "screen route",
        ),
        requirement(
            "castle_and_barracks_centered_input",
            "Castle overview and barracks centered input are proven",
            "pass"
            if (
                castle_ready
                and manual_item_passed(manual, "castle_barracks_centered_input")
                and manual_item_passed(manual, "castle_overview_centered_input")
            )
            else "blocked",
            [str(args.castle_json), str(args.manual_json)],
            "castle/barracks centered input proof is release-ready"
            if castle_ready and manual_valid
            else "castle/barracks centered input remains validation-only or manual-proof blocked",
            "collect approved centered castle/barracks input proof",
            "screen route",
        ),
        requirement(
            "tactical_battle_entry_return",
            "Tactical battle entry/use/return is proven",
            "pass" if battle_ready else missing_or_blocked(battle),
            [str(args.battle_json)],
            "battle route is release-ready"
            if battle_ready
            else "battle evidence remains validation-only or missing visible click-to-callback proof",
            "prove battle entry, UI use, return, and post-return map health on an approved route",
            "screen route",
        ),
        requirement(
            "save_load_roundtrip",
            "Safe save/load roundtrip continuity is proven",
            "pass" if save_load_ok else missing_or_blocked(continuity),
            [str(args.continuity_json)],
            continuity_check_summary(continuity, "save_load_roundtrip", "save/load continuity", save_load_ok),
            "add safe test-save roundtrip evidence after short-tier stability",
            "state continuity",
        ),
        requirement(
            "turn_advancement",
            "Turn advancement avoids state desync",
            "pass" if turn_ok else missing_or_blocked(continuity),
            [str(args.continuity_json)],
            continuity_check_summary(continuity, "turn_advancement", "turn advancement", turn_ok),
            "add deterministic turn-advance route evidence after save/load is safe",
            "state continuity",
        ),
        requirement(
            "campaign_routes",
            "Campaign routes remain stable",
            "pass" if campaign_ok else missing_or_blocked(continuity),
            [str(args.continuity_json)],
            continuity_check_summary(continuity, "campaign_routes", "campaign route", campaign_ok),
            "add representative campaign route soaks after short/medium tiers are stable",
            "state continuity",
        ),
        requirement(
            "artifact_and_process_hygiene",
            "No prohibited artifacts or stale processes",
            "pass" if exe_ok and process_ok else "blocked",
            [str(args.exe_artifact_json), str(args.process_hygiene_json)],
            "artifact and process hygiene guards pass"
            if exe_ok and process_ok
            else "artifact or process hygiene guard is not passing",
            "clear hygiene guard failures before accepting runtime evidence",
            "repo hygiene",
        ),
        requirement(
            "no_speculative_promotion",
            "No validation-only promotion is hidden by endurance work",
            "pass" if no_speculative_promotion else "blocked",
            [str(args.stable_stage_json), str(args.right_bottom_json), str(args.castle_json), str(args.battle_json)],
            "stable-stage boundary remains unchanged while validation-only lanes stay non-promoting"
            if no_speculative_promotion
            else "one or more promotion boundaries are not fail-closed",
            "keep DEFAULT_STAGE unchanged until strict natural/manual/input and soak gates pass",
            "patch boundary",
        ),
    ]

    failures = [
        f"{row['id']}: {row['summary']}"
        for row in requirements
        if not row["passed"]
    ]
    counts = {
        "total": len(requirements),
        "passed": sum(1 for row in requirements if row["passed"]),
        "blocked": sum(1 for row in requirements if row["status"] == "blocked"),
        "missing": sum(1 for row in requirements if row["status"] == "missing"),
    }
    next_milestone = next(
        (
            row
            for row in requirements
            if row["id"] in (
                "short2_menu_idle_soak",
                "stable_menu_real_input",
                "stable_hd_map_real_input",
            )
            and not row["passed"]
        ),
        next((row for row in requirements if not row["passed"]), None),
    )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "passed": not failures,
        "runtime_policy": RUNTIME_POLICY,
        "protected_stable_stage": PROTECTED_STABLE_STAGE,
        "source_artifacts": {name: str(path) for name, path in sources.items()},
        "source_states": {
            name: ("missing" if load_json(path) is None else "present")
            for name, path in sources.items()
        },
        "counts": counts,
        "next_milestone": {
            "id": next_milestone["id"],
            "title": next_milestone["title"],
            "next_probe": next_milestone["next_probe"],
        }
        if next_milestone
        else None,
        "requirements": requirements,
        "full_game_complete": not failures,
        "full_game_percent_statement": (
            "100%; all release-horizon requirements have current evidence"
            if not failures
            else "not 100%; endurance, manual input, state continuity, or validation-route gates remain open"
        ),
        "current_completion_summary": {
            "full_game_complete": (completion or {}).get("full_game_complete"),
            "full_game_percent_statement": (completion or {}).get("full_game_percent_statement"),
        },
        "failures": failures,
    }


def to_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# HD Endurance Release Checklist",
        "",
        f"- Overall: {status_text(bool(report['passed']))}",
        f"- Generated: `{report['generated_at']}`",
        f"- Runtime policy: {report['runtime_policy']}",
        f"- Protected stable stage: `{report['protected_stable_stage']}`",
        f"- Full game complete: `{report['full_game_complete']}`",
        f"- Completion statement: {report['full_game_percent_statement']}",
        (
            f"- Counts: `{report['counts']['passed']}/{report['counts']['total']}` pass, "
            f"`{report['counts']['blocked']}` blocked, `{report['counts']['missing']}` missing"
        ),
    ]
    if report.get("next_milestone"):
        milestone = report["next_milestone"]
        lines.extend(
            [
                "",
                "## Next Milestone",
                "",
                f"- `{milestone['id']}`: {milestone['title']}",
                f"- Next probe: {milestone['next_probe']}",
            ]
        )

    lines.extend(["", "## Requirements", ""])
    for row in report["requirements"]:
        lines.append(
            f"- `{row['id']}`: `{row['status']}` - {row['summary']}"
        )
        details = row.get("details") or {}
        canonical_outputs = details.get("canonical_outputs") or {}
        short_status = details.get("short_step_status") or {}
        global_guard = details.get("global_report_guard") or {}
        if row["id"] == "short2_menu_idle_soak" and details:
            lines.append(
                "  "
                f"Canonical report: `{canonical_outputs.get('report_json') or global_guard.get('canonical_first_step_report')}` "
                f"present=`{global_guard.get('canonical_first_step_present') or short_status.get('canonical_report_present')}`; "
                f"guard: `{canonical_outputs.get('guard_json')}` present=`{short_status.get('guard_present')}`; "
                f"triage: `{canonical_outputs.get('triage_json')}` present=`{short_status.get('triage_present')}`"
            )

    if report["failures"]:
        lines.extend(["", "## Open Items", ""])
        for failure in report["failures"]:
            lines.append(f"- {failure}")

    lines.append("")
    return "\n".join(lines)


def write_outputs(report: dict[str, Any], json_path: Path | None, md_path: Path | None) -> None:
    if json_path:
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(report, indent=2) + "\n", encoding="ascii")
    if md_path:
        md_path.parent.mkdir(parents=True, exist_ok=True)
        md_path.write_text(to_markdown(report), encoding="ascii")


def add_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--stable-stage-json", type=Path, default=DEFAULT_STABLE_STAGE_JSON)
    parser.add_argument("--no-popup-json", type=Path, default=DEFAULT_NO_POPUP_JSON)
    parser.add_argument("--short-soak-json", type=Path, default=DEFAULT_SHORT_SOAK_JSON)
    parser.add_argument("--short-step-status-json", type=Path, default=DEFAULT_SHORT_STEP_STATUS_JSON)
    parser.add_argument("--long-soak-json", type=Path, default=DEFAULT_LONG_SOAK_JSON)
    parser.add_argument("--manual-json", type=Path, default=DEFAULT_MANUAL_JSON)
    parser.add_argument("--right-bottom-json", type=Path, default=DEFAULT_RIGHT_BOTTOM_JSON)
    parser.add_argument("--castle-json", type=Path, default=DEFAULT_CASTLE_JSON)
    parser.add_argument("--battle-json", type=Path, default=DEFAULT_BATTLE_JSON)
    parser.add_argument("--completion-json", type=Path, default=DEFAULT_COMPLETION_JSON)
    parser.add_argument("--continuity-json", type=Path, default=DEFAULT_CONTINUITY_JSON)
    parser.add_argument("--exe-artifact-json", type=Path, default=DEFAULT_EXE_ARTIFACT_JSON)
    parser.add_argument("--process-hygiene-json", type=Path, default=DEFAULT_PROCESS_HYGIENE_JSON)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    add_args(parser)
    parser.add_argument("--write-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--write-markdown", "--write-md", dest="write_markdown", type=Path, default=DEFAULT_MD)
    parser.add_argument("--require-pass", action="store_true")
    args = parser.parse_args()

    report = build_checklist(args)
    write_outputs(report, args.write_json, args.write_markdown)
    print(f"overall: {status_text(bool(report['passed']))}")
    print(f"runtime-policy: {report['runtime_policy']}")
    print(f"requirements: {report['counts']['passed']}/{report['counts']['total']} pass")
    if report.get("next_milestone"):
        print(f"next-milestone: {report['next_milestone']['id']}")
    if report["failures"]:
        print("open-items:")
        for failure in report["failures"]:
            print(f"  - {failure}")
    if args.require_pass and not report["passed"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
