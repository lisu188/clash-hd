#!/usr/bin/env python3
"""Pure PTILE debugger-command instrumentation and output-integrity checks.

This transforms a partial-tile extra probe, not the expanded base probe. Only
debugger pseudo-register $t9 is written. The base probe uses it at initialization
and in the load-menu breakpoint while $t14 == 0; PlayGame sets $t14 before the
initial-paint admission. The caller must preserve that ordering and ownership.

An increasing sequence identifies distinct breakpoint-command executions. A
repeated sequence is still a failure: output replay and reexecution of the reset
breakpoint cannot be distinguished from that observation alone. These checks
never deduplicate output and do not establish native call, render, or runtime
acceptance. The separate initial-paint validator owns those claims.
"""
from __future__ import annotations

import re


_BP = re.compile(r'(?P<head>bp\s*(?P<bp>[0-9]+)\s+(?P<va>[0-9a-f]{8})\s+")'
                 r'(?P<body>(?:\\.|[^"\\\r\n])*)(?P<tail>"[ \t]*)', re.I)
_EVENT = re.compile(r'PTILE_EVENT seq=([0-9]+) bp=([0-9]+) '
                    r'tid=([0-9a-fA-F]{1,8}) eip=([0-9a-fA-F]{1,8}) esp=([0-9a-fA-F]{1,8})')
_CLOSE = re.compile(r'PTILE_TRACE_CLOSED tid=([0-9a-fA-F]{1,8}) '
                    r'eip=([0-9a-fA-F]{1,8}) esp=([0-9a-fA-F]{1,8})')
_MEMBERS = {
    70: ("PTILE_STATUS",),
    71: ("PTILE_STATUS",),
    72: ("PTILE_INCREMENTAL_INPUT", "PTILE_STATUS"),
    73: ("PTILE_MAP_READY",),
    74: ("PTILE_NATIVE_NOOP_EXIT",),
    75: ("PTILE_COMPOSITION_GUARD",),
    76: ("PTILE_INITIAL_ADMISSION",),
    77: ("PTILE_INITIAL_RETURN",),
}
_HOOKS = {70: "full_converge", 71: "full_present", 72: "incremental"}
_PREAMBLE = {"PTILE_CONTRACT_PASS", "PTILE_SCOPE"}
SCOPE = ("Debugger-command output integrity only; native call/return, complete "
         "rendering, cleanup, visible input and promotion require separate evidence.")


def _prefix(bp: int, reset_bp: int) -> str:
    reset = "r @$t9 = 0; " if bp == reset_bp else ""
    return (reset + 'r @$t9 = @$t9 + 1; '
            f'.printf \\"PTILE_EVENT seq=%u bp={bp} tid=%x eip=%p esp=%p\\\\n\\", '
            '@$t9, @$tid, @eip, @esp; ')


def _probe_rows(probe: str, reset_bp: int, *, instrumented: bool):
    if reset_bp not in (73, 76):
        raise ValueError("reset_bp must be readiness 73 or initial admission 76")
    if not isinstance(probe, str) or not probe.isascii() or "\x00" in probe:
        raise ValueError("probe must be non-NUL ASCII text")
    expected = set(range(70, 76 if reset_bp == 73 else 78))
    rows = []
    sites = {}
    for number, line in enumerate(probe.splitlines(keepends=True), 1):
        raw = line.rstrip("\r\n")
        if len(raw) >= 4096:
            raise ValueError(f"line {number}: exceeds bounded CDB command length")
        match = _BP.fullmatch(raw)
        if match:
            bp = int(match["bp"])
            if bp not in expected or bp in sites:
                raise ValueError(f"line {number}: unsupported or duplicate breakpoint {bp}")
            va = int(match["va"], 16)
            if not va or va in sites.values():
                raise ValueError(f"line {number}: zero or duplicate breakpoint site")
            body = match["body"]
            prefix = _prefix(bp, reset_bp)
            if instrumented:
                if not body.startswith(prefix):
                    raise ValueError(f"line {number}: missing exact event instrumentation")
                body = body[len(prefix):]
            if "PTILE_EVENT" in body.upper() or re.search(r'\$t9\b', body, re.I):
                raise ValueError(f"line {number}: event/counter already used")
            if not all(member in body for member in _MEMBERS[bp]):
                raise ValueError(f"line {number}: breakpoint lacks its declared PTILE records")
            sites[bp] = va
            rows.append((line, match, bp))
        else:
            if (re.match(r'\s*(?:bp|bu|bm|ba)\b|\s*bp[0-9]', raw, re.I)
                    or re.search(r'\$t9\b|PTILE_EVENT', raw, re.I)):
                raise ValueError(f"line {number}: unsupported breakpoint/counter grammar")
            rows.append((line, None, None))
    if set(sites) != expected:
        raise ValueError(f"missing supported breakpoint declarations: {sorted(expected - set(sites))}")
    return rows, sites


