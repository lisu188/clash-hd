# Initial full map paint after UI initialization

Status, 2026-09-05: **implemented in a distinct validation stage; bounded
hidden validation passed at 800x600 and 1024x768**. The standalone x86 adapter and complete candidate builder
passed 11 adapter tests and 4 candidate integration tests. The adapter suite
executed 99 synthetic x86 invocations; it did not run the game or debugger.
Both new runs passed their loaded/status/initial-trace gates and exact
six-cell action-bar audits. Existing failed diagnostics remain failed. The original executable and
protected stable stage remain unchanged; this is not a full-mod completion or
promotion claim.

The opt-in stage is:

```text
gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-combinedui-partialtiles-initialpaint-validation
```

The existing [partial-tile implementation](PARTIAL_TILE_RENDERING.md) restores
the command bar after terrain and adds clipped partial cells. Its guarded full
redraw hooks need an eligible native full redraw after the ordinary map owner
and resources are ready. Merely waiting for the current `SURFDUMP_REDRAW`
counter does not establish that: the base probe emits that marker at `00406FA0`,
the update routine, rather than at native full redraw `00418700`.

## Source evidence and initialization order

The source audit used the user-owned `C:\Clash\clash95.asm` and the original
`C:\Clash\clash95.exe`, whose SHA-256 is
`500055d77d03d514e8d3168506bd10f67cd8569bcc450604ff8192f46cdaf3ae`.
These proprietary files remain external, read-only inputs.

Native `PlayGame` at `0040B660` performs three full redraws before the current
map-owner readiness join:

1. The direct call at `0040B798` returns to `0040B79D`.
2. The call to `sub_40A400` at `0040B7AE` loads `MAP_BUTT.S32`, stores its sprite
   set at `0052030C`, draws the command descriptors, and calls `00418700` again.
3. The direct call at `0040B7DC` returns to `0040B7E1`.

Only afterward does the block beginning at `0040B81C` install map render owner
`0040AD40` at global `005199D8`. Its tail falls through to `0040B88A`, which
loads the current player from `005202EC` and calls `UI_SetCurrentPlayer`
(`00423370`) at `0040B88F`, returning to `0040B894`.

`UI_SetCurrentPlayer` frees the old `INFO<n>.S32` object at `00527C24` and loads
the requested player's replacement. It does **not** create the command
descriptors or load `MAP_BUTT.S32`; that initialization happened earlier in
`sub_40A400`. Resource availability must be checked, not inferred from a
function name or return address.

Relevant assembly exports are `PlayGame` around lines 16914–17074,
`sub_40A400` around 15337–15361, and `UI_SetCurrentPlayer` around 54312–54361.
Line numbers are navigation aids; exact executable bytes are the contract.

## Implemented first-entry hook

Do not place an unconditional paint hook at the shared `0040B894` return.
After `nextPlayer`, native control jumps back to `0040B88A`; such a hook would
paint on every turn. The adapter intercepts the owner-installation tail
immediately before the shared join:

| Property | Verified original value |
| --- | --- |
| Hook VA | `0040B884` |
| Hook RVA | `0000B884` |
| File offset | `0000AC84` |
| Displaced length | 6 bytes |
| Old bytes | `BE D8 4C 54 00 5F` |
| Native instructions | `mov esi,00544CD8; pop edi` |
| Displaced HIGHLOW field | VA `0040B885`, RVA `0000B885` |
| Shared join preserved | `0040B88A` |
| Resume after initial UI call | `0040B894` |

Authenticate the complete adjacent 16-byte span `[0040B884,0040B894)`:

```text
BE D8 4C 54 00 5F A1 EC 02 52 00 E8 DC 7A 01 00
```

Its SHA-256 is
`2d2761525178e3d45a287ffcc84466c53a9a18258fd781f24746113e2371a6a4`.
The unchanged bytes at `0040B88A` load `005202EC`; the following relative call
targets `00423370`. HIGHLOW field `0040B88B` belongs to that shared load and
must remain in the original relocation table.

