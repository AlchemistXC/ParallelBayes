"""Independent arithmetic and corruption cases for the final W1 audit."""
from pathlib import Path
from fractions import Fraction as F
import json
import sqlite3
import sys
import pytest
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/analysis'))
import audit_w1_enclosure as a
I=a.Interval


def packed(x,rad=0):
    def dy(x):
        x=F(x);d=x.denominator
        assert d&(d-1)==0
        return [str(x.numerator),-(d.bit_length()-1)]
    return [dy(x),dy(rad)]


def test_signed_ratio_and_separate_moment_tails():
    rows=[list(map(I.point,[2,-4,2,10,4,1,1])),list(map(I.point,[1,-1,2,3,4,F(2,5),F(1,2)]))]
    tails=list(map(I.point,[F(1,10),F(1,5),F(3,10),F(2,5),F(1,2)]))
    den,ratios=a.reconstruct_posterior(rows,tails)
    assert den==I(F(3),F(31,10))
    assert ratios[0]==I(F(-26,15),F(-48,31))
    assert ratios[2].hi==F(67,15)
    assert ratios[-1]==I(F(10,31),F(11,30))


def test_unresolved_normalizer_and_illegal_negative_integral():
    den,ratios=a.reconstruct_posterior([[I(F(-1),F(1))]*7]*2,[I.point(0)]*5)
    assert ratios is None and den.lo==0
    with pytest.raises(ValueError,match='strictly positive'):
        I.point(1).ratio(den)
    with pytest.raises(ValueError,match='nonnegative'):
        I.point(-1).positive_part()


def test_relative_event_precision_is_separate():
    assert a.meets(I(F('1e-9'),F('1.0001e-9')),True)
    assert not a.meets(I(F('1e-14'),F('2e-14')),True)
    assert not a.meets(I(F(0),F('1e-15')),True)


def test_partition_t_junctions_and_equal_area_gap_overlap():
    p=a.Partition()
    for box in [(0,F(1,2),0,1),(F(1,2),1,0,F(1,3)),(F(1,2),1,F(1,3),1)]:p.add(box)
    assert p.check()['coverage_multiplicity_exact']==1
    bad=a.Partition()
    for _ in range(2):bad.add((F(0),F(1,2),F(0),F(1)))
    assert bad.area==1
    with pytest.raises(ValueError,match='gap or overlap'):bad.check()


def test_uncertain_event_boundary_dyadic_partition():
    boundary=F(7,13);start=F(-12);end=boundary
    point=start+(end-start)*F(11,32);eps=F(1,2**300)
    assert a.grid_coordinate(I(point-eps,point+eps),start,end)==F(11,32)
    with pytest.raises(ValueError,match='ambiguous'):
        a.grid_coordinate(I(F(-1),F(2)),F(0),F(1))


@pytest.fixture
def database(tmp_path):
    # A two-region exact algebra fixture, not a W1 target or a sampler.
    proto={'charge_per_cell':{'gauss2':7},'maximum_charged_evaluations_per_method':100,
           'maximum_active_cells_per_method':100,'geometry':{'center':[0.,0.],'factor':[[1.,0.],[0.,1.]]},
           'radius':1,'priorities':[['1']*7,['1']*7]}
    boxes=[[-1,1,-1,0],[-1,1,0,1]]
    values=[2,-4,2,8,2,1,1];zero=[packed(0)]*7
    binding={'identity':{'protocol_sha256':'test','method':'gauss2'},'method':'gauss2','charge_per_cell':7,
             'maximum_charged_evaluations':100,'maximum_cells':100,'priorities':proto['priorities'],
             'boxes':[[packed(v) for v in box] for box in boxes]}
    state={'splits':0,'next_id':2,'completed_external_callbacks':12,
           'quadrature':[[packed(v) for v in values]]*2,'error':[zero,zero]}
    path=tmp_path/'data.sqlite';db=sqlite3.connect(path)
    db.execute('CREATE TABLE metadata(key TEXT PRIMARY KEY,value TEXT)')
    db.execute('CREATE TABLE cells(id INTEGER PRIMARY KEY,region INTEGER,value TEXT)')
    for k,v in {'binding':binding,'state':state,'charged':14}.items():db.execute('INSERT INTO metadata VALUES (?,?)',(k,json.dumps(v)))
    for i,box in enumerate(boxes):
        db.execute('INSERT INTO cells VALUES (?,?,?)',(i,i,json.dumps({'box':[packed(v) for v in box],'value':[packed(v) for v in values],'remainder':zero,'evaluations':6})))
    db.commit();db.close()
    result={'active_cells':2,'completed_external_callbacks':12,'charged_evaluations_upper_bound':14,'committed_splits':0,
            'stop_reason':'tolerance_met','posterior':{'normalizer':{'binary_ball':packed(4)},'all_targets_met':True,'status':'posterior_targets_met',
                'functions':{n:{'binary_ball':packed(v)} for n,v in zip(a.NAMES,[-2,1,4,1,F(1,2),F(1,2),F(1,2)])}}}
    return path,proto,result


