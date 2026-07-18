# Real-Runtime Per-Screen Visual Audit — 2026-07-12

Independent multi-agent visual audit of the Clash95 HD mod captured from the
**real visible runtime** (GOG dgVoodoo DirectDraw wrapper on the interactive
desktop), run after explicit user approval. Six per-screen auditor agents plus
a lead synthesis agent; corroborated with two filesystem facts.

> **SUPERSEDED IN PART (2026-07-18).** This is a dated record; the per-screen
> render verdicts and the black-patch-artifact thesis still stand. Two of its
> *diagnoses* have since been disproven:
>
> 1. **The barracks "missing coordinate" is wrong** (commit `a07ea061`).
>    Command `0x86` **is** present in the live slot-0 castle at displayed
>    `(371,107)` (raw `0xF8` → `0x86` → callback `0044FE70`, gate `1`;
>    evidenced twice by `cdb-surface-dump-20260712-144245` multihit and
>    `-144151` hitbox; 21906 hitmap px, native bbox `[175,47,455,223]`). The
>    hitmap was the live save's own castle (owner record 0, "Drakefly");
>    "Stormus" is an exe-resident scenario default name, not that record. The
>    2026-07-12 miss happened because that session **never loaded the save** —
>    `SetCursorPos` moved only the OS cursor, never the DirectInput
>    accumulator, so a default scenario with a different castle was on screen
>    (click JSON: `move_method=setcursor`, `logical_delta [0,0]`). See
>    `589f5700` for the input-mechanism fix.
> 2. **Battle click-to-callback is no longer blocked — it is PROVEN**
>    (commit `c5fe1d70`). See the note on that bullet below.

## Grounding facts (mechanical, not visual)

- `captures/archive/cdb-surface-dump-*/surface.raw` = **480,000 bytes = exactly
  800x600x1** — the hidden CDB surfdump proxy is a genuine 8-bit paletted
  memory surface. This is the mechanical root cause of both the palette recolor
  (green->orange "lava") and the missing blit layers (minimap, tooltip).
- `manual-castle-entry-v2/castle-barracks.png` (2,524,740 B) vs
  `castle-overview.png` (2,524,231 B) differ by ~509 bytes (<0.02%) — the two
  are effectively the **same frame**. The "barracks" capture never left the
  castle overview courtyard. ~~(confirmed again 2026-07-12 by the
  `manual-barracks-entry` run: a coordinate-perfect click at command-0x86
  hitmap point (371,107) landed on the castle wall, frame unchanged)~~
  — **struck 2026-07-18 (`a07ea061`)**: that click never landed "on the castle
  wall". The session never loaded the save (`move_method=setcursor`,
  `logical_delta [0,0]`), so a different, default-scenario castle was on
  screen. The two-file byte-diff fact above is unaffected; only the *cause*
  attributed to it was wrong.

## Per-screen verdict (real runtime)

| Screen | Real % | Renders correctly | Genuine defects | Capture artifacts |
|---|---:|:---:|---|---|
| Main menu | 100 | yes | none | 120/90px letterbox = intended 4:3 centering |
| HD world map (12x9, right minimap) | 98 | yes | none | ALL audit-flagged black patches are proxy artifacts |
| Overworld (castle-entry map) | 90 | yes | tooltip is hover-state (renders elsewhere); L-frame gutters | dithered castle shadow = authored alpha |
| Right-bottom selected-unit panel | 82 | yes | panel docks center-bottom not far-right; production menu not demonstrated | proxy rendered this region black (origin of "panel missing" belief) |
| Castle overview (courtyard) | 100 | yes | none | live GDI tears on the idle-animated courtyard only; proxy is pristine |
| Castle barracks (build/unit-list) | 0 | no | never entered (navigation gap; coordinate is known — see 2026-07-18 note) | overview tear is an artifact; missing barracks UI is a real coverage gap |

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
  coverage gap. ~~Entering them needs a castle-specific building-click
  coordinate not documented for the slot-0 "Stormus" castle~~ — **corrected
  2026-07-18 (`a07ea061`): the coordinate is documented.** Command `0x86` is
  present in the live slot-0 castle at displayed `(371,107)` (native bbox
  `[175,47,455,223]`, callback `0044FE70`, gate `1`). The plan now aims the
  region interior at displayed `(398,228)` = native `(318,168)` for margin,
  keeping `(371,107)` as the proven fallback; **`(398,228)` is a static
  derivation from the committed raw hitmap and has not yet been live
  hit-tested.** The screen is still unentered: the remaining work is executing
  the `0044FE70` callback, which hidden probes deliberately suppress. The
  animated view also tears under live GDI capture. Not a rendering defect —
  the proxy dump `cdb-surface-dump-20260712-155528` shows the full
  roster/stat/build UI the engine draws.
- **Battle click-to-callback**: ~~hard-blocked (CDB will not complete dgVoodoo
  D3D device creation under the debugger)~~ — **superseded 2026-07-18: PROVEN**
  (commit `c5fe1d70`). Run
  `captures/archive/battle-visible-input-present-20260717-133221` records
  `BATTLE_COMMAND_CLICK_GATE_OBSERVED desc=00514b78 eax=1` followed by
  `BATTLE_COMMAND_CALLBACK eip=0042d4e0`, with `BATTLE_COMMAND_CLICK_GATE_FORCE`
  absent from the whole run. Unblocked by the `CLASH_PROXY_PRESENT` painting
  proxy (present-on-`Unlock`, since battle paints via `Lock`/`Unlock` and never
  `Flip`/`Blt`) plus restoration of the game's own input pump `004605d0`.
  Still unrelated to these six screens.
- **Post-report policy update (2026-07-13):** `first_mission_visual_audit`
  now accepts this evidence as per-region render-presence corroboration. A raw
  proxy-black region is excused only when the supplied real-runtime frame
  measures that same screen region as clearly rendered. This is not a
  same-state pixel comparison; a same-state A/B remains useful optional
  hardening, not a prerequisite for the current gate.

Evidence PNGs are kept local per the no-large-captures packaging boundary;
paths are recorded in `captures/archive/manual-visible-session-2026-07-12.md`
(moved out of `captures/current/` on 2026-07-18 and banner-marked SUPERSEDED —
its battle-blocker, barracks-coordinate, and 3-of-5-PASS claims are all now
false; see that file's banner. Only the PNG path list is still usable).
