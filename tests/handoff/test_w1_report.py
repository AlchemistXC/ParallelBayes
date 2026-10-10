"""Report gates, outward decimal bounds, and retained inconclusive W1 evidence."""
from fractions import Fraction as F
import csv
import io
import json
from pathlib import Path
import shutil
import sys
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'scripts/analysis'))
import report_w1_enclosure as r


def save(path, value):
    path.write_text(json.dumps(value,indent=2)+'\n')


def bind(directory):
    save(directory/'checksums.json', {p.name:r.sha(p) for p in directory.iterdir()
                                    if p.is_file() and p.name != 'checksums.json'})


def record(lo, hi):
    return {'lower_exact':[str(lo.numerator),str(lo.denominator)],
            'upper_exact':[str(hi.numerator),str(hi.denominator)]}


def encoded(mid, radius):
    def pack(x):
        x = F(x); d = x.denominator
        assert d & (d-1) == 0
        return [str(x.numerator), -(d.bit_length()-1)]
    return {'binary_ball':[pack(mid),pack(radius)]}


@pytest.fixture
def evidence(tmp_path):
    source, audit = tmp_path/'source', tmp_path/'audit'
    source.mkdir();audit.mkdir()
    methods, checked = [], []
    values = {n:(F(1) if n!='beta_positive' else F(1,2**35),
                 F(1,2**30) if n!='beta_positive' else F(1,2**50)) for n in r.NAMES}
    for method in ('gauss2','simpson'):
        functions = {n:encoded(*v) for n,v in values.items()}
        bounds = {n:record(v[0]-v[1],v[0]+v[1]) for n,v in values.items()}
        methods.append(dict(method=method,stop_reason='tolerance_met',active_cells=2,
            charged_evaluations_upper_bound=24,completed_external_callbacks=22,
            probe_charged_evaluations=100,
            posterior=dict(normalizer=encoded(1,0),functions=functions)))
        checked.append(dict(method=method,stop_reason='tolerance_met',charged=24,callbacks=22,
            denominator=record(F(1),F(1)),function_intervals=bounds,
            functions_meeting_targets={n:True for n in r.NAMES}))
    summary=dict(protocol_sha256=r.PROTOCOL_SHA,source_commit='fixture',new_mcmc_fits=0,
        preserved_old_references=True,methods=methods,intersection=methods[0]['posterior']['functions'],
        all_method_targets_met=True,charged_evaluations_upper_bound=568)
    save(source/'SUMMARY.json',summary);bind(source)
    check=dict(passed=True,both_methods_present=True,source_summary_sha256=r.sha(source/'SUMMARY.json'),
        protocol_sha256=r.PROTOCOL_SHA,numerical_source_commit='fixture',new_mcmc_calls=0,
        new_integrand_evaluations=0,methods=checked,combined=checked[0]['function_intervals'],
        charged_evaluations=568,all_method_targets_met=True)
    save(audit/'audit.json',check)
    singles,pairs=[],[]
    for name in r.NAMES:
        for budget in (1024,4096):
            for w in range(9):
                singles.append(dict(function=name,budget=budget,workflow=str(w),planned=24,valid=24,
                    old_reference_in_enclosure=True))
            for a in range(9):
                for b in range(a+1,9):
                    k=len(pairs)%4
                    lo,hi=[(F(1),F(2)),(F(-2),F(-1)),(F(0),F(0)),(F(-1),F(1))][k]
                    pairs.append(dict(function=name,budget=budget,workflow_a=str(a),workflow_b=str(b),
                        planned=24,paired_valid=24,paired_replicates=list(range(24)),
                        loss_difference_range=record(lo,hi),old_reference_loss_difference=record(F(1),F(1)),
                        reference_sign_stable=bool(hi<0 or lo>0),
                        direction='a_lower_loss' if hi<0 else 'b_lower_loss' if lo>0 else 'unresolved'))
    save(audit/'reference-sensitivity.json',dict(old_outcomes={'valid':432},individual=singles,paired=pairs))
    bind(audit)
    return source,audit


def mutate_summary(source,audit,change):
    s=json.loads((source/'SUMMARY.json').read_text());a=json.loads((audit/'audit.json').read_text())
    change(s,a)
    save(source/'SUMMARY.json',s);bind(source)
    a['source_summary_sha256']=r.sha(source/'SUMMARY.json')
    save(audit/'audit.json',a);bind(audit)


def test_outward_decimal_rounding_for_signed_rationals():
    for value in [F(1,3),F(-1,3),F(0),F(1,10**30),F(-1,10**30),F(2),F(-2)]:
        for places in (0,12,18):
            lower=F(r.decimal_bound(value,places));upper=F(r.decimal_bound(value,places,True))
            assert lower<=value<=upper and upper-lower<=F(1,10**places)
    assert r.decimal_bound(F(-1,3),2)=='-0.34'
    assert r.decimal_bound(F(-1,3),2,True)=='-0.33'


