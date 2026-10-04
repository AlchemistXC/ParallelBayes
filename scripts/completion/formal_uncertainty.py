"""Pointwise BCa uncertainty with one archived resampling plan per target.

The independent unit is a complete four-chain repetition. All workflows,
budgets, functions, failures and costs reuse the same row indices. References
are held fixed; these intervals do not propagate unknown reference bias.

BCa definition and tie convention are checked against scipy.stats.bootstrap
1.15.3 through its public API. No sampling or frozen historical code is used.
"""
from dataclasses import dataclass
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import zipfile

import numpy as np
from scipy.special import ndtr, ndtri
from scipy.stats import binomtest

from formal_error_summary import summarize, paired_difference


def _stamp(namespace, model, ids, seed, indices):
    header=json.dumps(dict(schema=1,namespace=namespace,model=model,
        replicate_ids=ids,rng_seed_hex=hex(seed),shape=list(indices.shape)),
        sort_keys=True,separators=(',',':')).encode()
    return hashlib.sha256(header+np.asarray(indices,dtype='<i8').tobytes()).hexdigest()


@dataclass(frozen=True)
class ResamplingPlan:
    namespace: str
    model: str
    replicate_ids: tuple
    rng_seed: int
    indices: np.ndarray
    sha256: str

    def receipt(self):
        return dict(schema=1,namespace=self.namespace,model=self.model,
            replicate_ids=list(self.replicate_ids),rng_seed_hex=hex(self.rng_seed),
            rng='numpy.Generator(PCG64)',n_resamples=len(self.indices),
            planned_repetitions=len(self.replicate_ids),sha256=self.sha256,
            independent_unit='complete_four_chain_repetition',
            reference_resampled=False,simultaneous_coverage=False)

    def validate(self):
        if self.indices.ndim!=2 or self.indices.shape[1]!=len(self.replicate_ids):
            raise ValueError('Resampling plan shape differs')
        if self.indices.dtype.kind not in 'iu' or np.any(self.indices<0) or np.any(self.indices>=len(self.replicate_ids)):
            raise ValueError('Resampling indices outside declared repetitions')
        if self.sha256!=_stamp(self.namespace,self.model,self.replicate_ids,self.rng_seed,self.indices):
            raise ValueError('Resampling plan identity or bytes changed')


def create_plan(namespace,model,replicate_ids,n_resamples=9999):
    ids=tuple(replicate_ids)
    if not namespace or not model or not isinstance(namespace,str) or not isinstance(model,str):
        raise ValueError('Explicit experiment namespace and model required')
    if len(ids)<2 or any(not isinstance(x,str) or not x for x in ids) or len(set(ids))!=len(ids):
        raise ValueError('At least two unique string repetition IDs required')
    if isinstance(n_resamples,bool) or not isinstance(n_resamples,(int,np.integer)) or n_resamples<2:
        raise ValueError('At least two resamples required')
    if len(ids)*int(n_resamples)*8>64*1024**2:
        raise MemoryError('Single resampling plan exceeds 64 MiB; do not materialize full study arrays')
    seed=int.from_bytes(hashlib.sha256(json.dumps(['parallelbayes-bootstrap-v1',namespace,model],
        separators=(',',':')).encode()).digest()[:16],'little')
    indices=np.random.default_rng(seed).integers(0,len(ids),size=(int(n_resamples),len(ids)),dtype=np.int64)
    stamp=_stamp(namespace,model,ids,seed,indices)
    indices.setflags(write=False)
    return ResamplingPlan(namespace,model,ids,seed,indices,stamp)


def save_plan(plan,directory):
    """Archive actual indices and their ordered repetition identities once."""
    plan.validate()
    directory=Path(directory)
    directory.mkdir(parents=True,exist_ok=False)
    payload=directory/'indices.npz'
    np.savez_compressed(payload,indices=plan.indices)
    record=dict(receipt=plan.receipt(),indices_file=payload.name,
        indices_file_sha256=hashlib.sha256(payload.read_bytes()).hexdigest())
    (directory/'plan.json').write_text(json.dumps(record,indent=2,allow_nan=False)+'\n')


