# Ordinary-map native runtime driver

As of 2026-09-26, `tools/resolution_playability.py` integrates the measured
planner, paused decoder and owned native-phase controller. The fifth retained
game run proves one controlled native selection dispatch: the real handler
accepted its left-query predicate and returned naturally, and the selected
index changed from -1 to 0. The subsequent decoder's existing panel-ownership
contract rejected the state, so full selection acceptance failed and movement
was not sent. The corrected contract now follows native single-squad behavior;
E remains a historical failed acceptance record, not evidence of an HD panel
defect or a fresh successful read under that correction. The sixth run stopped
before input writes because the strict native-button guard rejected existing
input; it did not exercise the corrected post-selection read.
Complete rendering, manual input and promotion remain unproven. The
[driver checkpoint](../../reports/ordinary-map-driver-20260926.json) retains
all six attempts and their exact identities; overall `passed=false`.

## Modes and ownership

`--mode hidden-controlled` is the default; without `--execute` it only describes
the selected launcher case. Actual hidden execution currently accepts the
Complete HD and modalwidgets profiles on Windows. It uses the exact launcher
candidate and a source-bound, non-presenting DirectDraw proxy. An optional
`--prepared-build` receipt must match the current launcher case, original and
candidate checksums, profile-specific metadata schema, source hashes and the
exact executable/manifest/probe inventory. It does not accept a presentation
override or overwrite `C:/Clash/clash95.exe`.

The explicit `--prepared-matrix-candidate EXE` option selects the separate
[ordinary castle-entry matrix recipe](ORDINARY_CASTLE_ENTRY_MATRIX.md). It is
available only in hidden-controlled mode and cannot be combined with
`--prepared-build` or `--native-present-bounds`. The default launcher selection
and receipt interface remain unchanged. A dry run describes the matrix case;
it does not read or authenticate the supplied bundle:

```powershell
python -B tools/resolution_playability.py --profile modalwidgets --resolution 1920x1080 --mode hidden-controlled --prepared-matrix-candidate C:/ClashTests/new-matrix/matrix.exe
```

Before hidden execution, `prepared_matrix_candidate` reconstructs the expected
candidate once in memory from the authenticated original. It requires exact
executable bytes, the complete canonical CLI-produced `.candidate.json`, and
the matching CRLF `.cdb` verifier. Schema, revision, stage, profile, resolution,
typed ancestry, admission, edits, source inventory and probe contract must all
match. Duplicate JSON fields, linked/reparse paths, stale sources and changes
during authentication fail closed. The final audit rechecks all three bundle
members and their sources without rebuilding.

The result records distinct `prepared_matrix` provenance; it does not invent a
launcher receipt. The actual matrix SHA and stage populate the same strict
six-field planner context used by held observations and measured selection and
movement. This option does not execute the generated castle verifier or add a
castle transition to the ordinary-map driver. The preceding September 30 matrix fixtures
pass all 60 methods without skips, including 17 artificial-bundle methods.
Actual matrix bundle compatibility and game runtime acceptance remain separate
verification requirements.

The distinct `--prepared-small-world-candidate EXE` option selects the
[bounded complete successor](SMALL_WORLD_INPUT.md). It supports the same two
complete profiles and six existing resolutions in hidden-controlled mode.
It rejects combinations with the launcher receipt, prepared matrix candidate
or presentation override. A dry run selects the case without opening,
authenticating or executing the supplied bundle:

```powershell
python -B tools/resolution_playability.py --profile modalwidgets --resolution 1920x1080 --mode hidden-controlled --prepared-small-world-candidate C:/ClashTests/new-small-world/small-world.exe
```

Before execution, the adapter reconstructs the exact original-bound successor
once and authenticates all three canonical CLI bundle members, complete typed
metadata, original and source bytes, and file identities before and after that
reconstruction. This binds the matrix ancestry, six guards, helper targets,
castle gate, merged relocations and final CRLF verifier. Sources and bundle
members must be regular nonlinked files; missing, stale, duplicate-field or
changed documents fail closed. The final audit rechecks bundle, source and
original identities without another reconstruction.

