"""Portable preparation checks; these never certify Windows or sampling."""
import copy
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT/'scripts/completion'), str(ROOT/'scripts/windows')]
import formal_freeze as freezing
from formal_freeze import InputArchive, FreezeConflict, protocol_document, seal_study
from formal_runtime import file_hash, ResourceWait
from formal_study_plan import create_study_plan


def requirements(model='M1', dimension=2, steps=16):
    return {model+'-rep0000.npz': dict(model=model, replicate=0, dimension=dimension, chains=4, steps=steps,
                                     roles=['initial', 'noise', 'log_uniform', 'directions', 'nuts_seeds'])}


def binding():
    return dict(source_commit='a'*40, source_files={'fixture.py': 'b'*64},
                required_versions={'numpy': np.__version__}, required_R_version='fixture-only',
                required_R_posterior='fixture-only', external_files={'fixture-data': 'c'*64},
                windows_limits=dict(rss_bytes=8*1024**3, job_commit_bytes=12*1024**3,
                                    disk_start_bytes=4*1024**3, disk_floor_bytes=1024**3, poll_seconds=.2),
                minimum_available_ram_bytes=12*1024**3)


def test_saved_inputs_resume_without_rng_and_reject_raw_mutation(tmp_path, monkeypatch):
    req = requirements()
    archive = InputArchive(tmp_path/'inputs', 'windows-formal-storage-fixture-v1', req, binding())
    name = next(iter(req)); receipt = archive.prepare(name)
    with np.load(archive.directory/'inputs'/name, allow_pickle=False) as raw:
        assert raw['initial'][:, 0].tolist() == [-5., 5., -5., 5.]
    before = {p.relative_to(archive.directory).as_posix(): file_hash(p)
              for p in archive.directory.rglob('*') if p.is_file()}
    def prohibited(*args, **kwargs):
        raise AssertionError('Verified preparation resume must not call RNG')
    monkeypatch.setattr(freezing, 'build_payload', prohibited)
    resumed = InputArchive(archive.directory, archive.identity, req, binding(), resume=True)
    assert resumed.prepare(name) == receipt
    assert resumed.inventory()[name]['sha256'] == receipt['sha256']
    assert before == {p.relative_to(archive.directory).as_posix(): file_hash(p)
                      for p in archive.directory.rglob('*') if p.is_file()}
    with (archive.directory/'inputs'/name).open('ab') as stream:
        stream.write(b'changed')
    with pytest.raises(FreezeConflict, match='input changed'):
        resumed.prepare(name)


def test_interrupted_partial_input_is_retained_not_regenerated(tmp_path, monkeypatch):
    archive = InputArchive(tmp_path/'inputs', 'windows-formal-interruption-fixture-v1', requirements(), binding())
    calls = []
    def failed_write(stream, **arrays):
        calls.append(1); stream.write(b'partial NPZ before I/O failure')
        raise OSError('Artificial write interruption')
    monkeypatch.setattr(freezing.np, 'savez_compressed', failed_write)
    name = 'M1-rep0000.npz'
    with pytest.raises(OSError, match='Artificial'):
        archive.prepare(name)
    before = {p.name: file_hash(p) for p in archive.directory.rglob('*') if p.is_file()}
    resumed = InputArchive(archive.directory, archive.identity, requirements(), binding(), resume=True)
    with pytest.raises(FreezeConflict, match='no silent regeneration'):
        resumed.prepare(name)
    assert calls == [1] and before == {p.name: file_hash(p) for p in archive.directory.rglob('*') if p.is_file()}
    with pytest.raises(FreezeConflict, match='Incomplete'):
        resumed.inventory()


def test_resource_refusal_precedes_intent_and_rng(tmp_path, monkeypatch):
    archive = InputArchive(tmp_path/'inputs', 'windows-formal-resource-fixture-v1', requirements(), binding())
    with monkeypatch.context() as m:
        m.setattr(freezing.shutil, 'disk_usage', lambda p: SimpleNamespace(free=0))
        def prohibited(*args, **kwargs):
            raise AssertionError('Refused before RNG')
        m.setattr(freezing, 'build_payload', prohibited)
        with pytest.raises(ResourceWait): archive.prepare('M1-rep0000.npz')
    assert not list((archive.directory/'intents').iterdir())
    archive.prepare('M1-rep0000.npz')
    assert len(archive.inventory()) == 1


