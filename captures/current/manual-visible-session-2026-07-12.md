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
HD rendering defect. This does not by itself flip the repo-only
`first_mission_visual_audit` gate (which still parses the proxy dumps), but it
materially changes the completion picture.

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
