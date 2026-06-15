# Current HD Map Evidence

- Updated: `2026-05-14`
- Scope: current 800x600 Clash95 HD map patch-stage evidence.
- Runtime policy: CDB-only evidence.
- Binary policy: generated executables stay outside the repository.

## Status

- HD map smoke matrix: PASS
- No-popup map evidence matrix: PASS, normal visibility and forced-visible
  baseline
- No-popup map evidence matrix tests: PASS, fixture coverage is included in
  the refresh
- Patch-stage byte gate: PASS, `118/118` selected current HD map bytes patched
- Post-owner visibility evidence: PASS
- Normal dark right/bottom cells: explained by visibility/fog state
- Forced-visible seven-cell proof: PASS, zero blank active cells
- Patch manifest comparison: available, no `original` / `unexpected` records
- Right-bottom owner/action route and action-box composition proof: PASS on
  hidden desktop
- Right-bottom debugger-side native-to-HD composition proof: PASS on hidden
  desktop, validation-only
- Right-bottom validation patch stage proof: PASS on hidden desktop,
  validation-only
- Right-bottom validation patch full-start owner/action route: PASS on hidden
  desktop, validation-only
- Right-bottom validation patch normal map gate: PASS on hidden desktop,
  validation-only
- Right-bottom validation patch natural UI probe: PASS on hidden desktop,
  validation-only
- Right-bottom validation patch controlled grid-hit proof: PASS on hidden
  desktop, validation-only
- Right-bottom validation patch promotion decision: PASS, defer stable
  promotion, `manual_input_proof_valid=False`
- Right-bottom validation evidence matrix: PASS, validation-stage only
- Right-bottom validation patch promotion decision tests: PASS, fixture
  coverage now rejects placeholder proof files and requires a valid manual
  proof manifest for manual promotion eligibility
- Right-bottom validation evidence matrix tests: PASS, fixture coverage is
  included in the refresh
- Right-bottom controlled grid-hit parser tests: PASS, fixture coverage is
  included in the refresh
- Castle overview evidence matrix: PASS, validation-stage only
- Castle owner records summary tests: PASS, fixture coverage is included in
  the refresh
- Castle overview evidence matrix tests: PASS, fixture coverage is included in
  the refresh
- Castle overview gate tests: PASS, fixture coverage is included in the refresh
- Castle overview hitbox summary tests: PASS, fixture coverage is included in
  the refresh
- Castle overview hitmap summary tests: PASS, fixture coverage is included in
  the refresh
- Castle overview multihit summary tests: PASS, fixture coverage is included
  in the refresh
- Castle overview baseline recheck: PASS, older visual baseline and barracks
  controlled-stop baseline still pass
- Castle overview baseline recheck tests: PASS, fixture coverage is included in
  the refresh
- Castle overview probe guard: PASS, focused descriptor-loop breakpoints remain
  covered and the old crashing overview input-wrapper marker is absent
- Castle overview probe guard tests: PASS, fixture coverage is included in the
  refresh
- Castle overview promotion decision: PASS, defer stable promotion,
  `manual_input_proof_valid=False`
- Castle overview promotion decision tests: PASS, fixture coverage now rejects
  placeholder proof files and requires a valid manual proof manifest for manual
  promotion eligibility
- Stable stage guard: PASS, validation-only groups absent from the default
  HD map stage and old `menu-surface` absent from `mapsurface` stages
- Stable stage guard tests: PASS, fixture coverage is included in the refresh
- Executable artifact guard: PASS, no repository `.exe` files present or
  tracked in the index
- Surface-dump policy guard: PASS, active-desktop fallback requires explicit
  `-AllowVisibleDesktop`
- Visible runtime launcher guard: PASS, legacy visible harnesses/helpers require
  `-AllowVisibleRuntime` before launching or touching visible-window input, and
  the root risky-call inventory has zero unclassified scripts
- Visible runtime launcher guard tests: PASS, fixture coverage proves missing
  switches, missing approval wording, gated foreground helpers, gated
  screen-capture helpers, guarded child-helper forwarding, unclassified risky
  scripts, documented exemptions, late guards, and CLI failures are caught
- Python runtime safety guard: PASS, risky Python helpers are classified as
  safe, test fixture, exempt, or manual/visible-runtime gated
- Python runtime safety guard tests: PASS, fixture coverage is included in the
  refresh
- Patch definition guard: PASS, stable/validation patch groups are statically
  checked without reading or building an executable
- Patch definition guard tests: PASS, fixture coverage catches default drift,
  validation leakage, unknown groups, and incompatible offset overlaps
- Capture corpus index: PASS, current capture references resolve while stale
  visible-era and sandbox-era artifacts remain non-promoting historical data
- Capture corpus index tests: PASS, fixture coverage is included in the refresh
- No-visible runtime guard: PASS, all referenced CDB surface-dump runs are
  hidden-desktop evidence
- No-visible runtime guard tests: PASS, fixture coverage is included in the
  refresh
- Process hygiene guard: PASS, no `cdb.exe` or `clash95*` process is running
- Process hygiene guard tests: PASS, fixture coverage is included in the
  refresh
- Manual DirectInput validation checklist: PASS, five remaining manual targets
  are enumerated, `manual_proof_valid=False`, the no-popup operator preference
  is recorded, and promotion remains blocked without a valid manual proof
  manifest or an explicit CDB-only override
