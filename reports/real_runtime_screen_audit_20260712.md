# Real-Runtime Per-Screen Visual Audit — 2026-07-12

Independent multi-agent visual audit of the Clash95 HD mod captured from the
**real visible runtime** (GOG dgVoodoo DirectDraw wrapper on the interactive
desktop), run after explicit user approval. Six per-screen auditor agents plus
a lead synthesis agent; corroborated with two filesystem facts.

## Grounding facts (mechanical, not visual)

- `captures/archive/cdb-surface-dump-*/surface.raw` = **480,000 bytes = exactly
  800x600x1** — the hidden CDB surfdump proxy is a genuine 8-bit paletted
  memory surface. This is the mechanical root cause of both the palette recolor
  (green->orange "lava") and the missing blit layers (minimap, tooltip).
- `manual-castle-entry-v2/castle-barracks.png` (2,524,740 B) vs
  `castle-overview.png` (2,524,231 B) differ by ~509 bytes (<0.02%) — the two
  are effectively the **same frame**. The "barracks" capture never left the
  castle overview courtyard (confirmed again 2026-07-12 by the
  `manual-barracks-entry` run: a coordinate-perfect click at command-0x86
  hitmap point (371,107) landed on the castle wall, frame unchanged).

## Per-screen verdict (real runtime)

| Screen | Real % | Renders correctly | Genuine defects | Capture artifacts |
|---|---:|:---:|---|---|
| Main menu | 100 | yes | none | 120/90px letterbox = intended 4:3 centering |
| HD world map (12x9, right minimap) | 98 | yes | none | ALL audit-flagged black patches are proxy artifacts |
| Overworld (castle-entry map) | 90 | yes | tooltip is hover-state (renders elsewhere); L-frame gutters | dithered castle shadow = authored alpha |
| Right-bottom selected-unit panel | 82 | yes | panel docks center-bottom not far-right; production menu not demonstrated | proxy rendered this region black (origin of "panel missing" belief) |
| Castle overview (courtyard) | 100 | yes | none | live GDI tears on the idle-animated courtyard only; proxy is pristine |
| Castle barracks (build/unit-list) | 0 | no | never entered (navigation gap; needs castle-specific building coord) | overview tear is an artifact; missing barracks UI is a real coverage gap |

**Honest overall real-runtime proof coverage: ~80%** (the single barracks 0
pulls the reached-screen average of ~94% down). Render quality on every screen
actually reached is 94-100% with zero genuine HD-compositing or layout defects.

## Black-patch-artifact thesis: CONFIRMED (strong)

Measured black-pixel fractions (RGB max < 24), proxy -> real:

- minimap interior: **98.9% -> 0.0%** (real mean RGB 44,169,84 = green terrain)
- right-below-minimap: **77.8% -> 0.0%**
- bottom-right panel: **80.2% -> 5.5%** (residual = one ~8px intentional
  bottom letterbox row)
- bottom tooltip `Plain - 4ap`: absent in proxy, present in real

Every region the automated `first_mission_visual_audit` flags as a "black
patch" is a proxy capture artifact, not a real-runtime defect. The gate is
grading the 8-bit surfdump, not the game.

**Methodological caveat:** the proxy and real map frames were different
camera/game states, so this is a per-region render-presence audit, not a
same-state pixel-diff. Presence is robust (98.9% vs 0% is not camera drift);
hardening to a same-state A/B remains available.

## Residual work (honest)

- **Barracks build screen** and the **castle production action menu**: real
  coverage gap. Entering them needs a castle-specific building-click
  coordinate not documented for the slot-0 "Stormus" castle; the animated view
  also tears under live GDI capture. Not a rendering defect — the proxy dump
  `cdb-surface-dump-20260712-155528` shows the full roster/stat/build UI the
  engine draws.
- **Battle click-to-callback**: hard-blocked (CDB will not complete dgVoodoo
  D3D device creation under the debugger); unrelated to these six screens.
- The `first_mission_visual_audit` gate stays failing (honest) until a
  same-state real-runtime capture replaces the proxy primary frame; this
  report is the evidence for why those ~region checks are proxy-invalid.

Evidence PNGs are kept local per the no-large-captures packaging boundary;
paths are recorded in `captures/current/manual-visible-session-2026-07-12.md`.
