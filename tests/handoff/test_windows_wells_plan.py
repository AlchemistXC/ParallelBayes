"""Portable handoff contracts only; these tests do not certify Windows/CUDA."""
import importlib.util
from pathlib import Path
import json
import subprocess
import sys
import pytest

ROOT=Path(__file__).resolve().parents[2]


def module():
    s=importlib.util.spec_from_file_location('windows_wells',ROOT/'scripts/completion/windows_wells.py')
    m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m


def test_platform_protocol_preserves_scientific_fields_and_actual_tape():
    original=json.loads((ROOT/'benchmark/protocols/external-wells-validation-v2.json').read_text())
    cpu=module().platform_protocol(original,'cpu','a'*40,{})
    gpu=module().platform_protocol(original,'cuda','a'*40,{})
    for p in [cpu,gpu]:
        assert p['required_os']=='Windows'
        assert p['tape_sha256']==original['tape_sha256']
        assert p['workflows']==original['workflows']
        assert p['base_config']['initial']==original['base_config']['initial']
        assert p['paired_atol']==1e-7 and p['acceptance_mismatches_allowed']==0
        assert p['identity']!=original['identity']
    assert cpu['base_config']['device']=='cpu' and gpu['base_config']['device']=='cuda'
    assert cpu['protocol_sha256']!=gpu['protocol_sha256']
    with pytest.raises(ValueError,match='device'):
        module().platform_protocol(original,'mps','a'*40,{})


@pytest.mark.skipif(sys.platform=='win32',reason='This checks rejection by a non-Windows host')
def test_non_windows_cannot_create_a_windows_runtime_receipt(tmp_path):
    result=subprocess.run([sys.executable,str(ROOT/'scripts/completion/windows_wells.py'),'run',
        '--device','cuda','--source',str(tmp_path/'source'),'--output',str(tmp_path/'output')],
        capture_output=True,text=True)
    assert result.returncode!=0
    assert 'Native Windows' in result.stderr
    assert not (tmp_path/'output').exists()
