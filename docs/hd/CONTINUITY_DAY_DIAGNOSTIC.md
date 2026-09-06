# Bounded native day-transition diagnostic

Status: **v3 observed a native day increment and banner exit, then timed out
without the forced call's return or a surface. The v4 run directly observed
eight held-left-button release tests and stopped at its diagnostic bound.
The separate v5 query-result control was approved and completed on 2026-09-05.
It reached the native day-call return and captured a surface, but its strict
continuity result failed. The separately approved v6 run also completed a
native day return and surface, but failed strict input-trace pairing**.
The existing three-advance campaign probe and its accepted evidence remain
unchanged. This adds an independent investigation of the missing day transition.

The combined mode-0 attempt `cdb-surface-dump-20260905-115726` emitted
`DAYDIAG_CONTRACT_FAIL route_entries` and a debugger syntax error at `q;`,
without `DAYDIAG_CONTRACT_PASS` or `DAYDIAG_START`. It supplies no day or
banner-wait proof. The v3 native predicates use explicit word/byte reads with
constants at most `FFFFh`, avoiding high-dword comparison ambiguity, and use
`q` without a trailing semicolon. Failed predicates also dump the checked
instruction spans. The actual generated probe has no already-armed breakpoint
inside those spans. The header layout and zero-padding checks are preserved.
The failed capture is retained; no cleanup PID receipt is manufactured for it.

The v3 combined mode-0 run `cdb-surface-dump-20260905-121022` passed the native
contract. Active slots were `(1,1,1,1,0)`. Calls 1-3 returned players 1, 2, 3;
call 4 logged a native day increment `1→2`, player 0, and the day-branch join.
Its banner test changed from EAX 0 to EAX 1 and logged banner exit in mode 0.
Both device reads returned `8007000C`; the later button bytes `87h/EDh` do not
establish a genuine input event. No forced-ack marker appeared. The run lacks
call-4 return, full-day-return, post-day-redraw, and surface markers. Repeated
or unpaired input trace lines remain disclosed errors, not silently removed.

The timeout sample again lies in DirectInput polling, with unreliable stack
unwinding. Source identifies a narrower next observation: the banner calls
`Render_Begin` at `004609D0`, which waits for both button bits to clear using
the routines labeled `DD_IsFlipping` and `DD_IsLost`.

The v4 mode-0 run `cdb-surface-dump-20260905-123426` directly entered that
release routine with caller return `0040AA06`. It logged eight left-button
tests returning EAX 1, flags 3, and button bytes `D1h/F0h`, then intentionally
stopped with `DAYDIAG_OBSERVED_RELEASE_INPUT_WAIT`. It did not override the
queries or return from the native next-player call. This establishes the
release wait for this run; it does not retroactively classify the July timeout.
The [v3 report](../../captures/current/continuity-day-v3-observation-current.json)
retains six input-trace pairing errors and 38 failed-HRESULT observations.
The [v4 report](../../captures/current/continuity-day-v4-observation-current.json)
retains 20 failed-HRESULT observations with no parser errors. Both have genuine
process-identity/cleanup receipts, and neither proves a complete day return.

The approved v5 control `cdb-surface-dump-20260905-130340` logged the native
day `1→2`, then overrode one left query at left test 8 and one right query at
right test 1 in the same release-loop iteration. It used no banner override.
The release returned with the expected ESP, followed by next-player return 4,
`DAYDIAG_FULL_DAY_RETURNED`, post-day redraw and the matching 480000-byte
surface. The outer surface harness and all 166 candidate byte records passed;
exact game/debugger PIDs 33576/37368 were observed live and then absent.

The [original strict v5 report](../../captures/current/continuity-day-v5-control-current.json)
is preserved as failed. Its raw trace repeats a mouse-call marker after the
release return; the exact cause is unproven because that trace lacks thread/
stack identity. The producer left its input breakpoints active beyond the
release phase. The parser also incorrectly expected mode 2 after release-only
overrides; only the banner override consumes mode 1 into mode 2. Correcting
that parser rule cannot remove the real overlapping-call failure.
The [corrected-parser recheck](../../captures/current/continuity-day-v5-control-recheck-current.json)
recognizes the full controlled-query return/surface sequence but still fails
on that overlapping input call. All 22 failed-HRESULT observations remain.

