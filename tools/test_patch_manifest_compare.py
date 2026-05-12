#!/usr/bin/env python3
"""Regression tests for patch_manifest_compare.py."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "patch_manifest_compare.py"
sys.path.insert(0, str(ROOT / "tools"))

import patch_manifest_compare  # noqa: E402


BASE_PATCHES = [
    {
        "group": "display",
        "offset": 0x10,
        "offset_hex": "0x000010",
        "rva_hex": "0x00401010",
        "va_hex": "0x00401010",
        "old": "E0 01",
        "new": "58 02",
        "actual": "58 02",
        "status": "patched",
        "note": "height 480 -> 600",
    },
    {
        "group": "helpers",
        "offset": 0x20,
        "offset_hex": "0x000020",
        "rva_hex": "0x00401020",
        "va_hex": "0x00401020",
        "old": "06",
        "new": "09",
        "actual": "09",
        "status": "patched",
        "note": "bottom row 6 -> 9",
    },
]


def manifest(name: str, patches: list[dict]) -> dict:
    counts: dict[str, int] = {}
    groups: dict[str, dict[str, int]] = {}
    for patch in patches:
        status = patch["status"]
        group = patch["group"]
        counts[status] = counts.get(status, 0) + 1
        groups.setdefault(group, {"total": 0})
        groups[group]["total"] += 1
        groups[group][status] = groups[group].get(status, 0) + 1
    return {
        "exe": name,
        "stage": "test-stage",
        "exe_sha256": name.upper(),
        "expected_base_sha256": "BASE",
        "image_base_hex": "0x00400000",
        "patch_count": len(patches),
        "status_counts": counts,
        "groups": groups,
        "current_hd_map_gate": {"passed": all(p["status"] == "patched" for p in patches)},
        "patches": patches,
    }


def run_compare(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def main() -> int:
    fixture = ROOT / ".codex-loop" / "tmp-tests" / "patch-manifest-compare-fixture"
    shutil.rmtree(fixture, ignore_errors=True)
    fixture.mkdir(parents=True)
    try:
        left_path = fixture / "left.json"
        same_path = fixture / "same.json"
        right_path = fixture / "right.json"
        out_json = fixture / "compare.json"
        out_md = fixture / "compare.md"

        left = manifest("left.exe", BASE_PATCHES)
        same = manifest("left.exe", BASE_PATCHES)
        right_patches = [
            BASE_PATCHES[0],
            {
                **BASE_PATCHES[1],
                "new": "0C",
                "actual": "06",
                "status": "original",
                "note": "bottom row 6 -> 12",
            },
            {
                "group": "new-group",
                "offset": 0x30,
                "offset_hex": "0x000030",
                "rva_hex": "0x00401030",
                "va_hex": "0x00401030",
                "old": "00",
                "new": "90",
                "actual": "90",
                "status": "patched",
                "note": "new test patch",
            },
        ]
        right = manifest("right.exe", right_patches)
        left_path.write_text(json.dumps(left), encoding="utf-8")
        same_path.write_text(json.dumps(same), encoding="utf-8")
        right_path.write_text(json.dumps(right), encoding="utf-8")

        same_cmp = patch_manifest_compare.build_comparison(left_path, same_path)
        assert same_cmp["counts"]["record_diff_count"] == 0, same_cmp
        assert same_cmp["counts"]["left_nonpatched"] == 0, same_cmp
        assert same_cmp["counts"]["right_nonpatched"] == 0, same_cmp

        changed_cmp = patch_manifest_compare.build_comparison(left_path, right_path)
        assert changed_cmp["counts"]["changed_records"] == 1, changed_cmp
        assert changed_cmp["counts"]["added_records"] == 1, changed_cmp
        assert changed_cmp["counts"]["right_nonpatched"] == 1, changed_cmp

        same_run = run_compare(str(left_path), str(same_path), "--fail-on-diff", "--fail-on-bad-status")
        assert same_run.returncode == 0, same_run.stdout + same_run.stderr

        diff_run = run_compare(str(left_path), str(right_path), "--fail-on-diff")
        assert diff_run.returncode == 2, diff_run.stdout + diff_run.stderr

        bad_run = run_compare(str(left_path), str(right_path), "--fail-on-bad-status")
        assert bad_run.returncode == 2, bad_run.stdout + bad_run.stderr

        write_run = run_compare(
            str(left_path),
            str(right_path),
            "--write-json",
            str(out_json),
            "--write-markdown",
            str(out_md),
        )
        assert write_run.returncode == 0, write_run.stdout + write_run.stderr
        assert out_json.is_file(), out_json
        assert out_md.is_file(), out_md
        written = json.loads(out_json.read_text(encoding="utf-8"))
        assert written["counts"]["changed_records"] == 1, written
    finally:
        shutil.rmtree(fixture, ignore_errors=True)
    print("patch_manifest_compare tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
