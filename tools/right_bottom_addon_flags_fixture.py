#!/usr/bin/env python3
r"""Plan or create an isolated right-bottom ``addon_flags`` save fixture.

Gate 1 of ``reports/hd_completion_certainty.md`` is disassembly-verified: the
right-bottom building action menu draws only when the clicked building record
has bit ``0x02`` set in its ``addon_flags`` byte (``building_record + 416``,
``clash95.c:49999``). With the bit clear the production panel and action rows
are skipped and the production action descriptor is parked off-screen at
``x=1000`` (``clash95.c:37758``). This matches the mod's observed
``owner_flag=0x00`` / parked-``(1000,426)`` natural-route evidence exactly: it
is correct binary behaviour, not a patch defect.

Because ``SaveSlot_LoadGame`` restores the save as a verbatim binary image
(skip a 16-byte header, then one bulk ``fread_(gameData, 0x8F29E, ...)``,
``clash95.c:61809``) with no per-building reconstruction, the natural route can
be reached by a single isolated save-byte edit -- exactly mirroring the proven
battle ``battle_constructed_save_fixture.py`` pattern.

This helper is repo-only by default. With no readable ``--source-save`` it runs
in plan-only mode, reporting the disassembly-derived offset math and writing
only JSON/Markdown evidence. Given a readable source save it additionally
inspects the target building record. It writes a copied+patched save only when
``--output-save`` is supplied, never mutates ``C:\Clash\save``, and refuses to
write inside the repository unless ``--allow-repo-output`` is passed.

Offset derivation (all citations are ``clash-disassembly/clash95.c``):

- building records live at ``gameData + 509674``, 467-byte stride, 100 records
  (``docs/SAVE_DAT_FORMAT.md`` row 509674);
- the save file prepends a 16-byte header before the ``gameData`` image, so a
  ``gameData`` byte ``N`` sits at file offset ``16 + N``;
- therefore the ``addon_flags`` byte of building ``i`` is at file offset
  ``16 + 509674 + i*467 + 416``.

Note: ``reports/hd_completion_certainty.md`` renders this as
``0x10 + 0x7C6FA + i*467 + 0x1A0``. That parenthetical is off by 16:
``0x7C6FA`` is ``509690`` -- the *save-file* record base ``16 + 509674``, which
already includes the header -- so adding ``0x10`` again double-counts it. The
decimal formula above (memory base ``509674`` plus one 16-byte header) is
authoritative and is what this tool computes: building 0's ``addon_flags`` byte
is at file offset ``510106`` (``0x7C89A``), not ``510122``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path, PureWindowsPath
from typing import Any


# Disassembly-verified save/building layout constants.
SAVE_HEADER_SIZE = 16  # SaveSlot_LoadGame skips a 16-byte header (clash95.c:61809)
GAMEDATA_IMAGE_SIZE = 0x8F29E  # bulk fread_ length into gameData (clash95.c:61809)
BUILDING_MEMORY_BASE_OFFSET = 509674  # gameData + 509674 (docs/SAVE_DAT_FORMAT.md)
BUILDING_SAVE_BASE_OFFSET = SAVE_HEADER_SIZE + BUILDING_MEMORY_BASE_OFFSET  # 509690
BUILDING_RECORD_STRIDE = 467
BUILDING_RECORD_COUNT = 100
OWNER_OFFSET = 3  # player index at building_record + 2/+3 (clash95.c:34125-34126)
TYPE_OFFSET = 4  # building type a1 at building_record + 4 (clash95.c:34124)
ADDON_FLAGS_OFFSET = 416  # addon_flags at building_record + 416 (clash95.c:37742)
PRODUCTION_FLAG_BIT = 0x02  # set only by Building_New(1, ...) (clash95.c:34184-34186)
EXPECTED_SAVE_SIZE = SAVE_HEADER_SIZE + GAMEDATA_IMAGE_SIZE

DEFAULT_SOURCE_SAVE = Path(r"C:\Clash\save\0.dat")
DEFAULT_JSON = Path("captures/current/right-bottom-addon-flags-fixture-current.json")
DEFAULT_MD = Path("captures/current/right-bottom-addon-flags-fixture-current.md")

RUNTIME_POLICY = (
    "repo-only fixture planner; reads at most one source save and writes only "
    "JSON/Markdown evidence unless --output-save is passed; never mutates "
    r"C:\Clash\save and never launches Clash95, CDB, wrappers, PowerShell, or "
    "visible windows"
)
PROMOTION_POLICY = (
    "non-promoting: the copied+patched save makes the right-bottom production "
    "panel drawable on a natural route, but promotion still requires approved "
    "real-input (manual DirectInput) proof per reports/final_hd_validation_matrix.md"
)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def path_is_under(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def _windows_parts_lower(path: Path) -> list[str]:
    return [part.lower() for part in PureWindowsPath(str(path)).parts]


def targets_protected_save_dir(path: Path) -> bool:
    r"""True if ``path`` resolves inside a ``...\Clash\save`` directory.

    Guards against writing the fixture over the user-owned original saves. The
    check is string-based on Windows-style parts so it also holds when this
    planner runs on a non-Windows host.
    """

    parts = _windows_parts_lower(path)
    for idx in range(len(parts) - 1):
        if parts[idx] == "clash" and parts[idx + 1] == "save":
            return True
    return False


def building_record_offset(building_index: int) -> int:
    return BUILDING_SAVE_BASE_OFFSET + (building_index * BUILDING_RECORD_STRIDE)


def addon_flags_offset(building_index: int) -> int:
    return building_record_offset(building_index) + ADDON_FLAGS_OFFSET


def validate_building_index(building_index: int) -> None:
    if not 0 <= building_index < BUILDING_RECORD_COUNT:
        raise ValueError(
            f"building index {building_index} outside 0..{BUILDING_RECORD_COUNT - 1}"
        )


def set_production_flag(data: bytes, *, building_index: int) -> bytes:
    """Return ``data`` with ``addon_flags`` bit ``0x02`` set for one building.

    Only the single ``addon_flags`` byte changes; every other byte is preserved.
    Setting a bit that is already set is a no-op (idempotent).
    """

    validate_building_index(building_index)
    offset = addon_flags_offset(building_index)
    if offset + 1 > len(data):
        raise ValueError(
            f"building index {building_index} addon_flags offset "
            f"0x{offset:08X} is outside save data of {len(data)} bytes"
        )
    patched = bytearray(data)
    patched[offset] |= PRODUCTION_FLAG_BIT
    return bytes(patched)


def describe_building(data: bytes, *, building_index: int) -> dict[str, Any]:
    validate_building_index(building_index)
    record = building_record_offset(building_index)
    flags_offset = addon_flags_offset(building_index)
    if flags_offset + 1 > len(data):
        raise ValueError(
            f"building index {building_index} addon_flags offset "
            f"0x{flags_offset:08X} is outside save data of {len(data)} bytes"
        )
    flags = data[flags_offset]
    return {
        "building_index": building_index,
        "record_offset": f"0x{record:08X}",
        "addon_flags_offset": f"0x{flags_offset:08X}",
        "addon_flags_offset_decimal": flags_offset,
        "owner_byte": data[record + OWNER_OFFSET],
        "type_byte": data[record + TYPE_OFFSET],
        "addon_flags": f"0x{flags:02X}",
        "production_flag_set": bool(flags & PRODUCTION_FLAG_BIT),
    }


def offset_math(building_index: int) -> dict[str, Any]:
    flags_offset = addon_flags_offset(building_index)
    return {
        "building_index": building_index,
        "save_header_size": SAVE_HEADER_SIZE,
        "building_memory_base_offset": BUILDING_MEMORY_BASE_OFFSET,
        "building_save_base_offset": BUILDING_SAVE_BASE_OFFSET,
        "building_record_stride": BUILDING_RECORD_STRIDE,
        "building_record_count": BUILDING_RECORD_COUNT,
        "addon_flags_field_offset": ADDON_FLAGS_OFFSET,
        "production_flag_bit": f"0x{PRODUCTION_FLAG_BIT:02X}",
        "record_offset": f"0x{building_record_offset(building_index):08X}",
        "addon_flags_file_offset": f"0x{flags_offset:08X}",
        "addon_flags_file_offset_decimal": flags_offset,
        "formula": "16 + 509674 + building_index*467 + 416",
        "expected_save_size": EXPECTED_SAVE_SIZE,
        "expected_save_size_hex": f"0x{EXPECTED_SAVE_SIZE:08X}",
    }


def build_summary(
    *,
    building_index: int,
    source_save: Path,
    source_data: bytes | None,
    output_save: Path | None,
    output_written: bool,
    output_data: bytes | None,
    warnings: list[str],
    notes: list[str],
) -> dict[str, Any]:
    math = offset_math(building_index)
    passed = not warnings
    summary: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "passed": passed,
        "mode": "apply" if output_written else "plan-only",
        "runtime_policy": RUNTIME_POLICY,
        "promotion_policy": PROMOTION_POLICY,
        "source_save": str(source_save),
        "offset_math": math,
        "warnings": warnings,
        "notes": notes,
    }
    if source_data is not None:
        summary["source_sha256"] = sha256_bytes(source_data)
        summary["source_size"] = len(source_data)
        summary["source_size_matches_expected"] = len(source_data) == EXPECTED_SAVE_SIZE
        summary["source_building"] = describe_building(
            source_data, building_index=building_index
        )
    if output_save is not None:
        summary["output_save"] = str(output_save)
        summary["output_written"] = output_written
    if output_data is not None:
        summary["output_sha256"] = sha256_bytes(output_data)
        summary["output_building"] = describe_building(
            output_data, building_index=building_index
        )
    return summary


def status_text(passed: bool) -> str:
    return "PASS" if passed else "FAIL"


def render_markdown(summary: dict[str, Any]) -> str:
    math = summary["offset_math"]
    lines = [
        "# Right-Bottom addon_flags Save Fixture",
        "",
        f"- Overall: {status_text(summary['passed'])}",
        f"- Mode: `{summary['mode']}`",
        f"- Generated: `{summary['generated_at']}`",
        f"- Runtime policy: {summary['runtime_policy']}",
        f"- Promotion policy: {summary['promotion_policy']}",
        f"- Source save: `{summary['source_save']}`",
        "",
        "## Offset math (disassembly-verified)",
        "",
        f"- Building index: `{math['building_index']}`",
        f"- Formula: `{math['formula']}`",
        f"- addon_flags file offset: `{math['addon_flags_file_offset']}` "
        f"(`{math['addon_flags_file_offset_decimal']}`)",
        f"- Record offset: `{math['record_offset']}`",
        f"- Production flag bit: `{math['production_flag_bit']}`",
        f"- Record stride: `{math['building_record_stride']}`, "
        f"count: `{math['building_record_count']}`",
        f"- Expected save size: `{math['expected_save_size']}` "
        f"(`{math['expected_save_size_hex']}`)",
    ]
    if "source_building" in summary:
        building = summary["source_building"]
        lines += [
            "",
            "## Source building record",
            "",
            f"- Source SHA-256: `{summary['source_sha256']}`",
            f"- Source size: `{summary['source_size']}` "
            f"(matches expected: `{summary['source_size_matches_expected']}`)",
            f"- Owner byte: `{building['owner_byte']}`",
            f"- Type byte: `{building['type_byte']}`",
            f"- addon_flags: `{building['addon_flags']}` "
            f"(production bit set: `{building['production_flag_set']}`)",
        ]
    if "output_save" in summary:
        lines += [
            "",
            "## Output fixture",
            "",
            f"- Output save: `{summary['output_save']}`",
            f"- Written: `{summary['output_written']}`",
        ]
        if "output_sha256" in summary:
            out_building = summary["output_building"]
            lines += [
                f"- Output SHA-256: `{summary['output_sha256']}`",
                f"- Output addon_flags: `{out_building['addon_flags']}` "
                f"(production bit set: `{out_building['production_flag_set']}`)",
            ]
    if summary["warnings"]:
        lines += ["", "## Warnings", ""]
        lines += [f"- {warning}" for warning in summary["warnings"]]
    if summary.get("notes"):
        lines += ["", "## Notes", ""]
        lines += [f"- {note}" for note in summary["notes"]]
    lines.append("")
    return "\n".join(lines)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--building-index", type=int, default=0)
    parser.add_argument("--source-save", type=Path, default=DEFAULT_SOURCE_SAVE)
    parser.add_argument("--output-save", type=Path, default=None)
    parser.add_argument("--allow-repo-output", action="store_true")
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--md", type=Path, default=DEFAULT_MD)
    parser.add_argument("--no-evidence", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    warnings: list[str] = []
    notes: list[str] = []

    try:
        validate_building_index(args.building_index)
    except ValueError as exc:
        print(f"error: {exc}")
        return 2

    source_data: bytes | None = None
    if args.source_save.exists():
        source_data = args.source_save.read_bytes()
        if len(source_data) != EXPECTED_SAVE_SIZE:
            warnings.append(
                f"source save size {len(source_data)} != expected "
                f"{EXPECTED_SAVE_SIZE}; offsets may not line up with a stock save"
            )
    else:
        notes.append(
            f"source save {args.source_save} not readable here; running plan-only "
            "(offset math is host-independent)"
        )

    output_written = False
    output_data: bytes | None = None
    if args.output_save is not None:
        if source_data is None:
            warnings.append(
                "cannot write --output-save without a readable --source-save"
            )
        elif targets_protected_save_dir(args.output_save):
            warnings.append(
                rf"refusing to write inside a Clash\save directory: {args.output_save}"
            )
        elif path_is_under(args.output_save, Path.cwd()) and not args.allow_repo_output:
            warnings.append(
                "refusing to write inside the repository without --allow-repo-output: "
                f"{args.output_save}"
            )
        else:
            output_data = set_production_flag(
                source_data, building_index=args.building_index
            )
            args.output_save.parent.mkdir(parents=True, exist_ok=True)
            args.output_save.write_bytes(output_data)
            output_written = True

    summary = build_summary(
        building_index=args.building_index,
        source_save=args.source_save,
        source_data=source_data,
        output_save=args.output_save,
        output_written=output_written,
        output_data=output_data,
        warnings=warnings,
        notes=notes,
    )

    if not args.no_evidence:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        args.md.parent.mkdir(parents=True, exist_ok=True)
        args.md.write_text(render_markdown(summary), encoding="utf-8")

    print(render_markdown(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
