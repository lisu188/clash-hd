#!/usr/bin/env python3
"""Offline contracts for the additive partial-tile surface harness path.

PowerShell parses the harness but executes only allowlisted AST fragments and
pure functions with synthetic values. Python builder invocation is mocked.
No harness is dot-sourced, no executable is read/built, and no game/debugger,
native API, process enumeration, or screenshot operation is performed.
"""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "scripts/cdb/run_cdb_surface_dump.ps1"
POWERSHELL = Path("C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe")
STABLE = "gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch"
BASE = STABLE + "-combinedui-validation"
STAGE = STABLE + "-combinedui-partialtiles-validation"
INITIAL_STAGE = STABLE + "-combinedui-partialtiles-initialpaint-validation"

FIXTURE = r'''
param([string]$Runner, [string]$RepoRoot, [string]$CasesPath)
$ErrorActionPreference = 'Stop'
$tokens = $null
$parseErrors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile($Runner, [ref]$tokens, [ref]$parseErrors)
if ($parseErrors.Count) { throw ($parseErrors | Out-String) }
$cases = Get-Content -LiteralPath $CasesPath -Raw | ConvertFrom-Json
$allowedCommands = @('Join-Path', 'Test-Path', 'Where-Object', 'ConvertFrom-Json', 'Get-SurfaceRuntimeFailure', 'Get-CdbFileToken')
$allowedMethods = @('GetFullPath', 'StartsWith', 'ToLowerInvariant', 'Match', 'ToUInt64',
                    'TryParse', 'ContainsKey', 'Contains', 'Remove', 'Replace', 'Floor', 'Ceiling', 'Max')
function Assert-PureAst {
    param($Node, [switch]$MockPython)
    foreach ($command in $Node.FindAll({ param($n) $n -is [System.Management.Automation.Language.CommandAst] }, $true)) {
        if ($command.GetCommandName() -notin $allowedCommands) {
            if (-not ($MockPython -and $command.Extent.Text.StartsWith('& $pythonExe '))) {
                throw "Unmocked command in extracted fragment: $($command.Extent.Text)"
            }
        }
    }
    foreach ($method in $Node.FindAll({ param($n) $n -is [System.Management.Automation.Language.InvokeMemberExpressionAst] }, $true)) {
        if ($method.Member.Value -notin $allowedMethods) {
            throw "Unmocked method in extracted fragment: $($method.Extent.Text)"
        }
    }
}
foreach ($name in @('Get-PartialTileValidationFailure', 'Get-SurfaceRuntimeFailure')) {
    $found = @($ast.FindAll({ param($n) $n -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -eq $name }, $true))
    if ($found.Count -ne 1) { throw "Missing unique pure helper $name" }
    Assert-PureAst $found[0]
    . ([scriptblock]::Create($found[0].Extent.Text))
}
$optionBlocks = @($ast.FindAll({ param($n) $n -is [System.Management.Automation.Language.IfStatementAst] -and
    $n.Clauses[0].Item1.Extent.Text -eq '$PartialTileValidation' -and $n.Extent.Text.Contains('$partialBase =') }, $true))
$initialOption = @($ast.FindAll({ param($n) $n -is [System.Management.Automation.Language.IfStatementAst] -and
    $n.Clauses[0].Item1.Extent.Text -eq '$InitialMapPaintValidation -and -not $PartialTileValidation' }, $true))
$dumpActions = @($ast.FindAll({ param($n) $n -is [System.Management.Automation.Language.AssignmentStatementAst] -and
    $n.Left.Extent.Text -eq '$surfaceDumpAction' }, $true))
$initialBounds = @($ast.FindAll({ param($n) $n -is [System.Management.Automation.Language.IfStatementAst] -and
    $n.Clauses[0].Item1.Extent.Text -eq '$InitialMapPaintValidation' -and $n.Extent.Text.Contains('$probeBoundsReady =') }, $true))
if ($initialOption.Count -ne 1 -or $dumpActions.Count -ne 1 -or $initialBounds.Count -ne 1) { throw 'Ambiguous initial-paint fragments' }
Assert-PureAst $initialOption[0]
Assert-PureAst $dumpActions[0]
Assert-PureAst $initialBounds[0]
function Get-CdbFileToken { throw 'Unexpected CDB-write path in initial-paint fixture' }
$buildBlocks = @($ast.EndBlock.Statements | Where-Object {
    $_ -is [System.Management.Automation.Language.IfStatementAst] -and
    $_.Clauses[0].Item1.Extent.Text -eq '$CompleteHdValidation' -and
    $_.Extent.Text.Contains('$partialBuildReport =')
})
if ($buildBlocks.Count -ne 1 -or $buildBlocks[0].Clauses.Count -ne 2 -or
    $buildBlocks[0].Clauses[1].Item1.Extent.Text -ne '$PartialTileValidation' -or
    $null -eq $buildBlocks[0].ElseClause) { throw 'Ambiguous complete/partial/ordinary build dispatch' }
# Execute only the actual legacy clause and ordinary fallback. The complete
# branch reads a candidate bundle and belongs to the separate complete suite.
$legacyClause = $buildBlocks[0].Clauses[1]
Assert-PureAst $legacyClause.Item1
Assert-PureAst $legacyClause.Item2 -MockPython
Assert-PureAst $buildBlocks[0].ElseClause -MockPython
$legacyBuildCode = 'if (' + $legacyClause.Item1.Extent.Text + ') ' + $legacyClause.Item2.Extent.Text +
    ' else ' + $buildBlocks[0].ElseClause.Extent.Text
$preflightBlocks = @($ast.FindAll({ param($n) $n -is [System.Management.Automation.Language.IfStatementAst] -and
    $n.Clauses[0].Item1.Extent.Text -eq '$PartialTileValidation' -and $n.Extent.Text.Contains('$partialPreflightJson =') }, $true))
$candidateGates = @($ast.FindAll({ param($n) $n -is [System.Management.Automation.Language.IfStatementAst] -and
    $n.Extent.Text.Contains("throw 'Partial-tile candidate differs from the preflight recipe.'") }, $true))
$allExitGates = @($ast.FindAll({ param($n) $n -is [System.Management.Automation.Language.IfStatementAst] -and
    $n.Clauses[0].Item1.Extent.Text -eq '$patchExit -ne 0' }, $true))
$exitGates = @($ast.EndBlock.Statements | Where-Object {
    $_ -is [System.Management.Automation.Language.IfStatementAst] -and
    $_.Clauses[0].Item1.Extent.Text -eq '$patchExit -ne 0'
})
$completeExitGates = @($buildBlocks[0].Clauses[0].Item2.FindAll({ param($n)
    $n -is [System.Management.Automation.Language.IfStatementAst] -and
    $n.Clauses[0].Item1.Extent.Text -eq '$patchExit -ne 0'
}, $true))
if ($allExitGates.Count -ne 2 -or $exitGates.Count -ne 1 -or $completeExitGates.Count -ne 1 -or
    -not $exitGates[0].Extent.Text.Contains('patch_clash95_hd.py failed with exit code') -or
    -not $completeExitGates[0].Extent.Text.Contains('Complete candidate builder failed with exit code') -or
    $exitGates[0].Extent.StartOffset -le $buildBlocks[0].Extent.EndOffset) {
    throw 'Ambiguous or misplaced legacy/complete builder exit gates'
}
Assert-PureAst $completeExitGates[0]
$runtimeAssignments = @($ast.FindAll({ param($n) $n -is [System.Management.Automation.Language.AssignmentStatementAst] -and
    $n.Left.Extent.Text -eq '$runtimeFailure' }, $true))
$outerGates = @($ast.FindAll({ param($n) $n -is [System.Management.Automation.Language.IfStatementAst] -and
    $n.Clauses[0].Item1.Extent.Text.StartsWith('-not $ready -or -not $dumpDone -or -not $rawExists') }, $true))
if ($optionBlocks.Count -ne 1 -or $buildBlocks.Count -ne 1 -or $exitGates.Count -ne 1 -or
    $preflightBlocks.Count -ne 1 -or $candidateGates.Count -ne 1 -or
    $runtimeAssignments.Count -ne 1 -or $outerGates.Count -ne 1) { throw 'Ambiguous harness integration fragments' }
Assert-PureAst $optionBlocks[0]
Assert-PureAst $preflightBlocks[0] -MockPython
Assert-PureAst $candidateGates[0]
Assert-PureAst $exitGates[0]
Assert-PureAst $runtimeAssignments[0]
Assert-PureAst $outerGates[0].Clauses[0].Item1
$partialTileBuilder = Join-Path $RepoRoot 'tools\build_partial_tile_candidate.py'
function Test-Path {
    param([string]$LiteralPath, [string]$PathType)
    if ($LiteralPath -ne $partialTileBuilder -or $PathType -ne 'Leaf') { throw 'Unexpected path access in option gate' }
    return -not $script:MissingBuilder
}
$result = [ordered]@{ options=@(); logs=@(); builds=@(); outer=@(); preflight=@(); candidates=@(); initial_dump=@(); complete_builder_exits=@() }
foreach ($case in $cases.options) {
    $PartialTileValidation=$true
    $CompleteHdValidation=$false; $FramedValidation=$false; $MinimapViewportValidation=$false
    $InitialMapPaintValidation=$false
    $ContinueAfterDumpSec=0
    $Stage=$cases.stage
    $UseDdrawProxy=$true
    $AllowVisibleDesktop=$false
    $ExtraProbeTemplate=''
    $ForceVisibleEdges=$false
    $PostOwnerForceVisibleSeven=$false
    $SkipMapValidation=$false
    $UseCdbWriteMem=$false
    $LoadSlot=0
    $ProbeTemplate=Join-Path $RepoRoot 'probes\cdb\render\clash95_surface_dump_probe.cdb'
    $CandidateDir='C:\ClashTests\synthetic-partial\candidate'
    $WorkDir='C:\ClashTests\synthetic-partial\workdir'
    $OutRoot='C:\ClashCaptures\synthetic-partial'
    $RequireGameplay=$false
    $recipeStage=$Stage
    $script:MissingBuilder=$false
    foreach ($property in $case.values.PSObject.Properties) {
        if ($property.Name -eq 'MissingBuilder') { $script:MissingBuilder=$property.Value }
        else { Set-Variable -Name $property.Name -Value $property.Value }
    }
    $failure=$null
    try {
        . ([scriptblock]::Create($initialOption[0].Extent.Text))
        . ([scriptblock]::Create($optionBlocks[0].Extent.Text))
    } catch { $failure=$_.Exception.Message }
    $result.options += [pscustomobject]@{ name=$case.name; error=$failure; recipe=$recipeStage; require_gameplay=$RequireGameplay; builder_options=@($partialBuilderOptions) }
}
$partialBuilderOptions=@()
$InitialMapPaintValidation=$true
$UseCdbWriteMem=$false
. ([scriptblock]::Create($dumpActions[0].Extent.Text))
foreach ($currentLogText in @('', 'SURFDUMP_HOST_READY', 'PTILE_TRACE_CLOSED', ('PTILE_TRACE_CLOSED tid=1 eip=00406fa0 esp=000e0000' + "`n" + 'SURFDUMP_HOST_READY'))) {
    $probeBoundsReady=$true
    . ([scriptblock]::Create($initialBounds[0].Extent.Text))
    $result.initial_dump += [pscustomobject]@{ log=$currentLogText; ready=$probeBoundsReady; action=$surfaceDumpAction }
}
foreach ($case in $cases.logs) {
    $failure=$null
    $exception=$null
    try {
        $failure=Get-PartialTileValidationFailure -LogText $case.log -Stage $cases.stage -Resolution $case.resolution -CandidateSha256 $cases.sha
    } catch { $exception=$_.Exception.Message }
    $result.logs += [pscustomobject]@{ name=$case.name; error=$failure; exception=$exception }
}
function Invoke-MockPython {
    $script:PythonCalls += ,@($args)
    $global:LASTEXITCODE=$script:MockExit
    if ($null -ne $script:MockResponse) { return $script:MockResponse }
}
$pythonExe='Invoke-MockPython'
$patcher=Join-Path $RepoRoot 'patch_clash95_hd.py'
$InputExe='C:\SyntheticOriginal\clash95.exe'
$inputFull='C:\SyntheticOriginal\clash95.exe'
$candidateFull='C:\ClashTests\synthetic-partial\candidate\new.exe'
$runDir='C:\ClashCaptures\synthetic-partial\run'
$script:MockResponse=$null
$CompleteHdValidation=$false
foreach ($PartialTileValidation in @($false,$true)) {
    foreach ($Resolution in @('800x600','1024x768')) {
        foreach ($script:MockExit in @(0,9)) {
            $Stage=if ($PartialTileValidation) { $cases.stage } else { $cases.base }
            $script:PythonCalls=@()
            $ExtraProbeTemplate=''
            $failure=$null
            . ([scriptblock]::Create($legacyBuildCode))
            $patchExit=$LASTEXITCODE
            try { . ([scriptblock]::Create($exitGates[0].Extent.Text)) } catch { $failure=$_.Exception.Message }
            $result.builds += [pscustomobject]@{
                partial=$PartialTileValidation; resolution=$Resolution; exit=$script:MockExit
                calls=$script:PythonCalls; error=$failure; extra_probe=$ExtraProbeTemplate
            }
        }
    }
}
foreach ($patchExit in @(0,9)) {
    $failure=$null
    try { . ([scriptblock]::Create($completeExitGates[0].Extent.Text)) } catch { $failure=$_.Exception.Message }
    $result.complete_builder_exits += [pscustomobject]@{ exit=$patchExit; error=$failure }
}
$PartialTileValidation=$true
$Stage=$cases.stage
$Resolution='1024x768'
foreach ($case in $cases.preflight) {
    $script:PythonCalls=@()
    $script:MockExit=$case.exit
    $script:MockResponse=$case.response
    $failure=$null
    try { . ([scriptblock]::Create($preflightBlocks[0].Extent.Text)) } catch { $failure=$_.Exception.Message }
    $result.preflight += [pscustomobject]@{ name=$case.name; error=$failure; calls=$script:PythonCalls }
}
$partialPreflight=[pscustomobject]@{candidate_sha256=$cases.sha}
foreach ($case in $cases.candidates) {
    $PartialTileValidation=$case.partial
    $candidateSha=$case.sha
    $failure=$null
    try { . ([scriptblock]::Create($candidateGates[0].Extent.Text)) } catch { $failure=$_.Exception.Message }
    $result.candidates += [pscustomobject]@{ name=$case.name; error=$failure }
}
$ready=$true
$dumpDone=$true
$rawExists=$true
$surfaceGeometryFailure=$null
$dumpInvalid=$false
foreach ($ContinueAfterDumpSec in @(0,5)) {
    foreach ($case in $cases.outer) {
        $av=$case.av
        $appRequestQuit=$case.quit
        $runtimeError=$case.runtime_error
        $partialValidationFailure=$case.partial_error
        . ([scriptblock]::Create($runtimeAssignments[0].Extent.Text))
        $failed=[bool](& ([scriptblock]::Create($outerGates[0].Clauses[0].Item1.Extent.Text)))
        $result.outer += [pscustomobject]@{ name=$case.name; grace=$ContinueAfterDumpSec; failed=$failed; error=$runtimeFailure }
    }
}
$result | ConvertTo-Json -Depth 12 -Compress
'''


