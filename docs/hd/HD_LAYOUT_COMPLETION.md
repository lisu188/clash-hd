# HD-layout completion evidence

`tools/hd_layout_completion_decision.py` is an additive, repo-only evaluator for
new layout evidence. It leaves the historical
`tools/hd_layout_promotion_decision.py` unchanged. The historical tool records
the July failed command click; its passing diagnostic is not affirmative input
proof. Existing battle callbacks are separate evidence and cannot satisfy this
new evaluator.

The new result can become `eligible_for_hd_layout_component_review` when every
required source passes. This sets `component_promotion_ready=true`, while
`promotion_ready`, `stable_stage_should_change`, and `full_game_complete` stay
false. The tool never applies patches or changes the protected default. An
explicit promotion decision, combined-stage interaction evidence, endurance,
continuity, and resolution-specific acceptance remain separate requirements.

No real passing command-input/composition proof is included by this change.
Missing evidence produces `defer_hd_layout_completion` and `passed=false`.
Fixtures use synthetic data in temporary directories and are not runtime proof.

## Safe invocation

From the repository root, use a discovered Python interpreter as described in
[AGENT_HANDOFF.md](AGENT_HANDOFF.md):

```powershell
& $clashPython -B tools/hd_layout_completion_decision.py --require-pass
& $clashPython -B tools/test_hd_layout_completion_decision.py
& $clashPython -B tools/test_hd_layout_asset_composition.py
```

The evaluator prints JSON and writes nothing by default. `--require-pass`
returns exit code 2 for deferred, missing, or invalid evidence. Optional
`--write-json` and `--write-markdown` explicitly select report destinations.
Neither evaluating evidence nor creating a dry-run plan authorizes runtime.
Visible execution, capture, and input still require fresh explicit user approval
under [the root guide](../../AGENTS.md).

## Approved visible session and native DPI

`tools/hd_layout_observation_manifest.py` and
`scripts/smoke/run_hd_layout_input_probe.ps1` default to file-only planning.
Execution requires the saved plan, an existing fresh approval bound to its
exact SHA and identity, and both explicit execution/visible-runtime switches.
The original executable, global display scale, registry compatibility settings,
and user configuration are not modified.

The approved action includes launching the exact local candidate through x86
CDB, displaying its wrapper window, human navigation/hover/click, capturing
the two stable pairs, and stopping the owned candidate and debugger. The
presenting proxy itself calls `ShowWindow` and `SetForegroundWindow` on its
first present (`src/ddraw_surfdump_proxy/ddraw_surfdump_proxy.cpp`); this window
activation belongs in the fresh approval. The observer does not inject mouse
input or automatically navigate. No saved plan or template constitutes approval.

The plan binds `launch_environment`: inherited compatibility layers and all
`CLASH_PROXY_` variables are removed case-insensitively, then the child receives
exactly `__COMPAT_LAYER=HIGHDPIAWARE` and, for the presenting proxy,
`CLASH_PROXY_PRESENT=1`. This environment is passed only to the owned CDB
process and inherited by its candidate child. The receipt records the exact
policy plus `effective_environment_sha256`; inherited environment values are
never written. That complete hash records execution provenance only, so an
unrelated Codex/host variable changing between planning and approved execution
does not invalidate approval. The explicit policy remains plan-bound.

