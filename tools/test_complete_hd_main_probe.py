"""Source-only exact debugger recipe fixtures; never starts CDB or the game."""
from __future__ import annotations

import base64
import copy
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

import complete_hd_main_probe as main
from framed_noop_progress_probe import inspect_breakpoints


def fixture(resolution="800x600"):
    image = b"synthetic complete candidate"
    probe = ".echo SYNTHETIC_CANONICAL_COMPLETE_EXTRA\n"
    return dict(candidate=image, probe=probe, framed=dict(stage=main.renderer.FRAMED_STAGE),
                manifest=dict(stage=main.complete.STAGE, recipe_revision=main.complete.REVISION,
                              resolution=resolution, candidate_sha256=main.sha(image),
                              probe_sha256=main.sha(probe.encode("ascii"))))


class NormalMainTests(unittest.TestCase):
    raw_path = "C:/ClashCaptures/fixture-normal-main/surface.raw"

    def test_all_presets_and_partial_cell_geometry(self):
        for resolution in ("800x600", "1024x768", "1280x720", "1280x960", "1366x768",
                           "1920x1080", "2560x1440", "3440x1440", "3840x2160", "802x602"):
            with self.subTest(resolution=resolution):
                context = fixture(resolution)
                rebuilt = main.rebuild_normal_main(context, self.raw_path)
                text = rebuilt["text"]
                result = main.verify_normal_main(text, context, self.raw_path)
                self.assertTrue(result["exact_recipe_verified"])
                self.assertFalse(result["acceptance"])
                self.assertFalse(result["runtime_executed"])
                width, height = map(int, resolution.split("x"))
                geometry = rebuilt["geometry"]
                self.assertEqual(geometry["terrain"], [32, 16, width - 33, height - 17])
                self.assertIn(f"@$t12 != 0n{width}", text)
                self.assertIn(f"@$t15 != 0n{height}", text)
                self.assertEqual(text.count(context["probe"].strip()), 1)
                self.assertIn("ed 00544cfc 00005000; ed 00544d00 00002980;", text)
                self.assertNotIn("__", text)

    def test_only_supported_line_endings_are_equivalent(self):
        context = fixture()
        rebuilt = main.rebuild_normal_main(context, self.raw_path)
        for text in (rebuilt["text"], rebuilt["lf_text"], rebuilt["lf_text"].replace("\n", "\r\n")):
            self.assertTrue(main.verify_normal_main(text, context, self.raw_path)["exact_recipe_verified"])
        for text in (rebuilt["lf_text"].rstrip("\n") + "\n", rebuilt["lf_text"] + "\n",
                     rebuilt["lf_text"].replace("\n", "\r", 1), rebuilt["lf_text"] + "\x00"):
            with self.assertRaisesRegex(ValueError, "exact normal hidden recipe"):
                main.verify_normal_main(text, context, self.raw_path)

    def test_extra_call_and_forced_write_cannot_be_rehashed_into_acceptance(self):
        context = fixture()
        text = main.rebuild_normal_main(context, self.raw_path)["lf_text"]
        for command in (".call 00418700(1)", "ed 005202e4 0", "eb 00523f54 4",
                        '.echo A_SELF_HASHED_ADDITIONAL_MARKER'):
            changed = text.replace("\ng\n", "\n" + command + "\ng\n")
            # The old breakpoint inventory admits these unchanged declarations.
            # Merely recording a fresh hash is not independent authentication.
            inventory = inspect_breakpoints(changed)
            self.assertEqual(inventory["rendered_probe_sha256"], main.sha(changed.encode("ascii")))
            self.assertNotEqual(main.sha(text.encode("ascii")), main.sha(changed.encode("ascii")))
            with self.subTest(command=command), self.assertRaisesRegex(ValueError, "exact normal hidden recipe"):
                main.verify_normal_main(changed, context, self.raw_path)

    def test_changed_route_guard_and_capture_steps_fail(self):
        context = fixture()
        text = main.rebuild_normal_main(context, self.raw_path)["lf_text"]
        variants = (text.replace("@$t13 >= 0n4", "@$t13 >= 0n2"),
                    text.replace("FRAMED_CAPTURE_REJECT missing_game_data; q", "FRAMED_CAPTURE_REJECT missing_game_data; gc"),
                    text.replace("ed 00544d00 00002980;", "ed 00544d00 00002f00;"),
                    text.replace("r eip=004478a1", "r eip=004478b1"),
                    text.replace(".echo SURFDUMP_HOST_READY;", ".echo SURFDUMP_HOST_READY; gc"),
                    text.replace("r @$t19 = 0", "r @$t19 = 1"))
        for changed in variants:
            self.assertNotEqual(changed, text)
            with self.assertRaisesRegex(ValueError, "exact normal hidden recipe"):
                main.verify_normal_main(changed, context, self.raw_path)

    def test_mixed_context_and_paths_fail(self):
        context = fixture()
        text = main.rebuild_normal_main(context, self.raw_path)["text"]
        for name, value in (("stage", main.renderer.FRAMED_STAGE), ("recipe_revision", "complete_hd_v2"),
                            ("candidate_sha256", "0" * 64), ("probe_sha256", "0" * 64)):
            changed = copy.deepcopy(context)
            changed["manifest"][name] = value
            with self.assertRaises(ValueError):
                main.verify_normal_main(text, changed, self.raw_path)
        with self.assertRaises(ValueError):
            main.verify_normal_main(text, fixture("1024x768"), self.raw_path)
        for path in ("surface.raw", "C:surface.raw", "C:/ClashCaptures/../surface.raw",
                     "C:/ClashCaptures/surface.raw\n.call 00418700(1)"):
            with self.assertRaises(ValueError):
                main.verify_normal_main(text, context, path)

    def test_independent_powershell_string_composition_matches(self):
        executable = shutil.which("pwsh") or shutil.which("powershell")
        if not executable:
            self.skipTest("PowerShell unavailable; portable recipe and negative fixtures still run")
        producer = main.HARNESS.read_text(encoding="utf-8-sig")
        start = "$probeText = $probeRecipe.template"
        end = "Set-Content -LiteralPath $generatedProbe -Value $probeText -Encoding ASCII"
        self.assertEqual(producer.count(start), 1)
        self.assertEqual(producer.count(end), 1)
        composition = producer.split(start, 1)[1].split(end, 1)[0]
        # Only the producer's string-composition region is extracted. It has no
        # candidate build, proxy, process, input, capture or output-write calls.
        script = r'''
$ErrorActionPreference = 'Stop'
$packet = Get-Content -LiteralPath $args[0] -Raw | ConvertFrom-Json
$probeRecipe = $packet.recipe
$surfaceGeometry = $probeRecipe.geometry
$ExtraProbeTemplate = $packet.extra_path
$rawPath = $packet.raw_path
$LoadSlot = 0
$LateLoadSlotForcingOnly = $false
$PostOwnerForceVisibleSeven = $false
$NoSkipStartAnims = $false
$FastForwardStartAnims = $true
$ForceVisibleEdges = $false
$InitialMapPaintValidation = $true
$UseCdbWriteMem = $false
$FramedValidation = $true
function Get-CdbFileToken { param([string]$Path) [System.IO.Path]::GetFullPath($Path).Replace('\', '/') }
''' + start + composition + r'''
$bytes = [System.Text.Encoding]::ASCII.GetBytes($probeText + "`r`n")
[Convert]::ToBase64String($bytes)
'''
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            ps = folder / "compose-string-only.ps1"
            ps.write_text(script, encoding="utf-8")
            extra = folder / "canonical-extra.txt"
            packet = folder / "input.json"
            for resolution in ("800x600", "1024x768", "1920x1080", "802x602"):
                context = fixture(resolution)
                extra.write_bytes(context["probe"].encode("ascii"))
                recipe = main.renderer.render_probe(main.renderer.BASE_PROBE.read_bytes().decode("utf-8-sig"),
                                                    resolution, main.renderer.FRAMED_STAGE, load_slot=0)
                packet.write_text(json.dumps(dict(recipe=recipe, extra_path=str(extra), raw_path=self.raw_path)), encoding="utf-8")
                result = subprocess.run([executable, "-NoProfile", "-NonInteractive", "-File", str(ps), str(packet)],
                                        capture_output=True, text=True, timeout=30, check=False)
                self.assertEqual(result.returncode, 0, result.stderr)
                actual = base64.b64decode(result.stdout.strip()).decode("ascii")
                rebuilt = main.rebuild_normal_main(context, self.raw_path)
                self.assertEqual(actual, rebuilt["text"], resolution)
                self.assertTrue(main.verify_normal_main(actual, context, self.raw_path)["exact_recipe_verified"])


if __name__ == "__main__":
    unittest.main()
