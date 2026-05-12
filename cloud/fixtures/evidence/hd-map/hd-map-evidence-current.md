# Current HD Map Evidence

- Updated: `2026-05-08`
- Scope: current 800x600 Clash95 HD map patch-stage evidence.
- Runtime policy: CDB-only evidence.
- Binary policy: generated executables stay outside the repository.

## Status

- HD map smoke matrix: PASS
- Patch-stage byte gate: PASS, `118/118` selected current HD map bytes patched
- Post-owner visibility evidence: PASS
- Normal dark right/bottom cells: explained by visibility/fog state
- Forced-visible seven-cell proof: PASS, zero blank active cells
- Patch manifest comparison: available, no `original` / `unexpected` records

## Reports

- [HD map smoke matrix](hd-map-smoke-current.md)
- [Post-owner evidence matrix](post-owner-evidence-current.md)
- [Patch manifest comparison, current vs partial12](patch-manifest-compare-current-vs-partial12.md)
- [Evidence index consistency check](hd-map-evidence-current-check.json)
- [Normal post-owner run summary](cdb-surface-dump-20260506-190037/RUN-SUMMARY.md)
- [Forced-visible post-owner run summary](cdb-surface-dump-20260506-201114/RUN-SUMMARY.md)

## Screenshot Artifacts

Normal post-owner visibility-zero surface:

![normal post-owner surface](<SOURCE_REPO>/captures/cdb-surface-dump-20260506-190037/surface.png)

Forced-visible post-owner surface:

![forced-visible post-owner surface](<SOURCE_REPO>/captures/cdb-surface-dump-20260506-201114/surface.png)

## Key Evidence

- Candidate selected by the smoke matrix:
  `C:\ClashTests\cdb-post-owner-forced-visible\clash95_hd_surfdump_20260506_201114.exe`
- Candidate SHA-256:
  `5E162FA81DF59533E0B99A0DCBC9EA24280DBEC46411AE871E968D6536C08B33`
- Stage:
  `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch`
- Normal evidence pair:
  `captures\cdb-surface-dump-20260506-190037`
- Forced-visible evidence pair:
  `captures\cdb-surface-dump-20260506-201114`
- Seven normal blank cells:
  `r6c10`, `r6c11`, `r7c10`, `r7c11`, `r8c0`, `r8c10`, `r8c11`
- Normal visibility classification:
  all seven cells are `visibility_zero`
- Forced-visible classification:
  no blank active cells remain

## Patch Manifest Highlights

`patch-manifest-compare-current-vs-partial12.md` compares the archived
dynvswitch manifest to the partial12 manifest. It highlights:

- `0x017DFF`: full redraw bottom-row column cutoff `09 -> 0C`
- `0x017EDB`: single-tile repaint bottom-row cutoff `09 -> 0C`
- `0x0E8DC0`: dynamic viewport-switch cave branch byte change

## Refresh Commands

```powershell
& '<USER_HOME>\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' tools\hd_map_smoke_matrix.py `
  --require-pass `
  --write-json captures\hd-map-smoke-current.json `
  --write-markdown captures\hd-map-smoke-current.md
```

```powershell
& '<USER_HOME>\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' tools\patch_manifest_compare.py `
  captures\patch-stage-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-20260424.json `
  captures\patch-stage-mapdraw-partial12-20260424.json `
  --write-json captures\patch-manifest-compare-current-vs-partial12.json `
  --write-markdown captures\patch-manifest-compare-current-vs-partial12.md `
  --limit 8
```

```powershell
& '<USER_HOME>\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' tools\evidence_index_check.py `
  captures\hd-map-evidence-current.md `
  --require-pass `
  --write-json captures\hd-map-evidence-current-check.json
```

## Interpretation

The current HD map path draws the right/bottom cells when visibility permits it.
The normal black cells in this save are explained by fog/unexplored visibility,
not by a remaining 12x9 map loop, present-bounds, minimap, or action-panel
copyback defect.
