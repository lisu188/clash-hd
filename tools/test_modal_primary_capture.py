"""Synthetic, offline adapter fixtures. No game, debugger, or process calls."""
import copy
import json
from pathlib import Path
import re
import struct
import tempfile
import unittest
from unittest.mock import patch

import modal_primary_capture as tool
import modal_primary_surface_audit as audit
import test_modal_primary_trace as native
import test_framed_primary_surface as frozen


def sequence_fixture(checkpoint='final-ready',cursor=1):
    text,packet,_=native.native_fixture(checkpoint=checkpoint,barracks_cursor=cursor)
    packet['primary_capture']={}
    lines=['MPRI_NATIVE_CONTRACT_PASS']
    for line in text.splitlines():
        lines.append(line)
        if line=='MPCAP_PRIMARY_OBSERVERS_ARM':
            lines+=['MPRI_LOCK_CALL tid=2345 esp=00300000 backend=28000000 surface=28001000 descriptor=28000038 rect=0 flags=1 event=0',
                    'MPRI_LOCK_RETURN tid=2345 esp=00300014 backend=28000000 hr=0 surface=28001000 descriptor=28000038 pixels=29000000 size=(800,600) pitch=800']
        if line.startswith('MPCAP_CHECKPOINT name='):
            name=re.search(r'name=([a-z-]+)',line)[1];eip=re.search(r'eip=([0-9a-f]+)',line)[1];esp=re.search(r'esp=([0-9a-f]+)',line)[1]
            lines.append(f'MPRI_CHECKPOINT name={name} tid=2345 eip={eip} esp={esp} backend=28000000 surface=28001000 palette=28002000 pixels=29000000 size=(800,600) pitch=800')
    return '\n'.join(lines)+'\n',packet


def core(log,packet,checkpoint='final-ready'):
    sequence=tool.route.evaluate_sequence(log,packet,checkpoint=checkpoint)
    primary=tool.route.evaluate_primary_route(log,packet,sequence,checkpoint=checkpoint)
    return dict(primary_route_sequence=primary,modal_sequence=sequence)


