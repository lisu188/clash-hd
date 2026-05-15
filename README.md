# LLM Wiki

This repository is a markdown-first personal knowledge base inspired by Andrej
Karpathy's LLM Wiki pattern: the user curates source material, and an LLM
maintains a durable wiki that compounds over time.

The wiki is designed to work immediately in Obsidian or any markdown editor. No
database, vector index, web app, or external dependency is required.

## Repository Layout

```text
raw/
  inbox/       New user-added source files waiting for ingest
  processed/   Sources moved after explicit user approval
  assets/      User-provided images, PDFs, media, and attachments
wiki/
  index.md     Catalog of wiki content
  log.md       Append-only maintenance and ingest log
  overview.md  Starter guide for this wiki
  sources/     Source summary pages
  entities/    People, organizations, projects, places, works
  concepts/    Reusable ideas, methods, terms, patterns
  syntheses/   Cross-source synthesis pages
  questions/   Open questions and unresolved research threads
  comparisons/ Structured comparisons
meta/
  templates/   Page templates
  workflows/   Operating workflows
tools/
  wiki_search.py
  wiki_lint.py
AGENTS.md      Durable instructions for Codex and future LLM agents
```

## Core Rules

- `raw/` is source-of-truth and user-owned.
- Agents must not edit raw sources.
- Moving files from `raw/inbox/` to `raw/processed/` requires explicit approval.
- `wiki/` is agent-maintained and should stay readable by humans.
- Every sourced wiki claim needs a citation.
- Contradictions are recorded; older claims are not silently overwritten.

## Add A Source

1. Put the source file in `raw/inbox/`.
2. Ask Codex to ingest it using the prompt at the end of this README.
3. Review the generated source summary and any linked entity, concept,
   synthesis, question, or comparison pages.
4. If the ingest looks good, explicitly tell Codex whether to move the raw file
   to `raw/processed/`.

## Ask Codex To Ingest A Source

Use a prompt like:

```text
Ingest raw/inbox/<file-name> into the LLM Wiki. Follow AGENTS.md. Create or
update source, entity, concept, synthesis, question, and comparison pages as
appropriate. Cite every sourced claim. Do not move or modify the raw source
unless I explicitly approve it after review. Run the linter when done.
```

## Query The Wiki

Ask natural questions, for example:

```text
Search the wiki for what we know about <topic>. Separate sourced facts,
interpretation, uncertainty, contradictions, and open questions. Cite the
relevant wiki/source pages.
```

Codex should search `wiki/`, read relevant pages, inspect cited raw sources only
when needed, and update the wiki when a durable insight or gap is found.

## Tools

Search markdown pages under `wiki/`:

```powershell
python tools/wiki_search.py wiki
python tools/wiki_search.py "your query here"
```

Lint wiki structure and links:

```powershell
python tools/wiki_lint.py
```

Both scripts use only the Python standard library.

If `python` is not on your `PATH`, run the same scripts with any Python 3
interpreter path, for example:

```powershell
& 'C:\Users\andrz\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' tools\wiki_lint.py
& 'C:\Users\andrz\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' tools\wiki_search.py wiki
```

Battle UI probe scaffolding is repo-only and safe to test without launching the
game:

```powershell
& 'C:\Users\andrz\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' tools\test_battle_ui_summary.py
& 'C:\Users\andrz\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' tools\test_battle_ui_gate.py
```

## Clash95 HD Map Smoke Reproduction

The HD mod workspace keeps generated executables outside the repository. Use a
fresh, user-owned `C:\Clash\clash95.exe` as input and write candidates under
`C:\ClashTests\...`. Never overwrite `C:\Clash\clash95.exe`, and do not commit
patched executables or game-derived dumps.

## Clash95 HD Release Packaging Boundary

This repository ships source scripts, documentation, and small evidence
manifests only. It does not ship the original game binary, patched `.exe`
files, wrapper DLL binaries, copied game assets, saves, memory dumps, CD/ISO
contents, cracks, or large raw captures. Users must provide their own
`C:\Clash\clash95.exe` and build candidates locally under `C:\ClashTests`.

Known-good input SHA-256:

