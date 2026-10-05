"""Read-only batches must remain bound to the whole plan, not self-consistent capsules."""
import copy
import json
from pathlib import Path
import sys
import pytest
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'scripts/completion'),str(ROOT/'r-package/inst/python'),str(ROOT/'examples')]


def test_rehashed_capsule_cannot_replace_frozen_scientific_plan():
    from audit_batch_archive import verify_binding
    from batch_contract import BatchPlan
    from formal_runtime import fingerprint
    p=json.loads((ROOT/'benchmark/protocols/batch-schema-maximum-mac-v1.json').read_text())
    plan=BatchPlan(p);task=next(t for t in plan.tasks() if t['kernel']=='mala');c,h=plan.capsule(task['id'])
    root=dict(protocol_sha256=plan.protocol_sha256,inputs='/historical/inputs',rscript='/historical/R',r_library='/historical/Rlib',host_lock='/historical/host.lock')
    binding=dict(task=dict(task,protocol_sha256=plan.protocol_sha256),request=dict(capsule=c,capsule_sha256=h,**{k:root[k] for k in ('inputs','rscript','r_library')}),
        worker_sha256=p['source_files']['scripts/completion/batch_worker.py'],
        host_lock=root['host_lock'],required_disk_bytes=p['required_disk_bytes_per_task'],max_tree_rss_bytes=p['process_tree_rss_limit_bytes'])
    assert verify_binding(plan,task,binding,root)==(c,h)
    changed=copy.deepcopy(binding);changed['request']['capsule']['target']['step_mala']*=2
    changed['request']['capsule_sha256']=fingerprint(changed['request']['capsule'])
    with pytest.raises(ValueError,match='declared plan'):
        verify_binding(plan,task,changed,root)
    changed=copy.deepcopy(binding);changed['request']['inputs']='/regenerated/inputs'
    with pytest.raises(ValueError,match='input/environment'):
        verify_binding(plan,task,changed,root)
    changed=copy.deepcopy(binding);changed['max_tree_rss_bytes']*=2
    with pytest.raises(ValueError,match='resource'):
        verify_binding(plan,task,changed,root)
