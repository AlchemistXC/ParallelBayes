"""Public experiment contracts: planned comparisons, actual arrays and resume."""
import importlib.util
from pathlib import Path
import numpy as np
import pytest

ROOT=Path(__file__).resolve().parents[2]


def module():
    s=importlib.util.spec_from_file_location('mechanism_runner',ROOT/'scripts/completion/mechanism_runner.py')
    m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m


def test_design_includes_fixed_output_chain_allocation_and_step_contrast():
    plan=module().design('windows')
    assert plan['required_platform']=='win32'
    assert plan['devices']==['cpu','cuda']
    assert plan['independent_tapes_per_model']==2
    assert sum(1+len(g['windows']) for g in plan['groups'])*2==192
    for name,scale in [('G2',.25),('L1',.1)]:
        rows=[g for g in plan['groups'] if g['model']==name and g['kernel']=='rwm'
              and g['replicate']==0 and g['step_size']==scale]
        assert any(g['chains']==1 and g['draws']==512 and 16 in g['windows'] for g in rows)
        assert any(g['chains']==4 and g['draws']==128 and 4 in g['windows'] for g in rows)
        assert any(g['chains']==16 and g['draws']==32 and g['windows']==[] for g in rows)
    assert not plan['inference_claim']


def test_actual_workflows_are_audited_and_resume_never_replaces_terminal_evidence(tmp_path):
    m=module()
    spec=dict(kind='gaussian',dimension=1,mean=[0.],covariance=[[1.]],coordinate_id='identity')
    group=dict(id='tiny',model='known_normal',kernel='mala',replicate=0,chains=1,draws=4,
               windows=[2],step_size=.1,role='runner_validation')
    tape=dict(noise=np.array([[[.25],[-.5],[1.],[.1]]]),log_uniform=np.full((1,4),-1.),directions=np.ones((1,4,1)))
    folder=tmp_path/'group'
    state=m.run_group(spec,group,tape,folder,'cpu',technical_replays=1)
    assert state['status']=='completed' and state['audited_workflows']==2
    assert state['paired_acceptance_mismatches']==0 and state['replays_identical']
    original=(folder/'state.json').read_bytes()
    assert m.run_group(spec,group,tape,folder,'cpu',technical_replays=1,resume=True)==state
    assert (folder/'state.json').read_bytes()==original
    name=next(n for n in state['assets'] if n.endswith('.npz'))
    p=folder/name;p.write_bytes(p.read_bytes()+b'corruption')
    with pytest.raises(ValueError,match='checksum'):
        m.run_group(spec,group,tape,folder,'cpu',technical_replays=1,resume=True)


def test_cost_probe_preserves_known_gaussian_transitions_and_reports_separate_costs(tmp_path):
    module() # Configure the project Python import path.
    import torch
    from parallelbayes.torch_backend.models import make_model
    s=importlib.util.spec_from_file_location('mechanism_probes',ROOT/'scripts/completion/mechanism_probes.py')
    m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
    model=make_model(dict(kind='gaussian',dimension=1,mean=[0.],covariance=[[1.]]),'cpu')
    tensor=lambda x:torch.tensor(x,dtype=torch.float64)
    report=m.probe_fixed_batch(model,tensor([[[0.],[.5]]]),tensor([[[.1],[-.2]]]),
         tensor([[-1.,-1.]]),tensor([[[1.],[1.]]]),.5,'rwm',tmp_path/'probe',repeats=1,block=1)
    assert report['status']=='passed'
    assert report['numerical_checks']['accepted']==2
    assert report['numerical_checks']['acceptance_mismatches']==0
    assert report['numerical_checks']['transition_max_abs_error']<1e-14
    assert {'density_batch','transition_batch','surrogate_jvp_batch','affine_scan','prefix_scalar_read'} <= set(report['measurements'])
    assert report['components_are_additive'] is False


def test_active_operating_system_lease_rejects_a_second_runner(tmp_path):
    m=module()
    with m.experiment_lease(tmp_path):
        with pytest.raises(RuntimeError,match='active runner'):
            with m.experiment_lease(tmp_path):
                raise AssertionError('Concurrent ownership was admitted')
    # A released OS lease may be taken again; a stale metadata file is not proof of running work.
    with m.experiment_lease(tmp_path):
        pass
