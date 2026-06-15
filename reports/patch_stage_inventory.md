# Patch Stage Inventory

Generated: 2026-05-15

Sources: `patch_clash95_hd.py`, `captures\current\patch-definition-current.json`,
`captures\current\stable-stage-guard-current.json`, and current evidence reports.

## Summary

- Patches: `165`.
- Patch groups: `36`.
- Stages: `48`.
- Stable/default stage: `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch`.
- Stable selected patch count: `118`.
- Validation-only groups absent from stable: yes.
- Current incompatible overlap failures: `0`.

## Active Stage Categories

- Stable: `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch`.
- Validation-only: `rightbottomcompose`, `castlecenter`, `castlecenter-hitbox`, `castlecenter-all`.
- Legacy diagnostics: `menusurface*`, broad `core`/`draw`/`helpers`, old centered/menu-only experiments.
- Input diagnostics: `absinput`, `absformat`, `absquarter`, `screenorigin`, `deltaclamp`, `hybridmouse`, and nonexclusive mouse stages.

## Stage Table

| Stage | Category | Groups | Patches | Extras / notes |
|---|---:|---:|---:|---|
| `display` | diagnostic | 1 | 4 |  |
| `display-absinput` | input diagnostic | 2 | 5 | `mouse-absolute-assign` |
| `display-centered-visual-absinput` | input diagnostic | 3 | 6 | `menu-only-center-blit`, `mouse-absolute-assign` |
| `isolate-gameplay-surface-absinput` | diagnostic isolate | 3 | 7 | `mouse-absolute-assign` |
| `isolate-viewport-init-absinput` | diagnostic isolate | 4 | 9 | `mouse-absolute-assign` |
| `isolate-input-bounds-absinput` | diagnostic isolate | 3 | 7 | `mouse-absolute-assign` |
| `isolate-viewport-call-absinput` | diagnostic isolate | 3 | 7 | `mouse-absolute-assign` |
| `isolate-main-loops-absinput` | diagnostic isolate | 3 | 19 | `mouse-absolute-assign` |
| `isolate-surface-viewport-absinput` | diagnostic isolate | 5 | 11 | `mouse-absolute-assign` |
| `gameplay-menu640` | diagnostic | 5 | 24 |  |
| `gameplay-menu640-centered` | diagnostic | 6 | 25 | `menu-only-center-blit` |
| `gameplay-menu640-centered-hitboxes` | diagnostic | 7 | 65 | `menu-only-center-blit` |
| `gameplay-menu640-centered-relinput` | diagnostic | 7 | 65 | `menu-only-center-blit` |
| `gameplay-menu640-centered-map12-relinput` | diagnostic | 9 | 99 | `viewport-switch`, `menu-only-center-blit` |
| `gameplay-menu640-centered-map12-novswitch-relinput` | diagnostic | 8 | 97 | `menu-only-center-blit` |
| `gameplay-menu640-centered-map12-nonexclusive` | input diagnostic | 9 | 98 | `menu-only-center-blit`, `mouse-nonexclusive-coop` |
| `gameplay-menu640-centered-map12-absinput` | input diagnostic | 9 | 98 | `menu-only-center-blit`, `mouse-absolute-assign` |
| `gameplay-menu640-centered-map12-absnonexclusive` | input diagnostic | 10 | 99 | `menu-only-center-blit`, `mouse-nonexclusive-coop`, `mouse-absolute-assign` |
| `gameplay-menu640-centered-map12-absformat` | input diagnostic | 11 | 100 | `menu-only-center-blit`, `mouse-absolute-format`, `mouse-nonexclusive-coop`, `mouse-absolute-assign` |
| `gameplay-menu640-centered-map12-hybridmouse` | input diagnostic | 10 | 100 | `menu-only-center-blit`, `mouse-nonexclusive-coop`, `mouse-hybrid-input` |
| `gameplay-menu640-centered-map12-deltaclamp` | input diagnostic | 9 | 99 | `menu-only-center-blit`, `mouse-delta-clamp` |
| `gameplay-menu640-centered-map12-absquarter` | input diagnostic | 9 | 98 | `menu-only-center-blit`, `mouse-absolute-quarter` |
| `gameplay-menu640-centered-map12-screenorigin` | input diagnostic | 9 | 99 | `menu-only-center-blit`, `mouse-screenorigin-diagnostic` |
| `gameplay-menu640-centered-map12-dynorigin` | diagnostic | 9 | 99 | `menu-only-center-blit` |
| `gameplay-menu640-centered-map12-dynorigin-sharedscratch` | diagnostic | 10 | 101 | `menu-only-center-blit` |
| `gameplay-menu640-centered-map12-dynorigin-menusurface` | legacy diagnostic | 11 | 103 | `menu-surface`, `menu-only-center-blit` |
| `gameplay-menu640-centered-map12-dynorigin-menusurface-scrollclamp` | legacy diagnostic | 12 | 105 | `menu-surface`, `menu-only-center-blit`, `saved-scroll-clamp` |
| `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp` | diagnostic | 12 | 107 | stable precursor |
| `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds` | diagnostic | 13 | 113 | stable precursor |
| `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapclip` | diagnostic | 14 | 115 | stable precursor |
| `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright` | diagnostic | 15 | 116 | stable precursor |
| `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-vswitch` | diagnostic | 16 | 118 | `viewport-switch` precursor |
| `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch` | stable | 16 | 118 | stable core |
| `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-rightbottomcompose` | validation | 17 | 122 | `right-bottom-compose-proof` |
| `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-castlecenter` | validation | 17 | 120 | `castle-ui-center-present` |
| `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-castlecenter-hitbox` | validation | 18 | 128 | `castle-ui-center-present`, `castle-ui-centered-input` |
| `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-castlecenter-all` | validation | 20 | 134 | `castle-ui-center-present-wrapper`, `castle-ui-centered-input`, `castle-overview-center-present-wrapper`, `castle-overview-centered-input` |
| `gameplay-menu640-centered-map12-hybridmouse-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch` | input diagnostic | 17 | 119 | `mouse-nonexclusive-coop`, `mouse-hybrid-input` |
| `gameplay-menu640-absinput` | input diagnostic | 6 | 25 | `mouse-absolute-assign` |
| `gameplay-menu640-centered-visual-absinput` | input diagnostic | 7 | 26 | `menu-only-center-blit`, `mouse-absolute-assign` |
| `gameplay-menu640-centered-mousefix` | diagnostic | 8 | 69 | `menu-only-center-blit`, `mouse-relative-format` |
| `gameplay-menu640-centered-nonexclusive` | input diagnostic | 8 | 66 | `menu-only-center-blit`, `mouse-nonexclusive-coop` |
| `gameplay-menu640-centered-absinput` | input diagnostic | 8 | 66 | `menu-only-center-blit`, `mouse-absolute-assign` |
| `gameplay` | diagnostic | 6 | 26 | `viewport-switch` |
| `gameplay-helpers` | diagnostic | 7 | 58 | `viewport-switch` |
| `core` | diagnostic | 7 | 16 | `menu-surface`, `viewport-switch` |
| `draw` | diagnostic | 8 | 30 | `menu-surface`, `viewport-switch` |
| `helpers` | diagnostic | 9 | 62 | `menu-surface`, `viewport-switch` |

