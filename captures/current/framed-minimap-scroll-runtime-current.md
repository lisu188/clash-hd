# Controlled minimap scroll: recorded runtime evidence

Recorded 2026-09-06T05:27:58.724747+00:00. The optional minimap correction remains validation-only.

| Resolution | Actual scroll | Inclusive outline, before → after | Old-only pixels restored | Frame / footer / action bar |
| --- | --- | --- | --- | --- |
| 1024x768 | (0, 17) → (11, 17) | `(784, 56, 815, 80)` → `(806, 56, 837, 80)` | 90/90 | Both captures pass all four edges, footer and 6/6 cells |
| 802x602 | (0, 17) → (89, 92) | `(562, 56, 587, 75)` → `(740, 206, 763, 223)` | 88/88 | Both captures pass all four edges, footer and 6/6 cells |
| 1024x768 | (0, 17) → (0, 18) | `(784, 56, 815, 80)` → `(784, 58, 815, 82)` | 64/64 | Both captures pass all four edges, footer and 6/6 cells |

Both source-bound native callback/trace and independent final-log erasure evaluations pass.
Retained CDB/game handles confirm all three owned process pairs stopped; workdir assets and original executable are unchanged.

[Exact manifests, source/candidate hashes, captures and cleanup receipts](framed-minimap-scroll-runtime-current.json).

The first 1024 run started at (0,17), so it is an eleven-tile horizontal pan. The later
1024 run moved one tile vertically to (0,18), repairing all 64 old-only border pixels. The 802 run
requested (90,93) and clamped to (89,92); its rectangle shrank to the remaining
704×512 world pixels. Its far-corner map area is black in the captured software surface.

These are controlled hidden captures, with disclosed mouse-global writes and a gate-result
override. They do not establish natural/manual input, final visible composition, scale-4
runtime, other resolutions, no-op cases or promotion. Earlier failures remain preserved.
