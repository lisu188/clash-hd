"""Strict client for held native-loop observations and controlled input phases.

This does not launch a process or deliver OS input. The explicit phase host
owns each native stop; decoder reads and plan revalidation happen before the
same held lease is committed. Receipts describe controlled native dispatch,
never manual DirectInput or visible composition.
"""
from copy import deepcopy
import json
import os
import re
import uuid

from ordinary_map_pause_client import (PauseClient, LeaseError, LEASE_SCHEMA,
    TOKEN, require, unique_object)

SCHEMA = 'clash95_native_phase_ack_v1'
ACK_KEYS = set('schema session_id request_seq status lease_id pid primary_tid creation_filetime image_base deadline_tick_ms paused phase controller_sha256 root_esp held_esp held_eip human_entry_seen postpoll_seen action_index capture_index binding_sha256 target_x target_y dispatch_seen dispatch_eip dispatch_esp dispatch_return predicate_observed predicate_value return_seen return_eip return_esp'.split())
BOOL_KEYS = {'paused', 'human_entry_seen', 'postpoll_seen', 'dispatch_seen', 'predicate_observed', 'return_seen'}
INT_KEYS = set('request_seq pid primary_tid creation_filetime image_base deadline_tick_ms root_esp held_esp held_eip action_index capture_index target_x target_y dispatch_eip dispatch_esp dispatch_return predicate_value return_eip return_esp'.split())


class PhaseClient(PauseClient):
    def __init__(self, directory, *, controller_sha256, **kwargs):
        require(type(controller_sha256) is str and re.fullmatch('[0-9a-f]{64}', controller_sha256),
                'Expected phase controller hash required')
        self.controller_sha256 = controller_sha256
        super().__init__(directory, **kwargs)

    def ack(self):
        path = self.directory/'phase-ack.json'
        if not path.exists():
            return None
        require(not path.is_symlink() and path.stat().st_size <= 4096, 'Invalid phase acknowledgment file')
        data = json.loads(path.read_text(encoding='ascii'), object_pairs_hook=unique_object)
        require(type(data) is dict and set(data) == ACK_KEYS, 'Phase acknowledgment schema differs')
        require(data['schema'] == SCHEMA and data['session_id'] == self.session_id and
                data['controller_sha256'] == self.controller_sha256, 'Phase session or controller differs')
        for name in BOOL_KEYS:
            require(type(data[name]) is bool, 'Invalid phase boolean: '+name)
        for name in INT_KEYS:
            require(type(data[name]) is int and (-1 if name == 'capture_index' else 0) <= data[name] <= 0xffffffffffffffff,
                    'Invalid phase integer: '+name)
        require(data['primary_tid'] > 0 and all(data[key] == self.identity[key]
                for key in ('pid', 'creation_filetime', 'image_base')), 'Phase target identity differs')
        require(data['binding_sha256'] == '' or (type(data['binding_sha256']) is str and
                re.fullmatch('[0-9a-f]{64}', data['binding_sha256'])), 'Invalid phase binding digest')
        status = data['status']
        require(status in ('ready', 'held', 'executing', 'released'), 'Unknown phase status')
        if status == 'held':
            require(type(data['lease_id']) is str and TOKEN.fullmatch(data['lease_id']) and
                    data['paused'] and data['deadline_tick_ms'] > 0 and data['request_seq'] > 0 and
                    data['human_entry_seen'] and data['postpoll_seen'] and data['held_eip'] == 0x40B233+self.identity['image_base']-0x400000 and data['root_esp'] > 0 and data['held_esp'] > 0 and
                    data['phase'] in ('predispatch-before', 'predispatch-after'), 'Invalid held native phase')
            require(all(type(data[k]) is int and 0x10000 <= data[k] < 0x7FFE0000 and data[k] % 4 == 0 for k in ('root_esp','held_esp')) and
                    data['held_esp'] == data['root_esp']-28, 'Native hold is outside the observed human-loop frame')
        else:
            require(data['lease_id'] == '' and not data['paused'] and data['deadline_tick_ms'] == 0 and
                    data['phase'] == status, 'Contradictory unheld phase acknowledgment')
            require((data['request_seq'] == 0) == (status == 'ready'), 'Invalid phase request sequence')
        return data

    def _wait_phase(self, status, lease_id, sequence, timeout_ms):
        end = self.clock_ms()+timeout_ms
        while self.clock_ms() < end:
            self.live()
            ack = self.ack()
            if ack is not None:
                require(ack['request_seq'] <= sequence, 'Unexpected newer phase request')
                if ack['request_seq'] == sequence:
                    if ack['status'] == 'executing' and status == 'held':
                        pass
                    else:
                        require(ack['status'] == status and ack['lease_id'] == lease_id,
                                'Phase acknowledgment differs from requested transition')
                        self.receipts.append(deepcopy(ack))
                        return ack
            self.sleep(.01)
        raise LeaseError('Timed out waiting for owned native phase')

    def wait_ready(self, timeout_ms=12000):
        require(self.sequence == 0 and self._active is None, 'Phase readiness is only valid at session start')
        return self._wait_phase('ready', '', 0, timeout_ms)

    def _phase_request(self, operation, *parts):
        self.live()
        self.sequence += 1
        wire = f'CLASH_PHASE_V1 {self.session_id} {self.sequence} {operation} '+ ' '.join(map(str, parts))+'\n'
        data = wire.encode('ascii')
        require(len(data) <= 256 and all('\n' not in str(p) and ' ' not in str(p) for p in parts),
                'Native phase request exceeds grammar bounds')
        destination = self.directory/'phase-request.txt'
        require(not destination.is_symlink(), 'Phase request path is a link')
        temporary = self.directory/('.phase-request-'+uuid.uuid4().hex+'.tmp')
        try:
            with temporary.open('xb') as stream:
                stream.write(data); stream.flush(); os.fsync(stream.fileno())
            os.replace(temporary, destination)
        finally:
            if temporary.exists():
                temporary.unlink()
        return self.sequence

    def _activate(self, ack, lease_id, sequence):
        require(0 < ack['deadline_tick_ms']-self.clock_ms() <= 20000,
                'Native read lease expired or exceeds host bound')
        lease = dict(schema=LEASE_SCHEMA, lease_id=lease_id, paused=True, **self.identity)
        self._active = deepcopy(lease)
        self._active_sequence = sequence
        self.check_lease(lease)
        return lease

    def acquire(self, timeout_ms=25000):
        self.live()
        require(self._active is None, 'Nested native phase leases are forbidden')
        lease_id = uuid.uuid4().hex
        try:
            seq = self._phase_request('acquire', lease_id)
            ack = self._wait_phase('held', lease_id, seq, timeout_ms)
            require(ack['phase'] == 'predispatch-before', 'Acquisition did not stop before native input')
            return self._activate(ack, lease_id, seq)
        except BaseException:
            self._poisoned = True
            raise

    def check_lease(self, lease):
        self.live()
        require(self._active is not None and lease == self._active, 'Native lease is inactive, changed or released')
        ack = self.ack()
        require(ack is not None and ack['status'] == 'held' and ack['paused'] and
                ack['request_seq'] == self._active_sequence and ack['lease_id'] == lease['lease_id'],
                'Host no longer holds this native read lease')
        require(self.clock_ms() < ack['deadline_tick_ms'], 'Native read lease expired')

    def click(self, lease, point, binding_sha256, timeout_ms=25000):
        self.check_lease(lease)
        require(type(point) in (list, tuple) and len(point) == 2 and
                all(type(v) is int and 0 <= v < 4096 for v in point), 'Invalid controlled input point')
        require(type(binding_sha256) is str and re.fullmatch('[0-9a-f]{64}', binding_sha256),
                'Plan and held observation binding required')
        before = self.ack()
        successor = uuid.uuid4().hex
        try:
            self._active = None; self._active_sequence = None
            seq = self._phase_request('click', lease['lease_id'], successor, *point, binding_sha256)
            ack = self._wait_phase('held', successor, seq, timeout_ms)
            require(ack['phase'] == 'predispatch-after' and ack['action_index'] == before['action_index']+1 and
                    ack['binding_sha256'] == binding_sha256 and (ack['target_x'], ack['target_y']) == tuple(point),
                    'Native completion is not bound to the requested action')
            return self._activate(ack, successor, seq)
        except BaseException:
            self._poisoned = True
            raise

    def release(self, lease, timeout_ms=3000):
        try:
            self.check_lease(lease)
            self._active = None; self._active_sequence = None
            seq = self._phase_request('release', lease['lease_id'])
            return self._wait_phase('released', '', seq, timeout_ms)
        except BaseException:
            self._poisoned = True
            raise