The six-byte installation is a relative jump plus one NOP to the additive RX
`.hdcode` section, whose code begins at `00562000`. The
[PE extension contract](PE_CODE_EXTENSION.md) reconstructs the exact combined
candidate, verifies each displaced byte and records every edit. The initial
hook is the fourth installed hook, alongside full convergence, full
presentation and incremental entry.

| Resolution | Initial hook destination | New bytes at `0040B884` | Complete code bytes | Declared absolute fields |
| --- | --- | --- | --- | --- |
| 800x600 | `005633B4` | `E9 2B 7B 15 00 90` | 5,106 | 122 |
| 1024x768 | `005635C1` | `E9 38 7D 15 00 90` | 5,631 | 122 |
| 1280x720 | `00563391` | `E9 08 7B 15 00 90` | 5,071 | 122 |
| 1280x960 | `005636B6` | `E9 2D 7E 15 00 90` | 5,876 | 122 |
| 1920x1080 | `0056385A` | `E9 D1 7F 15 00 90` | 6,296 | 122 |
| 802x602 | `00563512` | `E9 89 7C 15 00 90` | 5,456 | 122 |

The complete stage removes exactly three old HIGHLOW fields: RVAs `000187A2`
and `000187B8` for the existing full hooks, plus `0000B885` for this new hook.
The initial adapter adds seven absolute fields to the existing bundle's 115.
Its cloned `00544CD8` immediate and `005202EC` load receive new HIGHLOW records;
the original shared field at VA `0040B88B`, RVA `0000B88B`, remains intact.
Relative calls/jumps are separately declared and never loader HIGHLOW fixups.

## API and opt-in builder

[initial_map_paint.py](../../src/patcher/initial_map_paint.py) exposes:

```python
emit_hook_bundle(original, combined_candidate, *, base_va, width, height)
```

The returned `InitialMapPaintBundle` extends `partial_tile_hooks.HookBundle`.
It preserves the previous code prefix, entry addresses, relocations, three
hook sites and `status_vas`; it appends the admission helper and initial
trampoline, with a fourth `HookSite` named `initial_paint`. Each site records
file offset, VA/RVA, old bytes, destination, continuation and displaced HIGHLOW
fields. `initial_status_vas` separately identifies `ui_return`, `admission`,
`ready` and `paint_return`. `initial_contract` records native span hashes,
observer instruction spans and bytes, preceding call targets, preserved
shared-join relocation, tile counts and stack relationships.

The raw emitter retains `installation_ready=False`; the separate
[candidate builder](../../tools/build_partial_tile_candidate.py) performs the
authenticated installation. Its API is
`build_candidate(original, resolution, initial_paint=False)`. The CLI opts in
with `--initial-map-paint`; omitting it preserves the previous partial-tile
candidate bytes. `--preflight` builds only in memory and writes no artifacts,
even if output paths are supplied. Actual candidate output remains exclusive,
outside the repository under `C:\ClashTests`, and separate from the original.

## Adapter ABI and lifetime

The adapter executes this sequence:

1. Replay `mov esi,00544CD8; pop edi` exactly. The POP consumes the native saved
   EDI from the owner-installation block; it must not consume an adapter frame.
2. Execute the authenticated current-player load and call `00423370` exactly
   once, reproducing the original initial UI-resource transition.
3. After that call returns, save flags and all general registers. Preserve the
   **post-UI-call** state, including its EAX result and the resource handle in
   the surrounding native frame.
4. Preserve the exact render-device global at `00511230`, validate the state
   below, and call native `00418700` with EAX=1 to request drawing/presentation.
5. Restore `00511230`, registers, flags and stack on both the admitted and
   rejected paths, then resume at `0040B894`.

