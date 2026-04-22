# Contradiction Resolution Workflow

Use this workflow when a new source conflicts with existing wiki claims.

## Steps

1. Identify the existing claim and its citation.
2. Identify the new conflicting claim and its citation.
3. Keep both claims.
4. Add a `Contradictions` section to affected pages if one does not exist.
5. State the conflict plainly.
6. Link affected pages together.
7. Create or update a question page when more evidence is needed.
8. Add a contradiction entry to `wiki/log.md`.
9. Run `python tools/wiki_lint.py`.

## Contradiction Note Shape

```markdown
## Contradictions

- `Contradiction`: Source A says one thing, while Source B says another.
  Current status: unresolved. Citations: [source page: [[Source A]]],
  [source page: [[Source B]]].
```

