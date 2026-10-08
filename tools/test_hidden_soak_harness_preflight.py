#!/usr/bin/env python3
"""Source and AST-isolated hidden-soak contracts; never execute the harness.

The only child is a hidden PowerShell interpreter. Disk observations are mocked,
marker logs stay in memory. Tiny private raw-storage fixtures exercise exclusive
file retention; no game/debugger, native build, runtime report or candidate is created.
"""

from __future__ import annotations

import json
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts/cdb/run_hidden_soak.ps1"
POWERSHELL = Path("C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe")


def extracted_fixture(names: tuple[str, ...], body: str) -> object:
    """Read only whitelisted function ASTs, then run the supplied pure fixture."""
    allowed = {
        "Get-FullPath", "Assert-SoakPlainPaths", "Assert-SoakDiskReserve", "Parse-SoakLog", "Get-RouteValidationFailures",
        "Get-HiddenRawRetentionBudget", "Get-FileSha256", "Write-HiddenRawFrame",
        "Get-DirectorySizeBytes",
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
            "Set-Content -LiteralPath $generatedProbe",
            "$samples | ConvertTo-Json", "& $pythonExe $assembler", "& $pythonExe $grader",
        ):
            offset = source.index(write)
            self.assertIn(guard, source[max(0, offset - 160):offset], write)

    def test_every_periodic_and_terminal_raw_read_is_retained(self):
        source = RUNNER.read_text(encoding="ascii")
        self.assertEqual(source.count("$rawPath = Write-HiddenRawFrame -FramesDirectory"), 2)
        self.assertEqual(source.count("RawPath = $rawPath"), 2)
        self.assertNotIn("WriteAllBytes($rawPath", source)
        self.assertIn("[System.IO.FileMode]::CreateNew", source)
        self.assertIn("$stream.Flush($true)", source)
        budget = source.index("$rawRetentionBudget = Get-HiddenRawRetentionBudget")
        self.assertLess(budget, source.index("if (-not $Execute) {"))
        self.assertIn("$pendingArtifactBytes -lt $rawRetentionBudget.MinimumArtifactBytes", source)
        self.assertIn("(Get-DirectorySizeBytes -Path $runDir) + 2MB", source)
        self.assertIn("* 2MB", source)
        self.assertIn("Retained run artifacts exceeded the declared limit during collection", source)