On this host at 150% display scale, a temporary unmanifested x86 console helper
and its inherited child reported DPI awareness `0` without the override and
`2` with it, using both process and thread awareness APIs. The helper created
no windows and did not run the game or debugger. This is an environment check,
not game rendering or manual-input proof. Microsoft documents awareness `1`
as system-aware and `2` as per-monitor-aware; unaware applications can be bitmap
scaled. See [Microsoft's DPI awareness definitions](https://learn.microsoft.com/en-us/windows/win32/api/windef/ne-windef-dpi_awareness).

The observer verifies its own calling thread is per-monitor-aware. After the
owned child has created its window, it measures process and window awareness
and requires `1` or `2`; `0`, unknown values, and API failures stop the session.
It still requires an actual **800×600 physical client**, measured from the
observer's per-monitor-aware context, before capturing native pixels. This
does not assume that a compatibility label guarantees the resulting window
size. A system-aware window on a differently scaled monitor can fail that
physical gate and must not be moved or resized automatically to force a pass.
The receipt includes `candidate_dpi_awareness`, `window_dpi_awareness`, and
`physical_client_size`; each capture sidecar also records its measured
`WindowDpiAwareness`. Old plans missing this policy or binding earlier source
hashes must be regenerated and separately approved before execution.

## Required sources

| Argument | Evidence and independent validation |
| --- | --- |
| `--command-input-json` | Report from `hd_layout_command_input_summary.build_report(manifest_path)`. The evaluator verifies the source manifest hash, reruns that parser, and compares its identity, raw/probe/approval/receipt references, and ordered input/callback claims. |
| `--composition-json` | Same-run screen capture manifest described below. Geometry is recomputed from actual PNG pixels. |
| `--patch-json` | Complete `patch_stage_report.py` output for the exact command candidate/stage at `800x600`. The evaluator rereads the candidate and recomputes every selected byte record. |
| `--hidden-json` | `hd_layout_summary.py` output. Its raw log is reparsed, including all six panel anchors and the redraw-clip proof. |
| `--hidden-run-json` | The actual hidden run `summary.json`, binding the same log inside its recorded run directory, known original SHA, isolated candidate path/SHA, stage, hidden-desktop launch mode, and 800×600 software surface. |
| `--manual-proof` | Raw five-target proof accepted by `manual_directinput_checklist.py`, with exactly five unique IDs, per-target candidate paths/SHAs, and existing observation `artifacts`. Actual candidate bytes must match each target's declared stage and reconstruct the known original. |
| `--process-hygiene-json` | A successful process inspection covering `cdb.exe` and `clash95*`, with zero matches and a timestamp after this input run finished. |

Defaults use `captures/current/hd-layout-command-input-current.json`,
`hd-layout-composition-proof-current.json`, `patch-stage-hdlayout-current.json`,
`hd-layout-summary-current.json`, `manual-directinput-proof-current.json`, and
`process-hygiene-guard-current.json`. The default hidden run is the historical
`captures/archive/cdb-surface-dump-20260713-072428/summary.json`. These defaults
do not imply that the files are present or mutually eligible. Supply the exact
new candidate's reports explicitly, especially for combined UI validation.

Only registered validation stages containing `terrain-tooltip-bottom-center`,
`selected-unit-command-panel-right-bottom`, and `frame-restore-bands` qualify.
This includes `-hdlayout-framerestore` and `-combinedui-validation`; the older
frameless `-hdlayout` candidate is insufficient for component completion.
The current numeric geometry recipe supports only 800×600 logical output.
Candidate files must remain under `C:\ClashTests`; the original executable is
never modified. Undoing selected bytes **in memory** must reproduce the known
original SHA, so an unrelated modification outside patch offsets also fails.

The five manual targets keep their existing identities and stage requirements:
`stable_menu_load`, `stable_hd_map_input`, `right_bottom_validation_input`,
`castle_overview_centered_input`, and `castle_barracks_centered_input`.
They do not include the relocated layout command. The new ordered layout
observation is separately required and never automatically becomes manual
DirectInput proof. There is no CDB-only or automated-input override here.

## Same-run composition interface

The composition JSON has these required fields:

- `schema_version`: `1`.
- `evidence_class`: `approved_visible_automated_layout_composition`.
- `identity`: an exact copy of the command summary's identity, including run ID,
  candidate path/SHA, stage, `[800,600]` resolution, environment, input method,
  wrapper/input plan, `execution_plan_sha256`, measured HWND, and start/finish
  timestamps.
- `command_manifest` and `approval`: `{ "path": "...", "sha256": "..." }`
  references matching the command summary's actual source and approval record.
- `frames`: exactly `map` and `panel_hover`. Each contains two separately
  captured, ordered frame references. Each frame reference has `path`,
  `sha256`, and `sidecar`, where `sidecar` is another path/SHA reference.

All paths in this completion interface are absolute or repository-relative.
The command-input producer defines its own raw manifest reference resolution.

Each capture sidecar retains the capture helper's `Hash`, `Width`, `Height`,
`CaptureMode=screen`, `TargetHwnd`, `CenterWindowHwnd`, `CenterRootHwnd`, and
`CenterWindowMatchesTarget=true`. It additionally records these values measured
and bound by the producing session:

- `CaptureId`: a distinct identifier for this actual capture.
- `RunId`, `CandidateSha256`, and `Stage`: the exact input-run identity.
- `ClientSize`: `[800,600]`.
- `CapturedAt`: an ISO timestamp with timezone, inside that run's interval.
- `InputObservationBefore` and `InputObservationAfter`: each contains `line`,
  `prefix_bytes`, and `prefix_sha256`, identifying the latest passive native
  descriptor row in the exact complete raw-log prefix read around the capture.

The capture HWNDs must match the input session's measured HWND. PNG hashes,
sidecar hashes, actual dimensions, distinct capture paths/IDs, and chronological
timestamps are checked. The new asset check supports native 800×600 pixels and
exact 3:2 pixel replication in a raw 1200×900 capture. A filtered DPI capture
requires a separately validated sampling profile; it does not pass through a
colour tolerance. Numeric coordinates map onto original pixels, and no
resampled image artifact is written. Each pair must be pixel-stable and
non-suspect under `capture_tear_check.py`. That heuristic supports capture
interpretation; it cannot authenticate the human origin of observations.

The protocol keeps the **same selected unit** throughout both capture pairs:

1. On a map, hold the native cursor over empty traversable central terrain.
   Descriptor 0 must have state `2`, cursor metadata `005196C8`, and cursor
   sprite `3`. The terrain tooltip must satisfy the existing bottom-centred
   geometry and legacy-tooltip-absence checks.
2. Hover the first relocated icon, around logical `(640,544)`. Descriptor 0
   must have state `6`, cursor metadata `005196A0`, and cursor sprite `2`.
   Descriptor 3 stays in the same state (`1` or `2`) as the baseline.
3. Click once after both capture pairs finish. The ordered native gate and
   callback chain must follow the receipt's `click_observation_start_line`,
   which must follow all captures. The click begins in the recorded hover
   state with the same selected unit, cursor, and UI thread.

Each capture requires a fresh descriptor row afterward. Prefix hashes, raw
line ordering, and **every descriptor row between the before/after references**
are checked. The native cursor's logical position, draw position, sprite, and
metadata must remain consistent across that capture interval.

## Source-derived composition

The earlier `hd_layout_visible_summary.py` remains an unchanged historical
diagnostic. Its July 13 pair (`visual-smoke-20260713-075818`) shows descriptors
0/3 absent in `after-map-path.png` and present in
`after-hdlayout-panel-hover.png`. The no-click hover JSON records only Win32
cursor placement; it does not establish a native selection transition. Its
90% changed-area rule is unsuitable for a normal selected-map/hover sequence.

The original executable's `sub_40A360` (`0040A360`) writes descriptor-0 state
`1` when no unit is selected and `2` when a unit is selected. `sub_4191F0`
draws a base sprite in both states: bit `1` chooses descriptor field `+10h`,
otherwise it chooses `+14h`. Bit `4` additionally draws the `+18h` hover
sprite. Thus selecting a unit does not imply that an initially absent panel
will appear. `sub_409D80` is the map-mode callback and clears selection after
entry; the observer records that entry before the change.

The additive helper `tools/hd_layout_asset_composition.py` reads the approved
candidate workspace's `DATA/minimum.res` directly. The reference comes from
`session_receipt.plan.assets`; its path, length, SHA, and binding to the
approved execution-plan hash are independently checked. The supported archive
SHA is `86b43f5e01350d9d9dfbf02a91fd3f83809050474875c2f3c4e640519f437116`.
Loose `GFX/map_butt.s32`, `mouse.s32`, or `map.pal` overrides require separate
source validation. No extracted proprietary image or palette is tracked.

Native format references in the user-owned `C:\Clash\clash95.asm`:

- `004791A0`, `00478770`, and `004789F0`: LLRS header and directory traversal,
  including 26-byte name/flags/offset/length entries.
- `00405BC9` and `00406260`: S32's 1024-offset table and ten-byte sprite header.
  Indexed literal runs, transparent skips, and backward references to earlier
  literal runs are decoded in memory; references can cross sprite boundaries.
- `00401C40` and `00401B20`: `MAP.PAL` has an eight-byte header followed by
  256 RGB triples. The loader skips the header and reads those exact colours.
- `0040A400`: loads `MAP_BUTT.S32`. Descriptor 0 uses sprites `0/1`, descriptor
  3 uses `6/7`, and both specify hover sprite `14`.
- `00460490`, `00460D80`, and `00460EA0`: load `MOUSE.S32`, update cursor
  metadata/position, and draw the software cursor over the final surface.

The selected baseline contains sprite `1` at `(608,528)` and sprite `6` or `7`
at `(608,560)`. The hover frame adds sprite `14` over sprite `1`. Every expected
pixel is compared against the raw capture, including the recorded software
cursor where it covers an icon. Transparent runs preserve the base pixels;
they are not black fills or arbitrary exclusion masks. The same source sprites
must not remain at legacy anchors `(416,400)` and `(416,432)`.

The actual source archive was decoded read-only during implementation. Member
hashes are `511dd0aa848a8a7582139f7df9bd39ee87580c503dd9f731f3c4206f5206e620`
(`MAP_BUTT.S32`),
`62ca6363e0dd8bb1395afaa7287649be95da1ad006b1abc1dd3f1fb994749f68`
(`MOUSE.S32`), and
`a9a84ba3cddfdae1d376efe33ecb1c2091c1f274a2e36374fae1a08c2ae11414`
(`MAP.PAL`). This verifies the offline decoder's inputs, not a new runtime pass.
The hidden log still supplies the separate six-descriptor geometry proof.
Another resource variant, filtered capture profile, resolution, or UI state
requires separately justified acceptance; generic nonblack pixels do not pass.

Approval is recorded before execution against the exact planned run ID,
candidate path/SHA, stage, resolution, wrapper/configuration, input plan,
execution-plan hash, and expiry. It does not invent a future HWND. The
command-input producer then binds its measured process/window session receipt
to that plan, including candidate and debugger PIDs, parentage, image
path/hash, creation identity, HWND ownership, and verified cleanup. These
records must come from real approval and the actual owned runtime session;
this evaluator never creates either record and never repairs missing
provenance by copying another run's metadata. The initial producing session
supports manual DirectInput observations; automatic callback observation still
does not populate the separate five-target manual release proof.