Native `00418700` sets the render-device global to the map surface and does not
restore the previous pointer. Register preservation alone is therefore
insufficient. The existing partial-tile helpers must also retain their map
vtable save/restore contract.

Only the first owner-installation path traverses `0040B884`. Later turns retain
the original `0040B88A` current-player call and bypass the adapter. The alternate
initialization branch through `0040B97D` rejoins the owner-installation block
before this site. No process-global or mutable “once” flag is needed. This is
once per `PlayGame` invocation, including a legitimate recursive invocation
when another game is loaded, rather than once per process.

## Admission and rendering limits

Before entering the native full-tile loop, require:

- A nonnull loaded INFO sprite set at `00527C24` and a successful existing
  composition guard: requested map dimensions/pixels/vtable, map owner,
  supported player, command descriptors or AI resources, lower/post owners,
  and supported tooltip state.
- A nonnull game-data pointer; actual map width and height in `1..100`.
- Tile callback exactly zero. Other callbacks are rejected by this initial
  admission, even if separately supported by the partial-tile helpers.
- Full-tile counts `TX=(W-32)//64`, `TY=(H-16)//64`, with map dimensions at least
  `TX`/`TY`, nonnegative scroll, and `scrollX+TX <= mapWidth`,
  `scrollY+TY <= mapHeight`.

The native full loop forms tile pointers before the installed convergence
hook. A later partial-cell guard cannot protect an invalid earlier full loop.
Smaller-world layouts are outside this narrow implementation and must not be
silently treated as complete.

For admitted state, retain the established order: native full terrain, partial
cells and their minimap intersections, command/AI composition, frame-band
restoration, then bounded presentation with tooltip/cursor handling. Do not
call the map-owner routine merely to obtain a redraw: that adds resource and
other UI work beyond the needed native `00418700` call. Modal and army-panel
support remain separate limitations.

Admission failure skips the additional paint while preserving the original
continuation and exposes raw status zero at the admission observer. Returning from
native `00418700` is not a success signal: its EAX result has no such contract.
The existing actual full-convergence/full-presentation pair must establish
success for this invocation. No pass is assumed here.

## Observation ABI

The new-stage readiness breakpoint uses the adapter's authenticated point
**after** UI initialization and **before** the additional paint. The old
`0040B88A` join remains untouched for subsequent turns. Readiness executes
`MOV EAX,1; CALL 00418700`, a ten-byte span authenticated in the loaded probe.
The admission marker records the actual helper status; zero is a rejection.
The `paint_return` observer is a distinct NOP immediately after the call, and
the rejected path skips it. The returned EAX is recorded without success
interpretation.

| Observer | 800x600 VA | 1024x768 VA | Bound instruction span |
| --- | --- | --- | --- |
| `ui_return` | `005633C4` | `005635D1` | 8 bytes: PUSHFD, PUSHAD, save render pointer |
| `admission` | `005633D1` | `005635DE` | 9 bytes: compare exact status 1, conditional reject |
| `ready` | `005633DA` | `005635E7` | 10 bytes: present flag 1, native full call |
| `paint_return` | `005633E4` | `005635F1` | 14 bytes: return-only NOP and complete restore/resume tail |

Let `S` be native ESP immediately after `UI_SetCurrentPlayer`. Admission,
readiness and paint return observe `S-40`: PUSHFD, PUSHAD and the saved render
pointer consume 40 bytes. The full call adds its return address, six saved
registers, 24 bytes of native locals, and the full hook's PUSHFD/PUSHAD frame.
Consequently **full-status ESP + 88 = readiness ESP** for this invocation.
The synthetic fixture executes the actual three-hook chain to check that
relationship. Incremental calls retain their independent normalization:
guard ESP +120, input/status ESP +36, and native no-op-exit ESP +28 refer to
the same incremental native entry.

