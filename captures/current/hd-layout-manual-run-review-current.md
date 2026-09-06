# Prepared manual layout observation — not approved or executed

Prepared on 2026-09-05. The [plan](hd-layout-manual-run-plan-current.json)
has SHA-256 `fe5b8fe93c91b1cf1e4d1d6c4414e5342d06b69019ee6b57ba67ed215eb177b9`.
The earlier plan is [preserved](../archive/hd-layout-manual-plan-20260905-before-dpi.json)
as a superseded diagnostic; it must not be executed.

The candidate is the 800×600 `-combinedui-validation` executable under
`C:\ClashTests\hd-completion\layout-manual-20260905-111700`, with SHA-256
`0A75CF35F42EFE1E44FBA1AC4031EAAE5323CDFF51AA19D261C36C5BB84691C2`.
The plan binds its local proxy, configuration, 50 starting asset/settings files,
observer source, probe, interpreter, and x86 CDB. All required files are local;
the original executable remains untouched.

## What the proposed session would do

- Run for at most 15 minutes, with bounded cleanup afterward. Start a visible
  game window and a background x86 CDB observer in the isolated workspace.
- Allow the proxy's normal `ShowWindow` and `SetForegroundWindow` activation.
  Set native-DPI compatibility only for the owned debugger/game process chain;
  measure awareness and require a physical 800×600 client before capture.
- Observe the user's real input and capture the game client from the screen.
  Find one pixel-stable pair for each of two states; failed attempts are retained,
  so there may be more than four raw captures. The game window must stay unobscured.
- Save logs, frame sidecars, and process/window identity receipts under
  `C:\ClashCaptures\hd-layout-manual-20260905-prepared`. The game may update its
  private settings/cache. Stop only this session's verified candidate and debugger.

The observer does not inject mouse/keyboard input or force a route/callback.
The user would load a map, select a unit, and hold the normal selected-unit cursor
over empty central terrain until the first capture pair finishes. Next, hover
the first relocated command icon near `(640,544)` until the second pair finishes,
then click that icon once after the observer's prompt. Keep the same unit selected.

## Remaining boundary

No approval record exists and no manual session has run. The root
[agent guide](../../AGENTS.md) requires fresh explicit approval for visible/manual
runtime, foreground manipulation, and live capture. Approval must bind this
exact plan and cannot be inferred from a template or an older run.

The [combined geometry run](combinedui-layout-geometry-hidden-current.json)
`cdb-surface-dump-20260905-124215` on 2026-09-05 now passes the hidden layout,
surface, and 166-record byte checks on this exact candidate SHA. It observes
the relocated hit-scan anchors and the last panel descriptor's redraw accepted
at clip width 800, with one synthetic call returning at the saved ESP. This
resolves the missing geometry observations through a bounded forced redraw/list
scan; it supplies no click callback, manual input, or visible composition proof.
The [earlier run](combinedui-layout-hidden-current.json)
`cdb-surface-dump-20260905-122508` remains failed for missing hit-scan/redraw
observations; its report has not been replaced.

Before requesting the session, review the unfinished partial-edge terrain
rendering work when choosing the candidate. The geometry pass covers neither
those strips nor the proposed manual observation. A changed candidate or producer
requires a regenerated plan and matching approval. This proposed layout
observation does not replace the five separate manual-input targets, full
combined-candidate acceptance, or an explicit promotion decision.
