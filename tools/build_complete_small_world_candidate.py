#!/usr/bin/env python3
"""Build a distinct small-world matrix successor without launching the game."""
from pathlib import Path
import argparse
import json
import os
import shutil
import stat
import sys

ROOT = Path(__file__).resolve().parents[1]
SOURCE = 'tools/build_complete_small_world_candidate.py'
sys.path[:0] = [str(ROOT), str(ROOT/'tools')]
from src.patcher import complete_small_world_candidate as builder
from src.patcher import complete_hd_candidate as complete


def _plain_path(path: Path) -> Path:
    raw = Path(path).absolute()
    for part in (raw, *raw.parents):
        if part.is_symlink() or getattr(part, 'is_junction', lambda: False)():
            raise ValueError('candidate paths must not follow symbolic links or junctions')
        try:
            if getattr(part.lstat(), 'st_file_attributes', 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT:
                raise ValueError('candidate paths must not follow reparse points')
        except FileNotFoundError:
            pass
    return raw.resolve()


def checked_output(output) -> Path:
    target = _plain_path(Path(output)); permitted = _plain_path(Path('C:/ClashTests'))
    if (os.name != 'nt' or not target.is_relative_to(permitted) or target.suffix.lower() != '.exe'
            or target.is_relative_to(ROOT.resolve())):
        raise ValueError('a new Windows .exe under C:/ClashTests outside the repository is required')
    return target


def _existing_ancestor(path: Path) -> Path:
    for part in (path, *path.parents):
        if part.exists(): return part
    raise ValueError('output volume unavailable')


def disk_preflight(output: Path, payload_bytes: int = 0) -> None:
    """Preserve more than ten percent free on checkout and output volumes."""
    if type(payload_bytes) is not int or payload_bytes < 0:
        raise ValueError('nonnegative aggregate bundle size required')
    for path, needed in ((ROOT, 0), (_existing_ancestor(output), payload_bytes)):
        usage = shutil.disk_usage(path)
        if usage.free*10 <= usage.total or (usage.free-needed)*10 <= usage.total:
            raise ValueError('disk reserve requires more than ten percent free after the complete bundle write')


def _original(path: Path):
    plain = _plain_path(path)
    identity = plain.stat()
    if not stat.S_ISREG(identity.st_mode): raise ValueError('regular original executable required')
    data = plain.read_bytes()
    builder.pe._identity(data, builder.pe.ORIGINAL_SHA256, 'original')
    after = plain.stat()
    if (identity.st_dev, identity.st_ino, identity.st_size, identity.st_mtime_ns) != (
        after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns):
        raise ValueError('original file changed while reading')
    return plain, after, data


def write_candidate(original, output, profile, resolution):
    target = checked_output(output)
    paths = (target, target.with_suffix('.candidate.json'), target.with_suffix('.cdb'))
    if any(path.exists() or path.is_symlink() for path in paths):
        raise FileExistsError('bundle member already exists; choose a fresh destination')
    disk_preflight(target)
    own_before = builder.sha(Path(__file__).read_bytes())
    original_path, identity, original_bytes = _original(Path(original))
    if target == original_path or any(path == original_path for path in paths):
        raise ValueError('output cannot replace the original executable')
    image, metadata, probe = builder.build_candidate(original_bytes, profile, resolution)
    metadata['source_hashes'][SOURCE] = own_before
    payloads = (image, (json.dumps(metadata, indent=2)+'\n').encode('utf-8'), probe.encode('ascii'))
    # Authenticate all sources and the original again before creating directories.
    for name, digest in metadata['source_hashes'].items():
        if builder.sha(builder._source_path(name).read_bytes()) != digest:
            raise ValueError('source changed before bundle write: '+name)
    current_path, current_identity, current_bytes = _original(original_path)
    if current_path != original_path or current_bytes != original_bytes or (
        identity.st_dev, identity.st_ino, identity.st_size, identity.st_mtime_ns) != (
        current_identity.st_dev, current_identity.st_ino, current_identity.st_size, current_identity.st_mtime_ns):
        raise ValueError('original file changed during build')
    disk_preflight(target, sum(map(len, payloads)))
    if checked_output(target) != target or any(path.exists() or path.is_symlink() for path in paths):
        raise ValueError('output path changed during build or bundle member now exists')
    target.parent.mkdir(parents=True, exist_ok=True)
    if checked_output(target) != target: raise ValueError('output path changed before write')
    disk_preflight(target, sum(map(len, payloads)))
    complete._write_bundle(paths, payloads)
    return metadata


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--original', required=True, type=Path)
    parser.add_argument('--profile', required=True, choices=builder.PROFILES)
    parser.add_argument('--resolution', required=True, choices=builder.RESOLUTIONS)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--preflight', action='store_true')
    args = parser.parse_args(argv)
    if args.preflight:
        if args.output: parser.error('preflight accepts no output')
        _, _, original = _original(args.original)
        _, metadata, _ = builder.build_candidate(original, args.profile, args.resolution)
    else:
        if args.output is None: parser.error('output required unless preflight')
        metadata = write_candidate(args.original, args.output, args.profile, args.resolution)
    print(json.dumps({key: metadata[key] for key in ('stage', 'profile', 'resolution', 'candidate_sha256',
                                                   'runtime_executed', 'manual_input_proof', 'promotion_ready')}))


if __name__ == '__main__': main()
