#!/usr/bin/env python3
"""Entry point for the Clash95 HD launcher.

Starts the Tkinter GUI by default. ``--dry-run`` prints the environment
report and candidate plan as JSON without writing anything. A headless
launch needs the explicit double flag ``--launch --yes-launch``; that is the
CLI equivalent of the GUI Play button and is the only non-GUI path that
starts the game.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import bootstrap

bootstrap.ensure_repo_paths()

import core  # noqa: E402
import ini as ini_mod  # noqa: E402
import presets  # noqa: E402
import settings as settings_mod  # noqa: E402


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--resolution", default=None)
    parser.add_argument("--scaling", default=None)
    parser.add_argument("--stage", default=None)
    parser.add_argument("--clash-dir", type=Path, default=None)
    parser.add_argument("--candidates-root", type=Path, default=None)
    parser.add_argument(
        "--launch",
        action="store_true",
        help="build, deploy, and start the game (requires --yes-launch)",
    )
    parser.add_argument(
        "--yes-launch",
        action="store_true",
        help="second explicit confirmation required by --launch",
    )
    parser.add_argument("--gui-selftest", action="store_true")
    return parser.parse_args(argv)


def build_plan(args: argparse.Namespace) -> core.CandidatePlan:
    saved = settings_mod.load_settings()
    return core.plan_candidate(
        stage=args.stage,
        resolution=args.resolution or saved["last_resolution"],
        scaling_mode=args.scaling or saved["scaling_mode"],
        clash_dir=args.clash_dir or Path(saved["clash_dir"]),
        candidates_root=args.candidates_root or Path(saved["candidates_root"]),
    )


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    if args.gui_selftest:
        try:
            import gui
        except ImportError as exc:
            print(f"Tk is not available in this Python: {exc}")
            print("Install a python.org Python 3.10+ build with Tk support.")
            return 1
        print(f"gui-selftest: {gui.widget_selftest()}")
        return 0

    if args.dry_run:
        plan = build_plan(args)
        report = core.check_environment(
            clash_dir=plan.clash_dir, candidates_root=plan.candidates_root
        )
        payload = {
            "dry_run": True,
            "launcher_version": core.LAUNCHER_VERSION,
            "environment": report.to_dict(),
            "plan": plan.to_dict(),
            "launch_policy": core.LAUNCH_POLICY,
            "write_policy": core.WRITE_POLICY,
        }
        print(json.dumps(payload, indent=2))
        return 0 if report.ready_to_patch else 1

    if args.launch:
        if not args.yes_launch:
            print(
                "--launch starts a visible game process; pass --yes-launch as "
                "the second explicit confirmation."
            )
            return 2
        plan = build_plan(args)
        result = core.ensure_candidate(plan, progress=print)
        deploy = core.deploy_runtime_files(plan, result, progress=print)
        if deploy["wrapper"] != "copied":
            print(
                f"Launch blocked: {core.WRAPPER_DLL_NAME} missing in "
                f"{plan.clash_dir}. The launcher never ships DLLs."
            )
            return 1
        process = core.launch_game(plan, confirmed=True)
        print(f"Launched PID {process.pid}: {plan.candidate_exe}")
        return 0

    try:
        import gui
    except ImportError as exc:
        print(f"Tk is not available in this Python: {exc}")
        print("Install a python.org Python 3.10+ build with Tk support.")
        return 1
    return gui.start_gui()


if __name__ == "__main__":
    raise SystemExit(main())
