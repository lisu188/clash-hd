"""Portable protocol tests; fake host and synthetic identities, no process/input."""
import errno
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import ordinary_map_pause_client as tool


class FakeHost:
    def __init__(self, root):
        self.root=root
        self.session=tool.prepare_control(root)
        self.identity=dict(pid=123,creation_filetime=456,image_base=0x400000,candidate_sha256='a'*64)
        self.tick=1000
        self.alive=True
        self.seq=0
        self.lease=''
        self.ignore=False
        self.publish('ready',False)

    def publish(self, status, paused):
        data=dict(schema=tool.ACK_SCHEMA,session_id=self.session,request_seq=self.seq,
                  status=status,lease_id=self.lease,pid=123,primary_tid=789,
                  creation_filetime=456,image_base=0x400000,
                  deadline_tick_ms=self.tick+20000 if paused else 0,paused=paused)
        (self.root/'ack.json').write_text(json.dumps(data),encoding='ascii')

    def advance(self, seconds):
        self.tick += max(1,int(seconds*1000))
        path=self.root/'request.txt'
        if not self.alive or self.ignore or not path.exists(): return
        raw=path.read_bytes()
        assert raw.endswith(b'\n') and len(raw)<=256
        version,session,seq,op,lease=raw.decode().strip().split(' ')
        assert version=='CLASH_LEASE_V1' and session==self.session
        if int(seq)==self.seq:return
        assert int(seq)==self.seq+1
        self.seq=int(seq)
        if op=='pause':
            self.lease=lease;self.publish('paused',True)
        else:
            assert op=='resume' and lease==self.lease
            self.publish('resumed',False)

    def client(self):
        return tool.PauseClient(self.root,identity=self.identity,
            check_owner=lambda:dict(self.identity),host_alive=lambda:self.alive,
            clock_ms=lambda:self.tick,sleep=self.advance)


class ClientTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory(prefix='clash-lease-fixture-')
        self.addCleanup(temp.cleanup)
        self.host=FakeHost(Path(temp.name)/'control')
        self.client=self.host.client()

    def test_ready_pause_read_and_resume_have_bound_receipts(self):
        self.client.wait_ready()
        with self.client.paused() as lease:
            self.client.check_lease(lease)
            self.assertEqual(lease,dict(schema=tool.LEASE_SCHEMA,lease_id=self.host.lease,
                                      paused=True,**self.host.identity))
            self.assertEqual(self.host.seq,1)
        self.assertEqual([v['status'] for v in self.client.receipts],['ready','paused','resumed'])
        self.assertEqual(self.host.seq,2)
        with self.assertRaisesRegex(tool.LeaseError,'inactive'):
            self.client.check_lease(lease)

    def test_separate_leases_use_new_tokens_and_monotonic_requests(self):
        a=self.client.acquire();self.client.release(a)
        b=self.client.acquire();self.client.release(b)
        self.assertNotEqual(a['lease_id'],b['lease_id'])
        self.assertEqual([v['request_seq'] for v in self.client.receipts],[1,2,3,4])

    def test_existing_directory_is_not_adopted_or_cleared(self):
        before=(self.host.root/'session.token').read_bytes()
        with self.assertRaises(FileExistsError):tool.prepare_control(self.host.root)
        self.assertEqual((self.host.root/'session.token').read_bytes(),before)

    def test_nested_acquire_is_rejected_without_replacing_active_lease(self):
        lease=self.client.acquire()
        with self.assertRaisesRegex(tool.LeaseError,'Nested'):self.client.acquire()
        self.client.check_lease(lease);self.client.release(lease)

    def test_changed_or_released_lease_cannot_authorize_reads(self):
        lease=self.client.acquire()
        for field,value in [('pid',999),('candidate_sha256','b'*64),('lease_id','0'*32),('paused',False)]:
            with self.subTest(field=field),self.assertRaises(tool.LeaseError):
                self.client.check_lease(dict(lease,**{field:value}))
        self.client.release(lease)
        with self.assertRaises(tool.LeaseError):self.client.check_lease(lease)

    def test_owner_exit_and_host_exit_reject_active_leases(self):
        lease=self.client.acquire()
        self.host.alive=False
        with self.assertRaisesRegex(tool.LeaseError,'host exited'):self.client.check_lease(lease)
        self.host.alive=True;self.host.identity['creation_filetime']+=1
        with self.assertRaisesRegex(tool.LeaseError,'identity changed'):self.client.check_lease(lease)

    def test_expired_lease_is_not_resumed_or_reused(self):
        lease=self.client.acquire();self.host.tick+=20001
        with self.assertRaisesRegex(tool.LeaseError,'expired'):self.client.release(lease)
        self.assertEqual(self.host.seq,1)
        with self.assertRaisesRegex(tool.LeaseError,'cannot be reused'):self.client.acquire()

    def test_unresponsive_host_times_out_without_claiming_pause(self):
        self.host.ignore=True
        with self.assertRaisesRegex(tool.LeaseError,'Timed out'):self.client.acquire(timeout_ms=50)
        self.assertIsNone(self.client._active)
        self.assertEqual(self.host.seq,0)

    def test_wrong_session_identity_status_and_sequence_acknowledgments_reject(self):
        lease=self.client.acquire()
        path=self.host.root/'ack.json';original=path.read_text()
        for key,value in [('session_id','0'*32),('pid',456),('primary_tid',0),('request_seq',True),
                          ('request_seq',2),('status','resumed'),('paused',False),('unexpected',1)]:
            with self.subTest(field=key,value=value):
                data=json.loads(original);data[key]=value;path.write_text(json.dumps(data))
                with self.assertRaises(tool.LeaseError):self.client.check_lease(lease)
        path.write_text(original);self.client.release(lease)

    def test_duplicate_and_oversized_acknowledgments_reject(self):
        path=self.host.root/'ack.json';original=path.read_text()
        path.write_text(original[:-1]+',"pid":123}')
        with self.assertRaisesRegex(tool.LeaseError,'Duplicate'):self.client.wait_ready()
        path.write_text(' '*2049)
        with self.assertRaisesRegex(tool.LeaseError,'Invalid acknowledgment file'):self.client.wait_ready()

    def test_exception_inside_read_interval_releases_and_preserves_error(self):
        with self.assertRaisesRegex(ValueError,'decoder mismatch'):
            with self.client.paused():raise ValueError('decoder mismatch')
        self.assertEqual(self.client.receipts[-1]['status'],'resumed')

    def test_failed_release_does_not_hide_read_error(self):
        with self.assertRaisesRegex(ValueError,'read failed') as raised:
            with self.client.paused():
                self.host.alive=False
                raise ValueError('read failed')
        self.assertIn('Read-lease release failed',raised.exception.__notes__[0])
        self.assertTrue(self.client._poisoned)

    def test_native_owner_and_host_query_failures_are_retained_and_poison_session(self):
        for operation in ('host_alive', 'check_owner'):
            with self.subTest(operation=operation):
                peer=self.host.client()
                native=PermissionError(13, 'QueryFullProcessImageName failed')
                native.winerror=5
                calls=[]
                def failed():
                    calls.append(operation)
                    raise native
                setattr(peer,operation,failed)
                original=(self.host.root/'ack.json').read_bytes()
                with self.assertRaises(tool.LeaseError) as caught:peer.acquire()
                failure=caught.exception
                self.assertIs(failure.original_error,native)
                self.assertIs(failure.__cause__,native)
                self.assertEqual(failure.original_error.winerror,5)
                self.assertIs(peer.native_failures[0],failure)
                self.assertTrue(peer._poisoned)
                self.assertIsNone(peer._active)
                self.assertEqual(peer.sequence,0)
                self.assertEqual(peer.receipts,[])
                self.assertFalse((self.host.root/'request.txt').exists())
                self.assertEqual((self.host.root/'ack.json').read_bytes(),original)
                with self.assertRaisesRegex(tool.LeaseError,'cannot be reused'):peer.acquire()
                self.assertEqual(calls,[operation])

    def test_owner_query_failure_during_pause_wait_never_publishes_a_lease(self):
        self.host.ignore=True
        native=PermissionError(13,'target terminated during image-path query')
        native.winerror=5
        calls=[]
        def observe():
            calls.append(self.host.tick)
            if self.host.tick>1000:raise native
            return dict(self.host.identity)
        self.client.check_owner=observe
        with self.assertRaises(tool.LeaseError) as caught:self.client.acquire(timeout_ms=50)
        self.assertIs(caught.exception.__cause__,native)
        self.assertIs(self.client.native_failures[0].original_error,native)
        self.assertEqual(self.client.sequence,1)
        self.assertEqual(self.client.receipts,[])
        self.assertIsNone(self.client._active)
        self.assertTrue(self.client._poisoned)
        request=(self.host.root/'request.txt').read_bytes()
        with self.assertRaisesRegex(tool.LeaseError,'cannot be reused'):self.client.acquire()
        self.assertEqual((self.host.root/'request.txt').read_bytes(),request)
        self.assertEqual(calls[-1],1010)

    def test_native_failure_revokes_active_lease_without_resume_and_preserves_primary_error(self):
        native=PermissionError(13,'retained target identity unavailable')
        def failed():raise native
        with self.assertRaisesRegex(ValueError,'raw read failed') as caught:
            with self.client.paused():
                self.client.check_owner=failed
                raise ValueError('raw read failed')
        self.assertTrue(self.client._poisoned)
        self.assertIsNone(self.client._active)
        self.assertIsNone(self.client._active_sequence)
        self.assertEqual(self.client.sequence,1)
        self.assertEqual([row['status'] for row in self.client.receipts],['paused'])
        self.assertIs(self.client.native_failures[0].original_error,native)
        self.assertIn('Read-lease release failed',caught.exception.__notes__[0])
        with self.assertRaisesRegex(tool.LeaseError,'cannot be reused'):self.client.live()

    def test_invalid_clock_deadline_rejects_pause_acknowledgment(self):
        original=self.host.publish
        def publish(status, paused):
            original(status,paused)
            if paused:
                p=self.host.root/'ack.json';d=json.loads(p.read_text());d['deadline_tick_ms']+=1
                p.write_text(json.dumps(d))
        self.host.publish=publish
        with self.assertRaisesRegex(tool.LeaseError,'exceeds'):self.client.acquire()

    def test_ack_replacement_read_errors_retry_only_inside_original_wait(self):
        native = [PermissionError(errno.EACCES, 'CRT replacement read denied'),
                  FileNotFoundError(errno.ENOENT, 'replacement path absent')]
        path = self.host.root/'ack.json'
        before = path.read_bytes()
        original = Path.read_text
        observed = []
        def read(current, *args, **kwargs):
            if current == path and len(observed) < len(native):
                observed.append(self.host.tick)
                raise native[len(observed)-1]
            return original(current, *args, **kwargs)
        with mock.patch.object(Path, 'read_text', read):
            lease = self.client.acquire(timeout_ms=50)
        self.assertEqual(observed, [1000, 1010])
        self.assertEqual(self.host.tick, 1020)
        self.assertEqual(self.client.sequence, 1)
        self.assertEqual([row['status'] for row in self.client.receipts], ['paused'])
        self.assertEqual(len(self.client.ack_wait_failures), 2)
        for failure, error in zip(self.client.ack_wait_failures, native):
            self.assertIs(failure.original_error, error)
            self.assertEqual(failure.operation, 'acknowledgment read')
        self.assertIsNone(getattr(native[0], 'winerror', None))
        self.assertNotEqual(path.read_bytes(), before)
        self.client.check_lease(lease)
        self.client.release(lease)

    def test_permanent_ack_read_error_expires_without_reset_or_lease(self):
        for code in (None, 5, 32):
            with self.subTest(winerror=code):
                self.host.tick=1000; self.host.seq=0; self.host.lease=''
                self.host.publish('ready', False)
                request=self.host.root/'request.txt'
                if request.exists(): request.unlink()
                peer=self.host.client()
                native=PermissionError(errno.EACCES, 'ack remains unavailable')
                if code is not None: native.winerror=code
                ticks=[]
                def read(*_args, **_kwargs):
                    ticks.append(self.host.tick)
                    raise native
                with mock.patch.object(Path, 'read_text', read):
                    with self.assertRaisesRegex(tool.LeaseError, 'Timed out') as caught:
                        peer.acquire(timeout_ms=50)
                self.assertEqual(ticks, [1000, 1010, 1020, 1030, 1040])
                self.assertEqual(self.host.tick, 1050)
                self.assertIs(caught.exception.original_error, native)
                self.assertIs(caught.exception.__cause__, native)
                self.assertEqual(len(peer.ack_wait_failures), 5)
                self.assertTrue(all(row.original_error is native for row in peer.ack_wait_failures))
                self.assertTrue(peer._poisoned)
                self.assertIsNone(peer._active)
                self.assertEqual(peer.receipts, [])
                with self.assertRaisesRegex(tool.LeaseError, 'cannot be reused'): peer.acquire()

    def test_other_ack_io_errors_fail_immediately_and_keep_original_exception(self):
        native=PermissionError(errno.EACCES, 'unexpected native I/O result')
        native.winerror=87
        with mock.patch.object(Path, 'read_text', side_effect=native):
            with self.assertRaises(tool.LeaseError) as caught:
                self.client.acquire(timeout_ms=50)
        self.assertIs(caught.exception.__cause__, native)
        self.assertIs(caught.exception.original_error, native)
        self.assertEqual(self.host.tick, 1000)
        self.assertEqual(len(self.client.ack_wait_failures), 1)
        self.assertTrue(self.client._poisoned)
        self.assertIsNone(self.client._active)

    def test_ack_retry_rechecks_owner_before_another_read(self):
        native=PermissionError(errno.EACCES, 'replacement read denied')
        original=Path.read_text
        count=0
        def read(path, *args, **kwargs):
            nonlocal count
            count+=1
            if count==1: raise native
            return original(path, *args, **kwargs)
        def changed(seconds):
            self.host.advance(seconds)
            self.host.identity['creation_filetime']+=1
        self.client.sleep=changed
        with mock.patch.object(Path, 'read_text', read):
            with self.assertRaisesRegex(tool.LeaseError, 'identity changed'):
                self.client.acquire(timeout_ms=50)
        self.assertEqual(count, 1)
        self.assertEqual(self.host.tick, 1010)
        self.assertIsNone(self.client._active)
        self.assertEqual(self.client.receipts, [])
        self.assertIs(self.client.ack_wait_failures[0].original_error, native)

    def test_ack_retry_cannot_hide_a_later_invalid_acknowledgment(self):
        native=PermissionError(errno.EACCES, 'replacement read denied')
        count=0
        original=self.client.ack
        def read():
            nonlocal count
            count+=1
            if count==1: raise native
            data=original()
            data['lease_id']='0'*32
            return data
        self.client.ack=read
        with self.assertRaisesRegex(tool.LeaseError, 'differs from request'):
            self.client.acquire(timeout_ms=50)
        self.assertEqual(count, 2)
        self.assertEqual(self.host.tick, 1010)
        self.assertEqual(self.client.receipts, [])
        self.assertIsNone(self.client._active)
        self.assertTrue(self.client._poisoned)
        self.assertIs(self.client.ack_wait_failures[0].original_error, native)

    def test_owner_changed_during_valid_ack_read_cannot_publish_receipt(self):
        original=self.client.ack
        def read():
            data=original()
            self.host.identity['creation_filetime']+=1
            return data
        self.client.ack=read
        with self.assertRaisesRegex(tool.LeaseError, 'identity changed'):
            self.client.wait_ready()
        self.assertEqual(self.client.receipts, [])
        self.assertIsNone(self.client._active)

    def test_active_ack_read_failure_revokes_authority_without_retry_or_resume(self):
        lease=self.client.acquire()
        tick=self.host.tick
        before=(self.host.root/'ack.json').read_bytes()
        native=PermissionError(errno.EACCES, 'active acknowledgment unavailable')
        native.winerror=32
        with mock.patch.object(Path, 'read_text', side_effect=native):
            with self.assertRaises(tool.LeaseError) as caught: self.client.check_lease(lease)
        self.assertIs(caught.exception.original_error, native)
        self.assertIs(caught.exception.__cause__, native)
        self.assertIs(self.client.native_failures[0], caught.exception)
        self.assertEqual(self.client.ack_wait_failures, ())
        self.assertEqual(self.host.tick, tick)
        self.assertTrue(self.client._poisoned)
        self.assertIsNone(self.client._active)
        self.assertIsNone(self.client._active_sequence)
        with self.assertRaisesRegex(tool.LeaseError, 'cannot be reused'): self.client.release(lease)
        self.assertEqual(self.client.sequence, 1)
        self.assertEqual((self.host.root/'ack.json').read_bytes(), before)

    def test_valid_ack_returned_after_wait_deadline_cannot_authorize_pause(self):
        self.host.seq=1; self.host.lease='1'*32
        self.host.publish('paused', True)
        original=self.client.ack
        def late():
            result=original()
            self.host.tick+=50
            return result
        self.client.ack=late
        with self.assertRaisesRegex(tool.LeaseError, 'Timed out'):
            self.client._wait('paused', self.host.lease, 1, 50)
        self.assertEqual(self.host.tick, 1050)
        self.assertEqual(self.client.receipts, [])
        self.assertIsNone(self.client._active)


if __name__=='__main__':unittest.main(verbosity=2)
