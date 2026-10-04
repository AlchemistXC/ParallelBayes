"""Independent two-dimensional quadrature and explicit log-concave tail control."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import platform
import subprocess
import sys
import time
import numpy as np
import scipy
from scipy.optimize import root as solve_root
from scipy.special import expit, log_expit

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'r-package/inst/python'))
sys.path.insert(0, str(ROOT/'examples'))
from external_wells import load_wells, make_wells

SPEC = ROOT/'benchmark/protocols/wells-quadrature-v1.json'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False)+'\n')


def rule(a, b, nodes, weights):
    return .5*(a+b)+.5*(b-a)*nodes, .5*(b-a)*weights


def integrate_box(log_density_batch, center, scale, radius, order, chunk=128):
    """Return finite-square integrals; event boundary is integrated, not binned."""
    if order < 2 or order*order > 100000 or not 1 <= chunk <= 128 or radius <= 0:
        raise ValueError('Quadrature workspace guard')
    if not np.isfinite(scale).all() or not np.allclose(scale, np.tril(scale), rtol=0, atol=0) or scale[1, 1] <= 0:
        raise ValueError('Expected a finite lower-triangular Cholesky factor')
    nodes, weights = np.polynomial.legendre.leggauss(order)
    lp_center = float(log_density_batch(np.asarray(center)[None, :])[0])
    z, w = rule(-radius, radius, nodes, weights)
    zz = np.stack(np.meshgrid(z, z, indexing='ij'), axis=-1).reshape(-1, 2)
    ww = np.outer(w, w).ravel()

    def accumulate(points, quadrature_weights, moments):
        total = np.zeros(7 if moments else 1)
        for start in range(0, len(points), chunk):
            q = center + points[start:start+chunk] @ scale.T
            density = np.exp(log_density_batch(q)-lp_center)
            if not np.isfinite(density).all():
                raise ValueError('Nonfinite density during quadrature')
            weighted = density*quadrature_weights[start:start+chunk]
            if moments:
                a, b = q.T
                f = np.stack([np.ones(len(q)), a, b, a*a, b*b, expit(a), expit(a+b)], axis=1)
                total += np.sum(weighted[:, None]*f, axis=0)
            else:
                total[0] += np.sum(weighted)
        return total

    integrals = accumulate(zz, ww, True)
    # beta = center[1] + scale[1,0]*z1 + scale[1,1]*z2.
    cuts = [-radius, radius]
    if scale[1, 0] != 0:
        for bound in [-radius, radius]:
            cut = (-center[1]-scale[1, 1]*bound)/scale[1, 0]
            if -radius < cut < radius:
                cuts.append(float(cut))
    cuts = sorted(cuts)
    event = 0.
    for left, right in zip(cuts[:-1], cuts[1:]):
        x, wx = rule(left, right, nodes, weights)
        lower = np.maximum(-radius, (-center[1]-scale[1, 0]*x)/scale[1, 1])
        valid = lower < radius
        x, wx, lower = x[valid], wx[valid], lower[valid]
        if not len(x):
            continue
        y = .5*(lower[:, None]+radius)+.5*(radius-lower[:, None])*nodes
        wy = .5*(radius-lower[:, None])*weights
        points = np.stack([np.broadcast_to(x[:, None], y.shape), y], axis=-1).reshape(-1, 2)
        event += accumulate(points, (wx[:, None]*wy).ravel(), False)[0]
    if integrals[0] <= 0 or not np.isfinite(integrals).all() or not 0 <= event <= integrals[0]*(1+1e-8):
        raise ValueError('Invalid finite-square integral')
    means = list(integrals[1:]/integrals[0])+[float(event/integrals[0])]
    return dict(radius=radius, order=order, normalizer_z_scaled=float(integrals[0]),
                integrals_z_scaled=integrals.tolist(), event_integral_z_scaled=float(event), means=means)


def tail_bounds(logp, gradient, center, scale, radius, sectors):
    """Supporting-plane bounds outside disk R, enclosing the omitted square tail.

    This evaluates valid analytic inequalities in ordinary floating point;
    numerical roundoff and the interior quadrature are not interval-certified.
    """
    angle_width = 2*math.pi/sectors
    half = angle_width/2
    lp0 = logp(center)
    norms = np.linalg.norm(scale, axis=1)
    bounds = np.zeros(5)  # mass, |alpha|, |beta|, alpha^2, beta^2
    kappas = []
    for k in range(sectors):
        angle = (k+.5)*angle_width
        u = np.array([math.cos(angle), math.sin(angle)])
        v = np.array([-u[1], u[0]])
        point = center+scale@(radius*u)
        g = scale.T@gradient(point)
        a, b = float(g@u), float(g@v)
        maxima = [a*math.cos(half)+b*math.sin(half), a*math.cos(half)-b*math.sin(half)]
        stationary = math.atan2(b, a)
        if -half <= stationary <= half:
            maxima.append(float(np.linalg.norm(g)))
        kappa = -max(maxima)
        if not math.isfinite(kappa) or kappa <= 0:
            raise ValueError('No finite supporting-plane bound for a tail sector')
        kappas.append(kappa)
        c = logp(point)-lp0-float(g@(radius*u))
        e = angle_width*math.exp(c-kappa*radius)
        # Incomplete exponential moments with exp(-kappa*R) factored out.
        i1 = radius/kappa+1/kappa**2
        i2 = radius**2/kappa+2*radius/kappa**2+2/kappa**3
        i3 = radius**3/kappa+3*radius**2/kappa**2+6*radius/kappa**3+6/kappa**4
        bounds[0] += e*i1
        for j in range(2):
            a0, b0 = abs(center[j]), norms[j]
            bounds[1+j] += e*(a0*i1+b0*i2)
            bounds[3+j] += e*(a0*a0*i1+2*a0*b0*i2+b0*b0*i3)
    return dict(radius=radius, sectors=sectors, minimum_decay=min(kappas),
                mass_z_scaled=float(bounds[0]), absolute_moment_z_scaled=bounds[1:].tolist(),
                interpretation='Floating-point evaluation of analytic tail bounds; not a certified total numerical error')


def freeze(output):
    if output.exists():
        raise FileExistsError('Preserve prior lock')
    spec = json.loads(SPEC.read_text())
    commit = subprocess.check_output(['git','rev-parse','HEAD'], cwd=ROOT, text=True).strip()
    files = {}
    for name in spec['source_files']:
        if (ROOT/name).read_bytes() != subprocess.check_output(['git','show',commit+':'+name], cwd=ROOT):
            raise ValueError('Commit analysis source before freezing: '+name)
        files[name] = sha(ROOT/name)
    output.parent.mkdir(parents=True, exist_ok=True)
    write(output, dict(identity=spec['identity'], source_commit=commit, sources=files))
    print(json.dumps(dict(lock=str(output), sha256=sha(output), source_commit=commit)))


def run(source, lock, output):
    if output.exists():
        raise FileExistsError('Fresh output required')
    if source == output or source in output.parents:
        raise ValueError('Preserve upstream cache')
    frozen = json.loads(lock.read_text()); spec = json.loads(SPEC.read_text())
    if frozen['identity'] != spec['identity'] or set(frozen['sources']) != set(spec['source_files']):
        raise ValueError('Unexpected analysis lock')
    for name, digest in frozen['sources'].items():
        if sha(ROOT/name) != digest:
            raise ValueError('Frozen source changed: '+name)
    data = load_wells(source); model = make_wells(data)
    x = np.column_stack([np.ones(data['N']), np.asarray(data['dist'])/100.])
    y = np.asarray(data['switched']); signed = 2*y-1
    def information(q):
        eta = x@q
        w = expit(eta)*expit(-eta)
        return x.T@(w[:, None]*x)
    def log_batch(q):
        eta = q[:, 0, None]+q[:, 1, None]*x[:, 1]
        return log_expit(signed[None, :]*eta).sum(axis=1)
    output.mkdir(parents=True)
    (output/'analysis-lock.json').write_bytes(lock.read_bytes())
    report = dict(status='failed', identity=spec['identity'], source_commit=frozen['source_commit'],
                  target_id=model.target_id, python=platform.python_version(), numpy=np.__version__,
                  scipy=scipy.__version__, functions=spec['functions'], rows=[], tails=[])
    write(output/'started.json', report)
    try:
        solution = solve_root(model.gradient_reference, [0.,0.], jac=lambda q: -information(q),
                              options=dict(xtol=1e-10, maxfev=spec['root_max_function_evaluations']))
        center = solution.x
        residual = float(np.max(np.abs(model.gradient_reference(center))))
        if not solution.success or not np.isfinite(center).all() or residual > spec['mode_gradient_max']:
            raise ValueError('Stationary-point check failed: '+str(solution.message))
        info = information(center); scale = np.linalg.cholesky(np.linalg.inv(info))
        report['center'] = center.tolist(); report['scale_cholesky'] = scale.tolist()
        report['root'] = dict(success=bool(solution.success), message=str(solution.message),
                              evaluations=int(solution.nfev), gradient_max=residual)
        for radius in spec['radii']:
            tail = tail_bounds(model.reference, model.gradient_reference, center, scale, radius, spec['tail_sectors'])
            report['tails'].append(tail)
            for order in spec['orders']:
                start = time.perf_counter()
                row = integrate_box(log_batch, center, scale, radius, order, spec['chunk_nodes'])
                row['analysis_seconds'] = time.perf_counter()-start
                # Exact-domain tail inequality evaluated with the computed interior denominator.
                m = tail['mass_z_scaled']; d = row['normalizer_z_scaled']
                tail_num = np.array(tail['absolute_moment_z_scaled']+[m,m,m])
                row['tail_only_mean_error_estimate'] = ((tail_num+np.abs(row['means'])*m)/d).tolist()
                row['tail_mass_over_computed_normalizer'] = m/d
                report['rows'].append(row)
                write(output/f'R{radius}-n{order}.json', row)
                print(json.dumps(dict(radius=radius, order=order, seconds=row['analysis_seconds'])), flush=True)
        report.update(status='completed', selected_radius=12, selected_order=96,
                      error_interpretation=spec['error_interpretation'], torch_imported='torch' in sys.modules,
                      jax_imported='jax' in sys.modules)
    except Exception as error:
        report['error'] = type(error).__name__+': '+str(error)
        raise
    finally:
        write(output/'result.json', report)
        write(output/'checksums.json', {p.name: sha(p) for p in sorted(output.iterdir()) if p.is_file() and p.name!='checksums.json'})


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); sub = p.add_subparsers(dest='action', required=True)
    f = sub.add_parser('freeze'); f.add_argument('--output', type=Path, required=True)
    r = sub.add_parser('run'); r.add_argument('--source', type=Path, required=True)
    r.add_argument('--lock', type=Path, required=True); r.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    if a.action == 'freeze': freeze(a.output.resolve())
    else: run(a.source.resolve(), a.lock.resolve(), a.output.resolve())
