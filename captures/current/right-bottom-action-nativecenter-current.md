# Right-Bottom Action Native-Center Evidence

- Status: wrapper-aware hidden-desktop visual proof passed; natural castle-click
  route reaches castle overview first. Command `0x63` enters the owner loop,
  but this save's castle owner record has owner flag `0x00`, so the
  `004338E0` action descriptor is deliberately parked off-screen at `x=1000`;
  validation-only.
- Stage:
  `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-rightbottomaction-nativecenter`
- Current wrapper-aware run:
  `captures\archive\cdb-surface-dump-20260517-172611\RUN-SUMMARY.md`
- Natural castle-click route run:
  `captures\archive\cdb-surface-dump-20260518-092756\RUN-SUMMARY.md`
- Natural castle command `0x63` route-split run:
  `captures\archive\cdb-surface-dump-20260518-100917\RUN-SUMMARY.md`
- Natural castle owner-loop gate run:
  `captures\archive\cdb-surface-dump-20260518-213418\RUN-SUMMARY.md`
- Earlier visual run:
  `captures\archive\cdb-surface-dump-20260515-141804\RUN-SUMMARY.md`
- Screenshot:
  `captures\archive\cdb-surface-dump-20260517-172611\surface.png`
- Natural castle overview screenshot:
  `captures\archive\cdb-surface-dump-20260518-092756\surface.png`
- Natural post-owner descriptor screenshot:
  `captures\archive\cdb-surface-dump-20260518-100917\surface.png`
- Patch manifest:
  `captures\archive\patch-stage-right-bottom-action-nativecenter-20260515.json`
- Strict natural UI probe:
  `captures\archive\cdb-surface-dump-20260517-163734\right-bottom-ui-summary.json`
- Candidate SHA-256:
  `D3FF331FD6A7B10A91C55A55FF891685CFAC376917816557B40A483EBDBC569C`

## Result

The wrapper-aware hidden-desktop CDB/proxy run passed with
`StoppedAfterDump=True`, an 800x600 final surface, `SURFDUMP_READY`, and no AV
rows. It uses `-SkipMapValidation` because this is an action-screen UI frame,
not a pure gameplay tile-coverage frame. The visual output no longer has the
horizontal striped action backdrop, and the action buttons sit on the native
action-screen art instead of being independently shoved into the HD coordinate
space.

The refreshed strict natural UI probe against the same candidate SHA keeps the
normal hidden map path healthy, but fails the action-menu route gate:
`OwnerActionRowsSeen=False`, `RBUI_PANEL_DRAW=0`, and `RBUI_ACTION_BOX=0`.
This means the native-center wrapper fixes the controlled action-screen visual
but does not yet prove that the natural gameplay UI path opens that action
screen.

The focused natural castle-click probe forces the real map-handler call-site
click at `0040B233` for screen `(352,272)` / map `(15,21)`. It proves
`sub_4084A0 -> Building_GetInto -> 00422180` on castle tile `32768`, building
index `0`, owner `0`, mode `2`, active `0`, and dumps the native 640x480
castle overview surface. No `004338E0 -> 00435BC0` owner/action rows appear in
that route.

The command `0x63` follow-up probe drives that one-screen-deeper route:
`00422180` overview hit-test raw `254`, command `99`, callback `00433C20`,
then writes `dword_532150`, `dword_53214C`, and `dword_532154` for the castle
owner. After the probe exits the overview, the first map-loop descriptor scan
of `00511D40` reports `NCMD99_POST_OWNER_DESC_RESULT result=0`, with
`d532218=00000000` and no `NCMD99_ACTION_4338E0_ENTRY`,
`NCMD99_ACTION_CALL_WRAPPER`, or `NCMD99_OWNER_435BC0_ENTRY` rows. This proves
command `0x63` is owner-state setup, not the action-screen opener by itself.

The owner-loop gate rerun reaches full `00433C20` owner-loop descriptor setup.
It logs `NOWNER_OWNER_SCREEN_DESC_DRAW` with descriptor `d1` callback
`004338E0`, but the descriptor is at `(1000,426)` while `owner_flag=0x00`.
That makes the save-state gate explicit: the right-bottom action wrapper is
visually valid when forced, but this castle state cannot naturally hit the
action descriptor. The visual issue in the user's screenshot is therefore now
tracked in the battle UI lane instead of the castle owner/action lane.

![right-bottom action native-center](cdb-surface-dump-20260517-172611/surface.png)

![natural castle overview route](cdb-surface-dump-20260518-092756/surface.png)

![natural post-owner descriptor route](cdb-surface-dump-20260518-100917/surface.png)

![native-center strict natural UI map frame](cdb-surface-dump-20260517-163734/surface.png)

## Evidence Chain

- `captures\archive\cdb-surface-dump-20260515-131514\surface.png` showed the live
  `00515130` descriptor shift improved button placement but left the action
  backdrop striped.
- `captures\archive\cdb-surface-dump-20260515-131648\surface.png` cleared the map
  surface before the action route; the stripes remained, so they were not stale
  map pixels.