@unittest.skipUnless(sys.platform == "win32" and POWERSHELL.exists(), "pure storage fixtures need Windows")
class HiddenSoakRawRetentionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with tempfile.TemporaryDirectory(prefix="clash-soak-raw-storage-") as directory:
            frames = Path(directory) / "frames"
            frames.mkdir()
            escaped = str(frames).replace("'", "''")
            digest = hashlib.sha256(bytes((1, 2, 3, 4))).hexdigest()
            body = r'''
$script:Frames='__FRAMES__'
$script:Digest='__DIGEST__'
$script:ExistingBytes=0L
$script:ReserveFailure=$false
$script:HashFailure=$false
$script:InventoryFailure=$false
$script:ReserveCalls=0
$script:OriginalHasher=${function:Get-FileSha256}
function Assert-SoakDiskReserve {
    param([string[]]$Paths,[int64]$PendingBytes)
    $script:ReserveCalls++
    if ($script:ReserveFailure) { throw 'mock reserve refused before write' }
}
function Get-DirectorySizeBytes {
    param([string]$Path)
    if ($script:InventoryFailure) { throw 'mock artifact enumeration denied before write' }
    return $script:ExistingBytes
}
function Get-FileSha256 {
    param([string]$Path)
    if ($script:HashFailure) { return ('0' * 64) }
    & $script:OriginalHasher -Path $Path
}
function Invoke-StorageCase {
    param([string]$Case,[string]$Name,[byte[]]$Bytes,[int64]$Limit=100)
    $errorText=$null
    $path=$null
    try {
        $path=Write-HiddenRawFrame -FramesDirectory $script:Frames -Name $Name -Bytes $Bytes -ExpectedSha256 $script:Digest -DiskPaths @($script:Frames) -ArtifactLimitBytes $Limit
    }
    catch { $errorText=$_.Exception.Message }
    $expected=Join-Path $script:Frames ($Name + '.raw')
    $exists=Test-Path -LiteralPath $expected -PathType Leaf
    [ordered]@{Case=$Case;Error=$errorText;ReturnedPath=$path;Exists=$exists;
        Bytes=$(if($exists){@([System.IO.File]::ReadAllBytes($expected))}else{@()})}
}
$rows=@()
$rows+=Invoke-StorageCase 'round_trip' 'frame-0001' ([byte[]](1,2,3,4))
$rows+=Invoke-StorageCase 'duplicate' 'frame-0001' ([byte[]](5,6,7,8))
$script:ExistingBytes=98
$rows+=Invoke-StorageCase 'quota' 'frame-0002' ([byte[]](1,2,3,4))
$script:ExistingBytes=0
$script:ReserveFailure=$true
$rows+=Invoke-StorageCase 'reserve' 'frame-0003' ([byte[]](1,2,3,4))
$script:ReserveFailure=$false
$script:HashFailure=$true
$rows+=Invoke-StorageCase 'hash_drift' 'frame-0004' ([byte[]](1,2,3,4))
$script:HashFailure=$false
$rows+=Invoke-StorageCase 'bad_name' '../frame-0005' ([byte[]](1,2,3,4))
$rows+=Invoke-StorageCase 'empty' 'frame-0006' ([byte[]]@())
$rows+=Invoke-StorageCase 'zero_limit' 'frame-0007' ([byte[]](1,2,3,4)) 0
$script:InventoryFailure=$true
$rows+=Invoke-StorageCase 'inventory_denied' 'frame-0008' ([byte[]](1,2,3,4))
$budget=Get-HiddenRawRetentionBudget -DurationSec 7200 -FrameIntervalSec 30 -PngEdgeCount 3
$dense=Get-HiddenRawRetentionBudget -DurationSec 28800 -FrameIntervalSec 1 -PngEdgeCount 3
$badBudget=$null
try { Get-HiddenRawRetentionBudget -DurationSec 60 -FrameIntervalSec 0 -PngEdgeCount 3 | Out-Null }
catch { $badBudget=$_.Exception.Message }
[ordered]@{Cases=$rows;Budget=$budget;DenseBudget=$dense;BadBudget=$badBudget;ReserveCalls=$script:ReserveCalls} | ConvertTo-Json -Depth 6
'''.replace("__FRAMES__", escaped).replace("__DIGEST__", digest)
            cls.result = extracted_fixture(
                ("Get-FullPath", "Get-HiddenRawRetentionBudget", "Get-FileSha256", "Write-HiddenRawFrame"), body
            )
        cls.rows = {row["Case"]: row for row in cls.result["Cases"]}

    def test_original_bytes_round_trip_and_duplicate_never_overwrites(self):
        first = self.rows["round_trip"]
        self.assertIsNone(first["Error"])
        self.assertTrue(first["ReturnedPath"].endswith("frame-0001.raw"))
        self.assertEqual(first["Bytes"], [1, 2, 3, 4])
        self.assertIsNotNone(self.rows["duplicate"]["Error"])
        self.assertEqual(self.rows["duplicate"]["Bytes"], [1, 2, 3, 4])

    def test_reserve_quota_and_invalid_requests_do_not_create_files(self):
        for name in ("quota", "reserve", "bad_name", "empty", "zero_limit", "inventory_denied"):
            self.assertIsNotNone(self.rows[name]["Error"], name)
            self.assertFalse(self.rows[name]["Exists"], name)

    def test_hash_mismatch_retains_original_failure_artifact(self):
        row = self.rows["hash_drift"]
        self.assertIn("SHA does not match", row["Error"])
        self.assertTrue(row["Exists"])
        self.assertEqual(row["Bytes"], [1, 2, 3, 4])

    def test_full_raw_schedule_is_budgeted_before_execution(self):
        budget = self.result["Budget"]
        self.assertEqual(budget["MaximumScheduledFrames"], 242)
        self.assertEqual(budget["RawBytes"], 242 * 480000)
        self.assertGreater(budget["MinimumArtifactBytes"], budget["RawBytes"])
        self.assertLess(budget["MinimumArtifactBytes"], 250 * 1024 * 1024)
        self.assertGreater(self.result["DenseBudget"]["MinimumArtifactBytes"], 4096 * 1024 * 1024)
        self.assertIsNotNone(self.result["BadBudget"])


