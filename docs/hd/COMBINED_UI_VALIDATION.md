# Combined UI validation candidate

On 2026-09-05, a new validation stage combined existing patch groups without
changing the frozen patch table or protected stable default:

```text
gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-combinedui-validation
```

It contains the stable stage plus the extras from `-hdlayout-framerestore`,
`-rightbottomcompose`, and `-castlecenter-all-battlecenter-inputprobe`: 27 groups
and 166 patch records, selected in table order. The battle inputprobe suffix
includes actual grid and descriptor coordinate wrappers. Legacy alternative
present wrappers, action-descriptor anchors, and actionbar experiments are not
part of this candidate.

## Verified construction

- Input: the user-owned `C:\Clash\clash95.exe`, SHA-256
  `500055D77D03D514E8D3168506BD10F67CD8569BCC450604FF8192F46CDAF3AE`.
- Candidate:
  `C:\ClashTests\combinedui-validation\combinedui-20260905-095700\clash95_hd_combinedui_validation.exe`.
- Candidate SHA-256:
  `0A75CF35F42EFE1E44FBA1AC4031EAAE5323CDFF51AA19D261C36C5BB84691C2`.
- Initial candidate resolution: **800x600**. Its exact bytes remain unchanged
  after adding larger-resolution frame-restoration recipes.
- [Byte report](../../captures/current/combinedui-validation-patch-stage-current.json):
  166 patched, zero original, zero unexpected; current HD-map byte gate passes.
- Static fixtures verify the exact group union, absence of byte-span overlap,
  protected stable selection, and unchanged frozen `PATCHES` table hash
  `6683ee66851d23a28d856a8576e6b58c9b1285e0766bb592b9cdb0847bc8c55c`.

The patcher checked the original SHA and all selected old bytes before writing
the isolated candidate. The original was not overwritten.

## Initial hidden runtime evidence

The [2026-09-05 hidden checks](../../captures/current/combinedui-hidden-validation-current.md)
passed the existing full-tile geometry/visibility gate at 800x600 and 1024x768,
with five seconds of post-dump observation, no AV/quit marker, and the exact
constructed candidate SHAs. They used initialization-preserving startup
fast-forwarding. Separate native-startup timeout and whole-startup-bypass AV
results remain preserved; these passes do not establish native startup.

Source review found a gap outside that gate's full-tile coverage: terrain
redraw stops at the last complete tile, omitting the right/bottom partial
strips. At 1024x768 these are 32px and 48px; at 800x600 the bottom strip is 8px.
Increasing the draw counts alone is unsafe because native memory primitives
and world indexing need explicit bounds. A clipped partial-cell path is under
development. Complete rendering, visible composition, input, and promotion
remain unproven.

The [earlier combined layout run](../../captures/current/combinedui-layout-hidden-current.json)
on 2026-09-05 (`cdb-surface-dump-20260905-122508`) also passed the surface
and 166-record byte checks. It observed all six relocated panel draw routes
and the tooltip initialization anchor. Its [layout report](../../captures/current/combinedui-layout-summary-current.json) remains **failed**
because no panel hit-scan was observed; no direct redraw invocation occurred,
so that run did not prove redraw clipping. Both missing observations depended
on reaching `0x0040A460`, which the run did not observe. The failed report and
historical probe remain preserved.

The later [combined geometry run](../../captures/current/combinedui-layout-geometry-hidden-current.json)
(`cdb-surface-dump-20260905-124215`, 2026-09-05) uses the same 800x600 candidate
SHA above. Its [layout report](../../captures/current/combinedui-layout-geometry-summary-current.json)
**passes**, alongside the surface check and [166-record byte check](../../captures/current/combinedui-layout-geometry-patch-stage-current.json).
The new probe invokes a bounded redraw and list scan after panel setup at
`0x0040A431`. It observes all six relocated panel draws, the hit-scan anchors
`(608,528)` and `(736,560)`, the last descriptor accepted at clip width 800,
and the tooltip initialization anchor. One synthetic begin/return pair restores
ESP to `0x000EDCD0`; no AV or skipped-invocation marker occurs.

This is **forced geometry only**: the cursor stayed at `(320,166)`, outside the
command panel, and no native/user click callback was proved. No tooltip draw
occurred. Manual input, visible composition, promotion, and full-game completion
remain false in the evidence manifest. The pass does not cover the partial-tile
terrain strips, native startup, or final visible-wrapper composition.

The subsequent [six-screenshot audit](../../captures/current/action-bar-screenshot-audit-current.md)
finds **zero complete action-bar cells in all five 800×600 captures** and
**only the lower three cells complete at 1024×768**. This includes the
geometry-pass screenshot above. Exact indexed source comparisons confirm the
partial/missing captured composition; successful draw coordinates do not
establish that the bar survives the subsequent map redraw. Investigate the
draw/present order, then recheck every new screenshot. Hidden-layer limits
and the historical accepted right-bottom ruling remain separate.

## Larger-resolution construction

The new frame-restoration recipe repeats native left-band artwork
`(0,360)-(31,479)` down the additional left gutter and top-band artwork
`(480,0)-(639,15)` across the additional top gutter. It clips the final chunk;
it never enlarges a source rectangle beyond that artwork. Both backbuffer and
conditional screen copies preserve the native present flag and caller state.
The generated 217-byte code fits the existing 256-byte cave at VA `0x51BE00`.

On 2026-09-05, [isolated construction checks](../../captures/current/combinedui-resolution-build-current.md)
passed all 166 byte records at 800x600, 1024x768, 1280x720, 1280x960,
1920x1080, and the partial-tile custom case 802x602. The 800x600 output retains
the SHA above. Existing parser and immediate-width constraints still apply to
custom sizes. Semantic fixtures exercise 287 profiles and three present-flag
values, including clipped tails, callee register clobbers, and stack restoration;
independent x86 disassembly agrees with the generated instructions.

These are construction and generated-code checks. The initial 1024x768 hidden
surface result above covers full tiles only. Complete larger-resolution surface,
final-wrapper composition, input, and continuity evidence remains outstanding.
Launcher resolution statuses have not changed.

## Required combined-candidate evidence

Separate validation-stage successes remain useful existing evidence, but do
not prove the groups work together. Validate these on the exact combined SHA:

1. Selected-unit/hover restoration, terrain tooltip, command grid, and
   right-bottom status after owner/action redraw. The status copy and relocated
   command grid overlap in part of the bottom-right area; mode and redraw order
   must be checked in real composed frames.
2. Castle overview/interior/barracks entry and return, centered hitboxes, and
   observed callbacks. Preserve the accepted separate-stage evidence.
3. Battle entry/return, grid and descriptor callbacks, and final composition.
   The July 17 click-to-callback proof is already resolved; this requirement is
   for compatibility on the combined candidate.
4. Menu/map transitions, save/load, day advancement, representative campaign
   continuity, and endurance. Stable-stage soak results do not establish
   combined-candidate endurance.
5. Real manual-input release proof and an explicit promotion decision. Hidden
   surfaces cannot prove visible composition or manual input. Visible runtime,
   focus/cursor manipulation, input injection, and live capture require fresh
   explicit approval under the root agent guide.

For larger-resolution runtime validation, use dimension-aware stride, probe
coordinates, visibility coverage, and UI masks. Bind every evidence artifact to
matching dimensions, stage, and candidate SHA. Keep launcher statuses
experimental until their complete evidence lanes pass.
