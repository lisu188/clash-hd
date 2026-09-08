# Minimap scroll and old-outline erasure validation

Updated 2026-09-06 from local source and saved evidence. The controlled
hidden-CDB producer, strict parser and dedicated host are implemented, tested,
and have [three bounded runtime passes](../../captures/current/framed-minimap-scroll-runtime-current.md).
All actual runs began at `(0,17)`: 1024x768 moved to `(11,17)` and 802x602
requested `(90,93)`, reaching the native far-world clamp `(89,92)`. All 90 and
88 informative old-only outline pixels, respectively, were repaired correctly.
A third 1024x768 run moved one tile vertically to `(0,18)` and repaired all
64 informative old-only border pixels. All six screenshots pass the four
frame bands, footer and six action-bar cells.
The [checkpoint](../../captures/current/framed-minimap-scroll-runtime-current.json)
binds original artifacts, source/candidate hashes and retained-handle cleanup
receipts. The 802 far-corner map area is black in the software capture; this
does not prove unseen terrain contents. The protected stable stage, existing
probes, parsers, captures and current candidate bytes remain unchanged.

The optional framed minimap candidate already has bounded single-frame outline
evidence. For example, the [802x602 report](../../captures/current/framed-minimap-v1-802x602-viewport-20260906.json)
records world `(100,100)`, scale 2, scroll `(10,17)`, rectangle
`(582,56)..(607,75)` and 88/88 matching perimeter pixels. That proves neither
scroll callback execution nor removal of an earlier rectangle. The new test
must observe changed native scroll and compare the old border with the actual
clean minimap backing, including pixels whose natural index is already `4C`.

## Source and candidate contract

Use exactly `build_framed_candidate.build_candidate(..., minimap_viewport=True)`
and its current source/byte/relocation checks. The stage is
`gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-combinedui-partialtiles-initialpaint-framed-validation`.
The optional flag is essential: the same stage name alone does not identify
whether the new minimap outline is installed.

Original `C:\Clash\clash95.exe` SHA-256:
`500055d77d03d514e8d3168506bd10f67cd8569bcc450604ff8192f46cdaf3ae`.
The private `C:\Clash\clash95.asm` source was checked at lines 20455–20549
(scroll), 19820–19927 (backing repair/outline), 23718–23793 (unit centering),
and 146632–146638 (the misleadingly named `DD_IsFlipping`). The assembly file
SHA-256 is `b298e8c85086f542ebc8b02c26904019aa8278d531cbf02a88d785170cbb4436`.
Do not track or copy either proprietary file into this repository.

| Native site | File offset | Authenticated bytes / meaning |
| --- | --- | --- |
| `0040B0E0` | `00A4E0` | `E82B2B0000`: actual native caller of `0040DC10`; return `0040B0E5` |
| `0040DC10` | `00D010` | First 17 bytes `5351525657B8D84C5400E8D12C050085C0`: save five GPRs, gate object in EAX, call and test |
| `004608F0` | `05FCF0` | `F6402C010F95C025FF000000C3`: test bit 0 at `[EAX+2C]`, return Boolean |
| `0040DC1F` | `00D01F` | `85C0`: first instruction after the real gate call; observe before TEST |
| `0040DCB0` | `00D0B0` | Native `83EE09`, framed `83EE<TX>`: horizontal clamp |
| `0040DCDA`, `0040DD24` | `00D0DA`, `00D124` | Native `83EA07`, framed `83EA<TY>`: both vertical clamp branches |
| `0040DCEC` | `00D0EC` | `E80FAA0000`: actual full redraw call to `00418700`, EAX set to 1 immediately before it |
| `0040DCF1` | `00D0F1` | `5F5E5A595BC3`: five pops and RET after the full redraw, also the rejection/no-op exit |
| `0040D62E` | `00CA2E` | `E8AD4EFFFF`: backing blit through `004024E0`; return `0040D633` |
| `0040D633` | `00CA33` | Original `A1E4025200`, now the source-bound optional minimap hook; do not require original bytes in the patched candidate |
| `0041699C` | `015D9C` | `E8BF6BFFFF`: native full-tile tail calls minimap repair `0040D560` |
| `00418700` | `017B00` | Original `53515256575583EC18`; installed framed entry is a reconstructed hook, not these original bytes |
| `00406FA0` | `0063A0` | `51525583EC708B15F002520085D2740F`: existing authenticated paused map-update boundary |

