# Final HD Release Checklist

Generated: 2026-05-15

## Release Status

- [x] Work is on feature branch `complete-hd-mod-20260515`.
- [x] Original `C:\Clash\clash95.exe` was not overwritten.
- [x] Base SHA matches `500055d77d03d514e8d3168506bd10f67cd8569bcc450604ff8192f46cdaf3ae`.
- [x] Stable HD-map candidate builds under `C:\ClashTests\hd-map-smoke`.
- [x] Stable patch-stage gate passes with `118` patched, `0` original, `0` unexpected.
- [x] Stable HD-map smoke matrix passes.
- [x] Castlecenter-all hidden/no-popup catalog, visual-integrity, hitbox, and multi-hit runs pass on fixed SHA `1902213ADF825A7D7612A14C74AC5468BEBFCC4F00B43E60601FD8A832806DF6`.
- [x] Castlecenter-all patch-stage gate passes with `134` patched, `0` original, `0` unexpected.
- [x] No proprietary executable should be committed; generated candidates stay under `C:\ClashTests`.
- [x] README documents source-only packaging and local candidate build flow.
- [ ] Manual DirectInput proof manifest passes for all five required targets.
- [ ] Promotion decision tools allow stable promotion.

## Required Before Calling The Mod Complete

1. Ask for explicit visible/manual runtime approval.
2. Run a single controlled manual session on the stable stage first.
3. Run validation-stage manual checks for right-bottom and castlecenter-all.
4. Write a manual proof manifest with all five target IDs passing.
5. Run promotion decision tools against that manifest.
6. Only then promote proven validation patch groups or create a final `complete-hd` alias.

## Source-Only Release Boundary

Release packages must contain scripts, documentation, and small evidence
manifests only. Do not include patched executables, original game binaries,
wrapper DLL binaries, raw dumps, saves, copied game assets, CD/ISO contents,
cracks, or large proprietary captures.

## Cleanup Guidance

Generated candidates may be removed by deleting the relevant subdirectory under
`C:\ClashTests`. Never delete or mutate `C:\Clash\clash95.exe` as part of
cleanup.
