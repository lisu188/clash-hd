# Framed castle, building and battle screen validation

Inventory and current evidence recorded 2026-09-06 for the user's request to
check the castle, battle and every building inside the castle screens. The
1024x768 overview and hospital now have bounded runtime captures with visual
failures; no modal screen is accepted as complete. Other cells remain pending
for the exact stage:

```text
gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-combinedui-partialtiles-initialpaint-framed-validation
```

The [ordinary-map resolution matrix](../../captures/current/framed-map-resolution-matrix-current.json)
contains two bounded runtime passes and six frame/footer/action-bar pixel
passes. It does not validate castle or battle owners. The
[four-sided frame contract](FOUR_SIDED_FRAME.md) defines the map geometry;
modal screens require their own composition and input evidence.

## Source and complete callable castle inventory

Native source is the user-owned `C:/Clash/clash95.asm`, checked against the
known original executable SHA-256
`500055d77d03d514e8d3168506bd10f67cd8569bcc450604ff8192f46cdaf3ae`.
Addresses below are preferred-base VAs, not file offsets. No original code,
artwork, saves or screenshots are embedded in this document.

The full castle entry is `00422180`, with castle index in EAX. It establishes
the owner at `00526A64` and hit-test surface at `00526A68`; the overview
renderer is `00422020`. Native initial redraw is called at `0042232E` and
returns to `00422333`. Later action redraw calls/returns at
`00422674/00422679`.

The authoritative dispatch table `off_42215C` (ASM line 52637) subtracts
`F8` from the hit-map value at `00422544` and maps eight possible IDs. The
localized names are the triplets starting at `00513BD0` (ASM line 414669).
Descriptor setup uses `004229A0`; the native gate at `00422590` leads to
`CALL ECX` at `0042262C`, passing the owner pointer in EAX. These yield
**seven callable overview commands**, rather than eight interiors:

| Screen | Hit-map ID | Command (hex) | Entry VA | Native artwork family |
| --- | --- | --- | --- | --- |
| Castle overview | — | — | `00422180`, renderer `00422020` | Castle composition |
| Court | `F8` | `86` | `0044FE70` | `stat.gfx`, `stat.s32`, `stat` |
| Hospital | `FA` | `99` | `0043DCE0` | `dw_20.*` |
| School | `FB` | `9C` | `0043D8E0` | `dw_20.*` |
| Workshop | `FC` | `9F` | `0043DEE0` | `dw_20.*` |
| Smith's shop | `FD` | `A6` | `0043DAE0` | `dw_20.*` |
| Barracks / Baraki | `FE` | `63` | `00433C20` | `dw_12.*` |
| Peasants | `FF` | `87` | `0042B0A0` | `dw_15.*` |
| Barracks recruitment/detail | Descriptor `00514FF5`, callback field `00515015` | Separate callback | `004338E0` → `00435BC0` | `dw_13.*` |

The four `dw_20` facilities share artwork but have distinct title/body routines;
one screenshot cannot stand in for all four. Source loop entries following
their first completed presentation are School `0043DA5A`, Smith `0043DC5A`,
Hospital `0043DE5A` and Workshop `0043E05A`. Peasants reaches `0042B36F`;
Barracks reaches `00433EB4`. These are candidate bounded observation points,
not an authenticated ready-to-run probe: verify instruction bytes and owner,
surface and call state against the exact candidate before using them.

Barracks changes its displayed name according to owner `+1A0` bit 2. The
confirmed recruitment callback `004338E0` checks that bit and uses initialized
owner `00532150` before calling `00435BC0`. That screen draws through
`004347A0`, `00435150`, `00435280` and `00435500`, initially calls present at
`00435DAF` and returns to `00435DB4`, and has native input owner `00435B90`.
`00435DA5` is earlier register setup, replaced by an inherited composition
hook in the current candidate. Its additional selection/action
states should be observed separately from its initial screen; unit-upgrade
and dispatch callbacks are not additional building kinds.

