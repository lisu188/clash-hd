#!/usr/bin/env python3
"""Summarize HD top/right map regions in Clash95 PNG captures.

The CDB top-band probe samples individual pixels from the 800x600 map surface.
That is useful, but a sampled black palette value can also be legitimate terrain.
This script measures whole logical tile regions in captured frames so a suspected
blank band can be separated from a dark but rendered tile.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

from capture_geometry import Image, luminance, read_png


DEFAULT_X_STARTS = [608, 672, 736]
DEFAULT_Y_STARTS = [16, 80, 144, 208]


def logical_rect_to_pixels(
    image: Image,
    logical_rect: tuple[int, int, int, int],
    logical_width: int,
    logical_height: int,
) -> tuple[int, int, int, int]:
    """Convert an inclusive logical rect to an inclusive image-pixel rect."""

    left, top, right, bottom = logical_rect
    scale_x = image.width / logical_width
    scale_y = image.height / logical_height
    pixel_left = max(0, min(image.width - 1, math.floor(left * scale_x)))
    pixel_top = max(0, min(image.height - 1, math.floor(top * scale_y)))
    pixel_right = max(0, min(image.width - 1, math.ceil((right + 1) * scale_x) - 1))
    pixel_bottom = max(0, min(image.height - 1, math.ceil((bottom + 1) * scale_y) - 1))
    return pixel_left, pixel_top, pixel_right, pixel_bottom


def region_stats(
    image: Image,
    logical_rect: tuple[int, int, int, int],
    logical_width: int,
    logical_height: int,
    threshold: int,
    black_percent: float,
) -> dict[str, Any]:
    x0, y0, x1, y1 = logical_rect_to_pixels(image, logical_rect, logical_width, logical_height)
    total = 0
    nonblack = 0
    bright = 0
    luma_sum = 0.0
    min_luma = 255.0
    max_luma = 0.0

    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            rgb = image.rgb_at(x, y)
            luma = luminance(rgb)
            total += 1
            luma_sum += luma
            min_luma = min(min_luma, luma)
            max_luma = max(max_luma, luma)
            if max(rgb) > threshold:
                nonblack += 1
            if luma >= 96:
                bright += 1

    center_x = (x0 + x1) // 2
    center_y = (y0 + y1) // 2
    center_rgb = image.rgb_at(center_x, center_y)
    nonblack_percent = round(nonblack * 100.0 / total, 3) if total else 0.0

    return {
        "logical_rect": list(logical_rect),
        "image_rect": {
            "x": x0,
            "y": y0,
            "right": x1,
            "bottom": y1,
            "width": x1 - x0 + 1,
            "height": y1 - y0 + 1,
        },
        "pixels": total,
        "nonblack_percent": nonblack_percent,
        "bright_percent": round(bright * 100.0 / total, 3) if total else 0.0,
        "mean_luma": round(luma_sum / total, 3) if total else 0.0,
        "min_luma": round(min_luma, 3) if total else 0.0,
        "max_luma": round(max_luma, 3) if total else 0.0,
        "center_pixel": {
            "image_x": center_x,
            "image_y": center_y,
            "rgb": list(center_rgb),
            "luma": round(luminance(center_rgb), 3),
        },
        "mostly_black": nonblack_percent < black_percent,
    }


def build_regions(x_starts: list[int], y_starts: list[int], tile_size: int) -> list[tuple[str, tuple[int, int, int, int]]]:
    regions: list[tuple[str, tuple[int, int, int, int]]] = []
    for y in y_starts:
        for x in x_starts:
            regions.append((f"x{x}_y{y}", (x, y, x + tile_size - 1, y + tile_size - 1)))
    if len(x_starts) > 1 and len(y_starts) > 1:
        regions.append(
            (
                "combined",
                (
                    min(x_starts),
                    min(y_starts),
                    max(x_starts) + tile_size - 1,
                    max(y_starts) + tile_size - 1,
                ),
            )
        )
    return regions


def analyze_image(
    path: Path,
    regions: list[tuple[str, tuple[int, int, int, int]]],
    logical_width: int,
    logical_height: int,
    threshold: int,
    black_percent: float,
) -> dict[str, Any]:
    image = read_png(path)
    image_regions = {
        name: region_stats(image, rect, logical_width, logical_height, threshold, black_percent)
        for name, rect in regions
    }
    mostly_black = [name for name, stats in image_regions.items() if stats["mostly_black"]]
    return {
        "path": str(path),
        "image": {"width": image.width, "height": image.height},
        "logical_size": {"width": logical_width, "height": logical_height},
        "scale": {
            "x": round(image.width / logical_width, 6),
            "y": round(image.height / logical_height, 6),
        },
        "regions": image_regions,
        "mostly_black_regions": mostly_black,
    }


def print_summary(report: dict[str, Any]) -> None:
    for image in report["images"]:
        print(f"image: {image['path']} ({image['image']['width']}x{image['image']['height']}, scale={image['scale']['x']}x{image['scale']['y']})")
        for name, stats in image["regions"].items():
            if name == "combined" or name.startswith(("x672_", "x736_")):
                flag = " mostly_black" if stats["mostly_black"] else ""
                print(
                    "  {name}: logical={logical} nonblack={nonblack}% mean_luma={luma} "
                    "center_rgb={rgb}{flag}".format(
                        name=name,
                        logical=stats["logical_rect"],
                        nonblack=stats["nonblack_percent"],
                        luma=stats["mean_luma"],
                        rgb=stats["center_pixel"]["rgb"],
                        flag=flag,
                    )
                )
        if image["mostly_black_regions"]:
            print("  mostly_black_regions: " + ", ".join(image["mostly_black_regions"]))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("png", nargs="+", type=Path, help="PNG capture(s) to inspect")
    parser.add_argument("--logical-width", type=int, default=800)
    parser.add_argument("--logical-height", type=int, default=600)
    parser.add_argument("--tile-size", type=int, default=64)
    parser.add_argument("--x-starts", nargs="+", type=int, default=DEFAULT_X_STARTS)
    parser.add_argument("--y-starts", nargs="+", type=int, default=DEFAULT_Y_STARTS)
    parser.add_argument("--threshold", type=int, default=12, help="max RGB above this counts as nonblack")
    parser.add_argument("--black-percent", type=float, default=5.0, help="regions below this nonblack percent are flagged")
    parser.add_argument("--write-json", type=Path, help="write full JSON report")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    regions = build_regions(args.x_starts, args.y_starts, args.tile_size)
    report = {
        "threshold": args.threshold,
        "black_percent": args.black_percent,
        "regions": [{"name": name, "logical_rect": list(rect)} for name, rect in regions],
        "images": [
            analyze_image(
                path,
                regions,
                args.logical_width,
                args.logical_height,
                args.threshold,
                args.black_percent,
            )
            for path in args.png
        ],
    }
    if args.write_json:
        args.write_json.parent.mkdir(parents=True, exist_ok=True)
        args.write_json.write_text(json.dumps(report, indent=2), encoding="ascii")
    print_summary(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
