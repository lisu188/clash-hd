#!/usr/bin/env python3
"""Verify the Clash95 HD launcher keeps its user-initiated launch policy.

This is a repo-only source guard. It reads the launcher sources under
`src/launcher/`, the `scripts/launcher/` PowerShell entry, the evidence
refresh source, and `docs/hd/LAUNCHER.md`; it does not launch Clash95, CDB,
wrappers, PowerShell, or any visible GUI process.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_LAUNCHER_DIR = Path("src/launcher")
DEFAULT_SCRIPTS_DIR = Path("scripts/launcher")
DEFAULT_REFRESH_SCRIPT = Path("tools/current_evidence_refresh.py")
DEFAULT_DOC = Path("docs/hd/LAUNCHER.md")
DEFAULT_JSON = Path("captures/current/launcher-policy-guard-current.json")
DEFAULT_MD = Path("captures/current/launcher-policy-guard-current.md")
RUNTIME_POLICY = (
    "repo-only source inspection; does not launch Clash95, CDB, wrappers, "
    "PowerShell, or visible windows"
)
GUARD_POLICY = (
    "launcher visible launches must stay user-initiated (confirmed=True from "
    "the GUI Play button or the CLI double flag) and the launcher must never "
    "join the evidence refresh"
)

CONFIRMED_SIGNATURE = "*,\n    confirmed: bool,"
CONFIRMED_SIGNATURE_FLAT = "*, confirmed: bool"
REQUIRES_CONFIRMED = "requires confirmed=True"
WRITE_REFUSAL_OUTSIDE = "Refusing write outside candidates root"
WRITE_REFUSAL_GAME_DIR = "Refusing write inside the game directory"
NEVER_IN_REFRESH = "never part of the evidence refresh"
LAUNCH_CALL_ALLOWED_FILES = ("core.py", "gui.py", "run.py")
REFRESH_FORBIDDEN_TOKENS = ("launcher/gui", "launcher.gui", "run_launcher")
DOC_REQUIRED_PHRASES = (
    "user-initiated",
    "never part of the evidence refresh",
    "never ships or downloads DLLs",
)

PS_RISKY_RE = re.compile(
    r"Start-Process\b|::(?:SetForegroundWindow|BringWindowToTop|ShowWindow|"
    r"SetWindowPos|SetCursorPos|SendInput|PostMessage|keybd_event)\b|"
    r"\.CopyFromScreen\b|&\s*powershell\.exe\b",
    re.IGNORECASE,
)


def status_text(passed: bool) -> str:
    return "PASS" if passed else "FAIL"


def check_record(name: str, passed: bool, summary: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "name": name,
        "passed": passed,
        "summary": summary or {},
        "failures": [] if passed else [name],
    }


def read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return None


def build_guard(args: argparse.Namespace) -> dict[str, Any]:
    launcher_dir = Path(args.launcher_dir)
    scripts_dir = Path(args.scripts_dir)
    refresh_script = Path(args.refresh_script)
    doc = Path(args.doc)

    checks: dict[str, Any] = {}
    failures: list[str] = []
    check_specs: dict[str, tuple[bool, dict[str, Any], str]] = {}

    core_path = launcher_dir / "core.py"
    core_text = read_text(core_path)
    if core_text is None:
        check_specs["core_source_present"] = (
            False,
            {"path": str(core_path)},
            f"launcher core source is missing: {core_path}",
        )
        core_text = ""
    else:
        check_specs["core_source_present"] = (True, {"path": str(core_path)}, "")

    has_signature = (
        CONFIRMED_SIGNATURE in core_text or CONFIRMED_SIGNATURE_FLAT in core_text
    )
    check_specs["core_confirmed_gate"] = (
        has_signature and REQUIRES_CONFIRMED in core_text,
        {"keyword_only_signature": has_signature},
        "core.launch_game must take keyword-only confirmed and refuse without confirmed=True",
    )
    check_specs["core_write_refusal"] = (
        WRITE_REFUSAL_OUTSIDE in core_text and WRITE_REFUSAL_GAME_DIR in core_text,
        {},
        "core must refuse writes outside the candidates root and inside the game directory",
    )
    check_specs["core_refresh_isolation_policy"] = (
        NEVER_IN_REFRESH in core_text,
        {},
        "core must state the launcher is never part of the evidence refresh",
    )

    call_site_files: list[str] = []
    if launcher_dir.is_dir():
        for path in sorted(launcher_dir.glob("*.py")):
            text = read_text(path) or ""
            if "launch_game(" in text or "confirmed=True" in text:
                call_site_files.append(path.name)
    unexpected_call_sites = [
        name for name in call_site_files if name not in LAUNCH_CALL_ALLOWED_FILES
    ]
    check_specs["launch_call_sites"] = (
        not unexpected_call_sites and bool(call_site_files),
        {"call_site_files": call_site_files, "unexpected": unexpected_call_sites},
        "launch_game/confirmed=True may appear only in core.py, gui.py, and run.py",
    )

    refresh_text = read_text(refresh_script)
    if refresh_text is None:
        check_specs["refresh_isolation"] = (
            False,
            {"path": str(refresh_script)},
            f"evidence refresh source is missing: {refresh_script}",
        )
    else:
        found = [token for token in REFRESH_FORBIDDEN_TOKENS if token in refresh_text]
        check_specs["refresh_isolation"] = (
            not found,
            {"forbidden_tokens_found": found},
            "evidence refresh must not reference the launcher GUI or entry script",
        )

    ps_hits: dict[str, list[str]] = {}
    ps_files: list[str] = []
    if scripts_dir.is_dir():
        for path in sorted(scripts_dir.glob("*.ps1")):
            ps_files.append(path.name)
            text = read_text(path) or ""
            hits = [
                line.strip()
                for line in text.splitlines()
                if PS_RISKY_RE.search(line)
            ]
            if hits:
                ps_hits[path.name] = hits
    check_specs["launcher_scripts_no_risky_calls"] = (
        bool(ps_files) and not ps_hits,
        {"scripts": ps_files, "risky_lines": ps_hits},
        "scripts/launcher must exist and contain no process/window/input API calls",
    )

    doc_text = read_text(doc)
    if doc_text is None:
        check_specs["doc_policy"] = (
            False,
            {"path": str(doc)},
            f"launcher policy doc is missing: {doc}",
        )
    else:
        missing = [phrase for phrase in DOC_REQUIRED_PHRASES if phrase not in doc_text]
        check_specs["doc_policy"] = (
            not missing,
            {"missing_phrases": missing},
            "docs/hd/LAUNCHER.md must state the user-initiated and refresh-isolation policy",
        )

    for name, (passed, summary, failure) in check_specs.items():
        checks[name] = check_record(name, bool(passed), summary)
        if not passed:
            checks[name]["failures"] = [failure]
            failures.append(f"{name}: {failure}")

    return {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "passed": not failures,
        "runtime_policy": RUNTIME_POLICY,
        "guard_policy": GUARD_POLICY,
        "launcher_dir": str(launcher_dir),
        "scripts_dir": str(scripts_dir),
        "refresh_script": str(refresh_script),
        "doc": str(doc),
        "checks": checks,
        "failures": failures,
    }


def print_guard(guard: dict[str, Any]) -> None:
    print(f"overall: {status_text(guard['passed'])}")
    print(f"runtime-policy: {guard['runtime_policy']}")
    print(f"guard-policy: {guard['guard_policy']}")
    for name, check in guard["checks"].items():
        print(f"{name}: {status_text(bool(check.get('passed')))}")
    if guard["failures"]:
        print("failures:")
        for failure in guard["failures"]:
            print(f"  - {failure}")


def write_markdown(path: Path, guard: dict[str, Any]) -> None:
    lines = [
        "# Launcher Policy Guard",
        "",
        f"- Overall: {status_text(guard['passed'])}",
        f"- Generated: `{guard['generated_at']}`",
        f"- Runtime policy: {guard['runtime_policy']}",
        f"- Guard policy: {guard['guard_policy']}",
        f"- Launcher dir: `{guard['launcher_dir']}`",
        f"- Scripts dir: `{guard['scripts_dir']}`",
        f"- Doc: `{guard['doc']}`",
        "",
        "## Checks",
        "",
    ]
    for name, check in guard["checks"].items():
        lines.append(f"- `{name}`: `{status_text(bool(check.get('passed')))}`")
        for failure in check.get("failures", []):
            lines.append(f"  - {failure}")
    if guard["failures"]:
        lines.extend(["", "## Failures", ""])
        lines.extend(f"- {failure}" for failure in guard["failures"])
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--launcher-dir", type=Path, default=DEFAULT_LAUNCHER_DIR)
    parser.add_argument("--scripts-dir", type=Path, default=DEFAULT_SCRIPTS_DIR)
    parser.add_argument("--refresh-script", type=Path, default=DEFAULT_REFRESH_SCRIPT)
    parser.add_argument("--doc", type=Path, default=DEFAULT_DOC)
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
