# PR Body: Clash95 HD Completion Boundary

## Summary

This branch refreshes the Clash95 HD completion evidence and release packaging
boundary. The stable HD map stage remains unchanged:

`gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch`

`rightbottomcompose` and `castlecenter-all` remain validation-only until manual
DirectInput proof or a strict approved CDB-only override exists.

## Evidence

- Stable HD map candidate: `C:\ClashTests\hd-map-smoke\clash95_hd_smoke_20260515_103606.exe`
- Stable SHA-256: `5E162FA81DF59533E0B99A0DCBC9EA24280DBEC46411AE871E968D6536C08B33`
- Stable patch-stage: `118` patched, `0` original, `0` unexpected
- Castle validation SHA-256: `1902213ADF825A7D7612A14C74AC5468BEBFCC4F00B43E60601FD8A832806DF6`
- Castlecenter-all patch-stage: `134` patched, `0` original, `0` unexpected
- Castle overview gate now includes a visual-integrity stripe detector. The
  old stripey palette-aware run fails that detector; the fixed native-render
  overview wrapper passes it.
- Fresh hidden castle runs:
  - `captures\archive\cdb-surface-dump-20260515-105041`
  - `captures\archive\cdb-surface-dump-20260515-105411`
  - `captures\archive\cdb-surface-dump-20260515-105458`
  - `captures\archive\cdb-surface-dump-20260515-105557`
- Fresh small reports:
  - `reports\hd_completion_plan.md`
  - `reports\patch_stage_inventory.md`
  - `reports\final_hd_validation_matrix.md`
  - `reports\final_hd_release_checklist.md`

## Packaging Boundary

No proprietary game binaries, patched executables, copied assets, saves, dumps,
wrapper DLL binaries, ISO/CD contents, cracks, or large raw captures are part of
the release. Users build candidates locally from their own verified
`C:\Clash\clash95.exe`.

## Remaining Limitation

Manual DirectInput proof remains pending for five targets:
`stable_menu_load`, `stable_hd_map_input`, `right_bottom_validation_input`,
`castle_barracks_centered_input`, and `castle_overview_centered_input`.

This PR should not claim final release completion until that manifest passes or
a separately approved CDB-only override manifest is supplied.
