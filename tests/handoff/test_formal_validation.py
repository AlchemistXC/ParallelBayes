"""Portable freeze/dispatch/export checks. No native Job or sampler executes."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'scripts/completion'),str(ROOT/'scripts/windows')]
from formal_validation import (validation_design,validation_protocol,seal_validation,verify_validation_bundle,
                               validation_slots,validation_request,file_inventory,TEST_FILES)
from formal_freeze import InputArchive,FreezeConflict
from formal_execution import VALIDATION_ID,validate_worker_scope
from formal_study_plan import study_controls
from formal_runtime import atomic_json,file_hash,fingerprint
import validate_formal_adapter as native


@pytest.fixture(scope='module')
def prepared(tmp_path_factory):
    root=tmp_path_factory.mktemp('finite-freeze')/'bundle'
    catalog=json.loads((ROOT/'benchmark/protocols/inference-budget-pilot-mac-v1.json').read_text())
    design=validation_design(catalog); fixture=b'artificial metadata fixture, no native execution\n'
    digest=hashlib.sha256(fixture).hexdigest(); lock='artificial-python-lock\n'
    binding=dict(source_commit='c'*40,source_branch='artificial-fixture',source_files={'fixture.py':digest},
        validation_test_sources={name:digest for name in TEST_FILES},external_files={'LICENSE':digest},
        environment=dict(fixture_only=True,pip_freeze_sha256=hashlib.sha256(lock.encode()).hexdigest(),
                         rscript=r'D:\fixture\Rscript.exe',r_library=r'D:\fixture\R-library'),
        required_versions={'numpy':'fixture'},required_R_version='fixture',required_R_posterior='fixture',
        windows_limits=dict(rss_bytes=8*1024**3,job_commit_bytes=12*1024**3,disk_start_bytes=4*1024**3,
                            disk_floor_bytes=1024**3,poll_seconds=.2),minimum_available_ram_bytes=12*1024**3,
        shared_host_lock=r'D:\fixture\host.lock')
    archive=InputArchive(root,VALIDATION_ID,design['input_requirements'],binding)
    for name,value in {'catalog.json':catalog,'validation-design.json':design,'environment.json':binding['environment'],
                       'address-check.json':{'fixture_only':True}}.items():atomic_json(root/name,value)
    (root/'pip-freeze.txt').write_text(lock);(root/'pip-check.txt').write_text('Artificial fixture\n')
    for name in ['source/fixture.py','external/LICENSE',*['source/'+s for s in TEST_FILES]]:
        path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(fixture)
    for name in design['input_requirements']:archive.prepare(name,disk_floor_bytes=1024**2)
    marker=seal_validation(root,archive,catalog,binding)
    return root,marker,catalog,design,binding


def test_exact_three_input_27_24_plan_and_full_parameter_contract(prepared):
    root,marker,catalog,design,binding=prepared
    actual,p,rebuilt,bound=verify_validation_bundle(root)
    assert (actual,rebuilt,bound)==(marker,design,binding)
    assert p['controls']==study_controls()
    assert len(p['tasks'])==27 and len(design['cache_allocation']['probes'])==24
    assert len(p['inputs'])==3 and p['inputs']['G2-rep0000.npz']['steps']==16896
    assert {p['inputs'][n]['steps'] for n in ('G1-rep0000.npz','W1-rep0000.npz')}=={576}
    assert marker['formal_sampling_authorized'] is False and p['formal_scientific_repetitions']==0
    with pytest.raises(FreezeConflict,match='Finite validation design'):
        bad=copy.deepcopy(design);bad['controls']['window']=16
        validation_protocol(bad,catalog,p['inputs'],binding)


def test_input_resume_does_not_invoke_rng_or_change_evidence(prepared,monkeypatch):
    root,_,_,design,binding=prepared;before=file_inventory(root)
    import formal_freeze
    def forbidden(*a,**kw):raise AssertionError('Input RNG repeated')
    monkeypatch.setattr(formal_freeze,'build_payload',forbidden)
    archive=InputArchive(root,VALIDATION_ID,design['input_requirements'],binding,resume=True)
    for name in design['input_requirements']:archive.prepare(name)
    assert file_inventory(root)==before
    with pytest.raises(FreezeConflict,match='immutable'):
        seal_validation(root,archive,json.loads((root/'catalog.json').read_text()),binding)


def test_every_worker_request_has_frozen_inputs_and_external_target(prepared):
    root,marker,_,_,_=prepared;_,p,_,_=verify_validation_bundle(root)
    for phase,count in [('main',27),('cache',24)]:
        slots=list(validation_slots(p,phase));assert len(slots)==count
        for slot in slots:
            request=validation_request(slot,p,root,ROOT)
            assert validate_worker_scope(slot['capsule'],request,marker)==slot['capsule']
            assert request['source_directory']==str(root/'external')
            assert request['sealed_marker_sha256']==file_hash(root/'FROZEN.json')
            assert request['input_files'][str(root/'inputs'/slot['capsule']['task']['input'])]==slot['capsule']['input']['sha256']
            if phase=='cache':
                assert slot['task']['id']!=slot['capsule']['task']['id']
                assert request['probe']['primary_task_id']==slot['capsule']['task']['id']
    with pytest.raises(FreezeConflict):list(validation_slots(p,'unfrozen'))


def test_relocation_and_tampered_actual_input_are_distinct(prepared,tmp_path):
    original=prepared[0];copyto=tmp_path/'relocated';shutil.copytree(original,copyto)
    assert verify_validation_bundle(copyto)[1]==verify_validation_bundle(original)[1]
    raw=copyto/'inputs/G1-rep0000.npz';data=raw.read_bytes();raw.write_bytes(data[:-1]+bytes([data[-1]^1]))
    with pytest.raises(FreezeConflict,match='changed'):verify_validation_bundle(copyto)
    verify_validation_bundle(original)


def test_manifest_cannot_omit_required_test_source_even_when_resigned(prepared,tmp_path):
    bundle=tmp_path/'changed';shutil.copytree(prepared[0],bundle)
    inventory=json.loads((bundle/'freeze-manifest.json').read_text());inventory.pop('source/'+TEST_FILES[1])
    atomic_json(bundle/'freeze-manifest.json',inventory)
    marker=json.loads((bundle/'FROZEN.json').read_text());marker['manifest_sha256']=file_hash(bundle/'freeze-manifest.json')
    atomic_json(bundle/'FROZEN.json',marker)
    with pytest.raises(FreezeConflict,match='omits'):verify_validation_bundle(bundle)


@pytest.mark.skipif(sys.platform=='win32',reason='Non-native early refusal only')
def test_native_entry_points_refuse_before_creating_outputs(tmp_path):
    bundle=tmp_path/'absent'
    for action in (
        lambda:native.prepare(bundle,tmp_path,tmp_path/'lock',tmp_path/'Rscript',tmp_path/'Rlib'),
        lambda:native.runtime_tests(bundle),lambda:native.run_phase(bundle,'main'),lambda:native.seal(bundle)):
        with pytest.raises(FreezeConflict,match='Actual native Windows'):action()
    assert not list(tmp_path.iterdir())


def test_command_help_is_portable_and_exposes_explicit_steps():
    run=subprocess.run([sys.executable,str(ROOT/'scripts/windows/validate_formal_adapter.py'),'--help'],
                       capture_output=True,text=True)
    assert run.returncode==0
    assert '{prepare,test,run,seal,verify,export}' in run.stdout


def test_export_roundtrip_uses_original_common_integrity_verifier(prepared,tmp_path,monkeypatch):
    # This checks only archive mechanics. The deliberately injected result is
    # not a native gate; a real export first performs full acceptance verify.
    root=prepared[0];before=file_inventory(root)
    monkeypatch.setattr(native,'verify',lambda path:{'passed':True,'artificial_export_check_only':True})
    archive=tmp_path/'fixture.tar';receipt=native.export(root,archive)
    spec=importlib.util.spec_from_file_location('existing_return_verifier',ROOT/'scripts/verify-windows-return.py')
    reader=importlib.util.module_from_spec(spec);spec.loader.exec_module(reader)
    checked=reader.verify(archive)
    assert checked['archive_sha256']==receipt['archive_sha256'] and checked['checked_files']==len(before)
    assert file_inventory(root)==before
    with pytest.raises(FreezeConflict,match='fresh archive'):native.export(root,archive)
    with pytest.raises(FreezeConflict):native.export(root,root/'nested.tar')
