#!/usr/bin/env python3
"""Analyze Clash95 HD gameplay tile coverage in captured PNG frames.

The HD map path draws logical 64x64 map cells starting at x=32, y=16. This
helper measures those logical cells in scaled captures, masks known UI overlays
such as the moved minimap, and reports blank or suspiciously low-detail cells.
It is intentionally conservative: the report is evidence for where to inspect,
not proof that a patch is wrong.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

from capture_geometry import Image, luminance, read_png
from action_bar_surface_audit import FRAMED_STAGE, framed_stage
from src.patcher.framed_viewport import FramedViewport


DEFAULT_MASKS = {
    "hd_minimap": (586, 16, 799, 229),
}


def default_masks(logical_width: int) -> dict[str, tuple[int, int, int, int]]:
    """The 214px minimap is right-anchored; retain the legacy 800px mapping."""
    return {"hd_minimap": (logical_width - 214, 16, logical_width - 1, 229)}


def framed_coverage_geometry(stage: str, width: int, height: int, *,
                             minimap_enabled: bool, minimap_width: int | None = None,
                             minimap_height: int | None = None) -> dict[str, Any]:
    """Exact stage geometry, requiring observed enabled minimap dimensions.

    This capture lane requires the renderer's separately verified in-world
    ceiling window. It does not reclassify outside-world clears as terrain or
    derive visibility from PNG colors. UI masks remain explicitly unmeasured;
    action-bar and four-border source-pixel audits are separate requirements.
    """
    if not framed_stage(stage):
        raise ValueError("framed coverage requires the exact framed stage")
    layout = FramedViewport(width, height)
    if type(minimap_enabled) is not bool:
        raise ValueError("framed coverage requires observed minimap enabled state")
    masks = [("framed_commands", layout.action_bar.as_tuple())]
    if minimap_enabled:
        if type(minimap_width) is not int or type(minimap_height) is not int:
            raise ValueError("enabled minimap requires actual backing width and height")
        box = layout.minimap_box(minimap_width, minimap_height)
        masks.append(("hd_minimap", box.as_tuple()))
    elif minimap_width is not None or minimap_height is not None:
        raise ValueError("disabled minimap does not accept an enabled backing mask")
    cols, rows = layout.ceil_tiles
    cells = []
    for row in range(rows):
        for col in range(cols):
            rect = layout.cell_rect(col, row)
            cells.append(dict(id=f"r{row}c{col}", row=row, col=col, active=True,
                              logical_rect=rect.as_tuple(), partial=rect.width != 64 or rect.height != 64))
    return dict(stage=stage, terrain=list(layout.terrain.as_tuple()), columns=cols, rows=rows,
                cells=cells, masks=masks,
                minimap=dict(enabled=minimap_enabled, width=minimap_width, height=minimap_height,
                             exclusive_right=width-32),
                limits="Requires a separately verified in-world ceiling window. Masked UI cells are not terrain proof; frame/action-bar/input/runtime acceptance remains separate.")


def region_nonblack_percent(
    image: Image,
    logical_rect: tuple[int, int, int, int],
    logical_width: int,
    logical_height: int,
    threshold: int,
) -> float:
    if logical_rect[0] > logical_rect[2] or logical_rect[1] > logical_rect[3]:
        return 0.0
    x0, y0, x1, y1 = logical_rect_to_pixels(image, logical_rect, logical_width, logical_height)
    total = 0
    nonblack = 0
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            total += 1
            if max(image.rgb_at(x, y)) > threshold:
                nonblack += 1
    return round(nonblack * 100.0 / total, 3) if total else 0.0


def gameplay_frame_check(image: Image, args: argparse.Namespace) -> dict[str, Any]:
    """Return conservative confidence signals for logical gameplay-map captures."""

    full = (0, 0, args.logical_width - 1, args.logical_height - 1)
    top_border = (0, 0, args.logical_width - 1, min(15, args.logical_height - 1))
    left_border = (0, 0, min(31, args.logical_width - 1), args.logical_height - 1)
    right_edge = (
        max(0, args.logical_width - 64),
        min(230, args.logical_height - 1),
        args.logical_width - 1,
        args.logical_height - 1,
    )
    bottom_edge = (
        0,
        max(0, args.logical_height - 64),
        args.logical_width - 1,
        args.logical_height - 1,
    )
    framed = getattr(args, "framed_geometry", None)
    if framed is not None:
        left, top, right, bottom = framed["terrain"]
        minimap = framed["minimap"]
        below_minimap = top + minimap["height"] if minimap["enabled"] else top
        right_edge = (max(left, right-63), below_minimap, right, bottom)
        bottom_edge = (left, max(top, bottom-63), right, bottom)

    edge_coverage = {
        "overall_nonblack_percent": region_nonblack_percent(
            image, full, args.logical_width, args.logical_height, args.threshold
        ),
        "top_border_nonblack_percent": region_nonblack_percent(
            image, top_border, args.logical_width, args.logical_height, args.threshold
        ),
        "left_border_nonblack_percent": region_nonblack_percent(
            image, left_border, args.logical_width, args.logical_height, args.threshold
        ),
        "right_edge_below_minimap_nonblack_percent": region_nonblack_percent(
            image, right_edge, args.logical_width, args.logical_height, args.threshold
        ),
        "bottom_edge_nonblack_percent": region_nonblack_percent(
            image, bottom_edge, args.logical_width, args.logical_height, args.threshold
        ),
    }

    warnings: list[str] = []
    if (
        edge_coverage["top_border_nonblack_percent"] < args.min_gameplay_border_percent
        and edge_coverage["left_border_nonblack_percent"] < args.min_gameplay_border_percent
    ):
        warnings.append("low_top_left_gameplay_border_coverage")
    if edge_coverage["overall_nonblack_percent"] < args.min_gameplay_overall_percent:
        warnings.append("low_overall_gameplay_coverage")

    return {
        "gameplay_frame_likely": not warnings,
        "warnings": warnings,
        "edge_coverage": edge_coverage,
    }


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


def parse_mask(value: str) -> tuple[str, tuple[int, int, int, int]]:
    if ":" in value:
        name, rect_text = value.split(":", 1)
    else:
        name = f"mask_{abs(hash(value)) & 0xFFFF:04x}"
        rect_text = value
    parts = [part.strip() for part in rect_text.split(",")]
    if len(parts) != 4:
        raise argparse.ArgumentTypeError("mask must be name:left,top,right,bottom or left,top,right,bottom")
    try:
        left, top, right, bottom = [int(part, 0) for part in parts]
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid mask coordinate: {value}") from exc
    if right < left or bottom < top:
        raise argparse.ArgumentTypeError(f"invalid mask rectangle: {value}")
    return name, (left, top, right, bottom)


def overlaps(rect: tuple[int, int, int, int], other: tuple[int, int, int, int]) -> bool:
    return not (rect[2] < other[0] or other[2] < rect[0] or rect[3] < other[1] or other[3] < rect[1])


def contains(rect: tuple[int, int, int, int], x: int, y: int) -> bool:
    return rect[0] <= x <= rect[2] and rect[1] <= y <= rect[3]


def cell_stats(
    image: Image,
    logical_rect: tuple[int, int, int, int],
    mask_rects: list[tuple[str, tuple[int, int, int, int]]],
    logical_width: int,
    logical_height: int,
    threshold: int,
    black_percent: float,
    low_detail_bins: int,
    min_unmasked_percent: float,
) -> dict[str, Any]:
    image_rect = logical_rect_to_pixels(image, logical_rect, logical_width, logical_height)
    image_masks = [
        (name, logical_rect_to_pixels(image, rect, logical_width, logical_height))
        for name, rect in mask_rects
        if overlaps(logical_rect, rect)
    ]

    total = 0
    masked = 0
    sampled = 0
    nonblack = 0
    luma_sum = 0.0
    min_luma = 255.0
    max_luma = 0.0
    quantized_colors: set[tuple[int, int, int]] = set()
    mask_hits: dict[str, int] = {}

    x0, y0, x1, y1 = image_rect
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            total += 1
            hit_name = None
            for name, mask in image_masks:
                if contains(mask, x, y):
                    hit_name = name
                    break
            if hit_name:
                masked += 1
                mask_hits[hit_name] = mask_hits.get(hit_name, 0) + 1
                continue
            rgb = image.rgb_at(x, y)
            luma = luminance(rgb)
            sampled += 1
            luma_sum += luma
            min_luma = min(min_luma, luma)
            max_luma = max(max_luma, luma)
            if max(rgb) > threshold:
                nonblack += 1
            quantized_colors.add((rgb[0] >> 4, rgb[1] >> 4, rgb[2] >> 4))

    nonblack_percent = round(nonblack * 100.0 / sampled, 3) if sampled else 0.0
    masked_percent = round(masked * 100.0 / total, 3) if total else 0.0
    unmasked_percent = round(sampled * 100.0 / total, 3) if total else 0.0
    flags: list[str] = []
    if unmasked_percent < min_unmasked_percent:
        flags.append("insufficient_unmasked")
    if sampled and nonblack_percent < black_percent:
        flags.append("blank")
    if (
        low_detail_bins > 0
        and sampled
        and nonblack_percent >= black_percent
        and len(quantized_colors) <= low_detail_bins
    ):
        flags.append("possible_stale_or_solid")

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
        "sampled_pixels": sampled,
        "masked_pixels": masked,
        "masked_percent": masked_percent,
        "unmasked_percent": unmasked_percent,
        "mask_hits": mask_hits,
        "nonblack_percent": nonblack_percent,
        "mean_luma": round(luma_sum / sampled, 3) if sampled else 0.0,
        "min_luma": round(min_luma, 3) if sampled else 0.0,
        "max_luma": round(max_luma, 3) if sampled else 0.0,
        "quantized_color_bins": len(quantized_colors),
        "flags": flags,
    }


def build_cells(
    origin_x: int,
    origin_y: int,
    tile_size: int,
    columns: int,
    rows: int,
    bottom_row_active_cols: int,
) -> list[dict[str, Any]]:
    cells: list[dict[str, Any]] = []
    for row in range(rows):
        active_cols = columns
        if row == rows - 1 and bottom_row_active_cols > 0:
            active_cols = min(columns, bottom_row_active_cols)
        for col in range(columns):
            left = origin_x + col * tile_size
            top = origin_y + row * tile_size
            cells.append(
                {
                    "id": f"r{row}c{col}",
                    "row": row,
                    "col": col,
                    "active": col < active_cols,
                    "logical_rect": (left, top, left + tile_size - 1, top + tile_size - 1),
                }
            )
    return cells


def analyze_image(
    path: Path,
    cells: list[dict[str, Any]],
    masks: list[tuple[str, tuple[int, int, int, int]]],
    args: argparse.Namespace,
) -> dict[str, Any]:
    image = read_png(path)
    if (getattr(args, "framed_geometry", None) is not None and
            (image.width, image.height) != (args.logical_width, args.logical_height)):
        raise ValueError("framed capture dimensions differ from the bound physical resolution")
    frame_check = gameplay_frame_check(image, args)
    analyzed_cells = []
    flagged_cells = []
    inactive_cells = []

    for cell in cells:
        stats = cell_stats(
            image,
            cell["logical_rect"],
            masks,
            args.logical_width,
            args.logical_height,
            args.threshold,
            args.black_percent,
            args.low_detail_bins,
            args.min_unmasked_percent,
        )
        row = {
            "id": cell["id"],
            "row": cell["row"],
            "col": cell["col"],
            "active": cell["active"],
            **stats,
        }
        if "partial" in cell:
            row["partial"] = cell["partial"]
        if not cell["active"]:
            row["flags"] = ["inactive_bottom_clip", *row["flags"]]
            inactive_cells.append(row["id"])
        elif any(flag in {"blank", "possible_stale_or_solid"} for flag in row["flags"]):
            flagged_cells.append(row["id"])
        analyzed_cells.append(row)

    active_cells = [cell for cell in analyzed_cells if cell["active"]]
    blank_cells = [cell["id"] for cell in active_cells if "blank" in cell["flags"]]
    stale_cells = [cell["id"] for cell in active_cells if "possible_stale_or_solid" in cell["flags"]]
    insufficient_cells = [cell["id"] for cell in active_cells if "insufficient_unmasked" in cell["flags"]]
    measurable_cells = [cell for cell in active_cells if "insufficient_unmasked" not in cell["flags"]]
    lowest_nonblack = sorted(
        measurable_cells,
        key=lambda cell: (cell["nonblack_percent"], cell["unmasked_percent"]),
    )[:8]

    return {
        "path": str(path),
        "image": {"width": image.width, "height": image.height},
        "logical_size": {"width": args.logical_width, "height": args.logical_height},
        "scale": {
            "x": round(image.width / args.logical_width, 6),
            "y": round(image.height / args.logical_height, 6),
        },
        "frame_check": frame_check,
        "summary": {
            "cells": len(analyzed_cells),
            "active_cells": len(active_cells),
            "inactive_cells": len(inactive_cells),
            "flagged_active_cells": len(flagged_cells),
            "blank_active_cells": blank_cells,
            "possible_stale_or_solid_active_cells": stale_cells,
            "insufficient_unmasked_active_cells": insufficient_cells,
            "measurable_active_cells": len(measurable_cells),
            "lowest_nonblack_active_cells": [
                {
                    "id": cell["id"],
                    "logical_rect": cell["logical_rect"],
                    "nonblack_percent": cell["nonblack_percent"],
                    "unmasked_percent": cell["unmasked_percent"],
                    "mean_luma": cell["mean_luma"],
                    "flags": cell["flags"],
                }
                for cell in lowest_nonblack
            ],
        },
        "cells": analyzed_cells,
    }


def print_summary(report: dict[str, Any]) -> None:
    for image in report["images"]:
        summary = image["summary"]
        frame_check = image["frame_check"]
        print(
            "image: {path} ({width}x{height}, scale={sx}x{sy}) active={active} "
            "measurable={measurable} inactive={inactive} flagged={flagged} blank={blank} "
            "stale_or_solid={stale}".format(
                path=image["path"],
                width=image["image"]["width"],
                height=image["image"]["height"],
                sx=image["scale"]["x"],
                sy=image["scale"]["y"],
                active=summary["active_cells"],
                measurable=summary["measurable_active_cells"],
                inactive=summary["inactive_cells"],
                flagged=summary["flagged_active_cells"],
                blank=len(summary["blank_active_cells"]),
                stale=len(summary["possible_stale_or_solid_active_cells"]),
            )
        )
        print(
            "  gameplay_frame_likely={likely} warnings={warnings}".format(
                likely=frame_check["gameplay_frame_likely"],
                warnings=",".join(frame_check["warnings"]) if frame_check["warnings"] else "-",
            )
        )
        edge = frame_check["edge_coverage"]
        print(
            "  edge_coverage: overall={overall}% top={top}% left={left}% "
            "right_below_minimap={right}% bottom={bottom}%".format(
                overall=edge["overall_nonblack_percent"],
                top=edge["top_border_nonblack_percent"],
                left=edge["left_border_nonblack_percent"],
                right=edge["right_edge_below_minimap_nonblack_percent"],
                bottom=edge["bottom_edge_nonblack_percent"],
            )
        )
        if summary["blank_active_cells"]:
            print("  blank_active_cells: " + ", ".join(summary["blank_active_cells"]))
        if summary["possible_stale_or_solid_active_cells"]:
            print("  possible_stale_or_solid_active_cells: " + ", ".join(summary["possible_stale_or_solid_active_cells"]))
        if summary["insufficient_unmasked_active_cells"]:
            print("  masked_or_insufficient_active_cells: " + ", ".join(summary["insufficient_unmasked_active_cells"]))
        print("  lowest_nonblack_active_cells:")
        for cell in summary["lowest_nonblack_active_cells"]:
            print(
                "    {id}: nonblack={nonblack}% unmasked={unmasked}% mean_luma={luma} flags={flags}".format(
                    id=cell["id"],
                    nonblack=cell["nonblack_percent"],
                    unmasked=cell["unmasked_percent"],
                    luma=cell["mean_luma"],
                    flags=",".join(cell["flags"]) if cell["flags"] else "-",
                )
            )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("png", nargs="+", type=Path, help="PNG gameplay capture(s) to inspect")
    parser.add_argument("--logical-width", type=int, default=800)
    parser.add_argument("--logical-height", type=int, default=600)
    parser.add_argument("--stage", help="exact producer stage; framed geometry is never inferred from size")
    parser.add_argument("--minimap-enabled", type=int, choices=(0, 1),
                        help="observed enabled state, required only by the framed stage")
    parser.add_argument("--minimap-width", type=int, help="actual enabled minimap backing width")
    parser.add_argument("--minimap-height", type=int, help="actual enabled minimap backing height")
    parser.add_argument("--origin-x", type=int, default=32)
    parser.add_argument("--origin-y", type=int, default=16)
    parser.add_argument("--tile-size", type=int, default=64)
    parser.add_argument("--columns", type=int)
    parser.add_argument("--rows", type=int)
    parser.add_argument(
        "--bottom-row-active-cols",
        type=int,
        default=None,
        help="active cells in the clipped bottom row; 0 treats all columns as active",
    )
    parser.add_argument("--threshold", type=int, default=12, help="max RGB above this counts as nonblack")
    parser.add_argument("--black-percent", type=float, default=5.0)
    parser.add_argument(
        "--min-gameplay-border-percent",
        type=float,
        default=20.0,
        help="warn when both top and left logical gameplay border coverage fall below this",
    )
    parser.add_argument(
        "--min-gameplay-overall-percent",
        type=float,
        default=50.0,
        help="warn when whole-frame nonblack coverage falls below this",
    )
    parser.add_argument(
        "--require-gameplay",
        action="store_true",
        help="exit 2 if any analyzed image does not look like a gameplay-map frame",
    )
    parser.add_argument(
        "--low-detail-bins",
        type=int,
        default=0,
        help="flag nonblank cells with this many or fewer quantized color bins; 0 disables the heuristic",
    )
    parser.add_argument("--min-unmasked-percent", type=float, default=20.0)
    parser.add_argument(
        "--mask",
        type=parse_mask,
        action="append",
        default=[],
        help="extra mask as name:left,top,right,bottom in logical coordinates",
    )
    parser.add_argument("--no-default-masks", action="store_true")
    parser.add_argument("--write-json", type=Path)
    args = parser.parse_args()
    args.framed_geometry = None
    try:
        is_framed = framed_stage(args.stage)
        if is_framed:
            if args.minimap_enabled is None:
                raise ValueError("framed stage requires --minimap-enabled from the observed capture")
            if (args.origin_x, args.origin_y, args.tile_size) != (32, 16, 64):
                raise ValueError("framed terrain origin and tile size cannot be overridden")
            if any(v is not None for v in (args.columns, args.rows, args.bottom_row_active_cols)):
                raise ValueError("framed grid overrides are forbidden; every clipped ceiling cell is required")
            if args.no_default_masks or args.mask:
                raise ValueError("framed stage accepts only observed minimap and fixed command masks")
            geometry = framed_coverage_geometry(args.stage, args.logical_width, args.logical_height,
                        minimap_enabled=bool(args.minimap_enabled), minimap_width=args.minimap_width,
                        minimap_height=args.minimap_height)
            args.framed_geometry = geometry
            args.columns, args.rows = geometry["columns"], geometry["rows"]
            args.bottom_row_active_cols = args.columns
        else:
            if any(v is not None for v in (args.minimap_enabled, args.minimap_width, args.minimap_height)):
                raise ValueError("minimap observation options require the exact framed stage")
            args.columns = 12 if args.columns is None else args.columns
            args.rows = 9 if args.rows is None else args.rows
            args.bottom_row_active_cols = 12 if args.bottom_row_active_cols is None else args.bottom_row_active_cols
    except ValueError as exc:
        parser.error(str(exc))
    return args


def main() -> int:
    args = parse_args()
    if args.framed_geometry is not None:
        masks = args.framed_geometry["masks"]
        cells = args.framed_geometry["cells"]
    else:
        masks = [] if args.no_default_masks else list(default_masks(args.logical_width).items())
        masks.extend(args.mask)
        cells = build_cells(args.origin_x, args.origin_y, args.tile_size, args.columns,
                            args.rows, args.bottom_row_active_cols)
    report = {
        "parameters": {
            "logical_width": args.logical_width,
            "logical_height": args.logical_height,
            "origin_x": args.origin_x,
            "origin_y": args.origin_y,
            "tile_size": args.tile_size,
            "columns": args.columns,
            "rows": args.rows,
            "bottom_row_active_cols": args.bottom_row_active_cols,
            "threshold": args.threshold,
            "black_percent": args.black_percent,
            "min_gameplay_border_percent": args.min_gameplay_border_percent,
            "min_gameplay_overall_percent": args.min_gameplay_overall_percent,
            "low_detail_bins": args.low_detail_bins,
            "min_unmasked_percent": args.min_unmasked_percent,
        },
        "masks": [{"name": name, "logical_rect": list(rect)} for name, rect in masks],
        "images": [analyze_image(path, cells, masks, args) for path in args.png],
    }
    if args.framed_geometry is not None:
        report["framed_profile"] = {k: v for k, v in args.framed_geometry.items() if k not in ("cells", "masks")}
    if args.write_json:
        args.write_json.parent.mkdir(parents=True, exist_ok=True)
        args.write_json.write_text(json.dumps(report, indent=2), encoding="ascii")
    print_summary(report)
    if args.require_gameplay and any(
        not image["frame_check"]["gameplay_frame_likely"] for image in report["images"]
    ):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
