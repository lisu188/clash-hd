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

`--mode foreground-diagnostic` retains fixed campaign-menu coordinates only.
Timed dismissal and fixed ordinary-map selection/movement clicks have been
removed. It does not acquire the native-phase leases described here, and no
ordinary-map acceptance is inferred from it. Historical results and the
separate OS-input and visible-capture approval boundaries remain unchanged.

Hidden execution requires explicit approval text, verified user-owned assets,
a source-bound proxy, a new output directory below `C:/ClashTests`, and the
project disk reserve. `OwnedHiddenProcess` creates a private desktop and owns
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

Runs C/D/E/F freeze their producer files under each external `source/` directory
before execution; source identities, generated C++ and compiled host are
retained per run. A/B retain source hashes and generated host producers, but have no
equivalent `source/` tree. Do not reconstruct missing historical sources and
label them original captures. The old deleted `C:/ClashCaptures` and
`C:/ClashTests` evidence has not been restored by these new, uniquely named
runs. Raw captures, assets and binaries remain outside Git.

## Focused verification and remaining proof

Use the interpreter discovery in the [handoff](AGENT_HANDOFF.md#start-safely).
These commands are portable fixtures or a dry run; they launch no game:

```text
python -B tools/test_ordinary_map_startup.py
python -B tools/test_ordinary_map_phase_host.py
python -B tools/test_ordinary_map_phase_client.py
python -B tools/test_ordinary_map_input_plan.py
python -B tools/test_ordinary_map_observation.py
python -B tools/test_resolution_playability.py
python -B tools/resolution_playability.py --mode hidden-controlled --profile modalwidgets --resolution 1920x1080
```

The driver suite has 40 passing fixtures at this checkpoint, including its 18
previous cases, both prepared-candidate schemas, same-held-lease revalidation,
genuine state-transition requirements, the exact ordinary previous-index store,
false native predicates and cleanup after consumed leases. Source fixtures and the separate synthetic pause-engine
proof remain distinct from game runtime.

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