The result records `prepared_small_world` provenance, separate from launcher
and matrix receipts. The existing six-field planner context, held native
phases, selection transition, occupied source/destination cells, AP charge and
natural handler-return requirements remain in force. This option authenticates
the `.cdb` file but does not execute it; `probe_executed=false` is retained.
The [prepared-driver checkpoint](../../reports/prepared-small-world-driver-verification-20260930.json)
passes 81 methods without skips: the preceding 60
remain unchanged and 21 new artificial-bundle methods cover both profiles and
all six selectors, exact reconstruction, typed tampering, file/source identity
changes, final audits and bounded-world decoder/planner transitions.
Artificial-bundle fixtures establish adapter behavior, not actual serialized
bundle compatibility, successful game input, final rendering, lifecycle,
manual proof, endurance or promotion. Disk and runtime approval requirements
below still apply.

The separate [actual bundle checkpoint](../../reports/prepared-small-world-bundle-verification-20260930.json)
passes CLI-to-adapter compatibility for modalwidgets at 1920x1080. The guarded
producer wrote all three members outside the repository; the adapter used one
actual original-bound reconstruction and the final audit used none. The
38,798,089-byte bundle, original and complete source inventory remained
unchanged. Candidate SHA is
`657faf66ca2858f9b07dd7a2d9c96bd1853821c0e23e6f7042ec448f747b64fe`,
matching the original-backed CPU checkpoint. No game, compiler, debugger or
screen capture was invoked by this bundle check. Other actual serialized
profile/resolution bundles and all runtime acceptance remain unmeasured.

`--mode foreground-diagnostic` retains fixed campaign-menu coordinates only.
Timed dismissal and fixed ordinary-map selection/movement clicks have been
removed. It does not acquire the native-phase leases described here, and no
ordinary-map acceptance is inferred from it. Historical results and the
separate OS-input and visible-capture approval boundaries remain unchanged.

Hidden execution requires explicit approval text, verified user-owned assets,
a source-bound proxy, a new output directory below `C:/ClashTests`, and the
project disk reserve. Fresh checks cover checkout and output volumes before
directory creation, after asset verification, immediately before compilation,
immediately before copying, and before owned launch. Copy preparation reserves
the full verified runtime bytes plus the existing 128 MiB allowance; launch
requires the remaining 128 MiB. Each comparison requires strictly more than
ten percent free, uses integer arithmetic, and reports the failing phase/path.
Concurrent writers can still consume space between observations, so periodic
disk checks and bounded cleanup remain necessary. `OwnedHiddenProcess` creates a private desktop and owns
the host/debuggee job. The driver reads through a retained target handle and
checks process creation time, image identity and host ownership. Cleanup waits
for the retained target to exit and records host exit, an empty job and closed
handles. It uses no `SendInput`, foreground-window manipulation or desktop
screen capture. Captures are paused software surfaces from the private proxy;
they do not establish final wrapper composition.

The startup transform is deliberately controlled. Its 15 owned software
breakpoints bypass reviewed bootstrap delays/acquisition and menu predicates
to reach the native slot-zero loader. All retire at the real PlayGame entry,
`0x40B660`. The driver waits for both `OWNED_STARTUP_RETIRED` and
`REAL_PHASE_HUMAN` before requesting a gameplay lease. This startup evidence
does not prove genuine menu input. Runtime copies also create the manifest's
required empty directories, including `gfx/CACHE`, before launch.

## Held native boundary and action receipts

The composed host enables `native-phase-v1` explicitly. The generic pause host
and its strict native-break checks remain available unchanged; their mailbox
is not serviced concurrently with the phase mailbox. The phase controller
authenticates code anchors and owns its hardware breakpoints separately from
the startup software breakpoints.

It holds the first real human-loop entry at `0x40B0A0`, records the primary
thread and root ESP, and waits at most 20 seconds for the exact acquire request
before allowing the first poll. That entry stop is not itself a decoder lease.
Startup stays in the ordinary event path until this entry; it cannot become a
partially armed phase transaction. The controller then observes post-poll
`0x40B0D4` and holds the actual pre-dispatch CALL at `0x40B233`. Post-poll alone
is too early: another native poll can occur before that CALL. The held frame
must retain `ESP = root_esp - 28`. Read-only `REAL_PHASE_VIEW` diagnostics bind
the entry and caller-hold camera, cursor/shift, extents and native button data.

