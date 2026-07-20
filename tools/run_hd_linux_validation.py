#!/usr/bin/env python3
"""Drive the HD manual-DirectInput validation on Linux under Xvfb + wine.

This is the "run the game here" path chosen for HD completion. It attempts to
reproduce, on a Linux host, the approved visible runtime the completion sequence
needs (``reports/hd_completion_certainty.md``): patch the supplied
``clash95.exe`` for each required stage, prepare the isolated save fixtures,
launch the candidate under ``wine`` on a headless ``Xvfb`` display, drive real
DirectInput mouse moves/held-clicks with ``xdotool``, capture frames, and emit a
run manifest that ``tools/assemble_manual_directinput_proof.py`` turns into the
proof manifest.

Two safety properties are preserved from the Windows harnesses:

* **Dry-run by default.** With ``--dry-run`` (the default) it only *plans* -- it
  never installs packages, patches, or launches anything, and needs no game
  binary. This is what runs in CI / on this Linux container.
* **Explicit approval gate.** A real run requires ``--allow-visible-runtime``
  *and* a ``--source-exe`` that hashes to the expected base SHA. Without both it
  refuses to launch, mirroring the ``-AllowVisibleRuntime`` guard in
  ``scripts/smoke/run_clash_windows_sandbox.ps1``.

Fidelity caveat (documented in ``docs/hd/HD_VM_VALIDATION_RUNBOOK.md``): wine may
not reproduce the Windows DirectDraw/DirectInput click-consumption path exactly.
If a target cannot be observed faithfully here, fall back to the Windows Sandbox
driver and assemble the proof from that run instead.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shlex
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import manual_directinput_checklist as checklist
import manual_directinput_run_plan as run_plan


EXPECTED_BASE_SHA256 = "500055d77d03d514e8d3168506bd10f67cd8569bcc450604ff8192f46cdaf3ae"

# wine presents its prefix as C:\; the sanctioned test root maps under it.
WINE_TESTS_ROOT = "C:\\ClashTests\\linux-wine"
RUNTIME_POLICY = (
    "Linux Xvfb+wine visible-runtime driver; dry-run plans only and launches "
    "nothing without --allow-visible-runtime plus a SHA-verified source exe"
)
APPROVAL_POLICY = (
    "a real run requires explicit user approval recorded in --approval-record, "
    "the --allow-visible-runtime switch, and a --source-exe matching the base SHA"
)

# Stage each required target is validated on (authoritative from the checklist).
_STAGE_BY_ID = {item["id"]: item["stage"] for item in checklist.CHECKLIST_ITEMS}

# apt packages the real run needs. On Ubuntu 24.04 the i386 wine32 chain can be
# unavailable behind restricted mirrors; wine 9.0's new WoW64 runs the 32-bit
# clash95.exe from the amd64 `wine` package alone (verified: syswow64 present),
# so i386 packages are intentionally not required here.
REQUIRED_APT_PACKAGES = ("wine", "xvfb", "xdotool", "x11-utils", "ffmpeg")


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _candidate_name(stage: str) -> str:
    # Short, stable candidate filename per stage.
    tail = stage.split("dynvswitch", 1)[-1].strip("-") or "stable"
    return f"clash95_hd_{tail or 'stable'}.exe"


def build_plan(args: argparse.Namespace) -> dict[str, Any]:
    repo_root = Path(__file__).resolve().parents[1]
    run_dir = Path(args.run_dir)
    prefix = Path(args.wine_prefix)
    failures: list[str] = []

    source_exe = Path(args.source_exe) if args.source_exe else None
    source_present = bool(source_exe and source_exe.is_file())
    source_sha256: str | None = None
    if source_present:
        source_sha256 = sha256_of(source_exe)  # type: ignore[arg-type]
        if not args.allow_unknown_sha and source_sha256 != EXPECTED_BASE_SHA256:
            failures.append(
                f"source exe SHA-256 {source_sha256} does not match the expected base "
                f"{EXPECTED_BASE_SHA256}; pass --allow-unknown-sha only if intentional"
            )

    # Distinct candidate stages across the 5 targets (usually 3).
    stages = sorted({_STAGE_BY_ID[i] for i in checklist.REQUIRED_IDS})
    candidates = {
        stage: {
            "stage": stage,
            "candidate_wine_path": f"{WINE_TESTS_ROOT}\\{_candidate_name(stage)}",
            "candidate_host_path": str(prefix / "drive_c" / "ClashTests" / "linux-wine" / _candidate_name(stage)),
            "patch_command": [
                "python",
                "patch_clash95_hd.py",
                "--input",
                str(source_exe) if source_exe else "<source clash95.exe>",
                "--output",
                str(prefix / "drive_c" / "ClashTests" / "linux-wine" / _candidate_name(stage)),
                "--stage",
                stage,
                "--overwrite",
            ],
        }
        for stage in stages
    }

    spec_by_id = run_plan.COMMAND_SPECS
    targets = []
    for item_id in checklist.REQUIRED_IDS:
        stage = _STAGE_BY_ID[item_id]
        spec = spec_by_id[item_id]
        target_dir = run_dir / item_id
        wine_sh = repo_root / "scripts" / "smoke" / "run_clash_hd_linux_wine.sh"
        launch_command = [
            "bash",
            str(wine_sh),
            "--wine-prefix", str(prefix),
            "--display", args.display,
            "--candidate", candidates[stage]["candidate_wine_path"],
            "--route", str(spec["route"]),
            "--route-points", str(spec["route_points"]),
            "--followup-points", str(spec["followup_points"]),
            "--out-dir", str(target_dir),
            "--click-hold-ms", str(args.click_hold_ms),
            "--click-repeat", str(args.click_repeat),
            "--allow-visible-runtime",
        ]
        target = {
            "id": item_id,
            "title": checklist.CHECKLIST_ITEMS[[i["id"] for i in checklist.CHECKLIST_ITEMS].index(item_id)]["title"],
            "stage": stage,
            "candidate_path": candidates[stage]["candidate_wine_path"],
            "candidate_host_path": candidates[stage]["candidate_host_path"],
            "route": spec["route"],
            "route_points": spec["route_points"],
            "followup_points": spec["followup_points"],
            "notes": spec["notes"],
            "out_dir": str(target_dir),
            "launch_command": " ".join(shlex.quote(part) for part in launch_command),
            # Observation fields are intentionally empty until a real run + human
            # confirmation fills them; the assembler fails closed while they are.
            "observed_result": "",
            "evidence": "",
            "pass_fail_notes": "",
            "no_crash": False,
            "status": "pending",
        }
        # right-bottom needs the addon_flags save fixture prepared first.
        if item_id == "right_bottom_validation_input":
            fixture_dir = prefix / "drive_c" / "ClashTests" / "linux-wine" / "right-bottom-addon-fixture" / "save"
            target["fixture_command"] = " ".join(
                shlex.quote(part)
                for part in [
                    "python",
                    "tools/prepare_addon_flags_fixture.py",
                    "--source-save", args.source_save or "<C:\\Clash\\save\\5.dat via wine>",
                    "--out-dir", str(fixture_dir),
                    "--building-index", str(args.right_bottom_building_index),
                    "--execute",
                ]
            )
            target["fixture_note"] = (
                "set addon_flags bit 0x02 on a player-owned building so the natural "
                "right-bottom action panel draws (no binary patch)"
            )
        targets.append(target)

    if not args.dry_run and not args.allow_visible_runtime:
        failures.append("real run requires --allow-visible-runtime (explicit user approval)")
    if not args.dry_run and not source_present:
        failures.append("real run requires an existing --source-exe (clash95.exe)")
    if not args.dry_run and not str(args.approval_record).strip():
        failures.append("real run requires a non-empty --approval-record")

    return {
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "runner": "linux-wine",
        "runtime_policy": RUNTIME_POLICY,
        "approval_policy": APPROVAL_POLICY,
        "dry_run": bool(args.dry_run),
        "approved_visible_runtime": bool(args.allow_visible_runtime and not args.dry_run),
        "approval_record": args.approval_record,
        "no_stale_processes": bool(args.no_stale_processes),
        "expected_base_sha256": EXPECTED_BASE_SHA256,
        "source_exe": str(source_exe) if source_exe else None,
        "source_present": source_present,
        "source_sha256": source_sha256,
        "wine_prefix": str(prefix),
        "display": args.display,
        "run_dir": str(run_dir),
        "required_apt_packages": list(REQUIRED_APT_PACKAGES),
        "install_command": "sudo apt-get update && sudo apt-get install -y " + " ".join(REQUIRED_APT_PACKAGES),
        "xvfb_command": f"Xvfb {args.display} -screen 0 1024x768x24 &",
        # A representative primary candidate for the proof manifest top level.
        "candidate_path": candidates[_STAGE_BY_ID['stable_menu_load']]["candidate_wine_path"],
        "candidate_stages": candidates,
        "targets": targets,
        "assemble_command": (
            "python tools/assemble_manual_directinput_proof.py --run-manifest "
            f"{run_dir / 'run-manifest.json'} --require-valid"
        ),
        "fidelity_caveat": (
            "wine may not reproduce the Windows DirectDraw/DirectInput click path; "
            "fall back to scripts/smoke/run_clash_hd_full_validation.ps1 on Windows "
            "if a target cannot be observed faithfully"
        ),
        "passed": not failures,
        "failures": failures,
    }


def _read_target_summary(out_dir: str) -> tuple[bool, list[str]]:
    summary_path = Path(out_dir) / "target-summary.json"
    if not summary_path.exists():
        return False, []
    try:
        data = json.loads(summary_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False, []
    return bool(data.get("no_crash")), list(data.get("artifacts") or [])


def execute_plan(
    plan: dict[str, Any],
    *,
    runner: Callable[[list[str]], Any] | None = None,
    cwd: Path | None = None,
) -> dict[str, Any]:
    """Actually run the planned patch/fixture/launch steps.

    ``runner`` is a ``subprocess.run``-style callable returning an object with a
    ``returncode`` (injectable for tests). Failures accumulate and flip
    ``passed`` to False so a real run never silently exits 0 without evidence.
    """
    if runner is None:
        def runner(argv: list[str]) -> subprocess.CompletedProcess[str]:  # type: ignore[misc]
            return subprocess.run(argv, cwd=str(cwd) if cwd else None, check=False)

    steps: list[dict[str, Any]] = []
    failures = list(plan.get("failures", []))

    def _run(name: str, argv: list[str]) -> int:
        rc = getattr(runner(argv), "returncode", 1)
        steps.append({"step": name, "returncode": rc, "command": " ".join(argv)})
        if rc != 0:
            failures.append(f"{name} failed (exit {rc})")
        return rc

    # 1. Build every candidate stage.
    for cand in plan["candidate_stages"].values():
        _run(f"patch:{cand['stage']}", list(cand["patch_command"]))

    # 2. Prepare per-target fixtures (right-bottom addon_flags save).
    for target in plan["targets"]:
        if target.get("fixture_command"):
            _run(f"fixture:{target['id']}", shlex.split(target["fixture_command"]))

    # 3. Launch each target and fold its captured no_crash / artifacts.
    for target in plan["targets"]:
        _run(f"launch:{target['id']}", shlex.split(target["launch_command"]))
        no_crash, artifacts = _read_target_summary(target["out_dir"])
        target["no_crash"] = no_crash
        target["artifacts"] = artifacts

    plan["executed"] = True
    plan["execution_steps"] = steps
    plan["failures"] = failures
    plan["passed"] = not failures
    return plan


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-exe", help="Path to clash95.exe (base SHA verified) for a real run")
    parser.add_argument("--source-save", help="Path to a source save for the right-bottom addon_flags fixture")
    parser.add_argument("--right-bottom-building-index", type=int, default=0)
    parser.add_argument("--wine-prefix", default=str(Path.home() / ".clash-hd-wine"))
    parser.add_argument("--display", default=":99")
    parser.add_argument("--run-dir", default="captures/archive/linux-wine-run")
    parser.add_argument("--click-hold-ms", type=int, default=300)
    parser.add_argument("--click-repeat", type=int, default=2)
    parser.add_argument("--approval-record", default="")
    parser.add_argument("--allow-unknown-sha", action="store_true")
    parser.add_argument("--no-stale-processes", action="store_true", default=True)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--dry-run", dest="dry_run", action="store_true", default=True)
    group.add_argument("--execute", dest="dry_run", action="store_false")
    parser.add_argument("--allow-visible-runtime", action="store_true")
    parser.add_argument("--write-json", type=Path, help="Write the plan/run manifest JSON here")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    plan = build_plan(args)
    repo_root = Path(__file__).resolve().parents[1]

    # Real run: only execute once the preflight (approval + SHA-verified binary)
    # passed. Otherwise leave it as a plan and fail.
    executed = False
    if not plan["dry_run"] and plan["passed"]:
        plan = execute_plan(plan, cwd=repo_root)
        executed = True

    default_manifest = Path(args.run_dir) / "run-manifest.json"
    out_path = args.write_json or default_manifest
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")

    print(f"runner: {plan['runner']}")
    print(f"runtime-policy: {plan['runtime_policy']}")
    print(f"dry-run: {plan['dry_run']}")
    print(f"executed: {executed}")
    print(f"source-present: {plan['source_present']}")
    print(f"target-count: {len(plan['targets'])}")
    print(f"run-manifest: {out_path}")
    print(f"passed: {plan['passed']}")
    if plan["failures"]:
        print("failures:")
        for failure in plan["failures"]:
            print(f"  - {failure}")

    if plan["dry_run"]:
        # Planning only; never launches. Always succeeds so CI can validate shape.
        return 0
    return 0 if plan["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
