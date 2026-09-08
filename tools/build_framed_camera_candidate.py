#!/usr/bin/env python3
"""Build a camera-recovering framed validation candidate; never start the game."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.patcher import framed_camera as camera


def _outputs(original: Path, output: Path, report: Path) -> tuple[Path, Path]:
    paths = (output, report)
    for path in paths:
        if any(p.is_symlink() or getattr(p, "is_junction", lambda: False)()
               for p in (path, *path.parents)):
            raise ValueError("output paths must not follow links")
        if path.exists():
            raise ValueError(f"output already exists: {path}")
    paths = tuple(p.resolve() for p in paths)
    if (paths[0] == paths[1] or paths[0].suffix.lower() != ".exe" or paths[1].suffix.lower() != ".json"
            or any(p == original.resolve() or p.is_relative_to(original.resolve().parent)
                   or p.is_relative_to(ROOT) for p in paths)
            or not all(p.is_relative_to(Path("C:/ClashTests").resolve()) for p in paths)):
        raise ValueError("distinct .exe/.json outputs must be under C:/ClashTests and outside the repository and original game directory")
    return paths


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original", type=Path, required=True)
    parser.add_argument("--resolution", required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--report-json", type=Path)
    parser.add_argument("--preflight", action="store_true")
    args = parser.parse_args(argv)
    if not args.preflight and not (args.output and args.report_json):
        parser.error("--output and --report-json are required unless using --preflight")
    try:
        paths = None if args.preflight else _outputs(args.original, args.output, args.report_json)
        image, report = camera.build_candidate(args.original.read_bytes(), args.resolution)
        if paths is not None:
            _outputs(args.original, args.output, args.report_json)
            for path in paths:
                path.parent.mkdir(parents=True, exist_ok=True)
            report["builder_source_sha256"] = camera.sha(Path(__file__).read_bytes())
            with paths[0].open("xb") as target:
                target.write(image)
            if camera.sha(paths[0].read_bytes()) != report["output_sha256"]:
                raise ValueError("candidate on-disk verification failed")
            with paths[1].open("x", encoding="utf-8", newline="\n") as target:
                json.dump(report, target, indent=2, sort_keys=True)
                target.write("\n")
        print(json.dumps({"stage": camera.STAGE, "resolution": args.resolution,
            "preflight_passed": True, "candidate_sha256": report["output_sha256"],
            "written": paths is not None, "game_runtime_executed": False,
            "parent_probe_reusable": False}, sort_keys=True))
        return 0
    except (ValueError, OSError, ImportError, KeyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
