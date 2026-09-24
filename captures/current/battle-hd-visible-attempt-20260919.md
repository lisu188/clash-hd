# Expanded battle visible attempt — September 19, reviewed September 24

The approved 1280x720 session stopped before battle readiness. It supplies
startup and cleanup evidence, but no passing visible battle, input or lifecycle
evidence. The candidate remains validation-only.

The exact candidate SHA is
`7D04FE9005515DAD4E618DF507103946265D7E2A6421287281C1FC5F112D1E47`, stage
`gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-castlecenter-all-battlehd`.
The presenting proxy SHA is
`B4CF172509083066EEE011FDB866F9A07C6CC4FA1F0CE53EC1F90E28CB5A28B1`.
Candidate bytes and the original executable remain unchanged.

## Recorded outcome

The session ran from 2026-09-19 11:39:30 UTC to 11:54:30 UTC under x86 CDB,
using the isolated game directory under
`C:\ClashTests\battle-hd-visible-20260919`. The native acquisition call was
executed. Its mouse HRESULT was `80070005`; no successful device-read record
followed. The disclosed forced menu/load setup reached the loaded map.

CDB then stopped on a first-chance `80000003` exception at `0046E6DF` on worker
thread `7ac4`, immediately after startup breakpoints were disabled. The displayed
instruction was the restored native Sleep call, `2e ff 15 c0 a5 4e 00`. A queued
worker breakpoint after disabling is consistent with these observations; the
cause has not been reproduced independently. Two startup commands also failed:
`expr /s masm` and `.radix 16`.

The exact game PID was 31856, owned by debugger PID 31180. Sky enumerated the
unique isolated candidate window. A subsequent activation/capture request did
not return a result before the conversation interruption. No live screenshot
was saved, no OS click was recorded, and no manual input was observed.

The controller reached its 900-second deadline and stopped both retained
processes, with no cleanup errors. Neither process remained on the September 24
read-only check. The receipt's `failure: null` means no host exception was
recorded; `acceptance_passed: false` is the runtime result.

## Source repair and evidence limits

The standalone probe now leaves all three worker Sleep sites uninstrumented,
uses `.expr /s masm` and `n 16`, and checks that every breakpoint enable/disable
reference names a declared breakpoint. It retains only the reviewed main-thread
startup Sleep skip. No general breakpoint-exception suppression or input
acquisition bypass was added. The repair is source-checked; a fresh runtime has
not yet demonstrated that battle entry succeeds.

The new launch controller binds the exact candidate, proxy, configuration,
approval, unchanged private save, probe and producer. It reconstructs the probe
before launch, rejects reparse-point paths and scopes cleanup to retained process
identities. Window actions and screenshots are handled separately by the
approved computer-use controller.

All four frame edges, the six command descriptors, sidebar artwork, targeting,
dialogs, camera behavior and restored-map input remain unverified by this
attempt. There is no image to tear-check. Earlier hidden screenshots keep their
separate evidence classification. The presenting proxy does not establish final
GOG-wrapper composition, and a source merge does not promote the stage.

## September 24 verification

All 16 focused battle, patch, launcher and documentation suites completed
successfully. Their default optional-tool skips are explicit. Separate runs
with the installed x86 tools and original executable passed 835 core scenarios,
all 17 HUD tests and all 10 cursor tests. The new probe/controller fixtures
passed 10 and 7 tests respectively; actual-file reconstruction checks 64 exact
spans. Both new suites are included in Windows/Linux source-only CI, with
platform-dependent mocks explicitly skipped where unavailable.

The first optional cursor invocation supplied a nonexistent `cdb.log` filename.
Its failure log is retained. Repeating it with the existing
`cdb-surface-dump.log` passed without a test or evidence change. The machine
summary preserves both outcomes. No new game execution was part of these
checks.

The [machine-readable report](battle-hd-visible-attempt-20260919.json) records
the actual emitted markers, exact artifact hashes, process identities and
cleanup result. Raw logs and private game material remain outside Git.

The prior [hidden follow-up](battle-hd-followup-20260919.md) still reports 7/7
helper diagnostics and 12/14 forced lifecycle checks. The broader aggregate
result and its unrelated failures are preserved there; this attempt does not
replace them with a pass. That aggregate was not rerun for this probe/controller
follow-up.
