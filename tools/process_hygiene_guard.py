#!/usr/bin/env python3
"""Verify no Clash95/CDB runtime processes are left running.

This guard launches no game, debugger, wrapper, visible GUI process, or shell
helper. It uses the Windows Toolhelp snapshot API to inspect currently running
process names.
"""

from __future__ import annotations

import argparse
import ctypes
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_JSON = Path("captures/current/process-hygiene-guard-current.json")
DEFAULT_MD = Path("captures/current/process-hygiene-guard-current.md")
DEFAULT_EXACT_NAMES = ("cdb.exe",)
DEFAULT_PREFIXES = ("clash95",)
RUNTIME_POLICY = "local process inspection only; does not launch Clash95, CDB, wrappers, or visible windows"
TH32CS_SNAPPROCESS = 0x00000002
MAX_PATH = 260
INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value


class PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", ctypes.c_ulong),
        ("cntUsage", ctypes.c_ulong),
        ("th32ProcessID", ctypes.c_ulong),
        ("th32DefaultHeapID", ctypes.c_size_t),
        ("th32ModuleID", ctypes.c_ulong),
        ("cntThreads", ctypes.c_ulong),
        ("th32ParentProcessID", ctypes.c_ulong),
        ("pcPriClassBase", ctypes.c_long),
        ("dwFlags", ctypes.c_ulong),
        ("szExeFile", ctypes.c_wchar * MAX_PATH),
    ]


def status_text(passed: bool) -> str:
    return "PASS" if passed else "FAIL"


def process_snapshot_rows() -> tuple[list[dict[str, str]], int, str]:
    if os.name != "nt":
        return [], 1, "process hygiene guard requires Windows"

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateToolhelp32Snapshot.argtypes = [ctypes.c_ulong, ctypes.c_ulong]
    kernel32.CreateToolhelp32Snapshot.restype = ctypes.c_void_p
    kernel32.Process32FirstW.argtypes = [ctypes.c_void_p, ctypes.POINTER(PROCESSENTRY32W)]
    kernel32.Process32FirstW.restype = ctypes.c_int
    kernel32.Process32NextW.argtypes = [ctypes.c_void_p, ctypes.POINTER(PROCESSENTRY32W)]
    kernel32.Process32NextW.restype = ctypes.c_int
    kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
    kernel32.CloseHandle.restype = ctypes.c_int
    kernel32.ProcessIdToSessionId.argtypes = [ctypes.c_ulong, ctypes.POINTER(ctypes.c_ulong)]
    kernel32.ProcessIdToSessionId.restype = ctypes.c_int

    snapshot = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if snapshot == INVALID_HANDLE_VALUE:
        error = ctypes.get_last_error()
        return [], error, f"CreateToolhelp32Snapshot failed with Windows error {error}"

    rows: list[dict[str, str]] = []
    try:
        entry = PROCESSENTRY32W()
        entry.dwSize = ctypes.sizeof(PROCESSENTRY32W)
        ok = kernel32.Process32FirstW(snapshot, ctypes.byref(entry))
        if not ok:
            error = ctypes.get_last_error()
            return [], error, f"Process32FirstW failed with Windows error {error}"

        while ok:
            session_id = ctypes.c_ulong()
            session = ""
            if kernel32.ProcessIdToSessionId(entry.th32ProcessID, ctypes.byref(session_id)):
                session = str(session_id.value)
            rows.append(
                {
                    "image_name": entry.szExeFile,
                    "pid": str(entry.th32ProcessID),
                    "parent_pid": str(entry.th32ParentProcessID),
                    "thread_count": str(entry.cntThreads),
                    "session_number": session,
                }
            )
            ok = kernel32.Process32NextW(snapshot, ctypes.byref(entry))
    finally:
        kernel32.CloseHandle(snapshot)

    return rows, 0, ""


def is_target_process(
    image_name: str,
    exact_names: tuple[str, ...],
    prefixes: tuple[str, ...],
) -> bool:
    lower_name = image_name.lower()
    if lower_name in exact_names:
        return True
    return any(lower_name.startswith(prefix) for prefix in prefixes)


def build_guard(args: argparse.Namespace) -> dict[str, Any]:
    exact_names = tuple(name.lower() for name in args.exact_name)
    prefixes = tuple(prefix.lower() for prefix in args.prefix)
    rows, returncode, stderr = process_snapshot_rows()
    matching = [
        row
        for row in rows
        if is_target_process(row["image_name"], exact_names, prefixes)
    ]

    failures: list[str] = []
    if returncode:
        failures.append(stderr)
    if matching:
        names = ", ".join(f"{row['image_name']} pid={row['pid']}" for row in matching)
        failures.append(f"runtime processes still running: {names}")

    return {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "passed": not failures,
        "runtime_policy": RUNTIME_POLICY,
        "guard_policy": "no cdb.exe or clash95*.exe process may be running after evidence refresh",
        "inspection_source": "CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS)",
        "inspection_returncode": returncode,
        "inspection_error": stderr,
        "target_exact_names": list(exact_names),
        "target_prefixes": list(prefixes),
        "matching_processes": matching,
        "matching_process_count": len(matching),
        "failures": failures,
    }


def print_guard(guard: dict[str, Any]) -> None:
    print(f"overall: {status_text(guard['passed'])}")
    print(f"runtime-policy: {guard['runtime_policy']}")
    print(f"guard-policy: {guard['guard_policy']}")
    print(f"matching-process-count: {guard['matching_process_count']}")
    if guard["failures"]:
        print("failures:")
        for failure in guard["failures"]:
            print(f"  - {failure}")


def write_markdown(path: Path, guard: dict[str, Any]) -> None:
    lines = [
        "# Process Hygiene Guard",
        "",
        f"- Overall: {status_text(guard['passed'])}",
        f"- Generated: `{guard['generated_at']}`",
        f"- Runtime policy: {guard['runtime_policy']}",
        f"- Guard policy: {guard['guard_policy']}",
        f"- Inspection source: `{guard['inspection_source']}`",
        f"- Matching runtime processes: `{guard['matching_process_count']}`",
        "",
        "## Matching Processes",
        "",
    ]
    if guard["matching_processes"]:
        for process in guard["matching_processes"]:
            lines.append(
                "- `{image_name}` pid=`{pid}` parent=`{parent_pid}` session=`{session_number}`".format(
                    **process
                )
            )
    else:
        lines.append("- None")
    if guard["failures"]:
        lines.extend(["", "## Failures", ""])
        lines.extend(f"- {failure}" for failure in guard["failures"])
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exact-name", action="append", default=list(DEFAULT_EXACT_NAMES))
    parser.add_argument("--prefix", action="append", default=list(DEFAULT_PREFIXES))
    parser.add_argument("--write-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--write-markdown", type=Path, default=DEFAULT_MD)
    parser.add_argument("--require-pass", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    guard = build_guard(args)
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