The Python driver scans all 500 army records for its initial plan. Before each
selection or one-cell movement it decodes again and revalidates the plan under
the **same still-held lease**. The click binds the plan digest, action, fresh
validation and held acknowledgment. Only the measured point is sent; a stale
observation does not authorize a later click.

At that boundary the phase host may change only three native input DWORDs:
raw cursor X at `0x544CFC`, raw cursor Y at `0x544D00`, and the resolved left
button at `0x544D04`. Coordinates use the measured native shift. It checks old
values and readback, then resumes the original CALL. It does not invoke an
arbitrary routine, change EIP/ESP/registers, force a predicate, or write army,
selection, occupancy, movement or world state.

For an action receipt the controller must observe native dispatcher
`0x4084A0` with `[ESP] = 0x40B238`, the real left-query result at `0x4087E1`
after the call to `0x4608F0`, and the natural return to `0x40B238` with restored
caller ESP. A false or absent predicate remains a failed input result; the
controller does not force EAX to one. After return it clears a remaining
controlled left button and observes the next post-poll/pre-dispatch boundary,
issuing a distinct successor lease. The decoder then measures the resulting
state. Successful native dispatch alone cannot replace the planner's actual
selection or movement transition checks. Run E now supplies real call/query/
return evidence, but its later rejection by the panel-ownership contract still
prevents a full selection pass. Movement has no successful game-run evidence.
For this observed `0x4084A0` route the driver additionally requires
`after.previous_stack == before.selected_stack`. The state-only planner also
supports `0x408030`, which can preserve the previous index; that compatibility
does not relax the driver contract for the actual ordinary CALL.

The caller-created ASCII control directory contains `session.token` (32 lower
hexadecimal characters plus LF). Atomically replaced `phase-request.txt`
records are at most 256 bytes, with one canonical LF-terminated line:

```text
CLASH_PHASE_V1 <session> <seq> acquire <lease>
CLASH_PHASE_V1 <session> <seq> click <lease> <successor> <x> <y> <binding_sha256>
CLASH_PHASE_V1 <session> <seq> release <lease>
```

Sequence numbers start at one and advance exactly; lease identifiers are
one-use 32-character lower hexadecimal tokens. `phase-ack.json` is atomically
published, bounded to 4096 bytes, and uses `clash95_native_phase_ack_v1` with
statuses `ready`, `held`, `executing` and `released`. It includes retained
identity, controller-source SHA, request/lease identity, deadline, native
phase/frame, capture index, binding and observed dispatch/predicate/return
fields. `ready` is entry readiness, not a held ordinary-map read lease.

Each held lease and each native transition has a 20-second bound. Malformed,
stale, mixed-mailbox, expired or mismatched requests fail closed into owned
cleanup. Expiry never silently resumes a usable stale lease. A failed click
consumes the old lease; the driver releases only its current valid lease.
Held snapshots use indices `100 + 2 * action_index` and share the decoder's
native stop. Periodic window-enumeration captures are disabled in this mode.

## Actual small-world diagnostic — 2026-09-30

The [Run G checkpoint](../../reports/ordinary-small-world-input-20260930-g.json)
records actual hidden execution of modalwidgets1920 candidate `657faf66…7b64fe`,
with distinct prepared-small-world provenance and unchanged identities. The
existing user's hidden-control/debugger authorization is recorded accurately;
no OS or foreground input was performed.

One matched CALL/return/copy epoch records actual HRESULT `0x8007000c`, with the
16 local bytes unchanged. The native copy includes primary `0x95`, secondary
`0x97` and middle `0x06`; the later held caller observes resolved buttons `3`.
Measured selection planning and immediate revalidation pass, but the strict
pre-click guard rejects the existing data before controlled writes or dispatch.
There is no post-selection read, movement request or completed observation
interval. Host exit `2`, empty job, closed handles and retained-target exit are
verified. Overall acceptance stays failed.

