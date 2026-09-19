# Owned modal primary composition

This validation implementation addresses primary pixels that the owned native
canvas and physical-mirror checks cannot prove. It adds a separate
`-completehd-modalprimary-validation` stage, recipe `owned_modal_primary_v1`,
above the exact slots candidate. The complete-HD v1 and slots builders,
protected stable stage and launcher defaults retain their existing behavior.

## Retained defect evidence

The 2026-09-13 hidden barracks primary captures D at 1024x768 and F at 1920x1080
both contain the original placeholder sprite at native primary coordinates
`[220,289,423,409)`. All 24,360 pixels match sprite 25 from
`GFX/CASTLE.CHR/DW_12.S32`. At 1024x768, that rectangle overlaps the first two
lower portrait interiors. At 1920x1080, it lies outside the centered canvas.
The intended physical destinations are `[412,433,615,553)` and
`[860,589,1063,709)` respectively. Rectangles here exclude right and bottom.

Both runs' physical mirrors match their native canvases and have clear outer
margins. Their primary surfaces retain old map, minimap, frame and action-bar
pixels outside the modal canvas. D's five bottom modal controls and all four
canvas perimeter edges remain intact despite the interior overlay defect.

The retained D directory is
`C:/ClashCaptures/hd-completion/slots-primary-1024x768-20260913-d/`; its matching
attached-palette visualization is
`C:/ClashCaptures/completehd-integration-20260913/slots-primary-d-visualization/primary-1.png`.
F is `C:/ClashCaptures/hd-completion/slots-primary-1920x1080-20260913-f/`.
D remains failed for its original audit deadline/header rejection, and F
remains failed for overlapping memory-region claims. These diagnostic pixel
comparisons do not convert either host receipt into an accepted runtime run.

## Source correction

[`framed_modal_primary.py`](../../src/patcher/framed_modal_primary.py)
authenticates the original executable, reconstructs the entire slots candidate,
and checks the original panel, cursor and partial-copy instruction bodies.
It declares five indivisible hooks:

| Boundary | Behavior with valid owned modal state |
| --- | --- |
| Full blit `00401E30` | Mirror the native canvas, then publish the physical HD surface through the existing HD blitter at `(0,0)`. This replaces the old map margins at the original full-blit boundary. |
| Placeholder coordinates `00432F94` | Replay both native coordinate instructions and add the physical center offset for the primary-only sprite. Keep its original virtual call and seven stack arguments. |
| Cursor rectangles `00432F5C`, `004331D5` | Translate the panel overlap bounds to physical coordinates before delegating to the original cursor helper, retaining `RET 4`. |
| Selected panel copy `00433273` | Keep native source coordinates, copy its inclusive dirty rectangle into the physical mirror, and translate only the primary destination. Preserve native `RET 16` and callee clobbers. |

An active cursor needs its old saved background restored before the full HD
copy, then a new background captured before redrawing. The adapter uses the
original cursor remove and present routines in that order. It preserves the
original full-blitter argument and returned registers/flags around the added
cursor calls. It does not assign cursor flags, mouse state or input results.
The emitted source records its cursor prerequisites and remaining native
resource-allocation assumptions.

Every new path checks the inherited owner thread, canvas/header/pixel identity,
dimensions, nonwrapping disjoint buffers and sticky fault status. Unsupported
contexts delegate to the unchanged native or inherited path. In particular,
full-blit fallback retains the inherited mirror behavior, including its own
fault handling; it does not invoke the new full-HD publication or cursor pair.
No global partial-blit hook or late unconditional primary replacement is used.

The placeholder remains a primary-only layer. Its corrected primary output is
the centered native canvas plus the translated original sprite, with the
cursor handled separately. Requiring complete primary equality to the native
canvas would discard a legitimate original layer.

## Candidate and verification

[`build_framed_modal_primary_candidate.py`](../../tools/build_framed_modal_primary_candidate.py)
builds an exclusive `.exe`, `.candidate.json` and `.cdb` bundle under
`C:/ClashTests`. Its PE extension adds a thirteenth RX section, `.hdprim`,
without changing any old section header or removing historical relocations.
Every edit retains old/new bytes and offset/VA/RVA metadata. The source hashes
and the loaded-byte probe belong to this new stage. It emits no complete-HD,
army or slots pass marker for these modified bytes.

```powershell
python -B tools/build_framed_modal_primary_candidate.py --original C:/Clash/clash95.exe --resolution 1024x768 --preflight
python -B tools/test_framed_modal_primary.py
python -B tools/test_pe_modal_primary_extension.py
python -B tools/test_build_framed_modal_primary_candidate.py
```

The x86 fixtures execute emitted instructions in synthetic memory with the
existing owned-canvas lifecycle and native-call recorders. Their pixel,
register, flag, stack and callback-order checks are offline evidence.
Independent PE replay/rebase and Windows image-section admission do not launch
the candidate. Source-byte attributes keep reconstruction stable across clones.

The [2026-09-13 source validation record](../../captures/current/modal-primary-source-validation-20260913.json)
records 16 executable x86 fixture groups, nine PE fixtures and six candidate
build fixtures, all passing with no skips. The build checks cover all six
supported resolutions, including 1920x1080 and the 802x602 regression case.
The report binds source hashes and retained nonexecuted candidate artifacts.

Actual primary composition is still unverified on this stage. A new
source-bound runtime consumer must retain the inherited route evidence,
observe these hooks and cursor transitions, capture native/physical/primary
triplets with matching palettes, and compare the intended original overlays.
The current slots consumer must not accept or relabel this different stage.
Initial barracks entry exercises the placeholder and its cursor rectangle;
the selected-panel copy and its other cursor rectangle require a subsequent
selection case. Bind all five installed hooks, but report an unexercised branch
as unexercised. Cursor remove/redraw observations must identify the adapter's
actual call sites, rather than count unrelated global cursor calls.
Fresh hidden screenshots are required at 1024x768 and 1920x1080, including all
modal margins and controls, followed by selected-panel/cursor interactions.
Ordinary input, every castle building and transition, native ownership exit,
wider tactical battle, endurance, visible/manual proof and promotion remain
separate unfinished requirements for the full mod.