```text
500055d77d03d514e8d3168506bd10f67cd8569bcc450604ff8192f46cdaf3ae
```

Current release status as of 2026-05-15:

- Stable HD map stage remains
  `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch`.
- `rightbottomcompose` and `castlecenter-all` are validation-only; they are not
  part of the stable default stage.
- Hidden/no-popup validation passes for the stable map path and refreshed
  castle overview evidence.
- Manual DirectInput proof is still pending, so the mod should not be described
  as fully release-complete until that manifest passes or an explicit CDB-only
  override manifest is approved.

Fresh validation and release reports are in:

- `reports\hd_completion_plan.md`
- `reports\patch_stage_inventory.md`
- `reports\final_hd_validation_matrix.md`
- `reports\final_hd_release_checklist.md`
- `reports\pr_body_complete_hd_mod_20260515.md`

To remove generated candidates, delete the relevant subdirectory under
`C:\ClashTests`. Do not delete or mutate `C:\Clash\clash95.exe`.

Start with the dry-run helper. It verifies the base SHA when
`C:\Clash\clash95.exe` is accessible, prints a unique candidate path, prints the
exact commands it would run, and refuses repository-local candidate output by
default:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\prepare_hd_map_smoke_candidate.ps1 -Json
```

When the plan looks right, run the same helper with `-Execute` from a normal
Windows shell:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\prepare_hd_map_smoke_candidate.ps1 -Execute
```

The manual equivalent is below.

Current HD map stage:

```powershell
$BundledPy = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
if (Get-Command python -ErrorAction SilentlyContinue) {
  $Py = (Get-Command python).Source
} elseif (Test-Path $BundledPy) {
  $Py = $BundledPy
} else {
  throw 'Python 3 was not found on PATH and the bundled Codex runtime was not found.'
}
$Stage = 'gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch'
```

Verify the base executable hash before patching:

```powershell
$Expected = '500055d77d03d514e8d3168506bd10f67cd8569bcc450604ff8192f46cdaf3ae'
$Actual = (Get-FileHash 'C:\Clash\clash95.exe' -Algorithm SHA256).Hash.ToLowerInvariant()
if ($Actual -ne $Expected) {
  throw "Unexpected C:\Clash\clash95.exe SHA-256: $Actual"
}
```

Build a uniquely named candidate outside the repo:

```powershell
$CandidateDir = 'C:\ClashTests\hd-map-smoke'
New-Item -ItemType Directory -Force -Path $CandidateDir | Out-Null
$Candidate = Join-Path $CandidateDir ('clash95_hd_smoke_{0}.exe' -f (Get-Date -Format 'yyyyMMdd_HHmmss'))
& $Py .\patch_clash95_hd.py `
  --input 'C:\Clash\clash95.exe' `
  --output $Candidate `
  --stage $Stage
```

Generate the patch-stage byte manifest. The JSON includes each selected patch's
file offset, RVA, VA, expected old bytes, expected new bytes, actual bytes,
status, group, and rationale note:

```powershell
& $Py .\tools\patch_stage_report.py `
  --exe $Candidate `
  --stage $Stage `
  --require-current-hd-map `
  --write-json .\captures\patch-stage-current-hd-map.json
```

Reproduce the current repo-only HD map smoke matrix with the existing normal and
forced-visible CDB surface-dump evidence:

```powershell
& $Py .\tools\hd_map_smoke_matrix.py `
  --patch-exe $Candidate `
  --stage $Stage `
  --normal-run .\captures\cdb-surface-dump-20260506-190037 `
  --forced-run .\captures\cdb-surface-dump-20260506-201114 `
  --require-pass `
  --write-json .\captures\hd-map-smoke-current.json `
  --write-markdown .\captures\hd-map-smoke-current.md
```

The current known-good matrix expects:

- `patch_stage.status = pass`
- `patch_stage.status_counts.patched = 118`
- `patch_stage.status_counts.original = 0`
- `patch_stage.status_counts.unexpected = 0`
- `post_owner_evidence.status = pass`

This smoke matrix does not launch the game or CDB. It proves that a freshly
generated candidate has the current HD map patch bytes and matches the archived
normal/forced-visible CDB evidence. To create new visual evidence, use the
hidden-desktop CDB surface-dump workflow documented in `AGENTS.md`.

