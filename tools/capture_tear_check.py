#!/usr/bin/env python3
"""Check captured Clash95 frames for GDI capture tearing.

Live visible-runtime grabs (`scripts/capture/capture_clash_client_frame.ps1`)
read the desktop front buffer with `Graphics.CopyFromScreen` and can land mid
page-flip on animated dgVoodoo-wrapped screens. The result is horizontal
displacement bands ("tearing") that look like a render defect but are a
capture artifact: the hidden CDB surfdump of the same screen is coherent.
Calibration (castle overview, 2026-07-13): torn GDI grab row-to-row mean diff
18.4 vs 7.5 on the clean surface dump of the same screen. These thresholds are
content- and ROI-sensitive; a different screen or analysis rectangle needs its
own clean/torn calibration.

Two modes:

- Multi-frame (corroborating): pass 2+ distinct back-to-back grabs of the same
  screen. A consecutive pixel-identical pair strengthens an already
  non-suspect heuristic result, but does not prove capture independence and
  never clears a frame that the heuristic marks suspect.
- Single-frame (heuristic, advisory): tearing adds row-to-row energy without
  adding column-to-column energy, so the row/column mean-diff ratio and the
  excess of high-diff rows over high-diff columns flag suspect frames.
  Legitimate horizontal UI boundaries can produce the same signature. Treat a
  suspect result as a request for another capture or a calibrated ROI, not as
  proof of a game render defect.
  Beware: `tools/castle_overview_gate.py` gates only VERTICAL stripe metrics
  and will PASS a horizontally torn frame — it is meant for coherent proxy
  dumps, not desktop grabs.

Exit code 0 = no tear suspected by the advisory heuristic, 1 = tear suspected,
2 = usage/input error. Exit 0 is not proof that a capture is tear-free.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
from pathlib import Path
from typing import Any

from capture_geometry import Image, read_png


DEFAULT_DIFF_THRESHOLD = 40.0
DEFAULT_MAX_ROW_EXCESS_PERCENT = 6.0
DEFAULT_MAX_MEAN_RATIO = 1.8
DEFAULT_MIN_ROW_MEAN = 1.0


def validate_thresholds(
    *,
    diff_threshold: float,
    max_row_excess_percent: float,
    max_mean_ratio: float,
    min_row_mean: float,
) -> None:
    values = {
        "diff_threshold": diff_threshold,
        "max_row_excess_percent": max_row_excess_percent,
        "max_mean_ratio": max_mean_ratio,
        "min_row_mean": min_row_mean,
    }
    for name, value in values.items():
        if not math.isfinite(value) or value < 0:
            raise ValueError(f"{name} must be finite and nonnegative, got {value!r}")


def validate_frame_paths(frame_paths: list[Path]) -> list[Path]:
    if not frame_paths:
        raise ValueError("at least one frame is required")

    validated: list[Path] = []
    canonical_paths: dict[str, Path] = {}
    for path in frame_paths:
        if not path.exists():
            raise ValueError(f"missing frame: {path}")
        if not path.is_file():
            raise ValueError(f"frame is not a file: {path}")

        resolved = path.resolve(strict=True)
        canonical = os.path.normcase(str(resolved))
        duplicate = canonical_paths.get(canonical)
        if duplicate is not None:
            raise ValueError(f"duplicate frame path: {path} resolves to {duplicate}")

        # Resolve aliases that name the same file (for example, hard links).
        for prior in validated:
            if path.samefile(prior):
                raise ValueError(f"duplicate frame file: {path} is the same file as {prior}")

        canonical_paths[canonical] = path
        validated.append(path)
    return validated


def clamp_rect(image: Image, rect: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    left, top, right, bottom = rect
    left = max(0, left)
    top = max(0, top)
    right = min(image.width - 1, right)
    bottom = min(image.height - 1, bottom)
    if right <= left or bottom <= top:
        raise ValueError(f"empty analysis rect {rect} for {image.width}x{image.height} frame")
    return left, top, right, bottom


def rect_pixel_sha256(image: Image, rect: tuple[int, int, int, int]) -> str:
    left, top, right, bottom = clamp_rect(image, rect)
    digest = hashlib.sha256()
    for y in range(top, bottom + 1):
        row = y * image.width
        digest.update(bytes(value for x in range(left, right + 1) for value in image.pixels[row + x]))
    return digest.hexdigest()


def analyze_frame(
    image: Image,
    rect: tuple[int, int, int, int],
    *,
    diff_threshold: float = DEFAULT_DIFF_THRESHOLD,
    max_row_excess_percent: float = DEFAULT_MAX_ROW_EXCESS_PERCENT,
    max_mean_ratio: float = DEFAULT_MAX_MEAN_RATIO,
    min_row_mean: float = DEFAULT_MIN_ROW_MEAN,
) -> dict[str, Any]:
    validate_thresholds(
        diff_threshold=diff_threshold,
        max_row_excess_percent=max_row_excess_percent,
        max_mean_ratio=max_mean_ratio,
        min_row_mean=min_row_mean,
    )
    left, top, right, bottom = clamp_rect(image, rect)

    def average_diff(a: tuple[int, int, int], b: tuple[int, int, int]) -> float:
        return sum(abs(int(a[index]) - int(b[index])) for index in range(3)) / 3.0

    row_diffs: list[float] = []
    for y in range(top, bottom):
        total = 0.0
        for x in range(left, right + 1):
            total += average_diff(image.rgb_at(x, y), image.rgb_at(x, y + 1))
        row_diffs.append(total / max(1, right - left + 1))

    column_diffs: list[float] = []
    for x in range(left, right):
        total = 0.0
        for y in range(top, bottom + 1):
            total += average_diff(image.rgb_at(x, y), image.rgb_at(x + 1, y))
        column_diffs.append(total / max(1, bottom - top + 1))

    row_high = sum(1 for value in row_diffs if value >= diff_threshold)
    column_high = sum(1 for value in column_diffs if value >= diff_threshold)
    row_high_percent = round(row_high * 100.0 / max(1, len(row_diffs)), 3)
    column_high_percent = round(column_high * 100.0 / max(1, len(column_diffs)), 3)
    row_mean = sum(row_diffs) / max(1, len(row_diffs))
    column_mean = sum(column_diffs) / max(1, len(column_diffs))
    row_excess_percent = round(max(0.0, row_high_percent - column_high_percent), 3)
    mean_ratio = round(row_mean / max(0.001, column_mean), 3)

    tear_suspected = row_excess_percent > max_row_excess_percent or (
        mean_ratio > max_mean_ratio and row_mean >= min_row_mean
    )
    return {
        "heuristic_advisory": True,
        "heuristic_scope": "content_and_roi_calibrated",
        "rect": [left, top, right, bottom],
        "diff_threshold": diff_threshold,
        "row_mean_diff": round(row_mean, 3),
        "column_mean_diff": round(column_mean, 3),
        "row_high_percent": row_high_percent,
        "column_high_percent": column_high_percent,
        "row_excess_percent": row_excess_percent,
        "mean_ratio": mean_ratio,
        "max_row_excess_percent": max_row_excess_percent,
        "max_mean_ratio": max_mean_ratio,
        "min_row_mean": min_row_mean,
        "tear_suspected": tear_suspected,
    }


def build_report(
    frame_paths: list[Path],
    rect: tuple[int, int, int, int] | None,
    *,
    diff_threshold: float = DEFAULT_DIFF_THRESHOLD,
    max_row_excess_percent: float = DEFAULT_MAX_ROW_EXCESS_PERCENT,
    max_mean_ratio: float = DEFAULT_MAX_MEAN_RATIO,
    min_row_mean: float = DEFAULT_MIN_ROW_MEAN,
) -> dict[str, Any]:
    validate_thresholds(
        diff_threshold=diff_threshold,
        max_row_excess_percent=max_row_excess_percent,
        max_mean_ratio=max_mean_ratio,
        min_row_mean=min_row_mean,
    )
    frame_paths = validate_frame_paths(frame_paths)
    images = [read_png(path) for path in frame_paths]
    frames: list[dict[str, Any]] = []
    for path, image in zip(frame_paths, images):
        frame_rect = rect if rect is not None else (0, 0, image.width - 1, image.height - 1)
        analysis = analyze_frame(
            image,
            frame_rect,
            diff_threshold=diff_threshold,
            max_row_excess_percent=max_row_excess_percent,
            max_mean_ratio=max_mean_ratio,
            min_row_mean=min_row_mean,
        )
        analysis["frame"] = str(path)
        analysis["width"] = image.width
        analysis["height"] = image.height
        analysis["pixel_sha256"] = rect_pixel_sha256(image, frame_rect)
        frames.append(analysis)

    stable_pair_index = None
    for index in range(len(frames) - 1):
        current = frames[index]
        following = frames[index + 1]
        if (
            current["pixel_sha256"] == following["pixel_sha256"]
            and current["rect"] == following["rect"]
            and current["width"] == following["width"]
            and current["height"] == following["height"]
        ):
            stable_pair_index = index
            break

    any_suspect = any(frame["tear_suspected"] for frame in frames)
    if any_suspect:
        # Stable/identical content never overrides a suspect frame: file hashes
        # cannot prove that captures were independent or tear-free.
        verdict = "tear_suspected"
    elif stable_pair_index is not None:
        verdict = "clean_stable_pair"
    else:
        verdict = "clean_heuristic_only" if len(frames) == 1 else "animated_no_tear_suspected"

    least_torn_index = min(range(len(frames)), key=lambda index: frames[index]["row_mean_diff"])
    return {
        "frames": frames,
        "frame_count": len(frames),
        "stable_pair_index": stable_pair_index,
        "least_torn_index": least_torn_index,
        "least_torn_frame": frames[least_torn_index]["frame"],
        "verdict": verdict,
        "clean": verdict != "tear_suspected",
        "heuristic_advisory": True,
        "heuristic_scope": "content_and_roi_calibrated",
        "note": (
            "All tear verdicts are advisory, content- and ROI-calibrated heuristics. An "
            "identical pair only corroborates frames that are individually non-suspect; it "
            "does not prove capture independence and never clears a suspect frame. Tearing "
            "is a GDI CopyFromScreen capture artifact, not a game render defect — confirm "
            "geometry with a hidden CDB surface dump."
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Detect GDI capture tearing in Clash95 frame grabs.")
    parser.add_argument("frames", nargs="+", type=Path, help="one or more PNG frames, in capture order")
    parser.add_argument(
        "--rect",
        nargs=4,
        type=int,
        metavar=("LEFT", "TOP", "RIGHT", "BOTTOM"),
        help="analysis rect in frame pixels (default: full frame)",
    )
    parser.add_argument("--diff-threshold", type=float, default=DEFAULT_DIFF_THRESHOLD)
    parser.add_argument("--max-row-excess-percent", type=float, default=DEFAULT_MAX_ROW_EXCESS_PERCENT)
    parser.add_argument("--max-mean-ratio", type=float, default=DEFAULT_MAX_MEAN_RATIO)
    parser.add_argument("--min-row-mean", type=float, default=DEFAULT_MIN_ROW_MEAN)
    parser.add_argument("--out-json", type=Path, help="write the full report as JSON")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        report = build_report(
            list(args.frames),
            tuple(args.rect) if args.rect else None,
            diff_threshold=args.diff_threshold,
            max_row_excess_percent=args.max_row_excess_percent,
            max_mean_ratio=args.max_mean_ratio,
            min_row_mean=args.min_row_mean,
        )
    except (OSError, ValueError) as exc:
        print(f"input error: {exc}", file=sys.stderr)
        return 2
    if args.out_json:
        try:
            args.out_json.parent.mkdir(parents=True, exist_ok=True)
            args.out_json.write_text(json.dumps(report, indent=2), encoding="ascii")
        except OSError as exc:
            print(f"output error: {exc}", file=sys.stderr)
            return 2
    for frame in report["frames"]:
        print(
            "- {frame}: row_mean={row_mean} col_mean={col_mean} ratio={ratio} "
            "row_excess={excess}% tear_suspected={suspected}".format(
                frame=frame["frame"],
                row_mean=frame["row_mean_diff"],
                col_mean=frame["column_mean_diff"],
                ratio=frame["mean_ratio"],
                excess=frame["row_excess_percent"],
                suspected=frame["tear_suspected"],
            )
        )
    print(
        f"advisory verdict: {report['verdict']} "
        f"(least torn: {report['least_torn_frame']})"
    )
    return 0 if report["clean"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
