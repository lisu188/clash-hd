#!/usr/bin/env python3
"""Compare all six action-bar cells in existing indexed software captures.

This is a source-pixel diagnostic, not visible composition or input proof.
Only complete opaque source variants count as a matching cell. Row matches
explain partial overwrites without relaxing the whole-cell comparison.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import struct
import sys
import zlib

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.patcher.framed_viewport import FramedViewport
from src.patcher.complete_hd_candidate import STAGE as COMPLETE_HD_STAGE

from cdb_surface_dump_to_png import PNG_SIGNATURE, indices_to_rgb_rows, load_palette, png_chunk

from hd_layout_asset_composition import (
    RESOURCE_SHA256, Sprite, decode_sprite, resource_member,
)

FRAMED_STAGE = (
    "gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-"
    "presentbounds-minimapright-dynvswitch-combinedui-partialtiles-initialpaint-framed-validation"
)


def framed_stage(stage: str | None) -> bool:
    """Select only the exact producer stage; never guess a similar suffix."""
    if stage is not None and not isinstance(stage, str):
        raise ValueError("stage must be a string")
    if stage in (FRAMED_STAGE, COMPLETE_HD_STAGE):
        return True
    if stage is not None and any(name in stage.lower() for name in ("framed", "completehd")):
        raise ValueError("unsupported framed stage identity")
    return False


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_sprites(resource: bytes) -> tuple[dict[int, Sprite], str]:
    if digest(resource) != RESOURCE_SHA256:
        raise ValueError("unsupported source resource SHA-256")
    member = resource_member(resource, "MAP_BUTT.S32")
    sprites = {index: decode_sprite(member, index) for index in range(15)}
    if any((s.width, s.height) != (64, 32) for s in sprites.values()):
        raise ValueError("unexpected action-bar sprite dimensions")
    if any(None in sprites[index].pixels for index in range(12)):
        raise ValueError("base action-bar cells must be opaque")
    return sprites, digest(member)


def compare_cells(raw: bytes, width: int, height: int, sprites: dict[int, Sprite],
                  *, legacy: bool = False, stage: str | None = None) -> list[dict]:
    if (type(width) is not int or type(height) is not int
            or width < 640 or height < 480 or len(raw) != width * height):
        raise ValueError("invalid tightly packed indexed surface")
    for index in (*range(12), 14):
        sprite = sprites.get(index)
        if (not isinstance(sprite, Sprite) or (sprite.width, sprite.height) != (64, 32)
                or len(sprite.pixels) != 2048
                or any(not (type(p) is int and 0 <= p <= 255) and not (index == 14 and p is None)
                       for p in sprite.pixels)):
            raise ValueError("malformed action-bar sprite")
    is_framed = framed_stage(stage)
    if is_framed and legacy:
        raise ValueError("framed stage cannot select the native legacy anchor")
    if is_framed:
        layout = FramedViewport(width, height)
        left, top = layout.action_bar.left, layout.action_bar.top
    else:
        left, top = (416, 400) if legacy else (width - 192, height - 72)
    cells = []
    for cell in range(6):
        x, y = left + cell % 3 * 64, top + cell // 3 * 32
        actual = b"".join(raw[(y + row) * width + x:(y + row) * width + x + 64]
                          for row in range(32))
        variants = []
        for index in (cell * 2, cell * 2 + 1):
            base = sprites[index].pixels
            for hovered in (False, True):
                expected = bytes((overlay if hovered and overlay is not None else pixel)
                                 for pixel, overlay in zip(base, sprites[14].pixels))
                mismatches = sum(a != b for a, b in zip(actual, expected))
                rows = [row for row in range(32)
                        if actual[row * 64:(row + 1) * 64]
                        == expected[row * 64:(row + 1) * 64]]
                variants.append({"sprite": index, "hover_overlay": hovered,
                                 "mismatched_pixels": mismatches,
                                 "exact_rows": rows})
        best = min(variants, key=lambda item: item["mismatched_pixels"])
        cells.append({"cell": cell, "anchor": [x, y], "size": [64, 32],
                      "exact_source_match": best["mismatched_pixels"] == 0,
                      "closest_source_variant": best,
                      "matching_variants": [v for v in variants if v["mismatched_pixels"] == 0]})
    return cells


def bind_screenshot(summary: dict, raw: bytes, raw_path: Path, png_path: Path,
                    width: int, height: int) -> dict:
    metadata_path = Path(summary["PngMetadata"])
    if metadata_path.parent.resolve() != png_path.parent.resolve():
        raise ValueError("PNG metadata is outside the capture directory")
    metadata_data = metadata_path.read_bytes()
    metadata = json.loads(metadata_data.decode("utf-8-sig"))
    png = png_path.read_bytes()
    if (Path(metadata["raw_path"]).resolve() != raw_path.resolve()
            or Path(metadata["png_path"]).resolve() != png_path.resolve()
            or metadata["width"] != width or metadata["height"] != height
            or metadata["pitch"] != width
            or metadata["raw_bytes"] != len(raw) or metadata["used_bytes"] != len(raw)
            or metadata["raw_sha256"] != digest(raw) or metadata["used_sha256"] != digest(raw)
            or metadata["png_sha256"] != digest(png)
            or summary["PngSha256"].lower() != digest(png)):
        raise ValueError("PNG/metadata/raw identity mismatch")
    palette_path = Path(metadata["palette_path"]) if metadata.get("palette_path") else None
    palette, mode = load_palette(palette_path)
    if mode != metadata["palette_mode"]:
        raise ValueError("palette mode mismatch")
    # Require the known converter's exact serialization, not merely a filename
    # or a self-reported PNG hash. Reconstruction is in memory; no image edit.
    expected = (PNG_SIGNATURE
                + png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
                + png_chunk(b"IDAT", zlib.compress(indices_to_rgb_rows(raw, width, height, width, palette), 9))
                + png_chunk(b"IEND", b""))
    if png != expected:
        raise ValueError("PNG does not encode the recorded indexed raw surface and palette")
    candidate = Path(summary["CandidatePath"])
    if digest(candidate.read_bytes()) != summary["CandidateSha256"].lower():
        raise ValueError("candidate file SHA differs from summary")
    return {"metadata_path": str(metadata_path), "metadata_sha256": digest(metadata_data),
            "palette_path": str(palette_path) if palette_path else None,
            "palette_sha256": digest(palette_path.read_bytes()) if palette_path else None,
            "png_raw_palette_binding_verified": True, "candidate_file_sha_verified": True}


def audit_summary(path: Path, sprites: dict[int, Sprite]) -> dict:
    data = path.read_bytes()
    summary = json.loads(data.decode("utf-8-sig"))
    raw_path, png_path = Path(summary["RawPath"]), Path(summary["PngPath"])
    surface = summary["Surface"]
    width, height = surface["Width"], surface["Height"]
    if summary["Resolution"] != f"{width}x{height}":
        raise ValueError("summary resolution differs from surface")
    if raw_path.parent.resolve() != path.parent.resolve() or png_path.parent.resolve() != path.parent.resolve():
        raise ValueError("capture paths do not belong to the summary directory")
    raw = raw_path.read_bytes()
    if len(raw) != summary["RawBytes"] or len(raw) != surface["Bytes"]:
        raise ValueError("raw size differs from summary")
    binding = bind_screenshot(summary, raw, raw_path, png_path, width, height)
    cells = compare_cells(raw, width, height, sprites, stage=summary["Stage"])
    legacy = compare_cells(raw, width, height, sprites, legacy=True)
    return {"run_id": path.parent.name, "resolution": summary["Resolution"],
            "stage": summary["Stage"], "candidate_sha256": summary["CandidateSha256"],
            "summary": {"path": str(path), "sha256": digest(data)},
            "raw_surface": {"path": str(raw_path), "sha256": digest(raw)},
            "screenshot": {"path": str(png_path), "sha256": digest(png_path.read_bytes())},
            "artifact_binding": binding,
            "surface_gate_passed": summary["Passed"],
            "all_six_cells_match_source": all(c["exact_source_match"] for c in cells),
            "cells": cells,
            "legacy_matching_cells": [c["cell"] for c in legacy if c["exact_source_match"]],
            "visible_composition_proof": False, "manual_input_proof": False,
            "limits": "Exact indexed pixels only. Closest variants and matching rows are diagnostics, not passes. Unknown cursor overlays can cause mismatch; missing/partial cells require further composition investigation."}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--resource", type=Path, required=True)
    parser.add_argument("--summary", type=Path, action="append", required=True)
    parser.add_argument("--json-out", type=Path, required=True)
    args = parser.parse_args()
    sprites, member_sha = load_sprites(args.resource.read_bytes())
    rows = []
    for path in dict.fromkeys(args.summary):
        try:
            rows.append(audit_summary(path, sprites))
        except (OSError, ValueError, KeyError, TypeError) as exc:
            rows.append({"summary_path": str(path), "all_six_cells_match_source": False,
                         "error": str(exc)})
    result = {"schema": "clash95_action_bar_surface_audit_v1",
              "generated_at": datetime.now(timezone.utc).isoformat(),
              "resource_sha256": RESOURCE_SHA256, "member_sha256": member_sha,
              "passed": all(row["all_six_cells_match_source"] for row in rows),
              "scope": "Existing supplied hidden software surfaces; no runtime or image modification",
              "screenshots": rows}
    args.json_out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"passed": result["passed"], "screenshots": [
        {"run": r.get("run_id"), "resolution": r.get("resolution"),
         "matching_cells": sum(c["exact_source_match"] for c in r.get("cells", [])),
         "error": r.get("error")} for r in rows]}, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
