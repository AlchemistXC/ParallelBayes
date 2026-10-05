"""Finite read-only compatibility intake of the two archived Mac cache profiles.

No MCMC execution or timing is performed. The initial command creates new
companions; audit reconstructs those companions after an independent relocation.
"""
import argparse,copy,json,shutil,subprocess,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'scripts/completion'),str(ROOT/'r-package/inst/python'),str(ROOT/'examples')]
from formal_runtime import atomic_json,file_hash
from formal_uncertainty import load_plan
from cache_probe_analysis import analyze_cache_probes
from owned_cache_evidence import OwnedCacheEvidence


def collect(root,save=False):
    receipt=json.loads((root/'layout-receipt.json').read_text())
    with OwnedCacheEvidence(root,'owned-cache-layout.json',receipt['sha256']) as reader:
        rows={pid:reader.read_probe(pid) for pid in reader.probe_ids}
        comparisons={};paired_groups=0
        for model in {p['model'] for p in reader.probes.values()}:
            selected={pid:r for pid,r in rows.items() if r['probe']['model']==model}
            old=root/'archive/analysis'/model
            if old.is_dir():
                plan=load_plan(old/'resampling')
                report=analyze_cache_probes(reader.allocation,reader.protocol['tasks'],plan,
                    {pid:r['binding'] for pid,r in selected.items()},
                    {pid:r['observation'] for pid,r in selected.items()})
                arrays=report.pop('bootstrap_statistics');prior=json.loads((old/'analysis.json').read_text())
                for name,workflow in report['workflows'].items():
                    compared=dict(workflow);compared.pop('task_outcome_counts')
                    if compared!=prior['workflows'][name]:raise ValueError('Previously completed cache statistics changed')
                if report['pairs']!=prior['pairs']:raise ValueError('Previously completed pair statistics changed')
                with np.load(old/'bootstrap-statistics.npz',allow_pickle=False) as z:
                    if set(z.files)!=set(arrays) or any(not np.array_equal(z[k],arrays[k],equal_nan=True) for k in arrays):
                        raise ValueError('Previously completed bootstrap statistics changed')
                comparisons[model]=report;paired_groups+=len(report['pairs'])
            else:
                prior=json.loads((root/'archive/single-input-summary.json').read_text())
                if len({r['probe']['replicate'] for r in selected.values()})!=1:raise ValueError('Unexpected single-input profile')
                for r in selected.values():
                    if r['cached_seconds']!=prior['workflows'][r['probe']['workflow']]['cached_seconds']:
                        raise ValueError('Single-input descriptive cost changed')
                comparisons[model]=prior
        audits=events=records=0;maximum=0.
        for row in rows.values():
            for call in row['observation']['records']:
                if call is None:continue
                records+=1;audit=call.get('audit')
                if audit:
                    audits+=bool(audit['passed']);events+=sum(audit['acceptance_mismatches'])
                    maximum=max(maximum,max(audit['max_abs_path_error']))
        summary=dict(profile=reader.protocol['identity'],probes=len(rows),measurement_available=sum(r['measurement_available'] for r in rows.values()),
            saved_call_records=records,saved_audits_passed=audits,saved_acceptance_mismatches=events,saved_max_abs_path_error=maximum,
            verified_outer_calls=sum(r['outer_costs']['recorded_invocations'] for r in rows.values()),
            known_executor_seconds=sum(r['numerical_summary']['known_executor_seconds'] for r in rows.values()),
            previous_statistical_comparisons_unchanged=True,paired_groups=paired_groups,new_executor_calls=0,new_independent_audits=0,
            new_independent_repetitions=0,samples_eligible=False,native_windows_validated=False)
    for name,value in [('rows.json',rows),('statistics.json',comparisons),('SUMMARY.json',summary)]:
        path=root/name
        if save:atomic_json(path,value)
        elif json.loads(path.read_text())!=value:raise ValueError('Relocated derived companion differs: '+name)
    return summary


def prepare(source,output):
    source=Path(source).resolve();output=Path(output).resolve()
    inventory=json.loads((source/'MANIFEST.json').read_text())
    if file_hash(source/'registry-snapshot.sqlite3')!=inventory['registry-snapshot.sqlite3']:raise ValueError('Original registry snapshot differs')
    output.mkdir(parents=True,exist_ok=False);summaries={}
    for profile in ('short-v2','maximum-v2'):
        original=source/profile;manifest=json.loads((original/'MANIFEST.json').read_text())
        if file_hash(original/'MANIFEST.json')!=inventory[profile+'/MANIFEST.json']:raise ValueError('Original profile inventory differs')
        for name,h in manifest.items():
            if file_hash(original/name)!=h:raise ValueError('Original profile asset differs')
        root=output/profile;root.mkdir();shutil.copytree(original,root/'archive')
        shutil.copy2(source/'registry-snapshot.sqlite3',root/'registry.sqlite3')
        saved=json.loads(sorted((original/'invocations').glob('*.json'))[-1].read_text())['rows']
        locations={};probes={}
        for row in saved:
            original_name=row['costs']['history']['original']
            locations[original_name]='archive/tasks/'+row['probe_id']
            probes[row['probe_id']]=dict(original=original_name,calls='archive/'+row['relative_calls'])
        layout=dict(schema='owned-cache-evidence-v1',protocol='archive/protocol.json',allocation='archive/allocation.json',
            inputs='archive/inputs',snapshot='registry.sqlite3',snapshot_sha256=file_hash(root/'registry.sqlite3'),locations=locations,probes=probes)
        atomic_json(root/'owned-cache-layout.json',layout)
        atomic_json(root/'layout-receipt.json',dict(sha256=file_hash(root/'owned-cache-layout.json'),analysis_source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
            source_profile_manifest_sha256=file_hash(original/'MANIFEST.json'),scope='Read-only successor companion; original nested archive unmodified'))
        summaries[profile]=collect(root,save=True)
    atomic_json(output/'SUMMARY.json',summaries)
    return summaries


def audit(output):
    output=Path(output);summaries={profile:collect(output/profile) for profile in ('short-v2','maximum-v2')}
    if json.loads((output/'SUMMARY.json').read_text())!=summaries:raise ValueError('Combined receipt differs')
    return summaries


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['prepare','audit']);p.add_argument('--source',type=Path);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();print(json.dumps(prepare(a.source,a.output) if a.action=='prepare' else audit(a.output),indent=2))
