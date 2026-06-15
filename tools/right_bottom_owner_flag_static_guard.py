#!/usr/bin/env python3
"""Verify static owner-flag gates behind the right-bottom action route.

This helper reads the original local Clash95 executable bytes and checks the
small instruction windows that explain the natural right-bottom blocker. It
does not launch Clash95, CDB, wrappers, PowerShell, or any visible window.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_EXE = Path(r"C:\Clash\clash95.exe")
DEFAULT_JSON = Path("captures/current/right-bottom-owner-flag-static-guard-current.json")
DEFAULT_MD = Path("captures/current/right-bottom-owner-flag-static-guard-current.md")
EXPECTED_SHA256 = "500055D77D03D514E8D3168506BD10F67CD8569BCC450604FF8192F46CDAF3AE"
RUNTIME_POLICY = (
    "local original-executable byte inspection only; does not launch Clash95, "
    "CDB, wrappers, PowerShell, or visible windows"
)
GUARD_POLICY = (
    "the natural right-bottom action route must retain the command-99 owner-loop "
    "callback, owner-global writes, 004338E0 owner flag bit-2 early-return gate, "
    "and 00433C20 owner-loop bit gates before the current owner-flag blocker can "
    "be treated as understood evidence"
)


@dataclass(frozen=True)
class Pattern:
    name: str
    va: int
    offset: int
    expected_hex: str
    rationale: str

    @property
    def expected(self) -> bytes:
        return bytes.fromhex(self.expected_hex)


PATTERNS = (
    Pattern(
        "command_99_callback_pointer",
        0x00422709,
        0x021B09,
        "B9203C430083FE630F846FFEFFFF",
        "castle overview command 0x63 selects callback 00433C20",
    ),
    Pattern(
        "owner_global_532150_write",
        0x00433C26,
        0x033026,
        "A350215300",
        "00433C20 stores the owner pointer in dword_532150",
    ),
    Pattern(
        "owner_global_53214c_write",
        0x00433C4B,
        0x03304B,
        "A34C215300",
        "00433C20 stores the selected owner index/state in dword_53214C",
    ),
    Pattern(
        "owner_global_532154_write",
        0x00433D5A,
        0x03315A,
        "A354215300",
        "00433C20 stores the owner UI surface pointer in dword_532154",
    ),
    Pattern(
        "action_4338e0_bit2_early_return",
        0x004338E6,
        0x032CE6,
        "A150215300F680A00100000275025AC3",
        "004338E0 immediately returns unless owner flag bit 0x02 is set",
    ),
    Pattern(
        "action_433914_stock_owner_call",
        0x00433914,
        0x032D14,
        "E8A7220000",
        "the validation wrapper targets only the post-gate owner/action draw call",
    ),
    Pattern(
        "owner_loop_bit2_gate",
        0x00433CE3,
        0x0330E3,
        "A150215300F680A0010000020F84B2020000",
        "00433C20 checks owner flag bit 0x02 before the action descriptor lane",
    ),
    Pattern(
        "owner_loop_bit1_gate",
        0x00433CFF,
        0x0330FF,
        "A150215300F680A0010000010F84A0020000",
        "00433C20 checks owner flag bit 0x01 before an adjacent owner descriptor lane",
    ),
    Pattern(
        "owner_loop_bit8_gate",
        0x00433D1B,
        0x03311B,
        "A150215300F680A0010000080F848E020000",
        "00433C20 checks owner flag bit 0x08 before an adjacent owner descriptor lane",
    ),
)


def status_text(passed: bool) -> str:
    return "PASS" if passed else "FAIL"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def read_bytes(path: Path) -> tuple[bytes | None, list[str]]:
    if not path.exists():
        return None, [f"missing original executable: {path}"]
    try:
        return path.read_bytes(), []
    except OSError as exc:
        return None, [f"could not read {path}: {exc}"]


def check_pattern(data: bytes, pattern: Pattern) -> dict[str, Any]:
    end = pattern.offset + len(pattern.expected)
    actual = data[pattern.offset:end] if pattern.offset < len(data) else b""
    passed = actual == pattern.expected
    return {
        "name": pattern.name,
        "passed": passed,
        "va": f"0x{pattern.va:08X}",
        "file_offset": f"0x{pattern.offset:06X}",
        "expected_hex": pattern.expected.hex().upper(),
        "actual_hex": actual.hex().upper(),
        "rationale": pattern.rationale,
        "failure": None if passed else f"{pattern.name} bytes drifted at 0x{pattern.offset:06X}",
    }


def build_guard(exe: Path = DEFAULT_EXE) -> dict[str, Any]:
    failures: list[str] = []
    data, read_failures = read_bytes(exe)
    failures.extend(read_failures)
    pattern_checks: list[dict[str, Any]] = []
    digest = None
    if data is not None:
        digest = sha256(data)
        if digest != EXPECTED_SHA256:
            failures.append(f"original executable SHA-256 was {digest}, expected {EXPECTED_SHA256}")
        pattern_checks = [check_pattern(data, pattern) for pattern in PATTERNS]
        failures.extend(
            str(check["failure"])
            for check in pattern_checks
            if check.get("failure")
        )

    return {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "passed": not failures,
        "runtime_policy": RUNTIME_POLICY,
        "guard_policy": GUARD_POLICY,
        "exe": str(exe),
        "expected_sha256": EXPECTED_SHA256,
        "actual_sha256": digest,
        "patterns": pattern_checks,
        "summary": {
            "pattern_count": len(pattern_checks),
            "passed_pattern_count": sum(1 for check in pattern_checks if check.get("passed")),
            "command_99_callback_verified": any(
                check.get("name") == "command_99_callback_pointer" and check.get("passed")
                for check in pattern_checks
            ),
            "owner_globals_verified": all(
                any(check.get("name") == name and check.get("passed") for check in pattern_checks)
                for name in (
                    "owner_global_532150_write",
                    "owner_global_53214c_write",
                    "owner_global_532154_write",
                )
            ),
            "action_bit2_gate_verified": any(
                check.get("name") == "action_4338e0_bit2_early_return" and check.get("passed")
                for check in pattern_checks
            ),
            "owner_loop_bit_gates_verified": all(
                any(check.get("name") == name and check.get("passed") for check in pattern_checks)
                for name in ("owner_loop_bit2_gate", "owner_loop_bit1_gate", "owner_loop_bit8_gate")
            ),
        },
        "failures": failures,
    }


def write_markdown(path: Path, guard: dict[str, Any]) -> None:
    summary = guard.get("summary", {})
    lines = [
        "# Right-Bottom Owner-Flag Static Guard",
        "",
        f"- Overall: {status_text(bool(guard.get('passed')))}",
        f"- Generated: `{guard['generated_at']}`",
        f"- Runtime policy: {guard['runtime_policy']}",
        f"- Guard policy: {guard['guard_policy']}",
        f"- Executable: `{guard['exe']}`",
        f"- Expected SHA-256: `{guard['expected_sha256']}`",
        f"- Actual SHA-256: `{guard.get('actual_sha256')}`",
        f"- Patterns: `{summary.get('passed_pattern_count')}/{summary.get('pattern_count')}`",
        f"- Command 99 callback verified: `{summary.get('command_99_callback_verified')}`",
        f"- Owner globals verified: `{summary.get('owner_globals_verified')}`",
        f"- 004338E0 bit-2 gate verified: `{summary.get('action_bit2_gate_verified')}`",
        f"- Owner-loop bit gates verified: `{summary.get('owner_loop_bit_gates_verified')}`",
        "",
        "## Patterns",
        "",
    ]
    for check in guard.get("patterns", []):
        lines.append(
            "- `{name}`: `{status}` VA `{va}` file `{offset}` - {rationale}".format(
                name=check["name"],
                status=status_text(bool(check.get("passed"))),
                va=check["va"],
                offset=check["file_offset"],
                rationale=check["rationale"],
            )
        )
    if guard.get("failures"):
        lines.extend(["", "## Failures", ""])
        lines.extend(f"- {failure}" for failure in guard["failures"])
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exe", type=Path, default=DEFAULT_EXE)
    parser.add_argument("--write-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--write-markdown", type=Path, default=DEFAULT_MD)
    parser.add_argument("--require-pass", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    guard = build_guard(args.exe)
    print(f"overall: {status_text(bool(guard['passed']))}")
    print(f"runtime-policy: {guard['runtime_policy']}")
    print(f"sha256: {guard.get('actual_sha256')}")
    print(
        "patterns: {}/{}".format(
            guard["summary"].get("passed_pattern_count"),
            guard["summary"].get("pattern_count"),
        )
    )
    if guard["failures"]:
        print("failures:")
        for failure in guard["failures"]:
            print(f"  - {failure}")
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
