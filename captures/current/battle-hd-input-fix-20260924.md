# Battle HD input fix — 2026-09-24

The 1280x720 validation candidate contains two battle-only input fixes: sprite-aware HD bounds for tactical cursor shapes, and native relative DirectInput accumulation. The protected stable stage and inherited nonbattle mouse behavior remain unchanged.

- Candidate SHA-256: `99D92EC7C8F81DEBF60321DCC5C1B5872C96E3C485FA2BDD7D9332287B3C7E87`.
- Original SHA-256: `500055D77D03D514E8D3168506BD10F67CD8569BCC450604FF8192F46CDAF3AE`.
- Byte inventory: 283 patched records, strict original SHA/old-byte/section guards, repeat-build identity, and fresh reproduction against the recorded candidate.
- Status: **validation only; overall acceptance remains false**.

## Changed instructions

| Owner | File offset / VA | Behavior |
|---|---|---|
| Relative update | `05FE61` / `00460A61` | Stage-only 38-byte hook to `00563500`; native sensitivity and signed fixed-point accumulation, then buttons/clamp at `00460A87`. |
| Cursor bounds | `060211` / `00460E11` | Stage-only 38-byte hook to `00563400`; HD dimensions under battle renderer ownership, retaining native sprite margins and scale. |

The appended helpers occupy 60 bytes at `00563500` and 32 bytes at `00563400`. The existing mouse and cursor-switch caves at `004E9810` and `004E99C0` are unchanged. Full exact old/new bytes, RVAs, and artifact hashes are in the companion JSON.

## Verified checks

| Check | Result | Limit |
|---|---|---|
| Native relative-update/recenter emulation | 629 scenarios passed | Device polling and Windows calls are fixtures. |
| Native cursor-switch/clamp emulation | 675 scenarios passed | Includes native same-metadata early return. |
| Existing core emulation | 835 scenarios passed | No game process is launched. |
| Hidden helper diagnostic | 7/7 | Forced calls; real arena is 16x7. |
| Hidden lifecycle diagnostic | 11/14 | Banner, modal and results cursor-return checks fail. |

Both hidden runs passed identity checks and their bounded recorded runtime interval, and the harness confirmed cleanup with no owned processes remaining. Neither strict parser report passes overall acceptance. The helper raw surface is byte-identical to the earlier 2026-09-19 software dump.

The lifecycle queued `(576,360)` but measured banner `(4,324)`, modal `(601,1)`, and results `(576,385)` afterward. Its probe bypasses acquisition and does not record `GetDeviceState` return HRESULTs, so these are failed cursor-return observations without a measured device-error diagnosis.

## Artifact locations

- Build and patch report: `C:\ClashTests\battle-hd-input-fix-20260924\build.json` and `patch-stage.json`.
- Exact source snapshot: `C:\ClashTests\battle-hd-input-fix-20260924\source-snapshot\manifest.json`.
- Reproducible test logs: `C:\ClashTests\battle-hd-input-fix-20260924\focused-checks.json` and its referenced files.
- Helper run: `helper-captures\cdb-surface-dump-20260924-085204`.
- Lifecycle run: `lifecycle-captures\cdb-surface-dump-20260924-085326`.
- Each run contains a fresh `battle-hd-run.json` and strict `battle-hd-report.json/.md` with its own identity, wrapper hash, log hash and explicit forced actions.

No approval record, successful physical/manual input, final wrapper composition, or stable promotion is inferred. The aggregate repo-only refresh is recorded separately.

The user explicitly kept this candidate's visible validation pending and asked
for headless operation by default. `AGENTS.md` now records that preference.
The prepared v3 visible packet is unexecuted and grants no approval.

All 17 focused patch, launcher, battle parser and documentation suites pass;
their logs and source hashes are retained in
`C:\ClashTests\battle-hd-input-fix-20260924\integration-checks\summary.json`.
The [source-binding report](../../reports/battle_hd_source_binding_20260924.md)
records compatibility checks for the shared producer chain.