- Manual DirectInput checklist tests: PASS, fixture coverage is included in the
  refresh for no-popup preference text, proof-manifest validation, and
  fail-closed behavior
- Manual DirectInput proof template: PASS, template JSON is intentionally not
  valid as proof until an approved manual run replaces every placeholder
- Manual DirectInput proof template tests: PASS, fixture coverage proves the
  template stays non-promoting and can become valid only after required proof
  fields are supplied
- Promotion override guard: PASS, current right-bottom, castle overview, and
  manual checklist evidence all keep CDB-only promotion overrides inactive
- Promotion override guard tests: PASS, fixture coverage proves unexpected
  override/manual-proof/promotion-ready states fail closed
- Promotion override manifest: PASS, no active override manifest is supplied in
  current evidence
- Promotion override manifest tests: PASS, fixture coverage requires explicit
  approval, scope, stage/SHA, risk, evidence refs, and stale-process proof
- No-popup boundary guard: PASS, all no-popup boundary reports are present in
  the refresh and linked from this evidence index
- No-popup guard regression tests: PASS, fixture coverage is included in the
  refresh and the failing surface-policy CLI output stays fixture-local
- Docs consistency guard: PASS, generated stable-stage/no-popup/manual-proof
  facts agree with the evidence index, handoff docs, README/progress notes, and
  wiki summaries
- Docs consistency guard tests: PASS, fixture coverage catches stale generated
  counts and stale promotion-boundary facts
- Handoff freshness guard: PASS, current handoff points at the route timing
  guard and the manual/visible DirectInput or explicit CDB-only promotion
  blocker, keeps the non-promoting manual proof template artifact visible,
  preserves the no-popup runtime preference, and requires the visible-runtime
  launcher approval guard
- Handoff freshness guard tests: PASS, fixture coverage is included in the
  refresh with `test_count=10`, including missing proof-template artifact,
  missing no-popup-preference cases, missing visible-launcher-guard cases, and
  stale legacy outside-debugger/visible-capture task cases

## Reports

