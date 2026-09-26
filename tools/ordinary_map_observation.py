"""Bounded native-memory decoding for a caller-owned paused read lease.

No process is opened or controlled here. The caller authenticates the candidate,
identity and live paused lease, and supplies read_exact(address, size) and
check_lease(lease). Successful repeated reads establish consistency of supplied
bytes only; a dictionary or digest cannot establish process authentication.

Native layout: clash-disassembly recovered_structs.h/recovered_types.h;
40F060 visibility; 413920 costs (native metadata stride 88, costs at +30);
the ten selection flags at 526F78 are DWORDs, not ten adjacent bytes.
"""
from __future__ import annotations

from bisect import bisect_left
from copy import deepcopy
from inspect import iscoroutine
import struct

import ordinary_map_input_plan as planner

LEASE_SCHEMA = 'clash95_paused_read_lease_v1'
RECEIPT_SCHEMA = 'clash95_ordinary_map_read_receipt_v1'
MAX_UNIQUE_BYTES = 600_000
MAX_READ_CALLS = 2_000
MAX_TOTAL_BYTES = 2_000_000
MAX_SINGLE_READ = 362_500
GAME_DATA_BYTES = 586_398
STACK_BYTES = 725
STACK_COUNT = 500
PREFERRED_BASE = 0x400000


class ObservationError(planner.PlanError):
    """A lease, exact read, native layout or consistency requirement failed."""


def require(condition, message):
    if not condition:
        raise ObservationError(message)


def integer(value, low, high, name):
    require(type(value) is int and low <= value <= high, name+' is out of bounds or not an integer')
    return value


def record(value, fields, name):
    require(type(value) is dict and set(value) == set(fields.split()), name+' has missing or unknown fields')
    return value


def unpack(fmt, data, offset=0):
    return struct.unpack_from('<'+fmt, data, offset)


class _ReadSet:
    """Deduplicate contained reads; reject partial aliases and repeat all bytes."""

    def __init__(self, read_exact):
        require(callable(read_exact), 'read_exact must be callable')
        self.read_exact = read_exact
        self.regions = []
        self.addresses = []
        self.unique_bytes = 0
        self.calls = 0
        self.total_bytes = 0

    def _call(self, address, size):
        integer(address, 0x10000, planner.MAX_ADDRESS-1, 'read address')
        integer(size, 1, MAX_SINGLE_READ, 'read size')
        require(address+size <= planner.MAX_ADDRESS, 'read exceeds bounded user address space')
        require(self.calls < MAX_READ_CALLS and self.total_bytes+size <= MAX_TOTAL_BYTES,
                'read call/byte budget exceeded')
        self.calls += 1
        self.total_bytes += size
        try:
            data = self.read_exact(address, size)
        except Exception as error:
            raise ObservationError(f'exact read failed at {address:08x}, size {size}') from error
        require(type(data) is bytes and len(data) == size,
                f'exact immutable bytes required at {address:08x}, size {size}')
        return data

    def take(self, address, size, purpose, *, anchor=False):
        integer(address, 0x10000, planner.MAX_ADDRESS-1, 'read address')
        integer(size, 1, MAX_SINGLE_READ, 'read size')
        require(address+size <= planner.MAX_ADDRESS, 'read exceeds bounded user address space')
        at = bisect_left(self.addresses, address)
        for index in (at-1, at):
            if not 0 <= index < len(self.regions):
                continue
            region = self.regions[index]
            start, end = region['address'], region['address']+len(region['data'])
            if start < address+size and address < end:
                require(start <= address and address+size <= end,
                        'partially overlapping native read ranges are ambiguous')
                region['purposes'].add(purpose)
                region['anchor'] |= anchor
                return region['data'][address-start:address-start+size]
        require(self.unique_bytes+size <= MAX_UNIQUE_BYTES, 'unique read byte budget exceeded')
        data = self._call(address, size)
        self.regions.insert(at, dict(address=address, data=data, purposes={purpose}, anchor=anchor))
        self.addresses.insert(at, address)
        self.unique_bytes += size
        return data

    def compare(self, *, anchors_only=False):
        for region in self.regions:
            if anchors_only and not region['anchor']:
                continue
            if self._call(region['address'], len(region['data'])) != region['data']:
                raise ObservationError('paused bytes changed: '+', '.join(sorted(region['purposes'])))

    def manifest(self):
        from hashlib import sha256
        return [dict(address=r['address'], size=len(r['data']), sha256=sha256(r['data']).hexdigest(),
                     purposes=sorted(r['purposes']), anchor=r['anchor'])
                for r in self.regions]


