# Right-Bottom Slot Fixture Runtime Plan

- Status: PASS
- Generated: `2026-06-15T22:35:47+02:00`
- Runtime policy: repo-only command planner; reads generated JSON and writes JSON/Markdown reports; does not run PowerShell, copy saves, launch Clash95, CDB, wrappers, or visible windows
- Guard policy: passes only when the right-bottom slot fixture remains non-promoting, the dry-run preparation helper is source-guarded, and the future CDB command stays hidden-desktop with an isolated workdir/candidate dir
- Fixture plan: `captures\current\right-bottom-slot-fixture-plan-current.json`
- Script guard: `captures\current\right-bottom-slot-fixture-script-guard-current.json`
- Surface-dump script: `scripts\cdb\run_cdb_surface_dump.ps1`
- Extra probe: `probes\cdb\castle\clash95_castle_cmd99_owner_action_descriptor_extra.cdb`
- Result parser: `tools\right_bottom_slot_fixture_result_summary.py`

## Summary

- Proof class: `non_natural_isolated_fixture`
- Promotion ready: `False`
- stable_stage_should_change: `False`
- Fixture root: `C:\ClashTests\right-bottom-slot5-as-slot0-fixture`
- Fixture save: `C:\ClashTests\right-bottom-slot5-as-slot0-fixture\save\0.dat`
- Candidate dir: `C:\ClashTests\right-bottom-slot5-as-slot0-fixture\candidate`
- Target load slot: `0`
- Prepare seed workdir: `True`
- Stage: `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-rightbottomaction-nativecenter`
- Result log template: `captures\cdb-surface-dump-FIXTURE-RUN\cdb-surface-dump.log`
- Result JSON template: `captures\cdb-surface-dump-FIXTURE-RUN\right-bottom-slot-fixture-result-summary.json`
- Result Markdown template: `captures\cdb-surface-dump-FIXTURE-RUN\right-bottom-slot-fixture-result-summary.md`

## Commands

### prepare_dry_run

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File 'scripts\smoke\prepare_right_bottom_slot_fixture.ps1' -SeedWorkDir -Json
```

### prepare_execute

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File 'scripts\smoke\prepare_right_bottom_slot_fixture.ps1' -SeedWorkDir -Execute
```

### hidden_fixture_probe

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File 'scripts\cdb\run_cdb_surface_dump.ps1' -UseDdrawProxy -FastForwardStartAnims -SkipMapValidation -Stage 'gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-rightbottomaction-nativecenter' -WorkDir 'C:\ClashTests\right-bottom-slot5-as-slot0-fixture' -CandidateDir 'C:\ClashTests\right-bottom-slot5-as-slot0-fixture\candidate' -LoadSlot 0 -ExtraProbeTemplate 'probes\cdb\castle\clash95_castle_cmd99_owner_action_descriptor_extra.cdb' -RunSeconds 120
```

### summarize_fixture_result

```powershell
python 'tools\right_bottom_slot_fixture_result_summary.py' 'captures\cdb-surface-dump-FIXTURE-RUN\cdb-surface-dump.log' --expected-slot 0 --write-json 'captures\cdb-surface-dump-FIXTURE-RUN\right-bottom-slot-fixture-result-summary.json' --write-md 'captures\cdb-surface-dump-FIXTURE-RUN\right-bottom-slot-fixture-result-summary.md' --require-load-success --require-slot-match --require-owner-bit2 --require-owner-action
```

## Runtime Prerequisites

- fixture root must be a complete isolated Clash95 working directory seeded outside the repository
- scripts/smoke/prepare_right_bottom_slot_fixture.ps1 seeds non-save children from C:\Clash, then overlays only the route-compatible save as save\0.dat
- scripts/cdb/run_cdb_surface_dump.ps1 must use the fixture root as -WorkDir so save\0.dat is local to the fixture
- scripts/cdb/run_cdb_surface_dump.ps1 must use a child -CandidateDir so the DirectDraw proxy is not placed directly in the workdir
- right_bottom_slot_fixture_result_summary.py must keep selected_arg and selected_global consistent with expected slot 0
- the result remains non-natural fixture evidence until rows 3-5 naturally enter the load menu and LOADSAVE

## Expected Success Markers

- `SURFDUMP_LOADSAVE selected_arg=0 selected_global=0`
- `SURFDUMP_PLAYGAME`
- `NOWNER_OWNER_FLAG_TEST owner_flag has bit2 set`
- `NOWNER_4338E0_ENTRY or owner/action renderer rows`
- `fixture result summary status=owner_action_reached`
- `no AV_SURFDUMP rows`
