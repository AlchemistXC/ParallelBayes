"""Development Gaussian fixtures with fixed sufficient statistics across row counts."""
import json
from pathlib import Path
import sys

import numpy as np


def conditions(dimension, rows):
    diagonal = np.linspace(2., 10., dimension)
    linear = np.linspace(-1., 1., dimension)
    phase = np.pi * (np.arange(rows)+.5) / rows
    basis = np.cos(phase[:, None]*np.arange(1, dimension+1)[None, :]) * np.sqrt(2/rows)
    design = basis * np.sqrt(diagonal)
    response = np.einsum("ij,j->i", basis, linear / np.sqrt(diagonal))
    response += np.cos(phase*(dimension+1))*np.sqrt(2/rows)
    return design, response, diagonal, linear


def verify():
    reports = []
    for d in (8, 128):
        for rows in (256, 2048, 16384, 65536):
            matrix, y, diagonal, linear = conditions(d, rows)
            error_xx = np.max(np.abs(np.einsum("ij,ik->jk", matrix, matrix) - np.diag(diagonal)))
            error_xy = np.max(np.abs(np.einsum("ij,i->j", matrix, y) - linear))
            error_yy = abs(np.sum(y**2) - (np.sum(linear**2/diagonal) + 1))
            errors = []
            for point in (np.zeros(d), np.linspace(-2, 2, d), np.linspace(2,-2,d)):
                residual = np.einsum("ij,j->i", matrix, point) - y
                dense = -(np.sum(residual**2) - np.sum(y**2) + np.sum(point**2))/2
                dense_gradient = -(np.einsum("ij,i->j", matrix, residual) + point)
                analytic = point @ linear - .5*np.dot(point**2, diagonal+1)
                analytic_gradient = linear - (diagonal+1)*point
                errors.append([abs(dense-analytic), np.max(np.abs(dense_gradient-analytic_gradient))])
            density_error, gradient_error = np.max(errors, axis=0)
            values = [error_xx, error_xy, error_yy, density_error, gradient_error]
            assert np.all(np.isfinite(values)) and max(values) <= 1e-8, (d, rows, values)
            reports.append(dict(dimension=d, rows=rows, gram=error_xx, cross=error_xy, response=error_yy,
                                density=density_error, gradient=gradient_error))
    return reports


if __name__ == "__main__":
    with Path(sys.argv[1]).open("x") as file:
        json.dump(verify(), file, indent=2)
