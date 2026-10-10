#!/usr/bin/env python3
"""Read-only independent arithmetic/partition audit of completed W1 enclosures.

Uses exact rational endpoints, no FLINT and none of the integration/reporting
functions under audit. The derivative and supporting-plane inequalities remain
separate mathematical obligations; this is not a proof of all numerical code.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
from dataclasses import dataclass
import fcntl
from fractions import Fraction as F
import hashlib
import json
import math
from pathlib import Path
import sqlite3

PROTOCOL_SHA = '85506f871a4fedb6f1cb30da1d9509afa764d2621e40ee51c48a1a6b44a97d36'
STATISTICS_SHA = 'd928a497889e11f6aaf5829bf1ffd807a647a880a5d4ae7cef4acf3046c34bfb'
NAMES = ['alpha','beta','alpha_squared','beta_squared','p_switch_0m','p_switch_100m','beta_positive']


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(p):
    with Path(p).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def dyadic(pair):
    require(isinstance(pair,list) and len(pair)==2, 'invalid dyadic')
    n,e=int(pair[0]),int(pair[1])
    require(abs(e)<=100000 and len(str(abs(n)))<=10000, 'unreasonable dyadic')
    return F(n*(1<<e)) if e>=0 else F(n,1<<(-e))


@dataclass(frozen=True)
class Interval:
    lo: F
    hi: F

    def __post_init__(self):
        require(self.lo<=self.hi, 'reversed interval')

    @classmethod
    def point(cls,x):
        return cls(F(x),F(x))

    @classmethod
    def ball(cls,encoded):
        require(isinstance(encoded,list) and len(encoded)==2, 'invalid ball')
        m,r=map(dyadic,encoded)
        require(r>=0, 'negative radius')
        return cls(m-r,m+r)

    def __add__(self,other):
        return Interval(self.lo+other.lo,self.hi+other.hi)

    def contains(self,other):
        return self.lo<=other.lo and self.hi>=other.hi

    def ratio(self,den):
        require(den.lo>0, 'normalizer not strictly positive')
        corners=[x/y for x in (self.lo,self.hi) for y in (den.lo,den.hi)]
        return Interval(min(corners),max(corners))

    def positive_part(self):
        require(self.hi>=0, 'contradicts nonnegative integral')
        return Interval(max(F(0),self.lo),self.hi)

    def intersection(self,other):
        return Interval(max(self.lo,other.lo),min(self.hi,other.hi))

    def record(self):
        def rational(x): return [str(x.numerator),str(x.denominator)]
        return {'lower_exact':rational(self.lo),'upper_exact':rational(self.hi),
                'lower_display':float(self.lo),'upper_display':float(self.hi),
                'halfwidth_display':float((self.hi-self.lo)/2),
                'display_floats_are_not_bounds':True}


def reconstruct_posterior(regions,tails):
    require(len(regions)==2 and all(len(x)==7 for x in regions) and len(tails)==5, 'posterior dimensions')
    require(all(x.lo==x.hi and x.lo>=0 for x in tails), 'tail upper bounds must be nonnegative points')
    total=[a+b for a,b in zip(*regions)]
    mass=tails[0].hi
    denominator=total[0].positive_part()+Interval(F(0),mass)
    if denominator.lo<=0:
        return denominator,None
    numerators=[total[j]+Interval(-tails[j].hi,tails[j].hi) for j in (1,2)]
    numerators += [total[j].positive_part()+Interval(F(0),tails[t].hi) for j,t in [(3,3),(4,4),(5,0),(6,0)]]
    numerators += [regions[1][0].positive_part()+Interval(F(0),mass)]
    return denominator,[n.ratio(denominator) for n in numerators]


def meets(interval,event=False):
    radius=(interval.hi-interval.lo)/2
    if not event:
        return radius<=F('1e-8')
    return (interval.lo>0 and radius<=F('1e-13') and
            radius<=abs((interval.lo+interval.hi)/2)/100)


def grid_coordinate(interval,start,end):
    """Find a dyadic subdivision whose exact location is inside saved endpoints.

    This constructs a partition within the interval-valued boxes; it need not
    recover hidden correlations between rounded boundary representations.
    """
    require(end>start, 'invalid domain')
    a=(interval.lo-start)/(end-start); b=(interval.hi-start)/(end-start)
    for depth in range(257):
        scale=1<<depth
        first=-((-a*scale).numerator//(-a*scale).denominator)
        last=(b*scale).numerator//(b*scale).denominator
        if first==last:
            result=F(first,scale)
            require(0<=result<=1, 'cell endpoint outside domain')
            return result
        if first<last:
            raise ValueError('ambiguous saved endpoint')
    raise ValueError('endpoint subdivision unresolved at 256 levels')


class Partition:
    """Exact coverage via the jump of multiplicity across every vertical edge."""
    def __init__(self):
        self.edges=defaultdict(Counter);self.area=F(0);self.cells=0

    def add(self,rectangle):
        x0,x1,y0,y1=rectangle
        require(0<=x0<x1<=1 and 0<=y0<y1<=1, 'invalid normalized rectangle')
        for x,sign in [(x0,1),(x1,-1)]:
            self.edges[x][y0]+=sign;self.edges[x][y1]-=sign
        self.area+=(x1-x0)*(y1-y0);self.cells+=1

    def check(self):
        require(self.area==1, 'partition area differs')
        for x,changes in self.edges.items():
            nonzero={y:v for y,v in changes.items() if v}
            expected={F(0):1,F(1):-1} if x==0 else ({F(0):-1,F(1):1} if x==1 else {})
            require(nonzero==expected, 'partition has gap or overlap')
        require(0 in self.edges and 1 in self.edges, 'partition boundary absent')
        return {'cells':self.cells,'area_exact':'1','coverage_multiplicity_exact':1}


def audit_database(path,protocol,method,protocol_sha,result,probe_charge,tails):
    require(not Path(str(path)+'-wal').exists() or Path(str(path)+'-wal').stat().st_size==0,'unsettled SQLite WAL')
    db=sqlite3.connect(path.resolve().as_uri()+'?mode=ro&immutable=1',uri=True)
    try:
        require(db.execute('PRAGMA integrity_check').fetchone()[0]=='ok','SQLite integrity failure')
        meta={k:json.loads(v) for k,v in db.execute('SELECT key,value FROM metadata')}
        binding=meta['binding'];state=meta['state'];charge=protocol['charge_per_cell'][method]
        require(binding['identity']=={'protocol_sha256':protocol_sha,'method':method},'checkpoint identity')
        require(binding['method']==method and binding['charge_per_cell']==charge,'checkpoint rule')
        require(binding['priorities']==protocol['priorities'],'checkpoint priorities')
        limit=protocol['maximum_charged_evaluations_per_method']-probe_charge
        require(binding['maximum_charged_evaluations']==limit and meta['charged']<=limit,'checkpoint budget')
        require(binding['maximum_cells']==protocol['maximum_active_cells_per_method'],'checkpoint cell limit')
        geometry=protocol['geometry'];radius=F(protocol['radius'])
        require(geometry['factor'][1][0]==0 and geometry['factor'][1][1]>0,'event geometry')
        boundary=-F(geometry['center'][1])/F(geometry['factor'][1][1])
        domains=[(-radius,radius,-radius,boundary),(-radius,radius,boundary,radius)]
        require(len(binding['boxes'])==2,'two regions required')
        for box,domain in zip(binding['boxes'],domains):
            require(all(Interval.ball(v).contains(Interval.point(x)) for v,x in zip(box,domain)),'root box misses exact domain')
        partitions=[Partition(),Partition()]
        sums=[[Interval.point(0) for _ in range(7)] for _ in range(2)]
        errors=[[Interval.point(0) for _ in range(7)] for _ in range(2)]
        cells=0;max_id=-1
        for index,region,payload in db.execute('SELECT id,region,value FROM cells ORDER BY id'):
            require(region in (0,1),'invalid region');c=json.loads(payload);cells+=1;max_id=max(max_id,index)
            require(len(c['box'])==4 and len(c['value'])==len(c['remainder'])==7,'cell dimensions')
            require(c['evaluations']==(6 if method=='gauss2' else 11),'cell evaluation count')
            domain=domains[region];ends=[Interval.ball(v) for v in c['box']]
            xy=[grid_coordinate(v,domain[0 if i<2 else 2],domain[1 if i<2 else 3]) for i,v in enumerate(ends)]
            partitions[region].add(xy)
            for j in range(7):
                sums[region][j]+=Interval.ball(c['value'][j])
                e=Interval.ball(c['remainder'][j]);require(e.lo==e.hi and e.lo>=0,'invalid remainder upper bound')
                errors[region][j]+=e
        coverage=[p.check() for p in partitions]
        checkpoint_only=result is None
        if checkpoint_only:
            result={'active_cells':cells,'completed_external_callbacks':state['completed_external_callbacks'],
                    'charged_evaluations_upper_bound':meta['charged'],'committed_splits':state['splits']}
        require(cells==state['splits']+2==result['active_cells'],'cell/split count differs')
        require(state['next_id']==2+2*state['splits'] and max_id<state['next_id'],'cell identity sequence')
        callbacks=(6 if method=='gauss2' else 11)*(2+2*state['splits'])
        require(state['completed_external_callbacks']==callbacks==result['completed_external_callbacks'],'callback count differs')
        require(meta['charged']==result['charged_evaluations_upper_bound'] and meta['charged']>=charge*(2+2*state['splits']),'work reservation accounting')
        require(state['splits']==result['committed_splits'],'split counter differs')
        regions=[]
        for region in range(2):
            qs=[Interval.ball(v) for v in state['quadrature'][region]]
            es=[Interval.ball(v) for v in state['error'][region]]
            require(all(q.contains(v) for q,v in zip(qs,sums[region])),'quadrature aggregate narrows leaf bounds')
            require(all(e.contains(v) for e,v in zip(es,errors[region])),'remainder aggregate narrows leaf bounds')
            require(all(e.hi>=0 for e in es),'negative aggregate error')
            regions.append([q+Interval(-e.hi,e.hi) for q,e in zip(qs,es)])
        denominator,ratios=reconstruct_posterior(regions,tails)
        if checkpoint_only:
            actual={} if ratios is None else dict(zip(NAMES,ratios))
            return {'method':method,'checkpoint_only':True,'completed_result_verified':False,
                    'coverage':coverage,'leaf_aggregation_enclosed':True,'charged':meta['charged'],
                    'callbacks':callbacks,'denominator':denominator.record(),
                    'function_intervals':{k:v.record() for k,v in actual.items()}},actual
        reported=result['posterior'];den_saved=Interval.ball(reported['normalizer']['binary_ball'])
        require(den_saved.contains(denominator),'normalizer report is too narrow')
        actual={}
        if ratios is None:
            require(reported['functions'] is None and not reported['all_targets_met'],'unresolved normalizer promoted')
        else:
            require(set(reported['functions'])==set(NAMES),'function report incomplete')
            for name,needed in zip(NAMES,ratios):
                saved=Interval.ball(reported['functions'][name]['binary_ball'])
                require(saved.contains(needed),'posterior report is too narrow: '+name)
                actual[name]=saved
            met=all(meets(v,name=='beta_positive') for name,v in actual.items())
            require(reported['all_targets_met']==met,'target status differs')
            require(reported['status']==('posterior_targets_met' if met else 'valid_enclosure_wider_than_target'),'posterior status differs')
        reason=result['stop_reason']
        require(reason in ('tolerance_met','work_limit','coordinate_resolution','resource_stopped'),'nonterminal result')
        if reason=='tolerance_met': require(reported['all_targets_met'],'stopped early without precision')
        if reason=='work_limit':require(cells>=binding['maximum_cells'] or limit-meta['charged']<2*charge,'unexplained work limit')
        report={'method':method,'coverage':coverage,'leaf_aggregation_enclosed':True,
                'denominator':den_saved.record(),'function_intervals':{k:v.record() for k,v in actual.items()},
                'functions_meeting_targets':{k:meets(v,k=='beta_positive') for k,v in actual.items()},
                'stop_reason':reason,'charged':meta['charged'],'callbacks':callbacks,'quadrature_remainders':[[v.record() for v in row] for row in errors]}
        return report,actual
    finally:
        db.close()


def mean(values):return sum(values,F(0))/len(values)


def mse_range(values,reference):
    require(bool(values),'empty estimand group')
    center=mean(values);closest=min(reference.hi,max(reference.lo,center))
    loss=lambda c:mean([(v-c)**2 for v in values])
    return Interval(loss(closest),max(loss(reference.lo),loss(reference.hi)))


def difference_range(a,b,reference):
    require(len(a)==len(b)>0,'unequal paired group')
    intercept=mean([x*x-y*y for x,y in zip(a,b)])
    slope=-2*mean([x-y for x,y in zip(a,b)])
    ends=[intercept+slope*c for c in (reference.lo,reference.hi)]
    return Interval(min(ends),max(ends))


def sensitivity(statistics,intervals):
    manifest=statistics/'SHA256.json';require(sha(manifest)==STATISTICS_SHA,'unrecognized statistics')
    index=json.loads(manifest.read_text())
    for name in ('W1.frame.ndjson','reference-contract.json'):
        require(sha(statistics/name)==index[name],'old statistics file changed: '+name)
    reference=json.loads((statistics/'reference-contract.json').read_text())['W1']
    require(reference['names']==NAMES,'function order differs')
    rows=[json.loads(x) for x in (statistics/'W1.frame.ndjson').read_text().splitlines()]
    main=[r for r in rows if r['phase']=='main']
    require(len(main)==432,'original W1 planned denominator changed')
    groups=defaultdict(dict);outcomes=Counter()
    for row in main:
        t=row['task'];key=(t['budget'],t['workflow']);rep=t['replicate'];outcomes[row['outcome']]+=1
        require(rep not in groups[key],'duplicate W1 repeat')
        groups[key][rep]=row
    require(len(groups)==18 and all(len(v)==24 for v in groups.values()),'original W1 cells changed')
    individual=[];pairs=[]
    for name,bound in intervals.items():
        j=NAMES.index(name)
        original=Interval.point(F(reference['means'][j]))
        valid={k:{rep:F(row['means'][j]) for rep,row in rr.items() if row['outcome']=='valid' and math.isfinite(row['means'][j])} for k,rr in groups.items()}
        for (budget,workflow),v in sorted(valid.items()):
            individual.append({'function':name,'workflow':workflow,'budget':budget,'planned':24,'valid':len(v),
                'range':mse_range(list(v.values()),bound).record() if v else None,
                'old_reference_loss':mse_range(list(v.values()),original).record() if v else None,
                'old_reference_in_enclosure':bound.contains(original)})
        for budget in (1024,4096):
            workflows=sorted(w for n,w in groups if n==budget)
            for ia,wa in enumerate(workflows):
                for wb in workflows[ia+1:]:
                    a,b=valid[(budget,wa)],valid[(budget,wb)];common=sorted(set(a)&set(b))
                    interval=difference_range([a[k] for k in common],[b[k] for k in common],bound) if common else None
                    pairs.append({'function':name,'budget':budget,'workflow_a':wa,'workflow_b':wb,'planned':24,'paired_valid':len(common),
                        'paired_replicates':common,'loss_difference_range':None if interval is None else interval.record(),
                        'old_reference_loss_difference':difference_range([a[k] for k in common],[b[k] for k in common],original).record() if common else None,
                        'reference_sign_stable':None if interval is None else bool(interval.hi<0 or interval.lo>0),
                        'direction':None if interval is None else ('a_lower_loss' if interval.hi<0 else 'b_lower_loss' if interval.lo>0 else 'unresolved')})
    return {'old_frame_sha256':index['W1.frame.ndjson'],'old_outcomes':dict(outcomes),'individual':individual,'paired':pairs,
        'scope':'Exact rational propagation over saved binary64 function means and audited reference intervals; same original valid paired sets; descriptive numerical-reference sensitivity, not experiment uncertainty or a new CI. All s_f=1.'}


def audit(source,protocol_path,root,output,statistics=None):
    require(not output.exists(),'fresh audit output required')
    require(sha(protocol_path)==PROTOCOL_SHA,'frozen protocol differs')
    protocol=json.loads(protocol_path.read_text())
    require((source/'SUMMARY.json').is_file() and (source/'checksums.json').is_file(),'completed W1 output required')
    with (source/'run.lock').open('rb') as lock:
        fcntl.flock(lock,fcntl.LOCK_SH|fcntl.LOCK_NB)
        checks=json.loads((source/'checksums.json').read_text())
        for name,expected in checks.items():
            p=Path(name);require(not p.is_absolute() and '..' not in p.parts,'unsafe asset path')
            require(sha(source/p)==expected,'asset checksum differs: '+name)
        required={'SUMMARY.json','IDENTITY.json','tail.json','tail.sha256.json','work-reservations.json'}
        require(required<=set(checks),'required evidence absent from manifest')
        for name,expected in protocol['source_files'].items():require(sha(root/name)==expected,'frozen numerical source changed: '+name)
        identity=json.loads((source/'IDENTITY.json').read_text());summary=json.loads((source/'SUMMARY.json').read_text())
        require(identity=={'protocol_sha256':PROTOCOL_SHA,'target_id':protocol['target_id']},'source identity differs')
        require(summary['protocol_sha256']==PROTOCOL_SHA and summary['target_id']==protocol['target_id'] and summary['source_commit']==protocol['source_commit'],'summary identity differs')
        require(summary['new_mcmc_fits']==0 and summary['preserved_old_references'],'reference scope changed')
        tail_record=json.loads((source/'tail.json').read_text());tails=list(map(Interval.ball,tail_record['upper_bounds']))
        require(Interval.ball(tail_record['minimum_decay']).lo>0,'tail decay not positive')
        ledger=json.loads((source/'work-reservations.json').read_text())
        require(ledger['protocol_sha256']==PROTOCOL_SHA and 320<=ledger['shared']<=protocol['shared_tail_and_qualification_reserve'],'reservation binding')
        require(sha(source/'tail.json')==json.loads((source/'tail.sha256.json').read_text())['sha256'],'tail sidecar differs')
        for method in protocol['methods']:
            completed_probe_charge=0
            for bits in protocol['precision_bits']:
                name=f'probe-{method}-{bits}.json'; sidecar=f'probe-{method}-{bits}.sha256.json'
                require({name,sidecar}<=set(checks),'probe evidence absent from manifest')
                probe=json.loads((source/name).read_text())
                require(sha(source/name)==json.loads((source/sidecar).read_text())['sha256'],'probe sidecar differs')
                require(probe['method']==method and probe['precision_bits']==bits,'probe identity differs')
                charge=32*protocol['charge_per_cell'][method]
                require(probe['charged_evaluations']==charge,'probe work count differs')
                completed_probe_charge+=charge
            require(completed_probe_charge<=ledger['probes'][method],'probe reservation undercounts work')
        reports=[];method_intervals=[]
        for result in summary['methods']:
            method=result['method'];require(method in protocol['methods'],'unknown method')
            require({f'{method}.sqlite',f'{method}-result.json',f'{method}-result.sha256.json'}<=set(checks),'method evidence absent from manifest')
            require(sha(source/f'{method}-result.json')==json.loads((source/f'{method}-result.sha256.json').read_text())['sha256'],'method sidecar differs')
            require(result==json.loads((source/f'{method}-result.json').read_text()),'method projection differs')
            require(result['probe_charged_evaluations']==ledger['probes'][method],'probe charges differ')
            require(result['protocol_sha256']==PROTOCOL_SHA and result['source_commit']==protocol['source_commit'],'method identity differs')
            rep,interval=audit_database(source/f'{method}.sqlite',protocol,method,PROTOCOL_SHA,result,ledger['probes'][method],tails)
            reports.append(rep);method_intervals.append(interval)
        require([r['method'] for r in reports]==protocol['methods'][:len(reports)],'method order/duplicates')
        require(1<=len(reports)<=2,'no completed method')
        count=sum(r['charged']+ledger['probes'][r['method']] for r in reports)+ledger['shared']
        require(count==summary['charged_evaluations_upper_bound'] and count<=4000000,'total charged budget differs')
        combined={}
        if len(method_intervals)==2 and all(method_intervals):
            require(summary['intersection'] is not None,'missing intersection')
            for name in NAMES:
                required=method_intervals[0][name].intersection(method_intervals[1][name])
                stored=Interval.ball(summary['intersection'][name]['binary_ball'])
                require(stored.contains(required),'intersection rounded inward')
                combined[name]=stored
        else:require(summary['intersection'] is None,'unsupported intersection')
        met=len(reports)==2 and all(all(r['functions_meeting_targets'].values()) and len(r['functions_meeting_targets'])==7 for r in reports)
        require(summary['all_method_targets_met']==met,'combined target status differs')
        result={'identity':'w1-independent-arithmetic-audit-v1','passed':True,'checked_assets':len(checks),
            'source_summary_sha256':sha(source/'SUMMARY.json'),'protocol_sha256':PROTOCOL_SHA,
            'numerical_source_commit':protocol['source_commit'],'auditor_sha256':sha(Path(__file__)),
            'methods':reports,'tails':[x.record() for x in tails],'combined':{k:v.record() for k,v in combined.items()},
            'both_methods_present':len(reports)==2,'all_method_targets_met':met,'charged_evaluations':count,
            'new_integrand_evaluations':0,'new_mcmc_calls':0,
            'scope':'Exact endpoint arithmetic, rectangle coverage and saved bound aggregation. Does not re-evaluate integrands or prove all derivative/tail code; published certification must also rely on the documented inequalities and component qualification.'}
        propagated=sensitivity(statistics,combined) if statistics is not None and combined else None
        output.mkdir(parents=True)
        (output/'audit.json').write_text(json.dumps(result,indent=2)+'\n')
        if propagated is not None:(output/'reference-sensitivity.json').write_text(json.dumps(propagated,indent=2)+'\n')
        (output/'checksums.json').write_text(json.dumps({p.name:sha(p) for p in output.iterdir() if p.is_file()},indent=2)+'\n')
        return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('source','protocol','root','output'):p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--statistics',type=Path)
    a=p.parse_args();result=audit(a.source,a.protocol,a.root,a.output,a.statistics)
    print(json.dumps({k:result[k] for k in ('passed','both_methods_present','all_method_targets_met','checked_assets','new_integrand_evaluations')}))
