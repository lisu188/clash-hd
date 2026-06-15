# Clash95 HD Soak Test Roadmap

This roadmap moves HD validation from narrow route proofs toward endurance
evidence. It does not promote any validation-only patch group and does not
change the protected stable stage:

`gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch`

## Policy

- Soak runs are opt-in. The harness dry-runs by default and only launches the
  game with `-Execute -AllowVisibleRuntime`.
- Candidates are generated under `C:\ClashTests\...`.
- Raw frame artifacts are written outside the repo under `C:\ClashCaptures`.
- Repo output is limited to compact JSON/Markdown summaries in
  `captures/current`.
- The right-bottom action/menu lane remains non-promoting until real
  input-source or approved manual DirectInput proof replaces debugger-forced
  action-click proof.
- CDB-only and automated visible-runtime proof are diagnostic. They are not
  release-complete manual input proof.

## Harness

Dry-run the first short tier:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\smoke\run_hd_soak.ps1 `
  -Tier short2 `
  -Route menu-idle
```

Execute the first short tier only after approving visible runtime control:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\smoke\run_hd_soak.ps1 `
  -Tier short2 `
  -Route menu-idle `
  -Execute `
  -AllowVisibleRuntime `
  -RequirePass
```

Validate a generated report without launching the game:

```powershell
python tools\hd_soak_report.py captures\current\hd-soak-short-current.json --require-pass
```

## Short Tiers

| Tier | Duration | Initial routes | Promotion meaning |
| --- | ---: | --- | --- |
| `short2` | 2 min | `menu-idle`, then `map-idle` | Smoke endurance only. Does not promote. |
| `short10` | 10 min | `map-idle`, `map-pan` | Short stability trend. Does not promote. |
| `short30` | 30 min | `map-pan`, castle enter/exit when scripted | Pre-endurance screen/input trend. Does not promote. |

The first required milestone is one passing `short2` run on the protected
default stage. Longer tiers stay opt-in and should not enter default tests.

## Route Expansion

1. `menu-idle`: launch, skip startup, sample the main menu.
2. `map-idle`: load a representative save route and sample stable 800x600 map
   rendering.
3. `map-pan`: drive deterministic cursor movement across the map and sample
   input responsiveness plus frame stability.
4. Castle overview enter/exit: require centered input evidence and no modal
   desync.
5. Barracks/castle centered input: require enter/exit and click-path evidence.
6. Right-bottom action menu: run only when eligible and keep forced-coordinate
   rows diagnostic.
7. Tactical battle entry/return: require transition, battle UI, return, and
   post-return map health.
8. Save/load roundtrip: run only on safe test saves and verify continuity.
9. Turn advancement and campaign routes: add after short tiers show stable
   rendering and no input drift.

## Metrics

Each soak report must track:

- crash or AV class, exit code, and whether the harness stopped cleanly
- hang symptoms, frame sample count, and capture errors
- 800x600 frame size
- nonblack percent and nonblack bounds
- mean luminance
- unique sampled colors as a palette/artifact signal
- frame hash count and frame progression or stable-idle status
- route/input probe results
- working-set and handle growth when available
- artifact bytes and artifact root
- final route marker

A nonblack frame alone is not enough. A passing report needs process liveness,
clean stop, route/input evidence for the chosen route, and stable frame metrics.

## Failure Report

When a soak fails, the compact report should record:

- tier, route, stage, candidate SHA-256, and timestamp
- output directory under `C:\ClashCaptures`
- last route marker and last input probe row
- last frame hash, size, nonblack percent, mean luminance, and unique colors
- process state, exit code, working set, handle count, and clean-stop status
- crash, hang, capture, artifact-budget, or input-response classification
- next probe or harness refinement

## Release Horizon Checklist

Release completion needs all of these, not just a short soak:

- protected default stage remains unchanged until strict promotion evidence
  passes
- stable menu load with real input
- stable HD map input with no drift across long play
- castle overview centered input and enter/exit
- barracks/castle centered input and enter/exit
- right-bottom action/menu natural or approved manual DirectInput proof
- tactical battle entry, battle UI use, and return
- save/load roundtrip continuity on safe test saves
- turn advancement without state desync
- campaign-route progression without palette corruption
- 2h+ opt-in soak passes on representative routes
- no AVs, hangs, artifact buildup, handle growth trend, or memory growth trend
  outside the documented threshold
- no raw captures, binaries, saves, dumps, or local artifacts committed

## Current Status

Current evidence still shows the right-bottom action/menu lane as
non-promoting: v17b proves copyback only after a debugger-forced native action
click. The next short soak road must not mask that blocker. The first soak
milestone is a `short2` `menu-idle` run on the protected default stage, followed
by `map-idle` and `map-pan`.