def instrument_probe(probe: str, *, reset_bp: int) -> str:
    """Prepend one event per command hit; preserve all original command bytes.

    The reset breakpoint must execute first and only once in an accepted trace.
    Arming/disable commands and target register/memory operations are not added,
    removed or reordered. Repeated reset hits fail the event sequence validator.
    """
    rows, _ = _probe_rows(probe, reset_bp, instrumented=False)
    output = []
    for line, match, bp in rows:
        if match is None:
            output.append(line)
            continue
        insertion = match.start("body")
        changed = line[:insertion] + _prefix(bp, reset_bp) + line[insertion:]
        if len(changed.rstrip("\r\n")) >= 4096:
            raise ValueError("instrumented breakpoint exceeds bounded CDB command length")
        output.append(changed)
    return "".join(output)


def validate_event_integrity(log: str, probe: str, *, reset_bp: int) -> dict:
    """Validate raw event sequence, exact sites and per-command record membership.

    ``probe`` must be the instrumented extra used by the run. Every PTILE row,
    including malformed/rejected rows, remains in ``raw_records``. Event and
    boundary records use integer identities and one-based raw log line numbers.
    A close marker finalizes the current block and prohibits later PTILE output;
    its native-site/stack semantics and necessity belong to the caller's phase
    validator. Its absence alone is not an event-integrity failure.
    """
    errors, events, raw_records, boundaries = [], [], [], []
    result = dict(passed=False, errors=errors, events=events,
                  raw_records=raw_records, boundary_records=boundaries, scope=SCOPE)
    try:
        _, sites = _probe_rows(probe, reset_bp, instrumented=True)
    except (ValueError, TypeError) as exc:
        errors.append(f"instrumented probe: {exc}")
        # Preserve all raw observations even when the supplied probe is invalid.
        sites = {}
    current = None
    closed = False

    def fail(line: int, message: str):
        errors.append(f"line {line}: {message}")

    def finish():
        if current is None:
            return
        expected = _MEMBERS.get(current["bp"], ())
        actual = tuple(row["marker"] for row in current["records"])
        if actual != expected:
            fail(current["line"], f"breakpoint {current['bp']} record membership {actual!r}, expected {expected!r}")

    for number, text in enumerate(log.splitlines(), 1):
        if "PTILE_" not in text.upper():
            continue
        marker_match = re.match(r'(PTILE_[A-Z0-9_]+)(?:\s|$)', text)
        marker = marker_match[1] if marker_match else "MALFORMED_PTILE"
        row = dict(line=number, marker=marker, text=text)
        raw_records.append(row)
        if marker == "PTILE_EVENT":
            finish()
            current = None
            match = _EVENT.fullmatch(text)
            if not match:
                fail(number, "malformed event marker")
                continue
            seq, bp = int(match[1]), int(match[2])
            tid, eip, esp = (int(match[i], 16) for i in (3, 4, 5))
            current = dict(line=number, seq=seq, bp=bp, tid=tid, eip=eip, esp=esp, records=[])
            if closed:
                fail(number, "event after trace closure")
            if not 1 <= seq <= 0xFFFFFFFF or seq != len(events) + 1:
                fail(number, "event sequence is not strictly 1,2,3,...")
            if not events and bp != reset_bp:
                fail(number, "first event is not the reset/admission breakpoint")
            if events and bp == reset_bp:
                fail(number, "reset/admission breakpoint executed again")
            if bp not in sites or eip != sites.get(bp):
                fail(number, "event EIP does not match its declared breakpoint")
            if not tid or not esp:
                fail(number, "event thread/stack identity is zero")
            events.append(current)
        elif marker == "PTILE_TRACE_CLOSED":
            finish()
            current = None
            match = _CLOSE.fullmatch(text)
            if closed or not events:
                fail(number, "duplicate or premature trace closure")
            if not match or any(int(value, 16) == 0 for value in match.groups()):
                fail(number, "malformed trace closure identity")
            else:
                boundaries.append(dict(row, **dict(zip(("tid", "eip", "esp"),
                                                       (int(x, 16) for x in match.groups())))))
            closed = True
        elif marker in _PREAMBLE and not events and not closed:
            continue  # Exact contract/stage/SHA checks belong to the caller.
        else:
            if closed:
                fail(number, "PTILE record after trace closure")
            if current is None:
                fail(number, "PTILE record has no command event")
                continue
            current["records"].append(row)
            if marker in {"PTILE_REJECT", "PTILE_CONTRACT_FAIL", "MALFORMED_PTILE"}:
                fail(number, "rejected or malformed PTILE observation")
            if marker not in _MEMBERS.get(current["bp"], ()):
                fail(number, "record is not owned by its command breakpoint")
            if marker == "PTILE_STATUS":
                hooks = re.findall(r'(?:^| )hook=([^ ]+)(?= |$)', text)
                if hooks != [_HOOKS.get(current["bp"])]:
                    fail(number, "status hook does not match its command breakpoint")
            if marker != "PTILE_MAP_READY":
                for field in ("tid", "esp"):
                    values = re.findall(rf'(?:^| ){field}=([^ ]+)(?= |$)', text)
                    if (len(values) != 1 or not re.fullmatch(r'[0-9a-fA-F]{1,8}', values[0])
                            or int(values[0], 16) != current[field]):
                        fail(number, f"record {field} does not match its command event")
    finish()
    if not events:
        errors.append("no command events observed")
    result["passed"] = not errors
    return result
