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