Compare two patch-stage manifests without touching executables:

```powershell
& $Py .\tools\patch_manifest_compare.py `
  .\captures\patch-stage-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-20260424.json `
  .\captures\patch-stage-mapdraw-partial12-20260424.json `
  --write-json .\captures\patch-manifest-compare-current-vs-partial12.json `
  --write-markdown .\captures\patch-manifest-compare-current-vs-partial12.md
```

The comparer highlights changed offsets, groups, expected old/new bytes, actual
bytes, and `original` / `unexpected` statuses.

Open `captures/hd-map-evidence-current.md` for the compact current evidence
index. It links the smoke matrix, post-owner evidence matrix, patch-manifest
comparison, and the current screenshot artifacts.

Check that the evidence index links and screenshots still resolve:

```powershell
& $Py .\tools\evidence_index_check.py `
  .\captures\hd-map-evidence-current.md `
  --require-pass `
  --write-json .\captures\hd-map-evidence-current-check.json
```

Refresh the current repo-only evidence set, including the HD map smoke matrix,
no-popup map evidence matrix, no-popup map evidence matrix tests,
patch-manifest comparison, evidence-index check,
barracks success-branch proof,
right-bottom UI probe summary, right-bottom owner/action route proof,
right-bottom debugger composition proof, right-bottom validation patch proof,
right-bottom validation patch full-start route proof, right-bottom validation
patch normal map gate, right-bottom validation patch natural UI probe,
right-bottom validation patch promotion decision, right-bottom validation
evidence matrix, right-bottom validation patch promotion decision tests,
right-bottom validation evidence matrix tests, castle overview matrix,
castle overview promotion decision,
castle overview evidence matrix tests, castle overview promotion decision tests,
castle overview gate tests, castle overview baseline recheck,
castle owner records summary tests,
castle overview hitbox summary tests,
castle overview hitmap summary tests,
castle overview multihit summary tests,
castle overview baseline recheck tests, castle overview probe guard, castle
overview probe guard tests, stable stage
guard, stable stage guard tests, executable artifact guard, no-visible runtime
guard, no-visible runtime guard tests, and process hygiene guard. It also
checks the surface-dump launcher policy and the aggregate no-popup boundary,
then runs the no-popup guard regression tests:

```powershell
& $Py .\tools\current_evidence_refresh.py --require-pass
```

Current output is `captures\current-evidence-refresh-current.md`. It passes
without launching Clash95, CDB, wrappers, or a visible window. The current
no-popup map baseline is `captures\no-popup-map-evidence-current.md`, pairing
the stable normal visibility-explained run
`captures\cdb-surface-dump-20260429-140916` with the stable forced-visible
edge proof `captures\cdb-surface-dump-20260429-135242`.
Its fixture coverage is
`captures\no-popup-map-evidence-tests-current.md`, which passes repo-only with
`test_count=5` and covers explicit normal/forced inputs, latest passing-run
selection, normal visibility-gate regressions, forced-visible gate
regressions, and CLI `--require-pass` fail-closed behavior.

The current right-bottom owner/action route proof is
`captures\cdb-surface-dump-20260513-112339`, a hidden-desktop run with
`-SkipMapValidation` whose action-panel summary reaches the owner setup,
`004347A0`, `00434E20`, `00435280`, `00435500`, action-box redirect, copyback,
and `SURFDUMP_READY` with zero AV rows. Its action-box composition summary
records `13` filtered text rows, `5` null-destination present/copy rows, `2`
sample rows, and no present rows intersecting the bottom tooltip or bottom-right
panel regions, so the next right-bottom target is native anchor/final
composition behavior.

The current validation-only native-to-HD composition proof is
`captures\cdb-surface-dump-20260513-115303`. It is also hidden-desktop and
uses `-SkipMapValidation`; the extra probe manually copies the native status
rectangle to `(586,528)` and the native action-box rectangle to `(285,524)`.
The repo-only refresh records this as `right_bottom_compose_probe: PASS`:
`bottom_right_ui_corner` improves from `21.43%` to `48.228%` nonblack, while
previously black `r8c10` and `r8c11` recover to `54.102%` and `42.822%`.

The corresponding isolated validation patch stage is
`gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-rightbottomcompose`.
Its hidden-desktop proof is `captures\cdb-surface-dump-20260513-120712`, using
the existing owner/action extra probe rather than the debugger-side manual
composition probe. The byte manifest
`captures\patch-stage-right-bottom-compose-20260513.json` records `122/122`
selected bytes patched, including `4/4` in `right-bottom-compose-proof`, with
the current HD map gate still passing. The run SHA is
`EFE643F0511A85946AD752CD7AB516207722FDC8409E4529C3CE40660EA84756`; it stays
validation-only and is not part of the stable HD map stage.

The validation patch also passed a full-start controlled owner/action route at
`captures\cdb-surface-dump-20260513-122928` with `-NoSkipStartAnims`,
`-UseDdrawProxy`, `-SkipMapValidation`, and the existing owner/action extra
probe. That run keeps the same SHA, reports `ready=True` and `av_count=0`, and
reproduces the same lower/right recovery:
`bottom_right_ui_corner=48.228%`, `r8c10=54.102%`, and `r8c11=42.822%`.

The same validation stage also passed a normal hidden map-validation run at
`captures\cdb-surface-dump-20260513-121513` with `-NoSkipStartAnims`,
`-UseDdrawProxy`, and no `-SkipMapValidation`. It produced an 800x600
gameplay-like surface with `108` active cells; all `13` blank active cells were
explained as `visibility_zero`, with zero unexplained blanks.

It also passed the natural right-bottom UI launcher at
`captures\cdb-surface-dump-20260513-122200`. That run keeps the existing
descriptor/viewport evidence intact on the validation stage
(`RBUI_DESC_SWITCH=35`, `RBUI_VIEWPORT_SWITCH=1`) without naturally entering
the owner/action draw rows (`RBUI_PANEL_DRAW=0`, `RBUI_ACTION_BOX=0`).
Treat this as proof that a narrow final-composition patch is viable, not as a
stable-stage promotion.

The current explicit right-bottom promotion decision is
`captures\right-bottom-compose-promotion-decision-current.md`. It passes as a
decision record with `decision=defer_stable_promotion` and
`stable_stage_should_change=False`, because the validation evidence is still
repo-only CDB/proxy evidence, no manual/visible DirectInput proof has been
supplied, and the natural UI probe still does not enter the owner/action draw
rows.

The compact right-bottom validation matrix is
`captures\right-bottom-compose-evidence-current.md`. It passes repo-only with
`promotion_status=validation_stage_only`, `stable_stage_should_change=False`,
and the same validation-stage SHA
`EFE643F0511A85946AD752CD7AB516207722FDC8409E4529C3CE40660EA84756`.

The right-bottom validation guard tests are
`captures\right-bottom-compose-promotion-decision-tests-current.md` and
`captures\right-bottom-compose-evidence-matrix-tests-current.md`. Both pass
repo-only with `test_count=5`; they cover default defer behavior, missing or
failing route gates, manual-proof/CDB-override promotion eligibility, required
route/map/UI/decision gates, hidden-desktop and full-start safety, visibility
proof, candidate SHA agreement, and CLI `--require-pass` fail-closed behavior.

The castle overview baseline recheck is
`captures\castle-overview-baseline-recheck-current.md`. It passes repo-only,
runs the fixed full-overview visual baseline at
`captures\cdb-surface-dump-20260515-105041`, reruns the barracks controlled-stop
baseline at `captures\cdb-surface-dump-20260512-082418`, and
confirms the latest `castlecenter-all` matrix remains validation-only with
visible and dormant multi-hit target-done completion proof.

The castle overview baseline recheck tests are
`captures\castle-overview-baseline-recheck-tests-current.md`. They pass
repo-only and cover stale overview visual baselines, stale barracks
controlled-stop baselines, failing latest castle overview matrices, missing
visible/dormant target-done completion proof, and JSON/Markdown output writing.

The castle overview probe guard is
`captures\castle-overview-probe-guard-current.md`. It passes repo-only and
checks that `clash95_castle_overview_hitbox_extra.cdb` still covers the focused
descriptor-loop breakpoints `00422544`, `0042257E`, `00422590`, and `0042262C`,
that the old crashing `CASTLECAT_OVERVIEW_DESC_INPUT_WRAPPER_ENTRY` path has
not returned, and that the focused hitbox log still proves the displayed
coordinate click gate with zero AV rows.

The castle overview probe guard tests are
`captures\castle-overview-probe-guard-tests-current.md`. They pass repo-only
and cover the good focused-probe shape, each missing descriptor-loop
breakpoint, each missing required probe/parser marker, the old crashing
overview wrapper markers, AV rows in the focused hitbox log, missing focused
wrapper/gate proof rows, main/overview surface-size regressions, callback
entry, and the CLI JSON/Markdown output plus `--require-pass` fail-closed
path.

The stable stage guard is `captures\stable-stage-guard-current.md`. It passes
repo-only and confirms the patcher default remains the stable dynvswitch stage
with no validation-only groups included. It also checks that the right-bottom
composition group and castle visual/input groups remain scoped to their
validation stages, and that the castle overview promotion decision still
carries focused displayed-wrapper plus visible/dormant multi-hit proof. It
also checks the castle overview evidence matrix for the same proof bundle.

The stable stage guard tests are
`captures\stable-stage-guard-tests-current.md`. They pass repo-only and cover
patcher-default drift, validation-only group leakage into the stable stage,
missing `castlecenter-all` validation groups, promotion decisions that would
change the stable stage, stale castle promotion decisions or evidence matrices
without the required focused/multihit proof, and the CLI JSON/Markdown output plus
`--require-pass` fail-closed path.

The executable artifact guard is `captures\exe-artifact-guard-current.md`. It
passes repo-only with no `.exe` files present in the repository filesystem, no
`.exe` files tracked in the git index, and the root-level `.exe` ignore rule in
place. Staged root `.exe` removals are treated as allowed cleanup records.

The surface-dump policy guard is
`captures\surface-dump-policy-guard-current.md`. It passes repo-only and checks
that `run_cdb_surface_dump.ps1` defaults to hidden desktop, refuses implicit
visible fallback after `CreateDesktop` failure, and only uses active-desktop
launching inside the explicit `-AllowVisibleDesktop` branch.

The no-visible runtime guard is
`captures\no-visible-runtime-guard-current.md`. It passes repo-only and checks
that every referenced CDB surface-dump run in the current evidence set used
`LaunchMode=hidden-desktop` and `HiddenDesktop=True`, so visible-desktop
fallback cannot silently enter the current evidence refresh.
Its fixture coverage is
`captures\no-visible-runtime-guard-tests-current.md`, which passes repo-only
with `test_count=5` and covers hidden-desktop summaries, weak runtime policy
text, visible runtime summary regressions, missing run summaries, and CLI
`--require-pass` fail-closed behavior.

The process hygiene guard is `captures\process-hygiene-guard-current.md`. It
uses a Windows Toolhelp process snapshot, launches no game/debugger/window, and
passes with `0` matching `cdb.exe` or `clash95*` runtime processes, so stale
runtime processes cannot silently remain after a refresh.

The no-popup boundary guard is
`captures\no-popup-boundary-guard-current.md`. It passes repo-only and verifies
that the refresh includes the stable-stage, executable-artifact,
surface-dump-policy, no-visible-runtime, and process-hygiene guards. It also
requires the no-popup map evidence matrix and its fixture tests, no-popup guard
regression report, no-visible runtime guard tests,
right-bottom validation guard tests, castle overview baseline
recheck, castle overview baseline recheck tests, castle overview evidence
matrix tests, castle overview gate tests, castle overview promotion decision
tests, castle owner records summary tests, castle overview hitbox summary
tests, castle overview probe guard, castle overview hitmap summary tests,
castle overview multihit summary tests, castle overview probe guard tests,
and stable stage guard tests as supporting
reports, and verifies that the evidence index links every report.

The no-popup guard regression tests are repo-only:

```powershell
& $Py .\tools\test_no_popup_guards.py
```

They cover each missing boundary report link, missing/failed core refresh
checks, each missing supporting refresh check, and surface-dump launcher policy
drift. The failing surface-dump policy CLI fixture writes only under
`.codex-loop\tmp-tests\no-popup-guards-fixture`, keeping the current
`captures\surface-dump-policy-guard-current.md/json` reports reserved for live
refresh output. The current refresh report is
`captures\no-popup-guard-tests-current.md`.

Current castle/interior validation keeps the stable HD map stage unchanged and
uses this broader stage only for castle-screen evidence:

```powershell
$CastleStage = 'gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-castlecenter-all'
```

The current compact no-popup matrix is repo-only and does not launch Clash95,
CDB, wrappers, or a visible window:

```powershell
& $Py .\tools\castle_overview_evidence_matrix.py `
  --write-json .\captures\castle-overview-evidence-current.json `
  --write-markdown .\captures\castle-overview-evidence-current.md `
  --require-pass
```

