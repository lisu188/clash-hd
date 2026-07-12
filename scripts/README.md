# PowerShell script layout

PowerShell entrypoints are grouped by purpose so the repository root stays focused on source, notes, and wiki content.

| Directory | Purpose |
| --- | --- |
| `scripts/build/` | Local build helpers, including the DirectDraw surface-dump proxy builder. |
| `scripts/capture/` | Window and client-frame capture helpers. |
| `scripts/cdb/` | Repeatable CDB probe and hidden-desktop surface-dump harnesses. |
| `scripts/debug/` | Interactive debugger launch helpers. |
| `scripts/install/` | Windows debugger/tool installer helpers. |
| `scripts/launcher/` | User-facing HD launcher entrypoint (see `docs/hd/LAUNCHER.md`). |
| `scripts/smoke/` | Visual smoke tests, sandbox runs, and candidate-preparation entrypoints. |

Run scripts from the repository root with `powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\<group>\<script>.ps1 ...` unless a workflow documents a more specific working directory.

`scripts/smoke/run_hd_soak.ps1` is the opt-in endurance harness. It dry-runs by
default and requires `-Execute -AllowVisibleRuntime` before launching Clash95 or
capturing visible frames. The dry-run execute command also includes
`-VisibleRuntimeApprovalExpiresUtc` and `-VisibleRuntimeApprovalToken`, which is
recomputed from the critical command fields plus expiry so edited, stale, or
hand-typed visible runs fail closed. Execution also refuses approval packets
with less than 30 minutes remaining before expiry. Approved visible runs open a
Clash95 game window; the current intro-skip prep is pinned with
`-IntroSkipClickMode postmessage -IntroSkipClicks 8 -SkipPulses 4` and is not
manual DirectInput proof.

Moved root variants that could not be byte-for-byte reconciled are kept under
`scripts/cdb/legacy-root/` for inspection. Prefer the non-legacy grouped
entrypoints for new runs.