The v6 producer physically disables input breakpoints 87-91 at the verified
release return, emits `DAYDIAG_INPUT_TRACE_END phase=release_wait`, then
disables release breakpoints 92-95. Wrong-stack returns fail before the end
marker. This bounds tracing to the investigated phase; it does not deduplicate
or reinterpret the old log. All sixteen producer fixtures pass. Native call,
byte checks, and override limits are unchanged.
The user's subsequent "Approve debugger runs" message authorized the
[prepared v6 run](../../captures/current/continuity-day-v6-control-run-review-current.md).
Run `20260905-135344` returned native day 1→2, used one left and one right
release-query override with no banner override, and closed the release trace
correctly. All 166 bytes and the outer surface gate passed; live game/debugger
PIDs 33656/11392 were subsequently absent.
Its [strict report](../../captures/current/continuity-day-v6-control-current.md)
still fails: line 265 repeats the mouse return after call 263 and return 264
during advance 2. All 21 failed-HRESULT observations remain. Thread/stack
identity is needed to investigate the duplicate; neither it nor the earlier
failed trace is discarded. The [screenshot audit](../../captures/current/action-bar-screenshot-audit-current.md)
also finds no complete action-bar cells in the post-day 800×600 capture.

## What the archive establishes

The [2026-07-14 raw log](../../captures/archive/cdb-surface-dump-20260714-075917/cdb-surface-dump.log)
records player returns `0→1→2→3`, then a fourth `TURN_CALL` without a return.
Its [summary](../../captures/archive/cdb-surface-dump-20260714-075917/summary.json)
records a 900-second timeout on stable SHA
`5E162FA81DF59533E0B99A0DCBC9EA24280DBEC46411AE871E968D6536C08B33`.
The [timeout sample](../../captures/archive/cdb-surface-dump-20260714-075917/timeout-stack.log)
has main-thread EIP `0047BFD1`, inside the routine labeled `Time_Sleep`;
the raw log ends at its entry `0047BFD0`. The debugger explicitly reports
unreliable stack unwinding. Neither artifact records a day increment or the
caller of that poll. A fourth player advance is not necessarily a day wrap:
`nextPlayer` cycles five player slots, skipping inactive slots.

The historical assertion that a DirectDraw wait caused this timeout is **not
established**. Source inspection also shows that several function names are
misleading:

- `0047BFD0` polls DirectInput state: mouse/keyboard device-vtable calls at
  offset `+24h` request 16/256 bytes; failed reads can trigger acquisition at
  `+1Ch`. It is not an operating-system sleep routine.
- `004608F0`, labeled `DD_IsFlipping`, tests bit 0 of the supplied object's
  `+2Ch` field. `00460A50` derives that field from the mouse-button bytes
  `005451C0` and `005451C8`.
- The human-turn banner waits at `0040A93C` for that button test to return
  nonzero, pumping input otherwise. This supplies a concrete input-wait
  hypothesis; the archived trace does not prove that this loop was entered.
- `nextPlayer` increments the 16-bit day at `gameData+222F6h` on wrapping
  player order. `0040AB44` is immediately after the increment;
  `0040ABB9` joins the day/no-day branches after daily processing.

These findings were checked against the user-owned `C:\Clash\clash95.asm`, SHA
`B298E8C85086F542EBC8B02C26904019AA8278D531CBF02A88D785170CBB4436`.
The source text and game binaries are not added to the repository.

## The next experiment

Use the new [diagnostic extra probe](../../probes/cdb/continuity/clash95_continuity_day_diagnostic_extra.cdb)
alone, with the canonical 800x600 base probe. Both the protected stable stage
and the combined UI validation stage preserve its native hook instructions.
The extra probe checks complete call/branch instructions before arming its
breakpoints. It does not hash the candidate: bind its log to the outer harness
summary and a matching stage/resolution/candidate-SHA byte report. Its contract
marker explicitly declares that external identity prerequisite.

The combined 800x600 reference is SHA
`0A75CF35F42EFE1E44FBA1AC4031EAAE5323CDFF51AA19D261C36C5BB84691C2`
from the [166-record byte report](../../captures/current/combinedui-validation-patch-stage-current.json).
The historical stable SHA above remains a separate comparison, not evidence
for the combined candidate. Read-only inspection of the known original SHA
`500055D77D03D514E8D3168506BD10F67CD8569BCC450604FF8192F46CDAF3AE`
confirmed the diagnostic instruction bytes; source selection confirms that
neither stage patches those spans.

