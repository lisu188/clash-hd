#!/usr/bin/env python3
"""Scan installed Clash95 saves for castle owner/action flag metadata.

This helper reads local save files and reports only compact metadata from
plausible castle-owner record blocks. It does not copy raw save bytes into the
repository and does not launch Clash95, CDB, wrappers, PowerShell, or any
visible window.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_SAVES_ROOT = Path(r"C:\Clash\save")
DEFAULT_KNOWN_OFFSET = 509690
DEFAULT_RECORD_COUNT = 64
RECORD_SIZE = 0x1D3
DEFAULT_JSON = Path("captures/current/castle-save-owner-flag-scan-current.json")
DEFAULT_MD = Path("captures/current/castle-save-owner-flag-scan-current.md")
RUNTIME_POLICY = (
    "local save metadata inspection only; reads installed save files but does "
    "not copy raw saves, launch Clash95, CDB, wrappers, PowerShell, or visible windows"
)
GUARD_POLICY = (
    "finds whether any installed save naturally has castle owner flag bit 0x02 "
    "set, which is required before the 004338E0 owner/action lane can be routed "
    "without debugger-forced owner flags"
)


def status_text(passed: bool) -> str:
    return "PASS" if passed else "FAIL"


def hex_byte(value: int) -> str:
    return f"0x{value:02X}"


def save_sort_key(path: Path) -> tuple[int, str]:
    try:
        return int(path.stem), path.name
    except ValueError:
        return sys.maxsize, path.name.lower()


def active_record(record: bytes) -> bool:
    return any(record) and record[4] != 0xFF


def record_metadata(save: Path, block_offset: int, index: int, record: bytes) -> dict[str, Any]:
    flags_1a0 = record[0x1A0]
    flags_1a4 = record[0x1A4]
    return {
        "save": str(save),
        "block_offset": block_offset,
        "record_index": index,
        "x": record[0],
        "y": record[1],
        "owner": record[2],
        "byte_4": record[4],
        "flags_1a0": flags_1a0,
        "flags_1a0_hex": hex_byte(flags_1a0),
        "flags_1a4": flags_1a4,
        "flags_1a4_hex": hex_byte(flags_1a4),
        "byte_1a5": record[0x1A5],
        "byte_1b3": record[0x1B3],
        "byte_1bc": record[0x1BC],
        "bit2": flags_1a0 & 0x02,
        "bit1": flags_1a0 & 0x01,
        "bit8": flags_1a0 & 0x08,
        "action_eligible": bool(flags_1a0 & 0x02),
    }


def plausible_active_record(row: dict[str, Any]) -> bool:
    return (
        0 <= int(row["x"]) < 100
        and 0 <= int(row["y"]) < 100
        and 0 <= int(row["owner"]) <= 15
        and int(row["byte_4"]) in {0, 1, 2, 3}
    )


def parse_owner_block(
    save: Path,
    data: bytes,
    offset: int,
    record_count: int = DEFAULT_RECORD_COUNT,
) -> dict[str, Any]:
    block_size = record_count * RECORD_SIZE
    failures: list[str] = []
    records: list[dict[str, Any]] = []

    if offset < 0:
        failures.append(f"negative owner-block offset: {offset}")
    elif offset + block_size > len(data):
        failures.append(
            "owner-block offset 0x{offset:06X} needs {needed} bytes, save has {size}".format(
                offset=offset,
                needed=block_size,
                size=len(data),
            )
        )
    else:
        for index in range(record_count):
            start = offset + index * RECORD_SIZE
            record = data[start : start + RECORD_SIZE]
            if active_record(record):
                records.append(record_metadata(save, offset, index, record))

    plausible_records = [row for row in records if plausible_active_record(row)]
    implausible_records = [row for row in records if not plausible_active_record(row)]
    records_with_any_owner_flag = [
        row for row in records if int(row["flags_1a0"]) or int(row["flags_1a4"])
    ]
    records_with_bit2 = [row for row in records if bool(row["action_eligible"])]

    if records and not plausible_records:
        failures.append("no active records at the candidate offset have plausible coordinates/owners")
    if implausible_records:
        failures.append(
            f"{len(implausible_records)} active records at the candidate offset are implausible"
        )
    if len(plausible_records) > 16:
        failures.append(
            f"{len(plausible_records)} plausible active records exceeds the expected castle-owner range"
        )

    plausible = not failures and 1 <= len(plausible_records) <= 16
    return {
        "save": str(save),
        "save_size": len(data),
        "offset": offset,
        "offset_hex": f"0x{offset:06X}",
        "record_size": RECORD_SIZE,
        "record_count": record_count,
        "plausible": plausible,
        "active_records": plausible_records,
        "active_record_count": len(plausible_records),
        "implausible_active_record_count": len(implausible_records),
        "records_with_any_owner_flag": records_with_any_owner_flag,
        "records_with_bit2": records_with_bit2,
        "records_with_any_owner_flag_count": len(records_with_any_owner_flag),
        "records_with_bit2_count": len(records_with_bit2),
        "flag_1a0_values": sorted({row["flags_1a0"] for row in plausible_records}),
        "flag_1a4_values": sorted({row["flags_1a4"] for row in plausible_records}),
        "failures": failures,
    }


def scan_save(save: Path, known_offset: int, record_count: int) -> dict[str, Any]:
    try:
        data = save.read_bytes()
    except OSError as exc:
        return {
            "save": str(save),
            "passed": False,
            "failures": [f"could not read save file: {exc}"],
            "known_offset_block": None,
        }

    block = parse_owner_block(save, data, known_offset, record_count)
    return {
        "save": str(save),
        "passed": bool(block.get("plausible")),
        "save_size": len(data),
        "known_offset_checked": known_offset,
        "known_offset_block": block,
        "failures": [] if block.get("plausible") else list(block.get("failures") or []),
    }


def find_recommended_target(blocks: list[dict[str, Any]]) -> dict[str, Any] | None:
    for block in blocks:
        for row in block.get("records_with_bit2") or []:
            return row
    return None


def build_report(
    saves_root: Path = DEFAULT_SAVES_ROOT,
    known_offset: int = DEFAULT_KNOWN_OFFSET,
    record_count: int = DEFAULT_RECORD_COUNT,
) -> dict[str, Any]:
    failures: list[str] = []
    if not saves_root.exists():
        failures.append(f"missing saves root: {saves_root}")
        save_paths: list[Path] = []
    else:
        save_paths = sorted(saves_root.glob("*.dat"), key=save_sort_key)
        if not save_paths:
            failures.append(f"no .dat save files found under {saves_root}")

    save_reports = [scan_save(path, known_offset, record_count) for path in save_paths]
    plausible_blocks = [
        report["known_offset_block"]
        for report in save_reports
        if (report.get("known_offset_block") or {}).get("plausible")
    ]
    records_with_bit2 = [
        row
        for block in plausible_blocks
        for row in block.get("records_with_bit2") or []
    ]
    records_with_any_owner_flag = [
        row
        for block in plausible_blocks
        for row in block.get("records_with_any_owner_flag") or []
    ]
    action_eligible_saves = sorted({row["save"] for row in records_with_bit2})

    if save_paths and not plausible_blocks:
        failures.append(
            f"no plausible castle-owner blocks found at known offset 0x{known_offset:06X}"
        )

    recommended = find_recommended_target(plausible_blocks)
    blocker = None
    if plausible_blocks and not records_with_bit2:
        blocker = (
            "no installed save currently has flags_1a0 bit 0x02 set in the "
            "known castle-owner block"
        )

    return {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "passed": not failures,
        "runtime_policy": RUNTIME_POLICY,
        "guard_policy": GUARD_POLICY,
        "saves_root": str(saves_root),
        "known_offset_checked": known_offset,
        "known_offset_hex": f"0x{known_offset:06X}",
        "record_size": RECORD_SIZE,
        "record_count": record_count,
        "save_reports": save_reports,
        "plausible_blocks": plausible_blocks,
        "records_with_bit2": records_with_bit2,
        "records_with_any_owner_flag": records_with_any_owner_flag,
        "recommended_route_target": recommended,
        "current_blocker": blocker,
        "summary": {
            "save_count": len(save_paths),
            "candidate_block_count": len(plausible_blocks),
            "action_eligible_save_count": len(action_eligible_saves),
            "action_eligible_record_count": len(records_with_bit2),
            "records_with_any_owner_flag_count": len(records_with_any_owner_flag),
            "active_record_count": sum(
                int(block.get("active_record_count") or 0) for block in plausible_blocks
            ),
            "recommended_route_target": recommended,
            "current_blocker": blocker,
        },
        "failures": failures,
    }


def format_target(row: dict[str, Any] | None) -> str:
    if not row:
        return "none"
    return (
        "{save} offset {offset} index {index} pos ({x},{y}) owner {owner} "
        "flags_1a0 {flags}".format(
            save=row["save"],
            offset=f"0x{int(row['block_offset']):06X}",
            index=row["record_index"],
            x=row["x"],
            y=row["y"],
            owner=row["owner"],
            flags=row["flags_1a0_hex"],
        )
    )


def write_markdown(path: Path, report: dict[str, Any]) -> None:
    summary = report.get("summary") or {}
    lines = [
        "# Castle Save Owner-Flag Scan",
        "",
        f"- Overall: {status_text(bool(report.get('passed')))}",
        f"- Generated: `{report['generated_at']}`",
        f"- Runtime policy: {report['runtime_policy']}",
        f"- Guard policy: {report['guard_policy']}",
        f"- Saves root: `{report['saves_root']}`",
        f"- Known owner-block offset checked: `{report['known_offset_hex']}`",
        f"- Save files scanned: `{summary.get('save_count')}`",
        f"- Plausible owner blocks: `{summary.get('candidate_block_count')}`",
        f"- Active records in plausible blocks: `{summary.get('active_record_count')}`",
        f"- Records with any owner flag: `{summary.get('records_with_any_owner_flag_count')}`",
        f"- Action-eligible records (`flags_1a0 & 0x02`): `{summary.get('action_eligible_record_count')}`",
        f"- Recommended route target: `{format_target(report.get('recommended_route_target'))}`",
        f"- Current blocker: `{report.get('current_blocker') or 'none'}`",
        "",
        "## Plausible Blocks",
        "",
    ]
    if not report.get("plausible_blocks"):
        lines.append("- none")
    for block in report.get("plausible_blocks") or []:
        lines.append(
            "- `{save}` offset `{offset}` active `{active}` any-owner-flag `{any_flag}` "
            "bit2 `{bit2}` flags_1a0 `{flags}`".format(
                save=block["save"],
                offset=block["offset_hex"],
                active=block["active_record_count"],
                any_flag=block["records_with_any_owner_flag_count"],
                bit2=block["records_with_bit2_count"],
                flags=", ".join(hex_byte(value) for value in block["flag_1a0_values"]) or "none",
            )
        )
    lines.extend(["", "## Action-Eligible Records", ""])
    if not report.get("records_with_bit2"):
        lines.append("- none")
    for row in report.get("records_with_bit2") or []:
        lines.append(
            "- `{save}` offset `{offset}` index `{index}` pos `({x},{y})` owner `{owner}` "
            "flags_1a0 `{flags_1a0}` flags_1a4 `{flags_1a4}` byte_4 `{byte_4}`".format(
                save=row["save"],
                offset=f"0x{int(row['block_offset']):06X}",
                index=row["record_index"],
                x=row["x"],
                y=row["y"],
                owner=row["owner"],
                flags_1a0=row["flags_1a0_hex"],
                flags_1a4=row["flags_1a4_hex"],
                byte_4=row["byte_4"],
            )
        )
    if report.get("failures"):
        lines.extend(["", "## Failures", ""])
        lines.extend(f"- {failure}" for failure in report["failures"])
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--saves-root", type=Path, default=DEFAULT_SAVES_ROOT)
    parser.add_argument("--known-offset", type=int, default=DEFAULT_KNOWN_OFFSET)
    parser.add_argument("--record-count", type=int, default=DEFAULT_RECORD_COUNT)
    parser.add_argument("--write-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--write-markdown", type=Path, default=DEFAULT_MD)
    parser.add_argument("--require-pass", action="store_true")
    parser.add_argument("--require-action-eligible", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(args.saves_root, args.known_offset, args.record_count)
    summary = report["summary"]
    print(f"overall: {status_text(bool(report['passed']))}")
    print(f"runtime-policy: {report['runtime_policy']}")
    print(f"save-files: {summary['save_count']}")
    print(f"plausible-owner-blocks: {summary['candidate_block_count']}")
    print(f"action-eligible-records: {summary['action_eligible_record_count']}")
    print(f"recommended-route-target: {format_target(report.get('recommended_route_target'))}")
    if report.get("current_blocker"):
        print(f"current-blocker: {report['current_blocker']}")
    if args.write_json:
        args.write_json.parent.mkdir(parents=True, exist_ok=True)
        args.write_json.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if args.write_markdown:
        write_markdown(args.write_markdown, report)
    if args.require_pass and not report["passed"]:
        return 2
    if args.require_action_eligible and not summary["action_eligible_record_count"]:
        print("no action-eligible owner records found", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