- [Current repo-only evidence refresh](current-evidence-refresh-current.md)
- [No-popup map evidence matrix](no-popup-map-evidence-current.md)
- [No-popup map evidence matrix tests](no-popup-map-evidence-tests-current.md)
- [No-popup boundary guard](no-popup-boundary-guard-current.md)
- [No-popup guard regression tests](no-popup-guard-tests-current.md)
- [Visible runtime launcher guard](visible-runtime-launcher-guard-current.md)
- [Visible runtime launcher guard tests](visible-runtime-launcher-guard-tests-current.md)
- [Python runtime safety guard](python-runtime-safety-current.md)
- [Python runtime safety guard tests](python-runtime-safety-tests-current.md)
- [Patch definition guard](patch-definition-current.md)
- [Patch definition guard tests](patch-definition-tests-current.md)
- [Capture corpus index](capture-corpus-index-current.md)
- [Capture corpus index tests](capture-corpus-index-tests-current.md)
- [Handoff freshness guard](handoff-freshness-guard-current.md)
- [Handoff freshness guard tests](handoff-freshness-guard-tests-current.md)
- [No-visible runtime guard](no-visible-runtime-guard-current.md)
- [No-visible runtime guard tests](no-visible-runtime-guard-tests-current.md)
- [Process hygiene guard](process-hygiene-guard-current.md)
- [Process hygiene guard tests](process-hygiene-guard-tests-current.md)
- [Manual DirectInput validation checklist](manual-directinput-validation-checklist-current.md)
- [Manual DirectInput checklist tests](manual-directinput-validation-checklist-tests-current.md)
- [Manual DirectInput proof template](manual-directinput-proof-template-current.md)
- [Manual DirectInput proof template tests](manual-directinput-proof-template-tests-current.md)
- [Promotion override guard](promotion-override-guard-current.md)
- [Promotion override guard tests](promotion-override-guard-tests-current.md)
- [Promotion override manifest](promotion-override-manifest-current.md)
- [Promotion override manifest tests](promotion-override-manifest-tests-current.md)
- [Docs consistency guard](docs-consistency-current.md)
- [Docs consistency guard tests](docs-consistency-tests-current.md)
- [Surface-dump policy guard](surface-dump-policy-guard-current.md)
- [Executable artifact guard](exe-artifact-guard-current.md)
- [Stable stage guard](stable-stage-guard-current.md)
- [Stable stage guard tests](stable-stage-guard-tests-current.md)
- [Castle overview baseline recheck](castle-overview-baseline-recheck-current.md)
- [Castle overview baseline recheck tests](castle-overview-baseline-recheck-tests-current.md)
- [Castle overview probe guard](castle-overview-probe-guard-current.md)
- [Castle overview probe guard tests](castle-overview-probe-guard-tests-current.md)
- [Castle overview evidence matrix](castle-overview-evidence-current.md)
- [Castle owner records summary tests](castle-owner-records-summary-tests-current.md)
- [Castle overview evidence matrix tests](castle-overview-evidence-matrix-tests-current.md)
- [Castle overview gate tests](castle-overview-gate-tests-current.md)
- [Castle overview hitbox summary tests](castle-overview-hitbox-summary-tests-current.md)
- [Castle overview hitmap summary tests](castle-overview-hitmap-summary-tests-current.md)
- [Castle overview multihit summary tests](castle-overview-multihit-summary-tests-current.md)
- [Castle overview promotion decision](castle-overview-promotion-decision-current.md)
- [Castle overview promotion decision tests](castle-overview-promotion-decision-tests-current.md)
- [Right-bottom validation evidence matrix](right-bottom-compose-evidence-current.md)
- [Right-bottom validation patch promotion decision](right-bottom-compose-promotion-decision-current.md)
- [Right-bottom validation patch promotion decision tests](right-bottom-compose-promotion-decision-tests-current.md)
- [Right-bottom validation evidence matrix tests](right-bottom-compose-evidence-matrix-tests-current.md)
- [HD map smoke matrix](hd-map-smoke-current.md)
- [Post-owner evidence matrix](post-owner-evidence-current.md)
- [Patch manifest comparison, current vs partial12](patch-manifest-compare-current-vs-partial12.md)
- [Evidence index consistency check](hd-map-evidence-current-check.json)
- [Right-bottom owner/action route summary](cdb-surface-dump-20260513-112339/action-panel-route-summary.md)
- [Right-bottom action-box composition summary](cdb-surface-dump-20260513-112339/action-box-composition-summary.md)
- [Right-bottom owner/action route run summary](cdb-surface-dump-20260513-112339/RUN-SUMMARY.md)
- [Right-bottom debugger composition route summary](cdb-surface-dump-20260513-115303/action-panel-route-summary.md)
- [Right-bottom debugger composition summary](cdb-surface-dump-20260513-115303/action-box-compose-summary.md)
- [Right-bottom debugger composition run summary](cdb-surface-dump-20260513-115303/RUN-SUMMARY.md)
- [Right-bottom validation patch route summary](cdb-surface-dump-20260513-120712/action-panel-route-patch-summary.md)
- [Right-bottom validation patch composition summary](cdb-surface-dump-20260513-120712/action-box-compose-patch-summary.md)
- [Right-bottom validation patch run summary](cdb-surface-dump-20260513-120712/RUN-SUMMARY.md)
- [Right-bottom validation patch full-start route summary](cdb-surface-dump-20260513-122928/action-panel-route-fullstart-summary.md)
- [Right-bottom validation patch full-start composition summary](cdb-surface-dump-20260513-122928/action-box-compose-fullstart-summary.md)
- [Right-bottom validation patch full-start run summary](cdb-surface-dump-20260513-122928/RUN-SUMMARY.md)
- [Right-bottom validation patch normal map run summary](cdb-surface-dump-20260513-121513/RUN-SUMMARY.md)
- [Right-bottom validation patch normal map coverage](cdb-surface-dump-20260513-121513/map-tile-coverage.txt)
- [Right-bottom validation patch normal map visibility](cdb-surface-dump-20260513-121513/visibility-coverage.txt)
- [Right-bottom validation patch natural UI probe summary](cdb-surface-dump-20260513-122200/right-bottom-ui-summary.json)
- [Right-bottom validation patch natural UI run summary](cdb-surface-dump-20260513-122200/RUN-SUMMARY.md)
- [Right-bottom controlled grid-hit report](right-bottom-grid-hit-current.md)
- [Right-bottom controlled grid-hit parser tests](right-bottom-grid-hit-summary-tests-current.md)
- [Right-bottom controlled grid-hit probe guard](right-bottom-grid-hit-probe-guard-current.md)
- [Right-bottom controlled grid-hit probe guard tests](right-bottom-grid-hit-probe-guard-tests-current.md)
- [Right-bottom route timing guard](right-bottom-route-timing-guard-current.md)
- [Right-bottom route timing guard tests](right-bottom-route-timing-guard-tests-current.md)
- [Right-bottom controlled grid-hit run summary](cdb-surface-dump-20260514-140601/RUN-SUMMARY.md)
- [Right-bottom controlled grid-hit run parser summary](cdb-surface-dump-20260514-140601/right-bottom-grid-hit-summary.md)
- [Right-bottom validation patch byte manifest](patch-stage-right-bottom-compose-20260513.json)
- [Normal post-owner run summary](cdb-surface-dump-20260506-190037/RUN-SUMMARY.md)
- [Forced-visible post-owner run summary](cdb-surface-dump-20260506-201114/RUN-SUMMARY.md)

## Screenshot Artifacts

Normal post-owner visibility-zero surface:

![normal post-owner surface](<CLOUD_WORKTREE>/captures/archive/cdb-surface-dump-20260506-190037/surface.png)

Forced-visible post-owner surface:

![forced-visible post-owner surface](<CLOUD_WORKTREE>/captures/archive/cdb-surface-dump-20260506-201114/surface.png)

Right-bottom owner/action route surface:

![right-bottom owner route surface](<CLOUD_WORKTREE>/captures/archive/cdb-surface-dump-20260513-112339/surface.png)

Right-bottom debugger composition surface:

![right-bottom debugger composition surface](<CLOUD_WORKTREE>/captures/archive/cdb-surface-dump-20260513-115303/surface.png)

Right-bottom validation patch surface:

![right-bottom validation patch surface](<CLOUD_WORKTREE>/captures/archive/cdb-surface-dump-20260513-120712/surface.png)

Right-bottom validation patch full-start owner/action route surface:

