# Codex Cloud Handoff

This directory packages the parts of the Clash95 HD workspace that are useful in
Codex Cloud without requiring the local Windows install, debugger tools, or
proprietary game binaries.

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
- `evidence/hd-map/` contains the current HD map archived patch report, the
  paired normal/forced-visible post-owner evidence, and screenshots.
- `evidence/castle-barracks-centered/` contains the current castle/barracks
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

## Current Cloud-Safe Next Step

Use `.codex-loop/NEXT.md` in the local checkout as the authoritative live task
queue. At the time this handoff was built, the next local Windows task was to
continue the full castle overview centering investigation around
`00422180` / `00422020` / `00422305`. Cloud Codex can inspect patch scripts,
probe templates, notes, and fixture evidence for that task, but fresh proof
still needs local CDB.
