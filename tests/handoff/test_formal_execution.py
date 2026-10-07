"""Complete dispatch/contract checks; no native sampler or Job is simulated."""
import copy
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

import pytest

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'scripts/completion'),str(ROOT/'scripts/windows')]
from formal_execution import StudyDispatch,validate_worker_scope,load_worker_request,VALIDATION_ID
from formal_study_plan import create_study_plan
from formal_freeze import protocol_document
from formal_runtime import file_hash,fingerprint


@pytest.fixture(scope='module')
def study():
    catalog=json.loads((ROOT/'benchmark/protocols/inference-budget-pilot-mac-v1.json').read_text())
    design=create_study_plan('windows-formal-dispatch-fixture-v1',catalog)
    inventory={n:dict(**{k:r[k] for k in ('model','replicate','dimension','chains','steps')},
                      sha256='a'*64,actual_sha256='b'*64) for n,r in design['input_requirements'].items()}
    binding=dict(source_commit='c'*40,source_files={'fixture.py':'d'*64},external_files={},
        required_versions={'numpy':'fixture'},required_R_version='fixture-R',required_R_posterior='fixture-posterior',
        windows_limits=dict(rss_bytes=8*1024**3,job_commit_bytes=12*1024**3,disk_start_bytes=4*1024**3,
                            disk_floor_bytes=1024**3,poll_seconds=.2),minimum_available_ram_bytes=12*1024**3)
    p=protocol_document(design,catalog,inventory,binding)
    return StudyDispatch(p,design['cache_allocation'],catalog),design,catalog


def test_complete_owned_frames_keep_cache_distinct_and_original_capsule(study):
    dispatch,design,_=study;main=[];cache=[]
    for batch in range(4):
        a=list(dispatch.tasks(batch,'main'));b=list(dispatch.tasks(batch,'cache'))
        assert len(a)==10368 and len(b)==2304
        main+=a;cache+=b
    assert len({t['id'] for t in main+cache})==50688
    assert {t['artifact_kind'] for t in cache}=={'cache_measurement'}
    probe=next(dispatch.slots(0,'cache'))
    assert probe['task']['id']==probe['probe']['id']
    assert probe['capsule']['task']['id']==probe['probe']['primary_task_id']
    assert probe['task']['id']!=probe['capsule']['task']['id']
    expected,digest=dispatch.plan.capsule(probe['probe']['primary_task_id'])
    assert probe['capsule']==expected and probe['capsule_sha256']==digest
    assert dispatch.predecessors(1,'main')==((0,'main'),(0,'cache'))
    assert len(dispatch.predecessors(3,'cache'))==7
    with pytest.raises(ValueError):list(dispatch.tasks(4,'main'))


def rows(dispatch,batch,phase):
    return [dict(task=t,scheduled_index=i+1,outcome='numerical_failure',samples_eligible=False,measurement_available=False,
                 history_export_sha256='e'*64,history_export=t['id']+'.json')
            for i,t in enumerate(dispatch.tasks(batch,phase))]


def test_phase_denominator_retains_failures_interruptions_and_missing(study):
    dispatch,_,_=study;records=rows(dispatch,0,'main')
    records[0]['outcome']='infrastructure_interruption'
    report=dispatch.summarize_phase(0,'main',records)
    assert report['closed'] and report['counts']['numerical_failure']==10367
    assert report['counts']['infrastructure_interruption']==1 and report['closed_is_convergence'] is False
    missing=dispatch.summarize_phase(0,'main',records[:-1])
    assert not missing['closed'] and missing['missing']==1
    pending=copy.deepcopy(records);pending[0]['outcome']='not_run';pending[0].pop('history_export_sha256')
    report=dispatch.summarize_phase(0,'main',pending)
    assert not report['closed'] and report['counts']['not_run']==1
    assert dispatch.summarize_phase(0,'cache',rows(dispatch,0,'cache'))['closed']


def test_wells_cache_request_binds_original_input_and_external_snapshot(study,tmp_path):
    dispatch,_,_=study
    slot=next(s for s in dispatch.slots(0,'cache') if s['task']['model']=='W1')
    marker=tmp_path/'marker.json';marker.write_text('{}')
    gate=tmp_path/'gate.json';gate.write_text('{}')
    bundle=tmp_path/'bundle';source=tmp_path/'source'
    request=dispatch.request(slot,bundle=bundle,source_root=source,rscript=tmp_path/'Rscript',
        r_library=tmp_path/'R-library',sealed_marker=marker,native_acceptance=gate)
    assert request['phase']=='cache' and request['source_directory']==str(bundle/'external')
    assert request['capsule']['task']['id']==request['probe']['primary_task_id']
    assert request['probe']['id']==slot['task']['id']
    assert request['input_files'][str(bundle/'inputs'/slot['task']['input'])]==slot['capsule']['input']['sha256']
    assert request['source_files'][str(source/'fixture.py')]=='d'*64
    assert request['sealed_marker_sha256']==file_hash(marker) and request['native_acceptance_sha256']==file_hash(gate)


def test_canonical_json_row_sorting_preserves_summary_but_not_changed_schedule(study):
    dispatch,_,_=study;records=rows(dispatch,0,'cache')
    expected=dispatch.summarize_phase(0,'cache',records)
    # atomic_json sorts mapping keys. Reconstructing closed rows from such a
    # manifest must not change the summary, while each frozen position remains.
    mapping={r['task']['id']:r for r in records}
    restored=list(json.loads(json.dumps(mapping,sort_keys=True)).values())
    assert dispatch.summarize_phase(0,'cache',restored)==expected
    restored[0]['scheduled_index']=-1
    with pytest.raises(ValueError,match='frozen schedule'):
        dispatch.summarize_phase(0,'cache',restored)


