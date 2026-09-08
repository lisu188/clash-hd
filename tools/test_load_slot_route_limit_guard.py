#!/usr/bin/env python3
"""Tests for load_slot_route_limit_guard.py."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import load_slot_route_limit_guard as guard


DECOMP_TEXT = """
int __usercall sub_4443C0@<eax>(int a1@<eax>, int a2@<edx>)
{
  return sprintf_(a2, "save\\\\%d.dat", a1);
}
int __usercall sub_44A110@<eax>(int a1@<eax>, DWORD a2@<ebp>)
{
  result = sub_444750(dword_5441E0, a2);
  if ( result )
  {
    dword_544190 = 1;
    dword_543D78 = 1;
  }
  return result;
}
case 5:
  for ( k = 0; k < 10; sub_44A140(k, (DWORD)a3) )
    ;
  if ( v108 <= 9 )
  {
    dword_5441E0 = ((dword_544D00 >> byte_54512C) - 155) / 22;
    sub_44A110(0, (DWORD)a3);
  }
  sub_444490(a2, (DWORD)a3, a4);
void *__usercall sub_44A140@<eax>(int a1@<eax>, DWORD a2@<ebp>)
{
  v4 = (unsigned __int16)(22 * a1 + 155);
  UI_DrawTextFmt(v4, 244, 410, 22 * a1 + 155, 3, (int)v7);
}
"""
HARNESS_TEXT = r"""
[ValidateRange(0,9)]
[int]$LoadSlot = 0
$probeRenderer = Join-Path $RepoRoot 'tools\render_cdb_surface_probe.py'
$renderArgs = @('-B', $probeRenderer, '--template', $ProbeTemplate, '--resolution', $Resolution, '--stage', $recipeStage, '--load-slot', $LoadSlot)
if ($ExtraProbeTemplate) { $renderArgs += '--extra-probe' }
$probeRecipeJson = & $pythonExe @renderArgs
if ($LASTEXITCODE -ne 0) {
    throw 'Surface probe resolution preflight failed; no candidate was built.'
}
$probeRecipe = $probeRecipeJson | ConvertFrom-Json
$surfaceGeometry = $probeRecipe.geometry
$Resolution = $surfaceGeometry.resolution
$probeText = $probeRecipe.template
$loadMouseX = $surfaceGeometry.load_mouse[0]
$loadMouseY = $surfaceGeometry.load_mouse[1]
$loadMouseRawX = $loadMouseX -shl 6
$loadMouseRawY = $loadMouseY -shl 6
$probeText = $probeText.Replace('__LOAD_SLOT__', [string]$LoadSlot)
$probeText = $probeText.Replace('__LOAD_MOUSE_RAW_X__', ('{0:x8}' -f $loadMouseRawX))
$probeText = $probeText.Replace('__LOAD_MOUSE_RAW_Y__', ('{0:x8}' -f $loadMouseRawY))
"""
STAGE = "gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch"


def success_log(slot: int) -> str:
    y = 166 + (22 * slot)
    return (
        f"route-injects load slot {slot}, waits for gameplay redraw, then dumps dword_5202E0\n"
        f"SURFDUMP_LOAD_COORD seq=0 choice=5 entry=0x000efa5d ex=232 ey=228 mouse=(320,{y}) selected=0 accept=0\n"
        f"SURFDUMP_FORCE_LOAD_SELECT seq=0 mouse=(320,{y}) selected=-1 accept=0\n"
        f"SURFDUMP_FORCE_LOAD_ACCEPT seq=0 selected={slot} accept=0 mouse=(320,{y})\n"
        f"SURFDUMP_LOAD_ACCEPT_CALL arg=0 selected={slot} accept_before=0 mouse=(320,{y})\n"
        f"SURFDUMP_LOADSAVE selected_arg={slot} selected_global={slot} accept=1 choice=5 gd=03fe0030\n"
        "SURFDUMP_PLAYGAME gd=03fe0030 map=(50,50) scroll=(39,42) surface=03fac880 size=(640,480)\n"
    )


def blocked_log(slot: int, *, force: bool = False, loadsave: bool = False) -> str:
    y = 166 + (22 * slot)
    text = (
        f"route-injects load slot {slot}, waits for gameplay redraw, then dumps dword_5202E0\n"
        f"SURFDUMP_LOAD_COORD seq=0 choice=5 entry=0x000efa5d ex=232 ey=228 mouse=(320,{y}) selected=0 accept=0\n"
    )
    if force:
        text += f"SURFDUMP_FORCE_LOAD_SELECT seq=0 mouse=(320,{y}) selected=-1 accept=0\n"
    if loadsave:
        text += (
            f"SURFDUMP_LOADSAVE selected_arg={slot} selected_global={slot} accept=1 choice=5 gd=03fe0030\n"
            "SURFDUMP_PLAYGAME gd=03fe0030 map=(50,50) scroll=(39,42) surface=03fac880 size=(640,480)\n"
        )
    return text


def write_run(
    root: Path,
    name: str,
    *,
    slot: int,
    log_text: str,
    passed: bool,
    timed_out: bool,
) -> Path:
    run = root / name
    run.mkdir()
    (run / "summary.json").write_text(
        json.dumps(
            {
                "Passed": passed,
                "TimedOut": timed_out,
                "HiddenDesktop": True,
                "AllowVisibleDesktop": False,
                "UseDdrawProxy": True,
                "SkipMapValidation": True,
                "FastForwardStartAnims": True,
                "Stage": STAGE,
                "CandidateSha256": "F3BC",
                "LoadSlot": slot,
                "Av": False,
                "PngPath": str(run / "surface.png"),
                "TimeoutStackLog": str(run / "timeout-stack.log") if timed_out else None,
            }
        ),
        encoding="utf-8",
    )
    (run / "cdb-surface-dump.log").write_text(log_text, encoding="utf-8")
    return run


def write_fixture(
    root: Path,
    *,
    decomp_text: str = DECOMP_TEXT,
    slot2_log: str | None = None,
    slot3_log: str | None = None,
    recent_slot5_log: str | None = None,
) -> dict[str, Path]:
    decomp = root / "clash95.c"
    harness = root / "scripts/cdb/run_cdb_surface_dump.ps1"
    decomp.write_text(decomp_text, encoding="utf-8")
    harness.parent.mkdir(parents=True, exist_ok=True)
    harness.write_text(HARNESS_TEXT, encoding="utf-8")
    renderer_path = root / "tools/render_cdb_surface_probe.py"
    renderer_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(Path(guard.probe_renderer.__file__), renderer_path)
    return {
        "decomp": decomp,
        "harness": harness,
        "slot2": write_run(root, "slot2", slot=2, log_text=slot2_log or success_log(2), passed=True, timed_out=False),
        "slot3": write_run(root, "slot3", slot=3, log_text=slot3_log or blocked_log(3), passed=False, timed_out=True),
        "slot4": write_run(root, "slot4", slot=4, log_text=blocked_log(4), passed=False, timed_out=True),
        "slot5": write_run(root, "slot5", slot=5, log_text=blocked_log(5), passed=False, timed_out=True),
        "recent_slot5": write_run(
            root,
            "recent_slot5",
            slot=5,
            log_text=recent_slot5_log or blocked_log(5),
            passed=False,
            timed_out=True,
        ),
    }


def build(paths: dict[str, Path]) -> dict[str, object]:
    return guard.build_report(
        decomp_c=paths["decomp"],
        surface_probe_script=paths["harness"],
        slot2_run=paths["slot2"],
        slot3_run=paths["slot3"],
        slot4_run=paths["slot4"],
        slot5_run=paths["slot5"],
        recent_slot5_run=paths["recent_slot5"],
    )


def test_passes_current_route_limit_shape() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        report = build(write_fixture(Path(tmp)))
    assert report["passed"], report
    assert report["summary"]["static_load_rows"] == "0..9"
    assert report["summary"]["archived_success_slots"] == [2]
    assert report["summary"]["archived_blocked_slots"] == [3, 4, 5]
    assert report["promotion_ready"] is False
    assert "historical" in report["summary"]["current_boundary"]
    assert "do not reopen" in report["summary"]["current_boundary"]


def test_current_harness_and_all_slots_use_canonical_native_geometry() -> None:
    report = guard.check_surface_geometry(guard.DEFAULT_SURFACE_PROBE_SCRIPT)
    assert report["passed"], report
    generated = report["generated_geometry"]
    assert len(generated["rows"]) == 20
    assert generated["source_sha256"]
    for row in generated["rows"]:
        x, y = row["mouse"]
        # Independently apply the native hit-test bounds and row division.
        assert 244 <= x <= 410
        assert (y - 155) // 22 == row["slot"]
        assert x == 320 and y == 166 + 22 * row["slot"]


def test_fails_on_broken_canonical_harness_wiring() -> None:
    mutations = [
        ("[ValidateRange(0,9)]", "[ValidateRange(0,5)]"),
        ("tools\\render_cdb_surface_probe.py", "tools\\other_probe.py"),
        ("'--load-slot', $LoadSlot", "'--load-slot', 0"),
        ("'--resolution', $Resolution", "'--resolution', '640x480'"),
        ("'--stage', $recipeStage", "'--stage', 'other-stage'"),
        ("'--template', $ProbeTemplate", "'--template', 'unrelated.cdb'"),
        ("$probeRecipeJson = & $pythonExe @renderArgs", "$probeRecipeJson = '{}'"),
        ("if ($LASTEXITCODE -ne 0)", "if ($LASTEXITCODE -eq 0)"),
        ("throw 'Surface probe", "Write-Warning 'Surface probe"),
        ("$probeRecipe = $probeRecipeJson | ConvertFrom-Json", "$probeRecipe = $cachedRecipe"),
        ("$surfaceGeometry = $probeRecipe.geometry", "$surfaceGeometry = $other.geometry"),
        ("$probeText = $probeRecipe.template", "$probeText = $oldTemplate"),
        ("$loadMouseX = $surfaceGeometry.load_mouse[0]", "$loadMouseX = $surfaceGeometry.load_mouse[1]"),
        ("$loadMouseY = $surfaceGeometry.load_mouse[1]", "$loadMouseY = 166 + (22 * $LoadSlot)"),
        ("$loadMouseRawX = $loadMouseX -shl 6", "$loadMouseRawX = $loadMouseX -shl 5"),
        ("$loadMouseRawY = $loadMouseY -shl 6", "$loadMouseRawY = $loadMouseX -shl 6"),
        ("('__LOAD_SLOT__', [string]$LoadSlot)", "('__LOAD_SLOT__', '0')"),
        ("'__LOAD_MOUSE_RAW_Y__', ('{0:x8}' -f $loadMouseRawY)", "'__LOAD_MOUSE_RAW_Y__', ('{0:x8}' -f $loadMouseRawX)"),
        ("$surfaceGeometry = $probeRecipe.geometry", "# $surfaceGeometry = $probeRecipe.geometry"),
        ("$loadMouseX = $surfaceGeometry.load_mouse[0]", "<#\n$loadMouseX = $surfaceGeometry.load_mouse[0]\n#>"),
        ("$loadMouseX = $surfaceGeometry.load_mouse[0]", "$loadMouseX = $surfaceGeometry.load_mouse[0]\n$loadMouseX = 0"),
        ("$loadMouseX = $surfaceGeometry.load_mouse[0]\n$loadMouseY = $surfaceGeometry.load_mouse[1]", "$loadMouseY = $surfaceGeometry.load_mouse[1]\n$loadMouseX = $surfaceGeometry.load_mouse[0]"),
    ]
    with tempfile.TemporaryDirectory() as tmp:
        paths = write_fixture(Path(tmp))
        for old, new in mutations:
            assert old in HARNESS_TEXT, old
            paths["harness"].write_text(HARNESS_TEXT.replace(old, new), encoding="utf-8")
            report = build(paths)
            assert not report["passed"], (old, report)
            assert any("harness:" in failure for failure in report["failures"]), (old, report)
        paths["harness"].unlink()
        assert not build(paths)["passed"]


def test_fails_on_canonical_generator_geometry_drift_or_missing_source() -> None:
    render = guard.probe_renderer.render_probe
    for field, value in (("load_mouse", [320, 160]), ("load_mouse", [166, 320]),
                         ("load_input_space", "centered_menu"), ("resolution", "640x480")):
        def bad_recipe(*args: object, **kwargs: object) -> dict[str, object]:
            result = render(*args, **kwargs)
            # Catch drift at just one normally overlooked slot, not only rows 3-5.
            if kwargs.get("load_slot") == 9:
                result["geometry"][field] = value
            return result
        with patch.object(guard.probe_renderer, "render_probe", side_effect=bad_recipe):
            report = guard.check_generated_geometry()
        assert not report["passed"], (field, report)
        assert all("row 9" in failure for failure in report["failures"]), report
    with tempfile.TemporaryDirectory() as tmp:
        with patch.object(guard.probe_renderer, "BASE_PROBE", Path(tmp) / "missing.cdb"):
            assert not guard.check_generated_geometry()["passed"]


def test_fails_if_canonical_generator_accepts_out_of_range_slot() -> None:
    render = guard.probe_renderer.render_probe
    def accepts_bad_slot(*args: object, **kwargs: object) -> dict[str, object]:
        kwargs["load_slot"] = max(0, min(9, kwargs["load_slot"]))
        return render(*args, **kwargs)
    with patch.object(guard.probe_renderer, "render_probe", side_effect=accepts_bad_slot):
        report = guard.check_generated_geometry()
    assert not report["passed"]
    assert len(report["failures"]) == 4, report
    assert all("out-of-range slot" in failure for failure in report["failures"])


def test_fails_without_static_ten_row_evidence() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        report = build(write_fixture(Path(tmp), decomp_text=DECOMP_TEXT.replace("k < 10", "k < 5")))
    assert not report["passed"]
    assert any("draws_ten_rows" in failure for failure in report["failures"])


def test_fails_when_slot2_no_longer_loads() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        report = build(write_fixture(Path(tmp), slot2_log=blocked_log(2)))
    assert not report["passed"]
    assert any("slot2_success" in failure and "LOADSAVE" in failure for failure in report["failures"])


def test_fails_when_blocked_slot_loads() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        report = build(write_fixture(Path(tmp), slot3_log=blocked_log(3, loadsave=True)))
    assert not report["passed"]
    assert any("slot3_blocked" in failure and "LOADSAVE" in failure for failure in report["failures"])


def test_fails_when_blocked_slot_reaches_force_select() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        report = build(write_fixture(Path(tmp), recent_slot5_log=blocked_log(5, force=True)))
    assert not report["passed"]
    assert any("recent_slot5_blocked" in failure and "forced load-select" in failure for failure in report["failures"])


def test_cli_writes_outputs_and_requires_pass() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        paths = write_fixture(root)
        output_json = root / "out.json"
        output_md = root / "out.md"
        result = subprocess.run(
            [
                sys.executable,
                str(Path(guard.__file__)),
                "--decomp-c",
                str(paths["decomp"]),
                "--surface-probe-script",
                str(paths["harness"]),
                "--slot2-run",
                str(paths["slot2"]),
                "--slot3-run",
                str(paths["slot3"]),
                "--slot4-run",
                str(paths["slot4"]),
                "--slot5-run",
                str(paths["slot5"]),
                "--recent-slot5-run",
                str(paths["recent_slot5"]),
                "--write-json",
                str(output_json),
                "--write-markdown",
                str(output_md),
                "--require-pass",
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        assert output_json.exists()
        assert output_md.exists()


def test_shared_renderer_path_and_actual_rows() -> None:
    repo = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory() as tmp:
        paths = write_fixture(Path(tmp))
        shutil.copyfile(repo / "scripts/cdb/run_cdb_surface_dump.ps1", paths["harness"])
        renderer_path = Path(tmp) / "tools/render_cdb_surface_probe.py"
        renderer_path.parent.mkdir(exist_ok=True)
        shutil.copyfile(repo / "tools/render_cdb_surface_probe.py", renderer_path)
        report = build(paths)
        assert report["passed"], report["failures"]
        contract = report["harness"]
        assert contract["source_mode"] == "shared_python_recipe"
        assert [row["logical"] for row in contract["row_geometry"]] == [[320, 166 + 22 * slot] for slot in range(10)]
        raw = renderer_path.read_text(encoding="utf-8")
        renderer_path.write_text(raw.replace('"load_mouse": [320, 166 + 22 * load_slot]', '"load_mouse": [320, 160 + 22 * load_slot]'), encoding="utf-8")
        report = build(paths)
        assert not report["harness"]["passed"], report


def test_commented_inline_formula_is_not_code() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        paths = write_fixture(Path(tmp))
        for fake in ("\n".join("# " + line for line in HARNESS_TEXT.splitlines()),
                     "<#\n" + HARNESS_TEXT + "\n#>", "$example = @'\n" + HARNESS_TEXT + "\n'@"):
            paths["harness"].write_text(fake, encoding="utf-8")
            report = build(paths)
            assert not report["harness"]["passed"], report


def run_tests() -> None:
    test_shared_renderer_path_and_actual_rows()
    test_commented_inline_formula_is_not_code()
    test_passes_current_route_limit_shape()
    test_current_harness_and_all_slots_use_canonical_native_geometry()
    test_fails_on_broken_canonical_harness_wiring()
    test_fails_on_canonical_generator_geometry_drift_or_missing_source()
    test_fails_if_canonical_generator_accepts_out_of_range_slot()
    test_fails_without_static_ten_row_evidence()
    test_fails_when_slot2_no_longer_loads()
    test_fails_when_blocked_slot_loads()
    test_fails_when_blocked_slot_reaches_force_select()
    test_cli_writes_outputs_and_requires_pass()


if __name__ == "__main__":
    run_tests()
    print("load_slot_route_limit_guard tests passed")
