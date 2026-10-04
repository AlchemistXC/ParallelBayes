"""Archived runtime evidence is relocatable without consulting a live host."""
import json
from pathlib import Path
import shutil
import sqlite3
import sys

import numpy as np
import pytest

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'scripts/completion'),str(ROOT/'r-package/inst/python')]


@pytest.mark.skipif(sys.platform!='darwin',reason='Fixture producer uses native Mac coordinator')
def test_registered_evidence_survives_relocation_and_rejects_changed_identity(tmp_path):
    from formal_coordinator import TaskCoordinator
    from formal_runtime import file_hash
    from formal_evidence import RuntimeEvidence
    worker=tmp_path/'worker.py'
    worker.write_text('''import json,sys
from pathlib import Path
out=Path(sys.argv[2]);(out/'payload.bin').write_bytes(b'actual immutable payload')
(out/'worker-result.json').write_text(json.dumps(dict(status='completed',samples_eligible=True)))
''')
    original=tmp_path/'original';task={'id':'a','protocol_sha256':'fixture'}
    c=TaskCoordinator(tmp_path/'host.lock')
    c.run(task,{'input':'frozen'},worker,original,0,2**30)
    moved=tmp_path/'moved';moved.mkdir();shutil.copytree(original,moved/'task-a')
    snapshot=moved/'registry.sqlite3'
    with sqlite3.connect(c.registry_path/'registry.sqlite3') as src:
        with sqlite3.connect(snapshot) as dst:src.backup(dst)
    expected=file_hash(snapshot)
    # Original paths are no longer available to the reader. They remain in
    # binding/process records only as historical identities.
    shutil.rmtree(original);worker.unlink()
    locations={str(original):'task-a',str(tmp_path/'never-started'):'missing'}
    with RuntimeEvidence(snapshot,expected,moved,locations) as evidence:
        h=evidence.history(task,str(original))
        assert h['summary']['outcome']=='valid' and h['summary']['attempt_count']==1
        assert h['eligible_directory']==str((moved/'task-a').resolve())
        assert h['attempts'][0]['attempt_id']==str(original)
        assert evidence.history({'id':'unregistered','protocol_sha256':'fixture'},str(tmp_path/'never-started'))['summary']['outcome']=='not_run'
        with pytest.raises(ValueError,match='identity'):
            evidence.history(dict(task,model='changed'),str(original))
    (moved/'task-a/attempt-0001/payload.bin').write_bytes(b'changed')
    with RuntimeEvidence(snapshot,expected,moved,locations) as evidence:
        with pytest.raises(ValueError,match='checksum'):
            evidence.history(task,str(original))
    with pytest.raises(ValueError,match='snapshot'):
        RuntimeEvidence(snapshot,'0'*64,moved,locations)


@pytest.mark.skipif(sys.platform!='darwin',reason='Fixture producer uses native Mac coordinator')
def test_relocated_recovery_keeps_original_cost_and_unique_retry_lineage(tmp_path):
    from formal_coordinator import TaskCoordinator
    from formal_runtime import file_hash
    from formal_evidence import RuntimeEvidence
    worker=tmp_path/'worker.py'
    worker.write_text('''import json,sys
from pathlib import Path
out=Path(sys.argv[2]);(out/'payload.bin').write_bytes(Path(sys.argv[1]).read_bytes())
if out.parent.name=='original':sys.exit(7)
(out/'worker-result.json').write_text(json.dumps(dict(status='completed',samples_eligible=True)))
''')
    c=TaskCoordinator(tmp_path/'host.lock');task={'id':'recover','protocol_sha256':'fixture'}
    original=tmp_path/'original'
    first=c.run(task,{'actual_noise':[1.,-1.]},worker,original,0,2**30)
    retried=c.retry(original,reason='Injected exit after actual request saved')
    moved=tmp_path/'moved';moved.mkdir()
    for suffix in ('','.retry','.recovery'):
        shutil.copytree(tmp_path/('original'+suffix),moved/('relocated'+suffix))
    snapshot=moved/'snapshot.sqlite3'
    with sqlite3.connect(c.registry_path/'registry.sqlite3') as src:
        with sqlite3.connect(snapshot) as dst:src.backup(dst)
    for suffix in ('','.retry','.recovery'):shutil.rmtree(tmp_path/('original'+suffix))
    locations={str(original):'relocated',str(original)+'.retry':'relocated.retry'}
    with RuntimeEvidence(snapshot,file_hash(snapshot),moved,locations) as evidence:
        h=evidence.history(task,str(original))
        assert h['summary']==retried['history']['summary']
        assert h['summary']['prior_interruption_known_seconds']==first['completion']['inclusive_preflight_through_terminal_seconds']
        assert h['summary']['attempt_count']==2 and h['summary']['outcome']=='valid'
        assert h['eligible_directory']==str(moved/'relocated.retry')
        assert [a['attempt_id'] for a in h['attempts']]==[str(original),str(original)+'.retry']
    recovery=moved/'relocated.recovery/recovery.json';recovery.write_text('{}')
    with RuntimeEvidence(snapshot,file_hash(snapshot),moved,locations) as evidence:
        with pytest.raises(ValueError,match='checksum'):
            evidence.history(task,str(original))
