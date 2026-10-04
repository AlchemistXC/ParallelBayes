"""Prespecified within-kernel development heuristic, never a convergence test."""
import numpy as np


def score_path(path,initial,accept,warmup):
    q=np.asarray(path,float);q0=np.asarray(initial,float);a=np.asarray(accept)
    if q.ndim!=3 or min(q.shape)<1 or q0.shape!=(q.shape[0],q.shape[2]) or a.shape!=q.shape[:2]:
        raise ValueError('Invalid tuning arrays')
    if not np.isfinite(q).all() or not np.isfinite(q0).all() or not np.isin(a,[False,True]).all():
        raise ValueError('Invalid finite trajectory or acceptance events')
    if isinstance(warmup,bool) or not isinstance(warmup,int) or not 0<=warmup<q.shape[1]:
        raise ValueError('Warmup must leave retained transitions')
    previous=np.concatenate((q0[:,None,:],q[:,:-1,:]),axis=1)
    delta=q[:,warmup:,:]-previous[:,warmup:,:]
    with np.errstate(over='raise',invalid='raise'):
        squared=np.einsum('ctd,ctd->ct',delta,delta,optimize=False)/q.shape[2]
    if not np.isfinite(squared).all():raise FloatingPointError('Nonfinite jump score')
    events=a[:,warmup:].astype(bool)
    return dict(mean_squared_jump_per_dimension=float(squared.mean()),
        chain_scores=squared.mean(axis=1).tolist(),transitions=int(events.size),
        accepted=int(events.sum()),rejections=int(events.size-events.sum()),
        acceptance_rate=float(events.mean()),retained_draws_per_chain=q.shape[1]-warmup,
        coordinate_scope='Fixed chosen coordinates; not invariant to reparameterization',
        statistical_convergence_claim=False)


def select_candidate(rows,steps,replicates):
    if not steps or len(set(steps))!=len(steps) or not all(np.isfinite(s) and s>0 for s in steps):
        raise ValueError('Distinct finite positive candidates required')
    if not replicates or len(set(replicates))!=len(replicates):raise ValueError('Distinct replicate identities required')
    seen={}
    for row in rows:
        key=(row['step'],row['replicate'])
        if row['step'] not in steps or row['replicate'] not in replicates or key in seen:
            raise ValueError('Unexpected or duplicate tuning result')
        seen[key]=row
    candidates=[]
    for step in steps:
        records=[seen.get((step,rep)) for rep in replicates]
        eligible=all(r is not None and r['status']=='completed' and r.get('score') is not None
                     and np.isfinite(r['score']) and r['score']>=0 for r in records)
        candidates.append(dict(step=step,eligible=bool(eligible),
            statuses=['missing' if r is None else r['status'] for r in records],
            scores=[None if r is None else r.get('score') for r in records],
            mean_score=float(np.mean([r['score'] for r in records])) if eligible else None))
    possible=[r for r in candidates if r['eligible'] and r['mean_score']>0]
    selected=max(possible,key=lambda r:(r['mean_score'],-r['step'])) if possible else None
    return dict(selected_step=None if selected is None else selected['step'],candidates=candidates,
        reason='maximum mean ESJD/d across all planned valid development replicates; exact ties choose smaller step' if selected else 'no valid positive-motion candidate',
        failures_deleted=False,statistical_convergence_claim=False)
