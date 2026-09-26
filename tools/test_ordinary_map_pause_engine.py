"""Opt-in real DbgEng lease tests on a marked, eight-byte synthetic loop only."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import tempfile
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
        passed=completed and all(row['passed'] for row in records), cases=records)


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
                    lease=peer.acquire()
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
