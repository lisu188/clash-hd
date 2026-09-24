"""Read fresh text-stage primary/cursor query ledgers without running a target.

The outer host supplies independently authenticated expectations. This reader
proves only that the retained files and query/read sequence match them; it does
not authenticate a live process, candidate source, trace semantics or pixels.
Historical primary-v1/v2 receipts are deliberately not admitted here.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
from pathlib import Path, PureWindowsPath
import re

import modal_slots_primary_capture as frozen

ROOT = Path(__file__).resolve().parents[1]
REVISION = 'modal_primary_checkpoint_ledger_v1'
SCHEME = 'primary_virtual_query_ledger_v1'
STAGE = ('gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-'
         'presentbounds-minimapright-dynvswitch-completehd-modalprimarytext-validation')
RECIPE = 'owned_modal_primary_text_v1'
RESOLUTIONS = ('800x600', '1024x768', '1280x720', '1280x960', '1920x1080', '802x602')
CHECKPOINTS = ('full-published', 'placeholder-before', 'placeholder-after', 'final-ready')
PINS = {
    'tools/modal_slots_primary_capture.py': '02eacae19e5cb9b83dd38f525e8e9917cceef216388d23027df135b53436eb6e',
    'tools/modal_slots_primary_surface.py': 'd905d43e2781849ed54d862e78725af98f188b7d47ec3f5dae3796c01ee10442',
}
PRIMARY_READS = (('primary', 220), ('backend', 176), ('surface_full', 32), ('palette', 1036),
                 ('proxy_header', 512), ('proxy_getpalette', 83), ('surface', 4),
                 ('surface_vtable', 144), ('palette_vtable', 28))
# Read-PrimaryCursorState reads the barracks pointer before its target, even
# though it inserts that pointer into its receipt dictionary last.
CURSOR_READS = (('state', 68), ('descriptor', 40), ('resource', 0x1010), ('sprite_header', 10),
                ('backing_header', 188), ('backing_pixels', 4096), ('barracks_pointer', 4),
                ('barracks_resource', 0x1010), ('placeholder_sprite_header', 10))
LIMITS = [
    'The expected binding must come from a separately authenticated outer host/context/trace.',
    'A file ledger cannot independently prove that a live VirtualQueryEx or ReadProcessMemory call occurred.',
    'Pointer-chain, proxy layout, source artwork, pixel correctness, cleanup and input need separate audits.',
    'Each result covers one sample only; the outer host must require three captures and compare stability at every checkpoint.',
    'After file and bounded row-count admission, every raw ledger row remains available in the result or LedgerError.diagnostics, including rejected rows.',
]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def parse_json(raw):
    """Strict JSON for callers loading receipts as well as each ledger line."""
    if type(raw) is not bytes:
        raise ValueError('immutable JSON bytes required')
    def pairs(rows):
        result = {}
        for key, value in rows:
            need(key not in result, 'duplicate JSON key: ' + key)
            result[key] = value
        return result
    def constant(value):
        raise ValueError('non-finite JSON number: ' + value)
    try:
        value = json.loads(raw.decode('utf-8'), object_pairs_hook=pairs, parse_constant=constant)
        canonical(value)  # Also reject overflowing finite syntax such as 1e999.
    except RecursionError as error:
        raise ValueError('JSON nesting exceeds parser capacity') from error
    return value


def need(value, message):
    if not value:
        raise ValueError(message)


def integer(value, low, high, label):
    need(type(value) is int and low <= value <= high, 'invalid integer ' + label)
    return value


def digest(value, label):
    need(type(value) is str and re.fullmatch('[0-9a-f]{64}', value), 'invalid SHA256 ' + label)


def exact(actual, expected, label):
    need(canonical(actual) == canonical(expected), label + ' differs')


@dataclass(frozen=True)
class _Snapshot:
    path: Path
    data: bytes
    stamp: tuple


def _path(value):
    need(isinstance(value, (str, Path)) and str(value), 'artifact path required')
    path = Path(value)
    need(path.is_absolute(), 'absolute artifact path required')
    for ancestor in (path, *path.parents):
        if ancestor.exists():
            stat = ancestor.lstat()
            need(not ancestor.is_symlink() and not getattr(stat, 'st_file_attributes', 0) & 0x400,
                 'reparse artifact path or ancestor')
    need(path.resolve(strict=True) == path, 'canonical non-aliased artifact path required')
    return path


def _snapshot(value):
    path = _path(value)
    def stamp():
        s = path.stat()
        return (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
    before = stamp()
    need(0 < before[2] <= 64 * 1024 * 1024, 'artifact actual file size exceeds bounded reads')
    data = path.read_bytes()
    need(before == stamp() and len(data) == before[2] and _path(value) == path,
         'artifact changed while reading')
    return _Snapshot(path, data, before)


class _Files:
    def __init__(self):
        self.files = {}
        self.identities = {}

    def read(self, record, expected_path, count=None, *, memory=True):
        fields = {'path', 'bytes', 'sha256'} | ({'address'} if memory else set())
        need(type(record) is dict and set(record) == fields, 'exact artifact receipt fields required')
        size = integer(record['bytes'], 1, 64 * 1024 * 1024, 'artifact byte count')
        if count is not None:
            need(size == count, 'artifact fixed extent differs')
        if memory:
            address = integer(record['address'], 1, 0xffffffff, 'read address')
            need(size <= 0x100000000 - address, 'read range wraps')
        digest(record['sha256'], 'artifact')
        need(type(record['path']) is str and Path(record['path']) == expected_path,
             'artifact filename or checkpoint directory differs')
        snapshot = _snapshot(record['path'])
        need(len(snapshot.data) == size and sha(snapshot.data) == record['sha256'], 'artifact bytes/hash differ')
        if snapshot.path in self.files:
            need(snapshot == self.files[snapshot.path], 'artifact changed between reads')
        else:
            identity = snapshot.stamp[:2]
            need(identity not in self.identities, 'distinct artifact paths alias one file identity')
            self.identities[identity] = snapshot.path
            self.files[snapshot.path] = snapshot
        return snapshot.data

    def unchanged(self):
        for snapshot in self.files.values():
            need(_snapshot(snapshot.path) == snapshot, 'bound artifact changed during audit')


class LedgerError(ValueError):
    """Rejected observations remain attached without modifying their files."""
    def __init__(self, message, diagnostics):
        super().__init__(message)
        self.diagnostics = diagnostics


def _binding(binding, capture_dir):
    fields = {'stage', 'recipe_revision', 'candidate_sha256', 'resolution', 'run_id',
              'checkpoint', 'capture_index', 'game_identity', 'trace'}
    need(type(binding) is dict and set(binding) == fields, 'exact outer checkpoint binding required')
    need(binding['stage'] == STAGE and binding['recipe_revision'] == RECIPE
         and binding['resolution'] in RESOLUTIONS, 'only the fresh text stage/revision/resolution is supported')
    digest(binding['candidate_sha256'], 'candidate')
    need(type(binding['run_id']) is str and re.fullmatch('[A-Za-z0-9][A-Za-z0-9_-]{0,127}', binding['run_id']),
         'bounded run identity required')
    point = binding['checkpoint']
    need(type(point) is dict and set(point) == {'name', 'index'}, 'exact checkpoint name/index required')
    index = integer(point['index'], 0, 3, 'checkpoint index')
    need(point['name'] == CHECKPOINTS[index], 'checkpoint order differs')
    sample = integer(binding['capture_index'], 1, 3, 'capture index')
    need(capture_dir.name == f'capture-{sample}' and capture_dir.parent.name == point['name'],
         'capture directory does not match checkpoint/sample')
    identity = binding['game_identity']
    need(type(identity) is dict and set(identity) == {'process_id', 'path', 'creation_filetime', 'creation_utc', 'handle_retained'},
         'exact retained process identity required')
    integer(identity['process_id'], 1, 0xffffffff, 'process ID')
    integer(identity['creation_filetime'], 1, 0x7fffffffffffffff, 'process creation FILETIME')
    need(type(identity['path']) is str and PureWindowsPath(identity['path']).is_absolute()
         and PureWindowsPath(identity['path']).suffix.lower() == '.exe', 'absolute process executable identity required')
    need(type(identity['creation_utc']) is str and re.fullmatch(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{7}Z', identity['creation_utc'])
         and identity['handle_retained'] is True, 'retained process timestamp/handle identity required')
    seconds = datetime.strptime(identity['creation_utc'][:19], '%Y-%m-%dT%H:%M:%S') - datetime(1601, 1, 1)
    ticks = (seconds.days * 86400 + seconds.seconds) * 10000000 + int(identity['creation_utc'][20:27])
    need(identity['creation_filetime'] == ticks, 'process creation UTC and FILETIME differ')


def _read_order(receipt, stream, capture_dir, resolution):
    need(type(receipt['reads']) is dict and set(receipt['reads']) == {'before', 'after'}, 'two exact read phases required')
    shapes = PRIMARY_READS if stream == 'primary' else CURSOR_READS
    result = []
    for phase in ('before', 'after'):
        rows = receipt['reads'][phase]
        need(type(rows) is dict and set(rows) == {name for name, _ in shapes}, 'closed ' + stream + ' read inventory differs')
        for name, size in shapes:
            filename = 'barracks-pointer' if name == 'barracks_pointer' else name
            result.append((rows[name], capture_dir / f'{stream}-{phase}-{filename}.raw', size))
        if stream == 'primary' and phase == 'before':
            width, height = map(int, resolution.split('x'))
            result.append((receipt['pixels'], capture_dir / 'primary.raw', width * height))
    return result


def audit_checkpoint_ledger(receipt, *, stream, capture_dir, expected_binding):
    """Validate only primary19 or cursor18 against explicit outer expectations.

    Receipt keys: revision, region_scheme, stream, binding, reads, regions,
    query_ledger, plus pixels for primary. The header carries the same binding,
    revision and stream, page_size=4096 and mbi_bytes=28 or48. Query and read
    rows retain the existing primary_virtual_query_ledger_v1 shapes verbatim.
    After file and bounded row-count admission, LedgerError.diagnostics retains
    all ledger text/decoded rows on rejection.
    """
    diagnostics = dict(revision=REVISION, ledger_valid=False, raw_records=[], source_authenticated=False,
                       live_process_authenticated=False, runtime_accepted=False, primary_composition_proven=False,
                       manual_input_proof=False, promotion_ready=False, limits=LIMITS)
    try:
        need(stream in ('primary', 'cursor'), 'only primary and cursor streams are supported')
        directory = _path(capture_dir)
        need(directory.is_dir() and not directory.is_relative_to(ROOT.resolve()), 'external capture directory required')
        _binding(expected_binding, directory)
        fields = {'revision', 'region_scheme', 'stream', 'binding', 'reads', 'regions', 'query_ledger'}
        if stream == 'primary':
            fields.add('pixels')
        need(type(receipt) is dict and set(receipt) == fields, 'fresh checkpoint ledger receipt fields required')
        need(receipt['revision'] == REVISION and receipt['region_scheme'] == SCHEME and receipt['stream'] == stream,
             'fresh checkpoint ledger revision/scheme/stream differs')
        exact(receipt['binding'], expected_binding, 'outer checkpoint/process/trace binding')
        sources = {name: _snapshot(ROOT / name) for name in PINS}
        need(Path(frozen.__file__).resolve() == ROOT / 'tools/modal_slots_primary_capture.py'
             and Path(frozen.primary.__file__).resolve() == ROOT / 'tools/modal_slots_primary_surface.py',
             'frozen certificate module path differs')
        for name, snapshot in sources.items():
            need(sha(snapshot.data) == PINS[name], 'frozen certificate dependency changed: ' + name)
        files = _Files()
        files.read(expected_binding['trace'], directory.parent / 'capture-prefix.log', memory=False)
        artifact = receipt['query_ledger']
        need(type(artifact) is dict and set(artifact) == {'path', 'bytes', 'sha256', 'records', 'scheme'}, 'exact query ledger artifact required')
        need(artifact['scheme'] == SCHEME, 'ledger artifact scheme differs')
        integer(artifact['bytes'], 1, 32 * 1024 * 1024, 'ledger byte count')
        raw = files.read({k: artifact[k] for k in ('path', 'bytes', 'sha256')},
                         directory / f'{stream}-query-ledger.jsonl', memory=False)
        diagnostics['ledger'] = dict(path=artifact['path'], bytes=len(raw), sha256=sha(raw))
        lines = raw.split(b'\n')[:-1] if raw.endswith(b'\n') else raw.split(b'\n')
        need(0 < len(lines) <= 65536, 'ledger line count is outside the bounded contract')
        rows, errors = [], []
        for number, line in enumerate(lines, 1):
            record = dict(line=number, text=line.decode('utf-8', errors='replace'), record=None)
            diagnostics['raw_records'].append(record)
            try:
                need(line and not line.endswith(b'\r'), 'blank or noncanonical ledger line')
                record['record'] = parse_json(line)
                need(type(record['record']) is dict, 'ledger row must be an object')
                rows.append(record['record'])
            except (ValueError, UnicodeError) as error:
                record['parse_error'] = str(error)
                errors.append(f'line {number}: {error}')
        need(not errors, '; '.join(errors))
        need(raw.endswith(b'\n'), 'ledger is truncated without final newline')
        integer(artifact['records'], 1, 65536, 'ledger records')
        need(artifact['records'] == len(rows), 'ledger record count differs')
        header = rows[0]
        integer(header.get('mbi_bytes'), 28, 48, 'MBI byte count')
        need(header['mbi_bytes'] in (28, 48), 'unsupported host MBI layout')
        exact(header, dict(kind='header', revision=REVISION, scheme=SCHEME, stream=stream,
                           binding=expected_binding, page_size=4096, mbi_bytes=header['mbi_bytes']), 'ledger header')
        expected = _read_order(receipt, stream, directory, expected_binding['resolution'])
        for name, _ in PRIMARY_READS if stream == 'primary' else CURSOR_READS:
            before, after = (receipt['reads'][phase][name] for phase in ('before', 'after'))
            exact({key: before[key] for key in ('address', 'bytes', 'sha256')},
                  {key: after[key] for key in ('address', 'bytes', 'sha256')}, 'paused paired read identity')
        observations, position = [], 1
        for index, (record, path, size) in enumerate(expected, 1):
            files.read(record, path, size)
            request = {k: record[k] for k in ('path', 'address', 'bytes')}
            cursor, end, query = request['address'], request['address'] + size, 0
            while cursor < end:
                need(position < len(rows), 'query coverage is incomplete')
                row = rows[position]; position += 1; query += 1
                need(set(row) == {'kind', 'read_index', 'query_index', 'request', 'cursor', 'requested_mbi_bytes', 'returned_mbi_bytes', 'region'},
                     'exact raw query fields required')
                expected_query = dict(kind='query', read_index=index, query_index=query, request=request,
                                      cursor=cursor, requested_mbi_bytes=header['mbi_bytes'], returned_mbi_bytes=header['mbi_bytes'], region=row['region'])
                exact(row, expected_query, 'query sequence/request/cursor/MBI result')
                region = row['region']
                frozen.region_certificate([region], 4096)
                need(region['address'] <= cursor < region['address'] + region['size'], 'query leaves a read gap')
                observations.append(region)
                cursor = min(end, region['address'] + region['size'])
            need(position < len(rows), 'completed read receipt is missing')
            exact(rows[position], dict(kind='read', read_index=index, artifact=record), 'completed read receipt')
            position += 1
        need(position == len(rows), 'ledger contains extra, omitted or contradictory observations')
        certificate = frozen.region_certificate(observations, 4096)
        need(type(receipt['regions']) is list and receipt['regions'], 'mandatory region certificate missing')
        exact(frozen.region_certificate(receipt['regions'], 4096), receipt['regions'], 'canonical receipt regions')
        exact(receipt['regions'], certificate, 'complete query certificate')
        files.unchanged()
        for name, snapshot in sources.items():
            need(_snapshot(ROOT / name) == snapshot, 'frozen certificate source changed during audit')
        diagnostics.update(ledger_valid=True, stream=stream, binding_sha256=sha(canonical(expected_binding).encode()),
                           records=len(rows), queries=len(observations), reads=len(expected), certificate=certificate,
                           certificate_source_hashes=PINS.copy(), artifacts=[dict(path=str(v.path), bytes=len(v.data), sha256=sha(v.data))
                                                                          for v in files.files.values()])
        return diagnostics
    except (ValueError, KeyError, TypeError, OSError, UnicodeError) as error:
        diagnostics['failures'] = [str(error)]
        raise LedgerError(str(error), diagnostics) from error
