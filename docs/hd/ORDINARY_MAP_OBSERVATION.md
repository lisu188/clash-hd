# Ordinary-map paused observations

The observation components provide bounded read transactions for the
[measured input planner](ORDINARY_MAP_INPUT_PLAN.md). They remain outside the
game driver. No real-game runtime, army selection, movement, click-to-callback
success, manual-input proof or stable promotion is established in this
checkpoint, and no screenshots were generated.

## Components and ownership

- `tools/ordinary_map_observation.py` decodes the strict planner schema through
  an injected exact-memory reader. It opens no process and controls no debugger.
  Image globals/code pointers relocate; measured GD and surface pointers do not.
  Native signed sentinels and byte/WORD/DWORD widths are preserved.
- `tools/ordinary_map_pause_host.py` exposes `render_source(base_source)`, an
  opt-in source transform of the existing owned DbgEng harness. Its compiled host
  enables the pause/read/resume mailbox only with the extra control-directory
  argument. The normal harness is not silently replaced.
- `tools/ordinary_map_pause_client.py` supplies `PauseClient` and the Windows
  `RetainedTarget` reader. The retained handle binds reads to the expected path,
  creation time and candidate file hash. Its PE32-header check does not replace
  the host's loaded-code authentication.
- `tools/ordinary_map_observation_session.py` composes those components.
  `ObservationSession(client, read_exact, candidate=candidate, stack_indices=None).read()`
  returns `{snapshot, receipt, host_transaction: {paused, resumed}}`.
  Observation sequences increase even on failure. It returns a result only
  after decoding and the matching resume acknowledgment both succeed.

A host `ready` acknowledgment means executable/entry readiness, not
ordinary-map readiness or a held pause. Only the matching `paused`
acknowledgment authorizes reads. Session and one-use lease tokens, ordered
request numbers, retained process/thread identity and the same Windows clock
bind the transaction. The host verifies the native break event and holds the
debuggee for at most 20 seconds. It resumes only for the matching next request;
expiry or protocol failure enters owned cleanup rather than preserving a usable
stale lease.

This protocol has no cursor, input or game-state-write operation. Decoder
relocation fixtures do not expand the inherited host's executable-authentication
policy. The foreground input adapter and hidden-desktop input transport remain
separate work.

## Decoder API and receipts

```python
observe(
    read_exact,
    candidate=candidate,
    identity=identity,
    sequence=sequence,
    lease=lease,
    check_lease=client.check_lease,
    stack_indices=None,
)
# {"snapshot": strict_planner_observation, "receipt": read_receipt}
```

`read_exact(address, size)` must return immutable bytes of exactly that size or
raise. `check_lease(lease)` must synchronously return `None` only while the same
live host lease is held, or raise; boolean/async returns are rejected. It runs
before reads, between full passes, and after final comparison. The caller
authenticates the candidate, owner and host. A JSON flag or digest alone does
not authenticate them.

