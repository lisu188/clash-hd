"""Portable protocol tests; fake host and synthetic identities, no process/input."""
import json
from pathlib import Path
import tempfile
import unittest

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

    def test_invalid_clock_deadline_rejects_pause_acknowledgment(self):
        original=self.host.publish
        def publish(status, paused):
            original(status,paused)
            if paused:
                p=self.host.root/'ack.json';d=json.loads(p.read_text());d['deadline_tick_ms']+=1
                p.write_text(json.dumps(d))
        self.host.publish=publish
        with self.assertRaisesRegex(tool.LeaseError,'exceeds'):self.client.acquire()


if __name__=='__main__':unittest.main(verbosity=2)
