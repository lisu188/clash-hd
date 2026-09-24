# Retained resolution playability evidence: screen ownership

Reviewed 2026-09-24 against source `a1ba36cf8f00c90bbe394aeb010c744e6c8cf015`.
The latest actual run is [35565038115](https://github.com/lisu188/clash-hd/actions/runs/35565038115),
from 2026-09-21 at `4019fbcee20cd40cdf404fe9ebafeb53b4d7d8a3`.
The later green run `35565152328` is source-only and does not supersede its
runtime failures. See the [bound observation index](resolution-playability-screen-audit-20260924.json)
for the archive, report, primary/raw/palette/PNG and matching native-state identities.
Downloaded artifacts and original reports were preserved unchanged outside the repository.

| Candidate | Actual final native owner | Remaining failure |
| --- | --- | --- |
| modalwidgets 1024x768 + native-present bounds | Castle overview `00422020` | Corrupt castle image; subsequent unit/move clicks remained on the castle screen. No unit selected. |
| framed 3840x2160 + native-present bounds | Ordinary map `0040AD40` | All four frame bands fail the existing exact artwork audit; only 3/6 action cells match. Fixed input targets fall in fog. No unit selected. |
| classic 3840x2160 + native-present bounds | Ordinary map `0040AD40` | Action cells match 0/6; selection aiming fails. No four-sided-frame claim applies to Classic. |

All three retained runs completed the 110-second observation without a recorded
runtime exception, retained-process cleanup passed, and original/candidate identity
checks passed. Those observations do not make any complete playability result pass.

## Correct the audit without reclassifying the failed runs

The previous harness audited the last three primary buffers as ordinary maps
without checking native ownership. At 1024x768 all three buffers belong to the
castle. Retained map buffers and an active-map pointer survive that transition;
neither establishes that the ordinary map owns the screen. The archived top/left/right
mismatch counts and six matching action cells therefore cannot prove a map-frame
failure or a successful castle control layout. The visible corruption remains an
independent failed observation requiring instruction-boundary investigation.

`tools/resolution_playability.py` now requires each final primary's matching
`map-state-NN.json`, a paused primary record, the ordinary-map owner, inactive
native-modal state, valid map pointers, and bounded world/scroll coordinates.
Missing state, another owner's state, or a castle capture fails map eligibility.
All three final samples remain in the result; the audit never substitutes older
map screenshots for a later castle screen. Valid ordinary-map samples still run
the existing four-frame-band and six-action-cell artwork comparisons.

The 18 focused fixtures cover missing/wrong-index/unpaused state, retained map
buffers on castle entry, invalid context, all six cells, three final samples,
and preservation of genuine map pixel failures. This is an audit correction;
the runtime input sequence is not repaired by it.

## Next input and rendering work

The fixed unit target `(320,365)` addresses world tile `(scroll_x+4,scroll_y+5)`.
The observed scroll was `(26,39)` at 1024 and `(0,17)` at 4K. The retained states
contain no army, occupancy or visibility records, so they cannot identify a
selectable unit retrospectively. Capture those records, require an owned visible
stack, verify screen ownership immediately before input, and require a matching
selected-stack transition before attempting movement. The native handler's previous
selection at `00511B5C` is distinct from the panel cache at `00514194`, currently
labelled `previous_stack` by this diagnostic.

A separate source blocker is the lower world-size bound in
`src/patcher/framed_input.py`: at 4K it requires a world width of at least 59 tiles,
while this campaign is 50 tiles wide. Correct targeting alone cannot fix that
rejection. Any patch correction needs its own source/byte-bound validation stage
and relevant input evidence; do not alter frozen candidates or weaken their pins.

The 1024 screenshots reconstruct exactly from their recorded raw surface, pitch
and private palette. They are paused debugger-memory captures, separate from GDI
window grabs. They differ during animation and are not a stable pair; stopping
mid-render is still possible. Diagnose ordinary castle entry and its ownership,
allocation and draw boundaries before assigning a precise rendering cause.
No fresh runtime, manual input, stable promotion or release acceptance is claimed.
