#!/usr/bin/env python3
"""Inspect right-side and bottom-right Clash95 gameplay UI bounds in PNG captures.

This is a repo-side validation helper for HD map/UI work. It reads existing
screenshots or reconstructed surface PNGs, maps known logical 800x600 UI
regions to the actual image size, and reports coverage plus black-component
bounds. It does not launch the game and does not read or write proprietary
binaries.
"""

from __future__ import annotations

import argparse
import json
import math
from collections import deque
from pathlib import Path
from typing import Any

from capture_geometry import Image, luminance, read_png


DEFAULT_REGIONS: dict[str, tuple[int, int, int, int]] = {
    "minimap_top_right": (586, 16, 799, 229),
    "right_side_total": (586, 16, 799, 599),
    "right_side_below_minimap": (586, 230, 799, 599),
    "bottom_strip": (0, 528, 799, 599),
    "bottom_right_ui_corner": (586, 528, 799, 599),
    "bottom_right_tile_r8c9": (608, 528, 671, 591),
    "bottom_right_tile_r8c10": (672, 528, 735, 591),
    "bottom_right_tile_r8c11": (736, 528, 799, 591),
}


def parse_region(value: str) -> tuple[str, tuple[int, int, int, int]]:
    if ":" not in value:
        raise argparse.ArgumentTypeError("region must be name:left,top,right,bottom")
    name, rect_text = value.split(":", 1)
    parts = [part.strip() for part in rect_text.split(",")]
    if len(parts) != 4:
        raise argparse.ArgumentTypeError("region must be name:left,top,right,bottom")
    try:
        left, top, right, bottom = [int(part, 0) for part in parts]
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid region coordinate: {value}") from exc
    if not name:
        raise argparse.ArgumentTypeError("region name cannot be empty")
    if right < left or bottom < top:
        raise argparse.ArgumentTypeError(f"invalid region rectangle: {value}")
    return name, (left, top, right, bottom)


