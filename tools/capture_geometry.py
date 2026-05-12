#!/usr/bin/env python3
"""Analyze Clash95 click-test PNG captures without external dependencies."""

from __future__ import annotations

import argparse
import json
import struct
import zlib
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


@dataclass(frozen=True)
class Image:
    width: int
    height: int
    pixels: list[tuple[int, int, int]]

    def rgb_at(self, x: int, y: int) -> tuple[int, int, int]:
        return self.pixels[y * self.width + x]


def paeth(a: int, b: int, c: int) -> int:
    p = a + b - c
    pa = abs(p - a)
    pb = abs(p - b)
    pc = abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    if pb <= pc:
        return b
    return c


def read_png(path: Path) -> Image:
    data = path.read_bytes()
    if not data.startswith(PNG_SIGNATURE):
        raise ValueError(f"not a PNG file: {path}")

    pos = len(PNG_SIGNATURE)
    width = height = bit_depth = color_type = None
    compressed = bytearray()
    while pos < len(data):
        length = struct.unpack(">I", data[pos : pos + 4])[0]
        chunk_type = data[pos + 4 : pos + 8]
        chunk_data = data[pos + 8 : pos + 8 + length]
        pos += 12 + length
        if chunk_type == b"IHDR":
            width, height, bit_depth, color_type, _, _, _ = struct.unpack(">IIBBBBB", chunk_data)
        elif chunk_type == b"IDAT":
            compressed.extend(chunk_data)
        elif chunk_type == b"IEND":
            break

    if width is None or height is None or bit_depth != 8:
        raise ValueError(f"unsupported PNG header in {path}")

    channels_by_type = {
        0: 1,  # grayscale
        2: 3,  # RGB
        6: 4,  # RGBA
    }
    if color_type not in channels_by_type:
        raise ValueError(f"unsupported PNG color type {color_type} in {path}")

    channels = channels_by_type[color_type]
    row_bytes = width * channels
    raw = zlib.decompress(bytes(compressed))
    rows: list[bytes] = []
    raw_pos = 0
    prior = bytearray(row_bytes)
    for _ in range(height):
        filter_type = raw[raw_pos]
        raw_pos += 1
        current = bytearray(raw[raw_pos : raw_pos + row_bytes])
        raw_pos += row_bytes

        for i in range(row_bytes):
            left = current[i - channels] if i >= channels else 0
            up = prior[i]
            upper_left = prior[i - channels] if i >= channels else 0
            if filter_type == 1:
                current[i] = (current[i] + left) & 0xFF
            elif filter_type == 2:
                current[i] = (current[i] + up) & 0xFF
            elif filter_type == 3:
                current[i] = (current[i] + ((left + up) // 2)) & 0xFF
            elif filter_type == 4:
                current[i] = (current[i] + paeth(left, up, upper_left)) & 0xFF
            elif filter_type != 0:
                raise ValueError(f"unsupported PNG filter {filter_type} in {path}")

        rows.append(bytes(current))
        prior = current

    pixels: list[tuple[int, int, int]] = []
    for row in rows:
        for x in range(width):
            offset = x * channels
            if color_type == 0:
                value = row[offset]
                pixels.append((value, value, value))
            else:
                pixels.append((row[offset], row[offset + 1], row[offset + 2]))

    return Image(width=width, height=height, pixels=pixels)


def luminance(rgb: tuple[int, int, int]) -> float:
    r, g, b = rgb
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def bounds_for(
    image: Image,
    predicate,
) -> dict[str, int] | None:
    min_x = image.width
    min_y = image.height
    max_x = -1
    max_y = -1
    count = 0
    for y in range(image.height):
        row = y * image.width
        for x in range(image.width):
            if predicate(image.pixels[row + x]):
                min_x = min(min_x, x)
                min_y = min(min_y, y)
                max_x = max(max_x, x)
                max_y = max(max_y, y)
                count += 1
    if count == 0:
        return None
    return {
        "x": min_x,
        "y": min_y,
        "right": max_x,
        "bottom": max_y,
        "width": max_x - min_x + 1,
        "height": max_y - min_y + 1,
        "pixels": count,
    }


def changed_bounds(before: Image, after: Image, threshold: int) -> dict[str, int | float] | None:
    if before.width != after.width or before.height != after.height:
        raise ValueError("cannot diff images with different dimensions")

    min_x = before.width
    min_y = before.height
    max_x = -1
    max_y = -1
    changed = 0
    for i, (a, b) in enumerate(zip(before.pixels, after.pixels)):
        if max(abs(a[0] - b[0]), abs(a[1] - b[1]), abs(a[2] - b[2])) > threshold:
            y, x = divmod(i, before.width)
            min_x = min(min_x, x)
            min_y = min(min_y, y)
            max_x = max(max_x, x)
            max_y = max(max_y, y)
            changed += 1
    if changed == 0:
        return None
    total = before.width * before.height
    return {
        "x": min_x,
        "y": min_y,
        "right": max_x,
        "bottom": max_y,
        "width": max_x - min_x + 1,
        "height": max_y - min_y + 1,
        "pixels": changed,
        "percent": round(changed * 100.0 / total, 3),
        "center_x": round((min_x + max_x) / 2.0, 2),
        "center_y": round((min_y + max_y) / 2.0, 2),
    }


def region_stats(
    image: Image,
    center_x: int,
    center_y: int,
    radius: int,
    threshold: int,
) -> dict[str, int | float]:
    x0 = max(0, center_x - radius)
    y0 = max(0, center_y - radius)
    x1 = min(image.width - 1, center_x + radius)
    y1 = min(image.height - 1, center_y + radius)
    total = 0
    nonblack = 0
    bright = 0
    lum_sum = 0.0
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            rgb = image.rgb_at(x, y)
            lum = luminance(rgb)
            total += 1
            lum_sum += lum
            if max(rgb) > threshold:
                nonblack += 1
            if lum >= 96:
                bright += 1
    return {
        "x": x0,
        "y": y0,
        "right": x1,
        "bottom": y1,
        "pixels": total,
        "mean_luma": round(lum_sum / total, 2) if total else 0,
        "nonblack_percent": round(nonblack * 100.0 / total, 2) if total else 0,
        "bright_percent": round(bright * 100.0 / total, 2) if total else 0,
    }


def changed_region_percent(
    before: Image,
    after: Image,
    center_x: int,
    center_y: int,
    radius: int,
    threshold: int,
) -> float | None:
    if before.width != after.width or before.height != after.height:
        return None
    x0 = max(0, center_x - radius)
    y0 = max(0, center_y - radius)
    x1 = min(before.width - 1, center_x + radius)
    y1 = min(before.height - 1, center_y + radius)
    total = 0
    changed = 0
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            a = before.rgb_at(x, y)
            b = after.rgb_at(x, y)
            total += 1
            if max(abs(a[0] - b[0]), abs(a[1] - b[1]), abs(a[2] - b[2])) > threshold:
                changed += 1
    return round(changed * 100.0 / total, 3) if total else None


def analyze_case(result: dict, threshold: int, radius: int) -> dict:
    before_path = Path(result["Before"]) if result.get("Before") else None
    after_path = Path(result["After"]) if result.get("After") else None
    if before_path is None or not before_path.exists():
        return {"case": result.get("Case"), "error": "before image missing"}

    before = read_png(before_path)
    after = read_png(after_path) if after_path and after_path.exists() else None

    nonblack = bounds_for(before, lambda rgb: max(rgb) > threshold)
    light_ui = bounds_for(
        before,
        lambda rgb: luminance(rgb) >= 64 and (max(rgb) - min(rgb) <= 110 or min(rgb) >= 80),
    )

    click_x = int(result.get("ClientClickX") or 0)
    click_y = int(result.get("ClientClickY") or 0)
    target = region_stats(before, click_x, click_y, radius, threshold)
    target["changed_percent"] = (
        changed_region_percent(before, after, click_x, click_y, radius, threshold) if after else None
    )

    diff = changed_bounds(before, after, threshold) if after else None
    border = None
    nonblack_percent = 0.0
    click_in_nonblack = False
    if nonblack:
        nonblack_percent = round(nonblack["pixels"] * 100.0 / (before.width * before.height), 3)
        click_in_nonblack = (
            nonblack["x"] <= click_x <= nonblack["right"]
            and nonblack["y"] <= click_y <= nonblack["bottom"]
        )
        border = {
            "left": nonblack["x"],
            "top": nonblack["y"],
            "right": before.width - 1 - nonblack["right"],
            "bottom": before.height - 1 - nonblack["bottom"],
        }

    click_delta = None
    if diff:
        click_delta = {
            "dx": round(click_x - diff["center_x"], 2),
            "dy": round(click_y - diff["center_y"], 2),
        }

    frame_flags: list[str] = []
    if nonblack_percent < 0.5:
        frame_flags.append("all_black_or_blank")
    if border == {"left": 0, "top": 0, "right": 0, "bottom": 0}:
        frame_flags.append("full_frame_nonblack")
    if diff:
        frame_flags.append("changed_after_click")
    else:
        frame_flags.append("stable_after_click")

    return {
        "case": result.get("Case"),
        "click": result.get("Click"),
        "passed": result.get("Passed"),
        "error": result.get("Error"),
        "before_hash": result.get("BeforeHash"),
        "after_hash": result.get("AfterHash"),
        "image": {"width": before.width, "height": before.height},
        "reported_client": {
            "width": result.get("ClientWidth"),
            "height": result.get("ClientHeight"),
            "render_scale": result.get("RenderScale"),
        },
        "nonblack_bounds": nonblack,
        "nonblack_percent": nonblack_percent,
        "nonblack_border": border,
        "approx_menu_panel_bounds": light_ui,
        "click_in_nonblack_bounds": click_in_nonblack,
        "click_target_probe": target,
        "changed_bounds": diff,
        "click_delta_from_changed_bounds_center": click_delta,
        "frame_state_hint": frame_flags,
    }


def load_results(capture_dir: Path) -> list[dict]:
    path = capture_dir / "results.json"
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    return data if isinstance(data, list) else [data]


def latest_capture_dir(root: Path) -> Path:
    candidates = sorted(p for p in root.glob("clicktest-*") if (p / "results.json").exists())
    if not candidates:
        raise SystemExit(f"no clicktest results found under {root}")
    return candidates[-1]


def print_summary(report: dict) -> None:
    print(f"capture: {report['capture_dir']}")
    for case in report["cases"]:
        if case.get("error") and "image" not in case:
            print(f"- {case.get('case')}: {case['error']}")
            continue
        nb = case.get("nonblack_bounds") or {}
        panel = case.get("approx_menu_panel_bounds") or {}
        diff = case.get("changed_bounds") or {}
        target = case.get("click_target_probe") or {}
        delta = case.get("click_delta_from_changed_bounds_center") or {}
        print(
            "- {case}: image={w}x{h} nonblack=({x},{y}) {bw}x{bh} "
            "panel~=({px},{py}) {pw}x{ph} target_luma={lum} "
            "target_changed={tc}% diff={dc}% delta=({dx},{dy}) "
            "flags={flags} passed={passed} error={err}".format(
                case=case.get("case"),
                w=case.get("image", {}).get("width"),
                h=case.get("image", {}).get("height"),
                x=nb.get("x"),
                y=nb.get("y"),
                bw=nb.get("width"),
                bh=nb.get("height"),
                px=panel.get("x"),
                py=panel.get("y"),
                pw=panel.get("width"),
                ph=panel.get("height"),
                lum=target.get("mean_luma"),
                tc=target.get("changed_percent"),
                dc=diff.get("percent", 0),
                dx=delta.get("dx"),
                dy=delta.get("dy"),
                flags=",".join(case.get("frame_state_hint", [])),
                passed=case.get("passed"),
                err=case.get("error"),
            )
        )
    warnings = report.get("warnings") or []
    for warning in warnings:
        print(f"warning: {warning}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze Clash95 click-test capture geometry.")
    parser.add_argument(
        "capture_dir",
        nargs="?",
        type=Path,
        help="capture clicktest directory; defaults to latest under captures/",
    )
    parser.add_argument("--captures-root", type=Path, default=Path("captures"))
    parser.add_argument("--threshold", type=int, default=12)
    parser.add_argument("--target-radius", type=int, default=18)
    parser.add_argument("--write-json", action="store_true", help="write geometry.json next to results.json")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    capture_dir = args.capture_dir or latest_capture_dir(args.captures_root)
    results = load_results(capture_dir)
    before_hash_counts: dict[str, int] = {}
    for result in results:
        value = result.get("BeforeHash")
        if value:
            before_hash_counts[value] = before_hash_counts.get(value, 0) + 1
    report = {
        "capture_dir": str(capture_dir),
        "threshold": args.threshold,
        "target_radius": args.target_radius,
        "cases": [analyze_case(result, args.threshold, args.target_radius) for result in results],
        "warnings": [],
    }
    for case in report["cases"]:
        before_hash = case.get("before_hash")
        if before_hash:
            case["before_hash_reused_count"] = before_hash_counts.get(before_hash, 0)
            if before_hash_counts.get(before_hash, 0) == 1 and len(before_hash_counts) > 1:
                case["frame_state_hint"].append("unique_before_state")
                report["warnings"].append(
                    f"{case.get('case')} has a unique before-frame hash; compare state before treating pass/fail as click evidence"
                )
        if "full_frame_nonblack" in case.get("frame_state_hint", []):
            report["warnings"].append(
                f"{case.get('case')} has full-frame nonblack bounds; border detection alone cannot prove menu placement"
            )
    if args.write_json:
        (capture_dir / "geometry.json").write_text(json.dumps(report, indent=2), encoding="ascii")
    print_summary(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
