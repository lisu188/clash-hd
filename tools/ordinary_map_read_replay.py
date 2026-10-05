"""Bounded raw-read retention and offline ordinary-map decoding, never runtime proof.

The caller supplies an independently authenticated candidate/process/phase,
canonical probe digest and source pins. Nothing here authenticates a process,
checks a currently live lease, launches a program, writes files or grants input,
geometry, manual or release acceptance. Persist canonical_bytes(raw_capture)
outside source control and retain its digest in the owning run's immutable index.
Replay requires that independently retained digest, not a hash from the report.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import inspect
import json
import math
from pathlib import Path
import re

import ordinary_map_input_plan as planner
import ordinary_map_observation as observer
import ordinary_map_phase_client as phase_client
import ordinary_map_pause_client as pause_client
from src.patcher import framed_army_viewport as army_geometry
from src.patcher import framed_viewport as geometry

ROOT = Path(__file__).resolve().parents[1]
BINDING_SCHEMA = 'clash95_ordinary_map_raw_binding_v1'
CAPTURE_SCHEMA = 'clash95_ordinary_map_raw_reads_v1'
REPLAY_SCHEMA = 'clash95_ordinary_map_raw_replay_v1'
PARTIAL_SCHEMA = 'clash95_ordinary_map_partial_raw_reads_v1'
SOURCE_PATHS = (
    'tools/ordinary_map_read_replay.py', 'tools/ordinary_map_observation.py',
    'tools/ordinary_map_input_plan.py', 'tools/ordinary_map_phase_client.py',
    'tools/ordinary_map_pause_client.py', 'src/patcher/framed_viewport.py',
    'src/patcher/framed_army_viewport.py',
)
MAX_CAPTURE_BYTES = 5 * 1024 * 1024
MAX_JSON_NODES = 300_000
FALSE_CLAIMS = ('live_lease_verified', 'runtime_evidence_verified', 'native_input_proof',
                'manual_input_proof', 'full_geometry_proof', 'release_evidence_verified',
                'promotion_ready')
READ_PHASES = {'initial', 'anchor_first', 'complete', 'anchor_last'}
LEASE_PHASES = {'before_initial', 'before_rereads', 'after_rereads'}


class ReplayError(ValueError):
    pass


def require(condition, reason):
    if not condition:
        raise ReplayError(reason)


def canonical_bytes(value):
    """Exact finite JSON types; booleans and numeric spellings stay distinct."""
    nodes = 0
    def inspect(item, depth=0):
        nonlocal nodes
        nodes += 1
        require(nodes <= MAX_JSON_NODES, 'structured value exceeds the node limit')
        require(depth <= 64, 'structured value exceeds the nesting limit')
        if type(item) is dict:
            require(all(type(key) is str for key in item), 'JSON object keys must be strings')
            for child in item.values():
                inspect(child, depth + 1)
        elif type(item) is list:
            for child in item:
                inspect(child, depth + 1)
        elif type(item) is float:
            require(math.isfinite(item), 'finite JSON numbers required')
        else:
            require(type(item) in (type(None), str, int, bool), 'exact JSON types required')
    inspect(value)
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=True, allow_nan=False).encode('ascii')


def digest(value):
    return sha256(canonical_bytes(value)).hexdigest()


def same(left, right):
    return canonical_bytes(left) == canonical_bytes(right)


def checked_hash(value, name):
    require(type(value) is str and re.fullmatch('[0-9a-f]{64}', value), name + ' must be a lowercase SHA-256')
    return value


def _loaded_source_paths():
    require(Path(ROOT).resolve() == Path(__file__).resolve().parents[1] and
            Path(__file__).resolve() == (ROOT / SOURCE_PATHS[0]).resolve(),
            'replay helper root or loaded path differs')
    for module, relative in ((observer, 'tools/ordinary_map_observation.py'),
                             (planner, 'tools/ordinary_map_input_plan.py'),
                             (phase_client, 'tools/ordinary_map_phase_client.py'),
                             (pause_client, 'tools/ordinary_map_pause_client.py'),
                             (geometry, 'src/patcher/framed_viewport.py'),
                             (army_geometry, 'src/patcher/framed_army_viewport.py')):
        require(Path(module.__file__).resolve() == (ROOT / relative).resolve(),
                'loaded replay module has a foreign path')
    require(observer.planner is planner and planner.FramedViewport is geometry.FramedViewport and
            planner.Rect is geometry.Rect and planner.FramedArmyViewport is army_geometry.FramedArmyViewport and
            army_geometry.FramedViewport is geometry.FramedViewport and army_geometry.Rect is geometry.Rect and
            phase_client.PauseClient is pause_client.PauseClient,
            'loaded replay dependency or viewport class is foreign')
    for cls, relative in ((planner.FramedViewport, 'src/patcher/framed_viewport.py'),
                          (planner.Rect, 'src/patcher/framed_viewport.py'),
                          (planner.FramedArmyViewport, 'src/patcher/framed_army_viewport.py'),
                          (phase_client.PauseClient, 'tools/ordinary_map_pause_client.py')):
        require(Path(inspect.getfile(cls)).resolve() == (ROOT / relative).resolve(),
                'loaded replay class has a foreign path')


def current_source_hashes():
    """Recheck the seven fixed loaded sources before and after their byte reads."""
    _loaded_source_paths()
    hashes, identities = {}, {}
    for name in SOURCE_PATHS:
        path = ROOT / name
        before = path.stat()
        data = path.read_bytes()
        after = path.stat()
        identity = lambda value: (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns)
        require(identity(before) == identity(after), 'replay source changed while reading: ' + name)
        hashes[name], identities[name] = sha256(data).hexdigest(), identity(after)
    for name in SOURCE_PATHS:
        path = ROOT / name
        before = path.stat()
        require((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) == identities[name]
                and sha256(path.read_bytes()).hexdigest() == hashes[name], 'replay source changed during snapshot: ' + name)
        after = path.stat()
        require((after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns) == identities[name],
                'replay source changed after snapshot: ' + name)
    _loaded_source_paths()
    return hashes


def _phase_contract(phase, identity, lease):
    require(type(phase) is dict and set(phase) == phase_client.ACK_KEYS,
            'exact recorded held-phase acknowledgment required')
    require(phase['schema'] == phase_client.SCHEMA, 'held-phase schema differs')
    for name in phase_client.BOOL_KEYS:
        require(type(phase[name]) is bool, 'held-phase boolean type differs: ' + name)
    for name in phase_client.INT_KEYS:
        minimum = -1 if name == 'capture_index' else 0
        require(type(phase[name]) is int and minimum <= phase[name] <= 0xffffffffffffffff,
                'held-phase integer differs: ' + name)
    require(type(phase['session_id']) is str and re.fullmatch('[0-9a-f]{32}', phase['session_id']),
            'held-phase session token differs')
    checked_hash(phase['controller_sha256'], 'held-phase controller')
    require(type(phase['binding_sha256']) is str and (phase['binding_sha256'] == '' or
            re.fullmatch('[0-9a-f]{64}', phase['binding_sha256'])), 'held-phase action binding differs')
    require(phase['status'] == 'held' and phase['paused'] is True and
            phase['phase'] in ('predispatch-before', 'predispatch-after') and
            type(phase['lease_id']) is str and re.fullmatch('[0-9a-f]{32}', phase['lease_id']) and
            phase['lease_id'] == lease['lease_id'] and
            phase['deadline_tick_ms'] > 0 and phase['request_seq'] > 0 and
            phase['human_entry_seen'] is True and phase['postpoll_seen'] is True,
            'recorded phase is not the same held native lease')
    require(0 < phase['primary_tid'] <= 0xffffffff and
            all(type(phase[name]) is type(identity[name]) and phase[name] == identity[name]
                for name in ('pid', 'creation_filetime', 'image_base')),
            'held-phase process identity differs')
    delta = identity['image_base'] - observer.PREFERRED_BASE
    require(phase['held_eip'] == 0x40B233 + delta and
            all(0x10000 <= phase[name] < planner.MAX_ADDRESS and phase[name] % 4 == 0
                for name in ('root_esp', 'held_esp')) and
            phase['held_esp'] == phase['root_esp'] - 28,
            'held-phase native instruction or stack differs')


def validate_binding(binding):
    observer.record(binding, 'schema candidate identity sequence lease phase canonical_probe_sha256 source_hashes requested_stack_indices', 'raw binding')
    require(binding['schema'] == BINDING_SCHEMA, 'raw binding schema differs')
    observer._contracts(binding['candidate'], binding['identity'], binding['sequence'], binding['lease'])
    _phase_contract(binding['phase'], binding['identity'], binding['lease'])
    checked_hash(binding['canonical_probe_sha256'], 'canonical probe')
    require(type(binding['source_hashes']) is dict and set(binding['source_hashes']) == set(SOURCE_PATHS),
            'fixed replay source inventory differs')
    for name, value in binding['source_hashes'].items():
        checked_hash(value, name)
    require(same(binding['source_hashes'], current_source_hashes()), 'authenticated replay sources have changed')
    indices = binding['requested_stack_indices']
    require(type(indices) is list and 1 <= len(indices) <= observer.STACK_COUNT and
            all(type(index) is int and 0 <= index < observer.STACK_COUNT for index in indices) and
            indices == sorted(set(indices)), 'exact sorted requested stack indices required')
    canonical_bytes(binding)


def authenticated_binding(*, candidate, identity, sequence, lease, phase,
                          canonical_probe_sha256, source_hashes, stack_indices=None):
    """Bind caller-authenticated inputs; this helper performs no authentication."""
    if stack_indices is None:
        requested = list(range(observer.STACK_COUNT))
    else:
        require(type(stack_indices) in (list, tuple) and 1 <= len(stack_indices) <= observer.STACK_COUNT,
                'bounded stack indices required')
        require(all(type(index) is int and 0 <= index < observer.STACK_COUNT for index in stack_indices)
                and len(set(stack_indices)) == len(stack_indices), 'invalid or duplicate stack index')
        requested = sorted(stack_indices)
    binding = dict(schema=BINDING_SCHEMA, candidate=deepcopy(candidate), identity=deepcopy(identity),
        sequence=sequence, lease=deepcopy(lease), phase=deepcopy(phase),
        canonical_probe_sha256=canonical_probe_sha256, source_hashes=deepcopy(source_hashes),
        requested_stack_indices=requested)
    validate_binding(binding)
    return binding


def _encoded_event(event):
    require(type(event) is dict and type(event.get('kind')) is str, 'raw event must be an object')
    encoded = deepcopy(event)
    if event['kind'] == 'read':
        require(set(event) == {'kind', 'ordinal', 'phase', 'address', 'size', 'data'}, 'raw read keys differ')
        require(type(event['data']) is bytes and len(event['data']) == event['size'], 'exact immutable read bytes required')
        encoded.pop('data')
        encoded['data_hex'] = event['data'].hex()
        encoded['sha256'] = sha256(event['data']).hexdigest()
    _validate_event(encoded)
    return encoded


def _validate_event(event):
    require(type(event) is dict, 'raw event must be an object')
    kind = event.get('kind')
    if kind == 'context':
        require(set(event) == {'kind', 'candidate', 'identity', 'sequence', 'lease', 'requested_stack_indices'},
                'context event keys differ')
    elif kind == 'lease':
        require(set(event) == {'kind', 'phase', 'lease'} and event['phase'] in LEASE_PHASES,
                'lease event keys or phase differ')
    elif kind == 'result':
        require(set(event) == {'kind', 'snapshot_sha256', 'receipt_sha256'}, 'result event keys differ')
        checked_hash(event['snapshot_sha256'], 'snapshot')
        checked_hash(event['receipt_sha256'], 'receipt')
    elif kind == 'read':
        require(set(event) == {'kind', 'ordinal', 'phase', 'address', 'size', 'data_hex', 'sha256'}, 'read event keys differ')
        observer.integer(event['ordinal'], 1, observer.MAX_READ_CALLS, 'raw read ordinal')
        observer.integer(event['address'], 0x10000, planner.MAX_ADDRESS - 1, 'raw read address')
        observer.integer(event['size'], 1, observer.MAX_SINGLE_READ, 'raw read size')
        require(event['address'] + event['size'] <= planner.MAX_ADDRESS and event['phase'] in READ_PHASES,
                'raw read range or phase differs')
        text = event['data_hex']
        require(type(text) is str and len(text) == 2 * event['size'] and re.fullmatch('[0-9a-f]+', text),
                'bounded exact lowercase raw read hex required')
        checked_hash(event['sha256'], 'raw read')
        require(sha256(bytes.fromhex(text)).hexdigest() == event['sha256'], 'raw read byte digest differs')
    else:
        raise ReplayError('unknown raw event kind')
    canonical_bytes(event)


class RawReadCapture:
    """Opt-in sink retaining at most the observer's existing total-read budget."""
    def __init__(self, binding):
        validate_binding(binding)
        self.binding = deepcopy(binding)
        self.events = []
        self.read_calls = 0
        self.read_bytes = 0

    def record(self, event):
        encoded = _encoded_event(event)
        require(len(self.events) < observer.MAX_READ_CALLS + 5, 'raw event budget exceeded')
        if encoded['kind'] == 'context':
            expected = {name: self.binding[name] for name in
                        ('candidate', 'identity', 'sequence', 'lease', 'requested_stack_indices')}
            expected['kind'] = 'context'
            require(not self.events and same(encoded, expected), 'captured observer context differs from authenticated binding')
        else:
            require(self.events and self.events[0]['kind'] == 'context', 'raw events lack the initial bound context')
        if encoded['kind'] == 'lease':
            require(same(encoded['lease'], self.binding['lease']), 'captured lease differs from authenticated binding')
        if encoded['kind'] == 'read':
            self.read_calls += 1
            self.read_bytes += encoded['size']
            require(encoded['ordinal'] == self.read_calls and self.read_calls <= observer.MAX_READ_CALLS and
                    self.read_bytes <= observer.MAX_TOTAL_BYTES, 'raw read count, order or total byte budget differs')
        self.events.append(encoded)

    def finish(self, observation):
        validate_binding(self.binding)
        require(self.events and self.events[-1]['kind'] == 'result' and
                len(self.events) == self.read_calls + 5, 'successful complete observation events required')
        receipt = observation['receipt']
        require(receipt['read_calls'] == self.read_calls and receipt['total_read_bytes'] == self.read_bytes,
                'retained read metrics differ from the observer')
        require(same(self.events[-1], dict(kind='result', snapshot_sha256=digest(observation['snapshot']),
                receipt_sha256=digest(receipt))), 'retained final result differs from observer output')
        capture = dict(schema=CAPTURE_SCHEMA, binding=deepcopy(self.binding), events=deepcopy(self.events),
            observation_sha256=digest(observation), **{name: False for name in FALSE_CLAIMS})
        require(len(canonical_bytes(capture)) <= MAX_CAPTURE_BYTES, 'serialized raw capture exceeds its bound')
        return capture


