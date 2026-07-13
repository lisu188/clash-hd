#!/usr/bin/env python3
"""Summarize the hidden-CDB evidence for the chosen 800x600 HD UI layout.

The parser is repo-only: it reads an existing CDB log and never launches the
game, a debugger, or a visible process.  Its pass gate matches the markers
emitted by ``probes/cdb/ui/clash95_hd_layout_extra.cdb``.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


EXPECTED_TOOLTIP = {
    "left": 240,
    "top": 586,
    "right": 553,
    "bottom": 599,
    "width": 800,
    "height": 600,
}
EXPECTED_PANEL_COORDS = {
    0x00511D40: (608, 528),
    0x00511D75: (672, 528),
    0x00511DAA: (736, 528),
    0x00511DDF: (608, 560),
    0x00511E14: (672, 560),
    0x00511E49: (736, 560),
}
EXPECTED_CLIP = 800
EXPECTED_WIDTH = 800
EXPECTED_HEIGHT = 600
EXPECTED_HITSCAN_E0 = EXPECTED_PANEL_COORDS[0x00511D40]
EXPECTED_HITSCAN_E5 = EXPECTED_PANEL_COORDS[0x00511E49]

INT = r"-?\d+"
PTR = r"(?:0x)?[0-9a-fA-F`]+"

TOOLTIP_INIT_RE = re.compile(
    rf"HDLAYOUT_TOOLTIP_INIT\s+ret=(?P<ret>{PTR})\s+"
    rf"left=(?P<left>{INT})\s+top=(?P<top>{INT})\s+"
    rf"right=(?P<right>{INT})\s+bottom=(?P<bottom>{INT})\s+"
    rf"surface=(?P<surface>{PTR})\s+map_surface=(?P<map_surface>{PTR})\s+"
    rf"size=\((?P<width>{INT}),(?P<height>{INT})\)"
)
TOOLTIP_DRAW_RE = re.compile(
    rf"HDLAYOUT_TOOLTIP_DRAW\s+ret=(?P<ret>{PTR})\s+"
    rf"left=(?P<left>{INT})\s+top=(?P<top>{INT})\s+"
    rf"right=(?P<right>{INT})\s+bottom=(?P<bottom>{INT})\s+"
    rf"surface=(?P<surface>{PTR})\s+map_surface=(?P<map_surface>{PTR})\s+"
    rf"mouse=\((?P<mouse_x>{INT}),(?P<mouse_y>{INT})\)"
)
PANEL_SETUP_RE = re.compile(
    rf"HDLAYOUT_PANEL_SETUP\s+ret=(?P<ret>{PTR})\s+"
    rf"clip_single=(?P<clip_single>{INT})\s+clip_list=(?P<clip_list>{INT})\s+"
    rf"e0=\((?P<e0_x>{INT}),(?P<e0_y>{INT})\)\s+"
    rf"e1=\((?P<e1_x>{INT}),(?P<e1_y>{INT})\)\s+"
    rf"e2=\((?P<e2_x>{INT}),(?P<e2_y>{INT})\)\s+"
    rf"e3=\((?P<e3_x>{INT}),(?P<e3_y>{INT})\)\s+"
    rf"e4=\((?P<e4_x>{INT}),(?P<e4_y>{INT})\)\s+"
    rf"e5=\((?P<e5_x>{INT}),(?P<e5_y>{INT})\)\s+"
    rf"render=(?P<render>{PTR})\s+map_surface=(?P<map_surface>{PTR})\s+"
    rf"size=\((?P<width>{INT}),(?P<height>{INT})\)"
)
PANEL_REDRAW_INVOKE_RE = re.compile(
    rf"HDLAYOUT_PANEL_REDRAW_INVOKE\s+desc=(?P<desc>{PTR})\s+"
    rf"x=(?P<x>{INT})\s+y=(?P<y>{INT})\s+helper=(?P<helper>{PTR})\s+"
    rf"return=(?P<return>{PTR})"
)
PANEL_DRAW_RE = re.compile(
    rf"HDLAYOUT_PANEL_DRAW\s+desc=(?P<desc>{PTR})\s+"
    rf"x=(?P<x>{INT})\s+y=(?P<y>{INT})\s+flags=0x(?P<flags>[0-9a-fA-F]+)\s+"
    rf"draw=(?P<draw>{PTR})\s+hit=(?P<hit>{PTR})\s+"
    rf"render=(?P<render>{PTR})\s+map_surface=(?P<map_surface>{PTR})"
)
PANEL_REDRAW_RE = re.compile(
    rf"HDLAYOUT_PANEL_REDRAW\s+desc=(?P<desc>{PTR})\s+"
    rf"x=(?P<x>{INT})\s+y=(?P<y>{INT})\s+flags=0x(?P<flags>[0-9a-fA-F]+)\s+"
    rf"draw=(?P<draw>{PTR})\s+hit=(?P<hit>{PTR})\s+"
    rf"render=(?P<render>{PTR})\s+map_surface=(?P<map_surface>{PTR})"
)
PANEL_REDRAW_ALLOWED_RE = re.compile(
    rf"HDLAYOUT_PANEL_REDRAW_ALLOWED\s+desc=(?P<desc>{PTR})\s+"
    rf"x=(?P<x>{INT})\s+y=(?P<y>{INT})\s+clip=(?P<clip>{INT})\s+"
    rf"draw=(?P<draw>{PTR})\s+render=(?P<render>{PTR})\s+"
    rf"map_surface=(?P<map_surface>{PTR})"
)
PANEL_HITSCAN_RE = re.compile(
    rf"HDLAYOUT_PANEL_HITSCAN\s+list=(?P<list>{PTR})\s+"
    rf"mouse=\((?P<mouse_x>{INT}),(?P<mouse_y>{INT})\)\s+"
    rf"e0=\((?P<e0_x>{INT}),(?P<e0_y>{INT})\)\s+"
    rf"e5=\((?P<e5_x>{INT}),(?P<e5_y>{INT})\)"
)
ACCESS_VIOLATION_RE = re.compile(
    r"(?:\bAV_[A-Z0-9_]+\b|^\s*AV\s*$|\baccess violation\b|\bc0000005\b)",
    re.IGNORECASE,
)

POINTER_FIELDS = {
    "ret",
    "surface",
    "map_surface",
    "render",
    "desc",
    "draw",
    "hit",
    "list",
    "helper",
    "return",
}
HEX_FIELDS = {"flags"}


def _hex_value(value: str) -> int:
    return int(value.lower().replace("0x", "").replace("`", ""), 16)


def _convert(match: re.Match[str], line_no: int) -> dict[str, int]:
    row: dict[str, int] = {"line_no": line_no}
    for key, value in match.groupdict().items():
        if key in POINTER_FIELDS or key in HEX_FIELDS:
            row[key] = _hex_value(value)
        else:
            row[key] = int(value)
    return row


def parse_text(text: str) -> dict[str, list[dict[str, Any]]]:
    """Parse layout markers and access-violation markers from CDB text."""

    rows: dict[str, list[dict[str, Any]]] = {
        "tooltip_init": [],
        "tooltip_draw": [],
        "panel_setup": [],
        "panel_redraw_invoke_marker": [],
        "panel_redraw_invoke": [],
        "panel_draw": [],
        "panel_redraw": [],
        "panel_redraw_allowed": [],
        "panel_hitscan": [],
        "access_violation": [],
    }
    patterns = (
        ("tooltip_init", TOOLTIP_INIT_RE),
        ("tooltip_draw", TOOLTIP_DRAW_RE),
        ("panel_setup", PANEL_SETUP_RE),
        ("panel_redraw_invoke", PANEL_REDRAW_INVOKE_RE),
        ("panel_draw", PANEL_DRAW_RE),
        ("panel_redraw_allowed", PANEL_REDRAW_ALLOWED_RE),
        ("panel_redraw", PANEL_REDRAW_RE),
        ("panel_hitscan", PANEL_HITSCAN_RE),
    )
    for line_no, line in enumerate(text.splitlines(), start=1):
        if "HDLAYOUT_PANEL_REDRAW_INVOKE" in line:
            rows["panel_redraw_invoke_marker"].append({"line_no": line_no, "text": line.strip()})
        for bucket, pattern in patterns:
            match = pattern.search(line)
            if match:
                rows[bucket].append(_convert(match, line_no))
                break
        if ACCESS_VIOLATION_RE.search(line):
            rows["access_violation"].append({"line_no": line_no, "text": line.strip()})
    return rows


def parse_log(path: Path) -> dict[str, list[dict[str, Any]]]:
    return parse_text(path.read_text(encoding="utf-8", errors="replace"))


def _tooltip_matches(row: dict[str, Any]) -> bool:
    return all(int(row[key]) == value for key, value in EXPECTED_TOOLTIP.items())


def _setup_coords(row: dict[str, Any]) -> list[tuple[int, int]]:
    return [(int(row[f"e{index}_x"]), int(row[f"e{index}_y"])) for index in range(6)]


def _setup_matches(row: dict[str, Any]) -> bool:
    return (
        int(row["clip_single"]) == EXPECTED_CLIP
        and int(row["clip_list"]) == EXPECTED_CLIP
        and _setup_coords(row) == list(EXPECTED_PANEL_COORDS.values())
        and int(row["render"]) == int(row["map_surface"])
        and int(row["width"]) == EXPECTED_WIDTH
        and int(row["height"]) == EXPECTED_HEIGHT
    )


def _draw_matches(row: dict[str, Any]) -> bool:
    expected = EXPECTED_PANEL_COORDS.get(int(row["desc"]))
    return bool(
        expected
        and (int(row["x"]), int(row["y"])) == expected
        and int(row["render"]) == int(row["map_surface"])
    )


def _hitscan_matches(row: dict[str, Any]) -> bool:
    return (
        (int(row["e0_x"]), int(row["e0_y"])) == EXPECTED_HITSCAN_E0
        and (int(row["e5_x"]), int(row["e5_y"])) == EXPECTED_HITSCAN_E5
    )


def _redraw_invoke_matches(row: dict[str, Any]) -> bool:
    return (
        int(row["desc"]) == 0x00511E49
        and (int(row["x"]), int(row["y"])) == (736, 560)
        and int(row["helper"]) == 0x00419D60
        and int(row["return"]) == 0x0040A460
    )


def _direct_redraw_matches(row: dict[str, Any]) -> bool:
    return (
        int(row["desc"]) == 0x00511E49
        and (int(row["x"]), int(row["y"])) == (736, 560)
        and int(row["render"]) == int(row["map_surface"])
    )


def _redraw_allowed_matches(row: dict[str, Any]) -> bool:
    return (
        int(row["desc"]) == 0x00511E49
        and (int(row["x"]), int(row["y"])) == (736, 560)
        and int(row["clip"]) == EXPECTED_CLIP
        and int(row["draw"]) == 0x004191F0
        and int(row["render"]) == int(row["map_surface"])
    )


def _pointer(value: int) -> str:
    return f"0x{value:08x}"


def build_summary(log: Path, rows: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    tooltip_matches = [row for row in rows["tooltip_init"] if _tooltip_matches(row)]
    setup_matches = [row for row in rows["panel_setup"] if _setup_matches(row)]

    expected_descriptors = set(EXPECTED_PANEL_COORDS)
    expected_draw_rows = [row for row in rows["panel_draw"] if int(row["desc"]) in expected_descriptors]
    valid_draw_rows = [row for row in expected_draw_rows if _draw_matches(row)]
    valid_descriptors = {int(row["desc"]) for row in valid_draw_rows}
    invalid_draw_rows = [row for row in expected_draw_rows if not _draw_matches(row)]
    missing_descriptors = sorted(expected_descriptors - valid_descriptors)

    valid_hitscans = [row for row in rows["panel_hitscan"] if _hitscan_matches(row)]
    redraw_invoke_present = bool(rows["panel_redraw_invoke_marker"])
    valid_redraw_invokes = [row for row in rows["panel_redraw_invoke"] if _redraw_invoke_matches(row)]
    valid_direct_redraws = [row for row in rows["panel_redraw"] if _direct_redraw_matches(row)]
    valid_redraw_allowed = [row for row in rows["panel_redraw_allowed"] if _redraw_allowed_matches(row)]
    # Assigning EIP directly to 00419D60 does not re-trigger CDB's entry
    # breakpoint there. REDRAW_ALLOWED at 00419D6D is the decisive proof that
    # the helper took its clipped draw branch; PANEL_REDRAW remains telemetry.
    redraw_clip_proved = bool(valid_redraw_invokes and valid_redraw_allowed)
    checks: dict[str, dict[str, Any]] = {
        "no_access_violation": {
            "passed": not rows["access_violation"],
            "marker_count": len(rows["access_violation"]),
            "markers": rows["access_violation"][:10],
        },
        "tooltip_init_anchor": {
            "passed": bool(tooltip_matches),
            "expected": EXPECTED_TOOLTIP,
            "row_count": len(rows["tooltip_init"]),
            "matching_row_count": len(tooltip_matches),
            "first_row": rows["tooltip_init"][:1],
        },
        "panel_setup": {
            "passed": bool(setup_matches),
            "expected_clip_single": EXPECTED_CLIP,
            "expected_clip_list": EXPECTED_CLIP,
            "expected_coords": [list(coords) for coords in EXPECTED_PANEL_COORDS.values()],
            "expected_size": [EXPECTED_WIDTH, EXPECTED_HEIGHT],
            "requires_render_equals_map_surface": True,
            "row_count": len(rows["panel_setup"]),
            "matching_row_count": len(setup_matches),
            "first_row": rows["panel_setup"][:1],
        },
        "panel_draws": {
            "passed": valid_descriptors == expected_descriptors and not invalid_draw_rows,
            "expected_descriptor_count": len(expected_descriptors),
            "valid_descriptor_count": len(valid_descriptors),
            "valid_descriptors": [_pointer(value) for value in sorted(valid_descriptors)],
            "missing_descriptors": [_pointer(value) for value in missing_descriptors],
            "invalid_row_count": len(invalid_draw_rows),
            "invalid_rows": invalid_draw_rows[:10],
            "row_count": len(rows["panel_draw"]),
        },
        "panel_hitscan_anchor": {
            "passed": bool(valid_hitscans),
            "expected_e0": list(EXPECTED_HITSCAN_E0),
            "expected_e5": list(EXPECTED_HITSCAN_E5),
            "row_count": len(rows["panel_hitscan"]),
            "matching_row_count": len(valid_hitscans),
            "first_row": rows["panel_hitscan"][:1],
        },
        "panel_redraw_clip": {
            "passed": not redraw_invoke_present or redraw_clip_proved,
            "required": redraw_invoke_present,
            "proved": redraw_clip_proved,
            "redraw_invoke_row_count": len(rows["panel_redraw_invoke_marker"]),
            "parsed_redraw_invoke_row_count": len(rows["panel_redraw_invoke"]),
            "matching_redraw_invoke_row_count": len(valid_redraw_invokes),
            "matching_redraw_row_count": len(valid_direct_redraws),
            "redraw_row_required": False,
            "redraw_allowed_row_count": len(rows["panel_redraw_allowed"]),
            "matching_redraw_allowed_row_count": len(valid_redraw_allowed),
            "expected_descriptor": _pointer(0x00511E49),
            "expected_coords": [736, 560],
            "expected_helper": _pointer(0x00419D60),
            "expected_return": _pointer(0x0040A460),
            "expected_clip": EXPECTED_CLIP,
            "expected_draw": _pointer(0x004191F0),
            "first_redraw_invoke_marker": rows["panel_redraw_invoke_marker"][:1],
            "first_redraw_invoke_row": rows["panel_redraw_invoke"][:1],
            "first_matching_redraw_row": valid_direct_redraws[:1],
            "first_matching_redraw_allowed_row": valid_redraw_allowed[:1],
        },
    }
    return {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "runtime_policy": "repo-only parser; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows",
        "log": str(log),
        "target_size": [EXPECTED_WIDTH, EXPECTED_HEIGHT],
        "passed": all(check["passed"] for check in checks.values()),
        "redraw_clip_proved": redraw_clip_proved,
        "checks": checks,
        "marker_counts": {
            "tooltip_init": len(rows["tooltip_init"]),
            "tooltip_draw": len(rows["tooltip_draw"]),
            "panel_setup": len(rows["panel_setup"]),
            "panel_redraw_invoke": len(rows["panel_redraw_invoke_marker"]),
            "panel_draw": len(rows["panel_draw"]),
            "panel_redraw": len(rows["panel_redraw"]),
            "panel_redraw_allowed": len(rows["panel_redraw_allowed"]),
            "panel_hitscan": len(rows["panel_hitscan"]),
            "access_violation": len(rows["access_violation"]),
        },
        "tooltip_draw_required": False,
        "tooltip_draw_note": (
            "A tooltip draw is optional: the init marker proves the anchor even when the proxy cursor "
            "does not reach a terrain cell."
        ),
    }


def summarize(path: Path) -> dict[str, Any]:
    return build_summary(path, parse_log(path))


def write_markdown(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# HD Layout CDB Summary",
        "",
        f"- Generated: `{summary['generated_at']}`",
        f"- Log: `{summary['log']}`",
        f"- Target: `{summary['target_size'][0]}x{summary['target_size'][1]}`",
        f"- Result: `{'PASS' if summary['passed'] else 'FAIL'}`",
        "- Tooltip draw required: `false` (the init marker is the anchor proof)",
        "",
        "## Checks",
        "",
        "| Check | Result | Evidence |",
        "| --- | --- | --- |",
    ]
    for name, check in summary["checks"].items():
        evidence = ""
        if name == "no_access_violation":
            evidence = f"markers={check['marker_count']}"
        elif name == "tooltip_init_anchor":
            evidence = f"matching={check['matching_row_count']}/{check['row_count']}"
        elif name == "panel_setup":
            evidence = f"matching={check['matching_row_count']}/{check['row_count']}"
        elif name == "panel_draws":
            evidence = (
                f"descriptors={check['valid_descriptor_count']}/{check['expected_descriptor_count']}, "
                f"invalid_rows={check['invalid_row_count']}"
            )
        elif name == "panel_hitscan_anchor":
            evidence = f"matching={check['matching_row_count']}/{check['row_count']}"
        elif name == "panel_redraw_clip":
            evidence = (
                f"required={str(check['required']).lower()}, "
                f"invoke={check['matching_redraw_invoke_row_count']}, "
                f"redraw={check['matching_redraw_row_count']}, "
                f"allowed={check['matching_redraw_allowed_row_count']}"
            )
        lines.append(f"| `{name}` | `{'PASS' if check['passed'] else 'FAIL'}` | {evidence} |")
    lines.extend(
        [
            "",
            "## Marker Counts",
            "",
            "| Marker | Count |",
            "| --- | ---: |",
        ]
    )
    for marker, count in summary["marker_counts"].items():
        lines.append(f"| `{marker}` | {count} |")
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def print_summary(summary: dict[str, Any]) -> None:
    print(f"log: {summary['log']}")
    print(f"result: {'PASS' if summary['passed'] else 'FAIL'}")
    for name, check in summary["checks"].items():
        print(f"{name}: {'PASS' if check['passed'] else 'FAIL'}")
    counts = summary["marker_counts"]
    print(
        "markers: tooltip_init={tooltip_init} tooltip_draw={tooltip_draw} "
        "panel_setup={panel_setup} panel_redraw_invoke={panel_redraw_invoke} "
        "panel_draw={panel_draw} panel_redraw={panel_redraw} "
        "panel_redraw_allowed={panel_redraw_allowed} "
        "panel_hitscan={panel_hitscan} av={access_violation}".format(**counts)
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log", type=Path, help="CDB log containing HDLAYOUT_* markers")
    parser.add_argument("--write-json", type=Path)
    parser.add_argument("--write-markdown", "--write-md", dest="write_markdown", type=Path)
    parser.add_argument("--require-pass", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary = summarize(args.log)
    print_summary(summary)
    if args.write_json:
        args.write_json.parent.mkdir(parents=True, exist_ok=True)
        args.write_json.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    if args.write_markdown:
        write_markdown(args.write_markdown, summary)
    if args.require_pass and not summary["passed"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