def load_plan(directory):
    """Verify stored bytes and deterministic identity before using a plan."""
    directory=Path(directory)
    record=json.loads((directory/'plan.json').read_text())
    if record['indices_file']!='indices.npz':raise ValueError('Unexpected plan payload name')
    payload=directory/'indices.npz'
    if hashlib.sha256(payload.read_bytes()).hexdigest()!=record['indices_file_sha256']:
        raise ValueError('Archived resampling indices hash differs')
    with zipfile.ZipFile(payload) as z:
        if z.namelist()!=['indices.npy'] or z.infolist()[0].file_size>64*1024**2+4096:
            raise ValueError('Unexpected or oversized plan archive')
    receipt=record['receipt']
    expected=create_plan(receipt['namespace'],receipt['model'],receipt['replicate_ids'],receipt['n_resamples'])
    if expected.receipt()!=receipt:raise ValueError('Stored resampling identity is inconsistent')
    with np.load(payload,allow_pickle=False) as z:
        actual=z['indices']
        if actual.dtype!=expected.indices.dtype or not np.array_equal(actual,expected.indices):
            raise ValueError('Archived indices differ from declared deterministic plan')
    return expected


def _aligned(plan, values):
    if set(values)!=set(plan.replicate_ids):
        raise ValueError('Every planned repetition ID required; use explicit None for unavailable estimates')
    xs=[values[x] for x in plan.replicate_ids]
    if any(x is not None and not np.isfinite(float(x)) for x in xs):
        raise ValueError('Nonfinite observations need explicit unavailable status')
    return xs


def _bca(row, values, valid, plan):
    """BCa for a conditional mean; missing rows remain in the sampling frame."""
    count=int(valid.sum())
    row.update(confidence_interval=None,interval_method='BCa',confidence_level=.95,
        interval_coverage='pointwise_conditional_on_supplied_reference',
        minimum_valid_repetitions=20,resampling_plan_sha256=plan.sha256)
    if count<20:
        row['interval_status']='fewer_than_20_valid_repetitions'
        return None
    observed=values[valid]
    if np.ptp(observed)==0:
        row['interval_status']='degenerate_empirical_loss_or_difference'
        return None
    clean=np.where(valid,values,0.)
    bootstrap=np.empty(len(plan.indices),dtype=float)
    denominators=np.empty(len(plan.indices),dtype=np.int64)
    # Bound temporary gather arrays, independent of the number of functions.
    for start in range(0,len(plan.indices),64):
        indices=plan.indices[start:start+64]
        denominators[start:start+len(indices)]=valid[indices].sum(axis=1)
        numerator=clean[indices].sum(axis=1)
        np.divide(numerator,denominators[start:start+len(indices)],
            out=bootstrap[start:start+len(indices)],where=denominators[start:start+len(indices)]>0)
    invalid=denominators==0
    bootstrap[invalid]=np.nan
    row['resampled_valid_count_range']=[int(denominators.min()),int(denominators.max())]
    row['undefined_bootstrap_replicates']=int(invalid.sum())
    if invalid.any() or not np.isfinite(bootstrap).all():
        row['interval_status']='undefined_bootstrap_statistic'
        return bootstrap
    # Delete each planned repetition, including failures, from the same frame.
    jackknife=(clean.sum()-clean)/(count-valid.astype(int))
    theta=float(observed.mean())
    centered=jackknife.mean()-jackknife
    scale=np.max(np.abs(centered))
    if scale==0 or not np.isfinite(jackknife).all():
        row['interval_status']='degenerate_jackknife'
        return bootstrap
    centered=centered/scale
    acceleration=float(np.sum(centered**3)/(6*np.sum(centered**2)**1.5))
    percentile=(np.count_nonzero(bootstrap<theta)+np.count_nonzero(bootstrap<=theta))/(2*len(bootstrap))
    if not 0<percentile<1:
        row['interval_status']='degenerate_bias_correction'
        return bootstrap
    z0=ndtri(percentile)
    z=z0+ndtri(np.array([.025,.975]))
    divisor=1-acceleration*z
    if np.any(divisor<=0):
        row['interval_status']='singular_bca_adjustment'
        return bootstrap
    quantiles=ndtr(z0+z/divisor)
    if not (np.isfinite(quantiles).all() and 0<quantiles[0]<quantiles[1]<1):
        row['interval_status']='invalid_bca_quantiles'
        return bootstrap
    bounds=np.quantile(bootstrap,quantiles,method='linear')
    if not np.isfinite(bounds).all() or bounds[0]>=bounds[1]:
        row['interval_status']='degenerate_bca_interval'
        return bootstrap
    row.update(interval_status='available',
        confidence_interval=dict(low=float(bounds[0]),high=float(bounds[1])),
        bca_bias_percentile=float(percentile),bca_acceleration=acceleration,
        bca_adjusted_quantiles=quantiles.tolist(),
        bootstrap_expected_tail_counts=[float(len(bootstrap)*quantiles[0]),float(len(bootstrap)*(1-quantiles[1]))])
    return bootstrap


