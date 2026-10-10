"""Synthetic archived-identity tests; no Windows or MCMC qualification claim."""
from pathlib import Path
import csv
import hashlib
import io
import json
import sqlite3
import sys
import tarfile
import pytest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/analysis'))
import audit_nuts_return as receiver


def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,sort_keys=True,indent=2)+'\n')


def hashes(root,exclude=()):
    return {p.relative_to(root).as_posix():receiver.sha(p) for p in root.rglob('*')
            if p.is_file() and p.relative_to(root).as_posix() not in exclude}


def remanifest(root):
    write(root/'MANIFEST.json',{p.relative_to(root).as_posix():dict(size=p.stat().st_size,sha256=receiver.sha(p))
                              for p in root.rglob('*') if p.is_file() and p.name!='MANIFEST.json'})


def fixture(tmp_path,monkeypatch):
    root=tmp_path/'received';s=root/'study';s.mkdir(parents=True)
    source={'scripts/completion/inference_nuts.py':hashlib.sha256(b'# synthetic; never executed\n').hexdigest()}
    capsule={'required_versions':{'numpy':'synthetic'},'required_R_version':'synthetic R',
             'required_R_posterior':'synthetic posterior','source_files':source}
    for model in receiver.MODELS:
        case={'source_capsule':capsule,'chain_seeds':[1,2,3,4],'initial':[[0.,0.]]*4,'target_id':'synthetic-'+model}
        write(s/'inputs'/f'{model}-case.json',case)
        write(s/'prepared-cases'/f'{model}.json',dict(case,names=['x','y']))
        write(s/'rng'/f'{model}.json',{'seeds':[1,2,3,4],'states':[{'synthetic':i} for i in range(4)]})
    for model in ('G1','G2','W1'):
        (s/'inputs'/f'{model}-diagnostic.npz').write_bytes(b'Synthetic bytes; never passed to an array loader')
    write(s/'inputs/checksums.json',hashes(s/'inputs'))
    input_sha=receiver.sha(s/'inputs/checksums.json');monkeypatch.setattr(receiver,'INPUT_SHA',input_sha)
    study=dict(identity=receiver.IDENTITY,posterior_samples_eligible=False,maximum_registered_calls=48,
               maximum_qualification_rounds=3,input_manifest_sha256=input_sha,
               required_versions=capsule['required_versions'],required_R_version=capsule['required_R_version'],
               required_R_posterior=capsule['required_R_posterior'],working_limit_bytes=6*1024**3,
               per_host_incremental_limit_bytes=receiver.MAX_BYTES)
    write(s/'STUDY.json',study)
    write(s/'prepared-cases/Q2.json',dict(initial=[[-2.,-1.],[-1.,2.],[1.,-2.],[2.,1.]],names=['x','y']))
    write(s/'rng/Q2.json',dict(states=[{'synthetic':i} for i in range(4)]))
    write(s/'prepared-checksums.json',{k:v for k,v in hashes(s).items() if k.startswith(('inputs/','rng/','prepared-cases/'))})
    identity=dict(source_files=source,system='Windows',python='3.12.14',versions=capsule['required_versions'],
                  R={'R':capsule['required_R_version'],'posterior':capsule['required_R_posterior']})
    key=receiver.fingerprint(identity);commit='a'*40
    write(s/'bindings'/f'{key}.json',dict(identity=identity,binding_sha256=key,source_commit=commit))
    target=root/'source'/key/'scripts/completion/inference_nuts.py';target.parent.mkdir(parents=True);target.write_bytes(b'# synthetic; never executed\n')
    gate=s/'native-checks'/key;write(gate/'result.json',dict(passed=True,tests=3,failed=0,skipped=0,exit_code=0,binding_sha256=key))
    (gate/'tests.xml').write_text('<testsuites><testsuite><testcase name="fake1"/><testcase name="fake2"/><testcase name="fake3"/></testsuite></testsuites>')
    write(gate/'checksums.json',hashes(gate))
    db=sqlite3.connect(s/'calls.sqlite');db.execute('CREATE TABLE identity(value TEXT)');db.execute('INSERT INTO identity VALUES (?)',(json.dumps(study),))
    db.execute('CREATE TABLE calls(id TEXT PRIMARY KEY,phase TEXT,request TEXT,request_sha TEXT,registered_ns INTEGER,outcome TEXT)')
    requests=[]
    for model in ('G1','G2','W1'):
        for kind,workers in [('legacy',1),('legacy',4),('modern',1)]:
            requests.append(dict(id=f'diagnostic-{model}-{kind}-w{workers}',phase='diagnostic',model=model,
                                 diagnostic_kind=kind,workers=workers,diagnostic_input_sha256=receiver.sha(s/'inputs'/f'{model}-diagnostic.npz')))
    requests.append(dict(id='qualification-r0-w1-d1',phase='qualification',model='Q2',round=0,workers=1,diagnostics_enabled=True,
                         case=receiver.read(s/'prepared-cases/Q2.json'),rng_sha256=receiver.sha(s/'rng/Q2.json'),
                         config=dict(draws=64,warmup=64,max_tree_depth=8,target_accept_prob=.8,full_mass=False,memory_limit_mb=2048)))
    call_rows=[]
    for index,request in enumerate(requests):
        request.update(posterior_samples_eligible=False,binding_sha256=key,source_commit=commit)
        directory=s/'calls'/request['id'];write(directory/'request.json',request)
        finished=dict(status='failed',managed_active_processes=0,kernel_terminal_verified=True,
                      posterior_samples_eligible=False,termination_proof='synthetic_not_launched')
        write(directory/'finished.json',finished);write(directory/'checksums.json',hashes(directory))
        outcome=dict(finished,checksums_sha256=receiver.sha(directory/'checksums.json'))
        db.execute('INSERT INTO calls VALUES (?,?,?,?,?,?)',(request['id'],request['phase'],json.dumps(request),receiver.fingerprint(request),index,json.dumps(outcome)))
        call_rows.append(dict(id=request['id'],phase=request['phase'],status='failed'))
    db.commit();db.close()
    a=root/'analysis';write(a/'SUMMARY.json',dict(calls=10,new_registered_four_chain_calls=1,diagnostic_jobs=9,
                                               main_registered=0,main_completed=0,registry_sha256=receiver.sha(s/'calls.sqlite'),
                                               new_sampler_calls_by_analysis=0,historical_failures_reclassified=0,
                                               posterior_samples_added=0,protocol_sha256=None))
    with (a/'calls.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['id','phase','status']);w.writeheader();w.writerows(call_rows)
    write(a/'checksums.json',hashes(a));remanifest(root)
    return root,key


def test_incomplete_failed_study_is_kept_without_native_success_claim(tmp_path,monkeypatch):
    root,key=fixture(tmp_path,monkeypatch);before=hashes(root);result=receiver.audit(root)
    assert result['identity_audit_passed'] and result['calls']==10
    assert result['phase_counts']=={'diagnostic':9,'qualification':1}
    assert not result['all_main_calls_registered'] and not result['protocol_present']
    assert not result['native_trajectory_qualification_recomputed']
    assert not result['remote_live_process_state_verified']
    assert result['new_sampler_calls']==result['posterior_samples_added']==0
    assert hashes(root)==before


def test_archive_round_trip_and_external_hash_required(tmp_path,monkeypatch):
    root,key=fixture(tmp_path,monkeypatch);archive=tmp_path/'return.tar'
    with tarfile.open(archive,'w') as tar:
        for p in sorted(root.rglob('*')):
            if p.is_file():tar.add(p,arcname=p.relative_to(root).as_posix(),recursive=False)
    with pytest.raises(ValueError,match='SHA256 differs'):
        receiver.unpack(archive,tmp_path/'wrong','0'*64)
    assert not (tmp_path/'wrong').exists()
    result=receiver.unpack(archive,tmp_path/'unpacked',receiver.sha(archive))
    assert result['verified_members']==len(receiver.read(root/'MANIFEST.json'))
    assert receiver.audit(tmp_path/'unpacked')['identity_audit_passed']


@pytest.mark.parametrize('bad_name',['../escape','study\\escape','study/../escape','C:/escape'])
def test_unsafe_archive_paths_rejected_before_extraction(tmp_path,bad_name):
    archive=tmp_path/'bad.tar'
    with tarfile.open(archive,'w') as t:
        m=tarfile.TarInfo(bad_name);m.size=1;t.addfile(m,io.BytesIO(b'x'))
    with pytest.raises(ValueError,match='Unsafe relative path'):
        receiver.unpack(archive,tmp_path/'out',receiver.sha(archive))
    assert not (tmp_path/'out').exists()


def test_corrupt_return_and_source_tamper_rejected(tmp_path,monkeypatch):
    root,key=fixture(tmp_path,monkeypatch);p=root/'source'/key/'scripts/completion/inference_nuts.py';p.write_text('changed')
    with pytest.raises(ValueError,match='Extracted member differs'):receiver.audit(root)
    remanifest(root)
    with pytest.raises(ValueError,match='Member checksum differs'):receiver.audit(root)


def test_registry_request_change_cannot_be_hidden_by_outer_checksum(tmp_path,monkeypatch):
    root,key=fixture(tmp_path,monkeypatch);db=sqlite3.connect(root/'study/calls.sqlite')
    row=db.execute('SELECT id,request FROM calls LIMIT 1').fetchone();request=json.loads(row[1]);request['workers']=4
    db.execute('UPDATE calls SET request=? WHERE id=?',(json.dumps(request),row[0]));db.commit();db.close();remanifest(root)
    with pytest.raises(ValueError,match='fingerprint'):receiver.audit(root)


def test_omitted_call_directory_is_not_a_successful_smaller_run(tmp_path,monkeypatch):
    root,key=fixture(tmp_path,monkeypatch);db=sqlite3.connect(root/'study/calls.sqlite')
    db.execute('DELETE FROM calls WHERE phase="qualification"');db.commit();db.close();remanifest(root)
    with pytest.raises(ValueError,match='directory/registry'):receiver.audit(root)


def test_relabelled_analysis_failure_rejected_even_if_resealed(tmp_path,monkeypatch):
    root,key=fixture(tmp_path,monkeypatch);a=root/'analysis';p=a/'calls.csv';p.write_text(p.read_text().replace('failed','completed',1))
    write(a/'checksums.json',hashes(a,('checksums.json',)));remanifest(root)
    with pytest.raises(ValueError,match='dropped/relabeled'):receiver.audit(root)


def test_skipped_native_gate_is_not_promoted(tmp_path,monkeypatch):
    root,key=fixture(tmp_path,monkeypatch);gate=root/'study/native-checks'/key
    p=gate/'tests.xml';p.write_text(p.read_text().replace('<testcase name="fake1"/>','<testcase name="fake1"><skipped/></testcase>'))
    write(gate/'checksums.json',hashes(gate,('checksums.json',)));remanifest(root)
    with pytest.raises(ValueError,match='Native Job gate'):receiver.audit(root)


def test_constant_event_and_duplicate_keys_are_not_silently_normalized():
    with pytest.raises(ValueError,match='Duplicate JSON key'):receiver.parse('{"calls":1,"calls":2}')
    with pytest.raises(ValueError,match='Nonfinite JSON'):receiver.parse('{"mean":NaN}')


def extend_main(root,key):
    """Complete identity fixture only; contains no real chains or Job activity."""
    s=root/'study';commit='a'*40;db=sqlite3.connect(s/'calls.sqlite')
    first_id='qualification-r0-w1-d1'
    def insert(request,status='completed'):
        directory=s/'calls'/request['id'];write(directory/'request.json',request)
        finished=dict(status=status,managed_active_processes=0,kernel_terminal_verified=True,
                      posterior_samples_eligible=False,termination_proof='synthetic_not_launched')
        write(directory/'finished.json',finished);write(directory/'checksums.json',hashes(directory,('checksums.json',)))
        outcome=dict(finished,checksums_sha256=receiver.sha(directory/'checksums.json'))
        db.execute('INSERT OR REPLACE INTO calls VALUES (?,?,?,?,?,?)',
                   (request['id'],request['phase'],json.dumps(request),receiver.fingerprint(request),
                    db.execute('SELECT count(*) FROM calls').fetchone()[0]+1,json.dumps(outcome)))
    first=json.loads(db.execute('SELECT request FROM calls WHERE id=?',(first_id,)).fetchone()[0]);insert(first)
    qualified=[first_id]
    for workers,enabled in [(1,False),(4,True),(4,False)]:
        request=dict(first,id=f'qualification-r0-w{workers}-d{int(enabled)}',workers=workers,diagnostics_enabled=enabled)
        insert(request);qualified.append(request['id'])
    schedule=[]
    for model in receiver.MODELS:
        for workers,enabled in [(1,True),(4,True),(1,False),(4,False)]:
            item=dict(id=f'main-{model}-w{workers}-d{int(enabled)}',phase='main',model=model,
                      workers=workers,diagnostics_enabled=enabled);schedule.append(item)
            request=dict(item,binding_sha256=key,source_commit=commit,posterior_samples_eligible=False,
                         case=receiver.read(s/'prepared-cases'/f'{model}.json'),rng_sha256=receiver.sha(s/'rng'/f'{model}.json'),
                         config=dict(draws=4096,warmup=1024,max_tree_depth=8,target_accept_prob=.8,full_mass=False,memory_limit_mb=2048))
            insert(request,'failed' if model=='G1' and enabled else 'completed')
    db.commit();db.close();write(s/'schedule.json',schedule)
    prepared=receiver.read(s/'prepared-checksums.json');prepared['schedule.json']=receiver.sha(s/'schedule.json');write(s/'prepared-checksums.json',prepared)
    protocol=dict(identity=receiver.IDENTITY,study_sha256=receiver.sha(s/'STUDY.json'),prepared_sha256=receiver.sha(s/'prepared-checksums.json'),
                  maximum_registered_calls=48,main_calls=36,qualification_registered=4,maximum_confirmation_calls=8,
                  posterior_samples_eligible=False,require_same_initial_actual_rng_states=True,schedule=schedule,
                  qualification_ids=qualified,binding_sha256=key,source_commit=commit,
                  confirmation_model_order=list(receiver.MODELS),confirmation_pair_order=receiver.PAIR_ORDER)
    write(s/'protocol.json',protocol);write(s/'protocol.sha256.json',dict(sha256=receiver.sha(s/'protocol.json')))
    db=sqlite3.connect(s/'calls.sqlite');records=[(i,p,json.loads(o)) for i,p,o in db.execute('SELECT id,phase,outcome FROM calls')];db.close()
    a=root/'analysis';summary=receiver.read(a/'SUMMARY.json')
    summary.update(calls=49,new_registered_four_chain_calls=40,main_registered=36,main_completed=34,
                   registry_sha256=receiver.sha(s/'calls.sqlite'),protocol_sha256=receiver.sha(s/'protocol.json'))
    write(a/'SUMMARY.json',summary)
    with (a/'calls.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['id','phase','status']);w.writeheader()
        w.writerows(dict(id=i,phase=p,status=o['status']) for i,p,o in records)
    write(a/'checksums.json',hashes(a,('checksums.json',)));remanifest(root)


def test_complete_main_identities_still_do_not_claim_native_trajectory_check(tmp_path,monkeypatch):
    root,key=fixture(tmp_path,monkeypatch);extend_main(root,key);result=receiver.audit(root)
    assert result['all_main_calls_registered'] and result['protocol_present']
    assert result['phase_counts']['main']==36 and result['calls']==49
    assert result['requires_portable_analysis_reconstruction']
    assert result['native_trajectory_qualification_recomputed'] is False


def test_changed_protocol_quota_rejected_even_if_outer_hashes_updated(tmp_path,monkeypatch):
    root,key=fixture(tmp_path,monkeypatch);extend_main(root,key);s=root/'study'
    protocol=receiver.read(s/'protocol.json');protocol['maximum_registered_calls']=49
    write(s/'protocol.json',protocol);write(s/'protocol.sha256.json',dict(sha256=receiver.sha(s/'protocol.json')));remanifest(root)
    with pytest.raises(ValueError,match='Frozen quota'):receiver.audit(root)


def test_registration_caps_checked_before_any_sampling_reconstruction(tmp_path,monkeypatch):
    root,key=fixture(tmp_path,monkeypatch);extend_main(root,key);db=sqlite3.connect(root/'study/calls.sqlite')
    for i in range(9):
        db.execute('INSERT INTO calls VALUES (?,?,?,?,?,?)',(f'confirmation-{i}','confirmation','{}','synthetic',100+i,'{}'))
    db.commit();db.close();remanifest(root)
    with pytest.raises(ValueError,match='quota exceeded'):receiver.audit(root)


@pytest.mark.parametrize('kind',['duplicate','link'])
def test_duplicate_or_link_archive_members_rejected(tmp_path,kind):
    archive=tmp_path/'bad.tar'
    with tarfile.open(archive,'w') as t:
        if kind=='duplicate':
            for _ in range(2):
                m=tarfile.TarInfo('study/a');m.size=1;t.addfile(m,io.BytesIO(b'x'))
        else:
            m=tarfile.TarInfo('study/a');m.type=tarfile.SYMTYPE;m.linkname='/outside';t.addfile(m)
    with pytest.raises(ValueError,match='Duplicate archive|Only regular'):receiver.unpack(archive,tmp_path/'out',receiver.sha(archive))
    assert not (tmp_path/'out').exists()
