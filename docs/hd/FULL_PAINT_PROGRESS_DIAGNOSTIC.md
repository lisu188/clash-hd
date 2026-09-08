# Full-paint progress observer

The complete 800x600 run `cdb-surface-dump-20260908-103759` failed its strict
initial-map trace: PTILE events 97 and 98 reported full convergence at the same
thread/stack/site, followed by event 99 reporting presentation. The initial
paint itself had already returned. The original failure remains unchanged.

This trace lacks later full-function entry/return observations and the native
presentation argument. It cannot distinguish a debugger retrap from separate
native calls reusing the same stack, including an offscreen call that skips
presentation. Microsoft documents `gc` as preserving the previous execution
mode and explicitly supports its use in logging breakpoints; the command alone
does not explain duplicate observations.
[Microsoft gc documentation](https://learn.microsoft.com/en-us/windows-hardware/drivers/debuggercmds/gc--go-from-conditional-breakpoint-)

`tools/framed_full_progress_probe.py` creates a separate complete-candidate-bound
diagnostic. `-FullPaintProgressDiagnostic` enables it in the hidden surface
harness. IDs 83–85 are checked against all existing declarations; minimap keeps
80/81 and the optional no-op observer keeps 82. The existing canonical PTILE
probe, declarations, counters and log records are preserved.

The three observations are:

- Native full-function entry at `00418700`: entry ESP, return address, caller
  EBP and the actual EAX presentation argument. The unchanged native instruction
  at `00418709` copies EAX to EBP after preserving the caller's register frame.
- Immediately after the convergence status store: the next instruction is
  POPAD. ESP is 144 bytes below full entry; `[ESP+8]` is the saved native EBP,
  `[ESP+36]` is the stored result, and `[ESP+144]` is the original caller.
- The emitted wrapper's native-return observer: ESP is 52 bytes below entry,
  wrapper EBP is 36 bytes below entry, and the original caller EBP and native
  return EAX are still in the wrapper's saved frame. Return EAX is uninterpreted.

The generator checks these exact instruction bytes and stack contracts against
the reconstructed candidate before emitting live read-only byte checks. Bytes
occupied by existing software breakpoints retain their earlier canonical check.
The observers read the existing PTILE counter for correlation without modifying
it. Sequence fixtures preserve repeated, malformed and unmatched observations
as failures. A zero native EBP only becomes meaningful when the matching call's
entry, progress, return and presentation observations establish what occurred.
No diagnostic result overrides the existing trace evaluator or grants release
acceptance.

The complete hidden lane also preserves three consecutive ReadProcessMemory
captures at its stopped trace-closed boundary. These raw captures stay outside
the repository and their individual paths, byte counts and hashes are recorded
in `SurfaceCaptureSet`; they are software-surface evidence rather than manual
input or final wrapper-color proof.

The first preparation attempt on September 8 failed before debugger launch:
PowerShell supplied an uppercase SHA to the strict lowercase argument. The
harness now normalizes that argument; an offline AST fixture evaluates the
actual argument expression. The rejected preparation and its log remain saved.

The subsequent 800x600 diagnostic C reached the map with the unchanged complete
candidate. Its strict initial trace passed, and all three paused surfaces have
SHA-256 `dc9ae0d3a0ba096de98dab638b2e2919e94c28d1132ae065ddd6da72fccb10ff`.
The earlier duplicate did not recur; its cause remains unresolved. Image coverage
still failed on 82 blank cells, and the final failing summary was preserved.
Cleanup, original-executable preservation and both live/isolated save checks
passed. The small evidence reference is
`captures/current/completehd-full-progress-800x600-20260908.json`.
