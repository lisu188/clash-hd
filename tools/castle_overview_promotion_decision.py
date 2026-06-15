#!/usr/bin/env python3
"""Record a repo-only castle overview promotion decision.

The evidence matrix can prove the current castle overview validation stage
without launching the game. This helper turns that result into an explicit
promotion decision so the stable HD map stage is not changed silently.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import manual_directinput_checklist
import promotion_override_manifest


DEFAULT_MATRIX = Path("captures/current/castle-overview-evidence-current.json")
DEFAULT_STABLE_STAGE = (
    "gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-"
    "presentbounds-minimapright-dynvswitch"
)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def all_targets_completed(check: dict[str, Any]) -> bool:
    targets = check.get("targets") or []
    return bool(targets) and all(target.get("completion_ok") is True for target in targets)


def build_proof_summary(matrix: dict[str, Any]) -> dict[str, Any]:
    checks = matrix.get("checks", {})
    focused = checks.get("focused_hitbox") or {}
    visible = checks.get("visible_multihit") or {}
    dormant = checks.get("dormant_multihit") or {}
    return {
        "focused_hitbox_passed": bool(focused.get("passed")),
        "focused_displayed_wrapper_ok": bool(focused.get("displayed_wrapper_ok")),
        "focused_av_count": int(focused.get("av_count") or 0),
        "visible_multihit_passed": bool(visible.get("passed")),
        "visible_multihit_completion_ok": all_targets_completed(visible),
        "visible_multihit_target_count": len(visible.get("targets") or []),
        "visible_multihit_av_count": int(visible.get("av_count") or 0),
        "dormant_multihit_passed": bool(dormant.get("passed")),
        "dormant_multihit_completion_ok": all_targets_completed(dormant),
        "dormant_multihit_target_count": len(dormant.get("targets") or []),
        "dormant_multihit_av_count": int(dormant.get("av_count") or 0),
    }


def proof_summary_failures(proof: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    if not proof["focused_hitbox_passed"]:
        failures.append("focused overview hitbox gate is not passing")
    if not proof["focused_displayed_wrapper_ok"]:
        failures.append("focused overview hitbox displayed-wrapper proof is missing")
    if proof["focused_av_count"]:
        failures.append("focused overview hitbox AV rows were observed")
    if not proof["visible_multihit_passed"]:
        failures.append("visible-command multi-hit gate is not passing")
    if not proof["visible_multihit_completion_ok"]:
        failures.append("visible-command multi-hit target-done completion proof is missing")
    if proof["visible_multihit_av_count"]:
        failures.append("visible-command multi-hit AV rows were observed")
    if not proof["dormant_multihit_passed"]:
        failures.append("dormant-command multi-hit gate is not passing")
    if not proof["dormant_multihit_completion_ok"]:
        failures.append("dormant-command multi-hit target-done completion proof is missing")
    if proof["dormant_multihit_av_count"]:
        failures.append("dormant-command multi-hit AV rows were observed")
    return failures


def validate_manual_input_proof(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {
            "path": None,
            "supplied": False,
            "valid": False,
            "summary": {
                "executable_sha256": None,
                "checked_item_count": 0,
            },
            "failures": [],
        }

    proof, failures = manual_directinput_checklist.validate_manual_proof(path)
    return {
        "path": str(path),
        "supplied": True,
        "valid": proof is not None and not failures,
        "summary": {
            "executable_sha256": proof.get("executable_sha256") if proof else None,
            "checked_item_count": len(proof.get("checked_items", [])) if proof else 0,
        },
        "failures": failures,
    }


def build_decision(args: argparse.Namespace) -> dict[str, Any]:
    failures: list[str] = []
    matrix = load_json(args.matrix)
    matrix_passed = bool(matrix.get("passed"))
    if not matrix_passed:
        failures.append("castle overview evidence matrix is not passing")
    proof = build_proof_summary(matrix)
    failures.extend(proof_summary_failures(proof))

    patch_stage = matrix.get("checks", {}).get("patch_stage", {})
    resolved_validation_stage = patch_stage.get("resolved_stage") or matrix.get("stage")
    manual_input_proof = validate_manual_input_proof(getattr(args, "manual_input_proof", None))
    failures.extend(manual_input_proof["failures"])
    manual_input_proof_valid = bool(manual_input_proof["valid"])
    cdb_only_override = bool(getattr(args, "allow_cdb_only_promotion", False))
    override_manifest = promotion_override_manifest.validate_manifest(
        getattr(args, "promotion_override_manifest", None),
        expected_target_scope="castle_overview",
        expected_candidate_stage=resolved_validation_stage,
        expected_candidate_sha256=patch_stage.get("sha256"),
    )
    failures.extend(override_manifest["failures"])
    override_manifest_valid = bool(override_manifest["valid"])
    bare_override_blocked = bool(cdb_only_override and not override_manifest["supplied"])
    if bare_override_blocked:
        failures.append(
            "bare --allow-cdb-only-promotion is blocked; supply --promotion-override-manifest"
        )
    evidence_ready = (
        matrix_passed
        and not proof_summary_failures(proof)
        and not manual_input_proof["failures"]
        and not override_manifest["failures"]
        and not bare_override_blocked
    )

    if evidence_ready and manual_input_proof_valid:
        decision = "eligible_for_stable_promotion"
        stable_stage_should_change = True
        reasons = [
            "castle overview evidence matrix is passing",
            "focused displayed-wrapper and multi-hit completion proof is present",
            f"manual/real input proof was supplied: {args.manual_input_proof}",
        ]
    elif evidence_ready and override_manifest_valid:
        decision = "eligible_for_override_manifest_promotion"
        stable_stage_should_change = True
        reasons = [
            "castle overview evidence matrix is passing",
            "focused displayed-wrapper and multi-hit completion proof is present",
            f"CDB/proxy-only promotion override manifest is valid: {override_manifest['path']}",
        ]
    else:
        decision = "defer_stable_promotion"
        stable_stage_should_change = False
        reasons = [
            "castle overview evidence matrix is passing" if matrix_passed else "castle overview evidence matrix is not passing",
            (
                "focused displayed-wrapper and multi-hit completion proof is present"
                if not proof_summary_failures(proof)
                else "focused displayed-wrapper or multi-hit completion proof is incomplete"
            ),
            "current proof is repo-only CDB/proxy evidence",
            "manual/visible DirectInput validation has not been supplied"
            if not manual_input_proof["supplied"]
            else "manual/visible DirectInput proof was supplied but failed manifest validation",
            "promotion override manifest is valid"
            if override_manifest_valid
            else (
                "bare CDB-only promotion flag is blocked without a manifest"
                if bare_override_blocked
                else "promotion override manifest has not been supplied"
            ),
            "visible/manual runs require explicit user approval",
        ]

    next_actions = []
    if decision == "defer_stable_promotion":
        next_actions.extend(
            [
                "keep the patcher default stable HD map stage unchanged",
                "keep castle overview wrappers scoped to castlecenter-all",
                "continue with repo-only or hidden-desktop/CDB evidence only",
                "request explicit approval before any visible/manual input validation",
            ]
        )
    else:
        next_actions.extend(
            [
                "update the patcher default or stable stage intentionally",
                "rerun patch byte and evidence gates after any stage change",
                "document the promotion scope and evidence class",
            ]
        )

    return {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "passed": not failures,
        "decision": decision,
        "stable_stage_should_change": stable_stage_should_change,
        "current_stable_stage": args.current_stable_stage,
        "validation_stage": matrix.get("stage"),
        "resolved_validation_stage": resolved_validation_stage,
        "candidate_sha256": patch_stage.get("sha256"),
        "matrix": {
            "path": str(args.matrix),
            "passed": matrix_passed,
            "promotion_status": matrix.get("promotion_status"),
            "runtime_policy": matrix.get("runtime_policy"),
        },
        "proof": proof,
        "manual_input_proof": str(args.manual_input_proof) if args.manual_input_proof else None,
        "manual_input_proof_supplied": bool(manual_input_proof["supplied"]),
        "manual_input_proof_valid": manual_input_proof_valid,
        "manual_input_proof_summary": manual_input_proof["summary"],
        "allow_cdb_only_promotion": cdb_only_override,
        "bare_cdb_only_promotion_blocked": bare_override_blocked,
        "promotion_override_manifest": override_manifest["path"],
        "promotion_override_manifest_supplied": bool(override_manifest["supplied"]),
        "promotion_override_manifest_valid": override_manifest_valid,
        "promotion_override_manifest_summary": override_manifest["summary"],
        "reasons": reasons,
        "next_actions": next_actions,
        "failures": failures,
    }


def print_decision(decision: dict[str, Any]) -> None:
    print(f"decision-record: {'PASS' if decision['passed'] else 'FAIL'}")
    print(f"decision: {decision['decision']}")
    print(f"stable-stage-should-change: {decision['stable_stage_should_change']}")
    print(f"current-stable-stage: {decision['current_stable_stage']}")
    print(f"validation-stage: {decision['validation_stage']}")
    print(f"candidate-sha256: {decision.get('candidate_sha256')}")
    print(f"manual-input-proof-valid: {decision['manual_input_proof_valid']}")
    print(f"promotion-override-manifest-valid: {decision['promotion_override_manifest_valid']}")
    print(f"bare-cdb-only-promotion-blocked: {decision['bare_cdb_only_promotion_blocked']}")
    proof = decision["proof"]
    print(f"focused-displayed-wrapper-ok: {proof['focused_displayed_wrapper_ok']}")
    print(f"visible-multihit-completion-ok: {proof['visible_multihit_completion_ok']}")
    print(f"dormant-multihit-completion-ok: {proof['dormant_multihit_completion_ok']}")
    print("reasons:")
    for reason in decision["reasons"]:
        print(f"  - {reason}")
    if decision["failures"]:
        print("failures:")
        for failure in decision["failures"]:
            print(f"  - {failure}")


def write_markdown(path: Path, decision: dict[str, Any]) -> None:
    lines = [
        "# Castle Overview Promotion Decision",
        "",
        f"- Decision record: {'PASS' if decision['passed'] else 'FAIL'}",
        f"- Decision: `{decision['decision']}`",
        f"- Stable stage should change: `{decision['stable_stage_should_change']}`",
        f"- Generated: `{decision['generated_at']}`",
        f"- Current stable stage: `{decision['current_stable_stage']}`",
        f"- Validation stage: `{decision['validation_stage']}`",
        f"- Resolved validation stage: `{decision['resolved_validation_stage']}`",
        f"- Candidate SHA-256: `{decision['candidate_sha256']}`",
        f"- Evidence matrix: `{decision['matrix']['path']}`",
        f"- Matrix status: `{decision['matrix']['passed']}`",
        f"- Matrix promotion status: `{decision['matrix']['promotion_status']}`",
        f"- Runtime policy: {decision['matrix']['runtime_policy']}",
        f"- Focused displayed-wrapper proof: `{decision['proof']['focused_displayed_wrapper_ok']}`",
        f"- Visible target completion proof: `{decision['proof']['visible_multihit_completion_ok']}`",
        f"- Visible target count: `{decision['proof']['visible_multihit_target_count']}`",
        f"- Dormant target completion proof: `{decision['proof']['dormant_multihit_completion_ok']}`",
        f"- Dormant target count: `{decision['proof']['dormant_multihit_target_count']}`",
        f"- Manual input proof: `{decision['manual_input_proof']}`",
        f"- Manual input proof supplied: `{decision['manual_input_proof_supplied']}`",
        f"- Manual input proof valid: `{decision['manual_input_proof_valid']}`",
        f"- Manual input proof SHA-256: `{decision['manual_input_proof_summary'].get('executable_sha256')}`",
        f"- Manual input proof checked items: `{decision['manual_input_proof_summary'].get('checked_item_count')}`",
        f"- CDB-only promotion override: `{decision['allow_cdb_only_promotion']}`",
        f"- Bare CDB-only promotion blocked: `{decision['bare_cdb_only_promotion_blocked']}`",
        f"- Promotion override manifest: `{decision['promotion_override_manifest']}`",
        f"- Promotion override manifest supplied: `{decision['promotion_override_manifest_supplied']}`",
        f"- Promotion override manifest valid: `{decision['promotion_override_manifest_valid']}`",
        f"- Promotion override scope: `{decision['promotion_override_manifest_summary'].get('target_scope')}`",
        f"- Promotion override SHA-256: `{decision['promotion_override_manifest_summary'].get('candidate_sha256')}`",
        "",
        "## Reasons",
        "",
    ]
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
    parser.add_argument("--matrix", type=Path, default=DEFAULT_MATRIX)
    parser.add_argument("--current-stable-stage", default=DEFAULT_STABLE_STAGE)
    parser.add_argument("--manual-input-proof", type=Path)
    parser.add_argument("--allow-cdb-only-promotion", action="store_true")
    parser.add_argument("--promotion-override-manifest", type=Path)
    parser.add_argument("--write-json", type=Path)
    parser.add_argument("--write-markdown", type=Path)
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
