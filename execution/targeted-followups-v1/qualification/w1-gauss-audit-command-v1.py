from pathlib import Path
import argparse,sys,json,hashlib,time
p=argparse.ArgumentParser()
p.add_argument('--root',type=Path,required=True);p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
a=p.parse_args();root=a.root.resolve();source=a.source.resolve();out=a.output.resolve()
sys.path.insert(0,str(root/'scripts/analysis'))
import audit_w1_enclosure as audit
assert not (out/'audit.json').exists(),'Do not overwrite earlier audit'
ph=root/'benchmark/protocols/w1-reference-enclosure-v1.json'
assert audit.sha(ph)==audit.PROTOCOL_SHA
protocol=json.loads(ph.read_text())
for name,h in protocol['source_files'].items():assert audit.sha(root/name)==h,name
files=['IDENTITY.json','tail.json','tail.sha256.json','gauss2-result.json','gauss2-result.sha256.json','gauss2.sqlite']
for bits in protocol['precision_bits']:files += [f'probe-gauss2-{bits}.json',f'probe-gauss2-{bits}.sha256.json']
before={f:audit.sha(source/f) for f in files}
identity=json.loads((source/'IDENTITY.json').read_text())
assert identity=={'protocol_sha256':audit.PROTOCOL_SHA,'target_id':protocol['target_id']}
for name in ['tail','gauss2-result']+[f'probe-gauss2-{b}' for b in protocol['precision_bits']]:
    assert before[name+'.json']==json.loads((source/(name+'.sha256.json')).read_text())['sha256'],name
result=json.loads((source/'gauss2-result.json').read_text());tail=json.loads((source/'tail.json').read_text())
assert result['method']=='gauss2' and result['source_commit']==protocol['source_commit'] and result['protocol_sha256']==audit.PROTOCOL_SHA
assert audit.Interval.ball(tail['minimum_decay']).lo>0
charge=0
for bits in protocol['precision_bits']:
    probe=json.loads((source/f'probe-gauss2-{bits}.json').read_text())
    assert probe['method']=='gauss2' and probe['precision_bits']==bits
    assert probe['charged_evaluations']==32*protocol['charge_per_cell']['gauss2']
    charge+=probe['charged_evaluations']
assert charge<=result['probe_charged_evaluations']
started=time.monotonic()
report,intervals=audit.audit_database(source/'gauss2.sqlite',protocol,'gauss2',audit.PROTOCOL_SHA,result,result['probe_charged_evaluations'],list(map(audit.Interval.ball,tail['upper_bounds'])))
after={f:audit.sha(source/f) for f in files}
assert before==after,'Source changed while being read'
assert len(intervals)==7 and all(report['functions_meeting_targets'].values())
record={'identity':'w1-gauss-completed-method-audit-v1','scope':'Completed Gauss method only, while the separate Simpson calculation remains active. Not the final dual-method audit or portable rebuild.','completed_method_verified':True,'full_study_verified':False,'publication_eligible_as_final_dual_method_result':False,'protocol_sha256':audit.PROTOCOL_SHA,'target_id':protocol['target_id'],'frozen_source_commit':protocol['source_commit'],'auditor_sha256':audit.sha(root/'scripts/analysis/audit_w1_enclosure.py'),'command_sha256':audit.sha(Path(__file__)),'original_files_unchanged':before,'elapsed_seconds':time.monotonic()-started,'report':report,'new_integrand_evaluations':0,'new_mcmc_calls':0,'limitations':'Does not re-evaluate integrands, derivative bounds or tails; these retain their mathematical and component-qualification obligations. Full study checksum and restore verification will follow the complete run.'}
(out/'audit.json').write_text(json.dumps(record,indent=2)+'\n')
(out/'checksums.json').write_text(json.dumps({f.name:audit.sha(f) for f in out.iterdir() if f.is_file() and f.name not in ['checksums.json','stdout.log','stderr.log']},indent=2)+'\n')
print(json.dumps({'completed_method_verified':True,'full_study_verified':False,'functions_meeting_targets':report['functions_meeting_targets'],'coverage':report['coverage'],'unchanged_source_files':len(before),'elapsed_seconds':record['elapsed_seconds']}),flush=True)
