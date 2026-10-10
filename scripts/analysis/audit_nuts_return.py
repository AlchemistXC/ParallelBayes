#!/usr/bin/env python3
"""Read-only archive and identity audit for the S2 native Windows return.

This standard-library receiver never imports returned source or invokes a
sampler, R, Windows recovery, or an operating-system process query. Passing it
means that archived identities agree, not that a remote process is live/dead,
qualification trajectories agree, or a reported root cause is proved.
"""
import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import re
import shutil
import sqlite3
import tarfile
from urllib.parse import quote
import xml.etree.ElementTree as ET

INPUT_SHA = 'd92824d78f352295449d80556368fd9ee3bed1e9b7af2d0443c3ffb7bfbc7504'
IDENTITY = 'windows-nuts-localization-v1'
MODELS = ('G1', 'L1', 'L2', 'H1', 'H2', 'M1', 'G2', 'A1', 'W1')
CONDITIONS = {(1, True), (1, False), (4, True), (4, False)}
CAPS = {'diagnostic': 9, 'qualification': 12, 'main': 36, 'confirmation': 8}
PAIR_ORDER = [[[4, True], [4, False]], [[1, True], [1, False]],
              [[1, True], [4, True]], [[1, False], [4, False]]]
MAX_BYTES = 20 * 1024**3


def need(value, message):
    if not value:
        raise ValueError(message)


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        need(key not in result, 'Duplicate JSON key: ' + key)
        result[key] = value
    return result


def parse(text):
    def invalid(value):
        raise ValueError('Nonfinite JSON number: ' + value)
    return json.loads(text, object_pairs_hook=unique_pairs, parse_constant=invalid)


def read(path):
    return parse(Path(path).read_text(encoding='utf-8'))


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     allow_nan=False).encode()).hexdigest()


def relative(name, legacy=False):
    need(isinstance(name, str), 'Non-string member name')
    canonical = name.replace('\\', '/') if legacy else name
    need('\\' not in canonical and ':' not in canonical and '\x00' not in canonical,
         'Unsafe relative path: ' + name)
    need(all(part not in ('', '.', '..') for part in canonical.split('/')),
         'Unsafe relative path: ' + name)
    return canonical


def normalized(mapping, legacy=False):
    result = {}
    folded = set()
    for name, value in mapping.items():
        key = relative(name, legacy)
        need(key.casefold() not in folded, 'Duplicate portable path: ' + key)
        folded.add(key.casefold())
        result[key] = value
    return result


def check_hashes(root, values, exact=False, exclude=()):
    values = normalized(values, legacy=True)
    if exact:
        files = {p.relative_to(root).as_posix() for p in root.rglob('*')
                 if p.is_file() and p.relative_to(root).as_posix() not in exclude}
        need(files == set(values), 'Integrity member set differs: ' + str(root))
    for name, digest in values.items():
        path = root / name
        need(path.is_file() and not path.is_symlink() and
             path.resolve().is_relative_to(root.resolve()), 'Missing/unsafe member: ' + name)
        need(sha(path) == digest, 'Member checksum differs: ' + name)
    return len(values)


