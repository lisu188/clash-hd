#!/usr/bin/env python3
"""Fixture tests for first_mission_visual_audit.py."""

from __future__ import annotations

import json
import shutil
import struct
import subprocess
import sys
import zlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "first_mission_visual_audit.py"
sys.path.insert(0, str(ROOT / "tools"))

import first_mission_visual_audit  # noqa: E402


def write_png(path: Path, width: int, height: int, pixel_at) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = bytearray()
    for y in range(height):
        rows.append(0)
        for x in range(width):
            rows.extend(pixel_at(x, y))
    compressed = zlib.compress(bytes(rows))

    def chunk(kind: bytes, payload: bytes) -> bytes:
        crc = zlib.crc32(kind + payload) & 0xFFFFFFFF
        return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", crc)

    data = bytearray(b"\x89PNG\r\n\x1a\n")
    data.extend(chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)))
    data.extend(chunk(b"IDAT", compressed))
    data.extend(chunk(b"IEND", b""))
    path.write_bytes(bytes(data))
    return path


def clean_pixel(x: int, y: int) -> tuple[int, int, int]:
    if 32 <= x <= 585 and 16 <= y <= 527:
        return (90 + (x % 48), 120 + (y % 64), 35 + ((x + y) % 80))
    if 586 <= x <= 799 and 230 <= y <= 599:
        return (80, 70, 45)
    if 594 <= x <= 793 and 24 <= y <= 220:
        return (30, 100, 60)
    if 32 <= x <= 585 and 528 <= y <= 599:
        return (70, 60, 50)
    return (25, 25, 25)


def striped_pixel(x: int, y: int) -> tuple[int, int, int]:
    if 32 <= x <= 585 and 16 <= y <= 527:
        return (230, 230, 230) if y % 2 == 0 else (5, 5, 5)
    return clean_pixel(x, y)


def black_patch_pixel(x: int, y: int) -> tuple[int, int, int]:
    if 586 <= x <= 799 and 230 <= y <= 599:
        return (0, 0, 0)
    return clean_pixel(x, y)


def scaled_black_patch_pixel(x: int, y: int) -> tuple[int, int, int]:
    native_x = int(x * 800 / 1200)
    native_y = int(y * 600 / 900)
    return black_patch_pixel(native_x, native_y)


def legacy_middle_bar_pixel(x: int, y: int) -> tuple[int, int, int]:
    if 150 <= x <= 520 and 455 <= y <= 500:
        return (45, 40, 30)
    if 215 <= x <= 585 and 580 <= y <= 599:
        return (0, 0, 0)
    return clean_pixel(x, y)


def ns(**kwargs):
    defaults = {
        "threshold": 12,
        "bright_threshold": 96.0,
        "diff_threshold": 40.0,
        "max_stripe_high_percent": 12.0,
        "max_stripe_excess_percent": 8.0,
    }
    defaults.update(kwargs)
    return type("Args", (), defaults)()


def frame(path: Path, item_id: str = "primary", primary: bool = True) -> dict:
    return {
        "id": item_id,
        "role": item_id,
        "path": str(path),
        "primary": primary,
    }


