"""Prepare three read-only text observations; authenticate and audit their trace.

This fragment depends on the exact text candidate's loaded-image probe. It does
not launch, steer, capture, or accept a game, and never projects predecessor logs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import struct

import modal_primary_text_context as context_reader
from src.patcher import framed_modal_canvas as canvas
from src.patcher import framed_modal_primary_text as text
from src.patcher import pe_extension as pe

PROTOCOL = 'modal_primary_text_observation_v1'
SCHEMA = 'clash95_modal_primary_text_observer_v1'
EVENTS = ('ADAPTER', 'NATIVE', 'RETURN')
DEFAULT_IDS = (150, 151, 152)
FLAGS_MASK = 0xCD5  # Arithmetic and direction flags; excludes debugger RF/TF.
USER_LIMIT = 0x80000000
LIMITS = [
    'Only one source-bound text argument/call/return triplet is evaluated.',
    'The exact candidate loaded-image probe must execute before this fragment is armed.',
    'The surrounding host must authenticate the complete command file and breakpoint inventory.',
    'No route, screenshot, cleanup, input, whole-runtime, or promotion acceptance is established.',
    'Every matching, malformed, repeated, and rejected observation remains in raw_records.',
]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def _read(candidate, view, va, size):
    offset = view.file_offset(va - view.image_base, size)
    return candidate[offset:offset + size]


def _sites(candidate, manifest):
    """Only called after complete candidate/context authentication."""
    view = pe.inspect_pe(candidate)
    base, size = manifest['code_va'], manifest['code_bytes']
    entry = manifest['text_entry_vas']['quantity']
    if type(size) is not int or not 0 < size < 4096 or entry != base:
        raise ValueError('exact bounded text entry/code contract required')
    code = _read(candidate, view, base, size)
    if sha(code) != manifest['code_sha256'] or not code.startswith(b'\x9c\x60'):
        raise ValueError('emitted text code identity differs')
    call = b'\xe8' + struct.pack('<i', entry - text.TEXT_CALL - 5)
    if _read(candidate, view, text.TEXT_CALL, 5) != call:
        raise ValueError('installed quantity CALL target differs')
    if code[-7:-5] != b'\x61\x9d' or code[-5] != 0xE9 or base + size + struct.unpack('<i', code[-4:])[0] != text.TEXT_TARGET:
        raise ValueError('text tail delegation differs')
    if _read(candidate, view, text.TEXT_RETURN, 3) != b'\x83\xc4\x18':
        raise ValueError('native six-argument caller cleanup differs')
    if _read(candidate, view, text.TEXT_FORMAT, 3) != b'%d\0':
        raise ValueError('native signed quantity format differs')
    spans = []
    for va, length, digest in text.NATIVE_SPANS:
        data = _read(candidate, view, va, length)
        # The caller window contains our one installed CALL; all other bytes
        # must retain its source-pinned original digest.
        predecessor = bytearray(data)
        if va <= text.TEXT_CALL and text.TEXT_CALL + 5 <= va + length:
            predecessor[text.TEXT_CALL - va:text.TEXT_CALL - va + 5] = text.TEXT_OLD
        if sha(predecessor) != digest:
            raise ValueError('source-pinned native text span differs')
        spans.append(dict(va=va, length=length, candidate_hex=data.hex(), sha256=sha(data),
                          predecessor_sha256=digest))
    for va, data in ((base, code), (text.TEXT_CALL, call), (text.TEXT_RETURN, b'\x83\xc4\x18'),
                     (text.TEXT_FORMAT, b'%d\0')):
        spans.append(dict(va=va, length=len(data), candidate_hex=data.hex(), sha256=sha(data)))
    return dict(adapter=entry, native=text.TEXT_TARGET, return_va=text.TEXT_RETURN,
                call_va=text.TEXT_CALL, state_va=manifest['modal_state_va'], byte_spans=spans)


def _inventory(breakpoint_ids, occupied_breakpoints, sites):
    ids = tuple(breakpoint_ids)
    if len(ids) != 3 or any(type(n) is not int or not 0 <= n <= 999 for n in ids) or len(set(ids)) != 3:
        raise ValueError('three distinct bounded integer breakpoint IDs required')
    if type(occupied_breakpoints) is not dict:
        raise ValueError('explicit occupied breakpoint inventory required')
    for key, va in occupied_breakpoints.items():
        if type(key) is not int or not 0 <= key <= 999 or type(va) is not int or not 0 < va < USER_LIMIT:
            raise ValueError('invalid occupied breakpoint ID/address')
    addresses = (sites['adapter'], sites['native'], sites['return_va'])
    if len(set(addresses)) != 3 or set(ids) & set(occupied_breakpoints) or set(addresses) & set(occupied_breakpoints.values()):
        raise ValueError('text observer breakpoint ID/address collision')
    return ids, addresses


def _expressions(state, event):
    at = lambda name: f'dwo({state + canvas.STATE[name]:08x})'
    native, physical = at('native'), at('physical')
    base = 0 if event == 'RETURN' else 4
    expressions = dict(tid='@$tid', eip='@eip', esp='@esp', caller='@eip' if event == 'RETURN' else 'dwo(@esp)',
                       eax='@eax', ebx='@ebx', ecx='@ecx', edx='@edx', esi='@esi', edi='@edi', ebp='@ebp', flags='@efl')
    expressions.update((f'arg{i}', f'dwo(@esp+{base + i * 4:x})') for i in range(6))
    expressions.update(state=f'{state:08x}', phase=at('phase'), fault=at('fault'), owner_tid=at('owner_tid'),
                       root_esp=at('root_esp'), physical=physical, native=native,
                       physical_pixels=at('physical_pixels'), native_pixels=at('native_pixels'),
                       map=f'dwo({canvas.MAP:08x})', render=f'dwo({canvas.RENDER:08x})')
    for prefix, address in (('native', native), ('physical', physical)):
        expressions.update({prefix + '_width': f'wo({address})', prefix + '_height': f'wo({address}+2)',
                            prefix + '_data': f'dwo({address}+4)', prefix + '_com': f'dwo({address}+ac)',
                            prefix + '_vtable': f'dwo({address}+b8)'})
    expressions.update(primary_width=f'wo({canvas.PRIMARY:08x})', primary_height=f'wo({canvas.PRIMARY + 2:08x})',
                       primary_vtable=f'dwo({canvas.PRIMARY + 0xB8:08x})', primary_depth=f'dwo({canvas.PRIMARY + 0xD4:08x})',
                       primary_backend=f'dwo({canvas.PRIMARY + 0xBC:08x})',
                       primary_surface=f'dwo(dwo({canvas.PRIMARY + 0xBC:08x})+a4)')
    return expressions


FIELDS = tuple(_expressions(0x600000, 'ADAPTER'))
EVENT_RE = re.compile(r'MPTEXT_EVENT event=(ADAPTER|NATIVE|RETURN) ' +
                      ' '.join(rf'{name}=(?P<{name}>[0-9a-fA-F]{{8}})' for name in FIELDS))
FAILURE_RE = re.compile(r'\b(?:[A-Z0-9_]*(?:CONTRACT_FAIL|REJECT)|AV_SURFDUMP|SURFDUMP_INVALID)\b|'
                        r'syntax error|couldn.t resolve|memory access error|access violation|'
                        r'(?:first|second) chance.*c0000005|Unable to insert breakpoint|'
                        r'\bbp[0-9]+ at .* failed\b|Command file execution failed', re.I)


def _printf(message, expressions):
    slash = chr(92)
    return '.printf ' + slash + '"' + message + slash * 2 + 'n' + slash + '", ' + ', '.join(expressions)


def _compose(context, sites, *, breakpoint_ids, occupied_breakpoints):
    ids, addresses = _inventory(breakpoint_ids, occupied_breakpoints, sites)
    width, height = map(int, context['resolution'].split('x'))
    if (context['stage'] != context_reader.STAGE or context['recipe_revision'] != context_reader.REVISION
            or context['resolution'] not in context_reader.RESOLUTIONS
            or context['source_hashes'] != context['manifest']['source_hashes']):
        raise ValueError('exact text context identity required')
    loaded = [line.removeprefix('.echo ') for line in context['probe'].splitlines()
              if line.startswith(('.echo MPRIMARYTEXT_CONTRACT_PASS ', '.echo MPRIMARYTEXT_SCOPE '))]
    expected_loaded = [
        f'MPRIMARYTEXT_CONTRACT_PASS stage={context_reader.STAGE} resolution={context["resolution"]} '
        f'candidate_sha256={context["candidate_sha256"]} revision={context_reader.REVISION}',
        'MPRIMARYTEXT_SCOPE owned_modal_primary_text primary_composition_proven=false manual_input_proof=false promotion_ready=false',
    ]
    if loaded != expected_loaded or sha(context['probe'].encode('utf-8')) != context['probe_sha256']:
        raise ValueError('exact text loaded-image probe identity/markers required')
    binding = dict(stage=context['stage'], recipe_revision=context['recipe_revision'], resolution=context['resolution'],
                   candidate_sha256=context['candidate_sha256'], original_sha256=context['original_sha256'],
                   source_hashes=context['source_hashes'], context_source_sha256=context['context_source_sha256'],
                   producer_sha256=sha(Path(__file__).read_bytes()), manifest_path=context['manifest_path'],
                   manifest_sha256=context['manifest_sha256'], manifest_canonical_sha256=context['manifest_canonical_sha256'],
                   required_candidate_probe_sha256=context['probe_sha256'], sites=sites,
                   breakpoint_ids=list(ids), occupied_breakpoints={str(k): v for k, v in sorted(occupied_breakpoints.items())})
    binding_hash = sha(context_reader.canonical_json(binding).encode('utf-8'))
    contract = (f'MPTEXT_OBSERVER_CONTRACT stage={context["stage"]} resolution={context["resolution"]} '
                f'candidate_sha256={context["candidate_sha256"]} revision={context["recipe_revision"]} '
                f'protocol={PROTOCOL} binding_sha256={binding_hash} runtime_acceptance=0')
    lines, commands = ['.echo ' + contract], {}
    for bp, va, event in zip(ids, addresses, EVENTS):
        expr = _expressions(sites['state_va'], event)
        message = 'MPTEXT_EVENT event=' + event + ' ' + ' '.join(name + '=%08x' for name in FIELDS)
        observation = _printf(message, expr.values())
        # These range checks prevent obviously invalid nested header reads.
        # Bad state emits an explicit failure, never a fabricated event/pass.
        checks = []
        for pointer, extent in ((expr['native'], 0xBC), (expr['physical'], 0xBC), (expr['primary_backend'], 0xA8)):
            checks.extend((f'({pointer} >= 00010000)', f'({pointer} <= {USER_LIMIT - extent:08x})'))
        rejected = _printf(f'MPTEXT_OBSERVER_REJECT event={event} reason=header_pointer tid=%08x eip=%08x esp=%08x',
                           ('@$tid', '@eip', '@esp'))
        body = '.if (' + ' & '.join(checks) + ') { ' + observation + ' } .else { ' + rejected + ' }; gc'
        # Other formatter callers are outside this source-pinned call's scope.
        # Every invocation whose return matches is retained, including duplicates.
        if event == 'NATIVE':
            body = f'.if (dwo(@esp) == {text.TEXT_RETURN:08x}) {{ {body} }} .else {{ gc }}'
        commands[str(bp)] = dict(va=va, event=event, body=body)
        lines.extend((f'bp{bp} {va:08x} "{body}"', f'bd {bp}'))
    # Native DbgEng ExecuteCommandFile requires the Windows CRLF transport;
    # LF-only exports can truncate command prefixes before parsing them.
    fragment = '\r\n'.join(lines) + '\r\n'
    if any(len(line.encode('ascii')) >= 4096 for line in fragment.splitlines()):
        raise ValueError('text observer exceeds CDB4096-byte line limit')
    return dict(schema=SCHEMA, protocol_revision=PROTOCOL, prepared=True, binding=binding,
                binding_sha256=binding_hash, contract_line=contract, fragment=fragment,
                fragment_sha256=sha(fragment.encode('ascii')), breakpoint_commands=commands,
                arm_command='be ' + ' '.join(map(str, ids)), disarm_command='bd ' + ' '.join(map(str, ids)),
                expected_loaded_records=loaded, required_candidate_probe=context['probe'],
                expected_original_args=[text.TEXT_LEFT, text.TEXT_RIGHT, text.TEXT_Y, text.TEXT_ALIGN, text.TEXT_FORMAT],
                expected_translated_args=[text.TEXT_LEFT + (width - 640) // 2, text.TEXT_RIGHT + (width - 640) // 2,
                                          text.TEXT_Y + (height - 480) // 2, text.TEXT_ALIGN, text.TEXT_FORMAT],
                runtime_accepted=False, manual_input_proof=False, promotion_ready=False, limits=LIMITS)


def build_fragment(original, candidate, candidate_manifest, *, occupied_breakpoints, breakpoint_ids=DEFAULT_IDS):
    """Authenticate first; this API has no supplied-context or rebuild override."""
    source_before = sha(Path(__file__).read_bytes())
    context = context_reader.load_context(original, candidate, Path(candidate_manifest))
    packet = _compose(context, _sites(candidate, context['manifest']), breakpoint_ids=breakpoint_ids,
                      occupied_breakpoints=occupied_breakpoints)
    if sha(Path(__file__).read_bytes()) != source_before or packet['binding']['producer_sha256'] != source_before:
        raise ValueError('text observer source changed during preparation')
    return packet


def evaluate_sequence(log, packet):
    """Pure sequence diagnosis only; callers cannot turn this into source proof."""
    failures, raw, events = [], [], []
    def fail(message, line=None):
        failures.append((f'line {line}: ' if line is not None else '') + message)
    try:
        if type(log) is not str or type(packet) is not dict or packet.get('schema') != SCHEMA or packet.get('protocol_revision') != PROTOCOL:
            raise ValueError('exact observer packet and text log required')
        binding, sites = packet['binding'], packet['binding']['sites']
        if binding['stage'] != context_reader.STAGE or binding['recipe_revision'] != context_reader.REVISION or binding['resolution'] not in context_reader.RESOLUTIONS:
            raise ValueError('exact text stage/revision/resolution required')
        if sha(context_reader.canonical_json(binding).encode()) != packet['binding_sha256']:
            raise ValueError('observer binding hash differs')
        width, height = map(int, binding['resolution'].split('x'))
        if any(type(binding.get(key)) is not str or re.fullmatch(r'[0-9a-f]{64}', binding[key]) is None
               for key in ('candidate_sha256', 'original_sha256', 'producer_sha256', 'context_source_sha256')):
            raise ValueError('full observer source/candidate SHA256 identities required')
        expected_original = [text.TEXT_LEFT, text.TEXT_RIGHT, text.TEXT_Y, text.TEXT_ALIGN, text.TEXT_FORMAT]
        expected_translated = [text.TEXT_LEFT + (width - 640) // 2, text.TEXT_RIGHT + (width - 640) // 2,
                               text.TEXT_Y + (height - 480) // 2, text.TEXT_ALIGN, text.TEXT_FORMAT]
        expected_loaded = [
            f'MPRIMARYTEXT_CONTRACT_PASS stage={binding["stage"]} resolution={binding["resolution"]} '
            f'candidate_sha256={binding["candidate_sha256"]} revision={binding["recipe_revision"]}',
            'MPRIMARYTEXT_SCOPE owned_modal_primary_text primary_composition_proven=false manual_input_proof=false promotion_ready=false',
        ]
        expected_contract = (f'MPTEXT_OBSERVER_CONTRACT stage={binding["stage"]} resolution={binding["resolution"]} '
                             f'candidate_sha256={binding["candidate_sha256"]} revision={binding["recipe_revision"]} '
                             f'protocol={PROTOCOL} binding_sha256={packet["binding_sha256"]} runtime_acceptance=0')
        if (packet['expected_original_args'] != expected_original or packet['expected_translated_args'] != expected_translated
                or packet['expected_loaded_records'] != expected_loaded or packet['contract_line'] != expected_contract
                or sites['native'] != text.TEXT_TARGET or sites['return_va'] != text.TEXT_RETURN or sites['call_va'] != text.TEXT_CALL):
            raise ValueError('observer native geometry/startup contract differs')
    except (ValueError, KeyError, TypeError) as error:
        return dict(sequence_passed=False, source_authenticated=False, text_call_observed=False,
                    failures=[str(error)], raw_records=raw, runtime_accepted=False, limits=LIMITS)
    startup = []
    for number, line in enumerate(log.splitlines(), 1):
        recorded = False
        if re.search(r'(?:MPTEXT_|MPRIMARYTEXT_)', line, re.I):
            record = dict(line=number, text=line, values=None)
            raw.append(record)
            recorded = True
            match = EVENT_RE.fullmatch(line)
            if match:
                record['event'] = match[1]
                record['values'] = {k: int(v, 16) for k, v in match.groupdict().items()}
                events.append(record)
            elif line in packet['expected_loaded_records'] or line == packet['contract_line']:
                startup.append((number, line))
            else:
                fail('unknown, malformed, prefixed, or rejected text observation', number)
        legacy_startup = re.search(r'(?<!\S)(?:MPRIMARY|SLOTS|ARMY|COMPLETEHD|MCANVAS)_CONTRACT_PASS\b', line, re.I)
        tile_startup = re.search(r'(?<!\S)PTILE_CONTRACT_PASS\b', line, re.I)
        expected_tile = (f'PTILE_CONTRACT_PASS stage={binding["stage"]} resolution={binding["resolution"]} '
                         f'candidate_sha256={binding["candidate_sha256"]}')
        mixed_startup = legacy_startup or (tile_startup and line != expected_tile)
        if FAILURE_RE.search(line) or mixed_startup:
            if mixed_startup:
                fail('mixed predecessor or mismatched candidate startup record', number)
            fail('retained runtime/probe/debugger failure', number)
            if not recorded:
                raw.append(dict(line=number, text=line, values=None, kind='external_failure'))
    if [line for _, line in startup] != packet['expected_loaded_records'] + [packet['contract_line']]:
        fail('loaded text identity/scope and observer contract are missing, duplicated, or reordered')
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
        if any(returned[key] != native[key] for key in ('ebx', 'ecx', 'edx', 'ebp')):
            fail('native formatter did not preserve its saved registers', events[2]['line'])
    quantity = events[0]['values']['arg5'] if events else None
    signed = quantity - 0x100000000 if quantity is not None and quantity & 0x80000000 else quantity
    return dict(sequence_passed=not failures, source_authenticated=False, text_call_observed=False,
                failures=failures, raw_records=raw, observed_event_count=len(events), signed_quantity=signed,
                runtime_accepted=False, manual_input_proof=False, promotion_ready=False, limits=LIMITS)


def validate_trace(log, original, candidate, candidate_manifest, packet, fragment, *, occupied_breakpoints, breakpoint_ids=DEFAULT_IDS):
    """Bind a diagnosis to the exact new context and generated observer source."""
    expected = build_fragment(original, candidate, candidate_manifest, occupied_breakpoints=occupied_breakpoints,
                              breakpoint_ids=breakpoint_ids)
    if context_reader.canonical_json(packet) != context_reader.canonical_json(expected) or fragment != expected['fragment']:
        raise ValueError('text observer packet or fragment differs from exact regeneration')
    result = evaluate_sequence(log, expected)
    result.update(source_authenticated=True, text_call_observed=result['sequence_passed'],
                  candidate_sha256=expected['binding']['candidate_sha256'], stage=expected['binding']['stage'],
                  recipe_revision=expected['binding']['recipe_revision'], resolution=expected['binding']['resolution'],
                  log_sha256=sha(log.encode('utf-8')), observer_binding_sha256=expected['binding_sha256'])
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--original', type=Path, required=True)
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--candidate-manifest', type=Path, required=True)
    parser.add_argument('--occupied-breakpoints', type=Path, required=True, help='JSON object mapping explicit breakpoint IDs to VAs; {} when none')
    parser.add_argument('--breakpoint-ids', nargs=3, type=int, default=DEFAULT_IDS)
    parser.add_argument('--packet', type=Path)
    parser.add_argument('--fragment', type=Path)
    parser.add_argument('--log', type=Path)
    args = parser.parse_args()
    try:
        inventory = context_reader.parse_manifest(args.occupied_breakpoints.read_bytes())
        if any(re.fullmatch(r'0|[1-9][0-9]{0,2}', key) is None for key in inventory):
            raise ValueError('canonical decimal occupied breakpoint IDs required')
        inventory = {int(key): value for key, value in inventory.items()}
        original, candidate = args.original.read_bytes(), args.candidate.read_bytes()
        if args.log is None and args.packet is None and args.fragment is None:
            result = build_fragment(original, candidate, args.candidate_manifest, occupied_breakpoints=inventory, breakpoint_ids=args.breakpoint_ids)
        elif args.log is not None and args.packet is not None and args.fragment is not None:
            result = validate_trace(args.log.read_text(encoding='utf-8'), original, candidate, args.candidate_manifest,
                                    context_reader.parse_manifest(args.packet.read_bytes()), args.fragment.read_bytes().decode('ascii'),
                                    occupied_breakpoints=inventory, breakpoint_ids=args.breakpoint_ids)
        else:
            raise ValueError('evaluation requires packet, fragment, and log together')
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(2, f'text observation refused: {error}\n')
    print(json.dumps(result, indent=2))
    return 0 if 'sequence_passed' not in result or result['sequence_passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
