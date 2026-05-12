#!/usr/bin/env python3
"""Classify Clash95 tile-coverage blanks using CDB visibility evidence.

`tools/map_tile_coverage.py` is intentionally image-only, so palette-1 fog can
look like a render gap. This helper joins its JSON output with CDB visibility
probe logs and reports which blank cells are explained by the game's own
visibility/fog path.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


VIS_RE = re.compile(
    r"(?P<prefix>BRANCH_VIS|POSTTILE_VIS|VISRET|R8VISRET|SCROLL_VISRET|SURFDUMP_VEDGE_VISRET) "
    r"seq=(?P<seq>-?\d+) "
    r"(?:xy|screen)=\((?P<x>-?\d+),(?P<y>-?\d+)\) "
    r"(?:map|center)=\((?P<mx>-?\d+),(?P<my>-?\d+)\) "
    r"vis=(?P<vis>-?\d+)"
)
CLIP_RE = re.compile(
    r"(?P<prefix>BRANCH_CLIP|POSTTILE_CLIP|R8CLIP|SCROLL_CLIP) "
    r"seq=(?P<seq>-?\d+) "
    r"(?:xy|screen)=\((?P<x>-?\d+),(?P<y>-?\d+)\) "
    r"clip=(?P<clip>-?\d+)"
)
CLEAR_RE = re.compile(
    r"(?P<prefix>BRANCH_CLEAR|POSTTILE_CLEAR|R8CLEAR|SCROLL_CLEAR|SURFDUMP_VEDGE_CLEAR) "
    r"seq=(?P<seq>-?\d+) "
    r"(?:xy|screen)=\((?P<x>-?\d+),(?P<y>-?\d+)\)"
)
POST_RE = re.compile(
    r"(?P<prefix>BRANCH_POST|POSTTILE_POST|R8POST|SCROLL_POST|SURFDUMP_VEDGE_POST) "
    r"seq=(?P<seq>-?\d+) "
    r".*?(?:xy|screen)=\((?P<x>-?\d+),(?P<y>-?\d+)\) "
    r"sample=(?P<sample>[0-9a-fA-F]{2})"
)
NBR_RE = re.compile(
    r"(?P<prefix>VISNBR|R8NBR|SCROLL_NBR) "
    r"seq=(?P<seq>-?\d+) "
    r"idx=(?P<idx>\d+) "
    r"screen=\((?P<x>-?\d+),(?P<y>-?\d+)\) "
    r"center=\((?P<mx>-?\d+),(?P<my>-?\d+)\) "
    r"args=\((?P<nx>-?\d+),(?P<ny>-?\d+),p(?P<player>-?\d+)\) "
    r"byte=(?P<byte>[0-9a-fA-F]{2}) "
    r"mask=(?P<mask>[0-9a-fA-F]{2}) "
    r"hit=(?P<hit>[0-9a-fA-F]{2})"
)
VISDUMP_RE = re.compile(
    r"SCROLL_VISDUMP "
    r"player=(?P<player>-?\d+) "
    r"screen0=\((?P<x>-?\d+),(?P<y>-?\d+)\) "
    r"map0=\((?P<mx>-?\d+),(?P<my>-?\d+)\) "
    r"rows=(?P<rows>\d+) "
    r"cols=(?P<cols>\d+) "
    r"tile=\((?P<tile_x>\d+),(?P<tile_y>\d+)\) "
    r"vis_base=(?P<vis_base>[0-9a-fA-F`]+) "
    r"dump_start=(?P<dump_start>[0-9a-fA-F`]+) "
    r"count=(?P<count>\d+)"
)
APVIS_CELL_RE = re.compile(
    r"APVIS_CELL "
    r"id=(?P<id>\S+) "
    r"screen=\((?P<x>-?\d+),(?P<y>-?\d+)\) "
    r"map=\((?P<mx>-?\d+),(?P<my>-?\d+)\) "
    r"byte=(?P<byte>[0-9a-fA-F]{2}) "
    r"mask=(?P<mask>[0-9a-fA-F]{2}) "
    r"hit=(?P<hit>[0-9a-fA-F]{2}) "
    r"sample=(?P<sample>[0-9a-fA-F]{2}) "
    r"center_sample=(?P<center>[0-9a-fA-F]{2})"
)
DB_RE = re.compile(
    r"^\s*(?P<addr>[0-9a-fA-F`]{8,17})\s+"
    r"(?P<bytes>[0-9a-fA-F]{2}(?:[ -][0-9a-fA-F]{2}){0,15})"
)


@dataclass
class Observation:
    x: int
    y: int
    seqs: set[int] = field(default_factory=set)
    map_points: set[tuple[int, int]] = field(default_factory=set)
    vis_values: list[int] = field(default_factory=list)
    clips: list[int] = field(default_factory=list)
    clear_count: int = 0
    post_samples: list[str] = field(default_factory=list)
    neighbor_checks: int = 0
    neighbor_hits: int = 0
    sources: set[str] = field(default_factory=set)

    def add_source(self, path: Path) -> None:
        self.sources.add(str(path))

    @property
    def any_vis_zero(self) -> bool:
        return any(value == 0 for value in self.vis_values)

    @property
    def any_vis_nonzero(self) -> bool:
        return any(value != 0 for value in self.vis_values)

    @property
    def any_clip_nonzero(self) -> bool:
        return any(value != 0 for value in self.clips)

    @property
    def all_neighbors_miss(self) -> bool:
        return self.neighbor_checks > 0 and self.neighbor_hits == 0


def parse_int(match: re.Match[str], name: str) -> int:
    return int(match.group(name), 10)


def parse_hex(value: str) -> int:
    return int(value.replace("`", ""), 16)


def observation_for(observations: dict[tuple[int, int], Observation], x: int, y: int) -> Observation:
    key = (x, y)
    if key not in observations:
        observations[key] = Observation(x=x, y=y)
    return observations[key]


def parse_db_dump(lines: list[str], start_index: int, count: int) -> dict[int, int]:
    memory: dict[int, int] = {}
    for line in lines[start_index:]:
        match = DB_RE.match(line)
        if not match:
            if memory:
                break
            continue
        address = parse_hex(match.group("addr"))
        for offset, token in enumerate(re.findall(r"[0-9a-fA-F]{2}", match.group("bytes"))):
            memory[address + offset] = int(token, 16)
            if len(memory) >= count:
                return memory
    return memory


def expand_visdump(
    observations: dict[tuple[int, int], Observation],
    match: re.Match[str],
    lines: list[str],
    line_index: int,
    path: Path,
) -> None:
    player = parse_int(match, "player")
    screen_x = parse_int(match, "x")
    screen_y = parse_int(match, "y")
    map_x0 = parse_int(match, "mx")
    map_y0 = parse_int(match, "my")
    rows = parse_int(match, "rows")
    cols = parse_int(match, "cols")
    tile_x = parse_int(match, "tile_x")
    tile_y = parse_int(match, "tile_y")
    vis_base = parse_hex(match.group("vis_base"))
    count = parse_int(match, "count")
    memory = parse_db_dump(lines, line_index + 1, count)
    seq = 0
    for row in range(rows):
        for col in range(cols):
            map_x = map_x0 + col
            map_y = map_y0 + row
            address = vis_base + (player * 1423) + (map_x * 13) + (map_y >> 3)
            if address not in memory:
                seq += 1
                continue
            vis_value = memory[address] & (1 << (map_y & 7))
            obs = observation_for(observations, screen_x + (col * tile_x), screen_y + (row * tile_y))
            obs.seqs.add(seq)
            obs.map_points.add((map_x, map_y))
            obs.vis_values.append(vis_value)
            obs.add_source(path)
            seq += 1


def parse_logs(paths: list[Path]) -> dict[tuple[int, int], Observation]:
    observations: dict[tuple[int, int], Observation] = {}
    for path in paths:
        text = path.read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines()
        for line_index, line in enumerate(lines):
            if match := VIS_RE.search(line):
                x = parse_int(match, "x")
                y = parse_int(match, "y")
                obs = observation_for(observations, x, y)
                obs.seqs.add(parse_int(match, "seq"))
                obs.map_points.add((parse_int(match, "mx"), parse_int(match, "my")))
                obs.vis_values.append(parse_int(match, "vis"))
                obs.add_source(path)
                continue
            if match := CLIP_RE.search(line):
                obs = observation_for(observations, parse_int(match, "x"), parse_int(match, "y"))
                obs.seqs.add(parse_int(match, "seq"))
                obs.clips.append(parse_int(match, "clip"))
                obs.add_source(path)
                continue
            if match := CLEAR_RE.search(line):
                obs = observation_for(observations, parse_int(match, "x"), parse_int(match, "y"))
                obs.seqs.add(parse_int(match, "seq"))
                obs.clear_count += 1
                obs.add_source(path)
                continue
            if match := POST_RE.search(line):
                obs = observation_for(observations, parse_int(match, "x"), parse_int(match, "y"))
                obs.seqs.add(parse_int(match, "seq"))
                obs.post_samples.append(match.group("sample").lower())
                obs.add_source(path)
                continue
            if match := NBR_RE.search(line):
                obs = observation_for(observations, parse_int(match, "x"), parse_int(match, "y"))
                obs.seqs.add(parse_int(match, "seq"))
                obs.map_points.add((parse_int(match, "mx"), parse_int(match, "my")))
                obs.neighbor_checks += 1
                if int(match.group("hit"), 16) != 0:
                    obs.neighbor_hits += 1
                obs.add_source(path)
                continue
            if match := VISDUMP_RE.search(line):
                expand_visdump(observations, match, lines, line_index, path)
                continue
            if match := APVIS_CELL_RE.search(line):
                obs = observation_for(observations, parse_int(match, "x"), parse_int(match, "y"))
                obs.map_points.add((parse_int(match, "mx"), parse_int(match, "my")))
                obs.vis_values.append(int(match.group("hit"), 16))
                obs.post_samples.append(match.group("sample").lower())
                obs.post_samples.append(match.group("center").lower())
                obs.add_source(path)
    return observations


def load_cells(coverage: dict[str, Any]) -> list[dict[str, Any]]:
    images = coverage.get("images") or []
    if not images:
        return []
    return list(images[0].get("cells") or [])


def observation_for_cell(
    cell: dict[str, Any],
    observations: dict[tuple[int, int], Observation],
) -> Observation | None:
    rect = cell.get("logical_rect")
    if not isinstance(rect, list) or len(rect) != 4:
        return None
    return observations.get((int(rect[0]), int(rect[1])))


def classify_cell(cell: dict[str, Any], obs: Observation | None) -> str:
    flags = set(cell.get("flags") or [])
    if "blank" not in flags:
        return "not_blank"
    if obs is None:
        return "unexplained_blank"
    if obs.any_clip_nonzero:
        return "clip_blocked"
    if obs.any_vis_zero and obs.clear_count:
        return "fog_cleared"
    if obs.any_vis_zero and obs.all_neighbors_miss:
        return "fog_zero_neighbors"
    if obs.any_vis_zero:
        return "visibility_zero"
    if obs.any_vis_nonzero:
        return "blank_despite_visible"
    return "unexplained_blank"


def summarize_observation(obs: Observation | None) -> dict[str, Any] | None:
    if obs is None:
        return None
    return {
        "screen": [obs.x, obs.y],
        "seqs": sorted(obs.seqs),
        "map_points": [list(point) for point in sorted(obs.map_points)],
        "vis_values": obs.vis_values,
        "clips": obs.clips,
        "clear_count": obs.clear_count,
        "post_samples": obs.post_samples,
        "neighbor_checks": obs.neighbor_checks,
        "neighbor_hits": obs.neighbor_hits,
        "sources": sorted(obs.sources),
    }


def build_report(coverage_path: Path, log_paths: list[Path]) -> dict[str, Any]:
    coverage = json.loads(coverage_path.read_text(encoding="utf-8"))
    observations = parse_logs(log_paths)
    cells = load_cells(coverage)
    blank_cells = [cell for cell in cells if "blank" in set(cell.get("flags") or []) and cell.get("active")]
    classified = []
    for cell in blank_cells:
        obs = observation_for_cell(cell, observations)
        status = classify_cell(cell, obs)
        classified.append(
            {
                "id": cell.get("id"),
                "logical_rect": cell.get("logical_rect"),
                "nonblack_percent": cell.get("nonblack_percent"),
                "status": status,
                "observation": summarize_observation(obs),
            }
        )
    status_counts: dict[str, int] = {}
    for row in classified:
        status_counts[row["status"]] = status_counts.get(row["status"], 0) + 1
    explained_statuses = {"fog_cleared", "fog_zero_neighbors", "visibility_zero", "clip_blocked"}
    unexplained = [row["id"] for row in classified if row["status"] not in explained_statuses]
    return {
        "coverage_json": str(coverage_path),
        "logs": [str(path) for path in log_paths],
        "observation_points": len(observations),
        "blank_cells": [cell.get("id") for cell in blank_cells],
        "status_counts": status_counts,
        "explained_blank_cells": [
            row["id"] for row in classified if row["status"] in explained_statuses
        ],
        "unexplained_blank_cells": unexplained,
        "classified_cells": classified,
    }


def print_report(report: dict[str, Any]) -> None:
    print(f"coverage: {report['coverage_json']}")
    print(f"logs: {len(report['logs'])}")
    print(f"observation_points: {report['observation_points']}")
    print("blank_cells: " + (", ".join(report["blank_cells"]) if report["blank_cells"] else "-"))
    print(
        "explained_blank_cells: "
        + (", ".join(report["explained_blank_cells"]) if report["explained_blank_cells"] else "-")
    )
    print(
        "unexplained_blank_cells: "
        + (", ".join(report["unexplained_blank_cells"]) if report["unexplained_blank_cells"] else "-")
    )
    print("status_counts:")
    for status, count in sorted(report["status_counts"].items()):
        print(f"  {status}: {count}")
    print("classified_cells:")
    for row in report["classified_cells"]:
        obs = row["observation"] or {}
        vis = ",".join(str(value) for value in obs.get("vis_values", [])) or "-"
        clear = obs.get("clear_count", 0)
        hits = obs.get("neighbor_hits", 0)
        checks = obs.get("neighbor_checks", 0)
        print(
            f"  {row['id']}: {row['status']} vis={vis} clear={clear} "
            f"neighbors={hits}/{checks}"
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("coverage_json", type=Path)
    parser.add_argument("--log", type=Path, action="append", required=True)
    parser.add_argument("--write-json", type=Path)
    parser.add_argument(
        "--require-explained",
        action="store_true",
        help="exit 2 if any blank active cell lacks visibility/clip evidence",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = build_report(args.coverage_json, args.log)
    if args.write_json:
        args.write_json.parent.mkdir(parents=True, exist_ok=True)
        args.write_json.write_text(json.dumps(report, indent=2), encoding="ascii")
    print_report(report)
    if args.require_explained and report["unexplained_blank_cells"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
