"""Ordinary child-process wall and delayed fixed-tape eligibility checks.

Candidate production is measured separately. A candidate is not a research
sample until the outer worker records the required audit result. No frozen
sampler code or numerical tolerances are changed.
"""
import subprocess
import time
from pathlib import Path

import numpy as np


def audit_candidate(model,config,tape,candidate):
    from parallelbayes.torch_backend.sampling import settings,audit_path,tape_hash
    c=settings(config)
    if c['audit'] is not False:raise ValueError('Ordinary candidate must exclude the trajectory audit')
    if c['on_failure']!='error':raise ValueError('This measured profile does not permit implicit fallback')
    if candidate['config']!=c or candidate['target_id']!=model.target_id or candidate['tape_sha256']!=tape_hash(tape):
        raise ValueError('Candidate model/config/actual input identity differs')
    report=dict(status='failed',samples_eligible=False,audit=None,failure_category='numerical_failure',
                candidate_arrays_retained=True,audit_location='after_ordinary_process_exit')
    if candidate['status']=='failed':
        report['reason']='Ordinary solver or transform output standard failed';return report
    if candidate['status']!='completed' or candidate['audit'] is not None:
        raise ValueError('Inconsistent ordinary candidate eligibility')
    path=candidate['unconstrained'];accept=candidate['accept'];draws=candidate['draws']
    expected=(c['chains'],c['draws'],model.dimension)
    if path is None or draws is None or path.shape!=expected or draws.shape!=expected or accept.shape!=expected[:2]:
        raise ValueError('Candidate shape differs')
    q0=np.zeros((c['chains'],model.dimension)) if c['initial'] is None else np.asarray(c['initial'],float)
    if q0.shape==(model.dimension,):q0=np.broadcast_to(q0,(c['chains'],model.dimension)).copy()
    audit=audit_path(model,c,q0,tape,path,accept)
    report['audit']=audit
    try:
        transformed=model.constrain(path)
        transform_ok=bool(np.isfinite(draws).all() and np.isfinite(transformed).all() and
                          np.allclose(draws,transformed,rtol=1e-10,atol=1e-12))
    except (ValueError,FloatingPointError,OverflowError):transform_ok=False
    report['independent_transform_passed']=transform_ok
    if audit['passed'] and transform_ok:
        report.update(status='completed',samples_eligible=True,failure_category=None)
    else:report['reason']='Independent full path, acceptance or transform audit failed'
    return report


def ordinary_process(command,directory):
    """Time actual process startup through exit; log opening is outside it.

    The enclosing owned runtime process group supplies memory/lifecycle guards.
    No timeout is introduced. A nonzero exit is returned for outer classification.
    """
    directory=Path(directory)
    with (directory/'ordinary-stdout.log').open('wb') as stdout,(directory/'ordinary-stderr.log').open('wb') as stderr:
        before=time.perf_counter()
        result=subprocess.run(command,stdout=stdout,stderr=stderr)
        seconds=time.perf_counter()-before
    return dict(return_code=result.returncode,ordinary_process_wall_seconds=seconds,
                boundary='Before child process creation through wait for its exit; includes imports, model/input, sampling, transform, ordinary output and diagnostics',
                logs_opening_included=False,outer_audit_included=False,
                nested_sampler_timings_additive=False)
