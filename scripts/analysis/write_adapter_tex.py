"""Render one reviewed finite native-v2 receipt into bounded manuscript prose.

Pinned derivative records are supported by a separately archived raw intake.
This is not a raw oracle, a sampler, or a generic formal-results generator.
"""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path

INPUTS = {'benchmark/analysis/outputs/windows-formal-v2-intake-v1/receiver-summary.json': '9b9341f765e1c43252db0a6cf6289b95bd90de21d8d49dc1d6bb5c09d95600e8', 'benchmark/analysis/outputs/windows-formal-v2-intake-v1/analysis-resume-summary.json': '2bf882cae2e3710549ad21588fe8a22292cc3b63ef85ef038b56139d48ce4ca5', 'benchmark/analysis/outputs/windows-formal-v2-intake-v1/source-design-bridge.json': '04c47765f64c30796f278a574650f320dd86c0dbdd27afb9f77ec6f3e04bb65a', 'benchmark/analysis/outputs/windows-formal-v2-intake-v1/G1/diagnostics.csv': 'd7a22eee1795d966e663ae3f3399f43a17c27b737717df95cdf56f2c734a258a', 'benchmark/analysis/outputs/windows-formal-v2-intake-v1/G2/diagnostics.csv': 'd8902be4286adc9386a8314431846c424602e60f0d82893ed02a0800eb00826d', 'benchmark/analysis/outputs/windows-formal-v2-intake-v1/W1/diagnostics.csv': '97d5222a0f5188bb17327e3e6d7bd1895dd8b17af2e3b89686132e23f3eba9f9', 'manuscript/software/adapter.template.tex': 'af07ce8044628c2bb8e4521732cd8248eea3b79f129f90c70fafadcfb2066cbc'}
PREFIX = 'benchmark/analysis/outputs/windows-formal-v2-intake-v1/'


def render(root):
    data = {}
    for name, expected in INPUTS.items():
        path = Path(root) / name
        if path.is_symlink() or not path.is_file():
            raise ValueError('Missing/nonregular reviewed input: '+name)
        content = path.read_bytes()
        if hashlib.sha256(content).hexdigest() != expected:
            raise ValueError('Changed reviewed input: '+name)
        data[name] = content
    receiver = json.loads(data[PREFIX+'receiver-summary.json'])
    resume = json.loads(data[PREFIX+'analysis-resume-summary.json'])
    bridge = json.loads(data[PREFIX+'source-design-bridge.json'])
    frame = resume['frame']
    if (frame['identity'] != 'windows-formal-adapter-validation-v1' or
            frame['scope'] != 'technical_batch_validation' or
            frame['formal_scientific_repetitions_per_model'] != 0 or
            not resume['evidence_complete'] or resume['new_analyses'] != 0 or
            resume['reused_analyses'] != receiver['main']+receiver['cache']):
        raise ValueError('Finite identity, evidence frame or zero-reanalysis resume differs')
    if (receiver['main_outcomes'] != {'valid':receiver['main']} or
            not receiver['all_raw_reader_completed'] or
            receiver['MH_acceptance_mismatches'] != 0 or
            receiver['cache_acceptance_mismatches'] != 0 or
            not receiver['cache_all_samples_ineligible'] or
            receiver['formal_scientific_repetitions'] != 0 or
            receiver['new_MCMC_calls'] != 0):
        raise ValueError('Receiver numerical/eligibility contract differs')
    if (bridge['accepted_execution_commit'] != '0ba5643a6b580e79b8040f13a5e3165322db0e77' or
            bridge['changed_accepted_files'] or bridge['formal_inputs_generated'] or
            bridge['formal_protocol_frozen'] or bridge['new_sampler_calls']):
        raise ValueError('Source compatibility is not formal study completion')
    diagnostics=[]
    for model in ('G1','G2','W1'):
        records=list(csv.DictReader(io.StringIO(data[PREFIX+model+'/diagnostics.csv'].decode())))
        if any(int(r['planned']) != 1 or int(r['missing']) != 0 for r in records):
            raise ValueError('One technical input per model; no missing diagnostics allowed in this edition')
        diagnostics.extend(records)
    comparisons = {
        'diagnostic_rows':sum(int(r['received']) for r in diagnostics),
        'rhat_above_1_01':sum(int(r['rhat_above_1_01']) for r in diagnostics),
    }
    if any(receiver[k] != value for k,value in comparisons.items()):
        raise ValueError('Diagnostic source rows and receiver summary differ')
    for field in ('rhat','ess_bulk','ess_tail','mcse_mean'):
        if sum(int(r[field+'_undefined']) for r in diagnostics) != receiver['undefined'][field]:
            raise ValueError('Undefined diagnostic count differs: '+field)
    values=dict(MAIN=receiver['main'],CACHE=receiver['cache'],CALLS=receiver['cache_calls'],
        MH=receiver['MH_replays'],MISMATCH=receiver['MH_acceptance_mismatches'],
        DIAG=receiver['diagnostic_rows'],REUSED=resume['reused_analyses'],BAD=receiver['rhat_above_1_01'],
        NULL=receiver['undefined']['rhat'],TAIL=receiver['undefined']['ess_tail'])
    template=data['manuscript/software/adapter.template.tex'].decode()
    for key,value in values.items():template=template.replace('@@'+key+'@@',str(value))
    if '@@' in template:raise ValueError('Unfilled manuscript placeholder')
    provenance=''.join(f'% Reviewed input SHA256 {value} {name}\n' for name,value in INPUTS.items())
    report=dict(scope='Reviewed finite native-v2 intake records to manuscript; not formal scientific results',
        source_inputs=INPUTS,values=values,formal_independent_repetitions_added=0,
        sampler_calls=0,R_diagnostic_calls=0,figures_regenerated=False,
        raw_replay_performed_by_prior_intake=True,raw_arrays_replayed_this_step=False)
    return provenance+template,report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[2])
    p.add_argument('--output',type=Path,required=True);p.add_argument('--report',type=Path)
    args=p.parse_args();outputs=[args.output]+([args.report] if args.report else [])
    if len({p.resolve() for p in outputs}) != len(outputs):raise ValueError('Distinct output paths required')
    if any(p.exists() for p in outputs):raise FileExistsError('Existing reviewed output is retained')
    text,report=render(args.root)
    for path in outputs:path.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(text,encoding='utf-8')
    if args.report:args.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(status='passed',finite_main_tasks=report['values']['MAIN'],sampler_calls=0)))


if __name__=='__main__':main()