Current output is `captures\castle-overview-evidence-current.md`. It passes
with `134` patched bytes, `0` original bytes, `0` unexpected bytes, centered
overview geometry, focused command `0x86`, visible commands `0x86`, `0x63`,
`0x87`, forced dormant commands `0x99`, `0x9C`, `0x9F`, `0xA6`, and the
barracks no-echo baseline. Its status is still `validation_stage_only`; it is
not a stable HD map-stage promotion.

The castle overview evidence matrix tests are
`captures\castle-overview-evidence-matrix-tests-current.md`. They pass
repo-only and cover all-checks-pass aggregation, every required component-gate
failure, required displayed-wrapper proof in the focused command `0x86`
hitbox gate, target-done completion proof in the visible/dormant multi-hit
gates, validation-stage-only status, and JSON/Markdown CLI output with
`--require-pass` failure.

The castle owner records summary tests are
`captures\castle-owner-records-summary-tests-current.md`. They pass repo-only
and cover active, retired, nonempty, interesting, and flag-value record
classification plus no-active, require-interesting, forbid-interesting, and
truncated raw-dump fail-closed paths.

The castle overview gate tests are
`captures\castle-overview-gate-tests-current.md`. They pass repo-only and
cover overview readiness, AV rows, overview post-draw/surface size, expected
commands, centered geometry, barracks baseline regressions, and JSON/Markdown
CLI output with `--require-pass` failure.

