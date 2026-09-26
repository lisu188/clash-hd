# Expanded battle visible rerun — September 24, 2026

The approved rerun displayed the expanded battle and recorded successful native
mouse and keyboard acquisition. Automated input dismissed the turn banner, but
subsequent pointer motion exposed a coordinate defect. **Overall acceptance
remains false.** Command callbacks, tactical movement/attack, battle completion,
map return, manual targeting and stable promotion are not established.

The [machine-readable report](battle-hd-visible-rerun-20260924.json) binds the
logs, original captures, frozen producers, launch plans, approval and cleanup
by SHA-256. The [September 19 failed attempt](battle-hd-visible-attempt-20260919.md)
and all earlier hidden and centered reports remain unchanged.

## Identity and launch conditions

Both runs used candidate
`7D04FE9005515DAD4E618DF507103946265D7E2A6421287281C1FC5F112D1E47`, stage
`gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-castlecenter-all-battlehd`,
at **1280×720**. The presenting proxy DLL was
`B4CF172509083066EEE011FDB866F9A07C6CC4FA1F0CE53EC1F90E28CB5A28B1`; its retained
build receipt records historical source `407D41D0…14ECB8EB`. This is the
presenting-proxy lane, not final GOG-wrapper composition. The retained
`dxcfg.ini` is provenance only; this proxy does not consume it.

The frozen v2 probe producer is
`F0C69F7885F45EE97BF3804C676568BB13FA6BC8F2B6BB4EE8E8F344E044132A`.
Run-02 used runner `D926B639…9A2BC2FF`; run-03 used `6A0A8E9E…20A6C598`.
Full hashes and source paths are in the JSON. The review verified retained
source/probe/approval files against each launch plan and rehashed the unchanged
original executable, candidate, private slot-zero save, DLL and build receipt.

The user explicitly approved the visible rerun, foreground/cursor control,
automated input and screenshots. Both runs disclose forced menu/load, adjacent
unit placement, battle-UI preference and entry-dialog setup. Subsequent battle
grid and command outcomes remain native. The recorded Sky input is automated;
it supplies no manual-input proof.

| Run | Observed result | Cleanup |
| --- | --- | --- |
| `run-02`, 06:24:41–06:31:03 UTC | Mouse acquisition returned `80070005`. The debugger reached `BHDV_READY` and six descriptors, but window activation failed and the retained JPEG contains wallpaper. No clicks were injected. | Owned candidate and debugger stopped on the controller's stop request; no cleanup errors. |
| `run-03`, 06:37:09–06:45:58 UTC | Runner used `UseShellExecute=false`, `CreateNoWindow=true`, normal game-window launch. Mouse and keyboard acquisition returned zero; 15 observed mouse reads returned zero. Eight battle JPEGs and four automated actions were retained. | Owned candidate and debugger stopped on the controller's stop request; no cleanup errors. |

The launch change and successful acquisition occurred together in run-03; this
does not isolate every possible cause of run-02's failure. `failure: null` in
the controller record describes its exception field, not acceptance.

## What the input log establishes

The real arena is **16×7**, camera `(0,0)`. All six live descriptors have their
expanded coordinates and original callbacks. The ready cursor bounds are
`(1,1,609,450)`; this is a transient native cursor state, not a measurement of
every later cursor. Selected unit type 5 records `attack_available=8` and
`attack_enabled=0`; no command state was forced to make it clickable.

The [run-03 log](C:/ClashTests/battle-hd-visible-20260924/run-03/cdb.log) records:

- Lines 375–381: successful device reads include the recorded click's button
  press/release. The turn banner disappears; the native cursor setter requests
  and returns `(576,360)`, and the prior renderer is restored.
- Lines 382–383: the grid accepts local/world `(8,3)` with button/latch zero.
  This follows native cursor restoration and does **not** prove tactical
  selection beyond column seven.
- Lines 386–388: successful relative delta `(-29,+1)` is followed by logical
  mouse `(576,4)`, rejected as outside the battlefield.
- Lines 393–395: delta `(-257,-5)` with the button held leaves `(576,4)` and
  is rejected again. The attempted drag did not establish unit movement.

Independent inspection of the exact candidate identifies a relative mouse
format (`dwFlags=2` at `004E80F0`). The inherited updater at `004E9810` scales
fresh deltas as absolute coordinates and rejects negative transformed values
with unsigned checks; the positive Y delta 1 becomes 4 while X remains 576.
The cursor-bounds helper at `004E99C0` also grants HD bounds only to metadata
`005196A0`; the ready battle cursor uses `005196C8`. These findings describe
the tested candidate. A correction needs separate candidate and runtime proof.

Return did not change the banner capture. Escape did not yield a recorded
dialog, command callback or return to the map. No such success is inferred
from a key press or from the absence of further markers.

## Capture and tear audit

The eight original files are in
[run-03/captures](C:/ClashTests/battle-hd-visible-20260924/run-03/captures).
They are **853×480 logical Sky Windows.Graphics.Capture JPEGs** of the
1280×720 candidate. No resizing, cropping, filters or drawing were applied
during this audit. Pillow decoded the three final JPEGs to RGB, saved lossless
PNGs and reopened them to verify exact equality with those decoded RGB bytes.
The original JPEGs are unchanged.

The retained `06-final-a`, `07-final-b` and `08-final-c` files are identical
both as JPEG bytes and as decoded pixels. Their capture metadata records
06:45:26.195, 06:45:32.620 and 06:45:50.891 UTC respectively. Both adjacent
pairs match. The same repo tear heuristic produced:

| Region, inclusive logical pixels | Ratio in each of three frames | Advisory verdict |
| --- | --- | --- |
| Full capture `(0,0)-(852,479)` | 1.064 | `clean_stable_pair` |
| Full battle band `(0,80)-(852,399)` | 1.045 | `clean_stable_pair` |
| Battlefield approximation `(21,90)-(745,389)` | 1.009 | `clean_stable_pair` |

The [audit manifest](C:/ClashTests/battle-hd-visible-20260924/run-03/audit-20260924/audit-manifest.json)
has SHA-256 `6405C4F4DC1D84F0E08B1393E06BA3448D22D1ADA72F22668B9C0D6CDE149CA5`.
It binds all eight original JPEGs/metadata, three derived PNGs, pair comparisons,
checker source and full metrics. The exact audit producer is retained beside it.

Visual inspection of the final frame shows all four frame edges, the native
sidebar statistics and command artwork, and black padding after the real
16-column battlefield. The bottom-right controls are visible; this is not six
observed successful command clicks. The sword cursor is visible in upper black
padding after the faulty motion. This inspection passes only the bounded
artwork-presence check at the retained logical resolution.

The tear heuristic is advisory and content/ROI dependent. Identical retained
frames do not establish capture independence, exact native-resolution pixels,
correct hitboxes or complete final-wrapper composition. JPEG decoding cannot
reverse pre-existing loss or logical scaling.

During later review, the user replied **“Battle is visible”** to the earlier
run-02 foreground question, after both owned runs had stopped. The observation
has no bound run/frame timestamp and is not assigned retrospectively to either
capture. It supplies no manual targeting proof; run-03's retained image evidence
stands independently.

Next acceptance work requires correct native pointer tracking, real displayed
grid selection/movement/attack, each available command, hover/dialog/results
behavior, and completed exit/map restoration with map interaction. Wider real
arenas, native/final-wrapper pixels, endurance and manual-input requirements
remain separate. No stable/default stage is promoted by these reruns.
