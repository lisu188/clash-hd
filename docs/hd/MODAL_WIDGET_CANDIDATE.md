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