The castle overview hitbox summary tests are
`captures\castle-overview-hitbox-summary-tests-current.md`. They pass
repo-only and cover focused displayed/native hit parsing, descriptor and
click-gate parsing, callback suppression/callback entry, AV rows, ready size,
and required CLI flag failures.

The castle overview hitmap summary tests are
`captures\castle-overview-hitmap-summary-tests-current.md`. They pass
repo-only and cover raw command IDs, presence/absence, counts, bounding boxes,
centered displayed coordinates, required present/absent CLI flags, and wrong
raw-dimension handling.

The castle overview multihit summary tests are
`captures\castle-overview-multihit-summary-tests-current.md`. They pass
repo-only and cover target-set rows, hit-test results, descriptor and
click-gate parsing, target-done completion rows, callback entry, AV rows,
ready size, and required CLI flag failures including completion mismatch.

The current explicit promotion decision is also repo-only:

```powershell
& $Py .\tools\castle_overview_promotion_decision.py `
  --write-json .\captures\castle-overview-promotion-decision-current.json `
  --write-markdown .\captures\castle-overview-promotion-decision-current.md `
  --require-pass
```

Current output is
`captures\castle-overview-promotion-decision-current.md`. It records
`decision=defer_stable_promotion` and `stable_stage_should_change=False`.
It also records the focused displayed-wrapper proof, visible target completion
proof, and dormant target completion proof before deferring promotion. Reason:
the evidence matrix passes, but the current proof is CDB/proxy-only and
manual/visible DirectInput validation has not been supplied. The default stable
HD map stage stays
`gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch`;
castle overview wrappers stay scoped to `castlecenter-all`.

The castle overview promotion decision tests are
`captures\castle-overview-promotion-decision-tests-current.md`. They pass
repo-only and cover the default defer decision, the failing-matrix
fail-closed path, missing focused/multihit proof, manual-proof promotion
eligibility, explicit CDB-only override promotion eligibility, and
JSON/Markdown CLI output with `--require-pass` failure.

The stable stage guard can be refreshed directly with:

```powershell
& $Py .\tools\stable_stage_guard.py --require-pass
```

After a full castle overview CDB surface-dump run, gate it with:

```powershell
& $Py .\tools\castle_overview_gate.py `
  .\captures\cdb-surface-dump-YYYYMMDD-HHMMSS `
  --barracks-run .\captures\cdb-surface-dump-20260512-082418 `
  --require-pass `
  --write-json .\captures\castle-overview-gate-current.json `
  --write-markdown .\captures\castle-overview-gate-current.md
```

