# Small-world input: complete successor and evidence limits

Updated: 2026-09-30. The additive complete successor integrates the bounded
component into both complete profiles. The historical component evidence and
September 24 allocation analysis below explain its source dependencies. Source
construction and CPU fixtures do not declare the September ordinary-input runs
repaired.

## Complete successor

`src/patcher/complete_small_world_candidate.py` reconstructs the exact
original-bound `ordinary_castle_entry_matrix` parent before applying six
old-byte-checked replacements: two 124-byte render dispatch guards and four
16-byte input-axis guards across the ordinary and army-private routes. It
retains the ordinary army-backing exclusion, private ownership checks, native
predicate order, integrated frame/panel/presentation targets and the inherited
96-byte castle-entry gate. Single-squad selection retains the native ordinary
route; the authenticated multi-squad private route is not broadened.

The helper is appended after the actual matrix `SizeOfImage`, within an
extension of its final RX section. No section is added. Existing payload and
relocation-directory bytes remain unchanged; a new merged directory preserves
all inherited HIGHLOW entries and adds the five helper absolute operands.
Declared PE-header changes and appended bytes are checked separately from the
six semantic replacements. Frozen predecessors and their source pins remain
unchanged.

The distinct stage is `ordinary_castle_entry_matrix.stage(profile)` with its
trailing `-validation` replaced by `-smallworld-validation`. Its schema is
`clash95_complete_small_world_candidate_v1`, revision `complete_small_world_v1`.
Only `completehd` and `modalwidgets` at the existing 800x600, 802x602,
1024x768, 1280x720, 1280x960 and 1920x1080 resolutions are supported.

The [September 30 source/CPU checkpoint](../../reports/complete-small-world-source-verification-20260930.json)
passes 32 methods without skips: nine portable, seven CLI, eight synthetic CPU
and eight original-backed CPU methods. The actual modalwidgets1920 image was
constructed once in memory: candidate SHA
`657faf66ca2858f9b07dd7a2d9c96bd1853821c0e23e6f7042ec448f747b64fe`,
parent SHA `2a3dac1e51ffe2ec12a91e8d1d687171135a31ed3c88b8bcbdb7974e85149e3d`.
The inherited gate remains at `0x648000`; the new helper starts at `0x649000`.
Both profiles and all six geometries have synthetic byte coverage; this
checkpoint does not construct twelve original-backed candidates or qualify
their runtime. Drawing dependency returns are modeled. No game, compiler,
debugger, bundle write or screen capture accompanied the local checkpoint.
The [initial CI startup failure](../../reports/complete-small-world-ci-startup-failure-20260930.json)
is retained separately: GitHub rejected the inline pip command's YAML before
starting a job. The correction uses a literal block; it changes no producer or
CPU fixture bytes. Actual debugger-verifier results require the subsequent run.

The final CRLF verifier checks final headers, executable file-backed ranges
and inherited legacy wrapper spans. It masks loaded DWORD values and relocation
arithmetic, requires ordered chunks, and emits a candidate-, stage- and
resolution-bound `CSW_FINAL_OK` only after all checks complete. Missing,
reordered or unreadable chunks cannot qualify. Earlier component or
`OCEM_CONTRACT_PASS` markers identify other images and cannot qualify this one.

Safe source verification commands are:

```powershell
python -B tools/test_complete_small_world_candidate.py --synthetic-only --require-machine-tools -v
python -B tools/test_complete_small_world_candidate.py --source-exe C:/Clash/clash95.exe --require-machine-tools -v
python -B tools/build_complete_small_world_candidate.py --original C:/Clash/clash95.exe --profile modalwidgets --resolution 1920x1080 --preflight
```

The synthetic and original-backed CPU lanes execute only fixture memory. The
original-backed lane reconstructs one actual candidate in memory and writes no
candidate bundle. The preflight also writes no bundle and launches no game.
Unicorn must be available; an existing retained library can be selected with
`--toolchain PATH` without installing another copy. The required-tools mode rejects missing dependencies
and the synthetic CI lane rejects skips. The separate Windows CI verifier lane
uses the restricted debugger harness on explicitly marked artificial PE32
fixtures paused before their entrypoints; it never reads the original game.

The CLI can write a fresh `.exe`, `.candidate.json` and `.cdb` bundle only to
a nonlinked external path under `C:/ClashTests`, after rechecking original and
source identities and more than ten percent disk reserve on both relevant
volumes, including the aggregate bundle size. Local bundle creation and game
runs remain paused while the checkout volume is below that reserve.

