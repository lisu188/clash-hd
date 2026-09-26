#!/usr/bin/env python3
"""Build the distinct native-caller matrix successor; never launch the game."""
from pathlib import Path
import argparse
import json
import os
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'tools')]
from src.patcher import ordinary_castle_entry_matrix as builder
from src.patcher import complete_hd_candidate as complete


def checked_output(output):
    raw = Path(output).absolute()
    if any(path.is_symlink() or getattr(path, 'is_junction', lambda: False)()
           for path in (raw, *raw.parents)):
        raise ValueError('candidate outputs must not follow symbolic links or junctions')
    target = raw.resolve()
    permitted = Path('C:/ClashTests').resolve()
    if (os.name != 'nt' or not target.is_relative_to(permitted) or target.suffix.lower() != '.exe'
            or target.is_relative_to(ROOT.resolve())):
        raise ValueError('a new Windows .exe under C:/ClashTests outside the repository is required')
    return target


def write_candidate(original, output, profile, resolution):
    target = checked_output(output)
    paths = (target, target.with_suffix('.candidate.json'), target.with_suffix('.cdb'))
    if any(path.exists() or path.is_symlink() for path in paths):
        raise FileExistsError('bundle member already exists; choose a fresh destination')
    own_before = builder.sha(Path(__file__).read_bytes())
    image, metadata, probe = builder.build_candidate(Path(original).read_bytes(), profile, resolution)
    if own_before != builder.sha(Path(__file__).read_bytes()):
        raise ValueError('CLI source changed during build')
    metadata['source_hashes']['tools/build_ordinary_castle_entry_matrix_candidate.py'] = own_before
    target.parent.mkdir(parents=True, exist_ok=True)
    if checked_output(target) != target:
        raise ValueError('output path changed during build')
    complete._write_bundle(paths, (image, (json.dumps(metadata, indent=2)+'\n').encode(), probe.encode()))
    return metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--original', required=True, type=Path)
    parser.add_argument('--profile', required=True, choices=builder.PROFILES)
    parser.add_argument('--resolution', required=True, choices=builder.RESOLUTIONS)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--preflight', action='store_true')
    args = parser.parse_args()
    if args.preflight:
        if args.output: parser.error('preflight accepts no output')
        _, metadata, _ = builder.build_candidate(args.original.read_bytes(), args.profile, args.resolution)
    else:
        if args.output is None: parser.error('output required unless preflight')
        metadata = write_candidate(args.original, args.output, args.profile, args.resolution)
    print(json.dumps({key: metadata[key] for key in ('stage', 'profile', 'resolution', 'candidate_sha256', 'runtime_executed', 'promotion_ready')}))


if __name__ == '__main__': main()
