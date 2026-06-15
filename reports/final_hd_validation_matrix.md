# Final HD Validation Matrix

Generated: 2026-05-22

## Verdict

Automated repo-only and hidden/no-popup validation is passing. The HD mod is not
yet release-complete because manual DirectInput proof remains pending and the
user has not approved a CDB-only promotion override. The focused
battle/right-bottom command lane is `99.91%`: command readiness is proven in
visible runs, but real visible click-to-callback proof is still open.

## Gate Matrix

| Area | Command / source | Candidate SHA | Result | Artifacts |
|---|---|---|---|---|
| Stable dry run | `scripts/smoke/prepare_hd_map_smoke_candidate.ps1 -Json` | n/a | PASS | base SHA `ok`; planned output under `C:\ClashTests\hd-map-smoke` |
| Stable build | `scripts/smoke/prepare_hd_map_smoke_candidate.ps1 -Execute` | `5E162FA81DF59533E0B99A0DCBC9EA24280DBEC46411AE871E968D6536C08B33` | PASS | `C:\ClashTests\hd-map-smoke\clash95_hd_smoke_20260515_103606.exe` |
| Stable patch-stage | `patch_stage_report.py --require-current-hd-map` via helper | `5E162FA81DF59533E0B99A0DCBC9EA24280DBEC46411AE871E968D6536C08B33` | PASS | `captures\current\patch-stage-current-hd-map.json`; `118` patched, `0` original, `0` unexpected |
| Stable smoke matrix | `hd_map_smoke_matrix.py --require-pass` via helper | `5E162FA81DF59533E0B99A0DCBC9EA24280DBEC46411AE871E968D6536C08B33` | PASS | `captures\current\hd-map-smoke-current.json`, `captures\current\hd-map-smoke-current.md` |
| Castle catalog hidden run | `scripts/cdb/run_cdb_surface_dump.ps1 -UseDdrawProxy -FastForwardStartAnims -SkipMapValidation -ExtraProbeTemplate .\probes\cdb\castle\clash95_castle_interior_catalog_extra.cdb` | `1902213ADF825A7D7612A14C74AC5468BEBFCC4F00B43E60601FD8A832806DF6` | PASS | `captures\archive\cdb-surface-dump-20260515-105041`; DirectDraw-palette screenshot is clean/non-stripey |
| Castle patch-stage | `patch_stage_report.py --stage ...castlecenter-all` | `1902213ADF825A7D7612A14C74AC5468BEBFCC4F00B43E60601FD8A832806DF6` | PASS | `reports\castlecenter_all_patch_stage_20260515_105041.json`; `134` patched, `0` original, `0` unexpected |
| Castle overview gate | `castle_overview_gate.py captures\archive\cdb-surface-dump-20260515-105041 --barracks-run captures\archive\cdb-surface-dump-20260512-082418 --require-pass` | `1902213ADF825A7D7612A14C74AC5468BEBFCC4F00B43E60601FD8A832806DF6` | PASS | `reports\castle_overview_gate_20260515_105041.json`, `.md`; centered geometry and stripe visual-integrity gate PASS |
| Focused overview hitbox | `castle_overview_hitbox_summary.py ... --require-displayed-hit --require-descriptor --require-click-gate --forbid-callback` | `1902213ADF825A7D7612A14C74AC5468BEBFCC4F00B43E60601FD8A832806DF6` | PASS | `reports\castle_overview_hitbox_20260515_105411.json`, `.md`; displayed wrapper/gate proof passed |
| Overview visible multi-hit | `castle_overview_multihit_summary.py ... --require-all-targets --forbid-callback` | `1902213ADF825A7D7612A14C74AC5468BEBFCC4F00B43E60601FD8A832806DF6` | PASS | `reports\castle_overview_multihit_20260515_105458.json`, `.md`; commands `0x86`, `0x63`, `0x87` |
| Overview dormant multi-hit | `castle_overview_multihit_summary.py ... --require-all-targets --forbid-callback` | `1902213ADF825A7D7612A14C74AC5468BEBFCC4F00B43E60601FD8A832806DF6` | PASS | `reports\castle_overview_flags1f_multihit_20260515_105557.json`, `.md`; commands `0x99`, `0x9C`, `0x9F`, `0xA6` |
| Battle/right-bottom evidence matrix | `battle_ui_evidence_matrix.py --require-pass` | `F3BC31F22EC15765D525ED3EADD00183C78BB1B8F76B3B1C3978AF3480A546EF` / `F84933776944E2B616F6BBCCF7708ABBF06498D5438FA8DF7B7AF1BB56CD180A` | PASS | `captures\current\battle-ui-evidence-current.json`, `.md`; visible command readiness included; promotion remains validation-only |
| Battle visible input summary | `battle_visible_input_summary.py --require-click-consumed` | n/a | EXPECTED FAIL until proof | `captures\current\battle-visible-input-current.json`, `.md`; focused completion `99.91%`, command-ready runs `2/3`, click-consumed runs `0/3`, invalid runs `1`, post-`g` break-instruction exception runs `1/3` |
| Battle visible harness guard | `battle_visible_harness_guard.py --require-pass` | n/a | PASS | `captures\current\battle-visible-harness-guard-current.json`, `.md`; fail-fast coverage for breakpoint insert/remove failures and post-`g` `80000003` exceptions |
| Manual DirectInput | `manual_directinput_checklist.py --require-promotion-ready` | n/a | EXPECTED FAIL until proof | Five required target IDs remain pending |
| Artifact hygiene | `rg --files -g "*.exe"` | n/a | expected empty | no repository executables may be present |

