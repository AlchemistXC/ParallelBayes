"""Real-scope candidate inputs must not be sealed with marked mock receipts."""
from hashlib import sha256
from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/prospective_reference'))
from create_freeze import create
from formal_run import reference_scope, verify_freeze
from prepare_inputs import generate
from qualification_inventory import tasks


def write(path,data):
    path.write_text(json.dumps(data)+'\n')


def main():
    with tempfile.TemporaryDirectory(prefix='real-mock-guard-') as temporary:
        root=Path(temporary);inputs=root/'candidate';generate(inputs)
        manifest=json.loads((inputs/'manifest.json').read_text())
        assert reference_scope(manifest)=='formal'
        assert reference_scope({'scope':'SYNTHETIC TEST ONLY'})=='synthetic_test'
        try:reference_scope({'scope':'unclassified'})
        except ValueError:pass
        else:raise AssertionError('unknown data scope accepted')
        write(inputs/'preflight.json',{'scope':'candidate-only preflight',
            'formal_sampling_started':False,'inputs_manifest_sha256':sha256((inputs/'manifest.json').read_bytes()).hexdigest(),
            'data_sha256':manifest['data_sha256'],'initials_sha256':manifest['initials_sha256'],
            'checks':{'logistic':{'passed':True,'rows':[{'chain':i,'finite':True,'density_delta_error':0.,
                                                       'gradient_max_ratio':0.} for i in range(1,11)]}}})
        restart=root/'restart.json'
        write(restart,{'model':'logistic','steps':2000,'position_and_diagnostics_byte_identical':True,
                       'rollback_at_200':True,'wrong_chain_rejected':True,'idempotency':True})
        windows=root/'windows.json';capacity=root/'capacity.json'
        window_data={'identity':'prospective-first-use-v1','status':'passed','planned':880,'accounted':880,
                     'scope':'MOCK TEST ONLY','evidence_kind':'actual'}
        capacity_data={'identity':'prospective-first-use-v1','status':'passed',
                       'scope':'prospective_capacity_budget','evidence_kind':'actual',
                       'resources':{key:{'available':10,'conservative':1} for key in
                                    ('windows_hours','windows_disk','mac_disk','archive')}}
        write(windows,window_data);write(capacity,capacity_data)
        try:create(root/'reject-mock-windows',inputs,'logistic',windows,capacity,restart)
        except ValueError as error:assert 'windows_qualification must be explicitly identified' in str(error)
        else:raise AssertionError('mock Windows evidence accepted')
        assert not (root/'reject-mock-windows/seal.json').exists()
        window_data['scope']='prospective_windows_qualification';del window_data['evidence_kind'];write(windows,window_data)
        try:create(root/'reject-unmarked-windows',inputs,'logistic',windows,capacity,restart)
        except ValueError as error:assert 'windows_qualification must be explicitly identified' in str(error)
        else:raise AssertionError('unmarked Windows evidence accepted')
        assert not (root/'reject-unmarked-windows/seal.json').exists()
        window_data['evidence_kind']='actual';write(windows,window_data)
        capacity_data['scope']='MOCK TEST ONLY';write(capacity,capacity_data)
        try:create(root/'reject-mock-capacity',inputs,'logistic',windows,capacity,restart)
        except ValueError as error:assert 'capacity must be explicitly identified' in str(error)
        else:raise AssertionError('mock capacity evidence accepted')
        assert not (root/'reject-mock-capacity/seal.json').exists()
        capacity_data['scope']='prospective_capacity_budget';write(capacity,capacity_data)
        restart_data=json.loads(restart.read_text());restart_data['scope']='MOCK TEST ONLY';write(restart,restart_data)
        try:create(root/'reject-mock-restart',inputs,'logistic',windows,capacity,restart)
        except ValueError as error:assert 'marked as mock evidence' in str(error)
        else:raise AssertionError('mock restart evidence accepted')
        assert not (root/'reject-mock-restart/seal.json').exists()
        # The following data and external receipts are deliberately fabricated
        # inside a temporary directory solely to exercise structural guards.
        # They are not study evidence and no reference sampling is performed.
        del restart_data['scope'];write(restart,restart_data)
        try:create(root/'reject-missing-audit',inputs,'logistic',windows,capacity,restart)
        except ValueError as error:assert 'candidate audit and fresh preflight are required' in str(error)
        else:raise AssertionError('candidate without audit accepted')
        assert not (root/'reject-missing-audit/seal.json').exists()
        fresh=root/'TEST-ONLY-fresh-preflight.json';fresh.write_bytes((inputs/'preflight.json').read_bytes())
        fake_audit=root/'TEST-ONLY-candidate-audit.json'
        audit={'scope':'candidate audit only; no freeze or posterior sampling','status':'passed',
               'models':['ode'],'manifest_sha256':sha256((inputs/'manifest.json').read_bytes()).hexdigest(),
               'audit_source_sha256':sha256((ROOT/'scripts/prospective_reference/audit_candidate.py').read_bytes()).hexdigest(),
               'data_sha256':manifest['data_sha256'],'initials_sha256':manifest['initials_sha256'],
               'archive_sha256':'a'*64,
               'prior_identity_verified':True,'actual_data_and_archive_bytes_match':True,
               'formal_sampling_started':False,'strata':{'logistic':{'chains':10,'coordinates':130,
                       'candidates_per_chain':4,'distinct_initials':True}},
               'preflights':[{'path':'old','sha256':sha256((inputs/'preflight.json').read_bytes()).hexdigest()},
                             {'path':'fresh','sha256':sha256(fresh.read_bytes()).hexdigest()}]}
        write(fake_audit,audit)
        try:create(root/'reject-wrong-model-audit',inputs,'logistic',windows,capacity,restart,fake_audit,fresh)
        except ValueError as error:assert 'candidate audit identity or coverage differs' in str(error)
        else:raise AssertionError('other-model candidate audit accepted')
        assert not (root/'reject-wrong-model-audit/seal.json').exists()
        audit['models']=['logistic'];write(fake_audit,audit)
        try:create(root/'reject-missing-ledger',inputs,'logistic',windows,capacity,restart,fake_audit,fresh)
        except ValueError as error:assert 'qualification ledger and verified accounting are required' in str(error)
        else:raise AssertionError('missing qualification ledger accepted')
        assert not (root/'reject-missing-ledger/seal.json').exists()
        artifacts=root/'TEST-ONLY-artifacts';artifacts.mkdir();evidence=artifacts/'mock.txt';evidence.write_text('mock evidence only')
        evidence_hash=sha256(evidence.read_bytes()).hexdigest()
        rows=[{'task_id':task['task_id'],'attempt':1,'status':'completed','reason':'',
               'elapsed_seconds':1.,'artifacts':[{'path':'mock.txt','sha256':evidence_hash}]} for task in tasks()]
        rows[0]['status']='failed';rows[0]['reason']='synthetic failure'
        rows.append({**rows[0],'attempt':2,'status':'completed','reason':''})
        ledger=root/'TEST-ONLY-ledger.jsonl'
        def write_ledger(items):ledger.write_text(''.join(json.dumps(row)+'\n' for row in items))
        write_ledger(rows[:-2]);window_data['ledger_sha256']=sha256(ledger.read_bytes()).hexdigest();write(windows,window_data)
        try:create(root/'reject-incomplete-ledger',inputs,'logistic',windows,capacity,restart,fake_audit,fresh,ledger,artifacts)
        except ValueError as error:assert 'qualification accounting incomplete' in str(error)
        else:raise AssertionError('incomplete qualification ledger accepted')
        assert not (root/'reject-incomplete-ledger/seal.json').exists()
        write_ledger(rows);window_data['ledger_sha256']=sha256(ledger.read_bytes()).hexdigest();write(windows,window_data)
        with redirect_stdout(StringIO()):
            create(root/'TEST-ONLY-seal',inputs,'logistic',windows,capacity,restart,fake_audit,fresh,ledger,artifacts)
        seal=root/'TEST-ONLY-seal/seal.json'
        verify_freeze(seal,inputs,'logistic')
        accounting=json.loads((seal.parent/'qualification_accounting.json').read_text())
        assert accounting['total_attempts']==881 and len(accounting['first_failures'])==1
        ledger_copy=seal.parent/'qualification_ledger.jsonl';original_ledger=ledger_copy.read_bytes()
        ledger_copy.write_text('tampered')
        try:verify_freeze(seal,inputs,'logistic')
        except ValueError as error:assert 'qualification ledger hash mismatch' in str(error)
        else:raise AssertionError('modified qualification ledger accepted')
        ledger_copy.write_bytes(original_ledger)
        (seal.parent/'fresh_preflight.json').write_text('tampered')
        try:verify_freeze(seal,inputs,'logistic')
        except ValueError as error:assert 'hash mismatch' in str(error)
        else:raise AssertionError('modified fresh preflight accepted')
    print('real-scope candidate rejects marked mock qualification and capacity receipts')


if __name__=='__main__':main()
