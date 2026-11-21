"""Statistical decision rules for paired inputs in the prospective study."""
import math

import numpy as np
from scipy.stats import beta, bootstrap


def bca_mean(values, confidence, seed):
    if np.all(values == values[0]):
        return None
    result = bootstrap((values,), np.mean, confidence_level=confidence, method="BCa",
                       n_resamples=9999, random_state=seed)
    interval = tuple(map(float, result.confidence_interval))
    return interval if all(map(math.isfinite, interval)) else None


def first_use(sequential, strategy, complete, *, validated, missing_explained, seed):
    """Inputs are in the same frozen replicate order. Unavailable timings are NaN."""
    sequential, strategy = [np.asarray(values, dtype=float) for values in (sequential, strategy)]
    complete = np.asarray(complete)
    if any(values.shape != (32,) for values in (sequential, strategy, complete)):
        raise ValueError("each cell requires 32 aligned planned inputs")
    if complete.dtype.kind != "b":
        raise ValueError("complete must contain explicit boolean outcomes")
    for timings in (sequential, strategy):
        if np.any(~np.isnan(timings) & ((timings <= 0) | ~np.isfinite(timings))):
            raise ValueError("available elapsed times must be positive and finite")
    valid = np.isfinite(sequential) & np.isfinite(strategy) & complete
    count = int(valid.sum())
    deliveries = int(complete.sum())
    log_ratios = np.log(sequential[valid]) - np.log(strategy[valid])
    ratio = math.exp(float(log_ratios.mean())) if count else None
    limits = bca_mean(log_ratios, .95, seed) if count >= 20 else None
    interval = tuple(map(math.exp, limits)) if limits else None
    reasons = []
    if not validated or not missing_explained:
        reasons.append("invalid_or_unexplained")
    if count < 31:
        reasons.append("pair_coverage")
    if interval is None:
        reasons.append("interval_unavailable")
    elif interval[0] <= 1.10:
        reasons.append("benefit_not_established")
    return dict(planned=32, complete=deliveries, pairs=count, ratio=ratio, interval=interval,
                completeness_lower=float(beta.ppf(.05, deliveries, 33-deliveries)) if deliveries else 0.,
                recommended=not reasons, reasons=reasons)


def align_reference_estimates(planned_ids, method_a, method_b):
    """Align lists of (input hash, estimate) pairs; None means unavailable.

    The caller must still verify the hashes against actual input arrays and
    classify each missing fit in the study failure ledger.
    """
    def valid_id(value):
        return isinstance(value,str) and len(value)==64 and all(c in '0123456789abcdef' for c in value)
    if (not isinstance(planned_ids,(list,tuple)) or len(planned_ids)!=32
            or not all(valid_id(x) for x in planned_ids) or len(set(planned_ids))!=32):
        raise ValueError("32 unique frozen input SHA-256 identities required")
    planned=set(planned_ids)
    arrays=[];missing=[]
    for data in (method_a,method_b):
        if not isinstance(data,list):
            raise ValueError("estimates must be lists of input/estimate pairs")
        lookup={}
        for row in data:
            if not isinstance(row,(list,tuple)) or len(row)!=2 or not valid_id(row[0]) or row[0] not in planned:
                raise ValueError("estimates contain unknown input identities")
            if row[0] in lookup:
                raise ValueError("duplicate input identity")
            lookup[row[0]]=row[1]
        values=[];absent=[]
        for ident in planned_ids:
            value=lookup.get(ident)
            if value is None:
                values.append(np.nan);absent.append(ident)
            elif isinstance(value,(bool,np.bool_)) or not isinstance(value,(int,float,np.integer,np.floating)) or not math.isfinite(value):
                raise ValueError("available estimates must be finite numbers")
            else:
                values.append(float(value))
        arrays.append(np.asarray(values));missing.append(absent)
    return {'a':arrays[0], 'b':arrays[1], 'missing_a':missing[0], 'missing_b':missing[1]}


def reference_sensitivity(a, b, reference, mcse, *, seed):
    """A and B cover 32 aligned planned inputs; only NaN denotes unavailable fits."""
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    if a.shape != (32,) or b.shape != (32,):
        raise ValueError("each method requires 32 aligned planned inputs")
    if np.isinf(a).any() or np.isinf(b).any():
        raise ValueError("infinite estimates are invalid, not missing fits")
    if not math.isfinite(reference) or not math.isfinite(mcse) or mcse < 0:
        raise ValueError("invalid reference estimate or MCSE")
    valid_a, valid_b = int((~np.isnan(a)).sum()), int((~np.isnan(b)).sum())
    keep = ~np.isnan(a) & ~np.isnan(b)
    a, b = a[keep], b[keep]
    endpoints = reference-2*mcse, reference+2*mcse
    if not all(map(math.isfinite,endpoints)):
        raise ValueError("reference endpoints are nonfinite")
    if not len(a):
        return dict(planned=32, valid_a=valid_a, valid_b=valid_b, common=0,
                    reference_endpoints=endpoints, loss_difference=None,
                    intervals=None, direction=None)
    with np.errstate(over="raise", invalid="raise"):
        contrasts = [(a-b)*((a-c)+(b-c)) for c in endpoints]
    # Both BCa calls see the same RNG state and number of pairs, so they reuse
    # the input-block resampling indices.
    bands = [bca_mean(values, .975, seed) for values in contrasts] if len(a) >= 20 else None
    direction = None
    if bands is not None and all(band is not None for band in bands):
        if all(band[1] < 0 for band in bands):
            direction = "a"
        elif all(band[0] > 0 for band in bands):
            direction = "b"
    return dict(planned=32, valid_a=valid_a, valid_b=valid_b, common=len(a), reference_endpoints=endpoints,
                loss_difference=[float(values.mean()) for values in contrasts],
                intervals=bands, direction=direction)
