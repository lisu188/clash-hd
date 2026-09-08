# Approved hidden day-transition control: return observed, gate failed

Run: `cdb-surface-dump-20260905-130340`, 2026-09-05.
The user's [approval](continuity-day-control-approval-current.json) covered
the [prepared plan](continuity-day-control-run-plan-current.json).

- The combined 800×600 candidate matched SHA-256
  `0A75CF35F42EFE1E44FBA1AC4031EAAE5323CDFF51AA19D261C36C5BB84691C2`.
  All [166 byte records](continuity-day-control-patch-stage-current.json) passed.
- The native path incremented day 1 to 2. At release-loop iteration 8 the
  control overrode one held-left query (left test 8) and one held-right query
  (right test 1). No banner acknowledgment override was used.
- The release routine returned with its checked ESP, then native next-player
  call 4 returned to player 0. Full-day and post-day-redraw markers preceded
  the matching 800×600 host-read software surface. The outer surface gate passed.
- Recorded live game/debugger PIDs 33576/37368 were both absent after exec
  session 65463 completed with exit 0. The cleanup receipt binds their identities,
  candidate, generated probe, log, and raw-surface hashes.

**The continuity gate fails.** The [original result](continuity-day-v5-control-current.json)
preserves all five parser errors plus its incomplete-proof failure. After a
source-backed mode correction, the [separate recheck](continuity-day-v5-control-recheck-current.json)
recognizes the complete controlled-query return/surface sequence but still
fails on the overlapping mouse-call marker at raw log line 309. All 22 failed
DirectInput HRESULT observations remain; the input bytes are not manual events.

The producer had left input breakpoints active after the release routine
returned. The exact reason for the duplicate markers is unproven without thread/
stack identity. v6 now physically closes tracing at that verified return and
requires an explicit trace-end marker. Its sixteen producer and twenty-five
parser fixtures pass. The [v6 run](continuity-day-v6-control-run-review-current.md)
subsequently executed; its [strict result](continuity-day-v6-control-current.md)
also fails, on a duplicate return during advance 2. Both failed reports remain
preserved.

Raw files remain outside the repository at
`C:\ClashCaptures\hd-completion\continuity-daydiag-combined-v5-control\cdb-surface-dump-20260905-130340`.
Generated probe SHA-256:
`B138E21B3798729780E28ACC76250C99C338D2B37DFCD5C643B51FF63D4EAC38`.
Log SHA-256:
`4FEB9184965FA42E2F7DB1912F13E0C565A2090174D34FDD8979126D08EE5BA2`.
Raw surface SHA-256:
`1E441F7A756E241AFDCF924E00E935B24EA8EE1BDAAA585732BD7BD4F2DEF504`.

This is bounded hidden forced-call/control evidence. It does not prove real
end-turn input, sustained multi-day play, visible composition, or promotion.
