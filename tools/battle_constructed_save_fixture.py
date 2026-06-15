#!/usr/bin/env python3
r"""Plan or create an isolated battle save with an enabled command unit type.

This helper never edits ``C:\Clash\save``. By default it performs a dry run:
it reads one source save and the original executable command table, reports the
unit-record byte that would change, and writes only JSON/Markdown evidence. If
``--output-save`` is supplied, it writes a copied save to that path and refuses
to write inside the repository unless ``--allow-repo-output`` is passed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import battle_command_availability as availability
import battle_save_unit_inventory as inventory
from patch_stage_report import parse_pe_sections


DEFAULT_SOURCE_SAVE = Path(r"C:\Clash\save\0.dat")
DEFAULT_EXE = Path(r"C:\Clash\clash95.exe")
DEFAULT_JSON = Path("captures/current/battle-constructed-save-fixture-current.json")
DEFAULT_MD = Path("captures/current/battle-constructed-save-fixture-current.md")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def path_is_under(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def unit_record_offset(unit_index: int, *, base_offset: int = inventory.SAVE_UNIT_BASE_OFFSET) -> int:
    return base_offset + (unit_index * inventory.UNIT_RECORD_STRIDE)


def unit_type_offset(unit_index: int, *, base_offset: int = inventory.SAVE_UNIT_BASE_OFFSET) -> int:
    return unit_record_offset(unit_index, base_offset=base_offset) + inventory.TYPE_OFFSET


def patch_unit_type(data: bytes, *, unit_index: int, target_unit_type: int) -> bytes:
    offset = unit_type_offset(unit_index)
    if offset + 2 > len(data):
        raise ValueError(f"unit index {unit_index} type offset 0x{offset:08X} is outside save data")
    patched = bytearray(data)
    patched[offset : offset + 2] = target_unit_type.to_bytes(2, "little")
    return bytes(patched)


def command_info(exe: Path, unit_type: int) -> dict[str, Any]:
    data = exe.read_bytes()
    image_base, sections = parse_pe_sections(data)
    if image_base is None:
        raise ValueError(f"could not read image base from {exe}")
    return availability.availability_for_type(data, image_base, sections, unit_type)


def build_summary(
    source_save: Path,
    exe: Path,
    *,
    unit_index: int,
    target_unit_type: int,
    output_save: Path | None = None,
    allow_repo_output: bool = False,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    source_data = source_save.read_bytes()
    units = inventory.parse_save_units(source_data)
    selected = next((unit for unit in units if int(unit["idx"]) == unit_index), None)
    if selected is None:
        raise ValueError(f"unit index {unit_index} was not parsed from {source_save}")

    old_type = int(selected["unit_type"])
    old_info = command_info(exe, old_type)
    target_info = command_info(exe, target_unit_type)
    patched_data = patch_unit_type(source_data, unit_index=unit_index, target_unit_type=target_unit_type)
    patched_units = inventory.parse_save_units(patched_data)
    patched_selected = next((unit for unit in patched_units if int(unit["idx"]) == unit_index), None)
    if patched_selected is None or int(patched_selected["unit_type"]) != target_unit_type:
        raise ValueError("patched save did not reparse with the requested target unit type")

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

    return {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "runtime_policy": (
            "save fixture planner; reads source save/exe; never edits C:\\Clash\\save; "
            "writes copied save only when --output-save is supplied"
        ),
        "source_save": str(source_save),
        "exe": str(exe),
        "output_save": output_path_text,
        "dry_run": not wrote_output,
        "source_sha256": sha256_bytes(source_data),
        "patched_sha256": sha256_bytes(patched_data),
        "unit_index": unit_index,
        "unit_type_offset": f"0x{unit_type_offset(unit_index):08X}",
        "unit_record_offset": f"0x{unit_record_offset(unit_index):08X}",
        "old_unit_type": old_type,
        "old_name": old_info.get("name_en"),
        "old_asset": old_info.get("asset_key"),
        "old_availability": old_info.get("availability"),
        "old_enabled": old_info.get("enabled"),
        "target_unit_type": target_unit_type,
        "target_name": target_info.get("name_en"),
        "target_asset": target_info.get("asset_key"),
        "target_availability": target_info.get("availability"),
        "target_enabled": target_info.get("enabled"),
        "target_is_enabled": int(target_info.get("enabled") or 0) > 0,
        "source_unit_count": len(units),
        "patched_unit_count": len(patched_units),
        "wrote_output": wrote_output,
    }


def write_markdown(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# Battle Constructed Save Fixture",
        "",
        f"- Generated: `{summary['generated_at']}`",
        f"- Runtime policy: {summary['runtime_policy']}",
        f"- Source save: `{summary['source_save']}`",
        f"- Executable: `{summary['exe']}`",
        f"- Output save: `{summary['output_save']}`",
        f"- Dry run: `{summary['dry_run']}`",
        f"- Wrote output: `{summary['wrote_output']}`",
        f"- Source SHA-256: `{summary['source_sha256']}`",
        f"- Patched SHA-256: `{summary['patched_sha256']}`",
        "",
        "## Planned Change",
        "",
        "| Unit index | Type offset | Old type | Old name | Old enabled | Target type | Target name | Target enabled |",
        "| ---: | --- | ---: | --- | ---: | ---: | --- | ---: |",
        (
            f"| {summary['unit_index']} | `{summary['unit_type_offset']}` | "
            f"{summary['old_unit_type']} | {summary['old_name'] or ''} | {summary['old_enabled']} | "
            f"{summary['target_unit_type']} | {summary['target_name'] or ''} | {summary['target_enabled']} |"
        ),
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-save", type=Path, default=DEFAULT_SOURCE_SAVE)
    parser.add_argument("--exe", type=Path, default=DEFAULT_EXE)
    parser.add_argument("--unit-index", type=int, default=0)
    parser.add_argument("--target-unit-type", type=int, default=8)
    parser.add_argument("--output-save", type=Path)
    parser.add_argument("--allow-repo-output", action="store_true")
    parser.add_argument("--write-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--write-markdown", "--write-md", dest="write_markdown", type=Path, default=DEFAULT_MD)
    parser.add_argument("--require-target-enabled", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary = build_summary(
        args.source_save,
        args.exe,
        unit_index=args.unit_index,
        target_unit_type=args.target_unit_type,
        output_save=args.output_save,
        allow_repo_output=args.allow_repo_output,
    )
    print(f"dry-run: {summary['dry_run']}")
    print(f"unit-index: {summary['unit_index']}")
    print(f"old-unit: {summary['old_unit_type']} {summary['old_name']}")
    print(f"target-unit: {summary['target_unit_type']} {summary['target_name']}")
    print(f"target-enabled: {summary['target_enabled']}")
    print(f"wrote-output: {summary['wrote_output']}")
    if args.write_json:
        args.write_json.parent.mkdir(parents=True, exist_ok=True)
        args.write_json.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    if args.write_markdown:
        write_markdown(args.write_markdown, summary)
    if args.require_target_enabled and not summary["target_is_enabled"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
