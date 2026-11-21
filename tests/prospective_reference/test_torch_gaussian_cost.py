from pathlib import Path
import sys

import numpy as np
import pytest
import torch

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/prospective_torch'))
from gaussian_cost import build,inputs


def test_density_geometry_constant_across_costs():
    q=np.linspace(-2,2,8)
    values=[]
    for m in (256,2048):
        model,(x,y,diag,linear)=build(8,m,'cpu')
        actual=torch.tensor(q,dtype=torch.float64,requires_grad=True)
        value=model.log_density(actual);grad=torch.autograd.grad(value,actual)[0]
        assert x.shape==(m,8) and y.shape==(m,)
        np.testing.assert_allclose(float(value.detach()),model.reference(q),rtol=0,atol=1e-8)
        np.testing.assert_allclose(grad.detach().numpy(),model.gradient_reference(q),rtol=0,atol=1e-8)
        values.append(float(value.detach()))
    np.testing.assert_allclose(values[0],values[1],rtol=0,atol=1e-8)


def test_study_grid_bounds_allocation():
    for dim,rows in ((8,2),(129,65536),(8,65537),(True,256)):
        with pytest.raises(ValueError):inputs(dim,rows)
