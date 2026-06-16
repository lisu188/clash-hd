#!/usr/bin/env python3
"""Generate the manual DirectInput proof manifest template.

This is repo-only. It writes an intentionally non-passing JSON template so the
manual proof format is visible without pretending manual input evidence exists.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import manual_directinput_checklist


DEFAULT_TEMPLATE_JSON = Path("captures/current/manual-directinput-proof-template-current.json")
DEFAULT_JSON = Path("captures/current/manual-directinput-proof-template-report-current.json")
DEFAULT_MD = Path("captures/current/manual-directinput-proof-template-current.md")
RUNTIME_POLICY = "repo-only; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows"
GUARD_POLICY = (
    "manual proof template must document the accepted manifest shape while "
    "remaining invalid as proof until approved manual evidence replaces every placeholder"
)
REQUIRED_FIELDS = [
    *manual_directinput_checklist.REQUIRED_MANUAL_PROOF_FIELDS,
]
CANDIDATE_PATH_TEMPLATE = (
    manual_directinput_checklist.EXPECTED_CANDIDATE_ROOT
    + "\\manual-directinput\\REPLACE_WITH_CANDIDATE_EXE"
)
CANDIDATE_PATH_POLICY = (
    "candidate_path must be a freshly built, hashed executable under "
    f"{manual_directinput_checklist.EXPECTED_CANDIDATE_ROOT}; never use "
    f"{manual_directinput_checklist.FORBIDDEN_LIVE_ORIGINAL} or a repository-local executable"
)


def status_text(passed: bool) -> str:
    return "PASS" if passed else "FAIL"


def build_template() -> dict[str, Any]:
    return {
        "template_note": (
            "This template is intentionally not valid proof. Replace placeholders "
            "only after an approved visible/manual DirectInput validation run."
        ),
        "evidence_class": "manual_directinput_template",
        "approved_visible_runtime": False,
        "approval_record": "REPLACE_WITH_APPROVAL_NOTE_OR_LINK",
        "candidate_path_policy": CANDIDATE_PATH_POLICY,
        "candidate_path": CANDIDATE_PATH_TEMPLATE,
        "executable_sha256": "REPLACE_WITH_64_HEX_SHA256",
        "no_stale_processes": False,
        "checked_items": [
            {
                "id": item["id"],
                "title": item["title"],
                "stage": item["stage"],
                "status": "pending",
                "observed_result": "REPLACE_WITH_MANUAL_OBSERVATION",
                "evidence": "REPLACE_WITH_SCREENSHOT_OR_NOTES",
                "pass_fail_notes": "REPLACE_WITH_EXACT_PASS_FAIL_NOTES",
                "no_crash": False,
            }
            for item in manual_directinput_checklist.CHECKLIST_ITEMS
        ],
    }


def build_report(template_json: Path, template: dict[str, Any] | None = None) -> dict[str, Any]:
    template_data = template or build_template()
    template_failures = manual_directinput_checklist.validate_manual_proof_data(template_data)
    template_valid_as_proof = not template_failures
    failures = []
    if template_valid_as_proof:
        failures.append("manual DirectInput proof template unexpectedly validates as proof")
    checked_ids = [
        item.get("id")
        for item in template_data.get("checked_items", [])
        if isinstance(item, dict)
    ]
    missing_template_ids = [
        item_id
        for item_id in manual_directinput_checklist.REQUIRED_IDS
        if item_id not in checked_ids
    ]
    if missing_template_ids:
        failures.append(f"manual DirectInput proof template is missing ids: {missing_template_ids}")
    return {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "passed": not failures,
        "runtime_policy": RUNTIME_POLICY,
        "guard_policy": GUARD_POLICY,
        "candidate_path_policy": CANDIDATE_PATH_POLICY,
        "candidate_path_template": template_data.get("candidate_path"),
        "template_json": str(template_json),
        "template_valid_as_proof": template_valid_as_proof,
        "template_validation_failures": template_failures,
        "required_fields": REQUIRED_FIELDS,
        "required_ids": list(manual_directinput_checklist.REQUIRED_IDS),
        "checked_template_ids": checked_ids,
        "failures": failures,
    }


def print_report(report: dict[str, Any]) -> None:
    print(f"overall: {status_text(bool(report['passed']))}")
    print(f"runtime-policy: {report['runtime_policy']}")
    print(f"guard-policy: {report['guard_policy']}")
    print(f"candidate-path-policy: {report['candidate_path_policy']}")
    print(f"template-json: {report['template_json']}")
    print(f"template-valid-as-proof: {report['template_valid_as_proof']}")
    print(f"required-id-count: {len(report['required_ids'])}")
    if report["failures"]:
        print("failures:")
        for failure in report["failures"]:
            print(f"  - {failure}")


def write_markdown(path: Path, report: dict[str, Any]) -> None:
    lines = [
        "# Manual DirectInput Proof Template",
        "",
        f"- Overall: {status_text(bool(report['passed']))}",
        f"- Generated: `{report['generated_at']}`",
        f"- Runtime policy: {report['runtime_policy']}",
        f"- Guard policy: {report['guard_policy']}",
        f"- Candidate path policy: {report['candidate_path_policy']}",
        f"- Candidate path template: `{report['candidate_path_template']}`",
        f"- Template JSON: `{report['template_json']}`",
        f"- Template valid as proof: `{report['template_valid_as_proof']}`",
        "",
        "## Required Fields",
        "",
    ]
    lines.extend(f"- `{field}`" for field in report["required_fields"])
    lines.extend(["", "## Required Items", ""])
    lines.extend(f"- `{item_id}`" for item_id in report["required_ids"])
    lines.extend(["", "## Why The Template Fails Closed", ""])
    lines.extend(f"- {failure}" for failure in report["template_validation_failures"])
    if report["failures"]:
        lines.extend(["", "## Failures", ""])
        lines.extend(f"- {failure}" for failure in report["failures"])
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-template-json", type=Path, default=DEFAULT_TEMPLATE_JSON)
    parser.add_argument("--write-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--write-markdown", type=Path, default=DEFAULT_MD)
    parser.add_argument("--require-pass", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    template = build_template()
    if args.write_template_json:
        args.write_template_json.parent.mkdir(parents=True, exist_ok=True)
        args.write_template_json.write_text(json.dumps(template, indent=2) + "\n", encoding="utf-8")
    report = build_report(args.write_template_json, template)
    print_report(report)
    if args.write_json:
        args.write_json.parent.mkdir(parents=True, exist_ok=True)
        args.write_json.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if args.write_markdown:
        write_markdown(args.write_markdown, report)
    if args.require_pass and not report["passed"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