The complete original scroll span `[0040DC10,0040DD2B)` is 283 bytes, SHA-256
`efc84e280a1845d15f51687db427964017c8d1ba8e3c8b40adcf7964303bb576`.
For the saved 1024x768 optional candidate SHA
`69899e07f70dde2094264be694300e00c7a778f1391ac7797b74c59c56ee1ce0`,
the same span SHA is
`b8edfb906e3325a9164ef01b6e92f86b088bcbb1d9262c8b434c688a457fe66f`;
its three changed clamp instructions are `83EE0F`, `83EA0B`, `83EA0B`.
Reconstruct every other resolution instead of copying this candidate-span hash.
The original 362-byte `0040D560` span hash remains
`a23f3e93b580fbb57849333ab89efa35c0bdde61b1809f94a48ed51a34f11733`;
its installed right-clamp and optional outline hooks require candidate bytes.
Verify loaded spans before installing software breakpoints over those bytes.

`0040DC10` has no register/stack arguments. It reads gameData `005202E4`,
world W/H at GD+`222E0/222E4`, scroll at GD+`222E8/222EC`, minimap selector
GD+`23EC7`, enabled flag GD+selector*`58F`+`2230F`, origin words
`00523344/00523346`, scale byte `00523F54`, raw mouse dwords
`00544CFC/00544D00`, and shift byte `0054512C`. The gate object is
`00544CD8`, so bit 0 is read from `00544D04`. Its IDA name does not establish
a graphics flip operation; the authenticated machine code is the contract.

The native target is the **top-left scroll**, computed using signed division:
`((raw_mouse >> shift) - minimap_origin - 7) / scale`. There is no half-view
subtraction in this callback. Unit-centering helper `0040FAD0` is different:
framed recipe immediates at VA `0040FB01/0040FB18`, file `00EF01/00EF18`,
are `TX//2`, `TY//2`. Do not use that helper to claim minimap callback proof.

## Bounded controlled sequence

1. Use a new private candidate/proxy/output directory and an isolated workdir,
   exact input/candidate/source manifests, the non-presenting proxy and an
   explicitly approved hidden debugger plan. No visible fallback, OS input,
   injected mouse event, asset mutation, or executable patch is needed. Require
   the ordinary player-0 map owner `0040AD40`, lower/post owners zero and tile
   callback zero for this experiment. Confirm native memory map dimensions,
   vtable `0050EE24`, bounded pixels, valid world/scroll, enabled minimap and
   source-selected scale (4 when world area <=2500, otherwise 2).
2. Reach the existing fourth-update stop with the canonical initial-map trace
   unchanged. Validate it and the current minimap observer before continuation.
   Save the complete raw log prefix, its exact byte length/hash, packet/probe,
   before-frame raw/PNG/palette, map header, and clean backing raw/header at
   `poi(0052334C)`. The backing must be a distinct native memory surface of
   `(worldW*S+14,worldH*S+14)`, with its own bounded, tightly packed pixels.
   Reject aliasing with map/primary. Bind actual PID, creation time, candidate,
   thread, EIP/ESP and pause state; a saved old screenshot is not this before
   frame.
3. Begin a separately declared observation phase only after that accepted
   prefix is immutable. Disable the now-complete initial PTILE producers and
   the original update breakpoint before controlled continuation; do not edit
   their source or remove any logged event. New non-PTILE phase markers and
   independent parser must preserve all subsequent output. Inventory IDs:
   existing optional minimap observers use 80/81, so reserve only verified free
   IDs above them. If observing the same emitted full-status addresses, declare
   the explicit phase transition from the disabled old breakpoints; never leave
   two active producers at one address. Save/declare any reused debugger
   pseudo-registers. The existing single-frame audit must consume the immutable
   before prefix, not be weakened to accept later draws after its close marker.
4. Record the intended target and original native mouse words, GPRs, EFLAGS and
   stack state. For target `(sx,sy)`, derive native logical mouse
   `(Mx+7+sx*S, My+7+sy*S)`, then raw coordinates by the observed shift. Admit
   only an explicitly bounded shift whose signed raw values fit and round-trip
   exactly; require coordinates inside the current minimap footprint. Write
   only these two native mouse dwords, with exact old/new disclosure. Do not
   write scroll or world dimensions. Invoke the source-authenticated CALL at
   `0040B0E0`, stopping at its exact return `0040B0E5` before the next native
   call. This is deliberate debugger-controlled dispatch, not a natural click.
   Observe the real gate at `0040DC1F`; if it returned zero, an explicitly
   declared one-shot EAX=1 override can make this a controlled gate test. Record
   the prior value and override separately. Never manufacture a successful
   observed gate or treat forced dispatch as manual input proof.