Two exclusions keep the inventory honest:

- Tower has a localized name and overview artwork, but hit `F9` dispatches to
  the default `004227FF` branch. There is no source-proven Tower interior
  callback. Check its overview appearance without inventing a fullscreen.
- A `dw_14` screen body exists at `00436300`, but the original-image/source
  inspection found no verified direct or absolute caller. It remains an
  unlinked screen variant requiring route discovery, not a proven reachable
  barracks subpage or a completed capture requirement.

## Natural and constructed availability

Castle owner byte `+2` selects a player. The value at
`gameData + 2231F + player*58F` selects Christian (`castle.chr`, nonzero) or
pagan (`castle.pog`, zero) artwork for the `dw_*` families. Capture both
resource variants where a screen uses them; do not duplicate a shared Court
asset claim merely to fill a matrix. Record castle/player and actual style.

The read-only inspected save `0.dat`, SHA-256
`4f2182409d209985a527f07c4116b19e44332416698d6acb0a3d35ae68db8a89`,
exists in the isolated `partialtiles-800x600-20260905-142000/workdir/save`
and matching 1024 workdir under `C:/ClashTests/hd-completion`. Its first four
castle records have feature fields `+1A0/+1A4` zero. Castle 0 at `(14,20)`
belongs to player 0 with Christian style; castle 2 at `(60,46)` belongs to
player 2 with pagan style. These facts do not establish enabled interiors or
permission to change ownership/availability silently.

The existing visible hit-map catalog distinguishes Court, Barracks and
Peasants from four dormant facility entries. The flags probe writes owner
`+1A0=1F` and `+1A4=01` to expose those entries. Such an isolated constructed
fixture can demonstrate a controlled route/draw only when its mutations are
recorded; it is not natural availability or manual-input proof. Copy the
verified fixture to a unique workdir and preserve the original save and hash.
Do not modify a user save or retain in-game writes in the source installation.

## Battle screens and fixtures

| View | Source route | Observation boundary / limitation |
| --- | --- | --- |
| Initial battle overview | `Unit_Attack 0041AD20` → call at `0041B145` → `BattleRunner 0042E9E0`; building-attack entry is `0041B7D0` | Initial present `0042F2F5`, return `0042F2FA`; entry alone does not prove a composed control screen |
| Enabled tactical command | Grid route `0042E4ED` → `0042CB50`; descriptor route `0042E501` → `00419DC0`; command descriptor `00514B78` → callback `0042D4E0` | Disabled branch `0042D51C`, enabled state branches `0042D543/0042D55C`; record the actual branch and resulting draw |
| Post-battle outcome windows / route discovery | Native writeback call `0042F46C` → `HandleBattleResults 0042E5A0`; a conditional outcome branch later calls `UI_ShowInfoWindow` at `0042F4DC` | Writeback is not a screen. `0042E6F0` is a battle-grid state helper, not an after-results boundary. Each actual outcome window needs its own completed draw contract; these symbols do not establish a generic results screen |

The [remaining-route source review](FRAMED_REMAINING_SCREEN_ROUTES.md)
records exact native bytes, candidate hook differences and stack contracts for
Court, recruitment and battle. It identifies Court's converged first present
and a specific post-battle message route while keeping unsupported capture
boundaries explicit. Historical probe labels do not establish a results view.

The [constructed battle save manifest](../../captures/current/battle-constructed-save-fixture-current.json)
binds the isolated fixture
`C:/ClashTests/battle-enabled-fixture-20260520-210728/game/save/0.dat`, SHA-256
`278126f248c5f7a84f396eebf25f37b21948968557571838cf73462edfd39cdc`.
It changes unit 0 from Light cavalry to Dragon cavalry to enable the command
route. Preserve that provenance when copying the fixture to a fresh workdir.
The original save is unchanged. A forced attack probe additionally relocates
an attacker next to an enemy and invokes the native attack; that is controlled
route evidence, not a natural user action.

## Historical probes and the separate framed modal lane

