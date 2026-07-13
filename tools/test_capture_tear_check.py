#!/usr/bin/env python3
"""Fixture tests for capture_tear_check.py."""

from __future__ import annotations

import io
import struct
import sys
import tempfile
import zlib
from contextlib import redirect_stderr
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import capture_tear_check  # noqa: E402
from capture_geometry import read_png  # noqa: E402


WIDTH = 320
HEIGHT = 240
BAND_HEIGHT = 8


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


def sawtooth_pixel(x: int) -> tuple[int, int, int]:
    value = (x * 2) % 256
    return (value, (value + 40) % 256, (value + 90) % 256)


def clean_pixel(x: int, y: int) -> tuple[int, int, int]:
    return sawtooth_pixel(x)


def torn_pixel(x: int, y: int) -> tuple[int, int, int]:
    # Horizontal displacement bands: each band shifts the same content in x,
    # mimicking a GDI grab that lands mid page-flip while the screen scrolls.
    band = y // BAND_HEIGHT
    offset = (band * 37) % WIDTH
    return sawtooth_pixel((x + offset) % WIDTH)


def test_clean_frame_not_suspected(tmp_dir: Path) -> None:
    frame = write_png(tmp_dir / "clean.png", WIDTH, HEIGHT, clean_pixel)
    report = capture_tear_check.build_report([frame], None)
    assert report["verdict"] == "clean_heuristic_only", report["verdict"]
    assert report["clean"] is True
    assert report["frames"][0]["tear_suspected"] is False, report["frames"][0]


def test_torn_frame_suspected(tmp_dir: Path) -> None:
    frame = write_png(tmp_dir / "torn.png", WIDTH, HEIGHT, torn_pixel)
    report = capture_tear_check.build_report([frame], None)
    assert report["verdict"] == "tear_suspected", report["frames"][0]
    assert report["clean"] is False
    frame_report = report["frames"][0]
    assert frame_report["mean_ratio"] > frame_report["max_mean_ratio"] or (
        frame_report["row_excess_percent"] > frame_report["max_row_excess_percent"]
    ), frame_report


def test_suspect_stable_pair_remains_suspect(tmp_dir: Path) -> None:
    # Identical pixels do not prove independent captures. A stable hash must
    # never clear either frame's advisory tear suspicion.
    first = write_png(tmp_dir / "suspect-stable-1.png", WIDTH, HEIGHT, torn_pixel)
    second = write_png(tmp_dir / "suspect-stable-2.png", WIDTH, HEIGHT, torn_pixel)
    report = capture_tear_check.build_report([first, second], None)
    assert report["stable_pair_index"] == 0, report
    assert all(frame["tear_suspected"] for frame in report["frames"]), report
    assert report["verdict"] == "tear_suspected", report["verdict"]
    assert report["clean"] is False


def test_clean_stable_pair_is_clean(tmp_dir: Path) -> None:
    first = write_png(tmp_dir / "clean-stable-1.png", WIDTH, HEIGHT, clean_pixel)
    second = write_png(tmp_dir / "clean-stable-2.png", WIDTH, HEIGHT, clean_pixel)
    report = capture_tear_check.build_report([first, second], None)
    assert all(not frame["tear_suspected"] for frame in report["frames"]), report
    assert report["verdict"] == "clean_stable_pair", report["verdict"]
    assert report["clean"] is True
    assert report["stable_pair_index"] == 0


def test_duplicate_torn_path_is_rejected(tmp_dir: Path) -> None:
    frame = write_png(tmp_dir / "duplicate-torn.png", WIDTH, HEIGHT, torn_pixel)
    try:
        capture_tear_check.build_report([frame, frame], None)
    except ValueError as exc:
        assert "duplicate frame" in str(exc), exc
    else:
        raise AssertionError("duplicate frame path was accepted")

    stderr = io.StringIO()
    old_argv = sys.argv
    try:
        sys.argv = ["capture_tear_check.py", str(frame), str(frame)]
        with redirect_stderr(stderr):
            exit_code = capture_tear_check.main()
    finally:
        sys.argv = old_argv
    assert exit_code == 2, (exit_code, stderr.getvalue())
    assert "duplicate frame" in stderr.getvalue(), stderr.getvalue()


def test_animated_pair_picks_least_torn(tmp_dir: Path) -> None:
    torn = write_png(tmp_dir / "animated-torn.png", WIDTH, HEIGHT, torn_pixel)
    clean = write_png(tmp_dir / "animated-clean.png", WIDTH, HEIGHT, clean_pixel)
    report = capture_tear_check.build_report([torn, clean], None)
    assert report["stable_pair_index"] is None
    assert report["verdict"] == "tear_suspected", report["verdict"]
    assert report["least_torn_frame"] == str(clean), report["least_torn_frame"]


def test_rect_pixel_sha256_matches_for_identical_content(tmp_dir: Path) -> None:
    first = read_png(write_png(tmp_dir / "hash-1.png", WIDTH, HEIGHT, clean_pixel))
    second = read_png(write_png(tmp_dir / "hash-2.png", WIDTH, HEIGHT, clean_pixel))
    rect = (0, 0, WIDTH - 1, HEIGHT - 1)
    assert capture_tear_check.rect_pixel_sha256(first, rect) == capture_tear_check.rect_pixel_sha256(
        second, rect
    )


def test_invalid_rect_cli_returns_input_error(tmp_dir: Path) -> None:
    frame = write_png(tmp_dir / "invalid-rect.png", WIDTH, HEIGHT, clean_pixel)
    stderr = io.StringIO()
    old_argv = sys.argv
    try:
        sys.argv = [
            "capture_tear_check.py",
            str(frame),
            "--rect",
            "0",
            "0",
            "0",
            "0",
        ]
        with redirect_stderr(stderr):
            exit_code = capture_tear_check.main()
    finally:
        sys.argv = old_argv
    assert exit_code == 2, (exit_code, stderr.getvalue())
    assert "empty analysis rect" in stderr.getvalue(), stderr.getvalue()


def test_nan_threshold_cli_returns_input_error(tmp_dir: Path) -> None:
    frame = write_png(tmp_dir / "nan-threshold.png", WIDTH, HEIGHT, clean_pixel)
    stderr = io.StringIO()
    old_argv = sys.argv
    try:
        sys.argv = [
            "capture_tear_check.py",
            str(frame),
            "--max-mean-ratio",
            "NaN",
        ]
        with redirect_stderr(stderr):
            exit_code = capture_tear_check.main()
    finally:
        sys.argv = old_argv
    assert exit_code == 2, (exit_code, stderr.getvalue())
    assert "must be finite and nonnegative" in stderr.getvalue(), stderr.getvalue()


def main() -> int:
    tests = [
        test_clean_frame_not_suspected,
        test_torn_frame_suspected,
        test_suspect_stable_pair_remains_suspect,
        test_clean_stable_pair_is_clean,
        test_duplicate_torn_path_is_rejected,
        test_animated_pair_picks_least_torn,
        test_rect_pixel_sha256_matches_for_identical_content,
        test_invalid_rect_cli_returns_input_error,
        test_nan_threshold_cli_returns_input_error,
    ]
    with tempfile.TemporaryDirectory() as raw_tmp:
        tmp_dir = Path(raw_tmp)
        for test in tests:
            test(tmp_dir)
            print(f"PASS {test.__name__}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
