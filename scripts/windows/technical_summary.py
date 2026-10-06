"""Portable single-input descriptive cache summary; never a repeat interval."""
import math
import statistics

def cache_description(report,task_outcome):
    states=report['observation']['execution_outcomes'];records=report['observation']['records']
    if len(states)!=4 or len(records)!=4:raise ValueError('Four declared slots, including missing calls, required')
    if report['samples_eligible'] is not False:raise ValueError('Cache measurement cannot supply posterior samples')
    if task_outcome not in ('measurement_available','numerical_failure','resource_failure','output_failure_unclassified','infrastructure_interruption','not_run'):
        raise ValueError('Explicit outer task outcome required')
    valid=all(s=='valid' and r and r['technical_output_valid'] for s,r in zip(states,records))
    clocks=all(r is not None and r.get('executor_wall_seconds') is not None and math.isfinite(r['executor_wall_seconds']) for r in records)
    available=bool(task_outcome=='measurement_available' and report['measurement_available'] and valid and clocks)
    times=[r.get('executor_wall_seconds') for r in records if r is not None]
    known=[v for v in times if v is not None]
    return dict(task_outcome=task_outcome,measurement_available=available,samples_eligible=False,
        execution_outcomes=states,executions_recorded=sum(r is not None for r in records),
        known_executor_seconds=sum(known),missing_clock_measurements=sum(v is None for v in times),
        cached_seconds=statistics.median([r['executor_wall_seconds'] for r in records[1:]]) if available else None,
        first_seconds=records[0]['executor_wall_seconds'] if available else None,
        confidence_interval=None,independent_technical_inputs=1,formal_repetitions_added=0,
        scope='One actual technical input; three replays are technical measurements, not independent MCMC repetitions')
