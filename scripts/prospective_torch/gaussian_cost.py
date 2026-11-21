"""Dense Gaussian cost fixture; analytic sufficient statistics are an independent oracle."""
from pathlib import Path
import sys

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "r-package/inst/python"))
from parallelbayes.reference import Model


def inputs(dimension, rows):
    if type(dimension) is not int or type(rows) is not int or dimension not in (8,32,128) or rows not in (256,2048,16384,65536):
        raise ValueError("dimension and row count must be in the bounded study design")
    diagonal = np.linspace(2., 10., dimension)
    linear = np.linspace(-1., 1., dimension)
    phase = np.pi * (np.arange(rows)+.5)/rows
    basis = np.cos(phase[:,None]*np.arange(1,dimension+1)[None,:])*np.sqrt(2/rows)
    design = basis*np.sqrt(diagonal)
    response = np.einsum("ij,j->i", basis, linear/np.sqrt(diagonal))
    response += np.cos(phase*(dimension+1))*np.sqrt(2/rows)
    return design, response, diagonal, linear


class DenseGaussian:
    def __init__(self, design, response, device):
        x = np.asarray(design, dtype=np.float64)
        y = np.asarray(response, dtype=np.float64)
        if x.ndim != 2 or y.shape != (x.shape[0],) or not np.isfinite(x).all() or not np.isfinite(y).all():
            raise ValueError("invalid finite dense design/response")
        requested = torch.device(device)
        self.x = torch.as_tensor(x, dtype=torch.float64, device=requested)
        self.y = torch.as_tensor(y, dtype=torch.float64, device=requested)
        self.device = self.x.device
        self.y2 = torch.dot(self.y,self.y)
        self.dimension = x.shape[1]

    def log_density(self, q):
        if q.shape[-1:] != (self.dimension,) or q.dtype != torch.float64 or q.device != self.device:
            raise ValueError("coordinates do not match target dimension, device and dtype")
        residual = torch.matmul(q, self.x.T)-self.y
        return -(residual.square().sum(dim=-1)-self.y2+q.square().sum(dim=-1))/2


def build(dimension, rows, device):
    x,y,diagonal,linear = inputs(dimension, rows)
    target = DenseGaussian(x,y,device)
    def reference(q):
        return np.dot(q,linear)-np.dot(q*q,diagonal+1)/2
    def gradient(q):
        return linear-(diagonal+1)*q
    spec = {"kind":"prospective_dense_gaussian", "coordinate_id":"native-gaussian-v1",
            "dimension":dimension, "rows":rows, "design":"dct-orthogonal-v1",
            "prior":"standard_normal", "status":"development_not_formal"}
    model = Model(spec,dimension,target.log_density,reference,gradient,lambda q:np.asarray(q),
                  [f"q{i}" for i in range(dimension)],backend="torch")
    model.device = torch.device(device)
    model.constrain_device = lambda q:q
    return model, (x,y,diagonal,linear)
