#!/usr/bin/env python3
"""Fixture tests for border_frame_restore_check.py."""

from __future__ import annotations

import argparse
import copy
import json
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "border_frame_restore_check.py"
sys.path.insert(0, str(ROOT / "tools"))

import border_frame_restore_check  # noqa: E402


def run_script(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def region_payload(name: str, nonblack_percent: float) -> dict:
    return {
        "name": name,
        "logical_rect": list(border_frame_restore_check.border_frame_bounds.DEFAULT_REGIONS[name]),
        "nonblack_percent": nonblack_percent,
        "black_percent": round(100.0 - nonblack_percent, 3),
        "mean_luma": 60.0,
        "flags": [],
    }


def image_payload(source_frame: Path, *, similarity: float = 0.68) -> dict:
    regions = []
    for name in border_frame_restore_check.REQUIRED_BANDS:
        if name in border_frame_restore_check.EXTENSION_BANDS:
            nonblack = 100.0
        elif name == "bottom_letterbox":
            nonblack = 0.0
        else:
            nonblack = 100.0
        regions.append(region_payload(name, nonblack))
    matches = [
        {
            "dest": dest,
            "source": source,
            "similarity": similarity,
            "dest_nonblack_percent": 100.0,
            "source_nonblack_percent": 100.0,
        }
        for dest, source in border_frame_restore_check.REQUIRED_MATCH_PAIRS.items()
    ]
    gate_checks = []
    for band in border_frame_restore_check.EXTENSION_BANDS:
        gate_checks.append(
            {
                "kind": "nonblack",
                "region": band,
                "minimum_nonblack_percent": 95.0,
                "actual_nonblack_percent": 100.0,
                "passed": True,
            }
        )
    for dest, source in border_frame_restore_check.REQUIRED_MATCH_PAIRS.items():
        gate_checks.append(
            {
                "kind": "match",
                "dest": dest,
                "source": source,
                "minimum_similarity": 0.3,
                "actual_similarity": similarity,
                "passed": True,
            }
        )
    return {
        "path": str(source_frame),
        "image": {"width": 800, "height": 600},
        "logical_size": {"width": 800, "height": 600},
        "scale": {"x": 1.0, "y": 1.0},
        "regions": regions,
        "matches": matches,
        "gate": {"passed": True, "checks": gate_checks, "failures": []},
    }


def evidence_payload(source_frame: Path, *, similarity: float = 0.68) -> dict:
    return {
        "parameters": {
            "logical_width": 800,
            "logical_height": 600,
            "threshold": 12,
        },
        "regions": [
            {"name": name, "logical_rect": list(rect)}
            for name, rect in border_frame_restore_check.border_frame_bounds.DEFAULT_REGIONS.items()
        ],
        "images": [image_payload(source_frame, similarity=similarity)],
    }


def write_fixture(fixture: Path) -> argparse.Namespace:
    fixture.mkdir(parents=True, exist_ok=True)
    proxy_frame = fixture / "cdb-surface-dump-fixture" / "surface.png"
    real_frame = fixture / "visual-smoke-fixture" / "after-map-path.png"
    for frame in (proxy_frame, real_frame):
        frame.parent.mkdir(parents=True, exist_ok=True)
        frame.write_bytes(b"png-fixture")
    evidence_json = fixture / "border-frame-restore-current.json"
    realruntime_json = fixture / "border-frame-restore-realruntime-current.json"
    write_json(evidence_json, evidence_payload(proxy_frame))
    write_json(realruntime_json, evidence_payload(real_frame))
    return argparse.Namespace(
        evidence_json=evidence_json,
        realruntime_json=realruntime_json,
        proxy_run_token=border_frame_restore_check.DEFAULT_PROXY_RUN_TOKEN,
        real_runtime_run_token=border_frame_restore_check.DEFAULT_REAL_RUNTIME_RUN_TOKEN,
        repo_root=fixture,
    )


def rewrite_realruntime(args: argparse.Namespace, mutate) -> None:
    payload = json.loads(args.realruntime_json.read_text(encoding="utf-8"))
    mutate(payload)
    write_json(args.realruntime_json, payload)


def test_committed_shape_passes(fixture: Path) -> None:
    args = write_fixture(fixture)
    report = border_frame_restore_check.build_check(args)
    assert report["passed"] is True, report
    assert report["real_runtime_frames"], report
    assert "visual-smoke-fixture" in report["real_runtime_frames"][0], report


def test_missing_evidence_file_fails(fixture: Path) -> None:
    args = write_fixture(fixture)
    args.evidence_json = fixture / "does-not-exist.json"
    report = border_frame_restore_check.build_check(args)
    assert report["passed"] is False, report
    assert any("border evidence is missing" in failure for failure in report["failures"]), report


def test_missing_band_fails(fixture: Path) -> None:
    args = write_fixture(fixture)

    def drop_band(payload: dict) -> None:
        payload["images"][0]["regions"] = [
            region
            for region in payload["images"][0]["regions"]
            if region["name"] != "left_frame_hd_extension"
        ]

    rewrite_realruntime(args, drop_band)
    report = border_frame_restore_check.build_check(args)
    assert report["passed"] is False, report
    assert any("missing border bands" in failure for failure in report["failures"]), report


def test_black_extension_band_fails(fixture: Path) -> None:
    args = write_fixture(fixture)

    def blacken(payload: dict) -> None:
        for region in payload["images"][0]["regions"]:
            if region["name"] == "top_right_extension":
                region["nonblack_percent"] = 0.0

    rewrite_realruntime(args, blacken)
    report = border_frame_restore_check.build_check(args)
    assert report["passed"] is False, report
    assert any("is not filled" in failure for failure in report["failures"]), report


def test_low_similarity_fails(fixture: Path) -> None:
    args = write_fixture(fixture)

    def weaken(payload: dict) -> None:
        payload["images"][0]["matches"][0]["similarity"] = 0.05

    rewrite_realruntime(args, weaken)
    report = border_frame_restore_check.build_check(args)
    assert report["passed"] is False, report
    assert any("similarity" in failure for failure in report["failures"]), report


def test_failed_gate_fails(fixture: Path) -> None:
    args = write_fixture(fixture)

    def fail_gate(payload: dict) -> None:
        gate = payload["images"][0]["gate"]
        gate["passed"] = False
        gate["failures"] = [{"reason": "low_similarity"}]

    rewrite_realruntime(args, fail_gate)
    report = border_frame_restore_check.build_check(args)
    assert report["passed"] is False, report
    assert any("gate did not pass" in failure for failure in report["failures"]), report


def test_weak_gate_threshold_fails(fixture: Path) -> None:
    args = write_fixture(fixture)

    def weaken_threshold(payload: dict) -> None:
        for check in payload["images"][0]["gate"]["checks"]:
            if check["kind"] == "match":
                check["minimum_similarity"] = 0.01

    rewrite_realruntime(args, weaken_threshold)
    report = border_frame_restore_check.build_check(args)
    assert report["passed"] is False, report
    assert any("gate similarity minimum" in failure for failure in report["failures"]), report


def test_missing_real_runtime_reference_fails(fixture: Path) -> None:
    args = write_fixture(fixture)
    proxy_frame_payload = json.loads(args.evidence_json.read_text(encoding="utf-8"))

    def point_at_proxy(payload: dict) -> None:
        payload["images"] = copy.deepcopy(proxy_frame_payload["images"])

    rewrite_realruntime(args, point_at_proxy)
    report = border_frame_restore_check.build_check(args)
    assert report["passed"] is False, report
    assert any(
        "does not reference a 'visual-smoke-' run" in failure for failure in report["failures"]
    ), report


def test_missing_source_frame_fails(fixture: Path) -> None:
    args = write_fixture(fixture)

    def orphan_frame(payload: dict) -> None:
        payload["images"][0]["path"] = str(fixture / "visual-smoke-fixture" / "deleted.png")

    rewrite_realruntime(args, orphan_frame)
    report = border_frame_restore_check.build_check(args)
    assert report["passed"] is False, report
    assert any("source frame is missing" in failure for failure in report["failures"]), report


def test_cli_writes_outputs_and_fails_closed(fixture: Path) -> None:
    good_args = write_fixture(fixture / "good")
    out_json = fixture / "good-output" / "border-check.json"
    out_md = fixture / "good-output" / "border-check.md"
    good_run = run_script(
        "--evidence-json",
        str(good_args.evidence_json),
        "--realruntime-json",
        str(good_args.realruntime_json),
        "--repo-root",
        str(good_args.repo_root),
        "--write-json",
        str(out_json),
        "--write-markdown",
        str(out_md),
        "--require-pass",
    )
    assert good_run.returncode == 0, good_run.stdout + good_run.stderr
    assert json.loads(out_json.read_text(encoding="utf-8"))["passed"] is True
    assert "- Overall: PASS" in out_md.read_text(encoding="utf-8")

    bad_args = write_fixture(fixture / "bad")
    bad_json = fixture / "bad-output" / "border-check.json"
    bad_md = fixture / "bad-output" / "border-check.md"
    bad_run = run_script(
        "--evidence-json",
        str(fixture / "bad" / "missing.json"),
        "--realruntime-json",
        str(bad_args.realruntime_json),
        "--repo-root",
        str(bad_args.repo_root),
        "--write-json",
        str(bad_json),
        "--write-markdown",
        str(bad_md),
        "--require-pass",
    )
    assert bad_run.returncode == 2, bad_run.stdout + bad_run.stderr
    assert json.loads(bad_json.read_text(encoding="utf-8"))["passed"] is False
    assert "- Overall: FAIL" in bad_md.read_text(encoding="utf-8")


def run_tests() -> None:
    fixture = ROOT / ".codex-loop" / "tmp-tests" / "border-frame-restore-check-fixture"
    shutil.rmtree(fixture, ignore_errors=True)
    fixture.mkdir(parents=True)
    try:
        test_committed_shape_passes(fixture / "good")
        test_missing_evidence_file_fails(fixture / "missing-file")
        test_missing_band_fails(fixture / "missing-band")
        test_black_extension_band_fails(fixture / "black-band")
        test_low_similarity_fails(fixture / "low-similarity")
        test_failed_gate_fails(fixture / "failed-gate")
        test_weak_gate_threshold_fails(fixture / "weak-threshold")
        test_missing_real_runtime_reference_fails(fixture / "missing-real-runtime")
        test_missing_source_frame_fails(fixture / "missing-frame")
        test_cli_writes_outputs_and_fails_closed(fixture / "cli")
    finally:
        shutil.rmtree(fixture, ignore_errors=True)


def main() -> int:
    run_tests()
    print("border frame restore check tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
