#!/usr/bin/env python3
"""Summarize Clash95 castle owner records dumped from gameData."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


RECORD_SIZE = 0x1D3
DEFAULT_RECORDS = 64


def summarize(path: Path, count: int) -> dict[str, Any]:
    data = path.read_bytes()
    if len(data) < count * RECORD_SIZE:
        raise ValueError(f"expected at least {count * RECORD_SIZE} bytes, got {len(data)}")

    records: list[dict[str, Any]] = []
    for index in range(count):
        record = data[index * RECORD_SIZE : (index + 1) * RECORD_SIZE]
        row = {
            "index": index,
            "x": record[0],
            "y": record[1],
            "owner": record[2],
            "byte_4": record[4],
            "flags_1a0": record[0x1A0],
            "flags_1a4": record[0x1A4],
            "byte_1a5": record[0x1A5],
            "word_1ae": int.from_bytes(record[0x1AE : 0x1B0], "little"),
            "dword_1b6": int.from_bytes(record[0x1B6 : 0x1BA], "little"),
            "byte_1bc": record[0x1BC],
            "byte_1b3": record[0x1B3],
            "nonzero": any(record),
        }
        records.append(row)

    interesting = [
        row
        for row in records
        if row["nonzero"] and (row["flags_1a0"] or row["flags_1a4"] or row["byte_4"] == 1)
    ]
    nonempty = [row for row in records if row["nonzero"]]
    active = [row for row in records if row["nonzero"] and row["byte_4"] != 0xFF]
    return {
        "path": str(path),
        "record_size": RECORD_SIZE,
        "record_count": count,
        "records": records,
        "nonempty_records": nonempty,
        "active_records": active,
        "interesting_records": interesting,
        "flag_1a0_values": sorted({row["flags_1a0"] for row in records if row["nonzero"]}),
        "flag_1a4_values": sorted({row["flags_1a4"] for row in records if row["nonzero"]}),
    }


def format_flags(value: int) -> str:
    return f"0x{value:02X}"


def write_markdown(summary: dict[str, Any], path: Path) -> None:
    lines = [
        "# Castle Owner Records Summary",
        "",
        f"- Raw dump: `{summary['path']}`",
        f"- Record size: `{summary['record_size']}`",
        f"- Records parsed: `{summary['record_count']}`",
        f"- `flags_1a0` values: {', '.join(format_flags(value) for value in summary['flag_1a0_values'])}",
        f"- `flags_1a4` values: {', '.join(format_flags(value) for value in summary['flag_1a4_values'])}",
        f"- Active records: `{len(summary['active_records'])}`",
        f"- Non-zero records: `{len(summary['nonempty_records'])}`",
        f"- Interesting records: `{len(summary['interesting_records'])}`",
        "",
        "## Active Records",
        "",
    ]
    if not summary["active_records"]:
        lines.append("- none")
    for row in summary["active_records"]:
        lines.append(
            "- index `{index}` pos `({x},{y})` owner `{owner}` byte_4 `{byte_4}` "
            "flags_1a0 `{flags_1a0}` flags_1a4 `{flags_1a4}` byte_1a5 `{byte_1a5}` "
            "byte_1b3 `{byte_1b3}` byte_1bc `{byte_1bc}`".format(
                **{
                    **row,
                    "flags_1a0": format_flags(row["flags_1a0"]),
                    "flags_1a4": format_flags(row["flags_1a4"]),
                }
            )
        )
    lines.extend(
        [
        "",
        "## Interesting Records",
        "",
        ]
    )
    if not summary["interesting_records"]:
        lines.append("- none")
    for row in summary["interesting_records"]:
        lines.append(
            "- index `{index}` pos `({x},{y})` owner `{owner}` byte_4 `{byte_4}` "
            "flags_1a0 `{flags_1a0}` flags_1a4 `{flags_1a4}` byte_1a5 `{byte_1a5}` "
            "byte_1b3 `{byte_1b3}` byte_1bc `{byte_1bc}`".format(
                **{
                    **row,
                    "flags_1a0": format_flags(row["flags_1a0"]),
                    "flags_1a4": format_flags(row["flags_1a4"]),
                }
            )
        )
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("raw", type=Path)
    parser.add_argument("--count", type=int, default=DEFAULT_RECORDS)
    parser.add_argument("--write-json", type=Path)
    parser.add_argument("--write-md", type=Path)
    parser.add_argument("--require-active", action="store_true")
    parser.add_argument("--require-interesting", action="store_true")
    parser.add_argument("--forbid-interesting", action="store_true")
    args = parser.parse_args()

    summary = summarize(args.raw, args.count)
    if args.write_json:
        args.write_json.parent.mkdir(parents=True, exist_ok=True)
        args.write_json.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    if args.write_md:
        write_markdown(summary, args.write_md)

    print(
        "records={records} active={active} nonzero={nonempty} interesting={interesting} "
        "flags_1a0={flags_1a0} flags_1a4={flags_1a4}".format(
            records=summary["record_count"],
            active=len(summary["active_records"]),
            nonempty=len(summary["nonempty_records"]),
            interesting=len(summary["interesting_records"]),
            flags_1a0=",".join(format_flags(value) for value in summary["flag_1a0_values"]),
            flags_1a4=",".join(format_flags(value) for value in summary["flag_1a4_values"]),
        )
    )
    if args.require_interesting and not summary["interesting_records"]:
        print("no interesting owner records found", file=sys.stderr)
        return 2
    if args.require_active and not summary["active_records"]:
        print("no active owner records found", file=sys.stderr)
        return 2
    if args.forbid_interesting and summary["interesting_records"]:
        print("interesting owner records found", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
