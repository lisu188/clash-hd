# LLM Wiki Agent Operating Schema

## Project Purpose

This repository is a personal, Obsidian-compatible, LLM-maintained markdown wiki.
The user curates durable source material in `raw/`. Codex and future LLM agents
read those sources, extract stable knowledge, and maintain `wiki/` as a
compounding knowledge base with summaries, entities, concepts, contradictions,
backlinks, syntheses, comparisons, questions, and a chronological log.

The wiki is not a transient chat answer and not just a search index. Treat it as
the user's long-lived memory artifact.

## Directory Ownership Rules

- `raw/`: User-owned source of truth. Do not edit raw files.
- `raw/inbox/`: New user-provided sources waiting for ingest.
- `raw/processed/`: Sources moved here only after explicit user approval.
- `raw/assets/`: User-provided images, PDFs, media, and other supporting files.
- `wiki/`: Agent-maintained markdown knowledge base.
- `wiki/sources/`: One source-summary page per ingested source.
- `wiki/entities/`: People, organizations, projects, products, places, works,
  datasets, and other named things.
- `wiki/concepts/`: Reusable ideas, terms, methods, patterns, and theories.
- `wiki/syntheses/`: Cross-source synthesis pages.
- `wiki/questions/`: Open questions, research threads, and unresolved decisions.
- `wiki/comparisons/`: Structured comparisons between entities, concepts,
  sources, or options.
- `meta/templates/`: Page templates. Update when page conventions evolve.
- `meta/workflows/`: Human-readable workflows for ingest, query, lint, and
  contradiction handling.
- `tools/`: Small dependency-free helper scripts.

## Safety Rules For Raw Sources

- Never modify, rewrite, normalize, OCR, rename, delete, or move files under
  `raw/` unless the user explicitly asks.
- Moving a file from `raw/inbox/` to `raw/processed/` requires explicit user
  approval for that specific file or batch.
- If a raw source appears corrupt, duplicated, or misnamed, document the issue in
  `wiki/questions/` or `wiki/log.md`; do not fix the raw file silently.
- Derived pages in `wiki/` may quote only small excerpts as needed and should
  prefer paraphrase plus precise citations.

## Markdown Conventions

- Prefer plain markdown that reads well in Obsidian and any text editor.
- Every page under `wiki/` must have YAML frontmatter.
- Prefer Obsidian wikilinks for internal links: `[[Page Name]]`.
- Use descriptive Title Case page headings.
- Use kebab-case filenames for source pages and new wiki pages.
- Keep sections skimmable: short paragraphs, compact lists, and explicit status
  labels.
- Avoid creating empty pages unless they are required index/log/overview files or
  user-requested placeholders.
- Do not fabricate facts, source titles, people, organizations, or citations.

## Source Citation Rules

Every factual claim derived from a source needs a citation.

Acceptable citation forms:

- Raw source path: `[source: raw/inbox/file-name.ext]`
- Source summary page: `[source page: [[Source Title]]]`
- Combined citation for important claims:
  `[source: raw/processed/file-name.ext; source page: [[Source Title]]]`

Citation expectations:

- Cite claims at the bullet or paragraph level.
- Page-level `source_path:` frontmatter is useful but not enough for new claims.
- Synthesis pages must distinguish sourced facts from interpretation.
- If a claim is inferred from multiple pages, cite all relevant source pages.
- If no source supports a statement, label it as interpretation, uncertainty, or
  an open question.

## Ingest Workflow

Use this flow when the user asks to ingest one or more files from `raw/inbox/`.

1. Identify the exact raw source path(s).
2. Read the source material without modifying it.
3. Create or update one page in `wiki/sources/` per source using
   `meta/templates/source-summary.md`.
4. Extract durable entities into `wiki/entities/` and concepts into
   `wiki/concepts/` when they are likely to recur.
5. Update or create synthesis, question, and comparison pages only when the
   source supports them.
6. Add backlinks between related pages using wikilinks.
7. Record contradictions instead of overwriting conflicting claims.
8. Append an entry to `wiki/log.md`.
9. Run `python tools/wiki_lint.py`.
10. Ask before moving source files from `raw/inbox/` to `raw/processed/`.

## Query Workflow

Use this flow when the user asks a question against the wiki.

1. Search the wiki with `python tools/wiki_search.py "<query>"`.
2. Read the most relevant wiki pages and their cited source summaries.
3. If the answer depends on raw sources, inspect the cited raw files as needed.
4. Answer from the wiki first, with citations to source pages or raw paths.
5. Separate sourced facts, interpretation, uncertainty, contradictions, and open
   questions when the answer is not straightforward.
6. If the query reveals a durable insight or gap, update the appropriate wiki
   page and append to `wiki/log.md`.

## Lint Workflow

Run:

```powershell
python tools/wiki_lint.py
```

Fix errors before considering maintenance work done. Warnings should be reviewed
and either fixed or consciously left in place when they are conservative false
positives.

The linter checks:

- Missing `wiki/index.md` or `wiki/log.md`
- Empty required files
- Missing YAML frontmatter in `wiki/**/*.md`
- Broken Obsidian wikilinks
- Possible orphan pages
- Raw file paths mentioned without citation syntax

## Contradiction Handling

Never silently replace an older claim with a conflicting newer claim.

When sources disagree:

1. Keep the older claim with its citation.
2. Add the newer conflicting claim with its citation.
3. Add a `Contradictions` section or update the existing one.
4. State exactly what conflicts and which source says what.
5. Add or update a page in `wiki/questions/` if resolution requires more work.
6. Link affected pages to the contradiction note.
7. Append the contradiction to `wiki/log.md`.

Use labels:

- `Sourced fact`
- `Interpretation`
- `Uncertainty`
- `Contradiction`
- `Open question`

## Logging Format

`wiki/log.md` is append-only. Add newest entries near the top unless the user
chooses another convention.

Use:

```markdown
## [YYYY-MM-DD] ingest | Source Title
- Source: raw/path
- Pages created:
- Pages updated:
- Contradictions:
- Open questions:
```

For non-ingest maintenance:

```markdown
## [YYYY-MM-DD] maintenance | Short Title
- Trigger:
- Pages created:
- Pages updated:
- Checks run:
- Notes:
```

## Page Templates

Use templates from `meta/templates/`:

- `source-summary.md`
- `entity.md`
- `concept.md`
- `synthesis.md`
- `question.md`
- `comparison.md`

Templates are conventions, not cages. Preserve required frontmatter and source
citation sections, but adapt section detail to the source.

## Naming Rules

- Source summary filename: kebab-case source title, for example
  `wiki/sources/source-title.md`.
- Entity filename: kebab-case canonical name, for example
  `wiki/entities/jane-doe.md`.
- Concept filename: kebab-case concept name.
- Synthesis filename: kebab-case thesis or topic.
- Question filename: kebab-case short question.
- Comparison filename: `a-vs-b.md` or a clear descriptive comparison name.
- H1 heading: human-friendly Title Case.
- Wikilink text should usually match the target page H1.

## Done Criteria

An agent maintenance task is done when:

- Raw sources were not mutated.
- Relevant wiki pages were created or updated.
- Claims include citations or are labeled as interpretation/uncertainty.
- Contradictions and open questions are recorded.
- `wiki/log.md` has an entry when durable wiki state changed.
- `wiki/index.md` links important new pages.
- `python tools/wiki_lint.py` passes without errors.
- The final response summarizes changed pages and any residual uncertainty.

## Updating This File

When the workflow evolves, update `AGENTS.md` in the same change as the workflow
or tool update. Future agents should not have to reconstruct project rules from
chat history.

