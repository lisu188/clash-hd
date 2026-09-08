#!/usr/bin/env python3
"""Render a resolution-aware COPY of the hidden surface probe, without runtime.

The original 800x600 template and its legacy harness substitutions stay intact.
Larger map lanes use the patcher's full-tile geometry. Visibility reads retain
the documented player-0, 100x100 map layout (13 bytes per column); runtime guards
reject another player or a viewport outside that layout before dumping/forcing.
Extra UI probes have their own recipes and are deliberately not generalized.
The exact framed validation stage uses its source-bound scalar recipe and
reserved four-border terrain; physical software-surface stride stays W.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import patch_clash95_hd as patcher  # noqa: E402

BASE_PROBE = ROOT / "probes/cdb/render/clash95_surface_dump_probe.cdb"
FRAMED_STAGE = patcher.DEFAULT_STAGE + "-combinedui-partialtiles-initialpaint-framed-validation"
BATTLE_STAGE = patcher.DEFAULT_STAGE + "-castlecenter-all-battlehd"


def render_main_menu(template: str, x: int, y: int) -> str:
    """Accept the two audited spellings of the canonical menu route point."""
    literal = "ed 00544cfc 00004b00; ed 00544d00 00003680;"
    placeholder = "ed 00544cfc __MAIN_MOUSE_RAW_X__; ed 00544d00 __MAIN_MOUSE_RAW_Y__;"
    if template.count(literal) + template.count(placeholder) != 1:
        raise ValueError("unrecognized surface probe recipe: missing or duplicate main-menu point")
    old = placeholder if placeholder in template else literal
    return replace_exact(template, old, f"ed 00544cfc {x << 6:08x}; ed 00544d00 {y << 6:08x};")


def replace_exact(text: str, old: str, new: str, count: int = 1) -> str:
    if text.count(old) != count:
        raise ValueError(f"unrecognized surface probe recipe: expected {count} copies of {old!r}")
    return text.replace(old, new)


def visibility_count(columns: int, rows: int, map_y: int) -> int:
    """Contiguous span including exactly every requested cell's visibility byte."""
    return (columns - 1) * 13 + ((map_y + rows - 1) >> 3) - (map_y >> 3) + 1


def map_guard(columns: int, rows: int, *, forced: bool = False) -> str:
    gd = "poi(005202e4)"
    mx, my = ("0n10", "0n17") if forced else (
        f"poi({gd}+0n140008)", f"poi({gd}+0n140012)"
    )
    tests = [
        "poi(005202ec) != 0", f"poi({gd}+0n140000) > 0n100",
        f"poi({gd}+0n140004) > 0n100", f"{mx} < 0", f"{my} < 0",
        f"({mx}+0n{columns}) > poi({gd}+0n140000)",
        f"({my}+0n{rows}) > poi({gd}+0n140004)",
    ]
    return " | ".join(f"({test})" for test in tests)


def forced_edge_action(columns: int, rows: int) -> str:
    # Only the observed edge cells are revealed, using OR to preserve other fog
    # bits. t0 is a pre-game trace counter, no longer live after t14 becomes 1.
    writes = []
    for col in (0, columns - 2, columns - 1):
        address = f"@$t18+0n140081+(0n{10 + col}*0n13)+((0n17+@$t0)>>3)"
        writes.append(f"eb {address} (by({address}) | (1 << ((0n17+@$t0) & 7))); ")
    return (
        f".if ({map_guard(columns, rows, forced=True)}) {{ "
        ".echo SURFDUMP_INVALID forced_edge_map_or_player_bounds; q; } .else { "
        "r @$t18 = poi(005202e4); "
        f".for (r @$t0 = 0n3; @$t0 < 0n{rows}; r @$t0 = @$t0 + 1) {{ "
        + "".join(writes) + "}; "
        + "; ".join(f"be {i}" for i in range(7)) + "; "
        + r'.printf \"SURFDUMP_FORCE_VISIBLE_EDGES recipe=grid_edge_cells player=0 '
        + f"scroll=(10,17) rows={rows} cols={columns} timing=playgame"
        + r'\\n\"; };'
    )