The trace verifier requires admission, readiness, the matching exact-success
initial convergence/presentation pair and native return in order, on the same
thread and normalized frame. The initial pair requires callback zero and
ordinary player-zero context. A debugger event sequence retains repeated,
malformed and incomplete records as failures. Observation closes at a declared
complete update-call boundary before the host surface dump; the probe does not
manufacture rendering success. Later full redraws with native EBP=0 can omit
presentation, but their present intent is not logged here; an unpaired full
convergence therefore remains rejected rather than being silently forgiven.

## Completed offline verification and identities

Both suites passed on 2026-09-05:

- [11 adapter tests](../../tools/test_initial_map_paint.py), including 99
  synthetic x86 invocations at original and rebased addresses. They execute
  the actual emitted admission/trampoline, use destructive UI/guard/paint
  callees, verify post-UI flags/GPR/render state and stack canaries, reject
  unsafe map/scroll/resources/owners, and check initial-entry versus shared-turn
  behavior. Source bytes bind the alternate initial path; no game execution
  of that path is claimed.
- [4 candidate integration tests](../../tools/test_initial_map_candidate.py)
  reconstruct all six complete images in memory, verify four hook targets,
  all edit old/new bytes, the three removed and remaining HIGHLOW fields,
  additive RX section contents, positive and negative loader rebasing,
  loaded probe coverage and safe opt-in CLI preflight. The original remains
  unchanged and no candidate executable is written by these tests.

Frozen source/test checkpoint:

| File | SHA-256 |
| --- | --- |
| `src/patcher/initial_map_paint.py` | `a4dfce3dd267d109417a04f6d63f1d7dfc2e7e862525e8e7446748606f24955b` |
| `tools/test_initial_map_paint.py` | `00a302f9db039a71e89b9160d4ca5f17ab9b27f05b5e20e25750f5329bca56b6` |
| `tools/build_partial_tile_candidate.py` | `285b20813b6a05bfb373b41b86c4def3746abaf3ecb1065142d0f6c5e636408f` |
| `tools/test_initial_map_candidate.py` | `04ffa58b2a01697a38a8474de9f77a9fc1913628c7cd5e433692a51de86afdb9` |
| `src/patcher/partial_tile_clip.py` | `944119033895bd9e638a31e14a3c6c342e18efa28691679b97c831a989345c5a` |
| `src/patcher/partial_tile_hooks.py` | `a5953f662f8d663daa8eb4f7e6f7327a67a4bbd2d382f64fa0815fadefb403f6` |
| `src/patcher/pe_extension.py` | `efa974b294df3cdc7268788d6d17c2baf8c3575c4d388167f8939d96ae9a08ab` |

The new validation candidate identities are:

| Resolution | Candidate SHA-256 | Runtime evidence at this checkpoint |
| --- | --- | --- |
| 800x600 | `e72a57fd3bb26509179e0b4360fc9134bef804e152ac338fcd755cdfa41c548f` | Bounded hidden validation and 6/6 action-bar audit PASS |
| 1024x768 | `5ebbaf23ad999a97209a5e0ca8883e8d42e31190fb3891f03cfc3c38001bc338` | Bounded hidden validation and 6/6 action-bar audit PASS |

These identities describe the new initial-paint stage. They do not replace the
earlier [v2 800x600 rejection](../../captures/current/partialtiles-latearm-v2-800-failure-20260905-195041.json)
or the [v4b 800x600](../../captures/current/partialtiles-noop-v4-800-observation-current.json)
and [v4b 1024x768](../../captures/current/partialtiles-noop-v4-1024-observation-current.json)
failed runtime records. The v4b images' separate six-cell action-bar pixel
passes do not cure their trace-integrity failures or missing full-paint pairs.

## Bounded hidden runtime evidence

The [combined runtime observation](../../captures/current/initial-map-paint-runtime-current.json)
records both runs and their separate trace, image and cleanup claims.

