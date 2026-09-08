# Resolution-aware camera recovery (validation only)

`tools/build_framed_camera_candidate.py` builds an opt-in Framed + minimap
candidate that clamps camera coordinates before the initial paint and full
redraw. The launcher and previous builders remain unchanged. This is an actual
emitted x86 patch, not only the pure display planner's camera calculation.

## Behavior

Changing the viewport changes its legal maximum camera position. For a 100x100
world, a camera at (89,92) fits Framed 800x600 but exceeds the Framed 1280x720
limit of (81,90). The existing initial/full redraw gates reject that position.
The new validation stage clamps it to (81,90) before native tile pointer
formation. Negative values clamp to zero. Already valid coordinates keep their
values. The patch changes in-memory camera fields, not a save's file format or
world/unit coordinates, and does not write save files.

Both dimensions are validated BEFORE either axis is stored. World width and
height must each be between the corresponding full-tile count and 100. Full
tile counts are positive, so these checks also preserve the old minimum-one
condition. Invalid or small worlds reject without changing either camera axis.
This does not install a bounded small-world renderer.

The existing composition-owner, surface, callback, resource and null-pointer
checks run first and are byte-identical. Their native fallback and rejection
paths remain unchanged. The replacement uses EAX/ECX for intermediate values
and EDX as the admitted gameData pointer. Existing enclosing save/restore
frames retain the original register/stack contracts. It introduces no global
scratch, calls, absolute pointer operands, CMOV requirement, or new allocation.

## Byte and source contract

The new stage is the existing framed stage with its final `-validation`
replaced by `-camera-clamp-validation`. It is not silently added to Classic,
the Framed launcher profile, or the stable resolution registry.

The public builder requires the known original executable SHA-256, verifies
the reviewed parent builder hash plus all 14 implementation source pins, and
builds the parent with minimap correction explicitly enabled. It then applies
exactly two equal-length 124-byte replacements inside the existing RX
`.hdcode` section. Prefixes and displaced gate bytes are reconstructed and
checked at the parent's declared initial/full-entry addresses, not searched
across an arbitrary binary. Repeated application and unknown input are rejected.

The image length, PE headers, section layout, entry points and base-relocation
directory remain byte-identical to the intermediate parent. The new branches
are relative and point to existing rejection labels. Any HIGHLOW or declared
relocation overlap causes rejection rather than deleting or guessing entries.
Metadata records original/intermediate/final hashes, source identities, file
offsets, VA/RVA, old/new bytes, rationale, stage and resolution.

`parent_build` describes the intermediate image. Apply its construction and
then the top-level camera `edits` to reconstruct the final image. It is not
metadata for the final payload. The final payload SHA is reported separately.
Old debugger probes and evidence must NOT be reused: `parent_probe_reusable`
is false and this tool deliberately does not emit a purported runtime probe.
A separate source-bound observation recipe and gameplay qualification remain
necessary before runtime claims or launcher adoption.

## Build without launching

In-memory build/byte preflight:

```powershell
python tools/build_framed_camera_candidate.py --original C:\Clash\clash95.exe --resolution 1366x768 --preflight
```

Write a new isolated executable and report:

```powershell
python tools/build_framed_camera_candidate.py --original C:\Clash\clash95.exe --resolution 1366x768 --output C:\ClashTests\camera-1366\clash95_camera_1366x768.exe --report-json C:\ClashTests\camera-1366\camera-build.json
```

Both outputs must be new, distinct files under `C:/ClashTests`, outside the
repository and original game directory. Existing output files and links are
rejected; no overwrite option exists. An interrupted write may leave an
isolated incomplete artifact; a later run rejects it instead of assuming
success. Preflight writes nothing even when output arguments are present.
Neither mode starts the game, a wrapper, CDB or a visible window.

## Validation

```powershell
python tools/test_framed_camera.py -v
```

Byte tests compare the old-gate reconstruction against the ACTUAL existing
full/initial Python emitters, using explicitly synthetic input and test-local
mocked original/PE admission. They also check exact PE-image reconstruction,
source pins, tampering, relocation overlap, unknown input and output boundaries.
They are not substitutes for an original-executable candidate build.

Native tests execute the emitted 32-bit code in isolated source-built worker
processes: freestanding i386 on Linux and an x86 C# allocation/dispatch fixture
on Windows. They exercise ten resolutions through 3840x2160, signed coordinate
extremes, valid-position parity, small/invalid worlds, rebasing, GPR/flags
preservation and memory sentinels. No third-party emulator or game material is
required. A host without x86 execution support reports that coverage as skipped;
the dedicated CI workflow rejects any skips and requires all tests to run.

This work does not establish gameplay, manual input, stable promotion, smaller
world rendering, live internal-resolution changes or new DPI/input behavior.
The safety and evidence boundaries of the original framed renderer still apply.

Format reference: Microsoft PE/COFF base-relocation specification:
https://learn.microsoft.com/en-us/windows/win32/debug/pe-format