The local Windows SDK's `dinput.h` defines this error as `DIERR_NOTACQUIRED`;
`DIERR_INPUTLOST` instead equals `0x8007001e`. Original routine `0x47BFD0`
reacquires only for INPUTLOST and does not retry the read. All outcomes reach
the native packet copy. Original caller `0x460A50` then consumes those fields
without a mouse-read success check. The
[recovered backend at `44928710`](https://github.com/lisu188/clash-disassembly/blob/44928710be14842127d9c581e2e67dfff2d65e09/src/media/0047AA90_0047C760_media_013.cpp#L1102)
and [original assembly](https://github.com/lisu188/clash-disassembly/blob/44928710be14842127d9c581e2e67dfff2d65e09/clash95.asm#L194599)
document those branches. These source files were inspected in the user's
separate checkout; that checkout is not a fresh-clone runtime prerequisite.

The current [controlled startup source](../../tools/ordinary_map_startup.py)
bypasses mouse Acquire at `0x47BD66` and keyboard Acquire at `0x47BDAE`, setting
EAX to zero and advancing past their failure checks. Ready flags therefore do
not establish device acquisition. Original mouse cooperative flags are
exclusive/foreground; natural `WM_ACTIVATEAPP` calls Acquire or Unacquire.
The next bounded diagnostic should authenticate actual activation and native
acquisition return values while preserving startup retirement and pre-click
rejection. Do not clear the copied buttons or fabricate a successful read.

The only screenshot is a paused pre-action 1920x1080 private-proxy surface.
Its matching map-owner record passes; all four structural bands and all six
action cells match. Footer background matches only 464/4,860 pixels and remains
unverified. Full frame acceptance and required three-sample control coverage
fail. The broad black area retains no final-wrapper proof. No castle, battle,
manual-input, endurance or promotion acceptance follows.

The old reserve decision preceded long bundle authentication and compilation.
Concurrent space loss was detected after this attempt completed, so no process
was stopped by the attempted preparation stop. The
[cleanup checkpoint](../../reports/ordinary-small-world-static-cleanup-20260930.json)
preserves the failed run and removes only exact DATA/AVI/STRATEG duplicates
from its confirmed inactive work copy. Saves, settings, original/candidate,
proxy, sources, compiler diagnostics, control receipts and all captures remain.
Future launches from that work copy require reconstruction from the complete
retained reference. Its temporary bare-reserve recovery does not authorize a
new run without fresh full-copy and scratch headroom.

The [fresh-reserve fixture checkpoint](../../reports/ordinary-map-runtime-space-guard-20260930.json)
passes all 92 driver methods without skips, preserving the earlier 81 and
adding 11 checks. Tiny artificial assets and mocked native boundaries exercise
actual driver orchestration: drops during authentication stop compilation,
drops during compilation stop copying, and drops during copying stop launch.
Both volumes, exact threshold/budget equality and one-byte-above cases are
covered. These fixture results provide no new actual runtime acceptance.

## Native polling CPU contracts — 2026-09-30

The [standalone CPU fixture](../../tools/test_ordinary_map_native_poll_cpu.py)
executes the authenticated 154-byte polling body in artificial x86 memory with
modeled COM dependencies. Its [source-only receipt](../../reports/ordinary-map-native-poll-cpu-20260930.json)
keeps these branch checks separate from Run G's actual failed device read.
Success supplies a distinct packet; NOTACQUIRED copies the preseeded packet
without Acquire; INPUTLOST performs exactly one Acquire, then copies the same
packet without a read retry even when acquisition succeeds. X/Y and the three
zero-extended button fields retain their original ABI. With mouse enabled and
other devices disabled, final EAX is the middle-button byte, not the saved read HRESULT.

The fixture also covers disabled mouse input, saved registers, native stdcall
arguments and stack cleanup, and bounded writes. It does not load a game image,
call Windows input APIs, build a candidate, or observe a real device. Natural
activation/acquisition, selection/movement and final composition still require
matching runtime evidence. CI requires the pinned emulator and forbids skipped
CPU methods on both platforms; existing native acceptance remains unchanged.

## Native activation diagnostic preparation — 2026-09-30

The [read-only activation observer](../../tools/ordinary_map_activation_host.py)
is composed into the existing owned hidden driver. It authenticates seven
original instruction spans against candidate disk and loaded bytes, arms one
primary-thread hardware execute breakpoint before the first GO, and follows
native `WM_ACTIVATEAPP` transactions. Together with the existing phase observer,
the maximum is four hardware breakpoints. It adds no activation requests,
input writes, startup overrides or native acceptance changes.

Each transaction records the actual startup-retirement flag, retained WndProc
arguments and caller, backend CALL/return, and each enabled device's COM
CALL/return. Native execution order is mouse then keyboard. Ready flags govern
skips; enabled joystick state fails closed because that path is outside this
observer's scope. Each device HRESULT is sampled before the next call can
replace EAX. The outer EAX is the final enabled device's value, or the backend
pointer if both devices are skipped; it is not an aggregate acquisition result.

[The strict offline consumer](../../tools/ordinary_map_activation_trace.py)
binds PID, primary TID, creation time, image base, session and the activation
host's separate source digest. The driver derives this identity after loaded
code/entry matching, retained-target authentication and validated initial phase
readiness, before waiting for startup retirement. Its final diagnostic collector
therefore retains early startup failures even without measured action receipts.
Raw, paired and completed device returns stay separate; genuine partial returns
remain visible while impossible return addresses cannot supply HRESULT counts.

The existing host deadline bounds the observer. Each pending transaction has
at most 20 seconds and the finite cap is 16 transactions. Zero-event, missing,
rejected or unfinished traces remain incomplete. Reaching the WndProc RET
instruction is pre-return evidence only. A rotating breakpoint cannot establish
coverage of all activation events or nested callbacks. Diagnostic completeness
never proves input, selection, movement, final composition, manual proof,
endurance or promotion, and does not change `hidden_success`.

The [source checkpoint](../../reports/ordinary-map-activation-source-20260930.json)
passes 154 methods without skips: 18 host-source, 38 synthetic-log, six driver
integration and all 92 existing driver methods. The integration fixture retains
bound diagnostics through an artificial startup failure while input acceptance
stays false. Existing phase-host and driver-fixture bytes are unchanged. The
original was read only to verify its SHA and all seven spans. No local compiler,
debugger or game ran; no new device result or screenshot was captured. CI runs
all three new suites on Windows and Ubuntu and separately compiles the composed
x86 observer without executing it. These are preparation checks; actual natural
activation/acquisition still requires a fresh owned run with sufficient disk
reserve and matching runtime evidence.

## Actual attempts on 2026-09-26

All six used modalwidgets at 1920x1080, recipe
`owned_modal_widget_bounds_v1`, stage
`gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-completehd-modalwidgets-validation`,
candidate SHA-256
`baea13ce80c89d0f9369947881c187adcf9065ddaee5295978fdfea4f72ca5a9`.
The original and working original remained unchanged. The small tracked
[checkpoint](../../reports/ordinary-map-driver-20260926.json) binds each local
report, debugger log, generated host source/executable and capture hash.

| Retained report | Result and diagnostic boundary |
| --- | --- |
| `C:/ClashTests/ordinary-native-input-20260926/run-a/playability.json` | Failed before a useful map observation. Acquisition was requested during startup; a queued first-chance exception could not satisfy the strict native-break contract. Cleanup also exposed the invalid `Release` after `RemoveBreakpoint` lifetime handling. No click or snapshot was produced. |
| `C:/ClashTests/ordinary-native-input-20260926/run-b/playability.json` | Waiting for startup avoided the early acquisition. Missing `gfx/CACHE` exposed a native `fwrite` access violation at `0x475F96`; the host also hit the breakpoint-cleanup defect. The retained 1920x1080 menu surface is not an ordinary-map control audit. No action occurred. |
| `C:/ClashTests/ordinary-native-input-20260926/run-c/playability.json` | With the required directory and breakpoint lifetime fixes, all 15 startup breakpoints retired before human entry. The host held `0x40B233`, completed the real decoder transaction, explicitly released the lease and finished 110,125 ms with clean owned shutdown. Planning rejected the measured scene before any click. Overall `passed=false`. |
| `C:/ClashTests/ordinary-native-input-20260926/run-d/playability.json` | The new first-human-entry hold retained the saved camera `(10,17)` before the first poll. Planning and immediate revalidation selected stack 0 at measured point `(320,368)`, but the strict existing-button guard rejected the request before any controlled input writes or dispatcher receipt. Owned cleanup passed; the 110-second interval did not complete. |
| `C:/ClashTests/ordinary-native-input-20260926/run-e/playability.json` | With the same strict guard and additional read-only button diagnostics, native dispatcher `0x4084A0`, predicate 1 and return `0x40B238` were observed for stack 0's selection point. Selected index changed from -1 to 0. The next decoder's universal panel-ownership contract rejected the state, so movement was not sent. The host completed 110,407 ms and clean owned shutdown; overall `passed=false`. |
| `C:/ClashTests/ordinary-native-input-20260926/run-f/playability.json` | The corrected panel contract was present, but the caller-hold and pre-click diagnostics recorded resolved button 1, primary byte `f0`, secondary byte `04` at camera `(10,17)`. The measured target `(320,368)` had `raw_target_valid=1`; the existing-input guard rejected it before writes or dispatch. Sources and original/candidate identities were unchanged, and all owned cleanup checks passed. The interval and selection failed; no corrected post-action read or movement occurred. |

Run C observes a 100x100 world at camera `(36,17)`, no selected army, and 18
nonempty army records from the all-500 scan. The failure is
`no eligible friendly stack/cardinal pair in the measured records`. Its action
list is empty: no native click predicate/return, selected-army transition or
movement transition was proved by this run.

The two ordinary-map software captures, `run-c/capture/primary-00.png` and
`run-c/capture/primary-100.png`, each pass all six bottom-right action-bar cells
and the top, bottom, left and right structural frame bands. Both retain
`footer.exact=false` and black terrain. Frame continuity outside the separately
checked footer does not establish complete rendering. There are only two
samples, so the existing three-sample aggregate control gate remains false;
neither it nor the full driver passes. Hidden proxy limitations remain relevant
to the black area; this capture is not a verified final-wrapper defect or a
rendering pass.

Runs D/E retain camera `(10,17)` and show armies in the explored map area.
Run E's `capture/primary-102.png` shows selection brackets and the
`Light cavalry` footer. Its bound dispatch acknowledgment passes an independent
`verify_dispatch` check recorded in the checkpoint. This does not retroactively
change the raw driver's failed action: decoding stops with
`ObservationError: selected map/panel ownership is incoherent` before its
selection verifier can run. The paused state records `selected_stack=0`, but
panel word `0x514194` remains -1 and `lower_owner=0`. The successor lease was
explicitly released. There is no movement request or full selection pass.

Subsequent original-code review explains why this rejection is not a confirmed
HD panel defect: native `0x40A500` creates the lower panel only when
`Unit_GetSquadCount` is greater than one. Run E's stack 0 has one occupied slot
(type 5), for which panel -1 and lower owner 0 are expected. The universal
panel requirement in the recorded decoder therefore overconstrains this case.
The corrected contract uses the measured contiguous slot count, stopping at
the signed type -1 sentinel. A one-squad selection requires lower owner 0,
panel -1 and all ten slot flags zero; a dormant active pointer must remain
equal to its measured pre-action value. A multi-squad selection still requires
lower owner 1, matching panel index and its exact GD-relative active pointer.
The selected record must itself be measured; the decoder adds it when a
bounded read list omitted it. These source corrections do not alter the
frozen E report or manufacture a successful post-action read or movement result.

Every Run E capture passes all six bottom-right action-bar cells. The two
pre-action captures have zero mismatches on all four structural frame bands.
The post-action capture has 275 left-band mismatches at the cursor overlap
near `(4,324)`; top, bottom and right bands still have zero mismatches. This is
retained as a failed structural audit, not silently masked. Every footer audit
remains false. The visible bracket/footer response and native-dispatch receipt
are narrower findings than complete map/panel composition or input acceptance.

Run F's single `capture/primary-100.png` is a fresh 1920x1080 software capture.
All six action cells and all four structural frame bands match exactly;
`footer.exact=false` remains. This pre-action capture cannot prove the blocked
selection, and one sample cannot pass the aggregate control gate.

Source review of `clash-disassembly/clash95.asm` at `0x47BFD0` and
`0x47C01C`–`0x47C069` supports a hypothesis that a failed hidden DirectInput
backend read can leave input data uninitialized. The native `GetDeviceState`
call at `0x47C029` compares only against HRESULT `0x8007001E` before copying
stack X/Y/button fields; recovered C++ adds fallback behavior and is not the
authority for these original bytes. This may explain unexpected native
button/cursor values, but these runs did not measure the actual HRESULT. The
strict rejections in D/F were preserved; E's success at the native dispatch is not
evidence that hidden device reads are reliable.

## Read-only mouse polling preparation — 2026-09-30

The phase-host source now prepares a read-only diagnostic for the original
mouse `GetDeviceState` CALL at `0x47C029`, return at `0x47C02C` and completed
local-buffer copy at `0x47C065`. One rotating hardware breakpoint observes
these three stops only while awaiting post-poll/caller-hold boundaries, after
startup controls retire. Each epoch has the existing 20-second transition
deadline and a maximum of 64 paired polls; its breakpoint retires before the
held snapshot or controlled input action. This checkpoint is source and
portable-fixture preparation only. No September 30 game run or actual device
HRESULT has been measured, and the six September 26 failures remain unchanged.
The composed declarations keep the lease owner before startup and phase
controllers. Startup and phase checks both cover `0x47BFD0`; candidate code is
authenticated before startup installs its software breakpoint there, and all
phase byte comparisons remain exact. Loaded-byte readback after breakpoint
installation still needs a fresh bounded runtime check.

Each `REAL_MOUSE_POLL_V1` record uses
`clash95_native_mouse_poll_trace_v1` and binds the epoch/action, process/thread,
creation time, image base, retained root stack, controller SHA and session.
The host checks original code, the whitelisted caller and native COM arguments.
It saves the actual return HRESULT before an `Acquire` can overwrite EAX;
the native `0x8007001E` path falls through into the copy without another
`GetDeviceState` call. Before/after/copy-time 16-byte samples and all five copied
backend words remain diagnostic observations. Resolved buttons and raw cursor
coordinates are separately read snapshots.

The [offline consumer](../../tools/ordinary_map_input_poll_trace.py) binds every
record to an authenticated phase identity and rejects malformed, unmatched,
out-of-order or incomplete coverage. Zero observed polls cannot establish
coverage. Its `complete` flag describes trace structure, including paired
failed HRESULTs; it never establishes successful input, manual proof, gameplay
acceptance or promotion. Changes to the local bytes after return are reported
without relabeling the saved HRESULT. Telemetry adds no target writes and does
not change the controlled three-field input path or its acceptance checks.
The driver supplies identity from its retained-process phase client; supplying
a dictionary to the standalone parser alone does not authenticate a process.

Runs C/D/E/F freeze their producer files under each external `source/` directory
before execution; source identities, generated C++ and compiled host are
retained per run. A/B retain source hashes and generated host producers, but have no
equivalent `source/` tree. Do not reconstruct missing historical sources and
label them original captures. The earlier deleted castle/runtime bundles under
`C:/ClashCaptures` and `C:/ClashTests` have not been restored by these new,
uniquely named runs. The September 26 ordinary-run captures and producers are
retained separately. Raw captures, assets and binaries remain outside Git.

The [September 30 cleanup receipt](../../reports/ordinary-map-artifact-cleanup-20260930.json)
records removal of 228 exact duplicate DATA/AVI/STRATEG inputs, totaling
5,070,128,718 bytes, from the completed A–F work copies. The full reference,
manifests, raw failure captures, sources, compiled hosts and candidates remain
retained, with historical classifications unchanged. Reconstruct those static
inputs from the retained reference before any future launch of an affected
work copy. The ten-percent reserve was not restored; large artifact-producing
operations remain subject to the existing disk guard. Continue regular verified
cleanup after bounded completed batches without deleting unique proof.

The [September 30 synthetic CI failure](../../reports/ordinary-map-pause-engine-ci-20260930-failure.json)
retains a separate infrastructure failure at the first pause acknowledgment.
The target reached its authenticated native stop; atomic replacement of
`ack.json` failed with Windows error 5 and owned cleanup terminated the target.
The expiry fixture passed. The failing report remains unchanged. This is
synthetic debugger infrastructure, with no game or screenshot execution; it
does not alter the six September 26 game attempts.

The shared pause/phase publisher now retries only actual Windows access-denied
or sharing-violation failures while replacing the same flushed acknowledgment.
Its fixed one-second publication bound also honors any earlier active lease
deadline. Each attempt rechecks ownership, the session token, regular paths and
exact payload bytes; successful publication checks the destination file identity.
Other errors fail immediately. The native synthetic fixture holds a real reader
without delete sharing: one case releases it only after an actual retry marker,
and another holds it through bounded failure and verified owned-target cleanup.
These fixtures do not change game input, acknowledgment schemas or lease limits.

The [source-bound CI receipt](../../reports/ordinary-map-native-ci-verification-20260930.json)
retains [both native pause cases](../../reports/ordinary-map-pause-engine-ci-20260930.json),
[composed x86 compilation](../../reports/ordinary-map-phase-compile-ci-20260930.json)
and [both owned-descendant cleanup cases](../../reports/owned-process-ci-20260930.json)
from workflow run `36686641640` at commit
`be568ee10064f879c3ff2a05ca6ec43988208827`. The transient reader recovered
after a real Windows error 5 retry. The permanent reader remained open through
62 retries, publication expiry at exactly 1,000 ms, host exit 2 and verified
target cleanup. Counter pause/resume and lease expiry also passed. Raw producer
hashes match that commit, and both generated source identities replay locally.
The full observer compiled without being executed; no device HRESULT, game
input, screenshot or promotion proof is supplied by this synthetic checkpoint.

## Focused verification and remaining proof

Use [Development and verification](DEVELOPMENT.md#python-and-dependencies) for interpreter discovery.
These commands are portable fixtures or a dry run; they launch no game:

```text
python -B tools/test_ordinary_map_startup.py
python -B tools/test_ordinary_map_phase_host.py
python -B tools/test_ordinary_map_phase_client.py
python -B tools/test_ordinary_map_input_poll_trace.py
python -B tools/test_ordinary_map_input_plan.py
python -B tools/test_ordinary_map_observation.py
python -B tools/test_resolution_playability.py
python -B tools/resolution_playability.py --mode hidden-controlled --profile modalwidgets --resolution 1920x1080
```

The September 26 driver suite recorded 40 passing fixtures, including its 18
previous cases, both prepared-candidate schemas, same-held-lease revalidation,
genuine state-transition requirements, the exact ordinary previous-index store,
false native predicates and cleanup after consumed leases. Source fixtures and the separate synthetic pause-engine
proof remain distinct from game runtime.
The September 30 preparation passes 201 ordinary-map portable fixtures, with
the two native engine cases skipped locally, and all 43 driver fixtures.
The ordinary-map total includes 14 pause-host source fixtures, 26 phase-host
source fixtures, four engine report fixtures and 36 poll-trace fixtures.
The three new driver cases bind
the trace to phase identity, reject identity changes and keep diagnostic
coverage separate from gameplay acceptance. CI compiles the composed x86 host
without executing it; successful compilation supplies no actual device or game
evidence. The real reader-lock cases run only in the opt-in synthetic Windows
lane; portable source checks do not establish their native execution.

The next run must exercise the corrected native conditional panel-ownership
contract, retain a fresh held observation for each click, and prove full
selection and subsequent movement transitions. The native dispatch proof in E
does not satisfy those state requirements. Hidden backend reads, the black map
area, footer and cursor/frame overlap need their own diagnosis. Resolution
coverage, small-world integration, castle/interior/battle lifecycle, manual DirectInput,
visible composition and promotion keep their existing separate requirements.
`ordinary_controlled_input_passed` describes only the controlled native lane;
`native_input_passed`, `os_input_executed`, `manual_input_proof` and
`promotion_ready` remain false in these runs. The protected stable stage and
launcher defaults are unchanged.
