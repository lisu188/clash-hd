# Primary publication works; a later quantity label remains uncentered

The [1024x768 checkpoint](../../captures/current/modal-primary-initial-1024x768-20260919.json)
records the first completed bounded capture of recipe `owned_modal_primary_v1`,
stage `-completehd-modalprimary-validation`, on 2026-09-19. Candidate SHA-256 is
`bee7db23414bc7831d32af05ad03d04f800aa795c7af66db1bc1e7b4c9ad11b8`.
The host, complete initial/final traces and primary memory-query audit pass.
**Primary composition still fails:** the quantity text `250` is drawn in the
top margin, outside the centered native screen.

The [1920x1080 checkpoint](../../captures/current/modal-primary-initial-1920x1080-20260919.json)
independently passes the same bounded capture checks with candidate
`042e1681aa24d8a42f8391e2c8c7faf68fa32f47ab94551dfb52e164ab240b13`.
Its native canvas is centered at `(640,300)`, but the quantity text remains at
the original coordinates. Its cursor also lies outside the centered canvas;
cursor pixels require their own backing/state oracle and must not be treated
as quantity text or excluded through an invented mask.

## Evidence and scope

The run is retained at
`C:/ClashCaptures/hd-completion/modal-primary-initial-1024x768-20260919-a`.
Its source snapshot is
`C:/ClashCaptures/completehd-integration-20260919/source-snapshot-modal-primary-initial-1024x768-a`.
The checkpoint binds all 50 source files, candidate/manifest/probe identities,
raw files, query ledgers, host decisions and cleanup receipts.
The 1920x1080 run and snapshot use the corresponding `1920x1080` paths;
their independent artifact hashes are bound in that checkpoint.
The prototype, checkpoint helpers and full pixel diagnostic are additionally
preserved byte-for-byte under
`C:/ClashCaptures/completehd-integration-20260919/initial-checkpoint-prototype-archive/`.
Its 18-file manifest SHA-256 is
`4a97a200cf29329153e9743704d0440d7bcbf5a579e93c84743e90d72525eef4`.

This is the untracked, snapshotted `modal_primary_cached_capture_v1` prototype:
one completed barracks presentation with three paused native/physical/primary
captures. It is distinct from the original checkout's concurrently developed
`owned_modal_primary_capture_v1` protocol, which observes four separate
composition checkpoints. Do not exchange their packets, sources or receipts.
The prototype uses exact source reconstruction, thirteen adapter observers,
ordered twelve-slot validation and the fresh v2 primary query ledger.
An independently found slot/placeholder ordering gap was fixed before this
run; its earlier source and failing synthetic mutation remain preserved.

All three captures are identical, including the primary palette. The native
640x480 canvas is centered at `(192,144)`. Physical matches the centered native
canvas and cleared margins exactly. Primary contains all twelve portrait slots,
the correctly centered placeholder wall and five modal button artworks. Those
artworks do not prove button callbacks or manual controls.

The [1024x768 pixel diagnostic](../../captures/current/modal-primary-text-placement-1024x768-20260919.json)
measures 231 nonzero palette indices in the top margin, within the exclusive
rectangle `[564,53,593,64)`. Of these, 227 render nonblack and four use a black
palette entry. No pixels were excluded as cursor pixels. The physical mirror
has zero nonzero indices outside its centered canvas. This local comparison
identifies the misplaced label; it is not a complete primary composition
oracle.

Inspection uses the actual cached-primary capture
`capture-1/primary.png`, rendered with its captured palette. Left, right and
bottom outer margins are clear. The top margin contains the misplaced quantity
label. Ordinary-map borders and six action cells are not applicable to this
modal frame. No visible desktop capture or input injection was performed.

The host exited successfully only for the bounded capture claim. Cleanup
confirms absence of both retained game/debugger identities, closed handles and
closed hidden desktop. Root postflight confirms the original executable, all
15 live saves, four isolated saves, isolated assets, planned files and all 50
sources remained unchanged. Native exit/destruction, ordinary selection,
other castle routes, visible/manual input and release acceptance remain open.

## Remaining native text boundary

The original call at `00432C66`, file offset `00032066`, has bytes
`E8 E5 94 FD FF` and calls `UI_DrawTextFmt` at `0040C150`. It follows the twelve
slot copies. The native code selects primary device `0051D4C0` and font 5,
then passes six cdecl arguments: left 545, right 613, y 53, alignment 3,
format pointer `004EFC3A` (`%d`), and the quantity loaded from
`[[00532150]+1B6]`. Return at `00432C6B` cleans 24 stack bytes.

These native coordinates explain the observed top-margin text. A further
correction must translate only this authenticated primary-only call while the
owned modal canvas is active, preserving the other arguments, registers, flags
and calling convention. It belongs to a new validation stage; do not change
the current primary recipe or retrofit its result into a composition pass.

The [memory-ledger integration review](MODAL_PRIMARY_LEDGER_INTEGRATION_REVIEW.md)
separately identifies provenance work for the richer four-checkpoint host.
Its pixel oracle and cursor backing observations are the intended composition
validation path. The old failed D/F primary runs remain unchanged.

## Aggregate checkpoint

The [2026-09-19 aggregate receipt](../../captures/current/aggregate-refresh-20260919.json)
preserves the completed run against source commit
`b39f9bd3d4ecf566eaa80aa7798cb36ef4fe6282`: **154 of 167 checks passed**,
with exit 2 and all thirteen failures retained. Its framed batch reports 620
successful tests, one skip and three failed suites. Failures include missing
historical artifacts, pending manual/endurance evidence, an unclassified-source
guard, a long fixture path, two builder output-boundary fixtures, and the old
primary fixture's 600-second timeout. The full report and all 331 regenerated
tracked reports are preserved outside the repository with pre/postflight
bindings; no source file changed during that run.

Later focused fixes are separate results. In particular, PR #88 partitions
the inherited-blitter fixture and passes all nineteen test groups within the
existing suite deadline. It does not change the retained aggregate failure or
establish a passing aggregate on the newer source revision.
