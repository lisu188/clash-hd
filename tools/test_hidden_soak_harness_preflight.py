#!/usr/bin/env python3
"""Source and AST-isolated hidden-soak contracts; never execute the harness.

The only child is a hidden PowerShell interpreter. Disk observations are mocked,
marker logs stay in memory, and no game/debugger, native build, report, candidate
or temporary fixture file is created.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts/cdb/run_hidden_soak.ps1"
POWERSHELL = Path("C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe")


def extracted_fixture(names: tuple[str, ...], body: str) -> object:
    """Read only whitelisted function ASTs, then run the supplied pure fixture."""
    allowed = {
        "Get-FullPath", "Assert-SoakPlainPaths", "Assert-SoakDiskReserve", "Parse-SoakLog", "Get-RouteValidationFailures",
    }
    if not set(names) <= allowed:
        raise AssertionError("Runtime helper extraction is forbidden")
    runner = str(RUNNER).replace("'", "''")
    quoted_names = ",".join(f"'{name}'" for name in names)
    script = f"""
$ErrorActionPreference = 'Stop'
$tokens = $null
$errors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile('{runner}', [ref]$tokens, [ref]$errors)
if ($errors.Count) {{ throw ($errors | Out-String) }}
foreach ($name in @({quoted_names})) {{
    $nodes = @($ast.FindAll({{ param($node)
        $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -eq $name
    }}, $true))
    if ($nodes.Count -ne 1) {{ throw "Expected one pure helper: $name" }}
    . ([scriptblock]::Create($nodes[0].Extent.Text))
}}
{body}
"""
    environment = os.environ.copy()
    environment.pop("PSModulePath", None)
    result = subprocess.run(
        [str(POWERSHELL), "-NoProfile", "-NonInteractive", "-Command",
         "& ([scriptblock]::Create([Console]::In.ReadToEnd()))"],
        input=script, capture_output=True, text=True, timeout=30, env=environment,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    if result.returncode:
        raise AssertionError(result.stdout + result.stderr)
    return json.loads(result.stdout)


def pan_log() -> list[str]:
    rows = [
        "SOAK_ROUTE_START route_ticks=7680 pan=1 player=0 tick=1000 gd=00c00000 scroll=(4,6)",
        "SOAK_SURFDUMP_READY redraw_seq=4 surface=00a00000 size=(800,600) base=00b40000 bytes=480000",
        "SOAK_PAN_PLAN base=(4,6) delta=(1,1) max=(20,20) safe=1",
    ]
    for index in range(11):
        phase = index % 4
        x = 5 if phase in (1, 2) else 4
        y = 7 if phase in (2, 3) else 6
        rows.append(
            f"SOAK_PAN_SET phase={phase} x={x} y={y} hits={(index + 1) * 100} "
            f"tickdelta={(index + 1) * 640} delta=(1,1)"
        )
        if index == 0:
            rows.append("SOAK_HEARTBEAT hits=150 tickdelta=1000 player=0 scroll=(4,6)")
    rows.append("SOAK_ROUTE_END route_ticks=7680 pan=1 hits=2000 tickdelta=7680 player=0 scroll=(5,7)")
    return rows


class HiddenSoakHarnessSourceTests(unittest.TestCase):
    def test_disk_preflight_precedes_execute_and_all_initial_mutations(self):
        source = RUNNER.read_text(encoding="ascii")
        gate = source.index("if (-not $Execute) {")
        reserve = source.index("Assert-SoakDiskReserve -Paths $diskPaths -PendingBytes $pendingRunBytes")
        self.assertLess(reserve, gate)
        for mutation in (
            "    Add-Type @'", "New-Item -ItemType Directory -Path $candidateRunDir",
            "& $pythonExe $patcher --input", "& $DdrawProxyBuildScript -OutputDll",
            "$launch = Start-CdbOnHiddenDesktop",
        ):
            self.assertGreater(source.index(mutation), gate, mutation)
        self.assertIn("[ValidateRange(64, 4096)]\n    [int]$BuildHeadroomMB", source)
        self.assertIn("$pendingArtifactBytes + [int64]$BuildHeadroomMB * 1MB", source)
        physical = source.index("Assert-SoakPlainPaths -Paths @($RepoRoot, $InputExe")
        self.assertLess(physical, gate)
        self.assertIn("Assert-SoakPlainPaths -Paths $Paths", source[:physical])

    def test_reserve_rechecked_during_runtime_and_before_persistence(self):
        source = RUNNER.read_text(encoding="ascii")
        guard = "Assert-SoakDiskReserve -Paths $diskPaths -PendingBytes $pendingArtifactBytes"
        loop = source.index("    while ((Get-Date) -lt $overallDeadline)")
        self.assertLess(source.index(guard, loop), source.index("Start-Sleep -Milliseconds 500", loop))
        for write in (
            "Set-Content -LiteralPath $generatedProbe", "[System.IO.File]::WriteAllBytes($rawPath",
            "$samples | ConvertTo-Json", "& $pythonExe $assembler", "& $pythonExe $grader",
        ):
            offset = source.index(write)
            self.assertIn(guard, source[max(0, offset - 160):offset], write)


@unittest.skipUnless(sys.platform == "win32" and POWERSHELL.exists(), "pure PowerShell AST fixtures need Windows")
class HiddenSoakHarnessDiskTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = extracted_fixture(("Get-FullPath", "Assert-SoakDiskReserve"), r'''
$script:Calls = @()
function Assert-SoakPlainPaths { param([string[]]$Paths) }
function Get-SoakDiskSpace {
    param([string]$VolumeRoot)
    $script:Calls += $VolumeRoot
    [pscustomobject]@{TotalBytes=$script:Total; FreeBytes=$script:Free}
}
$cases = @(
    @{Name='above'; Total=1000; Free=151; Pending=50},
    @{Name='exact'; Total=1000; Free=150; Pending=50},
    @{Name='below'; Total=1000; Free=149; Pending=50},
    @{Name='already_full'; Total=1000; Free=100; Pending=0},
    @{Name='negative'; Total=1000; Free=999; Pending=-1},
    @{Name='unknown'; Total=0; Free=0; Pending=0},
    @{Name='invalid'; Total=1000; Free=1001; Pending=0}
)
$results = @()
foreach ($case in $cases) {
    $script:Total=$case.Total; $script:Free=$case.Free; $script:Calls=@()
    $errorText=$null
    try { Assert-SoakDiskReserve -Paths @('C:\Synthetic\Candidate', 'c:\Synthetic\Reports') -PendingBytes $case.Pending }
    catch { $errorText=$_.Exception.Message }
    $results += [ordered]@{Name=$case.Name; Error=$errorText; Calls=@($script:Calls)}
}
$results | ConvertTo-Json -Depth 5
''')

    def test_strict_threshold_includes_pending_headroom(self):
        rows = {row["Name"]: row for row in self.rows}
        self.assertIsNone(rows["above"]["Error"])
        for name in ("exact", "below", "already_full"):
            self.assertIn("Disk reserve refused", rows[name]["Error"])

    def test_invalid_observations_fail_closed(self):
        rows = {row["Name"]: row for row in self.rows}
        for name in ("negative", "unknown", "invalid"):
            self.assertTrue(rows[name]["Error"], rows[name])

    def test_shared_volume_is_counted_once(self):
        rows = {row["Name"]: row for row in self.rows}
        self.assertEqual(rows["above"]["Calls"], ["C:\\"])


@unittest.skipUnless(sys.platform == "win32" and POWERSHELL.exists(), "pure PowerShell AST fixtures need Windows")
class HiddenSoakHarnessPhysicalPathTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = extracted_fixture(("Get-FullPath", "Assert-SoakPlainPaths"), r'''
function Get-Item {
    [CmdletBinding()]
    param([string]$LiteralPath, [switch]$Force)
    $script:Queries += $LiteralPath
    if ($LiteralPath -eq $script:Unreadable) { throw [UnauthorizedAccessException]::new('mock unreadable ancestor') }
    if (-not $script:Items.ContainsKey($LiteralPath)) {
        throw [System.Management.Automation.ItemNotFoundException]::new('mock path missing')
    }
    if ($LiteralPath -eq $script:Unknown) { return [pscustomobject]@{Attributes=$null} }
    [pscustomobject]@{Attributes=[System.IO.FileAttributes]$script:Items[$LiteralPath]}
}
$results = @()
foreach ($name in @('ordinary','junction_parent','symlink_input','reparse_grandparent','unreadable_parent','unreadable_root','missing_root','unknown_attributes')) {
    $script:Items = @{
        'C:\'=16; 'C:\Synthetic'=16; 'C:\Synthetic\Game'=16
        'C:\Synthetic\Game\original.exe'=32; 'C:\Synthetic\Candidates'=16
        'C:\Synthetic\Reports'=16
    }
    $script:Unreadable=$null; $script:Unknown=$null; $script:Queries=@()
    if ($name -eq 'junction_parent') { $script:Items['C:\Synthetic\Candidates']=16+1024 }
    if ($name -eq 'symlink_input') { $script:Items['C:\Synthetic\Game\original.exe']=32+1024 }
    if ($name -eq 'reparse_grandparent') { $script:Items['C:\Synthetic']=16+1024 }
    if ($name -eq 'unreadable_parent') { $script:Unreadable='C:\Synthetic\Candidates' }
    if ($name -eq 'unreadable_root') { $script:Unreadable='C:\' }
    if ($name -eq 'missing_root') { $script:Items.Remove('C:\') }
    if ($name -eq 'unknown_attributes') { $script:Unknown='C:\Synthetic\Candidates' }
    $errorText=$null
    try {
        Assert-SoakPlainPaths -Paths @(
            'C:\Synthetic\Game\original.exe', 'C:\Synthetic\Game',
            'C:\Synthetic\Candidates\new-run\candidate.exe', 'C:\Synthetic\Reports\new-run\report.json'
        )
    } catch { $errorText=$_.Exception.Message }
    $results += [ordered]@{Name=$name; Error=$errorText; Queries=@($script:Queries)}
}
$results | ConvertTo-Json -Depth 8
''')

    def test_ordinary_existing_and_uncreated_descendants_pass(self):
        row = next(row for row in self.rows if row["Name"] == "ordinary")
        self.assertIsNone(row["Error"], row)
        self.assertIn(r"C:\Synthetic\Candidates", row["Queries"])
        self.assertIn(r"C:\Synthetic\Reports", row["Queries"])

    def test_reparse_ancestors_and_input_fail_without_following_them(self):
        rows = {row["Name"]: row for row in self.rows}
        for name in ("junction_parent", "symlink_input", "reparse_grandparent"):
            self.assertIn("Reparse-point", rows[name]["Error"])
        row = rows["junction_parent"]
        self.assertNotIn(r"C:\Synthetic\Candidates\new-run\candidate.exe", row["Queries"])
        self.assertEqual(row["Queries"][-1], r"C:\Synthetic\Candidates")

    def test_unreadable_or_missing_root_and_unknown_attributes_fail_closed(self):
        rows = {row["Name"]: row for row in self.rows}
        for name in ("unreadable_parent", "unreadable_root"):
            self.assertIn("unreadable ancestor", rows[name]["Error"])
        self.assertIn("no readable existing volume root", rows["missing_root"]["Error"])
        self.assertIn("attributes are unavailable", rows["unknown_attributes"]["Error"])


@unittest.skipUnless(sys.platform == "win32" and POWERSHELL.exists(), "pure PowerShell AST fixtures need Windows")
class HiddenSoakHarnessMarkerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        baseline = pan_log()
        cases = {"valid": baseline}
        cases["bounded_jitter"] = [
            next((row.replace(f"tickdelta={tick} ", f"tickdelta={tick + 128} ")
                  for tick in range(640, 7041, 640) if f"tickdelta={tick} " in row), row)
            if row.startswith("SOAK_PAN_SET") else row
            for row in baseline
        ]
        cases["first_gap"] = [row.replace("tickdelta=640 ", "tickdelta=769 ") for row in baseline]
        cases["one_pan"] = [row for row in baseline if not row.startswith("SOAK_PAN_SET") or "tickdelta=640 " in row]
        cases["tail_gap"] = [row for row in baseline if "tickdelta=7040 " not in row]
        cases["interior_gap"] = [row.replace("tickdelta=1280 ", "tickdelta=1409 ") for row in baseline]
        cases["short_gap"] = [row.replace("tickdelta=5120 ", "tickdelta=5121 ") for row in baseline]
        cases["backwards_global"] = baseline.copy()
        heartbeat = cases["backwards_global"].pop(4)
        cases["backwards_global"].insert(5, heartbeat)
        cases["end_hits"] = [row.replace("hits=2000 ", "hits=1000 ") for row in baseline]
        cases["player_changed"] = [row.replace("tickdelta=7680 player=0", "tickdelta=7680 player=1") for row in baseline]
        cases["end_scroll"] = [row.replace("tickdelta=7680 player=0 scroll=(5,7)", "tickdelta=7680 player=0 scroll=(4,6)") for row in baseline]
        cases["ready_early"] = [baseline[1], baseline[0], *baseline[2:]]
        cases["plan_early"] = [baseline[2], *baseline[:2], *baseline[3:]]
        cases["unsafe_bound"] = [row.replace("max=(20,20)", "max=(4,6)") for row in baseline]
        cases["no_direction"] = [row.replace("delta=(1,1)", "delta=(0,0)") for row in baseline]
        cases["prose"] = [".echo SOAK_ROUTE_START SOAK_SURFDUMP_READY SOAK_ROUTE_END SOAK_HEARTBEAT SOAK_PAN_SET"]
        payload = json.dumps([{"name": name, "log": "\n".join(rows)} for name, rows in cases.items()])
        body = "$cases = @'\n" + payload + "\n'@ | ConvertFrom-Json\n" + r'''
$results = @()
foreach ($case in $cases) {
    $observed=Parse-SoakLog -LogText $case.log
    $failures=@(Get-RouteValidationFailures -Observations $observed -ExpectedRoute 'map-pan' -ExpectedDurationTicks 7680 -ExpectedPanIntervalTicks 640)
    $results += [ordered]@{
        Name=$case.name; Failures=$failures; Ready=@($observed.ReadyRows).Count
        Starts=@($observed.RouteStarts).Count; Ends=@($observed.RouteEnds).Count
        Heartbeats=@($observed.Heartbeats).Count; Pans=@($observed.PanEvents).Count
    }
}
$results | ConvertTo-Json -Depth 8
'''
        cls.rows = {row["Name"]: row for row in extracted_fixture(("Parse-SoakLog", "Get-RouteValidationFailures"), body)}

    def assert_failure(self, name: str, text: str):
        self.assertTrue(any(text in failure for failure in self.rows[name]["Failures"]), self.rows[name])

    def test_complete_pan_route_passes(self):
        self.assertEqual(self.rows["valid"]["Failures"], [])
        self.assertEqual(self.rows["bounded_jitter"]["Failures"], [])

    def test_missing_pan_and_terminal_coverage_fail(self):
        self.assert_failure("one_pan", "terminal coverage")
        self.assert_failure("tail_gap", "terminal coverage")

    def test_interior_gap_fails_without_relaxing_minimum_interval(self):
        self.assert_failure("first_gap", "coverage gap")
        self.assert_failure("interior_gap", "coverage gap")
        self.assert_failure("short_gap", "requested pan interval")

    def test_global_counter_and_player_order_fail(self):
        self.assert_failure("backwards_global", "globally ordered")
        self.assert_failure("end_hits", "globally ordered")
        self.assert_failure("player_changed", "player changed")
        self.assert_failure("end_scroll", "scroll changed")

    def test_ready_and_plan_order_fail(self):
        self.assert_failure("ready_early", "SOAK_SURFDUMP_READY was not ordered")
        self.assert_failure("plan_early", "SOAK_PAN_PLAN was not ordered")

    def test_unsafe_or_empty_inward_direction_fails(self):
        self.assert_failure("unsafe_bound", "leaves the live scroll bounds")
        self.assert_failure("no_direction", "safe inward")

    def test_prose_never_produces_observations(self):
        row = self.rows["prose"]
        for field in ("Ready", "Starts", "Ends", "Heartbeats", "Pans"):
            self.assertEqual(row[field], 0)


def run_tests() -> None:
    """Aggregate entrypoint: skipped platform fixtures are not a full pass."""
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    if not result.wasSuccessful() or result.skipped:
        raise AssertionError(
            f"hidden harness preflight: failures={len(result.failures)}, "
            f"errors={len(result.errors)}, skipped={len(result.skipped)}"
        )


if __name__ == "__main__":
    run_tests()
