# Tools

This directory contains dependency-light Python helpers for parsing CDB logs,
building evidence summaries, checking patch manifests, guarding policy, and
running repo-only tests.

Keep tools separate by purpose. Do not merge unrelated validators just to reduce
file count; the compact structure comes from moving source families into the
right directories, not from hiding distinct checks inside larger scripts.

Run all tool tests with:

```powershell
Get-ChildItem tools\test_*.py | ForEach-Object { python $_.FullName }
```