## Fresh Hidden Commands Run

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\smoke\prepare_hd_map_smoke_candidate.ps1 -Execute

powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts/cdb/run_cdb_surface_dump.ps1 -UseDdrawProxy -FastForwardStartAnims -SkipMapValidation -Stage 'gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-castlecenter-all' -ExtraProbeTemplate .\probes\cdb\castle\clash95_castle_interior_catalog_extra.cdb -CandidateDir C:\ClashTests\cdb-castle-overview-catalog -RunSeconds 120

powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts/cdb/run_cdb_surface_dump.ps1 -UseDdrawProxy -FastForwardStartAnims -SkipMapValidation -Stage 'gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-castlecenter-all' -ExtraProbeTemplate .\probes\cdb\castle\clash95_castle_interior_catalog_extra.cdb -CandidateDir C:\ClashTests\cdb-castle-overview-nativerender -RunSeconds 120

powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts/cdb/run_cdb_surface_dump.ps1 -UseDdrawProxy -FastForwardStartAnims -SkipMapValidation -Stage 'gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-castlecenter-all' -ExtraProbeTemplate .\probes\cdb\castle\clash95_castle_overview_hitbox_extra.cdb -CandidateDir C:\ClashTests\cdb-castle-overview-nativerender-hitbox -RunSeconds 120

powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts/cdb/run_cdb_surface_dump.ps1 -UseDdrawProxy -FastForwardStartAnims -SkipMapValidation -Stage 'gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-castlecenter-all' -ExtraProbeTemplate .\probes\cdb\castle\clash95_castle_overview_multihit_extra.cdb -CandidateDir C:\ClashTests\cdb-castle-overview-nativerender-multihit -RunSeconds 120

powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts/cdb/run_cdb_surface_dump.ps1 -UseDdrawProxy -FastForwardStartAnims -SkipMapValidation -Stage 'gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-castlecenter-all' -ExtraProbeTemplate .\probes\cdb\castle\clash95_castle_overview_flags1f_multihit_extra.cdb -CandidateDir C:\ClashTests\cdb-castle-overview-nativerender-flags1f-multihit -RunSeconds 120
```

## Remaining Release Limitation

The current evidence is structured and reproducible, but it is hidden CDB/proxy
evidence plus partial visible-window command-readiness evidence. It is not
manual DirectInput proof, and it is not yet real visible battle command
click-to-callback proof. Stable promotion and release-ready claims remain
blocked until the approved manual proof manifest passes or a separate explicit
CDB-only override manifest is approved.

## Completion Summary

- Focused battle/right-bottom command lane: `99.91%`.
- Full-game reverse engineering: not `100%`.
- Current blocker: real visible click-to-callback proof for the battle command
  descriptor.
