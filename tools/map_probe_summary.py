#!/usr/bin/env python3
"""Summarize Clash95 CDB gameplay-map runtime probe logs."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


PLAYGAME_RE = re.compile(
    r"PLAYGAME gd=(?P<gd>\S+) map=\((?P<mapw>-?\d+),(?P<maph>-?\d+)\) "
    r"scroll=\((?P<scrollx>-?\d+),(?P<scrolly>-?\d+)\) player=(?P<player>-?\d+) "
    r"selected=(?P<selected>-?\d+) mission=(?P<mission>-?\d+) turn=(?P<turn>-?\d+)"
)
LOADSAVE_RE = re.compile(r"LOADSAVE slot=(?P<slot>-?\d+) gd=(?P<gd>\S+)")
LOADMAP_RE = re.compile(r"LOADMAP arg=(?P<arg>\S+) gd=(?P<gd>\S+)")
MAP_REDRAW_RE = re.compile(
    r"MAP_REDRAW seq=(?P<seq>\d+) gd=(?P<gd>\S+) "
    r"scroll=\((?P<scrollx>-?\d+),(?P<scrolly>-?\d+)\) "
    r"map=\((?P<mapw>-?\d+),(?P<maph>-?\d+)\) "
    r"end12=\((?P<end12x>-?\d+),(?P<end12y>-?\d+)\) "
    r"end9=\((?P<end9x>-?\d+),(?P<end9y>-?\d+)\) "
    r"player=(?P<player>-?\d+) selected=(?P<selected>-?\d+) "
    r"fog=(?P<fog>-?\d+) mission=(?P<mission>-?\d+) turn=(?P<turn>-?\d+)"
)
MAP_SCROLL_RE = re.compile(
    r"MAP_SCROLLHELPER seq=(?P<seq>\d+) gd=(?P<gd>\S+) "
    r"scroll=\((?P<scrollx>-?\d+),(?P<scrolly>-?\d+)\) "
    r"map=\((?P<mapw>-?\d+),(?P<maph>-?\d+)\) "
    r"mouse=\((?P<mousex>-?\d+),(?P<mousey>-?\d+)\)"
)
MAP_REPAINT_RE = re.compile(
    r"MAP_REPAINT seq=(?P<seq>\d+) gd=(?P<gd>\S+) "
    r"scroll=\((?P<scrollx>-?\d+),(?P<scrolly>-?\d+)\) "
    r"map=\((?P<mapw>-?\d+),(?P<maph>-?\d+)\) "
    r"eax=(?P<eax>\S+) ebx=(?P<ebx>\S+) ecx=(?P<ecx>\S+) edx=(?P<edx>\S+)"
)
COPY_PRE_RE = re.compile(
    r"COPY_PRE seq=(?P<seq>\d+) ebp=(?P<ebp>\S+) obj=(?P<obj>\S+) "
    r"objvt=(?P<objvt>\S+) srcbase=(?P<srcbase>\S+) dst_eax=(?P<dst_eax>\S+) "
    r"src_esi=(?P<src_esi>\S+) len_ebx=(?P<len_ebx>-?\d+) copy_ecx=(?P<copy_ecx>-?\d+) "
    r"dst_end=(?P<dst_end>\S+) src_end=(?P<src_end>\S+) "
    r"scratchvt=(?P<scratchvt>\S+) scratchobj=(?P<scratchobj>\S+)"
)
COPY_EXEC_RE = re.compile(
    r"COPY_EXEC seq=(?P<seq>\d+) ebp=(?P<ebp>\S+) obj=(?P<obj>\S+) "
    r"objvt=(?P<objvt>\S+) dst_edi=(?P<dst_edi>\S+) src_esi=(?P<src_esi>\S+) "
    r"len_eax=(?P<len_eax>-?\d+) dwords_ecx=(?P<dwords_ecx>-?\d+) "
    r"dst_end=(?P<dst_end>\S+) src_end=(?P<src_end>\S+) "
    r"scratchvt=(?P<scratchvt>\S+) scratchobj=(?P<scratchobj>\S+)"
)
COPY_STATE_RE = re.compile(
    r"COPY_STATE ebp=(?P<ebp>\S+) dst_edi=(?P<dst_edi>\S+) "
    r"src_esi=(?P<src_esi>\S+) len_eax=(?P<len_eax>-?\d+) "
    r"dwords_ecx=(?P<dwords_ecx>-?\d+) edx=(?P<edx>\S+) "
    r"obj_local=(?P<obj_local>\S+) src_local=(?P<src_local>\S+)"
)
OBJ_STATE_RE = re.compile(
    r"OBJ_STATE obj=(?P<obj>[0-9a-fA-F]{8}) objvt=(?P<objvt>[0-9a-fA-F]{8}) "
    r"obj_cursor=(?P<obj_cursor>[0-9a-fA-F]{8}) obj_aux=(?P<obj_aux>[0-9a-fA-F]{8}) "
    r"scratch_obj=(?P<scratch_obj>[0-9a-fA-F]{8}) scratchvt=(?P<scratchvt>[0-9a-fA-F]{8}) "
    r"scratch_p4=(?P<scratch_p4>[0-9a-fA-F]{8}) scratch_p8=(?P<scratch_p8>[0-9a-fA-F]{8})"
)
COPY_DIFF_RE = re.compile(
    r"COPY_DIFF dst_minus_obj_cursor=(?P<dst_minus_obj_cursor>-?\d+) "
    r"dst_minus_scratch_p4=(?P<dst_minus_scratch_p4>-?\d+) "
    r"dst_minus_scratch_p8=(?P<dst_minus_scratch_p8>-?\d+)"
)
STREAM_RE = re.compile(
    r"STREAM_(?P<kind>[AB]) seq=(?P<seq>\d+) obj=(?P<obj>\S+) "
    r"surf=(?P<surf>\S+) width=(?P<width>-?\d+) height=(?P<height>-?\d+) "
    r"base=(?P<base>\S+) row=(?P<row>-?\d+) x=(?P<x>-?\d+) "
    r"cursor=(?P<cursor>\S+)"
)
SCROLL_RESTORE_RE = re.compile(
    r"SCROLL_RESTORE before=\((?P<beforex>-?\d+),(?P<beforey>-?\d+)\) "
    r"max=\((?P<maxx>-?\d+),(?P<maxy>-?\d+)\) "
    r"map=\((?P<mapw>-?\d+),(?P<maph>-?\d+)\)"
)
SCROLL_RESTORE_CLAMP_RE = re.compile(
    r"SCROLL_RESTORE_CLAMP after=\((?P<afterx>-?\d+),(?P<aftery>-?\d+)\)"
)
ACCESS_VIOLATION_RE = re.compile(
    r"Access violation - code (?P<code>[0-9a-fA-F]+) \((?P<chance>[^)]+)\)"
)
EXCEPTION_ADDRESS_RE = re.compile(
    r"ExceptionAddress: (?P<address>[0-9a-fA-F]+) \((?P<symbol>[^)]+)\)"
)
WRITE_ADDRESS_RE = re.compile(r"Attempt to write to address (?P<address>[0-9a-fA-F]+)")
EIP_RE = re.compile(r"eip=(?P<eip>[0-9a-fA-F]+)")


INT_FIELDS = {
    "seq",
    "slot",
    "mapw",
    "maph",
    "scrollx",
    "scrolly",
    "end12x",
    "end12y",
    "end9x",
    "end9y",
    "player",
    "selected",
    "mission",
    "turn",
    "fog",
    "mousex",
    "mousey",
    "width",
    "height",
    "row",
    "x",
    "beforex",
    "beforey",
    "maxx",
    "maxy",
    "afterx",
    "aftery",
    "len_ebx",
    "copy_ecx",
    "len_eax",
    "dwords_ecx",
    "dst_minus_obj_cursor",
    "dst_minus_scratch_p4",
    "dst_minus_scratch_p8",
}


def convert(match: re.Match[str], line_no: int) -> dict:
    row: dict[str, int | str] = {"line_no": line_no}
    for key, value in match.groupdict().items():
        row[key] = int(value) if key in INT_FIELDS else value
    return row


def parse_rows(text: str) -> dict[str, list[dict]]:
    rows = {
        "loadsave": [],
        "loadmap": [],
        "playgame": [],
        "redraw": [],
        "scroll": [],
        "repaint": [],
        "copy_pre": [],
        "copy_exec": [],
        "copy_state": [],
        "obj_state": [],
        "copy_diff": [],
        "stream": [],
        "restore": [],
        "restore_clamp": [],
        "exceptions": [],
        "exception_addresses": [],
        "write_addresses": [],
        "eip": [],
    }
    patterns = [
        ("loadsave", LOADSAVE_RE),
        ("loadmap", LOADMAP_RE),
        ("playgame", PLAYGAME_RE),
        ("redraw", MAP_REDRAW_RE),
        ("scroll", MAP_SCROLL_RE),
        ("repaint", MAP_REPAINT_RE),
        ("copy_pre", COPY_PRE_RE),
        ("copy_exec", COPY_EXEC_RE),
        ("copy_state", COPY_STATE_RE),
        ("obj_state", OBJ_STATE_RE),
        ("copy_diff", COPY_DIFF_RE),
        ("stream", STREAM_RE),
        ("restore", SCROLL_RESTORE_RE),
        ("restore_clamp", SCROLL_RESTORE_CLAMP_RE),
    ]
    for line_no, line in enumerate(text.splitlines(), start=1):
        for kind, pattern in patterns:
            match = pattern.search(line)
            if match:
                rows[kind].append(convert(match, line_no))
                break
        av_match = ACCESS_VIOLATION_RE.search(line)
        if av_match:
            rows["exceptions"].append(
                {
                    "line_no": line_no,
                    "code": av_match.group("code").lower(),
                    "chance": av_match.group("chance"),
                }
            )
        exception_address_match = EXCEPTION_ADDRESS_RE.search(line)
        if exception_address_match:
            rows["exception_addresses"].append(
                {
                    "line_no": line_no,
                    "address": exception_address_match.group("address").lower(),
                    "symbol": exception_address_match.group("symbol"),
                }
            )
        write_address_match = WRITE_ADDRESS_RE.search(line)
        if write_address_match:
            rows["write_addresses"].append(
                {
                    "line_no": line_no,
                    "address": write_address_match.group("address").lower(),
                }
            )
        eip_match = EIP_RE.search(line)
        if eip_match:
            rows["eip"].append({"line_no": line_no, "eip": eip_match.group("eip").lower()})
    return rows


def range_for(rows: list[dict], field: str) -> dict[str, int] | None:
    values = [int(row[field]) for row in rows if field in row]
    if not values:
        return None
    return {"min": min(values), "max": max(values), "unique": len(set(values))}


def hex_int(value: str) -> int:
    return int(value, 16)


def copy_group_summary(rows: list[dict], dst_field: str, len_field: str) -> list[dict]:
    groups: dict[tuple[str, str], dict] = {}
    for row in rows:
        key = (str(row.get("obj", "")), str(row.get("objvt", "")))
        dst = hex_int(str(row[dst_field]))
        dst_end = hex_int(str(row["dst_end"]))
        length = int(row[len_field])
        group = groups.setdefault(
            key,
            {
                "obj": key[0],
                "objvt": key[1],
                "count": 0,
                "first_seq": row["seq"],
                "last_seq": row["seq"],
                "dst_min": dst,
                "dst_max": dst,
                "dst_end_max": dst_end,
                "len_min": length,
                "len_max": length,
                "length_counts": {},
            },
        )
        group["count"] += 1
        group["last_seq"] = row["seq"]
        group["dst_min"] = min(group["dst_min"], dst)
        group["dst_max"] = max(group["dst_max"], dst)
        group["dst_end_max"] = max(group["dst_end_max"], dst_end)
        group["len_min"] = min(group["len_min"], length)
        group["len_max"] = max(group["len_max"], length)
        group["length_counts"][length] = group["length_counts"].get(length, 0) + 1

    summaries = []
    for group in groups.values():
        group = dict(group)
        group["dst_min_hex"] = f"{group['dst_min']:08x}"
        group["dst_max_hex"] = f"{group['dst_max']:08x}"
        group["dst_end_max_hex"] = f"{group['dst_end_max']:08x}"
        group["length_counts"] = [
            {"length": length, "count": count}
            for length, count in sorted(
                group["length_counts"].items(), key=lambda item: (-item[1], item[0])
            )[:12]
        ]
        summaries.append(group)
    return sorted(summaries, key=lambda item: (-item["count"], item["obj"], item["objvt"]))


def stream_group_summary(rows: list[dict]) -> list[dict]:
    groups: dict[tuple[str, int, int, str], dict] = {}
    for row in rows:
        cursor = hex_int(str(row["cursor"]))
        key = (str(row["surf"]), int(row["width"]), int(row["height"]), str(row["base"]))
        group = groups.setdefault(
            key,
            {
                "surf": key[0],
                "width": key[1],
                "height": key[2],
                "base": key[3],
                "count": 0,
                "first_seq": row["seq"],
                "last_seq": row["seq"],
                "cursor_min": cursor,
                "cursor_max": cursor,
                "row_min": int(row["row"]),
                "row_max": int(row["row"]),
                "x_min": int(row["x"]),
                "x_max": int(row["x"]),
                "kinds": {},
                "objects": {},
            },
        )
        group["count"] += 1
        group["last_seq"] = row["seq"]
        group["cursor_min"] = min(group["cursor_min"], cursor)
        group["cursor_max"] = max(group["cursor_max"], cursor)
        group["row_min"] = min(group["row_min"], int(row["row"]))
        group["row_max"] = max(group["row_max"], int(row["row"]))
        group["x_min"] = min(group["x_min"], int(row["x"]))
        group["x_max"] = max(group["x_max"], int(row["x"]))
        group["kinds"][row["kind"]] = group["kinds"].get(row["kind"], 0) + 1
        group["objects"][row["obj"]] = group["objects"].get(row["obj"], 0) + 1

    summaries = []
    for group in groups.values():
        group = dict(group)
        group["cursor_min_hex"] = f"{group['cursor_min']:08x}"
        group["cursor_max_hex"] = f"{group['cursor_max']:08x}"
        group["kinds"] = [
            {"kind": kind, "count": count}
            for kind, count in sorted(group["kinds"].items(), key=lambda item: item[0])
        ]
        group["objects"] = [
            {"obj": obj, "count": count}
            for obj, count in sorted(
                group["objects"].items(), key=lambda item: (-item[1], item[0])
            )[:8]
        ]
        summaries.append(group)
    return sorted(summaries, key=lambda item: (-item["count"], item["surf"], item["base"]))


def expected_tile_counts(expected_tiles: dict | None) -> tuple[int, int] | None:
    if not expected_tiles:
        return None
    try:
        return int(expected_tiles["x"]), int(expected_tiles["y"])
    except (KeyError, TypeError, ValueError):
        return None


def edge_overruns(rows: list[dict], expected_tiles: dict | None) -> list[dict]:
    tile_counts = expected_tile_counts(expected_tiles)
    if not tile_counts:
        return []
    tiles_x, tiles_y = tile_counts
    overruns = []
    for row in rows:
        mapw = int(row["mapw"])
        maph = int(row["maph"])
        scrollx = int(row["scrollx"])
        scrolly = int(row["scrolly"])
        max_scrollx = max(0, mapw - tiles_x)
        max_scrolly = max(0, maph - tiles_y)
        overrun_x = scrollx + tiles_x > mapw
        overrun_y = scrolly + tiles_y > maph
        if overrun_x or overrun_y:
            overruns.append(
                {
                    "line_no": row["line_no"],
                    "seq": row.get("seq"),
                    "scroll": {"x": scrollx, "y": scrolly},
                    "map": {"x": mapw, "y": maph},
                    "expected_visible_tiles": {"x": tiles_x, "y": tiles_y},
                    "expected_max_scroll": {"x": max_scrollx, "y": max_scrolly},
                    "overrun": {
                        "x": max(0, scrollx + tiles_x - mapw),
                        "y": max(0, scrolly + tiles_y - maph),
                    },
                }
            )
    return overruns


def summarize(log: Path, patch_report: Path | None) -> dict:
    rows = parse_rows(log.read_text(encoding="utf-8", errors="replace"))
    patch = json.loads(patch_report.read_text(encoding="ascii")) if patch_report else None
    expected_tiles = patch.get("map", {}).get("visible_tiles") if patch else None
    redraw = rows["redraw"]
    overruns = edge_overruns(redraw, expected_tiles)
    summary = {
        "log": str(log),
        "patch_report": str(patch_report) if patch_report else None,
        "expected_visible_tiles": expected_tiles,
        "loadsave_rows": len(rows["loadsave"]),
        "loadmap_rows": len(rows["loadmap"]),
        "playgame_rows": len(rows["playgame"]),
        "redraw_rows": len(redraw),
        "scroll_rows": len(rows["scroll"]),
        "repaint_rows": len(rows["repaint"]),
        "copy_pre_rows": len(rows["copy_pre"]),
        "copy_exec_rows": len(rows["copy_exec"]),
        "copy_state_rows": len(rows["copy_state"]),
        "obj_state_rows": len(rows["obj_state"]),
        "copy_diff_rows": len(rows["copy_diff"]),
        "stream_rows": len(rows["stream"]),
        "first_stream": rows["stream"][:1],
        "last_stream": rows["stream"][-1:] if rows["stream"] else [],
        "stream_groups": stream_group_summary(rows["stream"]),
        "first_copy_pre": rows["copy_pre"][:1],
        "last_copy_pre": rows["copy_pre"][-1:] if rows["copy_pre"] else [],
        "first_copy_exec": rows["copy_exec"][:1],
        "last_copy_exec": rows["copy_exec"][-1:] if rows["copy_exec"] else [],
        "last_copy_state": rows["copy_state"][-1:] if rows["copy_state"] else [],
        "last_obj_state": rows["obj_state"][-1:] if rows["obj_state"] else [],
        "last_copy_diff": rows["copy_diff"][-1:] if rows["copy_diff"] else [],
        "copy_pre_groups": copy_group_summary(rows["copy_pre"], "dst_eax", "len_ebx"),
        "copy_exec_groups": copy_group_summary(rows["copy_exec"], "dst_edi", "len_eax"),
        "restore_rows": len(rows["restore"]),
        "restore_clamp_rows": len(rows["restore_clamp"]),
        "first_restore": rows["restore"][:1],
        "first_restore_clamp": rows["restore_clamp"][:1],
        "exception_rows": len(rows["exceptions"]),
        "first_exception": rows["exceptions"][:1],
        "last_exception": rows["exceptions"][-1:] if rows["exceptions"] else [],
        "last_exception_address": rows["exception_addresses"][-1:] if rows["exception_addresses"] else [],
        "last_write_address": rows["write_addresses"][-1:] if rows["write_addresses"] else [],
        "last_eip": rows["eip"][-1:] if rows["eip"] else [],
        "map_entered": bool(rows["playgame"] or redraw),
        "redraw_hit": bool(redraw),
        "first_loadsave": rows["loadsave"][:1],
        "first_loadmap": rows["loadmap"][:1],
        "first_playgame": rows["playgame"][:1],
        "first_redraw": redraw[:1],
        "last_redraw": redraw[-1:] if redraw else [],
        "scrollx_range": range_for(redraw, "scrollx"),
        "scrolly_range": range_for(redraw, "scrolly"),
        "mapw_range": range_for(redraw, "mapw"),
        "maph_range": range_for(redraw, "maph"),
        "edge_overrun_rows": len(overruns),
        "first_edge_overrun": overruns[:1],
        "last_edge_overrun": overruns[-1:] if overruns else [],
    }
    if expected_tiles:
        summary["static_patch_expects_12x9"] = expected_tiles == {"x": 12, "y": 9}
    return summary


def print_summary(summary: dict) -> None:
    print(f"log: {summary['log']}")
    print(f"patch_report: {summary['patch_report']}")
    print(
        "rows: loadsave={loadsave_rows} loadmap={loadmap_rows} playgame={playgame_rows} "
        "redraw={redraw_rows} scroll={scroll_rows} repaint={repaint_rows}".format(**summary)
    )
    print(f"map_entered: {summary['map_entered']}")
    print(f"redraw_hit: {summary['redraw_hit']}")
    print(f"expected_visible_tiles: {summary['expected_visible_tiles']}")
    if summary["first_loadsave"]:
        print(f"first_loadsave: {summary['first_loadsave'][0]}")
    if summary["first_playgame"]:
        print(f"first_playgame: {summary['first_playgame'][0]}")
    if summary["first_redraw"]:
        print(f"first_redraw: {summary['first_redraw'][0]}")
    if summary["last_redraw"]:
        print(f"last_redraw: {summary['last_redraw'][0]}")
    print(
        "copy_rows: pre={copy_pre_rows} exec={copy_exec_rows} "
        "state={copy_state_rows} obj_state={obj_state_rows} diff={copy_diff_rows}".format(
            **summary
        )
    )
    print(f"stream_rows: {summary['stream_rows']}")
    if summary["last_stream"]:
        print(f"last_stream: {summary['last_stream'][0]}")
    for group in summary.get("stream_groups", [])[:3]:
        print(
            f"stream_group: surf={group['surf']} size={group['width']}x{group['height']} "
            f"base={group['base']} count={group['count']} seq={group['first_seq']}..{group['last_seq']} "
            f"cursor={group['cursor_min_hex']}..{group['cursor_max_hex']} "
            f"row={group['row_min']}..{group['row_max']} x={group['x_min']}..{group['x_max']} "
            f"kinds={group['kinds']} objects={group['objects'][:3]}"
        )
    if summary["last_copy_pre"]:
        print(f"last_copy_pre: {summary['last_copy_pre'][0]}")
    if summary["last_copy_exec"]:
        print(f"last_copy_exec: {summary['last_copy_exec'][0]}")
    if summary["last_copy_state"]:
        print(f"last_copy_state: {summary['last_copy_state'][0]}")
    if summary["last_obj_state"]:
        print(f"last_obj_state: {summary['last_obj_state'][0]}")
    if summary["last_copy_diff"]:
        print(f"last_copy_diff: {summary['last_copy_diff'][0]}")
    for label in ("copy_pre_groups", "copy_exec_groups"):
        groups = summary.get(label, [])
        if groups:
            group = groups[0]
            print(
                f"{label}[0]: obj={group['obj']} objvt={group['objvt']} "
                f"count={group['count']} seq={group['first_seq']}..{group['last_seq']} "
                f"dst={group['dst_min_hex']}..{group['dst_end_max_hex']} "
                f"len={group['len_min']}..{group['len_max']} top_lengths={group['length_counts'][:4]}"
            )
    if summary["first_restore"]:
        print(f"first_restore: {summary['first_restore'][0]}")
    if summary["first_restore_clamp"]:
        print(f"first_restore_clamp: {summary['first_restore_clamp'][0]}")
    print(f"edge_overrun_rows: {summary['edge_overrun_rows']}")
    if summary["first_edge_overrun"]:
        print(f"first_edge_overrun: {summary['first_edge_overrun'][0]}")
    print(f"exception_rows: {summary['exception_rows']}")
    if summary["last_exception"]:
        print(f"last_exception: {summary['last_exception'][0]}")
    if summary["last_exception_address"]:
        print(f"last_exception_address: {summary['last_exception_address'][0]}")
    if summary["last_write_address"]:
        print(f"last_write_address: {summary['last_write_address'][0]}")
    if summary["last_eip"]:
        print(f"last_eip: {summary['last_eip'][0]}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize a Clash95 CDB gameplay-map runtime probe.")
    parser.add_argument("log", type=Path)
    parser.add_argument("--patch-report", type=Path)
    parser.add_argument("--write-json", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary = summarize(args.log, args.patch_report)
    if args.write_json:
        args.write_json.parent.mkdir(parents=True, exist_ok=True)
        args.write_json.write_text(json.dumps(summary, indent=2), encoding="ascii")
    print_summary(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