def analyze_function(plan,estimates,reference,pairs=()):
    """Analyze one fixed function across all workflow/budget labels.

    Each label maps every planned repetition ID to a finite estimate or None.
    Returns JSON-ready summaries plus separately archivable bootstrap arrays.
    A new function call must reuse the same plan, not a new random seed.
    """
    plan.validate()
    if not estimates:raise ValueError('At least one workflow required')
    xs={name:_aligned(plan,v) for name,v in estimates.items()}
    rows={};pair_rows=[];distributions={}
    for name,values in xs.items():
        row=summarize(values,reference)
        if row['reference_eligible'] and row['interval_status']!='nonfinite_loss':
            valid=np.array([v is not None for v in values])
            losses=np.array([0. if v is None else (v-reference['value'])**2 for v in values])
            dist=_bca(row,losses,valid,plan)
            if dist is not None:distributions['workflow:'+name]=dist
        rows[name]=row
    for i,(a,b) in enumerate(pairs):
        if a==b or a not in xs or b not in xs:raise ValueError('Distinct declared workflow pair required')
        row=paired_difference(xs[a],xs[b],reference)
        row.update(workflow_a=a,workflow_b=b,direction='A_squared_loss_minus_B_squared_loss')
        if row['reference_eligible'] and row['interval_status']!='nonfinite_loss':
            valid=np.array([x is not None and y is not None for x,y in zip(xs[a],xs[b])])
            losses=np.array([0. if x is None or y is None else (x-reference['value'])**2-(y-reference['value'])**2 for x,y in zip(xs[a],xs[b])])
            dist=_bca(row,losses,valid,plan)
            if dist is not None:distributions['pair:'+str(i)]=dist
        pair_rows.append(row)
    return dict(resampling=plan.receipt(),workflows=rows,pairs=pair_rows,
        bootstrap_statistics=distributions,
        scope='Per-function pointwise repeated-run uncertainty; not convergence, simultaneous coverage, or propagated reference uncertainty.')


