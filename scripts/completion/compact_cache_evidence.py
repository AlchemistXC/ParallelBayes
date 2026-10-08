"""Read-only compact cache artifact validation; no executor or random generation."""
import json
from pathlib import Path
import numpy as np
from compact_contract import validate_probe
from compact_cache_summary import summarize_probe
from formal_runtime import file_hash
from formal_streaming import read_member


def read_cached_probe(directory):
    directory=Path(directory);manifest=json.loads((directory/'MANIFEST.json').read_text())
    if {p.name for p in directory.iterdir() if p.is_file()}!=set(manifest)|{'MANIFEST.json'}:
        raise ValueError('Compact cache inventory differs')
    for name,h in manifest.items():
        path=directory/name
        if Path(name).name!=name or path.is_symlink() or file_hash(path)!=h:raise ValueError('Compact cache member changed')
    request=json.loads((directory/'request.json').read_text());probe=request['probe']
    c=validate_probe(request['capsule'],request['capsule_sha256'],probe)
    binding=json.loads((directory/'binding.json').read_text());report=json.loads((directory/'cache-result.json').read_text())
    if (report['artifact_kind']!='cache_measurement' or report['samples_eligible'] is not False or
        report['probe']!=probe or report['binding']!=binding):raise ValueError('Compact cache identity/qualification differs')
    records=report['observation']['records'];states=report['observation']['execution_outcomes']
    if len(records)!=4 or len(states)!=4:raise ValueError('Complete four-call frame required')
    for i,r in enumerate(records):
        if r is None:continue
        if r!=json.loads((directory/f'execution-{i}.json').read_text()):raise ValueError('Compact per-call record changed')
        if r['actual_array_file'] is None:
            if r['technical_output_valid'] or states[i]=='valid' or r['actual_array_sha256'] is not None:
                raise ValueError('Missing cache arrays cannot qualify')
            continue
        raw=directory/r['actual_array_file']
        if raw.name!=f'execution-{i}.npz' or file_hash(raw)!=r['actual_array_sha256']:raise ValueError('Compact raw cache hash differs')
        q=read_member(raw,'unconstrained',c['controls']['maximum_member_bytes'])
        accept=read_member(raw,'accept',c['controls']['maximum_member_bytes'])
        shape=(binding['config']['chains'],binding['config']['draws'],c['target']['dimension'])
        if q.shape!=shape or accept.shape!=shape[:2] or accept.dtype!=np.bool_:raise ValueError('Compact cache shape/type differs')
        if r['technical_output_valid'] and (not np.isfinite(q).all() or not r['audit']['passed'] or any(r['audit']['acceptance_mismatches'])):
            raise ValueError('Cache validity conflicts with saved audit')
        if (states[i]=='valid')!=r['technical_output_valid']:raise ValueError('Compact cache call outcome differs')
    expected=summarize_probe(probe,records,expected_tape_sha256=binding['tape_sha256'],
        expected_target_id=binding['target_id'],expected_config=binding['config'])
    if report['summary']!=expected or report['measurement_available']!=expected['all_executions_valid']:
        raise ValueError('Compact cache summary differs')
    return report