![right-bottom validation patch full-start route surface](<CLOUD_WORKTREE>/captures/archive/cdb-surface-dump-20260513-122928/surface.png)

Right-bottom validation patch normal map surface:

![right-bottom validation patch normal map surface](<CLOUD_WORKTREE>/captures/archive/cdb-surface-dump-20260513-121513/surface.png)

Right-bottom validation patch natural UI surface:

![right-bottom validation patch natural UI surface](<CLOUD_WORKTREE>/captures/archive/cdb-surface-dump-20260513-122200/surface.png)

Right-bottom validation patch controlled grid-hit surface:

![right-bottom validation patch controlled grid-hit surface](<CLOUD_WORKTREE>/captures/archive/cdb-surface-dump-20260514-140601/surface.png)

## Key Evidence

- Candidate selected by the smoke matrix:
  `C:\ClashTests\cdb-post-owner-forced-visible\clash95_hd_surfdump_20260506_201114.exe`
- Candidate SHA-256:
  `5E162FA81DF59533E0B99A0DCBC9EA24280DBEC46411AE871E968D6536C08B33`
- Stage:
  `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch`
- No-popup map evidence matrix:
  `captures\current\no-popup-map-evidence-current.md`
- No-popup map evidence matrix tests:
  `captures\current\no-popup-map-evidence-tests-current.md`
- Normal evidence pair:
  `captures\archive\cdb-surface-dump-20260506-190037`
- Forced-visible evidence pair:
  `captures\archive\cdb-surface-dump-20260506-201114`
- Right-bottom owner/action route proof:
  `captures\archive\cdb-surface-dump-20260513-112339`
- Right-bottom debugger composition proof:
  `captures\archive\cdb-surface-dump-20260513-115303`
- Right-bottom validation patch proof:
  `captures\archive\cdb-surface-dump-20260513-120712`
- Right-bottom validation patch full-start owner/action route proof:
  `captures\archive\cdb-surface-dump-20260513-122928`
- Right-bottom validation patch normal map proof:
  `captures\archive\cdb-surface-dump-20260513-121513`
- Right-bottom validation patch natural UI proof:
  `captures\archive\cdb-surface-dump-20260513-122200`
- Right-bottom validation patch controlled grid-hit proof:
  `captures\archive\cdb-surface-dump-20260514-140601`
- Right-bottom validation patch promotion decision:
  `captures\current\right-bottom-compose-promotion-decision-current.md`
- Right-bottom validation evidence matrix:
  `captures\current\right-bottom-compose-evidence-current.md`
- Right-bottom validation patch controlled grid-hit report:
  `captures\current\right-bottom-grid-hit-current.md`
- Right-bottom validation patch controlled grid-hit probe guard:
  `captures\current\right-bottom-grid-hit-probe-guard-current.md`
- Right-bottom validation patch promotion decision tests:
  `captures\current\right-bottom-compose-promotion-decision-tests-current.md`
- Right-bottom validation evidence matrix tests:
  `captures\current\right-bottom-compose-evidence-matrix-tests-current.md`
- Right-bottom validation patch controlled grid-hit parser tests:
  `captures\current\right-bottom-grid-hit-summary-tests-current.md`
- Right-bottom validation patch controlled grid-hit probe guard tests:
  `captures\current\right-bottom-grid-hit-probe-guard-tests-current.md`
- Castle overview baseline recheck:
  `captures\current\castle-overview-baseline-recheck-current.md`
- Castle overview evidence matrix:
  `captures\current\castle-overview-evidence-current.md`
- Castle owner records summary tests:
  `captures\current\castle-owner-records-summary-tests-current.md`
- Castle overview evidence matrix tests:
  `captures\current\castle-overview-evidence-matrix-tests-current.md`
- Castle overview gate tests:
  `captures\current\castle-overview-gate-tests-current.md`
- Castle overview hitbox summary tests:
  `captures\current\castle-overview-hitbox-summary-tests-current.md`
- Castle overview hitmap summary tests:
  `captures\current\castle-overview-hitmap-summary-tests-current.md`
- Castle overview multihit summary tests:
  `captures\current\castle-overview-multihit-summary-tests-current.md`
- Castle overview promotion decision:
  `captures\current\castle-overview-promotion-decision-current.md`
- Castle overview promotion decision tests:
  `captures\current\castle-overview-promotion-decision-tests-current.md`
- Stable stage guard:
  `captures\current\stable-stage-guard-current.md`
- Executable artifact guard:
  `captures\current\exe-artifact-guard-current.md`
- Surface-dump policy guard:
  `captures\current\surface-dump-policy-guard-current.md`
- No-visible runtime guard:
  `captures\current\no-visible-runtime-guard-current.md`
- No-visible runtime guard tests:
  `captures\current\no-visible-runtime-guard-tests-current.md`
- Process hygiene guard:
  `captures\current\process-hygiene-guard-current.md`
- No-popup boundary guard:
  `captures\current\no-popup-boundary-guard-current.md`
- No-popup guard regression tests:
  `captures\current\no-popup-guard-tests-current.md`
- Right-bottom validation patch SHA-256:
  `EFE643F0511A85946AD752CD7AB516207722FDC8409E4529C3CE40660EA84756`
- Right-bottom validation patch stage:
  `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-rightbottomcompose`
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

Refresh the current repo-only evidence set:

```powershell
& '<USER_HOME>\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' tools\current_evidence_refresh.py `
  --require-pass
