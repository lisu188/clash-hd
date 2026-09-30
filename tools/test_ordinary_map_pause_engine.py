"""Opt-in real DbgEng lease tests on a marked, eight-byte synthetic loop only."""
import hashlib
import inspect
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import threading
import time
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'tools')]
import ordinary_map_pause_client as client
import ordinary_map_pause_host as host
import real_exe_smoke as smoke
import test_framed_loaded_probe_engine as fixture_source


def sha(data):return hashlib.sha256(data).hexdigest()


def counter_fixture():
    data,_,_=fixture_source.executable_fixture()
    view=fixture_source.probe.pe.inspect_pe(data)
    counter=view.image_base+0x2000
    loop=b'\xff\x05'+struct.pack('<I',counter)+b'\xeb\xf8'
    mutable=bytearray(data)
    at=view.file_offset(0x10e0,len(loop));mutable[at:at+len(loop)]=loop
    return bytes(mutable),counter


def restricted_source():
    source=host.render_source(smoke.HARNESS)
    old='if (disk.size()<4096 || memcmp(disk.data(),"MZ",2))'
    replacement='if (disk.size()<4096 || memcmp(disk.data(),"MZ",2) || memcmp(disk.data()+64,"CLASH_HD_DEBUGGER_FIXTURE_V1",28))'
    assert source.count(old)==1
    source=source.replace(old,replacement)
    old='DEBUG_ONLY_THIS_PROCESS),"CreateProcess real EXE")'
    assert source.count(old)==1
    return source.replace(old,'DEBUG_ONLY_THIS_PROCESS | CREATE_NO_WINDOW),"CreateProcess synthetic fixture")')


EXPECTED_CASES = {'pause-resume-counter', 'expired-lease'}
PUBLICATION_CASES = {'transient-reader', 'permanent-reader'}
RETRY_ROW = re.compile(r'^REAL_ACK_REPLACE_RETRY file=ack\.json seq=1 attempt=([1-9][0-9]*) winerror=(5|32) deadline_tick_ms=([0-9]+)$', re.M)
EXPIRY_ROW = re.compile(r'^REAL_ACK_REPLACE_EXPIRED file=ack\.json started_tick_ms=([0-9]+) deadline_tick_ms=([0-9]+) now_tick_ms=([0-9]+) attempts=([1-9][0-9]*)$', re.M)


class DenyingAckReader:
    """Actual Windows read handle permitting other reads/writes, never deletion."""
    def __init__(self, path):
        if os.name!='nt':raise AssertionError('Real ACK reader requires Windows')
        self.kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        self.kernel.CreateFileW.argtypes=[wintypes.LPCWSTR,wintypes.DWORD,wintypes.DWORD,
            ctypes.c_void_p,wintypes.DWORD,wintypes.DWORD,wintypes.HANDLE]
        self.kernel.CreateFileW.restype=wintypes.HANDLE
        self.kernel.CloseHandle.argtypes=[wintypes.HANDLE]
        self.kernel.CloseHandle.restype=wintypes.BOOL
        self.kernel.GetTickCount64.argtypes=[]
        self.kernel.GetTickCount64.restype=ctypes.c_ulonglong
        self.lock=threading.Lock();self.closed=False
        self.handle=self.kernel.CreateFileW(str(path),0x80000000,0x1|0x2,None,3,0x80|0x00200000,None)
        if self.handle in (None,ctypes.c_void_p(-1).value):
            raise OSError(ctypes.get_last_error(),'Open real ACK reader without delete sharing')

    def close(self):
        with self.lock:
            if self.handle is not None:
                if not self.kernel.CloseHandle(self.handle):
                    raise OSError(ctypes.get_last_error(),'Close real ACK reader')
                self.handle=None;self.closed=True


