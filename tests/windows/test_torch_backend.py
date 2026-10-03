"""Same assertions run first on CPU, then explicitly on CUDA; no GPU skip."""
import json
import os
import subprocess
import sys
from pathlib import Path
import numpy as np
import pytest
import torch
from parallelbayes import sample,make_model,validate_model
from parallelbayes.reference import benchmark_model,make_reference,numpy_reference
from parallelbayes.torch_backend.sampling import settings,random_tape,tape_hash
from parallelbayes.torch_backend.kernels import transition
from parallelbayes.torch_backend.executors import affine_scan

DEVICE=os.environ.get("PB_TORCH_DEVICE","cpu")
PAIRS=[("mala","sequential"),("mala","quasi_deer"),("rwm","sequential"),("rwm","online_picard")]


def run(spec,c=None,tape=None):
    return sample(spec,dict(device=DEVICE,**(c or {})),tape,backend="torch")


def test_independent_imports():
    code="import sys; import parallelbayes; import parallelbayes.reference; assert 'jax' not in sys.modules and 'torch' not in sys.modules"
    subprocess.run([sys.executable,"-c",code],check=True)


@pytest.mark.parametrize("name",["G1","G2","L1","L2","T1","H1","H2","A1","M1"])
def test_density_gradient_hvp_constrain(name):
    reference=benchmark_model(name)
    model=make_model(reference.spec,backend="torch",device=DEVICE)
    result=validate_model(model)
    assert result["passed"],result
    assert model.target_id==reference.target_id
    assert model.names==reference.names


@pytest.mark.parametrize("name",["G1","G2","L1","T1","H1","H2","A1","M1"])
@pytest.mark.parametrize("kernel,executor",PAIRS)
def test_actual_tape_reference(name,kernel,executor):
    c=settings(dict(device=DEVICE,draws=19,chains=2,window=8,kernel=kernel,executor=executor,step_size=.005))
    spec=benchmark_model(name).spec
    tape=random_tape(c,spec["dimension"])
    r=run(spec,c={k:v for k,v in c.items() if k!="device"},tape=tape)
    assert r["status"]=="completed",r
    assert r["audit"]["acceptance_mismatches"]==[0,0]
    assert max(r["audit"]["max_abs_path_error"])<1e-7
    assert r["diagnostics"]["tensor_device"].startswith(DEVICE)
    assert r["diagnostics"]["confirmed"]==38
    if DEVICE=="cuda":
        cpu=sample(spec,dict(c,device="cpu"),tape,backend="torch")
        assert cpu["status"]=="completed"
        np.testing.assert_array_equal(cpu["accept"],r["accept"])
        np.testing.assert_allclose(cpu["unconstrained"],r["unconstrained"],atol=1e-8,rtol=1e-8)
        np.testing.assert_allclose(cpu["draws"],r["draws"],atol=1e-8,rtol=1e-8)


def test_scan_order_non_power_of_two():
    rng=np.random.default_rng(92)
    a=rng.uniform(-.8,.8,(2,13,3));b=rng.normal(size=a.shape);base=rng.normal(size=(2,3))
    expected=[];q=base.copy()
    for i in range(13):
        q=a[:,i]*q+b[:,i];expected.append(q.copy())
    actual=affine_scan(*(torch.tensor(x,device=DEVICE,dtype=torch.float64) for x in (a,b,base)))
    np.testing.assert_allclose(actual.cpu(),np.stack(expected,axis=1),atol=1e-12)


@pytest.mark.parametrize("kernel,executor",PAIRS)
def test_acceptance_boundary_and_self_loop(kernel,executor):
    c=dict(kernel=kernel,executor=executor,draws=3,window=2,step_size=.5 if kernel=="mala" else 1.)
    # Binary-exact arithmetic: MALA h=.5 => y=1 and ratio=-.125; RWM s=1 => -.5.
    threshold=-.125 if kernel=="mala" else -.5
    z=np.ones((1,3,1));u=np.array([[threshold,np.nextafter(threshold,-np.inf),0.]])
    tape=dict(noise=z,log_uniform=u,directions=z.copy())
    r=run(dict(kind="gaussian",dimension=1),c,tape)
    assert r["status"]=="completed",r
    assert not r["accept"][0,0] and r["accept"][0,1]
    q=np.concatenate((np.zeros((1,1)),r["unconstrained"][0]))
    np.testing.assert_allclose(q[1:][~r["accept"][0]],q[:-1][~r["accept"][0]],atol=1e-9)


