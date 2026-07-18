# SUPERSEDED — archived historical session record (do not cite as current evidence)

> **This document is a hand-written 2026-07-12 session log that has been
> superseded. It is retained as a historical record only. Four of its
> load-bearing claims are now known to be FALSE.** Archived 2026-07-18.
>
> 1. **"Battle visible click-to-callback: blocked by an environmental
>    incompatibility"** (see "Not achieved this session") is DEAD. The battle
>    natural click-to-callback is PROVEN — commit `c5fe1d70`, run
>    `captures/archive/battle-visible-input-present-20260717-133221`
>    (`eax=1` click gate + `0042d4e0` callback consumed). Canonical current
>    status: `captures/current/battle-visible-input-summary-current.md`
>    (focused completion 99.95%, click-consumed runs 1/1).
> 2. **"the building-sprite click coordinates are not documented"** (barracks)
>    is DEAD as a diagnosis. Commit `a07ea061` shows the barracks gap was a
>    misdiagnosis, not a coordinate problem: `0x86` IS present in the live
>    slot-0 castle, and the absent `0xFA`–`0xFD` are explained by
>    `flags_1a0=0x00`.
> 3. **The "PASS" rows in the per-target table are NOT valid input evidence.**
>    Every click in this session used `SetCursorPos`-style OS-cursor movement,
>    which the engine never sees — the menu reads its mouse from the
>    DirectInput accumulator. See commit `589f5700` (root cause) and `a07ea061`
>    ("that session never loaded the save at all ... `move_method setcursor`,
>    `logical_delta [0,0]`"). The castle reached at (470,397) was therefore a
>    default scenario, not the slot-0 save castle, and "Stormus" is an
>    exe-resident scenario default name rather than that record.
> 4. **"3 of 5 targets have clean verified-real-input evidence"** is DEAD. The
>    machine-generated checklist
>    `captures/current/manual-directinput-validation-checklist-current.md`
>    records all five targets as `pending_manual`, `manual_proof_supplied:
>    False`, `promotion_ready: False` — i.e. **0 of 5 accepted**.
>
> The still-standing contribution of this document is the headline finding that
> the HD UI renders correctly in the real runtime (the black patches are a
> hidden-proxy capture artifact). That finding is independently carried by
> `tools/first_mission_visual_audit.py`.

# Manual Visible-Runtime Session — 2026-07-12

Real DirectInput visible-runtime session, run after explicit user approval
("visible runtime approved"). All runs launched the game with the on-screen
GOG DirectDraw wrapper (`ddraw.dll`, "GOG.com DirectX 1-7 wrapper") from
`C:\Clash`, driven by real `SendInput` mouse events through
`scripts/smoke/run_clash_visual_smoke.ps1`, `tools/mouse_path_probe.py`, and
`scripts/capture/capture_clash_client_frame.ps1`. Client window is 800x600;
captures are 1200x900 GDI grabs (1.5x). Candidate SHAs: stable
`5E162FA81DF59533E0B99A0DCBC9EA24280DBEC46411AE871E968D6536C08B33`, castle
`1902213ADF825A7D7612A14C74AC5468BEBFCC4F00B43E60601FD8A832806DF6`,
right-bottom `D3FF331FD6A7B10A91C55A55FF891685CFAC376917816557B40A483EBDBC569C`.

## Headline finding: the HD UI renders correctly in the real runtime

The hidden-desktop CDB surface-dump proxy is an 8-bit memory-only fake
DirectDraw. It could never capture the minimap interior, the bottom
tooltip/status strip, or the selected-unit action panel, which is why the
`first_mission_visual_audit` flagged `minimap_interior`, `right_below_minimap`,
and `bottom_right_panel` as "black patches". In the **real visible runtime**
those regions render correctly:

- **Minimap**: fully populated with real terrain colours (land/water/roads)
  and the viewport rectangle — `captures/archive/visual-smoke-20260712-202900/after-map-path.png`.
- **Bottom tooltip/status text**: renders live — "Plain - 4ap",
  "Road - 3ap", "Desert - 5ap" on the respective tiles.
- **Selected-unit action panel** (the "right-bottom" widget): the wooden
  globe/units panel renders on the HD map surface after a real click —
  `captures/archive/manual-rightbottom-entry/after-load-map.png`.

So the black patches are a capture-tool artifact of the hidden proxy, not an
HD rendering defect.

**Post-session policy update (2026-07-13):** the repo-only
`first_mission_visual_audit` now combines its proxy primary-frame checks with
explicit per-region measurements from the tracked real-runtime frame above.
That corroboration can excuse the proxy-only black regions, but it remains a
render-presence check rather than a same-state pixel comparison.

## Per-target result

| Target | Real input result | Evidence | Status |
|---|---|---|---|
| `stable_menu_load` | Centered HD menu rendered; intro-skip click path verified; routed to gameplay | `visual-smoke-20260712-202900/menu.png`, `results.json` `MainMenuReady=True` | PASS |
| `stable_hd_map_input` | HD 12x9 map reached with working minimap + bottom tooltip; load-route clicks coordinate-verified (client error 0) | `visual-smoke-20260712-202900/after-map-path.png` | PASS |
| `castle_overview_centered_input` | Real click at client (470,397), error [0,0], `CaptureMode=screen`, entered castle overview ("Stormus" resource bar + MENU + back-arrow chrome) | `manual-castle-entry-v2/castle-overview.png`, `click-castle.json` | PASS (input); live capture tears on the animated overview |
| `right_bottom_validation_input` | Selected-unit action panel renders on the HD surface and the map responds to real clicks on the flagged fixture | `manual-rightbottom-entry/after-load-map.png` | PARTIAL — right-bottom UI renders + responds; the specific production action-menu descriptor was not isolated |
| `castle_barracks_centered_input` | Castle overview entered by real click; the specific barracks build sub-screen was not isolated with a verified click | `manual-castle-entry-v2/castle-barracks.png` | INCOMPLETE — real click reached the overview, not the barracks screen |

## Soak

`short2` menu-idle visible soak PASSED (`captures/current/hd-soak-short-current.json`):
120s, 8 frame samples, 9 process samples, 0 failures, min nonblack 60.5%,
input drift <=1px, negative working-set/private-memory/handle growth (no leak).

## Not achieved this session

- **Battle visible click-to-callback**: blocked by an environmental
  incompatibility, not a game defect. The visible battle input probe launches
  the game under x86 CDB with the dgVoodoo/GOG on-screen wrapper; CDB produces
  an empty log (the wrapper's D3D device creation does not complete under the
  debugger). The historical May runs used the memory surfdump proxy (no
  visible window), which is why they ran under CDB but never truly tested a
  visible click. A DirectInput-compatible visible wrapper that also tolerates
  CDB, or a gate that accepts visual command-execution proof, is needed.
- **`castle_barracks_centered_input`** and the exact
  `right_bottom_validation_input` action-menu descriptor: the animated castle
  interior tears under live GDI capture and the building-sprite click
  coordinates are not documented, so a clean verified click into those
  sub-screens was not isolated.

## Honesty note

The manual proof manifest is intentionally NOT marked promotion-ready: only 3
of 5 targets have clean verified-real-input evidence. The remaining targets and
the battle gate are recorded truthfully rather than forced to pass.
