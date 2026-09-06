# Framed minimap viewport outline

Implementation and six-resolution evidence: **2026-09-06**. All six optional
minimap candidates pass exact outline geometry/pixels, all four frame bands,
the footer and six action cells. **Runtime passes are limited to 800x600,
1024x768 and 802x602.** Both 1280 cases retain coverage failures; 1920x1080
retains a strict trace failure. The original stable stage and all earlier
candidate outcomes remain unchanged. The [runtime matrix](../../captures/current/framed-minimap-runtime-current.md)
and [hash-bound manifest](../../captures/current/framed-minimap-runtime-current.json)
keep these claims separate.

## Problem and installed revision

The user's mismatch comes from the active native `0040D560` path, which adds
9 to scroll X and 7 to scroll Y when constructing the viewport outline. That
9x7 window does not describe the larger framed gameplay viewport. Correct
minimap backing placement, frame artwork and action-bar pixels are separate
claims and cannot establish the outline dimensions.

[framed_minimap.py](../../src/patcher/framed_minimap.py) emits the guarded
replacement. [build_framed_candidate.py](../../tools/build_framed_candidate.py)
installs it only with `build_candidate(..., minimap_viewport=True)` or the
explicit CLI `--minimap-viewport`. The hidden surface harness requires
`-MinimapViewportValidation` together with its existing framed, partial-tile
and initial-paint flags. These are opt-in choices, not a new stable default.
The existing six default framed candidates retain their prior bytes.

The exact stage remains:

```text
gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-combinedui-partialtiles-initialpaint-framed-validation
```

Because this optional revision shares that validation-stage name, its candidate
SHA, `minimap_viewport=true`, revision
`framed_minimap_actual_terrain_v1`, source hashes and emitted contract must also
be bound. A stage string alone cannot identify the correction.

The active hook is **VA `0040D633`, RVA `D633`, file offset `CA33`**, after the
native minimap backing repair. It verifies displaced bytes `A1E4025200`,
replaces that complete instruction with the declared relative branch and
removes only its displaced HIGHLOW field at VA `0040D634` / RVA `D634`.
The successful/rejected HD route resumes at `0040D6C6`. A valid native
640x480 fallback replays the original `MOV EAX,[005202E4]` and resumes at
`0040D638`. The latent `0040D450` outline has no established current call or
pointer reference; it remains unchanged.

The callable helper preserves stack, flags, non-result registers and the
exact render-device pointer. Its hook preserves all entry registers. It
validates the known memory/explicit clipped vtable or a separate guarded
primary target, dimensions, world/scroll, native scale choice, enabled
minimap and backing identity. Native backing repair still precedes the hook;
these checks do not make arbitrary invalid object lifetimes safe. Memory
draws call `00404040`; primary draws use `00404560` with an already valid
backend pixel pointer and pitch. Status 1 means the native draw call returned,
status 2 selects native 640 fallback, and status 0 skips an invalid HD outline.
A returned status alone is not pixel proof.

## Geometry and native raster

The physical surface is `W x H`; framed terrain is `W-64` by `H-32` pixels.
Let `S` be measured minimap scale, `(mw,mh)` world size, `(sx,sy)` scroll and
`(Mx,My)` the minimap origin. Native scale is 4 for world area at most 2500,
otherwise 2. The backing dimensions are `(mw*S+14, mh*S+14)`, anchored at
exclusive right edge `W-32`, with `My=16`.

```text
L = Mx + 6 + sx*S
T = My + 6 + sy*S
R = L + 1 + ceil(min(W-64, (mw-sx)*64) * S / 64)
B = T + 1 + ceil(min(H-32, (mh-sy)*64) * S / 64)
```

This projects actual terrain pixels, including partial tiles, and excludes
out-of-world tails. Rounding the viewport to whole tiles first gives a
different result at some resolutions and is rejected by the fixtures.

Native `00404040` draws the top interior `L+1..R-1`, both sides from `T`
through `B-1`, then the inclusive bottom `L..R`. The combined result is the
inclusive rectangle's one-pixel perimeter, including every corner, at indexed
color **`4C`**. The audit compares those raw indices, not a guessed displayed
RGB color.

## First actual observation

The [immutable run plan](../../captures/current/framed-minimap-run-plan-20260906-031649.json)
binds the first optional candidate and both prepared main-probe hashes.
Run `cdb-surface-dump-20260906-051740` is under:

```text
C:/ClashCaptures/hd-completion/framed-minimap-v1-1024x768-20260906-031649/
```

Candidate SHA-256:

```text
69899e07f70dde2094264be694300e00c7a778f1391ac7797b74c59c56ee1ce0
```

The [bound viewport audit](../../captures/current/framed-minimap-v1-1024x768-viewport-20260906.json)
records:

| Observation | Actual result |
| --- | --- |
| World / scroll / scale | `100x100` / `(10,17)` / `2` |
| Minimap backing | Origin `(778,16)`, size `214x214` |
| Visible world pixels | `960x736` |
| Projected extent | `960*2/64 = 30`, `736*2/64 = 23` |
| Inclusive outline | `(804,56)..(835,80)` |
| Exact perimeter | **110/110 pixels `4C`, zero mismatches** |
| Observed draw calls | 64 memory draws; last memory draw at log line 294 |
| Paused binding | READY 624, visibility 625, viewport 638, minimap 639, closure 640 |
| Original runtime / initial trace | Both passed; retained as separate verdicts |