class SequenceTests(unittest.TestCase):
    def evaluate(self,log,packet,checkpoint='final-ready'):
        return tool.evaluate_primary_sequence(log,packet,core(log,packet,checkpoint),checkpoint)

    def test_all_named_prefixes_use_actual_native_checkpoints(self):
        for cursor in (0,1):
            for name in tool.CHECKPOINTS:
                log,packet=sequence_fixture(name,cursor);c=core(log,packet,name)
                self.assertTrue(c['modal_sequence']['sequence_passed'],c['modal_sequence']['failures'])
                self.assertTrue(c['primary_route_sequence']['passed'],c['primary_route_sequence']['failures'])
                result=self.evaluate(log,packet,name)
                self.assertTrue(result['passed']);self.assertEqual(result['checkpoint'],name)
                self.assertEqual(len(result['checkpoints']),tool.CHECKPOINTS.index(name)+1)
                self.assertEqual(result['checkpoints'][-1]['canvas']['event'],'CHECKPOINT')

    def test_missing_duplicate_prefixed_malformed_and_unknown_observations_fail(self):
        log,packet=sequence_fixture();lines=log.splitlines()
        for index,line in enumerate(lines):
            if not line.startswith('MPRI_'):continue
            for mutation in (lines[:index]+lines[index+1:],lines[:index]+[line]+lines[index:],
                             lines[:index]+[' '+line]+lines[index+1:],lines[:index]+['0:000> '+line]+lines[index+1:]):
                with self.subTest(line=line[:40]),self.assertRaises((ValueError,IndexError)):
                    self.evaluate('\n'.join(mutation),packet)
        with self.assertRaises(ValueError):self.evaluate(log+'MPRI_UNKNOWN\n',packet)

    def test_lock_pairing_range_and_current_palette_fail_closed(self):
        log,packet=sequence_fixture()
        for old,new in [('esp=00300014','esp=00300010'),('descriptor=28000038','descriptor=2800003c'),
                        ('rect=0 flags=1','rect=1 flags=1'),('flags=1 event=0','flags=0 event=0'),
                        ('flags=1 event=0','flags=1 event=1'),('hr=0 surface','hr=80004005 surface'),
                        ('pitch=800','pitch=640'),('pixels=29000000','pixels=fffff000'),
                        ('palette=28002000','palette=0'),('backend=28000000 hr','backend=28000004 hr')]:
            with self.subTest(mutation=new),self.assertRaises(ValueError):self.evaluate(log.replace(old,new),packet)

    def test_lock_before_arming_or_after_last_pause_rejected(self):
        log,packet=sequence_fixture();lines=log.splitlines();pair=[l for l in lines if l.startswith(('MPRI_LOCK_CALL','MPRI_LOCK_RETURN'))]
        moved='\n'.join(pair+[l for l in lines if l not in pair])
        with self.assertRaises(ValueError):self.evaluate(moved,packet)
        with self.assertRaises(ValueError):self.evaluate(log+'\n'.join(pair)+'\n',packet)
        accepted=self.evaluate(log+'quit:\nntdll!DbgBreakPoint:\n',packet)
        self.assertTrue(accepted['passed'])

    def test_prefix_recheck_preserves_exact_core_sequence_verdict(self):
        for name in tool.CHECKPOINTS:
            log,packet=sequence_fixture(name)
            result=audit.bound_capture_report(log.encode(),packet,dict(candidate_sha256=packet['candidate_sha256']),name)
            self.assertTrue(result['passed']);self.assertEqual(result['capture_checkpoint']['core_values']['cursor'],0 if name=='full-published' else 1)

    def test_ready_file_has_real_native_checkpoint_then_observed_primary(self):
        _,packet=sequence_fixture()
        for name in tool.CHECKPOINTS:
            script=tool.ready_script(name,packet)
            self.assertLess(script.index('MCAP_CANVAS event=CHECKPOINT'),script.index('MPCAP_CHECKPOINT name='+name))
            self.assertLess(script.index('MPCAP_CHECKPOINT name='+name),script.index('MPRI_CHECKPOINT name='+name))
            self.assertNotIn('MPCAP_HOST_READY',script);self.assertNotIn('.call',script)
            self.assertIsNone(re.search(r'(?i)(?:^|[;{}])\s*(?:ed|eb|ew|eq|r @)\s+',script))
            self.assertTrue(all(len(line)<4096 for line in script.splitlines()))

    def test_compiler_replaces_exact_seams_and_requires_all_files(self):
        paths={name:'C:/fixture/primary-'+name+'.cdb' for name in tool.CHECKPOINTS}
        contract=dict(proxy_manifest={'path':'C:/proxy.json'},ready_files=paths)
        packet=dict(primary_capture=contract,startup_commands_before_final_g='',byte_checks_before_first_breakpoint='')
        generated='.echo MPCAP_PRIMARY_OBSERVERS_ARM\n'+'\n'.join('.echo MPCAP_HOST_READY name='+n for n in [tool.CHECKPOINTS[0],*tool.CHECKPOINTS])+'\n'
        with patch.object(tool,'contract',return_value=contract),patch.object(tool.route,'compile_probe',return_value=generated):
            compiled=tool.compile_probe(packet)
            self.assertEqual(compiled.count('$$>a<'),5);self.assertIn('be 110 111',compiled)
        for bad in (generated.replace('.echo MPCAP_PRIMARY_OBSERVERS_ARM',''),generated+'\n.echo MPCAP_HOST_READY name=final-ready'):
            with patch.object(tool,'contract',return_value=contract),patch.object(tool.route,'compile_probe',return_value=bad),self.assertRaises(ValueError):
                tool.compile_probe(packet)

    def test_whole_probe_scripts_and_failed_native_route_cannot_be_projected(self):
        log,packet=sequence_fixture();scripts={n:tool.ready_script(n,packet).encode() for n in tool.CHECKPOINTS}
        failure=dict(passed=False,failures=['actual native route rejected'])
        with patch.object(tool,'compile_probe',return_value='canonical\n'),patch.object(tool.route,'compile_probe',return_value='native\n'), \
             patch.object(tool.route,'evaluate_trace',return_value=failure):
            for probe,files in ((b'canonical\n',scripts),(b'canonical\ng\n',scripts),(b'canonical\n',dict(scripts,**{'final-ready':b'forged\n'}))):
                with self.assertRaises(ValueError):tool.evaluate_trace(log,original=b'original',candidate=b'candidate',packet=packet,
                    generated_probe=probe,ready_scripts=files)


