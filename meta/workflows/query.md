# Query Workflow

Use this workflow when the user asks a question against the wiki.

## Steps

1. Run `python tools/wiki_search.py "<query>"`.
2. Read relevant pages under `wiki/`.
3. Follow citations to source-summary pages and raw sources when needed.
4. Answer with clear labels:
   - Sourced facts
   - Interpretation
   - Uncertainty
   - Contradictions
   - Open questions
5. Cite relevant source pages or raw paths.
6. If the answer reveals durable knowledge, update the wiki and log it.

## Query Prompt

```text
Search the wiki for <topic>. Answer from the wiki first. Separate sourced facts,
interpretation, uncertainty, contradictions, and open questions. Cite the
relevant source pages or raw source paths.
```

