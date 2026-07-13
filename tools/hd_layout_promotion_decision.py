#!/usr/bin/env python3
"""Record the fail-closed HD-layout stable-promotion decision.

This is a repo-only evidence parser.  It intentionally has no promotion path:
the current evidence proves hidden geometry and authentic visible composition,
but the only relocated command-panel click attempt missed its requested client
coordinate and produced no callback.  The helper passes only when it records
that exact limitation and keeps the protected stable stage unchanged.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_PATCH_JSON = Path("captures/current/patch-stage-hdlayout-current.json")
DEFAULT_HIDDEN_JSON = Path("captures/current/hd-layout-summary-current.json")
DEFAULT_HIDDEN_RUN_JSON = Path(
    "captures/archive/cdb-surface-dump-20260713-072428/summary.json"
)
DEFAULT_VISIBLE_JSON = Path("captures/current/hd-layout-visible-current.json")
DEFAULT_MANUAL_JSON = Path(
    "captures/current/manual-directinput-validation-checklist-current.json"
)
DEFAULT_PROCESS_HYGIENE_JSON = Path(
    "captures/current/process-hygiene-guard-current.json"
)
DEFAULT_OUTPUT_JSON = Path(
    "captures/current/hd-layout-promotion-decision-current.json"
)
DEFAULT_OUTPUT_MD = Path(
    "captures/current/hd-layout-promotion-decision-current.md"
)

EXPECTED_CANDIDATE_SHA256 = (
    "911A4F1CFB3CFEE7974F50742CC98FDD16DCC82EAA95C88F748E0976140E6FBD"
)
PROTECTED_STABLE_STAGE = (
    "gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-"
    "presentbounds-minimapright-dynvswitch"
)
HD_LAYOUT_STAGE = f"{PROTECTED_STABLE_STAGE}-hdlayout"
EXPECTED_PATCH_GROUPS = {
    "terrain-tooltip-bottom-center": {"patched": 12, "total": 12},
    "selected-unit-command-panel-right-bottom": {"patched": 8, "total": 8},
}
EXPECTED_FAILED_CLICK = {
    "requested_client": [760, 560],
    "actual_client": [716, 493],
    "client_error": [-44, -67],
}


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError("top-level JSON value is not an object")
    return payload


def _upper_sha(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    return value.upper()


def _new_check() -> dict[str, Any]:
    return {"passed": True, "failures": []}


def _require(
    checks: dict[str, dict[str, Any]],
    name: str,
    condition: bool,
    failure: str,
) -> None:
    check = checks.setdefault(name, _new_check())
    if not condition:
        check["passed"] = False
        check["failures"].append(failure)


def evaluate_decision(
    args: argparse.Namespace,
    *,
    patch: dict[str, Any],
    hidden: dict[str, Any],
    hidden_run: dict[str, Any],
    visible: dict[str, Any],
    manual: dict[str, Any],
    process_hygiene: dict[str, Any],
    input_failures: list[str] | None = None,
) -> dict[str, Any]:
    """Evaluate already-loaded evidence dictionaries."""

    checks: dict[str, dict[str, Any]] = {}

    patch_stage = patch.get("stage")
    patch_groups = patch.get("groups") or {}
    current_hd_map_gate = patch.get("current_hd_map_gate") or {}
    _require(
        checks,
        "patch_manifest",
        patch_stage == HD_LAYOUT_STAGE,
        f"patch stage is {patch_stage!r}, expected exact HD-layout stage {HD_LAYOUT_STAGE!r}",
    )
    for group, expected in EXPECTED_PATCH_GROUPS.items():
        actual = patch_groups.get(group)
        _require(
            checks,
            "patch_manifest",
            actual == expected,
            f"patch group {group!r} is {actual!r}, expected {expected!r}",
        )
    _require(
        checks,
        "patch_manifest",
        current_hd_map_gate.get("passed") is True,
        "current HD map gate is not passing in the HD-layout patch manifest",
    )
    map_gate_checks = current_hd_map_gate.get("checks") or {}
    _require(
        checks,
        "patch_manifest",
        bool(map_gate_checks)
        and all(
            isinstance(item, dict) and item.get("passed") is True
            for item in map_gate_checks.values()
        ),
        "one or more current HD map subchecks are missing or not passing",
    )

    patch_sha = _upper_sha(patch.get("exe_sha256"))
    hidden_run_sha = _upper_sha(hidden_run.get("CandidateSha256"))
    visible_sha = _upper_sha(visible.get("candidate_sha256"))
    sha_values = {
        "patch_manifest": patch_sha,
        "hidden_archived_run": hidden_run_sha,
        "visible_composition": visible_sha,
    }
    for source, value in sha_values.items():
        _require(
            checks,
            "candidate_identity",
            value == EXPECTED_CANDIDATE_SHA256,
            f"{source} candidate SHA-256 is {value!r}, expected {EXPECTED_CANDIDATE_SHA256}",
        )
    _require(
        checks,
        "candidate_identity",
        len(set(sha_values.values())) == 1,
        f"candidate SHA-256 differs across evidence sources: {sha_values}",
    )

    hidden_checks = hidden.get("checks") or {}
    _require(
        checks,
        "hidden_geometry",
        hidden.get("passed") is True,
        "hidden HD-layout geometry summary is not passing",
    )
    _require(
        checks,
        "hidden_geometry",
        hidden.get("redraw_clip_proved") is True,
        "hidden HD-layout summary did not prove the relocated redraw clip",
    )
    _require(
        checks,
        "hidden_geometry",
        hidden.get("target_size") == [800, 600],
        f"hidden HD-layout target size is {hidden.get('target_size')!r}, expected [800, 600]",
    )
    for name in (
        "no_access_violation",
        "tooltip_init_anchor",
        "panel_setup",
        "panel_draws",
        "panel_hitscan_anchor",
        "panel_redraw_clip",
    ):
        _require(
            checks,
            "hidden_geometry",
            isinstance(hidden_checks.get(name), dict)
            and hidden_checks[name].get("passed") is True,
            f"hidden geometry check {name!r} is missing or not passing",
        )
    _require(
        checks,
        "hidden_geometry",
        hidden_run.get("Passed") is True,
        "archived hidden-desktop run summary is not passing",
    )
    _require(
        checks,
        "hidden_geometry",
        hidden_run.get("HiddenDesktop") is True
        and hidden_run.get("AllowVisibleDesktop") is False,
        "archived geometry run was not strictly hidden-desktop/no-visible-fallback",
    )
    _require(
        checks,
        "hidden_geometry",
        hidden_run.get("Stage") == HD_LAYOUT_STAGE,
        f"archived hidden run stage is {hidden_run.get('Stage')!r}, expected {HD_LAYOUT_STAGE!r}",
    )

    visible_checks = visible.get("checks") or {}
    _require(
        checks,
        "visible_composition",
        visible.get("passed") is True,
        "visible HD-layout composition summary is not passing",
    )
    _require(
        checks,
        "visible_composition",
        visible.get("evidence_class")
        == "approved_visible_automated_layout_composition",
        "visible evidence class is not approved automated layout composition",
    )
    for name in (
        "candidate_identity",
        "map_capture_authenticity",
        "hover_capture_authenticity",
        "gameplay_route",
        "tooltip_bottom_center_visible",
        "panel_right_bottom_visible",
    ):
        _require(
            checks,
            "visible_composition",
            isinstance(visible_checks.get(name), dict)
            and visible_checks[name].get("passed") is True,
            f"visible composition check {name!r} is missing or not passing",
        )
    for name in ("map_capture_authenticity", "hover_capture_authenticity"):
        frame = visible_checks.get(name) or {}
        _require(
            checks,
            "visible_composition",
            frame.get("hash_matches") is True
            and frame.get("handles_match") is True
            and frame.get("capture_mode") == "screen",
            f"visible frame {name!r} is not an authentic hash/handle-matched screen capture",
        )

    failed_click = visible.get("failed_panel_click_attempt") or {}
    for key, expected in EXPECTED_FAILED_CLICK.items():
        _require(
            checks,
            "failed_command_click",
            failed_click.get(key) == expected,
            f"failed command click {key} is {failed_click.get(key)!r}, expected {expected!r}",
        )
    _require(
        checks,
        "failed_command_click",
        failed_click.get("attempt_observed") is True
        and failed_click.get("classified_failed_attempt") is True,
        "the descriptor-5 attempt is not explicitly recorded as an observed failed attempt",
    )
    for key in ("path_verified", "click_path_verified", "alignment_passed"):
        _require(
            checks,
            "failed_command_click",
            failed_click.get(key) is False,
            f"failed command click incorrectly claims {key}=true",
        )
    _require(
        checks,
        "failed_command_click",
        visible.get("command_click_alignment") is False,
        "visible summary incorrectly claims relocated command-click alignment",
    )
    _require(
        checks,
        "failed_command_click",
        visible.get("panel_click_callback_proof") is False,
        "visible summary incorrectly claims a command-panel callback",
    )

    hover = visible.get("automated_hover_alignment") or {}
    _require(
        checks,
        "automated_hover_scope",
        hover.get("passed") is True
        and hover.get("requested_client") == [640, 544]
        and hover.get("actual_client") == [640, 544]
        and hover.get("click_event_count") == 0,
        "automated hover is not the exact no-click Win32 alignment observation",
    )
    _require(
        checks,
        "automated_hover_scope",
        hover.get("proof_class") == "automated_win32_setcursor_alignment"
        and hover.get("manual_directinput_proof") is False
        and hover.get("command_click_alignment") is False,
        "automated hover was incorrectly elevated to manual or command-click proof",
    )

    manual_summary = manual.get("manual_proof_summary") or {}
    checklist_summary = manual.get("summary") or {}
    items = manual.get("items") or []
    _require(
        checks,
        "manual_directinput_pending",
        manual.get("passed") is True
        and manual.get("status") == "pending_manual_validation",
        "manual DirectInput checklist is missing, invalid, or no longer pending",
    )
    _require(
        checks,
        "manual_directinput_pending",
        manual.get("manual_proof") in (None, False)
        and manual.get("manual_proof_supplied") is False
        and manual.get("manual_proof_valid") is False,
        "manual DirectInput proof was supplied or claimed valid",
    )
    _require(
        checks,
        "manual_directinput_pending",
        manual_summary.get("checked_item_count") == 0
        and len(items) == 5
        and checklist_summary.get("pending_count") == 5,
        "manual DirectInput checklist is not exactly 0/5 checked and 5/5 pending",
    )
    _require(
        checks,
        "manual_directinput_pending",
        all(isinstance(item, dict) and item.get("status") == "pending_manual" for item in items),
        "one or more manual DirectInput checklist items are not pending_manual",
    )

    for key in (
        "manual_directinput_proof",
        "stable_stage_promotion_ready",
        "promotion_ready",
    ):
        _require(
            checks,
            "promotion_state",
            visible.get(key) is False,
            f"visible summary incorrectly claims {key}=true",
        )
    _require(
        checks,
        "promotion_state",
        manual.get("promotion_ready") is False
        and checklist_summary.get("promotion_ready") is False
        and manual.get("stable_stage_should_change") is False
        and checklist_summary.get("stable_stage_should_change") is False,
        "manual checklist incorrectly claims promotion readiness or a stable-stage change",
    )

    _require(
        checks,
        "process_hygiene",
        process_hygiene.get("passed") is True
        and process_hygiene.get("matching_process_count") == 0
        and process_hygiene.get("matching_processes") == [],
        "current process-hygiene result does not record zero Clash95/CDB processes",
    )

    current_stable_stage = getattr(args, "current_stable_stage", PROTECTED_STABLE_STAGE)
    _require(
        checks,
        "stable_stage_protection",
        current_stable_stage == PROTECTED_STABLE_STAGE,
        f"current stable stage is {current_stable_stage!r}, expected protected stage {PROTECTED_STABLE_STAGE!r}",
    )
    _require(
        checks,
        "stable_stage_protection",
        patch_stage != current_stable_stage,
        "validation-only HD-layout stage was presented as the current stable stage",
    )

    allow_cdb_only = bool(getattr(args, "allow_cdb_only_promotion", False))
    override_manifest = getattr(args, "promotion_override_manifest", None)
    _require(
        checks,
        "no_override",
        not allow_cdb_only,
        "CDB-only promotion overrides are prohibited for the HD-layout decision",
    )
    _require(
        checks,
        "no_override",
        override_manifest is None,
        "promotion override manifests are not accepted by the HD-layout decision",
    )

    failures = list(input_failures or [])
    for name, check in checks.items():
        failures.extend(f"{name}: {failure}" for failure in check["failures"])

    decision = "defer_stable_promotion"
    stable_stage_should_change = False
    passed = not failures
    return {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "runtime_policy": (
            "repo-only JSON decision; does not launch or control Clash95, CDB, "
            "wrappers, PowerShell, input automation, or visible windows"
        ),
        "passed": passed,
        "decision": decision,
        "stable_stage_should_change": stable_stage_should_change,
        "current_stable_stage": current_stable_stage,
        "protected_stable_stage": PROTECTED_STABLE_STAGE,
        "validation_stage": patch_stage,
        "expected_validation_stage": HD_LAYOUT_STAGE,
        "candidate_sha256": patch_sha,
        "expected_candidate_sha256": EXPECTED_CANDIDATE_SHA256,
        "candidate_identity": sha_values,
        "manual_directinput_proof": False,
        "manual_checked_item_count": manual_summary.get("checked_item_count"),
        "manual_checklist_item_count": len(items),
        "command_click_alignment": False,
        "panel_click_callback_proof": False,
        "promotion_ready": False,
        "allow_cdb_only_promotion": allow_cdb_only,
        "promotion_override_manifest": (
            str(override_manifest) if override_manifest is not None else None
        ),
        "override_accepted": False,
        "checks": checks,
        "evidence": {
            "patch_groups": {
                name: patch_groups.get(name) for name in EXPECTED_PATCH_GROUPS
            },
            "current_hd_map_gate": current_hd_map_gate,
            "hidden_redraw_clip_proved": hidden.get("redraw_clip_proved"),
            "hidden_run": {
                "passed": hidden_run.get("Passed"),
                "hidden_desktop": hidden_run.get("HiddenDesktop"),
                "allow_visible_desktop": hidden_run.get("AllowVisibleDesktop"),
                "stage": hidden_run.get("Stage"),
                "candidate_sha256": hidden_run_sha,
            },
            "visible_composition_passed": visible.get("passed"),
            "visible_evidence_class": visible.get("evidence_class"),
            "failed_panel_click_attempt": failed_click,
            "automated_hover_alignment": hover,
            "manual_checklist_status": manual.get("status"),
            "process_hygiene_matching_process_count": process_hygiene.get(
                "matching_process_count"
            ),
        },
        "reasons": [
            "the exact HD-layout patch and current HD map gate are passing",
            "hidden CDB geometry proves the tooltip anchor, all six panel coordinates, and the redraw clip",
            "authentic visible frames prove the relocated tooltip and active lower-right panel composition",
            "the descriptor-5 click attempt was clamped from [760, 560] to [716, 493] and failed alignment",
            "no relocated command callback or manual DirectInput proof exists",
            "the manual DirectInput checklist remains 0/5 and promotion readiness remains false",
            "the protected stable stage remains unchanged and no override is accepted",
        ],
        "next_actions": [
            "keep the protected stable stage unchanged",
            "obtain a correctly aligned real command click and observed callback before reconsidering promotion",
            "complete the five-item manual DirectInput checklist with separately approved visible validation",
        ],
        "failures": failures,
    }


def build_decision(args: argparse.Namespace) -> dict[str, Any]:
    input_specs = (
        ("patch", args.patch_json),
        ("hidden", args.hidden_json),
        ("hidden_run", args.hidden_run_json),
        ("visible", args.visible_json),
        ("manual", args.manual_json),
        ("process_hygiene", args.process_hygiene_json),
    )
    payloads: dict[str, dict[str, Any]] = {}
    input_failures: list[str] = []
    for name, path in input_specs:
        try:
            payloads[name] = load_json(path)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            payloads[name] = {}
            input_failures.append(f"input {name} ({path}): {exc}")
    return evaluate_decision(args, input_failures=input_failures, **payloads)


def print_decision(decision: dict[str, Any]) -> None:
    print(f"hd-layout-promotion-decision: {'PASS' if decision['passed'] else 'FAIL'}")
    print(f"decision: {decision['decision']}")
    print(f"stable-stage-should-change: {decision['stable_stage_should_change']}")
    print(f"current-stable-stage: {decision['current_stable_stage']}")
    print(f"validation-stage: {decision['validation_stage']}")
    print(f"candidate-sha256: {decision['candidate_sha256']}")
    print(f"manual-directinput-proof: {decision['manual_directinput_proof']}")
    print(
        "manual-checklist: "
        f"{decision['manual_checked_item_count']}/{decision['manual_checklist_item_count']}"
    )
    print(f"command-click-alignment: {decision['command_click_alignment']}")
    print(f"panel-click-callback-proof: {decision['panel_click_callback_proof']}")
    print(f"promotion-ready: {decision['promotion_ready']}")
    print(f"override-accepted: {decision['override_accepted']}")
    print("checks:")
    for name, check in decision["checks"].items():
        print(f"  - {name}: {'PASS' if check['passed'] else 'FAIL'}")
    if decision["failures"]:
        print("failures:")
        for failure in decision["failures"]:
            print(f"  - {failure}")


def write_markdown(path: Path, decision: dict[str, Any]) -> None:
    click = decision["evidence"]["failed_panel_click_attempt"]
    lines = [
        "# HD Layout Promotion Decision",
        "",
        f"- Decision record: `{'PASS' if decision['passed'] else 'FAIL'}`",
        f"- Decision: `{decision['decision']}`",
        f"- Stable stage should change: `{decision['stable_stage_should_change']}`",
        f"- Current stable stage: `{decision['current_stable_stage']}`",
        f"- Validation stage: `{decision['validation_stage']}`",
        f"- Candidate SHA-256: `{decision['candidate_sha256']}`",
        f"- Manual DirectInput proof: `{decision['manual_directinput_proof']}`",
        f"- Manual checklist: `{decision['manual_checked_item_count']}/{decision['manual_checklist_item_count']}`",
        f"- Command-click alignment: `{decision['command_click_alignment']}`",
        f"- Panel callback proof: `{decision['panel_click_callback_proof']}`",
        f"- Promotion ready: `{decision['promotion_ready']}`",
        f"- Override accepted: `{decision['override_accepted']}`",
        "",
        "## Required Checks",
        "",
    ]
    lines.extend(
        f"- `{name}`: `{'PASS' if check['passed'] else 'FAIL'}`"
        for name, check in decision["checks"].items()
    )
    lines.extend(
        [
            "",
            "## Evidence Boundary",
            "",
            f"- Tooltip patch group: `{decision['evidence']['patch_groups'].get('terrain-tooltip-bottom-center')}`",
            f"- Panel patch group: `{decision['evidence']['patch_groups'].get('selected-unit-command-panel-right-bottom')}`",
            f"- Current HD map gate: `{decision['evidence']['current_hd_map_gate'].get('passed')}`",
            f"- Hidden redraw clip proved: `{decision['evidence']['hidden_redraw_clip_proved']}`",
            f"- Visible composition passed: `{decision['evidence']['visible_composition_passed']}`",
            f"- Failed click requested / actual / error: `{click.get('requested_client')}` / `{click.get('actual_client')}` / `{click.get('client_error')}`",
            f"- Failed click alignment: `{click.get('alignment_passed')}`",
            "- Visible composition PASS is not command-input, callback, manual DirectInput, or promotion proof.",
            "",
            "## Reasons",
            "",
        ]
    )
    lines.extend(f"- {reason}" for reason in decision["reasons"])
    lines.extend(["", "## Next Actions", ""])
    lines.extend(f"- {action}" for action in decision["next_actions"])
    if decision["failures"]:
        lines.extend(["", "## Failures", ""])
        lines.extend(f"- {failure}" for failure in decision["failures"])
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--patch-json", type=Path, default=DEFAULT_PATCH_JSON)
    parser.add_argument("--hidden-json", type=Path, default=DEFAULT_HIDDEN_JSON)
    parser.add_argument("--hidden-run-json", type=Path, default=DEFAULT_HIDDEN_RUN_JSON)
    parser.add_argument("--visible-json", type=Path, default=DEFAULT_VISIBLE_JSON)
    parser.add_argument("--manual-json", type=Path, default=DEFAULT_MANUAL_JSON)
    parser.add_argument(
        "--process-hygiene-json", type=Path, default=DEFAULT_PROCESS_HYGIENE_JSON
    )
    parser.add_argument("--current-stable-stage", default=PROTECTED_STABLE_STAGE)
    parser.add_argument(
        "--allow-cdb-only-promotion",
        action="store_true",
        help="Rejected fail-closed; retained only so attempted overrides are explicit.",
    )
    parser.add_argument(
        "--promotion-override-manifest",
        type=Path,
        help="Rejected fail-closed; HD-layout promotion requires new direct evidence.",
    )
    parser.add_argument("--write-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--write-markdown", type=Path, default=DEFAULT_OUTPUT_MD)
    parser.add_argument("--require-pass", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    decision = build_decision(args)
    print_decision(decision)
    if args.write_json:
        args.write_json.parent.mkdir(parents=True, exist_ok=True)
        args.write_json.write_text(json.dumps(decision, indent=2) + "\n", encoding="utf-8")
    if args.write_markdown:
        write_markdown(args.write_markdown, decision)
    if args.require_pass and not decision["passed"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
