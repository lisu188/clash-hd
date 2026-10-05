# Mandatory resolution release matrix

The October 1 release target is all four launcher profiles at all nine presets:
Classic, Framed, Complete HD and Modal Widgets at 800x600, 1024x768, 1280x720,
1280x960, 1366x768, 1920x1080, 2560x1440, 3440x1440 and 3840x2160.
These are 36 independent acceptance combinations. The 802x602 partial-tile
fixture and arbitrary custom dimensions remain experimental.

## Read-only inspection and evaluation

```powershell
python -B tools/resolution_release_matrix.py
python -B tools/complete_hd_promotion.py --matrix-manifest C:/ClashTests/release/matrix.json
```

Both commands are stdout-only by default. Incomplete matrix evaluation returns
exit 2 without requiring `--require-pass`. An explicit `--write-json` creates a
fresh report and refuses to overwrite an existing file. Neither command runs a
game, debugger, input driver, capture tool or promotion operation.

The matrix index uses `resolution_release_matrix_v1` and immutable `path` and
`sha256` references. Every row identifies its `profile/WxH` id, candidate bundle
and original release index. Repository code selects the reconstruction recipe;
a manifest cannot select executable code or replace missing proof with passing
booleans. Candidate authentication and release acceptance are separate results.
Wide Classic uses its actual resolved menu-widget recipe rather than borrowing
the narrow Classic identity. A candidate or source change invalidates the
matching acceptance evidence.

The fixed source registry also admits `classic_all_presets_v1`,
`framed_all_presets_v1`, `complete_hd_all_presets_v1` and
`modal_widgets_all_presets_v1` for candidate reconstruction under their exact
profile, preset, stage and repository source identity. This is explicitly
reported as `unregistered_source_validation_recipe`; it does not substitute
for the launcher-resolved recipe or advertise a missing preset. Legacy
acceptance cannot qualify these successors, and the matrix remains failed
without all applicable production evidence and a promotion decision.

## Current implementation limits

The matrix adds mandatory inventory, exact candidate reconstruction, existing
complete-HD release replay and refusal of unsupported acceptance. The separate
source successors cover all four profiles at the nine presets;
they remain outside launcher registration. The matrix does not install the
expanded-battle successor, implement the fourteen missing runtime verifiers,
or supply fresh runtime evidence. Existing
legacy acceptance cannot qualify the required expanded-battle release.

The current catalog advertises 28 of the 36 preset combinations. Complete HD
and Modal Widgets each lack 1366x768, 2560x1440, 3440x1440 and 3840x2160.
The existing release evaluator implements two of sixteen production lane
verifiers; the remaining fourteen still fail explicitly. No new stable status,
whole-release pass or promotion is established by this checkpoint.

## Subsequent source preparation

`src/patcher/classic_all_presets_candidate.py` preserves the narrow scalar
and wide menu-widget recipes as distinct authenticated predecessors. Its
initial probe binds the final image to the selected predecessor and source
identity. The protected Classic 800x600 fallback and its launcher selection
remain unchanged. Inherited scalar patches do not declare every instruction
operand; exact source/byte reconstruction is not a complete loader audit.

`src/patcher/framed_all_presets_candidate.py` reconstructs the frozen Framed
map/input/minimap recipe with four inset bands and native modal fallback. An
independent second reconstruction binds every declared operand, hook and
typed metadata field before PE and original-to-final replay checks. Only the
known top-level legacy wall-clock field is omitted. It preserves the exact
source-owned DGROUP fallback and documents its deployment execution limit.
Both constructors retain their existing candidate bytes, add no battle hooks
and remain outside launcher registration.

`src/patcher/complete_hd_all_presets_candidate.py` provides a separately versioned
nine-preset Complete HD constructor. It reconstructs exact frozen producer
snapshots in a private namespace, verifies the final PE and declared relocation
inventory, and replays original-to-final byte records. The old six-size recipe
is unchanged. The new constructor remains outside the launcher registry; its
inherited initial-map probe uses preferred addresses and is not
the loader-rebased final verifier of the newer small-world chain. The Modal
Widgets successor in `src/patcher/modal_widgets_all_presets_candidate.py`
adds the complete owned slot/primary/text/widget chain under its own validation
identity. It authenticates supplied predecessor contexts instead of recursively
rebuilding the frozen six-size recipes, verifies each RX extension and inherited
owned state, replays original-to-final edits and rebinds the canonical initial
probe to the final image. Four RX layers leave fifteen PE sections and only one
additional header slot. Expanded-battle RX/RW allocation needs a separate design.
Constructor fixtures and source authentication establish no composition,
input, runtime or promotion acceptance.

`src/patcher/framed_battle_saved_views.py` supplies two uninstalled initial-camera
adapters. With complete phase-2 ownership admission, right-start X is actual
arena columns minus visible columns. Rejection preserves the original subtraction
and continuation. CPU fixtures cover all nine presets, small arenas, relocation
at two bases, registers, flags and inert state. Rendering, animation, HUD, input,
presentation and restoration must be installed atomically before these adapters
can become an expanded-battle recipe.

`tools/complete_hd_evidence.py::audit_hidden_soak_raw` replays the existing
samples/log format and recomputes every supplied raw frame's hash and histogram,
sample timing and process growth. It remains a diagnostic helper: its overall
pass, candidate authentication, cleanup verification and release acceptance are
always false. The producer lacks complete-candidate loaded contracts, every-frame
raw references, PID/path/creation-bound termination receipts, an authenticated
candidate/probe/wrapper run envelope and the menu-idle ladder route. These gaps
cannot be filled by passing report booleans; all fourteen production lane
verifiers remain unimplemented.

## Required acceptance and next work

Each final candidate needs actual native acquisition/read, selection/movement,
scrolling and focus recovery; map frame/footer, all six action cells, panel and
minimap alignment; castle and every supported building route; expanded battle
commands/outcome/healthy return; isolated save/load and player/day continuity;
approved final-wrapper composition and genuine human input; and the ordered
short ladder followed by two-hour map-idle and map-pan runs with owned cleanup.
The unchanged endurance schedule totals 176.4 measured hours across 36 cells.
Passing source or CPU fixtures cannot satisfy these requirements.

Expanded battles retain native 64-pixel tiles, seven rows and the actual arena
width capped at twenty columns. Their right HUD uses native-size top and bottom
slices, including bottom-anchored commands. Existing modular geometry tests now
cover all nine presets, but their native hook/routing integration remains
uninstalled. Preserve historical standalone battle recipes and diagnostics.

Resolve the current input failure using the prepared activation observer before
changing input behavior. Require fresh disk measurements before any compiler,
bundle, copy or game run; preserve the greater-than-ten-percent reserve and
next-operation allowance. Prior hidden/debugger authorization does not grant a
new visible/manual session. Prepare concrete candidate-bound human plans and
obtain fresh approval before those observations and live capture.

Preserve the frozen Classic 800x600 fallback, protected stable stage and current
default. Further source checkpoints may merge while unfinished entries remain
experimental. A stable entry requires accepted exact-candidate evidence and an
explicit promotion decision, rather than a successful build or process exit.

See [the handoff](AGENT_HANDOFF.md), [current evidence evaluation](COMPLETE_HD_EVIDENCE.md)
and [the contributor rules](../../AGENTS.md) for the existing operating boundaries.