@unittest.skipUnless(sys.platform == "win32" and POWERSHELL.exists(), "pure inventory fixtures need Windows")
class HiddenSoakArtifactInventoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = extracted_fixture(("Get-DirectorySizeBytes",), r'''
function New-Entry {
    param([string]$Name,[bool]$Directory,[object]$Length=0L,[int64]$Attributes=0)
    [pscustomobject]@{FullName=$Name;PSIsContainer=$Directory;Length=$Length;Attributes=$Attributes}
}
function Get-Item {
    [CmdletBinding()]
    param([string]$LiteralPath,[switch]$Force)
    if ($script:Case -eq 'missing_root') { throw 'mock root missing' }
    if ($script:Case -eq 'denied_root') { throw 'mock root access denied' }
    if ($script:Case -eq 'file_root') { return (New-Entry $LiteralPath $false 3L) }
    if ($script:Case -eq 'reparse_root') { return (New-Entry $LiteralPath $true 0L 1024) }
    New-Entry $LiteralPath $true
}
function Get-ChildItem {
    [CmdletBinding()]
    param([string]$LiteralPath,[switch]$Force)
    if (-not $Force) { throw 'Hidden files must be inventoried' }
    if ($script:Case -eq 'denied_enumeration' -or
        ($script:Case -eq 'denied_nested' -and $LiteralPath.EndsWith('\nested'))) {
        throw 'mock artifact enumeration denied'
    }
    if ($LiteralPath.EndsWith('\nested')) { return (New-Entry ($LiteralPath+'\b.raw') $false 7L) }
    switch ($script:Case) {
        'empty' { return }
        'reparse_child' { return (New-Entry ($LiteralPath+'\linked') $true 0L 1024) }
        'reparse_file' { return (New-Entry ($LiteralPath+'\linked.raw') $false 1L 1024) }
        'negative_length' { return (New-Entry ($LiteralPath+'\bad.raw') $false -1L) }
        'missing_length' { return (New-Entry ($LiteralPath+'\bad.raw') $false $null) }
        'string_length' { return (New-Entry ($LiteralPath+'\bad.raw') $false '7') }
        'overflow' {
            New-Entry ($LiteralPath+'\a.raw') $false ([int64]::MaxValue)
            New-Entry ($LiteralPath+'\b.raw') $false 1L
            return
        }
    }
    New-Entry ($LiteralPath+'\a.raw') $false 3L 2
    New-Entry ($LiteralPath+'\nested') $true
}
$rows=@()
foreach ($case in @('valid','empty','missing_root','denied_root','file_root','reparse_root',
    'denied_enumeration','denied_nested','reparse_child','reparse_file','negative_length',
    'missing_length','string_length','overflow')) {
    $script:Case=$case; $size=$null; $errorText=$null
    try { $size=Get-DirectorySizeBytes -Path 'C:\Synthetic\Run' }
    catch { $errorText=$_.Exception.Message }
    $rows += [ordered]@{Name=$case;Size=$size;Error=$errorText}
}
$rows | ConvertTo-Json -Depth 4
''')
        cls.rows = {row["Name"]: row for row in cls.rows}

    def test_complete_inventory_counts_hidden_and_nested_files(self):
        self.assertIsNone(self.rows["valid"]["Error"])
        self.assertEqual(self.rows["valid"]["Size"], 10)
        self.assertIsNone(self.rows["empty"]["Error"])
        self.assertEqual(self.rows["empty"]["Size"], 0)

    def test_unreadable_or_missing_inventory_never_returns_zero(self):
        for name in ("missing_root", "denied_root", "file_root", "denied_enumeration", "denied_nested"):
            self.assertIsNotNone(self.rows[name]["Error"], name)
            self.assertIsNone(self.rows[name]["Size"], name)

    def test_reparse_points_and_invalid_sizes_fail_closed(self):
        for name in ("reparse_root", "reparse_child", "reparse_file", "negative_length",
                     "missing_length", "string_length", "overflow"):
            self.assertIsNotNone(self.rows[name]["Error"], name)
            self.assertIsNone(self.rows[name]["Size"], name)


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