def publication_proofs_pass(row):
    cases=row.get('publication_cases',[])
    return (len(cases)==len(PUBLICATION_CASES)
            and {item.get('case') for item in cases}==PUBLICATION_CASES
            and all(item.get('passed') is True and item.get('actual_retry_observed') is True
                    and item.get('reader_closed') is True for item in cases)
            and next(item for item in cases if item['case']=='transient-reader').get('released_after_retry') is True
            and all(next(item for item in cases if item['case']=='permanent-reader').get(key) is True
                    for key in ('deadline_expired','target_cleanup_verified','fixture_file_unchanged','held_through_terminal','ready_ack_unchanged'))
            and next(item for item in cases if item['case']=='permanent-reader').get('host_returncode')==2)


def report_payload(records, compiled_source_sha256=None):
    completed = (len(records) == len(EXPECTED_CASES)
                 and {row['case'] for row in records} == EXPECTED_CASES
                 and all(row.get('completed') is True for row in records))
    return dict(schema='clash95_pause_engine_fixture_v1', game_runtime_executed=False,
        fixture_runtime_executed=any(row.get('fixture_entry_observed') is True for row in records),
        host_started=any(row.get('host_started') is True for row in records), manual_input_proof=False,
        host_source_sha256=sha(Path(host.__file__).read_bytes()),
        client_source_sha256=sha(Path(client.__file__).read_bytes()),
        fixture_source_sha256=sha(Path(__file__).read_bytes()),
        inherited_host_sha256=sha(Path(smoke.__file__).read_bytes()),
        compiled_source_sha256=compiled_source_sha256,
        expected_cases=len(EXPECTED_CASES), completed=completed,
        passed=completed and all(row['passed'] for row in records)
            and publication_proofs_pass(next(row for row in records if row['case']=='pause-resume-counter')),
        cases=records)