def render_probe(
    template: str, resolution: str, stage: str, *, canonical_template: bool = True,
    force_visible_edges: bool = False, post_owner_force_visible_seven: bool = False,
    extra_probe: bool = False, load_slot: int = 0, skip_map_validation: bool = False,
) -> dict[str, Any]:
    if not 0 <= load_slot <= 9:
        raise ValueError("LoadSlot must be in 0..9")
    profile = patcher.parse_resolution(resolution)
    # Source-only selection checks the real stage/recipe/imm8 constraints.
    framed = stage == FRAMED_STAGE
    battle = stage == BATTLE_STAGE
    layout = None
    if framed:
        from src.patcher import framed_recipe
        from src.patcher.framed_viewport import FramedViewport
        # The canonical module authenticates its own protected source/table.
        # Its package class is deliberately distinct from the legacy wrapper.
        framed_recipe.select_patches_for(framed_recipe.patcher.parse_resolution(resolution))
        layout = FramedViewport(profile.width, profile.height)
    else:
        patcher.select_patches_for(stage, profile)
    legacy = profile == patcher.PROFILE_800 and not framed
    full_columns, full_rows = layout.full_tiles if layout is not None else (profile.tiles_x, profile.tiles_y)
    columns, rows = layout.ceil_tiles if layout is not None else (full_columns, full_rows)
    if battle:
        if (profile.key != "1280x720" or not canonical_template or not extra_probe
                or not skip_map_validation or force_visible_edges or post_owner_force_visible_seven):
            raise ValueError("battle HD surface validation requires exact 1280x720, canonical base, an explicit extra probe and SkipMapValidation; map visibility forcing is forbidden")
    elif not legacy:
        if not canonical_template or extra_probe or post_owner_force_visible_seven:
            raise ValueError("non-800x600 surface validation supports only the canonical map probe; custom/extra probes and PostOwnerForceVisibleSeven need separate resolution recipes")
        if force_visible_edges and load_slot != 0:
            raise ValueError("resolution-aware ForceVisibleEdges requires LoadSlot 0 and the player-0 (10,17) map fixture")
        if skip_map_validation:
            raise ValueError("non-800x600 canonical map validation cannot skip its map/visibility gates")
    geometry = {
        "resolution": profile.key, "width": profile.width, "height": profile.height,
        "columns": columns, "rows": rows, "origin": [32, 16], "tile_size": 64,
        "partial_col_px": layout.partial_pixels[0] if layout is not None else profile.partial_col_px,
        "partial_row_px": layout.partial_pixels[1] if layout is not None else profile.partial_row_px,
        "visibility_dump_max_bytes": 160 if legacy else max(visibility_count(columns, rows, y) for y in range(8)),
        # Existing VEDGE markers authenticate native full-loop return sites.
        # Emitted partial-tile callers require their separate status trace.
        "edge_columns": [0, full_columns - 2, full_columns - 1], "edge_rows": list(range(3, full_rows)),
        "expected_vedge_count": 3 * 3 * (full_rows - 3),
        "visibility_recipe": "legacy_player0" if legacy else "bounded_player0_map100",
        "force_recipe": ("legacy_seven_cells" if legacy else "grid_edge_cells") if force_visible_edges else "none",
        # 0x419B80 compares the shifted main-menu descriptors. Preserve the
        # legacy interior point relative to their (OFFX,OFFY) centering shift.
        "main_menu_mouse": [220 + profile.off_x, 158 + profile.off_y],
        # The load-list path at 0x448A68..0x448AD9 directly tests native X
        # 244..410 and divides (Y-155) by22; selected stages do not patch it.
        "load_mouse": [320, 166 + 22 * load_slot],
        "load_input_space": "native_slot_list",
    }
    result = {"geometry": geometry, "template": template, "force_playgame_action": None}
    if battle:
        from src.patcher.battle_hd_layout import BATTLE_LAYOUT
        text = render_main_menu(template, *geometry["main_menu_mouse"])
        text = replace_exact(text, "@$t16*0n800", f"@$t16*0n{profile.width}", 3)
        # The supplied battle probe owns capture readiness. Keeping the native
        # map auto-dump would allow an unrelated early map frame to end the run.
        map_dump_lines = re.findall(r'^bp 00406FA0 .*$', text, flags=re.MULTILINE)
        if len(map_dump_lines) != 1 or "SURFDUMP_READY" not in map_dump_lines[0]:
            raise ValueError("unrecognized battle HD base map auto-dump breakpoint")
        text = text.replace(map_dump_lines[0], 'bp 00406FA0 "gc"')
        geometry.update(columns=BATTLE_LAYOUT.columns, rows=BATTLE_LAYOUT.rows,
                        origin=[BATTLE_LAYOUT.left, BATTLE_LAYOUT.top],
                        partial_col_px=0, partial_row_px=0, edge_columns=[], edge_rows=[],
                        expected_vedge_count=0, visibility_dump_max_bytes=0,
                        visibility_recipe="not_applicable_battle_extra_probe",
                        visibility_scope="no_map_visibility_claim",
                        layout_profile="battle_hd_native_17x7",
                        battlefield=list(BATTLE_LAYOUT.battlefield), sidebar=list(BATTLE_LAYOUT.sidebar),
                        capture_owner="explicit_battle_extra_probe", map_validation_applicable=False)
        result.update(template=text, stage=stage, proof_class="forced_hidden_battle_fixture",
                      source_bindings={"battle_layout": {
                          "path": str(ROOT / "src/patcher/battle_hd_layout.py"),
                          "sha256": hashlib.sha256((ROOT / "src/patcher/battle_hd_layout.py").read_bytes()).hexdigest()}})
        return result
    if framed:
        geometry.update(layout_profile="native_four_border_tiles_v1",
                        terrain=list(layout.terrain.as_tuple()), frame_insets=[32,16,32,16],
                        surface=[0,0,profile.width-1,profile.height-1],
                        full_columns=full_columns, full_rows=full_rows,
                        visibility_scope="all_ceiling_cells_in_world",
                        visibility_limit="This initial screenshot lane rejects a ceiling cell outside the world; it provides no far-world clear proof.",
                        vedge_scope="native_full_cells_only")
        result.update(stage=stage, scalar_recipe_stage=framed_recipe.FRAME_BASE_STAGE,
                      source_bindings={name: {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
                        for name, path in (("framed_recipe", Path(framed_recipe.__file__)),
                                           ("framed_viewport", ROOT / "src/patcher/framed_viewport.py"))})
    if legacy:
        return result
    text = template
    main_x, main_y = geometry["main_menu_mouse"]
    text = render_main_menu(text, main_x, main_y)
    text = replace_exact(text, "@$t16*0n800", f"@$t16*0n{profile.width}", 3)
    text = replace_exact(text, "(@eax == 0n32) | (@eax == 0n672) | (@eax == 0n736)",
                         " | ".join(f"(@eax == 0n{32 + col * 64})" for col in geometry["edge_columns"]))
    text = replace_exact(text, " | ".join(f"(@edx == 0n{16 + row * 64})" for row in range(3, 9)),
                         f"(@edx >= 0n208) & (@edx <= 0n{16 + (full_rows - 1) * 64}) & (((@edx-0n16) & 0n63) == 0)")
    text = replace_exact(text, "@$t3 < 0n96", f"@$t3 < 0n{max(96, geometry['expected_vedge_count'] + 1)}")
    text = replace_exact(text, "end12=", "endgrid=")
    text = replace_exact(text, "poi(@$t10+0n140008)+0n12", f"poi(@$t10+0n140008)+0n{full_columns}")
    text = replace_exact(text, "poi(@$t10+0n140012)+0n9", f"poi(@$t10+0n140012)+0n{full_rows}")
    text = replace_exact(text, "(@$t12 < 0n320) | (@$t15 < 0n200) | (@$t12 > 0n2048) | (@$t15 > 0n2048)",
                         f"(@$t12 != 0n{profile.width}) | (@$t15 != 0n{profile.height}) | {map_guard(columns, rows)}")
    # Count depends on the loaded scroll-Y residue, so do not overread a column
    # merely to retain the legacy rounded 160-byte diagnostic span.
    count_expr = f"(0n{(columns - 1) * 13}+((poi(@$t10+0n140012)+0n{rows - 1})>>3)-(poi(@$t10+0n140012)>>3)+1)"
    text = replace_exact(text, "rows=9 cols=12", f"rows={rows} cols={columns}")
    text = replace_exact(text, "count=160", "count=%d")
    text = replace_exact(text, r'.printf \"SCROLL_VISDUMP ',
                         f"r @$t18 = {count_expr}; " + r'.printf \"SCROLL_VISDUMP ')
    dump_address = "@$t10+0n140081+(poi(@$t10+0n140008)*0n13)+(poi(@$t10+0n140012)>>3)"
    text = replace_exact(text, dump_address + "; db ", dump_address + ", @$t18; db ")
    text = replace_exact(text, "L0n160", "L@$t18")
    result["template"] = text
    if force_visible_edges:
        result["force_playgame_action"] = forced_edge_action(full_columns, full_rows)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--template", type=Path, default=BASE_PROBE)
    parser.add_argument("--resolution", default="800x600")
    parser.add_argument("--stage", default=patcher.DEFAULT_STAGE)
    parser.add_argument("--force-visible-edges", action="store_true")
    parser.add_argument("--post-owner-force-visible-seven", action="store_true")
    parser.add_argument("--extra-probe", action="store_true")
    parser.add_argument("--extra-probe-path", type=Path)
    parser.add_argument("--load-slot", type=int, default=0)
    parser.add_argument("--skip-map-validation", action="store_true")
    args = parser.parse_args()
    try:
        data = args.template.read_bytes()
        if args.stage == BATTLE_STAGE and args.extra_probe_path is None:
            raise ValueError("battle HD preflight requires --extra-probe-path for source binding")
        # Preserve CRLF/LF exactly, as Get-Content -Raw does in the harness.
        report = render_probe(data.decode("utf-8-sig"), args.resolution, args.stage,
                              canonical_template=args.template.resolve() == BASE_PROBE.resolve(),
                              force_visible_edges=args.force_visible_edges,
                              post_owner_force_visible_seven=args.post_owner_force_visible_seven,
                              extra_probe=args.extra_probe, load_slot=args.load_slot,
                              skip_map_validation=args.skip_map_validation)
        report["base_probe_sha256"] = hashlib.sha256(data).hexdigest()
        if args.extra_probe_path is not None:
            if not args.extra_probe:
                raise ValueError("--extra-probe-path requires --extra-probe")
            report["extra_probe_path"] = str(args.extra_probe_path.resolve())
            report["extra_probe_sha256"] = hashlib.sha256(args.extra_probe_path.read_bytes()).hexdigest()
        print(json.dumps(report))
    except (OSError, ValueError) as exc:
        parser.exit(2, f"surface probe rendering refused: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