The diagnostic calls native `nextPlayer` at most five times, with two seconds
of map activity between returns. This shorter cadence is deliberately distinct
from the archived long campaign run. It preserves general registers, flags,
and the original stack pointer. It does not snapshot the extended floating-point
or SIMD register state; these forced calls are a diagnostic mechanism rather
than an ordinary end-turn input path. A matching return address alone is insufficient:
only a return with the saved ESP is accepted, so nested map redraws cannot be
mistaken for completion of the injected call. Initial player 0 must be active,
and the accepted day increment must return to player 0, matching the base
probe's player-0 visibility interpretation. It never writes the game's day,
player, button, or visibility fields. Verified PE-header padding at
`00400300..0040034F` and the synthetic return address are debugger-only
modifications, disclosed in the log. The original section table ends at
header offset `280h`, and `SizeOfHeaders=400h`; all 80 scratch bytes must be
zero before use. A preliminary fixture exposed that the original PE header
starts at `70h`, so extending old DOS scratch through `7Fh` would be invalid.
The new layout check and zero-padding gate fail closed before any writes.

Default mode 0 observes the native path after each forced call. It records the five active/controller
flags, native day increment, branch join, banner entry/test/exit, and the first
16 input-poll call/return samples per advance. At eight unacknowledged banner
tests it emits `DAYDIAG_OBSERVED_BANNER_INPUT_WAIT` and quits. That intentional
stop is diagnostic evidence, not a passing surface/continuity run. Calls that
block inside a device/other routine remain bounded by the outer 180-second
harness timeout; timeout by itself is never classified as a DirectDraw wait.

The v4 extra leaves only its route-entry breakpoint enabled during startup.
Input tracing is armed immediately before a forced next-player call and
physically disabled after 16 complete polls or the call's return. Logging
conditions alone did not remove the globally hot v3 breakpoints; their possible
timing overhead is not evidence that they caused the observed timeout.