- `captures\archive\cdb-surface-dump-20260515-140535\surface.png` skipped the
  `00435C80` `dw_13.gfx` load; the stripes disappeared with the backdrop,
  localizing the corruption to that 640-wide background decode.
- The new wrapper makes `00433914` call `0051B7E0`. The CDB log shows
  `APNATIVE_OWNER_435BC0_ENTRY ret=0051b837 ... surface=... sz=(640,480)`, so
  stock `00435BC0` ran on the temporary native surface.
- The same run then logs `APNATIVE_WRAPPER_RESTORE_MAP old_sz=(800,600)
  temp_sz=(640,480)` and `APNATIVE_WRAPPER_COPYBACK_DONE surface=... size=(800,600)`,
  proving the HD map surface was restored before the final dump.
- The earlier legacy `APPOST` probe against the same wrapper hit
  `00435BC0` correctly but timed out after a probe-only memory-access error:
  it sampled 800-wide offsets while `dword_5202E0` intentionally pointed at the
  temporary 640x480 surface. `probes/cdb/map/clash95_post_owner_action_nativecenter_extra.cdb`
  replaces that unsafe sampling with wrapper-address breakpoints.
- `tools\patch_stage_report.py --require-current-hd-map` reports `128 patched,
  0 original, 0 unexpected`; `right-bottom-action-native-center-wrapper` is
  `2/2`, `castle-ui-centered-input` is `8/8`, and the current HD map gate is
  `PASS`.
- `captures\archive\cdb-surface-dump-20260517-163116` reran the full-start natural UI
  launcher against the native-center stage. It timed out before gameplay with
  no AV rows, which matches the known hidden-desktop full-start fragility.
- `captures\archive\cdb-surface-dump-20260517-163734` reran the natural UI launcher
  with startup fast-forward and the stricter owner/action-row gate. The map
  dump passed on hidden desktop with `VisibilityExplainedGate.Passed=True`,
  `SURFDUMP_READY=1`, and the same candidate SHA, but
  `right-bottom-ui-summary.json` records `Passed=false`,
  `DescriptorOrViewportSeen=true`, `OwnerActionRowsSeen=false`,
  `RBUI_VIEWPORT_SWITCH=1`, `RBUI_PANEL_DRAW=0`, and `RBUI_ACTION_BOX=0`.
- `scripts/cdb/run_cdb_right_bottom_ui_probe.ps1` and its `scripts\cdb` mirror now fail
  closed by default unless owner/action rows appear; descriptor-only evidence
  requires the explicit `-AllowDescriptorOnly` switch.
- Unit-selection diagnostics are now explicitly separated from this menu:
  `captures\archive\cdb-surface-dump-20260517-171559` proves
  `sub_408030 -> sub_406980 -> sub_40A500 -> sub_423B00`, but that route is the
  selected-unit info/action path and does not enter `004338E0 -> 00435BC0`.
- `probes/cdb/ui/clash95_building_click_route_extra.cdb` now proves a castle-cell click route
  through the real map-handler call site. The passing hidden-desktop run
  `captures\archive\cdb-surface-dump-20260518-092756` logs
  `RBUILD_FORCE_AT_40B233 screen=(352,272)`, computes map `(15,21)`, re-arms the
  consumed commit click at `004087D7`, and reaches the owned castle tile row
  `tile=32768 index=0 owner=0 mode=2 active=0`.
- The same run logs
  `RBUILD_CALL_BUILDING_GETINTO -> RBUILD_GETINTO_CALL_422180 ->
  RBUILD_CASTLE_OVERVIEW_SURFDUMP_READY` and dumps surface `00526A68` as a
  640x480 castle overview. It does not log `RBUILD_CASTLE_UI_ENTRY`,
  `RBUILD_CASTLE_UI_CALL_435BC0`, or `RBUILD_OWNER_435BC0_ENTRY`.
- `probes/cdb/castle/clash95_castle_click_cmd99_to_action_extra.cdb` continues the route through
  the castle overview command. The passing hidden-desktop run
  `captures\archive\cdb-surface-dump-20260518-100917` logs
  `NCMD99_CASTLE_HITTEST_RESULT raw_hit=254`, installs command `99` callback
  `00433C20`, and records `NCMD99_WRITE_532150`,
  `NCMD99_WRITE_53214C`, and `NCMD99_WRITE_532154`.
- The full owner-loop gate run
  `captures\archive\cdb-surface-dump-20260518-213418` logs
  `NOWNER_OWNER_SCREEN_DESC_DRAW ... d1=(1000,426 cb=004338e0)` and
  `NOWNER_OWNER_DESC_RESULT_SURFDUMP_READY result=0 ... owner_flag=0x00`.
  This classifies the castle route as save-state gated rather than an HD
  coordinate failure.

## Interpretation

This supersedes the descriptor-shift visual attempt for controlled right-bottom
action-screen layout work. It remains validation-only because the refreshed
natural UI route still reaches only the map/viewport path, the natural
castle-click route reaches the castle overview screen first, command `0x63`
sets owner globals, and the owner-loop descriptor is intentionally off-screen
for owner flag `0x00`. The battle UI lane now carries the user's visible
stripe/layout complaint.