def unpack(archive, output, expected_sha256):
    """Validate an externally supplied digest before inspecting or extracting."""
    need(re.fullmatch('[0-9a-f]{64}', expected_sha256) is not None, 'Expected SHA256 required')
    need(sha(archive) == expected_sha256, 'Return archive SHA256 differs')
    need(not output.exists(), 'Use a new extraction directory')
    with tarfile.open(archive, 'r:') as tar:
        members = tar.getmembers()
        need(len(members) <= 200000, 'Archive member limit exceeded')
        names = [relative(m.name) for m in members]
        need(len(names) == len(set(n.casefold() for n in names)), 'Duplicate archive member')
        need(all(m.isfile() for m in members), 'Only regular archive files are accepted')
        need(names.count('MANIFEST.json') == 1, 'Archive manifest absent')
        manifest_member = tar.getmember('MANIFEST.json')
        need(manifest_member.size <= 64 * 1024**2, 'Archive manifest too large')
        manifest = normalized(parse(tar.extractfile(manifest_member).read().decode('utf-8')))
        need(set(names) == set(manifest) | {'MANIFEST.json'}, 'Archive member set differs')
        total = sum(m.size for m in members)
        need(total + archive.stat().st_size <= MAX_BYTES, 'Archive plus extracted copy exceeds 20 GiB')
        for name in manifest:
            need(name.split('/')[0] in ('study', 'analysis', 'source'), 'Unexpected archive root')
        for member in members:
            if member.name == 'MANIFEST.json':
                continue
            entry = manifest[member.name]
            need(member.size == entry['size'], 'Archive member size differs: ' + member.name)
            with tar.extractfile(member) as stream:
                need(hashlib.file_digest(stream, 'sha256').hexdigest() == entry['sha256'],
                     'Archive member checksum differs: ' + member.name)
        parent = output.parent
        while not parent.exists():
            parent = parent.parent
        need(shutil.disk_usage(parent).free >= total + 4 * 1024**3,
             'Insufficient free space for extraction and 4 GiB reserve')
        output.mkdir(parents=True)
        for member in members:
            target = output / member.name
            target.parent.mkdir(parents=True, exist_ok=True)
            with tar.extractfile(member) as source, target.open('xb') as destination:
                shutil.copyfileobj(source, destination, 1024**2)
    result = verify_tree(output)
    result.update(archive_sha256=expected_sha256, archive_bytes=archive.stat().st_size)
    return result


def verify_tree(root):
    need(not any(p.is_symlink() for p in root.rglob('*')), 'Archive tree contains a symlink')
    manifest = normalized(read(root / 'MANIFEST.json'))
    need({p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}
         == set(manifest) | {'MANIFEST.json'}, 'Extracted archive member set differs')
    for name, entry in manifest.items():
        p = root / name
        need(p.stat().st_size == entry['size'] and sha(p) == entry['sha256'],
             'Extracted member differs: ' + name)
    return dict(verified_members=len(manifest), manifest_sha256=sha(root / 'MANIFEST.json'),
                extracted_bytes=sum(entry['size'] for entry in manifest.values()), new_sampler_calls=0)