This source successor remains outside the launcher and measured runtime driver.
The driver's `--prepared-matrix-candidate` accepts the older matrix recipe;
it must reject this distinct successor. A matching execution adapter and fresh
runtime evidence are still required. Construction, synthetic execution,
loaded-byte verification, ordinary/manual input, final visual composition,
endurance and promotion are separate claims. No stable stage is changed.

## Existing component

`src/patcher/framed_bounded_input.py` already provides the correction above
`src/patcher/framed_bounded_paint.py`. Its stage is:

```text
gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-combinedui-partialtiles-initialpaint-framed-bounded-paint-input-validation
```

Do not create a second public stage for the same framed candidate. A fresh
original-backed reconstruction at 3840x2160 produced:

| Artifact | SHA-256 |
| --- | --- |
| Original | `500055d77d03d514e8d3168506bd10f67cd8569bcc450604ff8192f46cdaf3ae` |
| Bounded-paint parent | `2ad1b61ff3d5869209016ff3b79f4162c0511123c7454dba541648626f546cbc` |
| Existing bounded-input candidate | `1aa9554e804fed89e064f2e14bf0fe43dc44ef508689775efde81305da607486` |

The correction changes two 16-byte regions in the ordinary map pixel guard.
Each axis retains dimension validation (1..100), negative-scroll rejection,
physical frame/overlay exclusions and the actual clicked world-coordinate
bound. The only changed rule is:

```text
0 <= scroll <= max(0, world_dimension - full_viewport_tiles)
```

The input helper never writes the camera or target memory. Bounded repaint
must clamp a stale camera before input can be admitted. At 3840x2160 there are
59x33 full tiles; a 50x50 world therefore permits maximum scroll `(0,17)`.
Physical x=3231 can address column49, while x=3232 addresses column50 and must
be denied. Minimap and action-bar exclusions still take precedence.

`tools/test_framed_smallworld_input.py` adds original-backed execution of the
complete existing mouse wrappers. The original click/minimap predicates are
copied into synthetic x86 fixture memory with their authenticated relocations.
The fixture verifies that the candidate actually contains these tested wrapper
bytes. It uses an independent scalar oracle and retains the original frame,
minimap, action-bar, owner, player, callback, signed-shift and ABI cases. Added
cases cover 4K50x50, one or both axes smaller than the viewport, 1x1/10x10
worlds, out-of-world clicks, partial tiles, stale scroll and rebased execution.
Each CPU case checks preserved registers, ESP, flags/DF, native predicate
ordering and unchanged game/global/surface memory.

Run from the repository root with an available interpreter:

```powershell
python -B tools/test_framed_smallworld_input.py -v
python -B tools/test_framed_bounded_input.py
python -B tools/test_framed_loaded_probe.py
python -B tools/build_framed_bounded_input_candidate.py --original C:/Clash/clash95.exe --resolution 3840x2160 --preflight
```

The 2026-09-24 local check passed 12/12 new full-wrapper tests, 22/22 existing
bounded-input tests and 21/21 loaded-probe tests, with zero skips. The real
original-backed 4K preflight returned the candidate SHA above with
`written=false`. No game/debugger run accompanied these checks.

The full-wrapper CPU tests require Windows, an x86 C# fixture compiler and the
known original; unavailable prerequisites are explicit skips. They start only
the synthetic fixture executable, never Clash95, CDB or a wrapper. They do not
send input or capture a screen. A passing CPU fixture does not establish
in-game selection, movement or manual-input proof.

The existing `--probe-cdb` option generates a final component byte verifier
through `tools/framed_loaded_probe.py`. It checks relocation-aware loaded
headers, selected scalar spans, installed hooks and the final injected code.
Its ordered chunk counter prevents read/expression errors from producing a
success marker. Generation does not run CDB. That component verifier must not
be relabeled as a complete/modalwidgets verifier.

## Historical integration gap — 2026-09-24

The launcher nativepresent chain still reconstructs the frozen framed or
complete/modalwidgets predecessors. It does not incorporate bounded paint or
bounded input. The September21 4K framed run therefore still used the old
unconditional rejection when world width50 was below viewport width59.

The complete chain cannot safely import an entire frozen input helper:

- `framed_army_composition.py` rewrites the ordinary `context_guard` to admit
  an authenticated own-army lower owner. It also replaces the first eight bytes
  of `pixel_guard` with the army-backing exclusion wrapper.
- `framed_army_input.py` embeds a private copy of the frozen input helper with
  lower owner1. Its `guarded_map_click` calls `private.click_gate`, then checks
  current ownership/selection and excludes the full army backing.
- Army composition also modifies the shared composition guard, edge/cell
  admission, panel composition and frame-presentation admission. Bounded
  rendering must call these integrated entrypoints, retaining portraits,
  command composition, owner validation and temporary-vtable restoration.
