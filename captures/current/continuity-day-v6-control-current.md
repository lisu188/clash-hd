# v6 hidden day control: native return observed, strict trace failed

Run `cdb-surface-dump-20260905-135344` executed on 2026-09-05 under the user's
[debugger approval](continuity-day-v6-control-approval-current.json), bound to
the [prepared plan](continuity-day-v6-control-run-plan-current.json).

The [166 byte records](continuity-day-v6-control-patch-stage-current.json)
and outer software-surface gate pass. Native next-player call 4 returned with
the checked stack after day 1→2. No banner override was used; one held-left
and one held-right query were changed to released after the bounded wait.
The release trace ended explicitly before the post-day redraw.

**The [strict continuity report](continuity-day-v6-control-current.json) fails.**
Raw log line 265 repeats a mouse input-return marker following the matching
call at line 263 and return at line 264. This happens during advance 2,
before release-trace closure. All 21 failed-HRESULT return observations are
retained. The duplicated marker is not discarded or treated as a successful
input event; its cause requires thread/stack-aware investigation.

Recorded live game/debugger PIDs 33656/11392 were both absent after terminal
exec session 94873 exited 0. The cleanup observation binds their recorded
identities and all run hashes. Candidate SHA-256:
`0A75CF35F42EFE1E44FBA1AC4031EAAE5323CDFF51AA19D261C36C5BB84691C2`.
Generated probe SHA-256:
`41483758D0C79E516E56A272FA2063CD30F376F6BC46965B4285775154B8A4DD`.
Raw log SHA-256:
`5A42E7BC4678E700BE155E1D8F4016128981563570F3D69B90DFD0DA4D97CED1`.
Raw surface SHA-256:
`2CF149C0FDC1A5346CE79A27379866D46D1987FA2215D050D497692B15FEE946`.

Raw artifacts remain under
`C:\ClashCaptures\hd-completion\continuity-daydiag-combined-v6-control\cdb-surface-dump-20260905-135344`.
The 800×600 screenshot also [fails the complete action-bar check](action-bar-screenshot-audit-current.md).
Bounded forced calls do not prove ordinary end-turn input, sustained campaign
continuity, visible composition, or promotion. The failed v5 evidence remains
unchanged.
