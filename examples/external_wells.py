"""External posteriordb wells distance model through the public Model contract.

The prior is flat in (alpha, beta). This is not the built-in normal-prior
logistic target. Backend modules are imported only when explicitly requested.
"""
import hashlib
import json
from pathlib import Path
import zipfile
import numpy as np
from scipy.special import expit, log_expit
from parallelbayes.reference import Model


def make_wells(data, backend="numpy", device="cpu"):
    n=data["N"]
    distance=np.asarray(data["dist"],dtype=float)
    switched=np.asarray(data["switched"],dtype=float)
    if isinstance(n,bool) or int(n)!=n or n<1 or distance.shape!=(n,) or switched.shape!=(n,):
        raise ValueError("Invalid wells data dimensions")
    if not np.isfinite(distance).all() or (distance<0).any() or not np.isin(switched,[0,1]).all():
        raise ValueError("Finite nonnegative distances and binary outcomes required")
    x=np.column_stack((np.ones(n),distance/100.))
    signed=2*switched-1
    def reference(q):
        return float(log_expit(signed*np.einsum("ij,j->i",x,q)).sum())
    def gradient(q):
        residual=switched-expit(np.einsum("ij,j->i",x,q))
        return np.einsum("ij,i->j",x,residual)
    spec=dict(kind="external_wells_distance",dimension=2,coordinate_id="alpha-beta-dist100-flat",
        N=int(n),dist=distance.tolist(),switched=switched.astype(int).tolist(),
        distance_divisor=100.,prior="flat in alpha and beta",parameter_order=["alpha","beta[1]"])
    model=Model(spec,2,reference,reference,gradient,lambda q:np.asarray(q),["alpha","beta[1]"])
    if backend=="numpy" and device=="cpu":
        return model
    if backend!="torch" or device not in ("cpu","cuda","cuda:0"):
        raise ValueError("Unsupported external target backend/device")
    import torch
    target_device=torch.device(device)
    if target_device.type=="cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA unavailable; CPU substitution is forbidden")
    xx=torch.tensor(x,dtype=torch.float64,device=target_device)
    yy=torch.tensor(switched,dtype=torch.float64,device=target_device)
    def logp(q):
        eta=xx@q
        return (yy*eta-torch.logaddexp(torch.zeros_like(eta),eta)).sum()
    model.log_density=logp
    model.backend="torch"
    model.device=target_device
    model.constrain_device=lambda q:q
    return model


def load_wells(source_root):
    """Load the selected upstream data only after all eight source hashes match."""
    root=Path(source_root)
    manifest=Path(__file__).resolve().parents[1]/"models/external/wells/source-manifest.json"
    source=json.loads(manifest.read_text(encoding="utf-8"))
    for row in source["files"]:
        b=(root/row["path"]).read_bytes()
        if len(b)!=row["bytes"] or hashlib.sha256(b).hexdigest()!=row["sha256"]:
            raise ValueError("External source checksum differs: "+row["path"])
    with zipfile.ZipFile(root/"posterior_database/data/data/wells_data.json.zip") as archive:
        data=json.loads(archive.read("wells_data.json"))
    make_wells(data)  # Same public target contract validates dimensions/values.
    return data


def propriety_certificate(data):
    """A sufficient certificate for this flat-prior target, not a general test.

    Two distinct distances each observed with both labels give
    L(alpha,beta) <= exp(-|alpha+x1*beta|-|alpha+x2*beta|), whose integral
    is 4/abs(x2-x1). All other Bernoulli factors are at most one.
    """
    model=make_wells(data)
    groups={}
    for i,(distance,label) in enumerate(zip(model.spec["dist"],model.spec["switched"])):
        groups.setdefault(distance,{}).setdefault(label,i)
    pairs=[(distance,indices) for distance,indices in sorted(groups.items()) if len(indices)==2]
    if len(pairs)<2:
        return dict(certified=False,integral_upper_bound=None,witnesses=[],
                    reason="This sufficient duplicate-outcome certificate is unavailable; not proof of impropriety")
    witnesses=[dict(distance_metres=distance,scaled_distance=distance/100.,
        zero_index=indices[0],one_index=indices[1]) for distance,indices in [pairs[0],pairs[-1]]]
    determinant=abs(witnesses[1]["scaled_distance"]-witnesses[0]["scaled_distance"])
    return dict(certified=True,witnesses=witnesses,determinant=determinant,
        integral_upper_bound=4./determinant,duplicate_outcome_distances=len(pairs),
        bound="L(alpha,beta) <= exp(-abs(alpha+x1*beta)-abs(alpha+x2*beta))",
        scope="Sufficient integrability certificate for the exact likelihood and flat alpha/beta prior")
