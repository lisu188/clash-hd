"""Bounded client for the opt-in owned-debuggee pause/read/resume protocol.

This module launches nothing and sends no game input. The host owns the debug
session. A lease authenticates a paused read interval, not a later input event.
"""
from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
import ctypes as C
from ctypes import wintypes as W
import json
import os
from pathlib import Path
import re
import time
import uuid

ACK_SCHEMA = 'clash95_debug_pause_ack_v1'
LEASE_SCHEMA = 'clash95_paused_read_lease_v1'
IDENTITY_KEYS = {'pid', 'creation_filetime', 'image_base', 'candidate_sha256'}
ACK_KEYS = {'schema', 'session_id', 'request_seq', 'status', 'lease_id', 'pid',
            'primary_tid', 'creation_filetime', 'image_base', 'deadline_tick_ms', 'paused'}
TOKEN = re.compile(r'[0-9a-f]{32}')


class LeaseError(RuntimeError):
    pass


def require(condition, message):
    if not condition:
        raise LeaseError(message)


def checked_directory(path):
    raw = Path(path).absolute()
    require(str(raw).isascii(), 'Control directory must have an ASCII path')
    for item in (raw, *raw.parents):
        require(not item.is_symlink() and not getattr(item, 'is_junction', lambda:False)(),
                'Control path follows a link or junction')
    return raw.resolve()


def prepare_control(path):
    """Create one new private mailbox; never adopt or clear a previous run."""
    directory = checked_directory(path)
    directory.mkdir()  # Parent must already exist; existing runs are rejected.
    token = uuid.uuid4().hex
    with (directory/'session.token').open('x', encoding='ascii', newline='\n') as stream:
        stream.write(token+'\n')
    return token


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'Duplicate acknowledgment field')
        result[key] = value
    return result


def windows_tick_ms():
    require(os.name == 'nt', 'Production clock requires the Windows host clock')
    kernel = C.WinDLL('kernel32', use_last_error=True)
    kernel.GetTickCount64.restype = C.c_ulonglong
    return kernel.GetTickCount64()


class PauseClient:
    def __init__(self, directory, *, identity, check_owner, host_alive,
                 clock_ms=windows_tick_ms, sleep=time.sleep):
        require(type(identity) is dict and set(identity)==IDENTITY_KEYS, 'Exact owned identity required')
        for key in ('pid','creation_filetime','image_base'):
            require(type(identity[key]) is int and identity[key]>0, 'Invalid owned identity: '+key)
        require(type(identity['candidate_sha256']) is str and
                re.fullmatch('[0-9a-f]{64}', identity['candidate_sha256']), 'Candidate SHA-256 required')
        require(all(callable(fn) for fn in (check_owner,host_alive,clock_ms,sleep)), 'Owned callbacks required')
        self.directory = checked_directory(directory)
        raw = (self.directory/'session.token').read_bytes()
        require(len(raw)==33 and raw.endswith(b'\n'), 'Invalid control-session token file')
        self.session_id = raw[:-1].decode('ascii')
        require(TOKEN.fullmatch(self.session_id), 'Invalid control-session token')
        self.identity = deepcopy(identity)
        self.check_owner, self.host_alive = check_owner, host_alive
        self.clock_ms, self.sleep = clock_ms, sleep
        self.sequence = 0
        self._active = None
        self._active_sequence = None
        self._poisoned = False
        self.receipts = []

    def live(self):
        require(not self._poisoned, 'Failed control session cannot be reused')
        require(self.host_alive() is True, 'Owned observation host exited')
        require(self.check_owner() == self.identity, 'Retained target identity changed')
        require(checked_directory(self.directory)==self.directory, 'Control directory changed')

    def ack(self):
        path = self.directory/'ack.json'
        if not path.exists():
            return None
        require(not path.is_symlink() and path.stat().st_size<=2048, 'Invalid acknowledgment file')
        data = json.loads(path.read_text(encoding='ascii'), object_pairs_hook=unique_object)
        require(type(data) is dict and set(data)==ACK_KEYS, 'Acknowledgment schema fields differ')
        require(data['schema']==ACK_SCHEMA and data['session_id']==self.session_id, 'Wrong host session')
        for name in ('request_seq','pid','primary_tid','creation_filetime','image_base','deadline_tick_ms'):
            require(type(data[name]) is int and data[name]>=0, 'Invalid acknowledgment integer')
        require(data['primary_tid']>0 and type(data['paused']) is bool, 'Invalid host pause identity')
        require(all(data[key]==self.identity[key] for key in ('pid','creation_filetime','image_base')),
                'Host acknowledged a different target')
        require(data['status'] in ('ready','paused','resumed'), 'Unknown host acknowledgment status')
        if data['status']=='ready':
            require(data['request_seq']==0 and data['lease_id']=='' and not data['paused'] and
                    data['deadline_tick_ms']==0, 'Invalid ready acknowledgment')
        else:
            require(type(data['lease_id']) is str and TOKEN.fullmatch(data['lease_id']), 'Invalid lease token')
            require(data['request_seq']>0 and data['paused']==(data['status']=='paused'), 'Contradictory pause acknowledgment')
            require((data['deadline_tick_ms']>0)==data['paused'], 'Invalid acknowledgment deadline')
        return data

    def _wait(self, status, lease_id, sequence, timeout_ms):
        end = self.clock_ms()+timeout_ms
        while self.clock_ms()<end:
            self.live()
            ack = self.ack()
            if ack is not None:
                require(ack['request_seq']<=sequence, 'Unexpected newer host request')
                if ack['request_seq']==sequence:
                    require(ack['status']==status and ack['lease_id']==lease_id, 'Host acknowledgment differs from request')
                    self.receipts.append(deepcopy(ack))
                    return ack
            self.sleep(.01)
        raise LeaseError('Timed out waiting for owned host acknowledgment')

    def wait_ready(self, timeout_ms=12000):
        require(self.sequence==0 and self._active is None, 'Readiness is only valid at session start')
        return self._wait('ready','',0,timeout_ms)

    def _request(self, operation, lease_id):
        self.live()
        self.sequence += 1
        data=f'CLASH_LEASE_V1 {self.session_id} {self.sequence} {operation} {lease_id}\n'.encode('ascii')
        require(len(data)<=256, 'Control request too long')
        destination=self.directory/'request.txt'
        require(not destination.is_symlink(), 'Request path is a link')
        temporary=self.directory/('.request-'+uuid.uuid4().hex+'.tmp')
        try:
            with temporary.open('xb') as stream:
                stream.write(data); stream.flush(); os.fsync(stream.fileno())
            os.replace(temporary,destination)
        finally:
            if temporary.exists(): temporary.unlink()
        return self.sequence

    def acquire(self, timeout_ms=12000):
        self.live()
        require(self._active is None, 'Nested read leases are forbidden')
        lease_id=uuid.uuid4().hex
        try:
            sequence=self._request('pause',lease_id)
            ack=self._wait('paused',lease_id,sequence,timeout_ms)
            require(0<ack['deadline_tick_ms']-self.clock_ms()<=20000, 'Read lease expired or exceeds the host bound')
            lease=dict(schema=LEASE_SCHEMA,lease_id=lease_id,paused=True,**self.identity)
            self._active=deepcopy(lease); self._active_sequence=sequence
            self.check_lease(lease)
            return lease
        except BaseException:
            self._poisoned=True
            raise

    def check_lease(self, lease):
        self.live()
        require(self._active is not None and lease==self._active, 'Lease is inactive, changed or released')
        ack=self.ack()
        require(ack is not None and ack['status']=='paused' and ack['paused'] and
                ack['request_seq']==self._active_sequence and ack['lease_id']==lease['lease_id'],
                'Host no longer holds this paused lease')
        require(self.clock_ms()<ack['deadline_tick_ms'], 'Paused read lease expired')

    def release(self, lease, timeout_ms=3000):
        try:
            self.check_lease(lease)
            lease_id=lease['lease_id']
            self._active=None; self._active_sequence=None  # Invalidate before any resumption.
            sequence=self._request('resume',lease_id)
            return self._wait('resumed',lease_id,sequence,timeout_ms)
        except BaseException:
            self._poisoned=True
            raise

    @contextmanager
    def paused(self):
        lease=self.acquire()
        try:
            yield lease
        except BaseException as original:
            try:
                self.release(lease)
            except BaseException as cleanup:
                original.add_note('Read-lease release failed: '+str(cleanup))
            raise
        else:
            self.release(lease)


