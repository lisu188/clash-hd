#!/usr/bin/env python3
"""Core logic for the Clash95 HD launcher: verify, patch, deploy, launch.

Launch policy: the game process starts only on an explicit user action.
``launch_game`` requires confirmed=True (the GUI Play button or the CLI
``--launch --yes-launch`` double flag) and refuses everything else. This
module writes only under the launcher candidates root and the per-user
settings directory; it never modifies ``C:\\Clash\\clash95.exe`` and is never
part of the evidence refresh.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import bootstrap

REPO_ROOT = bootstrap.ensure_repo_paths()

import patch_clash95_hd  # noqa: E402
import process_hygiene_guard  # noqa: E402

import ini as ini_mod  # noqa: E402
import presets  # noqa: E402


LAUNCHER_VERSION = "0.1.0"
DEFAULT_CLASH_DIR = Path("C:/Clash")
DEFAULT_CANDIDATES_ROOT = Path("C:/ClashTests/launcher")
BASE_EXE_NAME = "clash95.exe"
WRAPPER_DLL_NAME = "ddraw.dll"
DXCFG_NAME = "dxcfg.ini"
MANIFEST_NAME = "candidate-manifest.json"
MANIFEST_SCHEMA = 1
MIN_FREE_BYTES = 50 * 1024 * 1024
LAUNCH_POLICY = (
    "user-initiated visible launch only; launch_game requires confirmed=True; "
    "the launcher is never part of the evidence refresh"
)
WRITE_POLICY = (
    "writes only under the launcher candidates root and the per-user settings "
    "directory; never modifies the base game executable"
)
PROCESS_EXACT_NAMES = ("cdb.exe",)
PROCESS_PREFIXES = ("clash95",)


class LauncherError(RuntimeError):
    """A launcher precondition failed; the message is user-facing."""


@dataclass(frozen=True)
class CheckResult:
    name: str
    passed: bool
    detail: dict[str, Any]


@dataclass(frozen=True)
class EnvironmentReport:
    base_exe: CheckResult
    wrapper_dll: CheckResult
    candidates_root: CheckResult
    running_processes: CheckResult

    @property
    def ready_to_patch(self) -> bool:
        return self.base_exe.passed and self.candidates_root.passed

    def to_dict(self) -> dict[str, Any]:
        return {
            check.name: {"passed": check.passed, **check.detail}
            for check in (
                self.base_exe,
                self.wrapper_dll,
                self.candidates_root,
                self.running_processes,
            )
        }


@dataclass(frozen=True)
class CandidatePlan:
    stage: str
    resolution: str
    scaling_mode: str
    clash_dir: Path
    candidates_root: Path
    candidate_dir: Path
    candidate_exe: Path
    wrapper_source: Path
    wrapper_target: Path
    dxcfg_target: Path
    manifest_path: Path
    base_exe: Path
    expected_base_sha: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "stage": self.stage,
            "resolution": self.resolution,
            "scaling_mode": self.scaling_mode,
            "clash_dir": str(self.clash_dir),
            "candidates_root": str(self.candidates_root),
            "candidate_dir": str(self.candidate_dir),
            "candidate_exe": str(self.candidate_exe),
            "wrapper_source": str(self.wrapper_source),
            "wrapper_target": str(self.wrapper_target),
            "dxcfg_target": str(self.dxcfg_target),
            "manifest_path": str(self.manifest_path),
            "base_exe": str(self.base_exe),
            "expected_base_sha": self.expected_base_sha,
        }


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _norm(path: Path | str) -> str:
    return os.path.normcase(str(Path(path).resolve()))


def is_under(path: Path | str, root: Path | str) -> bool:
    norm_path = _norm(path)
    norm_root = _norm(root)
    if norm_path == norm_root:
        return True
    return norm_path.startswith(norm_root.rstrip("\\/") + os.sep)


def _existing_ancestor(path: Path) -> Path | None:
    for candidate in (path, *path.resolve().parents):
        if candidate.exists():
            return candidate
    return None


def find_running_clash(
    snapshot_rows: list[dict[str, str]] | None = None,
) -> list[dict[str, str]]:
    if snapshot_rows is None:
        rows, returncode, error = process_hygiene_guard.process_snapshot_rows()
        if returncode != 0:
            return [{"image_name": "<snapshot-error>", "pid": "", "error": error}]
    else:
        rows = snapshot_rows
    return [
        row
        for row in rows
        if process_hygiene_guard.is_target_process(
            str(row.get("image_name", "")).lower(),
            PROCESS_EXACT_NAMES,
            PROCESS_PREFIXES,
        )
    ]


def pid_alive(pid: int) -> bool:
    rows, returncode, _error = process_hygiene_guard.process_snapshot_rows()
    if returncode != 0:
        return True
    return any(str(pid) == str(row.get("pid", "")) for row in rows)


def check_environment(
    clash_dir: Path = DEFAULT_CLASH_DIR,
    candidates_root: Path = DEFAULT_CANDIDATES_ROOT,
    expected_sha: str | None = None,
    snapshot_rows: list[dict[str, str]] | None = None,
) -> EnvironmentReport:
    expected = expected_sha or patch_clash95_hd.EXPECTED_SHA256
    base = Path(clash_dir) / BASE_EXE_NAME
    if base.is_file():
        actual = sha256_bytes(base.read_bytes())
        base_check = CheckResult(
            "base_exe",
            actual == expected,
            {"path": str(base), "sha256": actual, "expected_sha256": expected},
        )
    else:
        base_check = CheckResult(
            "base_exe",
            False,
            {"path": str(base), "error": "base game executable not found"},
        )

    wrapper = Path(clash_dir) / WRAPPER_DLL_NAME
    wrapper_check = CheckResult(
        "wrapper_dll", wrapper.is_file(), {"path": str(wrapper)}
    )

    anchor = _existing_ancestor(Path(candidates_root))
    if anchor is None:
        root_check = CheckResult(
            "candidates_root",
            False,
            {"path": str(candidates_root), "error": "no existing ancestor"},
        )
    else:
        try:
            usage = shutil.disk_usage(anchor)
            root_check = CheckResult(
                "candidates_root",
                usage.free >= MIN_FREE_BYTES,
                {"path": str(candidates_root), "free_bytes": usage.free},
            )
        except OSError as exc:
            root_check = CheckResult(
                "candidates_root",
                False,
                {"path": str(candidates_root), "error": str(exc)},
            )

    running = find_running_clash(snapshot_rows=snapshot_rows)
    running_check = CheckResult(
        "running_processes", not running, {"matches": running}
    )
    return EnvironmentReport(base_check, wrapper_check, root_check, running_check)


def plan_candidate(
    stage: str | None = None,
    resolution: str = "800x600",
    scaling_mode: str = ini_mod.DEFAULT_SCALING_MODE,
    clash_dir: Path = DEFAULT_CLASH_DIR,
    candidates_root: Path = DEFAULT_CANDIDATES_ROOT,
    manifest: dict[str, Any] | None = None,
    expected_base_sha: str | None = None,
    allow_repo_candidates: bool = False,
) -> CandidatePlan:
    manifest = manifest if manifest is not None else presets.load_manifest()
    stage = stage or presets.stable_stage(manifest)
    if stage not in patch_clash95_hd.STAGE_GROUPS:
        raise LauncherError(f"Unknown patch stage: {stage}")
    presets.parse_resolution_key(resolution)
    default = presets.default_key(manifest)
    if resolution != default and not presets.patcher_supports_resolutions(
        patch_clash95_hd
    ):
        raise LauncherError(
            f"Resolution {resolution} is not supported yet: the patcher builds "
            f"only {default} until multi-resolution support lands."
        )
    if scaling_mode not in ini_mod.VERIFIED_SCALING_MODES:
        known = ", ".join(sorted(ini_mod.VERIFIED_SCALING_MODES))
        raise LauncherError(
            f"Unknown scaling mode {scaling_mode!r}; verified modes: {known}"
        )

    clash_dir = Path(clash_dir)
    candidates_root = Path(candidates_root)
    if is_under(candidates_root, clash_dir):
        raise LauncherError(
            f"Refusing candidates root inside the game directory: {candidates_root}"
        )
    if is_under(candidates_root, REPO_ROOT) and not allow_repo_candidates:
        raise LauncherError(
            f"Refusing candidates root inside the repository: {candidates_root} "
            "(allow_repo_candidates is reserved for fixture tests)"
        )

    candidate_dir = candidates_root / resolution
    candidate_exe = candidate_dir / f"clash95_hd_{resolution}.exe"
    base_exe = clash_dir / BASE_EXE_NAME
    if _norm(candidate_exe) == _norm(base_exe):
        raise LauncherError("Refusing to target the base game executable.")
    return CandidatePlan(
        stage=stage,
        resolution=resolution,
        scaling_mode=scaling_mode,
        clash_dir=clash_dir,
        candidates_root=candidates_root,
        candidate_dir=candidate_dir,
        candidate_exe=candidate_exe,
        wrapper_source=clash_dir / WRAPPER_DLL_NAME,
        wrapper_target=candidate_dir / WRAPPER_DLL_NAME,
        dxcfg_target=candidate_dir / DXCFG_NAME,
        manifest_path=candidate_dir / MANIFEST_NAME,
        base_exe=base_exe,
        expected_base_sha=expected_base_sha or patch_clash95_hd.EXPECTED_SHA256,
    )


def assert_plan_paths(plan: CandidatePlan) -> None:
    for target in (
        plan.candidate_dir,
        plan.candidate_exe,
        plan.wrapper_target,
        plan.dxcfg_target,
        plan.manifest_path,
    ):
        if not is_under(target, plan.candidates_root):
            raise LauncherError(f"Refusing write outside candidates root: {target}")
        if is_under(target, plan.clash_dir):
            raise LauncherError(f"Refusing write inside the game directory: {target}")


def classify_candidate_bytes(
    data: bytes, patches: list[Any]
) -> dict[str, Any]:
    counts: dict[str, Any] = {"patched": 0, "original": 0, "unexpected": 0}
    failures: list[str] = []
    for patch in patches:
        actual = data[patch.offset : patch.offset + len(patch.new)]
        if actual == patch.new:
            counts["patched"] += 1
        elif actual == patch.old:
            counts["original"] += 1
            failures.append(
                f"0x{patch.offset:06X}: still original bytes ({patch.note})"
            )
        else:
            counts["unexpected"] += 1
            failures.append(
                f"0x{patch.offset:06X}: unexpected bytes ({patch.note})"
            )
    counts["failures"] = failures
    return counts


def read_candidate_manifest(plan: CandidatePlan) -> dict[str, Any] | None:
    try:
        manifest = json.loads(plan.manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError):
        return None
    return manifest if isinstance(manifest, dict) else None


def _manifest_matches(plan: CandidatePlan, output_sha: str) -> bool:
    manifest = read_candidate_manifest(plan)
    if not manifest:
        return False
    return (
        manifest.get("schema") == MANIFEST_SCHEMA
        and manifest.get("stage") == plan.stage
        and manifest.get("resolution") == plan.resolution
        and manifest.get("output_sha256") == output_sha
    )


def ensure_candidate(
    plan: CandidatePlan, progress: Callable[[str], None] | None = None
) -> dict[str, Any]:
    say = progress or (lambda message: None)
    assert_plan_paths(plan)
    if not plan.base_exe.is_file():
        raise LauncherError(f"Base game executable not found: {plan.base_exe}")
    data = plan.base_exe.read_bytes()
    base_sha = sha256_bytes(data)
    if base_sha != plan.expected_base_sha:
        raise LauncherError(
            "Base executable SHA-256 mismatch; refusing to patch.\n"
            f"Expected: {plan.expected_base_sha}\n"
            f"Actual:   {base_sha}\n"
            "The launcher has no override; restore an original clash95.exe."
        )
    say(f"Base SHA-256 verified: {base_sha[:16]}…")

    patches = patch_clash95_hd.select_patches(plan.stage)
    try:
        patch_clash95_hd.validate_input(data, patches)
    except SystemExit as exc:
        raise LauncherError(f"Base byte validation failed: {exc}") from exc
    patched = patch_clash95_hd.apply_patches(data, patches)
    output_sha = sha256_bytes(patched)

    reused = False
    if plan.candidate_exe.is_file() and _manifest_matches(plan, output_sha):
        if sha256_bytes(plan.candidate_exe.read_bytes()) == output_sha:
            reused = True
            say(f"Reusing existing candidate: {plan.candidate_exe}")
    if not reused:
        plan.candidate_dir.mkdir(parents=True, exist_ok=True)
        plan.candidate_exe.write_bytes(patched)
        say(f"Wrote candidate: {plan.candidate_exe}")

    disk = plan.candidate_exe.read_bytes()
    if sha256_bytes(disk) != output_sha:
        raise LauncherError(
            f"Candidate on disk does not match the expected output SHA: "
            f"{plan.candidate_exe}"
        )
    gate = classify_candidate_bytes(disk, patches)
    if gate["original"] or gate["unexpected"]:
        details = "\n".join(gate["failures"][:10])
        raise LauncherError(
            f"Byte-manifest gate failed for {plan.candidate_exe}:\n{details}"
        )
    say(
        f"Byte gate: {gate['patched']} patched, {gate['original']} original, "
        f"{gate['unexpected']} unexpected"
    )
    return {
        "reused": reused,
        "base_sha256": base_sha,
        "output_sha256": output_sha,
        "patch_count": len(patches),
        "byte_gate": gate,
    }


def deploy_runtime_files(
    plan: CandidatePlan,
    candidate_result: dict[str, Any] | None = None,
    progress: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    say = progress or (lambda message: None)
    assert_plan_paths(plan)
    plan.candidate_dir.mkdir(parents=True, exist_ok=True)

    result: dict[str, Any] = {"wrapper": "missing", "wrapper_dll_sha256": None}
    if plan.wrapper_source.is_file():
        shutil.copyfile(plan.wrapper_source, plan.wrapper_target)
        result["wrapper"] = "copied"
        result["wrapper_dll_sha256"] = sha256_bytes(
            plan.wrapper_target.read_bytes()
        )
        say(f"Copied wrapper {WRAPPER_DLL_NAME} next to the candidate.")
    else:
        say(
            f"Wrapper {WRAPPER_DLL_NAME} not found in {plan.clash_dir}; "
            "the launcher never ships or downloads DLLs."
        )

    plan.dxcfg_target.write_text(
        ini_mod.render_dxcfg(plan.scaling_mode), encoding="utf-8"
    )
    result["dxcfg"] = "written"

    manifest = {
        "schema": MANIFEST_SCHEMA,
        "generated_at": datetime.now(timezone.utc)
        .astimezone()
        .isoformat(timespec="seconds"),
        "launcher_version": LAUNCHER_VERSION,
        "stage": plan.stage,
        "resolution": plan.resolution,
        "scaling_mode": plan.scaling_mode,
        "base_sha256": (candidate_result or {}).get("base_sha256"),
        "output_sha256": (candidate_result or {}).get("output_sha256"),
        "patch_count": (candidate_result or {}).get("patch_count"),
        "wrapper_dll_sha256": result["wrapper_dll_sha256"],
    }
    plan.manifest_path.write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    result["manifest"] = "written"
    return result


def launch_game(
    plan: CandidatePlan,
    *,
    confirmed: bool,
    popen: Callable[..., Any] | None = None,
) -> Any:
    if confirmed is not True:
        raise PermissionError(
            "launch_game requires confirmed=True from an explicit user action "
            "(the GUI Play button or the CLI --launch --yes-launch double flag)."
        )
    assert_plan_paths(plan)
    if not plan.candidate_exe.is_file():
        raise LauncherError(f"Candidate not built yet: {plan.candidate_exe}")
    if not plan.wrapper_target.is_file():
        raise LauncherError(
            f"Wrapper {WRAPPER_DLL_NAME} is not deployed next to the candidate. "
            f"Copy your DirectDraw wrapper {WRAPPER_DLL_NAME} into "
            f"{plan.clash_dir} and retry; the launcher never ships DLLs."
        )
    starter = popen if popen is not None else subprocess.Popen
    return starter([str(plan.candidate_exe)], cwd=str(plan.clash_dir))


def clean_candidate_dir(plan: CandidatePlan) -> list[str]:
    assert_plan_paths(plan)
    removed: list[str] = []
    if plan.candidate_dir.is_dir():
        for child in sorted(plan.candidate_dir.iterdir()):
            removed.append(str(child))
        shutil.rmtree(plan.candidate_dir)
    return removed