5. Require one ordered callback entry, real gate result, native scroll state at
   `0040DCEC`, admitted framed full convergence/presentation, full return at
   `0040DCF1`, then callback return at `0040B0E5`. The after state must differ
   from the before state for a pan case. Require the same thread and exact stack
   relations: if caller ESP before `0040B0E0` is C, callback entry is C-4,
   gate return and full CALL/return are C-24, and final return is C. Use emitted
   framed metadata (`full_status_to_caller_before_call=148`) to bind full-status
   ESP to the observed full CALL's C-24, rather than reuse initial-phase stacks.
   Return EAX is incidental; do not use it as callback/redraw success.
6. At the exact final return, keep the debugger paused. Verify actual scroll,
   owner, target/header/backing identity and state again; snapshot the full
   memory map and backing once each. Restore only the two saved mouse words and
   saved controlled-call context while paused, with a restoration receipt; do
   not resume ordinary gameplay in this bounded experiment. Preserve both raw
   states, all phase log bytes and failure outputs. Stop the exact debugger
   first, then the exact owned candidate, and record handle-backed absence.

The dedicated [host](../../scripts/cdb/run_framed_minimap_scroll_capture.ps1)
uses [framed_minimap_scroll_probe.py](../../tools/framed_minimap_scroll_probe.py)
and [framed_minimap_scroll_trace.py](../../tools/framed_minimap_scroll_trace.py).
The existing modal-screen host remains unchanged. The current soak pan path
discloses direct scroll writes; those are not a substitute for this native
callback sequence.

## Implemented host and offline verification

The host is dry-run by default. Required parameters are `-InputCandidate`,
`-ProxyBuildManifest`, `-WorkDir`, `-CandidateDir`, `-OutDir`, `-TargetX` and
`-TargetY`; `-Resolution` accepts only `1024x768` or `802x602`. The original
defaults to `C:\Clash\clash95.exe`. Explicit `-Execute` enables the reviewed
hidden path. Preparation reconstructs the entire optional-minimap candidate
and canonical packet, hashes sources, runtimes and proxy, and validates new
isolated output locations without creating directories or calling native APIs.
No arbitrary caller-supplied command file is supported.

Execution creates a unique candidate/proxy copy, a hidden desktop and one
owned CDB session with `CLASH_PROXY_PRESENT=0`. An inherited stdin read pipe
is paired with a non-inheritable parent write handle. The initial command uses
`-hd -logo <log> -c '$$>a<"<initial file>"'`; subsequent writes are exactly
`$$>a<"<before file>"` and `$$>a<"<continue file>"`, each followed by CRLF and
sent only after its preceding phase passes independent validation. The
source-quiet `$$>a<` form is necessary because other CDB file commands echo
source text, which the strict parser correctly rejects. Paths containing
argument tokens, delimiters or non-ASCII characters are rejected. Windows
argument quoting is exercised through actual `CommandLineToArgvW`.

The host reads the actual `-logo` bytes, rather than prompt-prefixed console
output. It binds immutable initial/before/after prefix hashes, validates both
live 188-byte surface headers before either pixel read, then reads each paused
map and clean backing once. Core `before-receipt.json` / `after-receipt.json`
retain the parser's exact key set. Separate capture envelopes bind actual
process identity, timestamps, addresses, header hashes and source hashes.
The final erasure call revalidates the full log and all original packet files.
The packet's historical `host_integration_implemented=false` field remains
unchanged; the dedicated host reports its implementation separately.

The shared 120-second capture deadline covers readiness, phase validation and
both raw captures. Trace, erasure or cleanup failures preserve raw evidence and
diagnostic PNGs. Cleanup waits for the retained debugger first, then its exact
candidate child; stdin is explicitly closed only after debugger termination
has signaled. A missing cleanup confirmation or artifact hash makes the final
summary fail. The host does not delete candidates, logs, partial captures or
failed outputs.

