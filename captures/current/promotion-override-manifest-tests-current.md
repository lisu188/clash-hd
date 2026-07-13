# Promotion Override Manifest Tests

- Status: PASS
- Generated: `2026-07-13T08:54:57+02:00`
- Runtime policy: repo-only fixture tests; launches only Python child processes for CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Guard policy: proves CDB-only promotion overrides require an explicit valid manifest

## Tests

- `promotion_override_manifest treats absent manifest as inactive`
- `promotion_override_manifest validates complete override manifests`
- `promotion_override_manifest rejects missing approval, bad SHA, and stale process evidence`
- `promotion_override_manifest rejects scope/stage/SHA mismatches`
- `promotion_override_manifest CLI writes outputs and fails closed`
