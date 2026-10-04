"""Formal loss estimands, reference eligibility and explicit failure conditions.

This new module never changes historical pilot summaries. Point-reference
discrepancy is not promoted to true MSE or an uncertainty-adjusted interval.
Bootstrap intervals belong to the separately frozen whole-repetition analysis.
"""
import math
import statistics

KINDS={'analytic':'analytic_mse','finite_mcmc':'finite_reference_discrepancy',
       'numerical_uncertified':'uncertified_numerical_discrepancy','unresolved':'unresolved_reference'}


def _values(estimates):
    xs=list(estimates)
    if not xs:raise ValueError('Explicit planned repetitions required')
    if not all(x is None or math.isfinite(float(x)) for x in xs):
        raise ValueError('Nonfinite estimates require explicit unavailable status')
    return [None if x is None else float(x) for x in xs]


def _reference(ref):
    kind=ref['kind'];mu=ref.get('value');mcse=ref.get('mcse')
    if kind not in KINDS:raise ValueError('Unknown reference category')
    if kind!='unresolved' and (mu is None or not math.isfinite(mu)):
        raise ValueError('Eligible reference needs a finite value')
    if mcse is not None and (not math.isfinite(mcse) or mcse<0):
        raise ValueError('Invalid reference MCSE')
    return kind,mu,mcse


def summarize(estimates,reference):
    xs=_values(estimates);kind,mu,mcse=_reference(reference)
    valid=[x for x in xs if x is not None];n=len(valid)
    row=dict(planned=len(xs),valid=n,failed_or_unavailable=len(xs)-n,
        observed_estimate_mean=statistics.mean(valid) if n else None,
        supplied_reference_value=mu,reference_kind=kind,reference_mcse=mcse,
        reference_eligible=kind!='unresolved',claim_type=KINDS[kind],
        conditional_squared_discrepancy=None,unconditional_squared_discrepancy=None,
        squared_discrepancy_standard_error=None,reference_shift_min=None,reference_shift_max=None,
        reference_shift_is_confidence_interval=False,confidence_interval=None,
        interval_status='unresolved_reference' if kind=='unresolved' else 'no_valid_estimates')
    if kind=='unresolved' or not n:return row
    errors=[(x-mu)**2 for x in valid];mean=statistics.mean(errors)
    row['conditional_squared_discrepancy']=mean
    if n==len(xs):row['unconditional_squared_discrepancy']=mean
    if n<2:row['interval_status']='fewer_than_two_valid_estimates'
    elif max(errors)==min(errors):
        row['interval_status']='degenerate_empirical_loss'
        # Observed constancy is recorded without claiming known zero uncertainty.
    else:
        row['interval_status']='pending_whole_repetition_resampling'
        row['squared_discrepancy_standard_error']=statistics.stdev(errors)/math.sqrt(n)
    if kind=='analytic':
        row['reference_shift_min']=row['reference_shift_max']=mean
    elif kind=='finite_mcmc' and mcse is not None:
        lower,upper=mu-2*mcse,mu+2*mcse
        optimum=min(upper,max(lower,statistics.mean(valid)))
        discrepancy=lambda center:statistics.mean([(x-center)**2 for x in valid])
        row['reference_shift_min']=discrepancy(optimum)
        row['reference_shift_max']=max(discrepancy(lower),discrepancy(upper))
    return row


def paired_difference(a,b,reference):
    a=_values(a);b=_values(b);kind,mu,mcse=_reference(reference)
    if len(a)!=len(b):raise ValueError('Paired planned repetition sets must have equal length')
    table={k:0 for k in ['n11','n10','n01','n00']};pairs=[]
    for x,y in zip(a,b):
        table[f'n{int(x is not None)}{int(y is not None)}']+=1
        if x is not None and y is not None:pairs.append((x,y))
    row=dict(planned=len(a),validity_table=table,conditioning='both_workflows_have_valid_estimates',
        reference_kind=kind,reference_eligible=kind!='unresolved',claim_type=KINDS[kind],
        conditional_mean_loss_difference=None,unconditional_mean_loss_difference=None,
        paired_difference_standard_error=None,reference_shift_min=None,reference_shift_max=None,
        reference_shift_is_confidence_interval=False,confidence_interval=None,
        interval_status='unresolved_reference' if kind=='unresolved' else 'no_jointly_valid_estimates')
    if kind=='unresolved' or not pairs:return row
    difference=lambda center:statistics.mean([(x-center)**2-(y-center)**2 for x,y in pairs])
    losses=[(x-mu)**2-(y-mu)**2 for x,y in pairs];value=statistics.mean(losses)
    row['conditional_mean_loss_difference']=value
    if len(pairs)==len(a):row['unconditional_mean_loss_difference']=value
    if len(pairs)<2:row['interval_status']='fewer_than_two_jointly_valid_estimates'
    elif max(losses)==min(losses):row['interval_status']='degenerate_empirical_difference'
    else:
        row['interval_status']='pending_whole_repetition_resampling'
        row['paired_difference_standard_error']=statistics.stdev(losses)/math.sqrt(len(pairs))
    if kind=='analytic':row['reference_shift_min']=row['reference_shift_max']=value
    elif kind=='finite_mcmc' and mcse is not None:
        ends=[difference(mu-2*mcse),difference(mu+2*mcse)]
        row['reference_shift_min']=min(ends);row['reference_shift_max']=max(ends)
    return row
