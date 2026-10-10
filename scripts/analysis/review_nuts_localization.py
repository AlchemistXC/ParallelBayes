#!/usr/bin/env python3
"""Independent read-only review after the S2 archive identity audit.

Uses trusted local evidence readers; never imports the returned source, starts
sampling, queries Windows, or rewrites a frozen record. The caller provides the
received tree, the separately rebuilt analysis, and a new output directory.
"""
import argparse
from collections import Counter
import hashlib
import itertools
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
from urllib.parse import quote
import xml.etree.ElementTree as ET

import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / 'scripts/followups'))
from nuts_evidence import failure_stage, paired_prefixes, phase_path, read_events


def need(value, message):
    if not value:
        raise ValueError(message)


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def sha(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def review(root, rebuilt, r_rebuilt, output):
    need(not output.exists(), 'Use a new review directory')
    study = root / 'study'
    registry = study / 'calls.sqlite'
    registry_sha = sha(registry)
    db = sqlite3.connect('file:' + quote(str(registry.resolve()), safe='/') + '?mode=ro', uri=True)
    try:
        records = [dict(id=i, phase=p, request=json.loads(r), registered_ns=t,
                        outcome=json.loads(o)) for i,p,r,s,t,o in
                   db.execute('SELECT * FROM calls ORDER BY registered_ns,id')]
    finally:
        db.close()
    by_id = {r['id']: r for r in records}
    need(len(records)==53 and sum(r['phase']!='diagnostic' for r in records)==44,
         'Finite denominator differs')
    selected_failures = [r for r in records if r['phase']=='main' and
                         r['request']['case']['original_outcome']=='output_failure_unclassified']
    need(len(selected_failures)==24 and len({r['request']['model'] for r in selected_failures})==6,
         'Historical failure-case selection differs')
    not_reproduced = all(r['outcome']['status']=='completed' for r in selected_failures)
    protocol = read(study / 'protocol.json')
    counts = {}
    for phase in ['diagnostic', 'qualification', 'main', 'confirmation']:
        counts[phase] = dict(Counter(r['outcome']['status'] for r in records if r['phase'] == phase))

    # Git object bytes are a different check from archive-to-binding integrity.
    source_rows = []
    for p in sorted((study / 'bindings').glob('*.json')):
        binding = read(p)
        commit = binding['source_commit']
        subprocess.run(['git', 'cat-file', '-e', commit + '^{commit}'], cwd=REPO, check=True)
        for name, expected in binding['identity']['source_files'].items():
            need('\\' not in name and ':' not in name and '..' not in Path(name).parts,
                 'Nonportable source name')
            blob = subprocess.run(['git', 'show', commit + ':' + name], cwd=REPO,
                                  check=True, capture_output=True).stdout
            digest = hashlib.sha256(blob).hexdigest()
            need(digest == expected == sha(root / 'source' / p.stem / name), 'Git source differs: ' + name)
            source_rows.append(dict(binding=p.stem, commit=commit, path=name, sha256=digest))

    # Scientific files must agree in bytes; prose line-ending drift is explicit.
    differences = []
    expected_names = {p.name for p in (root / 'analysis').iterdir() if p.is_file()}
    need(expected_names == {p.name for p in rebuilt.iterdir() if p.is_file()}, 'Analysis member set differs')
    for name in sorted(expected_names):
        old, new = root / 'analysis' / name, rebuilt / name
        a, b = old.read_bytes(), new.read_bytes()
        kind = 'byte_identical' if a == b else 'difference'
        if name == 'README.md' and a.replace(b'\r\n', b'\n') == b:
            kind = 'CRLF_to_LF_only'
        if name == 'checksums.json' and a != b:
            aa, bb = read(old), read(new)
            need(set(aa) == set(bb) and [k for k in aa if aa[k] != bb[k]] == ['README.md'],
                 'Unexpected manifest content difference')
            kind = 'README_checksum_only'
        need(kind != 'difference', 'Unexplained analysis difference: ' + name)
        differences.append(dict(file=name, comparison=kind, windows_sha256=sha(old), mac_sha256=sha(new)))
    qualification = read(rebuilt / 'qualification-reconstruction.json')
    need(len(qualification) == 1 and qualification[0]['passed'], 'Actual qualification did not pass')

    # Recompute the schedule and confirmation eligibility from the full main set.
    main = [r for r in records if r['phase'] == 'main']
    need([r['id'] for r in main] == [r['id'] for r in protocol['schedule']], 'Actual schedule differs')
    chosen = []
    def signature(record):
        if record['outcome']['status'] == 'completed':
            return ['completed']
        return [record['outcome']['status']] + [x['observed_stage'] for x in
                 failure_stage(study / 'calls' / record['id'])]
    for model in protocol['confirmation_model_order']:
        if len(chosen) >= protocol['maximum_confirmation_calls']:
            break
        for pair in protocol['confirmation_pair_order']:
            ids = [f'main-{model}-w{w}-d{int(d)}' for w,d in pair]
            if signature(by_id[ids[0]]) != signature(by_id[ids[1]]):
                for old_id, (workers, enabled) in zip(ids, pair):
                    chosen.append(dict(id=f'confirmation-{model}-w{workers}-d{int(enabled)}',
                                       phase='confirmation', model=model, workers=workers,
                                       diagnostics_enabled=enabled, confirms=old_id))
                break
    need(chosen == read(study / 'confirmation-selection.json'), 'Confirmation rule not followed')
    need({r['id'] for r in records if r['phase'] == 'confirmation'} == {r['id'] for r in chosen},
         'Registered confirmations differ from eligible selection')
    confirmation_pairs = [dict(id=x['id'], confirms=x['confirms'], rows=paired_prefixes(
                           study / 'calls' / x['id'], study / 'calls' / x['confirms'])) for x in chosen]
    need(all(row['exact_match'] is True for pair in confirmation_pairs for row in pair['rows']),
         'Confirmation path/RNG differs')
    main_pairs = read(rebuilt / 'paired-prefixes.json')
    need(len(main_pairs) == 54 and all(x['exact_match'] is True for pair in main_pairs for x in pair['rows']),
         'Main common path/RNG evidence missing or different')

    resources = read(rebuilt / 'resources.json')
    failed = []
    for record in records:
        directory = study / 'calls' / record['id']
        need(record['outcome']['final_job']['hard_job_commit_limit_bytes'] == 12 * 1024**3,
             'Native Job cap changed')
        if record['outcome']['status'] == 'completed':
            continue
        detail = dict(id=record['id'], phase=record['phase'], error=record['outcome']['error'],
                      resources=resources[record['id']], chains=[])
        if record['phase'] != 'diagnostic':
            for chain in range(4):
                folder = directory / f'chain-{chain}'
                warm, sample = phase_path(folder, 'warmup'), phase_path(folder, 'sample')
                need(warm is not None and sample is not None and len(warm)==1024 and len(sample)==4096,
                     'Failed sampling call lacks complete durable path')
                saved = np.load(folder / 'samples-before-diagnostics.npy', allow_pickle=False)
                need(np.array_equal(saved, sample), 'Final saved sample differs from hook chunks')
                events, truncated = read_events(folder / 'events.ndjson')
                names = [e['event'] for e in events]
                required = ['warmup_completed','sample_completed','mcmc_run_returned',
                            'samples_persisted_before_diagnostics','legacy_diagnostics_enter']
                indices = [names.index(x) for x in required]
                need(indices == sorted(indices) and not truncated and
                     'legacy_diagnostics_exit' not in names, 'Failure stage differs')
                detail['chains'].append(dict(chain=chain, warmup=len(warm), sample=len(sample),
                                            final_sample_matches_chunks=True, last_event=names[-1]))
            need(resources[record['id']]['memory_limit_messages'], 'No direct Job memory evidence')
        else:
            need(record['id'] == 'diagnostic-G2-legacy-w4' and
                 record['outcome']['error']['message'] == 'Owned process RSS guard exceeded',
                 'Unexpected saved-array diagnostic failure')
            for chain in range(4):
                events, truncated = read_events(directory / f'chain-{chain}/parent-events.ndjson')
                names = [e['event'] for e in events]
                need('legacy_ess_enter' in names and 'legacy_ess_exit' not in names,
                     'ESS failure interval differs')
                detail['chains'].append(dict(chain=chain, last_event=names[-1], truncated=truncated))
        failed.append(detail)
    need(len(failed) == 5, 'Unexpected failure denominator')

    # Inspect frozen dependency text, not the currently installed Pyro version.
    pyro = study / 'administrative/dependency-sources/pyro-1.9.2-stats.py'
    text = pyro.read_text()
    need(sha(pyro) == 'eedfd0787cbfc7f39765b3d93e4e7808914f3112b7b04a17ec01026606a16df1',
         'Frozen Pyro source differs')
    need('input.unsqueeze(0).repeat((N,) + (1,) * input.dim())' in text and
         'triu_mask.expand((N, N) + input.shape[1:]) > 0.5' in text and
         'Rho_positive = Rho_k[1:].clamp(min=0)' in text, 'ESS allocation construction differs')
    positive = 4096 // 2 - 1
    allocation = dict(positive_pair_count=positive, dimension=64,
                      repeat_float64_bytes=positive**2 * 64 * 8,
                      expanded_boolean_bytes=positive**2 * 64,
                      measured_specific_allocator_peak=False, pyro_source_sha256=sha(pyro))

    terminal_root = study / 'administrative/terminal-verification'
    snapshots = [read(terminal_root / n) for n in ['study-before.json','study-after-1.json','study-after-2.json']]
    need(snapshots[0] == snapshots[1] == snapshots[2] and len(snapshots[0]) == 29444,
         'Terminal snapshots changed')
    for name, entry in snapshots[0].items():
        p = study / name
        need(p.is_file() and p.stat().st_size == entry['bytes'] and sha(p) == entry['sha256'],
             'Terminal preserved file differs: ' + name)
    for n in [1,2]:
        f = terminal_root / f'command-{n}'
        result = read(f / 'finished.json')
        need(result['exit_code'] == 0, 'Native terminal verify command failed')
        saved = json.loads((f / 'stdout.log').read_text())
        need(saved['new_executions'] == 0 and saved['registered_calls'] == 44 and
             saved['diagnostics'] == 9 and saved['managed_active_processes'] == 0,
             'Native terminal verify evidence differs')
    observed = read(study / 'administrative/observations/nuts-status-10-terminal.json')
    need(not observed['active_calls'] and len(observed['registered_jobs']) == 53 and
         all(r['state'] == 'absent' for r in observed['registered_jobs']), 'Recorded native terminal state differs')

    r_compare = []
    for model in ['G1','G2','W1']:
        olddir = study / 'calls' / f'diagnostic-{model}-modern-w1'
        newdir = r_rebuilt / model
        need(sha(olddir/'draws.bin') == sha(olddir/'draws.bin.roundtrip') ==
             sha(newdir/'draws.bin') == sha(newdir/'draws.bin.roundtrip'), 'R binary transport differs')
        a, b = read(olddir/'posterior.json'), read(newdir/'posterior.json')
        need(a['posterior'] == b['posterior'] == '1.7.0', 'R posterior version differs')
        x, y = a['results'][model], b['results'][model]
        need(len(x) == len(y), 'Modern diagnostic row count differs')
        diff = []; maximum=0.0; classification=0
        for aa,bb in zip(x,y):
            need(set(aa) == set(bb) and aa['variable'] == bb['variable'], 'Modern variable schema differs')
            for k in aa:
                if k == 'variable': continue
                u,v = aa[k],bb[k]
                need((u is None)==(v is None), 'Undefined modern diagnostic differs')
                if u is None: continue
                d = abs(u-v)/max(1,abs(u),abs(v)); maximum=max(maximum,d)
                if u != v: diff.append(dict(variable=aa['variable'],field=k,windows=u,mac=v,scaled_difference=d))
                if k == 'rhat' and (u>1.01)!=(v>1.01): classification+=1
        # Retain every difference; threshold classifications are reported separately.
        need(classification == 0, 'Rhat threshold classification changed; review before paper generation')
        r_compare.append(dict(model=model,variables=len(x),windows_R=a['R'],mac_R=b['R'],
                              numeric_differences=diff,max_scaled_difference=maximum,
                              rhat_threshold_classifications_changed=classification,
                              binary_transport_equal=True))

    tests = {}
    for kind, file, count in [('portable',study/'administrative/portable-tests.xml',21),
                              ('native',study/'native-checks'/protocol['binding_sha256']/'tests.xml',3)]:
        tree = ET.parse(file).getroot()
        cases = tree.findall('.//testcase')
        need(len(cases)==count and not tree.findall('.//failure') and not tree.findall('.//error') and
             not tree.findall('.//skipped'), 'Saved native/portable check result differs')
        tests[kind] = dict(passed=count,failed=0,skipped=0,mac_executed_native_tests=False)
    need(sha(registry)==registry_sha, 'Read-only review changed registry')
    result = dict(identity='nuts-mac-scientific-review-v1',passed=True, phase_counts=counts,
                  registered_four_chain_calls=44, source_files_verified=len(source_rows),
                  source_commit=protocol['source_commit'], protocol_sha256=sha(study/'protocol.json'),
                  registry_sha256=registry_sha, actual_qualification_passed=True,
                  main_pairs=54, main_path_rng_records=864, main_path_rng_mismatches=0,
                  confirmation_selection_recomputed=True, confirmation_path_rng_records=64,
                  confirmation_path_rng_mismatches=0, saved_terminal_files_verified=29444,
                  recorded_native_jobs_absent=53, remote_current_kernel_queried=False,
                  native_verify_new_executions=[0,0], saved_tests=tests,
                  new_sampler_calls=0,historical_failures_reclassified=0,posterior_samples_added=0,
                  six_selected_historical_failures_not_reproduced=not_reproduced,
                  ESS_specific_allocation_identified_from_failure_stack=False,
                  whole_historical_105_root_cause_established=False)
    output.mkdir(parents=True)
    values = {'SUMMARY.json':result,'git-source-verification.json':source_rows,
              'analysis-comparison.json':differences,'confirmation-selection.json':chosen,
              'confirmation-prefixes.json':confirmation_pairs,'failed-call-review.json':failed,
              'ESS-static-allocation.json':allocation,'modern-R-comparison.json':r_compare}
    for name,value in values.items():
        (output/name).write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    (output/'checksums.json').write_text(json.dumps({n:sha(output/n) for n in values},indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False))


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',required=True,type=Path)
    p.add_argument('--rebuilt',required=True,type=Path)
    p.add_argument('--r-rebuilt',required=True,type=Path)
    p.add_argument('--output',required=True,type=Path)
    a=p.parse_args();review(a.root.resolve(),a.rebuilt.resolve(),a.r_rebuilt.resolve(),a.output.resolve())
