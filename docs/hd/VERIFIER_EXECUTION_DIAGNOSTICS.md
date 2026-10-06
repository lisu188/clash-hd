# Synthetic verifier execution diagnostics

The shared x86 fixture harness in `tools/test_framed_loaded_probe_engine.py`
retains diagnostics around the existing `IDebugControl.Execute` and
`ExecuteCommandFile` calls. It runs only marked public synthetic executables,
stopped at the initial loader breakpoint. It supplies no game, input,
rendering, endurance, release or promotion evidence.

On 2026-10-06, Small World full-block cases repeatedly timed out at the unchanged
35-second case boundary, after execute-begin and before any scope marker or
execute-end. Their original reports remain failed and their raw stdout/stderr
remain separate historical diagnostics. File-mode runs of the same exact
14,457,121-byte script completed. The missing return does not establish its
cause. Microsoft's [script-file documentation](https://learn.microsoft.com/en-us/windows-hardware/drivers/debuggercmds/-----------------------a---run-script-file-)
states that `$$><` condenses a file into one command block; that behavior alone
does not prove parser cost caused the timeouts.

The self-process watchdog writes a baseline and scheduled 5/10/20/30-second
observations to stderr while the existing call is pending. It records original
QPC, GetProcessTimes and GetProcessIoCounters results/errors and complete scalar
outputs, plus separately atomic callback counts and input-byte counts. It makes
no debugger or target calls, does not execute game instructions, and does not
change the probe, comparisons, invocation mode or external 35-second deadline.

Interpret an observation only when its relevant native API succeeded. Initialized
zero buffers after a failed API are unavailable rather than measured zero. The
live process exit FILETIME is undefined. Process CPU includes all self-process
threads and the watchdog; I/O includes diagnostic output. Callback counters
measure original callback input before stdout text translation; the two atomic
counters are not a transactional pair. Active-before/after and the actual QPC
values constrain interpretation. Scheduled seconds label wait intervals; sampling
and diagnostic overhead also consume real time.

The owned CRT worker is stopped, joined and closed before ordinary completion.
Its join is externally bounded by the unchanged case deadline, not an independent
join timeout. An unknown join retains heap state and handles for process lifetime
to avoid a worker using freed memory. Failed owned operations cannot establish
healthy diagnostic cleanup. A timed-out process may have only partial streams;
the retained ledger distinguishes unknown output from an observed empty buffer.

Watchdog output cannot supply execute-end, source identity, paused context,
unchanged bytes, successful termination or other required acceptance markers.
Retain the complete original stdout/stderr and sticky failures before interpreting
progress. CPU activity without callbacks can narrow a future diagnosis, but does
not independently prove parsing, byte verification, liveness or native cleanup.
