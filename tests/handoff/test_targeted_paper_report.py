"""Evidence integrity and portable reconstruction of the H1/L2 paper companion."""
import importlib.util
import json
from pathlib import Path
import shutil
import pytest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('targeted_report', ROOT/'scripts/analysis/write_targeted_followups_tex.py')
REPORT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(REPORT)
MANIFEST = ROOT/'manuscript/software/targeted-inputs.json'
TEMPLATES = ROOT/'manuscript/software'


def capsule(tmp_path):
    manifest=json.loads(MANIFEST.read_text())
    for relative in manifest['files']:
        target=tmp_path/relative
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(ROOT/relative,target)
    templates=tmp_path/'templates'
    templates.mkdir()
    for p in TEMPLATES.glob('targeted-*.template.tex'):
        shutil.copy2(p,templates/p.name)
    m=tmp_path/'manifest.json'
    shutil.copy2(MANIFEST,m)
    return m,templates


def rebind(tmp_path,manifest_path,relative,data):
    p=tmp_path/relative
    p.write_text(json.dumps(data,indent=2)+'\n')
    m=json.loads(manifest_path.read_text())
    m['files'][relative]=REPORT.digest(p.read_bytes())
    manifest_path.write_text(json.dumps(m,indent=2)+'\n')


def test_full_summaries_and_relocation(tmp_path):
    original=REPORT.render(ROOT,MANIFEST,TEMPLATES)
    m,t=capsule(tmp_path)
    assert REPORT.render(tmp_path,m,t)==original
    assert r'3.08\times10^{-7}' in original['targeted-h1-main.generated.tex']
    assert r'1.56548\times10^{-9}' in original['targeted-l2-si.generated.tex']
    assert r'7.067\%' in original['targeted-l2-si.generated.tex']
    assert '100\\%' in original['targeted-l2-main.generated.tex']


def test_changed_input_is_rejected(tmp_path):
    m,t=capsule(tmp_path)
    with (tmp_path/(REPORT.H1+'function-differences.csv')).open('a') as f:
        f.write('\n')
    with pytest.raises(ValueError,match='SHA256 mismatch'):
        REPORT.render(tmp_path,m,t)


def test_summary_mcse_not_blindly_copied(tmp_path):
    m,t=capsule(tmp_path)
    name=REPORT.L2+'SUMMARY.json'
    s=json.loads((tmp_path/name).read_text())
    s['reference_estimates'][0]['mcse']*=2
    rebind(tmp_path,m,name,s)
    name_a=REPORT.L2+'audit.json'
    audit=json.loads((tmp_path/name_a).read_text())
    audit['source_summary_sha256']=REPORT.digest((tmp_path/name).read_bytes())
    rebind(tmp_path,m,name_a,audit)
    with pytest.raises(ValueError,match='MCSE disagreement'):
        REPORT.render(tmp_path,m,t)


def test_failed_outputs_cannot_be_promoted(tmp_path):
    m,t=capsule(tmp_path)
    name=REPORT.H1+'SUMMARY.json'
    s=json.loads((tmp_path/name).read_text())
    s['failed_paths_promoted']=1
    rebind(tmp_path,m,name,s)
    name_p=REPORT.H1+'provenance.json'
    p=json.loads((tmp_path/name_p).read_text())
    p['source_summary_sha256']=REPORT.digest((tmp_path/name).read_bytes())
    rebind(tmp_path,m,name_p,p)
    with pytest.raises(ValueError,match='boundary changed'):
        REPORT.render(tmp_path,m,t)


def test_unknown_template_token_is_rejected(tmp_path):
    m,t=capsule(tmp_path)
    with (t/'targeted-l2-main.template.tex').open('a') as f:
        f.write('@L2_NOT_MEASURED@')
    with pytest.raises(ValueError,match='unknown template tokens'):
        REPORT.render(tmp_path,m,t)
