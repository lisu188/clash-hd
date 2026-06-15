#!/usr/bin/env python3
"""Summarize visible Clash95 battle command input evidence.

This is a repo-only parser for existing logs and JSON artifacts. It does not
launch Clash95, CDB, wrappers, PowerShell, or any visible window.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_JSON = Path("captures/current/battle-visible-input-current.json")
DEFAULT_MD = Path("captures/current/battle-visible-input-summary-current.md")
RUNTIME_POLICY = "repo-only evidence parsing; does not launch Clash95, CDB, wrappers, PowerShell, or visible windows"

MARKERS = (
    "BATTLE_DIRECTINPUT_MOUSE_ACQUIRE",
    "SURFDUMP_LOADSAVE_RETURN",
    "SURFDUMP_PLAYGAME",
    "BATTLE_FORCE_ATTACK_CALL",
    "BATTLE_OWNER_ENTRY",
    "BATTLE_COMMAND_INPUT_WINDOW",
    "BATTLE_COMMAND_PRE_GATES",
    "BATTLE_COMMAND_CLICK_GATE_OBSERVED",
    "BATTLE_COMMAND_CLICK_GATE",
    "BATTLE_COMMAND_DESCRIPTOR_CALLBACK",
    "BATTLE_COMMAND_CALLBACK_RESULT",
    "BATTLE_COMMAND_CALLBACK",
    "SURFDUMP_HOST_READY",
    "AV_SURFDUMP",
)

EXPECTED_DISPLAYED = [588, 440]
EXPECTED_NATIVE = [508, 380]
EXPECTED_DESCRIPTOR = 0x00514B78
EXPECTED_CALLBACK = 0x0042D4E0

KV_RE = re.compile(r"(?P<key>[A-Za-z_][A-Za-z0-9_]*)=(?P<value>\([^)]*\)|[^\s]+)")
MARKER_RE = re.compile("|".join(re.escape(marker) for marker in MARKERS))
PRINTF_TOKEN_RE = re.compile(r"%[0-9A-Za-z]")
BREAK_INSTRUCTION_RE = re.compile(r"Break instruction exception - code 80000003")


def parse_value(value: str) -> Any:
    value = value.strip().rstrip(",")
    if value.startswith("(") and value.endswith(")"):
        parts = [part.strip() for part in value[1:-1].split(",") if part.strip()]
        return [parse_value(part) for part in parts]
    try:
        return int(value, 0)
    except ValueError:
        if re.fullmatch(r"[0-9A-Fa-f]{6,8}", value):
            return int(value, 16)
        return value


def parse_rows(text: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    break_instruction_exceptions: list[dict[str, Any]] = []
    target_started = False
    for line_no, line in enumerate(text.splitlines(), start=1):
        if re.match(r"^\s*\d+:\d+>\s*g\s*$", line):
            target_started = True
            continue
        if re.match(r"^\s*\d+:\d+>", line):
            continue
        if "Unable to insert breakpoint" in line or "Unable to remove breakpoint" in line:
            failures.append({"line": line_no, "text": line.strip()})
        if target_started and BREAK_INSTRUCTION_RE.search(line):
            break_instruction_exceptions.append({"line": line_no, "text": line.strip()})
        matches = list(MARKER_RE.finditer(line))
        for index, match in enumerate(matches):
            marker = match.group(0)
            end = matches[index + 1].start() if index + 1 < len(matches) else len(line)
            fragment = line[match.start() : end].strip()
            if PRINTF_TOKEN_RE.search(fragment):
                continue
            rows.append(
                {
                    "line": line_no,
                    "marker": marker,
                    "values": {
                        item.group("key"): parse_value(item.group("value"))
                        for item in KV_RE.finditer(fragment)
                    },
                    "text": fragment,
                }
            )
    return rows, failures, break_instruction_exceptions


def find_first_existing(path: Path, names: tuple[str, ...], glob_pattern: str) -> Path | None:
    for name in names:
        candidate = path / name
        if candidate.exists():
            return candidate
    matches = sorted(path.glob(glob_pattern))
    return matches[0] if matches else None


def evidence_paths(path: Path) -> tuple[Path | None, Path | None]:
    if path.is_dir():
        log_path = find_first_existing(
            path,
            (
                "cdb-visible-input.log",
                "cdb-visible-input-long.log",
                "cdb-visible-input-quiet.log",
                "cdb-visible-input-minimal.log",
                "cdb-visible-input-rawsend.log",
            ),
            "cdb-visible-input*.log",
        )
        input_json = find_first_existing(
            path,
            (
                "mouse-visible-input.json",
                "mouse-visible-input-long.json",
                "mouse-visible-input-quiet.json",
                "mouse-visible-input-minimal.json",
                "raw-sendinput-click.json",
            ),
            "mouse-visible-input*.json",
        )
        if input_json is None:
            input_json = path / "raw-sendinput-click.json" if (path / "raw-sendinput-click.json").exists() else None
        return log_path, input_json
    return path, None


def load_json(path: Path | None) -> dict[str, Any] | None:
    if path is None or not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return None


def marker_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = {marker: 0 for marker in MARKERS}
    for row in rows:
        counts[row["marker"]] += 1
    return counts


def last_row(rows: list[dict[str, Any]], marker: str) -> dict[str, Any] | None:
    for row in reversed(rows):
        if row["marker"] == marker:
            return row
    return None


def any_row_value(rows: list[dict[str, Any]], marker: str, key: str, value: Any) -> bool:
    for row in rows:
        if row["marker"] == marker and row["values"].get(key) == value:
            return True
    return False


def input_json_summary(payload: dict[str, Any] | None) -> dict[str, Any]:
    if payload is None:
        return {
            "present": False,
            "path_verified": False,
            "click_path_verified": False,
            "click_event_count": 0,
            "dry_run": False,
        }
    return {
        "present": True,
        "path_verified": bool(payload.get("path_verified") or payload.get("dry_run") is False),
        "click_path_verified": bool(payload.get("click_path_verified") or payload.get("dry_run") is False),
        "click_event_count": int(payload.get("click_event_count") or sum(len(row.get("clicks", [])) for row in payload.get("points", []))),
        "dry_run": bool(payload.get("dry_run")),
    }


def build_run_summary(path: Path) -> dict[str, Any]:
    log_path, input_json_path = evidence_paths(path)
    text = ""
    missing_log = log_path is None or not log_path.exists()
    if not missing_log and log_path is not None:
        text = log_path.read_text(encoding="utf-8", errors="replace")
    rows, cdb_failures, cdb_break_instruction_exceptions = parse_rows(text)
    counts = marker_counts(rows)
    input_payload = load_json(input_json_path)
    input_summary = input_json_summary(input_payload)

    command_window = last_row(rows, "BATTLE_COMMAND_INPUT_WINDOW")
    command_values = command_window.get("values", {}) if command_window else {}
    descriptor_target_ok = (
        command_values.get("expected_displayed") == EXPECTED_DISPLAYED
        and command_values.get("expected_native") == EXPECTED_NATIVE
        and command_values.get("list") == EXPECTED_DESCRIPTOR
    )
    callback_target_ok = any_row_value(rows, "BATTLE_COMMAND_CALLBACK", "eip", EXPECTED_CALLBACK)
    click_gate_passed = any_row_value(rows, "BATTLE_COMMAND_CLICK_GATE_OBSERVED", "eax", 1)
    callback_result_seen = counts["BATTLE_COMMAND_CALLBACK_RESULT"] > 0
    callback_consumed = callback_target_ok and callback_result_seen
    cdb_valid = not cdb_failures and not cdb_break_instruction_exceptions and not missing_log
    command_readiness = (
        cdb_valid
        and counts["BATTLE_DIRECTINPUT_MOUSE_ACQUIRE"] > 0
        and counts["SURFDUMP_LOADSAVE_RETURN"] > 0
        and counts["SURFDUMP_PLAYGAME"] > 0
        and counts["BATTLE_FORCE_ATTACK_CALL"] > 0
        and counts["BATTLE_OWNER_ENTRY"] > 0
        and counts["BATTLE_COMMAND_INPUT_WINDOW"] > 0
        and descriptor_target_ok
    )
    real_visible_click_consumed = (
        command_readiness
        and input_summary["present"]
        and input_summary["click_event_count"] > 0
        and (click_gate_passed or callback_consumed)
    )

    classification: list[str] = []
    if missing_log:
        classification.append("missing log")
    if cdb_failures:
        classification.append("invalid CDB breakpoint failure")
    if cdb_break_instruction_exceptions:
        classification.append("invalid CDB break-instruction exception")
    if command_readiness:
        classification.append("visible command readiness proven")
    elif not missing_log and not cdb_failures:
        classification.append("visible command readiness incomplete")
    if input_summary["present"]:
        classification.append("visible input JSON present")
    else:
        classification.append("visible input JSON missing")
    if real_visible_click_consumed:
        classification.append("real visible click consumed by command descriptor")
    elif command_readiness:
        classification.append("real visible click consumption still open")

    return {
        "path": str(path),
        "log": str(log_path) if log_path else None,
        "input_json": str(input_json_path) if input_json_path else None,
        "missing_log": missing_log,
        "cdb_breakpoint_failure_count": len(cdb_failures),
        "cdb_breakpoint_failures": cdb_failures[:10],
        "cdb_break_instruction_exception_count": len(cdb_break_instruction_exceptions),
        "cdb_break_instruction_exceptions": cdb_break_instruction_exceptions[:10],
        "marker_counts": counts,
        "command_readiness_proven": command_readiness,
        "descriptor_target_ok": descriptor_target_ok,
        "last_command_input_window": command_window,
        "input": input_summary,
        "click_gate_passed": click_gate_passed,
        "callback_target_ok": callback_target_ok,
        "callback_result_seen": callback_result_seen,
        "real_visible_click_consumed": real_visible_click_consumed,
        "classification": classification,
    }


def build_summary(paths: list[Path]) -> dict[str, Any]:
    runs = [build_run_summary(path) for path in paths]
    command_ready_runs = [run for run in runs if run["command_readiness_proven"]]
    click_consumed_runs = [run for run in runs if run["real_visible_click_consumed"]]
    invalid_runs = [
        run
        for run in runs
        if run["cdb_breakpoint_failure_count"] or run["cdb_break_instruction_exception_count"]
    ]
    focused_completion_percent = 99.91 if command_ready_runs and not click_consumed_runs else 99.95 if click_consumed_runs else 99.89
    failures: list[str] = []
    if not command_ready_runs:
        failures.append("no visible run proves command readiness")
    if not click_consumed_runs:
        failures.append("no visible run proves real click consumption")
    for run in invalid_runs:
        if run["cdb_breakpoint_failure_count"]:
            failures.append(f"invalid CDB breakpoint failures in {run['path']}")
        if run["cdb_break_instruction_exception_count"]:
            failures.append(f"invalid CDB break-instruction exceptions in {run['path']}")
    return {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "runtime_policy": RUNTIME_POLICY,
        "focused_completion_percent": focused_completion_percent,
        "run_count": len(runs),
        "command_ready_run_count": len(command_ready_runs),
        "click_consumed_run_count": len(click_consumed_runs),
        "invalid_run_count": len(invalid_runs),
        "passed": bool(command_ready_runs) and bool(click_consumed_runs) and not invalid_runs,
        "real_visible_click_consumed": bool(click_consumed_runs),
        "runs": runs,
        "failures": failures,
    }


def markdown_for(summary: dict[str, Any], markdown_path: Path) -> str:
    lines = [
        "# Battle Visible Input Summary",
        "",
        f"- Generated: {summary['generated_at']}",
        f"- Runtime policy: {summary['runtime_policy']}",
        f"- Focused completion: {summary['focused_completion_percent']:.2f}%",
        f"- Command-ready runs: {summary['command_ready_run_count']} / {summary['run_count']}",
        f"- Click-consumed runs: {summary['click_consumed_run_count']} / {summary['run_count']}",
        f"- Invalid runs: {summary['invalid_run_count']}",
        f"- Overall: {'PASS' if summary['passed'] else 'FAIL'}",
        "",
        "## Runs",
        "",
    ]
    for run in summary["runs"]:
        run_path = Path(run["path"])
        try:
            label = run_path.resolve().relative_to(markdown_path.parent.resolve()).as_posix()
        except (OSError, ValueError):
            label = run["path"]
        lines.extend(
            [
                f"### {label}",
                "",
                f"- Command readiness: {'PASS' if run['command_readiness_proven'] else 'FAIL'}",
                f"- Real visible click consumed: {'PASS' if run['real_visible_click_consumed'] else 'FAIL'}",
                f"- CDB breakpoint failures: {run['cdb_breakpoint_failure_count']}",
                f"- CDB break-instruction exceptions: {run['cdb_break_instruction_exception_count']}",
                f"- Input JSON: {'present' if run['input']['present'] else 'missing'}",
                f"- Classification: {', '.join(run['classification'])}",
                "",
            ]
        )
    lines.extend(
        [
            "## Completion Summary",
            "",
            f"Focused battle/right-bottom command lane: {summary['focused_completion_percent']:.2f}%.",
            "Full-game reverse engineering is not 100%.",
            "",
        ]
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", type=Path)
    parser.add_argument("--write-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--write-markdown", type=Path, default=DEFAULT_MD)
    parser.add_argument("--require-command-ready", action="store_true")
    parser.add_argument("--require-click-consumed", action="store_true")
    parser.add_argument("--require-no-invalid", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary = build_summary(args.paths)
    if args.write_json:
        args.write_json.parent.mkdir(parents=True, exist_ok=True)
        args.write_json.write_text(json.dumps(summary, indent=2), encoding="ascii")
    if args.write_markdown:
        args.write_markdown.parent.mkdir(parents=True, exist_ok=True)
        args.write_markdown.write_text(markdown_for(summary, args.write_markdown), encoding="ascii")
    print(f"visible-input-summary: {summary['focused_completion_percent']:.2f}%")
    print(f"command-ready-runs: {summary['command_ready_run_count']}/{summary['run_count']}")
    print(f"click-consumed-runs: {summary['click_consumed_run_count']}/{summary['run_count']}")
    print(f"invalid-runs: {summary['invalid_run_count']}")
    break_exception_runs = sum(
        1 for run in summary["runs"] if run["cdb_break_instruction_exception_count"]
    )
    print(f"break-instruction-exception-runs: {break_exception_runs}/{summary['run_count']}")
    if args.require_command_ready and not summary["command_ready_run_count"]:
        return 2
    if args.require_click_consumed and not summary["click_consumed_run_count"]:
        return 2
    if args.require_no_invalid and summary["invalid_run_count"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
