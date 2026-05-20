#!/usr/bin/env python3
"""Fixture tests for the battle UI evidence matrix helper."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from copy import deepcopy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "battle_ui_evidence_matrix.py"
sys.path.insert(0, str(ROOT / "tools"))

import battle_ui_evidence_matrix  # noqa: E402


SHA = battle_ui_evidence_matrix.EXPECTED_BATTLE_SHA256


def run_script(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def summary(**overrides) -> dict:
    payload = {
        "battle_ready": True,
        "surface_size": [800, 600],
        "visual_mode": "centered-native-640x480",
        "centered_offset": [80, 60],
        "centered_wrapper_seen": True,
        "av_count": 0,
        "hidden_desktop": True,
        "candidate": r"C:\ClashTests\battle\clash95_hd_battle.exe",
        "candidate_sha256": SHA,
        "screenshot": r"captures\fixture\surface.png",
    }
    payload.update(overrides)
    return payload


def good_payloads() -> dict[str, dict]:
    return {
        "force_entry": summary(),
        "command_hit": summary(command_hit_ok=True, command_native_hit_ok=True),
        "command_callback": summary(
            command_callback_ok=True,
            command_callback_result_ok=True,
            last_command_callback_result={"values": {"branch": "precondition-disabled"}},
        ),
        "enabled_callback": summary(
            command_callback_ok=True,
            command_callback_result_ok=True,
            command_render_begin_skip_seen=True,
            last_command_callback_result={"values": {"branch": "state2"}},
        ),
        "grid_hit": summary(
            grid_hit_ok=True,
            last_grid_result={"values": {"cell": [1, 1]}},
            last_grid_hit={"values": {"cell": [0, 0]}},
        ),
        "modal_classified": summary(
            modal_classified=True,
            last_modal_classified={"values": {"status": "input_update_seen_no_modal"}},
        ),
    }


def write_json(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def write_fixture(fixture: Path, payloads: dict[str, dict] | None = None) -> argparse.Namespace:
    payloads = payloads or good_payloads()
    paths = {name: write_json(fixture / f"{name}.json", payload) for name, payload in payloads.items()}
    patch_stage = write_json(
        fixture / "patch-stage.json",
        {
            "exe": r"C:\ClashTests\battle\clash95_hd_battle.exe",
            "stage": battle_ui_evidence_matrix.EXPECTED_STAGE,
            "exe_sha256": SHA,
            "expected_base_sha256": battle_ui_evidence_matrix.EXPECTED_BASE_SHA256,
            "status_counts": {"patched": 136, "original": 0, "unexpected": 0},
            "groups": {"battle-ui-center-present-wrapper": {"patched": 2, "total": 2}},
        },
    )
    stable = write_json(fixture / "stable-smoke.json", {"passed": True})
    return argparse.Namespace(
        force_entry_json=paths["force_entry"],
        command_hit_json=paths["command_hit"],
        command_callback_json=paths["command_callback"],
        enabled_callback_json=paths["enabled_callback"],
        grid_hit_json=paths["grid_hit"],
        modal_classified_json=paths["modal_classified"],
        patch_stage_json=patch_stage,
        stable_smoke_json=stable,
    )


def test_matrix_passes_with_current_evidence_shape(fixture: Path) -> None:
    matrix = battle_ui_evidence_matrix.build_matrix(write_fixture(fixture))
    assert matrix["passed"] is True, matrix
    assert matrix["promotion_status"] == "validation_stage_only", matrix
    assert matrix["stable_stage_should_change"] is False, matrix
    assert matrix["key_evidence"]["grid_visual_cell"] == [1, 1], matrix
    assert matrix["key_evidence"]["grid_native_cell"] == [0, 0], matrix


def test_matrix_fails_closed_for_each_summary(fixture: Path) -> None:
    for name in battle_ui_evidence_matrix.SUMMARY_NAMES:
        payloads = good_payloads()
        payloads[name] = deepcopy(payloads[name])
        payloads[name]["av_count"] = 1
        matrix = battle_ui_evidence_matrix.build_matrix(write_fixture(fixture / name, payloads))
        assert matrix["passed"] is False, matrix
        assert any(name in failure and "AV rows" in failure for failure in matrix["failures"]), matrix


def test_matrix_rejects_feature_regressions(fixture: Path) -> None:
    cases = [
        ("command_hit", "command_hit_ok", False, "visual command hit"),
        ("command_hit", "command_native_hit_ok", False, "native command hit"),
        ("enabled_callback", "command_render_begin_skip_seen", False, "render-begin skip"),
        ("grid_hit", "grid_hit_ok", False, "grid hit"),
        ("modal_classified", "modal_classified", False, "modal path"),
    ]
    for name, key, value, expected in cases:
        payloads = good_payloads()
        payloads[name] = deepcopy(payloads[name])
        payloads[name][key] = value
        matrix = battle_ui_evidence_matrix.build_matrix(write_fixture(fixture / key, payloads))
        assert matrix["passed"] is False, matrix
        assert any(expected in failure for failure in matrix["failures"]), matrix


def test_cli_writes_outputs_and_requires_pass(fixture: Path) -> None:
    args = write_fixture(fixture / "cli")
    out_json = fixture / "matrix.json"
    out_md = fixture / "matrix.md"
    run = run_script(
        "--force-entry-json",
        str(args.force_entry_json),
        "--command-hit-json",
        str(args.command_hit_json),
        "--command-callback-json",
        str(args.command_callback_json),
        "--enabled-callback-json",
        str(args.enabled_callback_json),
        "--grid-hit-json",
        str(args.grid_hit_json),
        "--modal-classified-json",
        str(args.modal_classified_json),
        "--patch-stage-json",
        str(args.patch_stage_json),
        "--stable-smoke-json",
        str(args.stable_smoke_json),
        "--write-json",
        str(out_json),
        "--write-md",
        str(out_md),
        "--require-pass",
    )
    assert run.returncode == 0, run.stdout + run.stderr
    assert json.loads(out_json.read_text(encoding="utf-8"))["passed"] is True
    assert "- Overall: PASS" in out_md.read_text(encoding="utf-8")

    failing = run_script("--force-entry-json", str(fixture / "missing.json"), "--require-pass")
    assert failing.returncode == 2, failing.stdout + failing.stderr


def run_tests() -> None:
    fixture = ROOT / ".codex-loop" / "tmp-tests" / "battle-ui-evidence-matrix-fixture"
    shutil.rmtree(fixture, ignore_errors=True)
    fixture.mkdir(parents=True)
    try:
        test_matrix_passes_with_current_evidence_shape(fixture / "pass")
        test_matrix_fails_closed_for_each_summary(fixture / "summaries")
        test_matrix_rejects_feature_regressions(fixture / "features")
        test_cli_writes_outputs_and_requires_pass(fixture / "cli")
    finally:
        shutil.rmtree(fixture, ignore_errors=True)


def main() -> int:
    run_tests()
    print("battle UI evidence matrix tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
