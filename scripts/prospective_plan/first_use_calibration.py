"""Exploratory simultaneous one-sided split-conformal speedup calibration.

This mathematical component assumes an independently fitted, fixed prediction
model and exchangeable full vectors of development calibration and future inputs.
It cannot verify these assumptions, certify 90% conditional coverage, or establish
validity on held-out dimensions, models, devices or budgets. Predicted and observed
speedups must include the same complete first-use cost, including probe and fallback.
"""
import hashlib
import json
import math

from first_use_policy import WINDOWS, number


def is_sha256(value):
    return isinstance(value,str) and len(value)==64 and all(c in '0123456789abcdef' for c in value)


def calibrate(records, *, fit_input_sha256s, model_sha256):
    if not is_sha256(model_sha256):
        raise ValueError('a SHA-256 identity for the separately fitted model is required')
    if not isinstance(fit_input_sha256s,list) or not fit_input_sha256s or any(
            not is_sha256(x) for x in fit_input_sha256s) or len(set(fit_input_sha256s))!=len(fit_input_sha256s):
        raise ValueError('nonempty unique fitting input SHA-256 identities required')
    if not isinstance(records,list) or not records:
        raise ValueError('nonempty calibration records required')
    seen=set(); scores=[]; failed=[]
    for record in records:
        if not isinstance(record,dict) or set(record)!={'input_sha256','dimension','rows','predicted','observed'}:
            raise ValueError('calibration record fields differ')
        ident=record['input_sha256']
        if not is_sha256(ident) or ident in seen or ident in fit_input_sha256s:
            raise ValueError('calibration inputs must be unique and disjoint from fitting')
        seen.add(ident)
        if type(record['dimension']) is not int or record['dimension'] not in (8,128):
            raise ValueError('calibration may use only development dimensions')
        if type(record['rows']) is not int or record['rows'] not in (256,2048,16384,65536):
            raise ValueError('row count outside development design')
        predicted,observed=record['predicted'],record['observed']
        if not isinstance(predicted,dict) or not isinstance(observed,dict) or set(predicted)!=set(WINDOWS) or set(observed)!=set(WINDOWS):
            raise ValueError('each calibration input must account for all planned windows')
        error=[]
        for w in WINDOWS:
            prediction=number(predicted[w],f'prediction {w}',positive=True)
            actual=observed[w]
            if actual is None:
                # A non-delivery is kept as worst-case, not deleted.
                error.append(math.inf);failed.append({'input_sha256':ident,'window':w})
            else:
                actual=number(actual,f'observed {w}',positive=True)
                error.append(math.log(prediction)-math.log(actual))
        scores.append(max(error))
    n=len(scores)
    rank=(9*(n+1)+9)//10  # ceil(0.9 * (n+1)) without floating rounding.
    threshold=math.inf if rank>n else sorted(scores)[rank-1]
    canonical=json.dumps(records,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
    return {'scope':'exploratory development calibration; exchangeability not established',
            'method':'one-sided max-log-error split conformal', 'nominal_marginal_coverage':.9,
            'model_sha256':model_sha256,'fit_input_sha256s':fit_input_sha256s,
            'calibration_sha256':hashlib.sha256(canonical).hexdigest(),
            'calibration_input_sha256s':[r['input_sha256'] for r in records],
            'n':n,'rank_1_based':rank,'threshold':threshold if math.isfinite(threshold) else None,
            'threshold_infinite':not math.isfinite(threshold),'failed_observations':failed}


def bounds(predicted, calibration, *, input_sha256):
    if not is_sha256(input_sha256):
        raise ValueError('future input SHA-256 identity required')
    if input_sha256 in calibration['fit_input_sha256s'] or input_sha256 in calibration['calibration_input_sha256s']:
        raise ValueError('future input overlaps fitting or calibration')
    if not isinstance(predicted,dict) or set(predicted)!=set(WINDOWS):
        raise ValueError('all planned window predictions are required')
    predictions={w:number(predicted[w],f'prediction {w}',positive=True) for w in WINDOWS}
    if calibration['threshold_infinite']:
        return {w:0. for w in WINDOWS}
    threshold=calibration['threshold']
    if not isinstance(threshold,(int,float)) or not math.isfinite(threshold):
        raise ValueError('invalid calibration threshold')
    try:
        factor=math.exp(-threshold)
    except OverflowError:
        raise ValueError('calibrated bound overflows') from None
    result={w:predictions[w]*factor for w in WINDOWS}
    if not all(math.isfinite(x) and x>=0 for x in result.values()):
        raise ValueError('calibrated bound is nonfinite')
    return result
