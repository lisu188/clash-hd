"""Offline validation of bounded native mouse-poll logs, never input proof.

The source host observes the original GetDeviceState CALL, its saved HRESULT,
and the later local-buffer copy. This consumer binds those records to a supplied
authenticated process identity. It does not read or write a target, launch a
process, or convert diagnostic coverage into gameplay or promotion evidence.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re

MARKER = "REAL_MOUSE_POLL_V1"
SCHEMA = "clash95_native_mouse_poll_trace_v1"
REPORT_SCHEMA = "clash95_native_mouse_poll_trace_report_v1"
IDENTITY_KEYS = frozenset("pid tid creation_filetime image_base controller_sha256 session_id".split())
COMMON_KEYS = IDENTITY_KEYS | {"schema", "kind", "epoch", "action_index", "root_esp"}
KIND_KEYS = {
    "start": {"startup_retired", "deadline_tick_ms"},
    "call": set("poll caller call_esp frame_esp entry_esp backend device vtable method buffer pre_hex".split()),
    "return": set("poll return_esp hresult post_hex".split()),
    "copy": set("poll copy_esp local_hex backend_x backend_y primary middle secondary resolved raw_x raw_y".split()),
    "end": {"polls", "pending", "retired_before_hold", "reason"},
}
UINT32 = (1 << 32) - 1
UINT64 = (1 << 64) - 1
LOW_PTR, HIGH_PTR = 0x10000, 0x7FFE0000
MAX_POLLS = 64
CALLERS = (0x4463BD, 0x460930, 0x460A61)


def _require(condition, reason):
    if not condition:
        raise ValueError(reason)


def _uint(value, key, maximum=UINT32, minimum=0):
    _require(type(value) is int and minimum <= value <= maximum,
             f"invalid integer field {key}")


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
    _require(type(expected) is dict and set(expected) == IDENTITY_KEYS,
             "expected identity keys differ")
    for key in ("pid", "tid"):
        _uint(expected[key], key, minimum=1)
    _uint(expected["creation_filetime"], "creation_filetime", UINT64, 1)
    _pointer(expected["image_base"], "image_base")
    _require(expected["image_base"] % 0x10000 == 0 and
             expected["image_base"] + 0x1451CC < HIGH_PTR,
             "expected image base cannot contain native backend")
    _hex(expected["controller_sha256"], "controller_sha256", 64)
    _hex(expected["session_id"], "session_id", 32)


def _record(body, expected):
    _require(body and len(body) <= 4096 and body.isascii(),
             "trace record is empty, oversized or non-ASCII")
    row = json.loads(body, object_pairs_hook=_unique_object,
                     parse_constant=lambda value: (_ for _ in ()).throw(ValueError("invalid JSON constant " + value)))
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
    for key in ("epoch", "action_index"):
        _uint(row[key], key, minimum=1 if key == "epoch" else 0)
    _pointer(row["root_esp"], "root_esp")
    _require(row["root_esp"] >= LOW_PTR + 0x4000,
             "root stack cannot contain bounded poll frames")
    if kind == "start":
        _require(row["startup_retired"] is True, "poll tracing precedes startup retirement")
        _uint(row["deadline_tick_ms"], "deadline_tick_ms", UINT64, 1)
    elif kind == "end":
        _uint(row["polls"], "polls", MAX_POLLS)
        _require(row["pending"] is False and row["retired_before_hold"] is True and
                 row["reason"] == "caller_hold", "trace did not retire cleanly before caller hold")
    else:
        _uint(row["poll"], "poll", MAX_POLLS, 1)
        if kind == "call":
            for key in ("call_esp", "frame_esp", "entry_esp", "backend", "device", "vtable", "buffer"):
                _pointer(row[key], key)
            _pointer(row["caller"], "caller", aligned=False)
            _pointer(row["method"], "method", aligned=False)
            _require(row["vtable"] <= HIGH_PTR - 0x28,
                     "native mouse vtable method span exceeds pointer bounds")
            _hex(row["pre_hex"], "pre_hex", 32)
        elif kind == "return":
            _pointer(row["return_esp"], "return_esp")
            _uint(row["hresult"], "hresult")
            _hex(row["post_hex"], "post_hex", 32)
        else:
            _pointer(row["copy_esp"], "copy_esp")
            _hex(row["local_hex"], "local_hex", 32)
            for key in ("backend_x", "backend_y", "primary", "middle", "secondary", "resolved", "raw_x", "raw_y"):
                _uint(row[key], key)
    return row


def parse_trace(log: str, expected_identity: dict) -> dict:
    """Return structural coverage and raw diagnostics; malformed logs fail closed.

    ``expected_identity`` has exactly pid/tid/creation_filetime/image_base,
    controller_sha256/session_id, taken from the authenticated phase receipt.
    Every closed epoch must cover at least one paired CALL/return/copy. A failed
    HRESULT remains a valid diagnostic observation, never successful input.
    """
    result = dict(schema=REPORT_SCHEMA, scope="native_mouse_poll_diagnostic_only",
                  complete=False, errors=[], observed_marker_count=0,
                  completed_epochs=0, completed_polls=0, failed_hresult_count=0,
                  completed_failed_hresult_count=0, return_observations=[],
                  failed_hresult_with_unchanged_buffer_count=0,
                  local_changed_after_return_count=0, hresults={}, epochs=[], polls=[],
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
    active = None
    pending = None
    root = None
    fatal = False
    last_epoch = 0
    last_action = None
    delta = expected_identity["image_base"] - 0x400000
    for line_number, line in enumerate(log.splitlines(), 1):
        # Other debugger output is allowed; a displaced or malformed marker is
        # rejected instead of silently becoming an ignored trace record.
        if MARKER not in line:
            continue
        result["observed_marker_count"] += 1
        try:
            _require(line.startswith(MARKER + " "), "trace marker is displaced or missing its separator")
            row = _record(line[len(MARKER) + 1:], expected_identity)
            # Retain saved GetDeviceState HRESULTs even when the subsequent
            # copy/end is absent or rejected. This is diagnostic data, not a
            # reason to accept an unpaired record.
            returned_observation = None
            if row["kind"] == "return":
                returned_observation = dict(line=line_number, record=row, paired=False,
                                            hresult_failed=bool(row["hresult"] & 0x80000000))
                result["return_observations"].append(returned_observation)
                result["failed_hresult_count"] += int(returned_observation["hresult_failed"])
                hresult = f"0x{row['hresult']:08x}"
                result["hresults"][hresult] = result["hresults"].get(hresult, 0) + 1
            _require(not fatal, "trace continues after a rejected record")
            kind = row["kind"]
            if kind == "start":
                _require(active is None and pending is None, "duplicate start or overlapping poll epoch")
                _require(row["epoch"] == last_epoch + 1,
                         "epoch sequence is stale, skipped or out of order")
                _require(row["action_index"] == 0 if last_action is None else
                         row["action_index"] in (last_action, last_action + 1),
                         "action sequence is decreasing, skipped or out of order")
                if last_action is not None and row["action_index"] == last_action + 1:
                    _require(row["root_esp"] == root,
                             "post-action epoch changed its retained human root stack")
                # A released hold can be reacquired without another click, and
                # a fresh human entry can supply a new retained root. Both are
                # admitted only here at the same action after clean closure.
                # The direct post-action return must retain the previous root.
                root = row["root_esp"]
                active = dict(epoch=row["epoch"], action_index=row["action_index"], root_esp=root,
                              start_line=line_number, deadline_tick_ms=row["deadline_tick_ms"],
                              polls=0, complete=False)
                result["epochs"].append(active)
                continue
            _require(active is not None, "trace record has no active epoch")
            _require(all(row[key] == active[key] for key in ("epoch", "action_index", "root_esp")),
                     "epoch/action/root stack differs from active trace owner")
            if kind == "call":
                _require(pending is None, "duplicate CALL or overlapping mouse polls")
                _require(row["poll"] == active["polls"] + 1, "mouse poll index is stale or skipped")
                frame = row["frame_esp"]
                _require(frame == row["call_esp"] + 12 and row["entry_esp"] == frame + 0x6C and
                         row["buffer"] == frame + 0x50, "native CALL/frame/buffer stack arithmetic differs")
                _require(root - 0x4000 <= row["entry_esp"] <= root - 28 and
                         root - 0x4000 <= row["call_esp"] < frame and frame + 0x60 <= root,
                         "native poll frame escapes the retained human stack")
                _require(row["caller"] in tuple(value + delta for value in CALLERS),
                         "native poll caller is outside the rebased whitelist")
                _require(row["backend"] == 0x545198 + delta, "native mouse backend differs")
                mouse_interface = [row[key] for key in ("device", "vtable", "method")]
                _require("mouse_interface" not in active or active["mouse_interface"] == mouse_interface,
                         "native mouse device/vtable/method changed within the epoch")
                active["mouse_interface"] = mouse_interface
                pending = {"call": row, "call_line": line_number}
            elif kind == "return":
                _require(pending is not None and "return" not in pending, "unpaired or duplicate mouse return")
                _require(row["poll"] == pending["call"]["poll"] and
                         row["return_esp"] == pending["call"]["frame_esp"],
                         "mouse return poll or restored stack differs")
                pending.update({"return": row, "return_line": line_number})
                returned_observation["paired"] = True
            elif kind == "copy":
                _require(pending is not None and "return" in pending, "mouse copy has no paired CALL/return")
                _require(row["poll"] == pending["call"]["poll"] and
                         row["copy_esp"] == pending["call"]["frame_esp"],
                         "mouse copy poll or stack differs")
                local = bytes.fromhex(row["local_hex"])
                words = dict(backend_x=int.from_bytes(local[0:4], "little"),
                             backend_y=int.from_bytes(local[4:8], "little"),
                             primary=local[12], secondary=local[13], middle=local[14])
                _require(all(row[key] == value for key, value in words.items()),
                         "five copied backend words differ from native local bytes")
                call, returned = pending["call"], pending["return"]
                failed = bool(returned["hresult"] & 0x80000000)
                unchanged = call["pre_hex"] == returned["post_hex"]
                changed_after = returned["post_hex"] != row["local_hex"]
                observation = dict(epoch=active["epoch"], action_index=active["action_index"], poll=row["poll"],
                                   call_line=pending["call_line"], return_line=pending["return_line"],
                                   copy_line=line_number, call=call, returned=returned, copy=row,
                                   hresult_failed=failed, device_buffer_unchanged=unchanged,
                                   local_changed_after_return=changed_after)
                result["polls"].append(observation)
                result["completed_polls"] += 1
                result["completed_failed_hresult_count"] += int(failed)
                result["failed_hresult_with_unchanged_buffer_count"] += int(failed and unchanged)
                result["local_changed_after_return_count"] += int(changed_after)
                active["polls"] += 1
                pending = None
            else:
                _require(pending is None, "epoch ended with an unpaired mouse poll")
                _require(row["polls"] == active["polls"], "epoch end poll count differs")
                _require(active["polls"] > 0, "epoch has no observed mouse-poll coverage")
                active.update(complete=True, end_line=line_number)
                result["completed_epochs"] += 1
                last_epoch = active["epoch"]
                last_action = active["action_index"]
                active = None
        except (ValueError, TypeError) as exc:
            errors.append(f"line {line_number}: {exc}")
            fatal = True
    if pending is not None:
        errors.append("trace ends with an unpaired mouse poll")
    if active is not None:
        errors.append("trace ends without its epoch end record")
    if result["observed_marker_count"] == 0:
        errors.append("no native mouse-poll trace records")
    if result["completed_polls"] == 0:
        errors.append("no complete native mouse-poll observations")
    result["complete"] = not errors and result["completed_epochs"] > 0 and result["completed_polls"] > 0
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