class RetainedTarget:
    """Read-only Windows handle bound to a caller-authenticated candidate file.

    Disk/path/process identity and a PE32 mapping are checked. Full loaded-code
    authentication is still the debugger host's contract, not inferred here.
    """
    def __init__(self, *, identity, candidate_path):
        require(os.name=='nt', 'Retained process reads require Windows')
        import run_original_game_smoke as owned
        self.owned=owned
        self.identity=deepcopy(identity)
        self.candidate_path=Path(candidate_path).resolve()
        require(owned.sha(self.candidate_path)==identity['candidate_sha256'], 'Candidate file hash differs')
        self.kernel, _, _ = owned.win32()
        self.handle=owned.require(self.kernel.OpenProcess(0x1000|0x100000|0x10,False,identity['pid']), 'retain read-only observation target')
        self.kernel.ReadProcessMemory.argtypes=[W.HANDLE,C.c_void_p,C.c_void_p,C.c_size_t,C.POINTER(C.c_size_t)]
        self.kernel.ReadProcessMemory.restype=W.BOOL
        try:
            self.check_owner()
            base=identity['image_base']
            header=self.read_exact(base,64)
            require(header[:2]==b'MZ', 'Expected main-image mapping is absent')
            pe_offset=int.from_bytes(header[60:64],'little')
            require(64<=pe_offset<=4096, 'Unexpected PE header offset')
            pe_header=self.read_exact(base+pe_offset,26)
            require(pe_header[:6]==b'PE\0\0\x4c\x01' and pe_header[24:26]==b'\x0b\x01',
                    'Owned mapping is not a PE32 x86 image')
        except BaseException:
            self.close()
            raise

    def check_owner(self):
        require(self.handle and self.kernel.WaitForSingleObject(self.handle,0)==258, 'Owned target is no longer live')
        actual=self.owned.process_identity(self.kernel,self.handle)
        require(actual['creation_filetime']==self.identity['creation_filetime'] and
                Path(actual['path']).resolve()==self.candidate_path, 'Owned target path/creation changed')
        return deepcopy(self.identity)

    def read_exact(self, address, size):
        self.check_owner()
        require(type(address) is int and type(size) is int and 0<size<=1024*1024 and
                0x10000<=address<=0x7FFE0000-size, 'Read outside bounded PE32 user address range')
        buffer=C.create_string_buffer(size); actual=C.c_size_t()
        require(bool(self.kernel.ReadProcessMemory(self.handle,address,buffer,size,C.byref(actual))) and
                actual.value==size, 'Short or unmapped owned-process read')
        return buffer.raw

    def close(self):
        if getattr(self,'handle',None):
            self.kernel.CloseHandle(self.handle); self.handle=None
