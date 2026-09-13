"""Exact sidecar/rebuild context for the separate slots diagnostic stage."""
from pathlib import Path
import json

import build_framed_modal_slots_candidate as builder


def load_context(original: bytes,candidate: bytes,manifest_path: Path):
    path=Path(manifest_path).resolve()
    if not path.name.endswith('.candidate.json'):
        raise ValueError('slots candidate manifest must have .candidate.json suffix')
    raw=path.read_bytes();declared=json.loads(raw)
    if not isinstance(declared,dict) or declared.get('stage')!=builder.STAGE or declared.get('recipe_revision')!=builder.REVISION:
        raise ValueError('exact slots manifest stage/revision required')
    image,manifest,probe=builder.build_candidate(original,declared.get('resolution'))
    if candidate!=image or declared!=manifest:
        raise ValueError('slots candidate or manifest differs from exact current source rebuild')
    stem=path.name.removesuffix('.candidate.json')
    executable=path.with_name(stem+'.exe');command=path.with_name(stem+'.cdb')
    if executable.read_bytes()!=image or command.read_bytes()!=probe.encode('utf-8'):
        raise ValueError('slots manifest sibling executable/probe bytes differ')
    if path.read_bytes()!=raw:
        raise ValueError('slots manifest changed during reconstruction')
    return dict(manifest=manifest,probe=probe,manifest_path=str(path),manifest_sha256=builder.sha(raw),
                executable_path=str(executable),candidate_sha256=builder.sha(candidate))
