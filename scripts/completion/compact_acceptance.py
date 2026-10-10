"""New compact native difference gate; old acceptance is a numerical foundation only."""
from collections import Counter
import json
from pathlib import Path
import xml.etree.ElementTree as ET

from compact_contract import IDENTITY,TECHNICAL_ID
from compact_freeze import verify
from compact_execution import CompactDispatch
from compact_native_evidence import read_native_task
from formal_freeze import relative_file
from formal_runtime import fingerprint,file_hash,atomic_json

FOUNDATION_SHA256='1b71fc0809c5019140768778572681f076bfbf8e7810523f2aed92047c1dd173'
NATIVE_CASES=Counter(test_native_compact_boundary_pause_and_zero_recompute=1,
    test_completion_zero_recompute_and_kind_separation=2,
    test_legacy_registration_reconciled_before_v2_launch=1)
PORTABLE_FILES=tuple('tests/handoff/'+n for n in ('test_compact_contract.py','test_compact_control.py',
    'test_compact_transfer.py','test_compact_freeze_and_cache.py'))
NATIVE_FILES=('tests/windows/test_compact_runtime.py',
    'tests/windows/test_formal_owned_runtime.py::test_completion_zero_recompute_and_kind_separation',
    'tests/windows/test_formal_owned_runtime.py::test_legacy_registration_reconciled_before_v2_launch')


def foundation(path,source_root):
    path=Path(path).resolve();root=path.parent;source_root=Path(source_root)
    if file_hash(path)!=FOUNDATION_SHA256:raise ValueError('Original received v2 acceptance identity differs')
    gate=json.loads(path.read_text());unsigned=dict(gate);digest=unsigned.pop('gate_sha256')
    if fingerprint(unsigned)!=digest or gate['passed'] is not True:raise ValueError('Original native foundation incomplete')
    for name,h in gate['files'].items():
        if file_hash(relative_file(root,name))!=h:raise ValueError('Original foundation evidence changed: '+name)
    prefixes=('r-package/inst/python/parallelbayes/','scripts/completion/inference_','examples/')
    fixed=('scripts/completion/cached_execution.py','scripts/completion/formal_inputs.py',
        'scripts/windows/job_objects.py','scripts/windows/formal_owned_runtime.py',
        'scripts/completion/task_journal.py','scripts/completion/posterior_diagnostics.R')
    numerical={n:h for n,h in gate['source_files'].items() if n.startswith(prefixes) or n in fixed}
    for n,h in numerical.items():
        if file_hash(source_root/n)!=h:raise ValueError('Scientific kernel/native ownership foundation changed: '+n)
    return dict(acceptance_file_sha256=FOUNDATION_SHA256,foundation_root=str(root),unchanged_scientific_sources=numerical,
        old_full_source_gate_used_for_new_execution=False,old_runtime_cases_reexecuted=0,
        old_native_environment=gate['environment'])


def _command(root,name,files,expected_source):
    folder=relative_file(root,name)
    def read(member):
        rel=name+'/'+member
        if files.get(rel)!=file_hash(root/rel):raise ValueError('Unbound native command evidence')
        return json.loads((root/rel).read_text())
    started=read('started.json');finished=read('finished.json');intent=read('job-intent.json')
    if (started['source_sha256']!=expected_source or finished['source_sha256']!=expected_source or
        finished['exit_code']!=0 or finished['error'] is not None or
        finished['job_final']['job_name']!=intent['name'] or finished['job_final']['active_processes']!=0):
        raise ValueError('Native command/actual Job completion failed')
    if started['git_status'] or started['source_commit']!=expected_source_commit(root):
        raise ValueError('Native command must use the clean frozen candidate commit')
    return started,finished


def expected_source_commit(root):
    return json.loads((Path(root)/'protocol.json').read_text())['source_commit']


def integration(root,p,plan,files):
    root=Path(root);dispatch=CompactDispatch(p,plan,root/'source');rows=[]
    for batch,phase in dispatch.phases:
        base=root/'formal-runs'/f'batch-{batch:02d}'/phase
        ptr=json.loads((base/'latest-closed.json').read_text());closed=relative_file(base,ptr['summary'])
        if file_hash(closed)!=ptr['sha256']:raise ValueError('Compact finite closure changed')
        saved=json.loads(closed.read_text());recorded=[]
        for name,h in saved['rows'].items():
            path=relative_file(closed.parent,name)
            if file_hash(path)!=h:raise ValueError('Compact finite row changed')
            row=json.loads(path.read_text());recorded.append(row)
        if saved['summary']!=dispatch.summarize_phase(batch,phase,recorded):raise ValueError('Finite compact complete frame differs')
        for slot in dispatch.slots(batch,phase):
            task=slot['task'];row=next(r for r in recorded if r['task']==task)
            history=(closed.parent/row['history_export']).relative_to(root).as_posix()
            directory=(base/'tasks'/task['id']).relative_to(root).as_posix()
            ledger=(base/'call-costs'/task['id']).relative_to(root).as_posix()
            h=read_native_task(root,task=task,history_export=history,directory=directory,
                ledger=ledger,manifest=files,source_files=p['source_files'])
            desired='valid' if phase=='main' else 'measurement_available'
            if (h['summary']['outcome']!=desired or len(h['attempts'])!=1 or
                h['costs']['verification_only_invocations']<2 or h['binding']['request']['capsule']!=slot['capsule']):
                raise ValueError('Every finite task and two zero-reexecution checks must qualify')
            rows.append(dict(phase=phase,task_id=task['id'],outcome=desired,history_export=history,directory=directory,ledger=ledger))
    if Counter(r['phase'] for r in rows)!=Counter(main=18,cache=16):raise ValueError('Finite 18/16 grid incomplete')
    return rows


