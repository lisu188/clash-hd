#!/usr/bin/env python3
"""Build an experimental small-world repaint and mouse candidate; never start the game."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.patcher import framed_bounded_input as bounded
from src.patcher import framed_camera as camera
import framed_loaded_probe


def _outputs(original: Path, output: Path, report: Path, probe: Path | None = None) -> tuple[Path, ...]:
    paths = (output, report) if probe is None else (output, report, probe)
    for path in paths:
        if any(p.is_symlink() or getattr(p, "is_junction", lambda: False)()
               for p in (path, *path.parents)):
            raise ValueError("output paths must not follow links")
        if path.exists():
            raise ValueError(f"output already exists: {path}")
    paths = tuple(p.resolve() for p in paths)
    if (len(set(paths)) != len(paths) or paths[0].suffix.lower() != ".exe" or paths[1].suffix.lower() != ".json"
            or (probe is not None and paths[2].suffix.lower() != ".cdb")
            or any(p == original.resolve() or p.is_relative_to(original.resolve().parent)
                   or p.is_relative_to(ROOT) for p in paths)
            or not all(p.is_relative_to(Path("C:/ClashTests").resolve()) for p in paths)):
        raise ValueError("distinct .exe/.json and optional .cdb outputs must be under C:/ClashTests and outside the repository and original game directory")
    return paths


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original", type=Path, required=True)
    parser.add_argument("--resolution", required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--report-json", type=Path)
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--probe-cdb", type=Path, help="write a final-stage loaded-byte verifier, without running CDB")
    args = parser.parse_args(argv)
    if not args.preflight and not (args.output and args.report_json):
        parser.error("--output and --report-json are required unless using --preflight")
    try:
        paths = None if args.preflight else _outputs(args.original, args.output, args.report_json, args.probe_cdb)
        image, report = bounded.build_candidate(args.original.read_bytes(), args.resolution)
        probe_text = None
        if args.probe_cdb is not None:
            probe_text, report["loaded_probe"] = framed_loaded_probe.render_probe(image, report)
        if paths is not None:
            _outputs(args.original, args.output, args.report_json, args.probe_cdb)
            for path in paths:
                path.parent.mkdir(parents=True, exist_ok=True)
            report["builder_source_sha256"] = camera.sha(Path(__file__).read_bytes())
            with paths[0].open("xb") as target:
                target.write(image)
            if camera.sha(paths[0].read_bytes()) != report["output_sha256"]:
                raise ValueError("candidate on-disk verification failed")
            if probe_text is not None:
                with paths[2].open("x", encoding="ascii", newline="\n") as target:
                    target.write(probe_text)
                if camera.sha(paths[2].read_bytes()) != report["loaded_probe"]["probe_sha256"]:
                    raise ValueError("probe on-disk verification failed")
            with paths[1].open("x", encoding="utf-8", newline="\n") as target:
                json.dump(report, target, indent=2, sort_keys=True)
                target.write("\n")
        print(json.dumps({"stage": bounded.STAGE, "resolution": args.resolution,
            "preflight_passed": True, "candidate_sha256": report["output_sha256"],
            "written": paths is not None, "game_runtime_executed": False,
            "parent_probe_reusable": False, "loaded_probe_generated": probe_text is not None}, sort_keys=True))
        return 0
    except (ValueError, OSError, ImportError, KeyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
