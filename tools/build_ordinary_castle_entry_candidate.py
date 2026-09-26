#!/usr/bin/env python3
"""Build the separate 1024x768 ordinary castle entry candidate; never run it."""
from pathlib import Path
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'tools')]
from src.patcher import ordinary_castle_entry as builder


def checked_output(output):
    target = Path(output).resolve()
    permitted = Path('C:/ClashTests').resolve()
    if (not target.is_relative_to(permitted) or target.suffix.lower() != '.exe'
            or target.is_relative_to(ROOT.resolve())):
        raise ValueError('a new .exe under C:/ClashTests outside the repository is required')
    return target


def write_candidate(original, output, resolution=builder.RESOLUTION):
    target = checked_output(output)
    paths = (target, target.with_suffix('.candidate.json'), target.with_suffix('.cdb'))
    if any(path.exists() for path in paths):
        raise FileExistsError('bundle member already exists; choose a fresh destination')
    image, metadata, probe = builder.build_candidate(Path(original).read_bytes(), resolution)
    metadata['source_hashes']['tools/build_ordinary_castle_entry_candidate.py'] = builder.sha(Path(__file__).read_bytes())
    payloads = (image, (json.dumps(metadata, indent=2)+'\n').encode(), probe.encode())
    target.parent.mkdir(parents=True, exist_ok=True)
    for path, data in zip(paths, payloads):
        with path.open('xb') as stream: stream.write(data)
    return metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--original', required=True, type=Path)
    parser.add_argument('--resolution', choices=[builder.RESOLUTION], default=builder.RESOLUTION)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--preflight', action='store_true')
    args = parser.parse_args()
    if args.preflight:
        if args.output: parser.error('preflight accepts no output')
        _, metadata, _ = builder.build_candidate(args.original.read_bytes(), args.resolution)
    else:
        if args.output is None: parser.error('output is required unless preflight')
        metadata = write_candidate(args.original, args.output, args.resolution)
    print(json.dumps({k: metadata[k] for k in ('stage','resolution','candidate_sha256','runtime_executed','promotion_ready')}))


if __name__ == '__main__': main()
