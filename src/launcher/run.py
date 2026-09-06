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
import framed
import ini as ini_mod  # noqa: E402
import presets  # noqa: E402
import settings as settings_mod  # noqa: E402
from src.display_plan import PresentationTransform


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--describe-plan", action="store_true", help="inspect a display plan without needing game files")
    parser.add_argument("--list-resolutions", action="store_true", help="list recipe eligibility and profile-scoped status")
    parser.add_argument("--map-size", nargs=2, type=int, metavar=("WIDTH", "HEIGHT"), help="world tile dimensions for inspection only")
    parser.add_argument("--client-size", nargs=2, type=int, metavar=("WIDTH", "HEIGHT"), help="hypothetical client pixels for inspection only")
    parser.add_argument("--profile", choices=("classic", "framed"), default="classic")
    parser.add_argument("--prepare", action="store_true", help="build and deploy without starting the game")
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
    args = parser.parse_args(argv)
    if args.prepare and (args.launch or args.dry_run or args.gui_selftest):
        parser.error("--prepare cannot be combined with --launch, --dry-run, or --gui-selftest")
    if (args.describe_plan or args.list_resolutions) and sum(bool(value) for value in
            (args.describe_plan, args.list_resolutions, args.dry_run, args.prepare, args.launch, args.gui_selftest)) != 1:
        parser.error("Inspection modes cannot be combined with other modes.")
    if (args.map_size or args.client_size) and not args.describe_plan:
        parser.error("--map-size and --client-size require --describe-plan; they do not change a live game.")
    return args


def build_plan(args: argparse.Namespace) -> core.CandidatePlan:
    saved = settings_mod.load_settings()
    backend = framed if args.profile == "framed" else core
    return backend.plan_candidate(
        stage=args.stage,
        resolution=args.resolution or saved["last_resolution"],
        scaling_mode=args.scaling or saved["scaling_mode"],
        clash_dir=args.clash_dir or Path(saved["clash_dir"]),
        candidates_root=args.candidates_root or Path(saved["candidates_root"]),
    )


def inspect_display(args: argparse.Namespace) -> int:
    manifest = presets.load_manifest()
    if args.list_resolutions:
        resolutions = [presets.resolution_info(option.key, renderer=args.profile, stage=args.stage,
                        scaling_mode=args.scaling or ini_mod.DEFAULT_SCALING_MODE, manifest=manifest)
                       for option in presets.load_options(manifest, args.profile)]
        payload = {"schema": 1, "profile": args.profile, "default": presets.default_key(manifest, args.profile),
                   "resolutions": resolutions, "game_runtime_executed": False}
        if args.profile == "framed":
            payload["source_preflight"] = framed.source_status()
        print(json.dumps(payload, indent=2))
        return 0 if payload.get("source_preflight", {"passed": True})["passed"] else 1
    plan = build_plan(args)
    display = core.display_for_plan(plan)
    payload = {"schema": 1, "inspection_only": True, "plan": plan.to_dict(),
               "compatibility": presets.resolution_info(plan.resolution, renderer=args.profile,
                    stage=plan.stage, scaling_mode=plan.scaling_mode, manifest=manifest),
               "game_runtime_executed": False}
    compatible = True
    if args.profile == "framed":
        payload["source_preflight"] = framed.source_status()
        compatible = payload["source_preflight"]["passed"]
    if args.map_size:
        world = display.world_view(*args.map_size)
        payload["world_plan"] = world.to_dict()
        compatible = compatible and world.native_full_loop_safe
        if not world.native_full_loop_safe:
            payload["blocked_reason"] = "The current native full renderer cannot admit this world/viewport combination."
    if args.client_size:
        transform = PresentationTransform.integer_fit(display.width, display.height, *args.client_size)
        payload["presentation_plan"] = {"requested_client_size": args.client_size,
            "content_rectangle": [transform.left, transform.top, transform.width, transform.height],
            "rectangle_format": "left,top,width,height", "observed_runtime_geometry": False}
    print(json.dumps(payload, indent=2))
    return 0 if compatible else 1


def _main(args: argparse.Namespace) -> int:
    backend = framed if args.profile == "framed" else core

    if args.describe_plan or args.list_resolutions:
        return inspect_display(args)

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
        payload["profile"] = args.profile
        if args.profile == "framed":
            payload["source_preflight"] = framed.source_status()
            payload["warning"] = framed.WARNING
        print(json.dumps(payload, indent=2))
        return 0 if report.ready_to_patch and payload.get("source_preflight", {"passed": True})["passed"] else 1

    if args.launch or args.prepare:
        if args.launch and not args.yes_launch:
            print(
                "--launch starts a visible game process; pass --yes-launch as "
                "the second explicit confirmation."
            )
            return 2
        plan = build_plan(args)
        result = backend.ensure_candidate(plan, progress=print)
        deploy = backend.deploy_runtime_files(plan, result, progress=print)
        if args.prepare:
            print(json.dumps({"prepared": True, "runtime_deployed": deploy["wrapper"] == "copied",
                              "profile": args.profile, "plan": plan.to_dict(), "candidate": result,
                              "game_runtime_executed": False}, indent=2))
            return 0
        if deploy["wrapper"] != "copied":
            print(
                f"Launch blocked: {core.WRAPPER_DLL_NAME} missing in "
                f"{plan.clash_dir}. The launcher never ships DLLs."
            )
            return 1
        if backend is framed:
            framed.verify_launch(plan)
        process = core.launch_game(plan, confirmed=True)
        print(f"Launched PID {process.pid}: {plan.candidate_exe}")
        return 0

    try:
        import gui
    except ImportError as exc:
        print(f"Tk is not available in this Python: {exc}")
        print("Install a python.org Python 3.10+ build with Tk support.")
        return 1
    return gui.start_gui(initial_profile=args.profile)


def main(argv: list[str] | None = None) -> int:
    try:
        return _main(parse_args(argv))
    except (core.LauncherError, core.DisplayPlanError, presets.ManifestError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