```

The refresh script updates the HD map smoke matrix, patch-manifest comparison,
the no-popup map evidence matrix, the no-popup map evidence matrix tests, this
evidence-index check, the barracks success-branch proof, the right-bottom UI
probe summary, the right-bottom owner/action route proof, the right-bottom
debugger composition proof, the right-bottom validation patch proof, the
right-bottom validation patch full-start owner/action route proof, the
right-bottom validation patch normal map gate, the right-bottom validation
patch natural UI probe, the right-bottom validation patch promotion decision,
the right-bottom validation evidence matrix, the right-bottom validation patch
controlled grid-hit proof, right-bottom validation patch promotion decision
tests, right-bottom validation evidence matrix tests, right-bottom controlled
grid-hit parser tests, the castle overview evidence matrix, castle owner
records summary tests, castle overview evidence matrix tests, the castle
overview promotion decision, castle overview gate tests, castle overview
hitbox summary tests, castle overview hitmap summary tests, castle overview
multihit summary tests, castle overview baseline recheck, castle overview
baseline recheck tests, castle overview probe guard, castle overview probe
guard tests, castle overview promotion decision tests, and the stable stage
guard plus stable stage guard tests. It also runs the executable artifact
guard, surface-dump policy guard, visible runtime launcher guard, visible
runtime launcher guard tests, no-visible runtime guard, no-visible runtime
guard tests, process hygiene guard, process hygiene guard tests, manual
DirectInput validation checklist, manual DirectInput checklist tests, manual
DirectInput proof template, manual DirectInput proof template tests, promotion
override guard, promotion override guard tests, handoff freshness guard,
handoff freshness guard tests, no-popup boundary guard, and no-popup guard
regression tests. It does not launch Clash95, CDB, wrappers, or any visible
window.

```powershell
& '<USER_HOME>\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' tools\hd_map_smoke_matrix.py `
  --require-pass `
  --write-json captures\current\hd-map-smoke-current.json `
  --write-markdown captures\current\hd-map-smoke-current.md
```

```powershell
& '<USER_HOME>\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' tools\patch_manifest_compare.py `
  captures\archive\patch-stage-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-20260424.json `
  captures\archive\patch-stage-mapdraw-partial12-20260424.json `
  --write-json captures\current\patch-manifest-compare-current-vs-partial12.json `
  --write-markdown captures\current\patch-manifest-compare-current-vs-partial12.md `
  --limit 8
```

```powershell
& '<USER_HOME>\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' tools\evidence_index_check.py `
  captures\current\hd-map-evidence-current.md `
  --require-pass `
  --write-json captures\current\hd-map-evidence-current-check.json
```

## Interpretation

The current HD map path draws the right/bottom cells when visibility permits it.
The normal black cells in this save are explained by fog/unexplored visibility,
not by a remaining 12x9 map loop, present-bounds, minimap, or action-panel
copyback defect.

The right-bottom owner/action proof is separate from the map-visibility gate:
`captures\archive\cdb-surface-dump-20260513-112339` uses a hidden-desktop CDB route
with map validation skipped to prove the current stage can reach the
action/status owner setup, draw cluster, action-box redirect, copyback, and
surface dump without an AV. The composition rows show the current action-box
text and copy rectangles are still native-positioned around `x=285..430` /
`y=349..450`, and no present row intersects the bottom tooltip or bottom-right
panel regions. The remaining visual issue is a native-anchor/composition
problem, not a failure to enter the route under this proof.

The follow-up debugger composition proof is also separate from the stable stage:
`captures\archive\cdb-surface-dump-20260513-115303` uses hidden-desktop CDB to
manually copy the native status rectangle `(401,288,593,357)` to `(586,528)`
and the native action-box rectangle `(285,350,450,425)` to `(285,524)` on the
800x600 surface. It passes with no AV rows and proves the native content can be
composed into the HD lower/right regions: `bottom_right_ui_corner` improves
from `21.43%` to `48.228%` nonblack, `r8c10` from `0.0%` to `54.102%`, and
`r8c11` from `0.0%` to `42.822%`. This is validation evidence for a narrow
future patch; it does not promote any right-bottom composition patch into the
stable HD map stage.

The validation patch proof turns that debugger-only composition into an
isolated patch group named `right-bottom-compose-proof`, still outside the
stable HD map stage. `captures\archive\cdb-surface-dump-20260513-120712` applies the
new validation stage through the hidden-desktop harness with `-SkipMapValidation`
and the existing owner/action extra probe. It passes the current HD map byte
gate plus all four right-bottom patch bytes/caves, reaches the same owner/action
route with `av_count=0`, and reproduces the same lower/right recovery:
`bottom_right_ui_corner=48.228%`, `r8c10=54.102%`, and `r8c11=42.822%`
nonblack. This proves the narrow patch shape, but the stable stage remains
`gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch`.

The full-start controlled owner/action route for the same validation patch is
`captures\archive\cdb-surface-dump-20260513-122928`. It uses the same patched SHA,
hidden desktop, `-UseDdrawProxy`, `-NoSkipStartAnims`, `-SkipMapValidation`,
and `probes/cdb/map/clash95_post_owner_action_extra.cdb`. It passes with `ready=True`,
`av_count=0`, `owner_rows=11`, `draw_rows=5`, `13` text rows, and the same
lower/right recovery: `bottom_right_ui_corner=48.228%`, `r8c10=54.102%`, and
`r8c11=42.822%` nonblack. This extends the route proof from fast-forwarded
startup to the full startup/resource path while keeping the stage
validation-only.

