"""Portable integrity/failure checks; these do not certify Windows/CUDA support."""
from pathlib import Path
import hashlib,importlib.util,json,subprocess,sys
import pytest
ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('assembly',ROOT/'scripts/windows/assemble_evidence.py');assembly=importlib.util.module_from_spec(spec);spec.loader.exec_module(assembly)
def entry(name,b):return dict(name=name,bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def fixture(tmp_path):
    chunks=[b'one actual evidence array',b'and its continuation'];parts=[]
    for i,b in enumerate(chunks):
        name=f'raw.tar.part{i}';(tmp_path/name).write_bytes(b);parts.append(entry(name,b))
    record=entry('raw.tar',b''.join(chunks));record['parts']=parts
    return {'archives':[record]},b''.join(chunks)
def test_reassembly_is_exact_and_idempotent(tmp_path):
    manifest,want=fixture(tmp_path);assert assembly.assemble(tmp_path,manifest)==['raw.tar']
    assert (tmp_path/'raw.tar').read_bytes()==want
    assert assembly.assemble(tmp_path,manifest)==['raw.tar']
def test_corrupt_chunk_rejected_without_final_output(tmp_path):
    manifest,_=fixture(tmp_path);(tmp_path/'raw.tar.part1').write_bytes(b'bad')
    with pytest.raises(ValueError,match='Checksum'):assembly.assemble(tmp_path,manifest)
    assert not (tmp_path/'raw.tar').exists()
def test_existing_different_archive_is_not_overwritten(tmp_path):
    manifest,_=fixture(tmp_path);(tmp_path/'raw.tar').write_bytes(b'unrelated')
    with pytest.raises(ValueError):assembly.assemble(tmp_path,manifest)
    assert (tmp_path/'raw.tar').read_bytes()==b'unrelated'
@pytest.mark.parametrize('name',['../file','..\\file','C:secrets','/absolute','..'])
def test_manifest_paths_are_basenames(name):
    with pytest.raises(ValueError):assembly.safe_name(name)
@pytest.mark.skipif(sys.platform=='win32',reason='Non-Windows refusal path only')
def test_windows_probe_cannot_pass_on_mac_or_linux(tmp_path):
    target=tmp_path/'environment.json';p=subprocess.run([sys.executable,str(ROOT/'scripts/windows/probe_environment.py'),'--require-windows','--require-cuda','--output',str(target)],capture_output=True)
    assert p.returncode!=0
    record=json.loads(target.read_text());assert record['status']=='failed' and record['gpu_verified'] is False
    assert 'Native Windows required' in record['error']
    assert len(list(tmp_path.glob('environment-*.json')))==1
