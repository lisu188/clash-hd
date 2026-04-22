# Ingest Workflow

Use this workflow when the user asks Codex to ingest source material.

## Steps

1. Confirm the source path under `raw/inbox/` or another user-provided raw path.
2. Read the source without modifying it.
3. Create a `wiki/sources/` source-summary page from
   `meta/templates/source-summary.md`.
4. Extract durable entities into `wiki/entities/`.
5. Extract durable concepts into `wiki/concepts/`.
6. Create syntheses, questions, or comparisons only when the source supports
   them.
7. Add citations to every sourced claim.
8. Link pages with Obsidian wikilinks.
9. Update `wiki/index.md`.
10. Append to `wiki/log.md`.
11. Run `python tools/wiki_lint.py`.
12. Ask for approval before moving raw files to `raw/processed/`.

## Ingest Prompt

```text
Ingest raw/inbox/<file-name> into the LLM Wiki. Follow AGENTS.md exactly.
Create or update source, entity, concept, synthesis, question, and comparison
pages as appropriate. Cite every sourced claim. Do not move or modify the raw
source unless I explicitly approve it after review. Run the linter when done.
```