def run_database(fixture,result=True):
    p,pr,r=fixture
    return a.audit_database(p,pr,'gauss2','test',r if result else None,0,[I.point(0)]*5)


def test_complete_database_and_explicit_checkpoint_scope(database):
    report,intervals=run_database(database)
    assert all(report['functions_meeting_targets'].values())
    report,other=run_database(database,False)
    assert report['checkpoint_only'] and not report['completed_result_verified']
    assert intervals==other


def test_corrupt_quadrature_aggregate_detected(database):
    p,pr,r=database;db=sqlite3.connect(p)
    state=json.loads(db.execute("SELECT value FROM metadata WHERE key='state'").fetchone()[0])
    state['quadrature'][0][0]=packed(1)
    db.execute("UPDATE metadata SET value=? WHERE key='state'",(json.dumps(state),));db.commit();db.close()
    with pytest.raises(ValueError,match='aggregate narrows'):run_database(database)


def test_omitted_tail_or_narrowed_ratio_detected(database):
    p,pr,r=database
    tails=[I.point(F(1,8))]*5
    with pytest.raises(ValueError,match='normalizer report is too narrow'):
        a.audit_database(p,pr,'gauss2','test',r,0,tails)
    r['posterior']['functions']['alpha']['binary_ball']=packed(-1)
    with pytest.raises(ValueError,match='posterior report is too narrow'):run_database(database)


def test_missing_partition_cannot_pass(database):
    p,pr,r=database;db=sqlite3.connect(p);db.execute('DELETE FROM cells WHERE id=0');db.commit();db.close()
    with pytest.raises(ValueError,match='partition area'):run_database(database)


def test_exact_mse_range_and_paired_cancellation():
    v=[F(0),F(2)];assert a.mse_range(v,I(F(0),F(2)))==I(F(1),F(2))
    # D(c)=mean((A-c)^2-(B-c)^2)=2c-5, including an interior crossing.
    assert a.difference_range([F(0),F(4)],[F(1),F(5)],I(F(2),F(3)))==I(F(-1),F(1))
    assert a.difference_range(v,v,I(F(-100),F(100)))==I.point(0)


def test_running_or_absent_result_not_a_completed_audit(tmp_path):
    source=tmp_path/'source';source.mkdir();output=tmp_path/'audit'
    with pytest.raises(ValueError,match='completed W1 output required'):
        a.audit(source,ROOT/'benchmark/protocols/w1-reference-enclosure-v1.json',ROOT,output)
    assert not output.exists()


def test_sensitivity_preserves_planned_and_paired_failures(tmp_path,monkeypatch):
    rows=[]
    for budget in [1024,4096]:
        for workflow in range(9):
            for rep in range(24):
                rows.append({'phase':'main','task':{'budget':budget,'workflow':f'method-{workflow}','replicate':rep},
                    'outcome':'output_failure_unclassified' if workflow==0 and rep==0 else 'valid',
                    'means':[float(rep/32+workflow/8)]*7})
    (tmp_path/'W1.frame.ndjson').write_text('\n'.join(json.dumps(r) for r in rows)+'\n')
    (tmp_path/'reference-contract.json').write_text(json.dumps({'W1':{'names':a.NAMES,'means':[.25]*7}}))
    (tmp_path/'SHA256.json').write_text(json.dumps({n:a.sha(tmp_path/n) for n in ['W1.frame.ndjson','reference-contract.json']}))
    monkeypatch.setattr(a,'STATISTICS_SHA',a.sha(tmp_path/'SHA256.json'))
    result=a.sensitivity(tmp_path,{n:I(F(0),F(1)) for n in a.NAMES})
    assert result['old_outcomes']=={'valid':430,'output_failure_unclassified':2}
    assert len(result['individual'])==126 and len(result['paired'])==504
    first=next(p for p in result['paired'] if p['workflow_a']=='method-0')
    assert first['planned']==24 and first['paired_valid']==23 and 0 not in first['paired_replicates']
    assert first['old_reference_loss_difference'] is not None