def scenarios():
    digest = "ab" * 32
    contract = f"PTILE_CONTRACT_PASS stage={STAGE} resolution=800x600 candidate_sha256={digest}"
    ready = "PTILE_MAP_READY owner=0040ad40 size=(800,600)"

    def row(hook, status=1, tid="3ac", esp="000edc00", owner="00514d10", player=0):
        return (f"PTILE_STATUS hook={hook} status={status} tid={tid} esp={esp} "
                f"owner={owner} tile=00416850 post=00000000 lower=00405000 player={player}")

    converge, present = row("full_converge"), row("full_present")
    valid = [contract, ready, converge, present]
    logs = []

    def add(name, lines, *, passed=False, resolution="800x600"):
        logs.append(dict(name=name, log="\r\n".join(lines) + "\r\n", passed=passed, resolution=resolution))

    def incremental(*, world=(14, 20), scroll=(10, 17), dimensions=(100, 100),
                    status=1, tid=0x3AC, native_sp=0xEDC24, caller=0x407125,
                    gd=0x3E60030, vtable=0x50EE24, owner=0x40AD40, tile=0,
                    post=0, lower=0, player=0, guard_status=1, cell=None, present_flag=1):
        # Each marker contains its measured ESP, not a fabricated common ESP.
        # Normalization follows the actual PUSHFD/PUSHAD and native prologue.
        if cell is None:
            cell = (world[0] - scroll[0], world[1] - scroll[1])
        guard = (f"PTILE_COMPOSITION_GUARD tid={tid:x} esp={native_sp - 120:08x} status={guard_status} "
                 f"world=({world[0]},{world[1]}) cell=({cell[0]},{cell[1]}) "
                 f"present={present_flag} caller={caller:08x}")

        def observed(kind, esp):
            return (f"PTILE_{kind} tid={tid:x} esp={esp:08x} world=({world[0]},{world[1]}) "
                    f"caller={caller:08x} gd={gd:08x} map=({dimensions[0]},{dimensions[1]}) "
                    f"scroll=({scroll[0]},{scroll[1]}) vtable={vtable:08x}")

        packet = [guard, observed("INCREMENTAL_INPUT", native_sp - 36),
                  f"PTILE_STATUS hook=incremental status={status} tid={tid:x} esp={native_sp - 36:08x} "
                  f"owner={owner:08x} tile={tile:08x} post={post:08x} lower={lower:08x} player={player}"]
        if status == 0:
            packet.append(observed("NATIVE_NOOP_EXIT", native_sp - 28))
        return packet

    add("valid800", valid, passed=True)
    add("valid1024", [contract.replace("800x600", "1024x768"), ready.replace("800,600", "1024,768"),
                      converge, present], passed=True, resolution="1024x768")
    add("unpaired_ebp0_converge", [*valid, converge], passed=True)
    add("interleaved_frames", [contract, ready, converge, row("full_converge", tid="44c", esp="00700000"),
                               row("full_present", tid="44c", esp="00700000"), present], passed=True)
    add("two_fresh_pairs", [*valid, converge, present], passed=True)
    draw = incremental()
    clear = incremental(world=(14, 100), scroll=(10, 91), status=2)
    noop = incremental(world=(90, 7), status=0)
    add("incremental_draw_clear", [*valid, *draw, *clear], passed=True)
    add("incremental_native_noop", [*valid, *noop], passed=True)
    add("incremental_fresh_reused_stack", [*valid, *draw, *noop, *draw, *noop], passed=True)
    add("incremental_road_callback", [*valid, *incremental(tile=0x425120)], passed=True)
    add("incremental_build_callback", [*valid, *incremental(tile=0x429EC0)], passed=True)
    add("incremental_noop_is_not_presentation", [contract, ready, *noop])
    add("incremental_draw_is_not_presentation", [contract, ready, *draw])
    other = incremental(world=(90, 7), status=0, tid=0x44C, native_sp=0x700024)
    add("incremental_threads_interleaved", [*valid, noop[0], other[0], noop[1], other[1],
                                            other[2], noop[2], other[3], noop[3]], passed=True)
    for i, point in enumerate(((9, 20), (22, 20), (14, 16), (14, 27))):
        add(f"incremental_noop_edge800_{i}", [*valid, *incremental(world=point, status=0)], passed=True)
    for resolution, prefix, partials in (
        ("800x600", valid, ((14, 26),)),
        ("1024x768", [contract.replace("800x600", "1024x768"), ready.replace("800,600", "1024,768"),
                      converge, present], ((25, 20), (14, 28), (25, 28))),
    ):
        for i, point in enumerate(partials):
            add(f"incremental_partial_draw_{resolution}_{i}", [*prefix, *incremental(world=point)],
                passed=True, resolution=resolution)
            add(f"incremental_partial_zero_{resolution}_{i}", [*prefix, *incremental(world=point, status=0)],
                resolution=resolution)
    for name, packet in (("noop", noop), ("draw", draw), ("clear", clear)):
        for i in range(len(packet)):
            add(f"incremental_{name}_missing_{i}", [*valid, *packet[:i], *packet[i + 1:]])
            add(f"incremental_{name}_duplicate_{i}", [*valid, *packet[:i + 1], packet[i], *packet[i + 1:]])
        add(f"incremental_{name}_reversed", [*valid, *reversed(packet)])
        add(f"incremental_{name}_missing_guard_after_dump", [*valid, "SURFDUMP_DONE", *packet[1:]])
    add("incremental_extra_exit_after_draw", [*valid, *draw, noop[-1]])
    add("incremental_stale_guard", [*valid, noop[0], *draw])
    add("incremental_unfinished_after_dump", [*valid, "SURFDUMP_DONE", noop[0]])
    add("incremental_noop_without_exit_then_fresh_call", [*valid, *noop[:-1], *draw])
    nested_draw = incremental(native_sp=0xEDB24)
    for phase in (1, 2, 3):
        add(f"incremental_stale_other_stack_{phase}", [*valid, *noop[:phase], *nested_draw, *noop[phase:]])
    # A visible cell can call native rendering callbacks; an independently
    # completed nested call must not erase its outer guard/input requirement.
    add("incremental_visible_nested_call", [*valid, draw[0], *nested_draw, *draw[1:]], passed=True)
    add("incremental_premature_guard", [contract, noop[0], ready, *noop[1:], converge, present])
    add("incremental_zero_visible_full", [*valid, *incremental(status=0)])
    add("incremental_draw_outside_viewport", [*valid, *incremental(world=(90, 7))])
    add("incremental_clear_inside_world", [*valid, *incremental(status=2)])
    add("incremental_draw_outside_world", [*valid, *incremental(world=(14, 100), scroll=(10, 91))])
    add("incremental_clear_offscreen", [*valid, *incremental(world=(90, 7), status=2)])
    for name, options in (
        ("guard_zero", dict(guard_status=0)), ("guard_two", dict(guard_status=2)),
        ("guard_present_zero", dict(present_flag=0)), ("guard_present_two", dict(present_flag=2)),
        ("guard_wrong_cell", dict(cell=(0, 0))), ("null_caller", dict(caller=0)),
        ("null_gd", dict(gd=0)), ("null_vtable", dict(vtable=0)),
        ("map_width_zero", dict(dimensions=(0, 100))), ("map_width_large", dict(dimensions=(101, 100))),
        ("map_height_zero", dict(dimensions=(100, 0))), ("map_height_large", dict(dimensions=(100, 101))),
        ("negative_scroll_x", dict(scroll=(-1, 17))), ("negative_scroll_y", dict(scroll=(10, -1))),
        ("scroll_x_past_clamp", dict(scroll=(89, 17))), ("scroll_y_past_clamp", dict(scroll=(10, 92))),
        ("small_map_scroll", dict(dimensions=(8, 7), scroll=(1, 0))),
        ("unknown_owner", dict(owner=0x4617A0)), ("unknown_callback", dict(tile=0x416850)),
        ("post_callback", dict(post=0x425120)), ("lower_owner", dict(lower=1)),
        ("player_one", dict(player=1)), ("thread_zero", dict(tid=0)),
        ("coordinate_overflow", dict(world=(2147483648, 7))),
        ("negative_coordinate_overflow", dict(world=(-2147483649, 7))),
    ):
        add("incremental_invalid_" + name, [*valid, *incremental(**options)])
    for name, options in (
        ("negative_world", dict(world=(-1, 7))), ("outside_world", dict(world=(100, 7))),
        ("other_vtable", dict(vtable=0x562100)), ("road_callback", dict(tile=0x425120)),
        ("build_callback", dict(tile=0x429EC0)),
    ):
        add("incremental_noop_invalid_" + name, [*valid, *incremental(status=0, **options)])
    # Every identity and context field is checked independently, even if a
    # different call previously established an optimistic status or guard.
    for index, fields in (
        (0, (("esp=000edbac", "esp=000edbb0"), ("caller=00407125", "caller=00407126"),
             ("tid=3ac", "tid=44c"), ("world=(90,7)", "world=(91,7)"),
             ("cell=(80,-10)", "cell=(81,-10)"))),
        (1, (("esp=000edc00", "esp=000edc04"), ("caller=00407125", "caller=00407126"),
             ("tid=3ac", "tid=44c"), ("world=(90,7)", "world=(91,7)"))),
        (2, (("esp=000edc00", "esp=000edc04"), ("tid=3ac", "tid=44c"))),
        (3, (("esp=000edc08", "esp=000edc00"), ("caller=00407125", "caller=00407126"),
             ("tid=3ac", "tid=44c"), ("world=(90,7)", "world=(91,7)"),
             ("gd=03e60030", "gd=03e60034"), ("map=(100,100)", "map=(99,100)"),
             ("map=(100,100)", "map=(100,99)"), ("scroll=(10,17)", "scroll=(11,17)"),
             ("scroll=(10,17)", "scroll=(10,18)"), ("vtable=0050ee24", "vtable=0050ee28"))),
    ):
        for i, (old, new) in enumerate(fields):
            assert old in noop[index], (index, old, noop[index])
            changed = list(noop)
            changed[index] = changed[index].replace(old, new)
            add(f"incremental_changed_marker_{index}_{i}", [*valid, *changed])
    for i in range(4):
        for suffix, transform in (
            ("malformed", lambda value: value + " extra=1"),
            ("oversized_hex", lambda value: value.replace("tid=3ac", "tid=100000000")),
            ("stack_overflow", lambda value: value.replace(value.split("esp=", 1)[1].split()[0], "fffffff0")),
        ):
            changed = list(noop)
            changed[i] = transform(changed[i])
            add(f"incremental_marker_{i}_{suffix}", [*valid, *changed])
        # Malformed observations after an otherwise complete packet remain
        # failures; case errors cannot turn evidence rows into ignored text.
        add(f"incremental_marker_{i}_mixed_case_trailing",
            [*valid, *noop, "SURFDUMP_DONE", noop[i].replace("PTILE_", "Ptile_", 1)])
        marker, rest = noop[i].split(" ", 1)
        add(f"incremental_marker_{i}_unknown_suffix", [*valid, *noop, marker + "_EXTRA " + rest])
    normalized = list(noop)
    normalized[0] = normalized[0].replace("tid=3ac", "tid=000003AC").replace("caller=00407125", "caller=407125")
    normalized[-1] = normalized[-1].replace("vtable=0050ee24", "vtable=50EE24").replace("gd=03e60030", "gd=3E60030")
    add("incremental_hex_identity_normalized", [*valid, *normalized], passed=True)
    add("missing_contract", valid[1:])
    add("duplicate_contract", [contract, *valid])
    for name, replacement in (("wrong_sha", contract.replace(digest, "cd" * 32)),
                              ("wrong_stage", contract.replace(STAGE, BASE)),
                              ("wrong_resolution", contract.replace("800x600", "1024x768"))):
        add(name, [replacement, ready, converge, present])
        add(name + "_contamination", [replacement, *valid])
    add("premature_status", [converge, contract, ready, present])
    add("missing_converge", [contract, ready, present])
    add("missing_present", [contract, ready, converge])
    add("reversed_pair", [contract, ready, present, converge])
    add("reused_converge", [*valid, present])
    for field, kwargs in (("thread", dict(tid="44c")), ("stack", dict(esp="00700000")),
                          ("owner", dict(owner="00514e10"))):
        add("wrong_present_" + field, [contract, ready, converge, row("full_present", **kwargs)])
    for name, bad in (("zero_thread", row("full_converge", tid="0")),
                      ("zero_stack", row("full_converge", esp="0")),
                      ("oversized_thread", row("full_converge", tid="100000000")),
                      ("overflow_stack", row("full_converge", esp="10000000000000000")),
                      ("wrong_player", row("full_converge", player=1)),
                      ("unknown_hook", row("unknown")),
                      ("malformed_row", "PTILE_STATUS hook=full_converge"),
                      ("status_zero", row("full_converge", 0)),
                      ("present_status_two", row("full_present", 2)),
                      ("incremental_status_three", row("incremental", 3))):
        add(name, [*valid, "SURFDUMP_DONE", bad])
    add("reject_after_dump", [*valid, "SURFDUMP_DONE", "PTILE_REJECT full_present"])
    add("contract_fail_after_dump", [*valid, "SURFDUMP_DONE", "PTILE_CONTRACT_FAIL"])
    add("missing_map_ready", [contract, converge, present])
    add("repeated_map_ready", [contract, ready, ready, converge, present])
    add("map_ready_repeated_after_dump", [*valid, "SURFDUMP_DONE", ready])
    add("map_ready_before_contract", [ready, contract, converge, present])
    add("map_ready_after_converge", [contract, converge, ready, present])
    add("map_ready_after_complete_pair", [contract, converge, present, ready])
    add("incremental_before_map_ready", [contract, row("incremental"), ready, converge, present])
    for name, bad_ready in (
        ("wrong_map_owner", ready.replace("0040ad40", "0040ad41")),
        ("wrong_map_width", ready.replace("800,600", "1024,600")),
        ("wrong_map_height", ready.replace("800,600", "800,768")),
        ("wrong_map_resolution", ready.replace("800,600", "1024,768")),
        ("map_ready_missing_owner", "PTILE_MAP_READY size=(800,600)"),
        ("map_ready_missing_size", "PTILE_MAP_READY owner=0040ad40"),
        ("map_ready_wrong_case", ready.replace("ad40", "AD40")),
        ("map_ready_extra_field", ready + " accepted=1"),
        ("map_ready_malformed_size", ready.replace("800,600", "800x600")),
    ):
        add(name, [contract, bad_ready, converge, present])
        # A later correct line cannot erase an earlier bad readiness claim;
        # a completed dump cannot hide trailing readiness contamination either.
        add(name + "_before_valid", [contract, bad_ready, ready, converge, present])
        add(name + "_after_dump", [*valid, "SURFDUMP_DONE", bad_ready])
    options = [dict(name="valid", values={}, passed=True),
               dict(name="initial_valid", values=dict(InitialMapPaintValidation=True, Stage=INITIAL_STAGE), passed=True),
               dict(name="initial_without_partial", values=dict(InitialMapPaintValidation=True, PartialTileValidation=False, Stage=INITIAL_STAGE), passed=False),
               dict(name="initial_wrong_stage", values=dict(InitialMapPaintValidation=True), passed=False),
               dict(name="initial_stage_without_flag", values=dict(Stage=INITIAL_STAGE), passed=False),
               dict(name="initial_grace", values=dict(InitialMapPaintValidation=True, Stage=INITIAL_STAGE, ContinueAfterDumpSec=5), passed=False),
               dict(name="ordinary_unaffected", values=dict(PartialTileValidation=False, Stage=BASE,
                    CandidateDir="", WorkDir="C:\\Clash", OutRoot=str(ROOT / "captures/archive")), passed=True)]
    forbidden = dict(Stage=BASE, UseDdrawProxy=False, AllowVisibleDesktop=True, ExtraProbeTemplate="custom.cdb",
                     ForceVisibleEdges=True, PostOwnerForceVisibleSeven=True, SkipMapValidation=True,
                     UseCdbWriteMem=True, LoadSlot=1, ProbeTemplate="C:\\Synthetic\\custom.cdb", MissingBuilder=True)
    for name, value in forbidden.items():
        options.append(dict(name="reject_" + name, values={name: value}, passed=False))
    for name, values in (
        ("candidate_missing", dict(CandidateDir="")),
        ("candidate_repo", dict(CandidateDir=str(ROOT / "candidate"))),
        ("candidate_prefix_collision", dict(CandidateDir="C:\\ClashTestsOther\\candidate")),
        ("candidate_escape", dict(CandidateDir="C:\\ClashTests\\..\\Windows\\candidate")),
        ("workdir_original", dict(WorkDir="C:\\Clash")),
        ("output_repo", dict(OutRoot=str(ROOT / "captures/archive"))),
        ("output_prefix_collision", dict(OutRoot="C:\\ClashCapturesOther\\run")),
        ("output_escape", dict(OutRoot="C:\\ClashCaptures\\..\\Windows\\run")),
    ):
        options.append(dict(name=name, values=values, passed=False))
    outer = [dict(name="healthy", av=False, quit=False, runtime_error=None, partial_error=None, failed=False),
             dict(name="partial_rejected", av=False, quit=False, runtime_error=None, partial_error="synthetic partial failure", failed=True),
             dict(name="access_violation", av=True, quit=False, runtime_error=None, partial_error=None, failed=True),
             dict(name="native_quit", av=False, quit=True, runtime_error=None, partial_error=None, failed=True),
             dict(name="host_error", av=False, quit=False, runtime_error="synthetic host failure", partial_error=None, failed=True)]
    preflight = []
    preflight_good = dict(preflight_passed=True, stage=STAGE, resolution="1024x768", candidate_sha256=digest)
    for name, update, exit_code in (("good", {}, 0), ("nonzero_exit", {}, 9),
                                    ("false_pass", dict(preflight_passed=False), 0),
                                    ("wrong_stage", dict(stage=BASE), 0),
                                    ("wrong_resolution", dict(resolution="800x600"), 0)):
        preflight.append(dict(name=name, response=json.dumps({**preflight_good, **update}),
                              exit=exit_code, passed=name == "good"))
    preflight.append(dict(name="malformed_response", response="not json", exit=0, passed=False))
    candidates = [dict(name="exact", partial=True, sha=digest, passed=True),
                  dict(name="uppercase_host_hash", partial=True, sha=digest.upper(), passed=True),
                  dict(name="wrong_hash", partial=True, sha="cd" * 32, passed=False),
                  dict(name="ordinary_unaffected", partial=False, sha="cd" * 32, passed=True)]
    return dict(stage=STAGE, base=BASE, sha=digest, options=options, logs=logs, outer=outer,
                preflight=preflight, candidates=candidates)