The 800x600 run `cdb-surface-dump-20260905-210832` used the exact new candidate
above on a hidden desktop with the non-presenting memory proxy
(`ProxyPresentSetting=0`), slot 0, startup fast-forward and no forced visibility
edges. Its source-bound [action-bar audit](../../captures/current/initial-map-paint-800-action-bar-audit-current.json)
links the original summary, raw surface, PNG, palette and candidate hashes.
The external run directory is:

```text
C:/ClashCaptures/hd-completion/initialpaint-v1-800x600-20260905-190806/cdb-surface-dump-20260905-210832
```

`summary.json` SHA-256 is
`7862a8074612fa66e83713af1effb0f772c7cb1d73b10adc7532bac87446d51f`.
It records `Passed=true`, `PartialTileStatusGatePassed=true`,
`InitialMapPaintTrace.passed=true`, no AV and no timeout. One exact initial
convergence/presentation pair occurred between admission/readiness and return,
with the required 88-byte stack relationship. The event sequence contains 140
events: the five initial events, 49 incremental guards, 49 incremental
input/status events and 37 matched native no-op exits. Native return EAX was
`000002E0`; this value is recorded and is not the success criterion.

The trace closes at `00406FA0` before the paused host memory capture. The
800x600 raw surface contains 480,000 bytes; all 11 blank active cells in the
existing visibility gate are explained by visibility zero, with no unexplained
blank cells. The PNG/raw/palette binding and candidate file SHA are verified.
All six 64x32 action cells match their source sprites exactly at bottom-right
anchors `(608,528)` through `(736,560)`; this is an indexed software-surface
pixel claim, not visible-wrapper or manual-input proof.

The run's `terminal-process-receipt.json` records exit 0 and absence of the
recorded CDB PID 41588 and game PID 43528 at `2026-09-05T19:09:39.7553877Z`.
Its SHA-256 is
`7ed7977fdaf3a393ff102d8fab477e8c476bbe54c9f8be182a3545e77b7e6ab1`.

The 1024x768 run `cdb-surface-dump-20260905-211004` used the matching candidate
above with the same hidden/non-presenting launch class, slot and force settings.
Its [action-bar audit](../../captures/current/initial-map-paint-1024-action-bar-audit-current.json)
verifies every cell against source pixels, including the complete upper row
at Y=696 and lower row at Y=728, with X anchors 832, 896 and 960. The external
run directory is:

```text
C:/ClashCaptures/hd-completion/initialpaint-v1-1024x768-20260905-190806/cdb-surface-dump-20260905-211004
```

`summary.json` SHA-256 is
`ef3d95d113edae320d8eaddf55b371a9e45ae2c61d598a9815b95be9e774e70c`.
It records the same three passing gates, no AV or timeout, one initial full
pair and 140 events with the same 49 guard/input and 37 no-op counts. Native
return EAX was `000003A0`, again uninterpreted. The raw surface has 786,432
bytes; the visibility gate reports no unexplained blank cells, and the
PNG/raw/palette and candidate bindings pass.

Cleanup evidence is narrower for 1024x768. The process-identity query arrived
after this short run had finished: `live-process-receipt.json` records an empty
process list at `2026-09-05T19:10:43.3709246Z`. Exact candidate-path and matching
CDB-command absence were checked, but no live PIDs were captured. This must not
be described as a recorded-PID cleanup check equivalent to the 800x600 receipt.
The later `terminal-process-receipt.json` records exit 0, an empty matching
process list and `live_pids_recorded=false` at
`2026-09-05T19:12:32.5329812Z`; its SHA-256 is
`bf4b5bf4156fcbe8d683c9eccd55462b39a7e9bd34fca1e6175f00e63e9409cf`.

These bounded traces have no duplicated PTILE event sequence. They do not diagnose
or erase the older duplicate-output failures: repeated base-probe records
before the forced load remain a separate observation. Full and partial terrain
coverage across other scroll positions and world edges, modal/army composition,
broader HD completion, visible composition, manual input and stable promotion
remain separate work and evidence boundaries.
