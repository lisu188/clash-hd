# Widget-bound validation candidate

`tools/build_framed_modal_widgets_candidate.py` builds recipe
`owned_modal_widget_bounds_v1`, stage
`gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-completehd-modalwidgets-validation`.
It starts from the exact frozen `owned_modal_primary_text_v1` candidate and adds
the [two guarded descriptor comparisons](MODAL_WIDGET_BOUNDS.md). The inherited
primary, text, modal, slot and map implementations are not rewritten.

## Binary contract

The builder authenticates the original SHA-256, frozen predecessor sources and
complete predecessor reconstruction before checking the single/list dispatcher
windows. Only the two six-byte width comparisons are replaced with CALL/NOP.
The added fifteenth `.hdwgt` section is RX; the existing fourteen section headers
and all unrelated original bytes remain unchanged. Its unused virtual capacity
keeps the existing 128 KiB extension reservation convention. There is no new
mutable state: guards consult the inherited `.hdstate` owner and call its
source-bound `is_active` entry only for a non-faulted owned native render target.

The extension preserves every inherited HIGHLOW relocation, adds the eight new
absolute fields, rejects displaced historical fields, and retains the old
relocation table as untouched bytes. The complete relocation directory moves
into the new RX section. Every byte edit carries the checked old/new bytes,
file offset, RVA and VA. The manifest binds both candidate identities, exact
sources, entry addresses, hook records and the loaded-image probe.

The probe retains every predecessor check. Only bytes belonging to declared
edits can change their expected loaded values. Full new code/relocation payload,
section header and both complete dispatcher windows are checked. New startup
markers name the widget stage and actual candidate SHA; old primary/text logs
cannot become evidence by changing a manifest's name or hash.

## Preparation

The builder never launches a process. Its output is a new `.exe`,
`.candidate.json` and `.cdb` triplet under `C:/ClashTests`, outside the source
checkout. It rejects an occupied destination or sidecar before reading input.
Use the original from the user-owned, hash-verified `clash-assets` runtime:

```powershell
python tools/build_framed_modal_widgets_candidate.py --original C:/Clash/clash95.exe --resolution 1024x768 --output C:/ClashTests/modalwidgets-validation/widget-1024x768.exe
```

`--preflight` with no output reconstructs and reports the candidate without
writing it. Six canonical fixture resolutions are accepted; the new
asset-backed Windows workflow tests 1024x768 and 1920x1080 separately.

## Evidence boundary

Synthetic format tests independently replay every edit, compare every unchanged
byte/header, relocate the image, and check loaded-predicate coverage. Negative
cases cover layout collisions, permissions, malformed/overlapping hooks,
relocation targets and operands, source/probe drift, noncanonical profiles and
output collisions. The original-backed tests rebuild the full ancestral recipe,
verify source identities, inspect both actual native dispatcher comparisons,
and ask Windows to create a nonexecuting `SEC_IMAGE` section without mapping it
or starting a game process. The native guard CPU fixture uses a labeled owner
stub; it is not native ownership execution.

A fresh stage-aware capture consumer and original-artwork comparison are still
required. No existing primary/text-stage host accepts this candidate implicitly.
Successful construction, loading or synthetic CPU checks do not establish
corrected lower-frame pixels, whole game execution, native modal exit, ordinary
input, endurance or stable promotion. Classic/800x600 and all historical failed
capture receipts remain unchanged.

## Exact bundle context for new consumers

`tools/modal_widgets_context.py` provides
`load_context(original_bytes, candidate_bytes, manifest_path)`. It authenticates
the actual widgets-v1 stage by rebuilding the complete candidate, typed manifest
and sibling probe. Its exact 36-file recipe inventory, frozen text/widget pins,
separate text-context dependency and bundle identities are checked before and
after reconstruction. Missing files, duplicates/nonfinite JSON, aliases, stale
source bytes, changed artifacts and predecessor-stage manifests fail closed.

The result retains the widget stage and SHA. Its `text_context`, `primary_context`,
`slots_context` and `owner_context` are separately named, detached ancestor
metadata for building a new explicit consumer. They do not admit widget logs to
old primary/text readers. The unchanged text reader rejects a real widget bundle.

The [2026-09-24 source-validation receipt](../../captures/current/modal-widgets-context-source-validation-20260924.json)
records a fresh original-backed 1024x768 build and exact authentication: 15 PE
sections, 36 recipe sources, candidate
`ebea660f885da43896ad5e4303e6e7d7fe112def6c897b4c26312df8505376e5`.
All 21 synthetic boundary fixtures pass, and independent review rechecked the
receipt and its identities. The original executable remains unchanged.
The source-only build took 196.328 seconds and authentication 281.125 seconds;
a future host needs a measured, bounded preparation timeout rather than the
older 120-second limit. Neither operation launched the game or debugger.

Run the synthetic fixtures without game assets:

```powershell
python -B tools/test_modal_widgets_context.py
```

This reader covers widgets-v1 only. It does not authenticate the separate
`nativepresent` successor from the failed September 21 playability run. A
matching capture host, native ownership/artwork/text checks and new runtime
observations are still required. Source authentication is not a rendering,
input, lifecycle, manual-proof or promotion pass.

The separate [barracks probe preparation](MODAL_WIDGET_BARRACKS_PROBE.md) now
binds the actual widget bundle and genuine ancestor observer sites. It keeps
the compiled diagnostic command explicitly not ready for runtime while trace,
Lock/text/owner observations, host queries and pixel validation are integrated.
