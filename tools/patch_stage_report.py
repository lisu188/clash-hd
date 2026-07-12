#!/usr/bin/env python3
"""Report which Clash95 HD patch-stage bytes are present in an executable."""

from __future__ import annotations

import argparse
import importlib.util
import json
import struct
import sys
from collections import Counter, defaultdict
from pathlib import Path
from types import ModuleType
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PATCHER = ROOT / "patch_clash95_hd.py"
MAP_GROUPS = {
    "input-bounds",
    "viewport-init",
    "viewport-switch",
    "viewport-switch-dynamic-surface",
    "main-loops",
    "full-redraw-12x9",
    "full-redraw-present-bounds-800",
    "minimap-right-clip",
    "minimap-hd-right-anchor",
    "helpers",
    "saved-scroll-clamp",
    "map-surface-upgrade-scrollclamp",
}
DEFAULT_RESOLUTION = "800x600"


def current_hd_map_gate_checks(profile: Any = None) -> dict:
    """Gate expectations, parameterized by resolution profile.

    Check key NAMES are historical labels baked into archived report JSON
    (e.g. `input_bounds_800x600`); only expected VALUES parameterize. With
    profile=None the returned dict is the frozen 800x600 constant.
    """
    if profile is None:
        tiles = {"x": 12, "y": 9}
    else:
        tiles = {"x": profile.tiles_x, "y": profile.tiles_y}
    return {
        "visible_tiles_12x9": ("visible_tiles", tiles),
        "main_loops_12x9": ("main_loops_12x9", True),
        "full_redraw_12x9": ("full_redraw_12x9", True),
        "full_redraw_present_bounds_800": ("full_redraw_present_bounds_800", True),
        "minimap_right_clip": ("minimap_right_clip", True),
        "minimap_hd_right_anchor": ("minimap_hd_right_anchor", True),
        "helpers_12x9": ("helpers_12x9", True),
        "input_bounds_800x600": ("input_bounds_800x600", True),
        "viewport_init_800x600": ("viewport_init_800x600", True),
        "viewport_switch_800x600": ("viewport_switch_800x600", True),
        "viewport_switch_dynamic_surface": ("viewport_switch_dynamic_surface", True),
        "saved_scroll_restore_clamp": ("saved_scroll_restore_clamp", True),
        "map_surface_upgrade_after_menu": ("map_surface_upgrade_after_menu", True),
    }


CURRENT_HD_MAP_GATE_CHECKS = current_hd_map_gate_checks()