def run_script(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def test_clean_frame_passes(fixture: Path) -> None:
    png = write_png(fixture / "clean.png", 800, 600, clean_pixel)
    report = first_mission_visual_audit.build_report([frame(png)], ns())
    assert report["passed"] is True, report
    assert report["first_mission_visual_clean"] is True, report
    assert report["frames"][0]["stripe_metrics"]["passed"] is True, report


def test_horizontal_stripes_fail(fixture: Path) -> None:
    png = write_png(fixture / "striped.png", 800, 600, striped_pixel)
    report = first_mission_visual_audit.build_report([frame(png)], ns())
    assert report["passed"] is False, report
    metrics = report["frames"][0]["stripe_metrics"]
    assert metrics["horizontal_stripe_detected"] is True, metrics
    assert "primary first-mission frame is not visually clean" in report["failures"][0]


def test_black_patch_regions_fail_playability(fixture: Path) -> None:
    png = write_png(fixture / "black-patch.png", 800, 600, black_patch_pixel)
    report = first_mission_visual_audit.build_report([frame(png)], ns())
    assert report["passed"] is False, report
    assert "right_below_minimap" in report["summary"]["primary_black_patch_regions"], report
    details = report["summary"]["primary_black_patch_details"]
    assert set(details[0]) == {
        "region",
        "rect",
        "black_percent",
        "nonblack_percent",
        "mean_luma",
        "quantized_color_bins",
    }, details
    assert details[0]["region"] == "right_below_minimap", details
    assert details[0]["rect"] == [586, 230, 799, 599], details
    assert details[0]["black_percent"] >= 70.0, details
    assert details[0]["nonblack_percent"] <= 30.0, details
    assert details[0]["mean_luma"] >= 0.0, details
    assert details[0]["quantized_color_bins"] > 0, details
    assert report["primary_frame_path"] == str(png), report
    assert report["summary"]["primary_frame_path"] == str(png), report
    assert "compose or present path" in report["next_probe"], report
    assert "compose or present path" in report["summary"]["next_probe"], report


def test_black_patch_excused_when_real_frame_corroborates(fixture: Path) -> None:
    # Proxy primary frame has a black right_below_minimap patch...
    proxy = write_png(fixture / "proxy.png", 800, 600, black_patch_pixel)
    # ...but a real visible-runtime frame renders that region fully (clean).
    real = write_png(fixture / "real.png", 1200, 900, clean_pixel)
    report = first_mission_visual_audit.build_report(
        [frame(proxy)], ns(real_runtime_frame=real)
    )
    assert report["passed"] is True, report
    assert report["proxy_artifact_confirmed_regions"], report
    assert "right_below_minimap" in report["proxy_artifact_confirmed_regions"], report
    assert report["summary"]["primary_black_patch_regions"] == [], report
    assert report["current_status"].endswith("black_patches_are_proxy_artifacts"), report


def test_black_patch_not_excused_when_real_frame_also_black(fixture: Path) -> None:
    proxy = write_png(fixture / "proxy2.png", 800, 600, black_patch_pixel)
    # The 1200x900 real frame is ALSO black in the correctly scaled region.
    real = write_png(fixture / "real2.png", 1200, 900, scaled_black_patch_pixel)
    report = first_mission_visual_audit.build_report(
        [frame(proxy)], ns(real_runtime_frame=real)
    )
    assert report["passed"] is False, report
    assert "right_below_minimap" in report["summary"]["primary_black_patch_regions"], report
    corroboration = report["real_runtime_corroboration"]["regions"]["right_below_minimap"]
    assert corroboration["corroborated_rendered"] is False, corroboration


def test_legacy_middle_action_bar_fails_bottom_gate(fixture: Path) -> None:
    png = write_png(fixture / "legacy-middle.png", 800, 600, legacy_middle_bar_pixel)
    report = first_mission_visual_audit.build_report([frame(png)], ns())
    assert report["passed"] is False, report
    assert report["current_status"] == "legacy_middle_action_bar_detected", report
    first = report["frames"][0]
    assert first["legacy_middle_action_bar_visible"] is True, first
    assert first["selected_action_bar_visible"] is False, first
    assert any("legacy middle placement" in failure for failure in first["failures"]), report


def test_diagnostic_black_frame_is_reported(fixture: Path) -> None:
    png = write_png(fixture / "black.png", 800, 600, lambda _x, _y: (0, 0, 0))
    report = first_mission_visual_audit.build_report([frame(png, "diagnostic")], ns())
    assert report["passed"] is False, report
    assert report["summary"]["diagnostic_black_frames"] == ["diagnostic"], report


def test_cli_writes_outputs(fixture: Path) -> None:
    png = write_png(fixture / "clean.png", 800, 600, clean_pixel)
    out_json = fixture / "out" / "audit.json"
    out_md = fixture / "out" / "audit.md"
    run = run_script(
        "--frame",
        f"primary:true:test clean frame:{png}",
        "--write-json",
        str(out_json),
        "--write-markdown",
        str(out_md),
        "--require-pass",
    )
    assert run.returncode == 0, run.stdout + run.stderr
    payload = json.loads(out_json.read_text(encoding="utf-8"))
    assert payload["passed"] is True, payload
    markdown = out_md.read_text(encoding="utf-8")
    assert "First Mission Visual Audit" in markdown
    assert "Next probe:" in markdown


def run_tests() -> None:
    fixture = ROOT / ".codex-loop" / "tmp-tests" / "first-mission-visual-audit-fixture"
    shutil.rmtree(fixture, ignore_errors=True)
    fixture.mkdir(parents=True)
    try:
        test_clean_frame_passes(fixture / "clean")
        test_horizontal_stripes_fail(fixture / "striped")
        test_black_patch_regions_fail_playability(fixture / "black-patch")
        test_black_patch_excused_when_real_frame_corroborates(fixture / "corroborated")
        test_black_patch_not_excused_when_real_frame_also_black(fixture / "still-black")
        test_legacy_middle_action_bar_fails_bottom_gate(fixture / "legacy-middle")
        test_diagnostic_black_frame_is_reported(fixture / "diagnostic")
        test_cli_writes_outputs(fixture / "cli")
    finally:
        shutil.rmtree(fixture, ignore_errors=True)


def main() -> int:
    run_tests()
    print("first mission visual audit tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