The lease schema is `clash95_paused_read_lease_v1`, with exact fields `schema`,
`lease_id`, `paused`, `pid`, `creation_filetime`, `image_base` and
`candidate_sha256`. Identity must match the separately supplied candidate and
lease. The observation remains `clash95_ordinary_map_observation_v1`; all record
keys and native source fields are in
[the planner's schema and read map](ORDINARY_MAP_INPUT_PLAN.md#caller-and-schema-contract).

`stack_indices=None` scans all 500 native records. A bounded unique list/tuple
reads only requested army records and newly discovered neighboring occupants.
Terrain, player/visibility and occupancy use bulk reads; contiguous armies are
coalesced. Empty native army sentinels are recorded as omissions. Occupancy must
match its measured army coordinates; unknown, duplicated or empty-record
occupants fail. Discovery does not recursively expand neighboring armies.

Every collected byte range is repeated, with additional anchor comparisons.
The `clash95_ordinary_map_read_receipt_v1` receipt contains the lease, candidate,
observation digest and ordered read-set addresses, sizes, purposes and SHA-256
values. It records requested, empty and newly discovered army indices without
embedding raw memory. Short/unmapped reads, partial aliases, changing bytes or
pointers, lease loss and exhausted budgets fail closed.

The synthetic all-500 fixture measured 544,086 unique bytes, 1,103,120 bytes
including repeats and 60 exact-read calls. Hard limits are 600,000 unique bytes,
2,000,000 total bytes and 2,000 calls. These bounds do not extend the host
deadline or establish real-game timing.

## Evidence at 2026-09-26

The decoder's 32 portable fixtures pass, including sparse memory, relocation,
native widths/sentinels, small worlds, newly occupied neighbors, replacement
armies sharing an index, consistency/lease failures and direct planner state
validation. Independent source review found no actionable defects and verified
the native packed layouts and fixed X-major strides. The session adapter's ten
portable fixtures separately check the composed transaction. These are source
and supplied-state checks.

Three retained reports describe actual x86 DbgEng runs against a marked
eight-byte synthetic counter loop:

| Report | Observed result and scope |
| --- | --- |
| [Attempt a](../../reports/ordinary-map-pause-engine-20260926-a.json) | Both cases failed before useful lease evidence. The readiness acknowledgment became visible before the buffered entry log marker; the log-flushing defect remains a failed attempt. |
| [Attempt b](../../reports/ordinary-map-pause-engine-20260926-b.json) | 2/2 cases pass after flushing entry output before readiness. `pause-resume-counter` observes a stable counter while paused and advancement after explicit resume. `expired-lease` rejects the expired lease and verifies target termination; host exit code 2 is expected for that failure-path case. |
| [Attempt c: current source](../../reports/ordinary-map-pause-engine-20260926-c.json) | 2/2 cases pass with the final fixture-reporting correction. Both rows observe executable entry, unchanged fixture bytes, retained-target exit and owned cleanup. Host, client, engine-fixture and inherited-harness source hashes match this checkpoint. |

The current report retains `game_runtime_executed=false`,
`fixture_runtime_executed=true` and `manual_input_proof=false`, with observed
entry and cleanup in both rows. The synthetic counter has no Clash surface;
its `REAL_PRIMARY_UNAVAILABLE` messages are not rendering evidence.

Each report binds the pause-host, client, engine-fixture and inherited smoke
sources plus the compiled C++ source hash for that attempt. Attempts a and b
remain unchanged historical attempts; b is an initial pass for its recorded
sources. Their fixture-runtime flag was unconditional. Attempt c derives that
flag from observed executable entry, so a setup failure cannot claim execution;
its current source hashes were checked on 2026-09-26. None of these counter
reports exercises the native-map decoder or full observation session against
a game process.

Previously recorded game artifacts under `C:/ClashCaptures` and `C:/ClashTests`
were deleted and remain unavailable at their recorded paths. These reports and
temporary synthetic tests restore none of those raw captures, source snapshots
or candidate bundles. Recheck current free space and the project reserve before
recreating bounded game evidence.

## Safe verification and remaining integration

These commands run portable fixtures only:

```text
python -B tools/test_ordinary_map_observation.py
python -B tools/test_ordinary_map_pause_client.py
python -B tools/test_ordinary_map_pause_host.py
python -B tools/test_ordinary_map_observation_session.py
```

The engine fixture is a separate opt-in Windows lane, not a default repository
check. Its retained results are not instructions to launch a debugger or game.

The playability driver still needs to adopt these transactions, replace timed
dismiss/fixed map clicks, validate the actual click boundary, and bind each
planned selection/movement transition to native input evidence. A completed
read/resume transaction describes a past paused interval; it neither authorizes
nor proves later input. Preserve the separate screenshot, frame/action-bar,
manual DirectInput and promotion requirements in the root agent guide.