def parse_region_threshold(value: str) -> tuple[str, float]:
    if ":" not in value:
        raise argparse.ArgumentTypeError("threshold must be region:min_nonblack_percent")
    name, percent_text = value.split(":", 1)
    try:
        percent = float(percent_text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid threshold percent: {value}") from exc
    if percent < 0 or percent > 100:
        raise argparse.ArgumentTypeError(f"threshold percent out of range: {value}")
    return name, percent


def logical_rect_to_pixels(
    image: Image,
    logical_rect: tuple[int, int, int, int],
    logical_width: int,
    logical_height: int,
) -> tuple[int, int, int, int]:
    left, top, right, bottom = logical_rect
    scale_x = image.width / logical_width
    scale_y = image.height / logical_height
    pixel_left = max(0, min(image.width - 1, math.floor(left * scale_x)))
    pixel_top = max(0, min(image.height - 1, math.floor(top * scale_y)))
    pixel_right = max(0, min(image.width - 1, math.ceil((right + 1) * scale_x) - 1))
    pixel_bottom = max(0, min(image.height - 1, math.ceil((bottom + 1) * scale_y) - 1))
    return pixel_left, pixel_top, pixel_right, pixel_bottom


def pixel_bounds_to_logical(
    bounds: dict[str, int] | None,
    image: Image,
    logical_width: int,
    logical_height: int,
) -> dict[str, float] | None:
    if not bounds:
        return None
    scale_x = logical_width / image.width
    scale_y = logical_height / image.height
    left = bounds["x"] * scale_x
    top = bounds["y"] * scale_y
    right = (bounds["right"] + 1) * scale_x - 1
    bottom = (bounds["bottom"] + 1) * scale_y - 1
    return {
        "x": round(left, 2),
        "y": round(top, 2),
        "right": round(right, 2),
        "bottom": round(bottom, 2),
        "width": round(right - left + 1, 2),
        "height": round(bottom - top + 1, 2),
    }


def bounds_from_points(points: list[tuple[int, int]]) -> dict[str, int] | None:
    if not points:
        return None
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    return {
        "x": min(xs),
        "y": min(ys),
        "right": max(xs),
        "bottom": max(ys),
        "width": max(xs) - min(xs) + 1,
        "height": max(ys) - min(ys) + 1,
        "pixels": len(points),
    }


def largest_black_components(
    image: Image,
    pixel_rect: tuple[int, int, int, int],
    threshold: int,
    min_area: int,
    max_components: int,
) -> list[dict[str, int]]:
    x0, y0, x1, y1 = pixel_rect
    width = x1 - x0 + 1
    height = y1 - y0 + 1
    visited = bytearray(width * height)
    components: list[dict[str, int]] = []

    def local_index(x: int, y: int) -> int:
        return (y - y0) * width + (x - x0)

    def is_black(x: int, y: int) -> bool:
        return max(image.rgb_at(x, y)) <= threshold

    for start_y in range(y0, y1 + 1):
        for start_x in range(x0, x1 + 1):
            start_index = local_index(start_x, start_y)
            if visited[start_index] or not is_black(start_x, start_y):
                visited[start_index] = 1
                continue

            queue: deque[tuple[int, int]] = deque([(start_x, start_y)])
            visited[start_index] = 1
            pixels: list[tuple[int, int]] = []
            while queue:
                x, y = queue.popleft()
                pixels.append((x, y))
                for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                    if nx < x0 or nx > x1 or ny < y0 or ny > y1:
                        continue
                    index = local_index(nx, ny)
                    if visited[index]:
                        continue
                    visited[index] = 1
                    if is_black(nx, ny):
                        queue.append((nx, ny))

            bounds = bounds_from_points(pixels)
            if bounds and bounds["pixels"] >= min_area:
                components.append(bounds)

    components.sort(key=lambda item: item["pixels"], reverse=True)
    return components[:max_components]


def analyze_region(
    image: Image,
    name: str,
    logical_rect: tuple[int, int, int, int],
    args: argparse.Namespace,
) -> dict[str, Any]:
    pixel_rect = logical_rect_to_pixels(image, logical_rect, args.logical_width, args.logical_height)
    x0, y0, x1, y1 = pixel_rect
    total = 0
    black = 0
    nonblack = 0
    bright = 0
    luma_sum = 0.0
    black_points: list[tuple[int, int]] = []
    nonblack_points: list[tuple[int, int]] = []

    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            rgb = image.rgb_at(x, y)
            luma = luminance(rgb)
            total += 1
            luma_sum += luma
            if max(rgb) <= args.threshold:
                black += 1
                black_points.append((x, y))
            else:
                nonblack += 1
                nonblack_points.append((x, y))
            if luma >= args.bright_threshold:
                bright += 1

    black_bounds = bounds_from_points(black_points)
    nonblack_bounds = bounds_from_points(nonblack_points)
    components = largest_black_components(
        image,
        pixel_rect,
        args.threshold,
        args.black_component_min_area,
        args.max_black_components,
    )
    region_pixels = max(1, total)
    largest_component = components[0] if components else None
    largest_component_percent = (
        round(largest_component["pixels"] * 100.0 / region_pixels, 3) if largest_component else 0.0
    )

    flags: list[str] = []
    nonblack_percent = round(nonblack * 100.0 / region_pixels, 3)
    black_percent = round(black * 100.0 / region_pixels, 3)
    if nonblack_percent < args.mostly_black_percent:
        flags.append("mostly_black")
    if largest_component_percent >= args.large_component_percent:
        flags.append("large_black_component")
    if black_bounds and black_bounds["right"] == x1 and black_bounds["bottom"] == y1:
        flags.append("black_touches_bottom_right")

    return {
        "name": name,
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
        "black_percent": black_percent,
        "nonblack_percent": nonblack_percent,
        "bright_percent": round(bright * 100.0 / region_pixels, 3),
        "mean_luma": round(luma_sum / region_pixels, 3),
        "black_bounds_image": black_bounds,
        "black_bounds_logical": pixel_bounds_to_logical(
            black_bounds, image, args.logical_width, args.logical_height
        ),
        "nonblack_bounds_image": nonblack_bounds,
        "nonblack_bounds_logical": pixel_bounds_to_logical(
            nonblack_bounds, image, args.logical_width, args.logical_height
        ),
        "largest_black_component_percent": largest_component_percent,
        "largest_black_components": components,
        "largest_black_components_logical": [
            pixel_bounds_to_logical(component, image, args.logical_width, args.logical_height)
            for component in components
        ],
        "flags": flags,
    }


def gate_image(image_report: dict[str, Any], thresholds: list[tuple[str, float]]) -> dict[str, Any]:
    regions = {region["name"]: region for region in image_report["regions"]}
    failures = []
    checks = []
    for name, minimum in thresholds:
        region = regions.get(name)
        if not region:
            failures.append({"region": name, "reason": "missing_region", "minimum_nonblack_percent": minimum})
            continue
        actual = float(region["nonblack_percent"])
        check = {
            "region": name,
            "minimum_nonblack_percent": minimum,
            "actual_nonblack_percent": actual,
            "passed": actual >= minimum,
        }
        checks.append(check)
        if not check["passed"]:
            failures.append({**check, "reason": "low_nonblack_percent"})
    return {"passed": not failures, "checks": checks, "failures": failures}


def analyze_image(path: Path, regions: list[tuple[str, tuple[int, int, int, int]]], args: argparse.Namespace) -> dict[str, Any]:
    image = read_png(path)
    report = {
        "path": str(path),
        "image": {"width": image.width, "height": image.height},
        "logical_size": {"width": args.logical_width, "height": args.logical_height},
        "scale": {
            "x": round(image.width / args.logical_width, 6),
            "y": round(image.height / args.logical_height, 6),
        },
        "regions": [analyze_region(image, name, rect, args) for name, rect in regions],
    }
    report["gate"] = gate_image(report, args.require_region_min_nonblack)
    return report


def print_summary(report: dict[str, Any]) -> None:
    for image in report["images"]:
        print(
            "image: {path} ({width}x{height}, scale={sx}x{sy}) gate={gate}".format(
                path=image["path"],
                width=image["image"]["width"],
                height=image["image"]["height"],
                sx=image["scale"]["x"],
                sy=image["scale"]["y"],
                gate="PASS" if image["gate"]["passed"] else "FAIL",
            )
        )
        for region in image["regions"]:
            largest = region["largest_black_components"][0] if region["largest_black_components"] else {}
            print(
                "  {name}: logical={logical} image=({x},{y}) {w}x{h} "
                "nonblack={nonblack}% black={black}% luma={luma} "
                "largest_black={largest_pct}% {largest_w}x{largest_h} flags={flags}".format(
                    name=region["name"],
                    logical=region["logical_rect"],
                    x=region["image_rect"]["x"],
                    y=region["image_rect"]["y"],
                    w=region["image_rect"]["width"],
                    h=region["image_rect"]["height"],
                    nonblack=region["nonblack_percent"],
                    black=region["black_percent"],
                    luma=region["mean_luma"],
                    largest_pct=region["largest_black_component_percent"],
                    largest_w=largest.get("width", 0),
                    largest_h=largest.get("height", 0),
                    flags=",".join(region["flags"]) if region["flags"] else "-",
                )
            )
            if region["black_bounds_logical"]:
                print(f"    black_bounds_logical: {region['black_bounds_logical']}")
        if image["gate"]["failures"]:
            print(f"  gate_failures: {image['gate']['failures']}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("png", nargs="+", type=Path, help="PNG captures or reconstructed surface dumps")
    parser.add_argument("--logical-width", type=int, default=800)
    parser.add_argument("--logical-height", type=int, default=600)
    parser.add_argument("--threshold", type=int, default=12, help="max RGB at or below this counts as black")
    parser.add_argument("--bright-threshold", type=int, default=96)
    parser.add_argument("--mostly-black-percent", type=float, default=5.0)
    parser.add_argument("--large-component-percent", type=float, default=20.0)
    parser.add_argument("--black-component-min-area", type=int, default=128)
    parser.add_argument("--max-black-components", type=int, default=5)
    parser.add_argument("--region", type=parse_region, action="append", default=[], help="extra name:left,top,right,bottom")
    parser.add_argument("--only-custom-regions", action="store_true")
    parser.add_argument(
        "--require-region-min-nonblack",
        type=parse_region_threshold,
        action="append",
        default=[],
        help="fail with exit 2 unless region has at least this nonblack percent, as name:percent",
    )
    parser.add_argument("--write-json", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    regions = [] if args.only_custom_regions else list(DEFAULT_REGIONS.items())
    regions.extend(args.region)
    report = {
        "parameters": {
            "logical_width": args.logical_width,
            "logical_height": args.logical_height,
            "threshold": args.threshold,
            "bright_threshold": args.bright_threshold,
            "mostly_black_percent": args.mostly_black_percent,
            "large_component_percent": args.large_component_percent,
            "black_component_min_area": args.black_component_min_area,
            "max_black_components": args.max_black_components,
            "require_region_min_nonblack": [
                {"region": name, "minimum_nonblack_percent": percent}
                for name, percent in args.require_region_min_nonblack
            ],
        },
        "regions": [{"name": name, "logical_rect": list(rect)} for name, rect in regions],
        "images": [analyze_image(path, regions, args) for path in args.png],
    }
    if args.write_json:
        args.write_json.parent.mkdir(parents=True, exist_ok=True)
        args.write_json.write_text(json.dumps(report, indent=2), encoding="ascii")
    print_summary(report)
    if any(not image["gate"]["passed"] for image in report["images"]):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
