#!/usr/bin/env python3
"""Verify current runtime evidence uses no visible-desktop fallback.

This is a repo-only guard. It reads existing evidence JSON/summary files and
does not launch Clash95, CDB, wrappers, or any visible GUI process.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


RUN_RE = re.compile(r"captures[\\/]+(?:archive[\\/]+)?cdb-surface-dump-\d{8}-\d{6}", re.IGNORECASE)
DEFAULT_JSON = Path("captures/current/no-visible-runtime-guard-current.json")
DEFAULT_MD = Path("captures/current/no-visible-runtime-guard-current.md")
DEFAULT_REFRESH_JSON = Path("captures/current/current-evidence-refresh-current.json")


def canonical_run_dir(run: Path) -> Path:
    if run.exists():
        return run
    normalized = str(run).replace("\\", "/")
    prefix = "captures/"
    archive_prefix = "captures/archive/"
    if normalized.lower().startswith(prefix) and not normalized.lower().startswith(archive_prefix):
        suffix = normalized[len(prefix) :]
        if suffix.lower().startswith("cdb-surface-dump-"):
            archived = Path(archive_prefix + suffix)
            if archived.exists():
                return archived
    return run


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def status_text(passed: bool) -> str:
    return "PASS" if passed else "FAIL"


def repo_relative(path: Path) -> str:
    try:
        return str(path.relative_to(Path.cwd()))
    except ValueError:
        return str(path)


def collect_run_dirs(value: Any) -> set[Path]:
    runs: set[Path] = set()
    if isinstance(value, dict):
        for child in value.values():
            runs.update(collect_run_dirs(child))
    elif isinstance(value, list):
        for child in value:
            runs.update(collect_run_dirs(child))
    elif isinstance(value, str):
        # RUN_RE already accepts either separator; rebuild the matched run dir
        # with forward slashes so Path() splits it into components on POSIX
        # hosts instead of keeping a literal backslash filename.
        for match in RUN_RE.finditer(value):
            token = match.group(0).replace("\\", "/")
            runs.add(canonical_run_dir(Path(token)))
    return runs


def summarize_run(run: Path) -> dict[str, Any]:
    summary_path = run / "summary.json"
    if not summary_path.exists():
        return {
            "run": str(run),
            "summary_json": str(summary_path),
            "passed": False,
            "failures": [f"missing run summary: {summary_path}"],
        }
    try:
        summary = load_json(summary_path)
    except (OSError, json.JSONDecodeError) as exc:
        return {
            "run": str(run),
            "summary_json": str(summary_path),
            "passed": False,
            "failures": [f"could not read run summary {summary_path}: {type(exc).__name__}: {exc}"],
        }

    failures: list[str] = []
    if summary.get("HiddenDesktop") is not True:
        failures.append(f"{run} HiddenDesktop is {summary.get('HiddenDesktop')}")
    if summary.get("LaunchMode") != "hidden-desktop":
        failures.append(f"{run} LaunchMode is {summary.get('LaunchMode')}")
    if summary.get("AllowVisibleDesktop") is True:
        failures.append(f"{run} AllowVisibleDesktop is true")

    return {
        "run": str(run),
        "summary_json": str(summary_path),
        "passed": not failures,
        "launch_mode": summary.get("LaunchMode"),
        "hidden_desktop": summary.get("HiddenDesktop"),
        "desktop_name": summary.get("DesktopName"),
        "stage": summary.get("Stage"),
        "candidate_sha256": summary.get("CandidateSha256"),
        "extra_probe_template": summary.get("ExtraProbeTemplate"),
        "failures": failures,
    }


def build_guard_from_payloads(
    payloads: list[dict[str, Any]],
    runtime_policy: str | None = None,
) -> dict[str, Any]:
    failures: list[str] = []
    runtime_policy = runtime_policy or ""
    if "does not launch Clash95" not in runtime_policy or "visible windows" not in runtime_policy:
        failures.append(f"runtime policy does not explicitly forbid visible runtime launches: {runtime_policy}")

    runs: set[Path] = set()
    for payload in payloads:
        runs.update(collect_run_dirs(payload))

    run_summaries = [summarize_run(run) for run in sorted(runs, key=lambda item: str(item).lower())]
    for run in run_summaries:
        if not run.get("passed"):
            failures.extend(run.get("failures") or [f"{run.get('run')} failed no-visible guard"])

    return {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "passed": not failures,
        "runtime_policy": runtime_policy,
        "guard_policy": "all referenced CDB surface-dump runs must be hidden-desktop evidence",
        "run_count": len(run_summaries),
        "hidden_run_count": sum(1 for run in run_summaries if run.get("passed")),
        "runs": run_summaries,
        "failures": failures,
    }


def build_guard(args: argparse.Namespace) -> dict[str, Any]:
    payloads: list[dict[str, Any]] = []
    runtime_policy = ""
    if args.refresh_json.exists():
        refresh = load_json(args.refresh_json)
        payloads.append(refresh)
        runtime_policy = str(refresh.get("runtime_policy") or "")
    else:
        payloads.append({})
        runtime_policy = ""

    for path in args.include_json:
        if path.exists():
            payloads.append(load_json(path))

    return build_guard_from_payloads(payloads, runtime_policy=runtime_policy)


def print_guard(guard: dict[str, Any]) -> None:
    print(f"overall: {status_text(guard['passed'])}")
    print(f"runtime-policy: {guard['runtime_policy']}")
    print(f"run-count: {guard['run_count']}")
    print(f"hidden-run-count: {guard['hidden_run_count']}")
    if guard["failures"]:
        print("failures:")
        for failure in guard["failures"]:
            print(f"  - {failure}")


def write_markdown(path: Path, guard: dict[str, Any]) -> None:
    lines = [
        "# No-Visible Runtime Guard",
        "",
        f"- Overall: {status_text(guard['passed'])}",
        f"- Generated: `{guard['generated_at']}`",
        f"- Runtime policy: {guard['runtime_policy']}",
        f"- Guard policy: {guard['guard_policy']}",
        f"- Referenced CDB surface-dump runs: `{guard['run_count']}`",
        f"- Hidden-desktop runs: `{guard['hidden_run_count']}`",
        "",
        "## Runs",
        "",
    ]
    for run in guard["runs"]:
        lines.append(
            "- `{run}`: `{status}` launch=`{launch}` hidden=`{hidden}` stage=`{stage}`".format(
                run=run.get("run"),
                status=status_text(bool(run.get("passed"))),
                launch=run.get("launch_mode"),
                hidden=run.get("hidden_desktop"),
                stage=run.get("stage"),
            )
        )
        for failure in run.get("failures", []):
            lines.append(f"  - {failure}")
    if guard["failures"]:
        lines.extend(["", "## Failures", ""])
        lines.extend(f"- {failure}" for failure in guard["failures"])
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh-json", type=Path, default=DEFAULT_REFRESH_JSON)
    parser.add_argument("--include-json", type=Path, action="append", default=[])
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