@unittest.skipUnless(sys.platform == "win32" and POWERSHELL.exists(), "requires Windows PowerShell for pure AST fixtures")
class PartialTileSurfaceHarnessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = scenarios()
        with tempfile.TemporaryDirectory(prefix="clash-partial-surface-fixture-") as folder:
            script = Path(folder) / "pure-fixture.ps1"
            cases = Path(folder) / "cases.json"
            script.write_text(FIXTURE, encoding="utf-8")
            cases.write_text(json.dumps(cls.cases), encoding="utf-8")
            result = subprocess.run([str(POWERSHELL), "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
                                     "-File", str(script), str(HARNESS), str(ROOT), str(cases)],
                                    capture_output=True, text=True, timeout=30,
                                    creationflags=subprocess.CREATE_NO_WINDOW)
        if result.returncode:
            raise AssertionError(result.stderr + result.stdout)
        cls.result = json.loads(result.stdout)

    def test_partial_options_fail_before_artifacts_and_preserve_ordinary_mode(self):
        actual = {v["name"]: v for v in self.result["options"]}
        for case in self.cases["options"]:
            with self.subTest(case=case["name"]):
                row = actual[case["name"]]
                self.assertEqual(not bool(row["error"]), case["passed"], row)
        self.assertEqual(actual["valid"]["recipe"], BASE)
        self.assertTrue(actual["valid"]["require_gameplay"])
        self.assertFalse(actual["ordinary_unaffected"]["require_gameplay"])

    def test_loaded_contract_and_complete_fresh_status_pairs(self):
        actual = {v["name"]: v for v in self.result["logs"]}
        for case in self.cases["logs"]:
            with self.subTest(case=case["name"]):
                row = actual[case["name"]]
                self.assertIsNone(row["exception"], row)
                self.assertEqual(not bool(row["error"]), case["passed"], row)

    def test_initial_paint_requires_explicit_variant_and_pauses_at_closed_boundary(self):
        options = {v["name"]: v for v in self.result["options"]}
        self.assertEqual(options["initial_valid"]["builder_options"], ["--initial-map-paint"])
        self.assertEqual(options["initial_valid"]["recipe"], BASE)
        self.assertEqual([row["ready"] for row in self.result["initial_dump"]], [False, False, False, True])
        for row in self.result["initial_dump"]:
            action = row["action"]
            self.assertIn('PTILE_TRACE_CLOSED tid=%x eip=%p esp=%p', action)
            self.assertIn('@$tid, @eip, @esp', action)
            self.assertTrue(action.endswith('.echo SURFDUMP_HOST_READY;'))
            # No continue/quit or target write may follow the complete boundary.
            self.assertNotRegex(action, r'(?:^|;)\s*(?:g[co]?|q|r|e[bdw])(?:\s|;|$)')

    def test_map_readiness_is_unique_exact_and_precedes_every_status(self):
        actual = {v["name"]: v for v in self.result["logs"]}
        expected_errors = {
            "missing_map_ready": "native map-owner readiness missing or mismatched",
            "repeated_map_ready": "native map-owner readiness missing or mismatched",
            "map_ready_repeated_after_dump": "native map-owner readiness missing or mismatched",
            "map_ready_before_contract": "map readiness precedes loaded contract",
            "map_ready_after_converge": "malformed or premature partial-tile status",
            "map_ready_after_complete_pair": "malformed or premature partial-tile status",
            "incremental_before_map_ready": "malformed or premature partial-tile status",
        }
        for name, error in expected_errors.items():
            with self.subTest(case=name):
                self.assertEqual(actual[name]["error"], error)
        for name, row in actual.items():
            if name.startswith(("wrong_map_", "map_ready_missing_", "map_ready_wrong_",
                                "map_ready_extra_", "map_ready_malformed_")):
                with self.subTest(case=name):
                    self.assertEqual(row["error"], "native map-owner readiness missing or mismatched")
        # Previous status-pair negatives must still reach the status gate after
        # readiness, rather than passing only because their fixtures omit it.
        self.assertIn("preceding convergence", actual["missing_converge"]["error"])
        self.assertEqual(actual["status_zero"]["error"], "unsupported partial-tile status")

    def test_zero_status_requires_its_own_guard_and_native_exit_without_draw_credit(self):
        actual = {v["name"]: v for v in self.result["logs"]}
        for name in ("incremental_native_noop", "incremental_fresh_reused_stack",
                     "incremental_threads_interleaved", "incremental_hex_identity_normalized"):
            with self.subTest(case=name):
                self.assertIsNone(actual[name]["error"])
        self.assertEqual(actual["incremental_noop_is_not_presentation"]["error"],
                         "no complete partial-tile composition/presentation pair")
        self.assertEqual(actual["incremental_invalid_guard_zero"]["error"],
                         "incremental composition guard did not approve the actual call")
        for name in ("incremental_noop_missing_0", "incremental_noop_missing_1",
                     "incremental_noop_missing_2", "incremental_noop_missing_3",
                     "incremental_extra_exit_after_draw", "incremental_stale_other_stack_1",
                     "incremental_stale_other_stack_2", "incremental_stale_other_stack_3"):
            with self.subTest(case=name):
                self.assertTrue(actual[name]["error"])

    def test_partial_strips_require_rendering_and_world_edge_clear_is_distinct(self):
        actual = {v["name"]: v for v in self.result["logs"]}
        for name, row in actual.items():
            if name.startswith("incremental_partial_zero_"):
                with self.subTest(case=name):
                    self.assertEqual(row["error"], "zero status is not a supported native offscreen no-op")
            elif name.startswith("incremental_partial_draw_"):
                with self.subTest(case=name):
                    self.assertIsNone(row["error"])
        self.assertIsNone(actual["incremental_draw_clear"]["error"])
        for name in ("incremental_clear_inside_world", "incremental_draw_outside_world", "incremental_clear_offscreen"):
            with self.subTest(case=name):
                self.assertEqual(actual[name]["error"], "incremental draw or clear status contradicts actual cell bounds")

    def test_mocked_builder_is_bound_and_failure_prevents_acceptance(self):
        for row in self.result["builds"]:
            with self.subTest(partial=row["partial"], resolution=row["resolution"], exit=row["exit"]):
                self.assertEqual(len(row["calls"]), 1)
                args = row["calls"][0]
                if row["partial"]:
                    self.assertEqual(args, ["-B", str(ROOT / "tools/build_partial_tile_candidate.py"),
                        "--original", "C:\\SyntheticOriginal\\clash95.exe", "--output", "C:\\ClashTests\\synthetic-partial\\candidate\\new.exe",
                        "--resolution", row["resolution"], "--report-json", "C:\\ClashCaptures\\synthetic-partial\\run\\partial-tile-build.json",
                        "--probe-out", "C:\\ClashCaptures\\synthetic-partial\\run\\partial-tile-installed.extra.cdb"])
                    self.assertEqual(row["extra_probe"], args[-1])
                else:
                    self.assertEqual(args, [str(ROOT / "patch_clash95_hd.py"), "--input", "C:\\SyntheticOriginal\\clash95.exe",
                        "--output", "C:\\ClashTests\\synthetic-partial\\candidate\\new.exe", "--stage", BASE,
                        "--resolution", row["resolution"]])
                    self.assertEqual(row["extra_probe"], "")
                self.assertEqual(bool(row["error"]), row["exit"] != 0)

    def test_complete_builder_exit_gate_is_separate_and_fail_closed(self):
        rows = self.result["complete_builder_exits"]
        self.assertEqual([row["exit"] for row in rows], [0, 9])
        self.assertIsNone(rows[0]["error"])
        self.assertEqual(rows[1]["error"], "Complete candidate builder failed with exit code 9")

    def test_completed_dump_cannot_hide_partial_or_runtime_failure(self):
        expected = {v["name"]: v["failed"] for v in self.cases["outer"]}
        for row in self.result["outer"]:
            with self.subTest(case=row["name"], grace=row["grace"]):
                self.assertEqual(row["failed"], expected[row["name"]])
                self.assertEqual(bool(row["error"]), expected[row["name"]])

    def test_pure_preflight_and_written_candidate_must_match(self):
        for group in ("preflight", "candidates"):
            expected = {v["name"]: v["passed"] for v in self.cases[group]}
            for row in self.result[group]:
                with self.subTest(group=group, case=row["name"]):
                    self.assertEqual(not bool(row["error"]), expected[row["name"]], row)
                    if group == "preflight":
                        self.assertEqual(row["calls"], [["-B", str(ROOT / "tools/build_partial_tile_candidate.py"),
                            "--original", "C:\\SyntheticOriginal\\clash95.exe", "--resolution", "1024x768", "--preflight"]])

    def test_stage_mapping_preflight_and_loaded_candidate_provenance_are_wired(self):
        text = HARNESS.read_text(encoding="utf-8-sig")
        self.assertLess(text.index("Partial-tile builder is missing."), text.index("Add-Type @'"))
        self.assertLess(text.index("$probeRecipeJson = & $pythonExe"), text.index("& $DdrawProxyBuildScript"))
        self.assertLess(text.index("$partialPreflightJson = & $pythonExe"), text.index("& $DdrawProxyBuildScript"))
        self.assertLess(text.index("Partial-tile candidate differs from the preflight recipe."), text.index("$probeText = $probeRecipe.template"))
        self.assertIn("'--stage', $recipeStage", text)
        self.assertIn("$candidateSha = Get-FileSha256 -Path $candidateFull", text)
        self.assertIn("-CandidateSha256 $candidateSha", text)
        self.assertIn("PartialTileStatusGatePassed =", text)
        self.assertIn("HiddenDesktop = (-not $AllowVisibleDesktop)", text)


if __name__ == "__main__":
    unittest.main()