@pytest.mark.parametrize("accepted",[True,False])
def test_hard_forward_surrogate_jvp(accepted):
    h=.2;q=torch.tensor([.7],device=DEVICE,dtype=torch.float64);z=torch.tensor([1.1],device=DEVICE,dtype=torch.float64)
    u=torch.tensor(-10. if accepted else 0.,device=DEVICE,dtype=torch.float64)
    step=transition(lambda x:-.5*x.square().sum(),"mala")
    hard,acc,_=step(q,z,u,h)
    forward,jv=torch.func.jvp(lambda x:step(x,z,u,h,True)[0],(q,),(torch.ones_like(q),))
    np.testing.assert_array_equal(forward.cpu(),hard.cpu())
    assert bool(acc)==accepted
    # Gaussian MALA ratio h/4*(q^2-y^2), derivative h/2*(q-y*(1-h)).
    y=(1-h)*q+np.sqrt(2*h)*z
    ratio=h/4*(q.square()-y.square()).sum()
    smooth=torch.sigmoid(ratio-u)
    expected=1-h*float(accepted)+smooth*(1-smooth)*(h/2*(q-y*(1-h)))*(y-q)
    np.testing.assert_allclose(jv.cpu(),expected.cpu(),atol=1e-12)


@pytest.mark.parametrize("executor,kernel",[("quasi_deer","mala"),("online_picard","rwm")])
def test_failure_replay_and_fallback(executor,kernel):
    spec=dict(kind="gaussian",dimension=3)
    c=dict(executor=executor,kernel=kernel,draws=31,window=8,max_iter=1,step_size=.7)
    bad=run(spec,c);again=run(spec,c)
    assert bad["status"]=="failed" and bad["draws"] is None
    np.testing.assert_array_equal(bad["failed_trajectory"],again["failed_trajectory"])
    fallback=run(spec,dict(c,on_failure="sequential"))
    seq=run(spec,dict(c,executor="sequential"))
    assert fallback["status"]=="completed" and fallback["fallback"]
    assert fallback["timing"]["fallback"]>0 and fallback["timing"]["sample"]>0
    np.testing.assert_array_equal(fallback["draws"],seq["draws"])
    assert fallback["primary_failed_trajectory"] is not None
    assert fallback["tape_sha256"]==seq["tape_sha256"]


@pytest.mark.parametrize("mu",[-1000.,1000.])
def test_nonrepresentable_transform(mu):
    tape=dict(noise=np.zeros((1,1,1)),directions=np.ones((1,1,1)),log_uniform=np.full((1,1),-1.))
    r=run(dict(kind="lognormal",mu=mu),dict(draws=1,initial=[mu]),tape)
    assert r["status"]=="failed" and r["draws"] is None and r["failed_trajectory"] is not None


def test_nonfinite_and_oracle_exception(monkeypatch):
    model=make_model(dict(kind="gaussian",dimension=2),backend="torch",device=DEVICE)
    model.log_density=lambda q:q.sum()*float("nan")
    r=run(model,dict(draws=8))
    assert r["status"]=="failed" and r["diagnostics"]["status"]==2
    import parallelbayes.torch_backend.sampling as module
    def broken(*a,**kw):raise FloatingPointError("injected oracle failure")
    monkeypatch.setattr(module,"numpy_reference",broken)
    r=run(dict(kind="gaussian",dimension=2),dict(draws=8))
    assert r["status"]=="failed" and "injected" in r["audit"]["error"]


def test_error_injection_and_memory():
    model=make_model(dict(kind="lognormal"),backend="torch",device=DEVICE)
    model.log_density=lambda q:-.5*q.square().sum()-q.sum()
    assert not validate_model(model)["passed"]
    r=run(model,dict(draws=20,step_size=.4))
    assert r["status"]=="failed" and not r["audit"]["passed"]
    with pytest.raises(MemoryError):run(dict(kind="gaussian",dimension=8),dict(draws=100000,memory_limit_mb=1))


def test_diagonal_clipping_and_real_final_window():
    r=run(dict(kind="gaussian",dimension=2),dict(draws=13,window=8,executor="quasi_deer",jacobian_clip=.001))
    assert r["status"]=="completed" and r["diagnostics"]["clips"]>0
    assert r["diagnostics"]["confirmed"]==13
    p=np.array([[1.,.5],[.5,1.]])
    tape=dict(noise=np.zeros((1,5,2)),log_uniform=np.full((1,5),-1.),directions=np.ones((1,5,2)))
    tape['noise'][0,-1,0]=1.
    r=run(dict(kind='gaussian',dimension=2,covariance=np.linalg.inv(p).tolist()),
        dict(draws=5,window=4,max_iter=1,step_size=.1,executor='quasi_deer'),tape)
    assert r['status']=='completed'
    np.testing.assert_allclose(r['draws'][0,-1],[np.sqrt(.2),0.])


def test_invalid_tape_and_model():
    c=settings(dict(draws=3));tape=random_tape(c,1);tape['directions'][0,0,0]=0
    with pytest.raises(ValueError):run(dict(kind='gaussian',dimension=1),dict(draws=3),tape)
    with pytest.raises(ValueError):make_reference(dict(kind='gaussian',dimension=1.5))


@pytest.mark.parametrize("config",[dict(kernel="nuts"),dict(kernel="mala",executor="online_picard"),
    dict(step_size=0),dict(draws=1.2),dict(device="gpu"),dict(unknown=1)])
def test_unsupported_inputs(config):
    with pytest.raises(ValueError):
        sample(dict(kind="gaussian",dimension=1),config,backend="torch")