def test_phase_rejects_duplicate_altered_and_wrong_eligibility(study):
    dispatch,_,_=study;record=rows(dispatch,0,'cache')[0]
    with pytest.raises(ValueError,match='Duplicate'):
        dispatch.summarize_phase(0,'cache',[record,record])
    bad=copy.deepcopy(record);bad.update(outcome='valid',samples_eligible=True)
    with pytest.raises(ValueError,match='eligibility'):
        dispatch.summarize_phase(0,'cache',[bad])
    bad=copy.deepcopy(record);bad['task']['budget']+=1
    with pytest.raises(ValueError,match='altered'):
        dispatch.summarize_phase(0,'cache',[bad])
    bad=copy.deepcopy(record);bad.pop('history_export_sha256')
    with pytest.raises(ValueError,match='export'):
        dispatch.summarize_phase(0,'cache',[bad])


def test_worker_binding_requires_native_gate_and_frozen_protocol(study):
    dispatch,_,_=study;slot=next(dispatch.slots(0,'main'));c=slot['capsule']
    request=dict(native_runtime_schema='windows-owned-runtime-v2',phase='main')
    marker=dict(schema='formal-study-freeze-v1',identity=c['identity'],source_commit=c['source_commit'],
                protocol_sha256=c['protocol_sha256'],inputs=1152,sampling_authorized_by_this_document=False,
                native_execution_gate_required=True)
    with pytest.raises(ValueError,match='acceptance'):
        validate_worker_scope(c,request,marker)
    gate={k:c[k] for k in ('source_files','required_versions','required_R_version','required_R_posterior')}
    gate.update(schema='formal-native-acceptance-v1',passed=True,platform='win32')
    # Compact binding accepted here is explicitly NOT a native gate certificate.
    assert validate_worker_scope(c,request,marker,gate)==c
    bad=dict(marker,protocol_sha256='f'*64)
    with pytest.raises(ValueError,match='identity'):validate_worker_scope(c,request,bad,gate)
    bad=dict(gate,required_R_version='different')
    with pytest.raises(ValueError,match='acceptance'):validate_worker_scope(c,request,marker,bad)


def test_old_technical_and_expanded_validation_cannot_use_new_worker(study):
    dispatch,_,_=study;c=copy.deepcopy(next(dispatch.slots(0,'main'))['capsule'])
    c.update(scope_kind='technical_batch_validation',identity=VALIDATION_ID)
    c['task'].update(model='G1',replicate=0,batch=0,budget=64)
    marker=dict(schema='formal-adapter-validation-freeze-v1',identity=VALIDATION_ID,source_commit=c['source_commit'],
                protocol_sha256=c['protocol_sha256'],main_tasks=27,cache_probes=24,formal_scientific_repetitions=0)
    request=dict(native_runtime_schema='windows-owned-runtime-v2',phase='main')
    assert validate_worker_scope(c,request,marker)==c
    c['task']['replicate']=1
    with pytest.raises(ValueError,match='bounded'):validate_worker_scope(c,request,marker)
    c['task']['replicate']=0;c['identity']='windows-batch-technical-v1';marker['identity']=c['identity']
    with pytest.raises(ValueError,match='bounded'):validate_worker_scope(c,request,marker)


def test_acceptance_passed_flag_cannot_hide_incomplete_or_skipped_runtime(study,tmp_path):
    from formal_acceptance import verify_native_acceptance,RUNTIME_CASES
    dispatch,_,_=study;p=dispatch.protocol
    gate={k:p[k] for k in ('source_files','required_versions','required_R_version','required_R_posterior')}
    gate.update(schema='formal-native-acceptance-v1',platform='win32',passed=True,
                runtime_test_sha256=file_hash(ROOT/'tests/windows/test_formal_owned_runtime.py'),runtime_xml='runtime.xml',
                environment={'scope':'artificial gate-reader fixture'})
    for incomplete in (True,False):
        suite=ET.Element('testsuite')
        for name,count in RUNTIME_CASES.items():
            for i in range(count):
                case=ET.SubElement(suite,'testcase',name=name+'['+str(i)+']')
                if not incomplete:ET.SubElement(case,'skipped',message='Synthetic skipped native check')
            if incomplete:break
        ET.ElementTree(suite).write(tmp_path/'runtime.xml')
        gate['files']={'runtime.xml':file_hash(tmp_path/'runtime.xml')}
        gate.pop('gate_sha256',None);gate['gate_sha256']=fingerprint(gate)
        (tmp_path/'gate.json').write_text(json.dumps(gate))
        with pytest.raises(ValueError,match='Full native'):
            verify_native_acceptance(tmp_path/'gate.json',p,ROOT,environment={'scope':'changed'})
        with pytest.raises(ValueError,match='Every declared native runtime'):
            verify_native_acceptance(tmp_path/'gate.json',p,ROOT,environment=gate['environment'])


@pytest.mark.skipif(sys.platform=='win32',reason='Non-Windows refusal check only')
def test_native_worker_and_controller_refuse_before_loading_or_writing(tmp_path):
    with pytest.raises(ValueError,match='actual native Windows'):
        load_worker_request(tmp_path/'absent-request.json',ROOT)
    from formal_batch import run
    with pytest.raises(ValueError,match='Actual native Windows'):
        run(tmp_path/'bundle',tmp_path/'lock',tmp_path/'Rscript',tmp_path/'R-library',tmp_path/'acceptance',0,'main')
    assert not list(tmp_path.iterdir())
