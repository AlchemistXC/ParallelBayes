"""Report contracts with explicitly artificial statistics, never native evidence."""
import copy
import json
import math
from pathlib import Path
import shutil
import sys

import pytest

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'scripts/analysis'),str(ROOT/'scripts/completion')]
from test_formal_statistics import artificial_frame
from formal_statistics import summarize_model
from formal_runtime import atomic_json,file_hash
from formal_analyze import output_inventory
from formal_report import StatisticsBundle,build,diagnostic_rows,model_tables,nuts_rows,ratio_row


def seal(root):
    (root/'SHA256.json').unlink(missing_ok=True)
    atomic_json(root/'SHA256.json',output_inventory(root))
    return file_hash(root/'SHA256.json')


def make_bundle(root,*,technical=False,gap=False):
    rows,ref,protocol,allocation=artificial_frame(1 if technical else 32)
    if technical:protocol['scope_kind']='technical_batch_validation'
    for row in rows:
        if row['means'] is None:continue
        row['diagnostics']=[dict(variable=name,mean=value,sd=1.,rhat=None if name=='constant' else 1.02,
            ess_bulk=None if name=='constant' else 15.,ess_tail=None if name=='constant' else 12.,
            mcse_mean=None if name=='constant' else .2) for name,value in zip(ref['names'],row['means'])]
        if row['task']['kernel']=='nuts':
            row['nuts']=dict(chain_diagnostics=[dict(chain=i,records=[dict(diagnostics=dict(divergences={'chain 0':[0] if i==0 else []}))],
                tree_depth_hit_count=None,tree_depth_note='not supplied',max_tree_depth=8) for i in range(4)])
    if gap:rows[0].update(disposition='evidence_gap',outcome=None,means=None,diagnostics=None,costs=None)
    root.mkdir()
    s=summarize_model(rows,ref,name='G1',protocol=protocol,allocation=allocation,output=root/'G1')
    frame=dict(scope=protocol['scope_kind'],identity=protocol['identity'],protocol_sha256=protocol['protocol_sha256'],
        main_planned=s['main_planned'],cache_planned=s['cache_planned'],formal_scientific_repetitions_per_model=1 if technical else 32)
    atomic_json(root/'SUMMARY.json',dict(frame=frame,models=[s],formal_inference_complete=False))
    atomic_json(root/'reference-contract.json',dict(G1=ref))
    return root,seal(root)


@pytest.fixture(scope='module')
def complete(tmp_path_factory):return make_bundle(tmp_path_factory.mktemp('report-source')/'statistics')


def test_small_frame_requires_fixture_and_preserves_all_qualifications(complete,tmp_path):
    root,digest=complete
    with pytest.raises(ValueError,match='Complete formal design'):StatisticsBundle(root,digest)
    receipt=build(root,digest,tmp_path/'report',fixture=True,render=False)
    assert receipt['fixture'] and not receipt['scientific_results']
    assert receipt['new_sampler_calls']==receipt['new_statistical_repetitions']==0
    assert receipt['figures']==[]
    tables=json.loads((tmp_path/'report/G1/tables.json').read_text())
    assert sum(r['planned'] for r in tables['tasks'])==320
    assert len(tables['task_costs'])==320*4
    assert len(tables['diagnostics'])==30
    missing=next(r for r in tables['diagnostics'] if r['function']=='varying' and r['workflow']=='cpu-rwm-sequential' and r['budget']==8)
    assert (missing['planned'],missing['received'],missing['missing'])==(32,31,1)
    constant=next(r for r in tables['diagnostics'] if r['function']=='constant' and r['workflow']=='cpu-rwm-sequential' and r['budget']==8)
    assert constant['rhat_undefined']==31 and constant['ess_tail_minimum'] is None
    assert all(r['point'] is None and not r['plot_point'] for r in tables['errors'] if r['function']=='unresolved')
    assert all(r['point']==0. and r['low'] is None for r in tables['errors'] if r['function']=='constant')
    assert '人工数据' in (tmp_path/'report/report.tex').read_text()
    assert file_hash(tmp_path/'report/report.tex')==json.loads((tmp_path/'report/SHA256.json').read_text())['report.tex']
    with pytest.raises(ValueError,match='Fresh report'):build(root,digest,tmp_path/'report',fixture=True,render=False)


def test_ratio_intervals_are_exponentiated_scale_and_not_log_bounds(complete):
    root,digest=complete
    _,tables=model_tables(StatisticsBundle(root,digest,fixture=True),'G1')
    row=next(r for r in tables['ratios'] if r['phase']=='cached_executor')
    saved=row['source_record']
    assert row['low']==saved['ratio_confidence_interval']['low']==pytest.approx(math.exp(saved['confidence_interval']['low']))
    assert row['high']==saved['ratio_confidence_interval']['high']
    assert row['paired']==31 and row['validity_table']==dict(n11=31,n10=0,n01=1,n00=0)
    altered=copy.deepcopy(saved);altered['geometric_mean_ratio']=.01
    result=ratio_row(altered,phase='cached_executor',kind='same_kernel_execution')
    assert result['point']<result['low']  # An interval need not contain the point estimate.


def test_nuts_unknown_tree_depth_is_not_zero_and_divergence_denominator_is_draws(complete):
    root,digest=complete
    _,tables=model_tables(StatisticsBundle(root,digest,fixture=True),'G1')
    row=next(r for r in tables['nuts'] if r['budget']==8)
    assert row['known_divergences']==32 and row['known_divergence_chains']==128
    assert row['divergence_fraction_among_recorded_chain_draws']==32/(128*8)
    assert row['complete_tree_depth_hits'] is None and row['unknown_tree_depth_chains']==128
    rows=json.loads((root/'G1/task-frame.json').read_text())
    child=next(r for r in rows if r.get('nuts'))['nuts']['chain_diagnostics'][0]
    child['records'][0]['diagnostics']['divergences']['chain 0']=[0,0]
    with pytest.raises(ValueError,match='divergence positions'):nuts_rows(rows)


