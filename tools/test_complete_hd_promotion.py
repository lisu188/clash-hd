#!/usr/bin/env python3
"""Fixture tests for the HD promotion orchestrator.

These exercise the ordered step plan and the checklist-box update as pure
functions, so they never launch the promotion sub-tools (which would write to
captures/current) and stay deterministic.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import complete_hd_promotion as promo  # noqa: E402


def _args(**overrides):
    argv = ["--run-manifest", "captures/archive/run/run-manifest.json"]
    for key, value in overrides.items():
        flag = "--" + key.replace("_", "-")
        if value is True:
            argv.append(flag)
        elif value is not None:
            argv.extend([flag, str(value)])
    return promo.parse_args(argv)


def test_step_plan_order_without_battle() -> None:
    steps = promo.plan_steps(_args())
    names = [name for name, _ in steps]
    assert names == [
        "assemble_proof",
        "manual_checklist",
        "right_bottom_promotion",
        "castle_overview_promotion",
    ], names


def test_step_plan_includes_battle_when_dir_given() -> None:
    steps = promo.plan_steps(_args(battle_run_dir="captures/archive/battle"))
    names = [name for name, _ in steps]
    assert "battle_click_consumed" in names
    assert names.index("battle_click_consumed") == 2, names


def test_step_flags_reference_proof_and_manifest() -> None:
    args = _args(observations="obs.json", proof_json="p.json")
    steps = dict(promo.plan_steps(args))
    assemble = " ".join(steps["assemble_proof"])
    assert "assemble_manual_directinput_proof.py" in assemble
    assert "--run-manifest" in assemble and "--observations obs.json" in assemble
    assert "--output p.json" in assemble and "--require-valid" in assemble
    for key in ("right_bottom_promotion", "castle_overview_promotion"):
        joined = " ".join(steps[key])
        assert "--manual-input-proof p.json" in joined, joined
        assert "--require-pass" in joined
    checklist = " ".join(steps["manual_checklist"])
    assert "--require-promotion-ready" in checklist


def test_check_release_boxes_updates_both(fixture: Path) -> None:
    md = fixture / "checklist.md"
    md.write_text(
        "# Final HD Release Checklist\n\n"
        "- [x] Base SHA matches.\n"
        "- [ ] Manual DirectInput proof manifest passes for all five required targets.\n"
        "- [ ] Promotion decision tools allow stable promotion.\n",
        encoding="utf-8",
    )
    changed = promo.check_release_boxes(md)
    assert changed == md
    text = md.read_text(encoding="utf-8")
    assert "- [x] Manual DirectInput proof manifest passes for all five required targets." in text
    assert "- [x] Promotion decision tools allow stable promotion." in text
    # Idempotent: second call makes no change.
    assert promo.check_release_boxes(md) is None


def run_tests() -> None:
    fixture = ROOT / ".codex-loop" / "tmp-tests" / "complete-hd-promotion"
    shutil.rmtree(fixture, ignore_errors=True)
    fixture.mkdir(parents=True)
    try:
        test_step_plan_order_without_battle()
        test_step_plan_includes_battle_when_dir_given()
        test_step_flags_reference_proof_and_manifest()
        test_check_release_boxes_updates_both(fixture)
    finally:
        shutil.rmtree(fixture, ignore_errors=True)


def main() -> int:
    run_tests()
    print("complete HD promotion tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
