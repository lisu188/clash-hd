#!/usr/bin/env python3
"""Check whether a castle/interior UI dump is plausibly centered in 800x600."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from capture_geometry import Image, read_png


def region_stats(
    image: Image,
    rect: tuple[int, int, int, int],
    threshold: int,
) -> dict[str, Any]:
    left, top, right, bottom = rect
    clipped = (
        max(0, left),
        max(0, top),
        min(image.width - 1, right),
        min(image.height - 1, bottom),
    )
    total = 0
    nonblack = 0
    xs: list[int] = []
    ys: list[int] = []
    if clipped[0] > clipped[2] or clipped[1] > clipped[3]:
        return {
            "rect": list(rect),
            "clipped_rect": list(clipped),
            "pixels": 0,
            "nonblack_pixels": 0,
            "nonblack_percent": 0.0,
            "nonblack_bounds": None,
        }
    left, top, right, bottom = clipped
    for y in range(top, bottom + 1):
        for x in range(left, right + 1):
            total += 1
            if max(image.rgb_at(x, y)) > threshold:
                nonblack += 1
                xs.append(x)
                ys.append(y)
    bounds = None
    if xs and ys:
        bounds = {
            "x": min(xs),
            "y": min(ys),
            "right": max(xs),
            "bottom": max(ys),
            "width": max(xs) - min(xs) + 1,
            "height": max(ys) - min(ys) + 1,
        }
    return {
        "rect": list(rect),
        "clipped_rect": list(clipped),
        "pixels": total,
        "nonblack_pixels": nonblack,
        "nonblack_percent": round(nonblack * 100.0 / max(1, total), 3),
        "nonblack_bounds": bounds,
    }


def analyze(path: Path, threshold: int, max_echo_percent: float) -> dict[str, Any]:
    image = read_png(path)
    regions = {
        "full": region_stats(image, (0, 0, image.width - 1, image.height - 1), threshold),
        "centered_640x480": region_stats(image, (80, 60, 719, 539), threshold),
        "native_top_left_640x480": region_stats(image, (0, 0, 639, 479), threshold),
        "top_left_margin_80x60": region_stats(image, (0, 0, 79, 59), threshold),
        "left_margin_80x480": region_stats(image, (0, 60, 79, 539), threshold),
        "top_margin_640x60": region_stats(image, (80, 0, 719, 59), threshold),
    }
    centered = regions["centered_640x480"]["nonblack_percent"]
    top_left = regions["top_left_margin_80x60"]["nonblack_percent"]
    left = regions["left_margin_80x480"]["nonblack_percent"]
    top = regions["top_margin_640x60"]["nonblack_percent"]
    margin_max = max(top_left, left, top)
    gate = {
        "passed": image.width == 800
        and image.height == 600
        and centered >= 10.0
        and centered >= margin_max + 15.0
        and margin_max <= max_echo_percent,
        "checks": {
            "image_size_800x600": [image.width, image.height] == [800, 600],
            "centered_region_has_content": centered >= 10.0,
            "centered_region_dominates_margins": centered >= margin_max + 15.0,
            "native_origin_echo_absent": margin_max <= max_echo_percent,
        },
        "centered_nonblack_percent": centered,
        "max_margin_nonblack_percent": margin_max,
        "max_allowed_echo_percent": max_echo_percent,
    }
    return {
        "path": str(path),
        "image": {"width": image.width, "height": image.height},
        "threshold": threshold,
        "regions": regions,
        "gate": gate,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("png", type=Path)
    parser.add_argument("--threshold", type=int, default=12)
    parser.add_argument("--max-echo-percent", type=float, default=5.0)
    parser.add_argument("--write-json", type=Path)
    parser.add_argument("--require-centered", action="store_true")
    args = parser.parse_args()

    report = analyze(args.png, args.threshold, args.max_echo_percent)
    if args.write_json:
        args.write_json.parent.mkdir(parents=True, exist_ok=True)
        args.write_json.write_text(json.dumps(report, indent=2), encoding="ascii")

    gate = report["gate"]
    print(
        "centered_gate={gate} image={width}x{height} centered_nonblack={centered}% "
        "max_margin_nonblack={margin}%".format(
            gate="PASS" if gate["passed"] else "FAIL",
            width=report["image"]["width"],
            height=report["image"]["height"],
            centered=gate["centered_nonblack_percent"],
            margin=gate["max_margin_nonblack_percent"],
        )
    )
    for name, value in gate["checks"].items():
        print(f"- {name}: {value}")

    if args.require_centered and not gate["passed"]:
        print("required centered castle UI gate failed", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