The separate [frame/action-bar audit](../../captures/current/framed-minimap-v1-1024x768-pixels-20260906.json)
also passes all four frame bands, the footer and six complete action cells for
this same candidate and capture. The minimap audit does not substitute for
those checks or assert process cleanup.

## Six-resolution results

The [additional immutable plan](../../captures/current/framed-minimap-run-plan-20260906-032002.json)
binds the other five candidates. All six captures use world 100x100, scroll
`(10,17)` and scale 2. Each has zero outline mismatches and separate exact
frame/footer/action-bar passes.

| Resolution | Inclusive outline | Exact perimeter | Runtime | Initial trace |
| --- | --- | --- | --- | --- |
| 800x600 | `(580,56)..(604,75)` | 86/86 | PASS | PASS |
| 1024x768 | `(804,56)..(835,80)` | 110/110 | PASS | PASS |
| 1280x720 | `(1060,56)..(1099,79)` | 124/124 | FAIL: coverage | PASS |
| 1280x960 | `(1060,56)..(1099,86)` | 138/138 | FAIL: coverage | PASS |
| 1920x1080 | `(1700,56)..(1759,90)` | 186/186 | FAIL: strict trace | FAIL |
| 802x602 | `(582,56)..(607,75)` | 88/88 | PASS | PASS |

The two 1280 runs aborted on `map_tile_coverage.py` exit 2 with
`low_overall_gameplay_coverage`, before final runtime summaries. Their labeled
diagnostic summaries preserve that failure. The prior candidate revision's
fog evidence is not substituted for these new bytes. At 1920x1080 the strict
trace reports line 556: an incremental input/exit lacks a fresh matching guard
and phase. Its original failed summary and diagnostic PNG remain preserved.
Exact pixels do not repair any of these runtime failures.

The [process-receipt export](../../captures/current/framed-minimap-process-receipts-20260906.json)
records five actual CDB/game pairs and their later absence. The 802x602 query
arrived after completion and contains no live pair; it is not exact-PID
cleanup proof. Private original receipt files were inaccessible to the matrix
task, which inspected and hashed the coordinator's durable export instead.
The matrix retains source paths/hashes, identity relationships, times and this
limitation. Earlier framed outcomes remain evidence for their original bytes,
without automatic transfer or reclassification.

## Evidence and focused verification

[framed_minimap_probe.py](../../tools/framed_minimap_probe.py) reconstructs
the optional candidate in memory and adds read-only before-call observations
of target, rectangle, color, thread, scale, world and scroll. The paused
`FRAMED_MINIMAP_VIEWPORT` observation precedes the existing minimap backing
observation. Its prelaunch packet binds the source main, observed main,
canonical installed-byte extra and source hashes. The prepared plan hashes
the entire source-main LF text and observed-main bytes. The source main is a
bound producer input derived from a previous actual main; the observer does
not claim to reconstruct every original harness command from scratch.

[minimap_viewport_audit.py](../../tools/minimap_viewport_audit.py) independently
recomputes the rectangle, requires the latest memory draw to match the paused
surface/thread/world/scroll/scale, and checks every perimeter pixel. It also
reconstructs the optional candidate and observer transformation, verifies both
planned main hashes, and rebinds raw, PNG, palette and candidate artifacts.
Its CLI writes a new output exclusively. Runtime and initial-trace failures
remain failures even if this separate geometry audit passes.

Passing focused checkpoints:

- [6 emitter tests](../../tools/test_framed_minimap.py): synthetic x86 at two
  addresses, native comparison plus six HD/custom sizes, scales 2/4, partial
  pixels, world edges, both targets, rejected state and register/flag/stack
  preservation.
- [6 integration tests](../../tools/test_framed_minimap_integration.py): six
  unchanged default candidates, the explicit thirteenth hook, relocation and
  loaded-byte coverage, and read-only observer construction/rejection.
- [13 audit tests](../../tools/test_minimap_viewport_audit.py): independent
  geometry and native raster, stale 9x7 and incorrect rounding, missing pixels,
  changed context/targets/probes/artifacts, exclusive output and preserved
  runtime/trace failures.

Native backing repair remains before the replacement outline. Together with
full/edge repaint coverage, that source order supports erasing the repainted
parts of an old outline. **This is a source argument, not actual panning or
old-outline-erasure proof.** These captures are fixed paused scenes; actual
scroll transitions, far-world screenshots, scale-4 runtime, visible composition and manual
input remain separate validation work. No stable promotion is asserted.

The later [controlled-scroll checkpoint](../../captures/current/framed-minimap-scroll-runtime-current.md)
adds three actual hidden runs on 2026-09-06: an eleven-tile horizontal pan and
a one-tile vertical pan at 1024x768, plus the native far-world clamp at 802x602.
Every resulting outline and all 90, 64 and 88 informative old-only pixels,
respectively, pass their separate geometry/erasure checks. All six captures
also pass the four frame bands, footer and six action-bar cells. Their exact
source/candidate, paused native state, backing and process-cleanup bindings are
in the [manifest](../../captures/current/framed-minimap-scroll-runtime-current.json).
See [MINIMAP_SCROLL_VALIDATION.md](MINIMAP_SCROLL_VALIDATION.md) for the disclosed
controlled dispatch and its limits. Scale-4 runtime, a no-op control, final
visible composition and natural/manual input remain pending.