@pytest.mark.parametrize('alteration',['tamper','extra','semantic'])
def test_corrupted_or_inconsistent_statistics_are_rejected(complete,tmp_path,alteration):
    source,digest=complete;root=tmp_path/'copy';shutil.copytree(source,root)
    if alteration=='extra':(root/'not-in-manifest').write_text('extra')
    else:
        p=root/'G1/function-0.json';value=json.loads(p.read_text())
        value['error']['workflows']['cpu-rwm-sequential@8']['planned']=33
        atomic_json(p,value)
        if alteration=='semantic':digest=seal(root)
    with pytest.raises(ValueError):
        model_tables(StatisticsBundle(root,digest,fixture=True),'G1')


def test_partial_model_and_technical_scope_never_make_formal_figures(tmp_path):
    root,digest=make_bundle(tmp_path/'partial',gap=True)
    _,tables=model_tables(StatisticsBundle(root,digest,fixture=True),'G1')
    assert tables['errors']==[] and tables['paired_errors']==[]
    assert sum(r['outcomes'].get('unknown_evidence',0) for r in tables['tasks'])==1
    root,digest=make_bundle(tmp_path/'technical',technical=True)
    result=build(root,digest,tmp_path/'technical-report',fixture=True,render=False)
    assert result['frame']['scope']=='technical_batch_validation' and not result['scientific_results']


def test_diagnostics_cannot_promote_failed_task(complete):
    root,_=complete;rows=json.loads((root/'G1/task-frame.json').read_text())
    row=next(r for r in rows if r['diagnostics']);row['outcome']='numerical_failure'
    with pytest.raises(ValueError,match='ineligible'):diagnostic_rows(rows,['varying','constant','unresolved','finite_reference','quadrature'])


def test_rendered_figures_keep_zeros_unresolved_reference_and_fixture_watermark(complete,tmp_path):
    pytest.importorskip('matplotlib')
    root,digest=complete;out=tmp_path/'rendered'
    result=build(root,digest,out,fixture=True,render=True)
    assert len(result['figures'])==6 and sum(f['panels'] for f in result['figures'])==13
    const=json.loads((out/'G1/inference-1.contract.json').read_text())
    assert const['axis_scales']['error']['scale']=='linear' and not const['axis_scales']['error']['zero_values_replaced']
    unknown=json.loads((out/'G1/inference-2.contract.json').read_text())
    assert all(not p['plotted'] for p in unknown['points'])
    for f in result['figures']:
        stem=(out/f['file']).with_suffix('')
        assert stem.with_suffix('.pdf').stat().st_size>1000
        assert 'ARTIFICIAL TEST DATA' in stem.with_suffix('.svg').read_text()


def test_full_layout_is_explicitly_artificial_and_keeps_all_configuration_slots(complete,tmp_path):
    pytest.importorskip('matplotlib')
    from batch_contract import WORKFLOWS
    from formal_plots import configure,execution_figure,inference_figure,signed_axis,plt
    root,digest=complete
    _,tables=model_tables(StatisticsBundle(root,digest,fixture=True),'G1')
    sample=next(r for r in tables['errors'] if r['function']=='varying' and r['workflow']=='cpu-nuts-spawn_chains' and r['phase']=='ordinary_workflow')
    difference=next(r for r in tables['paired_errors'] if r['function']=='varying' and r['kind']=='end_to_end_workflow')
    ratio=next(r for r in tables['ratios'] if r['phase']=='cached_executor')
    errors=[];contrasts=[];ratios=[]
    for i,(w,config) in enumerate(WORKFLOWS.items()):
        for j,b in enumerate([256,1024,4096,16384]):
            point=(i+1)/(j+1);seconds=(i+1)*(j+1)
            errors.append(dict(sample,workflow=w,budget=b,point=point,low=.9*point,high=1.1*point,
                mean_seconds=seconds,cost_low=.9*seconds,cost_high=1.1*seconds))
            if config['kernel']!='nuts':
                contrasts.append(dict(difference,workflow_a=w,budget=b,point=i-4.,low=i-5.,high=i-3.))
            if config['executor'] in ('online_picard','quasi_deer'):
                a=config['device']+'-'+config['kernel']+'-sequential'
                for k,phase in enumerate(['cached_executor','ordinary_workflow','research_execution']):
                    point=10.**(j-2+k/3)
                    ratios.append(dict(ratio,workflow_a=a,workflow_b=w,budget=b,phase=phase,point=point,low=.8*point,high=1.2*point))
    data=dict(errors=errors,paired_errors=contrasts,ratios=ratios)
    configure();dest=tmp_path/'layout';dest.mkdir()
    execution_figure('G1',data,dest,fixture=True,technical=False)
    inference_figure('G1','varying',0,data,dest,fixture=True,technical=False)
    c=json.loads((dest/'execution-costs.contract.json').read_text())
    assert len(c['cells'])==48
    c=json.loads((dest/'inference-0.contract.json').read_text())
    assert len(c['points'])==36 and len(c['budget_marker_sizes'])==4
    fig,ax=plt.subplots()
    scale=signed_axis(ax,'x',[-1000.,0.,.001])
    assert scale['scale']=='symlog' and not scale['zero_values_replaced']
    plt.close(fig)
