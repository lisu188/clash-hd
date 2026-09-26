# Native castle-entry diagnostic — 2026-09-24

A hidden controlled call through the game's real Building_GetInto function
reproduced the castle corruption on the exact candidate used by the failed
September 21 widget runtime. The native function changes the renderer before
calling the castle root. The inherited HD canvas guard rejects that renderer,
so the castle draws against the 1024x768 map instead of an owned 640x480 canvas.

The [baseline manifest](ordinary-castle-entry-baseline-20260924.json) binds the
fresh rebuild, command files, host, loaded-code checks, raw observations,
palettes, images and cleanup. This is a controlled native-caller diagnostic
with an isolated slot-0 save, not a campaign mouse click or manual input proof.

## Availability checked 2026-09-26

The user confirmed removal of C:/ClashCaptures and C:/ClashTests for cleanup.
Both directories are absent on this host. The baseline manifest remains a
historical record; statements below about retained hashes, screenshots and
cleanup describe the September 24 inspection, not fresh access to those raw
artifacts. No successor runtime, screenshot or lifecycle pass is asserted.
The original C:/Clash/clash95.exe was rehashed and still matches the required
500055d77d03d514e8d3168506bd10f67cd8569bcc450604ff8192f46cdaf3ae.

## Exact observed chain

Candidate SHA: 23c766f439f3f871b6a2b992f22f2efa45b51373b9629cede5235596c519d743.

Stage: protected stable plus
-completehd-modalwidgets-nativepresent-validation, at 1024x768.

| Observation | Result |
| --- | --- |
| Before native owner change, 0x41ED54 | Ordinary owner 0x40AD40 |
| Native castle CALL, 0x41ED6A | Owner 0x4617A0; saved EBX 0x40AD40 |
| Canvas owner check, 0x57606B | Observes 0x4617A0 |
| Existing rejection, 0x576230 | Reached |
| Admission return, 0x5767A9 | EAX=0; no canvas allocation |
| First castle present returns, 0x42239F | Castle owner 0x422020, unchanged HD map, phase/enter/allocations=0 |

All six observations used the same native thread and matched expected stack
offsets. The diagnostic did not write ownership, canvas, construction flags or
admission results. Its controlled call changed only input registers and a
stop-only stack return sentinel. The native wrapper changed ownership itself.

The historical six-screen probe jumped directly into the castle root while the
ordinary renderer remained installed. It did not exercise this caller.

## Captures and evidence limits

Retained directory:
C:/ClashCaptures/ordinary-castle-entry-1024x768-20260924-e.

The preceding ordinary-map primary capture passes exact source-artwork
comparison for all four structural border bands and all six action cells.
The footer remains unverified, so the complete frame audit stays false.
This is one paused capture, not a temporal stable-pair claim.

The castle primary is visibly corrupted: upper scenery is scrambled and lower
map content and action cells remain. Castle frame continuity and modal controls
fail visual inspection. Ordinary-map cells cannot serve as castle-control
proof. The images came from paused software memory; visible-GDI tearing does
not explain this corruption.

Every retained read artifact matches its recorded hash. Before breakpoints,
the host compared all 1,024 header bytes and nine executable sections
(1,519,616 bytes) with the authenticated candidate. Mutable data and imported
library code are outside that whole-code claim. Loaded proxy path, rebased PE
headers and private vtable ranges were checked before reading its palette.

The final run completed with no declared failures. Retained debugger and game
handles confirmed both processes absent; the private desktop closed. The
original executable, live saves, isolated saves and declared source/bundle
files remained unchanged. Earlier preparation/capture failures remain in the
manifest, including the first attempt's missing retained-handle cleanup proof.

## Additive correction

The separate [ordinary-entry successor](../docs/hd/ORDINARY_CASTLE_ENTRY.md)
preserves the native caller and remaining canvas checks. It adds narrowly
authenticated caller admission without writing a renderer value to satisfy
the old guard. Source/CPU validation and a successor runtime comparison are
separate from this negative baseline.

Normal campaign selection, castle exit and freeing, all building interiors,
visible composition, manual input and stable promotion require matching
evidence. This report does not promote a stage or relabel historical captures.

## Source checkpoint verification — 2026-09-26

The [fresh verification record](ordinary-castle-entry-verification-20260926.json)
records nine passing source/original-backed byte test methods. Six machine-test
methods were not executed because Unicorn was removed with the local tool
output (31 skipped test/subtest entries). The 15-test invocation exited zero
with those skips; it is not a full CPU-validation pass. Both documentation
fixture suites and both current documentation guards pass. Independent source
review found no blocking defect. No game, debugger or new capture ran during
this checkpoint.
