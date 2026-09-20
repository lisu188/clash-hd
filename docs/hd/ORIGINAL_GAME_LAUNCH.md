# Actual original-game launch baseline

The original `clash95.exe` now has actual execution evidence on a disposable
Windows 2022 runner with the complete GOG runtime from `lisu188/clash-assets`.
This baseline is separate from synthetic CPU fixtures, nonexecuting PE admission,
and every HD validation recipe. No game or wrapper bytes were changed.

## Observed runs — 2026-09-20

The [40-second run](../../reports/original-game-launch-20260920-a.json), Actions
run `35494633605`, resumed the real original entry point and captured animated
intro frames. At all four samples the owned game process remained alive and its
visible `Clash` window was not reported hung. Its original EXE and all sixty
reference files remained unchanged. The eight PNGs, process observations and
cleanup results are retained in artifact `10600008273`.

The [180-second run](../../reports/original-game-launch-20260920-b.json), Actions
run `35494871354`, progressed naturally from the intro to the main menu, without
keyboard, mouse, debugger or message injection. The first menu sample was at
80 seconds; 120, 160 and 180 seconds retained the same menu. Both BitBlt and
PrintWindow produced identical decoded pixels at all four menu samples. The
six observed menu labels are load, campaign, exit, options, multi player and
credits. No menu item was selected, and no map was loaded.

The output window is 1024x768, but its nonblack artwork bounds are
`[192, 144, 832, 624)`: the original 640x480 menu, with black margins on all four
sides. This is not evidence of an expanded HD viewport. The final BitBlt pair
passes the advisory tear check as `clean_stable_pair`. There is no ordinary-map
action bar on the menu, so map-control acceptance is not inferred.

All sixteen second-run captures and the untouched runtime JSON are in artifact
`10599728961`, ZIP SHA-256
`a435725ef23040134170b72bc950adeb24bd6e9893782c1f2a57039c49fdf667`.
The runtime JSON SHA-256 is
`b8a855a47d980d2af654976c89f7167231ed9110e25db1be6dadf2ac1e602dae`.
Every original asset was rechecked afterward. Only `gfx/cache/m6316ed.s32` was
created in the disposable working copy; that proprietary cache is not uploaded.
Owned Job Object termination, process exit and handle closure were verified.
The collected matching Application error-event list is empty; that bounded
observation is not a guarantee that every possible error source was checked.

The initial Actions run `35494587418` failed workflow YAML parsing before any
Windows execution. It remains failed. Moving the colon-containing pip command
into a YAML block fixed provisioning, not game behavior. Neither later success
nor the additional menu interpretation rewrites an earlier runtime receipt.

## Runtime harness

`tools/run_original_game_smoke.py` validates exact runtime paths, sizes, hashes,
file count and total size, including original EXE SHA-256
`500055d77d03d514e8d3168506bd10f67cd8569bcc450604ff8192f46cdaf3ae`.
It requires a new output outside the checkout and reference assets, copies the
complete runtime there, and recreates the original empty cache/save directories.
The reference installation is never a working directory for a game process.

The real process is created suspended, assigned to an owned kill-on-close Job
Object, and then resumed. Its path, retained handle, creation time, PID, thread
and periodic window state are recorded. Each owned-window capture runs in a
five-second-bounded child and verifies both PID and process creation time.
PrintWindow can block, so it never runs unbounded in the observation host.
Finally, the harness terminates only its owned job/process and verifies exit.

By default the CLI is a nonexecuting dry run. Actual execution requires
`--execute` plus the caller's explicit `--approval-text`, native Windows and a
bounded observation interval. The capture-worker CLI also requires approval.
A diagnostic zero exit means the attempt and cleanup completed, not that game
rendering or gameplay passed. The raw report retains `gameplay_verified=false`.

`.github/workflows/original-game-launch.yml` now separates ordinary offline PR
checks from actual execution. Its source-only matrix launches no game and takes
no live captures. Actual execution is **workflow_dispatch only**, requires
supplied approval text, uses the immutable asset commit
`84a1e4bcf131e6bb75b39fc5e10941dd0b801767`, and uploads only the evidence folder.
The temporary branch push trigger and current-conversation approval fallback
used for these two authorized runs are removed from the final workflow.

## What is not established

This proves the complete original runtime can reach the menu in the tested
Windows environment. It does not prove menu input, a playable campaign, sound
output quality, save/load continuity, an expanded HD viewport, the widget-stage
lower-frame correction, modal lifecycle, endurance or stable promotion.

The next runtime checkpoint is a deliberately scoped map-entry/input test and
then the separate source-authenticated HD candidate with its matching capture
consumer. Original-stage observations cannot substitute for that candidate's
loaded-byte, render, input or original-artwork checks. Classic/800x600, protected
stable-stage recipes and historical HD failure receipts remain unchanged.
