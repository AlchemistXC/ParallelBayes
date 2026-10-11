import importlib.util
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('submission_reproduction', Path(__file__).parents[0] / 'reproduction.py')
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)


class ReproductionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.raw = self.root / 'raw'
        self.raw.mkdir()
        (self.raw / 'a').write_bytes(b'saved failure evidence')
        self.row = dict(bytes=(self.raw/'a').stat().st_size, sha256=r.sha(self.raw/'a'))
        self.m = self.root/'members.json'
        self.m.write_text(json.dumps(dict(files={'a':self.row})))
        self.c = dict(id='raw',kind='tree',files=1,bytes=self.row['bytes'],manifest_sha256=r.sha(self.m))

    def tearDown(self):
        self.temp.cleanup()

    def test_complete_tree(self):
        self.assertTrue(r.verify_component(self.c,dict(path=str(self.raw),manifest=str(self.m)))['passed'])

    def test_tampering(self):
        (self.raw/'a').write_bytes(b'corrupt')
        with self.assertRaises(ValueError):r.verify_component(self.c,dict(path=str(self.raw),manifest=str(self.m)))

    def test_missing_and_extra(self):
        (self.raw/'extra').write_bytes(b'new')
        with self.assertRaises(ValueError):r.verify_component(self.c,dict(path=str(self.raw),manifest=str(self.m)))
        (self.raw/'extra').unlink();(self.raw/'a').unlink()
        with self.assertRaises(ValueError):r.verify_component(self.c,dict(path=str(self.raw),manifest=str(self.m)))

    def test_manifest_not_self_trusted(self):
        self.m.write_text('{}')
        with self.assertRaises(ValueError):r.read_pinned(self.m,self.c['manifest_sha256'])

    def archive(self, names):
        p=self.root/'test.tar'
        with tarfile.open(p,'w') as t:
            for name in names:
                m=tarfile.TarInfo(name);m.size=1;t.addfile(m,io.BytesIO(b'x'))
        inv=self.root/'inventory.json'; inv.write_text(json.dumps(dict(identity='test',components=[dict(id='tar',kind='file',bytes=p.stat().st_size,sha256=r.sha(p))])))
        loc=self.root/'locations.json';loc.write_text(json.dumps({'tar':{'path':str(p)}}))
        return inv,loc

    def test_path_escape(self):
        inv,loc=self.archive(['../escaped'])
        with self.assertRaises(ValueError):r.extract(inv,r.sha(inv),loc,'tar',self.root/'out',100)
        self.assertFalse((self.root/'out').exists())

    def test_duplicate_archive_member(self):
        inv,loc=self.archive(['a','a'])
        with self.assertRaises(ValueError):r.extract(inv,r.sha(inv),loc,'tar',self.root/'out',100)

    def test_budget_and_safe_relocation(self):
        inv,loc=self.archive(['nested/a'])
        with self.assertRaises(ValueError):r.extract(inv,r.sha(inv),loc,'tar',self.root/'out',0)
        rec=r.extract(inv,r.sha(inv),loc,'tar',self.root/'out',10)
        self.assertEqual((self.root/'out/nested/a').read_bytes(),b'x')
        self.assertEqual(rec['new_sampler_calls'],0)
        with self.assertRaises(FileExistsError):r.extract(inv,r.sha(inv),loc,'tar',self.root/'out',10)


if __name__=='__main__':unittest.main()
