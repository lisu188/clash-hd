# Saved soak screenshots: action-bar audit

All **12 saved PNGs** in the two named completed runs were visually inspected and compared against the exact source sprites on 2026-09-05. **Every frame has 0/6 complete cells at the HD anchor and 0/6 at the legacy anchor.** Terrain occupies both tested regions; no recognizable six-cell command strip is visible.

Both runs use the protected stable stage and candidate SHA `5E162FA81DF59533E0B99A0DCBC9EA24280DBEC46411AE871E968D6536C08B33` at 800×600. The stable candidate retains legacy command placement. The tested first-cell anchors are HD `(608,528)` and legacy `(416,400)`; each strip contains three columns and two rows of 64×32 cells. These are separate pixel diagnostics, with no HD validation or promotion claim.

| Run | Frame | HD cells | Legacy cells | Visual inspection |
|---|---|---:|---:|---|
| hidden-soak-20260905-140338-409-map-idle | [frame-0001](C:/ClashCaptures/hd-soak/hidden/hidden-soak-20260905-140338-409-map-idle/frames/frame-0001.png) | 0/6 | 0/6 | Inspected; command strip absent |
| hidden-soak-20260905-140338-409-map-idle | [frame-0002](C:/ClashCaptures/hd-soak/hidden/hidden-soak-20260905-140338-409-map-idle/frames/frame-0002.png) | 0/6 | 0/6 | Inspected; command strip absent |
| hidden-soak-20260905-140338-409-map-idle | [frame-0003](C:/ClashCaptures/hd-soak/hidden/hidden-soak-20260905-140338-409-map-idle/frames/frame-0003.png) | 0/6 | 0/6 | Inspected; command strip absent |
| hidden-soak-20260905-140338-409-map-idle | [frame-0011](C:/ClashCaptures/hd-soak/hidden/hidden-soak-20260905-140338-409-map-idle/frames/frame-0011.png) | 0/6 | 0/6 | Inspected; command strip absent |
| hidden-soak-20260905-140338-409-map-idle | [frame-0012](C:/ClashCaptures/hd-soak/hidden/hidden-soak-20260905-140338-409-map-idle/frames/frame-0012.png) | 0/6 | 0/6 | Inspected; command strip absent |
| hidden-soak-20260905-140338-409-map-idle | [frame-0013](C:/ClashCaptures/hd-soak/hidden/hidden-soak-20260905-140338-409-map-idle/frames/frame-0013.png) | 0/6 | 0/6 | Inspected; command strip absent |
| hidden-soak-20260905-114207-433-map-idle | [frame-0001](C:/ClashCaptures/hd-soak/hidden/hidden-soak-20260905-114207-433-map-idle/frames/frame-0001.png) | 0/6 | 0/6 | Inspected; command strip absent |
| hidden-soak-20260905-114207-433-map-idle | [frame-0002](C:/ClashCaptures/hd-soak/hidden/hidden-soak-20260905-114207-433-map-idle/frames/frame-0002.png) | 0/6 | 0/6 | Inspected; command strip absent |
| hidden-soak-20260905-114207-433-map-idle | [frame-0003](C:/ClashCaptures/hd-soak/hidden/hidden-soak-20260905-114207-433-map-idle/frames/frame-0003.png) | 0/6 | 0/6 | Inspected; command strip absent |
| hidden-soak-20260905-114207-433-map-idle | [frame-0237](C:/ClashCaptures/hd-soak/hidden/hidden-soak-20260905-114207-433-map-idle/frames/frame-0237.png) | 0/6 | 0/6 | Inspected; command strip absent |
| hidden-soak-20260905-114207-433-map-idle | [frame-0238](C:/ClashCaptures/hd-soak/hidden/hidden-soak-20260905-114207-433-map-idle/frames/frame-0238.png) | 0/6 | 0/6 | Inspected; command strip absent |
| hidden-soak-20260905-114207-433-map-idle | [frame-0239](C:/ClashCaptures/hd-soak/hidden/hidden-soak-20260905-114207-433-map-idle/frames/frame-0239.png) | 0/6 | 0/6 | Inspected; command strip absent |

The 140338 cleanup regression retains its recorded soak and guard **PASS** (120 seconds, 13 sampled frames; six edge PNGs retained). The 114207 long run retains its recorded **FAIL** (7200 seconds, 239 sampled frames; six edge PNGs retained): process 1336 did not exit within the recorded five-second cleanup window, and the report contains three cleanup-related failures. No process-state reinterpretation was performed.

For each PNG, the report and sample manifest agree on the frame, timestamp, dimensions and raw SHA. The directory inventory exactly matches the six retained PNG/raw pairs in each report. The candidate file SHA matches both run identities and their byte reports. PNG metadata hashes and the exact converter serialization were checked against raw bytes in memory. These PNGs use `grayscale-index` (no live palette); nothing was recolored, resampled, cropped or rewritten. Source sprite bytes remain exclusively in the user-owned `C:/Clash/DATA/minimum.res`.

The [JSON audit](soak-action-bar-audit-current.json) records every file SHA, all six cell comparisons at both anchors, source-resource/member hashes and comparison-tool hashes. Exact full-cell source matches are required; closest variants and matching rows are diagnostics only.

This establishes what is absent from the retained hidden software surfaces. It does not prove final visible-wrapper composition, manual input, callback behavior, promotion readiness, or the content of unsaved intermediate frames. The separate 141501 long run and any future images were **not checked**. Existing historical right-bottom proof and the protected stable stage remain unchanged.
