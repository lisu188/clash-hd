# Ordinary castle entry successor

This validation-only 1024x768 successor addresses the native map-to-castle
admission mismatch. It does not change the protected stable stage, any
predecessor source/recipe, or the user's original executable.

The native caller Building_GetInto (0041EC70) saves the ordinary renderer
0040AD40 in EBX, installs Render_DefaultRH 004617A0 and calls the castle root
at 0041ED6A. Its root return address is 0041ED6F. The inherited owned-canvas
guard at 0057606B expects renderer 0040AD40, so this actual native call is
rejected. Historical six-screen probes called the root 00422180 directly
while renderer 0040AD40 was still installed; they did not exercise this caller.

The exact predecessor is the modalwidgets+nativepresent 1024 candidate:

```text
23c766f439f3f871b6a2b992f22f2efa45b51373b9629cede5235596c519d743
```

The new stage ends in
`-completehd-modalwidgets-nativepresent-ordinarycastleentry-validation`,
with recipe `owned_ordinary_castle_entry_v1`. Only 1024x768 is supported.

## Two-span change

The builder reconstructs the complete predecessor through
`native_present_bounds.build_candidate`, verifies its exact SHA and native
caller/root bytes, then changes only:

- Six bytes at 00576075: the old rejection JNE becomes JMP plus NOP.
- Ninety-six verified zero bytes at 00647B74: a preserving caller guard in the
  final .hdpblit RX section's padding, after the active relocation directory.

The existing comparison remains intact. Existing ordinary-map acceptance is
unchanged. An old rejection may continue only when the owner is 004617A0,
saved root EBX is 0040AD40, saved root ESI is 004617A0, the try_enter caller is
005767A9, its root-stack argument equals the authenticated wrapper's actual
stack location, and the native root return is 0041ED6F. Every mismatch takes the
original rejection. The guard preserves registers, EFLAGS and stack. Its
address operands use a local EIP anchor and relative displacements; the
complete HIGHLOW inventory, section headers and file size remain unchanged.

The remaining original checks for phase/fault, surface identity, lower/post
ownership, primary, OS thread, render target, allocation and rollback still
run. The patch never forces an owner or canvas state.

## Reproduction and evidence limits

Use the repository's discovered Python interpreter:

```powershell
python -B tools/test_ordinary_castle_entry.py
python -B tools/test_ordinary_castle_entry.py --source-exe C:/Clash/clash95.exe --require-machine-tools
python -B tools/build_ordinary_castle_entry_candidate.py --original C:/Clash/clash95.exe --preflight
python -B tools/build_ordinary_castle_entry_candidate.py --original C:/Clash/clash95.exe --output C:/ClashTests/hd-completion/ordinary-castle-successor-1024x768-20260924-a/candidate.exe
```

The CLI refuses existing bundle members and outputs outside C:/ClashTests.
It creates a candidate, manifest and targeted loaded-byte verifier only.
The verifier uses ordered completion in pseudo-register t19; a failed memory
read cannot fall through to its completion marker.
It does not launch the game/debugger, alter the original or record approval.

The Unicorn fixtures execute the actual inherited root hook, try_enter and
native base/member constructor. Allocation, free and OS-thread APIs are
explicit synthetic ABI models. They exercise ordinary-map compatibility,
native-call admission, each invalid caller context, retained admission
prerequisites, both allocator failures, register/flags/stack preservation,
and a relocated image. This establishes code behavior in synthetic memory.

Runtime remains separate. A controlled native Building_GetInto invocation
can diagnose admission and first presentation but is not a campaign mouse
click. Ordinary campaign input, complete castle/building rendering, normal
exit restoration/freeing, visible composition and promotion require their
own matching evidence. The existing September 21 captures show castle owner
with an HD map surface; they did not record the admission guard itself.
No historical capture is relabeled as successor proof.

## Current verification and next integration

The [first September 26 run](../../reports/ordinary-castle-entry-verification-20260926.json)
passed nine source/byte methods and skipped six CPU methods because the deleted
local tool directory had contained Unicorn. The separate
[fresh CPU follow-up](../../reports/ordinary-castle-entry-verification-20260926-b.json)
passes all 15 methods with zero skips using Unicorn 2.1.4 and the original-backed
candidate. Its intermediate source-drift and sandbox-import failures are retained
in that report. The original SHA and patcher source hashes remain unchanged.

Install or discover a usable Unicorn environment before requiring machine tests;
`--toolchain` accepts an existing local dependency directory. A namespace-only
import is not evidence that its native engine is available. This fixture tests
inherited entry, rollback and caller preservation in synthetic memory, not a
live game or normal castle exit.

The user confirmed removal of C:/ClashTests and C:/ClashCaptures. The retained
[baseline manifest](../../reports/ordinary-castle-entry-baseline-20260924.json)
records the earlier negative diagnostic, but its raw files cannot now be
rehash-checked or shown. No successor screenshot, complete rendering, normal
exit or input acceptance is asserted from unavailable artifacts.

Next runtime acceptance must measure the normal root return, phase zero,
leave_status one, allocations equal frees equal one, zero fault, restoration
of the original physical/render surfaces before map redraw, and the native
caller's renderer restoration. Entry allocation or the first present alone
cannot prove this lifecycle. All building interiors require their own checks.

The separate [matrix successor](ORDINARY_CASTLE_ENTRY_MATRIX.md) extends admission
across the six existing resolutions while retaining this exact-parent builder
and its historical identities.
Small-world rendering/input and widened tactical battle remain separate
integration work; this checkpoint does not satisfy the full HD completion goal.
