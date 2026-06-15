#!/usr/bin/env python3
"""Plan and optionally execute proof-preserving repo compaction.

The cleanup is intentionally conservative. It archives stale generated capture
artifacts out of the repository, deletes only ignored cache/test-temp
directories, and refuses to touch tracked or modified files.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import capture_corpus_index


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_JSON = Path("reports/repo-compaction-current.json")
DEFAULT_MD = Path("reports/repo-compaction-current.md")
RUNTIME_POLICY = (
    "repo-only dry-run by default; execute mode moves stale generated captures "
    "to the requested archive root and deletes only ignored cache directories; "
    "does not launch Clash95, CDB, wrappers, PowerShell harnesses, or visible windows"
)
GUARD_POLICY = (
    "archive/delete candidates must be untracked, unmodified, inside approved "
    "generated-output areas, outside raw/.git, and must not include current or "
    "preserved HD evidence"
)

PRESERVED_CAPTURE_ENTRIES = {
    "cdb-surface-dump-20260429-111340",
    "cdb-surface-dump-20260506-190037",
    "cdb-surface-dump-20260506-201114",
    "cdb-surface-dump-20260515-105041",
    "cdb-surface-dump-20260515-105411",
    "cdb-surface-dump-20260515-105458",
    "cdb-surface-dump-20260515-105557",
    "cdb-surface-dump-20260615-100407",
}

GENERATED_CAPTURE_DIR_PREFIXES = (
    "battle-visible-input-",
    "cdb-surface-dump-",
    "clicktest-",
    "sandbox-",
    "visual-smoke-",
)

CACHE_DIR_NAMES = {
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
}

EXTRA_TEMP_DIRS = {
    ".codex-loop/tmp-tests",
    ".codex-loop/tmp-tests-probe",
    "captures/tmp-tests-probe",
}

FORBIDDEN_REPO_SUFFIXES = {
    ".exe",
    ".dll",
    ".dmp",
    ".dump",
    ".pml",
    ".iso",
    ".cue",
    ".bin",
    ".sav",
    ".sg",
    ".dat",
}


@dataclass(frozen=True)
class GitState:
    tracked: set[str]
    modified: set[str]
    untracked: set[str]
    status_lines: list[str]
    failures: list[str]


def status_text(passed: bool) -> str:
    return "PASS" if passed else "FAIL"


def norm_rel(value: str | Path) -> str:
    return str(value).replace("\\", "/").strip("/")


def rel_to_root(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def is_under(rel: str, parent: str) -> bool:
    parent = norm_rel(parent)
    rel = norm_rel(rel)
    return rel == parent or rel.startswith(parent + "/")


def git_status_path(line: str) -> str:
    path = line[3:] if len(line) > 3 else ""
    if " -> " in path:
        path = path.split(" -> ", 1)[1]
    return norm_rel(path)


def run_git(root: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=str(root),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def read_git_state(root: Path) -> GitState:
    failures: list[str] = []
    tracked: set[str] = set()
    modified: set[str] = set()
    untracked: set[str] = set()
    status_lines: list[str] = []

    ls_files = run_git(root, ["ls-files", "-z"])
    if ls_files.returncode:
        failures.append(f"git ls-files failed: {ls_files.stderr.strip()}")
    else:
        tracked = {norm_rel(part) for part in ls_files.stdout.split("\0") if part}

    status = run_git(root, ["status", "--porcelain=v1", "--untracked-files=all"])
    if status.returncode:
        failures.append(f"git status failed: {status.stderr.strip()}")
    else:
        status_lines = [line for line in status.stdout.splitlines() if line.strip()]
        for line in status_lines:
            code = line[:2]
            path = git_status_path(line)
            if not path:
                continue
            if code == "??":
                untracked.add(path)
            else:
                modified.add(path)

    return GitState(
        tracked=tracked,
        modified=modified,
        untracked=untracked,
        status_lines=status_lines,
        failures=failures,
    )


def path_intersects_any(target: str, paths: set[str]) -> bool:
    target = norm_rel(target)
    for path in paths:
        if path == target or path.startswith(target + "/"):
            return True
    return False


def target_has_tracked_or_modified(target: str, git_state: GitState) -> bool:
    return path_intersects_any(target, git_state.tracked) or path_intersects_any(target, git_state.modified)


def safe_repo_target(root: Path, rel: str) -> tuple[bool, str]:
    rel = norm_rel(rel)
    if not rel or rel in {".", "/"}:
        return False, "target is repository root"
    if is_under(rel, ".git"):
        return False, "target is inside .git"
    if is_under(rel, "raw"):
        return False, "target is inside user-owned raw/"
    path = (root / rel).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError:
        return False, "target escapes repository root"
    return True, ""


def source_files_for_current_refs(root: Path) -> list[Path]:
    sources: set[Path] = set(capture_corpus_index.CURRENT_REFERENCE_SOURCES)
    captures = root / "captures"
    if captures.exists():
        for suffix in ("*.md", "*.json"):
            for path in captures.glob(suffix):
                name = path.name.lower()
                if "current" in name:
                    sources.add(path.relative_to(root))
        current = captures / "current"
        if current.exists():
            for suffix in ("*.md", "*.json"):
                for path in current.glob(suffix):
                    name = path.name.lower()
                    if "current" in name:
                        sources.add(path.relative_to(root))
    return sorted(sources, key=lambda path: path.as_posix().lower())


def active_capture_entries(root: Path) -> tuple[set[str], dict[str, list[str]]]:
    entries = {"current"}
    sources_by_entry: dict[str, list[str]] = {"current": ["current-evidence-directory"]}
    for entry in PRESERVED_CAPTURE_ENTRIES:
        for key in {entry, f"archive/{entry}"}:
            entries.add(key)
            sources_by_entry.setdefault(key, []).append("preserved-proof-set")
    for source in source_files_for_current_refs(root):
        source_path = root / source
        for ref in capture_corpus_index.extract_refs(root, source_path):
            entry = top_capture_entry(ref)
            if not entry:
                continue
            entries.add(entry)
            sources_by_entry.setdefault(entry, []).append(source.as_posix())
    return entries, sources_by_entry


def top_capture_entry(rel: str) -> str | None:
    parts = norm_rel(rel).split("/")
    if len(parts) >= 2 and parts[0] == "captures":
        if parts[1] == "current":
            return "current"
        if parts[1] == "archive" and len(parts) >= 3:
            return f"archive/{parts[2]}"
        return parts[1]
    return None


def is_current_capture_root_file(rel: str) -> bool:
    path = Path(norm_rel(rel))
    parts = path.parts
    if len(parts) >= 2 and parts[0] == "captures" and parts[1] == "current":
        return True
    return len(parts) == 2 and parts[0] == "captures" and "current" in parts[1].lower()


def is_generated_capture_dir_name(name: str) -> bool:
    name = norm_rel(name).split("/")[-1]
    lower = name.lower()
    return lower.startswith(GENERATED_CAPTURE_DIR_PREFIXES)


def is_capture_archive_candidate(rel: str, active_entries: set[str]) -> tuple[bool, str]:
    rel = norm_rel(rel)
    if rel == "captures/README.md":
        return False, "captures layout index"
    entry = top_capture_entry(rel)
    if not entry:
        return False, "not under captures/"
    if entry in active_entries:
        return False, "capture entry is current or preserved evidence"
    if is_current_capture_root_file(rel):
        return False, "current capture summary/report"
    if "/" in rel[len("captures/") :]:
        if is_generated_capture_dir_name(entry):
            return True, "stale generated capture directory"
        return True, "stale unreferenced capture directory"
    suffix = Path(rel).suffix.lower()
    if suffix in {".json", ".md", ".txt", ".csv", ".png"}:
        return True, "stale unreferenced capture file"
    return False, "capture path is not a recognized generated artifact"


def archive_target_for_untracked(rel: str, active_entries: set[str]) -> tuple[str | None, str]:
    rel = norm_rel(rel)
    should_archive, reason = is_capture_archive_candidate(rel, active_entries)
    if not should_archive:
        return None, reason
    entry = top_capture_entry(rel)
    if entry and "/" in rel[len("captures/") :] and is_generated_capture_dir_name(entry):
        return f"captures/{entry}", reason
    return rel, reason


def collect_archive_candidates(git_state: GitState, active_entries: set[str]) -> dict[str, dict[str, Any]]:
    candidates: dict[str, dict[str, Any]] = {}
    for rel in sorted(git_state.untracked):
        target, reason = archive_target_for_untracked(rel, active_entries)
        if not target:
            continue
        record = candidates.setdefault(
            target,
            {
                "path": target,
                "action": "archive",
                "reason": reason,
                "source_untracked_paths": [],
            },
        )
        record["source_untracked_paths"].append(rel)
    return candidates


def collect_delete_candidates(root: Path) -> dict[str, dict[str, Any]]:
    candidates: dict[str, dict[str, Any]] = {}
    for name in CACHE_DIR_NAMES:
        for path in root.rglob(name):
            rel = rel_to_root(root, path)
            if ".git" in path.parts or is_under(rel, ".codex-loop"):
                continue
            if path.is_dir():
                candidates[rel] = {
                    "path": rel,
                    "action": "delete",
                    "reason": f"ignored cache directory {name}",
                }
    for rel in EXTRA_TEMP_DIRS:
        path = root / rel
        if path.exists() and path.is_dir() and not contains_git_dir(path):
            candidates[norm_rel(rel)] = {
                "path": norm_rel(rel),
                "action": "delete",
                "reason": "ignored temporary test directory",
            }
    return candidates


def collect_forbidden_repo_artifacts(root: Path, git_state: GitState, archive_candidates: dict[str, dict[str, Any]]) -> list[str]:
    archive_targets = set(archive_candidates)
    bad: list[str] = []
    inventory = sorted(git_state.tracked | git_state.modified | git_state.untracked)
    for rel in inventory:
        suffix = Path(rel).suffix.lower()
        if suffix not in FORBIDDEN_REPO_SUFFIXES:
            continue
        if any(rel == target or rel.startswith(target + "/") for target in archive_targets):
            continue
        bad.append(rel)
    return bad


def contains_git_dir(path: Path) -> bool:
    if not path.is_dir():
        return False
    for child in path.rglob(".git"):
        if child.is_dir():
            return True
    return False


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def target_file_records(root: Path, rel: str) -> list[dict[str, Any]]:
    path = root / rel
    records: list[dict[str, Any]] = []
    if path.is_file():
        records.append(
            {
                "path": rel,
                "size": path.stat().st_size,
                "sha256": file_sha256(path),
            }
        )
        return records
    if path.is_dir():
        for file_path in sorted(path.rglob("*")):
            if not file_path.is_file():
                continue
            file_rel = rel_to_root(root, file_path)
            records.append(
                {
                    "path": file_rel,
                    "size": file_path.stat().st_size,
                    "sha256": file_sha256(file_path),
                }
            )
    return records


def archive_root_file_manifest(archive_root: Path) -> list[dict[str, Any]]:
    if not archive_root.exists():
        return []
    records: list[dict[str, Any]] = []
    for file_path in sorted(archive_root.rglob("*")):
        if not file_path.is_file():
            continue
        rel = file_path.relative_to(archive_root).as_posix()
        records.append(
            {
                "old_path": rel,
                "new_path": str(file_path),
                "size": file_path.stat().st_size,
                "sha256": file_sha256(file_path),
            }
        )
    return records


def candidate_size(root: Path, rel: str) -> int:
    path = root / rel
    if path.is_file():
        return path.stat().st_size
    if path.is_dir():
        return sum(file_path.stat().st_size for file_path in path.rglob("*") if file_path.is_file())
    return 0


def default_archive_root() -> Path:
    stamp = datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")
    return Path(r"C:\ClashCaptures") / f"repo-compaction-{stamp}"


def validate_archive_root(root: Path, archive_root: Path) -> tuple[bool, str]:
    resolved = archive_root.resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError:
        return True, ""
    return False, "archive root must be outside the repository"


def build_plan(
    *,
    root: Path,
    archive_root: Path,
    execute: bool,
) -> dict[str, Any]:
    root = root.resolve()
    archive_root = archive_root.resolve()
    git_state = read_git_state(root)
    active_entries, active_sources = active_capture_entries(root)
    archive_candidates = collect_archive_candidates(git_state, active_entries)
    delete_candidates = collect_delete_candidates(root)
    failures = list(git_state.failures)
    warnings: list[str] = []

    archive_root_ok, archive_root_failure = validate_archive_root(root, archive_root)
    if not archive_root_ok:
        failures.append(archive_root_failure)

    for rel in sorted(archive_candidates):
        safe, reason = safe_repo_target(root, rel)
        if not safe:
            failures.append(f"archive target rejected: {rel}: {reason}")
        if target_has_tracked_or_modified(rel, git_state):
            failures.append(f"archive target has tracked or modified content: {rel}")
        if not (root / rel).exists():
            failures.append(f"archive target is missing: {rel}")
    for rel in sorted(delete_candidates):
        safe, reason = safe_repo_target(root, rel)
        if not safe:
            failures.append(f"delete target rejected: {rel}: {reason}")
        if target_has_tracked_or_modified(rel, git_state):
            failures.append(f"delete target has tracked or modified content: {rel}")
        if not (root / rel).exists():
            warnings.append(f"delete target disappeared before execution: {rel}")

    forbidden_artifacts = collect_forbidden_repo_artifacts(root, git_state, archive_candidates)
    if forbidden_artifacts:
        failures.append("forbidden binary/dump/save artifacts in repo: " + ", ".join(forbidden_artifacts[:20]))

    preserved_present = sorted(
        entry
        for entry in PRESERVED_CAPTURE_ENTRIES
        if (root / "captures" / entry).exists() or (root / "captures" / "archive" / entry).exists()
    )
    preserved_missing = sorted(entry for entry in PRESERVED_CAPTURE_ENTRIES if entry not in preserved_present)
    archived_bytes = sum(candidate_size(root, rel) for rel in archive_candidates)
    delete_bytes = sum(candidate_size(root, rel) for rel in delete_candidates)

    plan = {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "passed": not failures,
        "executed": execute,
        "runtime_policy": RUNTIME_POLICY,
        "guard_policy": GUARD_POLICY,
        "root": str(root),
        "archive_root": str(archive_root),
        "git_status_count": len(git_state.status_lines),
        "tracked_count": len(git_state.tracked),
        "modified_count": len(git_state.modified),
        "untracked_count": len(git_state.untracked),
        "active_capture_entries": sorted(active_entries),
        "active_capture_entry_sources": active_sources,
        "preserved_capture_entries_present": preserved_present,
        "preserved_capture_entries_missing": preserved_missing,
        "forbidden_repo_artifacts": forbidden_artifacts,
        "archive_candidate_count": len(archive_candidates),
        "archive_candidate_bytes": archived_bytes,
        "delete_candidate_count": len(delete_candidates),
        "delete_candidate_bytes": delete_bytes,
        "archive_candidates": [
            {
                **archive_candidates[rel],
                "size": candidate_size(root, rel),
                "destination": str(archive_root / rel),
            }
            for rel in sorted(archive_candidates)
        ],
        "delete_candidates": [
            {
                **delete_candidates[rel],
                "size": candidate_size(root, rel),
            }
            for rel in sorted(delete_candidates)
        ],
        "moved_files": [],
        "archive_root_file_manifest": archive_root_file_manifest(archive_root),
        "deleted_paths": [],
        "warnings": warnings,
        "failures": failures,
    }
    return plan


def execute_plan(plan: dict[str, Any]) -> None:
    root = Path(plan["root"])
    archive_root = Path(plan["archive_root"])
    plan.setdefault("moved_files", [])
    plan.setdefault("deleted_paths", [])
    for candidate in plan["archive_candidates"]:
        rel = candidate["path"]
        source = root / rel
        destination = archive_root / rel
        if not source.exists():
            raise FileNotFoundError(f"archive source vanished: {rel}")
        if destination.exists():
            raise FileExistsError(f"archive destination already exists: {destination}")
        records = target_file_records(root, rel)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source), str(destination))
        for record in records:
            old_rel = record["path"]
            plan["moved_files"].append(
                {
                    **record,
                    "old_path": old_rel,
                    "new_path": str(archive_root / old_rel),
                    "archive_entry": rel,
                    "reason": candidate["reason"],
                }
            )

    for candidate in plan["delete_candidates"]:
        rel = candidate["path"]
        source = root / rel
        if not source.exists():
            continue
        size = candidate_size(root, rel)
        try:
            if source.is_dir():
                shutil.rmtree(source)
            else:
                source.unlink()
        except OSError as exc:
            plan.setdefault("warnings", []).append(f"delete skipped for {rel}: {exc}")
            continue
        plan["deleted_paths"].append({"path": rel, "size": size, "reason": candidate["reason"]})

    plan["archive_root_file_manifest"] = archive_root_file_manifest(archive_root)


def print_plan(plan: dict[str, Any]) -> None:
    print(f"overall: {status_text(bool(plan['passed']))}")
    print(f"executed: {plan['executed']}")
    print(f"runtime-policy: {plan['runtime_policy']}")
    print(f"archive-root: {plan['archive_root']}")
    print(f"modified: {plan['modified_count']}")
    print(f"untracked: {plan['untracked_count']}")
    print(f"archive-candidates: {plan['archive_candidate_count']}")
    print(f"archive-mb: {plan['archive_candidate_bytes'] / (1024 * 1024):.2f}")
    print(f"delete-candidates: {plan['delete_candidate_count']}")
    print(f"delete-mb: {plan['delete_candidate_bytes'] / (1024 * 1024):.2f}")
    if plan["warnings"]:
        print("warnings:")
        for warning in plan["warnings"][:20]:
            print(f"  - {warning}")
    if plan["failures"]:
        print("failures:")
        for failure in plan["failures"]:
            print(f"  - {failure}")


def write_markdown(path: Path, plan: dict[str, Any]) -> None:
    lines = [
        "# Repo Compaction Cleanup",
        "",
        f"- Overall: {status_text(bool(plan['passed']))}",
        f"- Generated: `{plan['generated_at']}`",
        f"- Executed: `{plan['executed']}`",
        f"- Runtime policy: {plan['runtime_policy']}",
        f"- Guard policy: {plan['guard_policy']}",
        f"- Archive root: `{plan['archive_root']}`",
        f"- Modified files: `{plan['modified_count']}`",
        f"- Untracked paths: `{plan['untracked_count']}`",
        f"- Archive candidates: `{plan['archive_candidate_count']}`",
        f"- Archive candidate size: `{plan['archive_candidate_bytes'] / (1024 * 1024):.2f} MB`",
        f"- Delete candidates: `{plan['delete_candidate_count']}`",
        f"- Delete candidate size: `{plan['delete_candidate_bytes'] / (1024 * 1024):.2f} MB`",
        f"- Moved files: `{len(plan['moved_files'])}`",
        f"- Archive-root manifest files: `{len(plan.get('archive_root_file_manifest', []))}`",
        f"- Deleted paths: `{len(plan['deleted_paths'])}`",
        "",
        "## Preserved Proof Entries",
        "",
    ]
    lines.extend(f"- `captures/{entry}`" for entry in plan["preserved_capture_entries_present"])
    if plan["preserved_capture_entries_missing"]:
        lines.extend(["", "## Preserved Entries Missing Locally", ""])
        lines.extend(f"- `captures/{entry}`" for entry in plan["preserved_capture_entries_missing"])
    lines.extend(["", "## Archive Candidates", ""])
    if plan["archive_candidates"]:
        for candidate in plan["archive_candidates"][:200]:
            lines.append(
                f"- `{candidate['path']}` -> `{candidate['destination']}` "
                f"({candidate['size'] / (1024 * 1024):.2f} MB, {candidate['reason']})"
            )
        if len(plan["archive_candidates"]) > 200:
            lines.append(f"- ... {len(plan['archive_candidates']) - 200} more")
    else:
        lines.append("- None")
    lines.extend(["", "## Delete Candidates", ""])
    if plan["delete_candidates"]:
        lines.extend(
            f"- `{candidate['path']}` ({candidate['size'] / (1024 * 1024):.2f} MB, {candidate['reason']})"
            for candidate in plan["delete_candidates"][:200]
        )
    else:
        lines.append("- None")
    if plan["warnings"]:
        lines.extend(["", "## Warnings", ""])
        lines.extend(f"- {warning}" for warning in plan["warnings"])
    if plan["failures"]:
        lines.extend(["", "## Failures", ""])
        lines.extend(f"- {failure}" for failure in plan["failures"])
    if plan["moved_files"]:
        lines.extend(["", "## Moved File Manifest", ""])
        for record in plan["moved_files"][:300]:
            lines.append(f"- `{record['old_path']}` -> `{record['new_path']}` sha256 `{record['sha256']}`")
        if len(plan["moved_files"]) > 300:
            lines.append(f"- ... {len(plan['moved_files']) - 300} more")
    if plan.get("archive_root_file_manifest"):
        lines.extend(["", "## Archive Root File Manifest", ""])
        for record in plan["archive_root_file_manifest"][:300]:
            lines.append(f"- `{record['old_path']}` -> `{record['new_path']}` sha256 `{record['sha256']}`")
        if len(plan["archive_root_file_manifest"]) > 300:
            lines.append(f"- ... {len(plan['archive_root_file_manifest']) - 300} more")
    if plan["deleted_paths"]:
        lines.extend(["", "## Deleted Paths", ""])
        lines.extend(f"- `{record['path']}` ({record['reason']})" for record in plan["deleted_paths"])
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=REPO_ROOT)
    parser.add_argument("--archive-root", type=Path, default=default_archive_root())
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--write-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--write-markdown", type=Path, default=DEFAULT_MD)
    parser.add_argument("--require-pass", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    execute = bool(args.execute)
    plan = build_plan(root=args.root, archive_root=args.archive_root, execute=execute)
    if execute and plan["passed"]:
        try:
            execute_plan(plan)
        except Exception as exc:  # noqa: BLE001 - reported in manifest for cleanup safety
            plan["passed"] = False
            plan["failures"].append(f"execution failed: {exc}")
    elif execute and not plan["passed"]:
        plan["warnings"].append("execute requested but skipped because safety checks failed")

    print_plan(plan)
    if args.write_json:
        args.write_json.parent.mkdir(parents=True, exist_ok=True)
        args.write_json.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    if args.write_markdown:
        write_markdown(args.write_markdown, plan)
    if args.require_pass and not plan["passed"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