The normal-map safety run for that validation stage is
`captures\archive\cdb-surface-dump-20260513-121513`. It uses the same patched SHA,
hidden desktop, `-UseDdrawProxy`, full startup animation path
(`-NoSkipStartAnims`), and map validation enabled. The run passes with an
800x600 gameplay-like surface, `108` active cells, `13` blank active cells,
`VisibilityRequireExplained=True`, `VisibilityExplainedGate.Passed=True`,
`VisibilityUnexplainedBlankCells=[]`, and `status_counts.visibility_zero=13`.
This adds normal map/visibility safety for the validation patch, but still does
not promote it into the stable HD map stage.

The natural right-bottom UI probe for that validation stage is
`captures\archive\cdb-surface-dump-20260513-122200`. It runs the existing
`probes/cdb/ui/clash95_right_bottom_ui_extra.cdb` probe on the validation patch through the
hidden-desktop launcher. The run passes with the same patched SHA,
`RBUI_VIEWPORT_SWITCH=1`, `RBUI_DESC_SWITCH=35`, `SURFDUMP_PLAYGAME=1`,
`SURFDUMP_READY=1`, no owner/action draw rows (`RBUI_PANEL_DRAW=0`,
`RBUI_ACTION_BOX=0`), and no AV evidence. This preserves the earlier natural
route observation while proving the validation patch does not break the
descriptor/viewport probe path.

The controlled right-bottom grid-hit proof for that validation stage is
`captures\archive\cdb-surface-dump-20260514-140601`. It uses hidden desktop,
`-UseDdrawProxy`, `-FastForwardStartAnims`, `-SkipMapValidation`, and
`probes/cdb/ui/clash95_right_bottom_grid_hit_extra.cdb` to route into the owner/action grid
loop with the native coordinate `(450,73)`. The parser records
`grid_hit_ok=True`, `last_grid_entry=[450, 73]`, `last_grid_result=0`,
`forced_gate_count=1`, `failure_exit_count=0`, `draw_row_count=5`, and
`av_count=0`. This is controlled CDB/proxy hitbox evidence for the validation
stage; it is not manual DirectInput proof and does not promote the patch into
the stable HD map stage.

The right-bottom route timing guard is
`captures\current\right-bottom-route-timing-guard-current.md`. It passes repo-only and
checks the archived validation patch route, full-start owner/action route, and
controlled grid-hit route for hidden-desktop execution, 800x600 surfaces,
candidate SHA agreement, no AV/failure-exit rows, and stable marker ordering
through the owner/action draw, copyback, ready, and grid-hit sequences. This
turns the existing broader route/input/timing evidence into a no-popup guard,
but it remains CDB/proxy evidence rather than manual DirectInput proof.

The right-bottom validation patch promotion decision is
`captures\current\right-bottom-compose-promotion-decision-current.md`. It records
`decision=defer_stable_promotion` and `stable_stage_should_change=False`
despite all required right-bottom validation checks passing, because the proof
class is still repo-only CDB/proxy evidence, no manual/visible DirectInput proof
has been supplied, the route timing/order guard is still CDB/proxy evidence,
and the natural right-bottom UI probe still records `RBUI_PANEL_DRAW=0` and
`RBUI_ACTION_BOX=0`. The stable HD map stage therefore remains unchanged.

The compact right-bottom validation evidence matrix is
`captures\current\right-bottom-compose-evidence-current.md`. It collects the validation
patch proof, full-start controlled owner/action route, normal map gate, natural
UI probe, controlled grid-hit proof, route timing guard, and promotion decision
into one repo-only PASS record with `promotion_status=validation_stage_only`
and `stable_stage_should_change=False`.

The stable stage guard is `captures\current\stable-stage-guard-current.md`. It passes
repo-only, confirms the patcher default is still
`gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch`,
and reports no validation-only groups in the stable stage. It also checks that
`right-bottom-compose-proof` remains scoped to `rightbottomcompose`, while the
castle visual/input wrappers remain scoped to the castle validation stages, and
that the castle promotion decision plus evidence matrix still carry
focused/multihit proof. It now also checks 11 `mapsurface` stages, with zero
stages reintroducing the old global `menu-surface` group and zero stages
missing `map-surface-upgrade-scrollclamp`.

The executable artifact guard is `captures\current\exe-artifact-guard-current.md`. It
passes repo-only with `0` filesystem `.exe` files, `0` git-index `.exe` files,
and the root-level `.exe` ignore rule present. The staged `.exe` removals are
reported as allowed deletions.

The surface-dump policy guard is
`captures\current\surface-dump-policy-guard-current.md`. It passes repo-only and
checks that `scripts/cdb/scripts\cdb\run_cdb_surface_dump.ps1` defaults to `hidden-desktop`, refuses
implicit visible fallback after `CreateDesktop` failure, and only uses the
active desktop from the explicit `-AllowVisibleDesktop` branch. Future summary
paths now record both `HiddenDesktop` and `AllowVisibleDesktop`.

