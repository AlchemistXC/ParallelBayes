"""Transport boundaries only. Standard-library unittest, no sampler calls."""
import hashlib
import json
from pathlib import Path
import stat
import tempfile
import unittest
import warnings
import zipfile
from v5_transport import extract_zip


def fixture(root, members):
    archive=root/'inputs.zip'
    with warnings.catch_warnings():
        warnings.simplefilter('ignore',UserWarning)
        with zipfile.ZipFile(archive,'w') as z:
            for name,data in members:z.writestr(name,data)
    component=dict(id='paper-v5',kind='file',bytes=archive.stat().st_size,
                   sha256=hashlib.sha256(archive.read_bytes()).hexdigest())
    manifest=root/'COMPONENTS.json';manifest.write_text(json.dumps(dict(components=[component])))
    locations=root/'locations.json';locations.write_text(json.dumps({'paper-v5':{'path':str(archive)}}))
    return manifest,hashlib.sha256(manifest.read_bytes()).hexdigest(),locations,archive


class TransportTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
    def tearDown(self):self.temp.cleanup()
    def run_extract(self,m,d,l,limit=100):return extract_zip(m,d,l,'paper-v5',self.root/'out',limit)
    def test_unicode_regular_files(self):
        m,d,l,_=fixture(self.root,[('manuscript/正文.tex',b'abc'),('MANIFEST.json',b'{}')])
        result=self.run_extract(m,d,l)
        self.assertEqual(result['members'],2)
        self.assertEqual((self.root/'out/manuscript/正文.tex').read_bytes(),b'abc')
    def test_link_rejected(self):
        link=zipfile.ZipInfo('link');link.create_system=3;link.external_attr=(stat.S_IFLNK|0o777)<<16
        m,d,l,_=fixture(self.root,[(link,b'target')])
        with self.assertRaises(ValueError):self.run_extract(m,d,l)
        self.assertFalse((self.root/'out').exists())
    def test_disk_guard_and_existing_directory(self):
        m,d,l,_=fixture(self.root,[('a',b'123')])
        with self.assertRaises(ValueError):self.run_extract(m,d,l,2)
        (self.root/'out').mkdir()
        with self.assertRaises(FileExistsError):self.run_extract(m,d,l)
    def test_archive_and_manifest_binding(self):
        m,d,l,a=fixture(self.root,[('a',b'123')])
        with self.assertRaises(ValueError):self.run_extract(m,'0'*64,l)
        a.write_bytes(a.read_bytes()+b'changed')
        with self.assertRaises(ValueError):self.run_extract(m,d,l)
        self.assertFalse((self.root/'out').exists())


def unsafe_test(names):
    def test(self):
        m,d,l,_=fixture(self.root,[(name,b'a') for name in names])
        with self.assertRaises(ValueError):self.run_extract(m,d,l)
        self.assertFalse((self.root/'out').exists())
    return test

for label,names in [('parent',['../escape']),('absolute',['/escape']),('drive',['C:/escape']),
                    ('backslash',['a\\b']),('duplicate',['same','same']),('case_alias',['A','a'])]:
    setattr(TransportTests,'test_unsafe_'+label,unsafe_test(names))

if __name__=='__main__':unittest.main(verbosity=2)