## Patch Group Table

| Group | Category | Patches | Stage membership count |
|---|---|---:|---:|
| `castle-overview-center-present-wrapper` | validation-only | 3 | 1 |
| `castle-overview-centered-input` | validation-only | 2 | 1 |
| `castle-ui-center-present` | validation-only | 2 | 2 |
| `castle-ui-center-present-wrapper` | validation-only | 3 | 1 |
| `castle-ui-centered-input` | validation-only | 8 | 2 |
| `center-blit` | diagnostic/legacy | 2 | 0 |
| `display` | stable core | 4 | 48 |
| `full-redraw-12x9` | stable core | 3 | 11 |
| `full-redraw-present-bounds-800` | stable core | 6 | 10 |
| `gameplay-surface` | stable core | 2 | 41 |
| `helpers` | stable core | 32 | 27 |
| `input-bounds` | stable core | 2 | 42 |
| `main-loops` | stable core | 14 | 39 |
| `map-surface-upgrade-scrollclamp` | stable core | 2 | 11 |
| `menu-center-hitboxes` | stable core | 40 | 30 |
| `menu-only-center-blit` | diagnostic/legacy | 1 | 22 |
| `menu-only-center-blit-640only` | diagnostic/legacy | 2 | 0 |
| `menu-surface` | diagnostic/legacy | 2 | 5 |
| `minimap-hd-right-anchor` | stable core | 1 | 8 |
| `minimap-right-clip` | stable core | 2 | 9 |
| `mouse-absolute-assign` | diagnostic/legacy | 1 | 14 |
| `mouse-absolute-format` | diagnostic/legacy | 1 | 1 |
| `mouse-absolute-quarter` | diagnostic/legacy | 1 | 1 |
| `mouse-delta-clamp` | diagnostic/legacy | 2 | 1 |
| `mouse-dynamic-origin` | stable core | 2 | 14 |
| `mouse-hybrid-input` | diagnostic/legacy | 2 | 2 |
| `mouse-nonexclusive-coop` | diagnostic/legacy | 1 | 6 |
| `mouse-relative-format` | diagnostic/legacy | 4 | 1 |
| `mouse-screenorigin-diagnostic` | diagnostic/legacy | 2 | 1 |
| `right-bottom-compose-proof` | validation-only | 4 | 1 |
| `saved-scroll-clamp` | diagnostic/legacy | 2 | 1 |
| `shared-surface` | stable core | 2 | 17 |
| `surface-blit-hd-aware` | stable core | 2 | 11 |
| `viewport-init` | stable core | 2 | 42 |
| `viewport-switch` | diagnostic/legacy | 2 | 7 |
| `viewport-switch-dynamic-surface` | stable core | 2 | 6 |

## Evidence Status

- Stable stage: PASS, current smoke candidate SHA `5E162FA81DF59533E0B99A0DCBC9EA24280DBEC46411AE871E968D6536C08B33`.
- Right-bottom compose: PASS as validation-only, promotion deferred.
- Castlecenter-all: PASS as validation-only on candidate SHA `1902213ADF825A7D7612A14C74AC5468BEBFCC4F00B43E60601FD8A832806DF6`. Current fixed hidden runs are `captures\archive\cdb-surface-dump-20260515-105041`, `captures\archive\cdb-surface-dump-20260515-105411`, `captures\archive\cdb-surface-dump-20260515-105458`, and `captures\archive\cdb-surface-dump-20260515-105557`; the full-overview wrapper now native-renders before HD center-copy, and the castle overview gate rejects the earlier stripey visual artifact.
- Manual DirectInput: pending; all five required target IDs still need approved visible/manual proof.
- Promotion override: inactive.