The visible runtime launcher guard is
`captures\current\visible-runtime-launcher-guard-current.md`. It passes repo-only,
checks 12 legacy visible launchers/helpers, and requires
`-AllowVisibleRuntime` before any risky `Start-Process`, window-focus, cursor,
SendInput, PostMessage, or `CopyFromScreen` call. Guarded child helpers must
receive the same switch. Its test report
`captures\current\visible-runtime-launcher-guard-tests-current.md` passes with
`test_count=10` and covers gated launchers, gated foreground helpers, gated
screen-capture helpers, guarded child-helper forwarding, missing switches,
missing approval wording, late guards, unclassified risky root scripts,
documented exemptions, and CLI fail-closed behavior. The guard inventory
reports `15` root PowerShell scripts
with risky runtime/window/input/capture calls, `12` guarded scripts, `3`
documented exemptions, and `0` unclassified scripts.

The no-popup map evidence matrix is
`captures\current\no-popup-map-evidence-current.md`. It passes repo-only by pairing
the stable normal visibility-explained run
`captures\archive\cdb-surface-dump-20260429-140916` with the stable forced-visible
edge proof `captures\archive\cdb-surface-dump-20260429-135242`, keeping the map
baseline visible in the one-command refresh.

The no-popup map evidence matrix tests are
`captures\current\no-popup-map-evidence-tests-current.md`. They pass repo-only and
cover explicit normal/forced inputs, latest passing-run selection, normal
visibility-gate regressions, forced-visible gate regressions, and CLI
`--require-pass` fail-closed behavior.

The no-visible runtime guard is
`captures\current\no-visible-runtime-guard-current.md`. It passes repo-only with `19`
referenced CDB surface-dump runs and `19` hidden-desktop runs. This makes the
current no-popup evidence policy explicit: any current evidence run that used
visible fallback would fail the refresh.

The no-visible runtime guard tests are
`captures\current\no-visible-runtime-guard-tests-current.md`. They pass repo-only and
cover hidden-desktop summaries, weak runtime policy text, visible runtime
summary regressions, missing run summaries, and CLI `--require-pass`
fail-closed behavior.

The process hygiene guard is `captures\current\process-hygiene-guard-current.md`. It
uses a Windows Toolhelp process snapshot, launches no game/debugger/window, and
passes with `0` matching `cdb.exe` or `clash95*` runtime processes. This catches
stale debugger/game processes before another evidence refresh is treated as
clean.

The promotion override guard is
`captures\current\promotion-override-guard-current.md`. It passes repo-only and verifies
that the current right-bottom compose promotion decision, castle overview
promotion decision, and manual DirectInput checklist all keep
`allow_cdb_only_promotion=False`, proof-valid flags false, and stable-stage
change flags false. The fixture tests in
`captures\current\promotion-override-guard-tests-current.md` cover unexpected override,
manual-proof, promotion-ready, missing-JSON, and CLI fail-closed cases.

The no-popup boundary guard is `captures\current\no-popup-boundary-guard-current.md`.
It passes repo-only and verifies that the current refresh includes the six
core boundary guards: stable stage, executable artifact, surface-dump policy,
visible-runtime launcher, no-visible runtime, and process hygiene. It records
`required_guard_count=6`, `required_supporting_report_count=44`, and
`required_report_count=50`. It also now
requires the no-popup map evidence matrix and its fixture tests, visible runtime
launcher guard tests, no-visible runtime guard fixture tests,
no-popup guard regression report, Python runtime safety guard and tests, patch
definition guard and tests, capture corpus index and tests, right-bottom validation
guard tests, manual DirectInput checklist and proof-template reports, promotion
override guard reports, promotion override manifest reports, docs consistency
guard reports, the right-bottom controlled grid-hit report, parser tests, probe
guard, probe guard tests, route timing guard, and route timing guard tests,
castle overview baseline recheck, castle overview baseline
recheck tests, castle owner records summary tests, castle overview evidence
matrix tests, castle overview gate tests, castle overview hitbox summary
tests, castle overview promotion decision tests, castle overview hitmap
summary tests, castle overview multihit summary tests, castle overview probe
guard plus its fixture-test report, and the stable stage guard fixture test
report as supporting reports, and checks that this evidence index links every
report.

The no-popup guard regression report is
`captures\current\no-popup-guard-tests-current.md`. It passes repo-only and records the
fixture tests that cover each missing evidence-index report link,
missing/failing core refresh checks, each missing supporting refresh check, and
surface-dump launcher policy drift.

The castle overview baseline recheck is
`captures\current\castle-overview-baseline-recheck-current.md`. It passes repo-only and
bundles the fixed full-overview visual baseline
`captures\archive\cdb-surface-dump-20260515-105041`, the barracks controlled-stop
baseline `captures\archive\cdb-surface-dump-20260512-082418`, and the latest
`castlecenter-all` evidence matrix with visible and dormant target-done
completion proof.

The castle overview baseline recheck tests are
`captures\current\castle-overview-baseline-recheck-tests-current.md`. They pass
repo-only and cover stale overview visual baselines, stale barracks
controlled-stop baselines, failing latest castle overview matrices, missing
visible/dormant target-done completion proof, and JSON/Markdown output writing.

The right-bottom compose promotion decision tests are
`captures\current\right-bottom-compose-promotion-decision-tests-current.md`. They pass
repo-only and cover the default defer decision, missing or failing
route/gate/grid/timing checks, valid manual-proof manifest promotion
eligibility, placeholder proof rejection, the explicit CDB-only override, and
the CLI JSON/Markdown output plus `--require-pass` fail-closed path.

