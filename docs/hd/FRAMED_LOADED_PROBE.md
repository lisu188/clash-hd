# Final bounded-stage loaded-byte verification

The combined bounded repaint and mouse-input candidate from
`tools/build_framed_bounded_input_candidate.py` can now emit its own debugger
byte gate with `--probe-cdb`. This closes a tooling gap: probes for earlier
camera-only, bounded-paint-only, and original framed stages are not valid for
the final combined image. It does not change any emitted game instruction,
launcher profile, registry status, or native navigation behavior.

## Build and export

```powershell
python tools/build_framed_bounded_input_candidate.py --original C:\Clash\clash95.exe --resolution 1366x768 --output C:\ClashTests\bounded-1366\clash95_bounded_1366x768.exe --report-json C:\ClashTests\bounded-1366\build.json --probe-cdb C:\ClashTests\bounded-1366\verify-loaded.cdb
```

All three outputs must be new and distinct, under `C:/ClashTests`, outside the
game directory and repository, without symlink/junction traversal. Probe
construction and contract validation finish before any candidate file is
written. The candidate and probe are verified on disk before the JSON report
is published. Interrupted writes may leave incomplete isolated artifacts;
they are not silently overwritten or accepted on the next run.

`--preflight` still writes nothing, even with `--probe-cdb` and other output
arguments. It builds the candidate and optional probe in memory. Omitting the
new option preserves the prior candidate generation path and output bytes.
Neither operation starts a game, debugger, wrapper or visible window.

## What is checked

`tools/framed_loaded_probe.py` uses the final candidate bytes, not the earlier
scalar/base image, for these loaded-memory checks:

- The complete PE header range, including section layout and image size.
- Every selected scalar patch span, including legacy code caves and resolution
  constants. Installed hooks can supersede scalar bytes; the final bytes win.
- Every installed native hook span from the bounded renderer's hook inventory.
- Every byte of the final injected code, including camera recovery, bounded
  repaint and small-world mouse admission. The merged relocation table is
  not misrepresented as executable code.

Construction authenticates the final image hash and code hash, original hash,
all 18 recorded parent implementation/builder source identities, stage,
resolution and feature flags. It verifies both final input edits and reverses
them to reproduce the intermediate parent's hash. It validates installed hook
bytes and their file-offset/RVA/VA mappings, and the final relocation-directory
identity. Metadata is output from the trusted builder, not a signed external
attestation; the CLI does not accept a user-supplied report as a substitute for
building from the verified original.

The report's `loaded_probe` object binds the script hash, generator source,
contract ID, candidate hash, selected ranges, byte count, hook/patch counts,
and expected command count. A generated script is not observed runtime proof.
The parent probe remains explicitly non-reusable.

## Relocated images

The script discovers the executable image base from the x86 PEB at the paused
initial process breakpoint. It does not depend on the executable filename or
assume a fixed load base. For a HIGHLOW field, the expected loaded value is:

```text
(file_value + loaded_base - preferred_base) & 0xffffffff
```

A selected range intersecting only part of an unaligned HIGHLOW field expands
to include all four bytes. Nonrelocated bytes remain exact; relative branches
are not incorrectly rebased. Overlapping relocation fields reject generation.
The base must be aligned and the complete loaded image must fit PE32 space.
The script refuses a non-32-bit debugger context rather than switching its
interpretation silently.

## Executing the script

Use a dedicated x86 CDB session, at the initial process breakpoint, before
other probes, breakpoints in checked code, or target initialization. Starting
a runtime session still requires the existing project approval; this feature
performs no runtime execution automatically. In that already authorized,
paused debugger session, load the generated command file:

```text
$$><C:\ClashTests\bounded-1366\verify-loaded.cdb
```

The script selects MASM expressions and uses debugger-only scratch registers
`$t18` and `$t19`. It does not write target registers or memory, install/clear
breakpoints, resume execution, kill processes or run external commands. It
leaves the target paused and leaves those two scratch registers occupied.
Do not combine it blindly with a probe that already owns them.

Each bounded command verifies at most 16 expressions and advances a sequential
success counter only on a successful read and comparison. A missing, duplicate
or out-of-order command cannot compensate for an unchecked range. A memory
read or expression error cannot advance the chain. No command exceeds 3800
ASCII bytes. Only the complete chain emits the final `BNDLOAD ... result=pass`
marker; mismatched bytes emit a chunk identifier and the final result is fail.
If a debugger error aborts processing before the final marker, the result is
incomplete, not a pass.

A matching result means only that the selected loaded patch ranges matched.
The candidate SHA printed in the marker identifies the expected source file;
the script does not compute a SHA of the entire live executable or process.
It does not establish route completion, drawing, input callbacks, correct
pixels, continuity, or stable promotion. Loaded data may legitimately change
after initialization, which is why this is an initial-breakpoint gate, not a
late-game memory check. Preserve the script, report and debugger log together.

## Tests

```powershell
python tools/test_framed_loaded_probe.py -v
```

Twenty source-only tests cover ten resolutions, complete code/header/hook/
scalar coverage, independent PE loader rebasing in both directions, 32-bit
wrapping, stale parent rejection, corruption at each scope, partial unaligned
relocations, sequential-command integrity, missing reads, metadata failures,
and CLI output boundaries/races. The actual rendered comparison expressions
are parsed and evaluated against independent synthetic loaded-memory images;
this is not execution of CDB's parser or the game. The dedicated Linux/Windows
CI lane requires all new tests without skips. Existing native x86 renderer and
input tests remain separate. Actual CDB execution and real-original candidate
qualification remain outstanding.

Primary format and debugger references:
- https://learn.microsoft.com/en-us/windows/win32/debug/pe-format
- https://learn.microsoft.com/en-us/windows-hardware/drivers/debuggercmds/pseudo-register-syntax
- https://learn.microsoft.com/en-us/windows-hardware/drivers/debuggercmds/masm-numbers-and-operators
