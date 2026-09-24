"""Prepare the actual widget candidate's controlled barracks route, offline.

The frozen primary producer supplies only pure native observation helpers.
Widget identity, complete ancestry, source bindings and startup checks remain
explicit. No historical packet, probe marker or runtime log is relabeled.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import re
import struct

import modal_primary_barracks_probe as primary
import modal_widgets_context as context_reader
import render_cdb_surface_probe as renderer
from render_cdb_surface_probe import BASE_PROBE, FRAMED_STAGE, render_probe

ROOT = Path(__file__).resolve().parents[1]
STAGE = context_reader.STAGE
REVISION = context_reader.REVISION
SCHEMA = 'clash95_modal_widgets_barracks_probe_packet_v1'
PROTOCOL = 'widgets_barracks_owned_canvas_v1'
PINS = {
    'patch_clash95_hd.py': 'b2d8af4caf3fef1de0e3902b638be3c6bfba731bca7cd8d10c85c93e12424093',
    'tools/modal_primary_barracks_probe.py': '70bfb222077599af69f405346ccf285afd41ba5fcc50631ec75631f2b189002a',
    'tools/modal_slots_barracks_probe.py': '2d82a009fa38e33bcc74483d2b9b479934f8a5ce20e37a6e99c7c5e84efb32f3',
    'tools/modal_widgets_context.py': 'fd211a1eaee64622c02e370adb5e1326d3f27ae0ad3f36fa56801b6177ab3d42',
    'tools/render_cdb_surface_probe.py': '12685fdfde4972e0f5f9c3d5678fd159fff965bd9ddd7642cb3718c8530296cf',
    'scripts/cdb/run_cdb_surface_dump.ps1': '01fbee7aeacceb6237fcf42fae84aa7d0c1912aba85fadc2fbab030c2b1475a8',
    'probes/cdb/render/clash95_surface_dump_probe.cdb': '6346ca89d5c3e8b63fbb6c96839c48920aa9eb039523f49b442f7fc47fef7df8',
}
SOURCES = (*PINS, 'tools/modal_widgets_barracks_probe.py')
PENDING = ['widget_stage_trace_consumer', 'cached_primary_lock_capture', 'quantity_text_observer',
           'widget_owner_observer', 'raw_query_ledgers', 'capture_host', 'source_artwork_pixel_audit']
LIMITS = [
    'Packet and command preparation only; no widget trace consumer or capture host is supplied here.',
    'Existing castle flags are preserved, but native case dispatch and the flipping gate remain forced diagnostics.',
    'The four native pauses do not yet include cached-primary Lock, quantity-text or widget-owner observation contracts.',
    'A separately authenticated host must bind raw queries, three samples per checkpoint, owned cleanup and final summaries.',
    'Native artwork, text pixels, ordinary input, modal exit, continuity and release acceptance remain unproved.',
    'The compiled probe is ASCII/LF preparation text; runtime command-file transport and its exact bytes are not implemented.',
]
sha = context_reader.sha
canonical = context_reader.canonical_json


def need(condition, message):
    if not condition:
        raise ValueError(message)


def _source_snapshots():
    need(Path(primary.__file__).resolve() == ROOT / 'tools/modal_primary_barracks_probe.py'
         and Path(context_reader.__file__).resolve() == ROOT / 'tools/modal_widgets_context.py'
         and Path(renderer.__file__).resolve() == ROOT / 'tools/render_cdb_surface_probe.py'
         and Path(renderer.patcher.__file__).resolve() == ROOT / 'patch_clash95_hd.py'
         and BASE_PROBE.resolve() == ROOT / 'probes/cdb/render/clash95_surface_dump_probe.cdb',
         'canonical widget observation helper locations required')
    rows = {name: context_reader._snapshot(ROOT / name) for name in SOURCES}
    for name, expected in PINS.items():
        need(sha(rows[name].data) == expected, 'frozen widget observation helper changed: ' + name)
    primary.check_helpers()
    return rows


def _native_contract(original, candidate, selected):
    spans = dict(primary.COMMON)
    for route in (primary.ROUTES['castle_overview'], selected):
        if route.name != 'castle_overview':
            spans[route.entry_va] = route.entry_bytes
        spans[route.present_call_va] = (b'\xe8' + struct.pack('<i', primary.PRESENT - route.stop_va)).hex()
        spans[route.stop_va] = route.return_bytes
        if route.branch_va is not None:
            spans[route.branch_va] = (b'\xb9' + struct.pack('<I', route.entry_va)).hex()
    spans.update(primary._native_spans(selected))
    records, predicates = [], []
    for va, old_hex in sorted(spans.items()):
        old = bytes.fromhex(old_hex)
        need(primary._read(original, va, len(old))[1] == old, f'native source span differs at {va:08x}')
        offset, current = primary._read(candidate, va, len(old))
        need(current == old, f'widget native observation span changed at {va:08x}')
        records.append(dict(va=va, rva=va-primary.IMAGE_BASE, offset=offset,
                            old_hex=old_hex, candidate_hex=current.hex()))
        predicates.extend(f'(by({va+i:08x}) != 0x{value:02x})' for i, value in enumerate(current))
    rejection = primary._reject('loaded_bytes').replace(r'\"', '"').replace(r'\\n', r'\n')
    checks = '\n'.join(f'.if ({" | ".join(predicates[i:i+48])}) {{ {rejection} }}'
                       for i in range(0, len(predicates), 48)) + '\n'
    checks += f'.echo MCAP_BYTE_CONTRACT_PASS candidate_sha256={sha(candidate)} route=barracks\n'
    return records, checks


def _startup_fragments(raw):
    source = raw.decode('utf-8-sig').replace('\r\n', '\n')
    block = re.search(r"elseif \(\$FastForwardStartAnims\) \{\n    @\(\n(.*?)\n    \) -join", source, re.S)
    need(block is not None, 'fixed startup-animation source block missing')
    rows = re.findall(r"^        '([^\n]*)'$", block[1], re.M)
    need(len(rows) == 6 and sum(row.startswith('bp ') for row in rows) == 5,
         'fixed five-breakpoint startup-animation recipe differs')
    before = re.findall(r"^    '(ed 00544cfc __LOAD_MOUSE_RAW_X__; ed 00544d00 __LOAD_MOUSE_RAW_Y__;[^\n]*)'$", source, re.M)
    need(len(before) == 1, 'fixed ordinary pre-entry coordinates missing')
    return '\n'.join(row.replace("''", "'") for row in rows), before[0].replace("''", "'")


def _breakpoints(command):
    """Inventory the fully expanded file; implicit IDs occupy the lowest free ID."""
    occupied, sites = {}, set()
    for line in command.splitlines():
        if not line.startswith('bp'):
            continue
        match = re.fullmatch(r'bp\s*(?:(\d+)\s+)?([0-9a-fA-F]{8})\s+"[^\r\n]*"', line)
        need(match is not None, 'unsupported breakpoint declaration')
        number = int(match[1]) if match[1] else next((i for i in range(1000) if i not in occupied), 1000)
        va = int(match[2], 16)
        need(0 <= number <= 999 and 0 < va < 2**32 and number not in occupied and va not in sites,
             'expanded breakpoint ID/address collision')
        occupied[number] = va
        sites.add(va)
    return {str(number): va for number, va in sorted(occupied.items())}


def _compile(packet, geometry, harness):
    fast, before = _startup_fragments(harness)
    command = packet['map_probe_template']
    need(command.count(primary.DUMP_TOKEN) == 1 and command.count('bc *\n') == 1
         and len(re.findall(r'(?m)^g$', command)) == 1, 'canonical template insertion boundaries differ')
    replacements = {
        '__START_ANIMS_BP__': fast, '__PRE_ENTRY_LOAD_COORD_ACTION__': before, '__LOAD_SLOT__': '0',
        '__LOAD_MOUSE_RAW_X__': f'{geometry["load_mouse"][0] << 6:08x}',
        '__LOAD_MOUSE_RAW_Y__': f'{geometry["load_mouse"][1] << 6:08x}',
        '__VISIBILITY_PLAYGAME_ACTION__': '', '__VISIBILITY_PATCH_ACTION__': '',
        primary.DUMP_TOKEN: packet['handoff_action'],
    }
    for old, new in replacements.items():
        need(old in command, 'required canonical token missing: ' + old)
        command = command.replace(old, new)
    command = command.replace('bc *\n', 'bc *\n' + packet['byte_checks_before_first_breakpoint'])
    command = re.sub(r'(?m)^g$', lambda _: packet['startup_commands_before_final_g'] + 'g', command)
    need(re.search(r'__[A-Z0-9_]+__', command) is None, 'unresolved command-file token')
    need(all(len(line.encode('ascii')) < 4096 for line in command.splitlines()), 'CDB command exceeds 4096-byte bound')
    return command, _breakpoints(command)


def build_screen_probe(original: bytes, candidate: bytes, *, candidate_sha256: str, stage: str,
                       resolution: str, candidate_manifest: Path, route='barracks',
                       availability='existing_flags', castle_index=0, minimap_viewport=True,
                       rendered_probe=None):
    """Authenticate once, then prepare observations; no supplied-context bypass."""
    need(type(original) is bytes and type(candidate) is bytes, 'immutable image bytes required')
    need(stage == STAGE and resolution in context_reader.RESOLUTIONS, 'exact widget stage and resolution required')
    need(route == 'barracks' and availability == 'existing_flags', 'only controlled barracks with existing flags is supported')
    need(type(castle_index) is int and 0 <= castle_index <= 3, 'inspected integer castle index 0..3 required')
    need(minimap_viewport is True, 'widget stage requires the minimap correction')
    need(type(candidate_sha256) is str and re.fullmatch(r'[0-9a-f]{64}', candidate_sha256)
         and sha(candidate) == candidate_sha256, 'exact candidate SHA-256 required')
    sources = _source_snapshots()
    context = context_reader.load_context(original, candidate, Path(candidate_manifest))
    need(context['stage'] == STAGE and context['recipe_revision'] == REVISION
         and context['resolution'] == resolution and context['candidate_sha256'] == candidate_sha256,
         'authenticated widget context identity differs')
    manifest = context['manifest']
    need(set(context['source_hashes']) == context_reader.RECIPE_SOURCE_PATHS
         and canonical(context['source_hashes']) == canonical(manifest['source_hashes']), 'complete widget recipe sources required')
    extra = context['probe']
    expected_loaded = [
        f'MWIDGETS_CONTRACT_PASS stage={STAGE} resolution={resolution} candidate_sha256={candidate_sha256} revision={REVISION}',
        'MWIDGETS_SCOPE owned_modal_widget_bounds primary_composition_proven=false manual_input_proof=false promotion_ready=false',
    ]
    loaded = [line.removeprefix('.echo ') for line in extra.splitlines() if line.startswith('.echo MWIDGETS_')]
    need(loaded == expected_loaded and sha(extra.encode()) == context['probe_sha256'], 'exact widget loaded-image probe required')
    need(not re.search(r'(?m)^\.echo (?:MPRIMARYTEXT|MPRIMARY|SLOTS|ARMY|COMPLETEHD|MCANVAS)_CONTRACT_PASS\b', extra),
         'predecessor startup success cannot substitute for widgets')
    tile = f'.echo PTILE_CONTRACT_PASS stage={STAGE} resolution={resolution} candidate_sha256={candidate_sha256}'
    need(extra.splitlines().count(tile) == 1, 'actual widget PTILE startup identity required')
    metadata = dict(context['owner_context'], slots_metadata=context['slots_context'],
                    primary_metadata=context['primary_context'],
                    primary_observers=primary.primary_observers(context['primary_context'], candidate))
    ancestors = {name: context[name] for name in ('text_context', 'primary_context', 'slots_context')}
    ancestors['complete_context'] = context['slots_context']['base_candidate']
    rendered = render_probe(sources['probes/cdb/render/clash95_surface_dump_probe.cdb'].data.decode('utf-8-sig').replace('\r\n', '\n'), resolution, FRAMED_STAGE)
    template = rendered['template']
    need(len(re.findall(r'(?m)^g$', template)) == 1 and template.rstrip().endswith('\ng'), 'one final canonical startup continuation required')
    template = re.sub(r'(?m)^g$', lambda _: extra.strip() + '\ng', template)
    need(rendered_probe is None or type(rendered_probe) is str and rendered_probe.replace('\r\n', '\n') == template,
         'unchanged canonical widget template required')
    selected = primary.ROUTES[route]
    spans, checks = _native_contract(original, candidate, selected)
    width, height = map(int, resolution.split('x'))
    handoff, commands = primary._commands(selected, width, height, castle_index, availability, metadata)
    startup = (f'.echo MCAP_CONTRACT stage={STAGE} resolution={resolution} candidate_sha256={candidate_sha256} '
               f'route=barracks availability=existing_flags castle_index={castle_index} protocol={PROTOCOL} runtime_acceptance=0\n')
    for number, (va, body) in commands.items():
        startup += f'bp{number} {va:08x} "{body}"\nbd {number}\n'
    packet = dict(schema=SCHEMA, protocol_revision=PROTOCOL, stage=STAGE, recipe_revision=REVISION,
        resolution=resolution, candidate_sha256=candidate_sha256, original_sha256=sha(original),
        source_sha256=dict(context['source_hashes']), producer_sha256=sha(sources[SOURCES[-1]].data),
        context_source_sha256=context['context_source_sha256'],
        authentication_source_hashes=dict(context['authentication_source_hashes']),
        preparation_source_hashes={name: sha(row.data) for name, row in sources.items()},
        candidate_manifest=dict(path=context['manifest_path'], sha256=context['manifest_sha256']),
        manifest_canonical_sha256=context['manifest_canonical_sha256'], canonical_extra_sha256=context['probe_sha256'],
        ancestor_identities={name: {key: ancestor[key] for key in ('stage', 'recipe_revision', 'candidate_sha256')}
                             for name, ancestor in ancestors.items()},
        map_probe_template=template, map_template_sha256=sha(template.encode('ascii')), candidate_extra=extra,
        route=asdict(selected), availability=availability, castle_index=castle_index, minimap_viewport=True,
        canvas_state_va=metadata['state_va'], canvas_state_offsets=metadata['modal_state_offsets'],
        canvas_observer_vas=metadata['modal_observer_vas'], canvas_entry_vas=metadata['modal_entry_vas'],
        canvas_revision=metadata['modal_native_canvas_revision'], slot_entry_vas=metadata['slots_metadata']['slot_entry_vas'],
        primary_entry_vas=metadata['primary_metadata']['primary_entry_vas'], primary_observers=metadata['primary_observers'],
        widget_entry_vas=manifest['widget_entry_vas'], checkpoints=primary.checkpoint_contract(metadata['primary_observers']),
        byte_spans=spans, byte_checks_before_first_breakpoint=checks, startup_commands_before_final_g=startup,
        handoff_action=handoff, dump_action_token=primary.DUMP_TOKEN,
        breakpoint_commands={str(k): dict(va=v[0], body=v[1]) for k, v in commands.items()},
        stop_va=selected.stop_va, return_sentinel_va=primary.SENTINEL,
        prepared=True, runtime_ready=False, runtime_accepted=False, source_authenticated=True,
        forced_native_dispatch=True, forced_gate_result=True, forced_os_input=False, availability_mutated=False,
        primary_composition_proven=False, manual_input_proof=False, promotion_ready=False,
        pending_integrations=PENDING.copy(), limits=LIMITS.copy())
    command, inventory = _compile(packet, rendered['geometry'], sources['scripts/cdb/run_cdb_surface_dump.ps1'].data)
    packet.update(compiled_probe=command, compiled_probe_sha256=sha(command.encode('ascii')),
                  compiled_probe_format=dict(encoding='ascii', line_endings='LF', hash_scope='prepared_text_bytes',
                                             runtime_command_file=False),
                  occupied_breakpoints=inventory, compiled_probe_complete_for_runtime=False)
    need(_source_snapshots() == sources, 'widget observation source changed during preparation')
    return packet


def regenerate_packet(original, candidate, packet):
    """Reject an altered packet after one authentic widget reconstruction."""
    need(type(packet) is dict and packet.get('schema') == SCHEMA, 'exact widget barracks packet required')
    expected = build_screen_probe(original, candidate, candidate_sha256=packet['candidate_sha256'],
        stage=packet['stage'], resolution=packet['resolution'], candidate_manifest=Path(packet['candidate_manifest']['path']),
        route=packet['route']['name'], availability=packet['availability'], castle_index=packet['castle_index'],
        minimap_viewport=packet['minimap_viewport'])
    need(canonical(packet) == canonical(expected), 'widget packet differs from complete authenticated regeneration')
    return expected


def checkpoint_script(packet, name):
    """Pure native stop script only; source admission remains regenerate_packet."""
    need(type(packet) is dict and packet.get('schema') == SCHEMA and packet.get('stage') == STAGE
         and packet.get('protocol_revision') == PROTOCOL, 'exact widget checkpoint packet required')
    return primary.checkpoint_script(packet, name)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--original', type=Path, required=True)
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--candidate-manifest', type=Path, required=True)
    parser.add_argument('--resolution', choices=context_reader.RESOLUTIONS, required=True)
    parser.add_argument('--castle-index', type=int, choices=range(4), default=0)
    args = parser.parse_args()
    try:
        candidate = args.candidate.read_bytes()
        result = build_screen_probe(args.original.read_bytes(), candidate, candidate_sha256=sha(candidate), stage=STAGE,
            resolution=args.resolution, candidate_manifest=args.candidate_manifest, castle_index=args.castle_index)
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(2, f'widget barracks preparation refused: {error}\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
