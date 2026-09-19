# Exact context for the primary-text candidate

[`modal_primary_text_context.py`](../../tools/modal_primary_text_context.py)
authenticates the separate `-completehd-modalprimarytext-validation` stage,
recipe `owned_modal_primary_text_v1`. It reads an external bundle and rebuilds
the full recipe without launching the executable. This is source and artifact
consistency evidence; actual text composition remains unverified.

## API and strict contract

```python
load_context(original: bytes, candidate: bytes, manifest_path: Path) -> dict
```

The inputs must be immutable bytes and a `.candidate.json` path. The original
must match the known original SHA-256. All three sibling files must be outside
the active checkout and must not alias the original executable or one another.
The supplied candidate must equal the sibling `.exe`; the sibling `.cdb` must
equal the exact reconstructed probe. There is no trusted-context, source-pin,
root, builder, or acceptance override in the production API.

The reader rejects duplicate JSON keys, including escaped and nested duplicates,
non-finite numbers and overflowing numeric literals. Canonical JSON comparison
preserves Boolean, integer and floating-point distinctions while normalizing the
builder's tuples to JSON arrays. The complete declared manifest must equal the
reconstructed manifest, including native byte spans, allocation, hooks, probe
contract, source hashes and ancestor metadata.

Before resolving or reading declared source files, the reader requires exactly
the 34 recipe paths. Paths must be canonical repository-relative POSIX `.py`
names; traversal, absolute names, alternate spellings and filesystem aliases
fail closed. The three additive text implementation hashes are fixed review
pins. All 34 source hashes must match the current bytes and the rebuilt
manifest. The reader snapshots its own source, all recipe sources and the
bundle files, then rejects content, identity or timestamp drift observed during
reconstruction.

The result includes the normalized `manifest`, untouched `probe`, true text
`stage`, `recipe_revision`, `resolution` and `candidate_sha256`; raw and canonical
manifest hashes; executable/probe paths; all recipe source hashes; and
`context_source_sha256`. Explicit `primary_context`, `slots_context` and
`owner_context` expose inherited primary, slots and native-canvas metadata.
Those ancestors retain their actual stages and hashes. Their returned copies
cannot mutate the top-level manifest. No old log or stage marker is projected
or relabeled, and the context does not provide runtime acceptance.

## Verified 800x600 comparison, 2026-09-19

The revised reader completed one fresh full rebuild in **142.738 seconds** and
matched the prepared bundle at:

`C:/ClashTests/completehd-validation-20260919/modal-primary-text-800x600-v1/clash95_modal_primary_text_800x600.candidate.json`

| Identity | SHA-256 |
| --- | --- |
| Candidate | `c30a260afd454cee62f5d49aad877f9db83e8241dd1f129e1d36e0c9877fc818` |
| Raw manifest | `88d3cfed41c67a1c19d8c57454823cc193605fae0e2c0f183de3616f5495c0e7` |
| Probe | `f48ab3d69d080ddd6d82080ae13f453f3c48ba6f308b401606e695f6ba5b1328` |
| Context reader | `d76367fb72d88b9df7aae9810c5f3f4edd29378892354649dbdec5dda1cd9c85` |
| Context fixtures | `0330280502c6fa9431ee28d21240d52440a56f2911ceb49540cf53ca195275d4` |
| Final comparison report | `18643f9b8c2153f1c92d569a5cba33fe24a99a11266a59087860fbbda8d9552b` |

The exact report is
`C:/Users/andrz/AppData/Local/Temp/clash-text-context-800-final-oidd0a4x/comparison.json`.
The two corresponding source files are preserved in its sibling `source/`
directory. The original executable and prepared bundle remained unchanged.
No game, debugger, input or visible capture was launched.

An earlier reader, SHA-256
`81b6ff8ad53b8b8b7643340650dc79d8d9fc869e5637360f7c552931bb0b7998`,
matched the same bundle before the exact 34-path admission check was added.
Its report remains at
`C:/Users/andrz/AppData/Local/Temp/clash-text-context-800-18b_hdiu/comparison.json`,
SHA-256 `b7da52b2c8748fee3647d8bde28ede7a6fcf96d7a60f6377d25817fb66fa8d03`.
Its source and fixture are preserved in `source-before-inventory/` beside that
report. This earlier receipt does not validate the revised reader.

Both reports, both exact two-file source snapshots and the registered fixture
report are also archived byte-for-byte under
`C:/ClashCaptures/completehd-integration-20260919/primary-text-context-validation-v1/`.
The seven-file archive manifest has SHA-256
`f5e0510789d5ebf2364289fc170d95f9780fa56b4868292a5939d9993e98aa95`.
The copies preserve the original report bytes and paths; no test was rerun to
produce the archive.

## Offline coverage and remaining work

The frozen fixture class contains **16 pure offline tests**. It exercises exact
bundle reconstruction with isolated synthetic builders; malformed, mixed and
typed metadata; all 34 source omissions; extra paths; source and file aliases;
changed sources and artifacts; and original/checkout boundaries. Independent
review also confirmed all 36 missing/extra/incomplete source-set cases fail
before resolving declared source paths.

The existing runner selects this class as one bounded group:

```powershell
python tools/run_framed_offline_tests.py --suite test_modal_primary_text_context.TextContextTests --require-complete
```

This group does not perform the full real-candidate rebuild or any runtime.
Observers must bind their own source receipts separately and reauthenticate the
context for each run. Fresh source-bound text events and native/physical/primary
captures remain necessary to evaluate glyph placement, original-location
clearing, overlays and screen transitions. Manual input, continuity, endurance
and release eligibility remain separate requirements.
