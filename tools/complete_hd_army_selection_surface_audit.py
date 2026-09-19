#!/usr/bin/env python3
"""Bind a complete-HD hidden selection capture and audit its retained pixels.

Offline only. Reads the actual host summary, commands, source identities, native
assets and five raw observations. No image is written or changed. Portrait
counts, map-unit artwork, ordinary input and final wrapper composition remain
outside this audit, even when the bounded pixel result passes.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import stat
import struct
import sys
import zlib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tools'))
import action_bar_surface_audit as bar
import frame_surface_audit as frame
import cdb_surface_dump_to_png as png
import complete_hd_army_selection_trace as trace
from hd_layout_asset_composition import Sprite, decode_sprite, resource_member
from src.patcher.framed_army_viewport import FramedArmyViewport

HOST_SCHEMA = 'clash95_complete_hd_army_selection_capture_v1'
PLAN_SCHEMA = 'clash95_complete_hd_army_selection_capture_plan_v1'
INFO_SHA = 'ba0747966bd3ff5722a41e6374fd2edc4d817215f79d83bb87cf1c1df3e65dcd'
MARKS_SHA = '026e2d549427163b5b9642a1c92f89c98b65885eec54b36a0e28fee812bc7667'
TYPES = [16, 16, 1, 1, 1, 1, 1, 1]
LABELS = ('before-redraw', 'after-redraw', 'capture-1', 'capture-2', 'capture-3')
FALSE_FLAGS = ('ordinary_input_proof', 'manual_input_proof', 'visible_composition_proof', 'promotion_ready')
LIMITS = [
    'Actual retained indexed software pixels only; this program performs no runtime or capture.',
    'Eight INFO1 portrait bodies use opaque rows 20..48; count text and badge composition are not independently verified.',
    'Exposed MARKS35 backing matches source art; the entire backing rectangle must also survive redraw unchanged.',
    'The map-unit sprite, count-text glyphs, command availability, ordinary input and final wrapper composition are not proved.',
    'Host cleanup is retained evidence checked for identity and consistency; this offline audit cannot observe live process absence.',
    'A bounded source/pixel pass never supplies manual-input proof or stable promotion.',
]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def canonical(value):
    return trace.canonical(value)


def object_pairs(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'duplicate JSON key: ' + key)
        result[key] = value
    return result


def path_value(value):
    require(type(value) is str and bool(value) and '\x00' not in value, 'absolute artifact path required')
    path = Path(value)
    require(path.is_absolute(), 'relative artifact path is forbidden: ' + value)
    # Check lexical ancestors before resolving: resolving first would conceal a
    # junction that aliases one retained snapshot directory to another.
    for component in (path, *path.parents):
        try:
            info = component.lstat()
        except FileNotFoundError:
            continue
        require(not stat.S_ISLNK(info.st_mode) and not (getattr(info, 'st_file_attributes', 0) & 0x400),
                'reparse or symbolic-link artifact path is forbidden: ' + str(component))
    return path.resolve()


class Artifacts:
    """Read each path once, retain provenance, and detect drift before returning."""

    def __init__(self):
        self.data = {}

    def read(self, path, *, expected=None, size=None):
        path = path_value(str(path))
        if path not in self.data:
            self.data[path] = path.read_bytes()
        data = self.data[path]
        if expected is not None:
            require(type(expected) is str and re.fullmatch('[0-9a-f]{64}', expected), 'invalid SHA-256: ' + str(path))
            require(sha(data) == expected, 'artifact SHA-256 differs: ' + str(path))
        if size is not None:
            require(type(size) is int and len(data) == size, 'artifact byte count differs: ' + str(path))
        return data

    def json(self, path):
        value = json.loads(self.read(path).decode('utf-8-sig'), object_pairs_hook=object_pairs)
        canonical(value)
        require(type(value) is dict, 'JSON object required: ' + str(path))
        return value

    def receipt(self, row, *, path=None, size=None):
        require(type(row) is dict, 'artifact receipt must be an object')
        actual = path_value(row['path'])
        if path is not None:
            require(actual == path_value(str(path)), 'artifact belongs to a different capture path: ' + str(actual))
        if 'bytes' in row:
            require(type(row['bytes']) is int and row['bytes'] >= 0, 'receipt bytes must be an integer')
            if size is not None:
                require(row['bytes'] == size, 'receipt byte count differs from expected size')
            size = row['bytes']
        return self.read(actual, expected=row['sha256'], size=size)

    def unchanged(self):
        for path, original in self.data.items():
            require(path.read_bytes() == original, 'artifact changed during audit: ' + str(path))

    def receipts(self):
        return [dict(path=str(path), sha256=sha(data), bytes=len(data)) for path, data in self.data.items()]


def load_assets(minimum, gfx3):
    require(sha(minimum) == bar.RESOURCE_SHA256, 'unsupported minimum.res identity')
    info = resource_member(minimum, 'INFO1.S32')
    marks = resource_member(minimum, 'MARKS.S32')
    require(sha(info) == INFO_SHA and sha(marks) == MARKS_SHA, 'portrait/backing member identity differs')
    portraits = {kind: decode_sprite(info, kind) for kind in set(TYPES)}
    backing = decode_sprite(marks, 35)
    sprites, bar_sha = bar.load_sprites(minimum)
    return dict(frame=frame.load_native_frame(gfx3), action=sprites, portraits=portraits, backing=backing,
                members=dict(info_sha256=sha(info), marks_sha256=sha(marks), action_sha256=bar_sha))


def sprite_shape(sprite, width, height):
    require(isinstance(sprite, Sprite) and (sprite.width, sprite.height) == (width, height)
            and len(sprite.pixels) == width * height
            and all(type(value) is int and 0 <= value <= 255 for value in sprite.pixels),
            'native portrait/backing sprite is not complete opaque indexed art')


def audit_pixels(raw, layout, assets):
    """Pure pixel oracle; decoded fixture assets alone carry no source authority."""
    require(type(raw) is bytes and len(raw) == layout.width * layout.height, 'raw surface size differs from geometry')
    backing = assets['backing']
    sprite_shape(backing, 387, 66)
    bodies = []
    for slot, kind in enumerate(TYPES):
        sprite = assets['portraits'][kind]
        sprite_shape(sprite, 32, 64)
        rect = layout.portrait(slot)
        bad = sum(raw[(rect.top + y) * layout.width + rect.left + x] != sprite.pixels[y * 32 + x]
                  for y in range(20, 49) for x in range(32))
        bodies.append(dict(slot=slot, type=kind, rectangle_inclusive=list(rect.as_tuple()),
                           checked_pixels=928, mismatches=bad, passed=bad == 0))
    occupied = [layout.portrait(i) for i in range(8)]
    checked = bad = 0
    for y in range(66):
        for x in range(387):
            px, py = layout.backing.left + x, layout.backing.top + y
            if any(r.left <= px <= r.right and r.top <= py <= r.bottom for r in occupied):
                continue
            checked += 1
            bad += raw[py * layout.width + px] != backing.pixels[y * 387 + x]
    edges = frame.audit_surface(raw, layout.framed, assets['frame'])
    cells = bar.compare_cells(raw, layout.width, layout.height, assets['action'], stage=bar.COMPLETE_HD_STAGE)
    return dict(passed=edges['passed'] and all(c['exact_source_match'] for c in cells)
                and all(r['passed'] for r in bodies) and bad == 0,
                frame=edges, action_bar=dict(passed=all(c['exact_source_match'] for c in cells), cells=cells),
                portrait_bodies=dict(passed=all(r['passed'] for r in bodies), rows_inclusive=[20, 48], slots=bodies),
                exposed_backing=dict(passed=bad == 0, checked_pixels=checked, mismatches=bad, sprite=35,
                                     rectangle_inclusive=list(layout.backing.as_tuple())))


def backing_bytes(raw, layout):
    rect = layout.backing
    return b''.join(raw[y * layout.width + rect.left:y * layout.width + rect.right + 1]
                    for y in range(rect.top, rect.bottom + 1))


def false_claims(value, names=FALSE_FLAGS):
    for name in names:
        require(value.get(name) is False, 'unsupported or missing evidence disclaimer: ' + name)


def verify_cleanup(summary, plan):
    cleanup = summary['cleanup']
    require(type(cleanup) is dict and cleanup.get('desktop_closed') is True, 'desktop closure is unverified')
    candidates = summary['candidates']
    require(type(candidates) is list and len(candidates) == 1, 'exactly one owned candidate identity required')
    stops = cleanup['candidates']
    require(type(stops) is list and len(stops) == 1, 'exactly one candidate cleanup required')
    cdb, game = summary['cdb'], candidates[0]
    for identity, expected in ((cdb, plan['cdb']), (game, plan['candidate_path'])):
        require(type(identity) is dict and path_value(identity['path']) == path_value(expected), 'cleanup executable identity differs')
        for key in ('process_id', 'creation_filetime'):
            require(type(identity.get(key)) is int and identity[key] > 0, 'invalid retained process identity: ' + key)
        require(identity.get('handle_retained') is True, 'process handle ownership was not retained')
    require(type(game.get('parent_process_id')) is int and game['parent_process_id'] == cdb['process_id']
            and game['process_id'] != cdb['process_id'] and game['creation_filetime'] >= cdb['creation_filetime']
            and game.get('candidate_sha256') == plan['candidate_sha256'],
            'candidate parent or executable hash differs')
    for stopped, identity in ((cleanup['cdb'], cdb), (stops[0], game)):
        require(type(stopped) is dict and stopped.get('absent') is True and stopped.get('handle_closed') is True,
                'owned process absence or handle closure is unverified')
        require(canonical(stopped.get('identity')) == canonical(identity), 'cleanup refers to a different process identity')
    return game


def verify_png(reader, summary, run, palette, width, height, final_raw):
    metadata = reader.json(run / 'surface.png.json')
    require(canonical(metadata) == canonical(summary['png']), 'PNG metadata differs from host summary')
    for key, expected in (('raw_path', run / 'surface.raw'), ('png_path', run / 'surface.png'),
                          ('palette_path', summary['palette']['path']), ('log_path', summary['capture_prefix']['path'])):
        require(path_value(metadata[key]) == path_value(str(expected)), 'PNG artifact path differs: ' + key)
    for key, expected in (('width', width), ('height', height), ('pitch', width),
                          ('raw_bytes', len(final_raw)), ('used_bytes', len(final_raw))):
        require(type(metadata.get(key)) is int and metadata[key] == expected, 'PNG integer field differs: ' + key)
    require(metadata.get('palette_mode') == 'directdraw-palette', 'PNG lacks a real DirectDraw palette')
    require(len(palette) == 1024 and any(palette[i] for i in range(1024) if i % 4 != 3), 'empty or malformed real palette')
    for key in ('raw_sha256', 'used_sha256'):
        require(metadata.get(key) == sha(final_raw), 'PNG raw identity differs: ' + key)
    require(reader.read(run / 'surface.raw') == final_raw, 'root surface copy differs from stopped snapshot')
    actual = reader.read(run / 'surface.png', expected=metadata['png_sha256'])
    expected = (png.PNG_SIGNATURE + png.png_chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0))
                + png.png_chunk(b'IDAT', zlib.compress(png.indices_to_rgb_rows(final_raw, width, height, width, palette), 9))
                + png.png_chunk(b'IEND', b''))
    require(actual == expected, 'PNG does not encode the actual stopped raw and retained palette')
    return dict(passed=True, path=str(run / 'surface.png'), sha256=sha(actual), palette_sha256=sha(palette),
                raw_sha256=sha(final_raw), encodes='capture-1; all three final raw copies must match')


def audit_summary(summary_path, resource_root):
    """Validate original host artifacts; resource_root is exactly its work_dir."""
    reader = Artifacts()
    report = dict(schema='clash95_complete_hd_army_selection_surface_audit_v1',
                  generated_at=datetime.now(timezone.utc).isoformat(), passed=False, source_authenticated=False,
                  pixels_verified=False, ready_for_bounded_selection_review=False, captures={}, failures=[],
                  ordinary_input_proof=False, manual_input_proof=False, visible_composition_proof=False,
                  promotion_ready=False, runtime_accepted=False, count_text_verified=False, map_unit_artwork_verified=False,
                  cleanup_receipts_verified=False, cleanup_observed_by_this_audit=False, limits=LIMITS.copy())
    audit_sources = {}
    try:
        for path in (Path(__file__), Path(bar.__file__), Path(frame.__file__), Path(png.__file__), Path(trace.__file__),
                     ROOT / 'tools/hd_layout_asset_composition.py', ROOT / 'src/patcher/framed_army_viewport.py',
                     ROOT / 'src/patcher/framed_viewport.py'):
            audit_sources[str(path.resolve())] = sha(reader.read(path.resolve()))
        summary_path = path_value(str(summary_path))
        run = summary_path.parent
        summary = reader.json(summary_path)
        require(summary.get('schema') == HOST_SCHEMA, 'unsupported host summary schema')
        plan = summary['plan']
        require(type(plan) is dict and plan.get('schema') == PLAN_SCHEMA, 'unsupported capture plan schema')
        require(canonical(reader.json(run / 'plan.json')) == canonical(plan), 'retained plan differs from summary')
        require(path_value(plan['out_dir']) == run, 'summary does not belong to the planned capture directory')
        work = path_value(str(resource_root))
        require(work == path_value(plan['work_dir']), 'resource-root must equal the original isolated work_dir')
        require(plan.get('stage') == bar.COMPLETE_HD_STAGE and plan.get('resolution') in trace.producer.builder.RESOLUTIONS,
                'unsupported complete-HD stage or resolution')
        width, height = map(int, plan['resolution'].split('x'))
        require(type(plan.get('width')) is int and type(plan.get('height')) is int
                and (plan['width'], plan['height']) == (width, height), 'plan dimensions differ')
        layout = FramedArmyViewport(width, height)
        report.update(stage=plan['stage'], resolution=plan['resolution'], candidate_sha256=plan['candidate_sha256'])
        for name in ('passed', 'executed', 'cleanup_verified', 'clean_stable_pair', 'source_and_input_identities_unchanged'):
            require(summary.get(name) is True, 'host prerequisite is not true: ' + name)
        require(summary.get('status') == 'bounded_hidden_complete_hd_army_selection_capture'
                and summary.get('failures') == [], 'host status or failures contradict success')
        false_claims(summary, FALSE_FLAGS + ('frame_verified', 'action_bar_verified'))
        false_claims(plan)
        for value in (summary, plan):
            for key in ('runtime_accepted', 'count_text_verified', 'map_unit_artwork_verified'):
                if key in value:
                    require(value[key] is False, 'unsupported extra evidence claim: ' + key)
        environment = plan.get('child_environment')
        require(plan.get('environment') == 'hidden_cdb_host' and type(environment) is dict
                and set(environment) == {'CLASH_PROXY_PRESENT', 'parent_environment_modified'}
                and environment.get('CLASH_PROXY_PRESENT') == '0' and environment.get('parent_environment_modified') is False,
                'hidden non-presenting environment contract differs')
        identities = plan['identities']
        require(type(identities) is list and identities, 'source/runtime/input identities are missing')
        identity_paths = {}
        for identity in identities:
            path = path_value(identity['path'])
            require(path not in identity_paths, 'duplicate planned file identity')
            identity_paths[path] = identity['sha256']
            reader.receipt(identity)
        for key in ('original', 'input_candidate', 'save', 'candidate_manifest', 'host_path', 'producer', 'trace', 'converter', 'cdb', 'python', 'proxy_input'):
            require(path_value(plan[key]) in identity_paths, 'required input lacks a planned identity: ' + key)
        for key, relative in (('host_path', 'scripts/cdb/run_complete_hd_army_selection_capture.ps1'),
                              ('producer', 'tools/complete_hd_army_selection_probe.py'),
                              ('trace', 'tools/complete_hd_army_selection_trace.py'), ('converter', 'tools/cdb_surface_dump_to_png.py')):
            require(path_value(plan[key]) == (ROOT / relative).resolve(), 'unreviewed source path: ' + key)
        reader.read(run / 'host.ps1', expected=identity_paths[path_value(plan['host_path'])])
        original = reader.read(plan['original'], expected=plan['original_sha256'])
        candidate = reader.read(plan['candidate_path'], expected=plan['candidate_sha256'])
        require(reader.read(plan['input_candidate']) == candidate, 'input/copy candidate differs')
        require(path_value(plan['save']) == (work / 'save/0.dat').resolve(), 'save is outside original work directory')
        save = reader.read(plan['save'], expected=plan['save_sha256'])
        reader.read(plan['proxy_path'], expected=plan['proxy_sha256'])
        require(reader.read(plan['proxy_input']) == reader.read(plan['proxy_path']), 'runtime proxy differs from prepared input')
        assets_before = plan['assets_before']
        require(type(assets_before) is dict and assets_before, 'work-directory inventory is missing')
        actual = {}
        for path in sorted(work.rglob('*')):
            require(not path.is_symlink(), 'work-directory reparse path is unsupported')
            if path.is_file():
                actual[path.relative_to(work).as_posix()] = sha(reader.read(path))
        require(canonical(actual) == canonical(assets_before) == canonical(summary['assets_after']), 'work-directory inventory changed')
        packet_bytes = reader.receipt(summary['packet'], path=run / 'packet.json')
        packet = reader.json(run / 'packet.json')
        probe = reader.receipt(summary['probe'], path=run / 'complete-hd-army-selection.cdb')
        require(sha(probe) == plan['probe_sha256'], 'plan probe SHA differs')
        require(packet.get('stage') == plan['stage'] and packet.get('resolution') == plan['resolution']
                and packet.get('unit_squad_types') == TYPES and path_value(packet['capture_dir']) == run,
                'packet route or capture identity differs')
        prefix = reader.receipt(summary['capture_prefix'], path=run / 'capture-prefix.log')
        final_log = reader.receipt(summary['final_log'], path=run / 'cdb.log')
        require(summary['final_log'].get('capture_prefix_preserved') is True and final_log.startswith(prefix), 'final log lost its capture prefix')
        fresh = trace.evaluate_bound_trace(final_log.decode('utf-8-sig'), packet, original=original, candidate=candidate,
                                          save=save, generated_probe=probe, candidate_manifest=reader.json(plan['candidate_manifest']))
        fresh['source']['log_raw_sha256'] = sha(final_log)
        require(fresh.get('passed') is True and fresh.get('ready_for_host_capture') is True
                and fresh.get('whole_candidate_bound') is True and fresh.get('source_authenticated') is True,
                'fresh complete source-bound trace failed: ' + json.dumps(fresh.get('failures')))
        require(canonical(fresh) == canonical(summary['final_trace']) == canonical(reader.json(run / 'trace-final.json')),
                'retained final trace differs from fresh full reconstruction')
        prefix_result = trace.evaluate_trace(prefix.decode('utf-8-sig'), packet)
        require(prefix_result.get('passed') is True and canonical(prefix_result['selection_sequence']) == canonical(fresh['selection_sequence']),
                'captured prefix differs from the complete bound native selection sequence')
        stored_trace = reader.json(run / 'trace.json')
        require(canonical(stored_trace) == canonical(summary['trace'])
                and stored_trace.get('passed') is True and stored_trace.get('ready_for_host_capture') is True
                and stored_trace['source'].get('log_raw_sha256') == sha(prefix)
                and canonical(stored_trace['selection_sequence']) == canonical(fresh['selection_sequence']),
                'host capture trace does not bind the retained prefix and native selection')
        for key in ('original_sha256', 'candidate_sha256', 'save_sha256', 'probe_raw_sha256', 'candidate_manifest_canonical_sha256', 'source_sha256'):
            require(canonical(stored_trace['source'][key]) == canonical(fresh['source'][key]), 'capture/final trace source differs: ' + key)
        require(fresh['source']['candidate_manifest_canonical_sha256'] == plan['candidate_manifest_canonical_sha256'], 'plan manifest identity differs')
        for relative, digest in fresh['source']['source_sha256'].items():
            require(identity_paths.get((ROOT / relative).resolve()) == digest, 'trace source lacks a matching planned identity: ' + relative)
        report['source_authenticated'] = True
        report['trace_binding'] = dict(passed=True, packet_sha256=sha(packet_bytes), probe_sha256=sha(probe),
                                      final_log_sha256=sha(final_log), capture_prefix_sha256=sha(prefix))
        game = verify_cleanup(summary, plan)
        snapshots = summary['snapshots']
        require(type(snapshots) is list and len(snapshots) == 3, 'all three stopped snapshots are required')
        require(canonical(summary['snapshot']) == canonical(snapshots[0]), 'primary snapshot differs from first stopped copy')
        surface = fresh['surface']
        raws = {}
        for label in LABELS[:2]:
            raws[label] = reader.receipt(summary[label], path=run / (label + '.raw'), size=width * height)
        headers = []
        for index, snapshot in enumerate(snapshots, 1):
            label = 'capture-' + str(index)
            require(type(snapshot) is dict, 'snapshot must be an object')
            for key, value in (('width', width), ('height', height), ('pitch', width), ('pixel_reads', 1), ('header_reads', 2), ('e0_reads', 2),
                               ('surface', surface['surface']), ('base', surface['base'])):
                require(type(snapshot.get(key)) is int and snapshot[key] == value, 'snapshot integer differs: ' + key)
            require(snapshot.get('paused') is True and snapshot.get('capture') == 'e0_software_diagnostic'
                    and canonical(snapshot['game_identity']) == canonical(game), 'snapshot ownership or capture method differs')
            raw_path = run / label / 'surface.raw'
            raws[label] = reader.receipt(snapshot, path=raw_path, size=width * height)
            for phase in ('before', 'after'):
                reads = snapshot['reads'][phase]
                e0 = reader.receipt(reads['e0'], path=raw_path.with_name('surface-' + phase + '-e0.raw'), size=4)
                header = reader.receipt(reads['header'], path=raw_path.with_name('surface-' + phase + '-header.raw'), size=188)
                require(type(reads['e0'].get('address')) is int and reads['e0']['address'] == 0x5202e0
                        and type(reads['header'].get('address')) is int and reads['header']['address'] == surface['surface'], 'snapshot read address differs')
                require(struct.unpack('<I', e0)[0] == surface['surface'] and struct.unpack_from('<HHI', header) == (width, height, surface['base'])
                        and struct.unpack_from('<I', header, 184)[0] == 0x50ee24, 'E0/header bytes differ from bound trace surface')
                headers.append((e0, header))
        require(all(value == headers[0] for value in headers), 'stopped E0/header observations changed')
        require(all(raws[name] == raws['capture-1'] for name in LABELS[2:]), 'stopped pixel triplet differs despite host claim')
        palette = reader.receipt(summary['palette'], path=plan['palette_path'], size=1024)
        report['screenshot'] = verify_png(reader, summary, run, palette, width, height, raws['capture-1'])
        assets = load_assets(reader.read(work / 'DATA/minimum.res'), reader.read(work / 'DATA/GFX3.RES'))
        report['asset_members'] = assets['members']
        for label, raw in raws.items():
            row = audit_pixels(raw, layout, assets)
            row.update(raw_sha256=sha(raw), bytes=len(raw), capture_path=str(run / (label + '.raw') if label in LABELS[:2] else run / label / 'surface.raw'))
            report['captures'][label] = row
            if not row['passed']:
                report['failures'].append(label + ': frame/footer, action-cell, portrait-body or exposed-backing pixels failed; see capture details')
        backing_equal = all(backing_bytes(raw, layout) == backing_bytes(raws['before-redraw'], layout) for raw in raws.values())
        report['complete_backing'] = dict(passed=backing_equal, checked_pixels_per_capture=25542,
                                         rectangle_inclusive=list(layout.backing.as_tuple()), compared=list(LABELS))
        if not backing_equal:
            report['failures'].append('complete 387x66 portrait backing changed through redraw or final capture')
        require(raws['after-redraw'] == raws['capture-1'], 'after-redraw and stopped final surface differ')
        report['pixels_verified'] = not report['failures']
        report['cleanup_receipts_verified'] = True
        reader.unchanged()
        report['passed'] = report['source_authenticated'] and report['pixels_verified']
        report['ready_for_bounded_selection_review'] = report['passed']
    except (OSError, KeyError, TypeError, ValueError, UnicodeError, struct.error, RecursionError) as error:
        report['failures'].append(str(error))
        report.update(passed=False, ready_for_bounded_selection_review=False,
                      source_authenticated=False, pixels_verified=False, cleanup_receipts_verified=False)
    report['artifacts'] = reader.receipts()
    report['audit_sources'] = audit_sources
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--summary', required=True, type=Path)
    parser.add_argument('--resource-root', required=True, type=Path, help='The same isolated work_dir recorded by the host; contains DATA and save.')
    args = parser.parse_args()
    result = audit_summary(args.summary, args.resource_root)
    print(json.dumps(result, indent=2))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
