# Failed thirty-minute hidden map-pan run

Run `hidden-soak-20260905-103139-257-map-pan` finished at `2026-09-05T09:02:15Z` and remains **failed**. The game and CDB terminated cleanly.

The report records event 7 at 5121 ticks and event 8 at 5760 ticks: 639 ticks apart, below the required 640. The probe read the clock separately for scheduling and logging. Its replacement latches one tick per redraw; this does not repair or promote the old evidence.

[Report](report.json), [shared guard](guard.json), and [clock diagnostic](../../current/hidden-soak-pan-clock-diagnostic-current.json) preserve identities, raw artifact hashes and observations. Raw captures and generated probe remain in the external run directory referenced by the report.