- [Castle descriptor catalog](../../probes/cdb/castle/clash95_castle_interior_catalog_extra.cdb)
  enters `00422180`, forces hit IDs and logs descriptors. At `00422590` it
  sets EAX to zero to suppress callbacks. Its seven-descriptor PASS supplies
  no building-interior screenshots.
- [Overview flags catalog](../../probes/cdb/castle/clash95_castle_overview_flags1f_multihit_extra.cdb)
  exposes dormant entries using explicit owner-flag writes and also suppresses
  the interior callback.
- [Barracks second-action probe](../../probes/cdb/castle/clash95_castle_barracks_second_action_select1_extra.cdb)
  supplies an existing controlled recruitment/detail route. Short returns,
  forced owner state and callback selection must remain disclosed.
- [Battle attack-entry probe](../../probes/cdb/battle/clash95_battle_force_attack_entry_extra.cdb)
  scans units and forces one native attack; the
  [command callback probe](../../probes/cdb/battle/clash95_battle_force_command_callback_extra.cdb)
  adds synthetic mouse/click state and bounded input-wait overrides. Its
  coordinates are tied to the legacy 800x600 path.

The current [surface harness](../../scripts/cdb/run_cdb_surface_dump.ps1)
requires `-FramedValidation -PartialTileValidation -InitialMapPaintValidation`,
the exact framed stage, hidden memory proxy, canonical map probe and load slot
0. That branch rejects `-ExtraProbeTemplate`, `-SkipMapValidation`, visible
desktop and custom probe substitutions. The
[resolution renderer](../../tools/render_cdb_surface_probe.py) also rejects
legacy extra probes outside the non-framed 800x600 profile. The harness always
builds from the known original; it does not accept a prebuilt candidate for
reuse. Supplying a framed executable as `InputExe` fails original identity.

The separate [modal host](../../scripts/cdb/run_framed_screen_capture.ps1),
[packet producer](../../tools/framed_screen_probe.py) and
[trace validator](../../tools/framed_screen_trace.py) now provide the supported
bounded path for overview, hospital, school, workshop, smith, barracks and
peasants. Its default is an offline plan; execution uses a hidden desktop and
non-presenting proxy, with candidate/source/loaded-byte checks, full initial
map trace, ordered modal draw and exact retained-process cleanup. Forced native
dispatch and optional `construct_all` availability remain explicit. The
[pixel auditor](../../tools/framed_screen_surface_audit.py) reconstructs the
packet/probe/trace and binds raw, PNG and palette before comparing pixels.
Court, recruitment and battle still need their own supported capture paths.

Ordinary map owner `0040AD40` admits the new frame path; castle/battle owners
use inherited native or prior centered fallback. That fallback does not prove
HD centering, complete modal composition or input alignment. A centered
native 640x480 modal has expected outer margins. Applying the full-window
ordinary-map frame/footer profile measures different geometry; a mismatch
alone is not a castle defect or an accepted modal-frame test.

## Current 2026-09-06 evidence

The [compact checkpoint](../../captures/current/framed-modal-runtime-current.md)
and [bound JSON](../../captures/current/framed-modal-runtime-current.json)
preserve four attempts on candidate
`69899e07f70dde2094264be694300e00c7a778f1391ac7797b74c59c56ee1ce0`,
with the optional minimap viewport fix at 1024x768:

| Attempt | Route / availability | Original result | Pixel and visual evidence |
| --- | --- | --- | --- |
| `035304` | Overview / `existing_flags` | FAIL before modal readiness | No snapshot; rejected entry observation preserved |
| `040604` | Overview / `existing_flags` | FAIL before host header read | Source-bound modal trace passes, but UIntPtr conversion prevents capture |
| `040923` | Overview / `existing_flags` | Bounded runtime and trace PASS | Existing PNG has displaced rows and a corrupt red lower region inside the centered modal; visual FAIL |
| `041248` | Hospital / `construct_all` | Bounded runtime and trace PASS | Existing PNG has horizontal corruption, hospital content near native640 coordinates and stale centered castle content below; visual FAIL |