- The existing bounded builder assumes `.hdcode` is the final section. That
  assumption fails for the complete chain. Existing predecessor modules and
  pins must remain unchanged.

The successor requirement identified at that review was to authenticate the exact final parent, retain those
army changes, append the bounded renderer, replace the two 124-byte render
dispatch regions, and correct both axes in both ordinary and army-private
world guards. Merely fixing ordinary selection leaves selected-army map
clicks blocked. Merely fixing input leaves small-world repaint unsupported.

The 2026-09-24 analysis reconstructed the archived 1024x768 nativepresent image
in memory by replaying its exact old-byte-checked records against the validated
widget candidate. No game was launched and no candidate was written:

| Bound ancestor | SHA-256 |
| --- | --- |
| Modalwidgets1024 | `ebea660f885da43896ad5e4303e6e7d7fe112def6c897b4c26312df8505376e5` |
| Nativepresent successor | `23c766f439f3f871b6a2b992f22f2efa45b51373b9629cede5235596c519d743` |

Its exact reviewed locations are below. Addresses are specific to that image;
a production successor must derive and verify them from its reconstructed
parent metadata, never apply them to an arbitrary executable.

| Region | Entry/start | Replacement start(s) | Rejection destination |
| --- | --- | --- | --- |
| Full redraw | `0x563987` | `0x5639AC`, 124 bytes | `0x563A87` |
| Initial paint | `0x563AC1` | `0x563AF8`, 124 bytes | `0x563B7E` |
| Ordinary input world gate | `0x564698` | `0x5646B0`, `0x564704`, 16 bytes each | `0x56474B` |
| Army-private world gate | `0x59726E` | `0x597286`, `0x5972DA`, 16 bytes each | `0x597321` |

Both input world regions match the existing component's original 190-byte
world gate. Both render entry prefixes and original 124-byte admission gates
also match source emission. The integrated renderer targets are:
`composition_guard=0x563023`, `cell=0x562492`, `draw_frame=0x562A37`,
`compose_panel=0x56342A`, `present_map_rect=0x56352E`.

There are already 16 PE sections. The final `.hdpblit` header is at file offset
`0x3C0`, RVA `0x237000`, raw offset1734656, raw size68608, virtual size69632,
and RX characteristics `0x60000020`. `SizeOfImage=0x248000`; the file has
1803264 bytes. Another section header does not fit the frozen 1024-byte header.

The historical proposed allocation extended this final RX section,
leaving all predecessor addresses and existing raw bytes unchanged. The next
page begins at VA `0x648000`, with a 1024-byte raw gap to fill before the new
code. Source emission of the bounded helper at this VA is 481 bytes with five
absolute and five relative relocation records. A new allocator must preserve
the old relocation directory bytes, append a complete merged directory,
update the final section extents and PE sizes/directories with old-byte checks,
and verify rebase behavior. These addresses describe that older nativepresent
image. The current matrix already appends its castle gate, so the new successor
derives the next allocation from the reconstructed matrix instead of reusing
the historical `0x648000` location. Existing zero padding and reserved data
must not be overwritten.

The complete predecessor currently accepts only 800x600, 802x602, 1024x768,
1280x720, 1280x960 and 1920x1080. A 4K component test does not extend that
allowlist. A complete 4K candidate requires an explicit additional integration
and validation step. Classic uses another recipe and has neither framed input
helper; this correction cannot be applied there by matching byte patterns.

## Verification requirements and remaining runtime

Authenticate source paths and raw hashes, original identity, complete parent
bytes and typed ancestor metadata before modification. Keep the existing
frozen pins. The reviewed framed input, framed builder, camera and bounded
paint files match their tracked LF bytes. Other tools can have differing CRLF
checkout bytes; do not invent a platform-only pin or normalize arbitrary source
to make a check pass.

The complete successor's fixtures must cover all six replacement spans,
tail allocation and merged relocations, and CPU composition cases for lower
owner0 and authenticated owner1. Test backing/minimap/action-bar exclusions,
out-of-world cells, partial tails, stale cameras, unsupported owners and exact
restoration of render targets and vtables. Bind fresh loaded-byte evidence to
the final stage and candidate SHA. Native selection must show the selected
index transition for a currently visible, occupied, owned army; movement needs
matching coordinate/occupancy/action-point changes and native handler return.

The actual hidden runtime, frame continuity, all six action-bar cells, minimap
viewport, castle/building transitions, tactical UI, manual input and promotion
requirements remain separate. Keep the protected stable stage and original
executable unchanged.
