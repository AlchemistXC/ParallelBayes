"""Actual input reading, without an execution/platform gate or RNG."""
from pathlib import Path
from formal_runtime import file_hash
def payload(request,c):
    from formal_streaming import read_member
    from mechanism_runner import actual_hash
    path=Path(request['inputs'])/c['task']['input']
    if file_hash(path)!=c['input']['sha256']:raise ValueError('Actual input file differs')
    values={k:read_member(path,k,c['controls']['maximum_member_bytes']) for k in ('initial','noise','log_uniform','directions','nuts_seeds')}
    if actual_hash(values)!=c['input']['actual_sha256']:raise ValueError('Actual input arrays differ')
    return values
