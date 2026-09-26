<a id="codex-cloud-handoff"></a>

# Portable fixtures and cloud checks

This directory packages portable Clash95 HD fixtures that can be inspected
without the local Windows install, debugger tools or proprietary game binaries.
Use the [documentation index](../docs/hd/README.md) to find the current owning
guide and the [development guide](../docs/hd/DEVELOPMENT.md) for check selection.

## What Cloud Codex Can Do

- Edit repository code, docs, and dependency-free Python helpers.
- Inspect `AGENTS.md`, `README.md`, patch notes, probe scripts, and archived
  fixture evidence.
- Run the cloud-safe validation command:

```bash
python tools/cloud_check.py --mode cloud
```

- Run the archived HD map gate directly:

```bash
python tools/hd_map_smoke_matrix.py \
  --captures-root cloud/fixtures/evidence/hd-map/runs \
  --patch-report-json cloud/fixtures/evidence/hd-map/patch-stage-report.json \
  --require-pass
```

## What Stays Local

- Fresh CDB, DirectDraw, DirectInput, Ghidra, x32dbg, or GUI validation.
- Building patched executables from `C:\Clash\clash95.exe`.
- Copying wrapper DLLs or debugger tooling.
- Any work that needs game assets, saves, CD/ISO content, dumps, or proprietary
  executable files.

Cloud results that affect runtime behavior should be treated as candidate
changes until a local Windows run produces fresh evidence.

## Fixture Tree

`cloud/fixtures/` is a searchable bundle, not an opaque dependency archive:

- `ghidra-out/` contains lightweight exported metadata, imports, and function
  inventory. It deliberately excludes `selected_decompilation.c`.
- `evidence/hd-map/` contains the historical HD map archived patch report, the
  paired normal/forced-visible post-owner evidence, and screenshots.
- `evidence/castle-barracks-centered/` contains the historical castle/barracks
  centered UI proof artifacts.
- `manifest.json` records each fixture file, source, SHA-256, byte count,
  reason, and exclusion policy.

Rebuild fixtures on the local Windows machine with:

```powershell
python tools\build_cloud_fixtures.py --manifest cloud\fixtures\manifest.json --refresh
```

Use a zip only for upload-only situations:

```powershell
python tools\build_cloud_fixtures.py --manifest cloud\fixtures\manifest.json --zip
```

The committed directory tree is preferred because Codex can search it directly.
Do not commit `cloud/cloud-fixtures.zip`.

<a id="current-cloud-safe-next-step"></a>

## Finding current work

Use the tracked [current handoff](../docs/hd/AGENT_HANDOFF.md) for active work.
Ignored `.codex-loop/` notes are scratch history, not an authoritative task
queue. The fixture manifest pins a bounded historical evidence set; passing
those fixtures does not verify a newer candidate, ordinary input or release
acceptance. Fixture regeneration writes files and requires the recorded source
artifacts to exist; do not infer their availability from retained metadata.
