# HD Soak Short2 Map-Idle Hidden CDB Follow-up

- Overall: PASS for the bounded hidden diagnostic only
- Status: `cdb_exit_not_reproduced_hidden_memory_proxy`
- Visible soak status: still failed with `unexpected_process_exit`
- Candidate SHA-256: `5E162FA81DF59533E0B99A0DCBC9EA24280DBEC46411AE871E968D6536C08B33`
- Stage: `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch`
- CDB summary: `C:\ClashCaptures\hd-soak-cdb-crash\cdb-surface-dump-20260715-070814\summary.json`
- Launch: hidden desktop, memory-only proxy, `CLASH_PROXY_PRESENT=0`
- Window config preflight: `display=application`, `presentation=windowed`, SHA-256 `0F35B74B13284901C07145FB945575A7F5A5F313E13AEB24392843609ECDA3FE`
- Route: load slot 0 reached `SURFDUMP_PLAYGAME` and `SURFDUMP_READY` at 800x600
- Observation: completed 45 seconds after the surface dump; no target/CDB exit, AV, `App_RequestQuit`, or timeout was observed
- Cleanup: zero Clash95/CDB processes remained; `C:\Clash\clash95.exe` retained SHA-256 `500055D77D03D514E8D3168506BD10F67CD8569BCC450604FF8192F46CDAF3AE`

This diagnostic does not clear the visible failure. The hidden memory-only
DirectDraw proxy differs from the application/windowed wrapper, visible input,
and screen-capture path. The next investigation should focus on that differing
wrapper/input/capture path; no visible rerun is approved by this record.

The protected stable stage remains unchanged.
