#!/usr/bin/env python3
r"""Plan or create an isolated save with a right-bottom action-eligible building.

Disassembly ground truth (`reports/hd_completion_certainty.md`, Gate 1): the
right-bottom production/action panel renders only while
``addon_flags & 0x02`` is set at ``building_record + 416`` (clash95.c:49999),
the bit is written only by ``Building_New(1, ...)`` (clash95.c:34186), and save
load is a verbatim binary image restore (clash95.c:61809). Building records
live at save file offset ``0x10 + 509674`` (16-byte header + gameData offset),
stride 467, 100 records (`docs/SAVE_DAT_FORMAT.md` row 509674). Setting bit
``0x02`` at ``0x10 + 509674 + i*467 + 0x1A0`` in a *copied* save therefore makes
building ``i`` action-eligible on the natural route without any binary patch.

This helper never edits ``C:\Clash\save``. By default it performs a dry run:
it reads one source save, selects (or accepts) a plausible player-owned
building record, reports the single byte that would change, and writes only
JSON/Markdown evidence. If ``--output-save`` is supplied, it writes a copied
save to that path and refuses to write inside the repository unless
``--allow-repo-output`` is passed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import castle_save_owner_flag_scan as owner_scan


DEFAULT_SOURCE_SAVE = Path(r"C:\Clash\save\0.dat")
DEFAULT_JSON = Path("captures/current/right-bottom-constructed-save-fixture-current.json")
DEFAULT_MD = Path("captures/current/right-bottom-constructed-save-fixture-current.md")

# File offset of building record 0: 16-byte save header + gameData offset
# 509674 (clash95.c:61809 bulk restore; docs/SAVE_DAT_FORMAT.md row 509674).
BUILDING_BLOCK_FILE_OFFSET = owner_scan.DEFAULT_KNOWN_OFFSET
BUILDING_RECORD_STRIDE = owner_scan.RECORD_SIZE
BUILDING_RECORD_COUNT = 100
ADDON_FLAGS_OFFSET = 0x1A0
ACTION_ELIGIBLE_BIT = 0x02

RUNTIME_POLICY = (
    "save fixture planner; reads one source save; never edits C:\\Clash\\save; "
    "writes copied save only when --output-save is supplied; does not launch "
    "Clash95, CDB, wrappers, PowerShell, or visible windows"
)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def path_is_under(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def building_record_offset(building_index: int, *, base_offset: int = BUILDING_BLOCK_FILE_OFFSET) -> int:
    return base_offset + building_index * BUILDING_RECORD_STRIDE


def addon_flags_file_offset(building_index: int, *, base_offset: int = BUILDING_BLOCK_FILE_OFFSET) -> int:
    return building_record_offset(building_index, base_offset=base_offset) + ADDON_FLAGS_OFFSET


def parse_buildings(
    data: bytes,
    *,
    base_offset: int = BUILDING_BLOCK_FILE_OFFSET,
    record_count: int = BUILDING_RECORD_COUNT,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index in range(record_count):
        start = building_record_offset(index, base_offset=base_offset)
        record = data[start : start + BUILDING_RECORD_STRIDE]
        if len(record) < BUILDING_RECORD_STRIDE:
            break
        if owner_scan.active_record(record):
            rows.append(owner_scan.record_metadata(Path("<memory>"), base_offset, index, record))
    return rows


def select_building_index(
    buildings: list[dict[str, Any]],
    *,
    player_index: int,
) -> int | None:
    for row in buildings:
        if not owner_scan.plausible_active_record(row):
            continue
        if int(row["owner"]) != player_index:
            continue
        if int(row["flags_1a0"]) & ACTION_ELIGIBLE_BIT:
            continue
        return int(row["record_index"])
    return None


def patch_addon_flags(
    data: bytes,
    *,
    building_index: int,
    set_bits: int = ACTION_ELIGIBLE_BIT,
    base_offset: int = BUILDING_BLOCK_FILE_OFFSET,
) -> bytes:
    if building_index < 0 or building_index >= BUILDING_RECORD_COUNT:
        raise ValueError(f"building index {building_index} outside record table 0..{BUILDING_RECORD_COUNT - 1}")
    offset = addon_flags_file_offset(building_index, base_offset=base_offset)
    if offset >= len(data):
        raise ValueError(f"building index {building_index} addon_flags offset 0x{offset:08X} is outside save data")
    patched = bytearray(data)
    patched[offset] |= set_bits
    return bytes(patched)


def build_summary(
    source_save: Path,
    *,
    building_index: int | None,
    player_index: int,
    output_save: Path | None = None,
    allow_repo_output: bool = False,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    source_data = source_save.read_bytes()
    buildings = parse_buildings(source_data)
    selection_mode = "explicit"
    if building_index is None:
        selection_mode = "auto"
        building_index = select_building_index(buildings, player_index=player_index)
        if building_index is None:
            raise ValueError(
                f"no plausible player-{player_index}-owned building without bit 0x02 found in {source_save}"
            )
    selected = next((row for row in buildings if int(row["record_index"]) == building_index), None)
    if selected is None:
        raise ValueError(f"building index {building_index} is not an active record in {source_save}")

    old_flags = int(selected["flags_1a0"])
    patched_data = patch_addon_flags(source_data, building_index=building_index)
    patched_buildings = parse_buildings(patched_data)
    patched_selected = next(
        (row for row in patched_buildings if int(row["record_index"]) == building_index), None
    )
    if patched_selected is None or not (int(patched_selected["flags_1a0"]) & ACTION_ELIGIBLE_BIT):
        raise ValueError("patched save did not reparse with addon_flags bit 0x02 set")

    wrote_output = False
    output_path_text = None
    if output_save is not None:
        repo_root = repo_root or Path.cwd()
        if path_is_under(output_save, repo_root) and not allow_repo_output:
            raise ValueError(f"refusing to write copied save inside repository: {output_save}")
        if output_save.resolve() == source_save.resolve():
            raise ValueError(f"refusing to overwrite source save: {source_save}")
        output_save.parent.mkdir(parents=True, exist_ok=True)
        output_save.write_bytes(patched_data)
        wrote_output = True
        output_path_text = str(output_save)

    flags_offset = addon_flags_file_offset(building_index)
    return {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "runtime_policy": RUNTIME_POLICY,
        "source_save": str(source_save),
        "output_save": output_path_text,
        "dry_run": not wrote_output,
        "source_sha256": sha256_bytes(source_data),
        "patched_sha256": sha256_bytes(patched_data),
        "building_index": building_index,
        "selection_mode": selection_mode,
        "player_index": player_index,
        "building_record_offset": f"0x{building_record_offset(building_index):08X}",
        "addon_flags_file_offset": f"0x{flags_offset:08X}",
        "old_addon_flags": f"0x{old_flags:02X}",
        "new_addon_flags": f"0x{int(patched_selected['flags_1a0']):02X}",
        "set_bit": f"0x{ACTION_ELIGIBLE_BIT:02X}",
        "building_x": int(selected["x"]),
        "building_y": int(selected["y"]),
        "building_owner": int(selected["owner"]),
        "action_eligible_after": bool(int(patched_selected["flags_1a0"]) & ACTION_ELIGIBLE_BIT),
        "active_building_count": len(buildings),
        "wrote_output": wrote_output,
        "disassembly_citations": [
            "clash95.c:49999 addon_flags & 0x02 render gate",
            "clash95.c:34186 Building_New(1,...) sets bit 0x02",
            "clash95.c:61809 SaveSlot_LoadGame verbatim bulk restore",
            "docs/SAVE_DAT_FORMAT.md row 509674 building records, stride 467",
        ],
    }


def write_markdown(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# Right-Bottom Constructed Save Fixture",
        "",
        f"- Generated: `{summary['generated_at']}`",
        f"- Runtime policy: {summary['runtime_policy']}",
        f"- Source save: `{summary['source_save']}`",
        f"- Output save: `{summary['output_save']}`",
        f"- Dry run: `{summary['dry_run']}`",
        f"- Wrote output: `{summary['wrote_output']}`",
        f"- Source SHA-256: `{summary['source_sha256']}`",
        f"- Patched SHA-256: `{summary['patched_sha256']}`",
        f"- Selection mode: `{summary['selection_mode']}` (player index {summary['player_index']})",
        "",
        "## Planned Change",
        "",
        "| Building index | (x,y) | Owner | addon_flags offset | Old flags | New flags | Action eligible |",
        "| ---: | --- | ---: | --- | --- | --- | --- |",
        (
            f"| {summary['building_index']} | ({summary['building_x']},{summary['building_y']}) | "
            f"{summary['building_owner']} | `{summary['addon_flags_file_offset']}` | "
            f"`{summary['old_addon_flags']}` | `{summary['new_addon_flags']}` | "
            f"{summary['action_eligible_after']} |"
        ),
        "",
        "## Disassembly Citations",
        "",
    ]
    lines.extend(f"- {citation}" for citation in summary["disassembly_citations"])
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-save", type=Path, default=DEFAULT_SOURCE_SAVE)
    parser.add_argument("--building-index", type=int, default=None)
    parser.add_argument("--player-index", type=int, default=0)
    parser.add_argument("--output-save", type=Path)
    parser.add_argument("--allow-repo-output", action="store_true")
    parser.add_argument("--write-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--write-markdown", "--write-md", dest="write_markdown", type=Path, default=DEFAULT_MD)
    parser.add_argument("--require-flag-set", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary = build_summary(
        args.source_save,
        building_index=args.building_index,
        player_index=args.player_index,
        output_save=args.output_save,
        allow_repo_output=args.allow_repo_output,
    )
    print(f"dry-run: {summary['dry_run']}")
    print(f"building-index: {summary['building_index']} ({summary['selection_mode']})")
    print(f"addon-flags-offset: {summary['addon_flags_file_offset']}")
    print(f"flags: {summary['old_addon_flags']} -> {summary['new_addon_flags']}")
    print(f"wrote-output: {summary['wrote_output']}")
    if args.write_json:
        args.write_json.parent.mkdir(parents=True, exist_ok=True)
        args.write_json.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    if args.write_markdown:
        write_markdown(args.write_markdown, summary)
    if args.require_flag_set and not summary["action_eligible_after"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
