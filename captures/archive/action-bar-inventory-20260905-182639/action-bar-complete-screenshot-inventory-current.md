# Action bar verified in every current screenshot

The two new validation-candidate software screenshots have all six bottom-right buttons intact. Every 64x32 cell matches the source sprite pixels exactly; no tolerance, masking or image edits were used.

| New capture | Resolution | Complete cells | Runtime trace |
| --- | --- | --- | --- |
| [cdb-surface-dump-20260905-201619](C:/ClashCaptures/hd-completion/partialtiles-noop-v4-800x600-20260905/cdb-surface-dump-20260905-201619/diagnostic-surface.png) | 800x600 | 6/6 | FAIL |
| [cdb-surface-dump-20260905-202225](C:/ClashCaptures/hd-completion/partialtiles-noop-v4-1024x768-20260905/cdb-surface-dump-20260905-202225/diagnostic-surface.png) | 1024x768 | 6/6 | FAIL |

Both original runtime summaries remain failed. The 800x600 log contains duplicate/unpaired events; the 1024x768 log contains repeated/out-of-order input. Neither run recorded a full convergence/presentation pair. Both produced a raw buffer without an observed access violation or timeout, and all four recorded game/debugger processes were verified stopped.

Each diagnostic PNG was converted from its captured raw buffer with the recorded palette. Its separate diagnostic summary retains `Passed: false` and binds the unchanged original runtime summary. The pixel result does not establish final visible-wrapper behavior, manual input, or promotion.

The [complete inventory](action-bar-complete-screenshot-inventory-current.json) binds all eight PNGs under the current resolution-capture roots: six older failures and these two new pixel passes. The [separate soak audit](soak-action-bar-audit-current.md) covers all twelve saved PNGs in its two named runs; every one still lacks a complete bar. All twenty screenshots have been checked; older results were not reclassified.

Detailed observations: [800x600](partialtiles-noop-v4-800-observation-current.json), [1024x768](partialtiles-noop-v4-1024-observation-current.json).
