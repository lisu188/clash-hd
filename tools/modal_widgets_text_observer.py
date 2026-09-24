"""Prepare and diagnose the actual widgets-v1 quantity argument/call/return.

Pure byte/site/expression helpers are imported from the frozen text observer.
The bounded sequence ABI checks below are copied from that source (pinned in
PINS), with an independent MWTEXT namespace and genuine widget admission.
No predecessor context or log is relabeled; no debugger or game is launched.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re

import modal_primary_text_observer as inherited
import modal_widgets_context as context_reader

ROOT = Path(__file__).resolve().parents[1]
STAGE, REVISION = context_reader.STAGE, context_reader.REVISION
PROTOCOL = 'modal_widgets_text_observation_v1'
SCHEMA = 'clash95_modal_widgets_text_observer_v1'
EVENTS, DEFAULT_IDS = inherited.EVENTS, inherited.DEFAULT_IDS
FIELDS, FLAGS_MASK, USER_LIMIT = inherited.FIELDS, inherited.FLAGS_MASK, inherited.USER_LIMIT
canvas, text = inherited.canvas, inherited.text
_sites, _inventory, _expressions, _printf = inherited._sites, inherited._inventory, inherited._expressions, inherited._printf
sha = context_reader.sha
PINS = {
    'tools/modal_primary_text_observer.py': 'b92fbe6fce1c73301ed53873c6739a3b3408662c8f29021abcde9482ff0d491d',
    'tools/modal_widgets_context.py': 'fd211a1eaee64622c02e370adb5e1326d3f27ae0ad3f36fa56801b6177ab3d42',
    **context_reader.AUTHENTICATION_SOURCES, **context_reader.FROZEN_SOURCES,
}
SOURCES = frozenset((*context_reader.RECIPE_SOURCE_PATHS, *PINS, 'tools/modal_widgets_text_observer.py'))
LIMITS = [
    'Only one source-bound widget quantity argument/call/return triplet is evaluated.',
    'Actual widget PTILE and MWIDGETS loaded-image checks must execute before the three disabled observers are armed.',
    'The surrounding host must authenticate its whole command file and occupied breakpoint inventory.',
    'No route, screenshot, cleanup, input, whole-runtime, or promotion acceptance is established.',
    'Every matching, malformed, repeated, rejected and predecessor observation remains in raw_records.',
]
EVENT_RE = re.compile(r'MWTEXT_EVENT event=(ADAPTER|NATIVE|RETURN) ' +
                     ' '.join(rf'{name}=(?P<{name}>[0-9a-fA-F]{{8}})' for name in FIELDS))
RESERVED_RE = re.compile(r'MWTEXT_|MWIDGETS_|PTILE_(?:CONTRACT_|SCOPE)|MPTEXT_|MPRIMARYTEXT_|'
                         r'(?:MPRIMARY|SLOTS|ARMY|COMPLETEHD|MCANVAS)_(?:CONTRACT_PASS|SCOPE)', re.I)
FAILURE_RE = inherited.FAILURE_RE


def need(condition, message):
    if not condition:
        raise ValueError(message)


def canonical(value):
    try:
        return context_reader.canonical_json(value)
    except RecursionError as error:
        raise ValueError('observer JSON nesting exceeds parser capacity') from error


def parse_object(raw):
    return context_reader.parse_manifest(raw)


def _source_snapshots():
    for module, name in ((inherited, 'tools/modal_primary_text_observer.py'),
                         (context_reader, 'tools/modal_widgets_context.py'),
                         (canvas, 'src/patcher/framed_modal_canvas.py'),
                         (text, 'src/patcher/framed_modal_primary_text.py'),
                         (inherited.pe, 'src/patcher/pe_extension.py')):
        need(Path(module.__file__).resolve() == ROOT / name, 'canonical observer dependency location required: ' + name)
    rows = {}
    for name in sorted(SOURCES):
        path = ROOT / name
        need(path.resolve(strict=True) == path, 'observer dependency path aliases another location: ' + name)
        rows[name] = context_reader._snapshot(path)
    need(len({row.stamp[:2] for row in rows.values()}) == len(rows), 'observer dependencies alias one file identity')
    for name, digest in PINS.items():
        need(sha(rows[name].data) == digest, 'frozen widget text observation source changed: ' + name)
    return rows


def _loaded(stage, resolution, digest):
    return [f'MWIDGETS_CONTRACT_PASS stage={stage} resolution={resolution} candidate_sha256={digest} revision={REVISION}',
            'MWIDGETS_SCOPE owned_modal_widget_bounds primary_composition_proven=false manual_input_proof=false promotion_ready=false',
            'ARMY_SCOPE own_player_0_to_3_native_size_panel manual_input_proof=false promotion_ready=false',
            f'PTILE_CONTRACT_PASS stage={stage} resolution={resolution} candidate_sha256={digest}',
            'PTILE_SCOPE guarded_map_only manual_input_proof=false promotion_ready=false']


def _compose(context, sites, sources, *, breakpoint_ids, occupied_breakpoints):
    ids, addresses = _inventory(breakpoint_ids, occupied_breakpoints, sites)
    need(context['stage'] == STAGE and context['recipe_revision'] == REVISION
         and context['resolution'] in context_reader.RESOLUTIONS, 'exact widget context identity required')
    recipe_hashes = {name: sha(sources[name].data) for name in context_reader.RECIPE_SOURCE_PATHS}
    need(canonical(context['source_hashes']) == canonical(recipe_hashes)
         and canonical(context['manifest']['source_hashes']) == canonical(recipe_hashes), 'complete current widget recipe sources required')
    need(canonical(context['authentication_source_hashes']) == canonical(context_reader.AUTHENTICATION_SOURCES)
         and context['context_source_sha256'] == sha(sources['tools/modal_widgets_context.py'].data),
         'widget authentication source binding differs')
    ancestor = context['text_context']
    need(ancestor['stage'] == STAGE.removesuffix('-modalwidgets-validation') + '-modalprimarytext-validation'
         and ancestor['recipe_revision'] == 'owned_modal_primary_text_v1'
         and ancestor['resolution'] == context['resolution']
         and canonical(ancestor) == canonical(context['manifest']['base_candidate'])
         and sites['state_va'] == context['manifest']['modal_state_va'] == context['owner_context']['state_va'],
         'genuine inherited text/owner context required')
    loaded = [line.removeprefix('.echo ') for line in context['probe'].splitlines()
              if line.startswith('.echo ') and RESERVED_RE.search(line)]
    expected_loaded = _loaded(STAGE, context['resolution'], context['candidate_sha256'])
    need(loaded == expected_loaded and sha(context['probe'].encode('utf-8')) == context['probe_sha256'],
         'exact widget PTILE/loaded-image probe identity required')
    width, height = map(int, context['resolution'].split('x'))
    binding = dict(stage=STAGE, recipe_revision=REVISION, resolution=context['resolution'],
        candidate_sha256=context['candidate_sha256'], original_sha256=context['original_sha256'],
        source_hashes=recipe_hashes, authentication_source_hashes=dict(context['authentication_source_hashes']),
        preparation_source_hashes={name: sha(row.data) for name, row in sources.items()},
        context_source_sha256=context['context_source_sha256'], producer_sha256=sha(sources['tools/modal_widgets_text_observer.py'].data),
        inherited_text_identity={key: ancestor[key] for key in ('stage', 'recipe_revision', 'resolution', 'candidate_sha256')},
        manifest_path=context['manifest_path'], manifest_sha256=context['manifest_sha256'],
        manifest_canonical_sha256=context['manifest_canonical_sha256'], required_candidate_probe_sha256=context['probe_sha256'],
        sites=sites, breakpoint_ids=list(ids), occupied_breakpoints={str(k): v for k, v in sorted(occupied_breakpoints.items())})
    binding_hash = sha(canonical(binding).encode('utf-8'))
    contract = (f'MWTEXT_OBSERVER_CONTRACT stage={STAGE} resolution={context["resolution"]} '
                f'candidate_sha256={context["candidate_sha256"]} revision={REVISION} '
                f'protocol={PROTOCOL} binding_sha256={binding_hash} runtime_acceptance=0')
    lines, commands = ['.echo ' + contract], {}
    for bp, va, event in zip(ids, addresses, EVENTS):
        expr = _expressions(sites['state_va'], event)
        observation = _printf('MWTEXT_EVENT event=' + event + ' ' + ' '.join(name + '=%08x' for name in FIELDS), expr.values())
        checks = []
        for pointer, extent in ((expr['native'], 0xBC), (expr['physical'], 0xBC), (expr['primary_backend'], 0xA8)):
            checks.extend((f'({pointer} >= 00010000)', f'({pointer} <= {USER_LIMIT - extent:08x})'))
        rejected = _printf(f'MWTEXT_OBSERVER_REJECT event={event} reason=header_pointer tid=%08x eip=%08x esp=%08x',
                           ('@$tid', '@eip', '@esp'))
        body = '.if (' + ' & '.join(checks) + ') { ' + observation + ' } .else { ' + rejected + ' }; gc'
        if event == 'NATIVE':
            body = f'.if (dwo(@esp) == {text.TEXT_RETURN:08x}) {{ {body} }} .else {{ gc }}'
        commands[str(bp)] = dict(va=va, event=event, body=body)
        lines.extend((f'bp{bp} {va:08x} "{body}"', f'bd {bp}'))
    fragment = '\r\n'.join(lines) + '\r\n'
    need(all(len(line.encode('ascii')) < 4096 for line in fragment.splitlines()), 'widget text observer exceeds CDB4096-byte line limit')
    return dict(schema=SCHEMA, protocol_revision=PROTOCOL, prepared=True, binding=binding,
        binding_sha256=binding_hash, contract_line=contract, fragment=fragment, fragment_sha256=sha(fragment.encode('ascii')),
        fragment_encoding='ascii', fragment_line_endings='CRLF', breakpoint_commands=commands,
        arm_command='be ' + ' '.join(map(str, ids)), disarm_command='bd ' + ' '.join(map(str, ids)),
        expected_loaded_records=loaded, required_candidate_probe=context['probe'],
        expected_original_args=[text.TEXT_LEFT, text.TEXT_RIGHT, text.TEXT_Y, text.TEXT_ALIGN, text.TEXT_FORMAT],
        expected_translated_args=[text.TEXT_LEFT + (width - 640) // 2, text.TEXT_RIGHT + (width - 640) // 2,
                                  text.TEXT_Y + (height - 480) // 2, text.TEXT_ALIGN, text.TEXT_FORMAT],
        runtime_ready=False, runtime_accepted=False, manual_input_proof=False, promotion_ready=False, limits=LIMITS.copy())


def build_fragment(original, candidate, candidate_manifest, *, occupied_breakpoints, breakpoint_ids=DEFAULT_IDS):
    """Authenticate the real widget once; callers cannot supply trusted contexts."""
    before = _source_snapshots()
    context = context_reader.load_context(original, candidate, Path(candidate_manifest))
    packet = _compose(context, _sites(candidate, context['text_context']), before,
                      breakpoint_ids=breakpoint_ids, occupied_breakpoints=occupied_breakpoints)
    need(_source_snapshots() == before, 'widget text observation source changed during preparation')
    return packet


def _raw_records(log):
    records = []
    if type(log) is str:
        for number, line in enumerate(log.splitlines(), 1):
            if RESERVED_RE.search(line) or FAILURE_RE.search(line):
                record = dict(line=number, text=line, values=None)
                match = EVENT_RE.fullmatch(line)
                if match:
                    record.update(event=match[1], values={key: int(value, 16) for key, value in match.groupdict().items()})
                records.append(record)
    return records


def _failure(raw, message):
    return dict(sequence_passed=False, source_authenticated=False, text_call_observed=False,
                failures=[message], raw_records=raw, observed_event_count=sum('event' in row for row in raw),
                runtime_accepted=False, manual_input_proof=False, promotion_ready=False, limits=LIMITS.copy())


def evaluate_sequence(log, packet):
    """Pure bounded diagnosis; even a passing sequence is not source proof."""
    raw = _raw_records(log)
    failures, events, startup = [], [], []
    def fail(message, line=None):
        failures.append((f'line {line}: ' if line is not None else '') + message)
    try:
        need(type(log) is str and type(packet) is dict and packet.get('schema') == SCHEMA
             and packet.get('protocol_revision') == PROTOCOL, 'exact widget observer packet and text log required')
        binding, sites = packet['binding'], packet['binding']['sites']
        need(binding['stage'] == STAGE and binding['recipe_revision'] == REVISION
             and binding['resolution'] in context_reader.RESOLUTIONS, 'exact widget stage/revision/resolution required')
        need(sha(canonical(binding).encode()) == packet['binding_sha256'], 'observer binding hash differs')
        width, height = map(int, binding['resolution'].split('x'))
        need(all(type(binding.get(key)) is str and re.fullmatch(r'[0-9a-f]{64}', binding[key])
                 for key in ('candidate_sha256', 'original_sha256', 'producer_sha256', 'context_source_sha256')),
             'full observer source/candidate SHA256 identities required')
        need(all(type(sites[key]) is int and 0x10000 <= sites[key] < USER_LIMIT
                 for key in ('adapter', 'native', 'return_va', 'call_va', 'state_va')), 'bounded native text sites required')
        expected_original = [text.TEXT_LEFT, text.TEXT_RIGHT, text.TEXT_Y, text.TEXT_ALIGN, text.TEXT_FORMAT]
        expected_translated = [text.TEXT_LEFT + (width - 640) // 2, text.TEXT_RIGHT + (width - 640) // 2,
                               text.TEXT_Y + (height - 480) // 2, text.TEXT_ALIGN, text.TEXT_FORMAT]
        expected_loaded = _loaded(STAGE, binding['resolution'], binding['candidate_sha256'])
        expected_contract = (f'MWTEXT_OBSERVER_CONTRACT stage={STAGE} resolution={binding["resolution"]} '
                             f'candidate_sha256={binding["candidate_sha256"]} revision={REVISION} '
                             f'protocol={PROTOCOL} binding_sha256={packet["binding_sha256"]} runtime_acceptance=0')
        need(canonical(packet['expected_original_args']) == canonical(expected_original)
             and canonical(packet['expected_translated_args']) == canonical(expected_translated)
             and packet['expected_loaded_records'] == expected_loaded and packet['contract_line'] == expected_contract
             and sites['native'] == text.TEXT_TARGET and sites['return_va'] == text.TEXT_RETURN and sites['call_va'] == text.TEXT_CALL,
             'widget observer native geometry/startup contract differs')
    except (ValueError, KeyError, TypeError, RecursionError) as error:
        return _failure(raw, str(error))
    for record in raw:
        number, line = record['line'], record['text']
        if 'event' in record:
            events.append(record)
        elif line in expected_loaded or line == expected_contract:
            startup.append((number, line))
        else:
            fail('unknown, malformed, prefixed, rejected or predecessor observation', number)
        if FAILURE_RE.search(line):
            fail('retained runtime/probe/debugger failure', number)
    if [line for _, line in startup] != expected_loaded + [expected_contract]:
        fail('widget PTILE/loaded identity/scope and observer contract are missing, duplicated, or reordered')
    if [record['event'] for record in events] != list(EVENTS):
        fail('text events are missing, duplicated, or reordered')
    if startup and events and startup[-1][0] >= events[0]['line']:
        fail('loaded/observer contracts must precede all text events')
    if len(events) == 3 and [record['event'] for record in events] == list(EVENTS):
        original, native, returned = (record['values'] for record in events)
        entry_esp, tid = original['esp'], original['tid']
        state_keys = [name for name in FIELDS if name not in {'tid', 'eip', 'esp', 'caller', 'eax', 'ebx', 'ecx', 'edx', 'esi', 'edi', 'ebp', 'flags', *(f'arg{i}' for i in range(6))}]
        for record, va, esp in zip(events, (sites['adapter'], sites['native'], sites['return_va']), (entry_esp, entry_esp, entry_esp + 4)):
            value = record['values']
            def require(condition, message):
                if not condition: fail(message, record['line'])
            require(value['eip'] == va and value['esp'] == esp and value['caller'] == text.TEXT_RETURN,
                    'native call site/stack/return identity differs')
            require(0 < tid == value['tid'] == value['owner_tid'] and 0x10000 <= esp < USER_LIMIT - 28 and esp % 4 == 0,
                    'thread/owned call stack differs')
            require(value['state'] == sites['state_va'] and value['phase'] == 1 and value['fault'] == 0,
                    'owned native canvas is inactive or faulted')
            require(value['ebp'] == canvas.PRIMARY and value['render'] == canvas.PRIMARY and value['map'] == value['native'],
                    'native caller EBP/render/map context differs')
            require(value['root_esp'] % 4 == 0 and esp < value['root_esp'] < USER_LIMIT and value['root_esp'] - esp < 0x10000,
                    'owned root stack is invalid')
            require((value['native_width'], value['native_height'], value['physical_width'], value['physical_height']) == (640, 480, width, height),
                    'owned native/physical surface geometry differs')
            require(value['native_vtable'] == value['physical_vtable'] == canvas.MEMORY_VTABLE and value['native_com'] == 0,
                    'owned canvas vtable/COM ownership differs')
            require(value['native_data'] == value['native_pixels'] and value['physical_data'] == value['physical_pixels'],
                    'owned pixel pointer identity differs')
            require(value['native'] != value['physical'] and all(0x10000 <= value[key] <= USER_LIMIT - 0xBC for key in ('native', 'physical')),
                    'owned header identity differs')
            n, p = value['native_pixels'], value['physical_pixels']
            require(0x10000 <= n <= USER_LIMIT - 307200 and 0x10000 <= p <= USER_LIMIT - width * height
                    and (n + 307200 <= p or p + width * height <= n), 'owned pixel ranges overlap or wrap')
            require((value['primary_width'], value['primary_height'], value['primary_depth'], value['primary_vtable']) ==
                    (width, height, 8, canvas.PRIMARY_VTABLE) and 0x10000 <= value['primary_backend'] <= USER_LIMIT - 0xA8
                    and 0x10000 <= value['primary_surface'] < USER_LIMIT, 'native primary backend/geometry differs')
            require(all(value[key] == original[key] for key in state_keys), 'owned state changed during the text call')
        if [original[f'arg{i}'] for i in range(5)] != packet['expected_original_args']:
            fail('original six-argument quantity call shape differs', events[0]['line'])
        for record in events[1:]:
            value = record['values']
            if [value[f'arg{i}'] for i in range(5)] != packet['expected_translated_args'] or value['arg5'] != original['arg5']:
                fail('translated coordinates or unchanged alignment/format/signed quantity differ', record['line'])
        if any(native[key] != original[key] for key in ('eax', 'ebx', 'ecx', 'edx', 'esi', 'edi', 'ebp')) or (native['flags'] ^ original['flags']) & FLAGS_MASK:
            fail('adapter changed incoming native registers or arithmetic/direction flags', events[1]['line'])
        if any(returned[key] != native[key] for key in ('ebx', 'esi', 'edi', 'ebp')):
            fail('native formatter did not preserve its saved registers', events[2]['line'])
    quantity = events[0]['values']['arg5'] if events else None
    signed = quantity - 0x100000000 if quantity is not None and quantity & 0x80000000 else quantity
    return dict(sequence_passed=not failures, source_authenticated=False, text_call_observed=False,
                failures=failures, raw_records=raw, observed_event_count=len(events), signed_quantity=signed,
                runtime_accepted=False, manual_input_proof=False, promotion_ready=False, limits=LIMITS.copy())


class AdmissionError(ValueError):
    """Fail closed while retaining unmodified raw diagnostics at public boundaries."""
    def __init__(self, message, diagnostic):
        super().__init__(message)
        self.diagnostic = diagnostic


def validate_trace(log, original, candidate, candidate_manifest, packet, fragment, *, occupied_breakpoints, breakpoint_ids=DEFAULT_IDS):
    """Regenerate the whole source-bound packet/CRLF fragment before acceptance."""
    try:
        need(type(log) is str, 'text log required')
        expected = build_fragment(original, candidate, candidate_manifest, occupied_breakpoints=occupied_breakpoints,
                                  breakpoint_ids=breakpoint_ids)
        need(canonical(packet) == canonical(expected) and type(fragment) is str and fragment == expected['fragment'],
             'widget text observer packet or fragment differs from exact regeneration')
    except (OSError, ValueError, KeyError, TypeError, RecursionError) as error:
        diagnostic = evaluate_sequence(log, packet)
        diagnostic.update(sequence_passed=False, source_authenticated=False, text_call_observed=False)
        diagnostic['failures'].insert(0, 'source admission failed: ' + str(error))
        raise AdmissionError(str(error), diagnostic) from error
    result = evaluate_sequence(log, expected)
    result.update(source_authenticated=True, text_call_observed=result['sequence_passed'],
                  candidate_sha256=expected['binding']['candidate_sha256'], stage=STAGE,
                  recipe_revision=REVISION, resolution=expected['binding']['resolution'],
                  log_sha256=sha(log.encode('utf-8')), observer_binding_sha256=expected['binding_sha256'])
    return result


def parse_inventory(raw):
    inventory = parse_object(raw)
    need(all(re.fullmatch(r'0|[1-9][0-9]{0,2}', key) for key in inventory), 'canonical decimal occupied breakpoint IDs required')
    return {int(key): value for key, value in inventory.items()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--original', type=Path, required=True)
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--candidate-manifest', type=Path, required=True)
    parser.add_argument('--occupied-breakpoints', type=Path, required=True)
    parser.add_argument('--breakpoint-ids', nargs=3, type=int, default=DEFAULT_IDS)
    parser.add_argument('--packet', type=Path)
    parser.add_argument('--fragment', type=Path)
    parser.add_argument('--log', type=Path)
    args = parser.parse_args()
    log = None
    try:
        if args.log is not None:
            log = args.log.read_bytes().decode('utf-8')
        inventory = parse_inventory(args.occupied_breakpoints.read_bytes())
        original, candidate = args.original.read_bytes(), args.candidate.read_bytes()
        if args.log is None and args.packet is None and args.fragment is None:
            result = build_fragment(original, candidate, args.candidate_manifest,
                                    occupied_breakpoints=inventory, breakpoint_ids=args.breakpoint_ids)
        elif args.log is not None and args.packet is not None and args.fragment is not None:
            result = validate_trace(log, original, candidate, args.candidate_manifest,
                                    parse_object(args.packet.read_bytes()), args.fragment.read_bytes().decode('ascii'),
                                    occupied_breakpoints=inventory, breakpoint_ids=args.breakpoint_ids)
        else:
            raise ValueError('evaluation requires packet, fragment, and log together')
    except AdmissionError as error:
        result = error.diagnostic
    except (OSError, ValueError, KeyError, TypeError) as error:
        if log is None:
            parser.exit(2, f'widget text observation refused: {error}\n')
        result = _failure(_raw_records(log), 'source admission failed: ' + str(error))
    print(json.dumps(result, indent=2))
    return 0 if 'sequence_passed' not in result or result['sequence_passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
