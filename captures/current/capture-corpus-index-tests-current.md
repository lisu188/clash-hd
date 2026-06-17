# Capture Corpus Index Tests

- Status: PASS
- Generated: `2026-06-17T09:48:32+02:00`
- Runtime policy: repo-only fixture tests; launches only Python child processes for CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Guard policy: proves capture references resolve, synthetic fixture/transition placeholders stay non-current, and stale visible-era artifacts cannot become active evidence silently

## Tests

- `capture_corpus_index passes current hidden CDB references`
- `capture_corpus_index fails missing current references`
- `capture_corpus_index ignores fixture-run placeholder references`
- `capture_corpus_index ignores transition-run placeholder references`
- `capture_corpus_index ignores external C:\ClashCaptures evidence paths`
- `capture_corpus_index reports stale visible artifacts without failing`
- `capture_corpus_index fails current visible/sandbox references`
- `capture_corpus_index fails current visible-fallback CDB references`
- `capture_corpus_index CLI writes outputs and fails closed`
