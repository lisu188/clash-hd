# Correct indexed GDI row stride — 2026-09-20

The diagnostic proxy passed its tightly packed native surface directly to
`StretchDIBits`. Its own comment assumed every width was divisible by four.
The launcher's 802 and 1366 pixel widths violate that assumption: uncompressed
DIB scanlines require DWORD-aligned storage. See Microsoft
[BITMAPINFOHEADER remarks](https://learn.microsoft.com/en-us/windows/win32/api/wingdi/ns-wingdi-bitmapinfoheader).

The presentation-only adapter now returns the original buffer for already
matching strides, otherwise copies only the visible bytes of each row into a
zero-padded DWORD-aligned temporary DIB. It checks dimensions, readable source
extent and multiplication bounds. Native surface pitch, allocations, private
object layout, game patch bytes, hidden non-presenting behavior and palettes
are unchanged. No new screen/window manipulation is introduced.

The production helper itself is compiled into the test, not a separate Python
model. The Linux C++ test validates 57 width/pitch cases. The Windows x86 test
also renders every case through native `StretchDIBits` into a memory DC and
checks all resulting RGB pixels. Both old width-802 and width-1366 layouts are
independently reproduced as failures, using safe padded fixture storage.
There are 17 zero-copy and 40 repacking cases, plus malformed input rejection.
All three test methods pass without skips. No game or live capture is involved.

## Source and observed checks

Old Git blob: `fdb6b06ed8d6ea5d547894d5ad59d61fc71a35f9`.
New CRLF source SHA-256:
`2b2e482e324a4bea302d9457cfeac6566cb7b536a23d636212c06107faef2ffc`.
Source commit: `317ab9834f6b42899b59b79c834a89ee159122cb`.

Windows run `35506574901` passed all native checks, the frozen source preflight,
and the actual x86 proxy build. Artifact `10604755335`, archive SHA-256
`b7b076f6b49cc5bd1a0762980729a41c49402a30dc5f3f216c780effb34cc218`,
contains source, native logs and the DLL build receipt, not the DLL. The archive
was downloaded, checksum-verified, and its source compared byte-for-byte with
the locally reviewed and tested change. The one-off write-enabled integration
workflow and script were removed before the PR; the retained workflow is
read-only and tests source, native memory GDI and compilation only.

Initial run `35506332827` already passed native GDI tests, but its subsequent
legacy PowerShell invocation lacked `Get-FileHash`. It remains failed. Artifact
`10603624683`, archive SHA-256
`11db96cb7c800b3627c18a1640006e0a510cc38e19c5d2d9c879aaef248b2521`,
retains those original test results. Selecting PowerShell 7 fixed the build
invocation; no production byte/check was weakened to repair that environment.

This fixes a concrete presentation defect, not all game resolution behavior.
Actual 802/1366 candidate startup, full-window display, map input, modal screens
and save/load remain separate runtime checks. Historical captures and their
original source identities are not rewritten, and no stable promotion occurs.