The right-bottom compose evidence matrix tests are
`captures\current\right-bottom-compose-evidence-matrix-tests-current.md`. They pass
repo-only and cover all required route, map, UI, grid-hit, timing, and
promotion-decision gates, candidate SHA agreement, hidden-desktop and
full-start safety requirements, normal visibility proof, and the CLI
JSON/Markdown output plus `--require-pass` fail-closed path.

The right-bottom controlled grid-hit probe guard is
`captures\current\right-bottom-grid-hit-probe-guard-current.md`. It passes repo-only
and verifies that `probes/cdb/ui/clash95_right_bottom_grid_hit_extra.cdb` still carries the
focused owner/action/grid breakpoints, that the parser recognizes every probe
row, and that the archived hidden-desktop run proves native coordinate
`(450,73)` returns grid cell `0` on an 800x600 surface with zero failure-exit
or AV rows.

The right-bottom controlled grid-hit probe guard tests are
`captures\current\right-bottom-grid-hit-probe-guard-tests-current.md`. They pass
repo-only and cover missing breakpoints, missing probe/parser markers, visible
fallback, wrong stage/surface regressions, missing grid proof, failure-exit
rows, AV rows, and the CLI JSON/Markdown output plus `--require-pass`
fail-closed path.

The castle owner records summary tests are
`captures\current\castle-owner-records-summary-tests-current.md`. They pass repo-only
and cover active, retired, nonempty, interesting, and flag-value record
classification plus no-active, require-interesting, forbid-interesting, and
truncated raw-dump fail-closed paths.

The castle overview evidence matrix tests are
`captures\current\castle-overview-evidence-matrix-tests-current.md`. They pass
repo-only and cover the all-checks-pass aggregation path, every required
component-gate failure, required displayed-wrapper proof in the focused
command `0x86` hitbox gate, target-done completion proof in the
visible/dormant multi-hit gates, validation-stage-only status, and the CLI
JSON/Markdown output plus `--require-pass` fail-closed path.

The castle overview gate tests are
`captures\current\castle-overview-gate-tests-current.md`. They pass repo-only and
cover overview readiness, AV, post-draw, surface-size, expected-command, and
centered-geometry regressions, barracks baseline regressions, and the CLI
JSON/Markdown output plus `--require-pass` fail-closed path.

The castle overview hitbox summary tests are
`captures\current\castle-overview-hitbox-summary-tests-current.md`. They pass
repo-only and cover focused displayed/native hit rows, descriptor and
click-gate parsing, callback suppression and callback-entry handling, AV rows,
ready surface size, and the CLI required-flag fail-closed paths.

The castle overview hitmap summary tests are
`captures\current\castle-overview-hitmap-summary-tests-current.md`. They pass
repo-only and cover raw command IDs, presence/absence, counts, bounding boxes,
centered displayed coordinates, required present/absent CLI flags, and wrong
raw-dimension handling.

The castle overview multihit summary tests are
`captures\current\castle-overview-multihit-summary-tests-current.md`. They pass
repo-only and cover target-set rows, hit-test results, descriptor and
click-gate parsing, target-done completion rows, callback-entry handling, AV
rows, ready surface size, and the CLI required-flag fail-closed paths
including completion mismatch.

The castle overview probe guard is
`captures\current\castle-overview-probe-guard-current.md`. It passes repo-only and
verifies that `probes/cdb/castle/clash95_castle_overview_hitbox_extra.cdb` still carries the
focused descriptor-loop breakpoints at `00422544`, `0042257E`, `00422590`, and
`0042262C`, that the known bad `CASTLECAT_OVERVIEW_DESC_INPUT_WRAPPER_ENTRY`
path is absent, and that the focused hitbox log still proves the displayed
coordinate wrapper and click gate with zero AV rows.

The castle overview probe guard tests are
`captures\current\castle-overview-probe-guard-tests-current.md`. They pass repo-only
and cover the good focused-probe shape, each missing descriptor-loop
breakpoint, each missing required probe/parser marker, the old crashing
overview wrapper markers, AV rows in the focused hitbox log, missing focused
wrapper/gate proof rows, main/overview surface-size regressions, callback
entry, and the CLI JSON/Markdown output plus `--require-pass` fail-closed
path.

The castle overview promotion decision tests are
`captures\current\castle-overview-promotion-decision-tests-current.md`. They pass
repo-only and cover the default defer decision, a failing matrix fail-closed
path, missing focused/multihit proof, valid manual-proof manifest promotion
eligibility, placeholder proof rejection, the explicit CDB-only override, and
the CLI JSON/Markdown output plus `--require-pass` fail-closed path.

The stable stage guard tests are
`captures\current\stable-stage-guard-tests-current.md`. They pass repo-only and cover
patcher-default drift, validation-only group leakage into the stable stage,
missing `castlecenter-all` validation groups, `mapsurface` stages that
reintroduce global `menu-surface`, `mapsurface` stages missing the
gameplay-only map-surface upgrade, promotion decisions that would change the
stable stage, stale castle promotion decisions or evidence matrices without
required focused/multihit proof, and the CLI JSON/Markdown output plus
`--require-pass` fail-closed path.
