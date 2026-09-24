# Expanded battle controls at the top and bottom edges

The separate `expanded_battle_edge_controls_v1` recipe builds a 1280x720
successor to the existing expanded-battle experiment. Its stage is:

```text
gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-castlecenter-all-battlehd-edgecontrols-validation
```

The previous experiment centered the whole native sidebar in the vertical
interval `[120,600)`. This successor follows the user's requested edge
anchoring: statistics and the top button start at the top edge; the five lower
commands stay at the bottom edge. Artwork and sprites retain native pixel size.
The battlefield keeps the inherited half-open bounds `(32,136)-(1120,584)`,
17-column capacity, seven real rows, camera bounds and combat rules. It is still
independent of the Complete HD and modalwidgets candidates.

## Composition and input contract

| Native sidebar source | Final destination | Purpose |
| --- | --- | --- |
| `(480,0)-(640,368)` | `(1120,0)-(1280,368)` | Top button, portraits and statistics |
| `(480,368)-(640,480)` | `(1120,608)-(1280,720)` | Bottom command backing |

Two 16-pixel native border strips continue the sidebar's left and right edges
through the intervening vertical interval. The middle of that gap remains
black and contains no descriptor or stat-hover target. Full frame construction
still clears the primary first, copies only frame/sidebar rectangles, and
mirrors the result to the allocated software surface. A stats refresh copies
only the top sidebar background; it cannot overwrite the battlefield, lower
commands or the gap.

The actual six 53-byte descriptors beginning at `00514B78` become:

| Index | Displayed origin | Original callback |
| --- | --- | --- |
| 0 | `(1138,610)` | `0042D4E0` |
| 1 | `(1201,610)` | `0042D3A0` |
| 2 | `(1138,641)` | `0042D5B0` |
| 3 | `(1138,672)` | `0042D670` |
| 4 | `(1201,641)` | `0042D560` |
| 5 | `(1145,0)` | `0042D6F0` |

Only their two coordinate fields change. Their native draw callback, click
callback, sprite indices, text, availability and other descriptor bytes stay
unchanged. Native `004191F0` drawing and `00419B80` hit testing read these same
fields. The descriptor-list dispatch at `0042E501` retains the original call;
there is no global mouse-coordinate rewrite affecting the battlefield.

Stat hover `0042E160`, icon draw/restore coordinates at `00514DA4`, native stats
`00430F80`, its present/cursor rectangle, and morale animation `00430E90` use
the top slice's native Y coordinates with the already widened X positions.
Shared result dialogs and battle teardown keep their earlier behavior.

## Source and binary integrity

`src/patcher/battle_hd_edge_controls.py` checks the original SHA and pinned
predecessor sources, reconstructs all 283 inherited patches, and requires the
unchanged expanded-battle SHA
`7d04fe9005515dad4e618df507103946265d7e2a6421287281c1fc5f112d1e47`.
The old stage and patch sources are not edited. The four battle dependency
files (`battle_hd_hud.py`, `battle_hd_core.py`, `battle_hd_layout.py` and
`battle_hd_section.py`) have two explicitly enumerated source identities:
the existing Windows CRLF checkout and the Git LF blob. Their complete bytes
were compared independently; removing only CRLF carriage returns reproduces
the Git blob exactly. No other source variation is accepted. The other three
dependencies keep a single exact identity. Verification hashes the actual
bytes without normalization, and the manifest records the actual observed
hash for each file. A mixed or changed source that matches neither identity
fails. Predecessor reconstruction and the exact candidate SHA remain required.

The successor appends one RX helper section using the checked PE extension
builder, preserving the eight inherited section headers and old relocation
table. Fifty-three explicit equal-length edits check their predecessor bytes:
the six descriptor coordinate pairs, six icon pairs, 31 native Y instructions,
eight trampoline Y immediates, and two complete helper prologues. The prologue
replacements tail-delegate to the new frame and stats helpers. No new mutable
state or gameplay/input API is added.

The manifest records every inherited patch and successor edit with file
offset, RVA, VA, old/new bytes and purpose. It retains exact sources, candidate
ancestry and loaded-probe identity. The generated read-only startup contract
checks the final bytes of every inherited patch, both generated code sections,
headers, descriptors and relevant native draw/input routines. It does not
supply an initial map route or an accepted runtime observation. Preserving old
HIGHLOW entries does not establish relocation completeness of the older
battle experiment; its preexisting relocation limitations remain separate.

## Reproduction and current verification

Prepare a new bundle with the dedicated builder, or use preflight to construct
it only in memory:

```powershell
python -B tools/build_battle_hd_edge_candidate.py --original C:/Clash/clash95.exe --preflight
python -B tools/build_battle_hd_edge_candidate.py --original C:/Clash/clash95.exe --output C:/ClashTests/battle-edge-validation/battle-edge-1280x720.exe
python -B tools/test_battle_hd_edge_controls.py --source-exe C:/Clash/clash95.exe --toolchain-path C:/ClashTests/battle-hd-tools/python --require-machine-tools -v
```

Outputs require a new absolute `.exe` path under `C:/ClashTests`, outside the
checkout; existing bundle members are never overwritten. The builder starts
no game or debugger. The old patcher/launcher stage choices remain unchanged.

On 2026-09-24, the final 15 focused fixtures passed without skips in 1.410 seconds.
Original-backed x86 fixtures executed the actual native descriptor draw/hit,
stat-hover, morale-animation and stats-present instruction paths. They verify
all six unchanged callback targets, descriptor drawing without scaling, three
cursor scales (0, 2 and 6), gap/boundary rejection, exact native copy rectangles,
register/stack/flags preservation, complete byte replay and relocation
preservation. The source compatibility fixtures exercise both enumerated EOL
forms, verify actual manifest hashes and unchanged candidate/probe bytes, and
reject non-EOL changes and unlisted mixed endings. Resource queries, input-query
results, rendering sinks and game
callbacks are explicitly stubbed in these CPU fixtures. They are not game,
artwork or natural/manual-input evidence.

The final in-memory preflight candidate SHA is
`26fa4f69095f8d47480b325e22c70bffb3f6c098760de04164ebd09fb93038e3`.
Fresh matching runtime and pixel evidence remains necessary: initial and
refreshed command artwork, top/bottom frame edges, all enabled commands and
hover regions, native entry/exit, the restored HD map, and final visible
composition. No old battle report is relabeled for this successor. The
September 19 capture's missing command artwork and failed hidden device reads
remain recorded. The protected stable stage, manual-input boundary and
promotion decision are unchanged.