class ReportTests(unittest.TestCase):
    """Portable evidence-report checks; these launch and write nothing."""
    def test_setup_and_pre_entry_failures_do_not_claim_fixture_execution(self):
        for rows in ([], [dict(case='pause-resume-counter', passed=False, completed=False)],
                     [dict(case='pause-resume-counter', passed=False, completed=True, host_started=True)]):
            with self.subTest(rows=rows):
                result=report_payload(rows)
                self.assertFalse(result['fixture_runtime_executed'])
                self.assertFalse(result['completed'])
                self.assertFalse(result['passed'])
                self.assertEqual(result['host_started'], bool(rows and rows[0].get('host_started')))

    def test_both_distinct_cases_must_finish_before_complete_or_pass(self):
        rows=[dict(case=name, passed=True, completed=True, host_started=True,
                   fixture_entry_observed=True) for name in sorted(EXPECTED_CASES)]
        positive=next(row for row in rows if row['case']=='pause-resume-counter')
        positive['publication_cases']=[dict(case='transient-reader',passed=True,actual_retry_observed=True,
            reader_closed=True,released_after_retry=True),dict(case='permanent-reader',passed=True,
            actual_retry_observed=True,reader_closed=True,deadline_expired=True,target_cleanup_verified=True,
            fixture_file_unchanged=True,held_through_terminal=True,ready_ack_unchanged=True,host_returncode=2)]
        result=report_payload(rows)
        self.assertTrue(result['fixture_runtime_executed'])
        self.assertTrue(result['completed'])
        self.assertTrue(result['passed'])
        for incomplete in ([rows[0]], [rows[0], rows[0]],
                           [rows[0], dict(rows[1], completed=False)]):
            result=report_payload(incomplete)
            self.assertFalse(result['completed'])
            self.assertFalse(result['passed'])
        result=report_payload([rows[0], dict(rows[1], passed=False)])
        self.assertTrue(result['completed'])
        self.assertFalse(result['passed'])

    def test_missing_failed_or_incomplete_real_publication_proofs_cannot_pass(self):
        transient=dict(case='transient-reader',passed=True,actual_retry_observed=True,reader_closed=True,
                       released_after_retry=True)
        permanent=dict(case='permanent-reader',passed=True,actual_retry_observed=True,reader_closed=True,
                       deadline_expired=True,target_cleanup_verified=True,fixture_file_unchanged=True,
                       held_through_terminal=True,ready_ack_unchanged=True,host_returncode=2)
        for cases in ([],[transient],[transient,transient],[transient,dict(permanent,passed=False)],
                      [dict(transient,released_after_retry=False),permanent],
                      [transient,dict(permanent,deadline_expired=False)],
                      [transient,dict(permanent,held_through_terminal=False)],
                      [transient,dict(permanent,actual_retry_observed=False)],
                      [transient,dict(permanent,reader_closed=False)],
                      [transient,dict(permanent,ready_ack_unchanged=False)],
                      [transient,dict(permanent,host_returncode=0)],
                      [transient,dict(permanent,target_cleanup_verified=False)]):
            with self.subTest(cases=cases):
                rows=[dict(case='pause-resume-counter',passed=True,completed=True,publication_cases=cases),
                      dict(case='expired-lease',passed=True,completed=True)]
                self.assertTrue(report_payload(rows)['completed'])
                self.assertFalse(report_payload(rows)['passed'])

    def test_reader_and_watcher_require_real_handles_and_actual_new_retry_marker(self):
        reader=inspect.getsource(DenyingAckReader)
        self.assertIn('CreateFileW(str(path),0x80000000,0x1|0x2,None,3,0x80|0x00200000,None)',reader)
        self.assertNotIn('0x4',reader)
        watcher=inspect.getsource(PauseEngineTests.acquire_with_transient_reader)
        self.assertLess(watcher.index('RETRY_ROW.search(text)'),watcher.index('reader.close()'))
        self.assertIn('text=logpath.read_text(errors=',watcher)
        self.assertIn('[offset:]',watcher)
        self.assertIn('finally:',watcher)
        self.assertIn('watcher.join(timeout=2)',watcher)
        self.assertIn('reader.close()',watcher)
        permanent=inspect.getsource(PauseEngineTests.permanent_reader_case)
        self.assertLess(permanent.index('process.wait(timeout=7)'),permanent.index('reader.close()'))
        self.assertIn('with self.assertRaises(client.LeaseError):peer.acquire(timeout_ms=4000)',permanent)
        self.assertIn('self.assertLessEqual(bound-started,1000)',permanent)


@unittest.skipUnless(os.name=='nt' and os.environ.get('CLASH_PAUSE_ENGINE_INTEGRATION')=='1',
                     'opt-in isolated Windows synthetic pause-engine lane required')
class PauseEngineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='clash-pause-engine-')
        cls.addClassCleanup(cls.temp.cleanup)
        cls.root=Path(cls.temp.name)
        cls.records=[]
        cls.addClassCleanup(cls.save_report)
        source=restricted_source()
        cls.compiled_source_sha256=sha(source.encode())
        cpp=cls.root/'lease-engine.cpp';cpp.write_text(source,encoding='utf-8')
        cls.runner=cls.root/'lease-engine.exe'
        compiler=shutil.which('cl.exe')
        if not compiler:raise AssertionError('MSVC x86 environment required')
        result=subprocess.run([compiler,'/nologo','/EHsc','/W4','/O2','/MT',str(cpp),
            '/Fe:'+str(cls.runner),'/Fo:'+str(cls.root/'lease-engine.obj'),'/link','/MACHINE:X86','user32.lib','gdi32.lib'],
            cwd=cls.root,capture_output=True,text=True,timeout=60,creationflags=subprocess.CREATE_NO_WINDOW)
        if result.returncode:raise AssertionError(result.stdout+result.stderr)

    @classmethod
    def save_report(cls):
        name=os.environ.get('CLASH_PAUSE_ENGINE_REPORT')
        if not name:return
        data=report_payload(cls.records,getattr(cls,'compiled_source_sha256',None))
        Path(name).write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')

    def acquire_with_transient_reader(self, peer, process, logpath, directory, row):
        proof=dict(case='transient-reader',passed=False,actual_retry_observed=False,
                   reader_closed=False,released_after_retry=False)
        row.setdefault('publication_cases',[]).append(proof)
        offset=len(logpath.read_text(errors='replace'))
        reader=DenyingAckReader(directory/'ack.json')
        stop=threading.Event();observed=threading.Event();errors=[]
        def release_on_retry():
            try:
                # Generic service can wait up to one existing 1000ms event
                # cycle before seeing the request. Its publication budget
                # starts later, at the logged retry's deadline.
                end=time.monotonic()+4
                while not stop.is_set() and time.monotonic()<end:
                    text=logpath.read_text(errors='replace')[offset:]
                    retry=RETRY_ROW.search(text)
                    if retry:
                        proof['retry_marker']=retry.group(0)
                        proof['actual_retry_observed']=True
                        proof['retry_observed_tick_ms']=reader.kernel.GetTickCount64()
                        if proof['retry_observed_tick_ms']>=int(retry.group(3)):
                            raise AssertionError('Reader retry marker arrived after publication deadline')
                        reader.close()
                        proof['released_after_retry']=True
                        observed.set();return
                    if process.poll() is not None:raise AssertionError('Host exited before actual replace retry')
                    stop.wait(.001)
                raise AssertionError('No actual replace retry within bounded reader watch')
            except BaseException as error:errors.append(repr(error))
        watcher=threading.Thread(target=release_on_retry,name='ack-reader-release',daemon=True)
        watcher.start()
        try:
            lease=peer.acquire(timeout_ms=4000)
            watcher.join(timeout=2)
            self.assertFalse(watcher.is_alive(),'Reader watcher did not finish')
            self.assertEqual(errors,[])
            self.assertTrue(observed.is_set(),'Reader was not released after actual retry')
            self.assertTrue(reader.closed)
            self.assertTrue(proof['released_after_retry'])
            proof['passed']=True
            return lease
        finally:
            stop.set();watcher.join(timeout=2)
            reader.close()
            watcher.join(timeout=2)
            proof['reader_closed']=reader.closed
            proof['watcher_errors']=errors
            self.assertFalse(watcher.is_alive(),'Reader watcher survived cleanup')

    def permanent_reader_case(self, parent, row):
        proof=dict(case='permanent-reader',passed=False,actual_retry_observed=False,
                   reader_closed=False,held_through_terminal=False,deadline_expired=False)
        row.setdefault('publication_cases',[]).append(proof)
        root=parent/'permanent-reader';root.mkdir()
        directory=root/'control';client.prepare_control(directory)
        image,_counter=counter_fixture();target=root/'fixture.exe';target.write_bytes(image)
        capture=root/'capture';capture.mkdir();logpath=root/'host.log'
        process=None;retained=None;reader=None
        try:
            with logpath.open('w',encoding='utf-8') as log:
                process=subprocess.Popen([str(self.runner),str(target),str(capture),'10','proxy',str(directory)],
                    cwd=root,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW,
                    env=dict(os.environ,_NT_SYMBOL_PATH='.',_NT_ALT_SYMBOL_PATH=''))
                end=time.monotonic()+12
                while not (directory/'ack.json').exists():
                    if process.poll() is not None:raise AssertionError(logpath.read_text(errors='replace'))
                    if time.monotonic()>=end:raise AssertionError('No bounded permanent-reader readiness')
                    time.sleep(.01)
                ready_bytes=(directory/'ack.json').read_bytes();ack=json.loads(ready_bytes)
                identity=dict(pid=ack['pid'],creation_filetime=ack['creation_filetime'],
                              image_base=ack['image_base'],candidate_sha256=sha(image))
                text=logpath.read_text(errors='replace')
                self.assertIn(f"REAL_LOADED pid={identity['pid']} base=00400000",text)
                self.assertIn('REAL_EXE_ENTRY observed=1',text)
                proof['fixture_entry_observed']=True
                retained=client.RetainedTarget(identity=identity,candidate_path=target)
                peer=client.PauseClient(directory,identity=identity,check_owner=retained.check_owner,
                                      host_alive=lambda:process.poll() is None)
                peer.wait_ready()
                reader=DenyingAckReader(directory/'ack.json')
                requested=time.monotonic()
                with self.assertRaises(client.LeaseError):peer.acquire(timeout_ms=4000)
                process.wait(timeout=7)
                proof['terminal_seconds_after_request']=time.monotonic()-requested
                self.assertLessEqual(proof['terminal_seconds_after_request'],7)
                self.assertEqual(process.returncode,2)
                self.assertFalse(reader.closed)
                proof['held_through_terminal']=True
                self.assertEqual(retained.kernel.WaitForSingleObject(retained.handle,5000),0)
                proof['target_cleanup_verified']=True
                with self.assertRaises(client.LeaseError):peer.acquire()
                self.assertEqual((directory/'ack.json').read_bytes(),ready_bytes)
                proof['ready_ack_unchanged']=True
                self.assertEqual(target.read_bytes(),image)
                proof['fixture_file_unchanged']=True
            final=logpath.read_text(errors='replace')
            retries=RETRY_ROW.findall(final);self.assertTrue(retries)
            proof['actual_retry_observed']=True
            proof['retry_count']=len(retries)
            expiry=EXPIRY_ROW.findall(final);self.assertEqual(len(expiry),1)
            started,bound,now,attempts=map(int,expiry[0])
            proof['publication_started_tick_ms']=started;proof['publication_deadline_tick_ms']=bound
            proof['publication_expired_tick_ms']=now;proof['publication_elapsed_ms']=now-started
            proof['publication_attempts']=attempts
            self.assertGreater(bound,started)
            self.assertLessEqual(bound-started,1000)
            self.assertGreaterEqual(now,bound)
            self.assertLessEqual(now-started,1500)
            self.assertEqual(attempts,len(retries))
            self.assertTrue(all(int(deadline)==bound for _attempt,_error,deadline in retries))
            self.assertEqual([int(attempt) for attempt,_error,_deadline in retries],list(range(1,attempts+1)))
            proof['deadline_expired']=True
            self.assertIn('lease acknowledgment atomic replace deadline expired',final)
            self.assertIn('REAL_CLEANUP absent=1',final)
            self.assertNotIn('REAL_END entered=1 exited=0 exception_stop=0',final)
            proof['passed']=True
        finally:
            # A failure may stop this fixture early; a passing proof requires
            # natural terminal failure and cleanup before this reader closes.
            if reader:
                reader.close();proof['reader_closed']=reader.closed
            if process and process.poll() is None:
                process.kill();process.wait(timeout=10)
            if retained:
                proof['target_cleanup_verified']=retained.kernel.WaitForSingleObject(retained.handle,5000)==0
                retained.close()
            proof['host_returncode']=process.returncode if process else None
            proof['log']=logpath.read_text(errors='replace') if logpath.exists() else ''

    def execute(self, expire):
        row=dict(case='expired-lease' if expire else 'pause-resume-counter', passed=False,
                 completed=False, host_started=False, fixture_entry_observed=False)
        self.records.append(row)
        with tempfile.TemporaryDirectory(prefix='case-',dir=self.root) as tmp:
            root=Path(tmp);directory=root/'control';client.prepare_control(directory)
            image,counter=counter_fixture();target=root/'fixture.exe';target.write_bytes(image)
            row['fixture_sha256']=sha(image);row['counter_address']=counter
            capture=root/'capture';capture.mkdir()
            logpath=root/'host.log';retained=None;process=None
            try:
                with logpath.open('w',encoding='utf-8') as log:
                    process=subprocess.Popen([str(self.runner),str(target),str(capture),'10','proxy',str(directory)],
                        cwd=root,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW,
                        env=dict(os.environ,_NT_SYMBOL_PATH='.',_NT_ALT_SYMBOL_PATH=''))
                    row['host_started']=True
                    end=time.monotonic()+12
                    while not (directory/'ack.json').exists():
                        if process.poll() is not None:raise AssertionError(logpath.read_text(errors='replace'))
                        if time.monotonic()>=end:raise AssertionError('No bounded host readiness')
                        time.sleep(.01)
                    ack=json.loads((directory/'ack.json').read_text())
                    identity=dict(pid=ack['pid'],creation_filetime=ack['creation_filetime'],
                                  image_base=ack['image_base'],candidate_sha256=sha(image))
                    text=logpath.read_text(errors='replace')
                    self.assertIn(f"REAL_LOADED pid={identity['pid']} base=00400000",text)
                    self.assertIn('REAL_EXE_ENTRY observed=1',text)
                    row['fixture_entry_observed']=True
                    retained=client.RetainedTarget(identity=identity,candidate_path=target)
                    peer=client.PauseClient(directory,identity=identity,check_owner=retained.check_owner,
                                          host_alive=lambda:process.poll() is None)
                    peer.wait_ready()
                    lease=peer.acquire() if expire else self.acquire_with_transient_reader(peer,process,logpath,directory,row)
                    peer.check_lease(lease)
                    before=retained.read_exact(counter,4)
                    time.sleep(.08)
                    peer.check_lease(lease)
                    self.assertEqual(before,retained.read_exact(counter,4))
                    row['counter_stable_while_paused']=True
                    if expire:
                        process.wait(timeout=25)
                        self.assertEqual(process.returncode,2)
                        with self.assertRaises(client.LeaseError):peer.check_lease(lease)
                        row['expired_lease_rejected']=True
                    else:
                        peer.release(lease)
                        with self.assertRaises(client.LeaseError):peer.check_lease(lease)
                        time.sleep(.08)
                        second=peer.acquire()
                        changed=retained.read_exact(counter,4)
                        self.assertNotEqual(before,changed)
                        peer.check_lease(second)
                        self.assertEqual(changed,retained.read_exact(counter,4))
                        peer.release(second)
                        row['counter_changed_after_resume']=True
                        process.wait(timeout=15)
                        self.assertEqual(process.returncode,0)
                    row['acknowledgments']=peer.receipts
                    self.assertEqual(retained.kernel.WaitForSingleObject(retained.handle,5000),0)
                    row['retained_target_exited']=True
                    self.assertEqual(target.read_bytes(),image)
                    row['fixture_file_unchanged']=True
                final=logpath.read_text(errors='replace')
                self.assertIn('REAL_CLEANUP absent=1',final)
                if expire:self.assertIn('lease expired; owned target must terminate',final)
                else:self.assertIn('REAL_END entered=1 exited=0 exception_stop=0',final)
                if not expire:
                    self.permanent_reader_case(root,row)
                    self.assertTrue(publication_proofs_pass(row))
                row['passed']=True
            finally:
                if process and process.poll() is None:
                    process.kill();process.wait(timeout=10)
                if retained:
                    row['target_cleanup_verified']=retained.kernel.WaitForSingleObject(retained.handle,5000)==0
                    retained.close()
                row['host_returncode']=process.returncode if process else None
                row['log']=logpath.read_text(errors='replace') if logpath.exists() else ''
                row['completed']=True

    def test_counter_stays_stopped_then_advances_only_after_resume(self):self.execute(False)
    def test_expired_lease_terminates_owned_target_and_cannot_authorize_reads(self):self.execute(True)


if __name__=='__main__':unittest.main(verbosity=2)