That gate intentionally requires the descriptor catalog, no AV rows, an 800x600
surface, centered 800x600 geometry, and the optional barracks no-echo baseline
when `--barracks-run` is supplied. Current passing full-overview catalog and
visual-integrity evidence is `captures\cdb-surface-dump-20260515-105041`;
candidate SHA-256
`1902213ADF825A7D7612A14C74AC5468BEBFCC4F00B43E60601FD8A832806DF6`, with
`castle-overview-center-present-wrapper` `3/3` and
`castle-overview-centered-input` `2/2` patched. This evidence uses the
native-render-first overview wrapper and the stripe detector in
`tools\castle_overview_gate.py`.

The focused overview hitbox proof is
`captures\cdb-surface-dump-20260515-105411`, summarized by
`tools\castle_overview_hitbox_summary.py --require-displayed-hit`: displayed
coordinate `(371,107)` hits command `0x86` through the binary wrapper, the
stock click gate returns `1`, and no AV rows are present. Keep castle patches
out of the default HD map stage until broader or manual/real overview input
proof is added.

Current broader overview input evidence is
`captures\cdb-surface-dump-20260515-105458`, summarized by
`tools\castle_overview_multihit_summary.py --require-all-targets`. It proves
real hitmap coordinates for commands `0x86`, `0x63`, and `0x87` under the
centered wrapper. The companion hitmap dump
`captures\castle-overview-hitmap-current.md` shows `0xFA` through `0xFD` are
absent in the current overview surface, so commands `0x99`, `0x9C`, `0x9F`,
and `0xA6` remain catalog-only until a state exposes those hit IDs.