def test_explicit_unsealed_recovery_keeps_original_and_same_address(tmp_path, monkeypatch):
    archive = InputArchive(tmp_path/'inputs', 'windows-formal-recovery-fixture-v1', requirements(), binding())
    name = 'M1-rep0000.npz'
    with monkeypatch.context() as m:
        def failed_write(stream, **arrays):
            stream.write(b'failed preparation, retained'); raise OSError('Artificial disk write failure')
        m.setattr(freezing.np, 'savez_compressed', failed_write)
        with pytest.raises(OSError): archive.prepare(name)
    old = file_hash(archive.directory/'inputs'/(name+'.partial'))
    proof = archive.recover_unsealed_input(name, reason='Artificial storage failure repaired')
    assert proof['retained_files']['inputs/'+name+'.partial'] == old
    receipt = archive.prepare(name)
    r = requirements()[name]
    expected = freezing.build_payload(archive.identity,'M1',0,2,16,4)
    assert receipt['actual_sha256'] == freezing.validate_payload(expected,archive.identity,r)
    retained = list((archive.directory/'preparation-recovery'/name).glob('*/inputs/*.partial'))
    assert len(retained) == 1 and file_hash(retained[0]) == old
    with pytest.raises(FreezeConflict, match='verified input'):
        archive.recover_unsealed_input(name, reason='Cannot redo completed preparation')


def test_binding_paths_and_unsealed_shape_are_rejected(tmp_path):
    archive = InputArchive(tmp_path/'inputs', 'windows-formal-binding-fixture-v1', requirements(), binding())
    bad = binding(); bad['source_commit'] = 'd'*40
    with pytest.raises(FreezeConflict, match='binding differs'):
        InputArchive(archive.directory, archive.identity, requirements(), bad, resume=True)
    for name in ('../outside', '/absolute', 'C:/escape', 'receipts\\file', 'inputs//file', 'inputs/./file'):
        with pytest.raises(FreezeConflict): freezing.relative_file(archive.directory, name)
    # Invalid actual input kinds/coordinates cannot be promoted even if finite.
    r = requirements()['M1-rep0000.npz']
    values = freezing.build_payload(archive.identity, 'M1', 0, 2, 16, 4)
    values['directions'][0, 0, 0] = 0
    with pytest.raises(FreezeConflict, match='Rademacher'):
        freezing.validate_payload(values, archive.identity, r)


def test_maximum_declared_input_roundtrip_is_bounded(tmp_path):
    # One full-size artificial input file, no sampler or formal experiment.
    req = requirements('G2', 64, 16896)
    archive = InputArchive(tmp_path/'maximum', 'windows-formal-max-input-fixture-v1', req, binding())
    result = archive.prepare('G2-rep0000.npz')
    assert result['logical_array_bytes'] == 8*(4*64+4*16896*129+4)
    assert result['sampler_calls'] == result['statistical_repetitions'] == 0
    assert archive.inventory()['G2-rep0000.npz']['steps'] == 16896


def test_complete_protocol_keeps_frame_and_partial_inventory_cannot_seal(tmp_path):
    catalog = json.loads((ROOT/'benchmark/protocols/inference-budget-pilot-mac-v1.json').read_text())
    plan = create_study_plan('windows-formal-protocol-fixture-v1', catalog)
    # This metadata-only assembly is deliberately not a sealed or runnable bundle.
    inventory = {n: dict(**{k: r[k] for k in ('model','replicate','dimension','chains','steps')},
                         sha256='e'*64, actual_sha256='f'*64) for n,r in plan['input_requirements'].items()}
    p = protocol_document(plan, catalog, inventory, binding())
    assert len(p['tasks']) == 41472 and len(p['inputs']) == 1152
    assert p['sampling_authorized_by_this_document'] is False
    assert p['native_execution_gate_required'] is True
    assert p['controls'] == plan['controls'] and p['analysis_policy']['L2_unresolved_sign_error'] is None
    from batch_contract import BatchPlan
    # Public worker capsule validation over the complete assembled frame.
    validated = BatchPlan(p)
    assert len(list(validated.tasks(3))) == 10368
    incomplete = dict(inventory); incomplete.pop(next(iter(incomplete)))
    with pytest.raises(FreezeConflict, match='1152'):
        protocol_document(plan, catalog, incomplete, binding())
    archive = InputArchive(tmp_path/'partial', plan['identity'], requirements(), binding())
    archive.prepare('M1-rep0000.npz')
    with pytest.raises(FreezeConflict, match='full scientific plan'):
        seal_study(archive.directory, plan, catalog, archive, binding(), {})
    assert not (archive.directory/'FROZEN.json').exists()


@pytest.mark.skipif(sys.platform == 'win32', reason='Non-Windows refusal check only')
def test_native_prepare_refuses_other_platform_before_output(tmp_path):
    from prepare_formal_study import prepare
    with pytest.raises(FreezeConflict, match='native Windows'):
        prepare(tmp_path/'formal', 'windows-formal-inference-v1', tmp_path/'external', tmp_path/'lock',
                tmp_path/'Rscript', tmp_path/'R-library')
    assert not (tmp_path/'formal').exists() and not (tmp_path/'lock').exists()