def audit(root):
    tree = verify_tree(root)
    study_root = root / 'study'
    study = read(study_root / 'STUDY.json')
    need(study['identity'] == IDENTITY and study['posterior_samples_eligible'] is False,
         'Study scope differs')
    need(study['maximum_registered_calls'] == 48 and study['maximum_qualification_rounds'] == 3,
         'Study quota differs')
    need(study['input_manifest_sha256'] == INPUT_SHA == sha(study_root / 'inputs/checksums.json'),
         'Fixed input selection differs')
    check_hashes(study_root / 'inputs', read(study_root / 'inputs/checksums.json'))
    check_hashes(study_root, read(study_root / 'prepared-checksums.json'))
    original = read(study_root / 'inputs/G1-case.json')['source_capsule']
    need(study['required_versions'] == original['required_versions'] and
         study['required_R_version'] == original['required_R_version'] and
         study['required_R_posterior'] == original['required_R_posterior'], 'Original environment requirement differs')
    need(study['working_limit_bytes'] == 6 * 1024**3 and
         study['per_host_incremental_limit_bytes'] == MAX_BYTES, 'Study storage protection differs')
    for model in MODELS:
        saved = read(study_root / 'prepared-cases' / (model + '.json'))
        case = read(study_root / 'inputs' / (model + '-case.json'))
        need({k:v for k,v in saved.items() if k != 'names'} == case, 'Prepared target changed from fixed input')
        need(read(study_root / 'rng' / (model + '.json'))['seeds'] == case['chain_seeds'],
             'Prepared RNG seed provenance differs')
    database = study_root / 'calls.sqlite'
    before = sha(database)
    db = sqlite3.connect('file:' + quote(str(database.resolve()), safe='/') + '?mode=ro', uri=True)
    try:
        need(db.execute('PRAGMA quick_check').fetchall() == [('ok',)], 'Registry integrity failed')
        identities = db.execute('SELECT value FROM identity').fetchall()
        need(len(identities) == 1 and parse(identities[0][0]) == study, 'Registry study identity differs')
        rows = db.execute('SELECT id,phase,request,request_sha,registered_ns,outcome FROM calls ORDER BY registered_ns,id').fetchall()
    finally:
        db.close()
    records = [dict(id=i, phase=p, request=parse(r), digest=s, registered_ns=t,
                    outcome=parse(o) if o is not None else None) for i,p,r,s,t,o in rows]
    counts = Counter(r['phase'] for r in records)
    need(set(counts) <= set(CAPS), 'Unknown registry phase')
    need(all(counts[p] <= cap for p, cap in CAPS.items()) and
         len(records) - counts['diagnostic'] <= 48, 'Technical call quota exceeded')
    need({p.name for p in (study_root / 'calls').iterdir()} == {r['id'] for r in records},
         'Call directory/registry set differs')
    bindings = {}
    for path in (study_root / 'bindings').glob('*.json'):
        binding = read(path)
        key = binding['binding_sha256']
        need(path.stem == key == fingerprint(binding['identity']), 'Source/environment binding differs')
        need(re.fullmatch('[0-9a-f]{40}', binding['source_commit']) is not None, 'Invalid source commit')
        check_hashes(root / 'source' / key, binding['identity']['source_files'])
        env = binding['identity']
        need(env['system'] == 'Windows' and env['python'].startswith('3.12.') and
             all(env['versions'].get(k) == v for k,v in original['required_versions'].items()) and
             env['R']['R'] == original['required_R_version'] and
             env['R']['posterior'] == original['required_R_posterior'], 'Bound native environment differs')
        baseline_names = [name for name in original['source_files'] if name.startswith('r-package/inst/python/parallelbayes/')
                          or name in ('scripts/completion/inference_nuts.py', 'scripts/completion/inference_parallel_nuts.py',
                                      'examples/affine_target.py', 'examples/external_wells.py')]
        bound_files = normalized(env['source_files'], legacy=True)
        need(all(bound_files.get(name) == original['source_files'][name] for name in baseline_names),
             'Frozen baseline source changed')
        bindings[key] = binding
    used = set()
    for record in records:
        request, outcome = record['request'], record['outcome']
        need(request['id'] == record['id'] and request['phase'] == record['phase'] and
             fingerprint(request) == record['digest'], 'Registry request fingerprint differs')
        relative(record['id'])
        need('/' not in record['id'], 'Unsafe call identity')
        need(request['posterior_samples_eligible'] is False, 'Technical call promoted to posterior samples')
        binding = bindings[request['binding_sha256']]
        need(request['source_commit'] == binding['source_commit'], 'Call source commit differs')
        used.add(request['binding_sha256'])
        directory = study_root / 'calls' / record['id']
        need(outcome is not None, 'Registered call lacks a terminal record; recover on Windows')
        need(outcome.get('managed_active_processes') == 0 and outcome.get('kernel_terminal_verified') is True
             and outcome.get('posterior_samples_eligible') is False, 'Terminal evidence fields incomplete')
        need(read(directory / 'request.json') == request, 'Saved request differs from registry')
        need(sha(directory / 'checksums.json') == outcome['checksums_sha256'], 'Call manifest binding differs')
        check_hashes(directory, read(directory / 'checksums.json'), exact=True, exclude=('checksums.json',))
        need(read(directory / 'finished.json') == {k:v for k,v in outcome.items() if k != 'checksums_sha256'},
             'Saved outcome differs from registry')
        model = request['model']
        if record['phase'] == 'diagnostic':
            need(model in ('G1','G2','W1') and (request['diagnostic_kind'],request['workers']) in
                 (('legacy',1),('legacy',4),('modern',1)), 'Unexpected diagnostic condition')
            need(request['diagnostic_input_sha256'] == sha(study_root / 'inputs' / (model + '-diagnostic.npz')),
                 'Diagnostic input differs')
            continue
        need((request['workers'], request['diagnostics_enabled']) in CONDITIONS, 'Unexpected sampling condition')
        case = read(study_root / 'prepared-cases' / (model + '.json'))
        need(request['case'] == case and request['rng_sha256'] == sha(study_root / 'rng' / (model + '.json')),
             'Prepared target/initial state/RNG binding differs')
        expected = dict(draws=64 if record['phase']=='qualification' else 4096,
                        warmup=64 if record['phase']=='qualification' else 1024,
                        max_tree_depth=8,target_accept_prob=.8,full_mass=False,memory_limit_mb=2048)
        need(request['config'] == expected, 'Sampling controls differ from finite plan')
        need(model == 'Q2' if record['phase']=='qualification' else model in MODELS, 'Unexpected target identity')
        states = read(study_root / 'rng' / (model + '.json'))['states']
        need(len(states) == len(case['initial']) == 4, 'Four-chain input required')
        for chain in range(4):
            initial = directory / f'chain-{chain}/initial-rng.json'
            if initial.exists():
                need(read(initial) == states[chain], 'Actual initial RNG state differs')
    for key in used:
        gate = study_root / 'native-checks' / key
        check_hashes(gate, read(gate / 'checksums.json'), exact=True, exclude=('checksums.json',))
        result = read(gate / 'result.json')
        cases = ET.parse(gate / 'tests.xml').findall('.//testcase')
        need(result['binding_sha256'] == key and result['passed'] is True and result['exit_code']==0 and
             len(cases)==result['tests']==3 and result['failed']==result['skipped']==0 and
             all(c.find('failure') is None and c.find('error') is None and c.find('skipped') is None for c in cases),
             'Native Job gate evidence differs')
    qualifications = [r for r in records if r['phase']=='qualification']
    rounds = sorted({r['request']['round'] for r in qualifications})
    need(not rounds or rounds == list(range(max(rounds)+1)) and max(rounds)<3, 'Qualification rounds differ')
    for round_id in rounds:
        group = [r for r in qualifications if r['request']['round']==round_id]
        need(len(group)<=4 and len({r['request']['binding_sha256'] for r in group})==1 and
             len({(r['request']['workers'],r['request']['diagnostics_enabled']) for r in group})==len(group),
             'Qualification conditions/bindings differ')
    diagnostic_conditions = [(r['request']['model'], r['request']['diagnostic_kind'], r['request']['workers'])
                             for r in records if r['phase']=='diagnostic']
    need(len(diagnostic_conditions) == len(set(diagnostic_conditions)), 'Duplicate diagnostic condition')
    if qualifications:
        need(counts['diagnostic']==9, 'Qualification preceded the nine diagnostic jobs')
    protocol = None
    if (study_root / 'protocol.json').exists():
        protocol = read(study_root / 'protocol.json')
        need(read(study_root / 'protocol.sha256.json')['sha256']==sha(study_root / 'protocol.json'),
             'Frozen protocol checksum differs')
        need(protocol['identity']==IDENTITY and protocol['study_sha256']==sha(study_root / 'STUDY.json') and
             protocol['prepared_sha256']==sha(study_root / 'prepared-checksums.json'), 'Frozen study/input binding differs')
        need(protocol['maximum_registered_calls']==48 and protocol['main_calls']==36 and
             protocol['qualification_registered']==len(qualifications) and
             protocol['maximum_confirmation_calls']==min(8,48-len(qualifications)-36), 'Frozen quota differs')
        need(protocol['posterior_samples_eligible'] is False and protocol['require_same_initial_actual_rng_states'] is True,
             'Frozen scientific scope differs')
        need(protocol['schedule']==read(study_root / 'schedule.json') and len(protocol['schedule'])==36 and
             {(r['model'],r['workers'],r['diagnostics_enabled']) for r in protocol['schedule']}
             == {(m,w,d) for m in MODELS for w,d in CONDITIONS}, 'Frozen main schedule differs')
        qualified = [r for r in qualifications if r['id'] in protocol['qualification_ids']]
        need(len(set(protocol['qualification_ids']))==len(qualified)==4 and
             all(r['outcome']['status']=='completed' and r['request']['binding_sha256']==protocol['binding_sha256']
                 for r in qualified), 'Frozen four-condition qualification records differ')
        need(protocol['source_commit']==bindings[protocol['binding_sha256']]['source_commit'] and
             protocol['confirmation_model_order']==list(MODELS) and protocol['confirmation_pair_order']==PAIR_ORDER,
             'Frozen source/confirmation rules differ')
    scientific = [r for r in records if r['phase'] in ('main','confirmation')]
    need(not scientific or protocol is not None, 'Main/confirmation calls lack a frozen protocol')
    if protocol:
        schedule = {item['id']:item for item in protocol['schedule']}
        for record in scientific:
            request = record['request']
            need(request['binding_sha256']==protocol['binding_sha256'] and
                 record['registered_ns']>max(r['registered_ns'] for r in qualified), 'Main source or qualification order differs')
            if record['phase']=='main':
                need(request['id'] in schedule and all(request[k]==v for k,v in schedule[request['id']].items()),
                     'Main call not in frozen schedule')
        if counts['confirmation']:
            need(counts['main']==36 and counts['confirmation']<=protocol['maximum_confirmation_calls'],
                 'Confirmation calls exceed eligible quota')
            selected = read(study_root / 'confirmation-selection.json')
            allowed = {item['id']:item for item in selected}
            need(len(allowed)==len(selected)<=protocol['maximum_confirmation_calls'], 'Confirmation selection differs')
            for record in scientific:
                if record['phase']=='confirmation':
                    need(record['id'] in allowed and all(record['request'][k]==v for k,v in allowed[record['id']].items()),
                         'Confirmation call not in saved selection')
    analysis = root / 'analysis'
    check_hashes(analysis, read(analysis / 'checksums.json'), exact=True, exclude=('checksums.json',))
    summary = read(analysis / 'SUMMARY.json')
    expected_summary = dict(calls=len(records),new_registered_four_chain_calls=len(records)-counts['diagnostic'],
                            diagnostic_jobs=counts['diagnostic'],main_registered=counts['main'],
                            main_completed=sum(r['phase']=='main' and r['outcome']['status']=='completed' for r in records),
                            registry_sha256=before,new_sampler_calls_by_analysis=0,
                            historical_failures_reclassified=0,posterior_samples_added=0,
                            protocol_sha256=sha(study_root / 'protocol.json') if protocol else None)
    need(all(summary[k]==v for k,v in expected_summary.items()), 'Returned analysis/registry identity differs')
    if records:
        with (analysis / 'calls.csv').open(encoding='utf-8', newline='') as f:
            calls = list(csv.DictReader(f))
        need(len(calls)==len(records) and {r['id'] for r in calls}=={r['id'] for r in records}, 'Analysis call denominator differs')
        by_id = {r['id']:r for r in records}
        need(all(r['phase']==by_id[r['id']]['phase'] and r['status']==by_id[r['id']]['outcome']['status'] for r in calls),
             'Analysis dropped/relabeled a call')
    need(sha(database)==before, 'Read-only audit changed the registry')
    return dict(identity='windows-nuts-return-identity-audit-v1',identity_audit_passed=True,**tree,
                calls=len(records),phase_counts=dict(counts),registry_sha256=before,
                bound_source_versions=len(bindings),used_source_versions=len(used),
                all_main_calls_registered=counts['main']==36,protocol_present=protocol is not None,
                native_trajectory_qualification_recomputed=False,git_commit_objects_verified=False,
                remote_live_process_state_verified=False,requires_portable_analysis_reconstruction=True,
                historical_failures_reclassified=0,posterior_samples_added=0,
                scope='Archived integrity and identity consistency only; failed or incomplete studies remain admissible evidence')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest='command',required=True)
    u=sub.add_parser('unpack');u.add_argument('--archive',type=Path,required=True);u.add_argument('--sha256',required=True);u.add_argument('--output',type=Path,required=True)
    a=sub.add_parser('audit');a.add_argument('--root',type=Path,required=True);a.add_argument('--report',type=Path,required=True)
    args=p.parse_args()
    if args.command=='unpack':
        result=unpack(args.archive,args.output,args.sha256)
    else:
        need(not args.report.exists() and not args.report.resolve().is_relative_to(args.root.resolve()),
             'Use a new report outside the received archive tree')
        result=audit(args.root)
        args.report.parent.mkdir(parents=True,exist_ok=True)
        args.report.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False))


if __name__=='__main__':
    main()
