"""Function-level differences for fixed H1 paths; no sampler dependencies."""
import numpy as np

NAMES = ('v_over_3', 'tanh_v_over_3', 'x1_positive', 'cos_z1')


def functions(draws):
    x = np.asarray(draws)
    if x.ndim != 3 or x.shape[-1] < 2 or x.dtype != np.float64:
        raise ValueError('Expected float64 chain/time/original-parameter array')
    v, x1 = x[..., 0], x[..., 1]
    with np.errstate(over='ignore', invalid='ignore', divide='ignore', under='ignore'):
        # Same mathematical functions as the frozen estimands; preserve NaNs.
        sign = np.where(np.isfinite(x1), (x1 > 0).astype(float), np.nan)
        result = np.stack((v/3., np.tanh(v/3.), sign, np.cos(x1*np.exp(-v/2.))), -1)
    result[~np.isfinite(v), :2] = np.nan
    return result


def _summary(delta, candidate, reference, offset, chain):
    finite = np.isfinite(delta) & np.isfinite(candidate) & np.isfinite(reference)
    bad = np.argwhere(~finite)
    result = dict(count=int(delta.size), nonfinite_count=int((~finite).sum()),
                  nonfinite_positions=[list(map(int, x)) for x in bad],
                  status='finite' if finite.all() else 'nonfinite')
    if not finite.all():
        result.update(max_abs=None, rms=None, mean_abs=None, signed_mean=None,
                      candidate_mean=None, reference_mean=None, maximum_location=None)
        return result
    absolute = np.abs(delta)
    maximum = float(absolute.max())
    where = np.unravel_index(int(absolute.argmax()), absolute.shape)
    result.update(max_abs=maximum,
        rms=0. if maximum == 0 else float(maximum*np.sqrt(np.mean((delta/maximum)**2))),
        mean_abs=float(absolute.mean()), signed_mean=float(delta.mean()),
        candidate_mean=float(candidate.mean()), reference_mean=float(reference.mean()),
        maximum_location=dict(chain_1based=int(where[0]+1 if chain is None else chain+1),
            transition_1based=int(where[-1]+offset+1)))
    return result


def compare_functions(candidate, reference, discard):
    a, b = np.asarray(candidate), np.asarray(reference)
    if a.shape != b.shape or a.ndim != 3 or a.shape[-1] != 4 or not 0 <= discard < a.shape[1]:
        raise ValueError('Function paths or discard differ')
    with np.errstate(over='ignore', invalid='ignore'):
        delta = a-b
    result = []
    for scope, start in [('full', 0), ('retained', discard)]:
        for j, name in enumerate(NAMES):
            for chain in [None, *range(a.shape[0])]:
                selector = slice(None) if chain is None else slice(chain, chain+1)
                aa, bb, dd = a[selector, start:, j], b[selector, start:, j], delta[selector, start:, j]
                row = dict(scope=scope, function=name, chain='pooled' if chain is None else chain+1,
                           **_summary(dd, aa, bb, start, chain))
                if j == 2:
                    finite = np.isfinite(aa) & np.isfinite(bb)
                    positions = np.argwhere((aa != bb) & finite)
                    row.update(event_disagreements=int(len(positions)),
                        event_disagreement_rate=None if not finite.all() else float(len(positions)/aa.size),
                        event_positions=[dict(chain_1based=int(k+1 if chain is None else chain+1),
                            transition_1based=int(t+start+1)) for k, t in positions])
                result.append(row)
    return result, delta
