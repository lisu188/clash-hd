# LLM Wiki

This repository is a markdown-first personal knowledge base inspired by Andrej
Karpathy's LLM Wiki pattern: the user curates source material, and an LLM
maintains a durable wiki that compounds over time.

The wiki is designed to work immediately in Obsidian or any markdown editor. No
database, vector index, web app, or external dependency is required.

## Repository Layout

```text
raw/
  inbox/       New user-added source files waiting for ingest
  processed/   Sources moved after explicit user approval
  assets/      User-provided images, PDFs, media, and attachments
wiki/
  index.md     Catalog of wiki content
  log.md       Append-only maintenance and ingest log
  overview.md  Starter guide for this wiki
  sources/     Source summary pages
  entities/    People, organizations, projects, places, works
  concepts/    Reusable ideas, methods, terms, patterns
  syntheses/   Cross-source synthesis pages
  questions/   Open questions and unresolved research threads
  comparisons/ Structured comparisons
meta/
  templates/   Page templates
  workflows/   Operating workflows
tools/
  wiki_search.py
  wiki_lint.py
AGENTS.md      Durable instructions for Codex and future LLM agents
```

## Core Rules

- `raw/` is source-of-truth and user-owned.
- Agents must not edit raw sources.
- Moving files from `raw/inbox/` to `raw/processed/` requires explicit approval.
- `wiki/` is agent-maintained and should stay readable by humans.
- Every sourced wiki claim needs a citation.
- Contradictions are recorded; older claims are not silently overwritten.

## Add A Source

1. Put the source file in `raw/inbox/`.
2. Ask Codex to ingest it using the prompt at the end of this README.
3. Review the generated source summary and any linked entity, concept,
   synthesis, question, or comparison pages.
4. If the ingest looks good, explicitly tell Codex whether to move the raw file
   to `raw/processed/`.

## Ask Codex To Ingest A Source

Use a prompt like:

```text
Ingest raw/inbox/<file-name> into the LLM Wiki. Follow AGENTS.md. Create or
update source, entity, concept, synthesis, question, and comparison pages as
appropriate. Cite every sourced claim. Do not move or modify the raw source
unless I explicitly approve it after review. Run the linter when done.
```

## Query The Wiki

Ask natural questions, for example:

```text
Search the wiki for what we know about <topic>. Separate sourced facts,
interpretation, uncertainty, contradictions, and open questions. Cite the
relevant wiki/source pages.
```

Codex should search `wiki/`, read relevant pages, inspect cited raw sources only
when needed, and update the wiki when a durable insight or gap is found.

## Tools

Search markdown pages under `wiki/`:

```powershell
python tools/wiki_search.py wiki
python tools/wiki_search.py "your query here"
```

Lint wiki structure and links:

```powershell
python tools/wiki_lint.py
```

Both scripts use only the Python standard library.

If `python` is not on your `PATH`, run the same scripts with any Python 3
interpreter path, for example:

```powershell
& 'C:\Users\andrz\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' tools\wiki_lint.py
& 'C:\Users\andrz\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' tools\wiki_search.py wiki
```

## Clash95 HD Map Smoke Reproduction

The HD mod workspace keeps generated executables outside the repository. Use a
fresh, user-owned `C:\Clash\clash95.exe` as input and write candidates under
`C:\ClashTests\...`. Never overwrite `C:\Clash\clash95.exe`, and do not commit
patched executables or game-derived dumps.

Start with the dry-run helper. It verifies the base SHA when
`C:\Clash\clash95.exe` is accessible, prints a unique candidate path, prints the
exact commands it would run, and refuses repository-local candidate output by
default:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\prepare_hd_map_smoke_candidate.ps1 -Json
```

When the plan looks right, run the same helper with `-Execute` from a normal
Windows shell:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\prepare_hd_map_smoke_candidate.ps1 -Execute
```

The manual equivalent is below.

Current HD map stage:

```powershell
$BundledPy = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
if (Get-Command python -ErrorAction SilentlyContinue) {
  $Py = (Get-Command python).Source
} elseif (Test-Path $BundledPy) {
  $Py = $BundledPy
} else {
  throw 'Python 3 was not found on PATH and the bundled Codex runtime was not found.'
}
$Stage = 'gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch'
```

Verify the base executable hash before patching:

```powershell
$Expected = '500055d77d03d514e8d3168506bd10f67cd8569bcc450604ff8192f46cdaf3ae'
$Actual = (Get-FileHash 'C:\Clash\clash95.exe' -Algorithm SHA256).Hash.ToLowerInvariant()
if ($Actual -ne $Expected) {
  throw "Unexpected C:\Clash\clash95.exe SHA-256: $Actual"
}
```

Build a uniquely named candidate outside the repo:

