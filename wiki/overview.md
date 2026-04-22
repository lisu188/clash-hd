---
title: Overview
type: overview
status: active
created: 2026-04-22
updated: 2026-04-22
tags:
  - overview
  - workflow
---

# Overview

This is a personal LLM Wiki: a markdown knowledge base maintained by Codex from
source material chosen by the user.

The wiki has three layers:

- `raw/` contains immutable source material added by the user.
- `wiki/` contains agent-maintained knowledge pages.
- `AGENTS.md` contains durable operating rules for Codex and future agents.

## Add Sources

Put new documents in `raw/inbox/`. Do not edit or reorganize raw sources during
ingest. After Codex creates wiki pages and you approve the result, you can ask
Codex to move the source into `raw/processed/`.

## Ask Questions

Ask Codex to search the wiki and answer from cited pages. Good answers should
separate sourced facts, interpretation, uncertainty, contradictions, and open
questions.

## Maintain The Wiki

Use [[Index]] as the catalog and [[Log]] as the chronological record. Run the
linter after edits:

```powershell
python tools/wiki_lint.py
```

Search the wiki:

```powershell
python tools/wiki_search.py "topic"
```

