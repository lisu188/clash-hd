"""Reconstruct the exact widgets-v1 bundle without running or accepting a game.

The returned ancestors are explicitly named source metadata, not alternative
candidate identities. No logs or predecessor markers are projected or relabeled.
Only load_context authenticates a bundle; parsing JSON alone confers no trust.
The fifteen-section recipe is rebuilt in full; no older consumer is changed.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path, PurePosixPath
import re

import build_framed_modal_widgets_candidate as builder

ROOT = Path(__file__).resolve().parents[1]
ORIGINAL_PATH = Path('C:/Clash/clash95.exe')
ORIGINAL_SHA256 = '500055d77d03d514e8d3168506bd10f67cd8569bcc450604ff8192f46cdaf3ae'
STAGE = ('gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-'
         'presentbounds-minimapright-dynvswitch-completehd-modalwidgets-validation')
REVISION = 'owned_modal_widget_bounds_v1'
SCHEMA = 'clash95_framed_modal_widgets_candidate_v1'
RESOLUTIONS = ('800x600', '1024x768', '1280x720', '1280x960', '1920x1080', '802x602')
FROZEN_TEXT_SOURCES = {
    'src/patcher/framed_modal_primary_text.py': '8c280d5019261c286078cefcd714d3c47ad27f36640c08521a9d9f45e95bb73c',
    'src/patcher/pe_modal_primary_text_extension.py': '178d6849acf65056d6be6fffca927d4c06f19e36eaca2b399dc844fc95356231',
    'tools/build_framed_modal_primary_text_candidate.py': 'c71ed8c370a3a577d1709ddf8a22d97275c64f16bb7c43688fcd7376982bca9a',
}
FROZEN_WIDGET_SOURCES = {
    'src/patcher/framed_modal_widget_bounds.py': '1c248c1009f9db443ab056f57ab5bcf245bb8588598943ee751d0d13d94913cc',
    'tools/build_framed_modal_widgets_candidate.py': '2ff2b1923f4220de862e9dac46f5238db3954122c5e451e8e2a15408fd041ba6',
}
FROZEN_SOURCES = FROZEN_TEXT_SOURCES | FROZEN_WIDGET_SOURCES
# The widget predecessor imports these frozen constants while reconstructing.
# This executable dependency is separate from the builder's 36-file recipe map.
AUTHENTICATION_SOURCES = {
    'tools/modal_primary_text_context.py': 'd76367fb72d88b9df7aae9810c5f3f4edd29378892354649dbdec5dda1cd9c85',
}
RECIPE_SOURCE_PATHS = frozenset((
    'tools/build_framed_modal_candidate.py',
    'src/patcher/framed_modal_canvas.py',
    'src/patcher/pe_modal_extension.py',
    'src/patcher/pe_extension.py',
    'tools/build_framed_candidate.py',
    'tools/build_partial_tile_candidate.py',
    'src/patcher/patch_clash95_hd.py',
    'src/patcher/partial_tile_clip.py',
    'src/patcher/partial_tile_hooks.py',
    'src/patcher/initial_map_paint.py',
    'src/patcher/framed_viewport.py',
    'src/patcher/framed_recipe.py',
    'src/patcher/four_sided_frame.py',
    'src/patcher/framed_full_paint.py',
    'src/patcher/framed_presentation.py',
    'src/patcher/framed_input.py',
    'tools/partial_tile_trace_probe.py',
    'src/patcher/framed_minimap.py',
    'src/patcher/pe_army_extension.py',
    'src/patcher/framed_army_viewport.py',
    'src/patcher/framed_army_draw.py',
    'src/patcher/framed_army_input.py',
    'src/patcher/framed_army_composition.py',
    'tools/build_framed_army_candidate.py',
    'src/patcher/complete_hd_candidate.py',
    'src/patcher/framed_modal_slots.py',
    'src/patcher/pe_modal_slots_extension.py',
    'tools/build_framed_modal_slots_candidate.py',
    'src/patcher/framed_modal_primary.py',
    'src/patcher/pe_modal_primary_extension.py',
    'tools/build_framed_modal_primary_candidate.py',
    *FROZEN_SOURCES,
))


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_json(value) -> str:
    """Compare JSON types exactly, normalizing only tuple-valued JSON arrays."""
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def parse_manifest(raw: bytes) -> dict:
    """Reject ambiguous keys and non-finite numbers at every nesting level."""
    if type(raw) is not bytes:
        raise ValueError('immutable manifest bytes required')

    def pairs(rows):
        result = {}
        for name, value in rows:
            if name in result:
                raise ValueError('duplicate manifest key: ' + name)
            result[name] = value
        return result

    def constant(value):
        raise ValueError('non-finite manifest number: ' + value)

    declared = json.loads(raw.decode('utf-8-sig'), object_pairs_hook=pairs, parse_constant=constant)
    if type(declared) is not dict:
        raise ValueError('manifest must be a JSON object')
    canonical_json(declared)  # Also rejects overflowed numeric literals (1e999).
    return declared


@dataclass(frozen=True)
class _Snapshot:
    path: Path
    data: bytes
    stamp: tuple


def _stamp(stat):
    return (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns)


def _snapshot(path: Path) -> _Snapshot:
    resolved = path.resolve(strict=True)
    before = _stamp(resolved.stat())
    data = resolved.read_bytes()
    after = _stamp(resolved.stat())
    if before != after or path.resolve(strict=True) != resolved or len(data) != after[2]:
        raise ValueError('file changed while reading: ' + str(path))
    return _Snapshot(resolved, data, after)


def _external(path: Path) -> None:
    root = ROOT.resolve()
    for location in (path.absolute(), path.resolve()):
        if location.is_relative_to(root):
            raise ValueError('candidate bundle must be outside the active checkout')
        if location == ORIGINAL_PATH.resolve():
            raise ValueError('candidate bundle must not alias the original executable')
    if path.exists() and ORIGINAL_PATH.exists() and path.samefile(ORIGINAL_PATH):
        raise ValueError('candidate bundle must not alias the original executable')


def _source_paths(sources) -> dict[str, Path]:
    if type(sources) is not dict or not sources:
        raise ValueError('complete source hash map required')
    paths = {}
    root = ROOT.resolve()
    for name, digest in sources.items():
        if (type(name) is not str or not re.fullmatch(r'(?:src/patcher|tools)/(?:[a-z0-9_]+/)*[a-z0-9_]+\.py', name)
                or PurePosixPath(name).as_posix() != name):
            raise ValueError('source path must be canonical repo-relative POSIX Python path')
        if type(digest) is not str or re.fullmatch(r'[0-9a-f]{64}', digest) is None:
            raise ValueError('source SHA-256 required: ' + name)
        paths[name] = root.joinpath(*PurePosixPath(name).parts)
    # Validate every lexical path before any source-file read or resolution.
    if set(sources) != RECIPE_SOURCE_PATHS:
        raise ValueError('complete recipe source path set differs: '
                         f'missing={sorted(RECIPE_SOURCE_PATHS - sources.keys())}; '
                         f'extra={sorted(sources.keys() - RECIPE_SOURCE_PATHS)}')
    for name, expected in FROZEN_SOURCES.items():
        if sources.get(name) != expected:
            raise ValueError('frozen widget/text source identity differs: ' + name)
    for name, path in paths.items():
        if path.resolve(strict=True) != path:
            raise ValueError('source path aliases a different location: ' + name)
    return paths


def _source_snapshots(sources, paths) -> dict[str, _Snapshot]:
    result = {name: _snapshot(path) for name, path in paths.items()}
    identities = set()
    for name, snapshot in result.items():
        if sha(snapshot.data) != sources[name]:
            raise ValueError('declared source hash differs from current bytes: ' + name)
        identity = snapshot.stamp[:2]
        if identity in identities:
            raise ValueError('source files alias one file identity: ' + name)
        identities.add(identity)
    return result


def _authentication_snapshots() -> dict[str, _Snapshot]:
    paths = {name: ROOT.resolve().joinpath(*PurePosixPath(name).parts)
             for name in AUTHENTICATION_SOURCES}
    for name, path in paths.items():
        if path.resolve(strict=True) != path:
            raise ValueError('authentication source aliases a different location: ' + name)
    return _source_snapshots(AUTHENTICATION_SOURCES, paths)


def _identity(manifest, original, candidate, probe):
    if (manifest.get('schema') != SCHEMA or manifest.get('stage') != STAGE
            or manifest.get('recipe_revision') != REVISION):
        raise ValueError('exact widgets-v1 manifest schema/stage/revision required')
    if type(manifest.get('resolution')) is not str or manifest['resolution'] not in RESOLUTIONS:
        raise ValueError('exact widgets-v1 fixture resolution required')
    if manifest.get('original_sha256') != sha(original):
        raise ValueError('manifest original identity differs')
    if manifest.get('candidate_sha256') != sha(candidate) or manifest.get('output_sha256') != sha(candidate):
        raise ValueError('manifest candidate identity differs')
    if manifest.get('probe_sha256') != sha(probe):
        raise ValueError('manifest sibling probe identity differs')
    text = manifest.get('base_candidate')
    primary = text.get('base_candidate') if type(text) is dict else None
    slots = primary.get('base_candidate') if type(primary) is dict else None
    complete = slots.get('base_candidate') if type(slots) is dict else None
    parent = manifest
    for child, suffix, revision in (
            (text, '-modalprimarytext-validation', 'owned_modal_primary_text_v1'),
            (primary, '-modalprimary-validation', 'owned_modal_primary_v1'),
            (slots, '-modalslots-validation', 'owned_barracks_dirty_slots_v1'),
            (complete, '-validation', 'complete_hd_v1')):
        expected_stage = STAGE.removesuffix('-modalwidgets-validation') + suffix
        if (type(child) is not dict or child.get('stage') != expected_stage
                or child.get('recipe_revision') != revision
                or child.get('resolution') != manifest['resolution']
                or parent.get('base_stage') != child['stage']
                or parent.get('base_candidate_sha256') != child.get('candidate_sha256')
                or parent.get('input_sha256') != child.get('candidate_sha256')):
            raise ValueError('widget candidate predecessor chain differs')
        parent = child
    try:
        owner = complete['predecessor']['base_candidate']
        if (type(owner) is not dict or owner['state_va'] != manifest['modal_state_va']
                or canonical_json(owner['modal_entry_vas']) != canonical_json(manifest['modal_entry_vas'])):
            raise ValueError('widget inherited owner context differs')
    except (KeyError, TypeError) as error:
        raise ValueError('widget inherited owner context missing') from error
    return text, primary, slots, owner


def load_context(original: bytes, candidate: bytes, manifest_path: Path) -> dict:
    """Authenticate an external bundle by one exact current-source rebuild.

    No caller-supplied context, source override, builder callback or acceptance
    switch is supported. File content and identity are checked before and after
    reconstruction; a later consumer must repeat this check for its own run.
    """
    if type(original) is not bytes or type(candidate) is not bytes:
        raise ValueError('immutable original and candidate bytes required')
    if sha(original) != ORIGINAL_SHA256:
        raise ValueError('original executable SHA-256 differs')
    path = Path(manifest_path).absolute()
    if not path.name.endswith('.candidate.json'):
        raise ValueError('widget manifest must have .candidate.json suffix')
    stem = path.name.removesuffix('.candidate.json')
    if not stem:
        raise ValueError('widget bundle requires a named candidate')
    executable, command = path.with_name(stem + '.exe'), path.with_name(stem + '.cdb')
    paths = (path, executable, command)
    for item in paths:
        _external(item)
    files = tuple(_snapshot(item) for item in paths)
    if len({item.stamp[:2] for item in files}) != 3:
        raise ValueError('candidate bundle files alias one file identity')
    raw, sibling, probe_raw = (item.data for item in files)
    if sibling != candidate:
        raise ValueError('manifest sibling executable differs from supplied candidate')
    declared = parse_manifest(raw)
    _identity(declared, original, candidate, probe_raw)
    sources = declared.get('source_hashes')
    source_paths = _source_paths(sources)
    before = _source_snapshots(sources, source_paths)
    dependencies = _authentication_snapshots()
    reader = _snapshot(Path(__file__))
    image, rebuilt, probe = builder.build_candidate(original, declared['resolution'])
    if type(image) is not bytes or type(probe) is not str or image != candidate or probe.encode('utf-8') != probe_raw:
        raise ValueError('candidate/probe differ from exact frozen widget-source rebuild')
    rebuilt_json = canonical_json(rebuilt)
    if canonical_json(declared) != rebuilt_json:
        raise ValueError('manifest differs from exact typed source rebuild')
    manifest = parse_manifest(rebuilt_json.encode('utf-8'))
    text, primary, slots, owner = _identity(manifest, original, candidate, probe_raw)
    if (_source_snapshots(sources, source_paths) != before
            or _authentication_snapshots() != dependencies or _snapshot(Path(__file__)) != reader):
        raise ValueError('context or recipe source changed during reconstruction')
    for item, saved in zip(paths, files):
        _external(item)
        if _snapshot(item) != saved:
            raise ValueError('candidate bundle changed during reconstruction: ' + str(item))
    return dict(
        schema='clash95_modal_widgets_context_v1', stage=STAGE, recipe_revision=REVISION,
        resolution=manifest['resolution'], original_sha256=sha(original), candidate_sha256=sha(candidate),
        manifest=manifest, manifest_path=str(files[0].path), manifest_sha256=sha(raw),
        manifest_canonical_sha256=sha(rebuilt_json.encode('utf-8')),
        executable_path=str(files[1].path), probe_path=str(files[2].path), probe=probe, probe_sha256=sha(probe_raw),
        source_hashes=dict(sources), authentication_source_hashes=dict(AUTHENTICATION_SOURCES),
        context_source_sha256=sha(reader.data),
        text_context=parse_manifest(canonical_json(text).encode('utf-8')),
        primary_context=parse_manifest(canonical_json(primary).encode('utf-8')),
        slots_context=parse_manifest(canonical_json(slots).encode('utf-8')),
        owner_context=parse_manifest(canonical_json(owner).encode('utf-8')),
    )