Dormant descriptor coverage is now documented separately. The owner-record dump
`captures\castle-owner-records-current.md` shows the current loaded castles have
zero feature flags, while the explicitly debugger-forced owner-feature run
`captures\cdb-surface-dump-20260513-095443` exposes all raw hit IDs
`0xF8` through `0xFF`. The follow-up multi-hit proof
`captures\cdb-surface-dump-20260515-105557`, summarized by
`captures\castle-overview-flags1f-multihit-current.md`, proves commands
`0x99`, `0x9C`, `0x9F`, and `0xA6` through real hitmap coordinates and stock
click gate `1` under the centered wrapper. This is still CDB/proxy evidence,
not manual DirectInput proof or stable-stage promotion.

## Use With Obsidian

Open this repository folder as an Obsidian vault. Obsidian will understand the
`[[wikilinks]]` used in `wiki/`. The repository intentionally avoids custom
plugins and generated app state. You may add an `.obsidian/` folder locally;
workspace/cache files are ignored by `.gitignore`.

## Current Limitations

- Search is simple keyword ranking, not semantic search.
- The linter is conservative and not a full markdown parser.
- No OCR, PDF extraction, vector search, database, or web app is included.
- Source ingest quality depends on the LLM reading the source carefully.
- Empty directories contain `.gitkeep` placeholders so the scaffold is visible
  to Git.

## First Source-Ingest Prompt

After dropping a file into `raw/inbox/`, use:

```text
Ingest raw/inbox/<file-name> into the LLM Wiki. Follow AGENTS.md exactly. Create
a source summary and any useful entity, concept, synthesis, question, or
comparison pages. Use Obsidian wikilinks. Cite every sourced claim with the raw
path or source page. Distinguish sourced facts, interpretation, uncertainty,
contradictions, and open questions. Append an entry to wiki/log.md. Run
python tools/wiki_lint.py. Do not move or modify the raw source until I approve.
```