After banner exit, v4 arms release-routine entry, left/right result tests, and
its exact caller return at `0040AA06`. It observes at most eight release-loop
iterations and stops with `DAYDIAG_OBSERVED_RELEASE_INPUT_WAIT` if either button
predicate remains true. It never writes button fields, changes those predicate
results, or bypasses the release routine. A return requires the entry ESP plus
four, and is separate from the eventual next-player return. The historical v4
mode 1 controlled only the separately disclosed single banner acknowledgment.
Current v5 keeps the same mode-0 observation behavior and extends mode 1 as
described below; the v4 observation is not evidence for those new overrides.
The extra owns decimal breakpoint IDs 80-95; these do not overlap the canonical
base's automatically assigned low IDs. The explicit ID syntax follows
[Microsoft's breakpoint documentation](https://learn.microsoft.com/en-us/windows-hardware/drivers/debuggercmds/bp--bu--bm--set-breakpoint-).

Run only from a separately prepared, isolated user-owned game work directory
under `C:\ClashTests`, including a private save folder and writable config/log
files. Do not point `-WorkDir` at `C:\Clash`, or share it with another live run.
The probe contains no explicit save calls, but native next-player processing
may still write game state. Preserve the original saves and prior slots 11/12.
Candidates, wrapper binaries, game assets, and captures remain outside Git.

After the private workdir and byte prerequisites are verified, with no other
run using that workdir or candidate directory, the bounded combined command is:

```powershell
$diagStage = 'gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-combinedui-validation'
& .\scripts\cdb\run_cdb_surface_dump.ps1 `
    -InputExe 'C:\Clash\clash95.exe' `
    -WorkDir 'C:\ClashTests\hd-completion\continuity-daydiag-combined-observe\workdir' `
    -CandidateDir 'C:\ClashTests\hd-completion\continuity-daydiag-combined-observe\candidate' `
    -OutRoot 'C:\ClashCaptures\hd-completion\continuity-daydiag-combined-observe' `
    -Python 'C:\Users\andrz\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' `
    -Cdb 'C:\Program Files (x86)\Windows Kits\10\Debuggers\x86\cdb.exe' `
    -Stage $diagStage -Resolution '800x600' -UseDdrawProxy `
    -LoadSlot 0 -FastForwardStartAnims -RequireGameplay -RunSeconds 180 `
    -ExtraProbeTemplate '.\probes\cdb\continuity\clash95_continuity_day_diagnostic_extra.cdb'
```

The workdir in this example must already contain private copies of the required
user-owned assets, saves, and writable configuration. Use a fresh directory for
each attempt. In particular, do not reuse another task's live geometry workdir.
The harness rebuilds a fresh candidate from the original; it has no prebuilt
candidate parameter and refuses to overwrite an existing candidate filename.
Do not pass the combined executable as `-InputExe`: the patcher requires the
known original and original bytes. Verify the resulting summary SHA against
the combined reference before accepting any markers as combined evidence.

The pure renderer accepts this canonical extra probe at 800x600 for both
stages. It rejects extra probes at larger resolutions; this diagnostic has no
larger-resolution visibility or UI recipe. A stable comparison uses the stage
without `-combinedui-validation`, its stable SHA, and another private directory.
The harness defaults to a hidden desktop and pins proxy presentation off.
The diagnostic's input entry is the second instruction `0047BFD1`, avoiding
the startup probe at `0047BFD0`. No visible window, OS input injection, or
manual-input claim is part of this experiment.

## Separate query-result control and acceptance

Only after reviewing mode 0, a separate controlled run may use an external
copy of the same probe with its **single** initialization `ed 00400304 0`
changed to `ed 00400304 1`. Record that copy's SHA, use a new isolated workdir
and candidate, and retain the mode-0 log. At the observation limit this mode
can override one zero banner-button result to EAX=1 at `0040A943`. It emits
`DAYDIAG_FORCED_BANNER_ACK` and consumes the option (internal mode 2), so a
later banner cannot silently receive another acknowledgment. It changes no
DirectInput bytes and skips no native day-processing routine. This is a
debugger-forced control experiment, never real or manual input proof.

The v5 control additionally permits one left and one right release-query
override to EAX 0 at release-loop iteration eight. Each
`DAYDIAG_FORCED_RELEASE` records the original result and actual per-button
test count: a first right test after eight held-left tests is still right
test 1. Global consumed flags survive later release entries, preventing a
second override for either button. No button, day, player, or visibility
field is written. The extra scratch dword at `0040034C` holds these flags
and the bounded right-test count.

The exact prepared [v5 plan](../../captures/current/continuity-day-control-run-plan-current.json)
is retained unchanged, including its preparation-time unapproved status.
The later [approval receipt](../../captures/current/continuity-day-control-approval-current.json)
records the user's explicit authorization for this 180-second hidden run.
It supplies no visible/manual authorization or promotion decision.

Interpret matching evidence conservatively:

- Repeated zero banner tests, completed input calls, and zero button flags
  demonstrate the observed banner/input wait. Failed input-read HRESULTs must
  be reported; stale input buffers cannot establish a genuine button event.
- An input call without its return narrows the unfinished call. Determine its
  actual target module from the captured pointer and timeout state; do not
  relabel it as DirectDraw from a misleading function name.
- Other timeouts remain unclassified until a concrete native caller/COM target
  is observed. Compare paired entry/return markers and native state.
- A full bounded day transition needs, in order, `DAYDIAG_NATIVE_DAY_INCREMENT`,
  its same-advance `DAYDIAG_AFTER_DAY_BRANCH`, a true `DAYDIAG_NEXT_RETURN`,
  `DAYDIAG_FULL_DAY_RETURNED`, `DAYDIAG_POST_DAY_REDRAW`, and the matching
  800x600 surface dump with no AV/invalid markers and verified cleanup. If a
  banner was entered, require its observed exit too. Bind everything to the
  candidate SHA, stage, private workdir, generated-probe SHA, and mode.

A passing generic surface summary alone does not satisfy that sequence.
Mode 1 can establish only a controlled-query/forced-native-call day transition. Neither mode
proves sustained multi-day play, endurance, visible composition, manual input,
or stable promotion. Keep all existing three-advance proof claims bounded.

## Repo-only verification

`tools/test_continuity_day_diagnostic_probe.py` executes the probe's own branch
conditions and writes against synthetic state. It covers active-player skipping,
16-bit day rollover, register restoration, nested-return exclusion, later
surface release, missing/wrong-player wraps, eight observations, and one forced
acknowledgment. It also checks every byte predicate with corruption negatives,
instruction boundaries, stage overlap, renderer restrictions, and the unchanged
campaign-probe SHA. When present, the pinned user-owned disassembly and original
are read only to check native semantics and PE-mapped bytes. It launches neither
game nor debugger and writes no runtime evidence.
The v4 fixtures also exercise late arming and actual trace-disable commands,
both bounded release predicates, absence of button mutations, and the release
routine's exact return-stack check.
The v5 probe suite has 15 focused tests, including independent actual
right-test counts, preserved global override limits, and unchanged mode 0.
The offline summary suite has 20 tests covering exact phase, per-button count,
prior-result, same-iteration effective-zero, and stack-return requirements.
Missing or malformed evidence fails; repeated trace errors remain disclosed.
