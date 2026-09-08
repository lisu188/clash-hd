# Integrated complete-HD candidate

`src/patcher/complete_hd_candidate.py` provides `build_candidate(original,
resolution)` and exclusive `write_candidate(original_path, output, resolution)`.
The patcher CLI selects it only for the exact protected stable stage plus
`-completehd-validation`. The stable default and historical builders are unchanged.

The recipe composes the authenticated framed, minimap, native modal canvas and
army layers. It retains centered native menus, castles and battles. This initial
integration does not include the newer bounded-world/camera experiments or the
widened-battle experiment, and does not claim to fix inherited runtime failures.

Supported fixture resolutions are 800x600, 1024x768, 1280x720, 1280x960,
1920x1080 and 802x602. The default is 800x600. Other complete-HD resolutions fail
closed until their recipe has been checked; existing other profiles remain separate.

The new bundle consists of an executable, `.candidate.json` and canonical `.cdb`
under `C:/ClashTests`. Existing files are never overwritten. The manifest records
the exact base/candidate SHA, resolution, recipe revision, every changed byte
with offset/RVA/VA and old/new bytes, source hashes, probe SHA and both complete
and inherited probe contracts. Timestamp fields are removed only from nested
builder metadata to make repeated construction deterministic. The inherited
candidate and failed evidence retain their original identities.

The candidate's loaded-byte checks run before its complete identity marker.
Consumers must retain the ARMY and PTILE checks as well as the complete marker;
the new stage label cannot substitute for loaded-byte verification.

Run `python tools/test_complete_hd_candidate.py` for portable boundary fixtures
and, when the user-owned original is available, all six in-memory builds and
repeated 800x600/1024x768/1920x1080 reconstruction. No game process is started.
Unknown input, source drift, overlapping records, wrong old bytes, append gaps
and unsafe/existing output paths are rejected.

The initial 1080p image is SHA-256
`95ba0c965d019d0b1c5fb45726e938bf0b1b22ce6fc8353375409477e94a90d0`.
This is a build identity, not a rendering, input, continuity, endurance or
promotion pass. All generated manifests explicitly keep those claims false.
