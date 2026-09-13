#!/usr/bin/env python3
"""Audit retained complete-HD native movement state and software pixels offline.

The exact original host fields and all four command files are bound; no report
is projected into a selection schema. Native movement, pixels and recorded
cleanup are separate from ordinary input, glyph correctness and promotion.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import struct
import sys
import zlib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tools'))
import complete_hd_army_selection_surface_audit as selection
import complete_hd_army_movement_trace as trace
from src.patcher.partial_tile_clip import file_offset

SELECTION_AUDIT_SHA = '7effc95203b231c9e007b7aca6a8b47fe2a5d2de8b9b2273a2a4c66260fedd5f'
HOST_SCHEMA = 'clash95_complete_hd_army_movement_capture_v1'
PLAN_SCHEMA = 'clash95_complete_hd_army_movement_capture_plan_v1'
CHECKPOINTS = ('movement-before', 'movement-preview', 'movement-after')
FINALS = ('capture-1', 'capture-2', 'capture-3')
LABELS = CHECKPOINTS + FINALS
PALETTE_SCOPE = 'all three checkpoint PNGs use the retained final proxy palette; intermediate palette changes are not independently traced'
FALSE_FLAGS = selection.FALSE_FLAGS
sha, require, canonical = selection.sha, selection.require, trace.canonical
path_value = selection.path_value
Artifacts = selection.Artifacts
bar, frame, png = selection.bar, selection.frame, selection.png
FramedArmyViewport = selection.FramedArmyViewport

LIMITS = [
    'Reads retained files only; no game, debugger, input, capture or image writing occurs.',
    'Complete bound movement proves one controlled native preview/confirmation route, never ordinary dispatch or manual input.',
    'Every raw observation must pass all four frame bands, footer, six action cells, eight portrait bodies and exposed backing source pixels.',
    'Portrait numbers load signed health/count byte army+31*slot+15, not action points at +14. Glyph shapes are not independently verified.',
    'Whole-backing stability applies only to unchanged portrait types, health/count inputs and status badges with the source-guarded ten selection flags zero.',
    'Map-unit artwork and terrain changes, command availability, complete world preservation and final wrapper composition remain unproved.',
    'Checkpoint PNGs use the retained final proxy palette as a diagnostic; intermediate palette changes were not independently captured. Indexed-pixel source checks do not depend on that colorization.',
    'Owned cleanup receipts are checked for identity and consistency; live process absence is not observed by this offline tool.',
    'No source, state, pixel or cleanup result supplies stable-stage promotion.',
]


def exact_int(value, expected, label):
    require(type(value) is int and value == expected, label + ' must be the exact expected integer')


def verify_native_panel_contract(original):
    """Small instruction spans within the fully reconstructed native suffix."""
    spans = ((0x42366b, bytes.fromhex('0fbe44020f')),  # MOVSX EAX,byte[EDX+EAX+0F]
             (0x423607, bytes.fromhex('f644021304')))  # TEST byte[EDX+EAX+13],04
    receipts = []
    for va, expected in spans:
        offset = file_offset(original, va, len(expected))
        require(original[offset:offset + len(expected)] == expected, 'native portrait number/status field instruction differs')
        receipts.append(dict(va=va, file_offset=offset, bytes=len(expected), sha256=sha(expected)))
    return receipts


def panel_inputs(record):
    require(type(record) is bytes and len(record) == 725, 'complete immutable army record required for panel inputs')
    return [dict(slot=i, unit_type=struct.unpack_from('<h', record, 6 + 31 * i)[0],
                 number_input=struct.unpack_from('<b', record, 15 + 31 * i)[0], status_badge=bool(record[19 + 31 * i] & 4))
            for i in range(8)]


def audit_panel_stability(raws, units, layout):
    """Compare the full panel without interpreting changed AP as number glyphs."""
    require(set(raws) == set(LABELS) and set(units) == set(CHECKPOINTS), 'all movement and final observations required')
    inputs = {name: panel_inputs(units[name]) for name in CHECKPOINTS}
    same_inputs = all(value == inputs[CHECKPOINTS[0]] for value in inputs.values())
    before = selection.backing_bytes(raws[CHECKPOINTS[0]], layout)
    differences = {name: sum(a != b for a, b in zip(before, selection.backing_bytes(raw, layout))) for name, raw in raws.items()}
    same_pixels = all(count == 0 for count in differences.values())
    return dict(passed=same_inputs and same_pixels, panel_inputs_unchanged=same_inputs,
                complete_backing_unchanged=same_pixels, checked_pixels_per_capture=25542,
                rectangle_inclusive=list(layout.backing.as_tuple()), mismatches_from_before=differences,
                input_fields=inputs, count_text_verified=False,
                scope='Full backing equality with unchanged type/health/status and source-guarded zero portrait-selection flags; no glyph oracle.')


def verify_png(reader, metadata, raw_path, png_path, metadata_path, palette_path, log_path, palette, width, height, raw):
    require(canonical(reader.json(metadata_path)) == canonical(metadata), 'PNG metadata differs from original host fields')
    for key, expected in (('raw_path', raw_path), ('png_path', png_path), ('palette_path', palette_path), ('log_path', log_path)):
        require(path_value(metadata[key]) == path_value(str(expected)), 'PNG path differs: ' + key)
    for key, expected in (('width', width), ('height', height), ('pitch', width), ('raw_bytes', len(raw)), ('used_bytes', len(raw))):
        exact_int(metadata.get(key), expected, 'PNG ' + key)
    require(metadata.get('palette_mode') == 'directdraw-palette' and len(palette) == 1024
            and any(palette[i] for i in range(1024) if i % 4 != 3), 'real nonempty DirectDraw palette required')
    require(metadata.get('raw_sha256') == sha(raw) and metadata.get('used_sha256') == sha(raw), 'PNG raw identity differs')
    require(reader.read(raw_path) == raw, 'PNG raw file is not the retained observation')
    actual = reader.read(png_path, expected=metadata['png_sha256'])
    expected = (png.PNG_SIGNATURE + png.png_chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0))
                + png.png_chunk(b'IDAT', zlib.compress(png.indices_to_rgb_rows(raw, width, height, width, palette), 9))
                + png.png_chunk(b'IEND', b''))
    require(actual == expected, 'PNG does not encode actual raw pixels and retained palette')
    return dict(passed=True, path=str(png_path), sha256=sha(actual), raw_sha256=sha(raw), palette_sha256=sha(palette))


def bind_plan(reader, summary, run, work):
    plan = summary['plan']
    require(type(plan) is dict and plan.get('schema') == PLAN_SCHEMA, 'unsupported movement plan schema')
    require(canonical(reader.json(run / 'plan.json')) == canonical(plan), 'retained plan differs from summary')
    require(path_value(plan['out_dir']) == run and path_value(plan['work_dir']) == work, 'capture or resource-root differs from original plan')
    require(plan.get('stage') == bar.COMPLETE_HD_STAGE and plan.get('resolution') in trace.producer.base.builder.RESOLUTIONS,
            'unsupported complete-HD stage or resolution')
    width, height = map(int, plan['resolution'].split('x'))
    exact_int(plan.get('width'), width, 'plan width'); exact_int(plan.get('height'), height, 'plan height')
    for name in ('passed', 'executed', 'cleanup_verified', 'clean_stable_pair', 'source_and_input_identities_unchanged'):
        require(summary.get(name) is True, 'host prerequisite is not true: ' + name)
    require(summary.get('status') == 'bounded_hidden_complete_hd_army_movement_capture'
            and type(summary.get('failures')) is list and summary['failures'] == [], 'host verdict contradicts success')
    require(summary.get('checkpoint_palette_scope') == PALETTE_SCOPE, 'host checkpoint palette scope is missing or contradicts final-palette diagnostics')
    selection.false_claims(summary, FALSE_FLAGS + ('frame_verified', 'action_bar_verified'))
    selection.false_claims(plan)
    for value in (summary, plan):
        for key in ('runtime_accepted', 'count_text_verified', 'map_unit_artwork_verified'):
            if key in value:
                require(value[key] is False, 'unsupported extra evidence claim: ' + key)
    environment = plan.get('child_environment')
    require(plan.get('environment') == 'hidden_cdb_host' and type(environment) is dict
            and set(environment) == {'CLASH_PROXY_PRESENT', 'parent_environment_modified'}
            and environment.get('CLASH_PROXY_PRESENT') == '0' and environment.get('parent_environment_modified') is False,
            'hidden non-presenting environment differs')
    require(type(plan.get('identities')) is list and plan['identities'], 'planned identities are missing')
    identities = {}
    for row in plan['identities']:
        path = path_value(row['path'])
        require(path not in identities, 'duplicate planned file identity')
        identities[path] = row['sha256']; reader.receipt(row)
    roles = ('original', 'input_candidate', 'save', 'candidate_manifest', 'host_path', 'producer', 'trace', 'converter',
             'cdb', 'python', 'proxy_input', 'proxy_source', 'proxy_manifest')
    for key in roles:
        require(path_value(plan[key]) in identities, 'required role has no planned identity: ' + key)
    for key, relative in (('host_path', 'scripts/cdb/run_complete_hd_army_movement_capture.ps1'),
                          ('producer', 'tools/complete_hd_army_movement_probe.py'), ('trace', 'tools/complete_hd_army_movement_trace.py'),
                          ('converter', 'tools/cdb_surface_dump_to_png.py'), ('proxy_source', 'src/ddraw_surfdump_proxy/ddraw_surfdump_proxy.cpp')):
        require(path_value(plan[key]) == (ROOT / relative).resolve(), 'unreviewed source role: ' + key)
    reader.read(run / 'host.ps1', expected=identities[path_value(plan['host_path'])])
    original = reader.read(plan['original'], expected=plan['original_sha256'])
    candidate = reader.read(plan['candidate_path'], expected=plan['candidate_sha256'])
    require(reader.read(plan['input_candidate']) == candidate, 'candidate copy differs from input')
    require(path_value(plan['save']) == (work / 'save/0.dat').resolve(), 'save is outside the original work directory')
    save = reader.read(plan['save'], expected=plan['save_sha256'])
    reader.read(plan['proxy_source'], expected=plan['proxy_source_sha256'])
    reader.read(plan['proxy_manifest'], expected=plan['proxy_manifest_sha256'])
    proxy = reader.json(plan['proxy_manifest'])
    require(proxy.get('generated_by') == 'clash-hd-surface-dump-proxy'
            and path_value(proxy['source']) == path_value(plan['proxy_source'])
            and path_value(proxy['output']) == path_value(plan['proxy_input'])
            and proxy.get('source_sha256', '').lower() == plan['proxy_source_sha256']
            and proxy.get('output_sha256', '').lower() == plan['proxy_sha256'], 'proxy manifest role or source/binary identity differs')
    require(reader.read(plan['proxy_path'], expected=plan['proxy_sha256']) == reader.read(plan['proxy_input']), 'copied proxy differs')
    require(type(plan.get('assets_before')) is dict and plan['assets_before'], 'work-directory inventory missing')
    inventory = {}
    for path in sorted(work.rglob('*')):
        checked = path_value(str(path))
        if checked.is_file():
            inventory[path.relative_to(work).as_posix()] = sha(reader.read(path))
    require(canonical(inventory) == canonical(plan['assets_before']) == canonical(summary['assets_after']), 'work-directory inventory changed')
    return plan, FramedArmyViewport(width, height), identities, dict(original=original, candidate=candidate, save=save,
                                                                    candidate_manifest=reader.json(plan['candidate_manifest']))


def bind_commands(reader, summary, plan, packet, run):
    rows = plan.get('supplemental_commands')
    require(type(rows) is list and len(rows) == 3 and canonical(rows) == canonical(summary.get('supplemental_commands')),
            'exact three actual/planned supplemental command receipts required')
    expected = {f"{packet['capture_dir']}/movement-checkpoint-{i}.cdb" for i in range(3)}
    require(type(packet.get('supplemental_commands')) is dict and set(packet['supplemental_commands']) == expected,
            'packet requires exact three supplemental commands')
    commands = {}
    for i, row in enumerate(rows):
        exact_int(row.get('checkpoint'), i, 'supplemental command checkpoint')
        packet_path = row['packet_path']
        require(type(packet_path) is str and packet_path == f"{packet['capture_dir']}/movement-checkpoint-{i}.cdb"
                and packet_path not in commands, 'supplemental command order/key differs')
        commands[packet_path] = reader.receipt(row, path=run / f'movement-checkpoint-{i}.cdb')
    return commands


def bind_checkpoints(reader, summary, packet, run, width, height):
    rows = summary.get('checkpoints')
    require(type(rows) is list and len(rows) == 3, 'all three measured movement checkpoints required')
    raw, headers, units = {}, {}, {}
    for index, (name, row, paths) in enumerate(zip(CHECKPOINTS, rows, trace.snapshot_paths(packet))):
        exact_int(row.get('checkpoint'), index, 'movement checkpoint')
        require(row.get('name') == name, 'movement checkpoint name/order differs')
        for key, size, destination in (('raw', width * height, raw), ('header', 188, headers), ('unit', 725, units)):
            path = paths[key + '_path']
            data = reader.receipt(row[key], path=run / Path(path).name, size=size)
            destination[name if key == 'raw' else path] = data
    return raw, headers, units


def bind_trace(reader, summary, plan, packet, run, inputs, identities):
    prefix = reader.receipt(summary['capture_prefix'], path=run / 'capture-prefix.log')
    final = reader.receipt(summary['final_log'], path=run / 'cdb.log')
    require(summary.get('final_trace_attempted') is True
            and summary['final_log'].get('unchanged_during_final_validation') is True
            and summary['final_log'].get('validator_log_identity_matched') is True,
            'final trace attempt or immutable validator log receipts are not true')
    require(summary['final_log'].get('capture_prefix_preserved') is True and final.startswith(prefix), 'final log lost the captured prefix')
    fresh = trace.evaluate_bound_capture(final.decode('utf-8-sig'), packet, **inputs)
    fresh['source']['log_raw_sha256'] = sha(final)
    for key in ('passed', 'ready_for_host_capture', 'source_authenticated', 'whole_candidate_bound', 'candidate_manifest_bound',
                'all_supplemental_commands_bound', 'snapshot_headers_verified', 'snapshot_units_verified'):
        require(fresh.get(key) is True, 'fresh complete bound capture failed (' + key + '): ' + json.dumps(fresh.get('failures')))
    require(fresh.get('sequence_only') is False and fresh.get('initial_log_projected') is False
            and fresh['movement_state'].get('passed') is True, 'movement capture has incomplete source/state validation')
    require(canonical(fresh) == canonical(summary['final_trace']) == canonical(reader.json(run / 'trace-final.json')),
            'retained final trace differs from full fresh reconstruction')
    observed = trace.evaluate_trace(prefix.decode('utf-8-sig'), packet)
    require(observed.get('passed') is True and canonical(observed['movement_sequence']) == canonical(fresh['movement_sequence']),
            'captured prefix differs from the bound native movement sequence')
    stored = reader.json(run / 'trace.json')
    require(canonical(stored) == canonical(summary['trace']) and stored.get('passed') is True
            and stored.get('ready_for_host_capture') is True and stored.get('snapshot_headers_verified') is True
            and stored.get('snapshot_units_verified') is True and stored['source'].get('log_raw_sha256') == sha(prefix)
            and canonical(stored['movement_sequence']) == canonical(fresh['movement_sequence']), 'stored capture trace differs from authenticated prefix')
    for key in ('original_sha256', 'candidate_sha256', 'save_sha256', 'probe_raw_sha256', 'candidate_manifest_canonical_sha256',
                'source_sha256', 'supplemental_commands', 'snapshot_headers', 'snapshot_units'):
        require(canonical(stored['source'][key]) == canonical(fresh['source'][key]), 'capture/final trace binding differs: ' + key)
    require(fresh['source']['candidate_manifest_canonical_sha256'] == plan['candidate_manifest_canonical_sha256'], 'plan manifest digest differs')
    for relative, digest in fresh['source']['source_sha256'].items():
        require(identities.get((ROOT / relative).resolve()) == digest, 'trace source lacks its planned identity: ' + relative)
    for row, observed in zip(summary['checkpoints'], fresh['snapshots']):
        require(canonical(row['surface']) == canonical(observed), 'checkpoint receipt surface differs from actual trace')
    return fresh


def bind_final_captures(reader, summary, plan, run, fresh, game, width, height, settled_unit, settled_header):
    rows = summary.get('snapshots')
    require(type(rows) is list and len(rows) == 3 and canonical(summary['snapshot']) == canonical(rows[0]), 'all three final snapshots and primary alias required')
    surface = fresh['surface']; ready = fresh['movement_sequence']['ready']
    unit_address = ready['unit']
    raw = {}; reads_seen = []
    for index, (label, row) in enumerate(zip(FINALS, rows), 1):
        require(type(row) is dict, 'final snapshot must be an object')
        for key, value in (('width', width), ('height', height), ('pitch', width), ('pixel_reads', 1), ('header_reads', 2), ('e0_reads', 2),
                           ('unit_reads', 2), ('surface', surface['surface']), ('base', surface['base']), ('unit_address', unit_address)):
            exact_int(row.get(key), value, 'final snapshot ' + key)
        require(row.get('paused') is True and row.get('capture') == 'e0_software_diagnostic'
                and canonical(row['game_identity']) == canonical(game), 'final snapshot ownership or capture class differs')
        raw_path = run / label / 'surface.raw'
        raw[label] = reader.receipt(row, path=raw_path, size=width * height)
        for phase in ('before', 'after'):
            readings = row['reads'][phase]; parts = {}
            for name, size, address in (('e0', 4, 0x5202e0), ('header', 188, surface['surface']), ('unit', 725, unit_address)):
                exact_int(readings[name].get('address'), address, name + ' capture address')
                parts[name] = reader.receipt(readings[name], path=raw_path.with_name(f'surface-{phase}-{name}.raw'), size=size)
            require(struct.unpack('<I', parts['e0'])[0] == surface['surface']
                    and struct.unpack_from('<HHI', parts['header']) == (width, height, surface['base'])
                    and struct.unpack_from('<I', parts['header'], 184)[0] == 0x50ee24, 'final E0/header disagrees with bound movement surface')
            require(parts['unit'] == settled_unit and row.get('unit_sha256') == sha(settled_unit), 'final unit record changed from movement-after')
            require(parts['header'] == settled_header, 'final complete surface header changed from movement-after')
            reads_seen.append(parts)
    require(all(parts == reads_seen[0] for parts in reads_seen), 'final E0/header/unit observations changed')
    require(all(data == raw[FINALS[0]] for data in raw.values()), 'final stopped pixels differ despite host stability claim')
    return raw


def audit_summary(summary_path, resource_root):
    reader = Artifacts()
    report = dict(schema='clash95_complete_hd_army_movement_surface_audit_v1', generated_at=datetime.now(timezone.utc).isoformat(),
                  passed=False, source_authenticated=False, unit_records_verified=False, pixels_verified=False, cleanup_receipts_verified=False,
                  ready_for_bounded_movement_review=False, captures={}, screenshots={}, failures=[], audit_sources={},
                  ordinary_input_proof=False, manual_input_proof=False, visible_composition_proof=False, promotion_ready=False,
                  runtime_accepted=False, count_text_verified=False, map_unit_artwork_verified=False, cleanup_observed_by_this_audit=False,
                  limits=LIMITS.copy())
    try:
        sources = (Path(__file__), Path(selection.__file__), Path(trace.__file__), Path(bar.__file__), Path(frame.__file__), Path(png.__file__),
                   ROOT / 'tools/hd_layout_asset_composition.py', ROOT / 'tools/framed_army_movement_state.py',
                   ROOT / 'src/patcher/framed_army_viewport.py', ROOT / 'src/patcher/framed_viewport.py')
        for path in sources:
            report['audit_sources'][str(path.resolve())] = sha(reader.read(path.resolve()))
        require(sha(reader.read(Path(selection.__file__).resolve())) == SELECTION_AUDIT_SHA, 'reviewed selection pixel/binding helper differs')
        summary_path = path_value(str(summary_path)); run = summary_path.parent; work = path_value(str(resource_root))
        summary = reader.json(summary_path)
        require(summary.get('schema') == HOST_SCHEMA, 'unsupported movement host summary schema')
        plan, layout, identities, inputs = bind_plan(reader, summary, run, work)
        width, height = layout.width, layout.height
        report.update(stage=plan['stage'], resolution=plan['resolution'], candidate_sha256=plan['candidate_sha256'])
        reader.receipt(summary['packet'], path=run / 'packet.json'); packet = reader.json(run / 'packet.json')
        probe = reader.receipt(summary['probe'], path=run / 'complete-hd-army-movement.cdb')
        require(sha(probe) == plan['probe_sha256'] and packet.get('stage') == plan['stage'] and packet.get('resolution') == plan['resolution']
                and path_value(packet['capture_dir']) == run, 'movement packet/probe route identity differs')
        commands = bind_commands(reader, summary, plan, packet, run)
        raws, headers, units_by_path = bind_checkpoints(reader, summary, packet, run, width, height)
        inputs.update(generated_probe=probe, supplemental_commands=commands, snapshot_headers=headers, snapshot_units=units_by_path)
        fresh = bind_trace(reader, summary, plan, packet, run, inputs, identities)
        report['source_authenticated'] = True
        report['native_panel_field_contract'] = verify_native_panel_contract(inputs['original'])
        units = {name: units_by_path[row['unit_path']] for name, row in zip(CHECKPOINTS, trace.snapshot_paths(packet))}
        game = selection.verify_cleanup(summary, plan)
        settled_header = headers[trace.snapshot_paths(packet)[2]['header_path']]
        raws.update(bind_final_captures(reader, summary, plan, run, fresh, game, width, height, units['movement-after'], settled_header))
        require(raws['movement-after'] == raws['capture-1'], 'movement-after and stopped final pixels differ')
        report['unit_records_verified'] = True
        report['movement_state'] = {name: trace.state.decode_unit(data) for name, data in units.items()}
        report['movement_state']['scope'] = 'Actual full records bound to complete native trace; no glyph or ordinary-input interpretation.'
        palette = reader.receipt(summary['palette'], path=plan['palette_path'], size=1024)
        for row in summary['checkpoints']:
            name = row['name']
            report['screenshots'][name] = verify_png(reader, row['png'], run / f'{name}.raw', run / f'{name}.png', run / f'{name}.png.json',
                                                   plan['palette_path'], summary['capture_prefix']['path'], palette, width, height, raws[name])
            report['screenshots'][name]['palette_scope'] = 'Retained final proxy palette; intermediate palette changes are not independently observed.'
        report['screenshots']['final'] = verify_png(reader, summary['png'], run / 'surface.raw', run / 'surface.png', run / 'surface.png.json',
                                                  plan['palette_path'], summary['capture_prefix']['path'], palette, width, height, raws['capture-1'])
        assets = selection.load_assets(reader.read(work / 'DATA/minimum.res'), reader.read(work / 'DATA/GFX3.RES'))
        report['asset_members'] = assets['members']
        for label, raw in raws.items():
            row = selection.audit_pixels(raw, layout, assets)
            path = run / f'{label}.raw' if label in CHECKPOINTS else run / label / 'surface.raw'
            row.update(raw_sha256=sha(raw), bytes=len(raw), capture_path=str(path))
            report['captures'][label] = row
            if not row['passed']:
                report['failures'].append(label + ': frame/footer, action cells, portrait bodies or exposed backing failed; see capture details')
        report['complete_backing'] = audit_panel_stability(raws, units, layout)
        if not report['complete_backing']['passed']:
            report['failures'].append('complete portrait backing or its type/health/status input context changed; glyph correctness is not inferred')
        report['pixels_verified'] = not report['failures']; report['cleanup_receipts_verified'] = True
        reader.unchanged()
        report['passed'] = report['source_authenticated'] and report['unit_records_verified'] and report['pixels_verified']
        report['ready_for_bounded_movement_review'] = report['passed']
    except (OSError, KeyError, TypeError, ValueError, UnicodeError, struct.error, RecursionError) as error:
        report['failures'].append(str(error))
        report.update(passed=False, source_authenticated=False, unit_records_verified=False, pixels_verified=False,
                      cleanup_receipts_verified=False, ready_for_bounded_movement_review=False)
    report['artifacts'] = reader.receipts()
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--summary', required=True, type=Path)
    parser.add_argument('--resource-root', required=True, type=Path, help='Original isolated plan.work_dir, containing DATA and save.')
    args = parser.parse_args()
    report = audit_summary(args.summary, args.resource_root)
    print(json.dumps(report, indent=2))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
