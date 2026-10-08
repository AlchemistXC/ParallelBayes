"""Administrative task-boundary pause records, outside frozen scientific assets."""
import json
from pathlib import Path
import time
import uuid
from formal_runtime import atomic_json,file_hash,host_lease


def request_pause(bundle,protocol_sha256,reason):
    if not isinstance(reason,str) or not reason.strip():raise ValueError('Explicit pause reason required')
    bundle=Path(bundle)
    with host_lease(bundle/'control.lock','compact pause request'):
        base=bundle/'control';record=base/'requests'/uuid.uuid4().hex;record.mkdir(parents=True,exist_ok=False)
        path=record/'request.json'
        atomic_json(path,dict(protocol_sha256=protocol_sha256,reason=reason,requested_ns=time.time_ns(),
            action='Finish current owned task, seal/export/checkpoint, then stop before new dispatch',
            scientific_protocol_changed=False))
        pointer=dict(path=path.relative_to(bundle).as_posix(),sha256=file_hash(path))
        atomic_json(base/'pause.json',pointer)
        return pointer


def pause_pending(bundle,protocol_sha256):
    bundle=Path(bundle);pointer=bundle/'control/pause.json'
    if not pointer.exists():return None
    p=json.loads(pointer.read_text());path=bundle/p['path']
    if file_hash(path)!=p['sha256']:raise ValueError('Pause request checksum changed')
    request=json.loads(path.read_text())
    if request['protocol_sha256']!=protocol_sha256:raise ValueError('Pause requested for another protocol')
    resumed=bundle/'control/resume.json'
    if resumed.exists():
        value=json.loads(resumed.read_text())
        if value['pause_request_sha256']==p['sha256']:return None
    return dict(pointer=p,request=request)


def acknowledge_pause(bundle,protocol_sha256,reason):
    if not isinstance(reason,str) or not reason.strip():raise ValueError('Explicit continuation reason required')
    bundle=Path(bundle)
    with host_lease(bundle/'control.lock','compact explicit pause acknowledgement'):
        pending=pause_pending(bundle,protocol_sha256)
        if pending is None:raise ValueError('No unacknowledged pause request')
        record=dict(pause_request_sha256=pending['pointer']['sha256'],reason=reason,acknowledged_ns=time.time_ns(),
            no_sampling=True)
        path=bundle/'control/acknowledgements'/uuid.uuid4().hex;path.mkdir(parents=True,exist_ok=False)
        atomic_json(path/'resume.json',record);atomic_json(bundle/'control/resume.json',record)
        return record
