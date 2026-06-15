#!/usr/bin/env python3
"""Summarize high-byte command IDs in a Clash95 castle overview hitmap dump."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


COMMAND_BY_RAW = {
    0xF8: 0x86,
    0xFA: 0x99,
    0xFB: 0x9C,
    0xFC: 0x9F,
    0xFD: 0xA6,
    0xFE: 0x63,
    0xFF: 0x87,
}


def summarize(path: Path, width: int, height: int) -> dict[str, Any]:
    data = path.read_bytes()
    if len(data) != width * height:
        raise ValueError(f"expected {width * height} bytes, got {len(data)}")

    values: dict[str, Any] = {}
    for raw in range(0xF8, 0x100):
        points = [(index % width, index // width) for index, byte in enumerate(data) if byte == raw]
        entry: dict[str, Any] = {
            "raw": raw,
            "command": COMMAND_BY_RAW.get(raw),
            "count": len(points),
            "present": bool(points),
        }
        if points:
            xs = [point[0] for point in points]
            ys = [point[1] for point in points]
            first = points[0]
            entry.update(
                {
                    "bbox": [min(xs), min(ys), max(xs), max(ys)],
                    "first_native": list(first),
                    "first_displayed": [first[0] + 80, first[1] + 60],
                    "mean_native": [sum(xs) / len(points), sum(ys) / len(points)],
                }
            )
        values[f"0x{raw:02X}"] = entry
    return {
        "path": str(path),
        "width": width,
        "height": height,
        "values": values,
        "present_raw_ids": [key for key, value in values.items() if value["present"]],
        "absent_catalog_raw_ids": [
            key
            for key, value in values.items()
            if value["command"] is not None and not value["present"]
        ],
    }


def write_markdown(summary: dict[str, Any], path: Path) -> None:
    lines = [
        "# Castle Overview Hitmap Summary",
        "",
        f"- Raw dump: `{summary['path']}`",
        f"- Size: `{summary['width']}x{summary['height']}`",
        f"- Present raw IDs: {', '.join(summary['present_raw_ids'])}",
        f"- Absent catalog raw IDs: {', '.join(summary['absent_catalog_raw_ids'])}",
        "",
        "## Values",
        "",
    ]
    for key, value in summary["values"].items():
        command = value["command"]
        command_text = f"0x{command:02X}" if isinstance(command, int) else "none"
        lines.append(
            f"- `{key}` command `{command_text}` count `{value['count']}` "
            f"first_displayed `{value.get('first_displayed')}` bbox `{value.get('bbox')}`"
        )
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("raw", type=Path)
    parser.add_argument("--width", type=int, default=640)
    parser.add_argument("--height", type=int, default=480)
    parser.add_argument("--write-json", type=Path)
    parser.add_argument("--write-md", type=Path)
    parser.add_argument("--require-present", action="append", default=[])
    parser.add_argument("--require-absent", action="append", default=[])
    args = parser.parse_args()

    summary = summarize(args.raw, args.width, args.height)
    if args.write_json:
        args.write_json.parent.mkdir(parents=True, exist_ok=True)
        args.write_json.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    if args.write_md:
        write_markdown(summary, args.write_md)

    print(
        "present={present} absent_catalog={absent}".format(
            present=",".join(summary["present_raw_ids"]),
            absent=",".join(summary["absent_catalog_raw_ids"]),
        )
    )

    for raw_text in args.require_present:
        key = f"0x{int(raw_text, 0):02X}"
        if not summary["values"].get(key, {}).get("present"):
            print(f"required present raw id {key} was absent", file=sys.stderr)
            return 2
    for raw_text in args.require_absent:
        key = f"0x{int(raw_text, 0):02X}"
        if summary["values"].get(key, {}).get("present"):
            print(f"required absent raw id {key} was present", file=sys.stderr)
            return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
