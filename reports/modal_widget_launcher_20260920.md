# Modal-widget launcher integration — 2026-09-20

The source launcher now exposes `modalwidgets` through its renderer selector,
CLI, resolution manifest and shared display plan. The thin adapter uses the
existing isolated Complete HD preparation/deployment/launch-verification path,
with a different stage, revision, directory and build identity. Classic/800x600
remains the default, and every widget resolution remains experimental.

## Exact source integration

Starting point: `6a0528a1abf04a08b5d3c16a41218e386b0a68d6`.
Reviewed source commit: `86bafb36512a96b6919cc4eb81a03d34186e62ea`.
Integration run: `35499506225` on an isolated Ubuntu 24.04 runner with Xvfb.
Artifact: `10601773862`, `widget-launcher-review`.
Artifact ZIP SHA-256:
`ccc8d67d0fdd16da4ee38b32249435dfbec35898a183cdb5a0c76a174898abf7`.

The one-off integration checked every original Git blob before applying changes,
then matched all eight resulting files against their independently reviewed
SHA-256 identities. It ran the full launcher fixture set, including actual Tk
interface fixtures on an isolated display: **96 methods, zero failures, errors
or skips**. The frozen patcher-source preflight also passed. The resulting
commit was pushed only to the task branch. The downloaded result archive and
all eight archived source files were independently checked against their hashes
and the local reviewed source. The one-off executor, identity-input file and
write-enabled workflow were removed before the PR; none remains in its final
tree.

The same 96 tests passed locally on an isolated Xvfb display. New coverage has
11 methods: profile paths and identity, exact synthetic bundle deployment,
reconstruction despite rehashed tampering, mixed-profile rejection, builder
identity drift, unknown original/output rejection, explicit launch confirmation,
source preflight and drift, packaged-launcher refusal, experimental-only manifest
rules, and CLI/GUI routing. These source/UI fixtures use synthetic candidate
bytes and do not execute the game. Real candidate construction and runtime are
separate evidence lanes, not inferred from these fixture results.

## Reviewed final source SHA-256

- `src/display_plan.py`: `3e5f0e1d273662a9723fb5b72a22de11453a30b9db3d22c17c2ffaaf89997ecb`
- `src/launcher/completehd.py`: `bd84e7d87d0cdecd9a9499d4ba9dc887dcef17ba50f0047b087344e3a23b6e55`
- `src/launcher/gui.py`: `43debd8c4f4916cdb2c01996f60711979f2fc5b2677a76b6a127c9b81f89211e`
- `src/launcher/presets.py`: `cf1aaf810d8a0620b743e62d0d4591091479bf4a77ce47a5049ff9884dda383a`
- `src/launcher/resolutions.json`: `e6df18cb47b3c8d858a8c8f1b60c1a7ed35595d65d3288ab466d88ccf56fb673`
- `src/launcher/run.py`: `50ff3735c1a14055ef96ce49287ce76e534fdc05084bbe6219efc68a59fdcc12`
- `src/launcher/modalwidgets.py`: `e4d05ee12a0a718272ea760495723f21a549fbbd6abe2d2e0f4a37a25f6ed0c6`
- `tools/test_launcher_modalwidgets.py`: `9071fbbba260c585601ad44443dd5ae4a48acff5fdb6e82d7ccf89940c770647`

The runtime patcher sources, existing recipe bytes and historical capture
receipts are unchanged. `--prepare` does not start a game. Play remains an
explicit GUI action or requires both `--launch --yes-launch` on the CLI.
The packaged launcher remains Classic-only. Startup evidence for an experimental
candidate is not map-input, barracks-artwork, save/load, lifecycle or stable
promotion acceptance. Usage is documented in
[`MODAL_WIDGET_LAUNCHER.md`](../docs/hd/MODAL_WIDGET_LAUNCHER.md).