def verify_dispatch(ack, identity, binding_sha256):
    """Validate observed natural call/query/return; no selection state inferred."""
    delta = identity['image_base']-0x400000
    require(ack['status'] == 'held' and ack['phase'] == 'predispatch-after' and
            ack['binding_sha256'] == binding_sha256, 'No bound post-action native phase')
    require(all(ack[key] == identity[key] for key in ('pid','creation_filetime','image_base')),
            'Native dispatch belongs to a different target')
    require(ack['human_entry_seen'] is True and ack['postpoll_seen'] is True and ack['dispatch_seen'] is True and ack['predicate_observed'] is True and
            type(ack['predicate_value']) is int and ack['predicate_value'] == 1 and ack['return_seen'] is True, 'Native input dispatch was not accepted and returned')
    require(all(type(ack[k]) is int and 0x10000 <= ack[k] < 0x7FFE0000 and ack[k] % 4 == 0
                for k in ('root_esp','held_esp','dispatch_esp','return_esp')) and
            ack['held_esp'] == ack['root_esp']-28, 'Native dispatch is outside the observed human-loop frame')
    require(ack['dispatch_eip'] == 0x4084A0+delta and ack['dispatch_return'] == 0x40B238+delta and
            ack['return_eip'] == 0x40B238+delta and ack['return_esp'] == ack['dispatch_esp']+4 and
            ack['held_esp'] == ack['return_esp'] and ack['held_eip'] == 0x40B233+delta, 'Native input caller or stack restoration differs')
    return dict(passed=True, binding_sha256=binding_sha256, proof_scope='controlled ordinary native call/query/return; not OS or manual input')
