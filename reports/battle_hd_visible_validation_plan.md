# Expanded battle visible validation plan

Status: the prepared controller was exercised in an approved September 19
session, which stopped before battle readiness. See the
[retained failed attempt](../captures/current/battle-hd-visible-attempt-20260919.md).
No passing visible, injected-input or manual evidence resulted. The candidate
is still validation-only; the checklist below remains outstanding.

## Concrete session target

- Executable: `C:\ClashTests\battle-hd-20260919\clash95_battlehd.exe`.
- SHA-256: `7D04FE9005515DAD4E618DF507103946265D7E2A6421287281C1FC5F112D1E47`.
- Stage: `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-castlecenter-all-battlehd`.
- Resolution: `1280x720`; record the actual wrapper DLL and configuration hashes.
- Prerequisites: 283/283 patch records verified, seven helper diagnostics pass,
  and failed hidden cursor polling is classified. See the
  [September 19 report](../captures/current/battle-hd-followup-20260919.md).

Fresh explicit approval must cover visible launch, foreground/cursor control,
process-scoped input injection and live captures for this session. Approval
alone supplies no runtime or manual evidence. Record the real approval only
after it is given, together with the exact session scope.

## Session implementation requirements

Use the separate expanded-stage
[`run_battle_hd_visible_session.ps1`](../scripts/cdb/run_battle_hd_visible_session.ps1)
and its byte-verified [`battle_hd_visible_probe.py`](../tools/battle_hd_visible_probe.py)
producer. The runner defaults to a plan-only path and requires an exact approval
record plus `-ExecuteApproved` to launch. It does not control windows or inject
input. The existing
[`run_cdb_battle_visible_input_probe.ps1`](../scripts/cdb/run_cdb_battle_visible_input_probe.ps1)
must not be reused unchanged: its default `(588,440)` target now lies inside
the battlefield, process selection/cleanup is broad, and its raw-input path
can fall back to unverified screen coordinates. Existing centered parsers and
the `(80,60)` translation probe cannot validate this stage.

Bind the candidate's SHA, stage, resolution and wrapper before launch. Retain
the exact launched process ID, start time and executable path; resolve its
window by process identity. Scope foreground actions, input, capture and
cleanup to that process and its task-owned debugger. Never select the newest
matching game or stop unrelated game/debugger processes.

Measure client origin, size and DPI before every input phase. Stop input if
the displayed geometry is unavailable or does not match the measured 1280x720
layout. Do not reuse fallback screen coordinates. Read all six live command
descriptors and enabled states before choosing command targets.

Preserve native DirectInput acquisition and polling. The hidden surface-dump
base probe bypasses mouse acquisition; making that route visible cannot
establish input proof. Observe device-read results and reject failed reads as
input evidence. Record any forced battle-entry setup separately from subsequent
OS input, and keep automated injection distinct from manual user actions.

## Observations to collect

1. Capture the displayed battle with all four battlefield/frame edges and the
   original sidebar. Record arena dimensions and horizontal camera position.
   The battlefield uses half-open bounds `(32,136)-(1120,584)`. A 16-column
   arena ends at x=1056, so its seventeenth slot must stay clear and inactive.
2. Verify grid selection, movement and attack targeting at final displayed
   coordinates, including columns beyond seven and boundary rejection. Check
   outer padding, the sidebar and nonexistent cells separately. Use only
   existing arena cells; do not fabricate wider maps for visual acceptance.
3. Exercise the six command descriptors according to their live enabled
   states and callbacks. The former first-command point translates to about
   `(1148,500)`, but this is a planning hint, not an authorized input target
   until the displayed descriptor and client transform are measured.
4. Observe camera endpoints and selection recentering when the real arena
   permits scrolling. Record narrow/equal/wider-arena coverage honestly; a
   16-column battle cannot establish wider-arena rendering.
5. Verify hover/tooltips, turn banners and dialogs: drawing, hitboxes, cursor
   position and restored background must agree. Successful native input reads
   are required before treating cursor behavior as evidence.
6. Complete battle results or exit and verify the restored HD map. Capture all
   four map edges and all six map action-bar cells, then demonstrate real map
   selection/interaction. A command callback or nonblack map is insufficient.

Take two or three consecutive captures at static checkpoints. Run
`python tools/capture_tear_check.py <frame.png>` on saved frames and retain the
results; prefer a consecutive pixel-identical pair. Annotate screenshots with
stage, resolution, capture method, input method and verification result. A
partial or torn frame cannot prove complete wrapper composition.

## Evidence and cleanup

Write new expanded-stage manifests and reports under a unique
`C:\ClashTests\...` session directory. Bind executable, wrapper/configuration,
runner/probe, logs, captures, measured geometry, input method and observations
by hashes. Keep raw/proprietary material outside Git. Preserve failed attempts
and their cleanup outcomes instead of replacing them with successful runs.

Close or stop only the session-owned processes and verify their termination.
Report which criteria remain pending, including any manual observations not
performed. Keep centered regression evidence and historical hidden diagnostics
intact. This session does not authorize stable promotion or changing launcher
resolution defaults.