class ArtifactTests(unittest.TestCase):
    def test_proxy_source_may_be_identical_bytes_in_another_checkout(self):
        image=bytearray(frozen.synthetic_proxy())
        image[0x470:0x470+len(tool.GET_PALETTE_BYTES)]=tool.GET_PALETTE_BYTES
        image=bytes(image);source=b'// synthetic proxy source, never compiled\n'
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)/'current';current=root/'src/ddraw_surfdump_proxy/ddraw_surfdump_proxy.cpp'
            current.parent.mkdir(parents=True);current.write_bytes(source)
            recorded=Path(folder)/'recorded-checkout/ddraw_surfdump_proxy.cpp'
            recorded.parent.mkdir();recorded.write_bytes(source)
            output=Path(folder)/'ddraw.dll';output.write_bytes(image)
            manifest=Path(folder)/'build.json'
            row=dict(generated_by='clash-hd-surface-dump-proxy',source=str(recorded),output=str(output),
                source_sha256=tool.sha(source),output_sha256=tool.sha(image))
            manifest.write_text(json.dumps(row))
            with patch.object(tool,'ROOT',root),patch.multiple(tool.reader,
                    SUPPORTED_PROXY_SHA256=tool.sha(image),SUPPORTED_PROXY_SOURCE_SHA256=tool.sha(source)):
                result=tool.proxy_context(manifest)
                self.assertEqual(Path(result['source']),recorded.resolve())
                self.assertNotEqual(recorded.resolve(),current.resolve())
                for path,data in ((recorded,source),(current,source),(output,image)):
                    with self.subTest(path=path.name):
                        path.write_bytes(data+b'changed')
                        with self.assertRaises(ValueError):tool.proxy_context(manifest)
                        path.write_bytes(data)
                manifest.write_text(json.dumps(dict(row,source_sha256='0'*64)))
                with self.assertRaises(ValueError):tool.proxy_context(manifest)

    def test_decoder_source_drift_and_numeric_contract_alias_reject_before_compilation(self):
        paths={name:'C:/fixture/primary-'+name+'.cdb' for name in tool.CHECKPOINTS}
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            for relative in tool.SOURCES:
                path=root/relative;path.parent.mkdir(parents=True,exist_ok=True)
                path.write_bytes((tool.ROOT/relative).read_bytes())
            with patch.object(tool,'ROOT',root),patch.object(tool,'proxy_context',return_value={'path':'C:/fixture/proxy.json'}):
                original=tool.contract('C:/fixture/proxy.json',paths)
                helper='tools/hd_layout_asset_composition.py'
                self.assertEqual(original['source_hashes'][helper],tool.sha((root/helper).read_bytes()))
                invalid=copy.deepcopy(original);invalid['lock_start']=float(invalid['lock_start'])
                with patch.object(tool.route,'compile_probe',side_effect=AssertionError('unbound contract reached compiler')):
                    with self.assertRaisesRegex(ValueError,'primary capture contract differs'):
                        tool.compile_probe({'primary_capture':invalid})
                    (root/helper).write_bytes((root/helper).read_bytes()+b'\n# changed decoder\n')
                    with self.assertRaisesRegex(ValueError,'primary capture contract differs'):
                        tool.compile_probe({'primary_capture':original})

    def test_exact_file_hash_size_missing_reparse_and_drift(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'raw';path.write_bytes(b'pixels');reader=tool.Artifacts()
            row=dict(path=str(path),sha256=tool.sha(b'pixels'),bytes=6,address=0x10000)
            self.assertEqual(reader.artifact(row,path=path,size=6,address=0x10000),b'pixels')
            for change in ({'sha256':'0'*64},{'bytes':5},{'bytes':True},{'address':True},{'path':str(path)+'-missing'}):
                with self.assertRaises((ValueError,OSError)):reader.artifact(dict(row,**change),path=path,size=6,address=0x10000)
            with patch.object(Path,'is_symlink',return_value=True),self.assertRaises(ValueError):tool.path_value(path)
            path.write_bytes(b'changed')
            with self.assertRaises(ValueError):reader.unchanged()

    def test_loaded_imagebase_is_the_only_permitted_header_difference(self):
        image=frozen.synthetic_proxy();base=0x30000000
        header=bytearray(image[:512]);struct.pack_into('<I',header,0x98+28,base)
        with patch.object(tool.reader,'SUPPORTED_PROXY_SHA256',tool.sha(image)):
            report=tool.validate_loaded_proxy_header(bytes(header),image,base)
            self.assertEqual(report['measured_load_base'],base)
            with self.assertRaises(ValueError):tool.validate_loaded_proxy_header(image[:512],image,base)
            for offset in (0,0x3c,0x98+28,400):
                bad=header.copy();bad[offset]^=1
                with self.subTest(offset=offset),self.assertRaises(ValueError):tool.validate_loaded_proxy_header(bytes(bad),image,base)

    def test_frozen_reader_is_exactly_pinned(self):
        tool.check_reader()
        with patch.object(tool,'READER_SHA256','0'*64),self.assertRaises(ValueError):tool.check_reader()


if __name__=='__main__':unittest.main()