def seal_acceptance(bundle,*,foundation_path,portable_xml,portable_command,native_xml,native_command,receiver_receipt,analysis_receipt,analysis_resume_receipt):
    bundle=Path(bundle).resolve();path=bundle/'native-acceptance.json'
    if path.exists():raise FileExistsError('Never overwrite compact acceptance')
    marker,p,plan,binding=verify(bundle)
    if p['identity']!=TECHNICAL_ID or not plan['technical']:raise ValueError('Only compact finite validation may create the new gate')
    baseline=foundation(foundation_path,bundle/'source')
    if binding['environment']['packages']!=baseline['old_native_environment']['packages']:
        raise ValueError('Python package versions differ from the received native environment')
    files={f.relative_to(bundle).as_posix():file_hash(f) for f in bundle.rglob('*') if f.is_file()}
    cases=list(ET.parse(relative_file(bundle,native_xml)).iter('testcase'))
    if Counter(c.attrib['name'].split('[')[0] for c in cases)!=NATIVE_CASES or any(c.find(n) is not None for c in cases for n in ('error','failure','skipped')):
        raise ValueError('All four affected actual native cases must pass, no skips')
    started,_=_command(bundle,native_command,files,p['source_files']['scripts/windows/compact_command.py'])
    if started['command'][1:3]!=['-m','pytest'] or any(n not in started['command'] for n in NATIVE_FILES):
        raise ValueError('Actual selected native pytest command required')
    if '--junitxml' not in started['command'] or Path(started['command'][started['command'].index('--junitxml')+1]).resolve()!=bundle/native_xml:
        raise ValueError('Actual selected native XML output required')
    portable_cases=list(ET.parse(relative_file(bundle,portable_xml)).iter('testcase'))
    if len(portable_cases)!=35 or any(c.find(n) is not None for c in portable_cases for n in ('error','failure','skipped')):
        raise ValueError('All 35 compact portable contract/guard/transfer cases must pass')
    portable_started,_=_command(bundle,portable_command,files,p['source_files']['scripts/windows/compact_command.py'])
    if portable_started['command'][1:3]!=['-m','pytest'] or any(n not in portable_started['command'] for n in PORTABLE_FILES):
        raise ValueError('Actual complete portable pytest command required')
    if '--junitxml' not in portable_started['command'] or Path(portable_started['command'][portable_started['command'].index('--junitxml')+1]).resolve()!=bundle/portable_xml:
        raise ValueError('Actual portable XML output required')
    rows=integration(bundle,p,plan,files)
    for member in (receiver_receipt,analysis_receipt,analysis_resume_receipt):
        if member not in files:raise ValueError('Bounded receive/reconstruction evidence missing')
    receiver=json.loads((bundle/receiver_receipt).read_text())
    first=json.loads((bundle/analysis_receipt).read_text());resumed=json.loads((bundle/analysis_resume_receipt).read_text())
    if (not receiver['passed'] or receiver['whole_tar_created'] is not False or
        first['counts']!={'main':{'analyzed':18},'cache':{'analyzed':16}} or first['evidence_complete'] is not True or
        resumed['new_analyses']!=0 or resumed['reused_analyses']!=34 or resumed['new_sampler_calls']!=0):
        raise ValueError('Complete bounded receive, numerical reconstruction and zero-reanalysis required')
    gate=dict(schema='compact-native-acceptance-v1',platform='win32',passed=True,
        source_commit=p['source_commit'],source_files=p['source_files'],required_versions=p['required_versions'],
        required_R_version=p['required_R_version'],required_R_posterior=p['required_R_posterior'],
        environment=binding['environment'],foundation=baseline,native_tests=4,native_xml=native_xml,native_command=native_command,
        portable_tests=35,portable_xml=portable_xml,portable_command=portable_command,
        finite_protocol_sha256=p['protocol_sha256'],finite_identity=TECHNICAL_ID,integration=rows,
        receiver_receipt=receiver_receipt,analysis_receipt=analysis_receipt,analysis_resume_receipt=analysis_resume_receipt,
        formal_scientific_repetitions=0,files=files)
    gate['gate_sha256']=fingerprint(gate);atomic_json(path,gate);return gate


def verify_acceptance(path,formal_protocol,source_root,*,environment):
    if path is None:raise ValueError('New compact acceptance is required')
    path=Path(path).resolve();root=path.parent
    gate=json.loads(path.read_text());unsigned=dict(gate);digest=unsigned.pop('gate_sha256')
    if gate.get('schema')!='compact-native-acceptance-v1' or not gate['passed'] or fingerprint(unsigned)!=digest:
        raise ValueError('Invalid compact native acceptance')
    for key in ('source_files','required_versions','required_R_version','required_R_posterior'):
        if gate[key]!=formal_protocol[key]:raise ValueError('Compact native acceptance binding differs: '+key)
    if gate['environment']!=environment:raise ValueError('Complete compact environment differs from actual native validation')
    for name,h in gate['files'].items():
        if file_hash(relative_file(root,name))!=h:raise ValueError('Compact acceptance evidence changed: '+name)
    _,p,plan,_=verify(root);integration(root,p,plan,gate['files'])
    for name,h in gate['source_files'].items():
        if file_hash(Path(source_root)/name)!=h:raise ValueError('Actual accepted source differs: '+name)
    return gate
