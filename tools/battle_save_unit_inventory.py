#!/usr/bin/env python3
r"""Inventory battle unit records directly from local Clash95 save files.

This is a read-only evidence helper. It reads ``C:\Clash\save\N.dat`` files
and the original executable's command availability table, then reports whether
any save slot contains a unit type whose battle command table is naturally
enabled. It does not write saves and does not launch Clash95, CDB, wrappers,
PowerShell, or any visible process.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import battle_command_availability as availability
from patch_stage_report import parse_pe_sections


DEFAULT_SAVE_DIR = Path(r"C:\Clash\save")
DEFAULT_EXE = Path(r"C:\Clash\clash95.exe")
DEFAULT_JSON = Path("captures/current/battle-save-unit-inventory-current.json")
DEFAULT_MD = Path("captures/current/battle-save-unit-inventory-current.md")

MEMORY_UNIT_BASE_OFFSET = 147174
SAVE_UNIT_BASE_OFFSET = 147190
SAVE_MEMORY_DELTA = SAVE_UNIT_BASE_OFFSET - MEMORY_UNIT_BASE_OFFSET
UNIT_RECORD_STRIDE = 725
MAX_UNIT_RECORDS = 500
TYPE_OFFSET = 6
STATUS_OFFSET = 720

SLOT_FILE_RE = re.compile(r"^(?P<slot>\d+)\.dat$", re.IGNORECASE)


def parse_save_units(data: bytes, *, base_offset: int = SAVE_UNIT_BASE_OFFSET) -> list[dict[str, Any]]:
    units: list[dict[str, Any]] = []
    for idx in range(MAX_UNIT_RECORDS):
        offset = base_offset + (idx * UNIT_RECORD_STRIDE)
        if offset + STATUS_OFFSET >= len(data):
            break
        x = int.from_bytes(data[offset : offset + 2], "little")
        y = int.from_bytes(data[offset + 2 : offset + 4], "little")
        owner = data[offset + 4]
        unit_type = int.from_bytes(data[offset + TYPE_OFFSET : offset + TYPE_OFFSET + 2], "little")
        status720 = data[offset + STATUS_OFFSET]
        if x < 100 and y < 100 and owner < 4 and unit_type <= 40:
            units.append(
                {
                    "idx": idx,
                    "save_offset": f"0x{offset:08X}",
                    "owner": owner,
                    "x": x,
                    "y": y,
                    "unit_type": unit_type,
                    "status720": status720,
                }
            )
    return units


def iter_save_files(save_dir: Path) -> list[tuple[int, Path]]:
    rows: list[tuple[int, Path]] = []
    for path in save_dir.iterdir():
        match = SLOT_FILE_RE.match(path.name)
        if match and path.is_file():
            rows.append((int(match.group("slot")), path))
    return sorted(rows)


def availability_map(exe: Path, unit_types: set[int]) -> dict[int, dict[str, Any]]:
    data = exe.read_bytes()
    image_base, sections = parse_pe_sections(data)
    if image_base is None:
        raise ValueError(f"could not read image base from {exe}")
    return {
        unit_type: availability.availability_for_type(data, image_base, sections, unit_type)
        for unit_type in sorted(unit_types)
    }


def build_summary(save_dir: Path, exe: Path) -> dict[str, Any]:
    slot_rows: list[dict[str, Any]] = []
    all_types: set[int] = set()
    for slot, path in iter_save_files(save_dir):
        units = parse_save_units(path.read_bytes())
        all_types.update(unit["unit_type"] for unit in units)
        slot_rows.append(
            {
                "slot": slot,
                "path": str(path),
                "unit_count": len(units),
                "unit_types": sorted({unit["unit_type"] for unit in units}),
                "units": units,
            }
        )

    by_type = availability_map(exe, all_types)
    natural_enabled_units: list[dict[str, Any]] = []
    for row in slot_rows:
        for unit in row["units"]:
            info = by_type[unit["unit_type"]]
            unit["availability"] = info["availability"]
            unit["enabled"] = info["enabled"]
            if int(unit["enabled"]) > 0:
                enabled_unit = dict(unit)
                enabled_unit["slot"] = row["slot"]
                natural_enabled_units.append(enabled_unit)

    return {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "runtime_policy": "read-only save/exe parser; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows",
        "save_dir": str(save_dir),
        "exe": str(exe),
        "memory_unit_base_offset": MEMORY_UNIT_BASE_OFFSET,
        "save_unit_base_offset": SAVE_UNIT_BASE_OFFSET,
        "save_memory_delta": SAVE_MEMORY_DELTA,
        "unit_record_stride": UNIT_RECORD_STRIDE,
        "slot_count": len(slot_rows),
        "total_unit_count": sum(int(row["unit_count"]) for row in slot_rows),
        "natural_enabled_unit_count": len(natural_enabled_units),
        "natural_enabled_units": natural_enabled_units,
        "unit_types": list(by_type.values()),
        "slots": slot_rows,
    }


def write_markdown(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# Battle Save Unit Inventory",
        "",
        f"- Generated: `{summary['generated_at']}`",
        f"- Runtime policy: {summary['runtime_policy']}",
        f"- Save dir: `{summary['save_dir']}`",
        f"- Executable: `{summary['exe']}`",
        f"- Save unit base offset: `0x{summary['save_unit_base_offset']:08X}`",
        f"- Memory unit base offset: `0x{summary['memory_unit_base_offset']:08X}`",
        f"- Save/memory delta: `{summary['save_memory_delta']}` bytes",
        f"- Unit record stride: `{summary['unit_record_stride']}`",
        f"- Slots: `{summary['slot_count']}`",
        f"- Total parsed units: `{summary['total_unit_count']}`",
        f"- Natural enabled unit count: `{summary['natural_enabled_unit_count']}`",
        "",
        "## Slots",
        "",
        "| Slot | Units | Types | Natural Enabled |",
        "| ---: | ---: | --- | ---: |",
    ]
    by_type = {row["unit_type"]: row for row in summary["unit_types"]}
    for slot in summary["slots"]:
        enabled = sum(1 for unit in slot["units"] if int(unit.get("enabled") or 0) > 0)
        type_labels = []
        for unit_type in slot["unit_types"]:
            info = by_type.get(unit_type, {})
            name = info.get("name_en") or "unknown"
            type_labels.append(f"{unit_type} {name}")
        types = ", ".join(type_labels) or "none"
        lines.append(f"| {slot['slot']} | {slot['unit_count']} | {types} | {enabled} |")

    lines.extend(
        [
            "",
            "## Unit Types",
            "",
            "| Type | Name | Asset | Availability | Enabled |",
            "| ---: | --- | --- | ---: | ---: |",
        ]
    )
    for row in summary["unit_types"]:
        lines.append(
            f"| {row['unit_type']} | {row.get('name_en') or ''} | {row.get('asset_key') or ''} | "
            f"{row['availability']} | {row['enabled']} |"
        )
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--save-dir", type=Path, default=DEFAULT_SAVE_DIR)
    parser.add_argument("--exe", type=Path, default=DEFAULT_EXE)
    parser.add_argument("--write-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--write-markdown", "--write-md", dest="write_markdown", type=Path, default=DEFAULT_MD)
    parser.add_argument("--require-no-natural-enabled", action="store_true")
    parser.add_argument("--require-min-slots", type=int, default=0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary = build_summary(args.save_dir, args.exe)
    print(f"slots: {summary['slot_count']}")
    print(f"total-unit-count: {summary['total_unit_count']}")
    print(f"natural-enabled-unit-count: {summary['natural_enabled_unit_count']}")
    if args.write_json:
        args.write_json.parent.mkdir(parents=True, exist_ok=True)
        args.write_json.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    if args.write_markdown:
        write_markdown(args.write_markdown, summary)
    if args.require_no_natural_enabled and summary["natural_enabled_unit_count"]:
        return 2
    if args.require_min_slots and summary["slot_count"] < args.require_min_slots:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
