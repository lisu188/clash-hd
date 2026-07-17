# HD Soak Short2 Map-Idle WER Follow-up

- Overall: PASS for failure classification
- Status: `application_hang_confirmed_wer_closed`
- Visible soak status: still failed
- Candidate SHA-256: `5E162FA81DF59533E0B99A0DCBC9EA24280DBEC46411AE871E968D6536C08B33`
- Windows event: `AppHangB1`
- Application Hang event 1002: `1`
- WER AppHang event 1001: `2`
- Application Error event 1000: `0`
- Windows action: the nonresponsive candidate was closed at `2026-07-14T17:30:31+02:00`
- WER report ID: `f786a5c6-0b39-460c-9443-af6a6c556eba`

The second capture timed out at `17:30:30.996` while it was still only
enumerating visible windows for the target PID. It never reached foreground
manipulation or GDI capture, and Windows logged the hang/closure immediately
afterward. The harness observed exit code 1 later; that code is therefore an
OS-closed hang outcome, not evidence of a voluntary game exit or an AV crash.

The route input logs prove exact cursor/button geometry, not game callbacks.
The last actual frame remained on the main menu. The hidden CDB follow-up for
the same candidate reached gameplay and stayed live. The harness now records
window responsiveness after launch and intro wait, before and after each route
step, and before each frame using
`EnumWindows`/`GetClientRect`/`IsHungAppWindow`. It stops further input and
capture at the first hung or missing live target window. The harness guard's
`window_health_stop` check passes, so the next step is a fresh tokened,
explicitly approved windowed retry.

The archived WER report directory exists but is not readable under the current
ACL, so no hang stack is claimed. No visible rerun is approved by this record,
and the protected stable stage remains unchanged.
