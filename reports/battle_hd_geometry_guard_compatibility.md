# Battle HD harness geometry-guard compatibility

The first aggregate after integration with main `326e703a` completed with
19/167 failing checks. Its 326 framed fixtures passed without skips. Two
geometry guards rejected the combined extra-probe argument append, producing
ten direct or downstream failures. The complete original result and stdout
are preserved under
`C:\ClashTests\battle-hd-1280x720\aggregate-326-first-complete-19fail\`.

The harness now appends `--extra-probe` in the existing guard-recognized
statement, followed by `--extra-probe-path` and its value under the same
condition. Arguments, ordering, source identity checks and rendered probes
retain their behavior. No guard or fixture assertion was weakened. Candidate
bytes remain `7D04FE9005515DAD4E618DF507103946265D7E2A6421287281C1FC5F112D1E47`.

Validation: 96 before/after argument vectors match across empty, ordinary,
spaced and Unicode paths, three load slots and optional flag combinations.
Both actual geometry contracts and their fixture suites pass; renderer
19/19, complete harness 6/6 and PowerShell parsing pass. These checks launch
no game or debugger. Final harness SHA-256 is
`01FBEE7AEACCEB6237FCF42FAE84AA7D0C1912ABA85FADC2FBAB030C2B1475A8`.

Five Python runtime-safety scanner findings are independent of this fix and
predate the battle stage. Comparing source at `326e703a` with this branch
shows identical matched lines in `src/launcher/gui.py`,
`tools/framed_army_portrait_trace.py`, `tools/framed_army_transition_trace.py`,
`tools/framed_primary_surface.py` and `tools/run_framed_offline_tests.py`.
The first four involve ordinary Tk calls, platform strings, error-regex text
or a docstring; the offline runner also contains real Python fixture-worker
subprocess calls. Existing scanner policy leaves these unclassified. Neither
the scanner nor these findings is changed or relabeled as passing here.

Missing castle raw evidence and long/manual release proof remain separate
from expanded-battle acceptance. The final aggregate rerun uses
`C:\ClashTests\battle-hd-1280x720\aggregate-final-geometry-compatible.log`;
its completed result belongs in the current battle validation report.
