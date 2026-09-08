#!/usr/bin/env python3
"""Repo-only renderer, visibility-span and harness-contract fixtures; no game/CDB."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import render_cdb_surface_probe as render
import surface_dump_policy_guard
import visibility_coverage


PROFILES = ("800x600", "802x602", "1024x768", "1280x720", "1280x960", "1920x1080", "3840x2160")
STAGE = render.patcher.DEFAULT_STAGE + "-combinedui-validation"
HARNESS = render.ROOT / "scripts/cdb/run_cdb_surface_dump.ps1"


def expression(text: str, *, regs: dict[str, int], memory: dict[int, int]) -> int:
    """Small fixture MASM expression subset, evaluated against synthetic memory."""
    text = re.sub(r"0n(\d+)", r"\1", text)
    text = text.replace("005202e4", "0x5202e4").replace("005202ec", "0x5202ec")
    text = re.sub(r"@\$(t\d+)", lambda m: str(regs[m[1]]), text)
    text = text.replace("@eax", str(regs.get("eax", 0))).replace("@edx", str(regs.get("edx", 0)))
    return int(eval(text, {"__builtins__": {}}, {"poi": lambda a: memory[a], "by": lambda a: memory[a] & 255}))


class RendererTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.base_bytes = render.BASE_PROBE.read_bytes()
        cls.base = cls.base_bytes.decode("utf-8-sig")

    def recipe(self, key: str, **kwargs):
        return render.render_probe(self.base, key, STAGE, **kwargs)

    def test_legacy_is_exact_and_does_not_mutate_base(self):
        for forced in (False, True):
            report = self.recipe("800x600", force_visible_edges=forced)
            self.assertEqual(report["template"], self.base)
            self.assertIsNone(report["force_playgame_action"])
            self.assertEqual(report["geometry"]["expected_vedge_count"], 54)
            self.assertEqual(report["geometry"]["visibility_dump_max_bytes"], 160)
        self.assertEqual(render.BASE_PROBE.read_bytes(), self.base_bytes)

    def test_fail_closed_unsupported_inputs_and_template_drift(self):
        for key in ("640x480", "801x600", "800x601", "8192x9000", "garbage"):
            with self.assertRaises(ValueError):
                self.recipe(key)
        for option in ({"extra_probe": True}, {"canonical_template": False}, {"post_owner_force_visible_seven": True}, {"load_slot": 1, "force_visible_edges": True}, {"skip_map_validation": True}, {"load_slot": -1}, {"load_slot": 10}):
            with self.assertRaises(ValueError):
                self.recipe("1024x768", **option)
        with self.assertRaises(ValueError):
            render.render_probe(self.base.replace("L0n160", "L0n159"), "1024x768", STAGE)
        with self.assertRaises(ValueError):
            render.render_probe(self.base, "1024x768", "unknown-stage")

    def test_geometry_and_edge_selection_from_rendered_conditions(self):
        for key in PROFILES[1:]:
            report = self.recipe(key, force_visible_edges=True)
            g, text = report["geometry"], report["template"]
            width, height = map(int, key.split("x"))
            self.assertEqual((g["columns"], g["rows"]), ((width-32)//64, (height-16)//64))
            self.assertEqual(text.count(f"@$t16*0n{width}"), 3)
            first = next(line for line in text.splitlines() if line.startswith("bp 00416850 "))
            condition = first.split("& ((@eax", 1)[1].split(") { r @$t6", 1)[0]
            condition = "((@eax" + condition
            actual = set()
            for row in range(g["rows"] + 2):
                for col in range(g["columns"] + 2):
                    if expression(condition, regs={"eax": 32 + 64*col, "edx": 16 + 64*row}, memory={}):
                        actual.add((col, row))
            expected = {(col, row) for col in (0, g["columns"]-2, g["columns"]-1) for row in range(3, g["rows"])}
            self.assertEqual(actual, expected, key)
            self.assertEqual(g["expected_vedge_count"], len(actual) * 3)
            for bad_y in (207, 209, height, -48):
                self.assertFalse(expression(condition, regs={"eax": 32, "edx": bad_y}, memory={}))

    def test_centered_main_menu_and_native_load_list_are_distinct(self):
        for key in PROFILES:
            profile = render.patcher.parse_resolution(key)
            selected = render.patcher.select_patches_for(STAGE, profile)
            descriptors = {p.offset: int.from_bytes(p.new, "little") for p in selected if p.group == "menu-center-hitboxes"}
            main_x, main_y = self.recipe(key)["geometry"]["main_menu_mouse"]
            # The known legacy interior point remains at the same displacement
            # from the actual generated first menu descriptor, at every size.
            self.assertEqual(main_x - descriptors[0x1163C0], 61)
            self.assertEqual(main_y - descriptors[0x1163C4], 22)
            first = next(line for line in self.recipe(key)["template"].splitlines() if line.startswith("bp 00419B80 "))
            self.assertIn(f"ed 00544cfc {main_x << 6:08x}; ed 00544d00 {main_y << 6:08x};", first)
            # VA448A68 uses the native list geometry without centering. Assert
            # no selected patch changes that consumer before relying on it.
            native_start, native_end = 0x448A68-0x400C00, 0x448AD9-0x400C00
            self.assertFalse(any(p.offset < native_end and p.offset+len(p.new) > native_start for p in selected))
            for slot in range(10):
                coords = self.recipe(key, load_slot=slot)["geometry"]["load_mouse"]
                self.assertTrue(244 <= coords[0] <= 410)
                self.assertEqual((coords[1]-155)//22, slot)
                self.assertEqual(coords, [320, 166+22*slot])

    def test_rendered_dump_covers_every_cell_without_crossing_last_byte(self):
        gd = 0x10000000
        for key in PROFILES[1:]:
            report = self.recipe(key)
            text, g = report["template"], report["geometry"]
            dump = re.search(r"; db (?P<address>.*?) L(?P<count>.*?); __SURFACE_DUMP_ACTION__", text)
            self.assertIsNotNone(dump)
            count_assignment = re.search(r'r @\$t18 = (.*?); \.printf \\\"SCROLL_VISDUMP', text)
            self.assertIsNotNone(count_assignment)
            for my in range(8):
                mx = 100-g["columns"]
                mem = {gd+140008: mx, gd+140012: my}
                start = expression(dump["address"], regs={"t10": gd}, memory=mem)
                t18 = expression(count_assignment[1], regs={"t10": gd}, memory=mem)
                count = expression(dump["count"], regs={"t10": gd, "t18": t18}, memory=mem)
                requested = {gd+140081+(mx+c)*13+((my+r)>>3) for c in range(g["columns"]) for r in range(g["rows"])}
                self.assertEqual(start, min(requested))
                self.assertEqual(start+count-1, max(requested))
                self.assertLessEqual(start+count, gd+140081+1300)
                header = f"SCROLL_VISDUMP player=0 screen0=(32,16) map0=({mx},{my}) rows={g['rows']} cols={g['columns']} tile=(64,64) vis_base={gd+140081:08x} dump_start={start:08x} count={count}"
                lines = [header] + [f"{start+i:08x}  " + " ".join("ff" for _ in range(min(16, count-i))) for i in range(0, count, 16)]
                observations = {}
                match = visibility_coverage.VISDUMP_RE.search(header)
                visibility_coverage.expand_visdump(observations, match, lines, 0, Path("fixture.log"))
                self.assertEqual(len(observations), g["columns"]*g["rows"])
                self.assertTrue(all(row.any_vis_nonzero for row in observations.values()))

    def test_forcing_preserves_other_bits_and_writes_only_requested_edges(self):
        gd = 0x10000000
        for key in PROFILES[1:]:
            report = self.recipe(key, force_visible_edges=True)
            g, action = report["geometry"], report["force_playgame_action"]
            # Actual generated eb address/value expressions, executed with no
            # target process against a deterministic 100x100 visibility array.
            writes = re.findall(r"eb (.*?) (\(by\(.*?);", action)
            self.assertEqual(len(writes), 3)
            before = {gd+140081+i: 0x24 for i in range(1300)}
            memory = dict(before)
            for row in range(3, g["rows"]):
                for address_expr, value_expr in writes:
                    regs = {"t18": gd, "t0": row}
                    address = expression(address_expr, regs=regs, memory=memory)
                    memory[address] = expression(value_expr, regs=regs, memory=memory)
            expected = dict(before)
            for col in (0, g["columns"]-2, g["columns"]-1):
                for row in range(3, g["rows"]):
                    x, y = 10+col, 17+row
                    expected[gd+140081+x*13+(y>>3)] |= 1 << (y & 7)
            self.assertEqual(memory, expected, key)

    def test_map_guard_rejects_wrong_player_small_map_and_scroll_overflow(self):
        gd = 0x10000000
        for key in PROFILES[1:]:
            g = self.recipe(key)["geometry"]
            condition = render.map_guard(g["columns"], g["rows"])
            good = {0x5202e4: gd, 0x5202ec: 0, gd+140000: 100, gd+140004: 100, gd+140008: 100-g["columns"], gd+140012: 100-g["rows"]}
            self.assertFalse(expression(condition, regs={}, memory=good))
            for address, value in ((0x5202ec, 1), (gd+140008, -1), (gd+140012, -1), (gd+140008, 101-g["columns"]), (gd+140012, 101-g["rows"]), (gd+140000, 101), (gd+140004, 101), (gd+140000, g["columns"]-1)):
                self.assertTrue(expression(condition, regs={}, memory={**good, address: value}))

    def test_cli_is_pure_json_and_rejects_extra_before_runtime(self):
        result = subprocess.run([sys.executable, "-B", str(Path(render.__file__)), "--resolution", "1024x768", "--stage", STAGE], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["geometry"]["resolution"], "1024x768")
        self.assertEqual(report["base_probe_sha256"], hashlib.sha256(self.base_bytes).hexdigest())
        result = subprocess.run([sys.executable, "-B", str(Path(render.__file__)), "--resolution", "1024x768", "--extra-probe"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn("separate resolution recipes", result.stderr)

    def test_harness_preserves_hidden_policy_and_threads_geometry(self):
        report = surface_dump_policy_guard.build_guard(argparse.Namespace(script=HARNESS))
        self.assertTrue(report["passed"], report["failures"])
        text = HARNESS.read_text()
        self.assertLess(text.index("$probeRecipeJson = & $pythonExe"), text.index("& $DdrawProxyBuildScript"))
        self.assertIn("--stage $Stage --resolution $Resolution", text)
        self.assertEqual(text.count("SurfaceGeometryMatched = (Test-RequestedSurfaceReady"), 2)
        # Runtime success/failure and the postprocessing failure summary.
        self.assertEqual(text.count("Resolution = $Resolution"), 3)
        self.assertIn("'--columns', $surfaceGeometry.columns, '--rows', $surfaceGeometry.rows", text)
        self.assertIn("--expect-vedge-visret $surfaceGeometry.expected_vedge_count", text)

    @unittest.skipUnless(sys.platform == "win32", "PowerShell AST/isolated function fixture needs Windows")
    def test_powershell_syntax_and_actual_surface_and_runtime_gates(self):
        # Parse, then execute ONLY isolated helper definitions extracted from
        # the AST. Never dot-source or invoke the runtime harness/Add-Type body.
        script = r'''
$ErrorActionPreference = 'Stop'
$tokens = $null
$parseErrors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile($args[0], [ref]$tokens, [ref]$parseErrors)
if ($parseErrors.Count) { throw ($parseErrors | Out-String) }
foreach ($name in @('Convert-CdbHexToUInt64', 'Test-RequestedSurfaceReady', 'Set-SurfaceProxyPresentSetting', 'Restore-SurfaceProxyPresentSetting', 'Get-SurfaceRuntimeFailure')) {
    $functions = @($ast.FindAll({ param($node) $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -eq $name }, $true))
    if ($functions.Count -ne 1) { throw "Expected one isolated helper: $name" }
    . ([scriptblock]::Create($functions[0].Extent.Text))
}
$geometry = [pscustomobject]@{ width=1024; height=768 }
$valid = @{ Width=1024; Height=768; Bytes=786432; Base='10000000'; Surface='11000000' }
if (-not (Test-RequestedSurfaceReady -Ready ([pscustomobject]$valid) -Geometry $geometry)) { throw 'Correct surface rejected' }
foreach ($case in @(@{Width=800}, @{Height=600}, @{Bytes=480000}, @{Base='00000000'}, @{Surface='00000000'})) {
    $row = $valid.Clone()
    foreach ($key in $case.Keys) { $row[$key] = $case[$key] }
    if (Test-RequestedSurfaceReady -Ready ([pscustomobject]$row) -Geometry $geometry) { throw 'Mismatched surface accepted' }
}
if (Test-RequestedSurfaceReady -Ready $null -Geometry $geometry) { throw 'Missing surface accepted' }
# Evaluate the real host assignment and early failure condition with a complete
# synthetic dump. A captured frame must not hide a crash, quit, or host error,
# including the default ContinueAfterDumpSec=0 path.
$assignments = @($ast.FindAll({ param($node) $node -is [System.Management.Automation.Language.AssignmentStatementAst] -and $node.Left.Extent.Text -eq '$runtimeFailure' }, $true))
$gates = @($ast.FindAll({ param($node) $node -is [System.Management.Automation.Language.IfStatementAst] -and $node.Clauses[0].Item1.Extent.Text.StartsWith('-not $ready -or -not $dumpDone -or -not $rawExists') }, $true))
if ($assignments.Count -ne 1 -or $gates.Count -ne 1) { throw 'Missing unique runtime assignment/capture gate' }
$ready = $true
$dumpDone = $true
$rawExists = $true
$surfaceGeometryFailure = $null
$dumpInvalid = $false
foreach ($ContinueAfterDumpSec in @(0, 5)) {
    foreach ($case in @(
        @{Av=$false; Quit=$false; Error=$null; Fail=$false},
        @{Av=$true; Quit=$false; Error=$null; Fail=$true},
        @{Av=$false; Quit=$true; Error=$null; Fail=$true},
        @{Av=$false; Quit=$false; Error='synthetic host read failure'; Fail=$true}
    )) {
        $av = $case.Av
        $appRequestQuit = $case.Quit
        $runtimeError = $case.Error
        . ([scriptblock]::Create($assignments[0].Extent.Text))
        $failed = [bool](& ([scriptblock]::Create($gates[0].Clauses[0].Item1.Extent.Text)))
        if ($failed -ne $case.Fail) { throw 'Completed dump hid runtime failure or rejected healthy capture' }
        if ([bool]$runtimeFailure -ne $case.Fail) { throw 'Runtime failure reason inconsistent with gate' }
    }
}
$originalPresent = [Environment]::GetEnvironmentVariable('CLASH_PROXY_PRESENT', 'Process')
try {
    [Environment]::SetEnvironmentVariable('CLASH_PROXY_PRESENT', '1', 'Process')
    $setting = Set-SurfaceProxyPresentSetting -HiddenDesktop $true
    if ($setting.Previous -ne '1' -or $setting.Effective -ne '0') { throw 'Hidden proxy setting not pinned' }
    Restore-SurfaceProxyPresentSetting -Setting $setting
    if ([Environment]::GetEnvironmentVariable('CLASH_PROXY_PRESENT', 'Process') -ne '1') { throw 'Caller environment not restored' }
    $setting = Set-SurfaceProxyPresentSetting -HiddenDesktop $false
    if ($setting.Effective -ne '1') { throw 'Explicit visible proxy setting changed' }
    Restore-SurfaceProxyPresentSetting -Setting $setting
    [Environment]::SetEnvironmentVariable('CLASH_PROXY_PRESENT', $null, 'Process')
    $setting = Set-SurfaceProxyPresentSetting -HiddenDesktop $true
    Restore-SurfaceProxyPresentSetting -Setting $setting
    if ($null -ne [Environment]::GetEnvironmentVariable('CLASH_PROXY_PRESENT', 'Process')) { throw 'Originally absent setting not restored' }
} finally {
    [Environment]::SetEnvironmentVariable('CLASH_PROXY_PRESENT', $originalPresent, 'Process')
}
Write-Output 'surface function fixture passed'
'''
        with tempfile.TemporaryDirectory(prefix="clash-surface-function-fixture-") as folder:
            path = Path(folder)/"pure-functions.ps1"
            path.write_text(script, encoding="utf-8")
            executable = Path("C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe")
            # Process-local policy only, for this synthetic fixture file. This
            # neither changes machine/user policy nor executes the harness.
            result = subprocess.run([str(executable), "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", str(path), str(HARNESS)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("surface function fixture passed", result.stdout)


class FramedRendererTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base_bytes = render.BASE_PROBE.read_bytes()
        cls.base = cls.base_bytes.decode("utf-8-sig")

    def recipe(self, key, **kwargs):
        return render.render_probe(self.base, key, render.FRAMED_STAGE, **kwargs)

    def test_all_legacy_reports_match_prechange_canonical_hashes(self):
        expected = {
            "800x600":"cec026bd4d9db6145e41fa8404e65f47d21521f4d5048a0a584bee5506ad3878",
            "802x602":"907054b30c77e5996360fc381ac1d7bd8ee449d0ce3a127b2158cdb7c8f53727",
            "1024x768":"d7bafe1cd9e7e11e6d4e3e0b8fcb2c2eac3d35000849c3b72fb431e426c155c4",
            "1280x720":"8105bc5ab89943ca76024de41883d6b9f50876f01029e8936f43e96c83f19554",
            "1280x960":"a1db4e44fffa95d4e19344be4630081887d59fda86c0ec64dd68ae786c05202a",
            "1920x1080":"1c54615fefaa461a22c51c3e8d1152b5c52c5a8b8342f45123e438fcbaf959b6",
            "3840x2160":"a2b5e8d2148671b5a2ab32695f82a23d36723337d71d142eb37f9b421a001ef4",
        }
        for key,digest in expected.items():
            reports=[render.render_probe(self.base,key,STAGE,force_visible_edges=forced) for forced in (False,True)]
            encoded=json.dumps(reports,sort_keys=True,separators=(",",":")).encode()
            self.assertEqual(hashlib.sha256(encoded).hexdigest(),digest,key)

    def test_exact_stage_binds_scalar_recipe_and_framed800_bypasses_legacy(self):
        from src.patcher import framed_recipe
        from src.patcher.framed_viewport import FramedViewport
        for key in PROFILES:
            report=self.recipe(key)
            w,h=map(int,key.split("x")); layout=FramedViewport(w,h)
            g,text=report["geometry"],report["template"]
            self.assertEqual(report["stage"],render.FRAMED_STAGE)
            self.assertEqual(report["scalar_recipe_stage"],framed_recipe.FRAME_BASE_STAGE)
            self.assertEqual((g["width"],g["height"]),(w,h))
            self.assertEqual((g["columns"],g["rows"]),((w-1)//64,(h+31)//64))
            self.assertEqual((g["full_columns"],g["full_rows"]),((w-64)//64,(h-32)//64))
            self.assertEqual((g["partial_col_px"],g["partial_row_px"]),((w-64)%64,(h-32)%64))
            self.assertEqual(g["terrain"],[32,16,w-33,h-17])
            self.assertEqual(g["surface"],[0,0,w-1,h-1])
            self.assertEqual(g["frame_insets"],[32,16,32,16])
            self.assertEqual(g["layout_profile"],"native_four_border_tiles_v1")
            self.assertEqual(text.count(f"@$t16*0n{w}"),3,"physical pixel stride changed")
            self.assertIn(f"rows={g['rows']} cols={g['columns']}",text)
            self.assertIn(f"poi(@$t10+0n140008)+0n{g['full_columns']}",text)
            self.assertIn(f"poi(@$t10+0n140012)+0n{g['full_rows']}",text)
            self.assertIn(f"(@$t12 != 0n{w}) | (@$t15 != 0n{h})",text)
            for ref in report["source_bindings"].values():
                self.assertEqual(hashlib.sha256(Path(ref["path"]).read_bytes()).hexdigest(),ref["sha256"])
            self.assertEqual(g["columns"],layout.ceil_tiles[0])
            self.assertEqual(g["visibility_scope"],"all_ceiling_cells_in_world")
            self.assertEqual(g["vedge_scope"],"native_full_cells_only")
            self.assertIn("no far-world clear proof",g["visibility_limit"])
        framed=self.recipe("800x600")
        self.assertNotEqual(framed["template"],self.base)
        self.assertEqual((framed["geometry"]["columns"],framed["geometry"]["rows"]),(12,9))
        self.assertEqual((framed["geometry"]["full_columns"],framed["geometry"]["full_rows"]),(11,8))
        self.assertEqual(framed["geometry"]["expected_vedge_count"],45)
        self.assertNotEqual(framed["geometry"]["visibility_dump_max_bytes"],160)
        self.assertEqual(render.BASE_PROBE.read_bytes(),self.base_bytes)
        with mock.patch.object(framed_recipe,"select_patches_for",side_effect=ValueError("source binding failed")):
            with self.assertRaisesRegex(ValueError,"source binding failed"):
                self.recipe("800x600")

    def test_generated_framed_edge_predicates_and_fog_writes_match_declared_full_cells(self):
        gd=0x10000000
        for key in PROFILES:
            report=self.recipe(key,force_visible_edges=True)
            g,text,action=report["geometry"],report["template"],report["force_playgame_action"]
            line=next(line for line in text.splitlines() if line.startswith("bp 00416850 "))
            condition="((@eax"+line.split("& ((@eax",1)[1].split(") { r @$t6",1)[0]
            actual={(col,row) for col in range(g["columns"]+2) for row in range(g["rows"]+2)
                    if expression(condition,regs={"eax":32+64*col,"edx":16+64*row},memory={})}
            expected={(col,row) for col in (0,g["full_columns"]-2,g["full_columns"]-1) for row in range(3,g["full_rows"])}
            self.assertEqual(actual,expected,key)
            self.assertEqual(g["expected_vedge_count"],3*len(expected))
            writes=re.findall(r"eb (.*?) (\(by\(.*?);",action)
            self.assertEqual(len(writes),3)
            memory={gd+140081+i:0x24 for i in range(1300)}; wanted=dict(memory)
            for row in range(3,g["full_rows"]):
                for address_expr,value_expr in writes:
                    regs={"t18":gd,"t0":row}
                    address=expression(address_expr,regs=regs,memory=memory)
                    memory[address]=expression(value_expr,regs=regs,memory=memory)
            for col,row in expected:
                wanted[gd+140081+(10+col)*13+((17+row)>>3)] |= 1<<((17+row)&7)
            self.assertEqual(memory,wanted,key)

    def test_framed_visibility_span_and_all_ten_native_load_slots(self):
        gd=0x10000000
        for key in PROFILES:
            report=self.recipe(key);g,text=report["geometry"],report["template"]
            dump=re.search(r"; db (?P<address>.*?) L(?P<count>.*?); __SURFACE_DUMP_ACTION__",text)
            count=re.search(r'r @\$t18 = (.*?); \.printf \\\"SCROLL_VISDUMP',text)
            self.assertIsNotNone(dump);self.assertIsNotNone(count)
            for my in range(8):
                mx=100-g["columns"];memory={gd+140008:mx,gd+140012:my}
                start=expression(dump["address"],regs={"t10":gd},memory=memory)
                length=expression(count[1],regs={"t10":gd},memory=memory)
                addresses={gd+140081+(mx+c)*13+((my+r)>>3) for c in range(g["columns"]) for r in range(g["rows"])}
                self.assertEqual((start,start+length-1),(min(addresses),max(addresses)))
                self.assertLessEqual(start+length,gd+140081+1300)
            for slot in range(10):
                point=self.recipe(key,load_slot=slot)["geometry"]["load_mouse"]
                self.assertEqual(point,[320,166+22*slot])
                self.assertEqual((point[1]-155)//22,slot)
            profile=render.patcher.parse_resolution(key)
            self.assertEqual(g["main_menu_mouse"],[220+profile.off_x,158+profile.off_y])
            # The renderer deliberately restricts this initial screenshot
            # lane, rather than overreading a far-world partial column/row.
            condition=render.map_guard(g["columns"],g["rows"])
            good={0x5202e4:gd,0x5202ec:0,gd+140000:100,gd+140004:100,
                  gd+140008:100-g["columns"],gd+140012:100-g["rows"]}
            self.assertFalse(expression(condition,regs={},memory=good))
            far={**good,gd+140008:100-g["full_columns"],gd+140012:100-g["full_rows"]}
            self.assertTrue(expression(condition,regs={},memory=far))

    def test_framed_exact_stage_options_drift_and_cli_fail_closed(self):
        from src.patcher import framed_recipe
        for stage in (framed_recipe.FRAME_BASE_STAGE,render.FRAMED_STAGE+"-extra",render.FRAMED_STAGE.upper(),None):
            with self.assertRaises((ValueError,KeyError)):
                render.render_probe(self.base,"800x600",stage)
        for key in ("800x600","1024x768"):
            for options in ({"extra_probe":True},{"canonical_template":False},
                    {"post_owner_force_visible_seven":True},{"skip_map_validation":True},
                    {"force_visible_edges":True,"load_slot":1}):
                with self.assertRaises(ValueError):self.recipe(key,**options)
            with self.assertRaises(ValueError):
                render.render_probe(self.base.replace("L0n160","L0n159"),key,render.FRAMED_STAGE)
        result=subprocess.run([sys.executable,"-B",str(Path(render.__file__)),"--resolution","800x600",
                               "--stage",render.FRAMED_STAGE],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        data=json.loads(result.stdout)
        self.assertEqual((data["geometry"]["columns"],data["geometry"]["rows"]),(12,9))
        self.assertEqual((data["geometry"]["full_columns"],data["geometry"]["full_rows"]),(11,8))
        self.assertEqual(data["base_probe_sha256"],hashlib.sha256(self.base_bytes).hexdigest())


class BattleRendererTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base_bytes = render.BASE_PROBE.read_bytes()
        cls.base = cls.base_bytes.decode("utf-8-sig")

    def recipe(self, resolution="1280x720", **options):
        return render.render_probe(self.base, resolution, render.BATTLE_STAGE,
                                   **({"extra_probe": True, "skip_map_validation": True} | options))

    def test_battle_recipe_uses_owned_capture_without_map_claim(self):
        report = self.recipe()
        geometry, text = report["geometry"], report["template"]
        self.assertEqual((geometry["width"], geometry["height"]), (1280, 720))
        self.assertEqual((geometry["columns"], geometry["rows"]), (17, 7))
        self.assertEqual(geometry["battlefield"], [32, 136, 1120, 584])
        self.assertEqual(geometry["sidebar"], [1120, 120, 1280, 600])
        self.assertEqual(geometry["main_menu_mouse"], [540, 278])
        self.assertEqual(geometry["load_mouse"], [320, 166])
        self.assertFalse(geometry["map_validation_applicable"])
        self.assertEqual(geometry["visibility_dump_max_bytes"], 0)
        self.assertEqual(geometry["expected_vedge_count"], 0)
        self.assertIn('bp 00406FA0 "gc"', text)
        self.assertNotIn("SURFDUMP_READY", text)
        self.assertNotIn("SCROLL_VISDUMP", text)
        self.assertEqual(text.count("@$t16*0n1280"), 3)
        self.assertIn("ed 00544cfc 00008700; ed 00544d00 00004580;", text)
        self.assertEqual(report["proof_class"], "forced_hidden_battle_fixture")
        binding = report["source_bindings"]["battle_layout"]
        self.assertEqual(binding["sha256"], hashlib.sha256(Path(binding["path"]).read_bytes()).hexdigest())
        self.assertEqual(render.BASE_PROBE.read_bytes(), self.base_bytes)

    def test_battle_options_do_not_open_generic_nonlegacy_guard(self):
        for resolution in ("800x600", "1024x768", "1280x960", "1920x1080"):
            with self.assertRaises(ValueError):
                self.recipe(resolution)
        for options in ({"extra_probe": False}, {"skip_map_validation": False},
                        {"canonical_template": False}, {"force_visible_edges": True},
                        {"post_owner_force_visible_seven": True}):
            with self.assertRaises(ValueError):
                self.recipe(**options)
        with self.assertRaises(ValueError):
            render.render_probe(self.base, "1280x720", STAGE, extra_probe=True, skip_map_validation=True)
        with self.assertRaises(ValueError):
            render.render_probe(self.base.replace("bp 00406FA0 ", "bp 00406FA1 "), "1280x720",
                                render.BATTLE_STAGE, extra_probe=True, skip_map_validation=True)

    def test_audited_placeholder_menu_spelling_is_supported_without_drift(self):
        literal = "ed 00544cfc 00004b00; ed 00544d00 00003680;"
        placeholder = "ed 00544cfc __MAIN_MOUSE_RAW_X__; ed 00544d00 __MAIN_MOUSE_RAW_Y__;"
        alternate = self.base.replace(literal, placeholder)
        report = render.render_probe(alternate, "1280x720", render.BATTLE_STAGE,
                                     extra_probe=True, skip_map_validation=True)
        self.assertEqual(report["template"], self.recipe()["template"])
        self.assertEqual(render.render_probe(alternate, "1024x768", STAGE)["template"],
                         render.render_probe(self.base, "1024x768", STAGE)["template"])
        for bad in (alternate + literal, alternate.replace("__MAIN_MOUSE_RAW_X__", "__BAD_X__")):
            with self.assertRaises(ValueError):
                render.render_main_menu(bad, 540, 278)

    def test_battle_cli_binds_explicit_extra_source_before_harness_build(self):
        extra = render.ROOT / "probes/cdb/battle/clash95_battle_hd_validation_extra.cdb"
        command = [sys.executable, "-B", str(Path(render.__file__)), "--resolution", "1280x720",
                   "--stage", render.BATTLE_STAGE, "--extra-probe", "--skip-map-validation"]
        missing = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(missing.returncode, 2)
        self.assertIn("--extra-probe-path", missing.stderr)
        result = subprocess.run(command + ["--extra-probe-path", str(extra)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(Path(report["extra_probe_path"]), extra.resolve())
        self.assertEqual(report["extra_probe_sha256"], hashlib.sha256(extra.read_bytes()).hexdigest())
        self.assertEqual(report["base_probe_sha256"], hashlib.sha256(self.base_bytes).hexdigest())
        harness = HARNESS.read_text()
        self.assertIn("'--extra-probe-path', $ExtraProbeTemplate", harness)
        self.assertLess(harness.index("Extra probe changed after source preflight"),
                        harness.index("$extraProbeText = (Get-Content"))


if __name__ == "__main__":
    unittest.main()
