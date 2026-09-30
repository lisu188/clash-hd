"""Strict offline native WM_ACTIVATEAPP diagnostics, never input acceptance.

The source observer follows a bounded set of paired transactions. It samples
each enabled mouse/keyboard COM return before another call can replace EAX.
Reaching the WndProc RET instruction is not observing the callback return, and
a rotating breakpoint does not establish coverage of every activation event.
This consumer reads text only; it never launches or accesses a target process.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re

MARKER = "REAL_ACTIVATION_V1"
SCHEMA = "clash95_native_activation_trace_v1"
REPORT_SCHEMA = "clash95_native_activation_trace_report_v1"
IDENTITY_KEYS = frozenset("pid tid creation_filetime image_base controller_sha256 session_id".split())
COMMON_KEYS = IDENTITY_KEYS | {"schema", "kind", "tx", "tick_ms", "startup_retired"}
ARGUMENT_KEYS = {"hwnd", "message", "wparam", "wparam_low16", "lparam", "wndproc_return", "entry_esp"}
KIND_KEYS = {
    "start": {"initial_stop_armed", "host_start_tick_ms", "deadline_tick_ms", "max_transactions"},
    "activation": ARGUMENT_KEYS | {"branch_esp", "deadline_tick_ms"},
    "outer_call": {"operation", "call_va", "return_va", "call_esp", "backend",
                   "mouse_ready", "keyboard_ready", "joystick_ready"},
    "device_call": {"device_kind", "call_va", "return_va", "call_esp", "device", "vtable", "method"},
    "device_return": {"device_kind", "return_va", "return_esp", "hresult"},
    "outer_return": {"return_va", "return_esp", "eax"},
    "end": ARGUMENT_KEYS | {"epilogue_va", "epilogue_esp"},
    "finish": {"transactions", "pending", "reason"},
}
UINT32, UINT64 = (1 << 32) - 1, (1 << 64) - 1
LOW_PTR, HIGH_PTR = 0x10000, 0x7FFE0000
MAX_TRANSACTIONS = 16
MAX_RECORDS = 2 + MAX_TRANSACTIONS * 8
TRANSACTION_MS = 20000
MIN_HOST_MS, MAX_HOST_MS = 10000, 180000
NATIVE_BASE = 0x400000
BACKEND = 0x545198
EPILOGUE = 0x4618A6
OUTER = {"acquire": (0x4618BB, 0x4618C0), "unacquire": (0x461869, 0x46186E)}
DEVICE = {
    "acquire": {"mouse": (0x47BF63, 0x47BF66), "keyboard": (0x47BF4D, 0x47BF50)},
    "unacquire": {"mouse": (0x47BFB3, 0x47BFB6), "keyboard": (0x47BF9D, 0x47BFA0)},
}


def _require(condition, reason):
    if not condition:
        raise ValueError(reason)


def _uint(value, key, maximum=UINT32, minimum=0):
    _require(type(value) is int and minimum <= value <= maximum, f"invalid integer field {key}")


def _pointer(value, key, aligned=True):
    _uint(value, key)
    _require(LOW_PTR <= value < HIGH_PTR and (not aligned or value % 4 == 0),
             f"invalid native pointer {key}")


def _hex(value, key, length):
    _require(type(value) is str and re.fullmatch(f"[0-9a-f]{{{length}}}", value) is not None,
             f"noncanonical hexadecimal field {key}")


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        _require(key not in result, f"duplicate JSON field {key}")
        result[key] = value
    return result


def _identity(expected):
    _require(type(expected) is dict and set(expected) == IDENTITY_KEYS, "expected identity keys differ")
    for key in ("pid", "tid"):
        _uint(expected[key], key, minimum=1)
    _uint(expected["creation_filetime"], "creation_filetime", UINT64, 1)
    _pointer(expected["image_base"], "image_base")
    _require(expected["image_base"] % 0x10000 == 0 and
             expected["image_base"] + BACKEND - NATIVE_BASE + 0x140 <= HIGH_PTR,
             "expected image base cannot contain native backend")
    _hex(expected["controller_sha256"], "controller_sha256", 64)
    _hex(expected["session_id"], "session_id", 32)


def _record(body, expected):
    _require(body and len(body) <= 4096 and body.isascii(), "trace record is empty, oversized or non-ASCII")
    try:
        row = json.loads(body, object_pairs_hook=_unique_object,
                         parse_constant=lambda value: (_ for _ in ()).throw(ValueError("invalid JSON constant " + value)))
    except RecursionError as exc:
        raise ValueError("trace JSON nesting exceeds parser bounds") from exc
    _require(type(row) is dict, "trace record is not a JSON object")
    kind = row.get("kind")
    _require(type(kind) is str and kind in KIND_KEYS, "unknown trace record kind")
    _require(set(row) == COMMON_KEYS | KIND_KEYS[kind], f"{kind} record keys differ")
    _require(json.dumps(row, separators=(",", ":"), ensure_ascii=True) == body,
             "trace JSON is not canonical compact encoding")
    _require(row["schema"] == SCHEMA, "trace schema differs")
    for key in IDENTITY_KEYS:
        _require(type(row[key]) is type(expected[key]) and row[key] == expected[key],
                 f"trace target identity differs: {key}")
    _uint(row["tx"], "tx", MAX_TRANSACTIONS, 0 if kind in ("start", "finish") else 1)
    _require(row["tx"] == 0 if kind in ("start", "finish") else row["tx"] > 0,
             "lifecycle record must use transaction zero")
    _uint(row["tick_ms"], "tick_ms", UINT64, 1)
    _require(type(row["startup_retired"]) is bool, "startup retirement flag is not boolean")
    if kind == "start":
        _require(row["initial_stop_armed"] is True and row["startup_retired"] is False,
                 "observer was not armed before first GO at the initial stop")
        _uint(row["host_start_tick_ms"], "host_start_tick_ms", UINT64, 1)
        _uint(row["deadline_tick_ms"], "deadline_tick_ms", UINT64, 1)
        _uint(row["max_transactions"], "max_transactions", MAX_TRANSACTIONS, MAX_TRANSACTIONS)
    elif kind == "finish":
        _uint(row["transactions"], "transactions", MAX_TRANSACTIONS)
        _require(row["pending"] is False and row["reason"] in
                 ("host_interval", "host_deadline", "transaction_cap"), "observer finish did not close cleanly")
    elif kind in ("activation", "end"):
        for key in ("hwnd", "message", "wparam", "wparam_low16", "lparam"):
            _uint(row[key], key, 0xFFFF if key == "wparam_low16" else UINT32,
                  1 if key == "hwnd" else 0)
        _pointer(row["entry_esp"], "entry_esp")
        _pointer(row["wndproc_return"], "wndproc_return", aligned=False)
        _require(row["message"] == 0x1C and row["wparam_low16"] == (row["wparam"] & 0xFFFF),
                 "activation message or LOWORD(wParam) differs")
        if kind == "activation":
            _pointer(row["branch_esp"], "branch_esp")
            _uint(row["deadline_tick_ms"], "deadline_tick_ms", UINT64, 1)
        else:
            _pointer(row["epilogue_va"], "epilogue_va", aligned=False)
            _pointer(row["epilogue_esp"], "epilogue_esp")
    elif kind in ("outer_call", "device_call"):
        for key in ("call_va", "return_va"):
            _pointer(row[key], key, aligned=False)
        _pointer(row["call_esp"], "call_esp")
        if kind == "outer_call":
            _require(type(row["operation"]) is str and row["operation"] in OUTER, "unknown native backend operation")
            _pointer(row["backend"], "backend")
            for key in ("mouse_ready", "keyboard_ready", "joystick_ready"):
                _uint(row[key], key)
        else:
            _require(row["device_kind"] in ("mouse", "keyboard"), "unknown native device kind")
            for key in ("device", "vtable"):
                _pointer(row[key], key)
            _pointer(row["method"], "method", aligned=False)
    elif kind == "device_return":
        _require(row["device_kind"] in ("mouse", "keyboard"), "unknown native device kind")
        _pointer(row["return_va"], "return_va", aligned=False)
        delta = expected["image_base"] - NATIVE_BASE
        _require(row["return_va"] in tuple(DEVICE[operation][row["device_kind"]][1] + delta for operation in DEVICE),
                 "native device return address is outside the rebased whitelist")
        _pointer(row["return_esp"], "return_esp")
        _uint(row["hresult"], "hresult")
    else:
        _pointer(row["return_va"], "return_va", aligned=False)
        _pointer(row["return_esp"], "return_esp")
        _uint(row["eax"], "eax")
    return row


def parse_trace(log: str, expected_identity: dict) -> dict:
    """Validate observed paired transactions against an authenticated identity.

    The identity contains exactly pid/tid/creation_filetime/image_base,
    controller_sha256/session_id. ``complete`` describes this finite trace,
    including its clean finish; it never describes all activation events or
    establishes that a callback returned, a startup override actually ran a
    device method, or input/gameplay/promotion succeeded.
    """
    result = dict(schema=REPORT_SCHEMA, scope="native_activation_diagnostic_only", complete=False,
                  errors=[], observed_marker_count=0, completed_transactions=0,
                  observed_device_returns=0, paired_device_returns=0, completed_device_returns=0,
                  failed_hresult_count=0, paired_failed_hresult_count=0,
                  completed_failed_hresult_count=0, hresults={}, return_observations=[],
                  transactions=[], initial_stop_armed=False, clean_finish=False,
                  device_hresult_coverage=False, all_activation_events_observed=False,
                  callback_return_observed=False, startup_acquisition_executed=False,
                  os_input_executed=False, os_input_proof=False, manual_input_proof=False,
                  gameplay_verified=False, gameplay_proof=False, promotion_ready=False)
    errors = result["errors"]
    try:
        _identity(expected_identity)
        _require(type(log) is str, "trace log must be text")
    except ValueError as exc:
        errors.append(str(exc))
        return result
    result["expected_identity"] = dict(expected_identity)
    delta = expected_identity["image_base"] - NATIVE_BASE
    start = active = pending = None
    finished = fatal = retired = False
    last_tick = 0
    phase = "start"
    for line_number, line in enumerate(log.splitlines(), 1):
        if MARKER not in line:
            continue
        result["observed_marker_count"] += 1
        if result["observed_marker_count"] > MAX_RECORDS:
            errors.append(f"line {line_number}: activation trace exceeds its finite record cap")
            fatal = True
            break
        try:
            _require(line.startswith(MARKER + " "), "trace marker is displaced or missing its separator")
            row = _record(line[len(MARKER) + 1:], expected_identity)
            kind = row["kind"]
            raw_return = None
            if kind == "device_return":
                # Preserve authenticated raw results on an incomplete trace;
                # separate paired/completed counts prevent false coverage.
                raw_return = dict(line=line_number, record=row, paired=False, transaction_complete=False,
                                  hresult_failed=bool(row["hresult"] & 0x80000000))
                result["return_observations"].append(raw_return)
                result["observed_device_returns"] += 1
                result["failed_hresult_count"] += int(raw_return["hresult_failed"])
                key = f"0x{row['hresult']:08x}"
                result["hresults"][key] = result["hresults"].get(key, 0) + 1
            _require(not fatal, "trace continues after a rejected record")
            _require(not finished, "trace continues after observer finish")
            _require(row["tick_ms"] >= last_tick, "observer ticks decrease")
            _require(not retired or row["startup_retired"], "startup retirement flag reverted")
            last_tick, retired = row["tick_ms"], row["startup_retired"]
            if kind == "start":
                _require(phase == "start" and start is None, "duplicate or out-of-order observer start")
                interval = row["deadline_tick_ms"] - row["host_start_tick_ms"]
                _require(MIN_HOST_MS <= interval <= MAX_HOST_MS and
                         row["host_start_tick_ms"] <= row["tick_ms"] < row["deadline_tick_ms"],
                         "observer host interval is outside finite bounds")
                start = row
                result["initial_stop_armed"] = True
                phase = "activation"
                continue
            _require(start is not None, "trace record has no observer start")
            if kind == "finish":
                _require(active is None and pending is None and phase == "activation",
                         "observer finished with a pending activation transaction")
                _require(row["transactions"] == result["completed_transactions"], "finish transaction count differs")
                if row["reason"] == "host_deadline":
                    _require(row["tick_ms"] >= start["deadline_tick_ms"], "host-deadline finish precedes its deadline")
                elif row["reason"] == "transaction_cap":
                    _require(row["transactions"] == MAX_TRANSACTIONS, "transaction-cap finish precedes its cap")
                else:
                    _require(row["tick_ms"] < start["deadline_tick_ms"] and
                             row["transactions"] < MAX_TRANSACTIONS, "host-interval finish is expired or capped")
                finished = True
                result["clean_finish"] = True
                result["finish"] = row
                continue
            _require(row["tick_ms"] < start["deadline_tick_ms"], "activation observation exceeds host deadline")
            if kind == "activation":
                _require(active is None and pending is None and phase == "activation",
                         "overlapping or out-of-order activation transaction")
                _require(row["tx"] == result["completed_transactions"] + 1, "transaction sequence is stale or skipped")
                frame = row["branch_esp"]
                _require(LOW_PTR + 0x20 <= frame and frame + 36 <= HIGH_PTR and
                         row["entry_esp"] == frame + 16, "WndProc branch/entry stack arithmetic differs")
                _require(row["tick_ms"] <= UINT64 - TRANSACTION_MS, "activation deadline arithmetic overflows")
                _require(row["deadline_tick_ms"] == min(start["deadline_tick_ms"], row["tick_ms"] + TRANSACTION_MS),
                         "activation deadline differs from the bounded host deadline")
                operation = {0: "unacquire", 1: "acquire"}.get(row["wparam_low16"])
                active = dict(tx=row["tx"], activation=row, operation=operation,
                              start_line=line_number, complete=False, devices=[], skipped_devices=[])
                result["transactions"].append(active)
                phase = "outer_call" if operation else "end"
                continue
            _require(active is not None, "trace record has no active transaction")
            activation = active["activation"]
            _require(row["tx"] == active["tx"], "transaction owner differs")
            _require(row["tick_ms"] < activation["deadline_tick_ms"], "activation observation exceeds transaction deadline")
            _require(kind == phase, f"expected {phase}, observed {kind}")
            frame, operation = activation["branch_esp"], active["operation"]
            if kind == "outer_call":
                pair = OUTER[operation]
                _require(row["operation"] == operation and row["call_va"] == pair[0] + delta and
                         row["return_va"] == pair[1] + delta, "native outer CALL/return or operation differs")
                _require(row["call_esp"] == frame and row["backend"] == BACKEND + delta,
                         "native outer stack or backend differs")
                _require(row["joystick_ready"] == 0, "joystick-ready path is outside this observer scope")
                active["outer_call"] = row
                active["expected_devices"] = [name for name in ("mouse", "keyboard") if row[name + "_ready"] != 0]
                active["skipped_devices"] = [name for name in ("mouse", "keyboard") if row[name + "_ready"] == 0]
                phase = "device_call" if active["expected_devices"] else "outer_return"
            elif kind == "device_call":
                device = active["expected_devices"][len(active["devices"])]
                pair = DEVICE[operation][device]
                _require(row["device_kind"] == device, "native device order or ready-flag branch differs")
                _require(row["call_va"] == pair[0] + delta and row["return_va"] == pair[1] + delta,
                         "native device CALL/return addresses differ")
                _require(row["call_esp"] == frame - 20, "native device CALL stack differs")
                slot = 0x1C if operation == "acquire" else 0x20
                _require(row["vtable"] + slot + 4 <= HIGH_PTR, "native vtable method span exceeds pointer bounds")
                pending = dict(call=row, call_line=line_number)
                phase = "device_return"
            elif kind == "device_return":
                call = pending["call"]
                _require(row["device_kind"] == call["device_kind"] and row["return_va"] == call["return_va"] and
                         row["return_esp"] == frame - 16, "native device return identity or restored stack differs")
                raw_return["paired"] = True
                result["paired_device_returns"] += 1
                result["paired_failed_hresult_count"] += int(raw_return["hresult_failed"])
                active["devices"].append(dict(call=call, returned=row, call_line=pending["call_line"],
                                              return_line=line_number, hresult_failed=raw_return["hresult_failed"],
                                              return_observation=raw_return))
                pending = None
                phase = "device_call" if len(active["devices"]) < len(active["expected_devices"]) else "outer_return"
            elif kind == "outer_return":
                _require(row["return_va"] == OUTER[operation][1] + delta and row["return_esp"] == frame,
                         "native outer return address or restored stack differs")
                # With joystick disabled, EAX is the final enabled device's
                # value, or the original backend argument if both are skipped.
                expected_eax = active["devices"][-1]["returned"]["hresult"] if active["devices"] else BACKEND + delta
                _require(row["eax"] == expected_eax, "outer EAX differs from the final native device result")
                active["outer_return"] = row
                phase = "end"
            else:
                _require(row["epilogue_va"] == EPILOGUE + delta and row["epilogue_esp"] == frame + 16,
                         "native WndProc RET observation or restored stack differs")
                _require(all(row[key] == activation[key] for key in ARGUMENT_KEYS), "WndProc return or arguments changed")
                active.update(end=row, end_line=line_number, complete=True, epilogue_observed=True,
                              callback_return_observed=False)
                result["completed_transactions"] += 1
                result["completed_device_returns"] += len(active["devices"])
                result["completed_failed_hresult_count"] += sum(int(item["hresult_failed"]) for item in active["devices"])
                for item in active["devices"]:
                    item["return_observation"]["transaction_complete"] = True
                active = None
                phase = "activation"
        except (ValueError, TypeError) as exc:
            errors.append(f"line {line_number}: {exc}")
            fatal = True
    if pending is not None:
        errors.append("trace ends with an unpaired native device CALL")
    if active is not None:
        errors.append("trace ends without its paired activation epilogue")
    if not finished:
        errors.append("trace ends without a clean observer finish")
    if result["completed_transactions"] == 0:
        errors.append("no complete observed activation transactions")
    if result["observed_marker_count"] == 0:
        errors.append("no native activation trace records")
    result["device_hresult_coverage"] = result["completed_device_returns"] > 0
    result["complete"] = not errors and result["completed_transactions"] > 0 and finished
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log", type=Path)
    parser.add_argument("--expected-identity", required=True, type=Path)
    args = parser.parse_args(argv)
    identity = json.loads(args.expected_identity.read_text(encoding="utf-8"), object_pairs_hook=_unique_object)
    report = parse_trace(args.log.read_text(encoding="utf-8"), identity)
    print(json.dumps(report, indent=2))
    return 0 if report["complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
