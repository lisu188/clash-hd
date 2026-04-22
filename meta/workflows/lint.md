# Lint Workflow

Run the linter after wiki edits:

```powershell
python tools/wiki_lint.py
```

## What It Checks

- Required wiki files exist.
- Required wiki files are not empty.
- Wiki markdown pages have YAML frontmatter.
- Obsidian wikilinks resolve to existing wiki pages.
- Likely orphan pages are reported.
- Raw file paths in wiki pages use citation syntax.

## Policy

- Fix linter errors before calling a maintenance task done.
- Review warnings. Some orphan warnings may be acceptable for temporary pages,
  but important pages should be linked from `wiki/index.md` or another page.
- If the linter is too strict or too loose, update `tools/wiki_lint.py`,
  `AGENTS.md`, and this workflow together.

