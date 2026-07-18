# First Mission Visual Audit Tests

- Status: PASS
- Generated: `2026-07-18T10:17:51+02:00`
- Runtime policy: repo-only fixture tests; launches only Python child processes for CLI coverage; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows
- Guard policy: proves first-mission visual audit detects stripe signatures, large black UI patches, legacy middle action-bar placement, and diagnostic black frames, and only excuses proxy-black regions with positive real-runtime corroboration, without launching runtime

## Tests

- `first_mission_visual_audit passes a clean first-mission frame`
- `first_mission_visual_audit fails horizontal stripe signatures`
- `first_mission_visual_audit fails large black patch regions`
- `first_mission_visual_audit excuses a proxy-black region only when a real-runtime frame corroborates it as rendered`
- `first_mission_visual_audit keeps a proxy-black region failing when the real-runtime frame is also black`
- `first_mission_visual_audit fails legacy middle action-bar placement`
- `first_mission_visual_audit reports diagnostic black frames`
- `first_mission_visual_audit CLI writes JSON/Markdown and honors --require-pass`
