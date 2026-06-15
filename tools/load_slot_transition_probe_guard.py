#!/usr/bin/env python3
"""Guard the focused load-slot entry transition extra probe.

This repo-only guard verifies that the late-entry CDB extra probe is ready for
the next hidden-desktop run and that scripts/cdb/run_cdb_surface_dump.ps1 replaces load-slot
placeholders in extra probes. It does not launch Clash95, CDB, wrappers,
PowerShell, or visible windows.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_PROBE = Path("probes/cdb/menu/clash95_load_slot_entry_transition_extra.cdb")
DEFAULT_SURFACE_DUMP_SCRIPT = Path("scripts/cdb/run_cdb_surface_dump.ps1")
DEFAULT_JSON = Path("captures/current/load-slot-transition-probe-guard-current.json")
DEFAULT_MD = Path("captures/current/load-slot-transition-probe-guard-current.md")

RUNTIME_POLICY = "repo-only source inspection; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows"
GUARD_POLICY = (
    "the focused transition extra probe must avoid early 00419B80 coordinate forcing, "
    "late-arm load-row selection only after 0044895A, keep select/accept conditions "
    "parameterized by __LOAD_SLOT__, and the surface-dump harness must replace "
    "load-slot placeholders in extra probe templates"
)

REQUIRED_BREAKPOINTS = {
    "00447780": "main Load callback entry before state write",
    "00419C60": "post-main-callback descriptor return state",
    "00447BF1": "main dispatch wait gate before case switch",
    "00447C0D": "main wait-loop pump call before case switch",
    "00447C1E": "main wait-loop compare after descriptor walker",
    "00447C26": "main wait-loop exit before case switch",
    "00447C3A": "main switch dispatch choice read",
    "00447D61": "main dispatch poll before case entry",
    "0044895A": "real case-5 load-menu entry",
    "0044A140": "load-slot row draw after case entry",
    "00448A45": "load-menu loop after entry",
    "00448A68": "late force-select inside load-menu loop",
    "00448AE3": "late force-accept inside load-menu loop",
    "0044A110": "load accept helper",
    "00444490": "LOADSAVE after accepted slot",
    "0040B660": "PlayGame after LOADSAVE",
}

REQUIRED_MARKERS = {
    "LSTRANS_LOAD_CALLBACK_ENTRY": "callback pre-write state row",
    "LSTRANS_AFTER_MAIN_CALLBACK": "post callback state row",
    "LSTRANS_MAIN_WAIT_GATE": "pre-switch wait-gate row",
    "LSTRANS_WAIT_LOOP_PUMP": "pre-switch wait-loop pump row",
    "LSTRANS_WAIT_LOOP_COMPARE": "pre-switch wait-loop compare row",
    "LSTRANS_WAIT_LOOP_EXIT": "pre-switch wait-loop exit row",
    "LSTRANS_MAIN_SWITCH_DISPATCH": "switch-dispatch row before case jump",
    "LSTRANS_MAIN_DISPATCH_POLL": "main dispatch polling row",
    "LSTRANS_LOAD_MENU_ENTRY": "real load-menu entry row",
    "LSTRANS_LATE_MOUSE_SET": "late mouse placement after load-menu entry",
    "LSTRANS_LOAD_SLOT_DRAW": "load-slot draw row",
    "LSTRANS_LOAD_MENU_LOOP": "load-loop row",
    "LSTRANS_LATE_FORCE_SELECT": "late select force row",
    "LSTRANS_LATE_FORCE_ACCEPT": "late accept force row",
    "LSTRANS_LOAD_ACCEPT_CALL": "load accept helper row",
    "LSTRANS_LOADSAVE": "save load row",
    "LSTRANS_PLAYGAME": "gameplay transition row",
}

REQUIRED_PLACEHOLDERS = (
    "__LOAD_SLOT__",
    "__LOAD_MOUSE_RAW_X__",
    "__LOAD_MOUSE_RAW_Y__",
)

SLOT_CONDITION_BREAKPOINTS = {
    "00448A68": "late force-select must be target-row parameterized",
    "00448AE3": "late force-accept must be target-row parameterized",
}

RUNNER_REPLACEMENTS = (
    "$extraProbeText = $extraProbeText.Replace('__LOAD_SLOT__'",
    "$extraProbeText = $extraProbeText.Replace('__LOAD_MOUSE_RAW_X__'",
    "$extraProbeText = $extraProbeText.Replace('__LOAD_MOUSE_RAW_Y__'",
)

RUNNER_LATE_LOAD_SLOT_MARKERS = (
    "[switch]$LateLoadSlotForcingOnly",
    "__PRE_ENTRY_LOAD_COORD_ACTION__",
    "SURFDUMP_PRE_ENTRY_SLOT_DEFERRED",
)

CALLBACK_SKIP_RE = re.compile(
    r"\bbp\s+00447780\b[^\r\n]*ed\s+00543d7c\s+5[^\r\n]*"
    r"ed\s+00543d78\s+1[^\r\n]*r\s+eip=poi\(@esp\)[^\r\n]*"
    r"r\s+esp=@esp\+4",
    re.IGNORECASE,
)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig", errors="replace")


def status_text(passed: bool) -> str:
    return "PASS" if passed else "FAIL"


def breakpoint_present(text: str, address: str) -> bool:
    return bool(re.search(rf"\bbp(?:\s+/1)?\s+{re.escape(address)}\b", text, re.IGNORECASE))


def has_standalone_go(text: str) -> bool:
    return bool(re.search(r"(?m)^\s*g\s*$", text))


def invalid_temp_registers(text: str) -> list[str]:
    registers = sorted(set(re.findall(r"@\$t([2-9][0-9])\b", text)))
    return [f"@$t{register}" for register in registers]


def slot_condition_uses_placeholder(text: str, address: str) -> bool:
    return bool(
        re.search(
            rf"\bbp\s+{re.escape(address)}\b[^\r\n]*poi\(00543d7c\)\s*==\s*__LOAD_SLOT__",
            text,
            re.IGNORECASE,
        )
    )


def check_probe(path: Path) -> dict[str, Any]:
    failures: list[str] = []
    text = ""
    if not path.exists():
        failures.append(f"missing transition extra probe: {path}")
    else:
        text = read_text(path)

    breakpoints = {
        address: {
            "present": breakpoint_present(text, address),
            "purpose": purpose,
        }
        for address, purpose in REQUIRED_BREAKPOINTS.items()
    }
    for address, record in breakpoints.items():
        if not record["present"]:
            failures.append(f"missing breakpoint {address}: {record['purpose']}")

    markers = {
        marker: {
            "present": marker in text,
            "purpose": purpose,
        }
        for marker, purpose in REQUIRED_MARKERS.items()
    }
    for marker, record in markers.items():
        if not record["present"]:
            failures.append(f"missing marker {marker}: {record['purpose']}")

    placeholders = {placeholder: placeholder in text for placeholder in REQUIRED_PLACEHOLDERS}
    for placeholder, present in placeholders.items():
        if not present:
            failures.append(f"missing placeholder {placeholder}")

    slot_conditions = {
        address: {
            "present": slot_condition_uses_placeholder(text, address),
            "purpose": purpose,
        }
        for address, purpose in SLOT_CONDITION_BREAKPOINTS.items()
    }
    for address, record in slot_conditions.items():
        if not record["present"]:
            failures.append(f"{address} must compare 00543d7c against __LOAD_SLOT__")

    if breakpoint_present(text, "00419B80"):
        failures.append("probe must not install an early 00419B80 descriptor breakpoint")
    if "SURFDUMP_LOAD_COORD" in text:
        failures.append("probe must not reuse SURFDUMP_LOAD_COORD early-descriptor forcing")
    if has_standalone_go(text):
        failures.append("extra probe contains a standalone g command")
    invalid_registers = invalid_temp_registers(text)
    if invalid_registers:
        failures.append(f"probe uses unsupported CDB temp registers: {invalid_registers}")
    callback_skip_preserved = bool(CALLBACK_SKIP_RE.search(text))
    if not callback_skip_preserved:
        failures.append("00447780 callback marker must preserve the existing skip-main-load-callback behavior")

    return {
        "path": str(path),
        "exists": path.exists(),
        "passed": not failures,
        "breakpoints": breakpoints,
        "markers": markers,
        "placeholders": placeholders,
        "slot_conditions": slot_conditions,
        "has_early_descriptor_breakpoint": breakpoint_present(text, "00419B80"),
        "has_standalone_go": has_standalone_go(text),
        "invalid_temp_registers": invalid_registers,
        "callback_skip_preserved": callback_skip_preserved,
        "failures": failures,
    }


def check_runner(path: Path) -> dict[str, Any]:
    failures: list[str] = []
    text = ""
    if not path.exists():
        failures.append(f"missing surface-dump script: {path}")
    else:
        text = read_text(path)

    replacements = {marker: marker in text for marker in RUNNER_REPLACEMENTS}
    for marker, present in replacements.items():
        if not present:
            failures.append(f"missing extra-probe placeholder replacement: {marker}")

    late_load_slot = {marker: marker in text for marker in RUNNER_LATE_LOAD_SLOT_MARKERS}
    for marker, present in late_load_slot.items():
        if not present:
            failures.append(f"surface-dump script cannot disable pre-0044895A load-slot forcing: {marker}")

    insertion_marker = "$probeText = [regex]::Replace("
    if insertion_marker not in text or "$extraProbeText" not in text:
        failures.append("surface-dump script no longer inserts extra probe text into the generated CDB probe")
    if "Extra CDB probe template must not contain a standalone g command" not in text:
        failures.append("surface-dump script no longer rejects standalone g in extra probes")

    return {
        "path": str(path),
        "exists": path.exists(),
        "passed": not failures,
        "extra_placeholder_replacements": replacements,
        "late_load_slot_forcing_only_support": late_load_slot,
        "failures": failures,
    }


def build_guard(
    probe: Path = DEFAULT_PROBE,
    surface_dump_script: Path = DEFAULT_SURFACE_DUMP_SCRIPT,
) -> dict[str, Any]:
    probe_check = check_probe(probe)
    runner_check = check_runner(surface_dump_script)
    checks = {
        "transition_extra_probe": probe_check,
        "surface_dump_runner": runner_check,
    }
    failures: list[str] = []
    for name, check in checks.items():
        if not check.get("passed"):
            failures.extend(f"{name}: {failure}" for failure in check.get("failures", []))

    return {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "passed": not failures,
        "runtime_policy": RUNTIME_POLICY,
        "guard_policy": GUARD_POLICY,
        "required_breakpoints": REQUIRED_BREAKPOINTS,
        "required_markers": REQUIRED_MARKERS,
        "required_placeholders": list(REQUIRED_PLACEHOLDERS),
        "checks": checks,
        "summary": {
            "probe": str(probe),
            "surface_dump_script": str(surface_dump_script),
            "late_entry_breakpoint": "0044895A",
            "early_descriptor_breakpoint_avoided": not probe_check.get("has_early_descriptor_breakpoint"),
            "slot_conditions_parameterized": all(
                bool(record.get("present")) for record in (probe_check.get("slot_conditions") or {}).values()
            ),
            "extra_probe_placeholders_replaced": runner_check.get("passed"),
            "late_load_slot_forcing_only_supported": all(
                bool(present) for present in (runner_check.get("late_load_slot_forcing_only_support") or {}).values()
            ),
        },
        "failures": failures,
    }


def write_markdown(path: Path, guard: dict[str, Any]) -> None:
    probe = guard["checks"]["transition_extra_probe"]
    runner = guard["checks"]["surface_dump_runner"]
    summary = guard["summary"]
    lines = [
        "# Load Slot Transition Probe Guard",
        "",
        f"- Overall: {status_text(bool(guard.get('passed')))}",
        f"- Generated: `{guard['generated_at']}`",
        f"- Runtime policy: {guard['runtime_policy']}",
        f"- Guard policy: {guard['guard_policy']}",
        f"- Probe: `{summary.get('probe')}`",
        f"- Surface-dump script: `{summary.get('surface_dump_script')}`",
        f"- Late-entry breakpoint: `{summary.get('late_entry_breakpoint')}`",
        f"- Early descriptor breakpoint avoided: `{summary.get('early_descriptor_breakpoint_avoided')}`",
        f"- Slot conditions parameterized: `{summary.get('slot_conditions_parameterized')}`",
        f"- Extra probe placeholders replaced: `{summary.get('extra_probe_placeholders_replaced')}`",
        f"- Late load-slot forcing only supported: `{summary.get('late_load_slot_forcing_only_supported')}`",
        "",
        "## Probe Breakpoints",
        "",
    ]
    for address, record in (probe.get("breakpoints") or {}).items():
        lines.append(f"- `{address}`: `{status_text(bool(record.get('present')))}` - {record.get('purpose')}")

    lines.extend(["", "## Probe Markers", ""])
    for marker, record in (probe.get("markers") or {}).items():
        lines.append(f"- `{marker}`: `{status_text(bool(record.get('present')))}` - {record.get('purpose')}")

    lines.extend(["", "## Slot Conditions", ""])
    for address, record in (probe.get("slot_conditions") or {}).items():
        lines.append(f"- `{address}`: `{status_text(bool(record.get('present')))}` - {record.get('purpose')}")

    lines.extend(["", "## Runner Placeholder Replacement", ""])
    for marker, present in (runner.get("extra_placeholder_replacements") or {}).items():
        lines.append(f"- `{marker}`: `{status_text(bool(present))}`")

    lines.extend(["", "## Late Load-Slot Forcing Support", ""])
    for marker, present in (runner.get("late_load_slot_forcing_only_support") or {}).items():
        lines.append(f"- `{marker}`: `{status_text(bool(present))}`")

    if guard.get("failures"):
        lines.extend(["", "## Failures", ""])
        lines.extend(f"- {failure}" for failure in guard["failures"])
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def print_guard(guard: dict[str, Any]) -> None:
    print(f"overall: {status_text(bool(guard.get('passed')))}")
    print(f"runtime-policy: {guard['runtime_policy']}")
    print(f"guard-policy: {guard['guard_policy']}")
    for name, check in guard["checks"].items():
        print(f"{name}: {status_text(bool(check.get('passed')))}")
    if guard.get("failures"):
        print("failures:")
        for failure in guard["failures"]:
            print(f"  - {failure}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--probe", type=Path, default=DEFAULT_PROBE)
    parser.add_argument("--surface-dump-script", type=Path, default=DEFAULT_SURFACE_DUMP_SCRIPT)
    parser.add_argument("--write-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--write-markdown", type=Path, default=DEFAULT_MD)
    parser.add_argument("--require-pass", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    guard = build_guard(args.probe, args.surface_dump_script)
    print_guard(guard)
    if args.write_json:
        args.write_json.parent.mkdir(parents=True, exist_ok=True)
        args.write_json.write_text(json.dumps(guard, indent=2) + "\n", encoding="utf-8")
    if args.write_markdown:
        write_markdown(args.write_markdown, guard)
    if args.require_pass and not guard["passed"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
