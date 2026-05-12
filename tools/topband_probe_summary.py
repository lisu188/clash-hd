#!/usr/bin/env python3
"""Summarize Clash95 HD top-band CDB probe logs."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


KEY_VALUE_RE = re.compile(r"([A-Za-z0-9_]+)=([^\s]+)")
LTRB_RE = re.compile(r"ltrb=\(([-0-9]+),([-0-9]+),([-0-9]+),([-0-9]+)\)")
SRC_LTRB_RE = re.compile(r"src_ltrb=\(([-0-9]+),([-0-9]+),([-0-9]+),([-0-9]+)\)")
DST_LTRB_RE = re.compile(r"dst_ltrb=\(([-0-9]+),([-0-9]+),([-0-9]+),([-0-9]+)\)")
SIZE_RE = re.compile(r"size=\(([-0-9]+),([-0-9]+)\)")
SRCSZ_RE = re.compile(r"srcsz=\(([-0-9]+),([-0-9]+)\)")
DSTSZ_RE = re.compile(r"dstsz=\(([-0-9]+),([-0-9]+)\)")


def parse_int(value: str) -> int | str:
    text = value.strip().rstrip(",")
    try:
        if text.lower().startswith("0x"):
            return int(text, 16)
        return int(text, 10)
    except ValueError:
        return text


def parse_pairs(line: str) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for key, value in KEY_VALUE_RE.findall(line):
        if value.startswith("("):
            continue
        values[key] = parse_int(value)
    return values


def parse_rect(regex: re.Pattern[str], line: str) -> list[int] | None:
    match = regex.search(line)
    if not match:
        return None
    return [int(part) for part in match.groups()]


def parse_size(regex: re.Pattern[str], line: str) -> list[int] | None:
    match = regex.search(line)
    if not match:
        return None
    return [int(part) for part in match.groups()]


def parse_log(path: Path) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    sample_values: dict[str, Counter[int]] = defaultdict(Counter)
    call_counts: Counter[str] = Counter()
    rect_counts: Counter[tuple[int, int, int, int]] = Counter()

    for line_no, raw in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
        line = raw.strip()
        kind = None
        if line.startswith("PLAYGAME "):
            kind = "PLAYGAME"
        elif line.startswith("FULLREDRAW_ENTER "):
            kind = "FULLREDRAW_ENTER"
        elif line.startswith("TOPSRC_BEFORE "):
            kind = "TOPSRC_BEFORE"
        elif line.startswith("TOPSRC_AFTER "):
            kind = "TOPSRC_AFTER"
        elif line.startswith("TOPBAND_PRESENT "):
            kind = "TOPBAND_PRESENT"
        elif line.startswith("TOPBAND_WRITE "):
            kind = "TOPBAND_WRITE"
        elif line == "AV_MAP_TOPBAND":
            kind = "AV_MAP_TOPBAND"
        if not kind:
            continue

        row = {"line_no": line_no, "kind": kind}
        row.update(parse_pairs(line))
        if size := parse_size(SIZE_RE, line):
            row["size"] = size
        if srcsz := parse_size(SRCSZ_RE, line):
            row["srcsz"] = srcsz
        if dstsz := parse_size(DSTSZ_RE, line):
            row["dstsz"] = dstsz
        if ltrb := parse_rect(LTRB_RE, line):
            row["ltrb"] = ltrb
            rect_counts[tuple(ltrb)] += 1
        if src_ltrb := parse_rect(SRC_LTRB_RE, line):
            row["src_ltrb"] = src_ltrb
        if dst_ltrb := parse_rect(DST_LTRB_RE, line):
            row["dst_ltrb"] = dst_ltrb

        if kind in {"TOPSRC_BEFORE", "TOPSRC_AFTER"}:
            for key, value in row.items():
                if key.startswith("s") and isinstance(value, int):
                    sample_values[f"{kind}:{key}"][value] += 1
        if kind in {"TOPBAND_PRESENT", "TOPBAND_WRITE"} and "call" in row:
            call_counts[str(row["call"])] += 1
        rows.append(row)

    sample_summary = {}
    for key, counts in sorted(sample_values.items()):
        total = sum(counts.values())
        sample_summary[key] = {
            "total": total,
            "zero": counts.get(0, 0),
            "zero_percent": round((counts.get(0, 0) * 100.0) / total, 3) if total else 0.0,
            "values": [{"value": value, "count": count} for value, count in counts.most_common()],
        }

    interesting_rows = [row for row in rows if row["kind"] in {"PLAYGAME", "FULLREDRAW_ENTER"}][:8]
    interesting_rows.extend([row for row in rows if row["kind"].startswith("TOPSRC_")][:6])
    interesting_rows.extend([row for row in rows if row["kind"] in {"TOPBAND_PRESENT", "TOPBAND_WRITE"}][:8])

    return {
        "log": str(path),
        "rows": len(rows),
        "counts": dict(Counter(row["kind"] for row in rows)),
        "call_counts": [{"call": call, "count": count} for call, count in call_counts.most_common()],
        "rect_counts": [
            {"ltrb": list(rect), "count": count}
            for rect, count in rect_counts.most_common(20)
        ],
        "sample_summary": sample_summary,
        "first_rows": interesting_rows,
        "av_rows": sum(1 for row in rows if row["kind"] == "AV_MAP_TOPBAND"),
    }


def print_summary(summary: dict[str, Any]) -> None:
    print(f"log: {summary['log']}")
    print("counts: " + ", ".join(f"{key}={value}" for key, value in summary["counts"].items()))
    print("top calls: " + ", ".join(f"{item['call']}:{item['count']}" for item in summary["call_counts"][:5]))
    for key, item in summary["sample_summary"].items():
        if key.endswith(("s672_16", "s736_16", "s672_80", "s736_80", "s672_144", "s736_144")):
            print(f"{key}: zero={item['zero']}/{item['total']} ({item['zero_percent']}%)")
    print(f"av_rows: {summary['av_rows']}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log", type=Path)
    parser.add_argument("--write-json", type=Path)
    args = parser.parse_args()

    summary = parse_log(args.log)
    if args.write_json:
        args.write_json.parent.mkdir(parents=True, exist_ok=True)
        args.write_json.write_text(json.dumps(summary, indent=2), encoding="ascii")
    print_summary(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