def test_final_driver_checks_both_rules_and_manifest(database,tmp_path,monkeypatch):
    import copy
    import shutil
    p,proto,fixture=database
    root=tmp_path/'root';root.mkdir();source=tmp_path/'source';source.mkdir()
    (root/'frozen.py').write_text('# fixture only\n')
    proto.update(identity='w1-reference-enclosure-v1',target_id='fixture',source_commit='fixture',
        source_files={'frozen.py':a.sha(root/'frozen.py')},methods=['gauss2','simpson'],precision_bits=[128,256,384],
        charge_per_cell={'gauss2':7,'simpson':12},maximum_charged_evaluations_per_method=10000,
        shared_tail_and_qualification_reserve=2000)
    protocol=root/'protocol.json';protocol.write_text(json.dumps(proto));ph=a.sha(protocol)
    monkeypatch.setattr(a,'PROTOCOL_SHA',ph)
    def save(name,data): (source/name).write_text(json.dumps(data))
    def sidecar(name):save(name[:-5]+'.sha256.json',{'sha256':a.sha(source/name)})
    results=[];probes={}
    for method,charge,callbacks in [('gauss2',7,6),('simpson',12,11)]:
        target=source/f'{method}.sqlite';shutil.copy2(p,target);db=sqlite3.connect(target)
        binding=json.loads(db.execute("SELECT value FROM metadata WHERE key='binding'").fetchone()[0])
        probes[method]=96*charge
        binding.update(identity={'protocol_sha256':ph,'method':method},method=method,charge_per_cell=charge,maximum_charged_evaluations=10000-probes[method])
        state=json.loads(db.execute("SELECT value FROM metadata WHERE key='state'").fetchone()[0]);state['completed_external_callbacks']=2*callbacks
        for key,value in [('binding',binding),('state',state),('charged',2*charge)]:
            db.execute('UPDATE metadata SET value=? WHERE key=?',(json.dumps(value),key))
        for index,payload in list(db.execute('SELECT id,value FROM cells')):
            cell=json.loads(payload);cell['evaluations']=callbacks
            db.execute('UPDATE cells SET value=? WHERE id=?',(json.dumps(cell),index))
        db.commit();db.close()
        result=copy.deepcopy(fixture);result.update(method=method,protocol_sha256=ph,source_commit='fixture',probe_charged_evaluations=probes[method],charged_evaluations_upper_bound=2*charge,completed_external_callbacks=2*callbacks)
        save(f'{method}-result.json',result);sidecar(f'{method}-result.json');results.append(result)
        for bits in proto['precision_bits']:
            name=f'probe-{method}-{bits}.json';save(name,{'method':method,'precision_bits':bits,'charged_evaluations':32*charge});sidecar(name)
    save('tail.json',{'upper_bounds':[packed(0)]*5,'minimum_decay':packed(1)})
    sidecar('tail.json')
    save('IDENTITY.json',{'protocol_sha256':ph,'target_id':'fixture'})
    save('work-reservations.json',{'protocol_sha256':ph,'shared':320,'probes':probes})
    save('SUMMARY.json',{'protocol_sha256':ph,'target_id':'fixture','source_commit':'fixture','new_mcmc_fits':0,'preserved_old_references':True,
        'methods':results,'intersection':results[0]['posterior']['functions'],'all_method_targets_met':True,
        'charged_evaluations_upper_bound':320+sum(probes.values())+38})
    (source/'run.lock').touch()
    save('checksums.json',{v.name:a.sha(v) for v in source.iterdir() if v.name!='run.lock'})
    result=a.audit(source,protocol,root,tmp_path/'audit')
    assert result['passed'] and result['both_methods_present'] and result['all_method_targets_met']
    assert result['new_integrand_evaluations']==0
    checks=json.loads((source/'checksums.json').read_text());checks.pop('tail.json');save('checksums.json',checks)
    with pytest.raises(ValueError,match='required evidence absent'):
        a.audit(source,protocol,root,tmp_path/'refused')
    assert not (tmp_path/'refused').exists()