def load_patcher() -> ModuleType:
    spec = importlib.util.spec_from_file_location("patch_clash95_hd", PATCHER)
    if spec is None or spec.loader is None:
        raise SystemExit(f"Cannot load patcher module: {PATCHER}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def parse_pe_sections(data: bytes) -> tuple[int | None, list[dict[str, int | str]]]:
    if len(data) < 0x100 or data[:2] != b"MZ":
        return None, []

    pe_offset = struct.unpack_from("<I", data, 0x3C)[0]
    if pe_offset + 0x18 >= len(data) or data[pe_offset : pe_offset + 4] != b"PE\0\0":
        return None, []

    number_of_sections = struct.unpack_from("<H", data, pe_offset + 6)[0]
    optional_header_size = struct.unpack_from("<H", data, pe_offset + 20)[0]
    optional_header = pe_offset + 24
    magic = struct.unpack_from("<H", data, optional_header)[0]
    image_base: int | None
    if magic == 0x10B:
        image_base = struct.unpack_from("<I", data, optional_header + 28)[0]
    elif magic == 0x20B:
        image_base = struct.unpack_from("<Q", data, optional_header + 24)[0]
    else:
        image_base = None

    sections = []
    section_table = optional_header + optional_header_size
    for index in range(number_of_sections):
        entry = section_table + index * 40
        if entry + 40 > len(data):
            break
        raw_name = data[entry : entry + 8].split(b"\0", 1)[0]
        virtual_size, virtual_address, raw_size, raw_pointer = struct.unpack_from("<IIII", data, entry + 8)
        sections.append(
            {
                "name": raw_name.decode("ascii", errors="replace"),
                "virtual_size": virtual_size,
                "virtual_address": virtual_address,
                "raw_size": raw_size,
                "raw_pointer": raw_pointer,
            }
        )
    return image_base, sections


def raw_to_rva(offset: int, sections: list[dict[str, int | str]]) -> int | None:
    for section in sections:
        raw_pointer = int(section["raw_pointer"])
        raw_size = int(section["raw_size"])
        if raw_pointer <= offset < raw_pointer + raw_size:
            return int(section["virtual_address"]) + (offset - raw_pointer)
    return None


def spaced_hex(data: bytes) -> str:
    return data.hex(" ").upper()


def status_for(actual: bytes, old: bytes, new: bytes) -> str:
    if actual == new:
        return "patched"
    if actual == old:
        return "original"
    return "unexpected"


def patch_record(patch: Any, data: bytes, image_base: int | None, sections: list[dict[str, int | str]]) -> dict:
    actual = data[patch.offset : patch.offset + len(patch.new)]
    rva = raw_to_rva(patch.offset, sections)
    va = image_base + rva if image_base is not None and rva is not None else None
    return {
        "group": patch.group,
        "offset": patch.offset,
        "offset_hex": f"0x{patch.offset:06X}",
        "rva": rva,
        "rva_hex": f"0x{rva:08X}" if rva is not None else None,
        "va": va,
        "va_hex": f"0x{va:08X}" if va is not None else None,
        "old": spaced_hex(patch.old),
        "new": spaced_hex(patch.new),
        "actual": spaced_hex(actual),
        "status": status_for(actual, patch.old, patch.new),
        "note": patch.note,
    }


def summarize_groups(records: list[dict]) -> dict:
    grouped: dict[str, Counter] = defaultdict(Counter)
    for record in records:
        grouped[record["group"]][record["status"]] += 1
        grouped[record["group"]]["total"] += 1
    return {group: dict(counts) for group, counts in sorted(grouped.items())}


def all_group_patched(group: str, groups: dict[str, dict]) -> bool:
    summary = groups.get(group, {})
    total = int(summary.get("total", 0))
    return total > 0 and int(summary.get("patched", 0)) == total


def map_summary(
    stage_groups: tuple[str, ...], groups: dict[str, dict], profile: Any = None
) -> dict:
    main_loops = all_group_patched("main-loops", groups)
    helpers = all_group_patched("helpers", groups)
    viewport_switch = all_group_patched("viewport-switch", groups) or all_group_patched(
        "viewport-switch-dynamic-surface", groups
    )
    hd_tiles = {"x": 12, "y": 9} if profile is None else {
        "x": profile.tiles_x,
        "y": profile.tiles_y,
    }
    return {
        "stage_groups": [group for group in stage_groups if group in MAP_GROUPS],
        "visible_tiles": hd_tiles if main_loops else {"x": 9, "y": 7},
        "main_loops_12x9": main_loops,
        "full_redraw_12x9": all_group_patched("full-redraw-12x9", groups),
        "full_redraw_present_bounds_800": all_group_patched(
            "full-redraw-present-bounds-800", groups
        ),
        "minimap_right_clip": all_group_patched("minimap-right-clip", groups),
        "minimap_hd_right_anchor": all_group_patched("minimap-hd-right-anchor", groups),
        "helpers_12x9": helpers,
        "input_bounds_800x600": all_group_patched("input-bounds", groups),
        "viewport_init_800x600": all_group_patched("viewport-init", groups),
        "viewport_switch_800x600": viewport_switch,
        "viewport_switch_dynamic_surface": all_group_patched("viewport-switch-dynamic-surface", groups),
        "menu_safe_viewport_switch": "viewport-switch" not in stage_groups
        and "viewport-switch-dynamic-surface" not in stage_groups,
        "saved_scroll_restore_clamp": all_group_patched("saved-scroll-clamp", groups)
        or all_group_patched("map-surface-upgrade-scrollclamp", groups),
        "map_surface_upgrade_after_menu": all_group_patched("map-surface-upgrade-scrollclamp", groups),
    }


def current_hd_map_gate(report: dict, gate_checks: dict | None = None) -> dict:
    failures = []
    status_counts = report["status_counts"]
    if int(status_counts.get("unexpected", 0)):
        failures.append(f"{status_counts['unexpected']} patch bytes are unexpected")
    if int(status_counts.get("original", 0)):
        failures.append(f"{status_counts['original']} selected patch bytes are still original")

    map_info = report["map"]
    checks = {}
    for name, (key, expected) in (gate_checks or CURRENT_HD_MAP_GATE_CHECKS).items():
        actual = map_info[key]
        passed = actual == expected
        checks[name] = {"expected": expected, "actual": actual, "passed": passed}
        if not passed:
            failures.append(f"{name} expected {expected!r}, got {actual!r}")

    return {
        "passed": not failures,
        "failures": failures,
        "checks": checks,
    }


def build_report(exe: Path, stage: str, resolution: str = DEFAULT_RESOLUTION) -> dict:
    module = load_patcher()
    if stage not in module.STAGE_GROUPS:
        choices = ", ".join(sorted(module.STAGE_GROUPS))
        raise SystemExit(f"Unknown stage: {stage}\nKnown stages: {choices}")
    try:
        profile = module.parse_resolution(resolution)
    except module.ResolutionError as exc:
        raise SystemExit(str(exc)) from exc
    legacy = resolution == DEFAULT_RESOLUTION
    data = exe.read_bytes()
    image_base, sections = parse_pe_sections(data)
    if legacy:
        patches = module.select_patches(stage)
        gate_profile = None
    else:
        try:
            patches = module.select_patches_for(stage, profile)
        except module.ResolutionError as exc:
            raise SystemExit(str(exc)) from exc
        gate_profile = profile
    records = [patch_record(patch, data, image_base, sections) for patch in patches]
    group_summary = summarize_groups(records)
    status_counts = Counter(record["status"] for record in records)
    report = {
        "exe": str(exe),
        "stage": stage,
        "resolution": resolution,
        "exe_sha256": module.sha256(data).upper(),
        "expected_base_sha256": module.EXPECTED_SHA256.upper(),
        "image_base_hex": f"0x{image_base:08X}" if image_base is not None else None,
        "sections": sections,
        "patch_count": len(records),
        "status_counts": dict(status_counts),
        "groups": group_summary,
        "map": map_summary(module.STAGE_GROUPS[stage], group_summary, gate_profile),
        "patches": records,
    }
    report["current_hd_map_gate"] = current_hd_map_gate(
        report, current_hd_map_gate_checks(gate_profile)
    )
    return report


def print_summary(report: dict) -> None:
    print(f"exe: {report['exe']}")
    print(f"stage: {report['stage']}")
    print(f"sha256: {report['exe_sha256']}")
    print(
        "patches: {patched} patched, {original} original, {unexpected} unexpected, {total} total".format(
            patched=report["status_counts"].get("patched", 0),
            original=report["status_counts"].get("original", 0),
            unexpected=report["status_counts"].get("unexpected", 0),
            total=report["patch_count"],
        )
    )
    map_info = report["map"]
    print(
        "map: visible_tiles={x}x{y} main_loops_12x9={loops} helpers_12x9={helpers} "
        "full_redraw_12x9={full_redraw} full_redraw_present_bounds_800={present_bounds} "
        "minimap_right_clip={minimap_clip} minimap_hd_right_anchor={minimap_anchor} "
        "viewport_init_800x600={vinit} viewport_switch_800x600={vswitch} "
        "viewport_switch_dynamic_surface={vdyn} "
        "menu_safe_switch={safe} saved_scroll_restore_clamp={saved_clamp}".format(
            x=map_info["visible_tiles"]["x"],
            y=map_info["visible_tiles"]["y"],
            loops=map_info["main_loops_12x9"],
            helpers=map_info["helpers_12x9"],
            full_redraw=map_info["full_redraw_12x9"],
            present_bounds=map_info["full_redraw_present_bounds_800"],
            minimap_clip=map_info["minimap_right_clip"],
            minimap_anchor=map_info["minimap_hd_right_anchor"],
            vinit=map_info["viewport_init_800x600"],
            vswitch=map_info["viewport_switch_800x600"],
            vdyn=map_info["viewport_switch_dynamic_surface"],
            safe=map_info["menu_safe_viewport_switch"],
            saved_clamp=map_info["saved_scroll_restore_clamp"],
        )
    )
    gate = report["current_hd_map_gate"]
    print(f"current_hd_map_gate: {'PASS' if gate['passed'] else 'FAIL'}")
    for failure in gate["failures"][:20]:
        print(f"gate failure: {failure}")
    for group, values in report["groups"].items():
        print(
            "- {group}: {patched}/{total} patched, {original} original, {unexpected} unexpected".format(
                group=group,
                patched=values.get("patched", 0),
                total=values.get("total", 0),
                original=values.get("original", 0),
                unexpected=values.get("unexpected", 0),
            )
        )
    unexpected = [record for record in report["patches"] if record["status"] == "unexpected"]
    for record in unexpected[:20]:
        print(
            "unexpected: {offset} {group} actual={actual} expected_new={new} note={note}".format(
                **record
            )
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Report Clash95 HD patch-stage byte status.")
    parser.add_argument("--exe", required=True, type=Path, help="candidate executable to inspect")
    parser.add_argument(
        "--stage",
        default="gameplay-menu640-centered-map12-dynorigin",
        help="patch stage to verify against patch_clash95_hd.py definitions",
    )
    parser.add_argument(
        "--resolution",
        default=DEFAULT_RESOLUTION,
        help=(
            "target resolution WxH; non-default resolutions verify the "
            "generated patch table and parameterize the tile-count gate"
        ),
    )
    parser.add_argument("--write-json", type=Path, help="write the full report as JSON")
    parser.add_argument(
        "--require-current-hd-map",
        action="store_true",
        help="exit 2 unless every current 12x9 HD-map patch group is present and no selected bytes are original/unexpected",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.exe.is_file():
        raise SystemExit(f"Executable does not exist: {args.exe}")
    report = build_report(args.exe, args.stage, args.resolution)
    if args.write_json:
        args.write_json.parent.mkdir(parents=True, exist_ok=True)
        args.write_json.write_text(json.dumps(report, indent=2), encoding="ascii")
    print_summary(report)
    if args.require_current_hd_map and not report["current_hd_map_gate"]["passed"]:
        return 2
    return 1 if report["status_counts"].get("unexpected", 0) else 0


if __name__ == "__main__":
    raise SystemExit(main())