class CaptureFailure(observer.ObservationError):
    """Retain bounded failed-read diagnostics without a successful-capture schema."""
    def __init__(self, reason, collector):
        super().__init__(reason)
        self.raw_diagnostics = dict(schema=PARTIAL_SCHEMA, binding=deepcopy(collector.binding),
            events=deepcopy(collector.events), observation_complete=False,
            **{name: False for name in FALSE_CLAIMS})


def capture_observation(read_exact, *, candidate, identity, sequence, lease, check_lease,
                        phase, canonical_probe_sha256, source_hashes, stack_indices=None):
    """Capture in memory only; caller must persist raw bytes externally after preflight."""
    binding = authenticated_binding(candidate=candidate, identity=identity, sequence=sequence,
        lease=lease, phase=phase, canonical_probe_sha256=canonical_probe_sha256,
        source_hashes=source_hashes, stack_indices=stack_indices)
    collector = RawReadCapture(binding)
    try:
        observation = observer.observe(read_exact, candidate=candidate, identity=identity, sequence=sequence,
            lease=lease, check_lease=check_lease, stack_indices=stack_indices, raw_sink=collector.record)
        capture = collector.finish(observation)
    except (observer.ObservationError, ReplayError, OSError) as error:
        raise CaptureFailure(str(error), collector) from error
    return dict(observation=observation, raw_capture=capture,
                raw_capture_sha256=digest(capture), observation_sha256=digest(observation))


