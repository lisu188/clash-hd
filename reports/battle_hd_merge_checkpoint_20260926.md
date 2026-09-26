# Expanded battle source checkpoint, September 26

The 1280×720 validation candidate is
`0EDEF38DAC3C5036C6012ADDE248BC57736273CC1BBCBB9FD05E5867A1946CA0`.
Its completed September 24 hidden run confirms that the turn banner now uses
the relative-input helper while a battle is active. Input and full lifecycle
acceptance remain pending. This checkpoint does not promote the stage.

The [matching JSON](battle_hd_merge_checkpoint_20260926.json) records exact
candidate, original, wrapper, probe, capture, build and source-snapshot hashes.
Its retained artifact references were verified on September 26. Runtime
observations below belong to September 24, not a new run.

## Candidate and source checks

All 283 patch records passed expected-byte verification, two builds were
identical, and the original executable remained unchanged. Compared with
candidate `99D92…C7E87`, 104 bytes differ within the two scoped input helpers;
native hook bytes and rendering/combat bytes are unchanged. Both helpers now
recognize the default render owner `004617A0` only while the battle pointer is
nonzero, in addition to the existing battle owner `0042E8B0`.

The root task reran focused fixtures on September 26: 1,249 relative-input
scenarios, 1,186 cursor-bounds scenarios, 835 existing core scenarios, nine
headless-probe tests and 19 frozen edge-controls tests passed. These results
were checked in console output; no separate test log was retained. Earlier
visible-probe, controller and focused-suite evidence retains its original date
and does not establish a new visible run.

## Completed headless diagnostic

Run `20260924-094304` used the hidden desktop and memory-only DirectDraw proxy.
The harness completed the capture without a logged runtime error, access
violation or timeout. Owned-process cleanup passed with no remaining process
IDs. The generated probe and retained source snapshot bind the observation to
the exact candidate; the preparation manifest is retained unchanged as
`prepared_not_run`, while the separate harness summary and log establish its
subsequent execution.

Runtime is bound to the archived producer and generated CDB. A subsequent
source-only portability correction accepts the exact reviewed LF and CRLF
dependency hashes and records the actual source hash. That correction was
not used for this retained runtime and does not change its evidence identity.

The read-only observer recorded 21 correlated events across the three cursor
calls, checking caller, thread, stack position, instruction order, buffer
identity, relative arithmetic and native clamping:

| Cursor call | Observed helper branch | Requested | Returned | Device-state HRESULT |
|---|---|---|---|---|
| Turn banner | Relative, owner `004617A0`, active battle | `(576,360)` | `(576,385)` | `8007000C` |
| Modal | Relative, owner `0042E8B0` | `(576,360)` | `(601,1)` | `8007000C` |
| Results | Relative, owner `0042E8B0` | `(576,360)` | `(576,385)` | `8007000C` |

Each failed native device-state read left its 16-byte target buffer unchanged.
The observed arithmetic therefore does not establish valid input deltas.
The unchanged lifecycle parser reports **11/14** checks passing; banner, modal
and results exact cursor-return checks still fail. The additive observer is
read-only, but the inherited startup and lifecycle fixture still force initial
acquisition results, route setup, callback invocation and dismissal. All forced
actions remain listed in the JSON. This is finite diagnostic evidence, not
natural input or a soak.

The [earlier 99D92 report](../captures/current/battle-hd-headless-followup-20260924.md)
separately preserves its camera 7/7 result and banner-branch defect. Those
measurements are not relabeled as runtime evidence for the new executable.

## Capture and aggregate limits

The retained 1280×720 hidden software surface shows map terrain, a partial
upper-left frame and the top-right minimap. The upper and left borders do not
form complete outer edges; the right outer edge and bottom frame are absent.
All six ordinary-map bottom-right action cells are absent. Complete map
composition and restored map input therefore remain unproven. No obvious
horizontal shearing appears, but no visible tear-check or stable-pair result is
claimed. The hidden proxy can omit separately composed layers.

The aggregate refresh attempt in the frozen checkout at
`5151f6765dbae51f30629d7828182d9d65125d50` did not produce a completed fresh
result: stdout remains empty and the final execution JSON is absent. Its
existing report is dated September 6 and is explicitly historical. The earlier
interrupted attempt's failure record is also preserved. No fresh aggregate
pass or fresh aggregate failure count is claimed.

Visible validation remains pending at the user's request. Headless operation
is the default, the launcher stays at 800×600, and the protected stable stage
is unchanged. No manual-input proof or stable promotion is implied by this
source checkpoint.