def analyze_costs(plan,costs,outcomes,pairs=(),phase='unspecified'):
    """One explicitly named timing phase, retaining unsuccessful attempt costs.

    Outcomes distinguish valid output, numerical failure, infrastructure
    interruption and not-run tasks. Cost ratios condition on both valid;
    total recorded consumption always retains known costs of every outcome.
    """
    plan.validate()
    if not costs or set(costs)!=set(outcomes):raise ValueError('Matching cost/outcome workflow sets required')
    states={};durations={};rows={};pair_rows=[];distributions={}
    allowed=('valid','numerical_failure','infrastructure_interruption','not_run')
    for name,values in costs.items():
        xs=_aligned(plan,values)
        if any(x is not None and x<0 for x in xs):raise ValueError('Timing values must be nonnegative seconds')
        if set(outcomes[name])!=set(plan.replicate_ids):raise ValueError('Every planned outcome required')
        ss=[outcomes[name][r] for r in plan.replicate_ids]
        if any(s not in allowed for s in ss):raise ValueError('Unknown task outcome')
        states[name]=ss;durations[name]=xs
        recorded=np.array([x is not None for x in xs]);n=int(recorded.sum())
        values=np.array([0. if x is None else x for x in xs],dtype=float)
        counts={s:ss.count(s) for s in allowed}
        valid_values=[x for x,s in zip(xs,ss) if s=='valid' and x is not None]
        row=dict(planned=len(xs),outcome_counts=counts,recorded_costs=n,missing_costs=len(xs)-n,
            total_recorded_seconds=math.fsum(values.tolist()),
            unusable_output_cost_seconds=math.fsum(x for x,s in zip(xs,ss) if x is not None and s!='valid'),
            mean_recorded_seconds=math.fsum(values.tolist())/n if n else None,
            mean_all_planned_seconds=math.fsum(values.tolist())/n if n==len(xs) else None,
            mean_successful_seconds=math.fsum(valid_values)/len(valid_values) if valid_values else None,
            failure_rate=None,failure_rate_interval=None,
            failure_interval_status='incomplete_scientific_outcomes',phase=phase,
            cost_estimator_condition='timing_recorded_including_unsuccessful_attempts')
        if counts['infrastructure_interruption']==counts['not_run']==0:
            failed=counts['numerical_failure'];ci=binomtest(failed,len(xs)).proportion_ci(confidence_level=.95,method='exact')
            row.update(failure_rate=failed/len(xs),failure_rate_interval=dict(low=float(ci.low),high=float(ci.high)),
                       failure_interval_status='available_pointwise_clopper_pearson')
        dist=_bca(row,values,recorded,plan)
        row['interval_coverage']='pointwise_conditional_on_timing_recorded'
        if dist is not None:distributions['workflow:'+name]=dist
        rows[name]=row
    for i,(a,b) in enumerate(pairs):
        if a==b or a not in durations or b not in durations:raise ValueError('Distinct declared workflow pair required')
        counts=Counter(f'n{int(x=="valid")}{int(y=="valid")}' for x,y in zip(states[a],states[b]))
        valid=np.array([x=='valid' and y=='valid' for x,y in zip(states[a],states[b])])
        missing=sum(flag and (x is None or y is None) for flag,x,y in zip(valid,durations[a],durations[b]))
        zero=sum(flag and (x==0 or y==0) for flag,x,y in zip(valid,durations[a],durations[b]))
        row=dict(workflow_a=a,workflow_b=b,planned=len(valid),phase=phase,
            validity_table={k:counts[k] for k in ['n11','n10','n01','n00']},
            conditioning='both_workflows_have_valid_outputs',
            ratio_definition='geometric_mean_of_A_seconds_divided_by_B_seconds',
            jointly_valid_pairs_missing_cost=int(missing),jointly_valid_pairs_zero_cost=int(zero),
            mean_log_ratio=None,geometric_mean_ratio=None,ratio_confidence_interval=None,
            confidence_interval=None,interval_status='no_jointly_valid_estimates',resampling_plan_sha256=plan.sha256)
        if missing or zero:
            row['interval_status']='unavailable_or_zero_cost_in_jointly_valid_pairs'
        else:
            logs=np.array([math.log(x)-math.log(y) if flag else 0. for flag,x,y in zip(valid,durations[a],durations[b])])
            if valid.any():
                row['mean_log_ratio']=float(logs[valid].mean())
                try:row['geometric_mean_ratio']=math.exp(row['mean_log_ratio'])
                except OverflowError:row['ratio_scale_status']='overflow'
            dist=_bca(row,logs,valid,plan)
            row['interval_coverage']='pointwise_conditional_on_both_valid_outputs'
            if dist is not None:distributions['pair:'+str(i)]=dist
            if row['confidence_interval'] is not None:
                try:
                    row['ratio_confidence_interval']={k:math.exp(v) for k,v in row['confidence_interval'].items()}
                except OverflowError:
                    row['ratio_scale_status']='overflow'
            row['confidence_interval_scale']='log_cost_ratio'
        pair_rows.append(row)
    return dict(resampling=plan.receipt(),phase=phase,workflows=rows,pairs=pair_rows,
        bootstrap_statistics=distributions,
        scope='Named recorded timing phase, not automatically a complete ordinary or audit workflow; failed-run cost retained. Ratios condition on both outputs valid.')
