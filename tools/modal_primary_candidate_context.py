"""Exact reconstruction of the owned-modal-primary bundle; no recipe projection."""
from pathlib import Path
import json
import build_framed_modal_primary_candidate as builder


def strict_json_object(raw: bytes) -> dict:
    """Decode one unambiguous object without discarding duplicate key values."""
    if type(raw) is not bytes:
        raise ValueError('immutable JSON bytes required')
    def pairs(rows):
        result = {}
        for name, value in rows:
            if name in result:
                raise ValueError('duplicate JSON key: ' + name)
            result[name] = value
        return result
    def constant(value):
        raise ValueError('non-finite JSON number: ' + value)
    try:
        value = json.loads(raw.decode('utf-8-sig'), object_pairs_hook=pairs, parse_constant=constant)
        if type(value) is not dict:
            raise ValueError('JSON root must be an object')
        json.dumps(value, allow_nan=False)  # Reject overflowing literals such as 1e999, too.
    except RecursionError as error:
        raise ValueError('JSON nesting exceeds supported depth') from error
    return value


def load_context(original: bytes, candidate: bytes, manifest_path: Path):
    path = Path(manifest_path).resolve()
    if not path.name.endswith('.candidate.json'):
        raise ValueError('primary candidate manifest must have .candidate.json suffix')
    raw = path.read_bytes()
    declared = strict_json_object(raw)
    if (not isinstance(declared, dict) or declared.get('schema') != 'clash95_framed_modal_primary_candidate_v1'
            or declared.get('stage') != builder.STAGE or declared.get('recipe_revision') != builder.REVISION):
        raise ValueError('exact primary manifest schema/stage/revision required')
    image, rebuilt, probe = builder.build_candidate(original, declared.get('resolution'))
    # A sidecar is JSON: tuple spans in the builder's in-memory metadata are
    # serialized as arrays. Compare every JSON value, never a recipe projection.
    manifest = json.loads(json.dumps(rebuilt, allow_nan=False))
    if (candidate != image or json.dumps(declared,sort_keys=True,separators=(',',':'),allow_nan=False)
            != json.dumps(manifest,sort_keys=True,separators=(',',':'),allow_nan=False)):
        raise ValueError('primary candidate or manifest differs from exact current source rebuild')
    stem = path.name.removesuffix('.candidate.json')
    executable, command = path.with_name(stem + '.exe'), path.with_name(stem + '.cdb')
    if executable.read_bytes() != image or command.read_bytes() != probe.encode('utf-8'):
        raise ValueError('primary manifest sibling executable/probe bytes differ')
    if path.read_bytes() != raw:
        raise ValueError('primary manifest changed during reconstruction')
    return dict(manifest=manifest, probe=probe, manifest_path=str(path), manifest_sha256=builder.sha(raw),
                executable_path=str(executable), candidate_sha256=builder.sha(candidate),
                probe_path=str(command), probe_sha256=builder.sha(probe.encode('utf-8')))
