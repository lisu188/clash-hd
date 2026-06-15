#!/usr/bin/env python3
"""Verify current evidence has no active CDB-only promotion override.

This is a repo-only guard. It reads existing promotion/checklist reports and
does not launch Clash95, CDB, wrappers, PowerShell, or any visible GUI process.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_RIGHT_BOTTOM_DECISION = Path("captures/current/right-bottom-compose-promotion-decision-current.json")
DEFAULT_CASTLE_DECISION = Path("captures/current/castle-overview-promotion-decision-current.json")
DEFAULT_MANUAL_CHECKLIST = Path("captures/current/manual-directinput-validation-checklist-current.json")
DEFAULT_JSON = Path("captures/current/promotion-override-guard-current.json")
DEFAULT_MD = Path("captures/current/promotion-override-guard-current.md")
RUNTIME_POLICY = "repo-only; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows"
GUARD_POLICY = (
    "current evidence must keep CDB-only promotion overrides inactive until "
    "manual proof or an explicit override decision is intentionally supplied"
)


def status_text(passed: bool) -> str:
    return "PASS" if passed else "FAIL"


def load_json(path: Path) -> tuple[dict[str, Any], list[str]]:
    if not path.exists():
        return {}, [f"missing JSON: {path}"]
    try:
        return json.loads(path.read_text(encoding="utf-8-sig")), []
    except (OSError, json.JSONDecodeError) as exc:
        return {}, [f"could not read {path}: {type(exc).__name__}: {exc}"]


def check_promotion_decision(label: str, path: Path) -> dict[str, Any]:
    payload, failures = load_json(path)
    if failures:
        return {
            "passed": False,
            "path": str(path),
            "summary": {},
            "failures": [f"{label}: {failure}" for failure in failures],
        }

    decision = payload.get("decision")
    allow_override = bool(payload.get("allow_cdb_only_promotion"))
    stable_stage_should_change = bool(payload.get("stable_stage_should_change"))
    manual_valid = bool(payload.get("manual_input_proof_valid"))
    manual_supplied = bool(payload.get("manual_input_proof_supplied"))
    passed = bool(payload.get("passed"))

    if decision != "defer_stable_promotion":
        failures.append(f"{label}: decision is {decision!r}, expected 'defer_stable_promotion'")
    if allow_override:
        failures.append(f"{label}: allow_cdb_only_promotion is active")
    if stable_stage_should_change:
        failures.append(f"{label}: stable_stage_should_change is true")
    if manual_valid:
        failures.append(f"{label}: manual_input_proof_valid is true in current no-popup evidence")
    if manual_supplied:
        failures.append(f"{label}: manual_input_proof_supplied is true in current no-popup evidence")

    return {
        "passed": not failures,
        "path": str(path),
        "summary": {
            "decision": decision,
            "passed": passed,
            "allow_cdb_only_promotion": allow_override,
            "stable_stage_should_change": stable_stage_should_change,
            "manual_input_proof_supplied": manual_supplied,
            "manual_input_proof_valid": manual_valid,
            "validation_stage": payload.get("validation_stage"),
        },
        "failures": failures,
    }


def check_manual_checklist(path: Path) -> dict[str, Any]:
    payload, failures = load_json(path)
    if failures:
        return {
            "passed": False,
            "path": str(path),
            "summary": {},
            "failures": [f"manual_checklist: {failure}" for failure in failures],
        }

    passed = bool(payload.get("passed"))
    allow_override = bool(payload.get("allow_cdb_only_promotion"))
    promotion_ready = bool(payload.get("promotion_ready"))
    manual_valid = bool(payload.get("manual_proof_valid"))
    manual_supplied = bool(payload.get("manual_proof_supplied"))
    stable_stage_should_change = bool(payload.get("stable_stage_should_change"))

    if not passed:
        failures.append("manual_checklist: checklist is not passing")
    if allow_override:
        failures.append("manual_checklist: allow_cdb_only_promotion is active")
    if promotion_ready:
        failures.append("manual_checklist: promotion_ready is true")
    if manual_valid:
        failures.append("manual_checklist: manual_proof_valid is true in current no-popup evidence")
    if manual_supplied:
        failures.append("manual_checklist: manual_proof_supplied is true in current no-popup evidence")
    if stable_stage_should_change:
        failures.append("manual_checklist: stable_stage_should_change is true")

    return {
        "passed": not failures,
        "path": str(path),
        "summary": {
            "passed": passed,
            "status": payload.get("status"),
            "allow_cdb_only_promotion": allow_override,
            "promotion_ready": promotion_ready,
            "manual_proof_supplied": manual_supplied,
            "manual_proof_valid": manual_valid,
            "stable_stage_should_change": stable_stage_should_change,
        },
        "failures": failures,
    }


def build_guard(args: argparse.Namespace) -> dict[str, Any]:
    checks = {
        "right_bottom_compose_promotion_decision": check_promotion_decision(
            "right_bottom_compose_promotion_decision",
            args.right_bottom_decision,
        ),
        "castle_overview_promotion_decision": check_promotion_decision(
            "castle_overview_promotion_decision",
            args.castle_decision,
        ),
        "manual_directinput_checklist": check_manual_checklist(args.manual_checklist),
    }
    failures: list[str] = []
    for check in checks.values():
        failures.extend(check.get("failures") or [])

    return {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "passed": not failures,
        "runtime_policy": RUNTIME_POLICY,
        "guard_policy": GUARD_POLICY,
        "checks": checks,
        "failures": failures,
    }


def print_guard(guard: dict[str, Any]) -> None:
    print(f"overall: {status_text(bool(guard['passed']))}")
    print(f"runtime-policy: {guard['runtime_policy']}")
    print(f"guard-policy: {guard['guard_policy']}")
    for name, check in guard["checks"].items():
        print(f"{name}: {status_text(bool(check.get('passed')))}")
    if guard["failures"]:
        print("failures:")
        for failure in guard["failures"]:
            print(f"  - {failure}")


def write_markdown(path: Path, guard: dict[str, Any]) -> None:
    lines = [
        "# Promotion Override Guard",
        "",
        f"- Overall: {status_text(bool(guard['passed']))}",
        f"- Generated: `{guard['generated_at']}`",
        f"- Runtime policy: {guard['runtime_policy']}",
        f"- Guard policy: {guard['guard_policy']}",
        "",
        "## Checks",
        "",
    ]
    for name, check in guard["checks"].items():
        summary = check.get("summary") or {}
        lines.append(
            "- `{name}`: `{status}` override=`{override}` stable_change=`{stable}` proof_valid=`{proof}`".format(
                name=name,
                status=status_text(bool(check.get("passed"))),
                override=summary.get("allow_cdb_only_promotion"),
                stable=summary.get("stable_stage_should_change"),
                proof=summary.get("manual_input_proof_valid", summary.get("manual_proof_valid")),
            )
        )
        for failure in check.get("failures", []):
            lines.append(f"  - {failure}")
    if guard["failures"]:
        lines.extend(["", "## Failures", ""])
        lines.extend(f"- {failure}" for failure in guard["failures"])
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--right-bottom-decision", type=Path, default=DEFAULT_RIGHT_BOTTOM_DECISION)
    parser.add_argument("--castle-decision", type=Path, default=DEFAULT_CASTLE_DECISION)
    parser.add_argument("--manual-checklist", type=Path, default=DEFAULT_MANUAL_CHECKLIST)
    parser.add_argument("--write-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--write-markdown", type=Path, default=DEFAULT_MD)
    parser.add_argument("--require-pass", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    guard = build_guard(args)
    print_guard(guard)
    if args.write_json:
        args.write_json.parent.mkdir(parents=True, exist_ok=True)
        args.write_json.write_text(json.dumps(guard, indent=2) + "\n", encoding="utf-8")
    if args.write_markdown:
        write_markdown(args.write_markdown, guard)
    if args.require_pass and not guard["passed"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
