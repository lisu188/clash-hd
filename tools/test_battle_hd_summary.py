#!/usr/bin/env python3
"""Synthetic, repo-only fixtures for the independent battle HD evidence lane."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import battle_hd_summary as hd


def write_json(path: Path, payload: dict) -> Path:
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def complete_observation_rows() -> str:
    rows = [f"BATTLE_HD_{name} eip={address:08x}" for name, address in hd.OWNER_ADDRESSES.items()
            if name not in {"RESULTS", "RETURN", "MAP_POLL"}]
    rows.extend([
        "BATTLE_HD_GEOMETRY observed_rect=(32,136,1120,584) observed_hud=(1120,120,1280,600) observed_tiles=(17,7) surface=(1280,720) source=measured",
        "BATTLE_HD_FULL_REDRAW eip=00430c20 clip=(32,136,1120,584) surface=(1280,720) bounds_ok=1",
        "BATTLE_HD_DIRTY_REDRAW eip=00430b20 clip=(32,136,1120,584) surface=(1280,720) bounds_ok=1",
        "BATTLE_HD_PRESENT surface=(1280,720) bounds_ok=1",
        "BATTLE_HD_GRID_RESULT case=top_left point=(32,136) camera=(0,0) cell=(0,0) accepted=1 source=observed",
        "BATTLE_HD_GRID_RESULT case=top_right point=(1119,136) camera=(0,0) cell=(16,0) accepted=1 source=observed",
        "BATTLE_HD_GRID_RESULT case=bottom_left point=(32,583) camera=(0,0) cell=(0,6) accepted=1 source=observed",
        "BATTLE_HD_GRID_RESULT case=bottom_right point=(1119,583) camera=(3,0) cell=(19,6) accepted=1 source=observed",
        "BATTLE_HD_GRID_RESULT case=hud point=(1120,136) camera=(0,0) cell=(-1,-1) accepted=0 source=observed",
        "BATTLE_HD_GRID_RESULT case=outside point=(31,136) camera=(0,0) cell=(-1,-1) accepted=0 source=observed",
        "BATTLE_HD_GRID_RESULT case=top_padding point=(32,135) camera=(0,0) cell=(-1,-1) accepted=0 source=observed",
        "BATTLE_HD_GRID_RESULT case=bottom_padding point=(32,584) camera=(0,0) cell=(-1,-1) accepted=0 source=observed",
        "BATTLE_HD_COMMAND_RESULT case=enabled matched=1 source=observed",
        "BATTLE_HD_COMMAND_RESULT case=disabled matched=1 source=observed",
        "BATTLE_HD_PAN_RESULT direction=left camera=(0,0) camera_after_repeat=(0,0) source=observed",
        "BATTLE_HD_PAN_RESULT direction=right camera=(3,0) camera_after_repeat=(3,0) source=observed",
        "BATTLE_HD_PAN_RESULT direction=up camera=(0,0) camera_after_repeat=(0,0) source=observed",
        "BATTLE_HD_PAN_RESULT direction=down camera=(0,0) camera_after_repeat=(0,0) source=observed",
        "BATTLE_HD_MODAL_RESULT opened=1 closed=1 input_restored=1 source=observed",
        "BATTLE_HD_RESULTS eip=0042e5a0",
        "BATTLE_HD_RETURN eip=0041b14a",
        "BATTLE_HD_MAP_POLL eip=0040b0c3",
        "BATTLE_HD_MAP_HEALTH surface=(1280,720) input_restored=1 render_restored=1 source=observed",
    ])
    return "\n".join(row + " arena=(20,7)" if row.startswith(("BATTLE_HD_GRID_RESULT", "BATTLE_HD_PAN_RESULT"))
                     else row for row in rows) + "\n"


def fixture(directory: Path, log: str | None = None) -> tuple[Path, Path, Path]:
    directory.mkdir(parents=True, exist_ok=True)
    log_path = directory / "cdb-surface-dump.log"
    log_path.write_text(complete_observation_rows() if log is None else log, encoding="utf-8")
    manifest = {
        "schema": 1, "candidate": r"C:\ClashTests\battlehd\fixture.exe",
        "candidate_sha256": "A" * 64, "stage": hd.EXPECTED_STAGE,
        "resolution": [1280, 720], "wrapper": "synthetic_test_fixture",
        "launch_mode": "hidden-desktop-cdb", "input_method": "pulse",
        "input_evidence_class": "automated_visible_runtime", "route_method": "natural",
        "forced_actions": [], "log_sha256": hd.digest(log_path),
    }
    patch = {"exe": manifest["candidate"], "exe_sha256": manifest["candidate_sha256"],
             "stage": hd.EXPECTED_STAGE, "resolution": "1280x720", "patch_count": 150,
             "expected_base_sha256": hd.EXPECTED_BASE_SHA256,
             "status_counts": {"patched": 150, "original": 0, "unexpected": 0}}
    return log_path, write_json(directory / "battle-hd-run.json", manifest), write_json(directory / "patch.json", patch)


def check(directory: Path, log: str | None = None) -> dict:
    return hd.build_summary(*fixture(directory, log))


def test_claims_are_independent(directory: Path) -> None:
    result = check(directory)
    assert not result["passed"] and not result["claims"]["visible"]["passed"], result
    for claim in ("identity", "route_catalog", "geometry", "render", "input", "modal", "return"):
        assert result["claims"][claim]["passed"], (claim, result)
    assert result["promotion_status"] == "validation_stage_only"
    assert result["stable_stage_should_change"] is False
    assert result["manual_input_claim_accepted"] is False


def test_catalog_and_centered_rows_cannot_prove_hd(directory: Path) -> None:
    catalog = "\n".join(f"BATTLE_HD_{name} eip={address:08x}" for name, address in hd.OWNER_ADDRESSES.items())
    result = check(directory / "catalog", catalog)
    assert result["claims"]["route_catalog"]["passed"]
    assert all(not result["claims"][name]["passed"] for name in ("geometry", "render", "input", "modal", "return", "visible"))
    old = check(directory / "old", "BATTLE_READY width=1280 height=720\nBATTLE_SURFACE mode=centered-native offset=(320,120)\n")
    assert not any(old["owner_visits"].values()) and old["visual_mode"] == "unproven"


def test_echoed_and_wrong_owner_markers_fail(directory: Path) -> None:
    rows, errors, _ = hd.parse_rows('0:000> .echo BATTLE_HD_ENTRY eip=0042e9e0\n.printf "BATTLE_HD_ENTRY eip=0042e9e0"\nBATTLE_HD_ENTRY eip=%p\n')
    assert rows == [] and errors == []
    wrong = check(directory, complete_observation_rows().replace("eip=0042e9e0", "eip=0042e5a0"))
    assert wrong["owner_visits"]["ENTRY"] is False and not wrong["claims"]["return"]["passed"]
    _, errors, _ = hd.parse_rows("BATTLE_HD_ENTRY eip=0042e9e0 eip=0042e5a0")
    assert errors


def test_space_separated_stream_preserves_chronology(directory: Path) -> None:
    # Matches the actual nested .printf output shape of the hidden CDB lane.
    stream = ("BATTLE_FORCE_ATTACK_CALL attacker=0 defender=4 "
              "BATTLE_OWNER_ENTRY source=BattleRunner eip=0042e9e0 "
              + complete_observation_rows().replace("\n", " "))
    result = check(directory, stream)
    assert result["claims"]["return"]["passed"], result
    assert result["claims"]["geometry"]["passed"]
    assert result["evidence_class"] == "forced_validation"
    rows, errors, interventions = hd.parse_rows(stream)
    assert not errors and interventions == ["BATTLE_FORCE_ATTACK_CALL"]
    assert all(row["line"] == 1 for row in rows)
    assert [row["order"] for row in rows] == list(range(len(rows)))
    reordered = stream.replace("BATTLE_HD_RESULTS eip=0042e5a0 BATTLE_HD_RETURN eip=0041b14a",
                               "BATTLE_HD_RETURN eip=0041b14a BATTLE_HD_RESULTS eip=0042e5a0")
    assert not check(directory / "reordered", reordered)["claims"]["return"]["passed"]


def test_stream_rejects_command_text_and_emitted_literals(directory: Path) -> None:
    fake = '\\"BATTLE_HD_ENTRY eip=0042e9e0 BATTLE_HD_RESULTS eip=0042e5a0\\"'
    log = (f'0:000> bp 0042e9e0 ".printf {fake}; gc"\n'
           f'bp 0042e9e0 ".printf {fake}; gc"\n'
           f'.printf {fake}\n'
           f'Syntax error in .printf {fake}\n'
           'BATTLE_HD_ENTRY eip=%p BATTLE_HD_RESULTS eip=%p\n'
           'BATTLE_HD_ENTRY eip=0042e9e0; .printf "BATTLE_HD_RESULTS eip=0042e5a0"\n'
           'BATTLE_HD_ENTRY eip=0042e9e0 unexpected_text\n')
    rows, errors, interventions = hd.parse_rows(log)
    assert rows == [] and not interventions, rows
    assert len(errors) == 1 and "Syntax error" in errors[0]
    rows, errors, _ = hd.parse_rows('^ Extra character error in \'r @t15=0; .if (...) { .printf "BATTLE_HD_ENTRY eip=0042e9e0"; } .if (...)\'')
    assert not rows and len(errors) == 1 and "Extra character error" in errors[0]


def test_cdb_helper_phase_protocol(directory: Path) -> None:
    import re
    root = Path(__file__).resolve().parents[1]
    for name in ("clash95_battle_hd_catalog_extra.cdb", "clash95_battle_hd_validation_extra.cdb"):
        probe = (root / "probes" / "cdb" / "battle" / name).read_text(encoding="utf-8")
        assert not re.search(r"(?<!\\)\\n", probe), "Nested bp printf requires two escaping layers"
    probe = (root / "probes" / "cdb" / "battle" / "clash95_battle_hd_validation_extra.cdb").read_text(encoding="utf-8")
    assert "} .if" not in probe, "Independent .if commands need semicolon separators"
    assert not re.search(r"r @\$t9=\d+;|@\$t15 == \d+\)", probe), "Phase IDs must be explicitly decimal"
    assert "ed poi(00532048)+0n808 0xfffffc19;" in probe, "Negative camera fixture must not enter interactive ed mode"


def helper_observation_rows(arena_columns: int = 20) -> str:
    """Synthetic register-read records; never persisted as runtime proof."""
    camera = max(0, arena_columns - 17)
    columns = min(17, arena_columns)
    rows = [f"BATTLE_HD_FORCE_CAMERA phase=lower requested=(-999,999) arena=({arena_columns},7)",
            f"BATTLE_HD_CLAMP_MEASURE case=lower camera=(0,0) arena=({arena_columns},7)",
            "BATTLE_HD_FORCE_CAMERA phase=upper requested=(999,999)",
            f"BATTLE_HD_CLAMP_MEASURE case=upper camera=({camera},0) arena=({arena_columns},7)"]
    points = {"top_left": (32, 136), "top_right": (1119, 136),
              "bottom_left": (32, 583), "bottom_right": (1119, 583),
              "hud": (1120, 136), "outside": (31, 136),
              "bottom_padding": (32, 584), "top_padding": (32, 135)}
    for case, (x, y) in points.items():
        inside = 32 <= x < 1120 and 136 <= y < 584 and (x - 32) // 64 + camera < arena_columns
        local = ((x - 32) // 64, (y - 136) // 64) if inside else (-1, -1)
        rows.append(f"BATTLE_HD_MOUSE_CELL_MEASURE case={case} point=({x},{y}) "
                    f"local=({local[0]},{local[1]}) carry={int(not inside)} camera=({camera},0) "
                    f"arena=({arena_columns},7) mouse_after=({x},{y})")
    for col in range(columns):
        for row in range(7):
            rows.extend([f"BATTLE_HD_TILE_MEASURE eip=0042ffb5 phase=11 world=({col},{row}) camera=(0,0)",
                         f"BATTLE_HD_PIXEL_MEASURE eip=0042ffe6 phase=11 x={32 + col*64} y={136 + row*64}"])
    rows.extend([f"BATTLE_HD_DRAW_COVERAGE camera=(0,0) arena=({arena_columns},7) columns_mask=0x{(1 << columns) - 1:08x} tile_calls={columns * 7}",
                 "BATTLE_HD_TILE_MEASURE eip=0042ffb5 phase=12 world=(8,0) camera=(0,0)",
                 "BATTLE_HD_PIXEL_MEASURE eip=0042ffe6 phase=12 x=544 y=136",
                 "BATTLE_HD_DIRTY_MEASURE returned=1 tile=(8,0)",
                 "BATTLE_HD_PRESENT_MEASURE eip=00460ea0 phase=14 ret=0042f2fa surface=(1280,720)"])
    positions = ((1138, 490), (1201, 490), (1138, 521), (1138, 552), (1201, 521), (1145, 120))
    callbacks = (0x42D4E0, 0x42D3A0, 0x42D5B0, 0x42D670, 0x42D560, 0x42D6F0)
    rows.extend(f"BATTLE_HD_HUD_DESCRIPTOR index={i} desc={0x514b78 + i*53:08x} xy=({x},{y}) callback={callbacks[i]:08x}"
                for i, (x, y) in enumerate(positions))
    rectangles = ((0, 0, 31, 479, 0, 120), (480, 0, 639, 479, 1120, 120),
                  (32, 0, 479, 15, 32, 120), (32, 464, 479, 479, 32, 584),
                  (32, 0, 479, 15, 480, 120), (32, 464, 479, 479, 480, 584),
                  (32, 0, 223, 15, 928, 120), (32, 464, 223, 479, 928, 584))
    rows.extend(f"BATTLE_HD_HUD_BLIT ret=005661aa src=00300000 dst=0051d4c0 source=({left},{top},{right},{bottom}) destination=({x},{y})"
                for left, top, right, bottom, x, y in rectangles)
    rows.append("BATTLE_HD_MEASUREMENTS_DONE evidence=forced_hidden_helper_measurements modal=pending return=pending callbacks=observation_only")
    return " ".join(rows) + "\n"


def test_helper_measurements_are_narrow_independent_claims(directory: Path) -> None:
    result = check(directory, helper_observation_rows())
    helper = result["helper_measurements"]
    assert helper["sequence_completed"] and all(value["passed"] for value in helper["checks"].values()), helper
    assert helper["observed_arenas"] == [(20, 7)]
    assert helper["acceptance_claims_satisfied_by_helpers"] is False
    assert result["evidence_class"] == "forced_validation"
    assert all(not result["claims"][name]["passed"] for name in ("geometry", "render", "input", "modal", "return", "visible"))
    mutations = (("camera=(3,0) arena=(20,7)", "camera=(3,1) arena=(20,7)", "camera_endpoints"),
                 ("local=(16,6) carry=0", "local=(6,6) carry=0", "mouse_cell_boundaries"),
                 ("x=1056 y=520", "x=416 y=520", "full_tile_projection"),
                 ("phase=12 x=544", "phase=12 x=543", "dirty_tile_projection"),
                 ("xy=(1145,120)", "xy=(505,0)", "hud_descriptor_coordinates"),
                 ("destination=(928,584)", "destination=(928,464)", "frame_copy_rectangles"))
    for old, new, name in mutations:
        mutated = check(directory / name, helper_observation_rows().replace(old, new))
        assert not mutated["helper_measurements"]["checks"][name]["passed"], (name, mutated)
    incomplete = check(directory / "incomplete", helper_observation_rows().replace("BATTLE_HD_MEASUREMENTS_DONE", "BATTLE_HD_NOT_DONE"))
    assert not any(value["passed"] for value in incomplete["helper_measurements"]["checks"].values())


def test_helper_uses_actual_arena_and_keeps_seven_rows(directory: Path) -> None:
    for columns in (16, 17, 20):
        result = check(directory / str(columns), helper_observation_rows(columns))
        helper = result["helper_measurements"]
        assert all(value["passed"] for value in helper["checks"].values()), helper
        assert helper["observed_arenas"] == [(columns, 7)]
    bad_rows = check(directory / "rows", helper_observation_rows(16).replace("arena=(16,7)", "arena=(16,8)"))
    assert not bad_rows["helper_measurements"]["checks"]["camera_endpoints"]["passed"]
    assert not bad_rows["helper_measurements"]["checks"]["mouse_cell_boundaries"]["passed"]
    assert not bad_rows["helper_measurements"]["checks"]["full_tile_projection"]["passed"]


def test_initial_loader_break_is_not_a_runtime_failure(directory: Path) -> None:
    initial = ("(8114.9ec0): Break instruction exception - code 80000003 (first chance)\n"
               "eax=00000000 ebx=00000000\neip=773787f8 esp=000efa54\n"
               "cs=0023  ss=002b\nntdll!LdrpDoDebuggerBreak+0x2b:\n773787f8 cc int 3\n")
    rows, errors, _ = hd.parse_rows(initial + helper_observation_rows())
    assert rows and not errors, errors
    _, errors, _ = hd.parse_rows(initial.replace("ntdll!LdrpDoDebuggerBreak", "clash95!BattleRunner"))
    assert errors
    _, errors, _ = hd.parse_rows(helper_observation_rows() + initial)
    assert errors
    _, errors, _ = hd.parse_rows(initial + initial)
    assert errors


def camera_observation_rows() -> str:
    cases = (("width17_lower", 17, 0, 1), ("width17_upper", 17, 0, 1),
             ("width20_lower", 20, 0, 1), ("width20_upper", 20, 3, 1),
             ("recenter_left", 20, 0, 0), ("recenter_right", 20, 3, 19), ("retain_visible", 20, 3, 10))
    rows = ["BATTLE_HD_CAMERA_FIXTURE_SAVED arena=(16,7) camera=(0,0) unit0_xy_word=00030001",
            "BATTLE_HD_CAMERA_FIXTURE_FORCE case=width17_lower arena=(17,7) camera=(-999,999)"]
    rows.extend(f"BATTLE_HD_CAMERA_FIXTURE_MEASURE case={name} arena=({width},7) camera=({camera},0) unit0=({unit},3)"
                for name, width, camera, unit in cases)
    rows.extend(["BATTLE_HD_CAMERA_FIXTURE_RESTORED arena=(16,7) camera=(0,0) unit0_xy_word=00030001",
                 "BATTLE_HD_CAMERA_FIXTURE_COMPLETE proof=forced_hidden_clamp_recenter_not_natural_arena"])
    return "\n".join(rows) + "\n"


def test_camera_fixture_is_bound_to_measured_returns_and_restore(directory: Path) -> None:
    result = check(directory, camera_observation_rows())
    camera = result["camera_measurements"]
    assert camera["sequence_completed"] and all(value["passed"] for value in camera["checks"].values()), camera
    assert not result["claims"]["input"]["passed"] and not result["claims"]["render"]["passed"]
    for old, new in (("case=recenter_right arena=(20,7) camera=(3,0)", "case=recenter_right arena=(20,7) camera=(4,0)"),
                     ("RESTORED arena=(16,7) camera=(0,0)", "RESTORED arena=(16,7) camera=(3,0)"),
                     ("BATTLE_HD_CAMERA_FIXTURE_COMPLETE", "BATTLE_HD_NOT_COMPLETE")):
        bad = check(directory / str(len(new)), camera_observation_rows().replace(old, new))
        assert not bad["camera_measurements"]["sequence_completed"]


def lifecycle_observation_rows() -> str:
    return "\n".join([
        "BATTLE_HD_LIFECYCLE_ENTRY battle=00000000 render=0a21f030 hook=0040ad40 input_bounds=(1,1,1250,692) surface=(1280,720)",
        "BATTLE_HD_LIFECYCLE_BANNER_DRAW rect=(405,267,746,451) render=0051d4c0 saved_render=0a21f030 hook=004617a0",
        "BATTLE_HD_LIFECYCLE_FORCE_BANNER_DISMISS old_eax=00000000 new_eax=1",
        "BATTLE_HD_LIFECYCLE_BANNER_RESTORED render=0a21f030 expected=0a21f030 hook=0042e8b0 expected_hook=0042e8b0 mouse=(4,360)",
        "BATTLE_HD_LIFECYCLE_COMMAND_RETURN case=disabled attack=0 descriptor_state=1 avail=1 enabled=0",
        "BATTLE_HD_LIFECYCLE_COMMAND_RETURN case=enabled attack=1 descriptor_state=2 avail=10 enabled=3",
        "BATTLE_HD_LIFECYCLE_MODAL_DRAW rect=(405,267,746,451) no=(637,375) yes=(432,375) callbacks=(0042dad0,0042dab0) render=0051d4c0 saved_render=0a21f030",
        "BATTLE_HD_LIFECYCLE_MODAL_CALLBACK_RETURN yes=1",
        "BATTLE_HD_LIFECYCLE_MODAL_RESTORED render=0a21f030 expected=0a21f030 mouse=(576,360) result=1",
        "BATTLE_HD_LIFECYCLE_RESULTS_ENTRY battle=0a20e050 attacker=04233f16 defender=04234a6a building=00000000",
        "BATTLE_HD_LIFECYCLE_RESULTS_RETURN battle=0a20e050 result=1",
        "BATTLE_HD_LIFECYCLE_RESULTS_GEOMETRY origin=(256,271) size=(640,178) scope=1 renderer=0a21f030",
        "BATTLE_HD_LIFECYCLE_RESULTS_COPY ret=004454f5 src=00000000 dst=0a53c330 source=(256,271,895,448) destination=(0,0)",
        "BATTLE_HD_LIFECYCLE_RESULTS_COPY ret=0044589f src=0a53c330 dst=00000000 source=(0,0,639,177) destination=(256,271)",
        "BATTLE_HD_LIFECYCLE_CURSOR_QUEUED ret=0042da46 logical=(576,360) shifted=(00009000,00005a00) raw=(0000001e,7fffffe1) shift=6",
        "BATTLE_HD_LIFECYCLE_CURSOR_QUEUED ret=0042de6e logical=(576,360) shifted=(00009000,00005a00) raw=(00000001,0000026d) shift=6",
        "BATTLE_HD_LIFECYCLE_CURSOR_QUEUED ret=00566533 logical=(576,360) shifted=(00009000,00005a00) raw=(0000026d,eed9b111) shift=6",
        "BATTLE_HD_LIFECYCLE_CURSOR_POST_POLL ret=00566533 logical=(4,360) shifted=(00000100,00005a00) raw=(00000001,0000026d) shift=6",
        "BATTLE_HD_LIFECYCLE_RESULTS_SCOPE_RESTORED scope=0 renderer=0a21f030 expected=0a21f030 hook=0042e8b0",
        "BATTLE_HD_LIFECYCLE_BATTLE_FREED battle=00000000",
        "BATTLE_HD_LIFECYCLE_OWNER_RESTORED battle=00000000 render=0051d4c0 hook=0040ad40 expected_hook=0040ad40 input_bounds=(1,1,1250,692) surface=(1280,720)",
        "BATTLE_HD_LIFECYCLE_UNIT_ATTACK_CONTINUATION battle=00000000 result=1 render=0051d4c0 hook=0040ad40",
        "BATTLE_HD_LIFECYCLE_MAP_POLL battle=00000000 render=0a21f030 hook=0040ad40 input_bounds=(1,1,1250,692) surface=(1280,720)",
        "BATTLE_HD_LIFECYCLE_MAP_REDRAW_RETURNED proof=forced_hidden_owner_call",
    ]) + "\n"


def test_lifecycle_route_does_not_prove_pixels_or_cursor_return(directory: Path) -> None:
    result = check(directory, lifecycle_observation_rows())
    lifecycle = result["lifecycle_measurements"]
    assert lifecycle["sequence_completed"] and result["claims"]["runtime_health"]["passed"], lifecycle
    assert not lifecycle["checks"]["banner_cursor_return"]["passed"]
    assert lifecycle["checks"]["modal_cursor_return"]["passed"]
    assert lifecycle["checks"]["owner_hook_and_map_state_restore"]["passed"]
    assert lifecycle["checks"]["results_geometry"]["passed"] and lifecycle["checks"]["results_copy_rectangles"]["passed"]
    assert lifecycle["checks"]["results_scope_restore"]["passed"] and lifecycle["checks"]["cursor_targets_queued"]["passed"]
    assert not lifecycle["checks"]["results_cursor_return"]["passed"]
    assert lifecycle["post_return_composition_proven"] is False
    assert not result["claims"]["return"]["passed"] and not result["claims"]["visible"]["passed"]
    wrong = check(directory / "map", lifecycle_observation_rows().replace("MAP_POLL battle=00000000 render=0a21f030", "MAP_POLL battle=00000000 render=0051d4c0"))
    assert wrong["lifecycle_measurements"]["sequence_completed"]
    assert not wrong["lifecycle_measurements"]["checks"]["owner_hook_and_map_state_restore"]["passed"]
    missing = check(directory / "freed", lifecycle_observation_rows().replace("BATTLE_HD_LIFECYCLE_BATTLE_FREED", "BATTLE_HD_NOT_FREED"))
    assert not missing["lifecycle_measurements"]["sequence_completed"]
    misplaced = check(directory / "results-copy", lifecycle_observation_rows().replace("destination=(256,271)", "destination=(0,150)"))
    assert not misplaced["lifecycle_measurements"]["checks"]["results_copy_rectangles"]["passed"]


def test_identity_cannot_be_forged_by_a_pass_flag(directory: Path) -> None:
    paths = fixture(directory)
    manifest = hd.load_json(paths[1])
    manifest.update(stage=hd.EXPECTED_STAGE.replace("battlehd", "battlecenter"), resolution=[800, 600], passed=True)
    write_json(paths[1], manifest)
    result = hd.build_summary(*paths)
    assert not result["claims"]["identity"]["passed"]
    assert not result["claims"]["geometry"]["passed"]
    assert not hd.candidate_is_isolated(r"C:\ClashTests\..\Clash\clash95.exe")
    assert not hd.candidate_is_isolated(r"C:\ClashTestsOther\candidate.exe")
    paths = fixture(directory)
    paths[0].write_text(complete_observation_rows() + "BATTLE_HD_ENTRY eip=0042e9e0\n", encoding="utf-8")
    assert not hd.build_summary(*paths)["claims"]["identity"]["passed"]
    paths = fixture(directory)
    patch = hd.load_json(paths[2])
    patch["status_counts"] = {"patched": 150, "original": 1, "unexpected": 0}
    write_json(paths[2], patch)
    assert not hd.build_summary(*paths)["claims"]["identity"]["passed"]
    patch["status_counts"] = {"patched": 150}  # Actual report Counter serialization.
    write_json(paths[2], patch)
    assert hd.build_summary(*paths)["claims"]["identity"]["passed"]
    patch["exe"] = r"C:\ClashTests\battlehd\same-sha-review.exe"
    write_json(paths[2], patch)
    bound = hd.build_summary(*paths)
    assert bound["claims"]["identity"]["passed"]
    assert bound["candidate"] != bound["patch_verification"]["candidate"]
    patch["exe_sha256"] = "B" * 64
    write_json(paths[2], patch)
    assert not hd.build_summary(*paths)["claims"]["identity"]["passed"]
    patch["exe_sha256"] = "A" * 64
    patch["patch_count"] = 151
    write_json(paths[2], patch)
    assert not hd.build_summary(*paths)["claims"]["identity"]["passed"]


def test_actual_grid_and_pan_results_are_checked(directory: Path) -> None:
    bad_grid = complete_observation_rows().replace("cell=(19,6)", "cell=(6,6) matched=1")
    assert not check(directory / "grid", bad_grid)["claims"]["input"]["passed"]
    bad_pan = complete_observation_rows().replace("camera_after_repeat=(3,0)", "camera_after_repeat=(4,0) matched=1")
    assert not check(directory / "pan", bad_pan)["claims"]["input"]["passed"]
    missing_modal = complete_observation_rows().replace("BATTLE_HD_MODAL_RESULT", "BATTLE_HD_NOT_A_MODAL_RESULT")
    assert not check(directory / "modal", missing_modal)["claims"]["modal"]["passed"]
    missing_health = complete_observation_rows().replace("BATTLE_HD_MAP_HEALTH", "BATTLE_HD_NOT_MAP_HEALTH")
    assert not check(directory / "health", missing_health)["claims"]["return"]["passed"]


def test_forced_and_automated_evidence_stay_distinct(directory: Path) -> None:
    automated = check(directory / "auto")
    assert automated["evidence_class"] == "automated_runtime"
    forced = check(directory / "forced", complete_observation_rows() + "BATTLE_COMMAND_CLICK_GATE_FORCE eax=1\n")
    assert forced["claims"]["route_catalog"]["passed"]
    assert forced["evidence_class"] == "forced_validation" and not forced["claims"]["unforced_runtime"]["passed"]
    crash = check(directory / "crash", complete_observation_rows() + "Access violation - code c0000005\n")
    assert not crash["claims"]["runtime_health"]["passed"] and not crash["claims"]["geometry"]["passed"]
    failed = check(directory / "lifecycle-fail", complete_observation_rows() + "BATTLE_HD_LIFECYCLE_FAIL disabled_command_changed_state\n")
    assert not failed["claims"]["runtime_health"]["passed"]
    assert any("BATTLE_HD_LIFECYCLE_FAIL" in item for item in failed["claims"]["runtime_health"]["failures"])


def test_approval_and_frame_assertions_are_not_proof(directory: Path) -> None:
    paths = fixture(directory)
    forged = hd.load_json(paths[1]) | {"approved": True, "approval_record": "placeholder", "passed": True,
                                    "composition_checks": {key: True for key in ("battlefield", "hud", "frame", "banner", "modal", "post_return_map")}}
    visible = write_json(directory / "visible.json", forged)
    result = hd.build_summary(*paths, visible_proof=visible)
    assert not result["claims"]["visible"]["passed"]
    assert any("frame" in message for message in result["claims"]["visible"]["failures"])


def test_cli_missing_evidence_fails_closed(directory: Path) -> None:
    directory.mkdir(parents=True)
    output = directory / "summary.json"
    run = subprocess.run([sys.executable, str(Path(hd.__file__)), str(directory / "absent.log"),
                          "--write-json", str(output), "--require-pass"], capture_output=True, text=True)
    assert run.returncode == 2, run.stdout + run.stderr
    assert not hd.load_json(output)["passed"]


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="clash-battle-hd-fixtures-") as name:
        base = Path(name)
        tests = [value for key, value in globals().copy().items() if key.startswith("test_") and callable(value)]
        for index, test in enumerate(tests):
            test(base / str(index))
    print("battle HD summary tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