The failed attempts remain in their original summaries and preserved
[entry](../../captures/current/framed-modal-overview-entry-failure-20260906.json)
and [host-read](../../captures/current/framed-modal-overview-host-read-failure-20260906.json)
observations. The later post-PUSH observer and explicit UIntPtr constructor
are distinct producer/host revisions; neither changes an earlier verdict.
All four runs retain matching signaled/closed debugger and game handles plus
closed hidden desktops. The checkpoint performs no new live process query.

The [overview](../../captures/current/framed-modal-overview-1024x768-pixels-20260906.json)
and [hospital](../../captures/current/framed-modal-hospital-1024x768-pixels-20260906.json)
audits pass their source, trace and image bindings. Their full-window
ordinary-map frame/footer comparisons fail and are retained as measurements.
Both have 0/6 ordinary-map action cells, explicitly inapplicable to modal
controls. Root and an independent reviewer inspected the existing PNGs:
the actionable visual failures are **inside the displayed modal content**,
not simply absent outer map artwork. Overview has a visible lower-left back
control; hospital shows its native-position arrow and a retained castle arrow.
Their input behavior is untested. Hidden software captures may omit
primary-only overlays; no final visible, gameplay, natural/manual input,
modal-controls or promotion acceptance follows from these runtime passes.

## Pending capture matrix

`Pending` means no completed framed-stage capture for this view. A captured
`runtime PASS / visual FAIL` cell still requires repair and new evidence; it
is not accepted as complete. The matrix enumerates nine castle views, two battle views and a
post-battle outcome-route discovery row at
five advertised HD presets plus one custom boundary case. For each applicable
castle row, include both actual artwork variants and record availability and
selection state; these are additional cases, not implied by one row's pass.

| View | 800x600 | 1024x768 | 1280x720 | 1280x960 | 1920x1080 | 802x602 |
| --- | --- | --- | --- | --- | --- | --- |
| Castle overview | Pending | Runtime PASS / visual FAIL | Pending | Pending | Pending | Pending |
| Court | Pending | Pending | Pending | Pending | Pending | Pending |
| Hospital | Pending | Runtime PASS / visual FAIL (`construct_all`) | Pending | Pending | Pending | Pending |
| School | Pending | Pending | Pending | Pending | Pending | Pending |
| Workshop | Pending | Pending | Pending | Pending | Pending | Pending |
| Smith's shop | Pending | Pending | Pending | Pending | Pending | Pending |
| Barracks / Baraki | Pending | Pending | Pending | Pending | Pending | Pending |
| Peasants | Pending | Pending | Pending | Pending | Pending | Pending |
| Barracks recruitment/detail | Pending | Pending | Pending | Pending | Pending | Pending |
| Battle initial overview | Pending | Pending | Pending | Pending | Pending | Pending |
| Battle enabled command | Pending | Pending | Pending | Pending | Pending | Pending |
| Post-battle outcome windows / route discovery | Pending | Pending | Pending | Pending | Pending | Pending |

Each accepted capture must bind the exact candidate SHA/stage/resolution,
original loaded-byte checks, save/source/probe hashes, hidden wrapper,
forced/natural route, owner and surface, actual ready/present markers, original
summary and terminal cleanup. Check complete screen edges, background/text,
controls and bottom-right composition in the actual captured pixels. Do not
grade a modal image with an ordinary-map terrain heuristic or interpret an
omitted primary-only layer as final visible composition. Route, draw, visual,
input and promotion claims remain separate.

Historical [castle overview evidence](../../captures/current/castle-overview-evidence-current.json)
and [battle UI evidence](../../captures/current/battle-ui-evidence-current.json)
remain tied to their older candidates. The resolved July right-bottom gate
decision and proven battle click-to-callback are not reopened by this new
matrix. Five-target manual input, final visible composition and explicit
stable promotion remain separate boundaries; no approval or result is
manufactured here.
