#!/usr/bin/env python3
"""Inspect the Clash95 HD gameplay border-frame bands in PNG captures/surfdumps.

Repo-side validation helper for the border-frame recovery work (the
``frame-restore-bands`` patch group). It reads existing screenshots or
reconstructed 8-bit surface PNGs, maps the known logical 800x600 border-frame
bands to the actual image size, and reports:

- per-band black / non-black coverage and mean luma (is the gutter still black?);
- for each HD-extension band, how closely the filled art matches an authentic
  native source band, via colour/index histogram intersection (does the fill
  look like the real frame rather than a flat colour or noise?).

The bands follow ``reports/border-frame-recovery.md`` (custom validation
regions). This tool never launches the game and never reads or writes
proprietary binaries.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

from capture_geometry import Image, luminance, read_png


# Logical 800x600 border-frame bands (left, top, right, bottom), inclusive.
# The native 640x480 chrome draws the top frame only across x=0..639 and the
# left frame only down to y=479; the `frame-restore-bands` cave extends both to
# fill the HD 800x600 screen. Roles:
#   *_native            authentic sources / regression controls (stay non-black)
#   *_extension         acceptance bands: were black, must become authentic art
#   bottom_letterbox    x>=32 bottom strip is the intended ~8px letterbox (black)
#   right_ui_band       proxy-only black artifact (real runtime fills it); info
# See reports/border-frame-recovery.md for the original investigation regions.
DEFAULT_REGIONS: dict[str, tuple[int, int, int, int]] = {
    "top_frame_native": (0, 0, 639, 15),
    "top_right_extension": (640, 0, 799, 15),
    "left_frame_native": (0, 16, 31, 479),
    "left_frame_hd_extension": (0, 480, 31, 599),
    "bottom_letterbox": (32, 592, 799, 599),
    "right_ui_band": (586, 230, 799, 599),
}

# Default authenticity pairs: a filled extension band should resemble the
# authentic native source band it is copied from.
#   left gutter extension <- persistent native left frame (copied downward)
#   top-right extension   <- persistent native top frame (copied rightward)
DEFAULT_MATCH_PAIRS: dict[str, str] = {
    "left_frame_hd_extension": "left_frame_native",
    "top_right_extension": "top_frame_native",
}

QUANT_LEVELS = 8  # per-channel histogram buckets (8^3 = 512 bins)


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


def parse_match_pair(value: str) -> tuple[str, str]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("match must be dest=source")
    dest, source = value.split("=", 1)
    dest = dest.strip()
    source = source.strip()
    if not dest or not source:
        raise argparse.ArgumentTypeError("match must be dest=source with both names set")
    return dest, source


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


def quantize(rgb: tuple[int, int, int], levels: int) -> int:
    r, g, b = rgb
    rc = min(levels - 1, r * levels // 256)
    gc = min(levels - 1, g * levels // 256)
    bc = min(levels - 1, b * levels // 256)
    return (rc * levels + gc) * levels + bc


def bucket_center(bucket: int, levels: int) -> tuple[int, int, int]:
    bc = bucket % levels
    gc = (bucket // levels) % levels
    rc = bucket // (levels * levels)
    step = 256 // levels
    half = step // 2
    return (rc * step + half, gc * step + half, bc * step + half)


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
    histogram: dict[int, int] = {}

    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            rgb = image.rgb_at(x, y)
            luma = luminance(rgb)
            total += 1
            luma_sum += luma
            if max(rgb) <= args.threshold:
                black += 1
            else:
                nonblack += 1
            if luma >= args.bright_threshold:
                bright += 1
            bucket = quantize(rgb, QUANT_LEVELS)
            histogram[bucket] = histogram.get(bucket, 0) + 1

    region_pixels = max(1, total)
    nonblack_percent = round(nonblack * 100.0 / region_pixels, 3)
    black_percent = round(black * 100.0 / region_pixels, 3)

    dominant = sorted(histogram.items(), key=lambda kv: kv[1], reverse=True)[:5]
    dominant_colors = [
        {
            "rgb": list(bucket_center(bucket, QUANT_LEVELS)),
            "percent": round(count * 100.0 / region_pixels, 3),
        }
        for bucket, count in dominant
    ]

    flags: list[str] = []
    if nonblack_percent < args.mostly_black_percent:
        flags.append("mostly_black")

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
        "dominant_colors": dominant_colors,
        "flags": flags,
        # kept for histogram-intersection matching; stripped before JSON output.
        "_histogram": histogram,
    }


def histogram_intersection(hist_a: dict[int, int], hist_b: dict[int, int]) -> float:
    total_a = sum(hist_a.values())
    total_b = sum(hist_b.values())
    if total_a == 0 or total_b == 0:
        return 0.0
    shared = 0.0
    for bucket, count in hist_a.items():
        other = hist_b.get(bucket)
        if other:
            shared += min(count / total_a, other / total_b)
    return round(shared, 4)


def gate_image(
    image_report: dict[str, Any],
    thresholds: list[tuple[str, float]],
    match_min: list[tuple[str, float]],
) -> dict[str, Any]:
    regions = {region["name"]: region for region in image_report["regions"]}
    matches = {match["dest"]: match for match in image_report["matches"]}
    failures = []
    checks = []
    for name, minimum in thresholds:
        region = regions.get(name)
        if not region:
            failures.append({"region": name, "reason": "missing_region", "minimum_nonblack_percent": minimum})
            continue
        actual = float(region["nonblack_percent"])
        check = {
            "kind": "nonblack",
            "region": name,
            "minimum_nonblack_percent": minimum,
            "actual_nonblack_percent": actual,
            "passed": actual >= minimum,
        }
        checks.append(check)
        if not check["passed"]:
            failures.append({**check, "reason": "low_nonblack_percent"})
    for dest, minimum in match_min:
        match = matches.get(dest)
        if not match:
            failures.append({"dest": dest, "reason": "missing_match", "minimum_similarity": minimum})
            continue
        actual = float(match["similarity"])
        check = {
            "kind": "match",
            "dest": dest,
            "source": match["source"],
            "minimum_similarity": minimum,
            "actual_similarity": actual,
            "passed": actual >= minimum,
        }
        checks.append(check)
        if not check["passed"]:
            failures.append({**check, "reason": "low_similarity"})
    return {"passed": not failures, "checks": checks, "failures": failures}


def analyze_image(
    path: Path,
    regions: list[tuple[str, tuple[int, int, int, int]]],
    match_pairs: dict[str, str],
    args: argparse.Namespace,
) -> dict[str, Any]:
    image = read_png(path)
    region_reports = [analyze_region(image, name, rect, args) for name, rect in regions]
    by_name = {region["name"]: region for region in region_reports}

    matches: list[dict[str, Any]] = []
    for dest, source in match_pairs.items():
        dest_region = by_name.get(dest)
        source_region = by_name.get(source)
        if not dest_region or not source_region:
            continue
        similarity = histogram_intersection(dest_region["_histogram"], source_region["_histogram"])
        matches.append(
            {
                "dest": dest,
                "source": source,
                "similarity": similarity,
                "dest_nonblack_percent": dest_region["nonblack_percent"],
                "source_nonblack_percent": source_region["nonblack_percent"],
            }
        )

    for region in region_reports:
        region.pop("_histogram", None)

    report = {
        "path": str(path),
        "image": {"width": image.width, "height": image.height},
        "logical_size": {"width": args.logical_width, "height": args.logical_height},
        "scale": {
            "x": round(image.width / args.logical_width, 6),
            "y": round(image.height / args.logical_height, 6),
        },
        "regions": region_reports,
        "matches": matches,
    }
    report["gate"] = gate_image(report, args.require_region_min_nonblack, args.require_match_min_similarity)
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
            dominant = region["dominant_colors"][0] if region["dominant_colors"] else {}
            print(
                "  {name}: logical={logical} image=({x},{y}) {w}x{h} "
                "nonblack={nonblack}% black={black}% luma={luma} "
                "dom_rgb={dom} ({dom_pct}%) flags={flags}".format(
                    name=region["name"],
                    logical=region["logical_rect"],
                    x=region["image_rect"]["x"],
                    y=region["image_rect"]["y"],
                    w=region["image_rect"]["width"],
                    h=region["image_rect"]["height"],
                    nonblack=region["nonblack_percent"],
                    black=region["black_percent"],
                    luma=region["mean_luma"],
                    dom=dominant.get("rgb"),
                    dom_pct=dominant.get("percent"),
                    flags=",".join(region["flags"]) if region["flags"] else "-",
                )
            )
        for match in image["matches"]:
            print(
                "  match {dest} <- {source}: similarity={sim} "
                "(dest_nonblack={dnb}% source_nonblack={snb}%)".format(
                    dest=match["dest"],
                    source=match["source"],
                    sim=match["similarity"],
                    dnb=match["dest_nonblack_percent"],
                    snb=match["source_nonblack_percent"],
                )
            )
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
    parser.add_argument("--region", type=parse_region, action="append", default=[], help="extra name:left,top,right,bottom")
    parser.add_argument("--only-custom-regions", action="store_true")
    parser.add_argument("--match", type=parse_match_pair, action="append", default=[], help="extra authenticity pair dest=source")
    parser.add_argument("--no-default-matches", action="store_true", help="skip the built-in authenticity pairs")
    parser.add_argument(
        "--require-region-min-nonblack",
        type=parse_region_threshold,
        action="append",
        default=[],
        help="fail with exit 2 unless region has at least this nonblack percent, as name:percent",
    )
    parser.add_argument(
        "--require-match-min-similarity",
        type=parse_region_threshold,
        action="append",
        default=[],
        help="fail with exit 2 unless a match's similarity is at least this, as dest:fraction(0..100 scaled)",
    )
    parser.add_argument("--write-json", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    regions = [] if args.only_custom_regions else list(DEFAULT_REGIONS.items())
    regions.extend(args.region)

    match_pairs: dict[str, str] = {} if args.no_default_matches else dict(DEFAULT_MATCH_PAIRS)
    for dest, source in args.match:
        match_pairs[dest] = source

    # require-match-min-similarity thresholds are given as percentages (0..100)
    # for CLI consistency with the nonblack gate; convert to the 0..1 scale that
    # histogram intersection uses, and do it BEFORE any gate runs.
    match_min = [(name, percent / 100.0) for name, percent in args.require_match_min_similarity]
    args.require_match_min_similarity = match_min

    report = {
        "parameters": {
            "logical_width": args.logical_width,
            "logical_height": args.logical_height,
            "threshold": args.threshold,
            "bright_threshold": args.bright_threshold,
            "mostly_black_percent": args.mostly_black_percent,
            "quant_levels": QUANT_LEVELS,
            "match_pairs": [{"dest": dest, "source": source} for dest, source in match_pairs.items()],
            "require_region_min_nonblack": [
                {"region": name, "minimum_nonblack_percent": percent}
                for name, percent in args.require_region_min_nonblack
            ],
            "require_match_min_similarity": [
                {"dest": name, "minimum_similarity": value} for name, value in match_min
            ],
        },
        "regions": [{"name": name, "logical_rect": list(rect)} for name, rect in regions],
        "images": [analyze_image(path, regions, match_pairs, args) for path in args.png],
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
