"""Descriptive error summaries with an explicit planned-repetition denominator.

Two-MCSE shifts are a sensitivity calculation, not confidence or bias bounds.
Normal-approximation repetition projections are illustrative planning only.
"""
import math
import statistics


def summarize_function(estimates,reference,reference_kind,reference_mcse=None):
    estimates=list(estimates)
    if not estimates or reference_kind not in ('analytic','finite_mcmc','numerical_uncertified','unresolved'):
        raise ValueError('Explicit planned repetitions and reference category required')
    if reference is not None and not math.isfinite(reference):raise ValueError('Invalid reference')
    if reference_mcse is not None and (not math.isfinite(reference_mcse) or reference_mcse<0):
        raise ValueError('Invalid reference MCSE')
    valid=[float(x) for x in estimates if x is not None]
    if not all(math.isfinite(x) for x in valid):raise ValueError('Nonfinite estimate must have an explicit failure record')
    n=len(valid)
    result=dict(planned=len(estimates),valid=n,failed_or_unavailable=len(estimates)-n,
        reference_point=reference,reference_adequacy=reference_kind,reference_mcse=reference_mcse,
        conditional_squared_discrepancy=None,unconditional_squared_discrepancy=None,
        squared_discrepancy_standard_error=None,reference_shift_min=None,reference_shift_max=None,
        reference_shift_is_confidence_interval=False,planning_repetitions_relative_25pct=None,
        planning_note='Illustrative normal-approximation n from pilot squared-discrepancy variability; not a power calculation, bias bound, convergence test or automatic formal-study decision.')
    if n==0 or reference is None:return result
    def discrepancy(mu):return statistics.mean([(x-mu)**2 for x in valid])
    errors=[(x-reference)**2 for x in valid];value=statistics.mean(errors)
    result['conditional_squared_discrepancy']=value
    if n==len(estimates):result['unconditional_squared_discrepancy']=value
    sd=statistics.stdev(errors) if n>1 else None
    result['squared_discrepancy_standard_error']=sd/math.sqrt(n) if sd is not None else None
    if reference_kind=='analytic':
        result.update(reference_shift_min=value,reference_shift_max=value)
    elif reference_kind=='finite_mcmc' and reference_mcse is not None:
        lower,upper=reference-2*reference_mcse,reference+2*reference_mcse
        optimum=min(upper,max(lower,statistics.mean(valid)))
        result.update(reference_shift_min=discrepancy(optimum),reference_shift_max=max(discrepancy(lower),discrepancy(upper)))
    if (n==len(estimates) and sd is not None and sd>0 and value>0 and
        (reference_kind=='analytic' or (reference_kind=='finite_mcmc' and reference_mcse is not None))):
        result['planning_repetitions_relative_25pct']=max(2,math.ceil((1.96*sd/(.25*value))**2))
    return result