[Focused host fixtures](../../tools/test_framed_minimap_scroll_capture.py)
exercise native declaration compilation without invoking those APIs, managed
`ReadProcessMemory` / `WriteFile` stand-ins with the real pointer-sized
signatures, exact command transport, tampered prefixes, actual header-read
ordering, and full mocked orchestration with real offline PNG conversion.
Failure cases cover each phase, partial process creation, changed sources,
short writes, deadlines and cleanup. The fixed Python bridge also executes
through actual PowerShell `-c` transport, and calls the unchanged real
packet/trace/erasure APIs for both resolutions using in-memory reconstructed
candidates and synthetic buffers. These are fixtures, not runtime proof.

Parent-run synthetic debugger transport checks are preserved separately at
`C:\ClashCaptures\hd-completion\cdb-script-transport-20260906-045348` and
`C:\ClashCaptures\hd-completion\cdb-script-transport-20260906-045549`.
They establish source-quiet script transport for a synthetic executable,
including the initial `-c` shape, not Clash95 scroll or pixel correctness.

## Pixel oracle and cases

At each pause compute, from actual observed values:

```text
TX = floor((W-64)/64); TY = floor((H-32)/64)
L = Mx + 6 + sx*S; T = My + 6 + sy*S
R = L + 1 + ceil(min(W-64, (worldW-sx)*64)*S/64)
B = T + 1 + ceil(min(H-32, (worldH-sy)*64)*S/64)
```

Use the exact inclusive native perimeter raster already described in
[minimap_viewport_audit.py](../../tools/minimap_viewport_audit.py). Require
the before/new border pixels to equal native index `4C`. Let `old_only` be the
old perimeter minus the new perimeter. Every after pixel in `old_only` must
equal the corresponding **after backing** pixel `(x-Mx,y-My)`. Record how many
of these backing pixels differ from `4C`; require nonempty informative support
on the moved borders. A still-white old pixel whose backing is also white is
inconclusive about erasure. Do not mask mismatches to obtain a pass. Prefer
identical before/after backing SHA; if it changed, report that fact and require
a separately established clean backing lifecycle before claiming old-outline
erasure. Record software cursor state and reject unexplained overlay overlap.

Observe backing blits at `0040D62E`: EAX=backing, EDX=target, EBX/ECX=source
left/top, stack `[0]/[4]/[8]/[12]`=source right/bottom/destination left/top.
Require bounded rectangles and completed calls; at `0040D633`, ESP has advanced
16 bytes. Require the union of actual memory-target repair rectangles to cover
the tested old-only pixels. The emitted memory-outline observer from candidate
metadata then has EAX=map target, EDX/EBX/ECX=L/T/R, stack `[0]=B,[4]=4C` just
before native `00404040`. Require the actual matching draw and completed full
redraw before accepting after pixels. Primary-only drawing is insufficient.

Start with separate one-axis moves so opposite old border segments are tested;
then a far-edge clamp transition and a declared no-op control. Illustrative
geometry for the already observed 100x100 world, S=2 follows; these are computed
expectations, not additional runtime observations.

| Resolution / target scroll | Inclusive expected outline |
| --- | --- |
| 1024x768 `(10,17)` -> `(11,17)` | `(804,56,835,80)` -> `(806,56,837,80)` |
| 1024x768 `(11,17)` -> `(11,18)` | `(806,56,837,80)` -> `(806,58,837,82)` |
| 1024x768 far clamp `(85,89)` | `(954,200,985,223)`; visible Y shrinks from 736 to 704 world pixels |
| 802x602 `(10,17)` -> `(11,17)` | `(582,56,607,75)` -> `(584,56,609,75)` |
| 802x602 far clamp `(89,92)` | `(740,206,763,223)`; visible extent shrinks from 738x570 to 704x512 |

For the far clamp, begin one tile inward and request `max+1` within the minimap
interior; require actual native results `worldW-TX, worldH-TY` and a changed
scroll. Repeating the exact current in-range target is a separate native no-op
control and must not count as a pan or require a redraw. Reject smaller-world
initial/full admission rather than silently treating its fallback as HD proof.
Scale-4 runtime coverage requires a real suitable smaller-world save and its
own source/evidence plan; never alter the current 100x100 world or its scale to
manufacture that case. Existing pure/x86 scale-4 fixtures remain a distinct
claim. The three recorded runs establish controlled native scroll and bounded
software-pixel erasure only, with manual-input and promotion false. The no-op
control and scale-4 runtime remain separate pending cases; the illustrative
table above is not evidence for unexecuted cases.
