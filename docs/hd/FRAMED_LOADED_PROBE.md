# Final bounded-stage loaded-byte verification

The combined bounded repaint and mouse-input candidate from
`tools/build_framed_bounded_input_candidate.py` can emit its own debugger
byte gate with `--probe-cdb`. Probes for earlier camera-only,
bounded-paint-only, and original framed stages are not valid for the final
combined image. This tool does not change emitted game instructions,
launcher profiles, registry status, or native navigation behavior.

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

Generated command files use ASCII with explicit CRLF line endings, including
when generated on Linux. Do not normalize the exported script to LF: the
Windows system debugger engine tested here loses command prefixes when reading
LF-only files through `ExecuteCommandFile`. The documented block loader is
also tested against the exact exported CRLF bytes. The generator source hash,
contract ID and script hash bind the output; regenerate the probe and matching
report after upgrading this generator. Do not rewrite an old probe or reuse
its old hash. Use a new output directory to preserve existing artifacts.

## What is checked

`tools/framed_loaded_probe.py` uses the final candidate bytes, not the earlier
scalar/base image, for these loaded-memory checks:

- The complete PE header range, including section layout and image size, with
  the ImageBase loader transformation checked as described below.
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
to include all four bytes. Relative branches are not incorrectly rebased.
Overlapping relocation fields reject generation. The base must be aligned and
the complete loaded image must fit PE32 space. The script refuses a non-32-bit
debugger context rather than switching its interpretation silently.

The PE32 OptionalHeader.ImageBase field at optional-header offset 28 is a
separate loader transformation, not a HIGHLOW relocation entry. In the actual
Windows loader test, a fixture with file ImageBase 0x00400000 loaded at
0x00470000, and its in-memory ImageBase became exactly 0x00470000. No other
header bytes changed. This behavior is observed by the debugger harness before
running the verifier, not inferred from the Python loader model.

The generator now checks those four bytes against the actual loaded base. It
does not exclude the field, accept arbitrary values, or accept either base
indiscriminately. It rejects a HIGHLOW field overlapping ImageBase. Metadata
identifies `loader_image_base_rva` and `loader_image_base_policy` separately
from `relocated_checks`; every other header byte retains its existing check.
This policy is qualified on the tested Windows Server 2022 loader, not claimed
as universal behavior of every historical Windows version. Other loader
behavior must be investigated rather than silently bypassed.

## Executing the script

Use a dedicated x86 CDB session, at the initial process breakpoint, before
other probes, breakpoints in checked code, or target initialization. Starting
a game/runtime session still requires the existing project approval; this
feature performs no runtime execution automatically. In that already
authorized, paused debugger session, load the generated command file:

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
incomplete, not a pass. A successful debugger API return code is not sufficient:
`ExecuteCommandFile` can continue to subsequent lines after a command error.

A matching result means only that the selected loaded patch ranges matched.
The candidate SHA printed in the marker identifies the expected source file;
the script does not compute a SHA of the entire live executable or process.
It does not establish route completion, drawing, input callbacks, correct
pixels, continuity, or stable promotion. Loaded data may legitimately change
after initialization, which is why this is an initial-breakpoint gate, not a
late-game memory check. Preserve the script, report and debugger log together.

## Source-only tests

```powershell
python tools/test_framed_loaded_probe.py -v
```

Twenty-one source-only tests cover ten resolutions, complete code/header/hook/
scalar coverage, independent PE loader rebasing in both directions, exact
loader-normalized ImageBase checking, 32-bit wrapping, stale parent rejection,
corruption at each scope, partial unaligned relocations, sequential-command
integrity, missing reads, metadata failures, and CLI output boundaries/races.
The rendered comparison expressions are parsed and evaluated against
independent synthetic loaded-memory images; these tests do not execute the
Microsoft debugger or the game. Existing native x86 renderer and input tests
remain separate.

## Actual Microsoft debugger-engine tests

`tools/test_framed_loaded_probe_engine.py` contains three portable fixture tests
and eight Windows debugger-engine test methods, with multiple cases per method.
The opt-in `.github/workflows/framed-probe-engine.yml` lane requires all eleven
tests without skips. It compiles an x86 controller with MSVC and checks the
Microsoft signature of the system x86 `dbgeng.dll`; it downloads no debugger
or game binary. Outside that explicitly enabled Windows lane, the eight engine
tests report skips rather than pretending to execute.

To run locally, use a Windows developer shell with MSVC configured for x86:

```powershell
$env:CLASH_DEBUGGER_INTEGRATION='1'; python tools/test_framed_loaded_probe_engine.py -v
```

This is an isolated debugger integration test, not an ordinary repo-only
check. Its controller accepts only the marked, source-generated PE32 fixture
in its own temporary directory. It creates that fixture without a visible
window, stops at the initial loader breakpoint before the fixture entry, and
executes the actual generated commands through both `ExecuteCommandFile` and
`$$><`. It does not attach to an existing process or start Clash. On completion
it terminates only its own fixture session.

Twenty-three debugger sessions cover ten fixed-base resolutions, the block
loader, actual ASLR, corruption in four checked scopes, missing/duplicate/
reordered chunks, stale mouse-gate bytes, unreadable memory, syntax errors and
an intentionally wrong effective processor context. The tests require exact,
whole-line result markers, not substrings echoed from command text. Valid
cases must contain no syntax error or mismatch; negative cases must never
emit an actual pass marker.

The harness snapshots loaded headers and executable sections and records the
instruction pointer before and after verification. It requires the target to
remain paused with identical snapshots and instruction pointer. After the
intentional wrong-context case, only the harness restores the debugger's
inspection context so those assertions can run; the exported probe does not
change effective processor type. This does not claim a snapshot of all process
memory or every CPU register.

Initial verified execution: Windows Server 2022, system x86 DbgEng
10.0.20348.2849, head d704c39ffa0d898dbbd3731f34458a8c8cf2aecf, workflow run
https://github.com/lisu188/clash-hd/actions/runs/34052934026.
All eleven tests passed: twelve valid sessions emitted pass and all eleven
negative sessions emitted fail. The same job passed 21 source-only verifier
and 34 display-plan tests. The retained `debugger-engine-test-report` artifact
contains only JSON logs and fixture/script/generator hashes, never executable
fixtures or debugger DLLs. Raw generator hashes identify the exact checkout
bytes, so LF and CRLF source checkouts can have different contract identities.

This establishes actual Microsoft command-engine behavior for the synthetic
fixtures, not execution of the CDB frontend application or qualification of a
real-original game candidate. Gameplay, route observers, final pixels, manual
input, other Windows loader variants, and stable promotion remain unverified.

Primary format and debugger references:
- https://learn.microsoft.com/en-us/windows/win32/debug/pe-format
- https://learn.microsoft.com/en-us/windows-hardware/drivers/debuggercmds/pseudo-register-syntax
- https://learn.microsoft.com/en-us/windows-hardware/drivers/debuggercmds/masm-numbers-and-operators
- https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/dbgeng/nf-dbgeng-idebugcontrol-executecommandfile
- https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/dbgeng/nf-dbgeng-idebugcontrol-seteffectiveprocessortype
