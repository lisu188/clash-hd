#!/usr/bin/env python3
"""Summarize natural battle command availability from CDB force-unit rows.

This is a repo-only/static helper: it parses existing ``BATTLE_FORCE_UNIT``
rows from a CDB log and reads the command availability bytes from a local
Clash95 executable. It does not launch Clash95, CDB, wrappers, PowerShell, or a
visible window.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from patch_stage_report import parse_pe_sections


DEFAULT_CAPTURE = Path("captures/archive/cdb-surface-dump-20260520-195244")
DEFAULT_EXE = Path(r"C:\Clash\clash95.exe")
DEFAULT_JSON = Path("captures/current/battle-command-availability-current.json")
DEFAULT_MD = Path("captures/current/battle-command-availability-current.md")

AVAILABILITY_BASE_VA = 0x0051257E
ENABLED_BASE_VA = 0x00512582
UNIT_RECORD_BASE_VA = AVAILABILITY_BASE_VA - 0x1E
UNIT_TYPE_STRIDE = 88
NAME_TABLE_OFFSET = 0x08
ASSET_KEY_OFFSET = 0x0C

UNIT_RE = re.compile(
    r"BATTLE_FORCE_UNIT\s+idx=(?P<idx>\d+)\s+ptr=(?P<ptr>[0-9a-fA-F]+)\s+"
    r"owner=(?P<owner>\d+)\s+xy=\((?P<x>\d+),(?P<y>\d+)\)\s+"
    r"first=(?P<unit_type>\d+)\s+status720=(?P<status720>\d+)"
)


def capture_log_path(path: Path) -> Path:
    if path.is_dir():
        return path / "cdb-surface-dump.log"
    return path


def parse_units(text: str) -> list[dict[str, Any]]:
    units: list[dict[str, Any]] = []
    for match in UNIT_RE.finditer(text):
        units.append(
            {
                "idx": int(match.group("idx")),
                "ptr": int(match.group("ptr"), 16),
                "owner": int(match.group("owner")),
                "x": int(match.group("x")),
                "y": int(match.group("y")),
                "unit_type": int(match.group("unit_type")),
                "status720": int(match.group("status720")),
            }
        )
    return units


def va_to_raw(va: int, image_base: int, sections: list[dict[str, Any]]) -> int:
    rva = va - image_base
    for section in sections:
        start = int(section["virtual_address"])
        size = int(section["raw_size"])
        if start <= rva < start + size:
            return int(section["raw_pointer"]) + (rva - start)
    raise ValueError(f"VA 0x{va:08X} is outside raw PE sections")


def read_c_string(data: bytes, image_base: int, sections: list[dict[str, Any]], va: int) -> str | None:
    if not va:
        return None
    try:
        raw = va_to_raw(va, image_base, sections)
    except ValueError:
        return None
    end = data.find(b"\x00", raw, min(len(data), raw + 128))
    if end < 0:
        return None
    text = data[raw:end]
    if not text:
        return None
    return text.decode("cp1250", errors="replace")


def unit_metadata(data: bytes, image_base: int, sections: list[dict[str, Any]], unit_type: int) -> dict[str, Any]:
    record_va = UNIT_RECORD_BASE_VA + (unit_type * UNIT_TYPE_STRIDE)
    record_raw = va_to_raw(record_va, image_base, sections)
    name_table_va = int.from_bytes(data[record_raw + NAME_TABLE_OFFSET : record_raw + NAME_TABLE_OFFSET + 4], "little")
    asset_key_va = int.from_bytes(data[record_raw + ASSET_KEY_OFFSET : record_raw + ASSET_KEY_OFFSET + 4], "little")
    names = [None, None, None]
    try:
        name_table_raw = va_to_raw(name_table_va, image_base, sections)
        name_ptrs = [
            int.from_bytes(data[name_table_raw + index * 4 : name_table_raw + index * 4 + 4], "little")
            for index in range(3)
        ]
        names = [read_c_string(data, image_base, sections, ptr) for ptr in name_ptrs]
    except ValueError:
        name_ptrs = [None, None, None]
    return {
        "record_va": f"0x{record_va:08X}",
        "name_table_va": f"0x{name_table_va:08X}" if name_table_va else None,
        "name_pl": names[0],
        "name_en": names[1],
        "name_de": names[2],
        "name_pointer_vas": [f"0x{ptr:08X}" if ptr else None for ptr in name_ptrs],
        "asset_key": read_c_string(data, image_base, sections, asset_key_va),
        "asset_key_va": f"0x{asset_key_va:08X}" if asset_key_va else None,
    }


def availability_for_type(data: bytes, image_base: int, sections: list[dict[str, Any]], unit_type: int) -> dict[str, Any]:
    avail_va = AVAILABILITY_BASE_VA + (unit_type * UNIT_TYPE_STRIDE)
    enabled_va = ENABLED_BASE_VA + (unit_type * UNIT_TYPE_STRIDE)
    avail_raw = va_to_raw(avail_va, image_base, sections)
    enabled_raw = va_to_raw(enabled_va, image_base, sections)
    return {
        "unit_type": unit_type,
        "availability": data[avail_raw],
        "enabled": data[enabled_raw],
        "availability_va": f"0x{avail_va:08X}",
        "enabled_va": f"0x{enabled_va:08X}",
        "availability_raw": f"0x{avail_raw:08X}",
        "enabled_raw": f"0x{enabled_raw:08X}",
        **unit_metadata(data, image_base, sections, unit_type),
    }


def scan_availability_table(
    data: bytes, image_base: int, sections: list[dict[str, Any]], max_unit_type: int
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for unit_type in range(max_unit_type + 1):
        try:
            rows.append(availability_for_type(data, image_base, sections, unit_type))
        except (IndexError, ValueError):
            break
    return rows


def build_summary(capture_or_log: Path, exe: Path, *, max_unit_type: int = 63) -> dict[str, Any]:
    log_path = capture_log_path(capture_or_log)
    text = log_path.read_text(encoding="utf-8", errors="replace")
    units = parse_units(text)
    data = exe.read_bytes()
    image_base, sections = parse_pe_sections(data)
    if image_base is None:
        raise ValueError(f"could not read image base from {exe}")

    by_type: dict[int, dict[str, Any]] = {}
    for unit_type in sorted({unit["unit_type"] for unit in units}):
        by_type[unit_type] = availability_for_type(data, image_base, sections, unit_type)

    enriched_units = []
    for unit in units:
        info = by_type[unit["unit_type"]]
        enriched = dict(unit)
        enriched["availability"] = info["availability"]
        enriched["enabled"] = info["enabled"]
        enriched["name_en"] = info.get("name_en")
        enriched["asset_key"] = info.get("asset_key")
        enriched_units.append(enriched)

    selected_unit = next((unit for unit in enriched_units if unit["idx"] == 0), None)
    naturally_enabled_units = [unit for unit in enriched_units if int(unit["enabled"]) > 0]
    table_scan = scan_availability_table(data, image_base, sections, max_unit_type)
    enabled_table_types = [row for row in table_scan if int(row["enabled"]) > 0]

    return {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "runtime_policy": "repo-only parser; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows",
        "input": str(capture_or_log),
        "log": str(log_path),
        "exe": str(exe),
        "unit_count": len(enriched_units),
        "unit_types": list(by_type.values()),
        "units": enriched_units,
        "selected_unit": selected_unit,
        "selected_unit_naturally_disabled": bool(
            selected_unit and selected_unit.get("unit_type") == 5 and selected_unit.get("availability") == 8 and selected_unit.get("enabled") == 0
        ),
        "naturally_enabled_unit_count": len(naturally_enabled_units),
        "naturally_enabled_units": naturally_enabled_units,
        "table_scan_max_unit_type": max_unit_type,
        "enabled_table_type_count": len(enabled_table_types),
        "enabled_table_types": enabled_table_types,
    }


def write_markdown(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# Battle Command Availability",
        "",
        f"- Generated: `{summary['generated_at']}`",
        f"- Runtime policy: {summary['runtime_policy']}",
        f"- Log: `{summary['log']}`",
        f"- Executable: `{summary['exe']}`",
        f"- Unit count: `{summary['unit_count']}`",
        f"- Selected unit naturally disabled: `{summary['selected_unit_naturally_disabled']}`",
        f"- Naturally enabled unit count: `{summary['naturally_enabled_unit_count']}`",
        f"- Enabled table type count: `{summary['enabled_table_type_count']}`",
        "",
        "## Unit Types",
        "",
        "| Type | Name | Asset | Availability | Enabled | Availability VA | Enabled VA |",
        "| --- | --- | --- | ---: | ---: | --- | --- |",
    ]
    for item in summary["unit_types"]:
        lines.append(
            f"| {item['unit_type']} | {item.get('name_en') or ''} | {item.get('asset_key') or ''} | "
            f"{item['availability']} | {item['enabled']} | "
            f"`{item['availability_va']}` | `{item['enabled_va']}` |"
        )
    lines.extend(
        [
            "",
            "## Units",
            "",
            "| Index | Owner | XY | Type | Name | Availability | Enabled |",
            "| ---: | ---: | --- | ---: | --- | ---: | ---: |",
        ]
    )
    for unit in summary["units"]:
        info = next((item for item in summary["unit_types"] if item["unit_type"] == unit["unit_type"]), {})
        lines.append(
            f"| {unit['idx']} | {unit['owner']} | ({unit['x']},{unit['y']}) | "
            f"{unit['unit_type']} | {info.get('name_en') or ''} | {unit['availability']} | {unit['enabled']} |"
        )
    lines.extend(
        ["", "## Enabled Table Types", "", "| Type | Name | Asset | Availability | Enabled |", "| ---: | --- | --- | ---: | ---: |"]
    )
    for item in summary["enabled_table_types"]:
        lines.append(
            f"| {item['unit_type']} | {item.get('name_en') or ''} | {item.get('asset_key') or ''} | "
            f"{item['availability']} | {item['enabled']} |"
        )
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture_or_log", type=Path, nargs="?", default=DEFAULT_CAPTURE)
    parser.add_argument("--exe", type=Path, default=DEFAULT_EXE)
    parser.add_argument("--max-unit-type", type=int, default=31)
    parser.add_argument("--write-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--write-markdown", "--write-md", dest="write_markdown", type=Path, default=DEFAULT_MD)
    parser.add_argument("--require-selected-disabled", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary = build_summary(args.capture_or_log, args.exe, max_unit_type=args.max_unit_type)
    print(f"unit-count: {summary['unit_count']}")
    print(f"selected-unit-naturally-disabled: {summary['selected_unit_naturally_disabled']}")
    print(f"naturally-enabled-unit-count: {summary['naturally_enabled_unit_count']}")
    print(f"enabled-table-type-count: {summary['enabled_table_type_count']}")
    if args.write_json:
        args.write_json.parent.mkdir(parents=True, exist_ok=True)
        args.write_json.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    if args.write_markdown:
        write_markdown(args.write_markdown, summary)
    if args.require_selected_disabled and not summary["selected_unit_naturally_disabled"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