def decode_capture(data):
    """Read canonical JSON bytes without duplicate keys, nonfinite values or files."""
    require(type(data) is bytes and 0 < len(data) <= MAX_CAPTURE_BYTES, 'bounded immutable capture bytes required')
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, 'duplicate structured key')
            result[key] = value
        return result
    def invalid(value):
        raise ReplayError('nonfinite JSON constant: ' + value)
    try:
        value = json.loads(data.decode('ascii'), object_pairs_hook=unique, parse_constant=invalid)
    except (UnicodeError, json.JSONDecodeError, RecursionError, OverflowError) as error:
        raise ReplayError('invalid canonical raw capture JSON') from error
    require(canonical_bytes(value) == data, 'raw capture serialization is not canonical')
    return value


def replay_observation(raw_capture, observation, *, expected_binding,
                       expected_capture_sha256, expected_observation_sha256):
    """Recompute recorded consistency using externally authenticated inputs and hashes."""
    result = dict(schema=REPLAY_SCHEMA, passed=False, raw_replay_passed=False,
        recorded_lease_consistency=False, candidate_binding_matched=False,
        phase_binding_matched=False, **{name: False for name in FALSE_CLAIMS}, failures=[],
        scope='offline replay of recorded bounded bytes; no live lease, runtime, input or release authentication')
    try:
        validate_binding(expected_binding)
        checked_hash(expected_capture_sha256, 'independently retained raw capture')
        checked_hash(expected_observation_sha256, 'independently retained observation')
        require(type(raw_capture) is dict and set(raw_capture) ==
                {'schema', 'binding', 'events', 'observation_sha256', *FALSE_CLAIMS}, 'raw capture keys differ')
        require(raw_capture['schema'] == CAPTURE_SCHEMA and
                all(raw_capture[name] is False for name in FALSE_CLAIMS), 'raw capture asserts forbidden proof')
        require(same(raw_capture['binding'], expected_binding), 'raw capture differs from authenticated binding')
        events = raw_capture['events']
        require(type(events) is list and 5 < len(events) <= observer.MAX_READ_CALLS + 5, 'bounded complete raw event list required')
        calls = total = 0
        for event in events:
            _validate_event(event)
            if event['kind'] == 'read':
                calls += 1
                total += event['size']
                require(event['ordinal'] == calls and total <= observer.MAX_TOTAL_BYTES, 'raw read order or total byte budget differs')
        require(len(canonical_bytes(raw_capture)) <= MAX_CAPTURE_BYTES and
                digest(raw_capture) == expected_capture_sha256, 'immutable raw capture digest differs')
        require(digest(observation) == expected_observation_sha256 == raw_capture['observation_sha256'],
                'immutable decoded observation digest differs')
        # Freeze decoded caller objects after their bounded, typed validation.
        # The replay then consumes copies rather than a mutable report graph.
        raw_capture, observation, expected_binding = deepcopy(raw_capture), deepcopy(observation), deepcopy(expected_binding)
        events = raw_capture['events']
        cursor = 0
        def read_exact(address, size):
            require(cursor < len(events), 'raw reads were omitted')
            event = events[cursor]
            require(event['kind'] == 'read' and event['address'] == address and event['size'] == size,
                    'raw read address, size or event order differs from the fixed observer')
            return bytes.fromhex(event['data_hex'])
        def recorded_lease(lease):
            require(same(lease, expected_binding['lease']), 'recorded lease differs from authenticated context')
        def match_event(event):
            nonlocal cursor
            require(cursor < len(events) and same(_encoded_event(event), events[cursor]),
                    'raw event differs from fixed observer replay')
            cursor += 1
        replayed = observer.observe(read_exact, candidate=expected_binding['candidate'],
            identity=expected_binding['identity'], sequence=expected_binding['sequence'],
            lease=expected_binding['lease'], check_lease=recorded_lease,
            stack_indices=expected_binding['requested_stack_indices'], raw_sink=match_event)
        require(cursor == len(events), 'extra retained events remain after replay')
        require(same(replayed, observation), 'decoded state or read metadata differs from raw replay')
        require(digest(raw_capture) == expected_capture_sha256 and
                digest(observation) == expected_observation_sha256,
                'retained input bytes changed during replay')
        validate_binding(expected_binding)
        result.update(raw_replay_passed=True, recorded_lease_consistency=True,
            candidate_binding_matched=True, phase_binding_matched=True,
            read_calls=calls, total_read_bytes=total,
            unique_read_bytes=replayed['receipt']['unique_read_bytes'],
            observation_sha256=expected_observation_sha256, raw_capture_sha256=expected_capture_sha256)
    except (ReplayError, observer.ObservationError, planner.PlanError, OSError,
            TypeError, ValueError, KeyError, AttributeError, RecursionError) as error:
        result['failures'].append(str(error) or type(error).__name__)
    return result