def test_completed_report_and_relocated_rebuild(evidence,tmp_path):
    source,audit=evidence;result=r.render(source,audit)
    output=tmp_path/'report';r.build(source,audit,output)
    rows=list(csv.DictReader(io.StringIO(result['reference-intervals.csv'])))
    check=json.loads((audit/'audit.json').read_text())
    for row in rows:
        lo,hi=r.interval(check['combined'][row['function']])
        assert F(row['lower'])<=lo<=hi<=F(row['upper'])
    prov=json.loads(result['report.provenance.json'])
    assert prov['reference_sensitivity_counts']==dict(stable_sign=252,exact_tie=126,
        unresolved=126,opposite_old_sign=126,missing_pairs=0)
    assert prov['all_method_targets_met'] and prov['new_mcmc_calls']==0
    relocated=tmp_path/'relocated';relocated.mkdir()
    shutil.copytree(source,relocated/'source');shutil.copytree(audit,relocated/'audit')
    assert r.render(relocated/'source',relocated/'audit')==result
    with pytest.raises(ValueError,match='fresh report'):r.build(source,audit,output)


def test_wide_valid_interval_not_promoted(evidence):
    source,audit=evidence
    def change(s,a):
        width=F(1,2**20)
        for saved,verified in zip(s['methods'],a['methods']):
            saved['stop_reason']=verified['stop_reason']='work_limit'
            saved['posterior']['functions']['alpha']=encoded(1,width)
            verified['function_intervals']['alpha']=record(1-width,1+width)
            verified['functions_meeting_targets']['alpha']=False
        s['intersection']['alpha']=encoded(1,width);a['combined']['alpha']=record(1-width,1+width)
        s['all_method_targets_met']=a['all_method_targets_met']=False
    mutate_summary(source,audit,change)
    result=r.render(source,audit)
    assert '存在未达到预设精度的函数' in result['REPORT.md']
    assert not json.loads(result['report.provenance.json'])['all_method_targets_met']


def test_outward_saved_intersection_may_extend_one_rounding_unit(evidence):
    source,audit=evidence
    def change(s,a):
        width=F(1,2**30)+F(1,2**90)
        s['intersection']['alpha']=encoded(1,width)
        a['combined']['alpha']=record(1-width,1+width)
    mutate_summary(source,audit,change)
    assert 'reference-intervals.csv' in r.render(source,audit)


def test_narrowed_intersection_is_rejected(evidence):
    source,audit=evidence
    def change(s,a):
        s['intersection']['alpha']=encoded(1,0);a['combined']['alpha']=record(F(1),F(1))
    mutate_summary(source,audit,change)
    with pytest.raises(ValueError,match='exact intersection'):r.render(source,audit)


def test_incomplete_and_changed_evidence_cannot_generate_report(evidence,tmp_path):
    source,audit=evidence
    a=json.loads((audit/'audit.json').read_text());a['both_methods_present']=False
    save(audit/'audit.json',a);bind(audit)
    with pytest.raises(ValueError,match='both completed'):r.build(source,audit,tmp_path/'forbidden')
    assert not (tmp_path/'forbidden').exists()
    a['both_methods_present']=True;save(audit/'audit.json',a);bind(audit)
    with (source/'SUMMARY.json').open('a') as f:f.write(' ')
    with pytest.raises(ValueError,match='checksum'):r.render(source,audit)


def test_audit_summary_binding_is_required(evidence):
    source,audit=evidence
    a=json.loads((audit/'audit.json').read_text());a['source_summary_sha256']='wrong'
    save(audit/'audit.json',a);bind(audit)
    with pytest.raises(ValueError,match='audit summary binding'):r.render(source,audit)


def test_recomputed_sensitivity_sign_catches_wrong_projection(evidence):
    source,audit=evidence
    p=audit/'reference-sensitivity.json';s=json.loads(p.read_text())
    s['paired'][0]['reference_sign_stable']=False
    save(p,s);bind(audit)
    with pytest.raises(ValueError,match='sign projection'):r.render(source,audit)


def test_original_denominator_and_complete_pair_family_are_required(evidence):
    source,audit=evidence
    p=audit/'reference-sensitivity.json';s=json.loads(p.read_text())
    s['old_outcomes']['valid']=431;save(p,s);bind(audit)
    with pytest.raises(ValueError,match='old task denominator'):r.render(source,audit)
    s['old_outcomes']['valid']=432;s['paired'].pop();save(p,s);bind(audit)
    with pytest.raises(ValueError,match='incomplete reference sensitivity'):r.render(source,audit)