```powershell
$CandidateDir = 'C:\ClashTests\hd-map-smoke'
New-Item -ItemType Directory -Force -Path $CandidateDir | Out-Null
$Candidate = Join-Path $CandidateDir ('clash95_hd_smoke_{0}.exe' -f (Get-Date -Format 'yyyyMMdd_HHmmss'))
& $Py .\patch_clash95_hd.py `
  --input 'C:\Clash\clash95.exe' `
  --output $Candidate `
  --stage $Stage
```

Generate the patch-stage byte manifest. The JSON includes each selected patch's
file offset, RVA, VA, expected old bytes, expected new bytes, actual bytes,
status, group, and rationale note:

```powershell
& $Py .\tools\patch_stage_report.py `
  --exe $Candidate `
  --stage $Stage `
  --require-current-hd-map `
  --write-json .\captures\patch-stage-current-hd-map.json
```

Reproduce the current repo-only HD map smoke matrix with the existing normal and
forced-visible CDB surface-dump evidence:

```powershell
& $Py .\tools\hd_map_smoke_matrix.py `
  --patch-exe $Candidate `
  --stage $Stage `
  --normal-run .\captures\cdb-surface-dump-20260506-190037 `
  --forced-run .\captures\cdb-surface-dump-20260506-201114 `
  --require-pass `
  --write-json .\captures\hd-map-smoke-current.json `
  --write-markdown .\captures\hd-map-smoke-current.md
```

The current known-good matrix expects:

- `patch_stage.status = pass`
- `patch_stage.status_counts.patched = 118`
- `patch_stage.status_counts.original = 0`
- `patch_stage.status_counts.unexpected = 0`
- `post_owner_evidence.status = pass`

This smoke matrix does not launch the game or CDB. It proves that a freshly
generated candidate has the current HD map patch bytes and matches the archived
normal/forced-visible CDB evidence. To create new visual evidence, use the
hidden-desktop CDB surface-dump workflow documented in `AGENTS.md`.

Compare two patch-stage manifests without touching executables:

```powershell
& $Py .\tools\patch_manifest_compare.py `
  .\captures\patch-stage-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-20260424.json `
  .\captures\patch-stage-mapdraw-partial12-20260424.json `
  --write-json .\captures\patch-manifest-compare-current-vs-partial12.json `
  --write-markdown .\captures\patch-manifest-compare-current-vs-partial12.md
```

The comparer highlights changed offsets, groups, expected old/new bytes, actual
bytes, and `original` / `unexpected` statuses.

Open `captures/hd-map-evidence-current.md` for the compact current evidence
index. It links the smoke matrix, post-owner evidence matrix, patch-manifest
comparison, and the current screenshot artifacts.

Check that the evidence index links and screenshots still resolve:

```powershell
& $Py .\tools\evidence_index_check.py `
  .\captures\hd-map-evidence-current.md `
  --require-pass `
  --write-json .\captures\hd-map-evidence-current-check.json
```

Current castle/interior validation keeps the stable HD map stage unchanged and
uses this broader stage only for castle-screen evidence:

```powershell
$CastleStage = 'gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-castlecenter-all'
```

After a full castle overview CDB surface-dump run, gate it with:

```powershell
& $Py .\tools\castle_overview_gate.py `
  .\captures\cdb-surface-dump-YYYYMMDD-HHMMSS `
  --require-pass `
  --write-json .\captures\castle-overview-gate-current.json `
  --write-markdown .\captures\castle-overview-gate-current.md
```

That gate intentionally requires the descriptor catalog, no AV rows, an 800x600
surface, and centered 800x600 geometry. The current known gap is the full
castle overview path around `00422180` / `00422020` / `00422305`; barracks-only
centering is already separate evidence and should not promote castle patches
into the default HD map stage by itself.

## Use With Obsidian

Open this repository folder as an Obsidian vault. Obsidian will understand the
`[[wikilinks]]` used in `wiki/`. The repository intentionally avoids custom
plugins and generated app state. You may add an `.obsidian/` folder locally;
workspace/cache files are ignored by `.gitignore`.

## Current Limitations

- Search is simple keyword ranking, not semantic search.
- The linter is conservative and not a full markdown parser.
- No OCR, PDF extraction, vector search, database, or web app is included.
- Source ingest quality depends on the LLM reading the source carefully.
- Empty directories contain `.gitkeep` placeholders so the scaffold is visible
  to Git.

## First Source-Ingest Prompt

After dropping a file into `raw/inbox/`, use:

```text
Ingest raw/inbox/<file-name> into the LLM Wiki. Follow AGENTS.md exactly. Create
a source summary and any useful entity, concept, synthesis, question, or
comparison pages. Use Obsidian wikilinks. Cite every sourced claim with the raw
path or source page. Distinguish sourced facts, interpretation, uncertainty,
contradictions, and open questions. Append an entry to wiki/log.md. Run
python tools/wiki_lint.py. Do not move or modify the raw source until I approve.
```
