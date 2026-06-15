#!/usr/bin/env python3
"""Report the remaining manual DirectInput validation matrix.

This is a repo-only checklist generator. It does not launch Clash95, CDB,
wrappers, PowerShell, or visible windows. Passing means the remaining manual
validation is explicitly enumerated; it does not mean manual input proof has
been supplied.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_JSON = Path("captures/current/manual-directinput-validation-checklist-current.json")
DEFAULT_MD = Path("captures/current/manual-directinput-validation-checklist-current.md")
RUNTIME_POLICY = "repo-only; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows"
NO_POPUP_OPERATOR_PREFERENCE = (
    "Do not launch Clash95, CDB, wrappers, PowerShell harnesses, or visible "
    "windows unless the user explicitly approves."
)
CHECKLIST_POLICY = (
    "manual DirectInput evidence is tracked separately from CDB/proxy proof; "
    "visible/manual validation requires explicit user approval; "
    f"{NO_POPUP_OPERATOR_PREFERENCE}"
)
CURRENT_STABLE_STAGE = (
    "gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-"
    "minimapright-dynvswitch"
)
RIGHT_BOTTOM_VALIDATION_STAGE = CURRENT_STABLE_STAGE + "-rightbottomcompose"
CASTLE_OVERVIEW_VALIDATION_STAGE = CURRENT_STABLE_STAGE + "-castlecenter-all"

REQUIRED_IDS = [
    "stable_menu_load",
    "stable_hd_map_input",
    "right_bottom_validation_input",
    "castle_barracks_centered_input",
    "castle_overview_centered_input",
]
SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")
PASS_STATUSES = {"pass", "passed"}
PLACEHOLDER_RE = re.compile(r"replace_|placeholder", re.IGNORECASE)
REQUIRED_MANUAL_PROOF_FIELDS = [
    "evidence_class",
    "approved_visible_runtime",
    "approval_record",
    "candidate_path",
    "executable_sha256",
    "no_stale_processes",
    "checked_items",
]
REQUIRED_MANUAL_PROOF_ITEM_FIELDS = [
    "id",
    "stage",
    "status",
    "observed_result",
    "evidence",
    "pass_fail_notes",
    "no_crash",
]

CHECKLIST_ITEMS: list[dict[str, str]] = [
    {
        "id": "stable_menu_load",
        "title": "Stable HD map stage menu load and held-click route",
        "stage": CURRENT_STABLE_STAGE,
        "input_route": "real mouse movement plus held left-clicks on the active desktop",
        "expected_observation": (
            "startup reaches the menu, centered 640x480 menu hitboxes respond, and "
            "held clicks are not missed by DirectInput polling"
        ),
        "current_cdb_evidence": "dynamic-origin/menu CDB and route evidence only",
        "status": "pending_manual",
        "promotion_relevance": "blocks treating synthetic input proof as manual menu proof",
    },
    {
        "id": "stable_hd_map_input",
        "title": "Stable HD map edge scroll, minimap, and selection input",
        "stage": CURRENT_STABLE_STAGE,
        "input_route": "real mouse movement near map edges plus held clicks on map/minimap targets",
        "expected_observation": (
            "map cursor movement, edge scrolling, minimap/action-panel clicks, and "
            "right/bottom tile selection align with the 800x600 presentation"
        ),
        "current_cdb_evidence": "hidden CDB/proxy map and grid-hit evidence only",
        "status": "pending_manual",
        "promotion_relevance": "blocks broader stable HD input promotion",
    },
    {
        "id": "right_bottom_validation_input",
        "title": "Right-bottom composition validation-stage manual input",
        "stage": RIGHT_BOTTOM_VALIDATION_STAGE,
        "input_route": "real mouse movement and held clicks around the recovered lower/right UI",
        "expected_observation": (
            "status/action UI remains recovered while owner/action hit-tests and grid "
            "selection still respond at the expected displayed positions"
        ),
        "current_cdb_evidence": (
            "right-bottom composition matrix, route timing guard, and controlled "
            "native (450,73) grid-hit proof"
        ),
        "status": "pending_manual",
        "promotion_relevance": "blocks promoting rightbottomcompose into the stable stage",
    },
    {
        "id": "castle_barracks_centered_input",
        "title": "Castle barracks centered manual input",
        "stage": CASTLE_OVERVIEW_VALIDATION_STAGE,
        "input_route": "real mouse movement and held clicks on centered barracks descriptors/actions",
        "expected_observation": (
            "barracks descriptor and action callbacks remain reachable through the "
            "centered 80,60 presentation"
        ),
        "current_cdb_evidence": "barracks controlled-stop descriptor/action CDB proof",
        "status": "pending_manual",
        "promotion_relevance": "blocks treating barracks CDB proof as real input proof",
    },
    {
        "id": "castle_overview_centered_input",
        "title": "Full castle overview centered manual input",
        "stage": CASTLE_OVERVIEW_VALIDATION_STAGE,
        "input_route": "real mouse movement and held clicks on visible overview descriptors",
        "expected_observation": (
            "visible overview commands such as 0x86, 0x63, and 0x87 respond at "
            "displayed centered coordinates without using debugger-forced state"
        ),
        "current_cdb_evidence": (
            "focused overview hitbox, visible multi-hit, dormant multi-hit, and "
            "castle overview probe guard evidence"
        ),
        "status": "pending_manual",
        "promotion_relevance": "blocks promoting castlecenter-all into the stable stage",
    },
]


def status_text(passed: bool) -> str:
    return "PASS" if passed else "FAIL"


def validate_items(items: list[dict[str, str]]) -> list[str]:
    failures: list[str] = []
    seen: set[str] = set()
    by_id = {item.get("id", ""): item for item in items}
    for required_id in REQUIRED_IDS:
        if required_id not in by_id:
            failures.append(f"missing required manual checklist item: {required_id}")
    for item in items:
        item_id = item.get("id", "")
        if not item_id:
            failures.append("manual checklist item is missing id")
            continue
        if item_id in seen:
            failures.append(f"duplicate manual checklist item id: {item_id}")
        seen.add(item_id)
        for field in [
            "title",
            "stage",
            "input_route",
            "expected_observation",
            "current_cdb_evidence",
            "status",
            "promotion_relevance",
        ]:
            if not item.get(field):
                failures.append(f"{item_id} is missing required field: {field}")
        if item.get("status") != "pending_manual":
            failures.append(f"{item_id} must remain status=pending_manual until proof is supplied")
    return failures


def _real_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip()) and not PLACEHOLDER_RE.search(value)


def validate_manual_proof_data(proof: Any) -> list[str]:
    failures: list[str] = []
    if not isinstance(proof, dict):
        return ["manual DirectInput proof must be a JSON object"]
    if proof.get("evidence_class") != "manual_directinput":
        failures.append("manual DirectInput proof evidence_class must be manual_directinput")
    if proof.get("approved_visible_runtime") is not True:
        failures.append("manual DirectInput proof must record approved_visible_runtime=true")
    if not _real_text(proof.get("approval_record")):
        failures.append("manual DirectInput proof must include a non-placeholder approval_record")
    if not _real_text(proof.get("candidate_path")):
        failures.append("manual DirectInput proof must include a non-placeholder candidate_path")
    sha = proof.get("executable_sha256")
    if not isinstance(sha, str) or not SHA256_RE.match(sha):
        failures.append("manual DirectInput proof must include a 64-hex executable_sha256")
    if proof.get("no_stale_processes") is not True:
        failures.append("manual DirectInput proof must record no_stale_processes=true")
    checked_items = proof.get("checked_items")
    if not isinstance(checked_items, list):
        failures.append("manual DirectInput proof must include checked_items list")
        return failures

    expected_by_id = {item["id"]: item for item in CHECKLIST_ITEMS}
    passed_ids: set[str] = set()
    for index, item in enumerate(checked_items):
        if not isinstance(item, dict):
            failures.append(f"manual DirectInput proof checked_items[{index}] must be an object")
            continue
        item_id = item.get("id")
        status = item.get("status")
        if item_id not in REQUIRED_IDS:
            failures.append(f"manual DirectInput proof has unknown checked item id: {item_id}")
            continue
        expected_stage = expected_by_id[item_id]["stage"]
        if item.get("stage") != expected_stage:
            failures.append(
                f"manual DirectInput proof item {item_id} must record stage {expected_stage}"
            )
        for field in ["observed_result", "evidence", "pass_fail_notes"]:
            if not _real_text(item.get(field)):
                failures.append(
                    f"manual DirectInput proof item {item_id} must include non-placeholder {field}"
                )
        if item.get("no_crash") is not True:
            failures.append(f"manual DirectInput proof item {item_id} must record no_crash=true")
        if isinstance(status, str) and status.lower() in PASS_STATUSES:
            passed_ids.add(item_id)
        else:
            failures.append(f"manual DirectInput proof item {item_id} must have status pass/passed")

    missing = [item_id for item_id in REQUIRED_IDS if item_id not in passed_ids]
    if missing:
        failures.append(f"manual DirectInput proof is missing passing items: {missing}")
    return failures


def validate_manual_proof(path: Path) -> tuple[dict[str, Any] | None, list[str]]:
    try:
        proof = json.loads(path.read_text(encoding="utf-8-sig"))
    except OSError as exc:
        return None, [f"could not read manual DirectInput proof file: {type(exc).__name__}: {exc}"]
    except json.JSONDecodeError as exc:
        return None, [f"manual DirectInput proof file is not valid JSON: {exc}"]

    if not isinstance(proof, dict):
        return None, ["manual DirectInput proof must be a JSON object"]
    return proof, validate_manual_proof_data(proof)


def build_checklist(
    args: argparse.Namespace,
    items: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    checklist_items = [dict(item) for item in (items or CHECKLIST_ITEMS)]
    failures = validate_items(checklist_items)
    manual_proof = getattr(args, "manual_proof", None)
    allow_cdb_only_promotion = bool(getattr(args, "allow_cdb_only_promotion", False))
    manual_proof_supplied = False
    manual_proof_valid = False
    manual_proof_data: dict[str, Any] | None = None
    if manual_proof:
        manual_proof = Path(manual_proof)
        if manual_proof.exists():
            manual_proof_supplied = True
            manual_proof_data, proof_failures = validate_manual_proof(manual_proof)
            if proof_failures:
                failures.extend(proof_failures)
            else:
                manual_proof_valid = True
        else:
            failures.append(f"manual DirectInput proof file does not exist: {manual_proof}")

    pending_ids = [
        item["id"]
        for item in checklist_items
        if item.get("status") == "pending_manual"
    ]
    promotion_ready = bool(manual_proof_valid or allow_cdb_only_promotion)
    return {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "passed": not failures,
        "runtime_policy": RUNTIME_POLICY,
        "checklist_policy": CHECKLIST_POLICY,
        "no_popup_operator_preference": NO_POPUP_OPERATOR_PREFERENCE,
        "status": "pending_manual_validation",
        "visible_runtime_requires_approval": True,
        "stable_stage_should_change": False,
        "manual_proof": str(manual_proof) if manual_proof else None,
        "manual_proof_supplied": manual_proof_supplied,
        "manual_proof_valid": manual_proof_valid,
        "manual_proof_summary": {
            "executable_sha256": manual_proof_data.get("executable_sha256") if manual_proof_data else None,
            "checked_item_count": len(manual_proof_data.get("checked_items", [])) if manual_proof_data else 0,
        },
        "allow_cdb_only_promotion": allow_cdb_only_promotion,
        "promotion_ready": promotion_ready,
        "items": checklist_items,
        "summary": {
            "item_count": len(checklist_items),
            "pending_count": len(pending_ids),
            "pending_ids": pending_ids,
            "promotion_ready": promotion_ready,
            "stable_stage_should_change": False,
        },
        "failures": failures,
    }


def print_checklist(checklist: dict[str, Any]) -> None:
    print(f"overall: {status_text(bool(checklist['passed']))}")
    print(f"runtime-policy: {checklist['runtime_policy']}")
    print(f"checklist-policy: {checklist['checklist_policy']}")
    print(f"status: {checklist['status']}")
    print(f"promotion-ready: {checklist['promotion_ready']}")
    print(f"pending-count: {checklist['summary']['pending_count']}")
    if checklist["failures"]:
        print("failures:")
        for failure in checklist["failures"]:
            print(f"  - {failure}")


def write_markdown(path: Path, checklist: dict[str, Any]) -> None:
    lines = [
        "# Manual DirectInput Validation Checklist",
        "",
        f"- Overall: {status_text(bool(checklist['passed']))}",
        f"- Generated: `{checklist['generated_at']}`",
        f"- Runtime policy: {checklist['runtime_policy']}",
        f"- Checklist policy: {checklist['checklist_policy']}",
        f"- No-popup operator preference: {checklist['no_popup_operator_preference']}",
        f"- Status: `{checklist['status']}`",
        f"- Promotion ready: `{checklist['promotion_ready']}`",
        f"- Stable stage should change: `{checklist['stable_stage_should_change']}`",
        f"- Visible runtime requires approval: `{checklist['visible_runtime_requires_approval']}`",
        f"- Manual proof supplied: `{checklist['manual_proof_supplied']}`",
        f"- Manual proof valid: `{checklist['manual_proof_valid']}`",
        f"- Explicit CDB-only override: `{checklist['allow_cdb_only_promotion']}`",
        "",
        "## Checklist",
        "",
    ]
    for item in checklist["items"]:
        lines.extend(
            [
                f"### {item['title']}",
                "",
                f"- ID: `{item['id']}`",
                f"- Stage: `{item['stage']}`",
                f"- Status: `{item['status']}`",
                f"- Input route: {item['input_route']}",
                f"- Expected observation: {item['expected_observation']}",
                f"- Current CDB evidence: {item['current_cdb_evidence']}",
                f"- Promotion relevance: {item['promotion_relevance']}",
                "",
            ]
        )
    if checklist["failures"]:
        lines.extend(["## Failures", ""])
        lines.extend(f"- {failure}" for failure in checklist["failures"])
        lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manual-proof", type=Path)
    parser.add_argument("--allow-cdb-only-promotion", action="store_true")
    parser.add_argument("--write-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--write-markdown", type=Path, default=DEFAULT_MD)
    parser.add_argument("--require-pass", action="store_true")
    parser.add_argument("--require-promotion-ready", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    checklist = build_checklist(args)
    print_checklist(checklist)
    if args.write_json:
        args.write_json.parent.mkdir(parents=True, exist_ok=True)
        args.write_json.write_text(json.dumps(checklist, indent=2) + "\n", encoding="utf-8")
    if args.write_markdown:
        write_markdown(args.write_markdown, checklist)
    if args.require_pass and not checklist["passed"]:
        return 2
    if args.require_promotion_ready and not checklist["promotion_ready"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