def _contracts(candidate, identity, sequence, lease):
    planner.candidate_contract(candidate)
    record(identity, 'pid creation_filetime candidate_sha256 image_base', 'identity')
    integer(identity['pid'], 1, 0xFFFFFFFF, 'PID')
    integer(identity['creation_filetime'], 1, 0x7FFFFFFFFFFFFFFF, 'creation filetime')
    base = integer(identity['image_base'], 0x10000, planner.MAX_ADDRESS-0x400000, 'image base')
    require(base % 0x10000 == 0 and identity['candidate_sha256'] == candidate['sha256'],
            'authenticated candidate and identity differ')
    integer(sequence, 0, 0x7FFFFFFF, 'sequence')
    record(lease, 'schema lease_id paused pid creation_filetime image_base candidate_sha256', 'lease')
    require(lease['schema'] == LEASE_SCHEMA and lease['paused'] is True, 'unsupported or unpaused lease')
    token = lease['lease_id']
    require(type(token) is str and 1 <= len(token) <= 128
            and all(c in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-' for c in token),
            'lease_id must be a bounded ASCII token')
    require(all(type(lease[key]) is type(value) and lease[key] == value for key, value in identity.items()),
            'paused lease and authenticated identity differ')


def _checked_lease(check_lease, lease):
    require(callable(check_lease), 'check_lease must be callable')
    before = planner.digest(lease)
    try:
        result = check_lease(lease)
    except Exception as error:
        raise ObservationError('caller could not verify the same live paused lease') from error
    # An async checker returns without running its body. Close that coroutine
    # and reject it rather than mistaking an unexecuted check for a live lease.
    if iscoroutine(result):
        result.close()
    require(result is None, 'lease callback must synchronously return None after validation')
    require(planner.digest(lease) == before, 'lease callback mutated the lease context')


def _runs(indices):
    """Half-open contiguous record-index ranges, deterministic and disjoint."""
    if not indices:
        return []
    ordered = sorted(indices)
    runs = [[ordered[0], ordered[0]+1]]
    for index in ordered[1:]:
        if index == runs[-1][1]:
            runs[-1][1] += 1
        else:
            runs.append([index, index+1])
    return runs


def _decode_stack(index, raw):
    # An empty first signed type is the native unused-stack sentinel. Its
    # leftover coordinates/owner/queue are not interpreted as a live army.
    if unpack('h', raw, 6)[0] == -1:
        return None
    slots = [dict(type=unpack('h', raw, 6+31*i)[0], ap=raw[14+31*i]) for i in range(10)]
    return dict(index=index, x=unpack('h', raw)[0], y=unpack('h', raw, 2)[0],
                owner=raw[4], hidden=raw[720] != 0, queue_count=unpack('i', raw, 316)[0],
                slots=slots)


def observe(read_exact, *, candidate, identity, sequence, lease, check_lease, stack_indices=None):
    """Decode strict planner state and a separate source-byte consistency receipt.

    stack_indices is None (all 500) or a nonempty list/tuple of unique native
    indices. The selected stack is always measured. Relevant neighboring
    occupants are added without recursively expanding their neighborhoods.
    Every native range is reread.
    check_lease must synchronously return None only while this lease is paused;
    it is checked before any reads, between passes, and after final comparison.
    No elapsed-time or process-authentication guarantee is provided here.
    """
    candidate, identity, lease = deepcopy(candidate), deepcopy(identity), deepcopy(lease)
    try:
        _contracts(candidate, identity, sequence, lease)
        if stack_indices is None:
            requested = list(range(STACK_COUNT))
        else:
            require(type(stack_indices) in (list, tuple) and 1 <= len(stack_indices) <= STACK_COUNT,
                    'stack_indices must be a bounded nonempty list/tuple')
            requested = [integer(i, 0, STACK_COUNT-1, 'stack index') for i in stack_indices]
            require(len(set(requested)) == len(requested), 'duplicate requested stack index')
            requested.sort()
        _checked_lease(check_lease, lease)
        reads = _ReadSet(read_exact)
        delta = identity['image_base']-PREFERRED_BASE
        def image(address, size, purpose, *, anchor=True):
            return reads.take(address+delta, size, purpose, anchor=anchor)
        def global_word(address, purpose, *, signed=False):
            return unpack('i' if signed else 'I', image(address, 4, purpose))[0]
        pointers = image(0x5202E0, 16, 'map/GD pointers, join mode and current player')
        surface, gd, join_mode, current_player = unpack('4I', pointers)
        integer(gd, 0x10000, planner.MAX_ADDRESS-GAME_DATA_BYTES, 'GD pointer')
        integer(surface, 0x10000, planner.MAX_ADDRESS-188, 'map surface pointer')
        # Read the two pointer-bearing headers once; runtime pointers are not
        # image-relative addresses and must never receive the relocation delta.
        header = reads.take(surface, 188, 'native map surface header', anchor=True)
        primary = image(0x51D4C0, 4, 'primary extent')
        owners = image(0x52698C, 12, 'native modal/post/lower owners')
        selection = image(0x511B58, 8, 'selected and previous indices')
        panel = global_word(0x514194, 'army panel index', signed=True)
        flags_active = image(0x526F78, 44, 'ten DWORD slot flags and active-stack pointer')
        metadata = reads.take(gd+140000, 7174, 'world, five player records and turn/view owners', anchor=True)
        mini = image(0x523344, 8, 'minimap rectangle')
        port = reads.take(gd+586374, 8, 'port footprint origin', anchor=True)
        integer(current_player, 0, 4, 'current player')
        player_offset = 24+1423*current_player
        world_values = unpack('4i', metadata)
        selected, previous = unpack('2i', selection)
        modal, post, lower = unpack('3I', owners)
        snapshot = dict(schema=planner.OBSERVATION_SCHEMA, sequence=sequence, paused=True,
            identity=identity,
            context=dict(game_data=gd, render_hook=global_word(0x5199D8, 'render owner'),
                map_active=global_word(0x527C24, 'map active'), native_modal=modal,
                post_callback=post, lower_owner=lower, map_surface=surface,
                map_pixels=unpack('I', header, 4)[0], map_vtable=unpack('I', header, 184)[0],
                map_extent=list(unpack('2H', header)), primary_extent=list(unpack('2H', primary)),
                current_player=current_player, turn_owner=unpack('I', metadata, 7139)[0],
                viewed_player=unpack('I', metadata, 7143)[0], selected_stack=selected,
                previous_stack=previous, panel_stack=panel, active_stack=unpack('I', flags_active, 40)[0],
                join_mode=join_mode, slot_flags=list(unpack('10I', flags_active))),
            world=dict(zip(('width', 'height', 'scroll_x', 'scroll_y'), world_values)),
            player=dict(index=current_player, human=unpack('I', metadata, player_offset+27)[0] != 0,
                        minimap_visible=unpack('I', metadata, player_offset+23)[0] != 0),
            minimap=dict(zip(('left', 'top', 'width', 'height'), unpack('4H', mini))),
            port=dict(zip(('x', 'y'), unpack('2i', port))),
            stacks=[], tiles=[], unit_profiles=[])
        # Bound native pointers, owner fields and player/world dimensions
        # before larger reads. Selection ownership still needs measured slots.
        planner.inspect_header(snapshot, candidate)
        width, height = snapshot['world']['width'], snapshot['world']['height']
        stacks, raw_stacks, empty = {}, {}, set()
        def load_stacks(indices):
            missing = set(indices)-raw_stacks.keys()
            for first, stop in _runs(missing):
                raw = reads.take(gd+147174+STACK_BYTES*first, STACK_BYTES*(stop-first),
                                 f'army records {first}..{stop-1}')
                for index in range(first, stop):
                    record_bytes = raw[STACK_BYTES*(index-first):STACK_BYTES*(index-first+1)]
                    raw_stacks[index] = record_bytes
                    stack = _decode_stack(index, record_bytes)
                    if stack is None:
                        empty.add(index)
                    else:
                        stacks[index] = stack
        selected_indices = {selected} if selected != -1 else set()
        added_selected = sorted(selected_indices-set(requested))
        load_stacks(set(requested) | selected_indices)
        snapshot['stacks'] = [stacks[i] for i in sorted(stacks)]
        planner.inspect(snapshot, candidate)
        for stack in stacks.values():
            planner.occupied_slots(stack)
        needed = set()
        for stack in list(stacks.values()):
            x, y = stack['x'], stack['y']
            centers = [(x, y)]+[(x+dx, y+dy) for dx, dy in planner.CARDINALS
                                if 0 <= x+dx < width and 0 <= y+dy < height]
            needed.update((cx+dx, cy+dy) for cx, cy in centers
                          for dx in (-1, 0, 1) for dy in (-1, 0, 1)
                          if 0 <= cx+dx < width and 0 <= cy+dy < height)
        terrain = reads.take(gd, 140000, '100x100 native terrain records')
        occupancy_traps = reads.take(gd+556374, 30000, '100x100 occupancy WORDs and trap bytes')
        profiles = image(0x52456C, 4096, '1024 terrain profile DWORDs', anchor=False)
        occupied = {}
        for x, y in sorted(needed):
            occupant = unpack('H', occupancy_traps, 200*x+2*y)[0]
            terrain_id, overlay, road = unpack('3H', terrain, 1400*x+14*y)
            integer(terrain_id, 0, 1023, 'measured terrain ID')
            tile = dict(x=x, y=y, occupant=occupant,
                visible=bool(metadata[player_offset+57+13*x+(y>>3)] & (1 << (y & 7))),
                terrain_id=terrain_id, terrain_profile=unpack('I', profiles, 4*terrain_id)[0],
                overlay_id=overlay, road_id=road, trap_mask=occupancy_traps[20000+100*x+y])
            snapshot['tiles'].append(tile)
            if occupant == planner.EMPTY or 0x8000 <= occupant < 0x8064:
                continue
            integer(occupant, 0, STACK_COUNT-1, 'measured neighboring occupant')
            require(occupant not in occupied, 'same army index occupies multiple measured tiles')
            occupied[occupant] = (x, y)
        added = sorted(set(occupied)-set(requested)-selected_indices)
        load_stacks(occupied)
        for index, xy in occupied.items():
            require(index in stacks, 'occupied tile points to a native empty army record')
            require((stacks[index]['x'], stacks[index]['y']) == xy, 'occupied tile and native army coordinates differ')
            planner.occupied_slots(stacks[index])
        snapshot['stacks'] = [stacks[i] for i in sorted(stacks)]
        unit_types = {slot['type'] for stack in stacks.values() for slot in planner.occupied_slots(stack)}
        for unit_type in sorted(unit_types):
            costs = image(0x512568+88*unit_type+30, 8, f'unit type {unit_type} terrain costs', anchor=False)
            snapshot['unit_profiles'].append(dict(type=unit_type, costs=list(costs)))
        planner.inspect(snapshot, candidate)
        _checked_lease(check_lease, lease)
        reads.compare(anchors_only=True)
        reads.compare()
        reads.compare(anchors_only=True)
        _checked_lease(check_lease, lease)
        manifest = reads.manifest()
        receipt = dict(schema=RECEIPT_SCHEMA, lease=lease, lease_sha256=planner.digest(lease),
            candidate=deepcopy(candidate), observation_sha256=planner.digest(snapshot),
            read_set=manifest, read_set_sha256=planner.digest(manifest),
            complete_read_passes=2, additional_anchor_passes=2,
            read_calls=reads.calls, unique_read_bytes=reads.unique_bytes, total_read_bytes=reads.total_bytes,
            requested_stack_indices=requested, added_selected_indices=added_selected,
            added_occupant_indices=added,
            empty_stack_indices=sorted(empty), measured_stack_indices=sorted(stacks),
            authentication_scope='candidate/process identity and live pause supplied by caller/host; dictionaries and digests do not authenticate them',
            proof_scope='consistent bounded supplied memory reads; no input, native callback, rendering or lifecycle proof')
        return dict(snapshot=snapshot, receipt=receipt)
    except ObservationError:
        raise
    except (planner.PlanError, TypeError, ValueError, struct.error) as error:
        raise ObservationError(str(error)) from error
