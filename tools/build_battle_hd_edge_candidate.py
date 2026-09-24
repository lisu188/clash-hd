"""Build a new expanded-battle edge-controls bundle without launching Clash."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.patcher import battle_hd_edge_controls as builder


def checked_output(path):
    path = Path(path)
    if not path.is_absolute() or path.suffix.lower() != '.exe':
        raise ValueError('an absolute .exe destination is required')
    resolved = path.resolve()
    if (not resolved.is_relative_to(Path('C:/ClashTests').resolve())
            or resolved.is_relative_to(ROOT.resolve()) or resolved == Path('C:/Clash/clash95.exe').resolve()):
        raise ValueError('output must be outside the checkout under C:/ClashTests')
    return resolved


def write_candidate(original, output, resolution=builder.RESOLUTION):
    target = checked_output(output)
    paths = (target, target.with_suffix('.candidate.json'), target.with_suffix('.cdb'))
    if any(path.exists() for path in paths):
        raise FileExistsError('bundle member already exists; choose a fresh destination')
    image, metadata, probe = builder.build_candidate(Path(original).read_bytes(), resolution)
    metadata['source_hashes']['tools/build_battle_hd_edge_candidate.py'] = builder.sha(Path(__file__).read_bytes())
    payloads = (image, (json.dumps(metadata, indent=2) + '\n').encode(), probe.encode())
    target.parent.mkdir(parents=True, exist_ok=True)
    for path, payload in zip(paths, payloads):
        with path.open('xb') as stream:
            stream.write(payload)
    return metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--original', type=Path, required=True)
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
    print(json.dumps({name: metadata[name] for name in ('stage', 'resolution', 'candidate_sha256', 'runtime_executed', 'promotion_ready')}))


if __name__ == '__main__':
    main()
