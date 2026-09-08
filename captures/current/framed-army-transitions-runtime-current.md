# Native army transitions: bounded 1024×768 pass

The hidden run executed **2026-09-06T09:49:52.7111501Z–09:51:12.5857021Z**
on unchanged validation candidate
`9bc99ba5a33248066b90b95119dd4301692d5af429d93167c4b35d2e508c53b5`.
The [bound checkpoint](framed-army-transitions-runtime-current.json) records
the full stage, immutable commands, actual screenshots, trace and cleanup.
The directory suffix `20260906-101900` is an artifact label; the host timestamps
above are the actual execution interval.

| Native transition | Selected / prior / lower owner | Portrait panel |
| --- | --- | --- |
| Select army 3 | 3 / 3 / 1 | Eight portraits |
| Switch to army 1 | 1 / 1 / 1 | Four portraits, six empty slots restored |
| Switch to army 2 | 2 / 2 / 1 | Two portraits, eight empty slots restored |
| Select single-squad unit 0 | 0 / -1 / 0 | Removed |
| Reselect army 3 | 3 / 3 / 1 | Eight portraits, entire screenshot identical to first selection |
| Native Map-mode callback | -1 / -1 / 0 | Removed |

All six actual screenshots pass every outer frame band and all six bottom-right
action cells. The 22 occupied portrait bodies and 18 inactive slot interiors
match their native source artwork. For both panel-close states, all 25,542
pixels of the former backing become palette index 1, recorded RGB black;
none retain their previous panel pixel. This is panel erasure in this scene,
not a complete terrain or fog proof. Portrait body comparisons use opaque
rows 20–48, excluding badges and count text.

The strict source-bound trace passes: six ordered states, eight paired draw
calls (four native and four composition, all returning 1), seven complete
terrain calls, and six consistent physical E0 identities. Map-mode deselection
uses descriptor `511D40` and native callback `409D80`, including its actual
selection write and both terrain returns. No selected index or native click
result is forced. The frozen initial-map startup separately controls menu entry.

The final host read equals the sixth stopped dump. Both retained processes
(CDB 30704, game 33568) are absent, both handles and the hidden desktop closed.
The original, candidate and all 58 workdir assets are unchanged. The plan's
packet receipt matches directly; this run needs no receipt correction. The
trace artifact preserves validator `3449a2e9…fbc49240`; a later CLI codec fix
does not change that recorded evaluation.

Screenshots are under
`C:/ClashCaptures/hd-completion/framed-army-transitions-20260906-101900/step-1.png`
through `step-6.png`. Source routes and expected stack/callback identities are
documented in [ARMY_TRANSITION_ROUTES.md](../../docs/hd/ARMY_TRANSITION_ROUTES.md).

This pass covers controlled native transitions and hidden software layout at
1024×768. Direct `408030` is a native selection routine, not ordinary map
dispatch through `40B10C`/`4084A0`. Portrait clicking, ordinary/manual input,
other resolutions, repeated scrolling, final visible composition, endurance
and stable promotion remain separate work. Earlier failed runs remain failed.
